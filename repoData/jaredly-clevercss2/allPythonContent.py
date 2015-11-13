__FILENAME__ = backwards
#!/usr/bin/env python

import cssutils
import logging
cssutils.log.setLevel(logging.FATAL)

def parseCSS(text):
    parser = cssutils.CSSParser()
    css = parser.parseString(text)
    rules = {}
    for rule in css.cssRules:
        commas = rule.selectorText.split(',')
        for comma in commas:
            parts = comma.split()
            c = rules
            for i, part in enumerate(parts):
                if part in '>+':
                    parts[i+1] = '&' + part + parts[i+1]
                    continue
                c = c.setdefault(part, {})
            c.setdefault(':rules:', []).append(rule)
    return rules

def rulesToCCSS(selector, rules):
    text = selector + ':\n  '
    if rules.get(':rules:'):
        text += '\n\n  '.join('\n  '.join(line.strip().rstrip(';') for line in rule.style.cssText.splitlines()) for rule in rules.get(':rules:', [])) + '\n'
    for other in rules:
        if other == ':rules:':
            continue
        text += '\n  ' + rulesToCCSS(other, rules[other]).replace('\n', '\n  ')
    return text

def cleverfy(fname):
    rules = parseCSS(open(fname).read())
    text = ''
    for rule in rules:
        text += rulesToCCSS(rule, rules[rule]) + '\n\n'
    return text

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = consts
#!/usr/bin/env python

# units and conversions
UNITS = ['em', 'ex', 'px', 'cm', 'mm', 'in', 'pt', 'pc', 'deg', 'rad'
          'grad', 'ms', 's', 'Hz', 'kHz', '%']
CONV = {
    'length': {
        'mm': 1.0,
        'cm': 10.0,
        'in': 25.4,
        'pt': 25.4 / 72,
        'pc': 25.4 / 6
    },
    'time': {
        'ms': 1.0,
        's':  1000.0
    },
    'freq': {
        'Hz':  1.0,
        'kHz': 1000.0
    }
}
UNIT_MAPPING = {}
for measures, units in CONV.iteritems():
    UNIT_MAPPING.update(dict((unit, measures) for unit in units))

# color literals
COLORS = {
    'aliceblue': '#f0f8ff',
    'antiquewhite': '#faebd7',
    'aqua': '#00ffff',
    'aquamarine': '#7fffd4',
    'azure': '#f0ffff',
    'beige': '#f5f5dc',
    'bisque': '#ffe4c4',
    'black': '#000000',
    'blanchedalmond': '#ffebcd',
    'blue': '#0000ff',
    'blueviolet': '#8a2be2',
    'brown': '#a52a2a',
    'burlywood': '#deb887',
    'cadetblue': '#5f9ea0',
    'chartreuse': '#7fff00',
    'chocolate': '#d2691e',
    'coral': '#ff7f50',
    'cornflowerblue': '#6495ed',
    'cornsilk': '#fff8dc',
    'crimson': '#dc143c',
    'cyan': '#00ffff',
    'darkblue': '#00008b',
    'darkcyan': '#008b8b',
    'darkgoldenrod': '#b8860b',
    'darkgray': '#a9a9a9',
    'darkgreen': '#006400',
    'darkkhaki': '#bdb76b',
    'darkmagenta': '#8b008b',
    'darkolivegreen': '#556b2f',
    'darkorange': '#ff8c00',
    'darkorchid': '#9932cc',
    'darkred': '#8b0000',
    'darksalmon': '#e9967a',
    'darkseagreen': '#8fbc8f',
    'darkslateblue': '#483d8b',
    'darkslategray': '#2f4f4f',
    'darkturquoise': '#00ced1',
    'darkviolet': '#9400d3',
    'deeppink': '#ff1493',
    'deepskyblue': '#00bfff',
    'dimgray': '#696969',
    'dodgerblue': '#1e90ff',
    'firebrick': '#b22222',
    'floralwhite': '#fffaf0',
    'forestgreen': '#228b22',
    'fuchsia': '#ff00ff',
    'gainsboro': '#dcdcdc',
    'ghostwhite': '#f8f8ff',
    'gold': '#ffd700',
    'goldenrod': '#daa520',
    'gray': '#808080',
    'green': '#008000',
    'greenyellow': '#adff2f',
    'honeydew': '#f0fff0',
    'hotpink': '#ff69b4',
    'indianred': '#cd5c5c',
    'indigo': '#4b0082',
    'ivory': '#fffff0',
    'khaki': '#f0e68c',
    'lavender': '#e6e6fa',
    'lavenderblush': '#fff0f5',
    'lawngreen': '#7cfc00',
    'lemonchiffon': '#fffacd',
    'lightblue': '#add8e6',
    'lightcoral': '#f08080',
    'lightcyan': '#e0ffff',
    'lightgoldenrodyellow': '#fafad2',
    'lightgreen': '#90ee90',
    'lightgrey': '#d3d3d3',
    'lightpink': '#ffb6c1',
    'lightsalmon': '#ffa07a',
    'lightseagreen': '#20b2aa',
    'lightskyblue': '#87cefa',
    'lightslategray': '#778899',
    'lightsteelblue': '#b0c4de',
    'lightyellow': '#ffffe0',
    'lime': '#00ff00',
    'limegreen': '#32cd32',
    'linen': '#faf0e6',
    'magenta': '#ff00ff',
    'maroon': '#800000',
    'mediumaquamarine': '#66cdaa',
    'mediumblue': '#0000cd',
    'mediumorchid': '#ba55d3',
    'mediumpurple': '#9370db',
    'mediumseagreen': '#3cb371',
    'mediumslateblue': '#7b68ee',
    'mediumspringgreen': '#00fa9a',
    'mediumturquoise': '#48d1cc',
    'mediumvioletred': '#c71585',
    'midnightblue': '#191970',
    'mintcream': '#f5fffa',
    'mistyrose': '#ffe4e1',
    'moccasin': '#ffe4b5',
    'navajowhite': '#ffdead',
    'navy': '#000080',
    'oldlace': '#fdf5e6',
    'olive': '#808000',
    'olivedrab': '#6b8e23',
    'orange': '#ffa500',
    'orangered': '#ff4500',
    'orchid': '#da70d6',
    'palegoldenrod': '#eee8aa',
    'palegreen': '#98fb98',
    'paleturquoise': '#afeeee',
    'palevioletred': '#db7093',
    'papayawhip': '#ffefd5',
    'peachpuff': '#ffdab9',
    'peru': '#cd853f',
    'pink': '#ffc0cb',
    'plum': '#dda0dd',
    'powderblue': '#b0e0e6',
    'purple': '#800080',
    'red': '#ff0000',
    'rosybrown': '#bc8f8f',
    'royalblue': '#4169e1',
    'saddlebrown': '#8b4513',
    'salmon': '#fa8072',
    'sandybrown': '#f4a460',
    'seagreen': '#2e8b57',
    'seashell': '#fff5ee',
    'sienna': '#a0522d',
    'silver': '#c0c0c0',
    'skyblue': '#87ceeb',
    'slateblue': '#6a5acd',
    'slategray': '#708090',
    'snow': '#fffafa',
    'springgreen': '#00ff7f',
    'steelblue': '#4682b4',
    'tan': '#d2b48c',
    'teal': '#008080',
    'thistle': '#d8bfd8',
    'tomato': '#ff6347',
    'turquoise': '#40e0d0',
    'violet': '#ee82ee',
    'wheat': '#f5deb3',
    'white': '#ffffff',
    'whitesmoke': '#f5f5f5',
    'yellow': '#ffff00',
    'yellowgreen': '#9acd32'
}
REV_COLORS = dict((v, k) for k, v in COLORS.iteritems())

