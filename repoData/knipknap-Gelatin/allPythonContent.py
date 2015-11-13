__FILENAME__ = mkapidoc
#!/usr/bin/env python
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Generates the *public* API documentation.
Remember to hide your private parts, people!
"""
import os, re, sys

project  = 'Gelatin'
base_dir = os.path.join('..', 'src')
doc_dir  = 'api'

# Create the documentation directory.
if not os.path.exists(doc_dir):
    os.makedirs(doc_dir)

# Generate the API documentation.
cmd = 'epydoc ' + ' '.join(['--name', project,
                            r'--exclude ^Gelatin\.parser\.Newline$',
                            r'--exclude ^Gelatin\.parser\.Indent$',
                            r'--exclude ^Gelatin\.parser\.Dedent$',
                            r'--exclude ^Gelatin\.parser\.Token$',
                            r'--exclude ^Gelatin\.parser\.util$',
                            r'--exclude ^Gelatin\.compiler\.Function$',
                            r'--exclude ^Gelatin\.compiler\.Grammar$',
                            r'--exclude ^Gelatin\.compiler\.Match',
                            r'--exclude ^Gelatin\.compiler\.Number$',
                            r'--exclude ^Gelatin\.compiler\.Regex$',
                            r'--exclude ^Gelatin\.compiler\.String$',
                            r'--exclude ^Gelatin\.compiler\.Token$',
                            '--html',
                            '--no-private',
                            '--introspect-only',
                            '--no-source',
                            '--no-frames',
                            '--inheritance=included',
                            '-v',
                            '-o %s' % doc_dir,
                            os.path.join(base_dir, project)])
print cmd
os.system(cmd)

########NEW FILE########
__FILENAME__ = Context
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import sys

def do_next(context):
    return 0

def do_skip(context):
    return 1

def do_fail(context, message = 'No matching statement found'):
    context._error(message)

def do_say(context, message):
    context._msg(message)
    return 0

def do_warn(context, message):
    context._warn(message)
    return 0

def do_return(context, levels = 1):
    #print "do.return():", -levels
    return -levels

def out_create(context, path, data = None):
    #print "out.create():", path, data
    context.builder.create(path, data)
    context.builder.enter(path)
    context._trigger(context.on_add, context.re_stack[-1])
    context.builder.leave()
    return 0

def out_replace(context, path, data = None):
    #print "out.replace():", path, data
    context.builder.add(path, data, replace = True)
    context.builder.enter(path)
    context._trigger(context.on_add, context.re_stack[-1])
    context.builder.leave()
    return 0

def out_add(context, path, data = None):
    #print "out.add():", path, data
    context.builder.add(path, data)
    context.builder.enter(path)
    context._trigger(context.on_add, context.re_stack[-1])
    context.builder.leave()
    return 0

def out_add_attribute(context, path, name, value):
    #print "out.add_attribute():", path, name, value
    context.builder.add_attribute(path, name, value)
    context.builder.enter(path)
    context._trigger(context.on_add, context.re_stack[-1])
    context.builder.leave()
    return 0

def out_open(context, path):
    #print "out.open():", path
    context.builder.open(path)
    context._trigger(context.on_add, context.re_stack[-1])
    context.stack[-1].on_leave.append((context.builder.leave, ()))
    return 0

def out_enter(context, path):
    #print "out.enter():", path
    context.builder.enter(path)
    context._trigger(context.on_add, context.re_stack[-1])
    context.stack[-1].on_leave.append((context.builder.leave, ()))
    return 0

def out_enqueue_before(context, regex, path, data = None):
    #print "ENQ BEFORE", regex.pattern, path, data
    context.on_match_before.append((regex, out_add, (context, path, data)))
    return 0

def out_enqueue_after(context, regex, path, data = None):
    #print "ENQ AFTER", regex.pattern, path, data
    context.on_match_after.append((regex, out_add, (context, path, data)))
    return 0

def out_enqueue_on_add(context, regex, path, data = None):
    #print "ENQ ON ADD", regex.pattern, path, data
    context.on_add.append((regex, out_add, (context, path, data)))
    return 0

def out_clear_queue(context):
    context._clear_triggers()
    return 1

class Context(object):
    def __init__(self):
        self.functions = {'do.fail':            do_fail,
                          'do.return':          do_return,
                          'do.next':            do_next,
                          'do.skip':            do_skip,
                          'do.say':             do_say,
                          'do.warn':            do_warn,
                          'out.create':         out_create,
                          'out.replace':        out_replace,
                          'out.add':            out_add,
                          'out.add_attribute':  out_add_attribute,
                          'out.open':           out_open,
                          'out.enter':          out_enter,
                          'out.enqueue_before': out_enqueue_before,
                          'out.enqueue_after':  out_enqueue_after,
                          'out.enqueue_on_add': out_enqueue_on_add,
                          'out.clear_queue':    out_clear_queue}
        self.lexicon  = {}
        self.grammars = {}
        self.input    = None
        self.builder  = None
        self.end      = 0
        self._init()

    def _init(self):
        self.start           = 0
        self.re_stack        = []
        self.stack           = []
        self._clear_triggers()

    def _clear_triggers(self):
        self.on_match_before = []
        self.on_match_after  = []
        self.on_add          = []

    def _trigger(self, triggers, match):
        matching = []
        for trigger in triggers:
            regex, func, args = trigger
            if regex.search(match.group(0)) is not None:
                matching.append(trigger)
        for trigger in matching:
            triggers.remove(trigger)
        for trigger in matching:
            regex, func, args = trigger
            func(*args)

    def _match_before_notify(self, match):
        self.re_stack.append(match)
        self._trigger(self.on_match_before, match)

    def _match_after_notify(self, match):
        self._trigger(self.on_match_after, match)
        self.re_stack.pop()

    def _get_lineno(self):
        return self.input.count('\n', 0, self.start) + 1

    def _get_line(self, number = None):
        if number is None:
            number = self._get_lineno()
        return self.input.split('\n')[number - 1]

    def _get_line_position_from_char(self, char):
        line_start = char
        while line_start != 0:
            if self.input[line_start - 1] == '\n':
                break
            line_start -= 1
        line_end = self.input.find('\n', char)
        return line_start, line_end

    def _format(self, error):
        start, end  = self._get_line_position_from_char(self.start)
        line_number = self._get_lineno()
        line        = self._get_line()
        offset      = self.start - start
        token_len   = 1
        output      = unicode(line, 'latin-1') + '\n'
        if token_len <= 1:
            output += (' ' * offset) + '^\n'
        else:
            output += (' ' * offset) + "'" + ('-' * (token_len - 2)) + "'\n"
        output += '%s in line %s' % (error, line_number)
        return output.encode('latin1', 'ignore')

    def _msg(self, error):
        print self._format(error)

    def _warn(self, error):
        sys.stderr.write(self._format(error) + '\n')

    def _error(self, error):
        raise Exception(self._format(error))

    def _eof(self):
        return self.start >= self.end

    def parse_string(self, input, builder):
        self._init()
        self.input   = input
        self.builder = builder
        self.end     = len(input)
        self.grammars['input'].parse(self)
        if self.start < self.end:
            self._error('parser returned, but did not complete')

    def parse(self, filename, builder):
        with open(filename, 'r') as input_file:
            return self.parse_string(input_file.read(), builder)

    def dump(self):
        for grammar in self.grammars.itervalues():
            print str(grammar)

########NEW FILE########
__FILENAME__ = Function
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Gelatin import INDENT
from Token   import Token

class Function(Token):
    def __init__(self):
        self.name = None
        self.args = []

    def parse(self, context):
        # Function names that have NO dot in them are references to another
        # grammar.
        if '.' not in self.name:
            start   = context.start
            grammar = context.grammars.get(self.name)
            if not grammar:
                raise Exception('call to undefined grammar ' + self.name)
            grammar.parse(context)
            if context.start != start:
                return 1
            return 0

        # Other functions are utilities.
        func = context.functions.get(self.name)
        if not func:
            raise Exception('unknown function ' + self.name)
        return func(context, *[a.value() for a in self.args])

    def dump(self, indent = 0):
        args = ', '.join(a.dump() for a in self.args)
        return INDENT * indent + self.name + '(' + args + ')'

########NEW FILE########
__FILENAME__ = Grammar
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Gelatin import INDENT
from Token   import Token

class Grammar(Token):
    def __init__(self):
        self.name       = None
        self.inherit    = None
        self.statements = None
        self.on_leave   = []

    def get_statements(self, context):
        if not self.inherit:
            return self.statements
        inherited = context.grammars[self.inherit].get_statements(context)
        return inherited + self.statements

    def _enter(self, context):
        context.stack.append(self)
        #print "ENTER", self.__class__.__name__

    def _leave(self, context):
        for func, args in self.on_leave:
            func(*args)
        self.on_leave = []
        context.stack.pop()
        #print "LEAVE", self.__class__.__name__

    def parse(self, context):
        self._enter(context)
        statements = self.get_statements(context)
        matched    = True
        while matched:
            if context._eof():
                self._leave(context)
                return
            matched = False
            #context._msg(self.name)
            for statement in statements:
                result = statement.parse(context)
                if result == 1:
                    matched = True
                    break
                elif result < 0:
                    self._leave(context)
                    return result + 1
        context._error('no match found, context was ' + self.name)

    def dump(self, indent = 0):
        res = INDENT * indent + 'grammar ' + self.name
        if self.inherit:
            res += '(' + self.inherit + ')'
        res += ':\n'
        for statement in self.statements:
            res += statement.dump(indent + 1)
        return res

########NEW FILE########
__FILENAME__ = MatchFieldList
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
try:
    import re2 as re
except ImportError:
    import re
from Gelatin import INDENT
from Token import Token

class MatchFieldList(Token):
    def __init__(self, modifiers = None):
        self.expressions = []
        self.regex       = None
        self.modifiers   = modifiers

    def when(self, context):
        if not self.regex:
            regex      = ')('.join(e.re_value() for e in self.expressions)
            unire      = unicode(regex, 'latin1')
            self.regex = re.compile('(' + unire + ')', self.modifiers)

        return self.regex.match(context.input, context.start)

    def match(self, context):
        match = self.when(context)
        if not match:
            return None
        context.start += len(match.group(0))
        return match

    def dump(self, indent = 0):
        res = INDENT * indent
        for expr in self.expressions:
            res += expr.dump() + ' '
        return res.rstrip()

########NEW FILE########
__FILENAME__ = MatchList
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Gelatin import INDENT
from Token   import Token

class MatchList(Token):
    def __init__(self):
        self.field_lists = []

    def when(self, context):
        for field_list in self.field_lists:
            match = field_list.when(context)
            if match:
                return match
        return None

    def match(self, context):
        for field_list in self.field_lists:
            match = field_list.match(context)
            if match:
                return match
        return None

    def dump(self, indent = 0):
        res = ''
        for field_list in self.field_lists:
            res += field_list.dump(indent) + '\n'
        return res.rstrip() + ':\n'

########NEW FILE########
__FILENAME__ = MatchStatement
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from WhenStatement import WhenStatement

class MatchStatement(WhenStatement):
    def parse(self, context):
        match = self.matchlist.match(context)
        return self._handle_match(context, match)

########NEW FILE########
__FILENAME__ = Number
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Gelatin import INDENT
from Token   import Token

class Number(Token):
    def __init__(self, number):
        self.data = number

    def value(self):
        return self.data

    def re_value(self):
        return str(self.data)

    def dump(self, indent = 0):
        return INDENT * indent + str(self.data)

########NEW FILE########
__FILENAME__ = Regex
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
try:
    import re2 as re
except ImportError:
    import re
from Gelatin import INDENT
from Token import Token

class Regex(Token):
    data   = None
    re_obj = None

    def re_value(self):
        return self.data

    def value(self):
        if not self.re_obj:
            self.re_obj = re.compile(self.data)
        return self.re_obj

    def dump(self, indent = 0):
        return INDENT * indent + '/' + self.data + '/'

########NEW FILE########
__FILENAME__ = String
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
from Gelatin import INDENT
from Token   import Token

_string_re = re.compile(r'(\\?)\$(\d*)')

class String(Token):
    def __init__(self, context, data):
        self.context = context
        self.data    = data

    def _expand_string(self, match):
        field    = match.group(0)
        escape   = match.group(1)
        fieldnum = match.group(2)

        # Check the variable name syntax.
        if escape:
            return '$' + fieldnum
        elif fieldnum == '':
            return '$'

        # Check the variable value.
        cmatch = self.context.re_stack[-1]
        try:
            value = cmatch.group(int(fieldnum) + 1)
        except IndexError, e:
            raise Exception('invalid field number %s in %s' % (fieldnum, self.data))
        return str(value)

    def value(self):
        value = _string_re.sub(self._expand_string, self.data)
        return unicode(value, 'latin-1')

    def re_value(self):
        return re.escape(self.data)

    def dump(self, indent = 0):
        return INDENT * indent + '\'' + self.data + '\''

########NEW FILE########
__FILENAME__ = SyntaxCompiler
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import re
from simpleparse.dispatchprocessor import DispatchProcessor, getString, singleMap
from Function                      import Function
from Grammar                       import Grammar
from WhenStatement                 import WhenStatement
from MatchStatement                import MatchStatement
from MatchFieldList                import MatchFieldList
from MatchList                     import MatchList
from Number                        import Number
from Regex                         import Regex
from String                        import String
from Context                       import Context

"""
Indent handling:
    o NEWLINE:
        - If the amount of indent matches the previous line, parse the \n
          and skip all indent.
        - If the amount of indent does NOT match the previous line, parse
          the \n and stay at the beginning of the new line to let INDENT
          or DEDENT figure it out.
    o INDENT: Skips all indent, then looks backward to update the indent
      count. Checks to make sure that the indent was increased.
    o DEDENT: Like INDENT, except it does not check for errors.
