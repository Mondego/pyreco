__FILENAME__ = asm
#!/usr/bin/env python

from __future__ import print_function

import struct
import re
import sys
import argparse
import os
import codecs


def disjunction(*lst):
    "make a uppercase/lowercase disjunction out of a list of strings"
    return "|".join([item.upper() for item in lst] + [item.lower() for item in lst])


BASIC_INSTRUCTIONS = disjunction("SET", "ADD", "SUB", "MUL", "DIV", "MOD", "SHL", "SHR", "AND", "BOR", "XOR", "IFE", "IFN", "IFG", "IFB")
GENERAL_REGISTERS = disjunction("A", "B", "C", "X", "Y", "Z", "I", "J")
ALL_REGISTERS = disjunction("A", "B", "C", "X", "Y", "Z", "I", "J", "POP", "PEEK", "PUSH", "SP", "PC", "O")


def operand_re(prefix):
    return """
    ( # operand
        (?P<""" + prefix + """register>""" + ALL_REGISTERS + """) # register
        |
        (\[\s*(?P<""" + prefix + """register_indirect>""" + GENERAL_REGISTERS + """)\s*\]) # register indirect
        |
        (\[\s*(0x(?P<""" + prefix + """hex_indexed>[0-9A-Fa-f]{1,4}))\s*\+\s*(?P<""" + prefix + """hex_indexed_index>""" + GENERAL_REGISTERS + """)\s*\]) # hex indexed
        |
        (\[\s*(?P<""" + prefix + """decimal_indexed>\d+)\s*\+\s*(?P<""" + prefix + """decimal_indexed_index>""" + GENERAL_REGISTERS + """)\s*\]) # decimal indexed
        |
        (\[\s*(?P<""" + prefix + """label_indexed>\w+)\s*\+\s*(?P<""" + prefix + """label_indexed_index>""" + GENERAL_REGISTERS + """)\s*\]) # label indexed
        |
        (\[\s*(0x(?P<""" + prefix + """hex_indirect>[0-9A-Fa-f]{1,4}))\s*\]) # hex indirect
        |
        (\[\s*(?P<""" + prefix + """decimal_indirect>\d+)\s*\]) # decimal indirect
        |
        (0x(?P<""" + prefix + """hex_literal>[0-9A-Fa-f]{1,4})) # hex literal
        |
        (\[\s*(?P<""" + prefix + """label_indirect>\w+)\s*\]) # label indirect
        |
        (?P<""" + prefix + """decimal_literal>\d+) # decimal literal
        |
        (?P<""" + prefix + """label>\w+) # label+
    )
    """

line_regex = re.compile(r"""^\s*
    (:(?P<label>\w+))? # label
    \s*
    (
        (
            (?P<basic>""" + BASIC_INSTRUCTIONS + """) # basic instruction
            \s+""" + operand_re("op1_") + """\s*,\s*""" + operand_re("op2_") + """
        )
        |(
            (?P<nonbasic>JSR|jsr) # non-basic instruction
            \s+""" + operand_re("op3_") + """
        )
        |(
            (DAT|dat) # data
            \s+(?P<data>("[^"]*"|0x[0-9A-Fa-f]{1,4}|\d+)(,\s*("[^"]*"|0x[0-9A-Fa-f]{1,4}|\d+))*)
        )
    )?
    \s*
    (?P<comment>;.*)? # comment
    $""", re.X)


IDENTIFIERS = {
    "A":    0x0,
    "B":    0x1,
    "C":    0x2,
    "X":    0x3,
    "Y":    0x4,
    "Z":    0x5,
    "I":    0x6,
    "J":    0x7,
    "POP":  0x18,
    "PEEK": 0x19,
    "PUSH": 0x1a,
    "SP":   0x1b,
    "PC":   0x1C,
    "O":    0x1D
}

OPCODES = {
    "SET": 0x1,
    "ADD": 0x2,
    "SUB": 0x3,
    "MUL": 0x4,
    "DIV": 0x5,
    "MOD": 0x6,
    "SHL": 0x7,
    "SHR": 0x8,
    "AND": 0x9,
    "BOR": 0xA,
    "XOR": 0xB,
    "IFE": 0xC,
    "IFN": 0xD,
    "IFG": 0xE,
    "IFB": 0xF
}


def clamped_value(l):
    return (0x20 + l, None) if l < 0x20 else (0x1F, l)


ADDR_MAP = {
    "register":              lambda t, v: (IDENTIFIERS[t.upper()], None),
    "register_indirect":     lambda t, v: (0x08 + IDENTIFIERS[t.upper()], None),
    "hex_indexed_index":     lambda t, v: (0x10 + IDENTIFIERS[t.upper()], int(v, 16)),
    "decimal_indexed_index": lambda t, v: (0x10 + IDENTIFIERS[t.upper()], int(v, 16)),
    "label_indexed_index":   lambda t, v: (0x10 + IDENTIFIERS[t.upper()], v),
    "hex_indirect":          lambda t, v: (0x1E, int(t, 16)),
    "decimal_indirect":      lambda t, v: (0x1E, int(t)),
    "hex_literal":           lambda t, v: clamped_value(int(t, 16)),
    "decimal_literal":       lambda t, v: clamped_value(int(t)),
    "label_indirect":        lambda t, v: (0x1E, t),
    "label":                 lambda t, v: (0x1F, t),
}


def handle(token_dict, prefix):
    token = [t for t in token_dict.keys() if t.startswith(prefix) and token_dict[t] is not None][0]
    suffix = token[len(prefix):]
    v = token_dict[token[:token.rfind("_index")]] if token.endswith("_index") else None
    return ADDR_MAP[suffix](token_dict[token], v)


