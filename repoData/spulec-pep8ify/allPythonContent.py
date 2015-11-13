__FILENAME__ = fix_blank_lines
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from .utils import find_indentation
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols

from .utils import (get_whitespace_before_definition, has_parent,
    tuplize_comments)


class FixBlankLines(BaseFix):
    '''
    Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.
    '''

    def match(self, node):
        # Get classes, non-decorateds funcs, decorators, and simple statements.
        # Ignore decorateds funcs since they will be taken care of with the
        # decorator.
        if (node.type == symbols.funcdef and node.parent.type != symbols.
            decorated or node.type == symbols.classdef and node.parent.type !=
            symbols.decorated or node.type == symbols.decorated or node.type
            == symbols.simple_stmt):
            return True
        return False

    def transform(self, node, results):
        # Sometimes newlines are in prefix of current node, sometimes they're
        # in prefix of the prev sibling
        if node.prefix.count('\n'):
            newline_node = node
        else:
            newline_node = get_whitespace_before_definition(node)
            if not newline_node:
                # No previous node, must be the first node.
                return

        if newline_node.type in [token.INDENT, token.NEWLINE]:
            # If the newline_node is an indent or newline, we don't need to
            # worry about fixing indentation since it is not part of the
            # prefix. Dedents do have it as part of the prefix.
            curr_node_indentation = ''
        else:
            curr_node_indentation = find_indentation(node)
        min_lines_between_defs, max_lines_between_defs = (self.
            get_newline_limits(node))
        new_prefix = self.trim_comments(curr_node_indentation, newline_node.
            prefix, min_lines_between_defs, max_lines_between_defs)

        if newline_node.prefix != new_prefix:
            newline_node.prefix = new_prefix
            newline_node.changed()

    def get_newline_limits(self, node):
        if node.type == symbols.simple_stmt or has_parent(node, symbols.
            simple_stmt):
            max_lines_between_defs = 1
            min_lines_between_defs = 0
        elif has_parent(node, symbols.classdef) or has_parent(node, symbols.
            funcdef):
            # If we're inside a definition, only use a single space
            max_lines_between_defs = 1
            min_lines_between_defs = 1
        else:
            # Top-level definition
            max_lines_between_defs = 2
            min_lines_between_defs = 2
        return (min_lines_between_defs, max_lines_between_defs)

    def trim_comments(self, curr_node_indentation, previous_whitespace,
        min_lines_between_defs, max_lines_between_defs):
        before_comments, comments, after_comments = tuplize_comments(
            previous_whitespace)

        if before_comments.count("\n") > max_lines_between_defs:
            before_comments = '\n' * max_lines_between_defs
        if after_comments.count("\n") > max_lines_between_defs:
            after_comments = '\n' * max_lines_between_defs

        if (before_comments.count("\n") + after_comments.count("\n") >
            max_lines_between_defs):
            if before_comments and after_comments:
                # If there are spaces before and after, trim them down on both
                # sides to either 1 before and 1 after or 0 before and 1 after.
                before_comments = ('\n' * (min_lines_between_defs - 1) if
                    min_lines_between_defs else '')
                after_comments = '\n'

        comment_lines = before_comments.count("\n") + after_comments.count(
            "\n")
        if comment_lines < min_lines_between_defs:
            before_comments += (min_lines_between_defs - comment_lines) * '\n'
        result = '%s%s%s' % (before_comments, comments, after_comments)

        # Make sure that the result indenation matches the original indentation
        if result.split('\n')[-1] != curr_node_indentation:
            result = "%s%s" % (result.rstrip(' '), curr_node_indentation)
        return result

########NEW FILE########
__FILENAME__ = fix_compound_statements
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from .utils import find_indentation
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols
from lib2to3.pytree import Node, Leaf


NL = Leaf(token.NEWLINE, '\n')

class FixCompoundStatements(BaseFix):
    """
    Compound statements (multiple statements on the same line) are
    generally discouraged.

    While sometimes it's okay to put an if/for/while with a small body
    on the same line, never do this for multi-clause statements. Also
    avoid folding such long lines!
    """

    def match(self, node):
        results = {}
        if (node.prev_sibling and isinstance(node.prev_sibling, Leaf) and node.
            prev_sibling.type == token.COLON and node.type != symbols.suite):
            # If it's inside a lambda definition, subscript, or sliceop, leave
            # it alone
            # symbols.trailer
            if node.parent.type in [symbols.lambdef, symbols.subscript,
                symbols.sliceop, symbols.dictsetmaker, symbols.trailer]:
                pass
            else:
                results["colon"] = True
        if (node.type == symbols.simple_stmt and Leaf(token.SEMI, ';') in node
            .children):
            results["semi"] = True
        return results

    def transform(self, node, results):
        if results.get("colon"):
            node = self.transform_colon(node)
        if results.get("semi"):
            node = self.transform_semi(node)

    def transform_colon(self, node):
        node_copy = node.clone()
        # Strip any whitespace that could have been there
        node_copy.prefix = node_copy.prefix.lstrip()
        old_depth = find_indentation(node)
        new_indent = '%s%s' % ((' ' * 4), old_depth)
        new_node = Node(symbols.suite, [Leaf(token.NEWLINE, '\n'), Leaf(token
            .INDENT, new_indent), node_copy, Leaf(token.DEDENT, '')])
        node.replace(new_node)
        node.changed()

        # Replace node with new_node in case semi
        return node_copy

    def transform_semi(self, node):
        for child in node.children:
            if child.type == token.SEMI:
                next_sibling = child.next_sibling
                # If the next sibling is a NL, this is a trailing semicolon;
                # simply remove it and the NL's prefix
                if next_sibling == NL:
                    child.remove()
                    continue

                # Strip any whitespace from the next sibling
                prefix = next_sibling.prefix
                stripped_prefix = prefix.lstrip()
                if prefix != stripped_prefix:
                    next_sibling.prefix = stripped_prefix
                    next_sibling.changed()
                # Replace the semi with a newline
                old_depth = find_indentation(child)

                child.replace([Leaf(token.NEWLINE, '\n'),
                               Leaf(token.INDENT, old_depth)])
                child.changed()
        return node

########NEW FILE########
__FILENAME__ = fix_extraneous_whitespace
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token

from .utils import node_text

LSTRIP_TOKENS = [token.LPAR, token.LSQB, token.LBRACE]
RSTRIP_TOKENS = [token.RPAR, token.RSQB, token.COLON, token.COMMA, token.SEMI,
    token.RBRACE]
STRIP_TOKENS = RSTRIP_TOKENS + LSTRIP_TOKENS


class FixExtraneousWhitespace(BaseFix):
    '''
    Avoid extraneous whitespace in the following situations:

    - Immediately inside parentheses, brackets or braces.

    - Immediately before a comma, semicolon, or colon.
    '''

    def match(self, node):
        if node.type in STRIP_TOKENS:
            return True
        return False

    def transform(self, node, results):
        if node.type in LSTRIP_TOKENS and node.get_suffix():
            new_prefix = node.next_sibling.prefix.lstrip(' \t')
            if node.next_sibling.prefix != new_prefix:
                node.next_sibling.prefix = new_prefix
                node.next_sibling.changed()
        elif node.type in RSTRIP_TOKENS and not node.prefix.count('\n'):
            # If the prefix has a newline, this node is the beginning
            # of a newline, no need to do anything.
            new_prefix = node.prefix.rstrip(' \t')
            if node.prev_sibling:
                prev_sibling_text = node_text(node.prev_sibling)
                # If the previous sibling ended in a comma, we don't want to
                # remove this space
                if prev_sibling_text[-1] == ',':
                    new_prefix = "%s " % new_prefix
            if node.prefix != new_prefix:
                node.prefix = new_prefix
                node.changed()

########NEW FILE########
__FILENAME__ = fix_imports_on_separate_lines
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from .utils import find_indentation
from lib2to3.pgen2 import token
from lib2to3.pytree import Node, Leaf
from lib2to3.pygram import python_symbols as symbols


class FixImportsOnSeparateLines(BaseFix):
    '''
    Imports should usually be on separate lines.
    '''

    def match(self, node):
        if (node.type == symbols.simple_stmt and
            node.children[0].type == symbols.import_name and
            node.children[0].children[1].type == symbols.dotted_as_names):
            return node.children[0].children[1].children
        return False

    def transform(self, node, results):
        child_imports = [leaf.value for leaf in results if leaf.type == token.
            NAME]
        current_indentation = find_indentation(node)
        new_nodes = []
        for index, module_name in enumerate(child_imports):
            new_prefix = current_indentation
            if not index:
                # Keep the prefix, if this is the first import name
                new_prefix = node.prefix
            new_nodes.append(Node(symbols.simple_stmt, [Node(symbols.
                import_name, [Leaf(token.NAME, 'import', prefix=new_prefix),
                Leaf(token.NAME, module_name, prefix=" ")]), Leaf(token.
                NEWLINE, '\n')]))

        node.replace(new_nodes)
        node.changed()

########NEW FILE########
__FILENAME__ = fix_indentation
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pytree import Leaf
from lib2to3.pgen2 import token

import re

from .utils import prefix_indent_count, IS_26, add_leaves_method, NUM_SPACES, SPACES