CSS_VALUES = 'visible relative solid dotted dashed left right center none transparent block no-repeat absolute hidden visible fixed auto pointer normal bold break-word'.split(' ')
CSS_FUNCTIONS = 'url rgb rgba'.split(' ')

def css_func(name):
    def meta(*args):
        return '%s(%s)' % (name, ', '.join(str(arg) for arg in args))
    return meta

defaults = {
    'visible': 'visible',
    'relative': 'relative',
    'solid': 'solid',
    'dotted': 'dotted',
    'left': 'left',
    'right': 'right',
    'center': 'center',
    'none': 'none',
    }

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = ctranslator
#!/usr/bin/env python

from codetalker.pgm import Translator, tokens
from errors import TranslateError
from grammar import grammar as ccssgrammar, declare_args
import grammar
import operator
import values
import consts

ccssgrammar.load_rule(declare_args)

CCSS = Translator(ccssgrammar, vbls=[consts.defaults.copy()], rule_stack=[], indent=4)

ast = ccssgrammar.ast_classes

def find_variable(name, scope):
    for vbls in scope.vbls:
        if name in vbls:
            return vbls[name]
    raise TranslateError('Undefined mixin %s' % name)

def handle_body(tree, scope):
    text, after = '', ''
    for node in tree.body:
        if isinstance(node, ast.rule_def):
            after += CCSS.translate(node, scope)
        elif isinstance(node, ast.declare):
            t, a = handle_declare(node, scope)
            text += t
            after += a
        else:
            text += CCSS.translate(node, scope)
    return text, after

@CCSS.translates(ast.Start)
def start(node, scope):
    return ''.join(CCSS.translate(st, scope) for st in node.body)

@CCSS.translates(ast.Assign)
def assign(node, scope):
    scope.vbls[0][node.left.value] = CCSS.translate(node.value, scope)
    return ''

@CCSS.translates(ast.Value)
def value(node, scope):
    return ' '.join(str(CCSS.translate(single, scope)) for single in node.values)

@CCSS.translates(ast.Declare)
def declarer(node, scope):
    text, after = handle_declare(node, scope)
    return text + '\n' + after

def handle_declare(node, scope):
    args, tree = find_variable(node.name.value, scope)
    scope.vbls.insert(0, {})
    i = 0
    for i, (arg, val) in enumerate(zip(args[0], node.args)):
        scope.vbls[0][arg] = CCSS.translate(val, scope)

    if i < len(args[0]) - len(args[1]) - 1:
        raise TranslateError('mixin %s requires at least %d argument (%d given)' % (node.name.value,
                                i, len(args[0]) - len(args[1])))

    for num in range(i+1, len(args[0])):
        scope.vbls[0][args[0][num]] = args[1][args[0][num]]

    text, after = handle_body(tree, scope)
    scope.vbls.pop(0)
    return text, after

@CCSS.translates(ast.Attribute)
def attribute(node, scope):
    return '%s: %s;\n' % (node.attr.value, CCSS.translate(node.value, scope))

@CCSS.translates(ast.RuleDef)
def rule_def(node, scope):
    selector = node.selector.value[:-1].strip()
    if selector.startswith('@'):
        args = declare_arguments(selector, scope)
        scope.vbls[0][selector[1:].split('(')[0]] = args, node
        return ''
    scope.vbls.insert(0, {})
    scope.rule_stack.append(selector)
    selector = get_selector(scope)
    text, after = handle_body(node, scope)
    scope.rule_stack.pop()
    scope.vbls.pop(0)
    if not text.strip():
        rule_text = ''
    else:
        rule_text = '%s {\n%s}\n' % (selector, indent(text, scope.indent))
    return rule_text + after

def get_selector(scope):
    rules = ['']
    for item in scope.rule_stack:
        new = []
        for parent in rules:
            for child in item.split(','):
                child = child.strip()
                if '&' in child:
                    new.append(child.replace('&', parent).strip())
                else:
                    new.append((parent + ' ' + child).strip())
        rules = new
    return ', '.join(rules)

