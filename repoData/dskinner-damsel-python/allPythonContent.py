__FILENAME__ = test_basic
# -*- coding: utf-8 -*-
import os.path
import unittest
from _parse import Template
import codecs

class TestBasic(unittest.TestCase):
    def setUp(self):
        self.t = {
            'basic_ending_colon': None,
            'basic_html': None,
            'basic_indent': None,
            'basic_inline': None,
            'basic_multilinetext': None,
            'basic_tabs': None,
            'basic_tag_hashes': None,
            'basic_variable_indent': None
            }

        for k, v in self.t.items():
            # template file
            a = k+'.dmsl'
            # expected output
            b = open(os.path.join('', k+'.html')).read()
            self.t[k] = (a, b)

    def test_basic_ending_colon(self):
        parsed, expected = self.t['basic_ending_colon']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_basic_html(self):
        parsed, expected = self.t['basic_html']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_basic_indent(self):
        parsed, expected = self.t['basic_indent']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
        
    def test_basic_inline(self):
        parsed, expected = self.t['basic_inline']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_basic_multilinetext(self):
        parsed, expected = self.t['basic_multilinetext']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_basic_tabs(self):
        parsed, expected = self.t['basic_tabs']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_basic_tag_hashes(self):
        parsed, expected = self.t['basic_tag_hashes']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_basic_variable_indent(self):
        parsed, expected = self.t['basic_variable_indent']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())


########NEW FILE########
__FILENAME__ = test_py
# -*- coding: utf-8 -*-
import os.path
import unittest
#from _parse import c_parse as parse
from _parse import Template
import codecs

class TestPy(unittest.TestCase):
    def setUp(self):
        self.t = {
            'py_block_default': None,
            'py_complex1': None,
            'py_complex2': None,
            'py_complex3': None,
            'py_embed': None,
            'py_ending_colon': None,
            'py_extends': None,
            'py_formatter': None,
            'py_func': None,
            'py_ifelse': None,
            'py_ifordering': None,
            'py_if_nested': None,
            'py_include': None,
            'py_looping': None,
            'py_mixed_content': None,
            'py_nested_for': None,
            'py_newline_var': None,
            'py_raise': None
            }

        for k, v in self.t.items():
            # template file
            a = k+'.dmsl'
            # expected output
            b = open(os.path.join('', k+'.html')).read()
            self.t[k] = (a, b)

    def test_py_block_default(self):
        parsed, expected = self.t['py_block_default']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_py_complex1(self):
        parsed, expected = self.t['py_complex1']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_py_complex2(self):
        parsed, expected = self.t['py_complex2']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_py_complex3(self):
        parsed, expected = self.t['py_complex3']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_embed(self):
        parsed, expected = self.t['py_embed']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_ending_colon(self):
        parsed, expected = self.t['py_ending_colon']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_extends(self):
        parsed, expected = self.t['py_extends']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_formatter(self):
        parsed, expected = self.t['py_formatter']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_func(self):
        parsed, expected = self.t['py_func']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_ifelse(self):
        parsed, expected = self.t['py_ifelse']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_py_ifordering(self):
        parsed, expected = self.t['py_ifordering']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_py_if_nested(self):
        parsed, expected = self.t['py_if_nested']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_include(self):
        parsed, expected = self.t['py_include']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_looping(self):
        parsed, expected = self.t['py_looping']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_mixed_content(self):
        parsed, expected = self.t['py_mixed_content']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_nested_for(self):
        parsed, expected = self.t['py_nested_for']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())

    def test_py_newline_var(self):
        parsed, expected = self.t['py_newline_var']
        parsed = Template(parsed).render()
        self.assertEqual(parsed.strip(), expected.strip())
    
    def test_py_raise(self):
        parsed, expected = self.t['py_raise']
        #TODO fix this test for 2.6
        self.assertRaises(Exception, Template(parsed).render)
        #self.assertEquals(str(e.exception), 'Testing raise Exception("...")')



