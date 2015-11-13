__FILENAME__ = easter
"""
Copyright (c) 2003-2005  Gustavo Niemeyer <gustavo@niemeyer.net>

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
        j = (y+y/4+i)%7
        if method == 2:
            # Extra dates to convert Julian to Gregorian date
            e = 10
            if y > 1600:
                e = e+y/100-16-(y/100-16)/4
    else:
        # New method
        c = y/100
        h = (c-c/4-(8*c+13)/25+19*g+15)%30
        i = h-(h/28)*(1-(h/28)*(29/(h+1))*((21-g)/11))
        j = (y+y/4+i+2-c+c/4)%7

    # p can be from -6 to 56 corresponding to dates 22 March to 23 May
    # (later dates apply to method 2, although 23 May never actually occurs)
    p = i-j+e
    d = 1+(p+27+(p+6)/40)%31
    m = 3+(p+26)/30
    return datetime.date(y,m,d)


########NEW FILE########
__FILENAME__ = parser
# -*- coding:iso-8859-1 -*-
"""
Copyright (c) 2003-2005  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import os.path
import string
import sys
import time

import datetime
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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class _timelex:
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

class parserinfo:

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
        self._century = self._year/100*100

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


class parser:

    def __init__(self, info=parserinfo):
        if issubclass(info, parserinfo):
            self.info = parserinfo()
        elif isinstance(info, parserinfo):
            self.info = info
        else:
            raise TypeError, "Unsupported parserinfo type"

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
                    value = float(l[i])
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
                            value = float(s[4:])
                            res.second = int(value)
                            if value%1:
                                res.microsecond = int(1000000*(value%1))
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
                                res.second = int(value)
                                if value%1:
                                    res.microsecond = int(1000000*(value%1))
                            i += 1
                            if i >= len_l or idx == 2:
                                break
                            # 12h00
                            try:
                                value = float(l[i])
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
                            value = float(l[i+1])
                            res.second = int(value)
                            if value%1:
                                res.microsecond = int(1000000*(value%1))
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

