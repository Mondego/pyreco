__FILENAME__ = ccss
#!/usr/bin/env python

from optparse import OptionParser
import re
import sys

import clevercss
from clevercss.errors import *

help_text = '''
usage: %prog <file 1> ... <file n>
if called with some filenames it will read each file, cut of
the extension and append a ".css" extension and save. If
the target file has the same name as the source file it will
abort, but if it overrides a file during this process it will
continue. This is a desired functionality. To avoid that you
must not give your source file a .css extension.

if you call it without arguments it will read from stdin and
write the converted css to stdout.
'''

version_text = '''\
CleverCSS Version %s
Licensed under the BSD license.
(c) Copyright 2007 by Armin Ronacher and Georg Brandl
(c) Copyright 2010 by Jared Forsyth''' % clevercss.VERSION

def main():
    parser = OptionParser(usage=help_text, version=version_text)
    parser.add_option('--eigen-test', action='store_true',
            help='evaluate the example from the docstring')
    parser.add_option('--list-colors', action='store_true',
            help='list all known color names')
    parser.add_option('-n', '--no-overwrite', action='store_true', dest='no_overwrite',
            help='don\'t overwrite any files (default=false)')
    parser.add_option('--to-ccss', action='store_true',
            help='convert css files to ccss')
    parser.add_option('--minified', action='store_true',
            help='minify the resulting css')

    (options, args) = parser.parse_args()
    if options.eigen_test:
        print(do_test())
    elif options.list_colors:
        list_colors()
    elif options.to_ccss:
        for arg in args:
            print(cleverfy(arg))
    elif len(args):
        convert_many(args, options)
    else:
        convert_stream()

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
    text = selector + ':\n '
    if rules.get(':rules:'):
        text += '\n\n '.join('\n '.join(line.strip().rstrip(';') for line in rule.style.cssText.splitlines()) for rule in rules.get(':rules:', [])) + '\n'
    for other in rules:
        if other == ':rules:':
            continue
        text += '\n ' + rulesToCCSS(other, rules[other]).replace('\n', '\n ')
    return text

def cleverfy(fname):
    rules = parseCSS(open(fname).read())
    text = ''
    for rule in rules:
        text += rulesToCCSS(rule, rules[rule]) + '\n\n'
    return text

def do_test():
    rx = re.compile(r'Example::\n(.*?)__END__(?ms)')
    text = rx.search(clevercss.__doc__).group(1)
    ccss = '\n'.join(line[8:].rstrip() for line in text.splitlines())
    return clevercss.convert(ccss)

def list_colors():
    print('%d known colors:' % len(clevercss.consts.COLORS))
    for color in sorted(clevercss.consts.COLORS.items()):
        print(' %-30s%s' % color)

def convert_stream():
    import sys
    try:
        print(clevercss.convert(sys.stdin.read()))
    except (ParserError, EvalException) as e:
        sys.stderr.write('Error: %s\n' % e)
        sys.exit(1)

def convert_many(files, options):
    for fname in files:
        target = fname.rsplit('.', 1)[0] + '.css'
        if fname == target:
            sys.stderr.write('Error: same name for '
                             'source and target file "%s".' % fname)
            sys.exit(2)
        elif options.no_overwrite and os.path.exists(target):
            sys.stderr.write('File exists (and --no-overwrite was used) "%s".' % target)
            sys.exit(3)

        src = open(fname)
        try:
            try:
                converted = clevercss.convert(src.read(), fname=fname)
            except (ParserError, EvalException) as e:
                sys.stderr.write('Error in file %s: %s\n' % (fname, e))
                sys.exit(1)
            if options.minified:
                css = cssutils.CSSParser().parseString(converted)
                cssutils.ser.prefs.useMinified()
                converted = css.cssText
            dst = open(target, 'w')
            try:
                print('Writing output to %s...' % target)
                dst.write(converted)
            finally:
                dst.close()
        finally:
            src.close()

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = consts

import re

# list of operators
OPERATORS = ['+', '-', '*', '/', '%', '(', ')', ';', ',']

# units and conversions
UNITS = ['em', 'ex', 'rem', 'px', 'cm', 'mm', 'in', 'pt', 'pc', 'deg', 'rad'
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
for measures, units in CONV.items():
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
REV_COLORS = dict((v, k) for k, v in COLORS.items())

# partial regular expressions for the expr parser
r_number = '(?:\s\-)?(?:\d+(?:\.\d+)?|\.\d+)'
r_string = r"(?:'(?:[^'\\]*(?:\\.[^'\\]*)*)'|" \
          r'\"(?:[^"\\]*(?:\\.[^"\\]*)*)")'
r_call = r'([a-zA-Z_][a-zA-Z0-9_]*)\('

regex = {
    # regular expressions for the normal parser
    'var_def': re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)'),
    'def': re.compile(r'^([a-zA-Z-]+)\s*:\s*(.+)'),
    'line_comment': re.compile(r'(?<!:)//.*?$'),
    'multi_comment': re.compile(r'/\*.+?\*/', re.S),
    'macros_def': re.compile(r'^def ([a-zA-Z-]+)\s*:\s*$'),
    'macros_call': re.compile(r'^\$([a-zA-Z-]+)'),
    # regular expressions for the expr parser
    'vendorprefix': re.compile(r'-(?:moz|webkit)-[a-z-]+'),
    'operator': re.compile('|'.join(re.escape(x) for x in OPERATORS)),
    'whitespace': re.compile(r'\s+'),
    'number': re.compile(r_number + '(?![a-zA-Z0-9_])'),
    'value': re.compile(r'(%s)(%s)(?![a-zA-Z0-9_])' % (r_number, '|'.join(UNITS))),
    'color': re.compile(r'#' + ('[a-fA-f0-9]{1,2}' * 3)),
    'string': re.compile('%s|([^\s*/();,.+$]+|\.(?!%s))+' % (r_string, r_call)),
    'url': re.compile(r'url\(\s*(%s|.*?)\s*\)' % r_string),
    'import': re.compile(r'\@import\s+url\(\s*"?(%s|.*?)"?\s*\)' % r_string),
    'spritemap': re.compile(r'spritemap\(\s*(%s|.*?)\s*\)' % r_string),
    'backstring': re.compile(r'`([^`]*)`'),
    'var': re.compile(r'(?<!\\)\$(?:([a-zA-Z_][a-zA-Z0-9_]*)|'
                    r'\{([a-zA-Z_][a-zA-Z0-9_]*)\})'),
    'call': re.compile(r'\.' + r_call)
}

browser_specific_expansions = {
    'transition-property': ['moz', 'webkit'],
    'transition-duration': ['moz', 'webkit'],
    'transition-timing-function': ['moz', 'webkit'],
    'transition-delay': ['moz', 'webkit'],

    'box-sizing': ['moz', 'webkit'],
}

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = engine
# -*- coding: utf-8 -*-

import sys
import re
import colorsys
import operator
from sys import version_info
if version_info >= (2, 7):
    from collections import OrderedDict
else:
    from ordereddict import OrderedDict

from clevercss import consts
from clevercss import utils
from clevercss import errors
from clevercss import expressions
from clevercss import line_iterator
import os
from clevercss.errors import *

