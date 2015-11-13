__FILENAME__ = aggregates

from __future__ import division

"""
An aggregate class is expected to accept two values at
instantiation: 'column' and 'name', and the class
must have two methods 'update(self, row)' and 'value(self)'.
The 'update' method is called for each row, and the 'value'
must return the final result of the aggregation.
"""

class Aggregate(object):
    def __init__(self, column, name=None):
        self.column = column and column.lower()
        self.name = (name or column).lower()

    def _to_number(self, val):
        if isinstance(val, (int, long, float)):
            return val
        if isinstance(val, basestring):
            if '.' in val:
                return float(val)
            return int(val)
        return float(val)

class AvgAggregate(Aggregate):
    """Calculate the average value for a column"""

    def __init__(self, *args, **kwargs):
        super(AvgAggregate, self).__init__(*args, **kwargs)
        self.sum = 0
        self.count = 0

    def update(self, row):
        self.sum += self._to_number(row[self.column]) 
        self.count += 1

    def value(self):
        if self.count == 0:
            return None
        return self.sum / self.count

class CountAggregate(Aggregate):
    """Count the number of rows"""

    def __init__(self, *args, **kwargs):
        super(CountAggregate, self).__init__(*args, **kwargs)
        self.count = 0

    def update(self, row):
        self.count += 1

    def value(self):
        return self.count

class MaxAggregate(Aggregate):
    """Calculate the maximum value for a column"""

    def __init__(self, *args, **kwargs):
        super(MaxAggregate, self).__init__(*args, **kwargs)
        self.max = None

    def update(self, row):
        val = self._to_number(row[self.column])
        if self.max is None:
            self.max = val
        else:
            self.max = max(self.max, val)

    def value(self):
        return self.max

class MinAggregate(Aggregate):
    """Calculate the minimum value for a column"""

    def __init__(self, *args, **kwargs):
        super(MinAggregate, self).__init__(*args, **kwargs)
        self.min = None

    def update(self, row):
        val = self._to_number(row[self.column])
        if self.min is None:
            self.min = val
        else:
            self.min = min(self.min, val)

    def value(self):
        return self.min

class SumAggregate(Aggregate):
    """Calculate the sum of values for a column"""

    def __init__(self, *args, **kwargs):
        super(SumAggregate, self).__init__(*args, **kwargs)
        self.sum = 0

    def update(self, row):
        self.sum += self._to_number(row[self.column])

    def value(self):
        return self.sum

aggregate_functions = dict(
    avg = AvgAggregate,
    count = CountAggregate,
    max = MaxAggregate,
    min = MinAggregate,
    sum = SumAggregate,
)

########NEW FILE########
__FILENAME__ = command

from __future__ import with_statement

import sys
from optparse import OptionParser
from squawk.query import Query
from squawk.output import output_formats
from squawk.parsers import parsers
from squawk.sql import sql_parser

def get_table_names(tokens):
    if not isinstance(tokens.tables[0][0], basestring):
        return get_table_names(tokens.tables[0][0])
    return [tokens.tables[0][0]]

class Combiner(object):
    def __init__(self, files, parser_class):
        self.files = files
        self.parser_class = parser_class
        self.index = 0
        self.next_file()

    def next_file(self):
        if self.index >= len(self.files):
            raise StopIteration()
        fname = self.files[self.index]
        self.parser = self.parser_class(sys.stdin if fname == '-' else open(fname, "r"))
        self.parser_iter = iter(self.parser)
        self.columns = self.parser.columns
        self.index += 1

    def __iter__(self):
        return self

    def next(self):
        while True:
            try:
                row = self.parser_iter.next()
            except StopIteration:
                self.next_file()
            else:
                return row

def build_opt_parser():
    parser = OptionParser()
    parser.add_option("-p", "--parser", dest="parser",
                      help="name of parser for input")
    parser.add_option("-f", "--format", dest="format", default="tabular",
                      help="write output in FORMAT format", metavar="FORMAT")
    # parser.add_option("-q", "--quiet",
    #                   action="store_false", dest="verbose", default=True,
    #                   help="don't print status messages to stdout")
    return parser

