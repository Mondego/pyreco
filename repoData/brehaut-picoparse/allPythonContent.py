__FILENAME__ = calculator
#!/usr/bin/env python
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

"""calculator.py - an example of infix expression parsing.

This example shows a simple approach to parsing a recursive infix expression 
using picoparse. It supports the four basic arithmetic operators, integer and 
floating point numbers, negatives, precedence order parenthesis.

The first half of the program defines a small set of syntax tree classes that
will be created by the various parsers. These nodes also know how to evaluate 
themselves.

The second half describes the parser itself. `expression` is the top level 
parser, and is described last as a specialisation of `choice` over binary 
operations and terms.

This parser assumes that whenever a bin_op is encountered, the left item is a 
term, and the right is another complex expression. Operator precedence is 
worked out by asking the node to `merge` with its right hand node. Examine
`bin_op` and `BinaryNode.merge` to see how this works.
"""

from string import digits as digit_chars

from picoparse import compose, p as partial
from picoparse import one_of, many1, choice, tri, commit, optional, fail, follow
from picoparse.text import run_text_parser, lexeme, build_string, whitespace, newline, as_string

# syntax tree classes
operators = ['-','+','*','/']
operator_functions = {
    '-': lambda l, r: l - r,
    '+': lambda l, r: l + r,
    '*': lambda l, r: l * r,
    '/': lambda l, r: l / r,
}
    

class ValueNode(object):
    """This is a leaf node for single numeric values. 
    
    Evaluates to itself, has maximum precedence
    """
    def __init__(self, value):
        self.left = value
        self.precedence = 1000

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.left)
        
    def evaluate(self):
        return self.left


class ParentheticalNode(object):
    """This node encapsulates a child node. 
    
    This node will be merged into BinaryNodes as if it were a single 
    value; This protects parenthesized trees from having order adjusted.   
    """
    def __init__(self, child):
        self.child = child
        self.precedence = 1000
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.child)
    
    def evaluate(self):
        return self.child.evaluate()
        
        
class BinaryNode(object):
    def __init__(self, left, op):
        self.left = left
        self.op = op
        self.right = None
        self.precedence = operators.index(op)
    
    def merge(self, right):
        if self.precedence >= right.precedence:
            self.right = right.left
            right.left = self
            return right
        else:
            self.right = right
            return self

    def __repr__(self):
        return "%s(%r, %r, %r)" % (self.__class__.__name__, self.left, 
                                                            self.op, 
                                                            self.right)
        
    def evaluate(self):
        return operator_functions[self.op](self.left.evaluate(), 
                                           self.right.evaluate())


# parser
digits = partial(lexeme, as_string(partial(many1, partial(one_of, digit_chars))))
operator = partial(lexeme, partial(one_of, operators))
    
@tri
def bin_op():
    left = term()
    op = operator()
    commit()
    right = expression()
    whitespace()
    
    n = BinaryNode(left, op)
    return n.merge(right) 
    
@tri
def parenthetical():
    whitespace()
    one_of('(')
    commit()
    whitespace()
    v = expression()
    whitespace()
    one_of(')')
    whitespace()
    return ParentheticalNode(v)

def int_value():
    return int(digits())

@tri
def float_value():
    whole_part = digits()
    one_of('.')
    commit()
    decimal_part = digits()
    return float('%s.%s' % (whole_part, decimal_part))

def value():
    is_negative = optional(partial(one_of, '-'), False)
    val = choice(float_value, int_value) * (is_negative and -1 or 1)
    return ValueNode(val)

term = partial('term', choice, parenthetical, partial('value', lexeme, value))
    
expression = partial('expression', choice, bin_op, term)

run_calculator = partial(run_text_parser, expression)

def calc(exp):
    tree, _ = run_calculator(exp)
    print exp, '=', tree.evaluate()
    print tree
    print

if __name__ == "__main__":
    exp = True
    while exp:
        exp = raw_input('> ')
        calc(exp)

    
########NEW FILE########
__FILENAME__ = emailaddress
#!/usr/bin/env python
# encoding: utf-8

# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
"""
emailaddress.py

An implentation of rfc 5322 email address checking. 

See http://tools.ietf.org/html/rfc5322 for the full specification. This program
implements the grammer for email address validation in sections 3.4 and 3.4.1 and related
grammers requird by those sections. This is an example of translating a grammer verbatim

Copyright (c) 2009 Andrew Brehaut. All rights reserved.
"""
from string import ascii_letters, digits

from picoparse import one_of, many, many1, not_one_of, run_parser, tri, commit, optional, fail
from picoparse import choice, string, peek, string, eof, many_until, any_token, satisfies
from picoparse import sep, sep1, compose, cue, seq
from picoparse.text import run_text_parser
from picoparse import partial


# generic parsers
def char_range(lower, upper):
    satisfies(lambda c: lower <= ord(c) <= upper)

# character parsers
comma = partial(one_of, ",")
colon = partial(one_of, ":")
semi = partial(one_of, ";")
angle = partial(one_of, "<")
unangle = partial(one_of, ">")
square = partial(one_of, "[")
unsquare = partial(one_of, "]")
paren = partial(one_of, "(")
unparen = partial(one_of, ")")
at = partial(one_of, "@")
dot = partial(one_of, ".")
slash = partial(one_of, "/")
backslash = partial(one_of, "\\")

# common rfc grammers
DQUOTE = partial(one_of, '"') # Double quote
VCHAR = partial(char_range, int('21', 16), int('7E', 16)) # visible (printing) characters
WSP = partial(one_of, " \t") # whitespace
CR = partial(one_of, chr(int('0D', 16))) # carriage return
LF = partial(one_of, chr(int('0A', 16))) # line feed
CRLF = partial(seq, CR, LF) # internet standard new line

# set the obsolete methods to fail
obs_dtext = fail
obs_domain = fail
obs_qtext = fail
obs_qp = fail
obs_local_part = fail
obs_addr_list = fail
obs_mbox_list = fail
obs_group_list = fail
obs_angle_addr = fail
obs_FWS = fail
obs_ctext = fail
obs_phrase = fail

# placeholders
CFWS = None
FWS = None


# Section 3.2.4 Parsers - http://tools.ietf.org/html/rfc5322#section-3.2.3
# qtext           =   %d33 /             ; Printable US-ASCII
#                     %d35-91 /          ;  characters not including
#                     %d93-126 /         ;  "\" or the quote character
#                     obs-qtext
qtext = partial(choice, partial(one_of, chr(33)), 
                        partial(char_range, 35, 91), 
                        partial(char_range, 93, 126),
                        obs_qtext)

# quoted-pair     =   ("\" (VCHAR / WSP)) / obs-qp
quoted_pair = partial(choice, partial(seq, backslash, partial(choice, VCHAR, WSP))
                            , obs_qp)

# qcontent        =   qtext / quoted-pair
qcontent = partial(choice, qtext, quoted_pair)

# quoted-string   =   [CFWS]
#                    DQUOTE *([FWS] qcontent) [FWS] DQUOTE
#                    [CFWS]
def quoted_string():
    optional(CFWS)
    DQUOTE()
    many(partial(seq, partial(optional, FWS), qcontent))
    optional(FWS)
    DQUOTE()
    optional(CFWS)
    