class Engine(object):
    """
    The central object that brings parser and evaluation together.  Usually
    nobody uses this because the `convert` function wraps it.
    """

    def __init__(self, source, parser=None, fname=None):
        if parser is None:
            parser = Parser(fname=fname)
        self._parser = parser
        self.rules, self._vars, self._imports = parser.parse(source)

    def evaluate(self, context=None):
        """Evaluate code."""
        expr = None
        if context is None:
            context = {}
        elif not isinstance(context, dict):
            raise TypeError("context argument must be a dictionary")

        for key, value in context.items():
            if isinstance(value, str):
                expr = self._parser.parse_expr(1, value)
                context[key] = expr
        context.update(self._vars)

        # pull in imports
        for fname, source in self._imports.items():
          for media, selectors, defs in Engine(source[1], fname=fname).evaluate(context):
            yield media, selectors, defs

        for media, selectors, defs in self.rules:
            all_defs = []
            for key, expr in defs:
                string_expr = expr.to_string(context)
                try:
                    prefixes = consts.browser_specific_expansions[key]
                except KeyError:
                    all_defs.append((key, string_expr))
                else:
                    for prefix in prefixes:
                        all_defs.append(('-%s-%s' % (prefix, key), string_expr))
            yield media, selectors, all_defs

    def to_css(self, context=None):
        """Evaluate the code and generate a CSS file."""
        if context.minified:
            return self.to_css_min(context)
        blocks = []
        current_media = None
        for media, selectors, defs in self.evaluate(context):
            if media:
                indent = '  '
            else:
                indent = ''
            block = []
            if media != current_media:
                if current_media:
                    block.append('}\n\n')
                if media:
                    block.append('@media %s {\n' % media)
                current_media = media
            block.append(indent + u',\n'.join(selectors) + ' {')
            for key, value in defs:
                block.append(indent + u'  %s: %s;' % (key, value))
            block.append(indent + u'}')
            blocks.append(u'\n'.join(block))
        if current_media:
            blocks.append('}')
        return u'\n\n'.join(blocks)

    def to_css_min(self, context=None):
        """Evaluate the code and generate a CSS file."""
        parts = []
        current_media = None
        for media, selectors, defs in self.evaluate(context):
            if media != current_media:
                if current_media:
                    parts.append('}')
                if media:
                    parts.append('@media %s{' % media)
                current_media = media
            parts.append(u''.join(u'%s{%s}' % (
                    u','.join(selectors),
                    u';'.join(u'%s:%s' % kv for kv in defs))))
        if current_media:
            parts.append('}')
        result = ''.join(parts)

        # Some browsers/editors choke on extremely long lines.
        # Output lines of 2000 characters or more, broken after a closing brace
        lines = []
        try:
            while True:
                split_index = result.index('}', 2000) + 1
                lines.append(result[:split_index])
                result = result[split_index:]
        except ValueError:
            pass
        lines.append(result)

        return '\n'.join(lines)

class TokenStream(object):
    """
    This is used by the expression parser to manage the tokens.
    """

    def __init__(self, lineno, gen):
        self.lineno = lineno
        self.gen = gen
        next(self)

    def __next__(self):
        try:
            self.current = next(self.gen)
        except StopIteration:
            self.current = None, 'eof'
    next = __next__

    def expect(self, value, token):
        if self.current != (value, token):
            raise ParserError(self.lineno, "expected '%s', got '%s'." %
                              (value, self.current[0]))
        next(self)