"""
class SyntaxCompiler(DispatchProcessor):
    """
    Processor sub-class defining processing functions for the productions.
    """
    def __init__(self):
        self.context = None

    def reset(self):
        self.context = Context()

    def _regex(self, (tag, left, right, sublist), buffer):
        regex      = Regex()
        regex.data = getString(sublist[0], buffer)
        return regex

    def _string(self, (tag, left, right, sublist), buffer):
        string = getString(sublist[0], buffer)
        return String(self.context, string)

    def _varname(self, token, buffer):
        varname = getString(token, buffer)
        return self.context.lexicon[varname]

    def _number(self, token, buffer):
        number = getString(token, buffer)
        return Number(int(number))

    def _expression(self, token, buffer):
        tag = token[0]
        if tag == 'string':
            return self._string(token, buffer)
        elif tag == 'regex':
            return self._regex(token, buffer)
        elif tag == 'varname':
            return self._varname(token, buffer)
        elif tag == 'number':
            return self._number(token, buffer)
        else:
            raise Exception('BUG: invalid token %s' % tag)

    def _match_field_list(self, (tag, left, right, sublist), buffer, flags):
        field_list = MatchFieldList(flags)
        for field in sublist:
            expression = self._expression(field, buffer)
            field_list.expressions.append(expression)
        return field_list

    def _match_list(self, (tag, left, right, sublist), buffer, flags):
        matchlist = MatchList()
        for field_list in sublist:
            field_list = self._match_field_list(field_list, buffer, flags)
            matchlist.field_lists.append(field_list)
        return matchlist

    def _match_stmt(self, (tag, left, right, sublist), buffer, flags = 0):
        matcher            = MatchStatement()
        matcher.matchlist  = self._match_list(sublist[0], buffer, flags)
        matcher.statements = self._suite(sublist[1], buffer)
        return matcher

    def _when_stmt(self, (tag, left, right, sublist), buffer, flags = 0):
        matcher            = WhenStatement()
        matcher.matchlist  = self._match_list(sublist[0], buffer, flags)
        matcher.statements = self._suite(sublist[1], buffer)
        return matcher

    def _function(self, (tag, left, right, sublist), buffer):
        function      = Function()
        function.name = getString(sublist[0], buffer)
        if len(sublist) == 1:
            return function
        for arg in sublist[1][3]:
            expression = self._expression(arg, buffer)
            function.args.append(expression)
        return function

    def _inherit(self, (tag, left, right, sublist), buffer):
        return getString(sublist[0], buffer)

    def _suite(self, (tag, left, right, sublist), buffer):
        statements = []
        for token in sublist:
            tag = token[0]
            if tag == 'match_stmt':
                statement = self._match_stmt(token, buffer)
            elif tag == 'imatch_stmt':
                statement = self._match_stmt(token, buffer, re.I)
            elif tag == 'when_stmt':
                statement = self._when_stmt(token, buffer)
            elif tag == 'function':
                statement = self._function(token, buffer)
            else:
                raise Exception('BUG: invalid token %s' % tag)
            statements.append(statement)
        return statements

    def define_stmt(self, (tag, left, right, sublist), buffer):
        name_tup, value_tup = sublist
        value_tag           = value_tup[0]
        name                = getString(name_tup,   buffer)
        value               = getString(value_tup,  buffer)
        if value_tag == 'regex':
            value = self._regex(value_tup, buffer)
        elif value_tag == 'varname':
            if not self.context.lexicon.has_key(value):
                _error(buffer, value_tup[1], 'no such variable')
            value = self.context.lexicon[value]
        else:
            raise Exception('BUG: invalid token %s' % value_tag)
        self.context.lexicon[name] = value

    def grammar_stmt(self, (tag, left, right, sublist), buffer):
        map                = singleMap(sublist)
        grammar            = Grammar()
        grammar.name       = getString(map['varname'], buffer)
        grammar.statements = self._suite(map['suite'], buffer)
        if map.has_key('inherit'):
            grammar.inherit = self._inherit(map['inherit'], buffer)
        self.context.grammars[grammar.name] = grammar

########NEW FILE########
__FILENAME__ = Token
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Gelatin import INDENT

class Token(object):
    def dump(self, indent = 0):
        return INDENT * indent, self.__class__.__name__

########NEW FILE########
__FILENAME__ = WhenStatement
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Gelatin import INDENT
from Token   import Token

class WhenStatement(Token):
    def __init__(self):
        self.matchlist  = None
        self.statements = None
        self.on_leave   = []

    def _enter(self, context):
        context.stack.append(self)

    def _leave(self, context):
        for func, args in self.on_leave:
            func(*args)
        self.on_leave = []
        context.stack.pop()

    def _handle_match(self, context, match):
        if not match:
            return 0
        self._enter(context)
        context._match_before_notify(match)
        for statement in self.statements:
            result = statement.parse(context)
            if result == 1:
                break
            elif result < 0:
                context._match_after_notify(match)
                self._leave(context)
                return result
        context._match_after_notify(match)
        self._leave(context)
        return 1

    def parse(self, context):
        match = self.matchlist.when(context)
        return self._handle_match(context, match)

    def dump(self, indent = 0):
        res  = INDENT * indent + 'match:\n'
        res += self.matchlist.dump(indent + 1)
        for statement in self.statements:
            res += statement.dump(indent + 2) + '\n'
        return res

########NEW FILE########
__FILENAME__ = Builder
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
import re
import shutil
from tempfile import NamedTemporaryFile
from urlparse import urlparse
from cgi import parse_qs

value   = r'"(?:\\.|[^"])*"'
attrib  = r'(?:[\$\w\-]+=%s)' % value
path_re = re.compile(r'^[^/"\?]+(?:\?%s?(?:&%s?)*)?' % (attrib, attrib))

class Builder(object):
    """
    Abstract base class for all generators.
    """
    def __init__(self):
        raise NotImplementedError('abstract method')

    def serialize(self):
        raise NotImplementedError('abstract method')

    def serialize_to_file(self, filename):
        with NamedTemporaryFile(delete = False) as thefile:
            thefile.write(self.serialize())
        if os.path.exists(filename):
            os.unlink(filename)
        shutil.move(thefile.name, filename)

    def dump(self):
        raise NotImplementedError('abstract method')

    def _splitpath(self, path):
        match  = path_re.match(path)
        result = []
        while match is not None:
            result.append(match.group(0))
            path  = path[len(match.group(0)) + 1:]
            match = path_re.match(path)
        return result

    def _splittag(self, tag):
        url     = urlparse(tag)
        attribs = []
        for key, value in parse_qs(url.query).iteritems():
            value = value[0]
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            attribs.append((str(key.lower()), value))
        return url.path.replace(' ', '-').lower(), attribs

    def create(self, path, data = None):
        """
        Creates the given node, regardless of whether or not it already
        exists.
        Returns the new node.
        """
        raise NotImplementedError('abstract method')

    def add(self, path, data = None, replace = False):
        """
        Creates the given node if it does not exist.
        Returns the (new or existing) node.
        """
        raise NotImplementedError('abstract method')

    def add_attribute(self, path, name, value):
        """
        Creates the given attribute and sets it to the given value.
        Returns the (new or existing) node to which the attribute was added.
        """
        raise NotImplementedError('abstract method')

    def open(self, path):
        """
        Creates and enters the given node, regardless of whether it already
        exists.
        Returns the new node.
        """
        raise NotImplementedError('abstract method')

    def enter(self, path):
        """
        Enters the given node. Creates it if it does not exist.
        Returns the node.
        """
        raise NotImplementedError('abstract method')

    def leave(self):
        """
        Returns to the node that was selected before the last call to enter().
        The history is a stack, to the method may be called multiple times.
        """
        raise NotImplementedError('abstract method')

########NEW FILE########
__FILENAME__ = Dummy
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Builder import Builder

class Dummy(Builder):
    def __init__(self):
        pass

    def serialize(self):
        return ''

    def dump(self):
        print self.serialize()

    def add(self, path, data = None, replace = False):
        pass

    def open(self, path):
        pass

    def enter(self, path):
        pass

    def leave(self):
        pass

########NEW FILE########
__FILENAME__ = Json
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import json
from collections import defaultdict
from Builder import Builder
from pprint import PrettyPrinter

class Node:
    def __init__(self, name, attribs = None):
        self.name = name
        self.attribs = attribs and attribs or []
        self.children = defaultdict(list)
        self.text = None

    def add(self, child):
        self.children[child.name].append(child)
        return child

    def get_child(self, name, attribs = None):
        """
        Returns the first child that matches the given name and
        attributes.
        """
        if name == '.':
            if attribs is None or len(attribs) == 0:
                return self
            if attribs == self.attribs:
                return self
        for child in self.children[name]:
            if child.attribs == attribs:
                return child
        return None

    def to_dict(self):
        thedict = dict(('@' + k, v) for (k, v) in self.attribs)
        children_dict = dict()
        for name, child_list in self.children.iteritems():
            if len(child_list) == 1:
                children_dict[name] = child_list[0].to_dict()
                continue
            children_dict[name] = [child.to_dict() for child in child_list]
        thedict.update(children_dict)
        if self.text is not None:
            thedict['#text'] = self.text
        return thedict

    def dump(self, indent = 0):
        for name, children in self.children.iteritems():
            for child in children:
                child.dump(indent + 1)

class Json(Builder):
    """
    Abstract base class for all generators.
    """
    def __init__(self):
        self.tree    = Node('root')
        self.current = [self.tree]

    def serialize(self):
        return json.dumps(self.tree.to_dict(), indent = 4)

    def dump(self):
        #pp = PrettyPrinter(indent = 4)
        #pp.pprint(self.tree.to_dict())
        self.tree.dump()

    def create(self, path, data = None):
        node    = self.current[-1]
        path    = self._splitpath(path)
        n_items = len(path)
        for n, item in enumerate(path):
            tag, attribs = self._splittag(item)

            # The leaf node is always newly created.
            if n == n_items:
                node = node.add(Node(tag, attribs))
                break

            # Parent nodes are only created if they do not exist yet.
            existing = node.get_child(tag, attribs)
            if existing:
                node = existing
            else:
                node = node.add(Node(tag, attribs))
        return node

    def add(self, path, data = None, replace = False):
        node = self.current[-1]
        for item in self._splitpath(path):
            tag, attribs = self._splittag(item)
            next_node    = node.get_child(tag, attribs)
            if next_node is not None:
                node = next_node
            else:
                node = node.add(Node(tag, attribs))
        if replace:
            node.text = ''
        if data:
            node.text = data
        return node

    def add_attribute(self, path, name, value):
        node = self.add(path)
        node.attribs.append((name, value))
        return node

    def open(self, path):
        self.current.append(self.create(path))
        return self.current[-1]

    def enter(self, path):
        self.current.append(self.add(path))
        return self.current[-1]

    def leave(self):
        self.current.pop()

########NEW FILE########
__FILENAME__ = Xml
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import urllib
from Builder import Builder
from lxml    import etree

class Xml(Builder):
    def __init__(self):
        self.etree   = etree.Element('xml')
        self.current = [self.etree]
        self.stack   = []
        self.map     = dict.fromkeys(range(32))

    def serialize(self):
        return etree.tostring(self.etree, pretty_print = True)

    def dump(self):
        print self.serialize()

    def _splittag(self, path):
        tag, attribs = Builder._splittag(self, path)
        theattribs   = []
        for key, value in attribs:
            theattribs.append((key, value))
        return tag, theattribs

    def _tag2xpath(self, tag, attribs):
        tag = tag.replace(' ', '-')
        if not attribs:
            return tag
        attribs = ['@' + k + '="' + v.replace('"', '%22') + '"' for k, v in attribs]
        return './' + tag + '[' + ' and '.join(attribs) + ']'

    def create(self, path, data = None):
        node    = self.current[-1]
        path    = self._splitpath(path)
        n_items = len(path)
        for n, item in enumerate(path, 1):
            tag, attribs = self._splittag(item)

            # The leaf node is always newly created.
            if n == n_items:
                node = etree.SubElement(node, tag, **dict(attribs))
                break

            # Parent nodes are only created if the do not exist yet.
            xp       = self._tag2xpath(tag, attribs)
            existing = node.find(xp)
            if existing is not None:
                node = existing
            else:
                node = etree.SubElement(node, tag, **dict(attribs))

        if data:
            node.text = data.translate(self.map)
        return node

    def add(self, path, data = None, replace = False):
        node = self.current[-1]
        for item in self._splitpath(path):
            tag, attribs = self._splittag(item)
            xpath        = self._tag2xpath(tag, attribs)
            try:
                next_node = node.xpath(xpath)
            except etree.XPathEvalError:
                msg = 'Invalid path: %s (%s)' % (repr(path), repr(xpath))
                raise Exception(msg)
            if next_node:
                node = next_node[0]
            else:
                node = etree.SubElement(node, tag, **dict(attribs))
        if replace:
            node.text = ''
        if data:
            node.text  = node.text is not None and node.text or ''
            node.text += data.translate(self.map)
        return node

    def add_attribute(self, path, name, value):
        node = self.add(path)
        node.attrib[name] = value
        return node

    def open(self, path):
        #print "OPEN", path
        node = self.create(path)
        self.stack.append(self.current[-1])
        self.current.append(node)
        return node

    def enter(self, path):
        #print "ENTER", path
        node = self.add(path)
        self.stack.append(self.current[-1])
        self.current.append(node)
        return node

    def leave(self):
        #print "LEAVE"
        node = self.stack.pop()
        while self.current[-1] != node:
            self.current.pop()

########NEW FILE########
__FILENAME__ = Yaml
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import yaml
from Json import Json

class Yaml(Json):  # Steal most of the implementation from JSON
    """
    Abstract base class for all generators.
    """
    def serialize(self):
        return yaml.dump(self.tree.to_dict())

########NEW FILE########
__FILENAME__ = Dedent
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from simpleparse.objectgenerator import Prebuilt
from simpleparse.stt.TextTools   import Call, Skip
from util                        import eat_indent, count_indent
from Token                       import Token

class Dedent(Token):
    def __call__(self, buffer, start, end):
        if start > end:
            return start + 1
        after_indent = eat_indent(buffer, start, end)
        self.processor.indent = count_indent(buffer, after_indent)
        return after_indent + 1  # +1/-1 hack

    def table(self):
        table = (None, Call, self), (None, Skip, -1)  # +1/-1 hack
        return Prebuilt(value = table, report = False)

########NEW FILE########
__FILENAME__ = Indent
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from util  import eat_indent, count_indent, error
from Token import Token

class Indent(Token):
    def __call__(self, buffer, start, end):
        after_indent = eat_indent(buffer, start, end)
        new_indent   = count_indent(buffer, after_indent)
        if new_indent != self.processor.indent + 1:
            error(buffer, start, 'Indentation error')
        self.processor.indent = new_indent
        return after_indent

########NEW FILE########
__FILENAME__ = Newline
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from simpleparse.objectgenerator import Prebuilt
from simpleparse.stt.TextTools   import Call, Skip
from util                        import eat_indent
from Token                       import Token

class Newline(Token):
    def __call__(self, buffer, start, end):
        # Skip empty lines.
        thestart = start
        try:
            if buffer[thestart] != '\n':
                return thestart
            while buffer[thestart] == '\n':
                thestart += 1
        except IndexError:
            return thestart + 2 # +1/-1 hack #EOF

        # If the indent of the non-empty line matches, we are done.
        return eat_indent(buffer, thestart, end, self.processor.indent) + 1 # +1/-1 hack

    def table(self):
        table = (None, Call, self), (None, Skip, -1) # +1/-1 hack
        return Prebuilt(value = table, report = False)

########NEW FILE########
__FILENAME__ = Parser
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import os
from simpleparse import parser
from Newline     import Newline
from Indent      import Indent
from Dedent      import Dedent
from util        import error

_ebnf_file = os.path.join(os.path.dirname(__file__), 'syntax.ebnf')
with open(_ebnf_file) as _thefile:
    _ebnf = _thefile.read()

class Parser(parser.Parser):
    def __init__(self):
        self.indent = 0
        offside     = (
            ("NEWLINE", Newline(self).table()),
            ("INDENT",  Indent(self).table()),
            ("DEDENT",  Dedent(self).table()),
        )
        parser.Parser.__init__(self, _ebnf, 'root', prebuilts = offside)

    def parse_string(self, input, compiler):
        compiler.reset()
        start, _, end = parser.Parser.parse(self, input, processor = compiler)
        if end < len(input):
            error(input, end)
        if not compiler.context.grammars.has_key('input'):
            error(input, end, 'Required grammar "input" not found.')
        return compiler.context

    def parse(self, filename, compiler):
        with open(filename, 'r') as input_file:
            return self.parse_string(input_file.read(), compiler)

########NEW FILE########
__FILENAME__ = Token
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from simpleparse.objectgenerator import Prebuilt
from simpleparse.stt.TextTools   import Call

class Token(object):
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, buffer, start, end):
        raise NotImplementedError('Token is abstract')

    def table(self):
        table = (None, Call, self),
        return Prebuilt(value = table, report = False)

########NEW FILE########
__FILENAME__ = util
# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
try:
    import re2 as re
except ImportError:
    import re
from Gelatin import INDENT_WIDTH

whitespace_re = re.compile(' *')

def _format(buffer, end, msg):
    line_start = buffer.rfind('\n', 0, end) + 1
    line_end   = buffer.find('\n', line_start)
    line_no    = buffer.count('\n', 0, end) + 1
    line       = buffer[line_start:line_end]
    offset     = end - line_start
    mark       = ' ' + ' ' * offset + '^'
    return '%s in line %d:\n%s\n%s' % (msg, line_no, repr(line), mark)

def say(buffer, end, msg):
    print _format(buffer, end, msg)

def error(buffer, end, msg = 'Syntax error'):
    msg = _format(buffer, end, msg)
    raise Exception(msg)

def eat_indent(buffer, start, end, expected_indent = None):
    result = whitespace_re.match(buffer, start, end)
    if result is None:
        # pyre2 returns None if the start parameter to match() is larger
        # than the length of the buffer.
        return start
    whitespace     = result.group(0)
    whitespace_len = len(whitespace)
    indent         = whitespace_len / INDENT_WIDTH
    if whitespace_len % INDENT_WIDTH != 0:
        msg = 'indent must be a multiple of %d' % INDENT_WIDTH
        error(buffer, start, msg)
    if expected_indent is None or expected_indent == indent:
        return start + whitespace_len
    return start

def count_indent(buffer, start):
    indent = start - buffer.rfind('\n', 0, start) - 1
    if indent % INDENT_WIDTH != 0:
        msg = 'indent must be a multiple of %d' % INDENT_WIDTH
        error(buffer, start, msg)
    if indent / INDENT_WIDTH > 2:
        msg = 'maximum indent (2 levels) exceeded.'
        error(buffer, start, msg)
    return indent / INDENT_WIDTH

########NEW FILE########
__FILENAME__ = util
import generator
from parser   import Parser
from compiler import SyntaxCompiler

def compile_string(syntax):
    """
    Builds a converter from the given syntax and returns it.

    @type  syntax: str
    @param syntax: A Gelatin syntax.
    @rtype:  compiler.Context
    @return: The compiled converter.
    """
    return Parser().parse_string(syntax, SyntaxCompiler())

def compile(syntax_file):
    """
    Like compile_string(), but reads the syntax from the file with the
    given name.

    @type  syntax_file: str
    @param syntax_file: Name of a file containing Gelatin syntax.
    @rtype:  compiler.Context
    @return: The compiled converter.
    """
    return Parser().parse(syntax_file, SyntaxCompiler())

def generate(converter, input_file, format = 'xml'):
    """
    Given a converter (as returned by compile()), this function reads
    the given input file and converts it to the requested output format.

    Supported output formats are 'xml', 'yaml', 'json', or 'none'.

    @type  converter: compiler.Context
    @param converter: The compiled converter.
    @type  input_file: str
    @param input_file: Name of a file to convert.
    @type  format: str
    @param format: The output format.
    @rtype:  str
    @return: The resulting output.
    """
    with open(input_file) as thefile:
        return generate_string(converter, thefile.read(), format = format)

def generate_to_file(converter, input_file, output_file, format = 'xml'):
    """
    Like generate(), but writes the output to the given output file
    instead.

    @type  converter: compiler.Context
    @param converter: The compiled converter.
    @type  input_file: str
    @param input_file: Name of a file to convert.
    @type  output_file: str
    @param output_file: The output filename.
    @type  format: str
    @param format: The output format.
    @rtype:  str
    @return: The resulting output.
    """
    with open(output_file, 'w') as thefile:
        result = generate(converter, input_file, format = format)
        thefile.write(result)

def generate_string(converter, input, format = 'xml'):
    """
    Like generate(), but reads the input from a string instead of
    from a file.

    @type  converter: compiler.Context
    @param converter: The compiled converter.
    @type  input: str
    @param input: The string to convert.
    @type  format: str
    @param format: The output format.
    @rtype:  str
    @return: The resulting output.
    """
    builder = generator.new(format)
    if builder is None:
        raise TypeError('invalid output format ' + repr(format))
    converter.parse_string(input, builder)
    return builder.serialize()

def generate_string_to_file(converter, input, output_file, format = 'xml'):
    """
    Like generate(), but reads the input from a string instead of
    from a file, and writes the output to the given output file.

    @type  converter: compiler.Context
    @param converter: The compiled converter.
    @type  input: str
    @param input: The string to convert.
    @type  output_file: str
    @param output_file: The output filename.
    @type  format: str
    @param format: The output format.
    @rtype:  str
    @return: The resulting output.
    """
    with open(output_file, 'w') as thefile:
        result = generate_string(converter, input_file, format = format)
        thefile.write(result)

########NEW FILE########
__FILENAME__ = version
# Warning: This file is automatically generated.
__version__ = 'DEVELOPMENT'

########NEW FILE########