def report_error(filename, lineno, error):
    print("%s:%i: %s" % (filename, lineno, error), file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="DCPU-16 assembler")
    parser.add_argument("-o", default="a.obj", help="Place the output into FILE", metavar="FILE")
    parser.add_argument("input", help="File with DCPU assembly code")
    args = parser.parse_args()

    program = []
    labels = {}

    for lineno, line in enumerate(open(args.input), start=1):
        if lineno == 1:
            line = line.lstrip(codecs.BOM_UTF8)

        mo = line_regex.match(line)
        if mo is None:
            report_error(args.input, lineno, "Syntax error: '%s'" % line.strip())
            break

        token_dict = mo.groupdict()
        if token_dict is None:
            report_error(args.input, lineno, "Syntax error: '%s'" % line.strip())
            break

        if token_dict["label"] is not None:
            labels[token_dict["label"]] = len(program)

        o = x = y = None
        if token_dict["basic"] is not None:
            o = OPCODES[token_dict["basic"].upper()]
            a, x = handle(token_dict, "op1_")
            b, y = handle(token_dict, "op2_")
        elif token_dict["nonbasic"] is not None:
            o, a = 0x00, 0x01
            b, y = handle(token_dict, "op3_")
        elif token_dict["data"] is not None:
            for datum in re.findall("""("[^"]*"|0x[0-9A-Fa-f]{1,4}|\d+)""", token_dict["data"]):
                if datum.startswith("\""):
                    program.extend(ord(ch) for ch in datum[1:-1])
                elif datum.startswith("0x"):
                    program.append(int(datum[2:], 16))
                else:
                    program.append(int(datum))

        if o is not None:
            program.append(((b << 10) + (a << 4) + o))
        if x is not None:
            program.append(x)
        if y is not None:
            program.append(y)

    try:
        with open(args.o, "wb") as f:
            for word in program:
                if isinstance(word, str):
                    word = labels[word]
                f.write(struct.pack(">H", word))
    except KeyError:
        os.remove(args.o)

########NEW FILE########
__FILENAME__ = asm_pyparsing
#! /usr/bin/env python
"""
pyparsing based grammar for DCPU-16 0x10c assembler
"""

try:
    from itertools import izip_longest
except ImportError:
    from itertools import zip_longest as izip_longest

try:
    basestring
except NameError:
    basestring = str

import logging; log = logging.getLogger("dcpu16_asm")
log.setLevel(logging.DEBUG)

import argparse
import os
import struct
import sys

import pyparsing as P
from collections import defaultdict

# Replace the debug actions so that the results go to the debug log rather
# than stdout, so that the output can be usefully piped.
def _defaultStartDebugAction(instring, loc, expr):
    log.debug("Match " + P._ustr(expr) + " at loc " + P._ustr(loc) + "(%d,%d)" 
              % ( P.lineno(loc,instring), P.col(loc,instring) ))