# Section 3.2.2 Parsers - http://tools.ietf.org/html/rfc5322#section-3.2.2
# FWS             =   ([*WSP CRLF] 1*WSP) /  obs-FWS ; Folding white space
FWS = partial(choice, partial(seq, partial(optional, partial(seq, partial(many, WSP), CRLF))
                                 , partial(many1, WSP))
                    , obs_FWS)
# ctext           =   %d33-39 /          ; Printable US-ASCII
#                     %d42-91 /          ;  characters not including
#                     %d93-126 /         ;  "(", ")", or "\"
#                     obs-ctext
ctext = partial(choice, partial(char_range, 33, 39)
                      , partial(char_range, 42, 91)
                      , partial(char_range, 93, 126)
                      , obs_ctext)


# comment         =   "(" *([FWS] ccontent) [FWS] ")"
def comment():
    paren()
    many(partial(seq, partial(optional, FWS), ccontent))
    optional(FWS)

# ccontent        =   ctext / quoted-pair / comment
ccontent = partial(choice, ctext, quoted_pair, comment)

# CFWS            =   (1*([FWS] comment) [FWS]) / FWS    
CFWS = partial(choice, partial(seq, partial(many1, partial(seq, partial(optional, FWS)
                                                              , comment))
                                  , partial(optional, FWS))
                     , FWS)

# Section 3.2.3 Parsers - http://tools.ietf.org/html/rfc5322#section-3.2.3

# atext           =   ALPHA / DIGIT /    ; Printable US-ASCII
#                     "!" / "#" /        ;  characters not including
#                     "$" / "%" /        ;  specials.  Used for atoms.
#                     "&" / "'" /
#                     "*" / "+" /
#                     "-" / "/" /
#                     "=" / "?" /
#                     "^" / "_" /
#                     "`" / "{" /
#                     "|" / "}" /
#                     "~"
atext = partial(one_of, ascii_letters + digits + "!#$%&'*+-/=?^_`{|}~")
atext_string = partial(many1, atext)

# atom            =   [CFWS] 1*atext [CFWS]
def atom():
    optional(CFWS)
    atext_string()
    optional(CFWS)

# dot-atom-text   =   1*atext *("." 1*atext)
dot_atom_text = partial(sep1, atext_string, dot)
    
# dot-atom        =   [CFWS] dot-atom-text [CFWS]
def dot_atom():
    optional(CFWS)
    dot_atom_text()
    optional(CFWS)

# specials        =   "(" / ")" /        ; Special characters that do
#                     "<" / ">" /        ;  not appear in atext
#                     "[" / "]" /
#                     ":" / ";" /
#                     "@" / "\" /
#                     "," / "." /
#                     DQUOTE
specials = partial(one_of, '()<>[]:;@\,."')


# Section 3.2.5 Parsers - http://tools.ietf.org/html/rfc5322#section-3.2.5

# word            =   atom / quoted-string
word = partial(choice, tri(atom), quoted_string)

# phrase          =   1*word / obs-phrase
phrase = partial(choice, tri(partial(many1, word)), obs_phrase)

# Section 3.4.1 Parsers - http://tools.ietf.org/html/rfc5322#section-3.4.1

# dtext           =   %d33-90 /          ; Printable US-ASCII
#                     %d94-126 /         ;  characters not including
#                     obs-dtext          ;  "[", "]", or "\"
dtext = partial(choice, partial(char_range, 33, 99), partial(char_range, 94, 126), obs_dtext)

# domain-literal  =   [CFWS] "[" *([FWS] dtext) [FWS] "]" [CFWS]
def domain_literal():
    optional(CFWS)
    square()
    many(partial(seq, partial(optional, FWS), dtext))
    optional(FWS)
    unsquare()
    optional(CFWS)

# domain          =   dot-atom / domain-literal / obs-domain
domain = partial(choice, dot_atom, domain_literal, obs_domain)

# local-part      =   dot-atom / quoted-string / obs-local-part
local_part = partial(choice, dot_atom, quoted_string, obs_local_part)

# addr-spec       =   local-part "@" domain
addr_spec = partial(seq, local_part, at, domain)



# Section 3.4 Parsers - http://tools.ietf.org/html/rfc5322#section-3.4
address = None # define the reference, allows circular definition
mailbox = None

# address-list    =   (address *("," address)) / obs-addr-list
address_list = tri(partial(choice, partial(seq, address, comma), obs_addr_list))

# mailbox-list    =   (mailbox *("," mailbox)) / obs-mbox-list
mailbox_list = tri(partial(choice, partial(sep, mailbox, comma), obs_mbox_list))

# group-list      =   mailbox-list / CFWS / obs-group-list
group_list = tri(partial(choice, mailbox_list, CFWS, obs_group_list))

# display-name    =   phrase
display_name = tri(phrase)

# group           =   display-name ":" [group-list] ";" [CFWS]
@tri
def group():
    display_name()
    colon()
    optional(group_list)
    semi()  

# angle-addr      =   [CFWS] "<" addr-spec ">" [CFWS] /
#                     obs-angle-addr
@tri
def angle_addr_nonobs():
    optional(CFWS)
    angle()
    addr_spec()
    unangle()
    optional(CFWS)
angle_addr = partial(choice, angle_addr_nonobs, obs_angle_addr)

# name-addr       =   [display-name] angle-addr
@tri
def name_addr():
    optional(display_name)
    angle_addr()

# mailbox         =   name-addr / addr-spec    
mailbox = partial(choice, name_addr, addr_spec)

# address         =   mailbox / group
address = partial(choice, mailbox, group)
 
 
def validate_address(text):
    try: 
        run_text_parser(partial(seq, address, partial(one_of, '\n')), text)
        return True
    except Exception, e:
        print e
        return False
    
import sys
print "address is valid" if validate_address(sys.argv[1]) else "address is not valid"

########NEW FILE########
__FILENAME__ = lambda
#!/usr/bin/env python
# Copyright (c) 2009, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

"""
A parser for a simple programming language.
"""

import sys
from picoparse import choice, p, one_of, many, many1, tri, eof, not_followed_by, satisfies, string, commit, optional, sep1, desc, not_one_of
from picoparse.text import run_text_parser, whitespace

reserved_words = ["let", "in", "fn", "def", "where"]
reserved_operators = ["=", "->"]
operator_chars = "+-*/!<>=@$%^&~|?"

def identifier_char1():
  return satisfies(lambda l: l.isalpha() or l == "_")

def identifier_char():
  return choice(identifier_char1, digit)

def digit():
  return satisfies(lambda l: l.isdigit())

@tri
def number():
  whitespace()
  lead = u''.join(many1(digit))
  commit()
  if optional(p(one_of, '.')):
    trail = u''.join(many1(digit))
    return ('float', float(lead + '.' + trail))
  else:
    return ('int', int(lead))

def string_char(quote):
  char = not_one_of(quote)
  if char == '\\':
    char = any_token()
  return char