class _tzparser:

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

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = relativedelta
"""
Copyright (c) 2003-2005  Gustavo Niemeyer <gustavo@niemeyer.net>

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
                            self.day = ydays
                        else:
                            self.day = yday-ydayidx[idx-1]
                        break
                else:
                    raise ValueError, "invalid year day (%d)" % yday

        self._fix()

    def _fix(self):
        if abs(self.microseconds) > 999999:
            s = self.microseconds/abs(self.microseconds)
            div, mod = divmod(self.microseconds*s, 1000000)
            self.microseconds = mod*s
            self.seconds += div*s
        if abs(self.seconds) > 59:
            s = self.seconds/abs(self.seconds)
            div, mod = divmod(self.seconds*s, 60)
            self.seconds = mod*s
            self.minutes += div*s
        if abs(self.minutes) > 59:
            s = self.minutes/abs(self.minutes)
            div, mod = divmod(self.minutes*s, 60)
            self.minutes = mod*s
            self.hours += div*s
        if abs(self.hours) > 23:
            s = self.hours/abs(self.hours)
            div, mod = divmod(self.hours*s, 24)
            self.hours = mod*s
            self.days += div*s
        if abs(self.months) > 11:
            s = self.months/abs(self.months)
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
            s = self.months/abs(self.months)
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
        return relativedelta(years=self.years*f,
                             months=self.months*f,
                             days=self.days*f,
                             hours=self.hours*f,
                             minutes=self.minutes*f,
                             seconds=self.seconds*f,
                             microseconds=self.microseconds*f,
                             leapdays=self.leapdays,
                             year=self.year,
                             month=self.month,
                             day=self.day,
                             weekday=self.weekday,
                             hour=self.hour,
                             minute=self.minute,
                             second=self.second,
                             microsecond=self.microsecond)

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
Copyright (c) 2003-2005  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import itertools
import datetime
import calendar
import thread
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
                 self._bysecond and minute not in self._bysecond)):
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
                self.genlist.remove(self)

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
        rlist.sort()
        exlist = []
        self._exdate.sort()
        self._genitem(exlist, iter(self._exdate).next)
        for gen in [iter(x).next for x in self._exrule]:
            self._genitem(exlist, gen)
        exlist.sort()
        lastdt = None
        total = 0
        while rlist:
            ritem = rlist[0]
            if not lastdt or lastdt != ritem.dt:
                while exlist and exlist[0] < ritem:
                    exlist[0].next()
                    exlist.sort()
                if not exlist or ritem != exlist[0]:
                    total += 1
                    yield ritem.dt
                lastdt = ritem.dt
            ritem.next()
            rlist.sort()
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
                elif i > 0 and line[0] == " ":
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
Copyright (c) 2003-2005  Gustavo Niemeyer <gustavo@niemeyer.net>

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
        return self._find_ttinfo(dt, laststd=1).delta-tti.delta

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
        if start is None:
            self._start_delta = relativedelta.relativedelta(
                    hours=+2, month=4, day=1, weekday=relativedelta.SU(+1))
        else:
            self._start_delta = start
        if end is None:
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
        year = datetime.date(dt.year,1,1)
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

        # We must initialize it first, since _delta() needs
        # _std_offset and _dst_offset set. Use False in start/end
        # to avoid building it two times.
        tzrange.__init__(self, res.stdabbr, res.stdoffset,
                         res.dstabbr, res.dstoffset,
                         start=False, end=False)

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
            elif i > 0 and line[0] == " ":
                lines[i-1] += line[1:]
                del lines[i]
            else:
                i += 1

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
                    else:
                        raise ValueError, "unsupported property: "+name
                else:
                    if name == "TZID":
                        if parms:
                            raise ValueError, \
                                  "unsupported TZID parm: "+parms[0]
                        tzid = value
                    elif name in ("TZURL", "LAST-MODIFIED", "COMMENT"):
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
__FILENAME__ = context_processors
from django.conf import settings


def site_info(request):
    return {'APP_NAME': settings.APP_NAME,
            'DOMAIN_URL': settings.DOMAIN_URL,
            'SECURE_DOMAIN_URL': settings.SECURE_DOMAIN_URL,
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
            'ADMIN_NAME': settings.ADMIN_NAME,
            'DEBUG': settings.DEBUG}

########NEW FILE########
__FILENAME__ = dateutils
from pytz import timezone

def get_timezone_for_gmt_offset(gmtoffset):
    if "GMT-5" in gmtoffset:
        return timezone('US/Eastern')
    elif "GMT-8" in gmtoffset:
        return timezone('US/Pacific')
    elif "GMT+0" in gmtoffset:
        return timezone("Europe/London")
    else:
        return timezone('US/Eastern')
########NEW FILE########
__FILENAME__ = html
#-*-coding:utf-8-*-
import htmlentitydefs
import re


def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                if text[1:-1] == "nbsp":
                    text = " "
                else:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)

########NEW FILE########
__FILENAME__ = http
import logging

try:
    from google.appengine.api.urlfetch import fetch as urlfetch_fetch
except ImportError:
    logging.warn("There's no Appengine UrlFetch")

    def urlfetch_fetch(url, deadline=10):  # noqa
        import httplib
        url = url[len("http://"):]
        conn = httplib.HTTPConnection(url[:url.find("/")])
        conn.request("GET", url[url.find("/"):])
        response = conn.getresponse()
        print response.status, response.reason
        data = response.read()
        return data


def get(url):
    response = urlfetch_fetch(url, deadline=10)
    if hasattr(response, 'status_code'):
        if response.status_code != 200:
            raise IOError
        return response.content
    else:
        return response


def post(url, content):
    return urlfetch_fetch(
        url,
        payload=content,
        method="POST",
        follow_redirects=True
    )

########NEW FILE########
__FILENAME__ = string_utils
import re


def normalize(s):
    s = re.sub(r"\(\d{4}\)$", "", s)
    return re.sub("[^\w ]", "", s.lower())

########NEW FILE########
__FILENAME__ = main
import logging
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Force sys.path to have our own directory first, in case we want to import
# from it.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Must set this env var *before* importing any part of Django

# import django.db
import django.core.signals
import django.dispatch
import django.core.handlers.wsgi


def log_exception(sender, **kwargs):
    if 'request' in kwargs:
        try:
            repr_request = repr(kwargs['request'])
        except:
            repr_request = 'Request repr() not available.'
    else:
        repr_request = 'Request not available.'
    if logging is not None:
        logging.exception("Request: %s" % repr_request)


django.dispatch.Signal.connect(
    django.core.signals.got_request_exception, log_exception)

# django.dispatch.Signal.disconnect(
#     django.core.signals.got_request_exception,
#     django.db._rollback_on_exception)


app = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = reference
'''
Reference tzinfo implementations from the Python docs.
Used for testing against as they are only correct for the years
1987 to 2006. Do not use these for real code.
'''

from datetime import tzinfo, timedelta, datetime
from pytz import utc, UTC, HOUR, ZERO

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()

# A complete implementation of current DST rules for major US time zones.

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt

# In the US, DST starts at 2am (standard time) on the first Sunday in April.
DSTSTART = datetime(1, 4, 1, 2)
# and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
# which is the first Sunday on or after Oct 25.
DSTEND = datetime(1, 10, 25, 1)

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = first_sunday_on_or_after(DSTSTART.replace(year=dt.year))
        end = first_sunday_on_or_after(DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")


########NEW FILE########
__FILENAME__ = test_docs
# -*- coding: ascii -*-

import unittest, os, os.path, sys
from doctest import DocTestSuite

# We test the documentation this way instead of using DocFileSuite so
# we can run the tests under Python 2.3
def test_README():
    pass

this_dir = os.path.dirname(__file__)
locs = [
    os.path.join(this_dir, os.pardir, 'README.txt'),
    os.path.join(this_dir, os.pardir, os.pardir, 'README.txt'),
    ]
for loc in locs:
    if os.path.exists(loc):
        test_README.__doc__ = open(loc).read()
        break
if test_README.__doc__ is None:
    raise RuntimeError('README.txt not found')


def test_suite():
    "For the Z3 test runner"
    return DocTestSuite()


if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath(os.path.join(
        this_dir, os.pardir, os.pardir
        )))
    unittest.main(defaultTest='test_suite')



########NEW FILE########
__FILENAME__ = test_tzinfo
# -*- coding: ascii -*-

import sys, os, os.path
import unittest, doctest
import cPickle as pickle
from datetime import datetime, tzinfo, timedelta

if __name__ == '__main__':
    # Only munge path if invoked as a script. Testrunners should have setup
    # the paths already
    sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, os.pardir)))

import pytz
from pytz import reference

# I test for expected version to ensure the correct version of pytz is
# actually being tested.
EXPECTED_VERSION='2009r'

fmt = '%Y-%m-%d %H:%M:%S %Z%z'

NOTIME = timedelta(0)

# GMT is a tzinfo.StaticTzInfo--the class we primarily want to test--while
# UTC is reference implementation.  They both have the same timezone meaning.
UTC = pytz.timezone('UTC')
GMT = pytz.timezone('GMT')


def prettydt(dt):
    """datetime as a string using a known format.

    We don't use strftime as it doesn't handle years earlier than 1900
    per http://bugs.python.org/issue1777412
    """
    if dt.utcoffset() >= timedelta(0):
        offset = '+%s' % (dt.utcoffset(),)
    else:
        offset = '-%s' % (-1 * dt.utcoffset(),)
    return '%04d-%02d-%02d %02d:%02d:%02d %s %s' % (
        dt.year, dt.month, dt.day,
        dt.hour, dt.minute, dt.second,
        dt.tzname(), offset)

class BasicTest(unittest.TestCase):

    def testVersion(self):
        # Ensuring the correct version of pytz has been loaded
        self.failUnlessEqual(EXPECTED_VERSION, pytz.__version__,
                'Incorrect pytz version loaded. Import path is stuffed '
                'or this test needs updating. (Wanted %s, got %s)'
                % (EXPECTED_VERSION, pytz.__version__)
                )

    def testGMT(self):
        now = datetime.now(tz=GMT)
        self.failUnless(now.utcoffset() == NOTIME)
        self.failUnless(now.dst() == NOTIME)
        self.failUnless(now.timetuple() == now.utctimetuple())
        self.failUnless(now==now.replace(tzinfo=UTC))

    def testReferenceUTC(self):
        now = datetime.now(tz=UTC)
        self.failUnless(now.utcoffset() == NOTIME)
        self.failUnless(now.dst() == NOTIME)
        self.failUnless(now.timetuple() == now.utctimetuple())


class PicklingTest(unittest.TestCase):

    def _roundtrip_tzinfo(self, tz):
        p = pickle.dumps(tz)
        unpickled_tz = pickle.loads(p)
        self.failUnless(tz is unpickled_tz, '%s did not roundtrip' % tz.zone)

    def _roundtrip_datetime(self, dt):
        # Ensure that the tzinfo attached to a datetime instance
        # is identical to the one returned. This is important for
        # DST timezones, as some state is stored in the tzinfo.
        tz = dt.tzinfo
        p = pickle.dumps(dt)
        unpickled_dt = pickle.loads(p)
        unpickled_tz = unpickled_dt.tzinfo
        self.failUnless(tz is unpickled_tz, '%s did not roundtrip' % tz.zone)

    def testDst(self):
        tz = pytz.timezone('Europe/Amsterdam')
        dt = datetime(2004, 2, 1, 0, 0, 0)

        for localized_tz in tz._tzinfos.values():
            self._roundtrip_tzinfo(localized_tz)
            self._roundtrip_datetime(dt.replace(tzinfo=localized_tz))

    def testRoundtrip(self):
        dt = datetime(2004, 2, 1, 0, 0, 0)
        for zone in pytz.all_timezones:
            tz = pytz.timezone(zone)
            self._roundtrip_tzinfo(tz)

    def testDatabaseFixes(self):
        # Hack the pickle to make it refer to a timezone abbreviation
        # that does not match anything. The unpickler should be able
        # to repair this case
        tz = pytz.timezone('Australia/Melbourne')
        p = pickle.dumps(tz)
        tzname = tz._tzname
        hacked_p = p.replace(tzname, '???')
        self.failIfEqual(p, hacked_p)
        unpickled_tz = pickle.loads(hacked_p)
        self.failUnless(tz is unpickled_tz)

        # Simulate a database correction. In this case, the incorrect
        # data will continue to be used.
        p = pickle.dumps(tz)
        new_utcoffset = tz._utcoffset.seconds + 42
        hacked_p = p.replace(str(tz._utcoffset.seconds), str(new_utcoffset))
        self.failIfEqual(p, hacked_p)
        unpickled_tz = pickle.loads(hacked_p)
        self.failUnlessEqual(unpickled_tz._utcoffset.seconds, new_utcoffset)
        self.failUnless(tz is not unpickled_tz)

    def testOldPickles(self):
        # Ensure that applications serializing pytz instances as pickles
        # have no troubles upgrading to a new pytz release. These pickles
        # where created with pytz2006j
        east1 = pickle.loads(
                "cpytz\n_p\np1\n(S'US/Eastern'\np2\nI-18000\n"
                "I0\nS'EST'\np3\ntRp4\n."
                )
        east2 = pytz.timezone('US/Eastern')
        self.failUnless(east1 is east2)

        # Confirm changes in name munging between 2006j and 2007c cause
        # no problems.
        pap1 = pickle.loads(
                "cpytz\n_p\np1\n(S'America/Port_minus_au_minus_Prince'"
                "\np2\nI-17340\nI0\nS'PPMT'\np3\ntRp4\n."
                )
        pap2 = pytz.timezone('America/Port-au-Prince')
        self.failUnless(pap1 is pap2)

        gmt1 = pickle.loads("cpytz\n_p\np1\n(S'Etc/GMT_plus_10'\np2\ntRp3\n.")
        gmt2 = pytz.timezone('Etc/GMT+10')
        self.failUnless(gmt1 is gmt2)


class USEasternDSTStartTestCase(unittest.TestCase):
    tzinfo = pytz.timezone('US/Eastern')

    # 24 hours before DST changeover
    transition_time = datetime(2002, 4, 7, 7, 0, 0, tzinfo=UTC)

    # Increase for 'flexible' DST transitions due to 1 minute granularity
    # of Python's datetime library
    instant = timedelta(seconds=1)

    # before transition
    before = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }

    # after transition
    after = {
        'tzname': 'EDT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }

    def _test_tzname(self, utc_dt, wanted):
        tzname = wanted['tzname']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(dt.tzname(), tzname,
            'Expected %s as tzname for %s. Got %s' % (
                tzname, str(utc_dt), dt.tzname()
                )
            )

    def _test_utcoffset(self, utc_dt, wanted):
        utcoffset = wanted['utcoffset']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(
                dt.utcoffset(), wanted['utcoffset'],
                'Expected %s as utcoffset for %s. Got %s' % (
                    utcoffset, utc_dt, dt.utcoffset()
                    )
                )

    def _test_dst(self, utc_dt, wanted):
        dst = wanted['dst']
        dt = utc_dt.astimezone(self.tzinfo)
        self.failUnlessEqual(dt.dst(),dst,
            'Expected %s as dst for %s. Got %s' % (
                dst, utc_dt, dt.dst()
                )
            )

    def test_arithmetic(self):
        utc_dt = self.transition_time

        for days in range(-420, 720, 20):
            delta = timedelta(days=days)

            # Make sure we can get back where we started
            dt = utc_dt.astimezone(self.tzinfo)
            dt2 = dt + delta
            dt2 = dt2 - delta
            self.failUnlessEqual(dt, dt2)

            # Make sure arithmetic crossing DST boundaries ends
            # up in the correct timezone after normalization
            utc_plus_delta = (utc_dt + delta).astimezone(self.tzinfo)
            local_plus_delta = self.tzinfo.normalize(dt + delta)
            self.failUnlessEqual(
                    prettydt(utc_plus_delta),
                    prettydt(local_plus_delta),
                    'Incorrect result for delta==%d days.  Wanted %r. Got %r'%(
                        days,
                        prettydt(utc_plus_delta),
                        prettydt(local_plus_delta),
                        )
                    )

    def _test_all(self, utc_dt, wanted):
        self._test_utcoffset(utc_dt, wanted)
        self._test_tzname(utc_dt, wanted)
        self._test_dst(utc_dt, wanted)

    def testDayBefore(self):
        self._test_all(
                self.transition_time - timedelta(days=1), self.before
                )

    def testTwoHoursBefore(self):
        self._test_all(
                self.transition_time - timedelta(hours=2), self.before
                )

    def testHourBefore(self):
        self._test_all(
                self.transition_time - timedelta(hours=1), self.before
                )

    def testInstantBefore(self):
        self._test_all(
                self.transition_time - self.instant, self.before
                )

    def testTransition(self):
        self._test_all(
                self.transition_time, self.after
                )

    def testInstantAfter(self):
        self._test_all(
                self.transition_time + self.instant, self.after
                )

    def testHourAfter(self):
        self._test_all(
                self.transition_time + timedelta(hours=1), self.after
                )

    def testTwoHoursAfter(self):
        self._test_all(
                self.transition_time + timedelta(hours=1), self.after
                )

    def testDayAfter(self):
        self._test_all(
                self.transition_time + timedelta(days=1), self.after
                )


class USEasternDSTEndTestCase(USEasternDSTStartTestCase):
    tzinfo = pytz.timezone('US/Eastern')
    transition_time = datetime(2002, 10, 27, 6, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EDT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }


class USEasternEPTStartTestCase(USEasternDSTStartTestCase):
    transition_time = datetime(1945, 8, 14, 23, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EWT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EPT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }


class USEasternEPTEndTestCase(USEasternDSTStartTestCase):
    transition_time = datetime(1945, 9, 30, 6, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'EPT',
        'utcoffset': timedelta(hours = -4),
        'dst': timedelta(hours = 1),
        }
    after = {
        'tzname': 'EST',
        'utcoffset': timedelta(hours = -5),
        'dst': timedelta(hours = 0),
        }


class WarsawWMTEndTestCase(USEasternDSTStartTestCase):
    # In 1915, Warsaw changed from Warsaw to Central European time.
    # This involved the clocks being set backwards, causing a end-of-DST
    # like situation without DST being involved.
    tzinfo = pytz.timezone('Europe/Warsaw')
    transition_time = datetime(1915, 8, 4, 22, 36, 0, tzinfo=UTC)
    before = {
        'tzname': 'WMT',
        'utcoffset': timedelta(hours=1, minutes=24),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'CET',
        'utcoffset': timedelta(hours=1),
        'dst': timedelta(0),
        }


class VilniusWMTEndTestCase(USEasternDSTStartTestCase):
    # At the end of 1916, Vilnius changed timezones putting its clock
    # forward by 11 minutes 35 seconds. Neither timezone was in DST mode.
    tzinfo = pytz.timezone('Europe/Vilnius')
    instant = timedelta(seconds=31)
    transition_time = datetime(1916, 12, 31, 22, 36, 00, tzinfo=UTC)
    before = {
        'tzname': 'WMT',
        'utcoffset': timedelta(hours=1, minutes=24),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'KMT',
        'utcoffset': timedelta(hours=1, minutes=36), # Really 1:35:36
        'dst': timedelta(0),
        }


class VilniusCESTStartTestCase(USEasternDSTStartTestCase):
    # In 1941, Vilnius changed from MSG to CEST, switching to summer
    # time while simultaneously reducing its UTC offset by two hours,
    # causing the clocks to go backwards for this summer time
    # switchover.
    tzinfo = pytz.timezone('Europe/Vilnius')
    transition_time = datetime(1941, 6, 23, 21, 00, 00, tzinfo=UTC)
    before = {
        'tzname': 'MSK',
        'utcoffset': timedelta(hours=3),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'CEST',
        'utcoffset': timedelta(hours=2),
        'dst': timedelta(hours=1),
        }


class LondonHistoryStartTestCase(USEasternDSTStartTestCase):
    # The first known timezone transition in London was in 1847 when
    # clocks where synchronized to GMT. However, we currently only
    # understand v1 format tzfile(5) files which does handle years
    # this far in the past, so our earliest known transition is in
    # 1916.
    tzinfo = pytz.timezone('Europe/London')
    # transition_time = datetime(1847, 12, 1, 1, 15, 00, tzinfo=UTC)
    # before = {
    #     'tzname': 'LMT',
    #     'utcoffset': timedelta(minutes=-75),
    #     'dst': timedelta(0),
    #     }
    # after = {
    #     'tzname': 'GMT',
    #     'utcoffset': timedelta(0),
    #     'dst': timedelta(0),
    #     }
    transition_time = datetime(1916, 5, 21, 2, 00, 00, tzinfo=UTC)
    before = {
        'tzname': 'GMT',
        'utcoffset': timedelta(0),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'BST',
        'utcoffset': timedelta(hours=1),
        'dst': timedelta(hours=1),
        }


class LondonHistoryEndTestCase(USEasternDSTStartTestCase):
    # Timezone switchovers are projected into the future, even
    # though no official statements exist or could be believed even
    # if they did exist. We currently only check the last known
    # transition in 2037, as we are still using v1 format tzfile(5)
    # files.
    tzinfo = pytz.timezone('Europe/London')
    # transition_time = datetime(2499, 10, 25, 1, 0, 0, tzinfo=UTC)
    transition_time = datetime(2037, 10, 25, 1, 0, 0, tzinfo=UTC)
    before = {
        'tzname': 'BST',
        'utcoffset': timedelta(hours=1),
        'dst': timedelta(hours=1),
        }
    after = {
        'tzname': 'GMT',
        'utcoffset': timedelta(0),
        'dst': timedelta(0),
        }


class NoumeaHistoryStartTestCase(USEasternDSTStartTestCase):
    # Noumea adopted a whole hour offset in 1912. Previously
    # it was 11 hours, 5 minutes and 48 seconds off UTC. However,
    # due to limitations of the Python datetime library, we need
    # to round that to 11 hours 6 minutes.
    tzinfo = pytz.timezone('Pacific/Noumea')
    transition_time = datetime(1912, 1, 12, 12, 54, 12, tzinfo=UTC)
    before = {
        'tzname': 'LMT',
        'utcoffset': timedelta(hours=11, minutes=6),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'NCT',
        'utcoffset': timedelta(hours=11),
        'dst': timedelta(0),
        }


class NoumeaDSTEndTestCase(USEasternDSTStartTestCase):
    # Noumea dropped DST in 1997.
    tzinfo = pytz.timezone('Pacific/Noumea')
    transition_time = datetime(1997, 3, 1, 15, 00, 00, tzinfo=UTC)
    before = {
        'tzname': 'NCST',
        'utcoffset': timedelta(hours=12),
        'dst': timedelta(hours=1),
        }
    after = {
        'tzname': 'NCT',
        'utcoffset': timedelta(hours=11),
        'dst': timedelta(0),
        }


class NoumeaNoMoreDSTTestCase(NoumeaDSTEndTestCase):
    # Noumea dropped DST in 1997. Here we test that it stops occuring.
    transition_time = (
        NoumeaDSTEndTestCase.transition_time + timedelta(days=365*10))
    before = NoumeaDSTEndTestCase.after
    after = NoumeaDSTEndTestCase.after


class TahitiTestCase(USEasternDSTStartTestCase):
    # Tahiti has had a single transition in its history.
    tzinfo = pytz.timezone('Pacific/Tahiti')
    transition_time = datetime(1912, 10, 1, 9, 58, 16, tzinfo=UTC)
    before = {
        'tzname': 'LMT',
        'utcoffset': timedelta(hours=-9, minutes=-58),
        'dst': timedelta(0),
        }
    after = {
        'tzname': 'TAHT',
        'utcoffset': timedelta(hours=-10),
        'dst': timedelta(0),
        }


class ReferenceUSEasternDSTStartTestCase(USEasternDSTStartTestCase):
    tzinfo = reference.Eastern
    def test_arithmetic(self):
        # Reference implementation cannot handle this
        pass


class ReferenceUSEasternDSTEndTestCase(USEasternDSTEndTestCase):
    tzinfo = reference.Eastern

    def testHourBefore(self):
        # Python's datetime library has a bug, where the hour before
        # a daylight savings transition is one hour out. For example,
        # at the end of US/Eastern daylight savings time, 01:00 EST
        # occurs twice (once at 05:00 UTC and once at 06:00 UTC),
        # whereas the first should actually be 01:00 EDT.
        # Note that this bug is by design - by accepting this ambiguity
        # for one hour one hour per year, an is_dst flag on datetime.time
        # became unnecessary.
        self._test_all(
                self.transition_time - timedelta(hours=1), self.after
                )

    def testInstantBefore(self):
        self._test_all(
                self.transition_time - timedelta(seconds=1), self.after
                )

    def test_arithmetic(self):
        # Reference implementation cannot handle this
        pass


class LocalTestCase(unittest.TestCase):
    def testLocalize(self):
        loc_tz = pytz.timezone('Europe/Amsterdam')

        loc_time = loc_tz.localize(datetime(1930, 5, 10, 0, 0, 0))
        # Actually +00:19:32, but Python datetime rounds this
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'AMT+0020')

        loc_time = loc_tz.localize(datetime(1930, 5, 20, 0, 0, 0))
        # Actually +00:19:32, but Python datetime rounds this
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'NST+0120')

        loc_time = loc_tz.localize(datetime(1940, 5, 10, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'NET+0020')

        loc_time = loc_tz.localize(datetime(1940, 5, 20, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CEST+0200')

        loc_time = loc_tz.localize(datetime(2004, 2, 1, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CET+0100')

        loc_time = loc_tz.localize(datetime(2004, 4, 1, 0, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CEST+0200')

        tz = pytz.timezone('Europe/Amsterdam')
        loc_time = loc_tz.localize(datetime(1943, 3, 29, 1, 59, 59))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'CET+0100')


        # Switch to US
        loc_tz = pytz.timezone('US/Eastern')

        # End of DST ambiguity check
        loc_time = loc_tz.localize(datetime(1918, 10, 27, 1, 59, 59), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EDT-0400')

        loc_time = loc_tz.localize(datetime(1918, 10, 27, 1, 59, 59), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

        self.failUnlessRaises(pytz.AmbiguousTimeError,
            loc_tz.localize, datetime(1918, 10, 27, 1, 59, 59), is_dst=None
            )

        # Start of DST non-existent times
        loc_time = loc_tz.localize(datetime(1918, 3, 31, 2, 0, 0), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

        loc_time = loc_tz.localize(datetime(1918, 3, 31, 2, 0, 0), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EDT-0400')

        self.failUnlessRaises(pytz.NonExistentTimeError,
            loc_tz.localize, datetime(1918, 3, 31, 2, 0, 0), is_dst=None
            )

        # Weird changes - war time and peace time both is_dst==True

        loc_time = loc_tz.localize(datetime(1942, 2, 9, 3, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EWT-0400')

        loc_time = loc_tz.localize(datetime(1945, 8, 14, 19, 0, 0))
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EPT-0400')

        loc_time = loc_tz.localize(datetime(1945, 9, 30, 1, 0, 0), is_dst=1)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EPT-0400')

        loc_time = loc_tz.localize(datetime(1945, 9, 30, 1, 0, 0), is_dst=0)
        self.failUnlessEqual(loc_time.strftime('%Z%z'), 'EST-0500')

    def testNormalize(self):
        tz = pytz.timezone('US/Eastern')
        dt = datetime(2004, 4, 4, 7, 0, 0, tzinfo=UTC).astimezone(tz)
        dt2 = dt - timedelta(minutes=10)
        self.failUnlessEqual(
                dt2.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '2004-04-04 02:50:00 EDT-0400'
                )

        dt2 = tz.normalize(dt2)
        self.failUnlessEqual(
                dt2.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '2004-04-04 01:50:00 EST-0500'
                )

    def testPartialMinuteOffsets(self):
        # utcoffset in Amsterdam was not a whole minute until 1937
        # However, we fudge this by rounding them, as the Python
        # datetime library 
        tz = pytz.timezone('Europe/Amsterdam')
        utc_dt = datetime(1914, 1, 1, 13, 40, 28, tzinfo=UTC) # correct
        utc_dt = utc_dt.replace(second=0) # But we need to fudge it
        loc_dt = utc_dt.astimezone(tz)
        self.failUnlessEqual(
                loc_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '1914-01-01 14:00:00 AMT+0020'
                )

        # And get back...
        utc_dt = loc_dt.astimezone(UTC)
        self.failUnlessEqual(
                utc_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
                '1914-01-01 13:40:00 UTC+0000'
                )

    def no_testCreateLocaltime(self):
        # It would be nice if this worked, but it doesn't.
        tz = pytz.timezone('Europe/Amsterdam')
        dt = datetime(2004, 10, 31, 2, 0, 0, tzinfo=tz)
        self.failUnlessEqual(
                dt.strftime(fmt),
                '2004-10-31 02:00:00 CET+0100'
                )

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('pytz'))
    suite.addTest(doctest.DocTestSuite('pytz.tzinfo'))
    import test_tzinfo
    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tzinfo))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


########NEW FILE########
__FILENAME__ = tzfile
#!/usr/bin/env python
'''
$Id: tzfile.py,v 1.8 2004/06/03 00:15:24 zenzen Exp $
'''

from cStringIO import StringIO
from datetime import datetime, timedelta
from struct import unpack, calcsize

from pytz.tzinfo import StaticTzInfo, DstTzInfo, memorized_ttinfo
from pytz.tzinfo import memorized_datetime, memorized_timedelta


def build_tzinfo(zone, fp):
    head_fmt = '>4s c 15x 6l'
    head_size = calcsize(head_fmt)
    (magic, format, ttisgmtcnt, ttisstdcnt,leapcnt, timecnt,
        typecnt, charcnt) =  unpack(head_fmt, fp.read(head_size))

    # Make sure it is a tzfile(5) file
    assert magic == 'TZif'

    # Read out the transition times, localtime indices and ttinfo structures.
    data_fmt = '>%(timecnt)dl %(timecnt)dB %(ttinfo)s %(charcnt)ds' % dict(
        timecnt=timecnt, ttinfo='lBB'*typecnt, charcnt=charcnt)
    data_size = calcsize(data_fmt)
    data = unpack(data_fmt, fp.read(data_size))

    # make sure we unpacked the right number of values
    assert len(data) == 2 * timecnt + 3 * typecnt + 1
    transitions = [memorized_datetime(trans)
                   for trans in data[:timecnt]]
    lindexes = list(data[timecnt:2 * timecnt])
    ttinfo_raw = data[2 * timecnt:-1]
    tznames_raw = data[-1]
    del data

    # Process ttinfo into separate structs
    ttinfo = []
    tznames = {}
    i = 0
    while i < len(ttinfo_raw):
        # have we looked up this timezone name yet?
        tzname_offset = ttinfo_raw[i+2]
        if tzname_offset not in tznames:
            nul = tznames_raw.find('\0', tzname_offset)
            if nul < 0:
                nul = len(tznames_raw)
            tznames[tzname_offset] = tznames_raw[tzname_offset:nul]
        ttinfo.append((ttinfo_raw[i],
                       bool(ttinfo_raw[i+1]),
                       tznames[tzname_offset]))
        i += 3

    # Now build the timezone object
    if len(transitions) == 0:
        ttinfo[0][0], ttinfo[0][2]
        cls = type(zone, (StaticTzInfo,), dict(
            zone=zone,
            _utcoffset=memorized_timedelta(ttinfo[0][0]),
            _tzname=ttinfo[0][2]))
    else:
        # Early dates use the first standard time ttinfo
        i = 0
        while ttinfo[i][1]:
            i += 1
        if ttinfo[i] == ttinfo[lindexes[0]]:
            transitions[0] = datetime.min
        else:
            transitions.insert(0, datetime.min)
            lindexes.insert(0, i)

        # calculate transition info
        transition_info = []
        for i in range(len(transitions)):
            inf = ttinfo[lindexes[i]]
            utcoffset = inf[0]
            if not inf[1]:
                dst = 0
            else:
                for j in range(i-1, -1, -1):
                    prev_inf = ttinfo[lindexes[j]]
                    if not prev_inf[1]:
                        break
                dst = inf[0] - prev_inf[0] # dst offset

                if dst <= 0: # Bad dst? Look further.
                    for j in range(i+1, len(transitions)):
                        stdinf = ttinfo[lindexes[j]]
                        if not stdinf[1]:
                            dst = inf[0] - stdinf[0]
                            if dst > 0:
                                break # Found a useful std time.

            tzname = inf[2]

            # Round utcoffset and dst to the nearest minute or the
            # datetime library will complain. Conversions to these timezones
            # might be up to plus or minus 30 seconds out, but it is
            # the best we can do.
            utcoffset = int((utcoffset + 30) / 60) * 60
            dst = int((dst + 30) / 60) * 60
            transition_info.append(memorized_ttinfo(utcoffset, dst, tzname))

        cls = type(zone, (DstTzInfo,), dict(
            zone=zone,
            _utc_transition_times=transitions,
            _transition_info=transition_info))

    return cls()

if __name__ == '__main__':
    import os.path
    from pprint import pprint
    base = os.path.join(os.path.dirname(__file__), 'zoneinfo')
    tz = build_tzinfo('Australia/Melbourne',
                      open(os.path.join(base,'Australia','Melbourne'), 'rb'))
    tz = build_tzinfo('US/Eastern',
                      open(os.path.join(base,'US','Eastern'), 'rb'))
    pprint(tz._utc_transition_times)
    #print tz.asPython(4)
    #print tz.transitions_mapping

########NEW FILE########
__FILENAME__ = tzinfo
'''Base classes and helpers for building zone specific tzinfo classes'''

from datetime import datetime, timedelta, tzinfo
from bisect import bisect_right
try:
    set
except NameError:
    from sets import Set as set

import pytz

__all__ = []

_timedelta_cache = {}
def memorized_timedelta(seconds):
    '''Create only one instance of each distinct timedelta'''
    try:
        return _timedelta_cache[seconds]
    except KeyError:
        delta = timedelta(seconds=seconds)
        _timedelta_cache[seconds] = delta
        return delta

_epoch = datetime.utcfromtimestamp(0)
_datetime_cache = {0: _epoch}
def memorized_datetime(seconds):
    '''Create only one instance of each distinct datetime'''
    try:
        return _datetime_cache[seconds]
    except KeyError:
        # NB. We can't just do datetime.utcfromtimestamp(seconds) as this
        # fails with negative values under Windows (Bug #90096)
        dt = _epoch + timedelta(seconds=seconds)
        _datetime_cache[seconds] = dt
        return dt

_ttinfo_cache = {}
def memorized_ttinfo(*args):
    '''Create only one instance of each distinct tuple'''
    try:
        return _ttinfo_cache[args]
    except KeyError:
        ttinfo = (
                memorized_timedelta(args[0]),
                memorized_timedelta(args[1]),
                args[2]
                )
        _ttinfo_cache[args] = ttinfo
        return ttinfo

_notime = memorized_timedelta(0)

def _to_seconds(td):
    '''Convert a timedelta to seconds'''
    return td.seconds + td.days * 24 * 60 * 60


class BaseTzInfo(tzinfo):
    # Overridden in subclass
    _utcoffset = None
    _tzname = None
    zone = None

    def __str__(self):
        return self.zone


class StaticTzInfo(BaseTzInfo):
    '''A timezone that has a constant offset from UTC

    These timezones are rare, as most locations have changed their
    offset at some point in their history
    '''
    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        return (dt + self._utcoffset).replace(tzinfo=self)

    def utcoffset(self,dt):
        '''See datetime.tzinfo.utcoffset'''
        return self._utcoffset

    def dst(self,dt):
        '''See datetime.tzinfo.dst'''
        return _notime

    def tzname(self,dt):
        '''See datetime.tzinfo.tzname'''
        return self._tzname

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time'''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'
        return dt.replace(tzinfo=self)

    def normalize(self, dt, is_dst=False):
        '''Correct the timezone information on the given datetime'''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'
        return dt.replace(tzinfo=self)

    def __repr__(self):
        return '<StaticTzInfo %r>' % (self.zone,)

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes. 
        return pytz._p, (self.zone,)


class DstTzInfo(BaseTzInfo):
    '''A timezone that has a variable offset from UTC

    The offset might change if daylight savings time comes into effect,
    or at a point in history when the region decides to change their
    timezone definition.
    '''
    # Overridden in subclass
    _utc_transition_times = None # Sorted list of DST transition times in UTC
    _transition_info = None # [(utcoffset, dstoffset, tzname)] corresponding
                            # to _utc_transition_times entries
    zone = None

    # Set in __init__
    _tzinfos = None
    _dst = None # DST offset

    def __init__(self, _inf=None, _tzinfos=None):
        if _inf:
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = _inf
        else:
            _tzinfos = {}
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = self._transition_info[0]
            _tzinfos[self._transition_info[0]] = self
            for inf in self._transition_info[1:]:
                if not _tzinfos.has_key(inf):
                    _tzinfos[inf] = self.__class__(inf, _tzinfos)

    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        dt = dt.replace(tzinfo=None)
        idx = max(0, bisect_right(self._utc_transition_times, dt) - 1)
        inf = self._transition_info[idx]
        return (dt + inf[0]).replace(tzinfo=self._tzinfos[inf])

    def normalize(self, dt):
        '''Correct the timezone information on the given datetime

        If date arithmetic crosses DST boundaries, the tzinfo
        is not magically adjusted. This method normalizes the
        tzinfo to the correct one.

        To test, first we need to do some setup

        >>> from pytz import timezone
        >>> utc = timezone('UTC')
        >>> eastern = timezone('US/Eastern')
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'

        We next create a datetime right on an end-of-DST transition point,
        the instant when the wallclocks are wound back one hour.

        >>> utc_dt = datetime(2002, 10, 27, 6, 0, 0, tzinfo=utc)
        >>> loc_dt = utc_dt.astimezone(eastern)
        >>> loc_dt.strftime(fmt)
        '2002-10-27 01:00:00 EST (-0500)'

        Now, if we subtract a few minutes from it, note that the timezone
        information has not changed.

        >>> before = loc_dt - timedelta(minutes=10)
        >>> before.strftime(fmt)
        '2002-10-27 00:50:00 EST (-0500)'

        But we can fix that by calling the normalize method

        >>> before = eastern.normalize(before)
        >>> before.strftime(fmt)
        '2002-10-27 01:50:00 EDT (-0400)'
        '''
        if dt.tzinfo is None:
            raise ValueError, 'Naive time - no tzinfo set'

        # Convert dt in localtime to UTC
        offset = dt.tzinfo._utcoffset
        dt = dt.replace(tzinfo=None)
        dt = dt - offset
        # convert it back, and return it
        return self.fromutc(dt)

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time.

        This method should be used to construct localtimes, rather
        than passing a tzinfo argument to a datetime constructor.

        is_dst is used to determine the correct timezone in the ambigous
        period at the end of daylight savings time.

        >>> from pytz import timezone
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'
        >>> amdam = timezone('Europe/Amsterdam')
        >>> dt  = datetime(2004, 10, 31, 2, 0, 0)
        >>> loc_dt1 = amdam.localize(dt, is_dst=True)
        >>> loc_dt2 = amdam.localize(dt, is_dst=False)
        >>> loc_dt1.strftime(fmt)
        '2004-10-31 02:00:00 CEST (+0200)'
        >>> loc_dt2.strftime(fmt)
        '2004-10-31 02:00:00 CET (+0100)'
        >>> str(loc_dt2 - loc_dt1)
        '1:00:00'

        Use is_dst=None to raise an AmbiguousTimeError for ambiguous
        times at the end of daylight savings

        >>> loc_dt1 = amdam.localize(dt, is_dst=None)
        Traceback (most recent call last):
            [...]
        AmbiguousTimeError: 2004-10-31 02:00:00

        is_dst defaults to False

        >>> amdam.localize(dt) == amdam.localize(dt, False)
        True

        is_dst is also used to determine the correct timezone in the
        wallclock times jumped over at the start of daylight savings time.

        >>> pacific = timezone('US/Pacific')
        >>> dt = datetime(2008, 3, 9, 2, 0, 0)
        >>> ploc_dt1 = pacific.localize(dt, is_dst=True)
        >>> ploc_dt2 = pacific.localize(dt, is_dst=False)
        >>> ploc_dt1.strftime(fmt)
        '2008-03-09 02:00:00 PDT (-0700)'
        >>> ploc_dt2.strftime(fmt)
        '2008-03-09 02:00:00 PST (-0800)'
        >>> str(ploc_dt2 - ploc_dt1)
        '1:00:00'

        Use is_dst=None to raise a NonExistentTimeError for these skipped
        times.

        >>> loc_dt1 = pacific.localize(dt, is_dst=None)
        Traceback (most recent call last):
            [...]
        NonExistentTimeError: 2008-03-09 02:00:00
        '''
        if dt.tzinfo is not None:
            raise ValueError, 'Not naive datetime (tzinfo is already set)'

        # Find the two best possibilities.
        possible_loc_dt = set()
        for delta in [timedelta(days=-1), timedelta(days=1)]:
            loc_dt = dt + delta
            idx = max(0, bisect_right(
                self._utc_transition_times, loc_dt) - 1)
            inf = self._transition_info[idx]
            tzinfo = self._tzinfos[inf]
            loc_dt = tzinfo.normalize(dt.replace(tzinfo=tzinfo))
            if loc_dt.replace(tzinfo=None) == dt:
                possible_loc_dt.add(loc_dt)

        if len(possible_loc_dt) == 1:
            return possible_loc_dt.pop()

        # If there are no possibly correct timezones, we are attempting
        # to convert a time that never happened - the time period jumped
        # during the start-of-DST transition period.
        if len(possible_loc_dt) == 0:
            # If we refuse to guess, raise an exception.
            if is_dst is None:
                raise NonExistentTimeError(dt)

            # If we are forcing the pre-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock forward a few
            # hours.
            elif is_dst:
                return self.localize(
                    dt + timedelta(hours=6), is_dst=True) - timedelta(hours=6)

            # If we are forcing the post-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock back.
            else:
                return self.localize(
                    dt - timedelta(hours=6), is_dst=False) + timedelta(hours=6)


        # If we get this far, we have multiple possible timezones - this
        # is an ambiguous case occuring during the end-of-DST transition.

        # If told to be strict, raise an exception since we have an
        # ambiguous case
        if is_dst is None:
            raise AmbiguousTimeError(dt)

        # Filter out the possiblilities that don't match the requested
        # is_dst
        filtered_possible_loc_dt = [
            p for p in possible_loc_dt
                if bool(p.tzinfo._dst) == is_dst
            ]

        # Hopefully we only have one possibility left. Return it.
        if len(filtered_possible_loc_dt) == 1:
            return filtered_possible_loc_dt[0]

        if len(filtered_possible_loc_dt) == 0:
            filtered_possible_loc_dt = list(possible_loc_dt)

        # If we get this far, we have in a wierd timezone transition
        # where the clocks have been wound back but is_dst is the same
        # in both (eg. Europe/Warsaw 1915 when they switched to CET).
        # At this point, we just have to guess unless we allow more
        # hints to be passed in (such as the UTC offset or abbreviation),
        # but that is just getting silly.
        #
        # Choose the earliest (by UTC) applicable timezone.
        def mycmp(a,b):
            return cmp(
                    a.replace(tzinfo=None) - a.tzinfo._utcoffset,
                    b.replace(tzinfo=None) - b.tzinfo._utcoffset,
                    )
        filtered_possible_loc_dt.sort(mycmp)
        return filtered_possible_loc_dt[0]

    def utcoffset(self, dt):
        '''See datetime.tzinfo.utcoffset'''
        return self._utcoffset

    def dst(self, dt):
        '''See datetime.tzinfo.dst'''
        return self._dst

    def tzname(self, dt):
        '''See datetime.tzinfo.tzname'''
        return self._tzname

    def __repr__(self):
        if self._dst:
            dst = 'DST'
        else:
            dst = 'STD'
        if self._utcoffset > _notime:
            return '<DstTzInfo %r %s+%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )
        else:
            return '<DstTzInfo %r %s%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes.
        return pytz._p, (
                self.zone,
                _to_seconds(self._utcoffset),
                _to_seconds(self._dst),
                self._tzname
                )


class InvalidTimeError(Exception):
    '''Base class for invalid time exceptions.'''


class AmbiguousTimeError(InvalidTimeError):
    '''Exception raised when attempting to create an ambiguous wallclock time.

    At the end of a DST transition period, a particular wallclock time will
    occur twice (once before the clocks are set back, once after). Both
    possibilities may be correct, unless further information is supplied.

    See DstTzInfo.normalize() for more info
    '''


class NonExistentTimeError(InvalidTimeError):
    '''Exception raised when attempting to create a wallclock time that
    cannot exist.

    At the start of a DST transition period, the wallclock time jumps forward.
    The instants jumped over never occur.
    '''


def unpickler(zone, utcoffset=None, dstoffset=None, tzname=None):
    """Factory function for unpickling pytz tzinfo instances.

    This is shared for both StaticTzInfo and DstTzInfo instances, because
    database changes could cause a zones implementation to switch between
    these two base classes and we can't break pickles on a pytz version
    upgrade.
    """
    # Raises a KeyError if zone no longer exists, which should never happen
    # and would be a bug.
    tz = pytz.timezone(zone)

    # A StaticTzInfo - just return it
    if utcoffset is None:
        return tz

    # This pickle was created from a DstTzInfo. We need to
    # determine which of the list of tzinfo instances for this zone
    # to use in order to restore the state of any datetime instances using
    # it correctly.
    utcoffset = memorized_timedelta(utcoffset)
    dstoffset = memorized_timedelta(dstoffset)
    try:
        return tz._tzinfos[(utcoffset, dstoffset, tzname)]
    except KeyError:
        # The particular state requested in this timezone no longer exists.
        # This indicates a corrupt pickle, or the timezone database has been
        # corrected violently enough to make this particular
        # (utcoffset,dstoffset) no longer exist in the zone, or the
        # abbreviation has been changed.
        pass

    # See if we can find an entry differing only by tzname. Abbreviations
    # get changed from the initial guess by the database maintainers to
    # match reality when this information is discovered.
    for localized_tz in tz._tzinfos.values():
        if (localized_tz._utcoffset == utcoffset
                and localized_tz._dst == dstoffset):
            return localized_tz

    # This (utcoffset, dstoffset) information has been removed from the
    # zone. Add it back. This might occur when the database maintainers have
    # corrected incorrect information. datetime instances using this
    # incorrect information will continue to do so, exactly as they were
    # before being pickled. This is purely an overly paranoid safety net - I
    # doubt this will ever been needed in real life.
    inf = (utcoffset, dstoffset, tzname)
    tz._tzinfos[inf] = tz.__class__(inf, tz._tzinfos)
    return tz._tzinfos[inf]


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from seriesly.series.models import Serie, Season, Episode

admin.site.register(Serie)
admin.site.register(Season)
admin.site.register(Episode)

########NEW FILE########
__FILENAME__ = models
import logging
import re
import datetime

from pytz import utc

from google.appengine.api import taskqueue
from google.appengine.api import memcache
from google.appengine.ext import db

from django.core.urlresolvers import reverse

from helper.string_utils import normalize
from helper.dateutils import get_timezone_for_gmt_offset

from series.tvrage import TVRage


class Show(db.Model):
    name = db.StringProperty()
    normalized_name = db.StringProperty()
    alt_names = db.StringProperty()
    slug = db.StringProperty()
    description = db.StringProperty(indexed=False)
    genres = db.StringProperty(indexed=False)
    network = db.StringProperty(indexed=False)
    active = db.BooleanProperty()
    country = db.StringProperty(indexed=False)
    runtime = db.IntegerProperty()
    timezone = db.StringProperty(indexed=False)
    tvrage_id = db.IntegerProperty()
    added = db.DateTimeProperty()

    _memkey_all_shows_ordered = "all_shows_ordered"
    _memkey_shows_dict = "all_shows_dict"
    re_find_the = re.compile("^The (.*)$")

    @classmethod
    def kind(cls):
        return "series_show"

    def __unicode__(self):
        return self.name

    @property
    def idnr(self):
        return self.key().id()

    @property
    def slug(self):
        return self.normalized_name.replace(" ", "-")

    def alternative_names(self):
        if self.alt_names is None:
            return []
        return self.alt_names.split("|")

    @classmethod
    def get_all_ordered(cls):
        shows = memcache.get(cls._memkey_all_shows_ordered)
        if shows is not None:
            return shows
        shows = Show.all().filter("active =", True)
        show_list = []
        for show in shows:
            if len(show.name) > 33:
                show.ordered_name = cls.re_find_the.sub(
                    "\\1, The", show.name[:33] + "...")
            else:
                show.ordered_name = cls.re_find_the.sub("\\1, The", show.name)
            show_list.append(show)
        shows = sorted(show_list, key=lambda x: x.ordered_name.lower())
        memcache.set(key=cls._memkey_all_shows_ordered, value=shows)
        return shows

    @classmethod
    def find(cls, show_name):
        if not len(show_name):
            return None
        norm_name = normalize(show_name)
        shows = Show.get_all_ordered()
        for show in shows:
            if show_name == show.name or norm_name == show.normalized_name or \
                    any([norm_name == alt_name for alt_name in show.alternative_names()]):
                return show

    @classmethod
    def get_all_dict(cls):
        show_dict = memcache.get(cls._memkey_shows_dict)
        if show_dict is not None:
            return show_dict
        shows = Show.get_all_ordered()
        show_dict = dict([(str(show.key()), show) for show in shows])
        memcache.set(key=cls._memkey_shows_dict, value=show_dict)
        return show_dict

    @classmethod
    def clear_cache(cls):
        memcache.delete(cls._memkey_all_shows_ordered)
        memcache.delete(cls._memkey_shows_dict)

    def add_update_task(self):
        t = taskqueue.Task(url=reverse('seriesly-shows-update_show'), params={"key": str(self.key())})
        t.add(queue_name="series")
        return t

    def update(self, show_info=None, get_everything=False):
        if show_info is None:
            tvrage = TVRage()
            show_info = tvrage.get_info(self.tvrage_id)
            # Kill Tabatha\u2019s ... here
            show_info.name = show_info.name.replace(u"\u2019", "'")
            # Kill >>'Til Death<< here
            if show_info.name.startswith("'"):
                show_info.name = show_info.name.replace("'", "", 1)
            attr_list = ["name", "network", "genres", "active",
                "country", "runtime", "timezone", "tvrage_id"]
            if self.update_attrs(show_info, attr_list):
                self.put()
        for season_info in show_info.seasons:
            logging.debug("Update or create Season...")
            Season.update_or_create(self, season_info, get_everything=get_everything)

    def update_attrs(self, info_obj, attr_list):
        changed = False
        for attr in attr_list:
            val = getattr(info_obj, attr)
            if val != getattr(self, attr):
                setattr(self, attr, val)
                changed = True
        return changed

    def put(self):
        self.normalized_name = normalize(self.name)
        return super(Show, self).put()

    @classmethod
    def update_or_create(cls, name, show_id=None):
        tvrage = TVRage()
        if name is not None:
            show_info = tvrage.get_info_by_name(name)
        else:
            show_info = tvrage.get_info(show_id)
        if show_info is None:
            return False
        logging.debug("Show exists..?")
        show = Show.all().filter("tvrage_id =", show_info.tvrage_id).get()
        if show is None:
            logging.debug("Creating Show...")
            show = Show(name=show_info.name,
                        network=show_info.network,
                        genres=show_info.genres,
                        active=show_info.active,
                        country=show_info.country,
                        runtime=show_info.runtime,
                        timezone=show_info.timezone,
                        tvrage_id=show_info.tvrage_id,
                        added=datetime.datetime.now())
            show.put()
        show.update(show_info)

    @property
    def is_new(self):
        if self.added is None:
            return False
        new_time = datetime.timedelta(days=7)
        if datetime.datetime.now() - self.added < new_time:
            return True
        return False


class Season(db.Model):
    show = db.ReferenceProperty(Show)
    number = db.IntegerProperty()
    start = db.DateTimeProperty()
    end = db.DateTimeProperty()

    @classmethod
    def kind(cls):
        return "series_season"

    @classmethod
    def update_or_create(cls, show, season_info, get_everything=False):
        season = Season.all().filter("show =", show).filter(
                "number =", season_info.season_nr).get()
        logging.debug("Found season? %s" % season)
        if season is None:
            season = Season(show=show, number=season_info.season_nr)
            season.put()
        season.update(season_info, get_everything=get_everything)
        season.put()

    def update(self, season_info, get_everything=False):
        first_date = None
        episode_info = None
        now = utc.localize(datetime.datetime.now())
        fortyeight_hours_ago = now - datetime.timedelta(hours=48)
        for episode_info in season_info.episodes:
            logging.debug("Update episode... %s" % episode_info)
            if first_date is None:
                first_date = episode_info.date
            if get_everything or episode_info.date is None or episode_info.date >= fortyeight_hours_ago:
                Episode.update_or_create(self, episode_info)
        logging.debug("All episodes updated...")
        self.start = first_date
        if episode_info is not None:
            self.end = episode_info.date


class Episode(db.Model):
    show = db.ReferenceProperty(Show)
    season = db.ReferenceProperty(Season)
    season_number = db.IntegerProperty()
    number = db.IntegerProperty()
    title = db.StringProperty()
    text = db.TextProperty(default="")
    date = db.DateTimeProperty()

    _memkey_episode_dict = "all_episodes_dict"

    @classmethod
    def kind(cls):
        return "series_episode"

    @property
    def date_end(self):
        return self.date + datetime.timedelta(minutes=self.show.runtime)

    @property
    def date_local(self):
        if getattr(self, "_date_local", None) is None:
            try:
                tz = get_timezone_for_gmt_offset(self.show.timezone)
            except Exception:
                tz = utc
            self._date_local = utc.localize(self.date).astimezone(tz)
        return self._date_local

    @property
    def date_local_end(self):
        if getattr(self, "_date_local_end", None) is None:
            try:
                tz = get_timezone_for_gmt_offset(self.show.timezone)
            except Exception:
                tz = utc
            self._date_local_end = utc.localize(self.date_end).astimezone(tz)
        return self._date_local_end

    @classmethod
    def update_or_create(cls, season, episode_info):
        episode = Episode.all().filter("show =", season.show).filter(
            "season =", season).filter("number =", episode_info.nr).get()
        logging.debug("Found episode... %s" % episode)
        if episode is None:
            episode = Episode.create(season, episode_info)
        else:
            episode.update(episode_info)
        episode.put()
        return episode

    @classmethod
    def create(cls, season, episode_info):
        return Episode(show=season.show, season=season,
                        season_number=season.number,
                        number=episode_info.nr,
                        title=episode_info.title,
                        date=episode_info.date)

    @classmethod
    def get_all_dict(cls):
        episode_dict = memcache.get(cls._memkey_episode_dict)
        if episode_dict is not None:
            return episode_dict
        now = datetime.datetime.now()
        one_week_ago = now - datetime.timedelta(days=8)
        # in_one_week = now + datetime.timedelta(days=8)
        episodes = Episode.all().filter("date >", one_week_ago)
        # removed this: .filter("date <",in_one_week).fetch(1000)
        episode_dict = {}
        for ep in episodes:
            if len(episode_dict.get(str(ep._show), [])) < 20:
                # store max of 20 episodes per show
                episode_dict.setdefault(str(ep._show), []).append(ep)
        memcache.set(key=cls._memkey_episode_dict, value=episode_dict)
        return episode_dict

    @classmethod
    def clear_cache(cls):
        memcache.delete(cls._memkey_episode_dict)

    @classmethod
    def add_clear_cache_task(cls, queue_name):
        t = taskqueue.Task(url=reverse('seriesly-shows-clear_cache'), params={})
        t.add(queue_name=queue_name)
        return t

    @classmethod
    def get_for_shows(cls, shows, before=None, after=None, order=None):
        episode_list = []
        episode_dict = Episode.get_all_dict()
        changed = False
        for show in shows:
            k = str(show.key())
            if k in episode_dict:
                episode_dict[k].sort(key=lambda x: x.date)
                prev = None
                for ep in episode_dict[k]:
                    if prev is not None:
                        prev.next = ep
                    ep.show = show
                    prev = ep
                episode_list.extend(episode_dict[k])
        if changed:
            memcache.set(key=cls._memkey_episode_dict, value=episode_dict)
        episode_list.sort(key=lambda x: x.date)
        if after is not None or before is not None:
            lower = None
            upper = len(episode_list)
            for ep, i in zip(episode_list, range(len(episode_list))):
                if after is not None and lower is None and ep.date > after:
                    lower = i
                if before is not None and ep.date > before:
                    upper = i
                    break
            if lower > 0 or upper < len(episode_list):
                episode_list = episode_list[lower:upper]
        if order is not None and order.startswith("-"):
            episode_list.reverse()
        return episode_list

    @classmethod
    def get_for_shows_old(cls, shows, before=None, after=None, order=None):
        def extra(q):
            if before is not None:
                q = q.filter("date <", before)
            if after is not None:
                q = q.filter("date >", after)
            if order is not None:
                q = q.order(order)
            return q

        if not len(shows):
            return []

        if len(shows) <= 28:
            logging.debug("starting query")
            query = Episode.all().filter("show IN", shows)
            return extra(query).fetch(1000)

        episodes = []
        for i in range(len(shows) / 28 + 1):
            q_shows = shows[i * 28:(i + 1) * 28]
            if not len(q_shows):
                continue
            episodes.extend(extra(Episode.all().filter("show IN", q_shows)).fetch(1000))
        if order is not None and order.startswith("-"):
            return sorted(episodes, lambda x: x.date).reverse()
        else:
            return sorted(episodes, lambda x: x.date)

    def update(self, episode_info):
        self.title = episode_info.title
        self.date = episode_info.date

    def get_next(self):
        return Episode.all().filter("date >", self.date).get()

    def create_event_details(self, cal):
        vevent = cal.add('vevent')
        vevent.add('uid').value = "seriesly-episode-%s" % self.key()
        try:
            tz = get_timezone_for_gmt_offset(self.show.timezone)
        except Exception:
            tz = utc
        date = utc.localize(self.date).astimezone(tz)
        vevent.add('dtstart').value = date
        vevent.add('dtend').value = date + datetime.timedelta(minutes=self.show.runtime)
        vevent.add('summary').value = "%s - %s (%dx%d)" % (self.show.name, self.title,
                                                                self.season_number, self.number)
        vevent.add('location').value = self.show.network
        return vevent

########NEW FILE########
__FILENAME__ = series_list
series_list="""10 Things I Hate About You
24
30 Rock
90210
Accidentally on Purpose
The Amazing Race
American Chopper
American Dad!
American Idol
Americas Funniest Home Videos
Americas Got Talent
Americas Next Top Model
Apparitions
The Apprentice UK
The Apprentice
Archer (2009)
Ashes to Ashes
The Bachelor
Being Erica
Being Human
Better Off Ted
The Big Bang Theory
Big Brother (US)
Big Brother UK
Big Brothers Big Mouth
Big Brothers Little Brother
Big Love
Biography Channel Documentaries
Black Gold
Bones
The Border
Bored to Death
Born Survivor Bear Grylls
Boy Meets Girl 2009
Breaking Bad
Brothers and Sisters
Burn Notice
Californication
Caprica
Castle
Catastrophe
Celebrity Fit Club (US)
The Chasers War on Everything
Chuck
City Homicide
Clone
The Closer
The Colbert Report
Cold Case
The CollegeHumor Show
Comedy Central Presents
Community
COPS
Cougar Town
Crash
Criminal Minds
CSI: Crime Scene Investigation
CSI: Miami
CSI: NY
Cupid (2009)
Curb Your Enthusiasm
The Daily Show
Damages
Dancing with the Stars
Dark Blue
Late Show with David Letterman
Deadliest Catch
Deadliest Warrior
Defying Gravity
Delocated
Desperate Housewives
Desperate Romantics
Dexter
Dirty Jobs
Discovery Channel
Doctor Who
Dollhouse
Drop Dead Diva
Durham County
Eastbound and Down
Eastwick
Emmy Awards
Entourage
Eureka
Family Guy
Feasting On Waves
Fifth Gear
The Fixer
FlashForward
Flashpoint
Fonejacker
The Forgotten (2009)
Friday Night Lights
Fringe
Frisky Dingo
Gary Unmarried
Gene Simmons Family Jewels
Ghost Whisperer
Glee
The Good Wife
Gossip Girl
Greek
Greys Anatomy
The Guard
Hawthorne
Hells Kitchen
Hells Kitchen US
Heroes
The Hills
History Channel Documentaries
The Hollowmen
Honest
Hope Springs
Hotel Babylon
House
How I met your mother
How Not To Live Your Life
Human Weapon
Hung
Hustle
Important Things with Demetri Martin
In Guantanamo
In Plain Sight
In Treatment
Inferno 999
The Invisibles
The IT Crowd
It's Always Sunny in Philadelphia
John Safrans Race Relations
Kingdom
Kitchen Nightmares
Krod Mandoon and the Flaming Sword of Fire
LA Ink
Lab Rats
Late Night with Conan O'Brien
Law and Order
Law and Order: Criminal Intent
Law and Order: Special Victims Unit
Law and Order: UK
Legend of the Seeker
Level 3
Leverage
Lewis Blacks the Root of all Evil
Lie to me
The Life and Times of Tim
Life Documentary
Lincoln Heights
The Line
The Lionshare
The Listener
Little Mosque on the Prairie
Lost
Mad Men
Make It or Break It
Man vs. Wild
Mark Loves Sharon
Medium
Melrose Place
Men of a Certain Age
Mental
The Mentalist
Mercy
Merlin
The Middle
Misfits
Mistresses
Modern Family
MonsterQuest
Moving Wallpaper
MV Group Documentaries
My Boys
Mythbusters
National Geographic
NCIS
NCIS: Los Angeles
The New Adventures Of Old Christine
New Tricks
Nip/Tuck
No 1 Ladies Detective Agency, The
No Heroics
Nova ScienceNOW
Numb3rs
Nurse Jackie
The Office
One Tree Hill
Packed To The Rafters
Parks and Recreation
Party Down
The Penguins Of Madagascar
Penn And Teller: Bullshit!
Personal Affairs
The Philanthropist
The Pick up Artist
Primeval
Private Practice
Project Runway
Psych
Psychoville
QI
Raising the bar
Real Time with Bill Maher
Red Dwarf
Rescue Me
Rita Rocks
Robot Chicken
Royal Pains
Rules of Engagement
Run's House
Rush
Sanctuary
The Sarah Jane Adventures
The Sarah Silverman Program
Saturday Night Live
Saving Grace
Saxondale
The Sci Fi Guys
Scrubs
The Secret Life of the American Teenager
The Simpsons
Skins
Smallville
So You Think You Can Dance
Sons of Anarchy
South Park
Southland
Spicks & Specks
Spooks
Spooks: Code 9
Star Wars: The Clone Wars (2008)
Stargate Universe
Supernatural
Survivor
Survivors
Til Death
Time Warp
The Tonight Show with Jay Leno
Top Chef
Top Gear
Top Gear Australia
Torchwood
TorrentFreak TV
Trauma
Trial and Retribution
True Blood
The Tudors
Two and a Half Men
Ugly Betty
The Ultimate Fighter
Underbelly
United States of Tara
The Universe
Us Now
V
The Vampire Diaries
The Venture Brothers
Wallander
Warehouse 13
Weeds
Whale Wars
Whistler
White Collar
World Series of Poker
The X Factor
You Have Been Watching"""
########NEW FILE########
__FILENAME__ = serieslytags
from django import template

register = template.Library()


@register.filter
def rfc3339(date):
    if date is None:
        return ""
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')

########NEW FILE########
__FILENAME__ = tvrage
#-*-coding:utf-8-*-
from xml.dom.minidom import parseString
import logging
import datetime
import urllib
import calendar

from pytz import utc

from helper.http import get as http_get
from helper.html import unescape
from helper.string_utils import normalize
from helper.dateutils import get_timezone_for_gmt_offset


monthsToNumber = dict((v,k) for k,v in enumerate(calendar.month_abbr))

class TVDataClass(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TVShowInfo(TVDataClass):
    pass


class TVSeasonInfo(TVDataClass):
    pass


class TVEpisodeInfo(TVDataClass):
    pass


class TVRage(object):
    show_info_url = "http://services.tvrage.com/feeds/full_show_info.php?sid=%d"
    search_info_url = "http://services.tvrage.com/feeds/search.php?%s"

    def get_info(self, show_id):
        """<Show>
        <name>Scrubs</name>
        <totalseasons>9</totalseasons>
        <showid>5118</showid>
        <showlink>http://tvrage.com/Scrubs</showlink>
        <started>Oct/02/2001</started>
        <ended></ended>
        <image>http://images.tvrage.com/shows/6/5118.jpg</image>
        <origin_country>US</origin_country>
        <status>Returning Series</status>
        <classification>Scripted</classification>
        <genres><genre>Comedy</genre></genres>
        <runtime>30</runtime>
        <network country="US">ABC</network>
        <airtime>21:00</airtime>
        <airday>Tuesday</airday>
        <timezone>GMT-5 -DST</timezone>
        <akas><aka country="LV">DakterÄ«Å¡i</aka><aka country="HU">Dokik</aka><aka country="SE">FÃ¶rsta hjÃ¤lpen</aka><aka country="NO">Helt sykt</aka><aka country="PL">HoÅ¼y doktorzy</aka><aka attr="Second Season" country="RU">Klinika</aka><aka attr="First Season" country="RU">Meditsinskaya akademiya</aka><aka country="DE">Scrubs: Die AnfÃ¤nger</aka><aka country="RO">Stagiarii</aka><aka attr="French Title" country="BE">Toubib or not toubib</aka><aka country="FI">Tuho Osasto</aka><aka country="IL">×¡×§×¨×‘×¡</aka></akas>
        <Episodelist>

        <Season no="1">
        <episode><epnum>1</epnum><seasonnum>01</seasonnum>
        <prodnum>535G</prodnum>
        <airdate>2001-10-02</airdate>
        <link>http://www.tvrage.com/Scrubs/episodes/149685</link>
        <title>My First Day</title>
        <screencap>http://images.tvrage.com/screencaps/26/5118/149685.jpg</screencap></episode>"""
        logging.debug("Start downloading...")
        show_xml = http_get(self.show_info_url % show_id)
        logging.debug("Start parsing...")
        dom = parseString(show_xml)
        logging.debug("Start walking...")
        show_doc = dom.getElementsByTagName("Show")[0]
        seasons = show_doc.getElementsByTagName("Season")
        special = show_doc.getElementsByTagName("Special")
        seasons.extend(special)
        timezone = show_doc.getElementsByTagName("timezone")[0].firstChild.data
        tz = get_timezone_for_gmt_offset(timezone)
        last_show_date = None
        delta_params = show_doc.getElementsByTagName("airtime")[0].firstChild.data.split(":")
        delta = datetime.timedelta(hours=int(delta_params[0]), minutes=int(delta_params[1]))
        season_list = []
        for season in seasons:
            try:
                season_nr = int(season.attributes["no"].value)
            except Exception:
                season_nr = False
            episode_list = []
            for episode in season.getElementsByTagName("episode"):
                if season_nr is False:
                    season_nr = int(episode.getElementsByTagName("season")[0].firstChild.data)
                try:
                    title = unescape(episode.getElementsByTagName("title")[0].firstChild.data)
                except AttributeError:
                    title = ""
                date_str = episode.getElementsByTagName("airdate")[0].firstChild.data
                try:
                    date = datetime.datetime(*map(int, date_str.split("-")))
                    date = date + delta
                    date = tz.localize(date)
                except ValueError:
                    date = None
                if date is not None:
                    if last_show_date is None or last_show_date < date:
                        last_show_date = date
                try:
                    epnum = int(episode.getElementsByTagName("seasonnum")[0].firstChild.data)
                except IndexError:
                    epnum = 0
                ep_info = TVEpisodeInfo(date=date, title=title, nr=epnum, season_nr=season_nr)
                episode_list.append(ep_info)
            season = TVSeasonInfo(season_nr=season_nr, episodes=episode_list)
            season_list.append(season)
        try:
            runtime = int(show_doc.getElementsByTagName("runtime")[0].firstChild.data)
        except IndexError:
            runtime = 30
        name = unescape(show_doc.getElementsByTagName("name")[0].firstChild.data)
        country = show_doc.getElementsByTagName("origin_country")[0].firstChild.data
        network = unescape(show_doc.getElementsByTagName("network")[0].firstChild.data)

        genres = show_doc.getElementsByTagName("genre")
        genre_list = []
        for genre in genres:
            if genre and genre.firstChild and genre.firstChild.data:
                genre_list.append(genre.firstChild.data)
        genre_str = "|".join(genre_list)
        active = show_doc.getElementsByTagName("ended")[0].firstChild
        if active is None or active.data == "0":
            active = True
        elif "/" in active.data:
            parts = active.data.split('/')
            if len(parts) == 3:
                try:
                    month = monthsToNumber[parts[0]]
                    day = int(parts[1])
                    year = int(parts[2])
                    if datetime.datetime.now() > datetime.datetime(year, month, day):
                        active = False
                    else:
                        active = True
                except (ValueError, KeyError):
                    active = True
            else:
                active = True
        else:
            active = False
        logging.debug("Return TVShowInfo...")
        return TVShowInfo(name=name,
                              seasons=season_list,
                              tvrage_id=show_id,
                              country=country,
                              runtime=runtime,
                              network=network,
                              timezone=timezone,
                              active=active,
                              genres=genre_str)

    def get_info_by_name(self, show_name):
        """<Results>
        <show>
        <showid>2445</showid>
        <name>24</name>
        <link>http://www.tvrage.com/24</link>
        <country>US</country>
        <started>2001</started>
        <ended>0</ended>
        <seasons>8</seasons>
        <status>Returning Series</status>
        <classification>Scripted</classification>
        <genres><genre01>Action</genre01><genre02>Adventure</genre02><genre03>Drama</genre03></genres>
        </show>
        <show>"""
        if show_name.endswith(", The"):
            show_name = show_name.replace(", The", "")
            show_name = "The " + show_name
        show_xml = http_get(self.search_info_url % urllib.urlencode({"show": show_name}))
        dom = parseString(show_xml)
        shows = dom.getElementsByTagName("show")
        show_id = None
        for show in shows:
            if normalize(unescape(show.getElementsByTagName("name")[0].firstChild.data)) == normalize(show_name):
                show_id = int(show.getElementsByTagName("showid")[0].firstChild.data)
                break
        if show_id is None:
            logging.warn("Did not really find %s" % show_name)
            if len(shows):
                logging.warn("Taking first")
                return self.get_info(int(shows[0].getElementsByTagName("showid")[0].firstChild.data))
            return None
        return self.get_info(show_id)


