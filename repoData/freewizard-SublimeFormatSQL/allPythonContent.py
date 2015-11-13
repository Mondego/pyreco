__FILENAME__ = FormatSQL
from __future__ import absolute_import
import sublime
import sublime_plugin

try:
    from .sqlparse import format
except ValueError:
    from sqlparse import format


class FormatSqlCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        regions = view.sel()
        # if there are more than 1 region or region one and it's not empty
        if len(regions) > 1 or not regions[0].empty():
            for region in view.sel():
                if not region.empty():
                    s = view.substr(region)
                    s = self._run(s)
                    view.replace(edit, region, s)
        else:  # format all text
            alltextreg = sublime.Region(0, view.size())
            s = view.substr(alltextreg)
            s = self._run(s)
            view.replace(edit, alltextreg, s)

    def _run(self, s):
        settings = self.view.settings()
        #indent_char = " " if settings.get("translate_tabs_to_spaces") else "\t"
        indent_char = " " #TODO indent by TAB (currently not supported in python-sqlparse)
        indent_size = int(settings.get("tab_size")) if indent_char == " " else 1
        s = s.encode("utf-8")
        return format(
            s, keyword_case="upper", reindent=True, indent_width=indent_size
        )

########NEW FILE########
__FILENAME__ = filter
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from ..sql import Statement, Token
from .. import tokens as T


class TokenFilter(object):

    def __init__(self, **options):
        self.options = options

    def process(self, stack, stream):
        """Process token stream."""
        raise NotImplementedError


class StatementFilter(TokenFilter):

    def __init__(self):
        TokenFilter.__init__(self)
        self._in_declare = False
        self._in_dbldollar = False
        self._is_create = False
        self._begin_depth = 0

    def _reset(self):
        self._in_declare = False
        self._in_dbldollar = False
        self._is_create = False
        self._begin_depth = 0

    def _change_splitlevel(self, ttype, value):
        # PostgreSQL
        if (ttype == T.Name.Builtin
            and value.startswith('$') and value.endswith('$')):
            if self._in_dbldollar:
                self._in_dbldollar = False
                return -1
            else:
                self._in_dbldollar = True
                return 1
        elif self._in_dbldollar:
            return 0

        # ANSI
        if ttype not in T.Keyword:
            return 0

        unified = value.upper()

        if unified == 'DECLARE' and self._is_create:
            self._in_declare = True
            return 1

        if unified == 'BEGIN':
            self._begin_depth += 1
            if self._in_declare:  # FIXME(andi): This makes no sense.
                return 0
            return 0

        if unified == 'END':
            # Should this respect a preceeding BEGIN?
            # In CASE ... WHEN ... END this results in a split level -1.
            self._begin_depth = max(0, self._begin_depth - 1)
            return -1

        if ttype is T.Keyword.DDL and unified.startswith('CREATE'):
            self._is_create = True
            return 0

        if (unified in ('IF', 'FOR')
            and self._is_create and self._begin_depth > 0):
            return 1

        # Default
        return 0

    def process(self, stack, stream):
        splitlevel = 0
        stmt = None
        consume_ws = False
        stmt_tokens = []
        for ttype, value in stream:
            # Before appending the token
            if (consume_ws and ttype is not T.Whitespace
                and ttype is not T.Comment.Single):
                consume_ws = False
                stmt.tokens = stmt_tokens
                yield stmt
                self._reset()
                stmt = None
                splitlevel = 0
            if stmt is None:
                stmt = Statement()
                stmt_tokens = []
            splitlevel += self._change_splitlevel(ttype, value)
            # Append the token
            stmt_tokens.append(Token(ttype, value))
            # After appending the token
            if (splitlevel <= 0 and ttype is T.Punctuation
                and value == ';'):
                consume_ws = True
        if stmt is not None:
            stmt.tokens = stmt_tokens
            yield stmt

########NEW FILE########
__FILENAME__ = grouping
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import itertools

from .. import sql
from .. import tokens as T

try:
    next
except NameError:  # Python < 2.6
    next = lambda i: i.next()


def _group_left_right(tlist, ttype, value, cls,
                      check_right=lambda t: True,
                      check_left=lambda t: True,
                      include_semicolon=False):
    [_group_left_right(sgroup, ttype, value, cls, check_right,
                       include_semicolon) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, cls)]
    idx = 0
    token = tlist.token_next_match(idx, ttype, value)
    while token:
        right = tlist.token_next(tlist.token_index(token))
        left = tlist.token_prev(tlist.token_index(token))
        if right is None or not check_right(right):
            token = tlist.token_next_match(tlist.token_index(token) + 1,
                                           ttype, value)
        elif left is None or not check_right(left):
            token = tlist.token_next_match(tlist.token_index(token) + 1,
                                           ttype, value)
        else:
            if include_semicolon:
                sright = tlist.token_next_match(tlist.token_index(right),
                                                T.Punctuation, ';')
                if sright is not None:
                    # only overwrite "right" if a semicolon is actually
                    # present.
                    right = sright
            tokens = tlist.tokens_between(left, right)[1:]
            if not isinstance(left, cls):
                new = cls([left])
                new_idx = tlist.token_index(left)
                tlist.tokens.remove(left)
                tlist.tokens.insert(new_idx, new)
                left = new
            left.tokens.extend(tokens)
            for t in tokens:
                tlist.tokens.remove(t)
            token = tlist.token_next_match(tlist.token_index(left) + 1,
                                           ttype, value)


def _group_matching(tlist, start_ttype, start_value, end_ttype, end_value,
                    cls, include_semicolon=False, recurse=False):
    def _find_matching(i, tl, stt, sva, ett, eva):
        depth = 1
        for t in tl.tokens[i:]:
            if t.match(stt, sva):
                depth += 1
            elif t.match(ett, eva):
                depth -= 1
                if depth == 1:
                    return t
        return None
    [_group_matching(sgroup, start_ttype, start_value, end_ttype, end_value,
                     cls, include_semicolon) for sgroup in tlist.get_sublists()
     if recurse]
    if isinstance(tlist, cls):
        idx = 1
    else:
        idx = 0
    token = tlist.token_next_match(idx, start_ttype, start_value)
    while token:
        tidx = tlist.token_index(token)
        end = _find_matching(tidx, tlist, start_ttype, start_value,
                             end_ttype, end_value)
        if end is None:
            idx = tidx + 1
        else:
            if include_semicolon:
                next_ = tlist.token_next(tlist.token_index(end))
                if next_ and next_.match(T.Punctuation, ';'):
                    end = next_
            group = tlist.group_tokens(cls, tlist.tokens_between(token, end))
            _group_matching(group, start_ttype, start_value,
                            end_ttype, end_value, cls, include_semicolon)
            idx = tlist.token_index(group) + 1
        token = tlist.token_next_match(idx, start_ttype, start_value)


def group_if(tlist):
    _group_matching(tlist, T.Keyword, 'IF', T.Keyword, 'END IF', sql.If, True)


def group_for(tlist):
    _group_matching(tlist, T.Keyword, 'FOR', T.Keyword, 'END LOOP',
                    sql.For, True)


def group_as(tlist):

    def _right_valid(token):
        # Currently limited to DML/DDL. Maybe additional more non SQL reserved
        # keywords should appear here (see issue8).
        return not token.ttype in (T.DML, T.DDL)
    _group_left_right(tlist, T.Keyword, 'AS', sql.Identifier,
                      check_right=_right_valid)


def group_assignment(tlist):
    _group_left_right(tlist, T.Assignment, ':=', sql.Assignment,
                      include_semicolon=True)


def group_comparison(tlist):

    def _parts_valid(token):
        return (token.ttype in (T.String.Symbol, T.Name, T.Number,
                                T.Number.Integer, T.Literal,
                                T.Literal.Number.Integer)
                or isinstance(token, (sql.Identifier,)))
    _group_left_right(tlist, T.Operator.Comparison, None, sql.Comparison,
                      check_left=_parts_valid, check_right=_parts_valid)


def group_case(tlist):
    _group_matching(tlist, T.Keyword, 'CASE', T.Keyword, 'END', sql.Case,
                    include_semicolon=True, recurse=True)


def group_identifier(tlist):
    def _consume_cycle(tl, i):
        x = itertools.cycle((
            lambda y: (y.match(T.Punctuation, '.')
                       or y.ttype is T.Operator),
            lambda y: (y.ttype in (T.String.Symbol,
                                   T.Name,
                                   T.Wildcard,
                                   T.Literal.Number.Integer))))
        for t in tl.tokens[i:]:
            if next(x)(t):
                yield t
            else:
                raise StopIteration

    def _next_token(tl, i):
        # chooses the next token. if two tokens are found then the
        # first is returned.
        t1 = tl.token_next_by_type(i, (T.String.Symbol, T.Name))
        t2 = tl.token_next_by_instance(i, sql.Function)
        if t1 and t2:
            i1 = tl.token_index(t1)
            i2 = tl.token_index(t2)
            if i1 > i2:
                return t2
            else:
                return t1
        elif t1:
            return t1
        else:
            return t2

    # bottom up approach: group subgroups first
    [group_identifier(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Identifier)]

    # real processing
    idx = 0
    token = _next_token(tlist, idx)
    while token:
        identifier_tokens = [token] + list(
            _consume_cycle(tlist,
                           tlist.token_index(token) + 1))
        if not (len(identifier_tokens) == 1
                and isinstance(identifier_tokens[0], sql.Function)):
            group = tlist.group_tokens(sql.Identifier, identifier_tokens)
            idx = tlist.token_index(group) + 1
        else:
            idx += 1
        token = _next_token(tlist, idx)


def group_identifier_list(tlist):
    [group_identifier_list(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.IdentifierList)]
    idx = 0
    # Allowed list items
    fend1_funcs = [lambda t: isinstance(t, (sql.Identifier, sql.Function,
                                            sql.Case)),
                   lambda t: t.is_whitespace(),
                   lambda t: t.ttype == T.Name,
                   lambda t: t.ttype == T.Wildcard,
                   lambda t: t.match(T.Keyword, 'null'),
                   lambda t: t.ttype == T.Number.Integer,
                   lambda t: t.ttype == T.String.Single,
                   lambda t: isinstance(t, sql.Comparison),
                   ]
    tcomma = tlist.token_next_match(idx, T.Punctuation, ',')
    start = None
    while tcomma is not None:
        before = tlist.token_prev(tcomma)
        after = tlist.token_next(tcomma)
        # Check if the tokens around tcomma belong to a list
        bpassed = apassed = False
        for func in fend1_funcs:
            if before is not None and func(before):
                bpassed = True
            if after is not None and func(after):
                apassed = True
        if not bpassed or not apassed:
            # Something's wrong here, skip ahead to next ","
            start = None
            tcomma = tlist.token_next_match(tlist.token_index(tcomma) + 1,
                                            T.Punctuation, ',')
        else:
            if start is None:
                start = before
            next_ = tlist.token_next(after)
            if next_ is None or not next_.match(T.Punctuation, ','):
                # Reached the end of the list
                tokens = tlist.tokens_between(start, after)
                group = tlist.group_tokens(sql.IdentifierList, tokens)
                start = None
                tcomma = tlist.token_next_match(tlist.token_index(group) + 1,
                                                T.Punctuation, ',')
            else:
                tcomma = next_


