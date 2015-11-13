__FILENAME__ = fix_dict
"""Fixer for it.next() -> advance_iterator(it)"""

# Local imports
from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import, Name, Call

bind_warning = "Calls to builtin next() possibly shadowed by global binding"


class FixDict(fixer_base.BaseFix):
    BM_compatible = True
    PATTERN = """
    power< base=any+ trailer< '.' method=('iterkeys'|'iteritems'|'itervalues') > trailer< '(' ')' > >
    """

    order = "pre" # Pre-order tree traversal

    def transform(self, node, results):
        assert results
        base = results.get('base')
        if not base:
            return
        method = results['method'][0]
        touch_import(None, u'six', node)
        base = [n.clone() for n in base]
        base[0].prefix = u""
        node.replace(Call(Name(u"six.%s" % method.value, prefix=node.prefix), base))

########NEW FILE########
__FILENAME__ = fix_filter
# Copyright 2008 Armin Ronacher.
# Licensed to PSF under a Contributor Agreement.

from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import


class FixFilter(fixer_base.BaseFix):

    BM_compatible = True
    order = "pre"

    PATTERN = """
    power< 'filter'
        trailer< '('
            arglist< (
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any) |
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any)
            ) >
        ')' >
    >
    """

    def transform(self, node, results):
        touch_import(u'six.moves', u'filter', node)

########NEW FILE########
__FILENAME__ = fix_map
# Copyright 2008 Armin Ronacher.
# Licensed to PSF under a Contributor Agreement.

from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import


class FixMap(fixer_base.BaseFix):

    BM_compatible = True
    order = "pre"

    PATTERN = """
    power< 'map'
        trailer< '('
            arglist< (
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any) |
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any)
            ) >
        ')' >
    >
    """

    def transform(self, node, results):
        touch_import(u'six.moves', u'map', node)

########NEW FILE########
__FILENAME__ = fix_metaclass
# coding: utf-8
"""Fixer for __metaclass__ = X -> (six.with_metaclass(X)) methods.

   The various forms of classef (inherits nothing, inherits once, inherints
   many) don't parse the same in the CST so we look at ALL classes for
   a __metaclass__ and if we find one normalize the inherits to all be
   an arglist.

   For one-liner classes ('class X: pass') there is no indent/dedent so
   we normalize those into having a suite.

   Moving the __metaclass__ into the classdef can also cause the class
   body to be empty so there is some special casing for that as well.

   This fixer also tries very hard to keep original indenting and spacing
   in all those corner cases.
"""
# This is a derived work of Lib/lib2to3/fixes/fix_metaclass.py under the
# copyright of the Python Software Foundation, licensed under the Python
# Software Foundation License 2.
#
# Copyright notice:
#
#     Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
#     2011, 2012, 2013 Python Software Foundation. All rights reserved.
#
# Full license text: http://docs.python.org/3.4/license.html

# Author: Jack Diederich, Daniel Neuhäuser

# Local imports
from lib2to3 import fixer_base
from lib2to3.pygram import token
from lib2to3.fixer_util import Name, syms, Node, Leaf, touch_import, Call, \
    String, Comma, parenthesize


def has_metaclass(parent):
    """ we have to check the cls_node without changing it.
        There are two possiblities:
          1)  clsdef => suite => simple_stmt => expr_stmt => Leaf('__meta')
          2)  clsdef => simple_stmt => expr_stmt => Leaf('__meta')
    """
    for node in parent.children:
        if node.type == syms.suite:
            return has_metaclass(node)
        elif node.type == syms.simple_stmt and node.children:
            expr_node = node.children[0]
            if expr_node.type == syms.expr_stmt and expr_node.children:
                left_side = expr_node.children[0]
                if isinstance(left_side, Leaf) and \
                        left_side.value == '__metaclass__':
                    return True
    return False


def fixup_parse_tree(cls_node):
    """ one-line classes don't get a suite in the parse tree so we add
        one to normalize the tree
    """
    for node in cls_node.children:
        if node.type == syms.suite:
            # already in the preferred format, do nothing
            return

    # !%@#! oneliners have no suite node, we have to fake one up
    for i, node in enumerate(cls_node.children):
        if node.type == token.COLON:
            break
    else:
        raise ValueError("No class suite and no ':'!")

    # move everything into a suite node
    suite = Node(syms.suite, [])
    while cls_node.children[i+1:]:
        move_node = cls_node.children[i+1]
        suite.append_child(move_node.clone())
        move_node.remove()
    cls_node.append_child(suite)
    node = suite