def main():
    tz = get_timezone_for_gmt_offset("GMT-5 -DST")
    date_str = "2011-01-31"
    date = datetime.datetime(*map(int, date_str.split("-")))
    delta = datetime.timedelta(hours=21, minutes=0)
    date = date + delta
    date = tz.localize(date)
    today = datetime.datetime.now(utc)
    print date >= today
    tvrage = TVRage()
    print tvrage.get_info(15614).active

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tvrage_quick
from google.appengine.api.urlfetch import fetch
import datetime


class TVRageFetcher(object):
    url = "http://www.tvrage.com/quickinfo.php?show=%(name)s&ep=%(season)dx%(episode)d"

    def __init__(self, show):
        self.show = show
        # TODO Add: filter("date >", today)
        self.last_episode = Episode.all().filter("show =", self.show.key()).order('-date').get()
        if last_episode is None:
            self.season_nr = 1
            self.episode_nr = 1
        else:
            self.season_nr = last_episode.season.number
            self.episode_nr = last_episode.number + 1

    def __iter__(self):
        return self

    def next(self):
        season_nr = self.season_nr
        episode_nr = self.episode_nr
        jumped_season = False
        while True:
            response = fetch(self.url % {"name": self.show.name, "season": season_nr, "episode": episode_nr})
            if response.status_code != 200:
                return
            info_dict = self.get_dict(response.content.split("\n"))
            if "Episode Info" not in info_dict and not jumped_season:
                jumped_season = True
                season_nr += 1
                episode_nr = 1
                continue
            elif "Episode Info" not in info_dict and jumped_season:
                return
            else:
                jumped_season = False
            season_nr = self.convert_seapisode(info_dict["Episode Info"][0])[0]
            episode_nr = self.convert_seapisode(info_dict["Episode Info"][0])[1]

            yield {
                "network": info_dict["Network"],
                "active": self.get_status(info_dict["Status"]),
                "country": info_dict["Country"],
                "runtime": int(info_dict["Runtime"])
            }, {
                "show": self.show,
                "number": season_nr,
                "start": self.get_start_date(info_dict),
                "end": self.get_start_date(info_dict)
            }, {
                "show": self.show,
                "number": episode_nr,
                "title": info_dict["Episode Info"][1],
                "date": self.get_start_date(info_dict)
            }

            if self.seapisode(info_dict["Latest Episode"][0]) == (season_nr, episode_nr):
                return
            episode_nr += 1
    __next__ = next

    def get_start_date(self, info):
        d = self.convert_datestring(info["Episode Info"][2])
        if "Airtime" in info:
            splits = info["Airtime"].split(" at ")  # Tuesday at 09:00 pm
            if len(splits) == 1:
                airtime = splits[0]
            else:
                airtime = splits[1]
            timeampm = airtime[1].split(" ")
            times = timeampm[0].split(":")
            if timeampm[1] == "pm":
                times[0] = int(times[0]) + 12
            td = datetime.timedelta(hours=int(times[0]), minutes=int(times[1]))
            d = d + td
        return d

    def get_status(self, status):
        status = status.lower()
        if "ended" in status or "canceled" in status:
            return False
        return True

    def convert_datestring(self, date_str):
        return datetime.datetime.strptime(date_str, "%b/%d/%Y")

    def convert_seapisode(self, seapisode_str):
        seapisode = seapisode_str.split("x")
        return (int(seapisode[0]), int(seapisode[1]))

    def get_dict(self, content):
        """Show Name@Alias
        Show URL@http://www.tvrage.com/Alias
        Premiered@2001
        Episode Info@02x04^Dead Drop^20/Oct/2002
        Episode URL@http://www.tvrage.com/Alias/episodes/4902
        Latest Episode@05x17^All the Time in the World^May/22/2006
        Country@USA
        Status@Canceled/Ended
        Classification@Scripted
        Genres@Action | Adventure | Drama
        Network@ABC
        Runtime@60


        Show Name@Lost
        Show URL@http://www.tvrage.com/Lost
        Premiered@2004
        Latest Episode@05x17^The Incident (2)^May/13/2009
        Next Episode@06x01^LA X (1)^Feb/02/2010
        RFC3339@2010-02-02T21:00:00-5:00
        Country@USA
        Status@Final Season
        Classification@Scripted
        Genres@Action | Adventure | Drama | Mystery
        Network@ABC
        Airtime@Tuesday at 09:00 pm
        Runtime@60"""
        info_dict = {}
        for line in content:
            line = line.strip()
            key, value = line.split("@", 1)
            if "^" in value:
                value = tuple(value.split("^"))
            info_dict[key] = value
        return info_dict

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin

urlpatterns = patterns('',
    (r'^import/$', 'series.views.import_show_task', {}, "seriesly-shows-import"),
    (r'^import_show/$', 'series.views.import_shows', {}, "seriesly-shows-import_show"),
    (r'^update/$', 'series.views.update', {}, "seriesly-shows-update"),
    (r'^update/show/$', 'series.views.update_show', {}, "seriesly-shows-update_show"),
    (r'^clear/cache/$', 'series.views.clear_cache', {}, "seriesly-shows-clear_cache"),
    (r'^episode/([0-9]+)', 'series.views.redirect_to_front', {}, "seriesly-shows-episode"),
#    (r'^update/(?P<seriesid>\d)?/?$', 'series.views.update'),
)

########NEW FILE########
__FILENAME__ = views
import logging

from google.appengine.api import users
from google.appengine.api import taskqueue

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.conf import settings

from helper import is_get, is_post
from series.models import Show, Episode


def import_shows(request):
    this_url = reverse("seriesly-shows-import_show")
    user = users.get_current_user()
    status = request.GET.get("status", None)
    if status is not None:
        status = "Shows are now being imported."
    nick = False
    if user:
        nick = user.nickname()
    if user and user.email() in settings.ADMIN_USERS:
        if request.method == "GET":
            return render_to_response("import_show.html", RequestContext(request,
                {"logged_in": True,
                    "nick": nick,
                    "status": status,
                    "logout_url": users.create_logout_url(this_url)}))
        else:
            shows = request.POST["show"]
            try:
                shows = [int(s.strip()) for s in shows.split(",")]
            except ValueError:
                return HttpResponse("Error: there was an invalid ID", status=400)
            for show in shows:
                t = taskqueue.Task(url=reverse('seriesly-shows-import'),
                        params={"show": str(show)})
                t.add(queue_name='series')
            return HttpResponseRedirect(this_url + "?status=Done")
    else:
        return render_to_response("import_show.html", RequestContext(request,
            {"logged_in": False, "nick": nick, "login_url": users.create_login_url(this_url),
            "logout_url": users.create_logout_url(this_url)}))


@is_post
def import_show_task(request):
    show_id = None
    try:
        show_id = request.POST.get("show", None)
        if show_id is None:
            raise Http404
        Show.update_or_create(None, int(show_id))
    except Http404:
        raise Http404
    except Exception, e:
        logging.error("Error Importing Show %s: %s" % (show_id, e))
        return HttpResponse("Done (with errors, %s))" % (show_id))
    logging.debug("Done importing show %s" % (show_id))
    return HttpResponse("Done: %s" % (show_id))


def update(request):
    shows = Show.get_all_ordered()
    for show in shows:
        show.add_update_task()
    Episode.add_clear_cache_task("series")
    return HttpResponse("Done: %d" % (len(shows)))


@is_post
def update_show(request):
    key = None
    show = None
    try:
        key = request.POST.get("key", None)
        if key is None:
            raise Http404
        show = Show.get_all_dict().get(key, None)
        if show is None:
            raise Http404
        show.update()
    except Http404:
        raise Http404
    except Exception, e:
        logging.error("Error Updating Show (%s)%s: %s" % (show, key, e))
        return HttpResponse("Done (with errors, %s(%s))" % (show, key))
    logging.debug("Done updating show %s(%s)" % (show, key))
    return HttpResponse("Done: %s(%s)" % (show, key))


def redirect_to_front(request, episode_id):
    return HttpResponseRedirect("/")


def clear_cache(request):
    Show.clear_cache()
    Episode.clear_cache()
    return HttpResponse("Done.")


@is_get
def redirect_to_amazon(request, show_id):
    show = Show.get_by_id(int(show_id))
    if show is None:
        raise Http404
    if not show.amazon_url:
        raise Http404
    return HttpResponseRedirect(show.amazon_url)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import os
ROOT_PATH = os.path.dirname(__file__)

from google.appengine.api import apiproxy_stub_map
have_appserver = bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))
on_production_server = have_appserver and \
    not os.environ.get('SERVER_SOFTWARE', '').lower().startswith('devel')


# Increase this when you update your media on the production site, so users
# don't have to refresh their cache. By setting this your MEDIA_URL
# automatically becomes /media/MEDIA_VERSION/
DEBUG = False

ADMIN_USERS = ()

MEDIA_VERSION = 1
if not on_production_server:
    DEBUG = True
# By hosting media on a different domain we can get a speedup (more parallel
# browser connections).
#if on_production_server or not have_appserver:
#    MEDIA_URL = 'http://media.mydomain.com/media/%d/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')
# 'project' refers to the name of the module created with django-admin.py
ROOT_URLCONF = 'urls'

DEFAULT_FROM_EMAIL = 'mail@seriesly.com'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

ADMIN_NAME = "Stefan Wehrmeyer"

DOMAIN_URL = "https://serieslycom.appspot.com"
SECURE_DOMAIN_URL = "https://serieslycom.appspot.com"

# Make this unique, and don't share it with anybody.
SECRET_KEY = '02ca0jaadlbjk;.93nfnvopm 40mu4w0daadlclm fniemcoia984<mHMImlkFUHA=")JRFP"Om'

TEMPLATE_CONTEXT_PROCESSORS = (
#    'django.core.context_processors.auth',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
#    'django.core.context_processors.i18n',
    'helper.context_processors.site_info',
)

MIDDLEWARE_CLASSES = (
   # 'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware',
   'django.middleware.common.CommonMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.middleware.doc.XViewMiddleware',
    'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware',
    'google.appengine.ext.ndb.django_middleware.NdbDjangoMiddleware',
)

INSTALLED_APPS = (

#    'django.contrib.auth',
#    'django.contrib.sessions',
#    'django.contrib.admin',
#    'django.contrib.webdesign',
#    'django.contrib.flatpages',
#    'django.contrib.redirects',
#    'django.contrib.sites',
    'series',
    'subscription',
    'helper',
    'statistics',
#    'mediautils',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".  Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    ROOT_PATH + '/templates',
)

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin

urlpatterns = patterns('',
    (r'^subscriptions/$', 'statistics.views.subscriptions', {}, "seriesly-statistics-subscriptions"),
    (r'^subscribed_shows/$', 'statistics.views.subscribed_shows', {}, "seriesly-statistics-subscribed_shows"),
    (r'^dump_subscriptions/$', 'statistics.views.dump_subscriptions', {}, "seriesly-statistics-dump_subscriptions"),
    (r'^memcache/$', 'statistics.views.memcache', {}, "seriesly-statistics-memcache"),
)

########NEW FILE########
__FILENAME__ = views
import datetime

from google.appengine.api.memcache import get_stats

from django.http import HttpResponse
from django.utils import simplejson as json

from subscription.models import Subscription, SubscriptionItem
from series.models import Show


def memcache(request):
    return HttpResponse("%s" % get_stats())


def subscriptions(request):
    now = datetime.datetime.now()
    threshold = now - datetime.timedelta(days=30 * 3)
    subcount = 0
    for subscription in Subscription.all():
        if subscription.last_visited is not None and subscription.last_visited > threshold:
            subcount += 1
    return HttpResponse("Done: \n%d" % subcount)


def subscribed_shows(request):
    subcount = 0
    show_ranking = {}
    user_ranking = {}
    for subitem in SubscriptionItem.all():
        # if subscription.last_visited is not None and subscription.last_visited > threshold:
        subcount += 1
        show_ranking.setdefault(subitem._show, 0)
        show_ranking[subitem._show] += 1
        user_ranking.setdefault(subitem._subscription, 0)
        user_ranking[subitem._subscription] += 1
    tops = []
    top_users = user_ranking.items()
    for show in Show.all():
        if show.active:
            tops.append((show.name, show_ranking.get(show.key(), 0)))
    tops.sort(key=lambda x: x[1], reverse=True)
    top_users.sort(key=lambda x: x[1], reverse=True)
    return HttpResponse("Done: <br/>%s" % "<br/>".join(map(lambda x: "%s: %d" % (x[0], x[1]), tops)) + "<hr/>" + "<br/>".join(map(lambda x: "%s: %d" % (x[0], x[1]), top_users)))


def dump_subscriptions(request):
    users = {}
    for subitem in SubscriptionItem.all():
        # if subscription.last_visited is not None and subscription.last_visited > threshold:
        users.setdefault(str(subitem._subscription), [])
        users[str(subitem._subscription)].append(str(subitem._show))
    return HttpResponse(json.dumps(users))

########NEW FILE########
__FILENAME__ = forms
from itertools import chain
import re

from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django import forms
from django.utils.safestring import mark_safe

from series.models import Show
from subscription.models import Subscription


def get_choices():
    shows = Show.get_all_ordered()
    return [(str(show.idnr),
            {"name": show.ordered_name, "new": show.is_new,
            "tvrage_id": show.tvrage_id}) for show in shows]


class HTML5EmailInput(forms.TextInput):
    input_type = 'email'


class HTML5URLInput(forms.TextInput):
    input_type = 'url'


class HTML5EmailField(forms.EmailField):
    widget = HTML5EmailInput

    def widget_attrs(self, widget):
        """
        Given a Widget instance (*not* a Widget class), returns a dictionary of
        any HTML attributes that should be added to the Widget, based on this
        Field.
        """
        return {
            "placeholder": "your.name@example.com",
            "class": "default-value email-sub"
        }


class HTML5XMPPField(forms.CharField):
    def widget_attrs(self, widget):
        """
        Given a Widget instance (*not* a Widget class), returns a dictionary of
        any HTML attributes that should be added to the Widget, based on this
        Field.
        """
        return {
            "placeholder": "account@example.com",
            "class": "default-value email-sub"
        }


class HTML5URLField(forms.CharField):
    widget = HTML5URLInput


class SerieslyCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        """From django.forms.widgets adapted to insert class"""
        if value is None:
            value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        # Normalize to strings
        output = []
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_dict) in enumerate(chain(self.choices, choices)):
            option_label = option_dict['name']
            option_new = option_dict['new']
            tvrage_id = option_dict['tvrage_id']
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''
            if option_new:
                label_new = ' class="new-show"'
            else:
                label_new = ''
            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value, attrs={"data-tvrage": str(tvrage_id)})
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'<li%s><label%s>%s %s</label></li>' % (label_new, label_for,
                rendered_cb, option_label))
        return mark_safe(u'\n'.join(output))


class SubscriptionForm(forms.Form):
    subkey = forms.CharField(required=False, widget=forms.HiddenInput)
    shows = forms.MultipleChoiceField(required=True, choices=get_choices(), widget=SerieslyCheckboxSelectMultiple,
        error_messages={'required': 'You need to select at least one show!'})

    def clean_subkey(self):
        subkey = self.cleaned_data["subkey"]
        if subkey != "":
            subscription = Subscription.all().filter("subkey =", subkey).get()
            if subscription is None:
                raise forms.ValidationError("You don't have a valid Seriesly Subscription Key")
            else:
                self._subscription = subscription
        return subkey

    def clean_shows(self):
        if len(self.cleaned_data["shows"]) > 90:
            raise forms.ValidationError("You can select 90 shows maximum!")
        return self.cleaned_data["shows"]

    def checkboxclean(self, key):
        if key in self.cleaned_data:
            self.cleaned_data[key] = True
        else:
            self.cleaned_data[key] = False
        return self.cleaned_data[key]


class MailSubscriptionForm(forms.Form):
    email = HTML5EmailField(required=False, label="Email",
            error_messages={'invalid': "This isn't a valid email address."})
    subkey = forms.CharField(required=True, widget=forms.HiddenInput)

    def clean_subkey(self):
        subkey = self.cleaned_data["subkey"]
        sub = Subscription.all().filter("subkey =", subkey).get()
        if sub is None:
            raise forms.ValidationError("You don't have a valid Seriesly Subscription Key")
        self._subscription = sub
        return subkey

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email == "your.name@example.com":
            email = ""
        return email

    def clean(self):
        cleaned_data = self.cleaned_data
        # if cleaned_data["email"] != "":
        #     self._errors["email"] = forms.util.ErrorList(
        #         ["This email address already has a subscription."]
        #     )
        #     del cleaned_data["email"]
        return cleaned_data


class XMPPSubscriptionForm(forms.Form):
    xmpp = HTML5XMPPField(required=False, label="XMPP-Address",
            error_messages={'invalid': "This isn't a valid xmpp address."})
    subkey = forms.CharField(required=True, widget=forms.HiddenInput)

    def clean_subkey(self):
        subkey = self.cleaned_data["subkey"]
        sub = Subscription.all().filter("subkey =", subkey).get()
        if sub is None:
            raise forms.ValidationError("You don't have a valid Seriesly Subscription Key")
        self._subscription = sub
        return subkey

    def clean_xmpp(self):
        xmpp = self.cleaned_data["xmpp"]
        if len(xmpp):
            match = re.match("^(?:([^@/<>'\"]+)@)?([^@/<>'\"]+)(?:/([^<>'\"]*))?$", xmpp)
            if match is None:
                raise forms.ValidationError("Sorry, that doesn't look like a valid XMPP Address.")
        return xmpp

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data["xmpp"] != "":
            sub = Subscription.all().filter("xmpp =", cleaned_data["xmpp"]).filter("subkey !=", self._subscription.subkey).get()
            if sub is not None:
                self._errors["xmpp"] = forms.util.ErrorList(["This XMPP address already belongs to a subscription."])
                del cleaned_data["xmpp"]
        return cleaned_data


class WebHookSubscriptionForm(forms.Form):
    webhook = HTML5URLField(required=False, label="Callback URL",
            error_messages={'invalid': "This isn't a valid HTTP URL."}, initial="http://")
    subkey = forms.CharField(required=True, widget=forms.HiddenInput)

    def clean_subkey(self):
        subkey = self.cleaned_data["subkey"]
        sub = Subscription.all().filter("subkey =", subkey).get()
        if sub is None:
            raise forms.ValidationError("You don't have a valid Seriesly Subscription Key")
        self._subscription = sub
        return subkey

    def clean_webhook(self):
        webhook = self.cleaned_data["webhook"]
        if len(webhook):
            if (not webhook.startswith("http://") and
                    not webhook.startswith("https://")):
                webhook = "http://" + webhook
            match = re.match("^https?://.+?$", webhook)
            if match is None:
                raise forms.ValidationError(
                    "Sorry, that doesn't look like a valid XMPP Address."
                )
        else:
            webhook = None
        return webhook


class SubscriptionKeyForm(forms.Form):
    subkey = forms.CharField(required=True, widget=forms.HiddenInput)

    def clean_subkey(self):
        subkey = self.cleaned_data["subkey"]
        sub = Subscription.all().filter("subkey =", subkey).get()
        if sub is None:
            raise forms.ValidationError("You don't have a valid Seriesly Subscription Key")
        self._subscription = sub
        return subkey

########NEW FILE########
__FILENAME__ = models
import random
import hashlib
import hmac
import datetime
import vobject

from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.api import xmpp
from google.appengine.api import taskqueue

from django.core.urlresolvers import reverse
from django.conf import settings

from helper.http import post as http_post

from series.models import Show, Episode


class Subscription(db.Model):
    subkey = db.StringProperty()
    last_visited = db.DateTimeProperty()
    last_changed = db.DateTimeProperty()
    activated_mail = db.BooleanProperty(default=False)
    email = db.StringProperty()
    activated_xmpp = db.BooleanProperty(default=False)
    xmpp = db.StringProperty()
    settings = db.TextProperty()
    webhook = db.StringProperty()
    public_id = db.StringProperty(default=None)

    feed_cache = db.TextProperty()
    feed_stamp = db.DateTimeProperty()
    calendar_cache = db.TextProperty()
    calendar_stamp = db.DateTimeProperty()

    feed_public_cache = db.TextProperty()
    feed_public_stamp = db.DateTimeProperty()

    show_cache = db.TextProperty()

    next_airtime = db.DateProperty(default=datetime.date(2010, 1, 1))

    BEACON_TIME = datetime.timedelta(days=30)

    @classmethod
    def kind(cls):
        return "subscription_subscription"

    def get_absolute_url(self):
        return reverse("seriesly-subscription-show", args=(self.subkey,))

    def get_domain_absolute_url(self):
        return settings.DOMAIN_URL + reverse("seriesly-subscription-show", args=(self.subkey,))

    def check_beacon_status(self, time):
        self.last_visited = time
        if self.last_visited is None or time - self.last_visited > self.BEACON_TIME:
            self.last_visited = time
            return True
        self.last_visited = time
        return False

    def needs_update(self, last_stamp, now):
        if last_stamp is None:
            return True
        diff = (now - last_stamp)
        max_distance = datetime.timedelta(hours=7)
        busy_distance = datetime.timedelta(minutes=20)
        normal_distance = datetime.timedelta(hours=3)
        if diff > max_distance:
            return True
        if (((last_stamp.hour > 5 and last_stamp.hour <= 13) or
                (now.hour > 5 and now.hour <= 13)) and
                diff > busy_distance):
            return True
        elif diff >= normal_distance:
            return True
        return False

    def check_confirmation_key(self, confirmkey):
        shouldbe = hmac.new(
            settings.SECRET_KEY,
            self.subkey,
            digestmod=hashlib.sha1
        ).hexdigest()
        # FIXME: constant time compare
        if confirmkey == shouldbe:
            return True
        return False

    def send_confirmation_mail(self):
        return Subscription.add_task('seriesly-subscription-send_confirm_mail', "mail-queue", self.key())

    def do_send_confirmation_mail(self):
        confirmation_key = hmac.new(settings.SECRET_KEY, self.subkey, digestmod=hashlib.sha1).hexdigest()
        confirmation_url = settings.DOMAIN_URL + reverse("seriesly-subscription-confirm_mail", args=(self.subkey, confirmation_key))
        sub_url = settings.DOMAIN_URL + reverse("seriesly-subscription-show", args=(self.subkey,))
        subject = "Confirm your seriesly.com email notifications"
        body = """Please confirm your email notifications for your favorite TV-Shows from seriesly.com by clicking the link below:

%s

You will only receive further emails from seriesly.com when you click the link.
If you did not expect this mail, you should ignore it.
By the way: your Seriesly subscription URL is: %s
""" % (confirmation_url, sub_url)
        mail.send_mail(settings.DEFAULT_FROM_EMAIL, self.email, subject, body)

    def send_invitation_xmpp(self):
        xmpp.send_invite(self.xmpp)

    def set_settings(self, d):
        self._cached_settings = d
        l = []
        for k, v in d.items():
            l.append("%s\t%s" % (k, v))
        self.settings = "\n".join(l)

    def get_settings(self):
        if hasattr(self, "_cached_settings"):
            return self._cached_settings
        lines = self.settings.split("\n")
        self._cached_settings = {}
        for l in lines:
            try:
                k, v = l.split("\t", 1)
                self._cached_settings[k] = v.strip()
            except ValueError:
                pass
        # FIXME: This is basically bad:
        for k, v in self._cached_settings.items():
            if v == "False":
                self._cached_settings[k] = False
            elif v == "True":
                self._cached_settings[k] = True
        return self._cached_settings

    @classmethod
    def generate_subkey(cls):
        return cls.generate_key("subkey")

    @classmethod
    def generate_key(cls, field="subkey"):
        CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        wtf = False
        while wtf is not None:
            key = ""
            for i in range(32):
                key += random.choice(CHARS)
            wtf = Subscription.all(keys_only=True).filter("%s =" % field, key).get()
        return key

    def get_shows(self):
        show_dict = Show.get_all_dict()
        return [show_dict[show_key] for show_key in self.get_show_cache() if show_key in show_dict]

    def get_shows_old(self):
        show_dict = Show.get_all_dict()
        return [show_dict[str(sub_item._show)] for sub_item in self.subscriptionitem_set if str(sub_item._show) in show_dict]

    def get_show_cache(self):
        if self.show_cache is None or not len(self.show_cache):
            self.set_show_cache([str(sub_item._show) for sub_item in self.subscriptionitem_set])
            self.put()
        return self.show_cache.split("|")

    def set_show_cache(self, show_keys):
        self.show_cache = '|'.join(show_keys)

    def set_shows(self, shows, old_shows=None):
        changes = False
        if old_shows is None:
            old_shows = []
        old_show_ids = [show.key() for show in old_shows]
        show_ids = [show.key() for show in shows]
        for show in shows:
            if not show.key() in old_show_ids:
                s = SubscriptionItem(subscription=self, show=show)
                s.put()
                changes = True
        for old_show in old_shows:
            if not old_show.key() in show_ids:
                key = SubscriptionItem.all(keys_only=True).filter(
                        "subscription =", self).filter(
                            "show =", old_show).get()
                if key:
                    db.delete(key)
                changes = True
        return changes

    def reset_cache(self, show_list):
        self.set_show_cache([str(show.key()) for show in show_list])
        # don't know next airtime
        self.next_airtime = datetime.date(2010, 1, 1)
        self.feed_stamp = None
        self.calendar_stamp = None
        self.feed_public_stamp = None

    @classmethod
    def add_email_task(cls, key):
        return cls.add_task('seriesly-subscription-mail', "mail-queue", key)

    @classmethod
    def add_xmpp_task(cls, key):
        return cls.add_task('seriesly-subscription-xmpp', "xmpp-queue", key)

    @classmethod
    def add_webhook_task(cls, key):
        return cls.add_task('seriesly-subscription-webhook', "webhook-queue", key)

    @classmethod
    def add_task(cls, url_name, queue_name, key):
        t = taskqueue.Task(url=reverse(url_name), params={"key": str(key)})
        t.add(queue_name=queue_name)
        return t

    def post_to_callback(self, body):
        response = http_post(self.webhook, body)
        if str(response.status_code)[0] != "2":
            raise IOError("Return status %s" % response.status_code)
        if len(response.content) > 0:
            raise ValueError("Returned content, is defined illegal")

    def get_message_context(self):
        the_shows = self.get_shows()
        now = datetime.datetime.now()
        twentyfour_hours_ago = now - datetime.timedelta(hours=24)
        episodes = Episode.get_for_shows(the_shows, after=twentyfour_hours_ago, order="date")
        if not len(episodes):
            return None
        context = {"subscription": self, "items": []}
        for episode in episodes:
            if episode.date > now:
                self.next_airtime = episode.date.date()
                break
            context["items"].append(episode)
        if not context["items"]:
            return None
        return context

    def get_icalendar(self, public):
        """Nice hints from here: http://blog.thescoop.org/archives/2007/07/31/django-ical-and-vobject/"""
        the_shows = self.get_shows()
        # two_weeks_ago = now - datetime.timedelta(days=7)
        # five_hours = datetime.timedelta(hours=5)
        # sub_settings = self.get_settings()
        self.get_settings()
        episodes = Episode.get_for_shows(the_shows, order="date")
        cal = vobject.iCalendar()
        cal.add('method').value = 'PUBLISH'  # IE/Outlook needs this
        for episode in episodes:
            episode.create_event_details(cal)
        return cal.serialize()