def _defaultSuccessDebugAction(instring, startloc, endloc, expr, toks):
    log.debug("Matched " + P._ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction(instring, loc, expr, exc):
    log.debug("Exception raised:" + P._ustr(exc))

P._defaultStartDebugAction = _defaultStartDebugAction
P._defaultSuccessDebugAction = _defaultSuccessDebugAction
P._defaultExceptionDebugAction = _defaultExceptionDebugAction


# Run with "DEBUG=1 python ./asm_pyparsing.py"
DEBUG = "DEBUG" in os.environ

WORD_MAX = 0xFFFF

# otherwise \n is also treated as ignorable whitespace
P.ParserElement.setDefaultWhitespaceChars(" \t")

identifier = P.Word(P.alphas+"_", P.alphanums+"_")
label = P.Combine(P.Literal(":").suppress() + identifier)

comment = P.Literal(";").suppress() + P.restOfLine

register = (P.Or(P.CaselessKeyword(x) for x in "ABCIJXYZO")
            | P.oneOf("PC SP", caseless=True))

stack_op = P.oneOf("PEEK POP PUSH", caseless=True)

hex_literal = P.Combine(P.Literal("0x") + P.Word(P.hexnums))
dec_literal = P.Word(P.nums)

numeric_literal = hex_literal | dec_literal
literal = numeric_literal | identifier

opcode = P.oneOf("SET ADD SUB MUL DIV MOD SHL SHR "
                 "AND BOR XOR IFE IFN IFG IFB JSR", caseless=True)

basic_operand = P.Group(register("register")
                        | stack_op("stack_op")
                        | literal("literal"))

indirect_expr = P.Group(literal("literal")
                        + P.Literal("+")
                        + register("register"))

hex_literal.setParseAction(lambda s, l, t: int(t[0], 16))
dec_literal.setParseAction(lambda s, l, t: int(t[0]))
register.addParseAction(P.upcaseTokens)
stack_op.addParseAction(P.upcaseTokens)
opcode.addParseAction(P.upcaseTokens)

def sandwich(brackets, expr):
    l, r = brackets
    return P.Literal(l).suppress() + expr + P.Literal(r).suppress()

indirection_content = indirect_expr("expr") | basic_operand("basic")
indirection = P.Group(sandwich("[]", indirection_content) |
                      sandwich("()", indirection_content))

operand = basic_operand("basic") | indirection("indirect")

def make_words(data):
    return [a << 8 | b for a, b in izip_longest(data[::2], data[1::2],
                                                  fillvalue=0)]
def wordize_string(s, l, tokens):
    bytes = [ord(c) for c in tokens.string]
    # TODO(pwaller): possibly add syntax for packing string data?
    packed = False
    return make_words(bytes) if packed else bytes

quoted_string = P.quotedString("string").addParseAction(P.removeQuotes).addParseAction(wordize_string)
datum = quoted_string | numeric_literal
def parse_data(string, loc, tokens):
    result = []
    for token in tokens:
        values = datum.parseString(token).asList()
        assert all(v < WORD_MAX for v in values), "Datum exceeds word size"
        result.extend(values)
    return result

# TODO(pwaller): Support for using macro argument values in data statement
datalist = P.commaSeparatedList.copy().setParseAction(parse_data)
data = P.CaselessKeyword("DAT")("opcode") + P.Group(datalist)("data")

line = P.Forward()

macro_definition_args = P.Group(P.delimitedList(P.Optional(identifier("arg"))))("args")

macro_definition = P.Group(
    P.CaselessKeyword("#macro").suppress()
    + identifier("name")
    + sandwich("()", macro_definition_args)
    + sandwich("{}", P.Group(P.OneOrMore(line))("lines"))
)("macro_definition")

macro_argument = operand | datum

macro_call_args = P.Group(P.delimitedList(P.Group(macro_argument)("arg")))("args")

macro_call = P.Group(
    identifier("name") + sandwich("()", macro_call_args)
)("macro_call")

instruction = (
    opcode("opcode")
    + P.Group(operand)("first")
    + P.Optional(P.Literal(",").suppress() + P.Group(operand)("second"))
)

statement = P.Group(
    instruction
    | data
    | macro_definition
    | macro_call
)

line << P.Group(
    P.Optional(label("label"))
    + P.Optional(statement("statement"), default=None)
    + P.Optional(comment("comment"))
    + P.lineEnd.suppress()
)("line")

full_grammar = (
    P.stringStart
    + P.ZeroOrMore(line)
    + (P.stringEnd | P.Literal("#stop").suppress())
)("program")


if DEBUG:
    # Turn setdebug on for all parse elements
    for name, var in locals().copy().items():
        if isinstance(var, P.ParserElement):
            var.setName(name).setDebug()
    def debug_line(string, location, tokens):
        """
        Show the current line number and content being parsed
        """
        lineno = string[:location].count("\n")
        remaining = string[location:]
        line_end = remaining.index("\n") if "\n" in remaining else None
        log.debug("====")
        log.debug("  Parse line {0}".format(lineno))
        log.debug("  '{0}'".format(remaining[:line_end]))
        log.debug("====")
    line.setDebugActions(debug_line, None, None)

IDENTIFIERS = {"A": 0x0, "B": 0x1, "C": 0x2, "X": 0x3, "Y": 0x4, "Z": 0x5,
               "I": 0x6, "J": 0x7,
               "POP": 0x18, "PEEK": 0x19, "PUSH": 0x1A,
               "SP": 0x1B, "PC": 0x1C,
               "O": 0x1D}
OPCODES = {"SET": 0x1, "ADD": 0x2, "SUB": 0x3, "MUL": 0x4, "DIV": 0x5,
           "MOD": 0x6, "SHL": 0x7, "SHR": 0x8, "AND": 0x9, "BOR": 0xA,
           "XOR": 0xB, "IFE": 0xC, "IFN": 0xD, "IFG": 0xE, "IFB": 0xF}
        
def process_operand(o, lvalue=False):
    """
    Returns (a, x) where a is a value which identifies the nature of the value
    and x is either None or a word to be inserted directly into the output stream
    (e.g. a literal value >= 0x20)
    """
    # TODO(pwaller): Reject invalid lvalues
    
    def invalid_op(reason):
        # TODO(pwaller): Need to indicate origin of error
        return RuntimeError("Invalid operand, {0}: {1}"
                            .format(reason, o.asXML()))

    def check_indirect_register(register):
        if register not in "ABCXYZIJ":
            raise invalid_op("only registers A-J can be used for indirection")

    if o.basic:
        # Literals, stack ops, registers
        b = o.basic
        if b.register:
            return IDENTIFIERS[b.register], None
            
        elif b.stack_op:
            return IDENTIFIERS[b.stack_op], None
            
        elif b.literal is not None:
            l = b.literal
            if not isinstance(l, basestring) and l < 0x20:
                return 0x20 | l, None
            if l == "": raise invalid_op("this is a bug")
            if isinstance(l, int) and not 0 <= l <= WORD_MAX:
                raise invalid_op("literal exceeds word size")
            return 0x1F, l
            
    elif o.indirect:
        i = o.indirect
        if i.basic:
            # [register], [literal]
            ib = i.basic
            if ib.register:
                check_indirect_register(ib.register)
                return 0x8 + IDENTIFIERS[ib.register], None
            
            elif ib.stack_op:
                raise invalid_op("don't use PUSH/POP/PEEK with indirection")
                
            
            elif ib.literal is not None:
                return 0x1E, ib.literal
            
        elif i.expr:
            # [register+literal]
            ie = i.expr
            check_indirect_register(ie.register)
            return 0x10 | IDENTIFIERS[ie.register], ie.literal
    
    raise invalid_op("this is a bug")

def codegen(source, input_filename="<unknown>"):
    
    try:
        parsed = full_grammar.parseString(source)
    except P.ParseException as exc:
        log.fatal("Parse error:")
        log.fatal("  {0}:{1}:{2} HERE {3}"
                  .format(input_filename, exc.lineno, exc.col,
                          exc.markInputline()))
        return None
    
    log.debug("=====")
    log.debug("  Successful parse, XML syntax interpretation:")
    log.debug("=====")
    log.debug(parsed.asXML())
    
    labels = {}
    macros = {}
    program = []
    # Number of times a given macro has been called so that we can generate
    # unique labels
    n_macro_calls = defaultdict(int)
    
    def process_macro_definition(statement):
        log.debug("Macro definition: {0}".format(statement.asXML()))
        macros[statement.name] = statement
        
    def process_macro_call(offset, statement, context=""):
        log.debug("--------------")
        log.debug("Macro call: {0}".format(statement.asXML()))
        log.debug("--------------")
        
        macroname = statement.name
        macro = macros.get(macroname, None)
        n_macro_calls[macroname] += 1
        context = context + macroname + str(n_macro_calls[macroname])
        
        if not macro:
            raise RuntimeError("Call to undefined macro: {0}".format(macroname))
        
        assert len(macro.args) == len(statement.args), (
            "Wrong number of arguments to macro call {0!r}".format(macroname))
        
        # TODO(pwaller): Check for collisions between argument name and code 
        #                label
        args = {}
        
        log.debug("Populated args:")
        for name, arg in zip(macro.args, statement.args):
            args[name] = arg
            log.debug("  - {0}: {1}".format(name, arg)) 
         
        lines = []
        
        for l in macro.lines:
            new_line = l.copy()
            s = l.statement
            if s:
                new_statement = s.copy()
                new_line["statement"] = new_statement
            #if l.label: new_line["label"] = context + l.label
            
            # Replace literals whose names are macro arguments
            # also, substitute labels with (context, label).
            # Resolution of a label happens later by first searching for a label
            # called `context + label`, and if it doesn't exist `label` is used.
            if s and s.first and s.first.basic and s.first.basic.literal:
                if s.first.basic.literal in args:
                    new_statement["first"] = args[s.first.basic.literal]
                elif isinstance(s.first.basic.literal, basestring):
                    new_basic = s.first.basic.copy()
                    new_basic["literal"] = context, s.first.basic.literal
                    new_op = new_statement.first.copy()
                    new_op["basic"] = new_basic
                    new_statement["first"] = new_op
                    
            if s and s.second and s.second.basic and s.second.basic.literal:
                if s.second.basic.literal in args:
                    new_statement["second"] = args[s.second.basic.literal]
                elif isinstance(s.second.basic.literal, basestring):
                    new_basic = s.second.basic.copy()
                    new_basic["literal"] = context, s.second.basic.literal
                    new_op = new_statement.second.copy()
                    new_op["basic"] = new_basic
                    new_statement["second"] = new_op
                    
            # Replace macro call arguments
            if s and s.macro_call:
                new_macro_call = s.macro_call.copy()
                new_statement["macro_call"] = new_macro_call
                new_macro_call_args = s.macro_call.args.copy()
                new_statement.macro_call["args"] = new_macro_call_args
                for i, arg in enumerate(s.macro_call.args):
                    if arg.basic.literal not in args:
                        continue
                    new_macro_call_args[i] = args[arg.basic.literal]
                
                        
            lines.append(new_line)
        
        log.debug("Populated macro: {0}"
                  .format("\n".join(l.dump() for l in lines)))
        
        # Do code generation
        code = []
        for l in lines:
            a = generate(offset + len(code), l, context)
            log.debug("Codegen for statement: {0}".format(l.asXML()))
            log.debug("  Code: {0}".format(a))
            code.extend(a)
        return code
        
    def generate(offset, line, context=""):
        log.debug("Interpreting element {0}: {1}".format(i, line))
        if line.label:
            label = context + line.label
            if label in labels:
                # TODO(pwaller): Line indications
                msg = "Duplicate label definition! {0}".format(label)
                log.fatal(msg)
                raise RuntimeError(msg)
            labels[label] = offset
            
        s = line.statement
        if not s: return []
        
        if s.macro_definition:
            process_macro_definition(s.macro_definition)
            return []
        elif s.macro_call:
            return process_macro_call(offset, s.macro_call, context)
            
        log.debug("Generating for {0}".format(s.asXML(formatted=False)))
        if s.opcode == "DAT":
            return s.data
        
        if s.opcode == "JSR":
            o = 0x00
            a, x = 0x01, None
            b, y = process_operand(s.first)
            
        else:
            o = OPCODES[s.opcode]
            a, x = process_operand(s.first, lvalue=True)
            b, y = process_operand(s.second)
        
        code = []
        code.append(((b << 10) + (a << 4) + o))
        if x is not None: code.append(x)
        if y is not None: code.append(y)
        return code
    
    for i, line in enumerate(parsed):
        program.extend(generate(len(program), line))
    
    log.debug("Labels: {0}".format(labels))
    
    log.debug("program: {0}".format(program))
    
    # Substitute labels
    for i, c in enumerate(program):
        if isinstance(c, basestring):
            if c not in labels:
                raise RuntimeError("Undefined label used: {0}".format(c))
            program[i] = labels[c]
        elif isinstance(c, tuple):
            context, label = c
            if context + label in labels:
                label = context + label
            if label not in labels:
                raise RuntimeError("Undefined label used: {0}".format(c))
            program[i] = labels[label]
    
    # Turn words into bytes
    result = bytes()
    for word in program:
        result += struct.pack(">H", word)
    return result

def main():
    parser = argparse.ArgumentParser(
        description='A simple pyparsing-based DCPU assembly compiler')
    parser.add_argument(
        'source', metavar='IN', type=str,
        help='file path of the file containing the assembly code')
    parser.add_argument(
        'destination', metavar='OUT', type=str, nargs='?',
        help='file path where to store the binary code')
    args = parser.parse_args()
    
    if not log.handlers:
        from sys import stderr
        handler = logging.StreamHandler(stderr)
        log.addHandler(handler)
        if not DEBUG: handler.setLevel(logging.INFO)
    
    if args.source == "-":
        program = codegen(sys.stdin.read(), "<stdin>")
    else:
        with open(args.source) as fd:
            program = codegen(fd.read(), args.source)
    
    if program is None:
        log.fatal("No program produced.")
        if not DEBUG:
            log.fatal("Run with DEBUG=1 ./asm_pyparsing.py "
                      "for more information.")
        return 1
    
    if not args.destination:
        if os.isatty(sys.stdout.fileno()):
            log.fatal("stdout is a tty, not writing binary. "
                      "Specify destination file or pipe output somewhere")
        else:
            sys.stdout.write(program)
    else:
        with open(args.destination, "wb") as fd:
            fd.write(program)
    log.info("Program written to {0} ({1} bytes, hash={2})"
             .format(args.destination, len(program),
                     hex(abs(hash(program)))))
            
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

########NEW FILE########
__FILENAME__ = dcpu16
#!/usr/bin/env python

import argparse
import importlib
import inspect
import struct
import sys
import time
import emuplugin
import disasm


try:
    raw_input
except NameError:
    raw_input = input


# offsets into DCPU16.memory corresponding to addressing mode codes
SP, PC, O, LIT = 0x1001B, 0x1001C, 0x1001D, 0x1001E


def opcode(code):
    """A decorator for opcodes"""
    def decorator(func):
        setattr(func, "_is_opcode", True)
        setattr(func, "_opcode", code)
        return func
    
    return decorator


class DCPU16:
    
    def __init__(self, memory, plugins=[]):
        
        self.plugins = plugins
        
        self.memory = [memory[i] if i < len(memory) else 0 for i in range(0x1001F)]
        
        self.skip = False
        self.cycle = 0
        
        self.opcodes = {}
        for name, value in inspect.getmembers(self):
            if inspect.ismethod(value) and getattr(value, "_is_opcode", False):
                self.opcodes[getattr(value, "_opcode")] = value 
    
    @opcode(0x01)
    def SET(self, a, b):
        self.memory[a] = b
        self.cycle += 1
    
    @opcode(0x02)
    def ADD(self, a, b):
        o, r = divmod(self.memory[a] + b, 0x10000)
        self.memory[O] = o
        self.memory[a] = r
        self.cycle += 2
    
    @opcode(0x03)
    def SUB(self, a, b):
        o, r = divmod(self.memory[a] - b, 0x10000)
        self.memory[O] = 0xFFFF if o == -1 else 0x0000
        self.memory[a] = r
        self.cycle += 2
    
    @opcode(0x04)
    def MUL(self, a, b):
        o, r = divmod(self.memory[a] * b, 0x10000)
        self.memory[a] = r
        self.memory[O] = o % 0x10000
        self.cycle += 2
    
    @opcode(0x05)
    def DIV(self, a, b):
        if b == 0x0:
            r = 0x0
            o = 0x0
        else:
            r = self.memory[a] / b % 0x10000
            o = ((self.memory[a] << 16) / b) % 0x10000
        self.memory[a] = r
        self.memory[O] = o
        self.cycle += 3
    
    @opcode(0x06)
    def MOD(self, a, b):
        if b == 0x0:
            r = 0x0
        else:
            r = self.memory[a] % b
        self.memory[a] = r
        self.cycle += 3
    
    @opcode(0x07)
    def SHL(self, a, b):
        o, r = divmod(self.memory[a] << b, 0x10000)
        self.memory[a] = r
        self.memory[O] = o % 0x10000
        self.cycle += 2
    
    @opcode(0x08)
    def SHR(self, a, b):
        r = self.memory[a] >> b
        o = ((self.memory[a] << 16) >> b) % 0x10000
        self.memory[a] = r
        self.memory[O] = o
        self.cycle += 2
    
    @opcode(0x09)
    def AND(self, a, b):
        self.memory[a] = self.memory[a] & b
        self.cycle += 1
    
    @opcode(0x0a)
    def BOR(self, a, b):
        self.memory[a] = self.memory[a] | b
        self.cycle += 1
    
    @opcode(0x0b)
    def XOR(self, a, b):
        self.memory[a] = self.memory[a] ^ b
        self.cycle += 1
    
    @opcode(0x0c)
    def IFE(self, a, b):
        self.skip = not (self.memory[a] == b)
        self.cycle += 2 + 1 if self.skip else 0
    
    @opcode(0x0d)
    def IFN(self, a, b):
        self.skip = not (self.memory[a] != b)
        self.cycle += 2 + 1 if self.skip else 0
    
    @opcode(0x0e)
    def IFG(self, a, b):
        self.skip = not (self.memory[a] > b)
        self.cycle += 2 + 1 if self.skip else 0
    
    @opcode(0x0f)
    def IFB(self, a, b):
        self.skip = not ((self.memory[a] & b) != 0)
        self.cycle += 2 + 1 if self.skip else 0
    
    @opcode(0x010)
    def JSR(self, a, b):
        self.memory[SP] = (self.memory[SP] - 1) % 0x10000
        pc = self.memory[PC]
        self.memory[self.memory[SP]] = pc
        self.memory[PC] = b
        self.cycle += 2
    
    def get_operand(self, a, dereference=False):
        literal = False
        if a < 0x08 or 0x1B <= a <= 0x1D:
            arg1 = 0x10000 + a
        elif a < 0x10:
            arg1 = self.memory[0x10000 + (a % 0x08)]
        elif a < 0x18:
            next_word = self.memory[self.memory[PC]]
            self.memory[PC] += 1
            arg1 = next_word + self.memory[0x10000 + (a % 0x10)]
            self.cycle += 0 if self.skip else 1
        elif a == 0x18:
            arg1 = self.memory[SP]
            if not self.skip:
                self.memory[SP] = (self.memory[SP] + 1) % 0x10000
        elif a == 0x19:
            arg1 = self.memory[SP]
        elif a == 0x1A:
            if not self.skip:
                self.memory[SP] = (self.memory[SP] - 1) % 0x10000
            arg1 = self.memory[SP]
        elif a == 0x1E:
            arg1 = self.memory[self.memory[PC]]
            self.memory[PC] += 1
            self.cycle += 0 if self.skip else 1
        elif a == 0x1F:
            arg1 = self.memory[PC]
            self.memory[PC] += 1
            self.cycle += 0 if self.skip else 1
        else:
            literal = True
            arg1 = a % 0x20
            if not dereference:
                self.memory[LIT] = arg1
                arg1 = LIT
        
        if dereference and not literal:
            arg1 = self.memory[arg1]
        return arg1
    
    def run(self, trace=False, show_speed=False):
        tick = 0
        last_time = time.time()
        last_cycle = self.cycle
        if trace:
            disassembler = disasm.Disassembler(self.memory)
        
        while True:
            pc = self.memory[PC]
            w = self.memory[pc]
            self.memory[PC] += 1
            
            operands, opcode = divmod(w, 16)
            b, a = divmod(operands, 64)
            
            if trace:
                disassembler.offset = pc
                print("(%08X) %s" % (self.cycle, disassembler.next_instruction()))
            
            if opcode == 0x00:
                if a == 0x00:
                    break
                arg1 = None
                opcode = (a << 4) + 0x0
            else:
                arg1 = self.get_operand(a)
            
            op = self.opcodes[opcode]
            arg2 = self.get_operand(b, dereference=True)
            
            if self.skip:
                if trace:
                    print("skipping")
                self.skip = False
            else:
                if 0x01 <= opcode <=0xB: # write to memory
                    oldval = self.memory[arg1]
                    op(arg1, arg2)
                    val = self.memory[arg1]
                    if oldval != val:
                        for p in self.plugins:
                            p.memory_changed(self, arg1, val, oldval)
                else:
                    op(arg1, arg2)
                if trace:
                    self.dump_registers()
                    self.dump_stack()
            
            tick += 1
            if tick >= 100000:
                if show_speed:
                    print("%dkHz" % (int((self.cycle - last_cycle) / (time.time() - last_time)) / 1000))
                last_time = time.time()
                last_cycle = self.cycle
                tick = 0
            try:
                for p in self.plugins:
                    p.tick(self)
            except SystemExit:
                break
    
    def dump_registers(self):
        print(" ".join("%s=%04X" % (["A", "B", "C", "X", "Y", "Z", "I", "J"][i],
            self.memory[0x10000 + i]) for i in range(8)))
        print("PC={0:04X} SP={1:04X} O={2:04X}".format(*[self.memory[i] for i in (PC, SP, O)]))
    
    def dump_stack(self):
        if self.memory[SP] == 0x0:
            print("Stack: []")
        else:
            print("Stack: [" + " ".join("%04X" % self.memory[m] for m in range(self.memory[SP], 0x10000)) + "]")


if __name__ == "__main__":
    plugins = emuplugin.importPlugins()
    parser = argparse.ArgumentParser(description="DCPU-16 emulator")
    parser.add_argument("-d", "--debug", action="store_const", const=True, default=False, help="Run emulator in debug mode. This implies '--trace'")
    parser.add_argument("-t", "--trace", action="store_const", const=True, default=False, help="Print dump of registers and stack after every step")
    parser.add_argument("-s", "--speed", action="store_const", const=True, default=False, help="Print speed the emulator is running at in kHz")
    parser.add_argument("object_file", help="File with assembled DCPU binary")
    
    for p in plugins:
        for args in p.arguments:
            parser.add_argument(*args[0], **args[1])
    
    args = parser.parse_args()
    if args.debug:
        args.trace = True
    
    program = []
    with open(args.object_file, "rb") as f:
        word = f.read(2)
        while word:
            program.append(struct.unpack(">H", word)[0])
            word = f.read(2)
    
    plugins_loaded = []
    try:
        for p in plugins:
            p = p(args)
            if p.loaded:
                print("Started plugin: %s" % p.name)
                plugins_loaded.append(p)
        
        dcpu16 = DCPU16(program, plugins_loaded)
        
        dcpu16.run(trace=args.trace, show_speed=args.speed)
    except KeyboardInterrupt:
        pass
    finally:
        for p in plugins_loaded:
            p.shutdown()

########NEW FILE########
__FILENAME__ = disasm
#!/usr/bin/env python

from __future__ import print_function

import struct
import sys
import argparse


INSTRUCTIONS = [None, "SET", "ADD", "SUB", "MUL", "DIV", "MOD", "SHL", "SHR", "AND", "BOR", "XOR", "IFE", "IFN", "IFG", "IFB"]
IDENTIFERS = ["A", "B", "C", "X", "Y", "Z", "I", "J", "POP", "PEEK", "PUSH", "SP", "PC", "O"]


class Disassembler:
    
    def __init__(self, program, output=sys.stdout):
        self.program = program
        self.offset = 0
        self.output = output
    
    def next_word(self):
        w = self.program[self.offset]
        self.offset += 1
        return w
    
    def format_operand(self, operand):
        if operand < 0x08:
            return "%s" % IDENTIFERS[operand]
        elif operand < 0x10:
            return "[%s]" % IDENTIFERS[operand % 0x08]
        elif operand < 0x18:
            return "[0x%02x + %s]" % (self.next_word(), IDENTIFERS[operand % 0x10])
        elif operand < 0x1E:
            return "%s" % IDENTIFERS[operand % 0x10]
        elif operand == 0x1E:
            return "[0x%02x]" % self.next_word()
        elif operand == 0x1F:
            return "0x%02x" % self.next_word()
        else:
            return "0x%02x" % (operand % 0x20)
    
    def next_instruction(self):
        offset = self.offset
        w = self.next_word()
            
        operands, opcode = divmod(w, 16)
        b, a = divmod(operands, 64)
            
        if opcode == 0x00:
            if a == 0x01:
                first = "JSR"
            else:
                return
        else:
            first = "%s %s," % (INSTRUCTIONS[opcode], self.format_operand(a))
            
        asm = "%s %s" % (first, self.format_operand(b))
        binary = " ".join("%04x" % word for word in self.program[offset:self.offset])
        return "%-40s ; %04x: %s" % (asm, offset, binary)
        
    def run(self):
        while self.offset < len(self.program):
            print(self.next_instruction(), file=self.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DCPU-16 disassembler")
    parser.add_argument("-o", help="Place the output into FILE instead of stdout", metavar="FILE")
    parser.add_argument("input", help="File with DCPU object code")
    args = parser.parse_args()
    
    program = []
    if args.input == "-":
        f = sys.stdin
    else:
        f = open(args.input, "rb")
    word = f.read(2)
    while word:
        program.append(struct.unpack(">H", word)[0])
        word = f.read(2)
    
    output = sys.stdout if args.o is None else open(args.o, "w")
    d = Disassembler(program, output=output)
    d.run()

########NEW FILE########
__FILENAME__ = emuplugin
import threading
import glob, imp
from os.path import join, basename, splitext, dirname

PLUGINS_DIR = join(dirname(__file__), "plugins")

def importPlugins(dir = PLUGINS_DIR):
    # http://tinyurl.com/cfceawr
    return [_load(path).plugin for path in glob.glob(join(dir,'[!_]*.py'))]

def _load(path):
    # http://tinyurl.com/cfceawr
    name, ext = splitext(basename(path))
    return imp.load_source(name, path)
    

class BasePlugin:
    """
        Plugin module to interface with a cpu core.

        
        Signaling a shutdown should be done via raising SystemExit within tick()
    """
    
    # Specify if you want to use a different name class name
    name = None
    
    # List in the format of [(*args, *kwargs)]
    arguments = []
    
    # Set in __init__ if you do not wish to have been "loaded" or called
    loaded = True
    
    def tick(self, cpu):
        """
            Gets called at the end of every cpu tick
        """
        pass
    
    def shutdown(self):
        """
            Gets called on shutdown of the emulator
        """
        pass
    
    def memory_changed(self, cpu, address, value, oldvalue):
        """
            Gets called on a write to memory
        """
        pass
    
    def __init__(self, args=None):
        self.name = self.__class__.__name__ if not self.name else self.name

# Assign this to your plugin class
plugin = None

########NEW FILE########
__FILENAME__ = debuggerplugin
from emuplugin import BasePlugin
import dcpu16

try:
    raw_input
except NameError:
    # Python3 raw_input was renamed to input
    raw_input = input

class DebuggerPlugin(BasePlugin):
    """
        A plugin to implement a debugger
    """
    
    def __init__(self, args):
        """
            Enable debugger if args.debug is True
        """
        BasePlugin.__init__(self)
        self.loaded = args.debug
        self.debugger_breaks = set()
        self.debugger_in_continue = False
    
    def tick(self, cpu):
        self.cpu = cpu
        if not self.debugger_in_continue or cpu.memory[dcpu16.PC] in self.debugger_breaks:
            self.debugger_in_continue = False
            while True:
                try:
                    command = [s.lower() for s in raw_input("debug> ").split()]
                except EOFError:
                    # Ctrl-D
                    print("")
                    raise SystemExit
                try:
                    if not command or command[0] in ("step", "st"):
                        break
                    elif command[0] == "help":
                        help_msg = """Commands:
help
st[ep] - (or simply newline) - execute next instruction
g[et] <address>|%<register> - (also p[rint]) - print value of memory cell or register
s[et] <address>|%<register> <value_in_hex> - set value of memory cell or register to <value_in_hex>
b[reak] <address> [<address2>...] - set breakpoint at given addresses (to be used with 'continue')
cl[ear] <address> [<address2>...] - remove breakpoints from given addresses
c[ont[inue]] - run without debugging prompt until breakpoint is encountered

All addresses are in hex (you can add '0x' at the beginning)
Close emulator with Ctrl-D
"""
                        print(help_msg)
                    elif command[0] in ("get", "g", "print", "p"):
                        self.debugger_get(*command[1:])
                    elif command[0] in ("set", "s"):
                        self.debugger_set(*command[1:])
                    elif command[0] in ("break", "b"):
                        if len(command) < 2:
                            raise ValueError("Break command takes at least 1 parameter!")
                        self.debugger_break(*command[1:])
                    elif command[0] in ("clear", "cl"):
                        self.debugger_clear(*command[1:])
                    elif command[0] in ("continue", "cont", "c"):
                        self.debugger_in_continue = True
                        break
                    else:
                        raise ValueError("Invalid command!")
                except ValueError as ex:
                    print(ex)
    
    @staticmethod
    def debugger_parse_location(what):
        registers = "abcxyzij"
        specials = ("pc", "sp", "o")
        if what.startswith("%"):
            what = what[1:]
            if what in registers:
                return  0x10000 + registers.find(what)
            elif what in specials:
                return  (dcpu16.PC, dcpu16.SP, dcpu16.O)[specials.index(what)]
            else:
                raise ValueError("Invalid register!")
        else:
            addr = int(what, 16)
            if not 0 <= addr <= 0xFFFF:
                raise ValueError("Invalid address!")
            return addr
    
    def debugger_break(self, *addrs):
        breaks = set()
        for addr in addrs:
            addr = int(addr, 16)
            if not 0 <= addr <= 0xFFFF:
                raise ValueError("Invalid address!")
            breaks.add(addr)
        self.debugger_breaks.update(breaks)
    
    def debugger_clear(self, *addrs):
        if not addrs:
            self.debugger_breaks = set()
        else:
            breaks = set()
            for addr in addrs:
                addr = int(addr, 16)
                if not 0 <= addr <= 0xFFFF:
                    raise ValueError("Invalid address!")
                breaks.add(addr)
            self.debugger_breaks.difference_update(breaks)
    
    def debugger_set(self, what, value):
        value = int(value, 16)
        if not 0 <= value <= 0xFFFF:
            raise ValueError("Invalid value!")
        addr = self.debugger_parse_location(what)
        self.cpu.memory[addr] = value
    
    def debugger_get(self, what):
        addr = self.debugger_parse_location(what)
        value = self.cpu.memory[addr]
        print("hex: {hex}\ndec: {dec}\nbin: {bin}".format(hex=hex(value), dec=value, bin=bin(value)))

plugin = DebuggerPlugin

########NEW FILE########
__FILENAME__ = terminalplugin
from emuplugin import BasePlugin
import importlib
import sys
import time
import os
import re

START_ADDRESS = 0x8000
MIN_DISPLAY_HZ = 60

class TerminalPlugin(BasePlugin):
    """
        A plugin to implement terminal selection
    """
    
    arguments = [
            (["--term"], dict(action="store", default="null", help="Terminal to use (e.g. null, pygame)")),
            (["--geometry"], dict(action="store", default="80x24", help="Geometry given as `width`x`height`", metavar="SIZE"))]
    
    def processkeys(self, cpu):
        keyptr = 0x9000
        for i in range(0, 16):
            if not cpu.memory[keyptr + i]:
                try:
                    key = self.term.keys.pop()
                except IndexError:
                    break
                cpu.memory[keyptr + i] = key
    
    def tick(self, cpu):
        """
            Update the display every .1s or always if debug is on
        """
        if self.debug or not self.time or (time.time() - self.time >= 1.0/float(MIN_DISPLAY_HZ)):
            self.time = time.time()
            self.term.redraw()
        self.term.updatekeys()
        if self.term.keys:
            self.processkeys(cpu)
    
    def memory_changed(self, cpu, address, value, oldval):
        """
            Inform the terminal that the memory is updated
        """
        if START_ADDRESS <= address <= START_ADDRESS + self.term.width * self.term.height:
            row, column = divmod(address - START_ADDRESS, self.term.width)
            ch = value % 0x0080
            ch = ord(' ') if not ch else ch
            fg = (value & 0x4000) >> 14 | (value & 0x2000) >> 12 | (value & 0x1000) >> 10
            bg = (value & 0x400) >> 10 | (value & 0x200) >> 8 | (value & 0x100) >> 6
            self.term.update_character(row, column, ch, (fg, bg))
    
    def shutdown(self):
        """
            Shutdown the terminal
        """
        self.term.quit()
    
    def __init__(self, args):
        """
            Create a terminal based on the term argument
        """
        if args.term == "null":
            self.loaded = False
            return
        BasePlugin.__init__(self)
        self.time = None
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "terminals")))
        try:
            terminal = importlib.import_module(args.term + "_terminal")
        except ImportError as e:
            print("Terminal %s not available: %s" % (args.term, e))
            raise SystemExit
        self.debug = args.debug

        m = re.match(r"(\d+)x(\d+)", args.geometry)
        if m is None:
            print("Invalid geometry `%s`" % args.geometry)
            args.width, args.height = 80, 24
        else:
            args.width = int(m.group(1))
            args.height = int(m.group(2))

        self.term = terminal.Terminal(args)
        self.name += "-%s" % args.term
        self.term.show()