def group_parenthesis(tlist):
    _group_matching(tlist, T.Punctuation, '(', T.Punctuation, ')',
                    sql.Parenthesis)


def group_comments(tlist):
    [group_comments(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Comment)]
    idx = 0
    token = tlist.token_next_by_type(idx, T.Comment)
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_not_matching(tidx + 1,
                                       [lambda t: t.ttype in T.Comment,
                                        lambda t: t.is_whitespace()])
        if end is None:
            idx = tidx + 1
        else:
            eidx = tlist.token_index(end)
            grp_tokens = tlist.tokens_between(token,
                                              tlist.token_prev(eidx, False))
            group = tlist.group_tokens(sql.Comment, grp_tokens)
            idx = tlist.token_index(group)
        token = tlist.token_next_by_type(idx, T.Comment)


def group_where(tlist):
    [group_where(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Where)]
    idx = 0
    token = tlist.token_next_match(idx, T.Keyword, 'WHERE')
    stopwords = ('ORDER', 'GROUP', 'LIMIT', 'UNION')
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_next_match(tidx + 1, T.Keyword, stopwords)
        if end is None:
            end = tlist._groupable_tokens[-1]
        else:
            end = tlist.tokens[tlist.token_index(end) - 1]
        group = tlist.group_tokens(sql.Where,
                                   tlist.tokens_between(token, end),
                                   ignore_ws=True)
        idx = tlist.token_index(group)
        token = tlist.token_next_match(idx, T.Keyword, 'WHERE')


def group_aliased(tlist):
    clss = (sql.Identifier, sql.Function, sql.Case)
    [group_aliased(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, clss)]
    idx = 0
    token = tlist.token_next_by_instance(idx, clss)
    while token:
        next_ = tlist.token_next(tlist.token_index(token))
        if next_ is not None and isinstance(next_, clss):
            grp = tlist.tokens_between(token, next_)[1:]
            token.tokens.extend(grp)
            for t in grp:
                tlist.tokens.remove(t)
        idx = tlist.token_index(token) + 1
        token = tlist.token_next_by_instance(idx, clss)


def group_typecasts(tlist):
    _group_left_right(tlist, T.Punctuation, '::', sql.Identifier)


def group_functions(tlist):
    [group_functions(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Function)]
    idx = 0
    token = tlist.token_next_by_type(idx, T.Name)
    while token:
        next_ = tlist.token_next(token)
        if not isinstance(next_, sql.Parenthesis):
            idx = tlist.token_index(token) + 1
        else:
            func = tlist.group_tokens(sql.Function,
                                      tlist.tokens_between(token, next_))
            idx = tlist.token_index(func) + 1
        token = tlist.token_next_by_type(idx, T.Name)


def group(tlist):
    for func in [group_parenthesis,
                 group_functions,
                 group_comments,
                 group_where,
                 group_case,
                 group_identifier,
                 group_typecasts,
                 group_as,
                 group_aliased,
                 group_assignment,
                 group_comparison,
                 group_identifier_list,
                 group_if,
                 group_for]:
        func(tlist)

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import re

from os.path import abspath, join

from . import sql
from . import tokens as T
from .engine import FilterStack
from .tokens import (
    Comment, Keyword, Name,
    Punctuation, String, Whitespace,
)


class Filter(object):

    def process(self, *args):
        raise NotImplementedError


class TokenFilter(Filter):

    def process(self, stack, stream):
        raise NotImplementedError


# --------------------------
# token process