class Parser(object):
    """
    Class with a bunch of methods that implement a tokenizer and parser.  In
    fact this class has two parsers.  One that splits up the code line by
    line and keeps track of indentions, and a second one for expressions in
    the value parts.
    """

    sprite_map_cls = expressions.SpriteMap

    def __init__(self, fname=None):
        self.fname = fname

    def preparse(self, source):
        """
        Do the line wise parsing and resolve indents.
        """
        rule = (None, [], [])
        vars = {}
        imports = OrderedDict({})
        indention_stack = [0]
        state_stack = ['root']
        group_block_stack = []
        rule_stack = [rule]
        sub_rules = []
        root_rules = rule[1]
        macroses = {}
        new_state = None
        lineiter = line_iterator.LineIterator(source, emit_endmarker=True)

        def fail(msg):
            raise ParserError(lineno, msg)

        def parse_definition():
            m = consts.regex['macros_call'].search(line)
            if m is not None:
                return lineiter.lineno, '__macros_call__', m.groups()[0]
            m = consts.regex['def'].search(line)
            if m is not None:
                return lineiter.lineno, m.group(1), m.group(2)
            fail('invalid syntax for style definition')

        for lineno, line in lineiter:
            raw_line = line.rstrip().expandtabs()
            line = raw_line.lstrip()
            indention = len(raw_line) - len(line)

            # indenting
            if indention > indention_stack[-1]:
                if not new_state:
                    fail('unexpected indent')
                state_stack.append(new_state)
                indention_stack.append(indention)
                new_state = None

            # dedenting
            elif indention < indention_stack[-1]:
                for level in indention_stack:
                    if level == indention:
                        while indention_stack[-1] != level:
                            if state_stack[-1] == 'rule':
                                rule = rule_stack.pop()
                            elif state_stack[-1] == 'group_block':
                                name, part_defs = group_block_stack.pop()
                                for lineno, key, val in part_defs:
                                    rule[2].append((lineno, name + '-' +
                                                    key, val))
                            indention_stack.pop()
                            state_stack.pop()
                        break
                else:
                    fail('invalid dedent')

            # new state but no indention. bummer
            elif new_state:
                fail('expected definitions, found nothing')

            # end of data
            if line == '__END__':
                break

            # root and rules
            elif state_stack[-1] in ('rule', 'root', 'macros'):
                # macros blocks
                if line.startswith('def ') and line.strip().endswith(":")\
                        and state_stack[-1] == 'root':
                    s_macros = consts.regex['macros_def'].search(line).groups()[0]
                    if s_macros in vars:
                        fail('name "%s" already bound to variable' % s_macros)
                    new_state = 'macros'
                    macros = []
                    macroses[s_macros] = macros

                # new rule blocks
                elif line.endswith(','):
                    sub_rules.append(line)

                elif line.endswith(':'):
                    sub_rules.append(line[:-1].rstrip())
                    s_rule = ' '.join(sub_rules)
                    sub_rules = []
                    if not s_rule:
                        fail('empty rule')
                    new_state = 'rule'
                    new_rule = (s_rule, [], [])
                    rule[1].append(new_rule)
                    rule_stack.append(rule)
                    rule = new_rule
                # if we in a root block we don't consume group blocks
                # or style definitions but variable defs
                elif state_stack[-1] == 'root':
                    if '=' in line:
                        m = consts.regex['var_def'].search(line)
                        if m is None:
                            fail('invalid syntax')
                        key = m.group(1)
                        if key in vars:
                            fail('variable "%s" defined twice' % key)
                        if key in macroses:
                            fail('name "%s" already bound to macros' % key)
                        vars[key] = (lineiter.lineno, m.group(2))
                    elif line.startswith("@"):
                        m = consts.regex['import'].search(line)
                        if m is None:
                            fail('invalid import syntax')
                        url = m.group(1)
                        if url in imports:
                            fail('file "%s" imported twice' % url)
                        # Use absolute paths to allow cross-directory execution
                        if self.fname:
                            absdir = os.path.dirname(os.path.abspath(self.fname))
                            absurl = os.path.join(absdir, url)
                        else:
                            absurl = url
                        if not os.path.isfile(absurl):
                            fail('file "%s" was not found' % absurl)
                        if sys.version_info < (3, 0):
                            fileobj = open(absurl)
                        else:
                            fileobj = open(absurl, encoding='utf-8')
                        imports[absurl] = (lineiter.lineno, fileobj.read())
                    else:
                        fail('Style definitions or group blocks are only '
                             'allowed inside a rule or group block.')

                # definition group blocks
                elif line.endswith('->'):
                    group_prefix = line[:-2].rstrip()
                    if not group_prefix:
                        fail('no group prefix defined')
                    new_state = 'group_block'
                    group_block_stack.append((group_prefix, []))

                # otherwise parse a style definition.
                else:
                    if state_stack[-1] == 'rule':
                        rule[2].append(parse_definition())
                    elif state_stack[-1] == 'macros':
                        macros.append(parse_definition())

            # group blocks
            elif state_stack[-1] == 'group_block':
                group_block_stack[-1][1].append(parse_definition())

            # something unparseable happened
            else:
                fail('unexpected character %s' % line[0])

        return root_rules, vars, imports, macroses

    def parse(self, source):
        """
        Create a flat structure and parse inline expressions.
        """
        expand_def = lambda lineno_k_v: (lineno_k_v[1], self.parse_expr(lineno_k_v[0], lineno_k_v[2]))
        expand_defs = lambda it: list(map(expand_def, it))

        def handle_rule(rule, children, defs, macroses):
            def recurse(macroses):
                if defs:
                    styles = []
                    for lineno, k, v in defs:
                        if k == '__macros_call__':
                            macros_defs = macroses.get(v, None)
                            if macros_defs is None:
                                raise ParserError(lineno, 'No macro with name "%s" is defined' % v)
                            styles.extend(expand_defs(macros_defs))
                        else:
                            styles.append(expand_def((lineno, k, v)))
                    result.append((media[-1], get_selectors(), styles))
                for i_r, i_c, i_d in children:
                    handle_rule(i_r, i_c, i_d, macroses)

            local_rules = []
            reference_rules = []
            if rule.startswith('@media '):
                media.append(rule.split(None, 1)[1])
                recurse(macroses)
            else:
                for r in rule.split(','):
                    r = r.strip()
                    if '&' in r:
                        reference_rules.append(r)
                    else:
                        local_rules.append(r)

            if local_rules:
                stack.append(local_rules)
                recurse(macroses)
                stack.pop()

            if reference_rules:
                if stack:
                    parent_rules = stack.pop()
                    push_back = True
                else:
                    parent_rules = ['*']
                    push_back = False
                virtual_rules = []
                for parent_rule in parent_rules:
                    for tmpl in reference_rules:
                        virtual_rules.append(tmpl.replace('&', parent_rule))
                stack.append(virtual_rules)
                recurse(macroses)
                stack.pop()
                if push_back:
                    stack.append(parent_rules)

            if rule.startswith('@media '):
                del media[-1]

        def get_selectors():
            branches = [()]
            for level in stack:
                new_branches = []
                for rule in level:
                    for item in branches:
                        new_branches.append(item + (rule,))
                branches = new_branches
            return [' '.join(branch) for branch in branches]

        root_rules, vars, imports, macroses = self.preparse(source)
        result = []
        stack = []
        media = [None]
        for i_r, i_c, i_d in root_rules:
            handle_rule(i_r, i_c, i_d, macroses)

        real_vars = {}
        for name, args in vars.items():
            real_vars[name] = self.parse_expr(*args)

        return result, real_vars, imports

    def parse_expr(self, lineno, s):
        def parse():
            pos = 0
            end = len(s)

            def process(token, group=0):
                return lambda m: (m.group(group), token)

            def process_string(m):
                value = m.group(0)
                try:
                    if value[:1] == value[-1:] and value[0] in '"\'':
                        value = value[1:-1].encode('utf-8') \
                                           .decode('unicode-escape')
                    elif value == 'rgb':
                        return None, 'rgb'
                    elif value == 'rgba':
                        return None, 'rgba'
                    elif value in consts.COLORS:
                        return value, 'color'
                except UnicodeError:
                    raise ParserError(lineno, 'invalid string escape')
                return value, 'string'

            rules = ((consts.regex['vendorprefix'], process_string),
                     (consts.regex['operator'], process('op')),
                     (consts.regex['call'], process('call', 1)),
                     (consts.regex['value'], lambda m: (m.groups(), 'value')),
                     (consts.regex['color'], process('color')),
                     (consts.regex['number'], process('number')),
                     (consts.regex['url'], process('url', 1)),
                     (consts.regex['import'], process('import', 1)),
                     (consts.regex['spritemap'], process('spritemap', 1)),
                     (consts.regex['backstring'], process('backstring', 1)),
                     (consts.regex['string'], process_string),
                     (consts.regex['var'], lambda m: (m.group(1) or m.group(2), 'var')),
                     (consts.regex['whitespace'], None))

            while pos < end:
                for rule, processor in rules:
                    m = rule.match(s, pos)
                    if m is not None and m.group():
                        if processor is not None:
                            yield processor(m)
                        pos = m.end()
                        break
                else:
                    raise ParserError(lineno, 'Syntax error')

        s = s.rstrip(';')
        return self.expr(TokenStream(lineno, parse()))

    def expr(self, stream, ignore_comma=False):
        args = [self.concat(stream)]
        list_delim = [(';', 'op')]
        if not ignore_comma:
            list_delim.append((',', 'op'))
        while stream.current in list_delim:
            next(stream)
            args.append(self.concat(stream))
        if len(args) == 1:
            return args[0]
        return expressions.List(args, lineno=stream.lineno)

    def concat(self, stream):
        args = [self.add(stream)]
        while stream.current[1] != 'eof' and \
              stream.current not in ((',', 'op'), (';', 'op'),
                                     (')', 'op')):
            args.append(self.add(stream))
        if len(args) == 1:
            node = args[0]
        else:
            node = expressions.ImplicitConcat(args, lineno=stream.lineno)
        return node

    def add(self, stream):
        left = self.sub(stream)
        while stream.current == ('+', 'op'):
            next(stream)
            left = expressions.Add(left, self.sub(stream), lineno=stream.lineno)
        return left

    def sub(self, stream):
        left = self.mul(stream)
        while stream.current == ('-', 'op'):
            next(stream)
            left = expressions.Sub(left, self.mul(stream), lineno=stream.lineno)
        return left

    def mul(self, stream):
        left = self.div(stream)
        while stream.current == ('*', 'op'):
            next(stream)
            left = expressions.Mul(left, self.div(stream), lineno=stream.lineno)
        return left

    def div(self, stream):
        left = self.mod(stream)
        while stream.current == ('/', 'op'):
            next(stream)
            left = expressions.Div(left, self.mod(stream), lineno=stream.lineno)
        return left

    def mod(self, stream):
        left = self.neg(stream)
        while stream.current == ('%', 'op'):
            next(stream)
            left = expressions.Mod(left, self.neg(stream), lineno=stream.lineno)
        return left

    def neg(self, stream):
        if stream.current == ('-', 'op'):
            next(stream)
            return expressions.Neg(self.primary(stream), lineno=stream.lineno)
        return self.primary(stream)

    def primary(self, stream):
        value, token = stream.current
        if token == 'number':
            next(stream)
            node = expressions.Number(value, lineno=stream.lineno)
        elif token == 'value':
            next(stream)
            node = expressions.Value(lineno=stream.lineno, *value)
        elif token == 'color':
            next(stream)
            node = expressions.Color(value, lineno=stream.lineno)
        elif token == 'rgb':
            next(stream)
            if stream.current == ('(', 'op'):
                next(stream)
                args = []
                while len(args) < 3:
                    if args:
                        stream.expect(',', 'op')
                    args.append(self.expr(stream, True))
                stream.expect(')', 'op')
                return expressions.RGB(tuple(args), lineno=stream.lineno)
            else:
                node = expressions.String('rgb')
        elif token == 'rgba':
            next(stream)
            if stream.current == ('(', 'op'):
                next(stream)
                args = []
                while len(args) < 4:
                    if args:
                        stream.expect(',', 'op')
                    args.append(self.expr(stream, True))
                stream.expect(')', 'op')
                return expressions.RGBA(args)
        elif token == 'backstring':
            next(stream)
            node = expressions.Backstring(value, lineno=stream.lineno)
        elif token == 'string':
            next(stream)
            node = expressions.String(value, lineno=stream.lineno)
        elif token == 'url':
            next(stream)
            node = expressions.URL(value, lineno=stream.lineno)
        elif token == 'import':
            next(stream)
            node = expressions.Import(value, lineno=stream.lineno)
        elif token == 'spritemap':
            next(stream)
            if value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1]
            value = expressions.String(value, lineno=stream.lineno)
            node = self.sprite_map_cls(value, fname=self.fname,
                                       lineno=stream.lineno)
        elif token == 'var':
            next(stream)
            node = expressions.Var(value, lineno=stream.lineno)
        elif token == 'op' and value == '(':
            next(stream)
            if stream.current == (')', 'op'):
                raise ParserError(stream.lineno, 'empty parentheses are '
                                  'not valid. If you want to use them as '
                                  'string you have to quote them.')
            node = self.expr(stream)
            stream.expect(')', 'op')
        else:
            if token == 'call':
                raise ParserError(stream.lineno, 'You cannot call standalone '
                                  'methods. If you wanted to use it as a '
                                  'string you have to quote it.')
            next(stream)
            node = expressions.String(value, lineno=stream.lineno)
        while stream.current[1] == 'call':
            node = self.call(stream, node)
        return node

    def call(self, stream, node):
        method, token = stream.current
        assert token == 'call'
        next(stream)
        args = []
        while stream.current != (')', 'op'):
            if args:
                stream.expect(',', 'op')
            args.append(self.expr(stream))
        stream.expect(')', 'op')
        return expressions.Call(node, method, args, lineno=stream.lineno)