plugin = TerminalPlugin

########NEW FILE########
__FILENAME__ = curses-bold_terminal
import curses_terminal

class Terminal(curses_terminal.Terminal):
    style_bold = True

########NEW FILE########
__FILENAME__ = curses_terminal
import curses


class Terminal:
    style_bold = False
    keymap = {'A': 0x3, 'C': 0x2, 'D': 0x1}

    def setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        self.colors = {}
        self.colors[(0, 0)] = 0
        self.colors[(7, 0)] = 0
        self.color_index = 1
        self.win.bkgd(curses.color_pair(0))

    def __init__(self, args):
        if args.debug:
            print("Curses conflicts with debugger")
            raise SystemExit
        self.win = curses.initscr()
        self.win.nodelay(1)
        self.win_height, self.win_width = self.win.getmaxyx()

        curses.curs_set(0)
        curses.noecho()
        self.width = args.width
        self.height = args.height
        self.keys = []
        self.setup_colors()

    def get_color(self, fg, bg):
        if (fg, bg) not in self.colors:
            curses.init_pair(self.color_index, fg, bg)
            self.colors[(fg, bg)] = self.color_index
            self.color_index += 1

        return self.colors[(fg, bg)]

    def update_character(self, row, column, character, color=None):
        try:
            pair = 0
            if color:
                pair = self.get_color(*color)
            color = curses.color_pair(pair)
            if self.style_bold:
                color |= curses.A_BOLD
            self.win.addch(row, column, character, color)
        except curses.error:
            pass

    def show(self):
        color = curses.color_pair(self.get_color(3, -1))

        if self.win_width > self.width:
            try:
                s = '.'*(self.win_width - self.width)
                for y in range(self.height):
                    self.win.addstr(y, self.width, s, color)
            except curses.error:
                pass

        if self.win_height > self.height:
            try:
                s = '.'*(self.win_width)
                for y in range(self.height, self.win_height):
                    self.win.addstr(y, 0, s, color)
            except curses.error:
                pass

    def updatekeys(self):
        try:
            # XXX: this is probably a bad place to check if the window has
            # resized but there is no other opportunity to do this
            win_height, win_width = self.win.getmaxyx()
            if win_height != self.win_height or win_width != self.win_width:
                self.win_height, self.win_width = win_height, win_width
                self.show()

            while(True):
                char = self.win.getkey()
                if len(char) == 1:
                    c = self.keymap[char] if char in self.keymap else ord(char)
                    self.keys.insert(0, c)
        except curses.error:
            pass

    def redraw(self):
        self.win.refresh()

    def quit(self):
        curses.endwin()