def declare_arguments(selector, scope):
    positional, default = [], {}
    if not selector.endswith(')'):
        if not '(' in selector:
            return [], {}
        else:
            raise TranslateError('Invalid syntax for mixin declaration: "%s"' % selector)
    elif not '(' in selector:
        raise TranslateError('Invalid syntax for mixin declaration: "%s"' % selector)
    ## ^ to do this right, list line/column numbers... TODO
    text = '(' + selector.split('(', 1)[1]
    tree = ccssgrammar.process(text, start=declare_args)
    tree = ccssgrammar.to_ast(tree)
    for arg in tree.args:
        if arg.value:
            default[arg.name.value] = CCSS.translate(arg.value, scope)
        positional.append(arg.name.value)
    return positional, default

@CCSS.translates(ast.BinOp)
def BinOp(node, scope):
    result = CCSS.translate(node.left, scope)
    operators = {'*': operator.mul, '/': operator.div, '+': operator.add, '-': operator.sub}
    for op, value in zip(node.ops, node.values):
        try:
            nv = CCSS.translate(value, scope)
            result = operators[op.value](result, nv)
        except TypeError:
            print [result, nv]
            raise
    return result

def indent(text, num):
    white = ' '*num
    return ''.join(white + line for line in text.splitlines(True))

@CCSS.translates(ast.Atomic)
def atomic(node, scope):
    value = CCSS.translate(node.literal, scope)
    for post in node.posts:
        if isinstance(post, ast.post_attr): # post.name == 'post_attr':
            value = getattr(value, str(post.name.value))
        elif isinstance(post, ast.post_subs): # post.name == 'post_subs':
            sub = CCSS.translate(post.subscript, scope)
            value = value.__getitem__(sub)
        elif isinstance(post, ast.post_call): # post.name == 'post_call':
            args = []
            for arg in post.args:
                args.append(CCSS.translate(arg, scope))
            value = value(*args)
        else:
            raise TranslateError('invalid postfix operation found: %s' % repr(post))
    return value

@CCSS.translates(grammar.CSSID)
def literal(node, scope):
    for dct in scope.vbls:
        if node.value in dct:
            return dct[node.value]
    if node.value in consts.CSS_VALUES:
        return node.value
    elif node.value in consts.CSS_FUNCTIONS:
        return consts.css_func(node.value)
    elif node.value in consts.COLORS:
        return values.Color(consts.COLORS[node.value])
    raise ValueError('Undefined variable: %s' % node.value)

@CCSS.translates(tokens.STRING)
def string(node, scope):
    return node.value

'''value types....

number (2, 3.5, 50%, 20px)
string (whatever)
function

'''

@CCSS.translates(ast.Value)
def value(node, scope):
    res = None
    if len(node.values) > 1:
        res = []
        for value in node.values:
            res.append(str(CCSS.translate(value, scope)))
        return ' '.join(res)
    elif not node.values:
        print node._tree
        raise ValueError('no values')
    return CCSS.translate(node.values[0], scope)

@CCSS.translates(grammar.CSSCOLOR)
def color(node, scope):
    return values.Color(node.value)

@CCSS.translates(grammar.CSSNUMBER)
def number(node, scope):
    return values.Number(node.value)


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python

from codetalker.pgm.errors import ParseError, TokenError

class TranslateError(Exception):
    pass


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = grammar
#!/usr/bin/env python
'''
This is the grammar for CleverCSS. There's no pseudo-code here -- it's all
human readable, pythonic, syntax definition. How is it done? `CodeTalker
<http://github.com/jabapyth/codetalker>`_ has just been reloaded, and is
really awesome ;) 
'''

from codetalker.pgm import Grammar
from codetalker.pgm.special import star, plus, _or, commas
from codetalker.pgm.tokens import STRING, ID, NUMBER, EOF, NEWLINE, WHITE, CCOMMENT, ReToken, INDENT, DEDENT, StringToken

class SYMBOL(StringToken):
    items = list('.()=:')

import re
class CSSNUMBER(ReToken):
    rx = re.compile(r'-?(?:\d+(?:\.\d+)?|\.\d+)(px|em|%|pt)?')

class CSSSELECTOR(ReToken):
    ## the more specific rx was **much** slower...
    rx = re.compile(r'[^\n]+:(?=\n)') #r'(?:[ \t]+|[.:#]?[\w-]+|[>,+&])+:(?=\n|$)')

class CSSID(ReToken):
    rx = re.compile(r'-?[a-zA-Z_][a-zA-Z0-9_-]*')

class CSSCOLOR(ReToken):
    rx = re.compile(r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})')

class SYMBOL(StringToken):
    items = tuple('+-*/@(),=:.')

def start(rule):
    rule | (star(_or(statement, NEWLINE)))
    rule.astAttrs = {'body': statement}

def statement(rule):
    rule | assign | declare | rule_def
    rule.pass_single = True

def assign(rule):
    rule | (CSSID, '=', value, _or(NEWLINE, EOF))
    rule.astAttrs = {'left': {'type':CSSID, 'single':True}, 'value': {'type':value, 'single':True}}

def attribute(rule):
    rule | (CSSID, ':', value, _or(NEWLINE, EOF))
    rule.astAttrs = {'attr': {'type':CSSID, 'single':True}, 'value': {'type':value, 'single':True}}

def value(rule):
    rule | plus(expression)
    rule.astAttrs = {'values': expression}

def declare(rule):
    rule | ('@', CSSID, '(', [commas(expression)], ')', _or(NEWLINE, EOF))
    rule.astAttrs = {'name': {'type':CSSID, 'single':True}, 'args': expression}

