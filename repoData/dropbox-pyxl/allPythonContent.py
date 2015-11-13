__FILENAME__ = finish_install
import shutil
from distutils.sysconfig import get_python_lib

python_lib = get_python_lib()
shutil.copy('pyxl.pth', python_lib)

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

# We want a way to generate non-colliding 'pyxl<num>' ids for elements, so we're
# using a non-cryptographically secure random number generator. We want it to be
# insecure because these aren't being used for anything cryptographic and it's
# much faster (2x). We're also not using NumPy (which is even faster) because
# it's a difficult dependency to fulfill purely to generate random numbers.
import random
import sys

from pyxl.utils import escape

class PyxlException(Exception):
    pass

class x_base_metaclass(type):
    def __init__(self, name, parents, attrs):
        super(x_base_metaclass, self).__init__(name, parents, attrs)
        x_base_parents = [parent for parent in parents if hasattr(parent, '__attrs__')]
        parent_attrs = x_base_parents[0].__attrs__ if len(x_base_parents) else {}
        self_attrs = self.__dict__.get('__attrs__', {})

        # Dont allow '_' in attr names
        for attr_name in self_attrs:
            assert '_' not in attr_name, (
                "%s: '_' not allowed in attr names, use '-' instead" % attr_name)

        combined_attrs = dict(parent_attrs)
        combined_attrs.update(self_attrs)
        setattr(self, '__attrs__', combined_attrs)
        setattr(self, '__tag__', name[2:])

class x_base(object):

    __metaclass__ = x_base_metaclass
    __attrs__ = {
        # HTML attributes
        'accesskey': unicode,
        'class': unicode,
        'dir': unicode,
        'id': unicode,
        'lang': unicode,
        'maxlength': unicode,
        'role': unicode,
        'style': unicode,
        'tabindex': int,
        'title': unicode,
        'xml:lang': unicode,

        # JS attributes
        'onabort': unicode,
        'onblur': unicode,
        'onchange': unicode,
        'onclick': unicode,
        'ondblclick': unicode,
        'onerror': unicode,
        'onfocus': unicode,
        'onkeydown': unicode,
        'onkeypress': unicode,
        'onkeyup': unicode,
        'onload': unicode,
        'onmousedown': unicode,
        'onmouseenter': unicode,
        'onmouseleave': unicode,
        'onmousemove': unicode,
        'onmouseout': unicode,
        'onmouseover': unicode,
        'onmouseup': unicode,
        'onreset': unicode,
        'onresize': unicode,
        'onselect': unicode,
        'onsubmit': unicode,
        'onunload': unicode,
        }

    def __init__(self, **kwargs):
        self.__attributes__ = {}
        self.__children__ = []

        for name, value in kwargs.iteritems():
            self.set_attr(x_base._fix_attribute_name(name), value)

    def __call__(self, *children):
        self.append_children(children)
        return self

    def get_id(self):
        eid = self.attr('id')
        if not eid:
            eid = 'pyxl%d' % random.randint(0, sys.maxint)
            self.set_attr('id', eid)
        return eid

    def children(self, selector=None, exclude=False):
        if not selector:
            return self.__children__

        # filter by class
        if selector[0] == '.':
            select = lambda x: selector[1:] in x.get_class() 

        # filter by id
        elif selector[0] == '#':
            select = lambda x: selector[1:] == x.get_id()

        # filter by tag name
        else:
            select = lambda x: x.__class__.__name__ == ('x_%s' % selector)

        if exclude:
            func = lambda x: not select(x)
        else:
            func = select

        return filter(func, self.__children__)

    def append(self, child):
        if type(child) in (list, tuple) or hasattr(child, '__iter__'):
            self.__children__.extend(c for c in child if c is not None and c is not False)
        elif child is not None and child is not False:
            self.__children__.append(child)

    def prepend(self, child):
        if child is not None and child is not False:
            self.__children__.insert(0, child)

    def __getattr__(self, name):
        return self.attr(name.replace('_', '-'))

    def attr(self, name, default=None):
        # this check is fairly expensive (~8% of cost)
        if not self.allows_attribute(name):
            raise PyxlException('<%s> has no attr named "%s"' % (self.__tag__, name))

        value = self.__attributes__.get(name)

        if value is not None:
            return value

        attr_type = self.__attrs__.get(name, unicode)
        if type(attr_type) == list:
            if not attr_type:
                raise PyxlException('Invalid attribute definition')

            if None in attr_type[1:]:
                raise PyxlException('None must be the first, default value')

            return attr_type[0]

        return default

    def transfer_attributes(self, element):
        for name, value in self.__attributes__.iteritems():
            if element.allows_attribute(name) and element.attr(name) is None:
                element.set_attr(name, value)

    def set_attr(self, name, value):
        # this check is fairly expensive (~8% of cost)
        if not self.allows_attribute(name):
            raise PyxlException('<%s> has no attr named "%s"' % (self.__tag__, name))

        if value is not None:
            attr_type = self.__attrs__.get(name, unicode)

            if type(attr_type) == list:
                # support for enum values in pyxl attributes
                values_enum = attr_type
                assert values_enum, 'Invalid attribute definition'

                if value not in values_enum:
                    msg = '%s: %s: incorrect value "%s" for "%s". Expecting enum value %s' % (
                        self.__tag__, self.__class__.__name__, value, name, values_enum)
                    raise PyxlException(msg)

            else:
                try:
                    # Validate type of attr and cast to correct type if possible
                    value = value if isinstance(value, attr_type) else attr_type(value)
                except Exception:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    msg = '%s: %s: incorrect type for "%s". expected %s, got %s' % (
                        self.__tag__, self.__class__.__name__, name, attr_type, type(value))
                    exception = PyxlException(msg)
                    raise exception, None, exc_tb

            self.__attributes__[name] = value

        elif name in self.__attributes__:
            del self.__attributes__[name]

    def get_class(self):
        return self.attr('class', '')

    def add_class(self, xclass):
        if not xclass: return
        current_class = self.attr('class')
        if current_class: current_class += ' ' + xclass
        else: current_class = xclass
        self.set_attr('class', current_class)

    def append_children(self, children):
        for child in children:
            self.append(child)

    def attributes(self):
        return self.__attributes__

    def set_attributes(self, attrs_dict):
        for name, value in attrs_dict.iteritems():
            self.set_attr(name, value)

    def allows_attribute(self, name):
        return (name in self.__attrs__ or name.startswith('data-') or name.startswith('aria-'))

    def to_string(self):
        l = []
        self._to_list(l)
        return u''.join(l)

    def _to_list(self, l):
        raise NotImplementedError()

    def __str__(self):
        return self.to_string()

    def __unicode__(self):
        return self.to_string()

    @staticmethod
    def _render_child_to_list(child, l):
        if isinstance(child, x_base): child._to_list(l)
        elif child is not None: l.append(escape(child))

    @staticmethod
    def _fix_attribute_name(name):
        if name == 'xclass': return 'class'
        if name == 'xfor': return 'for'
        return name.replace('_', '-').replace('COLON', ':')

########NEW FILE########
__FILENAME__ = browser_hacks
#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from pyxl.base import x_base
from pyxl.utils import escape

class x_cond_comment(x_base):
    __attrs__ = {
        'cond': unicode,
        }

    def _to_list(self, l):
        # allow '&', escape everything else from cond
        cond = self.__attributes__.get('cond', '')
        cond = '&'.join(map(escape, cond.split('&')))

        l.extend((u'<!--[if ', cond, u']>'))

        for child in self.__children__:
            x_base._render_child_to_list(child, l)

        l.append(u'<![endif]-->')

class x_cond_noncomment(x_base):
    ''' This is a conditional comment where browsers which don't support conditional comments
        will parse the children by default. '''
    __attrs__ = {
        'cond': unicode,
        }

    def _to_list(self, l):
        # allow '&', escape everything else from cond
        cond = self.__attributes__.get('cond', '')
        cond = '&'.join(map(escape, cond.split('&')))

        l.extend((u'<!--[if ', cond, u']><!-->'))

        for child in self.__children__:
            x_base._render_child_to_list(child, l)

        l.append(u'<!--<![endif]-->')


########NEW FILE########
__FILENAME__ = html_tokenizer
"""
A naive but strict HTML tokenizer. Based directly on
http://www.w3.org/TR/2011/WD-html5-20110525/tokenization.html

In the ATTRIBUTE_VALUE and BEFORE_ATTRIBUTE_VALUE states, python tokens are accepted.
"""

import sys
from collections import OrderedDict

class State(object):
    DATA = 1
    # unused states: charrefs, RCDATA, script, RAWTEXT, PLAINTEXT
    TAG_OPEN = 7
    END_TAG_OPEN = 8
    TAG_NAME = 9
    # unused states: RCDATA, RAWTEXT, script
    BEFORE_ATTRIBUTE_NAME = 34
    ATTRIBUTE_NAME = 35
    AFTER_ATTRIBUTE_NAME = 36
    BEFORE_ATTRIBUTE_VALUE = 37
    ATTRIBUTE_VALUE_DOUBLE_QUOTED = 38
    ATTRIBUTE_VALUE_SINGLE_QUOTED = 39
    ATTRIBUTE_VALUE_UNQUOTED = 40
    # unused state: CHARREF_IN_ATTRIBUTE_VALUE = 41
    AFTER_ATTRIBUTE_VALUE = 42
    SELF_CLOSING_START_TAG = 43
    # unused state: BOGUS_COMMENT_STATE = 44
    MARKUP_DECLARATION_OPEN = 45
    COMMENT_START = 46
    COMMENT_START_DASH = 47
    COMMENT = 48
    COMMENT_END_DASH = 49
    COMMENT_END = 50
    # unused state: COMMENT_END_BANG = 51
    DOCTYPE = 52
    DOCTYPE_CONTENTS = 53 # Gross oversimplification. Not to spec.
    # unused states: doctypes
    CDATA_SECTION = 68

    @classmethod
    def state_name(cls, state_val):
        for k, v in cls.__dict__.iteritems():
            if v == state_val:
                return k
        assert False, "impossible state value %r!" % state_val

class Tag(object):
    def __init__(self):
        self.tag_name = None
        self.attrs = OrderedDict()
        self.endtag = False
        self.startendtag = False

class ParseError(Exception):
    pass

class BadCharError(Exception):
    def __init__(self, state, char):
        super(BadCharError, self).__init__("unexpected character %r in state %r" %
                                           (char, State.state_name(state)))

class Unimplemented(Exception):
    pass

