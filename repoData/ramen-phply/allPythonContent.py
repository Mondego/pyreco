__FILENAME__ = phpast
# ----------------------------------------------------------------------
# phpast.py
#
# PHP abstract syntax node definitions.
# ----------------------------------------------------------------------

class Node(object):
    fields = []

    def __init__(self, *args, **kwargs):
        assert len(self.fields) == len(args), \
            '%s takes %d arguments' % (self.__class__.__name__,
                                       len(self.fields))
        try:
            self.lineno = kwargs['lineno']
        except KeyError:
            self.lineno = None
        for i, field in enumerate(self.fields):
            setattr(self, field, args[i])

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ', '.join([repr(getattr(self, field))
                                      for field in self.fields]))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for field in self.fields:
            if not (getattr(self, field) == getattr(other, field)):
                return False
        return True

    def accept(self, visitor):
        visitor(self)
        for field in self.fields:
            value = getattr(self, field)
            if isinstance(value, Node):
                value.accept(visitor)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Node):
                        item.accept(visitor)

    def generic(self, with_lineno=False):
        values = {}
        if with_lineno:
            values['lineno'] = self.lineno
        for field in self.fields:
            value = getattr(self, field)
            if hasattr(value, 'generic'):
                value = value.generic(with_lineno)
            elif isinstance(value, list):
                items = value
                value = []
                for item in items:
                    if hasattr(item, 'generic'):
                        item = item.generic(with_lineno)
                    value.append(item)
            values[field] = value
        return (self.__class__.__name__, values)

def node(name, fields):
    attrs = {'fields': fields}
    return type(name, (Node,), attrs)

InlineHTML = node('InlineHTML', ['data'])
Block = node('Block', ['nodes'])
Assignment = node('Assignment', ['node', 'expr', 'is_ref'])
ListAssignment = node('ListAssignment', ['nodes', 'expr'])
New = node('New', ['name', 'params'])
Clone = node('Clone', ['node'])
Break = node('Break', ['node'])
Continue = node('Continue', ['node'])
Return = node('Return', ['node'])
Global = node('Global', ['nodes'])
Static = node('Static', ['nodes'])
Echo = node('Echo', ['nodes'])
Print = node('Print', ['node'])
Unset = node('Unset', ['nodes'])
Try = node('Try', ['nodes', 'catches'])
Catch = node('Catch', ['class_', 'var', 'nodes'])
Throw = node('Throw', ['node'])
Declare = node('Declare', ['directives', 'node'])
Directive = node('Directive', ['name', 'node'])
Function = node('Function', ['name', 'params', 'nodes', 'is_ref'])
Method = node('Method', ['name', 'modifiers', 'params', 'nodes', 'is_ref'])
Closure = node('Closure', ['params', 'vars', 'nodes', 'is_ref'])
Class = node('Class', ['name', 'type', 'extends', 'implements', 'nodes'])
ClassConstants = node('ClassConstants', ['nodes'])
ClassConstant = node('ClassConstant', ['name', 'initial'])
ClassVariables = node('ClassVariables', ['modifiers', 'nodes'])
ClassVariable = node('ClassVariable', ['name', 'initial'])
Interface = node('Interface', ['name', 'extends', 'nodes'])
AssignOp = node('AssignOp', ['op', 'left', 'right'])
BinaryOp = node('BinaryOp', ['op', 'left', 'right'])
UnaryOp = node('UnaryOp', ['op', 'expr'])
TernaryOp = node('TernaryOp', ['expr', 'iftrue', 'iffalse'])
PreIncDecOp = node('PreIncDecOp', ['op', 'expr'])
PostIncDecOp = node('PostIncDecOp', ['op', 'expr'])
Cast = node('Cast', ['type', 'expr'])
IsSet = node('IsSet', ['nodes'])
Empty = node('Empty', ['expr'])
Eval = node('Eval', ['expr'])
Include = node('Include', ['expr', 'once'])
Require = node('Require', ['expr', 'once'])
Exit = node('Exit', ['expr'])
Silence = node('Silence', ['expr'])
MagicConstant = node('MagicConstant', ['name', 'value'])
Constant = node('Constant', ['name'])
Variable = node('Variable', ['name'])
StaticVariable = node('StaticVariable', ['name', 'initial'])
LexicalVariable = node('LexicalVariable', ['name', 'is_ref'])
FormalParameter = node('FormalParameter', ['name', 'default', 'is_ref', 'type'])
Parameter = node('Parameter', ['node', 'is_ref'])
FunctionCall = node('FunctionCall', ['name', 'params'])
Array = node('Array', ['nodes'])
ArrayElement = node('ArrayElement', ['key', 'value', 'is_ref'])
ArrayOffset = node('ArrayOffset', ['node', 'expr'])
StringOffset = node('StringOffset', ['node', 'expr'])
ObjectProperty = node('ObjectProperty', ['node', 'name'])
StaticProperty = node('StaticProperty', ['node', 'name'])
MethodCall = node('MethodCall', ['node', 'name', 'params'])
StaticMethodCall = node('StaticMethodCall', ['class_', 'name', 'params'])
If = node('If', ['expr', 'node', 'elseifs', 'else_'])
ElseIf = node('ElseIf', ['expr', 'node'])
Else = node('Else', ['node'])
While = node('While', ['expr', 'node'])
DoWhile = node('DoWhile', ['node', 'expr'])
For = node('For', ['start', 'test', 'count', 'node'])
Foreach = node('Foreach', ['expr', 'keyvar', 'valvar', 'node'])
ForeachVariable = node('ForeachVariable', ['name', 'is_ref'])
Switch = node('Switch', ['expr', 'nodes'])
Case = node('Case', ['expr', 'nodes'])
Default = node('Default', ['nodes'])
Namespace = node('Namespace', ['name', 'nodes'])
UseDeclarations = node('UseDeclarations', ['nodes'])
UseDeclaration = node('UseDeclaration', ['name', 'alias'])
ConstantDeclarations = node('ConstantDeclarations', ['nodes'])
ConstantDeclaration = node('ConstantDeclaration', ['name', 'initial'])

def resolve_magic_constants(nodes):
    current = {}
    def visitor(node):
        if isinstance(node, Namespace):
            current['namespace'] = node.name
        elif isinstance(node, Class):
            current['class'] = node.name
        elif isinstance(node, Function):
            current['function'] = node.name
        elif isinstance(node, Method):
            current['method'] = node.name
        elif isinstance(node, MagicConstant):
            if node.name == '__NAMESPACE__':
                node.value = current.get('namespace')
            elif node.name == '__CLASS__':
                node.value = current.get('class')
                if current.get('namespace'):
                    node.value = '%s\\%s' % (current.get('namespace'),
                                             node.value)
            elif node.name == '__FUNCTION__':
                node.value = current.get('function')
                if current.get('namespace'):
                    node.value = '%s\\%s' % (current.get('namespace'),
                                             node.value)
            elif node.name == '__METHOD__':
                node.value = current.get('method')
                if current.get('class'):
                    node.value = '%s::%s' % (current.get('class'),
                                             node.value)
                if current.get('namespace'):
                    node.value = '%s\\%s' % (current.get('namespace'),
                                             node.value)
    for node in nodes:
        if isinstance(node, Node):
            node.accept(visitor)

########NEW FILE########
__FILENAME__ = phplex
# ----------------------------------------------------------------------
# phplex.py
#
# A lexer for PHP.
# ----------------------------------------------------------------------

import ply.lex as lex
import re

# todo: nowdocs
# todo: backticks
# todo: binary string literals and casts
# todo: BAD_CHARACTER
# todo: <script> syntax (does anyone use this?)

states = (
    ('php', 'exclusive'),
    ('quoted', 'exclusive'),
    ('quotedvar', 'exclusive'),
    ('varname', 'exclusive'),
    ('offset', 'exclusive'),
    ('property', 'exclusive'),
    ('heredoc', 'exclusive'),
    ('heredocvar', 'exclusive'),
)

# Reserved words
reserved = (
    'ARRAY', 'AS', 'BREAK', 'CASE', 'CLASS', 'CONST', 'CONTINUE', 'DECLARE',
    'DEFAULT', 'DO', 'ECHO', 'ELSE', 'ELSEIF', 'EMPTY', 'ENDDECLARE',
    'ENDFOR', 'ENDFOREACH', 'ENDIF', 'ENDSWITCH', 'ENDWHILE', 'EVAL', 'EXIT',
    'EXTENDS', 'FOR', 'FOREACH', 'FUNCTION', 'GLOBAL', 'IF', 'INCLUDE',
    'INCLUDE_ONCE', 'INSTANCEOF', 'ISSET', 'LIST', 'NEW', 'PRINT', 'REQUIRE',
    'REQUIRE_ONCE', 'RETURN', 'STATIC', 'SWITCH', 'UNSET', 'USE', 'VAR',
    'WHILE', 'FINAL', 'INTERFACE', 'IMPLEMENTS', 'PUBLIC', 'PRIVATE',
    'PROTECTED', 'ABSTRACT', 'CLONE', 'TRY', 'CATCH', 'THROW', 'NAMESPACE',
)

# Not used by parser
unparsed = (
    # Invisible characters
    'WHITESPACE',

    # Open and close tags
    'OPEN_TAG', 'OPEN_TAG_WITH_ECHO', 'CLOSE_TAG',

    # Comments
    'COMMENT', 'DOC_COMMENT',
)

tokens = reserved + unparsed + (
    # Operators
    'PLUS', 'MINUS', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'NOT', 'XOR', 'SL',
    'SR', 'BOOLEAN_AND', 'BOOLEAN_OR', 'BOOLEAN_NOT', 'IS_SMALLER',
    'IS_GREATER', 'IS_SMALLER_OR_EQUAL', 'IS_GREATER_OR_EQUAL', 'IS_EQUAL',
    'IS_NOT_EQUAL', 'IS_IDENTICAL', 'IS_NOT_IDENTICAL',

    # Assignment operators
    'EQUALS', 'MUL_EQUAL', 'DIV_EQUAL', 'MOD_EQUAL', 'PLUS_EQUAL',
    'MINUS_EQUAL', 'SL_EQUAL', 'SR_EQUAL', 'AND_EQUAL', 'OR_EQUAL',
    'XOR_EQUAL', 'CONCAT_EQUAL',

    # Increment/decrement
    'INC', 'DEC',

    # Arrows
    'OBJECT_OPERATOR', 'DOUBLE_ARROW', 'DOUBLE_COLON',

    # Delimiters
    'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET', 'LBRACE', 'RBRACE', 'DOLLAR',
    'COMMA', 'CONCAT', 'QUESTION', 'COLON', 'SEMI', 'AT', 'NS_SEPARATOR',

    # Casts
    'ARRAY_CAST', 'BOOL_CAST', 'DOUBLE_CAST', 'INT_CAST', 'OBJECT_CAST',
    'STRING_CAST', 'UNSET_CAST',

    # Escaping from HTML
    'INLINE_HTML',

    # Identifiers and reserved words
    'DIR', 'FILE', 'LINE', 'FUNC_C', 'CLASS_C', 'METHOD_C', 'NS_C',
    'LOGICAL_AND', 'LOGICAL_OR', 'LOGICAL_XOR',
    'HALT_COMPILER',
    'STRING', 'VARIABLE',
    'LNUMBER', 'DNUMBER', 'NUM_STRING',
    'CONSTANT_ENCAPSED_STRING', 'ENCAPSED_AND_WHITESPACE', 'QUOTE',
    'DOLLAR_OPEN_CURLY_BRACES', 'STRING_VARNAME', 'CURLY_OPEN',

    # Heredocs
    'START_HEREDOC', 'END_HEREDOC',
)

# Newlines
def t_php_WHITESPACE(t):
    r'[ \t\r\n]+'
    t.lexer.lineno += t.value.count("\n")
    return t

# Operators
t_php_PLUS                = r'\+'
t_php_MINUS               = r'-'
t_php_MUL                 = r'\*'
t_php_DIV                 = r'/'
t_php_MOD                 = r'%'
t_php_AND                 = r'&'
t_php_OR                  = r'\|'
t_php_NOT                 = r'~'
t_php_XOR                 = r'\^'
t_php_SL                  = r'<<'
t_php_SR                  = r'>>'
t_php_BOOLEAN_AND         = r'&&'
t_php_BOOLEAN_OR          = r'\|\|'
t_php_BOOLEAN_NOT         = r'!'
t_php_IS_SMALLER          = r'<'
t_php_IS_GREATER          = r'>'
t_php_IS_SMALLER_OR_EQUAL = r'<='
t_php_IS_GREATER_OR_EQUAL = r'>='
t_php_IS_EQUAL            = r'=='
t_php_IS_NOT_EQUAL        = r'(!=(?!=))|(<>)'
t_php_IS_IDENTICAL        = r'==='
t_php_IS_NOT_IDENTICAL    = r'!=='

# Assignment operators
t_php_EQUALS               = r'='
t_php_MUL_EQUAL            = r'\*='
t_php_DIV_EQUAL            = r'/='
t_php_MOD_EQUAL            = r'%='
t_php_PLUS_EQUAL           = r'\+='
t_php_MINUS_EQUAL          = r'-='
t_php_SL_EQUAL             = r'<<='
t_php_SR_EQUAL             = r'>>='
t_php_AND_EQUAL            = r'&='
t_php_OR_EQUAL             = r'\|='
t_php_XOR_EQUAL            = r'\^='
t_php_CONCAT_EQUAL         = r'\.='

# Increment/decrement
t_php_INC                  = r'\+\+'
t_php_DEC                  = r'--'

# Arrows
t_php_DOUBLE_ARROW         = r'=>'
t_php_DOUBLE_COLON         = r'::'

def t_php_OBJECT_OPERATOR(t):
    r'->'
    if re.match(r'[A-Za-z_]', peek(t.lexer)):
        t.lexer.push_state('property')
    return t

# Delimeters
t_php_LPAREN               = r'\('
t_php_RPAREN               = r'\)'
t_php_DOLLAR               = r'\$'
t_php_COMMA                = r','
t_php_CONCAT               = r'\.(?!\d|=)'
t_php_QUESTION             = r'\?'
t_php_COLON                = r':'
t_php_SEMI                 = r';'
t_php_AT                   = r'@'
t_php_NS_SEPARATOR         = r'\\'

def t_php_LBRACKET(t):
    r'\['
    t.lexer.push_state('php')
    return t

def t_php_RBRACKET(t):
    r'\]'
    t.lexer.pop_state()
    return t

def t_php_LBRACE(t):
    r'\{'
    t.lexer.push_state('php')
    return t

def t_php_RBRACE(t):
    r'\}'
    t.lexer.pop_state()
    return t

# Casts
t_php_ARRAY_CAST           = r'\([ \t]*[Aa][Rr][Rr][Aa][Yy][ \t]*\)'
t_php_BOOL_CAST            = r'\([ \t]*[Bb][Oo][Oo][Ll]([Ee][Aa][Nn])?[ \t]*\)'
t_php_DOUBLE_CAST          = r'\([ \t]*([Rr][Ee][Aa][Ll]|[Dd][Oo][Uu][Bb][Ll][Ee]|[Ff][Ll][Oo][Aa][Tt])[ \t]*\)'
t_php_INT_CAST             = r'\([ \t]*[Ii][Nn][Tt]([Ee][Gg][Ee][Rr])?[ \t]*\)'
t_php_OBJECT_CAST          = r'\([ \t]*[Oo][Bb][Jj][Ee][Cc][Tt][ \t]*\)'
t_php_STRING_CAST          = r'\([ \t]*[Ss][Tt][Rr][Ii][Nn][Gg][ \t]*\)'
t_php_UNSET_CAST           = r'\([ \t]*[Uu][Nn][Ss][Ee][Tt][ \t]*\)'

# Comments

def t_php_DOC_COMMENT(t):
    r'/\*\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count("\n")
    return t

def t_php_COMMENT(t):
    r'/\*(.|\n)*?\*/ | //([^?%\n]|[?%](?!>))*\n? | \#([^?%\n]|[?%](?!>))*\n?'
    t.lexer.lineno += t.value.count("\n")
    return t

# Escaping from HTML

def t_OPEN_TAG(t):
    r'<[?%]((php[ \t\r\n]?)|=)?'
    if '=' in t.value: t.type = 'OPEN_TAG_WITH_ECHO'
    t.lexer.lineno += t.value.count("\n")
    t.lexer.begin('php')
    return t

def t_php_CLOSE_TAG(t):
    r'[?%]>\r?\n?'
    t.lexer.lineno += t.value.count("\n")
    t.lexer.begin('INITIAL')
    return t

def t_INLINE_HTML(t):
    r'([^<]|<(?![?%]))+'
    t.lexer.lineno += t.value.count("\n")
    return t

# Identifiers and reserved words

reserved_map = {
    '__DIR__':         'DIR',
    '__FILE__':        'FILE',
    '__LINE__':        'LINE',
    '__FUNCTION__':    'FUNC_C',
    '__CLASS__':       'CLASS_C',
    '__METHOD__':      'METHOD_C',
    '__NAMESPACE__':   'NS_C',

    'AND':             'LOGICAL_AND',
    'OR':              'LOGICAL_OR',
    'XOR':             'LOGICAL_XOR',

    'DIE':             'EXIT',
    '__HALT_COMPILER': 'HALT_COMPILER',
}

for r in reserved:
    reserved_map[r] = r

# Identifier
def t_php_STRING(t):
    r'[A-Za-z_][\w_]*'
    t.type = reserved_map.get(t.value.upper(), 'STRING')
    return t

# Variable
def t_php_VARIABLE(t):
    r'\$[A-Za-z_][\w_]*'
    return t

# Floating literal
def t_php_DNUMBER(t):
    r'(\d*\.\d+|\d+\.\d*)([Ee][+-]?\d+)? | (\d+[Ee][+-]?\d+)'
    return t

# Integer literal
def t_php_LNUMBER(t):
    r'(0x[0-9A-Fa-f]+)|\d+'
    return t

# String literal
def t_php_CONSTANT_ENCAPSED_STRING(t):
    r"'([^\\']|\\(.|\n))*'"
    t.lexer.lineno += t.value.count("\n")
    return t

def t_php_QUOTE(t):
    r'"'
    t.lexer.push_state('quoted')
    return t

def t_quoted_QUOTE(t):
    r'"'
    t.lexer.pop_state()
    return t

def t_quoted_ENCAPSED_AND_WHITESPACE(t):
    r'( [^"\\${] | \\(.|\n) | \$(?![A-Za-z_{]) | \{(?!\$) )+'
    t.lexer.lineno += t.value.count("\n")
    return t