class SubscriptionItem(db.Model):
    subscription = db.ReferenceProperty(Subscription)
    show = db.ReferenceProperty(Show)

    @classmethod
    def kind(cls):
        return "subscription_subscriptionitem"

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^edit/mail/$', 'subscription.views.edit_mail', {}, 'seriesly-subscription-edit_mail'),
    (r'^mail-task/$', 'subscription.views.email_task', {}, "seriesly-subscription-email_task"),
    (r'^confirmmail/$', 'subscription.views.send_confirm_mail', {}, "seriesly-subscription-send_confirm_mail"),
    (r'^mail/$', 'subscription.views.send_mail', {}, "seriesly-subscription-mail"),

    (r'^edit/xmpp/$', 'subscription.views.edit_xmpp', {}, 'seriesly-subscription-edit_xmpp'),
    (r'^xmpp-task/$', 'subscription.views.xmpp_task', {}, "seriesly-subscription-xmpp_task"),
    (r'^xmpp/$', 'subscription.views.send_xmpp', {}, "seriesly-subscription-xmpp"),

    (r'^edit/webhook/$', 'subscription.views.edit_webhook', {}, 'seriesly-subscription-edit_webhook'),
    (r'^webhook-task/$', 'subscription.views.webhook_task', {}, "seriesly-subscription-webhook_task"),
    (r'^webhook/$', 'subscription.views.post_to_callback', {}, "seriesly-subscription-webhook"),

    (r'^toggle/public-urls$', 'subscription.views.edit_public_id', {}, "seriesly-subscription-edit_public_id"),

    (r'^next-airtime-task/$', 'subscription.views.add_next_airtime_task', {}, "seriesly-subscription-add_next_airtime_task"),
    (r'^next-airtime/$', 'subscription.views.set_next_airtime', {}, "seriesly-subscription-set_next_airtime"),

)

########NEW FILE########
__FILENAME__ = views
import datetime
import logging
import re

from google.appengine.api import xmpp
from google.appengine.api import mail
from google.appengine.ext import db

from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.conf import settings

from helper import is_post
from series.models import Show, Episode
from subscription.forms import SubscriptionForm, MailSubscriptionForm, \
    XMPPSubscriptionForm, WebHookSubscriptionForm, SubscriptionKeyForm
from subscription.models import Subscription

WORD = re.compile("^\w+$")


def index(request, form=None, extra_context=None):
    if form is None:
        form = SubscriptionForm()
    context = {"form": form}
    if extra_context is not None:
        context.update(extra_context)
    return render_to_response("index.html", RequestContext(request, context))


@is_post
def subscribe(request):
    form = SubscriptionForm(request.POST)
    if not form.is_valid():
        return index(request, form=form)
    editing = False
    if form.cleaned_data["subkey"] == "":
        subkey = Subscription.generate_subkey()
        subscription = Subscription(last_changed=datetime.datetime.now(), subkey=subkey)
    else:
        editing = True
        subkey = form.cleaned_data["subkey"]
        subscription = form._subscription
    sub_settings = {}
    subscription.set_settings(sub_settings)

    try:
        selected_shows = Show.get_by_id(map(int, form.cleaned_data["shows"]))
    except ValueError:
        return index(request, form=form)

    old_shows = []
    if editing:
        old_shows = subscription.get_shows()

    subscription.reset_cache(selected_shows)
    subscription.put()  # stay here, need key for setting shows!

    if editing:
        subscription.set_shows(selected_shows, old_shows=old_shows)
    else:
        subscription.set_shows(selected_shows)

    response = HttpResponseRedirect(subscription.get_absolute_url())
    response.set_cookie("subkey", subkey, max_age=31536000)
    return response


def show(request, subkey, extra_context=None):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    if extra_context is None:
        extra_context = {}
    if "mail_form" in extra_context:
        subscription.mail_form = extra_context["mail_form"]
    else:
        subscription.mail_form = MailSubscriptionForm({"email": subscription.email, "subkey": subkey})
    if "xmpp_form" in extra_context:
        subscription.xmpp_form = extra_context["xmpp_form"]
    else:
        subscription.xmpp_form = XMPPSubscriptionForm({"xmpp": subscription.xmpp, "subkey": subkey})
    if "webhook_form" in extra_context:
        subscription.webhook_form = extra_context["webhook_form"]
    else:
        subscription.webhook_form = WebHookSubscriptionForm({"webhook": subscription.webhook, "subkey": subkey})
    if "public_id_form" in extra_context:
        subscription.public_id_form = extra_context["public_id_form"]
    else:
        subscription.public_id_form = SubscriptionKeyForm({"subkey": subkey})
    subscription.sub_settings = subscription.get_settings()
    response = render_to_response("subscription.html",
        RequestContext(
            request,
            {
                "shows": subscription.get_shows(),
                "subscription": subscription
            }
        ))
    response.set_cookie("subkey", subkey, max_age=31536000)
    return response


def show_public(request, public_id):
    subscription = Subscription.all().filter("public_id =", public_id).get()
    if subscription is None:
        raise Http404
    response = render_to_response("subscription_public.html",
        RequestContext(
            request,
            {
                "shows": subscription.get_shows(),
                "subscription": subscription
            }
        ))
    return response


def edit(request, subkey):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    if request.method == "GET":
        subscription.get_settings()
        sub_dict = {
            "email": subscription.email,
            "shows": map(lambda x: x.idnr, subscription.get_shows()),
            "subkey": subkey
        }
        form = SubscriptionForm(sub_dict)
        return index(request, form=form, extra_context={"subscription": subscription})
    return HttpResponseRedirect(subscription.get_absolute_url())


@is_post
def edit_public_id(request):
    form = SubscriptionKeyForm(request.POST)
    if not form.is_valid():
        return show(
            request,
            request.POST.get("subkey", ""),
            extra_context={"public_id_form": form}
        )
    subscription = form._subscription
    if subscription.public_id is None:
        subscription.public_id = Subscription.generate_key("public_id")
    else:
        subscription.public_id = None
    subscription.put()
    return HttpResponseRedirect(subscription.get_absolute_url() + "#public-urls")


def feed_rss(request, subkey):
    return feed(request, subkey, template="rss.xml")


def feed_atom(request, subkey, template="atom.xml"):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    now = datetime.datetime.now()
    if subscription.needs_update(subscription.feed_stamp, now):
        subscription.check_beacon_status(now)
        # don't specify encoding for unicode strings!
        subscription.feed_cache = db.Text(_feed(request, subscription, template))
        subscription.feed_stamp = now
        try:
            subscription.put()  # this put is not highly relevant
        except Exception, e:
            logging.warning(e)
    return HttpResponse(subscription.feed_cache, mimetype="application/atom+xml")


def feed(request, subkey, template):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    body = _feed(request, subscription, template)
    mimetype = "application/atom+xml"
    if "rss" in template:
        mimetype = "application/rss+xml"
    return HttpResponse(body, mimetype=mimetype)


def feed_atom_public(request, public_id, template="atom_public.xml"):
    subscription = Subscription.all().filter("public_id =", public_id).get()
    if subscription is None:
        raise Http404
    now = datetime.datetime.now()
    if subscription.needs_update(subscription.feed_public_stamp, now):
        subscription.check_beacon_status(now)
        # don't specify encoding for unicode strings!
        subscription.feed_public_cache = db.Text(_feed(request, subscription, template, public=True))
        subscription.feed_public_stamp = now
        try:
            subscription.put()  # this put is not highly relevant
        except Exception, e:
            logging.warning(e)
    return HttpResponse(subscription.feed_public_cache, mimetype="application/atom+xml")


def feed_rss_public(request, public_id, template="rss_public.xml"):
    subscription = Subscription.all().filter("public_id =", public_id).get()
    if subscription is None:
        raise Http404
    return HttpResponse(_feed(request, subscription, template, public=True), mimetype="application/rss+xml")


def _feed(request, subscription, template, public=False):
    now = datetime.datetime.now()
    subscription.get_settings()
    subscription.updated = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    subscription.expires = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    the_shows = subscription.get_shows()
    wait_time = datetime.timedelta(hours=6)
    episodes = Episode.get_for_shows(the_shows, before=now, order="-date")
    items = []
    for episode in episodes:
        if now > episode.date + wait_time:
            pub_date = episode.date_local
            episode.pub_date = pub_date
            items.append(episode)
    return render_to_string(
        template,
        RequestContext(
            request,
            {"subscription": subscription, "items": items}
        ))


def calendar(request, subkey):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    return _calendar(request, subscription)


def calendar_public(request, public_id):
    subscription = Subscription.all().filter("public_id =", public_id).get()
    if subscription is None:
        raise Http404
    return _calendar(request, subscription, public=True)


def _calendar(request, subscription, public=False):
    now = datetime.datetime.now()
    if subscription.needs_update(subscription.calendar_stamp, now):
        subscription.check_beacon_status(now)
        subscription.calendar_stamp = now
        # specify encoding for byte strings!
        subscription.calendar_cache = db.Text(subscription.get_icalendar(public), encoding="utf8")
        try:
            subscription.put()  # this put is not highly relevant
        except Exception, e:
            logging.warning(e)
    response = HttpResponse(subscription.calendar_cache, mimetype='text/calendar')
    response['Filename'] = 'seriesly-calendar.ics'  # IE needs this
    response['Content-Disposition'] = 'attachment; filename=seriesly-calendar.ics'
    return response


def guide(request, subkey):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    return _guide(request, subscription)


def guide_public(request, public_id):
    subscription = Subscription.all().filter("public_id =", public_id).get()
    if subscription is None:
        raise Http404
    return _guide(request, subscription, template="guide_public.html", public=True)


def _guide(request, subscription, template="guide.html",
           public=False, extra_context=None):
    subscription.is_public = public
    subscription.get_settings()
    now = datetime.datetime.now()
    the_shows = subscription.get_shows()
    episodes = Episode.get_for_shows(the_shows, order="date")
    twentyfour_hours_ago = now - datetime.timedelta(hours=24)
    recently = []
    last_week = []
    upcoming = []
    for episode in episodes:
        if episode.date < twentyfour_hours_ago:
            last_week.append(episode)
        elif episode.date <= now:
            recently.append(episode)
        else:
            upcoming.append(episode)
    context = {
        "subscription": subscription,
        "recently": recently,
        "upcoming": upcoming,
        "last_week": last_week
    }
    if extra_context is not None:
        context.update(extra_context)
    response = render_to_response(template, RequestContext(request, context))
    if not public:
        response.set_cookie("subkey", subscription.subkey)
    try:
        if subscription.check_beacon_status(now):
            subscription.put()  # this put is not highly relevant
    except Exception, e:
        logging.warning(e)
    return response


@is_post
def edit_mail(request):
    form = MailSubscriptionForm(request.POST)
    if not form.is_valid():
        return show(
            request,
            request.POST.get("subkey", ""),
            extra_context={"mail_form": form}
        )
    subscription = form._subscription
    if subscription.email != form.cleaned_data["email"]:
        subscription.activated_mail = False
    subscription.email = form.cleaned_data["email"]
    subscription.last_changed = datetime.datetime.now()
    subscription.put()
    if subscription.email != "" and subscription.activated_mail is False:
        subscription.send_confirmation_mail()
    return HttpResponseRedirect(subscription.get_absolute_url() + "#email")


def confirm_mail(request, subkey, confirmkey):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    if subscription.check_confirmation_key(confirmkey):
        if (subscription.activated_mail is False and
                subscription.email != ""):
            subscription.activated_mail = True
            subscription.put()
        return HttpResponseRedirect(
            subscription.get_absolute_url() + "#email"
        )
    else:
        raise Http404


def send_confirm_mail(request):
    key = None
    try:
        key = request.POST.get("key", None)
        if key is None:
            raise Http404
        subscription = Subscription.get(key)
        if subscription is None:
            raise Http404
    except Exception, e:
        logging.error(e)
        return HttpResponse("Done (with errors): %s" % key)
    subscription.do_send_confirmation_mail()
    logging.debug("Done sending Confirmation Mail to %s" % subscription.email)
    return HttpResponse("Done: %s" % key)


def email_task(request):
    filter_date = datetime.datetime.now().date() + datetime.timedelta(days=1)
    subscription_keys = Subscription.all(keys_only=True).filter("activated_mail =", True)\
            .filter("next_airtime <=", filter_date)
    counter = 0
    for key in subscription_keys:
        Subscription.add_email_task(key)
        counter += 1
    return HttpResponse("Done: added %d" % counter)


@is_post
def send_mail(request):
    key = None
    try:
        key = request.POST.get("key", None)
        if key is None:
            raise Http404
        subscription = Subscription.get(key)
        if subscription is None:
            raise Http404

        # quick fix for running tasks
        if subscription.email == "":
            subscription.activated_mail = False
            subscription.put()
            return HttpResponse("Skipping early.")
        context = subscription.get_message_context()
        if context is None:
            return HttpResponse("Nothing to do.")
        subscription.check_beacon_status(datetime.datetime.now())
        subject = "Seriesly.com - %d new episodes" % len(context["items"])
        body = render_to_string("subscription_mail.txt", RequestContext(request, context))
    except Exception, e:
        logging.error(e)
        return HttpResponse("Done (with errors): %s" % key)
    # let mail sending trigger an error to allow retries
    mail.send_mail(settings.DEFAULT_FROM_EMAIL, subscription.email, subject, body)
    try:
        subscription.put()  # this put is not highly relevant
    except Exception, e:
        logging.warning(e)
    return HttpResponse("Done: %s" % key)


def xmpp_task(request):
    subscription_keys = Subscription.all(keys_only=True).filter("activated_xmpp =", True)
        # .filter("next_airtime <", datetime.datetime.now().date())
    counter = 0
    for key in subscription_keys:
        Subscription.add_xmpp_task(key)
        counter += 1
    return HttpResponse("Done: added %d" % counter)


@is_post
def send_xmpp(request):
    key = None
    try:
        key = request.POST.get("key", None)
        if key is None:
            raise Http404
        subscription = Subscription.get(key)
        if subscription is None:
            raise Http404
        subscription.check_beacon_status(datetime.datetime.now())
        context = subscription.get_message_context()
        if context is None:
            return HttpResponse("Nothing to do.")
        body = render_to_string("subscription_xmpp.txt", RequestContext(request, context))
    except Exception, e:
        logging.error(e)
        return HttpResponse("Done (with errors): %s" % key)
    status_code = xmpp.send_message(subscription.xmpp, body)
    jid_broken = (status_code == xmpp.INVALID_JID)
    if jid_broken:
        subscription.xmpp = None
        subscription.xmpp_activated = False
    try:
        subscription.put()
    except Exception, e:
        logging.warn(e)
    return HttpResponse("Done: %s" % key)


@is_post
def edit_xmpp(request):
    form = XMPPSubscriptionForm(request.POST)
    if not form.is_valid():
        return show(
            request,
            request.POST.get("subkey", ""),
            extra_context={"xmpp_form": form}
        )
    subscription = form._subscription
    if subscription.xmpp != form.cleaned_data["xmpp"]:
        subscription.activated_xmpp = False
    subscription.xmpp = form.cleaned_data["xmpp"]
    subscription.last_changed = datetime.datetime.now()
    if subscription.xmpp != "" and subscription.activated_xmpp is False:
        try:
            subscription.send_invitation_xmpp()
        except Exception:
            form.errors["xmpp"] = ["Could not send invitation to this XMPP address"]
            return show(
                request,
                request.POST.get("subkey", ""),
                extra_context={"xmpp_form": form}
            )
    subscription.put()
    return HttpResponseRedirect(subscription.get_absolute_url() + "#xmpp")


def incoming_xmpp(request):
    try:
        message = xmpp.Message(request.POST)
    except Exception, e:
        logging.warn("Failed to parse XMPP Message: %s" % e)
        return HttpResponse()
    sender = message.sender.split("/")[0]
    subscription = Subscription.all().filter("xmpp =", sender).get()
    if subscription is None:
        message.reply("I don't know you. Please create a Seriesly subscription at http://www.seriesly.com")
        logging.warn("Sender not found: %s" % sender)
        return HttpResponse()
    if not subscription.activated_xmpp and message.body == "OK":
        subscription.activated_xmpp = True
        subscription.put()
        message.reply("Your Seriesly XMPP Subscription is now activated.")
    elif not subscription.activated_xmpp:
        message.reply("Someone requested this Seriesly Subscription to your XMPP address: %s . Please type 'OK' to confirm." % subscription.get_domain_absolute_url())
    else:
        message.reply("Your Seriesly XMPP Subscription is active. Go to %s to change settings." % subscription.get_domain_absolute_url())
    return HttpResponse()


@is_post
def edit_webhook(request):
    form = WebHookSubscriptionForm(request.POST)
    if not form.is_valid():
        return show(
            request,
            request.POST.get("subkey", ""),
            extra_context={"webhook_form": form}
        )
    subscription = form._subscription
    subscription.webhook = form.cleaned_data["webhook"]
    subscription.last_changed = datetime.datetime.now()
    subscription.put()
    return HttpResponseRedirect(subscription.get_absolute_url() + "#webhook")


def webhook_task(request):
    """BadFilterError: invalid filter: Only one property per query may have inequality filters (<=, >=, <, >).."""
    subscriptions = Subscription.all().filter("webhook !=", None)
    counter = 0
    for obj in subscriptions:
        Subscription.add_webhook_task(obj.key())
        counter += 1
    return HttpResponse("Done: added %d" % counter)


@is_post
def test_webhook(request, subkey):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None or subscription.webhook is None:
        raise Http404
    Subscription.add_webhook_task(subscription.key())
    return HttpResponse("Task for posting to %s added. Will run in some seconds. Be reminded of The Rules on http://www.seriesly.com/webhook-xml/#the-rules" % subscription.webhook)


@is_post
def post_to_callback(request):
    key = None
    webhook = None
    try:
        key = request.POST.get("key", None)
        if key is None:
            raise Http404
        subscription = Subscription.get(key)
        if subscription is None:
            raise Http404
        subscription.check_beacon_status(datetime.datetime.now())

        context = subscription.get_message_context()
        if context is None:
            return HttpResponse("Nothing to do.")
        body = render_to_string("subscription_webhook.xml", RequestContext(request, context))
        webhook = subscription.webhook
        try:
            subscription.post_to_callback(body)
        except Exception, e:
            subscription.webhook = None
            logging.warn("Webhook failed (%s): %s" % (key, e))

        subscription.put()
    except Exception, e:
        logging.error(e)
        return HttpResponse("Done (with errors): %s" % key)
    logging.debug("Done sending Webhook Callback to %s" % webhook)
    return HttpResponse("Done: %s" % key)


def get_extra_json_context(request):
    callback = request.GET.get("callback", None)
    extra_context = {"callback": None}
    if callback is not None and WORD.match(callback) is not None:
        extra_context = {"callback": callback}
    return extra_context


def json(request, subkey):
    subscription = Subscription.all().filter("subkey =", subkey).get()
    if subscription is None:
        raise Http404
    response = _guide(request, subscription, template="widget.json",
        extra_context=get_extra_json_context(request))
    response["Content-Type"] = 'application/json'
    return response


def json_public(request, public_id):
    subscription = Subscription.all().filter("public_id =", public_id).get()
    if subscription is None:
        raise Http404
    response = _guide(request, subscription, template="widget.json",
        public=True, extra_context=get_extra_json_context(request))
    response["Content-Type"] = 'application/json'
    return response

# TODO: Check if import here makes any special sense
from google.appengine.api import taskqueue


def add_next_airtime_task(request):
    for key in Subscription.all(keys_only=True).filter("activated_mail =", True):
        t = taskqueue.Task(url="/subscription/next-airtime/", params={"key": str(key)})
        t.add(queue_name="webhook-queue")
    return HttpResponse("Done: ")


def set_next_airtime(request):
    key = None
    key = request.POST.get("key", None)
    if key is None:
        raise Http404
    subscription = Subscription.get(key)
    subscription.next_airtime = datetime.date(2010, 1, 1)
    subscription.put()
    return HttpResponse("Done: %s" % key)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, include
from django.views.generic.simple import direct_to_template, redirect_to

urlpatterns = patterns('',
    (r'^$', 'subscription.views.index', {}, 'seriesly-index'),
    (r'^faq/$', direct_to_template, {"template": "faq.html"}, "seriesly-faq"),
    (r'^imprint/$', redirect_to, {'url': '/about/#impressum'}),
    (r'^terms/$', direct_to_template, {"template": "terms.html"}, "seriesly-terms"),
    (r'^about/$', direct_to_template, {"template": "about.html"}, "seriesly-about"),
    (r'^privacy/$', direct_to_template, {"template": "privacy.html"}, "seriesly-privacy"),
    (r'^missing/$', direct_to_template, {"template": "missing.html"}, "seriesly-missing"),
    (r'^webhook-xml/$', direct_to_template, {"template": "webhook_xml.html"}, "seriesly-webhook-xml"),
    (r'^subscribe/$', 'subscription.views.subscribe', {}, 'seriesly-subscribe'),
    (r'^shows/', include('series.urls')),
    (r'^subscription/', include('subscription.urls')),
    (r'^statistics/', include('statistics.urls')),
    (r'^_ah/xmpp/message/chat/$', 'subscription.views.incoming_xmpp', {}, 'seriesly-incoming_xmpp'),
    (r'^public/([A-Za-z0-9]{32})/$', 'subscription.views.show_public', {}, 'seriesly-subscription-show_public'),
    (r'^public/([A-Za-z0-9]{32})/guide/$', 'subscription.views.guide_public', {}, 'seriesly-subscription-guide_public'),
    (r'^public/([A-Za-z0-9]{32})/rss/$', 'subscription.views.feed_rss_public', {}, 'seriesly-subscription-rss_public'),
    (r'^public/([A-Za-z0-9]{32})/feed/$', 'subscription.views.feed_atom_public', {}, 'seriesly-subscription-atom_public'),
    (r'^public/([A-Za-z0-9]{32})/calendar/$', 'subscription.views.calendar_public', {}, 'seriesly-subscription-calendar_public'),
    (r'^public/([A-Za-z0-9]{32})/json/$', 'subscription.views.json_public', {}, 'seriesly-subscription-json_public'),

    (r'^([A-Za-z0-9]{32})/$', 'subscription.views.show', {}, 'seriesly-subscription-show'),
    (r'^([A-Za-z0-9]{32})/confirm/([a-f0-9]{40})/$', 'subscription.views.confirm_mail', {}, 'seriesly-subscription-confirm_mail'),
    (r'^([A-Za-z0-9]{32})/edit/$', 'subscription.views.edit', {}, 'seriesly-subscription-edit'),
    (r'^([A-Za-z0-9]{32})/guide/$', 'subscription.views.guide', {}, 'seriesly-subscription-guide'),
    (r'^([A-Za-z0-9]{32})/rss/$', 'subscription.views.feed_rss', {}, 'seriesly-subscription-rss'),
    (r'^([A-Za-z0-9]{32})/feed/$', 'subscription.views.feed_atom', {}, 'seriesly-subscription-atom'),
    (r'^([A-Za-z0-9]{32})/calendar/$', 'subscription.views.calendar', {}, 'seriesly-subscription-calendar'),
    (r'^([A-Za-z0-9]{32})/json/$', 'subscription.views.json', {}, 'seriesly-subscription-json'),
    (r'^([A-Za-z0-9]{32})/webhook-test/$', 'subscription.views.test_webhook', {}, 'seriesly-subscription-test_webhook'),
)

########NEW FILE########
__FILENAME__ = base
"""vobject module for reading vCard and vCalendar files."""

import copy
import re
import sys
import logging
import StringIO, cStringIO
import string
import exceptions
import codecs

#------------------------------------ Logging ----------------------------------
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.ERROR) # Log errors
DEBUG = False # Don't waste time on debug calls
#----------------------------------- Constants ---------------------------------
CR     = '\r'
LF     = '\n'
CRLF   = CR + LF
SPACE  = ' '
TAB    = '\t'
SPACEORTAB = SPACE + TAB
#-------------------------------- Useful modules -------------------------------
#   use doctest, it kills two birds with one stone and docstrings often become
#                more readable to boot (see parseLine's docstring).
#   use logging, then when debugging we can just set our verbosity.
#   use epydoc syntax for documenting code, please document every class and non-
#                trivial method (see http://epydoc.sourceforge.net/epytext.html
#                and http://epydoc.sourceforge.net/fields.html).  Also, please
#                follow http://www.python.org/peps/pep-0257.html for docstrings.
#-------------------------------------------------------------------------------

#--------------------------------- Main classes --------------------------------
class VBase(object):
    """Base class for ContentLine and Component.
    
    @ivar behavior:
        The Behavior class associated with this object, which controls
        validation, transformations, and encoding.
    @ivar parentBehavior:
        The object's parent's behavior, or None if no behaviored parent exists.
    @ivar isNative:
        Boolean describing whether this component is a Native instance.
    @ivar group:
        An optional group prefix, should be used only to indicate sort order in 
        vCards, according to RFC2426
    """
    def __init__(self, group=None, *args, **kwds):
        super(VBase, self).__init__(*args, **kwds)
        self.group      = group
        self.behavior   = None
        self.parentBehavior = None
        self.isNative = False
    
    def copy(self, copyit):
        self.group = copyit.group
        self.behavior = copyit.behavior
        self.parentBehavior = copyit.parentBehavior
        self.isNative = copyit.isNative
        
    def validate(self, *args, **kwds):
        """Call the behavior's validate method, or return True."""
        if self.behavior:
            return self.behavior.validate(self, *args, **kwds)
        else: return True

    def getChildren(self):
        """Return an iterable containing the contents of the object."""
        return []

    def clearBehavior(self, cascade=True):
        """Set behavior to None. Do for all descendants if cascading."""
        self.behavior=None
        if cascade: self.transformChildrenFromNative()

    def autoBehavior(self, cascade=False):
        """Set behavior if name is in self.parentBehavior.knownChildren.
        
        If cascade is True, unset behavior and parentBehavior for all
        descendants, then recalculate behavior and parentBehavior.
        
        """
        parentBehavior = self.parentBehavior
        if parentBehavior is not None:
            knownChildTup = parentBehavior.knownChildren.get(self.name, None)
            if knownChildTup is not None:
                behavior = getBehavior(self.name, knownChildTup[2])
                if behavior is not None:
                    self.setBehavior(behavior, cascade)
                    if isinstance(self, ContentLine) and self.encoded:
                        self.behavior.decode(self)
            elif isinstance(self, ContentLine):
                self.behavior = parentBehavior.defaultBehavior   
                if self.encoded and self.behavior:
                    self.behavior.decode(self)

    def setBehavior(self, behavior, cascade=True):
        """Set behavior. If cascade is True, autoBehavior all descendants."""
        self.behavior=behavior
        if cascade:
            for obj in self.getChildren():
                obj.parentBehavior=behavior
                obj.autoBehavior(True)

    def transformToNative(self):
        """Transform this object into a custom VBase subclass.
        
        transformToNative should always return a representation of this object.
        It may do so by modifying self in place then returning self, or by
        creating a new object.
        
        """
        if self.isNative or not self.behavior or not self.behavior.hasNative:
            return self
        else:
            try:
                return self.behavior.transformToNative(self)
            except Exception, e:      
                # wrap errors in transformation in a ParseError
                lineNumber = getattr(self, 'lineNumber', None)
                if isinstance(e, ParseError):
                    if lineNumber is not None:
                        e.lineNumber = lineNumber
                    raise
                else:
                    msg = "In transformToNative, unhandled exception: %s: %s"
                    msg = msg % (sys.exc_info()[0], sys.exc_info()[1])
                    new_error = ParseError(msg, lineNumber)
                    raise ParseError, new_error, sys.exc_info()[2]
                

    def transformFromNative(self):
        """Return self transformed into a ContentLine or Component if needed.
        
        May have side effects.  If it does, transformFromNative and
        transformToNative MUST have perfectly inverse side effects. Allowing
        such side effects is convenient for objects whose transformations only
        change a few attributes.
        
        Note that it isn't always possible for transformFromNative to be a
        perfect inverse of transformToNative, in such cases transformFromNative
        should return a new object, not self after modifications.
        
        """
        if self.isNative and self.behavior and self.behavior.hasNative:
            try:
                return self.behavior.transformFromNative(self)
            except Exception, e:
                # wrap errors in transformation in a NativeError
                lineNumber = getattr(self, 'lineNumber', None)
                if isinstance(e, NativeError):
                    if lineNumber is not None:
                        e.lineNumber = lineNumber
                    raise
                else:
                    msg = "In transformFromNative, unhandled exception: %s: %s"
                    msg = msg % (sys.exc_info()[0], sys.exc_info()[1])
                    new_error = NativeError(msg, lineNumber)
                    raise NativeError, new_error, sys.exc_info()[2]
        else: return self

    def transformChildrenToNative(self):
        """Recursively replace children with their native representation."""
        pass

    def transformChildrenFromNative(self, clearBehavior=True):
        """Recursively transform native children to vanilla representations."""
        pass

    def serialize(self, buf=None, lineLength=75, validate=True, behavior=None):
        """Serialize to buf if it exists, otherwise return a string.
        
        Use self.behavior.serialize if behavior exists.
        
        """
        if not behavior:
            behavior = self.behavior
        
        if behavior:
            if DEBUG: logger.debug("serializing %s with behavior" % self.name)
            return behavior.serialize(self, buf, lineLength, validate)
        else:
            if DEBUG: logger.debug("serializing %s without behavior" % self.name)
            return defaultSerialize(self, buf, lineLength)

