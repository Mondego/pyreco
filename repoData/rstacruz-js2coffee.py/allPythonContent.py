__FILENAME__ = builder
import jsparser
import re as regex

class Unsupported(Exception):
  pass

class Code(str):
  """A utility class that extends str with some neato stuff."""

  def __iadd__(self, other):
    """Adds an expression."""
    self = Code(self + other)

    return self

  def __imul__(self, other):
    """Adds a scope."""
    self = Code(self.rstrip() + ("\n  " + regex.sub(r"(\n+)", "\\1  ", other).strip()) + "\n")
    return self

  def __repr__(self):
    import json
    return json.dumps(self, indent=4)

def build(string):
  b = Builder()
  return b.build(string)

class Builder:
  """
  Code builder.

  Common usage:

    b = self.builder()
    b.self.build("var a = 2;")    # string
  """

  def build(self, item):
    # Needs to be a JSParser tree.
    if type(item) == str:
      item = jsparser.parse(item)

    # Get the handler (eg: blocks._bitwise_and)
    kind = "_%s" % item.type.lower()
    fn   = getattr(self, kind) if hasattr(self, kind) else self._other

    return fn(item)

  # The main thing! Always returns a string.
  def _script(self, tree, no_break=False, returnable=False):
    re = Code()

    if len(tree) > 0:
      # Optimize: omit return if not needed.
      if returnable:
        tree[-1].last = True

      # No breaks for switches
      if no_break and tree[-1].type == "BREAK":
        tree = tree[0:-1]

    for i in tree:
      if i.type == "FUNCTION":
        re += self.build(i)

    for i in tree:
      if i.type != "FUNCTION":
        re += self.build(i)

    return re

  _block = _script

  # All of these functions return either a string (expr)
  # or array (statement).

  def _var(self, item):
    re = ""

    for i in item:
      if i.type == "IDENTIFIER":
        if hasattr(i, 'initializer'):
          # var a = ...;
          re += "%s = " % self._id(i.name)
          re += self.build(i.initializer)
          re += "\n"

    return re

  def _function(self, item):
    re = Code()

    # "function name() { ... }" => "name = -> ..."
    if hasattr(item, 'name'):
      re += "%s = " % self._id(item.name)

    if item.params:
      re += "(%s) -> " % ', '.join([ self._param_id(str) for str in item.params 
        ])
    else:
      re += "->"

    re *= self._script(item.body, returnable=True)
    return re

  def _number(self, item):
    return str(item.value)

  def _string(self, item):
    return repr(str(item.value))

  def _semicolon(self, item):
    # Optimize: "alert(2)" should be "alert 2" and omit extra
    # parentheses. Only do this if it's the main statement in
    # the line.
    if item.expression == None:
      return ""

    if not hasattr(item.expression, 'type'):
      print item
      exit()
    if item.expression.type == "CALL":
      return self._call_statement(item.expression) + "\n"

    else:
      return self.build(item.expression) + "\n"

  def _increment(self, item):
    return self.build(item[0]) + "++"

  def _decrement(self, item):
    return self.build(item[0]) + "--"

  def _binary_operator(self, item, operation):
    return ''.join([self.build(item[0]), operation, self.build(item[1])])

  def _unary_operator(self, item, operation):
    return ''.join([operation, self.build(item[0])])

  def _this(self, item):
    return 'this'

  def _instanceof(self, item):
    return self._binary_operator(item, " instanceof ")

  def _plus(self, item):
    return self._binary_operator(item, " + ")

  def _minus(self, item):
    return self._binary_operator(item, " - ")

  def _mul(self, item):
    return self._binary_operator(item, " * ")

  def _div(self, item):
    return self._binary_operator(item, " / ")

  def _mod(self, item):
    return self._binary_operator(item, " % ")

  def _eq(self, item):
    return self._binary_operator(item, " == ")

  def _strict_eq(self, item):
    return self._binary_operator(item, " is ")

  def _strict_ne(self, item):
    return self._binary_operator(item, " isnt ")

  def _lsh(self, item):
    return self._binary_operator(item, " << ")

  def _ursh(self, item):
    return self._binary_operator(item, " >> ")

  def _rsh(self, item):
    return self._binary_operator(item, " >> ")

  def _ne(self, item):
    return self._binary_operator(item, " != ")

  def _lt(self, item):
    return self._binary_operator(item, " < ")

  def _le(self, item):
    return self._binary_operator(item, " <= ")

  def _gt(self, item):
    return self._binary_operator(item, " > ")

  def _ge(self, item):
    return self._binary_operator(item, " >= ")

  def _bitwise_and(self, item):
    return self._binary_operator(item, " & ")

  def _bitwise_or(self, item):
    return self._binary_operator(item, " | ")

  def _bitwise_xor(self, item):
    return self._binary_operator(item, " ^ ")

  def _bitwise_not(self, item):
    return self._unary_operator(item, "~")

  def _and(self, item):
    return self._binary_operator(item, " and ")

  def _or(self, item):
    return self._binary_operator(item, " or ")

  def _in(self, item):
    return self._binary_operator(item, " in ")

  def _new_with_args(self, item):
    return 'new %s(%s)' % (self.build(item[0]), self.build(item[1]))

  def _delete(self, item):
    return "\n".join([("delete %s" % self.build(i)) for i in item]) + "\n"

  def _unary_minus(self, item):
    return '-%s' % self.build(item[0])

  def _unary_plus(self, item):
    return '+%s' % self.build(item[0])

  def _try(self, item):
    re = Code()
    re += "try"
    re *= self.build(item.tryBlock)
    for clause in item.catchClauses:
      re += self.build(clause)
    return re

  def _catch(self, item):
    re = Code()
    re += "catch %s" % item.varName
    re *= self.build(item.block)
    return re

  def _throw(self, item):
    return 'throw %s' % self.build(item.exception)

  def _null(self, item):
    return "null"

  def _other(self, item):
    return "/*%s*/" % (item.type)

  def _group(self, item):
    return '(' + self.build(item[0]) + ')'

  def _return(self, item):
    if hasattr(item, 'last') and item.value != 'return':
      if item.value.type == "CALL":
        return self._call_statement(item.value) + "\n"
      else:
        return self.build(item.value)

    elif item.value == 'return':
      return "return\n"
    else:
      return "return %s\n" % self.build(item.value)

  def _new(self, item):
    return "new %s" % self.build(item[0])

  def _id(self, str):
    # Account for reserved keywords
    if str in ['off', 'on', 'when', 'not', 'until', '__indexOf']:
      # TODO: issue a warning
      return "%s_" % str
    else:
      return str

  # A parameter in a function.
  def _param_id(self, str):
    # Sidestep the usual jQuery thing of doing function($, undefined)
    if str in ['undefined']:
      return "undefined_"
    else:
      return self._id(str)

  def _identifier(self, item):
    return self._id(item.value)

  def _call(self, item):
    if len(item[1]) == 0:
      # alert()
      return self.build(item[0]) + "()"
    else:
      # alert(2)
      params = self.build(item[1])
      if "\n" in params:
        return "%s(%s\n)" % (self.build(item[0]), params)
      else:
        return "%s(%s)" % (self.build(item[0]), params)

  def _call_statement(self, item):
    # "alert(2);" => "alert 2"
    if len(item[1]) > 0:
      return "%s %s" % (self.build(item[0]), self.build(item[1]))

    else:
      return self._call(item)

  def _list(self, item):
    re = Code()

    first = True
    for i in item:

      if not first: re += ", "
      first = False

      if i.type == "OBJECT_INIT":
        re += self._object_init_short(i)
      else:
        re += self.build(i)

    return re.rstrip()

  def _if_short(self, item, then):
    return "%s if %s\n" % (then.strip(), self.build(item.condition).strip())

  def _if(self, item):
    # Optimize: if the 'then' part isn't much of a block, then compress it
    then = self.build(item.thenPart)
    if not item.elsePart and then.count("\n") <= 1:
      return self._if_short(item, then)

    re = Code()
    re += "if %s" % self.build(item.condition)
    re *= self.build(item.thenPart)
    if item.elsePart:
      re += "else "
      re += self.build(item.elsePart)
    return re

  def _true(self, item):
    return "true"

  def _false(self, item):
    return "false"

  def _typeof(self, item):
    return "typeof(%s)" % ( self.build(item[0]) )

  def _dot(self, item):
    if item[0].type == 'THIS':
      return '@%s' % self.build(item[1])
    else:
      return '%s.%s' % ( self.build(item[0]), self.build(item[1]) )

  def _assign(self, item):
    re = Code()
    re += '%s = ' % self.build(item[0])

    # Optimize: hashes in assignments can skip the brackets
    if item[1].type == "OBJECT_INIT":
      re += self._object_init_short(item[1])
    else:
      re += self.build(item[1])
    return re

  def _index(self, item):
    return '%s[%s]' % ( self.build(item[0]), self.build(item[1]) )

  def _label(self, item):
    raise Unsupported("Labels not supported")

  def _object_init(self, item):
    re = Code()
    items = [self.build(i) for i in item]

    if len(items) == 0:
      re = "{}"
    elif len(items) > 1:
      re += "{"
      re *= "\n".join(items)
      re += "}"
    else:
      re += "{%s}" % ", ".join(items)
    return re

  def _object_init_short(self, item):
    re = Code()
    items = [self.build(i) for i in item]

    if len(items) == 0:
      re = "{}"
    elif len(items) > 1:
      re *= "\n".join(items)
    else:
      re += "{%s}" % ", ".join(items)
    return re

  def _property_init(self, item):
    return '%s: %s' % (self.build(item[0]), self.build(item[1]))

  def _array_init(self, item):
    return "[%s]" % ", ".join([self.build(i) for i in item])

  def _for(self, item):
    re = Code()
    if item.setup:
      re += self.build(item.setup) + "\n"

    cond    = self.build(item.condition) if item.condition else "true"
    update  = self.build(item.update)    if item.update    else ""
    body    = self.build(item.body) + update

    re += "while %s" % cond
    re *= body if len(body.strip()) > 0 else "0"
    return re

  def _for_in(self, item):
    re = Code()
    re += "for %s of %s" % (self.build(item.iterator), self.build(item.object))
    body = self.build(item.body)
    re *= body if len(body.strip()) > 0 else "0"
    return re

  def _not(self, item):
    return "not %s" % self.build(item[0])

  def _comma(self, item):
    return "\n".join([self.build(i) for i in item])

  def _regexp(self, item):
    begins_with = item.value['regexp'][0]

    # Workaround for "/ /g" and "/=/" not being parseable.
    if begins_with in [' ', '=']:
      return "RegExp(%s, %s)" % (repr(item.value['regexp']), repr(item.value['modifiers']))

    else:
      return '/%s/%s' % (item.value['regexp'], item.value['modifiers'])

  def _while(self, item):
    re = Code()
    re += "while %s" % self.build(item.condition)
    body = self.build(item.body)
    re *= body if len(body.strip()) > 0 else "0"
    return re

  def _break(self, item):
    return "break\n"

  def _continue(self, item):
    return "continue\n"

  def _switch(self, item):
    disc = self.build(item.discriminant)
    re = Code()
    else_ = ""
    for case in item.cases:
      if hasattr(case, 'caseLabel'):
        re += "%sif %s == %s" % (else_, self.build(case.caseLabel), disc)
        else_ = "else "
      elif case.type == 'DEFAULT':
        re += 'else'
      re *= self._script(case.statements, no_break=True).strip()
    return re

  def _hook(self, item):
    return "(if %s then %s else %s)" % (self.build(item[0]), self.build(item[1]), self.build(item[2]))

  def _void(self, item):
    return '`void 0`'

  def _do(self, item):
    re = Code()
    re += "while true"

    sub = Code()
    sub += self.build(item.body)
    sub += "break unless %s" % self.build(item.condition)

    re *= sub
    return re