@tri
def string_literal():
  whitespace()
  quote = one_of('\'"')
  commit()
  st = u''.join(many1(p(string_char, quote)))
  one_of(quote)
  return ('str', st)

def value():
  return choice(number, string_literal)

@tri
def reserved(name):
  assert name in reserved_words
  whitespace()
  string(name)
  not_followed_by(identifier_char)
  return name

@tri
def identifier():
  whitespace()
  not_followed_by(p(choice, *[p(reserved, rw) for rw in reserved_words]))
  first = identifier_char1()
  commit()
  rest = many(identifier_char)
  name = u''.join([first] + rest)
  return ('ident', name)

def operator_char():
  return one_of(operator_chars)

@tri
def operator():
  whitespace()
  not_followed_by(p(choice, *[p(reserved_op, op) for op in reserved_operators]))
  name = u''.join(many1(operator_char))
  return ('op', name)

@tri
def reserved_op(name):
  assert name in reserved_operators
  whitespace()
  string(name)
  not_followed_by(operator_char)
  return name

@tri
def special(name):
  whitespace()
  string(name)
  return name

def expression():
  expr = choice(eval_expression, let_expression, fn_expression)
  where = optional(where_expression, None)
  if where:
	return ('where', expr, where)
  else:
	return expr

def eval_expression():
  parts = many1(expression_part)
  if len(parts) == 1:
    return parts[0]
  else:
    return ('eval', parts)

def expression_part():
  return choice(value, identifier, operator, parenthetical)

def let_binding():
  name = identifier()
  reserved_op('=')
  expr = expression()
  return ('bind', name, expr)

def let_expression():
  reserved('let')
  bindings = sep1(let_binding, p(special, ','))
  reserved('in')
  expr = expression()
  return ('let', bindings, expr)

def where_expression():
  reserved('where')
  return sep1(let_binding, p(special, ','))

def fn_expression():
  reserved('fn')
  params = many1(identifier)
  reserved_op('->')
  expr = expression()
  return ('fn', params, expr)

def parenthetical():
  special("(")
  expr = expression()
  special(")")
  return expr

def definition():
  reserved('def')
  name = identifier()
  reserved_op('=')
  expr = expression()
  return ('def', name, expr)

def semi():
  return special(';')

def program_part():
  expr = choice(definition, expression)
  optional(semi)
  return expr

def program():
  prog = many(program_part)
  whitespace()
  eof()
  return ('prog', prog)

if __name__ == "__main__":
    text = """
    def fib = fn n ->
        if (n == 0)
            then 0
            else (fib n1 + fib n2)
                where n1 = n - 1, n2 = n1 - 1
    let x = 5, y = 4
    in fib (x * y)
    """
    if len(sys.argv) > 1:
        text = sys.argv[1]
    print run_text_parser(program, text)


########NEW FILE########
__FILENAME__ = paren
#!/usr/bin/env python
"""A simple paren-expression parser."""
# Copyright (c) 2009, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

from picoparse import partial
from picoparse import one_of, optional, many, choice, p, cue
from picoparse.text import run_text_parser, whitespace
import sys


def bracketed():
    one_of('[')
    v = expression()
    one_of(']')
    return ['bracket', v]

def braced():
    one_of('{')
    v = expression()
    one_of('}')
    return ['brace', v]

def parened():
    one_of('(')
    v = expression()
    one_of(')')
    return ['paren', v]

part = p(choice, bracketed, braced, parened)
expression = p('expression', many, part)

if __name__ == "__main__":
    text = ''
    if len(sys.argv) > 1:
        text = sys.argv[1]
    print run_text_parser(p(cue, whitespace, part), text)


########NEW FILE########
__FILENAME__ = paren2
#!/usr/bin/env python
"""This parser is a reworking of paren.py to show how you could build a generalised
parser and specailise it with 'p'"""
# Copyright (c) 2009, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

from picoparse import partial
from picoparse import one_of, optional, many, choice, p, cue
from picoparse.text import run_text_parser, whitespace
import sys

def matched(start, stop, name):
    one_of(start)
    v = expression()
    one_of(stop)
    return [name, v]

bracketed = p(matched, '[', ']', 'bracket')
braced = p(matched, '{', '}', 'brace')
parened = p(matched, '(', ')', 'paren')

part = p(choice, bracketed, braced, parened)
expression = p('expression', many, part)

if __name__ == "__main__":
    text = ''
    if len(sys.argv) > 1:
        text = sys.argv[1]
    print run_text_parser(p(cue, whitespace, part), text)


########NEW FILE########
__FILENAME__ = xml
"""This is a simple _example_ of using picoparse to parse XML - not for real use. 

This example looks at XML as it is a textual stucture that the majority are familiar with. 
Comments throughout the file explain what is going on
"""
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

# We are going to import a lot of parsers and parser combinators from picoparse.
# You dont need to understand them all right away. This style of parser library lends itself 
# to learning and groking small pieces at a time
from picoparse import one_of, many, many1, not_one_of, run_parser, tri, commit, optional, fail
from picoparse import choice, string, peek, string, eof, many_until, any_token, satisfies
from picoparse import sep, sep1, compose, cue
from picoparse.text import build_string, caseless_string, quoted, quote, whitespace, whitespace1
from picoparse.text import lexeme, run_text_parser
from picoparse import partial

# We define common primative parsers by partial application. This is similar to the lexical 
# analysis stage of a more traditional parser tool.
#
# Note here is that these simple parsers are just specialisations of the general purpose
# 'one_of' parser that will accept any item that is the provided iterable.
#   partial(one_of, '<') is equivalent to lambda: one_of('<')
# This is an important idea with picoparse, as it lets you express the specialisation more
# succinctly and more precisely than defing a whole new function 
open_angle = partial(one_of, '<')
close_angle = partial(one_of, '>')
equals = partial(one_of, '=')
decimal_digit = partial(one_of, '0123456789')
hex_decimal_digit = partial(one_of, '0123456789AaBbCcDdEeFf')

# hex_value is a simple parser that knows how to parse out a set of hex digits and return them
# as an integer. build_string wraps up u''.join(iterable) for us. 
def hex_value():
    return int(build_string(many(hex_decimal_digit)), 16)

# The next primatives we need are for the XML name type. The specification for this is reasonably 
# involved; instead of manually implementing it, we are going to create a new parser for the
# grammer that the spec ifself uses. This parser will generate a new parser for us.
#
# To be clear, this piece of code creates a parser that runs when the module is loaded, not when
# parsing the XML itself.
#
# First we are going to create parsers for the individual characters that may appear in the spec,
# then we are going to define parsers for a character range.

# In the XML character spec, a hexdecimal digit begins with '#x'; cue is a parser combinator.
# it takes two parsers, runs the first, and then if that accepts, it runs the second and returns 
# the result. You can see that we are defining a specialisation of cue with a specialisation of 
# string (which only accepts if the input matches the iterable it is given), and hex_value above.
char_spec_hex = partial(cue, partial(string, '#x'), hex_value)

# The next two parsers use a function 'compose' as well as nested partials. This is creating
# a parser that returns a parser. compose(f, g) is equivalent to f(g()). 
char_spec_single_char = compose(partial(partial, one_of), quoted)
char_spec_single_hex_char = compose(partial(partial, one_of), char_spec_hex)

