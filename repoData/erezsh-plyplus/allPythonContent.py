__FILENAME__ = calc
# calc.py - # A simple calculator without using eval
# A shorter and simpler re-implementation of http://www.dabeaz.com/ply/example.html

import operator as op
from plyplus import Grammar, STransformer

calc_grammar = Grammar("""
    start: add;

    ?add: (add add_symbol)? mul;
    ?mul: (mul mul_symbol)? atom;
    @atom: neg | number | '\(' add '\)';
    neg: '-' atom;

    number: '[\d.]+';
    mul_symbol: '\*' | '/';
    add_symbol: '\+' | '-';

    WS: '[ \t]+' (%ignore);
""")

class Calc(STransformer):

    def _bin_operator(self, exp):
        arg1, operator_symbol, arg2 = exp.tail

        operator_func = { '+': op.add, '-': op.sub, '*': op.mul, '/': op.div }[operator_symbol]

        return operator_func(arg1, arg2)

    number      = lambda self, exp: float(exp.tail[0])
    neg         = lambda self, exp: -exp.tail[0]
    __default__ = lambda self, exp: exp.tail[0]

    add = _bin_operator
    mul = _bin_operator

def main():
    calc = Calc()
    while True:
        try:
            s = raw_input('> ')
        except EOFError:
            break
        if s == '':
            break
        tree = calc_grammar.parse(s)
        print(calc.transform(tree))

main()

########NEW FILE########
__FILENAME__ = json
from plyplus import Grammar, STransformer

json_grammar = Grammar(r"""
@start: value ;

?value : object | array | string | number | boolean | null ;

string : '".*?(?<!\\)(\\\\)*?"' ;
number : '-?([1-9]\d*|\d)(\.\d+)?([eE][+-]?\d+)?' ;
pair : string ':' value ;
object : '\{' ( pair ( ',' pair )* )? '\}' ;
array : '\[' ( value ( ',' value ) * )? '\]' ;
boolean : 'true' | 'false' ;
null : 'null' ;

WS: '[ \t\n]+' (%ignore) (%newline);
""")

class JSON_Transformer(STransformer):
    """Transforms JSON AST into Python native objects."""
    number  = lambda self, node: float(node.tail[0])
    string  = lambda self, node: node.tail[0][1:-1]
    boolean = lambda self, node: True if node.tail[0] == 'true' else False
    null    = lambda self, node: None
    array   = lambda self, node: node.tail
    pair    = lambda self, node: { node.tail[0] : node.tail[1] }
    def object(self, node):
        result = {}
        for i in node.tail:
            result.update( i )
        return result

def json_parse(json_string):
    """Parses a JSON string into native Python objects."""
    return JSON_Transformer().transform(json_grammar.parse(json_string))

def main():
    json = '''
        {
            "empty_object" : {},
            "empty_array"  : [],
            "booleans"     : { "YES" : true, "NO" : false },
            "numbers"      : [ 0, 1, -2, 3.3, 4.4e5, 6.6e-7 ],
            "strings"      : [ "This", [ "And" , "That" ] ],
            "nothing"      : null
        }
    '''
    print '### JSON Parser using PlyPlus'
    print '  # JSON allows empty arrays and objects.'
    print '  # This requires that empty AST sub-trees be kept in the AST tree.'
    print '  # If you pass the kwarg "keep_empty_trees=False" to the'
    print '  # Grammar() constructor, empty arrays and objects will be removed'
    print '  # and the JSON_Transformer class will fail.'
    print
    print '### Input'
    print json
    print '### Output'
    result = json_parse(json)
    import pprint
    pprint.pprint(result)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = permutations
"""Demonstrates the use of the permutation operator."""
from plyplus import Grammar

# Basic Permutations
perm1 = Grammar("""
start : a ^ b? ^ c ;

a : 'a' ;
b : 'b' ;
c : 'c' ;

WS: '[ \t]+' (%ignore);
""")

print perm1.parse(' c b a').pretty()
print perm1.parse('c a ').pretty()

# Permutations with a separator
perm2 = Grammar("""
start : a ^ (b|d)? ^ c ^^ ( COMMA | SEMI ) ;

a : 'a' ;
b : 'b' ;
c : 'c' ;
d : 'd' ;

COMMA : ',' ;
SEMI  : ';' ;

WS: '[ \t]+' (%ignore);
""")

print perm2.parse(' c ; a,b').pretty()
print perm2.parse('c;d, a ').pretty()
print perm2.parse('c , a ').pretty()

########NEW FILE########
__FILENAME__ = python_indent_postlex
from copy import copy

NL_type = 'NEWLINE'
INDENT_type = 'INDENT'
DEDENT_type = 'DEDENT'
PAREN_OPENERS = 'LPAR', 'LBRACE', 'LSQB'
PAREN_CLOSERS = 'RPAR', 'RBRACE', 'RSQB'


class Tok():
    def __init__(self, type=None, value=None, lexer=None):
        self.type = type
        self.value = value
        self.lineno = None
        self.lexpos = None
        self.lexer = lexer

class PythonIndentTracker:
    def __init__(self, lexer, tab_len=4):
        self.lexer = lexer

        self.tab_len = tab_len
        self.tab_str = ' '*tab_len
        self.current_state = lexer.current_state
        self.begin = lexer.begin

    def input(self, s):
        self.token_queue = []
        self.indent_level = [0]
        self.ignore_newline = False
        self.paren_level = 0
        return self.lexer.input(s)

    def token(self):
        # If tokens are waiting to be pushed, push them --
        if len(self.token_queue):
            return self.token_queue.pop()

        # Get original token
        tok = self.lexer.token()
        #print type(tok)

        if tok and tok.type == NL_type:
            # -- New line --
            ignore_nl = self.ignore_newline # save now, may change on self.token()
            while tok and tok.type == NL_type:  # treat successive NLs as one (the last of them)
                nl_tok = tok
                tok = self.token()

            if ignore_nl:  # ignore = don't indent, and skip new line too
                return tok

            self.token_queue.append(tok)
            return self.handle_newline(nl_tok)

        # -- End of input --
        if tok is None:
            #print self.indent_level
            if len(self.indent_level) > 1:
                while len(self.indent_level) > 1:
                    self.indent_level.pop()

                    new_token = Tok(lexer=self.lexer)
                    new_token.type = DEDENT_type
                    self.token_queue.append(new_token)
                return self.token() # assume it always returns None

            assert self.indent_level == [0], self.indent_level

            self.token_queue.append( None )
            #eof = Tok(lexer=self.lexer)
            #eof.type = 'EOF'
            #eof.value = '<EOF>'
            #return eof
            return None

        # -- Regular token --
        if tok.type != NL_type:
            #self.ignore_indent = (tok.type != 'COLON')
            if tok.type in PAREN_OPENERS:
                self.paren_level += 1
            elif tok.type in PAREN_CLOSERS:
                self.paren_level -= 1

            assert self.paren_level >= 0
            self.ignore_newline = (self.paren_level > 0)

            return tok

        assert False

    def handle_newline(self, tok):  # Do (most) indentation
        text = tok.value
        indent_str = text.rsplit('\n', 1)[1] # Tabs and spaces
        text = text[:text.rfind('\n') + 1]    # Without the indent

        #print tok.start, tok.stop, `tok.text`
        #indent = len(indent_str.replace('\t', self.tab_str))
        indent = indent_str.count(' ') + indent_str.count('\t') * self.tab_len

        # -- Indent --
        if indent > self.indent_level[-1]:
            #print "INDENT", indent
            self.indent_level.append(indent)

            new_token = copy(tok)
            new_token.type = INDENT_type
            new_token.value = indent_str
            self.token_queue.append(new_token)
        else:
            while indent < self.indent_level[-1]:
                #print "DEDENT", indent
                self.indent_level.pop()

                new_token = copy(tok)
                new_token.type = DEDENT_type
                new_token.value = indent_str
                self.token_queue.append(new_token)

            assert indent == self.indent_level[-1], '%s != %s' % (indent, self.indent_level[-1])


        return tok



def test():
    class Tok:
        def __init__(self, type, value=''):
            self.type = type
            self.value = value
    class A:
        def __init__(self):
            self.l = [
                    Tok('STMT'), Tok('NL', '\n'
                    ), Tok('STMT'), Tok('NL', '\n'
                    '\t'), Tok('STMT'), Tok('NL', '\n'
                    '\t'), Tok('LBRACK'), Tok('NL', '\n'
                    '\t\t'), Tok('STMT'), Tok('NL', '\n'
                    '\t\t\t'), Tok('RBRACK'), Tok('NL', '\n'
                    ), Tok('STMT'), Tok('NL', '\n'
                    '\t\t'), Tok('STMT'), Tok('NL', '\n'
                    '\t\t'), Tok('STMT'), Tok('NL', '\n'
                    '\t\t\t'),
                ][::-1]
        def input(self, t):
            return
        def token(self):
            if self.l:
                return self.l.pop()

    expected_result = [
            'STMT', 'NL',
            'STMT', 'NL',
            'INDENT', 'STMT', 'NL',
            'LBRACK', 'STMT', 'RBRACK', 'NL',
            'DEDENT', 'STMT', 'NL',
            'INDENT', 'STMT', 'NL',
            'STMT', 'NL',
            'INDENT', 'DEDENT', 'DEDENT'
            ]
    a = PythonIndentTracker(A())
    toks = []
    tok = a.token()
    while tok:
        print(tok.type)
        toks.append(tok.type)
        tok = a.token()

    print(['FAILED!', 'OK!'][toks == expected_result])



if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = grammar_lexer
from ply import lex

LEX_TAB_MODULE = "plyplus_grammar_lextab"

tokens = (
        'RULENAME',
        'TOKEN',
        'OPTION',
        'OPER',
        'PERM',
        'PERMSEP',
        'OR',
        'LPAR',
        'RPAR',
        'COLON',
        'SEMICOLON',
        'REGEXP',
        'SECTION',
        'LCURLY',
        'RCURLY',
#        'COMMENT',
    )

t_RULENAME = '[@#?]?[a-z_][a-z_0-9]*'
t_TOKEN = '[A-Z_][A-Z_0-9]*'
t_OPTION = '%[a-z_]+'

t_OPER = '[?*+]'
t_PERM = '\^'
t_PERMSEP = '\^\^'
t_OR = '\|'
t_LPAR = '\('
t_RPAR = '\)'
t_COLON = ':'
t_SEMICOLON = ';'
t_REGEXP = r"'(.|\n)*?[^\\]'"
t_LCURLY = '{'
t_RCURLY = '}'

def t_SECTION(t):
    r'\#\#\#(.|\n)*'
    # line number information used to ensure tracebacks refer to the correct line
    t.lineno = t.lexer.lineno
    return t

def t_COMMENT(t):
    r'//[^\n]*\n|/[*](.|\n)*?[*]/'
    t.lexer.lineno += t.value.count('\n')

def t_NL(t):
    r'\n'
    t.lexer.lineno += 1
    return 0

t_ignore = " \t\r"
def t_error(t):
    raise Exception("Illegal character in grammar: %r in %r" % (t.value[0], t.value[:10] ))

lexer = lex.lex(lextab=LEX_TAB_MODULE)

########NEW FILE########
__FILENAME__ = grammar_parser
from __future__ import absolute_import

from ply import yacc

from .strees import STree as S

from .grammar_lexer import tokens, lexer
from . import PLYPLUS_DIR

DEBUG = False
YACC_TAB_MODULE = "plyplus_grammar_parsetab"


def p_extgrammar(p):
    """extgrammar : grammar
    """
    p[0] = S('extgrammar', p.__getslice__(1, None))

def p_extgrammar_with_code(p):
    """extgrammar : grammar SECTION
    """
    p[0] = S('extgrammar', p.__getslice__(1, None))
    # preserve line-number information in AST, used for tracebacks
    p[0].tail[-1].line = p.slice[2].lineno

def p_grammar(p):
    """grammar  : def
                | def grammar
    """
    p[0] = S('grammar', p.__getslice__(1, None))

def p_def(p):
    """def  : ruledef
            | tokendef
            | optiondef
    """
    p[0] = p[1]