########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python

class CleverCssException(Exception):
    """Base class for exceptions raised by CleverCSS."""

    def __init__(self, lineno, message):
        self.lineno = lineno
        self.msg = message
        Exception.__init__(self, message)

    def __str__(self):
        return '%s (line %s)' % (
            self.msg,
            self.lineno
        )


class ParserError(CleverCssException):
    """Raised on syntax errors."""


class EvalException(CleverCssException):
    """Raised during evaluation."""

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = expressions
#!/usr/bin/env python

import os

from clevercss import utils
import operator
from clevercss import consts
from clevercss.errors import *

class Expr(object):
    """
    Baseclass for all expressions.
    """

    #: name for exceptions
    name = 'expression'

    #: empty iterable of dict with methods
    methods = ()

    def __init__(self, lineno=None):
        self.lineno = lineno

    def evaluate(self, context):
        return self

    def add(self, other, context):
        return String(self.to_string(context) + other.to_string(context))

    def sub(self, other, context):
        raise EvalException(self.lineno, 'cannot substract %s from %s' %
                            (self.name, other.name))

    def mul(self, other, context):
        raise EvalException(self.lineno, 'cannot multiply %s with %s' %
                            (self.name, other.name))

    def div(self, other, context):
        raise EvalException(self.lineno, 'cannot divide %s by %s' %
                            (self.name, other.name))

    def mod(self, other, context):
        raise EvalException(self.lineno, 'cannot use the modulo operator for '
                            '%s and %s. Misplaced unit symbol?' %
                            (self.name, other.name))

    def neg(self, context):
        raise EvalException(self.lineno, 'cannot negate %s' % self.name)

    def to_string(self, context):
        return self.evaluate(context).to_string(context)

    def call(self, name, args, context):
        if name == 'string':
            if isinstance(self, String):
                return self
            return String(self.to_string(context))
        elif name == 'type':
            return String(self.name)
        if name not in self.methods:
            raise EvalException(self.lineno, '%s objects don\'t have a method'
                                ' called "%s". If you want to use this'
                                ' construct as string, quote it.' %
                                (self.name, name))
        return self.methods[name](self, context, *args)

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join('%s=%r' % item for item in
                      self.__dict__.items())
        )


class ImplicitConcat(Expr):
    """
    Holds multiple expressions that are delimited by whitespace.
    """
    name = 'concatenated'
    methods = {
        'list':     lambda x, c: List(x.nodes)
    }

    def __init__(self, nodes, lineno=None):
        Expr.__init__(self, lineno)
        self.nodes = nodes

    def to_string(self, context):
        return u' '.join(x.to_string(context) for x in self.nodes)

class Bin(Expr):

    def __init__(self, left, right, lineno=None):
        Expr.__init__(self, lineno)
        self.left = left
        self.right = right

class Add(Bin):

    def evaluate(self, context):
        return self.left.evaluate(context).add(
               self.right.evaluate(context), context)

class Sub(Bin):

    def evaluate(self, context):
        return self.left.evaluate(context).sub(
               self.right.evaluate(context), context)

class Mul(Bin):

    def evaluate(self, context):
        return self.left.evaluate(context).mul(
               self.right.evaluate(context), context)

class Div(Bin):

    def evaluate(self, context):
        return self.left.evaluate(context).div(
               self.right.evaluate(context), context)

class Mod(Bin):

    def evaluate(self, context):
        return self.left.evaluate(context).mod(
               self.right.evaluate(context), context)

class Neg(Expr):

    def __init__(self, node, lineno=None):
        Expr.__init__(self, lineno)
        self.node = node

    def evaluate(self, context):
        return self.node.evaluate(context).neg(context)

class Call(Expr):

    def __init__(self, node, method, args, lineno=None):
        Expr.__init__(self, lineno)
        self.node = node
        self.method = method
        self.args = args

    def evaluate(self, context):
        return self.node.evaluate(context) \
                        .call(self.method, [x.evaluate(context)
                                            for x in self.args],
                              context)

class Literal(Expr):

    def __init__(self, value, lineno=None):
        Expr.__init__(self, lineno)
        self.value = value

    def to_string(self, context):
        rv = str(self.value)
        if len(rv.split(None, 1)) > 1:
            return u"'%s'" % rv.replace('\\', '\\\\') \
                               .replace('\n', '\\\n') \
                               .replace('\t', '\\\t') \
                               .replace('\'', '\\\'')
        return rv

class Number(Literal):
    name = 'number'

    methods = {
        'abs':      lambda x, c: Number(abs(x.value)),
        'round':    lambda x, c, p=0: Number(round(x.value, p))
    }

    def __init__(self, value, lineno=None):
        Literal.__init__(self, float(value), lineno)

    def add(self, other, context):
        if isinstance(other, Number):
            return Number(self.value + other.value, lineno=self.lineno)
        elif isinstance(other, Value):
            return Value(self.value + other.value, other.unit,
                         lineno=self.lineno)
        return Literal.add(self, other, context)

    def sub(self, other, context):
        if isinstance(other, Number):
            return Number(self.value - other.value, lineno=self.lineno)
        elif isinstance(other, Value):
            return Value(self.value - other.value, other.unit,
                         lineno=self.lineno)
        return Literal.sub(self, other, context)

    def mul(self, other, context):
        if isinstance(other, Number):
            return Number(self.value * other.value, lineno=self.lineno)
        elif isinstance(other, Value):
            return Value(self.value * other.value, other.unit,
                         lineno=self.lineno)
        return Literal.mul(self, other, context)

    def div(self, other, context):
        try:
            if isinstance(other, Number):
                return Number(self.value / other.value, lineno=self.lineno)
            elif isinstance(other, Value):
                return Value(self.value / other.value, other.unit,
                             lineno=self.lineno)
            return Literal.div(self, other, context)
        except ZeroDivisionError:
            raise EvalException(self.lineno, 'cannot divide by zero')

    def mod(self, other, context):
        try:
            if isinstance(other, Number):
                return Number(self.value % other.value, lineno=self.lineno)
            elif isinstance(other, Value):
                return Value(self.value % other.value, other.unit,
                             lineno=self.lineno)
            return Literal.mod(self, other, context)
        except ZeroDivisionError:
            raise EvalException(self.lineno, 'cannot divide by zero')

    def neg(self, context):
        return Number(-self.value)

    def to_string(self, context):
        return utils.number_repr(self.value, context)