########NEW FILE########
__FILENAME__ = debug_terminal
WIDTH = 80
HEIGHT = 24

class Terminal:
    width = WIDTH
    height = HEIGHT
    keys = []
    
    def __init__(self, args):
        pass
    
    def update_character(self, row, column, character, color=None):
        print("TERMINAL (%d,%d:'%s') %s" % (column, row, chr(character), str(color)))
    
    def show(self):
        pass
    
    def updatekeys(self):
        pass
    
    def redraw(self):
        pass
    
    def quit(self):
        pass

########NEW FILE########
__FILENAME__ = pygame_terminal
import pygame

class Terminal:
    
    COLORS = [(0,0,0), (255,0,0), (0,255,0), (255,255,0), (0,0,255), (255,0,255), (0, 255, 255), (255, 255, 255)]
    
    def __init__(self, args):
        self.width = args.width
        self.height = args.height
        self.keys = []
        pygame.font.init()
        self.font = pygame.font.match_font("Monospace,dejavusansmono")
        self.font = pygame.font.get_default_font() if not self.font else self.font
        self.font = pygame.font.Font(self.font, 12)
        self.cell_width = max([self.font.metrics(chr(c))[0][1] for c in range(0, 128)])
        self.cell_height = self.font.get_height()
        win_width = self.cell_width * args.width
        win_height = self.cell_height * args.height
        self.screen = pygame.display.set_mode((win_width, win_height))
    
    def update_character(self, row, column, character, color=None):
        if not color or (not color[0] and not color[1]):
            fgcolor = self.COLORS[7]
            bgcolor = self.COLORS[0]
        else:
            fgcolor = self.COLORS[color[0]]
            bgcolor = self.COLORS[color[1]]
        surf = pygame.Surface((self.cell_width, self.cell_height))
        surf.fill(pygame.Color(*bgcolor))
        char = self.font.render(chr(character), True, fgcolor)
        surf.blit(char, (1, 1))
        self.screen.blit(surf, (column*self.cell_width, row*self.cell_height))
    
    def show(self):
        pass
    
    def updatekeys(self):
        events = pygame.event.get(pygame.KEYDOWN)
        for e in events:
            key = e.unicode
            if key:
                self.keys.insert(0, ord(e.unicode))
    
    def redraw(self):
        pygame.display.flip()
    
    def quit(self):
        pass