def main():
    parser = build_opt_parser()
    (options, args) = parser.parse_args()

    sql = ' '.join(args).strip()
    if not sql:
        print "An SQL expression is required"
        return

    files = get_table_names(sql_parser.parseString(sql))

    parser_name = options.parser
    if parser_name:
        parser = parsers[parser_name]
    else:
        fn = files[0]
        if fn.rsplit('/', 1)[-1] == 'access.log':
            parser = parsers['access_log']
        elif fn.endswith('.csv'):
            parser = parsers['csv']
        else:
            sys.stderr.write("Can't figure out parser for input")
            sys.exit(1)

    source = Combiner(files, parser)
    query = Query(sql)

    output = output_formats[options.format]

    output(query(source))

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = output

import csv
import sys
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        json = None

def output_tabular(rows, fp=None):
    fp = fp or sys.stdout
    fp.write("\t| ".join(rows.columns))
    fp.write("\n")
    fp.write("-"*40+"\n")
    for row in rows:
        fp.write("\t| ".join(row[k] if isinstance(row[k], basestring) else str(row[k]) for k in rows.columns))
        fp.write("\n")

def output_json(rows, fp=None):
    fp = fp or sys.stdout
    fp.write('[')
    first = True
    for row in rows:
        if not first:
            fp.write(',\n')
        else:
            first = False
        fp.write(json.dumps(row))
    fp.write(']')

def output_csv(rows, fp=None, **kwargs):
    fp = fp or sys.stdout
    writer = csv.writer(fp, **kwargs)
    writer.writerow(rows.columns)
    for row in rows:
        writer.writerow([row[k] for k in rows.columns])

output_formats = dict(
    tabular = output_tabular,
    json = output_json,
    csv = output_csv,
)

########NEW FILE########
__FILENAME__ = access_log
import re

log_re = re.compile(
    r'^(?P<remote_addr>("[^"]+"|[^\s]+))'
    r" -"
    r" (?P<remote_user>[^\s]+)"
    r" \[(?P<time>[^\]]+)\]"
    r'\s+"(?P<request>[^"]*)"'
    r" (?P<status>[^\s]+)"
    r" (?P<bytes>[^\s]+)"
    r'\s+"(?P<referrer>[^"]*)"'
    r'\s+"(?P<user_agent>[^"]*)"'
    r".*$")

class AccessLogParser(object):
    def __init__(self, file):
        if isinstance(file, basestring):
            self.fp = open(file, "rb")
        else:
            self.fp = file

        self.columns = [x[0] for x in sorted(log_re.groupindex.items(), key=lambda g:g[1])]
        self.columns.remove("request")
        self.columns += ["method", "path", "httpver"]

    def __iter__(self):
        for line in self.fp:
            m = log_re.match(line.strip())
            d = m.groupdict()
            d['remote_addr'] = d['remote_addr'].replace('"', '')
            try:
                request = d.pop('request')
                method, path, httpver = request.split(' ')
            except ValueError:
                method, path, httpver = None, None, None
            try:
                d['bytes'] = int(d['bytes'])
            except ValueError:
                d['bytes'] = 0
            d['status'] = int(d['status'])
            yield d

########NEW FILE########
__FILENAME__ = csvparser

import csv

class CSVParser(object):
    def __init__(self, file):
        if isinstance(file, basestring):
            fp = open(file, "rb")
        else:
            fp = file
        self.reader = csv.DictReader(fp)
        self.columns = [x.lower() for x in self.reader.fieldnames]

    def __iter__(self):
        for row in self.reader:
            yield dict((k.lower(), v) for k, v in row.items())

########NEW FILE########
__FILENAME__ = pickleparser
try:
    import cPickle as pickle
