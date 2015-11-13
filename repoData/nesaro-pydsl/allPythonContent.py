__FILENAME__ = Alphabet
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

from pydsl.Grammar.Definition import Grammar
import logging
LOG=logging.getLogger(__name__)

class Alphabet(object):
    """Defines a set of valid elements"""
    @property
    def minsize(self):
        return 1 #FIXME: In some cases could be 0

    @property
    def maxsize(self):
        return 1

class GrammarCollection(Alphabet, tuple):
    """Uses a list of grammar definitions"""
    def __init__(self, grammarlist):
        Alphabet.__init__(self)
        tuple.__init__(self, grammarlist)
        for x in self:
            if not isinstance(x, Grammar):
                raise TypeError("Expected Grammar, Got %s:%s" % (x.__class__.__name__,x))

    def __str__(self):
        return str([str(x) for x in self])

    def __add__(self, other):
        return GrammarCollection(tuple.__add__(self,other))

class Encoding(Alphabet):
    """Defines an alphabet using an encoding string"""
    def __init__(self, encoding):
        Alphabet.__init__(self)
        self.encoding = encoding

    def __hash__(self):
        return hash(self.encoding)

    def __eq__(self, other):
        try:
            return self.encoding == other.encoding
        except AttributeError:
            return False

    def __getitem__(self, item):
        from pydsl.Grammar import String
        try:
            return String(chr(item))
        except (ValueError, TypeError):
            raise KeyError

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True

    def __str__(self):
        return self.encoding

    def enum(self):
        if self.encoding == "ascii":
            limit = 128
        elif self.encoding == "unicode":
            limit = 9635
        from pydsl.Grammar import String
        return [String(chr(x)) for x in range(limit)]

########NEW FILE########
__FILENAME__ = Check
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
from collections import Iterable
LOG = logging.getLogger(__name__)


def check(definition, data):
    checker = checker_factory(definition)
    return checker(data)

def checker_factory(grammar):
    from pydsl.Grammar.BNF import BNFGrammar
    from pydsl.Grammar.PEG import Sequence, Choice, OneOrMore, ZeroOrMore
    from pydsl.Grammar.Definition import PLYGrammar, RegularExpression, String, PythonGrammar
    from pydsl.Alphabet import Encoding
    from pydsl.Grammar.Parsley import ParsleyGrammar
    from collections import Iterable
    if isinstance(grammar, BNFGrammar):
        return BNFChecker(grammar)
    elif isinstance(grammar, RegularExpression):
        return RegularExpressionChecker(grammar)
    elif isinstance(grammar, PythonGrammar) or isinstance(grammar, dict) and "matchFun" in grammar:
        return PythonChecker(grammar)
    elif isinstance(grammar, PLYGrammar):
        return PLYChecker(grammar)
    elif isinstance(grammar, Choice):
        return ChoiceChecker(grammar)
    elif isinstance(grammar, ParsleyGrammar):
        return ParsleyChecker(grammar)
    elif isinstance(grammar, String):
        return StringChecker(grammar)
    elif isinstance(grammar, Encoding):
        return EncodingChecker(grammar)
    elif isinstance(grammar, Sequence):
        return SequenceChecker(grammar)
    elif isinstance(grammar, OneOrMore):
        return OneOrMoreChecker(grammar)
    elif isinstance(grammar, ZeroOrMore):
        return ZeroOrMoreChecker(grammar)
    elif isinstance(grammar, Iterable):
        return ChoiceChecker(grammar)
    else:
        raise ValueError(grammar)


class Checker(object):
    """ Ensures that input follows a rule, protocol, grammar alphabet..."""
    def __init__(self):
        pass

    def __call__(self, value):
        return self.check(value)

    def check(self, value):# -> bool:
        raise NotImplementedError

class RegularExpressionChecker(Checker):
    def __init__(self, regexp, flags = ""):
        Checker.__init__(self)
        import re
        self.__regexpstr = regexp
        myflags = 0
        if "i" in flags:
            myflags |= re.I
        if isinstance(regexp, str):
            self.__regexp = re.compile(regexp, myflags)
        else:
            self.__regexp = regexp

    def check(self, data):
        """returns True if any match any regexp"""
        if isinstance(data, Iterable):
            data = "".join([str(x) for x in data])
        try:
            data = str(data)
        except UnicodeDecodeError:
            return False
        if not data:
            return False
        return bool(self.__regexp.match(data))


class BNFChecker(Checker):
    """Calls another program to perform checking. Args are always file names"""
    def __init__(self, bnf, parser = None):
        Checker.__init__(self)
        self.gd = bnf
        parser = bnf.options.get("parser",parser)
        if parser in ("descent", "auto", "default", None):
            from pydsl.Parser.Backtracing import BacktracingErrorRecursiveDescentParser
            self.__parser = BacktracingErrorRecursiveDescentParser(bnf)
        else:
            raise ValueError("Unknown parser : " + parser)

    def check(self, data):
        for element in data:
            if not check(self.gd.alphabet, element):
                LOG.warning("Invalid input: %s,%s" % (self.gd.alphabet, element))
                return False
        try:
            return len(self.__parser.get_trees(data)) > 0
        except IndexError:
            return False 

class ParsleyChecker(Checker):
    def __init__(self, grammar):
        Checker.__init__(self)
        self.g=grammar
    def check(self, data):
        from parsley import ParseError
        try:
            self.g.match(data)
            return True
        except ParseError:
            return False


class PythonChecker(Checker):
    def __init__(self, module):
        Checker.__init__(self)
        self._matchFun = module["matchFun"]

    def check(self, data):
        try:
            return self._matchFun(data)
        except UnicodeDecodeError:
            return False


class PLYChecker(Checker):
    def __init__(self, gd):
        Checker.__init__(self)
        self.module = gd.module

    def check(self, data):
        if isinstance(data, Iterable):
            data = "".join([str(x) for x in data])
        from ply import yacc, lex
        lexer = lex.lex(self.module)
        parser = yacc.yacc(module = self.module)
        from pydsl.Exceptions import ParseError
        try:
            parser.parse(data, lexer = lexer)
        except ParseError:
            return False
        return True

class StringChecker(Checker):
    def __init__(self, gd):
        Checker.__init__(self)
        self.gd = gd

    def check(self, data):
        if isinstance(data, Iterable):
            data = "".join([str(x) for x in data])
        return self.gd == str(data)

class JsonSchemaChecker(Checker):
    def __init__(self, gd):
        Checker.__init__(self)
        self.gd = gd

    def check(self, data):
        from jsonschema import validate, ValidationError
        try:
            validate(data, self.gd)
        except ValidationError:
            return False
        return True

class ChoiceChecker(Checker):
    def __init__(self, gd):
        Checker.__init__(self)
        self.gd = gd
        self.checkerinstances = [checker_factory(x) for x in self.gd]

    def check(self, data):
        return any((x.check(data) for x in self.checkerinstances))

class EncodingChecker(Checker):
    def __init__(self, gd):
        Checker.__init__(self)
        self.gd = gd

    def check(self,data):
        encoding = self.gd.encoding
        if isinstance(data, Iterable):
            data = "".join([str(x) for x in data])
        if isinstance(data, str):
            try:
                data.encode(encoding)
            except UnicodeEncodeError:
                return False
            return True
        if isinstance(data, bytes):
            try:
                data.decode(encoding)
            except UnicodeDecodeError:
                return False
            return True
        return False

class SequenceChecker(Checker):
    def __init__(self, sequence):
        Checker.__init__(self)
        self.sequence = sequence

    def check(self,data):
        if len(self.sequence) != len(data):
            return False
        for index in range(len(self.sequence)):
            if not check(self.sequence[index], data[index]):
                return False
        return True


class OneOrMoreChecker(Checker):
    def __init__(self, element):
        Checker.__init__(self)
        self.element = element

    def check(self, data):
        if not data:
            return False
        for element in data:
            if not check(self.element.element, element):
                return False
        return True

class ZeroOrMoreChecker(Checker):
    def __init__(self, element):
        Checker.__init__(self)
        self.element = element

    def check(self, data):
        if not data:
            return True
        for element in data:
            if not check(self.element.element, element):
                return False
        return True

########NEW FILE########
__FILENAME__ = test_alphabet
grammarlist = ["integer","Date"]
iclass = "AlphabetList"

########NEW FILE########
__FILENAME__ = bnfgrammar
"""BNF grammars for testing"""

from pydsl.Grammar.Symbol import TerminalSymbol, NonTerminalSymbol, NullSymbol
from pydsl.Grammar.BNF import Production, BNFGrammar
from pydsl.File.BNF import strlist_to_production_set
from pydsl.File.Python import load_python_file
from pydsl.Grammar.Definition import String, RegularExpression

br = "max"
leftrecursive=["S ::= E","E ::= E dot | dot","dot := String,."]
rightrecursive=["S ::= E","E ::= dot E | dot","dot := String,."]
centerrecursive=["S ::= E","E ::= dot E dot | dot","dot := String,."]

#productionset0 definition

symbol1 = TerminalSymbol(String("S"))
symbol2 = TerminalSymbol(String("R"))
final1 = NonTerminalSymbol("exp")
rule1 = Production([final1], (symbol1, symbol2))
productionset0 = BNFGrammar(final1, (rule1,symbol1,symbol2))
p0good = "SR"
p0bad = "RS"


#productionset1 definition
symbol1 = TerminalSymbol(String("S"))
symbol2 = TerminalSymbol(String("R"))
symbol3 = TerminalSymbol(String(":"))
symbol4 = TerminalSymbol(RegularExpression("^[0123456789]*$"), None, br)
symbol5 = TerminalSymbol(load_python_file('pydsl/contrib/grammar/cstring.py'), None, br)
final1 = NonTerminalSymbol("storeexp") 
final2 = NonTerminalSymbol("retrieveexp") 
final3 = NonTerminalSymbol("exp")
rule1 = Production([final1], (symbol1, symbol3, symbol5))
rule2 = Production([final2], (symbol2, symbol3, symbol4))
rule3 = Production([final3], [final1])
rule4 = Production([final3], [final2])
rulelist = (rule1, rule2, rule3, rule4, symbol1, symbol2, symbol3, symbol4, symbol5)
productionset1 = BNFGrammar(final3, rulelist)

#productionset2 definition
symbola = TerminalSymbol(String("A"))
symbolb = TerminalSymbol(String("B"))
nonterminal = NonTerminalSymbol("res")
rulea = Production ((nonterminal,), (symbola, NullSymbol(), symbolb))
productionset2 = BNFGrammar(nonterminal, (rulea, symbola, symbolb))
productionsetlr = strlist_to_production_set(leftrecursive)
productionsetrr = strlist_to_production_set(rightrecursive)
productionsetcr = strlist_to_production_set(centerrecursive)

#arithmetic


arithmetic=["E ::= E plus T | T", "T ::= T times F | F" ,"F ::= open_parenthesis E close_parenthesis | id", "id := String,123" , "plus := String,+", "times := String,*", "open_parenthesis := String,(","close_parenthesis := String,)"]
productionset_arithmetic = strlist_to_production_set(arithmetic, start_symbol= "E")

addition=["S ::= E","E ::= E plus F | F" ,"F ::= open_parenthesis E close_parenthesis | id", "id := String,123" , "plus := String,+", "open_parenthesis := String,(","close_parenthesis := String,)"]
productionset_addition = strlist_to_production_set(addition)
#tokenlist definition
string1 = "S:a"
string2 = "S:"
string3 = "AB"
string4 = "AAB"
string5 = "ACB"
dots = "....."

########NEW FILE########
__FILENAME__ = calculator
from pydsl.File.BNF import strlist_to_production_set
from pydsl.Grammar import RegularExpression
from pydsl.Parser.LL import LL1RecursiveDescentParser

def tree_translator(tree):
    from pydsl.Grammar.Symbol import NonTerminalSymbol
    if tree.symbol == NonTerminalSymbol("E"):
        return int(str(tree.childlist[0].content)) + int(str(tree.childlist[2].content))
    elif len(tree.childlist) == 1:
        return tree_translator(tree.childlist[0])
    else:
        raise Exception
            

grammar_def = [
        "S ::= E",
        "E ::= number operator number",
        "number := Word,integer,max",
        "operator := String,+",
        ]
repository = {'integer':RegularExpression("^[0123456789]*$")}
production_set = strlist_to_production_set(grammar_def, repository)
rdp = LL1RecursiveDescentParser(production_set)


def translator(data):
    parse_tree = rdp(data)
    return tree_translator(parse_tree[0])


########NEW FILE########
__FILENAME__ = calc_ply
# -----------------------------------------------------------------------------
# calc.py
#
# A simple calculator with variables -- all in one file.
# -----------------------------------------------------------------------------

from pydsl.Exceptions import ParseError

tokens = (
    'NAME','NUMBER',
    'PLUS','MINUS','TIMES','DIVIDE','EQUALS',
    'LPAREN','RPAREN',
    )

# Tokens

t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_EQUALS  = r'='
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_NAME    = r'[a-zA-Z_][a-zA-Z0-9_]*'