########NEW FILE########
__FILENAME__ = jsparser
#!/usr/bin/env python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the Narcissus JavaScript engine, written in Javascript.
#
# The Initial Developer of the Original Code is
# Brendan Eich <brendan@mozilla.org>.
# Portions created by the Initial Developer are Copyright (C) 2004
# the Initial Developer. All Rights Reserved.
#
# The Python version of the code was created by JT Olds <jtolds@xnet5.com>,
# and is a direct translation from the Javascript version.
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK ***** */

"""
 PyNarcissus

 A lexical scanner and parser. JS implemented in JS, ported to Python.
"""

__author__ = "JT Olds"
__author_email__ = "jtolds@xnet5.com"
__date__ = "2009-03-24"
__all__ = ["ParseError", "parse", "tokens"]

import re, sys, types

class Object: pass
class Error_(Exception): pass
class ParseError(Error_): pass

tokens = dict(enumerate((
        # End of source.
        "END",

        # Operators and punctuators. Some pair-wise order matters, e.g. (+, -)
        # and (UNARY_PLUS, UNARY_MINUS).
        "\n", ";",
        ",",
        "=",
        "?", ":", "CONDITIONAL",
        "||",
        "&&",
        "|",
        "^",
        "&",
        "==", "!=", "===", "!==",
        "<", "<=", ">=", ">",
        "<<", ">>", ">>>",
        "+", "-",
        "*", "/", "%",
        "!", "~", "UNARY_PLUS", "UNARY_MINUS",
        "++", "--",
        ".",
        "[", "]",
        "{", "}",
        "(", ")",

        # Nonterminal tree node type codes.
        "SCRIPT", "BLOCK", "LABEL", "FOR_IN", "CALL", "NEW_WITH_ARGS", "INDEX",
        "ARRAY_INIT", "OBJECT_INIT", "PROPERTY_INIT", "GETTER", "SETTER",
        "GROUP", "LIST",

        # Terminals.
        "IDENTIFIER", "NUMBER", "STRING", "REGEXP",

        # Keywords.
        "break",
        "case", "catch", "const", "continue",
        "debugger", "default", "delete", "do",
        "else", "enum",
        "false", "finally", "for", "function",
        "if", "in", "instanceof",
        "new", "null",
        "return",
        "switch",
        "this", "throw", "true", "try", "typeof",
        "var", "void",
        "while", "with")))