# Now that we have parsers for the different notations for characters, we need to create a parser
# that can choose the correct parser to use. For this we are going to specialise 'choice', This 
# combinator is given a set of parsers to try in order; If a parser fails, it backtracks and tries
# the next, until one succeeds. If none succeed, then the choice fails. 
char_spec_range_char = partial(choice, char_spec_hex, any_token)

# The second part of the character spec is a range. This is more complex that previous parsers
# and we are using a def for it. This parser takes advantage of the previous definition of 
# the char_spec_range_char to find either literal characters or hexdecimal codepoints.
# It returns a new parser specialising 'satisfies'. satisfies takes a function that is called 
# against the input. In this case we are creating a parser that checks that a character is within
# the given range
def char_spec_range():
    one_of("[")
    low = char_spec_range_char()
    one_of('-')
    high = char_spec_range_char()
    one_of("]")
    return partial(satisfies, lambda c: low <= c <= high)

char_spec_seperator = partial(lexeme, partial(one_of, '|'))

# This is the top level parser for the chararacter spec. sep1 is a combinator that finds something
# seperated by something else. In this case it finds one of a range, a single character or a hex 
# character, and the seperator is a '|'. sep and sep1 return a list.
#
# Secondly, note the 'eof()' here. This parser is checking that we have reached the end of the input
#
# The last thing to be aware of is that each of the choices _returns a list of parsers_
def xml_char_spec_parser():
    v = sep1(partial(choice, char_spec_range, char_spec_single_char, char_spec_single_hex_char),
             char_spec_seperator)
    eof()
    return v

# We cant call parsers from outside of a 'run_parser' call. run_parser evaluates the parser function
# you provide over the input you provide, returning the result, and the remainder. Remember that 
# xml_char_spec_parser returns a list of parsers. This function wraps those parses up in a choice.
# This choice parser will accept a single character if it falls within the spec. 
def xml_char_spec(spec, extra_choices=[]):
    parsers, remainder = run_parser(xml_char_spec_parser, spec.strip())
    return partial(choice, *(extra_choices + parsers))

# Finally, we run the xml_char_spec function over the character sets to get two new parsers
# to accept the valid characters for names of elements and attributes. 
name_start_char = xml_char_spec('":" | [A-Z] | "_" | [a-z] | [#xC0-#xD6] | [#xD8-#xF6] | [#xF8-#x2FF] | [#x370-#x37D] | [#x37F-#x1FFF] | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]')
name_char = xml_char_spec('"-" | "." | [0-9] | #xB7 | [#x0300-#x036F] | [#x203F-#x2040]', [name_start_char])

# We return to the parser for XML now, rather than the grammer for xml characers.

# Now that we have those two primatives, we can build a parser that accepts an xml name.
# You can see that a name has one name_start_char, followed by zero or more name_chars
def xml_name():
    return build_string([name_start_char()] + many(name_char))

# Next we define the processing of an entity and then an xml_char, which are used later in node
# definitions. A more sophisticated parser would let additional entities be regestered with 
# directives
named_entities = {
    'amp':'&',
    'quot':'"',
    'apos':"'",
    'lt':'<',
    'gt':'>',
}

# entity is the toplevel parser for &...; notation, it chooses which sub parser to use
def entity():
    one_of('&')
    ent = choice(named_entity, numeric_entity)
    one_of(';')
    return ent

def named_entity():
    name = build_string(many1(partial(not_one_of,';#')))
    if name not in named_entities: fail()
    return named_entities[name]

def hex_entity():
    one_of('x')
    return unichr(hex_value())

def dec_entity():
    return unichr(int(build_string(many1(decimal_digit)), 10))

def numeric_entity():
    one_of('#')
    return choice(hex_entity, dec_entity)

# finally, xml_char is created by partially apply choice to either, normal characters or entities
xml_char = partial(choice, partial(not_one_of, '<>&'), entity)
    
# now we are ready to start implementing the main document parsers.
# xml is our entrypoint parser. The XML spec requires a specific (but optional) prolog
# before the root element node, of which there may only be one. Note that once again
# we are checking reach the end of input.
def xml():
    prolog()
    n = lexeme(element)
    eof()
    return n

def prolog():
    whitespace()
    optional(tri(partial(processing, xmldecl)), None)
    many(partial(choice, processing, comment, whitespace1))
    optional(doctype, None)    
    many(partial(choice, processing, comment, whitespace1))

# The xml declaration could be parsed with a specialised processing directive, or it can be
# handled as a special case. We are going to handle it as a specialisation of the processing.
# our processing directive can optionally be given a parser to provide more detailed handling
# or it will just consume the body 
@tri
def processing(parser = False):
    parser = parser or compose(build_string, partial(many, partial(not_one_of, '?')))

    string('<?')
    commit()
    result = parser()
    whitespace()
    
    string('?>')
    return result

def xmldecl():
    caseless_string('xml')
    whitespace()
    return ('xml', optional(partial(xmldecl_attr, 'version', version_num), "1.0"), 
                   optional(partial(xmldecl_attr, 'standalone', standalone), "yes"))
    
def xmldecl_attr(name, parser):
    string(name)
    lexeme(equals)
    value = quoted(version_num)
    return value

def version_num():
    string('1.')
    return "1." + build_string(many1(decimal_digit))
    
def standalone():
    return choice(partial(string, 'yes'), partial(string, 'no'))

@tri
def comment():
    string("<!--")
    commit()
    result, _ = many_until(any_token, tri(partial(string, "-->")))
    return "COMMENT", build_string(result)

# Node is the general purpose node parser. it wil choose the first parser
# from the set provided that matches the input
def node():
    return choice(processing, element, text_node, comment)

def text_node():
    return "TEXT", build_string(many1(xml_char))

@tri
def doctype():
    string('<!DOCTYPE')
    commit()
    many_until(any_token, close_angle)

@tri
def element():
    open_angle()
    name = xml_name()
    commit()
    attributes = lexeme(partial(sep, attribute, whitespace1))
    return "NODE", name, attributes, choice(closed_element, partial(open_element, name))

def closed_element():
    string('/>')
    return []

def open_element(name):
    close_angle()
    children = many(node)
    end_element(name)
    return children

@tri
def end_element(name):
    whitespace()
    string("</")
    commit()
    if name != xml_name():
        fail()
    whitespace()
    close_angle()

@tri
def attribute():
    name = xml_name()
    commit()
    lexeme(equals)
    return "ATTR", name, quoted()

parse_xml = partial(run_text_parser, xml)

tokens, remaining = parse_xml("""
<?xml version="1.0" ?>
<!DOCTYPE MyDoctype>

<!-- a comment -->
<root>
    <!-- another comment -->
    <self-closing />
    <? this processing is ignored ?>
    <node foo="bar" baz="bo&amp;p'">
        This is some node text &amp; it contains a named entity &#65;nd some &#x41; numeric
    </node>
</root>
""")

print "nodes:", tokens
print
print "remaining:", build_string(remaining)