class FixIndentation(BaseFix):
    """
    Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.
    """

    def __init__(self, options, log):
        self.indents = []
        self.indent_level = 0
        self.line_num = 0
        self.current_line_dedent = None
        # This is the indent of the previous line before it was modified
        self.prev_line_indent = 0

        super(FixIndentation, self).__init__(options, log)

    def match(self, node):
        if isinstance(node, Leaf):
            return True
        return False

    def transform(self, node, results):
        if node.type == token.INDENT:
            self.current_line_dedent = None
            self.transform_indent(node)
        elif node.type == token.DEDENT:
            self.transform_outdent(node)
        elif self.line_num != node.lineno:
            self.current_line_dedent = None
            self.transform_newline(node)

    def transform_indent(self, node):
        if IS_26:
            node = add_leaves_method(node)
        self.line_num = node.lineno
        # Indent spacing is stored in the value, node the prefix
        self.prev_line_indent = len(node.value.replace('\t', SPACES))
        self.indents.append(self.prev_line_indent)
        self.indent_level += 1

        new_value = SPACES * self.indent_level
        new_prefix = '\n'.join(self.align_preceding_comment(node)).rstrip(' ')

        if node.value != new_value or node.prefix != new_prefix:
            node.value = new_value
            node.prefix = new_prefix
            node.changed()

    def transform_outdent(self, node):
        if self.line_num == node.lineno:
            # If a line dedents more then one level (so it's a
            # multi-level dedent), there are several DEDENT nodes.
            # These have the same lineno, but only the very first one
            # has a prefix, the others must not.
            is_consecutive_indent = True
            assert not node.prefix # must be empty
            assert (self.current_line_dedent is None or
                    self.current_line_dedent.lineno == node.lineno)
        else:
            is_consecutive_indent = False
            self.current_line_dedent = node
            assert node.prefix or node.column == 0 # must not be empty

        self.line_num = node.lineno
        self.prev_line_indent = prefix_indent_count(node)

        # outdent, remove highest indent
        self.indent_level -= 1
        # if the last node was a dedent, too, modify that node's prefix
        # and remember that node
        self.fix_indent_prefix(self.current_line_dedent,
                               not is_consecutive_indent)
        # pop indents *after* prefix/comment has been reindented,
        # as the last indent-level may be needed there.
        self.indents.pop()


    def transform_newline(self, node):
        self.line_num = node.lineno
        if self.indent_level:
            # Don't reindent continuing lines that are already indented
            # past where they need to be.
            current_indent = prefix_indent_count(node)
            if current_indent <= self.prev_line_indent:
                self.fix_indent_prefix(node)
        else:
            # First line, no need to do anything
            pass

    def align_preceding_comment(self, node):
        prefix = node.prefix
        # Strip any previous empty lines since they shouldn't change
        # the comment indent
        comment_indent = re.sub(r'^([\s\t]*\n)?', '', prefix).find("#")
        if comment_indent > -1:
            # Determine if we should align the comment with the line before or
            # after
            # Default: indent to current level
            new_comment_indent = SPACES * self.indent_level

            if (node.type == token.INDENT and
                comment_indent < next(node.next_sibling.leaves()).column):
                # The comment is not aligned with the next indent, so
                # it should be aligned with the previous indent.
                new_comment_indent = SPACES * (self.indent_level - 1)
            elif node.type == token.DEDENT:
                # The comment is not aligned with the previous indent, so
                # it should be aligned with the next indent.
                try:
                    level = self.indents.index(comment_indent) + 1
                    new_comment_indent = level * SPACES
                except ValueError:
                    new_comment_indent = comment_indent * ' '
                    # indent of comment does not match an indent level
                    if comment_indent < self.indents[0]:
                        # not even at indent level 1, leave unchanged
                        new_comment_indent = comment_indent * ' '
                    else:
                        i = max(i for i in self.indents if i < comment_indent)
                        level = self.indents.index(i) + 1
                        new_comment_indent = (level * SPACES
                                              + (comment_indent-i) * ' ')

            # Split the lines of comment and prepend them with the new indent
            # value
            return [(new_comment_indent + line.lstrip()) if line else ''
                    for line in prefix.split('\n')]
        else:
            return prefix.split('\n')


    def fix_indent_prefix(self, node, align_comments=True):
        if node.prefix:

            if align_comments:
                prefix_lines = self.align_preceding_comment(node)[:-1]
            else:
                prefix_lines = node.prefix.split('\n')[:-1]
            prefix_lines.append(SPACES * self.indent_level)
            new_prefix = '\n'.join(prefix_lines)
            if node.prefix != new_prefix:
                node.prefix = new_prefix
                node.changed()

########NEW FILE########
__FILENAME__ = fix_maximum_line_length
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.fixer_util import LParen, RParen
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols
from lib2to3.pytree import Leaf, Node
from textwrap import TextWrapper

from .utils import (tuplize_comments, get_quotes, wrap_leaves,
    first_child_leaf, find_indentation, IS_26, add_leaves_method)

MAX_CHARS = 79
OPENING_TOKENS = [token.LPAR, token.LSQB, token.LBRACE]
CLOSING_TOKENS = [token.RPAR, token.RSQB, token.RBRACE]
SYMBOLS_WITH_NEWLINES_IN_COLONS = [symbols.funcdef, symbols.classdef,
    symbols.if_stmt, symbols.for_stmt, symbols.while_stmt, symbols.lambdef,
    symbols.try_stmt, symbols.with_stmt]


