__FILENAME__ = easter
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime

__all__ = ["easter", "EASTER_JULIAN", "EASTER_ORTHODOX", "EASTER_WESTERN"]

EASTER_JULIAN   = 1
EASTER_ORTHODOX = 2
EASTER_WESTERN  = 3

def easter(year, method=EASTER_WESTERN):
    """
    This method was ported from the work done by GM Arts,
    on top of the algorithm by Claus Tondering, which was
    based in part on the algorithm of Ouding (1940), as
    quoted in "Explanatory Supplement to the Astronomical
    Almanac", P.  Kenneth Seidelmann, editor.

    This algorithm implements three different easter
    calculation methods:
    
    1 - Original calculation in Julian calendar, valid in
        dates after 326 AD
    2 - Original method, with date converted to Gregorian
        calendar, valid in years 1583 to 4099
    3 - Revised method, in Gregorian calendar, valid in
        years 1583 to 4099 as well

    These methods are represented by the constants:

    EASTER_JULIAN   = 1
    EASTER_ORTHODOX = 2
    EASTER_WESTERN  = 3

    The default method is method 3.
    
    More about the algorithm may be found at:

    http://users.chariot.net.au/~gmarts/eastalg.htm

    and

    http://www.tondering.dk/claus/calendar.html

    """

    if not (1 <= method <= 3):
        raise ValueError, "invalid method"

    # g - Golden year - 1
    # c - Century
    # h - (23 - Epact) mod 30
    # i - Number of days from March 21 to Paschal Full Moon
    # j - Weekday for PFM (0=Sunday, etc)
    # p - Number of days from March 21 to Sunday on or before PFM
    #     (-6 to 28 methods 1 & 3, to 56 for method 2)
    # e - Extra days to add for method 2 (converting Julian
    #     date to Gregorian date)

    y = year
    g = y % 19
    e = 0
    if method < 3:
        # Old method
        i = (19*g+15)%30
        j = (y+y//4+i)%7
        if method == 2:
            # Extra dates to convert Julian to Gregorian date
            e = 10
            if y > 1600:
                e = e+y//100-16-(y//100-16)//4
    else:
        # New method
        c = y//100
        h = (c-c//4-(8*c+13)//25+19*g+15)%30
        i = h-(h//28)*(1-(h//28)*(29//(h+1))*((21-g)//11))
        j = (y+y//4+i+2-c+c//4)%7

    # p can be from -6 to 56 corresponding to dates 22 March to 23 May
    # (later dates apply to method 2, although 23 May never actually occurs)
    p = i-j+e
    d = 1+(p+27+(p+6)//40)%31
    m = 3+(p+26)//30
    return datetime.date(int(y),int(m),int(d))


########NEW FILE########
__FILENAME__ = parser
# -*- coding:iso-8859-1 -*-
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import string
import time
import sys
import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import relativedelta
import tz


__all__ = ["parse", "parserinfo"]


# Some pointers:
#
# http://www.cl.cam.ac.uk/~mgk25/iso-time.html
# http://www.iso.ch/iso/en/prods-services/popstds/datesandtime.html
# http://www.w3.org/TR/NOTE-datetime
# http://ringmaster.arc.nasa.gov/tools/time_formats.html
# http://search.cpan.org/author/MUIR/Time-modules-2003.0211/lib/Time/ParseDate.pm
# http://stein.cshl.org/jade/distrib/docs/java.text.SimpleDateFormat.html


class _timelex(object):

    def __init__(self, instream):
        if isinstance(instream, basestring):
            instream = StringIO(instream)
        self.instream = instream
        self.wordchars = ('abcdfeghijklmnopqrstuvwxyz'
                          'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
                          'ßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
                          'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ')
        self.numchars = '0123456789'
        self.whitespace = ' \t\r\n'
        self.charstack = []
        self.tokenstack = []
        self.eof = False

    def get_token(self):
        if self.tokenstack:
            return self.tokenstack.pop(0)
        seenletters = False
        token = None
        state = None
        wordchars = self.wordchars
        numchars = self.numchars
        whitespace = self.whitespace
        while not self.eof:
            if self.charstack:
                nextchar = self.charstack.pop(0)
            else:
                nextchar = self.instream.read(1)
                while nextchar == '\x00':
                    nextchar = self.instream.read(1)
            if not nextchar:
                self.eof = True
                break
            elif not state:
                token = nextchar
                if nextchar in wordchars:
                    state = 'a'
                elif nextchar in numchars:
                    state = '0'
                elif nextchar in whitespace:
                    token = ' '
                    break # emit token
                else:
                    break # emit token
            elif state == 'a':
                seenletters = True
                if nextchar in wordchars:
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == '0':
                if nextchar in numchars:
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == 'a.':
                seenletters = True
                if nextchar == '.' or nextchar in wordchars:
                    token += nextchar
                elif nextchar in numchars and token[-1] == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == '0.':
                if nextchar == '.' or nextchar in numchars:
                    token += nextchar
                elif nextchar in wordchars and token[-1] == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
        if (state in ('a.', '0.') and
            (seenletters or token.count('.') > 1 or token[-1] == '.')):
            l = token.split('.')
            token = l[0]
            for tok in l[1:]:
                self.tokenstack.append('.')
                if tok:
                    self.tokenstack.append(tok)
        return token

    def __iter__(self):
        return self

    def next(self):
        token = self.get_token()
        if token is None:
            raise StopIteration
        return token

    def split(cls, s):
        return list(cls(s))
    split = classmethod(split)


class _resultbase(object):

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def _repr(self, classname):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, `value`))
        return "%s(%s)" % (classname, ", ".join(l))

    def __repr__(self):
        return self._repr(self.__class__.__name__)


class parserinfo(object):

    # m from a.m/p.m, t from ISO T separator
    JUMP = [" ", ".", ",", ";", "-", "/", "'",
            "at", "on", "and", "ad", "m", "t", "of",
            "st", "nd", "rd", "th"] 

    WEEKDAYS = [("Mon", "Monday"),
                ("Tue", "Tuesday"),
                ("Wed", "Wednesday"),
                ("Thu", "Thursday"),
                ("Fri", "Friday"),
                ("Sat", "Saturday"),
                ("Sun", "Sunday")]
    MONTHS   = [("Jan", "January"),
                ("Feb", "February"),
                ("Mar", "March"),
                ("Apr", "April"),
                ("May", "May"),
                ("Jun", "June"),
                ("Jul", "July"),
                ("Aug", "August"),
                ("Sep", "September"),
                ("Oct", "October"),
                ("Nov", "November"),
                ("Dec", "December")]
    HMS = [("h", "hour", "hours"),
           ("m", "minute", "minutes"),
           ("s", "second", "seconds")]
    AMPM = [("am", "a"),
            ("pm", "p")]
    UTCZONE = ["UTC", "GMT", "Z"]
    PERTAIN = ["of"]
    TZOFFSET = {}

    def __init__(self, dayfirst=False, yearfirst=False):
        self._jump = self._convert(self.JUMP)
        self._weekdays = self._convert(self.WEEKDAYS)
        self._months = self._convert(self.MONTHS)
        self._hms = self._convert(self.HMS)
        self._ampm = self._convert(self.AMPM)
        self._utczone = self._convert(self.UTCZONE)
        self._pertain = self._convert(self.PERTAIN)

        self.dayfirst = dayfirst
        self.yearfirst = yearfirst

        self._year = time.localtime().tm_year
        self._century = self._year//100*100

    def _convert(self, lst):
        dct = {}
        for i in range(len(lst)):
            v = lst[i]
            if isinstance(v, tuple):
                for v in v:
                    dct[v.lower()] = i
            else:
                dct[v.lower()] = i
        return dct

    def jump(self, name):
        return name.lower() in self._jump

    def weekday(self, name):
        if len(name) >= 3:
            try:
                return self._weekdays[name.lower()]
            except KeyError:
                pass
        return None

    def month(self, name):
        if len(name) >= 3:
            try:
                return self._months[name.lower()]+1
            except KeyError:
                pass
        return None

    def hms(self, name):
        try:
            return self._hms[name.lower()]
        except KeyError:
            return None

    def ampm(self, name):
        try:
            return self._ampm[name.lower()]
        except KeyError:
            return None

    def pertain(self, name):
        return name.lower() in self._pertain

    def utczone(self, name):
        return name.lower() in self._utczone

    def tzoffset(self, name):
        if name in self._utczone:
            return 0
        return self.TZOFFSET.get(name)

    def convertyear(self, year):
        if year < 100:
            year += self._century
            if abs(year-self._year) >= 50:
                if year < self._year:
                    year += 100
                else:
                    year -= 100
        return year

    def validate(self, res):
        # move to info
        if res.year is not None:
            res.year = self.convertyear(res.year)
        if res.tzoffset == 0 and not res.tzname or res.tzname == 'Z':
            res.tzname = "UTC"
            res.tzoffset = 0
        elif res.tzoffset != 0 and res.tzname and self.utczone(res.tzname):
            res.tzoffset = 0
        return True


class parser(object):

    def __init__(self, info=None):
        self.info = info or parserinfo()

    def parse(self, timestr, default=None,
                    ignoretz=False, tzinfos=None,
                    **kwargs):
        if not default:
            default = datetime.datetime.now().replace(hour=0, minute=0,
                                                      second=0, microsecond=0)
        res = self._parse(timestr, **kwargs)
        if res is None:
            raise ValueError, "unknown string format"
        repl = {}
        for attr in ["year", "month", "day", "hour",
                     "minute", "second", "microsecond"]:
            value = getattr(res, attr)
            if value is not None:
                repl[attr] = value
        ret = default.replace(**repl)
        if res.weekday is not None and not res.day:
            ret = ret+relativedelta.relativedelta(weekday=res.weekday)
        if not ignoretz:
            if callable(tzinfos) or tzinfos and res.tzname in tzinfos:
                if callable(tzinfos):
                    tzdata = tzinfos(res.tzname, res.tzoffset)
                else:
                    tzdata = tzinfos.get(res.tzname)
                if isinstance(tzdata, datetime.tzinfo):
                    tzinfo = tzdata
                elif isinstance(tzdata, basestring):
                    tzinfo = tz.tzstr(tzdata)
                elif isinstance(tzdata, int):
                    tzinfo = tz.tzoffset(res.tzname, tzdata)
                else:
                    raise ValueError, "offset must be tzinfo subclass, " \
                                      "tz string, or int offset"
                ret = ret.replace(tzinfo=tzinfo)
            elif res.tzname and res.tzname in time.tzname:
                ret = ret.replace(tzinfo=tz.tzlocal())
            elif res.tzoffset == 0:
                ret = ret.replace(tzinfo=tz.tzutc())
            elif res.tzoffset:
                ret = ret.replace(tzinfo=tz.tzoffset(res.tzname, res.tzoffset))
        return ret

    class _result(_resultbase):
        __slots__ = ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond",
                     "tzname", "tzoffset"]

    def _parse(self, timestr, dayfirst=None, yearfirst=None, fuzzy=False):
        info = self.info
        if dayfirst is None:
            dayfirst = info.dayfirst
        if yearfirst is None:
            yearfirst = info.yearfirst
        res = self._result()
        l = _timelex.split(timestr)
        try:

            # year/month/day list
            ymd = []

            # Index of the month string in ymd
            mstridx = -1

            len_l = len(l)
            i = 0
            while i < len_l:

                # Check if it's a number
                try:
                    value_repr = l[i]
                    value = float(value_repr)
                except ValueError:
                    value = None

                if value is not None:
                    # Token is a number
                    len_li = len(l[i])
                    i += 1
                    if (len(ymd) == 3 and len_li in (2, 4)
                        and (i >= len_l or (l[i] != ':' and
                                            info.hms(l[i]) is None))):
                        # 19990101T23[59]
                        s = l[i-1]
                        res.hour = int(s[:2])
                        if len_li == 4:
                            res.minute = int(s[2:])
                    elif len_li == 6 or (len_li > 6 and l[i-1].find('.') == 6):
                        # YYMMDD or HHMMSS[.ss]
                        s = l[i-1] 
                        if not ymd and l[i-1].find('.') == -1:
                            ymd.append(info.convertyear(int(s[:2])))
                            ymd.append(int(s[2:4]))
                            ymd.append(int(s[4:]))
                        else:
                            # 19990101T235959[.59]
                            res.hour = int(s[:2])
                            res.minute = int(s[2:4])
                            res.second, res.microsecond = _parsems(s[4:])
                    elif len_li == 8:
                        # YYYYMMDD
                        s = l[i-1]
                        ymd.append(int(s[:4]))
                        ymd.append(int(s[4:6]))
                        ymd.append(int(s[6:]))
                    elif len_li in (12, 14):
                        # YYYYMMDDhhmm[ss]
                        s = l[i-1]
                        ymd.append(int(s[:4]))
                        ymd.append(int(s[4:6]))
                        ymd.append(int(s[6:8]))
                        res.hour = int(s[8:10])
                        res.minute = int(s[10:12])
                        if len_li == 14:
                            res.second = int(s[12:])
                    elif ((i < len_l and info.hms(l[i]) is not None) or
                          (i+1 < len_l and l[i] == ' ' and
                           info.hms(l[i+1]) is not None)):
                        # HH[ ]h or MM[ ]m or SS[.ss][ ]s
                        if l[i] == ' ':
                            i += 1
                        idx = info.hms(l[i])
                        while True:
                            if idx == 0:
                                res.hour = int(value)
                                if value%1:
                                    res.minute = int(60*(value%1))
                            elif idx == 1:
                                res.minute = int(value)
                                if value%1:
                                    res.second = int(60*(value%1))
                            elif idx == 2:
                                res.second, res.microsecond = \
                                    _parsems(value_repr)
                            i += 1
                            if i >= len_l or idx == 2:
                                break
                            # 12h00
                            try:
                                value_repr = l[i]
                                value = float(value_repr)
                            except ValueError:
                                break
                            else:
                                i += 1
                                idx += 1
                                if i < len_l:
                                    newidx = info.hms(l[i])
                                    if newidx is not None:
                                        idx = newidx
                    elif i+1 < len_l and l[i] == ':':
                        # HH:MM[:SS[.ss]]
                        res.hour = int(value)
                        i += 1
                        value = float(l[i])
                        res.minute = int(value)
                        if value%1:
                            res.second = int(60*(value%1))
                        i += 1
                        if i < len_l and l[i] == ':':
                            res.second, res.microsecond = _parsems(l[i+1])
                            i += 2
                    elif i < len_l and l[i] in ('-', '/', '.'):
                        sep = l[i]
                        ymd.append(int(value))
                        i += 1
                        if i < len_l and not info.jump(l[i]):
                            try:
                                # 01-01[-01]
                                ymd.append(int(l[i]))
                            except ValueError:
                                # 01-Jan[-01]
                                value = info.month(l[i])
                                if value is not None:
                                    ymd.append(value)
                                    assert mstridx == -1
                                    mstridx = len(ymd)-1
                                else:
                                    return None
                            i += 1
                            if i < len_l and l[i] == sep:
                                # We have three members
                                i += 1
                                value = info.month(l[i])
                                if value is not None:
                                    ymd.append(value)
                                    mstridx = len(ymd)-1
                                    assert mstridx == -1
                                else:
                                    ymd.append(int(l[i]))
                                i += 1
                    elif i >= len_l or info.jump(l[i]):
                        if i+1 < len_l and info.ampm(l[i+1]) is not None:
                            # 12 am
                            res.hour = int(value)
                            if res.hour < 12 and info.ampm(l[i+1]) == 1:
                                res.hour += 12
                            elif res.hour == 12 and info.ampm(l[i+1]) == 0:
                                res.hour = 0
                            i += 1
                        else:
                            # Year, month or day
                            ymd.append(int(value))
                        i += 1
                    elif info.ampm(l[i]) is not None:
                        # 12am
                        res.hour = int(value)
                        if res.hour < 12 and info.ampm(l[i]) == 1:
                            res.hour += 12
                        elif res.hour == 12 and info.ampm(l[i]) == 0:
                            res.hour = 0
                        i += 1
                    elif not fuzzy:
                        return None
                    else:
                        i += 1
                    continue

                # Check weekday
                value = info.weekday(l[i])
                if value is not None:
                    res.weekday = value
                    i += 1
                    continue

                # Check month name
                value = info.month(l[i])
                if value is not None:
                    ymd.append(value)
                    assert mstridx == -1
                    mstridx = len(ymd)-1
                    i += 1
                    if i < len_l:
                        if l[i] in ('-', '/'):
                            # Jan-01[-99]
                            sep = l[i]
                            i += 1
                            ymd.append(int(l[i]))
                            i += 1
                            if i < len_l and l[i] == sep:
                                # Jan-01-99
                                i += 1
                                ymd.append(int(l[i]))
                                i += 1
                        elif (i+3 < len_l and l[i] == l[i+2] == ' '
                              and info.pertain(l[i+1])):
                            # Jan of 01
                            # In this case, 01 is clearly year
                            try:
                                value = int(l[i+3])
                            except ValueError:
                                # Wrong guess
                                pass
                            else:
                                # Convert it here to become unambiguous
                                ymd.append(info.convertyear(value))
                            i += 4
                    continue

                # Check am/pm
                value = info.ampm(l[i])
                if value is not None:
                    if value == 1 and res.hour < 12:
                        res.hour += 12
                    elif value == 0 and res.hour == 12:
                        res.hour = 0
                    i += 1
                    continue

                # Check for a timezone name
                if (res.hour is not None and len(l[i]) <= 5 and
                    res.tzname is None and res.tzoffset is None and
                    not [x for x in l[i] if x not in string.ascii_uppercase]):
                    res.tzname = l[i]
                    res.tzoffset = info.tzoffset(res.tzname)
                    i += 1

                    # Check for something like GMT+3, or BRST+3. Notice
                    # that it doesn't mean "I am 3 hours after GMT", but
                    # "my time +3 is GMT". If found, we reverse the
                    # logic so that timezone parsing code will get it
                    # right.
                    if i < len_l and l[i] in ('+', '-'):
                        l[i] = ('+', '-')[l[i] == '+']
                        res.tzoffset = None
                        if info.utczone(res.tzname):
                            # With something like GMT+3, the timezone
                            # is *not* GMT.
                            res.tzname = None

                    continue

                # Check for a numbered timezone
                if res.hour is not None and l[i] in ('+', '-'):
                    signal = (-1,1)[l[i] == '+']
                    i += 1
                    len_li = len(l[i])
                    if len_li == 4:
                        # -0300
                        res.tzoffset = int(l[i][:2])*3600+int(l[i][2:])*60
                    elif i+1 < len_l and l[i+1] == ':':
                        # -03:00
                        res.tzoffset = int(l[i])*3600+int(l[i+2])*60
                        i += 2
                    elif len_li <= 2:
                        # -[0]3
                        res.tzoffset = int(l[i][:2])*3600
                    else:
                        return None
                    i += 1
                    res.tzoffset *= signal

                    # Look for a timezone name between parenthesis
                    if (i+3 < len_l and
                        info.jump(l[i]) and l[i+1] == '(' and l[i+3] == ')' and
                        3 <= len(l[i+2]) <= 5 and
                        not [x for x in l[i+2]
                                if x not in string.ascii_uppercase]):
                        # -0300 (BRST)
                        res.tzname = l[i+2]
                        i += 4
                    continue

                # Check jumps
                if not (info.jump(l[i]) or fuzzy):
                    return None

                i += 1

            # Process year/month/day
            len_ymd = len(ymd)
            if len_ymd > 3:
                # More than three members!?
                return None
            elif len_ymd == 1 or (mstridx != -1 and len_ymd == 2):
                # One member, or two members with a month string
                if mstridx != -1:
                    res.month = ymd[mstridx]
                    del ymd[mstridx]
                if len_ymd > 1 or mstridx == -1:
                    if ymd[0] > 31:
                        res.year = ymd[0]
                    else:
                        res.day = ymd[0]
            elif len_ymd == 2:
                # Two members with numbers
                if ymd[0] > 31:
                    # 99-01
                    res.year, res.month = ymd
                elif ymd[1] > 31:
                    # 01-99
                    res.month, res.year = ymd
                elif dayfirst and ymd[1] <= 12:
                    # 13-01
                    res.day, res.month = ymd
                else:
                    # 01-13
                    res.month, res.day = ymd
            if len_ymd == 3:
                # Three members
                if mstridx == 0:
                    res.month, res.day, res.year = ymd
                elif mstridx == 1:
                    if ymd[0] > 31 or (yearfirst and ymd[2] <= 31):
                        # 99-Jan-01
                        res.year, res.month, res.day = ymd
                    else:
                        # 01-Jan-01
                        # Give precendence to day-first, since
                        # two-digit years is usually hand-written.
                        res.day, res.month, res.year = ymd
                elif mstridx == 2:
                    # WTF!?
                    if ymd[1] > 31:
                        # 01-99-Jan
                        res.day, res.year, res.month = ymd
                    else:
                        # 99-01-Jan
                        res.year, res.day, res.month = ymd
                else:
                    if ymd[0] > 31 or \
                       (yearfirst and ymd[1] <= 12 and ymd[2] <= 31):
                        # 99-01-01
                        res.year, res.month, res.day = ymd
                    elif ymd[0] > 12 or (dayfirst and ymd[1] <= 12):
                        # 13-01-01
                        res.day, res.month, res.year = ymd
                    else:
                        # 01-13-01
                        res.month, res.day, res.year = ymd

        except (IndexError, ValueError, AssertionError):
            return None

        if not info.validate(res):
            return None
        return res

DEFAULTPARSER = parser()
def parse(timestr, parserinfo=None, **kwargs):
    if parserinfo:
        return parser(parserinfo).parse(timestr, **kwargs)
    else:
        return DEFAULTPARSER.parse(timestr, **kwargs)


class _tzparser(object):

    class _result(_resultbase):

        __slots__ = ["stdabbr", "stdoffset", "dstabbr", "dstoffset",
                     "start", "end"]

        class _attr(_resultbase):
            __slots__ = ["month", "week", "weekday",
                         "yday", "jyday", "day", "time"]

        def __repr__(self):
            return self._repr("")

        def __init__(self):
            _resultbase.__init__(self)
            self.start = self._attr()
            self.end = self._attr()

    def parse(self, tzstr):
        res = self._result()
        l = _timelex.split(tzstr)
        try:

            len_l = len(l)

            i = 0
            while i < len_l:
                # BRST+3[BRDT[+2]]
                j = i
                while j < len_l and not [x for x in l[j]
                                            if x in "0123456789:,-+"]:
                    j += 1
                if j != i:
                    if not res.stdabbr:
                        offattr = "stdoffset"
                        res.stdabbr = "".join(l[i:j])
                    else:
                        offattr = "dstoffset"
                        res.dstabbr = "".join(l[i:j])
                    i = j
                    if (i < len_l and
                        (l[i] in ('+', '-') or l[i][0] in "0123456789")):
                        if l[i] in ('+', '-'):
                            # Yes, that's right.  See the TZ variable
                            # documentation.
                            signal = (1,-1)[l[i] == '+']
                            i += 1
                        else:
                            signal = -1
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            setattr(res, offattr,
                                    (int(l[i][:2])*3600+int(l[i][2:])*60)*signal)
                        elif i+1 < len_l and l[i+1] == ':':
                            # -03:00
                            setattr(res, offattr,
                                    (int(l[i])*3600+int(l[i+2])*60)*signal)
                            i += 2
                        elif len_li <= 2:
                            # -[0]3
                            setattr(res, offattr,
                                    int(l[i][:2])*3600*signal)
                        else:
                            return None
                        i += 1
                    if res.dstabbr:
                        break
                else:
                    break

            if i < len_l:
                for j in range(i, len_l):
                    if l[j] == ';': l[j] = ','

                assert l[i] == ','

                i += 1

            if i >= len_l:
                pass
            elif (8 <= l.count(',') <= 9 and
                not [y for x in l[i:] if x != ','
                       for y in x if y not in "0123456789"]):
                # GMT0BST,3,0,30,3600,10,0,26,7200[,3600]
                for x in (res.start, res.end):
                    x.month = int(l[i])
                    i += 2
                    if l[i] == '-':
                        value = int(l[i+1])*-1
                        i += 1
                    else:
                        value = int(l[i])
                    i += 2
                    if value:
                        x.week = value
                        x.weekday = (int(l[i])-1)%7
                    else:
                        x.day = int(l[i])
                    i += 2
                    x.time = int(l[i])
                    i += 2
                if i < len_l:
                    if l[i] in ('-','+'):
                        signal = (-1,1)[l[i] == "+"]
                        i += 1
                    else:
                        signal = 1
                    res.dstoffset = (res.stdoffset+int(l[i]))*signal
            elif (l.count(',') == 2 and l[i:].count('/') <= 2 and
                  not [y for x in l[i:] if x not in (',','/','J','M',
                                                     '.','-',':')
                         for y in x if y not in "0123456789"]):
                for x in (res.start, res.end):
                    if l[i] == 'J':
                        # non-leap year day (1 based)
                        i += 1
                        x.jyday = int(l[i])
                    elif l[i] == 'M':
                        # month[-.]week[-.]weekday
                        i += 1
                        x.month = int(l[i])
                        i += 1
                        assert l[i] in ('-', '.')
                        i += 1
                        x.week = int(l[i])
                        if x.week == 5:
                            x.week = -1
                        i += 1
                        assert l[i] in ('-', '.')
                        i += 1
                        x.weekday = (int(l[i])-1)%7
                    else:
                        # year day (zero based)
                        x.yday = int(l[i])+1

                    i += 1

                    if i < len_l and l[i] == '/':
                        i += 1
                        # start time
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            x.time = (int(l[i][:2])*3600+int(l[i][2:])*60)
                        elif i+1 < len_l and l[i+1] == ':':
                            # -03:00
                            x.time = int(l[i])*3600+int(l[i+2])*60
                            i += 2
                            if i+1 < len_l and l[i+1] == ':':
                                i += 2
                                x.time += int(l[i])
                        elif len_li <= 2:
                            # -[0]3
                            x.time = (int(l[i][:2])*3600)
                        else:
                            return None
                        i += 1

                    assert i == len_l or l[i] == ','

                    i += 1

                assert i >= len_l

        except (IndexError, ValueError, AssertionError):
            return None
        
        return res


DEFAULTTZPARSER = _tzparser()
def _parsetz(tzstr):
    return DEFAULTTZPARSER.parse(tzstr)


def _parsems(value):
    """Parse a I[.F] seconds value into (seconds, microseconds)."""
    if "." not in value:
        return int(value), 0
    else:
        i, f = value.split(".")
        return int(i), int(f.ljust(6, "0")[:6])


# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = relativedelta
"""
Copyright (c) 2003-2010  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import calendar

__all__ = ["relativedelta", "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)

MO, TU, WE, TH, FR, SA, SU = weekdays = tuple([weekday(x) for x in range(7)])

class relativedelta:
    """
The relativedelta type is based on the specification of the excelent
work done by M.-A. Lemburg in his mx.DateTime extension. However,
notice that this type does *NOT* implement the same algorithm as
his work. Do *NOT* expect it to behave like mx.DateTime's counterpart.

There's two different ways to build a relativedelta instance. The
first one is passing it two date/datetime classes:

    relativedelta(datetime1, datetime2)

And the other way is to use the following keyword arguments:

    year, month, day, hour, minute, second, microsecond:
        Absolute information.

    years, months, weeks, days, hours, minutes, seconds, microseconds:
        Relative information, may be negative.

    weekday:
        One of the weekday instances (MO, TU, etc). These instances may
        receive a parameter N, specifying the Nth weekday, which could
        be positive or negative (like MO(+1) or MO(-2). Not specifying
        it is the same as specifying +1. You can also use an integer,
        where 0=MO.

    leapdays:
        Will add given days to the date found, if year is a leap
        year, and the date found is post 28 of february.

    yearday, nlyearday:
        Set the yearday or the non-leap year day (jump leap days).
        These are converted to day/month/leapdays information.

Here is the behavior of operations with relativedelta:

1) Calculate the absolute year, using the 'year' argument, or the
   original datetime year, if the argument is not present.

2) Add the relative 'years' argument to the absolute year.

3) Do steps 1 and 2 for month/months.