def ascii(s):
    """Turn s into a printable string.  Won't work for 8-bit ASCII."""
    return unicode(s).encode('ascii', 'replace')

def toVName(name, stripNum = 0, upper = False):
    """
    Turn a Python name into an iCalendar style name, optionally uppercase and 
    with characters stripped off.
    """
    if upper:
        name = name.upper()
    if stripNum != 0:
        name = name[:-stripNum]
    return name.replace('_', '-')

class ContentLine(VBase):
    """Holds one content line for formats like vCard and vCalendar.

    For example::
      <SUMMARY{u'param1' : [u'val1'], u'param2' : [u'val2']}Bastille Day Party>

    @ivar name:
        The uppercased name of the contentline.
    @ivar params:
        A dictionary of parameters and associated lists of values (the list may
        be empty for empty parameters).
    @ivar value:
        The value of the contentline.
    @ivar singletonparams:
        A list of parameters for which it's unclear if the string represents the
        parameter name or the parameter value. In vCard 2.1, "The value string
        can be specified alone in those cases where the value is unambiguous".
        This is crazy, but we have to deal with it.
    @ivar encoded:
        A boolean describing whether the data in the content line is encoded.
        Generally, text read from a serialized vCard or vCalendar should be
        considered encoded.  Data added programmatically should not be encoded.
    @ivar lineNumber:
        An optional line number associated with the contentline.
    """
    def __init__(self, name, params, value, group=None, 
                 encoded=False, isNative=False,
                 lineNumber = None, *args, **kwds):
        """Take output from parseLine, convert params list to dictionary."""
        # group is used as a positional argument to match parseLine's return
        super(ContentLine, self).__init__(group, *args, **kwds)
        self.name        = name.upper()
        self.value       = value
        self.encoded     = encoded
        self.params      = {}
        self.singletonparams = []
        self.isNative = isNative
        self.lineNumber = lineNumber
        def updateTable(x):
            if len(x) == 1:
                self.singletonparams += x
            else:
                paramlist = self.params.setdefault(x[0].upper(), [])
                paramlist.extend(x[1:])
        map(updateTable, params)
        qp = False
        if 'ENCODING' in self.params:
            if 'QUOTED-PRINTABLE' in self.params['ENCODING']:
                qp = True
                self.params['ENCODING'].remove('QUOTED-PRINTABLE')
                if 0==len(self.params['ENCODING']):
                    del self.params['ENCODING']
        if 'QUOTED-PRINTABLE' in self.singletonparams:
            qp = True
            self.singletonparams.remove('QUOTED-PRINTABLE')
        if qp:
            self.value = str(self.value).decode('quoted-printable')

        # self.value should be unicode for iCalendar, but if quoted-printable
        # is used, or if the quoted-printable state machine is used, text may be
        # encoded
        if type(self.value) is str:
            charset = 'iso-8859-1'
            if 'CHARSET' in self.params:
                charsets = self.params.pop('CHARSET')
                if charsets:
                    charset = charsets[0]
            self.value = unicode(self.value, charset)

    @classmethod
    def duplicate(clz, copyit):
        newcopy = clz('', {}, '')
        newcopy.copy(copyit)
        return newcopy

    def copy(self, copyit):
        super(ContentLine, self).copy(copyit)
        self.name = copyit.name
        self.value = copy.copy(copyit.value)
        self.encoded = self.encoded
        self.params = copy.copy(copyit.params)
        self.singletonparams = copy.copy(copyit.singletonparams)
        self.lineNumber = copyit.lineNumber
        
    def __eq__(self, other):
        try:
            return (self.name == other.name) and (self.params == other.params) and (self.value == other.value)
        except:
            return False

    def _getAttributeNames(self):
        """Return a list of attributes of the object.

           Python 2.6 will add __dir__ to customize what attributes are returned
           by dir, for now copy PyCrust so that IPython can accurately do
           completion.

        """
        keys = self.params.keys()
        params = [param + '_param' for param in keys]
        params.extend(param + '_paramlist' for param in keys)
        return params

    def __getattr__(self, name):
        """Make params accessible via self.foo_param or self.foo_paramlist.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.

        """
        try:
            if name.endswith('_param'):
                return self.params[toVName(name, 6, True)][0]
            elif name.endswith('_paramlist'):
                return self.params[toVName(name, 10, True)]
            else:
                raise exceptions.AttributeError, name
        except KeyError:
            raise exceptions.AttributeError, name

    def __setattr__(self, name, value):
        """Make params accessible via self.foo_param or self.foo_paramlist.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        
        """
        if name.endswith('_param'):
            if type(value) == list:
                self.params[toVName(name, 6, True)] = value
            else:
                self.params[toVName(name, 6, True)] = [value]
        elif name.endswith('_paramlist'):
            if type(value) == list:
                self.params[toVName(name, 10, True)] = value
            else:
                raise VObjectError("Parameter list set to a non-list")
        else:
            prop = getattr(self.__class__, name, None)
            if isinstance(prop, property):
                prop.fset(self, value)
            else:
                object.__setattr__(self, name, value)

    def __delattr__(self, name):
        try:
            if name.endswith('_param'):
                del self.params[toVName(name, 6, True)]
            elif name.endswith('_paramlist'):
                del self.params[toVName(name, 10, True)]
            else:
                object.__delattr__(self, name)
        except KeyError:
            raise exceptions.AttributeError, name

    def valueRepr( self ):
        """transform the representation of the value according to the behavior,
        if any"""
        v = self.value
        if self.behavior:
            v = self.behavior.valueRepr( self )
        return ascii( v )
        
    def __str__(self):
        return "<"+ascii(self.name)+ascii(self.params)+self.valueRepr()+">"

    def __repr__(self):
        return self.__str__().replace('\n', '\\n')

    def prettyPrint(self, level = 0, tabwidth=3):
        pre = ' ' * level * tabwidth
        print pre, self.name + ":", self.valueRepr()
        if self.params:
            lineKeys= self.params.keys()
            print pre, "params for ", self.name +':'
            for aKey in lineKeys:
                print pre + ' ' * tabwidth, aKey, ascii(self.params[aKey])

class Component(VBase):
    """A complex property that can contain multiple ContentLines.
    
    For our purposes, a component must start with a BEGIN:xxxx line and end with
    END:xxxx, or have a PROFILE:xxx line if a top-level component.

    @ivar contents:
        A dictionary of lists of Component or ContentLine instances. The keys
        are the lowercased names of child ContentLines or Components.
        Note that BEGIN and END ContentLines are not included in contents.
    @ivar name:
        Uppercase string used to represent this Component, i.e VCARD if the
        serialized object starts with BEGIN:VCARD.
    @ivar useBegin:
        A boolean flag determining whether BEGIN: and END: lines should
        be serialized.

    """
    def __init__(self, name=None, *args, **kwds):
        super(Component, self).__init__(*args, **kwds)
        self.contents  = {}
        if name:
            self.name=name.upper()
            self.useBegin = True
        else:
            self.name = ''
            self.useBegin = False
        
        self.autoBehavior()

    @classmethod
    def duplicate(clz, copyit):
        newcopy = clz()
        newcopy.copy(copyit)
        return newcopy

    def copy(self, copyit):
        super(Component, self).copy(copyit)
        
        # deep copy of contents
        self.contents = {}
        for key, lvalue in copyit.contents.items():
            newvalue = []
            for value in lvalue:
                newitem = value.duplicate(value)
                newvalue.append(newitem)
            self.contents[key] = newvalue

        self.name = copyit.name
        self.useBegin = copyit.useBegin
         
    def setProfile(self, name):
        """Assign a PROFILE to this unnamed component.
        
        Used by vCard, not by vCalendar.
        
        """
        if self.name or self.useBegin:
            if self.name == name: return
            raise VObjectError("This component already has a PROFILE or uses BEGIN.")
        self.name = name.upper()

    def _getAttributeNames(self):
        """Return a list of attributes of the object.

           Python 2.6 will add __dir__ to customize what attributes are returned
           by dir, for now copy PyCrust so that IPython can accurately do
           completion.

        """
        names = self.contents.keys()
        names.extend(name + '_list' for name in self.contents.keys())
        return names

    def __getattr__(self, name):
        """For convenience, make self.contents directly accessible.
        
        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        
        """
        # if the object is being re-created by pickle, self.contents may not
        # be set, don't get into an infinite loop over the issue
        if name == 'contents':
            return object.__getattribute__(self, name) 
        try:
            if name.endswith('_list'):
                return self.contents[toVName(name, 5)]
            else:
                return self.contents[toVName(name)][0]
        except KeyError:
            raise exceptions.AttributeError, name

    normal_attributes = ['contents','name','behavior','parentBehavior','group']
    def __setattr__(self, name, value):
        """For convenience, make self.contents directly accessible.

        Underscores, legal in python variable names, are converted to dashes,
        which are legal in IANA tokens.
        
        """
        if name not in self.normal_attributes and name.lower()==name:
            if type(value) == list:
                if name.endswith('_list'):
                    name = name[:-5]
                self.contents[toVName(name)] = value
            elif name.endswith('_list'):
                raise VObjectError("Component list set to a non-list")
            else:
                self.contents[toVName(name)] = [value]
        else:
            prop = getattr(self.__class__, name, None)
            if isinstance(prop, property):
                prop.fset(self, value)
            else:
                object.__setattr__(self, name, value)

    def __delattr__(self, name):
        try:
            if name not in self.normal_attributes and name.lower()==name:
                if name.endswith('_list'):
                    del self.contents[toVName(name, 5)]
                else:
                    del self.contents[toVName(name)]
            else:
                object.__delattr__(self, name)
        except KeyError:
            raise exceptions.AttributeError, name

    def getChildValue(self, childName, default = None, childNumber = 0):
        """Return a child's value (the first, by default), or None."""
        child = self.contents.get(toVName(childName))
        if child is None:
            return default
        else:
            return child[childNumber].value

    def add(self, objOrName, group = None):
        """Add objOrName to contents, set behavior if it can be inferred.
        
        If objOrName is a string, create an empty component or line based on
        behavior. If no behavior is found for the object, add a ContentLine.

        group is an optional prefix to the name of the object (see
        RFC 2425).
        """
        if isinstance(objOrName, VBase):
            obj = objOrName
            if self.behavior:
                obj.parentBehavior = self.behavior
                obj.autoBehavior(True)
        else:
            name = objOrName.upper()
            try:
                id=self.behavior.knownChildren[name][2]
                behavior = getBehavior(name, id)
                if behavior.isComponent:
                    obj = Component(name)
                else:
                    obj = ContentLine(name, [], '', group)
                obj.parentBehavior = self.behavior
                obj.behavior = behavior
                obj = obj.transformToNative()     
            except (KeyError, AttributeError):
                obj = ContentLine(objOrName, [], '', group)
            if obj.behavior is None and self.behavior is not None:
                if isinstance(obj, ContentLine):
                    obj.behavior = self.behavior.defaultBehavior
        self.contents.setdefault(obj.name.lower(), []).append(obj)
        return obj

    def remove(self, obj):
        """Remove obj from contents."""
        named = self.contents.get(obj.name.lower())
        if named:
            try:
                named.remove(obj)
                if len(named) == 0:
                    del self.contents[obj.name.lower()]
            except ValueError:
                pass;

    def getChildren(self):
        """Return an iterable of all children."""
        for objList in self.contents.values():
            for obj in objList: yield obj

    def components(self):
        """Return an iterable of all Component children."""
        return (i for i in self.getChildren() if isinstance(i, Component))

    def lines(self):
        """Return an iterable of all ContentLine children."""
        return (i for i in self.getChildren() if isinstance(i, ContentLine))

    def sortChildKeys(self):
        try:
            first = [s for s in self.behavior.sortFirst if s in self.contents]
        except:
            first = []
        return first + sorted(k for k in self.contents.keys() if k not in first)

    def getSortedChildren(self):
        return [obj for k in self.sortChildKeys() for obj in self.contents[k]]

    def setBehaviorFromVersionLine(self, versionLine):
        """Set behavior if one matches name, versionLine.value."""
        v=getBehavior(self.name, versionLine.value)
        if v: self.setBehavior(v)

    def transformChildrenToNative(self):
        """Recursively replace children with their native representation."""
        #sort to get dependency order right, like vtimezone before vevent
        for childArray in (self.contents[k] for k in self.sortChildKeys()):
            for i in xrange(len(childArray)):
                childArray[i]=childArray[i].transformToNative()
                childArray[i].transformChildrenToNative()

    def transformChildrenFromNative(self, clearBehavior=True):
        """Recursively transform native children to vanilla representations."""
        for childArray in self.contents.values():
            for i in xrange(len(childArray)):
                childArray[i]=childArray[i].transformFromNative()
                childArray[i].transformChildrenFromNative(clearBehavior)
                if clearBehavior:
                    childArray[i].behavior = None
                    childArray[i].parentBehavior = None
    
    def __str__(self):
        if self.name:
            return "<" + self.name + "| " + str(self.getSortedChildren()) + ">"
        else:
            return '<' + '*unnamed*' + '| ' + str(self.getSortedChildren()) + '>'

    def __repr__(self):
        return self.__str__()

    def prettyPrint(self, level = 0, tabwidth=3):
        pre = ' ' * level * tabwidth
        print pre, self.name
        if isinstance(self, Component):
            for line in self.getChildren():
                line.prettyPrint(level + 1, tabwidth)
        print

class VObjectError(Exception):
    def __init__(self, message, lineNumber=None):
        self.message = message
        if lineNumber is not None:
            self.lineNumber = lineNumber
    def __str__(self):
        if hasattr(self, 'lineNumber'):
            return "At line %s: %s" % \
                   (self.lineNumber, self.message)
        else:
            return repr(self.message)

class ParseError(VObjectError):
    pass

class ValidateError(VObjectError):
    pass

class NativeError(VObjectError):
    pass

#-------------------------- Parsing functions ----------------------------------

# parseLine regular expressions

patterns = {}

# Note that underscore is not legal for names, it's included because
# Lotus Notes uses it
patterns['name'] = '[a-zA-Z0-9\-_]+'                                  
patterns['safe_char'] = '[^";:,]'
patterns['qsafe_char'] = '[^"]'

# the combined Python string replacement and regex syntax is a little confusing;
# remember that %(foobar)s is replaced with patterns['foobar'], so for instance
# param_value is any number of safe_chars or any number of qsaf_chars surrounded
# by double quotes.

patterns['param_value'] = ' "%(qsafe_char)s * " | %(safe_char)s * ' % patterns


# get a tuple of two elements, one will be empty, the other will have the value
patterns['param_value_grouped'] = """
" ( %(qsafe_char)s * )" | ( %(safe_char)s + )
""" % patterns

# get a parameter and its values, without any saved groups
patterns['param'] = r"""
; (?: %(name)s )                     # parameter name
(?:
    (?: = (?: %(param_value)s ) )?   # 0 or more parameter values, multiple 
    (?: , (?: %(param_value)s ) )*   # parameters are comma separated
)*                         
""" % patterns

# get a parameter, saving groups for name and value (value still needs parsing)
patterns['params_grouped'] = r"""
; ( %(name)s )

(?: =
    (
        (?:   (?: %(param_value)s ) )?   # 0 or more parameter values, multiple 
        (?: , (?: %(param_value)s ) )*   # parameters are comma separated
    )
)?
""" % patterns

# get a full content line, break it up into group, name, parameters, and value
patterns['line'] = r"""
^ ((?P<group> %(name)s)\.)?(?P<name> %(name)s) # name group
  (?P<params> (?: %(param)s )* )               # params group (may be empty)
: (?P<value> .* )$                             # value group
""" % patterns

' "%(qsafe_char)s*" | %(safe_char)s* '

param_values_re = re.compile(patterns['param_value_grouped'], re.VERBOSE)
params_re       = re.compile(patterns['params_grouped'],      re.VERBOSE)
line_re         = re.compile(patterns['line'],    re.DOTALL | re.VERBOSE)
begin_re        = re.compile('BEGIN', re.IGNORECASE)


def parseParams(string):
    """
    >>> parseParams(';ALTREP="http://www.wiz.org"')
    [['ALTREP', 'http://www.wiz.org']]
    >>> parseParams('')
    []
    >>> parseParams(';ALTREP="http://www.wiz.org;;",Blah,Foo;NEXT=Nope;BAR')
    [['ALTREP', 'http://www.wiz.org;;', 'Blah', 'Foo'], ['NEXT', 'Nope'], ['BAR']]
    """
    all = params_re.findall(string)
    allParameters = []
    for tup in all:
        paramList = [tup[0]] # tup looks like (name, valuesString)
        for pair in param_values_re.findall(tup[1]):
            # pair looks like ('', value) or (value, '')
            if pair[0] != '':
                paramList.append(pair[0])
            else:
                paramList.append(pair[1])
        allParameters.append(paramList)
    return allParameters


def parseLine(line, lineNumber = None):
    """
    >>> parseLine("BLAH:")
    ('BLAH', [], '', None)
    >>> parseLine("RDATE:VALUE=DATE:19970304,19970504,19970704,19970904")
    ('RDATE', [], 'VALUE=DATE:19970304,19970504,19970704,19970904', None)
    >>> parseLine('DESCRIPTION;ALTREP="http://www.wiz.org":The Fall 98 Wild Wizards Conference - - Las Vegas, NV, USA')
    ('DESCRIPTION', [['ALTREP', 'http://www.wiz.org']], 'The Fall 98 Wild Wizards Conference - - Las Vegas, NV, USA', None)
    >>> parseLine("EMAIL;PREF;INTERNET:john@nowhere.com")
    ('EMAIL', [['PREF'], ['INTERNET']], 'john@nowhere.com', None)
    >>> parseLine('EMAIL;TYPE="blah",hah;INTERNET="DIGI",DERIDOO:john@nowhere.com')
    ('EMAIL', [['TYPE', 'blah', 'hah'], ['INTERNET', 'DIGI', 'DERIDOO']], 'john@nowhere.com', None)
    >>> parseLine('item1.ADR;type=HOME;type=pref:;;Reeperbahn 116;Hamburg;;20359;')
    ('ADR', [['type', 'HOME'], ['type', 'pref']], ';;Reeperbahn 116;Hamburg;;20359;', 'item1')
    >>> parseLine(":")
    Traceback (most recent call last):
    ...
    ParseError: 'Failed to parse line: :'
    """
    
    match = line_re.match(line)
    if match is None:
        raise ParseError("Failed to parse line: %s" % line, lineNumber)
    # Underscores are replaced with dash to work around Lotus Notes
    return (match.group('name').replace('_','-'),                                 
            parseParams(match.group('params')),
            match.group('value'), match.group('group'))

# logical line regular expressions

patterns['lineend'] = r'(?:\r\n|\r|\n|$)'
patterns['wrap'] = r'%(lineend)s [\t ]' % patterns
patterns['logicallines'] = r"""
(
   (?: [^\r\n] | %(wrap)s )*
   %(lineend)s
)
""" % patterns

patterns['wraporend'] = r'(%(wrap)s | %(lineend)s )' % patterns

wrap_re          = re.compile(patterns['wraporend'],    re.VERBOSE)
logical_lines_re = re.compile(patterns['logicallines'], re.VERBOSE)

testLines="""
Line 0 text
 , Line 0 continued.
Line 1;encoding=quoted-printable:this is an evil=
 evil=
 format.
Line 2 is a new line, it does not start with whitespace.
"""

def getLogicalLines(fp, allowQP=True, findBegin=False):
    """Iterate through a stream, yielding one logical line at a time.

    Because many applications still use vCard 2.1, we have to deal with the
    quoted-printable encoding for long lines, as well as the vCard 3.0 and
    vCalendar line folding technique, a whitespace character at the start
    of the line.
       
    Quoted-printable data will be decoded in the Behavior decoding phase.
       
    >>> import StringIO
    >>> f=StringIO.StringIO(testLines)
    >>> for n, l in enumerate(getLogicalLines(f)):
    ...     print "Line %s: %s" % (n, l[0])
    ...
    Line 0: Line 0 text, Line 0 continued.
    Line 1: Line 1;encoding=quoted-printable:this is an evil=
     evil=
     format.
    Line 2: Line 2 is a new line, it does not start with whitespace.

    """
    if not allowQP:
        bytes = fp.read(-1)
        if len(bytes) > 0:
            if type(bytes[0]) == unicode:
                val = bytes
            elif not findBegin:
                val = bytes.decode('utf-8')
            else:
                for encoding in 'utf-8', 'utf-16-LE', 'utf-16-BE', 'iso-8859-1':
                    try:
                        val = bytes.decode(encoding)
                        if begin_re.search(val) is not None:
                            break
                    except UnicodeDecodeError:
                        pass
                else:
                    raise ParseError, 'Could not find BEGIN when trying to determine encoding'
        else:
            val = bytes
        
        # strip off any UTF8 BOMs which Python's UTF8 decoder leaves

        val = val.lstrip( unicode( codecs.BOM_UTF8, "utf8" ) )

        lineNumber = 1
        for match in logical_lines_re.finditer(val):
            line, n = wrap_re.subn('', match.group())
            if line != '':
                yield line, lineNumber
            lineNumber += n
        
    else:
        quotedPrintable=False
        newbuffer = StringIO.StringIO
        logicalLine = newbuffer()
        lineNumber = 0
        lineStartNumber = 0
        while True:
            line = fp.readline()
            if line == '':
                break
            else:
                line = line.rstrip(CRLF)
                lineNumber += 1
            if line.rstrip() == '':
                if logicalLine.pos > 0:
                    yield logicalLine.getvalue(), lineStartNumber
                lineStartNumber = lineNumber
                logicalLine = newbuffer()
                quotedPrintable=False
                continue
    
            if quotedPrintable and allowQP:
                logicalLine.write('\n')
                logicalLine.write(line)
                quotedPrintable=False
            elif line[0] in SPACEORTAB:
                logicalLine.write(line[1:])
            elif logicalLine.pos > 0:
                yield logicalLine.getvalue(), lineStartNumber
                lineStartNumber = lineNumber
                logicalLine = newbuffer()
                logicalLine.write(line)
            else:
                logicalLine = newbuffer()
                logicalLine.write(line)
            
            # hack to deal with the fact that vCard 2.1 allows parameters to be
            # encoded without a parameter name.  False positives are unlikely, but
            # possible.
            val = logicalLine.getvalue()
            if val[-1]=='=' and val.lower().find('quoted-printable') >= 0:
                quotedPrintable=True
    
        if logicalLine.pos > 0:
            yield logicalLine.getvalue(), lineStartNumber


def textLineToContentLine(text, n=None):
    return ContentLine(*parseLine(text, n), **{'encoded':True, 'lineNumber' : n})
            

def dquoteEscape(param):
    """Return param, or "param" if ',' or ';' or ':' is in param."""
    if param.find('"') >= 0:
        raise VObjectError("Double quotes aren't allowed in parameter values.")
    for char in ',;:':
        if param.find(char) >= 0:
            return '"'+ param + '"'
    return param

def foldOneLine(outbuf, input, lineLength = 75):
    # Folding line procedure that ensures multi-byte utf-8 sequences are not broken
    # across lines

    if len(input) < lineLength:
        # Optimize for unfolded line case
        outbuf.write(input)
    else:
        # Look for valid utf8 range and write that out
        start = 0
        written = 0
        while written < len(input):
            # Start max length -1 chars on from where we are
            offset = start + lineLength - 1
            if offset >= len(input):
                line = input[start:]
                outbuf.write(line)
                written = len(input)
            else:
                # Check whether next char is valid utf8 lead byte
                while (input[offset] > 0x7F) and ((ord(input[offset]) & 0xC0) == 0x80):
                    # Step back until we have a valid char
                    offset -= 1
                
                line = input[start:offset]
                outbuf.write(line)
                outbuf.write("\r\n ")
                written += offset - start
                start = offset
    outbuf.write("\r\n")

def defaultSerialize(obj, buf, lineLength):
    """Encode and fold obj and its children, write to buf or return a string."""

    outbuf = buf or cStringIO.StringIO()

    if isinstance(obj, Component):
        if obj.group is None:
            groupString = ''
        else:
            groupString = obj.group + '.'
        if obj.useBegin:
            foldOneLine(outbuf, str(groupString + u"BEGIN:" + obj.name), lineLength)
        for child in obj.getSortedChildren():
            #validate is recursive, we only need to validate once
            child.serialize(outbuf, lineLength, validate=False)
        if obj.useBegin:
            foldOneLine(outbuf, str(groupString + u"END:" + obj.name), lineLength)
        
    elif isinstance(obj, ContentLine):
        startedEncoded = obj.encoded
        if obj.behavior and not startedEncoded: obj.behavior.encode(obj)
        s=codecs.getwriter('utf-8')(cStringIO.StringIO()) #unfolded buffer
        if obj.group is not None:
            s.write(obj.group + '.')
        s.write(obj.name.upper())
        for key, paramvals in obj.params.iteritems():
            s.write(';' + key + '=' + ','.join(dquoteEscape(p) for p in paramvals))
        s.write(':' + obj.value)
        if obj.behavior and not startedEncoded: obj.behavior.decode(obj)
        foldOneLine(outbuf, s.getvalue(), lineLength)
    
    return buf or outbuf.getvalue()


testVCalendar="""
BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY;blah=hi!:Bastille Day Party
END:VEVENT
END:VCALENDAR"""

class Stack:
    def __init__(self):
        self.stack = []
    def __len__(self):
        return len(self.stack)
    def top(self):
        if len(self) == 0: return None
        else: return self.stack[-1]
    def topName(self):
        if len(self) == 0: return None
        else: return self.stack[-1].name
    def modifyTop(self, item):
        top = self.top()
        if top:
            top.add(item)
        else:
            new = Component()
            self.push(new)
            new.add(item) #add sets behavior for item and children
    def push(self, obj): self.stack.append(obj)
    def pop(self): return self.stack.pop()


def readComponents(streamOrString, validate=False, transform=True,
                   findBegin=True, ignoreUnreadable=False,
                   allowQP=False):
    """Generate one Component at a time from a stream.

    >>> import StringIO
    >>> f = StringIO.StringIO(testVCalendar)
    >>> cal=readComponents(f).next()
    >>> cal
    <VCALENDAR| [<VEVENT| [<SUMMARY{u'BLAH': [u'hi!']}Bastille Day Party>]>]>
    >>> cal.vevent.summary
    <SUMMARY{u'BLAH': [u'hi!']}Bastille Day Party>
    
    """
    if isinstance(streamOrString, basestring):
        stream = StringIO.StringIO(streamOrString)
    else:
        stream = streamOrString

    try:
        stack = Stack()
        versionLine = None
        n = 0
        for line, n in getLogicalLines(stream, allowQP, findBegin):
            if ignoreUnreadable:
                try:
                    vline = textLineToContentLine(line, n)
                except VObjectError, e:
                    if e.lineNumber is not None:
                        msg = "Skipped line %(lineNumber)s, message: %(msg)s"
                    else:
                        msg = "Skipped a line, message: %(msg)s"
                    logger.error(msg % {'lineNumber' : e.lineNumber, 
                                        'msg' : e.message})
                    continue
            else:
                vline = textLineToContentLine(line, n)
            if   vline.name == "VERSION":
                versionLine = vline
                stack.modifyTop(vline)
            elif vline.name == "BEGIN":
                stack.push(Component(vline.value, group=vline.group))
            elif vline.name == "PROFILE":
                if not stack.top(): stack.push(Component())
                stack.top().setProfile(vline.value)
            elif vline.name == "END":
                if len(stack) == 0:
                    err = "Attempted to end the %s component, \
                           but it was never opened" % vline.value
                    raise ParseError(err, n)
                if vline.value.upper() == stack.topName(): #START matches END
                    if len(stack) == 1:
                        component=stack.pop()
                        if versionLine is not None:
                            component.setBehaviorFromVersionLine(versionLine)
                        else:
                            behavior = getBehavior(component.name)
                            if behavior:
                                component.setBehavior(behavior)
                        if validate: component.validate(raiseException=True)
                        if transform: component.transformChildrenToNative()
                        yield component #EXIT POINT
                    else: stack.modifyTop(stack.pop())
                else:
                    err = "%s component wasn't closed" 
                    raise ParseError(err % stack.topName(), n)
            else: stack.modifyTop(vline) #not a START or END line
        if stack.top():
            if stack.topName() is None:
                logger.warning("Top level component was never named")
            elif stack.top().useBegin:
                raise ParseError("Component %s was never closed" % (stack.topName()), n)
            yield stack.pop()

    except ParseError, e:
        e.input = streamOrString
        raise


def readOne(stream, validate=False, transform=True, findBegin=True,
            ignoreUnreadable=False, allowQP=False):
    """Return the first component from stream."""
    return readComponents(stream, validate, transform, findBegin,
                          ignoreUnreadable, allowQP).next()

#--------------------------- version registry ----------------------------------
__behaviorRegistry={}

def registerBehavior(behavior, name=None, default=False, id=None):
    """Register the given behavior.
    
    If default is True (or if this is the first version registered with this 
    name), the version will be the default if no id is given.
    
    """
    if not name: name=behavior.name.upper()
    if id is None: id=behavior.versionString
    if name in __behaviorRegistry:
        if default:
            __behaviorRegistry[name].insert(0, (id, behavior))
        else:
            __behaviorRegistry[name].append((id, behavior))
    else:
        __behaviorRegistry[name]=[(id, behavior)]

def getBehavior(name, id=None):
    """Return a matching behavior if it exists, or None.
    
    If id is None, return the default for name.
    
    """
    name=name.upper()
    if name in __behaviorRegistry:
        if id:
            for n, behavior in __behaviorRegistry[name]:
                if n==id:
                    return behavior

        return __behaviorRegistry[name][0][1]
    return None

def newFromBehavior(name, id=None):
    """Given a name, return a behaviored ContentLine or Component."""
    name = name.upper()
    behavior = getBehavior(name, id)
    if behavior is None:
        raise VObjectError("No behavior found named %s" % name)
    if behavior.isComponent:
        obj = Component(name)
    else:
        obj = ContentLine(name, [], '')
    obj.behavior = behavior
    obj.isNative = False
    return obj


#--------------------------- Helper function -----------------------------------
def backslashEscape(s):
    s=s.replace("\\","\\\\").replace(";","\;").replace(",","\,")
    return s.replace("\r\n", "\\n").replace("\n","\\n").replace("\r","\\n")

#------------------- Testing and running functions -----------------------------
if __name__ == '__main__':
    import tests
    tests._test()

########NEW FILE########
__FILENAME__ = behavior
"""Behavior (validation, encoding, and transformations) for vobjects."""

import base