class FixMaximumLineLength(BaseFix):
    '''
    Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.
    '''

    explicit = True  # The user must ask for this fixer

    def match(self, node):
        if (node.type in [token.NEWLINE] or node.type == token.COLON and node.
            parent.type in SYMBOLS_WITH_NEWLINES_IN_COLONS):
            # Sometimes the newline is wrapped into the next node, so we need
            # to check the colons also.
            if self.need_to_check_node(node):
                # For colon nodes, we need to add the len of the colon also
                return True
        if any(len(line) > MAX_CHARS for line in node.prefix.split('\n')):
            # There is a line in the prefix greater than MAX_CHARS
            return True
        return False

    def transform(self, node, results):
        if self.node_needs_splitting(node):
            node_to_split = node.prev_sibling
            if node_to_split.type == token.STRING:
                self.fix_docstring(node_to_split)
            else:
                if isinstance(node_to_split, Leaf):
                    node_to_split = node_to_split.parent
                combined_prefix = self.fix_leaves(node_to_split)
                if combined_prefix:
                    node.prefix = "%s\n%s" % (node.prefix, combined_prefix.
                        rstrip())
        if (any(len(line) > MAX_CHARS for line in node.prefix.split('\n')) or
            node.prefix.count("#") and node.column + len(node.prefix) >
            MAX_CHARS):
            # Need to fix the prefix
            self.fix_prefix(node)

    @staticmethod
    def need_to_check_node(node):
        # Returns if the node or it's docstring might need to be split
        if IS_26:
            node = add_leaves_method(node)
        if node.column > MAX_CHARS:
            return True
        if (node.type == token.COLON
            and node.column + len(node.value) > MAX_CHARS):
            return True
        if node.prev_sibling and any(child.column + len(child.value)
            > MAX_CHARS for child in node.prev_sibling.leaves()):
            return True

    @staticmethod
    def node_needs_splitting(node):
        if not node.prev_sibling:
            return False

        if IS_26:
            node = add_leaves_method(node)
        if node.type == token.NEWLINE:
            node_length = len(node.prefix)
        elif node.type == token.COLON:
            node_length = len(node.prefix) - len(node.value)
        if node.type in [token.NEWLINE, token.COLON]:
            if node.column - node_length > MAX_CHARS:
                return True

            for child in node.prev_sibling.leaves():
                if child.type == token.STRING:
                    lines = node.value.split('\n')
                    if child.column + len(lines.pop(0)) > MAX_CHARS:
                        return True
                    elif any(len(line) > MAX_CHARS for line in lines):
                        return True
                elif child.column + len(child.value) > MAX_CHARS:
                    return True

    def fix_prefix(self, node):
        before_comments, comments, after_comments = tuplize_comments(node.
            prefix)

        # Combine all comment lines together
        all_comments = ' '.join([line.replace('#', '', 1).lstrip() for line
            in comments.split('\n')])

        # It's an inline comment if it has not newlines
        is_inline_comment = not node.prefix.count('\n')

        initial_indent_level = comments.find('#')
        if initial_indent_level == -1:
            split_lines = ['']
        else:
            if is_inline_comment and node.prev_sibling:
                # If inline comment, find where the prev sibling started to
                # know how to indent lines
                initial_indent_level = (first_child_leaf(node.prev_sibling).
                    column)
            indent = '%s# ' % (' ' * initial_indent_level)

            wrapper = TextWrapper(width=MAX_CHARS, initial_indent=indent,
                subsequent_indent=indent)
            split_lines = wrapper.wrap(all_comments)

            if is_inline_comment:
                # If inline comment is too long, we'll move it to the next line
                split_lines[0] = "\n%s" % split_lines[0]
            else:
                # We need to add back a newline that was lost above
                after_comments = "\n%s" % after_comments
        new_prefix = '%s%s%s' % (before_comments, '\n'.join(split_lines),
            after_comments.lstrip(' '))
        # Append the trailing spaces back
        if node.prefix != new_prefix:
            node.prefix = new_prefix
            node.changed()

    def fix_docstring(self, node_to_split):
        # docstrings
        quote_start, quote_end = get_quotes(node_to_split.value)
        max_length = MAX_CHARS - node_to_split.column

        triple_quoted = quote_start.count('"""') or quote_start.count("'''")
        comment_indent = ' ' * (4 + node_to_split.column)

        if not triple_quoted:
            # If it's not tripled-quoted, we need to start and end each line
            # with quotes
            comment_indent = '%s%s' % (comment_indent, quote_start)
            # Since we will be appending the end_quote after each line after
            # the splitting
            max_length -= len(quote_end)
            # If it's not triple quoted, we need to paren it
            node_to_split.value = "(%s)" % node_to_split.value

        wrapper = TextWrapper(width=max_length,
            subsequent_indent=comment_indent)
        split_lines = wrapper.wrap(node_to_split.value)

        if not triple_quoted:
            # If it's not triple quoted, we need to close each line except for
            # the last one
            new_split_lines = []
            for index, line in enumerate(split_lines):
                if index != len(split_lines) - 1:
                    new_split_lines.append("%s%s" % (line, quote_end))
                else:
                    new_split_lines.append(line)
            split_lines = new_split_lines

        new_nodes = [Leaf(token.STRING, split_lines.pop(0))]
        for line in split_lines:
            new_nodes.extend([Leaf(token.NEWLINE, '\n'), Leaf(token.STRING,
                line)])

        node_to_split.replace(new_nodes)
        node_to_split.changed()

    def fix_leaves(self, node_to_split):
        if IS_26:
            node_to_split = add_leaves_method(node_to_split)
        parent_depth = find_indentation(node_to_split)
        new_indent = "%s%s" % (' ' * 4, parent_depth)
        # For now, just indent additional lines by 4 more spaces

        child_leaves = []
        combined_prefix = ""
        prev_leaf = None
        for index, leaf in enumerate(node_to_split.leaves()):
            if index and leaf.prefix.count('#'):
                if not combined_prefix:
                    combined_prefix = "%s#" % new_indent
                combined_prefix += leaf.prefix.split('#')[-1]

            # We want to strip all newlines so we can properly insert newlines
            # where they should be
            if leaf.type != token.NEWLINE:
                if leaf.prefix.count('\n') and index:
                    # If the line contains a newline, we need to strip all
                    # whitespace since there were leading indent spaces
                    if (prev_leaf and prev_leaf.type in [token.DOT, token.LPAR]
                        or leaf.type in [token.RPAR]):
                        leaf.prefix = ""
                    else:
                        leaf.prefix = " "

                    # Append any trailing inline comments to the combined
                    # prefix
                child_leaves.append(leaf)
                prev_leaf = leaf

        # Like TextWrapper, but for nodes. We split on MAX_CHARS - 1 since we
        # may need to insert a leading parenth. It's not great, but it would be
        # hard to do properly.
        split_leaves = wrap_leaves(child_leaves, width=MAX_CHARS - 1,
            subsequent_indent=new_indent)
        new_node = Node(node_to_split.type, [])

        # We want to keep track of if we are breaking inside a parenth
        open_count = 0
        need_parens = False
        for line_index, curr_line_nodes in enumerate(split_leaves):
            for node_index, curr_line_node in enumerate(curr_line_nodes):
                if line_index and not node_index:
                    # If first node in non-first line, reset prefix since there
                    # may have been spaces previously
                    curr_line_node.prefix = new_indent
                new_node.append_child(curr_line_node)
                if curr_line_node.type in OPENING_TOKENS:
                    open_count += 1
                if curr_line_node.type in CLOSING_TOKENS:
                    open_count -= 1

            if line_index != len(split_leaves) - 1:
                # Don't add newline at the end since it it part of the next
                # sibling
                new_node.append_child(Leaf(token.NEWLINE, '\n'))

                # Checks if we ended a line without being surrounded by parens
                if open_count <= 0:
                    need_parens = True
        if need_parens:
            # Parenthesize the parent if we're not inside parenths, braces,
            # brackets, since we inserted newlines between leaves
            parenth_before_equals = Leaf(token.EQUAL, "=") in split_leaves[0]
            self.parenthesize_parent(new_node, parenth_before_equals)
        node_to_split.replace(new_node)

        return combined_prefix

    def parenthesize_parent(self, node_to_split, parenth_before_equals):
        if node_to_split.type == symbols.print_stmt:
            self.parenthesize_print_stmt(node_to_split)
        elif node_to_split.type == symbols.return_stmt:
            self.parenthesize_after_arg(node_to_split, "return")
        elif node_to_split.type == symbols.expr_stmt:
            if parenth_before_equals:
                self.parenthesize_after_arg(node_to_split, "=")
            else:
                self.parenthesize_expr_stmt(node_to_split)
        elif node_to_split.type == symbols.import_from:
            self.parenthesize_after_arg(node_to_split, "import")
        elif node_to_split.type in [symbols.power, symbols.atom]:
            self.parenthesize_call_stmt(node_to_split)
        elif node_to_split.type in [symbols.or_test, symbols.and_test, symbols
            .not_test, symbols.test, symbols.arith_expr, symbols.comparison]:
            self.parenthesize_test(node_to_split)
        elif node_to_split.type == symbols.parameters:
            # Paramteres are always parenthesized already
            pass

    def parenthesize_test(self, node_to_split):
        first_child = node_to_split.children[0]
        if first_child != LParen():
            # node_to_split.children[0] is the "print" literal strip the
            # current 1st child, since we will be prepending an LParen
            if first_child.prefix != first_child.prefix.strip():
                first_child.prefix = first_child.prefix.strip()
                first_child.changed()
            left_paren = LParen()
            left_paren.prefix = " "
            node_to_split.insert_child(0, left_paren)
            node_to_split.append_child(RParen())
            node_to_split.changed()

    def parenthesize_print_stmt(self, node_to_split):
        # print "hello there"
        # return a, b
        second_child = node_to_split.children[1]
        if second_child != LParen():
            # node_to_split.children[0] is the "print" literal strip the
            # current 1st child, since we will be prepending an LParen
            if second_child.prefix != second_child.prefix.strip():
                second_child.prefix = second_child.prefix.strip()
                second_child.changed()
            node_to_split.insert_child(1, LParen())
            node_to_split.append_child(RParen())
            node_to_split.changed()

    def parenthesize_after_arg(self, node_to_split, value):
        # parenthesize the leaves after the first node with the value
        value_index = 0
        for index, child in enumerate(node_to_split.children):
            if child.value == value:
                value_index = index + 1
                break
        value_child = node_to_split.children[value_index]
        if value_child != LParen():
            # strip the current 1st child, since we will be prepending an
            # LParen
            if value_child.prefix != value_child.prefix.strip():
                value_child.prefix = value_child.prefix.strip()
                value_child.changed()
            # We set a space prefix since this is after the '='
            left_paren = LParen()
            left_paren.prefix = " "
            node_to_split.insert_child(value_index, left_paren)
            node_to_split.append_child(RParen())
            node_to_split.changed()

    def parenthesize_expr_stmt(self, node_to_split):
        # x = "foo" + bar
        if node_to_split.children[0] != LParen():
            node_to_split.insert_child(0, LParen())
            node_to_split.append_child(RParen())
            node_to_split.changed()

    def parenthesize_call_stmt(self, node_to_split):
        # a.b().c()
        first_child = node_to_split.children[0]
        if first_child != LParen():
            # Since this can be at the beginning of a line, we can't just
            # strip the prefix, we need to keep leading whitespace
            first_child.prefix = "%s(" % first_child.prefix
            first_child.changed()
            node_to_split.append_child(RParen())
            node_to_split.changed()

########NEW FILE########
__FILENAME__ = fix_missing_newline
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pygram import python_symbols as symbols

from .utils import get_leaves_after_last_newline


class FixMissingNewline(BaseFix):
    '''
    The last line should have a newline.

    This is somewhat tricky since the parse tree
    sometimes categorizes newlines as token.DEDENTs
    '''

    def match(self, node):
        # We only want to work with the top-level input since this should only
        # run once.
        if node.type != symbols.file_input:
            return

        leaves_after_last_newline = get_leaves_after_last_newline(node)
        if not any(leaf.prefix.count('\n')
                   for leaf in leaves_after_last_newline):
            # If none of those have a prefix containing a newline,
            # we need to add one
            return leaves_after_last_newline[0]

    def transform(self, node, leaf):
        if leaf.prefix != '\n':
            leaf.prefix = '\n'
            leaf.changed()

########NEW FILE########
__FILENAME__ = fix_missing_whitespace
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.fixer_util import Newline
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols


class FixMissingWhitespace(BaseFix):
    '''
    Each comma, semicolon or colon should be followed by whitespace.
    '''

    def match(self, node):
        if (node.type in (token.COLON, token.COMMA, token.SEMI) and node.
            get_suffix() != " "):
            # If there is a newline after, no space
            if (node.get_suffix().find('\n') == 0 or
                (node.next_sibling and node.next_sibling.children and
                node.next_sibling.children[0] == Newline())):
                return False
            # If we are using slice notation, no space necessary
            if node.parent.type in [symbols.subscript, symbols.sliceop]:
                return False
            return True
        return False

    def transform(self, node, results):
        next_sibling = node.next_sibling
        if not next_sibling:
            next_sibling = node.parent.next_sibling
            if not next_sibling:
                return
        new_prefix = " %s" % next_sibling.prefix.lstrip(' \t')
        if next_sibling.prefix != new_prefix:
            next_sibling.prefix = new_prefix
            next_sibling.changed()

########NEW FILE########
__FILENAME__ = fix_tabs
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pytree import Leaf

from .utils import SPACES

class FixTabs(BaseFix):
    '''
    For new projects, spaces-only are strongly recommended over tabs.  Most
    editors have features that make this easy to do.
    '''

    def match(self, node):
        if node.prefix.count('\t') or (isinstance(node, Leaf)
            and node.value.count('\t')):
            return True
        return False

    def transform(self, node, results):
        new_prefix = node.prefix.replace('\t', SPACES)
        new_value = node.value.replace('\t', SPACES)
        if node.prefix != new_prefix or node.value != new_value:
            node.prefix = new_prefix
            node.value = new_value
            node.changed()

########NEW FILE########
__FILENAME__ = fix_trailing_blank_lines
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pygram import python_symbols as symbols

from .utils import get_leaves_after_last_newline


class FixTrailingBlankLines(BaseFix):
    '''
    Trailing blank lines are superfluous.
    '''

    def match(self, node):
        # We only want to work with the top-level input since this should only
        # run once.
        if node.type != symbols.file_input:
            return

        leaves_after_last_newline = get_leaves_after_last_newline(node)
        # Return any leaves with newlines.
        return [leaf for leaf in leaves_after_last_newline
            if leaf.prefix.count('\n')]

    def transform(self, node, results):
        for index, result in enumerate(results):
            if index:
                # We've already stripped one newline. Strip any remaining
                if result.prefix != result.prefix.rstrip():
                    result.prefix = result.prefix.rstrip()
                    result.changed()
            else:
                # We haven't stripped any newlines yet. We need to strip all
                # whitespace, but leave a single newline.
                if result.prefix.strip():
                    # If there are existing comments, we need to add two
                    # newlines in order to have a trailing newline.
                    new_prefix = '%s\n\n' % result.prefix.rstrip()
                else:
                    new_prefix = '%s\n' % result.prefix.rstrip()
                if result.prefix != new_prefix:
                    result.prefix = new_prefix
                    result.changed()

########NEW FILE########
__FILENAME__ = fix_trailing_whitespace
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token