def p_tokendef(p):
    """tokendef : TOKEN COLON tokenvalue SEMICOLON
                | TOKEN COLON tokenvalue tokenmods SEMICOLON
                | TOKEN COLON tokenvalue subgrammar SEMICOLON
    """
    if len(p) > 5:
        p[0] = S('tokendef', (p[1], p[3], p[4]))
    else:
        p[0] = S('tokendef', (p[1], p[3]))

def p_tokenvalue(p):
    """tokenvalue : REGEXP
                  | TOKEN
                  | REGEXP tokenvalue
                  | TOKEN tokenvalue
    """
    p[0] = S('tokenvalue', p.__getslice__(1, None))

def p_tokenmods(p):
    """tokenmods : tokenmod
                 | tokenmod tokenmods
    """
    p[0] = S('tokenmods', p.__getslice__(1, None))

def p_tokenmod(p):
    """tokenmod : LPAR OPTION modtokenlist RPAR"""
    p[0] = S('tokenmod', (p[2], p[3]))

def p_modtokenlist(p):
    """modtokenlist : tokendef modtokenlist
                    |
    """
    p[0] = S('modtokenlist', p.__getslice__(1, None))

def p_subgrammar(p):
    """subgrammar : LCURLY extgrammar RCURLY"""
    p[0] = S('subgrammar', [p[2]])

def p_ruledef(p):
    """ruledef : RULENAME COLON rules_list SEMICOLON"""
    p[0] = S('ruledef', [p[1], p[3]])

def p_optiondef(p):
    """optiondef : OPTION COLON REGEXP SEMICOLON
                 | OPTION COLON TOKEN SEMICOLON
                 | OPTION COLON RULENAME SEMICOLON
                 | OPTION TOKEN COLON tokenvalue SEMICOLON
    """
    if len(p) == 6:
        assert p[1] == '%fragment'
        p[0] = S('fragmentdef', (p[2], p[4]))
    else:
        p[0] = S('optiondef', (p[1], p[3]))

def p_rules_list(p):
    """rules_list   : production
                    | production OR rules_list"""
    p[0] = S('rules_list', [p[1]] + p.__getslice__(3, None))

def p_production(p):
    """production : perm_rule
                  | rule
    """
    p[0] = p[1]

def p_perm_rule(p):
    """perm_rule : perm_phrase
                 | perm_phrase PERMSEP rule"""
    if len(p) == 2:
        p[0] = S('perm_rule', (p[1],))
    else:
        p[0] = S('perm_rule', (p[1], p[3]))

def p_perm_phrase(p):
    """perm_phrase : rule PERM rule
                   | rule PERM perm_phrase
    """
    p[0] = S('perm_phrase', [p[1]] + p.__getslice__(3, None))

def p_rule(p):
    """rule : expr
            | expr rule
            |
    """
    p[0] = S('rule', p.__getslice__(1, None))

def p_expr(p):
    """expr : RULENAME
            | TOKEN
            | REGEXP
            | oper
            | LPAR rules_list RPAR
    """
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[1]

def p_oper(p):
    "oper : expr OPER"
    p[0] = S('oper', (p[1], p[2]))



def p_error(p):
    if p:
        print("PLYPLUS: Syntax error in grammar at '%s'" % p.value, 'line', p.lineno, 'type', p.type)
    else:
        print("PLYPLUS: Unknown syntax error in grammar")

start = "extgrammar"


_parser = yacc.yacc(debug=DEBUG, tabmodule=YACC_TAB_MODULE, errorlog=Exception, outputdir=PLYPLUS_DIR)     # Return parser object
def parse(text, debug=False):
    lexer.lineno = 1
    return _parser.parse(text, lexer=lexer, debug=debug)

########NEW FILE########
__FILENAME__ = plyplus
"Author: Erez Shinan, erezshin at gmail.com"

from __future__ import absolute_import

import re, os
import types
import itertools
import logging
import ast
import hashlib
import codecs
try:
    import cPickle as pickle
except ImportError:
    import pickle

from ply import lex, yacc

from . import __version__, PLYPLUS_DIR, grammar_parser
from .utils import StringTypes, StringType

from .strees import STree, SVisitor, STransformer, is_stree, SVisitor_Recurse, Str

# -- Must!
#TODO: Support States
#TODO: @ on start symbols should expand them (right now not possible because of technical design issues)
#      alternatively (but not as good?): add option to expand all 'start' symbols

# -- Nice to have
#TODO: Operator precedence
#TODO: find better terms than expand and flatten
#TODO: Exact recovery of input (as text attr)
#      Allow to reconstruct the input with whatever changes were made to the tree
#TODO: Allow 'optimize' mode
#TODO: Rule Self-recursion (an operator? a 'self' keyword?)
#TODO: Add token history on parse error
#TODO: Add rule history on parse error?

# -- Unknown status
#TODO: Allow empty rules
#TODO: Multiply defined tokens (just concatinate with |?)
#TODO: Complete EOF handling in python grammar (postlex)
#TODO: Make filter behaviour consitent for both ()? and ()* / ()+
#TODO: better filters
#TODO: Offer mechanisms to easily avoid ambiguity (expr: expr '\+' expr etc.)
#TODO: Use PLY's ignore mechanism (=tokens return None) instead of post-filtering it myself?
#TODO: Support Compiling grammars into a single parser python file
#TODO: Support running multi-threaded
#TODO: Better debug mode (set debug level, choose between prints and interactive debugging?)

# -- Continual Tasks
#TODO: Optimize for space
#TODO: Optimize for speed
#TODO: require less knowledge of ply
#TODO: meaningful names to anonymous tokens

# -- Done
#DONE: anonymous tokens
#DONE: Resolve errors caused by dups of tokens
#DONE: Allow comments in grammar
#DONE: (a+)? is different from a*
#       print_stmt : PRINT (RIGHTSHIFT? test (COMMA test)* COMMA?)?  ;
#           --> only works as -->
#       print_stmt : PRINT (RIGHTSHIFT? test ((COMMA test)+)? COMMA?)?  ;
#
#      Similarly:
#      dictmaker : test COLON test (COMMA test COLON test)* COMMA? ;
#           --> only works as -->
#      dictmaker : test COLON test (COMMA test COLON test)+? COMMA? ;
#DONE: rename simps
#DONE: Recursive parsing
#DONE: Change rule+ into "rule simp*" instead of "simp+"
#DONE: Multi-line comments
#DONE: Better error handling (choose between prints and raising exception, setting threshold, etc.)
#

grammar_logger = logging.getLogger('Grammar')
grammar_logger.setLevel(logging.ERROR)


_TOKEN_NAMES = {
    ':' : 'COLON',
    ',' : 'COMMA',
    ';' : 'SEMICOLON',
    '+' : 'PLUS',
    '-' : 'MINUS',
    '*' : 'STAR',
    '/' : 'SLASH',
    '|' : 'VBAR',
    '!' : 'BANG',
    '?' : 'QMARK',
    '#' : 'HASH',
    '$' : 'DOLLAR',
    '&' : 'AMPERSAND',
    '<' : 'LESSTHAN',
    '>' : 'MORETHAN',
    '=' : 'EQUAL',
    '.' : 'DOT',
    '%' : 'PERCENT',
    '`' : 'BACKQUOTE',
    '^' : 'CIRCUMFLEX',
    '"' : 'DBLQUOTE',
    '\'' : 'QUOTE',
    '~' : 'TILDE',
    '@' : 'AT',
    '(' : 'LPAR',
    ')' : 'RPAR',
    '{' : 'LBRACE',
    '}' : 'RBRACE',
    '[' : 'LSQB',
    ']' : 'RSQB',
}

def get_token_name(token, default):
    return _TOKEN_NAMES.get( token, default)

class PlyplusException(Exception): pass

class GrammarException(PlyplusException): pass

class TokenizeError(PlyplusException): pass

class ParseError(PlyplusException): pass

class RuleMods(object):
    EXPAND = '@'    # Expand all instances of rule
    FLATTEN = '#'   # Expand all nested instances of rule
    EXPAND1 = '?'   # Expand all instances of rule with only one child


class ExtractSubgrammars_Visitor(SVisitor):
    def __init__(self, parent_source_name, parent_tab_filename, parent_options):
        self.parent_source_name = parent_source_name
        self.parent_tab_filename = parent_tab_filename
        self.parent_options = parent_options

        self.last_tok = None

    def tokendef(self, tok):
        self.last_tok = tok.tail[0]
    def subgrammar(self, tree):
        assert self.last_tok
        assert len(tree.tail) == 1
        source_name = '%s:%s' % (self.parent_source_name, self.last_tok.lower())
        tab_filename = '%s_%s' % (self.parent_tab_filename, self.last_tok.lower())
        subgrammar = _Grammar(tree.tail[0], source_name, tab_filename, **self.parent_options)
        tree.head, tree.tail = 'subgrammarobj', [subgrammar]

class ApplySubgrammars_Visitor(SVisitor):
    def __init__(self, subgrammars):
        self.subgrammars = subgrammars
    def __default__(self, tree):
        for i, tok in enumerate(tree.tail):
            if type(tok) == TokValue and tok.type in self.subgrammars:
                parsed_tok = self.subgrammars[tok.type].parse(tok)
                assert parsed_tok.head == 'start'
                tree.tail[i] = parsed_tok


class CollectTokenDefs_Visitor(SVisitor):
    def __init__(self, dict_to_populate):
        self.tokendefs = dict_to_populate

    def tokendef(self, tree):
        self.tokendefs[ tree.tail[0] ] = tree

    def fragmentdef(self, tree):
        self.tokendefs[ tree.tail[0] ] = tree

def _unescape_token_def(token_def):
    assert token_def[0] == "'" == token_def[-1]
    return token_def[1:-1].replace(r"\'", "'")

class SimplifyTokenDefs_Visitor(SVisitor):

    def __init__(self):
        self.tokendefs = {}

    def visit(self, tree):
        CollectTokenDefs_Visitor(self.tokendefs).visit(tree)
        SVisitor.visit(self, tree)

        for tokendef in self.tokendefs.values():
            self._simplify_token(tokendef)

        return self.tokendefs

    def _simplify_token(self, tokendef):
        token_value = tokendef.tail[1]
        if is_stree(token_value):
            assert token_value.head == 'tokenvalue'

            regexp = ''.join( _unescape_token_def(d)
                                if d.startswith("'")
                                else self._simplify_token(self.tokendefs[d])
                                for d in token_value.tail )
            tokendef.tail = list(tokendef.tail) # can't assign to a tuple
            tokendef.tail[1] = regexp

        return tokendef.tail[1]

class NameAnonymousTokens_Visitor(SVisitor):
    ANON_TOKEN_ID = 'ANON'

    def __init__(self, tokendefs):
        self._count = itertools.count()
        self._rules_to_add = []

        self.token_name_from_value = {}
        for name, tokendef in tokendefs.items():
            self.token_name_from_value[tokendef.tail[1]] = name

    def _get_new_tok_name(self, tok):
        return '_%s_%d' % (get_token_name(tok[1:-1], self.ANON_TOKEN_ID), next(self._count))

    def rule(self, tree):
        for i, child in enumerate(tree.tail):
            if isinstance(child, StringTypes) and child.startswith("'"):
                child = _unescape_token_def(child)
                try:
                    tok_name = self.token_name_from_value[child]
                except KeyError:
                    tok_name = self._get_new_tok_name(child) # Add anonymous token
                    self.token_name_from_value[child] = tok_name    # for future anonymous occurences
                    self._rules_to_add.append(STree('tokendef', [tok_name, child]))
                tree.tail[i] = tok_name

    def grammar(self, tree):
        if self._rules_to_add:
            tree.tail += self._rules_to_add