class HTMLTokenizer(object):

    def __init__(self):
        self.state = State.DATA

        # attribute_value is a list, where each element is either a string or a list of python
        # tokens.

        self.data = ""
        self.tag = None
        self.tag_name = None
        self.attribute_name = None
        self.attribute_value = None
        self.markup_declaration_buffer = None

    def handle_data(self, data):
        assert False, "subclass should override"

    def handle_starttag(self, tag_name, attrs):
        assert False, "subclass should override"

    def handle_startendtag(self, tag_name, attrs):
        assert False, "subclass should override"

    def handle_endtag(self, tag_name):
        assert False, "subclass should override"

    def handle_comment(self, tag_name):
        assert False, "subclass should override"

    def handle_doctype(self, data):
        assert False, "subclass should override"

    def handle_cdata(self, tag_name):
        assert False, "subclass should override"

    def emit_data(self):
        self.handle_data(self.data)
        self.data = ""

    def emit_tag(self):
        if self.tag.startendtag and self.tag.endtag:
            raise ParseError("both startendtag and endtag!?")
        if self.tag.startendtag:
            self.handle_startendtag(self.tag.tag_name, self.tag.attrs)
        elif self.tag.endtag:
            self.handle_endtag(self.tag.tag_name)
        else:
            self.handle_starttag(self.tag.tag_name, self.tag.attrs)

    def emit_comment(self):
        self.handle_comment(self.data)
        self.data = ""

    def emit_doctype(self):
        self.handle_doctype(self.data)
        self.data = ""

    def emit_cdata(self):
        self.handle_cdata(self.data)
        self.data = ""

    def got_attribute(self):
        if self.attribute_name in self.tag.attrs:
            raise ParseError("repeat attribute name %r" % self.attribute_name)
        self.tag.attrs[self.attribute_name] = self.attribute_value
        self.attribute_name = None
        self.attribute_value = None

    def add_data_char(self, build, c):
        """ For adding a new character to e.g. an attribute value """
        if len(build) and type(build[-1]) == str:
            build[-1] += c
        else:
            build.append(c)

    def feed(self, c):
        if self.state == State.DATA:
            if c == '<':
                self.emit_data()
                self.state = State.TAG_OPEN
            # Pass through; it's the browser's problem to understand these.
            #elif c == '&':
            #    raise Unimplemented
            else:
                self.data += c

        elif self.state == State.TAG_OPEN:
            self.tag = Tag()
            if c == '!':
                self.markup_declaration_buffer = ""
                self.state = State.MARKUP_DECLARATION_OPEN
            elif c == '/':
                self.state = State.END_TAG_OPEN
            elif c.isalpha():
                self.tag.tag_name = c
                self.state = State.TAG_NAME
            else:
                raise BadCharError(self.state, c)

        elif self.state == State.END_TAG_OPEN:
            self.tag.endtag = True
            if c.isalpha():
                self.tag.tag_name = c
                self.state = State.TAG_NAME
            else:
                raise BadCharError(self.state, c)

        elif self.state == State.TAG_NAME:
            if c in '\t\n\f ':
                self.state = State.BEFORE_ATTRIBUTE_NAME
            elif c == '/':
                self.state = State.SELF_CLOSING_START_TAG
            elif c == '>':
                self.emit_tag()
                self.state = State.DATA
            else:
                self.tag.tag_name += c

        elif self.state == State.BEFORE_ATTRIBUTE_NAME:
            if c in '\t\n\f ':
                pass
            elif c == '/':
                self.state = State.SELF_CLOSING_START_TAG
            elif c == '>':
                self.emit_tag()
                self.state = State.DATA
            elif c in "\"'<=":
                raise BadCharError(self.state, c)
            else:
                self.attribute_name = c.lower()
                self.state = State.ATTRIBUTE_NAME

        elif self.state == State.ATTRIBUTE_NAME:
            if c in '\t\n\f ':
                self.state = State.AFTER_ATTRIBUTE_NAME
            elif c == '/':
                self.got_attribute()
                self.state = State.SELF_CLOSING_START_TAG
            elif c == '=':
                self.state = State.BEFORE_ATTRIBUTE_VALUE
            elif c == '>':
                self.emit_tag()
                self.state = State.DATA
            elif c in "\"'<":
                raise BadCharError(self.state, c)
            else:
                self.attribute_name += c.lower()

        elif self.state == State.AFTER_ATTRIBUTE_NAME:
            if c in '\t\n\f ':
                pass
            elif c == '/':
                self.got_attribute()
                self.state = State.SELF_CLOSING_START_TAG
            elif c == '=':
                self.state = State.BEFORE_ATTRIBUTE_VALUE
            elif c == '>':
                self.got_attribute()
                self.emit_tag()
                self.state = State.DATA
            elif c in "\"'<":
                raise BadCharError(self.state, c)

        elif self.state == State.BEFORE_ATTRIBUTE_VALUE:
            if c in '\t\n\f ':
                pass
            elif c == '"':
                self.attribute_value = []
                self.state = State.ATTRIBUTE_VALUE_DOUBLE_QUOTED
            elif c == '&':
                self.attribute_value = []
                self.state = State.ATTRIBUTE_VALUE_UNQUOTED
                self.feed(c) # rehandle c
            elif c == "'":
                self.attribute_value = []
                self.state = State.ATTRIBUTE_VALUE_SINGLE_QUOTED
            elif c in '><=`':
                raise BadCharError(self.state, c)
            else:
                self.attribute_value = [c]
                self.state = State.ATTRIBUTE_VALUE_UNQUOTED

        elif self.state == State.ATTRIBUTE_VALUE_DOUBLE_QUOTED:
            if c == '"':
                self.state = State.AFTER_ATTRIBUTE_VALUE
            # Pass through; it's the browser's problem to understand these.
            #elif c == '&':
            #    raise Unimplemented
            else:
                self.add_data_char(self.attribute_value, c)

        elif self.state == State.ATTRIBUTE_VALUE_SINGLE_QUOTED:
            if c == "'":
                self.state = State.AFTER_ATTRIBUTE_VALUE
            # Pass through; it's the browser's problem to understand these.
            #elif c == '&':
            #    raise Unimplemented
            else:
                self.add_data_char(self.attribute_value, c)

        elif self.state == State.ATTRIBUTE_VALUE_UNQUOTED:
            if c in '\t\n\f ':
                self.got_attribute()
                self.state = State.BEFORE_ATTRIBUTE_NAME
            elif c == '>':
                self.got_attribute()
                self.emit_tag()
                self.state = State.DATA
            elif c in "\"'<=`":
                raise BadCharError(self.state, c)
            # Pass through; it's the browser's problem to understand these.
            #elif c == '&':
            #    raise Unimplemented
            else:
                self.add_data_char(self.attribute_value, c)

        elif self.state == State.AFTER_ATTRIBUTE_VALUE:
            self.got_attribute()
            if c in '\t\n\f ':
                self.state = State.BEFORE_ATTRIBUTE_NAME
            elif c == '/':
                self.state = State.SELF_CLOSING_START_TAG
            elif c == '>':
                self.emit_tag()
                self.state = State.DATA
            else:
                raise BadCharError(self.state, c)

        elif self.state == State.SELF_CLOSING_START_TAG:
            self.tag.startendtag = True
            if c == '>':
                self.emit_tag()
                self.state = State.DATA
            else:
                raise BadCharError(self.state, c)

        elif self.state == State.MARKUP_DECLARATION_OPEN:
            self.markup_declaration_buffer += c
            if self.markup_declaration_buffer == "--":
                self.data = ""
                self.state = State.COMMENT_START
            elif self.markup_declaration_buffer.lower() == "DOCTYPE".lower():
                self.state = State.DOCTYPE
            elif self.markup_declaration_buffer == "[CDATA[":
                self.data = ""
                self.cdata_buffer = ""
                self.state = State.CDATA_SECTION
            elif not ("--".startswith(self.markup_declaration_buffer) or
                      "DOCTYPE".lower().startswith(self.markup_declaration_buffer.lower()) or
                      "[CDATA[".startswith(self.markup_declaration_buffer)):
                raise BadCharError(self.state, c)

        elif self.state == State.COMMENT_START:
            if c == "-":
                self.state = State.COMMENT_START_DASH
            elif c == ">":
                raise BadCharError(self.state, c)
            else:
                self.data += c
                self.state = State.COMMENT

        elif self.state == State.COMMENT_START_DASH:
            if c == "-":
                self.state = State.COMMENT_END
            elif c == ">":
                raise BadCharError(self.state, c)
            else:
                self.data += "-" + c
                self.state = State.COMMENT

        elif self.state == State.COMMENT:
            if c == "-":
                self.state = State.COMMENT_END_DASH
            else:
                self.data += c

        elif self.state == State.COMMENT_END_DASH:
            if c == "-":
                self.state = State.COMMENT_END
            else:
                self.data += "-" + c
                self.state = State.COMMENT

        elif self.state == State.COMMENT_END:
            if c == ">":
                self.emit_comment()
                self.state = State.DATA
            else:
                raise BadCharError(self.state, c)

        elif self.state == State.DOCTYPE:
            if c in "\t\n\f ":
                self.data = ""
                self.state = State.DOCTYPE_CONTENTS
            else:
                raise BadCharError(self.state, c)

        elif self.state == State.DOCTYPE_CONTENTS:
            if c == ">":
                self.emit_doctype()
                self.state = State.DATA
            else:
                self.data += c

        elif self.state == State.CDATA_SECTION:
            self.cdata_buffer += c
            if self.cdata_buffer == "]]>":
                self.emit_cdata()
                self.state = State.DATA
            else:
                while self.cdata_buffer and not "]]>".startswith(self.cdata_buffer):
                    self.data += self.cdata_buffer[0]
                    self.cdata_buffer = self.cdata_buffer[1:]

        else:
            assert False, "bad state! %r" % self.state

    def feed_python(self, tokens):
        if self.state == State.BEFORE_ATTRIBUTE_VALUE:
            self.attribute_value = [tokens]
            self.state = State.ATTRIBUTE_VALUE_UNQUOTED
        elif self.state in [State.ATTRIBUTE_VALUE_DOUBLE_QUOTED,
                            State.ATTRIBUTE_VALUE_SINGLE_QUOTED,
                            State.ATTRIBUTE_VALUE_UNQUOTED]:
            self.attribute_value.append(tokens)
        else:
            raise ParseError("python not allow in state %r" % State.state_name(self.state))

class HTMLTokenDumper(HTMLTokenizer):
    def handle_data(self, data):
        print "DATA %r" % data

    def handle_starttag(self, tag_name, attrs):
        print "STARTTAG %r %r" % (tag_name, attrs)

    def handle_startendtag(self, tag_name, attrs):
        print "STARTENDTAG %r %r" % (tag_name, attrs)

    def handle_endtag(self, tag_name):
        print "ENDTAG %r" % tag_name

def main(filename):
    dumper = HTMLTokenDumper()
    with open(filename) as f:
        for line in f:
            for c in line:
                dumper.feed(c)

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = parser
#!/usr/bin/env python

import tokenize
from pyxl import html
from html_tokenizer import (
        HTMLTokenizer,
        ParseError as TokenizerParseError,
        State,
)
from pytokenize import Untokenizer

class ParseError(Exception):
    def __init__(self, message, pos=None):
        if pos is not None:
            super(ParseError, self).__init__("%s at line %d char %d" % ((message,) + pos))
        else:
            super(ParseError, self).__init__(message)