class FixTrailingWhitespace(BaseFix):
    '''
    Trailing whitespace is superfluous.
    Except when it occurs as part of a blank line (i.e. the line is
    nothing but whitespace). According to Python docs[1] a line with only
    whitespace is considered a blank line, and is to be ignored. However,
    matching a blank line to its indentation level avoids mistakenly
    terminating a multi-line statement (e.g. class declaration) when
    pasting code into the standard Python interpreter.

    [1] http://docs.python.org/reference/lexical_analysis.html#blank-lines
    '''

    def match(self, node):
        # Newlines can be from a newline token or inside a node prefix
        if node.type == token.NEWLINE or node.prefix.count('\n'):
            return True

    def transform(self, node, results):
        if node.prefix.count('#'):
            prefix_split = node.prefix.split('\n')
            # Rstrip every line except for the last one, since that is the
            # whitespace before this line
            new_prefix = '\n'.join([line.rstrip(' \t') for line in
                prefix_split[:-1]] + [prefix_split[-1]])
        else:
            new_prefix = node.prefix.lstrip(' \t')
            if new_prefix[0:1] == '\\':
                # Insert a space before a backslash ending line
                new_prefix = " %s" % new_prefix
        if node.prefix != new_prefix:
            node.prefix = new_prefix
            node.changed()

########NEW FILE########
__FILENAME__ = fix_whitespace_around_operator
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols
from lib2to3.pytree import Leaf

from .utils import OPERATORS, UNARY_OPERATORS

ARG_SYMBOLS = [symbols.arglist, symbols.varargslist, symbols.typedargslist]
KEYWORKD_ARG_SYMBOLS = [symbols.argument, symbols.arglist, symbols.
    typedargslist]


class FixWhitespaceAroundOperator(BaseFix):
    '''
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.
    '''

    def match(self, node):
        if isinstance(node, Leaf) and node.value in OPERATORS:
            return True
        return False

    def transform(self, node, results):
        # Allow unary operators: -123, -x, +1.
        if (node.value in UNARY_OPERATORS and node.parent.type == symbols.
            factor):
            self.rstrip(node)
        # Allow argument unpacking: foo(*args, **kwargs).
        elif(node.value in ['*', '**'] and node.parent.type in ARG_SYMBOLS
            and (not node.prev_sibling or node.prev_sibling.type == token.
            COMMA)):
            self.rstrip(node)
        # Allow keyword assignment: foobar(foo=bar)
        elif node.value == '=' and node.parent.type in KEYWORKD_ARG_SYMBOLS:
            self.no_spaces(node)
        # Finally check if the spacing actually needs fixing
        elif(node.prefix != " " or node.get_suffix() != " "):
            self.spaces(node)

    def rstrip(self, node):
        next_sibling = node.next_sibling
        next_sibling_new_prefix = next_sibling.prefix.lstrip(' \t')
        if next_sibling.prefix != next_sibling_new_prefix:
            next_sibling.prefix = next_sibling_new_prefix
            next_sibling.changed()

    def no_spaces(self, node):
        if node.prefix != "":
            node.prefix = ""
            node.changed()

        next_sibling = node.next_sibling
        next_sibling_new_prefix = next_sibling.prefix.lstrip(' \t')
        if next_sibling.prefix != next_sibling_new_prefix:
            next_sibling.prefix = next_sibling_new_prefix
            next_sibling.changed()

    def spaces(self, node):
        if not node.prefix.count('\n'):
            # If there are newlines in the prefix, this is a continued line,
            # don't strip anything
            new_prefix = " %s" % node.prefix.lstrip(' \t')
            if node.prefix != new_prefix:
                node.prefix = new_prefix
                node.changed()

        next_sibling = node.next_sibling
        if not next_sibling:
            return
        if next_sibling.prefix.count('\n'):
            next_sibling_new_prefix = next_sibling.prefix.lstrip(' \t')
            if next_sibling_new_prefix[0:1] == '\\':
                # Insert a space before a backslash ending line
                next_sibling_new_prefix = " %s" % next_sibling_new_prefix
        else:
            next_sibling_new_prefix = " %s" % next_sibling.prefix.lstrip(
                ' \t')
        if next_sibling.prefix != next_sibling_new_prefix:
            next_sibling.prefix = next_sibling_new_prefix
            next_sibling.changed()

########NEW FILE########
__FILENAME__ = fix_whitespace_before_inline_comment
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from .utils import node_text


def get_previous_node(node):
    """
    Return the node before this node.
    """
    if node.prev_sibling:
        return node.prev_sibling
    if node.parent:
        return get_previous_node(node.parent)


class FixWhitespaceBeforeInlineComment(BaseFix):
    '''
    Separate inline comments by at least two spaces.

    An inline comment is a comment on the same line as a statement.  Inline
    comments should be separated by at least two spaces from the statement.
    They should start with a # and a single space.
    '''

    def match(self, node):
        # An inline comment must contain with a #
        if not node.prefix.count("#"):
            return False

        # If the node's prefix starts with a newline, then this is not an
        # inline comment because there is not code before this.
        if node.prefix.lstrip(" \t").startswith("\n"):
            return False

        # If the previous node ended in a newline, then this node is
        # starting the line so it is not an inline comment.
        prev_node = get_previous_node(node)
        if not prev_node:
            # If no previous node, this is not an inline comment.
            return False
        prev_node_text = node_text(prev_node)
        if prev_node_text.endswith('\n'):
            return False

        return True

    def transform(self, node, results):
        position = node.prefix.find("#")
        if position > 2:
            # Already more than two spaces before comment
            whitespace_before, comment_after = node.prefix.split("#", 1)
            new_prefix = "%s# %s" % (whitespace_before, comment_after.lstrip(
            ))
        else:
            new_prefix = "  # %s" % node.prefix.replace("#", "", 1).lstrip()
        if node.prefix != new_prefix:
            node.prefix = new_prefix
            node.changed()

########NEW FILE########
__FILENAME__ = fix_whitespace_before_parameters
from __future__ import unicode_literals
from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols


class FixWhitespaceBeforeParameters(BaseFix):
    '''
    Avoid extraneous whitespace in the following situations:

    - Immediately before the open parenthesis that starts the argument
      list of a function call.

    - Immediately before the open parenthesis that starts an indexing or
      slicing.
    '''

    def match(self, node):
        if (node.type in (token.LPAR, token.LSQB) and node.parent.type ==
            symbols.trailer):
            return True
        return False

    def transform(self, node, results):
        if node.prefix != "":
            node.prefix = ""
            node.changed()

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as symbols
from lib2to3.pytree import Leaf
import types
import sys

IS_26 = False
if sys.version_info[0] == 2 and sys.version_info[1] == 6:
    IS_26 = True

BINARY_OPERATORS = frozenset(['**=', '*=', '+=', '-=', '!=', '<>',
    '%=', '^=', '&=', '|=', '==', '/=', '//=', '<=', '>=', '<<=', '>>=',
    '%', '^', '&', '|', '=', '/', '//', '<', '>', '<<'])
UNARY_OPERATORS = frozenset(['>>', '**', '*', '+', '-'])
OPERATORS = BINARY_OPERATORS | UNARY_OPERATORS
MAX_CHARS = 79

NUM_SPACES = 4
SPACES = ' ' * NUM_SPACES


def add_leaves_method(node):
    def leaves(node):
        if isinstance(node, Leaf):
            yield node
        else:
            for child in node.children:
                for x in  leaves(child):
                    yield x

    node.leaves = types.MethodType(leaves, node)
    other_nodes = ('prev_sibling', 'next_sibling', 'parent')
    for node_str in other_nodes:
        n = getattr(node, node_str)
        if n:
            setattr(n, 'leaves', types.MethodType(leaves, n))
    return node


def find_indentation(node):
    try:
        from lib2to3.fixer_util import find_indentation
        return find_indentation(node)
    except ImportError:
        while node is not None:
            if node.type == symbols.suite and len(node.children) > 2:
                indent = node.children[1]
                if indent.type == token.INDENT:
                    return indent.value
            node = node.parent
        return ""


def get_leaves_after_last_newline(node):
    # Get all of the leaves after the last newline leaf
    if IS_26:
        node = add_leaves_method(node)
    all_leaves = []
    last_newline_leaf_index = -1
    for index, leaf in enumerate(node.leaves()):
        all_leaves.append(leaf)
        if leaf.type == token.NEWLINE:
            last_newline_leaf_index = index
    return all_leaves[last_newline_leaf_index + 1:]


def first_child_leaf(node):
    if isinstance(node, Leaf):
        return node
    elif node.children:
        return first_child_leaf(node.children[0])
    else:
        return None


def node_text(node):
    result = ""
    if isinstance(node, Leaf):
        result += node.value
    elif node.children:
        for child in node.children:
            result += node_text(child)
    return result


def get_whitespace_before_definition(node):
    if node.prev_sibling:
        return get_last_child_with_whitespace(node.prev_sibling)


def get_last_child_with_whitespace(node):
    if IS_26:
        node = add_leaves_method(node)
    leaves = []
    for leaf in node.leaves():
        leaves.append(leaf)
    reverse_leaves = reversed(leaves)
    for leaf in reverse_leaves:
        if '\n' in leaf.prefix or leaf.value == '\n':
            return leaf


def has_parent(node, symbol_type):
    # Returns if node has a parent of type symbol_type
    if node.parent:
        return node.parent.type == symbol_type or has_parent(node.parent,
            symbol_type)


def prefix_indent_count(node):
    # Find the number of spaces preceding this line
    return len(node.prefix.split('\n')[-1].replace('\t', SPACES))


def node_length(*nodes):
    return sum(len(node.prefix.strip('\n\t')) +
        len(node.value.strip('\n\t')) for node in nodes)