def rule_def(rule):
    rule | (CSSSELECTOR, plus(NEWLINE), INDENT, plus(_or(statement, attribute, NEWLINE)), _or(DEDENT, EOF))
    rule.astAttrs = {'selector': {'type':CSSSELECTOR, 'single':True}, 'body': [statement, attribute]}

def binop(name, ops, next):
    def meta(rule):
        rule | (next, star(_or(*ops), next))
        rule.astAttrs = {'left': {'type':next, 'single':True}, 'ops': SYMBOL, 'values': {'type':next, 'start':1}}
    meta.astName = 'BinOp'
    return meta

def atomic(rule):
    rule | (literal, star(_or(post_attr, post_subs, post_call)))
    rule.astAttrs = {'literal':{'type':literal, 'single':True}, 'posts':(post_attr, post_subs, post_call)}

def mul_ex(rule):
    rule | (atomic, star(_or(*'*/'), atomic))
    rule.astAttrs = {'left': {'type':atomic, 'single':True}, 'ops': SYMBOL, 'values': {'type':atomic, 'start':1}}
mul_ex.astName = 'BinOp'

def expression(rule):
    rule | (mul_ex, star(_or(*'-+'), mul_ex))
    rule.astAttrs = {'left': {'type':mul_ex, 'single':True}, 'ops': SYMBOL, 'values': {'type':mul_ex, 'start':1}}
expression.astName = 'BinOp'

def literal(rule):
    rule | paren | STRING | CSSID | CSSNUMBER | CSSCOLOR
    rule.pass_single = True

def paren(rule):
    rule | ('(', expression, ')')
    rule.pass_single = True

def post_attr(rule):
    rule | ('.', CSSID)
    rule.astAttrs = {'name': {'type':CSSID, 'single':True}}

def post_subs(rule):
    rule | ('[', expression, ']')
    rule.astAttrs = {'subscript': {'type':expression, 'single':True}}

def post_call(rule):
    rule | ('(', [commas(expression)], ')')
    rule.astAttrs = {'args': expression}

def declare_args(rule):
    rule | ('(', [commas(arg)], ')')
    rule.astAttrs = {'args': arg}

def arg(rule):
    rule | (CSSID, ['=', expression])
    rule.astAttrs = {'name':{'type':CSSID, 'single':True},
                     'value':{'type':expression, 'optional':True, 'single':True}}

grammar = Grammar(start=start, indent=True, tokens=[CSSSELECTOR, STRING, CSSID, CSSNUMBER, CSSCOLOR, CCOMMENT, SYMBOL, NEWLINE, WHITE], ignore=[WHITE, CCOMMENT], ast_tokens=[CSSID, CSSCOLOR, STRING, CSSNUMBER])

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = translator
#!/usr/bin/env python

from codetalker.pgm.tokens import Token
from codetalker.pgm import tokens
from errors import TranslateError
import operator
import grammar
import values
import consts

translators = {}
def translates(name):
    def meta(func):
        translators[name] = func
        return func
    return meta

def translate(node, scope):
    if isinstance(node, Token):
        if node.__class__ in translators:
            return translators[node.__class__](node, scope)
        else:
            raise TranslateError('Unknown token: %s' % repr(node))
    elif type(node) in (list, tuple):
        return '\n'.join(''.join('' + line for line in str(translate(one, scope)).splitlines(True)) for one in node).strip() + '\n'
    elif node.name in translators:
        return translators[node.name](node, scope)
    raise TranslateError('unknown node type: %s' % node.name)

def indent(text, num):
    white = ' '*num
    return ''.join(white + line for line in text.splitlines(True))

def define_mixin(sel, node, scope):
    sel = sel.strip()
    if '(' in sel[1:]:
        name, args = sel[1:-1].split('(', 1)
        # TODO: have all the args processed by yon grammar
        args = args.split(',')
        pos = []
        defaults = {}
        dflag = False
        for arg in args:
            arg = arg.strip()
            if '=' in arg:
                dflag = True
                n, v = arg.strip().split('=')
                pos.append(n)
                dnode = grammar.grammar.process(v, grammar.add_ex)
                dnode = grammar.grammar.toAst(dnode)
                defaults[n] = translate(dnode, scope)
            elif dflag:
                raise TranslateError('positional argument after default argument: %s' % (repr(node)))
            else:
                pos.append(arg)
    else:
        pos = []
        defaults = {}
        name = sel[1:]
    # print 'mixingin', name, pos, defaults
    scope.vbls[-1][name] = (pos, defaults, node)
    return ''

def handle_body(node, scope):
    text = ''
    after = ''
    for item in node.body:
        if type(item) == list:
            if item[0].name == 'assign':
                translate(item[0], scope)
            elif item[0].name == 'declare':
                t, a = declare(item[0], scope)
                text += t
                after += a
            elif item[0].name == 'rule_def':
                after += translate(item[0], scope)
            else:
                raise TranslateError('unexpected sub rule %s %s' % (item[0].name, repr(item[0])))
        else:
            text += translate(item, scope)
    return text, after

@translates('rule_def')
def rule(node, scope):
    sel = node.selector.value[:-1].strip()
    if sel.startswith('@'):
        return define_mixin(sel, node, scope)
    scope.vbls.append({})
    scope.rules.append(sel)
    text, after = handle_body(node, scope)
    scope.vbls.pop(-1)
    selector = get_selector(scope)
    scope.rules.pop(-1)
    if not text.strip():
        rule_text = ''
    else:
        rule_text = '%s {\n%s}\n' % (selector, indent(text, scope.indent))
    return rule_text + after

def get_selector(scope):
    rules = ['']
    for item in scope.rules:
        new = []
        for parent in rules:
            for child in item.split(','):
                child = child.strip()
                if '&' in child:
                    new.append(child.replace('&', parent).strip())
                else:
                    new.append((parent + ' ' + child).strip())
        rules = new
    return ', '.join(rules)