class Value(Literal):
    name = 'value'

    methods = {
        'abs':      lambda x, c: Value(abs(x.value), x.unit),
        'round':    lambda x, c, p=0: Value(round(x.value, p), x.unit)
    }

    def __init__(self, value, unit, lineno=None):
        Literal.__init__(self, float(value), lineno)
        self.unit = unit

    def add(self, other, context):
        return self._conv_calc(other, context, operator.add, Literal.add,
                               'cannot add %s and %s')

    def sub(self, other, context):
        return self._conv_calc(other, context, operator.sub, Literal.sub,
                               'cannot subtract %s from %s')

    def mul(self, other, context):
        if isinstance(other, Number):
            return Value(self.value * other.value, self.unit,
                         lineno=self.lineno)
        return Literal.mul(self, other, context)

    def div(self, other, context):
        if isinstance(other, Number):
            try:
                return Value(self.value / other.value, self.unit,
                             lineno=self.lineno)
            except ZeroDivisionError:
                raise EvalException(self.lineno, 'cannot divide by zero',
                                    lineno=self.lineno)
        return Literal.div(self, other, context)

    def mod(self, other, context):
        if isinstance(other, Number):
            try:
                return Value(self.value % other.value, self.unit,
                             lineno=self.lineno)
            except ZeroDivisionError:
                raise EvalException(self.lineno, 'cannot divide by zero')
        return Literal.mod(self, other, context)

    def _conv_calc(self, other, context, calc, fallback, msg):
        if isinstance(other, Number):
            return Value(calc(self.value, other.value), self.unit)
        elif isinstance(other, Value):
            if self.unit == other.unit:
                return Value(calc(self.value,other.value), other.unit,
                             lineno=self.lineno)
            self_unit_type = consts.CONV_mapping.get(self.unit)
            other_unit_type = consts.CONV_mapping.get(other.unit)
            if not self_unit_type or not other_unit_type or \
               self_unit_type != other_unit_type:
                raise EvalException(self.lineno, msg % (self.unit, other.unit)
                                    + ' because the two units are '
                                    'not compatible.')
            self_unit = consts.CONV[self_unit_type][self.unit]
            other_unit = consts.CONV[other_unit_type][other.unit]
            if self_unit > other_unit:
                return Value(calc(self.value / other_unit * self_unit,
                                  other.value), other.unit,
                             lineno=self.lineno)
            return Value(calc(other.value / self_unit * other_unit,
                              self.value), self.unit, lineno=self.lineno)
        return fallback(self, other, context)

    def neg(self, context):
        return Value(-self.value, self.unit, lineno=self.lineno)

    def to_string(self, context):
        return utils.number_repr(self.value, context) + self.unit

class Color(Literal):
    name = 'color'

    def brighten(self, context, amount=None):
        if amount is None:
            amount = Value(10.0, '%')
        hue, lightness, saturation = utils.rgb_to_hls(*self.value)
        if isinstance(amount, Value):
            if amount.unit == '%':
                if not amount.value:
                    return self
                lightness *= 1.0 + amount.value / 100.0
            else:
                raise errors.EvalException(self.lineno, 'invalid unit %s for color '
                                    'calculations.' % amount.unit)
        elif isinstance(amount, Number):
            lightness += (amount.value / 100.0)
        if lightness > 1:
            lightness = 1.0
        return Color(utils.hls_to_rgb(hue, lightness, saturation))

    def darken(self, context, amount=None):
        if amount is None:
            amount = Value(10.0, '%')
        hue, lightness, saturation = utils.rgb_to_hls(*self.value)
        if isinstance(amount, Value):
            if amount.unit == '%':
                if not amount.value:
                    return self
                lightness *= amount.value / 100.0
            else:
                raise errors.EvalException(self.lineno, 'invalid unit %s for color '
                                    'calculations.' % amount.unit)
        elif isinstance(amount, Number):
            lightness -= (amount.value / 100.0)
        if lightness < 0:
            lightness = 0.0
        return Color(utils.hls_to_rgb(hue, lightness, saturation))

    def tint(self, context, lighten=None):
        """Specifies a relative value by which to lighten the color (e.g. toward
        white). This works in the opposite manner to the brighten function; a
        value of 0% produces white (no ink); a value of 50% produces a color
        halfway between the original and white (e.g. 50% halftone). Less
        ink also means colour saturation decreases linearly with the amount of
        ink used. Only positive values between 0-100 for tints are allowed; if you
        wish to darken an existing color use the darken method or shade_color.

        N.B. real printing presses -- and therefore some software -- may produce
        slightly different saturations at different tone curves. If you're really,
        REALLY anal about the colour that gets reproduced, you should probably
        trust your design software. For most intents and purposes, though, this
        is going to be more than sufficient.

        Valueless tints will be returned unmodified.
        """
        if lighten is None:
            return self
        elif isinstance(lighten, (Value, Number)):
            lighten = lighten.value
        lighten = abs(lighten) # Positive values only!

        hue, lit, sat = utils.rgb_to_hls(*self.value)

        # Calculate relative lightness
        lavail = 1.0 - lit
        lused = lavail - (lavail * (lighten / 100))
        lnew = lused + (1.0 - lavail)

        # Corresponding relative (de-)saturation
        if lit == 0:
            lit = 1
        snew = sat * (1 / (lnew/lit))

        return Color(utils.hls_to_rgb(hue, lnew, snew))

    def shade(self, context, values=None):
        """Allows specification of an absolute saturation as well as a
        relative value (lighteness) from the base color. Unlike tinting, shades
        can be either lighter OR darker than their original value; to achieve a
        darker color use a negative lightness value. Likewise, to desaturate,
        use a negative saturation.

        Because shades are not possible to acheive with print, they use the HSV
        colorspace to make modifications (instead of HSL, as is the case with
        brighten, darken, and tint_color). This may produce a different effect
        than expected, so here are a few examples:

            color.shade(0, 0)        # Original color (not modified)
            color.shade(100, 0)      # Full brightness at same saturation
            color.shade(0, 100)      # Full saturation at same brightness
            color.shade(0, -100)     # Greyscale representation of color
            color.shade(100, 100)    # Full saturation and value for this hue
            color.shade(100, -100)   # White
            color.shade(-100, [any]) # Black

        Note that some software may specify these values in reverse order (e.g.
        saturation first and value second), as well as reverse the meaning of
        values, e.g. instead of (value, saturation) these might be reported as
        (desaturation, value). A quick test should reveal if this is the case.
        """
        if values is None:
            return self
        lightness = 0.0
        saturation = 0.0
        if isinstance(values, (Value, Number, Neg)):
            values = List([values,])
        for idx, value in enumerate(values):
            if isinstance(value, (Value, Number)):
                value = value.value
            elif isinstance(value, (Neg)):
                value = -value.node.value
            if idx == 0:
                lightness = value
            if idx == 1:
                saturation = value

        hue, sat, val = utils.rgb_to_hsv(*self.value)

        # Calculate relative Value (referred to as lightness to avoid confusion)
        if lightness >= 0:
            lavail = 1.0 - val
            lnew = val + (lavail * (lightness / 100))
        else:
            lavail = val
            lnew = lavail + (lavail * (lightness / 100))

        # Calculate relative saturation
        if saturation >= 0:
            savail = 1.0 - sat
            snew = sat + (savail * (saturation / 100))
        else:
            savail = sat
            snew = savail + (savail * (saturation / 100))

        return Color(utils.hsv_to_rgb(hue, snew, lnew))


    def mix(self, context, values=None):
        """
        For design purposes, related colours that share the same hue are created
        in one of two manners: They are either a result of lightening or darkening
        the original colour by some amount, or represent a mix between an original
        value and some other colour value.

        In the case of print, the latter is most frequently explicitly employed as
        a "tint", which is produced using a screen of the original colour against
        the paper background (which is nominally -- although not necessarily --
        white); see http://en.wikipedia.org/wiki/Tints_and_shades.

        Since many web page designs choose to emulate paper and adopt a white
        background, in many cases the tint function behaves as expected. However,
        in cases where a page (or related) background colour may not necessarily
        be white, a much more intuitive means of driving a new color is by mixing
        two colours together in a certain proportion, which is what this function
        does.

        Mixing black with white using an amount of 0% produces black (the original
        colour); an amount of 100% with the same colours produces white (mixcolour),
        and an amount of 50% produces a medium grey.

        Note that operations are done in the RGB color space which seems to be
        both easiest and most predictable for
        """
        if values is None:
            return self
        items = []
        try:
            for val in values:
                items.append(val)
        except TypeError:
            raise IndexError("Two arguments are required to mix: a (second) "\
                            "color and a percentage")

        if len(items) != 2:
            raise IndexError("Exactly two arguments are required to mix: "\
                            "a (second) color and a percentage")
        else:
            amount = abs(items[0].value)
            mixcolor = items[1]

        # Evaluate mixcolor if it's a variable.
        if isinstance(mixcolor, Var):
            mixcolor = mixcolor.evaluate(context)

        if amount == 100:
            return mixcolor
        if amount == 0:
            return self

        # Express amount as a decimal
        amount /= 100.0

        r1, g1, b1 = self.value
        r2, g2, b2 = mixcolor.value

        rnew = ((r1 * (1-amount)) + (r2 * amount))
        gnew = ((g1 * (1-amount)) + (g2 * amount))
        bnew = ((b1 * (1-amount)) + (b2 * amount))

        return Color((rnew, gnew, bnew))

    methods = {
        'brighten': brighten,
        'darken':   darken,
        'tint':     tint,
        'shade':    shade,
        'mix':      mix,
        'hex':      lambda x, c: Color(x.value, x.lineno)
    }

    def __init__(self, value, lineno=None):
        self.from_name = False
        if isinstance(value, str):
            if not value.startswith('#'):
                value = consts.COLORS.get(value)
                if not value:
                    raise ParserError(lineno, 'unknown color name')
                self.from_name = True
            try:
                if len(value) == 4:
                    value = [int(x * 2, 16) for x in value[1:]]
                elif len(value) == 7:
                    value = [int(value[i:i + 2], 16) for i in range(1, 7, 2)]
                else:
                    raise ValueError()
            except ValueError as e:
                raise ParserError(lineno, 'invalid color value')
        Literal.__init__(self, tuple(value), lineno)

    def add(self, other, context):
        if isinstance(other, (Color, Number)):
            return self._calc(other, operator.add)
        return Literal.add(self, other, context)

    def sub(self, other, context):
        if isinstance(other, (Color, Number)):
            return self._calc(other, operator.sub)
        return Literal.sub(self, other, context)

    def mul(self, other, context):
        if isinstance(other, (Color, Number)):
            return self._calc(other, operator.mul)
        return Literal.mul(self, other, context)

    def div(self, other, context):
        if isinstance(other, (Color, Number)):
            return self._calc(other, operator.sub)
        return Literal.div(self, other, context)

    def to_string(self, context):
        code = '#%02x%02x%02x' % self.value
        if not context.minified:
            return self.from_name and consts.REV_COLORS.get(code) or code
        else:
            if all(x >> 4 == x & 15 for x in self.value):
                min_code = '#%x%x%x' % tuple(x & 15 for x in self.value)
            else:
                min_code = code
            name = consts.REV_COLORS.get(code)
            if name and len(name) < len(min_code):
                return name
            else:
                return min_code

    def _calc(self, other, method):
        is_number = isinstance(other, Number)
        channels = []
        for idx, val in enumerate(self.value):
            if is_number:
                other_val = int(other.value)
            else:
                other_val = other.value[idx]
            new_val = method(val, other_val)
            if new_val > 255:
                new_val = 255
            elif new_val < 0:
                new_val = 0
            channels.append(new_val)
        return Color(tuple(channels), lineno=self.lineno)