class SimplifyGrammar_Visitor(SVisitor_Recurse):
    ANON_RULE_ID = 'anon'

    def __init__(self):
        self._count = itertools.count()
        self._rules_to_add = []

    def _get_new_rule_name(self):
        return '_%s_%d' % (self.ANON_RULE_ID, next(self._count))

    @staticmethod
    def _flatten(tree):
        to_expand = [i for i, subtree in enumerate(tree.tail) if is_stree(subtree) and subtree.head == tree.head]
        if to_expand:
            tree.expand_kids_by_index(*to_expand)
        return bool(to_expand)

    def _visit(self, tree):
        "_visit simplifies the tree as much as possible"
        # visit until nothing left to change (not the most efficient, but good enough since it's only the grammar)
        while SVisitor_Recurse._visit(self, tree):
            pass

    def grammar(self, tree):
        changed = self._flatten(tree)

        if self._rules_to_add:
            changed = True
            tree.tail += self._rules_to_add
            self._rules_to_add = []
        return changed

    def _add_recurse_rule(self, mod, name, repeated_expr):
        new_rule = STree('ruledef', [mod+name, STree('rules_list', [STree('rule', [repeated_expr]), STree('rule', [name, repeated_expr])]) ])
        self._rules_to_add.append(new_rule)
        return new_rule

    def oper(self, tree):
        rule_operand, operator = tree.tail

        if operator == '*':
            # a : b c* d;
            #  --> in theory
            # a : b _c d;
            # _c : c _c |;
            #  --> in practice (much faster with PLY, approx x2)
            # a : b _c d | b d;
            # _c : _c c | c;
            new_name = self._get_new_rule_name() + '_star'
            self._add_recurse_rule(RuleMods.EXPAND, new_name, rule_operand)
            tree.head, tree.tail = 'rules_list', [STree('rule', [new_name]), STree('rule', [])]
        elif operator == '+':
            # a : b c+ d;
            #  -->
            # a : b _c d;
            # _c : _c c | c;
            new_name = self._get_new_rule_name() + '_plus'
            self._add_recurse_rule(RuleMods.EXPAND, new_name, rule_operand)
            tree.head, tree.tail = 'rule', [new_name]
        elif operator == '?':
            tree.head, tree.tail = 'rules_list', [rule_operand, STree('rule', [])]
        else:
            assert False, rule_operand

        return True # changed

    def rule(self, tree):
        # rules_list unpacking
        # a : b (c|d) e
        #  -->
        # a : b c e | b d e
        #
        # In actual terms:
        #
        # [rule [b] [rules_list [c] [d]] [e]]
        #   -->
        # [rules_list [rule [b] [c] [e]] [rule [b] [d] [e]] ]
        #
        changed = False

        if self._flatten(tree):
            changed = True

        for i, child in enumerate(tree.tail):
            if is_stree(child) and child.head == 'rules_list':
                # found. now flatten
                new_rules_list = []
                for option in child.tail:
                    new_rules_list.append(STree('rule', []))
                    # for each rule in rules_list
                    for j, child2 in enumerate(tree.tail):
                        if j == i:
                            new_rules_list[-1].tail.append(option)
                        else:
                            new_rules_list[-1].tail.append(child2)
                tree.head, tree.tail = 'rules_list', new_rules_list
                return True # changed

        return changed # Not changed

    def perm_rule(self, tree):
        """ Transforms a permutation rule into a rules_list of the permutations.
            x : a ^ b ^ c
             -->
            x : a b c | a c b | b a c | b c a | c a b | c b a

            It also handles operators on rules to be permuted.
            x : a ^ b? ^ c
             -->
            x : a b c | a c b | b a c | b c a | c a b | c b a
              | a c   | c a

            x : a ^ ( b | c ) ^ d
             -->
            x : a b d | a d b | b a d | b d a | d a b | d b a
              | a c d | a d c | c a d | c d a | d a c | d c a

            You can also insert a separator rule between permutated rules.
            x : a ^ b ^ c ^^ Z
             -->
            x : a Z b Z c | a Z c Z b | b Z a Z c
              | b Z c Z a | c Z a Z b | c Z b Z a

            x : a ^ b? ^ c ^^ Z
             -->
            x : a Z b Z c | a Z c Z b | b Z a Z c
              | b Z c Z a | c Z a Z b | c Z b Z a
              | a Z c     | c Z a
        """
        rules = tree.tail[0].tail
        has_sep = len(tree.tail) == 2
        sep = tree.tail[1] if has_sep else None
        tail = []
        for rule_perm in itertools.permutations(rules):
            rule = STree('rule', rule_perm)
            self._visit(rule)
            tail.append(rule)
        tree.head, tree.tail = 'rules_list', tail
        self._visit(tree)
        tree.tail = list(set(tree.tail))
        if has_sep:
            tail = []
            for rule in tree.tail:
                rule = [ i for i in itertools.chain.from_iterable([[sep,j]for j in rule.tail])][1:]
                rule = STree('rule', rule)
                self._visit(rule)
                tail.append(rule)
            tree.tail = tail
        return True

    modtokenlist = _flatten
    tokenmods = _flatten
    tokenvalue = _flatten
    number_list = _flatten
    rules_list = _flatten
    perm_phrase = _flatten



class ToPlyGrammar_Tranformer(STransformer):
    """Transforms grammar into ply-compliant grammar
    This is only a partial transformation that should be post-processd in order to apply
    XXX Probably a bad class name
    """
    @staticmethod
    def rules_list(tree):
        return '\n\t| '.join(tree.tail)

    @staticmethod
    def rule(tree):
        return ' '.join(tree.tail)

    @staticmethod
    def extrule(tree):
        return ' '.join(tree.tail)

    @staticmethod
    def oper(tree):
        return '(%s)%s' % (' '.join(tree.tail[:-1]), tree.tail[-1])

    @staticmethod
    def ruledef(tree):
        return STree('rule', (tree.tail[0], '%s\t: %s'%(tree.tail[0], tree.tail[1])))

    @staticmethod
    def optiondef(tree):
        return STree('option', tree.tail)

    @staticmethod
    def fragmentdef(tree):
        return STree('fragment', [None, None])

    @staticmethod
    def tokendef(tree):
        if len(tree.tail) > 2:
            return STree('token_with_mods', [tree.tail[0], tree.tail[1:]])
        else:
            return STree('token', tree.tail)

    @staticmethod
    def grammar(tree):
        return tree.tail

    @staticmethod
    def extgrammar(tree):
        return tree.tail


class SimplifySyntaxTree_Visitor(SVisitor):
    def __init__(self, rules_to_flatten, rules_to_expand, keep_empty_trees):
        self.rules_to_flatten = frozenset(rules_to_flatten)
        self.rules_to_expand = frozenset(rules_to_expand)
        self.keep_empty_trees = bool(keep_empty_trees)

    def __default__(self, tree):
        # Expand/Flatten rules if requested in grammar
        to_expand = [i for i, subtree in enumerate(tree.tail) if is_stree(subtree) and (
                        (subtree.head == tree.head and subtree.head in self.rules_to_flatten)
                        or (subtree.head in self.rules_to_expand)
                    ) ]
        if to_expand:
            tree.expand_kids_by_index(*to_expand)

        # Remove empty trees if requested
        if not self.keep_empty_trees:
            to_remove = [i for i, subtree in enumerate(tree.tail) if is_stree(subtree) and not subtree.tail]
            if to_remove:
                tree.remove_kids_by_index(*to_remove)

class FilterTokens_Visitor(SVisitor):
    def __default__(self, tree):
        if len(tree.tail) > 1:
            tree.tail = filter(is_stree, tree.tail)

class TokValue(Str):
    def __new__(cls, s, type=None, line=None, column=None, pos_in_stream=None, index=None):
        inst = Str.__new__(cls, s)
        inst.type = type
        inst.line = line
        inst.column = column
        inst.pos_in_stream = pos_in_stream
        inst.index = index
        return inst

class LexerWrapper(object):
    def __init__(self, lexer, newline_tokens_names, newline_char='\n', ignore_token_names=()):
        self.lexer = lexer
        self.newline_tokens_names = set(newline_tokens_names)
        self.ignore_token_names = ignore_token_names
        self.newline_char = newline_char

        self.current_state = lexer.current_state
        self.begin = lexer.begin

    def input(self, s):
        self.lineno = 1
        self._lexer_pos_of_start_column = -1
        self._tok_count = 0
        return self.lexer.input(s)

    def token(self):
        # get a new token that shouldn't be %ignored
        while True:
            self._tok_count += 1

            t = self.lexer.token()
            if not t:
                return t    # End of stream

            try:
                if t.type not in self.ignore_token_names:
                    self._wrap_token(t)
                    return t
            finally:
                # handle line and column
                # must happen after assigning, because we change _lexer_pos_of_start_column
                # in other words, we want to apply the token's effect to the lexer, not to itself
                if t.type in self.newline_tokens_names:
                    self._handle_newlines(t)


    def _wrap_token(self, t):
        tok_value = TokValue(t.value,
                        line = self.lineno,
                        column = t.lexpos-self._lexer_pos_of_start_column,
                        pos_in_stream = t.lexpos,
                        type = t.type,
                        index = self._tok_count,
                    )

        if hasattr(t, 'lexer'):
            t.lexer.lineno = self.lineno    # not self.lexer, because it may be another wrapper

        t.lineno = self.lineno
        t.value = tok_value

    def _handle_newlines(self, t):
        newlines = t.value.count(self.newline_char)
        self.lineno += newlines

        if newlines:
            self._lexer_pos_of_start_column = t.lexpos + t.value.rindex(self.newline_char)


class Grammar(object):
    def __init__(self, grammar, **options):
        # Some, but not all file-like objects have a 'name' attribute
        try:
            source = grammar.name
        except AttributeError:
            source = '<string>'
            tab_filename = "parsetab_%s" % str(hash(grammar)%(2**32))
        else:
            # PLY turns "a.b" into "b", so gotta get rid of the dot.
            tab_filename = "parsetab_%s" % os.path.basename(source).replace('.', '_')

        # Drain file-like objects to get their contents
        try:
            read = grammar.read
        except AttributeError:
            pass
        else:
            grammar = read()

        assert isinstance(grammar, StringTypes)

        cache_grammar = options.pop('cache_grammar', False)
        if cache_grammar:
            plyplus_cache_filename = PLYPLUS_DIR + '/%s-%s-%s.plyplus' % (tab_filename, hashlib.sha256(grammar).hexdigest(), __version__)
            if os.path.exists(plyplus_cache_filename):
                with open(plyplus_cache_filename, 'rb') as f:
                    self._grammar = pickle.load(f)
            else:
                self._grammar = self._create_grammar(grammar, source, tab_filename, options)

                with open(plyplus_cache_filename, 'wb') as f:
                    pickle.dump(self._grammar, f, pickle.HIGHEST_PROTOCOL)
        else:
            self._grammar = self._create_grammar(grammar, source, tab_filename, options)

    @staticmethod
    def _create_grammar(grammar, source, tab_filename, options):
        grammar_tree = grammar_parser.parse(grammar)
        if not grammar_tree:
            raise GrammarException("Parse Error: Could not create grammar")

        return _Grammar(grammar_tree, source, tab_filename, **options)

    def lex(self, text):
        return self._grammar.lex(text)

    def parse(self, text):
        return self._grammar.parse(text)