4) Calculate the absolute day, using the 'day' argument, or the
   original datetime day, if the argument is not present. Then,
   subtract from the day until it fits in the year and month
   found after their operations.

5) Add the relative 'days' argument to the absolute day. Notice
   that the 'weeks' argument is multiplied by 7 and added to
   'days'.

6) Do steps 1 and 2 for hour/hours, minute/minutes, second/seconds,
   microsecond/microseconds.

7) If the 'weekday' argument is present, calculate the weekday,
   with the given (wday, nth) tuple. wday is the index of the
   weekday (0-6, 0=Mon), and nth is the number of weeks to add
   forward or backward, depending on its signal. Notice that if
   the calculated date is already Monday, for example, using
   (0, 1) or (0, -1) won't change the day.
    """

    def __init__(self, dt1=None, dt2=None,
                 years=0, months=0, days=0, leapdays=0, weeks=0,
                 hours=0, minutes=0, seconds=0, microseconds=0,
                 year=None, month=None, day=None, weekday=None,
                 yearday=None, nlyearday=None,
                 hour=None, minute=None, second=None, microsecond=None):
        if dt1 and dt2:
            if not isinstance(dt1, datetime.date) or \
               not isinstance(dt2, datetime.date):
                raise TypeError, "relativedelta only diffs datetime/date"
            if type(dt1) is not type(dt2):
                if not isinstance(dt1, datetime.datetime):
                    dt1 = datetime.datetime.fromordinal(dt1.toordinal())
                elif not isinstance(dt2, datetime.datetime):
                    dt2 = datetime.datetime.fromordinal(dt2.toordinal())
            self.years = 0
            self.months = 0
            self.days = 0
            self.leapdays = 0
            self.hours = 0
            self.minutes = 0
            self.seconds = 0
            self.microseconds = 0
            self.year = None
            self.month = None
            self.day = None
            self.weekday = None
            self.hour = None
            self.minute = None
            self.second = None
            self.microsecond = None
            self._has_time = 0

            months = (dt1.year*12+dt1.month)-(dt2.year*12+dt2.month)
            self._set_months(months)
            dtm = self.__radd__(dt2)
            if dt1 < dt2:
                while dt1 > dtm:
                    months += 1
                    self._set_months(months)
                    dtm = self.__radd__(dt2)
            else:
                while dt1 < dtm:
                    months -= 1
                    self._set_months(months)
                    dtm = self.__radd__(dt2)
            delta = dt1 - dtm
            self.seconds = delta.seconds+delta.days*86400
            self.microseconds = delta.microseconds
        else:
            self.years = years
            self.months = months
            self.days = days+weeks*7
            self.leapdays = leapdays
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds
            self.microseconds = microseconds
            self.year = year
            self.month = month
            self.day = day
            self.hour = hour
            self.minute = minute
            self.second = second
            self.microsecond = microsecond

            if type(weekday) is int:
                self.weekday = weekdays[weekday]
            else:
                self.weekday = weekday

            yday = 0
            if nlyearday:
                yday = nlyearday
            elif yearday:
                yday = yearday
                if yearday > 59:
                    self.leapdays = -1
            if yday:
                ydayidx = [31,59,90,120,151,181,212,243,273,304,334,366]
                for idx, ydays in enumerate(ydayidx):
                    if yday <= ydays:
                        self.month = idx+1
                        if idx == 0:
                            self.day = yday
                        else:
                            self.day = yday-ydayidx[idx-1]
                        break
                else:
                    raise ValueError, "invalid year day (%d)" % yday

        self._fix()

    def _fix(self):
        if abs(self.microseconds) > 999999:
            s = self.microseconds//abs(self.microseconds)
            div, mod = divmod(self.microseconds*s, 1000000)
            self.microseconds = mod*s
            self.seconds += div*s
        if abs(self.seconds) > 59:
            s = self.seconds//abs(self.seconds)
            div, mod = divmod(self.seconds*s, 60)
            self.seconds = mod*s
            self.minutes += div*s
        if abs(self.minutes) > 59:
            s = self.minutes//abs(self.minutes)
            div, mod = divmod(self.minutes*s, 60)
            self.minutes = mod*s
            self.hours += div*s
        if abs(self.hours) > 23:
            s = self.hours//abs(self.hours)
            div, mod = divmod(self.hours*s, 24)
            self.hours = mod*s
            self.days += div*s
        if abs(self.months) > 11:
            s = self.months//abs(self.months)
            div, mod = divmod(self.months*s, 12)
            self.months = mod*s
            self.years += div*s
        if (self.hours or self.minutes or self.seconds or self.microseconds or
            self.hour is not None or self.minute is not None or
            self.second is not None or self.microsecond is not None):
            self._has_time = 1
        else:
            self._has_time = 0

    def _set_months(self, months):
        self.months = months
        if abs(self.months) > 11:
            s = self.months//abs(self.months)
            div, mod = divmod(self.months*s, 12)
            self.months = mod*s
            self.years = div*s
        else:
            self.years = 0

    def __radd__(self, other):
        if not isinstance(other, datetime.date):
            raise TypeError, "unsupported type for add operation"
        elif self._has_time and not isinstance(other, datetime.datetime):
            other = datetime.datetime.fromordinal(other.toordinal())
        year = (self.year or other.year)+self.years
        month = self.month or other.month
        if self.months:
            assert 1 <= abs(self.months) <= 12
            month += self.months
            if month > 12:
                year += 1
                month -= 12
            elif month < 1:
                year -= 1
                month += 12
        day = min(calendar.monthrange(year, month)[1],
                  self.day or other.day)
        repl = {"year": year, "month": month, "day": day}
        for attr in ["hour", "minute", "second", "microsecond"]:
            value = getattr(self, attr)
            if value is not None:
                repl[attr] = value
        days = self.days
        if self.leapdays and month > 2 and calendar.isleap(year):
            days += self.leapdays
        ret = (other.replace(**repl)
               + datetime.timedelta(days=days,
                                    hours=self.hours,
                                    minutes=self.minutes,
                                    seconds=self.seconds,
                                    microseconds=self.microseconds))
        if self.weekday:
            weekday, nth = self.weekday.weekday, self.weekday.n or 1
            jumpdays = (abs(nth)-1)*7
            if nth > 0:
                jumpdays += (7-ret.weekday()+weekday)%7
            else:
                jumpdays += (ret.weekday()-weekday)%7
                jumpdays *= -1
            ret += datetime.timedelta(days=jumpdays)
        return ret

    def __rsub__(self, other):
        return self.__neg__().__radd__(other)

    def __add__(self, other):
        if not isinstance(other, relativedelta):
            raise TypeError, "unsupported type for add operation"
        return relativedelta(years=other.years+self.years,
                             months=other.months+self.months,
                             days=other.days+self.days,
                             hours=other.hours+self.hours,
                             minutes=other.minutes+self.minutes,
                             seconds=other.seconds+self.seconds,
                             microseconds=other.microseconds+self.microseconds,
                             leapdays=other.leapdays or self.leapdays,
                             year=other.year or self.year,
                             month=other.month or self.month,
                             day=other.day or self.day,
                             weekday=other.weekday or self.weekday,
                             hour=other.hour or self.hour,
                             minute=other.minute or self.minute,
                             second=other.second or self.second,
                             microsecond=other.second or self.microsecond)

    def __sub__(self, other):
        if not isinstance(other, relativedelta):
            raise TypeError, "unsupported type for sub operation"
        return relativedelta(years=other.years-self.years,
                             months=other.months-self.months,
                             days=other.days-self.days,
                             hours=other.hours-self.hours,
                             minutes=other.minutes-self.minutes,
                             seconds=other.seconds-self.seconds,
                             microseconds=other.microseconds-self.microseconds,
                             leapdays=other.leapdays or self.leapdays,
                             year=other.year or self.year,
                             month=other.month or self.month,
                             day=other.day or self.day,
                             weekday=other.weekday or self.weekday,
                             hour=other.hour or self.hour,
                             minute=other.minute or self.minute,
                             second=other.second or self.second,
                             microsecond=other.second or self.microsecond)

    def __neg__(self):
        return relativedelta(years=-self.years,
                             months=-self.months,
                             days=-self.days,
                             hours=-self.hours,
                             minutes=-self.minutes,
                             seconds=-self.seconds,
                             microseconds=-self.microseconds,
                             leapdays=self.leapdays,
                             year=self.year,
                             month=self.month,
                             day=self.day,
                             weekday=self.weekday,
                             hour=self.hour,
                             minute=self.minute,
                             second=self.second,
                             microsecond=self.microsecond)

    def __nonzero__(self):
        return not (not self.years and
                    not self.months and
                    not self.days and
                    not self.hours and
                    not self.minutes and
                    not self.seconds and
                    not self.microseconds and
                    not self.leapdays and
                    self.year is None and
                    self.month is None and
                    self.day is None and
                    self.weekday is None and
                    self.hour is None and
                    self.minute is None and
                    self.second is None and
                    self.microsecond is None)

    def __mul__(self, other):
        f = float(other)
        return relativedelta(years        = int(round(self.years*f)),
                             months       = int(round(self.months*f)),
                             days         = int(round(self.days*f)),
                             hours        = int(round(self.hours*f)),
                             minutes      = int(round(self.minutes*f)),
                             seconds      = int(round(self.seconds*f)),
                             microseconds = self.microseconds*f,
                             leapdays     = self.leapdays,
                             year         = self.year,
                             month        = self.month,
                             day          = self.day,
                             weekday      = self.weekday,
                             hour         = self.hour,
                             minute       = self.minute,
                             second       = self.second,
                             microsecond  = self.microsecond)

    def __eq__(self, other):
        if not isinstance(other, relativedelta):
            return False
        if self.weekday or other.weekday:
            if not self.weekday or not other.weekday:
                return False
            if self.weekday.weekday != other.weekday.weekday:
                return False
            n1, n2 = self.weekday.n, other.weekday.n
            if n1 != n2 and not ((not n1 or n1 == 1) and (not n2 or n2 == 1)):
                return False
        return (self.years == other.years and
                self.months == other.months and
                self.days == other.days and
                self.hours == other.hours and
                self.minutes == other.minutes and
                self.seconds == other.seconds and
                self.leapdays == other.leapdays and
                self.year == other.year and
                self.month == other.month and
                self.day == other.day and
                self.hour == other.hour and
                self.minute == other.minute and
                self.second == other.second and
                self.microsecond == other.microsecond)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __div__(self, other):
        return self.__mul__(1/float(other))

    def __repr__(self):
        l = []
        for attr in ["years", "months", "days", "leapdays",
                     "hours", "minutes", "seconds", "microseconds"]:
            value = getattr(self, attr)
            if value:
                l.append("%s=%+d" % (attr, value))
        for attr in ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond"]:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, `value`))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = rrule
"""
Copyright (c) 2003-2010  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import itertools
import datetime
import calendar
import thread
import heapq
import sys

__all__ = ["rrule", "rruleset", "rrulestr",
           "YEARLY", "MONTHLY", "WEEKLY", "DAILY",
           "HOURLY", "MINUTELY", "SECONDLY",
           "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

# Every mask is 7 days longer to handle cross-year weekly periods.
M366MASK = tuple([1]*31+[2]*29+[3]*31+[4]*30+[5]*31+[6]*30+
                 [7]*31+[8]*31+[9]*30+[10]*31+[11]*30+[12]*31+[1]*7)
M365MASK = list(M366MASK)
M29, M30, M31 = range(1,30), range(1,31), range(1,32)
MDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
MDAY365MASK = list(MDAY366MASK)
M29, M30, M31 = range(-29,0), range(-30,0), range(-31,0)
NMDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
NMDAY365MASK = list(NMDAY366MASK)
M366RANGE = (0,31,60,91,121,152,182,213,244,274,305,335,366)
M365RANGE = (0,31,59,90,120,151,181,212,243,273,304,334,365)
WDAYMASK = [0,1,2,3,4,5,6]*55
del M29, M30, M31, M365MASK[59], MDAY365MASK[59], NMDAY365MASK[31]
MDAY365MASK = tuple(MDAY365MASK)
M365MASK = tuple(M365MASK)

(YEARLY,
 MONTHLY,
 WEEKLY,
 DAILY,
 HOURLY,
 MINUTELY,
 SECONDLY) = range(7)

# Imported on demand.
easter = None
parser = None

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        if n == 0:
            raise ValueError, "Can't create weekday with n == 0"
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)

MO, TU, WE, TH, FR, SA, SU = weekdays = tuple([weekday(x) for x in range(7)])