#------------------------ Abstract class for behavior --------------------------
class Behavior(object):
    """Abstract class to describe vobject options, requirements and encodings.
    
    Behaviors are used for root components like VCALENDAR, for subcomponents
    like VEVENT, and for individual lines in components.
    
    Behavior subclasses are not meant to be instantiated, all methods should
    be classmethods.
    
    @cvar name:
        The uppercase name of the object described by the class, or a generic
        name if the class defines behavior for many objects.
    @cvar description:
        A brief excerpt from the RFC explaining the function of the component or
        line.
    @cvar versionString:
        The string associated with the component, for instance, 2.0 if there's a
        line like VERSION:2.0, an empty string otherwise.
    @cvar knownChildren:
        A dictionary with uppercased component/property names as keys and a
        tuple (min, max, id) as value, where id is the id used by
        L{registerBehavior}, min and max are the limits on how many of this child
        must occur.  None is used to denote no max or no id.
    @cvar quotedPrintable:
        A boolean describing whether the object should be encoded and decoded
        using quoted printable line folding and character escaping.
    @cvar defaultBehavior:
        Behavior to apply to ContentLine children when no behavior is found.
    @cvar hasNative:
        A boolean describing whether the object can be transformed into a more
        Pythonic object.
    @cvar isComponent:
        A boolean, True if the object should be a Component.
    @cvar sortFirst:
        The lower-case list of children which should come first when sorting.
    @cvar allowGroup:
        Whether or not vCard style group prefixes are allowed.
    """
    name=''
    description=''
    versionString=''
    knownChildren = {}
    quotedPrintable = False
    defaultBehavior = None
    hasNative= False
    isComponent = False
    allowGroup = False
    forceUTC = False
    sortFirst = []

    def __init__(self):
        err="Behavior subclasses are not meant to be instantiated"
        raise base.VObjectError(err)
   
    @classmethod
    def validate(cls, obj, raiseException=False, complainUnrecognized=False):
        """Check if the object satisfies this behavior's requirements.
        
        @param obj:
            The L{ContentLine<base.ContentLine>} or
            L{Component<base.Component>} to be validated.
        @param raiseException:
            If True, raise a L{base.ValidateError} on validation failure.
            Otherwise return a boolean.
        @param complainUnrecognized:
            If True, fail to validate if an uncrecognized parameter or child is
            found.  Otherwise log the lack of recognition.

        """
        if not cls.allowGroup and obj.group is not None:
            err = str(obj) + " has a group, but this object doesn't support groups"
            raise base.VObjectError(err)
        if isinstance(obj, base.ContentLine):
            return cls.lineValidate(obj, raiseException, complainUnrecognized)
        elif isinstance(obj, base.Component):
            count = {}
            for child in obj.getChildren():
                if not child.validate(raiseException, complainUnrecognized):
                    return False
                name=child.name.upper()
                count[name] = count.get(name, 0) + 1
            for key, val in cls.knownChildren.iteritems():
                if count.get(key,0) < val[0]: 
                    if raiseException:
                        m = "%s components must contain at least %i %s"
                        raise base.ValidateError(m % (cls.name, val[0], key))
                    return False
                if val[1] and count.get(key,0) > val[1]:
                    if raiseException:
                        m = "%s components cannot contain more than %i %s"
                        raise base.ValidateError(m % (cls.name, val[1], key))
                    return False
            return True
        else:
            err = str(obj) + " is not a Component or Contentline"
            raise base.VObjectError(err)
    
    @classmethod
    def lineValidate(cls, line, raiseException, complainUnrecognized):
        """Examine a line's parameters and values, return True if valid."""
        return True

    @classmethod
    def decode(cls, line):
        if line.encoded: line.encoded=0
    
    @classmethod
    def encode(cls, line):
        if not line.encoded: line.encoded=1

    @classmethod
    def transformToNative(cls, obj):
        """Turn a ContentLine or Component into a Python-native representation.
        
        If appropriate, turn dates or datetime strings into Python objects.
        Components containing VTIMEZONEs turn into VtimezoneComponents.
        
        """
        return obj
    
    @classmethod
    def transformFromNative(cls, obj):
        """Inverse of transformToNative."""
        raise base.NativeError("No transformFromNative defined")
    
    @classmethod
    def generateImplicitParameters(cls, obj):
        """Generate any required information that don't yet exist."""
        pass
    
    @classmethod
    def serialize(cls, obj, buf, lineLength, validate=True):
        """Set implicit parameters, do encoding, return unicode string.
        
        If validate is True, raise VObjectError if the line doesn't validate
        after implicit parameters are generated.
        
        Default is to call base.defaultSerialize.
        
        """
      
        cls.generateImplicitParameters(obj)
        if validate: cls.validate(obj, raiseException=True)
        
        if obj.isNative:
            transformed = obj.transformFromNative()
            undoTransform = True
        else:
            transformed = obj
            undoTransform = False
        
        out = base.defaultSerialize(transformed, buf, lineLength)
        if undoTransform: obj.transformToNative()
        return out
    
    @classmethod
    def valueRepr( cls, line ):
        """return the representation of the given content line value"""
        return line.value
########NEW FILE########
__FILENAME__ = change_tz
"""Translate an ics file's events to a different timezone."""

from optparse import OptionParser
from vobject import icalendar, base
import sys
try:
    import PyICU
except:
    PyICU = None

from datetime import datetime

def change_tz(cal, new_timezone, default, utc_only=False, utc_tz=icalendar.utc):
    for vevent in getattr(cal, 'vevent_list', []):
        start = getattr(vevent, 'dtstart', None)
        end   = getattr(vevent, 'dtend',   None)
        for node in (start, end):
            if node:
                dt = node.value
                if (isinstance(dt, datetime) and
                    (not utc_only or dt.tzinfo == utc_tz)):
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo = default)
                    node.value = dt.astimezone(new_timezone)

def main():
    options, args = get_options()
    if PyICU is None:
        print "Failure. change_tz requires PyICU, exiting"
    elif options.list:
        for tz_string in PyICU.TimeZone.createEnumeration():
            print tz_string
    elif args:
        utc_only = options.utc
        if utc_only:
            which = "only UTC"
        else:
            which = "all"
        print "Converting %s events" % which
        ics_file = args[0]
        if len(args) > 1:
            timezone = PyICU.ICUtzinfo.getInstance(args[1])
        else:
            timezone = PyICU.ICUtzinfo.default
        print "... Reading %s" % ics_file
        cal = base.readOne(file(ics_file))
        change_tz(cal, timezone, PyICU.ICUtzinfo.default, utc_only)

        out_name = ics_file + '.converted'
        print "... Writing %s" % out_name
        out = file(out_name, 'wb')
        cal.serialize(out)
        print "Done"


version = "0.1"

def get_options():
    ##### Configuration options #####

    usage = """usage: %prog [options] ics_file [timezone]"""
    parser = OptionParser(usage=usage, version=version)
    parser.set_description("change_tz will convert the timezones in an ics file. ")

    parser.add_option("-u", "--only-utc", dest="utc", action="store_true",
                      default=False, help="Only change UTC events.")
    parser.add_option("-l", "--list", dest="list", action="store_true",
                      default=False, help="List available timezones")


    (cmdline_options, args) = parser.parse_args()
    if not args and not cmdline_options.list:
        print "error: too few arguments given"
        print
        print parser.format_help()
        return False, False

    return cmdline_options, args

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Aborted"

########NEW FILE########
__FILENAME__ = hcalendar
"""
hCalendar: A microformat for serializing iCalendar data
          (http://microformats.org/wiki/hcalendar)

Here is a sample event in an iCalendar:

BEGIN:VCALENDAR
PRODID:-//XYZproduct//EN
VERSION:2.0
BEGIN:VEVENT
URL:http://www.web2con.com/
DTSTART:20051005
DTEND:20051008
SUMMARY:Web 2.0 Conference
LOCATION:Argent Hotel\, San Francisco\, CA
END:VEVENT
END:VCALENDAR

and an equivalent event in hCalendar format with various elements optimized appropriately.

<span class="vevent">
 <a class="url" href="http://www.web2con.com/">
  <span class="summary">Web 2.0 Conference</span>: 
  <abbr class="dtstart" title="2005-10-05">October 5</abbr>-
  <abbr class="dtend" title="2005-10-08">7</abbr>,
 at the <span class="location">Argent Hotel, San Francisco, CA</span>
 </a>
</span>
"""

from base import foldOneLine, CRLF, registerBehavior
from icalendar import VCalendar2_0
from datetime import date, datetime, timedelta
import StringIO

class HCalendar(VCalendar2_0):
    name = 'HCALENDAR'
    
    @classmethod
    def serialize(cls, obj, buf=None, lineLength=None, validate=True):
        """
        Serialize iCalendar to HTML using the hCalendar microformat (http://microformats.org/wiki/hcalendar)
        """
        
        outbuf = buf or StringIO.StringIO()
        level = 0 # holds current indentation level        
        tabwidth = 3
        
        def indent():
            return ' ' * level * tabwidth
        
        def out(s):
            outbuf.write(indent())
            outbuf.write(s)
        
        # not serializing optional vcalendar wrapper
        
        vevents = obj.vevent_list
        
        for event in vevents:
            out('<span class="vevent">' + CRLF)
            level += 1
            
            # URL
            url = event.getChildValue("url")
            if url:
                out('<a class="url" href="' + url + '">' + CRLF)
                level += 1
            # SUMMARY
            summary = event.getChildValue("summary")
            if summary:
                out('<span class="summary">' + summary + '</span>:' + CRLF)
            
            # DTSTART
            dtstart = event.getChildValue("dtstart")
            if dtstart:
                if type(dtstart) == date:
                    timeformat = "%A, %B %e"
                    machine    = "%Y%m%d"
                elif type(dtstart) == datetime:
                    timeformat = "%A, %B %e, %H:%M"
                    machine    = "%Y%m%dT%H%M%S%z"

                #TODO: Handle non-datetime formats?
                #TODO: Spec says we should handle when dtstart isn't included
                
                out('<abbr class="dtstart", title="%s">%s</abbr>\r\n' % 
                     (dtstart.strftime(machine), dtstart.strftime(timeformat)))
                
                # DTEND
                dtend = event.getChildValue("dtend")
                if not dtend:
                    duration = event.getChildValue("duration")
                    if duration:
                        dtend = duration + dtstart
                   # TODO: If lacking dtend & duration?
               
                if dtend:
                    human = dtend
                    # TODO: Human readable part could be smarter, excluding repeated data
                    if type(dtend) == date:
                        human = dtend - timedelta(days=1)
                        
                    out('- <abbr class="dtend", title="%s">%s</abbr>\r\n' % 
                     (dtend.strftime(machine), human.strftime(timeformat)))    

            # LOCATION    
            location = event.getChildValue("location")
            if location:
                out('at <span class="location">' + location + '</span>' + CRLF)
        
            description = event.getChildValue("description")
            if description:
                out('<div class="description">' + description + '</div>' + CRLF)
            
            if url:
                level -= 1
                out('</a>' + CRLF)
            
            level -= 1                
            out('</span>' + CRLF) # close vevent

        return buf or outbuf.getvalue()
    
registerBehavior(HCalendar)
########NEW FILE########
__FILENAME__ = icalendar
"""Definitions and behavior for iCalendar, also known as vCalendar 2.0"""

import string
import behavior
import dateutil.rrule
import dateutil.tz
import StringIO, cStringIO
import datetime
import socket, random #for generating a UID
import itertools

from base import (VObjectError, NativeError, ValidateError, ParseError,
                    VBase, Component, ContentLine, logger, defaultSerialize,
                    registerBehavior, backslashEscape, foldOneLine,
                    newFromBehavior, CRLF, LF, ascii)

#------------------------------- Constants -------------------------------------
DATENAMES = ("rdate", "exdate")
RULENAMES = ("exrule", "rrule")
DATESANDRULES = ("exrule", "rrule", "rdate", "exdate")
PRODID = u"-//PYVOBJECT//NONSGML Version 1//EN"

WEEKDAYS = "MO", "TU", "WE", "TH", "FR", "SA", "SU"
FREQUENCIES = ('YEARLY', 'MONTHLY', 'WEEKLY', 'DAILY', 'HOURLY', 'MINUTELY',
               'SECONDLY')

zeroDelta = datetime.timedelta(0)
twoHours  = datetime.timedelta(hours=2)

#---------------------------- TZID registry ------------------------------------
__tzidMap={}

def toUnicode(s):
    """Take a string or unicode, turn it into unicode, decoding as utf-8"""
    if isinstance(s, str):
        s = s.decode('utf-8')
    return s

def registerTzid(tzid, tzinfo):
    """Register a tzid -> tzinfo mapping."""
    __tzidMap[toUnicode(tzid)]=tzinfo

def getTzid(tzid):
    """Return the tzid if it exists, or None."""
    return __tzidMap.get(toUnicode(tzid), None)

utc = dateutil.tz.tzutc()
registerTzid("UTC", utc)

#-------------------- Helper subclasses ----------------------------------------

class TimezoneComponent(Component):
    """A VTIMEZONE object.
    
    VTIMEZONEs are parsed by dateutil.tz.tzical, the resulting datetime.tzinfo
    subclass is stored in self.tzinfo, self.tzid stores the TZID associated
    with this timezone.
    
    @ivar name:
        The uppercased name of the object, in this case always 'VTIMEZONE'.
    @ivar tzinfo:
        A datetime.tzinfo subclass representing this timezone.
    @ivar tzid:
        The string used to refer to this timezone.
    
    """    
    def __init__(self, tzinfo=None, *args, **kwds):
        """Accept an existing Component or a tzinfo class."""
        super(TimezoneComponent, self).__init__(*args, **kwds)
        self.isNative=True
        # hack to make sure a behavior is assigned
        if self.behavior is None:
            self.behavior = VTimezone
        if tzinfo is not None:
            self.tzinfo = tzinfo
        if not hasattr(self, 'name') or self.name == '':
            self.name = 'VTIMEZONE'
            self.useBegin = True

    @classmethod
    def registerTzinfo(obj, tzinfo):
        """Register tzinfo if it's not already registered, return its tzid."""
        tzid = obj.pickTzid(tzinfo)
        if tzid and not getTzid(tzid):
            registerTzid(tzid, tzinfo)
        return tzid

    def gettzinfo(self):
        # workaround for dateutil failing to parse some experimental properties
        good_lines = ('rdate', 'rrule', 'dtstart', 'tzname', 'tzoffsetfrom',
                      'tzoffsetto', 'tzid')
        # serialize encodes as utf-8, cStringIO will leave utf-8 alone
        buffer = cStringIO.StringIO()
        # allow empty VTIMEZONEs
        if len(self.contents) == 0:
            return None
        def customSerialize(obj):
            if isinstance(obj, Component):
                foldOneLine(buffer, u"BEGIN:" + obj.name)
                for child in obj.lines():
                    if child.name.lower() in good_lines:
                        child.serialize(buffer, 75, validate=False)
                for comp in obj.components():
                    customSerialize(comp)
                foldOneLine(buffer, u"END:" + obj.name)
        customSerialize(self)
        buffer.seek(0) # tzical wants to read a stream
        return dateutil.tz.tzical(buffer).get()

    def settzinfo(self, tzinfo, start=2000, end=2030):
        """Create appropriate objects in self to represent tzinfo.
        
        Collapse DST transitions to rrules as much as possible.
        
        Assumptions:
        - DST <-> Standard transitions occur on the hour
        - never within a month of one another
        - twice or fewer times a year
        - never in the month of December
        - DST always moves offset exactly one hour later
        - tzinfo classes dst method always treats times that could be in either
          offset as being in the later regime
        
        """  
        def fromLastWeek(dt):
            """How many weeks from the end of the month dt is, starting from 1."""
            weekDelta = datetime.timedelta(weeks=1)
            n = 1
            current = dt + weekDelta
            while current.month == dt.month:
                n += 1
                current += weekDelta
            return n
        
        # lists of dictionaries defining rules which are no longer in effect
        completed = {'daylight' : [], 'standard' : []}
    
        # dictionary defining rules which are currently in effect
        working   = {'daylight' : None, 'standard' : None}
        
        # rule may be based on the nth week of the month or the nth from the last
        for year in xrange(start, end + 1):
            newyear = datetime.datetime(year, 1, 1)
            for transitionTo in 'daylight', 'standard':
                transition = getTransition(transitionTo, year, tzinfo)
                oldrule = working[transitionTo]
    
                if transition == newyear:
                    # transitionTo is in effect for the whole year
                    rule = {'end'        : None,
                            'start'      : newyear,
                            'month'      : 1,
                            'weekday'    : None,
                            'hour'       : None,
                            'plus'       : None,
                            'minus'      : None,
                            'name'       : tzinfo.tzname(newyear),
                            'offset'     : tzinfo.utcoffset(newyear),
                            'offsetfrom' : tzinfo.utcoffset(newyear)}
                    if oldrule is None:
                        # transitionTo was not yet in effect
                        working[transitionTo] = rule
                    else:
                        # transitionTo was already in effect
                        if (oldrule['offset'] != 
                            tzinfo.utcoffset(newyear)):
                            # old rule was different, it shouldn't continue
                            oldrule['end'] = year - 1
                            completed[transitionTo].append(oldrule)
                            working[transitionTo] = rule
                elif transition is None:
                    # transitionTo is not in effect
                    if oldrule is not None:
                        # transitionTo used to be in effect
                        oldrule['end'] = year - 1
                        completed[transitionTo].append(oldrule)
                        working[transitionTo] = None
                else:
                    # an offset transition was found
                    old_offset = tzinfo.utcoffset(transition - twoHours)
                    rule = {'end'     : None, # None, or an integer year
                            'start'   : transition, # the datetime of transition
                            'month'   : transition.month,
                            'weekday' : transition.weekday(),
                            'hour'    : transition.hour,
                            'name'    : tzinfo.tzname(transition),
                            'plus'    : (transition.day - 1)/ 7 + 1,#nth week of the month
                            'minus'   : fromLastWeek(transition), #nth from last week
                            'offset'  : tzinfo.utcoffset(transition), 
                            'offsetfrom' : old_offset}
        
                    if oldrule is None: 
                        working[transitionTo] = rule
                    else:
                        plusMatch  = rule['plus']  == oldrule['plus'] 
                        minusMatch = rule['minus'] == oldrule['minus'] 
                        truth = plusMatch or minusMatch
                        for key in 'month', 'weekday', 'hour', 'offset':
                            truth = truth and rule[key] == oldrule[key]
                        if truth:
                            # the old rule is still true, limit to plus or minus
                            if not plusMatch:
                                oldrule['plus'] = None
                            if not minusMatch:
                                oldrule['minus'] = None
                        else:
                            # the new rule did not match the old
                            oldrule['end'] = year - 1
                            completed[transitionTo].append(oldrule)
                            working[transitionTo] = rule
    
        for transitionTo in 'daylight', 'standard':
            if working[transitionTo] is not None:
                completed[transitionTo].append(working[transitionTo])
    
        self.tzid = []
        self.daylight = []
        self.standard = []
        
        self.add('tzid').value = self.pickTzid(tzinfo, True)
        
        old = None
        for transitionTo in 'daylight', 'standard':
            for rule in completed[transitionTo]:
                comp = self.add(transitionTo)
                dtstart = comp.add('dtstart')
                dtstart.value = rule['start']
                if rule['name'] is not None:
                    comp.add('tzname').value  = rule['name']
                line = comp.add('tzoffsetto')
                line.value = deltaToOffset(rule['offset'])
                line = comp.add('tzoffsetfrom')
                line.value = deltaToOffset(rule['offsetfrom'])
    
                if rule['plus'] is not None:
                    num = rule['plus']
                elif rule['minus'] is not None:
                    num = -1 * rule['minus']
                else:
                    num = None
                if num is not None:
                    dayString = ";BYDAY=" + str(num) + WEEKDAYS[rule['weekday']]
                else:
                    dayString = ""
                if rule['end'] is not None:
                    if rule['hour'] is None:
                        # all year offset, with no rule
                        endDate = datetime.datetime(rule['end'], 1, 1)
                    else:
                        weekday = dateutil.rrule.weekday(rule['weekday'], num)
                        du_rule = dateutil.rrule.rrule(dateutil.rrule.YEARLY,
                                   bymonth = rule['month'],byweekday = weekday,
                                   dtstart = datetime.datetime(
                                       rule['end'], 1, 1, rule['hour'])
                                  )
                        endDate = du_rule[0]
                    endDate = endDate.replace(tzinfo = utc) - rule['offsetfrom']
                    endString = ";UNTIL="+ dateTimeToString(endDate)
                else:
                    endString = ''
                rulestring = "FREQ=YEARLY%s;BYMONTH=%s%s" % \
                              (dayString, str(rule['month']), endString)
                
                comp.add('rrule').value = rulestring

    tzinfo = property(gettzinfo, settzinfo)
    # prevent Component's __setattr__ from overriding the tzinfo property
    normal_attributes = Component.normal_attributes + ['tzinfo']

    @staticmethod
    def pickTzid(tzinfo, allowUTC=False):
        """
        Given a tzinfo class, use known APIs to determine TZID, or use tzname.
        """
        if tzinfo is None or (not allowUTC and tzinfo_eq(tzinfo, utc)):
            #If tzinfo is UTC, we don't need a TZID
            return None
        # try PyICU's tzid key
        if hasattr(tzinfo, 'tzid'):
            return toUnicode(tzinfo.tzid)
            
        # try pytz zone key
        if hasattr(tzinfo, 'zone'):
            return toUnicode(tzinfo.zone)

        # try tzical's tzid key
        elif hasattr(tzinfo, '_tzid'):
            return toUnicode(tzinfo._tzid)
        else:
            # return tzname for standard (non-DST) time
            notDST = datetime.timedelta(0)
            for month in xrange(1,13):
                dt = datetime.datetime(2000, month, 1)
                if tzinfo.dst(dt) == notDST:
                    return toUnicode(tzinfo.tzname(dt))
        # there was no standard time in 2000!
        raise VObjectError("Unable to guess TZID for tzinfo %s" % str(tzinfo))

    def __str__(self):
        return "<VTIMEZONE | " + str(getattr(self, 'tzid', 'No TZID')) +">"
    
    def __repr__(self):
        return self.__str__()
    
    def prettyPrint(self, level, tabwidth):
        pre = ' ' * level * tabwidth
        print pre, self.name
        print pre, "TZID:", self.tzid
        print

class RecurringComponent(Component):
    """A vCalendar component like VEVENT or VTODO which may recur.
        
    Any recurring component can have one or multiple RRULE, RDATE,
    EXRULE, or EXDATE lines, and one or zero DTSTART lines.  It can also have a
    variety of children that don't have any recurrence information.  
    
    In the example below, note that dtstart is included in the rruleset.
    This is not the default behavior for dateutil's rrule implementation unless
    dtstart would already have been a member of the recurrence rule, and as a
    result, COUNT is wrong. This can be worked around when getting rruleset by
    adjusting count down by one if an rrule has a count and dtstart isn't in its
    result set, but by default, the rruleset property doesn't do this work
    around, to access it getrruleset must be called with addRDate set True.
    
    >>> import dateutil.rrule, datetime
    >>> vevent = RecurringComponent(name='VEVENT')
    >>> vevent.add('rrule').value =u"FREQ=WEEKLY;COUNT=2;INTERVAL=2;BYDAY=TU,TH"
    >>> vevent.add('dtstart').value = datetime.datetime(2005, 1, 19, 9)
    
    When creating rrule's programmatically it should be kept in
    mind that count doesn't necessarily mean what rfc2445 says.
    
    >>> list(vevent.rruleset)
    [datetime.datetime(2005, 1, 20, 9, 0), datetime.datetime(2005, 2, 1, 9, 0)]
    >>> list(vevent.getrruleset(addRDate=True))
    [datetime.datetime(2005, 1, 19, 9, 0), datetime.datetime(2005, 1, 20, 9, 0)]
    
    Also note that dateutil will expand all-day events (datetime.date values) to
    datetime.datetime value with time 0 and no timezone.
    
    >>> vevent.dtstart.value = datetime.date(2005,3,18)
    >>> list(vevent.rruleset)
    [datetime.datetime(2005, 3, 29, 0, 0), datetime.datetime(2005, 3, 31, 0, 0)]
    >>> list(vevent.getrruleset(True))
    [datetime.datetime(2005, 3, 18, 0, 0), datetime.datetime(2005, 3, 29, 0, 0)]
    
    @ivar rruleset:
        A U{rruleset<https://moin.conectiva.com.br/DateUtil>}.
    """
    def __init__(self, *args, **kwds):
        super(RecurringComponent, self).__init__(*args, **kwds)
        self.isNative=True
        #self.clobberedRDates=[]


    def getrruleset(self, addRDate = False):
        """Get an rruleset created from self.
        
        If addRDate is True, add an RDATE for dtstart if it's not included in
        an RRULE, and count is decremented if it exists.
        
        Note that for rules which don't match DTSTART, DTSTART may not appear
        in list(rruleset), although it should.  By default, an RDATE is not
        created in these cases, and count isn't updated, so dateutil may list
        a spurious occurrence.
        
        """
        rruleset = None
        for name in DATESANDRULES:
            addfunc = None
            for line in self.contents.get(name, ()):
                # don't bother creating a rruleset unless there's a rule
                if rruleset is None:
                    rruleset = dateutil.rrule.rruleset()
                if addfunc is None:
                    addfunc=getattr(rruleset, name)

                if name in DATENAMES:
                    if type(line.value[0]) == datetime.datetime:
                        map(addfunc, line.value)
                    elif type(line.value[0]) == datetime.date:
                        for dt in line.value:
                            addfunc(datetime.datetime(dt.year, dt.month, dt.day))
                    else:
                        # ignore RDATEs with PERIOD values for now
                        pass
                elif name in RULENAMES:
                    try:
                        dtstart = self.dtstart.value
                    except AttributeError, KeyError:
                        # Special for VTODO - try DUE property instead
                        try:
                            if self.name == "VTODO":
                                dtstart = self.due.value
                            else:
                                # if there's no dtstart, just return None
                                return None
                        except AttributeError, KeyError:
                            # if there's no due, just return None
                            return None

                    # rrulestr complains about unicode, so cast to str
                    # a Ruby iCalendar library escapes semi-colons in rrules,
                    # so also remove any backslashes
                    value = str(line.value).replace('\\', '')
                    rule = dateutil.rrule.rrulestr(value, dtstart=dtstart)
                    until = rule._until 
                    if until is not None and \
                       isinstance(dtstart, datetime.datetime) and \
                       (until.tzinfo != dtstart.tzinfo): 
                        # dateutil converts the UNTIL date to a datetime,
                        # check to see if the UNTIL parameter value was a date
                        vals = dict(pair.split('=') for pair in
                                    line.value.upper().split(';'))
                        if len(vals.get('UNTIL', '')) == 8:
                            until = datetime.datetime.combine(until.date(),
                                                              dtstart.time())
                        # While RFC2445 says UNTIL MUST be UTC, Chandler allows
                        # floating recurring events, and uses floating UNTIL values.
                        # Also, some odd floating UNTIL but timezoned DTSTART values
                        # have shown up in the wild, so put floating UNTIL values
                        # DTSTART's timezone
                        if until.tzinfo is None:
                            until = until.replace(tzinfo=dtstart.tzinfo)

                        if dtstart.tzinfo is not None:
                            until = until.astimezone(dtstart.tzinfo)

                        rule._until = until
                    
                    # add the rrule or exrule to the rruleset
                    addfunc(rule)
                    
                    if name == 'rrule' and addRDate:
                        try:
                            # dateutils does not work with all-day (datetime.date) items
                            # so we need to convert to a datetime.datetime
                            # (which is what dateutils does internally)
                            if not isinstance(dtstart, datetime.datetime):
                                adddtstart = datetime.datetime.fromordinal(dtstart.toordinal())
                            else:
                                adddtstart = dtstart
                            if rruleset._rrule[-1][0] != adddtstart:
                                rruleset.rdate(adddtstart)
                                added = True
                            else:
                                added = False
                        except IndexError:
                            # it's conceivable that an rrule might have 0 datetimes
                            added = False
                        if added and rruleset._rrule[-1]._count != None:
                            rruleset._rrule[-1]._count -= 1
        return rruleset

    def setrruleset(self, rruleset):
        
        # Get DTSTART from component (or DUE if no DTSTART in a VTODO)
        try:
            dtstart = self.dtstart.value
        except AttributeError, KeyError:
            if self.name == "VTODO":
                dtstart = self.due.value
            else:
                raise
            
        isDate = datetime.date == type(dtstart)
        if isDate:
            dtstart = datetime.datetime(dtstart.year,dtstart.month, dtstart.day)
            untilSerialize = dateToString
        else:
            # make sure to convert time zones to UTC
            untilSerialize = lambda x: dateTimeToString(x, True)

        for name in DATESANDRULES:
            if hasattr(self.contents, name):
                del self.contents[name]
            setlist = getattr(rruleset, '_' + name)
            if name in DATENAMES:
                setlist = list(setlist) # make a copy of the list
                if name == 'rdate' and dtstart in setlist:
                    setlist.remove(dtstart)
                if isDate:
                    setlist = [dt.date() for dt in setlist]
                if len(setlist) > 0:
                    self.add(name).value = setlist
            elif name in RULENAMES:
                for rule in setlist:
                    buf = StringIO.StringIO()
                    buf.write('FREQ=')
                    buf.write(FREQUENCIES[rule._freq])
                    
                    values = {}
                    
                    if rule._interval != 1:
                        values['INTERVAL'] = [str(rule._interval)]
                    if rule._wkst != 0: # wkst defaults to Monday
                        values['WKST'] = [WEEKDAYS[rule._wkst]]
                    if rule._bysetpos is not None:
                        values['BYSETPOS'] = [str(i) for i in rule._bysetpos]
                    
                    if rule._count is not None:
                        values['COUNT'] = [str(rule._count)]
                    elif rule._until is not None:
                        values['UNTIL'] = [untilSerialize(rule._until)]

                    days = []
                    if (rule._byweekday is not None and (
                                  dateutil.rrule.WEEKLY != rule._freq or 
                                   len(rule._byweekday) != 1 or 
                                rule._dtstart.weekday() != rule._byweekday[0])):
                        # ignore byweekday if freq is WEEKLY and day correlates
                        # with dtstart because it was automatically set by
                        # dateutil
                        days.extend(WEEKDAYS[n] for n in rule._byweekday)    
                        
                    if rule._bynweekday is not None:
                        days.extend(str(n) + WEEKDAYS[day] for day, n in rule._bynweekday)
                        
                    if len(days) > 0:
                        values['BYDAY'] = days 
                                                            
                    if rule._bymonthday is not None and len(rule._bymonthday) > 0:
                        if not (rule._freq <= dateutil.rrule.MONTHLY and
                                len(rule._bymonthday) == 1 and
                                rule._bymonthday[0] == rule._dtstart.day):
                            # ignore bymonthday if it's generated by dateutil
                            values['BYMONTHDAY'] = [str(n) for n in rule._bymonthday]

                    if rule._bynmonthday is not None and len(rule._bynmonthday) > 0:
                        values.setdefault('BYMONTHDAY', []).extend(str(n) for n in rule._bynmonthday)

                    if rule._bymonth is not None and len(rule._bymonth) > 0:
                        if (rule._byweekday is not None or
                            len(rule._bynweekday or ()) > 0 or
                            not (rule._freq == dateutil.rrule.YEARLY and
                                 len(rule._bymonth) == 1 and
                                 rule._bymonth[0] == rule._dtstart.month)):
                            # ignore bymonth if it's generated by dateutil
                            values['BYMONTH'] = [str(n) for n in rule._bymonth]

                    if rule._byyearday is not None:
                        values['BYYEARDAY'] = [str(n) for n in rule._byyearday]
                    if rule._byweekno is not None:
                        values['BYWEEKNO'] = [str(n) for n in rule._byweekno]

                    # byhour, byminute, bysecond are always ignored for now

                    
                    for key, paramvals in values.iteritems():
                        buf.write(';')
                        buf.write(key)
                        buf.write('=')
                        buf.write(','.join(paramvals))

                    self.add(name).value = buf.getvalue()


            
    rruleset = property(getrruleset, setrruleset)

    def __setattr__(self, name, value):
        """For convenience, make self.contents directly accessible."""
        if name == 'rruleset':
            self.setrruleset(value)
        else:
            super(RecurringComponent, self).__setattr__(name, value)

class TextBehavior(behavior.Behavior):
    """Provide backslash escape encoding/decoding for single valued properties.
    
    TextBehavior also deals with base64 encoding if the ENCODING parameter is
    explicitly set to BASE64.
    
    """
    base64string = 'BASE64' # vCard uses B
    
    @classmethod
    def decode(cls, line):
        """Remove backslash escaping from line.value."""
        if line.encoded:
            encoding = getattr(line, 'encoding_param', None)
            if encoding and encoding.upper() == cls.base64string:
                line.value = line.value.decode('base64')
            else:
                line.value = stringToTextValues(line.value)[0]
            line.encoded=False
    
    @classmethod
    def encode(cls, line):
        """Backslash escape line.value."""
        if not line.encoded:
            encoding = getattr(line, 'encoding_param', None)
            if encoding and encoding.upper() == cls.base64string:
                line.value = line.value.encode('base64').replace('\n', '')
            else:
                line.value = backslashEscape(line.value)
            line.encoded=True

class VCalendarComponentBehavior(behavior.Behavior):
    defaultBehavior = TextBehavior
    isComponent = True

class RecurringBehavior(VCalendarComponentBehavior):
    """Parent Behavior for components which should be RecurringComponents."""
    hasNative = True
    
    @staticmethod
    def transformToNative(obj):
        """Turn a recurring Component into a RecurringComponent."""
        if not obj.isNative:
            object.__setattr__(obj, '__class__', RecurringComponent)
            obj.isNative = True
        return obj
    
    @staticmethod
    def transformFromNative(obj):
        if obj.isNative:
            object.__setattr__(obj, '__class__', Component)
            obj.isNative = False
        return obj
    
    @staticmethod        
    def generateImplicitParameters(obj):
        """Generate a UID if one does not exist.
        
        This is just a dummy implementation, for now.
        
        """
        if not hasattr(obj, 'uid'):
            rand = str(int(random.random() * 100000))
            now = datetime.datetime.now(utc)
            now = dateTimeToString(now)
            host = socket.gethostname()
            obj.add(ContentLine('UID', [], now + '-' + rand + '@' + host))        
            
    