class _Grammar(object):
    def __init__(self, grammar_tree, source_name, tab_filename, **options):
        self.options = dict(options)
        self.debug = bool(options.pop('debug', False))
        self.just_lex = bool(options.pop('just_lex', False))
        self.ignore_postproc = bool(options.pop('ignore_postproc', False))
        self.auto_filter_tokens = bool(options.pop('auto_filter_tokens', True))
        self.keep_empty_trees = bool(options.pop('keep_empty_trees', True))
        self.tree_class = options.pop('tree_class', STree)

        if options:
            raise TypeError("Unknown options: %s"%options.keys())

        self.tab_filename = tab_filename
        self.source_name = source_name
        self.tokens = []    # for lex module
        self.rules_to_flatten = set()
        self.rules_to_expand = set()
        self._newline_tokens = set()
        self._ignore_tokens = set()
        self.lexer_postproc = None
        self._newline_value = '\n'

        # -- Build Grammar --
        self.subgrammars = {}
        ExtractSubgrammars_Visitor(source_name, tab_filename, self.options).visit(grammar_tree)
        SimplifyGrammar_Visitor().visit(grammar_tree)
        tokendefs = SimplifyTokenDefs_Visitor().visit(grammar_tree)
        NameAnonymousTokens_Visitor(tokendefs).visit(grammar_tree)
        ply_grammar_and_code = ToPlyGrammar_Tranformer().transform(grammar_tree)

        # code may be omitted
        if len(ply_grammar_and_code) == 1:
            ply_grammar, = ply_grammar_and_code
        else:
            ply_grammar, code = ply_grammar_and_code

            # prefix with newlines to get line-number count correctly (ensures tracebacks are correct)
            src_code = '\n' * (max(code.line, 1) - 1) + code

            # compiling before executing attaches source_name as filename: shown in tracebacks
            exec_code = compile(src_code, source_name, 'exec')
            exec(exec_code, locals())

        for x in ply_grammar:
            type_, (name, defin) = x.head, x.tail
            assert type_ in ('token', 'token_with_mods', 'rule', 'option', 'fragment'), "Can't handle type %s"%type_
            handler = getattr(self, '_add_%s' % type_)
            handler(name, defin)

        # -- Build lexer --
        lexer = lex.lex(module=self, reflags=re.UNICODE)
        lexer = LexerWrapper(lexer, newline_tokens_names=self._newline_tokens, newline_char=self._newline_value, ignore_token_names=self._ignore_tokens)
        if self.lexer_postproc and not self.ignore_postproc:
            lexer = self.lexer_postproc(lexer)  # apply wrapper
        self.lexer = lexer

        # -- Build Parser --
        if not self.just_lex:
            self.parser = yacc.yacc(module=self, debug=self.debug, tabmodule=tab_filename, errorlog=grammar_logger, outputdir=PLYPLUS_DIR)

    def __repr__(self):
        return '<Grammar from %s, tab at %s>' % (self.source_name, self.tab_filename)

    def lex(self, text):
        "Performs tokenizing as a generator"
        self.lexer.input(text)
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            yield tok

    def parse(self, text):
        "Parse the text into an AST"
        assert not self.just_lex

        self.errors = []
        tree = self.parser.parse(text, lexer=self.lexer, debug=self.debug)
        if not tree:
            self.errors.append("Could not create parse tree!")
        if self.errors:
            raise ParseError('\n'.join(self.errors))

        # Apply subgrammars
        if self.subgrammars:
            ApplySubgrammars_Visitor(self.subgrammars).visit(tree)

        SimplifySyntaxTree_Visitor(self.rules_to_flatten, self.rules_to_expand, self.keep_empty_trees).visit(tree)

        return tree

    def _add_fragment(self, _1, _2):
        pass

    def _add_option(self, name, defin):
        "Set an option"
        if name == '%newline_char':
            self._newline_value = ast.literal_eval(defin)   # XXX Safe enough?
        else:
            raise GrammarException( "Unknown option: %s " % name )


    def _extract_unless_tokens(self, modtokenlist):
        unless_toks_dict = {}
        unless_toks_regexps = []
        for modtoken in modtokenlist.tail:
            assert modtoken.head == 'token'
            modtok_name, modtok_value = modtoken.tail


            self._add_token(modtok_name, modtok_value)

            if not re.search(r'[^\w/-]', modtok_value):   # definitely not a regexp, let's optimize it
                unless_toks_dict[modtok_value] = modtok_name
            else:
                if not modtok_value.startswith('^'):
                    modtok_value = '^' + modtok_value
                if not modtok_value.endswith('$'):
                    modtok_value = modtok_value + '$'
                unless_toks_regexps += [(re.compile(modtok_value), modtok_name)]

        unless_toks_regexps.sort(key=lambda x:len(x[0].pattern), reverse=True)

        return unless_toks_dict, unless_toks_regexps

    def _unescape_unicode_in_token(self, token_value):
        # XXX HACK XXX
        # We want to convert unicode escapes into unicode characters,
        # because the regexp engine only supports the latter.
        # But decoding with unicode-escape converts whitespace as well,
        # which is bad because our regexps are whitespace agnostic.
        # It also unescapes double backslashes, which messes up with the
        # regexp.
        token_value = token_value.replace('\\'*2, '\\'*4)
        # The equivalent whitespace escaping is:
        # token_value = token_value.replace(r'\n', r'\\n')
        # token_value = token_value.replace(r'\r', r'\\r')
        # token_value = token_value.replace(r'\f', r'\\f')
        # but for speed reasons, I ended-up with this ridiculus regexp:
        token_value = re.sub(r'(\\[nrf])', r'\\\1', token_value)

        return codecs.getdecoder('unicode_escape')(token_value)[0]

    def _add_token_with_mods(self, name, defin):
        token_value, token_features = defin
        token_value = self._unescape_unicode_in_token(token_value)

        token_added = False
        if token_features is None:
            pass    # skip to simply adding it
        elif token_features.head == 'subgrammarobj':
            assert len(token_features.tail) == 1
            self.subgrammars[name] = token_features.tail[0]
        elif token_features.head == 'tokenmods':
            for token_mod in token_features.tail:
                mod, modtokenlist = token_mod.tail

                if mod == '%unless':
                    assert not token_added, "token already added, can't issue %unless"

                    unless_toks_dict, unless_toks_regexps = self._extract_unless_tokens(modtokenlist)

                    self.tokens.append(name)

                    def t_token(self, t):
                        t.type = getattr(self, '_%s_unless_toks_dict' % (name,)).get(t.value, name)
                        for regexp, tokname in getattr(self, '_%s_unless_toks_regexps' % (name,)):
                            if regexp.match(t.value):
                                t.type = tokname
                                break
                        return t
                    t_token.__doc__ = token_value

                    setattr(self, 't_%s' % (name,), t_token.__get__(self))
                    setattr(self, '_%s_unless_toks_dict' % (name,), unless_toks_dict)
                    setattr(self, '_%s_unless_toks_regexps' % (name,), unless_toks_regexps)

                    token_added = True

                elif mod == '%newline':
                    assert len(modtokenlist.tail) == 0
                    self._newline_tokens.add(name)

                elif mod == '%ignore':
                    assert len(modtokenlist.tail) == 0
                    self._ignore_tokens.add(name)
                else:
                    raise GrammarException("Unknown token modifier: %s" % mod)
        else:
            raise GrammarException("Unknown token feature: %s" % token_features.head)

        if not token_added:
            self.tokens.append(name)
            setattr(self, 't_%s'%name, token_value)

    def _add_token(self, name, token_value):
        assert isinstance(token_value, StringTypes), token_value
        self._add_token_with_mods(name, (token_value, None))

    def _add_rule(self, rule_name, rule_def):
        mods, = re.match('([@#?]*).*', rule_name).groups()
        if mods:
            assert rule_def[:len(mods)] == mods
            rule_def = rule_def[len(mods):]
            rule_name = rule_name[len(mods):]

        if RuleMods.EXPAND in mods:
            self.rules_to_expand.add( rule_name )
        elif RuleMods.FLATTEN in mods:
            self.rules_to_flatten.add( rule_name )

        def p_rule(self, p):
            subtree = []
            for child in p.__getslice__(1, None):
                if isinstance(child, self.tree_class) and (
                           (                            child.head in self.rules_to_expand )
                        or (child.head == rule_name and child.head in self.rules_to_flatten)
                        ):
                    # (EXPAND | FLATTEN) & mods -> here to keep tree-depth minimal, prevents unbounded tree-depth on
                    #                              recursive rules.
                    #           EXPAND1  & mods -> perform necessary expansions on children first to ensure we don't end
                    #                              up expanding inside our parents if (after expansion) we have more
                    #                              than one child.
                    subtree.extend(child.tail)
                else:
                    subtree.append(child)

            # Apply auto-filtering (remove 'punctuation' tokens)
            if self.auto_filter_tokens and len(subtree) != 1:
                subtree = list(filter(is_stree, subtree))

            if len(subtree) == 1 and (RuleMods.EXPAND in mods or RuleMods.EXPAND1 in mods):
                # Self-expansion: only perform on EXPAND and EXPAND1 rules
                p[0] = subtree[0]
            else:
                p[0] = self.tree_class(rule_name, subtree, skip_adjustments=True)
        p_rule.__doc__ = rule_def
        setattr(self, 'p_%s' % (rule_name,), types.MethodType(p_rule, self))


    @staticmethod
    def t_error(t):
        raise TokenizeError("Illegal character in input: '%s', line: %s, %s" % (t.value[:32], t.lineno, t.type))

    def p_error(self, p):
        if p:
            if isinstance(p.value, TokValue):
                msg = "Syntax error in input at '%s' (type %s) line %s col %s" % (p.value, p.type, p.value.line, p.value.column)
            else:
                msg = "Syntax error in input at '%s' (type %s) line %s" % (p.value, p.type, p.lineno)
        else:
            msg = "Syntax error in input (details unknown): %s" % p

        if self.debug:
            print(msg)

        self.errors.append(msg)

    start = "start"



########NEW FILE########
__FILENAME__ = selector
from __future__ import absolute_import

import re, copy
from itertools import chain
import weakref

from .strees import STree, is_stree
from .stree_collection import STreeCollection
from .plyplus import Grammar
from . import grammars

def sum_list(l):
    return chain(*l)  # Fastest way according to my tests

class _Match(object):
    __slots__ = 'match_track'

    def __init__(self, matched, selector_instance):
        self.match_track = [(matched, selector_instance)]

    def __hash__(self):
        return hash(tuple(self.match_track))
    def __eq__(self, other):
        return self.match_track == other.match_track

    @property
    def last_elem_matched(self):
        return self.match_track[0][0]

    def extend(self, other):
        self.match_track += other.match_track

    def get_result(self):
        yields = [m for m, s in self.match_track
                  if s.head=='elem'
                  and len(s.tail)>1
                  and s.tail[0].head=='yield']

        if not yields:
            # No yields; pick last element
            return self.match_track[-1][0]
        elif len(yields) == 1:
            return yields[0]
        else:
            # Multiple yields
            return tuple(yields)