@translates('declare')
def declares(node, scope):
    t, a = declare(node, scope)
    return t + '\n' + a

def declare(node, scope):
    for vbls in reversed(scope.vbls):
        if node.which.value in vbls:
            pos, dfl, dnode = vbls[node.which.value]
            break
    else:
        raise TranslateError('Undefined mixin called: %s' % repr(node.which))
    scope.vbls.append({})
    args = node.args
    i = 0
    for i, (arg, val) in enumerate(zip(pos, args)):
        scope.vbls[-1][arg] = translate(val, scope)
    if i < len(args) - len(dfl) - 1:
        raise TranslateError('Not enough arguments for mixin %s; at least %d re required (%d given)' % (node.which.value, i, len(pos) - len(dfl)))
    for a in range(i+1, len(pos)):
        scope.vbls[-2][pos[a]] = dfl[pos[a]]
    text, after = handle_body(dnode, scope)
    scope.vbls.pop(-1)
    return text, after

@translates('attribute')
def attribute(node, scope):
    return '%s: %s;\n' % (node.attr.value, translate(node.value, scope))

@translates('atomic')
def atomic(node, scope):
    value = translate(node.literal, scope)
    #if getattr(value, '__name__', None) == 'meta':
        #print 'meta -- css_func', [value, node.literal, node.posts]
    for post in node.posts:
        if post.name == 'post_attr':
            value = getattr(value, str(post.name.value))
        elif post.name == 'post_subs':
            sub = translate(post.subscript, scope)
            value = value.__getitem__(sub)
        elif post.name == 'post_call':
            args = []
            for arg in post.args:
                args.append(translate(arg, scope))
            value = value(*args)
        else:
            raise TranslateError('invalid postfix operation found: %s' % repr(post))
    return value

@translates('literal')
def literal(node, scope):
    return translate(node.items[0], scope)

@translates(grammar.CSSID)
def literal(node, scope):
    for dct in reversed(scope.vbls):
        if node.value in dct:
            return dct[node.value]
    if node.value in consts.CSS_VALUES:
        return node.value
    elif node.value in consts.CSS_FUNCTIONS:
        return consts.css_func(node.value)
    elif node.value in consts.COLORS:
        return values.Color(consts.COLORS[node.value])
    raise ValueError('Undefined variable: %s' % node.value)

@translates(tokens.STRING)
def string(node, scope):
    return node.value

'''value types....

number (2, 3.5, 50%, 20px)
string (whatever)
function

'''

@translates('value')
def value(node, scope):
    res = None
    if len(node.values) > 1:
        res = []
        for value in node.values:
            res.append(str(translate(value, scope)))
        return ' '.join(res)
    elif not node.values:
        print node._tree
        raise ValueError('no values')
    return translate(node.values[0], scope)

@translates('BinOp')
def BinOp(node, scope):
    result = translate(node.left, scope)
    # print 'first result %r ::::: from %r' % (result, node.left)
    operators = {'*': operator.mul, '/': operator.div, '+': operator.add, '-': operator.sub}
    for op, value in zip(node.ops, node.values):
        try:
            nv = translate(value, scope)
            result = operators[op.value](result, nv)
        except TypeError:
            print [result, nv]
            raise
    return result

@translates('assign')
def assign(node, scope):
    scope.vbls[-1][node.left.value] = translate(node.value, scope)
    return ''

@translates(grammar.CSSCOLOR)
def color(node, scope):
    return values.Color(node.value)

@translates(grammar.CSSNUMBER)
def number(node, scope):
    return values.Number(node.value)

@translates('paren')
def paren(node, scope):
    return translate(node.value, scope)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = values
#!/usr/bin/env python
import operator
import consts
import re

class Value(object):
    methods = []
    def __init__(self, value, raw=True):
        if raw:
            value = self.parse(value)
        self.value = value
    
    def parse(self, value):
        return value
    
    def __repr__(self):
        return str(self)

    def calc(self, op, other):
        return NotImplemented

    __add__ = lambda self, other: self.calc(other, operator.add)
    __sub__ = lambda self, other: self.calc(other, operator.sub)
    __rsub__ = lambda self, other: self.calc(other, operator.sub, True)
    __div__ = lambda self, other: self.calc(other, operator.div)
    __rdiv__ = lambda self, other: self.calc(other, operator.div, True)
    __mul__ = lambda self, other: self.calc(other, operator.mul)

class Number(Value):
    rx = re.compile(r'(-?(?:\d+(?:\.\d+)?|\.\d+))(px|em|%|pt)?')
    def parse(self, value):
        match = self.rx.match(value)
        if not match:
            raise ValueError("invalid number '%s'" % value.encode('string_escape'))
        num,units = match.groups()
        num = float(num)
        if int(num) == num:
            num = int(num)
        return num, units
        
    def __str__(self):
        if self.value[1]:
            return u'%s%s' % self.value
        return str(self.value[0])

    def calc(self, other, op, reverse=False):
        if isinstance(other, Number):
            if reverse:
                newvalue = op(other.value[0], self.value[0])
            else:
                newvalue = op(self.value[0], other.value[0])
            if other.value[1] == self.value[1]:
                return Number((newvalue, self.value[1]), False)
            elif self.value[1] and other.value[1]:
                raise ValueError('cannot do math on numbers of differing units')
            elif self.value[1]:
                return Number((newvalue, self.value[1]), False)
            elif other.value[1]:
                return Number((newvalue, other.value[1]), False)
        return NotImplemented

    methods = ['abs', 'round']
    def abs(self):
        return Number((abs(self.value[0]), self.value[1]), False)

    def round(self, places=0):
        return Number((round(self.value[0], places), self.value[1]), False)

class String(Value):
    def __str__(self):
        return self.value

