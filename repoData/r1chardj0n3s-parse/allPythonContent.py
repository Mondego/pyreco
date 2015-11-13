__FILENAME__ = parse
r'''Parse strings using a specification based on the Python format() syntax.

   ``parse()`` is the opposite of ``format()``

The module is set up to only export ``parse()``, ``search()`` and
``findall()`` when ``import *`` is used:

>>> from parse import *

From there it's a simple thing to parse a string:

>>> parse("It's {}, I love it!", "It's spam, I love it!")
<Result ('spam',) {}>
>>> _[0]
'spam'

Or to search a string for some pattern:

>>> search('Age: {:d}\n', 'Name: Rufus\nAge: 42\nColor: red\n')
<Result (42,) {}>

Or find all the occurrances of some pattern in a string:

>>> ''.join(r.fixed[0] for r in findall(">{}<", "<p>the <b>bold</b> text</p>"))
'the bold text'

If you're going to use the same pattern to match lots of strings you can
compile it once:

>>> from parse import compile
>>> p = compile("It's {}, I love it!")
>>> print(p)
<Parser "It's {}, I love it!">
>>> p.parse("It's spam, I love it!")
<Result ('spam',) {}>

("compile" is not exported for ``import *`` usage as it would override the
built-in ``compile()`` function)


Format Syntax
-------------

A basic version of the `Format String Syntax`_ is supported with anonymous
(fixed-position), named and formatted fields::

   {[field name]:[format spec]}

Field names must be a valid Python identifiers, including dotted names;
element indexes are supported (as they would make no sense.)

Numbered fields are also not supported: the result of parsing will include
the parsed fields in the order they are parsed.

The conversion of fields to types other than strings is done based on the
type in the format specification, which mirrors the ``format()`` behaviour.
There are no "!" field conversions like ``format()`` has.

Some simple parse() format string examples:

>>> parse("Bring me a {}", "Bring me a shrubbery")
<Result ('shrubbery',) {}>
>>> r = parse("The {} who say {}", "The knights who say Ni!")
>>> print(r)
<Result ('knights', 'Ni!') {}>
>>> print(r.fixed)
('knights', 'Ni!')
>>> r = parse("Bring out the holy {item}", "Bring out the holy hand grenade")
>>> print(r)
<Result () {'item': 'hand grenade'}>
>>> print(r.named)
{'item': 'hand grenade'}
>>> print(r['item'])
hand grenade

Dotted names are possible though the application must make additional sense of
the result:

>>> r = parse("Mmm, {food.type}, I love it!", "Mmm, spam, I love it!")
>>> print(r)
<Result () {'food.type': 'spam'}>
>>> print(r.named)
{'food.type': 'spam'}
>>> print(r['food.type'])
spam


Format Specification
--------------------

Most often a straight format-less ``{}`` will suffice where a more complex
format specification might have been used.

Most of `format()`'s `Format Specification Mini-Language`_ is supported:

   [[fill]align][0][width][type]

The differences between `parse()` and `format()` are:

- The align operators will cause spaces (or specified fill character) to be
  stripped from the parsed value. The width is not enforced; it just indicates
  there may be whitespace or "0"s to strip.
- Numeric parsing will automatically handle a "0b", "0o" or "0x" prefix.
  That is, the "#" format character is handled automatically by d, b, o
  and x formats. For "d" any will be accepted, but for the others the correct
  prefix must be present if at all.
- Numeric sign is handled automatically.
- The thousands separator is handled automatically if the "n" type is used.
- The types supported are a slightly different mix to the format() types.  Some
  format() types come directly over: "d", "n", "%", "f", "e", "b", "o" and "x".
  In addition some regular expression character group types "D", "w", "W", "s"
  and "S" are also available.
- The "e" and "g" types are case-insensitive so there is not need for
  the "E" or "G" types.

===== =========================================== ========
Type  Characters Matched                          Output
===== =========================================== ========
 w    Letters and underscore                      str
 W    Non-letter and underscore                   str
 s    Whitespace                                  str
 S    Non-whitespace                              str
 d    Digits (effectively integer numbers)        int
 D    Non-digit                                   str
 n    Numbers with thousands separators (, or .)  int
 %    Percentage (converted to value/100.0)       float
 f    Fixed-point numbers                         float
 e    Floating-point numbers with exponent        float
      e.g. 1.1e-10, NAN (all case insensitive)
 g    General number format (either d, f or e)    float
 b    Binary numbers                              int
 o    Octal numbers                               int
 x    Hexadecimal numbers (lower and upper case)  int
 ti   ISO 8601 format date/time                   datetime
      e.g. 1972-01-20T10:21:36Z ("T" and "Z"
      optional)
 te   RFC2822 e-mail format date/time             datetime
      e.g. Mon, 20 Jan 1972 10:21:36 +1000
 tg   Global (day/month) format date/time         datetime
      e.g. 20/1/1972 10:21:36 AM +1:00
 ta   US (month/day) format date/time             datetime
      e.g. 1/20/1972 10:21:36 PM +10:30
 tc   ctime() format date/time                    datetime
      e.g. Sun Sep 16 01:03:52 1973
 th   HTTP log format date/time                   datetime
      e.g. 21/Nov/2011:00:07:11 +0000
 tt   Time                                        time
      e.g. 10:21:36 PM -5:30
===== =========================================== ========

Some examples of typed parsing with ``None`` returned if the typing
does not match:

>>> parse('Our {:d} {:w} are...', 'Our 3 weapons are...')
<Result (3, 'weapons') {}>
>>> parse('Our {:d} {:w} are...', 'Our three weapons are...')
>>> parse('Meet at {:tg}', 'Meet at 1/2/2011 11:00 PM')
<Result (datetime.datetime(2011, 2, 1, 23, 0),) {}>

And messing about with alignment:

>>> parse('with {:>} herring', 'with     a herring')
<Result ('a',) {}>
>>> parse('spam {:^} spam', 'spam    lovely     spam')
<Result ('lovely',) {}>

Note that the "center" alignment does not test to make sure the value is
centered - it just strips leading and trailing whitespace.

Some notes for the date and time types:

- the presence of the time part is optional (including ISO 8601, starting
  at the "T"). A full datetime object will always be returned; the time
  will be set to 00:00:00. You may also specify a time without seconds.
- when a seconds amount is present in the input fractions will be parsed
  to give microseconds.
- except in ISO 8601 the day and month digits may be 0-padded.
- the date separator for the tg and ta formats may be "-" or "/".
- named months (abbreviations or full names) may be used in the ta and tg
  formats in place of numeric months.
- as per RFC 2822 the e-mail format may omit the day (and comma), and the
  seconds but nothing else.
- hours greater than 12 will be happily accepted.
- the AM/PM are optional, and if PM is found then 12 hours will be added
  to the datetime object's hours amount - even if the hour is greater
  than 12 (for consistency.)
- in ISO 8601 the "Z" (UTC) timezone part may be a numeric offset
- timezones are specified as "+HH:MM" or "-HH:MM". The hour may be one or two
  digits (0-padded is OK.) Also, the ":" is optional.
- the timezone is optional in all except the e-mail format (it defaults to
  UTC.)
- named timezones are not handled yet.

Note: attempting to match too many datetime fields in a single parse() will
currently result in a resource allocation issue. A TooManyFields exception
will be raised in this instance. The current limit is about 15. It is hoped
that this limit will be removed one day.

.. _`Format String Syntax`:
  http://docs.python.org/library/string.html#format-string-syntax
.. _`Format Specification Mini-Language`:
  http://docs.python.org/library/string.html#format-specification-mini-language


Result Objects
--------------

The result of a ``parse()`` operation is either ``None`` (no match) or a
``Result`` instance.

The ``Result`` instance has three attributes:

fixed
   A tuple of the fixed-position, anonymous fields extracted from the input.
named
   A dictionary of the named fields extracted from the input.
spans
   A dictionary mapping the names and fixed position indices matched to a
   2-tuple slice range of where the match occurred in the input.
   The span does not include any stripped padding (alignment or width).


Custom Type Conversions
-----------------------

If you wish to have matched fields automatically converted to your own type you
may pass in a dictionary of type conversion information to ``parse()`` and
``compile()``.

The converter will be passed the field string matched. Whatever it returns
will be substituted in the ``Result`` instance for that field.

Your custom type conversions may override the builtin types if you supply one
with the same identifier.

>>> def shouty(string):
...    return string.upper()
...
>>> parse('{:shouty} world', 'hello world', dict(shouty=shouty))
<Result ('HELLO',) {}>

If the type converter has the optional ``pattern`` attribute, it is used as
regular expression for better pattern matching (instead of the default one).

>>> def parse_number(text):
...    return int(text)
>>> parse_number.pattern = r'\d+'
>>> parse('Answer: {number:Number}', 'Answer: 42', dict(Number=parse_number))
<Result () {'number': 42}>
>>> _ = parse('Answer: {:Number}', 'Answer: Alice', dict(Number=parse_number))
>>> assert _ is None, "MISMATCH"

You can also use the ``with_pattern(pattern)`` decorator to add this
information to a type converter function:

>>> from parse import with_pattern
>>> @with_pattern(r'\d+')
... def parse_number(text):
...    return int(text)
>>> parse('Answer: {number:Number}', 'Answer: 42', dict(Number=parse_number))
<Result () {'number': 42}>

A more complete example of a custom type might be:

>>> yesno_mapping = {
...     "yes":  True,   "no":    False,
...     "on":   True,   "off":   False,
...     "true": True,   "false": False,
... }
... @with_pattern(r"|".join(yesno_mapping))
... def parse_yesno(text):
...     return yesno_mapping[text.lower()]


----

**Version history (in brief)**:

- 1.6.4 handle pipe "|" characters in parse string (thanks Martijn Pieters)
- 1.6.3 handle repeated instances of named fields, fix bug in PM time
  overflow
- 1.6.2 fix logging to use local, not root logger (thanks Necku)
- 1.6.1 be more flexible regarding matched ISO datetimes and timezones in
  general, fix bug in timezones without ":" and improve docs
- 1.6.0 add support for optional ``pattern`` attribute in user-defined types
  (thanks Jens Engel)
- 1.5.3 fix handling of question marks
- 1.5.2 fix type conversion error with dotted names (thanks Sebastian Thiel)
- 1.5.1 implement handling of named datetime fields
- 1.5 add handling of dotted field names (thanks Sebastian Thiel)
- 1.4.1 fix parsing of "0" in int conversion (thanks James Rowe)
- 1.4 add __getitem__ convenience access on Result.
- 1.3.3 fix Python 2.5 setup.py issue.
- 1.3.2 fix Python 3.2 setup.py issue.
- 1.3.1 fix a couple of Python 3.2 compatibility issues.
- 1.3 added search() and findall(); removed compile() from ``import *``
  export as it overwrites builtin.
- 1.2 added ability for custom and override type conversions to be
  provided; some cleanup
- 1.1.9 to keep things simpler number sign is handled automatically;
  significant robustification in the face of edge-case input.
- 1.1.8 allow "d" fields to have number base "0x" etc. prefixes;
  fix up some field type interactions after stress-testing the parser;
  implement "%" type.
- 1.1.7 Python 3 compatibility tweaks (2.5 to 2.7 and 3.2 are supported).
- 1.1.6 add "e" and "g" field types; removed redundant "h" and "X";
  removed need for explicit "#".
- 1.1.5 accept textual dates in more places; Result now holds match span
  positions.
- 1.1.4 fixes to some int type conversion; implemented "=" alignment; added
  date/time parsing with a variety of formats handled.
- 1.1.3 type conversion is automatic based on specified field types. Also added
  "f" and "n" types.
- 1.1.2 refactored, added compile() and limited ``from parse import *``
- 1.1.1 documentation improvements
- 1.1.0 implemented more of the `Format Specification Mini-Language`_
  and removed the restriction on mixing fixed-position and named fields
- 1.0.0 initial release

This code is copyright 2012-2013 Richard Jones <richard@python.org>
See the end of the source file for the license of use.
'''
__version__ = '1.6.4'