class STreeSelector(STree):
    def _post_init(self):

        if self.head == 'modifier':
            assert self.tail[0].head == 'modifier_name' and len(self.tail[0].tail) == 1
            modifier_name = self.tail[0].tail[0]

            try:
                f = getattr(self, 'match__modifier__' + modifier_name.replace('-', '_').replace(':',''))
            except AttributeError:
                raise NotImplementedError("Didn't implement %s yet" % modifier_name)
            else:
                setattr(self, 'match__modifier', f)

        elif self.head == 'elem':
            if self.tail[-1].head == 'modifier':
                self.match__elem = self.match__elem_with_modifier
            else:
                self.match__elem = self.match__elem_without_modifier

        try:
            self._match = getattr(self, 'match__' + self.head)
        except AttributeError:
            self._match = None # We shouldn't be matched

    def match__elem_head(self, other):
        if not hasattr(other, 'head'):
            return []
        [expected_head] = self.tail
        return [other] if other.head == expected_head else []

    def match__elem_class(self, other):
        raise NotImplementedError('Classes not implemented yet')

    def match__elem_any(self, other):
        return [other]

    def match__elem_regexp(self, other):
        if is_stree(other):
            s = other.head
        else:
            s = unicode(other)   # hopefully string
        regexp = self.tail[1]
        assert regexp[0] == regexp[-1] == '/'
        regexp = regexp[1:-1]
        return [other] if re.match(regexp, s) else []

    def match__elem_tree_param(self, other):
        assert self.head == 'elem_tree', 'Missing keyword: %s' % self
        return [other] if self.tail[1] == other else []

    def match__modifier__is_parent(self, other):
        return [other] if (is_stree(other) and other.tail) else []
    def match__modifier__is_leaf(self, other):
        return [other] if not is_stree(other) else []
    def match__modifier__is_root(self, other):
        return [other] if is_stree(other) and other is self.match_root() else []
    def match__modifier__is_first_child(self, other):
        return [other] if other.index_in_parent == 0 else []

    def match__elem_with_modifier(self, other):
        matches = self.tail[-1].match__modifier(other)   # skip possible yield
        matches = filter(self.tail[-2]._match, matches)
        return [_Match(m, self) for m in matches]

    def match__elem_without_modifier(self, other):
        matches = self.tail[-1]._match(other)   # skip possible yield
        return [_Match(m, self) for m in matches]


    def match__selector_list(self, other):
        assert self.head == 'result_list', 'call to _init_selector_list failed!'
        set_, = self.tail
        return [other] if other in set_ else []

    def _init_selector_list(self, other):
        if self.head == 'result_list':
            res = sum_list(kid._match(other) for kid in self.selector_list.tail)
            res = [r.get_result() for r in res]    # lose match objects, localize yields
            self.tail = [frozenset(res)] + self.tail[1:]
        else:
            res = sum_list(kid._match(other) for kid in self.tail)
            res = [r.get_result() for r in res]    # lose match objects, localize yields
            self.selector_list = copy.copy(self)
            self.reset('result_list', [frozenset(res)])

    def _travel_tree_by_op(self, tree, op):
        if not hasattr(tree, 'parent') or tree.parent is None:
            return  # XXX should I give out a warning?
        try:
            if op == '>':   # travel to parent
                yield tree.parent()
            elif op == '+': # travel to previous adjacent sibling
                new_index = tree.index_in_parent - 1
                if new_index < 0:
                    raise IndexError('We dont want it to overflow back to the last element')
                yield tree.parent().tail[new_index]
            elif op == '~': # travel to all previous siblings
                for x in tree.parent().tail[ :tree.index_in_parent ]:
                    yield x
            elif op == ' ': # travel back to root
                parent = tree.parent()  # TODO: what happens if the parent is garbage-collected?
                while parent is not None:
                    yield parent
                    if parent is self.match_root():
                        break
                    parent = parent.parent() if parent.parent else None

        except IndexError:
            pass


    def _match_selector_op(self, matches_so_far):
        _selector = self.tail[0]
        op = self.tail[1].tail[0] if len(self.tail) > 1 else ' '


        matches_found = []
        for match in matches_so_far:
            to_check = list(self._travel_tree_by_op(match.last_elem_matched, op))

            if to_check:
                for match_found in _selector.match__selector(to_check):
                    match_found.extend( match )
                    matches_found.append( match_found )

        return matches_found

    def match__selector(self, other):
        elem = self.tail[-1]
        if is_stree(other):
            res = sum_list(other.map(elem._match))
        else:
            res = sum_list([elem._match(item) for item in other]) # we were called by a selector_op
        if not res:
            return []   # shortcut

        if self.tail[0].head == 'selector_op':
            res = self.tail[0]._match_selector_op(res)

        return res

    def match__start(self, other):
        assert len(self.tail) == 1
        return self.tail[0]._match(other)

    # def _match(self, other):
    #     return getattr(self, 'match__' + self.head)(other)

    def match(self, other, **kwargs):
        other.calc_parents()    # TODO add caching?
        self.map(lambda x: is_stree(x) and setattr(x, 'match_root', weakref.ref(other)))

        # Selectors are re-usable right now, so we have to handle both first
        # use, and re-use. This will be bad if ever used threaded. The right
        # thing to do (if we want to keep caching them) is to deepcopy on each
        # use. It should also make the code simpler.
        for elem_tree_param in self.filter(lambda x: is_stree(x)
                                          and x.head in ('elem_tree_param', 'elem_tree')):
            elem_tree_param.reset('elem_tree', [elem_tree_param.tail[0], kwargs[elem_tree_param.tail[0]]])

        str_args = dict((k,re.escape(v)) for k,v in kwargs.items() if isinstance(v, (str, unicode)))
        for elem_regexp in self.filter(lambda x: is_stree(x) and x.head == 'elem_regexp'):
            elem_regexp.tail = [elem_regexp.tail[0], elem_regexp.tail[0].format(**str_args)]

        # Evaluate all selector_lists into result_lists
        selector_lists = self.filter(lambda x: is_stree(x)
                                     and x.head in ('selector_list', 'result_list'))
        for selector_list in reversed(selector_lists):  # reverse turns pre-order -> post-order
            selector_list._init_selector_list(other)

        # Match and return results
        return STreeCollection([x.get_result() for x in self._match(other)])


selector_dict = {}

selector_grammar = Grammar(grammars.open('selector.g'), tree_class=STreeSelector)
def selector(text):
    if text not in selector_dict:
        selector_ast = selector_grammar.parse(text)
        selector_ast.map(lambda x: is_stree(x) and x._post_init())
        selector_dict[text] = selector_ast
    return selector_dict[text]

def install():
    def select(self, text, **kw):
        return selector(text).match(self, **kw)
    def select1(self, text, **kw):
        [r] = self.select(text, **kw)
        return r

    def collection_select(self, *args, **kw):
        return STreeCollection(sum_list(stree.select(*args, **kw) for stree in self))

    STree.select = select
    STree.select1 = select1

    STreeCollection.select = collection_select
    STreeCollection.select1 = select1


########NEW FILE########
__FILENAME__ = strees
from __future__ import absolute_import

from weakref import ref
from copy import deepcopy
from .stree_collection import STreeCollection

from .utils import StringTypes, StringType, classify, _cache_0args


class WeakPickleMixin(object):
    """Prevent pickling of weak references to attributes"""

    weak_attributes = (
            'parent',
        )

    def __getstate__(self):
        dict = self.__dict__.copy()

        # Pickle weak references as hard references, pickle deals with circular references for us
        for key, val in dict.items():
            if isinstance(val, ref):
                dict[key] = val()

        return dict

    def __setstate__(self, data):
        self.__dict__.update(data)

        # Convert hard references that should be weak to weak references
        for key in data:
            val = getattr(self, key)
            if key in self.weak_attributes and val is not None:
                setattr(self, key, ref(val))

class Str(WeakPickleMixin, StringType): pass

class STree(WeakPickleMixin, object):
    # __slots__ = 'head', 'tail', '_cache', 'parent', 'index_in_parent'

    def __init__(self, head, tail, skip_adjustments=False):
        if skip_adjustments:
            self.head, self.tail = head, tail
            self.clear_cache()
        else:
            self.reset(head, tail)

    def reset(self, head, tail):
        "Warning: calculations done on tree will have to be manually re-run on the tail elements"    # XXX
        self.head = head
        if type(tail) != list:
            tail = list(tail)
        for i, x in enumerate(tail):
            if type(x) in StringTypes:
                tail[i] = Str(x)
        self.tail = tail
        self.clear_cache()

    def reset_from_tree(self, tree):
        self.reset(tree.head, tree.tail)

    def clear_cache(self):
        self._cache = {}

    def expand_kids_by_index(self, *indices):
        for i in sorted(indices, reverse=True): # reverse so that changing tail won't affect indices
            kid = self.tail[i]
            self.tail[i:i+1] = kid.tail
        self.clear_cache()

    def remove_kids_by_index(self, *indices):
        for i in sorted(indices, reverse=True): # reverse so that changing tail won't affect indices
            del self.tail[i]
        self.clear_cache()

    def remove_kid_by_head(self, head):
        for i, child in enumerate(self.tail):
            if child.head == head:
                del self.tail[i]
                self.clear_cache()
                return
        raise ValueError("head not found: %s"%head)

    def remove_kids_by_head(self, head):
        removed = 0
        for i, child in reversed(list(enumerate(self.tail))):
            if is_stree(child) and child.head == head:
                del self.tail[i]
                removed += 1
        if removed:
            self.clear_cache()
        return removed

    def remove_kid_by_id(self, child_id):
        for i, child in enumerate(self.tail):
            if id(child) == child_id:
                del self.tail[i]
                self.clear_cache()
                return
        raise ValueError("id not found: %s"%child_id)

    def prune_by_head(self, head):
        self.remove_kids_by_head(head)
        for kid in self.tail:
            if hasattr(kid, 'prune_by_head'):
                kid.prune_by_head(head)

    def remove_from_parent(self):
        self.parent().remove_kid_by_id(id(self))
        self.parent = None

    def expand_into_parent(self):
        self.parent().expand_kids_by_index(self.index_in_parent)
        self.parent = None

    def __len__(self):
        raise Exception('len')
    def __nonzero__(self):
        return True    # XXX ???
    def __bool__(self):
        return True    # XXX ???
    def __hash__(self):
        return hash((self.head, tuple(self.tail)))
    def __eq__(self, other):
        try:
            return self.head == other.head and self.tail == other.tail
        except AttributeError:
            return False
    def __ne__(self, other):
        return not (self == other)

    def __getstate__(self):
        dict = super(STree, self).__getstate__()
        # No point in pickling a cache...
        dict.pop('_cache', None)
        return dict

    def __setstate__(self, data):
        super(STree, self).__setstate__(data)

        # Ensure we've got a clean cache
        self.clear_cache()

    def __deepcopy__(self, memo):
        return type(self)(self.head, deepcopy(self.tail, memo))

    @property
    @_cache_0args
    def named_tail(self):
        "Warning: Assumes 'tail' doesn't change"
        return classify(self.tail, lambda e: is_stree(e) and e.head)
    def leaf(self, leaf_head, default=KeyError):
        try:
            [r] = self.named_tail[leaf_head]
        except KeyError:
            if default == KeyError:
                raise
            r = default
        return r

    def leaves(self, leaf_head):
        return self.leaves_by_pred(lambda x: x.head == leaf_head)

    def leaves_by_pred(self, pred):
        return STreeCollection(filter(pred, self.tail))

    def calc_parents(self):
        for i, kid in enumerate(self.tail):
            if is_stree(kid):
                kid.calc_parents()
            kid.parent = ref(self)
            kid.index_in_parent = i

        if not hasattr(self, 'parent'):
            self.parent = None
            self.index_in_parent = None

    def calc_depth(self, depth=0):
        self.depth = depth
        for kid in self.tail:
            try:
                kid.calc_depth(depth + 1)
            except AttributeError:
                pass

    # == Functional operations (STree -> list) ==

    def find_predicate(self, predicate):
        "XXX Deprecated"
        return self.filter(predicate)

    def map(self, func, context=None):
        if context is None:
            context = [ func(self) ]
        for kid in self.tail:
            if hasattr(kid, 'map'):
                kid.map(func, context)
            context.append( func(kid) )
        return context

    def filter(self, func, context=None):
        if context is None:
            context = []
        if func(self):
            context.append( self )
        for kid in self.tail:
            if hasattr(kid, 'filter'):
                kid.filter(func, context)
        return context

    def reduce(self, func, initial=None):
        return reduce(func, [kid.reduce(func, initial)
                for kid in self.tail
                if hasattr(kid, 'reduce')
            ], initial)

    def count(self):
        return self.reduce(lambda x,y: x+y, 1)

    # == Tree Navigation (assumes parent) ==

    @property
    def is_first_kid(self):
        return self.index_in_parent == 0

    @property
    def is_last_kid(self):
        return self.index_in_parent == len(self.parent().tail)-1

    @property
    def next_kid(self):
        return self.parent().tail[self.index_in_parent + 1]

    @property
    def prev_kid(self):
        new_index = self.index_in_parent - 1
        if new_index < 0:
            # We dont want it to overflow back to the last element
            raise IndexError('First element in tail')
        return self.parent().tail[new_index]

    @property
    def ancestors(self):
        parent = self.parent()
        while parent:
            yield parent
            parent = parent.parent() if parent.parent else None

    # == Output Functions ==

    def _to_pydot(self, graph):
        import pydot
        color = hash(self.head) & 0xffffff
        if not (color & 0x808080):
            color |= 0x808080

        def new_leaf(leaf):
            node = pydot.Node(id(leaf), label=repr(leaf))
            graph.add_node(node)
            return node

        subnodes = [kid._to_pydot(graph) if is_stree(kid) else new_leaf(kid) for kid in self.tail]
        node = pydot.Node(id(self), style="filled", fillcolor="#%x"%color, label=self.head)
        graph.add_node(node)

        for subnode in subnodes:
            graph.add_edge(pydot.Edge(node, subnode))

        return node

    def _pretty(self, indent_str='  '):
        if len(self.tail) == 1 and not is_stree(self.tail[0]):
            return [ indent_str*self.depth, self.head, '\t', self.tail[0], '\n']

        l = [ indent_str*self.depth, self.head, '\n' ]
        for n in self.tail:
            try:
                l += n._pretty(indent_str)
            except AttributeError:
                l += [ indent_str*(self.depth+1), StringType(n), '\n' ]

        return l

    def pretty(self, **kw):
        self.calc_depth()
        return ''.join(self._pretty(**kw))

    def to_png_with_pydot(self, filename):
        import pydot
        graph = pydot.Dot(graph_type='digraph', rankdir="LR")
        self._to_pydot(graph)
        graph.write_png(filename)

    def __repr__(self):
        return '%s(%s)' % (self.head, ', '.join(map(repr,self.tail)))