class PyxlParser(HTMLTokenizer):
    def __init__(self, row, col):
        super(PyxlParser, self).__init__()
        self.start = self.end = (row, col)
        self.output = []
        self.open_tags = []
        self.remainder = None
        self.next_thing_is_python = False
        self.last_thing_was_python = False
        self.last_thing_was_close_if_tag = False

    def feed(self, token):
        ttype, tvalue, tstart, tend, tline = token

        assert tstart[0] >= self.end[0], "row went backwards"
        if tstart[0] > self.end[0]:
            self.output.append("\n" * (tstart[0] - self.end[0]))

        # interpret jumps on the same line as a single space
        elif tstart[1] > self.end[1]:
            super(PyxlParser, self).feed(" ")

        self.end = tstart

        if ttype != tokenize.INDENT:
            while tvalue and not self.done():
                c, tvalue = tvalue[0], tvalue[1:]
                if c == "\n":
                    self.end = (self.end[0]+1, 0)
                else:
                    self.end = (self.end[0], self.end[1]+1)
                try:
                    super(PyxlParser, self).feed(c)
                except TokenizerParseError:
                    raise ParseError("HTML Parsing error", self.end)
        if self.done():
            self.remainder = (ttype, tvalue, self.end, tend, tline)
        else:
            self.end = tend

    def feed_python(self, tokens):
        ttype, tvalue, tstart, tend, tline = tokens[0]
        assert tstart[0] >= self.end[0], "row went backwards"
        if tstart[0] > self.end[0]:
            self.output.append("\n" * (tstart[0] - self.end[0]))
        ttype, tvalue, tstart, tend, tline = tokens[-1]
        self.end = tend

        if self.state in [State.DATA, State.CDATA_SECTION]:
            self.next_thing_is_python = True
            self.emit_data()
            self.output.append("%s, " % Untokenizer().untokenize(tokens))
            self.next_thing_is_python = False
            self.last_thing_was_python = True
        elif self.state in [State.BEFORE_ATTRIBUTE_VALUE,
                            State.ATTRIBUTE_VALUE_DOUBLE_QUOTED,
                            State.ATTRIBUTE_VALUE_SINGLE_QUOTED,
                            State.ATTRIBUTE_VALUE_UNQUOTED]:
            super(PyxlParser, self).feed_python(tokens)

    def feed_position_only(self, token):
        """update with any whitespace we might have missed, and advance position to after the
        token"""
        ttype, tvalue, tstart, tend, tline = token
        self.feed((ttype, '', tstart, tstart, tline))
        self.end = tend

    def python_comment_allowed(self):
        """Returns true if we're in a state where a # starts a comment.

        <a # comment before attribute name
           class="bar"# comment after attribute value
           href="#notacomment">
            # comment in data
            Link text
        </a>
        """
        return self.state in (State.DATA, State.TAG_NAME,
                              State.BEFORE_ATTRIBUTE_NAME, State.AFTER_ATTRIBUTE_NAME,
                              State.BEFORE_ATTRIBUTE_VALUE, State.AFTER_ATTRIBUTE_VALUE,
                              State.COMMENT, State.DOCTYPE_CONTENTS, State.CDATA_SECTION)

    def python_mode_allowed(self):
        """Returns true if we're in a state where a { starts python mode.

        <!-- {this isn't python} -->
        """
        return self.state not in (State.COMMENT,)

    def feed_comment(self, token):
        ttype, tvalue, tstart, tend, tline = token
        self.feed((ttype, '', tstart, tstart, tline))
        self.output.append(tvalue)
        self.end = tend

    def get_remainder(self):
        return self.remainder

    def done(self):
        return len(self.open_tags) == 0 and self.state == State.DATA and self.output

    def get_token(self):
        return (tokenize.STRING, ''.join(self.output), self.start, self.end, '')

    @staticmethod
    def safe_attr_name(name):
        if name == "class":
            return "xclass"
        if name == "for":
            return "xfor"
        return name.replace('-', '_').replace(':', 'COLON')

    def _handle_attr_value(self, attr_value):
        def format_parts():
            prev_was_python = False
            for i, part in enumerate(attr_value):
                if type(part) == list:
                    yield part
                    prev_was_python = True
                else:
                    next_is_python = bool(i+1 < len(attr_value) and type(attr_value[i+1]) == list)
                    part = self._normalize_data_whitespace(part, prev_was_python, next_is_python)
                    if part:
                        yield part
                    prev_was_python = False

        attr_value = list(format_parts())
        if len(attr_value) == 1:
            part = attr_value[0]
            if type(part) == list:
                self.output.append(Untokenizer().untokenize(part))
            else:
                self.output.append(repr(part))
        else:
            self.output.append('u"".join((')
            for part in attr_value:
                if type(part) == list:
                    self.output.append('unicode(')
                    self.output.append(Untokenizer().untokenize(part))
                    self.output.append(')')
                else:
                    self.output.append(repr(part))
                self.output.append(', ')
            self.output.append('))')

    @staticmethod
    def _normalize_data_whitespace(data, prev_was_py, next_is_py):
        if not data:
            return ''
        if '\n' in data and not data.strip():
            if prev_was_py and next_is_py:
                return ' '
            else:
                return ''
        if prev_was_py and data.startswith('\n'):
                data = " " + data.lstrip('\n')
        if next_is_py and data.endswith('\n'):
                data = data.rstrip('\n') + " "
        data = data.strip('\n')
        data = data.replace('\r', ' ')
        data = data.replace('\n', ' ')
        return data

    def handle_starttag(self, tag, attrs, call=True):
        self.open_tags.append({'tag':tag, 'row': self.end[0]})
        if tag == 'if':
            if len(attrs) != 1:
                raise ParseError("if tag only takes one attr called 'cond'", self.end)
            if 'cond' not in attrs:
                raise ParseError("if tag must contain the 'cond' attr", self.end)

            self.output.append('html._push_condition(bool(')
            self._handle_attr_value(attrs['cond'])
            self.output.append(')) and html.x_frag()(')
            self.last_thing_was_python = False
            self.last_thing_was_close_if_tag = False
            return
        elif tag == 'else':
            if len(attrs) != 0:
                raise ParseError("else tag takes no attrs", self.end)
            if not self.last_thing_was_close_if_tag:
                raise ParseError("<else> tag must come right after </if>", self.end)

            self.output.append('(not html._last_if_condition) and html.x_frag()(')
            self.last_thing_was_python = False
            self.last_thing_was_close_if_tag = False
            return

        module, dot, identifier = tag.rpartition('.')
        identifier = 'x_%s' % identifier
        x_tag = module + dot + identifier

        if hasattr(html, x_tag):
            self.output.append('html.')
        self.output.append('%s(' % x_tag)

        first_attr = True
        for attr_name, attr_value in attrs.iteritems():
            if first_attr: first_attr = False
            else: self.output.append(', ')

            self.output.append(self.safe_attr_name(attr_name))
            self.output.append('=')
            self._handle_attr_value(attr_value)

        self.output.append(')')
        if call:
            # start call to __call__
            self.output.append('(')
        self.last_thing_was_python = False
        self.last_thing_was_close_if_tag = False

    def handle_endtag(self, tag_name, call=True):
        if call:
            # finish call to __call__
            self.output.append(")")

        assert self.open_tags, "got </%s> but tag stack empty; parsing should be over!" % tag_name

        open_tag = self.open_tags.pop()
        if open_tag['tag'] != tag_name:
            raise ParseError("<%s> on line %d closed by </%s> on line %d" %
                             (open_tag['tag'], open_tag['row'], tag_name, self.end[0]))

        if open_tag['tag'] == 'if':
            self.output.append(',html._leave_if()')
            self.last_thing_was_close_if_tag = True
        else:
            self.last_thing_was_close_if_tag = False

        if len(self.open_tags):
            self.output.append(",")
        self.last_thing_was_python = False

    def handle_startendtag(self, tag_name, attrs):
        self.handle_starttag(tag_name, attrs, call=False)
        self.handle_endtag(tag_name, call=False)

    def handle_data(self, data):
        data = self._normalize_data_whitespace(
                data, self.last_thing_was_python, self.next_thing_is_python)
        if not data:
            return

        # XXX XXX mimics old pyxl, but this is gross and likely wrong. I'm pretty sure we actually
        # want %r instead of this crazy quote substitution and u"%s".
        data = data.replace('"', '\\"')
        self.output.append('html.rawhtml(u"%s"), ' % data)

        self.last_thing_was_python = False
        self.last_thing_was_close_if_tag = False

    def handle_comment(self, data):
        self.handle_startendtag("html_comment", {"comment": [data.strip()]})
        self.last_thing_was_python = False
        self.last_thing_was_close_if_tag = False

    def handle_doctype(self, data):
        self.handle_startendtag("html_decl", {"decl": ['DOCTYPE ' + data]})
        self.last_thing_was_python = False
        self.last_thing_was_close_if_tag = False

    def handle_cdata(self, data):
        self.handle_startendtag("html_marked_decl", {"decl": ['CDATA[' + data]})
        self.last_thing_was_python = False
        self.last_thing_was_close_if_tag = False

########NEW FILE########
__FILENAME__ = pytokenize
"""Tokenization help for Python programs.

generate_tokens(readline) is a generator that breaks a stream of
text into Python tokens.  It accepts a readline-like method which is called
repeatedly to get the next line of input (or "" for EOF).  It generates
5-tuples with these members:

    the token type (see token.py)
    the token (a string)
    the starting (row, column) indices of the token (a 2-tuple of ints)
    the ending (row, column) indices of the token (a 2-tuple of ints)
    the original line (string)

It is designed to match the working of the Python tokenizer exactly, except
that it produces COMMENT tokens for comments and gives type OP for all
operators

Older entry points
    tokenize_loop(readline, tokeneater)
    tokenize(readline, tokeneater=printtoken)
are the same, except instead of generating tokens, tokeneater is a callback
function to which the 5 fields described above are passed as 5 arguments,
each time a new token is found.


This file was taken from the python 2.7.4 library and modified for use by
the Pyxl decoder. Changes made:
    - When it encounters an unexpected EOF, the tokenizer does not raise an
      exception, and instead yields an errortoken if appropriate.
    - When it encounters an unexpected dedent, the tokenizer does not
      raise an exception.
    - The Untokenizer class was heavily modified.


PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
--------------------------------------------

1. This LICENSE AGREEMENT is between the Python Software Foundation
("PSF"), and the Individual or Organization ("Licensee") accessing and
otherwise using this software ("Python") in source or binary form and
its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
analyze, test, perform and/or display publicly, prepare derivative works,
distribute, and otherwise use Python alone or in any derivative version,
provided, however, that PSF's License Agreement and PSF's notice of copyright,
i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013 Python Software Foundation; All Rights Reserved" are retained
in Python alone or in any derivative version prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on
or incorporates Python or any part thereof, and wants to make
the derivative work available to others as provided herein, then
Licensee hereby agrees to include in any such work a brief summary of
the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS"
basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material
breach of its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any
relationship of agency, partnership, or joint venture between PSF and
Licensee.  This License Agreement does not grant permission to use PSF
trademarks or trade name in a trademark sense to endorse or promote
products or services of Licensee, or any third party.

8. By copying, installing or otherwise using Python, Licensee
agrees to be bound by the terms and conditions of this License
Agreement.
"""

__author__ = 'Ka-Ping Yee <ping@lfw.org>'
__credits__ = ('GvR, ESR, Tim Peters, Thomas Wouters, Fred Drake, '
               'Skip Montanaro, Raymond Hettinger')

import string, re
from token import *

import token
__all__ = [x for x in dir(token) if not x.startswith("_")]
__all__ += ["COMMENT", "tokenize", "generate_tokens", "NL", "untokenize"]
del x
del token

COMMENT = N_TOKENS
tok_name[COMMENT] = 'COMMENT'
NL = N_TOKENS + 1
tok_name[NL] = 'NL'
N_TOKENS += 2

def group(*choices): return '(' + '|'.join(choices) + ')'
def any(*choices): return group(*choices) + '*'
def maybe(*choices): return group(*choices) + '?'

Whitespace = r'[ \f\t]*'
Comment = r'#[^\r\n]*'
Ignore = Whitespace + any(r'\\\r?\n' + Whitespace) + maybe(Comment)
Name = r'[a-zA-Z_]\w*'

Hexnumber = r'0[xX][\da-fA-F]+[lL]?'
Octnumber = r'(0[oO][0-7]+)|(0[0-7]*)[lL]?'
Binnumber = r'0[bB][01]+[lL]?'
Decnumber = r'[1-9]\d*[lL]?'
Intnumber = group(Hexnumber, Binnumber, Octnumber, Decnumber)
Exponent = r'[eE][-+]?\d+'
Pointfloat = group(r'\d+\.\d*', r'\.\d+') + maybe(Exponent)
Expfloat = r'\d+' + Exponent
Floatnumber = group(Pointfloat, Expfloat)
Imagnumber = group(r'\d+[jJ]', Floatnumber + r'[jJ]')
Number = group(Imagnumber, Floatnumber, Intnumber)

# Tail end of ' string.
Single = r"[^'\\]*(?:\\.[^'\\]*)*'"
# Tail end of " string.
Double = r'[^"\\]*(?:\\.[^"\\]*)*"'
# Tail end of ''' string.
Single3 = r"[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''"
# Tail end of """ string.
Double3 = r'[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*"""'
Triple = group("[uUbB]?[rR]?'''", '[uUbB]?[rR]?"""')
# Single-line ' or " string.
String = group(r"[uUbB]?[rR]?'[^\n'\\]*(?:\\.[^\n'\\]*)*'",
               r'[uUbB]?[rR]?"[^\n"\\]*(?:\\.[^\n"\\]*)*"')

# Because of leftmost-then-longest match semantics, be sure to put the
# longest operators first (e.g., if = came before ==, == would get
# recognized as two instances of =).
Operator = group(r"\*\*=?", r">>=?", r"<<=?", r"<>", r"!=",
                 r"//=?",
                 r"[+\-*/%&|^=<>]=?",
                 r"~")