def tuplize_comments(prefix):
    # This tuplizes the newlines before and after the prefix
    # Given '\n\n\n    # test comment\n    \n'
    # returns (['\n\n\n'], ['    # test comment\n'], ['    \n'])

    if not prefix:
        return ('', '', '')

    # If there are no newlines, this was just a trailing comment. Leave it
    # alone.
    if not prefix.count('\n'):
        return ('', prefix, '')

    if prefix.count("#"):
        whitespace_before_first_comment = prefix[:prefix.index("#")]
        start_of_comment = whitespace_before_first_comment.rfind('\n')
        if prefix.count('\n') and not prefix.split('\n')[-1].strip():
            # Add a single newline back if there was a newline in the ending
            # whitespace
            comments = "%s\n" % prefix[start_of_comment + 1:].rstrip()
        else:
            comments = prefix[start_of_comment + 1:].rstrip()
    else:
        if prefix.count('\n'):
            comments = prefix.rsplit('\n')[1]
            # If no comments, there are no comments except the trailing spaces
            # before the current line
        else:
            comments = prefix
    comments_start = prefix.index(comments)
    return prefix[:comments_start].strip(' '), comments, prefix[
        comments_start + len(comments):]


def get_quotes(text):
    # Returns the quote type start and end
    # Given u"ur'the string'" returns (u"ur'", u"'")

    if text[:2].lower() in ['br', 'ur']:
        leading_chars = 2
    elif text[:1].lower() in ['b', 'u', 'r']:
        leading_chars = 1
    else:
        leading_chars = 0

    if text[leading_chars:leading_chars + 3] in ['"""', "'''"]:
        # Triple-quoted string
        quote_start = text[:leading_chars + 3]
    else:
        # Single-quoted string
        quote_start = text[:leading_chars + 1]
    return (quote_start, quote_start[leading_chars:])


# Like TextWrapper, but for leaves
def wrap_leaves(nodes, width=MAX_CHARS, initial_indent='',
    subsequent_indent=''):
    lines = []

    # Fake the prefix of the first node to be the indent that it should be.
    # We'll set it back afterward.
    first_node_prefix = nodes[0].prefix
    nodes[0].prefix = ' ' * nodes[0].column

    nodes.reverse()
    while nodes:
        tracking_back = False
        curr_line = []
        curr_len = 0

        # Figure out which static string will prefix this line.
        if lines:
            indent = subsequent_indent
        else:
            indent = initial_indent

        # Maximum width for this line.
        curr_width = width - len(indent)

        while nodes:
            last_node = nodes[-1]

            if lines and not curr_line:
                # Strip prefixes for subsequent lines
                last_node.prefix = ''

            curr_node_length = node_length(last_node)

            # Can at least squeeze this chunk onto the current line.
            if curr_len + curr_node_length <= curr_width:
                curr_line.append(nodes.pop())
                curr_len += curr_node_length

            # Nope, this line is full.
            else:
                # only disallow breaking on/after equals if parent of this type
                if nodes and nodes[-1].type in [token.COMMA, token.EQUAL]:
                    # We don't want the next line to start on one of these
                    # tokens
                    tracking_back = True
                    nodes.append(curr_line.pop())
                if (curr_line and curr_line[-1].type == token.EQUAL and
                    curr_line[-1].parent.type != symbols.expr_stmt):
                    # We don't want this line to end on one of these tokens.
                    # Move the last two nodes back onto the list
                    tracking_back = True
                    nodes.extend(reversed(curr_line[-2:]))
                    del curr_line[-2:]
                break

        # The current line is full, and the next chunk is too big to fit on
        # *any* line (not just this one).
        if nodes:
            next_chunk_length = node_length(nodes[-1])
            if tracking_back:
                next_chunk_length += node_length(nodes[-2])
            if next_chunk_length > curr_width:
                curr_line.append(nodes.pop())
                if nodes and nodes[-1].type in [token.COMMA, token.EQUAL]:
                    # We don't want the next line to start on these chars, just
                    # add them here Check maximum_line_length3_in:4 for an
                    # example
                    curr_line.append(nodes.pop())
            elif (len(nodes) > 2 and not curr_line and
                node_length(*nodes[-3:]) > curr_width):
                # This scenario happens when we were not able to break on an
                # assignment statement above and the next line is still too
                # long. Remove the last 3 nodes and move them to curr_line
                curr_line.extend(reversed(nodes[-3:]))
                del nodes[-3:]
                if nodes and nodes[-1].type in [token.COMMA, token.EQUAL]:
                    curr_len += node_length(nodes[-1])
                    curr_line.append(nodes.pop())

        if curr_line:
            curr_line[0].prefix = "%s%s" % (indent, curr_line[0].prefix)
            lines.append(curr_line)
        else:
            assert False, ("There was an error parsing this line."
                "Please report this to the package owner.")

    lines[0][0].prefix = first_node_prefix
    return lines

########NEW FILE########
__FILENAME__ = pep8ify
#!/usr/bin/env python

import lib2to3.main

try:
    import pep8ify.fixes
except ImportError:
    # if importing pep8ify fails, try to load from parent
    # directory to support running without installation
    import imp, os
    if not hasattr(os, 'getuid') or os.getuid() != 0:
        imp.load_module('pep8ify', *imp.find_module('pep8ify',
            [os.path.dirname(os.path.dirname(__file__))]))


def _main():
    raise SystemExit(lib2to3.main.main("pep8ify.fixes"))

if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = blank_lines1_in
def a():
    pass


# asdfasdf
def b():
    pass


@dec1
@dec2
def a():
    pass


# Foo
# Bar


def b():
    pass


class Foo:
    b = 0
    def bar():
        pass


    
    
    def bar2():
        pass

@decoratedclass
class Baz:
    def zorp():
        pass

def testing345():
    pass

def b(n):
    pass

def a():
    pass



def b(n):
    pass
def testing123():



    pass
@decorator
def a():
    print "testing 1"



    # test comment
    print "testing 2"

    print "testing 3"

foo = 7


bar = 2

########NEW FILE########
__FILENAME__ = blank_lines1_out
def a():
    pass


# asdfasdf
def b():
    pass


@dec1
@dec2
def a():
    pass

# Foo
# Bar

def b():
    pass


class Foo:
    b = 0

    def bar():
        pass

    def bar2():
        pass


@decoratedclass
class Baz:
    def zorp():
        pass


def testing345():
    pass


def b(n):
    pass


def a():
    pass


def b(n):
    pass


def testing123():

    pass


@decorator
def a():
    print "testing 1"

    # test comment
    print "testing 2"

    print "testing 3"

foo = 7

bar = 2

########NEW FILE########
__FILENAME__ = compound_statements1_in
if foo == 'blah':
    do_blah_thing()
do_one()
do_two()
do_three()

lambda x: 2 * x

if foo == 'blah': do_blah_thing()
for x in lst: total += x
while t < 10: t = delay()
if foo == 'blah': do_blah_thing()
else: do_non_blah_thing()
try: something()
finally: cleanup()


def func():
    if foo == 'blah':
        four()


def func():
    if foo == 'blah': four(); five()


def func2(): print "testing"

if foo == 'blah': one(); two(); three()

do_one(); do_two(); do_three()

if foo == 'blah':
    all_one(); all_two(); all_three()

########NEW FILE########
__FILENAME__ = compound_statements1_out
if foo == 'blah':
    do_blah_thing()
do_one()
do_two()
do_three()

lambda x: 2 * x

if foo == 'blah':
    do_blah_thing()
for x in lst:
    total += x
while t < 10:
    t = delay()
if foo == 'blah':
    do_blah_thing()
else:
    do_non_blah_thing()
try:
    something()
finally:
    cleanup()


def func():
    if foo == 'blah':
        four()


def func():
    if foo == 'blah':
        four()
        five()


def func2():
    print "testing"

if foo == 'blah':
    one()
    two()
    three()

do_one()
do_two()
do_three()

if foo == 'blah':
    all_one()
    all_two()
    all_three()

########NEW FILE########
__FILENAME__ = compound_statements2_in
def testing():
    return range(10)[:]

########NEW FILE########
__FILENAME__ = compound_statements2_out
def testing():
    return range(10)[:]

########NEW FILE########
__FILENAME__ = compound_statements3_in

do_it() ;

def x():
    do_it() ;
    dont_do_it()

def y():
    do_it() ;
    # comment
    dont_do_it()

########NEW FILE########
__FILENAME__ = compound_statements3_out

do_it()


def x():
    do_it()
    dont_do_it()


def y():
    do_it()
    # comment
    dont_do_it()

########NEW FILE########
__FILENAME__ = extraneous_whitespace1_in
spam(ham[1], {eggs: 2})
spam( ham[1], {eggs: 2})
spam(ham[ 1], {eggs: 2})
spam(ham[1], { eggs: 2})
spam(ham[1], {eggs: 2} )
spam(ham[1 ], {eggs: 2})
spam(ham[1], {eggs: 2 })

if x == 4:
    print x, y
    x, y = y , x
if x == 4 :
    print x, y
    x, y = y, x

re_comments, comments, after_comments = spam( 
    "testing")

re_comments, comments, after_comments = spam(
    "testing")

new_prefix = u"%s# %s" % ("whitespace_before", "comment_after".lstrip(
    ))

########NEW FILE########
__FILENAME__ = extraneous_whitespace1_out
spam(ham[1], {eggs: 2})
spam(ham[1], {eggs: 2})
spam(ham[1], {eggs: 2})
spam(ham[1], {eggs: 2})
spam(ham[1], {eggs: 2})
spam(ham[1], {eggs: 2})
spam(ham[1], {eggs: 2})

if x == 4:
    print x, y
    x, y = y, x
if x == 4:
    print x, y
    x, y = y, x

re_comments, comments, after_comments = spam(
    "testing")

re_comments, comments, after_comments = spam(
    "testing")

new_prefix = u"%s# %s" % ("whitespace_before", "comment_after".lstrip(
    ))

########NEW FILE########
__FILENAME__ = imports_on_separate_lines1_in
import math, sys, os

from subprocess import Popen, PIPE
from myclas import MyClass
from foo.bar.yourclass import YourClass
import myclass
import foo.bar.yourclass


class the_class():
    import os
    import sys

    def test_func():
        import math

    def other_func():
        import os, sys, math

########NEW FILE########
__FILENAME__ = imports_on_separate_lines1_out
import math
import sys
import os

from subprocess import Popen, PIPE
from myclas import MyClass
from foo.bar.yourclass import YourClass
import myclass
import foo.bar.yourclass