########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.getcwd())

import unittest
from test_basic import *
from test_py import *
#import dmsl

os.chdir('test/templates')
#dmsl.template_dir = 'test/templates'
unittest.main()

########NEW FILE########
__FILENAME__ = utils
'''
These are python equivalents of the cython parsing extensions, some are hardly
suitable for an actual pure python module of daml.
'''

directives = [u'%', u'#', u'.', u'\\']

def sub_str(a, b):
    i = len(b)
    if i == 0:
        return a
    return a[:-i]

def parse_ws(s):
    for i, c in enumerate(s):
        if c != u' ':
            return s[:i], s[i:].rstrip()
    return u'', s.rstrip()

def split_space(s):
    for i, c in enumerate(s):
        if c == u' ':
            return s[:i], s[i+1:]
    return s, u''

def split_pound(s):
    for i, c in enumerate(s):
        if c == u'#':
            return s[:i], s[i:]
    return s, u''

def split_period(s):
    for i, c in enumerate(s):
        if c == u'.':
            return s[:i], s[i:]
    return s, u''

def parse_tag(s):
    '''
    accepts input such as
    %tag.class#id.one.two
    and returns
    ('tag', 'id', 'class one two')
    '''
    r = [split_period(x) for x in split_pound(s)]
    return r[0][0][1:], r[1][0][1:], (r[0][1]+r[1][1]).replace(u'.', u' ')[1:]

def parse_attr(s):
    mark_start = None
    mark_end = None

    key_start = None
    val_start = None
    literal_start = None

    d = {}

    for i, c in enumerate(s):
        if key_start is not None:
            if val_start is not None:
                if i == val_start+1 and (c == u'"' or c == u"'"):
                    literal_start = i
                elif literal_start is not None and c == s[literal_start]:
                    d[s[key_start+1:val_start]] = s[literal_start+1:i]
                    key_start = None
                    val_start = None
                    literal_start = None
                elif literal_start is None and c == u']':
                    d[s[key_start+1:val_start]] = s[val_start+1:i]
                    key_start = None
                    val_start = None
            elif c == u'=':
                val_start = i
        elif c == u'[':
            key_start = i
            if mark_start is None:
                mark_start = i
        elif c == u' ':
            mark_end = i
            break
    
    if mark_start is None:
        return s, d
    if mark_end is None:
        return s[:mark_start], d
    else:
        return s[:mark_start]+s[mark_end:], d

def parse_inline(s, i):
    if u':' in s:
        a = s.index(u':', i)
    else:
        return u''
    if u'(' in s:
        b = s.index(u'(')
    else:
        return u''
    if u' ' in s[a:b] or a > b: # check a>b for attributes that have :
        try:
            a = s.index(u':', a+1)
            parse_inline(s, a)
        except ValueError:
            return u''

    c = s.index(u')')+1
    return s[a+1:c]

def is_assign(s):
    '''
    Tests a python string to determine if it is a variable assignment
    a = 1 # returns True
    map(a, b) # returns False
    '''
    a = s.find('(')
    b = s.find('=')
    if b != -1 and (b < a or a == -1):
        return True
    else:
        return False

def is_directive(c):
    x = u'%'
    y = u'#'
    z = u'.'

    if c != x and c != y and c != z:
        return False
    return True

########NEW FILE########
__FILENAME__ = _parse
#! /usr/bin/env python
# -*- coding: utf-8 -*-
from copy import copy, deepcopy

import _sandbox
from _pre import _pre
from _py import _compile
from cdoc import doc_pre, doc_py

def func():pass
func = type(func)