def fixup_simple_stmt(parent, i, stmt_node):
    """ if there is a semi-colon all the parts count as part of the same
        simple_stmt.  We just want the __metaclass__ part so we move
        everything efter the semi-colon into its own simple_stmt node
    """
    for semi_ind, node in enumerate(stmt_node.children):
        if node.type == token.SEMI: # *sigh*
            break
    else:
        return

    node.remove() # kill the semicolon
    new_expr = Node(syms.expr_stmt, [])
    new_stmt = Node(syms.simple_stmt, [new_expr])
    while stmt_node.children[semi_ind:]:
        move_node = stmt_node.children[semi_ind]
        new_expr.append_child(move_node.clone())
        move_node.remove()
    parent.insert_child(i, new_stmt)
    new_leaf1 = new_stmt.children[0].children[0]
    old_leaf1 = stmt_node.children[0].children[0]
    new_leaf1.prefix = old_leaf1.prefix


def remove_trailing_newline(node):
    if node.children and node.children[-1].type == token.NEWLINE:
        node.children[-1].remove()


def find_metas(cls_node):
    # find the suite node (Mmm, sweet nodes)
    for node in cls_node.children:
        if node.type == syms.suite:
            break
    else:
        raise ValueError("No class suite!")

    # look for simple_stmt[ expr_stmt[ Leaf('__metaclass__') ] ]
    for i, simple_node in list(enumerate(node.children)):
        if simple_node.type == syms.simple_stmt and simple_node.children:
            expr_node = simple_node.children[0]
            if expr_node.type == syms.expr_stmt and expr_node.children:
                # Check if the expr_node is a simple assignment.
                left_node = expr_node.children[0]
                if isinstance(left_node, Leaf) and \
                        left_node.value == u'__metaclass__':
                    # We found a assignment to __metaclass__.
                    fixup_simple_stmt(node, i, simple_node)
                    remove_trailing_newline(simple_node)
                    yield (node, i, simple_node)


def fixup_indent(suite):
    """ If an INDENT is followed by a thing with a prefix then nuke the prefix
        Otherwise we get in trouble when removing __metaclass__ at suite start
    """
    kids = suite.children[::-1]
    # find the first indent
    while kids:
        node = kids.pop()
        if node.type == token.INDENT:
            break

    # find the first Leaf
    while kids:
        node = kids.pop()
        if isinstance(node, Leaf) and node.type != token.DEDENT:
            if node.prefix:
                node.prefix = u''
            return
        else:
            kids.extend(node.children[::-1])


class FixMetaclass(fixer_base.BaseFix):
    BM_compatible = True

    PATTERN = """
    classdef<any*>
    """

    def transform(self, node, results):
        if not has_metaclass(node):
            return

        fixup_parse_tree(node)

        # find metaclasses, keep the last one
        last_metaclass = None
        for suite, i, stmt in find_metas(node):
            last_metaclass = stmt
            stmt.remove()

        text_type = node.children[0].type # always Leaf(nnn, 'class')

        # figure out what kind of classdef we have
        if len(node.children) == 7:
            # Node(classdef, ['class', 'name', '(', arglist, ')', ':', suite])
            #                 0        1       2    3        4    5    6
            if node.children[3].type == syms.arglist:
                arglist = node.children[3]
            # Node(classdef, ['class', 'name', '(', 'Parent', ')', ':', suite])
            else:
                parent = node.children[3].clone()
                arglist = Node(syms.arglist, [parent])
                node.set_child(3, arglist)
        elif len(node.children) == 6:
            # Node(classdef, ['class', 'name', '(',  ')', ':', suite])
            #                 0        1       2     3    4    5
            arglist = Node(syms.arglist, [])
            node.insert_child(3, arglist)
        elif len(node.children) == 4:
            # Node(classdef, ['class', 'name', ':', suite])
            #                 0        1       2    3
            arglist = Node(syms.arglist, [])
            node.insert_child(2, Leaf(token.RPAR, u')'))
            node.insert_child(2, arglist)
            node.insert_child(2, Leaf(token.LPAR, u'('))
        else:
            raise ValueError("Unexpected class definition")

        touch_import(None, u'six', node)

        metaclass = last_metaclass.children[0].children[2].clone()
        metaclass.prefix = u''

        arguments = [metaclass]

        if arglist.children:
            if len(arglist.children) == 1:
                base = arglist.children[0].clone()
                base.prefix = u' '
            else:
                # Unfortunately six.with_metaclass() only allows one base
                # class, so we have to dynamically generate a base class if
                # there is more than one.
                bases = parenthesize(arglist.clone())
                bases.prefix = u' '
                base = Call(Name('type'), [
                    String("'NewBase'"),
                    Comma(),
                    bases,
                    Comma(),
                    Node(
                        syms.atom,
                        [Leaf(token.LBRACE, u'{'), Leaf(token.RBRACE, u'}')],
                        prefix=u' '
                    )
                ], prefix=u' ')
            arguments.extend([Comma(), base])

        arglist.replace(Call(
            Name(u'six.with_metaclass', prefix=arglist.prefix),
            arguments
        ))

        fixup_indent(suite)

        # check for empty suite
        if not suite.children:
            # one-liner that was just __metaclass_
            suite.remove()
            pass_leaf = Leaf(text_type, u'pass')
            pass_leaf.prefix = orig_meta_prefix
            node.append_child(pass_leaf)
            node.append_child(Leaf(token.NEWLINE, u'\n'))

        elif len(suite.children) > 1 and \
                 (suite.children[-2].type == token.INDENT and
                  suite.children[-1].type == token.DEDENT):
            # there was only one line in the class body and it was __metaclass__
            pass_leaf = Leaf(text_type, u'pass')
            suite.insert_child(-1, pass_leaf)
            suite.insert_child(-1, Leaf(token.NEWLINE, u'\n'))