def t_quoted_VARIABLE(t):
    r'\$[A-Za-z_][\w_]*'
    t.lexer.push_state('quotedvar')
    return t

def t_quoted_CURLY_OPEN(t):
    r'\{(?=\$)'
    t.lexer.push_state('php')
    return t

def t_quoted_DOLLAR_OPEN_CURLY_BRACES(t):
    r'\$\{'
    if re.match(r'[A-Za-z_]', peek(t.lexer)):
        t.lexer.push_state('varname')
    else:
        t.lexer.push_state('php')
    return t

def t_quotedvar_QUOTE(t):
    r'"'
    t.lexer.pop_state()
    t.lexer.pop_state()
    return t

def t_quotedvar_LBRACKET(t):
    r'\['
    t.lexer.begin('offset')
    return t

def t_quotedvar_OBJECT_OPERATOR(t):
    r'->(?=[A-Za-z])'
    t.lexer.begin('property')
    return t

def t_quotedvar_ENCAPSED_AND_WHITESPACE(t):
    r'( [^"\\${] | \\(.|\n) | \$(?![A-Za-z_{]) | \{(?!\$) )+'
    t.lexer.lineno += t.value.count("\n")
    t.lexer.pop_state()
    return t

t_quotedvar_VARIABLE = t_php_VARIABLE

def t_quotedvar_CURLY_OPEN(t):
    r'\{(?=\$)'
    t.lexer.begin('php')
    return t

def t_quotedvar_DOLLAR_OPEN_CURLY_BRACES(t):
    r'\$\{'
    if re.match(r'[A-Za-z_]', peek(t.lexer)):
        t.lexer.begin('varname')
    else:
        t.lexer.begin('php')
    return t

def t_varname_STRING_VARNAME(t):
    r'[A-Za-z_][\w_]*'
    return t

t_varname_RBRACE = t_php_RBRACE
t_varname_LBRACKET = t_php_LBRACKET

def t_offset_STRING(t):
    r'[A-Za-z_][\w_]*'
    return t

def t_offset_NUM_STRING(t):
    r'\d+'
    return t

t_offset_VARIABLE = t_php_VARIABLE
t_offset_RBRACKET = t_php_RBRACKET

def t_property_STRING(t):
    r'[A-Za-z_][\w_]*'
    t.lexer.pop_state()
    return t

# Heredocs

def t_php_START_HEREDOC(t):
    r'<<<[ \t]*(?P<label>[A-Za-z_][\w_]*)\n'
    t.lexer.lineno += t.value.count("\n")
    t.lexer.push_state('heredoc')
    t.lexer.heredoc_label = t.lexer.lexmatch.group('label')
    return t   

def t_heredoc_END_HEREDOC(t):
    r'(?<=\n)[A-Za-z_][\w_]*'
    if t.value == t.lexer.heredoc_label:
        del t.lexer.heredoc_label
        t.lexer.pop_state()
    else:
        t.type = 'ENCAPSED_AND_WHITESPACE'
    return t

def t_heredoc_ENCAPSED_AND_WHITESPACE(t):
    r'( [^\n\\${] | \\. | \$(?![A-Za-z_{]) | \{(?!\$) )+\n? | \\?\n'
    t.lexer.lineno += t.value.count("\n")
    return t

def t_heredoc_VARIABLE(t):
    r'\$[A-Za-z_][\w_]*'
    t.lexer.push_state('heredocvar')
    return t

t_heredoc_CURLY_OPEN = t_quoted_CURLY_OPEN
t_heredoc_DOLLAR_OPEN_CURLY_BRACES = t_quoted_DOLLAR_OPEN_CURLY_BRACES

def t_heredocvar_ENCAPSED_AND_WHITESPACE(t):
    r'( [^\n\\${] | \\. | \$(?![A-Za-z_{]) | \{(?!\$) )+\n? | \\?\n'
    t.lexer.lineno += t.value.count("\n")
    t.lexer.pop_state()
    return t

t_heredocvar_LBRACKET = t_quotedvar_LBRACKET
t_heredocvar_OBJECT_OPERATOR = t_quotedvar_OBJECT_OPERATOR
t_heredocvar_VARIABLE = t_quotedvar_VARIABLE
t_heredocvar_CURLY_OPEN = t_quotedvar_CURLY_OPEN
t_heredocvar_DOLLAR_OPEN_CURLY_BRACES = t_quotedvar_DOLLAR_OPEN_CURLY_BRACES

def t_ANY_error(t):
    raise SyntaxError('illegal character', (None, t.lineno, None, t.value))

def peek(lexer):
    try:
        return lexer.lexdata[lexer.lexpos]
    except IndexError:
        return ''

class FilteredLexer(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.last_token = None

    @property
    def lineno(self):
        return self.lexer.lineno

    @lineno.setter
    def lineno(self, value):
        self.lexer.lineno = value

    @property
    def lexpos(self):
        return self.lexer.lexpos

    @lexpos.setter
    def lexpos(self, value):
        self.lexer.lexpos = value

    def clone(self):
        return FilteredLexer(self.lexer.clone())

    def current_state(self):
        return self.lexer.current_state()

    def input(self, input):
        self.lexer.input(input)

    def token(self):
        t = self.lexer.token()

        # Filter out tokens that the parser is not expecting.
        while t and t.type in unparsed:

            # Skip over open tags, but keep track of when we see them.
            if t.type == 'OPEN_TAG':
                self.last_token = t
                t = self.lexer.token()
                continue

            # Rewrite <?= to yield an "echo" statement.
            if t.type == 'OPEN_TAG_WITH_ECHO':
                t.type = 'ECHO'
                break

            # Insert semicolons in place of close tags where necessary.
            if t.type == 'CLOSE_TAG':
                if self.last_token and \
                       self.last_token.type in ('OPEN_TAG', 'SEMI', 'COLON',
                                                'LBRACE', 'RBRACE'):
                    # Dont insert semicolons after these tokens.
                    pass
                else:
                    # Rewrite close tag as a semicolon.
                    t.type = 'SEMI'
                    break

            t = self.lexer.token()

        self.last_token = t
        return t

    # Iterator interface
    def __iter__(self):
        return self

    def next(self):
        t = self.token()
        if t is None:
            raise StopIteration
        return t

    __next__ = next

full_lexer = lex.lex()
lexer = FilteredLexer(full_lexer)

full_tokens = tokens
tokens = filter(lambda token: token not in unparsed, tokens)

if __name__ == "__main__":
    lex.runmain(full_lexer)

########NEW FILE########
__FILENAME__ = phpparse
# -----------------------------------------------------------------------------
# phpparse.py
#
# A parser for PHP.
# -----------------------------------------------------------------------------

import os
import sys
import phplex
import phpast as ast
import ply.yacc as yacc

# Get the token map
tokens = phplex.tokens

precedence = (
    ('left', 'INCLUDE', 'INCLUDE_ONCE', 'EVAL', 'REQUIRE', 'REQUIRE_ONCE'),
    ('left', 'COMMA'),
    ('left', 'LOGICAL_OR'),
    ('left', 'LOGICAL_XOR'),
    ('left', 'LOGICAL_AND'),
    ('right', 'PRINT'),
    ('left', 'EQUALS', 'PLUS_EQUAL', 'MINUS_EQUAL', 'MUL_EQUAL', 'DIV_EQUAL', 'CONCAT_EQUAL', 'MOD_EQUAL', 'AND_EQUAL', 'OR_EQUAL', 'XOR_EQUAL', 'SL_EQUAL', 'SR_EQUAL'),
    ('left', 'QUESTION', 'COLON'),
    ('left', 'BOOLEAN_OR'),
    ('left', 'BOOLEAN_AND'),
    ('left', 'OR'),
    ('left', 'XOR'),
    ('left', 'AND'),
    ('nonassoc', 'IS_EQUAL', 'IS_NOT_EQUAL', 'IS_IDENTICAL', 'IS_NOT_IDENTICAL'),
    ('nonassoc', 'IS_SMALLER', 'IS_SMALLER_OR_EQUAL', 'IS_GREATER', 'IS_GREATER_OR_EQUAL'),
    ('left', 'SL', 'SR'),
    ('left', 'PLUS', 'MINUS', 'CONCAT'),
    ('left', 'MUL', 'DIV', 'MOD'),
    ('right', 'BOOLEAN_NOT'),
    ('nonassoc', 'INSTANCEOF'),
    ('right', 'NOT', 'INC', 'DEC', 'INT_CAST', 'DOUBLE_CAST', 'STRING_CAST', 'ARRAY_CAST', 'OBJECT_CAST', 'BOOL_CAST', 'UNSET_CAST', 'AT'),
    ('right', 'LBRACKET'),
    ('nonassoc', 'NEW', 'CLONE'),
    # ('left', 'ELSEIF'),
    # ('left', 'ELSE'),
    ('left', 'ENDIF'),
    ('right', 'STATIC', 'ABSTRACT', 'FINAL', 'PRIVATE', 'PROTECTED', 'PUBLIC'),
)

def p_start(p):
    'start : top_statement_list'
    p[0] = p[1]

def p_top_statement_list(p):
    '''top_statement_list : top_statement_list top_statement
                          | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_top_statement(p):
    '''top_statement : statement
                     | function_declaration_statement
                     | class_declaration_statement
                     | HALT_COMPILER LPAREN RPAREN SEMI'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        # ???
        pass

def p_top_statement_namespace(p):
    '''top_statement : NAMESPACE namespace_name SEMI
                     | NAMESPACE LBRACE top_statement_list RBRACE
                     | NAMESPACE namespace_name LBRACE top_statement_list RBRACE'''
    if len(p) == 4:
        p[0] = ast.Namespace(p[2], [], lineno=p.lineno(1))
    elif len(p) == 5:
        p[0] = ast.Namespace(None, p[3], lineno=p.lineno(1))
    else:
        p[0] = ast.Namespace(p[2], p[4], lineno=p.lineno(1))

def p_top_statement_constant(p):
    'top_statement : CONST constant_declarations SEMI'
    p[0] = ast.ConstantDeclarations(p[2], lineno=p.lineno(1))

def p_top_statement_use(p):
    'top_statement : USE use_declarations SEMI'
    p[0] = ast.UseDeclarations(p[2], lineno=p.lineno(1))

def p_use_declarations(p):
    '''use_declarations : use_declarations COMMA use_declaration
                        | use_declaration'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_use_declaration(p):
    '''use_declaration : namespace_name
                       | NS_SEPARATOR namespace_name
                       | namespace_name AS STRING
                       | NS_SEPARATOR namespace_name AS STRING'''
    if len(p) == 2:
        p[0] = ast.UseDeclaration(p[1], None, lineno=p.lineno(1))
    elif len(p) == 3:
        p[0] = ast.UseDeclaration(p[1] + p[2], None, lineno=p.lineno(1))
    elif len(p) == 4:
        p[0] = ast.UseDeclaration(p[1], p[3], lineno=p.lineno(2))
    else:
        p[0] = ast.UseDeclaration(p[1] + p[2], p[4], lineno=p.lineno(1))

def p_constant_declarations(p):
    '''constant_declarations : constant_declarations COMMA constant_declaration
                             | constant_declaration'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_constant_declaration(p):
    'constant_declaration : STRING EQUALS static_scalar'
    p[0] = ast.ConstantDeclaration(p[1], p[3], lineno=p.lineno(1))

def p_inner_statement_list(p):
    '''inner_statement_list : inner_statement_list inner_statement
                            | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_inner_statement(p):
    '''inner_statement : statement
                       | function_declaration_statement
                       | class_declaration_statement
                       | HALT_COMPILER LPAREN RPAREN SEMI'''
    assert len(p) == 2, "__HALT_COMPILER() can only be used from the outermost scope"
    p[0] = p[1]

def p_statement_block(p):
    'statement : LBRACE inner_statement_list RBRACE'
    p[0] = ast.Block(p[2], lineno=p.lineno(1))

def p_statement_if(p):
    '''statement : IF LPAREN expr RPAREN statement elseif_list else_single
                 | IF LPAREN expr RPAREN COLON inner_statement_list new_elseif_list new_else_single ENDIF SEMI'''
    if len(p) == 8:
        p[0] = ast.If(p[3], p[5], p[6], p[7], lineno=p.lineno(1))
    else:
        p[0] = ast.If(p[3], ast.Block(p[6], lineno=p.lineno(5)),
                      p[7], p[8], lineno=p.lineno(1))

def p_statement_while(p):
    'statement : WHILE LPAREN expr RPAREN while_statement'
    p[0] = ast.While(p[3], p[5], lineno=p.lineno(1))

def p_statement_do_while(p):
    'statement : DO statement WHILE LPAREN expr RPAREN SEMI'
    p[0] = ast.DoWhile(p[2], p[5], lineno=p.lineno(1))

def p_statement_for(p):
    'statement : FOR LPAREN for_expr SEMI for_expr SEMI for_expr RPAREN for_statement'
    p[0] = ast.For(p[3], p[5], p[7], p[9], lineno=p.lineno(1))

def p_statement_foreach(p):
    'statement : FOREACH LPAREN expr AS foreach_variable foreach_optional_arg RPAREN foreach_statement'
    if p[6] is None:
        p[0] = ast.Foreach(p[3], None, p[5], p[8], lineno=p.lineno(1))
    else:
        p[0] = ast.Foreach(p[3], p[5], p[6], p[8], lineno=p.lineno(1))

def p_statement_switch(p):
    'statement : SWITCH LPAREN expr RPAREN switch_case_list'
    p[0] = ast.Switch(p[3], p[5], lineno=p.lineno(1))

def p_statement_break(p):
    '''statement : BREAK SEMI
                 | BREAK expr SEMI'''
    if len(p) == 3:
        p[0] = ast.Break(None, lineno=p.lineno(1))
    else:
        p[0] = ast.Break(p[2], lineno=p.lineno(1))

def p_statement_continue(p):
    '''statement : CONTINUE SEMI
                 | CONTINUE expr SEMI'''
    if len(p) == 3:
        p[0] = ast.Continue(None, lineno=p.lineno(1))
    else:
        p[0] = ast.Continue(p[2], lineno=p.lineno(1))

def p_statement_return(p):
    '''statement : RETURN SEMI
                 | RETURN expr SEMI'''
    if len(p) == 3:
        p[0] = ast.Return(None, lineno=p.lineno(1))
    else:
        p[0] = ast.Return(p[2], lineno=p.lineno(1))

def p_statement_global(p):
    'statement : GLOBAL global_var_list SEMI'
    p[0] = ast.Global(p[2], lineno=p.lineno(1))

def p_statement_static(p):
    'statement : STATIC static_var_list SEMI'
    p[0] = ast.Static(p[2], lineno=p.lineno(1))

def p_statement_echo(p):
    'statement : ECHO echo_expr_list SEMI'
    p[0] = ast.Echo(p[2], lineno=p.lineno(1))

def p_statement_inline_html(p):
    'statement : INLINE_HTML'
    p[0] = ast.InlineHTML(p[1], lineno=p.lineno(1))

def p_statement_expr(p):
    'statement : expr SEMI'
    p[0] = p[1]

def p_statement_unset(p):
    'statement : UNSET LPAREN unset_variables RPAREN SEMI'
    p[0] = ast.Unset(p[3], lineno=p.lineno(1))

def p_statement_empty(p):
    'statement : SEMI'
    pass

def p_statement_try(p):
    'statement : TRY LBRACE inner_statement_list RBRACE CATCH LPAREN fully_qualified_class_name VARIABLE RPAREN LBRACE inner_statement_list RBRACE additional_catches'
    p[0] = ast.Try(p[3], [ast.Catch(p[7], ast.Variable(p[8], lineno=p.lineno(8)),
                                    p[11], lineno=p.lineno(5))] + p[13],
                   lineno=p.lineno(1))

def p_additional_catches(p):
    '''additional_catches : additional_catches CATCH LPAREN fully_qualified_class_name VARIABLE RPAREN LBRACE inner_statement_list RBRACE
                          | empty'''
    if len(p) == 10:
        p[0] = p[1] + [ast.Catch(p[4], ast.Variable(p[5], lineno=p.lineno(5)),
                                 p[8], lineno=p.lineno(2))]
    else:
        p[0] = []

def p_statement_throw(p):
    'statement : THROW expr SEMI'
    p[0] = ast.Throw(p[2], lineno=p.lineno(1))

def p_statement_declare(p):
    'statement : DECLARE LPAREN declare_list RPAREN declare_statement'
    p[0] = ast.Declare(p[3], p[5], lineno=p.lineno(1))

def p_declare_list(p):
    '''declare_list : STRING EQUALS static_scalar
                    | declare_list COMMA STRING EQUALS static_scalar'''
    if len(p) == 4:
        p[0] = [ast.Directive(p[1], p[3], lineno=p.lineno(1))]
    else:
        p[0] = p[1] + [ast.Directive(p[3], p[5], lineno=p.lineno(2))]

def p_declare_statement(p):
    '''declare_statement : statement
                         | COLON inner_statement_list ENDDECLARE SEMI'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ast.Block(p[2], lineno=p.lineno(1))

def p_elseif_list(p):
    '''elseif_list : empty
                   | elseif_list ELSEIF LPAREN expr RPAREN statement'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [ast.ElseIf(p[4], p[6], lineno=p.lineno(2))]

def p_else_single(p):
    '''else_single : empty
                   | ELSE statement'''
    if len(p) == 3:
        p[0] = ast.Else(p[2], lineno=p.lineno(1))

def p_new_elseif_list(p):
    '''new_elseif_list : empty
                       | new_elseif_list ELSEIF LPAREN expr RPAREN COLON inner_statement_list'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [ast.ElseIf(p[4], ast.Block(p[7], lineo=p.lineno(6)),
                                  lineno=p.lineno(2))]

def p_new_else_single(p):
    '''new_else_single : empty
                       | ELSE COLON inner_statement_list'''
    if len(p) == 4:
        p[0] = ast.Else(ast.Block(p[3], lineno=p.lineno(2)),
                        lineno=p.lineno(1))

def p_while_statement(p):
    '''while_statement : statement
                       | COLON inner_statement_list ENDWHILE SEMI'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ast.Block(p[2], lineno=p.lineno(1))

def p_for_expr(p):
    '''for_expr : empty
                | non_empty_for_expr'''
    p[0] = p[1]

def p_non_empty_for_expr(p):
    '''non_empty_for_expr : non_empty_for_expr COMMA expr
                          | expr'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_for_statement(p):
    '''for_statement : statement
                     | COLON inner_statement_list ENDFOR SEMI'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ast.Block(p[2], lineno=p.lineno(1))

def p_foreach_variable(p):
    '''foreach_variable : VARIABLE
                        | AND VARIABLE'''
    if len(p) == 2:
        p[0] = ast.ForeachVariable(p[1], False, lineno=p.lineno(1))
    else:
        p[0] = ast.ForeachVariable(p[2], True, lineno=p.lineno(1))

def p_foreach_optional_arg(p):
    '''foreach_optional_arg : empty
                            | DOUBLE_ARROW foreach_variable'''
    if len(p) == 3:
        p[0] = p[2]

def p_foreach_statement(p):
    '''foreach_statement : statement
                         | COLON inner_statement_list ENDFOREACH SEMI'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ast.Block(p[2], lineno=p.lineno(1))