Bracket = '[][(){}]'
Special = group(r'\r?\n', r'[:;.,`@]')
Funny = group(Operator, Bracket, Special)

PlainToken = group(Number, Funny, String, Name)
Token = Ignore + PlainToken

# First (or only) line of ' or " string.
ContStr = group(r"[uUbB]?[rR]?'[^\n'\\]*(?:\\.[^\n'\\]*)*" +
                group("'", r'\\\r?\n'),
                r'[uUbB]?[rR]?"[^\n"\\]*(?:\\.[^\n"\\]*)*' +
                group('"', r'\\\r?\n'))
PseudoExtras = group(r'\\\r?\n|\Z', Comment, Triple)
PseudoToken = Whitespace + group(PseudoExtras, Number, Funny, ContStr, Name)

tokenprog, pseudoprog, single3prog, double3prog = map(
    re.compile, (Token, PseudoToken, Single3, Double3))
endprogs = {"'": re.compile(Single), '"': re.compile(Double),
            "'''": single3prog, '"""': double3prog,
            "r'''": single3prog, 'r"""': double3prog,
            "u'''": single3prog, 'u"""': double3prog,
            "ur'''": single3prog, 'ur"""': double3prog,
            "R'''": single3prog, 'R"""': double3prog,
            "U'''": single3prog, 'U"""': double3prog,
            "uR'''": single3prog, 'uR"""': double3prog,
            "Ur'''": single3prog, 'Ur"""': double3prog,
            "UR'''": single3prog, 'UR"""': double3prog,
            "b'''": single3prog, 'b"""': double3prog,
            "br'''": single3prog, 'br"""': double3prog,
            "B'''": single3prog, 'B"""': double3prog,
            "bR'''": single3prog, 'bR"""': double3prog,
            "Br'''": single3prog, 'Br"""': double3prog,
            "BR'''": single3prog, 'BR"""': double3prog,
            'r': None, 'R': None, 'u': None, 'U': None,
            'b': None, 'B': None}

triple_quoted = {}
for t in ("'''", '"""',
          "r'''", 'r"""', "R'''", 'R"""',
          "u'''", 'u"""', "U'''", 'U"""',
          "ur'''", 'ur"""', "Ur'''", 'Ur"""',
          "uR'''", 'uR"""', "UR'''", 'UR"""',
          "b'''", 'b"""', "B'''", 'B"""',
          "br'''", 'br"""', "Br'''", 'Br"""',
          "bR'''", 'bR"""', "BR'''", 'BR"""'):
    triple_quoted[t] = t
single_quoted = {}
for t in ("'", '"',
          "r'", 'r"', "R'", 'R"',
          "u'", 'u"', "U'", 'U"',
          "ur'", 'ur"', "Ur'", 'Ur"',
          "uR'", 'uR"', "UR'", 'UR"',
          "b'", 'b"', "B'", 'B"',
          "br'", 'br"', "Br'", 'Br"',
          "bR'", 'bR"', "BR'", 'BR"' ):
    single_quoted[t] = t

tabsize = 8

class TokenError(Exception): pass

class StopTokenizing(Exception): pass

def printtoken(type, token, srow_scol, erow_ecol, line): # for testing
    srow, scol = srow_scol
    erow, ecol = erow_ecol
    print "%d,%d-%d,%d:\t%s\t%s" % \
        (srow, scol, erow, ecol, tok_name[type], repr(token))

def tokenize(readline, tokeneater=printtoken):
    """
    The tokenize() function accepts two parameters: one representing the
    input stream, and one providing an output mechanism for tokenize().

    The first parameter, readline, must be a callable object which provides
    the same interface as the readline() method of built-in file objects.
    Each call to the function should return one line of input as a string.

    The second parameter, tokeneater, must also be a callable object. It is
    called once for each token, with five arguments, corresponding to the
    tuples generated by generate_tokens().
    """
    try:
        tokenize_loop(readline, tokeneater)
    except StopTokenizing:
        pass

# backwards compatible interface
def tokenize_loop(readline, tokeneater):
    for token_info in generate_tokens(readline):
        tokeneater(*token_info)

class Untokenizer:

    # PYXL MODIFICATION: This entire class.

    def __init__(self, row=None, col=None):
        self.tokens = []
        self.prev_row = row
        self.prev_col = col

    def add_whitespace(self, start):
        row, col = start
        assert row >= self.prev_row, "row (%r) should be >= prev_row (%r)" % (row, self.prev_row)
        row_offset = row - self.prev_row
        if row_offset:
            self.tokens.append("\n" * row_offset)
        col_offset = col - self.prev_col
        if col_offset:
            self.tokens.append(" " * col_offset)

    def feed(self, t):
        assert len(t) == 5
        tok_type, token, start, end, line = t
        if (self.prev_row is None):
            self.prev_row, self.prev_col = start
        self.add_whitespace(start)
        self.tokens.append(token)
        self.prev_row, self.prev_col = end
        if tok_type in (NEWLINE, NL):
            self.prev_row += 1
            self.prev_col = 0

    def finish(self):
        return "".join(self.tokens)

    def untokenize(self, iterable):
        for t in iterable:
            self.feed(t)
        return self.finish()

def untokenize(iterable):
    """Transform tokens back into Python source code.

    Each element returned by the iterable must be a token sequence
    with at least two elements, a token number and token value.  If
    only two tokens are passed, the resulting output is poor.

    Round-trip invariant for full input:
        Untokenized source will match input source exactly

    Round-trip invariant for limited intput:
        # Output text will tokenize the back to the input
        t1 = [tok[:2] for tok in generate_tokens(f.readline)]
        newcode = untokenize(t1)
        readline = iter(newcode.splitlines(1)).next
        t2 = [tok[:2] for tok in generate_tokens(readline)]
        assert t1 == t2
    """
    ut = Untokenizer()
    return ut.untokenize(iterable)