########NEW FILE########
__FILENAME__ = fix_next
"""Fixer for it.next() -> advance_iterator(it)"""

# Local imports
from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import, Name, Call

bind_warning = "Calls to builtin next() possibly shadowed by global binding"


class FixNext(fixer_base.BaseFix):
    BM_compatible = True
    PATTERN = """
    power< base=any+ trailer< '.' attr='next' > trailer< '(' ')' > >
    """

    order = "pre" # Pre-order tree traversal

    def transform(self, node, results):
        assert results
        base = results.get('base')
        if not base:
            return
        touch_import(None, u'six', node)
        base = [n.clone() for n in base]
        base[0].prefix = u""
        node.replace(Call(Name(u"six.advance_iterator", prefix=node.prefix), base))

########NEW FILE########
__FILENAME__ = fix_print
# Copyright 2006 Google, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Fixer for print.

Change:
    'print'          into 'print()'
    'print ...'      into 'print(...)'
    'print ... ,'    into 'print(..., end=" ")'
    'print >>x, ...' into 'print(..., file=x)'

No changes are applied if print_function is imported from __future__

"""

# Local imports
from lib2to3 import patcomp, pytree, fixer_base
from lib2to3.pgen2 import token
from lib2to3.fixer_util import Name, Call, Comma, String
from libmodernize import add_future

parend_expr = patcomp.compile_pattern(
              """atom< '(' [atom|STRING|NAME] ')' >"""
              )


class FixPrint(fixer_base.BaseFix):

    BM_compatible = True

    PATTERN = """
              simple_stmt< any* bare='print' any* > | print_stmt
              """

    def transform(self, node, results):
        assert results

        bare_print = results.get("bare")

        if bare_print:
            # Special-case print all by itself
            bare_print.replace(Call(Name(u"print"), [],
                               prefix=bare_print.prefix))
            return
        assert node.children[0] == Name(u"print")
        args = node.children[1:]
        if len(args) == 1 and parend_expr.match(args[0]):
            # We don't want to keep sticking parens around an
            # already-parenthesised expression.
            return

        sep = end = file = None
        if args and args[-1] == Comma():
            args = args[:-1]
            end = " "
        if args and args[0] == pytree.Leaf(token.RIGHTSHIFT, u">>"):
            assert len(args) >= 2
            file = args[1].clone()
            args = args[3:] # Strip a possible comma after the file expression
        # Now synthesize a print(args, sep=..., end=..., file=...) node.
        l_args = [arg.clone() for arg in args]
        if l_args:
            l_args[0].prefix = u""
        if sep is not None or end is not None or file is not None:
            if sep is not None:
                self.add_kwarg(l_args, u"sep", String(repr(sep)))
            if end is not None:
                self.add_kwarg(l_args, u"end", String(repr(end)))
            if file is not None:
                self.add_kwarg(l_args, u"file", file)
        n_stmt = Call(Name(u"print"), l_args)
        n_stmt.prefix = node.prefix
        add_future(node, u'print_function')
        return n_stmt

    def add_kwarg(self, l_nodes, s_kwd, n_expr):
        # XXX All this prefix-setting may lose comments (though rarely)
        n_expr.prefix = u""
        n_argument = pytree.Node(self.syms.argument,
                                 (Name(s_kwd),
                                  pytree.Leaf(token.EQUAL, u"="),
                                  n_expr))
        if l_nodes:
            l_nodes.append(Comma())
            n_argument.prefix = u" "
        l_nodes.append(n_argument)

########NEW FILE########
__FILENAME__ = fix_raise
"""Fixer for 'raise E, V, T'