class _CaseFilter(TokenFilter):

    ttype = None

    def __init__(self, case=None):
        if case is None:
            case = 'upper'
        assert case in ['lower', 'upper', 'capitalize']
        self.convert = getattr(str, case)

    def process(self, stack, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = (T.Name, T.String.Symbol)

    def process(self, stack, stream):
        for ttype, value in stream:
            if ttype in self.ttype and not value.strip()[0] == '"':
                value = self.convert(value)
            yield ttype, value


class GetComments(Filter):
    """Get the comments from a stack"""
    def process(self, stack, stream):
        for token_type, value in stream:
            if token_type in Comment:
                yield token_type, value


class StripComments(Filter):
    """Strip the comments from a stack"""
    def process(self, stack, stream):
        for token_type, value in stream:
            if token_type not in Comment:
                yield token_type, value


class IncludeStatement(Filter):
    """Filter that enable a INCLUDE statement"""

    def __init__(self, dirpath=".", maxRecursive=10):
        self.dirpath = abspath(dirpath)
        self.maxRecursive = maxRecursive

        self.detected = False

    def process(self, stack, stream):
        # Run over all tokens in the stream
        for token_type, value in stream:
            # INCLUDE statement found, set detected mode
            if token_type in Name and value.upper() == 'INCLUDE':
                self.detected = True
                continue

            # INCLUDE statement was found, parse it
            elif self.detected:
                # Omit whitespaces
                if token_type in Whitespace:
                    pass

                # Get path of file to include
                path = None

                if token_type in String.Symbol:
#                if token_type in tokens.String.Symbol:
                    path = join(self.dirpath, value[1:-1])

                # Include file if path was found
                if path:
                    try:
                        f = open(path)
                        raw_sql = f.read()
                        f.close()
                    except IOError as err:
                        yield Comment, u'-- IOError: %s\n' % err

                    else:
                        # Create new FilterStack to parse readed file
                        # and add all its tokens to the main stack recursively
                        # [ToDo] Add maximum recursive iteration value
                        stack = FilterStack()
                        stack.preprocess.append(IncludeStatement(self.dirpath))

                        for tv in stack.run(raw_sql):
                            yield tv

                    # Set normal mode
                    self.detected = False

                # Don't include any token while in detected mode
                continue

            # Normal token
            yield token_type, value


# ----------------------
# statement process

class StripCommentsFilter(Filter):

    def _get_next_comment(self, tlist):
        # TODO(andi) Comment types should be unified, see related issue38
        token = tlist.token_next_by_instance(0, sql.Comment)
        if token is None:
            token = tlist.token_next_by_type(0, T.Comment)
        return token

    def _process(self, tlist):
        token = self._get_next_comment(tlist)
        while token:
            tidx = tlist.token_index(token)
            prev = tlist.token_prev(tidx, False)
            next_ = tlist.token_next(tidx, False)
            # Replace by whitespace if prev and next exist and if they're not
            # whitespaces. This doesn't apply if prev or next is a paranthesis.
            if (prev is not None and next_ is not None
                and not prev.is_whitespace() and not next_.is_whitespace()
                and not (prev.match(T.Punctuation, '(')
                         or next_.match(T.Punctuation, ')'))):
                tlist.tokens[tidx] = sql.Token(T.Whitespace, ' ')
            else:
                tlist.tokens.pop(tidx)
            token = self._get_next_comment(tlist)

    def process(self, stack, stmt):
        [self.process(stack, sgroup) for sgroup in stmt.get_sublists()]
        self._process(stmt)


class StripWhitespaceFilter(Filter):

    def _stripws(self, tlist):
        func_name = '_stripws_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._stripws_default)
        func(tlist)

    def _stripws_default(self, tlist):
        last_was_ws = False
        for token in tlist.tokens:
            if token.is_whitespace():
                if last_was_ws:
                    token.value = ''
                else:
                    token.value = ' '
            last_was_ws = token.is_whitespace()

    def _stripws_parenthesis(self, tlist):
        if tlist.tokens[1].is_whitespace():
            tlist.tokens.pop(1)
        if tlist.tokens[-2].is_whitespace():
            tlist.tokens.pop(-2)
        self._stripws_default(tlist)

    def process(self, stack, stmt):
        [self.process(stack, sgroup) for sgroup in stmt.get_sublists()]
        self._stripws(stmt)
        if stmt.tokens[-1].is_whitespace():
            stmt.tokens.pop(-1)


class ReindentFilter(Filter):

    def __init__(self, width=2, char=' ', line_width=None):
        self.width = width
        self.char = char
        self.indent = 0
        self.offset = 0
        self.line_width = line_width
        self._curr_stmt = None
        self._last_stmt = None

    def _get_offset(self, token):
        all_ = list(self._curr_stmt.flatten())
        idx = all_.index(token)
        raw = ''.join(str(x) for x in all_[:idx + 1])
        line = raw.splitlines()[-1]
        # Now take current offset into account and return relative offset.
        full_offset = len(line) - len(self.char * (self.width * self.indent))
        return full_offset - self.offset

    def nl(self):
        # TODO: newline character should be configurable
        ws = '\n' + (self.char * ((self.indent * self.width) + self.offset))
        return sql.Token(T.Whitespace, ws)

    def _split_kwds(self, tlist):
        split_words = ('FROM', 'JOIN$', 'AND', 'OR',
                       'GROUP', 'ORDER', 'UNION', 'VALUES',
                       'SET', 'BETWEEN')

        def _next_token(i):
            t = tlist.token_next_match(i, T.Keyword, split_words,
                                       regex=True)
            if t and t.value.upper() == 'BETWEEN':
                t = _next_token(tlist.token_index(t) + 1)
                if t and t.value.upper() == 'AND':
                    t = _next_token(tlist.token_index(t) + 1)
            return t

        idx = 0
        token = _next_token(idx)
        while token:
            prev = tlist.token_prev(tlist.token_index(token), False)
            offset = 1
            if prev and prev.is_whitespace():
                tlist.tokens.pop(tlist.token_index(prev))
                offset += 1
            if (prev
                and isinstance(prev, sql.Comment)
                and (str(prev).endswith('\n')
                     or str(prev).endswith('\r'))):
                nl = tlist.token_next(token)
            else:
                nl = self.nl()
                tlist.insert_before(token, nl)
            token = _next_token(tlist.token_index(nl) + offset)

    def _split_statements(self, tlist):
        idx = 0
        token = tlist.token_next_by_type(idx, (T.Keyword.DDL, T.Keyword.DML))
        while token:
            prev = tlist.token_prev(tlist.token_index(token), False)
            if prev and prev.is_whitespace():
                tlist.tokens.pop(tlist.token_index(prev))
            # only break if it's not the first token
            if prev:
                nl = self.nl()
                tlist.insert_before(token, nl)
            token = tlist.token_next_by_type(tlist.token_index(token) + 1,
                                             (T.Keyword.DDL, T.Keyword.DML))

    def _process(self, tlist):
        func_name = '_process_%s' % tlist.__class__.__name__.lower()
        func = getattr(self, func_name, self._process_default)
        func(tlist)

    def _process_where(self, tlist):
        token = tlist.token_next_match(0, T.Keyword, 'WHERE')
        tlist.insert_before(token, self.nl())
        self.indent += 1
        self._process_default(tlist)
        self.indent -= 1

    def _process_parenthesis(self, tlist):
        first = tlist.token_next(0)
        indented = False
        if first and first.ttype in (T.Keyword.DML, T.Keyword.DDL):
            self.indent += 1
            tlist.tokens.insert(0, self.nl())
            indented = True
        num_offset = self._get_offset(tlist.token_next_match(0,
                                                        T.Punctuation, '('))
        self.offset += num_offset
        self._process_default(tlist, stmts=not indented)
        if indented:
            self.indent -= 1
        self.offset -= num_offset

    def _process_identifierlist(self, tlist):
        identifiers = tlist.get_identifiers()
        if len(identifiers) > 1 and not tlist.within(sql.Function):
            first = list(identifiers[0].flatten())[0]
            num_offset = self._get_offset(first) - len(first.value)
            self.offset += num_offset
            for token in identifiers[1:]:
                tlist.insert_before(token, self.nl())
            self.offset -= num_offset
        self._process_default(tlist)

    def _process_case(self, tlist):
        is_first = True
        num_offset = None
        case = tlist.tokens[0]
        outer_offset = self._get_offset(case) - len(case.value)
        self.offset += outer_offset
        for cond, value in tlist.get_cases():
            if is_first:
                tcond = list(cond[0].flatten())[0]
                is_first = False
                num_offset = self._get_offset(tcond) - len(tcond.value)
                self.offset += num_offset
                continue
            if cond is None:
                token = value[0]
            else:
                token = cond[0]
            tlist.insert_before(token, self.nl())
        # Line breaks on group level are done. Now let's add an offset of
        # 5 (=length of "when", "then", "else") and process subgroups.
        self.offset += 5
        self._process_default(tlist)
        self.offset -= 5
        if num_offset is not None:
            self.offset -= num_offset
        end = tlist.token_next_match(0, T.Keyword, 'END')
        tlist.insert_before(end, self.nl())
        self.offset -= outer_offset

    def _process_default(self, tlist, stmts=True, kwds=True):
        if stmts:
            self._split_statements(tlist)
        if kwds:
            self._split_kwds(tlist)
        [self._process(sgroup) for sgroup in tlist.get_sublists()]

    def process(self, stack, stmt):
        if isinstance(stmt, sql.Statement):
            self._curr_stmt = stmt
        self._process(stmt)
        if isinstance(stmt, sql.Statement):
            if self._last_stmt is not None:
                if self._last_stmt.to_unicode().endswith('\n'):
                    nl = '\n'
                else:
                    nl = '\n\n'
                stmt.tokens.insert(0,
                    sql.Token(T.Whitespace, nl))
            if self._last_stmt != stmt:
                self._last_stmt = stmt


# FIXME: Doesn't work ;)
class RightMarginFilter(Filter):

    keep_together = (
#        sql.TypeCast, sql.Identifier, sql.Alias,
    )

    def __init__(self, width=79):
        self.width = width
        self.line = ''

    def _process(self, stack, group, stream):
        for token in stream:
            if token.is_whitespace() and '\n' in token.value:
                if token.value.endswith('\n'):
                    self.line = ''
                else:
                    self.line = token.value.splitlines()[-1]
            elif (token.is_group()
                  and not token.__class__ in self.keep_together):
                token.tokens = self._process(stack, token, token.tokens)
            else:
                val = token.to_unicode()
                if len(self.line) + len(val) > self.width:
                    match = re.search('^ +', self.line)
                    if match is not None:
                        indent = match.group()
                    else:
                        indent = ''
                    yield sql.Token(T.Whitespace, '\n%s' % indent)
                    self.line = indent
                self.line += val
            yield token

    def process(self, stack, group):
        return
        group.tokens = self._process(stack, group, group.tokens)


class ColumnsSelect(Filter):
    """Get the columns names of a SELECT query"""
    def process(self, stack, stream):
        mode = 0
        oldValue = ""
        parenthesis = 0

        for token_type, value in stream:
            # Ignore comments
            if token_type in Comment:
                continue

            # We have not detected a SELECT statement
            if mode == 0:
                if token_type in Keyword and value == 'SELECT':
                    mode = 1

            # We have detected a SELECT statement
            elif mode == 1:
                if value == 'FROM':
                    if oldValue:
                        yield oldValue

                    mode = 3    # Columns have been checked

                elif value == 'AS':
                    oldValue = ""
                    mode = 2

                elif (token_type == Punctuation
                      and value == ',' and not parenthesis):
                    if oldValue:
                        yield oldValue
                    oldValue = ""

                elif token_type not in Whitespace:
                    if value == '(':
                        parenthesis += 1
                    elif value == ')':
                        parenthesis -= 1

                    oldValue += value

            # We are processing an AS keyword
            elif mode == 2:
                # We check also for Keywords because a bug in SQLParse
                if token_type == Name or token_type == Keyword:
                    yield value
                    mode = 1


# ---------------------------
# postprocess

class SerializerUnicode(Filter):

    def process(self, stack, stmt):
        raw = stmt.to_unicode()
        add_nl = raw.endswith('\n')
        res = '\n'.join(line.rstrip() for line in raw.splitlines())
        if add_nl:
            res += '\n'
        return res

def Tokens2Unicode(stream):
    result = ""

    for _, value in stream:
        result += str(value)

    return result


class OutputPythonFilter(Filter):

    def __init__(self, varname='sql'):
        self.varname = varname
        self.cnt = 0

    def _process(self, stream, varname, count, has_nl):
        if count > 1:
            yield sql.Token(T.Whitespace, '\n')
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '=')
        yield sql.Token(T.Whitespace, ' ')
        if has_nl:
            yield sql.Token(T.Operator, '(')
        yield sql.Token(T.Text, "'")
        cnt = 0
        for token in stream:
            cnt += 1
            if token.is_whitespace() and '\n' in token.value:
                if cnt == 1:
                    continue
                after_lb = token.value.split('\n', 1)[1]
                yield sql.Token(T.Text, " '")
                yield sql.Token(T.Whitespace, '\n')
                for i in range(len(varname) + 4):
                    yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Text, "'")
                if after_lb:  # it's the indendation
                    yield sql.Token(T.Whitespace, after_lb)
                continue
            elif token.value and "'" in token.value:
                token.value = token.value.replace("'", "\\'")
            yield sql.Token(T.Text, token.value or '')
        yield sql.Token(T.Text, "'")
        if has_nl:
            yield sql.Token(T.Operator, ')')

    def process(self, stack, stmt):
        self.cnt += 1
        if self.cnt > 1:
            varname = '%s%d' % (self.varname, self.cnt)
        else:
            varname = self.varname
        has_nl = len(stmt.to_unicode().strip().splitlines()) > 1
        stmt.tokens = self._process(stmt.tokens, varname, self.cnt, has_nl)
        return stmt


class OutputPHPFilter(Filter):

    def __init__(self, varname='sql'):
        self.varname = '$%s' % varname
        self.count = 0

    def _process(self, stream, varname):
        if self.count > 1:
            yield sql.Token(T.Whitespace, '\n')
        yield sql.Token(T.Name, varname)
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Operator, '=')
        yield sql.Token(T.Whitespace, ' ')
        yield sql.Token(T.Text, '"')
        for token in stream:
            if token.is_whitespace() and '\n' in token.value:
                after_lb = token.value.split('\n', 1)[1]
                yield sql.Token(T.Text, ' "')
                yield sql.Token(T.Operator, ';')
                yield sql.Token(T.Whitespace, '\n')
                yield sql.Token(T.Name, varname)
                yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Punctuation, '.')
                yield sql.Token(T.Operator, '=')
                yield sql.Token(T.Whitespace, ' ')
                yield sql.Token(T.Text, '"')
                if after_lb:
                    yield sql.Token(T.Text, after_lb)
                continue
            elif '"' in token.value:
                token.value = token.value.replace('"', '\\"')
            yield sql.Token(T.Text, token.value)
        yield sql.Token(T.Text, '"')
        yield sql.Token(T.Punctuation, ';')

    def process(self, stack, stmt):
        self.count += 1
        if self.count > 1:
            varname = '%s%d' % (self.varname, self.count)
        else:
            varname = self.varname
        stmt.tokens = tuple(self._process(stmt.tokens, varname))
        return stmt


class Limit(Filter):
    """Get the LIMIT of a query.

    If not defined, return -1 (SQL specification for no LIMIT query)
    """
    def process(self, stack, stream):
        index = 7
        stream = list(stream)
        stream.reverse()

        # Run over all tokens in the stream from the end
        for token_type, value in stream:
            index -= 1

#            if index and token_type in Keyword:
            if index and token_type in Keyword and value == 'LIMIT':
                return stream[4 - index][1]

        return -1
########NEW FILE########
__FILENAME__ = formatter
# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""SQL formatter"""
from __future__ import absolute_import
from . import SQLParseError
from . import filters


def validate_options(options):
    """Validates options."""
    kwcase = options.get('keyword_case', None)
    if kwcase not in [None, 'upper', 'lower', 'capitalize']:
        raise SQLParseError('Invalid value for keyword_case: %r' % kwcase)

    idcase = options.get('identifier_case', None)
    if idcase not in [None, 'upper', 'lower', 'capitalize']:
        raise SQLParseError('Invalid value for identifier_case: %r' % idcase)

    ofrmt = options.get('output_format', None)
    if ofrmt not in [None, 'sql', 'python', 'php']:
        raise SQLParseError('Unknown output format: %r' % ofrmt)

    strip_comments = options.get('strip_comments', False)
    if strip_comments not in [True, False]:
        raise SQLParseError('Invalid value for strip_comments: %r'
                            % strip_comments)

    strip_ws = options.get('strip_whitespace', False)
    if strip_ws not in [True, False]:
        raise SQLParseError('Invalid value for strip_whitespace: %r'
                            % strip_ws)

    reindent = options.get('reindent', False)
    if reindent not in [True, False]:
        raise SQLParseError('Invalid value for reindent: %r'
                            % reindent)
    elif reindent:
        options['strip_whitespace'] = True
    indent_tabs = options.get('indent_tabs', False)
    if indent_tabs not in [True, False]:
        raise SQLParseError('Invalid value for indent_tabs: %r' % indent_tabs)
    elif indent_tabs:
        options['indent_char'] = '\t'
    else:
        options['indent_char'] = ' '
    indent_width = options.get('indent_width', 2)
    try:
        indent_width = int(indent_width)
    except (TypeError, ValueError):
        raise SQLParseError('indent_width requires an integer')
    if indent_width < 1:
        raise SQLParseError('indent_width requires an positive integer')
    options['indent_width'] = indent_width

    right_margin = options.get('right_margin', None)
    if right_margin is not None:
        try:
            right_margin = int(right_margin)
        except (TypeError, ValueError):
            raise SQLParseError('right_margin requires an integer')
        if right_margin < 10:
            raise SQLParseError('right_margin requires an integer > 10')
    options['right_margin'] = right_margin

    return options