def generate_tokens(readline):
    """
    The generate_tokens() generator requires one argment, readline, which
    must be a callable object which provides the same interface as the
    readline() method of built-in file objects. Each call to the function
    should return one line of input as a string.  Alternately, readline
    can be a callable function terminating with StopIteration:
        readline = open(myfile).next    # Example of alternate readline

    The generator produces 5-tuples with these members: the token type; the
    token string; a 2-tuple (srow, scol) of ints specifying the row and
    column where the token begins in the source; a 2-tuple (erow, ecol) of
    ints specifying the row and column where the token ends in the source;
    and the line on which the token was found. The line passed is the
    logical line; continuation lines are included.
    """
    lnum = parenlev = continued = 0
    namechars, numchars = string.ascii_letters + '_', '0123456789'
    contstr, needcont = '', 0
    contline = None
    indents = [0]

    while 1:                                   # loop over lines in stream
        try:
            line = readline()
        except StopIteration:
            line = ''
        lnum += 1
        pos, max = 0, len(line)

        if contstr:                            # continued string
            if not line:
                # PYXL MODIFICATION: instead of raising an error here, we
                # return the remainder of the file as an errortoken.
                yield (ERRORTOKEN, contstr,
                       strstart, (lnum, 0), contline + line)
                contstr, needcont = '', 0
                contline = None
                return
            endmatch = endprog.match(line)
            if endmatch:
                pos = end = endmatch.end(0)
                yield (STRING, contstr + line[:end],
                       strstart, (lnum, end), contline + line)
                contstr, needcont = '', 0
                contline = None
            elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
                yield (ERRORTOKEN, contstr + line,
                           strstart, (lnum, len(line)), contline)
                contstr = ''
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        elif parenlev == 0 and not continued:  # new statement
            if not line: break
            column = 0
            while pos < max:                   # measure leading whitespace
                if line[pos] == ' ':
                    column += 1
                elif line[pos] == '\t':
                    column = (column//tabsize + 1)*tabsize
                elif line[pos] == '\f':
                    column = 0
                else:
                    break
                pos += 1
            if pos == max:
                break

            if line[pos] in '#\r\n':           # skip comments or blank lines
                if line[pos] == '#':
                    comment_token = line[pos:].rstrip('\r\n')
                    nl_pos = pos + len(comment_token)
                    yield (COMMENT, comment_token,
                           (lnum, pos), (lnum, pos + len(comment_token)), line)
                    yield (NL, line[nl_pos:],
                           (lnum, nl_pos), (lnum, len(line)), line)
                else:
                    yield ((NL, COMMENT)[line[pos] == '#'], line[pos:],
                           (lnum, pos), (lnum, len(line)), line)
                continue

            if column > indents[-1]:           # count indents or dedents
                indents.append(column)
                yield (INDENT, line[:pos], (lnum, 0), (lnum, pos), line)
            while column < indents[-1]:
                if column not in indents:
                    # PYXL MODIFICATION: instead of raising an error here, we
                    # emit an empty dedent token, which has no effect on
                    # the decoded file.
                    pass
                indents = indents[:-1]
                yield (DEDENT, '', (lnum, pos), (lnum, pos), line)

        else:                                  # continued statement
            if not line:
                # PYXL MODIFICATION: instead of raising an error here, we
                # return as if successful.
                return
            continued = 0

        while pos < max:
            pseudomatch = pseudoprog.match(line, pos)
            if pseudomatch:                                # scan for tokens
                start, end = pseudomatch.span(1)
                spos, epos, pos = (lnum, start), (lnum, end), end
                if start == end:
                    continue
                token, initial = line[start:end], line[start]

                if initial in numchars or \
                   (initial == '.' and token != '.'):      # ordinary number
                    yield (NUMBER, token, spos, epos, line)
                elif initial in '\r\n':
                    yield (NL if parenlev > 0 else NEWLINE,
                           token, spos, epos, line)
                elif initial == '#':
                    assert not token.endswith("\n")
                    yield (COMMENT, token, spos, epos, line)
                elif token in triple_quoted:
                    endprog = endprogs[token]
                    endmatch = endprog.match(line, pos)
                    if endmatch:                           # all on one line
                        pos = endmatch.end(0)
                        token = line[start:pos]
                        yield (STRING, token, spos, (lnum, pos), line)
                    else:
                        strstart = (lnum, start)           # multiple lines
                        contstr = line[start:]
                        contline = line
                        break
                elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                    if token[-1] == '\n':                  # continued string
                        strstart = (lnum, start)
                        endprog = (endprogs[initial] or endprogs[token[1]] or
                                   endprogs[token[2]])
                        contstr, needcont = line[start:], 1
                        contline = line
                        break
                    else:                                  # ordinary string
                        yield (STRING, token, spos, epos, line)
                elif initial in namechars:                 # ordinary name
                    yield (NAME, token, spos, epos, line)
                elif initial == '\\':                      # continued stmt
                    continued = 1
                else:
                    if initial in '([{':
                        parenlev += 1
                    elif initial in ')]}':
                        parenlev -= 1
                    yield (OP, token, spos, epos, line)
            else:
                yield (ERRORTOKEN, line[pos],
                           (lnum, pos), (lnum, pos+1), line)
                pos += 1

    for indent in indents[1:]:                 # pop remaining indent levels
        yield (DEDENT, '', (lnum, 0), (lnum, 0), '')
    yield (ENDMARKER, '', (lnum, 0), (lnum, 0), '')

if __name__ == '__main__':                     # testing
    import sys
    if len(sys.argv) > 1:
        tokenize(open(sys.argv[1]).readline)
    else:
        tokenize(sys.stdin.readline)

########NEW FILE########
__FILENAME__ = register
#!/usr/bin/env python
from __future__ import with_statement

import codecs, cStringIO, encodings
import sys
import traceback
from encodings import utf_8
from pyxl.codec.tokenizer import pyxl_tokenize, pyxl_untokenize

def pyxl_transform(stream):
    try:
        output = pyxl_untokenize(pyxl_tokenize(stream.readline))
    except Exception, ex:
        print ex
        traceback.print_exc()
        raise

    return output.rstrip()

def pyxl_transform_string(text):
    stream = cStringIO.StringIO(text)
    return pyxl_transform(stream)

def pyxl_decode(input, errors='strict'):
    return utf_8.decode(pyxl_transform_string(input), errors)

class PyxlIncrementalDecoder(utf_8.IncrementalDecoder):
    def decode(self, input, final=False):
        self.buffer += input
        if final:
            buff = self.buffer
            self.buffer = ''
            return super(PyxlIncrementalDecoder, self).decode(
                pyxl_transform_string(buff), final=True)

class PyxlStreamReader(utf_8.StreamReader):
    def __init__(self, *args, **kwargs):
        codecs.StreamReader.__init__(self, *args, **kwargs)
        self.stream = cStringIO.StringIO(pyxl_transform(self.stream))

def search_function(encoding):
    if encoding != 'pyxl': return None
    # Assume utf8 encoding
    utf8=encodings.search_function('utf8')
    return codecs.CodecInfo(
        name = 'pyxl',
        encode = utf8.encode,
        decode = pyxl_decode,
        incrementalencoder = utf8.incrementalencoder,
        incrementaldecoder = PyxlIncrementalDecoder,
        streamreader = PyxlStreamReader,
        streamwriter = utf8.streamwriter)

codecs.register(search_function)

_USAGE = """\
Wraps a python command to allow it to recognize pyxl-coded files with
no source modifications.

Usage:
    python -m pyxl.codec.register -m module.to.run [args...]
    python -m pyxl.codec.register path/to/script.py [args...]
"""

if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '-m':
        mode = 'module'
        module = sys.argv[2]
        del sys.argv[1:3]
    elif len(sys.argv) >= 2:
        mode = 'script'
        script = sys.argv[1]
        sys.argv = sys.argv[1:]
    else:
        print >>sys.stderr, _USAGE
        sys.exit(1)

    if mode == 'module':
        import runpy
        runpy.run_module(module, run_name='__main__', alter_sys=True)
    elif mode == 'script':
        with open(script) as f:
            global __file__
            __file__ = script
            # Use globals as our "locals" dictionary so that something
            # that tries to import __main__ (e.g. the unittest module)
            # will see the right things.
            exec f.read() in globals(), globals()

########NEW FILE########
__FILENAME__ = tokenizer
#!/usr/bin/env python

import pytokenize as tokenize
import re
from StringIO import StringIO
from pyxl.codec.parser import PyxlParser
from pytokenize import Untokenizer

class PyxlParseError(Exception): pass

def get_end_pos(start_pos, tvalue):
    row, col = start_pos
    for c in tvalue:
        if c == '\n':
            col = 0
            row += 1
        else:
            col += 1
    return (row, col)

class RewindableTokenStream(object):
    """
    A token stream, with the ability to rewind and restart tokenization while maintaining correct
    token position information.

    Invariants:
        - zero_row and zero_col are the correct values to adjust the line and possibly column of the
        tokens being produced by _tokens.
        - Tokens in unshift_buffer have locations with absolute position (relative to the beginning
          of the file, not relative to where we last restarted tokenization).
    """

    def __init__(self, readline):
        self.orig_readline = readline
        self.unshift_buffer = []
        self.rewound_buffer = None
        self._tokens = tokenize.generate_tokens(self._readline)
        self.zero_row, self.zero_col = (0, 0)
        self.stop_readline = False

    def _dumpstate(self):
        print "tokenizer state:"
        print "  zero:", (self.zero_row, self.zero_col)
        print "  rewound_buffer:", self.rewound_buffer
        print "  unshift_buffer:", self.unshift_buffer

    def _readline(self):
        if self.stop_readline:
            return ""
        if self.rewound_buffer:
            line = self.rewound_buffer.readline()
            if line:
                return line
            else:
                self.rewound_buffer = None  # fallthrough to orig_readline
        return self.orig_readline()

    def _flush(self):
        self.stop_readline = True
        tokens = list(tok for tok in self)
        self.stop_readline = False
        return tokens

    def _adjust_position(self, pos):
        row, col = pos
        if row == 0:
            col += self.zero_col
        row += self.zero_row
        return (row, col)

    def rewind_and_retokenize(self, rewind_token):
        """Rewind the given token (which is expected to be the last token read from this stream, or
        the end of such token); then restart tokenization."""
        ttype, tvalue, (row, col), tend, tline = rewind_token
        tokens = [rewind_token] + self._flush()
        self.zero_row, self.zero_col = (row - 1, col - 1)
        self.rewound_buffer = StringIO(Untokenizer().untokenize(tokens))
        self.unshift_buffer = []
        self._tokens = tokenize.generate_tokens(self._readline)

    def next(self):
        if self.unshift_buffer:
            token = self.unshift_buffer.pop(0)
        else:
            ttype, tvalue, tstart, tend, tline = self._tokens.next()
            tstart = self._adjust_position(tstart)
            tend = self._adjust_position(tend)
            token = (ttype, tvalue, tstart, tend, tline)
        return token

    def __iter__(self):
        return self

    def unshift(self, token):
        """Rewind the given token, without retokenizing. It will be the next token read from the
        stream."""
        self.unshift_buffer[:0] = [token]

def pyxl_untokenize(tokens):
    parts = []
    prev_row = 1
    prev_col = 0

    for token in tokens:
        ttype, tvalue, tstart, tend, tline = token
        row, col = tstart

        assert row == prev_row, 'Unexpected jump in rows on line:%d: %s' % (row, tline)

        # Add whitespace
        col_offset = col - prev_col
        if col_offset > 0:
            parts.append(" " * col_offset)

        parts.append(tvalue)
        prev_row, prev_col = tend

        if ttype in (tokenize.NL, tokenize.NEWLINE):
            prev_row += 1
            prev_col = 0

    return ''.join(parts)

def pyxl_tokenize(readline):
    return transform_tokens(RewindableTokenStream(readline))

def transform_tokens(tokens):
    last_nw_token = None
    prev_token = None

    curly_depth = 0

    while 1:
        try:
            token = tokens.next()
        except (StopIteration, tokenize.TokenError):
            break

        ttype, tvalue, tstart, tend, tline = token

        if ttype == tokenize.OP and tvalue == '{':
            curly_depth += 1
        if ttype == tokenize.OP and tvalue == '}':
            curly_depth -= 1
            if curly_depth < 0:
                tokens.unshift(token)
                return

        if (ttype == tokenize.OP and tvalue == '<' and
            (last_nw_token == None or # if we have *just* entered python mode e.g
             (last_nw_token[0] == tokenize.OP and last_nw_token[1] == '=') or
             (last_nw_token[0] == tokenize.OP and last_nw_token[1] == '(') or
             (last_nw_token[0] == tokenize.OP and last_nw_token[1] == '[') or
             (last_nw_token[0] == tokenize.OP and last_nw_token[1] == '{') or
             (last_nw_token[0] == tokenize.OP and last_nw_token[1] == ',') or
             (last_nw_token[0] == tokenize.OP and last_nw_token[1] == ':') or
             (last_nw_token[0] == tokenize.NAME and last_nw_token[1] == 'print') or
             (last_nw_token[0] == tokenize.NAME and last_nw_token[1] == 'else') or
             (last_nw_token[0] == tokenize.NAME and last_nw_token[1] == 'yield') or
             (last_nw_token[0] == tokenize.NAME and last_nw_token[1] == 'return'))):
            token = get_pyxl_token(token, tokens)

        if ttype not in (tokenize.INDENT,
                         tokenize.DEDENT,
                         tokenize.NL,
                         tokenize.NEWLINE,
                         tokenize.COMMENT):
            last_nw_token = token

        # strip trailing newline from non newline tokens
        if tvalue and tvalue[-1] == '\n' and ttype not in (tokenize.NL, tokenize.NEWLINE):
            ltoken = list(token)
            tvalue = ltoken[1] = tvalue[:-1]
            token = tuple(ltoken)

        # tokenize has this bug where you can get line jumps without a newline token
        # we check and fix for that here by seeing if there was a line jump
        if prev_token:
            prev_ttype, prev_tvalue, prev_tstart, prev_tend, prev_tline = prev_token

            prev_row, prev_col = prev_tend
            cur_row, cur_col = tstart

            # check for a line jump without a newline token
            if (prev_row < cur_row and prev_ttype not in (tokenize.NEWLINE, tokenize.NL)):

                # tokenize also forgets \ continuations :(
                prev_line = prev_tline.strip()
                if prev_ttype != tokenize.COMMENT and prev_line and prev_line[-1] == '\\':
                    start_pos = (prev_row, prev_col)
                    end_pos = (prev_row, prev_col+1)
                    yield (tokenize.STRING, ' \\', start_pos, end_pos, prev_tline)
                    prev_col += 1

                start_pos = (prev_row, prev_col)
                end_pos = (prev_row, prev_col+1)
                yield (tokenize.NL, '\n', start_pos, end_pos, prev_tline)

        prev_token = token
        yield token

def get_pyxl_token(start_token, tokens):
    ttype, tvalue, tstart, tend, tline = start_token
    pyxl_parser = PyxlParser(tstart[0], tstart[1])
    pyxl_parser.feed(start_token)

    for token in tokens:
        ttype, tvalue, tstart, tend, tline = token

        if tvalue and tvalue[0] == '{':
            if pyxl_parser.python_mode_allowed():
                mid, right = tvalue[0], tvalue[1:]
                division = get_end_pos(tstart, mid)
                pyxl_parser.feed_position_only((ttype, mid, tstart, division, tline))
                tokens.rewind_and_retokenize((ttype, right, division, tend, tline))
                python_tokens = list(transform_tokens(tokens))

                close_curly = tokens.next()
                ttype, tvalue, tstart, tend, tline = close_curly
                close_curly_sub = (ttype, '', tend, tend, tline)

                pyxl_parser.feed_python(python_tokens + [close_curly_sub])
                continue
            # else fallthrough to pyxl_parser.feed(token)
        elif tvalue and ttype == tokenize.COMMENT:
            if not pyxl_parser.python_comment_allowed():
                tvalue, rest = tvalue[0], tvalue[1:]
                division = get_end_pos(tstart, tvalue)
                tokens.unshift((tokenize.ERRORTOKEN, rest, division, tend, tline))
                token = ttype, tvalue, tstart, division, tline
                # fallthrough to pyxl_parser.feed(token)
            else:
                pyxl_parser.feed_comment(token)
                continue
        elif tvalue and tvalue[0] == '#':
            # let the python tokenizer grab the whole comment token
            tokens.rewind_and_retokenize(token)
            continue
        else:
            sp = re.split('([#{])', tvalue, maxsplit=1)
            if len(sp) > 1:
                tvalue, mid, right = sp
                division = get_end_pos(tstart, tvalue)
                tokens.unshift((ttype, mid+right, division, tend, tline))
                token = ttype, tvalue, tstart, division, tline
                # fallthrough to pyxl_parser.feed(token)

        pyxl_parser.feed(token)

        if pyxl_parser.done(): break

    if not pyxl_parser.done():
        lines = ['<%s> at (line:%d)' % (tag_info['tag'], tag_info['row'])
                 for tag_info in pyxl_parser.open_tags]
        raise PyxlParseError('Unclosed Tags: %s' % ', '.join(lines))

    remainder = pyxl_parser.get_remainder()
    if remainder:
        tokens.rewind_and_retokenize(remainder)

    return pyxl_parser.get_token()

########NEW FILE########
__FILENAME__ = element
#!/usr/bin/env python

from pyxl.base import x_base

class x_element(x_base):

    _element = None  # render() output cached by _rendered_element()

    def _get_base_element(self):
        # Adding classes costs ~10%
        out = self._rendered_element()
        # Note: get_class() may return multiple space-separated classes.
        cls = self.get_class()
        classes = set(cls.split(' ')) if cls else set()

        while isinstance(out, x_element):
            new_out = out._rendered_element()
            cls = out.get_class()
            if cls:
                classes.update(cls.split(' '))
            out = new_out

        if classes and isinstance(out, x_base):
            classes.update(out.get_class().split(' '))
            out.set_attr('class', ' '.join(filter(None, classes)))

        return out

    def _to_list(self, l):
        self._render_child_to_list(self._get_base_element(), l)

    def _rendered_element(self):
        if self._element is None:
            self._element = self.render()
        return self._element

    def render(self):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = hello_world
# coding: pyxl

from pyxl import html

print <html><body>Hello World!</body></html>

########NEW FILE########
__FILENAME__ = html
#!/usr/bin/env python

from pyxl.utils import escape
from pyxl.base import x_base

# for backwards compatibility.
from pyxl.browser_hacks import x_cond_comment

_if_condition_stack = []
_last_if_condition = None

def _push_condition(cond):
    _if_condition_stack.append(cond)
    return cond

def _leave_if():
    global _last_if_condition
    _last_if_condition = _if_condition_stack.pop()
    return []

class x_html_element(x_base):
    def _to_list(self, l):
        l.extend((u'<', self.__tag__))
        for name, value in self.__attributes__.iteritems():
            l.extend((u' ', name, u'="', escape(value), u'"'))
        l.append(u'>')

        for child in self.__children__:
            x_base._render_child_to_list(child, l)

        l.extend((u'</', self.__tag__, u'>'))

class x_html_element_nochild(x_base):
    def append(self, child):
        raise Exception('<%s> does not allow children.', self.__tag__)

    def _to_list(self, l):
        l.extend((u'<', self.__tag__))
        for name, value in self.__attributes__.iteritems():
            l.extend((u' ', name, u'="', escape(value), u'"'))
        l.append(u' />')

class x_html_comment(x_base):
    __attrs__ = {
        'comment': unicode,
        }

    def _to_list(self, l):
        pass

class x_html_decl(x_base):
    __attrs__ = {
        'decl': unicode,
        }

    def _to_list(self, l):
        l.extend((u'<!', self.attr('decl'), u'>'))

class x_html_marked_decl(x_base):
    __attrs__ = {
        'decl': unicode,
        }

    def _to_list(self, l):
        l.extend((u'<![', self.attr('decl'), u']]>'))

class x_html_ms_decl(x_base):
    __attrs__ = {
        'decl': unicode,
        }

    def _to_list(self, l):
        l.extend((u'<![', self.attr('decl'), u']>'))

class x_rawhtml(x_html_element_nochild):
    __attrs__= {
        'text': unicode,
        }

    def _to_list(self, l):
        if not isinstance(self.text, unicode):
            l.append(unicode(self.text, 'utf8'))
        else:
            l.append(self.text)

def rawhtml(text):
    return x_rawhtml(text=text)

class x_frag(x_base):
    def _to_list(self, l):
        for child in self.__children__:
            self._render_child_to_list(child, l)

class x_a(x_html_element):
    __attrs__ = {
        'href': unicode,
        'rel': unicode,
        'type': unicode,
        'name': unicode,
        'target': unicode,
        'download': unicode,
        }

class x_abbr(x_html_element):
    pass

class x_acronym(x_html_element):
    pass

class x_address(x_html_element):
    pass

class x_area(x_html_element_nochild):
    __attrs__ = {
        'alt': unicode,
        'coords': unicode,
        'href': unicode,
        'nohref': unicode,
        'target': unicode,
        }

class x_article(x_html_element):
    pass

class x_aside(x_html_element):
    pass

class x_audio(x_html_element):
    __attrs__ = {
        'src': unicode
        }

class x_b(x_html_element):
   pass

class x_big(x_html_element):
   pass

class x_blockquote(x_html_element):
    __attrs__ = {
        'cite': unicode,
        }

class x_body(x_html_element):
    __attrs__ = {
        'contenteditable': unicode,
        }

class x_br(x_html_element_nochild):
   pass

class x_button(x_html_element):
    __attrs__ = {
        'disabled': unicode,
        'name': unicode,
        'type': unicode,
        'value': unicode,
        }

class x_canvas(x_html_element):
    __attrs__ = {
        'height': unicode,
        'width': unicode,
        }

class x_caption(x_html_element):
   pass

class x_cite(x_html_element):
   pass

class x_code(x_html_element):
   pass

class x_col(x_html_element_nochild):
    __attrs__ = {
        'align': unicode,
        'char': unicode,
        'charoff': int,
        'span': int,
        'valign': unicode,
        'width': unicode,
        }

class x_colgroup(x_html_element):
    __attrs__ = {
        'align': unicode,
        'char': unicode,
        'charoff': int,
        'span': int,
        'valign': unicode,
        'width': unicode,
        }

class x_datalist(x_html_element):
    pass

class x_dd(x_html_element):
   pass

class x_del(x_html_element):
    __attrs__ = {
        'cite': unicode,
        'datetime': unicode,
        }

class x_div(x_html_element):
   __attrs__ = {
        'contenteditable': unicode,
       }

class x_dfn(x_html_element):
   pass

class x_dl(x_html_element):
   pass

class x_dt(x_html_element):
   pass

class x_em(x_html_element):
   pass

class x_embed(x_html_element):
    __attrs__ = {
        'src': unicode,
        'width': unicode,
        'height': unicode,
        'allowscriptaccess': unicode,
        'allowfullscreen': unicode,
        'name': unicode,
        'type': unicode,
        }

class x_figure(x_html_element):
   pass

class x_figcaption(x_html_element):
   pass

class x_fieldset(x_html_element):
   pass

class x_footer(x_html_element):
    pass

class x_form(x_html_element):
    __attrs__ = {
        'action': unicode,
        'accept': unicode,
        'accept-charset': unicode,
        'autocomplete': unicode,
        'enctype': unicode,
        'method': unicode,
        'name': unicode,
        'novalidate': unicode,
        'target': unicode,
        }

class x_form_error(x_base):
    __attrs__ = {
        'name': unicode
        }

    def _to_list(self, l):
        l.extend((u'<form:error name="', self.attr('name'), u'" />'))

class x_frame(x_html_element_nochild):
    __attrs__ = {
        'frameborder': unicode,
        'longdesc': unicode,
        'marginheight': unicode,
        'marginwidth': unicode,
        'name': unicode,
        'noresize': unicode,
        'scrolling': unicode,
        'src': unicode,
        }

class x_frameset(x_html_element):
    __attrs__ = {
        'rows': unicode,
        'cols': unicode,
        }

class x_h1(x_html_element):
   pass

class x_h2(x_html_element):
   pass

class x_h3(x_html_element):
   pass

class x_h4(x_html_element):
   pass

class x_h5(x_html_element):
   pass

class x_h6(x_html_element):
   pass

class x_head(x_html_element):
    __attrs__ = {
        'profile': unicode,
        }

class x_header(x_html_element):
    pass

class x_hr(x_html_element_nochild):
    pass

class x_html(x_html_element):
    __attrs__ = {
        'content': unicode,
        'scheme': unicode,
        'http-equiv': unicode,
        'xmlns': unicode,
        'xmlns:og': unicode,
        'xmlns:fb': unicode,
        }

class x_i(x_html_element):
   pass

class x_iframe(x_html_element):
    __attrs__ = {
        'frameborder': unicode,
        'height': unicode,
        'longdesc': unicode,
        'marginheight': unicode,
        'marginwidth': unicode,
        'name': unicode,
        'sandbox': unicode,
        'scrolling': unicode,
        'src': unicode,
        'width': unicode,
        # rk: 'allowTransparency' is not in W3C's HTML spec, but it's supported in most modern browsers.
        'allowtransparency': unicode,
        'allowfullscreen': unicode,
        }

class x_video(x_html_element):
    __attrs__ = {
        'autoplay': unicode,
        'controls': unicode,
        'height': unicode,
        'loop': unicode,
        'muted': unicode,
        'poster': unicode,
        'preload': unicode,
        'src': unicode,
        'width': unicode,
        }

class x_img(x_html_element_nochild):
    __attrs__ = {
        'alt': unicode,
        'src': unicode,
        'height': unicode,
        'ismap': unicode,
        'longdesc': unicode,
        'usemap': unicode,
        'vspace': unicode,
        'width': unicode,
        }

class x_input(x_html_element_nochild):
    __attrs__ = {
        'accept': unicode,
        'align': unicode,
        'alt': unicode,
        'autofocus': unicode,
        'checked': unicode,
        'disabled': unicode,
        'list': unicode,
        'max': unicode,
        'maxlength': unicode,
        'min': unicode,
        'name': unicode,
        'pattern': unicode,
        'placeholder': unicode,
        'readonly': unicode,
        'size': unicode,
        'src': unicode,
        'step': unicode,
        'type': unicode,
        'value': unicode,
        'autocomplete': unicode,
        'autocorrect': unicode,
        'required': unicode,
        'spellcheck': unicode,
        'multiple': unicode,
        }

class x_ins(x_html_element):
    __attrs__ = {
        'cite': unicode,
        'datetime': unicode,
        }

class x_kbd(x_html_element):
    pass

class x_label(x_html_element):
    __attrs__ = {
        'for': unicode,
        }

class x_legend(x_html_element):
   pass

class x_li(x_html_element):
   pass

class x_link(x_html_element_nochild):
    __attrs__ = {
        'charset': unicode,
        'href': unicode,
        'hreflang': unicode,
        'media': unicode,
        'rel': unicode,
        'rev': unicode,
        'sizes': unicode,
        'target': unicode,
        'type': unicode,
        }

class x_main(x_html_element):
    # we are not enforcing the w3 spec of one and only one main element on the
    # page
    __attrs__ = {
        'role': unicode,
    }

class x_map(x_html_element):
    __attrs__ = {
        'name': unicode,
        }

class x_meta(x_html_element_nochild):
    __attrs__ = {
        'content': unicode,
        'http-equiv': unicode,
        'name': unicode,
        'property': unicode,
        'scheme': unicode,
        'charset': unicode,
        }

class x_nav(x_html_element):
    pass

class x_noframes(x_html_element):
   pass

class x_noscript(x_html_element):
   pass

class x_object(x_html_element):
    __attrs__ = {
        'align': unicode,
        'archive': unicode,
        'border': unicode,
        'classid': unicode,
        'codebase': unicode,
        'codetype': unicode,
        'data': unicode,
        'declare': unicode,
        'height': unicode,
        'hspace': unicode,
        'name': unicode,
        'standby': unicode,
        'type': unicode,
        'usemap': unicode,
        'vspace': unicode,
        'width': unicode,
        }

class x_ol(x_html_element):
   pass

class x_optgroup(x_html_element):
    __attrs__ = {
        'disabled': unicode,
        'label': unicode,
        }

class x_option(x_html_element):
    __attrs__ = {
        'disabled': unicode,
        'label': unicode,
        'selected': unicode,
        'value': unicode,
        }

class x_p(x_html_element):
   pass

class x_param(x_html_element):
    __attrs__ = {
        'name': unicode,
        'type': unicode,
        'value': unicode,
        'valuetype': unicode,
        }

class x_pre(x_html_element):
   pass

class x_progress(x_html_element):
    __attrs__ = {
        'max': int,
        'value': int,
    }

class x_q(x_html_element):
    __attrs__ = {
        'cite': unicode,
        }

class x_samp(x_html_element):
   pass

class x_script(x_html_element):
    __attrs__ = {
        'async': unicode,
        'charset': unicode,
        'defer': unicode,
        'src': unicode,
        'type': unicode,
        }

class x_section(x_html_element):
    pass

class x_select(x_html_element):
    __attrs__ = {
        'disabled': unicode,
        'multiple': unicode,
        'name': unicode,
        'size': unicode,
        'required': unicode,
        }

class x_small(x_html_element):
   pass

class x_span(x_html_element):
   pass

class x_strong(x_html_element):
   pass

class x_style(x_html_element):
    __attrs__ = {
        'media': unicode,
        'type': unicode,
        }

class x_sub(x_html_element):
   pass

class x_sup(x_html_element):
   pass

class x_table(x_html_element):
    __attrs__ = {
        'border': unicode,
        'cellpadding': unicode,
        'cellspacing': unicode,
        'frame': unicode,
        'rules': unicode,
        'summary': unicode,
        'width': unicode,
        }

class x_tbody(x_html_element):
    __attrs__ = {
        'align': unicode,
        'char': unicode,
        'charoff': unicode,
        'valign': unicode,
        }

class x_td(x_html_element):
    __attrs__ = {
        'abbr': unicode,
        'align': unicode,
        'axis': unicode,
        'char': unicode,
        'charoff': unicode,
        'colspan': unicode,
        'headers': unicode,
        'rowspan': unicode,
        'scope': unicode,
        'valign': unicode,
        }

class x_textarea(x_html_element):
    __attrs__ = {
        'cols': unicode,
        'rows': unicode,
        'disabled': unicode,
        'placeholder': unicode,
        'name': unicode,
        'readonly': unicode,
        'autocorrect': unicode,
        'autocomplete': unicode,
        'autocapitalize': unicode,
        'spellcheck': unicode,
        'autofocus': unicode,
        'required': unicode,
        }

class x_tfoot(x_html_element):
    __attrs__ = {
        'align': unicode,
        'char': unicode,
        'charoff': unicode,
        'valign': unicode,
        }

class x_th(x_html_element):
    __attrs__ = {
        'abbr': unicode,
        'align': unicode,
        'axis': unicode,
        'char': unicode,
        'charoff': unicode,
        'colspan': unicode,
        'rowspan': unicode,
        'scope': unicode,
        'valign': unicode,
        }

class x_thead(x_html_element):
    __attrs__ = {
        'align': unicode,
        'char': unicode,
        'charoff': unicode,
        'valign': unicode,
        }

class x_time(x_html_element):
    __attrs__ = {
        'datetime': unicode,
        }

class x_title(x_html_element):
   pass

class x_tr(x_html_element):
    __attrs__ = {
        'align': unicode,
        'char': unicode,
        'charoff': unicode,
        'valign': unicode,
        }

class x_tt(x_html_element):
    pass

class x_u(x_html_element):
    pass

class x_ul(x_html_element):
    pass

class x_var(x_html_element):
    pass

########NEW FILE########
__FILENAME__ = rss
import datetime

from pyxl.utils import escape
from pyxl.base import x_base

class x_rss_element(x_base):
    def _to_list(self, l):
        l.extend((u'<', self.__tag__))
        for name, value in self.__attributes__.iteritems():
            name, value = self._handle_attribute(name, value)
            l.extend((u' ', name, u'="', escape(value), u'"'))
        l.append(u'>')

        for child in self.__children__:
            x_base._render_child_to_list(child, l)

        l.extend((u'</', self.__tag__, u'>'))

    def _handle_attribute(self, name, value):
        return (name, value)

class x_rss_decl_standalone(x_base):
    def _to_list(self, l):
        l.append('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')

class x_rss(x_rss_element):
    __attrs__ = {
        'version':unicode,
        'uses-dublin-core':bool
    }

    def _handle_attribute(self, name, value):
        if name == 'uses-dublin-core' and value:
            return ('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
        else:
            return (name, value)

class x_channel(x_rss_element):
    pass

class x_title(x_rss_element):
    pass

class x_link(x_rss_element):
    pass

class x_description(x_rss_element):
    pass

class x_language(x_rss_element):
    pass

class x_rss_date_element(x_base):
    __attrs__ = {
            'date':datetime.datetime
        }

    def _to_list(self, l):
        l.extend((u'<', self.__tag__, '>'))
        l.append(unicode(self.date.strftime('%a, %d %b %Y %H:%M:%S GMT')))
        l.extend((u'</', self.__tag__, u'>'))

class x_lastBuildDate(x_rss_date_element):
    pass

class x_pubDate(x_rss_date_element):
    pass

class x_ttl(x_rss_element):
    pass

class x_item(x_rss_element):
    pass

class x_guid(x_rss_element):
    __attrs__ = {
        'is-perma-link':bool
    }

    def _handle_attribute(self, name, value):
        # This is needed because pyxl doesn't support mixed case attribute names.
        if name == 'is-perma-link':
            return ('isPermaLink', 'true' if value else 'false')
        else:
            return (name, value)

class x_creator(x_rss_element):
    def _to_list(self, l):
        l.append(u'<dc:creator>')
        for child in self.__children__:
            x_base._render_child_to_list(child, l)
        l.append(u'</dc:creator>')

########NEW FILE########
__FILENAME__ = parse_file
#!/usr/bin/env python

import sys
from pyxl.codec.tokenizer import pyxl_tokenize, pyxl_untokenize

f = open(sys.argv[1], 'r')
print pyxl_untokenize(pyxl_tokenize(f.readline)),

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

import xml.sax.saxutils

xml_escape = xml.sax.saxutils.escape
xml_unescape = xml.sax.saxutils.unescape
escape_other = {
    '"': '&quot;',
    }
unescape_other = {
    '&quot;': '"',
    }

def escape(obj):
    return xml_escape(unicode(obj), escape_other)

def unescape(obj):
    return xml_unescape(unicode(obj), unescape_other)

########NEW FILE########
__FILENAME__ = test_attr_name_case
# coding: pyxl
from pyxl import html
def test():
    assert str(<div cLaSs="foo"></div>) == '<div class="foo"></div>'

########NEW FILE########
__FILENAME__ = test_basic
# coding: pyxl
import unittest2
from pyxl import html
from pyxl.base import PyxlException, x_base

class PyxlTests(unittest2.TestCase):

    def test_basics(self):
        self.assertEqual(<div />.to_string(), '<div></div>')
        self.assertEqual(<img src="blah" />.to_string(), '<img src="blah" />')
        self.assertEqual(<div class="c"></div>.to_string(), '<div class="c"></div>')
        self.assertEqual(<div><span></span></div>.to_string(), '<div><span></span></div>')
        self.assertEqual(<frag><span /><span /></frag>.to_string(), '<span></span><span></span>')

    def test_escaping(self):
        self.assertEqual(<div class="&">&{'&'}</div>.to_string(), '<div class="&amp;">&&amp;</div>')
        self.assertEqual(<div>{html.rawhtml('&')}</div>.to_string(), '<div>&</div>')

    def test_comments(self):
        pyxl = (
            <div
                class="blah" # attr comment
                >  # comment1
                <!-- comment2 -->
                text# comment3
                # comment4
            </div>)
        self.assertEqual(pyxl.to_string(), '<div class="blah">text</div>')

    def test_cond_comment(self):
        s = 'blahblah'
        self.assertEqual(
            <cond_comment cond="lt IE 8"><div class=">">{s}</div></cond_comment>.to_string(),
            '<!--[if lt IE 8]><div class="&gt;">blahblah</div><![endif]-->')
        self.assertEqual(
            <cond_comment cond="(lt IE 8) & (gt IE 5)"><div>{s}</div></cond_comment>.to_string(),
            '<!--[if (lt IE 8) & (gt IE 5)]><div>blahblah</div><![endif]-->')

    def test_decl(self):
        self.assertEqual(
            <script><![CDATA[<div><div>]]></script>.to_string(),
            '<script><![CDATA[<div><div>]]></script>')

    def test_form_error(self):
        self.assertEqual(
            <form_error name="foo" />.to_string(),
            '<form:error name="foo" />')

    def test_enum_attrs(self):
        class x_foo(x_base):
            __attrs__ = {
                'value': ['a', 'b'],
            }

            def _to_list(self, l):
                pass

        self.assertEqual(<foo />.attr('value'), 'a')
        self.assertEqual(<foo />.value, 'a')
        self.assertEqual(<foo value="b" />.attr('value'), 'b')
        self.assertEqual(<foo value="b" />.value, 'b')
        with self.assertRaises(PyxlException):
            <foo value="c" />

        class x_bar(x_base):
            __attrs__ = {
                'value': ['a', None, 'b'],
            }

            def _to_list(self, l):
                pass

        with self.assertRaises(PyxlException):
            <bar />.attr('value')

        with self.assertRaises(PyxlException):
            <bar />.value

        class x_baz(x_base):
            __attrs__ = {
                'value': [None, 'a', 'b'],
            }

            def _to_list(self, l):
                pass

        self.assertEqual(<baz />.value, None)

if __name__ == '__main__':
    unittest2.main()

########NEW FILE########
__FILENAME__ = test_curlies_in_attrs_1
# coding: pyxl
from pyxl import html
def test():
    # kannan thinks this should be different
    assert str(<frag><img src="{'foo'}" /></frag>) == """<img src="foo" />"""

########NEW FILE########
__FILENAME__ = test_curlies_in_attrs_2
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag><img src="barbaz{'foo'}" /></frag>) == """<img src="barbazfoo" />"""

########NEW FILE########
__FILENAME__ = test_curlies_in_strings_1
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag> '{'foobar'}' </frag>) == """ 'foobar' """