class DateTimeBehavior(behavior.Behavior):
    """Parent Behavior for ContentLines containing one DATE-TIME."""
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into a datetime.

        RFC2445 allows times without time zone information, "floating times"
        in some properties.  Mostly, this isn't what you want, but when parsing
        a file, real floating times are noted by setting to 'TRUE' the
        X-VOBJ-FLOATINGTIME-ALLOWED parameter.

        """
        if obj.isNative: return obj
        obj.isNative = True
        if obj.value == '': return obj
        obj.value=str(obj.value)
        #we're cheating a little here, parseDtstart allows DATE
        obj.value=parseDtstart(obj)
        if obj.value.tzinfo is None:
            obj.params['X-VOBJ-FLOATINGTIME-ALLOWED'] = ['TRUE']
        if obj.params.get('TZID'):
            # Keep a copy of the original TZID around
            obj.params['X-VOBJ-ORIGINAL-TZID'] = [obj.params['TZID']]
            del obj.params['TZID']
        return obj

    @classmethod
    def transformFromNative(cls, obj):
        """Replace the datetime in obj.value with an ISO 8601 string."""
        if obj.isNative:
            obj.isNative = False
            tzid = TimezoneComponent.registerTzinfo(obj.value.tzinfo)
            obj.value = dateTimeToString(obj.value, cls.forceUTC)
            if not cls.forceUTC and tzid is not None:
                obj.tzid_param = tzid
            if obj.params.get('X-VOBJ-ORIGINAL-TZID'):
                if not hasattr(obj, 'tzid_param'):
                    obj.tzid_param = obj.x_vobj_original_tzid_param
                del obj.params['X-VOBJ-ORIGINAL-TZID']

        return obj

class UTCDateTimeBehavior(DateTimeBehavior):
    """A value which must be specified in UTC."""
    forceUTC = True

class DateOrDateTimeBehavior(behavior.Behavior):
    """Parent Behavior for ContentLines containing one DATE or DATE-TIME."""
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into a date or datetime."""
        if obj.isNative: return obj
        obj.isNative = True
        if obj.value == '': return obj
        obj.value=str(obj.value)
        obj.value=parseDtstart(obj, allowSignatureMismatch=True)
        if getattr(obj, 'value_param', 'DATE-TIME').upper() == 'DATE-TIME':
            if hasattr(obj, 'tzid_param'):
                # Keep a copy of the original TZID around
                obj.params['X-VOBJ-ORIGINAL-TZID'] = [obj.tzid_param]
                del obj.tzid_param
        return obj

    @staticmethod
    def transformFromNative(obj):
        """Replace the date or datetime in obj.value with an ISO 8601 string."""
        if type(obj.value) == datetime.date:
            obj.isNative = False
            obj.value_param = 'DATE'
            obj.value = dateToString(obj.value)
            return obj
        else: return DateTimeBehavior.transformFromNative(obj)

class MultiDateBehavior(behavior.Behavior):
    """
    Parent Behavior for ContentLines containing one or more DATE, DATE-TIME, or
    PERIOD.
    
    """
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """
        Turn obj.value into a list of dates, datetimes, or
        (datetime, timedelta) tuples.
        
        """
        if obj.isNative:
            return obj
        obj.isNative = True
        if obj.value == '':
            obj.value = []
            return obj
        tzinfo = getTzid(getattr(obj, 'tzid_param', None))
        valueParam = getattr(obj, 'value_param', "DATE-TIME").upper()
        valTexts = obj.value.split(",")
        if valueParam == "DATE":
            obj.value = [stringToDate(x) for x in valTexts]
        elif valueParam == "DATE-TIME":
            obj.value = [stringToDateTime(x, tzinfo) for x in valTexts]
        elif valueParam == "PERIOD":
            obj.value = [stringToPeriod(x, tzinfo) for x in valTexts]
        return obj

    @staticmethod
    def transformFromNative(obj):
        """
        Replace the date, datetime or period tuples in obj.value with
        appropriate strings.
        
        """
        if obj.value and type(obj.value[0]) == datetime.date:
            obj.isNative = False
            obj.value_param = 'DATE'
            obj.value = ','.join([dateToString(val) for val in obj.value])
            return obj
        # Fixme: handle PERIOD case
        else:
            if obj.isNative:
                obj.isNative = False
                transformed = []
                tzid = None
                for val in obj.value:
                    if tzid is None and type(val) == datetime.datetime:
                        tzid = TimezoneComponent.registerTzinfo(val.tzinfo)
                        if tzid is not None:
                            obj.tzid_param = tzid
                    transformed.append(dateTimeToString(val))
                obj.value = ','.join(transformed)
            return obj

class MultiTextBehavior(behavior.Behavior):
    """Provide backslash escape encoding/decoding of each of several values.
    
    After transformation, value is a list of strings.
    
    """
    listSeparator = ","

    @classmethod
    def decode(cls, line):
        """Remove backslash escaping from line.value, then split on commas."""
        if line.encoded:
            line.value = stringToTextValues(line.value,
                listSeparator=cls.listSeparator)
            line.encoded=False
    
    @classmethod
    def encode(cls, line):
        """Backslash escape line.value."""
        if not line.encoded:
            line.value = cls.listSeparator.join(backslashEscape(val) for val in line.value)
            line.encoded=True
    

class SemicolonMultiTextBehavior(MultiTextBehavior):
    listSeparator = ";"

#------------------------ Registered Behavior subclasses -----------------------
class VCalendar2_0(VCalendarComponentBehavior):
    """vCalendar 2.0 behavior. With added VAVAILABILITY support."""
    name = 'VCALENDAR'
    description = 'vCalendar 2.0, also known as iCalendar.'
    versionString = '2.0'
    sortFirst = ('version', 'calscale', 'method', 'prodid', 'vtimezone')
    knownChildren = {'CALSCALE':      (0, 1, None),#min, max, behaviorRegistry id
                     'METHOD':        (0, 1, None),
                     'VERSION':       (0, 1, None),#required, but auto-generated
                     'PRODID':        (1, 1, None),
                     'VTIMEZONE':     (0, None, None),
                     'VEVENT':        (0, None, None),
                     'VTODO':         (0, None, None),
                     'VJOURNAL':      (0, None, None),
                     'VFREEBUSY':     (0, None, None),
                     'VAVAILABILITY': (0, None, None),
                    }
                    
    @classmethod
    def generateImplicitParameters(cls, obj):
        """Create PRODID, VERSION, and VTIMEZONEs if needed.
        
        VTIMEZONEs will need to exist whenever TZID parameters exist or when
        datetimes with tzinfo exist.
        
        """
        for comp in obj.components():
            if comp.behavior is not None:
                comp.behavior.generateImplicitParameters(comp)
        if not hasattr(obj, 'prodid'):
            obj.add(ContentLine('PRODID', [], PRODID))
        if not hasattr(obj, 'version'):
            obj.add(ContentLine('VERSION', [], cls.versionString))
        tzidsUsed = {}

        def findTzids(obj, table):
            if isinstance(obj, ContentLine) and (obj.behavior is None or
                                                 not obj.behavior.forceUTC):
                if getattr(obj, 'tzid_param', None):
                    table[obj.tzid_param] = 1
                else:
                    if type(obj.value) == list:
                        for item in obj.value:
                            tzinfo = getattr(obj.value, 'tzinfo', None)
                            tzid = TimezoneComponent.registerTzinfo(tzinfo)
                            if tzid:
                                table[tzid] = 1
                    else:
                        tzinfo = getattr(obj.value, 'tzinfo', None)
                        tzid = TimezoneComponent.registerTzinfo(tzinfo)
                        if tzid:
                            table[tzid] = 1
            for child in obj.getChildren():
                if obj.name != 'VTIMEZONE':
                    findTzids(child, table)
        
        findTzids(obj, tzidsUsed)
        oldtzids = [toUnicode(x.tzid.value) for x in getattr(obj, 'vtimezone_list', [])]
        for tzid in tzidsUsed.keys():
            tzid = toUnicode(tzid)
            if tzid != u'UTC' and tzid not in oldtzids:
                obj.add(TimezoneComponent(tzinfo=getTzid(tzid)))
registerBehavior(VCalendar2_0)

class VTimezone(VCalendarComponentBehavior):
    """Timezone behavior."""
    name = 'VTIMEZONE'
    hasNative = True
    description = 'A grouping of component properties that defines a time zone.'
    sortFirst = ('tzid', 'last-modified', 'tzurl', 'standard', 'daylight')
    knownChildren = {'TZID':         (1, 1, None),#min, max, behaviorRegistry id
                     'LAST-MODIFIED':(0, 1, None),
                     'TZURL':        (0, 1, None),
                     'STANDARD':     (0, None, None),#NOTE: One of Standard or
                     'DAYLIGHT':     (0, None, None) #      Daylight must appear
                    }

    @classmethod
    def validate(cls, obj, raiseException, *args):
        if not hasattr(obj, 'tzid') or obj.tzid.value is None:
            if raiseException:
                m = "VTIMEZONE components must contain a valid TZID"
                raise ValidateError(m)
            return False            
        if obj.contents.has_key('standard') or obj.contents.has_key('daylight'):
            return super(VTimezone, cls).validate(obj, raiseException, *args)
        else:
            if raiseException:
                m = "VTIMEZONE components must contain a STANDARD or a DAYLIGHT\
                     component"
                raise ValidateError(m)
            return False


    @staticmethod
    def transformToNative(obj):
        if not obj.isNative:
            object.__setattr__(obj, '__class__', TimezoneComponent)
            obj.isNative = True
            obj.registerTzinfo(obj.tzinfo)
        return obj

    @staticmethod
    def transformFromNative(obj):
        return obj
registerBehavior(VTimezone)

class TZID(behavior.Behavior):
    """Don't use TextBehavior for TZID.
    
    RFC2445 only allows TZID lines to be paramtext, so they shouldn't need any
    encoding or decoding.  Unfortunately, some Microsoft products use commas
    in TZIDs which should NOT be treated as a multi-valued text property, nor
    do we want to escape them.  Leaving them alone works for Microsoft's breakage,
    and doesn't affect compliant iCalendar streams.
    """
registerBehavior(TZID)

class DaylightOrStandard(VCalendarComponentBehavior):
    hasNative = False
    knownChildren = {'DTSTART':      (1, 1, None),#min, max, behaviorRegistry id
                     'RRULE':        (0, 1, None)}

registerBehavior(DaylightOrStandard, 'STANDARD')
registerBehavior(DaylightOrStandard, 'DAYLIGHT')


class VEvent(RecurringBehavior):
    """Event behavior."""
    name='VEVENT'
    sortFirst = ('uid', 'recurrence-id', 'dtstart', 'duration', 'dtend')

    description='A grouping of component properties, and possibly including \
                 "VALARM" calendar components, that represents a scheduled \
                 amount of time on a calendar.'
    knownChildren = {'DTSTART':      (0, 1, None),#min, max, behaviorRegistry id
                     'CLASS':        (0, 1, None),  
                     'CREATED':      (0, 1, None),
                     'DESCRIPTION':  (0, 1, None),  
                     'GEO':          (0, 1, None),  
                     'LAST-MODIFIED':(0, 1, None),
                     'LOCATION':     (0, 1, None),  
                     'ORGANIZER':    (0, 1, None),  
                     'PRIORITY':     (0, 1, None),  
                     'DTSTAMP':      (0, 1, None),
                     'SEQUENCE':     (0, 1, None),  
                     'STATUS':       (0, 1, None),  
                     'SUMMARY':      (0, 1, None),                     
                     'TRANSP':       (0, 1, None),  
                     'UID':          (1, 1, None),  
                     'URL':          (0, 1, None),  
                     'RECURRENCE-ID':(0, 1, None),  
                     'DTEND':        (0, 1, None), #NOTE: Only one of DtEnd or
                     'DURATION':     (0, 1, None), #      Duration can appear
                     'ATTACH':       (0, None, None),
                     'ATTENDEE':     (0, None, None),
                     'CATEGORIES':   (0, None, None),
                     'COMMENT':      (0, None, None),
                     'CONTACT':      (0, None, None),
                     'EXDATE':       (0, None, None),
                     'EXRULE':       (0, None, None),
                     'REQUEST-STATUS': (0, None, None),
                     'RELATED-TO':   (0, None, None),
                     'RESOURCES':    (0, None, None),
                     'RDATE':        (0, None, None),
                     'RRULE':        (0, None, None),
                     'VALARM':       (0, None, None)
                    }

    @classmethod
    def validate(cls, obj, raiseException, *args):
        if obj.contents.has_key('dtend') and obj.contents.has_key('duration'):
            if raiseException:
                m = "VEVENT components cannot contain both DTEND and DURATION\
                     components"
                raise ValidateError(m)
            return False
        else:
            return super(VEvent, cls).validate(obj, raiseException, *args)
      
registerBehavior(VEvent)


class VTodo(RecurringBehavior):
    """To-do behavior."""
    name='VTODO'
    description='A grouping of component properties and possibly "VALARM" \
                 calendar components that represent an action-item or \
                 assignment.'
    knownChildren = {'DTSTART':      (0, 1, None),#min, max, behaviorRegistry id
                     'CLASS':        (0, 1, None),
                     'COMPLETED':    (0, 1, None),
                     'CREATED':      (0, 1, None),
                     'DESCRIPTION':  (0, 1, None),  
                     'GEO':          (0, 1, None),  
                     'LAST-MODIFIED':(0, 1, None),
                     'LOCATION':     (0, 1, None),  
                     'ORGANIZER':    (0, 1, None),  
                     'PERCENT':      (0, 1, None),  
                     'PRIORITY':     (0, 1, None),  
                     'DTSTAMP':      (0, 1, None),
                     'SEQUENCE':     (0, 1, None),  
                     'STATUS':       (0, 1, None),  
                     'SUMMARY':      (0, 1, None),
                     'UID':          (0, 1, None),  
                     'URL':          (0, 1, None),  
                     'RECURRENCE-ID':(0, 1, None),  
                     'DUE':          (0, 1, None), #NOTE: Only one of Due or
                     'DURATION':     (0, 1, None), #      Duration can appear
                     'ATTACH':       (0, None, None),
                     'ATTENDEE':     (0, None, None),
                     'CATEGORIES':   (0, None, None),
                     'COMMENT':      (0, None, None),
                     'CONTACT':      (0, None, None),
                     'EXDATE':       (0, None, None),
                     'EXRULE':       (0, None, None),
                     'REQUEST-STATUS': (0, None, None),
                     'RELATED-TO':   (0, None, None),
                     'RESOURCES':    (0, None, None),
                     'RDATE':        (0, None, None),
                     'RRULE':        (0, None, None),
                     'VALARM':       (0, None, None)
                    }

    @classmethod
    def validate(cls, obj, raiseException, *args):
        if obj.contents.has_key('due') and obj.contents.has_key('duration'):
            if raiseException:
                m = "VTODO components cannot contain both DUE and DURATION\
                     components"
                raise ValidateError(m)
            return False
        else:
            return super(VTodo, cls).validate(obj, raiseException, *args)
      
registerBehavior(VTodo)


class VJournal(RecurringBehavior):
    """Journal entry behavior."""
    name='VJOURNAL'
    knownChildren = {'DTSTART':      (0, 1, None),#min, max, behaviorRegistry id
                     'CLASS':        (0, 1, None),  
                     'CREATED':      (0, 1, None),
                     'DESCRIPTION':  (0, 1, None),  
                     'LAST-MODIFIED':(0, 1, None),
                     'ORGANIZER':    (0, 1, None),  
                     'DTSTAMP':      (0, 1, None),
                     'SEQUENCE':     (0, 1, None),  
                     'STATUS':       (0, 1, None),  
                     'SUMMARY':      (0, 1, None),                     
                     'UID':          (0, 1, None),  
                     'URL':          (0, 1, None),  
                     'RECURRENCE-ID':(0, 1, None),  
                     'ATTACH':       (0, None, None),
                     'ATTENDEE':     (0, None, None),
                     'CATEGORIES':   (0, None, None),
                     'COMMENT':      (0, None, None),
                     'CONTACT':      (0, None, None),
                     'EXDATE':       (0, None, None),
                     'EXRULE':       (0, None, None),
                     'REQUEST-STATUS': (0, None, None),
                     'RELATED-TO':   (0, None, None),
                     'RDATE':        (0, None, None),
                     'RRULE':        (0, None, None)
                    }
registerBehavior(VJournal)


class VFreeBusy(VCalendarComponentBehavior):
    """Free/busy state behavior.

    >>> vfb = newFromBehavior('VFREEBUSY')
    >>> vfb.add('uid').value = 'test'
    >>> vfb.add('dtstart').value = datetime.datetime(2006, 2, 16, 1, tzinfo=utc)
    >>> vfb.add('dtend').value   = vfb.dtstart.value + twoHours
    >>> vfb.add('freebusy').value = [(vfb.dtstart.value, twoHours / 2)]
    >>> vfb.add('freebusy').value = [(vfb.dtstart.value, vfb.dtend.value)]
    >>> print vfb.serialize()
    BEGIN:VFREEBUSY
    UID:test
    DTSTART:20060216T010000Z
    DTEND:20060216T030000Z
    FREEBUSY:20060216T010000Z/PT1H
    FREEBUSY:20060216T010000Z/20060216T030000Z
    END:VFREEBUSY

    """
    name='VFREEBUSY'
    description='A grouping of component properties that describe either a \
                 request for free/busy time, describe a response to a request \
                 for free/busy time or describe a published set of busy time.'
    sortFirst = ('uid', 'dtstart', 'duration', 'dtend')
    knownChildren = {'DTSTART':      (0, 1, None),#min, max, behaviorRegistry id
                     'CONTACT':      (0, 1, None),
                     'DTEND':        (0, 1, None),
                     'DURATION':     (0, 1, None),
                     'ORGANIZER':    (0, 1, None),  
                     'DTSTAMP':      (0, 1, None), 
                     'UID':          (0, 1, None),  
                     'URL':          (0, 1, None),   
                     'ATTENDEE':     (0, None, None),
                     'COMMENT':      (0, None, None),
                     'FREEBUSY':     (0, None, None),
                     'REQUEST-STATUS': (0, None, None)
                    }
registerBehavior(VFreeBusy)


class VAlarm(VCalendarComponentBehavior):
    """Alarm behavior."""
    name='VALARM'
    description='Alarms describe when and how to provide alerts about events \
                 and to-dos.'
    knownChildren = {'ACTION':       (1, 1, None),#min, max, behaviorRegistry id
                     'TRIGGER':      (1, 1, None),  
                     'DURATION':     (0, 1, None),
                     'REPEAT':       (0, 1, None),
                     'DESCRIPTION':  (0, 1, None)
                    }

    @staticmethod
    def generateImplicitParameters(obj):
        """Create default ACTION and TRIGGER if they're not set."""
        try:
            obj.action
        except AttributeError:
            obj.add('action').value = 'AUDIO'
        try:
            obj.trigger
        except AttributeError:
            obj.add('trigger').value = datetime.timedelta(0)


    @classmethod
    def validate(cls, obj, raiseException, *args):
        """
        #TODO
     audioprop  = 2*(

                ; 'action' and 'trigger' are both REQUIRED,
                ; but MUST NOT occur more than once

                action / trigger /

                ; 'duration' and 'repeat' are both optional,
                ; and MUST NOT occur more than once each,
                ; but if one occurs, so MUST the other

                duration / repeat /

                ; the following is optional,
                ; but MUST NOT occur more than once

                attach /

     dispprop   = 3*(

                ; the following are all REQUIRED,
                ; but MUST NOT occur more than once

                action / description / trigger /

                ; 'duration' and 'repeat' are both optional,
                ; and MUST NOT occur more than once each,
                ; but if one occurs, so MUST the other

                duration / repeat /

     emailprop  = 5*(

                ; the following are all REQUIRED,
                ; but MUST NOT occur more than once

                action / description / trigger / summary

                ; the following is REQUIRED,
                ; and MAY occur more than once

                attendee /

                ; 'duration' and 'repeat' are both optional,
                ; and MUST NOT occur more than once each,
                ; but if one occurs, so MUST the other

                duration / repeat /

     procprop   = 3*(

                ; the following are all REQUIRED,
                ; but MUST NOT occur more than once

                action / attach / trigger /

                ; 'duration' and 'repeat' are both optional,
                ; and MUST NOT occur more than once each,
                ; but if one occurs, so MUST the other

                duration / repeat /

                ; 'description' is optional,
                ; and MUST NOT occur more than once

                description /
        if obj.contents.has_key('dtend') and obj.contents.has_key('duration'):
            if raiseException:
                m = "VEVENT components cannot contain both DTEND and DURATION\
                     components"
                raise ValidateError(m)
            return False
        else:
            return super(VEvent, cls).validate(obj, raiseException, *args)
        """
        return True
    
registerBehavior(VAlarm)

class VAvailability(VCalendarComponentBehavior):
    """Availability state behavior.

    >>> vav = newFromBehavior('VAVAILABILITY')
    >>> vav.add('uid').value = 'test'
    >>> vav.add('dtstamp').value = datetime.datetime(2006, 2, 15, 0, tzinfo=utc)
    >>> vav.add('dtstart').value = datetime.datetime(2006, 2, 16, 0, tzinfo=utc)
    >>> vav.add('dtend').value   = datetime.datetime(2006, 2, 17, 0, tzinfo=utc)
    >>> vav.add('busytype').value = "BUSY"
    >>> av = newFromBehavior('AVAILABLE')
    >>> av.add('uid').value = 'test1'
    >>> av.add('dtstamp').value = datetime.datetime(2006, 2, 15, 0, tzinfo=utc)
    >>> av.add('dtstart').value = datetime.datetime(2006, 2, 16, 9, tzinfo=utc)
    >>> av.add('dtend').value   = datetime.datetime(2006, 2, 16, 12, tzinfo=utc)
    >>> av.add('summary').value = "Available in the morning"
    >>> ignore = vav.add(av)
    >>> print vav.serialize()
    BEGIN:VAVAILABILITY
    UID:test
    DTSTART:20060216T000000Z
    DTEND:20060217T000000Z
    BEGIN:AVAILABLE
    UID:test1
    DTSTART:20060216T090000Z
    DTEND:20060216T120000Z
    DTSTAMP:20060215T000000Z
    SUMMARY:Available in the morning
    END:AVAILABLE
    BUSYTYPE:BUSY
    DTSTAMP:20060215T000000Z
    END:VAVAILABILITY

    """
    name='VAVAILABILITY'
    description='A component used to represent a user\'s available time slots.'
    sortFirst = ('uid', 'dtstart', 'duration', 'dtend')
    knownChildren = {'UID':           (1, 1, None),#min, max, behaviorRegistry id
                     'DTSTAMP':       (1, 1, None),
                     'BUSYTYPE':      (0, 1, None),
                     'CREATED':       (0, 1, None),
                     'DTSTART':       (0, 1, None),
                     'LAST-MODIFIED': (0, 1, None),
                     'ORGANIZER':     (0, 1, None),
                     'SEQUENCE':      (0, 1, None),
                     'SUMMARY':       (0, 1, None),
                     'URL':           (0, 1, None),
                     'DTEND':         (0, 1, None),
                     'DURATION':      (0, 1, None),
                     'CATEGORIES':    (0, None, None),
                     'COMMENT':       (0, None, None),
                     'CONTACT':       (0, None, None),
                     'AVAILABLE':     (0, None, None),
                    }

    @classmethod
    def validate(cls, obj, raiseException, *args):
        if obj.contents.has_key('dtend') and obj.contents.has_key('duration'):
            if raiseException:
                m = "VAVAILABILITY components cannot contain both DTEND and DURATION\
                     components"
                raise ValidateError(m)
            return False
        else:
            return super(VAvailability, cls).validate(obj, raiseException, *args)
      
registerBehavior(VAvailability)

class Available(RecurringBehavior):
    """Event behavior."""
    name='AVAILABLE'
    sortFirst = ('uid', 'recurrence-id', 'dtstart', 'duration', 'dtend')

    description='Defines a period of time in which a user is normally available.'
    knownChildren = {'DTSTAMP':      (1, 1, None),#min, max, behaviorRegistry id
                     'DTSTART':      (1, 1, None),
                     'UID':          (1, 1, None),  
                     'DTEND':        (0, 1, None), #NOTE: One of DtEnd or
                     'DURATION':     (0, 1, None), #      Duration must appear, but not both
                     'CREATED':      (0, 1, None),
                     'LAST-MODIFIED':(0, 1, None),
                     'RECURRENCE-ID':(0, 1, None),  
                     'RRULE':        (0, 1, None),
                     'SUMMARY':      (0, 1, None),                     
                     'CATEGORIES':   (0, None, None),
                     'COMMENT':      (0, None, None),
                     'CONTACT':      (0, None, None),
                     'EXDATE':       (0, None, None),
                     'RDATE':        (0, None, None),
                    }

    @classmethod
    def validate(cls, obj, raiseException, *args):
        has_dtend = obj.contents.has_key('dtend')
        has_duration = obj.contents.has_key('duration')
        if has_dtend and has_duration:
            if raiseException:
                m = "AVAILABLE components cannot contain both DTEND and DURATION\
                     properties"
                raise ValidateError(m)
            return False
        elif not (has_dtend or has_duration):
            if raiseException:
                m = "AVAILABLE components must contain one of DTEND or DURATION\
                     properties"
                raise ValidateError(m)
            return False
        else:
            return super(Available, cls).validate(obj, raiseException, *args)
      
registerBehavior(Available)

class Duration(behavior.Behavior):
    """Behavior for Duration ContentLines.  Transform to datetime.timedelta."""
    name = 'DURATION'
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into a datetime.timedelta."""
        if obj.isNative: return obj
        obj.isNative = True
        obj.value=str(obj.value)
        if obj.value == '':
            return obj
        else:
            deltalist=stringToDurations(obj.value)
            #When can DURATION have multiple durations?  For now:
            if len(deltalist) == 1:
                obj.value = deltalist[0]
                return obj
            else:
                raise ParseError("DURATION must have a single duration string.")

    @staticmethod
    def transformFromNative(obj):
        """Replace the datetime.timedelta in obj.value with an RFC2445 string.
        """
        if not obj.isNative: return obj
        obj.isNative = False
        obj.value = timedeltaToString(obj.value)
        return obj
    
registerBehavior(Duration)

class Trigger(behavior.Behavior):
    """DATE-TIME or DURATION"""
    name='TRIGGER'
    description='This property specifies when an alarm will trigger.'
    hasNative = True
    forceUTC = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into a timedelta or datetime."""
        if obj.isNative: return obj
        value = getattr(obj, 'value_param', 'DURATION').upper()
        if hasattr(obj, 'value_param'):
            del obj.value_param
        if obj.value == '':
            obj.isNative = True
            return obj
        elif value  == 'DURATION':
            try:
                return Duration.transformToNative(obj)
            except ParseError:
                logger.warn("TRIGGER not recognized as DURATION, trying "
                             "DATE-TIME, because iCal sometimes exports "
                             "DATE-TIMEs without setting VALUE=DATE-TIME")
                try:
                    obj.isNative = False
                    dt = DateTimeBehavior.transformToNative(obj)
                    return dt
                except:
                    msg = "TRIGGER with no VALUE not recognized as DURATION " \
                          "or as DATE-TIME"
                    raise ParseError(msg)
        elif value == 'DATE-TIME':
            #TRIGGERs with DATE-TIME values must be in UTC, we could validate
            #that fact, for now we take it on faith.
            return DateTimeBehavior.transformToNative(obj)
        else:
            raise ParseError("VALUE must be DURATION or DATE-TIME")        

    @staticmethod
    def transformFromNative(obj):
        if type(obj.value) == datetime.datetime:
            obj.value_param = 'DATE-TIME'
            return UTCDateTimeBehavior.transformFromNative(obj)
        elif type(obj.value) == datetime.timedelta:
            return Duration.transformFromNative(obj)
        else:
            raise NativeError("Native TRIGGER values must be timedelta or datetime")

registerBehavior(Trigger)

class PeriodBehavior(behavior.Behavior):
    """A list of (date-time, timedelta) tuples.

    >>> line = ContentLine('test', [], '', isNative=True)
    >>> line.behavior = PeriodBehavior
    >>> line.value = [(datetime.datetime(2006, 2, 16, 10), twoHours)]
    >>> line.transformFromNative().value
    '20060216T100000/PT2H'
    >>> line.transformToNative().value
    [(datetime.datetime(2006, 2, 16, 10, 0), datetime.timedelta(0, 7200))]
    >>> line.value.append((datetime.datetime(2006, 5, 16, 10), twoHours))
    >>> print line.serialize().strip()
    TEST:20060216T100000/PT2H,20060516T100000/PT2H
    """
    hasNative = True
    
    @staticmethod
    def transformToNative(obj):
        """Convert comma separated periods into tuples."""
        if obj.isNative:
            return obj
        obj.isNative = True
        if obj.value == '':
            obj.value = []
            return obj
        tzinfo = getTzid(getattr(obj, 'tzid_param', None))
        obj.value = [stringToPeriod(x, tzinfo) for x in obj.value.split(",")]
        return obj
        
    @classmethod
    def transformFromNative(cls, obj):
        """Convert the list of tuples in obj.value to strings."""
        if obj.isNative:
            obj.isNative = False
            transformed = []
            for tup in obj.value:
                transformed.append(periodToString(tup, cls.forceUTC))
            if len(transformed) > 0:
                tzid = TimezoneComponent.registerTzinfo(tup[0].tzinfo)
                if not cls.forceUTC and tzid is not None:
                    obj.tzid_param = tzid
                            
            obj.value = ','.join(transformed)

        return obj

class FreeBusy(PeriodBehavior):
    """Free or busy period of time, must be specified in UTC."""
    name = 'FREEBUSY'
    forceUTC = True
registerBehavior(FreeBusy)

class RRule(behavior.Behavior):
    """
    Dummy behavior to avoid having RRULEs being treated as text lines (and thus
    having semi-colons inaccurately escaped).
    """
registerBehavior(RRule, 'RRULE')
registerBehavior(RRule, 'EXRULE')

#------------------------ Registration of common classes -----------------------

utcDateTimeList = ['LAST-MODIFIED', 'CREATED', 'COMPLETED', 'DTSTAMP']
map(lambda x: registerBehavior(UTCDateTimeBehavior, x), utcDateTimeList)

dateTimeOrDateList = ['DTEND', 'DTSTART', 'DUE', 'RECURRENCE-ID']
map(lambda x: registerBehavior(DateOrDateTimeBehavior, x),
    dateTimeOrDateList)
    
registerBehavior(MultiDateBehavior, 'RDATE')
registerBehavior(MultiDateBehavior, 'EXDATE')


textList = ['CALSCALE', 'METHOD', 'PRODID', 'CLASS', 'COMMENT', 'DESCRIPTION',
            'LOCATION', 'STATUS', 'SUMMARY', 'TRANSP', 'CONTACT', 'RELATED-TO',
            'UID', 'ACTION', 'BUSYTYPE']
map(lambda x: registerBehavior(TextBehavior, x), textList)

multiTextList = ['CATEGORIES', 'RESOURCES']
map(lambda x: registerBehavior(MultiTextBehavior, x), multiTextList)
registerBehavior(SemicolonMultiTextBehavior, 'REQUEST-STATUS')

#------------------------ Serializing helper functions -------------------------

def numToDigits(num, places):
    """Helper, for converting numbers to textual digits."""
    s = str(num)
    if len(s) < places:
        return ("0" * (places - len(s))) + s
    elif len(s) > places:
        return s[len(s)-places: ]
    else:
        return s

def timedeltaToString(delta):
    """Convert timedelta to an rfc2445 DURATION."""
    if delta.days == 0: sign = 1
    else: sign = delta.days / abs(delta.days)
    delta = abs(delta)
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds % 3600) / 60
    seconds = delta.seconds % 60
    out = ''
    if sign == -1: out = '-'
    out += 'P'
    if days: out += str(days) + 'D'
    if hours or minutes or seconds: out += 'T'
    elif not days: #Deal with zero duration
        out += 'T0S'
    if hours: out += str(hours) + 'H'
    if minutes: out += str(minutes) + 'M'
    if seconds: out += str(seconds) + 'S'
    return out