class RenderException(Exception):
    def __init__(self, f, py_str, exc_type, exc_value, exc_traceback):
        import traceback
        tb = traceback.extract_tb(exc_traceback)
        self.msg = ['']
        py_str = py_str.split('\n')

        for line in tb:
            fn = line[0]
            ln = line[1]
            fnc = line[2]
            src = line[3]
            try:
                src = py_str[ln].strip()
                for i, x in enumerate(f):
                    if src in x:
                        ln = i
                        break
            except:
                pass
            self.msg.append('  File {0}, line {1}, in {2}\n    {3}'.format(fn, ln, fnc, src))
        self.msg.append(repr(exc_value))
        #self.msg.append('\n--- DMSL PYTHON QUEUE ---')
        #self.msg.extend(py_q)
        self.msg = '\n'.join(self.msg)

    def __str__(self):
        return self.msg


class Template(object):
    debug = False

    def __init__(self, filename):
        self.sandbox = _sandbox.new()
        self.sandbox.update(_sandbox.extensions)

        if isinstance(filename, list):
            self.f = filename
            self.fn = '<string>'
        else:
            self.f = _sandbox._open(filename).read().splitlines()
            self.fn = filename

        self.r, self.py_q = _pre(self.f)
        self.r = doc_pre(self.r)

    def render(self, *args, **kwargs):
        self.sandbox['args'] = args
        self.sandbox['kwargs'] = kwargs

        r = copy(self.r)

        if len(self.py_q) == 0:
            return r.tostring()
        else:
            self.code, self.py_str = _compile(self.py_q, self.fn, kwargs)
            self.code = func(self.code.co_consts[0], self.sandbox)

        try:
            py_locals = self.code(**kwargs)
        except Exception as e:
            if isinstance(e, TypeError) or isinstance(e, KeyError):
                import sys
                if self.debug:
                    print self.py_str
                raise RenderException(self.f, self.py_str, *sys.exc_info())
            else:
                raise e

        # Check for empty doc, ussually result of python only code
        if r is None:
            return ''

        py_id = id(self.py_q)
        py_parse = py_locals['__py_parse__']
        doc_py(r, py_id, py_parse)
        return r.tostring()


if __name__ == '__main__':
    import sys
    import codecs
    from time import time
    _f = sys.argv[1]
    #print parse(_f)
    t = Template(_f)
    if '-p' in sys.argv:
        def run():
            for x in range(2000):
                t.render()
        import cProfile, pstats
        prof = cProfile.Profile()
        prof.run('run()')
        stats = pstats.Stats(prof)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        stats.print_stats(25)
    else:
        print t.render()


########NEW FILE########
__FILENAME__ = _pre
from cutils import parse_attr, split_space, parse_inline, parse_ws, sub_str, sub_strs, var_assign
from _sandbox import _open

directives = ['%', '#', '.', '\\']
py_stmts = ['for', 'if', 'while', 'try', 'except', 'with', 'def']

def is_py_stmt(l):
    if l[-1] != u':':
        return False
    for stmt in py_stmts:
        if l.startswith(stmt):
            return True
    return False

def parse_inlines(s):
    if u':' not in s:
        return s, ''
    
    l = []
    inline = parse_inline(s, 0)
    i = 0
    while inline != u'':
        s = s.replace(u':'+inline, u'{'+str(i)+u'}')
        l.append(inline)
        inline = parse_inline(s, 0)
        i += 1
    l = u','.join(l)
    if l != u'':
        l += u','
    return s, l

def expand_line(ws, l, i, f):
    el, attr = parse_attr(l)
    tag, txt = split_space(el)
    
    # Check for inlined tag hashes
    if txt != u'' and (txt[0] in directives or is_py_stmt(txt) or (txt[0] == u'[' and txt[-1] == u']')):
        l = l.replace(txt, u'')
        f[i] = ws+l
        f.insert(i+1, ws+u' '+txt)
    return l

txt_cmd = u'__py_parse__["{0}_{1}"] = {2}'
txt_fmt = u'__py_parse__["{0}_{1}"] = fmt(u"""{2}""", {3}**locals())'

def add_strs(*args):
    s = ''
    for arg in args:
        s += arg
    return s