# yes, I now have two problems
import re
import sys
from datetime import datetime, time, tzinfo, timedelta
from functools import partial
import logging

__all__ = 'parse search findall with_pattern'.split()

log = logging.getLogger(__name__)


def with_pattern(pattern):
    """Attach a regular expression pattern matcher to a custom type converter
    function.

    This annotates the type converter with the :attr:`pattern` attribute.

    EXAMPLE:
        >>> import parse
        >>> @parse.with_pattern(r"\d+")
        ... def parse_number(text):
        ...     return int(text)

    is equivalent to:

        >>> def parse_number(text):
        ...     return int(text)
        >>> parse_number.pattern = r"\d+"

    :param pattern: regular expression pattern (as text)
    :return: wrapped function
    """
    def decorator(func):
        func.pattern = pattern
        return func
    return decorator


def int_convert(base):
    '''Convert a string to an integer.

    The string may start with a sign.

    It may be of a base other than 10.

    It may also have other non-numeric characters that we can ignore.
    '''
    CHARS = '0123456789abcdefghijklmnopqrstuvwxyz'

    def f(string, match, base=base):
        if string[0] == '-':
            sign = -1
        else:
            sign = 1

        if string[0] == '0' and len(string) > 1:
            if string[1] in 'bB':
                base = 2
            elif string[1] in 'oO':
                base = 8
            elif string[1] in 'xX':
                base = 16
            else:
                # just go with the base specifed
                pass

        chars = CHARS[:base]
        string = re.sub('[^%s]' % chars, '', string.lower())
        return sign * int(string, base)
    return f


def percentage(string, match):
    return float(string[:-1]) / 100.


class FixedTzOffset(tzinfo):
    """Fixed offset in minutes east from UTC.
    """
    ZERO = timedelta(0)

    def __init__(self, offset, name):
        self._offset = timedelta(minutes=offset)
        self._name = name

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self._name,
            self._offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self._name

    def dst(self, dt):
        return self.ZERO

    def __eq__(self, other):
        return self._name == other._name and self._offset == other._offset


MONTHS_MAP = dict(
    Jan=1, January=1,
    Feb=2, February=2,
    Mar=3, March=3,
    Apr=4, April=4,
    May=5,
    Jun=6, June=6,
    Jul=7, July=7,
    Aug=8, August=8,
    Sep=9, September=9,
    Oct=10, October=10,
    Nov=11, November=11,
    Dec=12, December=12
)
DAYS_PAT = '(Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
MONTHS_PAT = '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
ALL_MONTHS_PAT = '(%s)' % '|'.join(MONTHS_MAP)
TIME_PAT = r'(\d{1,2}:\d{1,2}(:\d{1,2}(\.\d+)?)?)'
AM_PAT = r'(\s+[AP]M)'
TZ_PAT = r'(\s+[-+]\d\d?:?\d\d)'


def date_convert(string, match, ymd=None, mdy=None, dmy=None,
        d_m_y=None, hms=None, am=None, tz=None):
    '''Convert the incoming string containing some date / time info into a
    datetime instance.
    '''
    groups = match.groups()
    time_only = False
    if ymd is not None:
        y, m, d = re.split('[-/\s]', groups[ymd])
    elif mdy is not None:
        m, d, y = re.split('[-/\s]', groups[mdy])
    elif dmy is not None:
        d, m, y = re.split('[-/\s]', groups[dmy])
    elif d_m_y is not None:
        d, m, y = d_m_y
        d = groups[d]
        m = groups[m]
        y = groups[y]
    else:
        time_only = True

    H = M = S = u = 0
    if hms is not None and groups[hms]:
        t = groups[hms].split(':')
        if len(t) == 2:
            H, M = t
        else:
            H, M, S = t
            if '.' in S:
                S, u = S.split('.')
                u = int(float('.' + u) * 1000000)
            S = int(S)
        H = int(H)
        M = int(M)

    day_incr = False
    if am is not None:
        am = groups[am]
        if am and am.strip() == 'PM':
            H += 12
            if H > 23:
                day_incr = True
                H -= 24

    if tz is not None:
        tz = groups[tz]
    if tz == 'Z':
        tz = FixedTzOffset(0, 'UTC')
    elif tz:
        tz = tz.strip()
        if tz.isupper():
            # TODO use the awesome python TZ module?
            pass
        else:
            sign = tz[0]
            if ':' in tz:
                tzh, tzm = tz[1:].split(':')
            elif len(tz) == 4:  # 'snnn'
                tzh, tzm = tz[1], tz[2:4]
            else:
                tzh, tzm = tz[1:3], tz[3:5]
            offset = int(tzm) + int(tzh) * 60
            if sign == '-':
                offset = -offset
            tz = FixedTzOffset(offset, tz)

    if time_only:
        d = time(H, M, S, u, tzinfo=tz)
    else:
        y = int(y)
        if m.isdigit():
            m = int(m)
        else:
            m = MONTHS_MAP[m]
        d = int(d)
        d = datetime(y, m, d, H, M, S, u, tzinfo=tz)

    if day_incr:
        d = d + timedelta(days=1)

    return d