########NEW FILE########
__FILENAME__ = text
"""Text parsing utilities for picoparse.

These functions exist for convenience; they implement common ideas about text syntax
for instance the quote and quoted parsers assume quotes can be ' or "
"""
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

from string import whitespace as _whitespace_chars

from picoparse import p as partial
from picoparse import string, one_of, many, many1, many_until, any_token, run_parser
from picoparse import NoMatch, fail, tri, EndOfFile, optional, compose

def build_string(iterable):
    """A utility function to wrap up the converting a list of characters back into a string.
    """
    return u''.join(iterable)

as_string = partial(compose, build_string)



quote = partial(one_of, "\"'")
whitespace_char = partial(one_of, _whitespace_chars)
whitespace = as_string(partial(many, whitespace_char))
whitespace1 = as_string(partial(many1, whitespace_char))
newline = partial(one_of, "\n")

def caseless_string(s):
    """Attempts to match input to the letters in the string, without regard for case.
    """
    return string(zip(s.lower(), s.upper()))

def lexeme(parser):
    """Ignores any whitespace surrounding parser.
    """
    whitespace()
    v = parser()
    whitespace()
    return v
    
def quoted(parser=any_token):
    """Parses as much as possible until it encounters a matching closing quote.
    
    By default matches any_token, but can be provided with a more specific parser if required.
    Returns a string
    """
    quote_char = quote()
    value, _ = many_until(parser, partial(one_of, quote_char))
    return build_string(value)

def make_literal(s):
    "returns a literal parser"
    return partial(s, tri(string), s)

def literal(s):
    "A literal string."
    return make_literal(s)()
 
def make_caseless_literal(s):
    "returns a literal string, case independant parser."
    return partial(s, tri(caseless_string), s)

def caseless_literal(s):
    "A literal string, case independant."
    return make_caseless_literal(s)()


class Pos(object):
    def __init__(self, row, col):
        self.row = row
        self.col = col
    
    def __str__(self):
        return str(self.row) + ":" + str(self.col)


class TextDiagnostics(object):
    def __init__(self):
        self.lines = []
        self.row = 1
        self.col = 1
        self.line = []

    def generate_error_message(self, noMatch):
        return noMatch.default_message \
               + "\n" + "\n".join(self.lines)

    def cut(self, p):
        if p == EndOfFile:
            self.lines = []
        else:
            # 1   |  num rows = 5
            # 2 | |
            # 3 | |_ cut (3 rows) (2 discarded from buffer)
            # 4 |                  2 = 3 - (5 - 4)
            # 5 |_ buffer (4 rows)
            buffer_rows = len(self.lines)
            num_rows = self.row - 1
            cut_rows = p.row - 1
            discard_rows = cut_rows - (num_rows - buffer_rows)
            self.lines = self.lines[discard_rows:]

    def wrap(self, stream):
        try:
            while True:
                ch = stream.next()
                self.line.append(ch)
                if ch == '\n':
                    for tok in self.emit_line():
                        yield tok
        except StopIteration:
            for tok in self.emit_line():
                yield tok

    def emit_line(self):
        self.lines.append(u''.join(self.line))
        for ch in self.line:
            yield (ch, Pos(self.row, self.col))
            self.col += 4 if ch == '\t' else 1
        self.row += 1
        self.col = 1
        self.line = []

def run_text_parser(parser, input):
    return run_parser(parser, input, TextDiagnostics())


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

import unittest

from tests import *

if __name__ == "__main__":
    unittest.main()
########NEW FILE########
__FILENAME__ = backend
#!/usr/bin/env python
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

if __name__ == '__main__':
    import sys
    from os import path
    sys.path.insert(0, path.abspath(path.join(path.dirname(sys.argv[0]), '..')))

import unittest

from picoparse import NoMatch, DefaultDiagnostics, BufferWalker
from picoparse import partial as p
from itertools import count, izip

class TestDefaultDiagnostics(unittest.TestCase):
    """Checks some basic operations on the DefaultDiagnostics class
    Eventually this will report errors. For now, there isn't much to test.
    """
    def setUp(self):
        self.diag = DefaultDiagnostics()
        self.i = self.diag.wrap(xrange(1, 6))

    def test_wrap(self):
        for ((a, b), c) in izip(self.i, xrange(1, 6)):
             self.assertEquals(a, c)
             self.assertEquals(b, c)
    
    def test_wrap_len(self):
        self.assertEquals(len(list(self.i)), 5)
    
    def test_tokens(self):
        self.assertEquals(self.diag.tokens, [])
        for (a, b) in self.i:
             self.assertEquals(self.diag.tokens, zip(range(1, a+1),range(1, a+1)))
    
    def test_cut(self):
        self.i.next()
        self.i.next()
        c, p = self.i.next()
        self.diag.cut(p)
        self.assertEquals(self.diag.tokens, [(3,3)])


class TestBufferWalker(unittest.TestCase):
    """Checks all backend parser operations work as expected
    """
    def setUp(self):
        self.input = "abcdefghi"
        self.bw = BufferWalker(self.input, None)

    def test_next(self):
        for c in self.input[1:]:
            self.assertEquals(self.bw.next(), c)
    
    def test_peek(self):
        for c in self.input:
            self.assertEquals(self.bw.peek(), c)
            self.bw.next()
    
    def test_current(self):
        for c, pos in izip(self.input, count(1)):
            self.assertEquals(self.bw.current(), (c, pos))
            self.bw.next()
    
    def test_pos(self):
        for c, pos in izip(self.input, count(1)):
            self.assertEquals(self.bw.pos(), pos)
            self.bw.next()
    
    def test_fail(self):
        self.assertRaises(NoMatch, self.bw.fail)
        self.assertEquals(self.bw.peek(), 'a')
    
    def test_tri_accept(self):
        self.bw.tri(self.bw.next)
        self.assertEquals(self.bw.peek(), 'b')
    
    def test_tri_fail(self):
        def fun():
            self.bw.next()
            self.bw.fail()
        self.assertRaises(NoMatch, p(self.bw.tri, fun))

    def test_commit_multiple(self):
        def multiple_commits():
            self.bw.commit()
            self.bw.commit()
        multiple_commits()
        self.bw.tri(multiple_commits)

    def test_commit_accept(self):
        def fun():
            self.bw.next()
            self.bw.commit()
        self.bw.tri(fun)
        self.assertEquals(self.bw.peek(), 'b')
    
    def test_commit_fail(self):
        def fun():
            self.bw.next()
            self.bw.commit()
            self.bw.fail()
        self.assertRaises(NoMatch, p(self.bw.tri, fun))
        self.assertEquals(self.bw.peek(), 'b')
    
    def test_choice_null(self):
        self.bw.choice()
    
    def test_choice_accept(self):
        self.bw.choice(self.bw.fail, self.bw.next)
        self.bw.choice(self.bw.next, self.bw.fail)
        self.bw.choice(self.bw.next, self.bw.next)
        self.assertEquals(self.bw.peek(), 'd')
    
    def test_choice_fail(self):
        self.assertRaises(NoMatch, p(self.bw.choice, self.bw.fail, self.bw.fail))
    
    def test_choice_commit_fail(self):
        def fun():
            self.bw.next()
            self.bw.commit()
            self.bw.fail()
        self.assertRaises(NoMatch, p(self.bw.choice, fun))
        self.assertEquals(self.bw.peek(), 'b')