########NEW FILE########
__FILENAME__ = test_curlies_in_strings_2
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag> "{' "foobar'} </frag>) == ''' " &quot;foobar '''

########NEW FILE########
__FILENAME__ = test_curlies_in_strings_3
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag> "{' "foobar" '}" </frag>) == ''' " &quot;foobar&quot; " '''

########NEW FILE########
__FILENAME__ = test_curlies_in_strings_4
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>"</frag>) + '{}' == '''"{}'''

########NEW FILE########
__FILENAME__ = test_eof_1
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>'''</frag>) == """'''"""

########NEW FILE########
__FILENAME__ = test_errors
from pyxl.codec.register import pyxl_decode
from pyxl.codec.tokenizer import PyxlParseError
from pyxl.codec.parser import ParseError

import os

error_cases_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'error_cases')

def _expect_failure(file_name):
    path = os.path.join(error_cases_path, file_name)
    try:
        with open(path) as f:
            print pyxl_decode(f.read())
        assert False, "successfully decoded file %r" % file_name
    except (PyxlParseError, ParseError):
        pass

def test_error_cases():
    cases = os.listdir(error_cases_path)
    for file_name in cases:
        if file_name.endswith(".txt"):
            yield (_expect_failure, file_name)

########NEW FILE########
__FILENAME__ = test_html_comments_1
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag><!-- comment here --></frag>) == ""