def _pre(_f):
    f = _f[:]
    
    py_queue = []
    py_id = id(py_queue)
    py_count = 0
    
    mixed_ws = None
    mixed_ws_last = None
    get_new_mixed_ws = False
    
    comment = None
    
    i = 0
    
    while i < len(f):
        ws, l = parse_ws(f[i])
        if not l:
            del f[i]
            continue
        
        ### check for comments
        if l[:3] in [u'"""', u"'''"]:
            if comment is None:
                comment = l[:3]
                del f[i]
                continue
            elif l[:3] == comment:
                comment = None
                del f[i]
                continue
        
        if comment is not None:
            del f[i]
            continue
        ###
        
        ### maybe something better?
        if l[:8] == u'extends(':
            del f[i]
            _f = _open(l.split("'")[1]).readlines()
            for j, x in enumerate(_f):
                f.insert(i+j, x)
            continue
        if l[:8] == u'include(':
            del f[i]
            _f = _open(l.split("'")[1]).readlines()
            for j, x in enumerate(_f):
                f.insert(i+j, ws+x)
            continue
        ###
        
        # check for continued lines
        if l[-1] == u'\\':
            while l[-1] == u'\\':
                _ws, _l = parse_ws(f.pop(i+1))
                l = l[:-1] + _l
            f[i] = ws+l
        
        if l[0] in directives:
            l = expand_line(ws, l, i, f)
        elif l[0] == u'[' and l[-1] == u']': # else if list comprehension
            py_queue.append(txt_cmd.format(py_id, py_count, l))
            f[i] = ws+u'{{{0}}}'.format(py_count)
            py_count += 1
            i += 1
            continue
        # handle raise
        elif l[:5] == u'raise':
            py_queue.append(l)
            del f[i]
            i += 1
            continue
        # else if not a filter or mixed content
        elif l[0] != u':' and l[-1] != u':':
            if var_assign(l):
                py_queue.append(l)
                del f[i]
            else:
                py_queue.append(txt_cmd.format(py_id, py_count, l))
                f[i] = ws+u'{{{0}}}'.format(py_count)
                py_count += 1
                i += 1
            continue
        
        # inspect for format variables
        # and l[:3] is to prevent triggering dicts as formats in for, if, while statements
        if u'{' in l and l[:3] not in ['for', 'if ', 'whi']: # and mixed is None:
            l, inlines = parse_inlines(l)
            py_queue.append(txt_fmt.format(py_id, py_count, l, inlines))
            f[i] = ws+u'{{{0}}}'.format(py_count)
            py_count += 1
            i += 1
            continue
        
        # handle filter
        if l[0] == u':':
            func, sep, args = l[1:].partition(u' ')
            filter = [func+u'(u"""'+args]
            j = i+1
            fl_ws = None # first-line whitespace
            while j < len(f):
                _ws, _l = parse_ws(f[j])
                if _ws <= ws:
                    break
                fl_ws = fl_ws or _ws
                del f[j]
                filter.append(sub_str(_ws, fl_ws)+_l)
            filter.append(u'""", locals())')
            
            if func == u'block':
                f[i] = ws+u'{{block}}{{{0}}}'.format(args)
                py_queue.append(txt_cmd.format(py_id, py_count, u'\n'.join(filter)))
            else:
                f[i] = ws+u'{{{0}}}'.format(py_count)
                py_queue.append(txt_cmd.format(py_id, py_count, u'\n'.join(filter)))
                py_count += 1
        
        # handle mixed content
        elif is_py_stmt(l):
            orig_mixed_ws = ws
            mixed_ws = []
            mixed_ws_offset = []
            mixed_ws_last = ws
            
            content_ws = []
            content_ws_offset = []
            content_ws_last = None
            
            mixed_content_ws_offset = []
            
            get_new_mixed_ws = True
            get_new_content_ws = True
            level = 1
            
            content_ws_offset_append = False
            
            py_queue.append(u'__mixed_content__ = []')
            py_queue.append(l)
            del f[i]
            mixed_closed = False
            while i < len(f):
                _ws, _l = parse_ws(f[i])
                if not _l:
                    del f[i]
                    continue
                
                if content_ws_last is None:
                    content_ws_last = _ws
                
                if _ws <= orig_mixed_ws and _l[:4] not in [u'else', u'elif']:
                    py_queue.append(u'__py_parse__["{0}_{1}"] = list(__mixed_content__)'.format(py_id, py_count))
                    f.insert(i, mixed_ws[0]+u'{{{0}}}'.format(py_count))
                    py_count += 1
                    mixed_closed = True
                    break
                
                # check for ws changes here, python statement ws only
                if get_new_mixed_ws:
                    get_new_mixed_ws = False
                    mixed_ws_offset.append(sub_strs(_ws, mixed_ws_last))
                    if content_ws_offset_append:
                        mixed_content_ws_offset.append(sub_strs(_ws, mixed_ws_last))
                    mixed_ws.append(mixed_ws_last)
                

                # handles catching n[-1] of if,elif,else and related to align correctly
                while mixed_ws and _ws == mixed_ws[-1]:
                    mixed_ws_offset.pop()
                    mixed_ws.pop()
                
                #if _ws == mixed_ws[-1]:
                #    mixed_ws_offset.pop()
                #    mixed_ws.pop()

                # handles catching n[1:-1] of if,elif,else and related to align correctly
                while mixed_ws and _ws <= mixed_ws[-1]:
                    mixed_ws_offset.pop()
                    mixed_ws.pop()
                
                '''
                if get_new_content_ws:
                    get_new_content_ws = False
                    content_ws_offset.append(sub_strs(_ws, content_ws_last))
                    content_ws.append(content_ws_last)
                '''
                
                if _l[0] in directives:
                    _l = expand_line(_ws, _l, i, f)
                    _l, inlines = parse_inlines(_l)
                    
                    '''
                    if _ws > content_ws[-1]:
                        content_ws_offset.append(sub_strs(_ws, content_ws[-1]))
                        content_ws.append(_ws)
                    while _ws < content_ws[-1]:
                        content_ws_offset.pop()
                        content_ws.pop()
                    '''
                    #tmp_ws = add_strs(*content_ws_offset+mixed_content_ws_offset)
                    tmp_ws = sub_strs(_ws, orig_mixed_ws, *mixed_ws_offset)
                    #print '###', _l, mixed_ws_offset
                    py_queue.append(add_strs(*mixed_ws_offset)+u'__mixed_content__.append(fmt("""{0}{1}""", {2}**locals()))'.format(tmp_ws, _l, inlines))
                    
                    del f[i]
                    continue
                # is this a list comprehension?
                elif _l[0] == '[' and _l[-1] == ']':
                    py_queue.append(add_strs(*mixed_ws_offset)+u'__mixed_content__.extend({0})'.format(_l))
                    del f[i]
                else:
                    if _l[-1] == ':':
                        mixed_ws_last = _ws
                        get_new_mixed_ws = True
                        content_ws_offset_append = True
                    
                    py_queue.append(add_strs(*mixed_ws_offset)+_l)
                    
                    del f[i]
                    continue
            # maybe this could be cleaner? instead of copy and paste
            if not mixed_closed:
                py_queue.append(u'__py_parse__["{0}_{1}"] = list(__mixed_content__)'.format(py_id, py_count))
                f.insert(i, mixed_ws[0]+u'{{{0}}}'.format(py_count))
                py_count += 1
        # handle standalone embedded function calls
        elif ':' in l:
            l, inlines = parse_inlines(l)
            if inlines != '':
                py_queue.append(txt_fmt.format(py_id, py_count, l, inlines))
                f[i] = ws+u'{{{0}}}'.format(py_count)
                py_count += 1
                i += 1
                continue
        
        i += 1
    
    return f, py_queue


