__FILENAME__ = parser
# coding: utf8
"""
    cssselect.parser
    ================

    Tokenizer, parser and parsed objects for CSS selectors.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import sys
import re
import operator


if sys.version_info[0] < 3:
    _unicode = unicode
    _unichr = unichr
else:
    _unicode = str
    _unichr = chr


def ascii_lower(string):
    """Lower-case, but only in the ASCII range."""
    return string.encode('utf8').lower().decode('utf8')


class SelectorError(Exception):
    """Common parent for :class:`SelectorSyntaxError` and
    :class:`ExpressionError`.

    You can just use ``except SelectorError:`` when calling
    :meth:`~GenericTranslator.css_to_xpath` and handle both exceptions types.

    """

class SelectorSyntaxError(SelectorError, SyntaxError):
    """Parsing a selector that does not match the grammar."""


#### Parsed objects

class Selector(object):
    """
    Represents a parsed selector.

    :meth:`~GenericTranslator.selector_to_xpath` accepts this object,
    but ignores :attr:`pseudo_element`. It is the user’s responsibility
    to account for pseudo-elements and reject selectors with unknown
    or unsupported pseudo-elements.

    """
    def __init__(self, tree, pseudo_element=None):
        self.parsed_tree = tree
        if pseudo_element is not None and not isinstance(
                pseudo_element, FunctionalPseudoElement):
            pseudo_element = ascii_lower(pseudo_element)
        #: A :class:`FunctionalPseudoElement`,
        #: or the identifier for the pseudo-element as a string,
        #  or ``None``.
        #:
        #: +-------------------------+----------------+--------------------------------+
        #: |                         | Selector       | Pseudo-element                 |
        #: +=========================+================+================================+
        #: | CSS3 syntax             | ``a::before``  | ``'before'``                   |
        #: +-------------------------+----------------+--------------------------------+
        #: | Older syntax            | ``a:before``   | ``'before'``                   |
        #: +-------------------------+----------------+--------------------------------+
        #: | From the Lists3_ draft, | ``li::marker`` | ``'marker'``                   |
        #: | not in Selectors3       |                |                                |
        #: +-------------------------+----------------+--------------------------------+
        #: | Invalid pseudo-class    | ``li:marker``  | ``None``                       |
        #: +-------------------------+----------------+--------------------------------+
        #: | Functinal               | ``a::foo(2)``  | ``FunctionalPseudoElement(…)`` |
        #: +-------------------------+----------------+--------------------------------+
        #:
        #: .. _Lists3: http://www.w3.org/TR/2011/WD-css3-lists-20110524/#marker-pseudoelement
        self.pseudo_element = pseudo_element

    def __repr__(self):
        if isinstance(self.pseudo_element, FunctionalPseudoElement):
            pseudo_element = repr(self.pseudo_element)
        elif self.pseudo_element:
            pseudo_element = '::%s' % self.pseudo_element
        else:
            pseudo_element = ''
        return '%s[%r%s]' % (
            self.__class__.__name__, self.parsed_tree, pseudo_element)

    def specificity(self):
        """Return the specificity_ of this selector as a tuple of 3 integers.

        .. _specificity: http://www.w3.org/TR/selectors/#specificity

        """
        a, b, c = self.parsed_tree.specificity()
        if self.pseudo_element:
            c += 1
        return a, b, c


class Class(object):
    """
    Represents selector.class_name
    """
    def __init__(self, selector, class_name):
        self.selector = selector
        self.class_name = class_name

    def __repr__(self):
        return '%s[%r.%s]' % (
            self.__class__.__name__, self.selector, self.class_name)

    def specificity(self):
        a, b, c = self.selector.specificity()
        b += 1
        return a, b, c


class FunctionalPseudoElement(object):
    """
    Represents selector::name(arguments)

    .. attribute:: name

        The name (identifier) of the pseudo-element, as a string.

    .. attribute:: arguments

        The arguments of the pseudo-element, as a list of tokens.

        **Note:** tokens are not part of the public API,
        and may change between cssselect versions.
        Use at your own risks.

    """
    def __init__(self, name, arguments):
        self.name = ascii_lower(name)
        self.arguments = arguments

    def __repr__(self):
        return '%s[::%s(%r)]' % (
            self.__class__.__name__, self.name,
            [token.value for token in self.arguments])

    def argument_types(self):
        return [token.type for token in self.arguments]

    def specificity(self):
        a, b, c = self.selector.specificity()
        b += 1
        return a, b, c


class Function(object):
    """
    Represents selector:name(expr)
    """
    def __init__(self, selector, name, arguments):
        self.selector = selector
        self.name = ascii_lower(name)
        self.arguments = arguments

    def __repr__(self):
        return '%s[%r:%s(%r)]' % (
            self.__class__.__name__, self.selector, self.name,
            [token.value for token in self.arguments])

    def argument_types(self):
        return [token.type for token in self.arguments]

    def specificity(self):
        a, b, c = self.selector.specificity()
        b += 1
        return a, b, c


class Pseudo(object):
    """
    Represents selector:ident
    """
    def __init__(self, selector, ident):
        self.selector = selector
        self.ident = ascii_lower(ident)

    def __repr__(self):
        return '%s[%r:%s]' % (
            self.__class__.__name__, self.selector, self.ident)

    def specificity(self):
        a, b, c = self.selector.specificity()
        b += 1
        return a, b, c


class Negation(object):
    """
    Represents selector:not(subselector)
    """
    def __init__(self, selector, subselector):
        self.selector = selector
        self.subselector = subselector

    def __repr__(self):
        return '%s[%r:not(%r)]' % (
            self.__class__.__name__, self.selector, self.subselector)

    def specificity(self):
        a1, b1, c1 = self.selector.specificity()
        a2, b2, c2 = self.subselector.specificity()
        return a1 + a2, b1 + b2, c1 + c2


class Attrib(object):
    """
    Represents selector[namespace|attrib operator value]
    """
    def __init__(self, selector, namespace, attrib, operator, value):
        self.selector = selector
        self.namespace = namespace
        self.attrib = attrib
        self.operator = operator
        self.value = value

    def __repr__(self):
        if self.namespace:
            attrib = '%s|%s' % (self.namespace, self.attrib)
        else:
            attrib = self.attrib
        if self.operator == 'exists':
            return '%s[%r[%s]]' % (
                self.__class__.__name__, self.selector, attrib)
        else:
            return '%s[%r[%s %s %r]]' % (
                self.__class__.__name__, self.selector, attrib,
                self.operator, self.value)

    def specificity(self):
        a, b, c = self.selector.specificity()
        b += 1
        return a, b, c


class Element(object):
    """
    Represents namespace|element

    `None` is for the universal selector '*'

    """
    def __init__(self, namespace=None, element=None):
        self.namespace = namespace
        self.element = element

    def __repr__(self):
        element = self.element or '*'
        if self.namespace:
            element = '%s|%s' % (self.namespace, element)
        return '%s[%s]' % (self.__class__.__name__, element)

    def specificity(self):
        if self.element:
            return 0, 0, 1
        else:
            return 0, 0, 0


class Hash(object):
    """
    Represents selector#id
    """
    def __init__(self, selector, id):
        self.selector = selector
        self.id = id

    def __repr__(self):
        return '%s[%r#%s]' % (
            self.__class__.__name__, self.selector, self.id)

    def specificity(self):
        a, b, c = self.selector.specificity()
        a += 1
        return a, b, c


class CombinedSelector(object):
    def __init__(self, selector, combinator, subselector):
        assert selector is not None
        self.selector = selector
        self.combinator = combinator
        self.subselector = subselector

    def __repr__(self):
        if self.combinator == ' ':
            comb = '<followed>'
        else:
            comb = self.combinator
        return '%s[%r %s %r]' % (
            self.__class__.__name__, self.selector, comb, self.subselector)

    def specificity(self):
        a1, b1, c1 = self.selector.specificity()
        a2, b2, c2 = self.subselector.specificity()
        return a1 + a2, b1 + b2, c1 + c2


#### Parser

# foo
_el_re = re.compile(r'^[ \t\r\n\f]*([a-zA-Z]+)[ \t\r\n\f]*$')

# foo#bar or #bar
_id_re = re.compile(r'^[ \t\r\n\f]*([a-zA-Z]*)#([a-zA-Z0-9_-]+)[ \t\r\n\f]*$')

# foo.bar or .bar
_class_re = re.compile(
    r'^[ \t\r\n\f]*([a-zA-Z]*)\.([a-zA-Z][a-zA-Z0-9_-]*)[ \t\r\n\f]*$')


def parse(css):
    """Parse a CSS *group of selectors*.

    If you don't care about pseudo-elements or selector specificity,
    you can skip this and use :meth:`~GenericTranslator.css_to_xpath`.

    :param css:
        A *group of selectors* as an Unicode string.
    :raises:
        :class:`SelectorSyntaxError` on invalid selectors.
    :returns:
        A list of parsed :class:`Selector` objects, one for each
        selector in the comma-separated group.

    """
    # Fast path for simple cases
    match = _el_re.match(css)
    if match:
        return [Selector(Element(element=match.group(1)))]
    match = _id_re.match(css)
    if match is not None:
        return [Selector(Hash(Element(element=match.group(1) or None),
                              match.group(2)))]
    match = _class_re.match(css)
    if match is not None:
        return [Selector(Class(Element(element=match.group(1) or None),
                               match.group(2)))]

    stream = TokenStream(tokenize(css))
    stream.source = css
    return list(parse_selector_group(stream))
#    except SelectorSyntaxError:
#        e = sys.exc_info()[1]
#        message = "%s at %s -> %r" % (
#            e, stream.used, stream.peek())
#        e.msg = message
#        if sys.version_info < (2,6):
#            e.message = message
#        e.args = tuple([message])
#        raise


def parse_selector_group(stream):
    stream.skip_whitespace()
    while 1:
        yield Selector(*parse_selector(stream))
        if stream.peek() == ('DELIM', ','):
            stream.next()
            stream.skip_whitespace()
        else:
            break

def parse_selector(stream):
    result, pseudo_element = parse_simple_selector(stream)
    while 1:
        stream.skip_whitespace()
        peek = stream.peek()
        if peek in (('EOF', None), ('DELIM', ',')):
            break
        if pseudo_element:
            raise SelectorSyntaxError(
                'Got pseudo-element ::%s not at the end of a selector'
                % pseudo_element)
        if peek.is_delim('+', '>', '~'):
            # A combinator
            combinator = stream.next().value
            stream.skip_whitespace()
        else:
            # By exclusion, the last parse_simple_selector() ended
            # at peek == ' '
            combinator = ' '
        next_selector, pseudo_element = parse_simple_selector(stream)
        result = CombinedSelector(result, combinator, next_selector)
    return result, pseudo_element


def parse_simple_selector(stream, inside_negation=False):
    stream.skip_whitespace()
    selector_start = len(stream.used)
    peek = stream.peek()
    if peek.type == 'IDENT' or peek == ('DELIM', '*'):
        if peek.type == 'IDENT':
            namespace = stream.next().value
        else:
            stream.next()
            namespace = None
        if stream.peek() == ('DELIM', '|'):
            stream.next()
            element = stream.next_ident_or_star()
        else:
            element = namespace
            namespace = None
    else:
        element = namespace = None
    result = Element(namespace, element)
    pseudo_element = None
    while 1:
        peek = stream.peek()
        if peek.type in ('S', 'EOF') or peek.is_delim(',', '+', '>', '~') or (
                inside_negation and peek == ('DELIM', ')')):
            break
        if pseudo_element:
            raise SelectorSyntaxError(
                'Got pseudo-element ::%s not at the end of a selector'
                % pseudo_element)
        if peek.type == 'HASH':
            result = Hash(result, stream.next().value)
        elif peek == ('DELIM', '.'):
            stream.next()
            result = Class(result, stream.next_ident())
        elif peek == ('DELIM', '['):
            stream.next()
            result = parse_attrib(result, stream)
        elif peek == ('DELIM', ':'):
            stream.next()
            if stream.peek() == ('DELIM', ':'):
                stream.next()
                pseudo_element = stream.next_ident()
                if stream.peek() == ('DELIM', '('):
                    stream.next()
                    pseudo_element = FunctionalPseudoElement(
                        pseudo_element, parse_arguments(stream))
                continue
            ident = stream.next_ident()
            if ident.lower() in ('first-line', 'first-letter',
                                 'before', 'after'):
                # Special case: CSS 2.1 pseudo-elements can have a single ':'
                # Any new pseudo-element must have two.
                pseudo_element = _unicode(ident)
                continue
            if stream.peek() != ('DELIM', '('):
                result = Pseudo(result, ident)
                continue
            stream.next()
            stream.skip_whitespace()
            if ident.lower() == 'not':
                if inside_negation:
                    raise SelectorSyntaxError('Got nested :not()')
                argument, argument_pseudo_element = parse_simple_selector(
                    stream, inside_negation=True)
                next = stream.next()
                if argument_pseudo_element:
                    raise SelectorSyntaxError(
                        'Got pseudo-element ::%s inside :not() at %s'
                        % (argument_pseudo_element, next.pos))
                if next != ('DELIM', ')'):
                    raise SelectorSyntaxError("Expected ')', got %s" % (next,))
                result = Negation(result, argument)
            else:
                result = Function(result, ident, parse_arguments(stream))
        else:
            raise SelectorSyntaxError(
                "Expected selector, got %s" % (peek,))
    if len(stream.used) == selector_start:
        raise SelectorSyntaxError(
            "Expected selector, got %s" % (stream.peek(),))
    return result, pseudo_element


def parse_arguments(stream):
    arguments = []
    while 1:
        stream.skip_whitespace()
        next = stream.next()
        if next.type in ('IDENT', 'STRING', 'NUMBER') or next in [
                ('DELIM', '+'), ('DELIM', '-')]:
            arguments.append(next)
        elif next == ('DELIM', ')'):
            return arguments
        else:
            raise SelectorSyntaxError(
                "Expected an argument, got %s" % (next,))


def parse_attrib(selector, stream):
    stream.skip_whitespace()
    attrib = stream.next_ident_or_star()
    if attrib is None and stream.peek() != ('DELIM', '|'):
        raise SelectorSyntaxError(
            "Expected '|', got %s" % (stream.peek(),))
    if stream.peek() == ('DELIM', '|'):
        stream.next()
        if stream.peek() == ('DELIM', '='):
            namespace = None
            stream.next()
            op = '|='
        else:
            namespace = attrib
            attrib = stream.next_ident()
            op = None
    else:
        namespace = op = None
    if op is None:
        stream.skip_whitespace()
        next = stream.next()
        if next == ('DELIM', ']'):
            return Attrib(selector, namespace, attrib, 'exists', None)
        elif next == ('DELIM', '='):
            op = '='
        elif next.is_delim('^', '$', '*', '~', '|', '!') and (
                stream.peek() == ('DELIM', '=')):
            op = next.value + '='
            stream.next()
        else:
            raise SelectorSyntaxError(
                "Operator expected, got %s" % (next,))
    stream.skip_whitespace()
    value = stream.next()
    if value.type not in ('IDENT', 'STRING'):
        raise SelectorSyntaxError(
            "Expected string or ident, got %s" % (value,))
    stream.skip_whitespace()
    next = stream.next()
    if next != ('DELIM', ']'):
        raise SelectorSyntaxError(
            "Expected ']', got %s" % (next,))
    return Attrib(selector, namespace, attrib, op, value.value)


def parse_series(tokens):
    """
    Parses the arguments for :nth-child() and friends.

    :raises: A list of tokens
    :returns: :``(a, b)``

    """
    for token in tokens:
        if token.type == 'STRING':
            raise ValueError('String tokens not allowed in series.')
    s = ''.join(token.value for token in tokens).strip()
    if s == 'odd':
        return (2, 1)
    elif s == 'even':
        return (2, 0)
    elif s == 'n':
        return (1, 0)
    if 'n' not in s:
        # Just b
        return (0, int(s))
    a, b = s.split('n', 1)
    if not a:
        a = 1
    elif a == '-' or a == '+':
        a = int(a+'1')
    else:
        a = int(a)
    if not b:
        b = 0
    else:
        b = int(b)
    return (a, b)


#### Token objects

class Token(tuple):
    def __new__(cls, type_, value, pos):
        obj = tuple.__new__(cls, (type_, value))
        obj.pos = pos
        return obj

    def __repr__(self):
        return "<%s '%s' at %i>" % (self.type, self.value, self.pos)

    def is_delim(self, *values):
        return self.type == 'DELIM' and self.value in values

    type = property(operator.itemgetter(0))
    value = property(operator.itemgetter(1))


class EOFToken(Token):
    def __new__(cls, pos):
        return Token.__new__(cls, 'EOF', None, pos)

    def __repr__(self):
        return '<%s at %i>' % (self.type, self.pos)


#### Tokenizer


class TokenMacros:
    unicode_escape = r'\\([0-9a-f]{1,6})(?:\r\n|[ \n\r\t\f])?'
    escape = unicode_escape + r'|\\[^\n\r\f0-9a-f]'
    string_escape = r'\\(?:\n|\r\n|\r|\f)|' + escape
    nonascii = r'[^\0-\177]'
    nmchar = '[_a-z0-9-]|%s|%s' % (escape, nonascii)
    nmstart = '[_a-z]|%s|%s' % (escape, nonascii)

def _compile(pattern):
    return re.compile(pattern % vars(TokenMacros), re.IGNORECASE).match

_match_whitespace = _compile(r'[ \t\r\n\f]+')
_match_number = _compile('[+-]?(?:[0-9]*\.[0-9]+|[0-9]+)')
_match_hash = _compile('#(?:%(nmchar)s)+')
_match_ident = _compile('-?(?:%(nmstart)s)(?:%(nmchar)s)*')
_match_string_by_quote = {
    "'": _compile(r"([^\n\r\f\\']|%(string_escape)s)*"),
    '"': _compile(r'([^\n\r\f\\"]|%(string_escape)s)*'),
}

_sub_simple_escape = re.compile(r'\\(.)').sub
_sub_unicode_escape = re.compile(TokenMacros.unicode_escape, re.I).sub
_sub_newline_escape =re.compile(r'\\(?:\n|\r\n|\r|\f)').sub

# Same as r'\1', but faster on CPython
if hasattr(operator, 'methodcaller'):
    # Python 2.6+
    _replace_simple = operator.methodcaller('group', 1)
else:
    def _replace_simple(match):
        return match.group(1)

def _replace_unicode(match):
    codepoint = int(match.group(1), 16)
    if codepoint > sys.maxunicode:
        codepoint = 0xFFFD
    return _unichr(codepoint)


def unescape_ident(value):
    value = _sub_unicode_escape(_replace_unicode, value)
    value = _sub_simple_escape(_replace_simple, value)
    return value


def tokenize(s):
    pos = 0
    len_s = len(s)
    while pos < len_s:
        match = _match_whitespace(s, pos=pos)
        if match:
            yield Token('S', ' ', pos)
            pos = match.end()
            continue

        match = _match_ident(s, pos=pos)
        if match:
            value = _sub_simple_escape(_replace_simple,
                    _sub_unicode_escape(_replace_unicode, match.group()))
            yield Token('IDENT', value, pos)
            pos = match.end()
            continue

        match = _match_hash(s, pos=pos)
        if match:
            value = _sub_simple_escape(_replace_simple,
                    _sub_unicode_escape(_replace_unicode, match.group()[1:]))
            yield Token('HASH', value, pos)
            pos = match.end()
            continue

        quote = s[pos]
        if quote in _match_string_by_quote:
            match = _match_string_by_quote[quote](s, pos=pos + 1)
            assert match, 'Should have found at least an empty match'
            end_pos = match.end()
            if end_pos == len_s:
                raise SelectorSyntaxError('Unclosed string at %s' % pos)
            if s[end_pos] != quote:
                raise SelectorSyntaxError('Invalid string at %s' % pos)
            value = _sub_simple_escape(_replace_simple,
                    _sub_unicode_escape(_replace_unicode,
                    _sub_newline_escape('', match.group())))
            yield Token('STRING', value, pos)
            pos = end_pos + 1
            continue

        match = _match_number(s, pos=pos)
        if match:
            value = match.group()
            yield Token('NUMBER', value, pos)
            pos = match.end()
            continue

        pos2 = pos + 2
        if s[pos:pos2] == '/*':
            pos = s.find('*/', pos2)
            if pos == -1:
                pos = len_s
            else:
                pos += 2
            continue

        yield Token('DELIM', s[pos], pos)
        pos += 1

    assert pos == len_s
    yield EOFToken(pos)


class TokenStream(object):
    def __init__(self, tokens, source=None):
        self.used = []
        self.tokens = iter(tokens)
        self.source = source
        self.peeked = None
        self._peeking = False
        try:
            self.next_token = self.tokens.next
        except AttributeError:
            # Python 3
            self.next_token = self.tokens.__next__

    def next(self):
        if self._peeking:
            self._peeking = False
            self.used.append(self.peeked)
            return self.peeked
        else:
            next = self.next_token()
            self.used.append(next)
            return next

    def peek(self):
        if not self._peeking:
            self.peeked = self.next_token()
            self._peeking = True
        return self.peeked

    def next_ident(self):
        next = self.next()
        if next.type != 'IDENT':
            raise SelectorSyntaxError('Expected ident, got %s' % (next,))
        return next.value

    def next_ident_or_star(self):
        next = self.next()
        if next.type == 'IDENT':
            return next.value
        elif next == ('DELIM', '*'):
            return None
        else:
            raise SelectorSyntaxError(
                "Expected ident or '*', got %s" % (next,))

    def skip_whitespace(self):
        peek = self.peek()
        if peek.type == 'S':
            self.next()

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# coding: utf8
"""
    Tests for cssselect
    ===================

    These tests can be run either by py.test or by the standard library's
    unittest. They use plain ``assert`` statements and do little reporting
    themselves in case of failure.

    Use py.test to get fancy error reporting and assert introspection.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import sys