class rrulebase:
    def __init__(self, cache=False):
        if cache:
            self._cache = []
            self._cache_lock = thread.allocate_lock()
            self._cache_gen  = self._iter()
            self._cache_complete = False
        else:
            self._cache = None
            self._cache_complete = False
        self._len = None

    def __iter__(self):
        if self._cache_complete:
            return iter(self._cache)
        elif self._cache is None:
            return self._iter()
        else:
            return self._iter_cached()

    def _iter_cached(self):
        i = 0
        gen = self._cache_gen
        cache = self._cache
        acquire = self._cache_lock.acquire
        release = self._cache_lock.release
        while gen:
            if i == len(cache):
                acquire()
                if self._cache_complete:
                    break
                try:
                    for j in range(10):
                        cache.append(gen.next())
                except StopIteration:
                    self._cache_gen = gen = None
                    self._cache_complete = True
                    break
                release()
            yield cache[i]
            i += 1
        while i < self._len:
            yield cache[i]
            i += 1

    def __getitem__(self, item):
        if self._cache_complete:
            return self._cache[item]
        elif isinstance(item, slice):
            if item.step and item.step < 0:
                return list(iter(self))[item]
            else:
                return list(itertools.islice(self,
                                             item.start or 0,
                                             item.stop or sys.maxint,
                                             item.step or 1))
        elif item >= 0:
            gen = iter(self)
            try:
                for i in range(item+1):
                    res = gen.next()
            except StopIteration:
                raise IndexError
            return res
        else:
            return list(iter(self))[item]

    def __contains__(self, item):
        if self._cache_complete:
            return item in self._cache
        else:
            for i in self:
                if i == item:
                    return True
                elif i > item:
                    return False
        return False

    # __len__() introduces a large performance penality.
    def count(self):
        if self._len is None:
            for x in self: pass
        return self._len

    def before(self, dt, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        last = None
        if inc:
            for i in gen:
                if i > dt:
                    break
                last = i
        else:
            for i in gen:
                if i >= dt:
                    break
                last = i
        return last

    def after(self, dt, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        if inc:
            for i in gen:
                if i >= dt:
                    return i
        else:
            for i in gen:
                if i > dt:
                    return i
        return None

    def between(self, after, before, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        started = False
        l = []
        if inc:
            for i in gen:
                if i > before:
                    break
                elif not started:
                    if i >= after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        else:
            for i in gen:
                if i >= before:
                    break
                elif not started:
                    if i > after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        return l

class rrule(rrulebase):
    def __init__(self, freq, dtstart=None,
                 interval=1, wkst=None, count=None, until=None, bysetpos=None,
                 bymonth=None, bymonthday=None, byyearday=None, byeaster=None,
                 byweekno=None, byweekday=None,
                 byhour=None, byminute=None, bysecond=None,
                 cache=False):
        rrulebase.__init__(self, cache)
        global easter
        if not dtstart:
            dtstart = datetime.datetime.now().replace(microsecond=0)
        elif not isinstance(dtstart, datetime.datetime):
            dtstart = datetime.datetime.fromordinal(dtstart.toordinal())
        else:
            dtstart = dtstart.replace(microsecond=0)
        self._dtstart = dtstart
        self._tzinfo = dtstart.tzinfo
        self._freq = freq
        self._interval = interval
        self._count = count
        if until and not isinstance(until, datetime.datetime):
            until = datetime.datetime.fromordinal(until.toordinal())
        self._until = until
        if wkst is None:
            self._wkst = calendar.firstweekday()
        elif type(wkst) is int:
            self._wkst = wkst
        else:
            self._wkst = wkst.weekday
        if bysetpos is None:
            self._bysetpos = None
        elif type(bysetpos) is int:
            if bysetpos == 0 or not (-366 <= bysetpos <= 366):
                raise ValueError("bysetpos must be between 1 and 366, "
                                 "or between -366 and -1")
            self._bysetpos = (bysetpos,)
        else:
            self._bysetpos = tuple(bysetpos)
            for pos in self._bysetpos:
                if pos == 0 or not (-366 <= pos <= 366):
                    raise ValueError("bysetpos must be between 1 and 366, "
                                     "or between -366 and -1")
        if not (byweekno or byyearday or bymonthday or
                byweekday is not None or byeaster is not None):
            if freq == YEARLY:
                if not bymonth:
                    bymonth = dtstart.month
                bymonthday = dtstart.day
            elif freq == MONTHLY:
                bymonthday = dtstart.day
            elif freq == WEEKLY:
                byweekday = dtstart.weekday()
        # bymonth
        if not bymonth:
            self._bymonth = None
        elif type(bymonth) is int:
            self._bymonth = (bymonth,)
        else:
            self._bymonth = tuple(bymonth)
        # byyearday
        if not byyearday:
            self._byyearday = None
        elif type(byyearday) is int:
            self._byyearday = (byyearday,)
        else:
            self._byyearday = tuple(byyearday)
        # byeaster
        if byeaster is not None:
            if not easter:
                from dateutil import easter
            if type(byeaster) is int:
                self._byeaster = (byeaster,)
            else:
                self._byeaster = tuple(byeaster)
        else:
            self._byeaster = None
        # bymonthay
        if not bymonthday:
            self._bymonthday = ()
            self._bynmonthday = ()
        elif type(bymonthday) is int:
            if bymonthday < 0:
                self._bynmonthday = (bymonthday,)
                self._bymonthday = ()
            else:
                self._bymonthday = (bymonthday,)
                self._bynmonthday = ()
        else:
            self._bymonthday = tuple([x for x in bymonthday if x > 0])
            self._bynmonthday = tuple([x for x in bymonthday if x < 0])
        # byweekno
        if byweekno is None:
            self._byweekno = None
        elif type(byweekno) is int:
            self._byweekno = (byweekno,)
        else:
            self._byweekno = tuple(byweekno)
        # byweekday / bynweekday
        if byweekday is None:
            self._byweekday = None
            self._bynweekday = None
        elif type(byweekday) is int:
            self._byweekday = (byweekday,)
            self._bynweekday = None
        elif hasattr(byweekday, "n"):
            if not byweekday.n or freq > MONTHLY:
                self._byweekday = (byweekday.weekday,)
                self._bynweekday = None
            else:
                self._bynweekday = ((byweekday.weekday, byweekday.n),)
                self._byweekday = None
        else:
            self._byweekday = []
            self._bynweekday = []
            for wday in byweekday:
                if type(wday) is int:
                    self._byweekday.append(wday)
                elif not wday.n or freq > MONTHLY:
                    self._byweekday.append(wday.weekday)
                else:
                    self._bynweekday.append((wday.weekday, wday.n))
            self._byweekday = tuple(self._byweekday)
            self._bynweekday = tuple(self._bynweekday)
            if not self._byweekday:
                self._byweekday = None
            elif not self._bynweekday:
                self._bynweekday = None
        # byhour
        if byhour is None:
            if freq < HOURLY:
                self._byhour = (dtstart.hour,)
            else:
                self._byhour = None
        elif type(byhour) is int:
            self._byhour = (byhour,)
        else:
            self._byhour = tuple(byhour)
        # byminute
        if byminute is None:
            if freq < MINUTELY:
                self._byminute = (dtstart.minute,)
            else:
                self._byminute = None
        elif type(byminute) is int:
            self._byminute = (byminute,)
        else:
            self._byminute = tuple(byminute)
        # bysecond
        if bysecond is None:
            if freq < SECONDLY:
                self._bysecond = (dtstart.second,)
            else:
                self._bysecond = None
        elif type(bysecond) is int:
            self._bysecond = (bysecond,)
        else:
            self._bysecond = tuple(bysecond)

        if self._freq >= HOURLY:
            self._timeset = None
        else:
            self._timeset = []
            for hour in self._byhour:
                for minute in self._byminute:
                    for second in self._bysecond:
                        self._timeset.append(
                                datetime.time(hour, minute, second,
                                                    tzinfo=self._tzinfo))
            self._timeset.sort()
            self._timeset = tuple(self._timeset)

    def _iter(self):
        year, month, day, hour, minute, second, weekday, yearday, _ = \
            self._dtstart.timetuple()

        # Some local variables to speed things up a bit
        freq = self._freq
        interval = self._interval
        wkst = self._wkst
        until = self._until
        bymonth = self._bymonth
        byweekno = self._byweekno
        byyearday = self._byyearday
        byweekday = self._byweekday
        byeaster = self._byeaster
        bymonthday = self._bymonthday
        bynmonthday = self._bynmonthday
        bysetpos = self._bysetpos
        byhour = self._byhour
        byminute = self._byminute
        bysecond = self._bysecond

        ii = _iterinfo(self)
        ii.rebuild(year, month)

        getdayset = {YEARLY:ii.ydayset,
                     MONTHLY:ii.mdayset,
                     WEEKLY:ii.wdayset,
                     DAILY:ii.ddayset,
                     HOURLY:ii.ddayset,
                     MINUTELY:ii.ddayset,
                     SECONDLY:ii.ddayset}[freq]
        
        if freq < HOURLY:
            timeset = self._timeset
        else:
            gettimeset = {HOURLY:ii.htimeset,
                          MINUTELY:ii.mtimeset,
                          SECONDLY:ii.stimeset}[freq]
            if ((freq >= HOURLY and
                 self._byhour and hour not in self._byhour) or
                (freq >= MINUTELY and
                 self._byminute and minute not in self._byminute) or
                (freq >= SECONDLY and
                 self._bysecond and second not in self._bysecond)):
                timeset = ()
            else:
                timeset = gettimeset(hour, minute, second)

        total = 0
        count = self._count
        while True:
            # Get dayset with the right frequency
            dayset, start, end = getdayset(year, month, day)

            # Do the "hard" work ;-)
            filtered = False
            for i in dayset[start:end]:
                if ((bymonth and ii.mmask[i] not in bymonth) or
                    (byweekno and not ii.wnomask[i]) or
                    (byweekday and ii.wdaymask[i] not in byweekday) or
                    (ii.nwdaymask and not ii.nwdaymask[i]) or
                    (byeaster and not ii.eastermask[i]) or
                    ((bymonthday or bynmonthday) and
                     ii.mdaymask[i] not in bymonthday and
                     ii.nmdaymask[i] not in bynmonthday) or
                    (byyearday and
                     ((i < ii.yearlen and i+1 not in byyearday
                                      and -ii.yearlen+i not in byyearday) or
                      (i >= ii.yearlen and i+1-ii.yearlen not in byyearday
                                       and -ii.nextyearlen+i-ii.yearlen
                                           not in byyearday)))):
                    dayset[i] = None
                    filtered = True

            # Output results
            if bysetpos and timeset:
                poslist = []
                for pos in bysetpos:
                    if pos < 0:
                        daypos, timepos = divmod(pos, len(timeset))
                    else:
                        daypos, timepos = divmod(pos-1, len(timeset))
                    try:
                        i = [x for x in dayset[start:end]
                                if x is not None][daypos]
                        time = timeset[timepos]
                    except IndexError:
                        pass
                    else:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        res = datetime.datetime.combine(date, time)
                        if res not in poslist:
                            poslist.append(res)
                poslist.sort()
                for res in poslist:
                    if until and res > until:
                        self._len = total
                        return
                    elif res >= self._dtstart:
                        total += 1
                        yield res
                        if count:
                            count -= 1
                            if not count:
                                self._len = total
                                return
            else:
                for i in dayset[start:end]:
                    if i is not None:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        for time in timeset:
                            res = datetime.datetime.combine(date, time)
                            if until and res > until:
                                self._len = total
                                return
                            elif res >= self._dtstart:
                                total += 1
                                yield res
                                if count:
                                    count -= 1
                                    if not count:
                                        self._len = total
                                        return

            # Handle frequency and interval
            fixday = False
            if freq == YEARLY:
                year += interval
                if year > datetime.MAXYEAR:
                    self._len = total
                    return
                ii.rebuild(year, month)
            elif freq == MONTHLY:
                month += interval
                if month > 12:
                    div, mod = divmod(month, 12)
                    month = mod
                    year += div
                    if month == 0:
                        month = 12
                        year -= 1
                    if year > datetime.MAXYEAR:
                        self._len = total
                        return
                ii.rebuild(year, month)
            elif freq == WEEKLY:
                if wkst > weekday:
                    day += -(weekday+1+(6-wkst))+self._interval*7
                else:
                    day += -(weekday-wkst)+self._interval*7
                weekday = wkst
                fixday = True
            elif freq == DAILY:
                day += interval
                fixday = True
            elif freq == HOURLY:
                if filtered:
                    # Jump to one iteration before next day
                    hour += ((23-hour)//interval)*interval
                while True:
                    hour += interval
                    div, mod = divmod(hour, 24)
                    if div:
                        hour = mod
                        day += div
                        fixday = True
                    if not byhour or hour in byhour:
                        break
                timeset = gettimeset(hour, minute, second)
            elif freq == MINUTELY:
                if filtered:
                    # Jump to one iteration before next day
                    minute += ((1439-(hour*60+minute))//interval)*interval
                while True:
                    minute += interval
                    div, mod = divmod(minute, 60)
                    if div:
                        minute = mod
                        hour += div
                        div, mod = divmod(hour, 24)
                        if div:
                            hour = mod
                            day += div
                            fixday = True
                            filtered = False
                    if ((not byhour or hour in byhour) and
                        (not byminute or minute in byminute)):
                        break
                timeset = gettimeset(hour, minute, second)
            elif freq == SECONDLY:
                if filtered:
                    # Jump to one iteration before next day
                    second += (((86399-(hour*3600+minute*60+second))
                                //interval)*interval)
                while True:
                    second += self._interval
                    div, mod = divmod(second, 60)
                    if div:
                        second = mod
                        minute += div
                        div, mod = divmod(minute, 60)
                        if div:
                            minute = mod
                            hour += div
                            div, mod = divmod(hour, 24)
                            if div:
                                hour = mod
                                day += div
                                fixday = True
                    if ((not byhour or hour in byhour) and
                        (not byminute or minute in byminute) and
                        (not bysecond or second in bysecond)):
                        break
                timeset = gettimeset(hour, minute, second)

            if fixday and day > 28:
                daysinmonth = calendar.monthrange(year, month)[1]
                if day > daysinmonth:
                    while day > daysinmonth:
                        day -= daysinmonth
                        month += 1
                        if month == 13:
                            month = 1
                            year += 1
                            if year > datetime.MAXYEAR:
                                self._len = total
                                return
                        daysinmonth = calendar.monthrange(year, month)[1]
                    ii.rebuild(year, month)

class _iterinfo(object):
    __slots__ = ["rrule", "lastyear", "lastmonth",
                 "yearlen", "nextyearlen", "yearordinal", "yearweekday",
                 "mmask", "mrange", "mdaymask", "nmdaymask",
                 "wdaymask", "wnomask", "nwdaymask", "eastermask"]

    def __init__(self, rrule):
        for attr in self.__slots__:
            setattr(self, attr, None)
        self.rrule = rrule

    def rebuild(self, year, month):
        # Every mask is 7 days longer to handle cross-year weekly periods.
        rr = self.rrule
        if year != self.lastyear:
            self.yearlen = 365+calendar.isleap(year)
            self.nextyearlen = 365+calendar.isleap(year+1)
            firstyday = datetime.date(year, 1, 1)
            self.yearordinal = firstyday.toordinal()
            self.yearweekday = firstyday.weekday()

            wday = datetime.date(year, 1, 1).weekday()
            if self.yearlen == 365:
                self.mmask = M365MASK
                self.mdaymask = MDAY365MASK
                self.nmdaymask = NMDAY365MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M365RANGE
            else:
                self.mmask = M366MASK
                self.mdaymask = MDAY366MASK
                self.nmdaymask = NMDAY366MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M366RANGE

            if not rr._byweekno:
                self.wnomask = None
            else:
                self.wnomask = [0]*(self.yearlen+7)
                #no1wkst = firstwkst = self.wdaymask.index(rr._wkst)
                no1wkst = firstwkst = (7-self.yearweekday+rr._wkst)%7
                if no1wkst >= 4:
                    no1wkst = 0
                    # Number of days in the year, plus the days we got
                    # from last year.
                    wyearlen = self.yearlen+(self.yearweekday-rr._wkst)%7
                else:
                    # Number of days in the year, minus the days we
                    # left in last year.
                    wyearlen = self.yearlen-no1wkst
                div, mod = divmod(wyearlen, 7)
                numweeks = div+mod//4
                for n in rr._byweekno:
                    if n < 0:
                        n += numweeks+1
                    if not (0 < n <= numweeks):
                        continue
                    if n > 1:
                        i = no1wkst+(n-1)*7
                        if no1wkst != firstwkst:
                            i -= 7-firstwkst
                    else:
                        i = no1wkst
                    for j in range(7):
                        self.wnomask[i] = 1
                        i += 1
                        if self.wdaymask[i] == rr._wkst:
                            break
                if 1 in rr._byweekno:
                    # Check week number 1 of next year as well
                    # TODO: Check -numweeks for next year.
                    i = no1wkst+numweeks*7
                    if no1wkst != firstwkst:
                        i -= 7-firstwkst
                    if i < self.yearlen:
                        # If week starts in next year, we
                        # don't care about it.
                        for j in range(7):
                            self.wnomask[i] = 1
                            i += 1
                            if self.wdaymask[i] == rr._wkst:
                                break
                if no1wkst:
                    # Check last week number of last year as
                    # well. If no1wkst is 0, either the year
                    # started on week start, or week number 1
                    # got days from last year, so there are no
                    # days from last year's last week number in
                    # this year.
                    if -1 not in rr._byweekno:
                        lyearweekday = datetime.date(year-1,1,1).weekday()
                        lno1wkst = (7-lyearweekday+rr._wkst)%7
                        lyearlen = 365+calendar.isleap(year-1)
                        if lno1wkst >= 4:
                            lno1wkst = 0
                            lnumweeks = 52+(lyearlen+
                                           (lyearweekday-rr._wkst)%7)%7//4
                        else:
                            lnumweeks = 52+(self.yearlen-no1wkst)%7//4
                    else:
                        lnumweeks = -1
                    if lnumweeks in rr._byweekno:
                        for i in range(no1wkst):
                            self.wnomask[i] = 1

        if (rr._bynweekday and
            (month != self.lastmonth or year != self.lastyear)):
            ranges = []
            if rr._freq == YEARLY:
                if rr._bymonth:
                    for month in rr._bymonth:
                        ranges.append(self.mrange[month-1:month+1])
                else:
                    ranges = [(0, self.yearlen)]
            elif rr._freq == MONTHLY:
                ranges = [self.mrange[month-1:month+1]]
            if ranges:
                # Weekly frequency won't get here, so we may not
                # care about cross-year weekly periods.
                self.nwdaymask = [0]*self.yearlen
                for first, last in ranges:
                    last -= 1
                    for wday, n in rr._bynweekday:
                        if n < 0:
                            i = last+(n+1)*7
                            i -= (self.wdaymask[i]-wday)%7
                        else:
                            i = first+(n-1)*7
                            i += (7-self.wdaymask[i]+wday)%7
                        if first <= i <= last:
                            self.nwdaymask[i] = 1

        if rr._byeaster:
            self.eastermask = [0]*(self.yearlen+7)
            eyday = easter.easter(year).toordinal()-self.yearordinal
            for offset in rr._byeaster:
                self.eastermask[eyday+offset] = 1

        self.lastyear = year
        self.lastmonth = month

    def ydayset(self, year, month, day):
        return range(self.yearlen), 0, self.yearlen

    def mdayset(self, year, month, day):
        set = [None]*self.yearlen
        start, end = self.mrange[month-1:month+1]
        for i in range(start, end):
            set[i] = i
        return set, start, end

    def wdayset(self, year, month, day):
        # We need to handle cross-year weeks here.
        set = [None]*(self.yearlen+7)
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        start = i
        for j in range(7):
            set[i] = i
            i += 1
            #if (not (0 <= i < self.yearlen) or
            #    self.wdaymask[i] == self.rrule._wkst):
            # This will cross the year boundary, if necessary.
            if self.wdaymask[i] == self.rrule._wkst:
                break
        return set, start, i

    def ddayset(self, year, month, day):
        set = [None]*self.yearlen
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        set[i] = i
        return set, i, i+1

    def htimeset(self, hour, minute, second):
        set = []
        rr = self.rrule
        for minute in rr._byminute:
            for second in rr._bysecond:
                set.append(datetime.time(hour, minute, second,
                                         tzinfo=rr._tzinfo))
        set.sort()
        return set

    def mtimeset(self, hour, minute, second):
        set = []
        rr = self.rrule
        for second in rr._bysecond:
            set.append(datetime.time(hour, minute, second, tzinfo=rr._tzinfo))
        set.sort()
        return set

    def stimeset(self, hour, minute, second):
        return (datetime.time(hour, minute, second,
                tzinfo=self.rrule._tzinfo),)


class rruleset(rrulebase):

    class _genitem:
        def __init__(self, genlist, gen):
            try:
                self.dt = gen()
                genlist.append(self)
            except StopIteration:
                pass
            self.genlist = genlist
            self.gen = gen

        def next(self):
            try:
                self.dt = self.gen()
            except StopIteration:
                if self.genlist[0] is self:
                    heapq.heappop(self.genlist)
                else:
                    self.genlist.remove(self)
                    heapq.heapify(self.genlist)

        def __cmp__(self, other):
            return cmp(self.dt, other.dt)

    def __init__(self, cache=False):
        rrulebase.__init__(self, cache)
        self._rrule = []
        self._rdate = []
        self._exrule = []
        self._exdate = []

    def rrule(self, rrule):
        self._rrule.append(rrule)
    
    def rdate(self, rdate):
        self._rdate.append(rdate)

    def exrule(self, exrule):
        self._exrule.append(exrule)

    def exdate(self, exdate):
        self._exdate.append(exdate)

    def _iter(self):
        rlist = []
        self._rdate.sort()
        self._genitem(rlist, iter(self._rdate).next)
        for gen in [iter(x).next for x in self._rrule]:
            self._genitem(rlist, gen)
        heapq.heapify(rlist)
        exlist = []
        self._exdate.sort()
        self._genitem(exlist, iter(self._exdate).next)
        for gen in [iter(x).next for x in self._exrule]:
            self._genitem(exlist, gen)
        heapq.heapify(exlist)
        lastdt = None
        total = 0
        while rlist:
            ritem = rlist[0]
            if not lastdt or lastdt != ritem.dt:
                while exlist and exlist[0] < ritem:
                    exitem = exlist[0]
                    exitem.next()
                    if exlist and exlist[0] is exitem:
                        heapq.heapreplace(exlist, exitem)
                if not exlist or ritem != exlist[0]:
                    total += 1
                    yield ritem.dt
                lastdt = ritem.dt
            ritem.next()
            if rlist and rlist[0] is ritem:
                heapq.heapreplace(rlist, ritem)
        self._len = total

class _rrulestr:

    _freq_map = {"YEARLY": YEARLY,
                 "MONTHLY": MONTHLY,
                 "WEEKLY": WEEKLY,
                 "DAILY": DAILY,
                 "HOURLY": HOURLY,
                 "MINUTELY": MINUTELY,
                 "SECONDLY": SECONDLY}

    _weekday_map = {"MO":0,"TU":1,"WE":2,"TH":3,"FR":4,"SA":5,"SU":6}

    def _handle_int(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = int(value)

    def _handle_int_list(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = [int(x) for x in value.split(',')]

    _handle_INTERVAL   = _handle_int
    _handle_COUNT      = _handle_int
    _handle_BYSETPOS   = _handle_int_list
    _handle_BYMONTH    = _handle_int_list
    _handle_BYMONTHDAY = _handle_int_list
    _handle_BYYEARDAY  = _handle_int_list
    _handle_BYEASTER   = _handle_int_list
    _handle_BYWEEKNO   = _handle_int_list
    _handle_BYHOUR     = _handle_int_list
    _handle_BYMINUTE   = _handle_int_list
    _handle_BYSECOND   = _handle_int_list

    def _handle_FREQ(self, rrkwargs, name, value, **kwargs):
        rrkwargs["freq"] = self._freq_map[value]

    def _handle_UNTIL(self, rrkwargs, name, value, **kwargs):
        global parser
        if not parser:
            from dateutil import parser
        try:
            rrkwargs["until"] = parser.parse(value,
                                           ignoretz=kwargs.get("ignoretz"),
                                           tzinfos=kwargs.get("tzinfos"))
        except ValueError:
            raise ValueError, "invalid until date"

    def _handle_WKST(self, rrkwargs, name, value, **kwargs):
        rrkwargs["wkst"] = self._weekday_map[value]

    def _handle_BYWEEKDAY(self, rrkwargs, name, value, **kwarsg):
        l = []
        for wday in value.split(','):
            for i in range(len(wday)):
                if wday[i] not in '+-0123456789':
                    break
            n = wday[:i] or None
            w = wday[i:]
            if n: n = int(n)
            l.append(weekdays[self._weekday_map[w]](n))
        rrkwargs["byweekday"] = l

    _handle_BYDAY = _handle_BYWEEKDAY

    def _parse_rfc_rrule(self, line,
                         dtstart=None,
                         cache=False,
                         ignoretz=False,
                         tzinfos=None):
        if line.find(':') != -1:
            name, value = line.split(':')
            if name != "RRULE":
                raise ValueError, "unknown parameter name"
        else:
            value = line
        rrkwargs = {}
        for pair in value.split(';'):
            name, value = pair.split('=')
            name = name.upper()
            value = value.upper()
            try:
                getattr(self, "_handle_"+name)(rrkwargs, name, value,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos)
            except AttributeError:
                raise ValueError, "unknown parameter '%s'" % name
            except (KeyError, ValueError):
                raise ValueError, "invalid '%s': %s" % (name, value)
        return rrule(dtstart=dtstart, cache=cache, **rrkwargs)

    def _parse_rfc(self, s,
                   dtstart=None,
                   cache=False,
                   unfold=False,
                   forceset=False,
                   compatible=False,
                   ignoretz=False,
                   tzinfos=None):
        global parser
        if compatible:
            forceset = True
            unfold = True
        s = s.upper()
        if not s.strip():
            raise ValueError, "empty string"
        if unfold:
            lines = s.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                if not line:
                    del lines[i]
                elif i > 0 and line[0] in (" ", "\t"):
                    lines[i-1] += line[1:]
                    del lines[i]
                else:
                    i += 1
        else:
            lines = s.split()
        if (not forceset and len(lines) == 1 and
            (s.find(':') == -1 or s.startswith('RRULE:'))):
            return self._parse_rfc_rrule(lines[0], cache=cache,
                                         dtstart=dtstart, ignoretz=ignoretz,
                                         tzinfos=tzinfos)
        else:
            rrulevals = []
            rdatevals = []
            exrulevals = []
            exdatevals = []
            for line in lines:
                if not line:
                    continue
                if line.find(':') == -1:
                    name = "RRULE"
                    value = line
                else:
                    name, value = line.split(':', 1)
                parms = name.split(';')
                if not parms:
                    raise ValueError, "empty property name"
                name = parms[0]
                parms = parms[1:]
                if name == "RRULE":
                    for parm in parms:
                        raise ValueError, "unsupported RRULE parm: "+parm
                    rrulevals.append(value)
                elif name == "RDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError, "unsupported RDATE parm: "+parm
                    rdatevals.append(value)
                elif name == "EXRULE":
                    for parm in parms:
                        raise ValueError, "unsupported EXRULE parm: "+parm
                    exrulevals.append(value)
                elif name == "EXDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError, "unsupported RDATE parm: "+parm
                    exdatevals.append(value)
                elif name == "DTSTART":
                    for parm in parms:
                        raise ValueError, "unsupported DTSTART parm: "+parm
                    if not parser:
                        from dateutil import parser
                    dtstart = parser.parse(value, ignoretz=ignoretz,
                                           tzinfos=tzinfos)
                elif name.upper().startswith('X-'):
                    # Ignore experimental properties.
                    pass
                else:
                    raise ValueError, "unsupported property: "+name
            if (forceset or len(rrulevals) > 1 or
                rdatevals or exrulevals or exdatevals):
                if not parser and (rdatevals or exdatevals):
                    from dateutil import parser
                set = rruleset(cache=cache)
                for value in rrulevals:
                    set.rrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                    ignoretz=ignoretz,
                                                    tzinfos=tzinfos))
                for value in rdatevals:
                    for datestr in value.split(','):
                        set.rdate(parser.parse(datestr,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos))
                for value in exrulevals:
                    set.exrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                     ignoretz=ignoretz,
                                                     tzinfos=tzinfos))
                for value in exdatevals:
                    for datestr in value.split(','):
                        set.exdate(parser.parse(datestr,
                                                ignoretz=ignoretz,
                                                tzinfos=tzinfos))
                if compatible and dtstart:
                    set.rdate(dtstart)
                return set
            else:
                return self._parse_rfc_rrule(rrulevals[0],
                                             dtstart=dtstart,
                                             cache=cache,
                                             ignoretz=ignoretz,
                                             tzinfos=tzinfos)

    def __call__(self, s, **kwargs):
        return self._parse_rfc(s, **kwargs)

rrulestr = _rrulestr()

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = tz
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import struct
import time
import sys
import os

relativedelta = None
parser = None
rrule = None

__all__ = ["tzutc", "tzoffset", "tzlocal", "tzfile", "tzrange",
           "tzstr", "tzical", "tzwin", "tzwinlocal", "gettz"]

try:
    from dateutil.tzwin import tzwin, tzwinlocal
except (ImportError, OSError):
    tzwin, tzwinlocal = None, None

ZERO = datetime.timedelta(0)
EPOCHORDINAL = datetime.datetime.utcfromtimestamp(0).toordinal()

class tzutc(datetime.tzinfo):

    def utcoffset(self, dt):
        return ZERO
     
    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def __eq__(self, other):
        return (isinstance(other, tzutc) or
                (isinstance(other, tzoffset) and other._offset == ZERO))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__

class tzoffset(datetime.tzinfo):

    def __init__(self, name, offset):
        self._name = name
        self._offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt):
        return self._offset

    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        return self._name

    def __eq__(self, other):
        return (isinstance(other, tzoffset) and
                self._offset == other._offset)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               `self._name`,
                               self._offset.days*86400+self._offset.seconds)

    __reduce__ = object.__reduce__

class tzlocal(datetime.tzinfo):

    _std_offset = datetime.timedelta(seconds=-time.timezone)
    if time.daylight:
        _dst_offset = datetime.timedelta(seconds=-time.altzone)
    else:
        _dst_offset = _std_offset

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if self._isdst(dt):
            return self._dst_offset-self._std_offset
        else:
            return ZERO

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        # We can't use mktime here. It is unstable when deciding if
        # the hour near to a change is DST or not.
        # 
        # timestamp = time.mktime((dt.year, dt.month, dt.day, dt.hour,
        #                         dt.minute, dt.second, dt.weekday(), 0, -1))
        # return time.localtime(timestamp).tm_isdst
        #
        # The code above yields the following result:
        #
        #>>> import tz, datetime
        #>>> t = tz.tzlocal()
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRDT'
        #>>> datetime.datetime(2003,2,16,0,tzinfo=t).tzname()
        #'BRST'
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRST'
        #>>> datetime.datetime(2003,2,15,22,tzinfo=t).tzname()
        #'BRDT'
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRDT'
        #
        # Here is a more stable implementation:
        #
        timestamp = ((dt.toordinal() - EPOCHORDINAL) * 86400
                     + dt.hour * 3600
                     + dt.minute * 60
                     + dt.second)
        return time.localtime(timestamp+time.timezone).tm_isdst

    def __eq__(self, other):
        if not isinstance(other, tzlocal):
            return False
        return (self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset)
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__

class _ttinfo(object):
    __slots__ = ["offset", "delta", "isdst", "abbr", "isstd", "isgmt"]

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def __repr__(self):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, `value`))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

    def __eq__(self, other):
        if not isinstance(other, _ttinfo):
            return False
        return (self.offset == other.offset and
                self.delta == other.delta and
                self.isdst == other.isdst and
                self.abbr == other.abbr and
                self.isstd == other.isstd and
                self.isgmt == other.isgmt)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getstate__(self):
        state = {}
        for name in self.__slots__:
            state[name] = getattr(self, name, None)
        return state

    def __setstate__(self, state):
        for name in self.__slots__:
            if name in state:
                setattr(self, name, state[name])

class tzfile(datetime.tzinfo):

    # http://www.twinsun.com/tz/tz-link.htm
    # ftp://elsie.nci.nih.gov/pub/tz*.tar.gz
    
    def __init__(self, fileobj):
        if isinstance(fileobj, basestring):
            self._filename = fileobj
            fileobj = open(fileobj)
        elif hasattr(fileobj, "name"):
            self._filename = fileobj.name
        else:
            self._filename = `fileobj`

        # From tzfile(5):
        #
        # The time zone information files used by tzset(3)
        # begin with the magic characters "TZif" to identify
        # them as time zone information files, followed by
        # sixteen bytes reserved for future use, followed by
        # six four-byte values of type long, written in a
        # ``standard'' byte order (the high-order  byte
        # of the value is written first).

        if fileobj.read(4) != "TZif":
            raise ValueError, "magic not found"

        fileobj.read(16)

        (
         # The number of UTC/local indicators stored in the file.
         ttisgmtcnt,

         # The number of standard/wall indicators stored in the file.
         ttisstdcnt,
         
         # The number of leap seconds for which data is
         # stored in the file.
         leapcnt,

         # The number of "transition times" for which data
         # is stored in the file.
         timecnt,

         # The number of "local time types" for which data
         # is stored in the file (must not be zero).
         typecnt,

         # The  number  of  characters  of "time zone
         # abbreviation strings" stored in the file.
         charcnt,

        ) = struct.unpack(">6l", fileobj.read(24))

        # The above header is followed by tzh_timecnt four-byte
        # values  of  type long,  sorted  in ascending order.
        # These values are written in ``standard'' byte order.
        # Each is used as a transition time (as  returned  by
        # time(2)) at which the rules for computing local time
        # change.

        if timecnt:
            self._trans_list = struct.unpack(">%dl" % timecnt,
                                             fileobj.read(timecnt*4))
        else:
            self._trans_list = []

        # Next come tzh_timecnt one-byte values of type unsigned
        # char; each one tells which of the different types of
        # ``local time'' types described in the file is associated
        # with the same-indexed transition time. These values
        # serve as indices into an array of ttinfo structures that
        # appears next in the file.
        
        if timecnt:
            self._trans_idx = struct.unpack(">%dB" % timecnt,
                                            fileobj.read(timecnt))
        else:
            self._trans_idx = []
        
        # Each ttinfo structure is written as a four-byte value
        # for tt_gmtoff  of  type long,  in  a  standard  byte
        # order, followed  by a one-byte value for tt_isdst
        # and a one-byte  value  for  tt_abbrind.   In  each
        # structure, tt_gmtoff  gives  the  number  of
        # seconds to be added to UTC, tt_isdst tells whether
        # tm_isdst should be set by  localtime(3),  and
        # tt_abbrind serves  as an index into the array of
        # time zone abbreviation characters that follow the
        # ttinfo structure(s) in the file.

        ttinfo = []

        for i in range(typecnt):
            ttinfo.append(struct.unpack(">lbb", fileobj.read(6)))

        abbr = fileobj.read(charcnt)

        # Then there are tzh_leapcnt pairs of four-byte
        # values, written in  standard byte  order;  the
        # first  value  of  each pair gives the time (as
        # returned by time(2)) at which a leap second
        # occurs;  the  second  gives the  total  number of
        # leap seconds to be applied after the given time.
        # The pairs of values are sorted in ascending order
        # by time.

        # Not used, for now
        if leapcnt:
            leap = struct.unpack(">%dl" % (leapcnt*2),
                                 fileobj.read(leapcnt*8))

        # Then there are tzh_ttisstdcnt standard/wall
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as standard
        # time or wall clock time, and are used when
        # a time zone file is used in handling POSIX-style
        # time zone environment variables.

        if ttisstdcnt:
            isstd = struct.unpack(">%db" % ttisstdcnt,
                                  fileobj.read(ttisstdcnt))

        # Finally, there are tzh_ttisgmtcnt UTC/local
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as UTC or
        # local time, and are used when a time zone file
        # is used in handling POSIX-style time zone envi-
        # ronment variables.

        if ttisgmtcnt:
            isgmt = struct.unpack(">%db" % ttisgmtcnt,
                                  fileobj.read(ttisgmtcnt))

        # ** Everything has been read **

        # Build ttinfo list
        self._ttinfo_list = []
        for i in range(typecnt):
            gmtoff, isdst, abbrind =  ttinfo[i]
            # Round to full-minutes if that's not the case. Python's
            # datetime doesn't accept sub-minute timezones. Check
            # http://python.org/sf/1447945 for some information.
            gmtoff = (gmtoff+30)//60*60
            tti = _ttinfo()
            tti.offset = gmtoff
            tti.delta = datetime.timedelta(seconds=gmtoff)
            tti.isdst = isdst
            tti.abbr = abbr[abbrind:abbr.find('\x00', abbrind)]
            tti.isstd = (ttisstdcnt > i and isstd[i] != 0)
            tti.isgmt = (ttisgmtcnt > i and isgmt[i] != 0)
            self._ttinfo_list.append(tti)

        # Replace ttinfo indexes for ttinfo objects.
        trans_idx = []
        for idx in self._trans_idx:
            trans_idx.append(self._ttinfo_list[idx])
        self._trans_idx = tuple(trans_idx)

        # Set standard, dst, and before ttinfos. before will be
        # used when a given time is before any transitions,
        # and will be set to the first non-dst ttinfo, or to
        # the first dst, if all of them are dst.
        self._ttinfo_std = None
        self._ttinfo_dst = None
        self._ttinfo_before = None
        if self._ttinfo_list:
            if not self._trans_list:
                self._ttinfo_std = self._ttinfo_first = self._ttinfo_list[0]
            else:
                for i in range(timecnt-1,-1,-1):
                    tti = self._trans_idx[i]
                    if not self._ttinfo_std and not tti.isdst:
                        self._ttinfo_std = tti
                    elif not self._ttinfo_dst and tti.isdst:
                        self._ttinfo_dst = tti
                    if self._ttinfo_std and self._ttinfo_dst:
                        break
                else:
                    if self._ttinfo_dst and not self._ttinfo_std:
                        self._ttinfo_std = self._ttinfo_dst

                for tti in self._ttinfo_list:
                    if not tti.isdst:
                        self._ttinfo_before = tti
                        break
                else:
                    self._ttinfo_before = self._ttinfo_list[0]

        # Now fix transition times to become relative to wall time.
        #
        # I'm not sure about this. In my tests, the tz source file
        # is setup to wall time, and in the binary file isstd and
        # isgmt are off, so it should be in wall time. OTOH, it's
        # always in gmt time. Let me know if you have comments
        # about this.
        laststdoffset = 0
        self._trans_list = list(self._trans_list)
        for i in range(len(self._trans_list)):
            tti = self._trans_idx[i]
            if not tti.isdst:
                # This is std time.
                self._trans_list[i] += tti.offset
                laststdoffset = tti.offset
            else:
                # This is dst time. Convert to std.
                self._trans_list[i] += laststdoffset
        self._trans_list = tuple(self._trans_list)

    def _find_ttinfo(self, dt, laststd=0):
        timestamp = ((dt.toordinal() - EPOCHORDINAL) * 86400
                     + dt.hour * 3600
                     + dt.minute * 60
                     + dt.second)
        idx = 0
        for trans in self._trans_list:
            if timestamp < trans:
                break
            idx += 1
        else:
            return self._ttinfo_std
        if idx == 0:
            return self._ttinfo_before
        if laststd:
            while idx > 0:
                tti = self._trans_idx[idx-1]
                if not tti.isdst:
                    return tti
                idx -= 1
            else:
                return self._ttinfo_std
        else:
            return self._trans_idx[idx-1]

    def utcoffset(self, dt):
        if not self._ttinfo_std:
            return ZERO
        return self._find_ttinfo(dt).delta

    def dst(self, dt):
        if not self._ttinfo_dst:
            return ZERO
        tti = self._find_ttinfo(dt)
        if not tti.isdst:
            return ZERO

        # The documentation says that utcoffset()-dst() must
        # be constant for every dt.
        return tti.delta-self._find_ttinfo(dt, laststd=1).delta

        # An alternative for that would be:
        #
        # return self._ttinfo_dst.offset-self._ttinfo_std.offset
        #
        # However, this class stores historical changes in the
        # dst offset, so I belive that this wouldn't be the right
        # way to implement this.
        
    def tzname(self, dt):
        if not self._ttinfo_std:
            return None
        return self._find_ttinfo(dt).abbr

    def __eq__(self, other):
        if not isinstance(other, tzfile):
            return False
        return (self._trans_list == other._trans_list and
                self._trans_idx == other._trans_idx and
                self._ttinfo_list == other._ttinfo_list)

    def __ne__(self, other):
        return not self.__eq__(other)


    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self._filename`)

    def __reduce__(self):
        if not os.path.isfile(self._filename):
            raise ValueError, "Unpickable %s class" % self.__class__.__name__
        return (self.__class__, (self._filename,))

class tzrange(datetime.tzinfo):

    def __init__(self, stdabbr, stdoffset=None,
                 dstabbr=None, dstoffset=None,
                 start=None, end=None):
        global relativedelta
        if not relativedelta:
            from dateutil import relativedelta
        self._std_abbr = stdabbr
        self._dst_abbr = dstabbr
        if stdoffset is not None:
            self._std_offset = datetime.timedelta(seconds=stdoffset)
        else:
            self._std_offset = ZERO
        if dstoffset is not None:
            self._dst_offset = datetime.timedelta(seconds=dstoffset)
        elif dstabbr and stdoffset is not None:
            self._dst_offset = self._std_offset+datetime.timedelta(hours=+1)
        else:
            self._dst_offset = ZERO
        if dstabbr and start is None:
            self._start_delta = relativedelta.relativedelta(
                    hours=+2, month=4, day=1, weekday=relativedelta.SU(+1))
        else:
            self._start_delta = start
        if dstabbr and end is None:
            self._end_delta = relativedelta.relativedelta(
                    hours=+1, month=10, day=31, weekday=relativedelta.SU(-1))
        else:
            self._end_delta = end

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if self._isdst(dt):
            return self._dst_offset-self._std_offset
        else:
            return ZERO

    def tzname(self, dt):
        if self._isdst(dt):
            return self._dst_abbr
        else:
            return self._std_abbr

    def _isdst(self, dt):
        if not self._start_delta:
            return False
        year = datetime.datetime(dt.year,1,1)
        start = year+self._start_delta
        end = year+self._end_delta
        dt = dt.replace(tzinfo=None)
        if start < end:
            return dt >= start and dt < end
        else:
            return dt >= start or dt < end

    def __eq__(self, other):
        if not isinstance(other, tzrange):
            return False
        return (self._std_abbr == other._std_abbr and
                self._dst_abbr == other._dst_abbr and
                self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset and
                self._start_delta == other._start_delta and
                self._end_delta == other._end_delta)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(...)" % self.__class__.__name__

    __reduce__ = object.__reduce__

class tzstr(tzrange):
    
    def __init__(self, s):
        global parser
        if not parser:
            from dateutil import parser
        self._s = s

        res = parser._parsetz(s)
        if res is None:
            raise ValueError, "unknown string format"

        # Here we break the compatibility with the TZ variable handling.
        # GMT-3 actually *means* the timezone -3.
        if res.stdabbr in ("GMT", "UTC"):
            res.stdoffset *= -1

        # We must initialize it first, since _delta() needs
        # _std_offset and _dst_offset set. Use False in start/end
        # to avoid building it two times.
        tzrange.__init__(self, res.stdabbr, res.stdoffset,
                         res.dstabbr, res.dstoffset,
                         start=False, end=False)

        if not res.dstabbr:
            self._start_delta = None
            self._end_delta = None
        else:
            self._start_delta = self._delta(res.start)
            if self._start_delta:
                self._end_delta = self._delta(res.end, isend=1)

    def _delta(self, x, isend=0):
        kwargs = {}
        if x.month is not None:
            kwargs["month"] = x.month
            if x.weekday is not None:
                kwargs["weekday"] = relativedelta.weekday(x.weekday, x.week)
                if x.week > 0:
                    kwargs["day"] = 1
                else:
                    kwargs["day"] = 31
            elif x.day:
                kwargs["day"] = x.day
        elif x.yday is not None:
            kwargs["yearday"] = x.yday
        elif x.jyday is not None:
            kwargs["nlyearday"] = x.jyday
        if not kwargs:
            # Default is to start on first sunday of april, and end
            # on last sunday of october.
            if not isend:
                kwargs["month"] = 4
                kwargs["day"] = 1
                kwargs["weekday"] = relativedelta.SU(+1)
            else:
                kwargs["month"] = 10
                kwargs["day"] = 31
                kwargs["weekday"] = relativedelta.SU(-1)
        if x.time is not None:
            kwargs["seconds"] = x.time
        else:
            # Default is 2AM.
            kwargs["seconds"] = 7200
        if isend:
            # Convert to standard time, to follow the documented way
            # of working with the extra hour. See the documentation
            # of the tzinfo class.
            delta = self._dst_offset-self._std_offset
            kwargs["seconds"] -= delta.seconds+delta.days*86400
        return relativedelta.relativedelta(**kwargs)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self._s`)