if __name__ == '__main__':
    import codecs
    import sys
    _f = codecs.open(sys.argv[1], 'r', 'utf-8').read().expandtabs(4).splitlines()
    f, q = _pre(_f)
    print '\n=== F ==='
    for x in f:
        print `x`
    print '\n=== Q ==='
    for x in q:
        print `x`
    

########NEW FILE########
__FILENAME__ = _py
#from _parse_pre import _parse_pre
from _pre import _pre

def _compile(py_queue, fn, kwargs):
    py_str = '\n  '.join(py_queue)
    if py_str == '':
        return None
    arg_list = ','.join([key for key in kwargs.keys()])
    py_str = 'def _py('+arg_list+'):\n  __py_parse__, __blocks__ = {}, {}\n  '+py_str+'\n  return locals()'
    return compile(py_str, fn, 'exec'), py_str


########NEW FILE########
__FILENAME__ = _sandbox
# -*- coding: utf-8 -*-

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__ #Python 3.0

from copy import copy
import os.path
from cfmt import fmt
import codecs

### Default set of dmsl extensions
def css(s, _locals):
    s = s.splitlines()
    n = s[0]
    s = s[1:]
    return [u'%link[rel=stylesheet][href={0}{1}]'.format(n, x) for x in s]

def js(s, _locals):
    s = s.splitlines()
    n = s[0]
    s = s[1:]
    return ['%script[src={0}{1}]'.format(n, x) for x in s]