import unittest

from lxml import etree, html
from cssselect import (parse, GenericTranslator, HTMLTranslator,
                       SelectorSyntaxError, ExpressionError)
from cssselect.parser import (tokenize, parse_series, _unicode,
                              FunctionalPseudoElement)
from cssselect.xpath import _unicode_safe_getattr, XPathExpr


if sys.version_info[0] < 3:
    # Python 2
    def u(text):
        return text.decode('utf8')
else:
    # Python 3
    def u(text):
        return text


class TestCssselect(unittest.TestCase):
    def test_tokenizer(self):
        tokens = [
            _unicode(item) for item in tokenize(
                u(r'E\ é > f [a~="y\"x"]:nth(/* fu /]* */-3.7)'))]
        assert tokens == [
            u("<IDENT 'E é' at 0>"),
            "<S ' ' at 4>",
            "<DELIM '>' at 5>",
            "<S ' ' at 6>",
            # the no-break space is not whitespace in CSS
            u("<IDENT 'f ' at 7>"),  # f\xa0
            "<DELIM '[' at 9>",
            "<IDENT 'a' at 10>",
            "<DELIM '~' at 11>",
            "<DELIM '=' at 12>",
            "<STRING 'y\"x' at 13>",
            "<DELIM ']' at 19>",
            "<DELIM ':' at 20>",
            "<IDENT 'nth' at 21>",
            "<DELIM '(' at 24>",
            "<NUMBER '-3.7' at 37>",
            "<DELIM ')' at 41>",
            "<EOF at 42>",
        ]

    def test_parser(self):
        def repr_parse(css):
            selectors = parse(css)
            for selector in selectors:
                assert selector.pseudo_element is None
            return [repr(selector.parsed_tree).replace("(u'", "('")
                    for selector in selectors]

        def parse_many(first, *others):
            result = repr_parse(first)
            for other in others:
                assert repr_parse(other) == result
            return result

        assert parse_many('*') == ['Element[*]']
        assert parse_many('*|*') == ['Element[*]']
        assert parse_many('*|foo') == ['Element[foo]']
        assert parse_many('foo|*') == ['Element[foo|*]']
        assert parse_many('foo|bar') == ['Element[foo|bar]']
        # This will never match, but it is valid:
        assert parse_many('#foo#bar') == ['Hash[Hash[Element[*]#foo]#bar]']
        assert parse_many(
            'div>.foo',
            'div> .foo',
            'div >.foo',
            'div > .foo',
            'div \n>  \t \t .foo', 'div\r>\n\n\n.foo', 'div\f>\f.foo'
        ) == ['CombinedSelector[Element[div] > Class[Element[*].foo]]']
        assert parse_many('td.foo,.bar',
            'td.foo, .bar',
            'td.foo\t\r\n\f ,\t\r\n\f .bar'
        ) == [
            'Class[Element[td].foo]',
            'Class[Element[*].bar]'
        ]
        assert parse_many('div, td.foo, div.bar span') == [
            'Element[div]',
            'Class[Element[td].foo]',
            'CombinedSelector[Class[Element[div].bar] '
                '<followed> Element[span]]']
        assert parse_many('div > p') == [
            'CombinedSelector[Element[div] > Element[p]]']
        assert parse_many('td:first') == [
            'Pseudo[Element[td]:first]']
        assert parse_many('td:first') == [
            'Pseudo[Element[td]:first]']
        assert parse_many('td :first') == [
            'CombinedSelector[Element[td] '
                '<followed> Pseudo[Element[*]:first]]']
        assert parse_many('td :first') == [
            'CombinedSelector[Element[td] '
                '<followed> Pseudo[Element[*]:first]]']
        assert parse_many('a[name]', 'a[ name\t]') == [
            'Attrib[Element[a][name]]']
        assert parse_many('a [name]') == [
            'CombinedSelector[Element[a] <followed> Attrib[Element[*][name]]]']
        assert parse_many('a[rel="include"]', 'a[rel = include]') == [
            "Attrib[Element[a][rel = 'include']]"]
        assert parse_many("a[hreflang |= 'en']", "a[hreflang|=en]") == [
            "Attrib[Element[a][hreflang |= 'en']]"]
        assert parse_many('div:nth-child(10)') == [
            "Function[Element[div]:nth-child(['10'])]"]
        assert parse_many(':nth-child(2n+2)') == [
            "Function[Element[*]:nth-child(['2', 'n', '+2'])]"]
        assert parse_many('div:nth-of-type(10)') == [
            "Function[Element[div]:nth-of-type(['10'])]"]
        assert parse_many('div div:nth-of-type(10) .aclass') == [
            'CombinedSelector[CombinedSelector[Element[div] <followed> '
                "Function[Element[div]:nth-of-type(['10'])]] "
                '<followed> Class[Element[*].aclass]]']
        assert parse_many('label:only') == [
            'Pseudo[Element[label]:only]']
        assert parse_many('a:lang(fr)') == [
            "Function[Element[a]:lang(['fr'])]"]
        assert parse_many('div:contains("foo")') == [
            "Function[Element[div]:contains(['foo'])]"]
        assert parse_many('div#foobar') == [
            'Hash[Element[div]#foobar]']
        assert parse_many('div:not(div.foo)') == [
            'Negation[Element[div]:not(Class[Element[div].foo])]']
        assert parse_many('td ~ th') == [
            'CombinedSelector[Element[td] ~ Element[th]]']

    def test_pseudo_elements(self):
        def parse_pseudo(css):
            result = []
            for selector in parse(css):
                pseudo = selector.pseudo_element
                pseudo = _unicode(pseudo) if pseudo else pseudo
                # No Symbol here
                assert pseudo is None or type(pseudo) is _unicode
                selector = repr(selector.parsed_tree).replace("(u'", "('")
                result.append((selector, pseudo))
            return result

        def parse_one(css):
            result = parse_pseudo(css)
            assert len(result) == 1
            return result[0]

        assert parse_one('foo') == ('Element[foo]', None)
        assert parse_one('*') == ('Element[*]', None)
        assert parse_one(':empty') == ('Pseudo[Element[*]:empty]', None)

        # Special cases for CSS 2.1 pseudo-elements
        assert parse_one(':BEfore') == ('Element[*]', 'before')
        assert parse_one(':aftER') == ('Element[*]', 'after')
        assert parse_one(':First-Line') == ('Element[*]', 'first-line')
        assert parse_one(':First-Letter') == ('Element[*]', 'first-letter')

        assert parse_one('::befoRE') == ('Element[*]', 'before')
        assert parse_one('::AFter') == ('Element[*]', 'after')
        assert parse_one('::firsT-linE') == ('Element[*]', 'first-line')
        assert parse_one('::firsT-letteR') == ('Element[*]', 'first-letter')

        assert parse_one('::text-content') == ('Element[*]', 'text-content')
        assert parse_one('::attr(name)') == (
            "Element[*]", "FunctionalPseudoElement[::attr(['name'])]")

        assert parse_one('::Selection') == ('Element[*]', 'selection')
        assert parse_one('foo:after') == ('Element[foo]', 'after')
        assert parse_one('foo::selection') == ('Element[foo]', 'selection')
        assert parse_one('lorem#ipsum ~ a#b.c[href]:empty::selection') == (
            'CombinedSelector[Hash[Element[lorem]#ipsum] ~ '
                'Pseudo[Attrib[Class[Hash[Element[a]#b].c][href]]:empty]]',
            'selection')

        parse_pseudo('foo:before, bar, baz:after') == [
            ('Element[foo]', 'before'),
            ('Element[bar]', None),
            ('Element[baz]', 'after')]

        # Special cases for CSS 2.1 pseudo-elements are ignored by default
        for pseudo in ('after', 'before', 'first-line', 'first-letter'):
            selector, = parse('e:%s' % pseudo)
            assert selector.pseudo_element == pseudo
            assert GenericTranslator().selector_to_xpath(selector, prefix='') == "e"

        # Pseudo Elements are ignored by default, but if allowed they are not
        # supported by GenericTranslator
        tr = GenericTranslator()
        selector, = parse('e::foo')
        assert selector.pseudo_element == 'foo'
        assert tr.selector_to_xpath(selector, prefix='') == "e"
        self.assertRaises(ExpressionError, tr.selector_to_xpath, selector,
                          translate_pseudo_elements=True)

    def test_specificity(self):
        def specificity(css):
            selectors = parse(css)
            assert len(selectors) == 1
            return selectors[0].specificity()

        assert specificity('*') == (0, 0, 0)
        assert specificity(' foo') == (0, 0, 1)
        assert specificity(':empty ') == (0, 1, 0)
        assert specificity(':before') == (0, 0, 1)
        assert specificity('*:before') == (0, 0, 1)
        assert specificity(':nth-child(2)') == (0, 1, 0)
        assert specificity('.bar') == (0, 1, 0)
        assert specificity('[baz]') == (0, 1, 0)
        assert specificity('[baz="4"]') == (0, 1, 0)
        assert specificity('[baz^="4"]') == (0, 1, 0)
        assert specificity('#lipsum') == (1, 0, 0)

        assert specificity(':not(*)') == (0, 0, 0)
        assert specificity(':not(foo)') == (0, 0, 1)
        assert specificity(':not(.foo)') == (0, 1, 0)
        assert specificity(':not([foo])') == (0, 1, 0)
        assert specificity(':not(:empty)') == (0, 1, 0)
        assert specificity(':not(#foo)') == (1, 0, 0)

        assert specificity('foo:empty') == (0, 1, 1)
        assert specificity('foo:before') == (0, 0, 2)
        assert specificity('foo::before') == (0, 0, 2)
        assert specificity('foo:empty::before') == (0, 1, 2)

        assert specificity('#lorem + foo#ipsum:first-child > bar:first-line'
            ) == (2, 1, 3)

    def test_parse_errors(self):
        def get_error(css):
            try:
                parse(css)
            except SelectorSyntaxError:
                # Py2, Py3, ...
                return str(sys.exc_info()[1]).replace("(u'", "('")

        assert get_error('attributes(href)/html/body/a') == (
            "Expected selector, got <DELIM '(' at 10>")
        assert get_error('attributes(href)') == (
            "Expected selector, got <DELIM '(' at 10>")
        assert get_error('html/body/a') == (
            "Expected selector, got <DELIM '/' at 4>")
        assert get_error(' ') == (
            "Expected selector, got <EOF at 1>")
        assert get_error('div, ') == (
            "Expected selector, got <EOF at 5>")
        assert get_error(' , div') == (
            "Expected selector, got <DELIM ',' at 1>")
        assert get_error('p, , div') == (
            "Expected selector, got <DELIM ',' at 3>")
        assert get_error('div > ') == (
            "Expected selector, got <EOF at 6>")
        assert get_error('  > div') == (
            "Expected selector, got <DELIM '>' at 2>")
        assert get_error('foo|#bar') == (
            "Expected ident or '*', got <HASH 'bar' at 4>")
        assert get_error('#.foo') == (
            "Expected selector, got <DELIM '#' at 0>")
        assert get_error('.#foo') == (
            "Expected ident, got <HASH 'foo' at 1>")
        assert get_error(':#foo') == (
            "Expected ident, got <HASH 'foo' at 1>")
        assert get_error('[*]') == (
            "Expected '|', got <DELIM ']' at 2>")
        assert get_error('[foo|]') == (
            "Expected ident, got <DELIM ']' at 5>")
        assert get_error('[#]') == (
            "Expected ident or '*', got <DELIM '#' at 1>")
        assert get_error('[foo=#]') == (
            "Expected string or ident, got <DELIM '#' at 5>")
        assert get_error('[href]a') == (
            "Expected selector, got <IDENT 'a' at 6>")
        assert get_error('[rel=stylesheet]') == None
        assert get_error('[rel:stylesheet]') == (
            "Operator expected, got <DELIM ':' at 4>")
        assert get_error('[rel=stylesheet') == (
            "Expected ']', got <EOF at 15>")
        assert get_error(':lang(fr)') == None
        assert get_error(':lang(fr') == (
            "Expected an argument, got <EOF at 8>")
        assert get_error(':contains("foo') == (
            "Unclosed string at 10")
        assert get_error('foo!') == (
            "Expected selector, got <DELIM '!' at 3>")

        # Mis-placed pseudo-elements
        assert get_error('a:before:empty') == (
            "Got pseudo-element ::before not at the end of a selector")
        assert get_error('li:before a') == (
            "Got pseudo-element ::before not at the end of a selector")
        assert get_error(':not(:before)') == (
            "Got pseudo-element ::before inside :not() at 12")
        assert get_error(':not(:not(a))') == (
            "Got nested :not()")

    def test_translation(self):
        def xpath(css):
            return _unicode(GenericTranslator().css_to_xpath(css, prefix=''))

        assert xpath('*') == "*"
        assert xpath('e') == "e"
        assert xpath('*|e') == "e"
        assert xpath('e|f') == "e:f"
        assert xpath('e[foo]') == "e[@foo]"
        assert xpath('e[foo|bar]') == "e[@foo:bar]"
        assert xpath('e[foo="bar"]') == "e[@foo = 'bar']"
        assert xpath('e[foo~="bar"]') == (
            "e[@foo and contains("
               "concat(' ', normalize-space(@foo), ' '), ' bar ')]")
        assert xpath('e[foo^="bar"]') == (
            "e[@foo and starts-with(@foo, 'bar')]")
        assert xpath('e[foo$="bar"]') == (
            "e[@foo and substring(@foo, string-length(@foo)-2) = 'bar']")
        assert xpath('e[foo*="bar"]') == (
            "e[@foo and contains(@foo, 'bar')]")
        assert xpath('e[hreflang|="en"]') == (
            "e[@hreflang and ("
               "@hreflang = 'en' or starts-with(@hreflang, 'en-'))]")
        assert xpath('e:nth-child(1)') == (
            "*/*[name() = 'e' and (position() = 1)]")
        assert xpath('e:nth-last-child(1)') == (
            "*/*[name() = 'e' and (position() = last() - 1)]")
        assert xpath('e:nth-last-child(2n+2)') == (
            "*/*[name() = 'e' and ("
               "(position() +2) mod -2 = 0 and position() < (last() -2))]")
        assert xpath('e:nth-of-type(1)') == (
            "*/e[position() = 1]")
        assert xpath('e:nth-last-of-type(1)') == (
            "*/e[position() = last() - 1]")
        assert xpath('e:nth-last-of-type(1)') == (
            "*/e[position() = last() - 1]")
        assert xpath('div e:nth-last-of-type(1) .aclass') == (
            "div/descendant-or-self::*/e[position() = last() - 1]"
               "/descendant-or-self::*/*[@class and contains("
               "concat(' ', normalize-space(@class), ' '), ' aclass ')]")
        assert xpath('e:first-child') == (
            "*/*[name() = 'e' and (position() = 1)]")
        assert xpath('e:last-child') == (
            "*/*[name() = 'e' and (position() = last())]")
        assert xpath('e:first-of-type') == (
            "*/e[position() = 1]")
        assert xpath('e:last-of-type') == (
            "*/e[position() = last()]")
        assert xpath('e:only-child') == (
            "*/*[name() = 'e' and (last() = 1)]")
        assert xpath('e:only-of-type') == (
            "e[last() = 1]")
        assert xpath('e:empty') == (
            "e[not(*) and not(string-length())]")
        assert xpath('e:EmPTY') == (
            "e[not(*) and not(string-length())]")
        assert xpath('e:root') == (
            "e[not(parent::*)]")
        assert xpath('e:hover') == (
            "e[0]")  # never matches
        assert xpath('e:contains("foo")') == (
            "e[contains(., 'foo')]")
        assert xpath('e:ConTains(foo)') == (
            "e[contains(., 'foo')]")
        assert xpath('e.warning') == (
            "e[@class and contains("
               "concat(' ', normalize-space(@class), ' '), ' warning ')]")
        assert xpath('e#myid') == (
            "e[@id = 'myid']")
        assert xpath('e:not(:nth-child(odd))') == (
            "e[not((position() -1) mod 2 = 0 and position() >= 1)]")
        assert xpath('e:nOT(*)') == (
            "e[0]")  # never matches
        assert xpath('e f') == (
            "e/descendant-or-self::*/f")
        assert xpath('e > f') == (
            "e/f")
        assert xpath('e + f') == (
            "e/following-sibling::*[name() = 'f' and (position() = 1)]")
        assert xpath('e ~ f') == (
            "e/following-sibling::f")
        assert xpath('div#container p') == (
            "div[@id = 'container']/descendant-or-self::*/p")

        # Invalid characters in XPath element names
        assert xpath(r'di\a0 v') == (
            u("*[name() = 'di v']"))  # di\xa0v
        assert xpath(r'di\[v') == (
            "*[name() = 'di[v']")
        assert xpath(r'[h\a0 ref]') == (
            u("*[attribute::*[name() = 'h ref']]"))  # h\xa0ref
        assert xpath(r'[h\]ref]') == (
            "*[attribute::*[name() = 'h]ref']]")

        self.assertRaises(ExpressionError, xpath, u(':fİrst-child'))
        self.assertRaises(ExpressionError, xpath, ':first-of-type')
        self.assertRaises(ExpressionError, xpath, ':only-of-type')
        self.assertRaises(ExpressionError, xpath, ':last-of-type')
        self.assertRaises(ExpressionError, xpath, ':nth-of-type(1)')
        self.assertRaises(ExpressionError, xpath, ':nth-last-of-type(1)')
        self.assertRaises(ExpressionError, xpath, ':nth-child(n-)')
        self.assertRaises(ExpressionError, xpath, ':after')
        self.assertRaises(ExpressionError, xpath, ':lorem-ipsum')
        self.assertRaises(ExpressionError, xpath, ':lorem(ipsum)')
        self.assertRaises(ExpressionError, xpath, '::lorem-ipsum')
        self.assertRaises(TypeError, GenericTranslator().css_to_xpath, 4)
        self.assertRaises(TypeError, GenericTranslator().selector_to_xpath,
            'foo')

    def test_unicode(self):
        if sys.version_info[0] < 3:
            css = '.a\xc1b'.decode('ISO-8859-1')
        else:
            css = '.a\xc1b'

        xpath = GenericTranslator().css_to_xpath(css)
        assert css[1:] in xpath
        xpath = xpath.encode('ascii', 'xmlcharrefreplace').decode('ASCII')
        assert xpath == (
            "descendant-or-self::*[@class and contains("
            "concat(' ', normalize-space(@class), ' '), ' a&#193;b ')]")

    def test_quoting(self):
        css_to_xpath = GenericTranslator().css_to_xpath
        assert css_to_xpath('*[aval="\'"]') == (
            '''descendant-or-self::*[@aval = "'"]''')
        assert css_to_xpath('*[aval="\'\'\'"]') == (
            """descendant-or-self::*[@aval = "'''"]""")
        assert css_to_xpath('*[aval=\'"\']') == (
            '''descendant-or-self::*[@aval = '"']''')
        assert css_to_xpath('*[aval=\'"""\']') == (
            '''descendant-or-self::*[@aval = '"""']''')

    def test_unicode_escapes(self):
        # \22 == '"'  \20 == ' '
        css_to_xpath = GenericTranslator().css_to_xpath
        assert css_to_xpath(r'*[aval="\'\22\'"]') == (
            '''descendant-or-self::*[@aval = concat("'",'"',"'")]''')
        assert css_to_xpath(r'*[aval="\'\22 2\'"]') == (
            '''descendant-or-self::*[@aval = concat("'",'"2',"'")]''')
        assert css_to_xpath(r'*[aval="\'\20  \'"]') == (
            '''descendant-or-self::*[@aval = "'  '"]''')
        assert css_to_xpath('*[aval="\'\\20\r\n \'"]') == (
            '''descendant-or-self::*[@aval = "'  '"]''')

    def test_xpath_pseudo_elements(self):
        class CustomTranslator(GenericTranslator):
            def xpath_pseudo_element(self, xpath, pseudo_element):
                if isinstance(pseudo_element, FunctionalPseudoElement):
                    method = 'xpath_%s_functional_pseudo_element' % (
                        pseudo_element.name.replace('-', '_'))
                    method = _unicode_safe_getattr(self, method, None)
                    if not method:
                        raise ExpressionError(
                            "The functional pseudo-element ::%s() is unknown"
                        % pseudo_element.name)
                    xpath = method(xpath, pseudo_element.arguments)
                else:
                    method = 'xpath_%s_simple_pseudo_element' % (
                        pseudo_element.replace('-', '_'))
                    method = _unicode_safe_getattr(self, method, None)
                    if not method:
                        raise ExpressionError(
                            "The pseudo-element ::%s is unknown"
                            % pseudo_element)
                    xpath = method(xpath)
                return xpath

            # functional pseudo-class:
            # elements that have a certain number of attributes
            def xpath_nb_attr_function(self, xpath, function):
                nb_attributes = int(function.arguments[0].value)
                return xpath.add_condition(
                    "count(@*)=%d" % nb_attributes)

            # pseudo-class:
            # elements that have 5 attributes
            def xpath_five_attributes_pseudo(self, xpath):
                return xpath.add_condition("count(@*)=5")

            # functional pseudo-element:
            # element's attribute by name
            def xpath_attr_functional_pseudo_element(self, xpath, arguments):
                attribute_name = arguments[0].value
                other = XPathExpr('@%s' % attribute_name, '', )
                return xpath.join('/', other)

            # pseudo-element:
            # element's text() nodes
            def xpath_text_node_simple_pseudo_element(self, xpath):
                other = XPathExpr('text()', '', )
                return xpath.join('/', other)

            # pseudo-element:
            # element's href attribute
            def xpath_attr_href_simple_pseudo_element(self, xpath):
                other = XPathExpr('@href', '', )
                return xpath.join('/', other)

        def xpath(css):
            return _unicode(CustomTranslator().css_to_xpath(css))

        assert xpath(':five-attributes') == "descendant-or-self::*[count(@*)=5]"
        assert xpath(':nb-attr(3)') == "descendant-or-self::*[count(@*)=3]"
        assert xpath('::attr(href)') == "descendant-or-self::*/@href"
        assert xpath('::text-node') == "descendant-or-self::*/text()"
        assert xpath('::attr-href') == "descendant-or-self::*/@href"
        assert xpath('p img::attr(src)') == (
            "descendant-or-self::p/descendant-or-self::*/img/@src")

    def test_series(self):
        def series(css):
            selector, = parse(':nth-child(%s)' % css)
            args = selector.parsed_tree.arguments
            try:
                return parse_series(args)
            except ValueError:
                return None

        assert series('1n+3') == (1, 3)
        assert series('1n +3') == (1, 3)
        assert series('1n + 3') == (1, 3)
        assert series('1n+ 3') == (1, 3)
        assert series('1n-3') == (1, -3)
        assert series('1n -3') == (1, -3)
        assert series('1n - 3') == (1, -3)
        assert series('1n- 3') == (1, -3)
        assert series('n-5') == (1, -5)
        assert series('odd') == (2, 1)
        assert series('even') == (2, 0)
        assert series('3n') == (3, 0)
        assert series('n') == (1, 0)
        assert series('+n') == (1, 0)
        assert series('-n') == (-1, 0)
        assert series('5') == (0, 5)
        assert series('foo') == None
        assert series('n+') == None

    def test_lang(self):
        document = etree.fromstring(XMLLANG_IDS)
        sort_key = dict(
            (el, count) for count, el in enumerate(document.getiterator())
        ).__getitem__
        css_to_xpath = GenericTranslator().css_to_xpath

        def langid(selector):
            xpath = css_to_xpath(selector)
            items = document.xpath(xpath)
            items.sort(key=sort_key)
            return [element.get('id', 'nil') for element in items]

        assert langid(':lang("EN")') == ['first', 'second', 'third', 'fourth']
        assert langid(':lang("en-us")') == ['second', 'fourth']
        assert langid(':lang(en-nz)') == ['third']
        assert langid(':lang(fr)') == ['fifth']
        assert langid(':lang(ru)') == ['sixth']
        assert langid(":lang('ZH')") == ['eighth']
        assert langid(':lang(de) :lang(zh)') == ['eighth']
        assert langid(':lang(en), :lang(zh)') == [
            'first', 'second', 'third', 'fourth', 'eighth']
        assert langid(':lang(es)') == []

    def test_select(self):
        document = etree.fromstring(HTML_IDS)
        sort_key = dict(
            (el, count) for count, el in enumerate(document.getiterator())
        ).__getitem__
        css_to_xpath = GenericTranslator().css_to_xpath
        html_css_to_xpath = HTMLTranslator().css_to_xpath

        def select_ids(selector, html_only):
            xpath = css_to_xpath(selector)
            items = document.xpath(xpath)
            if html_only:
                assert items == []
                xpath = html_css_to_xpath(selector)
                items = document.xpath(xpath)
            items.sort(key=sort_key)
            return [element.get('id', 'nil') for element in items]

        def pcss(main, *selectors, **kwargs):
            html_only = kwargs.pop('html_only', False)
            result = select_ids(main, html_only)
            for selector in selectors:
                assert select_ids(selector, html_only) == result
            return result

        all_ids = pcss('*')
        assert all_ids[:6] == [
            'html', 'nil', 'link-href', 'link-nohref', 'nil', 'outer-div']
        assert all_ids[-1:] == ['foobar-span']
        assert pcss('div') == ['outer-div', 'li-div', 'foobar-div']
        assert pcss('DIV', html_only=True) == [
            'outer-div', 'li-div', 'foobar-div']  # case-insensitive in HTML
        assert pcss('div div') == ['li-div']
        assert pcss('div, div div') == ['outer-div', 'li-div', 'foobar-div']
        assert pcss('a[name]') == ['name-anchor']
        assert pcss('a[NAme]', html_only=True) == [
            'name-anchor'] # case-insensitive in HTML:
        assert pcss('a[rel]') == ['tag-anchor', 'nofollow-anchor']
        assert pcss('a[rel="tag"]') == ['tag-anchor']
        assert pcss('a[href*="localhost"]') == ['tag-anchor']
        assert pcss('a[href*=""]') == []
        assert pcss('a[href^="http"]') == ['tag-anchor', 'nofollow-anchor']
        assert pcss('a[href^="http:"]') == ['tag-anchor']
        assert pcss('a[href^=""]') == []
        assert pcss('a[href$="org"]') == ['nofollow-anchor']
        assert pcss('a[href$=""]') == []
        assert pcss('div[foobar~="bc"]', 'div[foobar~="cde"]') == [
            'foobar-div']
        assert pcss('[foobar~="ab bc"]',
                    '[foobar~=""]', '[foobar~=" \t"]') == []
        assert pcss('div[foobar~="cd"]') == []
        assert pcss('*[lang|="En"]', '[lang|="En-us"]') == ['second-li']
        # Attribute values are case sensitive
        assert pcss('*[lang|="en"]', '[lang|="en-US"]') == []
        assert pcss('*[lang|="e"]') == []
        # ... :lang() is not.
        assert pcss(':lang("EN")', '*:lang(en-US)', html_only=True) == [
            'second-li', 'li-div']
        assert pcss(':lang("e")', html_only=True) == []
        assert pcss('li:nth-child(3)') == ['third-li']
        assert pcss('li:nth-child(10)') == []
        assert pcss('li:nth-child(2n)', 'li:nth-child(even)',
                    'li:nth-child(2n+0)') == [
            'second-li', 'fourth-li', 'sixth-li']
        assert pcss('li:nth-child(+2n+1)', 'li:nth-child(odd)') == [
            'first-li', 'third-li', 'fifth-li', 'seventh-li']
        assert pcss('li:nth-child(2n+4)') == ['fourth-li', 'sixth-li']
        # FIXME: I'm not 100% sure this is right:
        assert pcss('li:nth-child(3n+1)') == [
            'first-li', 'fourth-li', 'seventh-li']
        assert pcss('li:nth-last-child(0)') == [
            'seventh-li']
        assert pcss('li:nth-last-child(2n)', 'li:nth-last-child(even)') == [
            'second-li', 'fourth-li', 'sixth-li']
        assert pcss('li:nth-last-child(2n+2)') == ['second-li', 'fourth-li']
        assert pcss('ol:first-of-type') == ['first-ol']
        assert pcss('ol:nth-child(1)') == []
        assert pcss('ol:nth-of-type(2)') == ['second-ol']
        # FIXME: like above', '(1) or (2)?
        assert pcss('ol:nth-last-of-type(1)') == ['first-ol']
        assert pcss('span:only-child') == ['foobar-span']
        assert pcss('li div:only-child') == ['li-div']
        assert pcss('div *:only-child') == ['li-div', 'foobar-span']
        self.assertRaises(ExpressionError, pcss, 'p *:only-of-type')
        assert pcss('p:only-of-type') == ['paragraph']
        assert pcss('a:empty', 'a:EMpty') == ['name-anchor']
        assert pcss('li:empty') == [
            'third-li', 'fourth-li', 'fifth-li', 'sixth-li']
        assert pcss(':root', 'html:root') == ['html']
        assert pcss('li:root', '* :root') == []
        assert pcss('*:contains("link")', ':CONtains("link")') == [
            'html', 'nil', 'outer-div', 'tag-anchor', 'nofollow-anchor']
        assert pcss('*:contains("LInk")') == []  # case sensitive
        assert pcss('*:contains("e")') == [
            'html', 'nil', 'outer-div', 'first-ol', 'first-li',
            'paragraph', 'p-em']
        assert pcss('*:contains("E")') == []  # case-sensitive
        assert pcss('.a', '.b', '*.a', 'ol.a') == ['first-ol']
        assert pcss('.c', '*.c') == ['first-ol', 'third-li', 'fourth-li']
        assert pcss('ol *.c', 'ol li.c', 'li ~ li.c', 'ol > li.c') == [
            'third-li', 'fourth-li']
        assert pcss('#first-li', 'li#first-li', '*#first-li') == ['first-li']
        assert pcss('li div', 'li > div', 'div div') == ['li-div']
        assert pcss('div > div') == []
        assert pcss('div>.c', 'div > .c') == ['first-ol']
        assert pcss('div + div') == ['foobar-div']
        assert pcss('a ~ a') == ['tag-anchor', 'nofollow-anchor']
        assert pcss('a[rel="tag"] ~ a') == ['nofollow-anchor']
        assert pcss('ol#first-ol li:last-child') == ['seventh-li']
        assert pcss('ol#first-ol *:last-child') == ['li-div', 'seventh-li']
        assert pcss('#outer-div:first-child') == ['outer-div']
        assert pcss('#outer-div :first-child') == [
            'name-anchor', 'first-li', 'li-div', 'p-b',
            'checkbox-fieldset-disabled', 'area-href']
        assert pcss('a[href]') == ['tag-anchor', 'nofollow-anchor']
        assert pcss(':not(*)') == []
        assert pcss('a:not([href])') == ['name-anchor']
        assert pcss('ol :Not(li[class])') == [
            'first-li', 'second-li', 'li-div',
            'fifth-li', 'sixth-li', 'seventh-li']
        # Invalid characters in XPath element names, should not crash
        assert pcss(r'di\a0 v', r'div\[') == []
        assert pcss(r'[h\a0 ref]', r'[h\]ref]') == []

        # HTML-specific
        assert pcss(':link', html_only=True) == [
            'link-href', 'tag-anchor', 'nofollow-anchor', 'area-href']
        assert pcss(':visited', html_only=True) == []
        assert pcss(':enabled', html_only=True) == [
            'link-href', 'tag-anchor', 'nofollow-anchor',
            'checkbox-unchecked', 'text-checked', 'checkbox-checked',
            'area-href']
        assert pcss(':disabled', html_only=True) == [
            'checkbox-disabled', 'checkbox-disabled-checked', 'fieldset',
            'checkbox-fieldset-disabled']
        assert pcss(':checked', html_only=True) == [
            'checkbox-checked', 'checkbox-disabled-checked']

    def test_select_shakespeare(self):
        document = html.document_fromstring(HTML_SHAKESPEARE)
        body = document.xpath('//body')[0]
        css_to_xpath = GenericTranslator().css_to_xpath

        try:
            basestring_ = basestring
        except NameError:
            basestring_ = (str, bytes)

        def count(selector):
            xpath = css_to_xpath(selector)
            results = body.xpath(xpath)
            assert not isinstance(results, basestring_)
            found = set()
            for item in results:
                assert item not in found
                found.add(item)
                assert not isinstance(item, basestring_)
            return len(results)

        # Data borrowed from http://mootools.net/slickspeed/

        ## Changed from original; probably because I'm only
        ## searching the body.
        #assert count('*') == 252
        assert count('*') == 246
        assert count('div:contains(CELIA)') == 26
        assert count('div:only-child') == 22 # ?
        assert count('div:nth-child(even)') == 106
        assert count('div:nth-child(2n)') == 106
        assert count('div:nth-child(odd)') == 137
        assert count('div:nth-child(2n+1)') == 137
        assert count('div:nth-child(n)') == 243
        assert count('div:last-child') == 53
        assert count('div:first-child') == 51
        assert count('div > div') == 242
        assert count('div + div') == 190
        assert count('div ~ div') == 190
        assert count('body') == 1
        assert count('body div') == 243
        assert count('div') == 243
        assert count('div div') == 242
        assert count('div div div') == 241
        assert count('div, div, div') == 243
        assert count('div, a, span') == 243
        assert count('.dialog') == 51
        assert count('div.dialog') == 51
        assert count('div .dialog') == 51
        assert count('div.character, div.dialog') == 99
        assert count('div.direction.dialog') == 0
        assert count('div.dialog.direction') == 0
        assert count('div.dialog.scene') == 1
        assert count('div.scene.scene') == 1
        assert count('div.scene .scene') == 0
        assert count('div.direction .dialog ') == 0
        assert count('div .dialog .direction') == 4
        assert count('div.dialog .dialog .direction') == 4
        assert count('#speech5') == 1
        assert count('div#speech5') == 1
        assert count('div #speech5') == 1
        assert count('div.scene div.dialog') == 49
        assert count('div#scene1 div.dialog div') == 142
        assert count('#scene1 #speech1') == 1
        assert count('div[class]') == 103
        assert count('div[class=dialog]') == 50
        assert count('div[class^=dia]') == 51
        assert count('div[class$=log]') == 50
        assert count('div[class*=sce]') == 1
        assert count('div[class|=dialog]') == 50 # ? Seems right
        assert count('div[class!=madeup]') == 243 # ? Seems right
        assert count('div[class~=dialog]') == 51 # ? Seems right