raise         -> raise
raise E       -> raise E
raise E, V    -> raise E(V)

raise (((E, E'), E''), E'''), V -> raise E(V)


CAVEATS:
1) "raise E, V" will be incorrectly translated if V is an exception
   instance. The correct Python 3 idiom is

        raise E from V

   but since we can't detect instance-hood by syntax alone and since
   any client code would have to be changed as well, we don't automate
   this.
"""
# Author: Collin Winter, Armin Ronacher

# Local imports
from lib2to3 import pytree, fixer_base
from lib2to3.pgen2 import token
from lib2to3.fixer_util import Name, Call, is_tuple

class FixRaise(fixer_base.BaseFix):

    BM_compatible = True
    PATTERN = """
    raise_stmt< 'raise' exc=any [',' val=any] >
    """

    def transform(self, node, results):
        syms = self.syms

        exc = results["exc"].clone()
        if exc.type == token.STRING:
            msg = "Python 3 does not support string exceptions"
            self.cannot_convert(node, msg)
            return

        # Python 2 supports
        #  raise ((((E1, E2), E3), E4), E5), V
        # as a synonym for
        #  raise E1, V
        # Since Python 3 will not support this, we recurse down any tuple
        # literals, always taking the first element.
        if is_tuple(exc):
            while is_tuple(exc):
                # exc.children[1:-1] is the unparenthesized tuple
                # exc.children[1].children[0] is the first element of the tuple
                exc = exc.children[1].children[0].clone()
            exc.prefix = u" "

        if "val" not in results:
            # One-argument raise
            new = pytree.Node(syms.raise_stmt, [Name(u"raise"), exc])
            new.prefix = node.prefix
            return new

        val = results["val"].clone()
        if is_tuple(val):
            args = [c.clone() for c in val.children[1:-1]]
        else:
            val.prefix = u""
            args = [val]

        return pytree.Node(syms.raise_stmt,
                           [Name(u"raise"), Call(exc, args)],
                           prefix=node.prefix)

########NEW FILE########
__FILENAME__ = fix_range
# Copyright 2008 Armin Ronacher.
# Licensed to PSF under a Contributor Agreement.

from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import


class FixRange(fixer_base.BaseFix):

    BM_compatible = True
    order = "pre"

    PATTERN = """
    power< name='range'|'xrange'
        trailer< '('
            arglist< (
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any) |
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any) |
                (not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any ','
                 not(argument<any '=' any>) any)
            ) >
        ')' >
    >
    """

    def transform(self, node, results):
        touch_import(u'six.moves', u'range', node)
        results['name'][0].value = 'range'

########NEW FILE########
__FILENAME__ = fix_unicode
import re
from lib2to3.pgen2 import token
from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import, Name, Call

_mapping = {u"unichr" : u"chr", u"unicode" : u"str"}
_literal_re = re.compile(ur"[uU][rR]?[\'\"]")

class FixUnicode(fixer_base.BaseFix):
    BM_compatible = True
    PATTERN = """
        STRING |
        power< name='unicode'
            trailer< '(' [any] ')' >
            any *
        >
    """

    def transform(self, node, results):
        if 'name' in results:
            touch_import(None, u'six', node)
            name = results['name']
            name.replace(Name(u'six.text_type', prefix=name.prefix))
        elif node.type == token.STRING and _literal_re.match(node.value):
            touch_import(None, u'six', node)
            new = node.clone()
            new.value = new.value[1:]
            new.prefix = ''
            node.replace(Call(Name(u'six.u', prefix=node.prefix), [new]))

########NEW FILE########
__FILENAME__ = fix_unicode_future
from lib2to3.fixes import fix_unicode
from libmodernize import add_future

class FixUnicodeFuture(fix_unicode.FixUnicode):
    def transform(self, node, results):
        res = super(FixUnicodeFuture, self).transform(node, results)
        if res:
            add_future(node, 'unicode_literals')
        return res

########NEW FILE########
__FILENAME__ = fix_zip
# Copyright 2008 Armin Ronacher.
# Licensed to PSF under a Contributor Agreement.

from lib2to3 import fixer_base
from lib2to3.fixer_util import touch_import


class FixZip(fixer_base.BaseFix):

    BM_compatible = True
    order = "pre"

    PATTERN = """
    power< 'map'
        trailer< '('
            arglist< any+ >
        ')' >
    >
    """

    def transform(self, node, results):
        touch_import(u'six.moves', u'zip', node)

########NEW FILE########
__FILENAME__ = main
import sys
import logging
import optparse

from lib2to3.main import warn, StdoutRefactoringTool
from lib2to3 import refactor

from libmodernize.fixes import lib2to3_fix_names, six_fix_names


def main(args=None):
    """Main program.

    Returns a suggested exit status (0, 1, 2).
    """
    # Set up option parser
    parser = optparse.OptionParser(usage="modernize [options] file|dir ...")
    parser.add_option("-d", "--doctests_only", action="store_true",
                      help="Fix up doctests only")
    parser.add_option("-f", "--fix", action="append", default=[],
                      help="Each FIX specifies a transformation; default: all")
    parser.add_option("-j", "--processes", action="store", default=1,
                      type="int", help="Run 2to3 concurrently")
    parser.add_option("-x", "--nofix", action="append", default=[],
                      help="Prevent a fixer from being run.")
    parser.add_option("-l", "--list-fixes", action="store_true",
                      help="List available transformations")
    parser.add_option("-p", "--print-function", action="store_true",
                      help="Modify the grammar so that print() is a function")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="More verbose logging")
    parser.add_option("--no-diffs", action="store_true",
                      help="Don't show diffs of the refactoring")
    parser.add_option("-w", "--write", action="store_true",
                      help="Write back modified files")
    parser.add_option("-n", "--nobackups", action="store_true", default=False,
                      help="Don't write backups for modified files.")
    parser.add_option("--compat-unicode", action="store_true", default=False,
                      help="Leave u'' and b'' prefixes unchanged (requires "
                           "Python 3.3 and higher).")
    parser.add_option("--future-unicode", action="store_true", default=False,
                      help="Use unicode_strings future_feature instead of the six.u function "
                      "(only useful for Python 2.6+).")
    parser.add_option("--no-six", action="store_true", default=False,
                      help="Exclude fixes that depend on the six package")

    fixer_pkg = 'libmodernize.fixes'
    avail_fixes = set(refactor.get_fixers_from_package(fixer_pkg))
    avail_fixes.update(lib2to3_fix_names)

    # Parse command line arguments
    refactor_stdin = False
    flags = {}
    options, args = parser.parse_args(args)
    if not options.write and options.no_diffs:
        warn("not writing files and not printing diffs; that's not very useful")
    if not options.write and options.nobackups:
        parser.error("Can't use -n without -w")
    if options.list_fixes:
        print "Available transformations for the -f/--fix option:"
        for fixname in sorted(avail_fixes):
            print fixname
        if not args:
            return 0
    if not args:
        print >> sys.stderr, "At least one file or directory argument required."
        print >> sys.stderr, "Use --help to show usage."
        return 2
    if "-" in args:
        refactor_stdin = True
        if options.write:
            print >> sys.stderr, "Can't write to stdin."
            return 2
    if options.print_function:
        flags["print_function"] = True

    # Set up logging handler
    level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    # Initialize the refactoring tool
    unwanted_fixes = set(options.nofix)

    # Remove unicode fixers depending on command line options
    if options.compat_unicode:
        unwanted_fixes.add('libmodernize.fixes.fix_unicode')
        unwanted_fixes.add('libmodernize.fixes.fix_unicode_future')
    elif options.future_unicode:
        unwanted_fixes.add('libmodernize.fixes.fix_unicode')
    else:
        unwanted_fixes.add('libmodernize.fixes.fix_unicode_future')

    if options.no_six:
        unwanted_fixes.update(six_fix_names)
    explicit = set()
    if options.fix:
        all_present = False
        for fix in options.fix:
            if fix == "all":
                all_present = True
            else:
                explicit.add(fix)
        requested = avail_fixes.union(explicit) if all_present else explicit
    else:
        requested = avail_fixes.union(explicit)
    fixer_names = requested.difference(unwanted_fixes)
    rt = StdoutRefactoringTool(sorted(fixer_names), flags, sorted(explicit),
                               options.nobackups, not options.no_diffs)

    # Refactor all files and directories passed as arguments
    if not rt.errors:
        if refactor_stdin:
            rt.refactor_stdin()
        else:
            try:
                rt.refactor(args, options.write, options.doctests_only,
                            options.processes)
            except refactor.MultiprocessingUnsupported:
                assert options.processes > 1
                print >> sys.stderr, "Sorry, -j isn't " \
                    "supported on this platform."
                return 1
        rt.summarize()

    # Return error status (0 if rt.errors is zero)
    return int(bool(rt.errors))

########NEW FILE########
__FILENAME__ = modernize
from libmodernize.main import main
main()

########NEW FILE########