# Operator and punctuator mapping from token to tree node type name.
# NB: superstring tokens (e.g., ++) must come before their substring token
# counterparts (+ in the example), so that the opRegExp regular expression
# synthesized from this list makes the longest possible match.
opTypeNames = [
        ('\n',   "NEWLINE"),
        (';',    "SEMICOLON"),
        (',',    "COMMA"),
        ('?',    "HOOK"),
        (':',    "COLON"),
        ('||',   "OR"),
        ('&&',   "AND"),
        ('|',    "BITWISE_OR"),
        ('^',    "BITWISE_XOR"),
        ('&',    "BITWISE_AND"),
        ('===',  "STRICT_EQ"),
        ('==',   "EQ"),
        ('=',    "ASSIGN"),
        ('!==',  "STRICT_NE"),
        ('!=',   "NE"),
        ('<<',   "LSH"),
        ('<=',   "LE"),
        ('<',    "LT"),
        ('>>>',  "URSH"),
        ('>>',   "RSH"),
        ('>=',   "GE"),
        ('>',    "GT"),
        ('++',   "INCREMENT"),
        ('--',   "DECREMENT"),
        ('+',    "PLUS"),
        ('-',    "MINUS"),
        ('*',    "MUL"),
        ('/',    "DIV"),
        ('%',    "MOD"),
        ('!',    "NOT"),
        ('~',    "BITWISE_NOT"),
        ('.',    "DOT"),
        ('[',    "LEFT_BRACKET"),
        (']',    "RIGHT_BRACKET"),
        ('{',    "LEFT_CURLY"),
        ('}',    "RIGHT_CURLY"),
        ('(',    "LEFT_PAREN"),
        (')',    "RIGHT_PAREN"),
    ]

keywords = {}

# Define const END, etc., based on the token names.  Also map name to index.
for i, t in tokens.copy().iteritems():
    if re.match(r'^[a-z]', t):
        const_name = t.upper()
        keywords[t] = i
    elif re.match(r'^\W', t):
        const_name = dict(opTypeNames)[t]
    else:
        const_name = t
    globals()[const_name] = i
    tokens[t] = i

assignOps = {}

# Map assignment operators to their indexes in the tokens array.
for i, t in enumerate(['|', '^', '&', '<<', '>>', '>>>', '+', '-', '*', '/', '%']):
    assignOps[t] = tokens[t]
    assignOps[i] = t

# Build a regexp that recognizes operators and punctuators (except newline).
opRegExpSrc = "^"
for i, j in opTypeNames:
    if i == "\n": continue
    if opRegExpSrc != "^": opRegExpSrc += "|^"
    opRegExpSrc += re.sub(r'[?|^&(){}\[\]+\-*\/\.]', lambda x: "\\%s" % x.group(0), i)
opRegExp = re.compile(opRegExpSrc)

# Convert opTypeNames to an actual dictionary now that we don't care about ordering
opTypeNames = dict(opTypeNames)

# A regexp to match floating point literals (but not integer literals).
fpRegExp = re.compile(r'^\d+\.\d*(?:[eE][-+]?\d+)?|^\d+(?:\.\d*)?[eE][-+]?\d+|^\.\d+(?:[eE][-+]?\d+)?')

# A regexp to match regexp literals.
reRegExp = re.compile(r'^\/((?:\\.|\[(?:\\.|[^\]])*\]|[^\/])+)\/([gimy]*)')

class SyntaxError_(ParseError):
    def __init__(self, message, filename, lineno):
        ParseError.__init__(self, "Syntax error: %s\n%s:%s" %
                (message, filename, lineno))