if __name__ == '__main__':
    unittest.main()

__all__ = [cls.__name__ for name, cls in locals().items()
                        if isinstance(cls, type) 
                        and name.startswith('Test')]


########NEW FILE########
__FILENAME__ = core_parsers
#!/usr/bin/env python
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

if __name__ == '__main__':
    import sys
    from os import path
    sys.path.insert(0, path.abspath(path.join(path.dirname(sys.argv[0]), '..')))

import unittest

from picoparse import partial as p
from picoparse import run_parser as run, NoMatch
from picoparse import any_token, one_of, not_one_of, satisfies, eof
from picoparse import many, many1, many_until, many_until1, n_of, optional
from picoparse import sep, sep1
from picoparse import cue, follow, seq, string
from picoparse import not_followed_by, remaining

from utils import ParserTestCase

# some simple parsers
nothing = p(one_of, '')
everything= p(not_one_of, '')
one_a = p(one_of, 'a')
not_a = p(not_one_of, 'a')
one_a_or_b = p(one_of, 'ab')
not_a_or_b = p(not_one_of, 'ab')

always_satisfies = p(satisfies, lambda i: True)
never_satisfies = p(satisfies, lambda i: False)
one_b_to_d = p(satisfies, lambda i: 'b' <= i <= 'd')

class TestTokenConsumers(ParserTestCase):
    """This TestCase checks that all the primative token consumers work as expected.
    """
    def testany_token(self):
        self.assertMatch(any_token, 'a', 'a', '')
        self.assertMatch(any_token, 'b', 'b', '')
        self.assertMatch(any_token, 'ab', 'a', 'b')
                
        self.assertNoMatch(any_token, '')
    
    def testone_of(self):
        # matches
        self.assertMatch(one_a, 'a', 'a', '')
        self.assertMatch(one_a_or_b, 'a', 'a', '')
        self.assertMatch(one_a_or_b, 'b', 'b', '')
        self.assertMatch(one_a, 'ac', 'a', 'c')
        self.assertMatch(one_a_or_b, 'ac', 'a', 'c')
        self.assertMatch(one_a_or_b, 'bc', 'b', 'c')
        
        # no match
        self.assertNoMatch(one_a, 'b')
        self.assertNoMatch(one_a_or_b, 'c')
        self.assertNoMatch(one_a, '')
        self.assertNoMatch(one_a_or_b, '')
        self.assertNoMatch(nothing, 'a')
        
    def testnot_one_of(self):
        # matches
        self.assertMatch(not_a, 'b', 'b', '')
        self.assertMatch(not_a_or_b, 'c', 'c', '')
        self.assertMatch(everything, 'a', 'a', '')
        self.assertMatch(everything, 'b', 'b', '')
        self.assertMatch(everything, 'ab', 'a', 'b')
        
        # no match
        self.assertNoMatch(not_a, '')
        self.assertNoMatch(not_a, 'a')
        self.assertNoMatch(not_a_or_b, '')
        self.assertNoMatch(not_a_or_b, 'a')
        self.assertNoMatch(not_a_or_b, 'b')
    
    def testsatisfies(self):
        self.assertMatch(always_satisfies, 'a', 'a', '')
        self.assertMatch(always_satisfies, 'b', 'b', '')
        self.assertNoMatch(always_satisfies, '')

        self.assertNoMatch(never_satisfies, 'a')
        self.assertNoMatch(never_satisfies, 'b')
        self.assertNoMatch(never_satisfies, '')

        self.assertMatch(one_b_to_d, 'b', 'b', '')
        self.assertMatch(one_b_to_d, 'c', 'c', '')
        self.assertMatch(one_b_to_d, 'd', 'd', '')
        self.assertMatch(one_b_to_d, 'bc', 'b', 'c')
        self.assertNoMatch(one_b_to_d, '')
        self.assertNoMatch(one_b_to_d, 'a')
        self.assertNoMatch(one_b_to_d, 'e')

    def testeof(self):
        self.assertMatch(eof, '', None, [])
        self.assertNoMatch(eof, 'a')
        

many_as = p(many, one_a)
at_least_one_a = p(many1, one_a)
one_b = p(one_of, 'b')
some_as_then_b = p(many_until, one_a, one_b)
at_least_one_a_then_b = p(many_until1, one_a, one_b)
three_as = p(n_of, one_a, 3)
zero_or_one_a = p(optional, one_a, None)


class TestManyCombinators(ParserTestCase):
    """Tests the simple many* parser combinators.
    """
    
    def testmany(self):
        self.assertMatch(many_as, '', [], '')
        self.assertMatch(many_as, 'a', ['a'], '')
        self.assertMatch(many_as, 'aa', ['a','a'], '')
        self.assertMatch(many_as, 'aaa', ['a','a', 'a'], '')
    
        self.assertMatch(many_as, 'b', [], 'b')
        self.assertMatch(many_as, 'ab', ['a'], 'b')
        self.assertMatch(many_as, 'aab', ['a','a'], 'b')
        self.assertMatch(many_as, 'aaab', ['a','a','a'], 'b')

    def testmany1(self):
        self.assertNoMatch(at_least_one_a, '')
        self.assertMatch(at_least_one_a, 'a', ['a'], '')
        self.assertMatch(at_least_one_a, 'aa', ['a','a'], '')
        self.assertMatch(at_least_one_a, 'aaa', ['a','a','a'], '')

        self.assertNoMatch(at_least_one_a, 'b')
        self.assertMatch(at_least_one_a, 'ab', ['a'], 'b')
        self.assertMatch(at_least_one_a, 'aab', ['a','a'], 'b')
        self.assertMatch(at_least_one_a, 'aaab', ['a','a','a'], 'b')
    
    def testmany_until(self):
        self.assertMatch(some_as_then_b, 'b', ([], 'b'), '')
        self.assertMatch(some_as_then_b, 'ab', (['a'], 'b'), '')
        self.assertMatch(some_as_then_b, 'aab', (['a','a'], 'b'), '')
        self.assertMatch(some_as_then_b, 'aaab', (['a','a','a'], 'b'), '')
        
        self.assertNoMatch(some_as_then_b, '')
        self.assertNoMatch(some_as_then_b, 'a')
        self.assertNoMatch(some_as_then_b, 'aa')
        
    def testmany_until1(self):
        self.assertNoMatch(at_least_one_a_then_b, 'b')
        self.assertMatch(at_least_one_a_then_b, 'ab', (['a'], 'b'), '')
        self.assertMatch(at_least_one_a_then_b, 'aab', (['a','a'], 'b'), '')
        self.assertMatch(at_least_one_a_then_b, 'aaab', (['a','a','a'], 'b'), '')

        self.assertNoMatch(at_least_one_a_then_b, '')
        self.assertNoMatch(at_least_one_a_then_b, 'a')
        self.assertNoMatch(at_least_one_a_then_b, 'aa')
    
    def testn_of(self):
        self.assertNoMatch(three_as, '')
        self.assertNoMatch(three_as, 'a')
        self.assertNoMatch(three_as, 'aa')
        self.assertMatch(three_as, 'aaa', ['a','a','a'], '')
        self.assertMatch(three_as, 'aaaa', ['a', 'a', 'a'], 'a')
        
        self.assertNoMatch(three_as, 'b')        
        self.assertNoMatch(three_as, 'ab')
        self.assertNoMatch(three_as, 'aab')
    
    def testoptional(self):
        self.assertMatch(zero_or_one_a, '', None, '')
        self.assertMatch(zero_or_one_a, 'a', 'a', '')
        self.assertMatch(zero_or_one_a, 'aa', 'a', 'a')
        self.assertMatch(zero_or_one_a, 'b', None, 'b')