def build_filter_stack(stack, options):
    """Setup and return a filter stack.

    Args:
      stack: :class:`~sqlparse.filters.FilterStack` instance
      options: Dictionary with options validated by validate_options.
    """
    # Token filter
    if options.get('keyword_case', None):
        stack.preprocess.append(
            filters.KeywordCaseFilter(options['keyword_case']))

    if options.get('identifier_case', None):
        stack.preprocess.append(
            filters.IdentifierCaseFilter(options['identifier_case']))

    # After grouping
    if options.get('strip_comments', False):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripCommentsFilter())

    if (options.get('strip_whitespace', False)
        or options.get('reindent', False)):
        stack.enable_grouping()
        stack.stmtprocess.append(filters.StripWhitespaceFilter())

    if options.get('reindent', False):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.ReindentFilter(char=options['indent_char'],
                                   width=options['indent_width']))

    if options.get('right_margin', False):
        stack.enable_grouping()
        stack.stmtprocess.append(
            filters.RightMarginFilter(width=options['right_margin']))

    # Serializer
    if options.get('output_format'):
        frmt = options['output_format']
        if frmt.lower() == 'php':
            fltr = filters.OutputPHPFilter()
        elif frmt.lower() == 'python':
            fltr = filters.OutputPythonFilter()
        else:
            fltr = None
        if fltr is not None:
            stack.postprocess.append(fltr)

    return stack

########NEW FILE########
__FILENAME__ = keywords
from __future__ import absolute_import
from . import tokens