class Tokenizer(object):
    def __init__(self, s, f, l):
        self.cursor = 0
        self.source = str(s)
        self.tokens = {}
        self.tokenIndex = 0
        self.lookahead = 0
        self.scanNewlines = False
        self.scanOperand = True
        self.filename = f
        self.lineno = l

    input_ = property(lambda self: self.source[self.cursor:])
    done = property(lambda self: self.peek() == END)
    token = property(lambda self: self.tokens.get(self.tokenIndex))

    def match(self, tt):
        return self.get() == tt or self.unget()

    def mustMatch(self, tt):
        if not self.match(tt):
            raise self.newSyntaxError("Missing " + tokens.get(tt).lower())
        return self.token

    def peek(self):
        if self.lookahead:
            next = self.tokens.get((self.tokenIndex + self.lookahead) & 3)
            if self.scanNewlines and (getattr(next, "lineno", None) !=
                    getattr(self, "lineno", None)):
                tt = NEWLINE
            else:
                tt = getattr(next, "type_", None)
        else:
            tt = self.get()
            self.unget()
        return tt

    def peekOnSameLine(self):
        self.scanNewlines = True
        tt = self.peek()
        self.scanNewlines = False
        return tt

    def get(self):
        while self.lookahead:
            self.lookahead -= 1
            self.tokenIndex = (self.tokenIndex + 1) & 3
            token = self.tokens.get(self.tokenIndex)
            if getattr(token, "type_", None) != NEWLINE or self.scanNewlines:
                return getattr(token, "type_", None)

        while True:
            input__ = self.input_
            if self.scanNewlines:
                match = re.match(r'^[ \t]+', input__)
            else:
                match = re.match(r'^\s+', input__)
            if match:
                spaces = match.group(0)
                self.cursor += len(spaces)
                newlines = re.findall(r'\n', spaces)
                if newlines:
                    self.lineno += len(newlines)
                input__ = self.input_

            match = re.match(r'^\/(?:\*(?:.|\n)*?\*\/|\/.*)', input__)
            if not match:
                break
            comment = match.group(0)
            self.cursor += len(comment)
            newlines = re.findall(r'\n', comment)
            if newlines:
                self.lineno += len(newlines)

        self.tokenIndex = (self.tokenIndex + 1) & 3
        token = self.tokens.get(self.tokenIndex)
        if not token:
            token = Object()
            self.tokens[self.tokenIndex] = token

        if not input__:
            token.type_ = END
            return END

        def matchInput():
            match = fpRegExp.match(input__)
            if match:
                token.type_ = NUMBER
                token.value = float(match.group(0))
                return match.group(0)

            match = re.match(r'^0[xX][\da-fA-F]+|^0[0-7]*|^\d+', input__)
            if match:
                token.type_ = NUMBER
                token.value = eval(match.group(0))
                return match.group(0)

            match = re.match(r'^[$_\w]+', input__)       # FIXME no ES3 unicode
            if match:
                id_ = match.group(0)
                token.type_ = keywords.get(id_, IDENTIFIER)
                token.value = id_
                return match.group(0)

            match = re.match(r'^"(?:\\.|[^"])*"|^\'(?:\\.|[^\'])*\'', input__)
            if match:
                token.type_ = STRING
                token.value = eval(match.group(0))
                return match.group(0)

            if self.scanOperand:
                match = reRegExp.match(input__)
                if match:
                    token.type_ = REGEXP
                    token.value = {"regexp": match.group(1),
                                   "modifiers": match.group(2)}
                    return match.group(0)

            match = opRegExp.match(input__)
            if match:
                op = match.group(0)
                if assignOps.has_key(op) and input__[len(op)] == '=':
                    token.type_ = ASSIGN
                    token.assignOp = globals()[opTypeNames[op]]
                    token.value = op
                    return match.group(0) + "="
                token.type_ = globals()[opTypeNames[op]]
                if self.scanOperand and (token.type_ in (PLUS, MINUS)):
                    token.type_ += UNARY_PLUS - PLUS
                token.assignOp = None
                token.value = op
                return match.group(0)

            if self.scanNewlines:
                match = re.match(r'^\n', input__)
                if match:
                    token.type_ = NEWLINE
                    return match.group(0)

            raise self.newSyntaxError("Illegal token")

        token.start = self.cursor
        self.cursor += len(matchInput())
        token.end = self.cursor
        token.lineno = self.lineno
        return getattr(token, "type_", None)

    def unget(self):
        self.lookahead += 1
        if self.lookahead == 4: raise "PANIC: too much lookahead!"
        self.tokenIndex = (self.tokenIndex - 1) & 3

    def newSyntaxError(self, m):
        return SyntaxError_(m, self.filename, self.lineno)

class CompilerContext(object):
    def __init__(self, inFunction):
        self.inFunction = inFunction
        self.stmtStack = []
        self.funDecls = []
        self.varDecls = []
        self.bracketLevel = 0
        self.curlyLevel = 0
        self.parenLevel = 0
        self.hookLevel = 0
        self.ecmaStrictMode = False
        self.inForLoopInit = False

def Script(t, x):
    n = Statements(t, x)
    n.type_ = SCRIPT
    n.funDecls = x.funDecls
    n.varDecls = x.varDecls
    return n

class Node(list):

    def __init__(self, t, type_=None, args=[]):
        list.__init__(self)

        token = t.token
        if token:
            if type_:
                self.type_ = type_
            else:
                self.type_ = getattr(token, "type_", None)
            self.value = token.value
            self.lineno = token.lineno
            self.start = token.start
            self.end = token.end
        else:
            self.type_ = type_
            self.lineno = t.lineno
        self.tokenizer = t

        for arg in args:
            self.append(arg)

    type = property(lambda self: tokenstr(self.type_))

    # Always use push to add operands to an expression, to update start and end.
    def append(self, kid, numbers=[]):
        if kid:
            if hasattr(self, "start") and kid.start < self.start:
                self.start = kid.start
            if hasattr(self, "end") and self.end < kid.end:
                self.end = kid.end
        return list.append(self, kid)

    indentLevel = 0

    def __str__(self):
        a = list((str(i), v) for i, v in enumerate(self))
        for attr in dir(self):
            if attr[0] == "_": continue
            elif attr == "tokenizer":
                a.append((attr, "[object Object]"))
            elif attr in ("append", "count", "extend", "getSource", "index",
                    "insert", "pop", "remove", "reverse", "sort", "type_",
                    "target", "filename", "indentLevel", "type"):
                continue
            else:
                a.append((attr, getattr(self, attr)))
        if len(self): a.append(("length", len(self)))
        a.sort(lambda a, b: cmp(a[0], b[0]))
        INDENTATION = "    "
        Node.indentLevel += 1
        n = Node.indentLevel
        s = "{\n%stype: %s" % ((INDENTATION * n), tokenstr(self.type_))
        for i, value in a:
            s += ",\n%s%s: " % ((INDENTATION * n), i)
            if i == "value" and self.type_ == REGEXP:
                s += "/%s/%s" % (value["regexp"], value["modifiers"])
            elif value is None:
                s += "null"
            elif value is False:
                s += "false"
            elif value is True:
                s += "true"
            elif type(value) == list:
                s += ','.join((str(x) for x in value))
            else:
                s += str(value)
        Node.indentLevel -= 1
        n = Node.indentLevel
        s += "\n%s}" % (INDENTATION * n)
        return s
    __repr__ = __str__

    def getSource(self):
        if getattr(self, "start", None) is not None:
            if getattr(self, "end", None) is not None:
                return self.tokenizer.source[self.start:self.end]
            return self.tokenizer.source[self.start:]
        if getattr(self, "end", None) is not None:
            return self.tokenizer.source[:self.end]
        return self.tokenizer.source[:]

    filename = property(lambda self: self.tokenizer.filename)

    def __nonzero__(self): return True

# Statement stack and nested statement handler.
def nest(t, x, node, func, end=None):
    x.stmtStack.append(node)
    n = func(t, x)
    x.stmtStack.pop()
    if end: t.mustMatch(end)
    return n

def tokenstr(tt):
    t = tokens[tt]
    if re.match(r'^\W', t):
        return opTypeNames[t]
    return t.upper()