########NEW FILE########
__FILENAME__ = test_html_comments_2
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag><!-- comment-here --></frag>) == ""

########NEW FILE########
__FILENAME__ = test_if_1
# coding: pyxl
from pyxl import html

def test():
    assert str(<frag><if cond="{True}">true</if><else>false</else></frag>) == "true"
    assert str(<frag><if cond="{False}">true</if><else>false</else></frag>) == "false"

########NEW FILE########
__FILENAME__ = test_if_2
# coding: pyxl
from pyxl import html

def test():
    assert str(<frag>
                   <if cond="{True}">true</if>
                   <else>false</else>
               </frag>) == "true"
    assert str(<frag>
                   <if cond="{False}">true</if>
                   <else>false</else>
               </frag>) == "false"

########NEW FILE########
__FILENAME__ = test_if_3
# coding: pyxl
from pyxl import html

def test():
    assert str(<frag>
                   <if cond="{True}">
                       <if cond="{True}">
                           one
                       </if>
                       <else>
                           two
                       </else>
                   </if>
                   <else>
                       <if cond="{True}">
                           three
                       </if>
                       <else>
                           four
                       </else>
                   </else>
               </frag>) == "one"

    assert str(<frag>
                   <if cond="{True}">
                       <if cond="{False}">
                           one
                       </if>
                       <else>
                           two
                       </else>
                   </if>
                   <else>
                       <if cond="{True}">
                           three
                       </if>
                       <else>
                           four
                       </else>
                   </else>
               </frag>) == "two"

    assert str(<frag>
                   <if cond="{False}">
                       <if cond="{False}">
                           one
                       </if>
                       <else>
                           two
                       </else>
                   </if>
                   <else>
                       <if cond="{True}">
                           three
                       </if>
                       <else>
                           four
                       </else>
                   </else>
               </frag>) == "three"

    assert str(<frag>
                   <if cond="{False}">
                       <if cond="{False}">
                           one
                       </if>
                       <else>
                           two
                       </else>
                   </if>
                   <else>
                       <if cond="{False}">
                           three
                       </if>
                       <else>
                           four
                       </else>
                   </else>
               </frag>) == "four"