class the_class():
    import os
    import sys

    def test_func():
        import math

    def other_func():
        import os
        import sys
        import math

########NEW FILE########
__FILENAME__ = imports_on_separate_lines2_in
# some comment
import math, sys

# some other comment

import this, that


class the_class():
    # some comment
    import os, sys

########NEW FILE########
__FILENAME__ = imports_on_separate_lines2_out
# some comment
import math
import sys
# some other comment

import this
import that


class the_class():
    # some comment
    import os
    import sys

########NEW FILE########
__FILENAME__ = imports_on_separate_lines3_in
# some comment
""" doc string """
import math, sys

class the_class():
    # some comment
    """ doc string """
    import os, sys


class second_class():
    some_statement
    import os, sys

########NEW FILE########
__FILENAME__ = imports_on_separate_lines3_out
# some comment
""" doc string """
import math
import sys


class the_class():
    # some comment
    """ doc string """
    import os
    import sys


class second_class():
    some_statement
    import os
    import sys

########NEW FILE########
__FILENAME__ = indentation1_in
import sys


def testing_func():
    if (x == 5 or
        x == 7):
        pass

    # Comment A
    if not any(leaf.prefix.count(u'\n')
                for leaf in leaves_after_last_newline):
        pass
    # Comment B
    elif all(leaf.prefix.count(u'\t')
                for leaf in leaves_after_last_newline):
        pass


def tester_method():

  # Comment 1
  # Comment 3
  def inner_method():
      pass

  def inner2():
    # This is a two line
    # comment

    pass


class tester_class():
        u"""
        this is a docstring that
        needs to have its indentation fixed
        """

        y = u"this is a string"

        def inner_class_method():
                x = u"""this is a constant
                that spans over multiples lines"""
                pass

        def innter_class_method2():
        # Comment 2
         pass

########NEW FILE########
__FILENAME__ = indentation1_out
import sys


def testing_func():
    if (x == 5 or
        x == 7):
        pass

    # Comment A
    if not any(leaf.prefix.count(u'\n')
                for leaf in leaves_after_last_newline):
        pass
    # Comment B
    elif all(leaf.prefix.count(u'\t')
                for leaf in leaves_after_last_newline):
        pass


def tester_method():

    # Comment 1
    # Comment 3
    def inner_method():
        pass

    def inner2():
        # This is a two line
        # comment

        pass


class tester_class():
    u"""
        this is a docstring that
        needs to have its indentation fixed
        """

    y = u"this is a string"

    def inner_class_method():
        x = u"""this is a constant
                that spans over multiples lines"""
        pass

    def innter_class_method2():
    # Comment 2
        pass

########NEW FILE########
__FILENAME__ = indentation2_in
try:
      if one & two:
           print "both"
except:
     print "failed"

########NEW FILE########
__FILENAME__ = indentation2_out
try:
    if one & two:
        print "both"
except:
    print "failed"

########NEW FILE########
__FILENAME__ = indentation3_in
#
# multi-level dedent with detent to level 1
#
if a:
  try:
   if one:
      if one & two:
           print "both"
  except:
     print "failed"

########NEW FILE########
__FILENAME__ = indentation3_out
#
# multi-level dedent with detent to level 1
#
if a:
    try:
        if one:
            if one & two:
                print "both"
    except:
        print "failed"

########NEW FILE########
__FILENAME__ = indentation4_in
#


class MyClass:

    # comment
    def my_func(self):
        if self.xxxx:
            self.xxxx()
        self.ping()

    def emptyline(self):
        return

########NEW FILE########
__FILENAME__ = indentation4_out
#


class MyClass:

    # comment
    def my_func(self):
        if self.xxxx:
            self.xxxx()
        self.ping()

    def emptyline(self):
        return

########NEW FILE########
__FILENAME__ = indentation5_in

is_android = True
try:
   import shutil
   # this comment should be intended to `import` and `if`
 # this ono, too
    # this comment should be intended, too
   if xxxx + 1:
      if yyyyy * 2:
         if zzzz / 3:
            aaaaa + 4
      # this should stay at `yyyy` level
   elif kkkk - 5:
      if lll + 6:
         mmmm * 7
         # this should stay at `mmm * 7` level
      nnnn / 8
   elif kkkk + 9:
      if lll - 10:
         mmmm * 11
         # this should stay at `mmm * 11` level
   else:
      # this should stay at `bbbb` level
      bbbb / 12
   # this should go to `eeee` level
   eeee
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = indentation5_out

is_android = True
try:
    import shutil
    # this comment should be intended to `import` and `if`
    # this ono, too
    # this comment should be intended, too
    if xxxx + 1:
        if yyyyy * 2:
            if zzzz / 3:
                aaaaa + 4
        # this should stay at `yyyy` level
    elif kkkk - 5:
        if lll + 6:
            mmmm * 7
            # this should stay at `mmm * 7` level
        nnnn / 8
    elif kkkk + 9:
        if lll - 10:
            mmmm * 11
            # this should stay at `mmm * 11` level
    else:
        # this should stay at `bbbb` level
        bbbb / 12
    # this should go to `eeee` level
    eeee
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = indentation6_in
try:
   import shutil
   if xxxx + 1:
      if yyyyy * 2:
         if zzzz / 3:
            aaaaa + 4
       # this should stay at `yyyy` level + one
   else:
      pass
except:
   end_of_program

########NEW FILE########
__FILENAME__ = indentation6_out
try:
    import shutil
    if xxxx + 1:
        if yyyyy * 2:
            if zzzz / 3:
                aaaaa + 4
         # this should stay at `yyyy` level + one
    else:
        pass
except:
    end_of_program

########NEW FILE########
__FILENAME__ = indentation7_in


class X:
     # We get new broks from schedulers
     # REF: doc/broker-modules.png (2)
     def get_new_broks(self):
            # Get the good links tab for looping..
         links = rechts


########NEW FILE########
__FILENAME__ = indentation7_out


class X:

    # We get new broks from schedulers
    # REF: doc/broker-modules.png (2)
    def get_new_broks(self):
        # Get the good links tab for looping..
        links = rechts

########NEW FILE########
__FILENAME__ = mixed_indents_in
#
# Test mixed intents
#

if True:
  if (x == 5 or x == 7):
        print "ping"

if True:
    if (x == 5 or x == 7):
      print "ping"


def testing_func():
    if True:
      if (x == 5 or x == 7):
            print "ping"

    if True:
        if (x == 5 or x == 7):
          print "ping"


def testing_func2():
  if True:
    if (x == 5 or x == 7):
          print "ping"

  if True:
      if (x == 5 or x == 7):
        print "ping"

########NEW FILE########
__FILENAME__ = mixed_indents_out
#
# Test mixed intents
#

if True:
    if (x == 5 or x == 7):
        print "ping"

if True:
    if (x == 5 or x == 7):
        print "ping"


def testing_func():
    if True:
        if (x == 5 or x == 7):
            print "ping"

    if True:
        if (x == 5 or x == 7):
            print "ping"


def testing_func2():
    if True:
        if (x == 5 or x == 7):
            print "ping"

    if True:
        if (x == 5 or x == 7):
            print "ping"

########NEW FILE########
__FILENAME__ = maximum_line_length1_in
testing = tuplize_comments("this is a short string")  # This is an inline comment that goes over 79 chars
testing = tuplize_comments("this is a longer string that breaks the 79 char limit")  # This is an inline comment that goes over 79 chars

LSTRIP_TOKENS = ["foobar1", "foobar1", "foobar1", "foobar1", "foobar1", "foo23", "foobar1", "foobar1"]

if ("foobar" == "foobar" or "foobar" == "foobar" or "foobar" == "foobar" or "foobar2" == "foobar"
    or "foobar" == "foobar" or "foobar" == "foobar" or "foobar" == "foobar" or "foobar3" == "foobar"):
    pass
new_prefix = '\n'.join([u"%s%s" % ("new_comment_indent", line.lstrip()) if line else u'' for line in "new_prefix".split('\n')]).rstrip(u' ') + "another long string"
from .utils import get_whitespace_before_definition, has_parent, tuplize_comments
before_comments, comments, after_comments_and_this_string_goes_on = tuplize_comments(u"asjdfsjf js ffsadasdfsf")

# Comment 1
new_prefix = ('\n'.join([u"%s%s" % (new_comment_indent, line.lstrip()) if line else u'' for  # A Comment
    line in new_prefix.split('\n')]).rstrip(u' '))


class tester:
    u"""this is testing the maximum length of a docstring and it is very long to ensure that the test will work well"""

    # This is a multiple line comment in front of a method that is defined inside of a class
    # and this is the second line
    def testering(self):
        print u"testering"
    
    # this is another testerig comment that makes sure that we are able to test the fixer properly.
    def tester2():
        u'''This is a long docstring that is inside of a function which is inside of a class'''
        new_comment_indent = u''
        new_prefix = u''
        # Split the lines of comment and prepend them with the new indent value
        if True:
            new_prefix = '\n'.join([u"%s%s" % (new_comment_indent, line.lstrip()) if line else u'' for line in new_prefix.split('\n')]).rstrip(u' ')
        # Allow unary operators: -123, -x, +1.
        if node.value in UNARY_OPERATORS and node.parent.type == symbols.factor:
            pass
        comment_start = 2
        comments = u''
        prefix = u''
        return prefix[:comments_start].strip(u' '), comments, prefix[comments_start + len(comments):]


# This is a tester comment that ensures we are able to fix top-level comments to not be too long.
def tester6():
    u'this is a single quoted docstring. I don\'t like them, but some people still use them'

    tester9 = u"all lines over 80 chars"
    # If someone uses string concat like this, I'm pretty sure the interpreter punches them in the face, but we should fix it anyway
    print "this is going to be" + "test that ensures that" + tester9 + "will be fixed appropriately"
    print "%s%s" % (tester9, "and another string that will make the total length go over 80s")

the_fixering = "testing"
that_other_thing_that_makes_this_over_eighty_chars_total = "testing2"
testering = the_fixering + that_other_thing_that_makes_this_over_eighty_chars_total