class _tzicalvtzcomp:
    def __init__(self, tzoffsetfrom, tzoffsetto, isdst,
                       tzname=None, rrule=None):
        self.tzoffsetfrom = datetime.timedelta(seconds=tzoffsetfrom)
        self.tzoffsetto = datetime.timedelta(seconds=tzoffsetto)
        self.tzoffsetdiff = self.tzoffsetto-self.tzoffsetfrom
        self.isdst = isdst
        self.tzname = tzname
        self.rrule = rrule

class _tzicalvtz(datetime.tzinfo):
    def __init__(self, tzid, comps=[]):
        self._tzid = tzid
        self._comps = comps
        self._cachedate = []
        self._cachecomp = []

    def _find_comp(self, dt):
        if len(self._comps) == 1:
            return self._comps[0]
        dt = dt.replace(tzinfo=None)
        try:
            return self._cachecomp[self._cachedate.index(dt)]
        except ValueError:
            pass
        lastcomp = None
        lastcompdt = None
        for comp in self._comps:
            if not comp.isdst:
                # Handle the extra hour in DST -> STD
                compdt = comp.rrule.before(dt-comp.tzoffsetdiff, inc=True)
            else:
                compdt = comp.rrule.before(dt, inc=True)
            if compdt and (not lastcompdt or lastcompdt < compdt):
                lastcompdt = compdt
                lastcomp = comp
        if not lastcomp:
            # RFC says nothing about what to do when a given
            # time is before the first onset date. We'll look for the
            # first standard component, or the first component, if
            # none is found.
            for comp in self._comps:
                if not comp.isdst:
                    lastcomp = comp
                    break
            else:
                lastcomp = comp[0]
        self._cachedate.insert(0, dt)
        self._cachecomp.insert(0, lastcomp)
        if len(self._cachedate) > 10:
            self._cachedate.pop()
            self._cachecomp.pop()
        return lastcomp

    def utcoffset(self, dt):
        return self._find_comp(dt).tzoffsetto

    def dst(self, dt):
        comp = self._find_comp(dt)
        if comp.isdst:
            return comp.tzoffsetdiff
        else:
            return ZERO

    def tzname(self, dt):
        return self._find_comp(dt).tzname

    def __repr__(self):
        return "<tzicalvtz %s>" % `self._tzid`

    __reduce__ = object.__reduce__