def Statements(t, x):
    n = Node(t, BLOCK)
    x.stmtStack.append(n)
    while not t.done and t.peek() != RIGHT_CURLY:
        n.append(Statement(t, x))
    x.stmtStack.pop()
    return n

def Block(t, x):
    t.mustMatch(LEFT_CURLY)
    n = Statements(t, x)
    t.mustMatch(RIGHT_CURLY)
    return n

DECLARED_FORM = 0
EXPRESSED_FORM = 1
STATEMENT_FORM = 2

def Statement(t, x):
    tt = t.get()

    # Cases for statements ending in a right curly return early, avoiding the
    # common semicolon insertion magic after this switch.
    if tt == FUNCTION:
        if len(x.stmtStack) > 1:
            type_ = STATEMENT_FORM
        else:
            type_ = DECLARED_FORM
        return FunctionDefinition(t, x, True, type_)

    elif tt == LEFT_CURLY:
        n = Statements(t, x)
        t.mustMatch(RIGHT_CURLY)
        return n

    elif tt == IF:
        n = Node(t)
        n.condition = ParenExpression(t, x)
        x.stmtStack.append(n)
        n.thenPart = Statement(t, x)
        if t.match(ELSE):
            n.elsePart = Statement(t, x)
        else:
            n.elsePart = None
        x.stmtStack.pop()
        return n

    elif tt == SWITCH:
        n = Node(t)
        t.mustMatch(LEFT_PAREN)
        n.discriminant = Expression(t, x)
        t.mustMatch(RIGHT_PAREN)
        n.cases = []
        n.defaultIndex = -1
        x.stmtStack.append(n)
        t.mustMatch(LEFT_CURLY)
        while True:
            tt = t.get()
            if tt == RIGHT_CURLY: break

            if tt in (DEFAULT, CASE):
                if tt == DEFAULT and n.defaultIndex >= 0:
                    raise t.newSyntaxError("More than one switch default")
                n2 = Node(t)
                if tt == DEFAULT:
                    n.defaultIndex = len(n.cases)
                else:
                    n2.caseLabel = Expression(t, x, COLON)
            else:
                raise t.newSyntaxError("Invalid switch case")
            t.mustMatch(COLON)
            n2.statements = Node(t, BLOCK)
            while True:
                tt = t.peek()
                if(tt == CASE or tt == DEFAULT or tt == RIGHT_CURLY): break
                n2.statements.append(Statement(t, x))
            n.cases.append(n2)
        x.stmtStack.pop()
        return n

    elif tt == FOR:
        n = Node(t)
        n2 = None
        n.isLoop = True
        t.mustMatch(LEFT_PAREN)
        tt = t.peek()
        if tt != SEMICOLON:
            x.inForLoopInit = True
            if tt == VAR or tt == CONST:
                t.get()
                n2 = Variables(t, x)
            else:
                n2 = Expression(t, x)
            x.inForLoopInit = False

        if n2 and t.match(IN):
            n.type_ = FOR_IN
            if n2.type_ == VAR:
                if len(n2) != 1:
                    raise SyntaxError("Invalid for..in left-hand side",
                            t.filename, n2.lineno)

                # NB: n2[0].type_ == INDENTIFIER and n2[0].value == n2[0].name
                n.iterator = n2[0]
                n.varDecl = n2
            else:
                n.iterator = n2
                n.varDecl = None
            n.object = Expression(t, x)
        else:
            if n2:
                n.setup = n2
            else:
                n.setup = None
            t.mustMatch(SEMICOLON)
            if t.peek() == SEMICOLON:
                n.condition = None
            else:
                n.condition = Expression(t, x)
            t.mustMatch(SEMICOLON)
            if t.peek() == RIGHT_PAREN:
                n.update = None
            else:
                n.update = Expression(t, x)
        t.mustMatch(RIGHT_PAREN)
        n.body = nest(t, x, n, Statement)
        return n

    elif tt == WHILE:
        n = Node(t)
        n.isLoop = True
        n.condition = ParenExpression(t, x)
        n.body = nest(t, x, n, Statement)
        return n

    elif tt == DO:
        n = Node(t)
        n.isLoop = True
        n.body = nest(t, x, n, Statement, WHILE)
        n.condition = ParenExpression(t, x)
        if not x.ecmaStrictMode:
            # <script language="JavaScript"> (without version hints) may need
            # automatic semicolon insertion without a newline after do-while.
            # See http://bugzilla.mozilla.org/show_bug.cgi?id=238945.
            t.match(SEMICOLON)
            return n

    elif tt in (BREAK, CONTINUE):
        n = Node(t)
        if t.peekOnSameLine() == IDENTIFIER:
            t.get()
            n.label = t.token.value
        ss = x.stmtStack
        i = len(ss)
        label = getattr(n, "label", None)
        if label:
            while True:
                i -= 1
                if i < 0:
                    raise t.newSyntaxError("Label not found")
                if getattr(ss[i], "label", None) == label: break
        else:
            while True:
                i -= 1
                if i < 0:
                    if tt == BREAK:
                        raise t.newSyntaxError("Invalid break")
                    else:
                        raise t.newSyntaxError("Invalid continue")
                if (getattr(ss[i], "isLoop", None) or (tt == BREAK and
                        ss[i].type_ == SWITCH)):
                    break
        n.target = ss[i]

    elif tt == TRY:
        n = Node(t)
        n.tryBlock = Block(t, x)
        n.catchClauses = []
        while t.match(CATCH):
            n2 = Node(t)
            t.mustMatch(LEFT_PAREN)
            n2.varName = t.mustMatch(IDENTIFIER).value
            if t.match(IF):
                if x.ecmaStrictMode:
                    raise t.newSyntaxError("Illegal catch guard")
                if n.catchClauses and not n.catchClauses[-1].guard:
                    raise t.newSyntaxError("Gaurded catch after unguarded")
                n2.guard = Expression(t, x)
            else:
                n2.guard = None
            t.mustMatch(RIGHT_PAREN)
            n2.block = Block(t, x)
            n.catchClauses.append(n2)
        if t.match(FINALLY):
            n.finallyBlock = Block(t, x)
        if not n.catchClauses and not getattr(n, "finallyBlock", None):
            raise t.newSyntaxError("Invalid try statement")
        return n

    elif tt in (CATCH, FINALLY):
        raise t.newSyntaxError(tokens[tt] + " without preceding try")

    elif tt == THROW:
        n = Node(t)
        n.exception = Expression(t, x)

    elif tt == RETURN:
        if not x.inFunction:
            raise t.newSyntaxError("Invalid return")
        n = Node(t)
        tt = t.peekOnSameLine()
        if tt not in (END, NEWLINE, SEMICOLON, RIGHT_CURLY):
            n.value = Expression(t, x)

    elif tt == WITH:
        n = Node(t)
        n.object = ParenExpression(t, x)
        n.body = nest(t, x, n, Statement)
        return n

    elif tt in (VAR, CONST):
        n = Variables(t, x)

    elif tt == DEBUGGER:
        n = Node(t)

    elif tt in (NEWLINE, SEMICOLON):
        n = Node(t, SEMICOLON)
        n.expression = None
        return n

    else:
        if tt == IDENTIFIER:
            t.scanOperand = False
            tt = t.peek()
            t.scanOperand = True
            if tt == COLON:
                label = t.token.value
                ss = x.stmtStack
                i = len(ss) - 1
                while i >= 0:
                    if getattr(ss[i], "label", None) == label:
                        raise t.newSyntaxError("Duplicate label")
                    i -= 1
                t.get()
                n = Node(t, LABEL)
                n.label = label
                n.statement = nest(t, x, n, Statement)
                return n

        n = Node(t, SEMICOLON)
        t.unget()
        n.expression = Expression(t, x)
        n.end = n.expression.end

    if t.lineno == t.token.lineno:
        tt = t.peekOnSameLine()
        if tt not in (END, NEWLINE, SEMICOLON, RIGHT_CURLY):
            raise t.newSyntaxError("Missing ; before statement")
    t.match(SEMICOLON)
    return n