class Color(Value):
    def parse(self, value):
        if len(value) == 4:
            value = '#' + value[1]*2 + value[2]*2 + value[3]*2
        return int(value[1:3], 16), int(value[3:5], 16), int(value[5:], 16)

    def __str__(self):
        value = '#%02x%02x%02x' % self.value
        return consts.REV_COLORS.get(value) or value

    def calc(self, other, op):
        if isinstance(other, Color):
            return Color(tuple(op(a, b) for a,b in zip(self.value, other.value)), False)
        elif isinstance(other, Number):
            if other.value[1]:
                return NotImplemented
            return Color(tuple(op(a, other.value[0]) for a in self.value), False)
        return NotImplemented

    methods = ['brighten', 'darken']

    def brighten(self, amount=Number('10%')):
        if not isinstance(amount, Number) or amount not in (None, '%'):
            raise ValueError('invalid arg for brighten: %s' % amount)
        num = amount.value[0]
        if amount.value[1] == '%':
            num /= 100.0
        num += 1.0
        hsv = colorsys.rgb_to_hsv(v/255.0 for v in self.value)
        hsv[2] *= num
        return Color(tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hsv)), False)
        
    def darken(self, amount=Number('10%')):
        if not isinstance(amount, Number) or amount not in (None, '%'):
            raise ValueError('invalid arg for brighten: %s' % amount)
        num = amount.value[0] * -1
        if amount.value[1] == '%':
            num /= 100.0
        num += 1.0
        hsv = colorsys.rgb_to_hsv(v/255.0 for v in self.value)
        hsv[2] *= num
        return Color(tuple(int(v * 255) for v in colorsys.hsv_to_rgb(hsv)), False)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = extract_sprites
#!/usr/bin/env python
"""Extract the names of the sprites of each sprite map in a CleverCSS."""

import sys
import clevercss

# This is *a little* ugly, but ISTM there are no really great solutions here.
# Pick your poision, sort of.
clevercss.Parser.sprite_map_cls = clevercss.AnnotatingSpriteMap

# Run the file through the parser so the annotater catches it all.
fname = sys.argv[1]
clevercss.convert(open(fname, "U").read(), fname=fname)

# Then extract the sprite names. Should probably add output options here.
for smap, sprites in clevercss.AnnotatingSpriteMap.all_used_sprites():
    map_name = smap.map_fname.to_string(None)
    sprite_names = " ".join(s.name for s in sprites)
    print "%s: %s" % (map_name, sprite_names)


########NEW FILE########
__FILENAME__ = ccss_to_css
#!/usr/bin/env python

import unittest
from magictest import MagicTest as TestCase

from textwrap import dedent

import clevercss
from clevercss import convert
from clevercss.line_iterator import LineIterator

def eigen_test():
    import re
    rx = re.compile(r'Example::\n(.*?)__END__(?ms)')
    text = rx.search(clevercss.__doc__).group(1)
    ccss = '\n'.join(line[8:].rstrip() for line in text.splitlines())
    return clevercss.convert(ccss)

class ConvertTestCase(TestCase):
    def convert(self):
        self.assertEqual(convert('''body: 
            color: $color 
        ''',{'color':'#eee'}),
        u'body {\n  color: #eeeeee;\n}')
    
    def convert2(self):
        self.assertEqual(convert('''body:
            background-color: $background_color
        ''', {'background_color': 'red.darken(10)'}),
        u'body {\n  background-color: #cc0000;\n}')

    def convert_rgba(self):
        self._test_attr('background-color','rgba(0, 255, 100%, 0.3)', 'rgba(0, 255, 255, 0.3)')

    def convert_rgba_float(self):
        self._test_attr('background-color','rgba(0, 255, 100%, .3)', 'rgba(0, 255, 255, 0.3)')

    def convert_float(self):
        self._test_attr('top','.3', '0.3')

    def _test_attr(self, attr, ccval, cssval):
        self.assertEqual(convert('body:\n  %s: %s\n' % (attr, ccval)), 'body {\n  %s: %s;\n}' % (attr, cssval))

    def test_math(self):
        self.assertEqual(convert(dedent("""
        div:
            margin: -2px -2px
            padding: 2px + 2px
            top: 1px+1
            left: 5+5px
            right: 4px-5px
            bottom: 0 - 5px
            text-shadow: 0px -1px 8px #fff
        """)), dedent("""
        div {
          margin: -2px -2px;
          padding: 4px;
          top: 2px;
          left: 10px;
          right: -1px;
          bottom: -5px;
          text-shadow: 0px -1px 8px #ffffff;
        }""").strip())

    def test_eigen(self):
        self.assertEqual(eigen_test(),dedent("""
        body {
          font-family: serif, sans-serif, Verdana, 'Times New Roman';
          color: #111111;
          padding-top: 4px;
          padding-right: 5px;
          padding-left: 5px;
          padding-bottom: 4px;
          background-color: #eeeeee;
        }

        div.foo {
          width: 220px;
          foo: foo/bar/baz/42;
        }

        a {
          color: #ff0000;
        }

        a:hover {
          color: #4d0000;
        }

        a:active {
          color: #ff1a1a;
        }

        div.navigation {
          height: 1.2em;
          padding: 0.2em;
          foo: '1 2 3';
        }

        div.navigation ul {
          margin: 0;
          padding: 0;
          list-style: none;
        }

        div.navigation ul li {
          float: left;
          height: 1.2em;
        }

        div.navigation ul li a {
          display: block;
          height: 1em;
          padding: 0.1em;
        }
        """).strip())

    def test_import_line(self):
      """
      Tests the @import url() command. assumes the code is running in the main
      directory. (i.e. python -c 'from tests import *; main()' from the same
      dir as clevercss)
      """
      self.assertEqual(convert(dedent("""
      @import url(tests/example.ccss)
      
      div:
          color: $arg
      """)), dedent("""
      #test1 {
        color: blue;
      }

      #test2 {
        color: blue;
      }

      #test3 {
        color: blue;
      }
      
      div {
        color: blue;
      }""").strip())
      

    def test_multiline_rule(self):
        self.assertEqual(convert(dedent("""
        ul.item1 li.item1,
        ul.item2 li.item2,
        ul.item3 li.item3:
            font-weight: bold
        """)), dedent("""
        ul.item1 li.item1,
        ul.item2 li.item2,
        ul.item3 li.item3 {
          font-weight: bold;
        }""").strip())

    def backstring(self):
        self.assertEqual(convert(dedent('''
        div.round:
            background-image: `-webkit-gradient(top left, bottom right, from(#fff), to(#000))`
        ''')), dedent('''\
        div.round {
          background-image: -webkit-gradient(top left, bottom right, from(#fff), to(#000));
        }'''))