class TooManyFields(ValueError):
    pass


class RepeatedNameError(ValueError):
    pass


# note: {} are handled separately
# note: I don't use r'' here because Sublime Text 2 syntax highlight has a fit
REGEX_SAFETY = re.compile('([?\\\\.[\]()*+\^$!\|])')

# allowed field types
ALLOWED_TYPES = set(list('nbox%fegwWdDsS') +
    ['t' + c for c in 'ieahgct'])


def extract_format(format, extra_types):
    '''Pull apart the format [[fill]align][0][width][type]
    '''
    fill = align = None
    if format[0] in '<>=^':
        align = format[0]
        format = format[1:]
    elif len(format) > 1 and format[1] in '<>=^':
        fill = format[0]
        align = format[1]
        format = format[2:]

    zero = False
    if format and format[0] == '0':
        zero = True
        format = format[1:]

    width = ''
    while format:
        if not format[0].isdigit():
            break
        width += format[0]
        format = format[1:]

    # the rest is the type, if present
    type = format
    if type and type not in ALLOWED_TYPES and type not in extra_types:
        raise ValueError('type %r not recognised' % type)

    return locals()


PARSE_RE = re.compile(r'({{|}}|{}|{:[^}]+?}|{\w+?(?:\.\w+?)*}|'
    r'{\w+?(?:\.\w+?)*:[^}]+?})')


class Parser(object):
    '''Encapsulate a format string that may be used to parse other strings.
    '''
    def __init__(self, format, extra_types={}):
        # a mapping of a name as in {hello.world} to a regex-group compatible
        # name, like hello__world Its used to prevent the transformation of
        # name-to-group and group to name to fail subtly, such as in:
        # hello_.world-> hello___world->hello._world
        self._group_to_name_map = {}
        # also store the original field name to group name mapping to allow
        # multiple instances of a name in the format string
        self._name_to_group_map = {}
        # and to sanity check the repeated instances store away the first
        # field type specification for the named field
        self._name_types = {}

        self._format = format
        self._extra_types = extra_types
        self._fixed_fields = []
        self._named_fields = []
        self._group_index = 0
        self._type_conversions = {}
        self._expression = self._generate_expression()
        self.__search_re = None
        self.__match_re = None

        log.debug('format %r -> %r' % (format, self._expression))

    def __repr__(self):
        if len(self._format) > 20:
            return '<%s %r>' % (self.__class__.__name__,
                self._format[:17] + '...')
        return '<%s %r>' % (self.__class__.__name__, self._format)

    @property
    def _search_re(self):
        if self.__search_re is None:
            try:
                self.__search_re = re.compile(self._expression,
                    re.IGNORECASE | re.DOTALL)
            except AssertionError:
                # access error through sys to keep py3k and backward compat
                e = str(sys.exc_info()[1])
                if e.endswith('this version only supports 100 named groups'):
                    raise TooManyFields('sorry, you are attempting to parse '
                        'too many complex fields')
        return self.__search_re

    @property
    def _match_re(self):
        if self.__match_re is None:
            expression = '^%s$' % self._expression
            try:
                self.__match_re = re.compile(expression,
                    re.IGNORECASE | re.DOTALL)
            except AssertionError:
                # access error through sys to keep py3k and backward compat
                e = str(sys.exc_info()[1])
                if e.endswith('this version only supports 100 named groups'):
                    raise TooManyFields('sorry, you are attempting to parse '
                        'too many complex fields')
            except re.error:
                raise NotImplementedError("Group names (e.g. (?P<name>) can "
                    "cause failure, as they are not escaped properly: '%s'" %
                    expression)
        return self.__match_re

    def parse(self, string):
        '''Match my format to the string exactly.

        Return either a Result instance or None if there's no match.
        '''
        m = self._match_re.match(string)
        if m is None:
            return None

        return self._generate_result(m)

    def search(self, string, pos=0, endpos=None):
        '''Search the string for my format.

        Optionally start the search at "pos" character index and limit the
        search to a maximum index of endpos - equivalent to
        search(string[:endpos]).

        Return either a Result instance or None if there's no match.
        '''
        if endpos is None:
            endpos = len(string)
        m = self._search_re.search(string, pos, endpos)
        if m is None:
            return None

        return self._generate_result(m)

    def findall(self, string, pos=0, endpos=None, extra_types={}):
        '''Search "string" for the all occurrances of "format".

        Optionally start the search at "pos" character index and limit the
        search to a maximum index of endpos - equivalent to
        search(string[:endpos]).

        Returns an iterator that holds Result instances for each format match
        found.
        '''
        if endpos is None:
            endpos = len(string)
        return ResultIterator(self, string, pos, endpos)

    def _generate_result(self, m):
        # ok, figure the fixed fields we've pulled out and type convert them
        fixed_fields = list(m.groups())
        for n in self._fixed_fields:
            if n in self._type_conversions:
                fixed_fields[n] = self._type_conversions[n](fixed_fields[n], m)
        fixed_fields = tuple(fixed_fields[n] for n in self._fixed_fields)

        # grab the named fields, converting where requested
        groupdict = m.groupdict()
        named_fields = {}
        name_map = {}
        for k in self._named_fields:
            korig = self._group_to_name_map[k]
            name_map[korig] = k
            if k in self._type_conversions:
                named_fields[korig] = self._type_conversions[k](groupdict[k],
                    m)
            else:
                named_fields[korig] = groupdict[k]

        # now figure the match spans
        spans = dict((n, m.span(name_map[n])) for n in named_fields)
        spans.update((i, m.span(n + 1))
            for i, n in enumerate(self._fixed_fields))

        # and that's our result
        return Result(fixed_fields, named_fields, spans)

    def _regex_replace(self, match):
        return '\\' + match.group(1)

    def _generate_expression(self):
        # turn my _format attribute into the _expression attribute
        e = []
        for part in PARSE_RE.split(self._format):
            if not part:
                continue
            elif part == '{{':
                e.append(r'\{')
            elif part == '}}':
                e.append(r'\}')
            elif part[0] == '{':
                # this will be a braces-delimited field to handle
                e.append(self._handle_field(part))
            else:
                # just some text to match
                e.append(REGEX_SAFETY.sub(self._regex_replace, part))
        return ''.join(e)

    def _to_group_name(self, field):
        # return a version of field which can be used as capture group, even
        # though it might contain '.'
        group = field.replace('.', '_')

        # make sure we don't collide ("a.b" colliding with "a_b")
        n = 1
        while group in self._group_to_name_map:
            n += 1
            if '.' in field:
                group = field.replace('.', '_' * n)
            elif '_' in field:
                group = field.replace('_', '_' * n)
            else:
                raise KeyError('duplicated group name %r' % (field, ))

        # save off the mapping
        self._group_to_name_map[group] = field
        self._name_to_group_map[field] = group
        return group

    def _handle_field(self, field):
        # first: lose the braces
        field = field[1:-1]

        # now figure whether this is an anonymous or named field, and whether
        # there's any format specification
        format = ''
        if field and field[0].isalpha():
            if ':' in field:
                name, format = field.split(':')
            else:
                name = field
            if name in self._name_to_group_map:
                if self._name_types[name] != format:
                    raise RepeatedNameError('field type %r for field "%s" '
                        'does not match previous seen type %r' % (format,
                        name, self._name_types[name]))
                group = self._name_to_group_map[name]
                # match previously-seen value
                return '(?P=%s)' % group
            else:
                group = self._to_group_name(name)
                self._name_types[name] = format
            self._named_fields.append(group)
            # this will become a group, which must not contain dots
            wrap = '(?P<%s>%%s)' % group
        else:
            self._fixed_fields.append(self._group_index)
            wrap = '(%s)'
            if ':' in field:
                format = field[1:]
            group = self._group_index

        # simplest case: no type specifier ({} or {name})
        if not format:
            self._group_index += 1
            return wrap % '.+?'

        # decode the format specification
        format = extract_format(format, self._extra_types)

        # figure type conversions, if any
        type = format['type']
        is_numeric = type and type in 'n%fegdobh'
        if type in self._extra_types:
            type_converter = self._extra_types[type]
            s = getattr(type_converter, 'pattern', r'.+?')

            def f(string, m):
                return type_converter(string)
            self._type_conversions[group] = f
        elif type == 'n':
            s = '\d{1,3}([,.]\d{3})*'
            self._group_index += 1
            self._type_conversions[group] = int_convert(10)
        elif type == 'b':
            s = '(0[bB])?[01]+'
            self._type_conversions[group] = int_convert(2)
            self._group_index += 1
        elif type == 'o':
            s = '(0[oO])?[0-7]+'
            self._type_conversions[group] = int_convert(8)
            self._group_index += 1
        elif type == 'x':
            s = '(0[xX])?[0-9a-fA-F]+'
            self._type_conversions[group] = int_convert(16)
            self._group_index += 1
        elif type == '%':
            s = r'\d+(\.\d+)?%'
            self._group_index += 1
            self._type_conversions[group] = percentage
        elif type == 'f':
            s = r'\d+\.\d+'
            self._type_conversions[group] = lambda s, m: float(s)
        elif type == 'e':
            s = r'\d+\.\d+[eE][-+]?\d+|nan|NAN|[-+]?inf|[-+]?INF'
            self._type_conversions[group] = lambda s, m: float(s)
        elif type == 'g':
            s = r'\d+(\.\d+)?([eE][-+]?\d+)?|nan|NAN|[-+]?inf|[-+]?INF'
            self._group_index += 2
            self._type_conversions[group] = lambda s, m: float(s)
        elif type == 'd':
            s = r'\d+|0[xX][0-9a-fA-F]+|[0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+'
            self._type_conversions[group] = int_convert(10)
        elif type == 'ti':
            s = r'(\d{4}-\d\d-\d\d)((\s+|T)%s)?(Z|\s*[-+]\d\d:?\d\d)?' % \
                TIME_PAT
            n = self._group_index
            self._type_conversions[group] = partial(date_convert, ymd=n + 1,
                hms=n + 4, tz=n + 7)
            self._group_index += 7
        elif type == 'tg':
            s = r'(\d{1,2}[-/](\d{1,2}|%s)[-/]\d{4})(\s+%s)?%s?%s?' % (
                ALL_MONTHS_PAT, TIME_PAT, AM_PAT, TZ_PAT)
            n = self._group_index
            self._type_conversions[group] = partial(date_convert, dmy=n + 1,
                hms=n + 5, am=n + 8, tz=n + 9)
            self._group_index += 9
        elif type == 'ta':
            s = r'((\d{1,2}|%s)[-/]\d{1,2}[-/]\d{4})(\s+%s)?%s?%s?' % (
                ALL_MONTHS_PAT, TIME_PAT, AM_PAT, TZ_PAT)
            n = self._group_index
            self._type_conversions[group] = partial(date_convert, mdy=n + 1,
                hms=n + 5, am=n + 8, tz=n + 9)
            self._group_index += 9
        elif type == 'te':
            # this will allow microseconds through if they're present, but meh
            s = r'(%s,\s+)?(\d{1,2}\s+%s\s+\d{4})\s+%s%s' % (DAYS_PAT,
                MONTHS_PAT, TIME_PAT, TZ_PAT)
            n = self._group_index
            self._type_conversions[group] = partial(date_convert, dmy=n + 3,
                hms=n + 5, tz=n + 8)
            self._group_index += 8
        elif type == 'th':
            # slight flexibility here from the stock Apache format
            s = r'(\d{1,2}[-/]%s[-/]\d{4}):%s%s' % (MONTHS_PAT, TIME_PAT,
                TZ_PAT)
            n = self._group_index
            self._type_conversions[group] = partial(date_convert, dmy=n + 1,
                hms=n + 3, tz=n + 6)
            self._group_index += 6
        elif type == 'tc':
            s = r'(%s)\s+%s\s+(\d{1,2})\s+%s\s+(\d{4})' % (
                DAYS_PAT, MONTHS_PAT, TIME_PAT)
            n = self._group_index
            self._type_conversions[group] = partial(date_convert,
                d_m_y=(n + 4, n + 3, n + 8), hms=n + 5)
            self._group_index += 8
        elif type == 'tt':
            s = r'%s?%s?%s?' % (TIME_PAT, AM_PAT, TZ_PAT)
            n = self._group_index
            self._type_conversions[group] = partial(date_convert, hms=n + 1,
                am=n + 4, tz=n + 5)
            self._group_index += 5
        elif type:
            s = r'\%s+' % type
        else:
            s = '.+?'

        align = format['align']
        fill = format['fill']

        # handle some numeric-specific things like fill and sign
        if is_numeric:
            # prefix with something (align "=" trumps zero)
            if align == '=':
                # special case - align "=" acts like the zero above but with
                # configurable fill defaulting to "0"
                if not fill:
                    fill = '0'
                s = '%s*' % fill + s
            elif format['zero']:
                s = '0*' + s

            # allow numbers to be prefixed with a sign
            s = r'[-+ ]?' + s

        if not fill:
            fill = ' '

        # Place into a group now - this captures the value we want to keep.
        # Everything else from now is just padding to be stripped off
        if wrap:
            s = wrap % s
            self._group_index += 1

        if format['width']:
            # all we really care about is that if the format originally
            # specified a width then there will probably be padding - without
            # an explicit alignment that'll mean right alignment with spaces
            # padding
            if not align:
                align = '>'

        if fill in '.\+?*[](){}^$':
            fill = '\\' + fill

        # align "=" has been handled
        if align == '<':
            s = '%s%s*' % (s, fill)
        elif align == '>':
            s = '%s*%s' % (fill, s)
        elif align == '^':
            s = '%s*%s%s*' % (fill, s, fill)

        return s