########NEW FILE########
__FILENAME__ = qt_terminal
import sys
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

# Ensure that the QT application does not try to handle (and spam) the KeyboardInterrupt
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

class Terminal(QtGui.QWidget):
    COLORS = [(0,0,0), (255,0,0), (0,255,0), (255,255,0), (0,0,255), (255,0,255), (0, 255, 255), (255, 255, 255)]
    
    def __init__(self, args):
        self.width = args.width
        self.height = args.height
        self.keys = []
        self.app = QtGui.QApplication(sys.argv)
        super(Terminal, self).__init__()
        
        self.font = QtGui.QFont("Monospace", 10)
        self.font.setStyleHint(QtGui.QFont.TypeWriter)
        font_metrics = QtGui.QFontMetrics(self.font)
        self.cell_width = font_metrics.maxWidth() + 2
        self.cell_height = font_metrics.height()
        win_width = self.cell_width * args.width
        win_height = self.cell_height * args.height

        self.pixmap_buffer = QtGui.QPixmap(win_width, win_height)
        self.pixmap_buffer.fill(Qt.black)
        
        self.resize(win_width, win_height)
        self.setMinimumSize(win_width, win_height)
        self.setMaximumSize(win_width, win_height)
        self.setWindowTitle("DCPU-16 terminal")
        
        self.app.setQuitOnLastWindowClosed(False)
        self.closed = False
    
    def update_character(self, row, column, character, color=None):
        char = chr(character)
        x = column * self.cell_width
        y = row * self.cell_height
        
        qp = QtGui.QPainter(self.pixmap_buffer)
        qp.setFont(self.font)
        if not color or (not color[0] and not color[1]):
            fgcolor = self.COLORS[7]
            bgcolor = self.COLORS[0]
        else:
            fgcolor = self.COLORS[color[0]]
            bgcolor = self.COLORS[color[1]]
        qp.fillRect(x, y, self.cell_width, self.cell_height, QtGui.QColor(*bgcolor))
        qp.setPen(QtGui.QColor(*fgcolor))
        qp.drawText(x, y, self.cell_width, self.cell_height, Qt.AlignCenter, char)
        qp.end()
    
    def closeEvent(self, e):
        self.closed = True
    
    def keyPressEvent(self, e):
        for c in str(e.text()):
            self.keys.insert(0, ord(c))
    
    def updatekeys(self):
        pass
    
    def redraw(self):
        if self.closed:
            raise SystemExit
        self.update()
        self.app.processEvents()
    
    def quit(self):
        self.app.quit()
    
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.drawPixmap(0, 0, self.pixmap_buffer)
        qp.end()