def p_switch_case_list(p):
    '''switch_case_list : LBRACE case_list RBRACE
                        | LBRACE SEMI case_list RBRACE'''
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[3]

def p_switch_case_list_colon(p):
    '''switch_case_list : COLON case_list ENDSWITCH SEMI
                        | COLON SEMI case_list ENDSWITCH SEMI'''
    if len(p) == 5:
        p[0] = p[2]
    else:
        p[0] = p[3]

def p_case_list(p):
    '''case_list : empty
                 | case_list CASE expr case_separator inner_statement_list
                 | case_list DEFAULT case_separator inner_statement_list'''
    if len(p) == 6:
        p[0] = p[1] + [ast.Case(p[3], p[5], lineno=p.lineno(2))]
    elif len(p) == 5:
        p[0] = p[1] + [ast.Default(p[4], lineno=p.lineno(2))]
    else:
        p[0] = []

def p_case_separator(p):
    '''case_separator : COLON
                      | SEMI'''
    pass

def p_global_var_list(p):
    '''global_var_list : global_var_list COMMA global_var
                       | global_var'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_global_var(p):
    '''global_var : VARIABLE
                  | DOLLAR variable
                  | DOLLAR LBRACE expr RBRACE'''
    if len(p) == 2:
        p[0] = ast.Variable(p[1], lineno=p.lineno(1))
    elif len(p) == 3:
        p[0] = ast.Variable(p[2], lineno=p.lineno(1))
    else:
        p[0] = ast.Variable(p[3], lineno=p.lineno(1))

def p_static_var_list(p):
    '''static_var_list : static_var_list COMMA static_var
                       | static_var'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_static_var(p):
    '''static_var : VARIABLE EQUALS static_scalar
                  | VARIABLE'''
    if len(p) == 4:
        p[0] = ast.StaticVariable(p[1], p[3], lineno=p.lineno(1))
    else:
        p[0] = ast.StaticVariable(p[1], None, lineno=p.lineno(1))

def p_echo_expr_list(p):
    '''echo_expr_list : echo_expr_list COMMA expr
                      | expr'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_unset_variables(p):
    '''unset_variables : unset_variables COMMA unset_variable
                       | unset_variable'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_unset_variable(p):
    'unset_variable : variable'
    p[0] = p[1]

def p_function_declaration_statement(p):
    'function_declaration_statement : FUNCTION is_reference STRING LPAREN parameter_list RPAREN LBRACE inner_statement_list RBRACE'
    p[0] = ast.Function(p[3], p[5], p[8], p[2], lineno=p.lineno(1))

def p_class_declaration_statement(p):
    '''class_declaration_statement : class_entry_type STRING extends_from implements_list LBRACE class_statement_list RBRACE
                                   | INTERFACE STRING interface_extends_list LBRACE class_statement_list RBRACE'''
    if len(p) == 8:
        p[0] = ast.Class(p[2], p[1], p[3], p[4], p[6], lineno=p.lineno(2))
    else:
        p[0] = ast.Interface(p[2], p[3], p[5], lineno=p.lineno(1))

def p_class_entry_type(p):
    '''class_entry_type : CLASS
                        | ABSTRACT CLASS
                        | FINAL CLASS'''
    if len(p) == 3:
        p[0] = p[1].lower()

def p_extends_from(p):
    '''extends_from : empty
                    | EXTENDS fully_qualified_class_name'''
    if len(p) == 3:
        p[0] = p[2]

def p_fully_qualified_class_name(p):
    '''fully_qualified_class_name : namespace_name
                                  | NS_SEPARATOR namespace_name
                                  | NAMESPACE NS_SEPARATOR namespace_name'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1] + p[2] + p[3]

def p_implements_list(p):
    '''implements_list : IMPLEMENTS interface_list
                       | empty'''
    if len(p) == 3:
        p[0] = p[2]
    else:
        p[0] = []

def p_class_statement_list(p):
    '''class_statement_list : class_statement_list class_statement
                            | empty'''

    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_class_statement(p):
    '''class_statement : method_modifiers FUNCTION is_reference STRING LPAREN parameter_list RPAREN method_body
                       | variable_modifiers class_variable_declaration SEMI
                       | class_constant_declaration SEMI'''
    if len(p) == 9:
        p[0] = ast.Method(p[4], p[1], p[6], p[8], p[3], lineno=p.lineno(2))
    elif len(p) == 4:
        p[0] = ast.ClassVariables(p[1], p[2], lineno=p.lineno(3))
    else:
        p[0] = ast.ClassConstants(p[1], lineno=p.lineno(2))

def p_class_variable_declaration_initial(p):
    '''class_variable_declaration : class_variable_declaration COMMA VARIABLE EQUALS static_scalar
                                  | VARIABLE EQUALS static_scalar'''
    if len(p) == 6:
        p[0] = p[1] + [ast.ClassVariable(p[3], p[5], lineno=p.lineno(2))]
    else:
        p[0] = [ast.ClassVariable(p[1], p[3], lineno=p.lineno(1))]

def p_class_variable_declaration_no_initial(p):
    '''class_variable_declaration : class_variable_declaration COMMA VARIABLE
                                  | VARIABLE'''
    if len(p) == 4:
        p[0] = p[1] + [ast.ClassVariable(p[3], None, lineno=p.lineno(2))]
    else:
        p[0] = [ast.ClassVariable(p[1], None, lineno=p.lineno(1))]

def p_class_constant_declaration(p):
    '''class_constant_declaration : class_constant_declaration COMMA STRING EQUALS static_scalar
                                  | CONST STRING EQUALS static_scalar'''
    if len(p) == 6:
        p[0] = p[1] + [ast.ClassConstant(p[3], p[5], lineno=p.lineno(2))]
    else:
        p[0] = [ast.ClassConstant(p[2], p[4], lineno=p.lineno(1))]

def p_interface_list(p):
    '''interface_list : interface_list COMMA fully_qualified_class_name
                      | fully_qualified_class_name'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_interface_extends_list(p):
    '''interface_extends_list : EXTENDS interface_list
                              | empty'''
    if len(p) == 3:
        p[0] = p[2]

def p_variable_modifiers_non_empty(p):
    'variable_modifiers : non_empty_member_modifiers'
    p[0] = p[1]

def p_variable_modifiers_var(p):
    'variable_modifiers : VAR'
    p[0] = []

def p_method_modifiers_non_empty(p):
    'method_modifiers : non_empty_member_modifiers'
    p[0] = p[1]

def p_method_modifiers_empty(p):
    'method_modifiers : empty'
    p[0] = []

def p_method_body(p):
    '''method_body : LBRACE inner_statement_list RBRACE
                   | SEMI'''
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = []

def p_non_empty_member_modifiers(p):
    '''non_empty_member_modifiers : non_empty_member_modifiers member_modifier
                                  | member_modifier'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_member_modifier(p):
    '''member_modifier : PUBLIC
                       | PROTECTED
                       | PRIVATE
                       | STATIC
                       | ABSTRACT
                       | FINAL'''
    p[0] = p[1].lower()

def p_is_reference(p):
    '''is_reference : AND
                    | empty'''
    p[0] = p[1] is not None

def p_parameter_list(p):
    '''parameter_list : parameter_list COMMA parameter
                      | parameter'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_parameter_list_empty(p):
    'parameter_list : empty'
    p[0] = []

def p_parameter(p):
    '''parameter : VARIABLE
                 | class_name VARIABLE
                 | AND VARIABLE
                 | class_name AND VARIABLE
                 | VARIABLE EQUALS static_scalar
                 | class_name VARIABLE EQUALS static_scalar
                 | AND VARIABLE EQUALS static_scalar
                 | class_name AND VARIABLE EQUALS static_scalar'''
    if len(p) == 2: # VARIABLE
        p[0] = ast.FormalParameter(p[1], None, False, None, lineno=p.lineno(1))
    elif len(p) == 3 and p[1] == '&': # AND VARIABLE
        p[0] = ast.FormalParameter(p[2], None, True, None, lineno=p.lineno(1))
    elif len(p) == 3 and p[1] != '&': # STRING VARIABLE 
        p[0] = ast.FormalParameter(p[2], None, False, p[1], lineno=p.lineno(1))
    elif len(p) == 4 and p[2] != '&': # VARIABLE EQUALS static_scalar 
        p[0] = ast.FormalParameter(p[1], p[3], False, None, lineno=p.lineno(1))
    elif len(p) == 4 and p[2] == '&': # STRING AND VARIABLE
        p[0] = ast.FormalParameter(p[3], None, True, p[1], lineno=p.lineno(1))
    elif len(p) == 5 and p[1] == '&': # AND VARIABLE EQUALS static_scalar
        p[0] = ast.FormalParameter(p[2], p[4], True, None, lineno=p.lineno(1))
    elif len(p) == 5 and p[1] != '&': # class_name VARIABLE EQUALS static_scalar
        p[0] = ast.FormalParameter(p[2], p[4], False, p[1], lineno=p.lineno(1))
    else: # STRING AND VARIABLE EQUALS static_scalar
        p[0] = ast.FormalParameter(p[3], p[5], True, p[1], lineno=p.lineno(1))

def p_expr_variable(p):
    'expr : variable'
    p[0] = p[1]

def p_expr_assign(p):
    '''expr : variable EQUALS expr
            | variable EQUALS AND expr'''
    if len(p) == 5:
        p[0] = ast.Assignment(p[1], p[4], True, lineno=p.lineno(2))
    else:
        p[0] = ast.Assignment(p[1], p[3], False, lineno=p.lineno(2))

def p_expr_new(p):
    'expr : NEW class_name_reference ctor_arguments'
    p[0] = ast.New(p[2], p[3], lineno=p.lineno(1))

def p_class_name_reference(p):
    '''class_name_reference : class_name
                            | dynamic_class_name_reference'''
    p[0] = p[1]

def p_class_name(p):
    '''class_name : namespace_name
                  | NS_SEPARATOR namespace_name
                  | NAMESPACE NS_SEPARATOR namespace_name'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = p[1] + p[2]
    else:
        p[0] = p[1] + p[2] + p[3]

def p_class_name_static(p):
    'class_name : STATIC'
    p[0] = p[1].lower()

def p_dynamic_class_name_reference(p):
    '''dynamic_class_name_reference : base_variable OBJECT_OPERATOR object_property dynamic_class_name_variable_properties
                                    | base_variable'''
    if len(p) == 5:
        name, dims = p[3]
        p[0] = ast.ObjectProperty(p[1], name, lineno=p.lineno(2))
        for class_, dim, lineno in dims:
            p[0] = class_(p[0], dim, lineno=lineno)
        for name, dims in p[4]:
            p[0] = ast.ObjectProperty(p[0], name, lineno=p.lineno(2))
            for class_, dim, lineno in dims:
                p[0] = class_(p[0], dim, lineno=lineno)
    else:
        p[0] = p[1]

def p_dynamic_class_name_variable_properties(p):
    '''dynamic_class_name_variable_properties : dynamic_class_name_variable_properties dynamic_class_name_variable_property
                                              | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_dynamic_class_name_variable_property(p):
    'dynamic_class_name_variable_property : OBJECT_OPERATOR object_property'
    p[0] = p[2]

def p_ctor_arguments(p):
    '''ctor_arguments : LPAREN function_call_parameter_list RPAREN
                      | empty'''
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = []

def p_expr_clone(p):
    'expr : CLONE expr'
    p[0] = ast.Clone(p[2], lineno=p.lineno(1))

def p_expr_list_assign(p):
    'expr : LIST LPAREN assignment_list RPAREN EQUALS expr'
    p[0] = ast.ListAssignment(p[3], p[6], lineno=p.lineno(1))

def p_assignment_list(p):
    '''assignment_list : assignment_list COMMA assignment_list_element
                       | assignment_list_element'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_assignment_list_element(p):
    '''assignment_list_element : variable
                               | empty
                               | LIST LPAREN assignment_list RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[3]

def p_variable(p):
    '''variable : base_variable_with_function_calls OBJECT_OPERATOR object_property method_or_not variable_properties
                | base_variable_with_function_calls'''
    if len(p) == 6:
        name, dims = p[3]
        params = p[4]
        if params is not None:
            p[0] = ast.MethodCall(p[1], name, params, lineno=p.lineno(2))
        else:
            p[0] = ast.ObjectProperty(p[1], name, lineno=p.lineno(2))
        for class_, dim, lineno in dims:
            p[0] = class_(p[0], dim, lineno=lineno)
        for (name, dims), params in p[5]:
            if params is not None:
                p[0] = ast.MethodCall(p[0], name, params, lineno=p.lineno(2))
            else:
                p[0] = ast.ObjectProperty(p[0], name, lineno=p.lineno(2))
            for class_, dim, lineno in dims:
                p[0] = class_(p[0], dim, lineno=lineno)
    else:
        p[0] = p[1]

def p_base_variable_with_function_calls(p):
    '''base_variable_with_function_calls : base_variable
                                         | function_call'''
    p[0] = p[1]

def p_function_call(p):
    '''function_call : namespace_name LPAREN function_call_parameter_list RPAREN
                     | NS_SEPARATOR namespace_name LPAREN function_call_parameter_list RPAREN
                     | NAMESPACE NS_SEPARATOR namespace_name LPAREN function_call_parameter_list RPAREN'''
    if len(p) == 5:
        p[0] = ast.FunctionCall(p[1], p[3], lineno=p.lineno(2))
    elif len(p) == 6:
        p[0] = ast.FunctionCall(p[1] + p[2], p[4], lineno=p.lineno(1))
    else:
        p[0] = ast.FunctionCall(p[1] + p[2] + p[3], p[5], lineno=p.lineno(1))

def p_function_call_static(p):
    '''function_call : class_name DOUBLE_COLON STRING LPAREN function_call_parameter_list RPAREN
                     | class_name DOUBLE_COLON variable_without_objects LPAREN function_call_parameter_list RPAREN
                     | variable_class_name DOUBLE_COLON STRING LPAREN function_call_parameter_list RPAREN
                     | variable_class_name DOUBLE_COLON variable_without_objects LPAREN function_call_parameter_list RPAREN'''
    p[0] = ast.StaticMethodCall(p[1], p[3], p[5], lineno=p.lineno(2))

def p_function_call_variable(p):
    'function_call : variable_without_objects LPAREN function_call_parameter_list RPAREN'
    p[0] = ast.FunctionCall(p[1], p[3], lineno=p.lineno(2))

def p_method_or_not(p):
    '''method_or_not : LPAREN function_call_parameter_list RPAREN
                     | empty'''
    if len(p) == 4:
        p[0] = p[2]

def p_variable_properties(p):
    '''variable_properties : variable_properties variable_property
                           | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []

def p_variable_property(p):
    'variable_property : OBJECT_OPERATOR object_property method_or_not'
    p[0] = (p[2], p[3])

def p_base_variable(p):
    '''base_variable : simple_indirect_reference
                     | static_member'''
    p[0] = p[1]

def p_simple_indirect_reference(p):
    '''simple_indirect_reference : DOLLAR simple_indirect_reference
                                 | reference_variable'''
    if len(p) == 3:
        p[0] = ast.Variable(p[2], lineno=p.lineno(1))
    else:
        p[0] = p[1]

def p_static_member(p):
    '''static_member : class_name DOUBLE_COLON variable_without_objects
                     | variable_class_name DOUBLE_COLON variable_without_objects'''
    p[0] = ast.StaticProperty(p[1], p[3], lineno=p.lineno(2))

def p_variable_class_name(p):
    'variable_class_name : reference_variable'
    p[0] = p[1]

def p_reference_variable_array_offset(p):
    'reference_variable : reference_variable LBRACKET dim_offset RBRACKET'
    p[0] = ast.ArrayOffset(p[1], p[3], lineno=p.lineno(2))

def p_reference_variable_string_offset(p):
    'reference_variable : reference_variable LBRACE expr RBRACE'
    p[0] = ast.StringOffset(p[1], p[3], lineno=p.lineno(2))

def p_reference_variable_compound_variable(p):
    'reference_variable : compound_variable'
    p[0] = p[1]

def p_compound_variable(p):
    '''compound_variable : VARIABLE
                         | DOLLAR LBRACE expr RBRACE'''
    if len(p) == 2:
        p[0] = ast.Variable(p[1], lineno=p.lineno(1))
    else:
        p[0] = ast.Variable(p[3], lineno=p.lineno(1))

def p_dim_offset(p):
    '''dim_offset : expr
                  | empty'''
    p[0] = p[1]

def p_object_property(p):
    '''object_property : variable_name object_dim_list
                       | variable_without_objects'''
    if len(p) == 3:
        p[0] = (p[1], p[2])
    else:
        p[0] = (p[1], [])

def p_object_dim_list_empty(p):
    'object_dim_list : empty'
    p[0] = []

def p_object_dim_list_array_offset(p):
    'object_dim_list : object_dim_list LBRACKET dim_offset RBRACKET'
    p[0] = p[1] + [(ast.ArrayOffset, p[3], p.lineno(2))]

def p_object_dim_list_string_offset(p):
    'object_dim_list : object_dim_list LBRACE expr RBRACE'
    p[0] = p[1] + [(ast.StringOffset, p[3], p.lineno(2))]

def p_variable_name(p):
    '''variable_name : STRING
                     | LBRACE expr RBRACE'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]

def p_variable_without_objects(p):
    'variable_without_objects : simple_indirect_reference'
    p[0] = p[1]

def p_expr_scalar(p):
    'expr : scalar'
    p[0] = p[1]

def p_expr_array(p):
    'expr : ARRAY LPAREN array_pair_list RPAREN'
    p[0] = ast.Array(p[3], lineno=p.lineno(1))