def FunctionDefinition(t, x, requireName, functionForm):
    f = Node(t)
    if f.type_ != FUNCTION:
        if f.value == "get":
            f.type_ = GETTER
        else:
            f.type_ = SETTER
    if t.match(IDENTIFIER):
        f.name = t.token.value
    elif requireName:
        raise t.newSyntaxError("Missing function identifier")

    t.mustMatch(LEFT_PAREN)
    f.params = []
    while True:
        tt = t.get()
        if tt == RIGHT_PAREN: break
        if tt != IDENTIFIER:
            raise t.newSyntaxError("Missing formal parameter")
        f.params.append(t.token.value)
        if t.peek() != RIGHT_PAREN:
            t.mustMatch(COMMA)

    t.mustMatch(LEFT_CURLY)
    x2 = CompilerContext(True)
    f.body = Script(t, x2)
    t.mustMatch(RIGHT_CURLY)
    f.end = t.token.end

    f.functionForm = functionForm
    if functionForm == DECLARED_FORM:
        x.funDecls.append(f)
    return f

def Variables(t, x):
    n = Node(t)
    while True:
        t.mustMatch(IDENTIFIER)
        n2 = Node(t)
        n2.name = n2.value
        if t.match(ASSIGN):
            if t.token.assignOp:
                raise t.newSyntaxError("Invalid variable initialization")
            n2.initializer = Expression(t, x, COMMA)
        n2.readOnly = not not (n.type_ == CONST)
        n.append(n2)
        x.varDecls.append(n2)
        if not t.match(COMMA): break
    return n

def ParenExpression(t, x):
    t.mustMatch(LEFT_PAREN)
    n = Expression(t, x)
    t.mustMatch(RIGHT_PAREN)
    return n

opPrecedence = {
    "SEMICOLON": 0,
    "COMMA": 1,
    "ASSIGN": 2, "HOOK": 2, "COLON": 2,
    # The above all have to have the same precedence, see bug 330975.
    "OR": 4,
    "AND": 5,
    "BITWISE_OR": 6,
    "BITWISE_XOR": 7,
    "BITWISE_AND": 8,
    "EQ": 9, "NE": 9, "STRICT_EQ": 9, "STRICT_NE": 9,
    "LT": 10, "LE": 10, "GE": 10, "GT": 10, "IN": 10, "INSTANCEOF": 10,
    "LSH": 11, "RSH": 11, "URSH": 11,
    "PLUS": 12, "MINUS": 12,
    "MUL": 13, "DIV": 13, "MOD": 13,
    "DELETE": 14, "VOID": 14, "TYPEOF": 14,
    # "PRE_INCREMENT": 14, "PRE_DECREMENT": 14,
    "NOT": 14, "BITWISE_NOT": 14, "UNARY_PLUS": 14, "UNARY_MINUS": 14,
    "INCREMENT": 15, "DECREMENT": 15,     # postfix
    "NEW": 16,
    "DOT": 17
}

# Map operator type code to precedence
for i in opPrecedence.copy():
    opPrecedence[globals()[i]] = opPrecedence[i]

opArity = {
    "COMMA": -2,
    "ASSIGN": 2,
    "HOOK": 3,
    "OR": 2,
    "AND": 2,
    "BITWISE_OR": 2,
    "BITWISE_XOR": 2,
    "BITWISE_AND": 2,
    "EQ": 2, "NE": 2, "STRICT_EQ": 2, "STRICT_NE": 2,
    "LT": 2, "LE": 2, "GE": 2, "GT": 2, "IN": 2, "INSTANCEOF": 2,
    "LSH": 2, "RSH": 2, "URSH": 2,
    "PLUS": 2, "MINUS": 2,
    "MUL": 2, "DIV": 2, "MOD": 2,
    "DELETE": 1, "VOID": 1, "TYPEOF": 1,
    # "PRE_INCREMENT": 1, "PRE_DECREMENT": 1,
    "NOT": 1, "BITWISE_NOT": 1, "UNARY_PLUS": 1, "UNARY_MINUS": 1,
    "INCREMENT": 1, "DECREMENT": 1,     # postfix
    "NEW": 1, "NEW_WITH_ARGS": 2, "DOT": 2, "INDEX": 2, "CALL": 2,
    "ARRAY_INIT": 1, "OBJECT_INIT": 1, "GROUP": 1
}

# Map operator type code to arity.
for i in opArity.copy():
    opArity[globals()[i]] = opArity[i]