XMLLANG_IDS = '''
<test>
  <a id="first" xml:lang="en">a</a>
  <b id="second" xml:lang="en-US">b</b>
  <c id="third" xml:lang="en-Nz">c</c>
  <d id="fourth" xml:lang="En-us">d</d>
  <e id="fifth" xml:lang="fr">e</e>
  <f id="sixth" xml:lang="ru">f</f>
  <g id="seventh" xml:lang="de">
    <h id="eighth" xml:lang="zh"/>
  </g>
</test>
'''

HTML_IDS = '''
<html id="html"><head>
  <link id="link-href" href="foo" />
  <link id="link-nohref" />
</head><body>
<div id="outer-div">
 <a id="name-anchor" name="foo"></a>
 <a id="tag-anchor" rel="tag" href="http://localhost/foo">link</a>
 <a id="nofollow-anchor" rel="nofollow" href="https://example.org">
    link</a>
 <ol id="first-ol" class="a b c">
   <li id="first-li">content</li>
   <li id="second-li" lang="En-us">
     <div id="li-div">
     </div>
   </li>
   <li id="third-li" class="ab c"></li>
   <li id="fourth-li" class="ab
c"></li>
   <li id="fifth-li"></li>
   <li id="sixth-li"></li>
   <li id="seventh-li">  </li>
 </ol>
 <p id="paragraph">
   <b id="p-b">hi</b> <em id="p-em">there</em>
   <b id="p-b2">guy</b>
   <input type="checkbox" id="checkbox-unchecked" />
   <input type="checkbox" id="checkbox-disabled" disabled="" />
   <input type="text" id="text-checked" checked="checked" />
   <input type="hidden" />
   <input type="hidden" disabled="disabled" />
   <input type="checkbox" id="checkbox-checked" checked="checked" />
   <input type="checkbox" id="checkbox-disabled-checked"
          disabled="disabled" checked="checked" />
   <fieldset id="fieldset" disabled="disabled">
     <input type="checkbox" id="checkbox-fieldset-disabled" />
     <input type="hidden" />
   </fieldset>
 </p>
 <ol id="second-ol">
 </ol>
 <map name="dummymap">
   <area shape="circle" coords="200,250,25" href="foo.html" id="area-href" />
   <area shape="default" id="area-nohref" />
 </map>
</div>
<div id="foobar-div" foobar="ab bc
cde"><span id="foobar-span"></span></div>
</body></html>
'''