def is_stree(obj):
    return type(obj) is STree or isinstance(obj, STree)

class SVisitor(object):
    def visit(self, tree):
        assert tree

        open_queue = [tree]
        queue = []

        while open_queue:
            node = open_queue.pop()
            queue.append(node)
            open_queue += filter(is_stree, node.tail)

        for node in reversed(queue):
            getattr(self, node.head, self.__default__)(node)

    def __default__(self, tree):
        pass

class SVisitor_Recurse(object):

    def visit(self, tree):
        self._visit(tree)
        return tree

    def _visit(self, tree):
        pre_f = getattr(self, 'pre_' + tree.head, None)
        if pre_f:
            pre_f(tree)

        for branch in tree.tail:
            if is_stree(branch):
                self._visit(branch)

        f = getattr(self, tree.head, self.__default__)
        return f(tree)

    def __default__(self, tree):
        pass

class STransformer(object):
    def transform(self, tree):
        return self._transform(tree)

    def _transform(self, tree):
        pre_f = getattr(self, 'pre_' + tree.head, None)
        if pre_f:
            return pre_f(tree)

        branches = [
                self._transform(branch) if is_stree(branch) else branch
                for branch in tree.tail
            ]

        new_tree = tree.__class__(tree.head, branches)
        if hasattr(tree, 'depth'):
            new_tree.depth = tree.depth # XXX ugly hack, need a general solution for meta-data (meta attribute?)
        if hasattr(tree, 'parent'):
            # XXX ugly hack, need a general solution for meta-data (meta attribute?)
            new_tree.parent = tree.parent
            new_tree.index_in_parent = tree.index_in_parent

        f = getattr(self, new_tree.head, self.__default__)
        return f(new_tree)

    def __default__(self, tree):
        return tree

########NEW FILE########
__FILENAME__ = stree_collection

class STreeCollection(object):
    def __init__(self, strees):
        self.strees = list(strees)

    def __len__(self):
        return len(self.strees)

    def __getitem__(self, index):
        return self.strees[index]

    def __eq__(self, other):
        return self.strees == other

    def __repr__(self):
        return '%s%s' % (type(self).__name__, repr(self.strees))

    def leaf(self, leaf_head):
        for stree in self.strees:
            try:
                yield stree.leaf(leaf_head)
            except KeyError:
                pass

########NEW FILE########
__FILENAME__ = python4ply-sample
# This contains nearly every legal token and grammar in Python.
# Used for the python_yacc.py --self-test input.

# Needed so Python 2.5's compiler understands this code
from __future__ import with_statement

# Might as well try the other imports here
import a
import a.b
import a.b.c
import a.b.c.d.e.f.g.h

import a as A
import a as A, b as B
import a.b as AB, a.b as B, a.b.c

from mod1 import mod2
from mod1.mod2 import mod3

from qmod import *
from qmod.qmod2 import *
from a1 import a1

from a import (xrt,
   yrt,
   zrt,
   zrt2)
from a import (xty,
   yty,
   zty,
   zrt2,)
from qwe import *
from qwe.wer import *
from qwe.wer.ert.rty import *

from .a import y
from ..a import y
from ..a import y as z
#from ...qwe import * This is not allowed
from ...a import (y as z, a as a2, t,)
from .................... import a,b,c  # 20 levels
from ...................... import (a,b,c)  # 22 levels


a = 2
a,b = 1, 222
a, = 1,
a, b, = 1, 234
a, b, c
1;
1;27
1;28;
1;29;3
1;21;33;
a.b
a.b.c
a.b.c.d.e.f

# Different number
0xDEADBEEF
0xDEADBEEFCAFE
0xDeadBeefCafe
0xDeadBeefCafeL
0xDeadBeefCafel

0123
0177
1.234
10E-3
1.2e+03
-1.9e+03
9j
9.8j
23.45E-9j


# 'factor' operations
a = -1
a = +1
a = ~1
b ** c
a = + + + + 1

# 'comparison' 'comp_op' expressions
a < b
a > b
a == b
a >= b
a <= b
a != b
a in b
a is b
a not in b
a is not b

# arith_expr
1 + 2
1 + 2 + 3
1 + 2 + 3 + 4
1 - 2
1 - 2 - 3
1 - 2 + 3 - 4 + 5
# 
1 - 2 + - 3 - + 4
1 + + + + + 1

# factors
a * 1
a * 1 * 2
b / 2
b / 2 / 3
c % 9
c % 9 % 7
d // 8
d // 8 // 5

a * 1 / 2 / 3 * 9 % 7 // 2 // 1


truth or dare
war and peace
this and that or that and this
a and b and c and d
x or y or z or w
not a
not not a
not not not a
not a or not b or not c
not a or not b and not c and not d

# All of the print statements
print
print "x"
print "a",
print 1, 2
print 1, 2,
print 1, 2, 93
print >>x
print >>x, 1
print >>x, 1,
print >>x, 9, 8
print >>x, 9, 8, 7

def yield_function():
    yield
    yield 1
    x = yield

@spam.qwe
def eggs():
    pass

@spam
def eggs():
    pass

@spam.qwe()
def eggs():
    pass

@spam1.qwe()
@spam2.qwe()
@spam3.qwe()
@spam3.qwe()
def eggs():
    pass

@spam(1)
def eggs():
    pass

@spam2\
(\
)
def eggs2():
    pass


@spam3\
(\
this,\
blahblabh\
)
def eggs9():
    pass

@spam\
(
**this
)
def qweqwe():
    pass

@spam.\
and_.\
eggs\
(
**this
)
def qweqwe():
    pass


spam()
spam(1)
spam(1,2)
spam(1,2,3)
spam(1,)
spam(1,2,)
spam(1,2,3,)
spam(*a)
spam(**a)
spam(*a,**b)
spam(1, *a)
spam(1, *a, **b)
spam(1, **b)
def spam(x): pass
def spam(x,): pass
def spam(a, b): pass
def spam(a, b,): pass
def spam(a, b, c): pass
def spam(a, *args): pass
def spam(a, *args, **kwargs): pass
def spam(a, **kwargs): pass
def spam(*args, **kwargs): pass
def spam(**kwargs): pass
def spam(*args): pass

def spam(x=1): pass
def spam(x=1,): pass
def spam(a=1, b=2): pass
def spam(a=1, b=2,): pass
def spam(a=1, *args): pass
def spam(a=9.1, *args, **kwargs): pass
def spam(a="", **kwargs): pass
def spam(a,b=1, *args): pass
def spam(a,b=9.1, *args, **kwargs): pass
def spam(a,b="", **kwargs): pass

def spam(a=1, b=2, *args): pass
def spam(a=1, b=2, *args, **kwargs): pass
def spam(a=1, b=2, **kwargs): pass

def spam(a=1, b=2, c=33, d=4): pass

#def spam((a) = c): pass # legal in Python 2.5, not 2.6
#def spam((((a))) = cc): pass # legal in Python 2.5, not 2.6
def spam((a,) = c): pass
def spam((a,b) = c): pass
def spam((a, (b, c)) = x96): pass
def spam((a,b,c)=x332): pass
def spam((a,b,c,d,e,f,g,h)=x12323): pass

# This show that the compiler module uses the function name location
# for the ast.Function lineno, and not the "def" reserved word.
def \
 spam \
  ( \
  ) \
  : \
  pass

a += 1
a -= 1
a *= 2
a /= 2
a %= 3
a &= 4
a |= 4
a ^= 5
a <<= 6
a >>= 7
a **= 9
a //= 10

b \
 += \
   3

a = b = c
a = b = c = d
# Shows that the ast.Assign gets the lineno from the first '='
a \
 = \
  b \
   = \
     c

a < b < c < d < e
a == b == c != d != e

a | b | c | d
a & b & c & d
a | b | c & d & e
a ^ b
a ^ b ^ c ^ d

a << 1
a << 1 << 2
a << c() << d[1]
a >> 3
a >> 6 >> 5
a >> 6 >> 5 >> 4 >> 3
a << 1 >> 2 << 3 >> 4

del a
del a,
del a, b
del a, b,
del a, b, c
del a, b, c,
del a.b
del a.b,
del a.b.c.d.e.f
del a[0]
del a[0].b
del (a, b)
del a[:5]
del a[:5,1,2,...]
del [a,b,[c,d]]


x = ()
x = (0)
x = (a,)
# x\
#  \
# =\
# (\   <-- I put the Assign line number here
# a\
# ,\   <-- Python puts the Assign line number here
# )

def spam():
    a = (yield x)

s = "this " "is "   "string " "concatenation"
s = "so " \
   "is "  \
   "this."

#for x, in ((1,),):
#    print x

for i in range(10):
    continue
for a,b in x:
    continue
for (a,b) in x:
    break

# p_trailer_3 : LSQB subscriptlist RSQB
x[0]
x[0,]
x[0:1]
x[0:1:2]
x[:3:4]
x[::6]
x[8::9]