########NEW FILE########
__FILENAME__ = tests
import nose.tools as nose
import os
import subprocess


ASSEMBLY_OUTPUT = "__test_output.obj"
SOURCE_DIR = "examples"
BINARY_DIR = "test_binaries"

def tearDownModule():
    if os.path.exists(ASSEMBLY_OUTPUT):
        os.remove(ASSEMBLY_OUTPUT)

def example(name):
    return os.path.join(SOURCE_DIR, name + ".asm")

def check_path(assembler, path):
    code = subprocess.call([assembler, path, ASSEMBLY_OUTPUT])
    nose.assert_equal(code, 0, "Assembly of {0} failed!".format(path))
    
    assert path.endswith(".asm")
    binary = os.path.join(BINARY_DIR, os.path.basename(path)[:-4] + ".bin")
    if os.path.exists(binary):
        with open(ASSEMBLY_OUTPUT, "rb") as testing, open(binary, "rb") as tested:
            nose.assert_equal(testing.read(), tested.read(), "Produced and tested binaries differ!")


# asm.py
def test_example_asm():
    check_path("./asm.py", "example.asm")

def test_hello_asm():
    check_path("./asm.py", example("hello"))

def test_hello2_asm():
    check_path("./asm.py", example("hello2"))

def test_fibonacci_asm():
    check_path("./asm.py", example("ique_fibonacci"))


# asm_pyparsing.py
def test_example_pyparsing():
    check_path("./asm_pyparsing.py", "example.asm")

def test_hello_pyparsing():
    check_path("./asm_pyparsing.py", example("hello"))

def test_hello2_pyparsing():
    check_path("./asm_pyparsing.py", example("hello2"))

def test_fibonacci_pyparsing():
    check_path("./asm_pyparsing.py", example("ique_fibonacci"))

########NEW FILE########