except ImportError:
    import pickle

class PickleParser(object):
    def __init__(self, file):
        if isinstance(file, basestring):
            self.fp = open(file, "rb")
        else:
            self.fp = file

        self.data = pickle.load(self.fp)
        if not isinstance(self.data, (list, tuple)):
            raise Exception("Unsupported format for pickled data. Should be a list of dictionaries e.g. [{'col': 'value'}]")

        self.columns = self.data[0].keys()

    def __iter__(self):
        for row in self.data:
            yield row

########NEW FILE########
__FILENAME__ = query

from __future__ import division
from functools import partial
import re

from squawk.aggregates import aggregate_functions
from squawk.sql import sql_parser

OPERATOR_MAPPING = {
    '<>': '!=',
    '!=': '!=',
    '=': '==',
    '<': '<',
    '>': '>',
    '<=': '<=',
    '>=': '>=',
}


def sql_like(like_clause):
    return like_clause.replace("%",".*").replace("_",".")

class Column(object):
    def __init__(self, column, name=None):
        self.column = column.lower()
        self.name = (name or column).lower()
        self._value = None

    def update(self, row):
        self._value = row[self.column]

    def value(self):
        return self._value

class LimitOffset(object):
    def __init__(self, source, limit, offset=0):
        self.source = source
        self.limit = limit
        self.offset = offset

    def __iter__(self):
        for i, row in enumerate(self.source):
            if i < self.offset:
                continue

            yield row

            if self.limit is not None and i+1 >= self.limit + self.offset:
                return

class OrderBy(object):
    def __init__(self, source, order_by, descending=False):
        self.source = source
        self.order_by = order_by.lower()
        self.descending = descending

    def __iter__(self):
        results = list(self.source)
        results.sort(key=lambda row:row[self.order_by], reverse=self.descending)
        for r in results:
            yield r

class GroupBy(object):
    def __init__(self, source, group_by, columns):
        self.source = source
        self.group_by = group_by
        self._columns = columns

    def __iter__(self):
        groups = {}
        for row in self.source:
            key = tuple(row[k] for k in self.group_by)
            if key not in groups:
                groups[key] = [x() for x in self._columns]
            for s in groups[key]:
                s.update(row)
        for key, row in groups.iteritems():
            yield dict((r.name, r.value()) for r in row)

class Filter(object):
    def __init__(self, source, function):
        self.source = source
        self.function = function

    def __iter__(self):
        for row in self.source:
            if self.function(row):
                yield row

class Selector(object):
    def __init__(self, source, columns):
        self.source = source
        self._columns = [(n.lower(), (a or n).lower()) for n, a in columns] if columns else None

    def __iter__(self):
        if self._columns:
            for row in self.source:
                yield dict((alias, row[name]) for name, alias in self._columns)
        else:
            for row in self.source:
                yield row

class Aggregator(object):
    def __init__(self, source, columns):
        self.source = source
        self._columns = columns

    def __iter__(self):
        columns = [c() for c in self._columns]
        for row in self.source:
            for c in columns:
                c.update(row)
        yield dict((c.name, c.value()) for c in columns)