class Result(object):
    '''The result of a parse() or search().

    Fixed results may be looked up using result[index]. Named results may be
    looked up using result['name'].
    '''
    def __init__(self, fixed, named, spans):
        self.fixed = fixed
        self.named = named
        self.spans = spans

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.fixed[item]
        return self.named[item]

    def __repr__(self):
        return '<%s %r %r>' % (self.__class__.__name__, self.fixed,
            self.named)


class ResultIterator(object):
    '''The result of a findall() operation.

    Each element is a Result instance.
    '''
    def __init__(self, parser, string, pos, endpos):
        self.parser = parser
        self.string = string
        self.pos = pos
        self.endpos = endpos

    def __iter__(self):
        return self

    def __next__(self):
        m = self.parser._search_re.search(self.string, self.pos, self.endpos)
        if m is None:
            raise StopIteration()
        self.pos = m.end()
        return self.parser._generate_result(m)

    # pre-py3k compat
    next = __next__


def parse(format, string, extra_types={}):
    '''Using "format" attempt to pull values from "string".

    The format must match the string contents exactly. If the value
    you're looking for is instead just a part of the string use
    search().

    The return value will be an Result instance with two attributes:

     .fixed - tuple of fixed-position values from the string
     .named - dict of named values from the string

    If the format is invalid a ValueError will be raised.

    See the module documentation for the use of "extra_types".

    In the case there is no match parse() will return None.
    '''
    return Parser(format, extra_types=extra_types).parse(string)


def search(format, string, pos=0, endpos=None, extra_types={}):
    '''Search "string" for the first occurance of "format".

    The format may occur anywhere within the string. If
    instead you wish for the format to exactly match the string
    use parse().

    Optionally start the search at "pos" character index and limit the search
    to a maximum index of endpos - equivalent to search(string[:endpos]).

    The return value will be an Result instance with two attributes:

     .fixed - tuple of fixed-position values from the string
     .named - dict of named values from the string

    If the format is invalid a ValueError will be raised.

    See the module documentation for the use of "extra_types".

    In the case there is no match parse() will return None.
    '''
    return Parser(format, extra_types=extra_types).search(string, pos, endpos)


def findall(format, string, pos=0, endpos=None, extra_types={}):
    '''Search "string" for the all occurrances of "format".

    You will be returned an iterator that holds Result instances
    for each format match found.

    Optionally start the search at "pos" character index and limit the search
    to a maximum index of endpos - equivalent to search(string[:endpos]).

    Each Result instance has two attributes:

     .fixed - tuple of fixed-position values from the string
     .named - dict of named values from the string

    If the format is invalid a ValueError will be raised.

    See the module documentation for the use of "extra_types".
    '''
    return Parser(format, extra_types=extra_types).findall(string, pos, endpos)