def p_array_pair_list(p):
    '''array_pair_list : empty
                       | non_empty_array_pair_list possible_comma'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1]

def p_non_empty_array_pair_list_item(p):
    '''non_empty_array_pair_list : non_empty_array_pair_list COMMA AND variable
                                 | non_empty_array_pair_list COMMA expr
                                 | AND variable
                                 | expr'''
    if len(p) == 5:
        p[0] = p[1] + [ast.ArrayElement(None, p[4], True, lineno=p.lineno(2))]
    elif len(p) == 4:
        p[0] = p[1] + [ast.ArrayElement(None, p[3], False, lineno=p.lineno(2))]
    elif len(p) == 3:
        p[0] = [ast.ArrayElement(None, p[2], True, lineno=p.lineno(1))]
    else:
        p[0] = [ast.ArrayElement(None, p[1], False, lineno=p.lineno(1))]

def p_non_empty_array_pair_list_pair(p):
    '''non_empty_array_pair_list : non_empty_array_pair_list COMMA expr DOUBLE_ARROW AND variable
                                 | non_empty_array_pair_list COMMA expr DOUBLE_ARROW expr
                                 | expr DOUBLE_ARROW AND variable
                                 | expr DOUBLE_ARROW expr'''
    if len(p) == 7:
        p[0] = p[1] + [ast.ArrayElement(p[3], p[6], True, lineno=p.lineno(2))]
    elif len(p) == 6:
        p[0] = p[1] + [ast.ArrayElement(p[3], p[5], False, lineno=p.lineno(2))]
    elif len(p) == 5:
        p[0] = [ast.ArrayElement(p[1], p[4], True, lineno=p.lineno(2))]
    else:
        p[0] = [ast.ArrayElement(p[1], p[3], False, lineno=p.lineno(2))]

def p_possible_comma(p):
    '''possible_comma : empty
                      | COMMA'''
    pass

def p_function_call_parameter_list(p):
    '''function_call_parameter_list : function_call_parameter_list COMMA function_call_parameter
                                    | function_call_parameter'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_function_call_parameter_list_empty(p):
    'function_call_parameter_list : empty'
    p[0] = []

def p_function_call_parameter(p):
    '''function_call_parameter : expr
                               | AND variable'''
    if len(p) == 2:
        p[0] = ast.Parameter(p[1], False, lineno=p.lineno(1))
    else:
        p[0] = ast.Parameter(p[2], True, lineno=p.lineno(1))

def p_expr_function(p):
    'expr : FUNCTION is_reference LPAREN parameter_list RPAREN lexical_vars LBRACE inner_statement_list RBRACE'
    p[0] = ast.Closure(p[4], p[6], p[8], p[2], lineno=p.lineno(1))

def p_lexical_vars(p):
    '''lexical_vars : USE LPAREN lexical_var_list RPAREN
                    | empty'''
    if len(p) == 5:
        p[0] = p[3]
    else:
        p[0] = []

def p_lexical_var_list(p):
    '''lexical_var_list : lexical_var_list COMMA AND VARIABLE
                        | lexical_var_list COMMA VARIABLE
                        | AND VARIABLE
                        | VARIABLE'''
    if len(p) == 5:
        p[0] = p[1] + [ast.LexicalVariable(p[4], True, lineno=p.lineno(2))]
    elif len(p) == 4:
        p[0] = p[1] + [ast.LexicalVariable(p[3], False, lineno=p.lineno(2))]
    elif len(p) == 3:
        p[0] = [ast.LexicalVariable(p[2], True, lineno=p.lineno(1))]
    else:
        p[0] = [ast.LexicalVariable(p[1], False, lineno=p.lineno(1))]

def p_expr_assign_op(p):
    '''expr : variable PLUS_EQUAL expr
            | variable MINUS_EQUAL expr
            | variable MUL_EQUAL expr
            | variable DIV_EQUAL expr
            | variable CONCAT_EQUAL expr
            | variable MOD_EQUAL expr
            | variable AND_EQUAL expr
            | variable OR_EQUAL expr
            | variable XOR_EQUAL expr
            | variable SL_EQUAL expr
            | variable SR_EQUAL expr'''
    p[0] = ast.AssignOp(p[2], p[1], p[3], lineno=p.lineno(2))

def p_expr_binary_op(p):
    '''expr : expr BOOLEAN_AND expr
            | expr BOOLEAN_OR expr
            | expr LOGICAL_AND expr
            | expr LOGICAL_OR expr
            | expr LOGICAL_XOR expr
            | expr AND expr
            | expr OR expr
            | expr XOR expr
            | expr CONCAT expr
            | expr PLUS expr
            | expr MINUS expr
            | expr MUL expr
            | expr DIV expr
            | expr SL expr
            | expr SR expr
            | expr MOD expr
            | expr IS_IDENTICAL expr
            | expr IS_NOT_IDENTICAL expr
            | expr IS_EQUAL expr
            | expr IS_NOT_EQUAL expr
            | expr IS_SMALLER expr
            | expr IS_SMALLER_OR_EQUAL expr
            | expr IS_GREATER expr
            | expr IS_GREATER_OR_EQUAL expr
            | expr INSTANCEOF expr'''
    p[0] = ast.BinaryOp(p[2].lower(), p[1], p[3], lineno=p.lineno(2))

def p_expr_unary_op(p):
    '''expr : PLUS expr
            | MINUS expr
            | NOT expr
            | BOOLEAN_NOT expr'''
    p[0] = ast.UnaryOp(p[1], p[2], lineno=p.lineno(1))

def p_expr_ternary_op(p):
    'expr : expr QUESTION expr COLON expr'
    p[0] = ast.TernaryOp(p[1], p[3], p[5], lineno=p.lineno(2))

def p_expr_pre_incdec(p):
    '''expr : INC variable
            | DEC variable'''
    p[0] = ast.PreIncDecOp(p[1], p[2], lineno=p.lineno(1))

def p_expr_post_incdec(p):
    '''expr : variable INC
            | variable DEC'''
    p[0] = ast.PostIncDecOp(p[2], p[1], lineno=p.lineno(2))

def p_expr_cast_int(p):
    'expr : INT_CAST expr'
    p[0] = ast.Cast('int', p[2], lineno=p.lineno(1))

def p_expr_cast_double(p):
    'expr : DOUBLE_CAST expr'
    p[0] = ast.Cast('double', p[2], lineno=p.lineno(1))

def p_expr_cast_string(p):
    'expr : STRING_CAST expr'
    p[0] = ast.Cast('string', p[2], lineno=p.lineno(1))

def p_expr_cast_array(p):
    'expr : ARRAY_CAST expr'
    p[0] = ast.Cast('array', p[2], lineno=p.lineno(1))

def p_expr_cast_object(p):
    'expr : OBJECT_CAST expr'
    p[0] = ast.Cast('object', p[2], lineno=p.lineno(1))

def p_expr_cast_bool(p):
    'expr : BOOL_CAST expr'
    p[0] = ast.Cast('bool', p[2], lineno=p.lineno(1))

def p_expr_cast_unset(p):
    'expr : UNSET_CAST expr'
    p[0] = ast.Cast('unset', p[2], lineno=p.lineno(1))

def p_expr_isset(p):
    'expr : ISSET LPAREN isset_variables RPAREN'
    p[0] = ast.IsSet(p[3], lineno=p.lineno(1))

def p_isset_variables(p):
    '''isset_variables : isset_variables COMMA variable
                       | variable'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

def p_expr_empty(p):
    'expr : EMPTY LPAREN expr RPAREN'
    p[0] = ast.Empty(p[3], lineno=p.lineno(1))

def p_expr_eval(p):
    'expr : EVAL LPAREN expr RPAREN'
    p[0] = ast.Eval(p[3], lineno=p.lineno(1))

def p_expr_include(p):
    'expr : INCLUDE expr'
    p[0] = ast.Include(p[2], False, lineno=p.lineno(1))

def p_expr_include_once(p):
    'expr : INCLUDE_ONCE expr'
    p[0] = ast.Include(p[2], True, lineno=p.lineno(1))

def p_expr_require(p):
    'expr : REQUIRE expr'
    p[0] = ast.Require(p[2], False, lineno=p.lineno(1))

def p_expr_require_once(p):
    'expr : REQUIRE_ONCE expr'
    p[0] = ast.Require(p[2], True, lineno=p.lineno(1))

def p_expr_exit(p):
    '''expr : EXIT
            | EXIT LPAREN RPAREN
            | EXIT LPAREN expr RPAREN'''
    if len(p) == 5:
        p[0] = ast.Exit(p[3], lineno=p.lineno(1))
    else:
        p[0] = ast.Exit(None, lineno=p.lineno(1))

def p_expr_print(p):
    'expr : PRINT expr'
    p[0] = ast.Print(p[2], lineno=p.lineno(1))

def p_expr_silence(p):
    'expr : AT expr'
    p[0] = ast.Silence(p[2], lineno=p.lineno(1))

def p_expr_group(p):
    'expr : LPAREN expr RPAREN'
    p[0] = p[2]

def p_scalar(p):
    '''scalar : class_constant
              | common_scalar
              | QUOTE encaps_list QUOTE
              | START_HEREDOC encaps_list END_HEREDOC'''
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[1]

def p_scalar_string_varname(p):
    'scalar : STRING_VARNAME'
    p[0] = ast.Variable('$' + p[1], lineno=p.lineno(1))

def p_scalar_namespace_name(p):
    '''scalar : namespace_name
              | NS_SEPARATOR namespace_name
              | NAMESPACE NS_SEPARATOR namespace_name'''
    if len(p) == 2:
        p[0] = ast.Constant(p[1], lineno=p.lineno(1))
    elif len(p) == 3:
        p[0] = ast.Constant(p[1] + p[2], lineno=p.lineno(1))
    else:
        p[0] = ast.Constant(p[1] + p[2] + p[3], lineno=p.lineno(1))

def p_class_constant(p):
    '''class_constant : class_name DOUBLE_COLON STRING
                      | variable_class_name DOUBLE_COLON STRING'''
    p[0] = ast.StaticProperty(p[1], p[3], lineno=p.lineno(2))

def p_common_scalar_lnumber(p):
    'common_scalar : LNUMBER'
    if p[1].startswith('0x'):
        p[0] = int(p[1], 16)
    elif p[1].startswith('0'):
        p[0] = int(p[1], 8)
    else:
        p[0] = int(p[1])

def p_common_scalar_dnumber(p):
    'common_scalar : DNUMBER'
    p[0] = float(p[1])

def p_common_scalar_string(p):
    'common_scalar : CONSTANT_ENCAPSED_STRING'
    p[0] = p[1][1:-1].replace("\\'", "'").replace('\\\\', '\\')

def p_common_scalar_magic_line(p):
    'common_scalar : LINE'
    p[0] = ast.MagicConstant(p[1].upper(), p.lineno(1), lineno=p.lineno(1))

def p_common_scalar_magic_file(p):
    'common_scalar : FILE'
    value = getattr(p.lexer, 'filename', None)
    p[0] = ast.MagicConstant(p[1].upper(), value, lineno=p.lineno(1))

def p_common_scalar_magic_dir(p):
    'common_scalar : DIR'
    value = getattr(p.lexer, 'filename', None)
    if value is not None:
        value = os.path.dirname(value)
    p[0] = ast.MagicConstant(p[1].upper(), value, lineno=p.lineno(1))

def p_common_scalar_magic_class(p):
    'common_scalar : CLASS_C'
    p[0] = ast.MagicConstant(p[1].upper(), None, lineno=p.lineno(1))

def p_common_scalar_magic_method(p):
    'common_scalar : METHOD_C'
    p[0] = ast.MagicConstant(p[1].upper(), None, lineno=p.lineno(1))

def p_common_scalar_magic_func(p):
    'common_scalar : FUNC_C'
    p[0] = ast.MagicConstant(p[1].upper(), None, lineno=p.lineno(1))

def p_common_scalar_magic_ns(p):
    'common_scalar : NS_C'
    p[0] = ast.MagicConstant(p[1].upper(), None, lineno=p.lineno(1))

def p_static_scalar(p):
    '''static_scalar : common_scalar
                     | QUOTE QUOTE
                     | QUOTE ENCAPSED_AND_WHITESPACE QUOTE'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = ''
    else:
        p[0] = p[2].decode('string_escape')

def p_static_scalar_namespace_name(p):
    '''static_scalar : namespace_name
                     | NS_SEPARATOR namespace_name
                     | NAMESPACE NS_SEPARATOR namespace_name'''
    if len(p) == 2:
        p[0] = ast.Constant(p[1], lineno=p.lineno(1))
    elif len(p) == 3:
        p[0] = ast.Constant(p[1] + p[2], lineno=p.lineno(1))
    else:
        p[0] = ast.Constant(p[1] + p[2] + p[3], lineno=p.lineno(1))

def p_static_scalar_unary_op(p):
    '''static_scalar : PLUS static_scalar
                     | MINUS static_scalar'''
    p[0] = ast.UnaryOp(p[1], p[2], lineno=p.lineno(1))

def p_static_scalar_array(p):
    'static_scalar : ARRAY LPAREN static_array_pair_list RPAREN'
    p[0] = ast.Array(p[3], lineno=p.lineno(1))