KEYWORDS = {
    'ABORT': tokens.Keyword,
    'ABS': tokens.Keyword,
    'ABSOLUTE': tokens.Keyword,
    'ACCESS': tokens.Keyword,
    'ADA': tokens.Keyword,
    'ADD': tokens.Keyword,
    'ADMIN': tokens.Keyword,
    'AFTER': tokens.Keyword,
    'AGGREGATE': tokens.Keyword,
    'ALIAS': tokens.Keyword,
    'ALL': tokens.Keyword,
    'ALLOCATE': tokens.Keyword,
    'ANALYSE': tokens.Keyword,
    'ANALYZE': tokens.Keyword,
    'ANY': tokens.Keyword,
    'ARE': tokens.Keyword,
    'ASC': tokens.Keyword,
    'ASENSITIVE': tokens.Keyword,
    'ASSERTION': tokens.Keyword,
    'ASSIGNMENT': tokens.Keyword,
    'ASYMMETRIC': tokens.Keyword,
    'AT': tokens.Keyword,
    'ATOMIC': tokens.Keyword,
    'AUTHORIZATION': tokens.Keyword,
    'AVG': tokens.Keyword,

    'BACKWARD': tokens.Keyword,
    'BEFORE': tokens.Keyword,
    'BEGIN': tokens.Keyword,
    'BETWEEN': tokens.Keyword,
    'BITVAR': tokens.Keyword,
    'BIT_LENGTH': tokens.Keyword,
    'BOTH': tokens.Keyword,
    'BREADTH': tokens.Keyword,

#    'C': tokens.Keyword,  # most likely this is an alias
    'CACHE': tokens.Keyword,
    'CALL': tokens.Keyword,
    'CALLED': tokens.Keyword,
    'CARDINALITY': tokens.Keyword,
    'CASCADE': tokens.Keyword,
    'CASCADED': tokens.Keyword,
    'CAST': tokens.Keyword,
    'CATALOG': tokens.Keyword,
    'CATALOG_NAME': tokens.Keyword,
    'CHAIN': tokens.Keyword,
    'CHARACTERISTICS': tokens.Keyword,
    'CHARACTER_LENGTH': tokens.Keyword,
    'CHARACTER_SET_CATALOG': tokens.Keyword,
    'CHARACTER_SET_NAME': tokens.Keyword,
    'CHARACTER_SET_SCHEMA': tokens.Keyword,
    'CHAR_LENGTH': tokens.Keyword,
    'CHECK': tokens.Keyword,
    'CHECKED': tokens.Keyword,
    'CHECKPOINT': tokens.Keyword,
    'CLASS': tokens.Keyword,
    'CLASS_ORIGIN': tokens.Keyword,
    'CLOB': tokens.Keyword,
    'CLOSE': tokens.Keyword,
    'CLUSTER': tokens.Keyword,
    'COALSECE': tokens.Keyword,
    'COBOL': tokens.Keyword,
    'COLLATE': tokens.Keyword,
    'COLLATION': tokens.Keyword,
    'COLLATION_CATALOG': tokens.Keyword,
    'COLLATION_NAME': tokens.Keyword,
    'COLLATION_SCHEMA': tokens.Keyword,
    'COLUMN': tokens.Keyword,
    'COLUMN_NAME': tokens.Keyword,
    'COMMAND_FUNCTION': tokens.Keyword,
    'COMMAND_FUNCTION_CODE': tokens.Keyword,
    'COMMENT': tokens.Keyword,
    'COMMIT': tokens.Keyword,
    'COMMITTED': tokens.Keyword,
    'COMPLETION': tokens.Keyword,
    'CONDITION_NUMBER': tokens.Keyword,
    'CONNECT': tokens.Keyword,
    'CONNECTION': tokens.Keyword,
    'CONNECTION_NAME': tokens.Keyword,
    'CONSTRAINT': tokens.Keyword,
    'CONSTRAINTS': tokens.Keyword,
    'CONSTRAINT_CATALOG': tokens.Keyword,
    'CONSTRAINT_NAME': tokens.Keyword,
    'CONSTRAINT_SCHEMA': tokens.Keyword,
    'CONSTRUCTOR': tokens.Keyword,
    'CONTAINS': tokens.Keyword,
    'CONTINUE': tokens.Keyword,
    'CONVERSION': tokens.Keyword,
    'CONVERT': tokens.Keyword,
    'COPY': tokens.Keyword,
    'CORRESPONTING': tokens.Keyword,
    'COUNT': tokens.Keyword,
    'CREATEDB': tokens.Keyword,
    'CREATEUSER': tokens.Keyword,
    'CROSS': tokens.Keyword,
    'CUBE': tokens.Keyword,
    'CURRENT': tokens.Keyword,
    'CURRENT_DATE': tokens.Keyword,
    'CURRENT_PATH': tokens.Keyword,
    'CURRENT_ROLE': tokens.Keyword,
    'CURRENT_TIME': tokens.Keyword,
    'CURRENT_TIMESTAMP': tokens.Keyword,
    'CURRENT_USER': tokens.Keyword,
    'CURSOR': tokens.Keyword,
    'CURSOR_NAME': tokens.Keyword,
    'CYCLE': tokens.Keyword,

    'DATA': tokens.Keyword,
    'DATABASE': tokens.Keyword,
    'DATETIME_INTERVAL_CODE': tokens.Keyword,
    'DATETIME_INTERVAL_PRECISION': tokens.Keyword,
    'DAY': tokens.Keyword,
    'DEALLOCATE': tokens.Keyword,
    'DECLARE': tokens.Keyword,
    'DEFAULT': tokens.Keyword,
    'DEFAULTS': tokens.Keyword,
    'DEFERRABLE': tokens.Keyword,
    'DEFERRED': tokens.Keyword,
    'DEFINED': tokens.Keyword,
    'DEFINER': tokens.Keyword,
    'DELIMITER': tokens.Keyword,
    'DELIMITERS': tokens.Keyword,
    'DEREF': tokens.Keyword,
    'DESC': tokens.Keyword,
    'DESCRIBE': tokens.Keyword,
    'DESCRIPTOR': tokens.Keyword,
    'DESTROY': tokens.Keyword,
    'DESTRUCTOR': tokens.Keyword,
    'DETERMINISTIC': tokens.Keyword,
    'DIAGNOSTICS': tokens.Keyword,
    'DICTIONARY': tokens.Keyword,
    'DISCONNECT': tokens.Keyword,
    'DISPATCH': tokens.Keyword,
    'DO': tokens.Keyword,
    'DOMAIN': tokens.Keyword,
    'DYNAMIC': tokens.Keyword,
    'DYNAMIC_FUNCTION': tokens.Keyword,
    'DYNAMIC_FUNCTION_CODE': tokens.Keyword,

    'EACH': tokens.Keyword,
    'ENCODING': tokens.Keyword,
    'ENCRYPTED': tokens.Keyword,
    'END-EXEC': tokens.Keyword,
    'EQUALS': tokens.Keyword,
    'ESCAPE': tokens.Keyword,
    'EVERY': tokens.Keyword,
    'EXCEPT': tokens.Keyword,
    'ESCEPTION': tokens.Keyword,
    'EXCLUDING': tokens.Keyword,
    'EXCLUSIVE': tokens.Keyword,
    'EXEC': tokens.Keyword,
    'EXECUTE': tokens.Keyword,
    'EXISTING': tokens.Keyword,
    'EXISTS': tokens.Keyword,
    'EXTERNAL': tokens.Keyword,
    'EXTRACT': tokens.Keyword,

    'FALSE': tokens.Keyword,
    'FETCH': tokens.Keyword,
    'FINAL': tokens.Keyword,
    'FIRST': tokens.Keyword,
    'FORCE': tokens.Keyword,
    'FOREIGN': tokens.Keyword,
    'FORTRAN': tokens.Keyword,
    'FORWARD': tokens.Keyword,
    'FOUND': tokens.Keyword,
    'FREE': tokens.Keyword,
    'FREEZE': tokens.Keyword,
    'FULL': tokens.Keyword,
    'FUNCTION': tokens.Keyword,

#    'G': tokens.Keyword,
    'GENERAL': tokens.Keyword,
    'GENERATED': tokens.Keyword,
    'GET': tokens.Keyword,
    'GLOBAL': tokens.Keyword,
    'GO': tokens.Keyword,
    'GOTO': tokens.Keyword,
    'GRANT': tokens.Keyword,
    'GRANTED': tokens.Keyword,
    'GROUPING': tokens.Keyword,

    'HANDLER': tokens.Keyword,
    'HAVING': tokens.Keyword,
    'HIERARCHY': tokens.Keyword,
    'HOLD': tokens.Keyword,
    'HOST': tokens.Keyword,

    'IDENTITY': tokens.Keyword,
    'IGNORE': tokens.Keyword,
    'ILIKE': tokens.Keyword,
    'IMMEDIATE': tokens.Keyword,
    'IMMUTABLE': tokens.Keyword,

    'IMPLEMENTATION': tokens.Keyword,
    'IMPLICIT': tokens.Keyword,
    'INCLUDING': tokens.Keyword,
    'INCREMENT': tokens.Keyword,
    'INDEX': tokens.Keyword,

    'INDITCATOR': tokens.Keyword,
    'INFIX': tokens.Keyword,
    'INHERITS': tokens.Keyword,
    'INITIALIZE': tokens.Keyword,
    'INITIALLY': tokens.Keyword,
    'INOUT': tokens.Keyword,
    'INPUT': tokens.Keyword,
    'INSENSITIVE': tokens.Keyword,
    'INSTANTIABLE': tokens.Keyword,
    'INSTEAD': tokens.Keyword,
    'INTERSECT': tokens.Keyword,
    'INTO': tokens.Keyword,
    'INVOKER': tokens.Keyword,
    'IS': tokens.Keyword,
    'ISNULL': tokens.Keyword,
    'ISOLATION': tokens.Keyword,
    'ITERATE': tokens.Keyword,

#    'K': tokens.Keyword,
    'KEY': tokens.Keyword,
    'KEY_MEMBER': tokens.Keyword,
    'KEY_TYPE': tokens.Keyword,

    'LANCOMPILER': tokens.Keyword,
    'LANGUAGE': tokens.Keyword,
    'LARGE': tokens.Keyword,
    'LAST': tokens.Keyword,
    'LATERAL': tokens.Keyword,
    'LEADING': tokens.Keyword,
    'LENGTH': tokens.Keyword,
    'LESS': tokens.Keyword,
    'LEVEL': tokens.Keyword,
    'LIMIT': tokens.Keyword,
    'LISTEN': tokens.Keyword,
    'LOAD': tokens.Keyword,
    'LOCAL': tokens.Keyword,
    'LOCALTIME': tokens.Keyword,
    'LOCALTIMESTAMP': tokens.Keyword,
    'LOCATION': tokens.Keyword,
    'LOCATOR': tokens.Keyword,
    'LOCK': tokens.Keyword,
    'LOWER': tokens.Keyword,

#    'M': tokens.Keyword,
    'MAP': tokens.Keyword,
    'MATCH': tokens.Keyword,
    'MAXVALUE': tokens.Keyword,
    'MESSAGE_LENGTH': tokens.Keyword,
    'MESSAGE_OCTET_LENGTH': tokens.Keyword,
    'MESSAGE_TEXT': tokens.Keyword,
    'METHOD': tokens.Keyword,
    'MINUTE': tokens.Keyword,
    'MINVALUE': tokens.Keyword,
    'MOD': tokens.Keyword,
    'MODE': tokens.Keyword,
    'MODIFIES': tokens.Keyword,
    'MODIFY': tokens.Keyword,
    'MONTH': tokens.Keyword,
    'MORE': tokens.Keyword,
    'MOVE': tokens.Keyword,
    'MUMPS': tokens.Keyword,

    'NAMES': tokens.Keyword,
    'NATIONAL': tokens.Keyword,
    'NATURAL': tokens.Keyword,
    'NCHAR': tokens.Keyword,
    'NCLOB': tokens.Keyword,
    'NEW': tokens.Keyword,
    'NEXT': tokens.Keyword,
    'NO': tokens.Keyword,
    'NOCREATEDB': tokens.Keyword,
    'NOCREATEUSER': tokens.Keyword,
    'NONE': tokens.Keyword,
    'NOT': tokens.Keyword,
    'NOTHING': tokens.Keyword,
    'NOTIFY': tokens.Keyword,
    'NOTNULL': tokens.Keyword,
    'NULL': tokens.Keyword,
    'NULLABLE': tokens.Keyword,
    'NULLIF': tokens.Keyword,

    'OBJECT': tokens.Keyword,
    'OCTET_LENGTH': tokens.Keyword,
    'OF': tokens.Keyword,
    'OFF': tokens.Keyword,
    'OFFSET': tokens.Keyword,
    'OIDS': tokens.Keyword,
    'OLD': tokens.Keyword,
    'ONLY': tokens.Keyword,
    'OPEN': tokens.Keyword,
    'OPERATION': tokens.Keyword,
    'OPERATOR': tokens.Keyword,
    'OPTION': tokens.Keyword,
    'OPTIONS': tokens.Keyword,
    'ORDINALITY': tokens.Keyword,
    'OUT': tokens.Keyword,
    'OUTPUT': tokens.Keyword,
    'OVERLAPS': tokens.Keyword,
    'OVERLAY': tokens.Keyword,
    'OVERRIDING': tokens.Keyword,
    'OWNER': tokens.Keyword,

    'PAD': tokens.Keyword,
    'PARAMETER': tokens.Keyword,
    'PARAMETERS': tokens.Keyword,
    'PARAMETER_MODE': tokens.Keyword,
    'PARAMATER_NAME': tokens.Keyword,
    'PARAMATER_ORDINAL_POSITION': tokens.Keyword,
    'PARAMETER_SPECIFIC_CATALOG': tokens.Keyword,
    'PARAMETER_SPECIFIC_NAME': tokens.Keyword,
    'PARAMATER_SPECIFIC_SCHEMA': tokens.Keyword,
    'PARTIAL': tokens.Keyword,
    'PASCAL': tokens.Keyword,
    'PENDANT': tokens.Keyword,
    'PLACING': tokens.Keyword,
    'PLI': tokens.Keyword,
    'POSITION': tokens.Keyword,
    'POSTFIX': tokens.Keyword,
    'PRECISION': tokens.Keyword,
    'PREFIX': tokens.Keyword,
    'PREORDER': tokens.Keyword,
    'PREPARE': tokens.Keyword,
    'PRESERVE': tokens.Keyword,
    'PRIMARY': tokens.Keyword,
    'PRIOR': tokens.Keyword,
    'PRIVILEGES': tokens.Keyword,
    'PROCEDURAL': tokens.Keyword,
    'PROCEDURE': tokens.Keyword,
    'PUBLIC': tokens.Keyword,

    'RAISE': tokens.Keyword,
    'READ': tokens.Keyword,
    'READS': tokens.Keyword,
    'RECHECK': tokens.Keyword,
    'RECURSIVE': tokens.Keyword,
    'REF': tokens.Keyword,
    'REFERENCES': tokens.Keyword,
    'REFERENCING': tokens.Keyword,
    'REINDEX': tokens.Keyword,
    'RELATIVE': tokens.Keyword,
    'RENAME': tokens.Keyword,
    'REPEATABLE': tokens.Keyword,
    'RESET': tokens.Keyword,
    'RESTART': tokens.Keyword,
    'RESTRICT': tokens.Keyword,
    'RESULT': tokens.Keyword,
    'RETURN': tokens.Keyword,
    'RETURNED_LENGTH': tokens.Keyword,
    'RETURNED_OCTET_LENGTH': tokens.Keyword,
    'RETURNED_SQLSTATE': tokens.Keyword,
    'RETURNS': tokens.Keyword,
    'REVOKE': tokens.Keyword,
    'RIGHT': tokens.Keyword,
    'ROLE': tokens.Keyword,
    'ROLLBACK': tokens.Keyword,
    'ROLLUP': tokens.Keyword,
    'ROUTINE': tokens.Keyword,
    'ROUTINE_CATALOG': tokens.Keyword,
    'ROUTINE_NAME': tokens.Keyword,
    'ROUTINE_SCHEMA': tokens.Keyword,
    'ROW': tokens.Keyword,
    'ROWS': tokens.Keyword,
    'ROW_COUNT': tokens.Keyword,
    'RULE': tokens.Keyword,

    'SAVE_POINT': tokens.Keyword,
    'SCALE': tokens.Keyword,
    'SCHEMA': tokens.Keyword,
    'SCHEMA_NAME': tokens.Keyword,
    'SCOPE': tokens.Keyword,
    'SCROLL': tokens.Keyword,
    'SEARCH': tokens.Keyword,
    'SECOND': tokens.Keyword,
    'SECURITY': tokens.Keyword,
    'SELF': tokens.Keyword,
    'SENSITIVE': tokens.Keyword,
    'SERIALIZABLE': tokens.Keyword,
    'SERVER_NAME': tokens.Keyword,
    'SESSION': tokens.Keyword,
    'SESSION_USER': tokens.Keyword,
    'SETOF': tokens.Keyword,
    'SETS': tokens.Keyword,
    'SHARE': tokens.Keyword,
    'SHOW': tokens.Keyword,
    'SIMILAR': tokens.Keyword,
    'SIMPLE': tokens.Keyword,
    'SIZE': tokens.Keyword,
    'SOME': tokens.Keyword,
    'SOURCE': tokens.Keyword,
    'SPACE': tokens.Keyword,
    'SPECIFIC': tokens.Keyword,
    'SPECIFICTYPE': tokens.Keyword,
    'SPECIFIC_NAME': tokens.Keyword,
    'SQL': tokens.Keyword,
    'SQLCODE': tokens.Keyword,
    'SQLERROR': tokens.Keyword,
    'SQLEXCEPTION': tokens.Keyword,
    'SQLSTATE': tokens.Keyword,
    'SQLWARNING': tokens.Keyword,
    'STABLE': tokens.Keyword,
    'START': tokens.Keyword,
    'STATE': tokens.Keyword,
    'STATEMENT': tokens.Keyword,
    'STATIC': tokens.Keyword,
    'STATISTICS': tokens.Keyword,
    'STDIN': tokens.Keyword,
    'STDOUT': tokens.Keyword,
    'STORAGE': tokens.Keyword,
    'STRICT': tokens.Keyword,
    'STRUCTURE': tokens.Keyword,
    'STYPE': tokens.Keyword,
    'SUBCLASS_ORIGIN': tokens.Keyword,
    'SUBLIST': tokens.Keyword,
    'SUBSTRING': tokens.Keyword,
    'SUM': tokens.Keyword,
    'SYMMETRIC': tokens.Keyword,
    'SYSID': tokens.Keyword,
    'SYSTEM': tokens.Keyword,
    'SYSTEM_USER': tokens.Keyword,

    'TABLE': tokens.Keyword,
    'TABLE_NAME': tokens.Keyword,
    ' TEMP': tokens.Keyword,
    'TEMPLATE': tokens.Keyword,
    'TEMPORARY': tokens.Keyword,
    'TERMINATE': tokens.Keyword,
    'THAN': tokens.Keyword,
    'TIMESTAMP': tokens.Keyword,
    'TIMEZONE_HOUR': tokens.Keyword,
    'TIMEZONE_MINUTE': tokens.Keyword,
    'TO': tokens.Keyword,
    'TOAST': tokens.Keyword,
    'TRAILING': tokens.Keyword,
    'TRANSATION': tokens.Keyword,
    'TRANSACTIONS_COMMITTED': tokens.Keyword,
    'TRANSACTIONS_ROLLED_BACK': tokens.Keyword,
    'TRANSATION_ACTIVE': tokens.Keyword,
    'TRANSFORM': tokens.Keyword,
    'TRANSFORMS': tokens.Keyword,
    'TRANSLATE': tokens.Keyword,
    'TRANSLATION': tokens.Keyword,
    'TREAT': tokens.Keyword,
    'TRIGGER': tokens.Keyword,
    'TRIGGER_CATALOG': tokens.Keyword,
    'TRIGGER_NAME': tokens.Keyword,
    'TRIGGER_SCHEMA': tokens.Keyword,
    'TRIM': tokens.Keyword,
    'TRUE': tokens.Keyword,
    'TRUNCATE': tokens.Keyword,
    'TRUSTED': tokens.Keyword,
    'TYPE': tokens.Keyword,

    'UNCOMMITTED': tokens.Keyword,
    'UNDER': tokens.Keyword,
    'UNENCRYPTED': tokens.Keyword,
    'UNION': tokens.Keyword,
    'UNIQUE': tokens.Keyword,
    'UNKNOWN': tokens.Keyword,
    'UNLISTEN': tokens.Keyword,
    'UNNAMED': tokens.Keyword,
    'UNNEST': tokens.Keyword,
    'UNTIL': tokens.Keyword,
    'UPPER': tokens.Keyword,
    'USAGE': tokens.Keyword,
    'USER': tokens.Keyword,
    'USER_DEFINED_TYPE_CATALOG': tokens.Keyword,
    'USER_DEFINED_TYPE_NAME': tokens.Keyword,
    'USER_DEFINED_TYPE_SCHEMA': tokens.Keyword,
    'USING': tokens.Keyword,

    'VACUUM': tokens.Keyword,
    'VALID': tokens.Keyword,
    'VALIDATOR': tokens.Keyword,
    'VALUES': tokens.Keyword,
    'VARIABLE': tokens.Keyword,
    'VERBOSE': tokens.Keyword,
    'VERSION': tokens.Keyword,
    'VIEW': tokens.Keyword,
    'VOLATILE': tokens.Keyword,

    'WHENEVER': tokens.Keyword,
    'WITH': tokens.Keyword,
    'WITHOUT': tokens.Keyword,
    'WORK': tokens.Keyword,
    'WRITE': tokens.Keyword,

    'YEAR': tokens.Keyword,

    'ZONE': tokens.Keyword,


    'ARRAY': tokens.Name.Builtin,
    'BIGINT': tokens.Name.Builtin,
    'BINARY': tokens.Name.Builtin,
    'BIT': tokens.Name.Builtin,
    'BLOB': tokens.Name.Builtin,
    'BOOLEAN': tokens.Name.Builtin,
    'CHAR': tokens.Name.Builtin,
    'CHARACTER': tokens.Name.Builtin,
    'DATE': tokens.Name.Builtin,
    'DEC': tokens.Name.Builtin,
    'DECIMAL': tokens.Name.Builtin,
    'FLOAT': tokens.Name.Builtin,
    'INT': tokens.Name.Builtin,
    'INTEGER': tokens.Name.Builtin,
    'INTERVAL': tokens.Name.Builtin,
    'LONG': tokens.Name.Builtin,
    'NUMBER': tokens.Name.Builtin,
    'NUMERIC': tokens.Name.Builtin,
    'REAL': tokens.Name.Builtin,
    'SERIAL': tokens.Name.Builtin,
    'SMALLINT': tokens.Name.Builtin,
    'VARCHAR': tokens.Name.Builtin,
    'VARCHAR2': tokens.Name.Builtin,
    'VARYING': tokens.Name.Builtin,
    'INT8': tokens.Name.Builtin,
    'SERIAL8': tokens.Name.Builtin,
    'TEXT': tokens.Name.Builtin,
    }