class RGB(Expr):
    """
    an expression that hopefully returns a Color object.
    """

    def __init__(self, rgb, lineno=None):
        Expr.__init__(self, lineno)
        self.rgb = rgb

    def evaluate(self, context):
        args = []
        for arg in self.rgb:
            arg = arg.evaluate(context)
            if isinstance(arg, Number):
                value = int(arg.value)
            elif isinstance(arg, Value) and arg.unit == '%':
                value = int(arg.value / 100.0 * 255)
            else:
                raise EvalException(self.lineno, 'colors defined using the '
                                    'rgb() literal only accept numbers and '
                                    'percentages.')
            if value < 0 or value > 255:
                raise EvalException(self.lineno, 'rgb components must be in '
                                'the range 0 to 255.')
            args.append(value)
        return Color(args, lineno=self.lineno)

class RGBA(RGB):
    """
    an expression for dealing w/ rgba colors
    """

    def to_string(self, context):
        args = []
        for i, arg in enumerate(self.rgb):
            arg = arg.evaluate(context)
            if isinstance(arg, Number):
                if i == 3:
                    value = float(arg.value)
                else:
                    value = int(arg.value)
            elif isinstance(arg, Value) and arg.unit == '%':
                if i == 3:
                    value = float(arg.value / 100.0)
                else:
                    value = int(arg.value / 100.0 * 255)
            else:
                raise EvalException(self.lineno, 'colors defined using the '
                                    'rgb() literal only accept numbers and '
                                    'percentages. (got %s)' % arg)
            if value < 0 or value > 255:
                raise EvalError(self.lineno, 'rgb components must be in '
                                'the range 0 to 255.')
            args.append(value)
        return 'rgba(%s)' % (', '.join(str(n) for n in args))

class Backstring(Literal):
    """
    A string meant to be escaped directly to output.
    """
    name = "backstring"

    def __init__(self, nodes, lineno=None):
        Expr.__init__(self, lineno)
        self.nodes = nodes

    def to_string(self, context):
        return str(self.nodes)

class String(Literal):
    name = 'string'

    methods = {
        'length':   lambda x, c: Number(len(x.value)),
        'upper':    lambda x, c: String(x.value.upper()),
        'lower':    lambda x, c: String(x.value.lower()),
        'strip':    lambda x, c: String(x.value.strip()),
        'split':    lambda x, c, d=None: String(x.value.split(d)),
        'eval':     lambda x, c: Parser().parse_expr(x.lineno, x.value)
                                         .evaluate(c)
    }

    def mul(self, other, context):
        if isinstance(other, Number):
            return String(self.value * int(other.value), lineno=self.lineno)
        return Literal.mul(self, other, context, lineno=self.lineno)

class URL(Literal):
    name = 'URL'
    methods = {
        'length':   lambda x, c: Number(len(self.value))
    }

    def add(self, other, context):
        return URL(self.value + other.to_string(context),
                   lineno=self.lineno)

    def mul(self, other, context):
        if isinstance(other, Number):
            return URL(self.value * int(other.value), lineno=self.lineno)
        return Literal.mul(self, other, context)

    def to_string(self, context):
        return 'url(%s)' % Literal.to_string(self, context)