def tuplize_comments(prefix):
    prefix = "foo"
    if prefix.count("#"):
        pass
    else:
        if prefix.count(u'\n'):
            comments = prefix.rsplit(u'\n')[1]  # If no comments, there are no comments except the trailing spaces before the current line
        else:
            comments = prefix
    comments_start = prefix.index(comments)

testing = tuplize_comments("this one string" + "another string that makes this line too long")


def tester4():
    # This is a docstring that starts with a '#' and is greater than the max chars

    tester_object.test_a_really_long_method().chain_it_with_another_super_long_method_name()


def tester5():
    if (tester1 == tester2 and tester3 == tester4 and tester5 == tester6 and tester7 == tester8):
        print "good testing"


def tester_func(param1=u'param_value1', param2=u'param_value2', param3=u'param_value3', param4=u'param_value4'):
    print "good testing"

tester_func(param1=u'param_value1', param2=u'param_value2', param3=u'param_value3', param4=u'param_value4')


def testing_func():
    if (node.type == symbols.funcdef and node.parent.type != symbols.decorated
        or node.type == symbols.classdef or node.type == symbols.decorated or node.type == symbols.simple_stmt):
        return node.type, node.type2, node.type3, node.type4, node.type5, node.type6

########NEW FILE########
__FILENAME__ = maximum_line_length1_out
testing = tuplize_comments("this is a short string")
# This is an inline comment that goes over 79 chars
testing = tuplize_comments(
    "this is a longer string that breaks the 79 char limit")
# This is an inline comment that goes over 79 chars

LSTRIP_TOKENS = ["foobar1", "foobar1", "foobar1", "foobar1", "foobar1",
    "foo23", "foobar1", "foobar1"]

if ("foobar" == "foobar" or "foobar" == "foobar" or "foobar" == "foobar" or
    "foobar2" == "foobar" or "foobar" == "foobar" or "foobar" == "foobar" or
    "foobar" == "foobar" or "foobar3" == "foobar"):
    pass
new_prefix = ('\n'.join([u"%s%s" % ("new_comment_indent", line.lstrip()) if
    line else u'' for line in "new_prefix".split('\n')]).rstrip(u' ') +
    "another long string")
from .utils import (get_whitespace_before_definition, has_parent,
    tuplize_comments)
before_comments, comments, after_comments_and_this_string_goes_on = (
    tuplize_comments(u"asjdfsjf js ffsadasdfsf"))

# Comment 1
new_prefix = ('\n'.join([u"%s%s" % (new_comment_indent, line.lstrip()) if line
    else u'' for line in new_prefix.split('\n')]).rstrip(u' '))
    # A Comment


class tester:
    u"""this is testing the maximum length of a docstring and it is very long
        to ensure that the test will work well"""

    # This is a multiple line comment in front of a method that is defined
    # inside of a class and this is the second line
    def testering(self):
        print u"testering"

    # this is another testerig comment that makes sure that we are able to test
    # the fixer properly.
    def tester2():
        u'''This is a long docstring that is inside of a function which is
            inside of a class'''
        new_comment_indent = u''
        new_prefix = u''
        # Split the lines of comment and prepend them with the new indent value
        if True:
            new_prefix = ('\n'.join([u"%s%s" % (new_comment_indent, line.lstrip
                ()) if line else u'' for line in new_prefix.split('\n')]).
                rstrip(u' '))
        # Allow unary operators: -123, -x, +1.
        if (node.value in UNARY_OPERATORS and node.parent.type == symbols.
            factor):
            pass
        comment_start = 2
        comments = u''
        prefix = u''
        return prefix[:comments_start].strip(u' '), comments, prefix[
            comments_start + len(comments):]


# This is a tester comment that ensures we are able to fix top-level comments
# to not be too long.
def tester6():
    (u'this is a single quoted docstring. I don\'t like them, but some people'
        u'still use them')

    tester9 = u"all lines over 80 chars"
    # If someone uses string concat like this, I'm pretty sure the interpreter
    # punches them in the face, but we should fix it anyway
    print("this is going to be" + "test that ensures that" + tester9 +
        "will be fixed appropriately")
    print "%s%s" % (tester9,
        "and another string that will make the total length go over 80s")

the_fixering = "testing"
that_other_thing_that_makes_this_over_eighty_chars_total = "testing2"
testering = (the_fixering +
    that_other_thing_that_makes_this_over_eighty_chars_total)


def tuplize_comments(prefix):
    prefix = "foo"
    if prefix.count("#"):
        pass
    else:
        if prefix.count(u'\n'):
            comments = prefix.rsplit(u'\n')[1]
            # If no comments, there are no comments except the trailing spaces
            # before the current line
        else:
            comments = prefix
    comments_start = prefix.index(comments)

testing = tuplize_comments("this one string" +
    "another string that makes this line too long")


def tester4():
    # This is a docstring that starts with a '#' and is greater than the max
    # chars

    (tester_object.test_a_really_long_method().
        chain_it_with_another_super_long_method_name())


def tester5():
    if (tester1 == tester2 and tester3 == tester4 and tester5 == tester6 and
        tester7 == tester8):
        print "good testing"


def tester_func(param1=u'param_value1', param2=u'param_value2',
    param3=u'param_value3', param4=u'param_value4'):
    print "good testing"

tester_func(param1=u'param_value1', param2=u'param_value2',
    param3=u'param_value3', param4=u'param_value4')


def testing_func():
    if (node.type == symbols.funcdef and node.parent.type != symbols.decorated
        or node.type == symbols.classdef or node.type == symbols.decorated or
        node.type == symbols.simple_stmt):
        return (node.type, node.type2, node.type3, node.type4, node.type5, node
            .type6)

########NEW FILE########
__FILENAME__ = maximum_line_length2_in
class Command(LoadDataCommand):

    option_list = LoadDataCommand.option_list + (
        make_option("-d", "--no-signals", dest="use_signals", default=True, 
            help='Disconnects all signals during import', action="store_false"),
    )

########NEW FILE########
__FILENAME__ = maximum_line_length2_out
class Command(LoadDataCommand):

    option_list = LoadDataCommand.option_list + (make_option("-d",
        "--no-signals", dest="use_signals", default=True,
        help='Disconnects all signals during import', action="store_false"),)

########NEW FILE########
__FILENAME__ = maximum_line_length3_in
def tester():
    foo = 1 + 2
    if not foo:
        logger.error(u"This is a long logger message that goes over the max length: %s", foo)

########NEW FILE########
__FILENAME__ = maximum_line_length3_out
def tester():
    foo = 1 + 2
    if not foo:
        logger.error(
            u"This is a long logger message that goes over the max length: %s",
            foo)

########NEW FILE########
__FILENAME__ = maximum_line_length4_in
class RequestForm(forms.ModelForm):
    company_url = forms.URLField(max_length=60, required=False, label="Company URL", widget=TextInput(attrs={'style': "width: %s;" % text_input_width}),)
    usage = forms.CharField(max_length=500, required=True, label="How are you planning to use this API? * \n(e.g. mobile app, local directory, etc)", widget=forms.Textarea(attrs={'class': 'forminput', 'style': "height: 100px"}),)
    category = models.ForeignKey('foo.bar', blank=False, null=True, help_text='You must select a category. If none is appropriate, select Other.')

########NEW FILE########
__FILENAME__ = maximum_line_length4_out
class RequestForm(forms.ModelForm):
    company_url = forms.URLField(max_length=60, required=False,
        label="Company URL", widget=TextInput(attrs={'style': "width: %s;" %
        text_input_width}), )
    usage = forms.CharField(max_length=500, required=True,
        label="How are you planning to use this API? * \n(e.g. mobile app, local directory, etc)",
        widget=forms.Textarea(attrs={'class': 'forminput', 'style':
        "height: 100px"}), )
    category = models.ForeignKey('foo.bar', blank=False, null=True,
        help_text='You must select a category. If none is appropriate, select Other.'
        )

########NEW FILE########
__FILENAME__ = maximum_line_length5_in
foo = 'bar'
                                                                                          
for x in foo:
    print(x)

########NEW FILE########
__FILENAME__ = maximum_line_length5_out
foo = 'bar'

for x in foo:
    print(x)

########NEW FILE########
__FILENAME__ = missing_newline1_in
class testing():
    def tester():
        pass
########NEW FILE########
__FILENAME__ = missing_newline1_out
class testing():
    def tester():
        pass

########NEW FILE########
__FILENAME__ = missing_newline2_in

from foo import bar

a_smallish_int = 5

########NEW FILE########
__FILENAME__ = missing_newline2_out

from foo import bar

a_smallish_int = 5

########NEW FILE########
__FILENAME__ = missing_newline3_in

from foo import bar

a_smallish_int = 5
########NEW FILE########
__FILENAME__ = missing_newline3_out

from foo import bar

a_smallish_int = 5

########NEW FILE########
__FILENAME__ = missing_newline4_in
import sys

import foo as bar


class testing():

    foobar = []

    def tester():
        pass


def standalone_func(arg):
    def inner_func():
        print "Some stuff in here"
########NEW FILE########
__FILENAME__ = missing_newline4_out
import sys

import foo as bar


class testing():

    foobar = []

    def tester():
        pass


def standalone_func(arg):
    def inner_func():
        print "Some stuff in here"

########NEW FILE########
__FILENAME__ = missing_whitespace1_in
BINARY_OPERATORS = frozenset(['**=', '*=', '+=', '-=', '!=', '<>',
    '%=', '^=', '&=', '|='])

a = range(10)
b = range(5)
foo = [a, b]
bar = (3,)
bar = (3, 1,)
foo = [1,2,]
foo = [1, 3]

foobar = a[1:4]
foobar = a[:4]
foobar = a[1:]
foobar = a[1:4:2]

foobar = ['a','b']
foobar = foo(bar,baz)


def tester_func():
    if node_to_split.type in [symbols.or_test, symbols.and_test, symbols.
        not_test, symbols.test, symbols.arith_expr, symbols.comparison]:
        pass