as_sep_by_b = p(sep, one_a, one_b)
one_or_more_as_sep_by_b = p(sep1, one_a, one_b)


class TestSeparatorCombinators(ParserTestCase):
    def testsep(self):
        self.assertMatch(as_sep_by_b, '', [], '')
        self.assertMatch(as_sep_by_b, 'a', ['a'], '')
        self.assertMatch(as_sep_by_b, 'ab', ['a'], 'b')
        self.assertMatch(as_sep_by_b, 'aba', ['a','a'], '')
        self.assertMatch(as_sep_by_b, 'abab', ['a', 'a'], 'b')
        self.assertMatch(as_sep_by_b, 'ababa', ['a','a','a'], '')
        self.assertMatch(as_sep_by_b, 'b', [], 'b')
        self.assertMatch(as_sep_by_b, 'ba', [], 'ba')
        self.assertMatch(as_sep_by_b, 'bab', [], 'bab')
        
    def testsep1(self):
        self.assertNoMatch(one_or_more_as_sep_by_b, '')
        self.assertMatch(one_or_more_as_sep_by_b, 'a', ['a'], '')
        self.assertMatch(one_or_more_as_sep_by_b, 'ab', ['a'], 'b')
        self.assertMatch(one_or_more_as_sep_by_b, 'aba', ['a','a'], '')
        self.assertMatch(one_or_more_as_sep_by_b, 'abab', ['a', 'a'], 'b')
        self.assertMatch(one_or_more_as_sep_by_b, 'ababa', ['a','a','a'], '')
        self.assertNoMatch(one_or_more_as_sep_by_b, 'b')
        self.assertNoMatch(one_or_more_as_sep_by_b, 'ba')
        self.assertNoMatch(one_or_more_as_sep_by_b, 'bab')


a_then_ret_b = p(cue, one_a, one_b)
ret_a_then_b = p(follow, one_a, one_b)
a_then_ab_then_b = p(seq, ('A', one_a), one_a, one_b, ('B', one_b))
abc = p(string, 'abc')
abc_caseless = p(string, ['aA','bB', 'cC'])


class TestSequencingCombinators(ParserTestCase):
    def testcue(self):
        self.assertMatch(a_then_ret_b, 'ab', 'b', [])
        self.assertNoMatch(a_then_ret_b, '')
        self.assertNoMatch(a_then_ret_b, 'a')
        self.assertNoMatch(a_then_ret_b, 'b')
        self.assertMatch(a_then_ret_b, 'aba', 'b', 'a')

    def testfollow(self):
        self.assertMatch(ret_a_then_b, 'ab', 'a', '')
        self.assertNoMatch(ret_a_then_b, '')
        self.assertNoMatch(ret_a_then_b, 'a')
        self.assertNoMatch(ret_a_then_b, 'b')
        self.assertMatch(ret_a_then_b, 'aba', 'a', 'a')

    def testseq(self):
        self.assertNoMatch(a_then_ab_then_b, '')
        self.assertNoMatch(a_then_ab_then_b, 'a')
        self.assertNoMatch(a_then_ab_then_b, 'ab')
        self.assertNoMatch(a_then_ab_then_b, 'aa')
        self.assertNoMatch(a_then_ab_then_b, 'aab')
        self.assertNoMatch(a_then_ab_then_b, 'aaa')
        self.assertNoMatch(a_then_ab_then_b, 'aaba')
        self.assertMatch(a_then_ab_then_b, 'aabb', {'A':'a', 'B':'b'}, '')
        self.assertMatch(a_then_ab_then_b, 'aabba', {'A':'a', 'B':'b'}, 'a')
    
    def teststring(self):
        self.assertMatch(abc, 'abc', ['a','b','c'], '')
        self.assertMatch(abc, 'abca', ['a','b','c'], 'a')
        self.assertNoMatch(abc, '')
        self.assertNoMatch(abc, 'a')
        self.assertNoMatch(abc, 'ab')        
        self.assertNoMatch(abc, 'aa')
        self.assertNoMatch(abc, 'aba')
        self.assertNoMatch(abc, 'abb')
    
        for triple in [(a, b, c) for a in 'aA' for b in 'bB' for c in 'cC']:
            s = u''.join(triple)
            l = list(triple)
            self.assertMatch(abc_caseless, s, l, '')
            s += 'a'
            self.assertMatch(abc_caseless, s, l, 'a')
        self.assertNoMatch(abc_caseless, '')
        

as_then_remaining = p(cue, many_as, remaining)
as_then_not_b = p(follow, many_as, p(not_followed_by, one_b))

        
class TestFuture(ParserTestCase):
    def testremaining(self):
        self.assertMatch(remaining, '', [], '')
        self.assertMatch(as_then_remaining, '', [], '')
        self.assertMatch(as_then_remaining, 'a', [], '')
        self.assertMatch(as_then_remaining, 'aa', [], '')
        self.assertMatch(as_then_remaining, 'b', ['b'], '')
        self.assertMatch(as_then_remaining, 'ab', ['b'], '')
        self.assertMatch(as_then_remaining, 'abb', ['b','b'], '')
        self.assertMatch(as_then_remaining, 'aabb', ['b','b'], '')

    def testnot_followed_By(self):
        self.assertMatch(as_then_not_b, '', [], '')
        self.assertMatch(as_then_not_b, 'a', ['a'], '')
        self.assertMatch(as_then_not_b, 'aa', ['a','a'], '')
        self.assertMatch(as_then_not_b, 'c', [], 'c')
        self.assertMatch(as_then_not_b, 'ac', ['a'], 'c')
        self.assertMatch(as_then_not_b, 'aac', ['a','a'], 'c')
                
        self.assertNoMatch(as_then_not_b, 'b')
        self.assertNoMatch(as_then_not_b, 'ab')
        self.assertNoMatch(as_then_not_b, 'aab')

                        
if __name__ == '__main__':
    unittest.main()

__all__ = [cls.__name__ for name, cls in locals().items()
                        if isinstance(cls, type) 
                        and name.startswith('Test')]

########NEW FILE########
__FILENAME__ = text_parsers
#!/usr/bin/env python
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

if __name__ == '__main__':
    import sys
    from os import path
    sys.path.insert(0, path.abspath(path.join(path.dirname(sys.argv[0]), '..')))

import unittest