class SpriteMap(Expr):
    name = 'SpriteMap'
    methods = {
        'sprite': lambda x, c, v: Sprite(x, v.value, lineno=v.lineno)
    }
    _magic_names = {
        "__url__": "image_url",
        "__resources__": "sprite_resource_dir",
        "__passthru__": "sprite_passthru_url",
    }

    image_url = None
    sprite_resource_dir = None
    sprite_passthru_url = None

    def __init__(self, map_fname, fname=None, lineno=None):
        Expr.__init__(self, lineno=lineno)
        self.map_fname = map_fname
        self.fname = fname

    def evaluate(self, context):
        self.map_fpath = os.path.join(os.path.dirname(self.fname),
                                      self.map_fname.to_string(context))
        self.mapping = self.read_spritemap(self.map_fpath)
        return self

    def read_spritemap(self, fpath):
        fo = open(fpath, "U")
        spritemap = {}
        try:
            for line in fo:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                rest = line.split(",")
                key = rest.pop(0).strip()
                if key[-2:] == key[:2] == "__":
                    if key not in self._magic_names:
                        raise ValueError("%r is not a valid field" % (key,))
                    att = self._magic_names[key]
                    setattr(self, att, rest[0].strip())
                elif len(rest) != 4:
                    raise ValueError("unexpected line: %r" % (line,))
                else:
                    x1, y1, x2, y2 = rest
                    spritemap[key] = [int(x) for x in (x1, y1, x2, y2)]
        finally:
            fo.close()
        return spritemap

    def get_sprite_def(self, name):
        if name in self.mapping:
            return self.mapping[name]
        elif self.sprite_passthru_url:
            return self._load_sprite(name)
        else:
            raise KeyError(name)

    def _load_sprite(self, name):
        try:
            from PIL import Image
        except ImportError:
            raise KeyError(name)

        spr_fname = os.path.join(os.path.dirname(self.map_fpath), name)
        if not os.path.exists(spr_fname):
            raise KeyError(name)

        im = Image.open(spr_fname)
        spr_def = (0, 0) + tuple(im.size)
        self.mapping[name] = spr_def
        return spr_def

    def get_sprite_url(self, sprite):
        if self.sprite_passthru_url:
            return self.sprite_passthru_url + sprite.name
        else:
            return self.image_url

    def annotate_used(self, sprite):
        pass

class AnnotatingSpriteMap(SpriteMap):
    sprite_maps = []

    def __init__(self, *args, **kwds):
        SpriteMap.__init__(self, *args, **kwds)
        self._sprites_used = {}
        self.sprite_maps.append(self)

    def read_spritemap(self, fname):
        self.image_url = "<annotator>"
        return {}

    def get_sprite_def(self, name):
        return 0, 0, 100, 100

    def get_sprite_url(self, sprite):
        return "<annotated %s>" % (sprite,)

    def annotate_used(self, sprite):
        self._sprites_used[sprite.name] = sprite

    @classmethod
    def all_used_sprites(cls):
        for smap in cls.sprite_maps:
            yield smap, list(smap._sprites_used.values())

class Sprite(Expr):
    name = 'Sprite'
    methods = {
        'url': lambda x, c: String("url(%s)" % x.spritemap.get_sprite_url(x)),
        'position': lambda x, c: ImplicitConcat(x._pos_vals(c)),
        'height': lambda x, c: Value(x.height, "px"),
        'width': lambda x, c: Value(x.width, "px"),
        'x1': lambda x, c: Value(x.x1, "px"),
        'y1': lambda x, c: Value(x.y1, "px"),
        'x2': lambda x, c: Value(x.x2, "px"),
        'y2': lambda x, c: Value(x.y2, "px")
    }

    def __init__(self, spritemap, name, lineno=None):
        if lineno:
            self.lineno = lineno
        else:
            self.lineno = name.lineno

        self.name = name
        self.spritemap = spritemap
        self.spritemap.annotate_used(self)
        try:
            self.coords = spritemap.get_sprite_def(name)
        except KeyError:
            msg = "Couldn't find sprite %r in mapping" % name
            raise EvalException(self.lineno, msg)

    def _get_coords(self):
        return self.x1, self.y1, self.x2, self.y2
    def _set_coords(self, value):
        self.x1, self.y1, self.x2, self.y2 = value
    coords = property(_get_coords, _set_coords)

    @property
    def width(self): return self.x2 - self.x1
    @property
    def height(self): return self.y2 - self.y1

    def _pos_vals(self, context):
        """Get a list of position values."""
        meths = self.methods
        call_names = "x1", "y1", "x2", "y2"
        return [meths[n](self, context) for n in call_names]

    def to_string(self, context):
        sprite_url = self.spritemap.get_sprite_url(self)
        return "url(%s) -%dpx -%dpx" % (sprite_url, self.x1, self.y1)

class Var(Expr):

    def __init__(self, name, lineno=None):
        self.name = name
        self.lineno = lineno

    def evaluate(self, context):
        if self.name not in context:
            raise EvalException(self.lineno, 'variable %s is not defined' %
                                (self.name,))
        val = context[self.name]
        context[self.name] = FailingVar(self, self.lineno)
        try:
            return val.evaluate(context)
        finally:
            context[self.name] = val

class FailingVar(Expr):

    def __init__(self, var, lineno=None):
        Expr.__init__(self, lineno or var.lineno)
        self.var = var

    def evaluate(self, context):
        raise EvalException(self.lineno, 'Circular variable dependencies '
                            'detected when resolving %s.' % (self.var.name,))

class List(Expr):
    name = 'list'

    methods = {
        'length':   lambda x, c: Number(len(x.items)),
        'join':     lambda x, c, d=String(' '): String(d.value.join(
                                 a.to_string(c) for a in x.items))
    }

    def __init__(self, items, lineno=None):
        Expr.__init__(self, lineno)
        self.items = items

    def __iter__(self):
        for item in self.items:
            yield item

    def __getslice__(self, i, j):
        return self.items[i:j]

    def __getitem__(self, i):
        return self.items[i]

    def add(self, other):
        if isinstance(other, List):
            return List(self.items + other.items, lineno=self.lineno)
        return List(self.items + [other], lineno=self.lineno)

    def to_string(self, context):
        return u', '.join(x.to_string(context) for x in self.items)

# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = line_iterator
#!/usr/bin/env python

from clevercss import consts
from clevercss import utils

class LineIterator(object):
    """
    This class acts as an iterator for sourcecode. It yields the lines
    without comments or empty lines and keeps track of the real line
    number.

    Example::

        >>> li = LineIterator(u'foo\nbar\n\n/* foo */bar')
        >>> li.next()
        1, u'foo'
        >>> li.next()
        2, 'bar'
        >>> li.next()
        4, 'bar'
        >>> li.next()
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        StopIteration
    """

    def __init__(self, source, emit_endmarker=False):
        """
        If `emit_endmarkers` is set to `True` the line iterator will send
        the string ``'__END__'`` before closing down.
        """
        lines = consts.regex['multi_comment'].sub('', source).splitlines()
        self.lineno = 0
        self.lines = len(lines)
        self.emit_endmarker = emit_endmarker
        self._lineiter = iter(lines)

    def __iter__(self):
        return self

    def _read_line(self):
        """Read the next non empty line.  This strips line comments."""
        line = ''
        while not line.strip():
            line += consts.regex['line_comment'].sub('', next(self._lineiter)).rstrip()
            self.lineno += 1
        return line

    def _next(self):
        """
        Get the next line without mutliline comments.
        """
        # XXX: this fails for a line like this: "/* foo */bar/*"
        line = self._read_line()
        comment_start = line.find('/*')
        if comment_start < 0:
            return self.lineno, line

        stripped_line = line[:comment_start]
        comment_end = line.find('*/', comment_start)
        if comment_end >= 0:
            return self.lineno, stripped_line + line[comment_end + 2:]

        start_lineno = self.lineno
        try:
            while True:
                line = self._read_line()
                comment_end = line.find('*/')
                if comment_end >= 0:
                    stripped_line += line[comment_end + 2:]
                    break
        except StopIteration:
            raise ParserError(self.lineno, 'missing end of multiline comment')
        return start_lineno, stripped_line

    def __next__(self):
        """
        Get the next line without multiline comments and emit the
        endmarker if we reached the end of the sourcecode and endmarkers
        were requested.
        """
        try:
            while True:
                lineno, stripped_line = self._next()
                if stripped_line:
                    return lineno, stripped_line
        except StopIteration:
            if self.emit_endmarker:
                self.emit_endmarker = False
                return self.lineno, '__END__'
            raise
    next = __next__


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