def compile(format, extra_types={}):
    '''Create a Parser instance to parse "format".

    The resultant Parser has a method .parse(string) which
    behaves in the same manner as parse(format, string).

    Use this function if you intend to parse many strings
    with the same format.

    See the module documentation for the use of "extra_types".

    Returns a Parser instance.
    '''
    return Parser(format, extra_types=extra_types)


# Copyright (c) 2012-2013 Richard Jones <richard@python.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# vim: set filetype=python ts=4 sw=4 et si tw=75

########NEW FILE########
__FILENAME__ = test_parse
'''Test suite for parse.py

This code is copyright 2011 eKit.com Inc (http://www.ekit.com/)
See the end of the source file for the license of use.
'''

import unittest
from datetime import datetime, time

import parse


class TestPattern(unittest.TestCase):
    def _test_expression(self, format, expression):
        self.assertEqual(parse.Parser(format)._expression, expression)

    def test_braces(self):
        # pull a simple string out of another string
        self._test_expression('{{ }}', '\{ \}')

    def test_fixed(self):
        # pull a simple string out of another string
        self._test_expression('{}', '(.+?)')
        self._test_expression('{} {}', '(.+?) (.+?)')

    def test_named(self):
        # pull a named string out of another string
        self._test_expression('{name}', '(?P<name>.+?)')
        self._test_expression('{name} {other}',
            '(?P<name>.+?) (?P<other>.+?)')

    def test_named_typed(self):
        # pull a named string out of another string
        self._test_expression('{name:w}', '(?P<name>\w+)')
        self._test_expression('{name:w} {other:w}',
            '(?P<name>\w+) (?P<other>\w+)')

    def test_beaker(self):
        # skip some trailing whitespace
        self._test_expression('{:<}', '(.+?) *')

    def test_left_fill(self):
        # skip some trailing periods
        self._test_expression('{:.<}', '(.+?)\.*')

    def test_bird(self):
        # skip some trailing whitespace
        self._test_expression('{:>}', ' *(.+?)')

    def test_center(self):
        # skip some surrounding whitespace
        self._test_expression('{:^}', ' *(.+?) *')

    def test_format_variety(self):
        def _(fmt, matches):
            d = parse.extract_format(fmt, {'spam': 'spam'})
            for k in matches:
                self.assertEqual(d.get(k), matches[k],
                    'm["%s"]=%r, expect %r' % (k, d.get(k), matches[k]))

        for t in '%obxegfdDwWsS':
            _(t, dict(type=t))
            _('10' + t, dict(type=t, width='10'))
        _('05d', dict(type='d', width='5', zero=True))
        _('<', dict(align='<'))
        _('.<', dict(align='<', fill='.'))
        _('>', dict(align='>'))
        _('.>', dict(align='>', fill='.'))
        _('^', dict(align='^'))
        _('.^', dict(align='^', fill='.'))
        _('x=d', dict(type='d', align='=', fill='x'))
        _('d', dict(type='d'))
        _('ti', dict(type='ti'))
        _('spam', dict(type='spam'))

        _('.^010d', dict(type='d', width='10', align='^', fill='.',
            zero=True))

    def test_dot_separated_fields(self):
        # this should just work and provide the named value
        res = parse.parse('{hello.world}_{jojo.foo.baz}_{simple}', 'a_b_c')
        assert res.named['hello.world'] == 'a'
        assert res.named['jojo.foo.baz'] == 'b'
        assert res.named['simple'] == 'c'

    def test_dot_separated_fields_name_collisions(self):
        # this should just work and provide the named value
        res = parse.parse('{a_.b}_{a__b}_{a._b}_{a___b}', 'a_b_c_d')
        assert res.named['a_.b'] == 'a'
        assert res.named['a__b'] == 'b'
        assert res.named['a._b'] == 'c'
        assert res.named['a___b'] == 'd'

    def test_invalid_groupnames_are_handled_gracefully(self):
        self.assertRaises(NotImplementedError, parse.parse,
            "{hello['world']}", "doesn't work")


class TestResult(unittest.TestCase):
    def test_fixed_access(self):
        r = parse.Result((1, 2), {}, None)
        self.assertEqual(r[0], 1)
        self.assertEqual(r[1], 2)
        self.assertRaises(IndexError, r.__getitem__, 2)
        self.assertRaises(KeyError, r.__getitem__, 'spam')

    def test_named_access(self):
        r = parse.Result((), {'spam': 'ham'}, None)
        self.assertEqual(r['spam'], 'ham')
        self.assertRaises(KeyError, r.__getitem__, 'ham')
        self.assertRaises(IndexError, r.__getitem__, 0)