import core_parsers
import string
from picoparse import partial as p
from picoparse.text import newline, whitespace_char, whitespace, whitespace1
from picoparse.text import lexeme, quote, quoted, caseless_string, run_text_parser

from utils import TextParserTestCase

class TestTextTokenConsumers(core_parsers.TestTokenConsumers):
    def run_parser(self, *args):
		return run_text_parser(*args)
		
class TestTextManyCombinators(core_parsers.TestManyCombinators):
    def run_parser(self, *args):
		return run_text_parser(*args)

class TestTextSeparatorCombinators(core_parsers.TestSeparatorCombinators):
    def run_parser(self, *args):
		return run_text_parser(*args)

class TestTextSequencingCombinators(core_parsers.TestSequencingCombinators):
    def run_parser(self, *args):
		return run_text_parser(*args)

class TestTextFuture(core_parsers.TestFuture):
    def run_parser(self, *args):
		return run_text_parser(*args)

whitespace_strings = [' ', '  ', '   ', '\n', '\t', '\n \n\r\t\n \t']

class TestWhitespaceParsers(TextParserTestCase):
    def testnewline(self):
        self.assertNoMatch(newline, '')
        self.assertMatch(newline, '\n', '\n', [])
        self.assertMatch(newline, '\n\n', '\n', '\n')
        self.assertNoMatch(newline, '\r\n')
        self.assertNoMatch(newline, '\r')

    def testwhitespace_char(self):
        self.assertNoMatch(whitespace_char, '')
        for ch in string.whitespace:
            self.assertMatch(whitespace_char, ch, ch, '')
            self.assertMatch(whitespace_char, ch + ' ', ch, ' ')
            self.assertMatch(whitespace_char, ch + 'a', ch, 'a')
        self.assertNoMatch(whitespace_char, 'a')

    def testwhitespace(self):
        self.assertMatch(whitespace, 'a', '', 'a')
        for ws in whitespace_strings:
            self.assertMatch(whitespace, ws, ws, '')
            self.assertMatch(whitespace, ws + 'a', ws, 'a')

    def testwhitespace1(self):
        self.assertNoMatch(whitespace1, '')
        self.assertNoMatch(whitespace1, 'a')
        for ws in whitespace_strings:
            self.assertMatch(whitespace1, ws, ws, '')
            self.assertMatch(whitespace1, ws + 'a', ws, 'a')

class TestSimpleParsers(TextParserTestCase):
    def testquote(self):
        self.assertMatch(quote, "'", "'", '')
        self.assertMatch(quote, '"', '"', '')
        self.assertMatch(quote, "'a", "'", 'a')
        self.assertMatch(quote, '"a', '"', 'a')
        self.assertNoMatch(quote, '')
    
    def testdigit(self):
        raise Exception('not implemented')
    
    def testdigits(self):
        raise Exception('not implemented')
        
    def testnumber(self):
        raise Exception('not implemented')
    
    def testfloating(self):
        raise Exception('not implemented')
    
    def testalpha(self):
        raise Exception('not implemented')
    
    def testword(self):
        raise Exception('not implemented')

    def testbuild_string(self):
        raise Exception('not implemented')

    def testas_string(self):
        raise Exception('not implemented')

    def testcaseless_string(self):
        raise Exception('not implemented')

class TestLiterals(TextParserTestCase):
    def make_literal(self):
        raise Exception('not implemented')

    def literal(self):
        raise Exception('not implemented')

    def make_caseless_literal(self):
        raise Exception('not implemented')

    def caseless_literal(self):
        raise Exception('not implemented')

class TestWrappers:
    def testparened(self):
        parened_lit = partial(parened, make_literal('lit'))
        self.testwrapper(parened_lit, "(", "lit", ")")

    def testbraced(self):
        braced_lit = partial(braced, make_literal('lit'))
        self.testwrapper(bracketed_lit, "[", "lit", "]")
        
    def testbraced(self):
        braced_lit = partial(braced, make_literal('lit'))
        self.testwrapper(bracketed_lit, "{", "lit", "}")

    def testquoted(self):
        quoted_quote = partial(quoted, quote)
        self.testwrapper(quoted, "'", 'thing', "'")
        self.testwrapper(quoted, '"', 'thing', '"')
        self.testwrapper(quoted_quote, "'", '"', "'")
        self.testwrapper(quoted_quote, '"', "'", '"')       
        self.assertNoMatch(quoted, '"thing\'')
        self.assertNoMatch(quoted, '\'thing"')
        self.assertNoMatch(quoted_quote, "\"''")
        self.assertNoMatch(quoted_quote, '\'""')

    def testlexeme(self):
        lex_lit = partial(lexeme, make_literal('lit'))
        lex_number = partial(lexeme, digits)
        self.assertMatch(lex_number, '0', '0', '')
        self.assertMatch(lex_number, '0', '0 ', 'a')
        self.assertMatch(lex_lit, 'lit', 'lit', '')
        self.assertMatch(lex_lit, 'lit', 'lit a', 'a')
        for ws1 in whitespace_strings:
            self.assertMatch(lex_lit, ws1 + 'lit', 'lit', '')
            self.assertMatch(lex_number, '1234' + ws1, 1234, '')
            self.assertMatch(lex_number, '1234' + ws1 + 'a', 1234, 'a')
            for ws2 in whitespace_strings:
                self.assertMatch(lex_lit, ws1 + 'lit' + ws2, 'lit', '')
                self.assertMatch(lex_number, ws1 + '1234' + ws2, 1234, '')
                self.assertMatch(lex_number, ws1 + '1234' + ws2 + 'a', 1234, 'a')

        self.assertNoMatch(lex_number, '')
        self.assertNoMatch(lex_lit, '')
        
    def testwrapper(self, parser, before, middle, after):
        self.assertMatch(parser, before + middle + after, middle, '')
        self.assertNoMatch(parser, '')
        self.assertNoMatch(parser, middle)
        self.assertNoMatch(parser, before + middle)
        self.assertNoMatch(parser, middle + after)
        self.assertNoMatch(parser, before + after)


if __name__ == '__main__':
    unittest.main()

__all__ = [cls.__name__ for name, cls in locals().items()
                        if isinstance(cls, type) 
                        and name.startswith('Test')]

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2009, Andrew Brehaut, Steven Ashley
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation  
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

import unittest

from picoparse import partial, NoMatch, run_parser
from picoparse.text import run_text_parser

class ParserTestCase(unittest.TestCase):
    """Allow test cases to specialize
    """
    def run_parser(self, parser, input):
        return run_parser(parser, input)

    """Handles a match
    """
    def assertMatch(self, parser, input, expected, remaining, *args):
        self.assertEquals(self.run_parser(parser, input), (expected, list(remaining)), *args)

    """Handles the common case that a parser doesnt match input.
    """
    def assertNoMatch(self, parser, input, *args):
        self.assertRaises(NoMatch, partial(self.run_parser, parser, input), *args)

class TextParserTestCase(ParserTestCase):
    """Allow test cases to specialize
    """
    def run_parser(self, parser, input):
        return run_text_parser(parser, input)

########NEW FILE########