def Expression(t, x, stop=None):
    operators = []
    operands = []
    bl = x.bracketLevel
    cl = x.curlyLevel
    pl = x.parenLevel
    hl = x.hookLevel

    def reduce_():
        n = operators.pop()
        op = n.type_
        arity = opArity[op]
        if arity == -2:
            # Flatten left-associative trees.
            left = (len(operands) >= 2 and operands[-2])
            if left.type_ == op:
                right = operands.pop()
                left.append(right)
                return left
            arity = 2

        # Always use append to add operands to n, to update start and end.
        a = operands[-arity:]
        del operands[-arity:]
        for operand in a:
            n.append(operand)

        # Include closing bracket or postfix operator in [start,end).
        if n.end < t.token.end:
            n.end = t.token.end

        operands.append(n)
        return n

    class BreakOutOfLoops(Exception): pass
    try:
        while True:
            tt = t.get()
            if tt == END: break
            if (tt == stop and x.bracketLevel == bl and x.curlyLevel == cl and
                    x.parenLevel == pl and x.hookLevel == hl):
                # Stop only if tt matches the optional stop parameter, and that
                # token is not quoted by some kind of bracket.
                break
            if tt == SEMICOLON:
                # NB: cannot be empty, Statement handled that.
                raise BreakOutOfLoops

            elif tt in (ASSIGN, HOOK, COLON):
                if t.scanOperand:
                    raise BreakOutOfLoops
                while ((operators and opPrecedence.get(operators[-1].type_,
                        None) > opPrecedence.get(tt)) or (tt == COLON and
                        operators and operators[-1].type_ == ASSIGN)):
                    reduce_()
                if tt == COLON:
                    if operators:
                        n = operators[-1]
                    if not operators or n.type_ != HOOK:
                        raise t.newSyntaxError("Invalid label")
                    x.hookLevel -= 1
                else:
                    operators.append(Node(t))
                    if tt == ASSIGN:
                        operands[-1].assignOp = t.token.assignOp
                    else:
                        x.hookLevel += 1

                t.scanOperand = True

            elif tt in (IN, COMMA, OR, AND, BITWISE_OR, BITWISE_XOR,
                    BITWISE_AND, EQ, NE, STRICT_EQ, STRICT_NE, LT, LE, GE, GT,
                    INSTANCEOF, LSH, RSH, URSH, PLUS, MINUS, MUL, DIV, MOD,
                    DOT):
                # We're treating comma as left-associative so reduce can fold
                # left-heavy COMMA trees into a single array.
                if tt == IN:
                    # An in operator should not be parsed if we're parsing the
                    # head of a for (...) loop, unless it is in the then part of
                    # a conditional expression, or parenthesized somehow.
                    if (x.inForLoopInit and not x.hookLevel and not
                            x.bracketLevel and not x.curlyLevel and
                            not x.parenLevel):
                        raise BreakOutOfLoops
                if t.scanOperand:
                    raise BreakOutOfLoops
                while (operators and opPrecedence.get(operators[-1].type_)
                        >= opPrecedence.get(tt)):
                    reduce_()
                if tt == DOT:
                    t.mustMatch(IDENTIFIER)
                    operands.append(Node(t, DOT, [operands.pop(), Node(t)]))
                else:
                    operators.append(Node(t))
                    t.scanOperand = True

            elif tt in (DELETE, VOID, TYPEOF, NOT, BITWISE_NOT, UNARY_PLUS,
                    UNARY_MINUS, NEW):
                if not t.scanOperand:
                    raise BreakOutOfLoops
                operators.append(Node(t))

            elif tt in (INCREMENT, DECREMENT):
                if t.scanOperand:
                    operators.append(Node(t)) # prefix increment or decrement
                else:
                    # Don't cross a line boundary for postfix {in,de}crement.
                    if (t.tokens.get((t.tokenIndex + t.lookahead - 1)
                            & 3).lineno != t.lineno):
                        raise BreakOutOfLoops

                    # Use >, not >=, so postfix has higher precedence than
                    # prefix.
                    while (operators and opPrecedence.get(operators[-1].type_,
                            None) > opPrecedence.get(tt)):
                        reduce_()
                    n = Node(t, tt, [operands.pop()])
                    n.postfix = True
                    operands.append(n)

            elif tt == FUNCTION:
                if not t.scanOperand:
                    raise BreakOutOfLoops
                operands.append(FunctionDefinition(t, x, False, EXPRESSED_FORM))
                t.scanOperand = False

            elif tt in (NULL, THIS, TRUE, FALSE, IDENTIFIER, NUMBER, STRING,
                    REGEXP):
                if not t.scanOperand:
                    raise BreakOutOfLoops
                operands.append(Node(t))
                t.scanOperand = False

            elif tt == LEFT_BRACKET:
                if t.scanOperand:
                    # Array initializer. Parse using recursive descent, as the
                    # sub-grammer here is not an operator grammar.
                    n = Node(t, ARRAY_INIT)
                    while True:
                        tt = t.peek()
                        if tt == RIGHT_BRACKET: break
                        if tt == COMMA:
                            t.get()
                            n.append(None)
                            continue
                        n.append(Expression(t, x, COMMA))
                        if not t.match(COMMA):
                            break
                    t.mustMatch(RIGHT_BRACKET)
                    operands.append(n)
                    t.scanOperand = False
                else:
                    operators.append(Node(t, INDEX))
                    t.scanOperand = True
                    x.bracketLevel += 1

            elif tt == RIGHT_BRACKET:
                if t.scanOperand or x.bracketLevel == bl:
                    raise BreakOutOfLoops
                while reduce_().type_ != INDEX:
                    continue
                x.bracketLevel -= 1

            elif tt == LEFT_CURLY:
                if not t.scanOperand:
                    raise BreakOutOfLoops
                # Object initializer. As for array initializers (see above),
                # parse using recursive descent.
                x.curlyLevel += 1
                n = Node(t, OBJECT_INIT)

                class BreakOutOfObjectInit(Exception): pass
                try:
                    if not t.match(RIGHT_CURLY):
                        while True:
                            tt = t.get()
                            if ((t.token.value == "get" or
                                    t.token.value == "set") and
                                    t.peek == IDENTIFIER):
                                if x.ecmaStrictMode:
                                    raise t.newSyntaxError("Illegal property "
                                            "accessor")
                                n.append(FunctionDefinition(t, x, True,
                                        EXPRESSED_FORM))
                            else:
                                if tt in (IDENTIFIER, NUMBER, STRING):
                                    id_ = Node(t)
                                elif tt == RIGHT_CURLY:
                                    if x.ecmaStrictMode:
                                        raise t.newSyntaxError("Illegal "
                                                "trailing ,")
                                    raise BreakOutOfObjectInit
                                else:
                                    raise t.newSyntaxError("Invalid property "
                                            "name")
                                t.mustMatch(COLON)
                                n.append(Node(t, PROPERTY_INIT, [id_,
                                        Expression(t, x, COMMA)]))
                            if not t.match(COMMA): break
                        t.mustMatch(RIGHT_CURLY)
                except BreakOutOfObjectInit, e: pass
                operands.append(n)
                t.scanOperand = False
                x.curlyLevel -= 1

            elif tt == RIGHT_CURLY:
                if not t.scanOperand and x.curlyLevel != cl:
                    raise ParseError("PANIC: right curly botch")
                raise BreakOutOfLoops

            elif tt == LEFT_PAREN:
                if t.scanOperand:
                    operators.append(Node(t, GROUP))
                    x.parenLevel += 1
                else:
                    while (operators and
                            opPrecedence.get(operators[-1].type_) >
                            opPrecedence[NEW]):
                        reduce_()

                    # Handle () now, to regularize the n-ary case for n > 0.
                    # We must set scanOperand in case there are arguments and
                    # the first one is a regexp or unary+/-.
                    if operators:
                        n = operators[-1]
                    else:
                        n = Object()
                        n.type_ = None
                    t.scanOperand = True
                    if t.match(RIGHT_PAREN):
                        if n.type_ == NEW:
                            operators.pop()
                            n.append(operands.pop())
                        else:
                            n = Node(t, CALL, [operands.pop(), Node(t, LIST)])
                        operands.append(n)
                        t.scanOperand = False
                    else:
                        if n.type_ == NEW:
                            n.type_ = NEW_WITH_ARGS
                        else:
                            operators.append(Node(t, CALL))
                        x.parenLevel += 1

            elif tt == RIGHT_PAREN:
                if t.scanOperand or x.parenLevel == pl:
                    raise BreakOutOfLoops
                while True:
                    tt = reduce_().type_
                    if tt in (GROUP, CALL, NEW_WITH_ARGS):
                        break
                if tt != GROUP:
                    if operands:
                        n = operands[-1]
                        if n[1].type_ != COMMA:
                            n[1] = Node(t, LIST, [n[1]])
                        else:
                            n[1].type_ = LIST
                    else:
                        raise ParseError, "Unexpected amount of operands"
                x.parenLevel -= 1

            # Automatic semicolon insertion means we may scan across a newline
            # and into the beginning of another statement. If so, break out of
            # the while loop and let the t.scanOperand logic handle errors.
            else:
                raise BreakOutOfLoops
    except BreakOutOfLoops, e: pass

    if x.hookLevel != hl:
        raise t.newSyntaxError("Missing : after ?")
    if x.parenLevel != pl:
        raise t.newSyntaxError("Missing ) in parenthetical")
    if x.bracketLevel != bl:
        raise t.newSyntaxError("Missing ] in index expression")
    if t.scanOperand:
        raise t.newSyntaxError("Missing operand")

    t.scanOperand = True
    t.unget()
    while operators:
        reduce_()
    return operands.pop()