HTML_SHAKESPEARE = '''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" debug="true">
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head>
<body>
	<div id="test">
	<div class="dialog">
	<h2>As You Like It</h2>
	<div id="playwright">
	  by William Shakespeare
	</div>
	<div class="dialog scene thirdClass" id="scene1">
	  <h3>ACT I, SCENE III. A room in the palace.</h3>
	  <div class="dialog">
	  <div class="direction">Enter CELIA and ROSALIND</div>
	  </div>
	  <div id="speech1" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.1">Why, cousin! why, Rosalind! Cupid have mercy! not a word?</div>
	  </div>
	  <div id="speech2" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.2">Not one to throw at a dog.</div>
	  </div>
	  <div id="speech3" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.3">No, thy words are too precious to be cast away upon</div>
	  <div id="scene1.3.4">curs; throw some of them at me; come, lame me with reasons.</div>
	  </div>
	  <div id="speech4" class="character">ROSALIND</div>
	  <div id="speech5" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.8">But is all this for your father?</div>
	  </div>
	  <div class="dialog">
	  <div id="scene1.3.5">Then there were two cousins laid up; when the one</div>
	  <div id="scene1.3.6">should be lamed with reasons and the other mad</div>
	  <div id="scene1.3.7">without any.</div>
	  </div>
	  <div id="speech6" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.9">No, some of it is for my child's father. O, how</div>
	  <div id="scene1.3.10">full of briers is this working-day world!</div>
	  </div>
	  <div id="speech7" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.11">They are but burs, cousin, thrown upon thee in</div>
	  <div id="scene1.3.12">holiday foolery: if we walk not in the trodden</div>
	  <div id="scene1.3.13">paths our very petticoats will catch them.</div>
	  </div>
	  <div id="speech8" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.14">I could shake them off my coat: these burs are in my heart.</div>
	  </div>
	  <div id="speech9" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.15">Hem them away.</div>
	  </div>
	  <div id="speech10" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.16">I would try, if I could cry 'hem' and have him.</div>
	  </div>
	  <div id="speech11" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.17">Come, come, wrestle with thy affections.</div>
	  </div>
	  <div id="speech12" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.18">O, they take the part of a better wrestler than myself!</div>
	  </div>
	  <div id="speech13" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.19">O, a good wish upon you! you will try in time, in</div>
	  <div id="scene1.3.20">despite of a fall. But, turning these jests out of</div>
	  <div id="scene1.3.21">service, let us talk in good earnest: is it</div>
	  <div id="scene1.3.22">possible, on such a sudden, you should fall into so</div>
	  <div id="scene1.3.23">strong a liking with old Sir Rowland's youngest son?</div>
	  </div>
	  <div id="speech14" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.24">The duke my father loved his father dearly.</div>
	  </div>
	  <div id="speech15" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.25">Doth it therefore ensue that you should love his son</div>
	  <div id="scene1.3.26">dearly? By this kind of chase, I should hate him,</div>
	  <div id="scene1.3.27">for my father hated his father dearly; yet I hate</div>
	  <div id="scene1.3.28">not Orlando.</div>
	  </div>
	  <div id="speech16" class="character">ROSALIND</div>
	  <div title="wtf" class="dialog">
	  <div id="scene1.3.29">No, faith, hate him not, for my sake.</div>
	  </div>
	  <div id="speech17" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.30">Why should I not? doth he not deserve well?</div>
	  </div>
	  <div id="speech18" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.31">Let me love him for that, and do you love him</div>
	  <div id="scene1.3.32">because I do. Look, here comes the duke.</div>
	  </div>
	  <div id="speech19" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.33">With his eyes full of anger.</div>
	  <div class="direction">Enter DUKE FREDERICK, with Lords</div>
	  </div>
	  <div id="speech20" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.34">Mistress, dispatch you with your safest haste</div>
	  <div id="scene1.3.35">And get you from our court.</div>
	  </div>
	  <div id="speech21" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.36">Me, uncle?</div>
	  </div>
	  <div id="speech22" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.37">You, cousin</div>
	  <div id="scene1.3.38">Within these ten days if that thou be'st found</div>
	  <div id="scene1.3.39">So near our public court as twenty miles,</div>
	  <div id="scene1.3.40">Thou diest for it.</div>
	  </div>
	  <div id="speech23" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.41">                  I do beseech your grace,</div>
	  <div id="scene1.3.42">Let me the knowledge of my fault bear with me:</div>
	  <div id="scene1.3.43">If with myself I hold intelligence</div>
	  <div id="scene1.3.44">Or have acquaintance with mine own desires,</div>
	  <div id="scene1.3.45">If that I do not dream or be not frantic,--</div>
	  <div id="scene1.3.46">As I do trust I am not--then, dear uncle,</div>
	  <div id="scene1.3.47">Never so much as in a thought unborn</div>
	  <div id="scene1.3.48">Did I offend your highness.</div>
	  </div>
	  <div id="speech24" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.49">Thus do all traitors:</div>
	  <div id="scene1.3.50">If their purgation did consist in words,</div>
	  <div id="scene1.3.51">They are as innocent as grace itself:</div>
	  <div id="scene1.3.52">Let it suffice thee that I trust thee not.</div>
	  </div>
	  <div id="speech25" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.53">Yet your mistrust cannot make me a traitor:</div>
	  <div id="scene1.3.54">Tell me whereon the likelihood depends.</div>
	  </div>
	  <div id="speech26" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.55">Thou art thy father's daughter; there's enough.</div>
	  </div>
	  <div id="speech27" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.56">So was I when your highness took his dukedom;</div>
	  <div id="scene1.3.57">So was I when your highness banish'd him:</div>
	  <div id="scene1.3.58">Treason is not inherited, my lord;</div>
	  <div id="scene1.3.59">Or, if we did derive it from our friends,</div>
	  <div id="scene1.3.60">What's that to me? my father was no traitor:</div>
	  <div id="scene1.3.61">Then, good my liege, mistake me not so much</div>
	  <div id="scene1.3.62">To think my poverty is treacherous.</div>
	  </div>
	  <div id="speech28" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.63">Dear sovereign, hear me speak.</div>
	  </div>
	  <div id="speech29" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.64">Ay, Celia; we stay'd her for your sake,</div>
	  <div id="scene1.3.65">Else had she with her father ranged along.</div>
	  </div>
	  <div id="speech30" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.66">I did not then entreat to have her stay;</div>
	  <div id="scene1.3.67">It was your pleasure and your own remorse:</div>
	  <div id="scene1.3.68">I was too young that time to value her;</div>
	  <div id="scene1.3.69">But now I know her: if she be a traitor,</div>
	  <div id="scene1.3.70">Why so am I; we still have slept together,</div>
	  <div id="scene1.3.71">Rose at an instant, learn'd, play'd, eat together,</div>
	  <div id="scene1.3.72">And wheresoever we went, like Juno's swans,</div>
	  <div id="scene1.3.73">Still we went coupled and inseparable.</div>
	  </div>
	  <div id="speech31" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.74">She is too subtle for thee; and her smoothness,</div>
	  <div id="scene1.3.75">Her very silence and her patience</div>
	  <div id="scene1.3.76">Speak to the people, and they pity her.</div>
	  <div id="scene1.3.77">Thou art a fool: she robs thee of thy name;</div>
	  <div id="scene1.3.78">And thou wilt show more bright and seem more virtuous</div>
	  <div id="scene1.3.79">When she is gone. Then open not thy lips:</div>
	  <div id="scene1.3.80">Firm and irrevocable is my doom</div>
	  <div id="scene1.3.81">Which I have pass'd upon her; she is banish'd.</div>
	  </div>
	  <div id="speech32" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.82">Pronounce that sentence then on me, my liege:</div>
	  <div id="scene1.3.83">I cannot live out of her company.</div>
	  </div>
	  <div id="speech33" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.84">You are a fool. You, niece, provide yourself:</div>
	  <div id="scene1.3.85">If you outstay the time, upon mine honour,</div>
	  <div id="scene1.3.86">And in the greatness of my word, you die.</div>
	  <div class="direction">Exeunt DUKE FREDERICK and Lords</div>
	  </div>
	  <div id="speech34" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.87">O my poor Rosalind, whither wilt thou go?</div>
	  <div id="scene1.3.88">Wilt thou change fathers? I will give thee mine.</div>
	  <div id="scene1.3.89">I charge thee, be not thou more grieved than I am.</div>
	  </div>
	  <div id="speech35" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.90">I have more cause.</div>
	  </div>
	  <div id="speech36" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.91">                  Thou hast not, cousin;</div>
	  <div id="scene1.3.92">Prithee be cheerful: know'st thou not, the duke</div>
	  <div id="scene1.3.93">Hath banish'd me, his daughter?</div>
	  </div>
	  <div id="speech37" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.94">That he hath not.</div>
	  </div>
	  <div id="speech38" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.95">No, hath not? Rosalind lacks then the love</div>
	  <div id="scene1.3.96">Which teacheth thee that thou and I am one:</div>
	  <div id="scene1.3.97">Shall we be sunder'd? shall we part, sweet girl?</div>
	  <div id="scene1.3.98">No: let my father seek another heir.</div>
	  <div id="scene1.3.99">Therefore devise with me how we may fly,</div>
	  <div id="scene1.3.100">Whither to go and what to bear with us;</div>
	  <div id="scene1.3.101">And do not seek to take your change upon you,</div>
	  <div id="scene1.3.102">To bear your griefs yourself and leave me out;</div>
	  <div id="scene1.3.103">For, by this heaven, now at our sorrows pale,</div>
	  <div id="scene1.3.104">Say what thou canst, I'll go along with thee.</div>
	  </div>
	  <div id="speech39" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.105">Why, whither shall we go?</div>
	  </div>
	  <div id="speech40" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.106">To seek my uncle in the forest of Arden.</div>
	  </div>
	  <div id="speech41" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.107">Alas, what danger will it be to us,</div>
	  <div id="scene1.3.108">Maids as we are, to travel forth so far!</div>
	  <div id="scene1.3.109">Beauty provoketh thieves sooner than gold.</div>
	  </div>
	  <div id="speech42" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.110">I'll put myself in poor and mean attire</div>
	  <div id="scene1.3.111">And with a kind of umber smirch my face;</div>
	  <div id="scene1.3.112">The like do you: so shall we pass along</div>
	  <div id="scene1.3.113">And never stir assailants.</div>
	  </div>
	  <div id="speech43" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.114">Were it not better,</div>
	  <div id="scene1.3.115">Because that I am more than common tall,</div>
	  <div id="scene1.3.116">That I did suit me all points like a man?</div>
	  <div id="scene1.3.117">A gallant curtle-axe upon my thigh,</div>
	  <div id="scene1.3.118">A boar-spear in my hand; and--in my heart</div>
	  <div id="scene1.3.119">Lie there what hidden woman's fear there will--</div>
	  <div id="scene1.3.120">We'll have a swashing and a martial outside,</div>
	  <div id="scene1.3.121">As many other mannish cowards have</div>
	  <div id="scene1.3.122">That do outface it with their semblances.</div>
	  </div>
	  <div id="speech44" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.123">What shall I call thee when thou art a man?</div>
	  </div>
	  <div id="speech45" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.124">I'll have no worse a name than Jove's own page;</div>
	  <div id="scene1.3.125">And therefore look you call me Ganymede.</div>
	  <div id="scene1.3.126">But what will you be call'd?</div>
	  </div>
	  <div id="speech46" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.127">Something that hath a reference to my state</div>
	  <div id="scene1.3.128">No longer Celia, but Aliena.</div>
	  </div>
	  <div id="speech47" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.129">But, cousin, what if we assay'd to steal</div>
	  <div id="scene1.3.130">The clownish fool out of your father's court?</div>
	  <div id="scene1.3.131">Would he not be a comfort to our travel?</div>
	  </div>
	  <div id="speech48" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.132">He'll go along o'er the wide world with me;</div>
	  <div id="scene1.3.133">Leave me alone to woo him. Let's away,</div>
	  <div id="scene1.3.134">And get our jewels and our wealth together,</div>
	  <div id="scene1.3.135">Devise the fittest time and safest way</div>
	  <div id="scene1.3.136">To hide us from pursuit that will be made</div>
	  <div id="scene1.3.137">After my flight. Now go we in content</div>
	  <div id="scene1.3.138">To liberty and not to banishment.</div>
	  <div class="direction">Exeunt</div>
	  </div>
	</div>
	</div>
</div>
</body>
</html>
'''


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = xpath
# coding: utf8
"""
    cssselect.xpath
    ===============

    Translation of parsed CSS selectors to XPath expressions.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import sys
import re

from cssselect.parser import parse, parse_series, SelectorError


if sys.version_info[0] < 3:
    _basestring = basestring
    _unicode = unicode
else:
    _basestring = str
    _unicode = str


def _unicode_safe_getattr(obj, name, default=None):
    # getattr() with a non-ASCII name fails on Python 2.x
    name = name.encode('ascii', 'replace').decode('ascii')
    return getattr(obj, name, default)


class ExpressionError(SelectorError, RuntimeError):
    """Unknown or unsupported selector (eg. pseudo-class)."""


#### XPath Helpers

class XPathExpr(object):

    def __init__(self, path='', element='*', condition='', star_prefix=False):
        self.path = path
        self.element = element
        self.condition = condition

    def __str__(self):
        path =  _unicode(self.path) + _unicode(self.element)
        if self.condition:
            path += '[%s]' % self.condition
        return path

    def __repr__(self):
        return '%s[%s]' % (self.__class__.__name__, self)

    def add_condition(self, condition):
        if self.condition:
            self.condition = '%s and (%s)' % (self.condition, condition)
        else:
            self.condition = condition
        return self

    def add_name_test(self):
        if self.element == '*':
            # We weren't doing a test anyway
            return
        self.add_condition(
            "name() = %s" % GenericTranslator.xpath_literal(self.element))
        self.element = '*'

    def add_star_prefix(self):
        """
        Append '*/' to the path to keep the context constrained
        to a single parent.
        """
        self.path += '*/'

    def join(self, combiner, other):
        path = _unicode(self) + combiner
        # Any "star prefix" is redundant when joining.
        if other.path != '*/':
            path += other.path
        self.path = path
        self.element = other.element
        self.condition = other.condition
        return self


split_at_single_quotes = re.compile("('+)").split

# The spec is actually more permissive than that, but don’t bother.
# This is just for the fast path.
# http://www.w3.org/TR/REC-xml/#NT-NameStartChar
is_safe_name = re.compile('^[a-zA-Z_][a-zA-Z0-9_.-]*$').match

# Test that the string is not empty and does not contain whitespace
is_non_whitespace = re.compile(r'^[^ \t\r\n\f]+$').match


#### Translation

class GenericTranslator(object):
    """
    Translator for "generic" XML documents.

    Everything is case-sensitive, no assumption is made on the meaning
    of element names and attribute names.

    """
    
    ####
    ####  HERE BE DRAGONS
    ####
    ####  You are welcome to hook into this to change some behavior,
    ####  but do so at your own risks.
    ####  Until is has recieved a lot more work and review,
    ####  I reserve the right to change this API in backward-incompatible ways
    ####  with any minor version of cssselect.
    ####  See https://github.com/SimonSapin/cssselect/pull/22
    ####  -- Simon Sapin.
    ####

    combinator_mapping = {
        ' ': 'descendant',
        '>': 'child',
        '+': 'direct_adjacent',
        '~': 'indirect_adjacent',
    }

    attribute_operator_mapping = {
       'exists': 'exists',
        '=': 'equals',
        '~=': 'includes',
        '|=': 'dashmatch',
        '^=': 'prefixmatch',
        '$=': 'suffixmatch',
        '*=': 'substringmatch',
        '!=': 'different',  # XXX Not in Level 3 but meh
    }

    #: The attribute used for ID selectors depends on the document language:
    #: http://www.w3.org/TR/selectors/#id-selectors
    id_attribute = 'id'

    #: The attribute used for ``:lang()`` depends on the document language:
    #: http://www.w3.org/TR/selectors/#lang-pseudo
    lang_attribute = 'xml:lang'

    #: The case sensitivity of document language element names,
    #: attribute names, and attribute values in selectors depends
    #: on the document language.
    #: http://www.w3.org/TR/selectors/#casesens
    #:
    #: When a document language defines one of these as case-insensitive,
    #: cssselect assumes that the document parser makes the parsed values
    #: lower-case. Making the selector lower-case too makes the comparaison
    #: case-insensitive.
    #:
    #: In HTML, element names and attributes names (but not attribute values)
    #: are case-insensitive. All of lxml.html, html5lib, BeautifulSoup4
    #: and HTMLParser make them lower-case in their parse result, so
    #: the assumption holds.
    lower_case_element_names = False
    lower_case_attribute_names = False
    lower_case_attribute_values = False

    # class used to represent and xpath expression
    xpathexpr_cls = XPathExpr

    def css_to_xpath(self, css, prefix='descendant-or-self::'):
        """Translate a *group of selectors* to XPath.

        Pseudo-elements are not supported here since XPath only knows
        about "real" elements.

        :param css:
            A *group of selectors* as an Unicode string.
        :param prefix:
            This string is prepended to the XPath expression for each selector.
            The default makes selectors scoped to the context node’s subtree.
        :raises:
            :class:`SelectorSyntaxError` on invalid selectors,
            :class:`ExpressionError` on unknown/unsupported selectors,
            including pseudo-elements.
        :returns:
            The equivalent XPath 1.0 expression as an Unicode string.

        """
        return ' | '.join(self.selector_to_xpath(selector, prefix,
                                                 translate_pseudo_elements=True)
                          for selector in parse(css))

    def selector_to_xpath(self, selector, prefix='descendant-or-self::',
                          translate_pseudo_elements=False):
        """Translate a parsed selector to XPath.


        :param selector:
            A parsed :class:`Selector` object.
        :param prefix:
            This string is prepended to the resulting XPath expression.
            The default makes selectors scoped to the context node’s subtree.
        :param translate_pseudo_elements:
            Unless this is set to ``True`` (as :meth:`css_to_xpath` does),
            the :attr:`~Selector.pseudo_element` attribute of the selector
            is ignored.
            It is the caller's responsibility to reject selectors
            with pseudo-elements, or to account for them somehow.
        :raises:
            :class:`ExpressionError` on unknown/unsupported selectors.
        :returns:
            The equivalent XPath 1.0 expression as an Unicode string.

        """
        tree = getattr(selector, 'parsed_tree', None)
        if not tree:
            raise TypeError('Expected a parsed selector, got %r' % (selector,))
        xpath = self.xpath(tree)
        assert isinstance(xpath, self.xpathexpr_cls)  # help debug a missing 'return'
        if translate_pseudo_elements and selector.pseudo_element:
            xpath = self.xpath_pseudo_element(xpath, selector.pseudo_element)
        return (prefix or '') + _unicode(xpath)

    def xpath_pseudo_element(self, xpath, pseudo_element):
        """Translate a pseudo-element.

        Defaults to not supporting pseudo-elements at all,
        but can be overridden by sub-classes.

        """
        raise ExpressionError('Pseudo-elements are not supported.')

    @staticmethod
    def xpath_literal(s):
        s = _unicode(s)
        if "'" not in s:
            s = "'%s'" % s
        elif '"' not in s:
            s = '"%s"' % s
        else:
            s = "concat(%s)" % ','.join([
                (("'" in part) and '"%s"' or "'%s'") % part
                for part in split_at_single_quotes(s) if part
                ])
        return s

    def xpath(self, parsed_selector):
        """Translate any parsed selector object."""
        type_name = type(parsed_selector).__name__
        method = getattr(self, 'xpath_%s' % type_name.lower(), None)
        if method is None:
            raise ExpressionError('%s is not supported.' %  type_name)
        return method(parsed_selector)


    # Dispatched by parsed object type

    def xpath_combinedselector(self, combined):
        """Translate a combined selector."""
        combinator = self.combinator_mapping[combined.combinator]
        method = getattr(self, 'xpath_%s_combinator' % combinator)
        return method(self.xpath(combined.selector),
                      self.xpath(combined.subselector))

    def xpath_negation(self, negation):
        xpath = self.xpath(negation.selector)
        sub_xpath = self.xpath(negation.subselector)
        sub_xpath.add_name_test()
        if sub_xpath.condition:
            return xpath.add_condition('not(%s)' % sub_xpath.condition)
        else:
            return xpath.add_condition('0')

    def xpath_function(self, function):
        """Translate a functional pseudo-class."""
        method = 'xpath_%s_function' % function.name.replace('-', '_')
        method = _unicode_safe_getattr(self, method, None)
        if not method:
            raise ExpressionError(
                "The pseudo-class :%s() is unknown" % function.name)
        return method(self.xpath(function.selector), function)

    def xpath_pseudo(self, pseudo):
        """Translate a pseudo-class."""
        method = 'xpath_%s_pseudo' % pseudo.ident.replace('-', '_')
        method = _unicode_safe_getattr(self, method, None)
        if not method:
            # TODO: better error message for pseudo-elements?
            raise ExpressionError(
                "The pseudo-class :%s is unknown" % pseudo.ident)
        return method(self.xpath(pseudo.selector))


    def xpath_attrib(self, selector):
        """Translate an attribute selector."""
        operator = self.attribute_operator_mapping[selector.operator]
        method = getattr(self, 'xpath_attrib_%s' % operator)
        if self.lower_case_attribute_names:
            name = selector.attrib.lower()
        else:
            name = selector.attrib
        safe = is_safe_name(name)
        if selector.namespace:
            name = '%s:%s' % (selector.namespace, name)
            safe = safe and is_safe_name(selector.namespace)
        if safe:
            attrib = '@' + name
        else:
            attrib = 'attribute::*[name() = %s]' % self.xpath_literal(name)
        if self.lower_case_attribute_values:
            value = selector.value.lower()
        else:
            value = selector.value
        return method(self.xpath(selector.selector), attrib, value)

    def xpath_class(self, class_selector):
        """Translate a class selector."""
        # .foo is defined as [class~=foo] in the spec.
        xpath = self.xpath(class_selector.selector)
        return self.xpath_attrib_includes(
            xpath, '@class', class_selector.class_name)

    def xpath_hash(self, id_selector):
        """Translate an ID selector."""
        xpath = self.xpath(id_selector.selector)
        return self.xpath_attrib_equals(xpath, '@id', id_selector.id)

    def xpath_element(self, selector):
        """Translate a type or universal selector."""
        element = selector.element
        if not element:
            element = '*'
            safe = True
        else:
            safe = is_safe_name(element)
            if self.lower_case_element_names:
                element = element.lower()
        if selector.namespace:
            # Namespace prefixes are case-sensitive.
            # http://www.w3.org/TR/css3-namespace/#prefixes
            element = '%s:%s' % (selector.namespace, element)
            safe = safe and is_safe_name(selector.namespace)
        xpath = self.xpathexpr_cls(element=element)
        if not safe:
            xpath.add_name_test()
        return xpath


    # CombinedSelector: dispatch by combinator

    def xpath_descendant_combinator(self, left, right):
        """right is a child, grand-child or further descendant of left"""
        return left.join('/descendant-or-self::*/', right)

    def xpath_child_combinator(self, left, right):
        """right is an immediate child of left"""
        return left.join('/', right)

    def xpath_direct_adjacent_combinator(self, left, right):
        """right is a sibling immediately after left"""
        xpath = left.join('/following-sibling::', right)
        xpath.add_name_test()
        return xpath.add_condition('position() = 1')

    def xpath_indirect_adjacent_combinator(self, left, right):
        """right is a sibling after left, immediately or not"""
        return left.join('/following-sibling::', right)


    # Function: dispatch by function/pseudo-class name

    def xpath_nth_child_function(self, xpath, function, last=False,
                                 add_name_test=True):
        try:
            a, b = parse_series(function.arguments)
        except ValueError:
            raise ExpressionError("Invalid series: '%r'" % function.arguments)
        if add_name_test:
            xpath.add_name_test()
        xpath.add_star_prefix()
        if a == 0:
            if last:
                b = 'last() - %s' % b
            return xpath.add_condition('position() = %s' % b)
        if last:
            # FIXME: I'm not sure if this is right
            a = -a
            b = -b
        if b > 0:
            b_neg = str(-b)
        else:
            b_neg = '+%s' % (-b)
        if a != 1:
            expr = ['(position() %s) mod %s = 0' % (b_neg, a)]
        else:
            expr = []
        if b >= 0:
            expr.append('position() >= %s' % b)
        elif b < 0 and last:
            expr.append('position() < (last() %s)' % b)
        expr = ' and '.join(expr)
        if expr:
            xpath.add_condition(expr)
        return xpath
        # FIXME: handle an+b, odd, even
        # an+b means every-a, plus b, e.g., 2n+1 means odd
        # 0n+b means b
        # n+0 means a=1, i.e., all elements
        # an means every a elements, i.e., 2n means even
        # -n means -1n
        # -1n+6 means elements 6 and previous

    def xpath_nth_last_child_function(self, xpath, function):
        return self.xpath_nth_child_function(xpath, function, last=True)

    def xpath_nth_of_type_function(self, xpath, function):
        if xpath.element == '*':
            raise ExpressionError(
                "*:nth-of-type() is not implemented")
        return self.xpath_nth_child_function(xpath, function,
                                             add_name_test=False)

    def xpath_nth_last_of_type_function(self, xpath, function):
        if xpath.element == '*':
            raise ExpressionError(
                "*:nth-of-type() is not implemented")
        return self.xpath_nth_child_function(xpath, function, last=True,
                                             add_name_test=False)

    def xpath_contains_function(self, xpath, function):
        # Defined there, removed in later drafts:
        # http://www.w3.org/TR/2001/CR-css3-selectors-20011113/#content-selectors
        if function.argument_types() not in (['STRING'], ['IDENT']):
            raise ExpressionError(
                "Expected a single string or ident for :contains(), got %r"
                % function.arguments)
        value = function.arguments[0].value
        return xpath.add_condition(
            'contains(., %s)' % self.xpath_literal(value))

    def xpath_lang_function(self, xpath, function):
        if function.argument_types() not in (['STRING'], ['IDENT']):
            raise ExpressionError(
                "Expected a single string or ident for :lang(), got %r"
                % function.arguments)
        value = function.arguments[0].value
        return xpath.add_condition(
            "lang(%s)" % (self.xpath_literal(value)))


    # Pseudo: dispatch by pseudo-class name

    def xpath_root_pseudo(self, xpath):
        return xpath.add_condition("not(parent::*)")

    def xpath_first_child_pseudo(self, xpath):
        xpath.add_star_prefix()
        xpath.add_name_test()
        return xpath.add_condition('position() = 1')

    def xpath_last_child_pseudo(self, xpath):
        xpath.add_star_prefix()
        xpath.add_name_test()
        return xpath.add_condition('position() = last()')

    def xpath_first_of_type_pseudo(self, xpath):
        if xpath.element == '*':
            raise ExpressionError(
                "*:first-of-type is not implemented")
        xpath.add_star_prefix()
        return xpath.add_condition('position() = 1')

    def xpath_last_of_type_pseudo(self, xpath):
        if xpath.element == '*':
            raise ExpressionError(
                "*:last-of-type is not implemented")
        xpath.add_star_prefix()
        return xpath.add_condition('position() = last()')

    def xpath_only_child_pseudo(self, xpath):
        xpath.add_name_test()
        xpath.add_star_prefix()
        return xpath.add_condition('last() = 1')

    def xpath_only_of_type_pseudo(self, xpath):
        if xpath.element == '*':
            raise ExpressionError(
                "*:only-of-type is not implemented")
        return xpath.add_condition('last() = 1')

    def xpath_empty_pseudo(self, xpath):
        return xpath.add_condition("not(*) and not(string-length())")

    def pseudo_never_matches(self, xpath):
        """Common implementation for pseudo-classes that never match."""
        return xpath.add_condition("0")

    xpath_link_pseudo = pseudo_never_matches
    xpath_visited_pseudo = pseudo_never_matches
    xpath_hover_pseudo = pseudo_never_matches
    xpath_active_pseudo = pseudo_never_matches
    xpath_focus_pseudo = pseudo_never_matches
    xpath_target_pseudo = pseudo_never_matches
    xpath_enabled_pseudo = pseudo_never_matches
    xpath_disabled_pseudo = pseudo_never_matches
    xpath_checked_pseudo = pseudo_never_matches

    # Attrib: dispatch by attribute operator

    def xpath_attrib_exists(self, xpath, name, value):
        assert not value
        xpath.add_condition(name)
        return xpath

    def xpath_attrib_equals(self, xpath, name, value):
        xpath.add_condition('%s = %s' % (name, self.xpath_literal(value)))
        return xpath

    def xpath_attrib_different(self, xpath, name, value):
        # FIXME: this seems like a weird hack...
        if value:
            xpath.add_condition('not(%s) or %s != %s'
                                % (name, name, self.xpath_literal(value)))
        else:
            xpath.add_condition('%s != %s'
                                % (name, self.xpath_literal(value)))
        return xpath

    def xpath_attrib_includes(self, xpath, name, value):
        if is_non_whitespace(value):
            xpath.add_condition(
                "%s and contains(concat(' ', normalize-space(%s), ' '), %s)"
                % (name, name, self.xpath_literal(' '+value+' ')))
        else:
            xpath.add_condition('0')
        return xpath

    def xpath_attrib_dashmatch(self, xpath, name, value):
        # Weird, but true...
        xpath.add_condition('%s and (%s = %s or starts-with(%s, %s))' % (
            name,
            name, self.xpath_literal(value),
            name, self.xpath_literal(value + '-')))
        return xpath

    def xpath_attrib_prefixmatch(self, xpath, name, value):
        if value:
            xpath.add_condition('%s and starts-with(%s, %s)' % (
                name, name, self.xpath_literal(value)))
        else:
            xpath.add_condition('0')
        return xpath

    def xpath_attrib_suffixmatch(self, xpath, name, value):
        if value:
            # Oddly there is a starts-with in XPath 1.0, but not ends-with
            xpath.add_condition(
                '%s and substring(%s, string-length(%s)-%s) = %s'
                % (name, name, name, len(value)-1, self.xpath_literal(value)))
        else:
            xpath.add_condition('0')
        return xpath

    def xpath_attrib_substringmatch(self, xpath, name, value):
        if value:
            # Attribute selectors are case sensitive
            xpath.add_condition('%s and contains(%s, %s)' % (
                name, name, self.xpath_literal(value)))
        else:
            xpath.add_condition('0')
        return xpath


class HTMLTranslator(GenericTranslator):
    """
    Translator for (X)HTML documents.

    Has a more useful implementation of some pseudo-classes based on
    HTML-specific element names and attribute names, as described in
    the `HTML5 specification`_. It assumes no-quirks mode.
    The API is the same as :class:`GenericTranslator`.

    .. _HTML5 specification: http://www.w3.org/TR/html5/links.html#selectors

    :param xhtml:
        If false (the default), element names and attribute names
        are case-insensitive.

    """

    lang_attribute = 'lang'

    def __init__(self, xhtml=False):
        self.xhtml = xhtml  # Might be useful for sub-classes?
        if not xhtml:
            # See their definition in GenericTranslator.
            self.lower_case_element_names = True
            self.lower_case_attribute_names = True

    def xpath_checked_pseudo(self, xpath):
        # FIXME: is this really all the elements?
        return xpath.add_condition(
            "(@selected and name(.) = 'option') or "
            "(@checked "
                "and (name(.) = 'input' or name(.) = 'command')"
                "and (@type = 'checkbox' or @type = 'radio'))")

    def xpath_lang_function(self, xpath, function):
        if function.argument_types() not in (['STRING'], ['IDENT']):
            raise ExpressionError(
                "Expected a single string or ident for :lang(), got %r"
                % function.arguments)
        value = function.arguments[0].value
        return xpath.add_condition(
            "ancestor-or-self::*[@lang][1][starts-with(concat("
                # XPath 1.0 has no lower-case function...
                "translate(@%s, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                               "'abcdefghijklmnopqrstuvwxyz'), "
                "'-'), %s)]"
            % (self.lang_attribute, self.xpath_literal(value.lower() + '-')))

    def xpath_link_pseudo(self, xpath):
        return xpath.add_condition("@href and "
            "(name(.) = 'a' or name(.) = 'link' or name(.) = 'area')")

    # Links are never visited, the implementation for :visited is the same
    # as in GenericTranslator

    def xpath_disabled_pseudo(self, xpath):
        # http://www.w3.org/TR/html5/section-index.html#attributes-1
        return xpath.add_condition('''
        (
            @disabled and
            (
                (name(.) = 'input' and @type != 'hidden') or
                name(.) = 'button' or
                name(.) = 'select' or
                name(.) = 'textarea' or
                name(.) = 'command' or
                name(.) = 'fieldset' or
                name(.) = 'optgroup' or
                name(.) = 'option'
            )
        ) or (
            (
                (name(.) = 'input' and @type != 'hidden') or
                name(.) = 'button' or
                name(.) = 'select' or
                name(.) = 'textarea'
            )
            and ancestor::fieldset[@disabled]
        )
        ''')
        # FIXME: in the second half, add "and is not a descendant of that
        # fieldset element's first legend element child, if any."

    def xpath_enabled_pseudo(self, xpath):
        # http://www.w3.org/TR/html5/section-index.html#attributes-1
        return xpath.add_condition('''
        (
            @href and (
                name(.) = 'a' or
                name(.) = 'link' or
                name(.) = 'area'
            )
        ) or (
            (
                name(.) = 'command' or
                name(.) = 'fieldset' or
                name(.) = 'optgroup'
            )
            and not(@disabled)
        ) or (
            (
                (name(.) = 'input' and @type != 'hidden') or
                name(.) = 'button' or
                name(.) = 'select' or
                name(.) = 'textarea' or
                name(.) = 'keygen'
            )
            and not (@disabled or ancestor::fieldset[@disabled])
        ) or (
            name(.) = 'option' and not(
                @disabled or ancestor::optgroup[@disabled]
            )
        )
        ''')
        # FIXME: ... or "li elements that are children of menu elements,
        # and that have a child element that defines a command, if the first
        # such element's Disabled State facet is false (not disabled)".
        # FIXME: after ancestor::fieldset[@disabled], add "and is not a
        # descendant of that fieldset element's first legend element child,
        # if any."

########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# cssselect documentation build configuration file, created by
# sphinx-quickstart on Tue Mar 27 14:20:34 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, re

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
              'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'cssselect'
copyright = '2012, Simon Sapin'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
init_py = open(os.path.join(os.path.dirname(__file__),
                            '..', 'cssselect', '__init__.py')).read()
release = re.search("VERSION = '([^']+)'", init_py).group(1)
# The short X.Y version.
version = release.rstrip('dev')

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'agogo'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'cssselectdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'cssselect.tex', 'cssselect Documentation',
   'Simon Sapin', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cssselect', 'cssselect Documentation',
     ['Simon Sapin'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'cssselect', 'cssselect Documentation',
   'Simon Sapin', 'cssselect', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