import colorsys

def number_repr(value, context):
    """
    CleverCSS uses floats internally.  To keep the string representation
    of the numbers small cut off the places if this is possible without
    losing much information.
    """
    value = str(value)
    integer, dot, fraction = value.partition('.')
    if dot and fraction == '0':
        return integer
    elif context.minified:
        return value.lstrip('0')
    else:
        return value


def rgb_to_hls(red, green, blue):
    """
    Convert RGB to HSL.  The RGB values we use are in the range 0-255, but
    HSL is in the range 0-1!
    """
    return colorsys.rgb_to_hls(red / 255.0, green / 255.0, blue / 255.0)


def hls_to_rgb(hue, saturation, lightness):
    """Convert HSL back to RGB."""
    t = colorsys.hls_to_rgb(hue, saturation, lightness)
    return tuple(int(round(x * 255)) for x in t)


def rgb_to_hsv(red, green, blue):
    """
    Converts RGB to HSV, which is more commonly used in design programs.
    """
    hsvtup = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
    return hsvtup


def hsv_to_rgb(hue, saturation, value):
    """Converts Hue/Saturation/Value back to RGB."""
    rgbtup = colorsys.hsv_to_rgb(hue, saturation, value)
    red = int(round(rgbtup[0] * 255, 0))
    green = int(round(rgbtup[1]* 255, 0))
    blue = int(round(rgbtup[2]* 255, 0))
    return (red, green, blue)

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
    print("%s: %s" % (map_name, sprite_names))


########NEW FILE########
__FILENAME__ = ccss_to_css
#!/usr/bin/env python

import os
import sys
import unittest
from tests.magictest import MagicTest as TestCase

from textwrap import dedent

import clevercss
from clevercss import convert
from clevercss.line_iterator import LineIterator

from clevercss.errors import *

def eigen_test():
    filename = os.path.join(os.path.dirname(__file__), 'eigentest.ccss')
    ccss = open(filename).read()
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
        if sys.version_info >= (3, 0):
            # round() behavior changed in Python 3
            # http://docs.python.org/3/whatsnew/3.0.html#builtins
            a_hover_color = '#4c0000'
        else:
            a_hover_color = '#4d0000'
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
          color: %(a_hover_color)s;
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
        """ % {'a_hover_color': a_hover_color}).strip())

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

    def test_undefined_macro(self):
        ccss = dedent('''
        body:
            $simple
            width:200px
        .other:
            $simple
        ''')
        self.assertRaises(ParserError, convert, ccss)

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
from tests.magictest import MagicTest as TestCase

from clevercss.utils import rgb_to_hls, hls_to_rgb

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
        for i in range(100):
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


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = mediatype
import unittest
from unittest import TestCase, main
from textwrap import dedent
from tests.magictest import MagicTest as TestCase

from clevercss import convert

class MediaTypeTestCase(TestCase):

    def test_01_global_media_type(self):
        self._assertConversion(
            """
            @media print:
              a:
                text-decoration: none""",

            """
            @media print {

              a {
                text-decoration: none;
              }

            }""")

    def test_02_leading_media_type(self):
        self._assertConversion(
            """
            @media print:
              a:
                text-decoration: none
            a:
              font-weight: bold""",

            """
            @media print {

              a {
                text-decoration: none;
              }

            }


            a {
              font-weight: bold;
            }""")

    def test_03_trailing_media_type(self):
        self._assertConversion(
            """
            a:
              font-weight: bold
            @media print:
              a:
                text-decoration: none""",

            """
            a {
              font-weight: bold;
            }

            @media print {

              a {
                text-decoration: none;
              }

            }""")

    def test_04_change_media_type(self):
        self._assertConversion(
            """
            @media aural:
              a:
                font-weight: bold
            @media print:
              a:
                text-decoration: none""",

            """
            @media aural {

              a {
                font-weight: bold;
              }

            }


            @media print {

              a {
                text-decoration: none;
              }

            }""")

    def test_05_repeat_media_type(self):
        self._assertConversion(
            """
            @media print:
              strong:
                font-weight: bold
            @media print:
              a:
                text-decoration: none""",

            """
            @media print {

              strong {
                font-weight: bold;
              }

              a {
                text-decoration: none;
              }

            }""")

    def test_06_nested_media_type(self):
        self._assertConversion(
            """
            @media print:
              #content:
                background: none
                @media handheld:
                  strong:
                    font-weight: bold
              a:
                text-decoration: none""",

            """
            @media print {

              #content {
                background: none;
              }

            }


            @media handheld {

              #content strong {
                font-weight: bold;
              }

            }


            @media print {

              a {
                text-decoration: none;
              }

            }""")

    def test_06_minimal_media_type(self):
        self._assertConversion(
            """
            @media print:
              #content:
                background: none
                @media handheld:
                  strong:
                    font-weight: bold
              a:
                text-decoration: none

            a:
                color: red

            @media handheld:
                td:
                    background-color: green""",
            """
            @media print{
              #content{
                background:none}
            }
            @media handheld{
              #content strong{
                font-weight:bold}
            }
            @media print{
              a{
                text-decoration:none}
            }
            a{
                color:red}
            @media handheld{
                td{
                    background-color:green}
            }
            """,
            minified=True)

    def _assertConversion(self, ccss, css, minified=False):
        got = convert(dedent(ccss), minified=minified)
        expected = dedent(css).lstrip()
        if minified:
            expected = ''.join(line.lstrip(' ') for line in expected.splitlines())
        assert got == expected, '\n' + expected.replace('\n', r'\n') + '\n' + got.replace('\n', r'\n')

def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [MediaTypeTestCase])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = minify
#!/usr/bin/env python

import unittest
from tests.magictest import MagicTest as TestCase

import clevercss
from clevercss import convert

class MinifiedConvertTestCase(TestCase):
    def test_01_min_convert(self):
        self.assertEqual(convert('''body:
            color: $color
        ''',{'color':'#eeeeee'}, minified=True),
        u'body{color:#eee}')

    def test_02_min_convert(self):
        self.assertEqual(convert('''body:
            background-color: $background_color
        ''', {'background_color': 'red.darken(10)'}, minified=True),
        u'body{background-color:#c00}')

    def test_02_min_convert_colors(self):
        self.assertEqual(convert('''body:
            background-color: #ffff00
            color: #fffafa
            p:
                background-color: #ff0000
                color: khaki
        ''', minified=True),
        u'body{background-color:#ff0;color:snow}body p{background-color:red;color:khaki}')

def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [MinifiedConvertTestCase])


# vim: et sw=4 sts=4

########NEW FILE########
__FILENAME__ = spritemap_test
#!/usr/bin/env python

import unittest
from tests.magictest import MagicTest as TestCase

from textwrap import dedent

import clevercss
from clevercss import convert
from clevercss.line_iterator import LineIterator

class SpriteMapTestCase(TestCase):
    def convert_spritemap(self):
        self.assertEqual(convert(open('tests/example_sprites.ccss').read(), fname='tests/example_sprites.ccss'),
            correct)

correct = '''body {
  background-image: url(big.png) -0px -0px;
  width: 20px;
  height: 20px;
}

body div.other,
body .some {
  background-image: url(big.png) -0px -20px;
}'''
def all_tests():
    return unittest.TestSuite(case.toSuite() for case in [SpriteMapTestCase])

# vim: et sw=4 sts=4

########NEW FILE########