class Query(object):
    def __init__(self, sql):
        self.tokens = sql_parser.parseString(sql) if isinstance(sql, basestring) else sql
        self.column_classes = None
        self._table_subquery = None
        self._parts = self._generate_parts()

    def _generate_parts(self):
        """Return a list of callables that can be composed to build a query generator"""
        tokens = self.tokens
        parts = []

        self.column_classes = [self._column_builder(c) for c in tokens.columns] if tokens.columns != '*' else None

        if not isinstance(tokens.tables[0][0], basestring):
            self._table_subquery = Query(tokens.tables[0][0])

        if tokens.where:
            func = eval("lambda row:"+self._filter_builder(tokens.where))
            parts.append(partial(Filter, function=func))
        if tokens.groupby:
            # Group by query
            parts.append(partial(GroupBy,
                    group_by = [c[0] for c in tokens.groupby],
                    columns = self.column_classes))
        elif self.column_classes and any(len(c.name)>1 for c in tokens.columns):
            # Aggregate query
            parts.append(partial(Aggregator, columns=self.column_classes))
        else:
            # Basic select
            parts.append(partial(Selector, columns=[(c.name[0], c.alias) for c in tokens.columns] if tokens.columns != '*' else None))
        if tokens.orderby:
            order = tokens.orderby
            parts.append(partial(OrderBy, order_by=order[0][0], descending=order[1]=='DESC' if len(order) > 1 else False))
        if tokens.limit or tokens.offset:
            parts.append(partial(LimitOffset,
                limit = int(tokens.limit) if tokens.limit else None,
                offset = int(tokens.offset) if tokens.offset else 0))

        return parts

    def _filter_builder(self, where):
        """Return a Python expression from a tokenized 'where' filter"""
        l = []
        for expr in where:
            if expr[0] == '(':
                l.append("(")
                l.append(self._filter_builder(expr[1:-1]))
                l.append(")")
            else:
                if isinstance(expr, basestring):
                    l.append(expr)
                elif len(expr) == 3:
                    if expr[1] == "like":
                        l.append('re.match(%s, row["%s"])' % (sql_like(expr[2]), expr[0].lower()))
                    elif expr[1] in ("~", '~*', '!~', '!~*'):
                        neg = "not " if expr[1][0] == '!' else ""
                        flags = re.I if expr[1][-1] == '*' else 0
                        l.append('%sre.match(r%s, row["%s"], %d)' % (neg, expr[2], expr[0].lower(), flags))
                    else:
                        op = OPERATOR_MAPPING[expr[1]]
                        l.append('(row["%s"] %s %s)' % (expr[0].lower(), op, expr[2]))
                elif expr[1] == "in":
                    l.append('(row["%s"] in %r)' % (expr[0].lower(), expr[3:-1]))
                else:
                    raise Exception("Don't understand expression %s in where clause" % expr)
        return " ".join(l)

    def _column_builder(self, col):
        """Return a callable that builds a column or aggregate object"""
        if len(col.name) > 1:
            # Aggregate
            try:
                aclass = aggregate_functions[col.name[0]]
            except KeyError:
                raise KeyError("Unknown aggregate function %s" % col.name[0])
            return lambda:aclass(col.name[1], col.alias if col.alias else '%s(%s)' % (col.name[0], col.name[1]))
        else:
            # Column
            return lambda:Column(col.name[0], col.alias)

    def __call__(self, source):
        executor = self._table_subquery(source) if self._table_subquery else source
        for p in self._parts:
            executor = p(source=executor)
        executor.columns = [c().name for c in self.column_classes] if self.column_classes else source.columns
        return executor

########NEW FILE########
__FILENAME__ = sql

# This file is camelCase to match pyparsing

__all__ = ["sql_parser"]

from pyparsing import Literal, CaselessLiteral, Word, Upcase, delimitedList, Optional, \
    Combine, Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString, \
    ZeroOrMore, restOfLine, Keyword, downcaseTokens, Suppress, stringEnd, Regex, NotAny

selectToken  = Keyword("select", caseless=True)
fromToken    = Keyword("from", caseless=True)
whereToken   = Keyword("where", caseless=True)
groupByToken = Keyword("group", caseless=True) + Keyword("by", caseless=True)
orderByToken = Keyword("order", caseless=True) + Keyword("by", caseless=True)
limitToken   = Keyword("limit", caseless=True)
offsetToken  = Keyword("offset", caseless=True)
keywords     = NotAny(selectToken | fromToken | whereToken | groupByToken | orderByToken | limitToken | offsetToken)

selectStmt  = Forward()