########NEW FILE########
__FILENAME__ = missing_whitespace1_out
BINARY_OPERATORS = frozenset(['**=', '*=', '+=', '-=', '!=', '<>',
    '%=', '^=', '&=', '|='])

a = range(10)
b = range(5)
foo = [a, b]
bar = (3, )
bar = (3, 1, )
foo = [1, 2, ]
foo = [1, 3]

foobar = a[1:4]
foobar = a[:4]
foobar = a[1:]
foobar = a[1:4:2]

foobar = ['a', 'b']
foobar = foo(bar, baz)


def tester_func():
    if node_to_split.type in [symbols.or_test, symbols.and_test, symbols.
        not_test, symbols.test, symbols.arith_expr, symbols.comparison]:
        pass

########NEW FILE########
__FILENAME__ = missing_whitespace2_in

# This file will not be changed, ut pep8yif must not crash :-)

def x():
    return item,

after = 1

########NEW FILE########
__FILENAME__ = missing_whitespace2_out

# This file will not be changed, ut pep8yif must not crash :-)

def x():
    return item,

after = 1

########NEW FILE########
__FILENAME__ = tab1_in
import foo


class testing():

	def tester(self):
		return self.blah

	def tester2():
		print "bleh"

########NEW FILE########
__FILENAME__ = tab1_out
import foo


class testing():

    def tester(self):
        return self.blah

    def tester2():
        print "bleh"

########NEW FILE########
__FILENAME__ = tabs2_in
try:
	if one and two:
		print "bleh"
except:
	print "fail"

########NEW FILE########
__FILENAME__ = tabs2_out
try:
    if one and two:
        print "bleh"
except:
    print "fail"

########NEW FILE########
__FILENAME__ = trailing_blank_lines1_in
class tester():
    def func1():
        return

    def func2():
        return


########NEW FILE########
__FILENAME__ = trailing_blank_lines1_out
class tester():
    def func1():
        return

    def func2():
        return

########NEW FILE########
__FILENAME__ = trailing_blank_lines2_in
class tester():
    def func1():
        return

    def func2():
        return

########NEW FILE########
__FILENAME__ = trailing_blank_lines2_out
class tester():
    def func1():
        return

    def func2():
        return

########NEW FILE########
__FILENAME__ = trailing_blank_lines3_in
class tester():
    def func1():
        return

    def func2():
        return
        
   


########NEW FILE########
__FILENAME__ = trailing_blank_lines3_out
class tester():
    def func1():
        return

    def func2():
        return

########NEW FILE########
__FILENAME__ = trailing_blank_lines4_in
def a():
    pass

    # This is commented
    #   out

########NEW FILE########
__FILENAME__ = trailing_blank_lines4_out
def a():
    pass

    # This is commented
    #   out

########NEW FILE########
__FILENAME__ = trailing_whitespace1_in
class tester(object):
    def __init__(self, attr1, attr2): 
        self.attr1 = attr1
        self.attr2 = attr2 
        self.attr3 = ["one string", 
            "another string"]
    
    def __unicode__(self):
        return u"testing unicode response"
    
    def test_method(self):
        return self.attr1 + self.attr2
    
    def test_method2(self, suffix):
        return "%s %s" % (self.attr1, suffix) 
    
    # This is a comment 
    # This is another comment 
    def test_method3(self):
        print("testing this %s", self.attr2)

########NEW FILE########
__FILENAME__ = trailing_whitespace1_out
class tester(object):
    def __init__(self, attr1, attr2):
        self.attr1 = attr1
        self.attr2 = attr2
        self.attr3 = ["one string",
            "another string"]

    def __unicode__(self):
        return u"testing unicode response"

    def test_method(self):
        return self.attr1 + self.attr2

    def test_method2(self, suffix):
        return "%s %s" % (self.attr1, suffix)

    # This is a comment
    # This is another comment
    def test_method3(self):
        print("testing this %s", self.attr2)

########NEW FILE########
__FILENAME__ = trailing_whitespace2_in
class testing():
    def tester():    
        pass

########NEW FILE########
__FILENAME__ = trailing_whitespace2_out
class testing():
    def tester():
        pass

########NEW FILE########
__FILENAME__ = whitespace_around_operator1_in
foo = 23 + 3
foo = 4  + 5
foo = 4 +  5
foo = 4	+ 5
foo = 4 +	5

i = i + 1
submitted += 1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)
foo(bar, key='word', *args, **kwargs)
foo(bar, key = 'word', *args, **kwargs)

x = (3 +
     2)
x = (3
     + 2)
x = 3 +\
    2
x = 3 +      \
    2


def func(foo, bar='tester'):
    return 5


def func(foo, bar = 'tester'):
    return 5

baz(**kwargs)
negative = -1
spam(-1)
alpha[:-i]
if not -5 < x < +5:
    pass
lambda *args, **kw: (args, kw)
lambda *args, ** kw: (args, kw)

i=i+1
submitted +=1
x = x*2 - 1
hypot2 = x*x + y*y
c = (a+b) * (a-b)
c = alpha -4
z = x **y

########NEW FILE########
__FILENAME__ = whitespace_around_operator1_out
foo = 23 + 3
foo = 4 + 5
foo = 4 + 5
foo = 4 + 5
foo = 4 + 5

i = i + 1
submitted += 1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)
foo(bar, key='word', *args, **kwargs)
foo(bar, key='word', *args, **kwargs)

x = (3 +
     2)
x = (3
     + 2)
x = 3 + \
    2
x = 3 + \
    2


def func(foo, bar='tester'):
    return 5


def func(foo, bar='tester'):
    return 5

baz(**kwargs)
negative = -1
spam(-1)
alpha[:-i]
if not -5 < x < +5:
    pass
lambda *args, **kw: (args, kw)
lambda *args, **kw: (args, kw)

i = i + 1
submitted += 1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)
c = alpha - 4
z = x ** y

########NEW FILE########
__FILENAME__ = whitespace_before_inline_comment1_in
x = x + 1  # Increment x
x = x + 1    # Increment x
x = x + 1 # Increment x
x = x + 1  #Increment x
x = x + 1  #  Increment x
x = x + 1    #Increment x

some_list = (
    foobar("asdf"), # some comment,
    foobar2(),
)

########NEW FILE########
__FILENAME__ = whitespace_before_inline_comment1_out
x = x + 1  # Increment x
x = x + 1    # Increment x
x = x + 1  # Increment x
x = x + 1  # Increment x
x = x + 1  # Increment x
x = x + 1    # Increment x

some_list = (
    foobar("asdf"),  # some comment,
    foobar2(),
)

########NEW FILE########
__FILENAME__ = whitespace_before_inline_comment2_in
import foo
# a comment

foo.bar()

########NEW FILE########
__FILENAME__ = whitespace_before_inline_comment2_out
import foo
# a comment

foo.bar()

########NEW FILE########
__FILENAME__ = whitespace_before_inline_comment3_in
# comment 1
# comment 2
import baz

baz.bar(
    a='foobar',
    # Comment between args
    b='foobaz',
)

########NEW FILE########
__FILENAME__ = whitespace_before_inline_comment3_out
# comment 1
# comment 2
import baz

baz.bar(
    a='foobar',
    # Comment between args
    b='foobaz',
)

########NEW FILE########
__FILENAME__ = whitespace_before_parameters1_in
foo = spam(1)
bar = spam (1)

dict['key'] = list[index]
dict ['key'] = list[index]
dict['key'] = list [index]

foobar = ['key']
foobar(['key'])

########NEW FILE########
__FILENAME__ = whitespace_before_parameters1_out
foo = spam(1)
bar = spam(1)

dict['key'] = list[index]
dict['key'] = list[index]
dict['key'] = list[index]

foobar = ['key']
foobar(['key'])

########NEW FILE########
__FILENAME__ = test_all_fixes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import partial
import os
from os.path import join
import shutil
from difflib import unified_diff

from lib2to3.main import main

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), '')


def setup():
    pass


def teardown():
    # This finds all of the backup files that we created and replaces
    # the *_in.py files that were created for testing
    potential_backups = []
    for root, dirs, files in os.walk(FIXTURE_PATH):
        for filename in files:
            potential_backups.append(join(root, filename))

    real_backups = [potential_backup for potential_backup in potential_backups
                    if potential_backup.endswith(".bak")]
    for backup in real_backups:
        shutil.move(backup, backup.replace(".bak", ""))


def in_and_out_files_from_directory(directory):
    fixture_files = os.listdir(directory)
    fixture_in_files = [join(directory, fixture_file)
        for fixture_file in fixture_files if fixture_file.endswith("_in.py")]
    all_fixture_files = [(fixture_in, fixture_in.replace("_in.py", "_out.py"))
        for fixture_in in fixture_in_files]
    return all_fixture_files


def test_all_fixtures():
    for root, dirs, files in os.walk(FIXTURE_PATH):
        # Loop recursively through all files. If the files is in a
        # subdirectory, only run the fixer of the subdirectory name, else run
        # all fixers.
        for in_file, out_file in in_and_out_files_from_directory(root):
            fixer_to_run = None

            # This partial business is a hack to make the description
            # attribute actually work.
            # See http://code.google.com/p/python-nose/issues/detail?id=244#c1
            func = partial(check_fixture, in_file, out_file, fixer_to_run)
            func.description = "All fixes"
            if in_file.startswith(FIXTURE_PATH):
                func.description = in_file[len(FIXTURE_PATH):]
            yield (func,)


test_all_fixtures.setup = setup
test_all_fixtures.teardown = teardown


def check_fixture(in_file, out_file, fixer):
    if fixer:
        main("pep8ify.fixes", args=['--no-diffs', '--fix', fixer, '-w', in_file])
    else:
        main("pep8ify.fixes", args=['--no-diffs', '--fix', 'all',
            '--fix', 'maximum_line_length', '-w', in_file])
    in_file_contents = open(in_file, 'r').readlines()
    out_file_contents = open(out_file, 'r').readlines()

    if in_file_contents != out_file_contents:
        text = "in_file doesn't match out_file\n"
        text += ''.join(unified_diff(out_file_contents, in_file_contents,
                                     'expected', 'refactured result'))
        raise AssertionError(text)

########NEW FILE########