KEYWORDS_COMMON = {
    'SELECT': tokens.Keyword.DML,
    'INSERT': tokens.Keyword.DML,
    'DELETE': tokens.Keyword.DML,
    'UPDATE': tokens.Keyword.DML,
    'REPLACE': tokens.Keyword.DML,
    'DROP': tokens.Keyword.DDL,
    'CREATE': tokens.Keyword.DDL,
    'ALTER': tokens.Keyword.DDL,

    'WHERE': tokens.Keyword,
    'FROM': tokens.Keyword,
    'INNER': tokens.Keyword,
    'JOIN': tokens.Keyword,
    'AND': tokens.Keyword,
    'OR': tokens.Keyword,
    'LIKE': tokens.Keyword,
    'ON': tokens.Keyword,
    'IN': tokens.Keyword,
    'SET': tokens.Keyword,

    'BY': tokens.Keyword,
    'GROUP': tokens.Keyword,
    'ORDER': tokens.Keyword,
    'LEFT': tokens.Keyword,
    'OUTER': tokens.Keyword,

    'IF': tokens.Keyword,
    'END': tokens.Keyword,
    'THEN': tokens.Keyword,
    'LOOP': tokens.Keyword,
    'AS': tokens.Keyword,
    'ELSE': tokens.Keyword,
    'FOR': tokens.Keyword,

    'CASE': tokens.Keyword,
    'WHEN': tokens.Keyword,
    'MIN': tokens.Keyword,
    'MAX': tokens.Keyword,
    'DISTINCT': tokens.Keyword,
    }

########NEW FILE########
__FILENAME__ = lexer
# -*- coding: utf-8 -*-

# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""SQL Lexer"""

# This code is based on the SqlLexer in pygments.
# http://pygments.org/
# It's separated from the rest of pygments to increase performance
# and to allow some customizations.
from __future__ import absolute_import
from __future__ import unicode_literals
import re

from . import tokens
from .keywords import KEYWORDS, KEYWORDS_COMMON


class include(str):
    pass


class combined(tuple):
    """Indicates a state combined from multiple states."""

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    def __init__(self, *args):
        # tuple.__init__ doesn't do anything
        pass


def is_keyword(value):
    test = value.upper()
    return KEYWORDS_COMMON.get(test, KEYWORDS.get(test, tokens.Name)), value


def apply_filters(stream, filters, lexer=None):
    """
    Use this method to apply an iterable of filters to
    a stream. If lexer is given it's forwarded to the
    filter, otherwise the filter receives `None`.
    """

    def _apply(filter_, stream):
        for token in filter_.filter(lexer, stream):
            yield token

    for filter_ in filters:
        stream = _apply(filter_, stream)
    return stream


class LexerMeta(type):
    """
    Metaclass for Lexer, creates the self._tokens attribute from
    self.tokens on the first instantiation.
    """

    def _process_state(cls, unprocessed, processed, state):
        assert type(state) is str, "wrong state name %r" % state
        assert state[0] != '#', "invalid state name %r" % state
        if state in processed:
            return processed[state]
        tokenlist = processed[state] = []
        rflags = cls.flags
        for tdef in unprocessed[state]:
            if isinstance(tdef, include):
                # it's a state reference
                assert tdef != state, "circular state reference %r" % state
                tokenlist.extend(cls._process_state(
                    unprocessed, processed, str(tdef)))
                continue

            assert type(tdef) is tuple, "wrong rule def %r" % tdef

            try:
                rex = re.compile(tdef[0], rflags).match
            except Exception as err:
                raise ValueError(("uncompilable regex %r in state"
                                  " %r of %r: %s"
                                  % (tdef[0], state, cls, err)))

            assert type(tdef[1]) is tokens._TokenType or callable(tdef[1]), \
                   ('token type must be simple type or callable, not %r'
                    % (tdef[1],))

            if len(tdef) == 2:
                new_state = None
            else:
                tdef2 = tdef[2]
                if isinstance(tdef2, str):
                    # an existing state
                    if tdef2 == '#pop':
                        new_state = -1
                    elif tdef2 in unprocessed:
                        new_state = (tdef2,)
                    elif tdef2 == '#push':
                        new_state = tdef2
                    elif tdef2[:5] == '#pop:':
                        new_state = -int(tdef2[5:])
                    else:
                        assert False, 'unknown new state %r' % tdef2
                elif isinstance(tdef2, combined):
                    # combine a new state from existing ones
                    new_state = '_tmp_%d' % cls._tmpname
                    cls._tmpname += 1
                    itokens = []
                    for istate in tdef2:
                        assert istate != state, \
                               'circular state ref %r' % istate
                        itokens.extend(cls._process_state(unprocessed,
                                                          processed, istate))
                    processed[new_state] = itokens
                    new_state = (new_state,)
                elif isinstance(tdef2, tuple):
                    # push more than one state
                    for state in tdef2:
                        assert (state in unprocessed or
                                state in ('#pop', '#push')), \
                               'unknown new state ' + state
                    new_state = tdef2
                else:
                    assert False, 'unknown new state def %r' % tdef2
            tokenlist.append((rex, tdef[1], new_state))
        return tokenlist

    def process_tokendef(cls):
        cls._all_tokens = {}
        cls._tmpname = 0
        processed = cls._all_tokens[cls.__name__] = {}
        #tokendefs = tokendefs or cls.tokens[name]
        for state in cls.tokens.keys():
            cls._process_state(cls.tokens, processed, state)
        return processed

    def __call__(cls, *args, **kwds):
        if not hasattr(cls, '_tokens'):
            cls._all_tokens = {}
            cls._tmpname = 0
            if hasattr(cls, 'token_variants') and cls.token_variants:
                # don't process yet
                pass
            else:
                cls._tokens = cls.process_tokendef()

        return type.__call__(cls, *args, **kwds)


