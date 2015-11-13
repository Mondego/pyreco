__FILENAME__ = converting
# coding: cp1251

import re, datetime

from pony.utils import is_ident

class ValidationError(ValueError):
    pass

def check_ip(s):
    s = s.strip()
    list = map(int, s.split('.'))
    if len(list) != 4: raise ValueError
    for number in list:
        if not 0 <= number <= 255: raise ValueError
    return s

def check_positive(s):
    i = int(s)
    if i > 0: return i
    raise ValueError

def check_identifier(s):
    if is_ident(s): return s
    raise ValueError

isbn_re = re.compile(r'(?:\d[ -]?)+x?')

def isbn10_checksum(digits):
    if len(digits) != 9: raise ValueError
    reminder = sum(digit*coef for digit, coef in zip(map(int, digits), xrange(10, 1, -1))) % 11
    if reminder == 1: return 'X'
    return reminder and str(11 - reminder) or '0'

def isbn13_checksum(digits):
    if len(digits) != 12: raise ValueError
    reminder = sum(digit*coef for digit, coef in zip(map(int, digits), (1, 3)*6)) % 10
    return reminder and str(10 - reminder) or '0'

def check_isbn(s, convert_to=None):
    s = s.strip().upper()
    if s[:4] == 'ISBN': s = s[4:].lstrip()
    digits = s.replace('-', '').replace(' ', '')
    size = len(digits)
    if size == 10: checksum_func = isbn10_checksum
    elif size == 13: checksum_func = isbn13_checksum
    else: raise ValueError
    digits, last = digits[:-1], digits[-1]
    if checksum_func(digits) != last:
        if last.isdigit() or size == 10 and last == 'X':
            raise ValidationError('Invalid ISBN checksum')
        raise ValueError
    if convert_to is not None:
        if size == 10 and convert_to == 13:
            digits = '978' + digits
            s = digits + isbn13_checksum(digits)
        elif size == 13 and convert_to == 10 and digits[:3] == '978':
            digits = digits[3:]
            s = digits + isbn10_checksum(digits)
    return s

def isbn10_to_isbn13(s):
    return check_isbn(s, convert_to=13)

def isbn13_to_isbn10(s):
    return check_isbn(s, convert_to=10)

# The next two regular expressions taken from
# http://www.regular-expressions.info/email.html

email_re = re.compile(
    r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.(?:[A-Z]{2}|com|org|net|gov|mil|biz|info|name|aero|biz|info|jobs|museum|coop)$',
    re.IGNORECASE)

rfc2822_email_re = re.compile(r'''
    ^(?: [a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*
     |   "(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*"
     )
     @
     (?: (?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?
     |   \[ (?: (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}
            (?: 25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]
                :(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+
            )
         \]
     )$''', re.IGNORECASE | re.VERBOSE)

def check_email(s):
    s = s.strip()
    if email_re.match(s) is None: raise ValueError
    return s

def check_rfc2822_email(s):
    s = s.strip()
    if rfc2822_email_re.match(s) is None: raise ValueError
    return s

date_str_list = [
    r'(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{4})',
    r'(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})',
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,4})',
    r'(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,4})',
    r'(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,4})',
    r'\D*(?P<year>\d{4})\D+(?P<day>\d{1,2})\D*',
    r'\D*(?P<day>\d{1,2})\D+(?P<year>\d{4})\D*'
    ]
date_re_list = [ re.compile('^%s$'%s, re.UNICODE) for s in date_str_list ]

time_str = r'(?P<hh>\d{1,2})(?:[:. ](?P<mm>\d{1,2})(?:[:. ](?P<ss>\d{1,2}))?)?\s*(?P<ampm>[ap][m])?'
time_re = re.compile('^%s$'%time_str)

datetime_re_list = [ re.compile('^%s(?: %s)?$' % (date_str, time_str), re.UNICODE) for date_str in date_str_list ]

month_lists = [
    "jan feb mar apr may jun jul aug sep oct nov dec".split(),
    u"янв фев мар апр май июн июл авг сен окт ноя дек".split(),  # Russian
    ]
month_dict = {}

for month_list in month_lists:
    for i, month in enumerate(month_list):
        month_dict[month] = i + 1

month_dict[u'мая'] = 5  # Russian

def str2date(s):
    s = s.strip().lower()
    for date_re in date_re_list:
        match = date_re.match(s)
        if match is not None: break
    else: raise ValueError('Unrecognized date format')
    dict = match.groupdict()
    year = dict['year']
    day = dict['day']
    month = dict.get('month')
    if month is None:
        for key, value in month_dict.iteritems():
            if key in s: month = value; break
        else: raise ValueError('Unrecognized date format')
    return datetime.date(int(year), int(month), int(day))

def str2time(s):
    s = s.strip().lower()
    match = time_re.match(s)
    if match is None: raise ValueError('Unrecognized time format')
    hh, mm, ss, ampm = match.groups()
    if ampm == 'pm': hh = int(hh) + 12
    return datetime.time(int(hh), int(mm or 0), int(ss or 0))

def str2datetime(s):
    s = s.strip().lower()
    for datetime_re in datetime_re_list:
        match = datetime_re.match(s)
        if match is not None: break
    else: raise ValueError('Unrecognized datetime format')
    dict = match.groupdict()
    year = dict['year']
    day = dict['day']
    month = dict.get('month')
    if month is None:
        for key, value in month_dict.iteritems():
            if key in s: month = value; break
        else: raise ValueError('Unrecognized datetime format')
    hh, mm, ss = dict.get('hh'), dict.get('mm'), dict.get('ss')
    if hh is None: hh, mm, ss = 12, 00, 00
    elif dict.get('ampm') == 'pm': hh = int(hh) + 12
    return datetime.datetime(int(year), int(month), int(day), int(hh), int(mm or 0), int(ss or 0))

converters = {
    int:  (int, unicode, 'Incorrect number'),
    long: (long, unicode, 'Incorrect number'),
    float: (float, unicode, 'Must be a real number'),
    'IP': (check_ip, unicode, 'Incorrect IP address'),
    'positive': (check_positive, unicode, 'Must be a positive number'),
    'identifier': (check_identifier, unicode, 'Incorrect identifier'),
    'ISBN': (check_isbn, unicode, 'Incorrect ISBN'),
    'email': (check_email, unicode, 'Incorrect e-mail address'),
    'rfc2822_email': (check_rfc2822_email, unicode, 'Must be correct e-mail address'),
    datetime.date: (str2date, unicode, 'Must be correct date (mm/dd/yyyy or dd.mm.yyyy)'),
    datetime.time: (str2time, unicode, 'Must be correct time (hh:mm or hh:mm:ss)'),
    datetime.datetime: (str2datetime, unicode, 'Must be correct date & time'),
    }

def str2py(value, type):
    if type is None or not isinstance(value, unicode): return value
    if isinstance(type, tuple): str2py, py2str, err_msg = type
    else: str2py, py2str, err_msg = converters.get(type, (type, unicode, None))
    try: return str2py(value)
    except ValidationError: raise
    except:
        if value == '': return None
        raise ValidationError(err_msg or 'Incorrect data')

########NEW FILE########
__FILENAME__ = options
DEBUG = True

STATIC_DIR = None

CUT_TRACEBACK = True

#postprocessing options:
STD_DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
STD_STYLESHEETS = [
    ("/pony/static/blueprint/screen.css", "screen, projection"),
    ("/pony/static/blueprint/print.css", "print"),
    ("/pony/static/blueprint/ie.css.css", "screen, projection", "if IE"),
    ("/pony/static/css/default.css", "screen, projection"),
    ]
BASE_STYLESHEETS_PLACEHOLDER = '<!--PONY-BASE-STYLESHEETS-->'
COMPONENT_STYLESHEETS_PLACEHOLDER = '<!--PONY-COMPONENTS-STYLESHEETS-->'
SCRIPTS_PLACEHOLDER = '<!--PONY-SCRIPTS-->'

# reloading options:
RELOADING_CHECK_INTERVAL = 1.0  # in seconds

# logging options:
LOG_TO_SQLITE = None
LOGGING_LEVEL = None
LOGGING_PONY_LEVEL = None

#auth options:
MAX_SESSION_CTIME = 60*24  # one day
MAX_SESSION_MTIME = 60*2  # 2 hours
MAX_LONGLIFE_SESSION = 14  # 14 days
COOKIE_SERIALIZATION_TYPE = 'json' # may be 'json' or 'pickle'
COOKIE_NAME = 'pony'
COOKIE_PATH = '/'
COOKIE_DOMAIN = None
HASH_ALGORITHM = None  # sha-1 by default
# HASH_ALGORITHM = hashlib.sha512

SESSION_STORAGE = None  # pony.sessionstorage.memcachedstorage by default
# SESSION_STORAGE = mystoragemodule
# SESSION_STORAGE = False  # means use cookies for save session data,
                           # can lead to race conditions

# memcached options (ignored under GAE):
MEMCACHE = None  # Use in-process python version by default
# MEMCACHE = [ "127.0.0.1:11211" ]
# MEMCACHE = MyMemcacheConnectionImplementation(...)
ALTERNATIVE_SESSION_MEMCACHE = None     # Use general memcache connection by default
ALTERNATIVE_ORM_MEMCACHE = None         # Use general memcache connection by default
ALTERNATIVE_TEMPLATING_MEMCACHE = None  # Use general memcache connection by default
ALTERNATIVE_RESPONCE_MEMCACHE = None    # Use general memcache connection by default

# pickle options:
PICKLE_START_OFFSET = 230
PICKLE_HTML_AS_PLAIN_STR = True

# encoding options for pony.pathces.repr
RESTORE_ESCAPES = True
SOURCE_ENCODING = None
CONSOLE_ENCODING = None

# db options
PREFETCHING = True
MAX_FETCH_COUNT = None

# used for select(...).show()
CONSOLE_WIDTH = 80

# sql translator options
SIMPLE_ALIASES = True  # if True just use entity name like "Course-1"
                       # if False use attribute names chain as an alias like "student-grades-course"

INNER_JOIN_SYNTAX = False # put conditions to INNER JOIN ... ON ... or to WHERE ...

# debugging options
DEBUGGING_REMOVE_ADDR = True
DEBUGGING_RESTORE_ESCAPES = True

########NEW FILE########
__FILENAME__ = asttranslation
from compiler import ast
from functools import update_wrapper

from pony.utils import throw

class TranslationError(Exception): pass

class ASTTranslator(object):
    def __init__(translator, tree):
        translator.tree = tree
        translator.pre_methods = {}
        translator.post_methods = {}
    def dispatch(translator, node):
        cls = node.__class__

        try: pre_method = translator.pre_methods[cls]
        except KeyError:
            pre_method = getattr(translator, 'pre' + cls.__name__, translator.default_pre)
            translator.pre_methods[cls] = pre_method
        stop = translator.call(pre_method, node)

        if stop: return

        for child in node.getChildNodes():
            translator.dispatch(child)

        try: post_method = translator.post_methods[cls]
        except KeyError:
            post_method = getattr(translator, 'post' + cls.__name__, translator.default_post)
            translator.post_methods[cls] = post_method
        translator.call(post_method, node)
    def call(translator, method, node):
        return method(node)
    def default_pre(translator, node):
        pass
    def default_post(translator, node):
        pass

def priority(p):
    def decorator(func):
        def new_func(translator, node):
            node.priority = p
            for child in node.getChildNodes():
                if getattr(child, 'priority', 0) >= p: child.src = '(%s)' % child.src
            return func(translator, node)
        return update_wrapper(new_func, func)
    return decorator

def binop_src(op, node):
    return op.join((node.left.src, node.right.src))

def ast2src(tree):
    try: PythonTranslator(tree)
    except NotImplementedError: return repr(tree)
    return tree.src

class PythonTranslator(ASTTranslator):
    def __init__(translator, tree):
        ASTTranslator.__init__(translator, tree)
        translator.dispatch(tree)
    def call(translator, method, node):
        node.src = method(node)
    def default_post(translator, node):
        throw(NotImplementedError, node)
    def postGenExpr(translator, node):
        return '(%s)' % node.code.src
    def postGenExprInner(translator, node):
        return node.expr.src + ' ' + ' '.join(qual.src for qual in node.quals)
    def postGenExprFor(translator, node):
        src = 'for %s in %s' % (node.assign.src, node.iter.src)
        if node.ifs:
            ifs = ' '.join(if_.src for if_ in node.ifs)
            src += ' ' + ifs
        return src
    def postGenExprIf(translator, node):
        return 'if %s' % node.test.src
    @priority(14)
    def postOr(translator, node):
        return ' or '.join(expr.src for expr in node.nodes)
    @priority(13)
    def postAnd(translator, node):
        return ' and '.join(expr.src for expr in node.nodes)
    @priority(12)
    def postNot(translator, node):
        return 'not ' + node.expr.src
    @priority(11)
    def postCompare(translator, node):
        result = [ node.expr.src ]
        for op, expr in node.ops: result.extend((op, expr.src))
        return ' '.join(result)
    @priority(10)
    def postBitor(translator, node):
        return ' | '.join(expr.src for expr in node.nodes)
    @priority(9)
    def postBitxor(translator, node):
        return ' ^ '.join(expr.src for expr in node.nodes)
    @priority(8)
    def postBitand(translator, node):
        return ' & '.join(expr.src for expr in node.nodes)
    @priority(7)
    def postLeftShift(translator, node):
        return binop_src(' << ', node)
    @priority(7)
    def postRightShift(translator, node):
        return binop_src(' >> ', node)
    @priority(6)
    def postAdd(translator, node):
        return binop_src(' + ', node)
    @priority(6)
    def postSub(translator, node):
        return binop_src(' - ', node)
    @priority(5)
    def postMul(translator, node):
        return binop_src(' * ', node)
    @priority(5)
    def postDiv(translator, node):
        return binop_src(' / ', node)
    @priority(5)
    def postMod(translator, node):
        return binop_src(' % ', node)
    @priority(4)
    def postUnarySub(translator, node):
        return '-' + node.expr.src
    @priority(4)
    def postUnaryAdd(translator, node):
        return '+' + node.expr.src
    @priority(4)
    def postInvert(translator, node):
        return '~' + node.expr.src
    @priority(3)
    def postPower(translator, node):
        return binop_src(' ** ', node)
    def postGetattr(translator, node):
        node.priority = 2
        return '.'.join((node.expr.src, node.attrname))
    def postCallFunc(translator, node):
        node.priority = 2
        args = [ arg.src for arg in node.args ]
        if node.star_args: args.append('*'+node.star_args.src)
        if node.dstar_args: args.append('**'+node.dstar_args.src)
        if len(args) == 1 and isinstance(node.args[0], ast.GenExpr):
            return node.node.src + args[0]
        return '%s(%s)' % (node.node.src, ', '.join(args))
    def postSubscript(translator, node):
        node.priority = 2
        if len(node.subs) == 1:
            sub = node.subs[0]
            if isinstance(sub, ast.Const) and type(sub.value) is tuple and len(sub.value) > 1:
                key = sub.src
                assert key.startswith('(') and key.endswith(')')
                key = key[1:-1]
            else: key = sub.src
        else: key = ', '.join([ sub.src for sub in node.subs ])
        return '%s[%s]' % (node.expr.src, key)
    def postSlice(translator, node):
        node.priority = 2
        lower = node.lower is not None and node.lower.src or ''
        upper = node.upper is not None and node.upper.src or ''
        return '%s[%s:%s]' % (node.expr.src, lower, upper)
    def postSliceobj(translator, node):
        return ':'.join(item.src for item in node.nodes)
    def postConst(translator, node):
        node.priority = 1
        value = node.value
        if type(value) is float: # for Python < 2.7
            s = str(value)
            if float(s) == value: return s
        return repr(value)
    def postList(translator, node):
        node.priority = 1
        return '[%s]' % ', '.join(item.src for item in node.nodes)
    def postTuple(translator, node):
        node.priority = 1
        if len(node.nodes) == 1: return '(%s,)' % node.nodes[0].src
        else: return '(%s)' % ', '.join(item.src for item in node.nodes)
    def postAssTuple(translator, node):
        node.priority = 1
        if len(node.nodes) == 1: return '(%s,)' % node.nodes[0].src
        else: return '(%s)' % ', '.join(item.src for item in node.nodes)
    def postDict(translator, node):
        node.priority = 1
        return '{%s}' % ', '.join('%s:%s' % (key.src, value.src) for key, value in node.items)
    def postSet(translator, node):
        node.priority = 1
        return '{%s}' % ', '.join(item.src for item in node.nodes)
    def postBackquote(translator, node):
        node.priority = 1
        return '`%s`' % node.expr.src
    def postName(translator, node):
        node.priority = 1
        return node.name
    def postAssName(translator, node):
        node.priority = 1
        return node.name
    def postKeyword(translator, node):
        return '='.join((node.name, node.expr.src))

nonexternalizable_types = (ast.Keyword, ast.Sliceobj, ast.List, ast.Tuple)

class PreTranslator(ASTTranslator):
    def __init__(translator, tree, additional_internal_names=()):
        ASTTranslator.__init__(translator, tree)
        translator.additional_internal_names = additional_internal_names
        translator.contexts = []
        translator.externals = externals = set()
        translator.dispatch(tree)
        for node in externals.copy():
            if isinstance(node, nonexternalizable_types):
                node.external = False
                externals.remove(node)
                externals.update(node.getChildNodes())
    def dispatch(translator, node):
        node.external = node.constant = False
        ASTTranslator.dispatch(translator, node)
        childs = node.getChildNodes()
        if childs and all(getattr(child, 'external', False) for child in childs):
            node.external = True
        if node.external and not node.constant:
            externals = translator.externals
            externals.difference_update(childs)
            externals.add(node)
    def preGenExprInner(translator, node):
        translator.contexts.append(set())
        dispatch = translator.dispatch
        for i, qual in enumerate(node.quals):
            dispatch(qual.iter)
            dispatch(qual.assign)
            for if_ in qual.ifs: dispatch(if_.test)
        dispatch(node.expr)
        translator.contexts.pop()
        return True
    def preLambda(translator, node):
        if node.varargs or node.kwargs or node.defaults: throw(NotImplementedError)
        translator.contexts.append(set(node.argnames))
        translator.dispatch(node.code)
        translator.contexts.pop()
        return True
    def postAssName(translator, node):
        if node.flags != 'OP_ASSIGN': throw(TypeError)
        name = node.name
        if name.startswith('__'): throw(TranslationError, 'Illegal name: %r' % name)
        translator.contexts[-1].add(name)
    def postName(translator, node):
        name = node.name
        for context in translator.contexts:
            if name in context: return
        if name in ('count', 'random'): return
        node.external = name not in translator.additional_internal_names
    def postConst(translator, node):
        node.external = node.constant = True

extractors_cache = {}

def create_extractors(code_key, tree, filter_num, additional_internal_names=()):
    result = extractors_cache.get(code_key)
    if result is None:
        pretranslator = PreTranslator(tree, additional_internal_names)
        extractors = {}
        for node in pretranslator.externals:
            src = node.src = ast2src(node)
            if src == '.0': code = None
            else: code = compile(src, src, 'eval')
            extractors[filter_num, src] = code
        varnames = list(sorted(extractors))
        result = extractors_cache[code_key] = extractors, varnames, tree
    return result

########NEW FILE########
__FILENAME__ = core
from __future__ import with_statement

import re, sys, types, logging
from compiler import ast, parse
from cPickle import loads, dumps
from operator import attrgetter, itemgetter
from itertools import count as _count, ifilter, ifilterfalse, imap, izip, chain, starmap, repeat
from time import time
import datetime
from random import shuffle, randint
from threading import Lock, currentThread as current_thread, _MainThread
from __builtin__ import min as _min, max as _max, sum as _sum
from contextlib import contextmanager
from collections import defaultdict

import pony
from pony import options
from pony.orm.decompiling import decompile
from pony.orm.ormtypes import AsciiStr, LongStr, LongUnicode, numeric_types, get_normalized_type_of
from pony.orm.asttranslation import create_extractors, TranslationError
from pony.orm.dbapiprovider import (
    DBAPIProvider, DBException, Warning, Error, InterfaceError, DatabaseError, DataError,
    OperationalError, IntegrityError, InternalError, ProgrammingError, NotSupportedError
    )
from pony.utils import (
    localbase, decorator, cut_traceback, throw, get_lambda_args, deprecated, import_module, parse_expr,
    is_ident, count, avg as _avg, distinct as _distinct, tostring, strjoin, concat
    )

__all__ = '''
    pony

    DBException RowNotFound MultipleRowsFound TooManyRowsFound

    Warning Error InterfaceError DatabaseError DataError OperationalError
    IntegrityError InternalError ProgrammingError NotSupportedError

    OrmError ERDiagramError DBSchemaError MappingError
    TableDoesNotExist TableIsNotEmpty ConstraintError CacheIndexError
    ObjectNotFound MultipleObjectsFoundError TooManyObjectsFoundError OperationWithDeletedObjectError
    TransactionError ConnectionClosedError TransactionIntegrityError IsolationError CommitException RollbackException
    UnrepeatableReadError OptimisticCheckError UnresolvableCyclicDependency UnexpectedError DatabaseSessionIsOver

    TranslationError ExprEvalError

    RowNotFound MultipleRowsFound TooManyRowsFound

    Database sql_debug show

    PrimaryKey Required Optional Set Discriminator
    composite_key
    flush commit rollback db_session with_transaction

    AsciiStr LongStr LongUnicode

    select left_join get exists

    count sum min max avg distinct

    desc

    concat

    JOIN
    '''.split()

debug = False
suppress_debug_change = False

def sql_debug(value):
    global debug
    if not suppress_debug_change: debug = value

orm_logger = logging.getLogger('pony.orm')
sql_logger = logging.getLogger('pony.orm.sql')

orm_log_level = logging.INFO

def log_orm(msg):
    if logging.root.handlers:
        orm_logger.log(orm_log_level, msg)
    else:
        print msg

def log_sql(sql, arguments=None):
    if type(arguments) is list:
        sql = 'EXECUTEMANY (%d)\n%s' % (len(arguments), sql)
    if logging.root.handlers:
        sql_logger.log(orm_log_level, sql)  # arguments can hold sensitive information
    else:
        print sql
        if not arguments: pass
        elif type(arguments) is list:
            for args in arguments: print args2str(args)
        else: print args2str(arguments)
        print

def args2str(args):
    if isinstance(args, (tuple, list)):
        return '[%s]' % ', '.join(map(repr, args))
    elif isinstance(args, dict):
        return '{%s}' % ', '.join('%s:%s' % (repr(key), repr(val)) for key, val in sorted(args.iteritems()))

adapted_sql_cache = {}
string2ast_cache = {}

class OrmError(Exception): pass

class ERDiagramError(OrmError): pass
class DBSchemaError(OrmError): pass
class MappingError(OrmError): pass

class TableDoesNotExist(OrmError): pass
class TableIsNotEmpty(OrmError): pass

class ConstraintError(OrmError): pass
class CacheIndexError(OrmError): pass

class RowNotFound(OrmError): pass
class MultipleRowsFound(OrmError): pass
class TooManyRowsFound(OrmError): pass

class ObjectNotFound(OrmError):
    def __init__(exc, entity, pkval):
        if type(pkval) is tuple:
            pkval = ','.join(map(repr, pkval))
        else: pkval = repr(pkval)
        msg = '%s[%s]' % (entity.__name__, pkval)
        OrmError.__init__(exc, msg)
        exc.entity = entity
        exc.pkval = pkval

class MultipleObjectsFoundError(OrmError): pass
class TooManyObjectsFoundError(OrmError): pass
class OperationWithDeletedObjectError(OrmError): pass
class TransactionError(OrmError): pass
class ConnectionClosedError(TransactionError): pass

class TransactionIntegrityError(TransactionError):
    def __init__(exc, msg, original_exc=None):
        Exception.__init__(exc, msg)
        exc.original_exc = original_exc

class CommitException(TransactionError):
    def __init__(exc, msg, exceptions):
        Exception.__init__(exc, msg)
        exc.exceptions = exceptions

class PartialCommitException(TransactionError):
    def __init__(exc, msg, exceptions):
        Exception.__init__(exc, msg)
        exc.exceptions = exceptions

class RollbackException(TransactionError):
    def __init__(exc, msg, exceptions):
        Exception.__init__(exc, msg)
        exc.exceptions = exceptions

class DatabaseSessionIsOver(TransactionError): pass
TransactionRolledBack = DatabaseSessionIsOver

class IsolationError(TransactionError): pass
class   UnrepeatableReadError(IsolationError): pass
class   OptimisticCheckError(IsolationError): pass
class UnresolvableCyclicDependency(TransactionError): pass

class UnexpectedError(TransactionError):
    def __init__(exc, msg, original_exc):
        Exception.__init__(exc, msg)
        exc.original_exc = original_exc

class ExprEvalError(TranslationError):
    def __init__(exc, src, cause):
        assert isinstance(cause, Exception)
        msg = '%s raises %s: %s' % (src, type(cause).__name__, str(cause))
        TranslationError.__init__(exc, msg)
        exc.cause = cause

class OptimizationFailed(Exception):
    pass  # Internal exception, cannot be encountered in user code

###############################################################################

def adapt_sql(sql, paramstyle):
    result = adapted_sql_cache.get((sql, paramstyle))
    if result is not None: return result
    pos = 0
    result = []
    args = []
    kwargs = {}
    if paramstyle in ('format', 'pyformat'): sql = sql.replace('%', '%%')
    while True:
        try: i = sql.index('$', pos)
        except ValueError:
            result.append(sql[pos:])
            break
        result.append(sql[pos:i])
        if sql[i+1] == '$':
            result.append('$')
            pos = i+2
        else:
            try: expr, _ = parse_expr(sql, i+1)
            except ValueError:
                raise # TODO
            pos = i+1 + len(expr)
            if expr.endswith(';'): expr = expr[:-1]
            compile(expr, '<?>', 'eval')  # expr correction check
            if paramstyle == 'qmark':
                args.append(expr)
                result.append('?')
            elif paramstyle == 'format':
                args.append(expr)
                result.append('%s')
            elif paramstyle == 'numeric':
                args.append(expr)
                result.append(':%d' % len(args))
            elif paramstyle == 'named':
                key = 'p%d' % (len(kwargs) + 1)
                kwargs[key] = expr
                result.append(':' + key)
            elif paramstyle == 'pyformat':
                key = 'p%d' % (len(kwargs) + 1)
                kwargs[key] = expr
                result.append('%%(%s)s' % key)
            else: throw(NotImplementedError)
    adapted_sql = ''.join(result)
    if args:
        source = '(%s,)' % ', '.join(args)
        code = compile(source, '<?>', 'eval')
    elif kwargs:
        source = '{%s}' % ','.join('%r:%s' % item for item in kwargs.items())
        code = compile(source, '<?>', 'eval')
    else:
        code = compile('None', '<?>', 'eval')
        if paramstyle in ('format', 'pyformat'): sql = sql.replace('%%', '%')
    result = adapted_sql, code
    adapted_sql_cache[(sql, paramstyle)] = result
    return result

next_num = _count().next

class Local(localbase):
    def __init__(local):
        local.db2cache = {}
        local.db_context_counter = 0
        local.db_session = None

local = Local()

def _get_caches():
    return list(sorted((cache for cache in local.db2cache.values()),
                       reverse=True, key=lambda cache : (cache.database.priority, cache.num)))

@cut_traceback
def flush():
    for cache in _get_caches(): cache.flush()

def reraise(exc_class, exceptions):
    try:
        cls, exc, tb = exceptions[0]
        msg = " ".join(tostring(arg) for arg in exc.args)
        if not issubclass(cls, TransactionError):
            msg = '%s: %s' % (cls.__name__, msg)
        raise exc_class, exc_class(msg, exceptions), tb
    finally: del tb

@cut_traceback
def commit():
    caches = _get_caches()
    if not caches: return
    primary_cache = caches[0]
    other_caches = caches[1:]
    exceptions = []
    try:
        try: primary_cache.commit()
        except:
            exceptions.append(sys.exc_info())
            for cache in other_caches:
                try: cache.rollback()
                except: exceptions.append(sys.exc_info())
            reraise(CommitException, exceptions)
        else:
            for cache in other_caches:
                try: cache.commit()
                except: exceptions.append(sys.exc_info())
            if exceptions:
                reraise(PartialCommitException, exceptions)
    finally:
        del exceptions

@cut_traceback
def rollback():
    exceptions = []
    try:
        for cache in _get_caches():
            try: cache.rollback()
            except: exceptions.append(sys.exc_info())
        if exceptions:
            reraise(RollbackException, exceptions)
        assert not local.db2cache
    finally:
        del exceptions

select_re = re.compile(r'\s*select\b', re.IGNORECASE)

class DBSessionContextManager(object):
    __slots__ = 'retry', 'retry_exceptions', 'allowed_exceptions', 'immediate', 'ddl', 'serializable'
    def __init__(self, retry=0, immediate=False, ddl=False, serializable=False,
                 retry_exceptions=(TransactionError,), allowed_exceptions=()):
        if retry is not 0:
            if type(retry) is not int: throw(TypeError,
                "'retry' parameter of db_session must be of integer type. Got: %s" % type(retry))
            if retry < 0: throw(TypeError,
                "'retry' parameter of db_session must not be negative. Got: %d" % retry)
            if ddl: throw(TypeError, "'ddl' and 'retry' parameters of db_session cannot be used together")
        if not callable(allowed_exceptions) and not callable(retry_exceptions):
            for e in allowed_exceptions:
                if e in retry_exceptions: throw(TypeError,
                    'The same exception %s cannot be specified in both '
                    'allowed and retry exception lists simultaneously' % e.__name__)
        self.retry = retry
        self.ddl = ddl
        self.serializable = serializable
        self.immediate = immediate or ddl or serializable
        self.retry_exceptions = retry_exceptions
        self.allowed_exceptions = allowed_exceptions
    def __call__(self, *args, **kwargs):
        if not args and not kwargs: return self
        if len(args) > 1: throw(TypeError,
            'Pass only keyword arguments to db_session or use db_session as decorator')
        if not args: return self.__class__(**kwargs)
        if kwargs: throw(TypeError,
            'Pass only keyword arguments to db_session or use db_session as decorator')
        func = args[0]
        def new_func(func, *args, **kwargs):
            if self.ddl and local.db_context_counter:
                if isinstance(func, types.FunctionType): func = func.__name__ + '()'
                throw(TransactionError, '%s cannot be called inside of db_session' % func)
            exc_tb = None
            try:
                for i in xrange(self.retry+1):
                    self._enter()
                    exc_type = exc_value = exc_tb = None
                    try:
                        try: return func(*args, **kwargs)
                        except Exception:
                            exc_type, exc_value, exc_tb = sys.exc_info()  # exc_value can be None in Python 2.6
                            retry_exceptions = self.retry_exceptions
                            if not callable(retry_exceptions):
                                do_retry = issubclass(exc_type, tuple(retry_exceptions))
                            else:
                                do_retry = exc_value is not None and retry_exceptions(exc_value)
                            if not do_retry: raise
                    finally: self.__exit__(exc_type, exc_value, exc_tb)
                raise exc_type, exc_value, exc_tb
            finally: del exc_tb
        return decorator(new_func, func)
    def __enter__(self):
        if self.retry is not 0: throw(TypeError,
            "@db_session can accept 'retry' parameter only when used as decorator and not as context manager")
        if self.ddl: throw(TypeError,
            "@db_session can accept 'ddl' parameter only when used as decorator and not as context manager")
        self._enter()
    def _enter(self):
        if local.db_session is None:
            assert not local.db_context_counter
            local.db_session = self
        elif self.serializable and not local.db_session.serializable: throw(TransactionError,
            'Cannot start serializable transaction inside non-serializable transaction')
        local.db_context_counter += 1
    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        local.db_context_counter -= 1
        if local.db_context_counter: return
        assert local.db_session is self
        try:
            if exc_type is None: can_commit = True
            elif not callable(self.allowed_exceptions):
                can_commit = issubclass(exc_type, tuple(self.allowed_exceptions))
            else:
                # exc_value can be None in Python 2.6 even if exc_type is not None
                try: can_commit = exc_value is not None and self.allowed_exceptions(exc_value)
                except:
                    rollback()
                    raise
            if can_commit:
                commit()
                for cache in _get_caches(): cache.release()
                assert not local.db2cache
            else: rollback()
        finally: local.db_session = None

db_session = DBSessionContextManager()

def with_transaction(*args, **kwargs):
    deprecated(3, "@with_transaction decorator is deprecated, use @db_session decorator instead")
    return db_session(*args, **kwargs)

@decorator
def db_decorator(func, *args, **kwargs):
    web = sys.modules.get('pony.web')
    allowed_exceptions = web and [ web.HttpRedirect ] or []
    try:
        with db_session(allowed_exceptions=allowed_exceptions):
            return func(*args, **kwargs)
    except (ObjectNotFound, RowNotFound):
        if web: throw(web.Http404NotFound)
        raise

class Database(object):
    def __deepcopy__(self, memo):
        return self  # Database cannot be cloned by deepcopy()
    @cut_traceback
    def __init__(self, *args, **kwargs):
        # argument 'self' cannot be named 'database', because 'database' can be in kwargs
        self.priority = 0
        self._insert_cache = {}

        # ER-diagram related stuff:
        self._translator_cache = {}
        self._constructed_sql_cache = {}
        self.entities = {}
        self.schema = None
        self.Entity = type.__new__(EntityMeta, 'Entity', (Entity,), {})
        self.Entity._database_ = self

        # Statistics-related stuff:
        self.global_stats = {}
        self.global_stats_lock = Lock()
        self._dblocal = DbLocal()

        self.provider = None
        if args or kwargs: self._bind(*args, **kwargs)
    @cut_traceback
    def bind(self, *args, **kwargs):
        self._bind(*args, **kwargs)
    def _bind(self, *args, **kwargs):
        # argument 'self' cannot be named 'database', because 'database' can be in kwargs
        if self.provider is not None:
            throw(TypeError, 'Database object was already bound to %s provider' % self.provider.dialect)
        if not args:
            throw(TypeError, 'Database provider should be specified as a first positional argument')
        provider, args = args[0], args[1:]
        if isinstance(provider, type) and issubclass(provider, DBAPIProvider):
            provider_cls = provider
        else:
            if not isinstance(provider, basestring): throw(TypeError)
            if provider == 'pygresql': throw(TypeError,
                'Pony no longer supports PyGreSQL module. Please use psycopg2 instead.')
            provider_module = import_module('pony.orm.dbproviders.' + provider)
            provider_cls = provider_module.provider_cls
        self.provider = provider = provider_cls(*args, **kwargs)
    @property
    def last_sql(database):
        return database._dblocal.last_sql
    @property
    def local_stats(database):
        return database._dblocal.stats
    def _update_local_stat(database, sql, query_start_time):
        dblocal = database._dblocal
        dblocal.last_sql = sql
        stats = dblocal.stats
        stat = stats.get(sql)
        if stat is not None: stat.query_executed(query_start_time)
        else: stats[sql] = QueryStat(sql, query_start_time)
    def merge_local_stats(database):
        setdefault = database.global_stats.setdefault
        database.global_stats_lock.acquire()
        try:
            for sql, stat in database._dblocal.stats.iteritems():
                global_stat = setdefault(sql, stat)
                if global_stat is not stat: global_stat.merge(stat)
        finally: database.global_stats_lock.release()
        database._dblocal.stats.clear()
    @cut_traceback
    def get_connection(database):
        cache = database._get_cache()
        if not cache.in_transaction:
            cache.immediate = True
            cache.prepare_connection_for_query_execution()
            cache.in_transaction = True
        connection = cache.connection
        assert connection is not None
        return connection
    @cut_traceback
    def disconnect(database):
        provider = database.provider
        if provider is None: return
        if local.db_context_counter: throw(TransactionError, 'disconnect() cannot be called inside of db_sesison')
        cache = local.db2cache.get(database)
        if cache is not None: cache.rollback()
        provider.disconnect()
    def _get_cache(database):
        if database.provider is None: throw(MappingError, 'Database object is not bound with a provider yet')
        cache = local.db2cache.get(database)
        if cache is not None: return cache
        if not local.db_context_counter and not (
                pony.MODE == 'INTERACTIVE' and current_thread().__class__ is _MainThread
            ): throw(TransactionError, 'db_session is required when working with the database')
        cache = local.db2cache[database] = SessionCache(database)
        return cache
    @cut_traceback
    def flush(database):
        database._get_cache().flush()
    @cut_traceback
    def commit(database):
        cache = local.db2cache.get(database)
        if cache is not None: cache.commit()
    @cut_traceback
    def rollback(database):
        cache = local.db2cache.get(database)
        if cache is not None: cache.rollback()
    @cut_traceback
    def execute(database, sql, globals=None, locals=None):
        return database._exec_raw_sql(sql, globals, locals, frame_depth=3)
    def _exec_raw_sql(database, sql, globals, locals, frame_depth):
        provider = database.provider
        if provider is None: throw(MappingError, 'Database object is not bound with a provider yet')
        sql = sql[:]  # sql = templating.plainstr(sql)
        if globals is None:
            assert locals is None
            frame_depth += 1
            globals = sys._getframe(frame_depth).f_globals
            locals = sys._getframe(frame_depth).f_locals
        adapted_sql, code = adapt_sql(sql, provider.paramstyle)
        arguments = eval(code, globals, locals)
        return database._exec_sql(adapted_sql, arguments)
    @cut_traceback
    def select(database, sql, globals=None, locals=None, frame_depth=0):
        if not select_re.match(sql): sql = 'select ' + sql
        cursor = database._exec_raw_sql(sql, globals, locals, frame_depth + 3)
        max_fetch_count = options.MAX_FETCH_COUNT
        if max_fetch_count is not None:
            result = cursor.fetchmany(max_fetch_count)
            if cursor.fetchone() is not None: throw(TooManyRowsFound)
        else: result = cursor.fetchall()
        if len(cursor.description) == 1: return map(itemgetter(0), result)
        row_class = type("row", (tuple,), {})
        for i, column_info in enumerate(cursor.description):
            column_name = column_info[0]
            if not is_ident(column_name): continue
            if hasattr(tuple, column_name) and column_name.startswith('__'): continue
            setattr(row_class, column_name, property(itemgetter(i)))
        return [ row_class(row) for row in result ]
    @cut_traceback
    def get(database, sql, globals=None, locals=None):
        rows = database.select(sql, globals, locals, frame_depth=3)
        if not rows: throw(RowNotFound)
        if len(rows) > 1: throw(MultipleRowsFound)
        row = rows[0]
        return row
    @cut_traceback
    def exists(database, sql, globals=None, locals=None):
        if not select_re.match(sql): sql = 'select ' + sql
        cursor = database._exec_raw_sql(sql, globals, locals, frame_depth=3)
        result = cursor.fetchone()
        return bool(result)
    @cut_traceback
    def insert(database, table_name, returning=None, **kwargs):
        if database.provider is None: throw(MappingError, 'Database object is not bound with a provider yet')
        table_name = table_name[:]  # table_name = templating.plainstr(table_name)
        query_key = (table_name,) + tuple(kwargs)  # keys are not sorted deliberately!!
        if returning is not None: query_key = query_key + (returning,)
        cached_sql = database._insert_cache.get(query_key)
        if cached_sql is None:
            ast = [ 'INSERT', table_name, kwargs.keys(),
                    [ [ 'PARAM', (i, None, None) ] for i in xrange(len(kwargs)) ], returning ]
            sql, adapter = database._ast2sql(ast)
            cached_sql = sql, adapter
            database._insert_cache[query_key] = cached_sql
        else: sql, adapter = cached_sql
        arguments = adapter(kwargs.values())  # order of values same as order of keys
        if returning is not None:
            return database._exec_sql(sql, arguments, returning_id=True)
        cursor = database._exec_sql(sql, arguments)
        return getattr(cursor, 'lastrowid', None)
    def _ast2sql(database, sql_ast):
        sql, adapter = database.provider.ast2sql(sql_ast)
        return sql, adapter
    def _exec_sql(database, sql, arguments=None, returning_id=False):
        cache = database._get_cache()
        connection = cache.prepare_connection_for_query_execution()
        cursor = connection.cursor()
        if debug: log_sql(sql, arguments)
        provider = database.provider
        t = time()
        try: new_id = provider.execute(cursor, sql, arguments, returning_id)
        except Exception, e:
            connection = cache.reconnect(e)
            cursor = connection.cursor()
            if debug: log_sql(sql, arguments)
            t = time()
            new_id = provider.execute(cursor, sql, arguments, returning_id)
        if cache.immediate: cache.in_transaction = True
        database._update_local_stat(sql, t)
        if not returning_id: return cursor
        if type(new_id) is long: new_id = int(new_id)
        return new_id
    @cut_traceback
    def generate_mapping(database, filename=None, check_tables=True, create_tables=False):
        provider = database.provider
        if provider is None: throw(MappingError, 'Database object is not bound with a provider yet')
        if database.schema: throw(MappingError, 'Mapping was already generated')
        if filename is not None: throw(NotImplementedError)
        schema = database.schema = provider.dbschema_cls(provider)
        entities = list(sorted(database.entities.values(), key=attrgetter('_id_')))
        for entity in entities:
            entity._resolve_attr_types_()
        for entity in entities:
            entity._link_reverse_attrs_()

        def get_columns(table, column_names):
            return tuple(map(table.column_dict.__getitem__, column_names))

        for entity in entities:
            entity._get_pk_columns_()
            table_name = entity._table_

            is_subclass = entity._root_ is not entity
            if is_subclass:
                if table_name is not None: throw(NotImplementedError)
                table_name = entity._root_._table_
                entity._table_ = table_name
            elif table_name is None:
                table_name = provider.get_default_entity_table_name(entity)
                entity._table_ = table_name
            else: assert isinstance(table_name, (basestring, tuple))

            table = schema.tables.get(table_name)
            if table is None: table = schema.add_table(table_name)
            elif table.entities:
                for e in table.entities:
                    if e._root_ is not entity._root_:
                        throw(MappingError, "Entities %s and %s cannot be mapped to table %s "
                                           "because they don't belong to the same hierarchy"
                                           % (e, entity, table_name))
            table.entities.add(entity)

            for attr in entity._new_attrs_:
                if attr.is_collection:
                    if not isinstance(attr, Set): throw(NotImplementedError)
                    reverse = attr.reverse
                    if not reverse.is_collection: # many-to-one:
                        if attr.table is not None: throw(MappingError,
                            "Parameter 'table' is not allowed for many-to-one attribute %s" % attr)
                        elif attr.columns: throw(NotImplementedError,
                            "Parameter 'column' is not allowed for many-to-one attribute %s" % attr)
                        continue
                    # many-to-many:
                    if not isinstance(reverse, Set): throw(NotImplementedError)
                    if attr.entity.__name__ > reverse.entity.__name__: continue
                    if attr.entity is reverse.entity and attr.name > reverse.name: continue

                    if attr.table:
                        if not reverse.table: reverse.table = attr.table
                        elif reverse.table != attr.table:
                            throw(MappingError, "Parameter 'table' for %s and %s do not match" % (attr, reverse))
                        table_name = attr.table
                    elif reverse.table: table_name = attr.table = reverse.table
                    else:
                        table_name = provider.get_default_m2m_table_name(attr, reverse)

                    m2m_table = schema.tables.get(table_name)
                    if m2m_table is not None:
                        if not attr.table:
                            seq = _count(2)
                            while m2m_table is not None:
                                new_table_name = table_name + '_%d' % seq.next()
                                m2m_table = schema.tables.get(new_table_name)
                            table_name = new_table_name
                        elif m2m_table.entities or m2m_table.m2m:
                            if isinstance(table_name, tuple): table_name = '.'.join(table_name)
                            throw(MappingError, "Table name '%s' is already in use" % table_name)
                        else: throw(NotImplementedError)
                    attr.table = reverse.table = table_name
                    m2m_table = schema.add_table(table_name)
                    m2m_columns_1 = attr.get_m2m_columns(is_reverse=False)
                    m2m_columns_2 = reverse.get_m2m_columns(is_reverse=True)
                    if m2m_columns_1 == m2m_columns_2: throw(MappingError,
                        'Different column names should be specified for attributes %s and %s' % (attr, reverse))
                    if attr.symmetric and len(attr.reverse_columns) != len(attr.entity._pk_attrs_):
                        throw(MappingError, "Invalid number of reverse columns for symmetric attribute %s" % attr)
                    assert len(m2m_columns_1) == len(reverse.converters)
                    assert len(m2m_columns_2) == len(attr.converters)
                    for column_name, converter in zip(m2m_columns_1 + m2m_columns_2, reverse.converters + attr.converters):
                        m2m_table.add_column(column_name, converter.sql_type(), converter, True)
                    m2m_table.add_index(None, tuple(m2m_table.column_list), is_pk=True)
                    m2m_table.m2m.add(attr)
                    m2m_table.m2m.add(reverse)
                else:
                    if attr.is_required: pass
                    elif not attr.is_string:
                        if attr.nullable is False:
                            throw(TypeError, 'Optional attribute with non-string type %s must be nullable' % attr)
                        attr.nullable = True
                    elif entity._database_.provider.dialect == 'Oracle':
                        if attr.nullable is False: throw(ERDiagramError,
                            'In Oracle, optional string attribute %s must be nullable' % attr)
                        attr.nullable = True

                    columns = attr.get_columns()  # initializes attr.converters
                    if not attr.reverse and attr.default is not None:
                        assert len(attr.converters) == 1
                        if not callable(attr.default): attr.default = attr.check(attr.default)
                    assert len(columns) == len(attr.converters)
                    if len(columns) == 1:
                        converter = attr.converters[0]
                        sql_type = attr.sql_type or converter.sql_type()
                        table.add_column(columns[0], sql_type, converter, not attr.nullable, attr.sql_default)
                    else:
                        if attr.sql_type is not None: throw(NotImplementedError,
                            'sql_type cannot be specified for composite attribute %s' % attr)
                        for (column_name, converter) in zip(columns, attr.converters):
                            table.add_column(column_name, converter.sql_type(), converter, not attr.nullable)
            entity._attrs_with_columns_ = [ attr for attr in entity._attrs_
                                                 if not attr.is_collection and attr.columns ]
            if not table.pk_index:
                if len(entity._pk_columns_) == 1 and entity._pk_attrs_[0].auto: is_pk = "auto"
                else: is_pk = True
                table.add_index(None, get_columns(table, entity._pk_columns_), is_pk)
            for key in entity._keys_:
                column_names = []
                for attr in key: column_names.extend(attr.columns)
                if len(key) == 1: index_name = key[0].index
                else: index_name = None
                table.add_index(index_name, get_columns(table, column_names), is_unique=True)
            columns = []
            columns_without_pk = []
            converters = []
            converters_without_pk = []
            for attr in entity._attrs_with_columns_:
                columns.extend(attr.columns)  # todo: inheritance
                converters.extend(attr.converters)
                if not attr.is_pk:
                    columns_without_pk.extend(attr.columns)
                    converters_without_pk.extend(attr.converters)
            entity._columns_ = columns
            entity._columns_without_pk_ = columns_without_pk
            entity._converters_ = converters
            entity._converters_without_pk_ = converters_without_pk
        for entity in entities:
            table = schema.tables[entity._table_]
            for attr in entity._new_attrs_:
                if attr.is_collection:
                    reverse = attr.reverse
                    if not reverse.is_collection: continue
                    if not isinstance(attr, Set): throw(NotImplementedError)
                    if not isinstance(reverse, Set): throw(NotImplementedError)
                    m2m_table = schema.tables[attr.table]
                    parent_columns = get_columns(table, entity._pk_columns_)
                    child_columns = get_columns(m2m_table, reverse.columns)
                    m2m_table.add_foreign_key(None, child_columns, table, parent_columns, attr.index)
                    if attr.symmetric:
                        child_columns = get_columns(m2m_table, attr.reverse_columns)
                        m2m_table.add_foreign_key(None, child_columns, table, parent_columns)
                elif attr.reverse and attr.columns:
                    rentity = attr.reverse.entity
                    parent_table = schema.tables[rentity._table_]
                    parent_columns = get_columns(parent_table, rentity._pk_columns_)
                    child_columns = get_columns(table, attr.columns)
                    table.add_foreign_key(None, child_columns, parent_table, parent_columns, attr.index)
                elif attr.index and attr.columns:
                    columns = tuple(map(table.column_dict.__getitem__, attr.columns))
                    table.add_index(attr.index, columns, is_unique=attr.is_unique)

        if create_tables: database.create_tables(check_tables)
        elif check_tables: database.check_tables()
    @cut_traceback
    @db_session(ddl=True)
    def drop_table(database, table_name, if_exists=False, with_all_data=False):
        if isinstance(table_name, EntityMeta):
            entity = table_name
            table_name = entity._table_
        elif isinstance(table_name, Set):
            attr = table_name
            if attr.reverse.is_collection: table_name = attr.table
            else: table_name = attr.entity._table_
        elif isinstance(table_name, Attribute): throw(TypeError,
            "Attribute %s is not Set and doesn't have corresponding table" % table_name)
        database._drop_tables([ table_name ], if_exists, with_all_data, try_normalized=True)
    @cut_traceback
    @db_session(ddl=True)
    def drop_all_tables(database, with_all_data=False):
        if database.schema is None: throw(ERDiagramError, 'No mapping was generated for the database')
        database._drop_tables(database.schema.tables, True, with_all_data)
    def _drop_tables(database, table_names, if_exists, with_all_data, try_normalized=False):
        cache = database._get_cache()
        connection = cache.prepare_connection_for_query_execution()
        provider = database.provider
        existed_tables = []
        for table_name in table_names:
            if table_name is None:
                if database.schema is None: throw(MappingError, 'No mapping was generated for the database')
                else: throw(TypeError, 'Table name cannot be None')
            if provider.table_exists(connection, table_name): existed_tables.append(table_name)
            elif not if_exists:
                if try_normalized:
                    normalized_table_name = provider.normalize_name(table_name)
                    if normalized_table_name != table_name \
                    and provider.table_exists(connection, normalized_table_name):
                        throw(TableDoesNotExist, 'Table %s does not exist (probably you meant table %s)'
                                                 % (table_name, normalized_table_name))
                throw(TableDoesNotExist, 'Table %s does not exist' % table_name)
        if not with_all_data:
            for table_name in existed_tables:
                if provider.table_has_data(connection, table_name): throw(TableIsNotEmpty,
                    'Cannot drop table %s because it is not empty. Specify option '
                    'with_all_data=True if you want to drop table with all data' % table_name)
        for table_name in existed_tables:
            if debug: log_orm('DROPPING TABLE %s' % table_name)
            provider.drop_table(connection, table_name)
    @cut_traceback
    @db_session(ddl=True)
    def create_tables(database, check_tables=False):
        cache = database._get_cache()
        if database.schema is None: throw(MappingError, 'No mapping was generated for the database')
        connection = cache.prepare_connection_for_query_execution()
        database.schema.create_tables(database.provider, connection)
        if check_tables: database.schema.check_tables(database.provider, connection)
    @db_session()
    def check_tables(database):
        cache = database._get_cache()
        if database.schema is None: throw(MappingError, 'No mapping was generated for the database')
        connection = cache.prepare_connection_for_query_execution()
        database.schema.check_tables(database.provider, connection)

class DbLocal(localbase):
    def __init__(dblocal):
        dblocal.stats = {}
        dblocal.last_sql = None

class QueryStat(object):
    def __init__(stat, sql, query_start_time=None):
        if query_start_time is not None:
            query_end_time = time()
            duration = query_end_time - query_start_time
            stat.min_time = stat.max_time = stat.sum_time = duration
            stat.db_count = 1
            stat.cache_count = 0
        else:
            stat.min_time = stat.max_time = stat.sum_time = None
            stat.db_count = 0
            stat.cache_count = 1
        stat.sql = sql
    def query_executed(stat, query_start_time):
        query_end_time = time()
        duration = query_end_time - query_start_time
        if stat.db_count:
            stat.min_time = _min(stat.min_time, duration)
            stat.max_time = _max(stat.max_time, duration)
            stat.sum_time += duration
        else: stat.min_time = stat.max_time = stat.sum_time = duration
        stat.db_count += 1
    def merge(stat, stat2):
        assert stat.sql == stat2.sql
        if not stat2.db_count: pass
        elif stat.db_count:
            stat.min_time = _min(stat.min_time, stat2.min_time)
            stat.max_time = _max(stat.max_time, stat2.max_time)
            stat.sum_time += stat2.sum_time
        else:
            stat.min_time = stat2.min_time
            stat.max_time = stat2.max_time
            stat.sum_time = stat2.sum_time
        stat.db_count += stat2.db_count
        stat.cache_count += stat2.cache_count
    @property
    def avg_time(stat):
        if not stat.db_count: return None
        return stat.sum_time / stat.db_count

class SessionCache(object):
    def __init__(cache, database):
        cache.is_alive = True
        cache.num = next_num()
        cache.database = database
        cache.indexes = defaultdict(dict)
        cache.seeds = defaultdict(set)
        cache.max_id_cache = {}
        cache.collection_statistics = {}
        cache.for_update = set()
        cache.noflush_counter = 0
        cache.modified_collections = defaultdict(set)
        cache.objects_to_save = []
        cache.query_results = {}
        cache.modified = False
        db_session = local.db_session
        cache.db_session = db_session
        cache.immediate = db_session is not None and db_session.immediate
        cache.connection = None
        cache.in_transaction = False
        cache.saved_fk_state = None
    def connect(cache):
        assert cache.connection is None
        if cache.in_transaction: throw(ConnectionClosedError,
            'Transaction cannot be continued because database connection failed')
        provider = cache.database.provider
        connection = provider.connect()
        try: provider.set_transaction_mode(connection, cache)  # can set cache.in_transaction
        except:
            provider.drop(connection)
            raise
        cache.connection = connection
        return connection
    def reconnect(cache, exc):
        provider = cache.database.provider
        if exc is not None:
            exc = getattr(exc, 'original_exc', exc)
            if not provider.should_reconnect(exc): raise
            if debug: log_orm('CONNECTION FAILED: %s' % exc)
            connection = cache.connection
            assert connection is not None
            cache.connection = None
            provider.drop(connection)
        else: assert cache.connection is None
        return cache.connect()
    def prepare_connection_for_query_execution(cache):
        db_session = local.db_session
        if db_session is not None and cache.db_session is None:
            # This situation can arise when a transaction was started
            # in the interactive mode, outside of the db_session
            if cache.in_transaction or cache.modified:
                local.db_session = None
                try: cache.commit()
                finally: local.db_session = db_session
            cache.db_session = db_session
            cache.immediate = cache.immediate or db_session.immediate
        else: assert cache.db_session is db_session, (cache.db_session, db_session)
        connection = cache.connection
        if connection is None: connection = cache.connect()
        elif cache.immediate and not cache.in_transaction:
            provider = cache.database.provider
            try: provider.set_transaction_mode(connection, cache)  # can set cache.in_transaction
            except Exception, e: connection = cache.reconnect(e)
        if not cache.noflush_counter and cache.modified: cache.flush()
        return connection
    def commit(cache):
        assert cache.is_alive
        database = cache.database
        provider = database.provider
        try:
            if cache.modified: cache.flush()
            if cache.in_transaction:
                assert cache.connection is not None
                provider.commit(cache.connection)
                cache.in_transaction = False
            cache.for_update.clear()
            cache.immediate = True
        except:
            cache.rollback()
            raise
    def rollback(cache):
        assert cache.is_alive
        database = cache.database
        x = local.db2cache.pop(database); assert x is cache
        cache.is_alive = False
        provider = database.provider
        connection = cache.connection
        if connection is None: return
        cache.connection = None
        try: provider.rollback(connection)
        except:
            provider.drop(connection)
            raise
        else: provider.release(connection, cache)
    def release(cache):
        assert cache.is_alive and not cache.in_transaction
        database = cache.database
        x = local.db2cache.pop(database); assert x is cache
        cache.is_alive = False
        provider = database.provider
        connection = cache.connection
        if connection is None: return
        cache.connection = None
        provider.release(connection, cache)
    def close(cache):
        assert cache.is_alive and not cache.in_transaction
        database = cache.database
        x = local.db2cache.pop(database); assert x is cache
        cache.is_alive = False
        provider = database.provider
        connection = cache.connection
        if connection is None: return
        cache.connection = None
        provider.drop(connection)
    @contextmanager
    def flush_disabled(cache):
        cache.noflush_counter += 1
        try: yield
        finally: cache.noflush_counter -= 1
    def flush(cache):
        if cache.noflush_counter: return
        assert cache.is_alive
        if not cache.immediate: cache.immediate = True
        if not cache.modified: return

        for obj in cache.objects_to_save:  # can grow during iteration
            if obj is not None: obj._before_save_()

        with cache.flush_disabled():
            cache.query_results.clear()
            modified_m2m = cache._calc_modified_m2m()
            for attr, (added, removed) in modified_m2m.iteritems():
                if not removed: continue
                attr.remove_m2m(removed)
            for obj in cache.objects_to_save:
                if obj is not None: obj._save_()
            for attr, (added, removed) in modified_m2m.iteritems():
                if not added: continue
                attr.add_m2m(added)
        cache.max_id_cache.clear()
        cache.modified_collections.clear()
        cache.objects_to_save[:] = []
        cache.modified = False
    def _calc_modified_m2m(cache):
        modified_m2m = {}
        for attr, objects in sorted(cache.modified_collections.iteritems(),
                                    key=lambda (attr, objects): (attr.entity.__name__, attr.name)):
            if not isinstance(attr, Set): throw(NotImplementedError)
            reverse = attr.reverse
            if not reverse.is_collection:
                for obj in objects:
                    setdata = obj._vals_[attr]
                    setdata.added = setdata.removed = None
                continue

            if not isinstance(reverse, Set): throw(NotImplementedError)
            if reverse in modified_m2m: continue
            added, removed = modified_m2m.setdefault(attr, (set(), set()))
            for obj in objects:
                setdata = obj._vals_[attr]
                if setdata.added:
                    for obj2 in setdata.added: added.add((obj, obj2))
                if setdata.removed:
                    for obj2 in setdata.removed: removed.add((obj, obj2))
                if obj._status_ == 'marked_to_delete': del obj._vals_[attr]
                else: setdata.added = setdata.removed = None
        cache.modified_collections.clear()
        return modified_m2m
    def update_simple_index(cache, obj, attr, old_val, new_val, undo):
        assert old_val != new_val
        index = cache.indexes[attr]
        if new_val is not None:
            obj2 = index.setdefault(new_val, obj)
            if obj2 is not obj: throw(CacheIndexError, 'Cannot update %s.%s: %s with key %s already exists'
                                                 % (obj.__class__.__name__, attr.name, obj2, new_val))
        if old_val is not None: del index[old_val]
        undo.append((index, old_val, new_val))
    def db_update_simple_index(cache, obj, attr, old_dbval, new_dbval):
        assert old_dbval != new_dbval
        index = cache.indexes[attr]
        if new_dbval is not None:
            obj2 = index.setdefault(new_dbval, obj)
            if obj2 is not obj: throw(TransactionIntegrityError,
                '%s with unique index %s.%s already exists: %s'
                % (obj2.__class__.__name__, obj.__class__.__name__, attr.name, new_dbval))
                # attribute which was created or updated lately clashes with one stored in database
        index.pop(old_dbval, None)
    def update_composite_index(cache, obj, attrs, prev_vals, new_vals, undo):
        if None in prev_vals: prev_vals = None
        if None in new_vals: new_vals = None
        if prev_vals is None and new_vals is None: return
        index = cache.indexes[attrs]
        if new_vals is not None:
            obj2 = index.setdefault(new_vals, obj)
            if obj2 is not obj:
                attr_names = ', '.join(attr.name for attr in attrs)
                throw(CacheIndexError, 'Cannot update %r: composite key (%s) with value %s already exists for %r'
                                 % (obj, attr_names, new_vals, obj2))
        if prev_vals is not None: del index[prev_vals]
        undo.append((index, prev_vals, new_vals))
    def db_update_composite_index(cache, obj, attrs, prev_vals, new_vals):
        index = cache.indexes[attrs]
        if None not in new_vals:
            obj2 = index.setdefault(new_vals, obj)
            if obj2 is not obj:
                key_str = ', '.join(repr(item) for item in new_vals)
                throw(TransactionIntegrityError, '%s with unique index (%s) already exists: %s'
                                 % (obj2.__class__.__name__, ', '.join(attr.name for attr in attrs), key_str))
        index.pop(prev_vals, None)

###############################################################################

class NotLoadedValueType(object):
    def __repr__(self): return 'NOT_LOADED'

NOT_LOADED = NotLoadedValueType()

class DefaultValueType(object):
    def __repr__(self): return 'DEFAULT'

DEFAULT = DefaultValueType()

class DescWrapper(object):
    def __init__(self, attr):
        self.attr = attr
    def __repr__(self):
        return '<DescWrapper(%s)>' % self.attr
    def __call__(self):
        return self
    def __eq__(self, other):
        return type(other) is DescWrapper and self.attr == other.attr
    def __ne__(self, other):
        return type(other) is not DescWrapper or self.attr != other.attr
    def __hash__(self):
        return hash(self.attr) + 1

next_attr_id = _count(1).next

class Attribute(object):
    __slots__ = 'nullable', 'is_required', 'is_discriminator', 'is_unique', 'is_part_of_unique_index', \
                'is_pk', 'is_collection', 'is_relation', 'is_basic', 'is_string', 'is_volatile', \
                'id', 'pk_offset', 'pk_columns_offset', 'py_type', 'sql_type', 'entity', 'name', \
                'lazy', 'lazy_sql_cache', 'args', 'auto', 'default', 'reverse', 'composite_keys', \
                'column', 'columns', 'col_paths', '_columns_checked', 'converters', 'kwargs', \
                'cascade_delete', 'index', 'original_default', 'sql_default'
    def __deepcopy__(attr, memo):
        return attr  # Attribute cannot be cloned by deepcopy()
    @cut_traceback
    def __init__(attr, py_type, *args, **kwargs):
        if attr.__class__ is Attribute: throw(TypeError, "'Attribute' is abstract type")
        attr.is_required = isinstance(attr, Required)
        attr.is_discriminator = isinstance(attr, Discriminator)
        attr.is_unique = kwargs.pop('unique', None)
        if isinstance(attr, PrimaryKey):
            if attr.is_unique is not None:
                throw(TypeError, "'unique' option cannot be set for PrimaryKey attribute ")
            attr.is_unique = True
        attr.nullable = kwargs.pop('nullable', None)
        attr.is_part_of_unique_index = attr.is_unique  # Also can be set to True later
        attr.is_pk = isinstance(attr, PrimaryKey)
        if attr.is_pk: attr.pk_offset = 0
        else: attr.pk_offset = None
        attr.id = next_attr_id()
        if not isinstance(py_type, (type, basestring, types.FunctionType)):
            if py_type is datetime: throw(TypeError,
                'datetime is the module and cannot be used as attribute type. Use datetime.datetime instead')
            throw(TypeError, 'Incorrect type of attribute: %r' % py_type)
        attr.py_type = py_type
        attr.is_string = type(py_type) is type and issubclass(py_type, basestring)
        attr.is_collection = isinstance(attr, Collection)
        attr.is_relation = isinstance(attr.py_type, (EntityMeta, basestring, types.FunctionType))
        attr.is_basic = not attr.is_collection and not attr.is_relation
        attr.sql_type = kwargs.pop('sql_type', None)
        attr.entity = attr.name = None
        attr.args = args
        attr.auto = kwargs.pop('auto', False)
        attr.cascade_delete = kwargs.pop('cascade_delete', None)

        attr.reverse = kwargs.pop('reverse', None)
        if not attr.reverse: pass
        elif not isinstance(attr.reverse, (basestring, Attribute)):
            throw(TypeError, "Value of 'reverse' option must be name of reverse attribute). Got: %r" % attr.reverse)
        elif not attr.is_relation:
            throw(TypeError, 'Reverse option cannot be set for this type: %r' % attr.py_type)

        attr.column = kwargs.pop('column', None)
        attr.columns = kwargs.pop('columns', None)
        if attr.column is not None:
            if attr.columns is not None:
                throw(TypeError, "Parameters 'column' and 'columns' cannot be specified simultaneously")
            if not isinstance(attr.column, basestring):
                throw(TypeError, "Parameter 'column' must be a string. Got: %r" % attr.column)
            attr.columns = [ attr.column ]
        elif attr.columns is not None:
            if not isinstance(attr.columns, (tuple, list)):
                throw(TypeError, "Parameter 'columns' must be a list. Got: %r'" % attr.columns)
            for column in attr.columns:
                if not isinstance(column, basestring):
                    throw(TypeError, "Items of parameter 'columns' must be strings. Got: %r" % attr.columns)
            if len(attr.columns) == 1: attr.column = attr.columns[0]
        else: attr.columns = []
        attr.index = kwargs.pop('index', None)
        attr.col_paths = []
        attr._columns_checked = False
        attr.composite_keys = []
        attr.lazy = kwargs.pop('lazy', getattr(py_type, 'lazy', False))
        attr.lazy_sql_cache = None
        attr.is_volatile = kwargs.pop('volatile', False)
        attr.sql_default = kwargs.pop('sql_default', None)
        attr.kwargs = kwargs
        attr.converters = []
    def _init_(attr, entity, name):
        attr.entity = entity
        attr.name = name
        if attr.pk_offset is not None and attr.lazy:
            throw(TypeError, 'Primary key attribute %s cannot be lazy' % attr)
        if attr.cascade_delete is not None and attr.is_basic:
            throw(TypeError, "'cascade_delete' option cannot be set for attribute %s, "
                             "because it is not relationship attribute" % attr)

        if not attr.is_required:
            if attr.is_unique and attr.nullable is False:
                throw(TypeError, 'Optional unique attribute %s must be nullable' % attr)
        if entity._root_ is not entity:
            if attr.nullable is False: throw(ERDiagramError,
                'Attribute %s must be nullable due to single-table inheritance' % attr)
            attr.nullable = True

        if 'default' in attr.kwargs:
            attr.default = attr.original_default = attr.kwargs.pop('default')
            if attr.is_required:
                if attr.default is None: throw(TypeError,
                    'Default value for required attribute %s cannot be None' % attr)
                if attr.default == '': throw(TypeError,
                    'Default value for required attribute %s cannot be empty string' % attr)
            elif attr.default is None and not attr.nullable: throw(TypeError,
                'Default value for non-nullable attribute %s cannot be set to None' % attr)
        elif attr.is_string and not attr.is_required and not attr.nullable:
            attr.default = ''
        else:
            attr.default = None

        if attr.sql_default not in (None, True, False) and not isinstance(attr.sql_default, basestring):
            throw(TypeError, "'sql_default' option of %s attribute must be of string or bool type. Got: %s"
                             % (attr, attr.sql_default))

        # composite keys will be checked later inside EntityMeta.__init__
        if attr.py_type == float:
            if attr.is_pk: throw(TypeError, 'PrimaryKey attribute %s cannot be of type float' % attr)
            elif attr.is_unique: throw(TypeError, 'Unique attribute %s cannot be of type float' % attr)
        if attr.is_volatile and (attr.is_pk or attr.is_collection): throw(TypeError,
            '%s attribute %s cannot be volatile' % (attr.__class__.__name__, attr))
    def linked(attr):
        reverse = attr.reverse
        if attr.cascade_delete is None:
            attr.cascade_delete = attr.is_collection and reverse.is_required
        elif attr.cascade_delete:
            if reverse.cascade_delete: throw(TypeError,
                "'cascade_delete' option cannot be set for both sides of relationship "
                "(%s and %s) simultaneously" % (attr, reverse))
            if reverse.is_collection: throw(TypeError,
                "'cascade_delete' option cannot be set for attribute %s, "
                "because reverse attribute %s is collection" % (attr, reverse))
    @cut_traceback
    def __repr__(attr):
        owner_name = not attr.entity and '?' or attr.entity.__name__
        return '%s.%s' % (owner_name, attr.name or '?')
    def check(attr, val, obj=None, entity=None, from_db=False):
        if val is None:
            if not attr.nullable and not from_db:
                throw(ConstraintError, 'Attribute %s cannot be set to None' % attr)
            return val
        assert val is not NOT_LOADED
        if val is DEFAULT:
            default = attr.default
            if default is None: return None
            if callable(default): val = default()
            else: val = default

        if entity is not None: pass
        elif obj is not None: entity = obj.__class__
        else: entity = attr.entity

        reverse = attr.reverse
        if not reverse:
            if isinstance(val, Entity): throw(TypeError, 'Attribute %s must be of %s type. Got: %s'
                % (attr, attr.py_type.__name__, val))
            if attr.converters:
                if len(attr.converters) != 1: throw(NotImplementedError)
                converter = attr.converters[0]
                if converter is not None:
                    try:
                        if from_db: return converter.sql2py(val)
                        else: return converter.validate(val)
                    except UnicodeDecodeError, e:
                        vrepr = repr(val)
                        if len(vrepr) > 100: vrepr = vrepr[:97] + '...'
                        raise ValueError('Value for attribute %s cannot be converted to unicode: %s' % (attr, vrepr))
            if type(val) is attr.py_type: return val
            return attr.py_type(val)

        rentity = reverse.entity
        if not isinstance(val, rentity):
            if type(val) is not tuple: val = (val,)
            if len(val) != len(rentity._pk_columns_): throw(ConstraintError,
                'Invalid number of columns were specified for attribute %s. Expected: %d, got: %d'
                % (attr, len(rentity._pk_columns_), len(val)))
            return rentity._get_by_raw_pkval_(val)

        if obj is not None: cache = obj._session_cache_
        else: cache = entity._database_._get_cache()
        if cache is not val._session_cache_:
            throw(TransactionError, 'An attempt to mix objects belongs to different caches')
        return val
    def parse_value(attr, row, offsets):
        assert len(attr.columns) == len(offsets)
        if not attr.reverse:
            if len(offsets) > 1: throw(NotImplementedError)
            offset = offsets[0]
            val = attr.check(row[offset], None, attr.entity, from_db=True)
        else:
            vals = map(row.__getitem__, offsets)
            if None in vals:
                assert len(set(vals)) == 1
                val = None
            else: val = attr.py_type._get_by_raw_pkval_(vals)
        return val
    def load(attr, obj):
        if not obj._session_cache_.is_alive: throw(DatabaseSessionIsOver,
            'Cannot load attribute %s.%s: the database session is over' % (safe_repr(obj), attr.name))
        if not attr.columns:
            reverse = attr.reverse
            assert reverse is not None and reverse.columns
            objects = reverse.entity._find_in_db_({reverse : obj}, 1)
            if not objects:
                obj._vals_[attr] = None
                return None
            elif len(objects) == 1:
                dbval = objects[0]
                assert obj._vals_[attr] == dbval
                return dbval
            else: assert False
        if attr.lazy:
            entity = attr.entity
            database = entity._database_
            if not attr.lazy_sql_cache:
                select_list = [ 'ALL' ] + [ [ 'COLUMN', None, column ] for column in attr.columns ]
                from_list = [ 'FROM', [ None, 'TABLE', entity._table_ ] ]
                pk_columns = entity._pk_columns_
                pk_converters = entity._pk_converters_
                criteria_list = [ [ 'EQ', [ 'COLUMN', None, column ], [ 'PARAM', (i, None, None), converter ] ]
                                  for i, (column, converter) in enumerate(izip(pk_columns, pk_converters)) ]
                sql_ast = [ 'SELECT', select_list, from_list, [ 'WHERE' ] + criteria_list ]
                sql, adapter = database._ast2sql(sql_ast)
                offsets = tuple(xrange(len(attr.columns)))
                attr.lazy_sql_cache = sql, adapter, offsets
            else: sql, adapter, offsets = attr.lazy_sql_cache
            arguments = adapter(obj._get_raw_pkval_())
            cursor = database._exec_sql(sql, arguments)
            row = cursor.fetchone()
            dbval = attr.parse_value(row, offsets)
            attr.db_set(obj, dbval)
        else: obj._load_()
        return obj._vals_[attr]
    @cut_traceback
    def __get__(attr, obj, cls=None):
        if obj is None: return attr
        if attr.pk_offset is not None: return attr.get(obj)
        result = attr.get(obj)
        bit = obj._bits_except_volatile_[attr]
        wbits = obj._wbits_
        if wbits is not None and not wbits & bit: obj._rbits_ |= bit
        return result
    def get(attr, obj):
        if attr.pk_offset is None and obj._status_ in ('deleted', 'cancelled'):
            throw_object_was_deleted(obj)
        val = obj._vals_[attr] if attr in obj._vals_ else attr.load(obj)
        if val is not None and attr.reverse and val._subclasses_ and val._status_ not in ('deleted', 'cancelled'):
            seeds = obj._session_cache_.seeds[val._pk_attrs_]
            if val in seeds: val._load_()
        return val
    @cut_traceback
    def __set__(attr, obj, new_val, undo_funcs=None):
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot assign new value to attribute %s.%s: the database session is over' % (safe_repr(obj), attr.name))
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        is_reverse_call = undo_funcs is not None
        reverse = attr.reverse
        new_val = attr.check(new_val, obj, from_db=False)
        if attr.pk_offset is not None:
            pkval = obj._pkval_
            if pkval is None: pass
            elif obj._pk_is_composite_:
                if new_val == pkval[attr.pk_offset]: return
            elif new_val == pkval: return
            throw(TypeError, 'Cannot change value of primary key')
        with cache.flush_disabled():
            old_val =  obj._vals_.get(attr, NOT_LOADED)
            if old_val is NOT_LOADED and reverse and not reverse.is_collection:
                old_val = attr.load(obj)
            status = obj._status_
            wbits = obj._wbits_
            objects_to_save = cache.objects_to_save
            if wbits is not None:
                obj._wbits_ = wbits | obj._bits_[attr]
                if status != 'updated':
                    assert status in ('loaded', 'saved')
                    assert obj._save_pos_ is None
                    obj._status_ = 'updated'
                    obj._save_pos_ = len(objects_to_save)
                    objects_to_save.append(obj)
                    cache.modified = True
            if not attr.reverse and not attr.is_part_of_unique_index:
                obj._vals_[attr] = new_val
                return
            if not is_reverse_call: undo_funcs = []
            undo = []
            def undo_func():
                obj._status_ = status
                obj._wbits_ = wbits
                if status in ('loaded', 'saved'):
                    assert objects_to_save
                    obj2 = objects_to_save.pop()
                    assert obj2 is obj and obj._save_pos_ == len(objects_to_save)
                    obj._save_pos_ = None

                if old_val is NOT_LOADED: obj._vals_.pop(attr)
                else: obj._vals_[attr] = old_val
                for index, old_key, new_key in undo:
                    if new_key is not None: del index[new_key]
                    if old_key is not None: index[old_key] = obj
            undo_funcs.append(undo_func)
            if old_val == new_val: return
            try:
                if attr.is_unique:
                    cache.update_simple_index(obj, attr, old_val, new_val, undo)
                for attrs, i in attr.composite_keys:
                    vals = map(obj._vals_.get, attrs)
                    prev_vals = tuple(vals)
                    vals[i] = new_val
                    new_vals = tuple(vals)
                    cache.update_composite_index(obj, attrs, prev_vals, new_vals, undo)

                obj._vals_[attr] = new_val

                if not reverse: pass
                elif not is_reverse_call: attr.update_reverse(obj, old_val, new_val, undo_funcs)
                elif old_val not in (None, NOT_LOADED):
                    if not reverse.is_collection:
                        if new_val is not None: reverse.__set__(old_val, None, undo_funcs)
                    elif isinstance(reverse, Set):
                        reverse.reverse_remove((old_val,), obj, undo_funcs)
                    else: throw(NotImplementedError)
            except:
                if not is_reverse_call:
                    for undo_func in reversed(undo_funcs): undo_func()
                raise
    def db_set(attr, obj, new_dbval, is_reverse_call=False):
        cache = obj._session_cache_
        assert cache.is_alive
        assert obj._status_ not in created_or_deleted_statuses
        assert attr.pk_offset is None
        if new_dbval is NOT_LOADED: assert is_reverse_call
        old_dbval = obj._dbvals_.get(attr, NOT_LOADED)

        if attr.py_type is float:
            if old_dbval is NOT_LOADED: pass
            elif attr.converters[0].equals(old_dbval, new_dbval): return
        elif old_dbval == new_dbval: return

        bit = obj._bits_[attr]
        if obj._rbits_ & bit:
            assert old_dbval is not NOT_LOADED
            if new_dbval is NOT_LOADED: diff = ''
            else: diff = ' (was: %s, now: %s)' % (old_dbval, new_dbval)
            throw(UnrepeatableReadError,
                'Value of %s.%s for %s was updated outside of current transaction%s'
                % (obj.__class__.__name__, attr.name, obj, diff))

        if new_dbval is NOT_LOADED: obj._dbvals_.pop(attr, None)
        else: obj._dbvals_[attr] = new_dbval

        wbit = bool(obj._wbits_ & bit)
        if not wbit:
            old_val = obj._vals_.get(attr, NOT_LOADED)
            assert old_val == old_dbval
            if attr.is_part_of_unique_index:
                cache = obj._session_cache_
                if attr.is_unique: cache.db_update_simple_index(obj, attr, old_val, new_dbval)
                for attrs, i in attr.composite_keys:
                    vals = map(obj._vals_.get, attrs)
                    old_vals = tuple(vals)
                    vals[i] = new_dbval
                    new_vals = tuple(vals)
                    cache.db_update_composite_index(obj, attrs, old_vals, new_vals)
            if new_dbval is NOT_LOADED: obj._vals_.pop(attr, None)
            else: obj._vals_[attr] = new_dbval

        reverse = attr.reverse
        if not reverse: pass
        elif not is_reverse_call: attr.db_update_reverse(obj, old_dbval, new_dbval)
        elif old_dbval not in (None, NOT_LOADED):
            if not reverse.is_collection:
                if new_dbval is not NOT_LOADED: reverse.db_set(old_dbval, NOT_LOADED, is_reverse_call=True)
            elif isinstance(reverse, Set):
                reverse.db_reverse_remove((old_dbval,), obj)
            else: throw(NotImplementedError)
    def update_reverse(attr, obj, old_val, new_val, undo_funcs):
        reverse = attr.reverse
        if not reverse.is_collection:
            if old_val not in (None, NOT_LOADED): reverse.__set__(old_val, None, undo_funcs)
            if new_val is not None: reverse.__set__(new_val, obj, undo_funcs)
        elif isinstance(reverse, Set):
            if old_val not in (None, NOT_LOADED): reverse.reverse_remove((old_val,), obj, undo_funcs)
            if new_val is not None: reverse.reverse_add((new_val,), obj, undo_funcs)
        else: throw(NotImplementedError)
    def db_update_reverse(attr, obj, old_dbval, new_dbval):
        reverse = attr.reverse
        if not reverse.is_collection:
            if old_dbval not in (None, NOT_LOADED): reverse.db_set(old_dbval, NOT_LOADED, True)
            if new_dbval is not None: reverse.db_set(new_dbval, obj, True)
        elif isinstance(reverse, Set):
            if old_dbval not in (None, NOT_LOADED): reverse.db_reverse_remove((old_dbval,), obj)
            if new_dbval is not None: reverse.db_reverse_add((new_dbval,), obj)
        else: throw(NotImplementedError)
    def __delete__(attr, obj):
        throw(NotImplementedError)
    def get_raw_values(attr, val):
        reverse = attr.reverse
        if not reverse: return (val,)
        rentity = reverse.entity
        if val is None: return rentity._pk_nones_
        return val._get_raw_pkval_()
    def get_columns(attr):
        assert not attr.is_collection
        assert not isinstance(attr.py_type, basestring)
        if attr._columns_checked: return attr.columns

        provider = attr.entity._database_.provider
        reverse = attr.reverse
        if not reverse: # attr is not part of relationship
            if not attr.columns: attr.columns = provider.get_default_column_names(attr)
            elif len(attr.columns) > 1: throw(MappingError, "Too many columns were specified for %s" % attr)
            attr.col_paths = [ attr.name ]
            attr.converters = [ provider.get_converter_by_attr(attr) ]
        else:
            def generate_columns():
                reverse_pk_columns = reverse.entity._get_pk_columns_()
                reverse_pk_col_paths = reverse.entity._pk_paths_
                if not attr.columns:
                    attr.columns = provider.get_default_column_names(attr, reverse_pk_columns)
                elif len(attr.columns) != len(reverse_pk_columns): throw(MappingError,
                    'Invalid number of columns specified for %s' % attr)
                attr.col_paths = [ '-'.join((attr.name, paths)) for paths in reverse_pk_col_paths ]
                attr.converters = []
                for a in reverse.entity._pk_attrs_:
                    attr.converters.extend(a.converters)

            if reverse.is_collection: # one-to-many:
                generate_columns()
            # one-to-one:
            elif attr.is_required:
                assert not reverse.is_required
                generate_columns()
            elif attr.columns: generate_columns()
            elif reverse.columns: pass
            elif attr.entity.__name__ > reverse.entity.__name__: pass
            else: generate_columns()
        attr._columns_checked = True
        if len(attr.columns) == 1: attr.column = attr.columns[0]
        else: attr.column = None
        return attr.columns
    @property
    def asc(attr):
        return attr
    @property
    def desc(attr):
        return DescWrapper(attr)
    def describe(attr):
        t = attr.py_type
        if isinstance(t, type): t = t.__name__
        options = []
        if attr.args: options.append(', '.join(map(str, attr.args)))
        if attr.auto: options.append('auto=True')
        if not isinstance(attr, PrimaryKey) and attr.is_unique: options.append('unique=True')
        if attr.default is not None: options.append('default=%s' % attr.default)
        if not options: options = ''
        else: options = ', ' + ', '.join(options)
        result = "%s(%s%s)" % (attr.__class__.__name__, t, options)
        return "%s = %s" % (attr.name,result)

class Optional(Attribute):
    __slots__ = []

class Required(Attribute):
    __slots__ = []
    def check(attr, val, obj=None, entity=None, from_db=False):
        if val == '' \
        or val is None and not attr.auto \
        or val is DEFAULT and attr.default in (None, '') \
                and not attr.auto and not attr.is_volatile and not attr.sql_default:
            if obj is None: throw(ConstraintError, 'Attribute %s is required' % attr)
            throw(ConstraintError, 'Attribute %r.%s is required' % (obj, attr.name))
        return Attribute.check(attr, val, obj, entity, from_db)

class Discriminator(Required):
    __slots__ = [ 'code2cls' ]
    def __init__(attr, py_type, *args, **kwargs):
        Attribute.__init__(attr, py_type, *args, **kwargs)
        attr.code2cls = {}
    def _init_(attr, entity, name):
        if entity._root_ is not entity: throw(ERDiagramError,
            'Discriminator attribute %s cannot be declared in subclass' % attr)
        Required._init_(attr, entity, name)
        entity._discriminator_attr_ = attr
    @staticmethod
    def create_default_attr(entity):
        if hasattr(entity, 'classtype'): throw(ERDiagramError,
            "Cannot create discriminator column for %s automatically "
            "because name 'classtype' is already in use" % entity.__name__)
        attr = Discriminator(str, column='classtype')
        attr._init_(entity, 'classtype')
        entity._attrs_.append(attr)
        entity._new_attrs_.append(attr)
        entity._adict_['classtype'] = attr
        entity._bits_[attr] = 0
        type.__setattr__(entity, 'classtype', attr)
        attr.process_entity_inheritance(entity)
    def process_entity_inheritance(attr, entity):
        if '_discriminator_' not in entity.__dict__:
            entity._discriminator_ = entity.__name__
        discr_value = entity._discriminator_
        if discr_value is None:
            discr_value = entity._discriminator_ = entity.__name__
        discr_type = type(discr_value)
        for code, cls in attr.code2cls.items():
            if type(code) != discr_type: throw(ERDiagramError,
                'Discriminator values %r and %r of entities %s and %s have different types'
                % (code, discr_value, cls, entity))
        attr.code2cls[discr_value] = entity
    def check(attr, val, obj=None, entity=None, from_db=False):
        if from_db: return val
        elif val is DEFAULT:
            assert entity is not None
            return entity._discriminator_
        return Attribute.check(attr, val, obj, entity)
    def load(attr, obj):
        raise AssertionError
    def __get__(attr, obj, cls=None):
        if obj is None: return attr
        return obj._discriminator_
    def __set__(attr, obj, new_val):
        throw(TypeError, 'Cannot assign value to discriminator attribute')
    def db_set(attr, obj, new_dbval):
        assert False
    def update_reverse(attr, obj, old_val, new_val, undo_funcs):
        assert False

def composite_key(*attrs):
    if len(attrs) < 2: throw(TypeError,
        'composite_key() must receive at least two attributes as arguments')
    for i, attr in enumerate(attrs):
        if not isinstance(attr, Attribute): throw(TypeError,
            'composite_key() arguments must be attributes. Got: %r' % attr)
        attr.is_part_of_unique_index = True
        attr.composite_keys.append((attrs, i))
    cls_dict = sys._getframe(1).f_locals
    composite_keys = cls_dict.setdefault('_key_dict_', {})
    composite_keys[attrs] = False

class PrimaryKey(Required):
    __slots__ = []
    def __new__(cls, *args, **kwargs):
        if not args: throw(TypeError, 'PrimaryKey must receive at least one positional argument')
        cls_dict = sys._getframe(1).f_locals
        attrs = tuple(a for a in args if isinstance(a, Attribute))
        non_attrs = [ a for a in args if not isinstance(a, Attribute) ]
        cls_dict = sys._getframe(1).f_locals

        if not attrs:
            return Required.__new__(cls)
        elif non_attrs or kwargs:
            throw(TypeError, 'PrimaryKey got invalid arguments: %r %r' % (args, kwargs))
        elif len(attrs) == 1:
            attr = attrs[0]
            attr_name = 'something'
            for key, val in cls_dict.iteritems():
                if val is attr: attr_name = key; break
            py_type = attr.py_type
            type_str = py_type.__name__ if type(py_type) is type else repr(py_type)
            throw(TypeError, 'Just use %s = PrimaryKey(%s, ...) directly instead of PrimaryKey(%s)'
                  % (attr_name, type_str, attr_name))

        for i, attr in enumerate(attrs):
            attr.is_part_of_unique_index = True
            attr.composite_keys.append((attrs, i))
        keys = cls_dict.setdefault('_key_dict_', {})
        keys[attrs] = True
        return None

class Collection(Attribute):
    __slots__ = 'table', 'wrapper_class', 'symmetric', 'reverse_column', 'reverse_columns', \
                'nplus1_threshold', 'cached_load_sql', 'cached_add_m2m_sql', 'cached_remove_m2m_sql', \
                'cached_count_sql', 'cached_empty_sql'
    def __init__(attr, py_type, *args, **kwargs):
        if attr.__class__ is Collection: throw(TypeError, "'Collection' is abstract type")
        table = kwargs.pop('table', None)  # TODO: rename table to link_table or m2m_table
        if table is not None and not isinstance(table, basestring):
            if not isinstance(table, (list, tuple)):
                throw(TypeError, "Parameter 'table' must be a string. Got: %r" % table)
            for name_part in table:
                if not isinstance(name_part, basestring):
                    throw(TypeError, 'Each part of table name must be a string. Got: %r' % name_part)
            table = tuple(table)
        attr.table = table
        Attribute.__init__(attr, py_type, *args, **kwargs)
        if attr.auto: throw(TypeError, "'auto' option could not be set for collection attribute")
        kwargs = attr.kwargs

        attr.reverse_column = kwargs.pop('reverse_column', None)
        attr.reverse_columns = kwargs.pop('reverse_columns', None)
        if attr.reverse_column is not None:
            if attr.reverse_columns is not None and attr.reverse_columns != [ attr.reverse_column ]:
                throw(TypeError, "Parameters 'reverse_column' and 'reverse_columns' cannot be specified simultaneously")
            if not isinstance(attr.reverse_column, basestring):
                throw(TypeError, "Parameter 'reverse_column' must be a string. Got: %r" % attr.reverse_column)
            attr.reverse_columns = [ attr.reverse_column ]
        elif attr.reverse_columns is not None:
            if not isinstance(attr.reverse_columns, (tuple, list)):
                throw(TypeError, "Parameter 'reverse_columns' must be a list. Got: %r" % attr.reverse_columns)
            for reverse_column in attr.reverse_columns:
                if not isinstance(reverse_column, basestring):
                    throw(TypeError, "Parameter 'reverse_columns' must be a list of strings. Got: %r" % attr.reverse_columns)
            if len(attr.reverse_columns) == 1: attr.reverse_column = attr.reverse_columns[0]
        else: attr.reverse_columns = []

        attr.nplus1_threshold = kwargs.pop('nplus1_threshold', 1)
        for option in attr.kwargs: throw(TypeError, 'Unknown option %r' % option)
        attr.cached_load_sql = {}
        attr.cached_add_m2m_sql = None
        attr.cached_remove_m2m_sql = None
        attr.cached_count_sql = None
        attr.cached_empty_sql = None
    def _init_(attr, entity, name):
        Attribute._init_(attr, entity, name)
        if attr.is_unique: throw(TypeError,
            "'unique' option cannot be set for attribute %s because it is collection" % attr)
        if attr.default is not None:
            throw(TypeError, 'Default value could not be set for collection attribute')
        attr.symmetric = (attr.py_type == entity.__name__ and attr.reverse == name)
        if not attr.symmetric and attr.reverse_columns: throw(TypeError,
            "'reverse_column' and 'reverse_columns' options can be set for symmetric relations only")
    def load(attr, obj):
        assert False, 'Abstract method'
    def __get__(attr, obj, cls=None):
        assert False, 'Abstract method'
    def __set__(attr, obj, val):
        assert False, 'Abstract method'
    def __delete__(attr, obj):
        assert False, 'Abstract method'
    def prepare(attr, obj, val, fromdb=False):
        assert False, 'Abstract method'
    def set(attr, obj, val, fromdb=False):
        assert False, 'Abstract method'

class SetData(set):
    __slots__ = 'is_fully_loaded', 'added', 'removed', 'count'
    def __init__(setdata):
        setdata.is_fully_loaded = False
        setdata.added = setdata.removed = None
        setdata.count = None

def construct_criteria_list(alias, columns, converters, row_value_syntax, count=1, start=0):
    assert count > 0
    if count == 1:
        return [ [ 'EQ', [ 'COLUMN', alias, column ], [ 'PARAM', (start, None, j), converter ] ]
                 for j, (column, converter) in enumerate(izip(columns, converters)) ]
    if len(columns) == 1:
        column = columns[0]
        converter = converters[0]
        param_list = [ [ 'PARAM', (i+start, None, 0), converter ] for i in xrange(count) ]
        condition = [ 'IN', [ 'COLUMN', alias, column ], param_list ]
        return [ condition ]
    elif row_value_syntax:
        row = [ 'ROW' ] + [ [ 'COLUMN', alias, column ] for column in columns ]
        param_list = [ [ 'ROW' ] + [ [ 'PARAM', (i+start, None, j), converter ]
                                     for j, converter in enumerate(converters) ]
                       for i in xrange(count) ]
        condition = [ 'IN', row, param_list ]
        return [ condition ]
    else:
        conditions = [ [ 'AND' ] + [ [ 'EQ', [ 'COLUMN', alias, column ], [ 'PARAM', (i+start, None, j), converter ] ]
                                     for j, (column, converter) in enumerate(izip(columns, converters)) ]
                       for i in xrange(count) ]
        return [ [ 'OR' ] + conditions ]

class Set(Collection):
    __slots__ = []
    def check(attr, val, obj=None, entity=None, from_db=False):
        assert val is not NOT_LOADED
        if val is None or val is DEFAULT: return set()
        if entity is not None: pass
        elif obj is not None: entity = obj.__class__
        else: entity = attr.entity
        reverse = attr.reverse
        if not reverse: throw(NotImplementedError)
        if isinstance(val, reverse.entity): items = set((val,))
        else:
            rentity = reverse.entity
            try: items = set(val)
            except TypeError: throw(TypeError, 'Item of collection %s.%s must be an instance of %s. Got: %r'
                                              % (entity.__name__, attr.name, rentity.__name__, val))
            for item in items:
                if not isinstance(item, rentity):
                    throw(TypeError, 'Item of collection %s.%s must be an instance of %s. Got: %r'
                                    % (entity.__name__, attr.name, rentity.__name__, item))
        if obj is not None: cache = obj._session_cache_
        else: cache = entity._database_._get_cache()
        for item in items:
            if item._session_cache_ is not cache:
                throw(TransactionError, 'An attempt to mix objects belongs to different caches')
        return items
    def load(attr, obj, items=None):
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot load collection %s.%s: the database session is over' % (safe_repr(obj), attr.name))
        assert obj._status_ not in del_statuses
        setdata = obj._vals_.get(attr)
        if setdata is None: setdata = obj._vals_[attr] = SetData()
        elif setdata.is_fully_loaded: return setdata
        entity = attr.entity
        reverse = attr.reverse
        rentity = reverse.entity
        if not reverse: throw(NotImplementedError)
        database = obj._database_
        if cache is not database._get_cache():
            throw(TransactionError, "Transaction of object %s belongs to different thread")

        counter = cache.collection_statistics.setdefault(attr, 0)
        nplus1_threshold = attr.nplus1_threshold
        prefetching = options.PREFETCHING and not attr.lazy and nplus1_threshold is not None \
                      and (counter >= nplus1_threshold or cache.noflush_counter)

        if items:
            if not reverse.is_collection:
                items = set(item for item in items if reverse not in item._vals_)
            else:
                items = set(items)
                items -= setdata
                if setdata.removed: items -= setdata.removed
            if not items: return setdata

        if items and (attr.lazy or not setdata):
            items = list(items)
            if not reverse.is_collection:
                sql, adapter, attr_offsets = rentity._construct_batchload_sql_(len(items))
                arguments = adapter(items)
                cursor = database._exec_sql(sql, arguments)
                items = rentity._fetch_objects(cursor, attr_offsets)
                return setdata

            sql, adapter = attr.construct_sql_m2m(1, len(items))
            items.append(obj)
            arguments = adapter(items)
            cursor = database._exec_sql(sql, arguments)
            loaded_items = set(imap(rentity._get_by_raw_pkval_, cursor.fetchall()))
            setdata |= loaded_items
            reverse.db_reverse_add(loaded_items, obj)
            return setdata

        objects = [ obj ]
        setdata_list = [ setdata ]
        if prefetching:
            pk_index = cache.indexes[entity._pk_attrs_]
            max_batch_size = database.provider.max_params_count // len(entity._pk_columns_)
            for obj2 in pk_index.itervalues():
                if obj2 is obj: continue
                if obj2._status_ in created_or_deleted_statuses: continue
                setdata2 = obj2._vals_.get(attr)
                if setdata2 is None: setdata2 = obj2._vals_[attr] = SetData()
                elif setdata2.is_fully_loaded: continue
                objects.append(obj2)
                setdata_list.append(setdata2)
                if len(objects) >= max_batch_size: break

        if not reverse.is_collection:
            sql, adapter, attr_offsets = rentity._construct_batchload_sql_(len(objects), reverse)
            arguments = adapter(objects)
            cursor = database._exec_sql(sql, arguments)
            items = rentity._fetch_objects(cursor, attr_offsets)
        else:
            sql, adapter = attr.construct_sql_m2m(len(objects))
            arguments = adapter(objects)
            cursor = database._exec_sql(sql, arguments)
            pk_len = len(entity._pk_columns_)
            d = {}
            if len(objects) > 1:
                for row in cursor.fetchall():
                    obj2 = entity._get_by_raw_pkval_(row[:pk_len])
                    item = rentity._get_by_raw_pkval_(row[pk_len:])
                    items = d.get(obj2)
                    if items is None: items = d[obj2] = set()
                    items.add(item)
            else: d[obj] = set(imap(rentity._get_by_raw_pkval_, cursor.fetchall()))
            for obj2, items in d.iteritems():
                setdata2 = obj2._vals_.get(attr)
                if setdata2 is None: setdata2 = obj._vals_[attr] = SetData()
                else:
                    phantoms = setdata2 - items
                    if setdata2.added: phantoms -= setdata2.added
                    if phantoms: throw(UnrepeatableReadError,
                        'Phantom object %s disappeared from collection %s.%s'
                        % (safe_repr(phantoms.pop()), safe_repr(obj), attr.name))
                items -= setdata2
                if setdata2.removed: items -= setdata2.removed
                setdata2 |= items
                reverse.db_reverse_add(items, obj2)

        for setdata2 in setdata_list:
            setdata2.is_fully_loaded = True
            setdata2.count = len(setdata2)
        cache.collection_statistics[attr] = counter + 1
        return setdata
    def construct_sql_m2m(attr, batch_size=1, items_count=0):
        if items_count:
            assert batch_size == 1
            cache_key = -items_count
        else: cache_key = batch_size
        cached_sql = attr.cached_load_sql.get(cache_key)
        if cached_sql is not None: return cached_sql
        reverse = attr.reverse
        assert reverse is not None and reverse.is_collection and issubclass(reverse.py_type, Entity)
        table_name = attr.table
        assert table_name is not None
        select_list = [ 'ALL' ]
        if not attr.symmetric:
            columns = attr.columns
            converters = attr.converters
            rcolumns = reverse.columns
            rconverters = reverse.converters
        else:
            columns = attr.reverse_columns
            rcolumns = attr.columns
            converters = rconverters = attr.converters
        if batch_size > 1:
            select_list.extend([ 'COLUMN', 'T1', column ] for column in rcolumns)
        select_list.extend([ 'COLUMN', 'T1', column ] for column in columns)
        from_list = [ 'FROM', [ 'T1', 'TABLE', table_name ]]
        database = attr.entity._database_
        row_value_syntax = database.provider.translator_cls.row_value_syntax
        where_list = [ 'WHERE' ]
        where_list += construct_criteria_list('T1', rcolumns, rconverters, row_value_syntax, batch_size, items_count)
        if items_count:
            where_list += construct_criteria_list('T1', columns, converters, row_value_syntax, items_count)
        sql_ast = [ 'SELECT', select_list, from_list, where_list ]
        sql, adapter = attr.cached_load_sql[cache_key] = database._ast2sql(sql_ast)
        return sql, adapter
    def copy(attr, obj):
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        setdata = obj._vals_.get(attr)
        if setdata is None or not setdata.is_fully_loaded: setdata = attr.load(obj)
        reverse = attr.reverse
        if not reverse.is_collection and reverse.pk_offset is None:
            added = setdata.added or ()
            for item in setdata:
                if item in added: continue
                bit = item._bits_except_volatile_[reverse]
                assert item._wbits_ is not None
                if not item._wbits_ & bit: item._rbits_ |= bit
        return set(setdata)
    @cut_traceback
    def __get__(attr, obj, cls=None):
        if obj is None: return attr
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        rentity = attr.py_type
        wrapper_class = rentity._get_set_wrapper_subclass_()
        return wrapper_class(obj, attr)
    @cut_traceback
    def __set__(attr, obj, new_items, undo_funcs=None):
        if isinstance(new_items, SetWrapper) and new_items._obj_ is obj and new_items._attr_ is attr:
            return  # after += or -=
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot change collection %s.%s: the database session is over' % (safe_repr(obj), attr))
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        with cache.flush_disabled():
            new_items = attr.check(new_items, obj)
            reverse = attr.reverse
            if not reverse: throw(NotImplementedError)
            setdata = obj._vals_.get(attr)
            if setdata is None:
                if obj._status_ == 'created':
                    setdata = obj._vals_[attr] = SetData()
                    setdata.is_fully_loaded = True
                    setdata.count = 0
                else: setdata = attr.load(obj)
            elif not setdata.is_fully_loaded: setdata = attr.load(obj)
            if new_items == setdata: return
            to_add = new_items - setdata
            to_remove = setdata - new_items
            if undo_funcs is None: undo_funcs = []
            try:
                if not reverse.is_collection:
                    for item in to_remove: reverse.__set__(item, None, undo_funcs)
                    for item in to_add: reverse.__set__(item, obj, undo_funcs)
                else:
                    reverse.reverse_remove(to_remove, obj, undo_funcs)
                    reverse.reverse_add(to_add, obj, undo_funcs)
            except:
                for undo_func in reversed(undo_funcs): undo_func()
                raise
        setdata.clear()
        setdata |= new_items
        if setdata.count is not None: setdata.count = len(new_items)
        added = setdata.added
        removed = setdata.removed
        if to_add:
            if removed: (to_add, setdata.removed) = (to_add - removed, removed - to_add)
            if added: added |= to_add
            else: setdata.added = to_add  # added may be None
        if to_remove:
            if added: (to_remove, setdata.added) = (to_remove - added, added - to_remove)
            if removed: removed |= to_remove
            else: setdata.removed = to_remove  # removed may be None
        cache.modified_collections[attr].add(obj)
        cache.modified = True
    def __delete__(attr, obj):
        throw(NotImplementedError)
    def reverse_add(attr, objects, item, undo_funcs):
        undo = []
        cache = item._session_cache_
        objects_with_modified_collections = cache.modified_collections[attr]
        for obj in objects:
            setdata = obj._vals_.get(attr)
            if setdata is None: setdata = obj._vals_[attr] = SetData()
            else: assert item not in setdata
            if setdata.added is None: setdata.added = set()
            else: assert item not in setdata.added
            in_removed = setdata.removed and item in setdata.removed
            was_modified_earlier = obj in objects_with_modified_collections
            undo.append((obj, in_removed, was_modified_earlier))
            setdata.add(item)
            if setdata.count is not None: setdata.count += 1
            if in_removed: setdata.removed.remove(item)
            else: setdata.added.add(item)
            objects_with_modified_collections.add(obj)
        def undo_func():
            for obj, in_removed, was_modified_earlier in undo:
                setdata = obj._vals_[attr]
                setdata.remove(item)
                if setdata.count is not None: setdata.count -= 1
                if in_removed: setdata.removed.add(item)
                else: setdata.added.remove(item)
                if not was_modified_earlier: objects_with_modified_collections.remove(obj)
        undo_funcs.append(undo_func)
    def db_reverse_add(attr, objects, item):
        for obj in objects:
            setdata = obj._vals_.get(attr)
            if setdata is None: setdata = obj._vals_[attr] = SetData()
            elif setdata.is_fully_loaded: throw(UnrepeatableReadError,
                'Phantom object %s appeared in collection %s.%s' % (safe_repr(item), safe_repr(obj), attr.name))
            setdata.add(item)
    def reverse_remove(attr, objects, item, undo_funcs):
        undo = []
        cache = item._session_cache_
        objects_with_modified_collections = cache.modified_collections[attr]
        for obj in objects:
            setdata = obj._vals_.get(attr)
            assert setdata is not None
            assert item in setdata
            if setdata.removed is None: setdata.removed = set()
            else: assert item not in setdata.removed
            in_added = setdata.added and item in setdata.added
            was_modified_earlier = obj in objects_with_modified_collections
            undo.append((obj, in_added, was_modified_earlier))
            objects_with_modified_collections.add(obj)
            setdata.remove(item)
            if setdata.count is not None: setdata.count -= 1
            if in_added: setdata.added.remove(item)
            else: setdata.removed.add(item)
        def undo_func():
            for obj, in_removed, was_modified_earlier in undo:
                setdata = obj._vals_[attr]
                setdata.add(item)
                if setdata.count is not None: setdata.count += 1
                if in_added: setdata.added.add(item)
                else: setdata.removed.remove(item)
                if not was_modified_earlier: objects_with_modified_collections.remove(obj)
        undo_funcs.append(undo_func)
    def db_reverse_remove(attr, objects, item):
        for obj in objects:
            setdata = obj._vals_[attr]
            setdata.remove(item)
    def get_m2m_columns(attr, is_reverse=False):
        entity = attr.entity
        if attr.symmetric:
            if attr._columns_checked:
                if not is_reverse: return attr.columns
                else: return attr.reverse_columns
            if attr.columns:
                if len(attr.columns) != len(entity._get_pk_columns_()): throw(MappingError,
                    'Invalid number of columns for %s' % attr.reverse)
            else:
                provider = attr.entity._database_.provider
                attr.columns = provider.get_default_m2m_column_names(entity)
            attr.converters = entity._pk_converters_
            if not attr.reverse_columns:
                attr.reverse_columns = [ column + '_2' for column in attr.columns ]
            attr._columns_checked = True
            if not is_reverse: return attr.columns
            else: return attr.reverse_columns

        reverse = attr.reverse
        if attr._columns_checked: return attr.reverse.columns
        elif reverse.columns:
            if len(reverse.columns) != len(entity._get_pk_columns_()): throw(MappingError,
                'Invalid number of columns for %s' % reverse)
        else:
            provider = attr.entity._database_.provider
            reverse.columns = provider.get_default_m2m_column_names(entity)
        reverse.converters = entity._pk_converters_
        attr._columns_checked = True
        return reverse.columns
    def remove_m2m(attr, removed):
        assert removed
        entity = attr.entity
        database = entity._database_
        cached_sql = attr.cached_remove_m2m_sql
        if cached_sql is None:
            reverse = attr.reverse
            table_name = attr.table
            assert table_name is not None
            where_list = [ 'WHERE' ]
            if attr.symmetric:
                columns = attr.columns + attr.reverse_columns
                converters = attr.converters + attr.converters
            else:
                columns = reverse.columns + attr.columns
                converters = reverse.converters + attr.converters
            for i, (column, converter) in enumerate(zip(columns, converters)):
                where_list.append([ 'EQ', ['COLUMN', None, column], [ 'PARAM', (i, None, None), converter ] ])
            sql_ast = [ 'DELETE', table_name, where_list ]
            sql, adapter = database._ast2sql(sql_ast)
            attr.cached_remove_m2m_sql = sql, adapter
        else: sql, adapter = cached_sql
        arguments_list = [ adapter(obj._get_raw_pkval_() + robj._get_raw_pkval_())
                           for obj, robj in removed ]
        database._exec_sql(sql, arguments_list)
    def add_m2m(attr, added):
        assert added
        entity = attr.entity
        database = entity._database_
        cached_sql = attr.cached_add_m2m_sql
        if cached_sql is None:
            reverse = attr.reverse
            table_name = attr.table
            assert table_name is not None
            if attr.symmetric:
                columns = attr.columns + attr.reverse_columns
                converters = attr.converters + attr.converters
            else:
                columns = reverse.columns + attr.columns
                converters = reverse.converters + attr.converters
            params = [ [ 'PARAM', (i, None, None), converter ] for i, converter in enumerate(converters) ]
            sql_ast = [ 'INSERT', table_name, columns, params ]
            sql, adapter = database._ast2sql(sql_ast)
            attr.cached_add_m2m_sql = sql, adapter
        else: sql, adapter = cached_sql
        arguments_list = [ adapter(obj._get_raw_pkval_() + robj._get_raw_pkval_())
                           for obj, robj in added ]
        database._exec_sql(sql, arguments_list)
    @cut_traceback
    @db_session(ddl=True)
    def drop_table(attr, with_all_data=False):
        if attr.reverse.is_collection: table_name = attr.table
        else: table_name = attr.entity._table_
        attr.entity._database_._drop_tables([ table_name ], True, with_all_data)

def unpickle_setwrapper(obj, attrname, items):
    attr = getattr(obj.__class__, attrname)
    wrapper_cls = attr.py_type._get_set_wrapper_subclass_()
    wrapper = wrapper_cls(obj, attr)
    setdata = obj._vals_.get(attr)
    if setdata is None: setdata = obj._vals_[attr] = SetData()
    setdata.is_fully_loaded = True
    setdata.count = len(setdata)
    return wrapper

class SetWrapper(object):
    __slots__ = '_obj_', '_attr_', '_attrnames_'
    _parent_ = None
    def __init__(wrapper, obj, attr):
        wrapper._obj_ = obj
        wrapper._attr_ = attr
        wrapper._attrnames_ = (attr.name,)
    def __reduce__(wrapper):
        return unpickle_setwrapper, (wrapper._obj_, wrapper._attr_.name, wrapper.copy())
    @cut_traceback
    def copy(wrapper):
        return wrapper._attr_.copy(wrapper._obj_)
    @cut_traceback
    def __repr__(wrapper):
        return '<%s %r.%s>' % (wrapper.__class__.__name__, wrapper._obj_, wrapper._attr_.name)
    @cut_traceback
    def __str__(wrapper):
        if not wrapper._obj_._session_cache_.is_alive: content = '...'
        else: content = ', '.join(imap(str, wrapper))
        return '%s([%s])' % (wrapper.__class__.__name__, content)
    @cut_traceback
    def __nonzero__(wrapper):
        attr = wrapper._attr_
        obj = wrapper._obj_
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        setdata = obj._vals_.get(attr)
        if setdata is None: setdata = attr.load(obj)
        if setdata: return True
        if not setdata.is_fully_loaded: setdata = attr.load(obj)
        return bool(setdata)
    @cut_traceback
    def is_empty(wrapper):
        attr = wrapper._attr_
        obj = wrapper._obj_
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        setdata = obj._vals_.get(attr)
        if setdata is None: setdata = obj._vals_[attr] = SetData()
        elif setdata.is_fully_loaded: return not setdata
        elif setdata: return False
        elif setdata.count is not None: return not setdata.count
        entity = attr.entity
        reverse = attr.reverse
        rentity = reverse.entity
        database = entity._database_
        cached_sql = attr.cached_empty_sql
        if cached_sql is None:
            where_list = [ 'WHERE' ]
            for i, (column, converter) in enumerate(zip(reverse.columns, reverse.converters)):
                where_list.append([ 'EQ', [ 'COLUMN', None, column ], [ 'PARAM', (i, None, None), converter ] ])
            if not reverse.is_collection:
                table_name = rentity._table_
                select_list, attr_offsets = rentity._construct_select_clause_()
            else:
                table_name = attr.table
                select_list = [ 'ALL' ] + [ [ 'COLUMN', None, column ] for column in attr.columns ]
                attr_offsets = None
            sql_ast = [ 'SELECT', select_list, [ 'FROM', [ None, 'TABLE', table_name ] ],
                        where_list, [ 'LIMIT', [ 'VALUE', 1 ] ] ]
            sql, adapter = database._ast2sql(sql_ast)
            attr.cached_empty_sql = sql, adapter, attr_offsets
        else: sql, adapter, attr_offsets = cached_sql
        arguments = adapter(obj._get_raw_pkval_())
        cursor = database._exec_sql(sql, arguments)
        if reverse.is_collection:
            row = cursor.fetchone()
            if row is not None:
                loaded_item = rentity._get_by_raw_pkval_(row)
                setdata.add(loaded_item)
                reverse.db_reverse_add((loaded_item,), obj)
        else: rentity._fetch_objects(cursor, attr_offsets)
        if setdata: return False
        setdata.is_fully_loaded = True
        setdata.count = 0
        return True
    @cut_traceback
    def __len__(wrapper):
        attr = wrapper._attr_
        obj = wrapper._obj_
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        setdata = obj._vals_.get(attr)
        if setdata is None or not setdata.is_fully_loaded: setdata = attr.load(obj)
        return len(setdata)
    @cut_traceback
    def count(wrapper):
        attr = wrapper._attr_
        obj = wrapper._obj_
        cache = obj._session_cache_
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        setdata = obj._vals_.get(attr)
        if setdata is None: setdata = obj._vals_[attr] = SetData()
        elif setdata.count is not None: return setdata.count
        entity = attr.entity
        reverse = attr.reverse
        database = entity._database_
        cached_sql = attr.cached_count_sql
        if cached_sql is None:
            where_list = [ 'WHERE' ]
            for i, (column, converter) in enumerate(zip(reverse.columns, reverse.converters)):
                where_list.append([ 'EQ', [ 'COLUMN', None, column ], [ 'PARAM', (i, None, None), converter ] ])
            if not reverse.is_collection: table_name = reverse.entity._table_
            else: table_name = attr.table
            sql_ast = [ 'SELECT', [ 'AGGREGATES', [ 'COUNT', 'ALL' ] ],
                                  [ 'FROM', [ None, 'TABLE', table_name ] ], where_list ]
            sql, adapter = database._ast2sql(sql_ast)
            attr.cached_count_sql = sql, adapter
        else: sql, adapter = cached_sql
        arguments = adapter(obj._get_raw_pkval_())
        with cache.flush_disabled():
            cursor = database._exec_sql(sql, arguments)
        setdata.count = cursor.fetchone()[0]
        if setdata.added: setdata.count += len(setdata.added)
        if setdata.removed: setdata.count -= len(setdata.removed)
        return setdata.count
    @cut_traceback
    def __iter__(wrapper):
        return iter(wrapper.copy())
    @cut_traceback
    def __eq__(wrapper, other):
        if isinstance(other, SetWrapper):
            if wrapper._obj_ is other._obj_ and wrapper._attr_ is other._attr_: return True
            else: other = other.copy()
        elif not isinstance(other, set): other = set(other)
        items = wrapper.copy()
        return items == other
    @cut_traceback
    def __ne__(wrapper, other):
        return not wrapper.__eq__(other)
    @cut_traceback
    def __add__(wrapper, new_items):
        return wrapper.copy().union(new_items)
    @cut_traceback
    def __sub__(wrapper, items):
        return wrapper.copy().difference(items)
    @cut_traceback
    def __contains__(wrapper, item):
        obj = wrapper._obj_
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        attr = wrapper._attr_
        if not isinstance(item, attr.py_type): return False

        reverse = attr.reverse
        if not reverse.is_collection:
            obj2 = item._vals_[reverse] if reverse in item._vals_ else reverse.load(item)
            wbits = item._wbits_
            if wbits is not None:
                bit = item._bits_except_volatile_[reverse]
                if not wbits & bit: item._rbits_ |= bit
            return obj is obj2

        setdata = obj._vals_.get(attr)
        if setdata is not None:
            if item in setdata: return True
            if setdata.is_fully_loaded: return False
        setdata = attr.load(obj, (item,))
        return item in setdata
    @cut_traceback
    def create(wrapper, **kwargs):
        attr = wrapper._attr_
        reverse = attr.reverse
        if reverse.name in kwargs: throw(TypeError,
            'When using %s.%s.create(), %r attribute should not be passed explicitly'
            % (attr.entity.__name__, attr.name, reverse.name))
        kwargs[reverse.name] = wrapper._obj_
        item_type = attr.py_type
        item = item_type(**kwargs)
        wrapper.add(item)
        return item
    @cut_traceback
    def add(wrapper, new_items):
        obj = wrapper._obj_
        attr = wrapper._attr_
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot change collection %s.%s: the database session is over' % (safe_repr(obj), attr))
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        with cache.flush_disabled():
            reverse = attr.reverse
            if not reverse: throw(NotImplementedError)
            new_items = attr.check(new_items, obj)
            if not new_items: return
            setdata = obj._vals_.get(attr)
            if setdata is not None: new_items -= setdata
            if setdata is None or not setdata.is_fully_loaded:
                setdata = attr.load(obj, new_items)
            new_items -= setdata
            undo_funcs = []
            try:
                if not reverse.is_collection:
                      for item in new_items: reverse.__set__(item, obj, undo_funcs)
                else: reverse.reverse_add(new_items, obj, undo_funcs)
            except:
                for undo_func in reversed(undo_funcs): undo_func()
                raise
        setdata |= new_items
        if setdata.count is not None: setdata.count += len(new_items)
        added = setdata.added
        removed = setdata.removed
        if removed: (new_items, setdata.removed) = (new_items-removed, removed-new_items)
        if added: added |= new_items
        else: setdata.added = new_items  # added may be None

        cache.modified_collections[attr].add(obj)
        cache.modified = True
    @cut_traceback
    def __iadd__(wrapper, items):
        wrapper.add(items)
        return wrapper
    @cut_traceback
    def remove(wrapper, items):
        obj = wrapper._obj_
        attr = wrapper._attr_
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot change collection %s.%s: the database session is over' % (safe_repr(obj), attr))
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        with cache.flush_disabled():
            reverse = attr.reverse
            if not reverse: throw(NotImplementedError)
            items = attr.check(items, obj)
            setdata = obj._vals_.get(attr)
            if setdata is not None and setdata.removed:
                items -= setdata.removed
            if not items: return
            if setdata is None or not setdata.is_fully_loaded:
                setdata = attr.load(obj, items)
            items &= setdata
            undo_funcs = []
            try:
                if not reverse.is_collection:
                    for item in items: reverse.__set__(item, None, undo_funcs)
                else: reverse.reverse_remove(items, obj, undo_funcs)
            except:
                for undo_func in reversed(undo_funcs): undo_func()
                raise
        setdata -= items
        if setdata.count is not None: setdata.count -= len(items)
        added = setdata.added
        removed = setdata.removed
        if added: (items, setdata.added) = (items - added, added - items)
        if removed: removed |= items
        else: setdata.removed = items  # removed may be None

        cache.modified_collections[attr].add(obj)
        cache.modified = True
    @cut_traceback
    def __isub__(wrapper, items):
        wrapper.remove(items)
        return wrapper
    @cut_traceback
    def clear(wrapper):
        obj = wrapper._obj_
        attr = wrapper._attr_
        if not obj._session_cache_.is_alive: throw(DatabaseSessionIsOver,
            'Cannot change collection %s.%s: the database session is over' % (safe_repr(obj), attr))
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        attr.__set__(obj, None)

def unpickle_multiset(obj, attrnames, items):
    entity = obj.__class__
    for name in attrnames:
        attr = entity._adict_[name]
        if attr.reverse: entity = attr.py_type
        else:
            entity = None
            break
    if entity is None: multiset_cls = Multiset
    else: multiset_cls = entity._get_multiset_subclass_()
    return multiset_cls(obj, attrnames, items)

class Multiset(object):
    __slots__ = [ '_obj_', '_attrnames_', '_items_' ]
    @cut_traceback
    def __init__(multiset, obj, attrnames, items):
        multiset._obj_ = obj
        multiset._attrnames_ = attrnames
        if type(items) is dict: multiset._items_ = items
        else: multiset._items_ = _distinct(items)
    def __reduce__(multiset):
        return unpickle_multiset, (multiset._obj_, multiset._attrnames_, multiset._items_)
    @cut_traceback
    def distinct(multiset):
        return multiset._items_.copy()
    @cut_traceback
    def __repr__(multiset):
        if multiset._obj_._session_cache_.is_alive:
            size = _sum(multiset._items_.itervalues())
            if size == 1: size_str = ' (1 item)'
            else: size_str = ' (%d items)' % size
        else: size_str = ''
        return '<%s %r.%s%s>' % (multiset.__class__.__name__, multiset._obj_,
                                 '.'.join(multiset._attrnames_), size_str)
    @cut_traceback
    def __str__(multiset):
        items_str = '{%s}' % ', '.join('%r: %r' % pair for pair in sorted(multiset._items_.iteritems()))
        return '%s(%s)' % (multiset.__class__.__name__, items_str)
    @cut_traceback
    def __nonzero__(multiset):
        return bool(multiset._items_)
    @cut_traceback
    def __len__(multiset):
        return _sum(multiset._items_.values())
    @cut_traceback
    def __iter__(multiset):
        for item, cnt in multiset._items_.iteritems():
            for i in xrange(cnt): yield item
    @cut_traceback
    def __eq__(multiset, other):
        if isinstance(other, Multiset):
            return multiset._items_ == other._items_
        if isinstance(other, dict):
            return multiset._items_ == other
        if hasattr(other, 'keys'):
            return multiset._items_ == dict(other)
        return multiset._items_ == _distinct(other)
    @cut_traceback
    def __ne__(multiset, other):
        return not multiset.__eq__(other)
    @cut_traceback
    def __contains__(multiset, item):
        return item in multiset._items_

##class List(Collection): pass
##class Dict(Collection): pass
##class Relation(Collection): pass

class EntityIter(object):
    def __init__(self, entity):
        self.entity = entity
    def next(self):
        throw(TypeError, 'Use select(...) function or %s.select(...) method for iteration'
                         % self.entity.__name__)

next_entity_id = _count(1).next
next_new_instance_id = _count(1).next

select_re = re.compile(r'select\b', re.IGNORECASE)
lambda_re = re.compile(r'lambda\b')

class EntityMeta(type):
    def __setattr__(entity, name, val):
        if name.startswith('_') and name.endswith('_'):
            type.__setattr__(entity, name, val)
        else: throw(NotImplementedError)
    def __new__(meta, name, bases, cls_dict):
        if 'Entity' in globals():
            if '__slots__' in cls_dict: throw(TypeError, 'Entity classes cannot contain __slots__ variable')
            cls_dict['__slots__'] = ()
        return super(EntityMeta, meta).__new__(meta, name, bases, cls_dict)
    @cut_traceback
    def __init__(entity, name, bases, cls_dict):
        super(EntityMeta, entity).__init__(name, bases, cls_dict)
        entity._database_ = None
        if name == 'Entity': return

        databases = set()
        for base_class in bases:
            if isinstance(base_class, EntityMeta):
                database = base_class._database_
                if database is None: throw(ERDiagramError, 'Base Entity does not belong to any database')
                databases.add(database)
        if not databases: assert False
        elif len(databases) > 1: throw(ERDiagramError,
            'With multiple inheritance of entities, all entities must belong to the same database')
        database = databases.pop()

        if entity.__name__ in database.entities:
            throw(ERDiagramError, 'Entity %s already exists' % entity.__name__)
        assert entity.__name__ not in database.__dict__

        if database.schema is not None: throw(ERDiagramError,
            'Cannot define entity %r: database mapping has already been generated' % entity.__name__)

        entity._database_ = database

        entity._id_ = next_entity_id()
        direct_bases = [ c for c in entity.__bases__ if issubclass(c, Entity) and c.__name__ != 'Entity' ]
        entity._direct_bases_ = direct_bases
        all_bases = entity._all_bases_ = set()
        entity._subclasses_ = set()
        for base in direct_bases:
            all_bases.update(base._all_bases_)
            all_bases.add(base)
        for base in all_bases:
            base._subclasses_.add(entity)
        if direct_bases:
            roots = set(base._root_ for base in direct_bases)
            if len(roots) > 1: throw(ERDiagramError,
                'With multiple inheritance of entities, inheritance graph must be diamond-like')
            root = entity._root_ = roots.pop()
            if root._discriminator_attr_ is None:
                assert root._discriminator_ is None
                Discriminator.create_default_attr(root)
        else:
            entity._root_ = entity
            entity._discriminator_attr_ = None

        base_attrs = []
        base_attrs_dict = {}
        for base in direct_bases:
            for a in base._attrs_:
                prev = base_attrs_dict.get(a.name)
                if prev is None:
                    base_attrs_dict[a.name] = a
                    base_attrs.append(a)
                elif prev is not a: throw(ERDiagramError,
                    'Attribute "%s" clashes with attribute "%s" in derived entity "%s"'
                    % (prev, a, entity.__name__))
        entity._base_attrs_ = base_attrs

        new_attrs = []
        for name, attr in entity.__dict__.items():
            if name in base_attrs_dict: throw(ERDiagramError, "Name '%s' hides base attribute %s" % (name,base_attrs_dict[name]))
            if not isinstance(attr, Attribute): continue
            if name.startswith('_') and name.endswith('_'): throw(ERDiagramError,
                'Attribute name cannot both start and end with underscore. Got: %s' % name)
            if attr.entity is not None: throw(ERDiagramError,
                'Duplicate use of attribute %s in entity %s' % (attr, entity.__name__))
            attr._init_(entity, name)
            new_attrs.append(attr)
        new_attrs.sort(key=attrgetter('id'))

        keys = entity.__dict__.get('_key_dict_', {})
        for attr in new_attrs:
            if attr.is_unique: keys[(attr,)] = isinstance(attr, PrimaryKey)
        for key, is_pk in keys.items():
            for attr in key:
                if attr.entity is not entity: throw(ERDiagramError,
                    'Invalid use of attribute %s in entity %s' % (attr, entity.__name__))
                key_type = 'primary key' if is_pk else 'unique index'
                if attr.is_collection or attr.is_discriminator or (is_pk and not attr.is_required and not attr.auto):
                    throw(TypeError, '%s attribute %s cannot be part of %s' % (attr.__class__.__name__, attr, key_type))
                if isinstance(attr.py_type, type) and issubclass(attr.py_type, float):
                    throw(TypeError, 'Attribute %s of type float cannot be part of %s' % (attr, key_type))
                if is_pk and attr.is_volatile:
                    throw(TypeError, 'Volatile attribute %s cannot be part of primary key' % attr)
                if not attr.is_required:
                    if attr.nullable is False:
                        throw(TypeError, 'Optional attribute %s must be nullable, because it is part of composite key' % attr)
                    attr.nullable = True
                    if attr.is_string and attr.default == '' and not hasattr(attr, 'original_default'):
                        attr.default = None

        primary_keys = set(key for key, is_pk in keys.items() if is_pk)
        if direct_bases:
            if primary_keys: throw(ERDiagramError, 'Primary key cannot be redefined in derived classes')
            for base in direct_bases:
                keys[base._pk_attrs_] = True
                for key in base._keys_: keys[key] = False
            primary_keys = set(key for key, is_pk in keys.items() if is_pk)

        if len(primary_keys) > 1: throw(ERDiagramError, 'Only one primary key can be defined in each entity class')
        elif not primary_keys:
            if hasattr(entity, 'id'): throw(ERDiagramError,
                "Cannot create primary key for %s automatically because name 'id' is alredy in use" % entity.__name__)
            attr = PrimaryKey(int, auto=True)
            attr._init_(entity, 'id')
            type.__setattr__(entity, 'id', attr)  # entity.id = attr
            new_attrs.insert(0, attr)
            pk_attrs = (attr,)
            keys[pk_attrs] = True
        else: pk_attrs = primary_keys.pop()
        for i, attr in enumerate(pk_attrs): attr.pk_offset = i
        entity._pk_columns_ = None
        entity._pk_attrs_ = pk_attrs
        entity._pk_is_composite_ = len(pk_attrs) > 1
        entity._pk_ = len(pk_attrs) > 1 and pk_attrs or pk_attrs[0]
        entity._keys_ = [ key for key, is_pk in keys.items() if not is_pk ]
        entity._simple_keys_ = [ key[0] for key in entity._keys_ if len(key) == 1 ]
        entity._composite_keys_ = [ key for key in entity._keys_ if len(key) > 1 ]

        entity._new_attrs_ = new_attrs
        entity._attrs_ = base_attrs + new_attrs
        entity._adict_ = dict((attr.name, attr) for attr in entity._attrs_)
        entity._subclass_attrs_ = set()
        for base in entity._all_bases_:
            base._subclass_attrs_.update(new_attrs)

        entity._bits_ = {}
        entity._bits_except_volatile_ = {}
        next_offset = _count().next
        all_bits = all_bits_except_volatile = 0
        for attr in entity._attrs_:
            if attr.is_collection or attr.is_discriminator or attr.pk_offset is not None: bit = 0
            else: bit = 1 << next_offset()
            all_bits |= bit
            entity._bits_[attr] = bit
            if attr.is_volatile: bit = 0
            all_bits_except_volatile |= bit
            entity._bits_except_volatile_[attr] = bit
        entity._all_bits_ = all_bits
        entity._all_bits_except_volatile_ = all_bits_except_volatile

        try: table_name = entity.__dict__['_table_']
        except KeyError: entity._table_ = None
        else:
            if not isinstance(table_name, basestring):
                if not isinstance(table_name, (list, tuple)): throw(TypeError,
                    '%s._table_ property must be a string. Got: %r' % (entity.__name__, table_name))
                for name_part in table_name:
                    if not isinstance(name_part, basestring):throw(TypeError,
                        'Each part of table name must be a string. Got: %r' % name_part)
                entity._table_ = table_name = tuple(table_name)

        database.entities[entity.__name__] = entity
        setattr(database, entity.__name__, entity)

        entity._cached_max_id_sql_ = None
        entity._find_sql_cache_ = {}
        entity._batchload_sql_cache_ = {}
        entity._insert_sql_cache_ = {}
        entity._update_sql_cache_ = {}
        entity._delete_sql_cache_ = {}

        entity._propagation_mixin_ = None
        entity._set_wrapper_subclass_ = None
        entity._multiset_subclass_ = None

        if '_discriminator_' not in entity.__dict__:
            entity._discriminator_ = None
        if entity._discriminator_ is not None and not entity._discriminator_attr_:
            Discriminator.create_default_attr(entity)
        if entity._discriminator_attr_:
            entity._discriminator_attr_.process_entity_inheritance(entity)

        iter_name = entity._default_iter_name_ = (
            ''.join(letter for letter in entity.__name__ if letter.isupper()).lower()
            or entity.__name__
            )
        for_expr = ast.GenExprFor(ast.AssName(iter_name, 'OP_ASSIGN'), ast.Name('.0'), [])
        inner_expr = ast.GenExprInner(ast.Name(iter_name), [ for_expr ])
        entity._default_genexpr_ = inner_expr
    def _resolve_attr_types_(entity):
        database = entity._database_
        for attr in entity._new_attrs_:
            py_type = attr.py_type
            if isinstance(py_type, basestring):
                rentity = database.entities.get(py_type)
                if rentity is None:
                    throw(ERDiagramError, 'Entity definition %s was not found' % py_type)
                attr.py_type = py_type = rentity
            elif isinstance(py_type, types.FunctionType):
                rentity = py_type()
                if not isinstance(rentity, EntityMeta): throw(TypeError,
                    'Invalid type of attribute %s: expected entity class, got %r' % (attr, rentity))
                attr.py_type = py_type = rentity
            if isinstance(py_type, EntityMeta) and py_type.__name__ == 'Entity': throw(TypeError,
                'Cannot link attribute %s to abstract Entity class. Use specific Entity subclass instead' % attr)
    def _link_reverse_attrs_(entity):
        database = entity._database_
        for attr in entity._new_attrs_:
            py_type = attr.py_type
            if not issubclass(py_type, Entity): continue

            entity2 = py_type
            if entity2._database_ is not database:
                throw(ERDiagramError, 'Interrelated entities must belong to same database. '
                                   'Entities %s and %s belongs to different databases'
                                   % (entity.__name__, entity2.__name__))
            reverse = attr.reverse
            if isinstance(reverse, basestring):
                attr2 = getattr(entity2, reverse, None)
                if attr2 is None: throw(ERDiagramError, 'Reverse attribute %s.%s not found' % (entity2.__name__, reverse))
            elif isinstance(reverse, Attribute):
                attr2 = reverse
                if attr2.entity is not entity2: throw(ERDiagramError, 'Incorrect reverse attribute %s used in %s' % (attr2, attr)) ###
            elif reverse is not None: throw(ERDiagramError, "Value of 'reverse' option must be string. Got: %r" % type(reverse))
            else:
                candidates1 = []
                candidates2 = []
                for attr2 in entity2._new_attrs_:
                    if attr2.py_type not in (entity, entity.__name__): continue
                    reverse2 = attr2.reverse
                    if reverse2 in (attr, attr.name): candidates1.append(attr2)
                    elif not reverse2:
                        if attr2 is attr: continue
                        candidates2.append(attr2)
                msg = 'Ambiguous reverse attribute for %s'
                if len(candidates1) > 1: throw(ERDiagramError, msg % attr)
                elif len(candidates1) == 1: attr2 = candidates1[0]
                elif len(candidates2) > 1: throw(ERDiagramError, msg % attr)
                elif len(candidates2) == 1: attr2 = candidates2[0]
                else: throw(ERDiagramError, 'Reverse attribute for %s not found' % attr)

            type2 = attr2.py_type
            if type2 != entity:
                throw(ERDiagramError, 'Inconsistent reverse attributes %s and %s' % (attr, attr2))
            reverse2 = attr2.reverse
            if reverse2 not in (None, attr, attr.name):
                throw(ERDiagramError, 'Inconsistent reverse attributes %s and %s' % (attr, attr2))

            if attr.is_required and attr2.is_required: throw(ERDiagramError,
                "At least one attribute of one-to-one relationship %s - %s must be optional" % (attr, attr2))

            attr.reverse = attr2
            attr2.reverse = attr
            attr.linked()
            attr2.linked()
    def _get_pk_columns_(entity):
        if entity._pk_columns_ is not None: return entity._pk_columns_
        pk_columns = []
        pk_converters = []
        pk_paths = []
        for attr in entity._pk_attrs_:
            attr_columns = attr.get_columns()
            attr_col_paths = attr.col_paths
            attr.pk_columns_offset = len(pk_columns)
            pk_columns.extend(attr_columns)
            pk_converters.extend(attr.converters)
            pk_paths.extend(attr_col_paths)
        entity._pk_columns_ = pk_columns
        entity._pk_converters_ = pk_converters
        entity._pk_nones_ = (None,) * len(pk_columns)
        entity._pk_paths_ = pk_paths
        return pk_columns
    def __iter__(entity):
        return EntityIter(entity)
    def _normalize_args_(entity, kwargs, setdefault=False):
        avdict = {}
        if setdefault:
            for name in ifilterfalse(entity._adict_.__contains__, kwargs):
                throw(TypeError, 'Unknown attribute %r' % name)
            for attr in entity._attrs_:
                val = kwargs.get(attr.name, DEFAULT)
                avdict[attr] = attr.check(val, None, entity, from_db=False)
        else:
            get = entity._adict_.get
            for name, val in kwargs.iteritems():
                attr = get(name)
                if attr is None: throw(TypeError, 'Unknown attribute %r' % name)
                avdict[attr] = attr.check(val, None, entity, from_db=False)
        if entity._pk_is_composite_:
            pkval = map(avdict.get, entity._pk_attrs_)
            if None in pkval: pkval = None
            else: pkval = tuple(pkval)
        else: pkval = avdict.get(entity._pk_attrs_[0])
        return pkval, avdict
    @cut_traceback
    def __getitem__(entity, key):
        if type(key) is not tuple: key = (key,)
        if len(key) != len(entity._pk_attrs_):
            throw(TypeError, 'Invalid count of attrs in %s primary key (%s instead of %s)'
                             % (entity.__name__, len(key), len(entity._pk_attrs_)))
        kwargs = dict(izip(imap(attrgetter('name'), entity._pk_attrs_), key))
        objects = entity._find_(1, kwargs)
        if not objects: throw(ObjectNotFound, entity, key)
        assert len(objects) == 1
        return objects[0]
    @cut_traceback
    def exists(entity, *args, **kwargs):
        if args: return entity._query_from_args_(args, kwargs, frame_depth=3).exists()
        try: objects = entity._find_(1, kwargs)
        except MultipleObjectsFoundError: return True
        return bool(objects)
    @cut_traceback
    def get(entity, *args, **kwargs):
        if args: return entity._query_from_args_(args, kwargs, frame_depth=3).get()
        objects = entity._find_(1, kwargs)  # can throw MultipleObjectsFoundError
        if not objects: return None
        assert len(objects) == 1
        return objects[0]
    @cut_traceback
    def get_for_update(entity, *args, **kwargs):
        nowait = kwargs.pop('nowait', False)
        if args: return entity._query_from_args_(args, kwargs, frame_depth=3).for_update(nowait).get()
        objects = entity._find_(1, kwargs, True, nowait)  # can throw MultipleObjectsFoundError
        if not objects: return None
        assert len(objects) == 1
        return objects[0]
    @cut_traceback
    def get_by_sql(entity, sql, globals=None, locals=None):
        objects = entity._find_by_sql_(1, sql, globals, locals, frame_depth=3)  # can throw MultipleObjectsFoundError
        if not objects: return None
        assert len(objects) == 1
        return objects[0]
    @cut_traceback
    def select(entity, func=None):
        if func is None:
            return Query(entity._default_iter_name_, entity._default_genexpr_, {}, { '.0' : entity })
        if not (type(func) is types.FunctionType or isinstance(func, basestring) and lambda_re.match(func)):
            throw(TypeError, 'Lambda function or its text representation expected. Got: %r' % func)
        return entity._query_from_lambda_(func, frame_depth=3)
    @cut_traceback
    def select_by_sql(entity, sql, globals=None, locals=None):
        return entity._find_by_sql_(None, sql, globals, locals, frame_depth=3)
    @cut_traceback
    def select_random(entity, limit):
        if entity._pk_is_composite_: return entity.select().random(limit)
        pk = entity._pk_attrs_[0]
        if not issubclass(pk.py_type, int) or entity._discriminator_ is not None and entity._root_ is not entity:
            return entity.select().random(limit)
        database = entity._database_
        cache = database._get_cache()
        if cache.modified: cache.flush()
        max_id = cache.max_id_cache.get(pk)
        if max_id is None:
            max_id_sql = entity._cached_max_id_sql_
            if max_id_sql is None:
                sql_ast = [ 'SELECT', [ 'AGGREGATES', [ 'MAX', [ 'COLUMN', None, pk.column ] ] ],
                                      [ 'FROM', [ None, 'TABLE', entity._table_ ] ] ]
                max_id_sql, adapter = database._ast2sql(sql_ast)
                entity._cached_max_id_sql_ = max_id_sql
            cursor = database._exec_sql(max_id_sql)
            max_id = cursor.fetchone()[0]
            cache.max_id_cache[pk] = max_id
        if max_id is None: return []
        if max_id <= limit * 2: return entity.select().random(limit)
        index = cache.indexes[entity._pk_attrs_]
        result = []
        tried_ids = set()
        found_in_cache = False
        for i in xrange(5):
            ids = []
            n = (limit - len(result)) * (i+1)
            for j in xrange(n * 2):
                id = randint(1, max_id)
                if id in tried_ids: continue
                if id in ids: continue
                obj = index.get(id)
                if obj is not None:
                    found_in_cache = True
                    tried_ids.add(id)
                    result.append(obj)
                    n -= 1
                else: ids.append(id)
                if len(ids) >= n: break

            if len(result) >= limit: break
            if not ids: continue
            sql, adapter, attr_offsets = entity._construct_batchload_sql_(len(ids))
            arguments = adapter([ (id,) for id in ids ])
            cursor = database._exec_sql(sql, arguments)
            objects = entity._fetch_objects(cursor, attr_offsets)
            result.extend(objects)
            tried_ids.update(ids)
            if len(result) >= limit: break

        if len(result) < limit: return entity.select().random(limit)
        
        result = result[:limit]
        if entity._subclasses_:
            seeds = cache.seeds[entity._pk_attrs_]
            if seeds:
                for obj in result:
                    if obj in seeds: obj._load_()
        if found_in_cache: shuffle(result)
        return result
    @cut_traceback
    def order_by(entity, *args):
        query = Query(entity._default_iter_name_, entity._default_genexpr_, {}, { '.0' : entity })
        return query.order_by(*args)
    def _find_(entity, max_fetch_count, kwargs, for_update=False, nowait=False):
        if entity._database_.schema is None:
            throw(ERDiagramError, 'Mapping is not generated for entity %r' % entity.__name__)
        pkval, avdict = entity._normalize_args_(kwargs, False)
        for attr in avdict:
            if attr.is_collection:
                throw(TypeError, 'Collection attribute %s cannot be specified as search criteria' % attr)
        objects = entity._find_in_cache_(pkval, avdict, for_update)
        if objects is None:
            objects = entity._find_in_db_(avdict, max_fetch_count, for_update, nowait)
        entity._set_rbits(objects, avdict)
        return objects
    def _find_in_cache_(entity, pkval, avdict, for_update=False):
        cache = entity._database_._get_cache()
        indexes = cache.indexes
        obj = None
        if pkval is not None: obj = indexes[entity._pk_attrs_].get(pkval)
        if obj is None:
            for attr in entity._simple_keys_:
                val = avdict.get(attr)
                if val is not None:
                    obj = indexes[attr].get(val)
                    if obj is not None: break
        if obj is None:
            for attrs in entity._composite_keys_:
                vals = map(avdict.get, attrs)
                if None in vals: continue
                index = indexes.get(attrs)
                if index is None: continue
                obj = index.get(tuple(vals))
                if obj is not None: break
        if obj is None:
            for attr, val in avdict.iteritems():
                if val is None: continue
                reverse = attr.reverse
                if reverse and not reverse.is_collection:
                    obj = reverse.__get__(val)
                    break
        if obj is None:
            for attr, val in avdict.iteritems():
                if isinstance(val, Entity) and val._pkval_ is None:
                    reverse = attr.reverse
                    if not reverse.is_collection:
                        obj = reverse.__get__(val)
                        if obj is None: return []
                    elif isinstance(reverse, Set):
                        filtered_objects = []
                        for obj in reverse.__get__(val):
                            for attr, val in avdict.iteritems():
                                if val != attr.get(obj): break
                            else:
                                if for_update and obj not in cache.for_update:
                                    return None  # object is found, but it is not locked
                                filtered_objects.append(obj)
                        filtered_objects.sort(key=entity._get_raw_pkval_)
                        return filtered_objects
                    else: throw(NotImplementedError)
        if obj is not None:
            if obj._discriminator_ is not None:
                if obj._subclasses_:
                    cls = obj.__class__
                    if not issubclass(entity, cls) and not issubclass(cls, entity): return []
                    seeds = cache.seeds[entity._pk_attrs_]
                    if obj in seeds: obj._load_()
                if not isinstance(obj, entity): return []
            if obj._status_ == 'marked_to_delete': return []
            for attr, val in avdict.iteritems():
                if val != attr.__get__(obj):
                    return []
            if for_update and obj not in cache.for_update:
                return None  # object is found, but it is not locked
            return [ obj ]
        return None
    def _find_in_db_(entity, avdict, max_fetch_count=None, for_update=False, nowait=False):
        if max_fetch_count is None: max_fetch_count = options.MAX_FETCH_COUNT
        database = entity._database_
        query_attrs = tuple((attr, value is None) for attr, value in sorted(avdict.iteritems()))
        single_row = (max_fetch_count == 1)
        sql, adapter, attr_offsets = entity._construct_sql_(query_attrs, not single_row, for_update, nowait)
        arguments = adapter(avdict)
        if for_update: database._get_cache().immediate = True
        cursor = database._exec_sql(sql, arguments)
        objects = entity._fetch_objects(cursor, attr_offsets, max_fetch_count, for_update=for_update)
        return objects
    def _find_by_sql_(entity, max_fetch_count, sql, globals, locals, frame_depth):
        if not isinstance(sql, basestring): throw(TypeError)
        database = entity._database_
        cursor = database._exec_raw_sql(sql, globals, locals, frame_depth+1)

        col_names = [ column_info[0].upper() for column_info in cursor.description ]
        attr_offsets = {}
        used_columns = set()
        for attr in entity._attrs_with_columns_:
            offsets = []
            for column in attr.columns:
                try: offset = col_names.index(column.upper())
                except ValueError: break
                offsets.append(offset)
                used_columns.add(offset)
            else: attr_offsets[attr] = offsets
        if len(used_columns) < len(col_names):
            for i in xrange(len(col_names)):
                if i not in used_columns: throw(NameError,
                    'Column %s does not belong to entity %s' % (cursor.description[i][0], entity.__name__))
        for attr in entity._pk_attrs_:
            if attr not in attr_offsets: throw(ValueError,
                'Primary key attribue %s was not found in query result set' % attr)

        objects = entity._fetch_objects(cursor, attr_offsets, max_fetch_count)
        return objects
    def _construct_select_clause_(entity, alias=None, distinct=False):
        attr_offsets = {}
        select_list = distinct and [ 'DISTINCT' ] or [ 'ALL' ]
        root = entity._root_
        for attr in chain(root._attrs_, root._subclass_attrs_):
            if attr.is_collection: continue
            if not attr.columns: continue
            if attr.lazy: continue
            attr_offsets[attr] = offsets = []
            for column in attr.columns:
                offsets.append(len(select_list) - 1)
                select_list.append([ 'COLUMN', alias, column ])
        return select_list, attr_offsets
    def _construct_discriminator_criteria_(entity, alias=None):
        discr_attr = entity._discriminator_attr_
        if discr_attr is None: return None
        code2cls = discr_attr.code2cls
        discr_values = [ [ 'VALUE', cls._discriminator_ ] for cls in entity._subclasses_ ]
        discr_values.append([ 'VALUE', entity._discriminator_])
        return [ 'IN', [ 'COLUMN', alias, discr_attr.column ], discr_values ]
    def _construct_batchload_sql_(entity, batch_size, attr=None):
        query_key = batch_size, attr
        cached_sql = entity._batchload_sql_cache_.get(query_key)
        if cached_sql is not None: return cached_sql
        table_name = entity._table_
        select_list, attr_offsets = entity._construct_select_clause_()
        from_list = [ 'FROM', [ None, 'TABLE', table_name ]]
        if attr is None:
            columns = entity._pk_columns_
            converters = entity._pk_converters_
        else:
            columns = attr.columns
            converters = attr.converters
        row_value_syntax = entity._database_.provider.translator_cls.row_value_syntax
        criteria_list = construct_criteria_list(None, columns, converters, row_value_syntax, batch_size)
        sql_ast = [ 'SELECT', select_list, from_list, [ 'WHERE' ] + criteria_list ]
        database = entity._database_
        sql, adapter = database._ast2sql(sql_ast)
        cached_sql = sql, adapter, attr_offsets
        entity._batchload_sql_cache_[query_key] = cached_sql
        return cached_sql
    def _construct_sql_(entity, query_attrs, order_by_pk=False, for_update=False, nowait=False):
        if nowait: assert for_update
        query_key = query_attrs, order_by_pk, for_update, nowait
        cached_sql = entity._find_sql_cache_.get(query_key)
        if cached_sql is not None: return cached_sql
        table_name = entity._table_
        select_list, attr_offsets = entity._construct_select_clause_()
        from_list = [ 'FROM', [ None, 'TABLE', table_name ]]
        where_list = [ 'WHERE' ]
        values = []

        discr_attr = entity._discriminator_attr_
        if discr_attr and (discr_attr, False) not in query_attrs:
            discr_criteria = entity._construct_discriminator_criteria_()
            if discr_criteria: where_list.append(discr_criteria)

        for attr, attr_is_none in query_attrs:
            if not attr.reverse:
                if attr_is_none: where_list.append([ 'IS_NULL', [ 'COLUMN', None, attr.column ] ])
                else:
                    if len(attr.converters) > 1: throw(NotImplementedError)
                    where_list.append([ 'EQ', [ 'COLUMN', None, attr.column ], [ 'PARAM', (attr, None, None), attr.converters[0] ] ])
            elif not attr.columns: throw(NotImplementedError)
            else:
                attr_entity = attr.py_type; assert attr_entity == attr.reverse.entity
                if attr_is_none:
                    for column in attr.columns:
                        where_list.append([ 'IS_NULL', [ 'COLUMN', None, column ] ])
                else:
                    for j, (column, converter) in enumerate(zip(attr.columns, attr_entity._pk_converters_)):
                        where_list.append([ 'EQ', [ 'COLUMN', None, column ], [ 'PARAM', (attr, None, j), converter ] ])

        if not for_update: sql_ast = [ 'SELECT', select_list, from_list, where_list ]
        else: sql_ast = [ 'SELECT_FOR_UPDATE', bool(nowait), select_list, from_list, where_list ]
        if order_by_pk: sql_ast.append([ 'ORDER_BY' ] + [ [ 'COLUMN', None, column ] for column in entity._pk_columns_ ])
        database = entity._database_
        sql, adapter = database._ast2sql(sql_ast)
        cached_sql = sql, adapter, attr_offsets
        entity._find_sql_cache_[query_key] = cached_sql
        return cached_sql
    def _fetch_objects(entity, cursor, attr_offsets, max_fetch_count=None, for_update=False, used_attrs=()):
        if max_fetch_count is None: max_fetch_count = options.MAX_FETCH_COUNT
        if max_fetch_count is not None:
            rows = cursor.fetchmany(max_fetch_count + 1)
            if len(rows) == max_fetch_count + 1:
                if max_fetch_count == 1: throw(MultipleObjectsFoundError,
                    'Multiple objects were found. Use %s.select(...) to retrieve them' % entity.__name__)
                throw(TooManyObjectsFoundError,
                    'Found more then pony.options.MAX_FETCH_COUNT=%d objects' % options.MAX_FETCH_COUNT)
        else: rows = cursor.fetchall()
        objects = []
        if attr_offsets is None:
            objects = [ entity._get_by_raw_pkval_(row, for_update) for row in rows ]
            entity._load_many_(objects)
        else:
            for row in rows:
                real_entity_subclass, pkval, avdict = entity._parse_row_(row, attr_offsets)
                obj = real_entity_subclass._new_(pkval, 'loaded', for_update)
                if obj._status_ in del_statuses: continue
                obj._db_set_(avdict)
                objects.append(obj)
        if used_attrs: entity._set_rbits(objects, used_attrs)
        return objects
    def _set_rbits(entity, objects, attrs):
        rbits_dict = {}
        get_rbits = rbits_dict.get
        for obj in objects:
            wbits = obj._wbits_
            if wbits is None: continue
            rbits = get_rbits(obj.__class__)
            if rbits is None:
                rbits = sum(imap(obj._bits_.__getitem__, attrs))
                rbits_dict[obj.__class__] = rbits
            obj._rbits_ |= rbits & ~wbits
    def _parse_row_(entity, row, attr_offsets):
        discr_attr = entity._discriminator_attr_
        if not discr_attr: real_entity_subclass = entity
        else:
            discr_offset = attr_offsets[discr_attr][0]
            discr_value = discr_attr.check(row[discr_offset], None, entity, from_db=True)
            real_entity_subclass = discr_attr.code2cls[discr_value]

        avdict = {}
        for attr in real_entity_subclass._attrs_:
            offsets = attr_offsets.get(attr)
            if offsets is None or attr.is_discriminator: continue
            avdict[attr] = attr.parse_value(row, offsets)
        if not entity._pk_is_composite_: pkval = avdict.pop(entity._pk_attrs_[0], None)
        else: pkval = tuple(avdict.pop(attr, None) for attr in entity._pk_attrs_)
        return real_entity_subclass, pkval, avdict
    def _load_many_(entity, objects):
        database = entity._database_
        cache = database._get_cache()
        seeds = cache.seeds[entity._pk_attrs_]
        if not seeds: return
        objects = set(obj for obj in objects if obj in seeds)
        objects = sorted(objects, key=attrgetter('_pkval_'))
        max_batch_size = database.provider.max_params_count // len(entity._pk_columns_)
        while objects:
            batch = objects[:max_batch_size]
            objects = objects[max_batch_size:]
            sql, adapter, attr_offsets = entity._construct_batchload_sql_(len(batch))
            arguments = adapter(batch)
            cursor = database._exec_sql(sql, arguments)
            result = entity._fetch_objects(cursor, attr_offsets)
            if len(result) < len(batch):
                for obj in result:
                    if obj not in batch: throw(UnrepeatableReadError,
                                               'Phantom object %s disappeared' % safe_repr(obj))
    def _query_from_args_(entity, args, kwargs, frame_depth):
        if len(args) > 1: throw(TypeError, 'Only one positional argument expected')
        if kwargs: throw(TypeError, 'If positional argument presented, no keyword arguments expected')
        func = args[0]
        if not (type(func) is types.FunctionType or isinstance(func, basestring) and lambda_re.match(func)):
            throw(TypeError, 'Positional argument must be lambda function or its text source. '
                             'Got: %s.get(%r)' % (entity.__name__, func))
        return entity._query_from_lambda_(func, frame_depth+1)
    def _query_from_lambda_(entity, lambda_func, frame_depth):
        globals = sys._getframe(frame_depth+1).f_globals
        locals = sys._getframe(frame_depth+1).f_locals
        if type(lambda_func) is types.FunctionType:
            names = get_lambda_args(lambda_func)
            code_key = id(lambda_func.func_code)
            cond_expr, external_names = decompile(lambda_func)
        elif isinstance(lambda_func, basestring):
            code_key = lambda_func
            lambda_ast = string2ast(lambda_func)
            if not isinstance(lambda_ast, ast.Lambda):
                throw(TypeError, 'Lambda function is expected. Got: %s' % lambda_func)
            names = get_lambda_args(lambda_ast)
            cond_expr = lambda_ast.code
        else: assert False

        if len(names) != 1: throw(TypeError,
            'Lambda query requires exactly one parameter name, like %s.select(lambda %s: ...). '
            'Got: %d parameters' % (entity.__name__, entity.__name__[0].lower(), len(names)))
        name = names[0]

        if_expr = ast.GenExprIf(cond_expr)
        for_expr = ast.GenExprFor(ast.AssName(name, 'OP_ASSIGN'), ast.Name('.0'), [ if_expr ])
        inner_expr = ast.GenExprInner(ast.Name(name), [ for_expr ])
        locals = locals.copy()
        assert '.0' not in locals
        locals['.0'] = entity
        return Query(code_key, inner_expr, globals, locals)
    def _new_(entity, pkval, status, for_update=False, undo_funcs=None):
        cache = entity._database_._get_cache()
        pk_attrs = entity._pk_attrs_
        index = cache.indexes[pk_attrs]
        if pkval is None: obj = None
        else: obj = index.get(pkval)

        if obj is None: pass
        elif status == 'created':
            if entity._pk_is_composite_: pkval = ', '.join(str(item) for item in pkval)
            throw(CacheIndexError, 'Cannot create %s: instance with primary key %s already exists'
                             % (obj.__class__.__name__, pkval))
        elif obj.__class__ is entity: pass
        elif issubclass(obj.__class__, entity): pass
        elif not issubclass(entity, obj.__class__): throw(TransactionError,
            'Unexpected class change from %s to %s for object with primary key %r' %
            (obj.__class__, entity, obj._pkval_))
        elif obj._rbits_ or obj._wbits_: throw(NotImplementedError)
        else: obj.__class__ = entity

        if obj is None:
            with cache.flush_disabled():
                obj = object.__new__(entity)
                obj._pkval_ = pkval
                obj._status_ = status
                obj._vals_ = {}
                obj._dbvals_ = {}
                obj._save_pos_ = None
                obj._session_cache_ = cache
                if pkval is not None:
                    index[pkval] = obj
                    obj._newid_ = None
                else: obj._newid_ = next_new_instance_id()
                if obj._pk_is_composite_: pairs = zip(pk_attrs, pkval)
                else: pairs = ((pk_attrs[0], pkval),)
                if status == 'loaded':
                    assert undo_funcs is None
                    obj._rbits_ = obj._wbits_ = 0
                    for attr, val in pairs:
                        obj._vals_[attr] = val
                        if attr.reverse: attr.db_update_reverse(obj, NOT_LOADED, val)
                    cache.seeds[pk_attrs].add(obj)
                elif status == 'created':
                    assert undo_funcs is not None
                    obj._rbits_ = obj._wbits_ = None
                    for attr, val in pairs:
                        obj._vals_[attr] = val
                        if attr.reverse: attr.update_reverse(obj, NOT_LOADED, val, undo_funcs)
                else: assert False
        if for_update:
            assert cache.in_transaction
            cache.for_update.add(obj)
        return obj
    def _get_by_raw_pkval_(entity, raw_pkval, for_update=False):
        i = 0
        pkval = []
        for attr in entity._pk_attrs_:
            if attr.column is not None:
                val = raw_pkval[i]
                i += 1
                if not attr.reverse: val = attr.check(val, None, entity, from_db=True)
                else: val = attr.py_type._get_by_raw_pkval_((val,))
            else:
                if not attr.reverse: throw(NotImplementedError)
                vals = raw_pkval[i:i+len(attr.columns)]
                val = attr.py_type._get_by_raw_pkval_(vals)
                i += len(attr.columns)
            pkval.append(val)
        if not entity._pk_is_composite_: pkval = pkval[0]
        else: pkval = tuple(pkval)
        obj = entity._new_(pkval, 'loaded', for_update)
        assert obj._status_ != 'cancelled'
        return obj
    def _get_propagation_mixin_(entity):
        mixin = entity._propagation_mixin_
        if mixin is not None: return mixin
        cls_dict = { '_entity_' : entity }
        for attr in entity._attrs_:
            if not attr.reverse:
                def fget(wrapper, attr=attr):
                    attrnames = wrapper._attrnames_ + (attr.name,)
                    items = [ attr.__get__(item) for item in wrapper ]
                    return Multiset(wrapper._obj_, attrnames, items)
            elif not attr.is_collection:
                def fget(wrapper, attr=attr):
                    attrnames = wrapper._attrnames_ + (attr.name,)
                    items = [ attr.__get__(item) for item in wrapper ]
                    rentity = attr.py_type
                    cls = rentity._get_multiset_subclass_()
                    return cls(wrapper._obj_, attrnames, items)
            else:
                def fget(wrapper, attr=attr):
                    cache = attr.entity._database_._get_cache()
                    cache.collection_statistics.setdefault(attr, attr.nplus1_threshold)
                    attrnames = wrapper._attrnames_ + (attr.name,)
                    items = [ subitem for item in wrapper
                                      for subitem in attr.__get__(item) ]
                    rentity = attr.py_type
                    cls = rentity._get_multiset_subclass_()
                    return cls(wrapper._obj_, attrnames, items)
            cls_dict[attr.name] = property(fget)
        result_cls_name = entity.__name__ + 'SetMixin'
        result_cls = type(result_cls_name, (object,), cls_dict)
        entity._propagation_mixin_ = result_cls
        return result_cls
    def _get_multiset_subclass_(entity):
        result_cls = entity._multiset_subclass_
        if result_cls is None:
            mixin = entity._get_propagation_mixin_()
            cls_name = entity.__name__ + 'Multiset'
            result_cls = type(cls_name, (Multiset, mixin), {})
            entity._multiset_subclass_ = result_cls
        return result_cls
    def _get_set_wrapper_subclass_(entity):
        result_cls = entity._set_wrapper_subclass_
        if result_cls is None:
            mixin = entity._get_propagation_mixin_()
            cls_name = entity.__name__ + 'Set'
            result_cls = type(cls_name, (SetWrapper, mixin), {})
            entity._set_wrapper_subclass_ = result_cls
        return result_cls
    @cut_traceback
    def describe(entity):
        result = []
        parents = ','.join(cls.__name__ for cls in entity.__bases__)
        result.append('class %s(%s):' % (entity.__name__, parents))
        if entity._base_attrs_:
            result.append('# inherited attrs')
            result.extend(attr.describe() for attr in entity._base_attrs_)
            result.append('# attrs introduced in %s' % entity.__name__)
        result.extend(attr.describe() for attr in entity._new_attrs_)
        return '\n    '.join(result)
    @cut_traceback
    @db_session(ddl=True)
    def drop_table(entity, with_all_data=False):
        entity._database_._drop_tables([ entity._table_ ], True, with_all_data)

def populate_criteria_list(criteria_list, columns, converters, params_count=0, table_alias=None):
    assert len(columns) == len(converters)
    for column, converter in zip(columns, converters):
        if converter is not None:
            criteria_list.append([ 'EQ', [ 'COLUMN', table_alias, column ],
                                         [ 'PARAM', (params_count, None, None), converter ] ])
        else:
            criteria_list.append([ 'IS_NULL', [ 'COLUMN', None, column ] ])
        params_count += 1
    return params_count

statuses = set(['created', 'cancelled', 'loaded', 'updated', 'saved', 'marked_to_delete', 'deleted'])
del_statuses = set(['marked_to_delete', 'deleted', 'cancelled'])
created_or_deleted_statuses = set(['created']) | del_statuses

def throw_object_was_deleted(obj):
    assert obj._status_ in del_statuses
    throw(OperationWithDeletedObjectError, '%s was %s'
          % (safe_repr(obj), obj._status_.replace('_', ' ')))

def unpickle_entity(d):
    entity = d.pop('__class__')
    cache = entity._database_._get_cache()
    if not entity._pk_is_composite_: pkval = d.get(entity._pk_attrs_[0].name)
    else: pkval = tuple(d[attr.name] for attr in entity._pk_attrs_)
    assert pkval is not None
    obj = entity._new_(pkval, 'loaded')
    if obj._status_ in del_statuses: return obj
    avdict = {}
    for attrname, val in d.iteritems():
        attr = entity._adict_[attrname]
        if attr.pk_offset is not None: continue
        avdict[attr] = val
    obj._db_set_(avdict, unpickling=True)
    return obj

def safe_repr(obj):
    return Entity.__repr__(obj)

class Entity(object):
    __metaclass__ = EntityMeta
    __slots__ = '_session_cache_', '_status_', '_pkval_', '_newid_', '_dbvals_', '_vals_', '_rbits_', '_wbits_', '_save_pos_', '__weakref__'
    def __reduce__(obj):
        if obj._status_ in del_statuses: throw(
            OperationWithDeletedObjectError, 'Deleted object %s cannot be pickled' % safe_repr(obj))
        if obj._status_ in ('created', 'updated'): throw(
            OrmError, '%s object %s has to be stored in DB before it can be pickled'
                      % (obj._status_.capitalize(), safe_repr(obj)))
        d = {'__class__' : obj.__class__}
        adict = obj._adict_
        for attr, val in obj._vals_.iteritems():
            if not attr.is_collection: d[attr.name] = val
        return unpickle_entity, (d,)
    @cut_traceback
    def __new__(entity, *args, **kwargs):
        if args: raise TypeError('%s constructor accept only keyword arguments. Got: %d positional argument%s'
                                 % (entity.__name__, len(args), len(args) > 1 and 's' or ''))
        if entity._database_.schema is None:
            throw(ERDiagramError, 'Mapping is not generated for entity %r' % entity.__name__)

        pkval, avdict = entity._normalize_args_(kwargs, True)
        undo_funcs = []
        cache = entity._database_._get_cache()
        indexes = cache.indexes
        indexes_update = {}
        with cache.flush_disabled():
            for attr in entity._simple_keys_:
                val = avdict[attr]
                if val is None: continue
                if val in indexes[attr]: throw(CacheIndexError,
                    'Cannot create %s: value %r for key %s already exists' % (entity.__name__, val, attr.name))
                indexes_update[attr] = val
            for attrs in entity._composite_keys_:
                vals = map(avdict.__getitem__, attrs)
                if None in vals: continue
                vals = tuple(vals)
                if vals in indexes[attrs]:
                    attr_names = ', '.join(attr.name for attr in attrs)
                    throw(CacheIndexError, 'Cannot create %s: value %s for composite key (%s) already exists'
                                     % (entity.__name__, vals, attr_names))
                indexes_update[attrs] = vals
            try:
                obj = entity._new_(pkval, 'created', undo_funcs=undo_funcs)
                for attr, val in avdict.iteritems():
                    if attr.pk_offset is not None: continue
                    elif not attr.is_collection:
                        obj._vals_[attr] = val
                        if attr.reverse: attr.update_reverse(obj, None, val, undo_funcs)
                    else: attr.__set__(obj, val, undo_funcs)
            except:
                for undo_func in reversed(undo_funcs): undo_func()
                raise
        if pkval is not None: indexes[entity._pk_attrs_][pkval] = obj
        for key, vals in indexes_update.iteritems(): indexes[key][vals] = obj
        objects_to_save = cache.objects_to_save
        obj._save_pos_ = len(objects_to_save)
        objects_to_save.append(obj)
        cache.modified = True
        return obj
    def _get_raw_pkval_(obj):
        pkval = obj._pkval_
        if not obj._pk_is_composite_:
            if not obj._pk_attrs_[0].reverse: return (pkval,)
            else: return pkval._get_raw_pkval_()
        raw_pkval = []
        append = raw_pkval.append
        for attr, val in zip(obj._pk_attrs_, pkval):
            if not attr.reverse: append(val)
            else: raw_pkval += val._get_raw_pkval_()
        return tuple(raw_pkval)
    @cut_traceback
    def __lt__(entity, other):
        return entity._cmp_(other) < 0
    @cut_traceback
    def __le__(entity, other):
        return entity._cmp_(other) <= 0
    @cut_traceback
    def __gt__(entity, other):
        return entity._cmp_(other) > 0
    @cut_traceback
    def __ge__(entity, other):
        return entity._cmp_(other) >= 0
    def _cmp_(entity, other):
        if entity is other: return 0
        if isinstance(other, Entity):
            pkval = entity._pkval_
            other_pkval = other._pkval_
            if pkval is not None:
                if other_pkval is None: return -1
                result = cmp(pkval, other_pkval)
            else:
                if other_pkval is not None: return 1
                result = cmp(entity._newid_, other._newid_)
            if result: return result
        return cmp(id(entity), id(other))
    @cut_traceback
    def __repr__(obj):
        pkval = obj._pkval_
        if pkval is None: return '%s[new:%d]' % (obj.__class__.__name__, obj._newid_)
        if obj._pk_is_composite_: pkval = ','.join(map(repr, pkval))
        else: pkval = repr(pkval)
        return '%s[%s]' % (obj.__class__.__name__, pkval)
    def _load_(obj):
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot load object %s: the database session is over' % safe_repr(obj))
        entity = obj.__class__
        database = entity._database_
        if cache is not database._get_cache():
            throw(TransactionError, "Object %s doesn't belong to current transaction" % safe_repr(obj))
        seeds = cache.seeds[entity._pk_attrs_]
        max_batch_size = database.provider.max_params_count // len(entity._pk_columns_)
        objects = [ obj ]
        if options.PREFETCHING:
            for seed in seeds:
                if len(objects) >= max_batch_size: break
                if seed is not obj: objects.append(seed)
        sql, adapter, attr_offsets = entity._construct_batchload_sql_(len(objects))
        arguments = adapter(objects)
        cursor = database._exec_sql(sql, arguments)
        objects = entity._fetch_objects(cursor, attr_offsets)
        if obj not in objects: throw(UnrepeatableReadError,
                                     'Phantom object %s disappeared' % safe_repr(obj))
    def _db_set_(obj, avdict, unpickling=False):
        assert obj._status_ not in created_or_deleted_statuses
        if not avdict: return

        cache = obj._session_cache_
        assert cache.is_alive
        cache.seeds[obj._pk_attrs_].discard(obj)

        get_val = obj._vals_.get
        get_dbval = obj._dbvals_.get
        rbits = obj._rbits_
        wbits = obj._wbits_
        for attr, new_dbval in avdict.items():
            assert attr.pk_offset is None
            assert new_dbval is not NOT_LOADED
            old_dbval = get_dbval(attr, NOT_LOADED)
            if unpickling and old_dbval is not NOT_LOADED:
                del avdict[attr]
                continue
            elif attr.py_type is float:
                if old_dbval is NOT_LOADED: pass
                elif attr.converters[0].equals(old_dbval, new_dbval):
                    del avdict[attr]
                    continue
            elif old_dbval == new_dbval:
                del avdict[attr]
                continue

            bit = obj._bits_[attr]
            if rbits & bit: throw(UnrepeatableReadError,
                'Value of %s.%s for %s was updated outside of current transaction (was: %r, now: %r)'
                % (obj.__class__.__name__, attr.name, obj, old_dbval, new_dbval))

            if attr.reverse: attr.db_update_reverse(obj, old_dbval, new_dbval)
            obj._dbvals_[attr] = new_dbval
            if wbits & bit: del avdict[attr]
            if attr.is_unique:
                old_val = get_val(attr)
                if old_val != new_dbval:
                    cache.db_update_simple_index(obj, attr, old_val, new_dbval)

        for attrs in obj._composite_keys_:
            for attr in attrs:
                if attr in avdict: break
            else: continue
            vals = map(get_val, attrs)
            prev_vals = tuple(vals)
            for i, attr in enumerate(attrs):
                if attr in avdict: vals[i] = avdict[attr]
            new_vals = tuple(vals)
            cache.db_update_composite_index(obj, attrs, prev_vals, new_vals)

        for attr, new_dbval in avdict.iteritems():
            obj._vals_[attr] = new_dbval
    def _delete_(obj, undo_funcs=None):
        status = obj._status_
        if status in del_statuses: return
        is_recursive_call = undo_funcs is not None
        if not is_recursive_call: undo_funcs = []
        cache = obj._session_cache_
        with cache.flush_disabled():
            get_val = obj._vals_.get
            undo_list = []
            objects_to_save = cache.objects_to_save
            save_pos = obj._save_pos_

            def undo_func():
                if obj._status_ == 'marked_to_delete':
                    assert objects_to_save
                    obj2 = objects_to_save.pop()
                    assert obj2 is obj
                    if save_pos is not None:
                        assert objects_to_save[save_pos] is None
                        objects_to_save[save_pos] = obj
                    obj._save_pos_ = save_pos
                obj._status_ = status
                for index, old_key in undo_list: index[old_key] = obj

            undo_funcs.append(undo_func)
            try:
                for attr in obj._attrs_:
                    reverse = attr.reverse
                    if not reverse: continue
                    if not attr.is_collection:
                        if not reverse.is_collection:
                            val = get_val(attr) if attr in obj._vals_ else attr.load(obj)
                            if val is None: continue
                            if attr.cascade_delete: val._delete_()
                            elif not reverse.is_required: reverse.__set__(val, None, undo_funcs)
                            else: throw(ConstraintError, "Cannot delete object %s, because it has associated %s, "
                                                         "and 'cascade_delete' option of %s is not set"
                                                         % (obj, attr.name, attr))
                        elif isinstance(reverse, Set):
                            if attr not in obj._vals_: continue
                            val = get_val(attr)
                            reverse.reverse_remove((val,), obj, undo_funcs)
                        else: throw(NotImplementedError)
                    elif isinstance(attr, Set):
                        set_wrapper = attr.__get__(obj)
                        if not set_wrapper.__nonzero__(): pass
                        elif attr.cascade_delete:
                            for robj in set_wrapper: robj._delete_()
                        elif not reverse.is_required: attr.__set__(obj, (), undo_funcs)
                        else: throw(ConstraintError, "Cannot delete object %s, because it has non-empty set of %s, "
                                                     "and 'cascade_delete' option of %s is not set"
                                                     % (obj, attr.name, attr))
                    else: throw(NotImplementedError)

                indexes = cache.indexes
                for attr in obj._simple_keys_:
                    val = get_val(attr)
                    if val is None: continue
                    index = indexes[attr]
                    obj2 = index.pop(val)
                    assert obj2 is obj
                    undo_list.append((index, val))

                for attrs in obj._composite_keys_:
                    vals = map(get_val, attrs)
                    if None in vals: continue
                    index = indexes[attrs]
                    vals = tuple(vals)
                    obj2 = index.pop(vals)
                    assert obj2 is obj
                    undo_list.append((index, vals))

                if status == 'created':
                    assert save_pos is not None
                    objects_to_save[save_pos] = None
                    obj._save_pos_ = None
                    obj._status_ = 'cancelled'
                    if obj._pkval_ is not None:
                        pk_index = indexes[obj._pk_attrs_]
                        obj2 = pk_index.pop(obj._pkval_)
                        assert obj2 is obj
                        undo_list.append((pk_index, obj._pkval_))
                else:
                    if status == 'updated':
                        assert save_pos is not None
                        objects_to_save[save_pos] = None
                    else:
                        assert status in ('loaded', 'saved')
                        assert save_pos is None
                    obj._save_pos_ = len(objects_to_save)
                    objects_to_save.append(obj)
                    obj._status_ = 'marked_to_delete'
                    cache.modified = True
            except:
                if not is_recursive_call:
                    for undo_func in reversed(undo_funcs): undo_func()
                raise
    @cut_traceback
    def delete(obj):
        if not obj._session_cache_.is_alive: throw(DatabaseSessionIsOver,
            'Cannot delete object %s: the database session is over' % safe_repr(obj))
        obj._delete_()
    @cut_traceback
    def set(obj, **kwargs):
        cache = obj._session_cache_
        if not cache.is_alive: throw(DatabaseSessionIsOver,
            'Cannot change object %s: the database session is over' % safe_repr(obj))
        if obj._status_ in del_statuses: throw_object_was_deleted(obj)
        with cache.flush_disabled():
            avdict, collection_avdict = obj._keyargs_to_avdicts_(kwargs)
            status = obj._status_
            wbits = obj._wbits_
            get_val = obj._vals_.get
            objects_to_save = cache.objects_to_save
            if avdict:
                for attr in avdict:
                    if attr not in obj._vals_ and attr.reverse and not attr.reverse.is_collection:
                        attr.load(obj)  # loading of one-to-one relations
                if wbits is not None:
                    new_wbits = wbits
                    for attr in avdict: new_wbits |= obj._bits_[attr]
                    obj._wbits_ = new_wbits
                    if status != 'updated':
                        assert status in ('loaded', 'saved')
                        assert obj._save_pos_ is None
                        obj._status_ = 'updated'
                        obj._save_pos_ = len(objects_to_save)
                        objects_to_save.append(obj)
                        cache.modified = True
                if not collection_avdict:
                    for attr in avdict:
                        if attr.reverse or attr.is_part_of_unique_index: break
                    else:
                        obj._vals_.update(avdict)
                        return
            undo_funcs = []
            undo = []
            def undo_func():
                obj._status_ = status
                obj._wbits_ = wbits
                if status in ('loaded', 'saved'):
                    assert objects_to_save
                    obj2 = objects_to_save.pop()
                    assert obj2 is obj and obj._save_pos_ == len(objects_to_save)
                    obj._save_pos_ = None
                for index, old_key, new_key in undo:
                    if new_key is not None: del index[new_key]
                    if old_key is not None: index[old_key] = obj
            try:
                for attr in obj._simple_keys_:
                    if attr not in avdict: continue
                    new_val = avdict[attr]
                    old_val = get_val(attr)
                    if old_val != new_val: cache.update_simple_index(obj, attr, old_val, new_val, undo)
                for attrs in obj._composite_keys_:
                    for attr in attrs:
                        if attr in avdict: break
                    else: continue
                    vals = map(get_val, attrs)
                    prev_vals = tuple(vals)
                    for i, attr in enumerate(attrs):
                        if attr in avdict: vals[i] = avdict[attr]
                    new_vals = tuple(vals)
                    cache.update_composite_index(obj, attrs, prev_vals, new_vals, undo)
                for attr, new_val in avdict.iteritems():
                    if not attr.reverse: continue
                    old_val = get_val(attr)
                    attr.update_reverse(obj, old_val, new_val, undo_funcs)
                for attr, new_val in collection_avdict.iteritems():
                    attr.__set__(obj, new_val, undo_funcs)
            except:
                for undo_func in undo_funcs: undo_func()
                raise
        obj._vals_.update(avdict)
    def _keyargs_to_avdicts_(obj, kwargs):
        avdict, collection_avdict = {}, {}
        get = obj._adict_.get
        for name, new_val in kwargs.items():
            attr = get(name)
            if attr is None: throw(TypeError, 'Unknown attribute %r' % name)
            new_val = attr.check(new_val, obj, from_db=False)
            if attr.is_collection: collection_avdict[attr] = new_val
            elif attr.pk_offset is None: avdict[attr] = new_val
            elif obj._vals_.get(attr, new_val) != new_val:
                throw(TypeError, 'Cannot change value of primary key attribute %s' % attr.name)
        return avdict, collection_avdict
    @classmethod
    def _attrs_with_bit_(entity, attrs, mask=-1):
        get_bit = entity._bits_.get
        for attr in attrs:
            if get_bit(attr) & mask: yield attr
    def _construct_optimistic_criteria_(obj):
        optimistic_columns = []
        optimistic_converters = []
        optimistic_values = []
        for attr in obj._attrs_with_bit_(obj._attrs_with_columns_, obj._rbits_):
            dbval = obj._dbvals_[attr]
            optimistic_columns.extend(attr.columns)
            if dbval is not None: converters = attr.converters
            else: converters = repeat(None, len(attr.converters))
            optimistic_converters.extend(converters)
            optimistic_values.extend(attr.get_raw_values(dbval))
        return optimistic_columns, optimistic_converters, optimistic_values
    def _save_principal_objects_(obj, dependent_objects):
        if dependent_objects is None: dependent_objects = []
        elif obj in dependent_objects:
            chain = ' -> '.join(obj2.__class__.__name__ for obj2 in dependent_objects)
            throw(UnresolvableCyclicDependency, 'Cannot save cyclic chain: ' + chain)
        dependent_objects.append(obj)
        status = obj._status_
        if status == 'created': attrs = obj._attrs_with_columns_
        elif status == 'updated': attrs = obj._attrs_with_bit_(obj._attrs_with_columns_, obj._wbits_)
        else: assert False
        for attr in attrs:
            if not attr.reverse: continue
            val = obj._vals_[attr]
            if val is not None and val._status_ == 'created':
                val._save_(dependent_objects)
    def _update_dbvals_(obj, after_create):
        bits = obj._bits_
        vals = obj._vals_
        dbvals = obj._dbvals_
        indexes = obj._session_cache_.indexes
        for attr in obj._attrs_with_columns_:
            if not bits.get(attr): continue
            if attr not in vals: continue
            val = vals[attr]
            if attr.is_volatile:
                if val is not None:
                    if attr.is_unique: indexes[attr].pop(val, None)
                    for key, i in attr.composite_keys:
                        keyval = tuple(map(vals.get, key))
                        indexes[key].pop(keyval, None)
                del vals[attr]
            elif after_create and val is None:
                obj._rbits_ &= ~bits[attr]
                del vals[attr]
            else: dbvals[attr] = val
    def _save_created_(obj):
        auto_pk = (obj._pkval_ is None)
        attrs = []
        values = []
        for attr in obj._attrs_with_columns_:
            if auto_pk and attr.is_pk: continue
            val = obj._vals_[attr]
            if val is not None:
                attrs.append(attr)
                values.extend(attr.get_raw_values(val))
        attrs = tuple(attrs)

        database = obj._database_
        cached_sql = obj._insert_sql_cache_.get(attrs)
        if cached_sql is None:
            columns = []
            converters = []
            for attr in attrs:
                columns.extend(attr.columns)
                converters.extend(attr.converters)
            assert len(columns) == len(converters)
            params = [ [ 'PARAM', (i, None, None),  converter ] for i, converter in enumerate(converters) ]
            entity = obj.__class__
            if not columns and database.provider.dialect == 'Oracle':
                sql_ast = [ 'INSERT', entity._table_, obj._pk_columns_,
                            [ [ 'DEFAULT' ] for column in obj._pk_columns_ ] ]
            else: sql_ast = [ 'INSERT', entity._table_, columns, params ]
            if auto_pk: sql_ast.append(entity._pk_columns_[0])
            sql, adapter = database._ast2sql(sql_ast)
            entity._insert_sql_cache_[attrs] = sql, adapter
        else: sql, adapter = cached_sql

        arguments = adapter(values)
        try:
            if auto_pk: new_id = database._exec_sql(sql, arguments, returning_id=True)
            else: database._exec_sql(sql, arguments)
        except IntegrityError, e:
            msg = " ".join(tostring(arg) for arg in e.args)
            throw(TransactionIntegrityError,
                  'Object %r cannot be stored in the database. %s: %s'
                  % (obj, e.__class__.__name__, msg), e)
        except DatabaseError, e:
            msg = " ".join(tostring(arg) for arg in e.args)
            throw(UnexpectedError, 'Object %r cannot be stored in the database. %s: %s'
                                   % (obj, e.__class__.__name__, msg), e)

        if auto_pk:
            pk_attrs = obj._pk_attrs_
            index = obj._session_cache_.indexes[pk_attrs]
            obj2 = index.setdefault(new_id, obj)
            if obj2 is not obj: throw(TransactionIntegrityError,
                'Newly auto-generated id value %s was already used in transaction cache for another object' % new_id)
            obj._pkval_ = obj._vals_[pk_attrs[0]] = new_id
            obj._newid_ = None

        obj._status_ = 'saved'
        obj._rbits_ = obj._all_bits_except_volatile_
        obj._wbits_ = 0
        obj._update_dbvals_(True)
    def _save_updated_(obj):
        update_columns = []
        values = []
        for attr in obj._attrs_with_bit_(obj._attrs_with_columns_, obj._wbits_):
            update_columns.extend(attr.columns)
            val = obj._vals_[attr]
            values.extend(attr.get_raw_values(val))
        if update_columns:
            for attr in obj._pk_attrs_:
                val = obj._vals_[attr]
                values.extend(attr.get_raw_values(val))
            cache = obj._session_cache_
            if obj not in cache.for_update:
                optimistic_columns, optimistic_converters, optimistic_values = \
                    obj._construct_optimistic_criteria_()
                values.extend(optimistic_values)
            else: optimistic_columns = optimistic_converters = ()
            query_key = (tuple(update_columns), tuple(optimistic_columns),
                         tuple(converter is not None for converter in optimistic_converters))
            database = obj._database_
            cached_sql = obj._update_sql_cache_.get(query_key)
            if cached_sql is None:
                update_converters = []
                for attr in obj._attrs_with_bit_(obj._attrs_with_columns_, obj._wbits_):
                    update_converters.extend(attr.converters)
                assert len(update_columns) == len(update_converters)
                update_params = [ [ 'PARAM', (i, None, None), converter ] for i, converter in enumerate(update_converters) ]
                params_count = len(update_params)
                where_list = [ 'WHERE' ]
                pk_columns = obj._pk_columns_
                pk_converters = obj._pk_converters_
                params_count = populate_criteria_list(where_list, pk_columns, pk_converters, params_count)
                if optimistic_columns:
                    populate_criteria_list(where_list, optimistic_columns, optimistic_converters, params_count)
                sql_ast = [ 'UPDATE', obj._table_, zip(update_columns, update_params), where_list ]
                sql, adapter = database._ast2sql(sql_ast)
                obj._update_sql_cache_[query_key] = sql, adapter
            else: sql, adapter = cached_sql
            arguments = adapter(values)
            cursor = database._exec_sql(sql, arguments)
            if cursor.rowcount != 1:
                throw(OptimisticCheckError, 'Object %s was updated outside of current transaction' % safe_repr(obj))
        obj._status_ = 'saved'
        obj._rbits_ |= obj._wbits_ & obj._all_bits_except_volatile_
        obj._wbits_ = 0
        obj._update_dbvals_(False)
    def _save_deleted_(obj):
        values = []
        values.extend(obj._get_raw_pkval_())
        cache = obj._session_cache_
        if obj not in cache.for_update:
            optimistic_columns, optimistic_converters, optimistic_values = \
                obj._construct_optimistic_criteria_()
            values.extend(optimistic_values)
        else: optimistic_columns = optimistic_converters = ()
        query_key = (tuple(optimistic_columns), tuple(converter is not None for converter in optimistic_converters))
        database = obj._database_
        cached_sql = obj._delete_sql_cache_.get(query_key)
        if cached_sql is None:
            where_list = [ 'WHERE' ]
            params_count = populate_criteria_list(where_list, obj._pk_columns_, obj._pk_converters_)
            if optimistic_columns:
                populate_criteria_list(where_list, optimistic_columns, optimistic_converters, params_count)
            sql_ast = [ 'DELETE', obj._table_, where_list ]
            sql, adapter = database._ast2sql(sql_ast)
            obj.__class__._delete_sql_cache_[query_key] = sql, adapter
        else: sql, adapter = cached_sql
        arguments = adapter(values)
        database._exec_sql(sql, arguments)
        obj._status_ = 'deleted'
        cache.indexes[obj._pk_attrs_].pop(obj._pkval_)
    def _save_(obj, dependent_objects=None):
        cache = obj._session_cache_
        assert cache.is_alive
        status = obj._status_
        if status in ('loaded', 'saved', 'cancelled'): return

        if status in ('created', 'updated'):
            obj._save_principal_objects_(dependent_objects)

        obj._save_pos_ = None
        if status == 'created': obj._save_created_()
        elif status == 'updated': obj._save_updated_()
        elif status == 'marked_to_delete': obj._save_deleted_()
        else: assert False
    def _before_save_(obj):
        status = obj._status_
        if status == 'created': obj.before_insert()
        elif status == 'updated': obj.before_update()
        elif status == 'marked_to_delete': obj.before_delete()
    def before_insert(obj):
        pass
    def before_update(obj):
        pass
    def before_delete(obj):
        pass

def string2ast(s):
    result = string2ast_cache.get(s)
    if result is not None: return result
    module_node = parse('(%s)' % s)
    if not isinstance(module_node, ast.Module): throw(TypeError)
    stmt_node = module_node.node
    if not isinstance(stmt_node, ast.Stmt) or len(stmt_node.nodes) != 1: throw(TypeError)
    discard_node = stmt_node.nodes[0]
    if not isinstance(discard_node, ast.Discard): throw(TypeError)
    result = string2ast_cache[s] = discard_node.expr
    # result = deepcopy(result)  # no need for now, but may be needed later
    return result

@cut_traceback
def select(gen, frame_depth=0, left_join=False):
    if isinstance(gen, types.GeneratorType):
        tree, external_names = decompile(gen)
        code_key = id(gen.gi_frame.f_code)
        globals = gen.gi_frame.f_globals
        locals = gen.gi_frame.f_locals
    elif isinstance(gen, basestring):
        query_string = gen
        tree = string2ast(query_string)
        if not isinstance(tree, ast.GenExpr): throw(TypeError)
        code_key = query_string
        globals = sys._getframe(frame_depth+3).f_globals
        locals = sys._getframe(frame_depth+3).f_locals
    else: throw(TypeError)
    return Query(code_key, tree.code, globals, locals, left_join)

@cut_traceback
def left_join(gen, frame_depth=0):
    return select(gen, frame_depth=frame_depth+3, left_join=True)

@cut_traceback
def get(gen):
    return select(gen, frame_depth=3).get()

def make_aggrfunc(std_func):
    def aggrfunc(*args, **kwargs):
        if kwargs: return std_func(*args, **kwargs)
        if len(args) != 1: return std_func(*args)
        arg = args[0]
        if type(arg) is types.GeneratorType:
            try: iterator = arg.gi_frame.f_locals['.0']
            except: return std_func(*args)
            if isinstance(iterator, EntityIter):
                return getattr(select(arg), std_func.__name__)()
        return std_func(*args)
    aggrfunc.__name__ = std_func.__name__
    return aggrfunc

count = make_aggrfunc(count)
sum = make_aggrfunc(_sum)
min = make_aggrfunc(_min)
max = make_aggrfunc(_max)
avg = make_aggrfunc(_avg)

distinct = make_aggrfunc(_distinct)

@cut_traceback
def exists(gen, frame_depth=0):
    return select(gen, frame_depth=frame_depth+3).exists()

def JOIN(expr):
    return expr

def desc(expr):
    if isinstance(expr, Attribute):
        return expr.desc
    if isinstance(expr, (int, long)) and expr > 0:
        return -expr
    if isinstance(expr, basestring):
        return 'desc(%s)' % expr
    return expr

def extract_vars(extractors, globals, locals):
    vars = {}
    vartypes = {}
    for key, code in extractors.iteritems():
        filter_num, src = key
        if src == '.0': value = locals['.0']
        else:
            try: value = eval(code, globals, locals)
            except Exception, cause: raise ExprEvalError(src, cause)
            if src == 'None' and value is not None: throw(TranslationError)
            if src == 'True' and value is not True: throw(TranslationError)
            if src == 'False' and value is not False: throw(TranslationError)
        try: vartypes[key] = get_normalized_type_of(value)
        except TypeError:
            if not isinstance(value, dict):
                unsupported = False
                try: value = tuple(value)
                except: unsupported = True
            else: unsupported = True
            if unsupported:
                typename = type(value).__name__
                if src == '.0': throw(TypeError, 'Cannot iterate over non-entity object')
                throw(TypeError, 'Expression %s has unsupported type %r' % (src, typename))
            vartypes[key] = get_normalized_type_of(value)
        vars[key] = value
    return vars, vartypes

def unpickle_query(query_result):
    return query_result

class Query(object):
    def __init__(query, code_key, tree, globals, locals, left_join=False):
        assert isinstance(tree, ast.GenExprInner)
        extractors, varnames, tree = create_extractors(code_key, tree, 0)
        vars, vartypes = extract_vars(extractors, globals, locals)

        node = tree.quals[0].iter
        origin = vars[0, node.src]
        if isinstance(origin, EntityIter): origin = origin.entity
        elif not isinstance(origin, EntityMeta):
            if node.src == '.0': throw(TypeError, 'Cannot iterate over non-entity object')
            throw(TypeError, 'Cannot iterate over non-entity object %s' % node.src)
        query._origin = origin
        database = origin._database_
        if database is None: throw(TranslationError, 'Entity %s is not mapped to a database' % origin.__name__)
        if database.schema is None: throw(ERDiagramError, 'Mapping is not generated for entity %r' % origin.__name__)
        database.provider.normalize_vars(vars, vartypes)
        query._vars = vars
        query._key = code_key, tuple(map(vartypes.__getitem__, varnames)), left_join
        query._database = database

        translator = database._translator_cache.get(query._key)
        if translator is None:
            pickled_tree = query._pickled_tree = dumps(tree, 2)
            tree = loads(pickled_tree)  # tree = deepcopy(tree)
            translator_cls = database.provider.translator_cls
            translator = translator_cls(tree, extractors, vartypes, left_join=left_join)
            name_path = translator.can_be_optimized()
            if name_path:
                tree = loads(pickled_tree)  # tree = deepcopy(tree)
                try: translator = translator_cls(tree, extractors, vartypes, left_join=True, optimize=name_path)
                except OptimizationFailed: translator.optimization_failed = True
            database._translator_cache[query._key] = translator
        query._translator = translator
        query._filters = ()
        query._next_kwarg_id = 0
        query._for_update = query._nowait = False
        query._result = None
    def _clone(query, **kwargs):
        new_query = object.__new__(Query)
        new_query.__dict__.update(query.__dict__)
        new_query._result = None
        new_query.__dict__.update(kwargs)
        return new_query
    def __reduce__(query):
        return unpickle_query, (query._fetch(),)
    def _construct_sql_and_arguments(query, range=None, distinct=None, aggr_func_name=None):
        translator = query._translator
        sql_key = query._key + (range, distinct, aggr_func_name, query._for_update, query._nowait,
                                options.INNER_JOIN_SYNTAX)
        database = query._database
        cache_entry = database._constructed_sql_cache.get(sql_key)
        if cache_entry is None:
            sql_ast, attr_offsets = translator.construct_sql_ast(
                range, distinct, aggr_func_name, query._for_update, query._nowait)
            cache = database._get_cache()
            sql, adapter = database.provider.ast2sql(sql_ast)
            cache_entry = sql, adapter, attr_offsets
            database._constructed_sql_cache[sql_key] = cache_entry
        else: sql, adapter, attr_offsets = cache_entry
        arguments = adapter(query._vars)
        if query._translator.query_result_is_cacheable:
            arguments_type = type(arguments)
            if arguments_type is tuple: arguments_key = arguments
            elif arguments_type is dict: arguments_key = tuple(sorted(arguments.iteritems()))
            try: hash(arguments_key)
            except: query_key = None  # arguments are unhashable
            else: query_key = sql_key + (arguments_key)
        else: query_key = None
        return sql, arguments, attr_offsets, query_key
    def _fetch(query, range=None, distinct=None):
        translator = query._translator
        if query._result is not None:
            return QueryResult(query._result, translator.expr_type, translator.col_names)

        sql, arguments, attr_offsets, query_key = query._construct_sql_and_arguments(range, distinct)
        database = query._database
        cache = database._get_cache()
        if query._for_update: cache.immediate = True
        try: result = cache.query_results[query_key]
        except KeyError:
            cursor = database._exec_sql(sql, arguments)
            if isinstance(translator.expr_type, EntityMeta):
                entity = translator.expr_type
                result = entity._fetch_objects(cursor, attr_offsets, for_update=query._for_update,
                                               used_attrs=translator.tableref.used_attrs)
            elif len(translator.row_layout) == 1:
                func, slice_or_offset, src = translator.row_layout[0]
                result = list(starmap(func, cursor.fetchall()))
            else:
                result = [ tuple(func(sql_row[slice_or_offset])
                                 for func, slice_or_offset, src in translator.row_layout)
                           for sql_row in cursor.fetchall() ]
                for i, t in enumerate(translator.expr_type):
                    if isinstance(t, EntityMeta) and t._subclasses_: t._load_many_(row[i] for row in result)
            if query_key is not None: cache.query_results[query_key] = result
        else:
            stats = database._dblocal.stats
            stat = stats.get(sql)
            if stat is not None: stat.cache_count += 1
            else: stats[sql] = QueryStat(sql)

        query._result = result
        return QueryResult(result, translator.expr_type, translator.col_names)
    @cut_traceback
    def show(query, width=None):
        query._fetch().show(width)
    @cut_traceback
    def get(query):
        objects = query[:2]
        if not objects: return None
        if len(objects) > 1: throw(MultipleObjectsFoundError,
            'Multiple objects were found. Use select(...) to retrieve them')
        return objects[0]
    @cut_traceback
    def first(query):
        translator = query._translator
        if translator.order: pass
        elif type(translator.expr_type) is tuple:
            query = query.order_by(*[i+1 for i in xrange(len(query._translator.expr_type))])
        else:
            query = query.order_by(1)
        objects = query[:1]
        if not objects: return None
        return objects[0]
    @cut_traceback
    def without_distinct(query):
        return query._fetch(distinct=False)
    @cut_traceback
    def distinct(query):
        return query._fetch(distinct=True)
    @cut_traceback
    def exists(query):
        objects = query[:1]
        return bool(objects)
    @cut_traceback
    def __len__(query):
        return len(query._fetch())
    @cut_traceback
    def __iter__(query):
        return iter(query._fetch())
    @cut_traceback
    def order_by(query, *args):
        if not args: throw(TypeError, 'order_by() method requires at least one argument')
        if args[0] is None:
            if len(args) > 1: throw(TypeError, 'When first argument of order_by() method is None, it must be the only argument')
            tup = ((),)
            new_key = query._key + tup
            new_filters = query._filters + tup
            new_translator = query._database._translator_cache.get(new_key)
            if new_translator is None:
                new_translator = query._translator.without_order()
                query._database._translator_cache[new_key] = new_translator
            return query._clone(_key=new_key, _filters=new_filters, _translator=new_translator)

        attributes = functions = strings = numbers = False
        for arg in args:
            if isinstance(arg, basestring): strings = True
            elif type(arg) is types.FunctionType: functions = True
            elif isinstance(arg, (int, long)): numbers = True
            elif isinstance(arg, (Attribute, DescWrapper)): attributes = True
            else: throw(TypeError, "Arguments of order_by() method must be attributes, numbers, strings or lambdas. Got: %r" % arg)
        if strings + functions + numbers + attributes > 1:
            throw(TypeError, 'All arguments of order_by() method must be of the same type')
        if len(args) > 1 and strings + functions:
            throw(TypeError, 'When argument of order_by() method is string or lambda, it must be the only argument')

        if numbers or attributes:
            new_key = query._key + ('order_by', args,)
            new_filters = query._filters + ((numbers, args),)
            new_translator = query._database._translator_cache.get(new_key)
            if new_translator is None:
                if numbers: new_translator = query._translator.order_by_numbers(args)
                else: new_translator = query._translator.order_by_attributes(args)
                query._database._translator_cache[new_key] = new_translator
            return query._clone(_key=new_key, _filters=new_filters, _translator=new_translator)

        globals = sys._getframe(3).f_globals
        locals = sys._getframe(3).f_locals
        func = args[0]
        return query._process_lambda(func, globals, locals, order_by=True)
    def _process_lambda(query, func, globals, locals, order_by):
        argnames = ()
        if isinstance(func, basestring):
            func_id = func
            func_ast = string2ast(func)
            if isinstance(func_ast, ast.Lambda):
                argnames = get_lambda_args(func_ast)
                func_ast = func_ast.code
        elif type(func) is types.FunctionType:
            argnames = get_lambda_args(func)
            subquery = query._translator.subquery
            func_id = id(func.func_code)
            func_ast = decompile(func)[0]
        elif not order_by: throw(TypeError,
            'Argument of filter() method must be a lambda functon or its text. Got: %r' % func)
        else: assert False

        if argnames:
            expr_type = query._translator.expr_type
            expr_count = len(expr_type) if type(expr_type) is tuple else 1
            if len(argnames) != expr_count:
                throw(TypeError, 'Incorrect number of lambda arguments. '
                                 'Expected: %d, got: %d' % (expr_count, len(argnames)))

        filter_num = len(query._filters) + 1
        extractors, varnames, func_ast = create_extractors(func_id, func_ast, filter_num, argnames or query._translator.subquery)
        if extractors:
            vars, vartypes = extract_vars(extractors, globals, locals)
            query._database.provider.normalize_vars(vars, vartypes)
            query._vars.update(vars)
            sorted_vartypes = tuple(map(vartypes.__getitem__, varnames))
        else: vars, vartypes, sorted_vartypes = {}, {}, ()

        new_key = query._key + ((order_by and 'order_by' or 'filter', func_id, sorted_vartypes),)
        new_filters = query._filters + ((order_by, func_ast, argnames, extractors, vartypes),)
        new_translator = query._database._translator_cache.get(new_key)
        if new_translator is None:
            prev_optimized = query._translator.optimize
            new_translator = query._translator.apply_lambda(filter_num, order_by, func_ast, argnames, extractors, vartypes)
            if not prev_optimized:
                name_path = new_translator.can_be_optimized()
                if name_path:
                    tree = loads(query._pickled_tree)  # tree = deepcopy(tree)
                    prev_extractors = query._translator.extractors
                    prev_vartypes = query._translator.vartypes
                    translator_cls = query._translator.__class__
                    new_translator = translator_cls(tree, prev_extractors, prev_vartypes,
                                                    left_join=True, optimize=name_path)
                    new_translator = query._reapply_filters(new_translator)
                    new_translator = new_translator.apply_lambda(filter_num, order_by, func_ast, argnames, extractors, vartypes)
            query._database._translator_cache[new_key] = new_translator
        return query._clone(_key=new_key, _filters=new_filters, _translator=new_translator)
    def _reapply_filters(query, translator):
        for i, tup in enumerate(query._filters):
            if not tup:
                translator = translator.without_order()
            elif len(tup) == 1:
                attrnames = tup[0]
                translator.apply_kwfilters(attrnames)
            elif len(tup) == 2:
                numbers, args = tup
                if numbers: translator = translator.order_by_numbers(args)
                else: translator = translator.order_by_attributes(args)
            else:
                order_by, func_ast, argnames, extractors, vartypes = tup
                translator = translator.apply_lambda(i+1, order_by, func_ast, argnames, extractors, vartypes)
        return translator
    @cut_traceback
    def filter(query, *args, **kwargs):
        if args:
            if len(args) > 1: throw(TypeError, 'Only one positional argument is supported')
            if kwargs: throw(TypeError, 'Keyword arguments cannot be specified together with positional arguments')
            func = args[0]
            globals = sys._getframe(3).f_globals
            locals = sys._getframe(3).f_locals
            return query._process_lambda(func, globals, locals, order_by=False)
        if not kwargs: return query

        entity = query._translator.expr_type
        if not isinstance(entity, EntityMeta): throw(TypeError,
            'Keyword arguments are not allowed: since query result type is not an entity, filter() method can accept only lambda')

        get = entity._adict_.get
        filterattrs = []
        value_dict = {}
        next_id = query._next_kwarg_id
        for attrname, val in sorted(kwargs.iteritems()):
            attr = get(attrname)
            if attr is None: throw(AttributeError,
                'Entity %s does not have attribute %s' % (entity.__name__, attrname))
            if attr.is_collection: throw(TypeError,
                '%s attribute %s cannot be used as a keyword argument for filtering'
                % (attr.__class__.__name__, attr))
            val = attr.check(val, None, entity, from_db=False)
            id = next_id
            next_id += 1
            filterattrs.append((attr, id, val is None))
            value_dict[id] = val

        filterattrs = tuple(filterattrs)
        new_key = query._key + ('filter', filterattrs)
        new_filters = query._filters + ((filterattrs,),)
        new_translator = query._database._translator_cache.get(new_key)
        if new_translator is None:
            new_translator = query._translator.apply_kwfilters(filterattrs)
            query._database._translator_cache[new_key] = new_translator
        new_query = query._clone(_key=new_key, _filters=new_filters, _translator=new_translator,
                                 _next_kwarg_id=next_id)
        new_query._vars.update(value_dict)
        return new_query
    @cut_traceback
    def __getitem__(query, key):
        if isinstance(key, slice):
            step = key.step
            if step is not None and step != 1: throw(TypeError, "Parameter 'step' of slice object is not allowed here")
            start = key.start
            if start is None: start = 0
            elif start < 0: throw(TypeError, "Parameter 'start' of slice object cannot be negative")
            stop = key.stop
            if stop is None:
                if not start: return query._fetch()
                else: throw(TypeError, "Parameter 'stop' of slice object should be specified")
        else: throw(TypeError, 'If you want apply index to query, convert it to list first')
        if start >= stop: return []
        return query._fetch(range=(start, stop))
    @cut_traceback
    def limit(query, limit, offset=None):
        start = offset or 0
        stop = start + limit
        return query[start:stop]
    @cut_traceback
    def page(query, pagenum, pagesize=10):
        start = (pagenum - 1) * pagesize
        stop = pagenum * pagesize
        return query[start:stop]
    def _aggregate(query, aggr_func_name):
        translator = query._translator
        sql, arguments, attr_offsets, query_key = query._construct_sql_and_arguments(aggr_func_name=aggr_func_name)
        cache = query._database._get_cache()
        try: result = cache.query_results[query_key]
        except KeyError:
            cursor = query._database._exec_sql(sql, arguments)
            row = cursor.fetchone()
            if row is not None: result = row[0]
            else: result = None
            if result is None and aggr_func_name == 'SUM': result = 0
            if result is None: pass
            elif aggr_func_name == 'COUNT': pass
            else:
                expr_type = translator.expr_type
                provider = query._database.provider
                converter = provider.get_converter_by_py_type(expr_type)
                result = converter.sql2py(result)
            if query_key is not None: cache.query_results[query_key] = result
        return result
    @cut_traceback
    def sum(query):
        return query._aggregate('SUM')
    @cut_traceback
    def avg(query):
        return query._aggregate('AVG')
    @cut_traceback
    def min(query):
        return query._aggregate('MIN')
    @cut_traceback
    def max(query):
        return query._aggregate('MAX')
    @cut_traceback
    def count(query):
        return query._aggregate('COUNT')
    @cut_traceback
    def for_update(query, nowait=False):
        provider = query._database.provider
        if nowait and not provider.select_for_update_nowait_syntax: throw(TranslationError,
            '%s provider does not support SELECT FOR UPDATE NOWAIT syntax' % provider.dialect)
        return query._clone(_for_update=True, _nowait=nowait)
    def random(query, limit):
        return query.order_by('random()')[:limit]

def strcut(s, width):
    if len(s) <= width:
        return s + ' ' * (width - len(s))
    else:
        return s[:width-3] + '...'

class QueryResult(list):
    __slots__ = '_expr_type', '_col_names'
    def __init__(result, list, expr_type, col_names):
        result[:] = list
        result._expr_type = expr_type
        result._col_names = col_names
    def __getstate__(result):
        return list(result), result._expr_type, result._col_names
    def __setstate__(result, state):
        result[:] = state[0]
        result._expr_type = state[1]
        result._col_names = state[2]
    @cut_traceback
    def show(result, width=None):
        if not width: width = options.CONSOLE_WIDTH
        max_columns = width // 5
        expr_type = result._expr_type
        col_names = result._col_names

        def to_str(x):
            return tostring(x).replace('\n', ' ')

        if isinstance(expr_type, EntityMeta):
            entity = expr_type
            col_names = [ attr.name for attr in entity._attrs_
                                    if not attr.is_collection and not attr.lazy ][:max_columns]
            row_maker = attrgetter(*col_names)
            rows = [ map(to_str, row_maker(obj)) for obj in result ]
        elif len(col_names) == 1:
            rows = [ (to_str(obj),) for obj in result ]
        else:
            rows = [ map(to_str, row) for row in result ]

        remaining_columns = {}
        for col_num, colname in enumerate(col_names):
            if not rows: max_len = len(colname)
            else: max_len = max(len(colname), max(len(row[col_num]) for row in rows))
            remaining_columns[col_num] = max_len

        width_dict = {}
        available_width = width - len(col_names) + 1
        while remaining_columns:
            base_len = (available_width - len(remaining_columns) + 1) // len(remaining_columns)
            for col_num, max_len in remaining_columns.items():
                if max_len <= base_len:
                    width_dict[col_num] = max_len
                    del remaining_columns[col_num]
                    available_width -= max_len
                    break
            else: break
        if remaining_columns:
            base_len = available_width // len(remaining_columns)
            for col_num, max_len in remaining_columns.items():
                width_dict[col_num] = base_len

        print strjoin('|', (strcut(colname, width_dict[i]) for i, colname in enumerate(col_names)))
        print strjoin('+', ('-' * width_dict[i] for i in xrange(len(col_names))))
        for row in rows:
            print strjoin('|', (strcut(item, width_dict[i]) for i, item in enumerate(row)))

@cut_traceback
def show(entity):
    x = entity
    if isinstance(x, EntityMeta):
        print x.describe()
    elif isinstance(x, Entity):
        print 'instance of ' + x.__class__.__name__
        # width = options.CONSOLE_WIDTH
        # for attr in x._attrs_:
        #     if attr.is_collection or attr.lazy: continue
        #     value = str(attr.__get__(x)).replace('\n', ' ')
        #     print '  %s: %s' % (attr.name, strcut(value, width-len(attr.name)-4))
        # print
        QueryResult([ x ], x.__class__, None).show()
    elif isinstance(x, (basestring, types.GeneratorType)):
        select(x).show()
    elif hasattr(x, 'show'):
        x.show()
    else:
        from pprint import pprint
        pprint(x)

########NEW FILE########
__FILENAME__ = dbapiprovider
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time
from uuid import uuid4, UUID
import re

import pony
from pony.utils import is_utf8, decorator, throw, localbase
from pony.converting import str2date, str2datetime
from pony.orm.ormtypes import LongStr, LongUnicode

class DBException(Exception):
    def __init__(exc, original_exc, *args):
        args = args or getattr(original_exc, 'args', ())
        Exception.__init__(exc, *args)
        exc.original_exc = original_exc

##StandardError
##        |__Warning
##        |__Error
##           |__InterfaceError
##           |__DatabaseError
##              |__DataError
##              |__OperationalError
##              |__IntegrityError
##              |__InternalError
##              |__ProgrammingError
##              |__NotSupportedError

class Warning(DBException): pass
class Error(DBException): pass
class   InterfaceError(Error): pass
class   DatabaseError(Error): pass
class     DataError(DatabaseError): pass
class     OperationalError(DatabaseError): pass
class     IntegrityError(DatabaseError): pass
class     InternalError(DatabaseError): pass
class     ProgrammingError(DatabaseError): pass
class     NotSupportedError(DatabaseError): pass

@decorator
def wrap_dbapi_exceptions(func, provider, *args, **kwargs):
    dbapi_module = provider.dbapi_module
    try: return func(provider, *args, **kwargs)
    except dbapi_module.NotSupportedError, e: raise NotSupportedError(e)
    except dbapi_module.ProgrammingError, e: raise ProgrammingError(e)
    except dbapi_module.InternalError, e: raise InternalError(e)
    except dbapi_module.IntegrityError, e: raise IntegrityError(e)
    except dbapi_module.OperationalError, e: raise OperationalError(e)
    except dbapi_module.DataError, e: raise DataError(e)
    except dbapi_module.DatabaseError, e: raise DatabaseError(e)
    except dbapi_module.InterfaceError, e:
        if e.args == (0, '') and getattr(dbapi_module, '__name__', None) == 'MySQLdb':
            throw(InterfaceError, e, 'MySQL server misconfiguration')
        raise InterfaceError(e)
    except dbapi_module.Error, e: raise Error(e)
    except dbapi_module.Warning, e: raise Warning(e)

def unexpected_args(attr, args):
    throw(TypeError,
        'Unexpected positional argument%s for attribute %s: %r'
        % ((args > 1 and 's' or ''), attr, ', '.join(map(repr, args))))

version_re = re.compile('[0-9\.]+')

def get_version_tuple(s):
    m = version_re.match(s)
    if m is not None:
        return tuple(map(int, m.group(0).split('.')))
    return None

class DBAPIProvider(object):
    paramstyle = 'qmark'
    quote_char = '"'
    max_params_count = 200
    max_name_len = 128
    table_if_not_exists_syntax = True
    index_if_not_exists_syntax = True
    max_time_precision = default_time_precision = 6
    select_for_update_nowait_syntax = True

    dialect = None
    dbapi_module = None
    dbschema_cls = None
    translator_cls = None
    sqlbuilder_cls = None

    name_before_table = 'schema_name'
    default_schema_name = None

    def __init__(provider, *args, **kwargs):
        pool_mockup = kwargs.pop('pony_pool_mockup', None)
        if pool_mockup: provider.pool = pool_mockup
        else: provider.pool = provider.get_pool(*args, **kwargs)
        connection = provider.connect()
        provider.inspect_connection(connection)
        provider.release(connection)

    @wrap_dbapi_exceptions
    def inspect_connection(provider, connection):
        pass

    def normalize_name(provider, name):
        return name[:provider.max_name_len]

    def get_default_entity_table_name(provider, entity):
        return provider.normalize_name(entity.__name__)

    def get_default_m2m_table_name(provider, attr, reverse):
        if attr.symmetric:
            assert reverse is attr
            return attr.entity.__name__ + '_' + attr.name
        name = attr.entity.__name__ + '_' + reverse.entity.__name__
        return provider.normalize_name(name)

    def get_default_column_names(provider, attr, reverse_pk_columns=None):
        normalize = provider.normalize_name
        if reverse_pk_columns is None:
            return [ normalize(attr.name) ]
        elif len(reverse_pk_columns) == 1:
            return [ normalize(attr.name) ]
        else:
            prefix = attr.name + '_'
            return [ normalize(prefix + column) for column in reverse_pk_columns ]

    def get_default_m2m_column_names(provider, entity):
        normalize = provider.normalize_name
        columns = entity._get_pk_columns_()
        if len(columns) == 1:
            return [ normalize(entity.__name__.lower()) ]
        else:
            prefix = entity.__name__.lower() + '_'
            return [ normalize(prefix + column) for column in columns ]

    def get_default_index_name(provider, table_name, column_names, is_pk=False, is_unique=False, m2m=False):
        if is_pk: index_name = 'pk_%s' % table_name
        else:
            if is_unique: template = 'unq_%(tname)s__%(cnames)s'
            elif m2m: template = 'idx_%(tname)s'
            else: template = 'idx_%(tname)s__%(cnames)s'
            index_name = template % dict(tname=table_name,
                                         cnames='_'.join(name for name in column_names))
        return provider.normalize_name(index_name.lower())

    def get_default_fk_name(provider, child_table_name, parent_table_name, child_column_names):
        fk_name = 'fk_%s__%s' % (child_table_name, '__'.join(child_column_names))
        return provider.normalize_name(fk_name.lower())

    def split_table_name(provider, table_name):
        if isinstance(table_name, basestring): return provider.default_schema_name, table_name
        if not table_name: throw(TypeError, 'Invalid table name: %r' % table_name)
        if len(table_name) != 2:
            size = len(table_name)
            throw(TypeError, '%s qualified table name must have two components: '
                             '%s and table_name. Got %d component%s: %s'
                             % (provider.dialect, provider.name_before_table,
                                size, 's' if size != 1 else '', table_name))
        return table_name[0], table_name[1]

    def quote_name(provider, name):
        quote_char = provider.quote_char
        if isinstance(name, basestring):
            name = name.replace(quote_char, quote_char+quote_char)
            return quote_char + name + quote_char
        return '.'.join(provider.quote_name(item) for item in name)

    def normalize_vars(provider, vars, vartypes):
        pass

    def ast2sql(provider, ast):
        builder = provider.sqlbuilder_cls(provider, ast)
        return builder.sql, builder.adapter

    def should_reconnect(provider, exc):
        return False

    @wrap_dbapi_exceptions
    def connect(provider):
        return provider.pool.connect()

    @wrap_dbapi_exceptions
    def set_transaction_mode(provider, connection, cache):
        pass

    @wrap_dbapi_exceptions
    def commit(provider, connection):
        core = pony.orm.core
        if core.debug: core.log_orm('COMMIT')
        connection.commit()

    @wrap_dbapi_exceptions
    def rollback(provider, connection):
        core = pony.orm.core
        if core.debug: core.log_orm('ROLLBACK')
        connection.rollback()

    @wrap_dbapi_exceptions
    def release(provider, connection, cache=None):
        core = pony.orm.core
        if cache is not None and cache.db_session is not None and cache.db_session.ddl:
            provider.drop(connection)
        else:
            if core.debug: core.log_orm('RELEASE CONNECTION')
            provider.pool.release(connection)

    @wrap_dbapi_exceptions
    def drop(provider, connection):
        core = pony.orm.core
        if core.debug: core.log_orm('CLOSE CONNECTION')
        provider.pool.drop(connection)

    @wrap_dbapi_exceptions
    def disconnect(provider):
        core = pony.orm.core
        if core.debug: core.log_orm('DISCONNECT')
        provider.pool.disconnect()

    @wrap_dbapi_exceptions
    def execute(provider, cursor, sql, arguments=None, returning_id=False):
        if type(arguments) is list:
            assert arguments and not returning_id
            cursor.executemany(sql, arguments)
        else:
            if arguments is None: cursor.execute(sql)
            else: cursor.execute(sql, arguments)
            if returning_id: return cursor.lastrowid

    converter_classes = []

    def _get_converter_type_by_py_type(provider, py_type):
        if isinstance(py_type, type):
            for t, converter_cls in provider.converter_classes:
                if issubclass(py_type, t): return converter_cls
        throw(TypeError, 'No database converter found for type %s' % py_type)

    def get_converter_by_py_type(provider, py_type):
        converter_cls = provider._get_converter_type_by_py_type(py_type)
        return converter_cls(py_type)

    def get_converter_by_attr(provider, attr):
        py_type = attr.py_type
        converter_cls = provider._get_converter_type_by_py_type(py_type)
        return converter_cls(py_type, attr)

    def get_pool(provider, *args, **kwargs):
        return Pool(provider.dbapi_module, *args, **kwargs)

    def table_exists(provider, connection, table_name, case_sensitive=True):
        throw(NotImplementedError)

    def index_exists(provider, connection, table_name, index_name, case_sensitive=True):
        throw(NotImplementedError)

    def fk_exists(provider, connection, table_name, fk_name, case_sensitive=True):
        throw(NotImplementedError)

    def table_has_data(provider, connection, table_name):
        table_name = provider.quote_name(table_name)
        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM %s LIMIT 1' % table_name)
        return cursor.fetchone() is not None

    def disable_fk_checks(provider, connection):
        pass

    def enable_fk_checks(provider, connection, prev_state):
        pass

    def drop_table(provider, connection, table_name):
        table_name = provider.quote_name(table_name)
        cursor = connection.cursor()
        sql = 'DROP TABLE %s' % table_name
        cursor.execute(sql)

class Pool(localbase):
    def __init__(pool, dbapi_module, *args, **kwargs): # called separately in each thread
        pool.dbapi_module = dbapi_module
        pool.args = args
        pool.kwargs = kwargs
        pool.con = None
    def connect(pool):
        core = pony.orm.core
        if pool.con is None:
            if core.debug: core.log_orm('GET NEW CONNECTION')
            pool.con = pool.dbapi_module.connect(*pool.args, **pool.kwargs)
        elif core.debug: core.log_orm('GET CONNECTION FROM THE LOCAL POOL')
        return pool.con
    def release(pool, con):
        assert con is pool.con
        try: con.rollback()
        except:
            pool.drop(con)
            raise
    def drop(pool, con):
        assert con is pool.con, (con, pool.con)
        pool.con = None
        con.close()
    def disconnect(pool):
        con = pool.con
        pool.con = None
        if con is not None: con.close()

class Converter(object):
    def __deepcopy__(converter, memo):
        return converter  # Converter instances are "immutable"
    def __init__(converter, py_type, attr=None):
        converter.py_type = py_type
        converter.attr = attr
        if attr is None: return
        kwargs = attr.kwargs.copy()
        converter.init(kwargs)
        for option in kwargs: throw(TypeError, 'Attribute %s has unknown option %r' % (attr, option))
    def init(converter, kwargs):
        attr = converter.attr
        if attr and attr.args: unexpected_args(attr, attr.args)
    def validate(converter, val):
        return val
    def py2sql(converter, val):
        return val
    def sql2py(converter, val):
        return val

class BoolConverter(Converter):
    def validate(converter, val):
        return bool(val)
    def sql2py(converter, val):
        return bool(val)
    def sql_type(converter):
        return "BOOLEAN"

class BasestringConverter(Converter):
    def __init__(converter, py_type, attr=None):
        converter.max_len = None
        converter.db_encoding = None
        Converter.__init__(converter, py_type, attr)
    def init(converter, kwargs):
        attr = converter.attr
        if not attr.args: max_len = None
        elif len(attr.args) > 1: unexpected_args(attr, attr.args[1:])
        else: max_len = attr.args[0]
        if issubclass(attr.py_type, (LongStr, LongUnicode)):
            if max_len is not None: throw(TypeError, 'Max length is not supported for CLOBs')
        elif max_len is None: max_len = 200
        elif not isinstance(max_len, (int, long)):
            throw(TypeError, 'Max length argument must be int. Got: %r' % max_len)
        converter.max_len = max_len
        converter.db_encoding = kwargs.pop('db_encoding', None)
    def validate(converter, val):
        max_len = converter.max_len
        val_len = len(val)
        if max_len and val_len > max_len:
            throw(ValueError, 'Value for attribute %s is too long. Max length is %d, value length is %d'
                             % (converter.attr, max_len, val_len))
        return val
    def sql_type(converter):
        if converter.max_len:
            return 'VARCHAR(%d)' % converter.max_len
        return 'TEXT'

class UnicodeConverter(BasestringConverter):
    def validate(converter, val):
        if val is None: pass
        elif isinstance(val, str): val = val.decode('ascii')
        elif not isinstance(val, unicode): throw(TypeError,
            'Value type for attribute %s must be unicode. Got: %r' % (converter.attr, type(val)))
        return BasestringConverter.validate(converter, val)

class StrConverter(BasestringConverter):
    def __init__(converter, py_type, attr=None):
        converter.encoding = 'ascii'  # for the case when attr is None
        BasestringConverter.__init__(converter, py_type, attr)
        converter.utf8 = is_utf8(converter.encoding)
    def init(converter, kwargs):
        BasestringConverter.init(converter, kwargs)
        converter.encoding = kwargs.pop('encoding', 'latin1')
    def validate(converter, val):
        if val is not None:
            if isinstance(val, str): pass
            elif isinstance(val, unicode): val = val.encode(converter.encoding)
            else: throw(TypeError, 'Value type for attribute %s must be str in encoding %r. Got: %r'
                                  % (converter.attr, converter.encoding, type(val)))
        return BasestringConverter.validate(converter, val)
    def py2sql(converter, val):
        return val.decode(converter.encoding)
    def sql2py(converter, val):
        return val.encode(converter.encoding, 'replace')

class IntConverter(Converter):
    def init(converter, kwargs):
        Converter.init(converter, kwargs)
        min_val = kwargs.pop('min', None)
        if min_val is not None and not isinstance(min_val, (int, long)):
            throw(TypeError, "'min' argument for attribute %s must be int. Got: %r" % (converter.attr, min_val))
        max_val = kwargs.pop('max', None)
        if max_val is not None and not isinstance(max_val, (int, long)):
            throw(TypeError, "'max' argument for attribute %s must be int. Got: %r" % (converter.attr, max_val))
        converter.min_val = min_val
        converter.max_val = max_val
    def validate(converter, val):
        if isinstance(val, (int, long)): pass
        elif isinstance(val, basestring):
            try: val = int(val)
            except ValueError: throw(ValueError,
                'Value type for attribute %s must be int. Got string %r' % (converter.attr, val))
        else: throw(TypeError, 'Value type for attribute %s must be int. Got: %r' % (converter.attr, type(val)))

        if converter.min_val and val < converter.min_val:
            throw(ValueError, 'Value %r of attr %s is less than the minimum allowed value %r'
                             % (val, converter.attr, converter.min_val))
        if converter.max_val and val > converter.max_val:
            throw(ValueError, 'Value %r of attr %s is greater than the maximum allowed value %r'
                             % (val, converter.attr, converter.max_val))
        return val
    def sql2py(converter, val):
        return int(val)
    def sql_type(converter):
        return 'INTEGER'

class RealConverter(Converter):
    default_tolerance = None
    def init(converter, kwargs):
        Converter.init(converter, kwargs)
        min_val = kwargs.pop('min', None)
        if min_val is not None:
            try: min_val = float(min_val)
            except ValueError:
                throw(TypeError, "Invalid value for 'min' argument for attribute %s: %r" % (converter.attr, min_val))
        max_val = kwargs.pop('max', None)
        if max_val is not None:
            try: max_val = float(max_val)
            except ValueError:
                throw(TypeError, "Invalid value for 'max' argument for attribute %s: %r" % (converter.attr, max_val))
        converter.min_val = min_val
        converter.max_val = max_val
        converter.tolerance = kwargs.pop('tolerance', converter.default_tolerance)
    def validate(converter, val):
        try: val = float(val)
        except ValueError:
            throw(TypeError, 'Invalid value for attribute %s: %r' % (converter.attr, val))
        if converter.min_val and val < converter.min_val:
            throw(ValueError, 'Value %r of attr %s is less than the minimum allowed value %r'
                             % (val, converter.attr, converter.min_val))
        if converter.max_val and val > converter.max_val:
            throw(ValueError, 'Value %r of attr %s is greater than the maximum allowed value %r'
                             % (val, converter.attr, converter.max_val))
        return val
    def equals(converter, x, y):
        tolerance = converter.tolerance
        if tolerance is None: return x == y
        denominator = max(abs(x), abs(y))
        if not denominator: return True
        diff = abs(x-y) / denominator
        return diff <= tolerance
    def sql2py(converter, val):
        return float(val)
    def sql_type(converter):
        return 'REAL'

class DecimalConverter(Converter):
    def __init__(converter, py_type, attr=None):
        converter.exp = None  # for the case when attr is None
        Converter.__init__(converter, py_type, attr)
    def init(converter, kwargs):
        attr = converter.attr
        args = attr.args
        if len(args) > 2: throw(TypeError, 'Too many positional parameters for Decimal '
                                           '(expected: precision and scale), got: %s' % args)
        if args: precision = args[0]
        else: precision = kwargs.pop('precision', 12)
        if not isinstance(precision, (int, long)):
            throw(TypeError, "'precision' positional argument for attribute %s must be int. Got: %r" % (attr, precision))
        if precision <= 0: throw(TypeError,
            "'precision' positional argument for attribute %s must be positive. Got: %r" % (attr, precision))

        if len(args) == 2: scale = args[1]
        else: scale = kwargs.pop('scale', 2)
        if not isinstance(scale, (int, long)):
            throw(TypeError, "'scale' positional argument for attribute %s must be int. Got: %r" % (attr, scale))
        if scale <= 0: throw(TypeError,
            "'scale' positional argument for attribute %s must be positive. Got: %r" % (attr, scale))

        if scale > precision: throw(ValueError, "'scale' must be less or equal 'precision'")
        converter.precision = precision
        converter.scale = scale
        converter.exp = Decimal(10) ** -scale

        min_val = kwargs.pop('min', None)
        if min_val is not None:
            try: min_val = Decimal(min_val)
            except TypeError: throw(TypeError,
                "Invalid value for 'min' argument for attribute %s: %r" % (attr, min_val))

        max_val = kwargs.pop('max', None)
        if max_val is not None:
            try: max_val = Decimal(max_val)
            except TypeError: throw(TypeError,
                "Invalid value for 'max' argument for attribute %s: %r" % (attr, max_val))

        converter.min_val = min_val
        converter.max_val = max_val
    def validate(converter, val):
        if isinstance(val, float):
            s = str(val)
            if float(s) != val: s = repr(val)
            val = Decimal(s)
        try: val = Decimal(val)
        except InvalidOperation, exc:
            throw(TypeError, 'Invalid value for attribute %s: %r' % (converter.attr, val))
        if converter.min_val is not None and val < converter.min_val:
            throw(ValueError, 'Value %r of attr %s is less than the minimum allowed value %r'
                             % (val, converter.attr, converter.min_val))
        if converter.max_val is not None and val > converter.max_val:
            throw(ValueError, 'Value %r of attr %s is greater than the maximum allowed value %r'
                             % (val, converter.attr, converter.max_val))
        return val
    def sql2py(converter, val):
        return Decimal(val)
    def sql_type(converter):
        return 'DECIMAL(%d, %d)' % (converter.precision, converter.scale)

class BlobConverter(Converter):
    def validate(converter, val):
        if isinstance(val, buffer): return val
        if isinstance(val, str): return buffer(val)
        throw(TypeError, "Attribute %r: expected type is 'buffer'. Got: %r" % (converter.attr, type(val)))
    def sql2py(converter, val):
        if not isinstance(val, buffer): val = buffer(val)
        return val
    def sql_type(converter):
        return 'BLOB'

class DateConverter(Converter):
    def validate(converter, val):
        if isinstance(val, datetime): return val.date()
        if isinstance(val, date): return val
        if isinstance(val, basestring): return str2date(val)
        throw(TypeError, "Attribute %r: expected type is 'date'. Got: %r" % (converter.attr, val))
    def sql2py(converter, val):
        if not isinstance(val, date): throw(ValueError,
            'Value of unexpected type received from database: instead of date got %s' % type(val))
        return val
    def sql_type(converter):
        return 'DATE'

class DatetimeConverter(Converter):
    sql_type_name = 'DATETIME'
    def __init__(converter, py_type, attr=None):
        converter.precision = None  # for the case when attr is None
        Converter.__init__(converter, py_type, attr)
    def init(converter, kwargs):
        attr = converter.attr
        args = attr.args        
        if len(args) > 1: throw(TypeError, 'Too many positional parameters for datetime attribute %s. '
                                           'Expected: precision, got: %r' % (attr, args))
        provider = attr.entity._database_.provider
        if args:
            precision = args[0]
            if 'precision' in kwargs: throw(TypeError,
                'Precision for datetime attribute %s has both positional and keyword value' % attr)
        else: precision = kwargs.pop('precision', provider.default_time_precision)
        if not isinstance(precision, int) or not 0 <= precision <= 6: throw(ValueError,
            'Precision value of datetime attribute %s must be between 0 and 6. Got: %r' % (attr, precision))
        if precision > provider.max_time_precision: throw(ValueError,
            'Precision value (%d) of attribute %s exceeds max datetime precision (%d) of %s %s'
            % (precision, attr, provider.max_time_precision, provider.dialect, provider.server_version))
        converter.precision = precision
    def validate(converter, val):
        if isinstance(val, datetime): pass
        elif isinstance(val, basestring): val = str2datetime(val)
        else: throw(TypeError, "Attribute %r: expected type is 'datetime'. Got: %r" % (converter.attr, val))
        p = converter.precision
        if not p: val = val.replace(microsecond=0)
        elif p == 6: pass
        else:
            rounding = 10 ** (6-p)
            microsecond = (val.microsecond // rounding) * rounding
            val = val.replace(microsecond=microsecond)
        return val
    def sql2py(converter, val):
        if not isinstance(val, datetime): throw(ValueError,
            'Value of unexpected type received from database: instead of datetime got %s' % type(val))
        return val
    def sql_type(converter):
        attr = converter.attr
        precision = converter.precision
        if not attr or precision == attr.entity._database_.provider.default_time_precision:
            return converter.sql_type_name
        return converter.sql_type_name + '(%d)' % precision

class UuidConverter(Converter):
    def __init__(converter, py_type, attr=None):
        if attr is not None and attr.auto:
            attr.auto = False
            if not attr.default: attr.default = uuid4
        Converter.__init__(converter, py_type, attr)
    def validate(converter, val):
        if isinstance(val, UUID): return val
        if isinstance(val, buffer): return UUID(bytes=val)
        if isinstance(val, basestring):
            if len(val) == 16: return UUID(bytes=val)
            return UUID(hex=val)
        if isinstance(val, int): return UUID(int=val)
        if converter.attr is not None:
            throw(ValueError, 'Value type of attribute %s must be UUID. Got: %r'
                               % (converter.attr, type(val)))
        else: throw(ValueError, 'Expected UUID value, got: %r' % type(val))
    def py2sql(converter, val):
        return buffer(val.bytes)
    sql2py = validate
    def sql_type(converter):
        return "UUID"

########NEW FILE########
__FILENAME__ = mysql
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time, timedelta
from uuid import UUID

import warnings
warnings.filterwarnings('ignore', '^Table.+already exists$', Warning, '^pony\\.orm\\.dbapiprovider$')

import MySQLdb
import MySQLdb.converters
from MySQLdb.constants import FIELD_TYPE, FLAG, CLIENT

from pony.orm import core, dbschema, dbapiprovider
from pony.orm.core import log_orm, log_sql, OperationalError
from pony.orm.dbapiprovider import DBAPIProvider, Pool, get_version_tuple, wrap_dbapi_exceptions
from pony.orm.sqltranslation import SQLTranslator
from pony.orm.sqlbuilding import SQLBuilder, join
from pony.utils import throw

class MySQLColumn(dbschema.Column):
    auto_template = '%(type)s PRIMARY KEY AUTO_INCREMENT'

class MySQLSchema(dbschema.DBSchema):
    dialect = 'MySQL'
    inline_fk_syntax = False
    column_class = MySQLColumn

class MySQLTranslator(SQLTranslator):
    dialect = 'MySQL'

class MySQLBuilder(SQLBuilder):
    dialect = 'MySQL'
    def CONCAT(builder, *args):
        return 'concat(',  join(', ', map(builder, args)), ')'
    def TRIM(builder, expr, chars=None):
        if chars is None: return 'trim(', builder(expr), ')'
        return 'trim(both ', builder(chars), ' from ' ,builder(expr), ')'
    def LTRIM(builder, expr, chars=None):
        if chars is None: return 'ltrim(', builder(expr), ')'
        return 'trim(leading ', builder(chars), ' from ' ,builder(expr), ')'
    def RTRIM(builder, expr, chars=None):
        if chars is None: return 'rtrim(', builder(expr), ')'
        return 'trim(trailing ', builder(chars), ' from ' ,builder(expr), ')'
    def YEAR(builder, expr):
        return 'year(', builder(expr), ')'
    def MONTH(builder, expr):
        return 'month(', builder(expr), ')'
    def DAY(builder, expr):
        return 'day(', builder(expr), ')'
    def HOUR(builder, expr):
        return 'hour(', builder(expr), ')'
    def MINUTE(builder, expr):
        return 'minute(', builder(expr), ')'
    def SECOND(builder, expr):
        return 'second(', builder(expr), ')'

def _string_sql_type(converter):
    result = 'VARCHAR(%d)' % converter.max_len if converter.max_len else 'LONGTEXT'
    if converter.db_encoding: result += ' CHARACTER SET %s' % converter.db_encoding
    return result

class MySQLUnicodeConverter(dbapiprovider.UnicodeConverter):
    sql_type = _string_sql_type

class MySQLStrConverter(dbapiprovider.StrConverter):
    sql_type = _string_sql_type

class MySQLLongConverter(dbapiprovider.IntConverter):
    def sql_type(converter):
        return 'BIGINT'

class MySQLRealConverter(dbapiprovider.RealConverter):
    def sql_type(converter):
        return 'DOUBLE'

class MySQLBlobConverter(dbapiprovider.BlobConverter):
    def sql_type(converter):
        return 'LONGBLOB'

class MySQLUuidConverter(dbapiprovider.UuidConverter):
    def sql_type(converter):
        return 'BINARY(16)'

class MySQLProvider(DBAPIProvider):
    dialect = 'MySQL'
    paramstyle = 'format'
    quote_char = "`"
    max_name_len = 64
    table_if_not_exists_syntax = True
    index_if_not_exists_syntax = False
    select_for_update_nowait_syntax = False
    max_time_precision = default_time_precision = 0

    dbapi_module = MySQLdb
    dbschema_cls = MySQLSchema
    translator_cls = MySQLTranslator
    sqlbuilder_cls = MySQLBuilder

    converter_classes = [
        (bool, dbapiprovider.BoolConverter),
        (unicode, MySQLUnicodeConverter),
        (str, MySQLStrConverter),
        (int, dbapiprovider.IntConverter),
        (long, MySQLLongConverter),
        (float, MySQLRealConverter),
        (Decimal, dbapiprovider.DecimalConverter),
        (buffer, MySQLBlobConverter),
        (datetime, dbapiprovider.DatetimeConverter),
        (date, dbapiprovider.DateConverter),
        (UUID, MySQLUuidConverter),
    ]

    def normalize_name(provider, name):
        return name[:provider.max_name_len].lower()

    @wrap_dbapi_exceptions
    def inspect_connection(provider, connection):
        cursor = connection.cursor()
        cursor.execute('select version()')
        row = cursor.fetchone()
        assert row is not None
        provider.server_version = get_version_tuple(row[0])
        if provider.server_version >= (5, 6, 4):
            provider.max_time_precision = 6
        cursor.execute('select database()')
        provider.default_schema_name = cursor.fetchone()[0]

    def should_reconnect(provider, exc):
        return isinstance(exc, MySQLdb.OperationalError) and exc.args[0] == 2006

    def get_pool(provider, *args, **kwargs):
        if 'conv' not in kwargs:
            conv = MySQLdb.converters.conversions.copy()
            conv[FIELD_TYPE.BLOB] = [(FLAG.BINARY, buffer)]
            conv[FIELD_TYPE.TIMESTAMP] = str2datetime
            conv[FIELD_TYPE.DATETIME] = str2datetime
            conv[FIELD_TYPE.TIME] = str2timedelta
            kwargs['conv'] = conv
        if 'charset' not in kwargs:
            kwargs['charset'] = 'utf8'
        kwargs['client_flag'] = kwargs.get('client_flag', 0) | CLIENT.FOUND_ROWS 
        return Pool(MySQLdb, *args, **kwargs)

    @wrap_dbapi_exceptions
    def set_transaction_mode(provider, connection, cache):
        assert not cache.in_transaction
        db_session = cache.db_session
        if db_session is not None and db_session.ddl:
            cursor = connection.cursor()
            cursor.execute("SHOW VARIABLES LIKE 'foreign_key_checks'")
            fk = cursor.fetchone()
            if fk is not None: fk = (fk[1] == 'ON')
            if fk:
                sql = 'SET foreign_key_checks = 0'
                if core.debug: log_orm(sql)
                cursor.execute(sql)
            cache.saved_fk_state = bool(fk)
            cache.in_transaction = True
        cache.immediate = True
        if db_session is not None and db_session.serializable:
            cursor = connection.cursor()
            sql = 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE'
            if core.debug: log_orm(sql)
            cursor.execute(sql)
            cache.in_transaction = True

    @wrap_dbapi_exceptions
    def release(provider, connection, cache=None):
        if cache is not None:
            db_session = cache.db_session
            if db_session is not None and db_session.ddl and cache.saved_fk_state:
                try:
                    cursor = connection.cursor()
                    sql = 'SET foreign_key_checks = 1'
                    if core.debug: log_orm(sql)
                    cursor.execute(sql)
                except:
                    provider.pool.drop(connection)
                    raise
        DBAPIProvider.release(provider, connection, cache)


    def table_exists(provider, connection, table_name, case_sensitive=True):
        db_name, table_name = provider.split_table_name(table_name)
        cursor = connection.cursor()
        if case_sensitive: sql = 'SELECT table_name FROM information_schema.tables ' \
                                 'WHERE table_schema=%s and table_name=%s'
        else: sql = 'SELECT table_name FROM information_schema.tables ' \
                    'WHERE table_schema=%s and UPPER(table_name)=UPPER(%s)'
        cursor.execute(sql, [ db_name, table_name ])
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def index_exists(provider, connection, table_name, index_name, case_sensitive=True):
        db_name, table_name = provider.split_table_name(table_name)
        if case_sensitive: sql = 'SELECT index_name FROM information_schema.statistics ' \
                                 'WHERE table_schema=%s and table_name=%s and index_name=%s'
        else: sql = 'SELECT index_name FROM information_schema.statistics ' \
                    'WHERE table_schema=%s and table_name=%s and UPPER(index_name)=UPPER(%s)'
        cursor = connection.cursor()
        cursor.execute(sql, [ db_name, table_name, index_name ])
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def fk_exists(provider, connection, table_name, fk_name, case_sensitive=True):
        db_name, table_name = provider.split_table_name(table_name)
        if case_sensitive: sql = 'SELECT constraint_name FROM information_schema.table_constraints ' \
                                 'WHERE table_schema=%s and table_name=%s ' \
                                 "and constraint_type='FOREIGN KEY' and constraint_name=%s"
        else: sql = 'SELECT constraint_name FROM information_schema.table_constraints ' \
                    'WHERE table_schema=%s and table_name=%s ' \
                    "and constraint_type='FOREIGN KEY' and UPPER(constraint_name)=UPPER(%s)"
        cursor = connection.cursor()
        cursor.execute(sql, [ db_name, table_name, fk_name ])
        row = cursor.fetchone()
        return row[0] if row is not None else None

provider_cls = MySQLProvider

def str2datetime(s):
    if 19 < len(s) < 26: s += '000000'[:26-len(s)]
    s = s.replace('-', ' ').replace(':', ' ').replace('.', ' ').replace('T', ' ')
    return datetime(*map(int, s.split()))

def str2timedelta(s):
    if '.' in s:
        s, fractional = s.split('.')
        microseconds = int((fractional + '000000')[:6])
    else: microseconds = 0
    h, m, s = map(int, s.split(':'))
    td = timedelta(hours=abs(h), minutes=m, seconds=s, microseconds=microseconds)
    return -td if h < 0 else td

########NEW FILE########
__FILENAME__ = oracle
import os
os.environ["NLS_LANG"] = "AMERICAN_AMERICA.UTF8"

from types import NoneType
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import cx_Oracle

from pony.orm import core, sqlbuilding, dbapiprovider, sqltranslation
from pony.orm.core import log_orm, log_sql, DatabaseError, TranslationError
from pony.orm.dbschema import DBSchema, DBObject, Table, Column
from pony.orm.dbapiprovider import DBAPIProvider, wrap_dbapi_exceptions, get_version_tuple
from pony.utils import throw

class OraTable(Table):
    def get_objects_to_create(table, created_tables=None):
        result = Table.get_objects_to_create(table, created_tables)
        for column in table.column_list:
            if column.is_pk == 'auto':
                sequence_name = column.converter.attr.kwargs.get('sequence_name')
                sequence = OraSequence(table, sequence_name)
                trigger = OraTrigger(table, column, sequence)
                result.extend((sequence, trigger))
                break
        return result

class OraSequence(DBObject):
    typename = 'Sequence'
    def __init__(sequence, table, name=None):
        sequence.table = table
        table_name = table.name
        if name is not None: sequence.name = name
        elif isinstance(table_name, basestring): sequence.name = table_name + '_SEQ'
        else: sequence.name = tuple(table_name[:-1]) + (table_name[0] + '_SEQ',)
    def exists(sequence, provider, connection, case_sensitive=True):
        if case_sensitive: sql = 'SELECT sequence_name FROM all_sequences ' \
                                 'WHERE sequence_owner = :so and sequence_name = :sn'
        else: sql = 'SELECT sequence_name FROM all_sequences ' \
                    'WHERE sequence_owner = :so and upper(sequence_name) = upper(:sn)'
        owner_name, sequence_name = provider.split_table_name(sequence.name)
        cursor = connection.cursor()
        cursor.execute(sql, dict(so=owner_name, sn=sequence_name))
        row = cursor.fetchone()
        return row[0] if row is not None else None
    def get_create_command(sequence):
        schema = sequence.table.schema
        seq_name = schema.provider.quote_name(sequence.name)
        return schema.case('CREATE SEQUENCE %s NOCACHE') % seq_name
        
trigger_template = """
CREATE TRIGGER %s
  BEFORE INSERT ON %s
  FOR EACH ROW
BEGIN
  IF :new.%s IS NULL THEN
    SELECT %s.nextval INTO :new.%s FROM DUAL;
  END IF;
END;""".strip()

class OraTrigger(DBObject):
    typename = 'Trigger'
    def __init__(trigger, table, column, sequence):
        trigger.table = table
        trigger.column = column
        trigger.sequence = sequence
        table_name = table.name
        if not isinstance(table_name, basestring): table_name = table_name[-1]
        trigger.name = table_name + '_BI' # Before Insert
    def exists(trigger, provider, connection, case_sensitive=True):
        if case_sensitive: sql = 'SELECT trigger_name FROM all_triggers ' \
                                 'WHERE table_name = :tbn AND table_owner = :o ' \
                                 'AND trigger_name = :trn AND owner = :o'
        else: sql = 'SELECT trigger_name FROM all_triggers ' \
                    'WHERE table_name = :tbn AND table_owner = :o ' \
                    'AND upper(trigger_name) = upper(:trn) AND owner = :o'
        owner_name, table_name = provider.split_table_name(trigger.table.name)
        cursor = connection.cursor()
        cursor.execute(sql, dict(tbn=table_name, trn=trigger.name, o=owner_name))
        row = cursor.fetchone()
        return row[0] if row is not None else None
    def get_create_command(trigger):
        schema = trigger.table.schema
        quote_name = schema.provider.quote_name
        trigger_name = quote_name(trigger.name)  
        table_name = quote_name(trigger.table.name)
        column_name = quote_name(trigger.column.name)
        seq_name = quote_name(trigger.sequence.name)
        return schema.case(trigger_template) % (trigger_name, table_name, column_name, seq_name, column_name)

class OraColumn(Column):
    auto_template = None

class OraSchema(DBSchema):
    dialect = 'Oracle'
    table_class = OraTable
    column_class = OraColumn

class OraNoneMonad(sqltranslation.NoneMonad):
    def __init__(monad, translator, value=None):
        assert value in (None, '')
        sqltranslation.ConstMonad.__init__(monad, translator, None)

class OraConstMonad(sqltranslation.ConstMonad):
    @staticmethod
    def new(translator, value):
        if value == '': value = None
        return sqltranslation.ConstMonad.new(translator, value)    

class OraTranslator(sqltranslation.SQLTranslator):
    dialect = 'Oracle'
    NoneMonad = OraNoneMonad
    ConstMonad = OraConstMonad

    @classmethod
    def get_normalized_type_of(translator, value):
        if value == '': return NoneType
        return sqltranslation.SQLTranslator.get_normalized_type_of(value)

class OraBuilder(sqlbuilding.SQLBuilder):
    dialect = 'Oracle'
    def INSERT(builder, table_name, columns, values, returning=None):
        result = sqlbuilding.SQLBuilder.INSERT(builder, table_name, columns, values)
        if returning is not None:
            result.extend((' RETURNING ', builder.quote_name(returning), ' INTO :new_id'))
        return result
    def SELECT_FOR_UPDATE(builder, nowait, *sections):
        assert not builder.indent
        last_section = sections[-1]
        if last_section[0] != 'LIMIT':
            return builder.SELECT(*sections), 'FOR UPDATE NOWAIT\n' if nowait else 'FOR UPDATE\n'

        from_section = sections[1]
        assert from_section[0] == 'FROM'
        if len(from_section) > 2: throw(NotImplementedError,
            'Table joins are not supported for Oracle queries which have both FOR UPDATE and ROWNUM')

        order_by_section = None
        for section in sections:
            if section[0] == 'ORDER_BY': order_by_section = section

        table_ast = from_section[1]
        assert len(table_ast) == 3 and table_ast[1] == 'TABLE'
        table_alias = table_ast[0]
        rowid = [ 'COLUMN', table_alias, 'ROWID' ]
        sql_ast = [ 'SELECT', sections[0], [ 'FROM', table_ast ], [ 'WHERE', [ 'IN', rowid,
                    ('SELECT', [ 'ROWID', ['AS', rowid, 'row-id' ] ]) + sections[1:] ] ] ]
        if order_by_section: sql_ast.append(order_by_section)
        result = builder(sql_ast)
        return result, 'FOR UPDATE NOWAIT\n' if nowait else 'FOR UPDATE\n'
    def SELECT(builder, *sections):
        last_section = sections[-1]
        limit = offset = None
        if last_section[0] == 'LIMIT':
            limit = last_section[1]
            if len(last_section) > 2: offset = last_section[2]
            sections = sections[:-1]
        result = builder.subquery(*sections)
        indent = builder.indent_spaces * builder.indent

        if sections[0][0] == 'ROWID':
            indent0 = builder.indent_spaces
            x = 't."row-id"'
        else:
            indent0 = ''
            x = 't.*'
            
        if not limit: pass
        elif not offset:
            result = [ indent0, 'SELECT * FROM (\n' ]
            builder.indent += 1
            result.extend(builder.subquery(*sections))
            builder.indent -= 1
            result.extend((indent, ') WHERE ROWNUM <= ', builder(limit), '\n'))
        else:
            indent2 = indent + builder.indent_spaces
            result = [ indent0, 'SELECT %s FROM (\n' % x, indent2, 'SELECT t.*, ROWNUM "row-num" FROM (\n' ]
            builder.indent += 2
            result.extend(builder.subquery(*sections))
            builder.indent -= 2
            result.extend((indent2, ') t '))
            if limit[0] == 'VALUE' and offset[0] == 'VALUE' \
                    and isinstance(limit[1], int) and isinstance(offset[1], int):
                total_limit = [ 'VALUE', limit[1] + offset[1] ]
                result.extend(('WHERE ROWNUM <= ', builder(total_limit), '\n'))
            else: result.extend(('WHERE ROWNUM <= ', builder(limit), ' + ', builder(offset), '\n'))
            result.extend((indent, ') t WHERE "row-num" > ', builder(offset), '\n'))
        if builder.indent:
            indent = builder.indent_spaces * builder.indent
            return '(\n', result, indent + ')'
        return result
    def ROWID(builder, *expr_list):
        return builder.ALL(*expr_list)
    def LIMIT(builder, limit, offset=None):
        assert False
    def DATE(builder, expr):
        return 'TRUNC(', builder(expr), ')'
    def RANDOM(builder):
        return 'dbms_random.value'

class OraBoolConverter(dbapiprovider.BoolConverter):
    def sql2py(converter, val):
        return bool(val)  # TODO: True/False, T/F, Y/N, Yes/No, etc.
    def sql_type(converter):
        return "NUMBER(1)"

def _string_sql_type(converter):
    if converter.max_len:
        return 'VARCHAR2(%d CHAR)' % converter.max_len
    return 'CLOB'

class OraUnicodeConverter(dbapiprovider.UnicodeConverter):
    def validate(converter, val):
        if val == '': return None
        return dbapiprovider.UnicodeConverter.validate(converter, val)
    def sql2py(converter, val):
        if isinstance(val, cx_Oracle.LOB):
            val = val.read()
            val = val.decode('utf8')
        return val
    sql_type = _string_sql_type  # TODO: Add support for NVARCHAR2 and NCLOB datatypes

class OraStrConverter(dbapiprovider.StrConverter):
    def validate(converter, val):
        if val == '': return None
        return dbapiprovider.StrConverter.validate(converter, val)
    def sql2py(converter, val):
        if isinstance(val, cx_Oracle.LOB):
            val = val.read()
            if converter.utf8: return val
            val = val.decode('utf8')
        if isinstance(val, unicode):
            val = val.encode(converter.encoding, 'replace')
        return val
    sql_type = _string_sql_type

class OraIntConverter(dbapiprovider.IntConverter):
    def init(self, kwargs):
        dbapiprovider.IntConverter.init(self, kwargs)
        sequence_name = kwargs.pop('sequence_name', None)
        if sequence_name is not None and not (self.attr.auto and self.attr.is_pk):
            throw(TypeError, "Parameter 'sequence_name' can be used only for PrimaryKey attributes with auto=True")
    def sql_type(converter):
        return 'NUMBER(38)'

class OraRealConverter(dbapiprovider.RealConverter):
    default_tolerance = 1e-14
    def sql_type(converter):
        return 'NUMBER'

class OraDecimalConverter(dbapiprovider.DecimalConverter):
    def sql_type(converter):
        return 'NUMBER(%d, %d)' % (converter.precision, converter.scale)

class OraBlobConverter(dbapiprovider.BlobConverter):
    def sql2py(converter, val):
        return buffer(val.read())

class OraDateConverter(dbapiprovider.DateConverter):
    def sql2py(converter, val):
        if isinstance(val, datetime): return val.date()
        if not isinstance(val, date): throw(ValueError,
            'Value of unexpected type received from database: instead of date got %s', type(val))
        return val

class OraDatetimeConverter(dbapiprovider.DatetimeConverter):
    sql_type_name = 'TIMESTAMP'

class OraUuidConverter(dbapiprovider.UuidConverter):
    def sql_type(converter):
        return 'RAW(16)'

class OraProvider(DBAPIProvider):
    dialect = 'Oracle'
    paramstyle = 'named'
    max_name_len = 30
    table_if_not_exists_syntax = False
    index_if_not_exists_syntax = False

    dbapi_module = cx_Oracle
    dbschema_cls = OraSchema
    translator_cls = OraTranslator
    sqlbuilder_cls = OraBuilder

    name_before_table = 'owner'

    converter_classes = [
        (bool, OraBoolConverter),
        (unicode, OraUnicodeConverter),
        (str, OraStrConverter),
        ((int, long), OraIntConverter),
        (float, OraRealConverter),
        (Decimal, OraDecimalConverter),
        (buffer, OraBlobConverter),
        (datetime, OraDatetimeConverter),
        (date, OraDateConverter),
        (UUID, OraUuidConverter),
    ]

    @wrap_dbapi_exceptions
    def inspect_connection(provider, connection):
        cursor = connection.cursor()
        cursor.execute('SELECT version FROM product_component_version '
                       "WHERE product LIKE 'Oracle Database %'")
        provider.server_version = get_version_tuple(cursor.fetchone()[0])
        cursor.execute("SELECT sys_context( 'userenv', 'current_schema' ) FROM DUAL")
        provider.default_schema_name = cursor.fetchone()[0]

    def should_reconnect(provider, exc):
        reconnect_error_codes = (
            3113,  # ORA-03113: end-of-file on communication channel
            3114,  # ORA-03114: not connected to ORACLE
            )
        return isinstance(exc, cx_Oracle.OperationalError) \
               and exc.args[0].code in reconnect_error_codes

    def normalize_name(provider, name):
        return name[:provider.max_name_len].upper()

    def normalize_vars(provider, vars, vartypes):
        for name, value in vars.iteritems():
            if value == '':
                vars[name] = None
                vartypes[name] = NoneType

    @wrap_dbapi_exceptions
    def set_transaction_mode(provider, connection, cache):
        assert not cache.in_transaction
        db_session = cache.db_session
        if db_session is not None and db_session.serializable:
            cursor = connection.cursor()
            sql = 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE'
            if core.debug: log_orm(sql)
            cursor.execute(sql)
        cache.immediate = True
        if db_session is not None and (db_session.serializable or db_session.ddl):
            cache.in_transaction = True

    @wrap_dbapi_exceptions
    def execute(provider, cursor, sql, arguments=None, returning_id=False):
        if type(arguments) is list:
            assert arguments and not returning_id
            set_input_sizes(cursor, arguments[0])
            cursor.executemany(sql, arguments)
        else:
            if arguments is not None: set_input_sizes(cursor, arguments)
            if returning_id:
                var = cursor.var(cx_Oracle.STRING, 40, cursor.arraysize, outconverter=int)
                arguments['new_id'] = var
                if arguments is None: cursor.execute(sql)
                else: cursor.execute(sql, arguments)
                return var.getvalue()
            if arguments is None: cursor.execute(sql)
            else: cursor.execute(sql, arguments)

    def get_pool(provider, *args, **kwargs):
        user = password = dsn = None
        if len(args) == 1:
            conn_str = args[0]
            if '/' in conn_str:
                user, tail = conn_str.split('/', 1)
                if '@' in tail: password, dsn = tail.split('@', 1)
            if None in (user, password, dsn): throw(ValueError,
                "Incorrect connection string (must be in form of 'user/password@dsn')")
        elif len(args) == 2: user, password = args
        elif len(args) == 3: user, password, dsn = args
        elif args: throw(ValueError, 'Invalid number of positional arguments')
        if user != kwargs.setdefault('user', user):
            throw(ValueError, 'Ambiguous value for user')
        if password != kwargs.setdefault('password', password):
            throw(ValueError, 'Ambiguous value for password')
        if dsn != kwargs.setdefault('dsn', dsn):
            throw(ValueError, 'Ambiguous value for dsn')
        kwargs.setdefault('threaded', True)
        kwargs.setdefault('min', 1)
        kwargs.setdefault('max', 10)
        kwargs.setdefault('increment', 1)
        return OraPool(**kwargs)

    def table_exists(provider, connection, table_name, case_sensitive=True):
        owner_name, table_name = provider.split_table_name(table_name)
        cursor = connection.cursor()
        if case_sensitive: sql = 'SELECT table_name FROM all_tables WHERE owner = :o AND table_name = :tn'
        else: sql = 'SELECT table_name FROM all_tables WHERE owner = :o AND upper(table_name) = upper(:tn)'
        cursor.execute(sql, dict(o=owner_name, tn=table_name))
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def index_exists(provider, connection, table_name, index_name, case_sensitive=True):
        owner_name, table_name = provider.split_table_name(table_name)
        if not isinstance(index_name, basestring): throw(NotImplementedError)
        if case_sensitive: sql = 'SELECT index_name FROM all_indexes WHERE owner = :o ' \
                                 'AND index_name = :i AND table_owner = :o AND table_name = :t'
        else: sql = 'SELECT index_name FROM all_indexes WHERE owner = :o ' \
                    'AND upper(index_name) = upper(:i) AND table_owner = :o AND table_name = :t'
        cursor = connection.cursor()
        cursor.execute(sql, dict(o=owner_name, i=index_name, t=table_name))
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def fk_exists(provider, connection, table_name, fk_name, case_sensitive=True):
        owner_name, table_name = provider.split_table_name(table_name)
        if not isinstance(fk_name, basestring): throw(NotImplementedError)
        if case_sensitive:
            sql = "SELECT constraint_name FROM user_constraints WHERE constraint_type = 'R' " \
                  'AND table_name = :tn AND constraint_name = :cn AND owner = :o'
        else: sql = "SELECT constraint_name FROM user_constraints WHERE constraint_type = 'R' " \
                    'AND table_name = :tn AND upper(constraint_name) = upper(:cn) AND owner = :o'
        cursor = connection.cursor()
        cursor.execute(sql, dict(tn=table_name, cn=fk_name, o=owner_name))
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def table_has_data(provider, connection, table_name):
        table_name = provider.quote_name(table_name)
        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM %s WHERE ROWNUM = 1' % table_name)
        return cursor.fetchone() is not None

    def drop_table(provider, connection, table_name):
        table_name = provider.quote_name(table_name)
        cursor = connection.cursor()
        sql = 'DROP TABLE %s CASCADE CONSTRAINTS' % table_name
        cursor.execute(sql)

provider_cls = OraProvider

def to_int_or_decimal(val):
    val = val.replace(',', '.')
    if '.' in val: return Decimal(val)
    return int(val)

def to_decimal(val):
    return Decimal(val.replace(',', '.'))

def output_type_handler(cursor, name, defaultType, size, precision, scale):
    if defaultType == cx_Oracle.NUMBER:
        if scale == 0:
            if precision: return cursor.var(cx_Oracle.STRING, 40, cursor.arraysize, outconverter=int)
            return cursor.var(cx_Oracle.STRING, 40, cursor.arraysize, outconverter=to_int_or_decimal)
        if scale != -127:
            return cursor.var(cx_Oracle.STRING, 100, cursor.arraysize, outconverter=to_decimal)
    elif defaultType in (cx_Oracle.STRING, cx_Oracle.FIXED_CHAR):
        return cursor.var(unicode, size, cursor.arraysize)  # from cx_Oracle example
    return None

class OraPool(object):
    def __init__(pool, **kwargs):
        pool._pool = cx_Oracle.SessionPool(**kwargs)
    def connect(pool):
        if core.debug: log_orm('GET CONNECTION')
        con = pool._pool.acquire()
        con.outputtypehandler = output_type_handler
        return con
    def release(pool, con):
        pool._pool.release(con)
    def drop(pool, con):
        pool._pool.drop(con)
    def disconnect(pool):
        pass

def get_inputsize(arg):
    if isinstance(arg, datetime):
        return cx_Oracle.TIMESTAMP
    return None

def set_input_sizes(cursor, arguments):
    if type(arguments) is dict:
        input_sizes = {}
        for name, arg in arguments.iteritems():
            size = get_inputsize(arg)
            if size is not None: input_sizes[name] = size
        cursor.setinputsizes(**input_sizes)
    elif type(arguments) is tuple:
        input_sizes = map(get_inputsize, arguments)
        cursor.setinputsizes(*input_sizes)
    else: assert False, type(arguments)

########NEW FILE########
__FILENAME__ = postgres
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID

import psycopg2
from psycopg2 import extensions

import psycopg2.extras
psycopg2.extras.register_uuid()

from pony.orm import core, dbschema, sqlbuilding, dbapiprovider
from pony.orm.core import log_orm
from pony.orm.dbapiprovider import DBAPIProvider, Pool, ProgrammingError, wrap_dbapi_exceptions
from pony.orm.sqltranslation import SQLTranslator
from pony.orm.sqlbuilding import Value
from pony.utils import throw

class PGColumn(dbschema.Column):
    auto_template = 'SERIAL PRIMARY KEY'

class PGSchema(dbschema.DBSchema):
    dialect = 'PostgreSQL'
    column_class = PGColumn

class PGTranslator(SQLTranslator):
    dialect = 'PostgreSQL'

class PGValue(Value):
    __slots__ = []
    def __unicode__(self):
        value = self.value
        if isinstance(value, bool): return value and 'true' or 'false'
        return Value.__unicode__(self)

class PGSQLBuilder(sqlbuilding.SQLBuilder):
    dialect = 'PostgreSQL'
    make_value = PGValue
    def INSERT(builder, table_name, columns, values, returning=None):
        if not values: result = [ 'INSERT INTO ', builder.quote_name(table_name) ,' DEFAULT VALUES' ]
        else: result = sqlbuilding.SQLBuilder.INSERT(builder, table_name, columns, values)
        if returning is not None: result.extend([' RETURNING ', builder.quote_name(returning) ])
        return result
    def TO_INT(builder, expr):
        return '(', builder(expr), ')::int'
    def DATE(builder, expr):
        return '(', builder(expr), ')::date'
    def RANDOM(builder):
        return 'random()'

class PGUnicodeConverter(dbapiprovider.UnicodeConverter):
    def py2sql(converter, val):
        return val.encode('utf-8')
    def sql2py(converter, val):
        if isinstance(val, unicode): return val
        return val.decode('utf-8')

class PGStrConverter(dbapiprovider.StrConverter):
    def py2sql(converter, val):
        return val.decode(converter.encoding).encode('utf-8')
    def sql2py(converter, val):
        if not isinstance(val, unicode):
            if converter.utf8: return val
            val = val.decode('utf-8')
        return val.encode(converter.encoding, 'replace')

class PGLongConverter(dbapiprovider.IntConverter):
    def sql_type(converter):
        return 'BIGINT'

class PGRealConverter(dbapiprovider.RealConverter):
    def sql_type(converter):
        return 'DOUBLE PRECISION'

class PGBlobConverter(dbapiprovider.BlobConverter):
    def sql_type(converter):
        return 'BYTEA'

class PGDatetimeConverter(dbapiprovider.DatetimeConverter):
    sql_type_name = 'TIMESTAMP'

class PGUuidConverter(dbapiprovider.UuidConverter):
    def py2sql(converter, val):
        return val

class PGPool(Pool):
    def connect(pool):
        if pool.con is None:
            if core.debug: log_orm('GET NEW CONNECTION')
            pool.con = pool.dbapi_module.connect(*pool.args, **pool.kwargs)
            if 'client_encoding' not in pool.kwargs:
                pool.con.set_client_encoding('UTF8')
        elif core.debug: log_orm('GET CONNECTION FROM THE LOCAL POOL')
        return pool.con
    def release(pool, con):
        assert con is pool.con
        try:
            con.rollback()
            con.autocommit = True
            cursor = con.cursor()
            cursor.execute('DISCARD ALL')
            con.autocommit = False
        except:
            pool.drop(con)
            raise

class PGProvider(DBAPIProvider):
    dialect = 'PostgreSQL'
    paramstyle = 'pyformat'
    max_name_len = 63
    index_if_not_exists_syntax = False

    dbapi_module = psycopg2
    dbschema_cls = PGSchema
    translator_cls = PGTranslator
    sqlbuilder_cls = PGSQLBuilder

    default_schema_name = 'public'

    def normalize_name(provider, name):
        return name[:provider.max_name_len].lower()

    @wrap_dbapi_exceptions
    def inspect_connection(provider, connection):
        provider.server_version = connection.server_version
        provider.table_if_not_exists_syntax = provider.server_version >= 90100

    def should_reconnect(provider, exc):
        return isinstance(exc, psycopg2.OperationalError) \
               and exc.pgcode is exc.pgerror is exc.cursor is None

    def get_pool(provider, *args, **kwargs):
        return PGPool(provider.dbapi_module, *args, **kwargs)

    @wrap_dbapi_exceptions
    def set_transaction_mode(provider, connection, cache):
        assert not cache.in_transaction
        if cache.immediate and connection.autocommit:
            connection.autocommit = False
            if core.debug: log_orm('SWITCH FROM AUTOCOMMIT TO TRANSACTION MODE')
        db_session = cache.db_session
        if db_session is not None and db_session.serializable:
            cursor = connection.cursor()
            sql = 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE'
            if core.debug: log_orm(sql)
            cursor.execute(sql)
        elif not cache.immediate and not connection.autocommit:
            connection.autocommit = True
            if core.debug: log_orm('SWITCH TO AUTOCOMMIT MODE')
        if db_session is not None and (db_session.serializable or db_session.ddl):
            cache.in_transaction = True

    @wrap_dbapi_exceptions
    def execute(provider, cursor, sql, arguments=None, returning_id=False):
        if isinstance(sql, unicode): sql = sql.encode('utf8')
        if type(arguments) is list:
            assert arguments and not returning_id
            cursor.executemany(sql, arguments)
        else:
            if arguments is None: cursor.execute(sql)
            else: cursor.execute(sql, arguments)
            if returning_id: return cursor.fetchone()[0]

    def table_exists(provider, connection, table_name, case_sensitive=True):
        schema_name, table_name = provider.split_table_name(table_name)
        cursor = connection.cursor()
        if case_sensitive: sql = 'SELECT tablename FROM pg_catalog.pg_tables ' \
                                 'WHERE schemaname = %s AND tablename = %s'
        else: sql = 'SELECT tablename FROM pg_catalog.pg_tables ' \
                    'WHERE schemaname = %s AND lower(tablename) = lower(%s)'
        cursor.execute(sql, (schema_name, table_name))
        row = cursor.fetchone()
        return row[0] if row is not None else None
    
    def index_exists(provider, connection, table_name, index_name, case_sensitive=True):
        schema_name, table_name = provider.split_table_name(table_name)
        cursor = connection.cursor()
        if case_sensitive: sql = 'SELECT indexname FROM pg_catalog.pg_indexes ' \
                                'WHERE schemaname = %s AND tablename = %s AND indexname = %s'
        else: sql = 'SELECT indexname FROM pg_catalog.pg_indexes ' \
                    'WHERE schemaname = %s AND tablename = %s AND lower(indexname) = lower(%s)'
        cursor.execute(sql, [ schema_name, table_name, index_name ])
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def fk_exists(provider, connection, table_name, fk_name, case_sensitive=True):
        schema_name, table_name = provider.split_table_name(table_name)
        if case_sensitive: sql = 'SELECT con.conname FROM pg_class cls ' \
                                 'JOIN pg_namespace ns ON cls.relnamespace = ns.oid ' \
                                 'JOIN pg_constraint con ON con.conrelid = cls.oid ' \
                                 'WHERE ns.nspname = %s AND cls.relname = %s ' \
                                 "AND con.contype = 'f' AND con.conname = %s"
        else: sql = 'SELECT con.conname FROM pg_class cls ' \
                    'JOIN pg_namespace ns ON cls.relnamespace = ns.oid ' \
                    'JOIN pg_constraint con ON con.conrelid = cls.oid ' \
                    'WHERE ns.nspname = %s AND cls.relname = %s ' \
                    "AND con.contype = 'f' AND lower(con.conname) = lower(%s)"
        cursor = connection.cursor()
        cursor.execute(sql, [ schema_name, table_name, fk_name ])
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def table_has_data(provider, connection, table_name):
        table_name = provider.quote_name(table_name)
        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM %s LIMIT 1' % table_name)
        return cursor.fetchone() is not None

    def drop_table(provider, connection, table_name):
        table_name = provider.quote_name(table_name)
        cursor = connection.cursor()
        sql = 'DROP TABLE %s CASCADE' % table_name
        cursor.execute(sql)

    converter_classes = [
        (bool, dbapiprovider.BoolConverter),
        (unicode, PGUnicodeConverter),
        (str, PGStrConverter),
        (long, PGLongConverter),
        (int, dbapiprovider.IntConverter),
        (float, PGRealConverter),
        (Decimal, dbapiprovider.DecimalConverter),
        (buffer, PGBlobConverter),
        (datetime, PGDatetimeConverter),
        (date, dbapiprovider.DateConverter),
        (UUID, PGUuidConverter),
    ]

provider_cls = PGProvider

########NEW FILE########
__FILENAME__ = sqlite
import os.path
import sqlite3 as sqlite
from decimal import Decimal
from datetime import datetime, date
from random import random
from time import strptime
from uuid import UUID

from pony.orm import core, dbschema, sqltranslation, dbapiprovider
from pony.orm.core import log_orm
from pony.orm.sqlbuilding import SQLBuilder, join
from pony.orm.dbapiprovider import DBAPIProvider, Pool, wrap_dbapi_exceptions
from pony.utils import localbase, datetime2timestamp, timestamp2datetime, decorator, absolutize_path, throw

class SQLiteForeignKey(dbschema.ForeignKey):
    def get_create_command(foreign_key):
        assert False

class SQLiteSchema(dbschema.DBSchema):
    dialect = 'SQLite'
    named_foreign_keys = False
    fk_class = SQLiteForeignKey

class SQLiteTranslator(sqltranslation.SQLTranslator):
    dialect = 'SQLite'
    sqlite_version = sqlite.sqlite_version_info
    row_value_syntax = False

class SQLiteBuilder(SQLBuilder):
    dialect = 'SQLite'
    def SELECT_FOR_UPDATE(builder, nowait, *sections):
        assert not builder.indent and not nowait
        return builder.SELECT(*sections)
    def INSERT(builder, table_name, columns, values, returning=None):
        if not values: return 'INSERT INTO %s DEFAULT VALUES' % builder.quote_name(table_name)
        return SQLBuilder.INSERT(builder, table_name, columns, values, returning)
    def TODAY(builder):
        return "date('now', 'localtime')"
    def NOW(builder):
        return "datetime('now', 'localtime')"
    def YEAR(builder, expr):
        return 'cast(substr(', builder(expr), ', 1, 4) as integer)'
    def MONTH(builder, expr):
        return 'cast(substr(', builder(expr), ', 6, 2) as integer)'
    def DAY(builder, expr):
        return 'cast(substr(', builder(expr), ', 9, 2) as integer)'
    def HOUR(builder, expr):
        return 'cast(substr(', builder(expr), ', 12, 2) as integer)'
    def MINUTE(builder, expr):
        return 'cast(substr(', builder(expr), ', 15, 2) as integer)'
    def SECOND(builder, expr):
        return 'cast(substr(', builder(expr), ', 18, 2) as integer)'
    def MIN(builder, *args):
        if len(args) == 0: assert False
        elif len(args) == 1: fname = 'MIN'
        else: fname = 'min'
        return fname, '(',  join(', ', map(builder, args)), ')'
    def MAX(builder, *args):
        if len(args) == 0: assert False
        elif len(args) == 1: fname = 'MAX'
        else: fname = 'max'
        return fname, '(',  join(', ', map(builder, args)), ')'
    def RANDOM(builder):
        return 'rand()'  # return '(random() / 9223372036854775807.0 + 1.0) / 2.0'

class SQLiteStrConverter(dbapiprovider.StrConverter):
    def py2sql(converter, val):
        if converter.utf8: return val
        return val.decode(converter.encoding)

class SQLiteDecimalConverter(dbapiprovider.DecimalConverter):
    def sql2py(converter, val):
        try: val = Decimal(str(val))
        except: return val
        exp = converter.exp
        if exp is not None: val = val.quantize(exp)
        return val
    def py2sql(converter, val):
        if type(val) is not Decimal: val = Decimal(val)
        exp = converter.exp
        if exp is not None: val = val.quantize(exp)
        return str(val)

class SQLiteDateConverter(dbapiprovider.DateConverter):
    def sql2py(converter, val):
        try:
            time_tuple = strptime(val[:10], '%Y-%m-%d')
            return date(*time_tuple[:3])
        except: return val
    def py2sql(converter, val):
        return val.strftime('%Y-%m-%d')

class SQLiteDatetimeConverter(dbapiprovider.DatetimeConverter):
    def sql2py(converter, val):
        try: return timestamp2datetime(val)
        except: return val
    def py2sql(converter, val):
        return datetime2timestamp(val)

class SQLiteProvider(DBAPIProvider):
    dialect = 'SQLite'
    max_name_len = 1024
    select_for_update_nowait_syntax = False

    dbapi_module = sqlite
    dbschema_cls = SQLiteSchema
    translator_cls = SQLiteTranslator
    sqlbuilder_cls = SQLiteBuilder

    name_before_table = 'db_name'

    server_version = sqlite.sqlite_version_info

    converter_classes = [
        (bool, dbapiprovider.BoolConverter),
        (unicode, dbapiprovider.UnicodeConverter),
        (str, SQLiteStrConverter),
        ((int, long), dbapiprovider.IntConverter),
        (float, dbapiprovider.RealConverter),
        (Decimal, SQLiteDecimalConverter),
        (buffer, dbapiprovider.BlobConverter),
        (datetime, SQLiteDatetimeConverter),
        (date, SQLiteDateConverter),
        (UUID, dbapiprovider.UuidConverter),
    ]

    @wrap_dbapi_exceptions
    def set_transaction_mode(provider, connection, cache):
        assert not cache.in_transaction
        cursor = connection.cursor()

        db_session = cache.db_session
        if db_session is not None and db_session.ddl:
            cursor.execute('PRAGMA foreign_keys')
            fk = cursor.fetchone()
            if fk is not None: fk = fk[0]
            if fk:
                sql = 'PRAGMA foreign_keys = false'
                if core.debug: log_orm(sql)
                cursor.execute(sql)
            cache.saved_fk_state = bool(fk)
            cache.in_transaction = True

        if cache.immediate:
            sql = 'BEGIN IMMEDIATE TRANSACTION'
            if core.debug: log_orm(sql)
            cursor.execute(sql)
            cache.in_transaction = True
        elif core.debug: log_orm('SWITCH TO AUTOCOMMIT MODE')

    @wrap_dbapi_exceptions
    def release(provider, connection, cache=None):
        if cache is not None:
            db_session = cache.db_session
            if db_session is not None and db_session.ddl and cache.saved_fk_state:
                try:
                    cursor = connection.cursor()
                    sql = 'PRAGMA foreign_keys = true'
                    if core.debug: log_orm(sql)
                    cursor.execute(sql)
                except:
                    provider.pool.drop(connection)
                    raise
        DBAPIProvider.release(provider, connection, cache)

    def get_pool(provider, filename, create_db=False):
        if filename != ':memory:':
            # When relative filename is specified, it is considered
            # not relative to cwd, but to user module where
            # Database instance is created

            # the list of frames:
            # 6 - user code: db = Database(...)
            # 5 - cut_traceback decorator wrapper
            # 4 - cut_traceback decorator
            # 3 - pony.orm.Database.__init__() / .bind()
            # 2 - pony.orm.Database._bind()
            # 1 - pony.dbapiprovider.DBAPIProvider.__init__()
            # 0 - pony.dbproviders.sqlite.get_pool()
            filename = absolutize_path(filename, frame_depth=6)
        return SQLitePool(filename, create_db)

    def table_exists(provider, connection, table_name, case_sensitive=True):
        return provider._exists(connection, table_name, None, case_sensitive)

    def index_exists(provider, connection, table_name, index_name, case_sensitive=True):
        return provider._exists(connection, table_name, index_name, case_sensitive)

    def _exists(provider, connection, table_name, index_name=None, case_sensitive=True):
        db_name, table_name = provider.split_table_name(table_name)

        if db_name is None: catalog_name = 'sqlite_master'
        else: catalog_name = (db_name, 'sqlite_master')
        catalog_name = provider.quote_name(catalog_name)

        cursor = connection.cursor()
        if index_name is not None:
            sql = "SELECT name FROM %s WHERE type='index' AND name=?" % catalog_name
            if not case_sensitive: sql += ' COLLATE NOCASE'
            cursor.execute(sql, [ index_name ])
        else:
            sql = "SELECT name FROM %s WHERE type='table' AND name=?" % catalog_name
            if not case_sensitive: sql += ' COLLATE NOCASE'
            cursor.execute(sql, [ table_name ])
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def fk_exists(provider, connection, table_name, fk_name):
        assert False

provider_cls = SQLiteProvider

def _text_factory(s):
    return s.decode('utf8', 'replace')

class SQLitePool(Pool):
    def __init__(pool, filename, create_db): # called separately in each thread
        pool.filename = filename
        pool.create_db = create_db
        pool.con = None
    def connect(pool):
        con = pool.con
        if con is not None:
            if core.debug: core.log_orm('GET CONNECTION FROM THE LOCAL POOL')
            return con
        filename = pool.filename
        if filename != ':memory:' and not pool.create_db and not os.path.exists(filename):
            throw(IOError, "Database file is not found: %r" % filename)
        if core.debug: log_orm('GET NEW CONNECTION')
        pool.con = con = sqlite.connect(filename, isolation_level=None)
        con.text_factory = _text_factory
        con.create_function('power', 2, pow)
        con.create_function('rand', 0, random)
        if sqlite.sqlite_version_info >= (3, 6, 19):
            con.execute('PRAGMA foreign_keys = true')
        return con
    def disconnect(pool):
        if pool.filename != ':memory:':
            Pool.disconnect(pool)
    def drop(pool, con):
        if pool.filename != ':memory:':
            Pool.drop(pool, con)
        else:
            con.rollback()

########NEW FILE########
__FILENAME__ = dbschema
from pony.orm import core
from pony.orm.core import log_sql, DBSchemaError
from pony.utils import throw

class DBSchema(object):
    dialect = None
    inline_fk_syntax = True
    named_foreign_keys = True
    def __init__(schema, provider, uppercase=True):
        schema.provider = provider
        schema.tables = {}
        schema.constraints = {}
        schema.indent = '  '
        schema.command_separator = ';\n\n'
        schema.uppercase = uppercase
        schema.names = {}
    def column_list(schema, columns):
        quote_name = schema.provider.quote_name
        return '(%s)' % ', '.join(quote_name(column.name) for column in columns)
    def case(schema, s):
        if schema.uppercase: return s.upper().replace('%S', '%s') \
            .replace(')S', ')s').replace('%R', '%r').replace(')R', ')r')
        else: return s.lower()
    def add_table(schema, table_name):
        return schema.table_class(table_name, schema)
    def order_tables_to_create(schema):
        tables = []
        created_tables = set()
        tables_to_create = sorted(schema.tables.itervalues(), key=lambda table: table.name)
        while tables_to_create:
            for table in tables_to_create:
                if table.parent_tables.issubset(created_tables):
                    created_tables.add(table)
                    tables_to_create.remove(table)
                    break
            else: table = tables_to_create.pop()
            tables.append(table)
        return tables
    def generate_create_script(schema):
        created_tables = set()
        commands = []
        for table in schema.order_tables_to_create():
            for db_object in table.get_objects_to_create(created_tables):
                commands.append(db_object.get_create_command())
        return schema.command_separator.join(commands)
    def create_tables(schema, provider, connection):
        created_tables = set()
        for table in schema.order_tables_to_create():
            for db_object in table.get_objects_to_create(created_tables):
                name = db_object.exists(provider, connection, case_sensitive=False)
                if name is None: db_object.create(provider, connection)
                elif name != db_object.name:
                    quote_name = schema.provider.quote_name
                    n1, n2 = quote_name(db_object.name), quote_name(name)
                    tn1, tn2 = db_object.typename, db_object.typename.lower()
                    throw(DBSchemaError, '%s %s cannot be created, because %s %s ' \
                                         '(with a different letter case) already exists in the database. ' \
                                         'Try to delete %s %s first.' % (tn1, n1, tn2, n2, n2, tn2))
    def check_tables(schema, provider, connection):
        cursor = connection.cursor()
        for table in sorted(schema.tables.itervalues(), key=lambda table: table.name):
            if isinstance(table.name, tuple): alias = table.name[-1]
            elif isinstance(table.name, basestring): alias = table.name
            else: assert False
            sql_ast = [ 'SELECT',
                        [ 'ALL', ] + [ [ 'COLUMN', alias, column.name ] for column in table.column_list ],
                        [ 'FROM', [ alias, 'TABLE', table.name ] ],
                        [ 'WHERE', [ 'EQ', [ 'VALUE', 0 ], [ 'VALUE', 1 ] ] ]
                      ]
            sql, adapter = provider.ast2sql(sql_ast)
            if core.debug: log_sql(sql)
            provider.execute(cursor, sql)

class DBObject(object):
    def create(table, provider, connection):
        sql = table.get_create_command()
        if core.debug: log_sql(sql)
        cursor = connection.cursor()
        provider.execute(cursor, sql)

class Table(DBObject):
    typename = 'Table'
    def __init__(table, name, schema):
        if name in schema.tables:
            throw(DBSchemaError, "Table %r already exists in database schema" % name)
        if name in schema.names:
            throw(DBSchemaError, "Table %r cannot be created, name is already in use" % name)
        schema.tables[name] = table
        schema.names[name] = table
        table.schema = schema
        table.name = name
        table.column_list = []
        table.column_dict = {}
        table.indexes = {}
        table.pk_index = None
        table.foreign_keys = {}
        table.parent_tables = set()
        table.child_tables = set()
        table.entities = set()
        table.m2m = set()
    def __repr__(table):
        table_name = table.name
        if isinstance(table_name, tuple):
            table_name = '.'.join(table_name)
        return '<Table(%s)>' % table_name
    def exists(table, provider, connection, case_sensitive=True):
        return provider.table_exists(connection, table.name, case_sensitive)
    def get_create_command(table):
        schema = table.schema
        case = schema.case
        provider = schema.provider
        quote_name = provider.quote_name
        if_not_exists = False # provider.table_if_not_exists_syntax and provider.index_if_not_exists_syntax
        cmd = []
        if not if_not_exists: cmd.append(case('CREATE TABLE %s (') % quote_name(table.name))
        else: cmd.append(case('CREATE TABLE IF NOT EXISTS %s (') % quote_name(table.name))
        for column in table.column_list:
            cmd.append(schema.indent + column.get_sql() + ',')
        if len(table.pk_index.columns) > 1:
            cmd.append(schema.indent + table.pk_index.get_sql() + ',')
        for index in sorted(table.indexes.itervalues(), key=lambda index: index.name):
            if index.is_pk: continue
            if not index.is_unique: continue
            if len(index.columns) == 1: continue
            cmd.append(schema.indent+index.get_sql() + ',')
        if not schema.named_foreign_keys:
            for foreign_key in sorted(table.foreign_keys.itervalues(), key=lambda fk: fk.name):
                if schema.inline_fk_syntax and len(foreign_key.child_columns) == 1: continue
                cmd.append(schema.indent+foreign_key.get_sql() + ',')
        cmd[-1] = cmd[-1][:-1]
        cmd.append(')')
        return '\n'.join(cmd)
    def get_objects_to_create(table, created_tables=None):
        if created_tables is None: created_tables = set()
        result = [ table ]
        for index in sorted(table.indexes.itervalues(), key=lambda index: index.name):
            if index.is_pk or index.is_unique: continue
            assert index.name is not None
            result.append(index)
        schema = table.schema
        if schema.named_foreign_keys:
            for foreign_key in sorted(table.foreign_keys.itervalues(), key=lambda fk: fk.name):
                if foreign_key.parent_table not in created_tables: continue
                result.append(foreign_key)
            for child_table in table.child_tables:
                if child_table not in created_tables: continue
                for foreign_key in sorted(child_table.foreign_keys.itervalues(), key=lambda fk: fk.name):
                    if foreign_key.parent_table is not table: continue
                    result.append(foreign_key)
        created_tables.add(table)
        return result
    def add_column(table, column_name, sql_type, converter, is_not_null=None, sql_default=None):
        return table.schema.column_class(column_name, table, sql_type, converter, is_not_null, sql_default)
    def add_index(table, index_name, columns, is_pk=False, is_unique=None, m2m=False):
        assert index_name is not False
        if index_name is True: index_name = None
        if index_name is None and not is_pk:
            provider = table.schema.provider
            index_name = provider.get_default_index_name(table.name, (column.name for column in columns),
                                                         is_pk=is_pk, is_unique=is_unique, m2m=m2m)
        index = table.indexes.get(columns)
        if index and index.name == index_name and index.is_pk == is_pk and index.is_unique == is_unique:
            return index
        return table.schema.index_class(index_name, table, columns, is_pk, is_unique)
    def add_foreign_key(table, fk_name, child_columns, parent_table, parent_columns, index_name=None):
        if fk_name is None:
            provider = table.schema.provider
            child_column_names = tuple(column.name for column in child_columns)
            fk_name = provider.get_default_fk_name(table.name, parent_table.name, child_column_names)
        return table.schema.fk_class(fk_name, table, child_columns, parent_table, parent_columns, index_name)

class Column(object):
    auto_template = '%(type)s PRIMARY KEY AUTOINCREMENT'
    def __init__(column, name, table, sql_type, converter, is_not_null=None, sql_default=None):
        if name in table.column_dict:
            throw(DBSchemaError, "Column %r already exists in table %r" % (name, table.name))
        table.column_dict[name] = column
        table.column_list.append(column)
        column.table = table
        column.name = name
        column.sql_type = sql_type
        column.converter = converter
        column.is_not_null = is_not_null
        column.sql_default = sql_default
        column.is_pk = False
        column.is_pk_part = False
        column.is_unique = False
    def __repr__(column):
        return '<Column(%s.%s)>' % (column.table.name, column.name)
    def get_sql(column):
        table = column.table
        schema = table.schema
        quote_name = schema.provider.quote_name
        case = schema.case
        result = []
        append = result.append
        append(quote_name(column.name))
        if column.is_pk == 'auto' and column.auto_template:
            append(case(column.auto_template % dict(type=column.sql_type)))
        else:
            append(case(column.sql_type))
            if column.is_pk:
                if schema.dialect == 'SQLite': append(case('NOT NULL'))
                append(case('PRIMARY KEY'))
            else:
                if column.is_unique: append(case('UNIQUE'))
                if column.is_not_null: append(case('NOT NULL'))
        if column.sql_default not in (None, True, False):
            append(case('DEFAULT'))
            append(column.sql_default)
        if schema.inline_fk_syntax and not schema.named_foreign_keys:
            foreign_key = table.foreign_keys.get((column,))
            if foreign_key is not None:
                parent_table = foreign_key.parent_table
                append(case('REFERENCES'))
                append(quote_name(parent_table.name))
                append(schema.column_list(foreign_key.parent_columns))
        return ' '.join(result)

class Constraint(DBObject):
    def __init__(constraint, name, schema):
        if name is not None:
            assert name not in schema.names
            if name in schema.constraints: throw(DBSchemaError,
                "Constraint with name %r already exists" % name)
            schema.names[name] = constraint
            schema.constraints[name] = constraint
        constraint.schema = schema
        constraint.name = name

class Index(Constraint):
    typename = 'Index'
    def __init__(index, name, table, columns, is_pk=False, is_unique=None):
        assert len(columns) > 0
        for column in columns:
            if column.table is not table: throw(DBSchemaError,
                "Column %r does not belong to table %r and cannot be part of its index"
                % (column.name, table.name))
        if columns in table.indexes:
            if len(columns) == 1: throw(DBSchemaError, "Index for column %r already exists" % columns[0].name)
            else: throw(DBSchemaError, "Index for columns (%s) already exists" % ', '.join(repr(column.name) for column in columns))
        if is_pk:
            if table.pk_index is not None: throw(DBSchemaError,
                'Primary key for table %r is already defined' % table.name)
            table.pk_index = index
            if is_unique is None: is_unique = True
            elif not is_unique: throw(DBSchemaError,
                "Incompatible combination of is_unique=False and is_pk=True")
        elif is_unique is None: is_unique = False
        schema = table.schema
        if name is not None and name in schema.names:
            throw(DBSchemaError, 'Index %s cannot be created, name is already in use')
        Constraint.__init__(index, name, schema)
        for column in columns:
            column.is_pk = len(columns) == 1 and is_pk
            column.is_pk_part = bool(is_pk)
            column.is_unique = is_unique and len(columns) == 1
        table.indexes[columns] = index
        index.table = table
        index.columns = columns
        index.is_pk = is_pk
        index.is_unique = is_unique
    def exists(index, provider, connection, case_sensitive=True):
        return provider.index_exists(connection, index.table.name, index.name, case_sensitive)
    def get_sql(index):
        return index._get_create_sql(inside_table=True)
    def get_create_command(index):
        return index._get_create_sql(inside_table=False)
    def _get_create_sql(index, inside_table):
        schema = index.schema
        case = schema.case
        quote_name = schema.provider.quote_name
        cmd = []
        append = cmd.append
        if not inside_table:
            if index.is_pk: throw(DBSchemaError,
                'Primary key index cannot be defined outside of table definition')
            append(case('CREATE'))
            if index.is_unique: append(case('UNIQUE'))
            append(case('INDEX'))
            # if schema.provider.index_if_not_exists_syntax:
            #     append(case('IF NOT EXISTS'))
            append(quote_name(index.name))
            append(case('ON'))
            append(quote_name(index.table.name))
        else:
            if index.name:
                append(case('CONSTRAINT'))
                append(quote_name(index.name))
            if index.is_pk: append(case('PRIMARY KEY'))
            elif index.is_unique: append(case('UNIQUE'))
            else: append(case('INDEX'))
        append(schema.column_list(index.columns))
        return ' '.join(cmd)

class ForeignKey(Constraint):
    typename = 'Foreign key'
    def __init__(foreign_key, name, child_table, child_columns, parent_table, parent_columns, index_name):
        schema = parent_table.schema
        if schema is not child_table.schema: throw(DBSchemaError,
            'Parent and child tables of foreign_key cannot belong to different schemata')
        for column in parent_columns:
            if column.table is not parent_table: throw(DBSchemaError,
                'Column %r does not belong to table %r' % (column.name, parent_table.name))
        for column in child_columns:
            if column.table is not child_table: throw(DBSchemaError,
                'Column %r does not belong to table %r' % (column.name, child_table.name))
        if len(parent_columns) != len(child_columns): throw(DBSchemaError,
            'Foreign key columns count do not match')
        if child_columns in child_table.foreign_keys:
            if len(child_columns) == 1: throw(DBSchemaError, 'Foreign key for column %r already defined' % child_columns[0].name)
            else: throw(DBSchemaError, 'Foreign key for columns (%s) already defined' % ', '.join(repr(column.name) for column in child_columns))
        if name is not None and name in schema.names:
            throw(DBSchemaError, 'Foreign key %s cannot be created, name is already in use' % name)
        Constraint.__init__(foreign_key, name, schema)
        child_table.foreign_keys[child_columns] = foreign_key
        if child_table is not parent_table:
            child_table.parent_tables.add(parent_table)
            parent_table.child_tables.add(child_table)
        foreign_key.parent_table = parent_table
        foreign_key.parent_columns = parent_columns
        foreign_key.child_table = child_table
        foreign_key.child_columns = child_columns

        if index_name is not False:
            child_columns_len = len(child_columns)
            for columns in child_table.indexes:
                if columns[:child_columns_len] == child_columns: break
            else: child_table.add_index(index_name, child_columns, is_pk=False,
                                        is_unique=False, m2m=bool(child_table.m2m))
    def exists(foreign_key, provider, connection, case_sensitive=True):
        return provider.fk_exists(connection, foreign_key.child_table.name, foreign_key.name, case_sensitive)
    def get_sql(foreign_key):
        return foreign_key._get_create_sql(inside_table=True)
    def get_create_command(foreign_key):
        return foreign_key._get_create_sql(inside_table=False)
    def _get_create_sql(foreign_key, inside_table):
        schema = foreign_key.schema
        case = schema.case
        quote_name = schema.provider.quote_name
        cmd = []
        append = cmd.append
        if not inside_table:
            append(case('ALTER TABLE'))
            append(quote_name(foreign_key.child_table.name))
            append(case('ADD'))
        if schema.named_foreign_keys and foreign_key.name:
            append(case('CONSTRAINT'))
            append(quote_name(foreign_key.name))
        append(case('FOREIGN KEY'))
        append(schema.column_list(foreign_key.child_columns))
        append(case('REFERENCES'))
        append(quote_name(foreign_key.parent_table.name))
        append(schema.column_list(foreign_key.parent_columns))
        return ' '.join(cmd)

DBSchema.table_class = Table
DBSchema.column_class = Column
DBSchema.index_class = Index
DBSchema.fk_class = ForeignKey

########NEW FILE########
__FILENAME__ = decompiling
import types
from compiler import ast
from opcode import opname as opnames, HAVE_ARGUMENT, EXTENDED_ARG, cmp_op
from opcode import hasconst, hasname, hasjrel, haslocal, hascompare, hasfree

from pony.utils import throw

##ast.And.__repr__ = lambda self: "And(%s: %s)" % (getattr(self, 'endpos', '?'), repr(self.nodes),)
##ast.Or.__repr__ = lambda self: "Or(%s: %s)" % (getattr(self, 'endpos', '?'), repr(self.nodes),)

ast_cache = {}

codeobjects = {}

def decompile(x):
    t = type(x)
    if t is types.CodeType: codeobject = x
    elif t is types.GeneratorType: codeobject = x.gi_frame.f_code
    elif t is types.FunctionType: codeobject = x.func_code
    else: throw(TypeError)
    key = id(codeobject)
    result = ast_cache.get(key)
    if result is None:
        codeobjects[key] = codeobject
        decompiler = Decompiler(codeobject)
        result = decompiler.ast, decompiler.external_names
        ast_cache[key] = result
    return result

def simplify(clause):
    if isinstance(clause, ast.And):
        if len(clause.nodes) == 1: result = clause.nodes[0]
        else: return clause
    elif isinstance(clause, ast.Or):
        if len(clause.nodes) == 1: result = ast.Not(clause.nodes[0])
        else: return clause
    else: return clause
    if getattr(result, 'endpos', 0) < clause.endpos: result.endpos = clause.endpos
    return result

class InvalidQuery(Exception): pass

class AstGenerated(Exception): pass

def binop(node_type, args_holder=tuple):
    def method(decompiler):
        oper2 = decompiler.stack.pop()
        oper1 = decompiler.stack.pop()
        return node_type(args_holder((oper1, oper2)))
    return method

class Decompiler(object):
    def __init__(decompiler, code, start=0, end=None):
        decompiler.code = code
        decompiler.start = decompiler.pos = start
        if end is None: end = len(code.co_code)
        decompiler.end = end
        decompiler.stack = []
        decompiler.targets = {}
        decompiler.ast = None
        decompiler.names = set()
        decompiler.assnames = set()
        decompiler.decompile()
        decompiler.ast = decompiler.stack.pop()
        decompiler.external_names = set(decompiler.names - decompiler.assnames)
        assert not decompiler.stack, decompiler.stack
    def decompile(decompiler):
        code = decompiler.code
        co_code = code.co_code
        free = code.co_cellvars + code.co_freevars
        try:
            while decompiler.pos < decompiler.end:
                i = decompiler.pos
                if i in decompiler.targets: decompiler.process_target(i)
                op = ord(code.co_code[i])
                i += 1
                if op >= HAVE_ARGUMENT:
                    oparg = ord(co_code[i]) + ord(co_code[i+1])*256
                    i += 2
                    if op == EXTENDED_ARG:
                        op = ord(code.co_code[i])
                        i += 1
                        oparg = ord(co_code[i]) + ord(co_code[i+1])*256 + oparg*65536
                        i += 2
                    if op in hasconst: arg = [code.co_consts[oparg]]
                    elif op in hasname: arg = [code.co_names[oparg]]
                    elif op in hasjrel: arg = [i + oparg]
                    elif op in haslocal: arg = [code.co_varnames[oparg]]
                    elif op in hascompare: arg = [cmp_op[oparg]]
                    elif op in hasfree: arg = [free[oparg]]
                    else: arg = [oparg]
                else: arg = []
                opname = opnames[op].replace('+', '_')
                # print opname, arg, decompiler.stack
                method = getattr(decompiler, opname, None)
                if method is None: throw(NotImplementedError('Unsupported operation: %s' % opname))
                decompiler.pos = i
                x = method(*arg)
                if x is not None: decompiler.stack.append(x)
        except AstGenerated: pass
    def pop_items(decompiler, size):
        if not size: return ()
        result = decompiler.stack[-size:]
        decompiler.stack[-size:] = []
        return result
    def store(decompiler, node):
        stack = decompiler.stack
        if not stack: stack.append(node); return
        top = stack[-1]
        if isinstance(top, (ast.AssTuple, ast.AssList)) and len(top.nodes) < top.count:
            top.nodes.append(node)
            if len(top.nodes) == top.count: decompiler.store(stack.pop())
        elif isinstance(top, ast.GenExprFor):
            assert top.assign is None
            top.assign = node
        else: stack.append(node)

    BINARY_POWER        = binop(ast.Power)
    BINARY_MULTIPLY     = binop(ast.Mul)
    BINARY_DIVIDE       = binop(ast.Div)
    BINARY_FLOOR_DIVIDE = binop(ast.FloorDiv)
    BINARY_ADD          = binop(ast.Add)
    BINARY_SUBTRACT     = binop(ast.Sub)
    BINARY_LSHIFT       = binop(ast.LeftShift)
    BINARY_RSHIFT       = binop(ast.RightShift)
    BINARY_AND          = binop(ast.Bitand, list)
    BINARY_XOR          = binop(ast.Bitxor, list)
    BINARY_OR           = binop(ast.Bitor, list)
    BINARY_TRUE_DIVIDE  = BINARY_DIVIDE
    BINARY_MODULO       = binop(ast.Mod)

    def BINARY_SUBSCR(decompiler):
        oper2 = decompiler.stack.pop()
        oper1 = decompiler.stack.pop()
        if isinstance(oper2, ast.Tuple): return ast.Subscript(oper1, 'OP_APPLY', list(oper2.nodes))
        else: return ast.Subscript(oper1, 'OP_APPLY', [ oper2 ])

    def BUILD_LIST(decompiler, size):
        return ast.List(decompiler.pop_items(size))

    def BUILD_MAP(decompiler, not_used):
        # Pushes a new empty dictionary object onto the stack. The argument is ignored and set to zero by the compiler
        return ast.Dict(())

    def BUILD_SET(decompiler, size):
        return ast.Set(decompiler.pop_items(size))

    def BUILD_SLICE(decompiler, size):
        return ast.Sliceobj(decompiler.pop_items(size))

    def BUILD_TUPLE(decompiler, size):
        return ast.Tuple(decompiler.pop_items(size))

    def CALL_FUNCTION(decompiler, argc, star=None, star2=None):
        pop = decompiler.stack.pop
        kwarg, posarg = divmod(argc, 256)
        args = []
        for i in range(kwarg):
            arg = pop()
            key = pop().value
            args.append(ast.Keyword(key, arg))
        for i in range(posarg): args.append(pop())
        args.reverse()
        tos = pop()
        if isinstance(tos, ast.GenExpr):
            assert len(args) == 1 and star is None and star2 is None
            genexpr = tos
            qual = genexpr.code.quals[0]
            assert isinstance(qual.iter, ast.Name)
            assert qual.iter.name in ('.0', '[outmost-iterable]')
            qual.iter = args[0]
            return genexpr
        else: return ast.CallFunc(tos, args, star, star2)

    def CALL_FUNCTION_VAR(decompiler, argc):
        return decompiler.CALL_FUNCTION(argc, decompiler.stack.pop())

    def CALL_FUNCTION_KW(decompiler, argc):
        return decompiler.CALL_FUNCTION(argc, None, decompiler.stack.pop())

    def CALL_FUNCTION_VAR_KW(decompiler, argc):
        star2 = decompiler.stack.pop()
        star = decompiler.stack.pop()
        return decompiler.CALL_FUNCTION(argc, star, star2)

    def COMPARE_OP(decompiler, op):
        oper2 = decompiler.stack.pop()
        oper1 = decompiler.stack.pop()
        return ast.Compare(oper1, [(op, oper2)])

    def DUP_TOP(decompiler):
        return decompiler.stack[-1]

    def FOR_ITER(decompiler, endpos):
        assign = None
        iter = decompiler.stack.pop()
        ifs = []
        return ast.GenExprFor(assign, iter, ifs)

    def GET_ITER(decompiler):
        pass

    def JUMP_IF_FALSE(decompiler, endpos):
        return decompiler.conditional_jump(endpos, ast.And)

    JUMP_IF_FALSE_OR_POP = JUMP_IF_FALSE

    def JUMP_IF_TRUE(decompiler, endpos):
        return decompiler.conditional_jump(endpos, ast.Or)

    JUMP_IF_TRUE_OR_POP = JUMP_IF_TRUE

    def conditional_jump(decompiler, endpos, clausetype):
        i = decompiler.pos  # next instruction
        if i in decompiler.targets: decompiler.process_target(i)
        expr = decompiler.stack.pop()
        clause = clausetype([ expr ])
        clause.endpos = endpos
        decompiler.targets.setdefault(endpos, clause)
        return clause

    def process_target(decompiler, pos, partial=False):
        if pos is None: limit = None
        elif partial: limit = decompiler.targets.get(pos, None)
        else: limit = decompiler.targets.pop(pos, None)
        top = decompiler.stack.pop()
        while True:
            top = simplify(top)
            if top is limit: break
            if isinstance(top, ast.GenExprFor): break

            top2 = decompiler.stack[-1]
            if isinstance(top2, ast.GenExprFor): break
            if partial and hasattr(top2, 'endpos') and top2.endpos == pos: break

            if isinstance(top2, (ast.And, ast.Or)):
                if top2.__class__ == top.__class__: top2.nodes.extend(top.nodes)
                else: top2.nodes.append(top)
            elif isinstance(top2, ast.IfExp):  # Python 2.5
                top2.else_ = top
                if hasattr(top, 'endpos'):
                    top2.endpos = top.endpos
                    if decompiler.targets.get(top.endpos) is top: decompiler.targets[top.endpos] = top2
            else: throw(NotImplementedError('Expression is too complex to decompile, try to pass query as string, e.g. select("x for x in Something")'))
            top2.endpos = max(top2.endpos, getattr(top, 'endpos', 0))
            top = decompiler.stack.pop()
        decompiler.stack.append(top)

    def JUMP_FORWARD(decompiler, endpos):
        i = decompiler.pos  # next instruction
        decompiler.process_target(i, True)
        then = decompiler.stack.pop()
        decompiler.process_target(i, False)
        test = decompiler.stack.pop()
        if_exp = ast.IfExp(simplify(test), simplify(then), None)
        if_exp.endpos = endpos
        decompiler.targets.setdefault(endpos, if_exp)
        if decompiler.targets.get(endpos) is then: decompiler.targets[endpos] = if_exp
        return if_exp

    def LIST_APPEND(decompiler):
        throw(NotImplementedError)

    def LOAD_ATTR(decompiler, attr_name):
        return ast.Getattr(decompiler.stack.pop(), attr_name)

    def LOAD_CLOSURE(decompiler, freevar):
        decompiler.names.add(freevar)
        return ast.Name(freevar)

    def LOAD_CONST(decompiler, const_value):
        return ast.Const(const_value)

    def LOAD_DEREF(decompiler, freevar):
        decompiler.names.add(freevar)
        return ast.Name(freevar)

    def LOAD_FAST(decompiler, varname):
        decompiler.names.add(varname)
        return ast.Name(varname)

    def LOAD_GLOBAL(decompiler, varname):
        decompiler.names.add(varname)
        return ast.Name(varname)

    def LOAD_NAME(decompiler, varname):
        decompiler.names.add(varname)
        return ast.Name(varname)

    def MAKE_CLOSURE(decompiler, argc):
        decompiler.stack[-2:-1] = [] # ignore freevars
        return decompiler.MAKE_FUNCTION(argc)

    def MAKE_FUNCTION(decompiler, argc):
        if argc: throw(NotImplementedError)
        tos = decompiler.stack.pop()
        codeobject = tos.value
        func_decompiler = Decompiler(codeobject)
        # decompiler.names.update(decompiler.names)  ???
        if codeobject.co_varnames[:1] == ('.0',):
            return func_decompiler.ast  # generator
        argnames = codeobject.co_varnames[:codeobject.co_argcount]
        defaults = []  # todo
        flags = 0  # todo
        return ast.Lambda(argnames, defaults, flags, func_decompiler.ast)

    POP_JUMP_IF_FALSE = JUMP_IF_FALSE
    POP_JUMP_IF_TRUE = JUMP_IF_TRUE

    def POP_TOP(decompiler):
        pass

    def RETURN_VALUE(decompiler):
        if decompiler.pos != decompiler.end: throw(NotImplementedError)
        expr = decompiler.stack.pop()
        decompiler.stack.append(simplify(expr))
        raise AstGenerated

    def ROT_TWO(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        decompiler.stack.append(tos)
        decompiler.stack.append(tos1)

    def ROT_THREE(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        tos2 = decompiler.stack.pop()
        decompiler.stack.append(tos)
        decompiler.stack.append(tos2)
        decompiler.stack.append(tos1)

    def SETUP_LOOP(decompiler, endpos):
        pass

    def SLICE_0(decompiler):
        return ast.Slice(decompiler.stack.pop(), 'OP_APPLY', None, None)

    def SLICE_1(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        return ast.Slice(tos1, 'OP_APPLY', tos, None)

    def SLICE_2(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        return ast.Slice(tos1, 'OP_APPLY', None, tos)

    def SLICE_3(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        tos2 = decompiler.stack.pop()
        return ast.Slice(tos2, 'OP_APPLY', tos1, tos)

    def STORE_ATTR(decompiler, attrname):
        decompiler.store(ast.AssAttr(decompiler.stack.pop(), attrname, 'OP_ASSIGN'))

    def STORE_DEREF(decompiler, freevar):
        decompiler.assnames.add(freevar)
        decompiler.store(ast.AssName(freevar, 'OP_ASSIGN'))

    def STORE_FAST(decompiler, varname):
        if varname.startswith('_['):
            throw(InvalidQuery('Use generator expression (... for ... in ...) instead of list comprehension [... for ... in ...] inside query'))
        decompiler.assnames.add(varname)
        decompiler.store(ast.AssName(varname, 'OP_ASSIGN'))

    def STORE_MAP(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        tos2 = decompiler.stack[-1]
        if not isinstance(tos2, ast.Dict): assert False
        if tos2.items == (): tos2.items = []
        tos2.items.append((tos, tos1))

    def STORE_SUBSCR(decompiler):
        tos = decompiler.stack.pop()
        tos1 = decompiler.stack.pop()
        tos2 = decompiler.stack.pop()
        if not isinstance(tos1, ast.Dict): assert False
        if tos1.items == (): tos1.items = []
        tos1.items.append((tos, tos2))

    def UNARY_POSITIVE(decompiler):
        return ast.UnaryAdd(decompiler.stack.pop())

    def UNARY_NEGATIVE(decompiler):
        return ast.UnarySub(decompiler.stack.pop())

    def UNARY_NOT(decompiler):
        return ast.Not(decompiler.stack.pop())

    def UNARY_CONVERT(decompiler):
        return ast.Backquote(decompiler.stack.pop())

    def UNARY_INVERT(decompiler):
        return ast.Invert(decompiler.stack.pop())

    def UNPACK_SEQUENCE(decompiler, count):
        ass_tuple = ast.AssTuple([])
        ass_tuple.count = count
        return ass_tuple

    def YIELD_VALUE(decompiler):
        expr = decompiler.stack.pop()
        fors = []
        while decompiler.stack:
            decompiler.process_target(None)
            top = decompiler.stack.pop()
            if not isinstance(top, (ast.GenExprFor)):
                cond = ast.GenExprIf(top)
                top = decompiler.stack.pop()
                assert isinstance(top, ast.GenExprFor)
                top.ifs.append(cond)
                fors.append(top)
            else: fors.append(top)
        fors.reverse()
        decompiler.stack.append(ast.GenExpr(ast.GenExprInner(simplify(expr), fors)))
        raise AstGenerated

test_lines = """
    (a and b if c and d else e and f for i in T if (A and B if C and D else E and F))

    (a for b in T)
    (a for b, c in T)
    (a for b in T1 for c in T2)
    (a for b in T1 for c in T2 for d in T3)
    (a for b in T if f)
    (a for b in T if f and h)
    (a for b in T if f and h or t)
    (a for b in T if f == 5 and r or t)
    (a for b in T if f and r and t)

    (a for b in T if f == 5 and +r or not t)
    (a for b in T if -t and ~r or `f`)

    (a**2 for b in T if t * r > y / 3)
    (a + 2 for b in T if t + r > y // 3)
    (a[2,v] for b in T if t - r > y[3])
    ((a + 2) * 3 for b in T if t[r, e] > y[3, r * 4, t])
    (a<<2 for b in T if t>>e > r & (y & u))
    (a|b for c in T1 if t^e > r | (y & (u & (w % z))))

    ([a, b, c] for d in T)
    ([a, b, 4] for d in T if a[4, b] > b[1,v,3])
    ((a, b, c) for d in T)
    ({} for d in T)
    ({'a' : x, 'b' : y} for a, b in T)
    (({'a' : x, 'b' : y}, {'c' : x1, 'd' : 1}) for a, b, c, d in T)
    ([{'a' : x, 'b' : y}, {'c' : x1, 'd' : 1}] for a, b, c, d in T)

    (a[1:2] for b in T)
    (a[:2] for b in T)
    (a[2:] for b in T)
    (a[:] for b in T)
    (a[1:2:3] for b in T)
    (a[1:2, 3:4] for b in T)
    (a[2:4:6,6:8] for a, y in T)

    (a.b.c for d.e.f.g in T)
    # (a.b.c for d[g] in T)

    ((s,d,w) for t in T if (4 != x.a or a*3 > 20) and a * 2 < 5)
    ([s,d,w] for t in T if (4 != x.amount or amount * 3 > 20 or amount * 2 < 5) and amount*8 == 20)
    ([s,d,w] for t in T if (4 != x.a or a*3 > 20 or a*2 < 5 or 4 == 5) and a * 8 == 20)
    (s for s in T if s.a > 20 and (s.x.y == 123 or 'ABC' in s.p.q.r))
    (a for b in T1 if c > d for e in T2 if f < g)

    (func1(a, a.attr, keyarg=123) for s in T)
    (func1(a, a.attr, keyarg=123, *e) for s in T)
    (func1(a, b, a.attr1, a.b.c, keyarg1=123, keyarg2='mx', *e, **f) for s in T)
    (func(a, a.attr, keyarg=123) for a in T if a.method(x, *y, **z) == 4)

    ((x or y) and (p or q) for a in T if (a or b) and (c or d))
    (x.y for x in T if (a and (b or (c and d))) or X)

    (a for a in T1 if a in (b for b in T2))
    (a for a in T1 if a in (b for b in T2 if b == a))

    (a for a in T1 if a in (b for b in T2))
    (a for a in T1 if a in select(b for b in T2))
    (a for a in T1 if a in (b for b in T2 if b in (c for c in T3 if c == a)))
    (a for a in T1 if a > x and a in (b for b in T1 if b < y) and a < z)
"""
##   should throw InvalidQuery due to using [] inside of a query
##   (a for a in T1 if a in [b for b in T2 if b in [(c, d) for c in T3]])

##    examples of conditional expressions
##    (a if b else c for x in T)
##    (x for x in T if (d if e else f))
##    (a if b else c for x in T if (d if e else f))
##    (a and b or c and d if x and y or p and q else r and n or m and k for i in T)
##    (i for i in T if (a and b or c and d if x and y or p and q else r and n or m and k))
##    (a and b or c and d if x and y or p and q else r and n or m and k for i in T if (A and B or C and D if X and Y or P and Q else R and N or M and K))

def test():
    import sys
    if sys.version[:3] > '2.4': outmost_iterable_name = '.0'
    else: outmost_iterable_name = '[outmost-iterable]'
    import dis, compiler
    for line in test_lines.split('\n'):
        if not line or line.isspace(): continue
        line = line.strip()
        if line.startswith('#'): continue
        code = compile(line, '<?>', 'eval').co_consts[0]
        ast1 = compiler.parse(line).node.nodes[0].expr
        ast1.code.quals[0].iter.name = outmost_iterable_name
        try: ast2 = Decompiler(code).ast
        except Exception, e:
            print
            print line
            print
            print ast1
            print
            dis.dis(code)
            raise
        if str(ast1) != str(ast2):
            print
            print line
            print
            print ast1
            print
            print ast2
            print
            dis.dis(code)
            break
        else: print 'OK: %s' % line
    else: print 'Done!'

if __name__ == '__main__': test()

########NEW FILE########
__FILENAME__ = bottle_example
from bottle import default_app, install, route, request, redirect, run, template

# Import eStore model http://editor.ponyorm.com/user/pony/eStore
from pony.orm.examples.estore import *
from pony.orm.integration.bottle_plugin import PonyPlugin

# After the plugin is installed each request will be processed
# in a separate database session. Once the HTTP request processing
# is finished the plugin does the following:
#  * commit the changes to the database (or rollback if an exception happened)
#  * clear the transaction cache
#  * return the database connection to the connection pool
install(PonyPlugin())

@route('/')
@route('/products/')
def all_products():
    # Get the list of all products from the database
    products = select(p for p in Product)
    return template('''
    <h1>List of products</h1>
    <ul>
    %for p in products:
        <li><a href="/products/{{ p.id }}/">{{ p.name }}</a>
    %end
    </ul>
    ''', products=products)

@route('/products/:id/')
def show_product(id):
    # Get the instance of the Product entity by the primary key
    p = Product[id]
    # You can traverse entity relationship attributes inside the template
    # In this examples it is many-to-many relationship p.categories
    # Since the data were not loaded into the cache yet,
    # it will result in a separate SQL query.
    return template('''
    <h1>{{ p.name }}</h1>
    <p>Price: {{ p.price }}</p>
    <p>Product categories:</p>
    <ul>
    %for c in p.categories:
        <li>{{ c.name }}
    %end
    </ul>
    <a href="/products/{{ p.id }}/edit/">Edit product info</a>
    <a href="/products/">Return to all products</a>
    ''', p=p)

@route('/products/:id/edit/')
def edit_product(id):
    # Get the instance of the Product entity and display its attributes
    p = Product[id]
    return template('''
    <form action='/products/{{ p.id }}/edit/' method='post'>
      <table>
        <tr>
          <td>Product name:</td>
          <td><input type="text" name="name" value="{{ p.name }}">
        </tr>
        <tr>
          <td>Product price:</td>
          <td><input type="text" name="price" value="{{ p.price }}">
        </tr>
      </table>
      <input type="submit" value="Save!">
    </form>
    <p><a href="/products/{{ p.id }}/">Discard changes</a>
    <p><a href="/products/">Return to all products</a>
    ''', p=p)

@route('/products/:id/edit/', method='POST')
def save_product(id):
    # Get the instance of the Product entity
    p = Product[id]
    # Update the attributes with the new values
    p.name = request.forms.get('name')
    p.price = request.forms.get('price')
    # We might put the commit() command here, but it is not necessary
    # because PonyPlugin will take care of this.
    redirect("/products/%d/" % p.id)
    # The Bottle's redirect function raises the HTTPResponse exception.
    # Normally PonyPlugin closes the session with rollback
    # if a callback function raises an exception. But in this case
    # PonyPlugin understands that this exception is not the error
    # and closes the session with commit.


run(debug=True, host='localhost', port=8080, reloader=True)

########NEW FILE########
__FILENAME__ = compositekeys
from datetime import date
from pony.orm.core import *

db = Database('sqlite', 'complex.sqlite', create_db=True)

class Group(db.Entity):
    dept = Required('Department')
    year = Required(int)
    spec = Required(int)
    students = Set('Student')
    courses = Set('Course')
    lessons = Set('Lesson', columns=['building', 'number', 'dt'])
    PrimaryKey(dept, year, spec)

class Department(db.Entity):
    number = PrimaryKey(int)
    faculty = Required('Faculty')
    name = Required(unicode)
    groups = Set(Group)
    teachers = Set('Teacher')

class Faculty(db.Entity):
    number = PrimaryKey(int)
    name = Required(unicode)
    depts = Set(Department)

class Student(db.Entity):
    name = Required(unicode)
    group = Required(Group)
    dob = Optional(date)
    grades = Set('Grade')
    PrimaryKey(name, group)

class Grade(db.Entity):
    student = Required(Student, columns=['student_name', 'dept', 'year', 'spec'])
    task = Required('Task')
    date = Required(date)
    value = Required(int)
    PrimaryKey(student, task)

class Task(db.Entity):
    course = Required('Course')
    type = Required(unicode)
    number = Required(int)
    descr = Optional(unicode)
    grades = Set(Grade)
    PrimaryKey(course, type, number)

class Course(db.Entity):
    subject = Required('Subject')
    semester = Required(int)
    groups = Set(Group)
    tasks = Set(Task)
    lessons = Set('Lesson')
    teachers = Set('Teacher')
    PrimaryKey(subject, semester)

class Subject(db.Entity):
    name = PrimaryKey(unicode)
    descr = Optional(unicode)
    courses = Set(Course)

class Room(db.Entity):
    building = Required(unicode)
    number = Required(unicode)
    floor = Optional(int)
    schedules = Set('Lesson')
    PrimaryKey(building, number)

class Teacher(db.Entity):
    dept = Required(Department)
    name = Required(unicode)
    courses = Set(Course)
    lessons = Set('Lesson')

class Lesson(db.Entity):
    _table_ = 'Schedule'
    groups = Set(Group)
    course = Required(Course)
    room = Required(Room)
    teacher = Required(Teacher)
    date = Required(date)
    PrimaryKey(room, date)
    composite_key(teacher, date)

db.generate_mapping(create_tables=True)

def test_queries():
    select(grade for grade in Grade if grade.task.type == 'Lab')[:]
    select(grade for grade in Grade if grade.task.descr.startswith('Intermediate'))[:]
    select(grade for grade in Grade if grade.task.course.semester == 2)[:]
    select(grade for grade in Grade if grade.task.course.subject.name == 'Math')[:]
    select(grade for grade in Grade if 'elementary' in grade.task.course.subject.descr.lower())[:]
    select(grade for grade in Grade if 'elementary' in grade.task.course.subject.descr.lower() and grade.task.descr.startswith('Intermediate'))[:]
    select(grade for grade in Grade if grade.task.descr.startswith('Intermediate') and 'elementary' in grade.task.course.subject.descr.lower())[:]
    select(s for s in Student if s.group.dept.faculty.name == 'Abc')[:]
    select(g for g in Group if avg(g.students.grades.value) > 4)[:]
    select(g for g in Group if avg(g.students.grades.value) > 4 and max(g.students.grades.date) < date(2011, 3, 2))[:]
    select(g for g in Group if '4-A' in g.lessons.room.number)[:]
    select(g for g in Group if 1 in g.lessons.room.floor)[:]
    select(t for t in Teacher if t not in t.courses.groups.lessons.teacher)[:]

sql_debug(True)

########NEW FILE########
__FILENAME__ = demo
from decimal import Decimal
from pony.orm import *

db = Database("sqlite", "demo.sqlite", create_db=True)

class Customer(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    email = Required(unicode, unique=True)
    orders = Set("Order")

class Order(db.Entity):
    id = PrimaryKey(int, auto=True)
    total_price = Required(Decimal)
    customer = Required(Customer)
    items = Set("OrderItem")

class Product(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    price = Required(Decimal)
    items = Set("OrderItem")

class OrderItem(db.Entity):
    quantity = Required(int, default=1)
    order = Required(Order)
    product = Required(Product)
    PrimaryKey(order, product)

sql_debug(True)
db.generate_mapping(create_tables=True)

def populate_database():
    c1 = Customer(name='John Smith', email='john@example.com')
    c2 = Customer(name='Matthew Reed', email='matthew@example.com')
    c3 = Customer(name='Chuan Qin', email='chuanqin@example.com')
    c4 = Customer(name='Rebecca Lawson', email='rebecca@example.com')
    c5 = Customer(name='Oliver Blakey', email='oliver@example.com')

    p1 = Product(name='Kindle Fire HD', price=Decimal('284.00'))
    p2 = Product(name='Apple iPad with Retina Display', price=Decimal('478.50'))
    p3 = Product(name='SanDisk Cruzer 16 GB USB Flash Drive', price=Decimal('9.99'))
    p4 = Product(name='Kingston DataTraveler 16GB USB 2.0', price=Decimal('9.98'))
    p5 = Product(name='Samsung 840 Series 120GB SATA III SSD', price=Decimal('98.95'))
    p6 = Product(name='Crucial m4 256GB SSD SATA 6Gb/s', price=Decimal('188.67'))

    o1 = Order(customer=c1, total_price=Decimal('292.00'))
    OrderItem(order=o1, product=p1)
    OrderItem(order=o1, product=p4, quantity=2)

    o2 = Order(customer=c1, total_price=Decimal('478.50'))
    OrderItem(order=o2, product=p2)

    o3 = Order(customer=c2, total_price=Decimal('680.50'))
    OrderItem(order=o3, product=p2)
    OrderItem(order=o3, product=p4, quantity=2)
    OrderItem(order=o3, product=p6)

    o4 = Order(customer=c3, total_price=Decimal('99.80'))
    OrderItem(order=o4, product=p4, quantity=10)

    o5 = Order(customer=c4, total_price=Decimal('722.00'))
    OrderItem(order=o5, product=p1)
    OrderItem(order=o5, product=p2)

    commit()


########NEW FILE########
__FILENAME__ = estore
from decimal import Decimal
from datetime import datetime

from pony.converting import str2datetime
from pony.orm import *

db = Database("sqlite", "estore.sqlite", create_db=True)

class Customer(db.Entity):
    email = Required(unicode, unique=True)
    password = Required(unicode)
    name = Required(unicode)
    country = Required(unicode)
    address = Required(unicode)
    cart_items = Set("CartItem")
    orders = Set("Order")

class Product(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    categories = Set("Category")
    description = Optional(unicode)
    picture = Optional(buffer)
    price = Required(Decimal)
    quantity = Required(int)
    cart_items = Set("CartItem")
    order_items = Set("OrderItem")

class CartItem(db.Entity):
    quantity = Required(int)
    customer = Required(Customer)
    product = Required(Product)

class OrderItem(db.Entity):
    quantity = Required(int)
    price = Required(Decimal)
    order = Required("Order")
    product = Required(Product)
    PrimaryKey(order, product)

class Order(db.Entity):
    id = PrimaryKey(int, auto=True)
    state = Required(unicode)
    date_created = Required(datetime)
    date_shipped = Optional(datetime)
    date_delivered = Optional(datetime)
    total_price = Required(Decimal)
    customer = Required(Customer)
    items = Set(OrderItem)

class Category(db.Entity):
    name = Required(unicode, unique=True)
    products = Set(Product)

sql_debug(True)

db.generate_mapping(create_tables=True)

# Order states
CREATED = 'CREATED'
SHIPPED = 'SHIPPED'
DELIVERED = 'DELIVERED'
CANCELLED = 'CANCELLED'

@db_session
def populate_database():
    c1 = Customer(email='john@example.com', password='***',
                  name='John Smith', country='USA', address='address 1')

    c2 = Customer(email='matthew@example.com', password='***',
                  name='Matthew Reed', country='USA', address='address 2')

    c3 = Customer(email='chuanqin@example.com', password='***',
                  name='Chuan Qin', country='China', address='address 3')

    c4 = Customer(email='rebecca@example.com', password='***',
                  name='Rebecca Lawson', country='USA', address='address 4')

    c5 = Customer(email='oliver@example.com', password='***',
                  name='Oliver Blakey', country='UK', address='address 5')

    tablets = Category(name='Tablets')
    flash_drives = Category(name='USB Flash Drives')
    ssd = Category(name='Solid State Drives')
    storage = Category(name='Data Storage')

    p1 = Product(name='Kindle Fire HD', price=Decimal('284.00'), quantity=120,
                 description='Amazon tablet for web, movies, music, apps, '
                             'games, reading and more',
                 categories=[tablets])

    p2 = Product(name='Apple iPad with Retina Display MD513LL/A (16GB, Wi-Fi, White)',
                 price=Decimal('478.50'), quantity=180,
                 description='iPad with Retina display now features an A6X chip, '
                             'FaceTime HD camera, and faster Wi-Fi',
                 categories=[tablets])

    p3 = Product(name='SanDisk Cruzer 16 GB USB Flash Drive', price=Decimal('9.99'),
                 quantity=400, description='Take it all with you on reliable '
                                           'SanDisk USB flash drive',
                 categories=[flash_drives, storage])

    p4 = Product(name='Kingston Digital DataTraveler SE9 16GB USB 2.0',
                 price=Decimal('9.98'), quantity=350,
                 description='Convenient - small, capless and pocket-sized '
                             'for easy transportability',
                 categories=[flash_drives, storage])

    p5 = Product(name='Samsung 840 Series 2.5 inch 120GB SATA III SSD',
                 price=Decimal('98.95'), quantity=0,
                 description='Enables you to boot up your computer '
                             'in as little as 15 seconds',
                 categories=[ssd, storage])

    p6 = Product(name='Crucial m4 256GB 2.5-Inch SSD SATA 6Gb/s CT256M4SSD2',
                 price=Decimal('188.67'), quantity=60,
                 description='The award-winning SSD delivers '
                             'powerful performance gains for SATA 6Gb/s systems',
                 categories=[ssd, storage])

    CartItem(customer=c1, product=p1, quantity=1)
    CartItem(customer=c1, product=p2, quantity=1)
    CartItem(customer=c2, product=p5, quantity=2)

    o1 = Order(customer=c1, total_price=Decimal('292.00'), state=DELIVERED,
               date_created=str2datetime('2012-10-20 15:22:00'),
               date_shipped=str2datetime('2012-10-21 11:34:00'),
               date_delivered=str2datetime('2012-10-26 17:23:00'))

    OrderItem(order=o1, product=p1, price=Decimal('274.00'), quantity=1)
    OrderItem(order=o1, product=p4, price=Decimal('9.98'), quantity=2)

    o2 = Order(customer=c1, total_price=Decimal('478.50'), state=DELIVERED,
               date_created=str2datetime('2013-01-10 09:40:00'),
               date_shipped=str2datetime('2013-01-10 14:03:00'),
               date_delivered=str2datetime('2013-01-13 11:57:00'))

    OrderItem(order=o2, product=p2, price=Decimal('478.50'), quantity=1)

    o3 = Order(customer=c2, total_price=Decimal('680.50'), state=DELIVERED,
               date_created=str2datetime('2012-11-03 12:10:00'),
               date_shipped=str2datetime('2012-11-04 11:47:00'),
               date_delivered=str2datetime('2012-11-07 18:55:00'))

    OrderItem(order=o3, product=p2, price=Decimal('478.50'), quantity=1)
    OrderItem(order=o3, product=p4, price=Decimal('9.98'), quantity=2)
    OrderItem(order=o3, product=p6, price=Decimal('199.00'), quantity=1)

    o4 = Order(customer=c3, total_price=Decimal('99.80'), state=SHIPPED,
               date_created=str2datetime('2013-03-11 19:33:00'),
               date_shipped=str2datetime('2013-03-12 09:40:00'))

    OrderItem(order=o4, product=p4, price=Decimal('9.98'), quantity=10)

    o5 = Order(customer=c4, total_price=Decimal('722.00'), state=CREATED,
               date_created=str2datetime('2013-03-15 23:15:00'))

    OrderItem(order=o5, product=p1, price=Decimal('284.00'), quantity=1)
    OrderItem(order=o5, product=p2, price=Decimal('478.50'), quantity=1)

@db_session
def test_queries():

    print 'All USA customers'
    print
    result = select(c for c in Customer if c.country == 'USA')[:]

    print result
    print

    print 'The number of customers for each country'
    print
    result = select((c.country, count(c)) for c in Customer)[:]

    print result
    print

    print 'Max product price'
    print
    result = max(p.price for p in Product)

    print result
    print

    print 'Max SSD price'
    print
    result = max(p.price for p in Product for cat in p.categories if cat.name == 'Solid State Drives')

    print result
    print

    print 'Three most expensive products:'
    print
    result = select(p for p in Product).order_by(desc(Product.price))[:3]

    print result
    print

    print 'Out of stock products'
    print
    result = select(p for p in Product if p.quantity == 0)[:]

    print result
    print

    print 'Most popular product'
    print
    result = select(p for p in Product).order_by(lambda p: desc(sum(p.order_items.quantity))).first()

    print result
    print

    print 'Products that have never been ordered'
    print
    result = select(p for p in Product if not p.order_items)[:]

    print result
    print

    print 'Customers who made several orders'
    print
    result = select(c for c in Customer if count(c.orders) > 1)[:]

    print result
    print

    print 'Three most valuable customers'
    print
    result = select(c for c in Customer).order_by(lambda c: desc(sum(c.orders.total_price)))[:3]
    
    print result
    print

    print 'Customers whose orders were shipped'
    print
    result = select(c for c in Customer if SHIPPED in c.orders.state)[:]

    print result
    print

    print 'The same query with the INNER JOIN instead of IN'
    print
    result = select(c for c in Customer if JOIN(SHIPPED in c.orders.state))[:]

    print result
    print

    print 'Customers with no orders'
    print
    result = select(c for c in Customer if not c.orders)[:]

    print result
    print

    print 'The same query with the LEFT JOIN instead of NOT EXISTS'
    print
    result = left_join(c for c in Customer for o in c.orders if o is None)[:]

    print result
    print

    print 'Customers which ordered several different tablets'
    print
    result = select(c for c in Customer
                      for p in c.orders.items.product
                      if 'Tablets' in p.categories.name and count(p) > 1)[:]

    print result
    print

    print 'Customers which ordered several products from the same category'
    print
    result = select((customer, category.name)
                    for customer in Customer
                    for product in customer.orders.items.product
                    for category in product.categories
                    if count(product) > 1)[:]    

    print result
    print

    print 'Customers which ordered several products from the same category in the same order'
    print
    result = select((customer, order, category.name)
                    for customer in Customer
                    for order in customer.orders
                    for product in order.items.product
                    for category in product.categories
                    if count(product) > 1)[:]

    print result
    print

    print 'Products whose price varies over time'
    print
    result = select(p.name for p in Product if count(p.order_items.price) > 1)[:]

    print result
    print

    print 'The same query, but with min and max price for each product'
    print
    result = select((p.name, min(p.order_items.price), max(p.order_items.price))
                    for p in Product if count(p.order_items.price) > 1)[:]

    print result
    print

    print 'Orders with a discount (order total price < sum of order item prices)'
    print
    result = select(o for o in Order if o.total_price < sum(o.items.price * o.items.quantity))[:]

    print result
    print


if __name__ == '__main__':
    with db_session:
        if Customer.select().first() is None:
            populate_database()
    test_queries()

########NEW FILE########
__FILENAME__ = inheritance1
from decimal import Decimal
from datetime import date

from pony import options
options.CUT_TRACEBACK = False

from pony.orm.core import *

sql_debug(False)

db = Database('sqlite', 'inheritance1.sqlite', create_db=True)

class Person(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    dob = Optional(date)
    ssn = Required(str, unique=True)

class Student(Person):
    group = Required("Group")
    mentor = Optional("Teacher")
    attend_courses = Set("Course")

class Teacher(Person):
    teach_courses = Set("Course")
    apprentices = Set("Student")
    salary = Required(Decimal)

class Assistant(Student, Teacher):
    pass

class Professor(Teacher):
    position = Required(unicode)

class Group(db.Entity):
    number = PrimaryKey(int)
    students = Set("Student")

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    students = Set(Student)
    teachers = Set(Teacher)
    PrimaryKey(name, semester)

db.generate_mapping(create_tables=True)

@db_session
def populate_database():
    if Person.select().first():
        return # already populated

    p = Person(name='Person1', ssn='SSN1')
    g = Group(number=123)
    prof = Professor(name='Professor1', salary=1000, position='position1', ssn='SSN5')
    a1 = Assistant(name='Assistant1', group=g, salary=100, ssn='SSN4', mentor=prof)
    a2 = Assistant(name='Assistant2', group=g, salary=200, ssn='SSN6', mentor=prof)
    s1 = Student(name='Student1', group=g, ssn='SSN2', mentor=a1)
    s2 = Student(name='Student2', group=g, ssn='SSN3')
    commit()

def show_all_persons():
    for obj in Person.select():
        print obj
        for attr in obj._attrs_:
            print attr.name, "=", attr.__get__(obj)
        print

if __name__ == '__main__':
    populate_database()
    # show_all_persons()

    sql_debug(True)

    with db_session:
        s1 = Student.get(name='Student1')
        if s1 is None:
            print 'Student1 not found'
        else:
            mentor = s1.mentor
            print mentor.name, 'is mentor of Student1'
            print 'Is he assistant?', isinstance(mentor, Assistant)
        print

        for s in Student.select(lambda s: s.mentor.salary == 1000):
            print s.name

########NEW FILE########
__FILENAME__ = presentation
from decimal import Decimal
from datetime import date

from pony.orm.core import *

db = Database()

class Department(db.Entity):
    number = PrimaryKey(int, auto=True)
    name = Required(unicode, unique=True)
    groups = Set("Group")
    courses = Set("Course")

class Group(db.Entity):
    number = PrimaryKey(int)
    major = Required(unicode)
    dept = Required("Department")
    students = Set("Student")

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    lect_hours = Required(int)
    lab_hours = Required(int)
    credits = Required(int)
    dept = Required(Department)
    students = Set("Student")
    PrimaryKey(name, semester)

class Student(db.Entity):
    # _table_ = "public", "Students"  # Schema support
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    dob = Required(date)
    tel = Optional(str)
    picture = Optional(buffer, lazy=True)
    gpa = Required(float, default=0)
    group = Required(Group)
    courses = Set(Course)

sql_debug(True)  # Output all SQL queries to stdout

db.bind('sqlite', 'presentation.sqlite', create_db=True)
#db.bind('mysql', host="localhost", user="presentation", passwd="pony", db="presentation")
#db.bind('postgres', user='presentation', password='pony', host='localhost', database='presentation')
#db.bind('oracle', 'presentation/pony@localhost')

db.generate_mapping(create_tables=True)

@db_session
def populate_database():
    if select(s for s in Student).count() > 0:
        return

    d1 = Department(name="Department of Computer Science")
    d2 = Department(name="Department of Mathematical Sciences")
    d3 = Department(name="Department of Applied Physics")

    c1 = Course(name="Web Design", semester=1, dept=d1,
                       lect_hours=30, lab_hours=30, credits=3)
    c2 = Course(name="Data Structures and Algorithms", semester=3, dept=d1,
                       lect_hours=40, lab_hours=20, credits=4)

    c3 = Course(name="Linear Algebra", semester=1, dept=d2,
                       lect_hours=30, lab_hours=30, credits=4)
    c4 = Course(name="Statistical Methods", semester=2, dept=d2,
                       lect_hours=50, lab_hours=25, credits=5)

    c5 = Course(name="Thermodynamics", semester=2, dept=d3,
                       lect_hours=25, lab_hours=40, credits=4)
    c6 = Course(name="Quantum Mechanics", semester=3, dept=d3,
                       lect_hours=40, lab_hours=30, credits=5)

    g101 = Group(number=101, major='B.E. in Computer Engineering', dept=d1)
    g102 = Group(number=102, major='B.S./M.S. in Computer Science', dept=d1)
    g103 = Group(number=103, major='B.S. in Applied Mathematics and Statistics', dept=d2)
    g104 = Group(number=104, major='B.S./M.S. in Pure Mathematics', dept=d2)
    g105 = Group(number=105, major='B.E in Electronics', dept=d3)
    g106 = Group(number=106, major='B.S./M.S. in Nuclear Engineering', dept=d3)

    s1 = Student(name='John Smith', dob=date(1991, 3, 20), tel='123-456', gpa=3, group=g101,
                        courses=[c1, c2, c4, c6])
    s2 = Student(name='Matthew Reed', dob=date(1990, 11, 26), gpa=3.5, group=g101,
                        courses=[c1, c3, c4, c5])
    s3 = Student(name='Chuan Qin', dob=date(1989, 2, 5), gpa=4, group=g101,
                        courses=[c3, c5, c6])
    s4 = Student(name='Rebecca Lawson', dob=date(1990, 4, 18), tel='234-567', gpa=3.3, group=g102,
                        courses=[c1, c4, c5, c6])
    s5 = Student(name='Maria Ionescu', dob=date(1991, 4, 23), gpa=3.9, group=g102,
                        courses=[c1, c2, c4, c6])
    s6 = Student(name='Oliver Blakey', dob=date(1990, 9, 8), gpa=3.1, group=g102,
                        courses=[c1, c2, c5])
    s7 = Student(name='Jing Xia', dob=date(1988, 12, 30), gpa=3.2, group=g102,
                        courses=[c1, c3, c5, c6])
    commit()

def print_students(students):
    for s in students:
        print s.name
    print

@db_session
def test_queries():
    students = select(s for s in Student)
    print_students(students)


    students = select(s for s in Student if s.gpa > 3.4 and s.dob.year == 1990)
    print_students(students)


    students = select(s for s in Student if len(s.courses) < 4)
    print_students(students)


    students = select(s for s in Student
                       if len(c for c in s.courses if c.dept.number == 1) < 4)
    print_students(students)


    students = select(s for s in Student if s.name.startswith("M"))
    print_students(students)


    students = select(s for s in Student if "Smith" in s.name)
    print_students(students)


    students = select(s for s in Student
                         if "Web Design" in s.courses.name)
    print_students(students)


    print 'Average GPA is', avg(s.gpa for s in Student)
    print


    students = select(s for s in Student
                         if sum(c.credits for c in s.courses) < 15)
    print_students(students)


    students = select(s for s in Student
                         if s.group.major == "B.E. in Computer Engineering")
    print_students(students)


    students = select(s for s in Student
                         if s.group.dept.name == "Department of Computer Science")
    print_students(students)


    students = select(s for s in Student).order_by(Student.name)
    print_students(students)


    students = select(s for s in Student).order_by(Student.name)[2:4]
    print_students(students)


    students = select(s for s in Student).order_by(Student.name.desc)
    print_students(students)


    students = select(s for s in Student) \
               .order_by(Student.group, Student.name.desc)
    print_students(students)


    students = select(s for s in Student
                         if s.group.dept.name == "Department of Computer Science"
                            and s.gpa > 3.5
                            and len(s.courses) > 3)
    print_students(students)


##if __name__ == '__main__':
##    populate_database()
##    test_queries()

########NEW FILE########
__FILENAME__ = university
from pony.orm.core import *
from decimal import Decimal
from datetime import date

db = Database('sqlite', 'university.sqlite', create_db=True)
# db = Database('mysql', host='localhost', user='root', passwd='root', db='university')

class Faculty(db.Entity):
    _table_ = 'Faculties'
    number = PrimaryKey(int)
    name = Required(str, unique=True)
    departments = Set('Department')

class Department(db.Entity):
    _table_ = 'Departments'
    number = PrimaryKey(int)
    name = Required(str, unique=True)
    faculty = Required(Faculty)
    teachers = Set('Teacher')
    majors = Set('Major')
    groups = Set('Group')

class Group(db.Entity):
    _table_ = 'Groups'
    number = PrimaryKey(int)
    grad_year = Required(int)
    department = Required(Department, column='dep')
    lessons = Set('Lesson', columns=['day_of_week', 'meeting_time', 'classroom_number', 'building'])
    students = Set('Student')

class Student(db.Entity):
    _table_ = 'Students'
    name = Required(unicode)
    scholarship = Required(Decimal, 10, 2, default=Decimal('0.0'))
    group = Required(Group)
    grades = Set('Grade')

class Major(db.Entity):
    _table_ = 'Majors'
    name = PrimaryKey(str)
    department = Required(Department)
    courses = Set('Course')

class Subject(db.Entity):
    _table_ = 'Subjects'
    name = PrimaryKey(str)
    courses = Set('Course')
    teachers = Set('Teacher')

class Course(db.Entity):
    _table_ = 'Courses'
    major = Required(Major)
    subject = Required(Subject)
    semester = Required(int)
    composite_key(major, subject, semester)
    lect_hours = Required(int)
    pract_hours = Required(int)
    credit = Required(int)
    lessons = Set('Lesson')
    grades = Set('Grade')

class Lesson(db.Entity):
    _table_ = 'Lessons'
    day_of_week = Required(int)
    meeting_time = Required(int)
    classroom = Required('Classroom')
    PrimaryKey(day_of_week, meeting_time, classroom)
    course = Required(Course)
    teacher = Required('Teacher')
    groups = Set(Group)

class Grade(db.Entity):
    _table_ = 'Grades'
    student = Required(Student)
    course = Required(Course)
    PrimaryKey(student, course)
    teacher = Required('Teacher')
    date = Required(date)
    value = Required(str)

class Teacher(db.Entity):
    _table_ = 'Teachers'
    name = Required(str)
    degree = Optional(str)
    department = Required(Department)
    subjects = Set(Subject)
    lessons = Set(Lesson)
    grades = Set(Grade)

class Building(db.Entity):
    _table_ = 'Buildings'
    number = PrimaryKey(str)
    description = Optional(str)
    classrooms = Set('Classroom')

class Classroom(db.Entity):
    _table_ = 'Classrooms'
    building = Required(Building)
    number = Required(str)
    PrimaryKey(building, number)
    description = Optional(str)
    lessons = Set(Lesson)

db.generate_mapping(create_tables=True)

sql_debug(True)

def test_queries():
    # very simple query
    select(s for s in Student)[:]

    # one condition
    select(s for s in Student if s.scholarship > 0)[:]

    # multiple conditions
    select(s for s in Student if s.scholarship > 0 and s.group.number == 4142)[:]

    # no join here - attribute can be found in table Students
    select(s for s in Student if s.group.number == 4142)[:]

    # automatic join of two tables because grad_year is stored in table Groups
    select(s for s in Student if s.group.grad_year == 2011)[:]

    # still two tables are joined
    select(s for s in Student if s.group.department.number == 44)[:]

    # automatic join of tree tables
    select(s for s in Student if s.group.department.name == 'Ancient Philosophy')[:]

    # manual join of tables will produce equivalent query
    select(s for s in Student for g in Group if s.group == g and g.department.name == 'Ancient Philosophy')[:]

    # join two tables by composite foreign key
    select(c for c in Classroom for l in Lesson if l.classroom == c and l.course.subject.name == 'Physics')[:]

    # Lessons  will be joined with Buildings directly without Classrooms
    select(s for s in Subject for l in Lesson if s == l.course.subject and l.classroom.building.description == 'some description')[:]

    # just another example of join of many tables
    select(c for c in Course if c.major.department.faculty.number == 4)[:]

########NEW FILE########
__FILENAME__ = bottle_plugin
from bottle import HTTPResponse, HTTPError
from pony.orm.core import db_session

def is_allowed_exception(e):
    return isinstance(e, HTTPResponse) and not isinstance(e, HTTPError)

class PonyPlugin(object):
    name = 'pony'
    api  = 2
    def apply(self, callback, route):
        return db_session(allowed_exceptions=is_allowed_exception)(callback)

########NEW FILE########
__FILENAME__ = ormtypes
import types
from types import NoneType
from decimal import Decimal
from datetime import date, datetime
from itertools import izip
from uuid import UUID

from pony.utils import throw

class AsciiStr(str): pass

class LongStr(str):
    lazy = True

class LongUnicode(unicode):
    lazy = True

class SetType(object):
    __slots__ = 'item_type'
    def __deepcopy__(self, memo):
        return self  # SetType instances are "immutable"
    def __init__(self, item_type):
        self.item_type = item_type
    def __eq__(self, other):
        return type(other) is SetType and self.item_type == other.item_type
    def __ne__(self, other):
        return type(other) is not SetType or self.item_type != other.item_type
    def __hash__(self):
        return hash(self.item_type) + 1

class FuncType(object):
    __slots__ = 'func'
    def __deepcopy__(self, memo):
        return self  # FuncType instances are "immutable"
    def __init__(self, func):
        self.func = func
    def __eq__(self, other):
        return type(other) is FuncType and self.func == other.func
    def __ne__(self, other):
        return type(other) is not FuncType or self.func != other.func
    def __hash__(self):
        return hash(self.func) + 1

class MethodType(object):
    __slots__ = 'obj', 'func'
    def __deepcopy__(self, memo):
        return self  # MethodType instances are "immutable"
    def __init__(self, method):
        self.obj = method.im_self
        self.func = method.im_func
    def __eq__(self, other):
        return type(other) is MethodType and self.obj == other.obj and self.func == other.func
    def __ne__(self, other):
        return type(other) is not SetType or self.obj != other.obj or self.func != other.func
    def __hash__(self):
        return hash(self.obj) ^ hash(self.func)

numeric_types = set([ bool, int, float, Decimal ])
string_types = set([ str, AsciiStr, unicode ])
comparable_types = set([ int, float, Decimal, str, AsciiStr, unicode, date, datetime, bool, UUID ])
primitive_types = set([ int, float, Decimal, str, AsciiStr, unicode, date, datetime, bool, buffer, UUID ])
type_normalization_dict = { long : int, LongStr : str, LongUnicode : unicode }
function_types = set([type, types.FunctionType, types.BuiltinFunctionType])

def get_normalized_type_of(value):
    t = type(value)
    if t is tuple: return tuple(get_normalized_type_of(item) for item in value)
    try: hash(value)  # without this, cannot do tests like 'if value in special_fucntions...'
    except TypeError: throw(TypeError, 'Unsupported type %r' % t.__name__)
    if t.__name__ == 'EntityMeta': return SetType(value)
    if t.__name__ == 'EntityIter': return SetType(value.entity)
    if isinstance(value, str):
        try: value.decode('ascii')
        except UnicodeDecodeError: pass
        else: return AsciiStr
    elif isinstance(value, unicode):
        try: value.encode('ascii')
        except UnicodeEncodeError: pass
        else: return AsciiStr
    if t in function_types: return FuncType(value)
    if t is types.MethodType: return MethodType(value)
    return normalize_type(t)

def normalize_type(t):
    tt = type(t)
    if tt is tuple: return tuple(normalize_type(item) for item in t)
    assert t.__name__ != 'EntityMeta'
    if tt.__name__ == 'EntityMeta': return t
    if t is NoneType: return t
    t = type_normalization_dict.get(t, t)
    if t in primitive_types: return t
    if issubclass(t, basestring):  # Mainly for Html -> unicode & StrHtml -> str conversion
        if issubclass(t, str): return str
        if issubclass(t, unicode): return unicode
        assert False
    throw(TypeError, 'Unsupported type %r' % t.__name__)

coercions = {
    (int, float) : float,
    (int, Decimal) : Decimal,
    (date, datetime) : datetime,
    (AsciiStr, str) : str,
    (AsciiStr, unicode) : unicode,
    (bool, int) : int,
    (bool, float) : float,
    (bool, Decimal) : Decimal
    }
coercions.update(((t2, t1), t3) for ((t1, t2), t3) in coercions.items())

def coerce_types(t1, t2):
    if t1 == t2: return t1
    is_set_type = False
    if type(t1) is SetType:
        is_set_type = True
        t1 = t1.item_type
    if type(t2) is SetType:
        is_set_type = True
        t2 = t2.item_type
    result = coercions.get((t1, t2))
    if result is not None and is_set_type: result = SetType(result)
    return result

def are_comparable_types(t1, t2, op='=='):
    # types must be normalized already!
    tt1 = type(t1)
    tt2 = type(t2)
    if op in ('in', 'not in'):
        if tt2 is not SetType: return False
        op = '=='
        t2 = t2.item_type
        tt2 = type(t2)
    if op in ('is', 'is not'):
        return t1 is not None and t2 is NoneType
    if tt1 is tuple:
        if not tt2 is tuple: return False
        if len(t1) != len(t2): return False
        for item1, item2 in izip(t1, t2):
            if not are_comparable_types(item1, item2): return False
        return True
    if op in ('==', '<>', '!='):
        if t1 is NoneType and t2 is NoneType: return False
        if t1 is NoneType or t2 is NoneType: return True
        if t1 in primitive_types:
            if t1 is t2: return True
            if (t1, t2) in coercions: return True
            if tt1 is not type or tt2 is not type: return False
            if issubclass(t1, (int, long)) and issubclass(t2, basestring): return True
            if issubclass(t2, (int, long)) and issubclass(t1, basestring): return True
            return False
        if tt1.__name__ == tt2.__name__ == 'EntityMeta':
            return t1._root_ is t2._root_
        return False
    if t1 is t2 and t1 in comparable_types: return True
    return (t1, t2) in coercions

########NEW FILE########
__FILENAME__ = sqlbuilding
from operator import attrgetter
from decimal import Decimal
from datetime import date, datetime
from binascii import hexlify

from pony import options
from pony.utils import datetime2timestamp, throw

class AstError(Exception): pass

class Param(object):
    __slots__ = 'style', 'id', 'paramkey', 'py2sql'
    def __init__(param, paramstyle, id, paramkey, converter=None):
        param.style = paramstyle
        param.id = id
        param.paramkey = paramkey
        param.py2sql = converter and converter.py2sql or (lambda val: val)
    def __unicode__(param):
        paramstyle = param.style
        if paramstyle == 'qmark': return u'?'
        elif paramstyle == 'format': return u'%s'
        elif paramstyle == 'numeric': return u':%d' % param.id
        elif paramstyle == 'named': return u':p%d' % param.id
        elif paramstyle == 'pyformat': return u'%%(p%d)s' % param.id
        else: throw(NotImplementedError)
    def __repr__(param):
        return '%s(%r)' % (param.__class__.__name__, param.paramkey)

class Value(object):
    __slots__ = 'paramstyle', 'value'
    def __init__(self, paramstyle, value):
        self.paramstyle = paramstyle
        self.value = value
    def __unicode__(self):
        value = self.value
        if value is None: return 'null'
        if isinstance(value, bool): return value and '1' or '0'
        if isinstance(value, (int, long, float, Decimal)): return str(value)
        if isinstance(value, basestring): return self.quote_str(value)
        if isinstance(value, datetime): return self.quote_str(datetime2timestamp(value))
        if isinstance(value, date): return self.quote_str(str(value))
        if isinstance(value, buffer): return "X'%s'" % hexlify(value)
        assert False, value
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)
    def quote_str(self, s):
        if self.paramstyle in ('format', 'pyformat'): s = s.replace('%', '%%')
        return "'%s'" % s.replace("'", "''")

def flat(tree):
    stack = [ tree ]
    result = []
    stack_pop = stack.pop
    stack_extend = stack.extend
    result_append = result.append
    while stack:
        x = stack_pop()
        if isinstance(x, basestring): result_append(x)
        else:
            try: stack_extend(reversed(x))
            except TypeError: result_append(x)
    return result

def flat_conditions(conditions):
    result = []
    for condition in conditions:
        if condition[0] == 'AND':
            result.extend(flat_conditions(condition[1:]))
        else: result.append(condition)
    return result

def join(delimiter, items):
    items = iter(items)
    try: result = [ items.next() ]
    except StopIteration: return []
    for item in items:
        result.append(delimiter)
        result.append(item)
    return result

def move_conditions_from_inner_join_to_where(sections):
    new_sections = list(sections)
    for i, section in enumerate(sections):
        if section[0] == 'FROM':
            new_from_list = [ 'FROM' ] + [ list(item) for item in section[1:] ]
            new_sections[i] = new_from_list
            if len(sections) > i+1 and sections[i+1][0] == 'WHERE':
                new_where_list = list(sections[i+1])
                new_sections[i+1] = new_where_list
            else:
                new_where_list = [ 'WHERE' ]
                new_sections.insert(i+1, new_where_list)
            break
    else: return sections
    for join in new_from_list[2:]:
        if join[1] in ('TABLE', 'SELECT') and len(join) == 4:
            new_where_list.append(join.pop())
    return new_sections

def make_binary_op(symbol, default_parentheses=False):
    def binary_op(builder, expr1, expr2, parentheses=None):
        if parentheses is None: parentheses = default_parentheses
        if parentheses: return '(', builder(expr1), symbol, builder(expr2), ')'
        return builder(expr1), symbol, builder(expr2)
    return binary_op

def make_unary_func(symbol):
    def unary_func(builder, expr):
        return '%s(' % symbol, builder(expr), ')'
    return unary_func

def indentable(method):
    def new_method(builder, *args, **kwargs):
        result = method(builder, *args, **kwargs)
        if builder.indent <= 1: return result
        return builder.indent_spaces * (builder.indent-1), result
    new_method.__name__ = method.__name__
    return new_method

def convert(values, params):
    for param in params:
        varkey, i, j = param.paramkey
        value = values[varkey]
        if i is not None:
            assert type(value) is tuple
            value = value[i]
        if j is not None:
            assert type(type(value)).__name__ == 'EntityMeta'
            value = value._get_raw_pkval_()[j]
        if value is not None:  # can value be None at all?
            value = param.py2sql(value)
        yield value

class SQLBuilder(object):
    dialect = None
    make_param = Param
    make_value = Value
    indent_spaces = " " * 4
    def __init__(builder, provider, ast):
        builder.provider = provider
        builder.quote_name = provider.quote_name
        builder.paramstyle = paramstyle = provider.paramstyle
        builder.ast = ast
        builder.indent = 0
        builder.keys = {}
        builder.inner_join_syntax = options.INNER_JOIN_SYNTAX
        builder.result = flat(builder(ast))
        builder.sql = u''.join(map(unicode, builder.result)).rstrip('\n')
        if paramstyle in ('qmark', 'format'):
            params = tuple(x for x in builder.result if isinstance(x, Param))
            def adapter(values):
                return tuple(convert(values, params))
        elif paramstyle == 'numeric':
            params = tuple(param for param in sorted(builder.keys.itervalues(), key=attrgetter('id')))
            def adapter(values):
                return tuple(convert(values, params))
        elif paramstyle in ('named', 'pyformat'):
            params = tuple(param for param in sorted(builder.keys.itervalues(), key=attrgetter('id')))
            def adapter(values):
                return dict(('p%d' % param.id, value) for param, value in zip(params, convert(values, params)))
        else: throw(NotImplementedError, paramstyle)
        builder.params = params
        builder.layout = tuple(param.paramkey for param in params)
        builder.adapter = adapter
    def __call__(builder, ast):
        if isinstance(ast, basestring):
            throw(AstError, 'An SQL AST list was expected. Got string: %r' % ast)
        symbol = ast[0]
        if not isinstance(symbol, basestring):
            throw(AstError, 'Invalid node name in AST: %r' % ast)
        method = getattr(builder, symbol, None)
        if method is None: throw(AstError, 'Method not found: %s' % symbol)
        try:
            return method(*ast[1:])
        except TypeError:
            raise
##            traceback = sys.exc_info()[2]
##            if traceback.tb_next is None:
##                del traceback
##                throw(AstError, 'Invalid data for method %s: %r'
##                               % (symbol, ast[1:]))
##            else:
##                del traceback
##                raise
    def INSERT(builder, table_name, columns, values, returning=None):
        return [ 'INSERT INTO ', builder.quote_name(table_name), ' (',
                 join(', ', [builder.quote_name(column) for column in columns ]),
                 ') VALUES (', join(', ', [builder(value) for value in values]), ')' ]
    def DEFAULT(builder):
        return 'DEFAULT'
    def UPDATE(builder, table_name, pairs, where=None):
        return [ 'UPDATE ', builder.quote_name(table_name), '\nSET ',
                 join(', ', [ (builder.quote_name(name), ' = ', builder(param)) for name, param in pairs]),
                 where and [ '\n', builder(where) ] or [] ]
    def DELETE(builder, table_name, where=None):
        result = [ 'DELETE FROM ', builder.quote_name(table_name) ]
        if where: result += [ '\n', builder(where) ]
        return result
    def subquery(builder, *sections):
        builder.indent += 1
        if not builder.inner_join_syntax:
            sections = move_conditions_from_inner_join_to_where(sections)
        result = [ builder(s) for s in sections ]
        builder.indent -= 1
        return result
    def SELECT(builder, *sections):
        result = builder.subquery(*sections)
        if builder.indent:
            indent = builder.indent_spaces * builder.indent
            return '(\n', result, indent + ')'
        return result
    def SELECT_FOR_UPDATE(builder, nowait, *sections):
        assert not builder.indent
        result = builder.SELECT(*sections)
        return result, 'FOR UPDATE NOWAIT\n' if nowait else 'FOR UPDATE\n'
    def EXISTS(builder, *sections):
        result = builder.subquery(*sections)
        indent = builder.indent_spaces * builder.indent
        return 'EXISTS (\n', indent, 'SELECT 1\n', result, indent, ')'
    def NOT_EXISTS(builder, *sections):
        return 'NOT ', builder.EXISTS(*sections)
    @indentable
    def ALL(builder, *expr_list):
        exprs = [ builder(e) for e in expr_list ]
        return 'SELECT ', join(', ', exprs), '\n'
    @indentable
    def DISTINCT(builder, *expr_list):
        exprs = [ builder(e) for e in expr_list ]
        return 'SELECT DISTINCT ', join(', ', exprs), '\n'
    @indentable
    def AGGREGATES(builder, *expr_list):
        exprs = [ builder(e) for e in expr_list ]
        return 'SELECT ', join(', ', exprs), '\n'
    def AS(builder, expr, alias):
        return builder(expr), ' AS ', builder.quote_name(alias)
    def compound_name(builder, name_parts):
        return '.'.join(p and builder.quote_name(p) or '' for p in name_parts)
    def sql_join(builder, join_type, sources):
        indent = builder.indent_spaces * (builder.indent-1)
        indent2 = indent + builder.indent_spaces
        indent3 = indent2 + builder.indent_spaces
        result = [ indent, 'FROM ']
        for i, source in enumerate(sources):
            if len(source) == 3:
                alias, kind, x = source
                join_cond = None
            elif len(source) == 4:
                alias, kind, x, join_cond = source
            else: throw(AstError, 'Invalid source in FROM section: %r' % source)
            if i > 0:
                if join_cond is None: result.append(', ')
                else: result += [ '\n', indent, '  %s JOIN ' % join_type ]
            if alias is not None: alias = builder.quote_name(alias)
            if kind == 'TABLE':
                if isinstance(x, basestring): result.append(builder.quote_name(x))
                else: result.append(builder.compound_name(x))
                if alias is not None: result += ' ', alias  # Oracle does not support 'AS' here
            elif kind == 'SELECT':
                if alias is None: throw(AstError, 'Subquery in FROM section must have an alias')
                result += builder.SELECT(*x), ' ', alias  # Oracle does not support 'AS' here
            else: throw(AstError, 'Invalid source kind in FROM section: %r' % kind)
            if join_cond is not None: result += [ '\n', indent2, 'ON ', builder(join_cond) ]
        result.append('\n')
        return result
    def FROM(builder, *sources):
        return builder.sql_join('INNER', sources)
    def INNER_JOIN(builder, *sources):
        builder.inner_join_syntax = True
        return builder.sql_join('INNER', sources)
    @indentable
    def LEFT_JOIN(builder, *sources):
        return builder.sql_join('LEFT', sources)
    def WHERE(builder, *conditions):
        if not conditions: return ''
        conditions = flat_conditions(conditions)
        indent = builder.indent_spaces * (builder.indent-1)
        result = [ indent, 'WHERE ' ]
        extend = result.extend
        extend((builder(conditions[0]), '\n'))
        for condition in conditions[1:]:
            extend((indent, '  AND ', builder(condition), '\n'))
        return result
    def HAVING(builder, *conditions):
        if not conditions: return ''
        conditions = flat_conditions(conditions)
        indent = builder.indent_spaces * (builder.indent-1)
        result = [ indent, 'HAVING ' ]
        extend = result.extend
        extend((builder(conditions[0]), '\n'))
        for condition in conditions[1:]:
            extend((indent, '  AND ', builder(condition), '\n'))
        return result
    @indentable
    def GROUP_BY(builder, *expr_list):
        exprs = [ builder(e) for e in expr_list ]
        return 'GROUP BY ', join(', ', exprs), '\n'
    @indentable
    def UNION(builder, kind, *sections):
        return 'UNION ', kind, '\n', builder.SELECT(*sections)
    @indentable
    def INTERSECT(builder, *sections):
        return 'INTERSECT\n', builder.SELECT(*sections)
    @indentable
    def EXCEPT(builder, *sections):
        return 'EXCEPT\n', builder.SELECT(*sections)
    @indentable
    def ORDER_BY(builder, *order_list):
        result = [ 'ORDER BY ' ]
        result.extend(join(', ', [ builder(expr) for expr in order_list ]))
        result.append('\n')
        return result
    def DESC(builder, expr):
        return builder(expr), ' DESC'
    @indentable
    def LIMIT(builder, limit, offset=None):
        if not offset: return 'LIMIT ', builder(limit), '\n'
        else: return 'LIMIT ', builder(limit), ' OFFSET ', builder(offset), '\n'
    def COLUMN(builder, table_alias, col_name):
        if table_alias: return [ '%s.%s' % (builder.quote_name(table_alias), builder.quote_name(col_name)) ]
        else: return [ '%s' % (builder.quote_name(col_name)) ]
    def PARAM(builder, paramkey, converter=None):
        keys = builder.keys
        param = keys.get(paramkey)
        if param is None:
            param = Param(builder.paramstyle, len(keys) + 1, paramkey, converter)
            keys[paramkey] = param
        return [ param ]
    def ROW(builder, *items):
        return '(', join(', ', map(builder, items)), ')'
    def VALUE(builder, value):
        return [ builder.make_value(builder.paramstyle, value) ]
    def AND(builder, *cond_list):
        cond_list = [ builder(condition) for condition in cond_list ]
        return join(' AND ', cond_list)
    def OR(builder, *cond_list):
        cond_list = [ builder(condition) for condition in cond_list ]
        return '(', join(' OR ', cond_list), ')'
    def NOT(builder, condition):
        return 'NOT (', builder(condition), ')'
    def POW(builder, expr1, expr2):
        return 'power(', builder(expr1), ', ', builder(expr2), ')'

    EQ  = make_binary_op(' = ')
    NE  = make_binary_op(' <> ')
    LT  = make_binary_op(' < ')
    LE  = make_binary_op(' <= ')
    GT  = make_binary_op(' > ')
    GE  = make_binary_op(' >= ')
    ADD = make_binary_op(' + ', True)
    SUB = make_binary_op(' - ', True)
    MUL = make_binary_op(' * ', True)
    DIV = make_binary_op(' / ', True)

    def CONCAT(builder, *args):
        return '(',  join(' || ', map(builder, args)), ')'
    def NEG(builder, expr):
        return '-(', builder(expr), ')'
    def IS_NULL(builder, expr):
        return builder(expr), ' IS NULL'
    def IS_NOT_NULL(builder, expr):
        return builder(expr), ' IS NOT NULL'
    def LIKE(builder, expr, template, escape=None):
        result = builder(expr), ' LIKE ', builder(template)
        if escape: result = result + (' ESCAPE ', builder(escape))
        return result
    def NOT_LIKE(builder, expr, template, escape=None):
        result = builder(expr), ' NOT LIKE ', builder(template)
        if escape: result = result + (' ESCAPE ', builder(escape))
        return result
    def BETWEEN(builder, expr1, expr2, expr3):
        return builder(expr1), ' BETWEEN ', builder(expr2), ' AND ', builder(expr3)
    def NOT_BETWEEN(builder, expr1, expr2, expr3):
        return builder(expr1), ' NOT BETWEEN ', builder(expr2), ' AND ', builder(expr3)
    def IN(builder, expr1, x):
        if not x: return '0 = 1'
        if len(x) >= 1 and x[0] == 'SELECT':
            return builder(expr1), ' IN ', builder(x)
        expr_list = [ builder(expr) for expr in x ]
        return builder(expr1), ' IN (', join(', ', expr_list), ')'
    def NOT_IN(builder, expr1, x):
        if not x: throw(AstError, 'Empty IN clause')
        if len(x) >= 1 and x[0] == 'SELECT':
            return builder(expr1), ' NOT IN ', builder(x)
        expr_list = [ builder(expr) for expr in x ]
        return builder(expr1), ' NOT IN (', join(', ', expr_list), ')'
    def COUNT(builder, kind, *expr_list):
        if kind == 'ALL':
            if not expr_list: return ['COUNT(*)']
            return 'COUNT(', join(', ', map(builder, expr_list)), ')'
        elif kind == 'DISTINCT':
            if not expr_list: throw(AstError, 'COUNT(DISTINCT) without argument')
            if len(expr_list) == 1: return 'COUNT(DISTINCT ', builder(expr_list[0]), ')'
            if builder.dialect == 'PostgreSQL':
                return 'COUNT(DISTINCT ', builder.ROW(*expr_list), ')'
            elif builder.dialect == 'MySQL':
                return 'COUNT(DISTINCT ', join(', ', map(builder, expr_list)), ')'
            # Oracle and SQLite queries translated to completely different subquery syntax
            else: throw(NotImplementedError)  # This line must not be executed
        throw(AstError, 'Invalid COUNT kind (must be ALL or DISTINCT)')
    def SUM(builder, expr, distinct=False):
        return distinct and 'coalesce(SUM(DISTINCT ' or 'coalesce(SUM(', builder(expr), '), 0)'
    def AVG(builder, expr, distinct=False):
        return distinct and 'AVG(DISTINCT ' or 'AVG(', builder(expr), ')'
    UPPER = make_unary_func('upper')
    LOWER = make_unary_func('lower')
    LENGTH = make_unary_func('length')
    ABS = make_unary_func('abs')
    def COALESCE(builder, *args):
        if len(args) < 2: assert False
        return 'coalesce(', join(', ', map(builder, args)), ')'
    def MIN(builder, *args):
        if len(args) == 0: assert False
        elif len(args) == 1: fname = 'MIN'
        else: fname = 'least'
        return fname, '(',  join(', ', map(builder, args)), ')'
    def MAX(builder, *args):
        if len(args) == 0: assert False
        elif len(args) == 1: fname = 'MAX'
        else: fname = 'greatest'
        return fname, '(',  join(', ', map(builder, args)), ')'
    def SUBSTR(builder, expr, start, len=None):
        if len is None: return 'substr(', builder(expr), ', ', builder(start), ')'
        return 'substr(', builder(expr), ', ', builder(start), ', ', builder(len), ')'
    def CASE(builder, expr, cases, default=None):
        result = [ 'case' ]
        if expr is not None:
            result.append(' ')
            result.extend(builder(expr))
        for condition, expr in cases:
            result.extend((' when ', builder(condition), ' then ', builder(expr)))
        if default is not None:
            result.extend((' else ', builder(default)))
        result.append(' end')
        return result
    def TRIM(builder, expr, chars=None):
        if chars is None: return 'trim(', builder(expr), ')'
        return 'trim(', builder(expr), ', ', builder(chars), ')'
    def LTRIM(builder, expr, chars=None):
        if chars is None: return 'ltrim(', builder(expr), ')'
        return 'ltrim(', builder(expr), ', ', builder(chars), ')'
    def RTRIM(builder, expr, chars=None):
        if chars is None: return 'rtrim(', builder(expr), ')'
        return 'rtrim(', builder(expr), ', ', builder(chars), ')'
    def TO_INT(builder, expr):
        return 'CAST(', builder(expr), ' AS integer)'
    def TODAY(builder):
        return 'CURRENT_DATE'
    def NOW(builder):
        return 'CURRENT_TIMESTAMP'
    def DATE(builder, expr):
        return 'DATE(', builder(expr) ,')'
    def YEAR(builder, expr):
        return 'EXTRACT(YEAR FROM ', builder(expr), ')'
    def MONTH(builder, expr):
        return 'EXTRACT(MONTH FROM ', builder(expr), ')'
    def DAY(builder, expr):
        return 'EXTRACT(DAY FROM ', builder(expr), ')'
    def HOUR(builder, expr):
        return 'EXTRACT(HOUR FROM ', builder(expr), ')'
    def MINUTE(builder, expr):
        return 'EXTRACT(MINUTE FROM ', builder(expr), ')'
    def SECOND(builder, expr):
        return 'EXTRACT(SECOND FROM ', builder(expr), ')'
    def RANDOM(builder):
        return 'RAND()'

########NEW FILE########
__FILENAME__ = sqlsymbols
symbols = [ 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'SELECT_FOR_UPDATE',
            'FROM', 'INNER_JOIN', 'LEFT_JOIN', 'WHERE', 'GROUP_BY', 'HAVING',
            'UNION', 'INTERSECT', 'EXCEPT',
            'ORDER_BY', 'LIMIT', 'ASC', 'DESC',
            'DISTINCT', 'ALL', 'AGGREGATES', 'AS',
            'COUNT', 'SUM', 'MIN', 'MAX', 'AVG',
            'TABLE', 'COLUMN', 'PARAM', 'VALUE', 'AND', 'OR', 'NOT',
            'EQ', 'NE', 'LT', 'LE', 'GT', 'GE', 'IS_NULL', 'IS_NOT_NULL',
            'LIKE', 'NOT_LIKE', 'BETWEEN', 'NOT_BETWEEN',
            'IN', 'NOT_IN', 'EXISTS', 'NOT_EXISTS', 'ROW',
            'ADD', 'SUB', 'MUL', 'DIV', 'POW', 'NEG', 'ABS',
            'UPPER', 'LOWER', 'CONCAT', 'STRIN', 'LIKE', 'SUBSTR', 'LENGTH', 'TRIM', 'LTRIM', 'RTRIM',
            'CASE', 'COALESCE',
            'TO_INT', 'RANDOM',
            'DATE', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'TODAY', 'NOW' ]

globals().update((s, s) for s in symbols)

########NEW FILE########
__FILENAME__ = sqltranslation
import types, sys, re
from itertools import izip, count
from types import NoneType
from compiler import ast
from decimal import Decimal
from datetime import date, datetime
from random import random
from cPickle import loads, dumps
from copy import deepcopy
from functools import update_wrapper

from pony import options
from pony.utils import avg, distinct, is_ident, throw, concat
from pony.orm.asttranslation import ASTTranslator, ast2src, TranslationError
from pony.orm.ormtypes import \
    string_types, numeric_types, comparable_types, SetType, FuncType, MethodType, \
    get_normalized_type_of, normalize_type, coerce_types, are_comparable_types
from pony.orm import core
from pony.orm.core import EntityMeta, Set, JOIN, OptimizationFailed, Attribute, DescWrapper

def check_comparable(left_monad, right_monad, op='=='):
    t1, t2 = left_monad.type, right_monad.type
    if t1 == 'METHOD': raise_forgot_parentheses(left_monad)
    if t2 == 'METHOD': raise_forgot_parentheses(right_monad)
    if not are_comparable_types(t1, t2, op):
        if op in ('in', 'not in') and isinstance(t2, SetType): t2 = t2.item_type
        throw(IncomparableTypesError, t1, t2)

class IncomparableTypesError(TypeError):
    def __init__(exc, type1, type2):
        msg = 'Incomparable types %r and %r in expression: {EXPR}' % (type2str(type1), type2str(type2))
        TypeError.__init__(exc, msg)
        exc.type1 = type1
        exc.type2 = type2

def sqland(items):
    if not items: return []
    if len(items) == 1: return items[0]
    result = [ 'AND' ]
    for item in items:
        if item[0] == 'AND': result.extend(item[1:])
        else: result.append(item)
    return result

def sqlor(items):
    if not items: return []
    if len(items) == 1: return items[0]
    result = [ 'OR' ]
    for item in items:
        if item[0] == 'OR': result.extend(item[1:])
        else: result.append(item)
    return result

def join_tables(alias1, alias2, columns1, columns2):
    assert len(columns1) == len(columns2)
    return sqland([ [ 'EQ', [ 'COLUMN', alias1, c1 ], [ 'COLUMN', alias2, c2 ] ] for c1, c2 in izip(columns1, columns2) ])

def type2str(t):
    if type(t) is tuple: return 'list'
    if type(t) is SetType: return 'Set of ' + type2str(t.item_type)
    try: return t.__name__
    except: return str(t)

class SQLTranslator(ASTTranslator):
    dialect = None
    row_value_syntax = True

    def default_post(translator, node):
        throw(NotImplementedError)  # pragma: no cover

    def dispatch(translator, node):
        if hasattr(node, 'monad'): return  # monad already assigned somehow
        if not getattr(node, 'external', False) or getattr(node, 'constant', False):
            return ASTTranslator.dispatch(translator, node)  # default route
        varkey = translator.filter_num, node.src
        t = translator.vartypes[varkey]
        tt = type(t)
        if t is NoneType:
            monad = translator.ConstMonad.new(translator, None)
        elif tt is SetType:
            if isinstance(t.item_type, EntityMeta):
                monad = translator.EntityMonad(translator, t.item_type)
            else: throw(NotImplementedError)  # pragma: no cover
        elif tt is FuncType:
            func = t.func
            if func not in translator.special_functions:
                throw(TypeError, 'Function %r cannot be used inside query' % func.__name__)
            func_monad_class = special_functions[func]
            monad = func_monad_class(translator)
        elif tt is MethodType:
            obj, func = t.obj, t.func
            if not isinstance(obj, EntityMeta): throw(NotImplementedError)
            entity_monad = translator.EntityMonad(translator, obj)
            if obj.__class__.__dict__.get(func.__name__) is not func: throw(NotImplementedError)
            monad = translator.MethodMonad(translator, entity_monad, func.__name__)
        elif isinstance(node, ast.Name) and node.name in ('True', 'False'):
            value = node.name == 'True' and True or False
            monad = translator.ConstMonad.new(translator, value)
        elif tt is tuple:
            params = []
            for i, item_type in enumerate(t):
                if item_type is NoneType:
                    throw(TypeError, 'Expression %r should not contain None values' % node.src)
                param = ParamMonad.new(translator, item_type, (varkey, i, None))
                params.append(param)
            monad = translator.ListMonad(translator, params)
        else:
            monad = translator.ParamMonad.new(translator, t, (varkey, None, None))
        node.monad = monad

    def call(translator, method, node):
        try: monad = method(node)
        except Exception:
            try:
                exc_class, exc, tb = sys.exc_info()
                if not exc.args: exc.args = (ast2src(node),)
                else:
                    msg = exc.args[0]
                    if isinstance(msg, basestring) and '{EXPR}' in msg:
                        msg = msg.replace('{EXPR}', ast2src(node))
                        exc.args = (msg,) + exc.args[1:]
                raise exc_class, exc, tb
            finally: del tb
        else:
            if monad is None: return
            node.monad = monad
            monad.node = node
            if not hasattr(monad, 'aggregated'):
                for child in node.getChildNodes():
                    m = getattr(child, 'monad', None)
                    if m and getattr(m, 'aggregated', False):
                        monad.aggregated = True
                        break
                else: monad.aggregated = False
            if not hasattr(monad, 'nogroup'):
                for child in node.getChildNodes():
                    m = getattr(child, 'monad', None)
                    if m and getattr(m, 'nogroup', False):
                        monad.nogroup = True
                        break
                else: monad.nogroup = False
            if monad.aggregated:
                translator.aggregated = True
                if monad.nogroup:
                    if isinstance(monad, ListMonad): pass
                    elif isinstance(monad, AndMonad): pass
                    else: throw(TranslationError, 'Too complex aggregation, expressions cannot be combined: %s' % ast2src(node))
            return monad

    def __init__(translator, tree, extractors, vartypes, parent_translator=None, left_join=False, optimize=None):
        assert isinstance(tree, ast.GenExprInner), tree
        ASTTranslator.__init__(translator, tree)
        translator.database = None
        translator.argnames = None
        translator.filter_num = 0
        translator.extractors = extractors
        translator.vartypes = vartypes
        translator.parent = parent_translator
        translator.left_join = left_join
        translator.optimize = optimize
        translator.from_optimized = False
        translator.optimization_failed = False
        if not parent_translator: subquery = Subquery(left_join=left_join)
        else: subquery = Subquery(parent_translator.subquery, left_join=left_join)
        translator.subquery = subquery
        tablerefs = subquery.tablerefs
        translator.distinct = False
        translator.conditions = subquery.conditions
        translator.having_conditions = []
        translator.order = []
        translator.aggregated = False if not optimize else True
        translator.inside_expr = False
        translator.inside_not = False
        translator.hint_join = False
        translator.query_result_is_cacheable = True
        translator.aggregated_subquery_paths = set()
        for i, qual in enumerate(tree.quals):
            assign = qual.assign
            if not isinstance(assign, ast.AssName): throw(NotImplementedError, ast2src(assign))
            if assign.flags != 'OP_ASSIGN': throw(TypeError, ast2src(assign))

            name = assign.name
            if name in tablerefs: throw(TranslationError, 'Duplicate name: %r' % name)
            if name.startswith('__'): throw(TranslationError, 'Illegal name: %r' % name)

            node = qual.iter
            monad = getattr(node, 'monad', None)
            src = getattr(node, 'src', None)
            if monad:  # Lambda was encountered inside generator
                assert isinstance(monad, EntityMonad)
                entity = monad.type.item_type
                tablerefs[name] = TableRef(subquery, name, entity)
            elif src:
                iterable = translator.vartypes[0, src]
                if not isinstance(iterable, SetType): throw(TranslationError,
                    'Inside declarative query, iterator must be entity. '
                    'Got: for %s in %s' % (name, ast2src(qual.iter)))
                entity = iterable.item_type
                if not isinstance(entity, EntityMeta):
                    throw(TranslationError, 'for %s in %s' % (name, ast2src(qual.iter)))
                if i > 0:
                    if translator.left_join: throw(TranslationError,
                        'Collection expected inside left join query. '
                        'Got: for %s in %s' % (name, ast2src(qual.iter)))
                    translator.distinct = True
                tablerefs[name] = TableRef(subquery, name, entity)
            else:
                attr_names = []
                while isinstance(node, ast.Getattr):
                    attr_names.append(node.attrname)
                    node = node.expr
                if not isinstance(node, ast.Name) or not attr_names:
                    throw(TranslationError, 'for %s in %s' % (name, ast2src(qual.iter)))
                node_name = node.name
                attr_names.reverse()
                name_path = node_name
                parent_tableref = subquery.get_tableref(node_name)
                if parent_tableref is None: throw(TranslationError, "Name %r must be defined in query" % node_name)
                parent_entity = parent_tableref.entity
                last_index = len(attr_names) - 1
                for j, attrname in enumerate(attr_names):
                    attr = parent_entity._adict_.get(attrname)
                    if attr is None: throw(AttributeError, attrname)
                    entity = attr.py_type
                    if not isinstance(entity, EntityMeta):
                        throw(NotImplementedError, 'for %s in %s' % (name, ast2src(qual.iter)))
                    can_affect_distinct = None
                    if attr.is_collection:
                        if not isinstance(attr, Set): throw(NotImplementedError, ast2src(qual.iter))
                        reverse = attr.reverse
                        if reverse.is_collection:
                            if not isinstance(reverse, Set): throw(NotImplementedError, ast2src(qual.iter))
                            translator.distinct = True
                        elif parent_tableref.alias != tree.quals[i-1].assign.name:
                            translator.distinct = True
                        else: can_affect_distinct = True
                    if j == last_index: name_path = name
                    else: name_path += '-' + attr.name
                    tableref = JoinedTableRef(subquery, name_path, parent_tableref, attr)
                    if can_affect_distinct is not None:
                        tableref.can_affect_distinct = can_affect_distinct
                    tablerefs[name_path] = tableref
                    parent_tableref = tableref
                    parent_entity = entity

            database = entity._database_
            assert database.schema is not None
            if translator.database is None: translator.database = database
            elif translator.database is not database: throw(TranslationError,
                'All entities in a query must belong to the same database')

            for if_ in qual.ifs:
                assert isinstance(if_, ast.GenExprIf)
                translator.dispatch(if_)
                if isinstance(if_.monad, translator.AndMonad): cond_monads = if_.monad.operands
                else: cond_monads = [ if_.monad ]
                for m in cond_monads:
                    if not m.aggregated: translator.conditions.extend(m.getsql())
                    else: translator.having_conditions.extend(m.getsql())

        translator.inside_expr = True
        translator.dispatch(tree.expr)
        assert not translator.hint_join
        assert not translator.inside_not
        monad = tree.expr.monad
        if isinstance(monad, translator.ParamMonad): throw(TranslationError,
            "External parameter '%s' cannot be used as query result" % ast2src(tree.expr))
        translator.groupby_monads = None
        expr_type = monad.type
        if isinstance(expr_type, SetType): expr_type = expr_type.item_type
        if isinstance(expr_type, EntityMeta):
            monad.orderby_columns = range(1, len(expr_type._pk_columns_)+1)
            if monad.aggregated: throw(TranslationError)
            if translator.aggregated: translator.groupby_monads = [ monad ]
            else: translator.distinct |= monad.requires_distinct()
            if isinstance(monad, translator.ObjectMixin):
                entity = monad.type
                tableref = monad.tableref
            elif isinstance(monad, translator.AttrSetMonad):
                entity = monad.type.item_type
                tableref = monad.make_tableref(translator.subquery)
            else: assert False  # pragma: no cover
            translator.tableref = tableref
            pk_only = parent_translator is not None or translator.aggregated
            alias, pk_columns = tableref.make_join(pk_only=pk_only)
            translator.alias = alias
            translator.expr_type = entity
            translator.expr_columns = [ [ 'COLUMN', alias, column ] for column in pk_columns ]
            translator.row_layout = None
            translator.col_names = [ attr.name for attr in entity._attrs_
                                               if not attr.is_collection and not attr.lazy ]
        else:
            translator.alias = None
            if isinstance(monad, translator.ListMonad):
                expr_monads = monad.items
                translator.expr_type = tuple(m.type for m in expr_monads)  # ?????
                expr_columns = []
                for m in expr_monads: expr_columns.extend(m.getsql())
                translator.expr_columns = expr_columns
            else:
                expr_monads = [ monad ]
                translator.expr_type = monad.type
                translator.expr_columns = monad.getsql()
            if translator.aggregated:
                translator.groupby_monads = [ m for m in expr_monads if not m.aggregated and not m.nogroup ]
            else:
                expr_set = set()
                for m in expr_monads:
                    if isinstance(m, ObjectIterMonad):
                        expr_set.add(m.tableref.name_path)
                    elif isinstance(m, AttrMonad) and isinstance(m.parent, ObjectIterMonad):
                        expr_set.add((m.parent.tableref.name_path, m.attr))
                for tr in tablerefs.values():
                    if not tr.can_affect_distinct: continue
                    if tr.name_path in expr_set: continue
                    for attr in tr.entity._pk_attrs_:
                        if (tr.name_path, attr) not in expr_set: break
                    else: continue
                    translator.distinct = True
                    break
            row_layout = []
            offset = 0
            provider = translator.database.provider
            for m in expr_monads:
                expr_type = m.type
                if isinstance(expr_type, SetType): expr_type = expr_type.item_type
                if isinstance(expr_type, EntityMeta):
                    next_offset = offset + len(expr_type._pk_columns_)
                    def func(values, constructor=expr_type._get_by_raw_pkval_):
                        if None in values: return None
                        return constructor(values)
                    row_layout.append((func, slice(offset, next_offset), ast2src(m.node)))
                    m.orderby_columns = range(offset+1, next_offset+1)
                    offset = next_offset
                else:
                    converter = provider.get_converter_by_py_type(expr_type)
                    def func(value, sql2py=converter.sql2py):
                        if value is None: return None
                        return sql2py(value)
                    row_layout.append((func, offset, ast2src(m.node)))
                    m.orderby_columns = (offset+1,)
                    offset += 1
            translator.row_layout = row_layout
            translator.col_names = [ src for func, slice_or_offset, src in translator.row_layout ]
    def shallow_copy_of_subquery_ast(translator, move_outer_conditions=True):
        subquery_ast, attr_offsets = translator.construct_sql_ast(distinct=False, is_not_null_checks=True)
        assert attr_offsets is None
        assert len(subquery_ast) >= 3 and subquery_ast[0] == 'SELECT'

        select_ast = subquery_ast[1][:]
        assert select_ast[0] == 'ALL'

        from_ast = subquery_ast[2][:]
        assert from_ast[0] == 'FROM'

        if len(subquery_ast) == 3:
            where_ast = [ 'WHERE' ]
            other_ast = []
        elif subquery_ast[3][0] != 'WHERE':
            where_ast = [ 'WHERE' ]
            other_ast = subquery_ast[3:]
        else:
            where_ast = subquery_ast[3][:]
            other_ast = subquery_ast[4:]

        if move_outer_conditions and len(from_ast[1]) == 4:
            outer_conditions = from_ast[1][-1]
            from_ast[1] = from_ast[1][:-1]
            if outer_conditions[0] == 'AND': where_ast[1:1] = outer_conditions[1:]
            else: where_ast.insert(1, outer_conditions)

        return [ 'SELECT', select_ast, from_ast, where_ast ] + other_ast
    def can_be_optimized(translator):
        if translator.groupby_monads: return False
        if len(translator.aggregated_subquery_paths) != 1: return False
        return iter(translator.aggregated_subquery_paths).next()
    def construct_sql_ast(translator, range=None, distinct=None, aggr_func_name=None, for_update=False, nowait=False,
                          is_not_null_checks=False):
        attr_offsets = None
        if distinct is None: distinct = translator.distinct
        ast_transformer = lambda ast: ast
        if for_update:
            sql_ast = [ 'SELECT_FOR_UPDATE', nowait ]
            translator.query_result_is_cacheable = False
        else: sql_ast = [ 'SELECT' ]
        if aggr_func_name:
            expr_type = translator.expr_type
            if not isinstance(expr_type, EntityMeta):
                if aggr_func_name in ('SUM', 'AVG') and expr_type not in numeric_types:
                    throw(TranslationError, '%r is valid for numeric attributes only' % aggr_func_name.lower())
                assert len(translator.expr_columns) == 1
                column_ast = translator.expr_columns[0]
            elif aggr_func_name is not 'COUNT': throw(TranslationError,
                'Attribute should be specified for %r aggregate function' % aggr_func_name.lower())
            aggr_ast = None
            if aggr_func_name == 'COUNT':
                if isinstance(expr_type, (tuple, EntityMeta)):
                    if translator.distinct:
                        select_ast = [ 'DISTINCT' ] + translator.expr_columns  # aggr_ast remains to be None
                        def ast_transformer(ast):
                            return [ 'SELECT', [ 'AGGREGATES', [ 'COUNT', 'ALL' ] ], [ 'FROM', [ 't', 'SELECT', ast[1:] ] ] ]
                    else: aggr_ast = [ 'COUNT', 'ALL' ]
                else: aggr_ast = [ 'COUNT', 'DISTINCT', column_ast ]
            else: aggr_ast = [ aggr_func_name, column_ast ]
            if aggr_ast: select_ast = [ 'AGGREGATES', aggr_ast ]
        elif isinstance(translator.expr_type, EntityMeta) and not translator.parent \
             and not translator.aggregated and not translator.optimize:
            select_ast, attr_offsets = translator.expr_type._construct_select_clause_(translator.alias, distinct)
        else: select_ast = [ distinct and 'DISTINCT' or 'ALL' ] + translator.expr_columns
        sql_ast.append(select_ast)
        sql_ast.append(translator.subquery.from_ast)

        conditions = translator.conditions[:]
        if is_not_null_checks:
            expr_monad = translator.tree.expr.monad
            if isinstance(expr_monad, translator.ListMonad):
                expr_monads = expr_monad.items
            else: expr_monads = [ expr_monad ]
            for monad in expr_monads:
                if isinstance(monad, translator.ObjectIterMonad): pass
                elif isinstance(monad, translator.AttrMonad) and not monad.attr.nullable: pass
                else: conditions.extend([ 'IS_NOT_NULL', column_ast ] for column_ast in monad.getsql())
        if conditions:
            sql_ast.append([ 'WHERE' ] + conditions)

        if translator.groupby_monads:
            group_by = [ 'GROUP_BY' ]
            for m in translator.groupby_monads: group_by.extend(m.getsql())
            sql_ast.append(group_by)
        else: group_by = None

        if translator.having_conditions:
            if not group_by: throw(TranslationError,
                'In order to use aggregated functions such as SUM(), COUNT(), etc., '
                'query must have grouping columns (i.e. resulting non-aggregated values)')
            sql_ast.append([ 'HAVING' ] + translator.having_conditions)

        if translator.order: sql_ast.append([ 'ORDER_BY' ] + translator.order)

        if range:
            start, stop = range
            limit = stop - start
            offset = start
            assert limit is not None
            limit_section = [ 'LIMIT', [ 'VALUE', limit ]]
            if offset: limit_section.append([ 'VALUE', offset ])
            sql_ast = sql_ast + [ limit_section ]

        sql_ast = ast_transformer(sql_ast)
        return sql_ast, attr_offsets
    def without_order(translator):
        translator = deepcopy(translator)
        translator.order = []
        return translator
    def order_by_numbers(translator, numbers):
        if 0 in numbers: throw(ValueError, 'Numeric arguments of order_by() method must be non-zero')
        translator = deepcopy(translator)
        order = translator.order = translator.order[:]  # only order will be changed
        expr_monad = translator.tree.expr.monad
        if isinstance(expr_monad, translator.ListMonad): monads = expr_monad.items
        else: monads = (expr_monad,)
        new_order = []
        for i in numbers:
            try: monad = monads[abs(i)-1]
            except IndexError:
                if len(monads) > 1: throw(IndexError,
                    "Invalid index of order_by() method: %d "
                    "(query result is list of tuples with only %d elements in each)" % (i, len(monads)))
                else: throw(IndexError,
                    "Invalid index of order_by() method: %d "
                    "(query result is single list of elements and has only one 'column')" % i)
            for pos in monad.orderby_columns:
                new_order.append(i < 0 and [ 'DESC', [ 'VALUE', pos ] ] or [ 'VALUE', pos ])
        order[:0] = new_order
        return translator
    def order_by_attributes(translator, attrs):
        entity = translator.expr_type
        if not isinstance(entity, EntityMeta): throw(NotImplementedError,
            'Ordering by attributes is limited to queries which return simple list of objects. '
            'Try use other forms of ordering (by tuple element numbers or by full-blown lambda expr).')
        translator = deepcopy(translator)
        order = translator.order = translator.order[:]  # only order will be changed
        alias = translator.alias
        new_order = []
        for x in attrs:
            if isinstance(x, DescWrapper):
                attr = x.attr
                desc_wrapper = lambda column: [ 'DESC', column ]
            elif isinstance(x, Attribute):
                attr = x
                desc_wrapper = lambda column: column
            else: assert False, x  # pragma: no cover
            if entity._adict_.get(attr.name) is not attr: throw(TypeError,
                'Attribute %s does not belong to Entity %s' % (attr, entity.__name__))
            if attr.is_collection: throw(TypeError,
                'Collection attribute %s cannot be used for ordering' % attr)
            for column in attr.columns:
                new_order.append(desc_wrapper([ 'COLUMN', alias, column]))
        order[:0] = new_order
        return translator
    def apply_kwfilters(translator, filterattrs):
        entity = translator.expr_type
        if not isinstance(entity, EntityMeta):
            throw(TypeError, 'Keyword arguments are not allowed when query result is not entity objects')
        translator = deepcopy(translator)
        expr_monad = translator.tree.expr.monad
        monads = []
        none_monad = translator.NoneMonad(translator)
        for attr, id, is_none in filterattrs:
            attr_monad = expr_monad.getattr(attr.name)
            if is_none: monads.append(CmpMonad('is', attr_monad, none_monad))
            else:
                param_monad = translator.ParamMonad.new(translator, attr.py_type, (id, None, None))
                monads.append(CmpMonad('==', attr_monad, param_monad))
        for m in monads: translator.conditions.extend(m.getsql())
        return translator
    def apply_lambda(translator, filter_num, order_by, func_ast, argnames, extractors, vartypes):
        translator = deepcopy(translator)
        pickled_func_ast = dumps(func_ast, 2)
        func_ast = loads(pickled_func_ast)  # func_ast = deepcopy(func_ast)
        translator.filter_num = filter_num
        translator.extractors.update(extractors)
        translator.vartypes.update(vartypes)
        translator.argnames = list(argnames)
        translator.dispatch(func_ast)
        if isinstance(func_ast, ast.Tuple): nodes = func_ast.nodes
        else: nodes = (func_ast,)
        if order_by:
            new_order = []
            for node in nodes:
                if isinstance(node.monad, translator.SetMixin):
                    t = node.monad.type.item_type
                    if isinstance(type(t), type): t = t.__name__
                    throw(TranslationError, 'Set of %s (%s) cannot be used for ordering'
                                            % (t, ast2src(node)))
                new_order.extend(node.monad.getsql())
            translator.order[:0] = new_order
        else:
            for node in nodes:
                monad = node.monad
                if isinstance(monad, translator.AndMonad): cond_monads = monad.operands
                else: cond_monads = [ monad ]
                for m in cond_monads:
                    if not m.aggregated: translator.conditions.extend(m.getsql())
                    else: translator.having_conditions.extend(m.getsql())
        return translator
    def preGenExpr(translator, node):
        inner_tree = node.code
        subtranslator = translator.__class__(inner_tree, translator.extractors, translator.vartypes, translator)
        return translator.QuerySetMonad(translator, subtranslator)
    def postGenExprIf(translator, node):
        monad = node.test.monad
        if monad.type is not bool: monad = monad.nonzero()
        return monad
    def preCompare(translator, node):
        monads = []
        ops = node.ops
        left = node.expr
        translator.dispatch(left)
        inside_not = translator.inside_not
        # op: '<' | '>' | '=' | '>=' | '<=' | '<>' | '!=' | '=='
        #         | 'in' | 'not in' | 'is' | 'is not'
        for op, right in node.ops:
            translator.inside_not = inside_not
            if op == 'not in': translator.inside_not = not inside_not
            translator.dispatch(right)
            if op.endswith('in'): monad = right.monad.contains(left.monad, op == 'not in')
            else: monad = left.monad.cmp(op, right.monad)
            if not hasattr(monad, 'aggregated'):
                monad.aggregated = getattr(left.monad, 'aggregated', False) or getattr(right.monad, 'aggregated', False)
            if not hasattr(monad, 'nogroup'):
                monad.nogroup = getattr(left.monad, 'nogroup', False) or getattr(right.monad, 'nogroup', False)
            if monad.aggregated and monad.nogroup: throw(TranslationError,
                'Too complex aggregation, expressions cannot be combined: {EXPR}')
            monads.append(monad)
            left = right
        translator.inside_not = inside_not
        if len(monads) == 1: return monads[0]
        return translator.AndMonad(monads)
    def postConst(translator, node):
        value = node.value
        if type(value) is not tuple:
            return translator.ConstMonad.new(translator, value)
        else:
            return translator.ListMonad(translator, [ translator.ConstMonad.new(translator, item) for item in value ])
    def postList(translator, node):
        return translator.ListMonad(translator, [ item.monad for item in node.nodes ])
    def postTuple(translator, node):
        return translator.ListMonad(translator, [ item.monad for item in node.nodes ])
    def postName(translator, node):
        name = node.name
        argnames = translator.argnames
        if translator.argnames and name in translator.argnames:
            i = translator.argnames.index(name)
            expr_monad = translator.tree.expr.monad
            if isinstance(expr_monad, translator.ListMonad):
                return expr_monad.items[i]
            assert i == 0
            return expr_monad
        tableref = translator.subquery.get_tableref(name)
        if tableref is not None:
            return translator.ObjectIterMonad(translator, tableref, tableref.entity)
        elif name == 'random':
            translator.query_result_is_cacheable = False
            return translator.RandomMonad(translator)
        elif name == 'count':
            return translator.FuncCountMonad(translator)
        else: assert False
    def postAdd(translator, node):
        return node.left.monad + node.right.monad
    def postSub(translator, node):
        return node.left.monad - node.right.monad
    def postMul(translator, node):
        return node.left.monad * node.right.monad
    def postDiv(translator, node):
        return node.left.monad / node.right.monad
    def postPower(translator, node):
        return node.left.monad ** node.right.monad
    def postUnarySub(translator, node):
        return -node.expr.monad
    def postGetattr(translator, node):
        return node.expr.monad.getattr(node.attrname)
    def postAnd(translator, node):
        return translator.AndMonad([ subnode.monad for subnode in node.nodes ])
    def postOr(translator, node):
        return translator.OrMonad([ subnode.monad for subnode in node.nodes ])
    def preNot(translator, node):
        translator.inside_not = not translator.inside_not
    def postNot(translator, node):
        translator.inside_not = not translator.inside_not
        return node.expr.monad.negate()
    def preCallFunc(translator, node):
        if node.star_args is not None: throw(NotImplementedError, '*%s is not supported' % ast2src(node.star_args))
        if node.dstar_args is not None: throw(NotImplementedError, '**%s is not supported' % ast2src(node.dstar_args))
        if not isinstance(node.node, (ast.Name, ast.Getattr)): throw(NotImplementedError)
        if len(node.args) > 1: return
        if not node.args: return
        arg = node.args[0]
        if isinstance(arg, ast.GenExpr):
            translator.dispatch(node.node)
            func_monad = node.node.monad
            translator.dispatch(arg)
            query_set_monad = arg.monad
            return func_monad(query_set_monad)
        if not isinstance(arg, ast.Lambda): return
        lambda_expr = arg
        translator.dispatch(node.node)
        method_monad = node.node.monad
        if not isinstance(method_monad, MethodMonad): throw(NotImplementedError)
        entity_monad = method_monad.parent
        if not isinstance(entity_monad, EntityMonad): throw(NotImplementedError)
        entity = entity_monad.type.item_type
        if method_monad.attrname != 'select': throw(TypeError)
        if len(lambda_expr.argnames) != 1: throw(TypeError)
        if lambda_expr.varargs: throw(TypeError)
        if lambda_expr.kwargs: throw(TypeError)
        if lambda_expr.defaults: throw(TypeError)
        iter_name = lambda_expr.argnames[0]
        cond_expr = lambda_expr.code
        if_expr = ast.GenExprIf(cond_expr)
        name_ast = ast.Name(entity.__name__)
        name_ast.monad = entity_monad
        for_expr = ast.GenExprFor(ast.AssName(iter_name, 'OP_ASSIGN'), name_ast, [ if_expr ])
        inner_expr = ast.GenExprInner(ast.Name(iter_name), [ for_expr ])
        subtranslator = translator.__class__(inner_expr, translator.extractors, translator.vartypes, translator)
        return translator.QuerySetMonad(translator, subtranslator)
    def postCallFunc(translator, node):
        args = []
        kwargs = {}
        for arg in node.args:
            if isinstance(arg, ast.Keyword):
                kwargs[arg.name] = arg.expr.monad
            else: args.append(arg.monad)
        func_monad = node.node.monad
        return func_monad(*args, **kwargs)
    def postKeyword(translator, node):
        pass  # this node will be processed by postCallFunc
    def postSubscript(translator, node):
        assert node.flags == 'OP_APPLY'
        assert isinstance(node.subs, list)
        if len(node.subs) > 1:
            for x in node.subs:
                if isinstance(x, ast.Sliceobj): throw(TypeError)
            key = translator.ListMonad(translator, [ item.monad for item in node.subs ])
            return node.expr.monad[key]
        sub = node.subs[0]
        if isinstance(sub, ast.Sliceobj):
            start, stop, step = (sub.nodes+[None])[:3]
            return node.expr.monad[start:stop:step]
        else: return node.expr.monad[sub.monad]
    def postSlice(translator, node):
        assert node.flags == 'OP_APPLY'
        expr_monad = node.expr.monad
        upper = node.upper
        if upper is not None: upper = upper.monad
        lower = node.lower
        if lower is not None: lower = lower.monad
        return expr_monad[lower:upper]
    def postSliceobj(translator, node):
        pass
    def postIfExp(translator, node):
        test_monad, then_monad, else_monad = node.test.monad, node.then.monad, node.else_.monad
        if test_monad.type is not bool: test_monad = test_monad.nonzero()
        result_type = coerce_types(then_monad.type, else_monad.type)
        test_sql, then_sql, else_sql = test_monad.getsql()[0], then_monad.getsql(), else_monad.getsql()
        if len(then_sql) == 1: then_sql, else_sql = then_sql[0], else_sql[0]
        elif not translator.row_value_syntax: throw(NotImplementedError)
        else: then_sql, else_sql = [ 'ROW' ] + then_sql, [ 'ROW' ] + else_sql
        expr = [ 'CASE', None, [ [ test_sql, then_sql ] ], else_sql ]
        result = translator.ExprMonad.new(translator, result_type, expr)
        result.aggregated = test_monad.aggregated or then_monad.aggregated or else_monad.aggregated
        return result

def coerce_monads(m1, m2):
    result_type = coerce_types(m1.type, m2.type)
    if result_type in numeric_types and bool in (m1.type, m2.type) and result_type is not bool:
        translator = m1.translator
        if translator.dialect == 'PostgreSQL':
            if m1.type is bool:
                new_m1 = NumericExprMonad(translator, int, [ 'TO_INT', m1.getsql()[0] ])
                new_m1.aggregated = m1.aggregated
                m1 = new_m1
            if m2.type is bool:
                new_m2 = NumericExprMonad(translator, int, [ 'TO_INT', m2.getsql()[0] ])
                new_m2.aggregated = m2.aggregated
                m2 = new_m2
    return result_type, m1, m2                

max_alias_length = 30

class Subquery(object):
    def __init__(subquery, parent_subquery=None, left_join=False):
        subquery.parent_subquery = parent_subquery
        subquery.left_join = left_join
        subquery.from_ast = [ 'LEFT_JOIN' if left_join else 'FROM' ]
        subquery.conditions = []
        subquery.tablerefs = {}
        if parent_subquery is None:
            subquery.alias_counters = {}
            subquery.expr_counter = count(1)
        else:
            subquery.alias_counters = parent_subquery.alias_counters.copy()
            subquery.expr_counter = parent_subquery.expr_counter
    def get_tableref(subquery, name_path):
        tableref = subquery.tablerefs.get(name_path)
        if tableref is not None: return tableref
        if subquery.parent_subquery:
            return subquery.parent_subquery.get_tableref(name_path)
        return None
    __contains__ = get_tableref
    def add_tableref(subquery, name_path, parent_tableref, attr):
        tablerefs = subquery.tablerefs
        assert name_path not in tablerefs
        tableref = JoinedTableRef(subquery, name_path, parent_tableref, attr)
        tablerefs[name_path] = tableref
        return tableref
    def get_short_alias(subquery, name_path, entity_name):
        if name_path:
            if is_ident(name_path): return name_path
            if not options.SIMPLE_ALIASES and len(name_path) <= max_alias_length:
                return name_path
        name = entity_name[:max_alias_length-3].lower()
        i = subquery.alias_counters.setdefault(name, 0) + 1
        alias = '%s-%d' % (name, i)
        subquery.alias_counters[name] = i
        return alias

class TableRef(object):
    def __init__(tableref, subquery, name, entity):
        tableref.subquery = subquery
        tableref.alias = tableref.name_path = name
        tableref.entity = entity
        tableref.joined = False
        tableref.can_affect_distinct = True
        tableref.used_attrs = set()
    def make_join(tableref, pk_only=False):
        entity = tableref.entity
        if not tableref.joined:
            subquery = tableref.subquery
            subquery.from_ast.append([ tableref.alias, 'TABLE', entity._table_ ])
            if entity._discriminator_attr_:
                discr_criteria = entity._construct_discriminator_criteria_(tableref.alias)
                assert discr_criteria is not None
                subquery.conditions.append(discr_criteria)
            tableref.joined = True
        return tableref.alias, entity._pk_columns_

class JoinedTableRef(object):
    def __init__(tableref, subquery, name_path, parent_tableref, attr):
        tableref.subquery = subquery
        tableref.name_path = name_path
        tableref.alias = None
        tableref.optimized = None
        tableref.parent_tableref = parent_tableref
        tableref.attr = attr
        tableref.entity = attr.py_type
        assert isinstance(tableref.entity, EntityMeta)
        tableref.joined = False
        tableref.can_affect_distinct = False
        tableref.used_attrs = set()
    def make_join(tableref, pk_only=False):
        entity = tableref.entity
        pk_only = pk_only and not entity._discriminator_attr_
        if tableref.joined:
            if pk_only or not tableref.optimized:
                return tableref.alias, tableref.pk_columns
        subquery = tableref.subquery
        attr = tableref.attr
        parent_pk_only = attr.pk_offset is not None or attr.is_collection
        parent_alias, left_pk_columns = tableref.parent_tableref.make_join(parent_pk_only)
        left_entity = attr.entity
        pk_columns = entity._pk_columns_
        if not attr.is_collection:
            if not attr.columns:
                reverse = attr.reverse
                assert reverse.columns and not reverse.is_collection
                alias = subquery.get_short_alias(tableref.name_path, entity.__name__)
                join_cond = join_tables(parent_alias, alias, left_pk_columns, reverse.columns)
            else:
                if attr.pk_offset is not None:
                    offset = attr.pk_columns_offset
                    left_columns = left_pk_columns[offset:offset+len(attr.columns)]
                else: left_columns = attr.columns
                if pk_only:
                    tableref.alias = parent_alias
                    tableref.pk_columns = left_columns
                    tableref.optimized = True
                    tableref.joined = True
                    return parent_alias, left_columns
                alias = subquery.get_short_alias(tableref.name_path, entity.__name__)
                join_cond = join_tables(parent_alias, alias, left_columns, pk_columns)
            subquery.from_ast.append([ alias, 'TABLE', entity._table_, join_cond ])
        elif not attr.reverse.is_collection:
            alias = subquery.get_short_alias(tableref.name_path, entity.__name__)
            join_cond = join_tables(parent_alias, alias, left_pk_columns, attr.reverse.columns)
            subquery.from_ast.append([ alias, 'TABLE', entity._table_, join_cond ])
        else:
            right_m2m_columns = attr.symmetric and attr.reverse_columns or attr.columns
            if not tableref.joined:
                m2m_table = attr.table
                m2m_alias = subquery.get_short_alias(None, 't')
                reverse_columns = attr.symmetric and attr.columns or attr.reverse.columns
                m2m_join_cond = join_tables(parent_alias, m2m_alias, left_pk_columns, reverse_columns)
                subquery.from_ast.append([ m2m_alias, 'TABLE', m2m_table, m2m_join_cond ])
                if pk_only:
                    tableref.alias = m2m_alias
                    tableref.pk_columns = right_m2m_columns
                    tableref.optimized = True
                    tableref.joined = True
                    return m2m_alias, tableref.pk_columns
            elif tableref.optimized:
                assert not pk_only
                m2m_alias = tableref.alias
            alias = subquery.get_short_alias(tableref.name_path, entity.__name__)
            join_cond = join_tables(m2m_alias, alias, right_m2m_columns, pk_columns)
            subquery.from_ast.append([ alias, 'TABLE', entity._table_, join_cond ])
        if entity._discriminator_attr_:
            discr_criteria = entity._construct_discriminator_criteria_(alias)
            assert discr_criteria is not None
            subquery.conditions.insert(0, discr_criteria)
        tableref.alias = alias
        tableref.pk_columns = pk_columns
        tableref.optimized = False
        tableref.joined = True
        return tableref.alias, pk_columns

def wrap_monad_method(cls_name, func):
    overrider_name = '%s_%s' % (cls_name, func.__name__)
    def wrapper(monad, *args, **kwargs):
        method = getattr(monad.translator, overrider_name, func)
        return method(monad, *args, **kwargs)
    return update_wrapper(wrapper, func)

class MonadMeta(type):
    def __new__(meta, cls_name, bases, cls_dict):
        for name, func in cls_dict.items():
            if not isinstance(func, types.FunctionType): continue
            if name in ('__new__', '__init__'): continue
            cls_dict[name] = wrap_monad_method(cls_name, func)
        return super(MonadMeta, meta).__new__(meta, cls_name, bases, cls_dict)

class MonadMixin(object):
    __metaclass__ = MonadMeta

class Monad(object):
    __metaclass__ = MonadMeta
    def __init__(monad, translator, type):
        monad.translator = translator
        monad.type = type
        monad.mixin_init()
    def mixin_init(monad):
        pass
    def cmp(monad, op, monad2):
        return monad.translator.CmpMonad(op, monad, monad2)
    def contains(monad, item, not_in=False): throw(TypeError)
    def nonzero(monad): throw(TypeError)
    def negate(monad):
        return monad.translator.NotMonad(monad)
    def getattr(monad, attrname):
        try: property_method = getattr(monad, 'attr_' + attrname)
        except AttributeError:
            if not hasattr(monad, 'call_' + attrname):
                throw(AttributeError, '%r object has no attribute %r' % (type2str(monad.type), attrname))
            translator = monad.translator
            return translator.MethodMonad(translator, monad, attrname)
        return property_method()
    def len(monad): throw(TypeError)
    def count(monad):
        translator = monad.translator
        if monad.aggregated: throw(TranslationError, 'Aggregated functions cannot be nested. Got: {EXPR}')
        expr = monad.getsql()
        count_kind = 'DISTINCT'
        if monad.type is bool:
            expr = [ 'CASE', None, [ [ expr[0], [ 'VALUE', 1 ] ] ], [ 'VALUE', None ] ]
            count_kind = 'ALL'
        elif len(expr) == 1: expr = expr[0]
        elif translator.dialect == 'PostgreSQL':
            row = [ 'ROW' ] + expr
            expr = [ 'CASE', None, [ [ [ 'IS_NULL', row ], [ 'VALUE', None ] ] ], row ]
        # elif translator.dialect == 'PostgreSQL':  # another way
        #     alias, pk_columns = monad.tableref.make_join(pk_only=False)
        #     expr = [ 'COLUMN', alias, 'ctid' ]
        elif translator.dialect in ('SQLite', 'Oracle'):
            alias, pk_columns = monad.tableref.make_join(pk_only=False)
            expr = [ 'COLUMN', alias, 'ROWID' ]
        # elif translator.row_value_syntax == True:  # doesn't work in MySQL
        #     expr = ['ROW'] + expr
        else: throw(NotImplementedError,
                    '%s database provider does not support entities '
                    'with composite primary keys inside aggregate functions. Got: {EXPR}'
                    % translator.dialect)
        result = translator.ExprMonad.new(translator, int, [ 'COUNT', count_kind, expr ])
        result.aggregated = True
        return result
    def aggregate(monad, func_name):
        translator = monad.translator
        if monad.aggregated: throw(TranslationError, 'Aggregated functions cannot be nested. Got: {EXPR}')
        expr_type = monad.type
        # if isinstance(expr_type, SetType): expr_type = expr_type.item_type
        if func_name in ('SUM', 'AVG'):
            if expr_type not in numeric_types:
                throw(TypeError, "Function '%s' expects argument of numeric type, got %r in {EXPR}"
                                 % (func_name, type2str(expr_type)))
        elif func_name in ('MIN', 'MAX'):
            if expr_type not in comparable_types:
                throw(TypeError, "Function '%s' cannot be applied to type %r in {EXPR}"
                                 % (func_name, type2str(expr_type)))
        else: assert False  # pragma: no cover
        expr = monad.getsql()
        if len(expr) == 1: expr = expr[0]
        elif translator.row_value_syntax == True: expr = ['ROW'] + expr
        else: throw(NotImplementedError,
                    '%s database provider does not support entities '
                    'with composite primary keys inside aggregate functions. Got: {EXPR} '
                    '(you can suggest us how to write SQL for this query)'
                    % translator.dialect)
        if func_name == 'AVG': result_type = float
        else: result_type = expr_type
        aggr_ast = [ func_name, expr ]
        if getattr(monad, 'forced_distinct', False) and func_name in ('SUM', 'AVG'):
            aggr_ast.append(True)
        result = translator.ExprMonad.new(translator, result_type, aggr_ast)
        result.aggregated = True
        return result
    def __call__(monad, *args, **kwargs): throw(TypeError)
    def __getitem__(monad, key): throw(TypeError)
    def __add__(monad, monad2): throw(TypeError)
    def __sub__(monad, monad2): throw(TypeError)
    def __mul__(monad, monad2): throw(TypeError)
    def __div__(monad, monad2): throw(TypeError)
    def __pow__(monad, monad2): throw(TypeError)
    def __neg__(monad): throw(TypeError)
    def abs(monad): throw(TypeError)

typeerror_re = re.compile(r'\(\) takes (no|(?:exactly|at (?:least|most)))(?: (\d+))? arguments \((\d+) given\)')

def reraise_improved_typeerror(exc, func_name, orig_func_name):
    if not exc.args: throw(exc)
    msg = exc.args[0]
    if not msg.startswith(func_name): throw(exc)
    msg = msg[len(func_name):]
    match = typeerror_re.match(msg)
    if not match:
        exc.args = (orig_func_name + msg,)
        throw(exc)
    what, takes, given = match.groups()
    takes, given = int(takes), int(given)
    if takes: what = '%s %d' % (what, takes-1)
    plural = takes > 2 and 's' or ''
    new_msg = '%s() takes %s argument%s (%d given)' % (orig_func_name, what, plural, given-1)
    exc.args = (new_msg,)
    throw(exc)

def raise_forgot_parentheses(monad):
    assert monad.type == 'METHOD'
    throw(TranslationError, 'You seems to forgot parentheses after %s' % ast2src(monad.node))

class MethodMonad(Monad):
    def __init__(monad, translator, parent, attrname):
        Monad.__init__(monad, translator, 'METHOD')
        monad.parent = parent
        monad.attrname = attrname
    def getattr(monad, attrname):
        raise_forgot_parentheses(monad)
    def __call__(monad, *args, **kwargs):
        method = getattr(monad.parent, 'call_' + monad.attrname)
        try: return method(*args, **kwargs)
        except TypeError, exc: reraise_improved_typeerror(exc, method.__name__, monad.attrname)

    def contains(monad, item, not_in=False): raise_forgot_parentheses(monad)
    def nonzero(monad): raise_forgot_parentheses(monad)
    def negate(monad): raise_forgot_parentheses(monad)
    def aggregate(monad, func_name): raise_forgot_parentheses(monad)
    def __getitem__(monad, key): raise_forgot_parentheses(monad)

    def __add__(monad, monad2): raise_forgot_parentheses(monad)
    def __sub__(monad, monad2): raise_forgot_parentheses(monad)
    def __mul__(monad, monad2): raise_forgot_parentheses(monad)
    def __div__(monad, monad2): raise_forgot_parentheses(monad)
    def __pow__(monad, monad2): raise_forgot_parentheses(monad)

    def __neg__(monad): raise_forgot_parentheses(monad)
    def abs(monad): raise_forgot_parentheses(monad)

class EntityMonad(Monad):
    def __init__(monad, translator, entity):
        Monad.__init__(monad, translator, SetType(entity))
        if translator.database is None:
            translator.database = entity._database_
        elif translator.database is not entity._database_:
            throw(TranslationError, 'All entities in a query must belong to the same database')
    def __getitem__(monad, *args):
        throw(NotImplementedError)

class ListMonad(Monad):
    def __init__(monad, translator, items):
        Monad.__init__(monad, translator, tuple(item.type for item in items))
        monad.items = items
    def contains(monad, x, not_in=False):
        translator = monad.translator
        for item in monad.items: check_comparable(item, x)
        left_sql = x.getsql()
        if len(left_sql) == 1:
            if not_in: sql = [ 'NOT_IN', left_sql[0], [ item.getsql()[0] for item in monad.items ] ]
            else: sql = [ 'IN', left_sql[0], [ item.getsql()[0] for item in monad.items ] ]
        elif not_in:
            sql = sqland([ sqlor([ [ 'NE', a, b ]  for a, b in zip(left_sql, item.getsql()) ]) for item in monad.items ])
        else:
            sql = sqlor([ sqland([ [ 'EQ', a, b ]  for a, b in zip(left_sql, item.getsql()) ]) for item in monad.items ])
        return translator.BoolExprMonad(translator, sql)

class BufferMixin(MonadMixin):
    pass

_binop_errmsg = 'Unsupported operand types %r and %r for operation %r in expression: {EXPR}'

def make_numeric_binop(op, sqlop):
    def numeric_binop(monad, monad2):
        translator = monad.translator
        if isinstance(monad2, (translator.AttrSetMonad, translator.NumericSetExprMonad)):
            return translator.NumericSetExprMonad(op, sqlop, monad, monad2)
        if monad2.type == 'METHOD': raise_forgot_parentheses(monad2)
        result_type, monad, monad2 = coerce_monads(monad, monad2)
        if result_type is None:
            throw(TypeError, _binop_errmsg % (type2str(monad.type), type2str(monad2.type), op))
        left_sql = monad.getsql()[0]
        right_sql = monad2.getsql()[0]
        return translator.NumericExprMonad(translator, result_type, [ sqlop, left_sql, right_sql ])
    numeric_binop.__name__ = sqlop
    return numeric_binop

class NumericMixin(MonadMixin):
    def mixin_init(monad):
        assert monad.type in numeric_types, monad.type
    __add__ = make_numeric_binop('+', 'ADD')
    __sub__ = make_numeric_binop('-', 'SUB')
    __mul__ = make_numeric_binop('*', 'MUL')
    __div__ = make_numeric_binop('/', 'DIV')
    def __pow__(monad, monad2):
        translator = monad.translator
        if not isinstance(monad2, translator.NumericMixin):
            throw(TypeError, _binop_errmsg % (type2str(monad.type), type2str(monad2.type), '**'))
        left_sql = monad.getsql()
        right_sql = monad2.getsql()
        assert len(left_sql) == len(right_sql) == 1
        return translator.NumericExprMonad(translator, float, [ 'POW', left_sql[0], right_sql[0] ])
    def __neg__(monad):
        sql = monad.getsql()[0]
        translator = monad.translator
        return translator.NumericExprMonad(translator, monad.type, [ 'NEG', sql ])
    def abs(monad):
        sql = monad.getsql()[0]
        translator = monad.translator
        return translator.NumericExprMonad(translator, monad.type, [ 'ABS', sql ])
    def nonzero(monad):
        translator = monad.translator
        return translator.CmpMonad('!=', monad, translator.ConstMonad.new(translator, 0))
    def negate(monad):
        translator = monad.translator
        return translator.CmpMonad('==', monad, translator.ConstMonad.new(translator, 0))

def datetime_attr_factory(name):
    def attr_func(monad):
        sql = [ name, monad.getsql()[0] ]
        translator = monad.translator
        return translator.NumericExprMonad(translator, int, sql)
    attr_func.__name__ = name.lower()
    return attr_func

class DateMixin(MonadMixin):
    def mixin_init(monad):
        assert monad.type is date
    attr_year = datetime_attr_factory('YEAR')
    attr_month = datetime_attr_factory('MONTH')
    attr_day = datetime_attr_factory('DAY')

class DatetimeMixin(DateMixin):
    def mixin_init(monad):
        assert monad.type is datetime
    def call_date(monad):
        translator = monad.translator
        sql = [ 'DATE', monad.getsql()[0] ]
        return translator.ExprMonad.new(translator, date, sql)
    attr_hour = datetime_attr_factory('HOUR')
    attr_minute = datetime_attr_factory('MINUTE')
    attr_second = datetime_attr_factory('SECOND')

def make_string_binop(op, sqlop):
    def string_binop(monad, monad2):
        translator = monad.translator
        if not are_comparable_types(monad.type, monad2.type, sqlop):
            if monad2.type == 'METHOD': raise_forgot_parentheses(monad2)
            throw(TypeError, _binop_errmsg % (type2str(monad.type), type2str(monad2.type), op))
        left_sql = monad.getsql()
        right_sql = monad2.getsql()
        assert len(left_sql) == len(right_sql) == 1
        return translator.StringExprMonad(translator, monad.type, [ sqlop, left_sql[0], right_sql[0] ])
    string_binop.__name__ = sqlop
    return string_binop

def make_string_func(sqlop):
    def func(monad):
        sql = monad.getsql()
        assert len(sql) == 1
        translator = monad.translator
        return translator.StringExprMonad(translator, monad.type, [ sqlop, sql[0] ])
    func.__name__ = sqlop
    return func

class StringMixin(MonadMixin):
    def mixin_init(monad):
        assert issubclass(monad.type, basestring), monad.type
    __add__ = make_string_binop('+', 'CONCAT')
    def __getitem__(monad, index):
        translator = monad.translator
        if isinstance(index, translator.ListMonad): throw(TypeError, "String index must be of 'int' type. Got 'tuple' in {EXPR}")
        elif isinstance(index, slice):
            if index.step is not None: throw(TypeError, 'Step is not supported in {EXPR}')
            start, stop = index.start, index.stop
            if start is None and stop is None: return monad
            if isinstance(monad, translator.StringConstMonad) \
               and (start is None or isinstance(start, translator.NumericConstMonad)) \
               and (stop is None or isinstance(stop, translator.NumericConstMonad)):
                if start is not None: start = start.value
                if stop is not None: stop = stop.value
                return translator.ConstMonad.new(translator, monad.value[start:stop])

            if start is not None and start.type is not int:
                throw(TypeError, "Invalid type of start index (expected 'int', got %r) in string slice {EXPR}" % type2str(start.type))
            if stop is not None and stop.type is not int:
                throw(TypeError, "Invalid type of stop index (expected 'int', got %r) in string slice {EXPR}" % type2str(stop.type))
            expr_sql = monad.getsql()[0]

            if start is None: start = translator.ConstMonad.new(translator, 0)

            if isinstance(start, translator.NumericConstMonad):
                if start.value < 0: throw(NotImplementedError, 'Negative indices are not supported in string slice {EXPR}')
                start_sql = [ 'VALUE', start.value + 1 ]
            else:
                start_sql = start.getsql()[0]
                start_sql = [ 'ADD', start_sql, [ 'VALUE', 1 ] ]

            if stop is None:
                len_sql = None
            elif isinstance(stop, translator.NumericConstMonad):
                if stop.value < 0: throw(NotImplementedError, 'Negative indices are not supported in string slice {EXPR}')
                if isinstance(start, translator.NumericConstMonad):
                    len_sql = [ 'VALUE', stop.value - start.value ]
                else:
                    len_sql = [ 'SUB', [ 'VALUE', stop.value ], start.getsql()[0] ]
            else:
                stop_sql = stop.getsql()[0]
                if isinstance(start, translator.NumericConstMonad):
                    len_sql = [ 'SUB', stop_sql, [ 'VALUE', start.value ] ]
                else:
                    len_sql = [ 'SUB', stop_sql, start.getsql()[0] ]

            sql = [ 'SUBSTR', expr_sql, start_sql, len_sql ]
            return translator.StringExprMonad(translator, monad.type, sql)

        if isinstance(monad, translator.StringConstMonad) and isinstance(index, translator.NumericConstMonad):
            return translator.ConstMonad.new(translator, monad.value[index.value])
        if index.type is not int: throw(TypeError,
            'String indices must be integers. Got %r in expression {EXPR}' % type2str(index.type))
        expr_sql = monad.getsql()[0]
        if isinstance(index, translator.NumericConstMonad):
            value = index.value
            if value >= 0: value += 1
            index_sql = [ 'VALUE', value ]
        else:
            inner_sql = index.getsql()[0]
            index_sql = [ 'ADD', inner_sql, [ 'CASE', None, [ (['GE', inner_sql, [ 'VALUE', 0 ]], [ 'VALUE', 1 ]) ], [ 'VALUE', 0 ] ] ]
        sql = [ 'SUBSTR', expr_sql, index_sql, [ 'VALUE', 1 ] ]
        return translator.StringExprMonad(translator, monad.type, sql)
    def nonzero(monad):
        sql = monad.getsql()[0]
        translator = monad.translator
        result = translator.BoolExprMonad(translator, [ 'GT', [ 'LENGTH', sql ], [ 'VALUE', 0 ]])
        result.aggregated = monad.aggregated
        return result
    def len(monad):
        sql = monad.getsql()[0]
        translator = monad.translator
        return translator.NumericExprMonad(translator, int, [ 'LENGTH', sql ])
    def contains(monad, item, not_in=False):
        translator = monad.translator
        check_comparable(item, monad, 'LIKE')
        if isinstance(item, translator.StringConstMonad):
            item_sql = [ 'VALUE', '%%%s%%' % item.value ]
        else:
            item_sql = [ 'CONCAT', [ 'VALUE', '%' ], item.getsql()[0], [ 'VALUE', '%' ] ]
        sql = [ 'NOT_LIKE' if not_in else 'LIKE', monad.getsql()[0], item_sql ]
        return translator.BoolExprMonad(translator, sql)
    call_upper = make_string_func('UPPER')
    call_lower = make_string_func('LOWER')
    def call_startswith(monad, arg):
        translator = monad.translator
        if not are_comparable_types(monad.type, arg.type, None):
            if arg.type == 'METHOD': raise_forgot_parentheses(arg)
            throw(TypeError, 'Expected %r argument but got %r in expression {EXPR}'
                            % (type2str(monad.type), type2str(arg.type)))
        if isinstance(arg, translator.StringConstMonad):
            assert isinstance(arg.value, basestring)
            arg_sql = [ 'VALUE', arg.value + '%' ]
        else:
            arg_sql = arg.getsql()[0]
            arg_sql = [ 'CONCAT', arg_sql, [ 'VALUE', '%' ] ]
        parent_sql = monad.getsql()[0]
        sql = [ 'LIKE', parent_sql, arg_sql ]
        return translator.BoolExprMonad(translator, sql)
    def call_endswith(monad, arg):
        translator = monad.translator
        if not are_comparable_types(monad.type, arg.type, None):
            if arg.type == 'METHOD': raise_forgot_parentheses(arg)
            throw(TypeError, 'Expected %r argument but got %r in expression {EXPR}'
                            % (type2str(monad.type), type2str(arg.type)))
        if isinstance(arg, translator.StringConstMonad):
            assert isinstance(arg.value, basestring)
            arg_sql = [ 'VALUE', '%' + arg.value ]
        else:
            arg_sql = arg.getsql()[0]
            arg_sql = [ 'CONCAT', [ 'VALUE', '%' ], arg_sql ]
        parent_sql = monad.getsql()[0]
        sql = [ 'LIKE', parent_sql, arg_sql ]
        return translator.BoolExprMonad(translator, sql)
    def strip(monad, chars, strip_type):
        translator = monad.translator
        if chars is not None and not are_comparable_types(monad.type, chars.type, None):
            if chars.type == 'METHOD': raise_forgot_parentheses(chars)
            throw(TypeError, "'chars' argument must be of %r type in {EXPR}, got: %r"
                            % (type2str(monad.type), type2str(chars.type)))
        parent_sql = monad.getsql()[0]
        sql = [ strip_type, parent_sql ]
        if chars is not None: sql.append(chars.getsql()[0])
        return translator.StringExprMonad(translator, monad.type, sql)
    def call_strip(monad, chars=None):
        return monad.strip(chars, 'TRIM')
    def call_lstrip(monad, chars=None):
        return monad.strip(chars, 'LTRIM')
    def call_rstrip(monad, chars=None):
        return monad.strip(chars, 'RTRIM')

class ObjectMixin(MonadMixin):
    def mixin_init(monad):
        assert isinstance(monad.type, EntityMeta)
    def getattr(monad, name):
        translator = monad.translator
        entity = monad.type
        try: attr = entity._adict_[name]
        except KeyError: throw(AttributeError)
        if hasattr(monad, 'tableref'): monad.tableref.used_attrs.add(attr)
        if not attr.is_collection:
            return translator.AttrMonad.new(monad, attr)
        else:
            return translator.AttrSetMonad(monad, attr)
    def requires_distinct(monad, joined=False):
        return monad.attr.reverse.is_collection or monad.parent.requires_distinct(joined)  # parent ???

class ObjectIterMonad(ObjectMixin, Monad):
    def __init__(monad, translator, tableref, entity):
        Monad.__init__(monad, translator, entity)
        monad.tableref = tableref
    def getsql(monad, subquery=None):
        entity = monad.type
        alias, pk_columns = monad.tableref.make_join(pk_only=True)
        return [ [ 'COLUMN', alias, column ] for column in pk_columns ]
    def requires_distinct(monad, joined=False):
        return monad.tableref.name_path != monad.translator.tree.quals[-1].assign.name

class AttrMonad(Monad):
    @staticmethod
    def new(parent, attr, *args, **kwargs):
        translator = parent.translator
        type = normalize_type(attr.py_type)
        if type in numeric_types: cls = translator.NumericAttrMonad
        elif type in string_types: cls = translator.StringAttrMonad
        elif type is date: cls = translator.DateAttrMonad
        elif type is datetime: cls = translator.DatetimeAttrMonad
        elif type is buffer: cls = translator.BufferAttrMonad
        elif isinstance(type, EntityMeta): cls = translator.ObjectAttrMonad
        else: throw(NotImplementedError, type)  # pragma: no cover
        return cls(parent, attr, *args, **kwargs)
    def __new__(cls, *args):
        if cls is AttrMonad: assert False, 'Abstract class'
        return Monad.__new__(cls)
    def __init__(monad, parent, attr):
        assert monad.__class__ is not AttrMonad
        translator = parent.translator
        attr_type = normalize_type(attr.py_type)
        Monad.__init__(monad, parent.translator, attr_type)
        monad.parent = parent
        monad.attr = attr
    def getsql(monad, subquery=None):
        parent = monad.parent
        attr = monad.attr
        entity = attr.entity
        pk_only = attr.pk_offset is not None
        alias, parent_columns = monad.parent.tableref.make_join(pk_only)
        if not pk_only: columns = attr.columns
        elif not entity._pk_is_composite_: columns = parent_columns
        else:
            offset = attr.pk_columns_offset
            columns = parent_columns[offset:offset+len(attr.columns)]
        return [ [ 'COLUMN', alias, column ] for column in columns ]

class ObjectAttrMonad(ObjectMixin, AttrMonad):
    def __init__(monad, parent, attr):
        AttrMonad.__init__(monad, parent, attr)
        translator = monad.translator
        parent_monad = monad.parent
        entity = monad.type
        name_path = '-'.join((parent_monad.tableref.name_path, attr.name))
        monad.tableref = translator.subquery.get_tableref(name_path)
        if monad.tableref is None:
            parent_subquery = parent_monad.tableref.subquery
            monad.tableref = parent_subquery.add_tableref(name_path, parent_monad.tableref, attr)

class NumericAttrMonad(NumericMixin, AttrMonad): pass
class StringAttrMonad(StringMixin, AttrMonad): pass
class DateAttrMonad(DateMixin, AttrMonad): pass
class DatetimeAttrMonad(DatetimeMixin, AttrMonad): pass
class BufferAttrMonad(BufferMixin, AttrMonad): pass

class ParamMonad(Monad):
    @staticmethod
    def new(translator, type, paramkey):
        type = normalize_type(type)
        if type in numeric_types: cls = translator.NumericParamMonad
        elif type in string_types: cls = translator.StringParamMonad
        elif type is date: cls = translator.DateParamMonad
        elif type is datetime: cls = translator.DatetimeParamMonad
        elif type is buffer: cls = translator.BufferParamMonad
        elif isinstance(type, EntityMeta): cls = translator.ObjectParamMonad
        else: throw(NotImplementedError, type)  # pragma: no cover
        result = cls(translator, type, paramkey)
        result.aggregated = False
        return result
    def __new__(cls, *args):
        if cls is ParamMonad: assert False, 'Abstract class'
        return Monad.__new__(cls)
    def __init__(monad, translator, type, paramkey):
        type = normalize_type(type)
        Monad.__init__(monad, translator, type)
        monad.paramkey = paramkey
        if not isinstance(type, EntityMeta):
            provider = translator.database.provider
            monad.converter = provider.get_converter_by_py_type(type)
        else: monad.converter = None
    def getsql(monad, subquery=None):
        return [ [ 'PARAM', monad.paramkey, monad.converter ] ]

class ObjectParamMonad(ObjectMixin, ParamMonad):
    def __init__(monad, translator, entity, paramkey):
        assert translator.database is entity._database_
        ParamMonad.__init__(monad, translator, entity, paramkey)
        varkey, i, j = paramkey
        assert j is None
        monad.params = tuple((varkey, i, j) for j in xrange(len(entity._pk_converters_)))
    def getsql(monad, subquery=None):
        entity = monad.type
        assert len(monad.params) == len(entity._pk_converters_)
        return [ [ 'PARAM', param, converter ] for param, converter in zip(monad.params, entity._pk_converters_) ]
    def requires_distinct(monad, joined=False):
        assert False  # pragma: no cover

class StringParamMonad(StringMixin, ParamMonad): pass
class NumericParamMonad(NumericMixin, ParamMonad): pass
class DateParamMonad(DateMixin, ParamMonad): pass
class DatetimeParamMonad(DatetimeMixin, ParamMonad): pass
class BufferParamMonad(BufferMixin, ParamMonad): pass

class ExprMonad(Monad):
    @staticmethod
    def new(translator, type, sql):
        if type in numeric_types: cls = translator.NumericExprMonad
        elif type in string_types: cls = translator.StringExprMonad
        elif type is date: cls = translator.DateExprMonad
        elif type is datetime: cls = translator.DatetimeExprMonad
        else: throw(NotImplementedError, type)  # pragma: no cover
        return cls(translator, type, sql)
    def __new__(cls, *args):
        if cls is ExprMonad: assert False, 'Abstract class'
        return Monad.__new__(cls)
    def __init__(monad, translator, type, sql):
        Monad.__init__(monad, translator, type)
        monad.sql = sql
    def getsql(monad, subquery=None):
        return [ monad.sql ]

class StringExprMonad(StringMixin, ExprMonad): pass
class NumericExprMonad(NumericMixin, ExprMonad): pass
class DateExprMonad(DateMixin, ExprMonad): pass
class DatetimeExprMonad(DatetimeMixin, ExprMonad): pass

class ConstMonad(Monad):
    @staticmethod
    def new(translator, value):
        value_type = get_normalized_type_of(value)
        if value_type in numeric_types: cls = translator.NumericConstMonad
        elif value_type in string_types: cls = translator.StringConstMonad
        elif value_type is date: cls = translator.DateConstMonad
        elif value_type is datetime: cls = translator.DatetimeConstMonad
        elif value_type is NoneType: cls = translator.NoneMonad
        elif value_type is buffer: cls = translator.BufferConstMonad
        else: throw(NotImplementedError, value_type)  # pragma: no cover
        result = cls(translator, value)
        result.aggregated = False
        return result
    def __new__(cls, *args):
        if cls is ConstMonad: assert False, 'Abstract class'
        return Monad.__new__(cls)
    def __init__(monad, translator, value):
        value_type = get_normalized_type_of(value)
        Monad.__init__(monad, translator, value_type)
        monad.value = value
    def getsql(monad, subquery=None):
        return [ [ 'VALUE', monad.value ] ]

class NoneMonad(ConstMonad):
    type = NoneType
    def __init__(monad, translator, value=None):
        assert value is None
        ConstMonad.__init__(monad, translator, value)

class BufferConstMonad(BufferMixin, ConstMonad): pass

class StringConstMonad(StringMixin, ConstMonad):
    def len(monad):
        return monad.translator.ConstMonad.new(monad.translator, len(monad.value))

class NumericConstMonad(NumericMixin, ConstMonad): pass
class DateConstMonad(DateMixin, ConstMonad): pass
class DatetimeConstMonad(DatetimeMixin, ConstMonad): pass

class BoolMonad(Monad):
    def __init__(monad, translator):
        monad.translator = translator
        monad.type = bool

sql_negation = { 'IN' : 'NOT_IN', 'EXISTS' : 'NOT_EXISTS', 'LIKE' : 'NOT_LIKE', 'BETWEEN' : 'NOT_BETWEEN', 'IS_NULL' : 'IS_NOT_NULL' }
sql_negation.update((value, key) for key, value in sql_negation.items())

class BoolExprMonad(BoolMonad):
    def __init__(monad, translator, sql):
        monad.translator = translator
        monad.type = bool
        monad.sql = sql
    def getsql(monad, subquery=None):
        return [ monad.sql ]
    def negate(monad):
        translator = monad.translator
        sql = monad.sql
        sqlop = sql[0]
        negated_op = sql_negation.get(sqlop)
        if negated_op is not None:
            negated_sql = [ negated_op ] + sql[1:]
        elif negated_op == 'NOT':
            assert len(sql) == 2
            negated_sql = sql[1]
        else: return translator.NotMonad(translator, sql)
        return translator.BoolExprMonad(translator, negated_sql)

cmp_ops = { '>=' : 'GE', '>' : 'GT', '<=' : 'LE', '<' : 'LT' }

cmp_negate = { '<' : '>=', '<=' : '>', '==' : '!=', 'is' : 'is not' }
cmp_negate.update((b, a) for a, b in cmp_negate.items())

class CmpMonad(BoolMonad):
    def __init__(monad, op, left, right):
        translator = left.translator
        if op == '<>': op = '!='
        if left.type is NoneType:
            assert right.type is not NoneType
            left, right = right, left
        if right.type is NoneType:
            if op == '==': op = 'is'
            elif op == '!=': op = 'is not'
        elif op == 'is': op = '=='
        elif op == 'is not': op = '!='
        check_comparable(left, right, op)
        result_type, left, right = coerce_monads(left, right)
        BoolMonad.__init__(monad, translator)
        monad.op = op
        monad.left = left
        monad.right = right
        monad.aggregated = getattr(left, 'aggregated', False) or getattr(right, 'aggregated', False)
    def negate(monad):
        return monad.translator.CmpMonad(cmp_negate[monad.op], monad.left, monad.right)
    def getsql(monad, subquery=None):
        op = monad.op
        sql = []
        left_sql = monad.left.getsql()
        if op == 'is':
            return [ sqland([ [ 'IS_NULL', item ] for item in left_sql ]) ]
        if op == 'is not':
            return [ sqland([ [ 'IS_NOT_NULL', item ] for item in left_sql ]) ]
        right_sql = monad.right.getsql()
        assert len(left_sql) == len(right_sql)
        if op in ('<', '<=', '>', '>='):
            assert len(left_sql) == len(right_sql) == 1
            return [ [ cmp_ops[op], left_sql[0], right_sql[0] ] ]
        if op == '==':
            return [ sqland([ [ 'EQ', a, b ] for (a, b) in zip(left_sql, right_sql) ]) ]
        if op == '!=':
            return [ sqlor([ [ 'NE', a, b ] for (a, b) in zip(left_sql, right_sql) ]) ]
        assert False  # pragma: no cover

class LogicalBinOpMonad(BoolMonad):
    def __init__(monad, operands):
        assert len(operands) >= 2
        items = []
        translator = operands[0].translator
        monad.translator = translator
        for operand in operands:
            if operand.type is not bool: items.append(operand.nonzero())
            elif isinstance(operand, translator.LogicalBinOpMonad) and monad.binop == operand.binop:
                items.extend(operand.operands)
            else: items.append(operand)
        BoolMonad.__init__(monad, items[0].translator)
        monad.operands = items
    def getsql(monad, subquery=None):
        result = [ monad.binop ]
        for operand in monad.operands:
            operand_sql = operand.getsql()
            assert len(operand_sql) == 1
            result.extend(operand_sql)
        return [ result ]

class AndMonad(LogicalBinOpMonad):
    binop = 'AND'

class OrMonad(LogicalBinOpMonad):
    binop = 'OR'

class NotMonad(BoolMonad):
    def __init__(monad, operand):
        if operand.type is not bool: operand = operand.nonzero()
        BoolMonad.__init__(monad, operand.translator)
        monad.operand = operand
    def negate(monad):
        return monad.operand
    def getsql(monad, subquery=None):
        return [ [ 'NOT', monad.operand.getsql()[0] ] ]

special_functions = SQLTranslator.special_functions = {}

class FuncMonadMeta(MonadMeta):
    def __new__(meta, cls_name, bases, cls_dict):
        func = cls_dict.get('func')
        monad_cls = super(FuncMonadMeta, meta).__new__(meta, cls_name, bases, cls_dict)
        if func:
            if type(func) is tuple: functions = func
            else: functions = (func,)
            for func in functions: special_functions[func] = monad_cls
        return monad_cls

class FuncMonad(Monad):
    __metaclass__ = FuncMonadMeta
    type = 'function'
    def __init__(monad, translator):
        monad.translator = translator
    def __call__(monad, *args, **kwargs):
        translator = monad.translator
        for arg in args:
            assert isinstance(arg, translator.Monad)
        for value in kwargs.values():
            assert isinstance(value, translator.Monad)
        try: return monad.call(*args, **kwargs)
        except TypeError, exc:
            func = monad.func
            if type(func) is tuple: func = func[0]
            reraise_improved_typeerror(exc, 'call', func.__name__)

class FuncBufferMonad(FuncMonad):
    func = buffer
    def call(monad, x):
        translator = monad.translator
        if not isinstance(x, translator.StringConstMonad): throw(TypeError)
        return translator.ConstMonad.new(translator, buffer(x.value))

class FuncDecimalMonad(FuncMonad):
    func = Decimal
    def call(monad, x):
        translator = monad.translator
        if not isinstance(x, translator.StringConstMonad): throw(TypeError)
        return translator.ConstMonad.new(translator, Decimal(x.value))

class FuncDateMonad(FuncMonad):
    func = date
    def call(monad, year, month, day):
        translator = monad.translator
        for x, name in zip((year, month, day), ('year', 'month', 'day')):
            if not isinstance(x, translator.NumericMixin) or x.type is not int: throw(TypeError,
                "'%s' argument of date(year, month, day) function must be of 'int' type. Got: %r" % (name, type2str(x.type)))
            if not isinstance(x, translator.ConstMonad): throw(NotImplementedError)
        return translator.ConstMonad.new(translator, date(year.value, month.value, day.value))
    def call_today(monad):
        translator = monad.translator
        return translator.DateExprMonad(translator, date, [ 'TODAY' ])

class FuncDatetimeMonad(FuncDateMonad):
    func = datetime
    def call(monad, *args):
        translator = monad.translator
        for x, name in zip(args, ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond')):
            if not isinstance(x, translator.NumericMixin) or x.type is not int: throw(TypeError,
                "'%s' argument of datetime(...) function must be of 'int' type. Got: %r" % (name, type2str(x.type)))
            if not isinstance(x, translator.ConstMonad): throw(NotImplementedError)
        return translator.ConstMonad.new(translator, datetime(*tuple(arg.value for arg in args)))
    def call_now(monad):
        translator = monad.translator
        return translator.DatetimeExprMonad(translator, datetime, [ 'NOW' ])

class FuncConcatMonad(FuncMonad):
    func = concat
    def call(monad, *args):
        if len(args) < 2: throw(TranslationError, 'concat() function requires at least two arguments')
        translator = args[0].translator
        s = u = False
        result_ast = [ 'CONCAT' ]
        for arg in args:
            t = arg.type
            if isinstance(t, EntityMeta) or type(t) in (tuple, SetType):
                throw(TranslationError, 'Invalid argument of concat() function: %s' % ast2src(arg.node))
            if t is str: s = True
            elif t is u: u = True
            result_ast.extend(arg.getsql())
        if s and u: throw(TranslationError, 'Mixing str and unicode in {EXPR}')
        result_type = str if s else unicode
        return translator.ExprMonad.new(translator, result_type, result_ast)

class FuncLenMonad(FuncMonad):
    func = len
    def call(monad, x):
        return x.len()

class FuncCountMonad(FuncMonad):
    func = count, core.count
    def call(monad, x=None):
        translator = monad.translator
        if isinstance(x, translator.StringConstMonad) and x.value == '*': x = None
        if x is not None: return x.count()
        result = translator.ExprMonad.new(translator, int, [ 'COUNT', 'ALL' ])
        result.aggregated = True
        return result

class FuncAbsMonad(FuncMonad):
    func = abs
    def call(monad, x):
        return x.abs()

class FuncSumMonad(FuncMonad):
    func = sum, core.sum
    def call(monad, x):
        return x.aggregate('SUM')

class FuncAvgMonad(FuncMonad):
    func = avg, core.avg
    def call(monad, x):
        return x.aggregate('AVG')

class FuncDistinctMonad(FuncMonad):
    func = distinct, core.distinct
    def call(monad, x):
        if isinstance(x, SetMixin): return x.call_distinct()
        if not isinstance(x, NumericMixin): throw(TypeError)
        result = object.__new__(x.__class__)
        result.__dict__.update(x.__dict__)
        result.forced_distinct = True
        return result

class FuncMinMonad(FuncMonad):
    func = min, core.min
    def call(monad, *args):
        if not args: throw(TypeError, 'min() function expected at least one argument')
        if len(args) == 1: return args[0].aggregate('MIN')
        return minmax(monad, 'MIN', *args)

class FuncMaxMonad(FuncMonad):
    func = max, core.max
    def call(monad, *args):
        if not args: throw(TypeError, 'max() function expected at least one argument')
        if len(args) == 1: return args[0].aggregate('MAX')
        return minmax(monad, 'MAX', *args)

def minmax(monad, sqlop, *args):
    assert len(args) > 1
    translator = monad.translator
    t = args[0].type
    if t == 'METHOD': raise_forgot_parentheses(args[0])
    if t not in comparable_types: throw(TypeError,
        "Value of type %r is not valid as argument of %r function in expression {EXPR}"
        % (type2str(t), sqlop.lower()))
    for arg in args[1:]:
        t2 = arg.type
        if t2 == 'METHOD': raise_forgot_parentheses(arg)
        t3 = coerce_types(t, t2)
        if t3 is None: throw(IncomparableTypesError, t, t2)
        t = t3
    if t3 in numeric_types and translator.dialect == 'PostgreSQL':
        args = list(args)
        for i, arg in enumerate(args):
            if arg.type is bool:
                args[i] = NumericExprMonad(translator, int, [ 'TO_INT', arg.getsql() ])
    sql = [ sqlop ] + [ arg.getsql()[0] for arg in args ]
    return translator.ExprMonad.new(translator, t, sql)

class FuncSelectMonad(FuncMonad):
    func = core.select
    def call(monad, queryset):
        translator = monad.translator
        if not isinstance(queryset, translator.QuerySetMonad): throw(TypeError,
            "'select' function expects generator expression, got: {EXPR}")
        return queryset

class FuncExistsMonad(FuncMonad):
    func = core.exists
    def call(monad, arg):
        if not isinstance(arg, monad.translator.SetMixin): throw(TypeError,
            "'exists' function expects generator expression or collection, got: {EXPR}")
        return arg.nonzero()

class FuncDescMonad(FuncMonad):
    func = core.desc
    def call(monad, expr):
        return DescMonad(expr)

class DescMonad(Monad):
    def __init__(monad, expr):
        Monad.__init__(monad, expr.translator, expr.type)
        monad.expr = expr
    def getsql(monad):
        return [ [ 'DESC', item ] for item in monad.expr.getsql() ]

class JoinMonad(Monad):
    def __init__(monad, translator):
        Monad.__init__(monad, translator, 'JOIN')
        monad.hint_join_prev = translator.hint_join
        translator.hint_join = True
    def __call__(monad, x):
        monad.translator.hint_join = monad.hint_join_prev
        return x
special_functions[JOIN] = JoinMonad

class RandomMonad(Monad):
    def __init__(monad, translator):
        Monad.__init__(monad, translator, '<function>')
    def __call__(monad):
        return NumericExprMonad(monad.translator, float, [ 'RANDOM' ])
    def getattr(monad, attrname):
        if attrname == 'random': return RandomMonad(monad.translator)
        return Monad.getattr(monad, attrname)

class SetMixin(MonadMixin):
    forced_distinct = False
    def call_distinct(monad):
        new_monad = object.__new__(monad.__class__)
        new_monad.__dict__.update(monad.__dict__)
        new_monad.forced_distinct = True
        return new_monad

def make_attrset_binop(op, sqlop):
    def attrset_binop(monad, monad2):
        NumericSetExprMonad = monad.translator.NumericSetExprMonad
        return NumericSetExprMonad(op, sqlop, monad, monad2)
    return attrset_binop

class AttrSetMonad(SetMixin, Monad):
    def __init__(monad, parent, attr):
        translator = parent.translator
        item_type = normalize_type(attr.py_type)
        Monad.__init__(monad, translator, SetType(item_type))
        monad.parent = parent
        monad.attr = attr
        monad.subquery = None
        monad.tableref = None
    def cmp(monad, op, monad2):
        translator = monad.translator
        if type(monad2.type) is SetType \
           and are_comparable_types(monad.type.item_type, monad2.type.item_type): pass
        elif monad.type != monad2.type: check_comparable(monad, monad2)
        throw(NotImplementedError)
    def contains(monad, item, not_in=False):
        translator = monad.translator
        check_comparable(item, monad, 'in')
        if not translator.hint_join:
            sqlop = not_in and 'NOT_IN' or 'IN'
            subquery = monad._subselect()
            expr_list = subquery.expr_list
            from_ast = subquery.from_ast
            conditions = subquery.outer_conditions + subquery.conditions
            if len(expr_list) == 1:
                subquery_ast = [ 'SELECT', [ 'ALL' ] + expr_list, from_ast, [ 'WHERE' ] + conditions ]
                sql_ast = [ sqlop, item.getsql()[0], subquery_ast ]
            elif translator.row_value_syntax:
                subquery_ast = [ 'SELECT', [ 'ALL' ] + expr_list, from_ast, [ 'WHERE' ] + conditions ]
                sql_ast = [ sqlop, [ 'ROW' ] + item.getsql(), subquery_ast ]
            else:
                conditions += [ [ 'EQ', expr1, expr2 ] for expr1, expr2 in izip(item.getsql(), expr_list) ]
                sql_ast = [ not_in and 'NOT_EXISTS' or 'EXISTS', from_ast, [ 'WHERE' ] + conditions ]
            result = translator.BoolExprMonad(translator, sql_ast)
            result.nogroup = True
            return result
        elif not not_in:
            translator.distinct = True
            tableref = monad.make_tableref(translator.subquery)
            expr_list = monad.make_expr_list()
            expr_ast = sqland([ [ 'EQ', expr1, expr2 ]  for expr1, expr2 in zip(expr_list, item.getsql()) ])
            return translator.BoolExprMonad(translator, expr_ast)
        else:
            subquery = Subquery(translator.subquery)
            tableref = monad.make_tableref(subquery)
            attr = monad.attr
            alias, columns = tableref.make_join(pk_only=attr.reverse)
            expr_list = monad.make_expr_list()
            if not attr.reverse: columns = attr.columns
            from_ast = translator.subquery.from_ast
            from_ast[0] = 'LEFT_JOIN'
            from_ast.extend(subquery.from_ast[1:])
            conditions = [ [ 'EQ', [ 'COLUMN', alias, column ], expr ]  for column, expr in zip(columns, item.getsql()) ]
            conditions.extend(subquery.conditions)
            from_ast[-1][-1] = sqland([ from_ast[-1][-1] ] + conditions)
            expr_ast = sqland([ [ 'IS_NULL', expr ] for expr in expr_list ])
            return translator.BoolExprMonad(translator, expr_ast)
    def getattr(monad, name):
        try: return Monad.getattr(monad, name)
        except AttributeError: pass
        entity = monad.type.item_type
        if not isinstance(entity, EntityMeta): throw(AttributeError)
        attr = entity._adict_.get(name)
        if attr is None: throw(AttributeError)
        return monad.translator.AttrSetMonad(monad, attr)
    def requires_distinct(monad, joined=False, for_count=False):
        if monad.parent.requires_distinct(joined): return True
        reverse = monad.attr.reverse
        if not reverse: return True
        if reverse.is_collection:
            translator = monad.translator
            if not for_count and not translator.hint_join: return True
            if isinstance(monad.parent, monad.translator.AttrSetMonad): return True
        return False
    def count(monad):
        translator = monad.translator

        subquery = monad._subselect()
        expr_list = subquery.expr_list
        from_ast = subquery.from_ast
        inner_conditions = subquery.conditions
        outer_conditions = subquery.outer_conditions

        distinct = monad.requires_distinct(joined=translator.hint_join, for_count=True)
        sql_ast = make_aggr = None
        extra_grouping = False
        if not distinct and monad.tableref.name_path != translator.optimize:
            make_aggr = lambda expr_list: [ 'COUNT', 'ALL' ]
        elif len(expr_list) == 1:
            make_aggr = lambda expr_list: [ 'COUNT', 'DISTINCT' ] + expr_list
        elif translator.dialect == 'Oracle':
            if monad.tableref.name_path == translator.optimize:
                alias, pk_columns = monad.tableref.make_join(pk_only=True)
                make_aggr = lambda expr_list: [ 'COUNT', 'DISTINCT' if distinct else 'ALL', [ 'COLUMN', alias, 'ROWID' ] ]
            else:
                extra_grouping = True
                if translator.hint_join: make_aggr = lambda expr_list: [ 'COUNT', 'ALL' ]
                else: make_aggr = lambda expr_list: [ 'COUNT', 'ALL', [ 'COUNT', 'ALL' ] ]
        elif translator.dialect == 'PostgreSQL':
            row = [ 'ROW' ] + expr_list
            expr = [ 'CASE', None, [ [ [ 'IS_NULL', row ], [ 'VALUE', None ] ] ], row ]
            make_aggr = lambda expr_list: [ 'COUNT', 'DISTINCT', expr ]
        elif translator.row_value_syntax:
            make_aggr = lambda expr_list: [ 'COUNT', 'DISTINCT' ] + expr_list
        elif translator.dialect == 'SQLite':
            if not distinct:
                alias, pk_columns = monad.tableref.make_join(pk_only=True)
                make_aggr = lambda expr_list: [ 'COUNT', 'ALL', [ 'COLUMN', alias, 'ROWID' ] ]
            elif translator.hint_join:  # Same join as in Oracle
                extra_grouping = True
                make_aggr = lambda expr_list: [ 'COUNT', 'ALL' ]
            elif translator.sqlite_version < (3, 6, 21):
                alias, pk_columns = monad.tableref.make_join(pk_only=False)
                make_aggr = lambda expr_list: [ 'COUNT', 'DISTINCT', [ 'COLUMN', alias, 'ROWID' ] ]
            else:
                sql_ast = [ 'SELECT', [ 'AGGREGATES', [ 'COUNT', 'ALL' ] ],
                          [ 'FROM', [ 't', 'SELECT', [
                              [ 'DISTINCT' ] + expr_list, from_ast,
                              [ 'WHERE' ] + outer_conditions + inner_conditions ] ] ] ]
        else: throw(NotImplementedError)  # pragma: no cover
        if sql_ast: optimized = False
        elif translator.hint_join:
            sql_ast, optimized = monad._joined_subselect(make_aggr, extra_grouping, coalesce_to_zero=True)
        else:
            sql_ast, optimized = monad._aggregated_scalar_subselect(make_aggr, extra_grouping)
        translator.aggregated_subquery_paths.add(monad.tableref.name_path)
        result = translator.ExprMonad.new(translator, int, sql_ast)
        if optimized: result.aggregated = True
        else: result.nogroup = True
        return result
    len = count
    def aggregate(monad, func_name):
        translator = monad.translator
        item_type = monad.type.item_type

        if func_name in ('SUM', 'AVG'):
            if item_type not in numeric_types: throw(TypeError,
                "Function %s() expects query or items of numeric type, got %r in {EXPR}"
                % (func_name.lower(), type2str(item_type)))
        elif func_name in ('MIN', 'MAX'):
            if item_type not in comparable_types: throw(TypeError,
                "Function %s() expects query or items of comparable type, got %r in {EXPR}"
                % (func_name.lower(), type2str(item_type)))
        else: assert False  # pragma: no cover

        if monad.forced_distinct and func_name in ('SUM', 'AVG'):
            make_aggr = lambda expr_list: [ func_name ] + expr_list + [ True ]
        else:
            make_aggr = lambda expr_list: [ func_name ] + expr_list

        if translator.hint_join:
            sql_ast, optimized = monad._joined_subselect(make_aggr, coalesce_to_zero=(func_name=='SUM'))
        else:
            sql_ast, optimized = monad._aggregated_scalar_subselect(make_aggr)

        result_type = func_name == 'AVG' and float or item_type
        translator.aggregated_subquery_paths.add(monad.tableref.name_path)
        result = translator.ExprMonad.new(monad.translator, result_type, sql_ast)
        if optimized: result.aggregated = True
        else: result.nogroup = True
        return result
    def nonzero(monad):
        subquery = monad._subselect()
        sql_ast = [ 'EXISTS', subquery.from_ast,
                    [ 'WHERE' ] + subquery.outer_conditions + subquery.conditions ]
        translator = monad.translator
        return translator.BoolExprMonad(translator, sql_ast)
    def negate(monad):
        subquery = monad._subselect()
        sql_ast = [ 'NOT_EXISTS', subquery.from_ast,
                    [ 'WHERE' ] + subquery.outer_conditions + subquery.conditions ]
        translator = monad.translator
        return translator.BoolExprMonad(translator, sql_ast)
    def make_tableref(monad, subquery):
        parent = monad.parent
        attr = monad.attr
        translator = monad.translator
        if isinstance(parent, ObjectMixin): parent_tableref = parent.tableref
        elif isinstance(parent, translator.AttrSetMonad): parent_tableref = parent.make_tableref(subquery)
        else: assert False  # pragma: no cover
        if attr.reverse:
            name_path = parent_tableref.name_path + '-' + attr.name
            monad.tableref = subquery.get_tableref(name_path) \
                             or subquery.add_tableref(name_path, parent_tableref, attr)
        else: monad.tableref = parent_tableref
        monad.tableref.can_affect_distinct = True
        return monad.tableref
    def make_expr_list(monad):
        attr = monad.attr
        pk_only = attr.reverse or attr.pk_offset is not None
        alias, columns = monad.tableref.make_join(pk_only)
        if attr.reverse: pass
        elif pk_only:
            offset = attr.pk_columns_offset
            columns = columns[offset:offset+len(attr.columns)]
        else: columns = attr.columns
        return [ [ 'COLUMN', alias, column ] for column in columns ]
    def _aggregated_scalar_subselect(monad, make_aggr, extra_grouping=False):
        translator = monad.translator
        subquery = monad._subselect()
        optimized = False
        if translator.optimize == monad.tableref.name_path:
            sql_ast = make_aggr(subquery.expr_list)
            optimized = True
            if not translator.from_optimized:
                from_ast = monad.subquery.from_ast[1:]
                from_ast[0] = from_ast[0] + [ sqland(subquery.outer_conditions) ]
                translator.subquery.from_ast.extend(from_ast)
                translator.from_optimized = True
        else: sql_ast = [ 'SELECT', [ 'AGGREGATES', make_aggr(subquery.expr_list) ],
                          subquery.from_ast,
                          [ 'WHERE' ] + subquery.outer_conditions + subquery.conditions ]
        if extra_grouping:  # This is for Oracle only, with COUNT(COUNT(*))
            sql_ast.append([ 'GROUP_BY' ] + subquery.expr_list)
        return sql_ast, optimized
    def _joined_subselect(monad, make_aggr, extra_grouping=False, coalesce_to_zero=False):
        translator = monad.translator
        subquery = monad._subselect()
        expr_list = subquery.expr_list
        from_ast = subquery.from_ast
        inner_conditions = subquery.conditions
        outer_conditions = subquery.outer_conditions

        groupby_columns = [ inner_column[:] for cond, outer_column, inner_column in outer_conditions ]
        assert len(set(alias for _, alias, column in groupby_columns)) == 1

        if extra_grouping:
            inner_alias = translator.subquery.get_short_alias(None, 't')
            inner_columns = [ 'DISTINCT' ]
            col_mapping = {}
            col_names = set()
            for i, column_ast in enumerate(groupby_columns + expr_list):
                assert column_ast[0] == 'COLUMN'
                tname, cname = column_ast[1:]
                if cname not in col_names:
                    col_mapping[tname, cname] = cname
                    col_names.add(cname)
                    expr = [ 'AS', column_ast, cname ]
                    new_name = cname
                else:
                    new_name = 'expr-%d' % translator.subquery.expr_counter.next()
                    col_mapping[tname, cname] = new_name
                    expr = [ 'AS', column_ast, new_name ]
                inner_columns.append(expr)
                if i < len(groupby_columns):
                    groupby_columns[i] = [ 'COLUMN', inner_alias, new_name ]
            inner_select = [ inner_columns, from_ast ]
            if inner_conditions: inner_select.append([ 'WHERE' ] + inner_conditions)
            from_ast = [ 'FROM', [ inner_alias, 'SELECT', inner_select ] ]
            outer_conditions = outer_conditions[:]
            for i, (cond, outer_column, inner_column) in enumerate(outer_conditions):
                assert inner_column[0] == 'COLUMN'
                tname, cname = inner_column[1:]
                new_name = col_mapping[tname, cname]
                outer_conditions[i] = [ cond, outer_column, [ 'COLUMN', inner_alias, new_name ] ]

        subquery_columns = [ 'ALL' ]
        for column_ast in groupby_columns:
            assert column_ast[0] == 'COLUMN'
            subquery_columns.append([ 'AS', column_ast, column_ast[2] ])
        expr_name = 'expr-%d' % translator.subquery.expr_counter.next()
        subquery_columns.append([ 'AS', make_aggr(expr_list), expr_name ])
        subquery_ast = [ subquery_columns, from_ast ]
        if inner_conditions and not extra_grouping:
            subquery_ast.append([ 'WHERE' ] + inner_conditions)
        subquery_ast.append([ 'GROUP_BY' ] + groupby_columns)

        alias = translator.subquery.get_short_alias(None, 't')
        for cond in outer_conditions: cond[2][1] = alias
        translator.subquery.from_ast.append([ alias, 'SELECT', subquery_ast, sqland(outer_conditions) ])
        expr_ast = [ 'COLUMN', alias, expr_name ]
        if coalesce_to_zero: expr_ast = [ 'COALESCE', expr_ast, [ 'VALUE', 0 ] ]
        return expr_ast, False
    def _subselect(monad):
        if monad.subquery is not None: return monad.subquery
        attr = monad.attr
        translator = monad.translator
        subquery = Subquery(translator.subquery)
        monad.make_tableref(subquery)
        subquery.expr_list = monad.make_expr_list()
        if not attr.reverse and not attr.is_required:
            subquery.conditions.extend([ 'IS_NOT_NULL', expr ] for expr in subquery.expr_list)
        if subquery is not translator.subquery:
            outer_cond = subquery.from_ast[1].pop()
            if outer_cond[0] == 'AND': subquery.outer_conditions = outer_cond[1:]
            else: subquery.outer_conditions = [ outer_cond ]
        monad.subquery = subquery
        return subquery
    def getsql(monad, subquery=None):
        if subquery is None: subquery = monad.translator.subquery
        monad.make_tableref(subquery)
        return monad.make_expr_list()
    __add__ = make_attrset_binop('+', 'ADD')
    __sub__ = make_attrset_binop('-', 'SUB')
    __mul__ = make_attrset_binop('*', 'MUL')
    __div__ = make_attrset_binop('/', 'DIV')

def make_numericset_binop(op, sqlop):
    def numericset_binop(monad, monad2):
        NumericSetExprMonad = monad.translator.NumericSetExprMonad
        return NumericSetExprMonad(op, sqlop, monad, monad2)
    return numericset_binop

class NumericSetExprMonad(SetMixin, Monad):
    def __init__(monad, op, sqlop, left, right):
        result_type, left, right = coerce_monads(left, right)
        assert type(result_type) is SetType
        if result_type.item_type not in numeric_types:
            throw(TypeError, _binop_errmsg % (type2str(left.type), type2str(right.type), op))
        Monad.__init__(monad, left.translator, result_type)
        monad.op = op
        monad.sqlop = sqlop
        monad.left = left
        monad.right = right
    def aggregate(monad, func_name):
        translator = monad.translator
        subquery = Subquery(translator.subquery)
        expr = monad.getsql(subquery)[0]
        translator.aggregated_subquery_paths.add(monad.tableref.name_path)
        outer_cond = subquery.from_ast[1].pop()
        if outer_cond[0] == 'AND': subquery.outer_conditions = outer_cond[1:]
        else: subquery.outer_conditions = [ outer_cond ]
        result_type = float if func_name == 'AVG' else monad.type.item_type
        aggr_ast = [ func_name, expr ]
        if monad.forced_distinct and func_name in ('SUM', 'AVG'): aggr_ast.append(True)
        if translator.optimize != monad.tableref.name_path:
            sql_ast = [ 'SELECT', [ 'AGGREGATES', aggr_ast ],
                        subquery.from_ast,
                        [ 'WHERE' ] + subquery.outer_conditions + subquery.conditions ]
            result = translator.ExprMonad.new(translator, result_type, sql_ast)
            result.nogroup = True
        else:
            if not translator.from_optimized:
                from_ast = subquery.from_ast[1:]
                from_ast[0] = from_ast[0] + [ sqland(subquery.outer_conditions) ]
                translator.subquery.from_ast.extend(from_ast)
                translator.from_optimized = True
            sql_ast = aggr_ast
            result = translator.ExprMonad.new(translator, result_type, sql_ast)
            result.aggregated = True
        return result
    def getsql(monad, subquery=None):
        if subquery is None: subquery = monad.translator.subquery
        left, right = monad.left, monad.right
        left_expr = left.getsql(subquery)[0]
        right_expr = right.getsql(subquery)[0]
        if isinstance(left, NumericMixin): left_path = ''
        else: left_path = left.tableref.name_path + '-'
        if isinstance(right, NumericMixin): right_path = ''
        else: right_path = right.tableref.name_path + '-'
        if left_path.startswith(right_path): tableref = left.tableref
        elif right_path.startswith(left_path): tableref = right.tableref
        else: throw(TranslationError, 'Cartesian product detected in %s' % ast2src(monad.node))
        monad.tableref = tableref
        return [ [ monad.sqlop, left_expr, right_expr ] ]
    __add__ = make_numericset_binop('+', 'ADD')
    __sub__ = make_numericset_binop('-', 'SUB')
    __mul__ = make_numericset_binop('*', 'MUL')
    __div__ = make_numericset_binop('/', 'DIV')

class QuerySetMonad(SetMixin, Monad):
    nogroup = True
    def __init__(monad, translator, subtranslator):
        monad.translator = translator
        monad.subtranslator = subtranslator
        item_type = subtranslator.expr_type
        monad.item_type = item_type
        monad_type = SetType(item_type)
        Monad.__init__(monad, translator, monad_type)
    def contains(monad, item, not_in=False):
        translator = monad.translator
        check_comparable(item, monad, 'in')
        if isinstance(item, translator.ListMonad):
            item_columns = []
            for subitem in item.items: item_columns.extend(subitem.getsql())
        else: item_columns = item.getsql()

        sub = monad.subtranslator
        subquery_ast = sub.shallow_copy_of_subquery_ast()
        select_ast, from_ast, where_ast = subquery_ast[1:4]
        if translator.hint_join and len(sub.subquery.from_ast[1]) == 3:
            subquery = translator.subquery
            if not not_in:
                translator.distinct = True
                if subquery.from_ast[0] == 'FROM':
                    subquery.from_ast[0] = 'INNER_JOIN'
            else:
                subquery.left_join = True
                subquery.from_ast[0] = 'LEFT_JOIN'
            col_names = set()
            next = subquery.expr_counter.next
            new_names = []
            exprs = []

            for i, column_ast in enumerate(select_ast):
                if not i: continue  # 'ALL'
                if column_ast[0] == 'COLUMN':
                    tab_name, col_name = column_ast[1:]
                    if col_name not in col_names:
                        col_names.add(col_name)
                        new_names.append(col_name)
                        select_ast[i] = [ 'AS', column_ast, col_name ]
                        continue
                new_name = 'expr-%d' % next()
                new_names.append(new_name)
                select_ast[i] = [ 'AS', column_ast, new_name ]

            alias = subquery.get_short_alias(None, 't')
            outer_conditions = [ [ 'EQ', item_column, [ 'COLUMN', alias, new_name ] ]
                                    for item_column, new_name in izip(item_columns, new_names) ]
            subquery.from_ast.append([ alias, 'SELECT', subquery_ast[1:], sqland(outer_conditions) ])
            if not_in: sql_ast = sqland([ [ 'IS_NULL', [ 'COLUMN', alias, new_name ] ]
                                              for new_name in new_names ])
            else: sql_ast = [ 'EQ', [ 'VALUE', 1 ], [ 'VALUE', 1 ] ]
        else:
            if len(item_columns) == 1:
                sql_ast = [ not_in and 'NOT_IN' or 'IN', item_columns[0], subquery_ast ]
            elif translator.row_value_syntax:
                sql_ast = [ not_in and 'NOT_IN' or 'IN', [ 'ROW' ] + item_columns, subquery_ast ]
            else:
                where_ast += [ [ 'EQ', expr1, expr2 ] for expr1, expr2 in izip(item_columns, select_ast[1:]) ]
                sql_ast = [ not_in and 'NOT_EXISTS' or 'EXISTS' ] + subquery_ast[2:]
        return translator.BoolExprMonad(translator, sql_ast)
    def nonzero(monad):
        subquery_ast = monad.subtranslator.shallow_copy_of_subquery_ast()
        subquery_ast = [ 'EXISTS' ] + subquery_ast[2:]
        translator = monad.translator
        return translator.BoolExprMonad(translator, subquery_ast)
    def negate(monad):
        sql = monad.nonzero().sql
        assert sql[0] == 'EXISTS'
        translator = monad.translator
        return translator.BoolExprMonad(translator, [ 'NOT_EXISTS' ] + sql[1:])
    def count(monad):
        translator = monad.translator
        sub = monad.subtranslator
        if sub.aggregated: throw(TranslationError, 'Too complex aggregation in {EXPR}')
        subquery_ast = sub.shallow_copy_of_subquery_ast()
        from_ast, where_ast = subquery_ast[2:4]
        sql_ast = None

        expr_type = sub.expr_type
        if isinstance(expr_type, (tuple, EntityMeta)):
            if not sub.distinct:
                select_ast = [ 'AGGREGATES', [ 'COUNT', 'ALL' ] ]
            elif len(sub.expr_columns) == 1:
                select_ast = [ 'AGGREGATES', [ 'COUNT', 'DISTINCT' ] + sub.expr_columns ]
            elif translator.dialect == 'Oracle':
                sql_ast = [ 'SELECT', [ 'AGGREGATES', [ 'COUNT', 'ALL', [ 'COUNT', 'ALL' ] ] ],
                            from_ast, where_ast, [ 'GROUP_BY' ] + sub.expr_columns ]
            elif translator.row_value_syntax:
                select_ast = [ 'AGGREGATES', [ 'COUNT', 'DISTINCT' ] + sub.expr_columns ]
            elif translator.dialect == 'SQLite':
                if translator.sqlite_version < (3, 6, 21):
                    if sub.aggregated: throw(TranslationError)
                    alias, pk_columns = sub.tableref.make_join(pk_only=False)
                    subquery_ast = sub.shallow_copy_of_subquery_ast()
                    from_ast, where_ast = subquery_ast[2:4]
                    sql_ast = [ 'SELECT',
                        [ 'AGGREGATES', [ 'COUNT', 'DISTINCT', [ 'COLUMN', alias, 'ROWID' ] ] ],
                        from_ast, where_ast ]
                else:
                    alias = translator.subquery.get_short_alias(None, 't')
                    sql_ast = [ 'SELECT', [ 'AGGREGATES', [ 'COUNT', 'ALL' ] ],
                                [ 'FROM', [ alias, 'SELECT', [
                                  [ 'DISTINCT' ] + sub.expr_columns, from_ast, where_ast ] ] ] ]
            else: assert False  # pragma: no cover
        elif len(sub.expr_columns) == 1:
            select_ast = [ 'AGGREGATES', [ 'COUNT', 'DISTINCT', sub.expr_columns[0] ] ]
        else: throw(NotImplementedError)  # pragma: no cover

        if sql_ast is None: sql_ast = [ 'SELECT', select_ast, from_ast, where_ast ]
        return translator.ExprMonad.new(translator, int, sql_ast)
    len = count
    def aggregate(monad, func_name):
        translator = monad.translator
        sub = monad.subtranslator
        if sub.aggregated: throw(TranslationError, 'Too complex aggregation in {EXPR}')
        subquery_ast = sub.shallow_copy_of_subquery_ast()
        from_ast, where_ast = subquery_ast[2:4]
        expr_type = sub.expr_type
        if func_name in ('SUM', 'AVG'):
            if expr_type not in numeric_types: throw(TypeError,
                "Function %s() expects query or items of numeric type, got %r in {EXPR}"
                % (func_name.lower(), type2str(expr_type)))
        elif func_name in ('MIN', 'MAX'):
            if expr_type not in comparable_types: throw(TypeError,
                "Function %s() cannot be applied to type %r in {EXPR}"
                % (func_name.lower(), type2str(expr_type)))
        else: assert False  # pragma: no cover
        assert len(sub.expr_columns) == 1
        aggr_ast = [ func_name, sub.expr_columns[0] ]
        if monad.forced_distinct and func_name in ('SUM', 'AVG'): aggr_ast.append(True)
        select_ast = [ 'AGGREGATES', aggr_ast ]
        sql_ast = [ 'SELECT', select_ast, from_ast, where_ast ]
        result_type = func_name == 'AVG' and float or expr_type
        return translator.ExprMonad.new(translator, result_type, sql_ast)
    def call_count(monad):
        return monad.count()
    def call_sum(monad):
        return monad.aggregate('SUM')
    def call_min(monad):
        return monad.aggregate('MIN')
    def call_max(monad):
        return monad.aggregate('MAX')
    def call_avg(monad):
        return monad.aggregate('AVG')

for name, value in globals().items():
    if name.endswith('Monad') or name.endswith('Mixin'):
        setattr(SQLTranslator, name, value)
del name, value

########NEW FILE########
__FILENAME__ = model1
from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    _table_ = "Students"
    record = PrimaryKey(int)
    name = Required(unicode, column="fio")
    group = Required("Group")
    scholarship = Required(int, default=0)
    marks = Set("Mark")

class Group(db.Entity):
    _table_ = "Groups"
    number = PrimaryKey(str)
    department = Required(int)
    students = Set("Student")
    subjects = Set("Subject")

class Subject(db.Entity):
    _table_ = "Subjects"
    name = PrimaryKey(unicode)
    groups = Set("Group")
    marks = Set("Mark")

class Mark(db.Entity):
    _table_ = "Exams"
    student = Required(Student, column="student")
    subject = Required(Subject, column="subject")
    value = Required(int)
    PrimaryKey(student, subject)


db.generate_mapping(create_tables=True)

@db_session
def populate_db():
    Physics = Subject(name='Physics')
    Chemistry = Subject(name='Chemistry')
    Math = Subject(name='Math')

    g3132 = Group(number='3132', department=33, subjects=[ Physics, Math ])
    g4145 = Group(number='4145', department=44, subjects=[ Physics, Chemistry, Math ])
    g4146 = Group(number='4146', department=44)

    s101 = Student(record=101, name='Bob', group=g4145, scholarship=0)
    s102 = Student(record=102, name='Joe', group=g4145, scholarship=800)
    s103 = Student(record=103, name='Alex', group=g4145, scholarship=0)
    s104 = Student(record=104, name='Brad', group=g3132, scholarship=500)
    s105 = Student(record=105, name='John', group=g3132, scholarship=1000)

    Mark(student=s101, subject=Physics, value=4)
    Mark(student=s101, subject=Math, value=3)
    Mark(student=s102, subject=Chemistry, value=5)
    Mark(student=s103, subject=Physics, value=2)
    Mark(student=s103, subject=Chemistry, value=4)
populate_db()

########NEW FILE########
__FILENAME__ = testutils
from pony.orm.core import Database
from pony.utils import import_module

def raises_exception(exc_class, msg=None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
                self.assert_(False, "expected exception %s wasn't raised" % exc_class.__name__)
            except exc_class, e:
                if not e.args: self.assertEqual(msg, None)
                elif msg is not None:
                    self.assertEqual(e.args[0], msg, "incorrect exception message. expected '%s', got '%s'" % (msg, e.args[0]))
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

def flatten(x):
    result = []
    for el in x:
        if hasattr(el, "__iter__") and not isinstance(el, basestring):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result

class TestConnection(object):
    def __init__(con, database):
        con.database = database
        if database and database.provider_name == 'postgres':
            con.autocommit = True
    def commit(con):
        pass
    def rollback(con):
        pass
    def cursor(con):
        return test_cursor

class TestCursor(object):
    def __init__(cursor):
        cursor.description = []
    def execute(cursor, sql, args=None):
        pass
    def fetchone(cursor):
        return None
    def fetchmany(cursor, size):
        return []
    def fetchall(cursor):
        return []

test_cursor = TestCursor()

class TestPool(object):
    def __init__(pool, database):
        pool.database = database
    def connect(pool):
        return TestConnection(pool.database)
    def release(pool, con):
        pass
    def drop(pool, con):
        pass
    def disconnect(pool):
        pass

class TestDatabase(Database):
    real_provider_name = None
    raw_server_version = None
    sql = None
    def bind(self, provider_name, *args, **kwargs):
        if self.real_provider_name is not None:
            provider_name = self.real_provider_name
        self.provider_name = provider_name
        provider_module = import_module('pony.orm.dbproviders.' + provider_name)
        provider_cls = provider_module.provider_cls
        raw_server_version = self.raw_server_version

        if raw_server_version is None:
            if provider_name == 'sqlite': raw_server_version = '3.7.17'
            elif provider_name in ('postgres', 'pygresql'): raw_server_version = '9.2'
            elif provider_name == 'oracle': raw_server_version = '11.2.0.2.0'
            elif provider_name == 'mysql': raw_server_version = '5.6.11'
            else: assert False, provider_name

        t = map(int, raw_server_version.split('.'))
        if len(t) == 2: t.append(0)
        server_version = tuple(t)
        if provider_name in ('postgres', 'pygresql'):
            server_version = int('%d%02d%02d' % server_version)

        class TestProvider(provider_cls):
            def inspect_connection(provider, connection):
                pass
        TestProvider.server_version = server_version

        kwargs['pony_check_connection'] = False
        kwargs['pony_pool_mockup'] = TestPool(self)
        Database.bind(self, TestProvider, *args, **kwargs)
    def _execute(database, sql, globals, locals, frame_depth):
        assert False
    def _exec_sql(database, sql, arguments=None, returning_id=False):
        assert type(arguments) is not list and not returning_id
        database.sql = sql
        database.arguments = arguments
        return test_cursor
    def generate_mapping(database, filename=None, check_tables=True, create_tables=False):
        return Database.generate_mapping(database, filename, create_tables=False)

########NEW FILE########
__FILENAME__ = test_all
import unittest
import pony.orm.core, pony.options

pony.options.CUT_TRACEBACK = False
pony.orm.core.sql_debug(False)

from test_diagram import *
from test_diagram_attribute import *
from test_diagram_inheritance import *
from test_diagram_keys import *
from test_mapping import *
from test_relations_one2one1 import *
from test_relations_one2one2 import *
from test_relations_symmetric_one2one import *
from test_relations_symmetric_m2m import *
from test_relations_one2many import *
from test_relations_m2m import *
from test_crud_raw_sql import *
from test_declarative_attr_set_monad import *
from test_declarative_date import *
from test_declarative_func_monad import *
from test_declarative_join_optimization import *
from test_declarative_method_monad import *
from test_declarative_object_flat_monad import *
from test_declarative_orderby_limit import *
from test_declarative_string_mixin import *
from test_declarative_query_set_monad import *
from test_declarative_sqltranslator import *
from test_declarative_sqltranslator2 import *
from test_declarative_exceptions import *
from test_collections import *
from test_sqlbuilding_formatstyles import *
from test_sqlbuilding_sqlast import *
from test_orm_query import *
from test_frames import *
from test_core_multiset import *
from test_core_find_in_cache import *
from test_db_session import *
from test_lazy import *
from test_query import *
from test_filter import *
from test_crud import *

#from new_tests import *

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_collections
import unittest
from testutils import raises_exception
from model1 import *

class TestCollections(unittest.TestCase):

    @db_session
    def test_setwrapper_len(self):
        g = Group.get(number='4145')
        self.assert_(len(g.students) == 3)

    @db_session
    def test_setwrapper_nonzero(self):
        g = Group.get(number='4145')
        self.assert_(bool(g.students) == True)
        self.assert_(len(g.students) == 3)

    @db_session
    @raises_exception(TypeError, 'Collection attribute Group.students cannot be specified as search criteria')
    def test_get_by_collection_error(self):
        Group.get(students=[])

# replace collection items when the old ones are not fully loaded
##>>> from pony.examples.orm.students01.model import *
##>>> s1 = Student[101]
##>>> g = s1.group
##>>> g.__dict__[Group.students].is_fully_loaded
##False
##>>> s2 = Student[104]
##>>> g.students = [s2]
##>>>

# replace collection items when the old ones are not loaded
##>>> from pony.examples.orm.students01.model import *
##>>> g = Group[4145]
##>>> Group.students not in g.__dict__
##True
##>>> s2 = Student[104]
##>>> g.students = [s2]


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_core_find_in_cache
from __future__ import with_statement

import unittest
from pony.orm.tests.testutils import raises_exception
from pony.orm import *

db = Database('sqlite', ':memory:')

class AbstractUser(db.Entity):
    username = PrimaryKey(unicode)

class User(AbstractUser):
    diagrams = Set('Diagram')
    email = Optional(unicode)

class SubUser1(User):
    attr1 = Optional(unicode)

class SubUser2(User):
    attr2 = Optional(unicode)

class Organization(AbstractUser):
    address = Optional(unicode)

class SubOrg1(Organization):
    attr3 = Optional(unicode)

class SubOrg2(Organization):
    attr4 = Optional(unicode)

class Diagram(db.Entity):
    name = Required(unicode)
    owner = Required(User)

db.generate_mapping(create_tables=True)

with db_session:
    u1 = User(username='user1')
    u2 = SubUser1(username='subuser1', attr1='some attr')
    u3 = SubUser2(username='subuser2', attr2='some attr')
    o1 = Organization(username='org1')
    o2 = SubOrg1(username='suborg1', attr3='some attr')
    o3 = SubOrg2(username='suborg2', attr4='some attr')
    au = AbstractUser(username='abstractUser')
    Diagram(name='diagram1', owner=u1)
    Diagram(name='diagram2', owner=u2)
    Diagram(name='diagram3', owner=u3)

def is_seed(entity, pk):
    cache = entity._database_._get_cache()
    return pk in [ obj._pk_ for obj in cache.seeds[entity._pk_attrs_] ]

class TestInheritance(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test1(self):
        u = User.get(username='org1')
        org = Organization.get(username='org1')
        u1 = User.get(username='org1')
        self.assertEqual(u, None)
        self.assertEqual(org, Organization['org1'])
        self.assertEqual(u1, None)

    def test_user_1(self):
        Diagram.get(lambda d: d.name == 'diagram1')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'user1'))
        u = AbstractUser['user1']
        self.assertNotEqual(last_sql, db.last_sql)
        self.assertEqual(u.__class__, User)
    def test_user_2(self):
        Diagram.get(lambda d: d.name == 'diagram1')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'user1'))
        u = User['user1']
        self.assertNotEqual(last_sql, db.last_sql)
        self.assertEqual(u.__class__, User)
    @raises_exception(ObjectNotFound)
    def test_user_3(self):
        Diagram.get(lambda d: d.name == 'diagram1')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'user1'))
        try:
            SubUser1['user1']
        finally:
            self.assertNotEqual(last_sql, db.last_sql)
    @raises_exception(ObjectNotFound)
    def test_user_4(self):
        Diagram.get(lambda d: d.name == 'diagram1')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'user1'))
        try:
            Organization['user1']
        finally:
            self.assertEqual(last_sql, db.last_sql)
    @raises_exception(ObjectNotFound)
    def test_user_5(self):
        Diagram.get(lambda d: d.name == 'diagram1')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'user1'))
        try:
            SubOrg1['user1']
        finally:
            self.assertEqual(last_sql, db.last_sql)


    def test_subuser_1(self):
        Diagram.get(lambda d: d.name == 'diagram2')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'subuser1'))
        u = AbstractUser['subuser1']
        self.assertNotEqual(last_sql, db.last_sql)
        self.assertEqual(u.__class__, SubUser1)
    def test_subuser_2(self):
        Diagram.get(lambda d: d.name == 'diagram2')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'subuser1'))
        u = User['subuser1']
        self.assertNotEqual(last_sql, db.last_sql)
        self.assertEqual(u.__class__, SubUser1)
    def test_subuser_3(self):
        Diagram.get(lambda d: d.name == 'diagram2')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'subuser1'))
        u = SubUser1['subuser1']
        self.assertNotEqual(last_sql, db.last_sql)
        self.assertEqual(u.__class__, SubUser1)
    @raises_exception(ObjectNotFound)
    def test_subuser_4(self):
        Diagram.get(lambda d: d.name == 'diagram2')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'subuser1'))
        try:
            Organization['subuser1']
        finally:
            self.assertEqual(last_sql, db.last_sql)
    @raises_exception(ObjectNotFound)
    def test_subuser_5(self):
        Diagram.get(lambda d: d.name == 'diagram2')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'subuser1'))
        try:
            SubUser2['subuser1']
        finally:
            self.assertNotEqual(last_sql, db.last_sql)
    @raises_exception(ObjectNotFound)
    def test_subuser_6(self):
        Diagram.get(lambda d: d.name == 'diagram2')
        last_sql = db.last_sql
        self.assert_(is_seed(User, 'subuser1'))
        try:
            SubOrg2['subuser1']
        finally:
            self.assertEqual(last_sql, db.last_sql)

    def test_user_6(self):
        u1 = SubUser1['subuser1']
        last_sql = db.last_sql
        u2 = SubUser1['subuser1']
        self.assertEqual(last_sql, db.last_sql)
        self.assertEqual(u1, u2)
    def test_user_7(self):
        u1 = SubUser1['subuser1']
        u1.delete()
        last_sql = db.last_sql
        u2 = SubUser1.get(username='subuser1')
        self.assertEqual(last_sql, db.last_sql)
        self.assertEqual(u2, None)
    def test_user_8(self):
        u1 = SubUser1['subuser1']
        last_sql = db.last_sql
        u2 = SubUser1.get(username='subuser1', attr1='wrong val')
        self.assertEqual(last_sql, db.last_sql)
        self.assertEqual(u2, None)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_core_multiset
import unittest
from cPickle import loads, dumps

from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Department(db.Entity):
    number = PrimaryKey(int)
    groups = Set('Group')
    courses = Set('Course')

class Group(db.Entity):
    number = PrimaryKey(int)
    department = Required(Department)
    students = Set('Student')

class Student(db.Entity):
    name = Required(str)
    group = Required(Group)
    courses = Set('Course')

class Course(db.Entity):
    name = PrimaryKey(str)
    department = Required(Department)
    students = Set('Student')

db.generate_mapping(create_tables=True)

with db_session:
    d1 = Department(number=1)
    d2 = Department(number=2)
    d3 = Department(number=3)

    g1 = Group(number=101, department=d1)
    g2 = Group(number=102, department=d1)
    g3 = Group(number=201, department=d2)

    c1 = Course(name='C1', department=d1)
    c2 = Course(name='C2', department=d1)
    c3 = Course(name='C3', department=d2)
    c4 = Course(name='C4', department=d2)
    c5 = Course(name='C5', department=d3)

    s1 = Student(name='S1', group=g1, courses=[c1, c2])
    s2 = Student(name='S2', group=g1, courses=[c1, c3])
    s3 = Student(name='S3', group=g1, courses=[c2, c3])

    s4 = Student(name='S4', group=g2, courses=[c1, c2])
    s5 = Student(name='S5', group=g2, courses=[c1, c2])

    s6 = Student(name='A', group=g3, courses=[c5])

class TestMultiset(unittest.TestCase):

    @db_session
    def test_multiset_repr_1(self):
        d = Department[1]
        multiset = d.groups.students
        self.assertEqual(repr(multiset), "<StudentMultiset Department[1].groups.students (5 items)>")

    @db_session
    def test_multiset_repr_2(self):
        g = Group[101]
        multiset = g.students.courses
        self.assertEqual(repr(multiset), "<CourseMultiset Group[101].students.courses (6 items)>")

    @db_session
    def test_multiset_repr_3(self):
        g = Group[201]
        multiset = g.students.courses
        self.assertEqual(repr(multiset), "<CourseMultiset Group[201].students.courses (1 item)>")

    def test_multiset_repr_4(self):
        with db_session:
            g = Group[101]
            multiset = g.students.courses
        self.assertEqual(multiset._obj_._session_cache_.is_alive, False)
        self.assertEqual(repr(multiset), "<CourseMultiset Group[101].students.courses>")

    @db_session
    def test_multiset_str(self):
        g = Group[101]
        multiset = g.students.courses
        self.assertEqual(str(multiset), "CourseMultiset({Course['C1']: 2, Course['C2']: 2, Course['C3']: 2})")

    @db_session
    def test_multiset_distinct(self):
        d = Department[1]
        multiset = d.groups.students.courses
        self.assertEqual(multiset.distinct(), {Course['C1']: 4, Course['C2']: 4, Course['C3']: 2})

    @db_session
    def test_multiset_nonzero(self):
        d = Department[1]
        multiset = d.groups.students
        self.assertEqual(bool(multiset), True)

    @db_session
    def test_multiset_len(self):
        d = Department[1]
        multiset = d.groups.students.courses
        self.assertEqual(len(multiset), 10)

    @db_session
    def test_multiset_eq(self):
        d = Department[1]
        multiset = d.groups.students.courses
        c1, c2, c3 = Course['C1'], Course['C2'], Course['C3']
        self.assertEqual(multiset, multiset)
        self.assertEqual(multiset, {c1: 4, c2: 4, c3: 2})
        self.assertEqual(multiset, [ c1, c1, c1, c2, c2, c2, c2, c3, c3, c1 ])

    @db_session
    def test_multiset_ne(self):
        d = Department[1]
        multiset = d.groups.students.courses
        self.assertFalse(multiset != multiset)
        
    @db_session
    def test_multiset_contains(self):
        d = Department[1]
        multiset = d.groups.students.courses
        self.assertTrue(Course['C1'] in multiset)
        self.assertFalse(Course['C5'] in multiset)

    def test_multiset_reduce(self):
        with db_session:
            d = Department[1]
            multiset = d.groups.students
            s = dumps(multiset)
        with db_session:
            d = Department[1]
            multiset_2 = d.groups.students
            multiset_1 = loads(s)        
            self.assertEqual(multiset_1, multiset_2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_crud
from __future__ import with_statement
from decimal import Decimal
import unittest
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Group(db.Entity):
    id = PrimaryKey(int)
    major = Required(unicode)
    students = Set('Student')

class Student(db.Entity):
    name = Required(unicode)
    scholarship = Required(Decimal, default=0)
    picture = Optional(buffer, lazy=True)
    email = Required(unicode, unique=True)
    phone = Optional(unicode, unique=True)
    courses = Set('Course')
    group = Optional('Group')

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    students = Set(Student)
    composite_key(name, semester)

db.generate_mapping(create_tables=True)

with db_session:
    g1 = Group(id=1, major='Math')
    g2 = Group(id=2, major='Physics')
    s1 = Student(id=1, name='S1', email='s1@example.com', group=g1)
    s2 = Student(id=2, name='S2', email='s2@example.com', group=g1)
    s3 = Student(id=3, name='S3', email='s3@example.com', group=g2)
    c1 = Course(name='Math', semester=1)
    c2 = Course(name='Math', semester=2)
    c3 = Course(name='Physics', semester=1)


class TestCRUD(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test_set1(self):
        s1 = Student[1]
        s1.set(name='New name', scholarship=100)
        self.assertEquals(s1.name, 'New name')
        self.assertEquals(s1.scholarship, 100)
    def test_set2(self):
        g1 = Group[1]
        s3 = Student[3]
        g1.set(students=[s3])
        self.assertEquals(s3.group, Group[1])
    def test_set3(self):
        c1 = Course[1]
        c1.set(name='Algebra', semester=3)
    def test_set4(self):
        s1 = Student[1]
        s1.set(name='New name', email='new_email@example.com')
########NEW FILE########
__FILENAME__ = test_crud_raw_sql
from __future__ import with_statement

import unittest
from pony.orm.core import *
from testutils import raises_exception

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    age = Optional(int)
    friends = Set("Student", reverse='friends')
    group = Required("Group")
    bio = Optional("Bio")

class Group(db.Entity):
    dept = Required(int)
    grad_year = Required(int)
    students = Set(Student)
    PrimaryKey(dept, grad_year)

class Bio(db.Entity):
    picture = Optional(buffer)
    desc = Required(unicode)
    Student = Required(Student)

db.generate_mapping(create_tables=True)

class TestRawSql(unittest.TestCase):
    def setUp(self):
        with db_session:
            db.execute('delete from Student')
            db.execute('delete from "Group"')
            db.insert('Group', dept=44, grad_year=1999)
            db.insert('Student', id=1, name='A', age=30, group_dept=44, group_grad_year=1999)
            db.insert('Student', id=2, name='B', age=25, group_dept=44, group_grad_year=1999)
            db.insert('Student', id=3, name='C', age=20, group_dept=44, group_grad_year=1999)
        rollback()
        db_session.__enter__()

    def tearDown(self):
        rollback()
        db_session.__exit__()

    def test1(self):
        students = set(Student.select_by_sql("select id, name, age, group_dept, group_grad_year from Student order by age"))
        self.assertEqual(students, set([Student[3], Student[2], Student[1]]))

    def test2(self):
        students = set(Student.select_by_sql("select id, age, group_dept from Student order by age"))
        self.assertEqual(students, set([Student[3], Student[2], Student[1]]))

    @raises_exception(NameError, "Column x does not belong to entity Student")
    def test3(self):
        students = set(Student.select_by_sql("select id, age, age*2 as x from Student order by age"))
        self.assertEqual(students, set([Student[3], Student[2], Student[1]]))

    @raises_exception(TypeError, 'Lambda function or its text representation expected. Got: 123')
    def test4(self):
        students = Student.select(123)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_db_session
from __future__ import with_statement

import unittest
from datetime import date
from decimal import Decimal
from itertools import count

from pony.orm.core import *
from testutils import *

class TestDBSession(unittest.TestCase):
    def setUp(self):
        self.db = Database('sqlite', ':memory:')
        class X(self.db.Entity):
            a = Required(int)
            b = Optional(int)
        self.X = X
        self.db.generate_mapping(create_tables=True)
        with db_session:
            x1 = X(a=1, b=1)
            x2 = X(a=2, b=2)

    @raises_exception(TypeError, "Pass only keyword arguments to db_session or use db_session as decorator")
    def test_db_session_1(self):
        db_session(1, 2, 3)

    @raises_exception(TypeError, "Pass only keyword arguments to db_session or use db_session as decorator")
    def test_db_session_2(self):
        db_session(1, 2, 3, a=10, b=20)

    def test_db_session_3(self):
        self.assertIs(db_session, db_session())

    def test_db_session_4(self):
        with db_session:
            with db_session:
                self.X(a=3, b=3)
        with db_session:
            self.assertEqual(count(x for x in self.X), 3)

    def test_db_session_decorator_1(self):
        @db_session
        def test():
            self.X(a=3, b=3)
        test()
        with db_session:
            self.assertEqual(count(x for x in self.X), 3)

    def test_db_session_decorator_2(self):
        @db_session
        def test():
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_3(self):
        @db_session(allowed_exceptions=[TypeError])
        def test():
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_4(self):
        @db_session(allowed_exceptions=[ZeroDivisionError])
        def test():
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 3)
        else:
            self.fail()

    @raises_exception(TypeError, "'retry' parameter of db_session must be of integer type. Got: <type 'str'>")
    def test_db_session_decorator_5(self):
        @db_session(retry='foobar')
        def test():
            pass

    @raises_exception(TypeError, "'retry' parameter of db_session must not be negative. Got: -1")
    def test_db_session_decorator_6(self):
        @db_session(retry=-1)
        def test():
            pass

    def test_db_session_decorator_7(self):
        counter = count().next
        @db_session(retry_exceptions=[ZeroDivisionError])
        def test():
            counter()
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            self.assertEqual(counter(), 1)
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_8(self):
        counter = count().next
        @db_session(retry=1, retry_exceptions=[ZeroDivisionError])
        def test():
            counter()
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            self.assertEqual(counter(), 2)
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_9(self):
        counter = count().next
        @db_session(retry=5, retry_exceptions=[ZeroDivisionError])
        def test():
            counter()
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            self.assertEqual(counter(), 6)
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_10(self):
        counter = count().next
        @db_session(retry=3, retry_exceptions=[TypeError])
        def test():
            counter()
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            self.assertEqual(counter(), 1)
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_11(self):
        counter = count().next
        @db_session(retry=5, retry_exceptions=[ZeroDivisionError])
        def test():
            i = counter()
            self.X(a=3, b=3)
            if i < 2: 1/0
        try:
            test()
        except ZeroDivisionError:
            self.fail()
        else:
            self.assertEqual(counter(), 3)
            with db_session:
                self.assertEqual(count(x for x in self.X), 3)

    @raises_exception(TypeError, "The same exception ZeroDivisionError cannot be specified "
                                 "in both allowed and retry exception lists simultaneously")
    def test_db_session_decorator_12(self):
        @db_session(retry=3, retry_exceptions=[ZeroDivisionError],
                             allowed_exceptions=[ZeroDivisionError])
        def test():
            pass

    def test_db_session_decorator_13(self):
        @db_session(allowed_exceptions=lambda e: isinstance(e, ZeroDivisionError))
        def test():
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 3)
        else:
            self.fail()
        
    def test_db_session_decorator_14(self):
        @db_session(allowed_exceptions=lambda e: isinstance(e, TypeError))
        def test():
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_decorator_15(self):
        counter = count().next
        @db_session(retry=3, retry_exceptions=lambda e: isinstance(e, ZeroDivisionError))
        def test():
            i = counter()
            self.X(a=3, b=3)
            1/0
        try:
            test()
        except ZeroDivisionError:
            self.assertEqual(counter(), 4)
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_manager_1(self):
        with db_session:
            self.X(a=3, b=3)
        with db_session:
            self.assertEqual(count(x for x in self.X), 3)

    @raises_exception(TypeError, "@db_session can accept 'retry' parameter "
                      "only when used as decorator and not as context manager")
    def test_db_session_manager_2(self):
        with db_session(retry=3):
            self.X(a=3, b=3)

    def test_db_session_manager_3(self):
        try:
            with db_session(allowed_exceptions=[TypeError]):
                self.X(a=3, b=3)
                1/0
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 2)
        else:
            self.fail()

    def test_db_session_manager_4(self):
        try:
            with db_session(allowed_exceptions=[ZeroDivisionError]):
                self.X(a=3, b=3)
                1/0
        except ZeroDivisionError:
            with db_session:
                self.assertEqual(count(x for x in self.X), 3)
        else:
            self.fail()

    @raises_exception(TypeError, "@db_session can accept 'ddl' parameter "
                      "only when used as decorator and not as context manager")
    def test_db_session_ddl_1(self):
        with db_session(ddl=True):
            pass

    @raises_exception(TransactionError, "test() cannot be called inside of db_session")
    def test_db_session_ddl_2(self):
        @db_session(ddl=True)
        def test():
            pass
        with db_session:
            test()

    def test_db_session_ddl_3(self):
        @db_session(ddl=True)
        def test():
            pass
        test()


db = Database('sqlite', ':memory:')

class Group(db.Entity):
    id = PrimaryKey(int)
    major = Required(unicode)
    students = Set('Student')

class Student(db.Entity):
    name = Required(unicode)
    picture = Optional(buffer, lazy=True)
    group = Required('Group')

db.generate_mapping(create_tables=True)

with db_session:
    g1 = Group(id=1, major='Math')
    g2 = Group(id=2, major='Physics')
    s1 = Student(id=1, name='S1', group=g1)
    s2 = Student(id=2, name='S2', group=g1)
    s3 = Student(id=3, name='S3', group=g2)


class TestDBSessionScope(unittest.TestCase):
    def setUp(self):
        rollback()
    def tearDown(self):
        rollback()
    def test1(self):
        with db_session:
            s1 = Student[1]
        name = s1.name
    @raises_exception(DatabaseSessionIsOver, 'Cannot load attribute Student[1].picture: the database session is over')
    def test2(self):
        with db_session:
            s1 = Student[1]
        picture = s1.picture
    @raises_exception(DatabaseSessionIsOver, 'Cannot load attribute Group[1].major: the database session is over')
    def test3(self):
        with db_session:
            s1 = Student[1]
        group_id = s1.group.id
        major = s1.group.major
    @raises_exception(DatabaseSessionIsOver, 'Cannot assign new value to attribute Student[1].name: the database session is over')
    def test4(self):
        with db_session:
            s1 = Student[1]
        s1.name = 'New name'
    def test5(self):
        with db_session:
            g1 = Group[1]
        self.assertAlmostEquals(str(g1.students), 'StudentSet([...])')
    @raises_exception(DatabaseSessionIsOver, 'Cannot load collection Group[1].students: the database session is over')
    def test6(self):
        with db_session:
            g1 = Group[1]
        l = len(g1.students)
    @raises_exception(DatabaseSessionIsOver, 'Cannot change collection Group[1].Group.students: the database session is over')
    def test7(self):
        with db_session:
            s1 = Student[1]
            g1 = Group[1]
        g1.students.remove(s1)
    @raises_exception(DatabaseSessionIsOver, 'Cannot change collection Group[1].Group.students: the database session is over')
    def test8(self):
        with db_session:
            g2_students = Group[2].students
            g1 = Group[1]
        g1.students = g2_students
    @raises_exception(DatabaseSessionIsOver, 'Cannot change collection Group[1].Group.students: the database session is over')
    def test9(self):
        with db_session:
            s3 = Student[3]
            g1 = Group[1]
        g1.students.add(s3)
    @raises_exception(DatabaseSessionIsOver, 'Cannot change collection Group[1].Group.students: the database session is over')
    def test10(self):
        with db_session:
            g1 = Group[1]
        g1.students.clear()
    @raises_exception(DatabaseSessionIsOver, 'Cannot delete object Student[1]: the database session is over')
    def test11(self):
        with db_session:
            s1 = Student[1]
        s1.delete()
    @raises_exception(DatabaseSessionIsOver, 'Cannot change object Student[1]: the database session is over')
    def test12(self):
        with db_session:
            s1 = Student[1]
        s1.set(name='New name')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_attr_set_monad
from __future__ import with_statement

import unittest
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    scholarship = Optional(int)
    group = Required("Group")
    marks = Set("Mark")

class Group(db.Entity):
    number = PrimaryKey(int)
    department = Required(int)
    students = Set(Student)
    subjects = Set("Subject")

class Subject(db.Entity):
    name = PrimaryKey(unicode)
    groups = Set(Group)
    marks = Set("Mark")

class Mark(db.Entity):
    value = Required(int)
    student = Required(Student)
    subject = Required(Subject)
    PrimaryKey(student, subject)

db.generate_mapping(create_tables=True)

with db_session:
    g41 = Group(number=41, department=101)
    g42 = Group(number=42, department=102)
    g43 = Group(number=43, department=102)
    g44 = Group(number=44, department=102)

    s1 = Student(id=1, name="Joe", scholarship=None, group=g41)
    s2 = Student(id=2, name="Bob", scholarship=100, group=g41)
    s3 = Student(id=3, name="Beth", scholarship=500, group=g41)
    s4 = Student(id=4, name="Jon", scholarship=500, group=g42)
    s5 = Student(id=5, name="Pete", scholarship=700, group=g42)
    s6 = Student(id=6, name="Mary", scholarship=300, group=g44)

    Math = Subject(name="Math")
    Physics = Subject(name="Physics")
    History = Subject(name="History")

    g41.subjects = [ Math, Physics, History ]
    g42.subjects = [ Math, Physics ]
    g43.subjects = [ Physics ]

    Mark(value=5, student=s1, subject=Math)
    Mark(value=4, student=s2, subject=Physics)
    Mark(value=3, student=s2, subject=Math)
    Mark(value=2, student=s2, subject=History)
    Mark(value=1, student=s3, subject=History)
    Mark(value=2, student=s3, subject=Math)
    Mark(value=2, student=s4, subject=Math)
    
class TestAttrSetMonad(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
        
    def tearDown(self):
        rollback()
        db_session.__exit__()

    def test1(self):
        groups = select(g for g in Group if len(g.students) > 2)[:]
        self.assertEqual(groups, [Group[41]])
    def test2(self):
        groups = set(select(g for g in Group if len(g.students.name) >= 2))
        self.assertEqual(groups, set([Group[41], Group[42]]))
    def test3(self):
        groups = select(g for g in Group if len(g.students.marks) > 2)[:]
        self.assertEqual(groups, [Group[41]])
    def test3a(self):
        groups = select(g for g in Group if len(g.students.marks) < 2)[:]
        self.assertEqual(groups, [Group[42], Group[43], Group[44]])
    def test4(self):
        groups = select(g for g in Group if max(g.students.marks.value) <= 2)[:]
        self.assertEqual(groups, [Group[42]])
    def test5(self):
        students = select(s for s in Student if len(s.marks.subject.name) > 5)[:]
        self.assertEqual(students, [])
    def test6(self):
        students = set(select(s for s in Student if len(s.marks.subject) >= 2))
        self.assertEqual(students, set([Student[2], Student[3]]))
    def test8(self):
        students = set(select(s for s in Student if s.group in (g for g in Group if g.department == 101)))
        self.assertEqual(students, set([Student[1], Student[2], Student[3]]))
    def test9(self):
        students = set(select(s for s in Student if s.group not in (g for g in Group if g.department == 101)))
        self.assertEqual(students, set([Student[4], Student[5], Student[6]]))
    def test10(self):
        students = set(select(s for s in Student if s.group in (g for g in Group if g.department == 101)))
        self.assertEqual(students, set([Student[1], Student[2], Student[3]]))
    def test11(self):
        students = set(select(g for g in Group if len(g.subjects.groups.subjects) > 1))
        self.assertEqual(students, set([Group[41], Group[42], Group[43]]))
    def test12(self):
        groups = set(select(g for g in Group if len(g.subjects) >= 2))
        self.assertEqual(groups, set([Group[41], Group[42]]))
    def test13(self):
        groups = set(select(g for g in Group if g.students))
        self.assertEqual(groups, set([Group[41], Group[42], Group[44]]))
    def test14(self):
        groups = set(select(g for g in Group if not g.students))
        self.assertEqual(groups, set([Group[43]]))
    def test15(self):
        groups = set(select(g for g in Group if exists(g.students)))
        self.assertEqual(groups, set([Group[41], Group[42], Group[44]]))
    def test15a(self):
        groups = set(select(g for g in Group if not not exists(g.students)))
        self.assertEqual(groups, set([Group[41], Group[42], Group[44]]))
    def test16(self):
        groups = select(g for g in Group if not exists(g.students))[:]
        self.assertEqual(groups, [Group[43]])
    def test17(self):
        groups = set(select(g for g in Group if 100 in g.students.scholarship))
        self.assertEqual(groups, set([Group[41]]))
    def test18(self):
        groups = set(select(g for g in Group if 100 not in g.students.scholarship))
        self.assertEqual(groups, set([Group[42], Group[43], Group[44]]))
    def test19(self):
        groups = set(select(g for g in Group if not not not 100 not in g.students.scholarship))
        self.assertEqual(groups, set([Group[41]]))
    def test20(self):
        groups = set(select(g for g in Group if exists(s for s in Student if s.group == g and s.scholarship == 500)))
        self.assertEqual(groups, set([Group[41], Group[42]]))
    def test21(self):
        groups = set(select(g for g in Group if g.department is not None))
        self.assertEqual(groups, set([Group[41], Group[42], Group[43], Group[44]]))
    def test21a(self):
        groups = set(select(g for g in Group if not g.department is not None))
        self.assertEqual(groups, set([]))
    def test21b(self):
        groups = set(select(g for g in Group if not not not g.department is None))
        self.assertEqual(groups, set([Group[41], Group[42], Group[43], Group[44]]))
    def test22(self):
        groups = set(select(g for g in Group if 700 in (s.scholarship for s in Student if s.group == g)))
        self.assertEqual(groups, set([Group[42]]))
    def test23a(self):
        groups = set(select(g for g in Group if 700 not in g.students.scholarship))
        self.assertEqual(groups, set([Group[41], Group[43], Group[44]]))
    def test23b(self):
        groups = set(select(g for g in Group if 700 not in (s.scholarship for s in Student if s.group == g)))
        self.assertEqual(groups, set([Group[41], Group[43], Group[44]]))
    @raises_exception(NotImplementedError)
    def test24(self):
        groups = set(select(g for g in Group for g2 in Group if g.students == g2.students))
    def test25(self):
        m1 = Mark[Student[1], Subject["Math"]]
        students = set(select(s for s in Student if m1 in s.marks))
        self.assertEqual(students, set([Student[1]]))
    def test26(self):
        s1 = Student[1]
        groups = set(select(g for g in Group if s1 in g.students))
        self.assertEqual(groups, set([Group[41]]))
    @raises_exception(AttributeError, 'g.students.name.foo')
    def test27(self):
        select(g for g in Group if g.students.name.foo == 1)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_date
from __future__ import with_statement

import unittest
from datetime import date, datetime
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Entity1(db.Entity):
	a = PrimaryKey(int)
	b = Required(date)
	c = Required(datetime)

db.generate_mapping(create_tables=True)

with db_session:
    Entity1(a=1, b=date(2009, 10, 20), c=datetime(2009, 10, 20, 10, 20, 30))
    Entity1(a=2, b=date(2010, 10, 21), c=datetime(2010, 10, 21, 10, 21, 31))
    Entity1(a=3, b=date(2011, 11, 22), c=datetime(2011, 11, 22, 10, 20, 32))

class TestDate(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test_create(self):
        e1 = Entity1(a=4, b=date(2011, 10, 20), c=datetime(2009, 10, 20, 10, 20, 30))
        self.assert_(True)
    def test_date_year(self):
        result = select(e for e in Entity1 if e.b.year > 2009)
        self.assertEqual(len(result), 2)
    def test_date_month(self):
        result = select(e for e in Entity1 if e.b.month == 10)
        self.assertEqual(len(result), 2)
    def test_date_day(self):
        result = select(e for e in Entity1 if e.b.day == 22)
        self.assertEqual(len(result), 1)
    def test_datetime_year(self):
        result = select(e for e in Entity1 if e.c.year > 2009)
        self.assertEqual(len(result), 2)
    def test_datetime_month(self):
        result = select(e for e in Entity1 if e.c.month == 10)
        self.assertEqual(len(result), 2)
    def test_datetime_day(self):
        result = select(e for e in Entity1 if e.c.day == 22)
        self.assertEqual(len(result), 1)
    def test_datetime_hour(self):
        result = select(e for e in Entity1 if e.c.hour == 10)
        self.assertEqual(len(result), 3)
    def test_datetime_minute(self):
        result = select(e for e in Entity1 if e.c.minute == 20)
        self.assertEqual(len(result), 2)
    def test_datetime_second(self):
        result = select(e for e in Entity1 if e.c.second == 30)
        self.assertEqual(len(result), 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_exceptions
from __future__ import with_statement

import unittest
from datetime import date
from decimal import Decimal
from pony.orm.core import *
from pony.orm.sqltranslation import IncomparableTypesError
from testutils import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    dob = Optional(date)
    gpa = Optional(float)
    scholarship = Optional(Decimal, 7, 2)
    group = Required('Group')
    courses = Set('Course')

class Group(db.Entity):
    number = PrimaryKey(int)
    students = Set(Student)
    dept = Required('Department')

class Department(db.Entity):
    number = PrimaryKey(int)
    groups = Set(Group)

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    PrimaryKey(name, semester)
    students = Set(Student)

db.generate_mapping(create_tables=True)

with db_session:
    d1 = Department(number=44)
    g1 = Group(number=101, dept=d1)
    Student(name='S1', group=g1)
    Student(name='S2', group=g1)
    Student(name='S3', group=g1)

class TestSQLTranslatorExceptions(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    @raises_exception(NotImplementedError, 'for x in s.name')
    def test1(self):
        x = 10
        select(s for s in Student for x in s.name)
    @raises_exception(TranslationError, "Inside declarative query, iterator must be entity. Got: for i in x")
    def test2(self):
        x = [1, 2, 3]
        select(s for s in Student for i in x)
    @raises_exception(TranslationError, "Inside declarative query, iterator must be entity. Got: for s2 in g.students")
    def test3(self):
        g = Group[101]
        select(s for s in Student for s2 in g.students)
    @raises_exception(NotImplementedError, "*args is not supported")
    def test4(self):
        args = 'abc'
        select(s for s in Student if s.name.upper(*args))
    @raises_exception(TypeError, "Expression {'a':'b', 'c':'d'} has unsupported type 'dict'")
    def test5(self):
        select(s for s in Student if s.name.upper(**{'a':'b', 'c':'d'}))
    @raises_exception(ExprEvalError, "1 in 2 raises TypeError: argument of type 'int' is not iterable")
    def test6(self):
        select(s for s in Student if 1 in 2)
    @raises_exception(NotImplementedError, 'Group[s.group.number]')
    def test7(self):
        select(s for s in Student if Group[s.group.number].dept.number == 44)
    # @raises_exception(TypeError, "Invalid count of attrs in Group primary key (2 instead of 1)")
    # def test8(self):
    #     select(s for s in Student if Group[s.group.number, 123].dept.number == 44)
    @raises_exception(ExprEvalError, "Group[123, 456].dept.number == 44 raises TypeError: Invalid count of attrs in Group primary key (2 instead of 1)")
    def test9(self):
        select(s for s in Student if Group[123, 456].dept.number == 44)
    @raises_exception(ExprEvalError, "Course[123] raises TypeError: Invalid count of attrs in Course primary key (1 instead of 2)")
    def test10(self):
        select(s for s in Student if Course[123] in s.courses)
    @raises_exception(TypeError, "Incomparable types 'unicode' and 'float' in expression: s.name < s.gpa")
    def test11(self):
        select(s for s in Student if s.name < s.gpa)
    @raises_exception(ExprEvalError, "Group(101) raises TypeError: Group constructor accept only keyword arguments. Got: 1 positional argument")
    def test12(self):
        select(s for s in Student if s.group == Group(101))
    @raises_exception(ExprEvalError, "Group[date(2011, 1, 2)] raises TypeError: Value type for attribute Group.number must be int. Got: <type 'datetime.date'>")
    def test13(self):
        select(s for s in Student if s.group == Group[date(2011, 1, 2)])
    @raises_exception(TypeError, "Unsupported operand types 'int' and 'unicode' for operation '+' in expression: s.group.number + s.name")
    def test14(self):
        select(s for s in Student if s.group.number + s.name < 0)
    @raises_exception(TypeError, "Unsupported operand types 'Decimal' and 'float' for operation '+' in expression: s.scholarship + 1.1")
    def test15(self):
        select(s for s in Student if s.scholarship + 1.1 > 10)
    @raises_exception(TypeError, "Unsupported operand types 'Decimal' and 'AsciiStr' for operation '**' in expression: s.scholarship ** 'abc'")
    def test16(self):
        select(s for s in Student if s.scholarship ** 'abc' > 10)
    @raises_exception(TypeError, "Unsupported operand types 'unicode' and 'int' for operation '+' in expression: s.name + 2")
    def test17(self):
        select(s for s in Student if s.name + 2 > 10)
    @raises_exception(TypeError, "Step is not supported in s.name[1:3:5]")
    def test18(self):
        select(s for s in Student if s.name[1:3:5] == 'A')
    @raises_exception(TypeError, "Invalid type of start index (expected 'int', got 'AsciiStr') in string slice s.name['a':1]")
    def test19(self):
        select(s for s in Student if s.name['a':1] == 'A')
    @raises_exception(TypeError, "Invalid type of stop index (expected 'int', got 'AsciiStr') in string slice s.name[1:'a']")
    def test20(self):
        select(s for s in Student if s.name[1:'a'] == 'A')
    @raises_exception(NotImplementedError, "Negative indices are not supported in string slice s.name[-1:1]")
    def test21(self):
        select(s for s in Student if s.name[-1:1] == 'A')
    @raises_exception(TypeError, "String indices must be integers. Got 'AsciiStr' in expression s.name['a']")
    def test22(self):
        select(s.name for s in Student if s.name['a'] == 'h')
    @raises_exception(TypeError, "Incomparable types 'int' and 'unicode' in expression: 1 in s.name")
    def test23(self):
        select(s.name for s in Student if 1 in s.name)
    @raises_exception(TypeError, "Expected 'unicode' argument but got 'int' in expression s.name.startswith(1)")
    def test24(self):
        select(s.name for s in Student if s.name.startswith(1))
    @raises_exception(TypeError, "Expected 'unicode' argument but got 'int' in expression s.name.endswith(1)")
    def test25(self):
        select(s.name for s in Student if s.name.endswith(1))
    @raises_exception(TypeError, "'chars' argument must be of 'unicode' type in s.name.strip(1), got: 'int'")
    def test26(self):
        select(s.name for s in Student if s.name.strip(1))
    @raises_exception(AttributeError, "s.group.foo")
    def test27(self):
        select(s.name for s in Student if s.group.foo.bar == 10)
    @raises_exception(ExprEvalError, "g.dept.foo.bar raises AttributeError: 'Department' object has no attribute 'foo'")
    def test28(self):
        g = Group[101]
        select(s for s in Student if s.name == g.dept.foo.bar)
    @raises_exception(ExprEvalError, "date('2011', 1, 1) raises TypeError: an integer is required")
    def test29(self):
        select(s for s in Student if s.dob < date('2011', 1, 1))
    @raises_exception(NotImplementedError, "date(s.id, 1, 1)")
    def test30(self):
        select(s for s in Student if s.dob < date(s.id, 1, 1))
    @raises_exception(ExprEvalError, "max() raises TypeError: max expected 1 arguments, got 0")
    def test31(self):
        select(s for s in Student if s.id < max())
    #@raises_exception(TypeError, "Value of type 'buffer' is not valid as argument of 'max' function in expression max(x, y)")
    # def test32(self):
    #     x = buffer('a')
    #     y = buffer('b')
    #    select(s for s in Student if max(x, y) == x)
    # @raises_exception(TypeError, "Incomparable types 'int' and 'AsciiStr' in expression: min(1, 'a')")
    # def test33(self):
    #     select(s for s in Student if min(1, 'a') == 1)
    # @raises_exception(TypeError, "Incomparable types 'AsciiStr' and 'int' in expression: min('a', 1)")
    # def test33a(self):
    #     select(s for s in Student if min('a', 1) == 1)
    # @raises_exception(TypeError, "'select' function expects generator expression, got: select('* from Students')")
    # def test34(self):
    #    select(s for s in Student if s.group in select("* from Students"))
    # @raises_exception(TypeError, "'exists' function expects generator expression or collection, got: exists('g for g in Group')")
    # def test35(self): ###
    #    select(s for s in Student if exists("g for g in Group"))
    @raises_exception(TypeError, "Incomparable types 'Student' and 'Course' in expression: s in s.courses")
    def test36(self):
        select(s for s in Student if s in s.courses)
    @raises_exception(AttributeError, "s.courses.name.foo")
    def test37(self):
        select(s for s in Student if 'x' in s.courses.name.foo.bar)
    @raises_exception(AttributeError, "s.courses.foo")
    def test38(self):
        select(s for s in Student if 'x' in s.courses.foo.bar)
    @raises_exception(TypeError, "Function sum() expects query or items of numeric type, got 'unicode' in sum(s.courses.name)")
    def test39(self):
        select(s for s in Student if sum(s.courses.name) > 10)
    @raises_exception(TypeError, "Function sum() expects query or items of numeric type, got 'unicode' in sum(c.name for c in s.courses)")
    def test40(self):
        select(s for s in Student if sum(c.name for c in s.courses) > 10)
    @raises_exception(TypeError, "Function sum() expects query or items of numeric type, got 'unicode' in sum(c.name for c in s.courses)")
    def test41(self):
        select(s for s in Student if sum(c.name for c in s.courses) > 10)
    @raises_exception(TypeError, "Function avg() expects query or items of numeric type, got 'unicode' in avg(c.name for c in s.courses)")
    def test42(self):
        select(s for s in Student if avg(c.name for c in s.courses) > 10 and len(s.courses) > 1)
    @raises_exception(TypeError, "strip() takes at most 1 argument (3 given)")
    def test43(self):
        select(s for s in Student if s.name.strip(1, 2, 3))
    @raises_exception(ExprEvalError, "len(1, 2) == 3 raises TypeError: len() takes exactly one argument (2 given)")
    def test44(self):
        select(s for s in Student if len(1, 2) == 3)
    # @raises_exception(NotImplementedError, "Group[101].students")
    # def test45(self):
    #     select(s for s in Student if s in Group[101].students)
    @raises_exception(TypeError, "Function sum() expects query or items of numeric type, got 'Student' in sum(s for s in Student if s.group == g)")
    def test46(self):
        select(g for g in Group if sum(s for s in Student if s.group == g) > 1)
    @raises_exception(TypeError, "Function avg() expects query or items of numeric type, got 'Student' in avg(s for s in Student if s.group == g)")
    def test47(self):
        select(g for g in Group if avg(s for s in Student if s.group == g) > 1)
    @raises_exception(TypeError, "Function min() cannot be applied to type 'Student' in min(s for s in Student if s.group == g)")
    def test48(self):
        select(g for g in Group if min(s for s in Student if s.group == g) > 1)
    @raises_exception(TypeError, "Function max() cannot be applied to type 'Student' in max(s for s in Student if s.group == g)")
    def test49(self):
        select(g for g in Group if max(s for s in Student if s.group == g) > 1)
    # @raises_exception(TypeError, "Incomparable types 'Decimal' and 'bool' in expression: s.scholarship == (True or False and not True)")
    # def test50(self):
    #     select(s for s in Student if s.scholarship == (True or False and not True))
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > +3")
    def test51(self): ###
        select(s for s in Student if s.name > +3)
    @raises_exception(TypeError, "Expression {'a':'b'} has unsupported type 'dict'")
    def test52(self):
        select(s for s in Student if s.name == {'a' : 'b'})
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > a ^ 2")
    def test53(self): ###
        a = 1
        select(s for s in Student if s.name > a ^ 2)
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > a | 2")
    def test54(self): ###
        a = 1
        select(s for s in Student if s.name > a | 2)
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > a & 2")
    def test55(self):
        a = 1
        select(s for s in Student if s.name > a & 2)
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > a << 2")
    def test56(self): ###
        a = 1
        select(s for s in Student if s.name > a << 2)
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > a >> 2")
    def test57(self): ###
        a = 1
        select(s for s in Student if s.name > a >> 2)
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > (a * 2) % 4")
    def test58(self): ###
        a = 1
        select(s for s in Student if s.name > a * 2 % 4)
    @raises_exception(IncomparableTypesError, "Incomparable types 'unicode' and 'int' in expression: s.name > ~a")
    def test59(self): ###
        a = 1
        select(s for s in Student if s.name > ~a)
    @raises_exception(TypeError, "Incomparable types 'unicode' and 'int' in expression: s.name > 1 / a - 3")
    def test60(self):
        a = 1
        select(s for s in Student if s.name > 1 / a - 3)
    @raises_exception(TypeError, "Incomparable types 'unicode' and 'int' in expression: s.name > -a")
    def test61(self):
        a = 1
        select(s for s in Student if s.name > -a)
    @raises_exception(TypeError, "Incomparable types 'unicode' and 'list' in expression: s.name == [1, (2,)]")
    def test62(self):
        select(s for s in Student if s.name == [1, (2,)])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_func_monad
from __future__ import with_statement

import unittest
from datetime import date, datetime
from decimal import Decimal
from pony.orm.core import *
from pony.orm.sqltranslation import IncomparableTypesError
from testutils import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    id = PrimaryKey(int)
    name = Required(unicode)
    dob = Required(date)
    last_visit = Required(datetime)
    scholarship = Required(Decimal, 6, 2)
    phd = Required(bool)
    group = Required('Group')

class Group(db.Entity):
    number = PrimaryKey(int)
    students = Set(Student)


db.generate_mapping(create_tables=True)

with db_session:
    g1 = Group(number=1)
    g2 = Group(number=2)

    Student(id=1, name="AA", dob=date(1981, 01, 01), last_visit=datetime(2011, 01, 01, 11, 11, 11),
                   scholarship=Decimal("0"), phd=True, group=g1)

    Student(id=2, name="BB", dob=date(1982, 02, 02), last_visit=datetime(2011, 02, 02, 12, 12, 12),
                   scholarship=Decimal("202.2"), phd=True, group=g1)

    Student(id=3, name="CC", dob=date(1983, 03, 03), last_visit=datetime(2011, 03, 03, 13, 13, 13),
                   scholarship=Decimal("303.3"), phd=False, group=g1)

    Student(id=4, name="DD", dob=date(1984, 04, 04), last_visit=datetime(2011, 04, 04, 14, 14, 14),
                   scholarship=Decimal("404.4"), phd=False, group=g2)

    Student(id=5, name="EE", dob=date(1985, 05, 05), last_visit=datetime(2011, 05, 05, 15, 15, 15),
                   scholarship=Decimal("505.5"), phd=False, group=g2)


class TestFuncMonad(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test_minmax1(self):
        result = set(select(s for s in Student if max(s.id, 3) == 3 ))
        self.assertEqual(result, set([Student[1], Student[2], Student[3]]))
    def test_minmax2(self):
        result = set(select(s for s in Student if min(s.id, 3) == 3 ))
        self.assertEqual(result, set([Student[4], Student[5], Student[3]]))
    def test_minmax3(self):
        result = set(select(s for s in Student if max(s.name, "CC") == "CC" ))
        self.assertEqual(result, set([Student[1], Student[2], Student[3]]))
    def test_minmax4(self):
        result = set(select(s for s in Student if min(s.name, "CC") == "CC" ))
        self.assertEqual(result, set([Student[4], Student[5], Student[3]]))
    @raises_exception(TypeError)
    def test_minmax5(self):
        x = chr(128)
        result = set(select(s for s in Student if min(s.name, x) == "CC" ))
    @raises_exception(TypeError)
    def test_minmax6(self):
        x = chr(128)
        result = set(select(s for s in Student if min(s.name, x, "CC") == "CC" ))
    def test_minmax5(self):
        result = set(select(s for s in Student if min(s.phd, 2) == 2 ))
    def test_date_func1(self):
        result = set(select(s for s in Student if s.dob >= date(1983, 3, 3)))
        self.assertEqual(result, set([Student[3], Student[4], Student[5]]))
    @raises_exception(ExprEvalError, "date(1983, 'three', 3) raises TypeError: an integer is required")
    def test_date_func2(self):
        result = set(select(s for s in Student if s.dob >= date(1983, 'three', 3)))
    # @raises_exception(NotImplementedError)
    # def test_date_func3(self):
    #     d = 3
    #     result = set(select(s for s in Student if s.dob >= date(1983, d, 3)))
    def test_datetime_func1(self):
        result = set(select(s for s in Student if s.last_visit >= date(2011, 3, 3)))
        self.assertEqual(result, set([Student[3], Student[4], Student[5]]))
    def test_datetime_func2(self):
        result = set(select(s for s in Student if s.last_visit >= datetime(2011, 3, 3)))
        self.assertEqual(result, set([Student[3], Student[4], Student[5]]))
    def test_datetime_func3(self):
        result = set(select(s for s in Student if s.last_visit >= datetime(2011, 3, 3, 13, 13, 13)))
        self.assertEqual(result, set([Student[3], Student[4], Student[5]]))
    @raises_exception(ExprEvalError, "date(1983, 'three', 3) raises TypeError: an integer is required")
    def test_datetime_func4(self):
        result = set(select(s for s in Student if s.last_visit >= date(1983, 'three', 3)))
    # @raises_exception(NotImplementedError)
    # def test_datetime_func5(self):
    #     d = 3
    #     result = set(select(s for s in Student if s.last_visit >= date(1983, d, 3)))
    def test_datetime_now1(self):
        result = set(select(s for s in Student if s.dob < date.today()))
        self.assertEqual(result, set([Student[1], Student[2], Student[3], Student[4], Student[5]]))
    @raises_exception(ExprEvalError, "1 < datetime.now() raises TypeError: can't compare datetime.datetime to int")
    def test_datetime_now2(self):
        select(s for s in Student if 1 < datetime.now())
    def test_datetime_now3(self):
        result = set(select(s for s in Student if s.dob < datetime.today()))
        self.assertEqual(result, set([Student[1], Student[2], Student[3], Student[4], Student[5]]))
    def test_decimal_func(self):
        result = set(select(s for s in Student if s.scholarship >= Decimal("303.3")))
        self.assertEqual(result, set([Student[3], Student[4], Student[5]]))
    def test_concat_1(self):
        result = set(select(concat(s.name, ':', s.dob.year, ':', s.scholarship) for s in Student))
        self.assertEqual(result, set(['AA:1981:0', 'BB:1982:202.2', 'CC:1983:303.3', 'DD:1984:404.4', 'EE:1985:505.5']))
    @raises_exception(TranslationError, 'Invalid argument of concat() function: g.students')
    def test_concat_2(self):
        result = set(select(concat(g.number, g.students) for g in Group))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_join_optimization
import unittest
from datetime import date
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Department(db.Entity):
    name = Required(str)
    groups = Set('Group')
    courses = Set('Course')

class Group(db.Entity):
    number = PrimaryKey(int)
    dept = Required(Department)
    major = Required(unicode)
    students = Set("Student")

class Course(db.Entity):
    name = Required(unicode)
    dept = Required(Department)
    semester = Required(int)
    credits = Required(int)
    students = Set("Student")
    PrimaryKey(name, semester)

class Student(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    dob = Required(date)
    picture = Optional(buffer)
    gpa = Required(float, default=0)
    group = Required(Group)
    courses = Set(Course)


db.generate_mapping(create_tables=True)

class TestM2MOptimization(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test1(self):
        q = select(s for s in Student if len(s.courses) > 2)
        self.assertEqual(Course._table_ not in flatten(q._translator.conditions), True)
    def test2(self):
        q = select(s for s in Student if max(s.courses.semester) > 2)
        self.assertEqual(Course._table_ not in flatten(q._translator.conditions), True)
    # def test3(self):
    #     q = select(s for s in Student if max(s.courses.credits) > 2)
    #     self.assertEqual(Course._table_ in flatten(q._translator.conditions), True)
    #     self.assertEqual(Course.students.table in flatten(q._translator.conditions), True)
    def test4(self):
        q = select(g for g in Group if sum(g.students.gpa) > 5)
        self.assertEqual(Group._table_ not in flatten(q._translator.conditions), True)
    def test5(self):
        q = select(s for s in Student if s.group.number == 1 or s.group.major == '1')
        self.assertEqual(Group._table_ in flatten(q._translator.subquery.from_ast), True)
    # def test6(self): ###  Broken with ExprEvalError: Group[101] raises ObjectNotFound: Group[101]
    #    q = select(s for s in Student if s.group == Group[101])
    #    self.assertEqual(Group._table_ not in flatten(q._translator.subquery.from_ast), True)
    def test7(self):
        q = select(s for s in Student if sum(c.credits for c in Course if s.group.dept == c.dept) > 10)
        objects = q[:]
        self.assertEqual(str(q._translator.subquery.from_ast),
            "['FROM', ['s', 'TABLE', 'Student'], ['group-1', 'TABLE', 'Group', ['EQ', ['COLUMN', 's', 'group'], ['COLUMN', 'group-1', 'number']]]]")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_method_monad
from __future__ import with_statement

import unittest
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    scholarship = Optional(int)

db.generate_mapping(create_tables=True)

with db_session:
    Student(id=1, name="Joe", scholarship=None)
    Student(id=2, name=" Bob ", scholarship=100)
    Student(id=3, name=" Beth ", scholarship=500)
    Student(id=4, name="Jon", scholarship=500)
    Student(id=5, name="Pete", scholarship=700)

class TestMethodMonad(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()

    def tearDown(self):
        rollback()
        db_session.__exit__()

    def test1(self):
        students = set(select(s for s in Student if not s.name.startswith('J')))
        self.assertEqual(students, set([Student[2], Student[3], Student[5]]))

    def test1a(self):
        x = "Pe"
        students = select(s for s in Student if s.name.startswith(x))[:]
        self.assertEqual(students, [Student[5]])

    def test1b(self):
        students = set(select(s for s in Student if not not s.name.startswith('J')))
        self.assertEqual(students, set([Student[1], Student[4]]))

    def test1c(self):
        students = set(select(s for s in Student if not not not s.name.startswith('J')))
        self.assertEqual(students, set([Student[2], Student[3], Student[5]]))

    def test2(self):
        students = set(select(s for s in Student if s.name.endswith('e')))
        self.assertEqual(students, set([Student[1], Student[5]]))

    def test2a(self):
        x = "te"
        students = select(s for s in Student if s.name.endswith(x))[:]
        self.assertEqual(students, [Student[5]])

    def test3(self):
        students = select(s for s in Student if s.name.strip() == 'Beth')[:]
        self.assertEqual(students, [Student[3]])

    @raises_exception(TypeError, "'chars' argument must be of 'unicode' type in s.name.strip(5), got: 'int'")
    def test3a(self):
        students = select(s for s in Student if s.name.strip(5) == 'Beth')[:]

    def test4(self):
        students = select(s for s in Student if s.name.rstrip('n') == 'Jo')[:]
        self.assertEqual(students, [Student[4]])

    def test5(self):
        students = select(s for s in Student if s.name.lstrip('P') == 'ete')[:]
        self.assertEqual(students, [Student[5]])

    @raises_exception(TypeError, "Expected 'unicode' argument but got 'int' in expression s.name.startswith(5)")
    def test6(self):
        students = select(s for s in Student if not s.name.startswith(5))[:]

    @raises_exception(TypeError, "Expected 'unicode' argument but got 'int' in expression s.name.endswith(5)")
    def test7(self):
        students = select(s for s in Student if not s.name.endswith(5))[:]

    def test8(self):
        result = select(s for s in Student if s.name.upper() == "JOE")[:]
        self.assertEqual(result, [Student[1]])

    def test9(self):
        result = select(s for s in Student if s.name.lower() == "joe")[:]
        self.assertEqual(result, [Student[1]])

    @raises_exception(AttributeError, "'unicode' object has no attribute 'unknown'")
    def test10(self):
        result = set(select(s for s in Student if s.name.unknown() == "joe"))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_object_flat_monad
from __future__ import with_statement

import unittest
from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    scholarship = Optional(int)
    group = Required("Group")
    marks = Set("Mark")

class Group(db.Entity):
    number = PrimaryKey(int)
    department = Required(int)
    students = Set(Student)
    subjects = Set("Subject")

class Subject(db.Entity):
    name = PrimaryKey(unicode)
    groups = Set(Group)
    marks = Set("Mark")

class Mark(db.Entity):
    value = Required(int)
    student = Required(Student)
    subject = Required(Subject)
    PrimaryKey(student, subject)

db.generate_mapping(create_tables=True)

with db_session:
    Math = Subject(name="Math")
    Physics = Subject(name="Physics")
    History = Subject(name="History")

    g41 = Group(number=41, department=101, subjects=[ Math, Physics, History ])
    g42 = Group(number=42, department=102, subjects=[ Math, Physics ])
    g43 = Group(number=43, department=102, subjects=[ Physics ])

    s1 = Student(id=1, name="Joe", scholarship=None, group=g41)
    s2 = Student(id=2, name="Bob", scholarship=100, group=g41)
    s3 = Student(id=3, name="Beth", scholarship=500, group=g41)
    s4 = Student(id=4, name="Jon", scholarship=500, group=g42)
    s5 = Student(id=5, name="Pete", scholarship=700, group=g42)

    Mark(value=5, student=s1, subject=Math)
    Mark(value=4, student=s2, subject=Physics)
    Mark(value=3, student=s2, subject=Math)
    Mark(value=2, student=s2, subject=History)
    Mark(value=1, student=s3, subject=History)
    Mark(value=2, student=s3, subject=Math)
    Mark(value=2, student=s4, subject=Math)

class TestObjectFlatMonad(unittest.TestCase):
    @db_session
    def test1(self):
        result = set(select(s.groups for s in Subject if len(s.name) == 4))
        self.assertEqual(result, set([Group[41], Group[42]]))

    @db_session
    def test2(self):
        result = set(select(g.students for g in Group if g.department == 102))
        self.assertEqual(result, set([Student[5], Student[4]]))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_orderby_limit
from __future__ import with_statement

import unittest
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    scholarship = Optional(int)
    group = Required(int)

db.generate_mapping(create_tables=True)

with db_session:
    Student(id=1, name="B", scholarship=None, group=41)
    Student(id=2, name="C", scholarship=700, group=41)
    Student(id=3, name="A", scholarship=500, group=42)
    Student(id=4, name="D", scholarship=500, group=43)
    Student(id=5, name="E", scholarship=700, group=42)

class TestOrderbyLimit(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()

    def tearDown(self):
        rollback()
        db_session.__exit__()

    def test1(self):
        students = set(select(s for s in Student).order_by(Student.name))
        self.assertEqual(students, set([Student[3], Student[1], Student[2], Student[4], Student[5]]))

    def test2(self):
        students = set(select(s for s in Student).order_by(Student.name.asc))
        self.assertEqual(students, set([Student[3], Student[1], Student[2], Student[4], Student[5]]))

    def test3(self):
        students = set(select(s for s in Student).order_by(Student.id.desc))
        self.assertEqual(students, set([Student[5], Student[4], Student[3], Student[2], Student[1]]))

    def test4(self):
        students = set(select(s for s in Student).order_by(Student.scholarship.asc, Student.group.desc))
        self.assertEqual(students, set([Student[1], Student[4], Student[3], Student[5], Student[2]]))

    def test5(self):
        students = set(select(s for s in Student).order_by(Student.name).limit(3))
        self.assertEqual(students, set([Student[3], Student[1], Student[2]]))

    def test6(self):
        students = set(select(s for s in Student).order_by(Student.name).limit(3, 1))
        self.assertEqual(students, set([Student[1], Student[2], Student[4]]))

    def test7(self):
        q = select(s for s in Student).order_by(Student.name).limit(3, 1)
        students = set(q)
        self.assertEqual(students, set([Student[1], Student[2], Student[4]]))
        students = set(q)
        self.assertEqual(students, set([Student[1], Student[2], Student[4]]))

    # @raises_exception(TypeError, "query.order_by() arguments must be attributes. Got: 'name'")
    # now generate: ExprEvalError: name raises NameError: name 'name' is not defined
    # def test8(self):
    # students = select(s for s in Student).order_by("name")

    def test9(self):
        students = set(select(s for s in Student).order_by(Student.id)[1:4])
        self.assertEqual(students, set([Student[2], Student[3], Student[4]]))

    def test10(self):
        students = set(select(s for s in Student).order_by(Student.id)[:4])
        self.assertEqual(students, set([Student[1], Student[2], Student[3], Student[4]]))

    @raises_exception(TypeError, "Parameter 'stop' of slice object should be specified")
    def test11(self):
        students = select(s for s in Student).order_by(Student.id)[4:]

    @raises_exception(TypeError, "Parameter 'start' of slice object cannot be negative")
    def test12(self):
        students = select(s for s in Student).order_by(Student.id)[-3:2]

    @raises_exception(TypeError, 'If you want apply index to query, convert it to list first')
    def test13(self):
        students = select(s for s in Student).order_by(Student.id)[3]
        self.assertEqual(students, Student[4])

    # @raises_exception(TypeError, 'If you want apply index to query, convert it to list first')
    # def test14(self):
    #    students = select(s for s in Student).order_by(Student.id)["a"]

    def test15(self):
        students = set(select(s for s in Student).order_by(Student.id)[0:4][1:3])
        self.assertEqual(students, set([Student[2], Student[3]]))

    def test16(self):
        students = set(select(s for s in Student).order_by(Student.id)[0:4][1:])
        self.assertEqual(students, set([Student[2], Student[3], Student[4]]))

    def test17(self):
        students = set(select(s for s in Student).order_by(Student.id)[:4][1:])
        self.assertEqual(students, set([Student[2], Student[3], Student[4]]))

    def test18(self):
        students = set(select(s for s in Student).order_by(Student.id)[:])
        self.assertEqual(students, set([Student[1], Student[2], Student[3], Student[4], Student[5]]))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_query_set_monad
from __future__ import with_statement

import unittest
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Group(db.Entity):
    id = PrimaryKey(int)
    students = Set('Student')

class Student(db.Entity):
    name = Required(unicode)
    group = Required('Group')
    scholarship = Required(int, default=0)
    courses = Set('Course')

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    PrimaryKey(name, semester)
    students = Set('Student')

db.generate_mapping(create_tables=True)

with db_session:
    g1 = Group(id=1)
    g2 = Group(id=2)
    s1 = Student(id=1, name='S1', group=g1, scholarship=0)
    s2 = Student(id=2, name='S2', group=g1, scholarship=100)
    s3 = Student(id=3, name='S3', group=g2, scholarship=500)
    c1 = Course(name='C1', semester=1, students=[s1, s2])
    c2 = Course(name='C2', semester=1, students=[s2, s3])
    c3 = Course(name='C3', semester=2, students=[s3])


class TestQuerySetMonad(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()

    def tearDown(self):
        rollback()
        db_session.__exit__()

    def test_len(self):
        result = set(select(g for g in Group if len(g.students) > 1))
        self.assertEqual(result, set([Group[1]]))

    def test_len_2(self):
        result = set(select(g for g in Group if len(s for s in Student if s.group == g) > 1))
        self.assertEqual(result, set([Group[1]]))

    def test_len_3(self):
        result = set(select(g for g in Group if len(s.name for s in Student if s.group == g) > 1))
        self.assertEqual(result, set([Group[1]]))

    def test_count_1(self):
        result = set(select(g for g in Group if count(s.name for s in g.students) > 1))
        self.assertEqual(result, set([Group[1]]))

    def test_count_2(self):
        result = set(select(g for g in Group if select(s.name for s in g.students).count() > 1))
        self.assertEqual(result, set([Group[1]]))

    def test_count_3(self):
        result = set(select(s for s in Student if count(c for c in s.courses) > 1))
        self.assertEqual(result, set([Student[2], Student[3]]))

    def test_count_4(self):
        result = set(select(c for c in Course if count(s for s in c.students) > 1))
        self.assertEqual(result, set([Course['C1', 1], Course['C2', 1]]))

    @raises_exception(TypeError)
    def test_sum_1(self):
        result = set(select(g for g in Group if sum(s for s in Student if s.group == g) > 1))
        self.assertEqual(result, set([]))

    @raises_exception(TypeError)
    def test_sum_2(self):
        select(g for g in Group if sum(s.name for s in Student if s.group == g) > 1)

    def test_sum_3(self):
        result = set(select(g for g in Group if sum(s.scholarship for s in Student if s.group == g) > 500))
        self.assertEqual(result, set([]))

    def test_sum_4(self):
        result = set(select(g for g in Group if select(s.scholarship for s in g.students).sum() > 200))
        self.assertEqual(result, set([Group[2]]))

    def test_min_1(self):
        result = set(select(g for g in Group if min(s.name for s in Student if s.group == g) == 'S1'))
        self.assertEqual(result, set([Group[1]]))

    @raises_exception(TypeError)
    def test_min_2(self):
        select(g for g in Group if min(s for s in Student if s.group == g) == None)

    def test_min_3(self):
        result = set(select(g for g in Group if select(s.scholarship for s in g.students).min() == 0))
        self.assertEqual(result, set([Group[1]]))

    def test_max_1(self):
        result = set(select(g for g in Group if max(s.scholarship for s in Student if s.group == g) > 100))
        self.assertEqual(result, set([Group[2]]))

    @raises_exception(TypeError)
    def test_max_2(self):
        select(g for g in Group if max(s for s in Student if s.group == g) == None)

    def test_max_3(self):
        result = set(select(g for g in Group if select(s.scholarship for s in g.students).max() == 100))
        self.assertEqual(result, set([Group[1]]))

    def test_avg_1(self):
        result = select(g for g in Group if avg(s.scholarship for s in Student if s.group == g) == 50)[:]
        self.assertEqual(result, [Group[1]])

    def test_avg_2(self):
        result = set(select(g for g in Group if select(s.scholarship for s in g.students).avg() == 50))
        self.assertEqual(result, set([Group[1]]))

    def test_exists(self):
        result = set(select(g for g in Group if exists(s for s in g.students if s.name == 'S1')))
        self.assertEqual(result, set([Group[1]]))

    def test_negate(self):
        result = set(select(g for g in Group if not(s.scholarship for s in Student if s.group == g)))
        self.assertEqual(result, set([]))

    def test_no_conditions(self):
        students = set(select(s for s in Student if s.group in (g for g in Group)))
        self.assertEqual(students, set([Student[1], Student[2], Student[3]]))

    def test_no_conditions_2(self):
        students = set(select(s for s in Student if s.scholarship == max(s.scholarship for s in Student)))
        self.assertEqual(students, set([Student[3]]))

    def test_hint_join_1(self):
        result = set(select(s for s in Student if JOIN(s.group in select(g for g in Group if g.id < 2))))
        self.assertEqual(result, set([Student[1], Student[2]]))

    def test_hint_join_2(self):
        result = set(select(s for s in Student if JOIN(s.group not in select(g for g in Group if g.id < 2))))
        self.assertEqual(result, set([Student[3]]))

    def test_hint_join_3(self):
        result = set(select(s for s in Student if JOIN(s.scholarship in
                        select(s.scholarship + 100 for s in Student if s.name != 'S2'))))
        self.assertEqual(result, set([Student[2]]))

    def test_hint_join_4(self):
        result = set(select(g for g in Group if JOIN(g in select(s.group for s in g.students))))
        self.assertEqual(result, set([Group[1], Group[2]]))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_sqltranslator
from __future__ import with_statement

import unittest
from datetime import date
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Department(db.Entity):
    number = PrimaryKey(int)
    groups = Set('Group')
    courses = Set('Course')

class Student(db.Entity):
    name = Required(unicode)
    group = Required('Group')
    scholarship = Required(int, default=0)
    picture = Optional(buffer)
    courses = Set('Course')
    grades = Set('Grade')

class Group(db.Entity):
    id = PrimaryKey(int)
    students = Set(Student)
    dept = Required(Department)
    rooms = Set('Room')

class Course(db.Entity):
    dept = Required(Department)
    name = Required(unicode)
    credits = Optional(int)
    semester = Required(int)
    PrimaryKey(name, semester)
    grades = Set('Grade')
    students = Set(Student)

class Grade(db.Entity):
    student = Required(Student)
    course = Required(Course)
    PrimaryKey(student, course)
    value = Required(str)
    date = Optional(date)
    teacher = Required('Teacher')

class Teacher(db.Entity):
    name = Required(unicode)
    grades = Set(Grade)

class Room(db.Entity):
    name = PrimaryKey(unicode)
    groups = Set(Group)

db.generate_mapping(create_tables=True)

with db_session:
    d1 = Department(number=44)
    d2 = Department(number=43)
    g1 = Group(id=1, dept=d1)
    g2 = Group(id=2, dept=d2)
    s1 = Student(id=1, name='S1', group=g1, scholarship=0)
    s2 = Student(id=2, name='S2', group=g1, scholarship=100)
    s3 = Student(id=3, name='S3', group=g2, scholarship=500)
    c1 = Course(name='Math', semester=1, dept=d1)
    c2 = Course(name='Economics', semester=1, dept=d1, credits=3)
    c3 = Course(name='Physics', semester=2, dept=d2)
    t1 = Teacher(id=101, name="T1")
    t2 = Teacher(id=102, name="T2")
    Grade(student=s1, course=c1, value='C', teacher=t2, date=date(2011, 1, 1))
    Grade(student=s1, course=c3, value='A', teacher=t1, date=date(2011, 2, 1))
    Grade(student=s2, course=c2, value='B', teacher=t1)
    r1 = Room(name='Room1')
    r2 = Room(name='Room2')
    r3 = Room(name='Room3')
    g1.rooms = [ r1, r2 ]
    g2.rooms = [ r2, r3 ]
    c1.students.add(s1)
    c2.students.add(s2)

db2 = Database('sqlite', ':memory:')

class Room2(db2.Entity):
    name = PrimaryKey(unicode)

db2.generate_mapping(create_tables=True)

name1 = 'S1'

class TestSQLTranslator(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test_select1(self):
        result = set(select(s for s in Student))
        self.assertEqual(result, set([Student[1], Student[2], Student[3]]))
    def test_select_param(self):
        result = select(s for s in Student if s.name == name1)[:]
        self.assertEqual(result, [Student[1]])
    def test_select_object_param(self):
        stud1 = Student[1]
        result = set(select(s for s in Student if s != stud1))
        self.assertEqual(result, set([Student[2], Student[3]]))
    def test_select_deref(self):
        x = 'S1'
        result = select(s for s in Student if s.name == x)[:]
        self.assertEqual(result, [Student[1]])
    def test_select_composite_key(self):
        grade1 = Grade[Student[1], Course['Physics', 2]]
        result = select(g for g in Grade if g != grade1)
        grades = [ grade.value for grade in result ]
        grades.sort()
        self.assertEqual(grades, ['B', 'C'])
    def test_function_max1(self):
        result = select(s for s in Student if max(s.grades.value) == 'C')[:]
        self.assertEqual(result, [Student[1]])
    @raises_exception(TypeError)
    def test_function_max2(self):
        grade1 = Grade[Student[1], Course['Physics', 2]]
        select(s for s in Student if max(s.grades) == grade1)
    def test_function_min(self):
        result = select(s for s in Student if min(s.grades.value) == 'B')[:]
        self.assertEqual(result, [Student[2]])
    @raises_exception(TypeError)
    def test_function_min2(self):
        grade1 = Grade[Student[1], Course['Physics', 2]]
        select(s for s in Student if min(s.grades) == grade1)
    def test_min3(self):
        d = date(2011, 1, 1)
        result = set(select(g for g in Grade if min(g.date, d) == d and g.date is not None))
        self.assertEqual(result, set([Grade[Student[1], Course[u'Math', 1]],
            Grade[Student[1], Course[u'Physics', 2]]]))
    def test_function_len1(self):
        result = select(s for s in Student if len(s.grades) == 1)[:]
        self.assertEqual(result, [Student[2]])
    def test_function_len2(self):
        result = select(s for s in Student if max(s.grades.value) == 'C')[:]
        self.assertEqual(result, [Student[1]])
    def test_function_sum1(self):
        result = select(g for g in Group if sum(g.students.scholarship) == 100)[:]
        self.assertEqual(result, [Group[1]])
    def test_function_avg1(self):
        result = select(g for g in Group if avg(g.students.scholarship) == 50)[:]
        self.assertEqual(result, [Group[1]])
    @raises_exception(TypeError)
    def test_function_sum2(self):
        select(g for g in Group if sum(g.students) == 100)
    @raises_exception(TypeError)
    def test_function_sum3(self):
        select(g for g in Group if sum(g.students.name) == 100)
    def test_function_abs(self):
        result = select(s for s in Student if abs(s.scholarship) == 100)[:]
        self.assertEqual(result, [Student[2]])
    def test_builtin_in_locals(self):
        x = max
        gen = (s.group for s in Student if x(s.grades.value) == 'C')
        result = select(gen)[:]
        self.assertEqual(result, [Group[1]])
        x = min
        result = select(gen)[:]
        self.assertEqual(result, [])
    # @raises_exception(TranslationError, "Name 'g' must be defined in query")
    # def test_name(self):
    #     select(s for s in Student for g in g.subjects)
    def test_chain1(self):
        result = set(select(g for g in Group for s in g.students if s.name.endswith('3')))
        self.assertEqual(result, set([Group[2]]))
    def test_chain2(self):
        result = set(select(s for g in Group if g.dept.number == 44 for s in g.students if s.name.startswith('S')))
        self.assertEqual(result, set([Student[1], Student[2]]))
    def test_chain_m2m(self):
        result = set(select(g for g in Group for r in g.rooms if r.name == 'Room2'))
        self.assertEqual(result, set([Group[1], Group[2]]))
    @raises_exception(TranslationError, 'All entities in a query must belong to the same database')
    def test_two_diagrams(self):
        select(g for g in Group for r in Room2 if r.name == 'Room2')
    def test_add_sub_mul_etc(self):
        result = select(s for s in Student if ((-s.scholarship + 200) * 10 / 5 - 100) ** 2 == 10000 or 5 == 2)[:]
        self.assertEqual(result, [Student[2]])
    def test_subscript(self):
        result = set(select(s for s in Student if s.name[1] == '2'))
        self.assertEqual(result, set([Student[2]]))
    def test_slice(self):
        result = set(select(s for s in Student if s.name[:1] == 'S'))
        self.assertEqual(result, set([Student[3], Student[2], Student[1]]))
    def test_attr_chain(self):
        s1 = Student[1]
        result = select(s for s in Student if s == s1)[:]
        self.assertEqual(result, [Student[1]])
        result = select(s for s in Student if not s == s1)[:]
        self.assertEqual(result, [Student[2], Student[3]])
        result = select(s for s in Student if s.group == s1.group)[:]
        self.assertEqual(result, [Student[1], Student[2]])
        result = select(s for s in Student if s.group.dept == s1.group.dept)[:]
        self.assertEqual(result, [Student[1], Student[2]])
    def test_list_monad1(self):
        result = select(s for s in Student if s.name in ['S1'])[:]
        self.assertEqual(result, [Student[1]])
    def test_list_monad2(self):
        result = select(s for s in Student if s.name not in ['S1', 'S2'])[:]
        self.assertEqual(result, [Student[3]])
    def test_list_monad3(self):
        grade1 = Grade[Student[1], Course['Physics', 2]]
        grade2 = Grade[Student[1], Course['Math', 1]]
        result = set(select(g for g in Grade if g in [grade1, grade2]))
        self.assertEqual(result, set([grade1, grade2]))
        result = set(select(g for g in Grade if g not in [grade1, grade2]))
        self.assertEqual(result, set([Grade[Student[2], Course['Economics', 1]]]))
    def test_tuple_monad1(self):
        n1 = 'S1'
        n2 = 'S2'
        result = select(s for s in Student if s.name in (n1, n2))[:]
        self.assertEqual(result, [Student[1], Student[2]])
    def test_None_value(self):
        result = select(s for s in Student if s.name is None)[:]
        self.assertEqual(result, [])
    def test_None_value2(self):
        result = select(s for s in Student if None == s.name)[:]
        self.assertEqual(result, [])
    def test_None_value3(self):
        n = None
        result = select(s for s in Student if s.name == n)[:]
        self.assertEqual(result, [])
    def test_None_value4(self):
        n = None
        result = select(s for s in Student if n == s.name)[:]
        self.assertEqual(result, [])
    @raises_exception(TranslationError, "External parameter 'a' cannot be used as query result")
    def test_expr1(self):
        a = 100
        result = select(a for s in Student)
    def test_expr2(self):
        result = set(select(s.group for s in Student))
        self.assertEqual(result, set([Group[1], Group[2]]))
    def test_numeric_binop(self):
        i = 100
        f = 2.0
        result = select(s for s in Student if s.scholarship > i + f)[:]
        self.assertEqual(result, [Student[3]])
    def test_string_const_monad(self):
        result = select(s for s in Student if len(s.name) > len('ABC'))[:]
        self.assertEqual(result, [])
    def test_numeric_to_bool1(self):
        result = set(select(s for s in Student if s.name != 'John' or s.scholarship))
        self.assertEqual(result, set([Student[1], Student[2], Student[3]]))
    def test_numeric_to_bool2(self):
        result = set(select(s for s in Student if not s.scholarship))
        self.assertEqual(result, set([Student[1]]))
    def test_not_monad1(self):
        result = set(select(s for s in Student if not (s.scholarship > 0 and s.name != 'S1')))
        self.assertEqual(result, set([Student[1]]))
    def test_not_monad2(self):
        result = set(select(s for s in Student if not not (s.scholarship > 0 and s.name != 'S1')))
        self.assertEqual(result, set([Student[2], Student[3]]))
    def test_subquery_with_attr(self):
        result = set(select(s for s in Student if max(g.value for g in s.grades) == 'C'))
        self.assertEqual(result, set([Student[1]]))
    def test_query_reuse(self):
        q = select(s for s in Student if s.scholarship > 0)
        q.count()
        self.assert_("ORDER BY" not in db.last_sql.upper())
        objects = q[:] # should not throw exception, query can be reused
        self.assert_(True)
    def test_lambda(self):
        result = Student.select(lambda s: s.scholarship > 0)[:]
        self.assertEqual(result, [Student[2], Student[3]])
    def test_lambda2(self):
        result = Student.get(lambda s: s.scholarship == 500)
        self.assertEqual(result, Student[3])
    def test_where(self):
        result = set(Student.select(lambda s: s.scholarship > 0))
        self.assertEqual(result, set([Student[2], Student[3]]))
    def test_order_by(self):
        result = list(Student.order_by(Student.name))
        self.assertEqual(result, [Student[1], Student[2], Student[3]])
    def test_read_inside_query(self):
        result = set(select(s for s in Student if Group[1].dept.number == 44))
        self.assertEqual(result, set([Student[1], Student[2], Student[3]]))
    def test_crud_attr_chain(self):
        result = set(select(s for s in Student if Group[1].dept.number == s.group.dept.number))
        self.assertEqual(result, set([Student[1], Student[2]]))
    def test_composite_key1(self):
        result = set(select(t for t in Teacher if Grade[Student[1], Course['Physics', 2]] in t.grades))
        self.assertEqual(result, set([Teacher.get(name='T1')]))
    def test_composite_key2(self):
        result = set(select(s for s in Student if Course['Math', 1] in s.courses))
        self.assertEqual(result, set([Student[1]]))
    def test_composite_key3(self):
        result = set(select(s for s in Student if Course['Math', 1] not in s.courses))
        self.assertEqual(result, set([Student[2], Student[3]]))
    def test_composite_key4(self):
        result = set(select(s for s in Student if len(c for c in Course if c not in s.courses) == 2))
        self.assertEqual(result, set([Student[1], Student[2]]))
    def test_composite_key5(self):
        result = set(select(s for s in Student if not (c for c in Course if c not in s.courses)))
        self.assertEqual(result, set())
    def test_composite_key6(self):
        result = set(select(c for c in Course if c not in (c2 for s in Student for c2 in s.courses)))
        self.assertEqual(result, set([Course['Physics', 2]]))
    def test_composite_key7(self):
        result = set(select(c for s in Student for c in s.courses))
        self.assertEqual(result, set([Course['Math', 1], Course['Economics', 1]]))
    def test_contains1(self):
        s1 = Student[1]
        result = set(select(g for g in Group if s1 in g.students))
        self.assertEqual(result, set([Group[1]]))
    def test_contains2(self):
        s1 = Student[1]
        result = set(select(g for g in Group if s1.name in g.students.name))
        self.assertEqual(result, set([Group[1]]))
    def test_contains3(self):
        s1 = Student[1]
        result = set(select(g for g in Group if s1 not in g.students))
        self.assertEqual(result, set([Group[2]]))
    def test_contains4(self):
        s1 = Student[1]
        result = set(select(g for g in Group if s1.name not in g.students.name))
        self.assertEqual(result, set([Group[2]]))
    def test_buffer_monad1(self):
        select(s for s in Student if s.picture == buffer('abc'))
    def test_database_monad(self):
        result = set(select(s for s in db.Student if db.Student[1] == s))
        self.assertEqual(result, set([Student[1]]))
    def test_duplicate_name(self):
        result = set(select(x for x in Student if x.group in (x for x in Group)))
        self.assertEqual(result, set([Student[1], Student[2], Student[3]]))
    def test_hint_join1(self):
        result = set(select(s for s in Student if JOIN(max(s.courses.credits) == 3)))
        self.assertEqual(result, set([Student[2]]))
    def test_hint_join2(self):
        result = set(select(c for c in Course if JOIN(len(c.students) == 1)))
        self.assertEqual(result, set([Course['Math', 1], Course['Economics', 1]]))
    def test_tuple_param(self):
        x = Student[1], Student[2]
        result = set(select(s for s in Student if s not in x))
        self.assertEqual(result, set([Student[3]]))
    @raises_exception(TypeError, "Expression 'x' should not contain None values")        
    def test_tuple_param_2(self):
        x = Student[1], None
        result = set(select(s for s in Student if s not in x))
        self.assertEqual(result, set([Student[3]]))
    @raises_exception(TypeError, "Function 'f' cannot be used inside query")
    def test_unknown_func(self):
        def f(x): return x
        select(s for s in Student if f(s))
    def test_method_monad(self):
        result = set(select(s for s in Student if s not in Student.select(lambda s: s.scholarship > 0)))
        self.assertEqual(result, set([Student[1]]))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_sqltranslator2
from __future__ import with_statement

import unittest
from datetime import date
from decimal import Decimal
from pony.orm.core import *
from pony.orm.sqltranslation import IncomparableTypesError
from testutils import *

db = Database('sqlite', ':memory:')

class Department(db.Entity):
    number = PrimaryKey(int, auto=True)
    name = Required(unicode, unique=True)
    groups = Set("Group")
    courses = Set("Course")

class Group(db.Entity):
    number = PrimaryKey(int)
    major = Required(unicode)
    dept = Required("Department")
    students = Set("Student")

class Course(db.Entity):
    name = Required(unicode)
    semester = Required(int)
    lect_hours = Required(int)
    lab_hours = Required(int)
    credits = Required(int)
    dept = Required(Department)
    students = Set("Student")
    PrimaryKey(name, semester)

class Student(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(unicode)
    dob = Required(date)
    tel = Optional(str)
    picture = Optional(buffer, lazy=True)
    gpa = Required(float, default=0)
    phd = Optional(bool)
    group = Required(Group)
    courses = Set(Course)

db.generate_mapping(create_tables=True)

with db_session:
    d1 = Department(name="Department of Computer Science")
    d2 = Department(name="Department of Mathematical Sciences")
    d3 = Department(name="Department of Applied Physics")

    c1 = Course(name="Web Design", semester=1, dept=d1,
                       lect_hours=30, lab_hours=30, credits=3)
    c2 = Course(name="Data Structures and Algorithms", semester=3, dept=d1,
                       lect_hours=40, lab_hours=20, credits=4)

    c3 = Course(name="Linear Algebra", semester=1, dept=d2,
                       lect_hours=30, lab_hours=30, credits=4)
    c4 = Course(name="Statistical Methods", semester=2, dept=d2,
                       lect_hours=50, lab_hours=25, credits=5)

    c5 = Course(name="Thermodynamics", semester=2, dept=d3,
                       lect_hours=25, lab_hours=40, credits=4)
    c6 = Course(name="Quantum Mechanics", semester=3, dept=d3,
                       lect_hours=40, lab_hours=30, credits=5)

    g101 = Group(number=101, major='B.E. in Computer Engineering', dept=d1)
    g102 = Group(number=102, major='B.S./M.S. in Computer Science', dept=d2)
    g103 = Group(number=103, major='B.S. in Applied Mathematics and Statistics', dept=d2)
    g104 = Group(number=104, major='B.S./M.S. in Pure Mathematics', dept=d2)
    g105 = Group(number=105, major='B.E in Electronics', dept=d3)
    g106 = Group(number=106, major='B.S./M.S. in Nuclear Engineering', dept=d3)

    Student(name='John Smith', dob=date(1991, 3, 20), tel='123-456', gpa=3, group=g101, phd=True,
                        courses=[c1, c2, c4, c6])
    Student(name='Matthew Reed', dob=date(1990, 11, 26), gpa=3.5, group=g101, phd=True,
                        courses=[c1, c3, c4, c5])
    Student(name='Chuan Qin', dob=date(1989, 2, 5), gpa=4, group=g101,
                        courses=[c3, c5, c6])
    Student(name='Rebecca Lawson', dob=date(1990, 4, 18), tel='234-567', gpa=3.3, group=g102,
                        courses=[c1, c4, c5, c6])
    Student(name='Maria Ionescu', dob=date(1991, 4, 23), gpa=3.9, group=g102,
                        courses=[c1, c2, c4, c6])
    Student(name='Oliver Blakey', dob=date(1990, 9, 8), gpa=3.1, group=g102,
                        courses=[c1, c2, c5])
    Student(name='Jing Xia', dob=date(1988, 12, 30), gpa=3.2, group=g102,
                        courses=[c1, c3, c5, c6])

class TestSQLTranslator2(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test_distinct1(self):
        q = select(c.students for c in Course)
        self.assertEqual(q._translator.distinct, True)
        self.assertEqual(q.count(), 7)
    def test_distinct3(self):
        q = select(d for d in Department if len(s for c in d.courses for s in c.students) > len(s for s in Student))
        self.assertEqual("DISTINCT" in flatten(q._translator.conditions), True)
        self.assertEqual(q[:], [])
    def test_distinct4(self):
        q = select(d for d in Department if len(d.groups.students) > 3)
        self.assertEqual("DISTINCT" not in flatten(q._translator.conditions), True)
        self.assertEqual(q[:], [Department[2]])
    def test_distinct5(self):
        result = set(select(s for s in Student))
        self.assertEqual(result, set([Student[1], Student[2], Student[3], Student[4], Student[5], Student[6], Student[7]]))
    def test_distinct6(self):
        result = set(select(s for s in Student).distinct())
        self.assertEqual(result, set([Student[1], Student[2], Student[3], Student[4], Student[5], Student[6], Student[7]]))
    def test_not_null1(self):
        q = select(g for g in Group if '123-45-67' not in g.students.tel and g.dept == Department[1])
        not_null = "IS_NOT_NULL COLUMN student-1 tel" in (" ".join(str(i) for i in flatten(q._translator.conditions)))
        self.assertEqual(not_null, True)
        self.assertEqual(q[:], [Group[101]])
    def test_not_null2(self):
        q = select(g for g in Group if 'John' not in g.students.name and g.dept == Department[1])
        not_null = "IS_NOT_NULL COLUMN student-1 name" in (" ".join(str(i) for i in flatten(q._translator.conditions)))
        self.assertEqual(not_null, False)
        self.assertEqual(q[:], [Group[101]])
    def test_chain_of_attrs_inside_for1(self):
        result = set(select(s for d in Department if d.number == 2 for s in d.groups.students))
        self.assertEqual(result, set([Student[4], Student[5], Student[6], Student[7]]))
    def test_chain_of_attrs_inside_for2(self):
        pony.options.SIMPLE_ALIASES = False
        result = set(select(s for d in Department if d.number == 2 for s in d.groups.students))
        self.assertEqual(result, set([Student[4], Student[5], Student[6], Student[7]]))
        pony.options.SIMPLE_ALIASES = True
    def test_non_entity_result1(self):
        result = select((s.name, s.group.number) for s in Student if s.name.startswith("J"))[:]
        self.assertEqual(sorted(result), [(u'Jing Xia', 102), (u'John Smith', 101)])
    def test_non_entity_result2(self):
        result = select((s.dob.year, s.group.number) for s in Student)[:]
        self.assertEqual(sorted(result), [(1988, 102), (1989, 101), (1990, 101), (1990, 102), (1991, 101), (1991, 102)])
    def test_non_entity_result3(self):
        result = select(s.dob.year for s in Student).without_distinct()
        self.assertEqual(sorted(result), [1988, 1989, 1990, 1990, 1990, 1991, 1991])
        result = select(s.dob.year for s in Student)[:]  # test the last query didn't override the cached one
        self.assertEqual(sorted(result), [1988, 1989, 1990, 1991])
    def test_non_entity_result3a(self):
        result = select(s.dob.year for s in Student)[:]
        self.assertEqual(sorted(result), [1988, 1989, 1990, 1991])
    def test_non_entity_result4(self):
        result = set(select(s.name for s in Student if s.name.startswith('M')))
        self.assertEqual(result, set([u'Matthew Reed', u'Maria Ionescu']))
    def test_non_entity_result5(self):
        result = select((s.group, s.dob) for s in Student if s.group == Group[101])[:]
        self.assertEqual(sorted(result), [(Group[101], date(1989, 2, 5)), (Group[101], date(1990, 11, 26)), (Group[101], date(1991, 3, 20))])
    def test_non_entity_result6(self):
        result = select((c, s) for s in Student for c in Course if c.semester == 1 and s.id < 3)[:]
        self.assertEqual(sorted(result), sorted([(Course[u'Linear Algebra',1], Student[1]), (Course[u'Linear Algebra',1],
            Student[2]), (Course[u'Web Design',1], Student[1]), (Course[u'Web Design',1], Student[2])]))
    def test_non_entity7(self):
        result = set(select(s for s in Student if (s.name, s.dob) not in (((s2.name, s2.dob) for s2 in Student if s.group.number == 101))))
        self.assertEqual(result, set([Student[4], Student[5], Student[6], Student[7]]))
    @raises_exception(IncomparableTypesError, "Incomparable types 'int' and 'Set of Student' in expression: g.number == g.students")
    def test_incompartible_types(self):
        select(g for g in Group if g.number == g.students)
    @raises_exception(TranslationError, "External parameter 'x' cannot be used as query result")
    def test_external_param1(self):
        x = Student[1]
        select(x for s in Student)
    def test_external_param2(self):
        x = Student[1]
        result = set(select(s for s in Student if s.name != x.name))
        self.assertEqual(result, set([Student[2], Student[3], Student[4], Student[5], Student[6], Student[7]]))
    @raises_exception(TypeError, "Use select(...) function or Group.select(...) method for iteration")
    def test_exception1(self):
        for g in Group: print g.number
    @raises_exception(MultipleObjectsFoundError, "Multiple objects were found. Use select(...) to retrieve them")
    def test_exception2(self):
         get(s for s in Student)
    def test_exists(self):
        result = exists(s for s in Student)
    @raises_exception(ExprEvalError, "db.FooBar raises AttributeError: 'Database' object has no attribute 'FooBar'")
    def test_entity_not_found(self):
        select(s for s in db.Student for g in db.FooBar)
    def test_keyargs1(self):
        result = set(select(s for s in Student if s.dob < date(year=1990, month=10, day=20)))
        self.assertEqual(result, set([Student[3], Student[4], Student[6], Student[7]]))
    def test_query_as_string1(self):
        result = set(select('s for s in Student if 3 <= s.gpa < 4'))
        self.assertEqual(result, set([Student[1], Student[2], Student[4], Student[5], Student[6], Student[7]]))
    def test_query_as_string2(self):
        result = set(select('s for s in db.Student if 3 <= s.gpa < 4'))
        self.assertEqual(result, set([Student[1], Student[2], Student[4], Student[5], Student[6], Student[7]]))
    def test_str_subclasses(self):
        result = select(d for d in Department for g in d.groups for c in d.courses if g.number == 106 and c.name.startswith('T'))[:]
        self.assertEqual(result, [Department[3]])
    def test_unicode_subclass(self):
        class Unicode2(unicode):
            pass
        u2 = Unicode2(u'\xf0')
        select(s for s in Student if len(u2) == 1)
    def test_bool(self):
        result = set(select(s for s in Student if s.phd == True))
        self.assertEqual(result, set([Student[1], Student[2]]))
    def test_bool2(self):
        result = list(select(s for s in Student if s.phd + 1 == True))
        self.assertEqual(result, [])
    def test_bool3(self):
        result = list(select(s for s in Student if s.phd + 1.1 == True))
        self.assertEqual(result, [])
    def test_bool4(self):
        result = list(select(s for s in Student if s.phd + Decimal('1.1') == True))
        self.assertEqual(result, [])
    def test_bool5(self):
        x = True
        result = set(select(s for s in Student if s.phd == True and (False or (True and x))))
        self.assertEqual(result, set([Student[1], Student[2]]))
    def test_bool6(self):
        x = False
        result = list(select(s for s in Student if s.phd == (False or (True and x)) and s.phd is True))
        self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_declarative_string_mixin
from __future__ import with_statement

import unittest
from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)

db.generate_mapping(create_tables=True)

with db_session:
    Student(id=1, name="ABCDEF")
    Student(id=2, name="Bob")
    Student(id=3, name="Beth")
    Student(id=4, name="Jon")
    Student(id=5, name="Pete")

class TestStringMixin(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()

    def tearDown(self):
        rollback()
        db_session.__exit__()

    def test1(self):
        name = "ABCDEF5"
        result = set(select(s for s in Student if s.name + "5" == name))
        self.assertEqual(result, set([Student[1]]))

    def test2(self):
        result = set(select(s for s in Student if s.name[0:2] == "ABCDEF"[0:2]))
        self.assertEqual(result, set([Student[1]]))

    def test3(self):
        result = set(select(s for s in Student if s.name[1:100] == "ABCDEF"[1:100]))
        self.assertEqual(result, set([Student[1]]))

    def test4(self):
        result = set(select(s for s in Student if s.name[:] == "ABCDEF"))
        self.assertEqual(result, set([Student[1]]))

    def test5(self):
        result = set(select(s for s in Student if s.name[:3] == "ABCDEF"[0:3]))
        self.assertEqual(result, set([Student[1]]))

    def test6(self):
        x = 4
        result = set(select(s for s in Student if s.name[:x] == "ABCDEF"[:x]))

    def test7(self):
        result = set(select(s for s in Student if s.name[0:] == "ABCDEF"[0:]))
        self.assertEqual(result, set([Student[1]]))

    def test8(self):
        x = 2
        result = set(select(s for s in Student if s.name[x:] == "ABCDEF"[x:]))
        self.assertEqual(result, set([Student[1]]))

    def test9(self):
        x = 4
        result = set(select(s for s in Student if s.name[0:x] == "ABCDEF"[0:x]))
        self.assertEqual(result, set([Student[1]]))

    def test10(self):
        x = 0
        result = set(select(s for s in Student if s.name[x:3] == "ABCDEF"[x:3]))
        self.assertEqual(result, set([Student[1]]))

    def test11(self):
        x = 1
        y = 4
        result = set(select(s for s in Student if s.name[x:y] == "ABCDEF"[x:y]))
        self.assertEqual(result, set([Student[1]]))

    def test12(self):
        x = 10
        y = 20
        result = set(select(s for s in Student if s.name[x:y] == "ABCDEF"[x:y]))
        self.assertEqual(result, set([Student[1], Student[2], Student[3], Student[4], Student[5]]))

    def test13(self):
        result = set(select(s for s in Student if s.name[1] == "ABCDEF"[1]))
        self.assertEqual(result, set([Student[1]]))

    def test14(self):
        x = 1
        result = set(select(s for s in Student if s.name[x] == "ABCDEF"[x]))
        self.assertEqual(result, set([Student[1]]))

    def test15(self):
        x = -1
        result = set(select(s for s in Student if s.name[x] == "ABCDEF"[x]))
        self.assertEqual(result, set([Student[1]]))

    def test16(self):
        result = set(select(s for s in Student if 'o' in s.name))
        self.assertEqual(result, set([Student[2], Student[4]]))

    def test17(self):
        x = 'o'
        result = set(select(s for s in Student if x in s.name))
        self.assertEqual(result, set([Student[2], Student[4]]))

    def test18(self):
        result = set(select(s for s in Student if 'o' not in s.name))
        self.assertEqual(result, set([Student[1], Student[3], Student[5]]))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_diagram
import unittest
from pony.orm.core import *
from pony.orm.core import Entity
from testutils import *

class TestDiag(unittest.TestCase):

    @raises_exception(ERDiagramError, 'Entity Entity1 already exists')
    def test_entity_duplicate(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
        class Entity1(db.Entity):
            id = PrimaryKey(int)

    @raises_exception(ERDiagramError, 'Interrelated entities must belong to same database.'
                                    ' Entities Entity2 and Entity1 belongs to different databases')
    def test_diagram1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required('Entity2')
        db = Database('sqlite', ':memory:')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping()

    @raises_exception(ERDiagramError, 'Entity definition Entity2 was not found')
    def test_diagram2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required('Entity2')
        db.generate_mapping()

    @raises_exception(TypeError, 'Entity1._table_ property must be a string. Got: 123')
    def test_diagram3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            _table_ = 123
            id = PrimaryKey(int)
        db.generate_mapping()

    def test_diagram4(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Set('Entity2', table='Table1')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1, table='Table1')
        db.generate_mapping(create_tables=True)

    def test_diagram5(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Set('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required(Entity1)
        db.generate_mapping(create_tables=True)

    @raises_exception(MappingError, "Parameter 'table' for Entity1.attr1 and Entity2.attr2 do not match")
    def test_diagram6(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Set('Entity2', table='Table1')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1, table='Table2')
        db.generate_mapping()

    @raises_exception(MappingError, "Table name 'Table1' is already in use")
    def test_diagram7(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            _table_ = 'Table1'
            id = PrimaryKey(int)
            attr1 = Set('Entity2', table='Table1')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1, table='Table1')
        db.generate_mapping()

    def test_diagram8(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Set('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1)
        db.generate_mapping(create_tables=True)
        m2m_table = db.schema.tables['Entity1_Entity2']
        col_names = set([ col.name for col in m2m_table.column_list ])
        self.assertEqual(col_names, set(['entity1', 'entity2']))
        self.assertEqual(Entity1.attr1.get_m2m_columns(), ['entity1'])

    def test_diagram9(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(str)
            PrimaryKey(a, b)
            attr1 = Set('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1)
        db.generate_mapping(create_tables=True)
        m2m_table = db.schema.tables['Entity1_Entity2']
        col_names = set([ col.name for col in m2m_table.column_list ])
        self.assertEqual(col_names, set(['entity1_a', 'entity1_b', 'entity2']))

    def test_diagram10(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(str)
            PrimaryKey(a, b)
            attr1 = Set('Entity2', column='z')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1, columns=['x', 'y'])
        db.generate_mapping(create_tables=True)

    @raises_exception(MappingError, 'Invalid number of columns for Entity2.attr2')
    def test_diagram11(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(str)
            PrimaryKey(a, b)
            attr1 = Set('Entity2', column='z')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Set(Entity1, columns=['x'])
        db.generate_mapping()

    @raises_exception(ERDiagramError, 'Base Entity does not belong to any database')
    def test_diagram12(self):
        class Test(Entity):
        	name = Required(unicode)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_diagram_attribute
import unittest
from pony.orm.core import *
from pony.orm.core import Attribute
from testutils import *

class TestAttribute(unittest.TestCase):

    @raises_exception(TypeError, "Attribute Entity1.id has unknown option 'another_option'")
    def test_attribute1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int, another_option=3)
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, 'Cannot link attribute Entity1.b to abstract Entity class. Use specific Entity subclass instead')
    def test_attribute2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            b = Required(db.Entity)
        db.generate_mapping()

    @raises_exception(TypeError, 'Default value for required attribute Entity1.b cannot be None')
    def test_attribute3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            b = Required(int, default=None)

    def test_attribute4(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required('Entity2', reverse='attr2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.attr1.reverse, Entity2.attr2)

    def test_attribute5(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1, reverse=Entity1.attr1)
        self.assertEqual(Entity2.attr2.reverse, Entity1.attr1)

    @raises_exception(TypeError, "Value of 'reverse' option must be name of reverse attribute). Got: 123")
    def test_attribute6(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required('Entity2', reverse=123)

    @raises_exception(TypeError, "Reverse option cannot be set for this type: <type 'str'>")
    def test_attribute7(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required(str, reverse='attr1')

    @raises_exception(TypeError, "'Attribute' is abstract type")
    def test_attribute8(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Attribute(str)

    @raises_exception(ERDiagramError, "Attribute name cannot both start and end with underscore. Got: _attr1_")
    def test_attribute9(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            _attr1_ = Required(str)

    @raises_exception(ERDiagramError, "Duplicate use of attribute Entity1.attr1 in entity Entity2")
    def test_attribute10(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required(str)
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Entity1.attr1

    @raises_exception(ERDiagramError, "Invalid use of attribute Entity1.a in entity Entity2")
    def test_attribute11(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(str)
        class Entity2(db.Entity):
            b = Required(str)
            composite_key(Entity1.a, b)

    @raises_exception(ERDiagramError, "Cannot create primary key for Entity1 automatically because name 'id' is alredy in use")
    def test_attribute12(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = Optional(str)

    @raises_exception(ERDiagramError, "Reverse attribute for Entity1.attr1 not found")
    def test_attribute13(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
        db.generate_mapping()

    @raises_exception(ERDiagramError, "Reverse attribute Entity1.attr1 not found")
    def test_attribute14(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required(Entity1, reverse='attr1')
        db.generate_mapping()

    @raises_exception(ERDiagramError, "Inconsistent reverse attributes Entity3.attr3 and Entity2.attr2")
    def test_attribute15(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required(Entity1)
        class Entity3(db.Entity):
            id = PrimaryKey(int)
            attr3 = Required(Entity2, reverse='attr2')
        db.generate_mapping()

    @raises_exception(ERDiagramError, "Inconsistent reverse attributes Entity3.attr3 and Entity2.attr2")
    def test_attribute16(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required(Entity1)
        class Entity3(db.Entity):
            id = PrimaryKey(int)
            attr3 = Required(Entity2, reverse=Entity2.attr2)
        db.generate_mapping()

    @raises_exception(ERDiagramError, 'Reverse attribute for Entity2.attr2 not found')
    def test_attribute18(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required('Entity1')
        db.generate_mapping()

    @raises_exception(ERDiagramError, 'Ambiguous reverse attribute for Entity1.a')
    def test_attribute19(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            a = Required('Entity2')
            b = Optional('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            c = Set(Entity1)
            d = Set(Entity1)
        db.generate_mapping()

    @raises_exception(ERDiagramError, 'Ambiguous reverse attribute for Entity1.c')
    def test_attribute20(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            c = Set('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            a = Required(Entity1, reverse='c')
            b = Optional(Entity1, reverse='c')
        db.generate_mapping()

    def test_attribute21(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            a = Required('Entity2', reverse='c')
            b = Optional('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            c = Set(Entity1)
            d = Set(Entity1)

    def test_attribute22(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            a = Required('Entity2', reverse='c')
            b = Optional('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            c = Set(Entity1, reverse='a')
            d = Set(Entity1)

    @raises_exception(ERDiagramError, 'Inconsistent reverse attributes Entity1.a and Entity2.b')
    def test_attribute23(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required('Entity2', reverse='b')
        class Entity2(db.Entity):
            b = Optional('Entity3')
        class Entity3(db.Entity):
            c = Required('Entity2')
        db.generate_mapping()

    @raises_exception(ERDiagramError, 'Inconsistent reverse attributes Entity1.a and Entity2.c')
    def test_attribute23(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required('Entity2', reverse='c')
            b = Required('Entity2', reverse='d')
        class Entity2(db.Entity):
            c = Optional('Entity1', reverse='b')
            d = Optional('Entity1', reverse='a')
        db.generate_mapping()

    @raises_exception(TypeError, "Parameters 'column' and 'columns' cannot be specified simultaneously")
    def test_columns1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional("Entity2", column='a', columns=['b', 'c'])
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)

    def test_columns2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int, column='a')
        self.assertEqual(Entity1.id.columns, ['a'])

    def test_columns3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int, columns=['a'])
        self.assertEqual(Entity1.id.column, 'a')

    @raises_exception(MappingError, "Too many columns were specified for Entity1.id")
    def test_columns5(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int, columns=['a', 'b'])
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameter 'columns' must be a list. Got: set(['a'])'")
    def test_columns6(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int, columns=set(['a']))
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameter 'column' must be a string. Got: 4")
    def test_columns7(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int, column=4)
        db.generate_mapping(create_tables=True)

    def test_columns8(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(int)
            attr1 = Optional('Entity2')
            PrimaryKey(a, b)
        class Entity2(db.Entity):
            attr2 = Required(Entity1, columns=['x', 'y'])
        self.assertEqual(Entity2.attr2.column, None)
        self.assertEqual(Entity2.attr2.columns, ['x', 'y'])

    @raises_exception(MappingError, 'Invalid number of columns specified for Entity2.attr2')
    def test_columns9(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(int)
            attr1 = Optional('Entity2')
            PrimaryKey(a, b)
        class Entity2(db.Entity):
            attr2 = Required(Entity1, columns=['x', 'y', 'z'])
        db.generate_mapping(create_tables=True)

    @raises_exception(MappingError, 'Invalid number of columns specified for Entity2.attr2')
    def test_columns10(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(int)
            attr1 = Optional('Entity2')
            PrimaryKey(a, b)
        class Entity2(db.Entity):
            attr2 = Required(Entity1, column='x')
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Items of parameter 'columns' must be strings. Got: [1, 2]")
    def test_columns11(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(int)
            attr1 = Optional('Entity2')
            PrimaryKey(a, b)
        class Entity2(db.Entity):
            attr2 = Required(Entity1, columns=[1, 2])

    def test_columns12(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', column='column1', reverse_column='column2', reverse_columns=['column2'])
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameters 'reverse_column' and 'reverse_columns' cannot be specified simultaneously")
    def test_columns13(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', column='column1', reverse_column='column2', reverse_columns=['column3'])
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameter 'reverse_column' must be a string. Got: 5")
    def test_columns14(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', column='column1', reverse_column=5)
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameter 'reverse_columns' must be a list. Got: 'column3'")
    def test_columns15(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', column='column1', reverse_columns='column3')
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameter 'reverse_columns' must be a list of strings. Got: [5]")
    def test_columns16(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', column='column1', reverse_columns=[5])
        db.generate_mapping(create_tables=True)

    def test_columns17(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', column='column1', reverse_columns=['column2'])
        db.generate_mapping(create_tables=True)

    def test_columns18(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', table='T1')
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Parameter 'table' must be a string. Got: 5")
    def test_columns19(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', table=5)
        db.generate_mapping(create_tables=True)

    @raises_exception(TypeError, "Each part of table name must be a string. Got: 1")
    def test_columns20(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            attr1 = Set('Entity1', reverse='attr1', table=[1, 'T1'])
        db.generate_mapping(create_tables=True)

    def test_nullable1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Optional(unicode, unique=True)
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.a.nullable, True)

    def test_nullable2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Optional(unicode, unique=True)
        db.generate_mapping(create_tables=True)
        with db_session:
            Entity1()
            commit()
            Entity1()
            commit()
        self.assert_(True)

    def test_lambda_1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(lambda: db.Entity2)
        class Entity2(db.Entity):
            b = Set(lambda: db.Entity1)
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.a.py_type, Entity2)
        self.assertEqual(Entity2.b.py_type, Entity1)

    @raises_exception(TypeError, "Invalid type of attribute Entity1.a: expected entity class, got 'Entity2'")
    def test_lambda_2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(lambda: 'Entity2')
        class Entity2(db.Entity):
            b = Set(lambda: db.Entity1)
        db.generate_mapping(create_tables=True)

    @raises_exception(ERDiagramError, 'Interrelated entities must belong to same database. '
                                      'Entities Entity1 and Entity2 belongs to different databases')
    def test_lambda_3(self):
        db1 = Database('sqlite', ':memory:')
        class Entity1(db1.Entity):
            a = Required(lambda: db2.Entity2)
        db2 = Database('sqlite', ':memory:')
        class Entity2(db2.Entity):
            b = Set(lambda: db1.Entity1)
        db1.generate_mapping(create_tables=True)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_diagram_inheritance
import unittest
from pony.orm.core import *
from testutils import *

class TestInheritance(unittest.TestCase):

    def test_inheritance1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
        class Entity2(Entity1):
            a = Required(int)
        class Entity3(Entity1):
            b = Required(int)
        class Entity4(Entity2, Entity3):
            c = Required(int)

    @raises_exception(ERDiagramError, 'With multiple inheritance of entities, inheritance graph must be diamond-like')
    def test_inheritance2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
        class Entity2(db.Entity):
            b = PrimaryKey(int)
        class Entity3(Entity1, Entity2):
            c = Required(int)

    def test_inheritance3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
        db = Database('sqlite', ':memory:')
        class Entity2(Entity1):
            a = Required(int)
        self.assert_(True)

    @raises_exception(ERDiagramError, 'Attribute "Entity2.a" clashes with attribute "Entity3.a" in derived entity "Entity4"')
    def test_inheritance4(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
        class Entity2(Entity1):
            a = Required(int)
        class Entity3(Entity1):
            a = Required(int)
        class Entity4(Entity2, Entity3):
            c = Required(int)

    @raises_exception(ERDiagramError, "Name 'a' hides base attribute Entity1.a")
    def test_inheritance5(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            a = Required(int)
        class Entity2(Entity1):
            a = Required(int)

    @raises_exception(ERDiagramError, "Primary key cannot be redefined in derived classes")
    def test_inheritance6(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
        class Entity2(Entity1):
            b = PrimaryKey(int)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_diagram_keys
import unittest
from pony.orm.core import *
from testutils import *

class TestKeys(unittest.TestCase):

    def test_keys1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Required(str)
        self.assertEqual(Entity1._pk_attrs_, (Entity1.a,))
        self.assertEqual(Entity1._pk_is_composite_, False)
        self.assertEqual(Entity1._pk_, Entity1.a)
        self.assertEqual(Entity1._keys_, [])
        self.assertEqual(Entity1._simple_keys_, [])
        self.assertEqual(Entity1._composite_keys_, [])

    def test_keys2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(str)
            PrimaryKey(a, b)
        self.assertEqual(Entity1._pk_attrs_, (Entity1.a, Entity1.b))
        self.assertEqual(Entity1._pk_is_composite_, True)
        self.assertEqual(Entity1._pk_, (Entity1.a, Entity1.b))
        self.assertEqual(Entity1._keys_, [])
        self.assertEqual(Entity1._simple_keys_, [])
        self.assertEqual(Entity1._composite_keys_, [])

    @raises_exception(ERDiagramError, 'Only one primary key can be defined in each entity class')
    def test_keys3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = PrimaryKey(int)

    @raises_exception(ERDiagramError, 'Only one primary key can be defined in each entity class')
    def test_keys4(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Required(int)
            c = Required(int)
            PrimaryKey(b, c)

    def test_unique1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Required(int, unique=True)
        self.assertEqual(Entity1._keys_, [(Entity1.b,)])
        self.assertEqual(Entity1._simple_keys_, [Entity1.b])
        self.assertEqual(Entity1._composite_keys_, [])

    def test_unique2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Optional(int, unique=True)
        self.assertEqual(Entity1._keys_, [(Entity1.b,)])
        self.assertEqual(Entity1._simple_keys_, [Entity1.b])
        self.assertEqual(Entity1._composite_keys_, [])

    def test_unique2_1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Optional(int)
            c = Required(int)
            composite_key(b, c)
        self.assertEqual(Entity1._keys_, [(Entity1.b, Entity1.c)])
        self.assertEqual(Entity1._simple_keys_, [])
        self.assertEqual(Entity1._composite_keys_, [(Entity1.b, Entity1.c)])

    @raises_exception(TypeError, 'composite_key() must receive at least two attributes as arguments')
    def test_unique3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            composite_key()

    @raises_exception(TypeError, 'composite_key() arguments must be attributes. Got: 123')
    def test_unique4(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            composite_key(123, 456)

    @raises_exception(TypeError, "composite_key() arguments must be attributes. Got: <type 'int'>")
    def test_unique5(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            composite_key(int, a)

    @raises_exception(TypeError, 'Set attribute Entity1.b cannot be part of unique index')
    def test_unique6(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Set('Entity2')
            composite_key(a, b)

    @raises_exception(TypeError, "'unique' option cannot be set for attribute Entity1.b because it is collection")
    def test_unique7(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Set('Entity2', unique=True)

    @raises_exception(TypeError, 'Optional attribute Entity1.b cannot be part of primary key')
    def test_unique8(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Optional(int)
            PrimaryKey(a, b)

    @raises_exception(TypeError, 'PrimaryKey attribute Entity1.a cannot be of type float')
    def test_float_pk(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(float)

    @raises_exception(TypeError, 'Attribute Entity1.b of type float cannot be part of primary key')
    def test_float_composite_pk(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(float)
            PrimaryKey(a, b)

    @raises_exception(TypeError, 'Attribute Entity1.b of type float cannot be part of unique index')
    def test_float_composite_key(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(float)
            composite_key(a, b)

    @raises_exception(TypeError, 'Unique attribute Entity1.a cannot be of type float')
    def test_float_unique(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(float, unique=True)

    @raises_exception(TypeError, 'PrimaryKey attribute Entity1.a cannot be volatile')
    def test_volatile_pk(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int, volatile=True)

    @raises_exception(TypeError, 'Set attribute Entity1.b cannot be volatile')
    def test_volatile_set(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            b = Set('Entity2', volatile=True)

    @raises_exception(TypeError, 'Volatile attribute Entity1.b cannot be part of primary key')
    def test_volatile_composite_pk(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(int, volatile=True)
            PrimaryKey(a, b)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_filter
import unittest
from model1 import *

class TestFilter(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test_filter_1(self):
        q = select(s for s in Student)
        result = set(q.filter(scholarship=0))
        self.assertEqual(result, set([Student[101], Student[103]]))
    def test_filter_2(self):
        q = select(s for s in Student)
        q2 = q.filter(scholarship=500)
        result = set(q2.filter(group=Group['3132']))
        self.assertEqual(result, set([Student[104]]))
    def test_filter_3(self):
        q = select(s for s in Student)
        q2 = q.filter(lambda s: s.scholarship > 500)
        result = set(q2.filter(lambda s: count(s.marks) > 0))
        self.assertEqual(result, set([Student[102]]))
    def test_filter_4(self):
        q = select(s for s in Student)
        q2 = q.filter(lambda s: s.scholarship != 500)
        q3 = q2.order_by(1)
        result = list(q3.filter(lambda s: count(s.marks) > 1))
        self.assertEqual(result, [Student[101], Student[103]])
    def test_filter_5(self):
        q = select(s for s in Student)
        q2 = q.filter(lambda s: s.scholarship != 500)
        q3 = q2.order_by(Student.name)
        result = list(q3.filter(lambda s: count(s.marks) > 1))
        self.assertEqual(result, [Student[103], Student[101]])
    def test_filter_6(self):
        q = select(s for s in Student)
        q2 = q.filter(lambda s: s.scholarship != 500)
        q3 = q2.order_by(lambda s: s.name)
        result = list(q3.filter(lambda s: count(s.marks) > 1))
        self.assertEqual(result, [Student[103], Student[101]])
    def test_filter_7(self):
        q = select(s for s in Student)
        q2 = q.filter(scholarship=0)
        result = set(q2.filter(lambda s: count(s.marks) > 1))
        self.assertEqual(result, set([Student[103], Student[101]]))
    def test_filter_8(self):
        q = select(s for s in Student)
        q2 = q.filter(lambda s: s.scholarship != 500)
        q3 = q2.order_by(lambda s: s.name)
        q4 = q3.order_by(None)
        result = set(q4.filter(lambda s: count(s.marks) > 1))
        self.assertEqual(result, set([Student[103], Student[101]]))

########NEW FILE########
__FILENAME__ = test_frames
import unittest

from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Person(db.Entity):
    name = Required(unicode)
    age = Required(int)

db.generate_mapping(create_tables=True)

with db_session:
    p1 = Person(name='John', age=22)
    p2 = Person(name='Mary', age=18)
    p3 = Person(name='Mike', age=25)

class TestFrames(unittest.TestCase):

    @db_session
    def test_select(self):
        x = 20
        result = select(p.id for p in Person if p.age > x)[:]
        self.assertEqual(set(result), set([1, 3]))

    @db_session
    def test_select_str(self):
        x = 20
        result = select('p.id for p in Person if p.age > x')[:]
        self.assertEqual(set(result), set([1, 3]))

    @db_session
    def test_left_join(self):
        x = 20
        result = left_join(p.id for p in Person if p.age > x)[:]
        self.assertEqual(set(result), set([1, 3]))

    @db_session
    def test_left_join_str(self):
        x = 20
        result = left_join('p.id for p in Person if p.age > x')[:]
        self.assertEqual(set(result), set([1, 3]))

    @db_session
    def test_get(self):
        x = 23
        result = get(p.id for p in Person if p.age > x)
        self.assertEqual(result, 3)

    @db_session
    def test_get_str(self):
        x = 23
        result = get('p.id for p in Person if p.age > x')
        self.assertEqual(result, 3)

    @db_session
    def test_exists(self):
        x = 23
        result = exists(p for p in Person if p.age > x)
        self.assertEqual(result, True)

    @db_session
    def test_exists_str(self):
        x = 23
        result = exists('p for p in Person if p.age > x')
        self.assertEqual(result, True)

    @db_session
    def test_entity_get(self):
        x = 23
        p = Person.get(lambda p: p.age > x)
        self.assertEqual(p, Person[3])

    @db_session
    def test_entity_get_str(self):
        x = 23
        p = Person.get('lambda p: p.age > x')
        self.assertEqual(p, Person[3])

    @db_session
    def test_entity_get_by_sql(self):
        x = 25
        p = Person.get_by_sql('select * from Person where age = $x')
        self.assertEqual(p, Person[3])

    @db_session
    def test_entity_select_by_sql(self):
        x = 25
        p = Person.select_by_sql('select * from Person where age = $x')
        self.assertEqual(p, [ Person[3] ])

    @db_session
    def test_entity_exists(self):
        x = 23
        result = Person.exists(lambda p: p.age > x)
        self.assertTrue(result)

    @db_session
    def test_entity_exists_str(self):
        x = 23
        result = Person.exists('lambda p: p.age > x')
        self.assertTrue(result)

    @db_session
    def test_entity_select(self):
        x = 20
        result = Person.select(lambda p: p.age > x)[:]
        self.assertEqual(set(result), set([Person[1], Person[3]]))

    @db_session
    def test_entity_select_str(self):
        x = 20
        result = Person.select('lambda p: p.age > x')[:]
        self.assertEqual(set(result), set([Person[1], Person[3]]))

    @db_session
    def test_order_by(self):
        x = 20
        y = -1
        result = Person.select(lambda p: p.age > x).order_by(lambda p: p.age * y)[:]
        self.assertEqual(result, [Person[3], Person[1]])

    @db_session
    def test_order_by_str(self):
        x = 20
        y = -1
        result = Person.select('lambda p: p.age > x').order_by('p.age * y')[:]
        self.assertEqual(result, [Person[3], Person[1]])

    @db_session
    def test_filter(self):
        x = 20
        y = 'M'
        result = Person.select(lambda p: p.age > x).filter(lambda p: p.name.startswith(y))[:]
        self.assertEqual(result, [Person[3]])

    @db_session
    def test_filter_str(self):
        x = 20
        y = 'M'
        result = Person.select('lambda p: p.age > x').filter('p.name.startswith(y)')[:]
        self.assertEqual(result, [Person[3]])

    @db_session
    def test_db_select(self):
        x = 20
        result = db.select('name from Person where age > $x order by name')
        self.assertEqual(result, ['John', 'Mike'])

    @db_session
    def test_db_get(self):
        x = 18
        result = db.get('name from Person where age = $x')
        self.assertEqual(result, 'Mary')

    @db_session
    def test_db_execute(self):
        x = 18
        result = db.execute('select name from Person where age = $x').fetchone()
        self.assertEqual(result, ('Mary',))

    @db_session
    def test_db_exists(self):
        x = 18
        result = db.exists('name from Person where age = $x')
        self.assertEqual(result, True)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_lazy
import unittest

from pony.orm.core import *

class TestLazy(unittest.TestCase):
    def setUp(self):
        self.db = Database('sqlite', ':memory:')
        class X(self.db.Entity):
            a = Required(int)
            b = Required(unicode, lazy=True)
        self.X = X
        self.db.generate_mapping(create_tables=True)
        with db_session:
            x1 = X(a=1, b='first')
            x2 = X(a=2, b='second')
            x3 = X(a=3, b='third')

    @db_session
    def test_lazy_1(self):
        X = self.X
        x1 = X[1]
        self.assertIn(X.a, x1._vals_)
        self.assertNotIn(X.b, x1._vals_)
        b = x1.b
        self.assertEquals(b, 'first')

    @db_session
    def test_lazy_2(self):
        X = self.X
        x1 = X[1]
        x2 = X[2]
        x3 = X[3]
        self.assertNotIn(X.b, x1._vals_)
        self.assertNotIn(X.b, x2._vals_)
        self.assertNotIn(X.b, x3._vals_)
        b = x1.b
        self.assertIn(X.b, x1._vals_)
        self.assertNotIn(X.b, x2._vals_)
        self.assertNotIn(X.b, x3._vals_)

########NEW FILE########
__FILENAME__ = test_mapping
from __future__ import with_statement

import unittest
from pony.orm.core import *
from pony.orm.dbschema import DBSchemaError
from testutils import *

class TestColumnsMapping(unittest.TestCase):

    # raise exception if mapping table by default is not found
    @raises_exception(OperationalError, 'no such table: Student')
    def test_table_check1(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            name = PrimaryKey(str)
        sql = "drop table if exists Student;"
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()

    # no exception if table was specified
    def test_table_check2(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            name = PrimaryKey(str)
        sql = """
            drop table if exists Student;
            create table Student(
                name varchar(30)
            );
        """
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()
        self.assertEqual(db.schema.tables['Student'].column_list[0].name, 'name')

    # raise exception if specified mapping table is not found
    @raises_exception(OperationalError, 'no such table: Table1')
    def test_table_check3(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            _table_ = 'Table1'
            name = PrimaryKey(str)
        db.generate_mapping()

    # no exception if table was specified
    def test_table_check4(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            _table_ = 'Table1'
            name = PrimaryKey(str)
        sql = """
            drop table if exists Table1;
            create table Table1(
                name varchar(30)
            );
        """
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()
        self.assertEqual(db.schema.tables['Table1'].column_list[0].name, 'name')

    # 'id' field created if primary key is not defined
    @raises_exception(OperationalError, 'no such column: Student.id')
    def test_table_check5(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            name = Required(str)
        sql = """
            drop table if exists Student;
            create table Student(
                name varchar(30)
            );
        """
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()

    # 'id' field created if primary key is not defined
    def test_table_check6(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            name = Required(str)
        sql = """
            drop table if exists Student;
            create table Student(
                id integer primary key,
                name varchar(30)
            );
        """
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()
        self.assertEqual(db.schema.tables['Student'].column_list[0].name, 'id')

    @raises_exception(DBSchemaError, "Column 'name' already exists in table 'Student'")
    def test_table_check7(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            name = Required(str, column='name')
            record = Required(str, column='name')
        sql = """
            drop table if exists Student;
            create table Student(
                id integer primary key,
                name varchar(30)
            );
        """
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()
        self.assert_(False)

    # user can specify column name for an attribute
    def test_custom_column_name(self):
        db = Database('sqlite', ':memory:')
        class Student(db.Entity):
            name = PrimaryKey(str, column='name1')
        sql = """
            drop table if exists Student;
            create table Student(
                name1 varchar(30)
            );
        """
        with db_session:
            db.get_connection().executescript(sql)
        db.generate_mapping()
        self.assertEqual(db.schema.tables['Student'].column_list[0].name, 'name1')

    # Required-Required raises exception
    @raises_exception(ERDiagramError,
        'At least one attribute of one-to-one relationship Entity1.attr1 - Entity2.attr2 must be optional')
    def test_relations1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required("Entity2")
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required(Entity1)
        db.generate_mapping()

    # no exception Optional-Required
    def test_relations2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional("Entity2")
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Required(Entity1)
        db.generate_mapping(create_tables=True)

    # no exception Optional-Required(column)
    def test_relations3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required("Entity2", column='a')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)

    def test_relations4(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Required("Entity2")
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1, column='a')
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.attr1.columns, ['attr1'])
        self.assertEqual(Entity2.attr2.columns, ['a'])

    # no exception Optional-Optional
    def test_relations5(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional("Entity2")
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)

    # no exception Optional-Optional(column)
    def test_relations6(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional("Entity2", column='a')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)

    def test_relations7(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional("Entity2", column='a')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1, column='a1')
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.attr1.columns, ['a'])
        self.assertEqual(Entity2.attr2.columns, ['a1'])

    def test_columns1(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = PrimaryKey(int)
            attr1 = Set("Entity2")
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)
        column_list = db.schema.tables['Entity2'].column_list
        self.assertEqual(len(column_list), 2)
        self.assertEqual(column_list[0].name, 'id')
        self.assertEqual(column_list[1].name, 'attr2')

    def test_columns2(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            a = Required(int)
            b = Required(int)
            PrimaryKey(a, b)
            attr1 = Set("Entity2")
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)
        column_list = db.schema.tables['Entity2'].column_list
        self.assertEqual(len(column_list), 3)
        self.assertEqual(column_list[0].name, 'id')
        self.assertEqual(column_list[1].name, 'attr2_a')
        self.assertEqual(column_list[2].name, 'attr2_b')

    def test_columns3(self):
        db = Database('sqlite', ':memory:')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional('Entity2')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional(Entity1)
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.attr1.columns, ['attr1'])
        self.assertEqual(Entity2.attr2.columns, [])

    def test_columns4(self):
        db = Database('sqlite', ':memory:')
        class Entity2(db.Entity):
            id = PrimaryKey(int)
            attr2 = Optional('Entity1')
        class Entity1(db.Entity):
            id = PrimaryKey(int)
            attr1 = Optional(Entity2)
        db.generate_mapping(create_tables=True)
        self.assertEqual(Entity1.attr1.columns, ['attr1'])
        self.assertEqual(Entity2.attr2.columns, [])

    @raises_exception(ERDiagramError, "Mapping is not generated for entity 'E1'")
    def test_generate_mapping1(self):
        db = Database('sqlite', ':memory:')
        class E1(db.Entity):
            a1 = Required(int)
        select(e for e in E1)

    @raises_exception(ERDiagramError, "Mapping is not generated for entity 'E1'")
    def test_generate_mapping2(self):
        db = Database('sqlite', ':memory:')
        class E1(db.Entity):
            a1 = Required(int)
        e = E1(a1=1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_orm_query
from __future__ import with_statement

import unittest
from datetime import date
from decimal import Decimal
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Student(db.Entity):
    name = Required(unicode)
    scholarship = Optional(int)
    gpa = Optional(Decimal,3,1)
    group = Required('Group')
    dob = Optional(date)

class Group(db.Entity):
    number = PrimaryKey(int)
    students = Set(Student)

db.generate_mapping(create_tables=True)

with db_session:
    g1 = Group(number=1)
    Student(id=1, name='S1', group=g1, gpa=3.1)
    Student(id=2, name='S2', group=g1, gpa=3.2, scholarship=100, dob=date(2000, 01, 01))
    Student(id=3, name='S3', group=g1, gpa=3.3, scholarship=200, dob=date(2001, 01, 02))

class TestQuery(unittest.TestCase):
    def setUp(self):
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    @raises_exception(TypeError, "Cannot iterate over non-entity object")
    def test_exception1(self):
        g = Group[1]
        select(s for s in g.students)
    @raises_exception(ExprEvalError, "a raises NameError: name 'a' is not defined")
    def test_exception2(self):
        select(a for s in Student)
    @raises_exception(TypeError,"Incomparable types 'unicode' and 'list' in expression: s.name == x")
    def test_exception3(self):
        x = ['A']
        select(s for s in Student if s.name == x)
    @raises_exception(TypeError,"Function 'f1' cannot be used inside query")
    def test_exception4(self):
        def f1(x):
            return x + 1
        select(s for s in Student if f1(s.gpa) > 3)
    @raises_exception(NotImplementedError, "m1(s.gpa, 1) > 3")
    def test_exception5(self):
        class C1(object):
            def method1(self, a, b):
                return a + b
        c = C1()
        m1 = c.method1
        select(s for s in Student if m1(s.gpa, 1) > 3)
    @raises_exception(TypeError, "Expression x has unsupported type 'complex'")
    def test_exception6(self):
        x = 1j
        select(s for s in Student if s.gpa == x)
    def test1(self):
        select(g for g in Group for s in db.Student)
        self.assert_(True)
    def test2(self):
        avg_gpa = avg(s.gpa for s in Student)
        self.assertEqual(avg_gpa, Decimal('3.2'))
    def test21(self):
        avg_gpa = avg(s.gpa for s in Student if s.id < 0)
        self.assertEqual(avg_gpa, None)
    def test3(self):
        sum_ss = sum(s.scholarship for s in Student)
        self.assertEqual(sum_ss, 300)
    def test31(self):
        sum_ss = sum(s.scholarship for s in Student if s.id < 0)
        self.assertEqual(sum_ss, 0)
    @raises_exception(TranslationError, "'avg' is valid for numeric attributes only")
    def test4(self):
        avg(s.name for s in Student)
    def wrapper(self):
        return count(s for s in Student if s.scholarship > 0)
    def test5(self):
        c = self.wrapper()
        c = self.wrapper()
        self.assertEqual(c, 2)
    def test6(self):
        c = count(s.scholarship for s in Student if s.scholarship > 0)
        self.assertEqual(c, 2)
    def test7(self):
        s = get(s.scholarship for s in Student if s.id == 3)
        self.assertEqual(s, 200)
    def test8(self):
        s = get(s.scholarship for s in Student if s.id == 4)
        self.assertEqual(s, None)
    def test9(self):
        s = select(s for s in Student if s.id == 4).exists()
        self.assertEqual(s, False)
    def test10(self):
        r = min(s.scholarship for s in Student)
        self.assertEqual(r, 100)
    def test11(self):
        r = min(s.scholarship for s in Student if s.id < 2)
        self.assertEqual(r, None)
    def test12(self):
        r = max(s.scholarship for s in Student)
        self.assertEqual(r, 200)
    def test13(self):
        r = max(s.dob.year for s in Student)
        self.assertEqual(r, 2001)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_queries
from __future__ import with_statement

import re, os, os.path, sys, imp

from pony import orm
from pony.orm import core
from pony.orm.tests import testutils

core.suppress_debug_change = True

directive_re = re.compile(r'(\w+)(\s+[0-9\.]+)?:')
directive = module_name = None
statements = []
lines = []

def Schema(param):
    if not statement_used:
        print
        print 'Statement not used:'
        print
        print '\n'.join(statements)
        print
        sys.exit()
    assert len(lines) == 1
    global module_name
    module_name = lines[0].strip()

def SQLite(server_version):
    do_test('sqlite', server_version)

def MySQL(server_version):
    do_test('mysql', server_version)

def PostgreSQL(server_version):
    do_test('postgres', server_version)

def Oracle(server_version):
    do_test('oracle', server_version)

unavailable_providers = set()

def do_test(provider_name, raw_server_version):
    if provider_name in unavailable_providers: return
    testutils.TestDatabase.real_provider_name = provider_name
    testutils.TestDatabase.raw_server_version = raw_server_version
    core.Database = orm.Database = testutils.TestDatabase
    sys.modules.pop(module_name, None)
    try: __import__(module_name)
    except ImportError, e:
        print
        print 'ImportError for database provider %s:\n%s' % (provider_name, e)
        print
        unavailable_providers.add(provider_name)
        return
    module = sys.modules[module_name]
    globals = vars(module).copy()
    with orm.db_session:
        for statement in statements[:-1]:
            code = compile(statement, '<string>', 'exec')
            exec code in globals
        statement = statements[-1]
        try: last_code = compile(statement, '<string>', 'eval')
        except SyntaxError:
            last_code = compile(statement, '<string>', 'exec')
            exec last_code in globals
        else:
            result = eval(last_code, globals)
            if isinstance(result, core.Query): result = list(result)
        sql = module.db.sql
    expected_sql = '\n'.join(lines)
    if sql == expected_sql: print '+', provider_name, statements[-1]
    else:
        print '-', provider_name, statements[-1]
        print
        print 'Expected:'
        print expected_sql
        print
        print 'Got:'
        print sql
        print
    global statement_used
    statement_used = True

dirname, fname = os.path.split(__file__)
queries_fname = os.path.join(dirname, 'queries.txt')

def orphan_lines(lines):
    SQLite(None)
    lines[:] = []

statement_used = True
for raw_line in file(queries_fname):
    line = raw_line.strip()
    if not line: continue
    if line.startswith('#'): continue
    match = directive_re.match(line)
    if match:
        if directive:
            directive(directive_param)
            lines[:] = []
        elif lines: orphan_lines(lines)
        directive = eval(match.group(1))
        if match.group(2):
            directive_param = match.group(2)
        else: directive_param = None
    elif line.startswith('>>> '):
        if directive:
            directive(directive_param)
            lines[:] = []
            statements[:] = []
        elif lines: orphan_lines(lines)
        directive = None
        directive_param = None
        statements.append(line[4:])
        statement_used = False
    else:
        lines.append(raw_line.rstrip())

if directive:
    directive(directive_param)
elif lines:
    orphan_lines(lines)

########NEW FILE########
__FILENAME__ = test_query
import unittest

from testutils import *
from model1 import *

class TestQuery(unittest.TestCase):
    @raises_exception(TypeError, 'Cannot iterate over non-entity object')
    def test_query_1(self):
        select(s for s in [])
    @raises_exception(TypeError, 'Cannot iterate over non-entity object X')
    def test_query_2(self):
        X = [1, 2, 3]
        select('x for x in X')
    @db_session
    def test_first1(self):
        q = select(s for s in Student).order_by(Student.record)
        self.assertEquals(q.first(), Student[101])
    @db_session
    def test_first2(self):
        q = select((s.name, s.group) for s in Student)
        self.assertEquals(q.first(), ('Alex', Group['4145']))
    @db_session
    def test_first3(self):
        q = select(s for s in Student)
        self.assertEquals(q.first(), Student[101])
########NEW FILE########
__FILENAME__ = test_relations_m2m
from __future__ import with_statement

import unittest
from pony.orm.core import *

class TestManyToManyNonComposite(unittest.TestCase):

    def setUp(self):
        db = Database('sqlite', ':memory:')

        class Group(db.Entity):
            number = PrimaryKey(int)
            subjects = Set("Subject")

        class Subject(db.Entity):
            name = PrimaryKey(str)
            groups = Set(Group)

        self.db = db
        self.Group = Group
        self.Subject = Subject
        
        self.db.generate_mapping(create_tables=True)

        with db_session:
           g1 = Group(number=101)
           g2 = Group(number=102)
           s1 = Subject(name='Subj1')
           s2 = Subject(name='Subj2')
           s3 = Subject(name='Subj3')
           s4 = Subject(name='Subj4')
           g1.subjects = [ s1, s2 ]

    def test_1(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s = Subject.get(name='Subj1')
            g.subjects.add(s)

        with db_session:
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    def test_2(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s = Subject.get(name='Subj3')
            g.subjects.add(s)

        with db_session:
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2', 'Subj3'])

    def test_3(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s = Subject.get(name='Subj3')
            g.subjects.remove(s)

        with db_session:
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    def test_4(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s = Subject.get(name='Subj2')
            g.subjects.remove(s)

        with db_session:
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1'])

    def test_5(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s1, s2, s3, s4 = Subject.select()[:]
            g.subjects.remove([s1, s2])
            g.subjects.add([s3, s4])

        with db_session:
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj3', 'Subj4'])
            self.assertEqual(Group[101].subjects, set([Subject['Subj3'], Subject['Subj4']]))

    def test_6(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s = Subject.get(name='Subj3')
            g.subjects.add(s)
            g.subjects.remove(s)
            last_sql = db.last_sql

        with db_session:
            self.assertEqual(db.last_sql, last_sql)  # assert no DELETE statement on commit
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    def test_7(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s = Subject.get(name='Subj1')
            g.subjects.remove(s)
            g.subjects.add(s)
            last_sql = db.last_sql

        with db_session:
            self.assertEqual(db.last_sql, last_sql)  # assert no INSERT statement on commit
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    def test_8(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s1 = Subject.get(name='Subj1')
            s2 = Subject.get(name='Subj2')
            g.subjects.clear()
            g.subjects.add([s1, s2])
            last_sql = db.last_sql

        with db_session:
            self.assertEqual(db.last_sql, last_sql)  # assert no INSERT statement on commit
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    def test_9(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g2 = Group.get(number=102)
            s1 = Subject.get(name='Subj1')
            g2.subjects.add(s1)
            g2.subjects.clear()
            last_sql = db.last_sql

        with db_session:
            self.assertEqual(db.last_sql, last_sql)  # assert no DELETE statement on commit
            db_subjects = db.select('subject from Group_Subject where "group" = 102')
            self.assertEqual(db_subjects , [])

    def test_10(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s1, s2, s3, s4 = Subject.select()[:]
            g.subjects = [ s2, s3 ]

        with db_session:
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj2', 'Subj3'])

    def test_11(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s1, s2, s3, s4 = Subject.select()[:]
            g.subjects.remove(s2)
            g.subjects = [ s1, s2 ]
            last_sql = db.last_sql

        with db_session:
            self.assertEqual(db.last_sql, last_sql)  # assert no INSERT statement on commit
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    def test_12(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        with db_session:
            g = Group.get(number=101)
            s1, s2, s3, s4 = Subject.select()[:]
            g.subjects.add(s3)
            g.subjects = [ s1, s2 ]
            last_sql = db.last_sql

        with db_session:
            self.assertEqual(db.last_sql, last_sql)  # assert no DELETE statement on commit
            db_subjects = db.select('subject from Group_Subject where "group" = 101')
            self.assertEqual(db_subjects , ['Subj1', 'Subj2'])

    @db_session
    def test_13(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        g1 = Group[101]
        s1 = Subject['Subj1']
        self.assertTrue(s1 in g1.subjects)

        group_setdata = g1._vals_[Group.subjects]
        self.assertTrue(s1 in group_setdata)
        self.assertEqual(group_setdata.added, None)
        self.assertEqual(group_setdata.removed, None)
        
        subj_setdata = s1._vals_[Subject.groups]
        self.assertTrue(g1 in subj_setdata)
        self.assertEqual(subj_setdata.added, None)
        self.assertEqual(subj_setdata.removed, None)

        g1.subjects.remove(s1)
        self.assertTrue(s1 not in group_setdata)
        self.assertEqual(group_setdata.added, None)
        self.assertEqual(group_setdata.removed, set([ s1 ]))
        self.assertTrue(g1 not in subj_setdata)
        self.assertEqual(subj_setdata.added, None)
        self.assertEqual(subj_setdata.removed, set([ g1 ]))
        
        g1.subjects.add(s1)
        self.assertTrue(s1 in group_setdata)
        self.assertEqual(group_setdata.added, set())
        self.assertEqual(group_setdata.removed, set())
        self.assertTrue(g1 in subj_setdata)
        self.assertEqual(subj_setdata.added, set())
        self.assertEqual(subj_setdata.removed, set())

    @db_session
    def test_14(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        g = Group[101]
        e = g.subjects.is_empty()
        self.assertEquals(e, False)

        db._dblocal.last_sql = None
        e = g.subjects.is_empty()  # should take result from the cache
        self.assertEquals(e, False)
        self.assertEquals(db.last_sql, None)

        g = Group[102]
        e = g.subjects.is_empty()  # should take SQL from the SQL cache
        self.assertEquals(e, True)

        db._dblocal.last_sql = None
        e = g.subjects.is_empty()  # should take result from the cache
        self.assertEquals(e, True)
        self.assertEquals(db.last_sql, None)

    @db_session
    def test_15(self):
        db, Group = self.db, self.Group

        g = Group[101]
        c = len(g.subjects)
        self.assertEquals(c, 2)
        db._dblocal.last_sql = None
        e = g.subjects.is_empty()  # should take result from the cache
        self.assertEquals(e, False)
        self.assertEquals(db.last_sql, None)
        
        g = Group[102]
        c = len(g.subjects)
        self.assertEquals(c, 0)
        db._dblocal.last_sql = None
        e = g.subjects.is_empty()  # should take result from the cache
        self.assertEquals(e, True)
        self.assertEquals(db.last_sql, None)

    @db_session
    def test_16(self):
        db, Group, Subject = self.db, self.Group, self.Subject

        g = Group[101]
        s1 = Subject['Subj1']
        s3 = Subject['Subj3']
        c = g.subjects.count()
        self.assertEquals(c, 2)

        db._dblocal.last_sql = None
        c = g.subjects.count()  # should take count from the cache
        self.assertEquals(c, 2)
        self.assertEquals(db.last_sql, None)

        g.subjects.add(s3)
        db._dblocal.last_sql = None
        c = g.subjects.count()  # should take modified count from the cache
        self.assertEquals(c, 3)
        self.assertEquals(db.last_sql, None)

        g.subjects.remove(s1)
        db._dblocal.last_sql = None
        c = g.subjects.count()  # should take modified count from the cache
        self.assertEquals(c, 2)
        self.assertEquals(db.last_sql, None)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_relations_one2many
from __future__ import with_statement

import unittest
from testutils import *
from pony.orm.core import *

class TestOneToMany(unittest.TestCase):

    def setUp(self):
        db = Database('sqlite', ':memory:', create_db=True)

        class Student(db.Entity):
            id = PrimaryKey(int)
            name = Required(unicode)
            group = Required('Group')

        class Group(db.Entity):
            number = PrimaryKey(int)
            students = Set(Student)

        self.db = db
        self.Group = Group
        self.Student = Student

        db.generate_mapping(create_tables=True)

        with db_session:
            g101 = Group(number=101)
            g102 = Group(number=102)
            g103 = Group(number=103)
            s1 = Student(id=1, name='Student1', group=g101)
            s2 = Student(id=2, name='Student2', group=g101)
            s3 = Student(id=3, name='Student3', group=g102)
            s4 = Student(id=4, name='Student3', group=g102)

        db_session.__enter__()

    def tearDown(self):
        rollback()
        db_session.__exit__()

    @raises_exception(ConstraintError, 'Attribute Student[1].group is required')
    def test_1(self):
        self.Student[1].group = None

    @raises_exception(ConstraintError, 'Attribute Student[1].group is required')
    def test_2(self):
        Student, Group = self.Student, self.Group
        Student[2].delete()  # in order to make exception text deterministic
        Group[101].students = Group[102].students

    def test_3(self):
        db, Group, Student = self.db, self.Group, self.Student

        g = Group[101]
        s3 = Student[3]  # s3 is loaded now
        db._dblocal.last_sql = None
        g.students.add(s3)
        # Group.students.load should not attempt to load s3 from db
        self.assertEquals(db.last_sql, None)

    def test_4(self):
        db, Group, Student = self.db, self.Group, self.Student

        g = Group[101]
        e = g.students.is_empty()
        self.assertEquals(e, False)

        db._dblocal.last_sql = None
        e = g.students.is_empty()  # should take result from the cache
        self.assertEquals(e, False)
        self.assertEquals(db.last_sql, None)

        g = Group[103]
        e = g.students.is_empty()  # should take SQL from the SQL cache
        self.assertEquals(e, True)

        db._dblocal.last_sql = None
        e = g.students.is_empty()  # should take result from the cache
        self.assertEquals(e, True)
        self.assertEquals(db.last_sql, None)

    def test_5(self):
        db, Group = self.db, self.Group

        g = Group[101]
        c = len(g.students)
        self.assertEquals(c, 2)
        db._dblocal.last_sql = None
        e = g.students.is_empty()  # should take result from the cache
        self.assertEquals(e, False)
        self.assertEquals(db.last_sql, None)
        
        g = Group[102]
        c = g.students.count()
        self.assertEquals(c, 2)
        db._dblocal.last_sql = None
        e = g.students.is_empty()  # should take result from the cache
        self.assertEquals(e, False)
        self.assertEquals(db.last_sql, None)

        g = Group[103]
        c = len(g.students)
        self.assertEquals(c, 0)
        db._dblocal.last_sql = None
        e = g.students.is_empty()  # should take result from the cache
        self.assertEquals(e, True)
        self.assertEquals(db.last_sql, None)

    def test_6(self):
        db, Group, Student = self.db, self.Group, self.Student

        g = Group[101]
        s3 = Student[3]
        c = g.students.count()
        self.assertEquals(c, 2)

        db._dblocal.last_sql = None
        c = g.students.count()  # should take count from the cache
        self.assertEquals(c, 2)
        self.assertEquals(db.last_sql, None)

        g.students.add(s3)
        c = g.students.count()  # should take modified count from the cache
        self.assertEquals(c, 3)
        self.assertEquals(db.last_sql, None)

        g2 = Group[102]
        c = g2.students.count()  # should send query to the database
        self.assertEquals(c, 1)
        self.assertTrue(db.last_sql is not None)

    def test_7_rbits(self):
        Group, Student = self.Group, self.Student
        g = Group[101]

        s1 = Student[1]
        self.assertEquals(s1._rbits_, 0)
        self.assertTrue(s1 in g.students)
        self.assertEquals(s1._rbits_, Student._bits_[Student.group])

        s3 = Student[3]
        self.assertEquals(s3._rbits_, 0)
        self.assertTrue(s3 not in g.students)
        self.assertEquals(s3._rbits_, Student._bits_[Student.group])

        s5 = Student(id=5, name='Student5', group=g)
        self.assertEquals(s5._rbits_, None)
        self.assertTrue(s5 in g.students)
        self.assertEquals(s5._rbits_, None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_relations_one2one1
from __future__ import with_statement

import unittest
from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Male(db.Entity):
    name = Required(unicode)
    wife = Optional('Female', column='wife')

class Female(db.Entity):
    name = Required(unicode)
    husband = Optional('Male')

db.generate_mapping(create_tables=True)

class TestOneToOne(unittest.TestCase):
    def setUp(self):
        with db_session:
            db.execute('delete from male')
            db.execute('delete from female')
            db.insert('female', id=1, name='F1')
            db.insert('female', id=2, name='F2')
            db.insert('female', id=3, name='F3')
            db.insert('male', id=1, name='M1', wife=1)
            db.insert('male', id=2, name='M2', wife=2)
            db.insert('male', id=3, name='M3', wife=None)
        db_session.__enter__()
    def tearDown(self):
        db_session.__exit__()
    def test_1(self):
        Male[3].wife = Female[3]

        self.assertEqual(Male[3]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[3]._vals_[Female.husband], Male[3])
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([1, 2, 3], wives)
    def test_2(self):
        Female[3].husband = Male[3]

        self.assertEqual(Male[3]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[3]._vals_[Female.husband], Male[3])
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([1, 2, 3], wives)
    def test_3(self):
        Male[1].wife = None

        self.assertEqual(Male[1]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([None, 2, None], wives)
    def test_4(self):
        Female[1].husband = None

        self.assertEqual(Male[1]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([None, 2, None], wives)
    def test_5(self):
        Male[1].wife = Female[3]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[3]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([3, 2, None], wives)
    def test_6(self):
        Female[3].husband = Male[1]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[3]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([3, 2, None], wives)
    def test_7(self):
        Male[1].wife = Female[2]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[2])
        self.assertEqual(Male[2]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[2]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([2, None, None], wives)
    def test_8(self):
        Female[2].husband = Male[1]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[2])
        self.assertEqual(Male[2]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[2]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from Male order by Male.id')
        self.assertEqual([2, None, None], wives)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_relations_one2one2
from __future__ import with_statement

import unittest
from pony.orm.core import *
from testutils import *

db = Database('sqlite', ':memory:')

class Male(db.Entity):
    name = Required(unicode)
    wife = Optional('Female', column='wife')

class Female(db.Entity):
    name = Required(unicode)
    husband = Optional('Male', column='husband')

db.generate_mapping(create_tables=True)

class TestOneToOne2(unittest.TestCase):
    def setUp(self):
        with db_session:
            db.execute('update female set husband=null')
            db.execute('update male set wife=null')
            db.execute('delete from male')
            db.execute('delete from female')
            db.insert('female', id=1, name='F1')
            db.insert('female', id=2, name='F2')
            db.insert('female', id=3, name='F3')
            db.insert('male', id=1, name='M1', wife=1)
            db.insert('male', id=2, name='M2', wife=2)
            db.insert('male', id=3, name='M3', wife=None)
            db.execute('update female set husband=1 where id=1')
            db.execute('update female set husband=2 where id=2')
        db_session.__enter__()
    def tearDown(self):
        db_session.__exit__()
    def test_1(self):
        Male[3].wife = Female[3]

        self.assertEqual(Male[3]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[3]._vals_[Female.husband], Male[3])
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([1, 2, 3], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([1, 2, 3], husbands)
    def test_2(self):
        Female[3].husband = Male[3]

        self.assertEqual(Male[3]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[3]._vals_[Female.husband], Male[3])
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([1, 2, 3], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([1, 2, 3], husbands)
    def test_3(self):
        Male[1].wife = None

        self.assertEqual(Male[1]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([None, 2, None], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([None, 2, None], husbands)
    def test_4(self):
        Female[1].husband = None

        self.assertEqual(Male[1]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([None, 2, None], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([None, 2, None], husbands)
    def test_5(self):
        Male[1].wife = Female[3]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[3]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([3, 2, None], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([None, 2, 1], husbands)
    def test_6(self):
        Female[3].husband = Male[1]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[3])
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[3]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([3, 2, None], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([None, 2, 1], husbands)
    def test_7(self):
        Male[1].wife = Female[2]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[2])
        self.assertEqual(Male[2]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[2]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([2, None, None], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([None, 1, None], husbands)
    def test_8(self):
        Female[2].husband = Male[1]

        self.assertEqual(Male[1]._vals_[Male.wife], Female[2])
        self.assertEqual(Male[2]._vals_[Male.wife], None)
        self.assertEqual(Female[1]._vals_[Female.husband], None)
        self.assertEqual(Female[2]._vals_[Female.husband], Male[1])
        commit()
        wives = db.select('wife from male order by male.id')
        self.assertEqual([2, None, None], wives)
        husbands = db.select('husband from female order by female.id')
        self.assertEqual([None, 1, None], husbands)
    @raises_exception(UnrepeatableReadError, 'Value of Male.wife for Male[1] was updated outside of current transaction')
    def test_9(self):
        db.execute('update female set husband = 3 where id = 1')
        m1 = Male[1]
        f1 = m1.wife
        f1.name
    def test_10(self):
        db.execute('update female set husband = 3 where id = 1')
        m1 = Male[1]
        f1 = Female[1]
        f1.name
        self.assert_(Male.wife not in m1._vals_)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_relations_symmetric_m2m
from __future__ import with_statement

import unittest
from pony.orm.core import *

db = Database('sqlite', ':memory:')

class Person(db.Entity):
    name = Required(unicode)
    friends = Set('Person', reverse='friends')
db.generate_mapping(create_tables=True)


class TestSymmetric(unittest.TestCase):
    def setUp(self):
        rollback()
        with db_session:
            for p in Person.select(): p.delete()
            commit()
            db.insert('person', id=1, name='A')
            db.insert('person', id=2, name='B')
            db.insert('person', id=3, name='C')
            db.insert('person', id=4, name='D')
            db.insert('person', id=5, name='E')
            db.insert('person_friends', person=1, person_2=2)
            db.insert('person_friends', person=2, person_2=1)
            db.insert('person_friends', person=1, person_2=3)
            db.insert('person_friends', person=3, person_2=1)
        rollback()
        db_session.__enter__()
    def tearDown(self):
        rollback()
        db_session.__exit__()
    def test1a(self):
        p1 = Person[1]
        p4 = Person[4]
        p1.friends.add(p4)
        self.assertEqual(set(p4.friends), set([p1]))
    def test1b(self):
        p1 = Person[1]
        p4 = Person[4]
        p1.friends.add(p4)
        self.assertEqual(set(p1.friends), set([Person[2], Person[3], p4]))
    def test1c(self):
        p1 = Person[1]
        p4 = Person[4]
        p1.friends.add(p4)
        commit()
        rows = db.select("* from person_friends order by person, person_2")
        self.assertEqual(rows, [(1,2), (1,3), (1,4), (2,1), (3,1), (4,1)])

    def test2a(self):
        p1 = Person[1]
        p2 = Person[2]
        p1.friends.remove(p2)
        self.assertEqual(set(p1.friends), set([Person[3]]))
    def test2b(self):
        p1 = Person[1]
        p2 = Person[2]
        p1.friends.remove(p2)
        self.assertEqual(set(Person[3].friends), set([p1]))
    def test2c(self):
        p1 = Person[1]
        p2 = Person[2]
        p1.friends.remove(p2)
        self.assertEqual(set(p2.friends), set())
    def test2d(self):
        p1 = Person[1]
        p2 = Person[2]
        p1.friends.remove(p2)
        commit()
        rows = db.select("* from person_friends order by person, person_2")
        self.assertEqual(rows, [(1,3), (3,1)])

    def test3a(self):
        db.execute('delete from person_friends')
        db.insert('person_friends', person=1, person_2=2)
        p1 = Person[1]
        p2 = Person[2]
        p2_friends = set(p2.friends)
        self.assertEqual(p2_friends, set())
        try:
            p1_friends = set(p1.friends)
        except UnrepeatableReadError, e:
            self.assertEqual(e.args[0], "Phantom object Person[1] appeared in collection Person[2].friends")
        else: self.assert_(False)
    def test3b(self):
        db.execute('delete from person_friends')
        db.insert('person_friends', person=1, person_2=2)
        p1 = Person[1]
        p2 = Person[2]
        p1_friends = set(p1.friends)
        self.assertEqual(p1_friends, set([p2]))
        try:
            p2_friends = set(p2.friends)
        except UnrepeatableReadError, e:
            self.assertEqual(e.args[0], "Phantom object Person[1] disappeared from collection Person[2].friends")
        else: self.assert_(False)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_relations_symmetric_one2one
import unittest
from pony.orm.core import *
from testutils import raises_exception

db = Database('sqlite', ':memory:')

class Person(db.Entity):
    name = Required(unicode)
    spouse = Optional('Person', reverse='spouse')

db.generate_mapping(create_tables=True)

class TestSymmetric(unittest.TestCase):
    def setUp(self):
        rollback()
        db.execute('update person set spouse=null')
        db.execute('delete from person')
        db.insert('person', id=1, name='A')
        db.insert('person', id=2, name='B', spouse=1)
        db.execute('update person set spouse=2 where id=1')
        db.insert('person', id=3, name='C')
        db.insert('person', id=4, name='D', spouse=3)
        db.execute('update person set spouse=4 where id=3')
        db.insert('person', id=5, name='E', spouse=None)
        commit()
        rollback()
    def test1(self):
        p1 = Person[1]
        p2 = Person[2]
        p5 = Person[5]
        p1.spouse = p5
        commit()
        self.assertEqual(p1._vals_.get('spouse'), p5)
        self.assertEqual(p5._vals_.get('spouse'), p1)
        self.assertEqual(p2._vals_.get('spouse'), None)
        data = db.select('spouse from person order by id')
        self.assertEqual([5, None, 4, 3, 1], data)
    def test2(self):
        p1 = Person[1]
        p2 = Person[2]
        p1.spouse = None
        commit()
        self.assertEqual(p1._vals_.get('spouse'), None)
        self.assertEqual(p2._vals_.get('spouse'), None)
        data = db.select('spouse from person order by id')
        self.assertEqual([None, None, 4, 3, None], data)
    def test3(self):
        p1 = Person[1]
        p2 = Person[2]
        p3 = Person[3]
        p4 = Person[4]
        p1.spouse = p3
        commit()
        self.assertEqual(p1._vals_.get('spouse'), p3)
        self.assertEqual(p2._vals_.get('spouse'), None)
        self.assertEqual(p3._vals_.get('spouse'), p1)
        self.assertEqual(p4._vals_.get('spouse'), None)
        data = db.select('spouse from person order by id')
        self.assertEqual([3, None, 1, None, None], data)
    def test4(self):
        persons = set(select(p for p in Person if p.spouse.name in ('B', 'D')))
        self.assertEqual(persons, set([Person[1], Person[3]]))
    @raises_exception(OptimisticCheckError, 'Value of Person.spouse for Person[1] was updated outside of current transaction')
    def test5(self):
        db.execute('update person set spouse = 3 where id = 2')
        p1 = Person[1]
        p1.spouse
        p2 = Person[2]
        p2.name
    def test6(self):
        db.execute('update person set spouse = 3 where id = 2')
        p1 = Person[1]
        p2 = Person[2]
        p2.name
        p1.spouse
        self.assertEqual(p2._vals_.get('spouse'), p1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sqlbuilding_formatstyles
import unittest
from pony.orm.sqlsymbols import *
from pony.orm.sqlbuilding import SQLBuilder
from pony.orm.dbapiprovider import DBAPIProvider
from pony.orm.tests.testutils import TestPool

class TestFormatStyles(unittest.TestCase):
    def setUp(self):
        self.key1 = object()
        self.key2 = object()
        self.provider = DBAPIProvider(pony_pool_mockup=TestPool(None))
        self.ast = [ SELECT, [ ALL, [COLUMN, None, 'A']], [ FROM, [None, TABLE, 'T1']],
                     [ WHERE, [ EQ, [COLUMN, None, 'B'], [ PARAM, self.key1 ] ],
                              [ EQ, [COLUMN, None, 'C'], [ PARAM, self.key2 ] ],
                              [ EQ, [COLUMN, None, 'D'], [ PARAM, self.key2 ] ],
                              [ EQ, [COLUMN, None, 'E'], [ PARAM, self.key1 ] ]
                     ]
                   ]
    def test_qmark(self):
        self.provider.paramstyle = 'qmark'
        b = SQLBuilder(self.provider, self.ast)
        self.assertEqual(b.sql, 'SELECT "A"\n'
                                'FROM "T1"\n'
                                'WHERE "B" = ?\n  AND "C" = ?\n  AND "D" = ?\n  AND "E" = ?')
        self.assertEqual(b.layout, (self.key1, self.key2, self.key2, self.key1))
    def test_numeric(self):
        self.provider.paramstyle = 'numeric'
        b = SQLBuilder(self.provider, self.ast)
        self.assertEqual(b.sql, 'SELECT "A"\n'
                                'FROM "T1"\n'
                                'WHERE "B" = :1\n  AND "C" = :2\n  AND "D" = :2\n  AND "E" = :1')
        self.assertEqual(b.layout, (self.key1, self.key2))
    def test_named(self):
        self.provider.paramstyle = 'named'
        b = SQLBuilder(self.provider, self.ast)
        self.assertEqual(b.sql, 'SELECT "A"\n'
                                'FROM "T1"\n'
                                'WHERE "B" = :p1\n  AND "C" = :p2\n  AND "D" = :p2\n  AND "E" = :p1')
        self.assertEqual(b.layout, (self.key1, self.key2))
    def test_format(self):
        self.provider.paramstyle = 'format'
        b = SQLBuilder(self.provider, self.ast)
        self.assertEqual(b.sql, 'SELECT "A"\n'
                                'FROM "T1"\n'
                                'WHERE "B" = %s\n  AND "C" = %s\n  AND "D" = %s\n  AND "E" = %s')
        self.assertEqual(b.layout, (self.key1, self.key2, self.key2, self.key1))
    def test_pyformat(self):
        self.provider.paramstyle = 'pyformat'
        b = SQLBuilder(self.provider, self.ast)
        self.assertEqual(b.sql, 'SELECT "A"\n'
                                'FROM "T1"\n'
                                'WHERE "B" = %(p1)s\n  AND "C" = %(p2)s\n  AND "D" = %(p2)s\n  AND "E" = %(p1)s')
        self.assertEqual(b.layout, (self.key1, self.key2))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sqlbuilding_sqlast
from __future__ import with_statement

import unittest
from pony.orm.core import Database, db_session
from pony.orm.sqlsymbols import *

class TestSQLAST(unittest.TestCase):
    def setUp(self):
        self.db = Database('sqlite', ':memory:')
        with db_session:
            conn = self.db.get_connection()
            conn.executescript("""
            create table if not exists T1(
                a integer primary key,
                b varchar(20) not null
                );
            insert or ignore into T1 values(1, 'abc');
            """)
    @db_session
    def test_alias(self):
        sql_ast = [SELECT, [ALL, [COLUMN, "Group", "a"]],
                           [FROM, ["Group", TABLE, "T1" ]]]
        sql, adapter = self.db._ast2sql(sql_ast)
        cursor = self.db._exec_sql(sql)
    @db_session
    def test_alias2(self):
        sql_ast = [SELECT, [ALL, [COLUMN, None, "a"]],
                            [FROM, [None, TABLE, "T1"]]]
        sql, adapter = self.db._ast2sql(sql_ast)
        cursor = self.db._exec_sql(sql)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = decorator
##########################     LICENCE     ###############################

# Copyright (c) 2005-2012, Michele Simionato
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#   Redistributions of source code must retain the above copyright 
#   notice, this list of conditions and the following disclaimer.
#   Redistributions in bytecode form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution. 

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

"""
Decorator module, see http://pypi.python.org/pypi/decorator
for the documentation.
"""

__version__ = '3.4.0'

__all__ = ["decorator", "FunctionMaker", "contextmanager"]

import sys, re, inspect
if sys.version >= '3':
    from inspect import getfullargspec
    def get_init(cls):
        return cls.__init__
else:
    class getfullargspec(object):
        "A quick and dirty replacement for getfullargspec for Python 2.X"
        def __init__(self, f):
            self.args, self.varargs, self.varkw, self.defaults = \
                inspect.getargspec(f)
            self.kwonlyargs = []
            self.kwonlydefaults = None
        def __iter__(self):
            yield self.args
            yield self.varargs
            yield self.varkw
            yield self.defaults
    def get_init(cls):
        return cls.__init__.im_func

DEF = re.compile('\s*def\s*([_\w][_\w\d]*)\s*\(')

# basic functionality
class FunctionMaker(object):
    """
    An object with the ability to create functions with a given signature.
    It has attributes name, doc, module, signature, defaults, dict and
    methods update and make.
    """
    def __init__(self, func=None, name=None, signature=None,
                 defaults=None, doc=None, module=None, funcdict=None):
        self.shortsignature = signature
        if func:
            # func can be a class or a callable, but not an instance method
            self.name = func.__name__
            if self.name == '<lambda>': # small hack for lambda functions
                self.name = '_lambda_' 
            self.doc = func.__doc__
            self.module = func.__module__
            if inspect.isfunction(func):
                argspec = getfullargspec(func)
                self.annotations = getattr(func, '__annotations__', {})
                for a in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs',
                          'kwonlydefaults'):
                    setattr(self, a, getattr(argspec, a))
                for i, arg in enumerate(self.args):
                    setattr(self, 'arg%d' % i, arg)
                if sys.version < '3': # easy way
                    self.shortsignature = self.signature = \
                        inspect.formatargspec(
                        formatvalue=lambda val: "", *argspec)[1:-1]
                else: # Python 3 way
                    allargs = list(self.args)
                    allshortargs = list(self.args)
                    if self.varargs:
                        allargs.append('*' + self.varargs)
                        allshortargs.append('*' + self.varargs)
                    elif self.kwonlyargs:
                        allargs.append('*') # single star syntax
                    for a in self.kwonlyargs:
                        allargs.append('%s=None' % a)
                        allshortargs.append('%s=%s' % (a, a))
                    if self.varkw:
                        allargs.append('**' + self.varkw)
                        allshortargs.append('**' + self.varkw)
                    self.signature = ', '.join(allargs)
                    self.shortsignature = ', '.join(allshortargs)
                self.dict = func.__dict__.copy()
        # func=None happens when decorating a caller
        if name:
            self.name = name
        if signature is not None:
            self.signature = signature
        if defaults:
            self.defaults = defaults
        if doc:
            self.doc = doc
        if module:
            self.module = module
        if funcdict:
            self.dict = funcdict
        # check existence required attributes
        assert hasattr(self, 'name')
        if not hasattr(self, 'signature'):
            raise TypeError('You are decorating a non function: %s' % func)

    def update(self, func, **kw):
        "Update the signature of func with the data in self"
        func.__name__ = self.name
        func.__doc__ = getattr(self, 'doc', None)
        func.__dict__ = getattr(self, 'dict', {})
        func.func_defaults = getattr(self, 'defaults', ())
        func.__kwdefaults__ = getattr(self, 'kwonlydefaults', None)
        func.__annotations__ = getattr(self, 'annotations', None)
        callermodule = sys._getframe(3).f_globals.get('__name__', '?')
        func.__module__ = getattr(self, 'module', callermodule)
        func.__dict__.update(kw)

    def make(self, src_templ, evaldict=None, addsource=False, **attrs):
        "Make a new function from a given template and update the signature"
        src = src_templ % vars(self) # expand name and signature
        evaldict = evaldict or {}
        mo = DEF.match(src)
        if mo is None:
            raise SyntaxError('not a valid function template\n%s' % src)
        name = mo.group(1) # extract the function name
        names = set([name] + [arg.strip(' *') for arg in 
                             self.shortsignature.split(',')])
        for n in names:
            if n in ('_func_', '_call_'):
                raise NameError('%s is overridden in\n%s' % (n, src))
        if not src.endswith('\n'): # add a newline just for safety
            src += '\n' # this is needed in old versions of Python
        try:
            # print src
            code = compile(src, '<auto generated wrapper of %s() function>' % self.name, 'single')
            # print >> sys.stderr, 'Compiling %s' % src
            exec code in evaldict
        except:
            print >> sys.stderr, 'Error in generated code:'
            print >> sys.stderr, src
            raise
        func = evaldict[name]
        if addsource:
            attrs['__source__'] = src
        self.update(func, **attrs)
        return func

    @classmethod
    def create(cls, obj, body, evaldict, defaults=None,
               doc=None, module=None, addsource=True, **attrs):
        """
        Create a function from the strings name, signature and body.
        evaldict is the evaluation dictionary. If addsource is true an attribute
        __source__ is added to the result. The attributes attrs are added,
        if any.
        """
        if isinstance(obj, str): # "name(signature)"
            name, rest = obj.strip().split('(', 1)
            signature = rest[:-1] #strip a right parens            
            func = None
        else: # a function
            name = None
            signature = None
            func = obj
        self = cls(func, name, signature, defaults, doc, module)
        ibody = '\n'.join('    ' + line for line in body.splitlines())
        return self.make('def %(name)s(%(signature)s):\n' + ibody, 
                        evaldict, addsource, **attrs)
  
def decorator(caller, func=None):
    """
    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.
    """
    if func is not None: # returns a decorated function
        evaldict = func.func_globals.copy()
        evaldict['_call_'] = caller
        evaldict['_func_'] = func
        return FunctionMaker.create(
            func, "return _call_(_func_, %(shortsignature)s)",
            evaldict, undecorated=func, __wrapped__=func)
    else: # returns a decorator
        if inspect.isclass(caller):
            name = caller.__name__.lower()
            callerfunc = get_init(caller)
            doc = 'decorator(%s) converts functions/generators into ' \
                'factories of %s objects' % (caller.__name__, caller.__name__)
            fun = getfullargspec(callerfunc).args[1] # second arg
        elif inspect.isfunction(caller):
            name = '_lambda_' if caller.__name__ == '<lambda>' \
                else caller.__name__
            callerfunc = caller
            doc = caller.__doc__
            fun = getfullargspec(callerfunc).args[0] # first arg
        else: # assume caller is an object with a __call__ method
            name = caller.__class__.__name__.lower()
            callerfunc = caller.__call__.im_func
            doc = caller.__call__.__doc__
            fun = getfullargspec(callerfunc).args[1] # second arg
        evaldict = callerfunc.func_globals.copy()
        evaldict['_call_'] = caller
        evaldict['decorator'] = decorator
        return FunctionMaker.create(
            '%s(%s)' % (name, fun), 
            'return decorator(_call_, %s)' % fun,
            evaldict, undecorated=caller, __wrapped__=caller,
            doc=doc, module=caller.__module__)

######################### contextmanager ########################

def __call__(self, func):
    'Context manager decorator'
    return FunctionMaker.create(
        func, "with _self_: return _func_(%(shortsignature)s)",
        dict(_self_=self, _func_=func), __wrapped__=func)

try: # Python >= 3.2

    from contextlib import _GeneratorContextManager 
    ContextManager = type(
        'ContextManager', (_GeneratorContextManager,), dict(__call__=__call__))

except ImportError: # Python >= 2.5

    from contextlib import GeneratorContextManager
    def __init__(self, f, *a, **k):
        return GeneratorContextManager.__init__(self, f(*a, **k))
    ContextManager = type(
        'ContextManager', (GeneratorContextManager,), 
        dict(__call__=__call__, __init__=__init__))
    
contextmanager = decorator(ContextManager)

########NEW FILE########
__FILENAME__ = utils
#coding: cp1251

import re, os, os.path, sys, datetime, types, linecache, warnings

from itertools import count as _count
from inspect import isfunction, ismethod, getargspec
from time import strptime
from os import urandom
from codecs import BOM_UTF8, BOM_LE, BOM_BE
from locale import getpreferredencoding
from bisect import bisect
from collections import defaultdict
from copy import deepcopy, _deepcopy_dispatch
from functools import update_wrapper
from compiler import ast

# deepcopy instance method patch for Python < 2.7:
if types.MethodType not in _deepcopy_dispatch:
    def _deepcopy_method(x, memo):
        return type(x)(x.im_func, deepcopy(x.im_self, memo), x.im_class)
    _deepcopy_dispatch[types.MethodType] = _deepcopy_method

import pony
from pony import options

from pony.thirdparty.decorator import decorator as _decorator

try: from pony.thirdparty import etree
except ImportError: etree = None

if pony.MODE.startswith('GAE-'): localbase = object
else: from threading import local as localbase

class PonyDeprecationWarning(DeprecationWarning):
    pass

def deprecated(stacklevel, message):
    warnings.warn(message, PonyDeprecationWarning, stacklevel)

warnings.simplefilter('once', PonyDeprecationWarning)

def _improved_decorator(caller, func):
    if isfunction(func):
        return _decorator(caller, func)
    def pony_wrapper(*args, **kwargs):
        return caller(func, *args, **kwargs)
    return pony_wrapper

def decorator(caller, func=None):
    if func is not None:
        return _improved_decorator(caller, func)
    def new_decorator(func):
        return _improved_decorator(caller, func)
    if isfunction(caller):
        update_wrapper(new_decorator, caller)
    return new_decorator

##def simple_decorator(dec):
##    def new_dec(func):
##        def pony_wrapper(*args, **kwargs):
##            return dec(func, *args, **kwargs)
##        return copy_func_attrs(pony_wrapper, func, dec.__name__)
##    return copy_func_attrs(new_dec, dec, 'simple_decorator')

##@simple_decorator
##def decorator_with_params(dec, *args, **kwargs):
##    if len(args) == 1 and not kwargs:
##        func = args[0]
##        new_func = dec(func)
##        return copy_func_attrs(new_func, func, dec.__name__)
##    def parameterized_decorator(old_func):
##        new_func = dec(func, *args, **kwargs)
##        return copy_func_attrs(new_func, func, dec.__name__)
##    return parameterized_decorator

def decorator_with_params(dec):
    def parameterized_decorator(*args, **kwargs):
        if len(args) == 1 and isfunction(args[0]) and not kwargs:
            return decorator(dec(), args[0])
        return decorator(dec(*args, **kwargs))
    return parameterized_decorator

@decorator_with_params
def with_headers(**headers):
    def new_dec(func, *args, **kwargs):
        print 'headers:', headers
        return func(*args, **kwargs)
    return new_dec

@with_headers(x=10, y=20)
def mul(a, b):
    return a * b

@decorator
def cut_traceback(func, *args, **kwargs):
    if not (pony.MODE == 'INTERACTIVE' and options.CUT_TRACEBACK):
        return func(*args, **kwargs)

    try: return func(*args, **kwargs)
    except AssertionError: raise
    except Exception:
        exc_type, exc, tb = sys.exc_info()
        last_pony_tb = None
        try:
            while tb.tb_next:
                module_name = tb.tb_frame.f_globals['__name__']
                if module_name == 'pony' or (module_name is not None  # may be None during import
                                             and module_name.startswith('pony.')):
                    last_pony_tb = tb
                tb = tb.tb_next
            if last_pony_tb is None: raise
            if tb.tb_frame.f_globals.get('__name__') == 'pony.utils' and tb.tb_frame.f_code.co_name == 'throw':
                raise exc_type, exc, last_pony_tb
            raise exc  # Set "pony.options.CUT_TRACEBACK = False" to see full traceback
        finally:
            del tb, last_pony_tb

def throw(exc_type, *args, **kwargs):
    if isinstance(exc_type, Exception):
        assert not args and not kwargs
        exc = exc_type
    else: exc = exc_type(*args, **kwargs)
    if not (pony.MODE == 'INTERACTIVE' and options.CUT_TRACEBACK):
        raise exc
    else:
        raise exc  # Set "pony.options.CUT_TRACEBACK = False" to see full traceback

lambda_args_cache = {}

def get_lambda_args(func):
    names = lambda_args_cache.get(func)
    if names is not None: return names
    if type(func) is types.FunctionType:
        names, argsname, kwname, defaults = getargspec(func)
    elif isinstance(func, ast.Lambda):
        names = func.argnames
        if func.kwargs: names, kwname = names[:-1], names[-1]
        else: kwname = None
        if func.varargs: names, argsname = names[:-1], names[-1]
        else: argsname = None
        defaults = func.defaults
    else: assert False
    if argsname: throw(TypeError, '*%s is not supported' % argsname)
    if kwname: throw(TypeError, '**%s is not supported' % kwname)
    if defaults: throw(TypeError, 'Defaults are not supported')
    lambda_args_cache[func] = names
    return names

_cache = {}
MAX_CACHE_SIZE = 1000

@decorator
def cached(f, *args, **kwargs):
    key = (f, args, tuple(sorted(kwargs.items())))
    value = _cache.get(key)
    if value is not None: return value
    if len(_cache) == MAX_CACHE_SIZE: _cache.clear()
    return _cache.setdefault(key, f(*args, **kwargs))

def error_method(*args, **kwargs):
    raise TypeError

_ident_re = re.compile(r'^[A-Za-z_]\w*\Z')

# is_ident = ident_re.match
def is_ident(string):
    'is_ident(string) -> bool'
    return bool(_ident_re.match(string))

_name_parts_re = re.compile(r'''
            [A-Z][A-Z0-9]+(?![a-z]) # ACRONYM
        |   [A-Z][a-z]*             # Capitalized or single capital
        |   [a-z]+                  # all-lowercase
        |   [0-9]+                  # numbers
        |   _+                      # underscores
        ''', re.VERBOSE)

def split_name(name):
    "split_name('Some_FUNNYName') -> ['Some', 'FUNNY', 'Name']"
    if not _ident_re.match(name):
        raise ValueError('Name is not correct Python identifier')
    list = _name_parts_re.findall(name)
    if not (list[0].strip('_') and list[-1].strip('_')):
        raise ValueError('Name must not starting or ending with underscores')
    return [ s for s in list if s.strip('_') ]

def uppercase_name(name):
    "uppercase_name('Some_FUNNYName') -> 'SOME_FUNNY_NAME'"
    return '_'.join(s.upper() for s in split_name(name))

def lowercase_name(name):
    "uppercase_name('Some_FUNNYName') -> 'some_funny_name'"
    return '_'.join(s.lower() for s in split_name(name))

def camelcase_name(name):
    "uppercase_name('Some_FUNNYName') -> 'SomeFunnyName'"
    return ''.join(s.capitalize() for s in split_name(name))

def mixedcase_name(name):
    "mixedcase_name('Some_FUNNYName') -> 'someFunnyName'"
    list = split_name(name)
    return list[0].lower() + ''.join(s.capitalize() for s in list[1:])

def import_module(name):
    "import_module('a.b.c') -> <module a.b.c>"
    mod = sys.modules.get(name)
    if mod is not None: return mod
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]: mod = getattr(mod, comp)
    return mod

if sys.platform == 'win32':
      _absolute_re = re.compile(r'^(?:[A-Za-z]:)?[\\/]')
else: _absolute_re = re.compile(r'^/')

def is_absolute_path(filename):
    return bool(_absolute_re.match(filename))

def absolutize_path(filename, frame_depth):
    if is_absolute_path(filename): return filename
    code_filename = sys._getframe(frame_depth+1).f_code.co_filename
    if not is_absolute_path(code_filename):
        if code_filename.startswith('<') and code_filename.endswith('>'):
            if pony.MODE == 'INTERACTIVE': raise ValueError(
                'When in interactive mode, please provide absolute file path. Got: %r' % filename)
            raise EnvironmentError('Unexpected module filename, which is not absolute file path: %r' % code_filename)
    code_path = os.path.dirname(code_filename)
    return os.path.join(code_path, filename)

def shortened_filename(filename):
    if pony.MAIN_DIR is None: return filename
    maindir = pony.MAIN_DIR + os.sep
    if filename.startswith(maindir): return filename[len(maindir):]
    return filename

def get_mtime(filename):
    stat = os.stat(filename)
    mtime = stat.st_mtime
    if sys.platform == "win32": mtime -= stat.st_ctime
    return mtime

coding_re = re.compile(r'coding[:=]\s*([-\w.]+)')

def detect_source_encoding(filename):
    for i, line in enumerate(linecache.getlines(filename)):
        if i == 0 and line.startswith(BOM_UTF8): return 'utf-8'
        if not line.lstrip().startswith('#'): continue
        match = coding_re.search(line)
        if match is not None: return match.group(1)
    else: return options.SOURCE_ENCODING or getpreferredencoding()

escape_re = re.compile(r'''
    (?<!\\)\\         # single backslash
    (?:
        x[0-9a-f]{2}  # byte escaping
    |   u[0-9a-f]{4}  # unicode escaping
    |   U[0-9a-f]{8}  # long unicode escaping
    )
    ''', re.VERBOSE)

def restore_escapes(s, console_encoding=None, source_encoding=None):
    if not options.RESTORE_ESCAPES: return s
    if source_encoding is None:
        source_encoding = options.SOURCE_ENCODING or getpreferredencoding()
    if console_encoding is None:
        try: console_encoding = getattr(sys.stderr, 'encoding', None)
        except: console_encoding = None  # workaround for PythonWin win32ui.error "The MFC object has died."
        console_encoding = console_encoding or options.CONSOLE_ENCODING
        console_encoding = console_encoding or getpreferredencoding()
    try: s = s.decode(source_encoding).encode(console_encoding)
    except (UnicodeDecodeError, UnicodeEncodeError): pass
    def f(match):
        esc = match.group()
        code = int(esc[2:], 16)
        if esc.startswith('\\x'):
            if code < 32: return esc
            try: return chr(code).decode(source_encoding).encode(console_encoding)
            except (UnicodeDecodeError, UnicodeEncodeError): return esc
        char = unichr(code)
        try: return char.encode(console_encoding)
        except UnicodeEncodeError: return esc
    return escape_re.sub(f, s)

def current_timestamp():
    return datetime2timestamp(datetime.datetime.now())

def datetime2timestamp(d):
    result = d.isoformat(' ')
    if len(result) == 19: return result + '.000000'
    return result

def timestamp2datetime(t):
    time_tuple = strptime(t[:19], '%Y-%m-%d %H:%M:%S')
    microseconds = int((t[20:26] + '000000')[:6])
    return datetime.datetime(*(time_tuple[:6] + (microseconds,)))

def read_text_file(fname, encoding=None):
    text = file(fname).read()
    for bom, enc in [ (BOM_UTF8, 'utf8'), (BOM_LE, 'utf-16le'), (BOM_BE, 'utf-16be') ]:
        if text[:len(bom)] == bom: return text[len(bom):].decode(enc)
    try: return text.decode('utf8')
    except UnicodeDecodeError:
        try: return text.decode(encoding or getpreferredencoding())
        except UnicodeDecodeError:
            return text.decode('ascii', 'replace')

def compress(s):
    zipped = s.encode('zip')
    if len(zipped) < len(s): return 'Z' + zipped
    return 'N' + s

def decompress(s):
    first = s[0]
    if first == 'N': return s[1:]
    elif first == 'Z': return s[1:].decode('zip')
    raise ValueError('Incorrect data')

nbsp_re = re.compile(ur"\s+(и|с|в|от)\s+")

def markdown(s):
    from pony.templating import Html, quote
    from pony.thirdparty.markdown import markdown
    s = quote(s)[:]
    result = markdown(s, html4tags=True)
    result = nbsp_re.sub(r" \1&nbsp;", result)
    return Html(result)

class JsonString(unicode): pass

def json(obj, **kwargs):
    from pony.thirdparty import simplejson
    result = JsonString(simplejson.dumps(obj, **kwargs))
    result.media_type = 'application/json'
    if 'encoding' in kwargs: result.charset = kwargs['encoding']
    return result

def new_guid():
    'new_guid() -> new_binary_guid'
    return buffer(urandom(16))

def guid2str(guid):
    """guid_binary2str(binary_guid) -> string_guid

    >>> guid2str(unxehlify('ff19966f868b11d0b42d00c04fc964ff'))
    '6F9619FF-8B86-D011-B42D-00C04FC964FF'
    """
    assert isinstance(guid, buffer) and len(guid) == 16
    guid = str(guid)
    return '%s-%s-%s-%s-%s' % tuple(map(hexlify, (
        guid[3::-1], guid[5:3:-1], guid[7:5:-1], guid[8:10], guid[10:])))

def str2guid(s):
    """guid_str2binary(str_guid) -> binary_guid

    >>> unhexlify(str2guid('6F9619FF-8B86-D011-B42D-00C04FC964FF'))
    'ff19966f868b11d0b42d00c04fc964ff'
    """
    assert isinstance(s, basestring) and len(s) == 36
    a, b, c, d, e = map(unhexlify, (s[:8],s[9:13],s[14:18],s[19:23],s[24:]))
    reverse = slice(-1, None, -1)
    return buffer(''.join((a[reverse], b[reverse], c[reverse], d, e)))

expr1_re = re.compile(r'''
        ([A-Za-z_]\w*)  # identifier (group 1)
    |   ([(])           # open parenthesis (group 2)
    ''', re.VERBOSE)

expr2_re = re.compile(r'''
     \s*(?:
            (;)                 # semicolon (group 1)
        |   (\.\s*[A-Za-z_]\w*) # dot + identifier (group 2)
        |   ([([])              # open parenthesis or braces (group 3)
        )
    ''', re.VERBOSE)

expr3_re = re.compile(r"""
        [()[\]]                   # parenthesis or braces (group 1)
    |   '''(?:[^\\]|\\.)*?'''     # '''triple-quoted string'''
    |   \"""(?:[^\\]|\\.)*?\"""   # \"""triple-quoted string\"""
    |   '(?:[^'\\]|\\.)*?'        # 'string'
    |   "(?:[^"\\]|\\.)*?"        # "string"
    """, re.VERBOSE)

def parse_expr(s, pos=0):
    z = 0
    match = expr1_re.match(s, pos)
    if match is None: raise ValueError
    start = pos
    i = match.lastindex
    if i == 1: pos = match.end()  # identifier
    elif i == 2: z = 2  # "("
    else: assert False
    while True:
        match = expr2_re.match(s, pos)
        if match is None: return s[start:pos], z==1
        pos = match.end()
        i = match.lastindex
        if i == 1: return s[start:pos], False  # ";" - explicit end of expression
        elif i == 2: z = 2  # .identifier
        elif i == 3:  # "(" or "["
            pos = match.end()
            counter = 1
            open = match.group(i)
            if open == '(': close = ')'
            elif open == '[': close = ']'; z = 2
            else: assert False
            while True:
                match = expr3_re.search(s, pos)
                if match is None: raise ValueError
                pos = match.end()
                x = match.group()
                if x == open: counter += 1
                elif x == close:
                    counter -= 1
                    if not counter: z += 1; break
        else: assert False

def tostring(x):
    if isinstance(x, basestring): return x
    if hasattr(x, '__unicode__'):
        try: return unicode(x)
        except: pass
    if etree is not None and hasattr(x, 'makeelement'): return etree.tostring(x)
    try: return str(x)
    except: pass
    try: return repr(x)
    except: pass
    if type(x) == types.InstanceType: return '<%s instance at 0x%X>' % (x.__class__.__name__)
    return '<%s object at 0x%X>' % (x.__class__.__name__)

def strjoin(sep, strings, source_encoding='ascii', dest_encoding=None):
    "Can join mix of unicode and byte strings in different encodings"
    strings = list(strings)
    try: return sep.join(strings)
    except UnicodeDecodeError: pass
    for i, s in enumerate(strings):
        if isinstance(s, str):
            strings[i] = s.decode(source_encoding, 'replace').replace(u'\ufffd', '?')
    result = sep.join(strings)
    if dest_encoding is None: return result
    return result.encode(dest_encoding, replace)

def make_offsets(s):
    offsets = [ 0 ]
    si = -1
    try:
        while True:
            si = s.index('\n', si + 1)
            offsets.append(si + 1)
    except ValueError: pass
    offsets.append(len(s))
    return offsets

def pos2lineno(pos, offsets):
    line = bisect(offsets, pos, 0, len(offsets)-1)
    if line == 1: offset = pos
    else: offset = pos - offsets[line - 1]
    return line, offset

def getline(text, offsets, lineno):
    return text[offsets[lineno-1]:offsets[lineno]]

def getlines(text, offsets, lineno, context=1):
    if context <= 0: return [], None
    start = max(0, lineno - 1 - context//2)
    end = min(len(offsets)-1, start + context)
    start = max(0, end - context)
    lines = []
    for i in range(start, end): lines.append(text[offsets[i]:offsets[i+1]])
    index = lineno - 1 - start
    return lines, index

def getlines2(filename, lineno, context=1):
    if context <= 0: return [], None
    lines = linecache.getlines(filename)
    if not lines: return [], None
    start = max(0, lineno - 1 - context//2)
    end = min(len(lines), start + context)
    start = max(0, end - context)
    lines = lines[start:start+context]
    index = lineno - 1 - start
    return lines, index

def count(*args, **kwargs):
    if kwargs: return _count(*args, **kwargs)
    if len(args) != 1: return _count(*args)
    arg = args[0]
    if hasattr(arg, 'count'): return arg.count()
    try: it = iter(arg)
    except TypeError: return _count(arg)
    return len(set(it))

def avg(iter):
    count = 0
    sum = 0.0
    for elem in iter:
        if elem is None: continue
        sum += elem
        count += 1
    if not count: return None
    return sum / count

def distinct(iter):
    d = defaultdict(int)
    for item in iter:
        d[item] = d[item] + 1
    return d

def concat(*args):
    return ''.join(map('%s'.__mod__, args))

def is_utf8(encoding):
    return encoding.upper().replace('_', '').replace('-', '') in ('UTF8', 'UTF', 'U8')

########NEW FILE########