class TestParse(unittest.TestCase):
    def test_no_match(self):
        # string does not match format
        self.assertEqual(parse.parse('{{hello}}', 'hello'), None)

    def test_nothing(self):
        # do no actual parsing
        r = parse.parse('{{hello}}', '{hello}')
        self.assertEqual(r.fixed, ())
        self.assertEqual(r.named, {})

    def test_regular_expression(self):
        # match an actual regular expression
        s = r'^(hello\s[wW]{}!+.*)$'
        e = s.replace('{}', 'orld')
        r = parse.parse(s, e)
        self.assertEqual(r.fixed, ('orld',))
        e = s.replace('{}', '.*?')
        r = parse.parse(s, e)
        self.assertEqual(r.fixed, ('.*?',))

    def test_question_mark(self):
        # issue9: make sure a ? in the parse string is handled correctly
        r = parse.parse('"{}"?', '"teststr"?')
        self.assertEqual(r[0], 'teststr')

    def test_pipe(self):
        # issue22: make sure a | in the parse string is handled correctly
        r = parse.parse('| {}', '| teststr')
        self.assertEqual(r[0], 'teststr')

    def test_fixed(self):
        # pull a fixed value out of string
        r = parse.parse('hello {}', 'hello world')
        self.assertEqual(r.fixed, ('world', ))

    def test_left(self):
        # pull left-aligned text out of string
        r = parse.parse('{:<} world', 'hello       world')
        self.assertEqual(r.fixed, ('hello', ))

    def test_right(self):
        # pull right-aligned text out of string
        r = parse.parse('hello {:>}', 'hello       world')
        self.assertEqual(r.fixed, ('world', ))

    def test_center(self):
        # pull center-aligned text out of string
        r = parse.parse('hello {:^} world', 'hello  there     world')
        self.assertEqual(r.fixed, ('there', ))

    def test_typed(self):
        # pull a named, typed values out of string
        r = parse.parse('hello {:d} {:w}', 'hello 12 people')
        self.assertEqual(r.fixed, (12, 'people'))
        r = parse.parse('hello {:w} {:w}', 'hello 12 people')
        self.assertEqual(r.fixed, ('12', 'people'))

    def test_custom_type(self):
        # use a custom type
        r = parse.parse('{:shouty} {:spam}', 'hello world',
            dict(shouty=lambda s: s.upper(),
                spam=lambda s: ''.join(reversed(s))))
        self.assertEqual(r.fixed, ('HELLO', 'dlrow'))
        r = parse.parse('{:d}', '12', dict(d=lambda s: int(s) * 2))
        self.assertEqual(r.fixed, (24,))
        r = parse.parse('{:d}', '12')
        self.assertEqual(r.fixed, (12,))

    def test_typed_fail(self):
        # pull a named, typed values out of string
        self.assertEqual(parse.parse('hello {:d} {:w}', 'hello people 12'),
            None)

    def test_named(self):
        # pull a named value out of string
        r = parse.parse('hello {name}', 'hello world')
        self.assertEqual(r.named, {'name': 'world'})

    def test_named_repeated(self):
        # test a name may be repeated
        r = parse.parse('{n} {n}', 'x x')
        self.assertEqual(r.named, {'n': 'x'})

    def test_named_repeated_type(self):
        # test a name may be repeated with type conversion
        r = parse.parse('{n:d} {n:d}', '1 1')
        self.assertEqual(r.named, {'n': 1})

    def test_named_repeated_fail_value(self):
        # test repeated name fails if value mismatches
        r = parse.parse('{n} {n}', 'x y')
        self.assertEqual(r, None)

    def test_named_repeated_type_fail_value(self):
        # test repeated name with type conversion fails if value mismatches
        r = parse.parse('{n:d} {n:d}', '1 2')
        self.assertEqual(r, None)

    def test_named_repeated_type_fail_value(self):
        # test repeated name with mismatched type
        self.assertRaises(parse.RepeatedNameError, parse.compile,
            '{n:d} {n:w}')

    def test_mixed(self):
        # pull a fixed and named values out of string
        r = parse.parse('hello {} {name} {} {spam}',
            'hello world and other beings')
        self.assertEqual(r.fixed, ('world', 'other'))
        self.assertEqual(r.named, dict(name='and', spam='beings'))

    def test_named_typed(self):
        # pull a named, typed values out of string
        r = parse.parse('hello {number:d} {things}', 'hello 12 people')
        self.assertEqual(r.named, dict(number=12, things='people'))
        r = parse.parse('hello {number:w} {things}', 'hello 12 people')
        self.assertEqual(r.named, dict(number='12', things='people'))

    def test_named_aligned_typed(self):
        # pull a named, typed values out of string
        r = parse.parse('hello {number:<d} {things}', 'hello 12      people')
        self.assertEqual(r.named, dict(number=12, things='people'))
        r = parse.parse('hello {number:>d} {things}', 'hello      12 people')
        self.assertEqual(r.named, dict(number=12, things='people'))
        r = parse.parse('hello {number:^d} {things}',
            'hello      12      people')
        self.assertEqual(r.named, dict(number=12, things='people'))

    def test_multiline(self):
        r = parse.parse('hello\n{}\nworld', 'hello\nthere\nworld')
        self.assertEqual(r.fixed[0], 'there')

    def test_spans(self):
        # test the string sections our fields come from
        string = 'hello world'
        r = parse.parse('hello {}', string)
        self.assertEqual(r.spans, {0: (6, 11)})
        start, end = r.spans[0]
        self.assertEqual(string[start:end], r.fixed[0])

        string = 'hello     world'
        r = parse.parse('hello {:>}', string)
        self.assertEqual(r.spans, {0: (10, 15)})
        start, end = r.spans[0]
        self.assertEqual(string[start:end], r.fixed[0])

        string = 'hello 0x12 world'
        r = parse.parse('hello {val:x} world', string)
        self.assertEqual(r.spans, {'val': (6, 10)})
        start, end = r.spans['val']
        self.assertEqual(string[start:end], '0x%x' % r.named['val'])

        string = 'hello world and other beings'
        r = parse.parse('hello {} {name} {} {spam}', string)
        self.assertEqual(r.spans, {0: (6, 11), 'name': (12, 15),
            1: (16, 21), 'spam': (22, 28)})

    def test_numbers(self):
        # pull a numbers out of a string
        def y(fmt, s, e, str_equals=False):
            p = parse.compile(fmt)
            r = p.parse(s)
            if r is None:
                self.fail('%r (%r) did not match %r' % (fmt, p._expression, s))
            r = r.fixed[0]
            if str_equals:
                self.assertEqual(str(r), str(e),
                    '%r found %r in %r, not %r' % (fmt, r, s, e))
            else:
                self.assertEqual(r, e,
                    '%r found %r in %r, not %r' % (fmt, r, s, e))

        def n(fmt, s, e):
            if parse.parse(fmt, s) is not None:
                self.fail('%r matched %r' % (fmt, s))
        y('a {:d} b', 'a 0 b', 0)
        y('a {:d} b', 'a 12 b', 12)
        y('a {:5d} b', 'a    12 b', 12)
        y('a {:5d} b', 'a   -12 b', -12)
        y('a {:d} b', 'a -12 b', -12)
        y('a {:d} b', 'a +12 b', 12)
        y('a {:d} b', 'a  12 b', 12)
        y('a {:d} b', 'a 0b1000 b', 8)
        y('a {:d} b', 'a 0o1000 b', 512)
        y('a {:d} b', 'a 0x1000 b', 4096)
        y('a {:d} b', 'a 0xabcdef b', 0xabcdef)

        y('a {:%} b', 'a 100% b', 1)
        y('a {:%} b', 'a 50% b', .5)
        y('a {:%} b', 'a 50.1% b', .501)

        y('a {:n} b', 'a 100 b', 100)
        y('a {:n} b', 'a 1,000 b', 1000)
        y('a {:n} b', 'a 1.000 b', 1000)
        y('a {:n} b', 'a -1,000 b', -1000)
        y('a {:n} b', 'a 10,000 b', 10000)
        y('a {:n} b', 'a 100,000 b', 100000)
        n('a {:n} b', 'a 100,00 b', None)
        y('a {:n} b', 'a 100.000 b', 100000)
        y('a {:n} b', 'a 1.000.000 b', 1000000)

        y('a {:f} b', 'a 12.0 b', 12.0)
        y('a {:f} b', 'a -12.1 b', -12.1)
        y('a {:f} b', 'a +12.1 b', 12.1)
        n('a {:f} b', 'a 12 b', None)

        y('a {:e} b', 'a 1.0e10 b', 1.0e10)
        y('a {:e} b', 'a 1.0E10 b', 1.0e10)
        y('a {:e} b', 'a 1.10000e10 b', 1.1e10)
        y('a {:e} b', 'a 1.0e-10 b', 1.0e-10)
        y('a {:e} b', 'a 1.0e+10 b', 1.0e10)
        # can't actually test this one on values 'cos nan != nan
        y('a {:e} b', 'a nan b', float('nan'), str_equals=True)
        y('a {:e} b', 'a NAN b', float('nan'), str_equals=True)
        y('a {:e} b', 'a inf b', float('inf'))
        y('a {:e} b', 'a +inf b', float('inf'))
        y('a {:e} b', 'a -inf b', float('-inf'))
        y('a {:e} b', 'a INF b', float('inf'))
        y('a {:e} b', 'a +INF b', float('inf'))
        y('a {:e} b', 'a -INF b', float('-inf'))

        y('a {:g} b', 'a 1 b', 1)
        y('a {:g} b', 'a 1e10 b', 1e10)
        y('a {:g} b', 'a 1.0e10 b', 1.0e10)
        y('a {:g} b', 'a 1.0E10 b', 1.0e10)

        y('a {:b} b', 'a 1000 b', 8)
        y('a {:b} b', 'a 0b1000 b', 8)
        y('a {:o} b', 'a 12345670 b', int('12345670', 8))
        y('a {:o} b', 'a 0o12345670 b', int('12345670', 8))
        y('a {:x} b', 'a 1234567890abcdef b', 0x1234567890abcdef)
        y('a {:x} b', 'a 1234567890ABCDEF b', 0x1234567890ABCDEF)
        y('a {:x} b', 'a 0x1234567890abcdef b', 0x1234567890abcdef)
        y('a {:x} b', 'a 0x1234567890ABCDEF b', 0x1234567890ABCDEF)

        y('a {:05d} b', 'a 00001 b', 1)
        y('a {:05d} b', 'a -00001 b', -1)
        y('a {:05d} b', 'a +00001 b', 1)

        y('a {:=d} b', 'a 000012 b', 12)
        y('a {:x=5d} b', 'a xxx12 b', 12)
        y('a {:x=5d} b', 'a -xxx12 b', -12)


    def test_two_datetimes(self):
        r = parse.parse('a {:ti} {:ti} b', 'a 1997-07-16 2012-08-01 b')
        self.assertEqual(len(r.fixed), 2)
        self.assertEqual(r[0], datetime(1997, 7, 16))
        self.assertEqual(r[1], datetime(2012, 8, 1))

    def test_datetimes(self):
        def y(fmt, s, e, tz=None):
            p = parse.compile(fmt)
            r = p.parse(s)
            if r is None:
                self.fail('%r (%r) did not match %r' % (fmt, p._expression, s))
            r = r.fixed[0]
            try:
                self.assertEqual(r, e,
                    '%r found %r in %r, not %r' % (fmt, r, s, e))
            except ValueError:
                self.fail('%r found %r in %r, not %r' % (fmt, r, s, e))

            if tz is not None:
                self.assertEqual(r.tzinfo, tz,
                    '%r found TZ %r in %r, not %r' % (fmt, r.tzinfo, s, e))

        def n(fmt, s, e):
            if parse.parse(fmt, s) is not None:
                self.fail('%r matched %r' % (fmt, s))

        utc = parse.FixedTzOffset(0, 'UTC')
        aest = parse.FixedTzOffset(10 * 60, '+1000')
        tz60 = parse.FixedTzOffset(60, '+01:00')

        # ISO 8660 variants
        # YYYY-MM-DD (eg 1997-07-16)
        y('a {:ti} b', 'a 1997-07-16 b', datetime(1997, 7, 16))

        # YYYY-MM-DDThh:mmTZD (eg 1997-07-16T19:20+01:00)
        y('a {:ti} b', 'a 1997-07-16 19:20 b',
            datetime(1997, 7, 16, 19, 20, 0))
        y('a {:ti} b', 'a 1997-07-16T19:20 b',
            datetime(1997, 7, 16, 19, 20, 0))
        y('a {:ti} b', 'a 1997-07-16T19:20Z b',
            datetime(1997, 7, 16, 19, 20, tzinfo=utc))
        y('a {:ti} b', 'a 1997-07-16T19:20+0100 b',
            datetime(1997, 7, 16, 19, 20, tzinfo=tz60))
        y('a {:ti} b', 'a 1997-07-16T19:20+01:00 b',
            datetime(1997, 7, 16, 19, 20, tzinfo=tz60))
        y('a {:ti} b', 'a 1997-07-16T19:20 +01:00 b',
            datetime(1997, 7, 16, 19, 20, tzinfo=tz60))

        # YYYY-MM-DDThh:mm:ssTZD (eg 1997-07-16T19:20:30+01:00)
        y('a {:ti} b', 'a 1997-07-16 19:20:30 b',
            datetime(1997, 7, 16, 19, 20, 30))
        y('a {:ti} b', 'a 1997-07-16T19:20:30 b',
            datetime(1997, 7, 16, 19, 20, 30))
        y('a {:ti} b', 'a 1997-07-16T19:20:30Z b',
            datetime(1997, 7, 16, 19, 20, 30, tzinfo=utc))
        y('a {:ti} b', 'a 1997-07-16T19:20:30+01:00 b',
            datetime(1997, 7, 16, 19, 20, 30, tzinfo=tz60))
        y('a {:ti} b', 'a 1997-07-16T19:20:30 +01:00 b',
            datetime(1997, 7, 16, 19, 20, 30, tzinfo=tz60))

        # YYYY-MM-DDThh:mm:ss.sTZD (eg 1997-07-16T19:20:30.45+01:00)
        y('a {:ti} b', 'a 1997-07-16 19:20:30.500000 b',
            datetime(1997, 7, 16, 19, 20, 30, 500000))
        y('a {:ti} b', 'a 1997-07-16T19:20:30.500000 b',
            datetime(1997, 7, 16, 19, 20, 30, 500000))
        y('a {:ti} b', 'a 1997-07-16T19:20:30.5Z b',
            datetime(1997, 7, 16, 19, 20, 30, 500000, tzinfo=utc))
        y('a {:ti} b', 'a 1997-07-16T19:20:30.5+01:00 b',
            datetime(1997, 7, 16, 19, 20, 30, 500000, tzinfo=tz60))

        aest_d = datetime(2011, 11, 21, 10, 21, 36, tzinfo=aest)
        dt = datetime(2011, 11, 21, 10, 21, 36)
        dt00 = datetime(2011, 11, 21, 10, 21)
        d = datetime(2011, 11, 21)

        # te   RFC2822 e-mail format        datetime
        y('a {:te} b', 'a Mon, 21 Nov 2011 10:21:36 +1000 b', aest_d)
        y('a {:te} b', 'a Mon, 21 Nov 2011 10:21:36 +10:00 b', aest_d)
        y('a {:te} b', 'a 21 Nov 2011 10:21:36 +1000 b', aest_d)

        # tg   global (day/month) format datetime
        y('a {:tg} b', 'a 21/11/2011 10:21:36 AM +1000 b', aest_d)
        y('a {:tg} b', 'a 21/11/2011 10:21:36 AM +10:00 b', aest_d)
        y('a {:tg} b', 'a 21-11-2011 10:21:36 AM +1000 b', aest_d)
        y('a {:tg} b', 'a 21/11/2011 10:21:36 +1000 b', aest_d)
        y('a {:tg} b', 'a 21/11/2011 10:21:36 b', dt)
        y('a {:tg} b', 'a 21/11/2011 10:21 b', dt00)
        y('a {:tg} b', 'a 21-11-2011 b', d)
        y('a {:tg} b', 'a 21-Nov-2011 10:21:36 AM +1000 b', aest_d)
        y('a {:tg} b', 'a 21-November-2011 10:21:36 AM +1000 b', aest_d)

        # ta   US (month/day) format     datetime
        y('a {:ta} b', 'a 11/21/2011 10:21:36 AM +1000 b', aest_d)
        y('a {:ta} b', 'a 11/21/2011 10:21:36 AM +10:00 b', aest_d)
        y('a {:ta} b', 'a 11-21-2011 10:21:36 AM +1000 b', aest_d)
        y('a {:ta} b', 'a 11/21/2011 10:21:36 +1000 b', aest_d)
        y('a {:ta} b', 'a 11/21/2011 10:21:36 b', dt)
        y('a {:ta} b', 'a 11/21/2011 10:21 b', dt00)
        y('a {:ta} b', 'a 11-21-2011 b', d)
        y('a {:ta} b', 'a Nov-21-2011 10:21:36 AM +1000 b', aest_d)
        y('a {:ta} b', 'a November-21-2011 10:21:36 AM +1000 b', aest_d)
        y('a {:ta} b', 'a November-21-2011 b', d)

        # th   HTTP log format date/time                   datetime
        y('a {:th} b', 'a 21/Nov/2011:10:21:36 +1000 b', aest_d)
        y('a {:th} b', 'a 21/Nov/2011:10:21:36 +10:00 b', aest_d)

        d = datetime(2011, 11, 21, 10, 21, 36)

        # tc   ctime() format           datetime
        y('a {:tc} b', 'a Mon Nov 21 10:21:36 2011 b', d)

        t530 = parse.FixedTzOffset(-5 * 60 - 30, '-5:30')
        t830 = parse.FixedTzOffset(-8 * 60 - 30, '-8:30')

        # tt   Time                                        time
        y('a {:tt} b', 'a 10:21:36 AM +1000 b', time(10, 21, 36, tzinfo=aest))
        y('a {:tt} b', 'a 10:21:36 AM +10:00 b', time(10, 21, 36, tzinfo=aest))
        y('a {:tt} b', 'a 10:21:36 AM b', time(10, 21, 36))
        y('a {:tt} b', 'a 10:21:36 PM b', time(22, 21, 36))
        y('a {:tt} b', 'a 10:21:36 b', time(10, 21, 36))
        y('a {:tt} b', 'a 10:21 b', time(10, 21))
        y('a {:tt} b', 'a 10:21:36 PM -5:30 b', time(22, 21, 36, tzinfo=t530))
        y('a {:tt} b', 'a 10:21:36 PM -530 b', time(22, 21, 36, tzinfo=t530))
        y('a {:tt} b', 'a 10:21:36 PM -05:30 b', time(22, 21, 36, tzinfo=t530))
        y('a {:tt} b', 'a 10:21:36 PM -0530 b', time(22, 21, 36, tzinfo=t530))
        y('a {:tt} b', 'a 10:21:36 PM -08:30 b', time(22, 21, 36, tzinfo=t830))
        y('a {:tt} b', 'a 10:21:36 PM -0830 b', time(22, 21, 36, tzinfo=t830))

    def test_datetime_group_count(self):
        # test we increment the group count correctly for datetimes
        r = parse.parse('{:ti} {}', '1972-01-01 spam')
        self.assertEqual(r.fixed[1], 'spam')
        r = parse.parse('{:tg} {}', '1-1-1972 spam')
        self.assertEqual(r.fixed[1], 'spam')
        r = parse.parse('{:ta} {}', '1-1-1972 spam')
        self.assertEqual(r.fixed[1], 'spam')
        r = parse.parse('{:th} {}', '21/Nov/2011:10:21:36 +1000 spam')
        self.assertEqual(r.fixed[1], 'spam')
        r = parse.parse('{:te} {}', '21 Nov 2011 10:21:36 +1000 spam')
        self.assertEqual(r.fixed[1], 'spam')
        r = parse.parse('{:tc} {}', 'Mon Nov 21 10:21:36 2011 spam')
        self.assertEqual(r.fixed[1], 'spam')
        r = parse.parse('{:tt} {}', '10:21 spam')
        self.assertEqual(r.fixed[1], 'spam')

    def test_mixed_types(self):
        # stress-test: pull one of everything out of a string
        r = parse.parse('''
            letters: {:w}
            non-letters: {:W}
            whitespace: "{:s}"
            non-whitespace: \t{:S}\n
            digits: {:d} {:d}
            non-digits: {:D}
            numbers with thousands: {:n}
            fixed-point: {:f}
            floating-point: {:e}
            general numbers: {:g} {:g}
            binary: {:b}
            octal: {:o}
            hex: {:x}
            ISO 8601 e.g. {:ti}
            RFC2822 e.g. {:te}
            Global e.g. {:tg}
            US e.g. {:ta}
            ctime() e.g. {:tc}
            HTTP e.g. {:th}
            time: {:tt}
            final value: {}
        ''',
        '''
            letters: abcdef_GHIJLK
            non-letters: !@#%$ *^%
            whitespace: "   \t\n"
            non-whitespace: \tabc\n
            digits: 12345 0b1011011
            non-digits: abcdef
            numbers with thousands: 1,000
            fixed-point: 100.2345
            floating-point: 1.1e-10
            general numbers: 1 1.1
            binary: 0b1000
            octal: 0o1000
            hex: 0x1000
            ISO 8601 e.g. 1972-01-20T10:21:36Z
            RFC2822 e.g. Mon, 20 Jan 1972 10:21:36 +1000
            Global e.g. 20/1/1972 10:21:36 AM +1:00
            US e.g. 1/20/1972 10:21:36 PM +10:30
            ctime() e.g. Sun Sep 16 01:03:52 1973
            HTTP e.g. 21/Nov/2011:00:07:11 +0000
            time: 10:21:36 PM -5:30
            final value: spam
        ''')
        self.assertNotEqual(r, None)
        self.assertEqual(r.fixed[22], 'spam')

    def test_mixed_type_variant(self):
        r = parse.parse('''
            letters: {:w}
            non-letters: {:W}
            whitespace: "{:s}"
            non-whitespace: \t{:S}\n
            digits: {:d}
            non-digits: {:D}
            numbers with thousands: {:n}
            fixed-point: {:f}
            floating-point: {:e}
            general numbers: {:g} {:g}
            binary: {:b}
            octal: {:o}
            hex: {:x}
            ISO 8601 e.g. {:ti}
            RFC2822 e.g. {:te}
            Global e.g. {:tg}
            US e.g. {:ta}
            ctime() e.g. {:tc}
            HTTP e.g. {:th}
            time: {:tt}
            final value: {}
        ''',
        '''
            letters: abcdef_GHIJLK
            non-letters: !@#%$ *^%
            whitespace: "   \t\n"
            non-whitespace: \tabc\n
            digits: 0xabcdef
            non-digits: abcdef
            numbers with thousands: 1.000.000
            fixed-point: 0.00001
            floating-point: NAN
            general numbers: 1.1e10 nan
            binary: 0B1000
            octal: 0O1000
            hex: 0X1000
            ISO 8601 e.g. 1972-01-20T10:21:36Z
            RFC2822 e.g. Mon, 20 Jan 1972 10:21:36 +1000
            Global e.g. 20/1/1972 10:21:36 AM +1:00
            US e.g. 1/20/1972 10:21:36 PM +10:30
            ctime() e.g. Sun Sep 16 01:03:52 1973
            HTTP e.g. 21/Nov/2011:00:07:11 +0000
            time: 10:21:36 PM -5:30
            final value: spam
        ''')
        self.assertNotEqual(r, None)
        self.assertEqual(r.fixed[21], 'spam')

    def test_too_many_fields(self):
        p = parse.compile('{:ti}' * 15)
        self.assertRaises(parse.TooManyFields, p.parse, '')