class Lexer(object, metaclass=LexerMeta):

    encoding = 'utf-8'
    stripall = False
    stripnl = False
    tabsize = 0
    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'--.*?(\r\n|\r|\n)', tokens.Comment.Single),
            # $ matches *before* newline, therefore we have two patterns
            # to match Comment.Single
            (r'--.*?$', tokens.Comment.Single),
            (r'(\r|\n|\r\n)', tokens.Newline),
            (r'\s+', tokens.Whitespace),
            (r'/\*', tokens.Comment.Multiline, 'multiline-comments'),
            (r':=', tokens.Assignment),
            (r'::', tokens.Punctuation),
            (r'[*]', tokens.Wildcard),
            (r'CASE\b', tokens.Keyword),  # extended CASE(foo)
            (r"`(``|[^`])*`", tokens.Name),
            (r"´(´´|[^´])*´", tokens.Name),
            (r'\$([a-zA-Z_][a-zA-Z0-9_]*)?\$', tokens.Name.Builtin),
            (r'\?{1}', tokens.Name.Placeholder),
            (r'[$:?%][a-zA-Z0-9_]+[^$:?%]?', tokens.Name.Placeholder),
            (r'@[a-zA-Z_][a-zA-Z0-9_]+', tokens.Name),
            (r'[a-zA-Z_][a-zA-Z0-9_]*(?=[.(])', tokens.Name),  # see issue39
            (r'[<>=~!]+', tokens.Operator.Comparison),
            (r'[+/@#%^&|`?^-]+', tokens.Operator),
            (r'0x[0-9a-fA-F]+', tokens.Number.Hexadecimal),
            (r'[0-9]*\.[0-9]+', tokens.Number.Float),
            (r'[0-9]+', tokens.Number.Integer),
            # TODO: Backslash escapes?
            (r"(''|'.*?[^\\]')", tokens.String.Single),
            # not a real string literal in ANSI SQL:
            (r'(""|".*?[^\\]")', tokens.String.Symbol),
            (r'(\[.*[^\]]\])', tokens.Name),
            (r'(LEFT |RIGHT )?(INNER |OUTER )?JOIN\b', tokens.Keyword),
            (r'END( IF| LOOP)?\b', tokens.Keyword),
            (r'NOT NULL\b', tokens.Keyword),
            (r'CREATE( OR REPLACE)?\b', tokens.Keyword.DDL),
            (r'(?<=\.)[a-zA-Z_][a-zA-Z0-9_]*', tokens.Name),
            (r'[a-zA-Z_][a-zA-Z0-9_]*', is_keyword),
            (r'[;:()\[\],\.]', tokens.Punctuation),
        ],
        'multiline-comments': [
            (r'/\*', tokens.Comment.Multiline, 'multiline-comments'),
            (r'\*/', tokens.Comment.Multiline, '#pop'),
            (r'[^/\*]+', tokens.Comment.Multiline),
            (r'[/*]', tokens.Comment.Multiline)
        ]}

    def __init__(self):
        self.filters = []

    def add_filter(self, filter_, **options):
        from .filters import Filter
        if not isinstance(filter_, Filter):
            filter_ = filter_(**options)
        self.filters.append(filter_)

    def get_tokens(self, text, unfiltered=False):
        """
        Return an iterable of (tokentype, value) pairs generated from
        `text`. If `unfiltered` is set to `True`, the filtering mechanism
        is bypassed even if filters are defined.

        Also preprocess the text, i.e. expand tabs and strip it if
        wanted and applies registered filters.
        """
        if not isinstance(text, str):
            if self.encoding == 'guess':
                try:
                    text = text.decode('utf-8')
                    if text.startswith(u'\ufeff'):
                        text = text[len(u'\ufeff'):]
                except UnicodeDecodeError:
                    text = text.decode('latin1')
            else:
                text = text.decode(self.encoding)
        if self.stripall:
            text = text.strip()
        elif self.stripnl:
            text = text.strip('\n')
        if self.tabsize > 0:
            text = text.expandtabs(self.tabsize)
#        if not text.endswith('\n'):
#            text += '\n'

        def streamer():
            for i, t, v in self.get_tokens_unprocessed(text):
                yield t, v
        stream = streamer()
        if not unfiltered:
            stream = apply_filters(stream, self.filters, self)
        return stream

    def get_tokens_unprocessed(self, text, stack=('root',)):
        """
        Split ``text`` into (tokentype, text) pairs.

        ``stack`` is the inital stack (default: ``['root']``)
        """
        pos = 0
        tokendefs = self._tokens  # see __call__, pylint:disable=E1101
        statestack = list(stack)
        statetokens = tokendefs[statestack[-1]]
        known_names = {}
        while 1:
            for rexmatch, action, new_state in statetokens:
                m = rexmatch(text, pos)
                if m:
                    # print rex.pattern
                    value = m.group()
                    if value in known_names:
                        yield pos, known_names[value], value
                    elif type(action) is tokens._TokenType:
                        yield pos, action, value
                    elif hasattr(action, '__call__'):
                        ttype, value = action(value)
                        known_names[value] = ttype
                        yield pos, ttype, value
                    else:
                        for item in action(self, m):
                            yield item
                    pos = m.end()
                    if new_state is not None:
                        # state transition
                        if isinstance(new_state, tuple):
                            for state in new_state:
                                if state == '#pop':
                                    statestack.pop()
                                elif state == '#push':
                                    statestack.append(statestack[-1])
                                else:
                                    statestack.append(state)
                        elif isinstance(new_state, int):
                            # pop
                            del statestack[new_state:]
                        elif new_state == '#push':
                            statestack.append(statestack[-1])
                        else:
                            assert False, "wrong state def: %r" % new_state
                        statetokens = tokendefs[statestack[-1]]
                    break
            else:
                try:
                    if text[pos] == '\n':
                        # at EOL, reset state to "root"
                        pos += 1
                        statestack = ['root']
                        statetokens = tokendefs['root']
                        yield pos, tokens.Text, u'\n'
                        continue
                    yield pos, tokens.Error, text[pos]
                    pos += 1
                except IndexError:
                    break


def tokenize(sql):
    """Tokenize sql.

    Tokenize *sql* using the :class:`Lexer` and return a 2-tuple stream
    of ``(token type, value)`` items.
    """
    lexer = Lexer()
    return lexer.get_tokens(sql)

########NEW FILE########
__FILENAME__ = pipeline
# Copyright (C) 2011 Jesus Leganes "piranna", piranna@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.
from __future__ import absolute_import
from types import GeneratorType


class Pipeline(list):
    """Pipeline to process filters sequentially"""

    def __call__(self, stream):
        """Run the pipeline

        Return a static (non generator) version of the result
        """

        # Run the stream over all the filters on the pipeline
        for filter in self:
            # Functions and callable objects (objects with '__call__' method)
            if callable(filter):
                stream = filter(stream)

            # Normal filters (objects with 'process' method)
            else:
                stream = filter.process(None, stream)

        # If last filter return a generator, staticalize it inside a list
        if isinstance(stream, GeneratorType):
            return list(stream)
        return stream

########NEW FILE########
__FILENAME__ = sql
# -*- coding: utf-8 -*-

"""This module contains classes representing syntactical elements of SQL."""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import re
import sys

from . import tokens as T


class Token(object):
    """Base class for all other classes in this module.

    It represents a single token and has two instance attributes:
    ``value`` is the unchange value of the token and ``ttype`` is
    the type of the token.
    """

    __slots__ = ('value', 'ttype', 'parent')

    def __init__(self, ttype, value):
        self.value = value
        self.ttype = ttype
        self.parent = None

    def __str__(self):
        if sys.version_info > (3, 0):
            return self.__unicode__()
        else:
            return unicode(self).encode('utf-8')

    def __repr__(self):
        short = self._get_repr_value()
        return '<%s \'%s\' at 0x%07x>' % (self._get_repr_name(),
                                          short, id(self))

    def __unicode__(self):
        return self.value or ''

    def to_unicode(self):
        """Returns a unicode representation of this object."""
        return str(self)

    def _get_repr_name(self):
        return str(self.ttype).split('.')[-1]

    def _get_repr_value(self):
        raw = str(self)
        if len(raw) > 7:
            short = raw[:6] + u'...'
        else:
            short = raw
        return re.sub('\s+', ' ', short)

    def flatten(self):
        """Resolve subgroups."""
        yield self

    def match(self, ttype, values, regex=False):
        """Checks whether the token matches the given arguments.

        *ttype* is a token type. If this token doesn't match the given token
        type.
        *values* is a list of possible values for this token. The values
        are OR'ed together so if only one of the values matches ``True``
        is returned. Except for keyword tokens the comparison is
        case-sensitive. For convenience it's ok to pass in a single string.
        If *regex* is ``True`` (default is ``False``) the given values are
        treated as regular expressions.
        """
        type_matched = self.ttype is ttype
        if not type_matched or values is None:
            return type_matched
        if isinstance(values, str):
            values = set([values])
        if regex:
            if self.ttype is T.Keyword:
                values = set([re.compile(v, re.IGNORECASE) for v in values])
            else:
                values = set([re.compile(v) for v in values])
            for pattern in values:
                if pattern.search(self.value):
                    return True
            return False
        else:
            if self.ttype in T.Keyword:
                values = set([v.upper() for v in values])
                return self.value.upper() in values
            else:
                return self.value in values

    def is_group(self):
        """Returns ``True`` if this object has children."""
        return False

    def is_whitespace(self):
        """Return ``True`` if this token is a whitespace token."""
        return self.ttype and self.ttype in T.Whitespace

    def within(self, group_cls):
        """Returns ``True`` if this token is within *group_cls*.

        Use this method for example to check if an identifier is within
        a function: ``t.within(sql.Function)``.
        """
        parent = self.parent
        while parent:
            if isinstance(parent, group_cls):
                return True
            parent = parent.parent
        return False

    def is_child_of(self, other):
        """Returns ``True`` if this token is a direct child of *other*."""
        return self.parent == other

    def has_ancestor(self, other):
        """Returns ``True`` if *other* is in this tokens ancestry."""
        parent = self.parent
        while parent:
            if parent == other:
                return True
            parent = parent.parent
        return False