def parse(source, filename=None, starting_line_number=1):
    """Parse some Javascript

    Args:
        source: the Javascript source, as a string
        filename: the filename to include in messages
        starting_line_number: the line number of the first line of the
            passed in source, for output messages
    Returns:
        the parsed source code data structure
    Raises:
        ParseError
    """
    t = Tokenizer(source, filename, starting_line_number)
    x = CompilerContext(False)
    n = Script(t, x)
    if not t.done:
        raise t.newSyntaxError("Syntax error")
    return n

if __name__ == "__main__":
    print str(parse(file(sys.argv[1]).read(),sys.argv[1]))

########NEW FILE########
__FILENAME__ = test
import unittest
import subprocess as sub
import os
import sys

from builder import build

class CoffeeTestCase(unittest.TestCase):
  def setUp(self):
    pass

  def compare(self, js, cs, name=''):
    out = build(js)
    if out.strip() == cs.strip():
      self.assertEqual(out.strip(), cs.strip())
    else:
      print ""
      print "----------------------------------------------------------------------"
      print "%s" % name
      print ""
      print "Output:"
      print "> " + out.strip().replace(' ', '_').replace("\n", "\n> ")
      print ""
      print "Expected:"
      print "> " + cs.strip().replace(' ', '_').replace("\n", "\n> ")
      self.assertTrue(False)

  def compare_file(self, name):
    path = os.path.join(os.path.dirname(__file__), "../test/features/%s" % name)

    js  = file("%s.js" % path).read()
    cs  = file("%s.coffee" % path).read()
    out = "%s.txt" % path

    if os.path.exists(out):
      p = sub.Popen(
          ['coffee', "%s.coffee" % path],
          stdout=sub.PIPE, stderr=sub.PIPE)

      output, errors = p.communicate()
      self.assertEqual(output, file(out).read())

    self.compare(js=js, cs=cs, name=name)


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
from js2coffee.test import CoffeeTestCase

class est(CoffeeTestCase):
  def test_var(self):
    self.compare_file('var')

  def test_for(self):
    self.compare_file('for')

  def test_if(self):
    self.compare_file('if')

  def test_empty_function(self):
    self.compare_file('empty_function')

  def test_equal_regex(self):
    self.compare_file('equal_regex')

  def test_switch(self):
    self.compare_file('switch')

  def test_ternary(self):
    self.compare_file('ternary')

  def test_unary(self):
    self.compare_file('unary')

  def test_throw(self):
    self.compare_file('throw')

  def test_return_function(self):
    self.compare_file('return_function')

  def test_single_return(self):
    self.compare_file('single_return')

  def test_for_in(self):
    self.compare_file('for_in')

  def test_not(self):
    self.compare_file('not')

  def test_instanceof(self):
    self.compare_file('instanceof')

  def test_blank_lines(self):
    self.compare_file('blank_lines')

  def test_void(self):
    self.compare_file('void')

  def test_assignment(self):
    self.compare_file('assignment')

  def test_reserved_words(self):
    self.compare_file('reserved_words')

  def test_index(self):
    self.compare_file('index')

  def test_assignment_condition(self):
    self.compare_file('assignment_condition')

  def test_delete(self):
    self.compare_file('delete')

  def test_do(self):
    self.compare_file('do')

  def test_return_in_if(self):
    self.compare_file('return_in_if')

  def test_call_statement(self):
    self.compare_file('call_statement')

  def test_function_order(self):
    self.compare_file('function_order')

  def test_empty_semicolon(self):
    self.compare_file('empty_semicolon')

  def test_others(self):
    self.compare_file('7')
    self.compare_file('12')
    self.compare_file('14')
    self.compare_file('15')
    self.compare_file('16')
    self.compare_file('17')
    self.compare_file('21')
    self.compare_file('23')

if __name__ == '__main__':
  import unittest
  unittest.main()

########NEW FILE########
__FILENAME__ = __main__
import sys
sys.path.append('..')

from __init__ import *

if __name__ == '__main__':
  import unittest
  unittest.main()

########NEW FILE########