def p_static_array_pair_list(p):
    '''static_array_pair_list : empty
                              | static_non_empty_array_pair_list possible_comma'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1]

def p_static_non_empty_array_pair_list_item(p):
    '''static_non_empty_array_pair_list : static_non_empty_array_pair_list COMMA static_scalar
                                        | static_scalar'''
    if len(p) == 4:
        p[0] = p[1] + [ast.ArrayElement(None, p[3], False, lineno=p.lineno(2))]
    else:
        p[0] = [ast.ArrayElement(None, p[1], False, lineno=p.lineno(1))]

def p_static_non_empty_array_pair_list_pair(p):
    '''static_non_empty_array_pair_list : static_non_empty_array_pair_list COMMA static_scalar DOUBLE_ARROW static_scalar
                                        | static_scalar DOUBLE_ARROW static_scalar'''
    if len(p) == 6:
        p[0] = p[1] + [ast.ArrayElement(p[3], p[5], False, lineno=p.lineno(2))]
    else:
        p[0] = [ast.ArrayElement(p[1], p[3], False, lineno=p.lineno(2))]

def p_namespace_name(p):
    '''namespace_name : namespace_name NS_SEPARATOR STRING
                      | STRING'''
    if len(p) == 4:
        p[0] = p[1] + p[2] + p[3]
    else:
        p[0] = p[1]

def p_encaps_list(p):
    '''encaps_list : encaps_list encaps_var
                   | empty'''
    if len(p) == 3:
        if p[1] == '':
            p[0] = p[2]
        else:
            p[0] = ast.BinaryOp('.', p[1], p[2], lineno=p.lineno(2))
    else:
        p[0] = ''

def p_encaps_list_string(p):
    'encaps_list : encaps_list ENCAPSED_AND_WHITESPACE'
    if p[1] == '':
        p[0] = p[2].decode('string_escape')
    else:
        p[0] = ast.BinaryOp('.', p[1], p[2].decode('string_escape'),
                            lineno=p.lineno(2))

def p_encaps_var(p):
    'encaps_var : VARIABLE'
    p[0] = ast.Variable(p[1], lineno=p.lineno(1))

def p_encaps_var_array_offset(p):
    'encaps_var : VARIABLE LBRACKET encaps_var_offset RBRACKET'
    p[0] = ast.ArrayOffset(ast.Variable(p[1], lineno=p.lineno(1)), p[3],
                           lineno=p.lineno(2))

def p_encaps_var_object_property(p):
    'encaps_var : VARIABLE OBJECT_OPERATOR STRING'
    p[0] = ast.ObjectProperty(ast.Variable(p[1], lineno=p.lineno(1)), p[3],
                              lineno=p.lineno(2))

def p_encaps_var_dollar_curly_expr(p):
    'encaps_var : DOLLAR_OPEN_CURLY_BRACES expr RBRACE'
    p[0] = p[2]

def p_encaps_var_dollar_curly_array_offset(p):
    'encaps_var : DOLLAR_OPEN_CURLY_BRACES STRING_VARNAME LBRACKET expr RBRACKET RBRACE'
    p[0] = ast.ArrayOffset(ast.Variable('$' + p[2], lineno=p.lineno(2)), p[4],
                           lineno=p.lineno(3))

def p_encaps_var_curly_variable(p):
    'encaps_var : CURLY_OPEN variable RBRACE'
    p[0] = p[2]

def p_encaps_var_offset_string(p):
    'encaps_var_offset : STRING'
    p[0] = p[1]

def p_encaps_var_offset_num_string(p):
    'encaps_var_offset : NUM_STRING'
    p[0] = int(p[1])

def p_encaps_var_offset_variable(p):
    'encaps_var_offset : VARIABLE'
    p[0] = ast.Variable(p[1], lineno=p.lineno(1))

def p_empty(p):
    'empty : '
    pass

# Error rule for syntax errors
def p_error(t):
    if t:
        raise SyntaxError('invalid syntax', (None, t.lineno, None, t.value))
    else:
        raise SyntaxError('unexpected EOF while parsing', (None, None, None, None))

# Build the grammar
parser = yacc.yacc()

if __name__ == '__main__':
    import readline
    import pprint
    s = ''
    lexer = phplex.lexer
    while True:
       try:
           if s:
               prompt = '     '
           else:
               prompt = lexer.current_state()
               if prompt == 'INITIAL': prompt = 'html'
               prompt += '> '
           s += raw_input(prompt)
       except EOFError:
           break
       if not s: continue
       s += '\n'
       try:
           lexer.lineno = 1
           result = parser.parse(s, lexer=lexer)
       except SyntaxError, e:
           if e.lineno is not None:
               print e, 'near', repr(e.text)
               s = ''
           continue
       if result:
           for item in result:
               if hasattr(item, 'generic'):
                   item = item.generic()
               pprint.pprint(item)
       s = ''

########NEW FILE########
__FILENAME__ = pythonast
import phpast as php
import ast as py

unary_ops = {
    '~': py.Invert,
    '!': py.Not,
    '+': py.UAdd,
    '-': py.USub,
}

bool_ops = {
    '&&': py.And,
    '||': py.Or,
    'and': py.And,
    'or': py.Or,
}

cmp_ops = {
    '!=': py.NotEq,
    '!==': py.NotEq,
    '<>': py.NotEq,
    '<': py.Lt,
    '<=': py.LtE,
    '==': py.Eq,
    '===': py.Eq,
    '>': py.Gt,
    '>=': py.GtE,
}

binary_ops = {
    '+': py.Add,
    '-': py.Sub,
    '*': py.Mult,
    '/': py.Div,
    '%': py.Mod,
    '<<': py.LShift,
    '>>': py.RShift,
    '|': py.BitOr,
    '&': py.BitAnd,
    '^': py.BitXor,
}

casts = {
    'double': 'float',
    'string': 'str',
    'array': 'list',
}

def to_stmt(pynode):
    if not isinstance(pynode, py.stmt):
        pynode = py.Expr(pynode,
                         lineno=pynode.lineno,
                         col_offset=pynode.col_offset)
    return pynode

def from_phpast(node):
    if node is None:
        return py.Pass(**pos(node))

    if isinstance(node, basestring):
        return py.Str(node, **pos(node))

    if isinstance(node, (int, float)):
        return py.Num(node, **pos(node))

    if isinstance(node, php.Array):
        if node.nodes:
            if node.nodes[0].key is not None:
                keys = []
                values = []
                for elem in node.nodes:
                    keys.append(from_phpast(elem.key))
                    values.append(from_phpast(elem.value))
                return py.Dict(keys, values, **pos(node))
            else:
                return py.List([from_phpast(x.value) for x in node.nodes],
                               py.Load(**pos(node)),
                               **pos(node))
        else:
            return py.List([], py.Load(**pos(node)), **pos(node))

    if isinstance(node, php.InlineHTML):
        args = [py.Str(node.data, **pos(node))]
        return py.Call(py.Name('inline_html',
                               py.Load(**pos(node)),
                               **pos(node)),
                       args, [], None, None,
                       **pos(node))

    if isinstance(node, php.Echo):
        return py.Call(py.Name('echo', py.Load(**pos(node)),
                               **pos(node)),
                       map(from_phpast, node.nodes),
                       [], None, None,
                       **pos(node))

    if isinstance(node, php.Print):
        return py.Print(None, [from_phpast(node.node)], True, **pos(node))

    if isinstance(node, php.Exit):
        args = []
        if node.expr is not None:
            args.append(from_phpast(node.expr))
        return py.Raise(py.Call(py.Name('Exit', py.Load(**pos(node)),
                                        **pos(node)),
                                args, [], None, None, **pos(node)),
                        None, None, **pos(node))

    if isinstance(node, php.Return):
        if node.node is None:
            return py.Return(None, **pos(node))
        else:
            return py.Return(from_phpast(node.node), **pos(node))

    if isinstance(node, php.Break):
        assert node.node is None, 'level on break not supported'
        return py.Break(**pos(node))

    if isinstance(node, php.Continue):
        assert node.node is None, 'level on continue not supported'
        return py.Continue(**pos(node))

    if isinstance(node, php.Silence):
        return from_phpast(node.expr)

    if isinstance(node, php.Block):
        return from_phpast(php.If(1, node, [], None, lineno=node.lineno))

    if isinstance(node, php.Unset):
        return py.Delete(map(from_phpast, node.nodes), **pos(node))

    if isinstance(node, php.IsSet) and len(node.nodes) == 1:
        if isinstance(node.nodes[0], php.ArrayOffset):
            return py.Compare(from_phpast(node.nodes[0].expr),
                              [py.In(**pos(node))],
                              [from_phpast(node.nodes[0].node)],
                              **pos(node))
        if isinstance(node.nodes[0], php.ObjectProperty):
            return py.Call(py.Name('hasattr', py.Load(**pos(node)),
                                   **pos(node)),
                           [from_phpast(node.nodes[0].node),
                            from_phpast(node.nodes[0].name)],
                           [], None, None, **pos(node))
        if isinstance(node.nodes[0], php.Variable):
            return py.Compare(py.Str(node.nodes[0].name[1:], **pos(node)),
                              [py.In(**pos(node))],
                              [py.Call(py.Name('vars', py.Load(**pos(node)),
                                               **pos(node)),
                                       [], [], None, None, **pos(node))],
                              **pos(node))
        return py.Compare(from_phpast(node.nodes[0]),
                          [py.IsNot(**pos(node))],
                          [py.Name('None', py.Load(**pos(node)), **pos(node))],
                          **pos(node))

    if isinstance(node, php.Empty):
        return from_phpast(php.UnaryOp('!',
                                       php.BinaryOp('&&',
                                                    php.IsSet([node.expr],
                                                              lineno=node.lineno),
                                                    node.expr,
                                                    lineno=node.lineno),
                                       lineno=node.lineno))

    if isinstance(node, php.Assignment):
        if (isinstance(node.node, php.ArrayOffset)
            and node.node.expr is None):
            return py.Call(py.Attribute(from_phpast(node.node.node),
                                        'append', py.Load(**pos(node)),
                                        **pos(node)),
                           [from_phpast(node.expr)],
                           [], None, None, **pos(node))
        if (isinstance(node.node, php.ObjectProperty)
            and isinstance(node.node.name, php.BinaryOp)):
            return to_stmt(py.Call(py.Name('setattr', py.Load(**pos(node)),
                                   **pos(node)),
                           [from_phpast(node.node.node),
                            from_phpast(node.node.name),
                            from_phpast(node.expr)],
                           [], None, None, **pos(node)))
        return py.Assign([store(from_phpast(node.node))],
                         from_phpast(node.expr),
                         **pos(node))

    if isinstance(node, php.ListAssignment):
        return py.Assign([py.Tuple(map(store, map(from_phpast, node.nodes)),
                                   py.Store(**pos(node)),
                                   **pos(node))],
                          from_phpast(node.expr),
                          **pos(node))

    if isinstance(node, php.AssignOp):
        return from_phpast(php.Assignment(node.left,
                                          php.BinaryOp(node.op[:-1],
                                                       node.left,
                                                       node.right,
                                                       lineno=node.lineno),
                                          False,
                                          lineno=node.lineno))

    if isinstance(node, (php.PreIncDecOp, php.PostIncDecOp)):
        return from_phpast(php.Assignment(node.expr,
                                          php.BinaryOp(node.op[0],
                                                       node.expr,
                                                       1,
                                                       lineno=node.lineno),
                                          False,
                                          lineno=node.lineno))

    if isinstance(node, php.ArrayOffset):
        return py.Subscript(from_phpast(node.node),
                            py.Index(from_phpast(node.expr), **pos(node)),
                            py.Load(**pos(node)),
                            **pos(node))

    if isinstance(node, php.ObjectProperty):
        if isinstance(node.name, (php.Variable, php.BinaryOp)):
            return py.Call(py.Name('getattr', py.Load(**pos(node)),
                                   **pos(node)),
                           [from_phpast(node.node),
                            from_phpast(node.name)],
                           [], None, None, **pos(node))            
        return py.Attribute(from_phpast(node.node),
                            node.name,
                            py.Load(**pos(node)),
                            **pos(node))

    if isinstance(node, php.Constant):
        name = node.name
        if name.lower() == 'true': name = 'True'
        if name.lower() == 'false': name = 'False'
        if name.lower() == 'null': name = 'None'
        return py.Name(name, py.Load(**pos(node)), **pos(node))

    if isinstance(node, php.Variable):
        name = node.name[1:]
        if name == 'this': name = 'self'
        return py.Name(name, py.Load(**pos(node)), **pos(node))

    if isinstance(node, php.Global):
        return py.Global([var.name[1:] for var in node.nodes], **pos(node))

    if isinstance(node, php.Include):
        once = py.Name('True' if node.once else 'False',
                       py.Load(**pos(node)),
                       **pos(node))
        return py.Call(py.Name('include', py.Load(**pos(node)),
                               **pos(node)),
                       [from_phpast(node.expr), once],
                       [], None, None, **pos(node))

    if isinstance(node, php.Require):
        once = py.Name('True' if node.once else 'False',
                       py.Load(**pos(node)),
                       **pos(node))
        return py.Call(py.Name('require', py.Load(**pos(node)),
                               **pos(node)),
                       [from_phpast(node.expr), once],
                       [], None, None, **pos(node))

    if isinstance(node, php.UnaryOp):
        op = unary_ops.get(node.op)
        assert op is not None, "unknown unary operator: '%s'" % node.op
        op = op(**pos(node))
        return py.UnaryOp(op, from_phpast(node.expr), **pos(node))

    if isinstance(node, php.BinaryOp):
        if node.op == '.':
            pattern, pieces = build_format(node.left, node.right)
            if pieces:
                return py.BinOp(py.Str(pattern, **pos(node)),
                                py.Mod(**pos(node)),
                                py.Tuple(map(from_phpast, pieces),
                                         py.Load(**pos(node)),
                                         **pos(node)),
                                **pos(node))
            else:
                return py.Str(pattern % (), **pos(node))
        if node.op in bool_ops:
            op = bool_ops[node.op](**pos(node))
            return py.BoolOp(op, [from_phpast(node.left),
                                  from_phpast(node.right)], **pos(node))
        if node.op in cmp_ops:
            op = cmp_ops[node.op](**pos(node))
            return py.Compare(from_phpast(node.left), [op],
                              [from_phpast(node.right)],
                              **pos(node))
        op = binary_ops.get(node.op)
        assert op is not None, "unknown binary operator: '%s'" % node.op
        op = op(**pos(node))
        return py.BinOp(from_phpast(node.left),
                        op,
                        from_phpast(node.right),
                        **pos(node))

    if isinstance(node, php.TernaryOp):
        return py.IfExp(from_phpast(node.expr),
                        from_phpast(node.iftrue),
                        from_phpast(node.iffalse),
                        **pos(node))

    if isinstance(node, php.Cast):
        return py.Call(py.Name(casts.get(node.type, node.type),
                               py.Load(**pos(node)),
                               **pos(node)),
                       [from_phpast(node.expr)],
                       [], None, None, **pos(node))

    if isinstance(node, php.If):
        orelse = []
        if node.else_:
            for else_ in map(from_phpast, deblock(node.else_.node)):
                orelse.append(to_stmt(else_))
        for elseif in reversed(node.elseifs):
            orelse = [py.If(from_phpast(elseif.expr),
                            map(to_stmt, map(from_phpast, deblock(elseif.node))),
                            orelse, **pos(node))]
        return py.If(from_phpast(node.expr),
                     map(to_stmt, map(from_phpast, deblock(node.node))),
                     orelse, **pos(node))

    if isinstance(node, php.For):
        assert node.test is None or len(node.test) == 1, \
            'only a single test is supported in for-loops'
        return from_phpast(php.Block((node.start or [])
                                     + [php.While(node.test[0] if node.test else 1,
                                                  php.Block(deblock(node.node)
                                                            + (node.count or []),
                                                            lineno=node.lineno),
                                                  lineno=node.lineno)],
                                     lineno=node.lineno))

    if isinstance(node, php.Foreach):
        if node.keyvar is None:
            target = py.Name(node.valvar.name[1:], py.Store(**pos(node)),
                             **pos(node))
        else:
            target = py.Tuple([py.Name(node.keyvar.name[1:],
                                       py.Store(**pos(node))),
                               py.Name(node.valvar.name[1:],
                                       py.Store(**pos(node)))],
                              py.Store(**pos(node)), **pos(node))
        return py.For(target, from_phpast(node.expr),
                      map(to_stmt, map(from_phpast, deblock(node.node))),
                      [], **pos(node))

    if isinstance(node, php.While):
        return py.While(from_phpast(node.expr),
                        map(to_stmt, map(from_phpast, deblock(node.node))),
                        [], **pos(node))

    if isinstance(node, php.DoWhile):
        condition = php.If(php.UnaryOp('!', node.expr, lineno=node.lineno),
                           php.Break(None, lineno=node.lineno),
                           [], None, lineno=node.lineno)
        return from_phpast(php.While(1,
                                     php.Block(deblock(node.node)
                                               + [condition],
                                               lineno=node.lineno),
                                     lineno=node.lineno))

    if isinstance(node, php.Try):
        return py.TryExcept(map(to_stmt, map(from_phpast, node.nodes)),
                            [py.ExceptHandler(py.Name(catch.class_,
                                                      py.Load(**pos(node)),
                                                      **pos(node)),
                                              store(from_phpast(catch.var)),
                                              map(to_stmt, map(from_phpast, catch.nodes)),
                                              **pos(node))
                             for catch in node.catches],
                            [],
                            **pos(node))

    if isinstance(node, php.Throw):
        return py.Raise(from_phpast(node.node), None, None, **pos(node))

    if isinstance(node, php.Function):
        args = []
        defaults = []
        for param in node.params:
            args.append(py.Name(param.name[1:],
                                py.Param(**pos(node)),
                                **pos(node)))
            if param.default is not None:
                defaults.append(from_phpast(param.default))
        body = map(to_stmt, map(from_phpast, node.nodes))
        if not body: body = [py.Pass(**pos(node))]
        return py.FunctionDef(node.name,
                              py.arguments(args, None, None, defaults),
                              body, [], **pos(node))

    if isinstance(node, php.Method):
        args = []
        defaults = []
        decorator_list = []
        if 'static' in node.modifiers:
            decorator_list.append(py.Name('classmethod',
                                          py.Load(**pos(node)),
                                          **pos(node)))
            args.append(py.Name('cls', py.Param(**pos(node)), **pos(node)))
        else:
            args.append(py.Name('self', py.Param(**pos(node)), **pos(node)))
        for param in node.params:
            args.append(py.Name(param.name[1:],
                                py.Param(**pos(node)),
                                **pos(node)))
            if param.default is not None:
                defaults.append(from_phpast(param.default))
        body = map(to_stmt, map(from_phpast, node.nodes))
        if not body: body = [py.Pass(**pos(node))]
        return py.FunctionDef(node.name,
                              py.arguments(args, None, None, defaults),
                              body, decorator_list, **pos(node))

    if isinstance(node, php.Class):
        name = node.name
        bases = []
        extends = node.extends or 'object'
        bases.append(py.Name(extends, py.Load(**pos(node)), **pos(node)))
        body = map(to_stmt, map(from_phpast, node.nodes))
        for stmt in body:
            if (isinstance(stmt, py.FunctionDef)
                and stmt.name in (name, '__construct')):
                stmt.name = '__init__'
        if not body: body = [py.Pass(**pos(node))]
        return py.ClassDef(name, bases, body, [], **pos(node))

    if isinstance(node, (php.ClassConstants, php.ClassVariables)):
        assert len(node.nodes) == 1, \
            'only one class-level assignment supported per line'
        if isinstance(node.nodes[0], php.ClassConstant):
            name = php.Constant(node.nodes[0].name, lineno=node.lineno)
        else:
            name = php.Variable(node.nodes[0].name, lineno=node.lineno)
        initial = node.nodes[0].initial
        if initial is None:
            initial = php.Constant('None', lineno=node.lineno)
        return py.Assign([store(from_phpast(name))],
                         from_phpast(initial),
                         **pos(node))

    if isinstance(node, (php.FunctionCall, php.New)):
        if isinstance(node.name, basestring):
            name = py.Name(node.name, py.Load(**pos(node)), **pos(node))
        else:
            name = py.Subscript(py.Call(py.Name('vars', py.Load(**pos(node)),
                                                **pos(node)),
                                        [], [], None, None, **pos(node)),
                                py.Index(from_phpast(node.name), **pos(node)),
                                py.Load(**pos(node)),
                                **pos(node))
        args, kwargs = build_args(node.params)
        return py.Call(name, args, kwargs, None, None, **pos(node))

    if isinstance(node, php.MethodCall):
        args, kwargs = build_args(node.params)
        return py.Call(py.Attribute(from_phpast(node.node),
                                    node.name,
                                    py.Load(**pos(node)),
                                    **pos(node)),
                       args, kwargs, None, None, **pos(node))

    if isinstance(node, php.StaticMethodCall):
        class_ = node.class_
        if class_ == 'self': class_ = 'cls' 
        args, kwargs = build_args(node.params)
        return py.Call(py.Attribute(py.Name(class_, py.Load(**pos(node)),
                                            **pos(node)),
                                    node.name,
                                    py.Load(**pos(node)),
                                    **pos(node)),
                       args, kwargs, None, None, **pos(node))

    if isinstance(node, php.StaticProperty):
        class_ = node.node
        name = node.name
        if isinstance(name, php.Variable):
            name = name.name[1:]
        return py.Attribute(py.Name(class_, py.Load(**pos(node)),
                                    **pos(node)),
                            name,
                            py.Load(**pos(node)),
                            **pos(node))        

    return py.Call(py.Name('XXX', py.Load(**pos(node)), **pos(node)),
                   [py.Str(str(node), **pos(node))],
                   [], None, None, **pos(node))

def pos(node):
    return {'lineno': getattr(node, 'lineno', 0), 'col_offset': 0}

def store(name):
    name.ctx = py.Store(**pos(name))
    return name

def deblock(node):
    if isinstance(node, php.Block):
        return node.nodes
    else:
        return [node]

def build_args(params):
    args = []
    kwargs = []
    for param in params:
        node = from_phpast(param.node)
        if isinstance(node, py.Assign):
            kwargs.append(py.keyword(node.targets[0].id, node.value))
        else:
            args.append(node)
    return args, kwargs

def build_format(left, right):
    if isinstance(left, basestring):
        pattern, pieces = left.replace('%', '%%'), []
    elif isinstance(left, php.BinaryOp) and left.op == '.':
        pattern, pieces = build_format(left.left, left.right)
    else:
        pattern, pieces = '%s', [left]
    if isinstance(right, basestring):
        pattern += right.replace('%', '%%')
    else:
        pattern += '%s'
        pieces.append(right)
    return pattern, pieces

########NEW FILE########
__FILENAME__ = test_lexer
from phply import phplex

import nose.tools
import pprint

def eq_tokens(input, expected, ignore=('WHITESPACE', 'OPEN_TAG', 'CLOSE_TAG')):
    output = []
    lexer = phplex.full_lexer.clone()
    lexer.input(input)

    while True:
        tok = lexer.token()
        if not tok: break
        if tok.type in ignore: continue
        output.append((tok.type, tok.value))

    print 'Lexer output:'
    pprint.pprint(output)
    print

    print 'Token by token:'
    for out, exp in zip(output, expected):
        print '\tgot:', out, '\texpected:', exp
        nose.tools.eq_(out, exp)

    assert len(output) == len(expected), \
           'output length was %d, expected %s' % (len(output), len(expected))

def test_whitespace():
    input = ' <?  \t\r\n ?>\t\t <?php  ?> <?php\n ?>'
    expected = [
        ('INLINE_HTML', ' '),
        ('OPEN_TAG', '<?'),
        ('WHITESPACE', '  \t\r\n '),
        ('CLOSE_TAG', '?>'),
        ('INLINE_HTML', '\t\t '),
        ('OPEN_TAG', '<?php '),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '?>'),
        ('INLINE_HTML', ' '),
        ('OPEN_TAG', '<?php\n'),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '?>'),
    ]
    eq_tokens(input, expected, ignore=())

def test_open_close_tags():
    input = '<? ?> <% %> <?php ?> <?= ?> <%= %>'
    expected = [
        ('OPEN_TAG', '<?'),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '?>'),
        ('INLINE_HTML', ' '),
        ('OPEN_TAG', '<%'),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '%>'),
        ('INLINE_HTML', ' '),
        ('OPEN_TAG', '<?php '),
        ('CLOSE_TAG', '?>'),
        ('INLINE_HTML', ' '),
        ('OPEN_TAG_WITH_ECHO', '<?='),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '?>'),
        ('INLINE_HTML', ' '),
        ('OPEN_TAG_WITH_ECHO', '<%='),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '%>'),
    ]
    eq_tokens(input, expected, ignore=())

def test_numbers():
    input = """<?
        0
        12
        34.56
        7e8
        9.01e23
        4.5E+6
        .78e-9
        1.e+2
        34.
        .56
        0xdEcAfBaD
        0x123456789abcdef
        0666
    ?>"""
    expected = [
        ('LNUMBER', '0'),
        ('LNUMBER', '12'),
        ('DNUMBER', '34.56'),
        ('DNUMBER', '7e8'),
        ('DNUMBER', '9.01e23'),
        ('DNUMBER', '4.5E+6'),
        ('DNUMBER', '.78e-9'),
        ('DNUMBER', '1.e+2'),
        ('DNUMBER', '34.'),
        ('DNUMBER', '.56'),
        ('LNUMBER', '0xdEcAfBaD'),
        ('LNUMBER', '0x123456789abcdef'),
        ('LNUMBER', '0666'),
    ]
    eq_tokens(input, expected)

def test_strings():
    input = r"""<?
        ''
        'hello'
        'what\'s up'
        'newlines
'
        ""
        "hello"
        "$world"
        "hello $cruel \"world\""
        "end$"
        "newlines
"
    ?>"""
    expected = [
        ('CONSTANT_ENCAPSED_STRING', "''"),
        ('CONSTANT_ENCAPSED_STRING', "'hello'"),
        ('CONSTANT_ENCAPSED_STRING', "'what\\'s up'"),
        ('CONSTANT_ENCAPSED_STRING', "'newlines\n'"),
        ('QUOTE', '"'), ('QUOTE', '"'),
        ('QUOTE', '"'), ('ENCAPSED_AND_WHITESPACE', 'hello'), ('QUOTE', '"'),
        ('QUOTE', '"'), ('VARIABLE', '$world'), ('QUOTE', '"'),
        ('QUOTE', '"'), ('ENCAPSED_AND_WHITESPACE', 'hello '),
        ('VARIABLE', '$cruel'), ('ENCAPSED_AND_WHITESPACE', ' \\"world\\"'), ('QUOTE', '"'),
        ('QUOTE', '"'), ('ENCAPSED_AND_WHITESPACE', 'end$'), ('QUOTE', '"'),
        ('QUOTE', '"'), ('ENCAPSED_AND_WHITESPACE', 'newlines\n'), ('QUOTE', '"'),
    ]
    eq_tokens(input, expected)

def test_string_backslash_escapes():
    input = r"""<?
    "
        \$escape
        \{$escape}
        \${escape}
    "
    ?>"""
    expected = [
        ('QUOTE', '"'),
        ('ENCAPSED_AND_WHITESPACE', "\n        \\$escape\n        \\{"),
        ('VARIABLE', "$escape"),
        ('ENCAPSED_AND_WHITESPACE', "}\n        \\${escape}\n    "),
        ('QUOTE', '"'),
    ]
    eq_tokens(input, expected)

def test_string_offset_lookups():
    input = r"""<?
    "
        $array[offset]
        $too[many][offsets]
        $next[to]$array
        ${curly['offset']}
        $object->property
        $too->many->properties
        $adjacent->object$lookup
        stray -> [ ]
        not[array]
        non->object
    "
    ?>"""
    expected = [
        ('QUOTE', '"'),
        ('ENCAPSED_AND_WHITESPACE', '\n        '),
        ('VARIABLE', '$array'), ('LBRACKET', '['), ('STRING', 'offset'), ('RBRACKET', ']'),
        ('ENCAPSED_AND_WHITESPACE', '\n        '),
        ('VARIABLE', '$too'), ('LBRACKET', '['), ('STRING', 'many'), ('RBRACKET', ']'),
        ('ENCAPSED_AND_WHITESPACE', '[offsets]\n        '),
        ('VARIABLE', '$next'), ('LBRACKET', '['), ('STRING', 'to'), ('RBRACKET', ']'),
        ('VARIABLE', '$array'), ('ENCAPSED_AND_WHITESPACE', '\n        '),
        ('DOLLAR_OPEN_CURLY_BRACES', '${'), ('STRING_VARNAME', 'curly'),
        ('LBRACKET', '['), ('CONSTANT_ENCAPSED_STRING', "'offset'"), ('RBRACKET', ']'),
        ('RBRACE', '}'), ('ENCAPSED_AND_WHITESPACE', '\n        '),
        ('VARIABLE', '$object'), ('OBJECT_OPERATOR', '->'), ('STRING', 'property'),
        ('ENCAPSED_AND_WHITESPACE', '\n        '),
        ('VARIABLE', '$too'), ('OBJECT_OPERATOR', '->'), ('STRING', 'many'),
        ('ENCAPSED_AND_WHITESPACE', '->properties\n        '),
        ('VARIABLE', '$adjacent'), ('OBJECT_OPERATOR', '->'), ('STRING', 'object'),
        ('VARIABLE', '$lookup'),
        ('ENCAPSED_AND_WHITESPACE', '\n        stray -> [ ]\n        not[array]\n        non->object\n    '),
        ('QUOTE', '"'),
    ]
    eq_tokens(input, expected)

def test_string_curly_dollar_expressions():
    input = r"""<?
    "
        a${dollar_curly}b
        c{$curly_dollar}d
        e${$dollar_curly_dollar}f
        {$array[0][1]}
        {$array['two'][3]}
        {$object->items[4]->five}
        {${$nasty}}
        {${funcall()}}
        {${$object->method()}}
        {$object->$variable}
        {$object->$variable[1]}
        {${static_class::variable}}
        {${static_class::$variable}}
    "
    ?>"""
    expected = [
        ('QUOTE', '"'),
        ('ENCAPSED_AND_WHITESPACE', "\n        a"),
        ('DOLLAR_OPEN_CURLY_BRACES', "${"), ('STRING_VARNAME', "dollar_curly"), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "b\n        c"),
        ('CURLY_OPEN', "{"), ('VARIABLE', "$curly_dollar"), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "d\n        e"),
        ('DOLLAR_OPEN_CURLY_BRACES', "${"), ('VARIABLE', "$dollar_curly_dollar"), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "f\n        "),
        ('CURLY_OPEN', "{"), ('VARIABLE', "$array"),
        ('LBRACKET', '['), ('LNUMBER', "0"), ('RBRACKET', ']'),
        ('LBRACKET', '['), ('LNUMBER', "1"), ('RBRACKET', ']'),
        ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('VARIABLE', "$array"),
        ('LBRACKET', '['), ('CONSTANT_ENCAPSED_STRING', "'two'"), ('RBRACKET', ']'),
        ('LBRACKET', '['), ('LNUMBER', "3"), ('RBRACKET', ']'),
        ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('VARIABLE', "$object"),
        ('OBJECT_OPERATOR', "->"), ('STRING', "items"),
        ('LBRACKET', '['), ('LNUMBER', "4"), ('RBRACKET', ']'),
        ('OBJECT_OPERATOR', "->"), ('STRING', "five"),
        ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('DOLLAR', '$'), ('LBRACE', '{'),
        ('VARIABLE', "$nasty"), ('RBRACE', '}'), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('DOLLAR', "$"), ('LBRACE', "{"), ('STRING', "funcall"),
        ('LPAREN', "("), ('RPAREN', ")"), ('RBRACE', '}'), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('DOLLAR', "$"), ('LBRACE', "{"),
        ('VARIABLE', "$object"), ('OBJECT_OPERATOR', "->"), ('STRING', "method"),
        ('LPAREN', "("), ('RPAREN', ")"),
        ('RBRACE', '}'), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"),
        ('VARIABLE', "$object"), ('OBJECT_OPERATOR', "->"), ('VARIABLE', "$variable"),
        ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"),
        ('VARIABLE', "$object"), ('OBJECT_OPERATOR', "->"), ('VARIABLE', "$variable"),
        ('LBRACKET', '['), ('LNUMBER', "1"), ('RBRACKET', ']'),
        ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('DOLLAR', "$"), ('LBRACE', "{"),
        ('STRING', "static_class"), ('DOUBLE_COLON', "::"), ('STRING', "variable"),
        ('RBRACE', '}'), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n        "),
        ('CURLY_OPEN', "{"), ('DOLLAR', "$"), ('LBRACE', "{"),
        ('STRING', "static_class"), ('DOUBLE_COLON', "::"), ('VARIABLE', "$variable"),
        ('RBRACE', '}'), ('RBRACE', '}'),
        ('ENCAPSED_AND_WHITESPACE', "\n    "),
        ('QUOTE', '"'),
    ]
    eq_tokens(input, expected)

def test_heredoc():
    input = r"""<?
        echo <<<EOT
This is a "$heredoc" with some $embedded->variables
This is not the EOT; this is:
EOT;
    ?>"""
    expected = [
        ('OPEN_TAG', '<?'),
        ('WHITESPACE', '\n        '),
        ('ECHO', 'echo'),
        ('WHITESPACE', ' '),
        ('START_HEREDOC', '<<<EOT\n'),
        ('ENCAPSED_AND_WHITESPACE', 'This'),     # We fudge a bit, producing more
        ('ENCAPSED_AND_WHITESPACE', ' is a "'),  # tokens than necessary.
        ('VARIABLE', '$heredoc'),
        ('ENCAPSED_AND_WHITESPACE', '" with some '),
        ('VARIABLE', '$embedded'),
        ('OBJECT_OPERATOR', '->'),
        ('STRING', 'variables'),
        ('ENCAPSED_AND_WHITESPACE', '\n'),
        ('ENCAPSED_AND_WHITESPACE', 'This'),
        ('ENCAPSED_AND_WHITESPACE', ' is not the EOT; this is:\n'),
        ('END_HEREDOC', 'EOT'),
        ('SEMI', ';'),
        ('WHITESPACE', '\n    '),
        ('CLOSE_TAG', '?>'),
    ]
    eq_tokens(input, expected, ignore=())

def test_heredoc_backslash_newline():
    input = r"""<?
        echo <<<EOT
oh noes!\
EOT;
    ?>"""
    expected = [
        ('OPEN_TAG', '<?'),
        ('WHITESPACE', '\n        '),
        ('ECHO', 'echo'),
        ('WHITESPACE', ' '),
        ('START_HEREDOC', '<<<EOT\n'),
        ('ENCAPSED_AND_WHITESPACE', 'oh'),
        ('ENCAPSED_AND_WHITESPACE', ' noes!'),
        ('ENCAPSED_AND_WHITESPACE', '\\\n'),
        ('END_HEREDOC', 'EOT'),
        ('SEMI', ';'),
        ('WHITESPACE', '\n    '),
        ('CLOSE_TAG', '?>'),
    ]
    eq_tokens(input, expected, ignore=())
    
def test_commented_close_tag():
    input = '<? {\n// ?>\n<?\n} ?>'
    expected = [
        ('OPEN_TAG', '<?'),
        ('WHITESPACE', ' '),
        ('LBRACE', '{'),
        ('WHITESPACE', '\n'),
        ('COMMENT', '// '),
        ('CLOSE_TAG', '?>\n'),  # PHP seems inconsistent regarding
        ('OPEN_TAG', '<?'),     # when \n is included in CLOSE_TAG
        ('WHITESPACE', '\n'),
        ('RBRACE', '}'),
        ('WHITESPACE', ' '),
        ('CLOSE_TAG', '?>'),
    ]
    eq_tokens(input, expected, ignore=())

def test_punctuation():
    input = '<? ([{}]):;,.@ ?>'
    expected = [
        ('LPAREN', '('),
        ('LBRACKET', '['),
        ('LBRACE', '{'),
        ('RBRACE', '}'),
        ('RBRACKET', ']'),
        ('RPAREN', ')'),
        ('COLON', ':'),
        ('SEMI', ';'),
        ('COMMA', ','),
        ('CONCAT', '.'),
        ('AT', '@'),
    ]
    eq_tokens(input, expected)

########NEW FILE########
__FILENAME__ = test_parser
from phply import phplex
from phply.phpparse import parser
from phply.phpast import *

import nose.tools
import pprint

def eq_ast(input, expected, filename=None):
    lexer = phplex.lexer.clone()
    lexer.filename = filename
    output = parser.parse(input, lexer=lexer)
    resolve_magic_constants(output)

    print 'Parser output:'
    pprint.pprint(output)
    print

    print 'Node by node:'
    for out, exp in zip(output, expected):
        print '\tgot:', out, '\texpected:', exp
        nose.tools.eq_(out, exp)

    assert len(output) == len(expected), \
           'output length was %d, expected %s' % (len(output), len(expected))

def test_inline_html():
    input = 'html <?php // php ?> more html'
    expected = [InlineHTML('html '), InlineHTML(' more html')]
    eq_ast(input, expected)

def test_echo():
    input = '<?php echo "hello, world!"; ?>'
    expected = [Echo(["hello, world!"])]
    eq_ast(input, expected)

def test_open_tag_with_echo():
    input = '<?= "hello, world!" ?><?= "test"; EXTRA; ?>'
    expected = [
        Echo(["hello, world!"]),
        Echo(["test"]),
        Constant('EXTRA'),
    ]
    eq_ast(input, expected)

def test_exit():
    input = '<?php exit; exit(); exit(123); die; die(); die(456); ?>'
    expected = [
        Exit(None), Exit(None), Exit(123),
        Exit(None), Exit(None), Exit(456),
    ]
    eq_ast(input, expected)

def test_isset():
    input = r"""<?php
        isset($a);
        isset($b->c);
        isset($d['e']);
        isset($f, $g);
    ?>"""
    expected = [
        IsSet([Variable('$a')]),
        IsSet([ObjectProperty(Variable('$b'), 'c')]),
        IsSet([ArrayOffset(Variable('$d'), 'e')]),
        IsSet([Variable('$f'), Variable('$g')]),
    ]
    eq_ast(input, expected)

def test_namespace_names():
    input = r"""<?php
        foo;
        bar\baz;
        one\too\tree;
        \top;
        \top\level;
        namespace\level;
    ?>"""
    expected = [
        Constant(r'foo'),
        Constant(r'bar\baz'),
        Constant(r'one\too\tree'),
        Constant(r'\top'),
        Constant(r'\top\level'),
        Constant(r'namespace\level'),
    ]
    eq_ast(input, expected)

def test_unary_ops():
    input = r"""<?
        $a = -5;
        $b = +6;
        $c = !$d;
        $e = ~$f;
    ?>"""
    expected = [
        Assignment(Variable('$a'), UnaryOp('-', 5), False),
        Assignment(Variable('$b'), UnaryOp('+', 6), False),
        Assignment(Variable('$c'), UnaryOp('!', Variable('$d')), False),
        Assignment(Variable('$e'), UnaryOp('~', Variable('$f')), False),
    ]
    eq_ast(input, expected)

def test_assignment_ops():
    input = r"""<?
        $a += 5;
        $b -= 6;
        $c .= $d;
        $e ^= $f;
    ?>"""
    expected = [
        AssignOp('+=', Variable('$a'), 5),
        AssignOp('-=', Variable('$b'), 6),
        AssignOp('.=', Variable('$c'), Variable('$d')),
        AssignOp('^=', Variable('$e'), Variable('$f')),
    ]
    eq_ast(input, expected)

def test_object_properties():
    input = r"""<?
        $object->property;
        $object->foreach;
        $object->$variable;
        $object->$variable->schmariable;
        $object->$variable->$schmariable;
    ?>"""
    expected = [
        ObjectProperty(Variable('$object'), 'property'),
        ObjectProperty(Variable('$object'), 'foreach'),
        ObjectProperty(Variable('$object'), Variable('$variable')),
        ObjectProperty(ObjectProperty(Variable('$object'), Variable('$variable')),
                       'schmariable'),
        ObjectProperty(ObjectProperty(Variable('$object'), Variable('$variable')),
                       Variable('$schmariable')),
    ]
    eq_ast(input, expected)

def test_string_unescape():
    input = r"""<?
        '\r\n\t\\\'';
        "\r\n\t\\\"";
    ?>"""
    expected = [
        r"\r\n\t\'",
        "\r\n\t\\\"",
    ]
    eq_ast(input, expected)

def test_string_offset_lookups():
    input = r"""<?
        "$array[offset]";
        "$array[42]";
        "$array[$variable]";
        "${curly['offset']}";
        "$too[many][offsets]";
        "$next[to]$array";
        "$object->property";
        "$too->many->properties";
        "$adjacent->object$lookup";
        "$two->$variables";
        "stray -> [ ]";
        "not[array]";
        "non->object";
    ?>"""
    expected = [
        ArrayOffset(Variable('$array'), 'offset'),
        ArrayOffset(Variable('$array'), 42),
        ArrayOffset(Variable('$array'), Variable('$variable')),
        ArrayOffset(Variable('$curly'), 'offset'),
        BinaryOp('.', ArrayOffset(Variable('$too'), 'many'), '[offsets]'),
        BinaryOp('.', ArrayOffset(Variable('$next'), 'to'), Variable('$array')),
        ObjectProperty(Variable('$object'), 'property'),
        BinaryOp('.', ObjectProperty(Variable('$too'), 'many'), '->properties'),
        BinaryOp('.', ObjectProperty(Variable('$adjacent'), 'object'), Variable('$lookup')),
        BinaryOp('.', BinaryOp('.', Variable('$two'), '->'), Variable('$variables')),
        'stray -> [ ]',
        'not[array]',
        'non->object',
    ]
    eq_ast(input, expected)

def test_string_curly_dollar_expressions():
    input = r"""<?
        "a${dollar_curly}b";
        "c{$curly_dollar}d";
        "e${$dollar_curly_dollar}f";
        "{$array[0][1]}";
        "{$array['two'][3]}";
        "{$object->items[4]->five}";
        "{${$nasty}}";
        "{${funcall()}}";
        "{${$object->method()}}";
        "{$object->$variable}";
        "{$object->$variable[1]}";
        "{${static_class::constant}}";
        "{${static_class::$variable}}";
    ?>"""
    expected = [
        BinaryOp('.', BinaryOp('.', 'a', Variable('$dollar_curly')), 'b'),
        BinaryOp('.', BinaryOp('.', 'c', Variable('$curly_dollar')), 'd'),
        BinaryOp('.', BinaryOp('.', 'e', Variable('$dollar_curly_dollar')), 'f'),
        ArrayOffset(ArrayOffset(Variable('$array'), 0), 1),
        ArrayOffset(ArrayOffset(Variable('$array'), 'two'), 3),
        ObjectProperty(ArrayOffset(ObjectProperty(Variable('$object'), 'items'), 4), 'five'),
        Variable(Variable('$nasty')),
        Variable(FunctionCall('funcall', [])),
        Variable(MethodCall(Variable('$object'), 'method', [])),
        ObjectProperty(Variable('$object'), Variable('$variable')),
        ObjectProperty(Variable('$object'), ArrayOffset(Variable('$variable'), 1)),
        Variable(StaticProperty('static_class', 'constant')),
        Variable(StaticProperty('static_class', Variable('$variable'))),
    ]
    eq_ast(input, expected)

def test_heredoc():
    input = r"""<?
        echo <<<EOT
This is a "$heredoc" with some $embedded->variables.
This is not the EOT; this is:
EOT;
    ?>"""
    expected = [
        Echo([BinaryOp('.',
                       BinaryOp('.',
                                BinaryOp('.',
                                         BinaryOp('.',
                                                  BinaryOp('.',
                                                           BinaryOp('.',
                                                                    BinaryOp('.',
                                                                             'This',
                                                                             ' is a "'),
                                                                    Variable('$heredoc')),
                                                           '" with some '),
                                                  ObjectProperty(Variable('$embedded'),
                                                                 'variables')),
                                         '.\n'),
                                'This'),
                       ' is not the EOT; this is:\n')]),
    ]
    eq_ast(input, expected)

def test_function_calls():
    input = r"""<?
        f();
        doit($arg1, &$arg2, 3 + 4);
        name\spaced();
        \name\spaced();
        namespace\d();
    ?>"""
    expected = [
        FunctionCall('f', []),
        FunctionCall('doit',
                     [Parameter(Variable('$arg1'), False),
                      Parameter(Variable('$arg2'), True),
                      Parameter(BinaryOp('+', 3, 4), False)]),
        FunctionCall('name\\spaced', []),
        FunctionCall('\\name\\spaced', []),
        FunctionCall('namespace\\d', []),
    ]
    eq_ast(input, expected)                   

def test_method_calls():
    input = r"""<?
        $obj->meth($a, &$b, $c . $d);
        $chain->one($x)->two(&$y);
    ?>"""
    expected = [
        MethodCall(Variable('$obj'), 'meth',
                   [Parameter(Variable('$a'), False),
                    Parameter(Variable('$b'), True),
                    Parameter(BinaryOp('.', Variable('$c'), Variable('$d')), False)]),
        MethodCall(MethodCall(Variable('$chain'),
                              'one', [Parameter(Variable('$x'), False)]),
                   'two', [Parameter(Variable('$y'), True)]),
    ]
    eq_ast(input, expected)

def test_if():
    input = r"""<?
        if (1)
            if (2)
                echo 3;
            else
                echo 4;
        else
            echo 5;
        if ($a < $b) {
            return -1;
        } elseif ($a > $b) {
            return 1;
        } elseif ($a == $b) {
            return 0;
        } else {
            return 'firetruck';
        }
        if ($if):
            echo 'a';
        elseif ($elseif):
            echo 'b';
        else:
            echo 'c';
        endif;
    ?>"""
    expected = [
        If(1,
           If(2,
              Echo([3]),
              [],
              Else(Echo([4]))),
           [],
           Else(Echo([5]))),
        If(BinaryOp('<', Variable('$a'), Variable('$b')),
           Block([Return(UnaryOp('-', 1))]),
           [ElseIf(BinaryOp('>', Variable('$a'), Variable('$b')),
                   Block([Return(1)])),
            ElseIf(BinaryOp('==', Variable('$a'), Variable('$b')),
                   Block([Return(0)]))],
           Else(Block([Return('firetruck')]))),
        If(Variable('$if'),
           Block([Echo(['a'])]),
           [ElseIf(Variable('$elseif'),
                   Block([Echo(['b'])]))],
           Else(Block([Echo(['c'])]))),
    ]
    eq_ast(input, expected)

def test_foreach():
    input = r"""<?
        foreach ($foo as $bar) {
            echo $bar;
        }
        foreach ($spam as $ham => $eggs) {
            echo "$ham: $eggs";
        }
        foreach (complex($expression) as &$ref)
            $ref++;
        foreach ($what as &$de => &$dealy):
            yo();
            yo();
        endforeach;
    ?>"""
    expected = [
        Foreach(Variable('$foo'), None, ForeachVariable('$bar', False),
                Block([Echo([Variable('$bar')])])),
        Foreach(Variable('$spam'),
                ForeachVariable('$ham', False),
                ForeachVariable('$eggs', False),
                Block([Echo([BinaryOp('.',
                                      BinaryOp('.', Variable('$ham'), ': '),
                                      Variable('$eggs'))])])),
        Foreach(FunctionCall('complex', [Parameter(Variable('$expression'),
                                                   False)]),
                None, ForeachVariable('$ref', True),
                PostIncDecOp('++', Variable('$ref'))),
        Foreach(Variable('$what'),
                ForeachVariable('$de', True),
                ForeachVariable('$dealy', True),
                Block([FunctionCall('yo', []),
                       FunctionCall('yo', [])])),
    ]
    eq_ast(input, expected)

def test_global_variables():
    input = r"""<?
        global $foo, $bar;
        global $$yo;
        global ${$dawg};
        global ${$obj->prop};
    ?>"""
    expected = [
        Global([Variable('$foo'), Variable('$bar')]),
        Global([Variable(Variable('$yo'))]),
        Global([Variable(Variable('$dawg'))]),
        Global([Variable(ObjectProperty(Variable('$obj'), 'prop'))]),
    ]
    eq_ast(input, expected)

def test_variable_variables():
    input = r"""<?
        $$a = $$b;
        $$a =& $$b;
        ${$a} = ${$b};
        ${$a} =& ${$b};
        $$a->b;
        $$$triple;
    ?>"""
    expected = [
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), False),
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), True),
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), False),
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), True),
        ObjectProperty(Variable(Variable('$a')), 'b'),
        Variable(Variable(Variable('$triple'))),
    ]
    eq_ast(input, expected)

def test_classes():
    input = r"""<?
        FINAL class Clown extends Unicycle implements RedNose, FacePaint {
            const the = 'only', constant = 'is';
            const change = 'chump';
            var $iable = 999, $nein;
            protected sTaTiC $x;
            public function conjunction_junction($arg1, $arg2) {
                return $arg1 . $arg2;
            }
        }
        class Stub {}
    ?>"""
    expected = [
        Class('Clown', 'final', 'Unicycle', ['RedNose', 'FacePaint'], [
            ClassConstants([ClassConstant('the', 'only'),
                            ClassConstant('constant', 'is')]),
            ClassConstants([ClassConstant('change', 'chump')]),
            ClassVariables([], [ClassVariable('$iable', 999),
                                ClassVariable('$nein', None)]),
            ClassVariables(['protected', 'static'],
                           [ClassVariable('$x', None)]),
            Method('conjunction_junction',
                   ['public'], 
                   [FormalParameter('$arg1', None, False, None),
                    FormalParameter('$arg2', None, False, None)],
                   [Return(BinaryOp('.', Variable('$arg1'), Variable('$arg2')))],
                   False),
        ]),
        Class('Stub', None, None, [], []),
    ]
    eq_ast(input, expected)

def test_new():
    input = r"""<?
        new Foo;
        new Foo();
        new Bar(1, 2, 3);
        $crusty =& new OldSyntax();
        new name\Spaced();
        new \name\Spaced();
        new namespace\D();
    ?>"""
    expected = [
        New('Foo', []),
        New('Foo', []),
        New('Bar', [Parameter(1, False),
                    Parameter(2, False),
                    Parameter(3, False)]),
        Assignment(Variable('$crusty'), New('OldSyntax', []), True),
        New('name\\Spaced', []),
        New('\\name\\Spaced', []),
        New('namespace\\D', []),
    ]
    eq_ast(input, expected)

def test_exceptions():
    input = r"""<?
        try {
            $a = $b + $c;
            throw new Food($a);
        } catch (Food $f) {
            echo "Received food: $f";
        } catch (\Bar\Food $f) {
            echo "Received bar food: $f";
        } catch (namespace\Food $f) {
            echo "Received namespace food: $f";
        } catch (Exception $e) {
            echo "Problem?";
        }
    ?>"""
    expected = [
        Try([
            Assignment(Variable('$a'),
                       BinaryOp('+', Variable('$b'), Variable('$c')),
                       False),
            Throw(New('Food', [Parameter(Variable('$a'), False)])),
        ], [
            Catch('Food', Variable('$f'), [
                Echo([BinaryOp('.', 'Received food: ', Variable('$f'))])
            ]),
            Catch('\\Bar\\Food', Variable('$f'), [
                Echo([BinaryOp('.', 'Received bar food: ', Variable('$f'))])
            ]),
            Catch('namespace\\Food', Variable('$f'), [
                Echo([BinaryOp('.', 'Received namespace food: ', Variable('$f'))])
            ]),
            Catch('Exception', Variable('$e'), [
                Echo(['Problem?']),
            ]),
        ])
    ]
    eq_ast(input, expected)

def test_declare():
    input = r"""<?
        declare(ticks=1) {
            echo 'hi';
        }
        declare(ticks=2);
        declare(ticks=3):
        echo 'bye';
        enddeclare;
    ?>"""
    expected = [
        Declare([Directive('ticks', 1)], Block([
            Echo(['hi']),
        ])),
        Declare([Directive('ticks', 2)], None),
        Declare([Directive('ticks', 3)], Block([
            Echo(['bye']),
        ])),
    ]
    eq_ast(input, expected)

def test_instanceof():
    input = r"""<?
        if ($foo iNsTaNcEoF Bar) {
            echo '$foo is a bar';
        }
        $foo instanceof $bar;
    ?>"""
    expected = [
        If(BinaryOp('instanceof', Variable('$foo'), Constant('Bar')),
           Block([Echo(['$foo is a bar'])]), [], None),
        BinaryOp('instanceof', Variable('$foo'), Variable('$bar')),
    ]
    eq_ast(input, expected)

def test_static_members():
    input = r"""<?
        Ztatic::constant;
        Ztatic::$variable;
        Ztatic::method();
        Ztatic::$variable_method();
        static::late_binding;
        STATIC::$late_binding;
        Static::late_binding();
    ?>"""
    expected = [
        StaticProperty('Ztatic', 'constant'),
        StaticProperty('Ztatic', Variable('$variable')),
        StaticMethodCall('Ztatic', 'method', []),
        StaticMethodCall('Ztatic', Variable('$variable_method'), []),
        StaticProperty('static', 'late_binding'),
        StaticProperty('static', Variable('$late_binding')),
        StaticMethodCall('static', 'late_binding', []),
    ]
    eq_ast(input, expected)

def test_casts():
    input = r"""<?
        (aRray) $x;
        (bOol) $x;
        (bOolean) $x;
        (rEal) $x;
        (dOuble) $x;
        (fLoat) $x;
        (iNt) $x;
        (iNteger) $x;
        (sTring) $x;
        (uNset) $x;
    ?>"""
    expected = [
        Cast('array', Variable('$x')),
        Cast('bool', Variable('$x')),
        Cast('bool', Variable('$x')),
        Cast('double', Variable('$x')),
        Cast('double', Variable('$x')),
        Cast('double', Variable('$x')),
        Cast('int', Variable('$x')),
        Cast('int', Variable('$x')),
        Cast('string', Variable('$x')),
        Cast('unset', Variable('$x')),
    ]
    eq_ast(input, expected)

def test_namespaces():
    input = r"""<?
        namespace my\name;
        namespace my\name {
            foo();
            bar();
        }
        namespace {
            foo();
            bar();
        }
    ?>"""
    expected = [
        Namespace('my\\name', []),
        Namespace('my\\name', [FunctionCall('foo', []),
                               FunctionCall('bar', [])]),
        Namespace(None, [FunctionCall('foo', []),
                         FunctionCall('bar', [])]),
    ]
    eq_ast(input, expected)

def test_use_declarations():
    input = r"""<?
        use me;
        use \me;
        use \me\please;
        use my\name as foo;
        use a, b;
        use a as b, \c\d\e as f;
    ?>"""
    expected = [
        UseDeclarations([UseDeclaration('me', None)]),
        UseDeclarations([UseDeclaration('\\me', None)]),
        UseDeclarations([UseDeclaration('\\me\\please', None)]),
        UseDeclarations([UseDeclaration('my\\name', 'foo')]),
        UseDeclarations([UseDeclaration('a', None),
                         UseDeclaration('b', None)]),
        UseDeclarations([UseDeclaration('a', 'b'),
                         UseDeclaration('\\c\\d\\e', 'f')]),
    ]
    eq_ast(input, expected)

def test_constant_declarations():
    input = r"""<?
        const foo = 42;
        const bar = 'baz', wat = \DOO;
        const ant = namespace\level;
        const dq1 = "";
        const dq2 = "nothing fancy";
    ?>"""
    expected = [
        ConstantDeclarations([ConstantDeclaration('foo', 42)]),
        ConstantDeclarations([ConstantDeclaration('bar', 'baz'),
                              ConstantDeclaration('wat', Constant('\\DOO'))]),
        ConstantDeclarations([ConstantDeclaration('ant', Constant('namespace\\level'))]),
        ConstantDeclarations([ConstantDeclaration('dq1', '')]),
        ConstantDeclarations([ConstantDeclaration('dq2', 'nothing fancy')]),
    ]
    eq_ast(input, expected)

def test_closures():
    input = r"""<?
        $greet = function($name) {
            printf("Hello %s\r\n", $name);
        };
        $greet('World');
        $cb = function&($a, &$b) use ($c, &$d) {};
    ?>"""
    expected = [
        Assignment(Variable('$greet'),
                   Closure([FormalParameter('$name', None, False, None)],
                           [],
                           [FunctionCall('printf',
                                         [Parameter('Hello %s\r\n', False),
                                          Parameter(Variable('$name'), False)])],
                           False),
                   False),
        FunctionCall(Variable('$greet'), [Parameter('World', False)]),
        Assignment(Variable('$cb'),
                   Closure([FormalParameter('$a', None, False, None),
                            FormalParameter('$b', None, True, None)],
                           [LexicalVariable('$c', False),
                            LexicalVariable('$d', True)],
                           [],
                           True),
                   False),
    ]
    eq_ast(input, expected)

def test_magic_constants():
    input = r"""<?
        namespace Shmamespace;

        function p($x) {
            echo __FUNCTION__ . ': ' . $x . "\n";
        }

        class Bar {
            function __construct() {
                p(__LINE__);
                p(__DIR__);
                p(__FILE__);
                p(__NAMESPACE__);
                p(__CLASS__);
                p(__METHOD__);
            }
        }

        new Bar();
    ?>"""
    expected = [
        Namespace('Shmamespace', []),
        Function('p', [FormalParameter('$x', None, False, None)], [
            Echo([BinaryOp('.', BinaryOp('.', BinaryOp('.',
                MagicConstant('__FUNCTION__', 'Shmamespace\\p'), ': '),
                Variable('$x')), '\n')])
        ], False),
        Class('Bar', None, None, [],
              [Method('__construct', [], [],
                      [FunctionCall('p', [Parameter(MagicConstant('__LINE__', 10), False)]),
                       FunctionCall('p', [Parameter(MagicConstant('__DIR__', '/my/dir'), False)]),
                       FunctionCall('p', [Parameter(MagicConstant('__FILE__', '/my/dir/file.php'), False)]),
                       FunctionCall('p', [Parameter(MagicConstant('__NAMESPACE__', 'Shmamespace'), False)]),
                       FunctionCall('p', [Parameter(MagicConstant('__CLASS__', 'Shmamespace\\Bar'), False)]),
                       FunctionCall('p', [Parameter(MagicConstant('__METHOD__', 'Shmamespace\\Bar::__construct'), False)])], False)]),
        New('Bar', []),
    ]
    eq_ast(input, expected, filename='/my/dir/file.php')

def test_type_hinting():
    input = r"""<?
    function foo(Foo $var1, Bar $var2=1, Quux &$var3, Corge &$var4=1) {
    }
    ?>""";
    expected = [
        Function('foo', 
            [FormalParameter('$var1', None, False, 'Foo'),
             FormalParameter('$var2', 1, False, 'Bar'),
             FormalParameter('$var3', None, True, 'Quux'),
             FormalParameter('$var4', 1, True, 'Corge')],
            [],
            False)]
    eq_ast(input, expected)


########NEW FILE########
__FILENAME__ = php2jinja
#!/usr/bin/env python

# php2jinja.py - Converts PHP to Jinja2 templates (experimental)
# Usage: php2jinja.py < input.php > output.html

import sys
sys.path.append('..')

from phply.phplex import lexer
from phply.phpparse import parser
from phply.phpast import *

input = sys.stdin
output = sys.stdout

op_map = {
    '&&':  'and',
    '||':  'or',
    '!':   'not',
    '!==': '!=',
    '===': '==',
    '.':   '~',
}

def unparse(nodes):
    result = []
    for node in nodes:
        result.append(unparse_node(node))
    return ''.join(result)

def unparse_node(node, is_expr=False):
    if isinstance(node, (basestring, int, float)):
        return repr(node)

    if isinstance(node, InlineHTML):
        return str(node.data)

    if isinstance(node, Constant):
        if node.name.lower() == 'null':
            return 'None'
        return str(node.name)

    if isinstance(node, Variable):
        return str(node.name[1:])

    if isinstance(node, Echo):
        return '{{ %s }}' % (''.join(unparse_node(x, True) for x in node.nodes))

    if isinstance(node, (Include, Require)):
        return '{%% include %s -%%}' % (unparse_node(node.expr, True))

    if isinstance(node, Block):
        return ''.join(unparse_node(x) for x in node.nodes)

    if isinstance(node, ArrayOffset):
        return '%s[%s]' % (unparse_node(node.node, True),
                           unparse_node(node.expr, True))

    if isinstance(node, ObjectProperty):
        return '%s.%s' % (unparse_node(node.node, True), node.name)

    if isinstance(node, Array):
        elems = []
        for elem in node.nodes:
            elems.append(unparse_node(elem, True))
        if node.nodes and node.nodes[0].key is not None:
            return '{%s}' % ', '.join(elems)
        else:
            return '[%s]' % ', '.join(elems)

    if isinstance(node, ArrayElement):
        if node.key:
            return '%s: %s' % (unparse_node(node.key, True),
                               unparse_node(node.value, True))
        else:
            return unparse_node(node.value, True)

    if isinstance(node, Assignment):
        if isinstance(node.node, ArrayOffset) and node.node.expr is None:
            return '{%% do %s.append(%s) -%%}' % (unparse_node(node.node.node, None),
                                                 unparse_node(node.expr, True))
        else:
            return '{%% set %s = %s -%%}' % (unparse_node(node.node, True),
                                            unparse_node(node.expr, True))

    if isinstance(node, UnaryOp):
        op = op_map.get(node.op, node.op)
        return '(%s %s)' % (op, unparse_node(node.expr, True))

    if isinstance(node, BinaryOp):
        op = op_map.get(node.op, node.op)
        return '(%s %s %s)' % (unparse_node(node.left, True), op,
                               unparse_node(node.right, True))

    if isinstance(node, TernaryOp):
        return '(%s if %s else %s)' % (unparse_node(node.iftrue, True),
                                       unparse_node(node.expr, True),
                                       unparse_node(node.iffalse, True))

    if isinstance(node, IsSet):
        if len(node.nodes) == 1:
            return '(%s is defined)' % unparse_node(node.nodes[0], True)
        else:
            tests = ['(%s is defined)' % unparse_node(n, True)
                     for n in node.nodes]
            return '(' + ' and '.join(tests) + ')'

    if isinstance(node, Empty):
        return '(not %s)' % (unparse_node(node.expr, True))

    if isinstance(node, Silence):
        return unparse_node(node.expr, True)

    if isinstance(node, Cast):
        filter = ''
        if node.type in ('int', 'float', 'string'):
            filter = '|%s' % node.type
        return '%s%s' % (unparse_node(node.expr, True), filter)

    if isinstance(node, If):
        body = unparse_node(node.node)
        for elseif in node.elseifs:
            body += '{%% elif %s -%%}%s' % (unparse_node(elseif.expr, True),
                                           unparse_node(elseif.node))
        if node.else_:
            body += '{%% else -%%}%s' % (unparse_node(node.else_.node))
        return '{%% if %s -%%}%s{%% endif -%%}' % (unparse_node(node.expr, True),
                                                 body)

    if isinstance(node, While):
        dummy = Foreach(node.expr, None, ForeachVariable('$XXX', False), node.node)
        return unparse_node(dummy)

    if isinstance(node, Foreach):
        var = node.valvar.name[1:]
        if node.keyvar:
            var = '%s, %s' % (node.keyvar.name[1:], var)
        return '{%% for %s in %s -%%}%s{%% endfor -%%}' % (var,
                                                         unparse_node(node.expr, True),
                                                         unparse_node(node.node))

    if isinstance(node, Function):
        name = node.name
        params = []
        for param in node.params:
            params.append(param.name[1:])
            # if param.default is not None:
            #     params.append('%s=%s' % (param.name[1:],
            #                              unparse_node(param.default, True)))
            # else:
            #     params.append(param.name[1:])
        params = ', '.join(params)
        body = '\n    '.join(unparse_node(node) for node in node.nodes)
        return '{%% macro %s(%s) -%%}\n    %s\n{%%- endmacro -%%}\n\n' % (name, params, body)

    if isinstance(node, Return):
        return '{{ %s }}' % unparse_node(node.node, True)

    if isinstance(node, FunctionCall):
        if node.name.endswith('printf'):
            params = [unparse_node(x.node, True) for x in node.params[1:]]
            if is_expr:
                return '%s %% (%s,)' % (unparse_node(node.params[0].node, True),
                                        ', '.join(params))
            else:
                return '{{ %s %% (%s,) }}' % (unparse_node(node.params[0].node, True),
                                              ', '.join(params))
        params = ', '.join(unparse_node(param.node, True)
                           for param in node.params)
        if is_expr:
            return '%s(%s)' % (node.name, params)
        else:
            return '{{ %s(%s) }}' % (node.name, params)

    if isinstance(node, MethodCall):
        params = ', '.join(unparse_node(param.node, True)
                           for param in node.params)
        if is_expr:
            return '%s.%s(%s)' % (unparse_node(node.node, True),
                                  node.name, params)
        else:
            return '{{ %s.%s(%s) }}' % (unparse_node(node.node, True),
                                        node.name, params)

    if is_expr:
        return 'XXX(%r)' % str(node)
    else:
        return '{# XXX %s #}' % node

output.write(unparse(parser.parse(input.read(), lexer=lexer)))

########NEW FILE########
__FILENAME__ = php2json
#!/usr/bin/env python

# php2json.py - Converts PHP to a JSON-based abstract syntax tree
# Usage: php2json.py < input.php > output.json

import sys
sys.path.append('..')

from phply.phplex import lexer
from phply.phpparse import parser

import simplejson

input = sys.stdin
output = sys.stdout
with_lineno = True

def export(items):
    result = []
    if items:
       for item in items:
           if hasattr(item, 'generic'):
               item = item.generic(with_lineno=with_lineno)
           result.append(item)
    return result

simplejson.dump(export(parser.parse(input.read(),
                                    lexer=lexer,
                                    tracking=with_lineno)),
                output, indent=2)
output.write('\n')

########NEW FILE########
__FILENAME__ = php2python
#!/usr/bin/env python

# php2python.py - Converts PHP to Python using unparse.py
# Usage: php2python.py < input.php > output.py

import sys
sys.path.append('..')

from phply.phplex import lexer
from phply.phpparse import parser
from phply import pythonast

from ast import Module
from unparse import Unparser

input = sys.stdin
output = sys.stdout

body = [pythonast.from_phpast(ast)
        for ast in parser.parse(input.read(), lexer=lexer)]
Unparser(body, output)

########NEW FILE########
__FILENAME__ = phpshell
#!/usr/bin/env python

# phpshell.py - PHP interactive interpreter

import sys
sys.path.append('..')

import ast
import pprint
import readline
import traceback

from phply import pythonast, phplex
from phply.phpparse import parser

def echo(*objs):
    for obj in objs:
        sys.stdout.write(str(obj))

def inline_html(obj):
    sys.stdout.write(obj)

def XXX(obj):
    print 'Not implemented:\n ', obj

def ast_dump(code):
    print 'AST dump:'
    print ' ', ast.dump(code, include_attributes=True)

def php_eval(nodes):
    body = []
    for node in nodes:
        stmt = pythonast.to_stmt(pythonast.from_phpast(node))
        body.append(stmt)
    code = ast.Module(body)
    # ast_dump(code)
    eval(compile(code, '<string>', mode='exec'), globals())

s = ''
lexer = phplex.lexer
parser.parse('<?', lexer=lexer)

while True:
   if s:
       prompt = '     '
   else:
       prompt = lexer.current_state()
       if prompt == 'INITIAL': prompt = 'html'
       prompt += '> '

   try:
       s += raw_input(prompt)
   except EOFError:
       break

   if not s: continue
   s += '\n'

   # Catch all exceptions and print tracebacks.
   try:
       # Try parsing the input normally.
       try:
           lexer.lineno = 1
           result = parser.parse(s, lexer=lexer)
           php_eval(result)
       except SyntaxError, e:
           # Parsing failed. See if it can be parsed as an expression.
           try:
               lexer.lineno = 1
               result = parser.parse('print ' + s + ';', lexer=lexer)
               php_eval(result)
           except (SyntaxError, TypeError):
               # That also failed. Try adding a semicolon.
               try:
                   lexer.lineno = 1
                   result = parser.parse(s + ';', lexer=lexer)
                   php_eval(result)
               except SyntaxError:
                   # Did we get an EOF? If so, we're still waiting for input.
                   # If not, it's a syntax error for sure.
                   if e.lineno is None:
                       continue
                   else:
                       print e, 'near', repr(e.text)
                       s = ''
   except:
       traceback.print_exc()

   s = ''

########NEW FILE########
__FILENAME__ = unparse
"Usage: unparse.py <path to source file>"
import sys
import _ast
import cStringIO
import os

def interleave(inter, f, seq):
    """Call f on each item in seq, calling inter() in between.
    """
    seq = iter(seq)
    try:
        f(seq.next())
    except StopIteration:
        pass
    else:
        for x in seq:
            inter()
            f(x)

class Unparser:
    """Methods in this class recursively traverse an AST and
    output source code for the abstract syntax; original formatting
    is disregarged. """

    def __init__(self, tree, file = sys.stdout):
        """Unparser(tree, file=sys.stdout) -> None.
         Print the source for tree to file."""
        self.f = file
        self._indent = 0
        self.dispatch(tree)
        print >>self.f,""
        self.f.flush()

    def fill(self, text = ""):
        "Indent a piece of text, according to the current indentation level"
        self.f.write("\n"+"    "*self._indent + text)

    def write(self, text):
        "Append a piece of text to the current line."
        self.f.write(text)

    def enter(self):
        "Print ':', and increase the indentation."
        self.write(":")
        self._indent += 1

    def leave(self):
        "Decrease the indentation level."
        self._indent -= 1

    def dispatch(self, tree):
        "Dispatcher function, dispatching tree type T to method _T."
        if isinstance(tree, list):
            for t in tree:
                self.dispatch(t)
            return
        meth = getattr(self, "_"+tree.__class__.__name__)
        meth(tree)


    ############### Unparsing methods ######################
    # There should be one method per concrete grammar type #
    # Constructors should be grouped by sum type. Ideally, #
    # this would follow the order in the grammar, but      #
    # currently doesn't.                                   #
    ########################################################

    def _Module(self, tree):
        for stmt in tree.body:
            self.dispatch(stmt)

    # stmt
    def _Expr(self, tree):
        self.fill()
        self.dispatch(tree.value)

    def _Import(self, t):
        self.fill("import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _ImportFrom(self, t):
        self.fill("from ")
        self.write(t.module)
        self.write(" import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)
        # XXX(jpe) what is level for?

    def _Assign(self, t):
        self.fill()
        for target in t.targets:
            self.dispatch(target)
            self.write(" = ")
        self.dispatch(t.value)

    def _AugAssign(self, t):
        self.fill()
        self.dispatch(t.target)
        self.write(" "+self.binop[t.op.__class__.__name__]+"= ")
        self.dispatch(t.value)

    def _Return(self, t):
        self.fill("return")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)

    def _Pass(self, t):
        self.fill("pass")

    def _Break(self, t):
        self.fill("break")

    def _Continue(self, t):
        self.fill("continue")

    def _Delete(self, t):
        self.fill("del ")
        self.dispatch(t.targets)

    def _Assert(self, t):
        self.fill("assert ")
        self.dispatch(t.test)
        if t.msg:
            self.write(", ")
            self.dispatch(t.msg)

    def _Exec(self, t):
        self.fill("exec ")
        self.dispatch(t.body)
        if t.globals:
            self.write(" in ")
            self.dispatch(t.globals)
        if t.locals:
            self.write(", ")
            self.dispatch(t.locals)

    def _Print(self, t):
        self.fill("print ")
        do_comma = False
        if t.dest:
            self.write(">>")
            self.dispatch(t.dest)
            do_comma = True
        for e in t.values:
            if do_comma:self.write(", ")
            else:do_comma=True
            self.dispatch(e)
        if not t.nl:
            self.write(",")

    def _Global(self, t):
        self.fill("global ")
        interleave(lambda: self.write(", "), self.write, t.names)

    def _Yield(self, t):
        self.write("(")
        self.write("yield")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)
        self.write(")")

    def _Raise(self, t):
        self.fill('raise ')
        if t.type:
            self.dispatch(t.type)
        if t.inst:
            self.write(", ")
            self.dispatch(t.inst)
        if t.tback:
            self.write(", ")
            self.dispatch(t.tback)

    def _TryExcept(self, t):
        self.fill("try")
        self.enter()
        self.dispatch(t.body)
        self.leave()

        for ex in t.handlers:
            self.dispatch(ex)
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _TryFinally(self, t):
        self.fill("try")
        self.enter()
        self.dispatch(t.body)
        self.leave()

        self.fill("finally")
        self.enter()
        self.dispatch(t.finalbody)
        self.leave()

    def _ExceptHandler(self, t):
        self.fill("except")
        if t.type:
            self.write(" ")
            self.dispatch(t.type)
        if t.name:
            self.write(", ")
            self.dispatch(t.name)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _ClassDef(self, t):
        self.write("\n")
        self.fill("class "+t.name)
        if t.bases:
            self.write("(")
            for a in t.bases:
                self.dispatch(a)
                self.write(", ")
            self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _FunctionDef(self, t):
        self.write("\n")
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("def "+t.name + "(")
        self.dispatch(t.args)
        self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _For(self, t):
        self.fill("for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave

    def _If(self, t):
        self.fill("if ")
        self.dispatch(t.test)
        self.enter()
        # XXX elif?
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _While(self, t):
        self.fill("while ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave

    def _With(self, t):
        self.fill("with ")
        self.dispatch(t.context_expr)
        if t.optional_vars:
            self.write(" as ")
            self.dispatch(t.optional_vars)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    # expr
    def _Str(self, tree):
        self.write(repr(tree.s))

    def _Name(self, t):
        self.write(t.id)

    def _Repr(self, t):
        self.write("`")
        self.dispatch(t.value)
        self.write("`")

    def _Num(self, t):
        self.write(repr(t.n))

    def _List(self, t):
        self.write("[")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("]")

    def _ListComp(self, t):
        self.write("[")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("]")

    def _GeneratorExp(self, t):
        self.write("(")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write(")")

    def _comprehension(self, t):
        self.write(" for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        for if_clause in t.ifs:
            self.write(" if ")
            self.dispatch(if_clause)

    def _IfExp(self, t):
        self.write("(")
        self.dispatch(t.body)
        self.write(" if ")
        self.dispatch(t.test)
        self.write(" else ")
        self.dispatch(t.orelse)
        self.write(")")

    def _Dict(self, t):
        self.write("{")
        def writem((k, v)):
            self.dispatch(k)
            self.write(": ")
            self.dispatch(v)
        interleave(lambda: self.write(", "), writem, zip(t.keys, t.values))
        self.write("}")

    def _Tuple(self, t):
        self.write("(")
        if len(t.elts) == 1:
            (elt,) = t.elts
            self.dispatch(elt)
            self.write(",")
        else:
            interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write(")")

    unop = {"Invert":"~", "Not": "not", "UAdd":"+", "USub":"-"}
    def _UnaryOp(self, t):
        self.write(self.unop[t.op.__class__.__name__])
        self.write("(")
        self.dispatch(t.operand)
        self.write(")")

    binop = { "Add":"+", "Sub":"-", "Mult":"*", "Div":"/", "Mod":"%",
                    "LShift":">>", "RShift":"<<", "BitOr":"|", "BitXor":"^", "BitAnd":"&",
                    "FloorDiv":"//", "Pow": "**"}
    def _BinOp(self, t):
        self.write("(")
        self.dispatch(t.left)
        self.write(" " + self.binop[t.op.__class__.__name__] + " ")
        self.dispatch(t.right)
        self.write(")")

    cmpops = {"Eq":"==", "NotEq":"!=", "Lt":"<", "LtE":"<=", "Gt":">", "GtE":">=",
                        "Is":"is", "IsNot":"is not", "In":"in", "NotIn":"not in"}
    def _Compare(self, t):
        self.write("(")
        self.dispatch(t.left)
        for o, e in zip(t.ops, t.comparators):
            self.write(" " + self.cmpops[o.__class__.__name__] + " ")
            self.dispatch(e)
            self.write(")")

    boolops = {_ast.And: 'and', _ast.Or: 'or'}
    def _BoolOp(self, t):
        self.write("(")
        s = " %s " % self.boolops[t.op.__class__]
        interleave(lambda: self.write(s), self.dispatch, t.values)
        self.write(")")

    def _Attribute(self,t):
        self.dispatch(t.value)
        self.write(".")
        self.write(t.attr)

    def _Call(self, t):
        self.dispatch(t.func)
        self.write("(")
        comma = False
        for e in t.args:
            if comma: self.write(", ")
            else: comma = True
            self.dispatch(e)
        for e in t.keywords:
            if comma: self.write(", ")
            else: comma = True
            self.dispatch(e)
        if t.starargs:
            if comma: self.write(", ")
            else: comma = True
            self.write("*")
            self.dispatch(t.starargs)
        if t.kwargs:
            if comma: self.write(", ")
            else: comma = True
            self.write("**")
            self.dispatch(t.kwargs)
        self.write(")")

    def _Subscript(self, t):
        self.dispatch(t.value)
        self.write("[")
        self.dispatch(t.slice)
        self.write("]")

    # slice
    def _Ellipsis(self, t):
        self.write("...")

    def _Index(self, t):
        self.dispatch(t.value)

    def _Slice(self, t):
        if t.lower:
            self.dispatch(t.lower)
        self.write(":")
        if t.upper:
            self.dispatch(t.upper)
        if t.step:
            self.write(":")
            self.dispatch(t.step)

    def _ExtSlice(self, t):
        interleave(lambda: self.write(', '), self.dispatch, t.dims)

    # others
    def _arguments(self, t):
        first = True
        nonDef = len(t.args)-len(t.defaults)
        for a in t.args[0:nonDef]:
            if first:first = False
            else: self.write(", ")
            self.dispatch(a)
        for a,d in zip(t.args[nonDef:], t.defaults):
            if first:first = False
            else: self.write(", ")
            self.dispatch(a),
            self.write("=")
            self.dispatch(d)
        if t.vararg:
            if first:first = False
            else: self.write(", ")
            self.write("*"+t.vararg)
        if t.kwarg:
            if first:first = False
            else: self.write(", ")
            self.write("**"+t.kwarg)

    def _keyword(self, t):
        self.write(t.arg)
        self.write("=")
        self.dispatch(t.value)

    def _Lambda(self, t):
        self.write("lambda ")
        self.dispatch(t.args)
        self.write(": ")
        self.dispatch(t.body)

    def _alias(self, t):
        self.write(t.name)
        if t.asname:
            self.write(" as "+t.asname)

def roundtrip(filename, output=sys.stdout):
    source = open(filename).read()
    tree = compile(source, filename, "exec", _ast.PyCF_ONLY_AST)
    Unparser(tree, output)



def testdir(a):
    try:
        names = [n for n in os.listdir(a) if n.endswith('.py')]
    except OSError:
        print >> sys.stderr, "Directory not readable: %s" % a
    else:
        for n in names:
            fullname = os.path.join(a, n)
            if os.path.isfile(fullname):
                output = cStringIO.StringIO()
                print 'Testing %s' % fullname
                try:
                    roundtrip(fullname, output)
                except Exception, e:
                    print '  Failed to compile, exception is %s' % repr(e)
            elif os.path.isdir(fullname):
                testdir(fullname)

def main(args):
    if args[0] == '--testdir':
        for a in args[1:]:
            testdir(a)
    else:
        for a in args:
            roundtrip(a)

if __name__=='__main__':
    main(sys.argv[1:])

########NEW FILE########