class TokenList(Token):
    """A group of tokens.

    It has an additional instance attribute ``tokens`` which holds a
    list of child-tokens.
    """

    __slots__ = ('value', 'ttype', 'tokens')

    def __init__(self, tokens=None):
        if tokens is None:
            tokens = []
        self.tokens = tokens
        Token.__init__(self, None, None)

    def __unicode__(self):
        return ''.join(str(x) for x in self.flatten())

    def __str__(self):
        if sys.version_info > (3, 0):
            return self.__unicode__()
        else:
            return unicode(self).encode('utf-8')

    def _get_repr_name(self):
        return self.__class__.__name__

    def _pprint_tree(self, max_depth=None, depth=0):
        """Pretty-print the object tree."""
        indent = ' ' * (depth * 2)
        for idx, token in enumerate(self.tokens):
            if token.is_group():
                pre = ' +-'
            else:
                pre = ' | '
            print("%s%s%d %s '%s'" % (
                indent,
                pre,
                idx,
                token._get_repr_name(),
                token._get_repr_value()
            ))
            if (token.is_group() and (max_depth is None or depth < max_depth)):
                token._pprint_tree(max_depth, depth + 1)

    def flatten(self):
        """Generator yielding ungrouped tokens.

        This method is recursively called for all child tokens.
        """
        for token in self.tokens:
            if isinstance(token, TokenList):
                for item in token.flatten():
                    yield item
            else:
                yield token

    def is_group(self):
        return True

    def get_sublists(self):
        return [x for x in self.tokens if isinstance(x, TokenList)]

    @property
    def _groupable_tokens(self):
        return self.tokens

    def token_first(self, ignore_whitespace=True):
        """Returns the first child token.

        If *ignore_whitespace* is ``True`` (the default), whitespace
        tokens are ignored.
        """
        for token in self.tokens:
            if ignore_whitespace and token.is_whitespace():
                continue
            return token
        return None

    def token_next_by_instance(self, idx, clss):
        """Returns the next token matching a class.

        *idx* is where to start searching in the list of child tokens.
        *clss* is a list of classes the token should be an instance of.

        If no matching token can be found ``None`` is returned.
        """
        if isinstance(clss, (list, tuple)):
            clss = (clss,)
        if isinstance(clss, tuple):
            clss = tuple(clss)
        for token in self.tokens[idx:]:
            if isinstance(token, clss):
                return token
        return None

    def token_next_by_type(self, idx, ttypes):
        """Returns next matching token by it's token type."""
        if not isinstance(ttypes, (list, tuple)):
            ttypes = [ttypes]
        for token in self.tokens[idx:]:
            if token.ttype in ttypes:
                return token
        return None

    def token_next_match(self, idx, ttype, value, regex=False):
        """Returns next token where it's ``match`` method returns ``True``."""
        if not isinstance(idx, int):
            idx = self.token_index(idx)
        for token in self.tokens[idx:]:
            if token.match(ttype, value, regex):
                return token
        return None

    def token_not_matching(self, idx, funcs):
        for token in self.tokens[idx:]:
            passed = False
            for func in funcs:
                if func(token):
                    passed = True
                    break
            if not passed:
                return token
        return None

    def token_matching(self, idx, funcs):
        for token in self.tokens[idx:]:
            for i, func in enumerate(funcs):
                if func(token):
                    return token
        return None

    def token_prev(self, idx, skip_ws=True):
        """Returns the previous token relative to *idx*.

        If *skip_ws* is ``True`` (the default) whitespace tokens are ignored.
        ``None`` is returned if there's no previous token.
        """
        if idx is None:
            return None
        if not isinstance(idx, int):
            idx = self.token_index(idx)
        while idx != 0:
            idx -= 1
            if self.tokens[idx].is_whitespace() and skip_ws:
                continue
            return self.tokens[idx]

    def token_next(self, idx, skip_ws=True):
        """Returns the next token relative to *idx*.

        If *skip_ws* is ``True`` (the default) whitespace tokens are ignored.
        ``None`` is returned if there's no next token.
        """
        if idx is None:
            return None
        if not isinstance(idx, int):
            idx = self.token_index(idx)
        while idx < len(self.tokens) - 1:
            idx += 1
            if self.tokens[idx].is_whitespace() and skip_ws:
                continue
            return self.tokens[idx]

    def token_index(self, token):
        """Return list index of token."""
        return self.tokens.index(token)

    def tokens_between(self, start, end, exclude_end=False):
        """Return all tokens between (and including) start and end.

        If *exclude_end* is ``True`` (default is ``False``) the end token
        is included too.
        """
        # FIXME(andi): rename exclude_end to inlcude_end
        if exclude_end:
            offset = 0
        else:
            offset = 1
        end_idx = self.token_index(end) + offset
        start_idx = self.token_index(start)
        return self.tokens[start_idx:end_idx]

    def group_tokens(self, grp_cls, tokens, ignore_ws=False):
        """Replace tokens by an instance of *grp_cls*."""
        idx = self.token_index(tokens[0])
        if ignore_ws:
            while tokens and tokens[-1].is_whitespace():
                tokens = tokens[:-1]
        for t in tokens:
            self.tokens.remove(t)
        grp = grp_cls(tokens)
        for token in tokens:
            token.parent = grp
        grp.parent = self
        self.tokens.insert(idx, grp)
        return grp

    def insert_before(self, where, token):
        """Inserts *token* before *where*."""
        self.tokens.insert(self.token_index(where), token)

    def has_alias(self):
        """Returns ``True`` if an alias is present."""
        return self.get_alias() is not None

    def get_alias(self):
        """Returns the alias for this identifier or ``None``."""
        kw = self.token_next_match(0, T.Keyword, 'AS')
        if kw is not None:
            alias = self.token_next(self.token_index(kw))
            if alias is None:
                return None
        else:
            next_ = self.token_next_by_instance(0, Identifier)
            if next_ is None:
                return None
            alias = next_
        if isinstance(alias, Identifier):
            return alias.get_name()
        else:
            return alias.to_unicode()

    def get_name(self):
        """Returns the name of this identifier.

        This is either it's alias or it's real name. The returned valued can
        be considered as the name under which the object corresponding to
        this identifier is known within the current statement.
        """
        alias = self.get_alias()
        if alias is not None:
            return alias
        return self.get_real_name()

    def get_real_name(self):
        """Returns the real name (object name) of this identifier."""
        # a.b
        dot = self.token_next_match(0, T.Punctuation, '.')
        if dot is None:
            return self.token_next_by_type(0, T.Name).value
        else:
            next_ = self.token_next_by_type(self.token_index(dot),
                                            (T.Name, T.Wildcard))
            if next_ is None:  # invalid identifier, e.g. "a."
                return None
            return next_.value



class Statement(TokenList):
    """Represents a SQL statement."""

    __slots__ = ('value', 'ttype', 'tokens')

    def get_type(self):
        """Returns the type of a statement.

        The returned value is a string holding an upper-cased reprint of
        the first DML or DDL keyword. If the first token in this group
        isn't a DML or DDL keyword "UNKNOWN" is returned.
        """
        first_token = self.token_first()
        if first_token is None:
            # An "empty" statement that either has not tokens at all
            # or only whitespace tokens.
            return 'UNKNOWN'
        elif first_token.ttype in (T.Keyword.DML, T.Keyword.DDL):
            return first_token.value.upper()
        else:
            return 'UNKNOWN'


class Identifier(TokenList):
    """Represents an identifier.

    Identifiers may have aliases or typecasts.
    """

    __slots__ = ('value', 'ttype', 'tokens')

    def get_parent_name(self):
        """Return name of the parent object if any.

        A parent object is identified by the first occuring dot.
        """
        dot = self.token_next_match(0, T.Punctuation, '.')
        if dot is None:
            return None
        prev_ = self.token_prev(self.token_index(dot))
        if prev_ is None:  # something must be verry wrong here..
            return None
        return prev_.value

    def is_wildcard(self):
        """Return ``True`` if this identifier contains a wildcard."""
        token = self.token_next_by_type(0, T.Wildcard)
        return token is not None

    def get_typecast(self):
        """Returns the typecast or ``None`` of this object as a string."""
        marker = self.token_next_match(0, T.Punctuation, '::')
        if marker is None:
            return None
        next_ = self.token_next(self.token_index(marker), False)
        if next_ is None:
            return None
        return next_.to_unicode()


class IdentifierList(TokenList):
    """A list of :class:`~sqlparse.sql.Identifier`\'s."""

    __slots__ = ('value', 'ttype', 'tokens')

    def get_identifiers(self):
        """Returns the identifiers.

        Whitespaces and punctuations are not included in this list.
        """
        return [x for x in self.tokens
                if not x.is_whitespace() and not x.match(T.Punctuation, ',')]


class Parenthesis(TokenList):
    """Tokens between parenthesis."""
    __slots__ = ('value', 'ttype', 'tokens')

    @property
    def _groupable_tokens(self):
        return self.tokens[1:-1]


class Assignment(TokenList):
    """An assignment like 'var := val;'"""
    __slots__ = ('value', 'ttype', 'tokens')


class If(TokenList):
    """An 'if' clause with possible 'else if' or 'else' parts."""
    __slots__ = ('value', 'ttype', 'tokens')


class For(TokenList):
    """A 'FOR' loop."""
    __slots__ = ('value', 'ttype', 'tokens')


class Comparison(TokenList):
    """A comparison used for example in WHERE clauses."""
    __slots__ = ('value', 'ttype', 'tokens')


class Comment(TokenList):
    """A comment."""
    __slots__ = ('value', 'ttype', 'tokens')


class Where(TokenList):
    """A WHERE clause."""
    __slots__ = ('value', 'ttype', 'tokens')


class Case(TokenList):
    """A CASE statement with one or more WHEN and possibly an ELSE part."""

    __slots__ = ('value', 'ttype', 'tokens')

    def get_cases(self):
        """Returns a list of 2-tuples (condition, value).

        If an ELSE exists condition is None.
        """
        ret = []
        in_value = False
        in_condition = True
        for token in self.tokens:
            if token.match(T.Keyword, 'CASE'):
                continue
            elif token.match(T.Keyword, 'WHEN'):
                ret.append(([], []))
                in_condition = True
                in_value = False
            elif token.match(T.Keyword, 'ELSE'):
                ret.append((None, []))
                in_condition = False
                in_value = True
            elif token.match(T.Keyword, 'THEN'):
                in_condition = False
                in_value = True
            elif token.match(T.Keyword, 'END'):
                in_condition = False
                in_value = False
            if (in_condition or in_value) and not ret:
                # First condition withou preceding WHEN
                ret.append(([], []))
            if in_condition:
                ret[-1][0].append(token)
            elif in_value:
                ret[-1][1].append(token)
        return ret


class Function(TokenList):
    """A function or procedure call."""

    __slots__ = ('value', 'ttype', 'tokens')

    def get_parameters(self):
        """Return a list of parameters."""
        parenthesis = self.tokens[-1]
        for t in parenthesis.tokens:
            if isinstance(t, IdentifierList):
                return t.get_identifiers()
        return []

########NEW FILE########
__FILENAME__ = tokens
# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

# The Token implementation is based on pygment's token system written
# by Georg Brandl.
# http://pygments.org/

"""Tokens"""
from __future__ import absolute_import


class _TokenType(tuple):
    parent = None

    def split(self):
        buf = []
        node = self
        while node is not None:
            buf.append(node)
            node = node.parent
        buf.reverse()
        return buf

    def __contains__(self, val):
        return val is not None and (self is val or val[:len(self)] == self)

    def __getattr__(self, val):
        if not val or not val[0].isupper():
            return tuple.__getattribute__(self, val)
        new = _TokenType(self + (val,))
        setattr(self, val, new)
        new.parent = self
        return new

    def __hash__(self):
        return hash(tuple(self))

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)


Token = _TokenType()

# Special token types
Text = Token.Text
Whitespace = Text.Whitespace
Newline = Whitespace.Newline
Error = Token.Error
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other = Token.Other

# Common token types for source code
Keyword = Token.Keyword
Name = Token.Name
Literal = Token.Literal
String = Literal.String
Number = Literal.Number
Punctuation = Token.Punctuation
Operator = Token.Operator
Comparison = Operator.Comparison
Wildcard = Token.Wildcard
Comment = Token.Comment
Assignment = Token.Assignement

# Generic types for non-source code
Generic = Token.Generic

# String and some others are not direct childs of Token.
# alias them:
Token.Token = Token
Token.String = String
Token.Number = Number

# SQL specific tokens
DML = Keyword.DML
DDL = Keyword.DDL
Command = Keyword.Command

Group = Token.Group
Group.Parenthesis = Token.Group.Parenthesis
Group.Comment = Token.Group.Comment
Group.Where = Token.Group.Where

########NEW FILE########