def t_NUMBER(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        print("Integer value too large %d", t.value)
        t.value = 0
    return t

# Ignored characters
t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    raise ParseError("unknown character", t.lexpos)
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Parsing rules

precedence = (
    ('left','PLUS','MINUS'),
    ('left','TIMES','DIVIDE'),
    ('right','UMINUS'),
    )

# dictionary of names
names = { }

def p_statement_assign(t):
    'statement : NAME EQUALS expression'
    names[t[1]] = t[3]

def p_statement_expr(t):
    'statement : expression'
    t[0] = t[1]

def p_expression_binop(t):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression'''
    if t[2] == '+'  : t[0] = t[1] + t[3]
    elif t[2] == '-': t[0] = t[1] - t[3]
    elif t[2] == '*': t[0] = t[1] * t[3]
    elif t[2] == '/': t[0] = t[1] / t[3]

def p_expression_uminus(t):
    'expression : MINUS expression %prec UMINUS'
    t[0] = -t[2]

def p_expression_group(t):
    'expression : LPAREN expression RPAREN'
    t[0] = t[2]

def p_expression_number(t):
    'expression : NUMBER'
    t[0] = t[1]

def p_expression_name(t):
    'expression : NAME'
    try:
        t[0] = names[t[1]]
    except LookupError:
        raise ParseError("Undefined name",0)
        t[0] = 0

def p_error(t):
    raise ParseError("Syntax error at", t.value)

iclass="PLY"

########NEW FILE########
__FILENAME__ = cstring
#!/usr/bin/python
# -*- coding: utf-8 -*-

#Copyright (C) 2008-2013 Nestor Arocha

"""Any string """

iclass="PythonGrammar"
def matchFun(inputstr):
    try:
        str(inputstr)
    except UnicodeDecodeError:
        return False
    return True


########NEW FILE########
__FILENAME__ = DayOfMonth
#!/usr/bin/python
# -*- coding: utf-8 -*-

#Copyright (C) 2008-2014 Nestor Arocha



def matchFun(myinput):
    from collections import Iterable
    if isinstance(myinput, Iterable):
        myinput = "".join([str(x) for x in myinput])
    strnumber = str(myinput)
    try:
        number = int(strnumber)
    except ValueError:
        return False
    if 0 < number < 32:
        return True
    return False

iclass = "PythonGrammar"

########NEW FILE########
__FILENAME__ = example_ply
#!/usr/bin/python3

"""Calculate the molecular weight given a molecular formula

Parse the formula using PLY.

See http://www.dalkescientific.com/writings/NBN/parsing_with_ply.html
"""
# ply_mw.py

from ply.lex import TOKEN
from pydsl.Exceptions import ParseError


### Define the lexer

tokens = (
    "ATOM",
    "DIGITS",
)

mw_table = {
    'H': 1.00794,
    'C': 12.001,
    'Cl': 35.453,
    'O': 15.999,
    'S': 32.06,
}


# I don't want to duplicate the atom names so extract the
# keys to make the lexer pattern.

# Sort order is:
#   - alphabetically on first character, to make it easier
# for a human to look at and debug any problems
# 
#   - then by the length of the symbol; two letters before 1
# Needed because Python's regular expression matcher
# uses "first match" not "longest match" rules.
# For example, "C|Cl" matches only the "C" in "Cl"
# The "-" in "-len(symbol)" is a trick to reverse the sort order.
#
#   - then by the full symbol, to make it easier for people

# (This is more complicated than needed; it's to show how
# this approach can scale to all 100+ known and named elements)

atom_names = sorted(
    mw_table.keys(),
    key = lambda symbol: (symbol[0], -len(symbol), symbol))

# Creates a pattern like:  Cl|C|H|O|S
atom_pattern = "|".join(atom_names)

# Use a relatively new PLY feature to set the __doc__
# string based on a Python variable.
@TOKEN(atom_pattern)
def t_ATOM(t):
    t.value = mw_table[t.value]
    return t

def t_DIGITS(t):
    r"\d+"
    t.value = int(t.value)
    return t

def t_error(t):
    raise ParseError("unknown character", t.lexpos)


## Here's an example of using the lexer

# data = "H2SO4"
# 
# lex.input(data)
# 
# for tok in iter(lex.token, None):
#     print tok

##### Define the grammar

# The molecular weight of "" is 0.0
def p_mw_empty(p):
    "mw : "
    p[0] = 0.0

def p_mw_formula(p):
    "mw : formula"
    p[0] = p[1]
    

def p_first_species_term(p):
    "formula : species"
    p[0] = p[1]

def p_species_list(p):
    "formula : formula species"
    p[0] = p[1] + p[2]

def p_species(p):
    "species : ATOM DIGITS"
    p[0] = p[1] * p[2]

def p_species_default(p):
    "species : ATOM"
    p[0] = p[1]

def p_error(p):
    raise ParseError("unexpected character", p.lexpos)

iclass="PLY"

########NEW FILE########
__FILENAME__ = Grammar2RecursiveDescentParserRecognizer
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Grammar 2 Recursive Descent Parser Recognizer
First recipe of the book "Language implementation patterns

grammar NestedNameList;
list : '[' elements ']' ; // match bracketed list
elements : element (',' element)* ; // match comma-separated list
element : NAME | list ; // element is name or nested list
NAME : ('a'..'z' |'A'..'Z' )+ ; // NAME is sequence of >=1 letter
"""


def matchFun(inputstr):
    def look_ahead(tl):
        if tl[0] == "[":
            return "list"
        elif tl[0] == ",":
            return ","

    def mlist(tl):
        if tl.pop(0) != "[":
            return False
        if not elements(tl):
            return False
        if tl.pop(0) != "]":
            return False
        return True

    def elements(tl):
        if not element(tl):
            return False
        while look_ahead(tl) == ",":
            tl.pop(0)
            if not element(tl):
                return False
        return True

    def element(tl):
        if look_ahead(tl) == "list":
            if not mlist(tl):
                return False
        else:
            if not name(tl):
                return False
        return True

    def name(tl):
        import re
        if not re.match("[a-zA-Z]", tl.pop(0)):
            return False
        while tl and re.match("[a-zA-Z]", tl[0]):
            tl.pop(0)
        return True

    inputlist = [x for x in inputstr]
    return element(inputlist) and not len(inputlist)


iclass = "PythonGrammar"

########NEW FILE########
__FILENAME__ = ImageFile
#!/usr/bin/python
# -*- coding: utf-8 -*-

#copyright (c) 2008-2013 Nestor Arocha

"""Image file recognizer"""

def matchFun(input):
    content = input #assuming bytes
    import imghdr
    try:
        return bool(imghdr.what(None, content))
    except:
        return False


iclass = "PythonGrammar"

########NEW FILE########
__FILENAME__ = integerop
#!/usr/bin/python
# -*- coding: utf-8 -*-

#Copyright (C) 2008-2013 Nestor Arocha


def propFun(input, property):
    if property == "Operator":
        return input[1]

def matchFun(myinput, auxgrammardict):
    myinput = str(myinput)
    validoperators = ["+", "-", "*", "/"]
    operatorexists = False
    currentoperator = None
    for operator in validoperators:
        if operator in myinput:
            operatorexists = True
            currentoperator = operator
            break
    if not operatorexists:
        return False
    parts = myinput.split(currentoperator)
    if len(parts) != 2:
        return False
    for part in parts:
        if not auxgrammardict["integer"].check(part):
            return False
    return True

auxdic = {"integer":"integer"}
iclass = "PythonGrammar"

########NEW FILE########
__FILENAME__ = MimeType
#!/usr/bin/python
# -*- coding: utf-8 -*-

#copyright (c) 2008-2013 Nestor Arocha

"""Mime Type recognizer"""

_mimelist = ["applicaiton/x-bytecode.python",
"application/acad",
"application/arj",
"application/base64",
"application/binhex",
"application/binhex4",
"application/book",
"application/cdf",
"application/clariscad",
"application/commonground",
"application/drafting",
"application/dsptype",
"application/dxf",
"application/envoy",
"application/excel",
"application/fractals",
"application/freeloader",
"application/futuresplash",
"application/gnutar",
"application/groupwise",
"application/hlp",
"application/hta",
"application/i-deas",
"application/iges",
"application/inf",
"application/java",
"application/java-byte-code",
"application/lha",
"application/lzx",
"application/mac-binary",
"application/macbinary",
"application/mac-binhex",
"application/mac-binhex40",
"application/mac-compactpro",
"application/marc",
"application/mbedlet",
"application/mcad",
"application/mime",
"application/mspowerpoint",
"application/msword",
"application/mswrite",
"application/netmc",
"application/octet-stream",
"application/oda",
"application/pdf",
"application/pkcs10",
"application/pkcs-12",
"application/pkcs7-mime",
"application/pkcs7-signature",
"application/pkcs-crl",
"application/pkix-cert",
"application/pkix-crl",
"application/plain",
"application/postscript",
"application/powerpoint",
"application/pro_eng",
"application/ringing-tones",
"application/rtf",
"application/sdp",
"application/sea",
"application/set",
"application/sla",
"application/smil",
"application/solids",
"application/sounder",
"application/step",
"application/streamingmedia",
"application/toolbook",
"application/vda",
"application/vnd.fdf",
"application/vnd.hp-hpgl",
"application/vnd.hp-pcl",
"application/vnd.ms-excel",
"application/vnd.ms-pki.certstore",
"application/vnd.ms-pki.pko",
"application/vnd.ms-pki.seccat",
"application/vnd.ms-pki.stl",
"application/vnd.ms-powerpoint",
"application/vnd.ms-project",
"application/vnd.nokia.configuration-message",
"application/vnd.nokia.ringing-tone",
"application/vnd.rn-realmedia",
"application/vnd.rn-realplayer",
"application/vnd.wap.wmlc",
"application/vnd.wap.wmlscriptc",
"application/vnd.xara",
"application/vocaltec-media-desc",
"application/vocaltec-media-file",
"application/wordperfect",
"application/wordperfect6.0",
"application/wordperfect6.1",
"application/x-123",
"application/x-aim",
"application/x-authorware-bin",
"application/x-authorware-map",
"application/x-authorware-seg",
"application/x-bcpio",
"application/x-binary",
"application/x-binhex40",
"application/x-bsh",
"application/x-bytecode.elisp (compiled elisp)",
"application/x-bzip",
"application/x-bzip2",
"application/x-cdf",
"application/x-cdlink",
"application/x-chat",
"application/x-cmu-raster",
"application/x-cocoa",
"application/x-compactpro",
"application/x-compress",
"application/x-compressed",
"application/x-conference",
"application/x-cpio",
"application/x-cpt",
"application/x-csh",
"application/x-deepv",
"application/x-director",
"application/x-dvi",
"application/x-elc",
"application/x-envoy",
"application/x-esrehber",
"application/x-excel",
"application/x-frame",
"application/x-freelance",
"application/x-gsp",
"application/x-gss",
"application/x-gtar",
"application/x-gzip",
"application/x-hdf",
"application/x-helpfile",
"application/x-httpd-imap",
"application/x-ima",
"application/x-internett-signup",
"application/x-inventor",
"application/x-ip2",
"application/x-java-class",
"application/x-java-commerce",
"application/x-javascript",
"application/x-koan",
"application/x-ksh",
"application/x-latex",
"application/x-lha",
"application/x-lisp",
"application/x-livescreen",
"application/x-lotus",
"application/x-lotusscreencam",
"application/x-lzh",
"application/x-lzx",
"application/x-macbinary",
"application/x-mac-binhex40",
"application/x-magic-cap-package-1.0",
"application/x-mathcad",
"application/x-meme",
"application/x-midi",
"application/x-mif",
"application/x-mix-transfer",
"application/xml",
"application/x-mplayer2",
"application/x-msexcel",
"application/x-mspowerpoint",
"application/x-navi-animation",
"application/x-navidoc",
"application/x-navimap",
"application/x-navistyle",
"application/x-netcdf",
"application/x-newton-compatible-pkg",
"application/x-nokia-9000-communicator-add-on-software",
"application/x-omc",
"application/x-omcdatamaker",
"application/x-omcregerator",
"application/x-pagemaker",
"application/x-pcl",
"application/x-pixclscript",
"application/x-pkcs10",
"application/x-pkcs12",
"application/x-pkcs7-certificates",
"application/x-pkcs7-certreqresp",
"application/x-pkcs7-mime",
"application/x-pkcs7-signature",
"application/x-pointplus",
"application/x-portable-anymap",
"application/x-project",
"application/x-qpro",
"application/x-rtf",
"application/x-sdp",
"application/x-sea",
"application/x-seelogo",
"application/x-sh",
"application/x-shar",
"application/x-shockwave-flash",
"application/x-sit",
"application/x-sprite",
"application/x-stuffit",
"application/x-sv4cpio",
"application/x-sv4crc",
"application/x-tar",
"application/x-tbook",
"application/x-tcl",
"application/x-tex",
"application/x-texinfo",
"application/x-troff",
"application/x-troff-man",
"application/x-troff-me",
"application/x-troff-ms",
"application/x-troff-msvideo",
"application/x-ustar",
"application/x-visio",
"application/x-vnd.audioexplosion.mzz",
"application/x-vnd.ls-xpix",
"application/x-vrml",
"application/x-wais-source",
"application/x-winhelp",
"application/x-wintalk",
"application/x-world",
"application/x-wpwin",
"application/x-wri",
"application/x-x509-ca-cert",
"application/x-x509-user-cert",
"application/x-zip-compressed",
"application/zip",
"audio/aiff",
"audio/basic",
"audio/it",
"audio/make",
"audio/make.my.funk",
"audio/mid",
"audio/midi",
"audio/mod",
"audio/mpeg",
"audio/mpeg3",
"audio/nspaudio",
"audio/s3m",
"audio/tsp-audio",
"audio/tsplayer",
"audio/vnd.qcelp",
"audio/voc",
"audio/voxware",
"audio/wav",
"audio/x-adpcm",
"audio/x-aiff",
"audio/x-au",
"audio/x-gsm",
"audio/x-jam",
"audio/x-liveaudio",
"audio/xm",
"audio/x-mid",
"audio/x-midi",
"audio/x-mod",
"audio/x-mpeg",
"audio/x-mpeg-3",
"audio/x-mpequrl",
"audio/x-nspaudio",
"audio/x-pn-realaudio",
"audio/x-pn-realaudio-plugin",
"audio/x-psid",
"audio/x-realaudio",
"audio/x-twinvq",
"audio/x-twinvq-plugin",
"audio/x-vnd.audioexplosion.mjuicemediafile",
"audio/x-voc",
"audio/x-wav",
"chemical/x-pdb",
"drawing/x-dwf (old)",
"image/bmp",
"image/cmu-raster",
"image/fif",
"image/florian",
"image/g3fax",
"image/gif",
"image/ief",
"image/jpeg",
"image/jutvision",
"image/naplps",
"image/pict",
"image/pjpeg",
"image/png",
"image/tiff",
"image/vasa",
"image/vnd.dwg",
"image/vnd.fpx",
"image/vnd.net-fpx",
"image/vnd.rn-realflash",
"image/vnd.rn-realpix",
"image/vnd.wap.wbmp",
"image/vnd.xiff",
"image/xbm",
"image/x-cmu-raster",
"image/x-dwg",
"image/x-icon",
"image/x-jg",
"image/x-jps",
"image/x-niff",
"image/x-pcx",
"image/x-pict",
"image/xpm",
"image/x-portable-anymap",
"image/x-portable-bitmap",
"image/x-portable-graymap",
"image/x-portable-greymap",
"image/x-portable-pixmap",
"image/x-quicktime",
"image/x-rgb",
"image/x-tiff",
"image/x-windows-bmp",
"image/x-xbitmap",
"image/x-xbm",
"image/x-xpixmap",
"image/x-xwd",
"image/x-xwindowdump",
"i-world/i-vrml",
"message/rfc822",
"model/iges",
"model/vnd.dwf",
"model/vrml",
"model/x-pov",
"multipart/x-gzip",
"multipart/x-ustar",
"multipart/x-zip",
"music/crescendo",
"music/x-karaoke",
"paleovu/x-pv",
"text/asp",
"text/css",
"text/html",
"text/mcf",
"text/pascal",
"text/plain",
"text/richtext",
"text/scriplet",
"text/sgml",
"text/tab-separated-values",
"text/uri-list",
"text/vnd.abc",
"text/vnd.fmi.flexstor",
"text/vnd.rn-realtext",
"text/vnd.wap.wml",
"text/vnd.wap.wmlscript",
"text/webviewhtml",
"text/x-asm",
"text/x-audiosoft-intra",
"text/x-c",
"text/x-component",
"text/x-fortran",
"text/x-h",
"text/x-java-source",
"text/x-la-asf",
"text/x-m",
"text/xml",
"text/x-pascal",
"text/x-script",
"text/x-script.csh",
"text/x-script.elisp",
"text/x-script.guile",
"text/x-script.ksh",
"text/x-script.lisp",
"text/x-script.perl",
"text/x-script.perl-module",
"text/x-script.phyton",
"text/x-script.rexx",
"text/x-script.scheme",
"text/x-script.sh",
"text/x-script.tcl",
"text/x-script.tcsh",
"text/x-script.zsh",
"text/x-server-parsed-html",
"text/x-setext",
"text/x-sgml",
"text/x-speech",
"text/x-uil",
"text/x-uuencode",
"text/x-vcalendar",
"video/animaflex",
"video/avi",
"video/avs-video",
"video/dl",
"video/fli",
"video/gl",
"video/mpeg",
"video/msvideo",
"video/quicktime",
"video/vdo",
"video/vivo",
"video/vnd.rn-realvideo",
"video/vnd.vivo",
"video/vosaic",
"video/x-amt-demorun",
"video/x-amt-showrun",
"video/x-atomic3d-feature",
"video/x-dl",
"video/x-dv",
"video/x-fli",
"video/x-gl",
"video/x-isvideo",
"video/x-motion-jpeg",
"video/x-mpeg",
"video/x-mpeq2a",
"video/x-ms-asf",
"video/x-ms-asf-plugin",
"video/x-msvideo",
"video/x-qtc",
"video/x-scm",
"video/x-sgi-movie",
"windows/metafile",
"www/mime",
"x-conference/x-cooltalk",
"xgl/drawing",
"xgl/movie",
"x-music/x-midi",
"x-world/x-3dmf",
"x-world/x-svr",
"x-world/x-vrml",
"x-world/x-vrt"]


def matchFun(input):
    content = str(input)
    return content in _mimelist

iclass = "PythonGrammar"


########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/python
# -*- coding: utf-8 -*-

#copyright (c) 2008-2011 Nestor Arocha

"""Protocols"""

def matchFun(inputd):
    inputs = str(inputd)
    return inputs.find("://") != -1

def propFun(inputd, propertyname):
    inputs = str(inputd)
    protocol, rest = inputs.split("://")
    if propertyname == "protocol":
        return protocol
    if "?" in rest:
        path, options = rest.split("?")
        if propertyname == "path":
            return path
        elif propertyname == "options":
            return options
    else:
        if propertyname == "path":
            return rest

iclass = "PythonGrammar"



########NEW FILE########
__FILENAME__ = SpanishID
#!/usr/bin/python
# -*- coding: utf-8 -*-

#copyright (c) 2008-2013 Nestor Arocha

"""spanish id number grammar"""

def matchFun(inputstr):
    dni = str(inputstr)
    if len(dni) != 9:
        return False
    string = 'TRWAGMYFPDXBNJZSQVHLCKE'
    resto = int(dni[:8]) % 23
    if dni[-1].lower() == string[resto].lower():
        return True
    return False

def propFun(inputstr, propertyname):
    dni = inputstr
    if propertyname == "number":
        return dni[:8]
    elif propertyname == "letter":
        return dni[:-1]
    else:
        return False

iclass = "PythonGrammar"


########NEW FILE########
__FILENAME__ = mongogrammar
spec = {"a":1,"b":2}
fullspec = {"a":{"$type":"integer"},"b":{"$type":"integer"}}

########NEW FILE########
__FILENAME__ = regexps
# -*- coding: utf-8 -*-

res={
        "australian_phone":{"regexp":"^(\+\d{2}[ \-]{0,1}){0,1}(((\({0,1}[ \-]{0,1})0{0,1}\){0,1}[2|3|7|8]{1}\){0,1}[ \-]*(\d{4}[ \-]{0,1}\d{4}))|(1[ \-]{0,1}(300|800|900|902)[ \-]{0,1}((\d{6})|(\d{3}[ \-]{0,1}\d{3})))|(13[ \-]{0,1}([\d \-]{5})|((\({0,1}[ \-]{0,1})0{0,1}\){0,1}4{1}[\d \-]{8,10})))$"},
        "australian_postcode":{"regexp":"(0[289][0-9]{2})|([1345689][0-9]{3})|(2[0-8][0-9]{2})|(290[0-9])|(291[0-4])|(7[0-4][0-9]{2})|(7[8-9][0-9]{2})"},
        "austrian_vat":{"regexp":"^(AT){0,1}[U]{0,1}[0-9]{8}$"},
        "belgian_vat":{"regexp":"^(BE)[0-1]{1}[0-9]{9}$|^((BE)|(BE ))[0-1]{1}(\d{3})([.]{1})(\d{3})([.]{1})(\d{3})"},
        "bic":{"regexp":"^([a-zA-Z]){4}(AF|AX|AL|DZ|AS|AD|AO|AI|AQ|AG|AR|AM|AW|AU|AZ|BS|BH|BD|BB|BY|BE|BZ|BJ|BM|BT|BO|BA|BW|BV|BR|IO|BN|BG|BF|BI|KH|CM|CA|CV|KY|CF|TD|CL|CN|CX|CC|CO|KM|CG|CD|CK|CR|CI|HR|CU|CY|CZ|DK|DJ|DM|DO|EC|EG|SV|GQ|ER|EE|ET|FK|FO|FJ|FI|FR|GF|PF|TF|GA|GM|GE|DE|GH|GI|GR|GL|GD|GP|GU|GT|GG|GN|GW|GY|HT|HM|VA|HN|HK|HU|IS|IN|ID|IR|IQ|IE|IM|IL|IT|JM|JP|JE|JO|KZ|KE|KI|KP|KR|KW|KG|LA|LV|LB|LS|LR|LY|LI|LT|LU|MO|MK|MG|MW|MY|MV|ML|MT|MH|MQ|MR|MU|YT|MX|FM|MD|MC|MC|MN|ME|MS|MA|MZ|MM|MA|NR|NP|NL|AN|NC|NZ|NI|NE|NG|NU|NF|MP|NO|OM|PK|PW|PS|PA|PG|PY|PE|PH|PN|PL|PT|PR|QA|RE|RO|RU|RW|SH|KN|LC|PM|VC|WS|SM|ST|SA|SN|RS|SC|SL|SG|SK|SI|SB|SO|ZA|GS|ES|LK|SD|SR|SJ|SZ|SE|CH|SY|TW|TJ|TZ|TH|TL|TG|TK|TO|TT|TN|TR|TM|TC|TV|UG|UA|AE|GB|US|UM|UY|UZ|VU|VE|VN|VG|VI|WF|EH|YE|ZM|ZW)([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})$"},
        "binary":{"regexp":"^[01]*$"},
        "brainfuck":{"regexp":"^(-|<|>|\.|,|\+|\[|\])+$"},
        "bulgarian_vat":{"regexp":"^(BG){0,1}([0-9]{9}|[0-9]{10})$"},
        "camelcase":{"regexp":"^[A-Z][a-z]+([A-Z][a-z]+)+$"},
        "canadian_postcode":{"regexp":"^[ABCEGHJKLMNPRSTVXYabceghjklmnprstvxy]{1}\d{1}[A-Za-z]{1}\d{1}[A-Za-z]{1}\d{1}$"},
        "characters":{"regexp":"^[A-z]+$"},
        "color_code":{"regexp":"^#(\d{6})|^#([A-F]{6})|^#([A-F]|[0-9]){6}"},
        "coordinate":{"regexp":"^\d{1,2}(\.\d*)?[NS] 1?\d{1,2}(\.\d*)?[EW]$"},
        "credit_card":{"regexp":"^(\d{4}-){3}\d{4}$|^(\d{4} ){3}\d{4}$|^\d{16}$"},
        "dms_coordinate":{"regexp":"[0-9]{1,2}[:|°][0-9]{1,2}[:|'](?:\b[0-9]+(?:\.[0-9]*)?|\.[0-9]+\b)\"?[N|S|E|W]"},
        "dutch_postcode":{"regexp":"^[1-9]{1}[0-9]{3}\s?[a-zA-Z]{2}$"},
        "email":{"regexp":"^(?P<user>[A-Z0-9._%+-]+)@(?P<domain>[A-Z0-9.-]+\.[A-Z]{2,4})$","flags":"i"},
        "FileFilter":{"regexp":"^([A-z]|[*?.])+$"},
        "float":{"regexp":"^[123456789][01234567890]*\.[0123456789]*$"},
        "fqdn":{"regexp":"^(?=^.{1,254}$)(^(?:(?!\.|-)([a-z0-9\-\*]{1,63}|([a-z0-9\-]{1,62}[a-z0-9]))\.)+(?:[a-z]{2,})$)$"},
        "german_postcode":{"regexp":"^[A-Z]{1}( |-)?[1-9]{1}[0-9]{3}$"},
        "hex":{"regexp":"^[0-9a-fA-F]*$"},
        "Identifier":{"regexp":"^[A-Za-z][_A-Za-z0-9]*$"},
        "indian_mobile_2":{"regexp":"^((\+){0,1}91(\s){0,1}(\-){0,1}(\s){0,1}){0,1}9[0-9](\s){0,1}(\-){0,1}(\s){0,1}[1-9]{1}[0-9]{7}$"},
        "indian_mobile":{"regexp":"^[89][0-9]{9}"},
        "indian_postcode":{"regexp":"^[1-9]{3}\s{0,1}[0-9]{3}$"},
        "integer":{"regexp":"^[0123456789]*$"},
        "ipv4_2":{"regexp":"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"},
        "ipv4":{"regexp":"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$"},
        "ipv6":{"regexp":"^((([0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){6}:[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){5}:([0-9A-Fa-f]{1,4}:)?[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){4}:([0-9A-Fa-f]{1,4}:){0,2}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){3}:([0-9A-Fa-f]{1,4}:){0,3}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){2}:([0-9A-Fa-f]{1,4}:){0,4}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){6}((\b((25[0-5])|(1\d{2})|(2[0-4]\d)|(\d{1,2}))\b)\.){3}(\b((25[0-5])|(1\d{2})|(2[0-4]\d)|(\d{1,2}))\b))|(([0-9A-Fa-f]{1,4}:){0,5}:((\b((25[0-5])|(1\d{2})|(2[0-4]\d)|(\d{1,2}))\b)\.){3}(\b((25[0-5])|(1\d{2})|(2[0-4]\d)|(\d{1,2}))\b))|(::([0-9A-Fa-f]{1,4}:){0,5}((\b((25[0-5])|(1\d{2})|(2[0-4]\d)|(\d{1,2}))\b)\.){3}(\b((25[0-5])|(1\d{2})|(2[0-4]\d)|(\d{1,2}))\b))|([0-9A-Fa-f]{1,4}::([0-9A-Fa-f]{1,4}:){0,5}[0-9A-Fa-f]{1,4})|(::([0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){1,7}:))$"},
        "isbn":{"regexp":"^((978[\--– ])?[0-9][0-9\--– ]{10}[\--– ][0-9xX])|((978)?[0-9]{9}[0-9Xx])$"},
        "iso_8601":{"regexp":"^(?<Date>(?<Year>\d{4})-(?<Month>\d{2})-(?<Day>\d{2}))(?:T(?<Time>(?<SimpleTime>(?<Hour>\d{2}):(?<Minute>\d{2})(?::(?<Second>\d{2}))?)?(?:\.(?<FractionalSecond>\d{1,7}))?(?<Offset>-\d{2}\:\d{2})?))?$"},
        "israel_mobile":{"regexp":"^\+?972(\-)?0?[23489]{1}(\-)?[^0\D]{1}\d{6}$"},
        "italian_fiscal_code":{"regexp":"^[A-Za-z]{6}[0-9LMNPQRSTUV]{2}[A-Za-z]{1}[0-9LMNPQRSTUV]{2}[A-Za-z]{1}[0-9LMNPQRSTUV]{3}[A -Za-z]{1}$"},
        "mac_address":{"regexp":"^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$"},
        "netherlands_postcode":{"regexp":"^[1-9]{1}[0-9]{3}\s?[A-Z]{2}$"},
        "nginxlog":{"regexp":"^(?P<ip>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)[^[]+\[([^]]+)\][^/]+([^ ]+).+$"},
        "pakistan_phone":{"regexp":"^((\+92)|(0092))-{0,1}\d{3}-{0,1}\d{7}$|^\d{11}$|^\d{4}-\d{7}$"},
        "passport":{"regexp":"^[A-Z0-9<]{9}[0-9]{1}[A-Z]{3}[0-9]{7}[A-Z]{1}[0-9]{7}[A-Z0-9<]{14}[0-9]{2}$"},
        "polish_landline":{"regexp":"^(\+48\s*)?\d{2}\s*\d{3}(\s*|\-)\d{2}(\s*|\-)\d{2}$"},
        "portuguese_phone":{"regexp":"^((\+351|00351|351)?)(2\d{1}|(9(3|6|2|1)))\d{7}$"},
        "portuguese_postcode":{"regexp":"^[0-9]{4}-[0-9]{3}$"},
        "pythonlogging":{"regexp":"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}),(?P<mil>\d*) \[(?P<level>\w*)\s*\] \[(?P<process>[_\.\w]*)\s*\]: (?P<message>.*)$"},
        "saudi_mobile":{"regexp":"05\d{8}"},
        "scientific_notation":{"regexp":"^(-?[1-9](\.\d+)?)((\s?[X*]\s?10[E^]([+-]?\d+))|(E([+-]?\d+)))$"},
        "slovak_postcode":{"regexp":"^(([0-9]{5})|([0-9]{3}[ ]{0,1}[0-9]{2}))$"},
        "slovenian_phone":{"regexp":"^(([0-9]{3})[ \-\/]?([0-9]{3})[ \-\/]?([0-9]{3}))|([0-9]{9})|([\+]?([0-9]{3})[ \-\/]?([0-9]{2})[ \-\/]?([0-9]{3})[ \-\/]?([0-9]{3}))$"},
        "space":{"regexp":"^ $"},
        "swedish_personnumber":{"regexp":"^[0-9]{6}-[0-9pPtTfF][0-9]{3}$"},
        "swiss_phone":{"regexp":"^(\+?)(\d{2,4})(\s?)(\-?)((\(0\))?)(\s?)(\d{2})(\s?)(\-?)(\d{3})(\s?)(\-?)(\d{2})(\s?)(\-?)(\d{2})"},
        "swiss_postcode":{"regexp":"^[1-9][0-9][0-9][0-9]$"},
        "uk_driving_license":{"regexp":"^([A-Z]{2}[9]{3}|[A-Z]{3}[9]{2}|[A-Z]{4}[9]{1}|[A-Z]{5})[0-9]{6}([A-Z]{1}[9]{1}|[A-Z]{2})[A-Z0-9]{3}[0-9]{2}$"},
        "uknin":{"regexp":"^[A-Z]{2}[0-9]{6}[A-DFM]{1}$", "description":"UK national insurance number"},
        "uk_postcode":{"regexp":"^[A-Za-z]{1,2}[\d]{1,2}([A-Za-z])?\s?[\d][A-Za-z]{2}$"},
        "ukranian_phone":{"regexp":"^((8|\+38)-?)?(\(?044\)?)?-?\d{3}-?\d{2}-?\d{2}$"},
        "uk_vat":{"regexp":"^([GB])*(([1-9]\d{8})|([1-9]\d{11}))$"},
        "unixFilename":{"regexp":"^(\d|\w|\ |\.|\*)*$"},
        "uptime_command":{"regexp":"^([0-2][0-9]\:[0-5][0-9]\:[0-5][0-9])\s+up\s+([0-9\:]{1,5})\s*(days|day|min|mins)?(?:\,\s+([0-9\:]{1,5})\s*(days|day|min|mins)?)?\,\s+([0-9]{1,4})\susers?\,\s+load\s+average\:\s+([0-9\.]{1,6})\,\s+([0-9\.]{1,6})\,\s+([0-9\.]{1,6})$"},
        "uri":{"regexp":"^(?P<protocol>[A-Z0-9]+)://(?P<resource>.*)$", "flags":"i"},
        "us_phone":{"regexp":"^(((\(\d{3}\)|\d{3})( |-|\.))|(\(\d{3}\)|\d{3}))?\d{3}( |-|\.)?\d{4}(( |-|\.)?([Ee]xt|[Xx])[.]?( |-|\.)?\d{4})?$"},
        "us_social_security_number":{"regexp":"^((?!000)(?!666)(?:[0-6]\d{2}|7[0-2][0-9]|73[0-3]|7[5-6][0-9]|77[0-2]))-((?!00)\d{2})-((?!0000)\d{4})$"},
        "uuid":{"regexp":"^((?-i:0x)?[A-Fa-f0-9]{32}| [A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}| \{[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}\})$"},
}


########NEW FILE########
__FILENAME__ = spark_example
#  Copyright (c) 1999-2000 John Aycock
#  
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#  
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from spark_scan_example import scan
from spark_parse_example import parse

if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    f = open(filename)
    parse(scan(f))
    f.close()
    print('ok')

########NEW FILE########
__FILENAME__ = spark_parse_example
#  Copyright (c) 1999-2000 John Aycock
#  
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#  
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
#  Based on Python 1.5.2 grammar.
#

from pydsl.external.spark import GenericParser

class CoreParser(GenericParser):
    def __init__(self, start):
        GenericParser.__init__(self, start)

    def typestring(self, token):
        return token.type

    def error(self, token):
        print("Syntax error at `%s' (line %s)" % (token, token.lineno))
        raise SystemExit

    def p_funcdef(self, args):
        '''
            funcdef ::= def NAME parameters : suite
        '''

    def p_parameters(self, args):
        '''
            parameters ::= ( varargslist )
            parameters ::= ( )
        '''

    def p_varargslist(self, args):
        '''
            varargslist ::= extraargs
            varargslist ::= primaryargs , extraargs
            varargslist ::= primaryargs opt_comma

            primaryargs ::= primaryargs , fpdef = test
            primaryargs ::= primaryargs , fpdef
            primaryargs ::= fpdef = test
            primaryargs ::= fpdef

            extraargs ::= * NAME
            extraargs ::= * NAME , ** NAME
            extraargs ::= * NAME , * * NAME
            extraargs ::= ** NAME
            extraargs ::= * * NAME
        '''

    def p_fpdef(self, args):
        '''
            fpdef ::= NAME
            fpdef ::= ( fplist )
        '''

    def p_fplist(self, args):
        '''
            fplist ::= bare_fplist opt_comma

            bare_fplist ::= bare_fplist , fpdef
            bare_fplist ::= fpdef
        '''

    def p_stmt(self, args):
        '''
            stmt ::= simple_stmt
            stmt ::= compound_stmt
        '''

    def p_simple_stmt(self, args):
        '''
            simple_stmt ::= small_stmt_list ; NEWLINE
            simple_stmt ::= small_stmt_list NEWLINE
        '''

    def p_small_stmt_list(self, args):
        '''
            small_stmt_list ::= small_stmt_list ; small_stmt
            small_stmt_list ::= small_stmt
        '''

    def p_small_stmt(self, args):
        '''
            small_stmt ::= expr_stmt
            small_stmt ::= print_stmt
            small_stmt ::= del_stmt
            small_stmt ::= pass_stmt
            small_stmt ::= flow_stmt
            small_stmt ::= import_stmt
            small_stmt ::= global_stmt
            small_stmt ::= exec_stmt
            small_stmt ::= assert_stmt
        '''

    def p_expr_stmt(self, args):
        '''
            expr_stmt ::= expr_stmt = testlist
            expr_stmt ::= testlist
        '''

    def p_print_stmt(self, args):
        '''
            print_stmt ::= print testlist
            print_stmt ::= print
        '''

    def p_del_stmt(self, args):
        '''
            del_stmt ::= del exprlist
        '''

    def p_pass_stmt(self, args):
        '''
            pass_stmt ::= pass
        '''

    def p_flow_stmt(self, args):
        '''
            flow_stmt ::= break_stmt
            flow_stmt ::= continue_stmt
            flow_stmt ::= return_stmt
            flow_stmt ::= raise_stmt
        '''

    def p_break_stmt(self, args):
        '''
            break_stmt ::= break
        '''

    def p_continue_stmt(self, args):
        '''
            continue_stmt ::= continue
        '''

    def p_return_stmt(self, args):
        '''
            return_stmt ::= return testlist
            return_stmt ::= return
        '''

    def p_raise_stmt(self, args):
        '''
            raise_stmt ::= raise test , test , test
            raise_stmt ::= raise test , test
            raise_stmt ::= raise test
            raise_stmt ::= raise
        '''

    def p_import_stmt(self, args):
        '''
            import_stmt ::= import dotted_name_list
            import_stmt ::= from dotted_name import *
            import_stmt ::= from dotted_name import name_list
        '''

    def p_dotted_name_list(self, args):
        '''
            dotted_name_list ::= dotted_name_list , dotted_name
            dotted_name_list ::= dotted_name
        '''

    def p_name_list(self, args):
        '''
            name_list ::= name_list , NAME
            name_list ::= NAME
        '''

    def p_dotted_name(self, args):
        '''
            dotted_name ::= dotted_name . NAME
            dotted_name ::= NAME
        '''

    def p_global_stmt(self, args):
        '''
            global_stmt ::= global name_list
        '''

    def p_exec_stmt(self, args):
        '''
            exec_stmt ::= exec expr in test , test
            exec_stmt ::= exec expr in test
            exec_stmt ::= exec expr
        '''

    def p_assert_stmt(self, args):
        '''
            assert_stmt ::= assert test , test
            assert_stmt ::= assert test
        '''

    def p_compound_stmt(self, args):
        '''
            compound_stmt ::= if_stmt
            compound_stmt ::= while_stmt
            compound_stmt ::= for_stmt
            compound_stmt ::= try_stmt
            compound_stmt ::= funcdef
            compound_stmt ::= classdef
        '''

    def p_if_stmt(self, args):
        '''
            if_stmt ::= if test : suite elif_clause_list opt_else_clause
            if_stmt ::= if test : suite opt_else_clause
        '''

    def p_elif_clause_list(self, args):
        '''
            elif_clause_list ::= elif_clause_list elif test : suite
            elif_clause_list ::= elif test : suite
        '''

    def p_opt_else_clause(self, args):
        '''
            opt_else_clause ::= else : suite
            opt_else_clause ::=
        '''

    def p_while_stmt(self, args):
        '''
            while_stmt ::= while test : suite opt_else_clause
        '''

    def p_for_stmt(self, args):
        '''
            for_stmt ::= for exprlist in testlist : suite opt_else_clause
        '''

    def p_try_stmt(self, args):
        '''
            try_stmt ::= try : suite except_clause_list opt_else_clause
            try_stmt ::= try : suite finally : suite
        '''

    def p_except_clause_list(self, args):
        '''
            except_clause_list ::= except_clause_list except_clause : suite
            except_clause_list ::= except_clause : suite
        '''

    def p_except_clause(self, args):
        '''
            except_clause ::= except test , test
            except_clause ::= except test
            except_clause ::= except
        '''

    def p_suite(self, args):
        '''
            suite ::= simple_stmt
            suite ::= NEWLINE INDENT stmt_list DEDENT
        '''

    def p_stmt_list(self, args):
        '''
            stmt_list ::= stmt_list stmt
            stmt_list ::= stmt
        '''

    def p_test(self, args):
        '''
            test ::= lambdef
            test ::= or_test
        '''

    def p_or_test(self, args):
        '''
            or_test ::= or_test or and_test
            or_test ::= and_test
        '''

    def p_and_test(self, args):
        '''
            and_test ::= and_test and not_test
            and_test ::= not_test
        '''

    def p_not_test(self, args):
        '''
            not_test ::= not not_test
            not_test ::= comparison
        '''

    def p_comparison(self, args):
        '''
            comparison ::= comparison comp_op expr
            comparison ::= expr
        '''

    def p_comp_op(self, args):
        '''
            comp_op ::= <
            comp_op ::= >
            comp_op ::= ==
            comp_op ::= >=
            comp_op ::= <=
            comp_op ::= <>
            comp_op ::= !=
            comp_op ::= in
            comp_op ::= not in
            comp_op ::= is
            comp_op ::= is not
        '''

    def p_expr(self, args):
        '''
            expr ::= expr | xor_expr
            expr ::= xor_expr
        '''

    def p_xor_expr(self, args):
        '''
            xor_expr ::= xor_expr ^ and_expr
            xor_expr ::= and_expr
        '''

    def p_and_expr(self, args):
        '''
            and_expr ::= and_expr & shift_expr
            and_expr ::= shift_expr
        '''

    def p_shift_expr(self, args):
        '''
            shift_expr ::= shift_expr << arith_expr
            shift_expr ::= shift_expr >> arith_expr
            shift_expr ::= arith_expr
        '''

    def p_arith_expr(self, args):
        '''
            arith_expr ::= arith_expr + term
            arith_expr ::= arith_expr - term
            arith_expr ::= term
        '''

    def p_term(self, args):
        '''
            term ::= term * factor
            term ::= term / factor
            term ::= term % factor
            term ::= factor
        '''

    def p_factor(self, args):
        '''
            factor ::= + factor
            factor ::= - factor
            factor ::= ~ factor
            factor ::= power
        '''

    def p_power(self, args):
        '''
            power ::= atom trailer_list power_list
            power ::= atom trailer_list
            power ::= atom power_list
            power ::= atom
        '''

    def p_trailer_list(self, args):
        '''
            trailer_list ::= trailer_list trailer
            trailer_list ::= trailer
        '''

    def p_power_list(self, args):
        '''
            power_list ::= power_list ** factor
            power_list ::= ** factor
        '''

    def p_atom(self, args):
        '''
            atom ::= ( testlist )
            atom ::= ( )
            atom ::= [ testlist ]
            atom ::= [ ]
            atom ::= { dictmaker }
            atom ::= { }
            atom ::= ` testlist `
            atom ::= NAME
            atom ::= NUMBER
            atom ::= string_list
        '''

    def p_string_list(self, args):
        '''
            string_list ::= string_list STRING
            string_list ::= STRING
        '''

    def p_lambdef(self, args):
        '''
            lambdef ::= lambda varargslist : test
            lambdef ::= lambda : test
        '''

    def p_trailer(self, args):
        '''
            trailer ::= ( arglist )
            trailer ::= ( )
            trailer ::= [ subscriptlist ]
            trailer ::= . NAME
        '''

    def p_subscriptlist(self, args):
        '''
            subscriptlist ::= bare_subscriptlist opt_comma

            bare_subscriptlist ::= bare_subscriptlist , subscript
            bare_subscriptlist ::= subscript
        '''

    def p_subscript(self, args):
        '''
            subscript ::= . . .
            subscript ::= test
            subscript ::= opt_test : opt_test
            subscript ::= opt_test : opt_test : opt_test
        '''

    def p_opt_test(self, args):
        '''
            opt_test ::= test
            opt_test ::=
        '''

    def p_opt_comma(self, args):
        '''
            opt_comma ::= ,
            opt_comma ::=
        '''

    def p_exprlist(self, args):
        '''
            exprlist ::= bare_exprlist opt_comma

            bare_exprlist ::= bare_exprlist , expr
            bare_exprlist ::= expr
        '''

    def p_testlist(self, args):
        '''
            testlist ::= bare_testlist opt_comma

            bare_testlist ::= bare_testlist , test
            bare_testlist ::= test
        '''

    def p_dictmaker(self, args):
        '''
            dictmaker ::= bare_dictmaker opt_comma

            bare_dictmaker ::= bare_dictmaker , test : test
            bare_dictmaker ::= test : test
        '''

    def p_classdef(self, args):
        '''
            classdef ::= class NAME ( testlist ) : suite
            classdef ::= class NAME : suite
        '''

    def p_arglist(self, args):
        '''
            arglist ::= bare_arglist opt_comma

            bare_arglist ::= bare_arglist , argument
            bare_arglist ::= argument
        '''

    def p_argument(self, args):
        '''
            argument ::= test = test
            argument ::= test
        '''

class SingleInputParser(CoreParser):
    def __init__(self):
        CoreParser.__init__(self, 'single_input')

    def p_single_input(self, args):
        '''
            single_input ::= NEWLINE
            single_input ::= simple_stmt
            single_input ::= compound_stmt NEWLINE
        '''

class FileInputParser(CoreParser):
    def __init__(self):
        CoreParser.__init__(self, 'file_input')

    def p_file_input(self, args):
        '''
            file_input ::= file_contents ENDMARKER
        '''

    def p_file_contents(self, args):
        '''
            file_contents ::= file_contents NEWLINE
            file_contents ::= file_contents stmt
            file_contents ::=
        '''

class EvalInputParser(CoreParser):
    def __init__(self):
        CoreParser.__init__(self, 'eval_input')

    def p_eval_input(self, args):
        '''
            eval_input ::= testlist newlines ENDMARKER
            eval_input ::= testlist ENDMARKER

            newlines ::= newlines NEWLINE
            newlines ::= NEWLINE
        '''

def parse(tokens):
    parser = FileInputParser()
    return parser.parse(tokens)

########NEW FILE########
__FILENAME__ = spark_scan_example
#  Copyright (c) 1999-2000 John Aycock
#  
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#  
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
#  Why would I write my own when GvR maintains this one?
#
import tokenize

class Token:
    def __init__(self, type, attr=None, lineno='???'):
        self.type = type
        self.attr = attr
        self.lineno = lineno

    def __cmp__(self, o):
        return cmp(self.type, o)
    ###
    def __repr__(self):
        return str(self.type)

_map = {
    tokenize.ENDMARKER    : 'ENDMARKER',
    tokenize.NAME         : 'NAME',
    tokenize.NUMBER        : 'NUMBER',
    tokenize.STRING        : 'STRING',
    tokenize.NEWLINE    : 'NEWLINE',
    tokenize.INDENT        : 'INDENT',
    tokenize.DEDENT        : 'DEDENT',
}

_rw = {
    'and'        : None,
    'assert'    : None,
    'break'        : None,
    'class'        : None,
    'continue'    : None,
    'def'        : None,
    'del'        : None,
    'elif'        : None,
    'else'        : None,
    'except'    : None,
    'exec'        : None,
    'finally'    : None,
    'for'        : None,
    'from'        : None,
    'global'    : None,
    'if'        : None,
    'import'    : None,
    'in'        : None,
    'is'        : None,
    'lambda'    : None,
    'not'        : None,
    'or'        : None,
    'pass'        : None,
    'print'        : None,
    'raise'        : None,
    'return'    : None,
    'try'        : None,
    'while'        : None,
}

def scan(f):
    tokens = []

    def callback(value, lexeme, lineno_column, end, line, list=tokens):
        attr = None
        type = lexeme
        lineno, column = lineno_column
        if value in (tokenize.COMMENT, tokenize.NL):
            return
        elif value in _map:
            if value != tokenize.NAME or not lexeme in _rw:
                attr = lexeme
                type = _map[value]

        t = Token(type, attr=attr, lineno=lineno)
        list.append(t)

    [callback(*token) for token in tokenize.generate_tokens(f.readline)]
    return tokens

########NEW FILE########
__FILENAME__ = chemicalFormulas
# chemicalFormulas.py
#
# Copyright (c) 2003, 2007, Paul McGuire
#

from pyparsing import Word, Optional, OneOrMore, Group, ParseException

# define a simple Python dict of atomic weights, with chemical symbols
# for keys
atomicWeight = {
    "O"  : 15.9994,
    "H"  : 1.00794,
    "Na" : 22.9897,
    "Cl" : 35.4527,
    "C"  : 12.0107,
    "S"  : 32.0655,
    }

# define some strings to use later, when describing valid lists 
# of characters for chemical symbols and numbers
caps = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
lowers = caps.lower()
digits = "0123456789"

# Version 1
# Define grammar for a chemical formula
# - an element is a Word, beginning with one of the characters in caps,
#   followed by zero or more characters in lowers
# - an integer is a Word composed of digits
# - an elementRef is an element, optionally followed by an integer - if 
#   the integer is omitted, assume the value "1" as a default; these are 
#   enclosed in a Group to make it easier to walk the list of parsed 
#   chemical symbols, each with its associated number of atoms per 
#   molecule
# - a chemicalFormula is just one or more elementRef's
element = Word( caps, lowers )
integer = Word( digits )
elementRef = Group( element + Optional( integer, default="1" ) )
chemicalFormula = OneOrMore( elementRef )

# Version 2 - Auto-convert integers, and add results names
def convertIntegers(tokens):
    return int(tokens[0])
    
element = Word( caps, lowers )
integer = Word( digits ).setParseAction( convertIntegers )
elementRef = Group( element("symbol") + Optional( integer, default=1 )("qty") )
# pre-1.4.7, use this: 
# elementRef = Group( element.setResultsName("symbol") + Optional( integer, default=1 ).setResultsName("qty") )
chemicalFormula = OneOrMore( elementRef )


# Version 3 - Compute partial molecular weight per element, simplifying 
# summing
# No need to redefine grammar, just define parse action function, and
# attach to elementRef
def computeElementWeight(tokens):
    element = tokens[0]
    element["weight"] = atomicWeight[element.symbol] * element.qty
    
elementRef.setParseAction(computeElementWeight)

root_symbol = chemicalFormula

iclass = "pyparsing"

########NEW FILE########
__FILENAME__ = echo
def function(input):
    return input


iclass = "PythonTransformer"
inputdic = {"input":"cstring"}
outputdic = {"output":"cstring"}

########NEW FILE########
__FILENAME__ = Exceptions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


"""Exceptions definitions"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"


class ParseError(Exception):

    def __init__(self, msg, offset):
        self.msg = msg
        self.offset = offset

    def __repr__(self):
        return "ParseError(%r, %r)" % (self.msg, self.offset)

    def __str__(self):
        return "%s at position %s" % (self.msg, self.offset + 1)

########NEW FILE########
__FILENAME__ = spark
#  Copyright (c) 1998-2002 John Aycock
#  
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#  
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#  
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

__version__ = 'SPARK-0.7 (pre-alpha-7)'

import re

def _namelist(instance):
    namelist, namedict, classlist = [], {}, [instance.__class__]
    for c in classlist:
        for b in c.__bases__:
            classlist.append(b)
        for name in c.__dict__.keys():
            if name not in namedict:
                namelist.append(name)
                namedict[name] = 1
    return namelist

class GenericScanner:
    def __init__(self, flags=0):
        pattern = self.reflect()
        self.re = re.compile(pattern, re.VERBOSE|flags)

        self.index2func = {}
        for name, number in self.re.groupindex.items():
            self.index2func[number-1] = getattr(self, 't_' + name)

    def makeRE(self, name):
        doc = getattr(self, name).__doc__
        rv = '(?P<%s>%s)' % (name[2:], doc)
        return rv

    def reflect(self):
        rv = []
        for name in _namelist(self):
            if name[:2] == 't_' and name != 't_default':
                rv.append(self.makeRE(name))

        rv.append(self.makeRE('t_default'))
        return '|'.join(rv)

    def error(self, s, pos):
        print("Lexical error at position %s" % pos)
        raise SystemExit

    def position(self, newpos=None):
        oldpos = self.pos
        if newpos is not None:
            self.pos = newpos
        return self.string, oldpos
        
    def tokenize(self, s):
        self.string = s
        self.pos = 0
        n = len(s)
        while self.pos < n:
            m = self.re.match(s, self.pos)
            if m is None:
                self.error(s, self.pos)

            groups = m.groups()
            self.pos = m.end()
            for i in range(len(groups)):
                if groups[i] is not None and i in self.index2func:
                    self.index2func[i](groups[i])

    def t_default(self, s):
        r'( . | \n )+'
        print("Specification error: unmatched input")
        raise SystemExit

#
#  Extracted from GenericParser and made global so that [un]picking works.
#
class _State:
    def __init__(self, stateno, items):
        self.T, self.complete, self.items = [], [], items
        self.stateno = stateno

class GenericParser:
    #
    #  An Earley parser, as per J. Earley, "An Efficient Context-Free
    #  Parsing Algorithm", CACM 13(2), pp. 94-102.  Also J. C. Earley,
    #  "An Efficient Context-Free Parsing Algorithm", Ph.D. thesis,
    #  Carnegie-Mellon University, August 1968.  New formulation of
    #  the parser according to J. Aycock, "Practical Earley Parsing
    #  and the SPARK Toolkit", Ph.D. thesis, University of Victoria,
    #  2001, and J. Aycock and R. N. Horspool, "Practical Earley
    #  Parsing", unpublished paper, 2001.
    #

    def __init__(self, start):
        self.rules = {}
        self.rule2func = {}
        self.rule2name = {}
        self.collectRules()
        self.augment(start)
        self.ruleschanged = 1

    _NULLABLE = '\e_'
    _START = 'START'
    _BOF = '|-'

    #
    #  When pickling, take the time to generate the full state machine;
    #  some information is then extraneous, too.  Unfortunately we
    #  can't save the rule2func map.
    #
    def __getstate__(self):
        if self.ruleschanged:
            #
            #  XXX - duplicated from parse()
            #
            self.computeNull()
            self.newrules = {}
            self.new2old = {}
            self.makeNewRules()
            self.ruleschanged = 0
            self.edges, self.cores = {}, {}
            self.states = { 0: self.makeState0() }
            self.makeState(0, self._BOF)
        #
        #  XXX - should find a better way to do this..
        #
        changes = 1
        while changes:
            changes = 0
            for k, v in self.edges.items():
                if v is None:
                    state, sym = k
                    if state in self.states:
                        self.goto(state, sym)
                        changes = 1
        rv = self.__dict__.copy()
        for s in self.states.values():
            del s.items
        del rv['rule2func']
        del rv['nullable']
        del rv['cores']
        return rv

    def __setstate__(self, D):
        self.rules = {}
        self.rule2func = {}
        self.rule2name = {}
        self.collectRules()
        start = D['rules'][self._START][0][1][1]    # Blech.
        self.augment(start)
        D['rule2func'] = self.rule2func
        D['makeSet'] = self.makeSet_fast
        self.__dict__ = D

    #
    #  A hook for GenericASTBuilder and GenericASTMatcher.  Mess
    #  thee not with this; nor shall thee toucheth the _preprocess
    #  argument to addRule.
    #
    def preprocess(self, rule, func):
        return rule, func

    def addRule(self, doc, func, _preprocess=1):
        fn = func
        rules = doc.split()

        index = []
        for i in range(len(rules)):
            if rules[i] == '::=':
                index.append(i-1)
        index.append(len(rules))

        for i in range(len(index)-1):
            lhs = rules[index[i]]
            rhs = rules[index[i]+2:index[i+1]]
            rule = (lhs, tuple(rhs))

            if _preprocess:
                rule, fn = self.preprocess(rule, func)

            if lhs in self.rules:
                self.rules[lhs].append(rule)
            else:
                self.rules[lhs] = [ rule ]
            self.rule2func[rule] = fn
            self.rule2name[rule] = func.__name__[2:]
        self.ruleschanged = 1

    def collectRules(self):
        for name in _namelist(self):
            if name[:2] == 'p_':
                func = getattr(self, name)
                doc = func.__doc__
                self.addRule(doc, func)

    def augment(self, start):
        rule = '%s ::= %s %s' % (self._START, self._BOF, start)
        self.addRule(rule, lambda args: args[1], 0)

    def computeNull(self):
        self.nullable = {}
        tbd = []

        for rulelist in self.rules.values():
            lhs = rulelist[0][0]
            self.nullable[lhs] = 0
            for rule in rulelist:
                rhs = rule[1]
                if len(rhs) == 0:
                    self.nullable[lhs] = 1
                    continue
                #
                #  We only need to consider rules which
                #  consist entirely of nonterminal symbols.
                #  This should be a savings on typical
                #  grammars.
                #
                for sym in rhs:
                    if sym not in self.rules:
                        break
                else:
                    tbd.append(rule)
        changes = 1
        while changes:
            changes = 0
            for lhs, rhs in tbd:
                if self.nullable[lhs]:
                    continue
                for sym in rhs:
                    if not self.nullable[sym]:
                        break
                else:
                    self.nullable[lhs] = 1
                    changes = 1

    def makeState0(self):
        s0 = _State(0, [])
        for rule in self.newrules[self._START]:
            s0.items.append((rule, 0))
        return s0

    def finalState(self, tokens):
        #
        #  Yuck.
        #
        if len(self.newrules[self._START]) == 2 and len(tokens) == 0:
            return 1
        start = self.rules[self._START][0][1][1]
        return self.goto(1, start)

    def makeNewRules(self):
        worklist = []
        for rulelist in self.rules.values():
            for rule in rulelist:
                worklist.append((rule, 0, 1, rule))

        for rule, i, candidate, oldrule in worklist:
            lhs, rhs = rule
            n = len(rhs)
            while i < n:
                sym = rhs[i]
                if sym not in self.rules or not self.nullable[sym]:
                    candidate = 0
                    i = i + 1
                    continue

                newrhs = list(rhs)
                newrhs[i] = self._NULLABLE+sym
                newrule = (lhs, tuple(newrhs))
                worklist.append((newrule, i+1,
                         candidate, oldrule))
                candidate = 0
                i = i + 1
            else:
                if candidate:
                    lhs = self._NULLABLE+lhs
                    rule = (lhs, rhs)
                if lhs in self.newrules:
                    self.newrules[lhs].append(rule)
                else:
                    self.newrules[lhs] = [ rule ]
                self.new2old[rule] = oldrule
    
    def typestring(self, token):
        return None

    def error(self, token):
        print("Syntax error at or near `%s' token" % token)
        raise SystemExit

    def parse(self, tokens):
        sets = [ [(1,0), (2,0)] ]
        self.links = {}
        
        if self.ruleschanged:
            self.computeNull()
            self.newrules = {}
            self.new2old = {}
            self.makeNewRules()
            self.ruleschanged = 0
            self.edges, self.cores = {}, {}
            self.states = { 0: self.makeState0() }
            self.makeState(0, self._BOF)

        for i in range(len(tokens)):
            sets.append([])

            if sets[i] == []:
                break                
            self.makeSet(tokens[i], sets, i)
        else:
            sets.append([])
            self.makeSet(None, sets, len(tokens))

        #_dump(tokens, sets, self.states)

        finalitem = (self.finalState(tokens), 0)
        if finalitem not in sets[-2]:
            if len(tokens) > 0:
                self.error(tokens[i-1])
            else:
                self.error(None)

        return self.buildTree(self._START, finalitem,
                      tokens, len(sets)-2)

    def isnullable(self, sym):
        #
        #  For symbols in G_e only.  If we weren't supporting 1.5,
        #  could just use sym.startswith().
        #
        return self._NULLABLE == sym[0:len(self._NULLABLE)]

    def skip(self, lhs_rhs, pos=0):
        lhs, rhs = lhs_rhs
        n = len(rhs)
        while pos < n:
            if not self.isnullable(rhs[pos]):
                break
            pos = pos + 1
        return pos

    def makeState(self, state, sym):
        assert sym is not None
        #
        #  Compute \epsilon-kernel state's core and see if
        #  it exists already.
        #
        kitems = []
        for rule, pos in self.states[state].items:
            lhs, rhs = rule
            if rhs[pos:pos+1] == (sym,):
                kitems.append((rule, self.skip(rule, pos+1)))
        core = kitems

        core.sort()
        tcore = tuple(core)
        if tcore in self.cores:
            return self.cores[tcore]
        #
        #  Nope, doesn't exist.  Compute it and the associated
        #  \epsilon-nonkernel state together; we'll need it right away.
        #
        k = self.cores[tcore] = len(self.states)
        K, NK = _State(k, kitems), _State(k+1, [])
        self.states[k] = K
        predicted = {}

        edges = self.edges
        rules = self.newrules
        for X in K, NK:
            worklist = X.items
            for item in worklist:
                rule, pos = item
                lhs, rhs = rule
                if pos == len(rhs):
                    X.complete.append(rule)
                    continue

                nextSym = rhs[pos]
                key = (X.stateno, nextSym)
                if nextSym not in rules:
                    if key not in edges:
                        edges[key] = None
                        X.T.append(nextSym)
                else:
                    edges[key] = None
                    if nextSym not in predicted:
                        predicted[nextSym] = 1
                        for prule in rules[nextSym]:
                            ppos = self.skip(prule)
                            new = (prule, ppos)
                            NK.items.append(new)
            #
            #  Problem: we know K needs generating, but we
            #  don't yet know about NK.  Can't commit anything
            #  regarding NK to self.edges until we're sure.  Should
            #  we delay committing on both K and NK to avoid this
            #  hacky code?  This creates other problems..
            #
            if X is K:
                edges = {}

        if NK.items == []:
            return k

        #
        #  Check for \epsilon-nonkernel's core.  Unfortunately we
        #  need to know the entire set of predicted nonterminals
        #  to do this without accidentally duplicating states.
        #
        core = list(predicted.keys())
        core.sort()
        tcore = tuple(core)
        if tcore in self.cores:
            self.edges[(k, None)] = self.cores[tcore]
            return k

        nk = self.cores[tcore] = self.edges[(k, None)] = NK.stateno
        self.edges.update(edges)
        self.states[nk] = NK
        return k

    def goto(self, state, sym):
        key = (state, sym)
        if key not in self.edges:
            #
            #  No transitions from state on sym.
            #
            return None

        rv = self.edges[key]
        if rv is None:
            #
            #  Target state isn't generated yet.  Remedy this.
            #
            rv = self.makeState(state, sym)
            self.edges[key] = rv
        return rv

    def gotoT(self, state, t):
        return [self.goto(state, t)]

    def gotoST(self, state, st):
        rv = []
        for t in self.states[state].T:
            if st == t:
                rv.append(self.goto(state, t))
        return rv

    def add(self, set, item, i=None, predecessor=None, causal=None):
        if predecessor is None:
            if item not in set:
                set.append(item)
        else:
            key = (item, i)
            if item not in set:
                self.links[key] = []
                set.append(item)
            self.links[key].append((predecessor, causal))

    def makeSet(self, token, sets, i):
        cur, next = sets[i], sets[i+1]

        ttype = token is not None and self.typestring(token) or None
        if ttype is not None:
            fn, arg = self.gotoT, ttype
        else:
            fn, arg = self.gotoST, token

        for item in cur:
            ptr = (item, i)
            state, parent = item
            add = fn(state, arg)
            for k in add:
                if k is not None:
                    self.add(next, (k, parent), i+1, ptr)
                    nk = self.goto(k, None)
                    if nk is not None:
                        self.add(next, (nk, i+1))

            if parent == i:
                continue

            for rule in self.states[state].complete:
                lhs, rhs = rule
                for pitem in sets[parent]:
                    pstate, pparent = pitem
                    k = self.goto(pstate, lhs)
                    if k is not None:
                        why = (item, i, rule)
                        pptr = (pitem, parent)
                        self.add(cur, (k, pparent),
                             i, pptr, why)
                        nk = self.goto(k, None)
                        if nk is not None:
                            self.add(cur, (nk, i))

    def makeSet_fast(self, token, sets, i):
        #
        #  Call *only* when the entire state machine has been built!
        #  It relies on self.edges being filled in completely, and
        #  then duplicates and inlines code to boost speed at the
        #  cost of extreme ugliness.
        #
        cur, next = sets[i], sets[i+1]
        ttype = token is not None and self.typestring(token) or None

        for item in cur:
            ptr = (item, i)
            state, parent = item
            if ttype is not None:
                k = self.edges.get((state, ttype), None)
                if k is not None:
                    #self.add(next, (k, parent), i+1, ptr)
                    #INLINED --v
                    new = (k, parent)
                    key = (new, i+1)
                    if new not in next:
                        self.links[key] = []
                        next.append(new)
                    self.links[key].append((ptr, None))
                    #INLINED --^
                    #nk = self.goto(k, None)
                    nk = self.edges.get((k, None), None)
                    if nk is not None:
                        #self.add(next, (nk, i+1))
                        #INLINED --v
                        new = (nk, i+1)
                        if new not in next:
                            next.append(new)
                        #INLINED --^
            else:
                add = self.gotoST(state, token)
                for k in add:
                    if k is not None:
                        self.add(next, (k, parent), i+1, ptr)
                        #nk = self.goto(k, None)
                        nk = self.edges.get((k, None), None)
                        if nk is not None:
                            self.add(next, (nk, i+1))

            if parent == i:
                continue

            for rule in self.states[state].complete:
                lhs, rhs = rule
                for pitem in sets[parent]:
                    pstate, pparent = pitem
                    #k = self.goto(pstate, lhs)
                    k = self.edges.get((pstate, lhs), None)
                    if k is not None:
                        why = (item, i, rule)
                        pptr = (pitem, parent)
                        #self.add(cur, (k, pparent),
                        #     i, pptr, why)
                        #INLINED --v
                        new = (k, pparent)
                        key = (new, i)
                        if new not in cur:
                            self.links[key] = []
                            cur.append(new)
                        self.links[key].append((pptr, why))
                        #INLINED --^
                        #nk = self.goto(k, None)
                        nk = self.edges.get((k, None), None)
                        if nk is not None:
                            #self.add(cur, (nk, i))
                            #INLINED --v
                            new = (nk, i)
                            if new not in cur:
                                cur.append(new)
                            #INLINED --^

    def predecessor(self, key, causal):
        for p, c in self.links[key]:
            if c == causal:
                return p
        assert 0

    def causal(self, key):
        links = self.links[key]
        if len(links) == 1:
            return links[0][1]
        choices = []
        rule2cause = {}
        for p, c in links:
            rule = c[2]
            choices.append(rule)
            rule2cause[rule] = c
        return rule2cause[self.ambiguity(choices)]

    def deriveEpsilon(self, nt):
        if len(self.newrules[nt]) > 1:
            rule = self.ambiguity(self.newrules[nt])
        else:
            rule = self.newrules[nt][0]
        #print rule

        rhs = rule[1]
        attr = [None] * len(rhs)

        for i in range(len(rhs)-1, -1, -1):
            attr[i] = self.deriveEpsilon(rhs[i])
        return self.rule2func[self.new2old[rule]](attr)

    def buildTree(self, nt, item, tokens, k):
        state, parent = item

        choices = []
        for rule in self.states[state].complete:
            if rule[0] == nt:
                choices.append(rule)
        rule = choices[0]
        if len(choices) > 1:
            rule = self.ambiguity(choices)
        #print rule

        rhs = rule[1]
        attr = [None] * len(rhs)

        for i in range(len(rhs)-1, -1, -1):
            sym = rhs[i]
            if sym not in self.newrules:
                if sym != self._BOF:
                    attr[i] = tokens[k-1]
                    key = (item, k)
                    item, k = self.predecessor(key, None)
            #elif self.isnullable(sym):
            elif self._NULLABLE == sym[0:len(self._NULLABLE)]:
                attr[i] = self.deriveEpsilon(sym)
            else:
                key = (item, k)
                why = self.causal(key)
                attr[i] = self.buildTree(sym, why[0],
                             tokens, why[1])
                item, k = self.predecessor(key, why)
        return self.rule2func[self.new2old[rule]](attr)

    def ambiguity(self, rules):
        #
        #  XXX - problem here and in collectRules() if the same rule
        #     appears in >1 method.  Also undefined results if rules
        #     causing the ambiguity appear in the same method.
        #
        sortlist = []
        name2index = {}
        for i in range(len(rules)):
            lhs, rhs = rule = rules[i]
            name = self.rule2name[self.new2old[rule]]
            sortlist.append((len(rhs), name))
            name2index[name] = i
        sortlist.sort()
        list = map(lambda a,b: b, sortlist)
        return rules[name2index[self.resolve(list)]]

    def resolve(self, list):
        #
        #  Resolve ambiguity in favor of the shortest RHS.
        #  Since we walk the tree from the top down, this
        #  should effectively resolve in favor of a "shift".
        #
        return list[0]

#
#  GenericASTBuilder automagically constructs a concrete/abstract syntax tree
#  for a given input.  The extra argument is a class (not an instance!)
#  which supports the "__setslice__" and "__len__" methods.
#
#  XXX - silently overrides any user code in methods.
#

class GenericASTBuilder(GenericParser):
    def __init__(self, AST, start):
        GenericParser.__init__(self, start)
        self.AST = AST

    def preprocess(self, rule, func):
        rebind = lambda lhs, self=self: \
                lambda args, lhs=lhs, self=self: \
                    self.buildASTNode(args, lhs)
        lhs, rhs = rule
        return rule, rebind(lhs)

    def buildASTNode(self, args, lhs):
        children = []
        for arg in args:
            if isinstance(arg, self.AST):
                children.append(arg)
            else:
                children.append(self.terminal(arg))
        return self.nonterminal(lhs, children)

    def terminal(self, token):
        return token

    def nonterminal(self, type, args):
        rv = self.AST(type)
        rv[:len(args)] = args
        return rv

#
#  GenericASTTraversal is a Visitor pattern according to Design Patterns.  For
#  each node it attempts to invoke the method n_<node type>, falling
#  back onto the default() method if the n_* can't be found.  The preorder
#  traversal also looks for an exit hook named n_<node type>_exit (no default
#  routine is called if it's not found).  To prematurely halt traversal
#  of a subtree, call the prune() method -- this only makes sense for a
#  preorder traversal.  Node type is determined via the typestring() method.
#

class GenericASTTraversalPruningException:
    pass

class GenericASTTraversal:
    def __init__(self, ast):
        self.ast = ast

    def typestring(self, node):
        return node.type

    def prune(self):
        raise GenericASTTraversalPruningException

    def preorder(self, node=None):
        if node is None:
            node = self.ast

        try:
            name = 'n_' + self.typestring(node)
            if hasattr(self, name):
                func = getattr(self, name)
                func(node)
            else:
                self.default(node)
        except GenericASTTraversalPruningException:
            return

        for kid in node:
            self.preorder(kid)

        name = name + '_exit'
        if hasattr(self, name):
            func = getattr(self, name)
            func(node)

    def postorder(self, node=None):
        if node is None:
            node = self.ast

        for kid in node:
            self.postorder(kid)

        name = 'n_' + self.typestring(node)
        if hasattr(self, name):
            func = getattr(self, name)
            func(node)
        else:
            self.default(node)


    def default(self, node):
        pass

#
#  GenericASTMatcher.  AST nodes must have "__getitem__" and "__cmp__"
#  implemented.
#
#  XXX - makes assumptions about how GenericParser walks the parse tree.
#

class GenericASTMatcher(GenericParser):
    def __init__(self, start, ast):
        GenericParser.__init__(self, start)
        self.ast = ast

    def preprocess(self, rule, func):
        rebind = lambda func, self=self: \
                lambda args, func=func, self=self: \
                    self.foundMatch(args, func)
        lhs, rhs = rule
        rhslist = list(rhs)
        rhslist.reverse()

        return (lhs, tuple(rhslist)), rebind(func)

    def foundMatch(self, args, func):
        func(args[-1])
        return args[-1]

    def match_r(self, node):
        self.input.insert(0, node)
        children = 0

        for child in node:
            if children == 0:
                self.input.insert(0, '(')
            children = children + 1
            self.match_r(child)

        if children > 0:
            self.input.insert(0, ')')

    def match(self, ast=None):
        if ast is None:
            ast = self.ast
        self.input = []

        self.match_r(ast)
        self.parse(self.input)

    def resolve(self, list):
        #
        #  Resolve ambiguity in favor of the longest RHS.
        #
        return list[-1]

def _dump(tokens, sets, states):
    for i in range(len(sets)):
        print('set', i)
        for item in sets[i]:
            print('\t', item)
            for (lhs, rhs), pos in states[item[0]].items:
                print('\t\t', lhs, '::=')
                print("".join(rhs[:pos]))
                print('.',)
                print("".join(rhs[pos:]))
        if i < len(tokens):
            print()
            print('token', str(tokens[i]))
            print()

########NEW FILE########
__FILENAME__ = Extract
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)
from pydsl.Check import checker_factory
from pydsl.Lex import lexer_factory
from pydsl.Alphabet import Alphabet, Encoding
from pydsl.Token import PositionToken, Token


def filter_subsets(lst):
    to_remove = []
    for i, j, _ in lst:
        for x,y, _ in lst:
            if (x < i and y >= j) or (x <= i and y > j):
                to_remove.append((i,j))
                break
    result = list(lst)

    for element in lst:
        if (element[0], element[1]) in to_remove:
            result.remove(element)
    return result


def extract_alphabet(alphabet, inputdata, fixed_start = False):
    """
    Receives a sequence and an alphabet, 
    returns a list of PositionTokens with all of the parts of the sequence that 
    are a subset of the alphabet
    """
    if not inputdata:
        return []
    if isinstance(alphabet, Encoding):
        base_alphabet = None
    else:
        base_alphabet = alphabet.alphabet

    if isinstance(inputdata[0], (Token, PositionToken)):
        inputdata = [x.content for x in inputdata]


    lexer = lexer_factory(alphabet, base_alphabet)
    totallen = len(inputdata)
    maxl = totallen
    minl = 1
    if fixed_start:
        max_start = 1
    else:
        max_start = totallen
    result = []
    for i in range(max_start):
        for j in range(i+minl, min(i+maxl, totallen) + 1):
            try:
                lexed = lexer(inputdata[i:j])
                if lexed:
                    result.append((i,j, inputdata[i:j]))
            except:
                continue
    result = filter_subsets(result)
    return [PositionToken(content, None, left, right) for (left, right, content) in result]

def extract(grammar, inputdata, fixed_start = False):
    """
    Receives a sequence and a grammar, 
    returns a list of PositionTokens with all of the parts of the sequence that 
    are recognized by the grammar
    """
    if not inputdata:
        return []
    checker = checker_factory(grammar)

    if isinstance(inputdata[0], (Token, PositionToken)):
        inputdata = [x.content for x in inputdata]

    totallen = len(inputdata)
    try:
        maxl = grammar.maxsize or totallen
    except NotImplementedError:
        maxl = totallen
    try:
        #minl = grammar.minsize #FIXME: It won't work with incompatible alphabets
        minl = 1
    except NotImplementedError:
        minl = 1
    if fixed_start:
        max_start = 1
    else:
        max_start = totallen
    result = []
    for i in range(max_start):
        for j in range(i+minl, min(i+maxl, totallen) + 1):
            check = checker.check(inputdata[i:j])
            if check:
                result.append(PositionToken(inputdata[i:j], None, i, j))
    return result


########NEW FILE########
__FILENAME__ = BNF
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


"""BNF format functions"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
import re
from pydsl.Grammar.Symbol import TerminalSymbol,  NonTerminalSymbol, NullSymbol
from pydsl.Grammar.BNF import Production
LOG = logging.getLogger(__name__)

""" pydsl Grammar definition file parser """

def __generateStringSymbol(rightside):
    head, tail = rightside.split(",", 1)
    if head != "String":
        raise TypeError
    content = tail
    if len(tail) > 2 and tail[1][0] == "'" and tail[1][-1] == "'":
        content = tail[1][1:-1]
    from pydsl.Grammar.Definition import String
    return TerminalSymbol(String(content))

def __generateWordSymbol(rightside, repository):
    args = rightside.split(",")
    if args[0] != "Word":
        raise TypeError
    br = args[2] #Boundary rule policy
    return TerminalSymbol(repository[args[1]], None, br)


def read_nonterminal_production(line, symboldict):
    sidesarray = line.split("::=")
    if len(sidesarray) < 2 or len(sidesarray) > 3:
        raise ValueError("Error reading nonterminal production rule")
    leftside = sidesarray[0].strip()
    #leftside contains at least one NonTerminalSymbol
    #FIXME supports only one symbol
    symboldict[leftside] = NonTerminalSymbol(leftside)
    rightside = sidesarray[1]
    alternatives = [alt.rstrip() for alt in rightside.split("|")]
    result = []
    n = 0
    for alternative in alternatives:
        symbollist = alternative.split()
        symbolinstancelist = []
        for symbol in symbollist:
            symbolinstancelist.append(symboldict[symbol])
        result.append(Production([symboldict[leftside]], symbolinstancelist))
        n += 1
    return result

def read_terminal_production(line, repository):
    leftside, rightside = line.split(":=")
    leftside = leftside.strip()
    symbolnames = leftside.split(" ")
    if len(symbolnames) != 1:
        LOG.error("Error generating terminal rule: " + line + "At left side")
        raise ValueError("Error reading left side of terminal production rule")
    #leftside is symbolname
    rightside = rightside.strip()
    #regexp to detect rightside: String, Grammar
    if re.search("^String", rightside):
        newsymbol = __generateStringSymbol(rightside)
    elif re.search("^Word", rightside):
        newsymbol = __generateWordSymbol(rightside, repository)
    elif re.search("^Null", rightside):
        newsymbol = NullSymbol()
    else:
        raise ValueError("Unknown terminal production type " + str(rightside))
    return symbolnames[0], newsymbol


def strlist_to_production_set(linelist, repository = None, start_symbol = "S"):
    if repository is None:
        repository = {}
    nonterminalrulelist = []
    terminalrulelist = []
    rulelist = []
    symboldict = {"Null":NullSymbol()}
    macrodict = {}
    #first read terminalsymbols
    for line in linelist:
        cleanline = re.sub("//.*$", "", line)
        if re.search("::=", cleanline):
            nonterminalrulelist.append(cleanline)
        elif re.search (":=", cleanline):
            symbolname, symbolinstance = read_terminal_production(cleanline, repository)
            symboldict[symbolname] = symbolinstance
            terminalrulelist.append(symbolinstance)
        elif re.search ("^#.*$", cleanline):
            pair = cleanline[1:].split("=")
            assert(len(pair)==2)
            macrodict[pair[0]] = pair[1].rstrip()
        elif re.search ("^\s*$", cleanline):
            pass #Empty line
        else:
            raise ValueError("Unknown line at bnf input file")

    #then read nonterminalsymbols
    while len(nonterminalrulelist) > 0:
        linestodrop = []
        for myindex in range(len(nonterminalrulelist)):
            try:
                newrules = read_nonterminal_production(nonterminalrulelist[myindex], symboldict)
                for newrule in newrules:
                    rulelist.append(newrule)
            except KeyError:
                pass
            else:
                linestodrop.append(myindex)
        linestodrop.reverse()
        if len(linestodrop) == 0:
            raise Exception("No rule found: ")
        for myindex in linestodrop:
            del nonterminalrulelist[myindex]
    from pydsl.Grammar.BNF import BNFGrammar
    for terminal in terminalrulelist:
        rulelist.append(terminal)
    return BNFGrammar(symboldict[start_symbol], rulelist, macrodict)


def load_bnf_file(filepath, repository = None):
    """Converts a bnf file into a BNFGrammar instance"""
    linelist = []
    with open(filepath,'r') as mlfile:
        for line in mlfile:
            linelist.append(line)
    return strlist_to_production_set(linelist, repository)


def str_to_productionset(string):
    """Converts a str into a ProductionRuleSet"""
    return strlist_to_production_set(string.split('\n'))


########NEW FILE########
__FILENAME__ = Parsley
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


from pydsl.Grammar.Parsley import ParsleyGrammar

__author__ = "Ptolom"
__copyright__ = "Copyright 2014, Ptolom"
__email__ = "ptolom@hexifact.co.uk"

#!/usr/bin/python
def load_parsley_grammar_file(filepath, root_rule, repository={}):
    with open(filepath,'r') as file:
        return ParsleyGrammar(file.read(), root_rule, repository)





########NEW FILE########
__FILENAME__ = Python
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


""" File Library class """

import imp

def getFileTuple(fullname):
    import os.path
    (dirName, fileName) = os.path.split(fullname)
    (fileBaseName, fileExtension) = os.path.splitext(fileName)
    return dirName, fileName, fileBaseName, fileExtension

def load_module(filepath, identifier = None):
    if identifier is None:
        (_, _, identifier, _) = getFileTuple(filepath)
    return imp.load_source(identifier, filepath)

def load_python_file(moduleobject):
    """ Try to create an indexable instance from a module"""
    if isinstance(moduleobject, str):
        moduleobject = load_module(moduleobject)
    if not hasattr(moduleobject, "iclass"):
        raise KeyError("Element" + str(moduleobject))
    iclass = getattr(moduleobject, "iclass")
    resultdic = {}
    mylist = list(filter(lambda x:x[:1] != "_" and x != "iclass", (dir(moduleobject))))
    for x in mylist:
        resultdic[x] = getattr(moduleobject, x)
    if iclass == "SymbolGrammar":
        from pydsl.Grammar.BNF import BNFGrammar
        return BNFGrammar(**resultdic)
    elif iclass == "PLY":
        from pydsl.Grammar.Definition import PLYGrammar
        return PLYGrammar(moduleobject)
    elif iclass == "MongoDict":
        from pydsl.Grammar.Definition import MongoGrammar
        return MongoGrammar(resultdic)
    elif iclass in ["PythonGrammar"]:
        from pydsl.Grammar.Definition import PythonGrammar
        return PythonGrammar(resultdic)
    elif iclass == "PythonTransformer":
        return resultdic
    elif iclass == "pyparsing":
        return resultdic['root_symbol']
    else:
        raise ValueError(str(moduleobject))



########NEW FILE########
__FILENAME__ = Regexp
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


"""Regular expression file parser"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2013, Nestor Arocha"
__email__ = "nesaro@gmail.com"


import re

def load_re_from_file(filepath):
    """Converts a re file to Regular Grammar instance"""
    regexp = None
    with open(filepath,'r') as mlfile:
        flagstr = ""
        for line in mlfile:
            cleanline = re.sub("//.*$", "", line)
            if re.search("^\s*$", cleanline):
                continue
            if re.search ("^#.*$", cleanline):
                flagstr = cleanline[1:]
                continue
            if regexp is not None:
                raise Exception("Regular expression file format error")
            else:
                regexp = cleanline.rstrip('\n')
    flags = 0
    if "i" in flagstr:
        flags |= re.I
    from pydsl.Grammar.Definition import RegularExpression
    return RegularExpression(regexp, flags)

########NEW FILE########
__FILENAME__ = BNF
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Production rules"""

from pydsl.Grammar.Symbol import Symbol, TerminalSymbol, NullSymbol, EndSymbol
from pydsl.Grammar.Definition import Grammar

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"


class Production(object):

    def __init__(self, leftside, rightside):
        # Left side must have at least one non terminal symbol
        for element in rightside:
            if not isinstance(element, Symbol):
                raise TypeError
        self.leftside = tuple(leftside)
        self.rightside = tuple(rightside)

    def __str__(self):
        """Pretty print"""
        leftstr = " ".join([x.name for x in self.leftside])
        rightstr = " ".join([str(x) for x in self.rightside])
        return leftstr + "::=" + rightstr

    def __eq__(self, other):
        try:
            if len(self.leftside) != len(other.leftside):
                return False
            if len(self.rightside) != len(other.rightside):
                return False
            for index in range(len(self.leftside)):
                if self.leftside[index] != other.leftside[index]:
                    return False
            for index in range(len(self.rightside)):
                if self.rightside[index] != other.rightside[index]:
                    return False
        except AttributeError:
            return False
        return True

    def __hash__(self):
        return hash(self.leftside) & hash(self.rightside)


#Only stores a ruleset, and methods to ask properties or validity check
class BNFGrammar(Grammar):

    def __init__(self, initialsymbol, fulllist, options=None):
        Grammar.__init__(self)
        self._initialsymbol = initialsymbol
        for rule in fulllist:
            if fulllist.count(rule) > 1:
                raise ValueError("Duplicated rule: " + str(rule))
        self.fulllist = tuple(fulllist)
        if not options:
            options = {}
        self.options = options

    def __hash__(self):
        return hash(self.fulllist)

    @property
    def alphabet(self):
        from pydsl.Alphabet import GrammarCollection
        return GrammarCollection([x.gd for x in self.terminal_symbols])

    @property
    def productions(self):
        return [x for x in self.fulllist if isinstance(x, Production)]

    @property
    def terminal_symbols(self):
        return [x for x in self.fulllist if isinstance(x, TerminalSymbol)]

    @property
    def first(self):
        """Returns the a grammar definition that includes all first elements of this grammar""" #TODO
        result = []
        for x in self.first_lookup(self.initialsymbol):
            result += x.first()
        if len(result) == 1:
            return result[0]
        return Choice(result)

    def first_lookup(self, symbol, size=1):
        """
        Returns a Grammar Definition with the first n terminal symbols
        produced by the input symbol
        """
        if isinstance(symbol, (TerminalSymbol, NullSymbol)):
            return [symbol.gd]
        result = []
        for production in self.productions:
            if production.leftside[0] != symbol:
                continue
            for right_symbol in production.rightside:
                if right_symbol == symbol: #Avoids infinite recursion
                    break
                current_symbol_first = self.first_lookup(right_symbol, size)
                result += current_symbol_first
                if NullSymbol not in current_symbol_first:
                    break # This element doesn't have Null in its first set so there is no need to continue
        if not result:
            raise KeyError("Symbol doesn't exist in this grammar")
        from pydsl.Grammar.PEG import Choice
        return Choice(result)

    def next_lookup(self, symbol):
        """Returns the next TerminalSymbols produced by the input symbol within this grammar definition"""
        result = []
        if symbol == self.initialsymbol:
            result.append(EndSymbol())
        for production in self.productions:
            if symbol in production.rightside:
                nextindex = production.rightside.index(symbol) + 1
                while nextindex < len(production.rightside):
                    nextsymbol = production.rightside[nextindex]
                    firstlist = self.first_lookup(nextsymbol)
                    cleanfirstlist = [x for x in firstlist if x != NullSymbol()]
                    result.append(cleanfirstlist)
                    if NullSymbol() not in firstlist:
                        break
                else:
                    result += self.next_lookup(production.leftside[0]) #reached the end of the rightside

        return result

    def __eq__(self, other):
        if not isinstance(other, BNFGrammar):
            return False
        if self._initialsymbol != other.initialsymbol:
            return False
        for index in range(len(self.productions)):
            if self.productions[index] != other.productions[index]:
                return False
        return True

    @property
    def initialsymbol(self):
        return self._initialsymbol

    @property
    def main_production(self):
        """Returns main rule"""
        for rule in self.productions:
            if rule.leftside[0] == self._initialsymbol:
                return rule
        raise IndexError

    def getProductionsBySide(self, symbol):
        result = []
        for rule in self.productions:
            if len(rule.leftside) != 1:
                continue
            if rule.leftside[0] == symbol:
                result.append(rule)
        if not result:
            raise IndexError("Symbol: %s" % str(symbol))
        return result

    def getSymbols(self):
        """Returns every symbol"""
        symbollist = []
        for rule in self.productions:
            for symbol in rule.leftside + rule.rightside:
                if symbol not in symbollist:
                    symbollist.append(symbol)
        symbollist += self.terminal_symbols
        return symbollist

    def __str__(self):
        return str(list(map(str, self.productions)))

########NEW FILE########
__FILENAME__ = Definition
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import collections

class ImmutableDict(dict):
    """A dict with a hash method"""
    def __hash__(self):
        if not self:
            return 0
        items = tuple(self.items())
        res = hash(items[0])
        for item in items[1:]:
            res ^= hash(item)
        return res

    def __setitem__(self, key, value):
        raise Exception


class Grammar(object):

    def __init__(self, base_alphabet = None):
        self.__base_alphabet = base_alphabet

    def enum(self):
        """Generates every possible accepted string"""
        raise NotImplementedError

    def first(self):# -> set:
        """Grammar definition that matches every possible first element.
        the returned value is a subset of the base_alphabet"""
        return self.alphabet

    @property
    def minsize(self):# -> int:
        """Returns the minimum size in alphabet tokens"""
        return 0

    @property
    def maxsize(self):
        """Returns the max size in alphabet tokens"""
        return None

    @property
    def alphabet(self):
        """Returns the alphabet used by this grammar"""
        if self.__base_alphabet is None:
            from pydsl.Alphabet import Encoding
            self.__base_alphabet = Encoding("ascii")
        return self.__base_alphabet

class PLYGrammar(Grammar):
    """PLY based grammar"""
    def __init__(self, module):
        Grammar.__init__(self)
        self.module = module

class RegularExpression(Grammar):
    def __init__(self, regexp, flags = 0):
        Grammar.__init__(self)
        import re
        retype = type(re.compile('hello, world'))
        if isinstance(regexp, retype):
            self.regexp = regexp
            self.regexpstr = regexp.pattern
            self.flags = regexp.flags
        elif isinstance(regexp, str):
            self.regexpstr = regexp
            self.flags = flags
            self.regexp = re.compile(regexp, flags)
        else:
            raise TypeError

    def __hash__(self):
        return hash(self.regexpstr)

    def __eq__(self, other):
        if not isinstance(other, RegularExpression):
            return False
        return self.regexpstr == other.regexpstr and self.flags == other.flags

    def __str__(self):
        return self.regexpstr

    def first(self):# -> set:
        i = 0
        while True:
            if self.regexpstr[i] == "^":
                i+=1
                continue
            if self.regexpstr[i] == "[":
                return [String(x) for x in self.regexpstr[i+1:self.regexpstr.find("]")]]
            return [String(self.regexpstr[i])]

    def __getattr__(self, attr):
        return getattr(self.regexp, attr)

class String(Grammar, str):
    def __init__(self, string):
        if isinstance(string, list):
            raise TypeError('Attempted to initialize a String with a list')
        Grammar.__init__(self)
        str.__init__(self, string)

    def first(self):
        return [String(self[0])]

    def enum(self):
        yield self

    @property
    def maxsize(self):
        return len(self)

    @property
    def minsize(self):
        return len(self)

class JsonSchema(Grammar, dict):
    def __init__(self, *args, **kwargs):
        Grammar.__init__(self)
        dict.__init__(self, *args, **kwargs)

class PythonGrammar(Grammar, dict):
    """
    A Python dictionary that defines a Grammar.
    it must define at least matchFun
    """
    def __init__(self, *args, **kwargs):
        """
        It receives a dictionary constructor which must define
        matchFun. Example: {'matchFun':<function x at 0x000000>}
        """
        Grammar.__init__(self)
        dict.__init__(self, *args, **kwargs)

    def __hash__(self):
        return hash(ImmutableDict(self))        

    @property
    def alphabet(self):
        if "alphabet" in self:
            return self['alphabet']
        from pydsl.Alphabet import Encoding
        return Encoding("ascii")

def grammar_factory(input_definition):
    if isinstance(input_definition, str):
        return String(input_definition)
    import re
    retype = type(re.compile('hello, world'))
    if isinstance(input_definition, retype):
        return RegularExpression(retype)
    if isinstance(input_definition, collections.Iterable):
        if isinstance(input_definition[0], str):
            #Return a composition grammar ([a,b] -> "a|b")
            pass
        elif isinstance(input_definition[0], collections.Iterable):
            #
            pass
    raise ValueError("Unable to create a grammar for %s" % input_definition)

########NEW FILE########
__FILENAME__ = Parsley
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

from pydsl.Grammar.Definition import Grammar
from pydsl.Check import checker_factory

__author__ = "Ptolom"
__copyright__ = "Copyright 2014, Ptolom"
__email__ = "ptolom@hexifact.co.uk"

class ParsleyGrammar(Grammar):
    def __init__(self, rules, root_rule, repository={}):
        import parsley
        Grammar.__init__(self)
        repo={}
        for k, v in repository.items():
            repo[k]=(v, checker_factory(v))[isinstance(v, Grammar)]
        self.grammar=parsley.makeGrammar(rules, repo)
        self.root_rule=root_rule 
    def match(self, data):
        return getattr(self.grammar(data), self.root_rule)() #call grammar(data).root_rule()

########NEW FILE########
__FILENAME__ = PEG
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

"""

Parser expression grammars

Loosely based on pymeta

https://launchpad.net/pymeta

See also http://en.wikipedia.org/wiki/Parsing_expression_grammar

"""

from .Definition import Grammar
from pydsl.Alphabet import GrammarCollection

class ZeroOrMore(Grammar):
    def __init__(self, element):
        Grammar.__init__(self)
        self.element = element

    def first(self):
        return Choice([self.element])


class OneOrMore(Grammar):
    def __init__(self, element):
        Grammar.__init__(self)
        self.element = element

    def first(self):
        return Choice([self.element])

class Sequence(Grammar, list):
    def __init__(self, *args, **kwargs):
        base_alphabet = kwargs.pop('base_alphabet', None)
        Grammar.__init__(self, base_alphabet)
        list.__init__(self, *args, **kwargs)

class Choice(GrammarCollection, Grammar):
    """Uses a list of grammar definitions with common base alphabets"""
    def __init__(self, grammarlist):
        GrammarCollection.__init__(self, grammarlist)
        base_alphabet_list = []
        for x in self:
            if not isinstance(x, Grammar):
                raise TypeError("Expected Grammar, Got %s:%s" % (x.__class__.__name__,x))
            if x.alphabet not in base_alphabet_list:
                base_alphabet_list.append(x.alphabet)
        if len(base_alphabet_list) != 1:
            raise ValueError('Different base alphabets from members %s' % base_alphabet_list)
        Grammar.__init__(self, base_alphabet_list[0])

    def __str__(self):
        return str([str(x) for x in self])

    def __add__(self, other):
        return Choice(GrammarCollection.__add__(self,other))

class Optional(object):
    def __init__(self, element):
        Grammar.__init__(self)
        self.element = element

class Not(object):
    def __init__(self, element):
        self.element = element

class And(object):
    def __init__(self, element):
        Grammar.__init__(self)
        self.element = element


########NEW FILE########
__FILENAME__ = Symbol
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Symbols"""
from pydsl.Check import check

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)
from pydsl.Grammar.Definition import Grammar, String

class Symbol(object):
    def __init__(self, weight):
        self._weight = weight

    @property
    def weight(self):
        return self._weight

class NonTerminalSymbol(Symbol):
    def __init__(self, name,  weight = 50):
        Symbol.__init__(self, weight)
        self.name = name

    def __str__(self):
        return "<NonTS: " + self.name + ">"

    def __hash__(self):
        return hash(self.name) ^ hash(self.weight)

    def __eq__(self, other):
        if not isinstance(other, NonTerminalSymbol):
            return False
        return self.name == other.name and self.weight == other.weight

    def __ne__(self, other):
        return not self.__eq__(other)


class TerminalSymbol(Symbol):

    def __init__(self, gd, weight=None, boundariesrules=None):
        if not isinstance(gd, Grammar):
            raise TypeError
        if isinstance(gd, String):
            weight = weight or 99
            boundariesrules = len(gd)
        else:
            weight = weight or 49
        Symbol.__init__(self, weight)
        if boundariesrules not in ("min", "max", "any") and not isinstance(boundariesrules, int):
            raise TypeError("Unknown boundaries rules %s" % boundariesrules)
        if not gd:
            raise Exception
        self.gd = gd
        self.boundariesrules = boundariesrules

    def __hash__(self):
        return hash(self.gd) ^ hash(self.boundariesrules)

    def check(self, data):# ->bool:
        """Checks if input is recognized as this symbol"""
        return check(self.gd, data)

    def first(self):
        return self.gd.first

    def __eq__(self, other):
        """StringTerminalSymbol are equals if definition and names are equal"""
        try:
            return self.gd == other.gd and self.boundariesrules == other.boundariesrules
        except AttributeError:
            return False

    def __str__(self):
        return "<TS: " + str(self.gd) + ">"

class NullSymbol(Symbol):
    def __init__(self):
        Symbol.__init__(self, 100)

    def __eq__(self, other):
        return isinstance(other, NullSymbol)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        return False

class EndSymbol(Symbol):
    def __init__(self):
        Symbol.__init__(self, 100)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return isinstance(other, EndSymbol)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        return False

    def __str__(self):
        return "$"

########NEW FILE########
__FILENAME__ = Guess
#!/usr/bin/python
# -*- coding: utf-8 -*-

#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


""" guess which types are the input data.  """

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)
from pydsl.Check import check

class Guesser(object):
    """Returns every grammar and alphabet definition that matches the input"""
    def __init__(self, grammarlist):
        self.grammarlist = grammarlist

    def __call__(self, data):
        result = []
        for gd in self.grammarlist:
            if check(gd, data):
                result.append(gd)
        return result

def guess(grammarlist, data):
    return Guesser(grammarlist)(data)

########NEW FILE########
__FILENAME__ = Lex
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Lexer classes. Receives and input sequences and returns a list of Tokens"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

from pydsl.Grammar.PEG import Choice
from pydsl.Alphabet import Encoding, GrammarCollection
from pydsl.Check import checker_factory
from pydsl.Token import Token, PositionToken
from pydsl.Tree import PositionResultList


class EncodingLexer(object):

    """Special Lexer that encodes from a string a reads a string"""

    def __init__(self, encoding):
        self.encoding = encoding

    def __call__(self, string): #TODO! make all the lexers work the same
        for x in string:
            yield Token(x, None)


#A1 A2
#|  |
#A3 A4
#|  |
#A5 |
#\  /
# A6

#Order is not always unique, as in the previous example A4 could be extracter after or before A3. At the moment the algorithm is to compute elements of the longest path first (extract elements from longest path every single time)


#Check that every element in the input belongs to base

#Call the lexers following the graph


#TODO: test
def graph_from_alphabet(alphabet, base):
    """Creates a graph that connects the base with the target through alphabets
    If every target is connected to any inputs, create the independent paths"""
    from pydsl.Alphabet import Alphabet
    if not isinstance(alphabet, Alphabet):
        raise TypeError(alphabet.__class__.__name__)
    if not isinstance(base, Alphabet):
        raise TypeError(base.__class__.__name__)
            
    import networkx
    result = networkx.DiGraph()
    current_alphabet = alphabet
    if isinstance(current_alphabet, GrammarCollection):
        pending_stack = list(current_alphabet)
    else:
        pending_stack = [current_alphabet]
    while pending_stack:
        current_alphabet = pending_stack.pop()
        if isinstance(current_alphabet, Encoding) or \
                (isinstance(current_alphabet, GrammarCollection) and current_alphabet in base):
            continue
        if isinstance(current_alphabet, GrammarCollection):
            for element in current_alphabet:
                result.add_edge(current_alphabet, element)
                result.add_edge(element, element.alphabet)
                pending_stack.append(element.alphabet)
        else: #A Grammar
            result.add_edge(current_alphabet, current_alphabet.alphabet)
            pending_stack.append(current_alphabet.alphabet)
    #print_graph(result)
    return result

def print_graph(result):
    import networkx
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8,8))
    # with nodes colored by degree sized by population
    networkx.draw(result, with_labels=True)
    plt.savefig("knuth_miles.png")

class GeneralLexer(object):
    """Multi level lexer"""
    def __init__(self, alphabet, base):
        from pydsl.Alphabet import Alphabet
        if not isinstance(alphabet, Alphabet):
            raise TypeError
        if not alphabet:
            raise ValueError
        if not base:
            raise ValueError
        self.alphabet = alphabet
        self.base = base


    def __call__(self, data, include_gd=False):
        if isinstance(self.base, Encoding):
            data = [x for x in EncodingLexer(self.base)(data)]
            from pydsl.Token import append_position_to_token_list
            data = append_position_to_token_list(data)
        for element in data:
            from pydsl.Check import check
            if not check(self.base, element):
                raise ValueError('Unexpected input grammar')
        graph = graph_from_alphabet(self.alphabet, self.base)
        solved_elements = {}
        graph.node[self.base]['parsed'] = data #Attach data to every element in the graph
        digraph_walker_backwards(graph, self.base, my_call_back)
        result = []
        for output_alphabet in self.alphabet:
            if output_alphabet not in graph.node or 'parsed' not in graph.node[output_alphabet]:
                raise Exception("alphabet not initialized:%s" % output_alphabet)
            for token in graph.node[output_alphabet]['parsed']:
                #This step needs to flat the token so it matches the signature of the function (base -> alphabet)
                def flat_token(token):
                    while hasattr(token, 'content'):
                        token = token.content
                    return token
                result.append(PositionToken(flat_token(token), output_alphabet, token.left, token.right))
        result = sorted(result, key=lambda x: x.left)
        result = remove_subsets(result)
        result = remove_duplicates(result)
        return [Token(x.content, x.gd) for x in result]


def is_subset(a, b):
    """Excluding same size"""
    return b.left <= a.left and b.right > a.right or b.left < a.left and b.right >= a.right 

def remove_subsets(ptoken_list):
    result = []
    for ptoken in ptoken_list:
        if not any((is_subset(ptoken, x) for x in ptoken_list)):
            result.append(ptoken)
    return result

def remove_duplicates(ptoken_list):
    result = []
    for x in ptoken_list:
        for y in result:
            if x.content == y.content and x.left == y.left and x.right == y.right: #ignores GD
                break
        else:
            result.append(x)
    return result

def my_call_back(graph, element):
    gne = graph.node[element]
    if 'parsed' in gne:
        return  # Already parsed
    flat_list = []
    for successor in graph.successors(element):
        if successor not in graph.node or 'parsed' not in graph.node[successor]:
            raise Exception("Uninitialized graph %s" % successor)
        for string, gd, left, right in graph.node[successor]['parsed']:
            flat_list.append(PositionToken(string, gd, left, right))
    sorted_flat_list = sorted(flat_list, key=lambda x: x.left) #Orders elements from all sucessors
    sorted_flat_list = remove_subsets(sorted_flat_list)
    lexed_list = []
    prev_right = 0
    for string, gd, left, right in sorted_flat_list:
        if prev_right != left:
            raise Exception("Non contiguous parsing from sucessors")
        prev_right = right
        lexed_list.append(Token(string, gd))
    from pydsl.Extract import extract
    gne['parsed'] = extract(element, lexed_list)



def digraph_walker_backwards(graph, element, call_back):
    """Visits every element guaranteeing that the previous elements have been visited before"""
    call_back(graph, element)
    for predecessor in graph.predecessors(element):
        call_back(graph, predecessor)
    for predecessor in graph.predecessors(element):
        digraph_walker_backwards(graph, predecessor, call_back)



class ChoiceLexer(object):

    """Lexer receives an Alphabet in the initialization (A1).
    Receives an input that belongs to A1 and generates a list of tokens in a different Alphabet A2
    It is always described with a regular grammar"""

    def __init__(self, alphabet):
        self.load(None)
        self.alphabet = alphabet

    def load(self, string):
        self.string = string
        self.index = 0

    def __call__(self, string, include_gd=True):  # -> "TokenList":
        """Tokenizes input, generating a list of tokens"""
        self.load(string)
        result = []
        while True:
            try:
                result.append(self.nextToken(include_gd))
            except:
                break
        return result

    def nextToken(self, include_gd=False):
        best_right = 0
        best_gd = None
        for gd in self.alphabet:
            checker = checker_factory(gd)
            left = self.index
            for right in range(left +1, len(self.string) +1):
                if checker.check(self.string[left:right]): #TODO: Use match
                    if right > best_right:
                        best_right = right
                        best_gd = gd
        if not best_gd:
            raise Exception("Nothing consumed")
        if include_gd:
            result = self.string[self.index:best_right], best_gd
        else:
            result = self.string[self.index:best_right]
        self.index = right
        return result


class ChoiceBruteForceLexer(object):

    """Attempts to generate the smallest token sequence by evaluating every accepted sequence"""

    def __init__(self, alphabet):
        self.alphabet = alphabet

    @property
    def current(self):
        """Returns the element under the cursor until the end of the string"""
        return self.string[self.index:]

    def __call__(self, string, include_gd=True):  # -> "TokenList":
        """Tokenizes input, generating a list of tokens"""
        self.string = string
        return [x for x in self.nextToken(include_gd)]

    def nextToken(self, include_gd=False):
        tree = PositionResultList()  # This is the extract algorithm
        valid_alternatives = []
        for gd in self.alphabet:
            checker = checker_factory(gd)
            for left in range(0, len(self.string)):
                for right in range(left +1, len(self.string) +1 ):
                    if checker.check(self.string[left:right]):
                        valid_alternatives.append((left, right, gd))
        if not valid_alternatives:
            raise Exception("Nothing consumed")
        for left, right, gd in valid_alternatives:
            string = self.string[left:right]
            tree.append(left, right, string, gd, check_position=False)

        right_length_seq = []
        for x in tree.valid_sequences():
            if x[-1]['right'] == len(self.string):
                right_length_seq.append(x)
        if not right_length_seq:
            raise Exception("No sequence found for input %s alphabet %s" % (self.string,self.alphabet))
        for y in sorted(right_length_seq, key=lambda x:len(x))[0]: #Always gets the match with less tokens
            if include_gd:
                yield Token(y['content'], y.get('gd'))
            else:
                yield Token(y['content'], None)

def lexer_factory(alphabet, base = None):
    if isinstance(alphabet, Choice) and alphabet.alphabet == base:
        return ChoiceBruteForceLexer(alphabet)
    elif isinstance(alphabet, Encoding):
        if base is not None:
            raise ValueError
        return EncodingLexer(alphabet)
    else:
        if base is None:
            base = Encoding('ascii')
        return GeneralLexer(alphabet, base)

def lex(alphabet, base, data):
    return lexer_factory(alphabet, base)(data)

def common_ancestor(alphabet):
    """Discovers the alphabet common to every element in the input"""
    expanded_alphabet_list = []
    for gd in alphabet:
        expanded_alphabet_list_entry = []
        from pydsl.Alphabet import Alphabet
        if isinstance(gd, Alphabet):
            expanded_alphabet_list_entry.append(gd)
        current_alphabet = gd.alphabet
        while current_alphabet is not None:
            expanded_alphabet_list_entry.append(current_alphabet)
            current_alphabet = getattr(current_alphabet,"alphabet", None)
        expanded_alphabet_list.append(expanded_alphabet_list_entry)
    flat_alphabet_list = []
    for entry in expanded_alphabet_list:
        for alphabet in entry:
            if alphabet not in flat_alphabet_list:
                flat_alphabet_list.append(alphabet)
    common_alphabets = [x for x in flat_alphabet_list if all((x in y for y in expanded_alphabet_list))]
    if not common_alphabets:
        return None
    if len(common_alphabets) != 1:
        raise NotImplementedError("Expected only one common ancestor, got %s " % str(common_alphabets))
    return common_alphabets[0]

def is_ancestor(parent_alphabet, child_alphabet):
    """Tests if parent_alphabet is an ancestor of the child_alphabet"""
    alphabet = parent_alphabet
    while alphabet:
        if child_alphabet == alphabet:
            return True
        alphabet = alphabet.alphabet
    return False

########NEW FILE########
__FILENAME__ = Backtracing
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Recursive descent parser"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)
from .Parser import TopDownParser
from pydsl.Tree import ParseTree, PositionResultList
from pydsl.Check import check


class BacktracingErrorRecursiveDescentParser(TopDownParser):
    """Recursive descent parser implementation. Backtracing. Null support. Error support"""
    def get_trees(self, data, showerrors = False): # -> list:
        """ returns a list of trees with valid guesses """
        for element in data:
            if not check(self._productionset.alphabet,element):
                raise ValueError("Unknown element %s" % str(element))
        result = self.__recursive_parser(self._productionset.initialsymbol, data, self._productionset.main_production, showerrors)
        finalresult = []
        for eresult in result:
            if eresult.left == 0 and eresult.right == len(data) and eresult not in finalresult:
                finalresult.append(eresult)        
        return finalresult

    def __recursive_parser(self, onlysymbol, data, production, showerrors = False):
        """ Aux function. helps check_word"""
        LOG.debug("__recursive_parser: Begin ")
        if not data:
            return []
        from pydsl.Grammar.Symbol import TerminalSymbol, NullSymbol, NonTerminalSymbol
        if isinstance(onlysymbol, TerminalSymbol):
            LOG.debug("Iteration: terminalsymbol")
            return self._reduce_terminal(onlysymbol,data[0], showerrors)
        elif isinstance(onlysymbol, NullSymbol):
            return [ParseTree(0, 0, onlysymbol, "")]
        elif isinstance(onlysymbol, NonTerminalSymbol):
            validstack = []
            invalidstack = []
            for alternative in self._productionset.getProductionsBySide(onlysymbol): #Alternative
                alternativetree = PositionResultList()
                alternativeinvalidstack = []
                for symbol in alternative.rightside: # Symbol
                    symbol_success = False
                    for totalpos in alternativetree.right_limit_list(): # Right limit
                        if totalpos >= len(data):
                            continue
                        thisresult =  self.__recursive_parser(symbol, data[totalpos:], alternative, showerrors)
                        if thisresult and all(thisresult):
                            symbol_success = True
                            for x in thisresult:
                                x.shift(totalpos)
                                success = alternativetree.append(x.left, x.right, x)
                                if not success:
                                    #TODO: Add as an error to the tree or to another place
                                    LOG.debug("Discarded symbol :" + str(symbol) + " position:" + str(totalpos))
                                else:
                                    LOG.debug("Added symbol :" + str(symbol) + " position:" + str(totalpos))
                        else:
                            alternativeinvalidstack += [x for x in thisresult if not x]

                    if not symbol_success:
                        LOG.debug("Symbol doesn't work" + str(symbol))
                        break #Try next alternative
                else: # Alternative success (no break happened)
                    invalidstack += alternativeinvalidstack
                for x in alternativetree.valid_sequences():
                    validstack.append(x)
            result = []

            LOG.debug("iteration result collection finished:" + str(validstack))
            for alternative in self._productionset.getProductionsBySide(onlysymbol):
                nullcount = alternative.rightside.count(NullSymbol())
                for results in validstack:
                    nnullresults = 0
                    left = results[0]['left']
                    right = results[-1]['right']
                    nnullresults = len([x for x in results if x['content'].symbol == NullSymbol()])
                    if len(results) - nnullresults != len(alternative.rightside) - nullcount:
                        LOG.debug("Discarded: incorrect number of non null symbols")
                        continue
                    if right > len(data):
                        LOG.debug("Discarded: length mismatch")
                        continue
                    for x in range(min(len(alternative.rightside), len(results))):
                        if results[x]['content'] != alternative.rightside[x]:
                            LOG.debug("Discarded: rule doesn't match partial result")
                            continue
                    childlist = [x['content'] for x in results]
                    allvalid = all([x.valid for x in childlist])
                    if allvalid:
                        newresult = ParseTree(0, right - left, onlysymbol,
                                data[left:right], childlist = childlist)
                        newresult.valid = True
                        result.append(newresult)
            if showerrors and not result:
                erroresult = ParseTree(0,len(data), onlysymbol , data, valid = False)
                for invalid in invalidstack:
                    if invalid.content in production.rightside:
                        erroresult.append_child(invalid)
                return [erroresult]
            return result
        raise Exception("Unknown symbol:" + str(onlysymbol))

########NEW FILE########
__FILENAME__ = LL
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""LL family parsers"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"
from pydsl.Check import check
from pydsl.Parser.Parser import TopDownParser
from pydsl.Tree import ParseTree
from pydsl.Exceptions import ParseError
import logging
LOG = logging.getLogger(__name__)



class LL1RecursiveDescentParser(TopDownParser):
    def get_trees(self, data, showerrors = False): # -> list:
        """ returns a list of trees with valid guesses """
        if showerrors:
            raise NotImplementedError("This parser doesn't implement errors")
        self.data = data
        self.index = 0
        try:
            return [self.__aux_parser(self._productionset.initialsymbol)]
        except (IndexError, ParseError):
            return []

    def __aux_parser(self, symbol):
        from pydsl.Grammar.Symbol import TerminalSymbol
        if isinstance(symbol, TerminalSymbol):
            LOG.debug("matching symbol %s, data:%s, index:%s" % (symbol,self.data,self.index ))
            result= self.match(symbol)
            LOG.debug("symbol matched %s" % result)
            return result
        productions = self._productionset.getProductionsBySide(symbol)
        valid_firsts = []
        for production in productions:
            first_of_production = self._productionset.first_lookup(production.rightside[0])
            if check(first_of_production, self.current):
                valid_firsts.append(production)
        if len(valid_firsts) != 1:
            raise ParseError("Expected only one valid production, found %s" % len(valid_firsts), 0)
        childlist = []
        for element in valid_firsts[0].rightside:
            childlist.append(self.__aux_parser(element))
        left = childlist[0].left
        right = childlist[-1].right
        content = [x.content for x in childlist]
        return ParseTree(left, right, symbol, content, childlist=childlist)


    def consume(self):
        self.index +=1
        if self.index > len(self.data):
            raise IndexError("Attempted to consume index %s of data %s" % (self.index, self.data))

    @property
    def current(self):
        result = self.data[self.index]
        return result

    def match(self, symbol):
        if symbol.check(self.current):
            current = self.current
            self.consume()
            return ParseTree(self.index-1, self.index, symbol, current)
        else:
            raise Exception("Not matched")

########NEW FILE########
__FILENAME__ = LR0
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""SLR0 implementation"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)
from pydsl.Parser.Parser import BottomUpParser
from pydsl.Grammar.Symbol import NonTerminalSymbol, TerminalSymbol, EndSymbol, Symbol
from pydsl.Grammar.BNF import Production

Extended_S = NonTerminalSymbol("EI")

def _build_item_closure(itemset, productionset):
    """Build input itemset closure """
    #For every item inside current itemset, if we have the following rule:
    #  xxx <cursor><nonterminalSymbol> xxx  append every rule from self._productionruleset that begins with that NonTerminalSymbol
    if not isinstance(itemset, LR0ItemSet):
        raise TypeError
    import copy
    resultset = copy.copy(itemset)
    changed = True
    while changed:
        changed = False
        for currentitem in resultset.itemlist:
            nextsymbol = currentitem.next_symbol()
            if nextsymbol is None:
                break
            for rule in productionset.productions:
                newitem = LR0Item(rule)
                if rule.leftside[0] == nextsymbol and newitem not in resultset.itemlist:
                    resultset.append_item(newitem)
                    changed = True
    return resultset

def item_set_goto(itemset, inputsymbol, productionset):
    """returns an itemset
    locate inside itemset every element with inputsymbol following cursor
    for every located item, append its itemclosure"""
    resultset = LR0ItemSet()
    for item in itemset.itemlist:
        if item.next_symbol() == inputsymbol:
            newitem = LR0Item(item.rule, item.position + 1)
            resultset.append_item(newitem)
    return _build_item_closure(resultset, productionset)

def build_states_sets(productionset):
    symbollist = productionset.getSymbols() + [EndSymbol()]
    mainproductionrule =  Production([Extended_S] , [productionset.initialsymbol, EndSymbol()])
    mainproductionruleitem = LR0Item(mainproductionrule)
    mainproductionruleitemset = LR0ItemSet()
    mainproductionruleitemset.append_item(mainproductionruleitem)
    index0 = _build_item_closure(mainproductionruleitemset, productionset)
    LOG.debug("buildStatesSets: mainsymbol closure: " + str(index0))
    result = [index0]
    changed = True
    #returns a set of itemsets
    while changed:
        changed = False
        for itemset in result[:]:
            for symbol in symbollist:
                if itemset.has_transition(symbol): #FIXME a symbol in a LR0item list?
                    continue
                newitemset = item_set_goto(itemset, symbol, productionset)
                if newitemset in result and itemset.has_transition(symbol) and itemset.get_transition(symbol) != newitemset:
                    changed = True
                    itemset.append_transition(symbol, newitemset)
                elif newitemset in result and not itemset.has_transition(symbol):
                    changed = True
                    itemset.append_transition(symbol, newitemset)
                elif newitemset and newitemset not in result: #avoid adding a duplicated entry
                    changed = True
                    result.append(newitemset)
                    itemset.append_transition(symbol, newitemset)
    return result

def _slr_build_parser_table(productionset):
    """SLR method to build parser table"""
    result = ParserTable()
    statesset = build_states_sets(productionset)
    for itemindex, itemset in enumerate(statesset):
        LOG.debug("_slr_build_parser_table: Evaluating itemset:" + str(itemset))
        for symbol in productionset.getSymbols() + [EndSymbol()]:
            numberoptions = 0
            for lritem in itemset.itemlist:
                #if cursor is before a terminal, and there is a transition to another itemset with the following terminal, append shift rule
                if isinstance(symbol, TerminalSymbol) and lritem.next_symbol() == symbol and itemset.has_transition(symbol):
                    destinationstate = statesset.index(itemset.get_transition(symbol))
                    result.append(itemindex, symbol, "Shift", destinationstate)
                    numberoptions += 1
                if isinstance(symbol, NonTerminalSymbol) and lritem.next_symbol() == symbol and itemset.has_transition(symbol):
                    destinationstate = statesset.index(itemset.get_transition(symbol))
                    result.append_goto(itemindex, symbol, destinationstate)
                #if cursor is at the end of the rule, then append reduce rule and go transition
                if lritem.previous_symbol() == symbol and lritem.is_last_position() and symbol != Extended_S:
                    for x in productionset.next_lookup(symbol):
                        from pydsl.Grammar.Definition import String
                        if isinstance(x, list):
                            result.append(itemindex, TerminalSymbol(String(x[0])), "Reduce", None, lritem.rule)
                        else:
                            result.append(itemindex, TerminalSymbol(String(x)), "Reduce", None, lritem.rule)
                    numberoptions += 1
                #if cursor is at the end of main rule, and current symbol is end, then append accept rule
                if isinstance(symbol, EndSymbol) and lritem.previous_symbol() == productionset.initialsymbol and lritem.next_symbol() == EndSymbol():
                    result.append(itemindex, symbol, "Accept", None)
                    numberoptions += 1
            if not numberoptions:
                LOG.info("No rule found to generate a new parsertable entry ")
                LOG.debug("symbol: " + str(symbol))
                LOG.debug("itemset: " + str(itemset))
            elif numberoptions > 1: #FIXME can it count duplicated entries?
                raise Exception("LR Conflict %s" % symbol)
    return result
    
class ParserTable(dict):
    """ Stores a state/symbol/action/new state relation """
    #Default for every state: Fail state #FIXME use default_dict

    def append(self, state, symbol, action, destinationstate, production = None):
        """Appends a new rule"""
        if action not in (None, "Accept", "Shift", "Reduce"):
            raise TypeError
        if not state in self:
            self[state] = {}
        rule = {"action":action, "dest":destinationstate}
        if action == "Reduce":
            if rule is None:
                raise TypeError("Expected production parameter")
            rule["rule"] = production
        if isinstance(symbol, list) and len(symbol) == 1:
            symbol = symbol[0]
        if not isinstance(symbol, Symbol):
            raise TypeError("Expected symbol, got %s" % symbol)
        self[state][symbol] = rule

    def append_goto(self, state, symbol, destinationstate):
        if not state in self:
            self[state] = {}
        if symbol in self[state] and self[state][symbol] != destinationstate:
            raise Exception
        self[state][symbol] = destinationstate

    def goto(self, state, symbol):
        return self[state][symbol]

    def insert(self, state, token):
        """change internal state, return action"""
        for symbol in self[state]:
            from pydsl.Check import check
            if symbol == EndSymbol() or isinstance(symbol, TerminalSymbol) and check(symbol.gd,token):
                break
        else:
            if token != EndSymbol():
                return {"action":"Fail"}
            else:
                symbol = EndSymbol()
        try:
            return self[state][symbol]
        except KeyError:
            return {"action":"Fail"}



class LR0Item(object):
    """LR0 table item"""
    def __init__(self, rule, position = 0):
        if not isinstance(rule, Production):
            raise TypeError
        if position > len(rule.rightside):
            raise ValueError("Position is outside the rule")
        self.rule = rule
        self.position = position

    def __str__(self):
        rscopy = [str(x) for x in self.rule.rightside]
        rscopy.insert(self.position, ".")
        return str([str(x) for x in self.rule.leftside]) + ": " + str(rscopy) 

    def __eq__(self, other):
        if not isinstance(other, LR0Item):
            return False
        return self.position == other.position and self.rule == other.rule

    def previous_symbol(self):
        """returns cursor's previous symbol"""
        if self.position == 0:
            return None
        return self.rule.rightside[self.position-1]

    def next_symbol(self):
        """returns the symbol located after cursor"""
        try:
            return self.rule.rightside[self.position]
        except IndexError:
            return None

    def is_last_position(self):
        """Returns true if cursor if after last element"""
        return self.position >= len(self.rule.rightside)

class LR0ItemSet(object):
    """Stores LR0Items, and a dic with symbols and destination states"""
    def __init__(self):
        self.itemlist = []
        self.transitions = {}

    def __str__(self):
        result = "<LR0ItemSet: \n"
        for item in self.itemlist:
            result += str(item) + ","
        if self.transitions:
            result += "transitions:" + str([str(x) + str(y) for (x,y) in self.transitions.items()])
        result += ">"
        return result

    def __bool__(self):
        return bool(self.itemlist)

    def __nonzero__(self):
        return self.__bool__()

    def __eq__(self, anotherset):
        """Tests on itemlist equality"""
        if not isinstance(anotherset, LR0ItemSet):
            raise TypeError
        if len(self.itemlist) != len(anotherset.itemlist):
            return False
        for element in self.itemlist:
            if element not in anotherset.itemlist:
                return False
        return True

    def append_item(self, item):
        """Append new item to set"""
        if not isinstance(item, LR0Item):
            raise TypeError
        self.itemlist.append(item)

    def append_transition(self, symbol, targetset):
        """Appends a transition"""
        if symbol in self.transitions:
            return
        self.transitions[symbol] = targetset

    def has_transition(self, symbol):
        return symbol in self.transitions

    def get_transition(self, symbol):
        """gets a transition"""
        return self.transitions[symbol]

class LR0Parser(BottomUpParser):
    """LR0 bottomup parser. Not finished"""
    def __init__(self, productionset):
        #TODO: Build extended productionset before calling parent constructor
        BottomUpParser.__init__(self, productionset)
        #Add main item to itemsclosure with cursor at 0 position
        self.__parsertable = _slr_build_parser_table(productionset)
        #build GoTo and Action Table from ProductionRuleSet

    def get_trees(self, tokenlist):
        try:
            return self.__parse(tokenlist)
        except IndexError:
            return False

    def __parse(self, tokenlist):
        """see parent docstring"""
        #empty stack
        #iterate over symbollist
        tokenlist = [x for x in tokenlist]
        if not isinstance(tokenlist, list):
            raise TypeError("Expected list, got %s" % tokenlist.__class__.__name__)
        LOG.debug("get_trees: checking list: " + str(tokenlist))
        stack = [(0, Extended_S)]
        while True:
            state = stack[-1][0]
            if len(tokenlist):#FIXME: tokenlist with one element is reported as false
                token = tokenlist[0]
            else:
                token = EndSymbol()
            newdic = self.__parsertable.insert(state, token)
            action = newdic["action"]
            if action == "Fail":
                return False
            elif action == "Accept":
                return True
            if action == "Reduce":
                reductionrule = newdic["rule"]
                #TODO extract len(right side) of the rule and insert left side
                for rsymbol in reversed(reductionrule.rightside):
                    state, symbol = stack.pop() # TODO: check
                state = stack[-1][0]
                state = self.__parsertable.goto(state,reductionrule.leftside[0])
                stack.append((state, reductionrule.leftside[0]))
            elif action == "Shift":
                stack.append((newdic['dest'], tokenlist.pop(0)))
            else:
                raise ValueError("Unknown action")
        return False


########NEW FILE########
__FILENAME__ = Parser
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Parser module"""
from pydsl.Lex import lexer_factory

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)


class Parser(object):
    """Expands an input based on grammar rules
    At this time, all parsers are tree based"""
    def get_trees(self, word): # -> list:
        """ returns a ParseTree list with all guesses """
        raise NotImplementedError

    def __call__(self, word):
        return self.get_trees(word)

    @property
    def productionset(self):
        """returns productionset"""
        return self._productionset

class TopDownParser(Parser):
    """Top down parser like descent parser"""
    def __init__(self, bnfgrammar):
        self._productionset = bnfgrammar

    def _reduce_terminal(self, symbol, data, showerrors = False):
        from pydsl.Check import check
        from pydsl.Tree import ParseTree
        result = check(symbol.gd, data)
        if result:
            return [ParseTree(0,1, symbol , data)]
        if showerrors and not result:
            return [ParseTree(0,1, symbol , data, valid = False)]
        return []

class BottomUpParser(Parser):
    """ leaf to root parser"""
    def __init__(self, bnfgrammar):
        self._lexer = lexer_factory(bnfgrammar.alphabet)
        self._productionset = bnfgrammar


def parser_factory(grammar, parser = None):
    from pydsl.Grammar.BNF import BNFGrammar
    if isinstance(grammar, BNFGrammar):
        if parser in ("auto" , "default" , "descent", None):
            from pydsl.Parser.Backtracing import BacktracingErrorRecursiveDescentParser
            return BacktracingErrorRecursiveDescentParser(grammar)
        elif parser == "lr0":
            from pydsl.Parser.LR0 import LR0Parser
            return LR0Parser(grammar)
        elif parser == "ll1":
            from pydsl.Parser.LL import LL1RecursiveDescentParser
            return LL1RecursiveDescentParser(grammar)
        else:
            raise Exception("Wrong parser name: " + str(parser))
    else:
        raise ValueError(grammar)


def parse(definition, data, parser = "auto"):
    return parser_factory(definition, parser)(data)

########NEW FILE########
__FILENAME__ = PEG

#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

from pydsl.Parser.Parser import Parser

class PEGParser(Parser):
    def __init__(self, gd):
        self.gd = gd

    def get_trees(self, data):
        pass

########NEW FILE########
__FILENAME__ = Token
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Token classes"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

from pydsl.Check import checker_factory
from collections import namedtuple

Token = namedtuple('Token', ('content','gd'))
PositionToken = namedtuple('PositionToken', ('content','gd','left','right'))


def append_position_to_token_list(token_list):
    """Converts a list of Token into a list of PositionToken, asuming size == 1"""
    return [PositionToken(value.content, value.gd, index, index+1) for (index, value) in enumerate(token_list)]

########NEW FILE########
__FILENAME__ = Translator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Python Transformers"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)

class PythonTranslator(object):
    """ Python function based translator """
    def __init__(self, inputdic, outputdic, function):
        self._function = function
        self.inputchanneldic = inputdic
        self.outputchanneldic = outputdic

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

class PLYTranslator(object):
    def __init__(self, grammardefinition):
        self.module = grammardefinition.module

    def __call__(self, input):
        from ply import yacc, lex
        lexer = lex.lex(self.module)
        parser = yacc.yacc(debug=0, module = self.module)
        return parser.parse(input, lexer = lexer)

class PyParsingTranslator(object):
    def __init__(self, root_symbol):
        self.root_symbol = root_symbol

    def __call__(self, input):
        return self.root_symbol.parseString(input)

class ParsleyTranslator(object):
    def __init__(self, grammar):
        self.g=grammar
    def __call__(self, input):
        return self.g.match(input)


def translator_factory(function):
    from pydsl.Grammar.Definition import PLYGrammar
    from pydsl.Grammar.Parsley import ParsleyGrammar
    if isinstance(function, PLYGrammar):
        return PLYTranslator(function)
    if isinstance(function, ParsleyGrammar):
        return ParsleyTranslator(function)
    if isinstance(function, dict):
        return PythonTranslator(**function)
    from pyparsing import OneOrMore
    if isinstance(function, OneOrMore):
        return PyParsingTranslator(function)
    if isinstance(function, PythonTranslator):
        return function
    raise ValueError(function)

def translate(definition, data):
    return translator_factory(definition)(**data)

########NEW FILE########
__FILENAME__ = Tree
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Tree class for tree based parsers"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import logging
LOG = logging.getLogger(__name__)


class ParseTree(object):

    """Stores the position of the original tree"""

    def __init__(self, left, right, symbol, content, childlist=None, valid=True):
        self.symbol = symbol
        if not isinstance(left, int) and left is not None:
            raise TypeError
        if not isinstance(right, int) and right is not None:
            raise TypeError
        if not childlist:
            childlist = []
        self.childlist = childlist
        self.left = left
        self.right = right
        self.content = content
        self.valid = valid

    def __eq__(self, other):
        try:
            return self.left == other.left and self.right == other.right and self.valid == other.valid and self.content == other.content 
        except AttributeError:
            return False

    def __bool__(self):
        """checks if it is a null result"""
        return self.valid

    def __nonzero__(self):
        return self.__bool__()

    def shift(self, amount):
        """ shifts position """
        if self.left is not None:
            self.left += amount
        if self.left is not None:
            self.right += amount

    def __len__(self):
        if self.right is None and self.left is None:
            return 0
        return self.right - self.left

    def append(self, dpr):
        """appends dpr to childlist"""
        self.childlist.append(dpr)


class PositionResultList(object):
    """Contains a list of results"""
    def __init__(self):
        self.possible_items = []

    @property
    def current_right(self):
        if not self.possible_items:
            return set([0])
        return set(x['right'] for x in self.possible_items)

    def append(self, left, right, content, gd = None, check_position=True):
        if left > right:
            raise ValueError('Attempted to add negative length alement')
        if check_position == True and left:
            if left not in self.current_right:
                raise ValueError("Unable to add element")
        result = {'left':left, 'right':right, 'content':content}
        if gd:
            result['gd'] = gd
        self.possible_items.append(result)

    def valid_sequences(self):
        """Returns list"""
        valid_sets = [[x] for x in self.possible_items if x['left'] == 0]
        change = True
        niter = 200
        while change and niter > 0:
            change = False
            niter -=1
            for possible in self.possible_items:
                for current_valid in valid_sets[:]:
                    if possible['left'] == current_valid[-1]['right']:
                        if current_valid + [possible] not in valid_sets:
                            if current_valid[-1]['left'] != current_valid[-1]['right'] or possible['left'] != possible['right']: #avoids Null insertion twice
                                valid_sets.append(current_valid + [possible])
                                change = True
        if not niter:
            raise Exception('too many iterations')
        return valid_sets

    def right_limit_list(self):
        if not self.possible_items:
            return [0]
        return list(set([x[-1]['right'] for x in self.valid_sequences()]))



########NEW FILE########
__FILENAME__ = test_Case
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Alphabet import Encoding
from pydsl.Lex import lexer_factory
from pydsl.Parser.LL import LL1RecursiveDescentParser

class TestCase(unittest.TestCase):
    def test_main_case(self):
        input_data = "1+2"
        ascii_encoding = Encoding("ascii")
        ascii_lexer = lexer_factory(ascii_encoding)
        ascii_tokens = [x.content for x in ascii_lexer(input_data)]
        self.assertListEqual([str(x) for x in ascii_tokens], ['1', '+', '2'])

        def concept_translator_fun(inputtokens):
            result = []
            for x in inputtokens:
                if x == "1":
                    result.append("one")
                elif x == "2":
                    result.append("two")
                elif x == "+":
                    result.append("addition")
                else:
                    raise Exception(x.__class__.__name__)

            return result
        def to_number(number):
            if number == "one":
                return 1
            if number == "two":
                return 2
 
        math_expression_concepts = concept_translator_fun(ascii_tokens)
        self.assertListEqual(math_expression_concepts, ['one', 'addition', 'two'])
        grammar_def = [
                "S ::= E",
                "E ::= one addition two",
                "one := String,one",
                "two := String,two",
                "addition := String,addition",
                ]
        from pydsl.File.BNF import strlist_to_production_set
        production_set = strlist_to_production_set(grammar_def, {})
        from pydsl.Parser.Backtracing import BacktracingErrorRecursiveDescentParser
        rdp = BacktracingErrorRecursiveDescentParser(production_set)
        parse_tree = rdp(math_expression_concepts)
        from pydsl.Grammar.Symbol import NonTerminalSymbol
        def parse_tree_walker(tree):
            if tree.symbol == NonTerminalSymbol("S"):
                return parse_tree_walker(tree.childlist[0])
            if tree.symbol == NonTerminalSymbol("E"):
                return to_number(tree.childlist[0].symbol.gd) + to_number(tree.childlist[2].symbol.gd)
            raise Exception
            
        result = parse_tree_walker(parse_tree[0])
        self.assertEqual(result, 3)


    def test_calculator_simple(self):
        grammar_def = [
                "S ::= E",
                "E ::= number operator number",
                "number := Word,integer,max",
                "operator := String,+",
                ]
        from pydsl.File.BNF import strlist_to_production_set
        from pydsl.Grammar import RegularExpression
        repository = {'integer':RegularExpression("^[0123456789]*$")}
        production_set = strlist_to_production_set(grammar_def, repository)
        rdp = LL1RecursiveDescentParser(production_set)
        parse_tree = rdp("1+2")

        def parse_tree_walker(tree):
            from pydsl.Grammar.Symbol import NonTerminalSymbol
            if tree.symbol == NonTerminalSymbol("S"):
                return parse_tree_walker(tree.childlist[0])
            if tree.symbol == NonTerminalSymbol("E"):
                return int(str(tree.childlist[0].content)) + int(str(tree.childlist[2].content))
            else:
                raise Exception
            
        result = parse_tree_walker(parse_tree[0])
        self.assertEqual(result, 3)
        from pydsl.Grammar.PEG import Choice
        from pydsl.Grammar.Definition import String, RegularExpression
        math_alphabet = Choice([RegularExpression("^[0123456789]*$"),String('+')])
        ascii_encoding = Encoding("ascii")
        from pydsl.Lex import lex
        tokens = [x[0] for x in lex(math_alphabet, ascii_encoding, "11+2")]
        parse_tree = rdp(tokens)
        result = parse_tree_walker(parse_tree[0])
        self.assertEqual(result, 13)


########NEW FILE########
__FILENAME__ = test_LogicGrammars
#!/usr/bin/python
# -*- coding: utf-8 -*-
from pydsl.Check import checker_factory

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Parser.Backtracing import BacktracingErrorRecursiveDescentParser
from pydsl.File.BNF import load_bnf_file
from pydsl.Lex import lex
from pydsl.Grammar import RegularExpression
from pydsl.Alphabet import Encoding
ascii_encoding = Encoding("ascii")


class TestLogicGrammars(unittest.TestCase):
    def setUp(self):
        #tokenlist definition
        self.tokelist5 = "True"

    def testLogicalExp(self):
        repository = {'TrueFalse':load_bnf_file("pydsl/contrib/grammar/TrueFalse.bnf")}
        productionrulesetlogical = load_bnf_file("pydsl/contrib/grammar/LogicalExpression.bnf", repository)
        parser = BacktracingErrorRecursiveDescentParser(productionrulesetlogical)
        tokens = [x[0] for x in lex(repository['TrueFalse'].alphabet, ascii_encoding, self.tokelist5)]
        self.assertEqual(len(tokens), 1)
        from pydsl.Lex import common_ancestor
        self.assertEqual(common_ancestor(productionrulesetlogical.alphabet), None)
        #tokens = [x[0] for x in lex(productionrulesetlogical.alphabet, Encoding('ascii'), tokens)] #FIXME
        tokens = [['True']]
        result = parser.get_trees(tokens)
        self.assertTrue(result)

    def testTrueFalse(self):
        productionrulesetlogical = load_bnf_file("pydsl/contrib/grammar/TrueFalse.bnf")
        parser = BacktracingErrorRecursiveDescentParser(productionrulesetlogical)
        tokens = [x[0] for x in lex(productionrulesetlogical.alphabet, ascii_encoding, self.tokelist5)]
        result = parser.get_trees(tokens)
        self.assertTrue(result)

    @unittest.skip('overlapping input')
    def testLogicalExpression(self):
        repository = {'TrueFalse':load_bnf_file("pydsl/contrib/grammar/TrueFalse.bnf")}
        productionrulesetlogical = load_bnf_file("pydsl/contrib/grammar/LogicalExpression.bnf", repository)
        parser = BacktracingErrorRecursiveDescentParser(productionrulesetlogical)
        tokens = [x[0] for x in lex(productionrulesetlogical.alphabet, ascii_encoding, "True&&False")]
        result = parser.get_trees(tokens)
        self.assertTrue(result)
        result = parser.get_trees("True&|False")
        self.assertFalse(result)



class TestHTMLGrammars(unittest.TestCase):
    def testHTMLTable(self):
        repository = {'integer':RegularExpression("^[0123456789]*$")}
        productionrulesetlogical = load_bnf_file("pydsl/contrib/grammar/TrueHTMLTable.bnf", repository)
        parser = BacktracingErrorRecursiveDescentParser(productionrulesetlogical)
        lexed = lex(productionrulesetlogical.alphabet, ascii_encoding, "<table><tr><td>1</td></tr></table>")
        self.assertTrue(lexed)
        lexed = [x.content for x in lexed]
        result = parser.get_trees(lexed)
        self.assertTrue(result)
        lexed = [x[0] for x in lex(productionrulesetlogical.alphabet, ascii_encoding, "<table><td>1</td></tr></table>")]
        result = parser.get_trees(lexed)
        self.assertFalse(result)


class TestLogGrammar(unittest.TestCase):
    def testLogLine(self):
        repository = {'space':RegularExpression("^ $"), 
                'integer':RegularExpression("^[0123456789]*$"),
                'ipv4':RegularExpression("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$"),
                'characters':RegularExpression("^[A-z]+$")}
        grammar = load_bnf_file("pydsl/contrib/grammar/logline.bnf", repository)
        checker = checker_factory(grammar)
        original_string = "1.2.3.4 - - [1/1/2003:11:11:11 +2] \"GET\" 1 1 \"referer\" \"useragent\""
        tokenized = [x.content for x in lex(grammar.alphabet, ascii_encoding, original_string)]
        self.assertTrue(checker.check(tokenized))
        self.assertFalse(checker.check("1.2.3.4 - - [1/1/2003:11:11:11 +2] \"GOT\" 1 1 \"referer\" \"useragent\""))

########NEW FILE########
__FILENAME__ = test_Alphabet
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.
from pydsl.Check import checker_factory
from pydsl.Lex import lexer_factory

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Grammar import String
from pydsl.Grammar.PEG import Sequence, Choice
from pydsl.Alphabet import Encoding, GrammarCollection
from pydsl.Grammar import RegularExpression
from pydsl.File.BNF import load_bnf_file
from pydsl.File.Python import load_python_file
import sys


class TestAlphabet(unittest.TestCase):
    def setUp(self):
        self.integer = RegularExpression("^[0123456789]*$")
        self.date = load_bnf_file("pydsl/contrib/grammar/Date.bnf", {'integer':self.integer, 'DayOfMonth':load_python_file('pydsl/contrib/grammar/DayOfMonth.py')})

    def testChecker(self):
        alphabet = GrammarCollection([self.integer,self.date])
        checker = checker_factory(alphabet)
        self.assertTrue(checker.check("1234"))
        self.assertTrue(checker.check([x for x in "1234"]))
        self.assertFalse(checker.check("11/11/1991")) #Non tokenized input
        self.assertFalse(checker.check([x for x in "11/11/1991"])) #Non tokenized input
        self.assertTrue(checker.check(["11","/","11","/","1991"])) #tokenized input
        self.assertFalse(checker.check("bcdf"))
        self.assertFalse(checker.check([x for x in "bcdf"]))

    @unittest.skipIf(sys.version_info < (3,0), "Full encoding support not available for python 2")
    def testEncoding(self):
        alphabet = Encoding('ascii')
        self.assertTrue(alphabet[0])
        self.assertEqual(len(alphabet.enum()), 128)
        alphabet = Encoding('unicode')
        self.assertTrue(alphabet[0])
        self.assertEqual(len(alphabet.enum()), 9635)
        self.assertRaises(KeyError, alphabet.__getitem__, 'a')
        self.assertRaises(KeyError, alphabet.__getitem__, 5.5)
        self.assertTrue(alphabet[100])

########NEW FILE########
__FILENAME__ = test_BNF
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from pydsl.Grammar.Definition import String


class TestBNF(unittest.TestCase):
    def setUp(self):
        from pydsl.contrib.bnfgrammar import productionset0
        self.grammardef = productionset0

    @unittest.skip("Not implemented")
    def testEnumerate(self):
        self.assertListEqual([x for x in self.grammardef.enum()], ["SR"])

    def testFirst(self):
        self.assertEqual(self.grammardef.first, String("S"))

    @unittest.skip("Not implemented")
    def testMin(self):
        self.assertEqual(self.grammardef.minsize,2)

    @unittest.skip("Not implemented")
    def testMax(self):
        self.assertEqual(self.grammardef.maxsize,2)

    def testFirstLookup(self):
        from pydsl.Grammar.Symbol import NonTerminalSymbol, TerminalSymbol
        from pydsl.Grammar.PEG import Choice
        self.grammardef.first_lookup(NonTerminalSymbol("exp"))[0]
        self.assertEqual(self.grammardef.first_lookup(NonTerminalSymbol("exp")),Choice([String("S")]))

    def testNextLookup(self):
        from pydsl.Grammar.Symbol import NonTerminalSymbol, EndSymbol
        self.grammardef.next_lookup(NonTerminalSymbol("exp"))[0]
        self.assertListEqual(self.grammardef.next_lookup(NonTerminalSymbol("exp")),[EndSymbol()])

    def testAlphabet(self):
        self.assertListEqual(list(self.grammardef.alphabet), [String(x) for x in ["S","R"]])

########NEW FILE########
__FILENAME__ = test_BNFLoad
#!/usr/bin/python
# -*- coding: utf-8 -*-

#Copyright (C) 2008-2013 Nestor Arocha

"""Test BNF file loading"""

import unittest
from pydsl.File.BNF import load_bnf_file
from pydsl.File.Python import load_python_file
from pydsl.Grammar.Definition import RegularExpression

class TestFileLoader(unittest.TestCase):
    """Loading a bnf instance from a .bnf file"""
    def testFileLoader(self):
        repository = {'integer':RegularExpression("^[0123456789]*$"), 
                'DayOfMonth':load_python_file('pydsl/contrib/grammar/DayOfMonth.py')}
        self.assertTrue(load_bnf_file("pydsl/contrib/grammar/Date.bnf", repository))

########NEW FILE########
__FILENAME__ = test_Checker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2013, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Grammar.Definition import String
import sys

class TestBNFChecker(unittest.TestCase):
    """BNF Checker"""
    def testStringInput(self):
        """Test checker instantiation and call"""
        from pydsl.Check import BNFChecker
        from pydsl.contrib.bnfgrammar import productionset0
        grammardef = productionset0
        checker = BNFChecker(grammardef)
        self.assertTrue(checker.check("SR"))
        self.assertTrue(checker.check("SR"))
        self.assertTrue(checker.check(("S","R")))
        self.assertFalse(checker.check("SL"))
        self.assertFalse(checker.check(("S","L")))
        self.assertFalse(checker.check(""))

class TestRegularExpressionChecker(unittest.TestCase):
    """BNF Checker"""
    def testCheck(self):
        """Test checker instantiation and call"""
        from pydsl.Check import RegularExpressionChecker
        input_str = "abc"
        checker = RegularExpressionChecker(input_str)
        self.assertTrue(checker.check(input_str))
        self.assertTrue(checker.check([x for x in input_str]))
        self.assertTrue(checker.check([x for x in input_str]))
        self.assertTrue(checker.check(input_str))
        self.assertFalse(checker.check("abd"))
        self.assertFalse(checker.check(""))

class TestPLYChecker(unittest.TestCase):
    def testCheck(self):
        """Test checker instantiation and call"""
        from pydsl.Check import PLYChecker
        from pydsl.contrib.grammar import example_ply
        from pydsl.Grammar.Definition import PLYGrammar
        grammardef = PLYGrammar(example_ply)
        checker = PLYChecker(grammardef)
        self.assertTrue(checker.check("O"))
        self.assertTrue(checker.check(["O"]))
        self.assertFalse(checker.check("FALSE"))
        #self.assertFalse(checker.check("")) #FIXME



class TestJsonSchemaChecker(unittest.TestCase):
    def testCheck(self):
        """Test checker instantiation and call"""
        from pydsl.Grammar.Definition import JsonSchema
        from pydsl.Check import JsonSchemaChecker
        schema = {
            "type" : "string",
            "items" : {
                "type" : ["string", "object"],
                "properties" : {
                    "foo" : {"enum" : [1, 3]},
                    #"bar" : { #See https://github.com/Julian/jsonschema/issues/89
                    #    "type" : "array",
                    #    "properties" : {
                    #        "bar" : {"required" : True},
                    #        "baz" : {"minItems" : 2},
                    #    }
                    #}
                }
            }
        }
        grammardef = JsonSchema(schema)
        checker = JsonSchemaChecker(grammardef)
        self.assertTrue(checker.check("a"))
        self.assertFalse(checker.check([1, {"foo" : 2, "bar" : {"baz" : [1]}}, "quux"]))


class TestEncodingChecker(unittest.TestCase):
    @unittest.skipIf(sys.version_info < (3,0), "Full encoding support not available for python 2")
    def testCheck(self):
        from pydsl.Check import EncodingChecker
        from pydsl.Alphabet import Encoding
        a = Encoding('ascii')
        checker = EncodingChecker(a)
        self.assertTrue(checker.check('1234'))
        self.assertTrue(checker.check([x for x in '1234']))
        self.assertTrue(checker.check('asdf'))
        self.assertFalse(checker.check('£'))
        #self.assertFalse(checker.check('')) #FIXME


class TestChoiceChecker(unittest.TestCase):
    def testCheck(self):
        from pydsl.Check import ChoiceChecker
        from pydsl.Grammar.PEG import Choice
        from pydsl.Grammar import RegularExpression
        a = Choice([RegularExpression('^[0123456789]*$')])
        checker = ChoiceChecker(a)
        self.assertTrue(checker.check([x for x in '1234']))
        self.assertTrue(checker.check('1234'))
        self.assertFalse(checker.check('abc'))
        self.assertFalse(checker.check(''))

class TestStringChecker(unittest.TestCase):
    def testCheck(self):
        """Test checker instantiation and call"""
        from pydsl.Check import StringChecker
        grammarchecker = StringChecker(String("string123"))
        self.assertTrue(grammarchecker("string123"))
        self.assertTrue(grammarchecker(["string123"]))
        self.assertTrue(grammarchecker(("string123",)))
        list_version = ["s","t","r","i","n","g","1","2","3"]
        self.assertTrue(grammarchecker(("s","t","r","i","n","g","1","2","3",)))
        self.assertTrue(grammarchecker(list_version))
        self.assertTrue(grammarchecker([String(x) for x in list_version]))
        self.assertTrue(grammarchecker([x for x in list_version]))
        self.assertFalse(grammarchecker(''))

class TestSequenceChecker(unittest.TestCase):
    def testCheck(self):
        from pydsl.Grammar.PEG import Sequence
        from pydsl.Check import SequenceChecker
        sequence = Sequence((String("a"), String("b"), String("c")))
        checker = SequenceChecker(sequence)
        self.assertTrue(checker.check("abc"))
        self.assertTrue(checker.check([x for x in "abc"]))
        self.assertFalse(checker.check("abd"))
        self.assertFalse(checker.check(""))

########NEW FILE########
__FILENAME__ = test_Extract
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Extract import extract, extract_alphabet
from pydsl.Grammar import RegularExpression, String
from pydsl.Grammar.PEG import Choice
from pydsl.Alphabet import Encoding
from pydsl.Token import PositionToken, Token
import sys


class TestGrammarExtract(unittest.TestCase):

    def testRegularExpression(self):
        gd = RegularExpression('^[0123456789]*$')
        expected_result = [
                PositionToken(content='1', gd=None, left=3, right=4), 
                PositionToken(content='12', gd=None, left=3, right=5), 
                PositionToken(content='123', gd=None, left=3, right=6), 
                PositionToken(content='1234', gd=None, left=3, right=7), 
                PositionToken(content='2', gd=None, left=4, right=5), 
                PositionToken(content='23', gd=None, left=4, right=6), 
                PositionToken(content='234', gd=None, left=4, right=7), 
                PositionToken(content='3', gd=None, left=5, right=6), 
                PositionToken(content='34', gd=None, left=5, right=7), 
                PositionToken(content='4', gd=None, left=6, right=7)]
        self.assertListEqual(extract(gd,'abc1234abc'), expected_result)
        expected_result = [
                PositionToken(content=['1'], gd=None, left=3, right=4), 
                PositionToken(content=['1','2'], gd=None, left=3, right=5), 
                PositionToken(content=['1','2','3'], gd=None, left=3, right=6), 
                PositionToken(content=['1','2','3','4'], gd=None, left=3, right=7), 
                PositionToken(content=['2'], gd=None, left=4, right=5), 
                PositionToken(content=['2','3'], gd=None, left=4, right=6), 
                PositionToken(content=['2','3','4'], gd=None, left=4, right=7), 
                PositionToken(content=['3'], gd=None, left=5, right=6), 
                PositionToken(content=['3','4'], gd=None, left=5, right=7), 
                PositionToken(content=['4'], gd=None, left=6, right=7)]
        self.assertListEqual(extract(gd,[Token(x, None) for x in 'abc1234abc']), expected_result)
        self.assertListEqual(extract(gd,[x for x in 'abc1234abc']), expected_result)
        self.assertRaises(Exception, extract, None)
        self.assertListEqual(extract(gd,''), []) #Empty input


class TestAlphabetExtract(unittest.TestCase):

    @unittest.skipIf(sys.version_info < (3,0), "Full encoding support not available for python 2")
    def testEncoding(self):
        ad = Encoding('ascii')
        self.assertListEqual(extract(ad,''), [])
        self.assertListEqual(extract(ad,'a£'), [PositionToken('a', None, 0,1)])
        self.assertListEqual(extract(ad,['a','£']), [PositionToken(['a'], None, 0,1)])
        self.assertRaises(Exception, extract, None)

    def testChoices(self):
        gd = Choice([String('a'), String('b'), String('c')])
        self.assertListEqual(extract_alphabet(gd,'axbycz'), [PositionToken('a', None,0,1), PositionToken('b', None, 2,3), PositionToken('c', None, 4,5)])
        self.assertListEqual(extract_alphabet(gd,'xyzabcxyz'), [PositionToken('abc', None, 3,6)])
        self.assertListEqual(extract_alphabet(gd,'abcxyz'), [PositionToken('abc', None, 0,3)])
        self.assertListEqual(extract_alphabet(gd,[Token(x, None) for x in 'abcxyz']), [PositionToken(['a','b','c'], None, 0,3)])
        self.assertListEqual(extract_alphabet(gd,'abc'), [PositionToken('abc', None, 0,3)])
        self.assertListEqual(extract_alphabet(gd,''), [])

########NEW FILE########
__FILENAME__ = test_GrammarDefinition
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


"""Tests the Grammar definition instances"""


__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Grammar.Definition import String
from pydsl.Alphabet import Encoding
from pydsl.Alphabet import Alphabet


@unittest.skip
class TestGrammarDefinitionPLY(unittest.TestCase):
    def setUp(self):
        import plye
        from pydsl.Grammar.Definition import PLYGrammar
        self.grammardef = PLYGrammar(plye)

    @unittest.skip
    def testEnumerate(self):
        self.grammardef.enum()

    @unittest.skip
    def testFirst(self):
        self.grammardef.first

    @unittest.skip
    def testMin(self):
        self.grammardef.minsize

    @unittest.skip
    def testMax(self):
        self.grammardef.maxsize

    def testAlphabet(self):
        self.assertListEqual(self.grammardef.alphabet, Alphabet)

class TestGrammarDefinitionJson(unittest.TestCase):
    def setUp(self):
        from pydsl.Grammar.Definition import JsonSchema
        self.grammardef = JsonSchema({})

    def testEnumerate(self):
        self.assertRaises(NotImplementedError, self.grammardef.enum)

    def testFirst(self):
        self.grammardef.first

    def testMin(self):
        self.grammardef.minsize

    def testMax(self):
        self.grammardef.maxsize

    def testAlphabet(self):
        self.assertEqual(self.grammardef.alphabet, Encoding('ascii'))


########NEW FILE########
__FILENAME__ = test_Guess
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Grammar import RegularExpression

class TestGuesser(unittest.TestCase):
    def testGuesser(self):
        cstring = RegularExpression('.*')
        g1234 = RegularExpression('1234')
        memorylist = [cstring, g1234 ]
        from pydsl.Guess import Guesser
        guesser = Guesser(memorylist)
        self.assertListEqual(guesser('1234'), [cstring, g1234])
        self.assertListEqual(guesser([x for x in '1234']), [cstring, g1234])
        self.assertListEqual(guesser('134'), [cstring])


########NEW FILE########
__FILENAME__ = test_Lexer
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Lex import EncodingLexer, lexer_factory
from pydsl.contrib.bnfgrammar import *
from pydsl.Grammar.Definition import String
from pydsl.Alphabet import GrammarCollection
from pydsl.Grammar.PEG import Sequence, Choice
from pydsl.File.BNF import load_bnf_file


class TestEncodingLexer(unittest.TestCase):
    def testLexer(self):
        """Lexer call"""
        lexer = lexer_factory(productionset1.alphabet)
        result = list(lexer(string1))
        self.assertTrue(result)

    def testencodingLexer(self):
        lexer = EncodingLexer('utf8')
        result = list(lexer("abcde"))
        self.assertTrue([str(x) for x in result])
        result = list(lexer([x for x in "abcde"]))
        self.assertTrue([str(x) for x in result])

class TestChoiceBruteForceLexer(unittest.TestCase):
    def testEmptyInput(self):
        integer = RegularExpression("^[0123456789]*$")
        date = load_bnf_file("pydsl/contrib/grammar/Date.bnf", {'integer':integer, 'DayOfMonth':load_python_file('pydsl/contrib/grammar/DayOfMonth.py')})
        mydef = GrammarCollection([integer,date])
        lexer = lexer_factory(mydef)
        self.assertFalse(lexer(""))

    def testSimpleLexing(self):
        """Test checker instantiation and call"""
        integer = RegularExpression("^[0123456789]*$")
        date = load_bnf_file("pydsl/contrib/grammar/Date.bnf", {'integer':integer, 'DayOfMonth':load_python_file('pydsl/contrib/grammar/DayOfMonth.py')})
        mydef = GrammarCollection([integer,date])
        lexer = lexer_factory(mydef)
        self.assertListEqual(lexer("1234"), [(["1","2","3","4"], integer)])
        self.assertListEqual(lexer([x for x in "1234"]), [(["1","2","3","4"], integer)])

    @unittest.skip('FIXME:  Non contiguous parsing from sucessors')
    def testOverlappingLexing(self):
        integer = RegularExpression("^[0123456789]*$")
        date = load_bnf_file("pydsl/contrib/grammar/Date.bnf", {'integer':integer, 'DayOfMonth':load_python_file('pydsl/contrib/grammar/DayOfMonth.py')})
        mydef = GrammarCollection([integer,date])
        lexer = lexer_factory(mydef)
        self.assertListEqual(lexer("123411/11/2001"), [("1234", integer),("11/11/2001", date)])
        self.assertListEqual(lexer([x for x in "123411/11/2001"]), [("1234", integer),("11/11/2001", date)])

    @unittest.skip('GeneralLexer doesn\'t know how to get from the base to the target')
    def testSecondLevelGrammar(self):
        a = String("a")
        b = String("b")
        c = String("c")
        x = String("x")
        y = String("y")
        z = String("z")
        first_level = Choice([a,b,c])
        first_levelb = Choice([x,y,z])
        second_level = Sequence([a,b], base_alphabet=first_level)
        from pydsl.Check import checker_factory
        checker = checker_factory(second_level)
        self.assertTrue(checker([a,b]))
        second_level_alphabet = Choice([first_level, first_levelb]) 
        lexer = lexer_factory(second_level_alphabet, base=first_level+first_levelb)
        self.assertListEqual(lexer("ab"), [("a",first_level),("b",first_level)])


class TestChoiceLexer(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def testSimpleChoiceLexer(self):
        a1 = Choice([String('a'), String('b'), String('c')])
        from pydsl.Lex import ChoiceLexer
        lexer = ChoiceLexer(a1)
        self.assertListEqual(lexer("abc"), [("a", String('a'))])

class TestPythonLexer(unittest.TestCase):
    def test_Concept(self):
        red = String("red")
        green = String("green")
        blue = String("blue")
        alphabet = Choice([red,green,blue])
        lexer = lexer_factory(alphabet)

        def concept_translator_fun(inputtokens):
            result = []
            for x,_ in inputtokens:
                if x == "red" or x == ["r","e","d"]:
                    result.append("color red")
                elif x == "green" or x == ["g","r","e","e","n"]:
                    result.append("color green")
                elif x == "blue" or x == ["b","l","u","e"]:
                    result.append("color blue")
                else:
                    raise Exception("%s,%s" % (x, x.__class__.__name__))

            return result

        ct = concept_translator_fun

        self.assertListEqual(ct(lexer("red")), ["color red"])
        self.assertListEqual(ct(lexer([x for x in "red"])), ["color red"])

########NEW FILE########
__FILENAME__ = test_Parser
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"



from pydsl.contrib.bnfgrammar import *
from pydsl.Parser.Backtracing import BacktracingErrorRecursiveDescentParser
from pydsl.Parser.LR0 import LR0Parser
from pydsl.Lex import EncodingLexer
from pydsl.Parser.LL import LL1RecursiveDescentParser
import unittest

class TestBacktracingRecursiveDescentParser(unittest.TestCase):
    def testRecursiveLeftRecursion(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionsetlr)
        self.assertRaises(RuntimeError, descentparser, dots)

    def testRightRecursion(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionsetrr)
        result = descentparser(dots)
        self.assertTrue(result)
        result = descentparser(list(dots))
        self.assertTrue(result)

    def testCenterRecursion(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionsetcr)
        result = descentparser(dots)
        self.assertTrue(result)
        result = descentparser(list(dots))
        self.assertTrue(result)

    def testRecursiveDescentParserStore(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionset1)
        result = descentparser(string1)
        self.assertTrue(result)
        result = descentparser(list(string1))
        self.assertTrue(result)

    def testRecursiveDescentParserBad(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionset1)
        result = descentparser(string2)
        self.assertFalse(result)
        result = descentparser(list(string2))
        self.assertFalse(result)


    def testRecursiveDescentParserNull(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionset2)
        result = descentparser(string3)
        self.assertTrue(result)
        result = descentparser(list(string3))
        self.assertTrue(result)

    def testRecursiveDescentParserNullBad(self):
        descentparser = BacktracingErrorRecursiveDescentParser(productionset2)
        from pydsl.Lex import lex
        from pydsl.Alphabet import Encoding
        ascii_encoding = Encoding('ascii')
        lexed_string4 = [x[0] for x in lex(productionset2.alphabet, ascii_encoding, string4)]
        result = descentparser(lexed_string4)
        self.assertFalse(result)
        result = descentparser(list(string4))
        self.assertFalse(result)


class TestLR0Parser(unittest.TestCase):
    def testLR0ParseTable(self):
        """Tests the lr0 table generation"""
        from pydsl.Parser.LR0 import _slr_build_parser_table, build_states_sets
        state_sets = build_states_sets(productionset0)
        self.assertEqual(len(state_sets), 5)
        #0 . EI: : . exp $ , 
        #   exp : .SR
        #       transitions: S -> 2,
        #       goto: exp -> 1
        #1 EI:  exp . $ ,
        #       transitions: $ -> 3
        #2 exp:  S . R,
        #       transitions: R -> 4
        #3 EI: exp $ .
        #4 exp:  S R .
        #       reduce

        parsetable = _slr_build_parser_table(productionset0)
        self.assertEqual(len(parsetable), 4)


    def testLR0ParserStore(self):
        parser = LR0Parser(productionset0)
        tokelist = [x.content for x in EncodingLexer('utf8')(p0good)]
        result = parser(tokelist)
        self.assertTrue(result)

    def testLR0ParserBad(self):
        parser = LR0Parser(productionset1)
        result = parser(string2)
        self.assertFalse(result)
        result = parser(list(string2))
        self.assertFalse(result)

    def testCenterRecursion(self):
        self.assertRaises(Exception, LR0Parser, productionsetcr)

    def testArithmetic(self):
        parser = LR0Parser(productionset_arithmetic)
        self.assertFalse(parser('1'))
        self.assertTrue(parser(['123']))
        self.assertTrue(parser(['123','+','123']))
        self.assertTrue(parser(['123','*','123']))
        self.assertFalse(parser(['123a','+','123']))
        self.assertFalse(parser(['123','+','+']))


class TestLL1RecursiveDescentParser(unittest.TestCase):
    @unittest.skip
    def testRecursiveLeftRecursion(self):
        descentparser = LL1RecursiveDescentParser(productionsetlr)
        result = descentparser(dots)
        self.assertTrue(result)

    def testRightRecursion(self):
        descentparser = LL1RecursiveDescentParser(productionsetrr)
        self.assertFalse(descentparser(dots)) #Ambiguous grammar

    def testCenterRecursion(self):
        descentparser = LL1RecursiveDescentParser(productionsetcr)
        self.assertFalse(descentparser(dots)) #Ambiguous grammar

    def testLL1RecursiveDescentParserStore(self):
        descentparser = LL1RecursiveDescentParser(productionset1)
        result = descentparser(string1)
        self.assertTrue(result)
        result = descentparser(list(string1))
        self.assertTrue(result)

    def testLL1RecursiveDescentParserBad(self):
        descentparser = LL1RecursiveDescentParser(productionset1)
        result = descentparser(string2)
        self.assertFalse(result)
        result = descentparser(list(string2))
        self.assertFalse(result)

@unittest.skip
class TestPEGParser(unittest.TestCase):
    def testBasicChoice(self):
        from pydsl.Grammar.Alphabet import Choice
        from pydsl.Tree import ParseTree
        from pydsl.Parser.PEG import PEGParser
        gd = Choice([String('a'), String('b')])
        parser = PEGParser(gd)
        result = parser('a')
        self.assertTrue(isinstance(result, ParseTree))



class TestParse(unittest.TestCase):
    def testverb(self):
        """Tests the lr0 table generation"""
        from pydsl.Parser.Parser import parse, parser_factory
        tokelist = [x.content for x in EncodingLexer('utf8')(p0good)]
        self.assertTrue(parse(productionset0, tokelist , "default"))
        self.assertTrue(parse(productionset0, tokelist , "lr0"))
        self.assertTrue(parse(productionset0, tokelist , "ll1"))
        tokelist = [x.content for x in EncodingLexer('utf8')(p0bad)]
        self.assertFalse(parse(productionset0, tokelist , "default"))
        self.assertFalse(parse(productionset0, tokelist , "lr0"))
        self.assertFalse(parse(productionset0, tokelist , "ll1"))

########NEW FILE########
__FILENAME__ = test_Parsley
#!/usr/bin/python
# -*- coding: utf-8 -*-
# This file is part of pydsl.
#
# pydsl is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pydsl is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from pydsl.Translator import translator_factory
from pydsl.Check import checker_factory
from pydsl.File.Python import load_python_file
import sys

__author__ = "Ptolom"
__copyright__ = "Copyright 2014, Ptolom"
__email__ = "ptolom@hexifact.co.uk"

@unittest.skipIf(sys.version_info > (3,0), "parsley not available for python 3")
class TestParsley(unittest.TestCase):
    """Loading a bnf instance from a .bnf file"""
    def testFileLoader(self):
        import parsley
        from pydsl.File.Parsley import load_parsley_grammar_file
        repository = {'DayOfMonth':load_python_file('pydsl/contrib/grammar/DayOfMonth.py')} #DayOfMonth loaded as checker
        G=load_parsley_grammar_file("pydsl/contrib/grammar/Date.parsley", "expr", repository)
        C=checker_factory(G)
        T=translator_factory(G)
        self.assertTrue(C("2/4/12"))
        self.assertEqual(T("2/4/12"),(2,4,12))
        self.assertRaises(parsley.ParseError,T, "40/4/12")
        

if __name__ == '__main__':
        unittest.main()

########NEW FILE########
__FILENAME__ = test_PEG
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

"""Tests PEG grammars"""

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Grammar.Definition import String, Grammar
from pydsl.Grammar.PEG import ZeroOrMore, OneOrMore, Not, Sequence, Choice

class TestPEG(unittest.TestCase):
    def testOneOrMore(self):
        mygrammar = OneOrMore(String("a"))
        self.assertTrue(isinstance(mygrammar, Grammar))
        self.assertEqual(mygrammar.first(), Choice([String("a")]))
        from pydsl.Check import check
        self.assertTrue(check(mygrammar, "a"))
        self.assertTrue(check(mygrammar, "aa"))
        self.assertTrue(check(mygrammar, "aaaa"))
        self.assertFalse(check(mygrammar, ""))
        self.assertFalse(check(mygrammar, "b"))

    def testZeroOrMore(self):
        mygrammar = ZeroOrMore(String("a"))
        self.assertTrue(isinstance(mygrammar, Grammar))
        self.assertEqual(mygrammar.first(), Choice([String("a")]))
        from pydsl.Check import check
        self.assertTrue(check(mygrammar, "a"))
        self.assertTrue(check(mygrammar, "aa"))
        self.assertTrue(check(mygrammar, "aaaa"))
        self.assertTrue(check(mygrammar, ""))
        self.assertFalse(check(mygrammar, "b"))

    def testChoice(self):
        mygrammar = Choice((String("a"), String("b")))
        from pydsl.Check import check
        self.assertTrue(check(mygrammar, "a"))
        self.assertTrue(check(mygrammar, "b"))
        self.assertFalse(check(mygrammar, "c"))

    def testNot(self):
        mygrammar = Not(String("a"))
        self.assertTrue(isinstance(mygrammar, Not))

    def testSequence(self):
        mygrammar = Sequence((String("a"), String("b")))
        self.assertTrue(isinstance(mygrammar, Grammar))

########NEW FILE########
__FILENAME__ = test_RegularExpression
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.


__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2013, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest
from pydsl.Grammar.Definition import RegularExpression
import re

class TestRegularExpression(unittest.TestCase):
    """Regular expression method tests"""
    def testInstantiation(self):
        re1 = RegularExpression('^a$')
        re2 = RegularExpression(re.compile('^a$'))
        self.assertEqual(str(re1), str(re2)) #FIXME python3 default flag value is 32

    def testEnumerate(self):
        re1 = RegularExpression(re.compile('^a$'))
        self.assertRaises(NotImplementedError, re1.enum)

    def testFirst(self):
        re1 = RegularExpression(re.compile('^a$'))
        self.assertEqual(len(re1.first()),1)
        from pydsl.Grammar.Definition import String
        self.assertEqual(re1.first()[0],String('a'))

    def testMin(self):
        re1 = RegularExpression(re.compile('^a$'))
        re1.minsize

    def testMax(self):
        re1 = RegularExpression(re.compile('^a$'))
        re1.maxsize

    def testAlphabet(self):
        from pydsl.Alphabet import Encoding
        re1 = RegularExpression(re.compile('^a$'))
        self.assertEqual(re1.alphabet, Encoding('ascii'))


########NEW FILE########
__FILENAME__ = test_Translate
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2013, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest

class TestTranslate(unittest.TestCase):
    def testEcho(self):
        from pydsl.Translator import translate, PythonTranslator
        from pydsl.Grammar.Definition import RegularExpression
        from pydsl.Check import checker_factory
        cstring = checker_factory(RegularExpression('.*'))
        def function(my_input):
            return my_input
        pt = PythonTranslator({'my_input':cstring}, {'output':cstring}, function)
        self.assertEqual(translate(pt,{'my_input':"1234"}),"1234")


########NEW FILE########
__FILENAME__ = test_Tree
#!/usr/bin/python
# -*- coding: utf-8 -*-
#This file is part of pydsl.
#
#pydsl is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pydsl is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pydsl.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Nestor Arocha"
__copyright__ = "Copyright 2008-2014, Nestor Arocha"
__email__ = "nesaro@gmail.com"

import unittest

class TestTrees(unittest.TestCase):
    def setUp(self):
        from pydsl.Tree import ParseTree
        a = ParseTree(0,6, None, "abcdef")
        self.firstleaf1 = ParseTree(0,1, None, "a")
        a.append(self.firstleaf1)
        b = ParseTree(1,3,None, "bc")
        a.append(b)
        b.append(ParseTree(1,2,None, "b"))
        b.append(ParseTree(2,3,None, "c"))
        a.append(ParseTree(3,4,None, "d"))
        a.append(ParseTree(4,5,None, "e"))
        a.append(ParseTree(5,6,None, "f"))
        self.tree1 = a
        c = ParseTree(0,6, None, "abcdef")
        self.firstleaf2 = ParseTree(0,1, None, "a")
        c.append(self.firstleaf2)
        b = ParseTree(1,3, None, "bc")
        c.append(b)
        b.append(ParseTree(1,2, None, "b"))
        b.append(ParseTree(2,3, None, "j"))
        c.append(ParseTree(3,4, None, "d"))
        c.append(ParseTree(4,5, None, "e"))
        c.append(ParseTree(5,6, None, "f"))
        self.tree2 = c

    def testBasics(self):
        self.assertTrue(len(self.tree1) == 6)


class TestPositionResultList(unittest.TestCase):
    def testMain(self):
        from pydsl.Tree import PositionResultList
        seq = PositionResultList()
        seq.append(0,1,".")
        seq.append(1,2,".")
        seq.append(2,3,".")
        seq.append(3,4,".")
        seq.append(4,5,".")
        self.assertEqual(len(seq.valid_sequences()[-1]), 5)


########NEW FILE########