class tzical:
    def __init__(self, fileobj):
        global rrule
        if not rrule:
            from dateutil import rrule

        if isinstance(fileobj, basestring):
            self._s = fileobj
            fileobj = open(fileobj)
        elif hasattr(fileobj, "name"):
            self._s = fileobj.name
        else:
            self._s = `fileobj`

        self._vtz = {}

        self._parse_rfc(fileobj.read())

    def keys(self):
        return self._vtz.keys()

    def get(self, tzid=None):
        if tzid is None:
            keys = self._vtz.keys()
            if len(keys) == 0:
                raise ValueError, "no timezones defined"
            elif len(keys) > 1:
                raise ValueError, "more than one timezone available"
            tzid = keys[0]
        return self._vtz.get(tzid)

    def _parse_offset(self, s):
        s = s.strip()
        if not s:
            raise ValueError, "empty offset"
        if s[0] in ('+', '-'):
            signal = (-1,+1)[s[0]=='+']
            s = s[1:]
        else:
            signal = +1
        if len(s) == 4:
            return (int(s[:2])*3600+int(s[2:])*60)*signal
        elif len(s) == 6:
            return (int(s[:2])*3600+int(s[2:4])*60+int(s[4:]))*signal
        else:
            raise ValueError, "invalid offset: "+s

    def _parse_rfc(self, s):
        lines = s.splitlines()
        if not lines:
            raise ValueError, "empty string"

        # Unfold
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line:
                del lines[i]
            elif i > 0 and line[0] in (" ", "\t"):
                lines[i-1] += line[1:]
                del lines[i]
            else:
                i += 1

        tzid = None
        comps = []
        invtz = False
        comptype = None
        for line in lines:
            if not line:
                continue
            name, value = line.split(':', 1)
            parms = name.split(';')
            if not parms:
                raise ValueError, "empty property name"
            name = parms[0].upper()
            parms = parms[1:]
            if invtz:
                if name == "BEGIN":
                    if value in ("STANDARD", "DAYLIGHT"):
                        # Process component
                        pass
                    else:
                        raise ValueError, "unknown component: "+value
                    comptype = value
                    founddtstart = False
                    tzoffsetfrom = None
                    tzoffsetto = None
                    rrulelines = []
                    tzname = None
                elif name == "END":
                    if value == "VTIMEZONE":
                        if comptype:
                            raise ValueError, \
                                  "component not closed: "+comptype
                        if not tzid:
                            raise ValueError, \
                                  "mandatory TZID not found"
                        if not comps:
                            raise ValueError, \
                                  "at least one component is needed"
                        # Process vtimezone
                        self._vtz[tzid] = _tzicalvtz(tzid, comps)
                        invtz = False
                    elif value == comptype:
                        if not founddtstart:
                            raise ValueError, \
                                  "mandatory DTSTART not found"
                        if tzoffsetfrom is None:
                            raise ValueError, \
                                  "mandatory TZOFFSETFROM not found"
                        if tzoffsetto is None:
                            raise ValueError, \
                                  "mandatory TZOFFSETFROM not found"
                        # Process component
                        rr = None
                        if rrulelines:
                            rr = rrule.rrulestr("\n".join(rrulelines),
                                                compatible=True,
                                                ignoretz=True,
                                                cache=True)
                        comp = _tzicalvtzcomp(tzoffsetfrom, tzoffsetto,
                                              (comptype == "DAYLIGHT"),
                                              tzname, rr)
                        comps.append(comp)
                        comptype = None
                    else:
                        raise ValueError, \
                              "invalid component end: "+value
                elif comptype:
                    if name == "DTSTART":
                        rrulelines.append(line)
                        founddtstart = True
                    elif name in ("RRULE", "RDATE", "EXRULE", "EXDATE"):
                        rrulelines.append(line)
                    elif name == "TZOFFSETFROM":
                        if parms:
                            raise ValueError, \
                                  "unsupported %s parm: %s "%(name, parms[0])
                        tzoffsetfrom = self._parse_offset(value)
                    elif name == "TZOFFSETTO":
                        if parms:
                            raise ValueError, \
                                  "unsupported TZOFFSETTO parm: "+parms[0]
                        tzoffsetto = self._parse_offset(value)
                    elif name == "TZNAME":
                        if parms:
                            raise ValueError, \
                                  "unsupported TZNAME parm: "+parms[0]
                        tzname = value
                    elif name == "COMMENT":
                        pass
                    elif name.upper().startswith('X-'):
                        # Ignore experimental properties.
                        pass
                    else:
                        raise ValueError, "unsupported property: "+name
                else:
                    if name == "TZID":
                        for p in parms:
                            if not p.upper().startswith('X-'):
                                raise ValueError, \
                                    "unsupported TZID parm: "+p
                        tzid = value
                    elif name in ("TZURL", "LAST-MODIFIED", "COMMENT"):
                        pass
                    elif name.upper().startswith('X-'):
                        # Ignore experimental properties.
                        pass
                    else:
                        raise ValueError, "unsupported property: "+name
            elif name == "BEGIN" and value == "VTIMEZONE":
                tzid = None
                comps = []
                invtz = True

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self._s`)

if sys.platform != "win32":
    TZFILES = ["/etc/localtime", "localtime"]
    TZPATHS = ["/usr/share/zoneinfo", "/usr/lib/zoneinfo", "/etc/zoneinfo"]
else:
    TZFILES = []
    TZPATHS = []

def gettz(name=None):
    tz = None
    if not name:
        try:
            name = os.environ["TZ"]
        except KeyError:
            pass
    if name is None or name == ":":
        for filepath in TZFILES:
            if not os.path.isabs(filepath):
                filename = filepath
                for path in TZPATHS:
                    filepath = os.path.join(path, filename)
                    if os.path.isfile(filepath):
                        break
                else:
                    continue
            if os.path.isfile(filepath):
                try:
                    tz = tzfile(filepath)
                    break
                except (IOError, OSError, ValueError):
                    pass
        else:
            tz = tzlocal()
    else:
        if name.startswith(":"):
            name = name[:-1]
        if os.path.isabs(name):
            if os.path.isfile(name):
                tz = tzfile(name)
            else:
                tz = None
        else:
            for path in TZPATHS:
                filepath = os.path.join(path, name)
                if not os.path.isfile(filepath):
                    filepath = filepath.replace(' ','_')
                    if not os.path.isfile(filepath):
                        continue
                try:
                    tz = tzfile(filepath)
                    break
                except (IOError, OSError, ValueError):
                    pass
            else:
                tz = None
                if tzwin:
                    try:
                        tz = tzwin(name)
                    except OSError:
                        pass
                if not tz:
                    from dateutil.zoneinfo import gettz
                    tz = gettz(name)
                if not tz:
                    for c in name:
                        # name must have at least one offset to be a tzstr
                        if c in "0123456789":
                            try:
                                tz = tzstr(name)
                            except ValueError:
                                pass
                            break
                    else:
                        if name in ("GMT", "UTC"):
                            tz = tzutc()
                        elif name in time.tzname:
                            tz = tzlocal()
    return tz

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = tzwin
# This code was originally contributed by Jeffrey Harris.
import datetime
import struct
import _winreg

__author__ = "Jeffrey Harris & Gustavo Niemeyer <gustavo@niemeyer.net>"

__all__ = ["tzwin", "tzwinlocal"]

ONEWEEK = datetime.timedelta(7)

TZKEYNAMENT = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"
TZKEYNAME9X = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Time Zones"
TZLOCALKEYNAME = r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation"

def _settzkeyname():
    global TZKEYNAME
    handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
    try:
        _winreg.OpenKey(handle, TZKEYNAMENT).Close()
        TZKEYNAME = TZKEYNAMENT
    except WindowsError:
        TZKEYNAME = TZKEYNAME9X
    handle.Close()

_settzkeyname()

class tzwinbase(datetime.tzinfo):
    """tzinfo class based on win32's timezones available in the registry."""

    def utcoffset(self, dt):
        if self._isdst(dt):
            return datetime.timedelta(minutes=self._dstoffset)
        else:
            return datetime.timedelta(minutes=self._stdoffset)

    def dst(self, dt):
        if self._isdst(dt):
            minutes = self._dstoffset - self._stdoffset
            return datetime.timedelta(minutes=minutes)
        else:
            return datetime.timedelta(0)
        
    def tzname(self, dt):
        if self._isdst(dt):
            return self._dstname
        else:
            return self._stdname

    def list():
        """Return a list of all time zones known to the system."""
        handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        tzkey = _winreg.OpenKey(handle, TZKEYNAME)
        result = [_winreg.EnumKey(tzkey, i)
                  for i in range(_winreg.QueryInfoKey(tzkey)[0])]
        tzkey.Close()
        handle.Close()
        return result
    list = staticmethod(list)

    def display(self):
        return self._display
    
    def _isdst(self, dt):
        dston = picknthweekday(dt.year, self._dstmonth, self._dstdayofweek,
                               self._dsthour, self._dstminute,
                               self._dstweeknumber)
        dstoff = picknthweekday(dt.year, self._stdmonth, self._stddayofweek,
                                self._stdhour, self._stdminute,
                                self._stdweeknumber)
        if dston < dstoff:
            return dston <= dt.replace(tzinfo=None) < dstoff
        else:
            return not dstoff <= dt.replace(tzinfo=None) < dston


class tzwin(tzwinbase):

    def __init__(self, name):
        self._name = name

        handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        tzkey = _winreg.OpenKey(handle, "%s\%s" % (TZKEYNAME, name))
        keydict = valuestodict(tzkey)
        tzkey.Close()
        handle.Close()

        self._stdname = keydict["Std"].encode("iso-8859-1")
        self._dstname = keydict["Dlt"].encode("iso-8859-1")

        self._display = keydict["Display"]
        
        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=3l16h", keydict["TZI"])
        self._stdoffset = -tup[0]-tup[1]         # Bias + StandardBias * -1
        self._dstoffset = self._stdoffset-tup[2] # + DaylightBias * -1
        
        (self._stdmonth,
         self._stddayofweek,  # Sunday = 0
         self._stdweeknumber, # Last = 5
         self._stdhour,
         self._stdminute) = tup[4:9]

        (self._dstmonth,
         self._dstdayofweek,  # Sunday = 0
         self._dstweeknumber, # Last = 5
         self._dsthour,
         self._dstminute) = tup[12:17]

    def __repr__(self):
        return "tzwin(%s)" % repr(self._name)

    def __reduce__(self):
        return (self.__class__, (self._name,))


class tzwinlocal(tzwinbase):
    
    def __init__(self):

        handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)

        tzlocalkey = _winreg.OpenKey(handle, TZLOCALKEYNAME)
        keydict = valuestodict(tzlocalkey)
        tzlocalkey.Close()

        self._stdname = keydict["StandardName"].encode("iso-8859-1")
        self._dstname = keydict["DaylightName"].encode("iso-8859-1")

        try:
            tzkey = _winreg.OpenKey(handle, "%s\%s"%(TZKEYNAME, self._stdname))
            _keydict = valuestodict(tzkey)
            self._display = _keydict["Display"]
            tzkey.Close()
        except OSError:
            self._display = None

        handle.Close()
        
        self._stdoffset = -keydict["Bias"]-keydict["StandardBias"]
        self._dstoffset = self._stdoffset-keydict["DaylightBias"]


        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=8h", keydict["StandardStart"])

        (self._stdmonth,
         self._stddayofweek,  # Sunday = 0
         self._stdweeknumber, # Last = 5
         self._stdhour,
         self._stdminute) = tup[1:6]

        tup = struct.unpack("=8h", keydict["DaylightStart"])

        (self._dstmonth,
         self._dstdayofweek,  # Sunday = 0
         self._dstweeknumber, # Last = 5
         self._dsthour,
         self._dstminute) = tup[1:6]

    def __reduce__(self):
        return (self.__class__, ())

def picknthweekday(year, month, dayofweek, hour, minute, whichweek):
    """dayofweek == 0 means Sunday, whichweek 5 means last instance"""
    first = datetime.datetime(year, month, 1, hour, minute)
    weekdayone = first.replace(day=((dayofweek-first.isoweekday())%7+1))
    for n in xrange(whichweek):
        dt = weekdayone+(whichweek-n)*ONEWEEK
        if dt.month == month:
            return dt

def valuestodict(key):
    """Convert a registry key's values to a dictionary."""
    dict = {}
    size = _winreg.QueryInfoKey(key)[1]
    for i in range(size):
        data = _winreg.EnumValue(key, i)
        dict[data[0]] = data[1]
    return dict

########NEW FILE########
__FILENAME__ = example
from dateutil.relativedelta import *
from dateutil.easter import *
from dateutil.rrule import *
from dateutil.parser import *
from datetime import *
import commands
import os
now = parse(commands.getoutput("date"))
today = now.date()
year = rrule(YEARLY,bymonth=8,bymonthday=13,byweekday=FR)[0].year
rdelta = relativedelta(easter(year), today)
print "Today is:", today
print "Year with next Aug 13th on a Friday is:", year
print "How far is the Easter of that year:", rdelta
print "And the Easter of that year is:", today+rdelta

########NEW FILE########
__FILENAME__ = rrulewrapper
from rrule import *

class rrulewrapper:
    def __init__(self, freq, **kwargs):
        self._construct = kwargs.copy()
        self._construct["freq"] = freq
        self._rrule = rrule(**self._construct)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self._rrule, name)
    
    def set(self, **kwargs):
        self._construct.update(kwargs)
        self._rrule = rrule(**self._construct)

########NEW FILE########
__FILENAME__ = scheduler
"""
Copyright (c) 2003-2005  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import thread
import signal
import time

class sched:

    def __init__(self, rrule,
                 tolerance=None, last=None,
                 execute=None, args=None, kwargs=None):
        self._rrule = rrule
        if tolerance:
            self._tolerance = datetime.timedelta(seconds=tolerance)
        else:
            self._tolerance = None
        self._last = last
        self._execute = execute
        self._args = args or ()
        self._kwargs = kwargs or {}

    def last(self):
        return self._last

    def next(self, now=None):
        if not now:
            now = datetime.datetime.now()
        return self._rrule.after(now)

    def check(self, now=None, readonly=False):
        if not now:
            now = datetime.datetime.now()
        item = self._rrule.before(now, inc=True)
        if (item is None or item == self._last or
            (self._tolerance and item+self._tolerance < now)):
            return None
        if not readonly:
            self._last = item
            if self._execute:
                self._execute(*self._args, **self._kwargs)
        return item


class schedset:
    def __init__(self):
        self._scheds = []

    def add(self, sched):
        self._scheds.append(sched)

    def next(self, now=None):
        if not now:
            now = datetime.datetime.now()
        res = None
        for sched in self._scheds:
            next = sched.next(now)
            if next and (not res or next < res):
                res = next
        return res

    def check(self, now=None, readonly=False):
        if not now:
            now = datetime.datetime.now()
        res = False
        for sched in self._scheds:
            if sched.check(now, readonly):
                res = True
        return res


class schedthread:
    
    def __init__(self, sched, lock=None):
        self._sched = sched
        self._lock = lock
        self._running = False

    def running(self):
        return self._running

    def run(self):
        self._running = True
        thread.start_new_thread(self._loop, ())
        
    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            if self._lock:
                self._lock.acquire()
            now = datetime.datetime.now()
            self._sched.check(now)
            if self._lock:
                self._lock.release()
            seconds = _seconds_left(self._sched.next(now))
            if seconds is None:
                self._running = False
                break
            if self._running:
                time.sleep(seconds)


class schedalarm:
    
    def __init__(self, sched, lock=None):
        self._sched = sched
        self._lock = lock
        self._running = False

    def running(self):
        return self._running

    def run(self):
        self._running = True
        signal.signal(signal.SIGALRM, self._handler)
        self._handler(None, None)
        
    def stop(self):
        self._running = False

    def _handler(self, sig, frame):
        while self._running:
            if self._lock:
                self._lock.acquire()
            now = datetime.datetime.now()
            self._sched.check(now)
            if self._lock:
                self._lock.release()
            if self._running:
                seconds = _seconds_left(self._sched.next(now))
                if seconds:
                    signal.alarm(seconds)
                    break
                elif seconds is None:
                    self._running = False
                    break


def _seconds_left(next):
    if not next:
        return None
    now = datetime.datetime.now()
    delta = next-now
    seconds = delta.days*86400+delta.seconds
    if seconds < 0:
        seconds = 0
    return seconds


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/python
# -*- encoding: utf-8 -*-
from cStringIO import StringIO
import unittest
import calendar
import time
import base64
import os

# Add build directory to search path
if os.path.exists("build"):
	from distutils.util import get_platform
	import sys
	s = "build/lib.%s-%.3s" % (get_platform(), sys.version)
	s = os.path.join(os.getcwd(), s)
	sys.path.insert(0,s)

from dateutil.relativedelta import *
from dateutil.parser import *
from dateutil.easter import *
from dateutil.rrule import *
from dateutil.tz import *
from dateutil import zoneinfo

from datetime import *


class RelativeDeltaTest(unittest.TestCase):
    now = datetime(2003, 9, 17, 20, 54, 47, 282310)
    today = date(2003, 9, 17)

    def test28Days(self):
        start_date = datetime(2000, 1, 1)
        unit = relativedelta(days=1)
        span = 28

        end_date = start_date + unit * span
        self.assertEqual(end_date, datetime(2000, 1, 29))

    def testNextMonth(self):
        self.assertEqual(self.now+relativedelta(months=+1),
                         datetime(2003, 10, 17, 20, 54, 47, 282310))

    def testNextMonthPlusOneWeek(self):
        self.assertEqual(self.now+relativedelta(months=+1, weeks=+1),
                         datetime(2003, 10, 24, 20, 54, 47, 282310))
    def testNextMonthPlusOneWeek10am(self):
        self.assertEqual(self.today +
                         relativedelta(months=+1, weeks=+1, hour=10),
                         datetime(2003, 10, 24, 10, 0))

    def testNextMonthPlusOneWeek10amDiff(self):
        self.assertEqual(relativedelta(datetime(2003, 10, 24, 10, 0),
                                       self.today),
                         relativedelta(months=+1, days=+7, hours=+10))

    def testOneMonthBeforeOneYear(self):
        self.assertEqual(self.now+relativedelta(years=+1, months=-1),
                         datetime(2004, 8, 17, 20, 54, 47, 282310))

    def testMonthsOfDiffNumOfDays(self):
        self.assertEqual(date(2003, 1, 27)+relativedelta(months=+1),
                         date(2003, 2, 27))
        self.assertEqual(date(2003, 1, 31)+relativedelta(months=+1),
                         date(2003, 2, 28))
        self.assertEqual(date(2003, 1, 31)+relativedelta(months=+2),
                         date(2003, 3, 31))

    def testMonthsOfDiffNumOfDaysWithYears(self):
        self.assertEqual(date(2000, 2, 28)+relativedelta(years=+1),
                         date(2001, 2, 28))
        self.assertEqual(date(2000, 2, 29)+relativedelta(years=+1),
                         date(2001, 2, 28))

        self.assertEqual(date(1999, 2, 28)+relativedelta(years=+1),
                         date(2000, 2, 28))
        self.assertEqual(date(1999, 3, 1)+relativedelta(years=+1),
                         date(2000, 3, 1))
        self.assertEqual(date(1999, 3, 1)+relativedelta(years=+1),
                         date(2000, 3, 1))

        self.assertEqual(date(2001, 2, 28)+relativedelta(years=-1),
                         date(2000, 2, 28))
        self.assertEqual(date(2001, 3, 1)+relativedelta(years=-1),
                         date(2000, 3, 1))

    def testNextFriday(self):
        self.assertEqual(self.today+relativedelta(weekday=FR),
                         date(2003, 9, 19))

    def testNextFridayInt(self):
        self.assertEqual(self.today+relativedelta(weekday=calendar.FRIDAY),
                         date(2003, 9, 19))

    def testLastFridayInThisMonth(self):
        self.assertEqual(self.today+relativedelta(day=31, weekday=FR(-1)),
                         date(2003, 9, 26))

    def testNextWednesdayIsToday(self):
        self.assertEqual(self.today+relativedelta(weekday=WE),
                         date(2003, 9, 17))


    def testNextWenesdayNotToday(self):
        self.assertEqual(self.today+relativedelta(days=+1, weekday=WE),
                         date(2003, 9, 24))
        
    def test15thISOYearWeek(self):
        self.assertEqual(date(2003, 1, 1) +
                         relativedelta(day=4, weeks=+14, weekday=MO(-1)),
                         date(2003, 4, 7))

    def testMillenniumAge(self):
        self.assertEqual(relativedelta(self.now, date(2001,1,1)),
                         relativedelta(years=+2, months=+8, days=+16,
                                       hours=+20, minutes=+54, seconds=+47,
                                       microseconds=+282310))

    def testJohnAge(self):
        self.assertEqual(relativedelta(self.now,
                                       datetime(1978, 4, 5, 12, 0)),
                         relativedelta(years=+25, months=+5, days=+12,
                                       hours=+8, minutes=+54, seconds=+47,
                                       microseconds=+282310))

    def testJohnAgeWithDate(self):
        self.assertEqual(relativedelta(self.today,
                                       datetime(1978, 4, 5, 12, 0)),
                         relativedelta(years=+25, months=+5, days=+11,
                                       hours=+12))

    def testYearDay(self):
        self.assertEqual(date(2003, 1, 1)+relativedelta(yearday=260),
                         date(2003, 9, 17))
        self.assertEqual(date(2002, 1, 1)+relativedelta(yearday=260),
                         date(2002, 9, 17))
        self.assertEqual(date(2000, 1, 1)+relativedelta(yearday=260),
                         date(2000, 9, 16))
        self.assertEqual(self.today+relativedelta(yearday=261),
                         date(2003, 9, 18))

    def testYearDayBug(self):
        # Tests a problem reported by Adam Ryan.
        self.assertEqual(date(2010, 1, 1)+relativedelta(yearday=15),
                         date(2010, 1, 15))

    def testNonLeapYearDay(self):
        self.assertEqual(date(2003, 1, 1)+relativedelta(nlyearday=260),
                         date(2003, 9, 17))
        self.assertEqual(date(2002, 1, 1)+relativedelta(nlyearday=260),
                         date(2002, 9, 17))
        self.assertEqual(date(2000, 1, 1)+relativedelta(nlyearday=260),
                         date(2000, 9, 17))
        self.assertEqual(self.today+relativedelta(yearday=261),
                         date(2003, 9, 18))

class RRuleTest(unittest.TestCase):

    def testYearly(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testYearlyInterval(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0),
                          datetime(2001, 9, 2, 9, 0)])

    def testYearlyIntervalLarge(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              interval=100,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(2097, 9, 2, 9, 0),
                          datetime(2197, 9, 2, 9, 0)])

    def testYearlyByMonth(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 2, 9, 0),
                          datetime(1998, 3, 2, 9, 0),
                          datetime(1999, 1, 2, 9, 0)])

    def testYearlyByMonthDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 10, 1, 9, 0),
                          datetime(1997, 10, 3, 9, 0)])

    def testYearlyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 9, 0),
                          datetime(1998, 1, 7, 9, 0),
                          datetime(1998, 3, 5, 9, 0)])

    def testYearlyByWeekDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testYearlyByNWeekDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 25, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 12, 31, 9, 0)])

    def testYearlyByNWeekDayLarge(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekday=(TU(3),TH(-3)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 11, 9, 0),
                          datetime(1998, 1, 20, 9, 0),
                          datetime(1998, 12, 17, 9, 0)])

    def testYearlyByMonthAndWeekDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 8, 9, 0)])

    def testYearlyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 29, 9, 0),
                          datetime(1998, 3, 3, 9, 0)])

    def testYearlyByMonthAndNWeekDayLarge(self):
        # This is interesting because the TH(-3) ends up before
        # the TU(3).
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(3),TH(-3)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 15, 9, 0),
                          datetime(1998, 1, 20, 9, 0),
                          datetime(1998, 3, 12, 9, 0)])

    def testYearlyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 2, 3, 9, 0),
                          datetime(1998, 3, 3, 9, 0)])

    def testYearlyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 3, 3, 9, 0),
                          datetime(2001, 3, 1, 9, 0)])

    def testYearlyByYearDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testYearlyByYearDayNeg(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testYearlyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 4, 10, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testYearlyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 4, 10, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testYearlyByWeekNo(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 9, 0),
                          datetime(1998, 5, 12, 9, 0),
                          datetime(1998, 5, 13, 9, 0)])

    def testYearlyByWeekNoAndWeekDay(self):
        # That's a nice one. The first days of week number one
        # may be in the last year.
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 9, 0),
                          datetime(1999, 1, 4, 9, 0),
                          datetime(2000, 1, 3, 9, 0)])

    def testYearlyByWeekNoAndWeekDayLarge(self):
        # Another nice test. The last days of week number 52/53
        # may be in the next year.
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1998, 12, 27, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testYearlyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1999, 1, 3, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testYearlyByEaster(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 9, 0),
                          datetime(1999, 4, 4, 9, 0),
                          datetime(2000, 4, 23, 9, 0)])

    def testYearlyByEasterPos(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 9, 0),
                          datetime(1999, 4, 5, 9, 0),
                          datetime(2000, 4, 24, 9, 0)])

    def testYearlyByEasterNeg(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 9, 0),
                          datetime(1999, 4, 3, 9, 0),
                          datetime(2000, 4, 22, 9, 0)])

    def testYearlyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 9, 0),
                          datetime(2004, 12, 27, 9, 0),
                          datetime(2009, 12, 28, 9, 0)])

    def testYearlyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 9, 0),
                          datetime(2004, 12, 27, 9, 0),
                          datetime(2009, 12, 28, 9, 0)])

    def testYearlyByHour(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1998, 9, 2, 6, 0),
                          datetime(1998, 9, 2, 18, 0)])

    def testYearlyByMinute(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6),
                          datetime(1997, 9, 2, 9, 18),
                          datetime(1998, 9, 2, 9, 6)])

    def testYearlyBySecond(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1998, 9, 2, 9, 0, 6)])

    def testYearlyByHourAndMinute(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6),
                          datetime(1997, 9, 2, 18, 18),
                          datetime(1998, 9, 2, 6, 6)])

    def testYearlyByHourAndSecond(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1998, 9, 2, 6, 0, 6)])

    def testYearlyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testYearlyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testYearlyBySetPos(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonthday=15,
                              byhour=(6,18),
                              bysetpos=(3,-3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 11, 15, 18, 0),
                          datetime(1998, 2, 15, 6, 0),
                          datetime(1998, 11, 15, 18, 0)])

    def testMonthly(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 10, 2, 9, 0),
                          datetime(1997, 11, 2, 9, 0)])

    def testMonthlyInterval(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 11, 2, 9, 0),
                          datetime(1998, 1, 2, 9, 0)])

    def testMonthlyIntervalLarge(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              interval=18,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1999, 3, 2, 9, 0),
                          datetime(2000, 9, 2, 9, 0)])

    def testMonthlyByMonth(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 2, 9, 0),
                          datetime(1998, 3, 2, 9, 0),
                          datetime(1999, 1, 2, 9, 0)])


    def testMonthlyByMonthDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 10, 1, 9, 0),
                          datetime(1997, 10, 3, 9, 0)])

    def testMonthlyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 9, 0),
                          datetime(1998, 1, 7, 9, 0),
                          datetime(1998, 3, 5, 9, 0)])

    def testMonthlyByWeekDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testMonthlyByNWeekDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 25, 9, 0),
                          datetime(1997, 10, 7, 9, 0)])

    def testMonthlyByNWeekDayLarge(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekday=(TU(3),TH(-3)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 11, 9, 0),
                          datetime(1997, 9, 16, 9, 0),
                          datetime(1997, 10, 16, 9, 0)])

    def testMonthlyByMonthAndWeekDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 8, 9, 0)])

    def testMonthlyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 29, 9, 0),
                          datetime(1998, 3, 3, 9, 0)])

    def testMonthlyByMonthAndNWeekDayLarge(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(3),TH(-3)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 15, 9, 0),
                          datetime(1998, 1, 20, 9, 0),
                          datetime(1998, 3, 12, 9, 0)])

    def testMonthlyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 2, 3, 9, 0),
                          datetime(1998, 3, 3, 9, 0)])

    def testMonthlyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 3, 3, 9, 0),
                          datetime(2001, 3, 1, 9, 0)])

    def testMonthlyByYearDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testMonthlyByYearDayNeg(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testMonthlyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 4, 10, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testMonthlyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 4, 10, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])


    def testMonthlyByWeekNo(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 9, 0),
                          datetime(1998, 5, 12, 9, 0),
                          datetime(1998, 5, 13, 9, 0)])

    def testMonthlyByWeekNoAndWeekDay(self):
        # That's a nice one. The first days of week number one
        # may be in the last year.
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 9, 0),
                          datetime(1999, 1, 4, 9, 0),
                          datetime(2000, 1, 3, 9, 0)])

    def testMonthlyByWeekNoAndWeekDayLarge(self):
        # Another nice test. The last days of week number 52/53
        # may be in the next year.
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1998, 12, 27, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testMonthlyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1999, 1, 3, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testMonthlyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 9, 0),
                          datetime(2004, 12, 27, 9, 0),
                          datetime(2009, 12, 28, 9, 0)])

    def testMonthlyByEaster(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 9, 0),
                          datetime(1999, 4, 4, 9, 0),
                          datetime(2000, 4, 23, 9, 0)])

    def testMonthlyByEasterPos(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 9, 0),
                          datetime(1999, 4, 5, 9, 0),
                          datetime(2000, 4, 24, 9, 0)])

    def testMonthlyByEasterNeg(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 9, 0),
                          datetime(1999, 4, 3, 9, 0),
                          datetime(2000, 4, 22, 9, 0)])

    def testMonthlyByHour(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1997, 10, 2, 6, 0),
                          datetime(1997, 10, 2, 18, 0)])

    def testMonthlyByMinute(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6),
                          datetime(1997, 9, 2, 9, 18),
                          datetime(1997, 10, 2, 9, 6)])

    def testMonthlyBySecond(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1997, 10, 2, 9, 0, 6)])

    def testMonthlyByHourAndMinute(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6),
                          datetime(1997, 9, 2, 18, 18),
                          datetime(1997, 10, 2, 6, 6)])

    def testMonthlyByHourAndSecond(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1997, 10, 2, 6, 0, 6)])

    def testMonthlyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testMonthlyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testMonthlyBySetPos(self):
        self.assertEqual(list(rrule(MONTHLY,
                              count=3,
                              bymonthday=(13,17),
                              byhour=(6,18),
                              bysetpos=(3,-3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 13, 18, 0),
                          datetime(1997, 9, 17, 6, 0),
                          datetime(1997, 10, 13, 18, 0)])

    def testWeekly(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testWeeklyInterval(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 16, 9, 0),
                          datetime(1997, 9, 30, 9, 0)])

    def testWeeklyIntervalLarge(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              interval=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 1, 20, 9, 0),
                          datetime(1998, 6, 9, 9, 0)])

    def testWeeklyByMonth(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 13, 9, 0),
                          datetime(1998, 1, 20, 9, 0)])

    def testWeeklyByMonthDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 10, 1, 9, 0),
                          datetime(1997, 10, 3, 9, 0)])

    def testWeeklyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 9, 0),
                          datetime(1998, 1, 7, 9, 0),
                          datetime(1998, 3, 5, 9, 0)])

    def testWeeklyByWeekDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testWeeklyByNWeekDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testWeeklyByMonthAndWeekDay(self):
        # This test is interesting, because it crosses the year
        # boundary in a weekly period to find day '1' as a
        # valid recurrence.
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 8, 9, 0)])

    def testWeeklyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 8, 9, 0)])

    def testWeeklyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 2, 3, 9, 0),
                          datetime(1998, 3, 3, 9, 0)])

    def testWeeklyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 3, 3, 9, 0),
                          datetime(2001, 3, 1, 9, 0)])

    def testWeeklyByYearDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testWeeklyByYearDayNeg(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testWeeklyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=4,
                              bymonth=(1,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 1, 1, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testWeeklyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=4,
                              bymonth=(1,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 1, 1, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testWeeklyByWeekNo(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 9, 0),
                          datetime(1998, 5, 12, 9, 0),
                          datetime(1998, 5, 13, 9, 0)])

    def testWeeklyByWeekNoAndWeekDay(self):
        # That's a nice one. The first days of week number one
        # may be in the last year.
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 9, 0),
                          datetime(1999, 1, 4, 9, 0),
                          datetime(2000, 1, 3, 9, 0)])

    def testWeeklyByWeekNoAndWeekDayLarge(self):
        # Another nice test. The last days of week number 52/53
        # may be in the next year.
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1998, 12, 27, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testWeeklyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1999, 1, 3, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testWeeklyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 9, 0),
                          datetime(2004, 12, 27, 9, 0),
                          datetime(2009, 12, 28, 9, 0)])

    def testWeeklyByEaster(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 9, 0),
                          datetime(1999, 4, 4, 9, 0),
                          datetime(2000, 4, 23, 9, 0)])

    def testWeeklyByEasterPos(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 9, 0),
                          datetime(1999, 4, 5, 9, 0),
                          datetime(2000, 4, 24, 9, 0)])

    def testWeeklyByEasterNeg(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 9, 0),
                          datetime(1999, 4, 3, 9, 0),
                          datetime(2000, 4, 22, 9, 0)])

    def testWeeklyByHour(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1997, 9, 9, 6, 0),
                          datetime(1997, 9, 9, 18, 0)])

    def testWeeklyByMinute(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6),
                          datetime(1997, 9, 2, 9, 18),
                          datetime(1997, 9, 9, 9, 6)])

    def testWeeklyBySecond(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1997, 9, 9, 9, 0, 6)])

    def testWeeklyByHourAndMinute(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6),
                          datetime(1997, 9, 2, 18, 18),
                          datetime(1997, 9, 9, 6, 6)])

    def testWeeklyByHourAndSecond(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1997, 9, 9, 6, 0, 6)])

    def testWeeklyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testWeeklyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testWeeklyBySetPos(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              byweekday=(TU,TH),
                              byhour=(6,18),
                              bysetpos=(3,-3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1997, 9, 4, 6, 0),
                          datetime(1997, 9, 9, 18, 0)])

    def testDaily(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0)])

    def testDailyInterval(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 6, 9, 0)])

    def testDailyIntervalLarge(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              interval=92,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 12, 3, 9, 0),
                          datetime(1998, 3, 5, 9, 0)])

    def testDailyByMonth(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 2, 9, 0),
                          datetime(1998, 1, 3, 9, 0)])

    def testDailyByMonthDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 10, 1, 9, 0),
                          datetime(1997, 10, 3, 9, 0)])

    def testDailyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 9, 0),
                          datetime(1998, 1, 7, 9, 0),
                          datetime(1998, 3, 5, 9, 0)])

    def testDailyByWeekDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testDailyByNWeekDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testDailyByMonthAndWeekDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 8, 9, 0)])

    def testDailyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 1, 8, 9, 0)])

    def testDailyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 2, 3, 9, 0),
                          datetime(1998, 3, 3, 9, 0)])

    def testDailyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 3, 3, 9, 0),
                          datetime(2001, 3, 1, 9, 0)])

    def testDailyByYearDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testDailyByYearDayNeg(self):
        self.assertEqual(list(rrule(DAILY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 9, 0),
                          datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 4, 10, 9, 0),
                          datetime(1998, 7, 19, 9, 0)])

    def testDailyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(DAILY,
                              count=4,
                              bymonth=(1,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 1, 1, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testDailyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(DAILY,
                              count=4,
                              bymonth=(1,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 9, 0),
                          datetime(1998, 7, 19, 9, 0),
                          datetime(1999, 1, 1, 9, 0),
                          datetime(1999, 7, 19, 9, 0)])

    def testDailyByWeekNo(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 9, 0),
                          datetime(1998, 5, 12, 9, 0),
                          datetime(1998, 5, 13, 9, 0)])

    def testDailyByWeekNoAndWeekDay(self):
        # That's a nice one. The first days of week number one
        # may be in the last year.
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 9, 0),
                          datetime(1999, 1, 4, 9, 0),
                          datetime(2000, 1, 3, 9, 0)])

    def testDailyByWeekNoAndWeekDayLarge(self):
        # Another nice test. The last days of week number 52/53
        # may be in the next year.
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1998, 12, 27, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testDailyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 9, 0),
                          datetime(1999, 1, 3, 9, 0),
                          datetime(2000, 1, 2, 9, 0)])

    def testDailyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 9, 0),
                          datetime(2004, 12, 27, 9, 0),
                          datetime(2009, 12, 28, 9, 0)])

    def testDailyByEaster(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 9, 0),
                          datetime(1999, 4, 4, 9, 0),
                          datetime(2000, 4, 23, 9, 0)])

    def testDailyByEasterPos(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 9, 0),
                          datetime(1999, 4, 5, 9, 0),
                          datetime(2000, 4, 24, 9, 0)])

    def testDailyByEasterNeg(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 9, 0),
                          datetime(1999, 4, 3, 9, 0),
                          datetime(2000, 4, 22, 9, 0)])

    def testDailyByHour(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1997, 9, 3, 6, 0),
                          datetime(1997, 9, 3, 18, 0)])

    def testDailyByMinute(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6),
                          datetime(1997, 9, 2, 9, 18),
                          datetime(1997, 9, 3, 9, 6)])

    def testDailyBySecond(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1997, 9, 3, 9, 0, 6)])

    def testDailyByHourAndMinute(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6),
                          datetime(1997, 9, 2, 18, 18),
                          datetime(1997, 9, 3, 6, 6)])

    def testDailyByHourAndSecond(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1997, 9, 3, 6, 0, 6)])

    def testDailyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testDailyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testDailyBySetPos(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              byhour=(6,18),
                              byminute=(15,45),
                              bysetpos=(3,-3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 15),
                          datetime(1997, 9, 3, 6, 45),
                          datetime(1997, 9, 3, 18, 15)])

    def testHourly(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 10, 0),
                          datetime(1997, 9, 2, 11, 0)])

    def testHourlyInterval(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 11, 0),
                          datetime(1997, 9, 2, 13, 0)])

    def testHourlyIntervalLarge(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              interval=769,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 10, 4, 10, 0),
                          datetime(1997, 11, 5, 11, 0)])

    def testHourlyByMonth(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 1, 0),
                          datetime(1998, 1, 1, 2, 0)])

    def testHourlyByMonthDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 0, 0),
                          datetime(1997, 9, 3, 1, 0),
                          datetime(1997, 9, 3, 2, 0)])

    def testHourlyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 0, 0),
                          datetime(1998, 1, 5, 1, 0),
                          datetime(1998, 1, 5, 2, 0)])

    def testHourlyByWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 10, 0),
                          datetime(1997, 9, 2, 11, 0)])

    def testHourlyByNWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 10, 0),
                          datetime(1997, 9, 2, 11, 0)])

    def testHourlyByMonthAndWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 1, 0),
                          datetime(1998, 1, 1, 2, 0)])

    def testHourlyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 1, 0),
                          datetime(1998, 1, 1, 2, 0)])

    def testHourlyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 1, 0),
                          datetime(1998, 1, 1, 2, 0)])

    def testHourlyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 1, 0),
                          datetime(1998, 1, 1, 2, 0)])

    def testHourlyByYearDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 0, 0),
                          datetime(1997, 12, 31, 1, 0),
                          datetime(1997, 12, 31, 2, 0),
                          datetime(1997, 12, 31, 3, 0)])

    def testHourlyByYearDayNeg(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 0, 0),
                          datetime(1997, 12, 31, 1, 0),
                          datetime(1997, 12, 31, 2, 0),
                          datetime(1997, 12, 31, 3, 0)])

    def testHourlyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 0, 0),
                          datetime(1998, 4, 10, 1, 0),
                          datetime(1998, 4, 10, 2, 0),
                          datetime(1998, 4, 10, 3, 0)])

    def testHourlyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 0, 0),
                          datetime(1998, 4, 10, 1, 0),
                          datetime(1998, 4, 10, 2, 0),
                          datetime(1998, 4, 10, 3, 0)])

    def testHourlyByWeekNo(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 0, 0),
                          datetime(1998, 5, 11, 1, 0),
                          datetime(1998, 5, 11, 2, 0)])

    def testHourlyByWeekNoAndWeekDay(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 0, 0),
                          datetime(1997, 12, 29, 1, 0),
                          datetime(1997, 12, 29, 2, 0)])

    def testHourlyByWeekNoAndWeekDayLarge(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 0, 0),
                          datetime(1997, 12, 28, 1, 0),
                          datetime(1997, 12, 28, 2, 0)])

    def testHourlyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 0, 0),
                          datetime(1997, 12, 28, 1, 0),
                          datetime(1997, 12, 28, 2, 0)])

    def testHourlyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 0, 0),
                          datetime(1998, 12, 28, 1, 0),
                          datetime(1998, 12, 28, 2, 0)])

    def testHourlyByEaster(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 0, 0),
                          datetime(1998, 4, 12, 1, 0),
                          datetime(1998, 4, 12, 2, 0)])

    def testHourlyByEasterPos(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 0, 0),
                          datetime(1998, 4, 13, 1, 0),
                          datetime(1998, 4, 13, 2, 0)])

    def testHourlyByEasterNeg(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 0, 0),
                          datetime(1998, 4, 11, 1, 0),
                          datetime(1998, 4, 11, 2, 0)])

    def testHourlyByHour(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1997, 9, 3, 6, 0),
                          datetime(1997, 9, 3, 18, 0)])

    def testHourlyByMinute(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6),
                          datetime(1997, 9, 2, 9, 18),
                          datetime(1997, 9, 2, 10, 6)])

    def testHourlyBySecond(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1997, 9, 2, 10, 0, 6)])

    def testHourlyByHourAndMinute(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6),
                          datetime(1997, 9, 2, 18, 18),
                          datetime(1997, 9, 3, 6, 6)])

    def testHourlyByHourAndSecond(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1997, 9, 3, 6, 0, 6)])

    def testHourlyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testHourlyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testHourlyBySetPos(self):
        self.assertEqual(list(rrule(HOURLY,
                              count=3,
                              byminute=(15,45),
                              bysecond=(15,45),
                              bysetpos=(3,-3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 15, 45),
                          datetime(1997, 9, 2, 9, 45, 15),
                          datetime(1997, 9, 2, 10, 15, 45)])

    def testMinutely(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 9, 1),
                          datetime(1997, 9, 2, 9, 2)])

    def testMinutelyInterval(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 9, 2),
                          datetime(1997, 9, 2, 9, 4)])

    def testMinutelyIntervalLarge(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              interval=1501,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 10, 1),
                          datetime(1997, 9, 4, 11, 2)])

    def testMinutelyByMonth(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 0, 1),
                          datetime(1998, 1, 1, 0, 2)])

    def testMinutelyByMonthDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 0, 0),
                          datetime(1997, 9, 3, 0, 1),
                          datetime(1997, 9, 3, 0, 2)])

    def testMinutelyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 0, 0),
                          datetime(1998, 1, 5, 0, 1),
                          datetime(1998, 1, 5, 0, 2)])

    def testMinutelyByWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 9, 1),
                          datetime(1997, 9, 2, 9, 2)])

    def testMinutelyByNWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 2, 9, 1),
                          datetime(1997, 9, 2, 9, 2)])

    def testMinutelyByMonthAndWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 0, 1),
                          datetime(1998, 1, 1, 0, 2)])

    def testMinutelyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 0, 1),
                          datetime(1998, 1, 1, 0, 2)])

    def testMinutelyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 0, 1),
                          datetime(1998, 1, 1, 0, 2)])

    def testMinutelyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0),
                          datetime(1998, 1, 1, 0, 1),
                          datetime(1998, 1, 1, 0, 2)])

    def testMinutelyByYearDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 0, 0),
                          datetime(1997, 12, 31, 0, 1),
                          datetime(1997, 12, 31, 0, 2),
                          datetime(1997, 12, 31, 0, 3)])

    def testMinutelyByYearDayNeg(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 0, 0),
                          datetime(1997, 12, 31, 0, 1),
                          datetime(1997, 12, 31, 0, 2),
                          datetime(1997, 12, 31, 0, 3)])

    def testMinutelyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 0, 0),
                          datetime(1998, 4, 10, 0, 1),
                          datetime(1998, 4, 10, 0, 2),
                          datetime(1998, 4, 10, 0, 3)])

    def testMinutelyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 0, 0),
                          datetime(1998, 4, 10, 0, 1),
                          datetime(1998, 4, 10, 0, 2),
                          datetime(1998, 4, 10, 0, 3)])

    def testMinutelyByWeekNo(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 0, 0),
                          datetime(1998, 5, 11, 0, 1),
                          datetime(1998, 5, 11, 0, 2)])

    def testMinutelyByWeekNoAndWeekDay(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 0, 0),
                          datetime(1997, 12, 29, 0, 1),
                          datetime(1997, 12, 29, 0, 2)])

    def testMinutelyByWeekNoAndWeekDayLarge(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 0, 0),
                          datetime(1997, 12, 28, 0, 1),
                          datetime(1997, 12, 28, 0, 2)])

    def testMinutelyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 0, 0),
                          datetime(1997, 12, 28, 0, 1),
                          datetime(1997, 12, 28, 0, 2)])

    def testMinutelyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 0, 0),
                          datetime(1998, 12, 28, 0, 1),
                          datetime(1998, 12, 28, 0, 2)])

    def testMinutelyByEaster(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 0, 0),
                          datetime(1998, 4, 12, 0, 1),
                          datetime(1998, 4, 12, 0, 2)])

    def testMinutelyByEasterPos(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 0, 0),
                          datetime(1998, 4, 13, 0, 1),
                          datetime(1998, 4, 13, 0, 2)])

    def testMinutelyByEasterNeg(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 0, 0),
                          datetime(1998, 4, 11, 0, 1),
                          datetime(1998, 4, 11, 0, 2)])

    def testMinutelyByHour(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0),
                          datetime(1997, 9, 2, 18, 1),
                          datetime(1997, 9, 2, 18, 2)])

    def testMinutelyByMinute(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6),
                          datetime(1997, 9, 2, 9, 18),
                          datetime(1997, 9, 2, 10, 6)])

    def testMinutelyBySecond(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1997, 9, 2, 9, 1, 6)])

    def testMinutelyByHourAndMinute(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6),
                          datetime(1997, 9, 2, 18, 18),
                          datetime(1997, 9, 3, 6, 6)])

    def testMinutelyByHourAndSecond(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1997, 9, 2, 18, 1, 6)])

    def testMinutelyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testMinutelyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testMinutelyBySetPos(self):
        self.assertEqual(list(rrule(MINUTELY,
                              count=3,
                              bysecond=(15,30,45),
                              bysetpos=(3,-3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 15),
                          datetime(1997, 9, 2, 9, 0, 45),
                          datetime(1997, 9, 2, 9, 1, 15)])

    def testSecondly(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 0),
                          datetime(1997, 9, 2, 9, 0, 1),
                          datetime(1997, 9, 2, 9, 0, 2)])

    def testSecondlyInterval(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              interval=2,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 0),
                          datetime(1997, 9, 2, 9, 0, 2),
                          datetime(1997, 9, 2, 9, 0, 4)])

    def testSecondlyIntervalLarge(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              interval=90061,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 0),
                          datetime(1997, 9, 3, 10, 1, 1),
                          datetime(1997, 9, 4, 11, 2, 2)])

    def testSecondlyByMonth(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonth=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0, 0),
                          datetime(1998, 1, 1, 0, 0, 1),
                          datetime(1998, 1, 1, 0, 0, 2)])

    def testSecondlyByMonthDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonthday=(1,3),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 3, 0, 0, 0),
                          datetime(1997, 9, 3, 0, 0, 1),
                          datetime(1997, 9, 3, 0, 0, 2)])

    def testSecondlyByMonthAndMonthDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(5,7),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 5, 0, 0, 0),
                          datetime(1998, 1, 5, 0, 0, 1),
                          datetime(1998, 1, 5, 0, 0, 2)])

    def testSecondlyByWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 0),
                          datetime(1997, 9, 2, 9, 0, 1),
                          datetime(1997, 9, 2, 9, 0, 2)])

    def testSecondlyByNWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 0),
                          datetime(1997, 9, 2, 9, 0, 1),
                          datetime(1997, 9, 2, 9, 0, 2)])

    def testSecondlyByMonthAndWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0, 0),
                          datetime(1998, 1, 1, 0, 0, 1),
                          datetime(1998, 1, 1, 0, 0, 2)])

    def testSecondlyByMonthAndNWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonth=(1,3),
                              byweekday=(TU(1),TH(-1)),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0, 0),
                          datetime(1998, 1, 1, 0, 0, 1),
                          datetime(1998, 1, 1, 0, 0, 2)])

    def testSecondlyByMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0, 0),
                          datetime(1998, 1, 1, 0, 0, 1),
                          datetime(1998, 1, 1, 0, 0, 2)])

    def testSecondlyByMonthAndMonthDayAndWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bymonth=(1,3),
                              bymonthday=(1,3),
                              byweekday=(TU,TH),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 1, 1, 0, 0, 0),
                          datetime(1998, 1, 1, 0, 0, 1),
                          datetime(1998, 1, 1, 0, 0, 2)])

    def testSecondlyByYearDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=4,
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 0, 0, 0),
                          datetime(1997, 12, 31, 0, 0, 1),
                          datetime(1997, 12, 31, 0, 0, 2),
                          datetime(1997, 12, 31, 0, 0, 3)])

    def testSecondlyByYearDayNeg(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=4,
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 31, 0, 0, 0),
                          datetime(1997, 12, 31, 0, 0, 1),
                          datetime(1997, 12, 31, 0, 0, 2),
                          datetime(1997, 12, 31, 0, 0, 3)])

    def testSecondlyByMonthAndYearDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(1,100,200,365),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 0, 0, 0),
                          datetime(1998, 4, 10, 0, 0, 1),
                          datetime(1998, 4, 10, 0, 0, 2),
                          datetime(1998, 4, 10, 0, 0, 3)])

    def testSecondlyByMonthAndYearDayNeg(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=4,
                              bymonth=(4,7),
                              byyearday=(-365,-266,-166,-1),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 10, 0, 0, 0),
                          datetime(1998, 4, 10, 0, 0, 1),
                          datetime(1998, 4, 10, 0, 0, 2),
                          datetime(1998, 4, 10, 0, 0, 3)])

    def testSecondlyByWeekNo(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekno=20,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 5, 11, 0, 0, 0),
                          datetime(1998, 5, 11, 0, 0, 1),
                          datetime(1998, 5, 11, 0, 0, 2)])

    def testSecondlyByWeekNoAndWeekDay(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekno=1,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 29, 0, 0, 0),
                          datetime(1997, 12, 29, 0, 0, 1),
                          datetime(1997, 12, 29, 0, 0, 2)])

    def testSecondlyByWeekNoAndWeekDayLarge(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekno=52,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 0, 0, 0),
                          datetime(1997, 12, 28, 0, 0, 1),
                          datetime(1997, 12, 28, 0, 0, 2)])

    def testSecondlyByWeekNoAndWeekDayLast(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekno=-1,
                              byweekday=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 12, 28, 0, 0, 0),
                          datetime(1997, 12, 28, 0, 0, 1),
                          datetime(1997, 12, 28, 0, 0, 2)])

    def testSecondlyByWeekNoAndWeekDay53(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byweekno=53,
                              byweekday=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 12, 28, 0, 0, 0),
                          datetime(1998, 12, 28, 0, 0, 1),
                          datetime(1998, 12, 28, 0, 0, 2)])

    def testSecondlyByEaster(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byeaster=0,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 12, 0, 0, 0),
                          datetime(1998, 4, 12, 0, 0, 1),
                          datetime(1998, 4, 12, 0, 0, 2)])

    def testSecondlyByEasterPos(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byeaster=1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 13, 0, 0, 0),
                          datetime(1998, 4, 13, 0, 0, 1),
                          datetime(1998, 4, 13, 0, 0, 2)])

    def testSecondlyByEasterNeg(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byeaster=-1,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1998, 4, 11, 0, 0, 0),
                          datetime(1998, 4, 11, 0, 0, 1),
                          datetime(1998, 4, 11, 0, 0, 2)])

    def testSecondlyByHour(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byhour=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 0),
                          datetime(1997, 9, 2, 18, 0, 1),
                          datetime(1997, 9, 2, 18, 0, 2)])

    def testSecondlyByMinute(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 0),
                          datetime(1997, 9, 2, 9, 6, 1),
                          datetime(1997, 9, 2, 9, 6, 2)])

    def testSecondlyBySecond(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0, 6),
                          datetime(1997, 9, 2, 9, 0, 18),
                          datetime(1997, 9, 2, 9, 1, 6)])

    def testSecondlyByHourAndMinute(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 0),
                          datetime(1997, 9, 2, 18, 6, 1),
                          datetime(1997, 9, 2, 18, 6, 2)])

    def testSecondlyByHourAndSecond(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byhour=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 0, 6),
                          datetime(1997, 9, 2, 18, 0, 18),
                          datetime(1997, 9, 2, 18, 1, 6)])

    def testSecondlyByMinuteAndSecond(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 6, 6),
                          datetime(1997, 9, 2, 9, 6, 18),
                          datetime(1997, 9, 2, 9, 18, 6)])

    def testSecondlyByHourAndMinuteAndSecond(self):
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              byhour=(6,18),
                              byminute=(6,18),
                              bysecond=(6,18),
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 18, 6, 6),
                          datetime(1997, 9, 2, 18, 6, 18),
                          datetime(1997, 9, 2, 18, 18, 6)])

    def testSecondlyByHourAndMinuteAndSecondBug(self):
        # This explores a bug found by Mathieu Bridon.
        self.assertEqual(list(rrule(SECONDLY,
                              count=3,
                              bysecond=(0,),
                              byminute=(1,),
                              dtstart=parse("20100322120100"))),
                         [datetime(2010, 3, 22, 12, 1),
                          datetime(2010, 3, 22, 13, 1),
                          datetime(2010, 3, 22, 14, 1)])

    def testUntilNotMatching(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000"),
                              until=parse("19970905T080000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0)])

    def testUntilMatching(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000"),
                              until=parse("19970904T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0)])

    def testUntilSingle(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000"),
                              until=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0)])

    def testUntilEmpty(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000"),
                              until=parse("19970901T090000"))),
                         [])

    def testUntilWithDate(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000"),
                              until=date(1997, 9, 5))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0)])

    def testWkStIntervalMO(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              interval=2,
                              byweekday=(TU,SU),
                              wkst=MO,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 7, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testWkStIntervalSU(self):
        self.assertEqual(list(rrule(WEEKLY,
                              count=3,
                              interval=2,
                              byweekday=(TU,SU),
                              wkst=SU,
                              dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 14, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testDTStartIsDate(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=date(1997, 9, 2))),
                         [datetime(1997, 9, 2, 0, 0),
                          datetime(1997, 9, 3, 0, 0),
                          datetime(1997, 9, 4, 0, 0)])

    def testDTStartWithMicroseconds(self):
        self.assertEqual(list(rrule(DAILY,
                              count=3,
                              dtstart=parse("19970902T090000.5"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0)])

    def testMaxYear(self):
        self.assertEqual(list(rrule(YEARLY,
                              count=3,
                              bymonth=2,
                              bymonthday=31,
                              dtstart=parse("99970902T090000"))),
                         [])

    def testGetItem(self):
        self.assertEqual(rrule(DAILY,
                               count=3,
                               dtstart=parse("19970902T090000"))[0],
                         datetime(1997, 9, 2, 9, 0))

    def testGetItemNeg(self):
        self.assertEqual(rrule(DAILY,
                               count=3,
                               dtstart=parse("19970902T090000"))[-1],
                         datetime(1997, 9, 4, 9, 0))

    def testGetItemSlice(self):
        self.assertEqual(rrule(DAILY,
                               #count=3,
                               dtstart=parse("19970902T090000"))[1:2],
                         [datetime(1997, 9, 3, 9, 0)])

    def testGetItemSliceEmpty(self):
        self.assertEqual(rrule(DAILY,
                               count=3,
                               dtstart=parse("19970902T090000"))[:],
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0)])

    def testGetItemSliceStep(self):
        self.assertEqual(rrule(DAILY,
                               count=3,
                               dtstart=parse("19970902T090000"))[::-2],
                         [datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 2, 9, 0)])

    def testCount(self):
        self.assertEqual(rrule(DAILY,
                               count=3,
                               dtstart=parse("19970902T090000")).count(),
                         3)

    def testContains(self):
        rr = rrule(DAILY, count=3, dtstart=parse("19970902T090000"))
        self.assertEqual(datetime(1997, 9, 3, 9, 0) in rr, True)

    def testContainsNot(self):
        rr = rrule(DAILY, count=3, dtstart=parse("19970902T090000"))
        self.assertEqual(datetime(1997, 9, 3, 9, 0) not in rr, False)

    def testBefore(self):
        self.assertEqual(rrule(DAILY,
                               #count=5,
                               dtstart=parse("19970902T090000"))
                               .before(parse("19970905T090000")),
                         datetime(1997, 9, 4, 9, 0))

    def testBeforeInc(self):
        self.assertEqual(rrule(DAILY,
                               #count=5,
                               dtstart=parse("19970902T090000"))
                               .before(parse("19970905T090000"), inc=True),
                         datetime(1997, 9, 5, 9, 0))

    def testAfter(self):
        self.assertEqual(rrule(DAILY,
                               #count=5,
                               dtstart=parse("19970902T090000"))
                               .after(parse("19970904T090000")),
                         datetime(1997, 9, 5, 9, 0))

    def testAfterInc(self):
        self.assertEqual(rrule(DAILY,
                               #count=5,
                               dtstart=parse("19970902T090000"))
                               .after(parse("19970904T090000"), inc=True),
                         datetime(1997, 9, 4, 9, 0))

    def testBetween(self):
        self.assertEqual(rrule(DAILY,
                               #count=5,
                               dtstart=parse("19970902T090000"))
                               .between(parse("19970902T090000"),
                                        parse("19970906T090000")),
                         [datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 5, 9, 0)])

    def testBetweenInc(self):
        self.assertEqual(rrule(DAILY,
                               #count=5,
                               dtstart=parse("19970902T090000"))
                               .between(parse("19970902T090000"),
                                        parse("19970906T090000"), inc=True),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 5, 9, 0),
                          datetime(1997, 9, 6, 9, 0)])

    def testCachePre(self):
        rr = rrule(DAILY, count=15, cache=True,
                   dtstart=parse("19970902T090000"))
        self.assertEqual(list(rr),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 5, 9, 0),
                          datetime(1997, 9, 6, 9, 0),
                          datetime(1997, 9, 7, 9, 0),
                          datetime(1997, 9, 8, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 10, 9, 0),
                          datetime(1997, 9, 11, 9, 0),
                          datetime(1997, 9, 12, 9, 0),
                          datetime(1997, 9, 13, 9, 0),
                          datetime(1997, 9, 14, 9, 0),
                          datetime(1997, 9, 15, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testCachePost(self):
        rr = rrule(DAILY, count=15, cache=True,
                   dtstart=parse("19970902T090000"))
        for x in rr: pass
        self.assertEqual(list(rr),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 5, 9, 0),
                          datetime(1997, 9, 6, 9, 0),
                          datetime(1997, 9, 7, 9, 0),
                          datetime(1997, 9, 8, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 10, 9, 0),
                          datetime(1997, 9, 11, 9, 0),
                          datetime(1997, 9, 12, 9, 0),
                          datetime(1997, 9, 13, 9, 0),
                          datetime(1997, 9, 14, 9, 0),
                          datetime(1997, 9, 15, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testCachePostInternal(self):
        rr = rrule(DAILY, count=15, cache=True,
                   dtstart=parse("19970902T090000"))
        for x in rr: pass
        self.assertEqual(rr._cache,
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 3, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 5, 9, 0),
                          datetime(1997, 9, 6, 9, 0),
                          datetime(1997, 9, 7, 9, 0),
                          datetime(1997, 9, 8, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 10, 9, 0),
                          datetime(1997, 9, 11, 9, 0),
                          datetime(1997, 9, 12, 9, 0),
                          datetime(1997, 9, 13, 9, 0),
                          datetime(1997, 9, 14, 9, 0),
                          datetime(1997, 9, 15, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testCachePreContains(self):
        rr = rrule(DAILY, count=3, cache=True,
                   dtstart=parse("19970902T090000"))
        self.assertEqual(datetime(1997, 9, 3, 9, 0) in rr, True)

    def testCachePostContains(self):
        rr = rrule(DAILY, count=3, cache=True,
                   dtstart=parse("19970902T090000"))
        for x in rr: pass
        self.assertEqual(datetime(1997, 9, 3, 9, 0) in rr, True)

    def testSet(self):
        set = rruleset()
        set.rrule(rrule(YEARLY, count=2, byweekday=TU,
                        dtstart=parse("19970902T090000")))
        set.rrule(rrule(YEARLY, count=1, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testSetDate(self):
        set = rruleset()
        set.rrule(rrule(YEARLY, count=1, byweekday=TU,
                        dtstart=parse("19970902T090000")))
        set.rdate(datetime(1997, 9, 4, 9))
        set.rdate(datetime(1997, 9, 9, 9))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testSetExRule(self):
        set = rruleset()
        set.rrule(rrule(YEARLY, count=6, byweekday=(TU,TH),
                        dtstart=parse("19970902T090000")))
        set.exrule(rrule(YEARLY, count=3, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testSetExDate(self):
        set = rruleset()
        set.rrule(rrule(YEARLY, count=6, byweekday=(TU,TH),
                        dtstart=parse("19970902T090000")))
        set.exdate(datetime(1997, 9, 4, 9))
        set.exdate(datetime(1997, 9, 11, 9))
        set.exdate(datetime(1997, 9, 18, 9))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testSetExDateRevOrder(self):
        set = rruleset()
        set.rrule(rrule(MONTHLY, count=5, bymonthday=10,
                        dtstart=parse("20040101T090000")))
        set.exdate(datetime(2004, 4, 10, 9, 0))
        set.exdate(datetime(2004, 2, 10, 9, 0))
        self.assertEqual(list(set),
                         [datetime(2004, 1, 10, 9, 0),
                          datetime(2004, 3, 10, 9, 0),
                          datetime(2004, 5, 10, 9, 0)])

    def testSetDateAndExDate(self):
        set = rruleset()
        set.rdate(datetime(1997, 9, 2, 9))
        set.rdate(datetime(1997, 9, 4, 9))
        set.rdate(datetime(1997, 9, 9, 9))
        set.rdate(datetime(1997, 9, 11, 9))
        set.rdate(datetime(1997, 9, 16, 9))
        set.rdate(datetime(1997, 9, 18, 9))
        set.exdate(datetime(1997, 9, 4, 9))
        set.exdate(datetime(1997, 9, 11, 9))
        set.exdate(datetime(1997, 9, 18, 9))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testSetDateAndExRule(self):
        set = rruleset()
        set.rdate(datetime(1997, 9, 2, 9))
        set.rdate(datetime(1997, 9, 4, 9))
        set.rdate(datetime(1997, 9, 9, 9))
        set.rdate(datetime(1997, 9, 11, 9))
        set.rdate(datetime(1997, 9, 16, 9))
        set.rdate(datetime(1997, 9, 18, 9))
        set.exrule(rrule(YEARLY, count=3, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testSetCount(self):
        set = rruleset()
        set.rrule(rrule(YEARLY, count=6, byweekday=(TU,TH),
                        dtstart=parse("19970902T090000")))
        set.exrule(rrule(YEARLY, count=3, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        self.assertEqual(set.count(), 3)

    def testSetCachePre(self):
        set = rruleset()
        set.rrule(rrule(YEARLY, count=2, byweekday=TU,
                        dtstart=parse("19970902T090000")))
        set.rrule(rrule(YEARLY, count=1, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testSetCachePost(self):
        set = rruleset(cache=True)
        set.rrule(rrule(YEARLY, count=2, byweekday=TU,
                        dtstart=parse("19970902T090000")))
        set.rrule(rrule(YEARLY, count=1, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        for x in set: pass
        self.assertEqual(list(set),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testSetCachePostInternal(self):
        set = rruleset(cache=True)
        set.rrule(rrule(YEARLY, count=2, byweekday=TU,
                        dtstart=parse("19970902T090000")))
        set.rrule(rrule(YEARLY, count=1, byweekday=TH,
                        dtstart=parse("19970902T090000")))
        for x in set: pass
        self.assertEqual(list(set._cache),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testStr(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=3\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrType(self):
        self.assertEqual(isinstance(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=3\n"
                              ), rrule), True)

    def testStrForceSetType(self):
        self.assertEqual(isinstance(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=3\n"
                              , forceset=True), rruleset), True)

    def testStrSetType(self):
        self.assertEqual(isinstance(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=2;BYDAY=TU\n"
                              "RRULE:FREQ=YEARLY;COUNT=1;BYDAY=TH\n"
                              ), rruleset), True)

    def testStrCase(self):
        self.assertEqual(list(rrulestr(
                              "dtstart:19970902T090000\n"
                              "rrule:freq=yearly;count=3\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrSpaces(self):
        self.assertEqual(list(rrulestr(
                              " DTSTART:19970902T090000 "
                              " RRULE:FREQ=YEARLY;COUNT=3 "
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrExperimentalProp(self):
        self.assertEqual(list(rrulestr(
                            "DTSTART:19970902T090000\n"
                            "X-MEN:Wolverine\n"
                            "RRULE:FREQ=YEARLY;COUNT=3\n"
                            )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrSpacesAndLines(self):
        self.assertEqual(list(rrulestr(
                              " DTSTART:19970902T090000 \n"
                              " \n"
                              " RRULE:FREQ=YEARLY;COUNT=3 \n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrNoDTStart(self):
        self.assertEqual(list(rrulestr(
                              "RRULE:FREQ=YEARLY;COUNT=3\n"
                              , dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrValueOnly(self):
        self.assertEqual(list(rrulestr(
                              "FREQ=YEARLY;COUNT=3\n"
                              , dtstart=parse("19970902T090000"))),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1998, 9, 2, 9, 0),
                          datetime(1999, 9, 2, 9, 0)])

    def testStrUnfold(self):
        for input in ("FREQ=YEA\n RLY;COUNT=3\n",
                      "FREQ=YEA\n\tRLY;COUNT=3\n"):
                self.assertEqual(list(rrulestr(
                                        input, unfold=True,
                                        dtstart=parse("19970902T090000"))),
                                 [datetime(1997, 9, 2, 9, 0),
                                  datetime(1998, 9, 2, 9, 0),
                                  datetime(1999, 9, 2, 9, 0)])

    def testStrSet(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=2;BYDAY=TU\n"
                              "RRULE:FREQ=YEARLY;COUNT=1;BYDAY=TH\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testStrSetDate(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=1;BYDAY=TU\n"
                              "RDATE:19970904T090000\n"
                              "RDATE:19970909T090000\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 4, 9, 0),
                          datetime(1997, 9, 9, 9, 0)])

    def testStrSetExRule(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=6;BYDAY=TU,TH\n"
                              "EXRULE:FREQ=YEARLY;COUNT=3;BYDAY=TH\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testStrSetExDate(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=6;BYDAY=TU,TH\n"
                              "EXDATE:19970904T090000\n"
                              "EXDATE:19970911T090000\n"
                              "EXDATE:19970918T090000\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testStrSetDateAndExDate(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RDATE:19970902T090000\n"
                              "RDATE:19970904T090000\n"
                              "RDATE:19970909T090000\n"
                              "RDATE:19970911T090000\n"
                              "RDATE:19970916T090000\n"
                              "RDATE:19970918T090000\n"
                              "EXDATE:19970904T090000\n"
                              "EXDATE:19970911T090000\n"
                              "EXDATE:19970918T090000\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testStrSetDateAndExRule(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RDATE:19970902T090000\n"
                              "RDATE:19970904T090000\n"
                              "RDATE:19970909T090000\n"
                              "RDATE:19970911T090000\n"
                              "RDATE:19970916T090000\n"
                              "RDATE:19970918T090000\n"
                              "EXRULE:FREQ=YEARLY;COUNT=3;BYDAY=TH\n"
                              )),
                         [datetime(1997, 9, 2, 9, 0),
                          datetime(1997, 9, 9, 9, 0),
                          datetime(1997, 9, 16, 9, 0)])

    def testStrKeywords(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=3;INTERVAL=3;"
                                    "BYMONTH=3;BYWEEKDAY=TH;BYMONTHDAY=3;"
                                    "BYHOUR=3;BYMINUTE=3;BYSECOND=3\n"
                              )),
                         [datetime(2033, 3, 3, 3, 3, 3),
                          datetime(2039, 3, 3, 3, 3, 3),
                          datetime(2072, 3, 3, 3, 3, 3)])

    def testStrNWeekDay(self):
        self.assertEqual(list(rrulestr(
                              "DTSTART:19970902T090000\n"
                              "RRULE:FREQ=YEARLY;COUNT=3;BYDAY=1TU,-1TH\n"
                              )),
                         [datetime(1997, 12, 25, 9, 0),
                          datetime(1998, 1, 6, 9, 0),
                          datetime(1998, 12, 31, 9, 0)])

    def testBadBySetPos(self):
        self.assertRaises(ValueError,
                          rrule, MONTHLY,
                                 count=1,
                                 bysetpos=0,
                                 dtstart=parse("19970902T090000"))

    def testBadBySetPosMany(self):
        self.assertRaises(ValueError,
                          rrule, MONTHLY,
                                 count=1,
                                 bysetpos=(-1,0,1),
                                 dtstart=parse("19970902T090000"))


class ParserTest(unittest.TestCase):

    def setUp(self):
        self.tzinfos = {"BRST": -10800}
        self.brsttz = tzoffset("BRST", -10800)
        self.default = datetime(2003, 9, 25)

    def testDateCommandFormat(self):
        self.assertEqual(parse("Thu Sep 25 10:36:28 BRST 2003",
                               tzinfos=self.tzinfos),
                         datetime(2003, 9, 25, 10, 36, 28,
                                  tzinfo=self.brsttz))

    def testDateCommandFormatUnicode(self):
        self.assertEqual(parse(u"Thu Sep 25 10:36:28 BRST 2003",
                               tzinfos=self.tzinfos),
                         datetime(2003, 9, 25, 10, 36, 28,
                                  tzinfo=self.brsttz))


    def testDateCommandFormatReversed(self):
        self.assertEqual(parse("2003 10:36:28 BRST 25 Sep Thu",
                               tzinfos=self.tzinfos),
                         datetime(2003, 9, 25, 10, 36, 28,
                                  tzinfo=self.brsttz))

    def testDateCommandFormatIgnoreTz(self):
        self.assertEqual(parse("Thu Sep 25 10:36:28 BRST 2003",
                               ignoretz=True),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip1(self):
        self.assertEqual(parse("Thu Sep 25 10:36:28 2003"),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip2(self):
        self.assertEqual(parse("Thu Sep 25 10:36:28", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip3(self):
        self.assertEqual(parse("Thu Sep 10:36:28", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip4(self):
        self.assertEqual(parse("Thu 10:36:28", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip5(self):
        self.assertEqual(parse("Sep 10:36:28", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip6(self):
        self.assertEqual(parse("10:36:28", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testDateCommandFormatStrip7(self):
        self.assertEqual(parse("10:36", default=self.default),
                         datetime(2003, 9, 25, 10, 36))

    def testDateCommandFormatStrip8(self):
        self.assertEqual(parse("Thu Sep 25 2003"),
                         datetime(2003, 9, 25))

    def testDateCommandFormatStrip9(self):
        self.assertEqual(parse("Sep 25 2003"),
                         datetime(2003, 9, 25))

    def testDateCommandFormatStrip9(self):
        self.assertEqual(parse("Sep 2003", default=self.default),
                         datetime(2003, 9, 25))

    def testDateCommandFormatStrip10(self):
        self.assertEqual(parse("Sep", default=self.default),
                         datetime(2003, 9, 25))

    def testDateCommandFormatStrip11(self):
        self.assertEqual(parse("2003", default=self.default),
                         datetime(2003, 9, 25))

    def testDateRCommandFormat(self):
        self.assertEqual(parse("Thu, 25 Sep 2003 10:49:41 -0300"),
                         datetime(2003, 9, 25, 10, 49, 41,
                                  tzinfo=self.brsttz))

    def testISOFormat(self):
        self.assertEqual(parse("2003-09-25T10:49:41.5-03:00"),
                         datetime(2003, 9, 25, 10, 49, 41, 500000,
                                  tzinfo=self.brsttz))

    def testISOFormatStrip1(self):
        self.assertEqual(parse("2003-09-25T10:49:41-03:00"),
                         datetime(2003, 9, 25, 10, 49, 41,
                                  tzinfo=self.brsttz))

    def testISOFormatStrip2(self):
        self.assertEqual(parse("2003-09-25T10:49:41"),
                         datetime(2003, 9, 25, 10, 49, 41))

    def testISOFormatStrip3(self):
        self.assertEqual(parse("2003-09-25T10:49"),
                         datetime(2003, 9, 25, 10, 49))

    def testISOFormatStrip4(self):
        self.assertEqual(parse("2003-09-25T10"),
                         datetime(2003, 9, 25, 10))

    def testISOFormatStrip5(self):
        self.assertEqual(parse("2003-09-25"),
                         datetime(2003, 9, 25))

    def testISOStrippedFormat(self):
        self.assertEqual(parse("20030925T104941.5-0300"),
                         datetime(2003, 9, 25, 10, 49, 41, 500000,
                                  tzinfo=self.brsttz))

    def testISOStrippedFormatStrip1(self):
        self.assertEqual(parse("20030925T104941-0300"),
                         datetime(2003, 9, 25, 10, 49, 41,
                                  tzinfo=self.brsttz))

    def testISOStrippedFormatStrip2(self):
        self.assertEqual(parse("20030925T104941"),
                         datetime(2003, 9, 25, 10, 49, 41))

    def testISOStrippedFormatStrip3(self):
        self.assertEqual(parse("20030925T1049"),
                         datetime(2003, 9, 25, 10, 49, 0))

    def testISOStrippedFormatStrip4(self):
        self.assertEqual(parse("20030925T10"),
                         datetime(2003, 9, 25, 10))

    def testISOStrippedFormatStrip5(self):
        self.assertEqual(parse("20030925"),
                         datetime(2003, 9, 25))

    def testNoSeparator1(self):
        self.assertEqual(parse("199709020908"),
                         datetime(1997, 9, 2, 9, 8))

    def testNoSeparator2(self):
        self.assertEqual(parse("19970902090807"),
                         datetime(1997, 9, 2, 9, 8, 7))

    def testDateWithDash1(self):
        self.assertEqual(parse("2003-09-25"),
                         datetime(2003, 9, 25))

    def testDateWithDash2(self):
        self.assertEqual(parse("2003-Sep-25"),
                         datetime(2003, 9, 25))

    def testDateWithDash3(self):
        self.assertEqual(parse("25-Sep-2003"),
                         datetime(2003, 9, 25))

    def testDateWithDash4(self):
        self.assertEqual(parse("25-Sep-2003"),
                         datetime(2003, 9, 25))

    def testDateWithDash5(self):
        self.assertEqual(parse("Sep-25-2003"),
                         datetime(2003, 9, 25))

    def testDateWithDash6(self):
        self.assertEqual(parse("09-25-2003"),
                         datetime(2003, 9, 25))

    def testDateWithDash7(self):
        self.assertEqual(parse("25-09-2003"),
                         datetime(2003, 9, 25))

    def testDateWithDash8(self):
        self.assertEqual(parse("10-09-2003", dayfirst=True),
                         datetime(2003, 9, 10))

    def testDateWithDash9(self):
        self.assertEqual(parse("10-09-2003"),
                         datetime(2003, 10, 9))

    def testDateWithDash10(self):
        self.assertEqual(parse("10-09-03"),
                         datetime(2003, 10, 9))

    def testDateWithDash11(self):
        self.assertEqual(parse("10-09-03", yearfirst=True),
                         datetime(2010, 9, 3))

    def testDateWithDot1(self):
        self.assertEqual(parse("2003.09.25"),
                         datetime(2003, 9, 25))

    def testDateWithDot2(self):
        self.assertEqual(parse("2003.Sep.25"),
                         datetime(2003, 9, 25))

    def testDateWithDot3(self):
        self.assertEqual(parse("25.Sep.2003"),
                         datetime(2003, 9, 25))

    def testDateWithDot4(self):
        self.assertEqual(parse("25.Sep.2003"),
                         datetime(2003, 9, 25))

    def testDateWithDot5(self):
        self.assertEqual(parse("Sep.25.2003"),
                         datetime(2003, 9, 25))

    def testDateWithDot6(self):
        self.assertEqual(parse("09.25.2003"),
                         datetime(2003, 9, 25))

    def testDateWithDot7(self):
        self.assertEqual(parse("25.09.2003"),
                         datetime(2003, 9, 25))

    def testDateWithDot8(self):
        self.assertEqual(parse("10.09.2003", dayfirst=True),
                         datetime(2003, 9, 10))

    def testDateWithDot9(self):
        self.assertEqual(parse("10.09.2003"),
                         datetime(2003, 10, 9))

    def testDateWithDot10(self):
        self.assertEqual(parse("10.09.03"),
                         datetime(2003, 10, 9))

    def testDateWithDot11(self):
        self.assertEqual(parse("10.09.03", yearfirst=True),
                         datetime(2010, 9, 3))

    def testDateWithSlash1(self):
        self.assertEqual(parse("2003/09/25"),
                         datetime(2003, 9, 25))

    def testDateWithSlash2(self):
        self.assertEqual(parse("2003/Sep/25"),
                         datetime(2003, 9, 25))

    def testDateWithSlash3(self):
        self.assertEqual(parse("25/Sep/2003"),
                         datetime(2003, 9, 25))

    def testDateWithSlash4(self):
        self.assertEqual(parse("25/Sep/2003"),
                         datetime(2003, 9, 25))

    def testDateWithSlash5(self):
        self.assertEqual(parse("Sep/25/2003"),
                         datetime(2003, 9, 25))

    def testDateWithSlash6(self):
        self.assertEqual(parse("09/25/2003"),
                         datetime(2003, 9, 25))

    def testDateWithSlash7(self):
        self.assertEqual(parse("25/09/2003"),
                         datetime(2003, 9, 25))

    def testDateWithSlash8(self):
        self.assertEqual(parse("10/09/2003", dayfirst=True),
                         datetime(2003, 9, 10))

    def testDateWithSlash9(self):
        self.assertEqual(parse("10/09/2003"),
                         datetime(2003, 10, 9))

    def testDateWithSlash10(self):
        self.assertEqual(parse("10/09/03"),
                         datetime(2003, 10, 9))

    def testDateWithSlash11(self):
        self.assertEqual(parse("10/09/03", yearfirst=True),
                         datetime(2010, 9, 3))

    def testDateWithSpace12(self):
        self.assertEqual(parse("25 09 03"),
                         datetime(2003, 9, 25))

    def testDateWithSpace13(self):
        self.assertEqual(parse("25 09 03"),
                         datetime(2003, 9, 25))

    def testDateWithSpace1(self):
        self.assertEqual(parse("2003 09 25"),
                         datetime(2003, 9, 25))

    def testDateWithSpace2(self):
        self.assertEqual(parse("2003 Sep 25"),
                         datetime(2003, 9, 25))

    def testDateWithSpace3(self):
        self.assertEqual(parse("25 Sep 2003"),
                         datetime(2003, 9, 25))

    def testDateWithSpace4(self):
        self.assertEqual(parse("25 Sep 2003"),
                         datetime(2003, 9, 25))

    def testDateWithSpace5(self):
        self.assertEqual(parse("Sep 25 2003"),
                         datetime(2003, 9, 25))

    def testDateWithSpace6(self):
        self.assertEqual(parse("09 25 2003"),
                         datetime(2003, 9, 25))

    def testDateWithSpace7(self):
        self.assertEqual(parse("25 09 2003"),
                         datetime(2003, 9, 25))

    def testDateWithSpace8(self):
        self.assertEqual(parse("10 09 2003", dayfirst=True),
                         datetime(2003, 9, 10))

    def testDateWithSpace9(self):
        self.assertEqual(parse("10 09 2003"),
                         datetime(2003, 10, 9))

    def testDateWithSpace10(self):
        self.assertEqual(parse("10 09 03"),
                         datetime(2003, 10, 9))

    def testDateWithSpace11(self):
        self.assertEqual(parse("10 09 03", yearfirst=True),
                         datetime(2010, 9, 3))

    def testDateWithSpace12(self):
        self.assertEqual(parse("25 09 03"),
                         datetime(2003, 9, 25))

    def testDateWithSpace13(self):
        self.assertEqual(parse("25 09 03"),
                         datetime(2003, 9, 25))

    def testStrangelyOrderedDate1(self):
        self.assertEqual(parse("03 25 Sep"),
                         datetime(2003, 9, 25))

    def testStrangelyOrderedDate2(self):
        self.assertEqual(parse("2003 25 Sep"),
                         datetime(2003, 9, 25))

    def testStrangelyOrderedDate3(self):
        self.assertEqual(parse("25 03 Sep"),
                         datetime(2025, 9, 3))

    def testHourWithLetters(self):
        self.assertEqual(parse("10h36m28.5s", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28, 500000))

    def testHourWithLettersStrip1(self):
        self.assertEqual(parse("10h36m28s", default=self.default),
                         datetime(2003, 9, 25, 10, 36, 28))

    def testHourWithLettersStrip1(self):
        self.assertEqual(parse("10h36m", default=self.default),
                         datetime(2003, 9, 25, 10, 36))

    def testHourWithLettersStrip2(self):
        self.assertEqual(parse("10h", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm1(self):
        self.assertEqual(parse("10h am", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm2(self):
        self.assertEqual(parse("10h pm", default=self.default),
                         datetime(2003, 9, 25, 22))

    def testHourAmPm3(self):
        self.assertEqual(parse("10am", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm4(self):
        self.assertEqual(parse("10pm", default=self.default),
                         datetime(2003, 9, 25, 22))

    def testHourAmPm5(self):
        self.assertEqual(parse("10:00 am", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm6(self):
        self.assertEqual(parse("10:00 pm", default=self.default),
                         datetime(2003, 9, 25, 22))

    def testHourAmPm7(self):
        self.assertEqual(parse("10:00am", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm8(self):
        self.assertEqual(parse("10:00pm", default=self.default),
                         datetime(2003, 9, 25, 22))

    def testHourAmPm9(self):
        self.assertEqual(parse("10:00a.m", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm10(self):
        self.assertEqual(parse("10:00p.m", default=self.default),
                         datetime(2003, 9, 25, 22))

    def testHourAmPm11(self):
        self.assertEqual(parse("10:00a.m.", default=self.default),
                         datetime(2003, 9, 25, 10))

    def testHourAmPm12(self):
        self.assertEqual(parse("10:00p.m.", default=self.default),
                         datetime(2003, 9, 25, 22))

    def testPertain(self):
        self.assertEqual(parse("Sep 03", default=self.default),
                         datetime(2003, 9, 3))
        self.assertEqual(parse("Sep of 03", default=self.default),
                         datetime(2003, 9, 25))

    def testWeekdayAlone(self):
        self.assertEqual(parse("Wed", default=self.default),
                         datetime(2003, 10, 1))

    def testLongWeekday(self):
        self.assertEqual(parse("Wednesday", default=self.default),
                         datetime(2003, 10, 1))

    def testLongMonth(self):
        self.assertEqual(parse("October", default=self.default),
                         datetime(2003, 10, 25))
        
    def testZeroYear(self):
        self.assertEqual(parse("31-Dec-00", default=self.default),
                         datetime(2000, 12, 31))

    def testFuzzy(self):
        s = "Today is 25 of September of 2003, exactly " \
            "at 10:49:41 with timezone -03:00."
        self.assertEqual(parse(s, fuzzy=True),
                         datetime(2003, 9, 25, 10, 49, 41,
                                  tzinfo=self.brsttz))

    def testExtraSpace(self):
        self.assertEqual(parse("  July   4 ,  1976   12:01:02   am  "),
                         datetime(1976, 7, 4, 0, 1, 2))

    def testRandomFormat1(self):
        self.assertEqual(parse("Wed, July 10, '96"),
                         datetime(1996, 7, 10, 0, 0))

    def testRandomFormat2(self):
        self.assertEqual(parse("1996.07.10 AD at 15:08:56 PDT",
                               ignoretz=True),
                         datetime(1996, 7, 10, 15, 8, 56))

    def testRandomFormat3(self):
        self.assertEqual(parse("1996.July.10 AD 12:08 PM"),
                         datetime(1996, 7, 10, 12, 8))

    def testRandomFormat4(self):
        self.assertEqual(parse("Tuesday, April 12, 1952 AD 3:30:42pm PST",
                               ignoretz=True),
                         datetime(1952, 4, 12, 15, 30, 42))

    def testRandomFormat5(self):
        self.assertEqual(parse("November 5, 1994, 8:15:30 am EST",
                               ignoretz=True),
                         datetime(1994, 11, 5, 8, 15, 30))

    def testRandomFormat6(self):
        self.assertEqual(parse("1994-11-05T08:15:30-05:00",
                               ignoretz=True),
                         datetime(1994, 11, 5, 8, 15, 30))

    def testRandomFormat7(self):
        self.assertEqual(parse("1994-11-05T08:15:30Z",
                               ignoretz=True),
                         datetime(1994, 11, 5, 8, 15, 30))

    def testRandomFormat8(self):
        self.assertEqual(parse("July 4, 1976"), datetime(1976, 7, 4))

    def testRandomFormat9(self):
        self.assertEqual(parse("7 4 1976"), datetime(1976, 7, 4))

    def testRandomFormat10(self):
        self.assertEqual(parse("4 jul 1976"), datetime(1976, 7, 4))

    def testRandomFormat11(self):
        self.assertEqual(parse("7-4-76"), datetime(1976, 7, 4))

    def testRandomFormat12(self):
        self.assertEqual(parse("19760704"), datetime(1976, 7, 4))

    def testRandomFormat13(self):
        self.assertEqual(parse("0:01:02", default=self.default),
                         datetime(2003, 9, 25, 0, 1, 2))

    def testRandomFormat14(self):
        self.assertEqual(parse("12h 01m02s am", default=self.default),
                         datetime(2003, 9, 25, 0, 1, 2))

    def testRandomFormat15(self):
        self.assertEqual(parse("0:01:02 on July 4, 1976"),
                         datetime(1976, 7, 4, 0, 1, 2))

    def testRandomFormat16(self):
        self.assertEqual(parse("0:01:02 on July 4, 1976"),
                         datetime(1976, 7, 4, 0, 1, 2))

    def testRandomFormat17(self):
        self.assertEqual(parse("1976-07-04T00:01:02Z", ignoretz=True),
                         datetime(1976, 7, 4, 0, 1, 2))

    def testRandomFormat18(self):
        self.assertEqual(parse("July 4, 1976 12:01:02 am"),
                         datetime(1976, 7, 4, 0, 1, 2))

    def testRandomFormat19(self):
        self.assertEqual(parse("Mon Jan  2 04:24:27 1995"),
                         datetime(1995, 1, 2, 4, 24, 27))

    def testRandomFormat20(self):
        self.assertEqual(parse("Tue Apr 4 00:22:12 PDT 1995", ignoretz=True),
                         datetime(1995, 4, 4, 0, 22, 12))

    def testRandomFormat21(self):
        self.assertEqual(parse("04.04.95 00:22"),
                         datetime(1995, 4, 4, 0, 22))

    def testRandomFormat22(self):
        self.assertEqual(parse("Jan 1 1999 11:23:34.578"),
                         datetime(1999, 1, 1, 11, 23, 34, 578000))

    def testRandomFormat23(self):
        self.assertEqual(parse("950404 122212"),
                         datetime(1995, 4, 4, 12, 22, 12))

    def testRandomFormat24(self):
        self.assertEqual(parse("0:00 PM, PST", default=self.default,
                               ignoretz=True),
                         datetime(2003, 9, 25, 12, 0))

    def testRandomFormat25(self):
        self.assertEqual(parse("12:08 PM", default=self.default),
                         datetime(2003, 9, 25, 12, 8))

    def testRandomFormat26(self):
        self.assertEqual(parse("5:50 A.M. on June 13, 1990"),
                         datetime(1990, 6, 13, 5, 50))

    def testRandomFormat27(self):
        self.assertEqual(parse("3rd of May 2001"), datetime(2001, 5, 3))

    def testRandomFormat28(self):
        self.assertEqual(parse("5th of March 2001"), datetime(2001, 3, 5))

    def testRandomFormat29(self):
        self.assertEqual(parse("1st of May 2003"), datetime(2003, 5, 1))

    def testRandomFormat30(self):
        self.assertEqual(parse("01h02m03", default=self.default),
                         datetime(2003, 9, 25, 1, 2, 3))

    def testRandomFormat31(self):
        self.assertEqual(parse("01h02", default=self.default),
                         datetime(2003, 9, 25, 1, 2))

    def testRandomFormat32(self):
        self.assertEqual(parse("01h02s", default=self.default),
                         datetime(2003, 9, 25, 1, 0, 2))

    def testRandomFormat33(self):
        self.assertEqual(parse("01m02", default=self.default),
                         datetime(2003, 9, 25, 0, 1, 2))

    def testRandomFormat34(self):
        self.assertEqual(parse("01m02h", default=self.default),
                         datetime(2003, 9, 25, 2, 1))

    def testRandomFormat35(self):
        self.assertEqual(parse("2004 10 Apr 11h30m", default=self.default),
                         datetime(2004, 4, 10, 11, 30))

    def testIncreasingCTime(self):
        # This test will check 200 different years, every month, every day,
        # every hour, every minute, every second, and every weekday, using
        # a delta of more or less 1 year, 1 month, 1 day, 1 minute and
        # 1 second.
        delta = timedelta(days=365+31+1, seconds=1+60+60*60)
        dt = datetime(1900, 1, 1, 0, 0, 0, 0)
        for i in range(200):
            self.assertEqual(parse(dt.ctime()), dt)
            dt += delta

    def testIncreasingISOFormat(self):
        delta = timedelta(days=365+31+1, seconds=1+60+60*60)
        dt = datetime(1900, 1, 1, 0, 0, 0, 0)
        for i in range(200):
            self.assertEqual(parse(dt.isoformat()), dt)
            dt += delta

    def testMicrosecondsPrecisionError(self):
        # Skip found out that sad precision problem. :-(
        dt1 = parse("00:11:25.01")
        dt2 = parse("00:12:10.01")
        self.assertEquals(dt1.microsecond, 10000)
        self.assertEquals(dt2.microsecond, 10000)

    def testMicrosecondPrecisionErrorReturns(self):
        # One more precision issue, discovered by Eric Brown.  This should
        # be the last one, as we're no longer using floating points.
        for ms in [100001, 100000, 99999, 99998,
                    10001,  10000,  9999,  9998,
                     1001,   1000,   999,   998,
                      101,    100,    99,    98]:
            dt = datetime(2008, 2, 27, 21, 26, 1, ms)
            self.assertEquals(parse(dt.isoformat()), dt)

    def testHighPrecisionSeconds(self):
        self.assertEquals(parse("20080227T21:26:01.123456789"),
                          datetime(2008, 2, 27, 21, 26, 1, 123456))

    def testCustomParserInfo(self):
        # Custom parser info wasn't working, as Michael ElsdÃ¶rfer discovered.
        from dateutil.parser import parserinfo, parser
        class myparserinfo(parserinfo):
            MONTHS = parserinfo.MONTHS[:]
            MONTHS[0] = ("Foo", "Foo")
        myparser = parser(myparserinfo())
        dt = myparser.parse("01/Foo/2007")
        self.assertEquals(dt, datetime(2007, 1, 1))


class EasterTest(unittest.TestCase):
    easterlist = [
                 # WESTERN            ORTHODOX
                  (date(1990, 4, 15), date(1990, 4, 15)),
                  (date(1991, 3, 31), date(1991, 4,  7)),
                  (date(1992, 4, 19), date(1992, 4, 26)),
                  (date(1993, 4, 11), date(1993, 4, 18)),
                  (date(1994, 4,  3), date(1994, 5,  1)),
                  (date(1995, 4, 16), date(1995, 4, 23)),
                  (date(1996, 4,  7), date(1996, 4, 14)),
                  (date(1997, 3, 30), date(1997, 4, 27)),
                  (date(1998, 4, 12), date(1998, 4, 19)),
                  (date(1999, 4,  4), date(1999, 4, 11)),

                  (date(2000, 4, 23), date(2000, 4, 30)),
                  (date(2001, 4, 15), date(2001, 4, 15)),
                  (date(2002, 3, 31), date(2002, 5,  5)),
                  (date(2003, 4, 20), date(2003, 4, 27)),
                  (date(2004, 4, 11), date(2004, 4, 11)),
                  (date(2005, 3, 27), date(2005, 5,  1)),
                  (date(2006, 4, 16), date(2006, 4, 23)),
                  (date(2007, 4,  8), date(2007, 4,  8)),
                  (date(2008, 3, 23), date(2008, 4, 27)),
                  (date(2009, 4, 12), date(2009, 4, 19)),

                  (date(2010, 4,  4), date(2010, 4,  4)),
                  (date(2011, 4, 24), date(2011, 4, 24)),
                  (date(2012, 4,  8), date(2012, 4, 15)),
                  (date(2013, 3, 31), date(2013, 5,  5)),
                  (date(2014, 4, 20), date(2014, 4, 20)),
                  (date(2015, 4,  5), date(2015, 4, 12)),
                  (date(2016, 3, 27), date(2016, 5,  1)),
                  (date(2017, 4, 16), date(2017, 4, 16)),
                  (date(2018, 4,  1), date(2018, 4,  8)),
                  (date(2019, 4, 21), date(2019, 4, 28)),

                  (date(2020, 4, 12), date(2020, 4, 19)),
                  (date(2021, 4,  4), date(2021, 5,  2)),
                  (date(2022, 4, 17), date(2022, 4, 24)),
                  (date(2023, 4,  9), date(2023, 4, 16)),
                  (date(2024, 3, 31), date(2024, 5,  5)),
                  (date(2025, 4, 20), date(2025, 4, 20)),
                  (date(2026, 4,  5), date(2026, 4, 12)),
                  (date(2027, 3, 28), date(2027, 5,  2)),
                  (date(2028, 4, 16), date(2028, 4, 16)),
                  (date(2029, 4,  1), date(2029, 4,  8)),

                  (date(2030, 4, 21), date(2030, 4, 28)),
                  (date(2031, 4, 13), date(2031, 4, 13)),
                  (date(2032, 3, 28), date(2032, 5,  2)),
                  (date(2033, 4, 17), date(2033, 4, 24)),
                  (date(2034, 4,  9), date(2034, 4,  9)),
                  (date(2035, 3, 25), date(2035, 4, 29)),
                  (date(2036, 4, 13), date(2036, 4, 20)),
                  (date(2037, 4,  5), date(2037, 4,  5)),
                  (date(2038, 4, 25), date(2038, 4, 25)),
                  (date(2039, 4, 10), date(2039, 4, 17)),

                  (date(2040, 4,  1), date(2040, 5,  6)),
                  (date(2041, 4, 21), date(2041, 4, 21)),
                  (date(2042, 4,  6), date(2042, 4, 13)),
                  (date(2043, 3, 29), date(2043, 5,  3)),
                  (date(2044, 4, 17), date(2044, 4, 24)),
                  (date(2045, 4,  9), date(2045, 4,  9)),
                  (date(2046, 3, 25), date(2046, 4, 29)),
                  (date(2047, 4, 14), date(2047, 4, 21)),
                  (date(2048, 4,  5), date(2048, 4,  5)),
                  (date(2049, 4, 18), date(2049, 4, 25)),

                  (date(2050, 4, 10), date(2050, 4, 17)),
                ]

    def testEaster(self):
        for western, orthodox in self.easterlist:
            self.assertEqual(western,  easter(western.year,  EASTER_WESTERN))
            self.assertEqual(orthodox, easter(orthodox.year, EASTER_ORTHODOX))

class TZTest(unittest.TestCase):

    TZFILE_EST5EDT = """
VFppZgAAAAAAAAAAAAAAAAAAAAAAAAAEAAAABAAAAAAAAADrAAAABAAAABCeph5wn7rrYKCGAHCh
ms1gomXicKOD6eCkaq5wpTWnYKZTyvCnFYlgqDOs8Kj+peCqE47wqt6H4KvzcPCsvmngrdNS8K6e
S+CvszTwsH4t4LGcUXCyZ0pgs3wzcLRHLGC1XBVwticOYLc793C4BvBguRvZcLnm0mC7BPXwu8a0
YLzk1/C9r9DgvsS58L+PsuDApJvwwW+U4MKEffDDT3bgxGRf8MUvWODGTXxwxw864MgtXnDI+Fdg
yg1AcMrYOWDLiPBw0iP0cNJg++DTdeTw1EDd4NVVxvDWIL/g1zWo8NgAoeDZFYrw2eCD4Nr+p3Db
wGXg3N6JcN2pgmDevmtw34lkYOCeTXDhaUZg4n4vcONJKGDkXhFw5Vcu4OZHLfDnNxDg6CcP8OkW
8uDqBvHw6vbU4Ovm0/Ds1rbg7ca18O6/02Dvr9Jw8J+1YPGPtHDyf5dg82+WcPRfeWD1T3hw9j9b
YPcvWnD4KHfg+Q88cPoIWeD6+Fjw++g74PzYOvD9yB3g/rgc8P+n/+AAl/7wAYfh4AJ34PADcP5g
BGD9cAVQ4GAGQN9wBzDCYAeNGXAJEKRgCa2U8ArwhmAL4IVwDNmi4A3AZ3AOuYTgD6mD8BCZZuAR
iWXwEnlI4BNpR/AUWSrgFUkp8BY5DOAXKQvwGCIpYBkI7fAaAgtgGvIKcBvh7WAc0exwHcHPYB6x
znAfobFgIHYA8CGBk2AiVeLwI2qv4CQ1xPAlSpHgJhWm8Ccqc+An/sNwKQpV4CnepXAq6jfgK76H
cCzTVGAtnmlwLrM2YC9+S3AwkxhgMWdn8DJy+mAzR0nwNFLcYDUnK/A2Mr5gNwcN8Dgb2uA45u/w
Ofu84DrG0fA7257gPK/ucD27gOA+j9BwP5ti4EBvsnBBhH9gQk+UcENkYWBEL3ZwRURDYEYPWHBH
JCVgR/h08EkEB2BJ2FbwSuPpYEu4OPBMzQXgTZga8E6s5+BPd/zwUIzJ4FFhGXBSbKvgU0D7cFRM
jeBVIN1wVixv4FcAv3BYFYxgWOChcFn1bmBawINwW9VQYFypn/BdtTJgXomB8F+VFGBgaWPwYX4w
4GJJRfBjXhLgZCkn8GU99OBmEkRwZx3W4GfyJnBo/bjgadIIcGrdmuBrsepwbMa3YG2RzHBupplg
b3GucHCGe2BxWsrwcmZdYHM6rPB0Rj9gdRqO8HYvW+B2+nDweA894HjaUvB57x/gero08HvPAeB8
o1Fwfa7j4H6DM3B/jsXgAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAB
AAEAAQABAgMBAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAB
AAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEA
AQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAB
AAEAAQABAAEAAQABAAEAAQABAAEAAf//x8ABAP//ubAABP//x8ABCP//x8ABDEVEVABFU1QARVdU
AEVQVAAAAAABAAAAAQ==
    """

    EUROPE_HELSINKI = """
VFppZgAAAAAAAAAAAAAAAAAAAAAAAAAFAAAABQAAAAAAAAB1AAAABQAAAA2kc28Yy85RYMy/hdAV
I+uQFhPckBcDzZAX876QGOOvkBnToJAaw5GQG7y9EBysrhAdnJ8QHoyQEB98gRAgbHIQIVxjECJM
VBAjPEUQJCw2ECUcJxAmDBgQJwVDkCf1NJAo5SWQKdUWkCrFB5ArtPiQLKTpkC2U2pAuhMuQL3S8
kDBkrZAxXdkQMnK0EDM9uxA0UpYQNR2dEDYyeBA2/X8QOBuUkDjdYRA5+3aQOr1DEDvbWJA8pl+Q
Pbs6kD6GQZA/mxyQQGYjkEGEORBCRgWQQ2QbEEQl55BFQ/0QRgXJkEcj3xBH7uYQSQPBEEnOyBBK
46MQS66qEEzMv5BNjowQTqyhkE9ubhBQjIOQUVeKkFJsZZBTN2yQVExHkFUXTpBWLCmQVvcwkFgV
RhBY1xKQWfUoEFq29JBb1QoQXKAREF207BBef/MQX5TOEGBf1RBhfeqQYj+3EGNdzJBkH5kQZT2u
kGYItZBnHZCQZ+iXkGj9cpBpyHmQat1UkGuoW5BsxnEQbYg9kG6mUxBvaB+QcIY1EHFRPBByZhcQ
czEeEHRF+RB1EQAQdi8VkHbw4hB4DveQeNDEEHnu2ZB6sKYQe867kHyZwpB9rp2QfnmkkH+Of5AC
AQIDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQD
BAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAMEAwQDBAME
AwQAABdoAAAAACowAQQAABwgAAkAACowAQQAABwgAAlITVQARUVTVABFRVQAAAAAAQEAAAABAQ==
    """

    NEW_YORK = """
VFppZgAAAAAAAAAAAAAAAAAAAAAAAAAEAAAABAAAABcAAADrAAAABAAAABCeph5wn7rrYKCGAHCh
ms1gomXicKOD6eCkaq5wpTWnYKZTyvCnFYlgqDOs8Kj+peCqE47wqt6H4KvzcPCsvmngrdNS8K6e
S+CvszTwsH4t4LGcUXCyZ0pgs3wzcLRHLGC1XBVwticOYLc793C4BvBguRvZcLnm0mC7BPXwu8a0
YLzk1/C9r9DgvsS58L+PsuDApJvwwW+U4MKEffDDT3bgxGRf8MUvWODGTXxwxw864MgtXnDI+Fdg
yg1AcMrYOWDLiPBw0iP0cNJg++DTdeTw1EDd4NVVxvDWIL/g1zWo8NgAoeDZFYrw2eCD4Nr+p3Db
wGXg3N6JcN2pgmDevmtw34lkYOCeTXDhaUZg4n4vcONJKGDkXhFw5Vcu4OZHLfDnNxDg6CcP8OkW
8uDqBvHw6vbU4Ovm0/Ds1rbg7ca18O6/02Dvr9Jw8J+1YPGPtHDyf5dg82+WcPRfeWD1T3hw9j9b
YPcvWnD4KHfg+Q88cPoIWeD6+Fjw++g74PzYOvD9yB3g/rgc8P+n/+AAl/7wAYfh4AJ34PADcP5g
BGD9cAVQ4GEGQN9yBzDCYgeNGXMJEKRjCa2U9ArwhmQL4IV1DNmi5Q3AZ3YOuYTmD6mD9xCZZucR
iWX4EnlI6BNpR/kUWSrpFUkp+RY5DOoXKQv6GCIpaxkI7fsaAgtsGvIKfBvh7Wwc0ex8HcHPbR6x
zn0fobFtIHYA/SGBk20iVeL+I2qv7iQ1xP4lSpHuJhWm/ycqc+8n/sOAKQpV8CnepYAq6jfxK76H
gSzTVHItnmmCLrM2cy9+S4MwkxhzMWdoBDJy+nQzR0oENFLcdTUnLAU2Mr51NwcOBjgb2vY45vAG
Ofu89jrG0gY72572PK/uhj27gPY+j9CGP5ti9kBvsoZBhH92Qk+UhkNkYXZEL3aHRURDd0XzqQdH
LV/3R9OLB0kNQfdJs20HSu0j90uciYdM1kB3TXxrh062IndPXE2HUJYEd1E8L4dSdeZ3UxwRh1RV
yHdU+/OHVjWqd1blEAdYHsb3WMTyB1n+qPdapNQHW96K91yEtgddvmz3XmSYB1+eTvdgTbSHYYdr
d2ItlodjZ013ZA14h2VHL3dl7VqHZycRd2fNPIdpBvN3aa0eh2rm1XdrljsHbM/x9212HQdur9P3
b1X/B3CPtfdxNeEHcm+X93MVwwd0T3n3dP7fh3Y4lnd23sGHeBh4d3i+o4d5+Fp3ep6Fh3vYPHd8
fmeHfbged35eSYd/mAB3AAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAB
AAEAAQABAgMBAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAB
AAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEA
AQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQABAAEAAQAB
AAEAAQABAAEAAQABAAEAAQABAAEAAf//x8ABAP//ubAABP//x8ABCP//x8ABDEVEVABFU1QARVdU
AEVQVAAEslgAAAAAAQWk7AEAAAACB4YfggAAAAMJZ1MDAAAABAtIhoQAAAAFDSsLhQAAAAYPDD8G
AAAABxDtcocAAAAIEs6mCAAAAAkVn8qJAAAACheA/goAAAALGWIxiwAAAAwdJeoMAAAADSHa5Q0A
AAAOJZ6djgAAAA8nf9EPAAAAECpQ9ZAAAAARLDIpEQAAABIuE1ySAAAAEzDnJBMAAAAUM7hIlAAA
ABU2jBAVAAAAFkO3G5YAAAAXAAAAAQAAAAE=
    """

    _template = """
BEGIN:VTIMEZONE
TZID{0}:US-Eastern
X-MUMBLE:Once upon a time ...
LAST-MODIFIED:19870101T000000Z
TZURL:http://zones.stds_r_us.net/tz/US-Eastern
BEGIN:STANDARD
X-FOO:Fu
DTSTART:19671029T020000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
TZNAME:EST
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19870405T020000
RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=4
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
TZNAME:EDT
END:DAYLIGHT
END:VTIMEZONE
    """

    TZICAL_EST5EDT=_template.format('')
    TZICAL_EST5EDT_X_DASH_ATTRIBUTE=_template.format(';X-WOO-HOO=frotzplotz')
    TZICAL_EST5EDT_UTTERLY_GOOFY_ATTRIBUTE=_template.format(';SNORK=BORK')
    
    def testStrStart1(self):
        self.assertEqual(datetime(2003,4,6,1,59,
                                  tzinfo=tzstr("EST5EDT")).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,
                                  tzinfo=tzstr("EST5EDT")).tzname(), "EDT")

    def testStrEnd1(self):
        self.assertEqual(datetime(2003,10,26,0,59,
                                  tzinfo=tzstr("EST5EDT")).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,
                                  tzinfo=tzstr("EST5EDT")).tzname(), "EST")

    def testStrStart2(self):
        s = "EST5EDT,4,0,6,7200,10,0,26,7200,3600"
        self.assertEqual(datetime(2003,4,6,1,59,
                                  tzinfo=tzstr(s)).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,
                                  tzinfo=tzstr(s)).tzname(), "EDT")

    def testStrEnd2(self):
        s = "EST5EDT,4,0,6,7200,10,0,26,7200,3600"
        self.assertEqual(datetime(2003,10,26,0,59,
                                  tzinfo=tzstr(s)).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,
                                  tzinfo=tzstr(s)).tzname(), "EST")

    def testStrStart3(self):
        s = "EST5EDT,4,1,0,7200,10,-1,0,7200,3600"
        self.assertEqual(datetime(2003,4,6,1,59,
                                  tzinfo=tzstr(s)).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,
                                  tzinfo=tzstr(s)).tzname(), "EDT")

    def testStrEnd3(self):
        s = "EST5EDT,4,1,0,7200,10,-1,0,7200,3600"
        self.assertEqual(datetime(2003,10,26,0,59,
                                  tzinfo=tzstr(s)).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,
                                  tzinfo=tzstr(s)).tzname(), "EST")

    def testStrStart4(self):
        s = "EST5EDT4,M4.1.0/02:00:00,M10-5-0/02:00"
        self.assertEqual(datetime(2003,4,6,1,59,
                                  tzinfo=tzstr(s)).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,
                                  tzinfo=tzstr(s)).tzname(), "EDT")

    def testStrEnd4(self):
        s = "EST5EDT4,M4.1.0/02:00:00,M10-5-0/02:00"
        self.assertEqual(datetime(2003,10,26,0,59,
                                  tzinfo=tzstr(s)).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,
                                  tzinfo=tzstr(s)).tzname(), "EST")

    def testStrStart5(self):
        s = "EST5EDT4,95/02:00:00,298/02:00"
        self.assertEqual(datetime(2003,4,6,1,59,
                                  tzinfo=tzstr(s)).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,
                                  tzinfo=tzstr(s)).tzname(), "EDT")

    def testStrEnd5(self):
        s = "EST5EDT4,95/02:00:00,298/02"
        self.assertEqual(datetime(2003,10,26,0,59,
                                  tzinfo=tzstr(s)).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,
                                  tzinfo=tzstr(s)).tzname(), "EST")

    def testStrStart6(self):
        s = "EST5EDT4,J96/02:00:00,J299/02:00"
        self.assertEqual(datetime(2003,4,6,1,59,
                                  tzinfo=tzstr(s)).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,
                                  tzinfo=tzstr(s)).tzname(), "EDT")

    def testStrEnd6(self):
        s = "EST5EDT4,J96/02:00:00,J299/02"
        self.assertEqual(datetime(2003,10,26,0,59,
                                  tzinfo=tzstr(s)).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,
                                  tzinfo=tzstr(s)).tzname(), "EST")

    def testStrCmp1(self):
        self.assertEqual(tzstr("EST5EDT"),
                         tzstr("EST5EDT4,M4.1.0/02:00:00,M10-5-0/02:00"))
        
    def testStrCmp2(self):
        self.assertEqual(tzstr("EST5EDT"),
                         tzstr("EST5EDT,4,1,0,7200,10,-1,0,7200,3600"))

    def testRangeCmp1(self):
        self.assertEqual(tzstr("EST5EDT"),
                         tzrange("EST", -18000, "EDT", -14400,
                                 relativedelta(hours=+2,
                                               month=4, day=1,
                                               weekday=SU(+1)),
                                 relativedelta(hours=+1,
                                               month=10, day=31,
                                               weekday=SU(-1))))

    def testRangeCmp2(self):
        self.assertEqual(tzstr("EST5EDT"),
                         tzrange("EST", -18000, "EDT"))

    def testFileStart1(self):
        tz = tzfile(StringIO(base64.decodestring(self.TZFILE_EST5EDT)))
        self.assertEqual(datetime(2003,4,6,1,59,tzinfo=tz).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,tzinfo=tz).tzname(), "EDT")
        
    def testFileEnd1(self):
        tz = tzfile(StringIO(base64.decodestring(self.TZFILE_EST5EDT)))
        self.assertEqual(datetime(2003,10,26,0,59,tzinfo=tz).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,tzinfo=tz).tzname(), "EST")

    def testZoneInfoFileStart1(self):
        tz = zoneinfo.gettz("EST5EDT")
        self.assertEqual(datetime(2003,4,6,1,59,tzinfo=tz).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,tzinfo=tz).tzname(), "EDT")

    def testZoneInfoFileEnd1(self):
        tz = zoneinfo.gettz("EST5EDT")
        self.assertEqual(datetime(2003,10,26,0,59,tzinfo=tz).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,tzinfo=tz).tzname(), "EST")

    def testZoneInfoOffsetSignal(self):
        utc = gettz("UTC")
        nyc = zoneinfo.gettz("America/New_York")
        t0 = datetime(2007,11,4,0,30, tzinfo=nyc)
        t1 = t0.astimezone(utc)
        t2 = t1.astimezone(nyc)
        self.assertEquals(t0, t2)
        self.assertEquals(nyc.dst(t0), timedelta(hours=1))

    def testICalUnfolding(self):
        """
        Just making sure we don't barf while unfolding.
        """
        for string in ("ho: hum\r\n frotz", "ho: hum\r\n\tfrotz"):
            tz = tzical(StringIO(string))
            self.assertEqual(dict(), tz._vtz)

    def testICalStart1(self):
        tz = tzical(StringIO(self.TZICAL_EST5EDT)).get()
        self.assertEqual(datetime(2003,4,6,1,59,tzinfo=tz).tzname(), "EST")
        self.assertEqual(datetime(2003,4,6,2,00,tzinfo=tz).tzname(), "EDT")

    def testICalEnd1(self):
        tz = tzical(StringIO(self.TZICAL_EST5EDT)).get()
        self.assertEqual(datetime(2003,10,26,0,59,tzinfo=tz).tzname(), "EDT")
        self.assertEqual(datetime(2003,10,26,1,00,tzinfo=tz).tzname(), "EST")

    def testIgnoresGoofyAttribute(self):
        tz = tzical(StringIO(self.TZICAL_EST5EDT_X_DASH_ATTRIBUTE)).get()
        self.assertEqual(datetime(2003,10,26,0,59,tzinfo=tz).tzname(), "EDT")

        self.assertRaises(ValueError, tzical, StringIO(self.TZICAL_EST5EDT_UTTERLY_GOOFY_ATTRIBUTE))

    def testRoundNonFullMinutes(self):
        # This timezone has an offset of 5992 seconds in 1900-01-01.
        tz = tzfile(StringIO(base64.decodestring(self.EUROPE_HELSINKI)))
        self.assertEquals(str(datetime(1900,1,1,0,0, tzinfo=tz)),
                          "1900-01-01 00:00:00+01:40")

    def testLeapCountDecodesProperly(self):
        # This timezone has leapcnt, and failed to decode until
        # Eugene Oden notified about the issue.
        tz = tzfile(StringIO(base64.decodestring(self.NEW_YORK)))
        self.assertEquals(datetime(2007,3,31,20,12).tzname(), None)

    def testBrokenIsDstHandling(self):
        # tzrange._isdst() was using a date() rather than a datetime().
        # Issue reported by Lennart Regebro.
        dt = datetime(2007,8,6,4,10, tzinfo=tzutc())
        self.assertEquals(dt.astimezone(tz=gettz("GMT+2")),
                          datetime(2007,8,6,6,10, tzinfo=tzstr("GMT+2")))

    def testGMTHasNoDaylight(self):
        # tzstr("GMT+2") improperly considered daylight saving time.
        # Issue reported by Lennart Regebro.
        dt = datetime(2007,8,6,4,10)
        self.assertEquals(gettz("GMT+2").dst(dt), timedelta(0))

    def testGMTOffset(self):
        # GMT and UTC offsets have inverted signal when compared to the
        # usual TZ variable handling.
        dt = datetime(2007,8,6,4,10, tzinfo=tzutc())
        self.assertEquals(dt.astimezone(tz=tzstr("GMT+2")),
                          datetime(2007,8,6,6,10, tzinfo=tzstr("GMT+2")))
        self.assertEquals(dt.astimezone(tz=gettz("UTC-2")),
                          datetime(2007,8,6,2,10, tzinfo=tzstr("UTC-2")))


if __name__ == "__main__":
	unittest.main()

# vim:ts=4:sw=4

########NEW FILE########
__FILENAME__ = updatezinfo
#!/usr/bin/python
from dateutil.zoneinfo import rebuild
import shutil
import sys
import os
import re

SERVER = "ftp.iana.org"
DIR = "/tz"
NAME = re.compile("tzdata(.*).tar.gz")

def main():
    if len(sys.argv) == 2:
        tzdata = sys.argv[1]
    else:
        from ftplib import FTP
        print "Connecting to %s..." % SERVER
        ftp = FTP(SERVER)
        print "Logging in..."
        ftp.login()
        print "Changing to %s..." % DIR
        ftp.cwd(DIR)
        print "Listing files..."
        for name in ftp.nlst():
            if NAME.match(name):
                break
        else:
            sys.exit("error: file matching %s not found" % NAME.pattern)
        if os.path.isfile(name):
            print "Found local %s..." % name
        else:
            print "Retrieving %s..." % name
            file = open(name, "w")
            ftp.retrbinary("RETR "+name, file.write)
            file.close()
        ftp.close()
        tzdata = name
    if not tzdata or not NAME.match(tzdata):
        sys.exit("Usage: updatezinfo.py tzdataXXXXX.tar.gz")
    print "Updating timezone information..."
    rebuild(tzdata, NAME.match(tzdata).group(1))
    print "Done."

if __name__ == "__main__":
    main()

########NEW FILE########