a[...]
a[:]
b[:9]
c[:9,]
d[-4:]
a[0]**3
c[:9,:1]
q[7:,]
q[::4,]
q[:,]
t[::2]
r[1,2,3]
r[1,2,3,]
r[1,2,3,4]
r[1,2,3,4,]
t[::]
t[::,::]
t[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
  1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
  1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
  1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,
  1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
p[1,2:,3:4]
p[1,2:,3:4,5:6:7,::,:9,::2, 1:2:3,
  1,2:,3:4,5:6:7,::,:9,::2, 1:2:3]


x[1] = 1
x[1:2] = 2
x[1:] = 3
x[:1] = 4
x[:] = 5
a[1,2] = 11
a[1:2,3:4] = 12

[a] = [1]
[a] = 1,
[a,b,[c,d]] = 1,2,(3,4)


# this is an 'atom'
{}

# an atom with a dictmaker
{1:2}
{1:2,}
{1:2,3:4}
{1:2,3:4,}
{1:2,3:4,5:6}
{1:2,3:4,5:6,}
{"name": "Andrew", "language": "Python", "dance": "tango"}

# Some lists
[]
[1]
[1,]
[1,2]
[1,2,]
[1,2,3,4,5,6]
[1,2,3,4,5,6,]

# List comprehensions
[1 for c in s]
[1 for c1 in s1 for c2 in s2]
[1 for c1 in s1 for c2 in s2 for c3 in s3]
[1 for c in s if c]
#TODO [(c,c2) for c in s1 if c != "n" for c2 in s2 if c2 != "a" if c2 != "e"]

[x.y for x.y in "this is legal"]

# Generator comprehensions
(1 for c in s)
(1 for c in s for d in t)

(x.y for x.y in "this is legal")
#TODO (1 for c in s if c if c+1 for d in t for e in u if d*e == c if 1 if 0)

# class definitions
class Spam:
    pass
# This shows that Python gets the line number from the 'NAME'
class \
 Spam:
    pass

class Spam: pass

class Spam(object):
    pass

class \
 Spam \
  (
   object
 ) \
 :
 pass

class Spam(): pass

class \
  Spam\
  ():
  pass

# backquotes
# Terminal "," are not supported
`1`
`1,2`
`1,2,3`
`a,b,c,d,e,f,g,h`

def a1():
    return

def a2():
    return 1,2

def a3():
    return 1,2,3

try:
    f()
except:
    pass

try:
    f()
finally:
    pass

try:
    f()
except Spam:
    a=2

try:
    f()
except (Spam, Eggs):
    a=2

# This is a Python 2.6-ism
#try:
#    f()
#except Spam as err:
#    p()

try:
    f()
except Spam, err:
    p()


try:
    f()
except Spam:
    g()
except Eggs:
    h()
except (Vikings+Marmalade), err:
    i()

try:
    a()
except Spam: b()
except Spam2: c()
finally: g()

try:
    a()
except:
    b()
else:
    c()

try: a()
except: b()
else: c()
finally: d()

try:
    raise Fail1
except:
    raise

try:
    raise Fail2, "qwer"
except:
    pass

try:
    raise Fail3, "qwer", "trw23r"
except:
    pass

try:
    raise AssertionError("raise an instance")
except:
    pass

# with statements

with x1:
  1+2
with x2 as a:
  2+3
with x3 as a.b:
  9
with x4 as a[1]:
  10
with (x5,y6) as a.b[1]:
  3+4
with x7 as (a,b):
  4+5
#with x as (a+b):  # should not work
#  5+6

with x8 as [a,b,[c.x.y,d[0]]]:
  (9).__class__

# make this 'x' and get the error "name 'x' is local and global"
# The compiler module doesn't verify this correctly.  Python does
def spam(xyz):
    global z
    z = z + 1

    global x, y
    x,y=y,z

    global a, b, c
    a,b,c = b,c,a

exec "x=1"
exec "x=1" in x
exec "z=1" in z, y
exec "raise" in {}, globals()

assert 0
assert f(x)
assert f(x), "this is not right"
assert f(x), "this is not %s" % ["left", "right"][1]

if 1:
    g()

if 1: f()

if (a+1):
    f()
    g()
    h()
    pass
else:
    pass
    a()
    b()

if a:
    z()
elif b():
    y()
elif c():
    x

if a:
    spam()
elif f()//g():
    eggs()
else:
    vikings()


while 1:
    break

while a > 1:
    a -= 1
else:
    raise AssertionError("this is a problem")

for x in s:
    1/0
for (a,b) in s:
    2/0
for (a, b.c, d[1], e[1].d.f) in (p[1], t.r.e):
    f(a)
for a in b:
    break
else:
    print "b was empty"
    print "did you hear me?"

# testlist_safe
[x for x in 1]
#[x for x in 1,]  # This isn't legal
[x for x in 1,2]
[x for x in 1,2,]
[x for x in 1,2,3]
[x for x in 1,2,3,]
[x for x in 1,2,3,4]
[x for x in 1,2,3,4,]

#[x for x in lambda :2]
#[x for x in lambda x:2*x]  # bug in compiler.transfomer prevents
#[x for x in lambda x,y:x*y]  # testing "safe" lambdas with arguments
#[x for x in lambda x,y=2:x*y]

lambda x: 5 if x else 2
#TODO: [ x for x in lambda: True, lambda: False if x() ]
#[ x for x in lambda: True, lambda: False if x else 2 ]


x = 1 if a else 2
y = 1 if a else 2 if b else 3

func = lambda : 1
func2 = lambda x, y: x+y
func3 = lambda x=2, y=3: x*y

f(1)
f(1,)
f(1,2)
f(1,2,)
f(1,2,3)
f(1,2,3,)
f(1,2,3,4)
f(1,2,3,4,)
f(a=1)
f(a=1,)
f(a=1, b=2)
f(a=1, b=2,)
f(a=1, b=2, c=3)
f(a=1, b=2, c=3,)
f(9, a=1)
f(9, a=1,)
f(9, a=1, b=2)
f(9, a=1, b=2,)
f(9, 8, a=1)
f(9, 7, a=1, b=2)

f(c for c in s)
f(x=2)
f(x, y=2)
f(x, *args, **kwargs)

#f(x+y=3)

## check some line number assignments.  Python's compiler module uses
## the first term inside of the bracket/parens/braces.  I prefer the
## line number of the first character (the '[', '(', or '{')

x = [


  "a", "b",
  # comment
  "c", "d", "e", "f"


]

y = (

  c for c in s)

def f():
  welk = (



      yield
      )

d = {


  "a":
 1,
  101: 102,
  103: 104}

# Check all the different ways of escaping and counting line numbers

"""
This text
goes over
various
lines.
"""

# this should have the right line number
x_triple_quoted = 3

'''
blah blah
and
blah
'''

# this should have the right line number
y_triple_quoted = 34

r"""
when shall we three meet again
"""

# this should have the right line number
z_triple_quoted = 3235

r'''
This text
goes over
various
lines.
'''

# this should have the right line number
x_triple_quoted = 373

u"""
When in the
course of human
events
"""

# this should have the right line number
x_triple_quoted = 65

ur'''
We hold these truths to be self-evident
'''

# this should have the right line number
y_triple_quoted = 3963


# Check the escaping for the newline
s1 = r'''
  This
has a newline\
and\
a\
few
more

'''

1

s1 = ur"""
Some more \
with\
newlines

"""
str123 = 'single quoted line\
line with embedded\
newlines.'

str367 = "another \
with \
embedded\
newlines."


u"\N{LATIN SMALL LETTER ETH}"
ur"\N{LATIN SMALL LETTER ETH}"

f(1
 +
 2)


print "The end"

########NEW FILE########
__FILENAME__ = python_sample1
def fib(n):
    if n <= 1: return 1
    return fib(n-1) + fib(n-2)

for i in range(11):
    print fib(i),

########NEW FILE########
__FILENAME__ = python_sample2
"""Sample 2
Author: Erez
"""
N = 16

print "Calculating Fib sequence, %d members" % N
a = 1   # fib(0)
b = 1   # fib(1)
for i in range(N):
    print a, '-',
    a, b = b, a+b


########NEW FILE########
__FILENAME__ = test_grammars
from __future__ import absolute_import, print_function
from io import open

import unittest
import time
import sys, os, glob
import logging

from plyplus import grammars
from plyplus.plyplus import Grammar

logging.basicConfig(level=logging.INFO)

CUR_PATH = os.path.split(__file__)[0]
def _read(n, *args):
    kwargs = {'encoding': 'iso-8859-1'}
    with open(os.path.join(CUR_PATH, n), *args, **kwargs) as f:
        return f.read()

if os.name == 'nt':
    if 'PyPy' in sys.version:
        PYTHON_LIB = os.path.join(sys.prefix, 'lib-python', sys.winver)
    else:
        PYTHON_LIB = os.path.join(sys.prefix, 'Lib')
else:
    PYTHON_LIB = '/usr/lib/python2.7/'

class TestPythonG(unittest.TestCase):
    def setUp(self):
        with grammars.open('python.g') as g:
            self.g = Grammar(g)

    def test_basic1(self):
        g = self.g
        g.parse(_read('python_sample1.py'))
        g.parse(_read('python_sample2.py'))
        g.parse(_read('../../examples/calc.py'))
        g.parse(_read('../grammar_lexer.py'))
        g.parse(_read('../grammar_parser.py'))
        g.parse(_read('../strees.py'))
        g.parse(_read('../grammars/python_indent_postlex.py'))

        g.parse(_read('../plyplus.py'))

        g.parse("c,d=x,y=a+b\nc,d=a,b\n")

    def test_weird_stuff(self):
        g = self.g
        for n in range(3):
            if n == 0:
                s = """
a = \\
        \\
        1\\
        +2\\
-3
print a
"""
            elif n == 1:
                s = "a=b;c=d;x=e\n"

            elif n == 2:
                s = r"""
@spam3 (\
this,\
blahblabh\
)
def eggs9():
    pass

"""

            g.parse(s)


    def test_python_lib(self):
        g = self.g

        path = PYTHON_LIB
        files = glob.glob(path+'/*.py')
        start = time.time()
        for f in files:
            f2 = os.path.join(path, f)
            logging.info( f2 )
            g.parse(_read(f2))

        end = time.time()
        logging.info( "test_python_lib (%d files), time: %s secs"%(len(files), end-start) )

    def test_python4ply_sample(self):
        g = self.g
        g.parse(_read(r'python4ply-sample.py'))


class TestConfigG(unittest.TestCase):
    def setUp(self):
        with grammars.open('config.g') as g:
            self.g = Grammar(g)

    def test_config_parser(self):
        g = self.g
        g.parse("""
            [ bla Blah bla ]
            thisAndThat = hel!l%o/
            one1111:~$!@ and all that stuff

            [Section2]
            whatever: whatever
            """)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_parser
from __future__ import absolute_import

import unittest
import logging
import os
import sys
try:
    from cStringIO import StringIO as cStringIO
except ImportError:
    # Available only in Python 2.x, 3.x only has io.StringIO from below
    cStringIO = None
from io import (
        StringIO as uStringIO,
        open,
    )
from ply import yacc

from plyplus.plyplus import Grammar, TokValue, ParseError

logging.basicConfig(level=logging.INFO)

CUR_PATH = os.path.dirname(__file__)
def _read(n, *args):
    with open(os.path.join(CUR_PATH, n), *args) as f:
        return f.read()


FIB = """
def fib(n):
    if n <= 1:
        return 1
    return fib(
n-1) + fib(n-2)

for i in range(11):
    print fib(i),
"""

class TestPlyPlus(unittest.TestCase):
    def test_basic1(self):
        g = Grammar("start: a+ b a+? 'b' a*; b: 'b'; a: 'a';")
        r = g.parse('aaabaab')
        self.assertEqual( ''.join(x.head for x in r.tail), 'aaabaa' )
        r = g.parse('aaabaaba')
        self.assertEqual( ''.join(x.head for x in r.tail), 'aaabaaa' )

        self.assertRaises(ParseError, g.parse, 'aaabaa')

    def test_basic2(self):
        # Multiple parsers and colliding tokens
        g = Grammar("start: B A ; B: '12'; A: '1'; ", auto_filter_tokens=False)
        g2 = Grammar("start: B A; B: '12'; A: '2'; ", auto_filter_tokens=False)
        x = g.parse('121')
        assert x.head == 'start' and x.tail == ['12', '1'], x
        x = g2.parse('122')
        assert x.head == 'start' and x.tail == ['12', '2'], x

    def test_basic3(self):
        g = Grammar("start: '\(' name_list (COMMA MUL NAME)? '\)'; @name_list: NAME | name_list COMMA NAME ;  MUL: '\*'; COMMA: ','; NAME: '\w+'; ")
        l = g.parse('(a,b,c,*x)')

        g = Grammar("start: '\(' name_list (COMMA MUL NAME)? '\)'; @name_list: NAME | name_list COMMA NAME ;  MUL: '\*'; COMMA: ','; NAME: '\w+'; ")
        l2 = g.parse('(a,b,c,*x)')
        assert l == l2, '%s != %s' % (l, l2)

    @unittest.skipIf(cStringIO is None, "cStringIO not available")
    def test_stringio_bytes(self):
        """Verify that a Grammar can be created from file-like objects other than Python's standard 'file' object"""
        Grammar(cStringIO(b"start: a+ b a+? 'b' a*; b: 'b'; a: 'a';"))

    def test_stringio_unicode(self):
        """Verify that a Grammar can be created from file-like objects other than Python's standard 'file' object"""
        Grammar(uStringIO(u"start: a+ b a+? 'b' a*; b: 'b'; a: 'a';"))

    def test_unicode(self):
        g = Grammar(r"""start: UNIA UNIB UNIA;
                    UNIA: '\xa3';
                    UNIB: '\u0101';
                    """)
        g.parse(u'\xa3\u0101\u00a3')

    def test_recurse_expansion(self):
        """Verify that stack depth doesn't get exceeded on recursive rules marked for expansion."""
        g = Grammar(r"""@start: a | start a ; a : A ; A : 'a' ;""")

        # Force PLY to write to the debug log, but prevent writing it to the terminal (uses repr() on the half-built
        # STree data structures, which uses recursion).
        g._grammar.debug = yacc.NullLogger()

        g.parse("a" * (sys.getrecursionlimit() / 4))

    def test_expand1_lists_with_one_item(self):
        g = Grammar(r"""start: list ;
                        ?list: item+ ;
                        item : A ;
                        A: 'a' ;
                    """)
        r = g.parse("a")

        # because 'list' is an expand-if-contains-one rule and we only provided one element it should have expanded to 'item'
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('item',))

        # regardless of the amount of items: there should be only *one* child in 'start' because 'list' isn't an expand-all rule
        self.assertEqual(len(r.tail), 1)

    def test_expand1_lists_with_one_item_2(self):
        g = Grammar(r"""start: list ;
                        ?list: item+ '!';
                        item : A ;
                        A: 'a' ;
                    """)
        r = g.parse("a!")

        # because 'list' is an expand-if-contains-one rule and we only provided one element it should have expanded to 'item'
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('item',))

        # regardless of the amount of items: there should be only *one* child in 'start' because 'list' isn't an expand-all rule
        self.assertEqual(len(r.tail), 1)

    def test_dont_expand1_lists_with_multiple_items(self):
        g = Grammar(r"""start: list ;
                        ?list: item+ ;
                        item : A ;
                        A: 'a' ;
                    """)
        r = g.parse("aa")

        # because 'list' is an expand-if-contains-one rule and we've provided more than one element it should *not* have expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # regardless of the amount of items: there should be only *one* child in 'start' because 'list' isn't an expand-all rule
        self.assertEqual(len(r.tail), 1)

        # Sanity check: verify that 'list' contains the two 'item's we've given it
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ('item', 'item'))

    def test_dont_expand1_lists_with_multiple_items_2(self):
        g = Grammar(r"""start: list ;
                        ?list: item+ '!';
                        item : A ;
                        A: 'a' ;
                    """)
        r = g.parse("aa!")

        # because 'list' is an expand-if-contains-one rule and we've provided more than one element it should *not* have expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # regardless of the amount of items: there should be only *one* child in 'start' because 'list' isn't an expand-all rule
        self.assertEqual(len(r.tail), 1)

        # Sanity check: verify that 'list' contains the two 'item's we've given it
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ('item', 'item'))



    def test_empty_expand1_list(self):
        g = Grammar(r"""start: list ;
                        ?list: item* ;
                        item : A ;
                        A: 'a' ;
                     """)
        r = g.parse("")

        # because 'list' is an expand-if-contains-one rule and we've provided less than one element (i.e. none) it should *not* have expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # regardless of the amount of items: there should be only *one* child in 'start' because 'list' isn't an expand-all rule
        self.assertEqual(len(r.tail), 1)

        # Sanity check: verify that 'list' contains no 'item's as we've given it none
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ())

    def test_empty_expand1_list_2(self):
        g = Grammar(r"""start: list ;
                        ?list: item* '!'?;
                        item : A ;
                        A: 'a' ;
                     """)
        r = g.parse("")

        # because 'list' is an expand-if-contains-one rule and we've provided less than one element (i.e. none) it should *not* have expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # regardless of the amount of items: there should be only *one* child in 'start' because 'list' isn't an expand-all rule
        self.assertEqual(len(r.tail), 1)

        # Sanity check: verify that 'list' contains no 'item's as we've given it none
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ())


    def test_empty_flatten_list(self):
        g = Grammar(r"""start: list ;
                        #list: | item ',' list;
                        item : A ;
                        A: 'a' ;
                     """)
        r = g.parse("")

        # Because 'list' is a flatten rule it's top-level element should *never* be expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # Sanity check: verify that 'list' contains no 'item's as we've given it none
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ())

    def test_single_item_flatten_list(self):
        g = Grammar(r"""start: list ;
                        #list: | item ',' list ;
                        item : A ;
                        A: 'a' ;
                     """)
        r = g.parse("a,")

        # Because 'list' is a flatten rule it's top-level element should *never* be expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # Sanity check: verify that 'list' contains exactly the one 'item' we've given it
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ('item',))

    def test_multiple_item_flatten_list(self):
        g = Grammar(r"""start: list ;
                        #list: | item ',' list ;
                        item : A ;
                        A: 'a' ;
                     """)
        r = g.parse("a,a,")

        # Because 'list' is a flatten rule it's top-level element should *never* be expanded
        self.assertSequenceEqual([subtree.head for subtree in r.tail], ('list',))

        # Sanity check: verify that 'list' contains exactly the two 'item's we've given it
        [list] = r.tail
        self.assertSequenceEqual([item.head for item in list.tail], ('item', 'item'))

    def test_recurse_flatten(self):
        """Verify that stack depth doesn't get exceeded on recursive rules marked for flattening."""
        g = Grammar(r"""#start: a | start a ; a : A ; A : 'a' ;""")

        # Force PLY to write to the debug log, but prevent writing it to the terminal (uses repr() on the half-built
        # STree data structures, which uses recursion).
        g._grammar.debug = yacc.NullLogger()

        g.parse("a" * (sys.getrecursionlimit() / 4))