def timeToString(dateOrDateTime):
    """
    Wraps dateToString and dateTimeToString, returning the results
    of either based on the type of the argument
    """
    # Didn't use isinstance here as date and datetime sometimes evalutes as both
    if (type(dateOrDateTime) == datetime.date):
        return dateToString(dateOrDateTime)
    elif(type(dateOrDateTime) == datetime.datetime):
        return dateTimeToString(dateOrDateTime)
    

def dateToString(date):
    year  = numToDigits( date.year,  4 )
    month = numToDigits( date.month, 2 )
    day   = numToDigits( date.day,   2 )
    return year + month + day

def dateTimeToString(dateTime, convertToUTC=False):
    """Ignore tzinfo unless convertToUTC.  Output string."""
    if dateTime.tzinfo and convertToUTC:
        dateTime = dateTime.astimezone(utc)
    if tzinfo_eq(dateTime.tzinfo, utc): utcString = "Z"
    else: utcString = ""

    year  = numToDigits( dateTime.year,  4 )
    month = numToDigits( dateTime.month, 2 )
    day   = numToDigits( dateTime.day,   2 )
    hour  = numToDigits( dateTime.hour,  2 )
    mins  = numToDigits( dateTime.minute,  2 )
    secs  = numToDigits( dateTime.second,  2 )

    return year + month + day + "T" + hour + mins + secs + utcString

def deltaToOffset(delta):
    absDelta = abs(delta)
    hours = absDelta.seconds / 3600
    hoursString      = numToDigits(hours, 2)
    minutesString    = '00'
    if absDelta == delta:
        signString = "+"
    else:
        signString = "-"
    return signString + hoursString + minutesString

def periodToString(period, convertToUTC=False):
    txtstart = dateTimeToString(period[0], convertToUTC)
    if isinstance(period[1], datetime.timedelta):
        txtend = timedeltaToString(period[1])
    else:
        txtend = dateTimeToString(period[1], convertToUTC)
    return txtstart + "/" + txtend

#----------------------- Parsing functions -------------------------------------

def isDuration(s):
    s = string.upper(s)
    return (string.find(s, "P") != -1) and (string.find(s, "P") < 2)

def stringToDate(s):
    year  = int( s[0:4] )
    month = int( s[4:6] )
    day   = int( s[6:8] )
    return datetime.date(year,month,day)

def stringToDateTime(s, tzinfo=None):
    """Returns datetime.datetime object."""
    try:
        year   = int( s[0:4] )
        month  = int( s[4:6] )
        day    = int( s[6:8] )
        hour   = int( s[9:11] )
        minute = int( s[11:13] )
        second = int( s[13:15] )
        if len(s) > 15:
            if s[15] == 'Z':
                tzinfo = utc
    except:
        raise ParseError("'%s' is not a valid DATE-TIME" % s)
    return datetime.datetime(year, month, day, hour, minute, second, 0, tzinfo)


# DQUOTE included to work around iCal's penchant for backslash escaping it,
# although it isn't actually supposed to be escaped according to rfc2445 TEXT
escapableCharList = '\\;,Nn"'

def stringToTextValues(s, listSeparator=',', charList=None, strict=False):
    """Returns list of strings."""
    
    if charList is None:
        charList = escapableCharList

    def escapableChar (c):
        return c in charList

    def error(msg):
        if strict:
            raise ParseError(msg)
        else:
            #logger.error(msg)
            print msg

    #vars which control state machine
    charIterator = enumerate(s)
    state        = "read normal"

    current = []
    results = []

    while True:
        try:
            charIndex, char = charIterator.next()
        except:
            char = "eof"

        if state == "read normal":
            if char == '\\':
                state = "read escaped char"
            elif char == listSeparator:
                state = "read normal"
                current = "".join(current)
                results.append(current)
                current = []
            elif char == "eof":
                state = "end"
            else:
                state = "read normal"
                current.append(char)

        elif state == "read escaped char":
            if escapableChar(char):
                state = "read normal"
                if char in 'nN': 
                    current.append('\n')
                else:
                    current.append(char)
            else:
                state = "read normal"
                # leave unrecognized escaped characters for later passes
                current.append('\\' + char)

        elif state == "end":    #an end state
            if len(current) or len(results) == 0:
                current = "".join(current)
                results.append(current)
            return results

        elif state == "error":  #an end state
            return results

        else:
            state = "error"
            error("error: unknown state: '%s' reached in %s" % (state, s))

def stringToDurations(s, strict=False):
    """Returns list of timedelta objects."""
    def makeTimedelta(sign, week, day, hour, minute, sec):
        if sign == "-": sign = -1
        else: sign = 1
        week      = int(week)
        day       = int(day)
        hour      = int(hour)
        minute    = int(minute)
        sec       = int(sec)
        return sign * datetime.timedelta(weeks=week, days=day, hours=hour, minutes=minute, seconds=sec)

    def error(msg):
        if strict:
            raise ParseError(msg)
        else:
            raise ParseError(msg)
            #logger.error(msg)
    
    #vars which control state machine
    charIterator = enumerate(s)
    state        = "start"

    durations = []
    current   = ""
    sign      = None
    week      = 0
    day       = 0
    hour      = 0
    minute    = 0
    sec       = 0

    while True:
        try:
            charIndex, char = charIterator.next()
        except:
            charIndex += 1
            char = "eof"

        if state == "start":
            if char == '+':
                state = "start"
                sign = char
            elif char == '-':
                state = "start"
                sign = char
            elif char.upper() == 'P':
                state = "read field"
            elif char == "eof":
                state = "error"
                error("got end-of-line while reading in duration: " + s)
            elif char in string.digits:
                state = "read field"
                current = current + char   #update this part when updating "read field"
            else:
                state = "error"
                print "got unexpected character %s reading in duration: %s" % (char, s)
                error("got unexpected character %s reading in duration: %s" % (char, s))

        elif state == "read field":
            if (char in string.digits):
                state = "read field"
                current = current + char   #update part above when updating "read field"   
            elif char.upper() == 'T':
                state = "read field"
            elif char.upper() == 'W':
                state = "read field"
                week    = current
                current = ""
            elif char.upper() == 'D':
                state = "read field"
                day     = current
                current = ""
            elif char.upper() == 'H':
                state = "read field"
                hour    = current
                current = ""
            elif char.upper() == 'M':
                state = "read field"
                minute  = current
                current = ""
            elif char.upper() == 'S':
                state = "read field"
                sec     = current
                current = ""
            elif char == ",":
                state = "start"
                durations.append( makeTimedelta(sign, week, day, hour, minute, sec) )
                current   = ""
                sign      = None
                week      = None
                day       = None
                hour      = None
                minute    = None
                sec       = None  
            elif char == "eof":
                state = "end"
            else:
                state = "error"
                error("got unexpected character reading in duration: " + s)
            
        elif state == "end":    #an end state
            #print "stuff: %s, durations: %s" % ([current, sign, week, day, hour, minute, sec], durations)

            if (sign or week or day or hour or minute or sec):
                durations.append( makeTimedelta(sign, week, day, hour, minute, sec) )
            return durations

        elif state == "error":  #an end state
            error("in error state")
            return durations

        else:
            state = "error"
            error("error: unknown state: '%s' reached in %s" % (state, s))

def parseDtstart(contentline, allowSignatureMismatch=False):
    """Convert a contentline's value into a date or date-time.
    
    A variety of clients don't serialize dates with the appropriate VALUE
    parameter, so rather than failing on these (technically invalid) lines,
    if allowSignatureMismatch is True, try to parse both varieties.
    
    """
    tzinfo = getTzid(getattr(contentline, 'tzid_param', None))
    valueParam = getattr(contentline, 'value_param', 'DATE-TIME').upper()
    if valueParam == "DATE":
        return stringToDate(contentline.value)
    elif valueParam == "DATE-TIME":
        try:
            return stringToDateTime(contentline.value, tzinfo)
        except:
            if allowSignatureMismatch:
                return stringToDate(contentline.value)
            else:
                raise

def stringToPeriod(s, tzinfo=None):
    values   = string.split(s, "/")
    start = stringToDateTime(values[0], tzinfo)
    valEnd   = values[1]
    if isDuration(valEnd): #period-start = date-time "/" dur-value
        delta = stringToDurations(valEnd)[0]
        return (start, delta)
    else:
        return (start, stringToDateTime(valEnd, tzinfo))


def getTransition(transitionTo, year, tzinfo):
    """Return the datetime of the transition to/from DST, or None."""

    def firstTransition(iterDates, test):
        """
        Return the last date not matching test, or None if all tests matched.
        """
        success = None
        for dt in iterDates:
            if not test(dt):
                success = dt
            else:
                if success is not None:
                    return success
        return success # may be None

    def generateDates(year, month=None, day=None):
        """Iterate over possible dates with unspecified values."""
        months = range(1, 13)
        days   = range(1, 32)
        hours  = range(0, 24)
        if month is None:
            for month in months:
                yield datetime.datetime(year, month, 1)
        elif day is None:
            for day in days:
                try:
                    yield datetime.datetime(year, month, day)
                except ValueError:
                    pass
        else:
            for hour in hours:
                yield datetime.datetime(year, month, day, hour)

    assert transitionTo in ('daylight', 'standard')
    if transitionTo == 'daylight':
        def test(dt): return tzinfo.dst(dt) != zeroDelta
    elif transitionTo == 'standard':
        def test(dt): return tzinfo.dst(dt) == zeroDelta
    newyear = datetime.datetime(year, 1, 1)
    monthDt = firstTransition(generateDates(year), test)
    if monthDt is None:
        return newyear
    elif monthDt.month == 12:
        return None
    else:
        # there was a good transition somewhere in a non-December month
        month = monthDt.month
        day         = firstTransition(generateDates(year, month), test).day
        uncorrected = firstTransition(generateDates(year, month, day), test)
        if transitionTo == 'standard':
            # assuming tzinfo.dst returns a new offset for the first
            # possible hour, we need to add one hour for the offset change
            # and another hour because firstTransition returns the hour
            # before the transition
            return uncorrected + datetime.timedelta(hours=2)
        else:
            return uncorrected + datetime.timedelta(hours=1)

def tzinfo_eq(tzinfo1, tzinfo2, startYear = 2000, endYear=2020):
    """Compare offsets and DST transitions from startYear to endYear."""
    if tzinfo1 == tzinfo2:
        return True
    elif tzinfo1 is None or tzinfo2 is None:
        return False
    
    def dt_test(dt):
        if dt is None:
            return True
        return tzinfo1.utcoffset(dt) == tzinfo2.utcoffset(dt)

    if not dt_test(datetime.datetime(startYear, 1, 1)):
        return False
    for year in xrange(startYear, endYear):
        for transitionTo in 'daylight', 'standard':
            t1=getTransition(transitionTo, year, tzinfo1)
            t2=getTransition(transitionTo, year, tzinfo2)
            if t1 != t2 or not dt_test(t1):
                return False
    return True


#------------------- Testing and running functions -----------------------------
if __name__ == '__main__':
    import tests
    tests._test()

########NEW FILE########
__FILENAME__ = ics_diff
"""Compare VTODOs and VEVENTs in two iCalendar sources."""
from base import Component, getBehavior, newFromBehavior

def getSortKey(component):
    def getUID(component):
        return component.getChildValue('uid', '')
    
    # it's not quite as simple as getUID, need to account for recurrenceID and 
    # sequence

    def getSequence(component):
        sequence = component.getChildValue('sequence', 0)
        return "%05d" % int(sequence)
    
    def getRecurrenceID(component):
        recurrence_id = component.getChildValue('recurrence_id', None)
        if recurrence_id is None:
            return '0000-00-00'
        else:
            return recurrence_id.isoformat()
    
    return getUID(component) + getSequence(component) + getRecurrenceID(component)

def sortByUID(components):
    return sorted(components, key=getSortKey)    

def deleteExtraneous(component, ignore_dtstamp=False):
    """
    Recursively walk the component's children, deleting extraneous details like
    X-VOBJ-ORIGINAL-TZID.
    """
    for comp in component.components():
        deleteExtraneous(comp, ignore_dtstamp)
    for line in component.lines():
        if line.params.has_key('X-VOBJ-ORIGINAL-TZID'):
            del line.params['X-VOBJ-ORIGINAL-TZID']
    if ignore_dtstamp and hasattr(component, 'dtstamp_list'):
        del component.dtstamp_list

def diff(left, right):
    """
    Take two VCALENDAR components, compare VEVENTs and VTODOs in them,
    return a list of object pairs containing just UID and the bits
    that didn't match, using None for objects that weren't present in one 
    version or the other.
    
    When there are multiple ContentLines in one VEVENT, for instance many
    DESCRIPTION lines, such lines original order is assumed to be 
    meaningful.  Order is also preserved when comparing (the unlikely case
    of) multiple parameters of the same type in a ContentLine
    
    """                
    
    def processComponentLists(leftList, rightList):
        output = []
        rightIndex = 0
        rightListSize = len(rightList)
        
        for comp in leftList:
            if rightIndex >= rightListSize:
                output.append((comp, None))
            else:
                leftKey  = getSortKey(comp)
                rightComp = rightList[rightIndex]
                rightKey = getSortKey(rightComp)
                while leftKey > rightKey:
                    output.append((None, rightComp))
                    rightIndex += 1
                    if rightIndex >= rightListSize:
                        output.append((comp, None))                    
                        break
                    else:
                        rightComp = rightList[rightIndex]
                        rightKey = getSortKey(rightComp)
                
                if leftKey < rightKey:
                    output.append((comp, None))
                elif leftKey == rightKey:
                    rightIndex += 1
                    matchResult = processComponentPair(comp, rightComp)
                    if matchResult is not None:
                        output.append(matchResult)
        
        return output

    def newComponent(name, body):
        if body is None:
            return None
        else:
            c = Component(name)
            c.behavior = getBehavior(name)
            c.isNative = True
            return c

    def processComponentPair(leftComp, rightComp):
        """
        Return None if a match, or a pair of components including UIDs and
        any differing children.
        
        """        
        leftChildKeys = leftComp.contents.keys()
        rightChildKeys = rightComp.contents.keys()
        
        differentContentLines = []
        differentComponents = {}
        
        for key in leftChildKeys:
            rightList = rightComp.contents.get(key, [])
            if isinstance(leftComp.contents[key][0], Component):
                compDifference = processComponentLists(leftComp.contents[key],
                                                       rightList)
                if len(compDifference) > 0:
                    differentComponents[key] = compDifference
                    
            elif leftComp.contents[key] != rightList:
                differentContentLines.append((leftComp.contents[key],
                                              rightList))
                
        for key in rightChildKeys:
            if key not in leftChildKeys:
                if isinstance(rightComp.contents[key][0], Component):
                    differentComponents[key] = ([], rightComp.contents[key])
                else:
                    differentContentLines.append(([], rightComp.contents[key]))
        
        if len(differentContentLines) == 0 and len(differentComponents) == 0:
            return None
        else:
            left  = newFromBehavior(leftComp.name)
            right = newFromBehavior(leftComp.name)
            # add a UID, if one existed, despite the fact that they'll always be
            # the same
            uid = leftComp.getChildValue('uid')
            if uid is not None:
                left.add( 'uid').value = uid
                right.add('uid').value = uid
                
            for name, childPairList in differentComponents.iteritems():
                leftComponents, rightComponents = zip(*childPairList)
                if len(leftComponents) > 0:
                    # filter out None
                    left.contents[name] = filter(None, leftComponents)
                if len(rightComponents) > 0:
                    # filter out None
                    right.contents[name] = filter(None, rightComponents)
            
            for leftChildLine, rightChildLine in differentContentLines:
                nonEmpty = leftChildLine or rightChildLine
                name = nonEmpty[0].name
                if leftChildLine is not None:
                    left.contents[name] = leftChildLine
                if rightChildLine is not None:
                    right.contents[name] = rightChildLine
            
            return left, right


    vevents = processComponentLists(sortByUID(getattr(left, 'vevent_list', [])),
                                    sortByUID(getattr(right, 'vevent_list', [])))
    
    vtodos = processComponentLists(sortByUID(getattr(left, 'vtodo_list', [])),
                                   sortByUID(getattr(right, 'vtodo_list', [])))
    
    return vevents + vtodos

def prettyDiff(leftObj, rightObj):
    for left, right in diff(leftObj, rightObj):
        print "<<<<<<<<<<<<<<<"
        if left is not None:
            left.prettyPrint()
        print "==============="
        if right is not None:
            right.prettyPrint()
        print ">>>>>>>>>>>>>>>"
        print
        
        
from optparse import OptionParser
import icalendar, base
import os
import codecs

def main():
    options, args = getOptions()
    if args:
        ignore_dtstamp = options.ignore
        ics_file1, ics_file2 = args
        cal1 = base.readOne(file(ics_file1))
        cal2 = base.readOne(file(ics_file2))
        deleteExtraneous(cal1, ignore_dtstamp=ignore_dtstamp)
        deleteExtraneous(cal2, ignore_dtstamp=ignore_dtstamp)
        prettyDiff(cal1, cal2)

version = "0.1"

def getOptions():
    ##### Configuration options #####

    usage = "usage: %prog [options] ics_file1 ics_file2"
    parser = OptionParser(usage=usage, version=version)
    parser.set_description("ics_diff will print a comparison of two iCalendar files ")

    parser.add_option("-i", "--ignore-dtstamp", dest="ignore", action="store_true",
                      default=False, help="ignore DTSTAMP lines [default: False]")

    (cmdline_options, args) = parser.parse_args()
    if len(args) < 2:
        print "error: too few arguments given"
        print
        print parser.format_help()
        return False, False

    return cmdline_options, args

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Aborted"

########NEW FILE########
__FILENAME__ = vcard
"""Definitions and behavior for vCard 3.0"""

import behavior
import itertools

from base import VObjectError, NativeError, ValidateError, ParseError, \
                    VBase, Component, ContentLine, logger, defaultSerialize, \
                    registerBehavior, backslashEscape, ascii
from icalendar import stringToTextValues

#------------------------ vCard structs ----------------------------------------

class Name(object):
    def __init__(self, family = '', given = '', additional = '', prefix = '',
                 suffix = ''):
        """Each name attribute can be a string or a list of strings."""
        self.family     = family
        self.given      = given
        self.additional = additional
        self.prefix     = prefix
        self.suffix     = suffix
        
    @staticmethod
    def toString(val):
        """Turn a string or array value into a string."""
        if type(val) in (list, tuple):
            return ' '.join(val)
        return val

    def __str__(self):
        eng_order = ('prefix', 'given', 'additional', 'family', 'suffix')
        out = ' '.join(self.toString(getattr(self, val)) for val in eng_order)
        return ascii(out)

    def __repr__(self):
        return "<Name: %s>" % self.__str__()

    def __eq__(self, other):
        try:
            return (self.family == other.family and
                    self.given == other.given and
                    self.additional == other.additional and
                    self.prefix == other.prefix and
                    self.suffix == other.suffix)
        except:
            return False

class Address(object):
    def __init__(self, street = '', city = '', region = '', code = '',
                 country = '', box = '', extended = ''):
        """Each name attribute can be a string or a list of strings."""
        self.box      = box
        self.extended = extended
        self.street   = street
        self.city     = city
        self.region   = region
        self.code     = code
        self.country  = country
        
    @staticmethod
    def toString(val, join_char='\n'):
        """Turn a string or array value into a string."""
        if type(val) in (list, tuple):
            return join_char.join(val)
        return val

    lines = ('box', 'extended', 'street')
    one_line = ('city', 'region', 'code')

    def __str__(self):
        lines = '\n'.join(self.toString(getattr(self, val)) for val in self.lines if getattr(self, val))
        one_line = tuple(self.toString(getattr(self, val), ' ') for val in self.one_line)
        lines += "\n%s, %s %s" % one_line
        if self.country:
            lines += '\n' + self.toString(self.country)
        return ascii(lines)

    def __repr__(self):
        return "<Address: %s>" % repr(str(self))[1:-1]

    def __eq__(self, other):
        try:
            return (self.box == other.box and
                    self.extended == other.extended and
                    self.street == other.street and
                    self.city == other.city and
                    self.region == other.region and
                    self.code == other.code and
                    self.country == other.country)
        except:
            False
        

#------------------------ Registered Behavior subclasses -----------------------

class VCardTextBehavior(behavior.Behavior):
    """Provide backslash escape encoding/decoding for single valued properties.
    
    TextBehavior also deals with base64 encoding if the ENCODING parameter is
    explicitly set to BASE64.
    
    """
    allowGroup = True
    base64string = 'B'
    
    @classmethod
    def decode(cls, line):
        """Remove backslash escaping from line.valueDecode line, either to remove
        backslash espacing, or to decode base64 encoding. The content line should
        contain a ENCODING=b for base64 encoding, but Apple Addressbook seems to
        export a singleton parameter of 'BASE64', which does not match the 3.0
        vCard spec. If we encouter that, then we transform the parameter to
        ENCODING=b"""
        if line.encoded:
            if 'BASE64' in line.singletonparams:
                line.singletonparams.remove('BASE64')
                line.encoding_param = cls.base64string
            encoding = getattr(line, 'encoding_param', None)
            if encoding:
                line.value = line.value.decode('base64')
            else:
                line.value = stringToTextValues(line.value)[0]
            line.encoded=False
    
    @classmethod
    def encode(cls, line):
        """Backslash escape line.value."""
        if not line.encoded:
            encoding = getattr(line, 'encoding_param', None)
            if encoding and encoding.upper() == cls.base64string:
                line.value = line.value.encode('base64').replace('\n', '')
            else:
                line.value = backslashEscape(line.value)
            line.encoded=True


class VCardBehavior(behavior.Behavior):
    allowGroup = True
    defaultBehavior = VCardTextBehavior

class VCard3_0(VCardBehavior):
    """vCard 3.0 behavior."""
    name = 'VCARD'
    description = 'vCard 3.0, defined in rfc2426'
    versionString = '3.0'
    isComponent = True
    sortFirst = ('version', 'prodid', 'uid')
    knownChildren = {'N':         (1, 1, None),#min, max, behaviorRegistry id
                     'FN':        (1, 1, None),
                     'VERSION':   (1, 1, None),#required, auto-generated
                     'PRODID':    (0, 1, None),
                     'LABEL':     (0, None, None),
                     'UID':       (0, None, None),
                     'ADR':       (0, None, None),
                     'ORG':       (0, None, None),
                     'PHOTO':     (0, None, None),
                     'CATEGORIES':(0, None, None)
                    }
                    
    @classmethod
    def generateImplicitParameters(cls, obj):
        """Create PRODID, VERSION, and VTIMEZONEs if needed.
        
        VTIMEZONEs will need to exist whenever TZID parameters exist or when
        datetimes with tzinfo exist.
        
        """
        if not hasattr(obj, 'version'):
            obj.add(ContentLine('VERSION', [], cls.versionString))
registerBehavior(VCard3_0, default=True)

class FN(VCardTextBehavior):
    name = "FN"
    description = 'Formatted name'
registerBehavior(FN)

class Label(VCardTextBehavior):
    name = "Label"
    description = 'Formatted address'
registerBehavior(Label)

wacky_apple_photo_serialize = True
REALLY_LARGE = 1E50

class Photo(VCardTextBehavior):
    name = "Photo"
    description = 'Photograph'
    @classmethod
    def valueRepr( cls, line ):
        return " (BINARY PHOTO DATA at 0x%s) " % id( line.value )

    @classmethod
    def serialize(cls, obj, buf, lineLength, validate):
        """Apple's Address Book is *really* weird with images, it expects
           base64 data to have very specific whitespace.  It seems Address Book
           can handle PHOTO if it's not wrapped, so don't wrap it."""
        if wacky_apple_photo_serialize:
            lineLength = REALLY_LARGE
        VCardTextBehavior.serialize(obj, buf, lineLength, validate)

registerBehavior(Photo)

def toListOrString(string):
    stringList = stringToTextValues(string)
    if len(stringList) == 1:
        return stringList[0]
    else:
        return stringList

def splitFields(string):
    """Return a list of strings or lists from a Name or Address."""
    return [toListOrString(i) for i in
            stringToTextValues(string, listSeparator=';', charList=';')]

def toList(stringOrList):
    if isinstance(stringOrList, basestring):
        return [stringOrList]
    return stringOrList

def serializeFields(obj, order=None):
    """Turn an object's fields into a ';' and ',' seperated string.
    
    If order is None, obj should be a list, backslash escape each field and
    return a ';' separated string.
    """
    fields = []
    if order is None:
        fields = [backslashEscape(val) for val in obj]
    else:
        for field in order:
            escapedValueList = [backslashEscape(val) for val in
                                toList(getattr(obj, field))]
            fields.append(','.join(escapedValueList))            
    return ';'.join(fields)

NAME_ORDER = ('family', 'given', 'additional', 'prefix', 'suffix')

class NameBehavior(VCardBehavior):
    """A structured name."""
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into a Name."""
        if obj.isNative: return obj
        obj.isNative = True
        obj.value = Name(**dict(zip(NAME_ORDER, splitFields(obj.value))))
        return obj

    @staticmethod
    def transformFromNative(obj):
        """Replace the Name in obj.value with a string."""
        obj.isNative = False
        obj.value = serializeFields(obj.value, NAME_ORDER)
        return obj
registerBehavior(NameBehavior, 'N')

ADDRESS_ORDER = ('box', 'extended', 'street', 'city', 'region', 'code', 
                 'country')

class AddressBehavior(VCardBehavior):
    """A structured address."""
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into an Address."""
        if obj.isNative: return obj
        obj.isNative = True
        obj.value = Address(**dict(zip(ADDRESS_ORDER, splitFields(obj.value))))
        return obj

    @staticmethod
    def transformFromNative(obj):
        """Replace the Address in obj.value with a string."""
        obj.isNative = False
        obj.value = serializeFields(obj.value, ADDRESS_ORDER)
        return obj
registerBehavior(AddressBehavior, 'ADR')
    
class OrgBehavior(VCardBehavior):
    """A list of organization values and sub-organization values."""
    hasNative = True

    @staticmethod
    def transformToNative(obj):
        """Turn obj.value into a list."""
        if obj.isNative: return obj
        obj.isNative = True
        obj.value = splitFields(obj.value)
        return obj

    @staticmethod
    def transformFromNative(obj):
        """Replace the list in obj.value with a string."""
        if not obj.isNative: return obj
        obj.isNative = False
        obj.value = serializeFields(obj.value)
        return obj
registerBehavior(OrgBehavior, 'ORG')
    

########NEW FILE########
__FILENAME__ = win32tz
import _winreg
import struct
import datetime

handle=_winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
tzparent=_winreg.OpenKey(handle,
            "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Time Zones")
parentsize=_winreg.QueryInfoKey(tzparent)[0]

localkey=_winreg.OpenKey(handle,
            "SYSTEM\\CurrentControlSet\\Control\\TimeZoneInformation")
WEEKS=datetime.timedelta(7)

def list_timezones():
    """Return a list of all time zones known to the system."""
    l=[]
    for i in xrange(parentsize):
        l.append(_winreg.EnumKey(tzparent, i))
    return l

class win32tz(datetime.tzinfo):
    """tzinfo class based on win32's timezones available in the registry.
    
    >>> local = win32tz('Central Standard Time')
    >>> oct1 = datetime.datetime(month=10, year=2004, day=1, tzinfo=local)
    >>> dec1 = datetime.datetime(month=12, year=2004, day=1, tzinfo=local)
    >>> oct1.dst()
    datetime.timedelta(0, 3600)
    >>> dec1.dst()
    datetime.timedelta(0)
    >>> braz = win32tz('E. South America Standard Time')
    >>> braz.dst(oct1)
    datetime.timedelta(0)
    >>> braz.dst(dec1)
    datetime.timedelta(0, 3600)
    
    """
    def __init__(self, name):
        self.data=win32tz_data(name)
        
    def utcoffset(self, dt):
        if self._isdst(dt):
            return datetime.timedelta(minutes=self.data.dstoffset)
        else:
            return datetime.timedelta(minutes=self.data.stdoffset)

    def dst(self, dt):
        if self._isdst(dt):
            minutes = self.data.dstoffset - self.data.stdoffset
            return datetime.timedelta(minutes=minutes)
        else:
            return datetime.timedelta(0)
        
    def tzname(self, dt):
        if self._isdst(dt): return self.data.dstname
        else: return self.data.stdname
    
    def _isdst(self, dt):
        dat=self.data
        dston = pickNthWeekday(dt.year, dat.dstmonth, dat.dstdayofweek,
                               dat.dsthour, dat.dstminute, dat.dstweeknumber)
        dstoff = pickNthWeekday(dt.year, dat.stdmonth, dat.stddayofweek,
                                dat.stdhour, dat.stdminute, dat.stdweeknumber)
        if dston < dstoff:
            if dston <= dt.replace(tzinfo=None) < dstoff: return True
            else: return False
        else:
            if dstoff <= dt.replace(tzinfo=None) < dston: return False
            else: return True

    def __repr__(self):
        return "<win32tz - %s>" % self.data.display

def pickNthWeekday(year, month, dayofweek, hour, minute, whichweek):
    """dayofweek == 0 means Sunday, whichweek > 4 means last instance"""
    first = datetime.datetime(year=year, month=month, hour=hour, minute=minute,
                              day=1)
    weekdayone = first.replace(day=((dayofweek - first.isoweekday()) % 7 + 1))
    for n in xrange(whichweek - 1, -1, -1):
        dt=weekdayone + n * WEEKS
        if dt.month == month: return dt


class win32tz_data(object):
    """Read a registry key for a timezone, expose its contents."""
    
    def __init__(self, path):
        """Load path, or if path is empty, load local time."""
        if path:
            keydict=valuesToDict(_winreg.OpenKey(tzparent, path))
            self.display = keydict['Display']
            self.dstname = keydict['Dlt']
            self.stdname = keydict['Std']
            
            #see http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
            tup = struct.unpack('=3l16h', keydict['TZI'])
            self.stdoffset = -tup[0]-tup[1] #Bias + StandardBias * -1
            self.dstoffset = self.stdoffset - tup[2] # + DaylightBias * -1
            
            offset=3
            self.stdmonth = tup[1 + offset]
            self.stddayofweek = tup[2 + offset] #Sunday=0
            self.stdweeknumber = tup[3 + offset] #Last = 5
            self.stdhour = tup[4 + offset]
            self.stdminute = tup[5 + offset]
            
            offset=11
            self.dstmonth = tup[1 + offset]
            self.dstdayofweek = tup[2 + offset] #Sunday=0
            self.dstweeknumber = tup[3 + offset] #Last = 5
            self.dsthour = tup[4 + offset]
            self.dstminute = tup[5 + offset]
            
        else:
            keydict=valuesToDict(localkey)
            
            self.stdname = keydict['StandardName']
            self.dstname = keydict['DaylightName']
            
            sourcekey=_winreg.OpenKey(tzparent, self.stdname)
            self.display = valuesToDict(sourcekey)['Display']
            
            self.stdoffset = -keydict['Bias']-keydict['StandardBias']
            self.dstoffset = self.stdoffset - keydict['DaylightBias']

            #see http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
            tup = struct.unpack('=8h', keydict['StandardStart'])

            offset=0
            self.stdmonth = tup[1 + offset]
            self.stddayofweek = tup[2 + offset] #Sunday=0
            self.stdweeknumber = tup[3 + offset] #Last = 5
            self.stdhour = tup[4 + offset]
            self.stdminute = tup[5 + offset]
            
            tup = struct.unpack('=8h', keydict['DaylightStart'])
            self.dstmonth = tup[1 + offset]
            self.dstdayofweek = tup[2 + offset] #Sunday=0
            self.dstweeknumber = tup[3 + offset] #Last = 5
            self.dsthour = tup[4 + offset]
            self.dstminute = tup[5 + offset]

def valuesToDict(key):
    """Convert a registry key's values to a dictionary."""
    dict={}
    size=_winreg.QueryInfoKey(key)[1]
    for i in xrange(size):
        dict[_winreg.EnumValue(key, i)[0]]=_winreg.EnumValue(key, i)[1]
    return dict

def _test():
    import win32tz, doctest
    doctest.testmod(win32tz, verbose=0)

if __name__ == '__main__':
    _test()
########NEW FILE########