class MacroTestCase(TestCase):
    def simpleMacro(self):
        ccss = dedent('''
        def simple:
            color: red
            font-size: 3px+10px
        body:
            $simple
            width:200px
        .other:
            $simple
        ''')
        css = dedent('''\
        body {
          color: red;
          font-size: 13px;
          width: 200px;
        }

        .other {
          color: red;
          font-size: 13px;
        }''')
        self.assertEqual(convert(ccss), css)

class LineIterTestCase(TestCase):
    def test_comments(self):
        line_iter = LineIterator(dedent(
        """
        /* block */
        /* multiblock 
        */
                
        aa, /* comment */bb: 
            x:1 // comment
            
        """))
        self.assertEqual("\n".join([s[1] for s in line_iter]),
            "aa, bb:\n    x:1")
    

def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [ConvertTestCase, LineIterTestCase, MacroTestCase])

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = color_convert
#!/usr/bin/env python

import unittest
from unittest import main
from magictest import MagicTest as TestCase

from clevercss.utils import rgb_to_hls

class RgbToHlsTestCase(TestCase):

    def rgb_to_hls(self):
        self._assertEqualHLS(rgb_to_hls(10, 100, 250),
                            [0.6042, 0.5098, 0.9600])

    def rgb_to_hls_underflow(self):
        self._assertEqualHLS(rgb_to_hls(-10, 100, 250),
                            [0.5962, 0.4706, 1.0833])

    def rgb_to_hls_overflow(self):
        self._assertEqualHLS(rgb_to_hls(10, 300, 250),
                            [0.4713, 0.6078, 1.4500])

    def _assertEqualHLS(self, got, expected):
        self.assertEqual([round(x, 4) for x in got],
                         [round(x, 4) for x in expected])

from clevercss.utils import hls_to_rgb

class HlsToRgbTestCase(TestCase):
    def hls_to_rgb(self):
        self.assertEqual(hls_to_rgb(0.6042, 0.5098, 0.9600),
                         (10, 100, 250))

    def hls_to_rgb_underflow(self):
        self.assertEqual(hls_to_rgb(0.5962, 0.4706, 1.0833),
                         (-10, 100, 250))

    def hls_to_rgb_overflow(self):
        self.assertEqual(hls_to_rgb(0.4713, 0.6078, 1.4500),
                         (10, 300, 250))

    def _assertEqualHLS(self, got, expected):
        self.assertEqual([round(x, 4) for x in got],
                         [round(x, 4) for x in expected])

class HlsRgbFuzzyTestCase(TestCase):
    def hls_to_rgb_and_back_fuzzy(self):
        for i in xrange(100):
            self._do_fuzzy()

    def _do_fuzzy(self):
        from random import seed, randint
        seed(0)
        rgb = tuple(randint(0, 255) for i in range(3))
        hls = rgb_to_hls(*rgb)
        hls2rgb = hls_to_rgb(*hls)
        self.assertEqual(rgb, hls2rgb)
        rgb2hls = rgb_to_hls(*hls2rgb)
        self.assertEqual(rgb2hls, hls)

def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [RgbToHlsTestCase, HlsRgbFuzzyTestCase, HlsToRgbTestCase])

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = magictest
#!/usr/bin/env python
import unittest
import inspect

class MagicTest(unittest.TestCase):
    @classmethod
    def _get_test_funcs(cls):
        testcase_methods = dir(unittest.TestCase)
        for m in inspect.classify_class_attrs(cls):
            if m.kind == 'method' and \
                    m.defining_class == cls and \
                    not m.name.startswith('_') and \
                    m.name not in testcase_methods:
                        yield (inspect.findsource(getattr(cls, m.name))[1],
                            m.name)
    
    @classmethod
    def toSuite(cls):
        funcs = sorted(cls._get_test_funcs())
        suite = unittest.TestSuite()
        for lineno, name in funcs:
            suite.addTest(cls(name))
        return suite

    @classmethod
    def runSuite(cls, vb=2):
        return unittest.TextTestRunner(verbosity=vb).run(cls.toSuite())

def suite(mod):
    print 'suiting',mod
    def meta():
        thesuite = unittest.TestSuite()
        module = __import__(mod)
        for sub in mod.split('.')[1:]:
            module = getattr(module, sub)
        for k,v in module.__dict__.iteritems():
            if inspect.isclass(v) and issubclass(v, MagicTest) and v.__module__ == mod:
                thesuite.addTest(v.toSuite())
        return thesuite
    return meta

def modsuite(*mods):
    def meta():
        return unittest.TestSuite(mod.all_tests() for mod in mods)
    return meta



# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = minify
#!/usr/bin/env python

import unittest
from magictest import MagicTest as TestCase

import clevercss
from clevercss import convert