def test_python_lex(code=FIB, expected=54):
    g = Grammar(_read('python.g'))
    l = list(g.lex(code))
    for x in l:
        y = x.value
        if isinstance(y, TokValue):
            logging.debug('%s %s %s', y.type, y.line, y.column)
        else:
            logging.debug('%s %s', x.type, x.value)
    assert len(l) == expected, len(l)

def test_python_lex2():
    test_python_lex(code="""
def add_token():
    a
# hello

# hello
    setattr(self, b)

        """, expected=26)

def test_python_lex3():
    test_python_lex("""
def test2():
    sexp = ['start',
             ]
        """, expected=18)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_selectors
from __future__ import absolute_import

import unittest
import logging
from plyplus.plyplus import Grammar, STree
from plyplus.selector import selector

logging.basicConfig(level=logging.INFO)

class TestSelectors(unittest.TestCase):
    def setUp(self):
        tree_grammar = Grammar("start: branch; branch: name ('{' branch* '}')?; name: '[a-z]';")

        self.tree1 = tree_grammar.parse('a{b{cde}}')
        self.tree2 = tree_grammar.parse('a{abc{bbab}c}')

    def test_elem_head(self):
        assert len( selector('name').match(self.tree1) ) == 5
        assert len( selector('branch').match(self.tree1) ) == 5
        assert len( selector('name').match(self.tree2) ) == 9
        assert len( selector('branch').match(self.tree2) ) == 9

    def test_elem_regexp(self):
        assert len( selector('/[a-c]$/').match(self.tree1) ) == 3
        assert len( selector('/[b-z]$/').match(self.tree2) ) == len('bcbbbc')

    def test_elem_any(self):
        assert len( selector('*').match(self.tree1) ) == 16
        assert len( selector('*').match(self.tree2) ) == 28


    def test_modifiers(self):
        assert len( selector('*:is-leaf').match(self.tree1) ) == 5
        assert len( selector('/[a-c]/:is-leaf').match(self.tree1) ) == 3

        assert len( selector('/[b]/:is-parent').match(self.tree1) ) == 5
        assert len( selector('/[b]/:is-parent').match(self.tree2) ) == 9

        assert len( selector('*:is-root').match(self.tree1) ) == 1, selector('*:is-root').match(self.tree1)
        assert len( selector('*:is-root').match(self.tree2) ) == 1
        assert len( selector('a:is-root + b').match(self.tree2) ) == 0
        assert len( selector('branch:is-root > branch').match(self.tree1.tail[0]) ) == 1
        assert len( selector('start:is-root > branch').match(self.tree2) ) == 1

        # TODO: More modifiers!

    def test_operators(self):
        tree1, tree2 = self.tree1, self.tree2
        assert len( selector('name /b/').match(tree2) ) == 4
        assert len( selector('name>/b/').match(tree2) ) == 4
        assert len( selector('branch>branch>name').match(tree1) ) == 4
        assert len( selector('branch>branch>branch>name').match(tree1) ) == 3
        assert len( selector('branch branch branch name').match(tree1) ) == 3
        assert len( selector('branch branch branch').match(tree1) ) == 3

        assert len( selector('branch+branch').match(tree1) ) == 2
        assert len( selector('branch~branch~branch').match(tree1) ) == 1
        assert len( selector('branch~branch~branch~branch').match(tree1) ) == 0

        assert len( selector('branch:is-parent + branch branch > name > /a/:is-leaf').match(tree2) ) == 1   # test all at once; only innermost 'a' matches

    def test_lists_repeated_use(self):
        assert self.tree1.select('name') == self.tree1.select('(name)')
        assert self.tree1.select('branch') == self.tree1.select('(branch)')
        assert self.tree2.select('name') == self.tree2.select('(name)')
        assert self.tree2.select('branch') == self.tree2.select('(branch)')

    def test_lists(self):
        tree1, tree2 = self.tree1, self.tree2
        assert set( selector('(/a/)').match(tree1) ) == set('a')
        assert set( selector('(/a/,/b$/)').match(tree1) ) == set('ab')
        assert set( selector('(/e/, (/a/,/b$/), /c/)').match(tree1) ) == set('abce')

    def test_lists2(self):
        tree1, tree2 = self.tree1, self.tree2
        assert set( tree1.select('(branch /d/)') ) == set('d')
        assert tree1.select1('=(=branch /d/) + (=branch /e/)').tail[0].tail[0] == 'd'
        assert len( self.tree2.select('(=branch>name>/c/) branch /b/') )

    def test_yield(self):
        tree1, tree2 = self.tree1, self.tree2
        assert list( selector('=name /a/').match(tree1) )[0].head == 'name'
        assert len( selector('=branch /c/').match(tree1) ) == 3
        assert set( selector('(=name /a/,name /b$/)').match(tree1) ) == set([STree('name', ['a']), 'b'])
        assert set( selector('=branch branch branch').match(tree1) ) == set([tree1.tail[0]])
        assert set( selector('=(name,=branch branch branch) /c/').match(tree1) ) == set([STree('name', ['c']), tree1.tail[0]])

    def test_collection(self):
        tree1, tree2 = self.tree1, self.tree2
        assert tree1.select('name') == tree1.select('name').select('=name').select('(name)').select('=(name)').select('=(=name)')
        assert tree1.select('name').select('/a|b/') == list(u'ab')
        assert tree1.select('name').select('name /a|b/') == list(u'ab')
        assert len( tree2.select('=branch>name>/a/').select('/^b$/') ) == 4

    def test_tree_param(self):
        tree1, tree2 = self.tree1, self.tree2
        name_ast = STree('name', ['a'])

        # Sanity test
        assert name_ast.select('{name}', name=name_ast) == [name_ast]

        # Test that all params are required
        with self.assertRaises(KeyError):
            name_ast.select('{name}')

        # Make sure it plays nicely with values and arguments that don't exist
        assert not name_ast.select('{name}', name='A', another='B')

        # Test select1, and more "advanced" features with a param
        assert tree1.select1('=branch =(={name})', name=name_ast) == (tree1.tail[0], name_ast)

    def test_regexp_param(self):
        tree1, tree2 = self.tree1, self.tree2

        # Sanity test
        assert tree1.select('/{value}/', value='a') == ['a']

        # Test combination with other regexp element
        assert tree1.select('/^{value}/', value='a') == ['a']

        # Test regexp encoding, selector re-use
        assert not tree1.select('/{value}/', value='^a')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_trees
from __future__ import absolute_import

import unittest
import logging
import copy
import pickle

from plyplus.plyplus import STree

logging.basicConfig(level=logging.INFO)

class TestSTrees(unittest.TestCase):
    def setUp(self):
        self.tree1 = STree('a', [STree(x, y) for x, y in zip('bcd', 'xyz')])

    def test_deepcopy(self):
        assert self.tree1 == copy.deepcopy(self.tree1)

    def test_parents(self):
        s = copy.deepcopy(self.tree1)
        s.calc_parents()
        for i, x in enumerate(s.tail):
            assert x.parent() == s
            assert x.index_in_parent == i

    def test_pickle(self):
        s = copy.deepcopy(self.tree1)
        data = pickle.dumps(s)
        assert pickle.loads(data) == s

    def test_pickle_with_parents(self):
        s = copy.deepcopy(self.tree1)
        s.calc_parents()
        data = pickle.dumps(s)
        s2 = pickle.loads(data)
        assert s2 == s

        for i, x in enumerate(s2.tail):
            assert x.parent() == s2
            assert x.index_in_parent == i

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = __main__
from __future__ import absolute_import, print_function

import unittest
import logging

from .test_trees import TestSTrees
from .test_selectors import TestSelectors
from .test_parser import TestPlyPlus
from .test_grammars import TestPythonG, TestConfigG

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import functools

try:
    # Python 2.6
    from types import StringTypes
except ImportError:
    # Python 3.0
    StringTypes = (str,)


StringType = type(u'')

def classify(seq, key=lambda x:x):
    d = {}
    for item in seq:
        k = key(item)
        if k not in d:
            d[k] = [ ]
        d[k].append( item )

    return d

def _cache_0args(obj):
    @functools.wraps(obj)
    def memoizer(self):
        _cache = self._cache
        _id = id(obj)
        if _id not in _cache:
            self._cache[_id] = obj(self)
        return _cache[_id]
    return memoizer

class DefaultDictX(dict):
    def __init__(self, default_factory):
        self.__default_factory = default_factory
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            self[key] = value = self.__default_factory(key)
            return value

########NEW FILE########