###

def form(s, _locals):
    s = s.splitlines()
    n = s[0]
    d, n = n.split(' ', 1)
    s = s[1:]
    r = ['%form[action={0}][method=post]'.format(n)]
    for e in s:
        _type, _id = e.split(' ')
        label = _id.replace('_', ' ').replace('number', '#').title()
        if _type == 'hidden':
            r.append(('  %input#{0}[name={0}][type={1}][value="{2!s}"]').format(_id, _type, _locals[d][_id]))
        elif _type == 'text':
            r.append('  %label[for={0}] {1}'.format(_id, label))
            r.append(('  %input#{0}[name={0}][type={1}][value="{2!s}"]').format(_id, _type, _locals[d][_id]))
        elif _type == 'submit':
            r.append('  %input[type=submit][value={0}]'.format(label))
    return r

def _open(f):
    return codecs.open(os.path.join(_open.template_dir, f), encoding='utf-8', errors='replace')
_open.template_dir = ''

default_sandbox = { '__builtins__': None,
                    'css': css,
                    'dict': __builtin__.dict,
                    'enumerate': __builtin__.enumerate,
                    'Exception': Exception,
                    'form': form,
                    'float': __builtin__.float,
                    'fmt': fmt,
                    'globals': __builtin__.globals,
                    'int': __builtin__.int,
                    'js': js,
                    'len': __builtin__.len,
                    'list': __builtin__.list,
                    'locals': __builtin__.locals,
                    'map': __builtin__.map,
                    'max': __builtin__.max,
                    'min': __builtin__.min,
                    'open': _open,
                    'range': __builtin__.range,
                    'repr': __builtin__.repr,
                    'reversed': __builtin__.reversed,
                    'set': __builtin__.set,
                    'sorted': __builtin__.sorted,
                    'str': __builtin__.str}

# Python3
if hasattr(__builtin__, 'False'):
    default_sandbox['False'] = getattr(__builtin__, 'False')

if hasattr(__builtin__, 'True'):
    default_sandbox['True'] = getattr(__builtin__, 'True')

# Python2
if hasattr(__builtin__, 'unicode'):
    default_sandbox['unicode'] = getattr(__builtin__, 'unicode')

#

def new():
    return copy(default_sandbox)

extensions = {}

########NEW FILE########
__FILENAME__ = __main__
import argparse
import ast
import timeit
import os

from _parse import Template
import _sandbox