class MinifiedConvertTestCase(TestCase):
    def test_01_min_convert(self):
        self.assertEqual(convert('''body:
            color: $color
        ''',{'color':'#eee'}, minified=True),
        u'body{color:#eee}')

    def test_02_min_convert(self):
        self.assertEqual(convert('''body:
            background-color: $background_color
        ''', {'background_color': 'red.darken(10)'}, minified=True),
        u'body{background-color:#c00}')

def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [MinifiedConvertTestCase])


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = one_liners
#!/usr/bin/env python

import magictest
from magictest import MagicTest as TestCase
from clevercss.grammar import grammar

class Parse(TestCase):
    pass
strings = [(
    # assignment + expressions
    'a = b',
    '\na = b + c',
    'a = b+c/3.0 - 12',
    'a = 12px',
    'a= 12px + 1/4%',
    'a = a b',
    # @declares
    '@import("abc.css")',
    '@dothis()',
    '@other(1, 3, 4+5, 45/manhatten)',
),()]

def make_pass(text):
    def meta(self, *a, **b):
        result = grammar.process(text)
        self.assertEquals(str(result), text)
        # self.assertEquals(''.join(str(tk) for tk in result), text)
    return meta

for st in strings[0]:
    setattr(Parse, st, make_pass(st))

all_tests = test_suite = magictest.suite(__name__)
## import unittest
## unittest.TextTestRunner(verbosity=2).run(test_suite())

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = parsing
#!/usr/bin/env python

import magictest
from magictest import MagicTest as TestCase

import clevercss
from clevercss.grammar import grammar
from codetalker.pgm.grammar import Text, ParseError
from codetalker.pgm.errors import *

class Convert(TestCase):
    pass

cases = [('body:\n top: 5', 'body {\n    top: 5;\n}\n', 'basic'),
        ('body:\n top: 2+4', 'body {\n    top: 6;\n}\n', 'add'),
        ('body:\n top: (5+4 - 1) /2', 'body {\n    top: 4;\n}\n', 'math'),
        ('one = 2\nbody:\n top: one', 'body {\n    top: 2;\n}\n', 'vbl'),
        ('one = 2\nbody:\n top: one+3', 'body {\n    top: 5;\n}\n', 'vbl math'),
        ('one = 2\nbody:\n one = 3\n top: one\ndiv:\n top: one',
         'body {\n    top: 3;\n}\ndiv {\n    top: 2;\n}\n', 'scoping')]

cases.append(('''.one, .two:
    top: 5px
    .three, .four:
        left: 10px
        & > div:
            bottom: auto''','''\
.one, .two {
    top: 5px;
}
.one .three, .one .four, .two .three, .two .four {
    left: 10px;
}
.one .three > div, .one .four > div, .two .three > div, .two .four > div {
    bottom: auto;
}
''', 'deep selectors'))

cases.append(('''
@something:
    color: green
    width: 25%
    size = 4
    a:
        font-size: 2px*size
        line-height: size*5px
body:
    height: 20px
    @something()
a, div:
    @something()
''', '''\
body {
    height: 20px;
    color: green;
    width: 25%;
}
body a {
    font-size: 8px;
    line-height: 20px;
}
a, div {
    color: green;
    width: 25%;
}
a a, div a {
    font-size: 8px;
    line-height: 20px;
}
''', 'bigold mixin'))
cases.append(('''
@abc(a, b, c=25px):
    color: a
    size: b
    font-size: c - 10px
body:
    @abc(green, 5em)
div:
    @abc(#F00, 2pt, 11px)
''', '''\
body {
    color: green;
    size: 5em;
    font-size: 15px;
}
div {
    color: red;
    size: 2pt;
    font-size: 1px;
}
''', 'mixin w/ args'))

def make_convert(ccss, css):
    def meta(self):
        a = clevercss.convert(ccss, indent=4)
        if a != css:
            print a
            print css
        self.assertEqual(a, css)
    return meta

for i, (ccss, css, name) in enumerate(cases):
    setattr(Convert, 'convert_%d_%s' % (i, name), make_convert(ccss, css))

def check_parse(text):
    try:
        return grammar.process(text)
    except:
        return grammar.process(text, debug=True)

def check_fail(text):
    try:
        grammar.process(text)
    except:
        pass
    else:
        grammar.process(text, debug=True)
        raise Exception('was supposed to fail on \'%s\'' % text.encode('string_escape'))
 
all_tests = magictest.suite(__name__)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = spritemap_test
#!/usr/bin/env python

import unittest
from magictest import MagicTest as TestCase

from textwrap import dedent

import clevercss
from clevercss import convert
from clevercss.line_iterator import LineIterator

class SpriteMapTestCase(TestCase):
    def convert_spritemap(self):
        self.assertEqual(convert(open('tests/example_sprites.ccss').read(), fname='tests/example_sprites.ccss'),
            correct)

correct = '''body {
  background-image: url('big.png') -0px -0px;
  width: 20px;
  height: 20px;
}

body div.other,
body .some {
  background-image: url('big.png') -0px -20px;
}'''
def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [SpriteMapTestCase])

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = tokenize_
#!/usr/bin/env python

import magictest
from magictest import MagicTest as TestCase
from clevercss.grammar import grammar

class Tokenize(TestCase):
    pass

strings = [(
    '',
    # assignment + expressions
    'a = b',
    '\na = b + c',
    'a = b+c/3.0 - 12',
    'a = 12px',
    'a= 12px + 1/4%',
    'a = a b',
    # @declares
    '@import("abc.css")',
    '@dothis()',
    '@other(1, 3, 4+5, 45/manhatten)',
),()]

def make_pass(text):
    def meta(self):
        result = grammar.get_tokens(text)
        self.assertEquals(''.join(str(tk) for tk in result), text)
    return meta

for st in strings[0]:
    setattr(Tokenize, st, make_pass(st))

all_tests = test_suite = magictest.suite(__name__)

# vim: et sw=4 sts=4

########NEW FILE########