ident          = Word(alphas, alphanums + "_$").setName("identifier")
# ident          = Regex(r'"?(?!^from$|^where$)[A-Za-z][A-Za-z0-9_$]*"?').setName("identifier")
columnName     = delimitedList(ident, ".", combine=True).setParseAction(downcaseTokens)

aggregateFunction = (
    (CaselessLiteral("count") | CaselessLiteral("sum") |
     CaselessLiteral("min") | CaselessLiteral("max") | CaselessLiteral("avg"))
    + Suppress("(") + (columnName | oneOf("1 *")) + Suppress(")"))
columnDef      = Group(aggregateFunction | columnName).setResultsName("name")
aliasDef       = Optional(Optional(Suppress(CaselessLiteral("AS"))) +
                   keywords +
                   columnName.setResultsName("alias"))

filename       = Word(alphanums+"/._-$").setName("filename")
tableName      = delimitedList(filename, ".", combine=True)
subQuery       = Group(Suppress("(") + selectStmt + Suppress(")"))
tableDef       = subQuery | tableName

# tableNameList  = Group(delimitedList(Group(tableDef + aliasDef))) # Standard SQL table list
tableNameList  = Group(delimitedList(Group(tableDef), ' ')) # Not standard SQL table list. Allow spaces to separate tables. Easier to use on command line.

whereExpression = Forward()
and_ = Keyword("and", caseless=True)
or_ = Keyword("or", caseless=True)
in_ = Keyword("in", caseless=True)
like = Keyword("like", caseless=True)

E = CaselessLiteral("E")
binop = oneOf("= != <> < > >= <= eq ne lt le gt ge", caseless=True)
regexOp = oneOf("~ ~* !~ !~*")
arithSign = Word("+-", exact=1)
realNum = (Combine(
    Optional(arithSign) + (
        Word(nums) + "." + Optional(Word(nums)) | ("." + Word(nums))
    ) + Optional(E + Optional(arithSign) + Word(nums)))
    .setName("real")
    .setParseAction(lambda s,l,toks: float(toks[0])))
intNum = (Combine(Optional(arithSign) + Word(nums) +
    Optional(E + Optional("+") + Word(nums)))
    .setName("integer")
    .setParseAction(lambda s,l,toks: int(toks[0])))

# WHERE
columnRval = realNum | intNum | quotedString | columnName # need to add support for alg expressions
columnLikeval = quotedString
whereCondition = Group(
        (columnName + binop + columnRval) |
        (columnName + like + columnLikeval) |
        (columnName + regexOp + quotedString) |
        (columnName + in_ + "(" + delimitedList(columnRval) + ")") |
        (columnName + in_ + "(" + selectStmt + ")") |
        ("(" + whereExpression + ")")
    )
whereExpression << whereCondition + ZeroOrMore((and_ | or_) + whereExpression) 

# GROUP BY
groupByExpression = Group(delimitedList(columnDef))

# ORDER BY
orderByExpression = Group(delimitedList(columnDef + Optional(CaselessLiteral("DESC") | CaselessLiteral("ASC"))))

# LIMIT
limitExpression = intNum

# OFFSET
offsetExpression = intNum

# define the grammar
selectColumnList = Group(delimitedList(Group(columnDef + aliasDef)))
selectStmt << (
    selectToken + 
    ('*' | selectColumnList).setResultsName("columns") + 
    fromToken + tableNameList.setResultsName("tables") + 
    Optional(whereToken + whereExpression.setResultsName("where"), "") +
    Optional(groupByToken + groupByExpression.setResultsName("groupby"), "") +
    Optional(orderByToken + orderByExpression.setResultsName("orderby"), "") +
    Optional(limitToken + limitExpression.setResultsName("limit"), "") +
    Optional(offsetToken + offsetExpression.setResultsName("offset"), ""))

sql_parser = selectStmt # + stringEnd

sqlComment = "--" + restOfLine # ignore comments
sql_parser.ignore(sqlComment)

########NEW FILE########
__FILENAME__ = version

VERSION = "0.3"

########NEW FILE########