class TestSearch(unittest.TestCase):
    def test_basic(self):
        # basic search() test
        r = parse.search('a {} c', ' a b c ')
        self.assertEqual(r.fixed, ('b',))

    def test_multiline(self):
        # multiline search() test
        r = parse.search('age: {:d}\n', 'name: Rufus\nage: 42\ncolor: red\n')
        self.assertEqual(r.fixed, (42,))

    def test_pos(self):
        # basic search() test
        r = parse.search('a {} c', ' a b c ', 2)
        self.assertEqual(r, None)


class TestFindall(unittest.TestCase):
    def test_findall(self):
        # basic findall() test
        s = ''.join(r.fixed[0] for r in parse.findall(">{}<",
            "<p>some <b>bold</b> text</p>"))
        self.assertEqual(s, "some bold text")


class TestBugs(unittest.TestCase):
    def test_named_date_issue7(self):
        r = parse.parse('on {date:ti}', 'on 2012-09-17')
        self.assertEqual(r['date'], datetime(2012, 9, 17, 0, 0, 0))

        # fix introduced regressions
        r = parse.parse('a {:ti} b', 'a 1997-07-16T19:20 b')
        self.assertEqual(r[0], datetime(1997, 7, 16, 19, 20, 0))
        r = parse.parse('a {:ti} b', 'a 1997-07-16T19:20Z b')
        utc = parse.FixedTzOffset(0, 'UTC')
        self.assertEqual(r[0], datetime(1997, 7, 16, 19, 20, tzinfo=utc))
        r = parse.parse('a {date:ti} b', 'a 1997-07-16T19:20Z b')
        self.assertEqual(r['date'], datetime(1997, 7, 16, 19, 20, tzinfo=utc))

    def test_dotted_type_conversion_pull_8(self):
        # test pull request 8 which fixes type conversion related to dotted
        # names being applied correctly
        r = parse.parse('{a.b:d}', '1')
        self.assertEqual(r['a.b'], 1)
        r = parse.parse('{a_b:w} {a.b:d}', '1 2')
        self.assertEqual(r['a_b'], '1')
        self.assertEqual(r['a.b'], 2)

    def test_pm_overflow_issue16(self):
        r = parse.parse('Meet at {:tg}', 'Meet at 1/2/2011 12:45 PM')
        self.assertEqual(r[0], datetime(2011, 2, 2, 0, 45))