def parse(template, context, _locals, timed, cache, repeat):
    # use of extensions to inject _locals
    _sandbox.extensions = _locals
    try:
        if timed and cache:
            t = timeit.Timer('tpl.render()', 'from __main__ import Template\ntpl = Template("{0}")\ncontext={1}'.format(template, str(context)))
            print '%.2f ms %s' % (1000 * t.timeit(100)/100, template)
        elif timed:
            t = timeit.Timer('Template("{0}").render()'.format(template), 'from __main__ import Template')
            print '%.2f ms %s' % (1000 * t.timeit(repeat)/repeat, template)
        else:
            t = Template(template)
            print(t.render(**context))
            #print '<!DOCTYPE html>\n'+etree.tostring(etree.fromstring(t.render(**context)), pretty_print=True)
    except Exception as e:
        print 'Exception rendering ', template
        print e

def parse_templates(templates, context, _locals, timed, cache, repeat):
    for template in templates:
        path = os.path.join(_sandbox._open.template_dir, template)

        if os.path.isfile(path):
            parse(template, context, _locals, timed, cache, repeat)
        elif os.path.isdir(path):
            files = get_files(path)
            for e in files:
                # make paths relative to template directory again
                e = e.replace(_sandbox._open.template_dir, '', 1)
                parse(e, context, _locals, timed, cache, repeat)

def get_files(directory):
    files = []
    for e in os.listdir(directory):
        path = os.path.join(directory, e)
        if os.path.isfile(path) and os.path.splitext(path)[1] == '.dmsl':
            files.append(path)
        elif os.path.isdir(path):
            files.extend(get_files(path))
    return files

parser = argparse.ArgumentParser(description='Render dmsl templates.')
parser.add_argument('templates', metavar='F', type=str, nargs='+', help='Location of dmsl template file(s). If given a directory, will traverse and locate dmsl templates.')
parser.add_argument('--kwargs', dest='kwargs', type=ast.literal_eval, nargs=1, default=[{}], help='Specify a dict as a string, i.e. "{\'a\': \'b\'}", thats parsed with ast.literal_eval for use as a \
    template\'s kwargs during parse. This is the same as calling Template(\'test.dmsl\').render(**kwargs)')
parser.add_argument('--locals', dest='_locals', type=ast.literal_eval, nargs=1, default=[{}], help='Specify a dict that will be used to inject locals for use by template (Useful for testing template blocks). \
    See --kwargs for example. If timing parse, keep in mind that these variables already exist in memory and are not instantiated in the template.')
parser.add_argument('--template-dir', dest='template_dir', type=str, nargs=1, default=None, help='If a template directory is given, templates should be specified local to that directory. Useful for testing templates \
    with include and extends.')
parser.add_argument('--timeit', dest='timed', action='store_const', const=True, default=False, help='Time the duration of parse.')
parser.add_argument('--cache', dest='cache', action='store_const', const=True, default=False, help='When timing parse,  prerender portions of the template and time final render.')
parser.add_argument('--repeat', dest='repeat', type=int, nargs=1, default=[100], help='When timing parse, specify number of runs to make.')
parser.add_argument('--debug', dest='debug', action='store_const', const=True, default=False, help='Parser step output for debugging module and templates. Negates any other options set (except --template-dir) and only applicable for parsing a single template file.')

args = parser.parse_args()

if args.template_dir is not None:
    _sandbox._open.template_dir = args.template_dir[0]

if not args.debug:
    parse_templates(args.templates, args.kwargs[0], args._locals[0], args.timed, args.cache, args.repeat[0])
else:
    import pprint
    from _pre import _pre
    from _py import _compile

    pp = pprint.PrettyPrinter(depth=3)

    fn = args.templates[0]
    f = _sandbox._open(fn).read().splitlines()
    r, py_q = _pre(f)
    print('\n!!! r !!!\n')
    pp.pprint(r)
    print('\n@@@ py_q @@@\n')
    pp.pprint(py_q)
    print('\n### py_str ###\n')
    code, py_str = _compile(py_q, fn)
    print(py_str)
    print('\n$$$$$$$$$$\n')





########NEW FILE########