########NEW FILE########
__FILENAME__ = test_if_4
# coding: pyxl
from pyxl import html

def test():
    count = [0]
    def foo(value):
        count[0] += 1
        return value
    assert str(<frag>
                   <if cond="{foo(True)}">a</if>
                   <else>b</else>
                   {count[0]}
               </frag>) == "a1"

    count[0] = 0
    assert str(<frag>
                   <if cond="{foo(False)}">a</if>
                   <else>b</else>
                   {count[0]}
               </frag>) == "b1"

########NEW FILE########
__FILENAME__ = test_nested_curlies
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{'{text}'}</frag>) == """{text}"""

########NEW FILE########
__FILENAME__ = test_python_comments_1
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>Im cool # lol
</frag>) == """Im cool """

########NEW FILE########
__FILENAME__ = test_python_comments_2
# coding: pyxl
from pyxl import html
def test():
    assert str(<div style="background-color: #1f75cc;"></div>) == """<div style="background-color: #1f75cc;"></div>"""

########NEW FILE########
__FILENAME__ = test_python_comments_3
# coding: pyxl
from pyxl import html
def test():
    assert str(<div #style="display: none;"
               ></div>) == "<div></div>"

########NEW FILE########
__FILENAME__ = test_rss
#coding: pyxl
import datetime

from  unittest2 import TestCase
from pyxl import html
from pyxl import rss

class RssTests(TestCase):
    def test_decl(self):
        decl = <rss.rss_decl_standalone />.to_string()
        self.assertEqual(decl, u'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')

    def test_rss(self):
        r = <rss.rss version="2.0" />.to_string()
        self.assertEqual(r, u'<rss version="2.0"></rss>')

    def test_channel(self):
        c = (
            <rss.rss version="2.0">
                <rss.channel />
            </rss.rss>
        ).to_string()

        self.assertEqual(c, u'<rss version="2.0"><channel></channel></rss>')

    def test_channel_with_required_elements(self):
        channel = (
            <frag>
                <rss.rss_decl_standalone />
                <rss.rss version="2.0">
                    <rss.channel>
                        <rss.title>A Title</rss.title>
                        <rss.link>https://www.dropbox.com</rss.link>
                        <rss.description>A detailed description</rss.description>
                    </rss.channel>
                </rss.rss>
            </frag>
        )

        expected = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<rss version="2.0">
    <channel>
        <title>A Title</title>
        <link>https://www.dropbox.com</link>
        <description>A detailed description</description>
    </channel>
</rss>
'''
        expected = u''.join(l.strip() for l in expected.splitlines())

        self.assertEqual(channel.to_string(), expected)

    def test_channel_with_optional_elements(self):
        channel = (
            <frag>
                <rss.rss_decl_standalone />
                <rss.rss version="2.0">
                    <rss.channel>
                        <rss.title>A Title</rss.title>
                        <rss.link>https://www.dropbox.com</rss.link>
                        <rss.description>A detailed description</rss.description>
                        <rss.ttl>60</rss.ttl>
                        <rss.language>en-us</rss.language>
                    </rss.channel>
                </rss.rss>
            </frag>
        )

        expected = """
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<rss version="2.0">
    <channel>
        <title>A Title</title>
        <link>https://www.dropbox.com</link>
        <description>A detailed description</description>
        <ttl>60</ttl>
        <language>en-us</language>
    </channel>
</rss>
"""

        expected = u''.join(l.strip() for l in expected.splitlines())
        self.assertEqual(channel.to_string(), expected)

    def test_item_with_common_elements(self):
        item = (
            <rss.item>
                <rss.title>Item Title</rss.title>
                <rss.description>
                    {html.rawhtml('<![CDATA[ ')}
                    This is a really interesting description
                    {html.rawhtml(']]>')}
                </rss.description>
                <rss.link>https://www.dropbox.com/somewhere</rss.link>
            </rss.item>
        )

        expected = """
<item>
    <title>Item Title</title>
    <description><![CDATA[  This is a really interesting description ]]></description>
    <link>https://www.dropbox.com/somewhere</link>
</item>
"""

        expected = u''.join(l.strip() for l in expected.splitlines())
        self.assertEqual(item.to_string(), expected)

    def test_guid(self):
        self.assertEqual(<rss.guid>foo</rss.guid>.to_string(), u'<guid>foo</guid>')
        self.assertEqual(<rss.guid is-perma-link="{False}">foo</rss.guid>.to_string(), 
                         u'<guid isPermaLink="false">foo</guid>')
        self.assertEqual(<rss.guid is-perma-link="{True}">foo</rss.guid>.to_string(),
                         u'<guid isPermaLink="true">foo</guid>')

    def test_date_elements(self):
        dt = datetime.datetime(2013, 12, 17, 23, 54, 14)
        self.assertEqual(<rss.pubDate date="{dt}" />.to_string(),
                         u'<pubDate>Tue, 17 Dec 2013 23:54:14 GMT</pubDate>')
        self.assertEqual(<rss.lastBuildDate date="{dt}" />.to_string(),
                         u'<lastBuildDate>Tue, 17 Dec 2013 23:54:14 GMT</lastBuildDate>')

    def test_rss_document(self):
        dt = datetime.datetime(2013, 12, 17, 23, 54, 14)
        dt2 = datetime.datetime(2013, 12, 18, 11, 54, 14)
        doc = (
            <frag>
                <rss.rss_decl_standalone />
                <rss.rss version="2.0">
                    <rss.channel>
                        <rss.title>A Title</rss.title>
                        <rss.link>https://www.dropbox.com</rss.link>
                        <rss.description>A detailed description</rss.description>
                        <rss.ttl>60</rss.ttl>
                        <rss.language>en-us</rss.language>
                        <rss.lastBuildDate date="{dt}" />
                        <rss.item>
                            <rss.title>Item Title</rss.title>
                            <rss.description>
                                {html.rawhtml('<![CDATA[ ')}
                                This is a really interesting description
                                {html.rawhtml(']]>')}
                            </rss.description>
                            <rss.link>https://www.dropbox.com/somewhere</rss.link>
                            <rss.pubDate date="{dt}" />
                            <rss.guid is-perma-link="{False}">123456789</rss.guid>
                        </rss.item>
                        <rss.item>
                            <rss.title>Another Item</rss.title>
                            <rss.description>
                                {html.rawhtml('<![CDATA[ ')}
                                This is another really interesting description
                                {html.rawhtml(']]>')}
                            </rss.description>
                            <rss.link>https://www.dropbox.com/nowhere</rss.link>
                            <rss.pubDate date="{dt2}" />
                            <rss.guid is-perma-link="{False}">ABCDEFGHIJ</rss.guid>
                        </rss.item>
                    </rss.channel>
                </rss.rss>
            </frag>
        )

        expected = """
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<rss version="2.0">
    <channel>
        <title>A Title</title>
        <link>https://www.dropbox.com</link>
        <description>A detailed description</description>
        <ttl>60</ttl>
        <language>en-us</language>
        <lastBuildDate>Tue, 17 Dec 2013 23:54:14 GMT</lastBuildDate>
        <item>
            <title>Item Title</title>
            <description><![CDATA[  This is a really interesting description ]]></description>
            <link>https://www.dropbox.com/somewhere</link>
            <pubDate>Tue, 17 Dec 2013 23:54:14 GMT</pubDate>
            <guid isPermaLink="false">123456789</guid>
        </item>
        <item>
            <title>Another Item</title>
            <description><![CDATA[  This is another really interesting description ]]></description>
            <link>https://www.dropbox.com/nowhere</link>
            <pubDate>Wed, 18 Dec 2013 11:54:14 GMT</pubDate>
            <guid isPermaLink="false">ABCDEFGHIJ</guid>
        </item>
    </channel>
</rss>
"""

        expected = ''.join(l.strip() for l in expected.splitlines())

        self.assertEqual(doc.to_string(), expected)

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_1
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{'<br />'}</frag>) == """&lt;br /&gt;"""

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_10
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{<br /> if False else <div></div>}</frag>) == '''<div></div>'''

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_2
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{'<img src="foo" />'}</frag>) == """&lt;img src=&quot;foo&quot; /&gt;"""

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_3
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{'<div> foobar </div>'}</frag>) == """&lt;div&gt; foobar &lt;/div&gt;"""

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_4
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{'<div class="foo"> foobar </div>'}</frag>) == """&lt;div class=&quot;foo&quot;&gt; foobar &lt;/div&gt;"""

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_5
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag> {'<img src="{cond}" />'} </frag>) == """ &lt;img src=&quot;{cond}&quot; /&gt; """

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_6
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag> {' "<br /> '} </frag>) == '''  &quot;&lt;br /&gt;  '''

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_7
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag> {' "<br />" '} </frag>) == '''  &quot;&lt;br /&gt;&quot;  '''

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_8
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{<br />}</frag>) == '''<br />'''

########NEW FILE########
__FILENAME__ = test_tags_in_curlies_9
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{<br /> if True else <div></div>}</frag>) == '''<br />'''

########NEW FILE########
__FILENAME__ = test_whitespace_1
# coding: pyxl
from pyxl import html
def test():
    assert str(<div class="{'blah'}">
                   blah <a href="%(url)s">blah</a> blah.
               </div>) == """<div class="blah">blah <a href="%(url)s">blah</a> blah.</div>"""

########NEW FILE########
__FILENAME__ = test_whitespace_10
# coding: pyxl
from pyxl import html
def test():
    assert str(<div class="{'foo'} {'bar'}"></div>) == '<div class="foo bar"></div>'

########NEW FILE########
__FILENAME__ = test_whitespace_11
# coding: pyxl
from pyxl import html

def test():
    # Presence of paretheses around html should not affect contents of tags. (In old pyxl,
    # this led to differences in whitespace handling.)
    assert str(get_frag1()) == str(get_frag2())

def get_frag1():
    return <frag>
        {'foo'}
    </frag>

def get_frag2():
    return (<frag>
        {'foo'}
    </frag>)

########NEW FILE########
__FILENAME__ = test_whitespace_12
# coding: pyxl
from pyxl import html
def test():
    # Presence of comments should not affect contents of tags. (In old pyxl, this led to differences
    # in whitespace handling.)
    assert str(get_frag1()) == str(get_frag2())

def get_frag1():
    return <frag>{'foo'}
    </frag>

def get_frag2():
    return <frag>{'foo'} # lol
    </frag>

########NEW FILE########
__FILENAME__ = test_whitespace_2
# coding: pyxl
from pyxl import html
def test():
    assert str(<div>
                   The owner has not granted you access to this file.
               </div>) == """<div>The owner has not granted you access to this file.</div>"""

########NEW FILE########
__FILENAME__ = test_whitespace_3
# coding: pyxl
from pyxl import html
def test():
    a = (<br />)
    b = (<div>
             foo
         </div>)
    assert str(b) == "<div>foo</div>"
    assert a  # pacify lint

########NEW FILE########
__FILENAME__ = test_whitespace_4
# coding: pyxl
from pyxl import html
def test():
    assert str(<div class="{ 'foo' }">foo</div>) == '<div class="foo">foo</div>'

########NEW FILE########
__FILENAME__ = test_whitespace_5
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>
                   {'foo'}
                   {'bar'}
               </frag>) == "foo bar"

########NEW FILE########
__FILENAME__ = test_whitespace_6
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>
                   {'foo'}
                   <if cond="{True}">
                       {'foo'}
                   </if>
               </frag>) == "foofoo"

########NEW FILE########
__FILENAME__ = test_whitespace_7
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>
                   foo
                   {'foo'}
               </frag>) == "foo foo"

########NEW FILE########
__FILENAME__ = test_whitespace_8
# coding: pyxl
from pyxl import html
def test():
    assert str(<frag>{ 'foo' }{ 'foo' }</frag>) == "foofoo"

########NEW FILE########
__FILENAME__ = test_whitespace_9
# coding: pyxl
from pyxl import html
def test():
    assert str(<div class="foo
                           bar">
               </div>) == '<div class="foo bar"></div>'

########NEW FILE########