# -----------------------------------------------------------------------------
# TEST SUPPORT FOR: TestParseType
# -----------------------------------------------------------------------------


class TestParseType(unittest.TestCase):

    def assert_match(self, parser, text, param_name, expected):
        result = parser.parse(text)
        self.assertEqual(result[param_name], expected)

    def assert_mismatch(self, parser, text, param_name):
        result = parser.parse(text)
        self.assertTrue(result is None)

    def test_pattern_should_be_used(self):
        def parse_number(text):
            return int(text)
        parse_number.pattern = r"\d+"
        parse_number.name = "Number"    # For testing only.

        extra_types = {parse_number.name: parse_number}
        format = "Value is {number:Number} and..."
        parser = parse.Parser(format, extra_types)

        self.assert_match(parser, "Value is 42 and...", "number", 42)
        self.assert_match(parser, "Value is 00123 and...", "number", 123)
        self.assert_mismatch(parser, "Value is ALICE and...", "number")
        self.assert_mismatch(parser, "Value is -123 and...", "number")

    def test_pattern_should_be_used2(self):
        def parse_yesno(text):
            return parse_yesno.mapping[text.lower()]
        parse_yesno.mapping = {
            "yes": True, "no": False,
            "on": True, "off": False,
            "true": True, "false": False,
        }
        parse_yesno.pattern = r"|".join(parse_yesno.mapping.keys())
        parse_yesno.name = "YesNo"      # For testing only.

        extra_types = {parse_yesno.name: parse_yesno}
        format = "Answer: {answer:YesNo}"
        parser = parse.Parser(format, extra_types)

        # -- ENSURE: Known enum values are correctly extracted.
        for value_name, value in parse_yesno.mapping.items():
            text = "Answer: %s" % value_name
            self.assert_match(parser, text, "answer", value)

        # -- IGNORE-CASE: In parsing, calls type converter function !!!
        self.assert_match(parser, "Answer: YES", "answer", True)
        self.assert_mismatch(parser, "Answer: __YES__", "answer")

    def test_with_pattern(self):
        ab_vals = dict(a=1, b=2)

        @parse.with_pattern(r'[ab]')
        def ab(text):
            return ab_vals[text]

        parser = parse.Parser('test {result:ab}', {'ab': ab})
        self.assert_match(parser, 'test a', 'result', 1)
        self.assert_match(parser, 'test b', 'result', 2)
        self.assert_mismatch(parser, "test c", "result")


if __name__ == '__main__':
    unittest.main()


# Copyright (c) 2011 eKit.com Inc (http://www.ekit.com/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# vim: set filetype=python ts=4 sw=4 et si tw=75

########NEW FILE########
