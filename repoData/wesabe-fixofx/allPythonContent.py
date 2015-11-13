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
                    res.microsecond = 2
                elif mstridx == 1:
                    if ymd[0] > 31 or (yearfirst and ymd[2] <= 31):
                        # 99-Jan-01
                        res.year, res.month, res.day = ymd
                        res.microsecond = 1
                    else:
                        # 01-Jan-01
                        # Give precendence to day-first, since
                        # two-digit years is usually hand-written.
                        res.day, res.month, res.year = ymd
                        res.microsecond = 3
                elif mstridx == 2:
                    # WTF!?
                    if ymd[1] > 31:
                        # 01-99-Jan
                        res.day, res.year, res.month = ymd
                        res.microsecond = 3
                    else:
                        # 99-01-Jan
                        res.year, res.day, res.month = ymd
                        res.microsecond = 1
                else:
                    if ymd[0] > 31 or \
                       (yearfirst and ymd[1] <= 12 and ymd[2] <= 31):
                        # 99-01-01
                        res.year, res.month, res.day = ymd
                        res.microsecond = 1
                    elif ymd[0] > 12 or (dayfirst and ymd[1] <= 12):
                        # 13-01-01
                        res.day, res.month, res.year = ymd
                        res.microsecond = 3
                    else:
                        # 01-13-01
                        res.month, res.day, res.year = ymd
                        res.microsecond = 2

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
            self._bysetpos = (bysetpos,)
        else:
            self._bysetpos = tuple(bysetpos)
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
                raise "unknown parameter '%s'" % name
            except (KeyError, ValueError):
                raise "invalid '%s': %s" % (name, value)
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
            leap = struct.unpack(">%dl" % leapcnt*2,
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
            tti = _ttinfo()
            tti.offset = ttinfo[i][0]
            tti.delta = datetime.timedelta(seconds=ttinfo[i][0])
            tti.isdst = ttinfo[i][1]
            tti.abbr = abbr[ttinfo[i][2]:abbr.find('\x00', ttinfo[i][2])]
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
                raise "no timezones defined"
            elif len(keys) > 1:
                raise "more than one timezone available"
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
__FILENAME__ = pyparsing
# module pyparsing.py
#
# Copyright (c) 2003-2006  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#  Todo:
#  - add pprint() - pretty-print output of defined BNF
#
#from __future__ import generators

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars

The pyparsing module is an alternative approach to creating and executing simple grammars, 
vs. the traditional lex/yacc approach, or the use of regular expressions.  With pyparsing, you
don't need to learn a new syntax for defining grammars or matching expressions - the parsing module 
provides a library of classes that you use to construct the grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form "<salutation>, <addressee>!")::

    from pyparsing import Word, alphas
    
    # define grammar of a greeting
    greet = Word( alphas ) + "," + Word( alphas ) + "!" 
    
    hello = "Hello, World!"
    print hello, "->", greet.parseString( hello )

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the self-explanatory 
class names, and the use of '+', '|' and '^' operators.

The parsed results returned from parseString() can be accessed as a nested list, a dictionary, or an 
object with named attributes.

The pyparsing module handles some of the problems that are typically vexing when writing text parsers:
 - extra or missing whitespace (the above program will also handle "Hello,World!", "Hello  ,  World  !", etc.)
 - quoted strings
 - embedded comments
"""
__version__ = "1.4.2"
__versionTime__ = "31 March 2006 17:53"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
import copy,sys
import warnings
import re
#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

def _ustr(obj):
    """Drop-in replacement for str(obj) that tries to be Unicode friendly. It first tries
       str(obj). If that fails with a UnicodeEncodeError, then it tries unicode(obj). It
       then < returns the unicode object | encodes it with the default encoding | ... >.
    """
    try:
        # If this works, then _ustr(obj) has the same behaviour as str(obj), so
        # it won't break any existing code.
        return str(obj)
        
    except UnicodeEncodeError, e:
        # The Python docs (http://docs.python.org/ref/customization.html#l2h-182)
        # state that "The return value must be a string object". However, does a
        # unicode object (being a subclass of basestring) count as a "string
        # object"?
        # If so, then return a unicode object:
        return unicode(obj)
        # Else encode it... but how? There are many choices... :)
        # Replace unprintables with escape codes?
        #return unicode(obj).encode(sys.getdefaultencoding(), 'backslashreplace_errors')
        # Replace unprintables with question marks?
        #return unicode(obj).encode(sys.getdefaultencoding(), 'replace')
        # ...

def _str2dict(strg):
    return dict( [(c,0) for c in strg] )

alphas     = string.lowercase + string.uppercase
nums       = string.digits
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums    

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    __slots__ = ( "loc","msg","pstr","parserElement" )
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible        
    def __init__( self, pstr, loc, msg, elem=None ):
        self.loc = loc
        self.msg = msg
        self.pstr = pstr
        self.parserElement = elem

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError, aname

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks 
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join( [line_str[:line_column], markerString, line_str[line_column:]])
        return line_str.strip()

class ParseException(ParseBaseException):
    """exception thrown when parse expressions don't match class"""
    """supported attributes by name are:
        - lineno - returns the line number of the exception text
        - col - returns the column number of the exception text
        - line - returns the line containing the exception text
    """
    pass
    
class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass
    
class RecursiveGrammarException(Exception):
    """exception thrown by validate() if the grammar could be improperly recursive"""
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList
    
    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (len(results))
       - by list index (results[0], results[1], etc.)
       - by attribute (results.<resultsName>)
       """
    __slots__ = ( "__toklist", "__tokdict", "__doinit", "__name", "__parent", "__modal" )
    def __new__(cls, toklist, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj
        
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist, name=None, asList=True, modal=True ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__modal = modal
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        # this line is related to debugging the asXML bug
        #~ asList = False
        
        if name:
            if not self.__name:
                self.__modal = self.__modal and modal
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not toklist in (None,'',[]):
                if isinstance(toklist,basestring): 
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = (toklist.copy(),-1)
                    else:
                        self[name] = (ParseResults(toklist[0]),-1)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except TypeError:
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if self.__modal:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v ):
        if isinstance(v,tuple):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = self
        
    def __delitem__( self, i ):
        del self.__toklist[i]

    def __contains__( self, k ):
        return self.__tokdict.has_key(k)
        
    def __len__( self ): return len( self.__toklist )
    def __iter__( self ): return iter( self.__toklist )
    def keys( self ): 
        """Returns all named result keys."""
        return self.__tokdict.keys()
    
    def items( self ): 
        """Returns all named result keys and values as a list of tuples."""
        return [(k,v[-1][0]) for k,v in self.__tokdict.items()]
    
    def values( self ): 
        """Returns all named result values."""
        return [ v[-1][0] for v in self.__tokdict.values() ]

    def __getattr__( self, name ):
        if name not in self.__slots__:
            if self.__tokdict.has_key( name ):
                if self.__modal:
                    return self.__tokdict[name][-1][0]
                else:
                    return ParseResults([ v[0] for v in self.__tokdict[name] ])
            else:
                return ""
        return None

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = ( lambda a: (a<0 and offset) or (a+offset) )
            otherdictitems = [(k,(v[0],addoffset(v[1])) ) for (k,vlist) in other.__tokdict.items() for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = self
        self.__toklist += other.__toklist
        del other
        return self
       
    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        out = "["
        sep = ""
        for i in self.__toklist:
            if isinstance(i, ParseResults):
                out += sep + _ustr(i)
            else:
                out += sep + repr(i)
            sep = ", "
        out += "]"
        return out

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """Returns the parse results as a nested list of matching tokens, all converted to strings."""
        out = []
        for res in self.__toklist:
            if isinstance(res,ParseResults):
                out.append( res.asList() )
            else:
                out.append( res )
        return out

    def asDict( self ):
        """Returns the named parse results as dictionary."""
        return dict( self.items() )

    def copy( self ):
        """Returns a new copy of a ParseResults object."""
        ret = ParseResults( self.__toklist )
        ret.__tokdict = self.__tokdict.copy()
        ret.__parent = self.__parent
        ret.__modal = self.__modal
        ret.__name = self.__name
        return ret
        
    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        nl = "\n"
        out = []
        namedItems = dict( [ (v[1],k) for (k,vlist) in self.__tokdict.items() for v in vlist ] )
        nextLevelIndent = indent + "  "
        
        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""
            
        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name
        
        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"
                
        out += [ nl, indent, "<", selfTag, ">" ]
        
        worklist = self.__toklist
        for i,res in enumerate(worklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i], namedItemsOnly and doctag is None, nextLevelIndent,formatted)]
                else:
                    out += [ res.asXML(None, namedItemsOnly and doctag is None, nextLevelIndent,formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                out += [ nl, nextLevelIndent, "<", resTag, ">", _ustr(res), "</", resTag, ">" ]
        
        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None
            
    def getName(self):
        """Returns the results name for this token expression."""
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and 
               len(self.__tokdict) == 1 and
               self.__tokdict.values()[0][0][1] in (0,-1)):
            return self.__tokdict.keys()[0]
        else:
            return None
            
    def dump(self,indent='',depth=0):
        """Diagnostic method for listing out the contents of a ParseResults.
           Accepts an optional indent argument so that this string can be embedded
           in a nested display of other data."""
        out = []
        keys = self.items()
        keys.sort()
        for k,v in keys:
            if out:
                out.append('\n')
            out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
            if isinstance(v,ParseResults):
                if v.keys():
                    out.append('\n')
                    out.append( dump(v,indent,depth+1) )
                    out.append('\n')
                else:
                    out.append(str(v))
            else:
                out.append(str(v))
        out.append('\n')
        out.append( indent+str(self.asList()) )
        return "".join(out)
    
def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.
   """
    return loc - strg.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
   The first line is number 1.
   """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR > 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print "Match",expr,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) )

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print "Matched",expr,"->",toks.asList()
    
def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print "Exception raised:", exc

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

class ParserElement(object):
    """Abstract base level parser element class."""
    DEFAULT_WHITE_CHARS = " \n\t\r"
    
    def setDefaultWhitespaceChars( chars ):
        """Overrides the default whitespace chars
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars
    setDefaultWhitespaceChars = staticmethod(setDefaultWhitespaceChars)
    
    def __init__( self, savelist=False ):
        self.parseAction = list()
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        self.mayReturnEmpty = False
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True
        self.errmsg = ""
        self.modalResults = True
        self.debugActions = ( None, None, None )
        self.re = None

    def copy( self ):
        """Make a copy of this ParserElement.  Useful for defining different parse actions
           for the same parsing pattern, using copies of the original parse element."""
        cpy = copy.copy( self )
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName( self, name ):
        """Define name for this expression, for use in debugging."""
        self.name = name
        self.errmsg = "Expected " + self.name
        return self

    def setResultsName( self, name, listAllMatches=False ):
        """Define name for referencing matching tokens as a nested attribute 
           of the returned parse results.
           NOTE: this returns a *copy* of the original ParserElement object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.
        """
        newself = self.copy()
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setParseAction( self, *fns ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with the arguments (s, loc, toks) where:
            - s   = the original string being parsed
            - loc = the location of the matching substring
            - toks = a list of the matched tokens, packaged as a ParseResults object
           If the functions in fns modify the tokens, it can return them as the return
           value from fn, and the modified list of tokens will replace the original.
           Otherwise, fn does not need to return any value.
        """
        self.parseAction += fns
        return self

    def skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e._parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self.skipIgnorables( instring, loc )
        
        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1
                
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc, []

    def postParse( self, instring, loc, tokenlist ):
        return tokenlist

    #~ @profile
    def _parseNoCache( self, instring, loc, doActions=True, callPreParse=True ):
        debugging = ( self.debug ) #and doActions )

        if debugging:
            #~ print "Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) )
            if (self.debugActions[0] ):
                self.debugActions[0]( instring, loc, self )
            if callPreParse:
                loc = self.preParse( instring, loc )
            tokensStart = loc
            try:
                try:
                    loc,tokens = self.parseImpl( instring, loc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            except ParseException, err:
                #~ print "Exception raised:", err
                if (self.debugActions[2] ):
                    self.debugActions[2]( instring, tokensStart, self, err )
                raise
        else:
            if callPreParse:
                loc = self.preParse( instring, loc )
            tokensStart = loc
            if self.mayIndexError or loc >= len(instring):
                try:
                    loc,tokens = self.parseImpl( instring, loc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            else:
                loc,tokens = self.parseImpl( instring, loc, doActions )
        
        tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults )
        if self.parseAction and doActions:
            if debugging:
                try:
                    for fn in self.parseAction:
                        tokens = fn( instring, tokensStart, retTokens )
                        if tokens is not None:
                            if isinstance(tokens,tuple):
                                tokens = tokens[1]
                                warnings.warn("Returning loc from parse actions is deprecated, return only modified tokens", DeprecationWarning,stacklevel=2)
                            retTokens = ParseResults( tokens, 
                                                      self.resultsName, 
                                                      asList=self.saveAsList and isinstance(tokens,(ParseResults,list)), 
                                                      modal=self.modalResults )
                except ParseException, err:
                    #~ print "Exception raised in user parse action:", err
                    if (self.debugActions[2] ):
                        self.debugActions[2]( instring, tokensStart, self, err )
                    raise
            else:
                for fn in self.parseAction:
                    tokens = fn( instring, tokensStart, retTokens )
                    if tokens is not None:
                        if isinstance(tokens,tuple):
                            tokens = tokens[1]
                            warnings.warn("Returning loc from parse actions is deprecated, return only modified tokens", DeprecationWarning,stacklevel=2)
                        retTokens = ParseResults( tokens, 
                                                  self.resultsName, 
                                                  asList=self.saveAsList and isinstance(tokens,(ParseResults,list)), 
                                                  modal=self.modalResults )

        if debugging:
            #~ print "Matched",self,"->",retTokens.asList()
            if (self.debugActions[1] ):
                self.debugActions[1]( instring, tokensStart, loc, self, retTokens )

        return loc, retTokens

    def tryParse( self, instring, loc ):
        return self._parse( instring, loc, doActions=False )[0]
    
    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        lookup = (self,instring,loc,callPreParse)
        if lookup in ParserElement._exprArgCache:
            value = ParserElement._exprArgCache[ lookup ]
            if isinstance(value,Exception):
                if isinstance(value,ParseBaseException):
                    value.loc = loc
                raise value
            return value
        else:
            try:
                ParserElement._exprArgCache[ lookup ] = \
                    value = self._parseNoCache( instring, loc, doActions, callPreParse )
                return value
            except Exception, pe:
                ParserElement._exprArgCache[ lookup ] = pe
                raise

    _parse = _parseNoCache

    # argument cache for optimizing repeated calls when backtracking through recursive expressions
    _exprArgCache = {}
    def resetCache():
        ParserElement._exprArgCache.clear()
    resetCache = staticmethod(resetCache)
    
    _packratEnabled = False
    def enablePackrat():
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens 
           often in many complex grammars) can immediately return a cached value, 
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.
            
           This speedup may break existing programs that use parse actions that 
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method ParserElement.enablePackrat().  If
           your program uses psyco to "compile as you go", you must call 
           enablePackrat before calling psyco.full().  If you do not do this,
           Python will crash.  For best results, call enablePackrat() immediately
           after importing pyparsing.
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            ParserElement._parse = ParserElement._parseCache
    enablePackrat = staticmethod(enablePackrat)

    def parseString( self, instring ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete 
           expression has been built.
        """
        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if self.keepTabs:
            loc, tokens = self._parse( instring, 0 )
        else:
            loc, tokens = self._parse( instring.expandtabs(), 0 )
        return tokens

    def scanString( self, instring ):
        """Scan the input string for expression matches.  Each match will return the matching tokens, start location, and end location."""
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()
        
        if not self.keepTabs:
            instring = instring.expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        while loc < instrlen:
            try:
                loc = preparseFn( instring, loc )
                nextLoc,tokens = parseFn( instring, loc, callPreParse=False )
            except ParseException:
                loc += 1
            else:
                yield tokens, loc, nextLoc
                loc = nextLoc
        
    def transformString( self, instring ):
        """Extension to scanString, to modify matching text with modified tokens that may
           be returned from a parse action.  To use transformString, define a grammar and 
           attach a parse action to it that modifies the returned token list.  
           Invoking transformString() on a target string will then scan for matches, 
           and replace the matched text patterns according to the logic in the parse 
           action.  transformString() returns the resulting transformed string."""
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        for t,s,e in self.scanString( instring ):
            out.append( instring[lastE:s] )
            if t:
                if isinstance(t,ParseResults):
                    out += t.asList()
                elif isinstance(t,list):
                    out += t
                else:
                    out.append(t)
            lastE = e
        out.append(instring[lastE:])
        return "".join(out)

    def searchString( self, instring ):
        """Another extension to scanString, simplifying the access to the tokens found
           to match the given parse expression.
        """
        return [ t[0] for t,s,e in self.scanString( instring ) ]
            
    def __add__(self, other ):
        """Implementation of + operator - returns And"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return And( [ self, other ] )

    def __radd__(self, other ):
        """Implementation of += operator"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return other + self

    def __or__(self, other ):
        """Implementation of | operator - returns MatchFirst"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        """Implementation of |= operator"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return other | self

    def __xor__(self, other ):
        """Implementation of ^ operator - returns Or"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        """Implementation of ^= operator"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return other ^ self

    def __and__(self, other ):
        """Implementation of & operator - returns Each"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return Each( [ self, other ] )

    def __rand__(self, other ):
        """Implementation of right-& operator"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot add element of type %s to ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
        return other & self

    def __invert__( self ):
        """Implementation of ~ operator - returns NotAny"""
        return NotAny( self )

    def suppress( self ):
        """Suppresses the output of this ParserElement; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        """Disables the skipping of whitespace before matching the characters in the 
           ParserElement's defined pattern.  This is normally only used internally by
           the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars( self, chars ):
        """Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        
    def parseWithTabs( self ):
        """Overrides default behavior to expand <TAB>s to spaces before parsing the input string.
           Must be called before parseString when the input grammar contains elements that 
           match <TAB> characters."""
        self.keepTabs = True
        return self
        
    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern 
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append( other )
        else:
            self.ignoreExprs.append( Suppress( other ) )
        return self

    def setDebugActions( self, startAction, successAction, exceptionAction ):
        """Enable display of debugging messages while doing pattern matching."""
        self.debugActions = (startAction or _defaultStartDebugAction, 
                             successAction or _defaultSuccessDebugAction, 
                             exceptionAction or _defaultExceptionDebugAction)
        self.debug = True
        return self

    def setDebug( self, flag=True ):
        """Enable display of debugging messages while doing pattern matching."""
        if flag:
            self.setDebugActions( _defaultStartDebugAction, _defaultSuccessDebugAction, _defaultExceptionDebugAction )
        else:
            self.debug = False
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return _ustr(self)
        
    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self
        
    def checkRecursion( self, parseElementList ):
        pass
        
    def validate( self, validateTrace=[] ):
        """Check defined expressions for valid structure, check for infinite recursive definitions."""
        self.checkRecursion( [] )

    def parseFile( self, file_or_filename ):
        """Execute the parse expression on the given file or filename.
           If a filename is specified (instead of a file object),
           the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            f = open(file_or_filename, "rb")
            file_contents = f.read()
            f.close()
        return self.parseString(file_contents)


class Token(ParserElement):
    """Abstract ParserElement subclass, for defining atomic matching patterns."""
    def __init__( self ):
        super(Token,self).__init__( savelist=False )
        self.myException = ParseException("",0,"",self)

    def setName(self, name):
        s = super(Token,self).setName(name)
        self.errmsg = "Expected " + self.name
        s.myException.msg = self.errmsg
        return s


class Empty(Token):
    """An empty token, will always match."""
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match."""
    def __init__( self ):
        super(NoMatch,self).__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"
        self.myException.msg = self.errmsg
        
    def parseImpl( self, instring, loc, doActions=True ):
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc


class Literal(Token):
    """Token to exactly match a specified string."""
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Literal; use Empty() instead", 
                            SyntaxWarning, stacklevel=2)
            self.__class__ = Empty
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        self.myException.msg = self.errmsg
        self.mayIndexError = False

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid calling startswith
    #~ @profile
    def parseImpl( self, instring, loc, doActions=True ):
        if (instring[loc] == self.firstMatchChar and
            (self.matchLen==1 or instring.startswith(self.match,loc)) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is, it must be 
       immediately followed by a non-keyword character.  Compare with Literal::
         Literal("if") will match the leading 'if' in 'ifAndOnlyIf'.
         Keyword("if") will not; it will only match the leading 'if in 'if x=1', or 'if(y==2)'
       Accepts two optional constructor arguments in addition to the keyword string:
       identChars is a string of characters that would be valid identifier characters,
       defaulting to all alphanumerics + "_" and "$"; caseless allows case-insensitive
       matching, default is False.
    """
    DEFAULT_KEYWORD_CHARS = alphanums+"_$"
    
    def __init__( self, matchString, identChars=DEFAULT_KEYWORD_CHARS, caseless=False ):
        super(Keyword,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Keyword; use Empty() instead", 
                            SyntaxWarning, stacklevel=2)
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = _str2dict(identChars)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.caseless:
            if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
                 (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) and
                 (loc == 0 or instring[loc-1].upper() not in self.identChars) ):
                return loc+self.matchLen, self.match
        else:
            if (instring[loc] == self.firstMatchChar and
                (self.matchLen==1 or instring.startswith(self.match,loc)) and
                (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen] not in self.identChars) and
                (loc == 0 or instring[loc-1] not in self.identChars) ):
                return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc
        
    def copy(self):
        c = super(Keyword,self).copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c
        
    def setDefaultKeywordChars( chars ):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars
    setDefaultKeywordChars = staticmethod(setDefaultKeywordChars)        


class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name
        self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() == self.match:
            return loc+self.matchLen, self.returnString
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class CaselessKeyword(Keyword):
    def __init__( self, matchString, identChars=Keyword.DEFAULT_KEYWORD_CHARS ):
        super(CaselessKeyword,self).__init__( matchString, identChars, caseless=True )

    def parseImpl( self, instring, loc, doActions=True ):
        if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
             (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Word(Token):
    """Token for matching words composed of allowed character sets.
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0 ):
        super(Word,self).__init__()
        self.initCharsOrig = initChars
        self.initChars = _str2dict(initChars)
        if bodyChars :
            self.bodyCharsOrig = bodyChars
            self.bodyChars = _str2dict(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = _str2dict(initChars)
            
        self.maxSpecified = max > 0

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = sys.maxint

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.myException.msg = self.errmsg
        self.mayIndexError = False
        
        if ' ' not in self.initCharsOrig+self.bodyCharsOrig and (min==1 and max==0 and exact==0):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _escapeRegexRangeChars(self.initCharsOrig)
            elif len(self.bodyCharsOrig) == 1:
                self.reString = "%s[%s]*" % \
                                      (re.escape(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            else:
                self.reString = "[%s][%s]*" % \
                                      (_escapeRegexRangeChars(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            try:
                self.re = re.compile( self.reString )
            except:
                self.re = None
        
    def parseImpl( self, instring, loc, doActions=True ):
        if self.re:
            result = self.re.match(instring,loc)
            if not result:
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
            
            loc = result.end()
            return loc,result.group()
        
        if not(instring[ loc ] in self.initChars):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, instrlen )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1
            
        throwException = False
        if loc - start < self.minLen:
            throwException = True
        if self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True

        if throwException:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass

            
        if self.strRepr is None:
            
            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s
            
            if ( self.initCharsOrig != self.bodyCharsOrig ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initCharsOrig), charsAsStr(self.bodyCharsOrig) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class Regex(Token):
    """Token for matching strings that match a given regular expression.
       Defined with string specifying the regular expression in a form recognized by the inbuilt Python re module.
    """
    def __init__( self, pattern, flags=0):
        """The parameters pattern and flags are passed to the re.compile() function as-is. See the Python re module for an explanation of the acceptable patterns and flags."""
        super(Regex,self).__init__()
        
        if len(pattern) == 0:
            warnings.warn("null string passed to Regex; use Empty() instead", 
                    SyntaxWarning, stacklevel=2)
    
        self.pattern = pattern
        self.flags = flags
        
        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except Exception,e:
            warnings.warn("invalid pattern (%s) passed to Regex" % pattern, 
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True
    
    def parseImpl( self, instring, loc, doActions=True ):
        result = self.re.match(instring,loc)
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        
        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d.keys():
                ret[k] = d[k]
        return loc,ret
    
    def __str__( self ):
        try:
            return super(Regex,self).__str__()
        except:
            pass
        
        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)
        
        return self.strRepr


class QuotedString(Token):
    """Token for matching strings that are delimited by quoting characters.
    """
    def __init__( self, quoteChar, escChar=None, escQuote=None, multiline=False, unquoteResults=True, endQuoteChar=None):
        """
           Defined with the following parameters:
           - quoteChar - string of one or more characters defining the quote delimiting string
           - escChar - character to escape quotes, typically backslash (default=None)
           - escQuote - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)
           - multiline - boolean indicating whether quotes can span multiple lines (default=False)
           - unquoteResults - boolean indicating whether the matched text should be unquoted (default=True)
           - endQuoteChar - string of one or more characters defining the end of the quote delimited string (default=None => same as quoteChar)
        """
        super(QuotedString,self).__init__()
        
        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if len(quoteChar) == 0:
            warnings.warn("quoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
            raise SyntaxError()
        
        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if len(endQuoteChar) == 0:
                warnings.warn("endQuoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
                raise SyntaxError()
        
        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults
        
        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r'%s([^%s%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        else:
            self.flags = 0
            self.pattern = r'%s([^%s\n\r%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                '|(' + ')|('.join(["%s[^%s]" % (re.escape(self.endQuoteChar[:i]),
                                               _escapeRegexRangeChars(self.endQuoteChar[i])) 
                                    for i in range(len(self.endQuoteChar)-1,0,-1)]) + ')'
                )
        if escQuote:
            self.pattern += (r'|(%s)' % re.escape(escQuote))
        if escChar:
            self.pattern += (r'|(%s.)' % re.escape(escChar))
            self.escCharReplacePattern = re.escape(self.escChar)+"(.)"
        self.pattern += (r')*%s' % re.escape(self.endQuoteChar))
        
        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except Exception,e:
            warnings.warn("invalid pattern (%s) passed to Regex" % self.pattern, 
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True
    
    def parseImpl( self, instring, loc, doActions=True ):
        result = instring[loc] == self.firstQuoteChar and self.re.match(instring,loc) or None
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        
        loc = result.end()
        ret = result.group()
        
        if self.unquoteResults:
            
            # strip off quotes
            ret = ret[self.quoteCharLen:-self.endQuoteCharLen]
                
            if isinstance(ret,basestring):
                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern,"\g<1>",ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret
    
    def __str__( self ):
        try:
            return super(QuotedString,self).__str__()
        except:
            pass
        
        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (self.quoteChar, self.endQuoteChar)
        
        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional 
       minimum, maximum, and/or exact length.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars
        
        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = sys.maxint

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact
        
        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )
        self.myException.msg = self.errmsg
        self.mayIndexError = False

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
            
        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars
        
        return self.strRepr

class White(Token):
    """Special matching class for matching whitespace.  Normally, whitespace is ignored
       by pyparsing grammars.  This class is included when some whitespace structures
       are significant.  Define with a string containing the whitespace characters to be
       matched; default is " \\t\\n".  Also takes optional min, max, and exact arguments,
       as defined for the Word class."""
    whiteStrs = {
        " " : "<SPC>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        }
    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super(White,self).__init__()
        self.matchWhite = ws
        self.whiteChars = "".join([c for c in self.whiteChars if c not in self.matchWhite])
        #~ self.leaveWhitespace()
        self.name = ("".join([White.whiteStrs[c] for c in self.matchWhite]))
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name
        self.myException.msg = self.errmsg

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = sys.maxint

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact
            
    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.matchWhite):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]


class PositionToken(Token):
    def __init__( self ):
        super(PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True

class GoToColumn(PositionToken):
    """Token to advance to a specific column of input text; useful for tabular report scraping."""
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self.skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException( instring, loc, "Text not in expected column", self )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, ret

class LineStart(PositionToken):
    """Matches if current position is at the beginning of a line within the parse string"""
    def __init__( self ):
        super(LineStart,self).__init__()
        self.whiteChars = " \t"
        self.errmsg = "Expected start of line"
        self.myException.msg = self.errmsg

    def preParse( self, instring, loc ):
        loc = super(LineStart,self).preParse(instring,loc)
        if instring[loc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or ( loc<len(instring) and instring[loc-1] == "\n" ) ): #col(loc, instring) != 1:
            #~ raise ParseException( instring, loc, "Expected start of line" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

class LineEnd(PositionToken):
    """Matches if current position is at the end of a line within the parse string"""
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.whiteChars = " \t"
        self.errmsg = "Expected end of line"
        self.myException.msg = self.errmsg
    
    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring):
            if instring[loc] == "\n":
                return loc+1, "\n"
            else:
                #~ raise ParseException( instring, loc, "Expected end of line" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        else:
            return loc, []

class StringStart(PositionToken):
    """Matches if current position is at the beginning of the parse string"""
    def __init__( self ):
        super(StringStart,self).__init__()
        self.errmsg = "Expected start of text"
        self.myException.msg = self.errmsg
    
    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                #~ raise ParseException( instring, loc, "Expected start of text" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class StringEnd(PositionToken):
    """Matches if current position is at the end of the parse string"""
    def __init__( self ):
        super(StringEnd,self).__init__()
        self.errmsg = "Expected end of text"
        self.myException.msg = self.errmsg
    
    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            #~ raise ParseException( instring, loc, "Expected end of text" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, list ):
            self.exprs = exprs
        elif isinstance( exprs, basestring ):
            self.exprs = [ Literal( exprs ) ]
        else:
            self.exprs = [ exprs ]

    def __getitem__( self, i ):
        return self.exprs[i]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        """Extends leaveWhitespace defined in base class, and also invokes leaveWhitespace on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [ copy.copy(e) for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )
        return self

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass
            
        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And( And( And( a,b), c), d) to And( a,b,c,d )
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if ( len(self.exprs) == 2 ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = other.exprs[:] + [ self.exprs[1] ]
                self.strRepr = None

            other = self.exprs[-1]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None

        return self

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ParseExpression,self).setResultsName(name,listAllMatches)
        #~ ret.saveAsList = True
        return ret
    
    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )

    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        if self.parseAction and doActions:
            return self._parseNoCache( instring, loc, doActions, callPreParse )
        return super(ParseExpression,self)._parseCache( instring, loc, doActions, callPreParse )

class And(ParseExpression):
    """Requires all given ParseExpressions to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the '+' operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.skipWhitespace = exprs[0].skipWhitespace
        self.whiteChars = exprs[0].whiteChars

    def parseImpl( self, instring, loc, doActions=True ):
        loc, resultlist = self.exprs[0]._parse( instring, loc, doActions )
        for e in self.exprs[1:]:
            loc, exprtokens = e._parse( instring, loc, doActions )
            if exprtokens or exprtokens.keys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #And( [ self, other ] )
        
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break
                
    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " ".join( [ _ustr(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr
    

class Or(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the '^' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in self.exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break
    
    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxMatchLoc = -1
        for e in self.exprs:
            try:
                loc2 = e.tryParse( instring, loc )
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError, err:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)
            else:
                if loc2 > maxMatchLoc:
                    maxMatchLoc = loc2
                    maxMatchExp = e
        
        if maxMatchLoc < 0:
            if self.exprs:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

        return maxMatchExp._parse( instring, loc, doActions )

    def __ixor__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join( [ _ustr(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr
    
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the '|' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        if exprs:
            self.mayReturnEmpty = False
            for e in self.exprs:
                if e.mayReturnEmpty:
                    self.mayReturnEmpty = True
                    break
        else:
            self.mayReturnEmpty = True
    
    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        for e in self.exprs:
            try:
                ret = e._parse( instring, loc, doActions )
                return ret
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError, err:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        else:
            if self.exprs:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

    def __ior__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " | ".join( [ _ustr(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr
    
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )

class Each(ParseExpression):
    """Requires all given ParseExpressions to be found, but in any order.
       Expressions may be separated by whitespace.
       May be constructed using the '&' operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(Each,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.skipWhitespace = True
        self.optionals = [ e.expr for e in exprs if isinstance(e,Optional) ]
        self.multioptionals = [ e.expr for e in exprs if isinstance(e,ZeroOrMore) ]
        self.multirequired = [ e.expr for e in exprs if isinstance(e,OneOrMore) ]
        self.required = [ e for e in exprs if not isinstance(e,(Optional,ZeroOrMore,OneOrMore)) ]
        self.required += self.multirequired

    def parseImpl( self, instring, loc, doActions=True ):
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt  = self.optionals[:]
        matchOrder = []

        keepMatching = True
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed = []
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse( instring, tmpLoc )
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(e)
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False
        
        if tmpReqd:
            missing = ", ".join( [ str(e) for e in tmpReqd ] )
            raise ParseException(instring,loc,"Missing one or more required elements (%s)" % missing )

        resultlist = []
        for e in matchOrder:
            loc,results = e._parse(instring,loc,doActions)
            resultlist.append(results)
            
        finalResults = ParseResults([])
        for r in resultlist:
            dups = {}
            for k in r.keys():
                if k in finalResults.keys():
                    tmp = ParseResults(finalResults[k])
                    tmp += ParseResults(r[k])
                    dups[k] = tmp
            finalResults += ParseResults(r)
            for k,v in dups.items():
                finalResults[k] = v
        return loc, finalResults

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + " & ".join( [ _ustr(e) for e in self.exprs ] ) + "}"
        
        return self.strRepr
    
    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, basestring ):
            expr = Literal(expr)
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.skipWhitespace = expr.skipWhitespace
            self.whiteChars = expr.whiteChars
            self.saveAsList = expr.saveAsList
    
    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr is not None:
            return self.expr._parse( instring, loc, doActions )
        else:
            raise ParseException("",loc,self.errmsg,self)
            
    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = copy.copy(self.expr)
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                if self.expr is not None:
                    self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            if self.expr is not None:
                self.expr.ignore( self.ignoreExprs[-1] )
        return self

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        if self.expr is not None:
            self.expr.checkRecursion( subRecCheckList )
        
    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion( [] )
    
    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass
            
        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.expr) )
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.  FollowedBy
    does *not* advance the parsing position within the input string, it only 
    verifies that the specified parse expression matches at the current 
    position.  FollowedBy always returns a null token list."""
    def __init__( self, expr ):
        super(FollowedBy,self).__init__(expr)
        self.mayReturnEmpty = True
        
    def parseImpl( self, instring, loc, doActions=True ):
        self.expr.tryParse( instring, loc )
        return loc, []


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.  NotAny
    does *not* advance the parsing position within the input string, it only 
    verifies that the specified parse expression does *not* match at the current 
    position.  Also, NotAny does *not* skip over leading whitespace. NotAny 
    always returns a null token list.  May be constructed using the '~' operator."""
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unexpected token, "+_ustr(self.expr)
        self.myException = ParseException("",0,self.errmsg,self)
        
    def parseImpl( self, instring, loc, doActions=True ):
        try:
            self.expr.tryParse( instring, loc )
        except (ParseException,IndexError):
            pass
        else:
            #~ raise ParseException(instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "~{" + _ustr(self.expr) + "}"
        
        return self.strRepr


class ZeroOrMore(ParseElementEnhance):
    """Optional repetition of zero or more of the given expression."""
    def __init__( self, expr ):
        super(ZeroOrMore,self).__init__(expr)
        self.mayReturnEmpty = True
    
    def parseImpl( self, instring, loc, doActions=True ):
        tokens = []
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions )
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    loc = self.skipIgnorables( instring, loc )
                loc, tmptokens = self.expr._parse( instring, loc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass
        except Exception,e:
            print "####",e

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]..."
        
        return self.strRepr
    
    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ZeroOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret
    

class OneOrMore(ParseElementEnhance):
    """Repetition of one or more of the given expression."""
    def parseImpl( self, instring, loc, doActions=True ):
        # must be at least one
        loc, tokens = self.expr._parse( instring, loc, doActions )
        try:
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    loc = self.skipIgnorables( instring, loc )
                loc, tmptokens = self.expr._parse( instring, loc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "{" + _ustr(self.expr) + "}..."
        
        return self.strRepr
    
    def setResultsName( self, name, listAllMatches=False ):
        ret = super(OneOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret

class _NullToken(object):
    def __bool__(self):
        return False
    def __str__(self):
        return ""

_optionalNotMatched = _NullToken()
class Optional(ParseElementEnhance):
    """Optional matching of the given expression.
       A default return string can also be specified, if the optional expression
       is not found.
    """
    def __init__( self, exprs, default=_optionalNotMatched ):
        super(Optional,self).__init__( exprs, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions )
        except (ParseException,IndexError):
            if self.defaultValue is not _optionalNotMatched:
                tokens = [ self.defaultValue ]
            else:
                tokens = []

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name
            
        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]"
        
        return self.strRepr


class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched expression is found.
       If include is set to true, the matched expression is also consumed.  The ignore
       argument is used to define grammars (typically quoted strings and comments) that 
       might contain false matches.
    """
    def __init__( self, other, include=False, ignore=None ):
        super( SkipTo, self ).__init__( other )
        if ignore is not None:
            self.expr = copy.copy( self.expr )
            self.expr.ignore(ignore)
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.errmsg = "No match found for "+_ustr(self.expr)
        self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        startLoc = loc
        instrlen = len(instring)
        expr = self.expr
        while loc < instrlen:
            try:
                loc = expr.skipIgnorables( instring, loc )
                expr._parse( instring, loc, doActions=False, callPreParse=False )
                if self.includeMatch:
                    skipText = instring[startLoc:loc]
                    loc,mat = expr._parse(instring,loc)
                    if mat:
                        return loc, [ skipText, mat ]
                    else:
                        return loc, [ skipText ]
                else:
                    return loc, [ instring[startLoc:loc] ]
            except (ParseException,IndexError):
                loc += 1
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the Forward variable using the '<<' operator.
       
       Note: take care when assigning to Forward to not overlook precedence of operators.
       Specifically, '|' has a lower precedence than '<<', so that::
          fwdExpr << a | b | c
       will actually be evaluated as::
          (fwdExpr << a) | b | c
       thereby leaving b and c out as parseable alternatives.  It is recommended that you
       explicitly group the values inserted into the Forward::
          fwdExpr << (a | b | c)
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        self.expr = other
        self.mayReturnEmpty = other.mayReturnEmpty
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None: 
                self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            if self.expr is not None: 
                self.expr.validate(tmp)
        self.checkRecursion([])        
        
    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        self.__class__ = _ForwardNoRecurse
        try:
            if self.expr is not None: 
                retString = _ustr(self.expr)
            else:
                retString = "None"
        finally:
            self.__class__ = Forward
        return "Forward: "+retString

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."
        
class TokenConverter(ParseElementEnhance):
    """Abstract subclass of ParseExpression, for converting parsed results."""
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )
        self.saveAsList = False


class Upcase(TokenConverter):
    """Converter to upper case all matching tokens."""
    def __init__(self, *args):
        super(Upcase,self).__init__(*args)
        warnings.warn("Upcase class is deprecated, use upcaseTokens parse action instead", 
                       DeprecationWarning,stacklevel=2)
    
    def postParse( self, instring, loc, tokenlist ):
        return map( string.upper, tokenlist )


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying 'adjacent=False' in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString

    def ignore( self, other ):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super( Combine, self).ignore( other )
        return self

    def postParse( self, instring, loc, tokenlist ):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults([ "".join(tokenlist._asStringList(self.joinString)) ], modal=self.modalResults)

        if self.resultsName and len(retToks.keys())>0:
            return [ retToks ]
        else:
            return retToks

class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for returning tokens of ZeroOrMore and OneOrMore expressions."""
    def __init__( self, expr ):
        super(Group,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        return [ tokenlist ]
        
class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, exprs ):
        super(Dict,self).__init__( exprs )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        for i,tok in enumerate(tokenlist):
            ikey = _ustr(tok[0]).strip()
            if len(tok)==1:
                tokenlist[ikey] = ("",i)
            elif len(tok)==2 and not isinstance(tok[1],ParseResults):
                tokenlist[ikey] = (tok[1],i)
            else:
                dictvalue = tok.copy() #ParseResults(i)
                del dictvalue[0]
                if len(dictvalue)!= 1 or (isinstance(dictvalue,ParseResults) and dictvalue.keys()):
                    tokenlist[ikey] = (dictvalue,i)
                else:
                    tokenlist[ikey] = (dictvalue[0],i)

        if self.resultsName:
            return [ tokenlist ]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression."""
    def postParse( self, instring, loc, tokenlist ):
        return []
    
    def suppress( self ):
        return self

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and 
       comments, but this can be overridden by passing 'combine=True' in the constructor.
       If combine is set to True, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    if combine:
        return Combine( expr + ZeroOrMore( delim + expr ) ).setName(_ustr(expr)+_ustr(delim)+"...")
    else:
        return ( expr + ZeroOrMore( Suppress( delim ) + expr ) ).setName(_ustr(expr)+_ustr(delim)+"...")

def countedArray( expr ):
    """Helper to define a counted list of expressions.
       This helper defines a pattern of the form::
           integer expr expr expr...
       where the leading integer tells how many expr expressions follow.
       The matched tokens returns the array of expr tokens as a list - the leading count token is suppressed.
    """
    arrayExpr = Forward()
    def countFieldParseAction(s,l,t):
        n = int(t[0])
        arrayExpr << (n and Group(And([expr]*n)) or Group(empty))
        return []
    return ( Word(nums).setParseAction(countFieldParseAction) + arrayExpr )
    
def _escapeRegexRangeChars(s):
    #~  escape these chars: ^-]
    for c in r"\^-]":
        s = s.replace(c,"\\"+c)
    s = s.replace("\n",r"\n")
    s = s.replace("\t",r"\t")
    return _ustr(s)
    
def oneOf( strs, caseless=False, useRegex=True ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do 
       longest-first testing when there is a conflict, regardless of the input order, 
       but returns a MatchFirst for best performance.  
       
       Parameters:
        - strs - a string of space-delimited literals, or a list of string literals
        - caseless - (default=False) - treat all literals as caseless
        - useRegex - (default=True) - as an optimization, will generate a Regex
          object; otherwise, will generate a MatchFirst object (if caseless=True, or
          if creating a Regex raises an exception)
    """
    if caseless:
        isequal = ( lambda a,b: a.upper() == b.upper() )
        masks = ( lambda a,b: b.upper().startswith(a.upper()) )
        parseElementClass = CaselessLiteral
    else:
        isequal = ( lambda a,b: a == b )
        masks = ( lambda a,b: b.startswith(a) )
        parseElementClass = Literal
    
    if isinstance(strs,(list,tuple)):
        symbols = strs[:]
    elif isinstance(strs,basestring):
        symbols = strs.split()
    else:
        warnings.warn("Invalid argument to oneOf, expected string or list",
                SyntaxWarning, stacklevel=2)
        
    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( isequal(other, cur) ):
                del symbols[i+j+1]
                break
            elif ( masks(cur, other) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1

    if not caseless and useRegex:
        #~ print strs,"->", "|".join( [ _escapeRegexChars(sym) for sym in symbols] )
        try:
            if len(symbols)==len("".join(symbols)):
                return Regex( "[%s]" % "".join( [ _escapeRegexRangeChars(sym) for sym in symbols] ) )
            else:
                return Regex( "|".join( [ re.escape(sym) for sym in symbols] ) )
        except:
            warnings.warn("Exception creating Regex for oneOf, building MatchFirst",
                    SyntaxWarning, stacklevel=2)


    # last resort, just use MatchFirst
    return MatchFirst( [ parseElementClass(sym) for sym in symbols ] )

def dictOf( key, value ):
    """Helper to easily and clearly define a dictionary by specifying the respective patterns
       for the key and value.  Takes care of defining the Dict, ZeroOrMore, and Group tokens
       in the proper order.  The key pattern can include delimiting markers or punctuation,
       as long as they are suppressed, thereby leaving the significant key text.  The value
       pattern can include named results, so that the Dict results can include named token 
       fields.
    """
    return Dict( ZeroOrMore( Group ( key + value ) ) )

_bslash = "\\"
printables = "".join( [ c for c in string.printable if c not in string.whitespace ] )

# convenience constants for positional expressions
empty       = Empty().setName("empty")
lineStart   = LineStart().setName("lineStart")
lineEnd     = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd   = StringEnd().setName("stringEnd")

_escapedPunc = Word( _bslash, r"\[]-*.$+^?()~ ", exact=2 ).setParseAction(lambda s,l,t:t[0][1])
_printables_less_backslash = "".join([ c for c in printables if c not in  r"\]" ])
_escapedHexChar = Combine( Suppress(_bslash + "0x") + Word(hexnums) ).setParseAction(lambda s,l,t:unichr(int(t[0],16)))
_escapedOctChar = Combine( Suppress(_bslash) + Word("0","01234567") ).setParseAction(lambda s,l,t:unichr(int(t[0],8)))
_singleChar = _escapedPunc | _escapedHexChar | _escapedOctChar | Word(_printables_less_backslash,exact=1)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = "[" + Optional("^").setResultsName("negate") + Group( OneOrMore( _charRange | _singleChar ) ).setResultsName("body") + "]"

_expanded = lambda p: (isinstance(p,ParseResults) and ''.join([ unichr(c) for c in range(ord(p[0]),ord(p[1])+1) ]) or p)
        
def srange(s):
    r"""Helper to easily define string ranges for use in Word construction.  Borrows
       syntax from regexp '[]' string range definitions::
          srange("[0-9]")   -> "0123456789"
          srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
          srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"
       The input string must be enclosed in []'s, and the returned string is the expanded 
       character set joined into a single string.
       The values enclosed in the []'s may be::
          a single character
          an escaped character with a leading backslash (such as \- or \])
          an escaped hex character with a leading '\0x' (\0x21, which is a '!' character)
          an escaped octal character with a leading '\0' (\041, which is a '!' character)
          a range of any of the above, separated by a dash ('a-z', etc.)
          any combination of the above ('aeiouy', 'a-zA-Z0-9_$', etc.)
    """
    try:
        return "".join([_expanded(part) for part in _reBracketExpr.parseString(s).body])
    except:
        return ""

def replaceWith(replStr):
    """Helper method for common parse actions that simply return a literal value.  Especially 
       useful when used with transformString().
    """
    def _replFunc(*args):
        return [replStr]
    return _replFunc

def removeQuotes(s,l,t):
    """Helper parse action for removing quotation marks from parsed quoted strings.
       To use, add this parse action to quoted string using::
         quotedString.setParseAction( removeQuotes )
    """
    return t[0][1:-1]

def upcaseTokens(s,l,t):
    """Helper parse action to convert tokens to upper case."""
    return map( str.upper, t )

def downcaseTokens(s,l,t):
    """Helper parse action to convert tokens to lower case."""
    return map( str.lower, t )

def _makeTags(tagStr, xml):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    tagAttrName = Word(alphanums)
    if (xml):
        tagAttrValue = dblQuotedString.copy().setParseAction( removeQuotes )
        openTag = Suppress("<") + Keyword(tagStr) + \
                Dict(ZeroOrMore(Group( tagAttrName + Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    else:
        printablesLessRAbrack = "".join( [ c for c in printables if c not in ">" ] )
        tagAttrValue = quotedString.copy().setParseAction( removeQuotes ) | Word(printablesLessRAbrack)
        openTag = Suppress("<") + Keyword(tagStr,caseless=True) + \
                Dict(ZeroOrMore(Group( tagAttrName.setParseAction(downcaseTokens) + \
                Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    closeTag = Combine("</" + Keyword(tagStr,caseless=not xml) + ">")
    
    openTag = openTag.setResultsName("start"+"".join(tagStr.replace(":"," ").title().split())).setName("<%s>" % tagStr)
    closeTag = closeTag.setResultsName("end"+"".join(tagStr.replace(":"," ").title().split())).setName("</%s>" % tagStr)
    
    return openTag, closeTag

def makeHTMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for HTML, given a tag name"""
    return _makeTags( tagStr, False )

def makeXMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for XML, given a tag name"""
    return _makeTags( tagStr, True )

alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xfe]")

_escapedChar = Regex(r"\\.")
dblQuotedString = Regex(r'"([^"\n\r\\]|("")|(\\.))*"').setName("string enclosed in double quotes")
sglQuotedString = Regex(r"'([^'\n\r\\]|('')|(\\.))*'").setName("string enclosed in single quotes")
quotedString = Regex(r'''("([^"\n\r\\]|("")|(\\.))*")|('([^'\n\r\\]|('')|(\\.))*')''').setName("quotedString using single or double quotes")

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Regex(r"\/\*[\s\S]*?\*\/").setName("C style comment")
htmlComment = Regex(r"<!--[\s\S]*?-->")
restOfLine = Regex(r".*").leaveWhitespace()
dblSlashComment = Regex(r"\/\/.*").setName("// comment")
cppStyleComment = Regex(r"(\/\*[\s\S]*?\*\/)|(\/\/.*)").setName("C++ style comment")
javaStyleComment = cppStyleComment
pythonStyleComment = Regex(r"#.*").setName("Python style comment")
_noncomma = "".join( [ c for c in printables if c != "," ] )
_commasepitem = Combine(OneOrMore(Word(_noncomma) + 
                                  Optional( Word(" \t") + 
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString | _commasepitem, default="") ).setName("commaSeparatedList")


if __name__ == "__main__":

    def test( teststring ):
        print teststring,"->",
        try:
            tokens = simpleSQL.parseString( teststring )
            tokenlist = tokens.asList()
            print tokenlist
            print "tokens = ",        tokens
            print "tokens.columns =", tokens.columns
            print "tokens.tables =",  tokens.tables
            print tokens.asXML("SQL",True)
        except ParseException, err:
            print err.line
            print " "*(err.column-1) + "^"
            print err
        print

    selectToken    = CaselessLiteral( "select" )
    fromToken      = CaselessLiteral( "from" )

    ident          = Word( alphas, alphanums + "_$" )
    columnName     = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    columnNameList = Group( delimitedList( columnName ) )#.setName("columns")
    tableName      = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    tableNameList  = Group( delimitedList( tableName ) )#.setName("tables")
    simpleSQL      = ( selectToken + \
                     ( '*' | columnNameList ).setResultsName( "columns" ) + \
                     fromToken + \
                     tableNameList.setResultsName( "tables" ) )
    
    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select AA,BB,CC from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select ^^^ frox Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )

########NEW FILE########
__FILENAME__ = httplib2_intercept

"""intercept HTTP connections that use httplib2

(see wsgi_intercept/__init__.py for examples)

"""

import httplib2
import wsgi_intercept
from httplib2 import HTTPConnectionWithTimeout, HTTPSConnectionWithTimeout
import sys

InterceptorMixin = wsgi_intercept.WSGI_HTTPConnection

# might make more sense as a decorator

def connect(self):
    """
    Override the connect() function to intercept calls to certain
    host/ports.
    """
    if wsgi_intercept.debuglevel:
        sys.stderr.write('connect: %s, %s\n' % (self.host, self.port,))

    (app, script_name) = self.get_app(self.host, self.port)
    if app:
        if wsgi_intercept.debuglevel:
            sys.stderr.write('INTERCEPTING call to %s:%s\n' % \
                             (self.host, self.port,))
        self.sock = wsgi_intercept.wsgi_fake_socket(app,
                                                    self.host, self.port,
                                                    script_name)
    else:
        self._connect()

class HTTP_WSGIInterceptorWithTimeout(HTTPConnectionWithTimeout, InterceptorMixin):
    _connect = httplib2.HTTPConnectionWithTimeout.connect
    connect = connect

class HTTPS_WSGIInterceptorWithTimeout(HTTPSConnectionWithTimeout, InterceptorMixin):
    _connect = httplib2.HTTPSConnectionWithTimeout.connect
    connect = connect

def install():
    httplib2.HTTPConnectionWithTimeout = HTTP_WSGIInterceptorWithTimeout
    httplib2.HTTPSConnectionWithTimeout = HTTPS_WSGIInterceptorWithTimeout

def uninstall():
    httplib2.HTTPConnectionWithTimeout = HTTPConnectionWithTimeout
    httplib2.HTTPSConnectionWithTimeout = HTTPSConnectionWithTimeout

########NEW FILE########
__FILENAME__ = wsgi_browser
"""
A mechanize browser that redirects specified HTTP connections to a WSGI
object.
"""

from httplib import HTTP
from mechanize import Browser as MechanizeBrowser
from wsgi_intercept.urllib2_intercept import install_opener, uninstall_opener
try:
    from mechanize import HTTPHandler
except ImportError:
    # pre mechanize 0.1.0 it was a separate package
    # (this will break if it is combined with a newer mechanize)
    from ClientCookie import HTTPHandler

import sys, os.path
from wsgi_intercept.urllib2_intercept import WSGI_HTTPHandler, WSGI_HTTPSHandler

class Browser(MechanizeBrowser):
    """
    A version of the mechanize browser class that
    installs the WSGI intercept handler
    """
    handler_classes = MechanizeBrowser.handler_classes.copy()
    handler_classes['http'] = WSGI_HTTPHandler
    handler_classes['https'] = WSGI_HTTPSHandler
    def __init__(self, *args, **kwargs):
        # install WSGI intercept handler.
        install(self)
        MechanizeBrowser.__init__(self, *args, **kwargs)

def install(browser):
    install_opener()
########NEW FILE########
__FILENAME__ = wsgi_browser
"""
A mechanoid browser that redirects specified HTTP connections to a WSGI
object.
"""

from httplib import HTTP
import httplib
from mechanoid import Browser as MechanoidBrowser
from mechanoid.useragent.http_handlers.HTTPHandler import HTTPHandler
from mechanoid.useragent.http_handlers.HTTPSHandler import HTTPSHandler

import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from wsgi_intercept import WSGI_HTTPConnection

class WSGI_HTTP(HTTP):
    _connection_class = WSGI_HTTPConnection

class WSGI_HTTPHandler(HTTPHandler):
    def http_open(self, req):
        return self.do_open(WSGI_HTTP, req)

if hasattr(httplib, 'HTTPS'):
    class WSGI_HTTPSHandler(HTTPSHandler):
        def https_open(self, req):
            return self.do_open(WSGI_HTTP, req)
else:
    WSGI_HTTPSHandler = None

class Browser(MechanoidBrowser):
    def __init__(self, *args, **kwargs):
        self.handler_classes['http'] = WSGI_HTTPHandler
        if WSGI_HTTPSHandler is not None:
            self.handler_classes['https'] = WSGI_HTTPSHandler
        MechanoidBrowser.__init__(self, *args, **kwargs)

########NEW FILE########
__FILENAME__ = mock_http
#
# mock_http.py
#
# Written by Marc Hedlund <marc@precipice.org>.
# Released under the same terms as wsgi_intercept.
#

"""
This is a dirt-simple example of using wsgi_intercept to set up a mock
object HTTP server for testing HTTP clients.
"""

import sys
sys.path.insert(0, 'urllib2')

import unittest
import urllib2
import wsgi_intercept
from wsgi_intercept import urllib2_intercept as wsgi_urllib2

test_page = """
    <html>
    <head>
        <title>Mock HTTP Server</title>
    </head>
    <body>
        <h1>Mock HTTP Server</h1>
        <p>You have successfully reached the Mock HTTP Server.</p>
    </body>
    </html>
"""

class MockHttpServer:
    def __init__(self, port=8000):
        """Initializes the mock server on localhost port 8000.  Use
        urllib2.urlopen('http://localhost:8000') to reach the test
        server.  The constructor takes a 'port=<int>' argument if you
        want the server to listen on a different port."""
        wsgi_intercept.add_wsgi_intercept('localhost', port, self.interceptor)
        wsgi_urllib2.install_opener()
    
    def handleResponse(self, environment, start_response):
        """Processes a request to the mock server, and returns a
        String object containing the response document.  The mock server
        will send this to the client code, which can read it as a
        StringIO document.  This example always returns a successful
        response to any request; a more intricate mock server could
        examine the request environment to determine what sort of
        response to give."""
        status  = "200 OK"
        headers = [('Content-Type', 'text/html')]
        start_response(status, headers)
        return test_page
    
    def interceptor(self):
        """Sets this class as the handler for intercepted urllib2
        requests."""
        return self.handleResponse

class MockHttpServerTest(unittest.TestCase):
    """Demonstrates the use of the MockHttpServer from client code."""
    def setUp(self):
        self.server = MockHttpServer()
        
    def test_simple_get(self):
        result = urllib2.urlopen('http://localhost:8000/')
        self.assertEqual(result.read(), test_page)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = build_docs

from distutils.cmd import Command
from distutils.errors import *
from distutils import log
from docutils import statemachine
from docutils.parsers.rst import directives
from docutils.core import (
    publish_file, publish_string, publish_doctree, publish_from_doctree)
from docutils.parsers import rst
from docutils.nodes import SparseNodeVisitor
from docutils.readers.standalone import Reader
from docutils.writers.html4css1 import HTMLTranslator, Writer
from docutils import nodes
import compiler
from compiler import visitor
from pprint import pprint
import pydoc, os, shutil

class DocInspector(object):
    """expose docstrings for objects by parsing the abstract syntax tree.
    
    splitdocfor() is the interface around this
    """
    def __init__(self, filename):
        self.filename = filename
        self.top_level_doc = None
        self.map = {}
    
    def __getitem__(self, path):
        return self.map[path]
    
    def __contains__(self, path):
        return path in self.map
    
    def makepath(self, node):
        path = [n.name for n in node.lineage] + [node.name]
        # skip first name in lineage because that's the file ...
        return ".".join(path[1:])
        
    def default(self, node):
        for child in node.getChildNodes():
            self.visit(child, node.lineage + [node])
            
    def visitModule(self, node):
        self.top_level_doc = node.doc
        node.name = self.filename
        node.lineage = []
        # descend into classes and functions
        self.default(node)
        
    def visitClass(self, node, lineage=[]):
        node.lineage = lineage
        self.map[self.makepath(node)] = node.doc
        self.default(node) 
        
    def visitFunction(self, node, lineage=[]):
        node.lineage = lineage
        self.map[self.makepath(node)] = node.doc
        self.default(node) 

def splitdocfor(path):
    """split the docstring for a path
    
    valid paths are::
        
        ./path/to/module.py
        ./path/to/module.py:SomeClass.method
    
    returns (description, long_description) from the docstring for path 
    or (None, None) if there isn't a docstring.
    
    Example::
    
        >>> splitdocfor("./wsgi_intercept/__init__.py")[0]
        'installs a WSGI application in place of a real URI for testing.'
        >>> splitdocfor("./wsgi_intercept/__init__.py:WSGI_HTTPConnection.get_app")[0]
        'Return the app object for the given (host, port).'
        >>> 
        
    """
    if ":" in path:
        filename, objpath = path.split(':')
    else:
        filename, objpath = path, None
    inspector = DocInspector(filename)
    visitor.walk(compiler.parseFile(filename), inspector)
    if objpath is None:
        if inspector.top_level_doc is None:
            return None, None
        return pydoc.splitdoc(inspector.top_level_doc)
    else:
        if inspector[objpath] is None:
            return None, None
        return pydoc.splitdoc(inspector[objpath])

def include_docstring(  
        name, arguments, options, content, lineno,
        content_offset, block_text, state, state_machine):
    """include reStructuredText from a docstring.  use the directive like:
        
        | .. include_docstring:: path/to/module.py
        | .. include_docstring:: path/to/module.py:SomeClass
        | .. include_docstring:: path/to/module.py:SomeClass.method
    
    """
    rawpath = arguments[0]
    summary, body = splitdocfor(rawpath)
    # nabbed from docutils.parsers.rst.directives.misc.include
    include_lines = statemachine.string2lines(body, convert_whitespace=1)
    state_machine.insert_input(include_lines, None)
    return []
    # return [publish_doctree(body)]

include_docstring.arguments = (1, 0, 0)
include_docstring.options = {}
include_docstring.content = 0

directives.register_directive('include_docstring', include_docstring)

class build_docs(Command):
    description = "build documentation for wsgi_intercept"
    user_options = [
        # ('optname=', None, ""),
    ]
    def initialize_options(self):
        pass
        
    def finalize_options(self):
        pass
        
    def run(self):
        """build end-user documentation."""
        if not os.path.exists('./build'):
            os.mkdir('./build')
            log.info("created build dir")
        if os.path.exists('./build/docs'):
            shutil.rmtree('./build/docs')
        os.mkdir("./build/docs")
        body = publish_file(open("./docs/index.rst", 'r'),
                    destination=open("./build/docs/index.html", 'w'),
                    writer_name='html',
                    # settings_overrides={'halt_level':2,
                    #                     'report_level':5}
                    )
        log.info("published docs to: ./build/docs/index.html")
        
########NEW FILE########
__FILENAME__ = publish_docs

import re, pydoc
from distutils.cmd import Command
from distutils.errors import *
from distutils import log
from docutils.core import publish_string, publish_parts
from docutils import nodes
from docutils.nodes import SparseNodeVisitor
from docutils.writers import Writer
import wsgi_intercept
from mechanize import Browser
wiki_word_re = re.compile(r'^[A-Z][a-z]+(?:[A-Z][a-z]+)+')
    
class WikiWriter(Writer):
    def translate(self):
        visitor = WikiVisitor(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()
        
class WikiVisitor(SparseNodeVisitor):
    """visits RST nodes and transforms into Moin Moin wiki syntax.
    
    swiped from the nose project, originally written by Jason Pellerin.
    """
    def __init__(self, document):
        SparseNodeVisitor.__init__(self, document)
        self.list_depth = 0
        self.list_item_prefix = None
        self.indent = self.old_indent = ''
        self.output = []
        self.preformat = False
        self.section_level = 0
        
    def astext(self):
        return ''.join(self.output)

    def visit_Text(self, node):
        #print "Text", node
        data = node.astext()
        if not self.preformat:
            data = data.lstrip('\n\r')
            data = data.replace('\r', '')
            data = data.replace('\n', ' ')
        self.output.append(data)
    
    def visit_bullet_list(self, node):
        self.list_depth += 1
        self.list_item_prefix = (' ' * self.list_depth) + '* '

    def depart_bullet_list(self, node):
        self.list_depth -= 1
        if self.list_depth == 0:
            self.list_item_prefix = None
        else:
            self.list_item_prefix = (' ' * self.list_depth) + '* '
        self.output.append('\n\n')
                           
    def visit_list_item(self, node):
        self.old_indent = self.indent
        self.indent = self.list_item_prefix

    def depart_list_item(self, node):
        self.indent = self.old_indent
        
    def visit_literal_block(self, node):
        self.output.extend(['{{{', '\n'])
        self.preformat = True

    def depart_literal_block(self, node):
        self.output.extend(['\n', '}}}', '\n\n'])
        self.preformat = False

    def visit_doctest_block(self, node):
        self.output.extend(['{{{', '\n'])
        self.preformat = True

    def depart_doctest_block(self, node):
        self.output.extend(['\n', '}}}', '\n\n'])
        self.preformat = False
        
    def visit_paragraph(self, node):
        self.output.append(self.indent)
        
    def depart_paragraph(self, node):
        self.output.append('\n')
        if not isinstance(node.parent, nodes.list_item):
            self.output.append('\n')
        if self.indent == self.list_item_prefix:
            # we're in a sub paragraph of a list item
            self.indent = ' ' * self.list_depth
        
    def visit_reference(self, node):
        if node.has_key('refuri'):
            href = node['refuri']
        elif node.has_key('refid'):
            href = '#' + node['refid']
        else:
            href = None
        self.output.append('[' + href + ' ')

    def depart_reference(self, node):
        self.output.append(']')
    
    def _find_header_level(self, node):
        if isinstance(node.parent, nodes.topic):
            h_level = 2 # ??
        elif isinstance(node.parent, nodes.document):
            h_level = 1
        else:
            assert isinstance(node.parent, nodes.section), (
                "unexpected parent: %s" % node.parent.__class__)
            h_level = self.section_level
        return h_level
    
    def _depart_header_node(self, node):
        h_level = self._find_header_level(node)
        self.output.append(' %s\n\n' % ('='*h_level))
        self.list_depth = 0
        self.indent = ''
    
    def _visit_header_node(self, node):
        h_level = self._find_header_level(node)
        self.output.append('%s ' % ('='*h_level))

    def visit_subtitle(self, node):
        self._visit_header_node(node)

    def depart_subtitle(self, node):
        self._depart_header_node(node)
        
    def visit_title(self, node):
        self._visit_header_node(node)

    def depart_title(self, node):
        self._depart_header_node(node)
        
    def visit_title_reference(self, node):
        self.output.append("`")

    def depart_title_reference(self, node):
        self.output.append("`")

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    def visit_emphasis(self, node):
        self.output.append('*')

    def depart_emphasis(self, node):
        self.output.append('*')
        
    def visit_literal(self, node):
        self.output.append('`')
        
    def depart_literal(self, node):
        self.output.append('`')
        
class publish_docs(Command):
    description = "publish documentation to front page of Google Code project"
    user_options = [
        ('google-user=', None, "Google Code username"),
        ('google-password=', None, "Google Code password"),
    ]
    def initialize_options(self):
        self.google_user = None
        self.google_password = None
    def finalize_options(self):
        if self.google_user is None and self.google_password is None:
            raise DistutilsOptionError("--google-user and --google-password are required")
    def run(self):        
        summary, doc = pydoc.splitdoc(wsgi_intercept.__doc__)
        wikidoc = publish_string(doc, writer=WikiWriter())
        print wikidoc
        
        ## Google html is so broken that this isn't working :/
        
        # br = Browser()
        # br.open('http://code.google.com/p/wsgi-intercept/admin')
        # url = br.geturl()
        # assert url.startswith('https://www.google.com/accounts/Login'), (
        #     "unexpected URL: %s" % url)
        # log.info("logging in to Google Code...")
        # forms = [f for f in br.forms()]
        # assert len(forms)==1, "unexpected forms: %s for %s" % (forms, br.geturl())
        # br.select_form(nr=0)
        # br['Email'] = self.google_user
        # br['Passwd'] = self.google_password
        # admin = br.submit()
        # url = admin.geturl()
        # assert url=='http://code.google.com/p/wsgi-intercept/admin', (
        #     "unexpected URL: %s" % url) 
        # br.select_form(nr=0)
        # br['projectdescription'] = wikidoc
        # br.submit()
        # print br.geturl()
        

########NEW FILE########
__FILENAME__ = test_httplib2
#! /usr/bin/env python2.4
from wsgi_intercept import httplib2_intercept
from nose.tools import with_setup, raises, eq_
from socket import gaierror
import wsgi_intercept
from wsgi_intercept import test_wsgi_app
import httplib2

_saved_debuglevel = None


def install(port=80):
    _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    httplib2_intercept.install()
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', port, test_wsgi_app.create_fn)

def uninstall():
    wsgi_intercept.debuglevel = _saved_debuglevel
    httplib2_intercept.uninstall()

@with_setup(install, uninstall)
def test_success():
    http = httplib2.Http()
    resp, content = http.request('http://some_hopefully_nonexistant_domain:80/', 'GET')
    eq_(content, "WSGI intercept successful!\n")
    assert test_wsgi_app.success()

@with_setup(install, uninstall)
@raises(gaierror)
def test_bogus_domain():
    wsgi_intercept.debuglevel = 1;
    httplib2_intercept.HTTP_WSGIInterceptorWithTimeout("_nonexistant_domain_").connect()

@with_setup(lambda: install(443), uninstall)
def test_https_success():
    http = httplib2.Http()
    resp, content = http.request('https://some_hopefully_nonexistant_domain/', 'GET')
    assert test_wsgi_app.success()
########NEW FILE########
__FILENAME__ = test_mechanize

from nose.tools import with_setup, raises
from urllib2 import URLError
from wsgi_intercept.mechanize_intercept import Browser
import wsgi_intercept
from wsgi_intercept import test_wsgi_app
from mechanize import Browser as MechanizeBrowser

###

_saved_debuglevel = None

def add_intercept():
    # _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 80, test_wsgi_app.create_fn)
    
def add_https_intercept():
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 443, test_wsgi_app.create_fn)

def remove_intercept():
    wsgi_intercept.remove_wsgi_intercept('some_hopefully_nonexistant_domain', 80)
    # wsgi_intercept.debuglevel = _saved_debuglevel

@with_setup(add_intercept, remove_intercept)
def test_intercepted():
    b = Browser()
    b.open('http://some_hopefully_nonexistant_domain:80/')
    assert test_wsgi_app.success()

@with_setup(add_intercept)
@raises(URLError)
def test_intercept_removed():
    remove_intercept()
    b = Browser()
    b.open('http://some_hopefully_nonexistant_domain:80/')

@with_setup(add_https_intercept, remove_intercept)
def test_https_intercept():
    b = Browser()
    b.open('https://some_hopefully_nonexistant_domain:443/')
    assert test_wsgi_app.success()

@with_setup(add_intercept, remove_intercept)
def test_https_intercept_default_port():
    b = Browser()
    b.open('https://some_hopefully_nonexistant_domain/')
    assert test_wsgi_app.success()
########NEW FILE########
__FILENAME__ = test_mechanoid
#! /usr/bin/env python2.3
from wsgi_intercept.mechanoid_intercept import Browser
from nose.tools import with_setup
import wsgi_intercept
from wsgi_intercept import test_wsgi_app

###

_saved_debuglevel = None

def install(port=80):
    _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', port, test_wsgi_app.create_fn)

def uninstall():
    wsgi_intercept.debuglevel = _saved_debuglevel

@with_setup(install, uninstall)
def test_success():
    b = Browser()
    b.open('http://some_hopefully_nonexistant_domain:80/')
    assert test_wsgi_app.success()
    
@with_setup(install, uninstall)
def test_https_success():
    b = Browser()
    b.open('https://some_hopefully_nonexistant_domain/')
    assert test_wsgi_app.success()
    
@with_setup(lambda: install(443), uninstall)
def test_https_specific_port_success():
    b = Browser()
    b.open('https://some_hopefully_nonexistant_domain:443/')
    assert test_wsgi_app.success()
########NEW FILE########
__FILENAME__ = test_webtest
#! /usr/bin/env python
import sys
import wsgi_intercept
from wsgi_intercept import test_wsgi_app, webtest_intercept

class WSGI_Test(webtest_intercept.WebCase):
    HTTP_CONN = wsgi_intercept.WSGI_HTTPConnection
    HOST = 'some_hopefully_nonexistant_domain'

    def setUp(self):
        wsgi_intercept.add_wsgi_intercept(self.HOST, self.PORT,
                                          test_wsgi_app.create_fn)
    
    def tearDown(self):
        wsgi_intercept.remove_wsgi_intercept()

    def test_page(self):
        self.getPage('http://%s:%s/' % (self.HOST, self.PORT))
        assert test_wsgi_app.success()
        
class WSGI_HTTPS_Test(webtest_intercept.WebCase):
    HTTP_CONN = wsgi_intercept.WSGI_HTTPConnection
    HOST = 'some_hopefully_nonexistant_domain'

    def setUp(self):
        wsgi_intercept.add_wsgi_intercept(self.HOST, self.PORT,
                                          test_wsgi_app.create_fn)
    
    def tearDown(self):
        wsgi_intercept.remove_wsgi_intercept()

    def test_page(self):
        self.getPage('https://%s:%s/' % (self.HOST, self.PORT))
        assert test_wsgi_app.success()

if __name__ == '__main__':
    webtest.main()

########NEW FILE########
__FILENAME__ = test_webunit
#! /usr/bin/env python
import sys, os.path

import wsgi_intercept
from wsgi_intercept import WSGI_HTTPConnection
from wsgi_intercept import test_wsgi_app

from httplib import HTTP

class WSGI_HTTP(HTTP):
    _connection_class = WSGI_HTTPConnection

###

from wsgi_intercept.webunit_intercept import WebTestCase
import unittest

class WSGI_WebTestCase(WebTestCase):
    scheme_handlers = dict(http=WSGI_HTTP)

    def setUp(self):
        wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 80,
                                          test_wsgi_app.create_fn)
    
    def tearDown(self):
        wsgi_intercept.remove_wsgi_intercept()

    def test_get(self):
        r = self.page('http://some_hopefully_nonexistant_domain/')
        assert test_wsgi_app.success()
        
class WSGI_HTTPS_WebTestCase(WebTestCase):
    scheme_handlers = dict(https=WSGI_HTTP)

    def setUp(self):
        wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 443,
                                          test_wsgi_app.create_fn)
    
    def tearDown(self):
        wsgi_intercept.remove_wsgi_intercept()

    def test_get(self):
        r = self.page('https://some_hopefully_nonexistant_domain/')
        assert test_wsgi_app.success()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_wsgi_compliance
#! /usr/bin/env python2.4
import warnings
from nose.tools import eq_
from wsgi_intercept.httplib2_intercept import install, uninstall
import wsgi_intercept
from wsgi_intercept import test_wsgi_app
import httplib2
from paste import lint

_saved_debuglevel = None

def prudent_wsgi_app():
    return lint.middleware(test_wsgi_app.create_fn())

def setup():
    warnings.simplefilter("error")
    _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    install()
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 80, prudent_wsgi_app)

def test():
    http = httplib2.Http()
    resp, content = http.request('http://some_hopefully_nonexistant_domain:80/', 'GET')
    assert test_wsgi_app.success()

def test_quoting_issue11():
    # see http://code.google.com/p/wsgi-intercept/issues/detail?id=11
    http = httplib2.Http()
    inspected_env = {}
    def make_path_checking_app():
        def path_checking_app(environ, start_response):
            inspected_env ['QUERY_STRING'] = environ['QUERY_STRING']
            inspected_env ['PATH_INFO'] = environ['PATH_INFO']
            status = '200 OK'
            response_headers = [('Content-type','text/plain')]
            start_response(status, response_headers)
            return []
        return path_checking_app
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 80, make_path_checking_app)
    resp, content = http.request('http://some_hopefully_nonexistant_domain:80/spaced+words.html?word=something%20spaced', 'GET')
    assert ('QUERY_STRING' in inspected_env and 'PATH_INFO' in inspected_env), "path_checking_app() was never called?"
    eq_(inspected_env['PATH_INFO'], '/spaced+words.html')
    eq_(inspected_env['QUERY_STRING'], 'word=something%20spaced')

def teardown():
    warnings.resetwarnings()
    wsgi_intercept.debuglevel = _saved_debuglevel
    uninstall()

if __name__ == '__main__':
    setup()
    try:
        test()
    finally:
        teardown()

########NEW FILE########
__FILENAME__ = test_wsgi_urllib2
#! /usr/bin/env python
import sys, os.path
from nose.tools import with_setup
import urllib2
from wsgi_intercept import urllib2_intercept
import wsgi_intercept
from wsgi_intercept import test_wsgi_app

_saved_debuglevel = None

def add_intercept():
    _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 80, test_wsgi_app.create_fn)
    
def add_https_intercept():
    _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', 443, test_wsgi_app.create_fn)

def remove_intercept():
    wsgi_intercept.debuglevel = _saved_debuglevel
    wsgi_intercept.remove_wsgi_intercept()

@with_setup(add_intercept, remove_intercept)
def test():
    urllib2_intercept.install_opener()
    urllib2.urlopen('http://some_hopefully_nonexistant_domain:80/')
    assert test_wsgi_app.success()
    
@with_setup(add_https_intercept, remove_intercept)
def test_https():
    urllib2_intercept.install_opener()
    urllib2.urlopen('https://some_hopefully_nonexistant_domain:443/')
    assert test_wsgi_app.success()
    
@with_setup(add_intercept, remove_intercept)
def test_https_default_port():
    # I guess the default port for https is 80 but I thoght it would be 443
    urllib2_intercept.install_opener()
    urllib2.urlopen('https://some_hopefully_nonexistant_domain/')
    assert test_wsgi_app.success()
########NEW FILE########
__FILENAME__ = test_zope_testbrowser

from nose.tools import with_setup, raises
from urllib2 import URLError
from wsgi_intercept.zope_testbrowser.wsgi_testbrowser import WSGI_Browser
import wsgi_intercept
from wsgi_intercept import test_wsgi_app

_saved_debuglevel = None
    
def add_intercept(port=80):
    # _saved_debuglevel, wsgi_intercept.debuglevel = wsgi_intercept.debuglevel, 1
    wsgi_intercept.add_wsgi_intercept('some_hopefully_nonexistant_domain', port, test_wsgi_app.create_fn)

def remove_intercept():
    wsgi_intercept.remove_wsgi_intercept()
    # wsgi_intercept.debuglevel = _saved_debuglevel

@with_setup(add_intercept, remove_intercept)
def test_intercepted():
    b = WSGI_Browser()
    b.open('http://some_hopefully_nonexistant_domain:80/')
    assert test_wsgi_app.success()

@with_setup(add_intercept)
@raises(URLError)
def test_intercept_removed():
    remove_intercept()
    b = WSGI_Browser()
    b.open('http://some_hopefully_nonexistant_domain:80/')
    
@with_setup(add_intercept, remove_intercept)
def test_https_intercepted():
    b = WSGI_Browser()
    b.open('https://some_hopefully_nonexistant_domain/')
    assert test_wsgi_app.success()
    
@with_setup(lambda: add_intercept(443), remove_intercept)
def test_https_intercepted_443_port():
    b = WSGI_Browser()
    b.open('https://some_hopefully_nonexistant_domain:443/')
    assert test_wsgi_app.success()
########NEW FILE########
__FILENAME__ = test_wsgi_app
"""
A simple WSGI application for testing.
"""

_app_was_hit = False

def success():
    return _app_was_hit

def simple_app(environ, start_response):
    """Simplest possible application object"""
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)

    global _app_was_hit
    _app_was_hit = True
    
    return ['WSGI intercept successful!\n']

def create_fn():
    global _app_was_hit
    _app_was_hit = False
    return simple_app

########NEW FILE########
__FILENAME__ = wsgi_urllib2
import sys
from wsgi_intercept import WSGI_HTTPConnection

import urllib2, httplib
from urllib2 import HTTPHandler, HTTPSHandler
from httplib import HTTP

#
# ugh, version dependence.
#

if sys.version_info[:2] == (2, 3):
    class WSGI_HTTP(HTTP):
        _connection_class = WSGI_HTTPConnection

    class WSGI_HTTPHandler(HTTPHandler):
        """
        Override the default HTTPHandler class with one that uses the
        WSGI_HTTPConnection class to open HTTP URLs.
        """
        def http_open(self, req):
            return self.do_open(WSGI_HTTP, req)
    
    # I'm not implementing HTTPS for 2.3 until someone complains about it! -Kumar
    WSGI_HTTPSHandler = None
    
else:
    class WSGI_HTTPHandler(HTTPHandler):
        """
        Override the default HTTPHandler class with one that uses the
        WSGI_HTTPConnection class to open HTTP URLs.
        """
        def http_open(self, req):
            return self.do_open(WSGI_HTTPConnection, req)
    
    if hasattr(httplib, 'HTTPS'):
        # urllib2 does this check as well, I assume it's to see if 
        # python was compiled with SSL support
        class WSGI_HTTPSHandler(HTTPSHandler):
            """
            Override the default HTTPSHandler class with one that uses the
            WSGI_HTTPConnection class to open HTTPS URLs.
            """
            def https_open(self, req):
                return self.do_open(WSGI_HTTPConnection, req)
    else:
        WSGI_HTTPSHandler = None
    
def install_opener():
    handlers = [WSGI_HTTPHandler()]
    if WSGI_HTTPSHandler is not None:
        handlers.append(WSGI_HTTPSHandler())
    opener = urllib2.build_opener(*handlers)
    urllib2.install_opener(opener)

    return opener

def uninstall_opener():
    urllib2.install_opener(None)

########NEW FILE########
__FILENAME__ = webtest
"""Extensions to unittest for web frameworks.

Use the WebCase.getPage method to request a page from your HTTP server.

Framework Integration
=====================

If you have control over your server process, you can handle errors
in the server-side of the HTTP conversation a bit better. You must run
both the client (your WebCase tests) and the server in the same process
(but in separate threads, obviously).

When an error occurs in the framework, call server_error. It will print
the traceback to stdout, and keep any assertions you have from running
(the assumption is that, if the server errors, the page output won't be
of further significance to your tests).
"""

import os, sys, time, re
import types
import pprint
import socket
import httplib
import traceback

from unittest import *
from unittest import _TextTestResult


class TerseTestResult(_TextTestResult):
    
    def printErrors(self):
        # Overridden to avoid unnecessary empty line
        if self.errors or self.failures:
            if self.dots or self.showAll:
                self.stream.writeln()
            self.printErrorList('ERROR', self.errors)
            self.printErrorList('FAIL', self.failures)


class TerseTestRunner(TextTestRunner):
    """A test runner class that displays results in textual form."""
    
    def _makeResult(self):
        return TerseTestResult(self.stream, self.descriptions, self.verbosity)
    
    def run(self, test):
        "Run the given test case or test suite."
        # Overridden to remove unnecessary empty lines and separators
        result = self._makeResult()
        startTime = time.time()
        test(result)
        timeTaken = float(time.time() - startTime)
        result.printErrors()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        return result


class ReloadingTestLoader(TestLoader):
    
    def loadTestsFromName(self, name, module=None):
        """Return a suite of all tests cases given a string specifier.

        The name may resolve either to a module, a test case class, a
        test method within a test case class, or a callable object which
        returns a TestCase or TestSuite instance.

        The method optionally resolves the names relative to a given module.
        """
        parts = name.split('.')
        if module is None:
            if not parts:
                raise ValueError("incomplete test name: %s" % name)
            else:
                parts_copy = parts[:]
                while parts_copy:
                    target = ".".join(parts_copy)
                    if target in sys.modules:
                        module = reload(sys.modules[target])
                        break
                    else:
                        try:
                            module = __import__(target)
                            break
                        except ImportError:
                            del parts_copy[-1]
                            if not parts_copy:
                                raise
                parts = parts[1:]
        obj = module
        for part in parts:
            obj = getattr(obj, part)
        
        if type(obj) == types.ModuleType:
            return self.loadTestsFromModule(obj)
        elif (isinstance(obj, (type, types.ClassType)) and
              issubclass(obj, TestCase)):
            return self.loadTestsFromTestCase(obj)
        elif type(obj) == types.UnboundMethodType:
            return obj.im_class(obj.__name__)
        elif callable(obj):
            test = obj()
            if not isinstance(test, TestCase) and \
               not isinstance(test, TestSuite):
                raise ValueError("calling %s returned %s, "
                                 "not a test" % (obj,test))
            return test
        else:
            raise ValueError("don't know how to make test from: %s" % obj)


try:
    # On Windows, msvcrt.getch reads a single char without output.
    import msvcrt
    def getchar():
        return msvcrt.getch()
except ImportError:
    # Unix getchr
    import tty, termios
    def getchar():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class WebCase(TestCase):
    HOST = "127.0.0.1"
    PORT = 8000
    HTTP_CONN=httplib.HTTPConnection
    
    def getPage(self, url, headers=None, method="GET", body=None):
        """Open the url with debugging support. Return status, headers, body."""
        ServerError.on = False
        
        self.url = url
        result = openURL(url, headers, method, body, self.HOST, self.PORT,
                         self.HTTP_CONN)
        self.status, self.headers, self.body = result
        
        # Build a list of request cookies from the previous response cookies.
        self.cookies = [('Cookie', v) for k, v in self.headers
                        if k.lower() == 'set-cookie']
        
        if ServerError.on:
            raise ServerError()
        return result
    
    interactive = True
    console_height = 30
    
    def _handlewebError(self, msg):
        if not self.interactive:
            raise self.failureException(msg)
        
        print
        print "    ERROR:", msg
        p = "    Show: [B]ody [H]eaders [S]tatus [U]RL; [I]gnore, [R]aise, or sys.e[X]it >> "
        print p,
        while True:
            i = getchar().upper()
            if i not in "BHSUIRX":
                continue
            print i.upper()  # Also prints new line
            if i == "B":
                for x, line in enumerate(self.body.splitlines()):
                    if (x + 1) % self.console_height == 0:
                        # The \r and comma should make the next line overwrite
                        print "<-- More -->\r",
                        m = getchar().lower()
                        # Erase our "More" prompt
                        print "            \r",
                        if m == "q":
                            break
                    print line
            elif i == "H":
                pprint.pprint(self.headers)
            elif i == "S":
                print self.status
            elif i == "U":
                print self.url
            elif i == "I":
                # return without raising the normal exception
                return
            elif i == "R":
                raise self.failureException(msg)
            elif i == "X":
                self.exit()
            print p,
    
    def exit(self):
        sys.exit()
    
    def __call__(self, result=None):
        if result is None:
            result = self.defaultTestResult()
        result.startTest(self)
        if hasattr(self, '_testMethodName'):
            # 2.5 + ?
            testMethod = getattr(self, self._testMethodName)
        elif hasattr(self, '_TestCase__testMethodName'):
            # 2.4
            testMethod = getattr(self, self._TestCase__testMethodName)
        else:
            raise AttributeError("Not sure how to get the test method in %s" % self)
        try:
            try:
                self.setUp()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                result.addError(self, self._TestCase__exc_info())
                return
            
            ok = 0
            try:
                testMethod()
                ok = 1
            except self.failureException:
                result.addFailure(self, self._TestCase__exc_info())
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                result.addError(self, self._TestCase__exc_info())
            
            try:
                self.tearDown()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                result.addError(self, self._TestCase__exc_info())
                ok = 0
            if ok:
                result.addSuccess(self)
        finally:
            result.stopTest(self)
    
    def assertStatus(self, status, msg=None):
        """Fail if self.status != status."""
        if isinstance(status, basestring):
            if not self.status == status:
                if msg is None:
                    msg = 'Status (%s) != %s' % (`self.status`, `status`)
                self._handlewebError(msg)
        else:
            if not self.status in status:
                if msg is None:
                    msg = 'Status (%s) not in %s' % (`self.status`, `status`)
                self._handlewebError(msg)
    
    def assertHeader(self, key, value=None, msg=None):
        """Fail if (key, [value]) not in self.headers."""
        lowkey = key.lower()
        for k, v in self.headers:
            if k.lower() == lowkey:
                if value is None or str(value) == v:
                    return
        
        if msg is None:
            if value is None:
                msg = '%s not in headers' % `key`
            else:
                msg = '%s:%s not in headers' % (`key`, `value`)
        self._handlewebError(msg)
    
    def assertNoHeader(self, key, msg=None):
        """Fail if key in self.headers."""
        lowkey = key.lower()
        matches = [k for k, v in self.headers if k.lower() == lowkey]
        if matches:
            if msg is None:
                msg = '%s in headers' % `key`
            self._handlewebError(msg)
    
    def assertBody(self, value, msg=None):
        """Fail if value != self.body."""
        if value != self.body:
            if msg is None:
                msg = 'expected body:\n%s\n\nactual body:\n%s' % (`value`, `self.body`)
            self._handlewebError(msg)
    
    def assertInBody(self, value, msg=None):
        """Fail if value not in self.body."""
        if value not in self.body:
            if msg is None:
                msg = '%s not in body' % `value`
            self._handlewebError(msg)
    
    def assertNotInBody(self, value, msg=None):
        """Fail if value in self.body."""
        if value in self.body:
            if msg is None:
                msg = '%s found in body' % `value`
            self._handlewebError(msg)
    
    def assertMatchesBody(self, pattern, msg=None, flags=0):
        """Fail if value (a regex pattern) is not in self.body."""
        if re.search(pattern, self.body, flags) is None:
            if msg is None:
                msg = 'No match for %s in body' % `pattern`
            self._handlewebError(msg)



def cleanHeaders(headers, method, body, host, port):
    """Return request headers, with required headers added (if missing)."""
    if headers is None:
        headers = []
    
    # Add the required Host request header if not present.
    # [This specifies the host:port of the server, not the client.]
    found = False
    for k, v in headers:
        if k.lower() == 'host':
            found = True
            break
    if not found:
        headers.append(("Host", "%s:%s" % (host, port)))
    
    if method in ("POST", "PUT"):
        # Stick in default type and length headers if not present
        found = False
        for k, v in headers:
            if k.lower() == 'content-type':
                found = True
                break
        if not found:
            headers.append(("Content-Type", "application/x-www-form-urlencoded"))
            headers.append(("Content-Length", str(len(body or ""))))
    
    return headers


def openURL(url, headers=None, method="GET", body=None,
            host="127.0.0.1", port=8000, http_conn=httplib.HTTPConnection):
    """Open the given HTTP resource and return status, headers, and body."""
    
    headers = cleanHeaders(headers, method, body, host, port)
    
    # Trying 10 times is simply in case of socket errors.
    # Normal case--it should run once.
    trial = 0
    while trial < 10:
        try:
            conn = http_conn(host, port)
            conn.putrequest(method.upper(), url)
            
            for key, value in headers:
                conn.putheader(key, value)
            conn.endheaders()
            
            if body is not None:
                conn.send(body)
            
            # Handle response
            response = conn.getresponse()
            
            status = "%s %s" % (response.status, response.reason)
            
            outheaders = []
            for line in response.msg.headers:
                key, value = line.split(":", 1)
                outheaders.append((key.strip(), value.strip()))
            
            outbody = response.read()
            
            conn.close()
            return status, outheaders, outbody
        except socket.error:
            trial += 1
            if trial >= 10:
                raise
            else:
                time.sleep(0.5)


# Add any exceptions which your web framework handles
# normally (that you don't want server_error to trap).
ignored_exceptions = []

# You'll want set this to True when you can't guarantee
# that each response will immediately follow each request;
# for example, when handling requests via multiple threads.
ignore_all = False

class ServerError(Exception):
    on = False


def server_error(exc=None):
    """Server debug hook. Return True if exception handled, False if ignored.
    
    You probably want to wrap this, so you can still handle an error using
    your framework when it's ignored.
    """
    if exc is None: 
        exc = sys.exc_info()
    
    if ignore_all or exc[0] in ignored_exceptions:
        return False
    else:
        ServerError.on = True
        print
        print "".join(traceback.format_exception(*exc))
        return True


########NEW FILE########
__FILENAME__ = config
"""
This file allows you to set up configuration variables to identify the
machine and port to test.

It needs some work, but in a nutshell, put a config.cfg in your "test"
directory with the following contents::

    [DEFAULT]
    machine = www.dev.ekorp.com
    port = 80
    
    [dev-ekit]
    # uses DEFAULT
    
    [dev-lp]
    machine = www.lonelyplanet.dev.ekorp.com
    port = 80

Then set the environment var "TEST_CONFIG" to the config to use.

"""
import os
if os.path.exists('test/config.cfg'):
    import ConfigParser
    cfg = ConfigParser.ConfigParser()
    cfg.read('test/config.cfg')

    # figure the active config
    active = os.environ.get('TEST_CONFIG', 'DEFAULT')

    # fetch the actual config info
    machine = cfg.get(active, 'machine')
    port = cfg.getint(active, 'port')

########NEW FILE########
__FILENAME__ = cookie
import re, urlparse, Cookie

class Error:
    '''Handles a specific cookie error.

    message - a specific message as to why the cookie is erroneous
    '''
    def __init__(self, message):
        self.message = str(message)

    def __str__(self):
        return 'COOKIE ERROR: %s'%self.message

def parse_cookie(text, qparmre=re.compile(
        r'([\0- ]*([^\0- ;,=\"]+)="([^"]*)\"([\0- ]*[;,])?[\0- ]*)'),
        parmre=re.compile(
        r'([\0- ]*([^\0- ;,=\"]+)=([^\0- ;,\"]*)([\0- ]*[;,])?[\0- ]*)')):
    result = {}
    l = 0
    while 1:
        if qparmre.match(text[l:]) >= 0:
            # Match quoted correct cookies
            name=qparmre.group(2)
            value=qparmre.group(3)
            l=len(qparmre.group(1))
        elif parmre.match(text[l:]) >= 0:
            # Match evil MSIE cookies ;)
            name=parmre.group(2)
            value=parmre.group(3)
            l=len(parmre.group(1))
        else:
            # this may be an invalid cookie.
            # We'll simply bail without raising an error
            # if the cookie is invalid.
            return result
        if not result.has_key(name):
            result[name]=value
    return result

def decodeCookies(url, server, headers, cookies):
    '''Decode cookies into the supplied cookies dictionary
       http://www.ietf.org/rfc/rfc2109.txt
    '''
    # the path of the request URL up to, but not including, the right-most /
    request_path = urlparse.urlparse(url)[2]
    if len(request_path) > 1 and request_path[-1] == '/':
        request_path = request_path[:-1]

    hdrcookies = Cookie.SimpleCookie("\n".join(map(lambda x: x.strip(), 
        headers.getallmatchingheaders('set-cookie'))))
    for cookie in hdrcookies.values():
        # XXX: there doesn't seem to be a way to determine if the
        # cookie was set or defaulted to an empty string :(
        if cookie['domain']:
            domain = cookie['domain']

            # reject if The value for the Domain attribute contains no
            # embedded dots or does not start with a dot.
            if '.' not in domain:
                raise Error, 'Cookie domain "%s" has no "."'%domain
            if domain[0] != '.':
                raise Error, 'Cookie domain "%s" doesn\'t start '\
                    'with "."'%domain
            # reject if The value for the request-host does not
            # domain-match the Domain attribute.
            if not server.endswith(domain):
                raise Error, 'Cookie domain "%s" doesn\'t match '\
                    'request host "%s"'%(domain, server)
            # reject if The request-host is a FQDN (not IP address) and
            # has the form HD, where D is the value of the Domain
            # attribute, and H is a string that contains one or more dots.
            if re.search(r'[a-zA-Z]', server):
                H = server[:-len(domain)]
                if '.' in H:
                    raise Error, 'Cookie domain "%s" too short '\
                    'for request host "%s"'%(domain, server)
        else:
            domain = server

        # path check
        path = cookie['path'] or request_path
        # reject if Path attribute is not a prefix of the request-URI
        # (noting that empty request path and '/' are often synonymous, yay)
        if not (request_path.startswith(path) or (request_path == '' and
                cookie['path'] == '/')):
            raise Error, 'Cookie path "%s" doesn\'t match '\
                'request url "%s"'%(path, request_path)

        bydom = cookies.setdefault(domain, {})
        bypath = bydom.setdefault(path, {})
        bypath[cookie.key] = cookie


########NEW FILE########
__FILENAME__ = HTMLParser
"""A parser for HTML."""

# This file is derived from sgmllib.py, which is part of Python.

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


import re
import string

# Regular expressions used for parsing

interesting_normal = re.compile('[&<]')
interesting_cdata = re.compile(r'<(/|\Z)')
incomplete = re.compile('(&[a-zA-Z][-.a-zA-Z0-9]*|&#[0-9]*)')

entityref = re.compile('&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]')
charref = re.compile('&#([0-9]+)[^0-9]')

starttagopen = re.compile('<[a-zA-Z]')
piopen = re.compile(r'<\?')
piclose = re.compile('>')
endtagopen = re.compile('</')
declopen = re.compile('<!')
special = re.compile('<![^<>]*>')
commentopen = re.compile('<!--')
commentclose = re.compile(r'--\s*>')
tagfind = re.compile('[a-zA-Z][-.a-zA-Z0-9:_]*')
attrfind = re.compile(
    r'\s*([a-zA-Z_][-.:a-zA-Z_0-9]*)(\s*=\s*'
    r'(\'[^\']*\'|"[^"]*"|[-a-zA-Z0-9./:;+*%?!&$\(\)_#=~]*))?')

locatestarttagend = re.compile(r"""
  <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
  (?:\s+                             # whitespace before attribute name
    (?:[a-zA-Z_][-.:a-zA-Z0-9_]*     # attribute name
      (?:\s*=\s*                     # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |\"[^\"]*\"                # LIT-enclosed value
          |[^'\">\s]+                # bare value
         )
       )?
     )
   )*
  \s*                                # trailing whitespace
""", re.VERBOSE)
endstarttag = re.compile(r"\s*/?>")
endendtag = re.compile('>')
endtagfind = re.compile('</\s*([a-zA-Z][-.a-zA-Z0-9:_]*)\s*>')

declname = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9]*\s*')
declstringlit = re.compile(r'(\'[^\']*\'|"[^"]*")\s*')


class HTMLParseError(Exception):
    """Exception raised for all parse errors."""

    def __init__(self, msg, position=(None, None)):
        assert msg
        self.msg = msg
        self.lineno = position[0]
        self.offset = position[1]

    def __str__(self):
        result = self.msg
        if self.lineno is not None:
            result = result + ", at line %d" % self.lineno
        if self.offset is not None:
            result = result + ", column %d" % (self.offset + 1)
        return result


# HTML parser class -- find tags and call handler functions.
# Usage:
#
#     p = HTMLParser(); p.feed(data); ...; p.close()

# Start tags are handled by calling self.handle_starttag() or
# self.handle_startendtag(); end tags by self.handle_endtag().  The
# data between tags is passed from the parser to the derived class by
# calling self.handle_data() with the data as argument (the data may
# be split up in arbitrary chunks).  Entity references are passed by
# calling self.handle_entityref() with the entity reference as the
# argument.  Numeric character references are passed to
# self.handle_charref() with the string containing the reference as
# the argument.

class HTMLParser:

    CDATA_CONTENT_ELEMENTS = ("script", "style")


    # Interface -- initialize and reset this instance
    def __init__(self):
        self.reset()

    # Interface -- reset this instance.  Loses all unprocessed data
    def reset(self):
        self.rawdata = ''
        self.stack = []
        self.lasttag = '???'
        self.lineno = 1
        self.offset = 0
        self.interesting = interesting_normal

    # Interface -- feed some data to the parser.  Call this as
    # often as you want, with as little or as much text as you
    # want (may include '\n').  (This just saves the text, all the
    # processing is done by goahead().)
    def feed(self, data):
        self.rawdata = self.rawdata + data
        self.goahead(0)

    # Interface -- handle the remaining data
    def close(self):
        self.goahead(1)

    # Internal -- update line number and offset.  This should be
    # called for each piece of data exactly once, in order -- in other
    # words the concatenation of all the input strings to this
    # function should be exactly the entire input.
    def updatepos(self, i, j):
        if i >= j:
            return j
        rawdata = self.rawdata
        nlines = string.count(rawdata, "\n", i, j)
        if nlines:
            self.lineno = self.lineno + nlines
            pos = string.rindex(rawdata, "\n", i, j) # Should not fail
            self.offset = j-(pos+1)
        else:
            self.offset = self.offset + j-i
        return j

    # Interface -- return current line number and offset.
    def getpos(self):
        return self.lineno, self.offset

    __starttag_text = None

    # Interface -- return full source of start tag: "<...>"
    def get_starttag_text(self):
        return self.__starttag_text

    def set_cdata_mode(self, tag):
        self.interesting = re.compile(r'<(/%s|\Z)'%tag)

    def clear_cdata_mode(self):
        self.interesting = interesting_normal

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        rawdata = self.rawdata
        i = 0
        n = len(rawdata)
        while i < n:
            match = self.interesting.search(rawdata, i) # < or &
            if match:
                j = match.start()
            else:
                j = n
            if i < j: self.handle_data(rawdata[i:j])
            i = self.updatepos(i, j)
            if i == n: break
            if rawdata[i] == '<':
                if starttagopen.match(rawdata, i): # < + letter
                    k = self.parse_starttag(i)
                elif endtagopen.match(rawdata, i): # </
                    k = self.parse_endtag(i)
                    if k >= 0:
                        self.clear_cdata_mode()
                elif commentopen.match(rawdata, i): # <!--
                    k = self.parse_comment(i)
                elif piopen.match(rawdata, i): # <?
                    k = self.parse_pi(i)
                elif declopen.match(rawdata, i): # <!
                    k = self.parse_declaration(i)
                else:
                    if i < n-1:
                        raise HTMLParseError(
                            "invalid '<' construct: %s" % `rawdata[i:i+2]`,
                            self.getpos())
                    k = -1
                if k < 0:
                    if end:
                        raise HTMLParseError("EOF in middle of construct",
                                             self.getpos())
                    break
                i = self.updatepos(i, k)
            elif rawdata[i] == '&':
                
                match = charref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_charref(name)
                    k = match.end()
                    if rawdata[k-1] != ';':
                        k = k-1
                    i = self.updatepos(i, k)
                    continue
                match = entityref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_entityref(name)
                    k = match.end()
                    if rawdata[k-1] != ';':
                        k = k-1
                    i = self.updatepos(i, k)
                    continue
                if incomplete.match(rawdata, i):
                    if end:
                        raise HTMLParseError(
                            "EOF in middle of entity or char ref",
                            self.getpos())
                    return -1 # incomplete
                #raise HTMLParseError("'&' not part of entity or char ref",
                #                     self.getpos())
                # people seem to be fond of bare '&', so skip it
                i = self.updatepos(i, i+1)
            else:
                assert 0, "interesting.search() lied"
        # end while
        if end and i < n:
            self.handle_data(rawdata[i:n])
            i = self.updatepos(i, n)
        self.rawdata = rawdata[i:]

    # Internal -- parse comment, return end or -1 if not terminated
    def parse_comment(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+4] == '<!--', 'unexpected call to parse_comment()'
        match = commentclose.search(rawdata, i+4)
        if not match:
            return -1
        j = match.start()
        self.handle_comment(rawdata[i+4: j])
        j = match.end()
        return j

    # Internal -- parse declaration.
    def parse_declaration(self, i):
        # This is some sort of declaration; in "HTML as
        # deployed," this should only be the document type
        # declaration ("<!DOCTYPE html...>").
        rawdata = self.rawdata
        j = i + 2
        assert rawdata[i:j] == "<!", "unexpected call to parse_declaration"
        if rawdata[j:j+1] in ("-", ""):
            # Start of comment followed by buffer boundary,
            # or just a buffer boundary.
            return -1
        # in practice, this should look like: ((name|stringlit) S*)+ '>'
        n = len(rawdata)
        while j < n:
            c = rawdata[j]
            if c == ">":
                # end of declaration syntax
                self.handle_decl(rawdata[i+2:j])
                return j + 1
            if c in "\"'":
                m = declstringlit.match(rawdata, j)
                if not m:
                    return -1 # incomplete
                j = m.end()
            elif c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                m = declname.match(rawdata, j)
                if not m:
                    return -1 # incomplete
                j = m.end()
            else:
                raise HTMLParseError(
                    "unexpected char in declaration: %s" % `rawdata[j]`,
                    self.getpos())
        return -1 # incomplete

    # Internal -- parse processing instr, return end or -1 if not terminated
    def parse_pi(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == '<?', 'unexpected call to parse_pi()'
        match = piclose.search(rawdata, i+2) # >
        if not match:
            return -1
        j = match.start()
        self.handle_pi(rawdata[i+2: j])
        j = match.end()
        return j

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = string.lower(rawdata[i+1:k])

        while k < endpos:
            m = attrfind.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
                attrvalue = self.unescape(attrvalue)
            attrs.append((string.lower(attrname), attrvalue))
            k = m.end()

        end = string.strip(rawdata[k:endpos])
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + string.count(self.__starttag_text, "\n")
                offset = len(self.__starttag_text) \
                         - string.rfind(self.__starttag_text, "\n")
            else:
                offset = offset + len(self.__starttag_text)
            raise HTMLParseError("junk characters in start tag: %s"
                                 % `rawdata[k:endpos][:20]`,
                                 (lineno, offset))
        if end[-2:] == '/>':
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
        return endpos

    # Internal -- check to see if we have a complete starttag; return end
    # or -1 if incomplete.
    def check_for_whole_start_tag(self, i):
        rawdata = self.rawdata
        m = locatestarttagend.match(rawdata, i)
        if m:
            j = m.end()
            next = rawdata[j:j+1]
            if next == ">":
                return j + 1
            if next == "/":
                s = rawdata[j:j+2]
                if s == "/>":
                    return j + 2
                if s == "/":
                    # buffer boundary
                    return -1
                # else bogus input
                self.updatepos(i, j + 1)
                raise HTMLParseError("malformed empty start tag",
                                     self.getpos())
            if next == "":
                # end of input
                return -1
            if next in ("abcdefghijklmnopqrstuvwxyz=/"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                # end of input in or before attribute value, or we have the
                # '/' from a '/>' ending
                return -1
            self.updatepos(i, j)
            raise HTMLParseError("malformed start tag", self.getpos())
        raise AssertionError("we should not gt here!")

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == "</", "unexpected call to parse_endtag"
        match = endendtag.search(rawdata, i+1) # >
        if not match:
            return -1
        j = match.end()
        match = endtagfind.match(rawdata, i) # </ + tag + >
        if not match:
            raise HTMLParseError("bad end tag: %s" % `rawdata[i:j]`,
                                 self.getpos())
        tag = match.group(1)
        self.handle_endtag(string.lower(tag))
        return j

    # Overridable -- finish processing of start+end tag: <tag.../>
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    # Overridable -- handle start tag
    def handle_starttag(self, tag, attrs):
        pass

    # Overridable -- handle end tag
    def handle_endtag(self, tag):
        pass

    # Overridable -- handle character reference
    def handle_charref(self, name):
        pass

    # Overridable -- handle entity reference
    def handle_entityref(self, name):
        pass

    # Overridable -- handle data
    def handle_data(self, data):
        pass

    # Overridable -- handle comment
    def handle_comment(self, data):
        pass

    # Overridable -- handle declaration
    def handle_decl(self, decl):
        pass

    # Overridable -- handle processing instruction
    def handle_pi(self, data):
        pass

    # Internal -- helper to remove special character quoting
    def unescape(self, s):
        if '&' not in s:
            return s
        s = string.replace(s, "&lt;", "<")
        s = string.replace(s, "&gt;", ">")
        s = string.replace(s, "&apos;", "'")
        s = string.replace(s, "&quot;", '"')
        s = string.replace(s, "&amp;", "&") # Must be last
        return s

########NEW FILE########
__FILENAME__ = IMGSucker
#
# Copyright (c) 2003 Richard Jones (http://mechanicalcat.net/richard)
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com/)
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
#
# See the README for full license details.
# 
# $Id: IMGSucker.py,v 1.2 2003/07/22 01:19:22 richard Exp $

import htmllib, formatter, urlparse

class IMGSucker(htmllib.HTMLParser):
    '''Suck in all the images and linked stylesheets for an HTML page.

    The sucker uses a HTTP session object which provides:
         url - the URL of the page that we're parsing
     session - a HTTP session object which provides:
               fetch: a method that retrieves a file from a URL
               images: a mapping that holds the fetched images
     
    Once instantiated, the sucker is fed data through its feed method and
    then it must be close()'ed.

    **CURRENTLY NOT IMPLEMENTED**
    Once done, the output attribute of the sucker holds the HTML with URLs
    rewritten for local files where appropriate.
    **CURRENTLY NOT IMPLEMENTED**
    '''
    def __init__(self, url, session):
        htmllib.HTMLParser.__init__(self, formatter.NullFormatter())
        self.base = url
        self.session = session
        self.output = ""

    def handle_data(self, data):
        self.output = self.output + data

    def unknown_starttag(self, tag, attributes):
        self.output = self.output + '<%s' % tag
        for name, value in attributes:
            self.output = self.output + ' %s="%s"' % (name, value)
        self.output = self.output + '>'

    def handle_starttag(self, tag, method, attributes):
        if tag == 'img' or tag == 'base' or tag == 'link':
            method(attributes)
        else:
            self.unknown_starttag(tag, attributes)

    def unknown_endtag(self, tag):
        self.output = self.output + '</%s>' % tag
    
    def handle_endtag(self, tag, method):
        self.unknown_endtag(tag)

    def close(self):
        htmllib.HTMLParser.close(self)

    def do_base(self, attributes):
        for name, value in attributes:
            if name == 'href':
                self.base = value
        # Write revised base tag to file
        self.unknown_starttag('base', attributes)

    def do_img(self, attributes):
        newattributes = []
        for name, value in attributes:
            if name == 'src':
                url = urlparse.urljoin(self.base, value)
                # TODO: figure the re-write path
                # newattributes.append((name, path))
                if not self.session.images.has_key(url):
                    self.session.images[url] = self.session.fetch(url)
            else:
                newattributes.append((name, value))
        # Write the img tag to file (with revised paths)
        self.unknown_starttag('img', newattributes)

    def do_link(self, attributes):
        newattributes = [('rel', 'stylesheet'), ('type', 'text/css')]
        for name, value in attributes:
            if name == 'href':
                url = urlparse.urljoin(self.base, value)
                # TODO: figure the re-write path
                # newattributes.append((name, path))
                self.session.fetch(url)
            else:
                newattributes.append((name, value))
        # Write the link tag to file (with revised paths)
        self.unknown_starttag('link', newattributes)

#
# $Log: IMGSucker.py,v $
# Revision 1.2  2003/07/22 01:19:22  richard
# patches
#
# Revision 1.1.1.1  2003/07/22 01:01:44  richard
#
#
# Revision 1.4  2002/02/27 03:00:08  rjones
# more tests, bugfixes
#
# Revision 1.3  2002/02/25 03:11:00  rjones
# *** empty log message ***
#
# Revision 1.2  2002/02/13 01:16:56  rjones
# *** empty log message ***
#
#
# vim: set filetype=python ts=4 sw=4 et si


########NEW FILE########
__FILENAME__ = SimpleDOM
#
# Copyright (c) 2003 Richard Jones (http://mechanicalcat.net/richard)
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com/)
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
#
# See the README for full license details.
#
# HISTORY:
# This code is heavily based on the TAL parsing code from the Zope Page
# Templates effort at www.zope.org. No copyright or license accompanied
# that code.
# 
# $Id: SimpleDOM.py,v 1.6 2004/01/21 22:50:09 richard Exp $

'''A Simple DOM parser

Simple usage:
>>> import SimpleDOM
>>> parser = SimpleDOM.SimpleDOMParser()
>>> parser.parseString("""<html><head><title>My Document</title></head>
... <body>
...  <p>This is a paragraph!!!</p>
...  <p>This is another para!!</p>
... </body>
... </html>""")
>>> dom = parser.getDOM()
>>> dom.getByName('p')
[<SimpleDOMNode "p" {} (1 elements)>, <SimpleDOMNode "p" {} (1 elements)>]
>>> dom.getByName('p')[0][0]
'This is a paragraph!!!'
>>> dom.getByName('title')[0][0]
'My Document'
'''

import sys, string

# NOTE this is using a modified HTMLParser
from HTMLParser import HTMLParser, HTMLParseError
from utility import Upload

BOOLEAN_HTML_ATTRS = [
    # List of Boolean attributes in HTML that may be given in
    # minimized form (e.g. <img ismap> rather than <img ismap="">)
    # From http://www.w3.org/TR/xhtml1/#guidelines (C.10)
    "compact", "nowrap", "ismap", "declare", "noshade", "checked",
    "disabled", "readonly", "multiple", "selected", "noresize",
    "defer"
    ]

EMPTY_HTML_TAGS = [
    # List of HTML tags with an empty content model; these are
    # rendered in minimized form, e.g. <img />.
    # From http://www.w3.org/TR/xhtml1/#dtds
    "base", "meta", "link", "hr", "br", "param", "img", "area",
    "input", "col", "basefont", "isindex", "frame",
    ]

PARA_LEVEL_HTML_TAGS = [
    # List of HTML elements that close open paragraph-level elements
    # and are themselves paragraph-level.
    "h1", "h2", "h3", "h4", "h5", "h6", "p",
    ]

BLOCK_CLOSING_TAG_MAP = {
    "tr": ("tr", "td", "th"),
    "td": ("td", "th"),
    "th": ("td", "th"),
    "li": ("li",),
    "dd": ("dd", "dt"),
    "dt": ("dd", "dt"),
    "option": ("option",),
    }

BLOCK_LEVEL_HTML_TAGS = [
    # List of HTML tags that denote larger sections than paragraphs.
    "blockquote", "table", "tr", "th", "td", "thead", "tfoot", "tbody",
    "noframe", "div", "form", "font", "p",
    "ul", "ol", "li", "dl", "dt", "dd",
    ]


class NestingError(HTMLParseError):
    """Exception raised when elements aren't properly nested."""

    def __init__(self, tagstack, endtag, position=(None, None)):
        self.endtag = endtag
        if tagstack:
            if len(tagstack) == 1:
                msg = ('Open tag <%s> does not match close tag </%s>'
                       % (tagstack[0], endtag))
            else:
                msg = ('Open tags <%s> do not match close tag </%s>'
                       % (string.join(tagstack, '>, <'), endtag))
        else:
            msg = 'No tags are open to match </%s>' % endtag
        HTMLParseError.__init__(self, msg, position)

class EmptyTagError(NestingError):
    """Exception raised when empty elements have an end tag."""

    def __init__(self, tag, position=(None, None)):
        self.tag = tag
        msg = 'Close tag </%s> should be removed' % tag
        HTMLParseError.__init__(self, msg, position)

_marker=[]
class SimpleDOMNode:
    '''Simple class that represents a tag in a HTML document. The node may
       have contents which are represented as a sequence of tags or strings
       of text.

       node.name  -- get the "name" attribute
       node[N]    -- get the Nth entry in the contents list
       len(node)  -- number of sub-content objects
    '''
    def __init__(self, name, attributes, contents):
        self.__dict__['__name'] = name
        self.__dict__['__attributes'] = attributes
        self.__dict__['__contents'] = contents

    def getByName(self, name, r=None):
        '''Return all nodes of type "name" from the contents of this DOM
           using a depth-first search.
        '''
        if r is None:
            r = []
        for entry in self.getContents():
            if isinstance(entry, SimpleDOMNode):
                if entry.__dict__['__name'] == name:
                    r.append(entry)
                entry.getByName(name, r)
        return r

    def getById(self, name, id):
        '''Return all nodes of type "name" from the contents of this DOM
           using a depth-first search.
        '''
        l = self.getByName(name)
        for entry in l:
            if hasattr(entry, 'id') and entry.id == id:
                return entry
        raise ValueError, 'No %r with id %r'%(name, id)

    def getByNameFlat(self, name):
        '''Return all nodes of type "name" from the contents of this node.
           NON-RECURSIVE.
        '''
        r = []
        for entry in self.getContents():
            if isinstance(entry, SimpleDOMNode):
                if entry.__dict__['__name'] == name:
                    r.append(entry)
        return r

    def getPath(self, path):
        '''Return all nodes of type "name" from the contents of this node.
           NON-RECURSIVE.
        '''
        current = self
        for name, count in path:
            for entry in current.getContents():
                if isinstance(entry, SimpleDOMNode) and \
                        entry.__dict__['__name'] == name:
                    if not count:
                        current = entry
                        break
                    count -= 1
        return current

    def hasChildNodes(self):
        '''Determine if the Node has any content nodes (rather than just text).
        '''
        for entry in self.getContents():
            if isinstance(entry, SimpleDOMNode):
                return 1
        return 0

    def getContents(self):
        return self.__dict__['__contents']

    def __getitem__(self, item):
        return self.getContents()[item]

    def hasattr(self, attr):
        return self.__dict__['__attributes'].has_key(attr)

    def getattr(self, attr, default=_marker):
        if self.__dict__['__attributes'].has_key(attr):
            return self.__dict__['__attributes'][attr]
        if default is _marker:
            raise AttributeError, attr
        return default

    def __getattr__(self, attr):
        if self.__dict__['__attributes'].has_key(attr):
            return self.__dict__['__attributes'][attr]
        if self.__dict__.has_key(attr):
            return self.__dict__[attr]
        raise AttributeError, attr
    
    def __len__(self):
        return len(self.getContents())

    def getContentString(self):
        s = ''
        for content in self.getContents():
            s = s + str(content)
        return s

    def __str__(self):
        attrs = []
        for attr in self.__dict__['__attributes'].items():
            if attr[0] in BOOLEAN_HTML_ATTRS:
                attrs.append(attr[0])
            else:
                attrs.append('%s="%s"'%attr)
        if attrs:
            s = '<%s %s>'%(self.__dict__['__name'], ' '.join(attrs))
        else:
            s = '<%s>'%self.__dict__['__name']
        s = s + self.getContentString()
        if self.__dict__['__name'] in EMPTY_HTML_TAGS:
            return s
        else:
            return s + '</%s>'%self.__dict__['__name']

    def __repr__(self):
        return '<SimpleDOMNode "%s" %s (%s elements)>'%(self.__dict__['__name'],
            self.__dict__['__attributes'], len(self.getContents()))

    def extractElements(self, path=[], include_submit=0, include_button=0):
        ''' Pull a form's elements out of the document given the path to the
            form.

            For most elements, the returned dictionary has a key:value pair
            holding the input elements name and value.

            For radio, checkboxes and selects, the value is a dictionary
            holding:

              value or name: 'selected'    (note: not 'checked')

            where the value of the input/option is used but if not
            present then the name is used.
        '''
        form = self
        for name, element in path:
            form = form.getByName(name)[element]
        elements = {}
        submits = 0
        buttons = 0
        for input in form.getByName('input'):
            if not hasattr(input, 'type'):
                elements[input.name] = input.getattr('value', '')
            elif input.type == 'image':
                continue
            elif input.type == 'button' and not include_button:
                continue
            elif input.type == 'submit' and not include_submit:
                continue
            elif input.type == 'file':
                elements[input.name] = Upload('')
            elif input.type in ['checkbox', 'radio']:
                l = elements.setdefault(input.name, {})
                key = input.hasattr('value') and input.value or input.name
                if input.hasattr('checked'):
                    l[key] = 'selected'
                else:
                    l[key] = ''
            elif input.type == 'submit':
                name = input.getattr('name', 'submit')
                if name == 'submit':
                    name = 'submit%s'%str(submits)
                    submits = submits + 1
                elements[name] = input.getattr('value', '')
            elif input.type == 'button':
                name = input.getattr('name', 'button')
                if name == 'button':
                    name = 'button%s'%str(buttons)
                    buttons = buttons + 1
                elements[name] = input.getattr('value', '')
            else:
                elements[input.name] = input.getattr('value', '')
        for textarea in form.getByName('textarea'):
            if len(textarea):
                elements[textarea.name] = textarea.getContentString()
            else:
                elements[textarea.name] = ''
        for input in form.getByName('select'):
            options = input.getByName('option')
            d = elements[input.name] = {}
            selected = first = None
            for option in options:
                if option.hasattr('value'):
                    key = option.value
                elif len(option) > 0:
                    key = option[0]
                else:
                    continue
                if first is None:
                    first = key
                if option.hasattr('selected'):
                    d[key] = 'selected'
                    selected = 1
                else: d[key] = ''
            if ((not input.hasattr('size') or input.size == 1)
                    and selected is None and first is not None):
                d[first] = 'selected'

        return elements

class SimpleDOMParser(HTMLParser):
    def __init__(self, debug=0):
        HTMLParser.__init__(self)
        self.tagstack = []
        self.__debug = debug

        #  DOM stuff
        self.content = self.dom = []
        self.stack = []

    def parseFile(self, file):
        f = open(file)
        data = f.read()
        f.close()
        self.parseString(data)

    def parseString(self, data):
        self.feed(data)
        self.close()
        while self.tagstack:
            self.implied_endtag(self.tagstack[-1], 2)

    def getDOM(self):
        return SimpleDOMNode('The Document', {}, self.dom)

    # Overriding HTMLParser methods

    def handle_starttag(self, tag, attrs):
        if self.__debug:
            print '\n>handle_starttag', tag
            print self.tagstack
        self.close_para_tags(tag)
        self.tagstack.append(tag)
        d = {}
        for k, v in attrs:
            d[string.lower(k)] = v
        self.emitStartElement(tag, d)
        if tag in EMPTY_HTML_TAGS:
            self.implied_endtag(tag, -1)

    def handle_startendtag(self, tag, attrs):
        if self.__debug:
            print '><handle_startendtag', tag
            print self.tagstack
        self.close_para_tags(tag)
        d = {}
        for k, v in attrs:
            d[string.lower(k)] = v
        self.emitStartElement(tag, d, isend=1)

    def handle_endtag(self, tag):
        if self.__debug:
            print '<handle_endtag', tag
            print self.tagstack
        if tag in EMPTY_HTML_TAGS:
            # </img> etc. in the source is an error
            raise EmptyTagError(tag, self.getpos())
        self.close_enclosed_tags(tag)
        self.emitEndElement(tag)
        self.tagstack.pop()

    def close_para_tags(self, tag):
        if tag in EMPTY_HTML_TAGS:
            return
        close_to = -1
        if BLOCK_CLOSING_TAG_MAP.has_key(tag):
            blocks_to_close = BLOCK_CLOSING_TAG_MAP[tag]
            for i in range(len(self.tagstack)):
                t = self.tagstack[i]
                if t in blocks_to_close:
                    if close_to == -1:
                        close_to = i
                elif t in BLOCK_LEVEL_HTML_TAGS:
                    close_to = -1
        elif tag in PARA_LEVEL_HTML_TAGS + BLOCK_LEVEL_HTML_TAGS:
            for i in range(len(self.tagstack)):
                if self.tagstack[i] in BLOCK_LEVEL_HTML_TAGS:
                    close_to = -1
                elif self.tagstack[i] in PARA_LEVEL_HTML_TAGS:
                    if close_to == -1:
                        close_to = i
        if close_to >= 0:
            while len(self.tagstack) > close_to:
                self.implied_endtag(self.tagstack[-1], 1)

    def close_enclosed_tags(self, tag):
        if tag not in self.tagstack:
            raise NestingError(self.tagstack, tag, self.getpos())
        while tag != self.tagstack[-1]:
            self.implied_endtag(self.tagstack[-1], 1)
        assert self.tagstack[-1] == tag

    def implied_endtag(self, tag, implied):
        if self.__debug:
            print '<implied_endtag', tag, implied
            print self.tagstack
        assert tag == self.tagstack[-1]
        assert implied in (-1, 1, 2)
        isend = (implied < 0)
        self.emitEndElement(tag, isend=isend, implied=implied)
        self.tagstack.pop()

    def handle_charref(self, name):
        self.emitText("&#%s;" % name)

    def handle_entityref(self, name):
        self.emitText("&%s;" % name)

    def handle_data(self, data):
        self.emitText(data)

    def handle_comment(self, data):
        self.emitText("<!--%s-->" % data)

    def handle_decl(self, data):
        self.emitText("<!%s>" % data)

    def handle_pi(self, data):
        self.emitText("<?%s>" % data)

    def emitStartTag(self, name, attrlist, isend=0):
        if isend:
            if self.__debug: print '*** content'
            self.content.append(SimpleDOMNode(name, attrlist, []))
        else:
            # generate a new scope and push the current one on the stack
            if self.__debug: print '*** push'
            newcontent = []
            self.stack.append(self.content)
            self.content.append(SimpleDOMNode(name, attrlist, newcontent))
            self.content = newcontent

    def emitEndTag(self, name):
        if self.__debug: print '*** pop'
        self.content = self.stack.pop()

    def emitText(self, text):
        self.content.append(text)

    def emitStartElement(self, name, attrlist, isend=0):
        # Handle the simple, common case
        self.emitStartTag(name, attrlist, isend)
        if isend:
            self.emitEndElement(name, isend)

    def emitEndElement(self, name, isend=0, implied=0):
        if not isend or implied:
            self.emitEndTag(name)


if __name__ == '__main__':
    tester = SimpleDOMParser(debug=0)
    tester.parseFile('/tmp/test.html')
    dom = tester.getDOM()
#    html = dom.getByNameFlat('html')[0]
#    body = html.getByNameFlat('body')[0]
#    table = body.getByNameFlat('table')[0]
#    tr = table.getByNameFlat('tr')[1]
#    td = tr.getByNameFlat('td')[2]
#    print td
    import pprint;pprint.pprint(dom)


########NEW FILE########
__FILENAME__ = utility
#
# Copyright (c) 2003 Richard Jones (http://mechanicalcat.net/richard)
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com/)
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
#
# See the README for full license details.
# 
# $Id: utility.py,v 1.3 2003/08/23 02:01:59 richard Exp $

import cStringIO
import os.path

class Upload:
    '''Simple "sentinel" class that lets us identify file uploads in POST
    data mappings.
    '''
    def __init__(self, filename):
        self.filename = filename
    def __cmp__(self, other):
        return cmp(self.filename, other.filename)

boundary = '--------------GHSKFJDLGDS7543FJKLFHRE75642756743254'
sep_boundary = '\n--' + boundary
end_boundary = sep_boundary + '--'

def mimeEncode(data, sep_boundary=sep_boundary, end_boundary=end_boundary):
    '''Take the mapping of data and construct the body of a
    multipart/form-data message with it using the indicated boundaries.
    '''
    ret = cStringIO.StringIO()
    for key, value in data.items():
        if not key:
            continue
        # handle multiple entries for the same name
        if type(value) != type([]): value = [value]
        for value in value:
            ret.write(sep_boundary)
            # if key starts with a '$' then the entry is a file upload
            if isinstance(value, Upload):
                ret.write('\nContent-Disposition: form-data; name="%s"'%key)
                ret.write('; filename="%s"\n\n'%value.filename)
                if value.filename:
                    value = open(os.path.join(value.filename), "rb").read()
                else:
                    value = ''
            else:
                ret.write('\nContent-Disposition: form-data; name="%s"'%key)
                ret.write("\n\n")
            ret.write(str(value))
            if value and value[-1] == '\r':
                ret.write('\n')  # write an extra newline
    ret.write(end_boundary)
    return ret.getvalue()

def log(message, content, logfile='logfile'):
    '''Log a single message to the indicated logfile
    '''
    logfile = open(logfile, 'a')
    logfile.write('\n>>> %s\n'%message)
    logfile.write(str(content) + '\n')
    logfile.close()

#
# $Log: utility.py,v $
# Revision 1.3  2003/08/23 02:01:59  richard
# fixes to cookie sending
#
# Revision 1.2  2003/07/22 01:19:22  richard
# patches
#
# Revision 1.1.1.1  2003/07/22 01:01:44  richard
#
#
# Revision 1.4  2002/02/25 02:59:09  rjones
# *** empty log message ***
#
# Revision 1.3  2002/02/22 06:24:31  rjones
# Code cleanup
#
# Revision 1.2  2002/02/13 01:16:56  rjones
# *** empty log message ***
#
#
# vim: set filetype=python ts=4 sw=4 et si


########NEW FILE########
__FILENAME__ = webunittest
#
# Copyright (c) 2003 Richard Jones (http://mechanicalcat.net/richard)
# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com/)
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
#
# See the README for full license details.
# 
# $Id: webunittest.py,v 1.12 2004/01/21 22:41:46 richard Exp $

import os, base64, urllib, urlparse, unittest, cStringIO, time, re, sys
import httplib

#try:
#    from M2Crypto import httpslib
#except ImportError:
#    httpslib = None

from SimpleDOM import SimpleDOMParser
from IMGSucker import IMGSucker
from utility import Upload, mimeEncode, boundary, log
import cookie

VERBOSE = os.environ.get('VERBOSE', '')

class HTTPError:
    '''Wraps a HTTP response that is not 200.

    url - the URL that generated the error
    code, message, headers - the information returned by httplib.HTTP.getreply()
    '''
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return 'ERROR: %s'%str(self.response)

class WebFetcher:
    '''Provide a "web client" class that handles fetching web pages.

       Handles basic authentication, HTTPS, detection of error content, ...
       Creates a HTTPResponse object on a valid response.
       Stores cookies received from the server.
    '''

    scheme_handlers = dict(http = httplib.HTTP,
                           https = httplib.HTTPS)
    
    def __init__(self):
        '''Initialise the server, port, authinfo, images and error_content
        attributes.
        '''
        self.protocol = 'http'
        self.server = '127.0.0.1'
        self.port = 80
        self.authinfo = ''
        self.url = None
        self.images = {}
        self.error_content = []
        self.expect_codes = [200, 301, 302]
        self.expect_content = None
        self.expect_cookies = None
        self.accept_cookies = 1
        self.cookies = {}

    result_count = 0

    def clearContext(self):
        self.authinfo = ''
        self.cookies = {}
        self.url = None
        self.images = {}

    def setServer(self, server, port):
        '''Set the server and port number to perform the HTTP requests to.
        '''
        self.server = server
        self.port = int(port)

    #
    # Authentication
    #
    def clearBasicAuth(self):
        '''Clear the current Basic authentication information
        '''
        self.authinfo = ''

    def setBasicAuth(self, username, password):
        '''Set the Basic authentication information to the given username
        and password.
        '''
        self.authinfo = base64.encodestring('%s:%s'%(username,
            password)).strip()

    #
    # cookie handling
    #
    def clearCookies(self):
        '''Clear all currently received cookies
        '''
        self.cookies = {}

    def setAcceptCookies(self, accept=1):
        '''Indicate whether to accept cookies or not
        '''
        self.accept_cookies = accept

    def registerErrorContent(self, content):
        '''Register the given string as content that should be considered a
        test failure (even though the response code is 200).
        '''
        self.error_content.append(content)

    def removeErrorContent(self, content):
        '''Remove the given string from the error content list.
        '''
        self.error_content.remove(content)

    def clearErrorContent(self):
        '''Clear the current list of error content strings.
        '''
        self.error_content = []

    def log(self, message, content):
        '''Log a message to the logfile
        '''
        log(message, content, 'logfile.'+self.server)

    #
    # Register cookies we expect to send to the server
    #
    def registerExpectedCookie(self, cookie):
        '''Register a cookie name that we expect to send to the server.
        '''
        if self.expect_cookies is None:
            self.expect_cookies = [cookie]
            return
        self.expect_cookies.append(cookie)
        self.expect_cookies.sort()

    def removeExpectedCookie(self, cookie):
        '''Remove the given cookie from the list of cookies we expect to
        send to the server.
        '''
        self.expect_cookies.remove(cookie)

    def clearExpectedCookies(self):
        '''Clear the current list of cookies we expect to send to the server.
        '''
        self.expect_cookies = None

    #
    # POST
    #
    def post(self, url, params, code=None, **kw):
        '''Perform a HTTP POST using the specified URL and form parameters.
        '''
        if code is None: code = self.expect_codes
        WebTestCase.result_count = WebTestCase.result_count + 1
        try:
            response = self.fetch(url, params, ok_codes=code, **kw)
        except HTTPError, error:
            self.log('post'+`(url, params)`, error.response.body)
            raise self.failureException, str(error.response)
        return response

    def postAssertCode(self, url, params, code=None, **kw):
        '''Perform a HTTP POST and assert that the return code from the
        server is one of the indicated codes.
        '''
        if code is None: code = self.expect_codes
        WebTestCase.result_count = WebTestCase.result_count + 1
        if type(code) != type([]):
            code = [code]
        try:
            response = self.fetch(url, params, ok_codes = code, **kw)
        except HTTPError, error:
            self.log('postAssertCode'+`(url, params, code)`,
                error.response.body)
            raise self.failureException, str(error.response)
        return response

    def postAssertContent(self, url, params, content, code=None, **kw):
        '''Perform a HTTP POST and assert that the data returned from the
        server contains the indicated content string.
        '''
        if code is None: code = self.expect_codes
        WebTestCase.result_count = WebTestCase.result_count + 1
        if type(code) != type([]):
            code = [code]
        try:
            response = self.fetch(url, params, ok_codes = code, **kw)
        except HTTPError, error:
            self.log('postAssertContent'+`(url, params, code)`,
                error.response.body)
            raise self.failureException, str(error)
        if response.body.find(content) == -1:
            self.log('postAssertContent'+`(url, params, content)`,
                response.body)
            raise self.failureException, 'Expected content not in response'
        return response

    def postAssertNotContent(self, url, params, content, code=None, **kw):
        '''Perform a HTTP POST and assert that the data returned from the
        server doesn't contain the indicated content string.
        '''
        if code is None: code = self.expect_codes
        WebTestCase.result_count = WebTestCase.result_count + 1
        if type(code) != type([]):
            code = [code]
        try:
            response = self.fetch(url, params, ok_codes = code, **kw)
        except HTTPError, error:
            self.log('postAssertNotContent'+`(url, params, code)`,
                error.response.body)
            raise self.failureException, str(error)
        if response.body.find(content) != -1:
            self.log('postAssertNotContent'+`(url, params, content)`,
                response.body)
            raise self.failureException, 'Expected content was in response'
        return response

    def postPage(self, url, params, code=None, **kw):
        '''Perform a HTTP POST using the specified URL and form parameters
        and then retrieve all image and linked stylesheet components for the
        resulting HTML page.
        '''
        if code is None: code = self.expect_codes
        WebTestCase.result_count = WebTestCase.result_count + 1
        try:
            response = self.fetch(url, params, ok_codes=code, **kw)
        except HTTPError, error:
            self.log('postPage %r'%((url, params),), error.response.body)
            raise self.failureException, str(error)

        # Check return code for redirect
        while response.code in (301, 302):
            try:
                # Figure the location - which may be relative
                newurl = response.headers['Location']
                url = urlparse.urljoin(url, newurl)
                response = self.fetch(url, ok_codes=code)
            except HTTPError, error:
                self.log('postPage %r'%url, error.response.body)
                raise self.failureException, str(error)

        # read and parse the content
        page = response.body
        if hasattr(self, 'results') and self.results:
            self.writeResult(url, page)
        try:
            self.pageImages(url, page)
        except HTTPError, error:
            raise self.failureException, str(error)
        return response

    #
    # GET
    #
    def assertCode(self, url, code=None, **kw):
        '''Perform a HTTP GET and assert that the return code from the
        server one of the indicated codes.
        '''
        if code is None: code = self.expect_codes
        return self.postAssertCode(url, None, code=code, **kw)
    get = getAssertCode = assertCode

    def assertContent(self, url, content, code=None, **kw):
        '''Perform a HTTP GET and assert that the data returned from the
        server contains the indicated content string.
        '''
        if code is None: code = self.expect_codes
        return self.postAssertContent(url, None, content, code)
    getAssertContent = assertContent

    def assertNotContent(self, url, content, code=None, **kw):
        '''Perform a HTTP GET and assert that the data returned from the
        server contains the indicated content string.
        '''
        if code is None: code = self.expect_codes
        return self.postAssertNotContent(url, None, content, code)
    getAssertNotContent = assertNotContent

    def page(self, url, code=None, **kw):
        '''Perform a HTTP GET using the specified URL and then retrieve all
        image and linked stylesheet components for the resulting HTML page.
        '''
        if code is None: code = self.expect_codes
        WebTestCase.result_count = WebTestCase.result_count + 1
        return self.postPage(url, None, code=code, **kw)

    def get_base_url(self):
        # try to get a <base> tag and use that to root the URL on
        if hasattr(self, 'getDOM'):
            base = self.getDOM().getByName('base')
            if base:
                # <base href="">
                return base[0].href
        if self.url is not None:
            # join the request URL with the "current" URL
            return self.url
        return None

    #
    # The function that does it all
    #
    def fetch(self, url, postdata=None, server=None, port=None, protocol=None,
                    ok_codes=None):
        '''Run a single test request to the indicated url. Use the POST data
        if supplied.

        Raises failureException if the returned data contains any of the
        strings indicated to be Error Content.
        Returns a HTTPReponse object wrapping the response from the server.
        '''
        # see if the url is fully-qualified (not just a path)
        t_protocol, t_server, t_url, x, t_args, x = urlparse.urlparse(url)
        if t_server:
            protocol = t_protocol
            if ':' in t_server:
                server, port = t_server.split(':')
            else:
                server = t_server
                if protocol == 'http':
                    port = '80'
                else:
                    port = '443'
            url = t_url
            if t_args:
                url = url + '?' + t_args
            # ignore the machine name if the URL is for localhost
            if t_server == 'localhost':
                server = None
        elif not server:
            # no server was specified with this fetch, or in the URL, so
            # see if there's a base URL to use.
            base = self.get_base_url()
            if base:
                t_protocol, t_server, t_url, x, x, x = urlparse.urlparse(base)
                if t_protocol:
                    protocol = t_protocol
                if t_server:
                    server = t_server
                if t_url:
                    url = urlparse.urljoin(t_url, url)

        # TODO: allow override of the server and port from the URL!
        if server is None: server = self.server
        if port is None: port = self.port
        if protocol is None: protocol = self.protocol
        if ok_codes is None: ok_codes = self.expect_codes

        if protocol == 'http':
            handler = self.scheme_handlers.get('http')
            h = handler(server, int(port))

            if int(port) == 80:
               host_header = server
            else: 
               host_header = '%s:%s'%(server, port)
        elif protocol == 'https':
            #if httpslib is None:
                #raise ValueError, "Can't fetch HTTPS: M2Crypto not installed"
            handler = self.scheme_handlers.get('https')
            h = handler(server, int(port))
            
            if int(port) == 443:
               host_header = server
            else: 
               host_header = '%s:%s'%(server, port)
        else:
            raise ValueError, protocol

        params = None
        if postdata:
            for field,value in postdata.items():
                if type(value) == type({}):
                    postdata[field] = []
                    for k,selected in value.items():
                        if selected: postdata[field].append(k)

            # Do a post with the data file
            params = mimeEncode(postdata)
            h.putrequest('POST', url)
            h.putheader('Content-type', 'multipart/form-data; boundary=%s'%
                boundary)
            h.putheader('Content-length', str(len(params)))
        else:
            # Normal GET
            h.putrequest('GET', url)

        # Other Full Request headers
        if self.authinfo:
            h.putheader('Authorization', "Basic %s"%self.authinfo)
        h.putheader('Host', host_header)

        # Send cookies
        #  - check the domain, max-age (seconds), path and secure
        #    (http://www.ietf.org/rfc/rfc2109.txt)
        cookies_used = []
        cookie_list = []
        for domain, cookies in self.cookies.items():
            # check cookie domain
            if not server.endswith(domain):
                continue
            for path, cookies in cookies.items():
                # check that the path matches
                urlpath = urlparse.urlparse(url)[2]
                if not urlpath.startswith(path) and not (path == '/' and
                        urlpath == ''):
                    continue
                for sendcookie in cookies.values():
                    # and that the cookie is or isn't secure
                    if sendcookie['secure'] and protocol != 'https':
                        continue
                    # TODO: check max-age
                    cookie_list.append("%s=%s;"%(sendcookie.key,
                        sendcookie.coded_value))
                    cookies_used.append(sendcookie.key)

        if cookie_list:
            h.putheader('Cookie', ' '.join(cookie_list))

        # check that we sent the cookies we expected to
        if self.expect_cookies is not None:
            assert cookies_used == self.expect_cookies, \
                "Didn't use all cookies (%s expected, %s used)"%(
                self.expect_cookies, cookies_used)

        # finish the headers
        h.endheaders()

        if params is not None:
            h.send(params)

        # handle the reply
        errcode, errmsg, headers = h.getreply()

        # get the body and save it
        f = h.getfile()
        g = cStringIO.StringIO()
        d = f.read()
        while d:
            g.write(d)
            d = f.read()
        response = HTTPResponse(self.cookies, protocol, server, port, url,
            errcode, errmsg, headers, g.getvalue(), self.error_content)
        f.close()

        if errcode not in ok_codes:
            if VERBOSE:
                sys.stdout.write('e')
                sys.stdout.flush()
            raise HTTPError(response)

        # decode the cookies
        if self.accept_cookies:
            try:
                # decode the cookies and update the cookies store
                cookie.decodeCookies(url, server, headers, self.cookies)
            except:
                if VERBOSE:
                    sys.stdout.write('c')
                    sys.stdout.flush()
                raise

        # Check errors
        if self.error_content:
            data = response.body
            for content in self.error_content:
                if data.find(content) != -1:
                    msg = "Matched error: %s"%content
                    if hasattr(self, 'results') and self.results:
                        self.writeError(url, msg)
                    self.log('Matched error'+`(url, content)`, data)
                    if VERBOSE:
                        sys.stdout.write('c')
                        sys.stdout.flush()
                    raise self.failureException, msg

        if VERBOSE:
            sys.stdout.write('_')
            sys.stdout.flush()
        return response

    def pageImages(self, url, page):
        '''Given the HTML page that was loaded from url, grab all the images.
        '''
        sucker = IMGSucker(url, self)
        sucker.feed(page)
        sucker.close()


class WebTestCase(WebFetcher, unittest.TestCase):
    '''Extend the standard unittest TestCase with some HTTP fetching and
    response testing functions.
    '''
    def __init__(self, methodName='runTest'):
        '''Initialise the server, port, authinfo, images and error_content
        attributes.
        '''
        unittest.TestCase.__init__(self, methodName=methodName)
        WebFetcher.__init__(self)


class HTTPResponse(WebFetcher, unittest.TestCase):
    '''Wraps a HTTP response.

    protocol, server, port, url - the request server and URL
    code, message, headers - the information returned by httplib.HTTP.getreply()
    body - the response body returned by httplib.HTTP.getfile()
    '''
    def __init__(self, cookies, protocol, server, port, url, code, message,
            headers, body, error_content=[]):
        WebFetcher.__init__(self)
        # single cookie store per test
        self.cookies = cookies

        self.error_content = error_content[:]

        # this is the request that generated this response
        self.protocol = protocol
        self.server = server
        self.port = port
        self.url = url

        # info about the response
        self.code = code
        self.message = message
        self.headers = headers
        self.body = body
        self.dom = None

    def __str__(self):
        return '%s\nHTTP Response %s: %s'%(self.url, self.code, self.message)

    def getDOM(self):
        '''Get a DOM for this page
        '''
        if self.dom is None:
            parser = SimpleDOMParser()
            try:
                parser.parseString(self.body)
            except:
                log('HTTPResponse.getDOM'+`(self.url, self.code, self.message,
                    self.headers)`, self.body)
                raise
            self.dom = parser.getDOM()
        return self.dom

    def extractForm(self, path=[], include_submit=0, include_button=0):
        '''Extract a form (as a dictionary) from this page.

        The "path" is a list of 2-tuples ('element name', index) to follow
        to find the form. So:
         <html><head>..</head><body>
          <p><form>...</form></p>
          <p><form>...</form></p>
         </body></html>

        To extract the second form, any of these could be used:
         [('html',0), ('body',0), ('p',1), ('form',0)]
         [('form',1)]
         [('p',1)]
        '''
        return self.getDOM().extractElements(path, include_submit,
            include_button)

    def getForm(self, formnum, getmethod, postargs, *args):
        '''Given this page, extract the "formnum"th form from it, fill the
           form with the "postargs" and post back to the server using the
           "postmethod" with additional "args".

           NOTE: the form submission will include any "default" values from
           the form extracted from this page. To "remove" a value from the
           form, just pass a value None for the elementn and it will be
           removed from the form submission.

           example WebTestCase:
             page = self.get('/foo')
             page.getForm(0, self.post, {'name': 'blahblah',
                     'password': 'foo'})

           or the slightly more complex:
             page = self.get('/foo')
             page.getForm(0, self.assertContent, {'name': 'blahblah',
                     'password': None}, 'password incorrect')
        '''
        formData, url = self.getFormData(formnum, postargs)

        # whack on the url params
        l = []
        for k, v in formData.items():
            if isinstance(v, type([])):
                for item in v:
                    l.append('%s=%s'%(urllib.quote(k), 
                        urllib.quote_plus(item, safe='')))
            else:
                l.append('%s=%s'%(urllib.quote(k),
                    urllib.quote_plus(v, safe='')))
        if l:
            url = url + '?' + '&'.join(l)

        # make the post
        return getmethod(url, *args)

    def postForm(self, formnum, postmethod, postargs, *args):
        '''Given this page, extract the "formnum"th form from it, fill the
           form with the "postargs" and post back to the server using the
           "postmethod" with additional "args".

           NOTE: the form submission will include any "default" values from
           the form extracted from this page. To "remove" a value from the
           form, just pass a value None for the elementn and it will be
           removed from the form submission.

           example WebTestCase:
             page = self.get('/foo')
             page.postForm(0, self.post, {'name': 'blahblah',
                     'password': 'foo'})

           or the slightly more complex:
             page = self.get('/foo')
             page.postForm(0, self.postAssertContent, {'name': 'blahblah',
                     'password': None}, 'password incorrect')
        '''
        formData, url = self.getFormData(formnum, postargs)

        # make the post
        return postmethod(url, formData, *args)
  
    def getFormData(self, formnum, postargs={}):
        ''' Postargs are in the same format as the data returned by the
            SimpleDOM extractElements() method, and they are merged with
            the existing form data.
        '''
        dom = self.getDOM()
        form = dom.getByName('form')[formnum]
        formData = form.extractElements()

        # Make sure all the postargs are present in the form:
# TODO this test needs to be switchable, as it barfs when you explicitly
# identify a submit button in the form - the existing form data doesn't
# have submit buttons in it
#        for k in postargs.keys():
#            assert formData.has_key(k), (formData, k)

        formData.update(postargs)
        for k,v in postargs.items():
            if v is None:
                del formData[k]

        # transmogrify select/checkbox/radio select options from dicts
        # (key:'selected') to lists of values
        for k,v in formData.items():
            if isinstance(v, type({})):
                l = []
                for kk,vv in v.items():
                    if vv in ('selected', 'checked'):
                        l.append(kk)
                formData[k] = l
 
        if form.hasattr('action'):
            url = form.action
            base = self.get_base_url()
            if not url or url == '.':
                if base and base[0].hasattr('href'):
                    url = base[0].href
                elif self.url.endswith('/'):
                    url = self.url
                elif self.url.startswith('http') or self.url.startswith('/'):
                    url = '%s/' % '/'.join(self.url.split('/')[:-1])
                else:
                    url = '/%s/' % '/'.join(self.url.split('/')[:-1])

            elif not (url.startswith('/') or url.startswith('http')):
                url = urlparse.urljoin(base, url)
        else:
            url = self.url

        return formData, url

#
# $Log: webunittest.py,v $
# Revision 1.12  2004/01/21 22:41:46  richard
# *** empty log message ***
#
# Revision 1.11  2004/01/20 23:59:39  richard
# *** empty log message ***
#
# Revision 1.10  2003/11/06 06:50:29  richard
# *** empty log message ***
#
# Revision 1.9  2003/11/03 05:11:17  richard
# *** empty log message ***
#
# Revision 1.5  2003/10/08 05:37:32  richard
# fixes
#
# Revision 1.4  2003/08/23 02:01:59  richard
# fixes to cookie sending
#
# Revision 1.3  2003/08/22 00:46:29  richard
# much fixes
#
# Revision 1.2  2003/07/22 01:19:22  richard
# patches
#
# Revision 1.1.1.1  2003/07/22 01:01:44  richard
#
#
# Revision 1.11  2002/02/27 03:00:08  rjones
# more tests, bugfixes
#
# Revision 1.10  2002/02/26 03:14:41  rjones
# more tests
#
# Revision 1.9  2002/02/25 02:58:47  rjones
# *** empty log message ***
#
# Revision 1.8  2002/02/22 06:24:31  rjones
# Code cleanup
#
# Revision 1.7  2002/02/22 04:15:34  rjones
# web test goodness
#
# Revision 1.6  2002/02/13 04:32:50  rjones
# *** empty log message ***
#
# Revision 1.5  2002/02/13 04:24:42  rjones
# *** empty log message ***
#
# Revision 1.4  2002/02/13 02:21:59  rjones
# *** empty log message ***
#
# Revision 1.3  2002/02/13 01:48:23  rjones
# *** empty log message ***
#
# Revision 1.2  2002/02/13 01:16:56  rjones
# *** empty log message ***
#
#
# vim: set filetype=python ts=4 sw=4 et si


########NEW FILE########
__FILENAME__ = wsgi_testbrowser
"""
A zope.testbrowser-style Web browser interface that redirects specified
connections to a WSGI application.
"""

from mechanize import Browser as MechanizeBrowser
from wsgi_intercept.mechanize_intercept import Browser as InterceptBrowser
from zope.testbrowser.browser import Browser as ZopeTestbrowser
from httplib import HTTP
import sys, os.path        

class WSGI_Browser(ZopeTestbrowser):
    """
    Override the zope.testbrowser.browser.Browser interface so that it
    uses PatchedMechanizeBrowser 
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['mech_browser'] = InterceptBrowser()
        ZopeTestbrowser.__init__(self, *args, **kwargs)

########NEW FILE########
__FILENAME__ = fakeofx
#!/usr/bin/env python

# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# fakeofx.py - a quick and ugly hack to generate fake OFX for testing
#

import os
import os.path
import sys

def fixpath(filename):
    mypath = os.path.dirname(sys._getframe(1).f_code.co_filename)
    return os.path.normpath(os.path.join(mypath, filename))

sys.path.insert(0, '3rdparty')
sys.path.insert(0, 'lib')

from datetime import date
from datetime import timedelta
import ofx
from optparse import OptionParser
import random

def generate_amt(base_amt):
    return random.uniform((base_amt * 0.6), (base_amt * 1.4))

# How long should this statement be?

days = 90
end_date = date.today()

# How much spending should the statement represent?

income = 85000
take_home_pay = income * .6
paycheck_amt = "%.02f" % (take_home_pay / 26)
daily_income = take_home_pay / 365

# Assume that people spend their whole income.  At least.

total_spending = daily_income * days

# How do people usually spend their money?  Taken from
# http://www.billshrink.com/blog/consumer-income-spending/
# The fees number is made up, but seemed appropriate.

spending_pcts = \
    { "food":          0.101,
      "housing":       0.278,
      "utility":       0.056,
      "clothing":      0.031,
      "auto":          0.144,
      "health":        0.047,
      "entertainment": 0.044,
      "gift":         0.020,
      "education":     0.016,
      "fee":           0.026 }

# How much do people spend per transaction?  This is taken from
# the tag_summaries table in the live database.

avg_txn_amts = \
    { "auto":          -70.77,
      "clothing":      -58.31,
      "education":     -62.64,
      "entertainment": -30.10,
      "fee":           -20.95,
      "food":          -25.52,
      "gift":          -18.84,
      "health":        -73.05,
      "mortgage":      -1168.49,
      "rent":          -643.30,
      "utility":       -90.81 }

# For now, just throw in some merchant names for each tag. Later
# this should come from the merchant_summaries table.

top_merchants = \
    { "auto":          ["Chevron", "Jiffy Lube", "Union 76", "Arco", "Shell", "Pep Boys"],
      "clothing":      ["Nordstrom", "Banana Republic", "Macy's", "The Gap", "Kenneth Cole", "J. Crew"],
      "education":     ["Tuition", "Amazon.com", "Registration", "The Crucible", "Campus Books"],
      "entertainment": ["AMC Theaters", "Amazon.com", "Netflix", "iTunes Music Store", "Rhapsody", "Metreon Theaters"],
      "fee":           ["Bank Fee", "Overlimit Fee", "Late Fee", "Interest Fee", "Monthly Fee", "Annual Fee"],
      "food":          ["Safeway", "Starbucks", "In-N-Out Burger", "Trader Joe's", "Whole Foods", "Olive Garden"],
      "gift":          ["Amazon.com", "Nordstrom", "Neiman-Marcus", "Apple Store", "K&L Wines"],
      "health":        ["Dr. Phillips", "Dr. Jackson", "Walgreen's", "Wal-Mart", "Dr. Roberts", "Dr. Martins"],
      "mortgage":      ["Mortgage Payment"],
      "rent":          ["Rent Payment"],
      "utility":       ["AT&T", "Verizon", "PG&E", "Comcast", "Brinks", ""] }

# Choose a random account type.
accttype = random.choice(['CHECKING', 'CREDITCARD'])

if accttype == "CREDITCARD":
    # Make up a random 16-digit credit card number with a standard prefix.
    acctid = "9789" + str(random.randint(000000000000, 999999999999))
    
    # Credit card statements don't use bankid.
    bankid = None
    
    # Make up a negative balance.
    balance = "%.02f" % generate_amt(-5000)
    
else:
    # Make up a random 8-digit account number.
    acctid = random.randint(10000000, 99999999)
    
    # Use a fake bankid so it's easy to find fake OFX uploads.
    bankid = "987987987"
    
    # Make up a positive balance.
    balance = "%.02f" % generate_amt(1000)

def generate_transaction(stmt, tag, type, date=None):
    if date is None:
        days_ago = timedelta(days=random.randint(0, days))
        date = (end_date - days_ago).strftime("%Y%m%d")
    
    amount = generate_amt(avg_txn_amts[tag])
    txn_amt = "%.02f" % amount
    
    merchant = random.choice(top_merchants[tag])
    
    stmt.add_transaction(date=date, amount=txn_amt, payee=merchant, type=type)
    return amount


stmt = ofx.Generator(fid="9789789", org="FAKEOFX", acctid=acctid, accttype=accttype, 
                     bankid=bankid, availbal=balance, ledgerbal=balance)

tags = spending_pcts.keys()
tags.remove("housing")

if accttype == "CREDITCARD":
    # Add credit card payments

    payment_days_ago = 0

    while payment_days_ago < days:
        payment_days_ago += 30
        payment_amt = "%.02f" % generate_amt(1000)
        paymentday = (end_date - timedelta(days=payment_days_ago)).strftime("%Y%m%d")
        stmt.add_transaction(date=paymentday, amount=payment_amt, payee="Credit Card Payment", type="PAYMENT")
    
elif accttype == "CHECKING":
    # First deal with income

    pay_days_ago = 0

    while pay_days_ago < days:
        pay_days_ago += 15
        payday = (end_date - timedelta(days=pay_days_ago)).strftime("%Y%m%d")
        stmt.add_transaction(date=payday, amount=paycheck_amt, payee="Payroll", type="DEP")

    # Then deal with housing

    housing_tag = random.choice(["rent", "mortgage"])

    housing_days_ago = 0

    while housing_days_ago < days:
        housing_days_ago += 30
        last_housing = (end_date - timedelta(days=housing_days_ago)).strftime("%Y%m%d")
        amount = generate_transaction(stmt, housing_tag, "DEBIT")
        total_spending -= abs(amount)

# Now deal with the rest of the tags

for tag in tags:
    tag_spending = total_spending * spending_pcts[tag]
    while tag_spending > 0 and total_spending > 0:
        amount = generate_transaction(stmt, tag, "DEBIT")
        tag_spending   -= abs(amount)
        total_spending -= abs(amount)

print stmt

########NEW FILE########
__FILENAME__ = fixofx
#!/usr/bin/env python

# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# fixofx.py - canonicalize all recognized upload formats to OFX 2.0
#

import os
import os.path
import sys

def fixpath(filename):
    mypath = os.path.dirname(sys._getframe(1).f_code.co_filename)
    return os.path.normpath(os.path.join(mypath, filename))

sys.path.insert(0, fixpath('3rdparty'))
sys.path.insert(0, fixpath('lib'))

import ofx
import ofxtools
from optparse import OptionParser
from pyparsing import ParseException

__doc__ = \
"""Canonicalizes files from several supported data upload formats (currently
OFX 1.02, OFX 1.5, OFX 1.6, OFX 2.0, OFC, and QIF) to OFX 2.0 (which is a
standard XML 1.0 file). Since it is easiest for the database loader to use a
single, XML-based format, and since users might prefer an XML document to OFX
1.02 or other formats for export, this script essentially removes the need for
any other code to know about all of the variations in data formats. By
default, the converter will read a single file of any supported format from
standard input and write the converted OFX 2.0 file to standard output. A
command line option also allows reading a single file, and other options allow
you to insert data into the output file not available in the source file (for
instance, QIF does not contain the account number, so an option allows you to
specify that for insertion into the OFX output)."""

# Import Psyco if available, for speed.
try:
    import psyco
    psyco.full()

except ImportError:
    pass


def convert(text, filetype, verbose=False, fid="UNKNOWN", org="UNKNOWN", 
            bankid="UNKNOWN", accttype="UNKNOWN", acctid="UNKNOWN",
            balance="UNKNOWN", curdef=None, lang="ENG", dayfirst=False, 
            debug=False):
    
    # This finishes a verbosity message started by the caller, where the
    # caller explains the source command-line option and this explains the
    # source format.
    if verbose: 
        sys.stderr.write("Converting from %s format.\n" % filetype)

    if options.debug and (filetype in ["OFC", "QIF"] or filetype.startswith("OFX")):
        sys.stderr.write("Starting work on raw text:\n")
        sys.stderr.write(rawtext + "\n\n")
    
    if filetype.startswith("OFX/2"):
        if verbose: sys.stderr.write("No conversion needed; returning unmodified.\n")
        
        # The file is already OFX 2 -- return it unaltered, ignoring
        # any of the parameters passed to this method.
        return text
    
    elif filetype.startswith("OFX"):
        if verbose: sys.stderr.write("Converting to OFX/2.0...\n")
        
        # This will throw a ParseException if it is unable to recognize
        # the source format.
        response = ofx.Response(text, debug=debug)        
        return response.as_xml(original_format=filetype)
    
    elif filetype == "OFC":
        if verbose: sys.stderr.write("Beginning OFC conversion...\n")
        converter = ofxtools.OfcConverter(text, fid=fid, org=org, curdef=curdef,
                                          lang=lang, debug=debug)
        
        # This will throw a ParseException if it is unable to recognize
        # the source format.
        if verbose: 
            sys.stderr.write("Converting to OFX/1.02...\n\n%s\n\n" %
                             converter.to_ofx102())
            sys.stderr.write("Converting to OFX/2.0...\n")
                                             
        return converter.to_xml()
    
    elif filetype == "QIF":
        if verbose: sys.stderr.write("Beginning QIF conversion...\n")
        converter = ofxtools.QifConverter(text, fid=fid, org=org,
                                          bankid=bankid, accttype=accttype, 
                                          acctid=acctid, balance=balance, 
                                          curdef=curdef, lang=lang, dayfirst=dayfirst,
                                          debug=debug)
        
        # This will throw a ParseException if it is unable to recognize
        # the source format.
        if verbose: 
            sys.stderr.write("Converting to OFX/1.02...\n\n%s\n\n" %
                             converter.to_ofx102())
            sys.stderr.write("Converting to OFX/2.0...\n")
                                             
        return converter.to_xml()
    
    else:
        raise TypeError("Unable to convert source format '%s'." % filetype)

parser = OptionParser(description=__doc__)
parser.add_option("-d", "--debug", action="store_true", dest="debug",
                  default=False, help="spit out gobs of debugging output during parse")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                  default=False, help="be more talkative, social, outgoing")
parser.add_option("-t", "--type", action="store_true", dest="type",
                  default=False, help="print input file type and exit")
parser.add_option("-f", "--file", dest="filename", default=None,
                  help="source file to convert (writes to STDOUT)")
parser.add_option("--fid", dest="fid", default="UNKNOWN",
                  help="(OFC/QIF only) FID to use in output")
parser.add_option("--org", dest="org", default="UNKNOWN",
                  help="(OFC/QIF only) ORG to use in output")
parser.add_option("--curdef", dest="curdef", default=None,
                  help="(OFC/QIF only) Currency identifier to use in output")
parser.add_option("--lang", dest="lang", default="ENG",
                  help="(OFC/QIF only) Language identifier to use in output")
parser.add_option("--bankid", dest="bankid", default="UNKNOWN",
                  help="(QIF only) Routing number to use in output")
parser.add_option("--accttype", dest="accttype", default="UNKNOWN",
                  help="(QIF only) Account type to use in output")
parser.add_option("--acctid", dest="acctid", default="UNKNOWN",
                  help="(QIF only) Account number to use in output")
parser.add_option("--balance", dest="balance", default="UNKNOWN",
                  help="(QIF only) Account balance to use in output")
parser.add_option("--dayfirst", action="store_true", dest="dayfirst", default=False,
                  help="(QIF only) Parse dates day first (UK format)")
(options, args) = parser.parse_args()

#
# Check the python environment for minimum sanity levels.
#

if options.verbose and not hasattr(open, 'newlines'):
    # Universal newlines are generally needed to deal with various QIF downloads.
    sys.stderr.write('Warning: universal newline support NOT available.\n')

if options.verbose: print "Options: %s" % options

#
# Load up the raw text to be converted.
#

rawtext = None

if options.filename:
    if os.path.isfile(options.filename):
        if options.verbose: 
            sys.stderr.write("Reading from '%s'\n." % options.filename)
        
        try:
            srcfile = open(options.filename, 'rU')
            rawtext = srcfile.read()
            srcfile.close()
        except StandardError, detail:
            print "Exception during file read:\n%s" % detail
            print "Exiting."
            sys.stderr.write("fixofx failed with error code 1\n")
            sys.exit(1)
        
    else:
        print "'%s' does not appear to be a file.  Try --help." % options.filename
        sys.stderr.write("fixofx failed with error code 2\n")
        sys.exit(2)

else:
    if options.verbose: 
        sys.stderr.write("Reading from standard input.\n")
    
    stdin_universal = os.fdopen(os.dup(sys.stdin.fileno()), "rU")
    rawtext = stdin_universal.read()
    
    if rawtext == "" or rawtext is None:
        print "No input.  Pipe a file to convert to the script,\n" + \
              "or call with -f.  Call with --help for more info."
        sys.stderr.write("fixofx failed with error code 3\n")
        sys.exit(3)

#
# Convert the raw text to OFX 2.0.
#

try:
    # Determine the type of file contained in 'text', using a quick guess
    # rather than parsing the file to make sure.  (Parsing will fail
    # below if the guess is wrong on OFX/1 and QIF.)
    filetype  = ofx.FileTyper(rawtext).trust()
    
    if options.type:
        print "Input file type is %s." % filetype
        sys.exit(0)
    elif options.debug:
        sys.stderr.write("Input file type is %s.\n" % filetype)
    
    converted = convert(rawtext, filetype, verbose=options.verbose, 
                        fid=options.fid, org=options.org, bankid=options.bankid, 
                        accttype=options.accttype, acctid=options.acctid, 
                        balance=options.balance, curdef=options.curdef,
                        lang=options.lang, dayfirst=options.dayfirst,
                        debug=options.debug)
    print converted
    sys.exit(0)

except ParseException, detail:
    print "Parse exception during '%s' conversion:\n%s" % (filetype, detail)
    print "Exiting."
    sys.stderr.write("fixofx failed with error code 4\n")
    sys.exit(4)

except TypeError, detail:
    print detail
    print "Exiting."
    sys.stderr.write("fixofx failed with error code 5\n")
    sys.exit(5)

########NEW FILE########
__FILENAME__ = account
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# ofx.account - container for information about a bank or credit card account.
#

import ofx

class Account:
    def __init__(self, acct_type="", acct_number="", aba_number="",
                 balance=None, desc=None, institution=None, ofx_block=None):
        self.balance     = balance
        self.desc        = desc
        self.institution = institution

        if ofx_block is not None:
            self.acct_type   = self._get_from_ofx(ofx_block, "ACCTTYPE")
            self.acct_number = self._get_from_ofx(ofx_block, "ACCTID")
            self.aba_number  = self._get_from_ofx(ofx_block, "BANKID")
        else:
            self.acct_type   = acct_type
            self.acct_number = acct_number
            self.aba_number  = aba_number

    def _get_from_ofx(self, data, key):
        data_dict = data.asDict()
        return data_dict.get(key, "")

    def get_ofx_accttype(self):
        # FIXME: I nominate this for the stupidest method in the Uploader.

        # OFX requests need to have a the account type match one of a few
        # known types.  This converts from the "display" version of the
        # type to the one OFX servers will recognize.
        if self.acct_type == "Checking" or self.acct_type == "CHECKING":
            return "CHECKING"
        elif self.acct_type == "Savings" or self.acct_type == "SAVINGS":
            return "SAVINGS"
        elif self.acct_type == "Credit Card" or self.acct_type == "CREDITCARD":
            return "CREDITCARD"
        elif self.acct_type == "Money Market" or self.acct_type == "MONEYMRKT"\
        or self.acct_type == "MONEYMARKT":
            return "MONEYMRKT"
        elif self.acct_type == "Credit Line" or self.acct_type == "CREDITLINE":
            return "CREDITLINE"
        else:
            return self.acct_type

    def is_complete(self):
        if self.institution is None:
            return False
        elif self.acct_type != "" and self.acct_number != "":
            if self.get_ofx_accttype() == "CREDITCARD":
                return True
            else:
                return self.aba_number != ""
        else:
            return False

    def is_equal(self, other):
        if self.acct_type == other.acct_type   and \
        self.acct_number  == other.acct_number and \
        self.aba_number   == other.aba_number:
            return True
        else:
            return False

    def to_s(self):
        return ("Account: %s; Desc: %s; Type: %s; ABA: %s; Institution: %s") % \
                (self.acct_number, self.desc, self.acct_type,
                 self.aba_number, self.broker_id, self.institution)

    def __repr__(self):
        return self.to_s()

    def as_dict(self):
        acct_dict = { 'acct_number' : self.acct_number,
                      'acct_type'   : self.get_ofx_accttype(),
                      'aba_number'  : self.aba_number,
                      'balance'     : self.balance,
                      'desc'        : self.desc }
        if self.institution is not None:
            acct_dict['institution'] = self.institution.as_dict()
        return acct_dict

    def load_from_dict(acct_dict):
        return ofx.Account(acct_type=acct_dict.get('acct_type'),
                           acct_number=acct_dict.get('acct_number'),
                           aba_number=acct_dict.get('aba_number'),
                           balance=acct_dict.get('balance'),
                           desc=acct_dict.get('desc'))
    load_from_dict = staticmethod(load_from_dict)



########NEW FILE########
__FILENAME__ = builder
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.builder - OFX document generator with focus on clean generation code.
#

"""
Builder of OFX message documents.  This module exposes a large set of
instances that are called as methods to generate an OFX document
component using the name of the instance.  Example usage:

    import ofx

    request = MESSAGE(
        HEADER(
            OFXHEADER("100"),
            DATA("OFXSGML"),
            VERSION("102"),
            SECURITY("NONE"),
            ENCODING("USASCII"),
            CHARSET("1252"),
            COMPRESSION("NONE"),
            OLDFILEUID("NONE"),
            NEWFILEUID("9B33CA3E-C237-4577-8F00-7AFB0B827B5E")),
        OFX(
            SIGNONMSGSRQV1(),
            # ... other OFX message components here ...
"""

# FIXME: This supports OFX 1.02.  Make something that supports OFX 2.0.

# REVIEW: This class is pretty hackish, and it's not easy to maintain
# (you have to add new tags in a few different places). However, it works,
# and it has a reasonable test suite, so I'm leaving it alone for now.
# I do need to have a way of generating OFX 2.0, and that will probably
# be the next major addition to the class.

class Tag:
    ofx1 = "OFX/1.0"
    ofx2 = "OFX/2.0"
    output = ofx1

    def _output_version(cls, version=ofx1):
        cls.output = version

    def __init__(self, tag, aggregate=False, header=False, encoding=False,
    header_block=False, payload_block=False, message_block=False, document_type=None):
        """Builds an OfxTag instance to be called by the name of
        the tag it represents.  For instance, to make an "APPID" tag,
        create the tag object with 'APPID = Tag("APPID")', and
        then use the instance as a method: 'APPID("MONEY")'."""
        self.tag           = tag
        self.aggregate     = aggregate
        self.header        = header
        self.encoding      = encoding
        self.header_block  = header_block
        self.message_block = message_block
        self.payload_block = payload_block
        self.document_type = document_type

    def __call__(self, *values, **params):
        """Invoked when an OfxTag instance is invoked as a method
        call (see constructor documentation for an example).  The
        instance will return a string using its tag as a marker,
        with the arguments to the call used as the value of the tag."""
        if self.document_type is not None:
            self._output_version(self.document_type)

        elif self.message_block:
            # For consistency, we use an empty join to put together
            # parts of an OFX message in a "message block" tag.
            return ''.join(values)

        elif self.header_block:
            if self.output == "ofx2":
                return "<?OFX " + ' '.join(values) + " ?>\r\n"
            else:
                # The header block takes all the headers and adds an
                # extra newline to signal the end of the block.
                return ''.join(values) + "\r\n"

        elif self.payload_block:
            # This is really a hack, to make sure that the OFX
            # tag generation doesn't end with a newline.  Hmm...
            return "<" + self.tag + ">" + "\r\n" + ''.join(values) \
                + "</" + self.tag + ">"

        elif self.header:
            # This is an individual name/value pair in the header.
            return self.tag + ":" + ''.join(values) + "\r\n"

        elif self.aggregate:
            return "<" + self.tag + ">" + "\r\n" + ''.join(values) \
                + "</" + self.tag + ">" + "\r\n"

        else:
            if values is None: return ""
            values = [str(x) for x in values]
            if values == "": return ""
            return "<" + self.tag + ">" + ''.join(values) + "\r\n"

# The following is really dumb and hackish.  Is there any way to know the
# name of the variable called when __call__ is invoked?  I guess that
# wouldn't help since we have no way of using closures to make a real
# builder.  :(

# This list of variable names is needed to avoid importing the unit test
# suite into any file that uses ofxbuilder.  Any new tags added below should
# also be added here, unfortunately.
__all__ = ['ACCTID', 'ACCTINFORQ', 'ACCTINFOTRNRQ', 'ACCTTYPE', 'APPID',
'APPVER', 'AVAILBAL', 'BALAMT', 'BANKACCTFROM', 'BANKID', 'BANKMSGSRQV1',
'BANKMSGSRSV1', 'BANKTRANLIST', 'BROKERID', 'CCACCTFROM', 'CCSTMTENDRQ',
'CCSTMTENDTRNRQ', 'CCSTMTRQ', 'CCSTMTRS', 'CCSTMTTRNRQ', 'CCSTMTTRNRS',
'CHARSET', 'CHECKNUM', 'CLIENTROUTING', 'CLTCOOKIE', 'CODE', 'COMPRESSION',
'CREDITCARDMSGSRQV1', 'CREDITCARDMSGSRSV1', 'CURDEF', 'DATA', 'DOCUMENT',
'DTACCTUP', 'DTASOF', 'DTCLIENT', 'DTEND', 'DTPOSTED', 'DTPROFUP', 'DTSERVER',
'DTSTART', 'ENCODING', 'FI', 'FID', 'FITID', 'HEADER', 'INCBAL', 'INCLUDE',
'INCOO', 'INCPOS', 'INCTRAN', 'INVACCTFROM', 'INVSTMTMSGSRQV1', 'INVSTMTRQ',
'INVSTMTTRNRQ', 'LANGUAGE', 'LEDGERBAL', 'MEMO', 'MESSAGE', 'NAME',
'NEWFILEUID', 'OFX', 'OFXHEADER', 'OFX1', 'OFX2', 'OLDFILEUID', 'ORG',
'PROFMSGSRQV1', 'PROFRQ', 'PROFTRNRQ', 'SECURITY', 'SEVERITY',
'SIGNONMSGSRQV1', 'SIGNONMSGSRSV1', 'SIGNUPMSGSRQV1', 'SONRQ', 'SONRS',
'STATUS', 'STMTENDRQ', 'STMTENDTRNRQ', 'STMTRQ', 'STMTTRN', 'STMTRS',
'STMTTRNRQ', 'STMTTRNRS', 'TRNAMT', 'TRNTYPE', 'TRNUID', 'USERID', 'USERPASS',
'VERSION']

# FIXME: Can I add a bunch of fields to the module with a loop?

ACCTID             = Tag("ACCTID")
ACCTINFORQ         = Tag("ACCTINFORQ", aggregate=True)
ACCTINFOTRNRQ      = Tag("ACCTINFOTRNRQ", aggregate=True)
ACCTTYPE           = Tag("ACCTTYPE")
APPID              = Tag("APPID")
APPVER             = Tag("APPVER")
AVAILBAL           = Tag("AVAILBAL", aggregate=True)
BALAMT             = Tag("BALAMT")
BANKACCTFROM       = Tag("BANKACCTFROM", aggregate=True)
BANKID             = Tag("BANKID")
BANKMSGSRQV1       = Tag("BANKMSGSRQV1", aggregate=True)
BANKMSGSRSV1       = Tag("BANKMSGSRSV1", aggregate=True)
BANKTRANLIST       = Tag("BANKTRANLIST", aggregate=True)
BROKERID           = Tag("BROKERID")
CCACCTFROM         = Tag("CCACCTFROM", aggregate=True)
CCSTMTENDRQ        = Tag("CCSTMTENDRQ", aggregate=True)
CCSTMTENDTRNRQ     = Tag("CCSTMTENDTRNRQ", aggregate=True)
CCSTMTRQ           = Tag("CCSTMTRQ", aggregate=True)
CCSTMTRS           = Tag("CCSTMTRS", aggregate=True)
CCSTMTTRNRQ        = Tag("CCSTMTTRNRQ", aggregate=True)
CCSTMTTRNRS        = Tag("CCSTMTTRNRS", aggregate=True)
CHARSET            = Tag("CHARSET", header=True)
CHECKNUM           = Tag("CHECKNUM")
CLIENTROUTING      = Tag("CLIENTROUTING")
CLTCOOKIE          = Tag("CLTCOOKIE")
CODE               = Tag("CODE")
COMPRESSION        = Tag("COMPRESSION", header=True)
CREDITCARDMSGSRQV1 = Tag("CREDITCARDMSGSRQV1", aggregate=True)
CREDITCARDMSGSRSV1 = Tag("CREDITCARDMSGSRSV1", aggregate=True)
CURDEF             = Tag("CURDEF")
DATA               = Tag("DATA", header=True)
DOCUMENT           = Tag("", message_block=True)
DTACCTUP           = Tag("DTACCTUP")
DTASOF             = Tag("DTASOF")
DTCLIENT           = Tag("DTCLIENT")
DTEND              = Tag("DTEND")
DTPOSTED           = Tag("DTPOSTED")
DTPROFUP           = Tag("DTPROFUP")
DTSERVER           = Tag("DTSERVER")
DTSTART            = Tag("DTSTART")
ENCODING           = Tag("ENCODING", header=True)
FI                 = Tag("FI", aggregate=True)
FID                = Tag("FID")
FITID              = Tag("FITID")
HEADER             = Tag("", header_block=True)
INCBAL             = Tag("INCBAL")
INCLUDE            = Tag("INCLUDE")
INCOO              = Tag("INCOO")
INCPOS             = Tag("INCPOS", aggregate=True)
INCTRAN            = Tag("INCTRAN", aggregate=True)
INVACCTFROM        = Tag("INVACCTFROM", aggregate=True)
INVSTMTMSGSRQV1    = Tag("INVSTMTMSGSRQV1", aggregate=True)
INVSTMTRQ          = Tag("INVSTMTRQ", aggregate=True)
INVSTMTTRNRQ       = Tag("INVSTMTTRNRQ", aggregate=True)
LANGUAGE           = Tag("LANGUAGE")
LEDGERBAL          = Tag("LEDGERBAL", aggregate=True)
MEMO               = Tag("MEMO")
MESSAGE            = Tag("MESSAGE")
NAME               = Tag("NAME")
NEWFILEUID         = Tag("NEWFILEUID", header=True)
OFX                = Tag("OFX", payload_block=True)
OFX1               = Tag("", document_type=Tag.ofx1)
OFX2               = Tag("", document_type=Tag.ofx2)
OFXHEADER          = Tag("OFXHEADER", header=True)
OLDFILEUID         = Tag("OLDFILEUID", header=True)
ORG                = Tag("ORG")
PROFMSGSRQV1       = Tag("PROFMSGSRQV1", aggregate=True)
PROFRQ             = Tag("PROFRQ", aggregate=True)
PROFTRNRQ          = Tag("PROFTRNRQ", aggregate=True)
SECURITY           = Tag("SECURITY", header=True)
SEVERITY           = Tag("SEVERITY")
SIGNONMSGSRQV1     = Tag("SIGNONMSGSRQV1", aggregate=True)
SIGNONMSGSRSV1     = Tag("SIGNONMSGSRSV1", aggregate=True)
SIGNUPMSGSRQV1     = Tag("SIGNUPMSGSRQV1", aggregate=True)
SONRQ              = Tag("SONRQ", aggregate=True)
SONRS              = Tag("SONRS", aggregate=True)
STATUS             = Tag("STATUS", aggregate=True)
STMTENDRQ          = Tag("STMTENDRQ", aggregate=True)
STMTENDTRNRQ       = Tag("STMTENDTRNRQ", aggregate=True)
STMTRQ             = Tag("STMTRQ", aggregate=True)
STMTRS             = Tag("STMTRS", aggregate=True)
STMTTRN            = Tag("STMTTRN", aggregate=True)
STMTTRNRQ          = Tag("STMTTRNRQ", aggregate=True)
STMTTRNRS          = Tag("STMTTRNRS", aggregate=True)
TRNAMT             = Tag("TRNAMT")
TRNTYPE            = Tag("TRNTYPE")
TRNUID             = Tag("TRNUID")
USERID             = Tag("USERID")
USERPASS           = Tag("USERPASS")
VERSION            = Tag("VERSION", header=True)

########NEW FILE########
__FILENAME__ = client
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# ofx.client - user agent for sending OFX requests and checking responses.
#

import ofx
import urllib2

class Client:
    """Network client for communicating with OFX servers.  The client
    handles forming a valid OFX request document, transmiting that
    request to the named OFX server, parsing the server's response for
    error flags and throwing errors as exceptions, and returning the
    requested OFX document if the request was successful."""

    def __init__(self, debug=False):
        """Constructs the Client object.  No configuration options
        are offered."""
        # FIXME: Need to let the client set itself for OFX 1.02 or OFX 2.0 formatting.
        self.request_msg = None
        self.debug = debug

    def get_fi_profile(self, institution,
                       username="anonymous00000000000000000000000",
                       password="anonymous00000000000000000000000"):
        request = ofx.Request()
        self.request_msg = request.fi_profile(institution, username, password)
        return self._send_request(institution.ofx_url, self.request_msg)

    def get_account_info(self, institution, username, password):
        request = ofx.Request()
        self.request_msg = request.account_info(institution, username, password)
        return self._send_request(institution.ofx_url, self.request_msg)

    def get_statement(self, account, username, password):
        acct_type = account.get_ofx_accttype()
        if acct_type == "CREDITCARD":
            return self.get_creditcard_statement(account, username, password)
        elif acct_type == "CHECKING" or acct_type == "SAVINGS" \
        or acct_type == "MONEYMRKT" or acct_type == "MONEYMARKT" or acct_type == "CREDITLINE":
            return self.get_bank_statement(account, username, password)
        else:
            raise ValueError("Unknown account type '%s'." % acct_type)

    def get_bank_statement(self, account, username, password):
        """Sends an OFX request for the given user's bank account
        statement, and returns that statement as an OFX document if
        the request is successful."""
        request = ofx.Request()
        # I'm breaking out these retries by statement type since I'm assuming that bank,
        # credit card, and investment OFX servers may each have different behaviors.
        try:
            # First, try to get a statement for the full year.  The USAA and American Express
            # OFX servers return a valid statement, although USAA only includes 90 days and
            # American Express seems to only include back to the first of the year.
            self.request_msg = request.bank_stmt(account, username, password, daysago=365)
            return self._send_request(account.institution.ofx_url, self.request_msg)
        except ofx.Error, detail:
            try:
                # If that didn't work, try 90 days back.
                self.request_msg = request.bank_stmt(account, username, password, daysago=90)
                return self._send_request(account.institution.ofx_url, self.request_msg)
            except ofx.Error, detail:
                # If that also didn't work, try 30 days back, which has been our default and
                # which always seems to work across all OFX servers.
                self.request_msg = request.bank_stmt(account, username, password, daysago=30)
                return self._send_request(account.institution.ofx_url, self.request_msg)

    def get_creditcard_statement(self, account, username, password):
        """Sends an OFX request for the given user's credit card
        statement, and returns that statement if the request is
        successful.  If the OFX server returns an error, the client
        will throw an OfxException indicating the error code and
        message."""
        # See comments in get_bank_statement, above, which explain these try/catch
        # blocks.
        request = ofx.Request()
        try:
            self.request_msg = request.creditcard_stmt(account, username, password, daysago=365)
            return self._send_request(account.institution.ofx_url, self.request_msg)
        except ofx.Error, detail:
            try:
                self.request_msg = request.creditcard_stmt(account, username, password, daysago=90)
                return self._send_request(account.institution.ofx_url, self.request_msg)
            except ofx.Error, detail:
                self.request_msg = request.creditcard_stmt(account, username, password, daysago=30)
                return self._send_request(account.institution.ofx_url, self.request_msg)

    def get_closing(self, account, username, password):
        # FIXME: Make sure this list only exists in one place and isn't duplicated here.
        acct_type = account.get_ofx_accttype()
        if acct_type == "CREDITCARD":
            return self.get_creditcard_closing(account, username, password)
        elif acct_type == "CHECKING" or acct_type == "SAVINGS" \
        or acct_type == "MONEYMRKT" or acct_type == "MONEYMARKT" or acct_type == "CREDITLINE":
            return self.get_bank_closing(account, username, password)
        else:
            raise ValueError("Unknown account type '%s'." % acct_type)

    def get_bank_closing(self, account, username, password):
        """Sends an OFX request for the given user's bank account
        statement, and returns that statement as an OFX document if
        the request is successful."""
        acct_type = account.get_ofx_accttype()
        request = ofx.Request()
        self.request_msg = request.bank_closing(account, username, password)
        return self._send_request(account.institution.ofx_url, self.request_msg)

    def get_creditcard_closing(self, account, username, password):
        """Sends an OFX request for the given user's credit card
        statement, and returns that statement if the request is
        successful.  If the OFX server returns an error, the client
        will throw an OfxException indicating the error code and
        message."""
        request = ofx.Request()
        self.request_msg = request.creditcard_closing(account, username, password)
        return self._send_request(account.institution.ofx_url, self.request_msg)

    def get_request_message(self):
        """Returns the last request message (or None if no request has been
        sent) for debugging purposes."""
        return self.request_msg

    def _send_request(self, url, request_body):
        """Transmits the message to the server and checks the response
        for error status."""

        request = urllib2.Request(url, request_body,
                                  { "Content-type": "application/x-ofx",
                                    "Accept": "*/*, application/x-ofx" })
        stream = urllib2.urlopen(request)
        response = stream.read()
        stream.close()

        if self.debug:
            print response

        response = ofx.Response(response)
        response.check_signon_status()

        parsed_ofx = response.as_dict()

        # FIXME: This needs to account for statement closing responses.

        if parsed_ofx.has_key("BANKMSGSRSV1"):
            bank_status = \
                parsed_ofx["BANKMSGSRSV1"]["STMTTRNRS"]["STATUS"]
            self._check_status(bank_status, "bank statement")

        elif parsed_ofx.has_key("CREDITCARDMSGSRSV1"):
            creditcard_status = \
                parsed_ofx["CREDITCARDMSGSRSV1"]["CCSTMTTRNRS"]["STATUS"]
            self._check_status(creditcard_status, "credit card statement")

        elif parsed_ofx.has_key("SIGNUPMSGSRSV1"):
            acctinfo_status = \
                parsed_ofx["SIGNUPMSGSRSV1"]["ACCTINFOTRNRS"]["STATUS"]
            self._check_status(acctinfo_status, "account information")

        return response

    def _check_status(self, status_block, description):
        # Convert the PyParsing result object into a dictionary so we can
        # provide default values if the status values don't exist in the
        # response.
        status = status_block.asDict()

        # There is no OFX status code "-1," so I'm using that code as a
        # marker for "No status code was returned."
        code = status.get("CODE", "-1")

        # Code "0" is "Success"; code "1" is "data is up-to-date."  Anything
        # else represents an error.
        if code is not "0" and code is not "1":
            # Try to find information about the error.  If the bank didn't
            # provide status information, return the value "NONE," which
            # should be both clear to a user and a marker of a lack of
            # information from the bank.
            severity = status.get("SEVERITY", "NONE")
            message  = status.get("MESSAGE", "NONE")

            # The "description" allows the code to give some indication
            # of where the error originated (for instance, the kind of
            # account we were trying to download when the error occurred).
            error = ofx.Error(description, code, severity, message)
            raise error


########NEW FILE########
__FILENAME__ = document
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.document - abstract OFX document.
#

import ofx
import xml.sax.saxutils as sax

class Document:
    def as_xml(self, original_format=None, date_format=None):
        """Formats this document as an OFX 2.0 XML document."""
        xml = ""

        # NOTE: Encoding in OFX, particularly in OFX 1.02,
        # is kind of a mess.  The OFX 1.02 spec talks about "UNICODE"
        # as a supported encoding, which the OFX 2.0 spec has
        # back-rationalized to "UTF-8".  The "US-ASCII" encoding is
        # given as "USASCII".  Yet the 1.02 spec acknowledges that
        # not everyone speaks English nor uses UNICODE, so they let
        # you throw any old encoding in there you'd like.  I'm going
        # with the idea that if the most common encodings are named
        # in an OFX file, they should be translated to "real" XML
        # encodings, and if no encoding is given, UTF-8 (which is a
        # superset of US-ASCII) should be assumed; but if a named
        # encoding other than USASCII or 'UNICODE' is given, that
        # should be preserved.  I'm also adding a get_encoding()
        # method so that we can start to survey what encodings
        # we're actually seeing, and use that to maybe be smarter
        # about this in the future.
        encoding = ""
        if self.parse_dict["header"]["ENCODING"] == "USASCII":
            encoding = "US-ASCII"
        elif self.parse_dict["header"]["ENCODING"] == "UNICODE":
            encoding = "UTF-8"
        elif self.parse_dict["header"]["ENCODING"] == "NONE":
            encoding = "UTF-8"
        else:
            encoding = self.parse_dict["header"]["ENCODING"]

        xml += """<?xml version="1.0" encoding="%s"?>\n""" % encoding
        xml += """<?OFX OFXHEADER="200" VERSION="200" """ + \
               """SECURITY="%s" OLDFILEUID="%s" NEWFILEUID="%s"?>\n""" % \
               (self.parse_dict["header"]["SECURITY"],
                self.parse_dict["header"]["OLDFILEUID"],
                self.parse_dict["header"]["NEWFILEUID"])

        if original_format is not None:
            xml += """<!-- Converted from: %s -->\n""" % original_format
        if date_format is not None:
            xml += """<!-- Date format was: %s -->\n""" % date_format

        taglist = self.parse_dict["body"]["OFX"].asList()
        xml += self._format_xml(taglist)

        return xml

    def _format_xml(self, mylist, indent=0):
        xml = ""
        indentstring = " " * indent
        tag = mylist.pop(0)
        if len(mylist) > 0 and isinstance(mylist[0], list):
            xml += "%s<%s>\n" % (indentstring, tag)
            for value in mylist:
                xml += self._format_xml(value, indent=indent + 2)
            xml += "%s</%s>\n" % (indentstring, tag)
        elif len(mylist) > 0:
            # Unescape then reescape so we don't wind up with '&amp;lt;', oy.
            value = sax.escape(sax.unescape(mylist[0]))
            xml += "%s<%s>%s</%s>\n" % (indentstring, tag, value, tag)
        return xml


########NEW FILE########
__FILENAME__ = error
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# ofx.error - OFX error message exception 
# 


class Error(Exception):
    def __init__(self, summary, code=None, severity=None, message=None):
        self.summary  = summary
        self.code     = int(code)
        self.severity = severity
        self.msg      = message

        self.codetable = \
            { 0: "OK",
              1: "Client is up-to-date",
              2000: "General error",
              2001: "Invalid account",
              2002: "General account error",
              2003: "Account not found",
              2004: "Account closed",
              2005: "Account not authorized",
              2006: "Source account not found",
              2007: "Source account closed",
              2008: "Source account not authorized",
              2009: "Destination account not found",
              2010: "Destination account closed",
              2011: "Destination account not authorized",
              2012: "Invalid amount",
              # Don't know why 2013 is missing from spec (1.02)
              2014: "Date too soon",
              2015: "Date too far in the future",
              2016: "Already committed",
              2017: "Already cancelled",
              2018: "Unknown server ID",
              2019: "Duplicate request",
              2020: "Invalid date",
              2021: "Unsupported version",
              2022: "Invalid TAN",
              10000: "Stop check in process",
              10500: "Too many checks to process",
              10501: "Invalid payee",
              10502: "Invalid payee address",
              10503: "Invalid payee account number",
              10504: "Insufficient funds",
              10505: "Cannot modify element",
              10506: "Cannot modify source account",
              10507: "Cannot modify destination account",
              10508: "Invalid frequency", # "..., Kenneth"
              10509: "Model already cancelled",
              10510: "Invalid payee ID",
              10511: "Invalid payee city",
              10512: "Invalid payee state",
              10513: "Invalid payee postal code",
              10514: "Bank payment already processed",
              10515: "Payee not modifiable by client",
              10516: "Wire beneficiary invalid",
              10517: "Invalid payee name",
              10518: "Unknown model ID",
              10519: "Invalid payee list ID",
              12250: "Investment transaction download not supported",
              12251: "Investment position download not supported",
              12252: "Investment positions for specified date not available",
              12253: "Investment open order download not supoorted",
              12254: "Investment balances download not supported",
              12500: "One or more securities not found",
              13000: "User ID & password will be sent out-of-band",
              13500: "Unable to enroll user",
              13501: "User already enrolled",
              13502: "Invalid service",
              13503: "Cannot change user information",
              15000: "Must change USERPASS",
              15500: "Signon (for example, user ID or password) invalid",
              15501: "Customer account already in use",
              15502: "USERPASS lockout",
              15503: "Could not change USERPASS",
              15504: "Could not provide random data",
              16500: "HTML not allowed",
              16501: "Unknown mail To:",
              16502: "Invalid URL",
              16503: "Unable to get URL", }

    def interpret_code(self, code=None):
        if code is None:
            code = self.code
        
        if self.codetable.has_key(code):
            return self.codetable[code]
        else:
            return "Unknown error code"
    
    def str(self):
        format = "%s\n(%s %s: %s)"
        return format % (self.msg, self.severity, self.code,
                         self.interpret_code())

    def __str__(self):
        return self.str()

    def __repr__(self):
        return self.str()

########NEW FILE########
__FILENAME__ = filetyper
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.FileTyper - figures out the type of a data file.
#

import csv
import re

class FileTyper:
    def __init__(self, text):
        self.text = text
    
    def trust(self):
        if re.search("OFXHEADER:", self.text, re.IGNORECASE) != None:
            match = re.search("VERSION:(\d)(\d+)", self.text)
            if match == None:
                return "OFX/1"
            else:
                major = match.group(1)
                minor = match.group(2)
                return "OFX/%s.%s" % (major, minor)
        
        elif re.search('<?OFX OFXHEADER="200"', self.text, re.IGNORECASE) != None:
            match = re.search('VERSION="(\d)(\d+)"', self.text)
            if match == None:
                return "OFX/2"
            else:
                major = match.group(1)
                minor = match.group(2)
                return "OFX/%s.%s" % (major, minor)
        
        elif self.text[0:100].find("MSISAM Database") != -1:
            return "MSMONEY-DB"
        
        elif self.text.find('<OFC>') != -1:
            return "OFC"
        
        elif re.search("^:20:", self.text, re.MULTILINE) != None and \
        re.search("^\:60F\:", self.text, re.MULTILINE) != None and \
        re.search("^-$", self.text, re.MULTILINE) != None:
            return "MT940"
        
        elif self.text.startswith('%PDF-'):
            return "PDF"
        
        elif self.text.find('<HTML') != -1 or self.text.find('<html') != -1:
            return "HTML"
        
        elif self.text.startswith("\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1\x00"):
            return "EXCEL"
            
        elif self.text.startswith("\xAC\x9E\xBD\x8F\x00\x00"):
            return "QUICKEN-DATA"
        
        elif self.text.startswith("\x4D\x5A"):
            return "EXE"
        
        elif self.text.find('Unix eFxTool 1.1') != -1:
            return "EFAX"
        
        elif re.compile("^\^(EUR)*\s*$", re.MULTILINE).search(self.text) != None or \
        re.compile("^!Type:", re.MULTILINE).search(self.text) != None:
            # A carat on a line by itself (ignoring whitespace) is a record
            # delimiter in QIF -- the only seemingly consistent marker in a
            # QIF file. (You can't rely on the "!Type" header since some banks
            # omit it.)
            return "QIF"
        
        else:
            # If more than 80% of the lines in the file have the same number of fields,
            # as determined by the CSV parser, and if there are more than 2 fields in
            # each of those lines, assume that it's CSV.
            dialect = csv.Sniffer().sniff(self.text, ",\t")
            if dialect is None:
                return "UNKNOWN"
            
            try:
                lines = self.text.splitlines()
                rows  = 0
                frequencies = {}
                for row in csv.reader(lines, dialect=dialect):
                    fields = len(row)
                    if fields > 0:
                        frequencies[fields] = frequencies.get(fields, 0) + 1
                        rows = rows + 1
            
                for fieldcount, frequency in frequencies.items():
                    percentage = (float(frequency) / float(rows)) * float(100)
                    if fieldcount > 2 and percentage > 80:
                        if dialect.delimiter == ",":
                            return "CSV"
                        elif dialect.delimiter == "\t":
                            return "TSV"
            except StandardError:
                pass
            
            # If we get all the way down here, we don't know what the file type is.
            return "UNKNOWN"


########NEW FILE########
__FILENAME__ = generator
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.generator - build up an OFX statement from source data.
#

from datetime import date
import ofx
from ofx.builder import *
import uuid

class Generator:
    def __init__(self, fid="UNKNOWN", org="UNKNOWN", bankid="UNKNOWN",
                 accttype="UNKNOWN", acctid="UNKNOWN", availbal="0.00",
                 ledgerbal="0.00", stmtdate=None, curdef="USD", lang="ENG"):
        self.fid       = fid
        self.org       = org
        self.bankid    = bankid
        self.accttype  = accttype
        self.acctid    = acctid
        self.availbal  = availbal
        self.ledgerbal = ledgerbal
        self.stmtdate  = stmtdate
        self.curdef    = curdef
        self.lang      = lang
        self.txns_by_date = {}
    
    def add_transaction(self, date=None, amount=None, number=None, 
                        txid=None, type=None, payee=None, memo=None):
        txn = ofx.Transaction(date=date, amount=amount, number=number, 
                              txid=txid, type=type, payee=payee, memo=memo)
        txn_date_list = self.txns_by_date.get(txn.date, [])
        txn_date_list.append(txn)
        self.txns_by_date[txn.date] = txn_date_list
    
    def to_ofx1(self):
        # Sort transactions and fill in date information.
        # OFX transactions appear most recent first, and oldest last.
        self.date_list = self.txns_by_date.keys()
        self.date_list.sort()
        self.date_list.reverse()
        
        self.startdate = self.date_list[-1]
        self.enddate   = self.date_list[0] 
        if self.stmtdate is None:
            self.stmtdate = date.today().strftime("%Y%m%d")
        
        # Generate the OFX statement.
        return DOCUMENT(self._ofx_header(),
                        OFX(self._ofx_signon(),
                            self._ofx_stmt()))
    
    def to_str(self):
        return self.to_ofx1()
    
    def __str__(self):
        return self.to_ofx1()
    
    def _ofx_header(self):
        return HEADER(
            OFXHEADER("100"),
            DATA("OFXSGML"),
            VERSION("102"),
            SECURITY("NONE"),
            ENCODING("USASCII"),
            CHARSET("1252"),
            COMPRESSION("NONE"),
            OLDFILEUID("NONE"),
            NEWFILEUID("NONE"))

    def _ofx_signon(self):
        return SIGNONMSGSRSV1(
            SONRS(
                STATUS(
                    CODE("0"),
                    SEVERITY("INFO"),
                    MESSAGE("SUCCESS")),
                DTSERVER(self.stmtdate),
                LANGUAGE(self.lang),
                FI(
                    ORG(self.org),
                    FID(self.fid))))

    def _ofx_stmt(self):
        if self.accttype == "CREDITCARD":
            return CREDITCARDMSGSRSV1(
                CCSTMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    CCSTMTRS(
                        CURDEF(self.curdef),
                        CCACCTFROM(
                            ACCTID(self.acctid)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))
        else:
            return BANKMSGSRSV1(
                STMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    STMTRS(
                        CURDEF(self.curdef),
                        BANKACCTFROM(
                            BANKID(self.bankid),
                            ACCTID(self.acctid),
                            ACCTTYPE(self.accttype)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))

    def _ofx_status(self):
        return STATUS(
            CODE("0"),
            SEVERITY("INFO"),
            MESSAGE("SUCCESS"))

    def _ofx_ledgerbal(self):
        return LEDGERBAL(
            BALAMT(self.ledgerbal),
            DTASOF(self.stmtdate))

    def _ofx_availbal(self):
        return AVAILBAL(
            BALAMT(self.availbal),
            DTASOF(self.stmtdate))

    def _ofx_txns(self):
        txns = ""
        
        for date in self.date_list:
            txn_list = self.txns_by_date[date]
            txn_index = len(txn_list)
            for txn in txn_list:
                txn_date = txn.date
                txn_amt  = txn.amount
        
                # Make a synthetic transaction ID using as many
                # uniqueness guarantors as possible.
                txn.txid = "%s-%s-%s-%s-%s" % (self.org, self.accttype,
                                                txn_date, txn_index,
                                                txn_amt)
                txns += txn.to_ofx()
                txn_index -= 1
        
        return BANKTRANLIST(
            DTSTART(self.startdate),
            DTEND(self.enddate),
            txns)
    
    
#
#  ofx.Transaction - clean and format transaction information.
#

class Transaction:
    def __init__(self, date="UNKNOWN", amount="0.00", number=None, 
                 txid=None, type="UNKNOWN", payee="UNKNOWN", memo=None):
        self.date     = date
        self.amount   = amount
        self.number   = number
        self.txid     = txid
        self.type     = type
        self.payee    = payee
        self.memo     = memo
    
    def to_ofx(self):
        fields = []
        
        if self.type is None:
            self.type = "DEBIT"
        
        fields.append(TRNTYPE(self.type))
        fields.append(DTPOSTED(self.date))
        fields.append(TRNAMT(self.amount))
        
        if self.number is not None:
            fields.append(CHECKNUM(self.number))
        
        if self.txid is None:
            self.txid = uuid.generate().upper()
        
        fields.append(FITID(self.txid))
        fields.append(NAME(self.payee))
        
        if self.memo is not None:
            fields.append(MEMO(self.memo))

        return STMTTRN(*fields)
    

########NEW FILE########
__FILENAME__ = institution
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# ofx.institution - container for financial insitution configuration data.
#

# REVIEW: Well, this certainly doesn't do much.
# At this point it works fine as a data structure.  Later on
# it would be nice if it actually, you know, did something.

import ofx

class Institution:
    def __init__(self, name="", ofx_org="", ofx_url="", ofx_fid=""):
        self.name    = name
        self.ofx_org = ofx_org
        self.ofx_url = ofx_url
        self.ofx_fid = ofx_fid

    def to_s(self):
        return ("Name: %s; Org: %s; OFX URL: %s; FID: %s") % \
               (self.name, self.ofx_org, self.ofx_url, self.ofx_fid)

    def __repr__(self):
        return self.to_s()

    def as_dict(self):
        return { 'name' : self.name,
                 'ofx_org' : self.ofx_org,
                 'ofx_url' : self.ofx_url,
                 'ofx_fid' : self.ofx_fid }

    def load_from_dict(fi_dict):
        return ofx.Institution(name=fi_dict.get('name'),
                               ofx_org=fi_dict.get('ofx_org'),
                               ofx_url=fi_dict.get('ofx_url'),
                               ofx_fid=fi_dict.get('ofx_fid'))
    load_from_dict = staticmethod(load_from_dict)


########NEW FILE########
__FILENAME__ = parser
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.parser - parser class for reading OFX documents.
#

import re
import sys
from pyparsing import alphanums, alphas, CharsNotIn, Dict, Forward, Group, \
Literal, OneOrMore, Optional, SkipTo, White, Word, ZeroOrMore

def _ofxStartDebugAction( instring, loc, expr ):
    sys.stderr.write("Match %s at loc %s (%d,%d)" % 
                    (expr, loc, 
                    instring.count("\n", 0, loc) + 1, 
                    loc - instring.rfind("\n", 0, loc)))

def _ofxSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    sys.stderr.write("Matched %s -> %s" % (expr, str(toks.asList())))
    
def _ofxExceptionDebugAction( instring, loc, expr, exc ):
    sys.stderr.write("Exception raised: %s" % exc)
    
class Parser:
    """Dirt-simple OFX parser for interpreting server results (primarily for
    errors at this point).  Currently parses OFX 1.02."""
    def __init__(self, debug=False):
        # Parser definition for headers
        header = Group(Word(alphas) + Literal(":").suppress() +
            Optional(CharsNotIn("\r\n")))
        headers = Dict(OneOrMore(header)).setResultsName("header")
        
        # Parser definition for OFX body
        aggregate = Forward().setResultsName("OFX")
        aggregate_open_tag, aggregate_close_tag = self._tag()
        content_open_tag = self._tag(closed=False)
        content = Group(content_open_tag + CharsNotIn("<\r\n"))
        aggregate << Group(aggregate_open_tag \
            + Dict(ZeroOrMore(aggregate | content)) \
            + aggregate_close_tag)
        body = Group(aggregate).setResultsName("body")
        
        # The parser as a whole
        self.parser = headers + body
        if (debug):
            self.parser.setDebugActions(_ofxStartDebugAction, _ofxSuccessDebugAction, _ofxExceptionDebugAction)
    
    def _tag(self, closed=True):
        """Generate parser definitions for OFX tags."""
        openTag = Literal("<").suppress() + Word(alphanums + ".") \
            + Literal(">").suppress()
        if (closed):
            closeTag = Group("</" + Word(alphanums + ".") + ">" + ZeroOrMore(White())).suppress()
            return openTag, closeTag
        else:
            return openTag
    
    def parse(self, ofx):
        """Parse a string argument and return a tree structure representing
        the parsed document."""
        ofx = self.strip_empty_tags(ofx)
        ofx = self.strip_close_tags(ofx)
        ofx = self.strip_blank_dtasof(ofx)
        ofx = self.strip_junk_ascii(ofx)
        ofx = self.fix_unknown_account_type(ofx)
        return self.parser.parseString(ofx).asDict()
    
    def strip_empty_tags(self, ofx):
        """Strips open/close tags that have no content."""
        strip_search = '<(?P<tag>[^>]+)>\s*</(?P=tag)>'
        return re.sub(strip_search, '', ofx)

    def strip_close_tags(self, ofx):
        """Strips close tags on non-aggregate nodes.  Close tags seem to be
        valid OFX/1.x, but they screw up our parser definition and are optional.
        This allows me to keep using the same parser without having to re-write
        it from scratch just yet."""
        strip_search = '<(?P<tag>[^>]+)>\s*(?P<value>[^<\n\r]+)(?:\s*</(?P=tag)>)?(?P<lineend>[\n\r]*)'
        return re.sub(strip_search, '<\g<tag>>\g<value>\g<lineend>', ofx)
    
    def strip_blank_dtasof(self, ofx):
        """Strips empty dtasof tags from wells fargo/wachovia downloads.  Again, it would
        be better to just rewrite the parser, but for now this is a workaround."""
        blank_search = '<(DTASOF|BALAMT|BANKID|CATEGORY|NAME)>[\n\r]+'
        return re.sub(blank_search, '', ofx)
    
    def strip_junk_ascii(self, ofx):
        """Strips high ascii gibberish characters from Schwab statements. They seem to 
        contains strings of EF BF BD EF BF BD 0A 08 EF BF BD 64 EF BF BD in the <NAME> field, 
        and the newline is screwing up the parser."""
        return re.sub('[\xBD-\xFF\x64\x0A\x08]{4,}', '', ofx)

    def fix_unknown_account_type(self, ofx):
        """Sets the content of <ACCTTYPE> nodes without content to be UNKNOWN so that the
        parser is able to parse it. This isn't really the best solution, but it's a decent workaround."""
        return re.sub('<ACCTTYPE>(?P<contentend>[<\n\r])', '<ACCTTYPE>UNKNOWN\g<contentend>', ofx)


########NEW FILE########
__FILENAME__ = request
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# ofx.request - build an OFX request document
#

from ofx.builder import *
import datetime
import uuid

class Request:
    def __init__(self, cookie=4, app_name="Money", app_version="1400"):
        # Note that American Express, at least, requires the app name
        # to be titlecase, and not all uppercase, for the request to
        # succeed.  Memories of Mozilla....
        self.app_name    = app_name
        self.app_version = app_version
        self.cookie      = cookie # FIXME: find out the meaning of this magic value.  Why not 3 or 5?
        self.request_id  = str(uuid.uuid4()).upper()
    
    def _format_date(self, date=None, datetime=datetime.datetime.now()):
        if date == None:
            return datetime.strftime("%Y%m%d%H%M%S")
        else:
            return date.strftime("%Y%m%d")
    
    def _message(self, institution, username, password, body):
        """Composes a complete OFX message document."""
        return DOCUMENT(self._header(),
                   OFX(self._sign_on(institution, username, password),
                       body))
    
    def _header(self):
        """Formats an OFX message header."""
        return HEADER(
            OFXHEADER("100"),
            DATA("OFXSGML"),
            VERSION("102"),
            SECURITY("NONE"),
            ENCODING("USASCII"),
            CHARSET("1252"),
            COMPRESSION("NONE"),
            OLDFILEUID("NONE"),
            NEWFILEUID(self.request_id))
    
    def _sign_on(self, institution, username, password):
        """Formats an OFX sign-on block."""
        return SIGNONMSGSRQV1(
            SONRQ(
                DTCLIENT(self._format_date()),
                USERID(username),
                USERPASS(password),
                LANGUAGE("ENG"),
                FI(
                    ORG(institution.ofx_org),
                    FID(institution.ofx_fid)),
                APPID(self.app_name),
                APPVER(self.app_version)))
    
    def fi_profile(self, institution, username, password):
        return self._message(institution, username, password,
            PROFMSGSRQV1(
                PROFTRNRQ(
                    TRNUID(self.request_id),
                    CLTCOOKIE(self.cookie),
                    PROFRQ(
                        CLIENTROUTING("NONE"),
                        DTPROFUP("19980101")))))
    
    def account_info(self, institution, username, password):
        """Returns a complete OFX account information request document."""
        return self._message(institution, username, password,
            SIGNUPMSGSRQV1(
                ACCTINFOTRNRQ(
                    TRNUID(self.request_id),
                    CLTCOOKIE(self.cookie),
                    ACCTINFORQ(
                        DTACCTUP("19980101")))))
    
    def bank_stmt(self, account, username, password, daysago=90):
        """Returns a complete OFX bank statement request document."""
        dt_start = datetime.datetime.now() - datetime.timedelta(days=daysago)
        return self._message(account.institution, username, password,
            BANKMSGSRQV1(
                STMTTRNRQ(
                    TRNUID(self.request_id),
                    CLTCOOKIE(self.cookie),
                    STMTRQ(
                        BANKACCTFROM(
                            BANKID(account.aba_number),
                            ACCTID(account.acct_number),
                            ACCTTYPE(account.get_ofx_accttype())),
                        INCTRAN(
                            DTSTART(self._format_date(date=dt_start)),
                            INCLUDE("Y"))))))
    
    def bank_closing(self, account, username, password):
        """Returns a complete OFX bank closing information request document."""
        return self._message(account.institution, username, password,
            BANKMSGSRQV1(
                STMTENDTRNRQ(
                    TRNUID(self.request_id),
                    CLTCOOKIE(self.cookie),
                    STMTENDRQ(
                        BANKACCTFROM(
                            BANKID(account.aba_number),
                            ACCTID(account.acct_number),
                            ACCTTYPE(account.get_ofx_accttype()))))))
    
    def creditcard_stmt(self, account, username, password, daysago=90):
        """Returns a complete OFX credit card statement request document."""
        dt_start = datetime.datetime.now() - datetime.timedelta(days=daysago)
        return self._message(account.institution, username, password,
            CREDITCARDMSGSRQV1(
                CCSTMTTRNRQ(
                    TRNUID(self.request_id),
                    CLTCOOKIE(self.cookie),
                    CCSTMTRQ(
                        CCACCTFROM(
                            ACCTID(account.acct_number)),
                        INCTRAN(
                            DTSTART(self._format_date(date=dt_start)),
                            INCLUDE("Y"))))))
    
    def creditcard_closing(self, account, username, password):
        """Returns a complete OFX credit card closing information request document."""
        dt_start = datetime.datetime.now() - datetime.timedelta(days=61)
        dt_end   = datetime.datetime.now() - datetime.timedelta(days=31)
        return self._message(account.institution, username, password,
            CREDITCARDMSGSRQV1(
                CCSTMTENDTRNRQ(
                    TRNUID(self.request_id),
                    CLTCOOKIE(self.cookie),
                    CCSTMTENDRQ(
                        CCACCTFROM(
                            ACCTID(account.acct_number)),
                        DTSTART(self._format_date(date=dt_end)),
                        DTEND(self._format_date(date=dt_end))))))
        
    

########NEW FILE########
__FILENAME__ = response
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.response - access to contents of an OFX response document.
#

import ofx

class Response(ofx.Document):
    def __init__(self, response, debug=False):
        # Bank of America (California) seems to be putting out bad Content-type
        # headers on manual OFX download.  I'm special-casing this out since
        # B of A is such a large bank.
        # REVIEW: Check later to see if this is still needed, espcially once
        # B of A is mechanized.
        # REVIEW: Checked.  Still needed.  Feh!
        self.raw_response = response.replace('Content- type:application/ofx', "")
        
        # Good god, another one.  Regex?
        self.raw_response = self.raw_response.replace('Content-Type: application/x-ofx', "")
        
        # I'm seeing this a lot, so here's an ugly workaround.  I wonder why multiple
        # FIs are causing it, though.
        self.raw_response = self.raw_response.replace('****OFX download terminated due to exception: Null or zero length FITID****', '')
        
        parser = ofx.Parser(debug)
        self.parse_dict = parser.parse(self.raw_response)
        self.ofx = self.parse_dict["body"]["OFX"].asDict()
    
    def as_dict(self):
        return self.ofx
    
    def as_string(self):
        return self.raw_response
    
    def get_encoding(self):
        return self.parse_dict["header"]["ENCODING"]
    
    def get_statements(self):
        # This allows us to parse out all statements from an OFX file
        # that contains multiple statements.
        
        # FIXME: I'm not positive this is legitimate.  Are there tagsets
        # a bank might use inside a bank or creditcard response *other*
        # than statements?  I bet there are.
        statements = []
        for tag in self.ofx.keys():
            if tag == "BANKMSGSRSV1" or tag == "CREDITCARDMSGSRSV1":
                for sub_tag in self.ofx[tag]:
                    statements.append(ofx.Statement(sub_tag))
        return statements
    
    def get_accounts(self):
        accounts = []
        for tag in self.ofx.keys():
            if tag == "SIGNUPMSGSRSV1":
                signup = self.ofx[tag].asDict()
                for signup_tag in signup:
                    if signup_tag == "ACCTINFOTRNRS":
                        accttrns = signup[signup_tag].asDict()
                        for accttrns_tag in accttrns:
                            if accttrns_tag == "ACCTINFORS":
                                acctrs = accttrns[accttrns_tag]
                                for acct in acctrs:
                                    if acct[0] == "ACCTINFO":
                                        account = self._extract_account(acct)
                                        if account is not None:
                                            accounts.append(account)
        return accounts
    
    def _extract_account(self, acct_block):
        acct_dict = acct_block.asDict()
        
        if acct_dict.has_key("DESC"):
            desc = acct_dict["DESC"]
        else:
            desc = None
        
        if acct_dict.has_key("BANKACCTINFO"):
            acctinfo = acct_dict["BANKACCTINFO"]
            return ofx.Account(ofx_block=acctinfo["BANKACCTFROM"], desc=desc)
        
        elif acct_dict.has_key("CCACCTINFO"):
            acctinfo = acct_dict["CCACCTINFO"]
            account = ofx.Account(ofx_block=acctinfo["CCACCTFROM"], desc=desc)
            account.acct_type = "CREDITCARD"
            return account
        
        else:
            return None
    
    def check_signon_status(self):
        status = self.ofx["SIGNONMSGSRSV1"]["SONRS"]["STATUS"]
        # This will throw an ofx.Error if the signon did not succeed.
        self._check_status(status, "signon")
        # If no exception was thrown, the signon succeeded.
        return True
    
    def _check_status(self, status_block, description):
        # Convert the PyParsing result object into a dictionary so we can
        # provide default values if the status values don't exist in the
        # response.
        status = status_block.asDict()
        
        # There is no OFX status code "-1," so I'm using that code as a
        # marker for "No status code was returned."
        code = status.get("CODE", "-1")
        
        # Code "0" is "Success"; code "1" is "data is up-to-date."  Anything
        # else represents an error.
        if code is not "0" and code is not "1":
            # Try to find information about the error.  If the bank didn't
            # provide status information, return the value "NONE," which
            # should be both clear to a user and a marker of a lack of
            # information from the bank.
            severity = status.get("SEVERITY", "NONE")
            message  = status.get("MESSAGE", "NONE")
            
            # The "description" allows the code to give some indication
            # of where the error originated (for instance, the kind of
            # account we were trying to download when the error occurred).
            error = ofx.Error(description, code, severity, message)
            raise error
    

class Statement(ofx.Document):
    def __init__(self, statement):
        self.parse_result = statement
        self.parse_dict = self.parse_result.asDict()
        
        if self.parse_dict.has_key("STMTRS"):
            stmt = self.parse_dict["STMTRS"]
            self.account = ofx.Account(ofx_block=stmt["BANKACCTFROM"])
        elif self.parse_dict.has_key("CCSTMTRS"):
            stmt = self.parse_dict["CCSTMTRS"]
            self.account = ofx.Account(ofx_block=stmt["CCACCTFROM"])
            self.account.acct_type = "CREDITCARD"
        else:
            error = ValueError("Unknown statement type: %s." % statement)
            raise error
        
        self.currency   = self._get(stmt,                 "CURDEF")
        self.begin_date = self._get(stmt["BANKTRANLIST"], "DTSTART")
        self.end_date   = self._get(stmt["BANKTRANLIST"], "DTEND")
        self.balance    = self._get(stmt["LEDGERBAL"],    "BALAMT")
        self.bal_date   = self._get(stmt["LEDGERBAL"],    "DTASOF")
    
    def _get(self, data, key):
        data_dict = data.asDict()
        return data_dict.get(key, "NONE")
    
    def as_dict(self):
        return self.parse_dict
    
    def as_xml(self, indent=4):
        taglist = self.parse_result.asList()
        return self._format_xml(taglist, indent)
    
    def get_account(self):
        return self.account
    
    def get_currency(self):
        return self.currency
    
    def get_begin_date(self):
        return self.begin_date
    
    def get_end_date(self):
        return self.end_date
    
    def get_balance(self):
        return self.balance
    
    def get_balance_date(self):
        return self.bal_date
    

########NEW FILE########
__FILENAME__ = validators
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# ofx.validators - Classes to validate certain financial data types.
#

class RoutingNumber:
    def __init__(self, number):
        self.number = number
        # FIXME: need to make sure we're really getting a number and not any non-number characters.
        try:
            self.digits = [int(digit) for digit in str(self.number).strip()]
            self.region_code = int(str(self.digits[0]) + str(self.digits[1]))
            self.converted = True
        except ValueError:
            # Not a number, failed to convert
            self.digits = None
            self.region_code = None
            self.converted = False
    
    def is_valid(self):
        if self.converted is False or len(self.digits) != 9:
            return False
        
        checksum = ((self.digits[0] * 3) +
                    (self.digits[1] * 7) +
                     self.digits[2]      +
                    (self.digits[3] * 3) +
                    (self.digits[4] * 7) +
                     self.digits[5]      +
                    (self.digits[6] * 3) +
                    (self.digits[7] * 7) +
                     self.digits[8]       )
        return (checksum % 10 == 0)
    
    def get_type(self):
        # Remember that range() stops one short of the second argument.
        # In other words, "x in range(1, 13)" means "x >= 1 and x < 13".
        if self.region_code == 0:
            return "United States Government"
        elif self.region_code in range(1, 13):
            return "Primary"
        elif self.region_code in range(21, 33):
            return "Thrift"
        elif self.region_code in range(61, 73):
            return "Electronic"
        elif self.region_code == 80:
            return "Traveller's Cheque"
        else:
            return None
    
    def get_region(self):
        if self.region_code == 0:
            return "United States Government"
        elif self.region_code in [1, 21, 61]:
            return "Boston"
        elif self.region_code in [2, 22, 62]:
            return "New York"
        elif self.region_code in [3, 23, 63]:
            return "Philadelphia"
        elif self.region_code in [4, 24, 64]:
            return "Cleveland"
        elif self.region_code in [5, 25, 65]:
            return "Richmond"
        elif self.region_code in [6, 26, 66]:
            return "Atlanta"
        elif self.region_code in [7, 27, 67]:
            return "Chicago"
        elif self.region_code in [8, 28, 68]:
            return "St. Louis"
        elif self.region_code in [9, 29, 69]:
            return "Minneapolis"
        elif self.region_code in [10, 30, 70]:
            return "Kansas City"
        elif self.region_code in [11, 31, 71]:
            return "Dallas"
        elif self.region_code in [12, 32, 72]:
            return "San Francisco"
        elif self.region_code == 80:
            return "Traveller's Cheque"
        else:
            return None
    
    def to_s(self):
        return str(self.number) + " (valid: %s; type: %s; region: %s)" % \
            (self.is_valid(), self.get_type(), self.get_region())
    
    def __repr__(self):
        return self.to_s()
    

########NEW FILE########
__FILENAME__ = csv_converter
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofxtools.CsvConverter - translate CSV files into OFX files.
#

import datetime
import dateutil.parser
import ofx
import ofxtools
import re
import sys
import xml.sax.saxutils as sax
from decimal import *
from ofx.builder import *

class CsvConverter:
    def __init__(self, qif, colspec=None, fid="UNKNOWN", org="UNKNOWN",
                 bankid="UNKNOWN", accttype="UNKNOWN", acctid="UNKNOWN",
                 balance="UNKNOWN", curdef=None, lang="ENG", dayfirst=False,
                 debug=False):
        self.qif      = qif
        self.colspec  = colspec
        self.fid      = fid
        self.org      = org
        self.bankid   = bankid
        self.accttype = accttype
        self.acctid   = acctid
        self.balance  = balance
        self.curdef   = curdef
        self.lang     = lang
        self.debug    = debug
        self.dayfirst = dayfirst

        self.parsed_csv = None

        # FIXME: Move this to one of the OFX generation classes (Document or Response).
        self.txns_by_date = {}

        if self.debug: sys.stderr.write("Parsing document.\n")

        parser = ofxtools.QifParser()  # debug=debug)
        self.parsed_qif = parser.parse(self.qif)

        if self.debug: sys.stderr.write("Cleaning transactions.\n")

        # We do a two-pass conversion in order to check the dates of all
        # transactions in the statement, and convert all the dates using
        # the same date format.  The first pass does nothing but look
        # at dates; the second actually applies the date conversion and
        # all other conversions, and extracts information needed for
        # the final output (like date range).
        txn_list = self._extract_txn_list(self.parsed_qif)
        self._guess_formats(txn_list)
        self._clean_txn_list(txn_list)

    def _extract_txn_list(self, qif):
        stmt_obj = qif.asDict()["QifStatement"]

        if self.accttype == "UNKNOWN":
            if "BankTransactions" in stmt_obj:
                self.accttype = "CHECKING"
            elif "CreditCardTransactions" in stmt_obj:
                self.accttype = "CREDITCARD"

        txn_list = []
        for stmt in stmt_obj:
            for txn in stmt:
                txn_list.append(txn)

        if len(txn_list) == 0:
            raise ValueError("Found no transactions to convert " +
                             "in the QIF source.")
        else:
            return txn_list

    #
    # Date methods
    #

    def _guess_formats(self, txn_list):
        # Go through the transactions one at a time, and try to parse the date
        # field and currency format. If we check the date format and find a
        # transaction where the first number must be the day (that is, the first
        # number is in the range 13..31), then set the state of the converter to
        # use dayfirst for all transaction cleanups. This is a guess because the
        # method will only work for UK dates if the statement contains a day in
        # the 13..31 range. (We could also test whether a date appears out of
        # order, or whether the jumps between transactions are especially long,
        # if this guessing method doesn't work reliably.)
        for txn_obj in txn_list:
            txn = txn_obj.asDict()
            txn_date     = txn.get("Date",     "UNKNOWN")
            txn_currency = txn.get("Currency", "UNKNOWN")
            # Look for date format.
            parsed_date = self._parse_date(txn_date)
            self._check_date_format(parsed_date)

    def _parse_date(self, txn_date, dayfirst=False):

    def _check_date_format(self, parsed_date):
        # If we *ever* find a date that parses as dayfirst, treat
        # *all* transactions in this statement as dayfirst.
        if parsed_date is not None and parsed_date != "UNKNOWN" and parsed_date.microsecond == 3:
            self.dayfirst = True

    #
    # Cleanup methods
    #

    def _clean_txn_list(self, txn_list):
        for txn_obj in txn_list:
            try:
                txn = self._clean_txn(txn_obj)
                txn_date = txn["Date"]
                txn_date_list = self.txns_by_date.get(txn_date, [])
                txn_date_list.append(txn)
                self.txns_by_date[txn_date] = txn_date_list
            except ValueError:
                # The _clean_txn method will sometimes find transactions
                # that are inherently unclean and are unable to be purified.
                # In these cases it will reject the transaction by throwing
                # a ValueError, which signals us not to store the transaction.
                if self.debug: sys.stderr.write("Skipping transaction '%s'." %
                                                str(txn_obj.asDict()))

        # Sort the dates (in YYYYMMDD format) and choose the lowest
        # date as our start date, and the highest date as our end
        # date.
        date_list = self.txns_by_date.keys()
        date_list.sort()

        self.start_date = date_list[0]
        self.end_date   = date_list[-1]

    def _clean_txn(self, txn_obj):
        # This is sort of the brute-force method of the converter.  It
        # looks at the data we get from the bank and tries as hard as
        # possible to make best-effort guesses about what the OFX 2.0
        # standard values for the transaction should be.  There's a
        # reasonable amount of guesswork in here -- some of it wise,
        # maybe some of it not.  If the cleanup method determines that
        # the txn_obj shouldn't be in the data, it will return None.
        # Otherwise, it will return a transaction cleaned to the best
        # of our abilities.
        txn = txn_obj.asDict()
        self._clean_txn_date(txn)
        self._clean_txn_amount(txn)
        self._clean_txn_number(txn)
        self._clean_txn_type(txn)
        self._clean_txn_payee(txn)
        return txn

    def _clean_txn_date(self, txn):
        txn_date    = txn.get("Date", "UNKNOWN").strip()
        if txn_date != "UNKNOWN":
            parsed_date = self._parse_date(txn_date, dayfirst=self.dayfirst)
            txn["Date"] = parsed_date.strftime("%Y%m%d")
        else:
            txn["Date"] = "UNKNOWN"

    def _clean_txn_amount(self, txn):
        txn_amount  = txn.get("Amount",  "00.00")
        txn_amount2 = txn.get("Amount2", "00.00")

        # Home Depot Credit Card seems to send two transaction records for each
        # transaction. They're out of order (that is, the second record is not
        # directly after the first, nor even necessarily after it at all), and
        # the second one *sometimes* appears to be a memo field on the first one
        # (e.g., a credit card payment will show up with an amount and date, and
        # then the next transaction will have the same date and a payee that
        # reads, "Thank you for your payment!"), and *sometimes* is the real
        # payee (e.g., the first will say "Home Depot" and the second will say
        # "Seasonal/Garden"). One of the two transaction records will have a
        # transaction amount of "-", and the other will have the real
        # transaction amount. Ideally, we would pull out the memo and attach it
        # to the right transaction, but unless the two transactions are the only
        # transactions on that date, there doesn't seem to be a good clue (order
        # in statement, amount, etc.) as to how to associate them. So, instead,
        # we're returning None, which means this transaction should be removed
        # from the statement and not displayed to the user. The result is that
        # for Home Depot cards, sometimes we lose the memo (which isn't that big
        # a deal), and sometimes we make the memo into the payee (which sucks).
        if txn_amount == "-" or txn_amount == " ":
            raise ValueError("Transaction amount is undefined.")

        # Some QIF sources put the amount in Amount2 instead, for unknown
        # reasons.  Here we ignore Amount2 unless Amount is unknown.
        if txn_amount == "00.00":
            txn_amount = txn_amount2

        # Okay, now strip out whitespace padding.
        txn_amount = txn_amount.strip()

        # Some QIF files have dollar signs in the amount.  Hey, why not?
        txn_amount = txn_amount.replace('$', '', 1)

        # Some QIF sources put three digits after the decimal, and the Ruby
        # code thinks that means we're in Europe.  So.....let's deal with
        # that now.
        try:
            txn_amount = str(Decimal(txn_amount).quantize(Decimal('.01')))
        except:
            # Just keep truckin'.
            pass

        txn["Amount"] = txn_amount

    def _clean_txn_number(self, txn):
        txn_number  = txn.get("Number", "UNKNOWN").strip()

        # Clean up bad check number behavior
        all_digits = re.compile("\d+")

        if txn_number == "N/A":
            # Get rid of brain-dead Chase check number "N/A"s
            del txn["Number"]

        elif txn_number.startswith("XXXX-XXXX-XXXX"):
            # Home Depot credit cards throw THE CREDIT CARD NUMBER
            # into the check number field.  Oy!  At least they mask
            # the first twelve digits, so we know they're insane.
            del txn["Number"]

        elif txn_number != "UNKNOWN" and self.accttype == "CREDITCARD":
            # Several other credit card companies (MBNA, CapitalOne)
            # seem to use the number field as a transaction ID.  Get
            # rid of this.
            del txn["Number"]

        elif txn_number == "0000000000" and self.accttype != "CREDITCARD":
            # There's some bank that puts "N0000000000" in every non-check
            # transaction.  (They do use normal check numbers for checks.)
            del txn["Number"]

        elif txn_number != "UNKNOWN" and all_digits.search(txn_number):
            # Washington Mutual doesn't indicate a CHECK transaction
            # when a check number is present.
            txn["Type"] = "CHECK"

    def _clean_txn_type(self, txn):
        txn_type    = "UNKNOWN"
        txn_amount  = txn.get("Amount", "UNKNOWN")
        txn_payee   = txn.get("Payee",  "UNKNOWN")
        txn_memo    = txn.get("Memo",   "UNKNOWN")
        txn_number  = txn.get("Number", "UNKNOWN")
        txn_sign    = self._txn_sign(txn_amount)

        # Try to figure out the transaction type from the Payee or
        # Memo field.
        for typestr in self.txn_types.keys():
            if txn_number == typestr:
                # US Bank sends "DEBIT" or "CREDIT" as a check number
                # on credit card transactions.
                txn["Type"] = self.txn_types[typestr]
                del txn["Number"]
                break

            elif txn_payee.startswith(typestr + "/") or \
            txn_memo.startswith(typestr + "/") or \
            txn_memo == typestr or txn_payee == typestr:
                if typestr == "ACH" and txn_sign == "credit":
                    txn["Type"] = "DIRECTDEP"

                elif typestr == "ACH" and txn_sign == "debit":
                    txn["Type"] = "DIRECTDEBIT"

                else:
                    txn["Type"] = self.txn_types[typestr]
                break

    def _clean_txn_payee(self, txn):
        txn_payee   = txn.get("Payee",  "UNKNOWN")
        txn_memo    = txn.get("Memo",   "UNKNOWN")
        txn_number  = txn.get("Number", "UNKNOWN")
        txn_type    = txn.get("Type",   "UNKNOWN")
        txn_amount  = txn.get("Amount", "UNKNOWN")
        txn_sign    = self._txn_sign(txn_amount)

        # Try to fill in the payee field with some meaningful value.
        if txn_payee == "UNKNOWN":
            if txn_number != "UNKNOWN" and (self.accttype == "CHECKING" or
            self.accttype == "SAVINGS"):
                txn["Payee"] = "Check #%s" % txn_number
                txn["Type"]  = "CHECK"

            elif txn_type == "INT" and txn_sign == "debit":
                txn["Payee"] = "Interest paid"

            elif txn_type == "INT" and txn_sign == "credit":
                txn["Payee"] = "Interest earned"

            elif txn_type == "ATM" and txn_sign == "debit":
                txn["Payee"] = "ATM Withdrawal"

            elif txn_type == "ATM" and txn_sign == "credit":
                txn["Payee"] = "ATM Deposit"

            elif txn_type == "POS" and txn_sign == "debit":
                txn["Payee"] = "Point of Sale Payment"

            elif txn_type == "POS" and txn_sign == "credit":
                txn["Payee"] = "Point of Sale Credit"

            elif txn_memo != "UNKNOWN":
                txn["Payee"] = txn_memo

            # Down here, we have no payee, no memo, no check number,
            # and no type.  Who knows what this stuff is.
            elif txn_type == "UNKNOWN" and txn_sign == "debit":
                txn["Payee"] = "Other Debit"
                txn["Type"]  = "DEBIT"

            elif txn_type == "UNKNOWN" and txn_sign == "credit":
                txn["Payee"] = "Other Credit"
                txn["Type"]  = "CREDIT"

        # Make sure the transaction type has some valid value.
        if not txn.has_key("Type") and txn_sign == "debit":
            txn["Type"] = "DEBIT"

        elif not txn.has_key("Type") and txn_sign == "credit":
            txn["Type"] = "CREDIT"

    def _txn_sign(self, txn_amount):
        # Is this a credit or a debit?
        if txn_amount.startswith("-"):
            return "debit"
        else:
            return "credit"

    #
    # Conversion methods
    #

    def to_ofx102(self):
        if self.debug: sys.stderr.write("Making OFX/1.02.\n")
        return DOCUMENT(self._ofx_header(),
                        OFX(self._ofx_signon(),
                            self._ofx_stmt()))

    def to_xml(self):
        ofx102 = self.to_ofx102()

        if self.debug:
            sys.stderr.write(ofx102 + "\n")
            sys.stderr.write("Parsing OFX/1.02.\n")
        response = ofx.Response(ofx102) #, debug=self.debug)

        if self.debug: sys.stderr.write("Making OFX/2.0.\n")
        if self.dayfirst:
            date_format = "DD/MM/YY"
        else:
            date_format = "MM/DD/YY"
        xml = response.as_xml(original_format="QIF", date_format=date_format)

        return xml



########NEW FILE########
__FILENAME__ = ofc_converter
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.OfcConverter - translate OFC files into OFX files.
#

import ofx
import ofxtools
import re
import sys
from ofx.builder import *

class OfcConverter:
    def __init__(self, ofc, fid="UNKNOWN", org="UNKNOWN", curdef=None,
                 lang="ENG", debug=False):
        self.ofc      = ofc
        self.fid      = fid
        self.org      = org
        self.curdef   = curdef
        self.lang     = lang
        self.debug    = debug

        self.bankid     = "UNKNOWN"
        self.accttype   = "UNKNOWN"
        self.acctid     = "UNKNOWN"
        self.balance    = "UNKNOWN"
        self.start_date = "UNKNOWN"
        self.end_date   = "UNKNOWN"

        self.parsed_ofc = None

        self.acct_types = { "0"  : "CHECKING",
                            "1"  : "SAVINGS",
                            "2"  : "CREDITCARD",
                            "3"  : "MONEYMRKT",
                            "4"  : "CREDITLINE",
                            "5"  : "UNKNOWN",
                            "6"  : "UNKNOWN",
                            "7"  : "UNKNOWN" }

        self.txn_types  = { "0"  : "CREDIT",
                            "1"  : "DEBIT",
                            "2"  : "INT",
                            "3"  : "DIV",
                            "4"  : "SRVCHG",
                            "5"  : "DEP",
                            "6"  : "ATM",
                            "7"  : "XFER",
                            "8"  : "CHECK",
                            "9"  : "PAYMENT",
                            "10" : "CASH",
                            "11" : "DIRECTDEP",
                            "12" : "OTHER" }

        if self.debug: sys.stderr.write("Parsing document.\n")

        parser = ofxtools.OfcParser(debug=debug)
        self.parsed_ofc = parser.parse(self.ofc)

        if self.debug: sys.stderr.write("Extracting document properties.\n")

        try:
            self.bankid     = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["ACCTFROM"]["BANKID"]
            acct_code       = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["ACCTFROM"]["ACCTTYPE"]
            self.accttype   = self.acct_types.get(acct_code, "UNKNOWN")
            self.acctid     = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["ACCTFROM"]["ACCTID"]
        except KeyError:
            self.bankid     = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["ACCTFROM"]["ACCOUNT"]["BANKID"]
            acct_code       = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["ACCTFROM"]["ACCOUNT"]["ACCTTYPE"]
            self.accttype   = self.acct_types.get(acct_code, "UNKNOWN")
            self.acctid     = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["ACCTFROM"]["ACCOUNT"]["ACCTID"]

        self.balance    = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["STMTRS"]["LEDGER"]
        self.start_date = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["STMTRS"]["DTSTART"]
        self.end_date   = self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["STMTRS"]["DTEND"]

    #
    # Conversion methods
    #

    def to_ofx102(self):
        if self.debug: sys.stderr.write("Making OFX/1.02.\n")
        return DOCUMENT(self._ofx_header(),
                        OFX(self._ofx_signon(),
                            self._ofx_stmt()))

    def to_xml(self):
        ofx102 = self.to_ofx102()

        if self.debug:
            sys.stderr.write(ofx102 + "\n")
            sys.stderr.write("Parsing OFX/1.02.\n")
        response = ofx.Response(ofx102, debug=self.debug)

        if self.debug: sys.stderr.write("Making OFX/2.0.\n")

        xml = response.as_xml(original_format="OFC")

        return xml

    # FIXME: Move the remaining methods to ofx.Document or ofx.Response.

    def _ofx_header(self):
        return HEADER(
            OFXHEADER("100"),
            DATA("OFXSGML"),
            VERSION("102"),
            SECURITY("NONE"),
            ENCODING("USASCII"),
            CHARSET("1252"),
            COMPRESSION("NONE"),
            OLDFILEUID("NONE"),
            NEWFILEUID("NONE"))

    def _ofx_signon(self):
        return SIGNONMSGSRSV1(
            SONRS(
                STATUS(
                  CODE("0"),
                  SEVERITY("INFO"),
                  MESSAGE("SUCCESS")),
                DTSERVER(self.end_date),
                LANGUAGE(self.lang),
                FI(
                    ORG(self.org),
                    FID(self.fid))))

    def _ofx_stmt(self):
        # Set default currency here, instead of on init, so that the caller
        # can override the currency format found in the QIF file if desired.
        # See also _guess_formats(), above.
        if self.curdef is None:
            curdef = "USD"
        else:
            curdef = self.curdef

        if self.accttype == "Credit Card":
            return CREDITCARDMSGSRSV1(
                CCSTMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    CCSTMTRS(
                        CURDEF(curdef),
                        CCACCTFROM(
                            ACCTID(self.acctid)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))
        else:
            return BANKMSGSRSV1(
                STMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    STMTRS(
                        CURDEF(curdef),
                        BANKACCTFROM(
                            BANKID(self.bankid),
                            ACCTID(self.acctid),
                            ACCTTYPE(self.accttype)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))

    def _ofx_status(self):
        return STATUS(
            CODE("0"),
            SEVERITY("INFO"),
            MESSAGE("SUCCESS"))

    def _ofx_ledgerbal(self):
        return LEDGERBAL(
            BALAMT(self.balance),
            DTASOF(self.end_date))

    def _ofx_availbal(self):
        return AVAILBAL(
            BALAMT(self.balance),
            DTASOF(self.end_date))

    def _ofx_txns(self):
        txns = ""
        last_date = None
        txn_index = 1

        for item in self.parsed_ofc["document"]["OFC"]["ACCTSTMT"]["STMTRS"]:
            if item[0] == "STMTTRN":
                txn = item.asDict()
                if txn.has_key('GENTRN'):
                    txn = txn['GENTRN'].asDict()

                txn_date = txn["DTPOSTED"]
                if txn_date != last_date:
                    last_date = txn_date
                    txn_index = 1

                txn_amt  = txn["TRNAMT"]
                txn_type = self.txn_types.get(txn["TRNTYPE"])
                if txn_type is None:
                    if txn_amt.startswith('-'):
                        txn["TRNTYPE"] = "DEBIT"
                    else:
                        txn["TRNTYPE"] = "CREDIT"

                # Make a synthetic transaction ID using as many
                # uniqueness guarantors as possible.
                txn["FITID"] = "%s-%s-%s-%s-%s" % (self.org, self.accttype,
                                                   txn_date, txn_index,
                                                   txn_amt)
                txns += self._ofx_txn(txn)
                txn_index += 1

        return BANKTRANLIST(
            DTSTART(self.start_date),
            DTEND(self.end_date),
            txns)

    def _ofx_txn(self, txn):
        fields = []
        if self._check_field("TRNTYPE", txn):
            fields.append(TRNTYPE(txn["TRNTYPE"].strip()))

        if self._check_field("DTPOSTED", txn):
            fields.append(DTPOSTED(txn["DTPOSTED"].strip()))

        if self._check_field("TRNAMT", txn):
            fields.append(TRNAMT(txn["TRNAMT"].strip()))

        if self._check_field("CHECKNUM", txn):
            fields.append(CHECKNUM(txn["CHECKNUM"].strip()))

        if self._check_field("FITID", txn):
            fields.append(FITID(txn["FITID"].strip()))

        if self._check_field("NAME", txn):
            fields.append(NAME(txn["NAME"].strip()))

        if self._check_field("MEMO", txn):
            fields.append(MEMO(txn["MEMO"].strip()))

        return STMTTRN(*fields)

    def _check_field(self, key, txn):
        return txn.has_key(key) and txn[key].strip() != ""



########NEW FILE########
__FILENAME__ = ofc_parser
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofxtools.ofc_parser - parser class for reading OFC documents.
#

import ofxtools
from pyparsing import alphanums, CharsNotIn, Dict, Forward, Group, \
Literal, OneOrMore, White, Word, ZeroOrMore

class OfcParser:
    """Dirt-simple OFC parser for interpreting OFC documents."""
    def __init__(self, debug=False):
        aggregate = Forward().setResultsName("OFC")
        aggregate_open_tag, aggregate_close_tag = self._tag()
        content_open_tag = self._tag(closed=False)
        content = Group(content_open_tag + CharsNotIn("<\r\n"))
        aggregate << Group(aggregate_open_tag \
            + Dict(OneOrMore(aggregate | content)) \
            + aggregate_close_tag)
        
        self.parser = Group(aggregate).setResultsName("document")
        if (debug):
            self.parser.setDebugActions(ofxtools._ofxtoolsStartDebugAction, 
                                        ofxtools._ofxtoolsSuccessDebugAction, 
                                        ofxtools._ofxtoolsExceptionDebugAction)
    
    def _tag(self, closed=True):
        """Generate parser definitions for OFX tags."""
        openTag = Literal("<").suppress() + Word(alphanums + ".") \
            + Literal(">").suppress()
        if (closed):
            closeTag = Group("</" + Word(alphanums + ".") + ">" + ZeroOrMore(White())).suppress()
            return openTag, closeTag
        else:
            return openTag
    
    def parse(self, ofc):
        """Parse a string argument and return a tree structure representing
        the parsed document."""
        return self.parser.parseString(ofc).asDict()
    


########NEW FILE########
__FILENAME__ = ofx_statement
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofxtools.OfxStatement - build up an OFX statement from source data.
#

import datetime
import dateutil.parser
import ofx
import ofxtools

class OfxStatement:
    def __init__(self, fid="UNKNOWN", org="UNKNOWN", bankid="UNKNOWN",
                 accttype="UNKNOWN", acctid="UNKNOWN", balance="UNKNOWN",
                 curdef="USD", lang="ENG"):
        self.fid      = fid
        self.org      = org
        self.bankid   = bankid
        self.accttype = accttype
        self.acctid   = acctid
        self.balance  = balance
        self.curdef   = curdef
        self.lang     = lang

    def add_transaction(self, date=None, amount=None, number=None,
                        type=None, payee=None, memo=None):
        txn = ofxtools.OfxTransaction(date, amount, number, type, payee, memo)

    def to_str(self):
        pass

    def __str__(self):
        pass

    def _ofx_header(self):
        return HEADER(
            OFXHEADER("100"),
            DATA("OFXSGML"),
            VERSION("102"),
            SECURITY("NONE"),
            ENCODING("USASCII"),
            CHARSET("1252"),
            COMPRESSION("NONE"),
            OLDFILEUID("NONE"),
            NEWFILEUID("NONE"))

    def _ofx_signon(self):
        return SIGNONMSGSRSV1(
            SONRS(
                STATUS(
                    CODE("0"),
                    SEVERITY("INFO"),
                    MESSAGE("SUCCESS")),
                DTSERVER(self.end_date),
                LANGUAGE(self.lang),
                FI(
                    ORG(self.org),
                    FID(self.fid))))

    def _ofx_stmt(self):
        if self.accttype == "CREDITCARD":
            return CREDITCARDMSGSRSV1(
                CCSTMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    CCSTMTRS(
                        CURDEF(curdef),
                        CCACCTFROM(
                            ACCTID(self.acctid)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))
        else:
            return BANKMSGSRSV1(
                STMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    STMTRS(
                        CURDEF(curdef),
                        BANKACCTFROM(
                            BANKID(self.bankid),
                            ACCTID(self.acctid),
                            ACCTTYPE(self.accttype)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))

    def _ofx_status(self):
        return STATUS(
            CODE("0"),
            SEVERITY("INFO"),
            MESSAGE("SUCCESS"))

    def _ofx_ledgerbal(self):
        return LEDGERBAL(
            BALAMT(self.balance),
            DTASOF(self.end_date))

    def _ofx_availbal(self):
        return AVAILBAL(
            BALAMT(self.balance),
            DTASOF(self.end_date))

    def _ofx_txns(self):
        txns = ""

        # OFX transactions appear most recent first, and oldest last,
        # so we do a reverse sort of the dates in this statement.
        date_list = self.txns_by_date.keys()
        date_list.sort()
        date_list.reverse()
        for date in date_list:
            txn_list = self.txns_by_date[date]
            txn_index = len(txn_list)
            for txn in txn_list:
                txn_date = txn.get("Date", "UNKNOWN")
                txn_amt  = txn.get("Amount", "00.00")

                # Make a synthetic transaction ID using as many
                # uniqueness guarantors as possible.
                txn["ID"] = "%s-%s-%s-%s-%s" % (self.org, self.accttype,
                                                txn_date, txn_index,
                                                txn_amt)
                txns += self._ofx_txn(txn)
                txn_index -= 1

        # FIXME: This should respect the type of statement being generated.
        return BANKTRANLIST(
            DTSTART(self.start_date),
            DTEND(self.end_date),
            txns)

    def _ofx_txn(self, txn):
        fields = []
        if self._check_field("Type", txn):
            fields.append(TRNTYPE(txn["Type"].strip()))

        if self._check_field("Date", txn):
            fields.append(DTPOSTED(txn["Date"].strip()))

        if self._check_field("Amount", txn):
            fields.append(TRNAMT(txn["Amount"].strip()))

        if self._check_field("Number", txn):
            fields.append(CHECKNUM(txn["Number"].strip()))

        if self._check_field("ID", txn):
            fields.append(FITID(txn["ID"].strip()))

        if self._check_field("Payee", txn):
            fields.append(NAME(sax.escape(sax.unescape(txn["Payee"].strip()))))

        if self._check_field("Memo", txn):
            fields.append(MEMO(sax.escape(sax.unescape(txn["Memo"].strip()))))

        return STMTTRN(*fields)

    def _check_field(self, key, txn):
        return txn.has_key(key) and txn[key].strip() != ""

#
#  ofxtools.OfxTransaction - clean and format transaction information.
#
#  Copyright Wesabe, Inc. (c) 2005-2007. All rights reserved.
#

class OfxTransaction:
    def __init__(self, date=None, amount=None, number=None,
                 type=None, payee=None, memo=None):
        self.raw_date = date
        self.date     = None
        self.amount   = amount
        self.number   = number
        self.type     = type
        self.payee    = payee
        self.memo     = memo
        self.dayfirst = False

        # This is a list of possible transaction types embedded in the
        # QIF Payee or Memo field (depending on bank and, it seems,
        # other factors).  The keys are used to match possible fields
        # that we can identify.  The values are used as substitutions,
        # since banks will use their own vernacular (like "DBT"
        # instead of "DEBIT") for some transaction types.  All of the
        # types in the values column (except "ACH", which is given
        # special treatment) are OFX-2.0 standard transaction types;
        # the keys are not all standard.  To add a new translation,
        # find the QIF name for the transaction type, and add it to
        # the keys column, then add the appropriate value from the
        # OFX-2.0 spec (see page 180 of doc/ofx/ofx-2.0/ofx20.pdf).
        # The substitution will be made if either the payee or memo
        # field begins with one of the keys followed by a "/", OR if
        # the payee or memo field exactly matches a key.
        self.txn_types = { "ACH"         : "ACH",
                           "CHECK CARD"  : "POS",
                           "CREDIT"      : "CREDIT",
                           "DBT"         : "DEBIT",
                           "DEBIT"       : "DEBIT",
                           "INT"         : "INT",
                           "DIV"         : "DIV",
                           "FEE"         : "FEE",
                           "SRVCHG"      : "SRVCHG",
                           "DEP"         : "DEP",
                           "DEPOSIT"     : "DEP",
                           "ATM"         : "ATM",
                           "POS"         : "POS",
                           "XFER"        : "XFER",
                           "CHECK"       : "CHECK",
                           "PAYMENT"     : "PAYMENT",
                           "CASH"        : "CASH",
                           "DIRECTDEP"   : "DIRECTDEP",
                           "DIRECTDEBIT" : "DIRECTDEBIT",
                           "REPEATPMT"   : "REPEATPMT",
                           "OTHER"       : "OTHER"        }

    def guess_date_format(self):
        pass

    def set_date_format(self, dayfirst=False):
        self.dayfirst = dayfirst

    def parse_date(self):
        # Try as best we can to parse the date into a datetime object. Note:
        # this assumes that we never see a timestamp, just the date, in any
        # QIF date.
        if self.date != "UNKNOWN":
            try:
                return dateutil.parser.parse(self.date, dayfirst=self.dayfirst)

            except ValueError:
                # dateutil.parser doesn't recognize dates of the
                # format "MMDDYYYY", though it does recognize
                # "MM/DD/YYYY".  So, if parsing has failed above,
                # try shoving in some slashes and see if that
                # parses.
                try:
                    if len(self.date) == 8:
                        # The int() cast will only succeed if all 8
                        # characters of txn_date are numbers.  If
                        # it fails, it will throw an exception we
                        # can catch below.
                        date_int = int(self.date)
                        # No exception?  Great, keep parsing the
                        # string (dateutil wants a string
                        # argument).
                        slashified = "%s/%s/%s" % (txn_date[0:2],
                                                   txn_date[2:4],
                                                   txn_date[4:])
                        return dateutil.parser.parse(slashified,
                                                     dayfirst=dayfirst)
                except:
                    pass

            # If we've made it this far, our guesses have failed.
            raise ValueError("Unrecognized date format: '%s'." % txn_date)
        else:
            return "UNKNOWN"

    def clean_date(self):
        pass

    def clean_amount(self):
        pass

    def clean_number(self):
        pass

    def clean_type(self):
        pass

    def clean_payee(self):
        pass

    def to_str(self):
        pass

    def __str__(self):
        pass


########NEW FILE########
__FILENAME__ = qif_converter
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.QifConverter - translate QIF files into OFX files.
#

import datetime
import dateutil.parser
import ofx
import ofxtools
import re
import sys
import xml.sax.saxutils as sax
from decimal import *
from time import localtime, strftime
from ofx.builder import *

class QifConverter:
    def __init__(self, qif, fid="UNKNOWN", org="UNKNOWN", bankid="UNKNOWN",
                 accttype="UNKNOWN", acctid="UNKNOWN", balance="UNKNOWN",
                 curdef=None, lang="ENG", dayfirst=False, debug=False):
        self.qif      = qif
        self.fid      = fid
        self.org      = org
        self.bankid   = bankid
        self.accttype = accttype
        self.acctid   = acctid
        self.balance  = balance
        self.curdef   = curdef
        self.lang     = lang
        self.debug    = debug
        self.dayfirst = dayfirst

        self.parsed_qif = None

        # FIXME: Move this to one of the OFX generation classes (Document or Response).
        self.txns_by_date = {}

        # This is a list of possible transaction types embedded in the
        # QIF Payee or Memo field (depending on bank and, it seems,
        # other factors).  The keys are used to match possible fields
        # that we can identify.  The values are used as substitutions,
        # since banks will use their own vernacular (like "DBT"
        # instead of "DEBIT") for some transaction types.  All of the
        # types in the values column (except "ACH", which is given
        # special treatment) are OFX-2.0 standard transaction types;
        # the keys are not all standard.  To add a new translation,
        # find the QIF name for the transaction type, and add it to
        # the keys column, then add the appropriate value from the
        # OFX-2.0 spec (see page 180 of doc/ofx/ofx-2.0/ofx20.pdf).
        # The substitution will be made if either the payee or memo
        # field begins with one of the keys followed by a "/", OR if
        # the payee or memo field exactly matches a key.
        self.txn_types = { "ACH"         : "ACH",
                           "CHECK CARD"  : "POS",
                           "CREDIT"      : "CREDIT",
                           "DBT"         : "DEBIT",
                           "DEBIT"       : "DEBIT",
                           "INT"         : "INT",
                           "DIV"         : "DIV",
                           "FEE"         : "FEE",
                           "SRVCHG"      : "SRVCHG",
                           "DEP"         : "DEP",
                           "DEPOSIT"     : "DEP",
                           "ATM"         : "ATM",
                           "POS"         : "POS",
                           "XFER"        : "XFER",
                           "CHECK"       : "CHECK",
                           "Checks"      : "CHECK",
                           "PAYMENT"     : "PAYMENT",
                           "CASH"        : "CASH",
                           "DIRECTDEP"   : "DIRECTDEP",
                           "DIRECTDEBIT" : "DIRECTDEBIT",
                           "REPEATPMT"   : "REPEATPMT",
                           "OTHER"       : "OTHER"        }

        # Some joker British bank starts QIF with a single bang and nothing
        # else.
        if re.match("!\n", self.qif) is not None:
            if self.debug: sys.stderr.write("Fixing typeless bang header.\n")
            self.qif = self.qif.replace("!", "!Type:Bank", 1)

        # Chase does not provide a Type header, so force one in the
        # case where it is omitted.
        if re.search("!Type:", self.qif, re.IGNORECASE) == None:
            if self.debug: sys.stderr.write("Forcing bank type header.\n")
            self.qif = "!Type:Bank\n" + self.qif

        acctblock = re.search("(!Account.*?\^\s*)", self.qif, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if acctblock is not None:
            block = acctblock.group(1)
            if self.debug:
                sys.stderr.write("Discarding account block from QIF file:\n%s" % block)
            self.qif = self.qif.replace(block, '', 1)

        # Some other personal finance program puts out a spurious transaction
        # showing current balance, but not as a balance -- instead as a
        # transaction before the type header.  And, there are a bunch of other
        # cases where crap before the type header is messing us up right now.
        # So, this is an awfully big hammer but one that at least lets people
        # import from other finance programs and broken banks.
        straycrap = re.search("^(.*?)!Type", self.qif, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if straycrap is not None:
            crap = straycrap.group(1)
            if len(crap) > 0:
              if self.debug:
                  sys.stderr.write("Discarding stray crap from beginning of QIF file:\n%s" % crap)
              self.qif = self.qif.replace(crap, '', 1)

        if self.debug: sys.stderr.write("Parsing document.\n")

        parser = ofxtools.QifParser(debug=debug)
        self.parsed_qif = parser.parse(self.qif)

        if self.debug: sys.stderr.write("Cleaning transactions.\n")

        # We do a two-pass conversion in order to check the dates of all
        # transactions in the statement, and convert all the dates using
        # the same date format.  The first pass does nothing but look
        # at dates; the second actually applies the date conversion and
        # all other conversions, and extracts information needed for
        # the final output (like date range).
        txn_list = self._extract_txn_list(self.parsed_qif)
        self._guess_formats(txn_list)
        self._clean_txn_list(txn_list)

    def _extract_txn_list(self, qif):
        stmt_obj = qif.asDict()["QifStatement"]

        if self.accttype == "UNKNOWN":
            if "BankTransactions" in stmt_obj:
                self.accttype = "CHECKING"
            elif "CreditCardTransactions" in stmt_obj:
                self.accttype = "CREDITCARD"

        txn_list = []
        for stmt in stmt_obj:
            for txn in stmt:
                txn_list.append(txn)

        return txn_list

    #
    # Date methods
    #

    def _guess_formats(self, txn_list):
        # Go through the transactions one at a time, and try to parse the date
        # field and currency format. If we check the date format and find a
        # transaction where the first number must be the day (that is, the first
        # number is in the range 13..31), then set the state of the converter to
        # use dayfirst for all transaction cleanups. This is a guess because the
        # method will only work for UK dates if the statement contains a day in
        # the 13..31 range. (We could also test whether a date appears out of
        # order, or whether the jumps between transactions are especially long,
        # if this guessing method doesn't work reliably.)
        for txn_obj in txn_list:
            txn = txn_obj.asDict()
            txn_date     = txn.get("Date",     "UNKNOWN")
            txn_currency = txn.get("Currency", "UNKNOWN")
            # Look for date format.
            parsed_date = self._parse_date(txn_date)
            self._check_date_format(parsed_date)
            # Look for currency format.
            if self.curdef is None and txn_currency == '^EUR':
                self.curdef = 'EUR'

    def _parse_date(self, txn_date, dayfirst=False):
        # Try as best we can to parse the date into a datetime object. Note:
        # this assumes that we never see a timestamp, just the date, in any
        # QIF date.
        if txn_date != "UNKNOWN":
            try:
                return dateutil.parser.parse(txn_date, dayfirst=dayfirst)

            except ValueError:
                # dateutil.parser doesn't recognize dates of the
                # format "MMDDYYYY", though it does recognize
                # "MM/DD/YYYY".  So, if parsing has failed above,
                # try shoving in some slashes and see if that
                # parses.
                try:
                    if len(txn_date) == 8:
                        # The int() cast will only succeed if all 8
                        # characters of txn_date are numbers.  If
                        # it fails, it will throw an exception we
                        # can catch below.
                        date_int = int(txn_date)
                        # No exception?  Great, keep parsing the
                        # string (dateutil wants a string
                        # argument).
                        slashified = "%s/%s/%s" % (txn_date[0:2],
                                                   txn_date[2:4],
                                                   txn_date[4:])
                        return dateutil.parser.parse(slashified,
                                                     dayfirst=dayfirst)
                except:
                    pass

            # If we've made it this far, our guesses have failed.
            raise ValueError("Unrecognized date format: '%s'." % txn_date)
        else:
            return "UNKNOWN"

    def _check_date_format(self, parsed_date):
        # If we *ever* find a date that parses as dayfirst, treat
        # *all* transactions in this statement as dayfirst.
        if parsed_date is not None and parsed_date != "UNKNOWN" and parsed_date.microsecond == 3:
            self.dayfirst = True

    #
    # Cleanup methods
    #

    def _clean_txn_list(self, txn_list):
        for txn_obj in txn_list:
            try:
                txn = self._clean_txn(txn_obj)
                txn_date = txn["Date"]
                txn_date_list = self.txns_by_date.get(txn_date, [])
                txn_date_list.append(txn)
                self.txns_by_date[txn_date] = txn_date_list
            except ValueError:
                # The _clean_txn method will sometimes find transactions
                # that are inherently unclean and are unable to be purified.
                # In these cases it will reject the transaction by throwing
                # a ValueError, which signals us not to store the transaction.
                if self.debug: sys.stderr.write("Skipping transaction '%s'." %
                                                str(txn_obj.asDict()))

        if len(txn_list) > 0:
            # Sort the dates (in YYYYMMDD format) and choose the lowest
            # date as our start date, and the highest date as our end
            # date.
            date_list = self.txns_by_date.keys()
            date_list.sort()

            self.start_date = date_list[0]
            self.end_date   = date_list[-1]

        else:
            # If we didn't get any transactions (which actually happens
            # quite a lot -- QIF statements are often just the type header,
            # presumably since there was no activity in the downloaded
            # statement), just assume that the start and end date were
            # both today.
            self.start_date = strftime("%Y%m%d", localtime())
            self.end_date   = self.start_date

    def _clean_txn(self, txn_obj):
        # This is sort of the brute-force method of the converter.  It
        # looks at the data we get from the bank and tries as hard as
        # possible to make best-effort guesses about what the OFX 2.0
        # standard values for the transaction should be.  There's a
        # reasonable amount of guesswork in here -- some of it wise,
        # maybe some of it not.  If the cleanup method determines that
        # the txn_obj shouldn't be in the data, it will throw a ValueError.
        # Otherwise, it will return a transaction cleaned to the best
        # of our abilities.
        txn = txn_obj.asDict()
        self._clean_txn_date(txn)
        self._clean_txn_amount(txn)
        self._clean_txn_number(txn)
        self._clean_txn_type(txn)
        self._clean_txn_payee(txn)
        return txn

    def _clean_txn_date(self, txn):
        txn_date    = txn.get("Date", "UNKNOWN").strip()
        if txn_date != "UNKNOWN":
            parsed_date = self._parse_date(txn_date, dayfirst=self.dayfirst)
            txn["Date"] = parsed_date.strftime("%Y%m%d")
        else:
            txn["Date"] = "UNKNOWN"

    def _clean_txn_amount(self, txn):
        txn_amount  = txn.get("Amount",  "00.00")
        txn_amount2 = txn.get("Amount2", "00.00")

        # Home Depot Credit Card seems to send two transaction records for each
        # transaction. They're out of order (that is, the second record is not
        # directly after the first, nor even necessarily after it at all), and
        # the second one *sometimes* appears to be a memo field on the first one
        # (e.g., a credit card payment will show up with an amount and date, and
        # then the next transaction will have the same date and a payee that
        # reads, "Thank you for your payment!"), and *sometimes* is the real
        # payee (e.g., the first will say "Home Depot" and the second will say
        # "Seasonal/Garden"). One of the two transaction records will have a
        # transaction amount of "-", and the other will have the real
        # transaction amount. Ideally, we would pull out the memo and attach it
        # to the right transaction, but unless the two transactions are the only
        # transactions on that date, there doesn't seem to be a good clue (order
        # in statement, amount, etc.) as to how to associate them. So, instead,
        # we're throwing a ValueError, which means this transaction should be removed
        # from the statement and not displayed to the user. The result is that
        # for Home Depot cards, sometimes we lose the memo (which isn't that big
        # a deal), and sometimes we make the memo into the payee (which sucks).
        if txn_amount == "-" or txn_amount == " ":
            raise ValueError("Transaction amount is undefined.")

        # Some QIF sources put the amount in Amount2 instead, for unknown
        # reasons.  Here we ignore Amount2 unless Amount is unknown.
        if txn_amount == "00.00":
            txn_amount = txn_amount2

        # Okay, now strip out whitespace padding.
        txn_amount = txn_amount.strip()

        # Some QIF files have dollar signs in the amount.  Hey, why not?
        txn_amount = txn_amount.replace('$', '', 1)

        # Some QIF files (usually from non-US banks) put the minus sign at
        # the end of the amount, rather than at the beginning. Let's fix that.
        if txn_amount[-1] == "-":
            txn_amount = "-" + txn_amount[:-1]

        # Some QIF sources put three digits after the decimal, and the Ruby
        # code thinks that means we're in Europe.  So.....let's deal with
        # that now.
        try:
            txn_amount = str(Decimal(txn_amount).quantize(Decimal('.01')))
        except:
            # Just keep truckin'.
            pass

        txn["Amount"] = txn_amount

    def _clean_txn_number(self, txn):
        txn_number  = txn.get("Number", "UNKNOWN").strip()
        txn_payee  = txn.get("Payee", "UNKNOWN").strip()

        # Clean up bad check number behavior
        all_digits = re.compile("\d+")

        if txn_number == "N/A":
            # Get rid of brain-dead Chase check number "N/A"s
            del txn["Number"]

        elif txn_number.startswith("XXXX-XXXX-XXXX"):
            # Home Depot credit cards throw THE CREDIT CARD NUMBER
            # into the check number field.  Oy!  At least they mask
            # the first twelve digits, so we know they're insane.
            del txn["Number"]

        elif txn_number != "UNKNOWN" and self.accttype == "CREDITCARD":
            # Several other credit card companies (MBNA, CapitalOne)
            # seem to use the number field as a transaction ID.  Get
            # rid of this.
            del txn["Number"]

        elif txn_number == "0000000000" and self.accttype != "CREDITCARD":
            # There's some bank that puts "N0000000000" in every non-check
            # transaction.  (They do use normal check numbers for checks.)
            del txn["Number"]

        elif txn_number != "UNKNOWN" and all_digits.search(txn_number):
            # Washington Mutual doesn't indicate a CHECK transaction
            # when a check number is present.
            txn["Type"] = "CHECK"

        elif txn_payee.startswith("CHECK # "):
            # USAA QIF export sends blank number fields but has the check
            # number in the payee field instead padded with leading zeros
            number = re.search("^CHECK # (\d+)", txn_payee)
            if number is not None:
                txn["Number"] = number.group(1).lstrip('0')

    def _clean_txn_type(self, txn):
        txn_type    = "UNKNOWN"
        txn_amount  = txn.get("Amount", "UNKNOWN")
        txn_payee   = txn.get("Payee",  "UNKNOWN")
        txn_memo    = txn.get("Memo",   "UNKNOWN")
        txn_number  = txn.get("Number", "UNKNOWN")
        txn_sign    = self._txn_sign(txn_amount)

        # Try to figure out the transaction type from the Payee or
        # Memo field.
        for typestr in self.txn_types.keys():
            if txn_number == typestr:
                # US Bank sends "DEBIT" or "CREDIT" as a check number
                # on credit card transactions.
                txn["Type"] = self.txn_types[typestr]
                del txn["Number"]
                break

            elif txn_payee.startswith(typestr + "/") or \
            txn_memo.startswith(typestr + "/") or \
            txn_memo == typestr or txn_payee == typestr:
                if typestr == "ACH" and txn_sign == "credit":
                    txn["Type"] = "DIRECTDEP"

                elif typestr == "ACH" and txn_sign == "debit":
                    txn["Type"] = "DIRECTDEBIT"

                else:
                    txn["Type"] = self.txn_types[typestr]
                break

    def _clean_txn_payee(self, txn):
        txn_payee   = txn.get("Payee",  "UNKNOWN")
        txn_memo    = txn.get("Memo",   "UNKNOWN")
        txn_number  = txn.get("Number", "UNKNOWN")
        txn_type    = txn.get("Type",   "UNKNOWN")
        txn_amount  = txn.get("Amount", "UNKNOWN")
        txn_sign    = self._txn_sign(txn_amount)

        # Try to fill in the payee field with some meaningful value.
        if txn_payee == "UNKNOWN":
            if txn_number != "UNKNOWN" and (self.accttype == "CHECKING" or
            self.accttype == "SAVINGS"):
                txn["Payee"] = "Check #%s" % txn_number
                txn["Type"]  = "CHECK"

            elif txn_type == "INT" and txn_sign == "debit":
                txn["Payee"] = "Interest paid"

            elif txn_type == "INT" and txn_sign == "credit":
                txn["Payee"] = "Interest earned"

            elif txn_type == "ATM" and txn_sign == "debit":
                txn["Payee"] = "ATM Withdrawal"

            elif txn_type == "ATM" and txn_sign == "credit":
                txn["Payee"] = "ATM Deposit"

            elif txn_type == "POS" and txn_sign == "debit":
                txn["Payee"] = "Point of Sale Payment"

            elif txn_type == "POS" and txn_sign == "credit":
                txn["Payee"] = "Point of Sale Credit"

            elif txn_memo != "UNKNOWN":
                txn["Payee"] = txn_memo

            # Down here, we have no payee, no memo, no check number,
            # and no type.  Who knows what this stuff is.
            elif txn_type == "UNKNOWN" and txn_sign == "debit":
                txn["Payee"] = "Other Debit"
                txn["Type"]  = "DEBIT"

            elif txn_type == "UNKNOWN" and txn_sign == "credit":
                txn["Payee"] = "Other Credit"
                txn["Type"]  = "CREDIT"

        # Make sure the transaction type has some valid value.
        if not txn.has_key("Type") and txn_sign == "debit":
            txn["Type"] = "DEBIT"

        elif not txn.has_key("Type") and txn_sign == "credit":
            txn["Type"] = "CREDIT"

    def _txn_sign(self, txn_amount):
        # Is this a credit or a debit?
        if txn_amount.startswith("-"):
            return "debit"
        else:
            return "credit"

    #
    # Conversion methods
    #

    def to_ofx102(self):
        if self.debug: sys.stderr.write("Making OFX/1.02.\n")
        return DOCUMENT(self._ofx_header(),
                        OFX(self._ofx_signon(),
                            self._ofx_stmt()))

    def to_xml(self):
        ofx102 = self.to_ofx102()

        if self.debug:
            sys.stderr.write(ofx102 + "\n")
            sys.stderr.write("Parsing OFX/1.02.\n")
        response = ofx.Response(ofx102) #, debug=self.debug)

        if self.debug: sys.stderr.write("Making OFX/2.0.\n")
        if self.dayfirst:
            date_format = "DD/MM/YY"
        else:
            date_format = "MM/DD/YY"
        xml = response.as_xml(original_format="QIF", date_format=date_format)

        return xml

    # FIXME: Move the remaining methods to ofx.Document or ofx.Response.

    def _ofx_header(self):
        return HEADER(
            OFXHEADER("100"),
            DATA("OFXSGML"),
            VERSION("102"),
            SECURITY("NONE"),
            ENCODING("USASCII"),
            CHARSET("1252"),
            COMPRESSION("NONE"),
            OLDFILEUID("NONE"),
            NEWFILEUID("NONE"))

    def _ofx_signon(self):
        return SIGNONMSGSRSV1(
            SONRS(
                STATUS(
                  CODE("0"),
                  SEVERITY("INFO"),
                  MESSAGE("SUCCESS")),
                DTSERVER(self.end_date),
                LANGUAGE(self.lang),
                FI(
                    ORG(self.org),
                    FID(self.fid))))

    def _ofx_stmt(self):
        # Set default currency here, instead of on init, so that the caller
        # can override the currency format found in the QIF file if desired.
        # See also _guess_formats(), above.
        if self.curdef is None:
            curdef = "USD"
        else:
            curdef = self.curdef

        if self.accttype == "CREDITCARD":
            return CREDITCARDMSGSRSV1(
                CCSTMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    CCSTMTRS(
                        CURDEF(curdef),
                        CCACCTFROM(
                            ACCTID(self.acctid)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))
        else:
            return BANKMSGSRSV1(
                STMTTRNRS(
                    TRNUID("0"),
                    self._ofx_status(),
                    STMTRS(
                        CURDEF(curdef),
                        BANKACCTFROM(
                            BANKID(self.bankid),
                            ACCTID(self.acctid),
                            ACCTTYPE(self.accttype)),
                        self._ofx_txns(),
                        self._ofx_ledgerbal(),
                        self._ofx_availbal())))

    def _ofx_status(self):
        return STATUS(
            CODE("0"),
            SEVERITY("INFO"),
            MESSAGE("SUCCESS"))

    def _ofx_ledgerbal(self):
        return LEDGERBAL(
            BALAMT(self.balance),
            DTASOF(self.end_date))

    def _ofx_availbal(self):
        return AVAILBAL(
            BALAMT(self.balance),
            DTASOF(self.end_date))

    def _ofx_txns(self):
        txns = ""

        # OFX transactions appear most recent first, and oldest last,
        # so we do a reverse sort of the dates in this statement.
        date_list = self.txns_by_date.keys()
        date_list.sort()
        date_list.reverse()
        for date in date_list:
            txn_list = self.txns_by_date[date]
            txn_index = len(txn_list)
            for txn in txn_list:
                txn_date = txn.get("Date", "UNKNOWN")
                txn_amt  = txn.get("Amount", "00.00")

                # Make a synthetic transaction ID using as many
                # uniqueness guarantors as possible.
                txn["ID"] = "%s-%s-%s-%s-%s" % (self.org, self.accttype,
                                                txn_date, txn_index,
                                                txn_amt)
                txns += self._ofx_txn(txn)
                txn_index -= 1

        # FIXME: This should respect the type of statement being generated.
        return BANKTRANLIST(
            DTSTART(self.start_date),
            DTEND(self.end_date),
            txns)

    def _ofx_txn(self, txn):
        fields = []
        if self._check_field("Type", txn):
            fields.append(TRNTYPE(txn["Type"].strip()))

        if self._check_field("Date", txn):
            fields.append(DTPOSTED(txn["Date"].strip()))

        if self._check_field("Amount", txn):
            fields.append(TRNAMT(txn["Amount"].strip()))

        if self._check_field("Number", txn):
            fields.append(CHECKNUM(txn["Number"].strip()))

        if self._check_field("ID", txn):
            fields.append(FITID(txn["ID"].strip()))

        if self._check_field("Payee", txn):
            fields.append(NAME(sax.escape(sax.unescape(txn["Payee"].strip()))))

        if self._check_field("Memo", txn):
            fields.append(MEMO(sax.escape(sax.unescape(txn["Memo"].strip()))))

        return STMTTRN(*fields)

    def _check_field(self, key, txn):
        return txn.has_key(key) and txn[key].strip() != ""



########NEW FILE########
__FILENAME__ = qif_parser
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  ofx.QifParser - comprehend the mess that is QIF.
#

import ofxtools
from pyparsing import CaselessLiteral, Group, LineEnd, Literal, \
    MatchFirst, oneOf, OneOrMore, Optional, Or, restOfLine, SkipTo, \
    White, Word, ZeroOrMore

class QifParser:
    def __init__(self, debug=False):
        account_items       = { 'N' : "Name",
                                'T' : "AccountType",
                                'D' : "Description",
                                'L' : "CreditLimit",
                                'X' : "UnknownField",
                                'B' : "Balance",
                                '/' : "BalanceDate",
                                '$' : "Balance" }
        
        noninvestment_items = { 'D' : "Date",
                                'T' : "Amount",
                                'U' : "Amount2",
                                'C' : "Cleared",
                                'N' : "Number",
                                'P' : "Payee",
                                'M' : "Memo",
                                'L' : "Category",
                                'A' : "Address",
                                'S' : "SplitCategory",
                                'E' : "SplitMemo",
                                '$' : "SplitAmount",
                                '-' : "NegativeSplitAmount" }
        
        investment_items    = { 'D' : "Date",
                                'N' : "Action",
                                'Y' : "Security",
                                'I' : "Price",
                                'Q' : "Quantity",
                                'T' : "Amount",
                                'C' : "Cleared",
                                'P' : "Text",
                                'M' : "Memo",
                                'O' : "Commission",
                                'L' : "TransferAccount",
                                '$' : "TransferAmount" }
        
        category_items      = { 'N' : "Name",
                                'D' : "Description",
                                'T' : "TaxRelated",
                                'I' : "IncomeCategory",
                                'E' : "ExpenseCategory",
                                'B' : "BudgetAmount",
                                'R' : "TaxSchedule" }
        
        class_items         = { 'N' : "Name",
                                'D' : "Description" }
        
        options   = Group(CaselessLiteral('!Option:') + restOfLine).suppress()
        
        banktxns  = Group(CaselessLiteral('!Type:Bank').suppress() + 
                          ZeroOrMore(Or([self._items(noninvestment_items),
                                         options]))
                          ).setResultsName("BankTransactions")
        
        cashtxns  = Group(CaselessLiteral('!Type:Cash').suppress() + 
                          ZeroOrMore(Or([self._items(noninvestment_items),
                                         options]))
                          ).setResultsName("CashTransactions")
        
        ccardtxns = Group(Or([CaselessLiteral('!Type:CCard').suppress(),
                              CaselessLiteral('!Type!CCard').suppress()]) + 
                          ZeroOrMore(Or([self._items(noninvestment_items),
                                         options]))
                          ).setResultsName("CreditCardTransactions")
        
        liabilitytxns = Group(CaselessLiteral('!Type:Oth L').suppress() + 
                          ZeroOrMore(Or([self._items(noninvestment_items),
                                         options]))
                          ).setResultsName("CreditCardTransactions")
        
        invsttxns = Group(CaselessLiteral('!Type:Invst').suppress() + 
                          ZeroOrMore(self._items(investment_items))
                          ).setResultsName("InvestmentTransactions")
        
        acctlist  = Group(CaselessLiteral('!Account').suppress() +
                          ZeroOrMore(Or([self._items(account_items, name="AccountInfo")]))
                          ).setResultsName("AccountList")
        
        category  = Group(CaselessLiteral('!Type:Cat').suppress() +
                          ZeroOrMore(self._items(category_items))
                          ).setResultsName("CategoryList")
        
        classlist = Group(CaselessLiteral('!Type:Class').suppress() +
                          ZeroOrMore(self._items(category_items))
                          ).setResultsName("ClassList")
        
        self.parser = Group(ZeroOrMore(White()).suppress() +
                            ZeroOrMore(acctlist).suppress() +
                            OneOrMore(ccardtxns | cashtxns | banktxns | liabilitytxns | invsttxns) +
                            ZeroOrMore(White()).suppress()
                            ).setResultsName("QifStatement")
        
        if (debug):
            self.parser.setDebugActions(ofxtools._ofxtoolsStartDebugAction, 
                                        ofxtools._ofxtoolsSuccessDebugAction, 
                                        ofxtools._ofxtoolsExceptionDebugAction)
        
    
    def _items(self, items, name="Transaction"):
        item_list = []
        for (code, name) in items.iteritems():
            item = self._item(code, name)
            item_list.append(item)
        return Group(OneOrMore(Or(item_list)) +
                     oneOf('^EUR ^').setResultsName('Currency') +
                     LineEnd().suppress()
                     ).setResultsName(name)
    
    def _item(self, code, name):
        return CaselessLiteral(code).suppress() + \
               restOfLine.setResultsName(name) + \
               LineEnd().suppress()
    
    def parse(self, qif):
        return self.parser.parseString(qif)
    

########NEW FILE########
__FILENAME__ = mock_ofx_server
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# MockOfxServer - simple mock server for testing
#

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx_test_utils

import urllib2
from wsgi_intercept.urllib2_intercept import install_opener
import wsgi_intercept

class MockOfxServer:
    def __init__(self, port=9876):
        install_opener()
        wsgi_intercept.add_wsgi_intercept('localhost', port, self.interceptor)
    
    def handleResponse(self, environment, start_response):
        status  = "200 OK"
        headers = [('Content-Type', 'application/ofx')]
        start_response(status, headers)
        if environment.has_key("wsgi.input"):
            request_body = environment["wsgi.input"].read()
            
            if request_body.find("<ACCTTYPE>CHECKING") != -1:
                return ofx_test_utils.get_checking_stmt()
            elif request_body.find("<ACCTTYPE>SAVINGS") != -1:
                return ofx_test_utils.get_savings_stmt()
            else:
                return ofx_test_utils.get_creditcard_stmt()
        else:
            return ofx_test_utils.get_creditcard_stmt()
    
    def interceptor(self):
        return self.handleResponse

import unittest

class MockOfxServerTest(unittest.TestCase):
    def setUp(self):
        self.server = MockOfxServer()
        self.success = ofx_test_utils.get_creditcard_stmt()
    
    def test_simple_get(self):
        result = urllib2.urlopen('http://localhost:9876/')
        self.assertEqual(result.read(), self.success)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = ofxtools_qif_converter
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofxtools
import textwrap
import unittest
from pyparsing import ParseException
from time import localtime, strftime

class QifConverterTests(unittest.TestCase):
    def setUp(self):
        pass
    
    def test_bank_stmttype(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.accttype, "CHECKING")
    
    def test_ccard_stmttype(self):
        qiftext = textwrap.dedent('''\
        !Type:CCard
        D01/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.accttype, "CREDITCARD")
    
    def test_no_stmttype(self):
        qiftext = textwrap.dedent('''\
        D01/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.accttype, "CHECKING")
    
    def test_no_txns(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        ''')
        today = strftime("%Y%m%d", localtime())
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.start_date, today)
        self.assertEqual(converter.end_date, today)
    
    def test_us_date(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertTrue(converter.txns_by_date.has_key("20050113"))
    
    def test_uk_date(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D13/01/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertTrue(converter.txns_by_date.has_key("20050113"))
    
    def test_ambiguous_date(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D12/01/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertTrue(converter.txns_by_date.has_key("20051201"))
    
    def test_mixed_us_dates(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/12/2005
        ^
        D01/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertTrue(converter.txns_by_date.has_key("20050112"))
        self.assertTrue(converter.txns_by_date.has_key("20050113"))
    
    def test_mixed_uk_dates(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D12/01/2005
        ^
        D13/01/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertTrue(converter.txns_by_date.has_key("20050112"))
        self.assertTrue(converter.txns_by_date.has_key("20050113"))
    
    def test_slashfree_date(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D12012005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertTrue(converter.txns_by_date.has_key("20051201"))
    
    def test_unparseable_date(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        DFnargle
        ^
        ''')
        self.assertRaises(ValueError, ofxtools.QifConverter, qiftext)
    
    def test_len_eight_no_int_date(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        DAAAAAAAA
        ^
        ''')
        self.assertRaises(ValueError, ofxtools.QifConverter, qiftext)
    
    def test_asc_dates(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/13/2005
        ^
        D01/27/2005
        ^
        D02/01/2005
        ^
        D02/01/2005
        ^        
        D02/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.start_date, "20050113")
        self.assertEqual(converter.end_date, "20050213")
        self.assertEqual(len(converter.txns_by_date.keys()), 4)
    
    def test_desc_dates(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D02/13/2005
        ^
        D02/01/2005
        ^
        D02/01/2005
        ^        
        D01/27/2005
        ^
        D01/13/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.start_date, "20050113")
        self.assertEqual(converter.end_date, "20050213")
        self.assertEqual(len(converter.txns_by_date.keys()), 4)
    
    def test_mixed_dates(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D02/01/2005
        ^
        D02/13/2005
        ^
        D01/13/2005
        ^
        D02/01/2005
        ^        
        D01/27/2005
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        self.assertEqual(converter.start_date, "20050113")
        self.assertEqual(converter.end_date, "20050213")
        self.assertEqual(len(converter.txns_by_date.keys()), 4)
    
    def test_default_currency(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.93
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        ofx102 = converter.to_ofx102()
        self.assertTrue(ofx102.find('<CURDEF>USD') != -1)
    
    def test_found_currency(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.93
        ^EUR
        ''')
        converter = ofxtools.QifConverter(qiftext)
        ofx102 = converter.to_ofx102()
        self.assertTrue(ofx102.find('<CURDEF>EUR') != -1)
    
    def test_explicit_currency(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.93
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext, curdef='GBP')
        ofx102 = converter.to_ofx102()
        self.assertTrue(ofx102.find('<CURDEF>GBP') != -1)
    
    def test_amount2(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D02/01/2005
        U25.42
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20050201"][0]
        self.assertEqual(txn["Amount"], "25.42")
    
    def test_bad_amount_precision(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.930
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20070125"][0]
        self.assertEqual(txn["Amount"], "417.93")
    
    def test_dash_amount(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D02/01/2005
        T25.42
        ^
        D02/01/2005
        T-
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn_list = converter.txns_by_date["20050201"]
        self.assertEqual(len(txn_list), 1)
        txn = txn_list[0]
        self.assertEqual(txn["Amount"], "25.42")
    
    def test_trailing_minus(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D08/06/2008
        T26.24-
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20080806"][0]
        self.assertEqual(txn["Amount"], "-26.24")
    
    def test_n_a_number(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.93
        NN/A
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20070125"][0]
        self.assertEqual(txn.has_key("Number"), False)
    
    def test_creditcard_number(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.93
        NXXXX-XXXX-XXXX-1234
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20070125"][0]
        self.assertEqual(txn.has_key("Number"), False)
    
    def test_creditcard_stmt_number(self):
        qiftext = textwrap.dedent('''\
        !Type:CCard
        D01/25/2007
        T417.93
        N1234
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20070125"][0]
        self.assertEqual(txn.has_key("Number"), False)
    
    def test_check_stmt_number(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T417.93
        N1234
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20070125"][0]
        self.assertEqual(txn.get("Type"), "CHECK")
    
    def test_usaa_check(self):
        qiftext = textwrap.dedent('''\
        !Type:Bank
        D01/25/2007
        T-22.00
        N
        PCHECK # 0000005287
        MChecks
        ^
        ''')
        converter = ofxtools.QifConverter(qiftext)
        txn = converter.txns_by_date["20070125"][0]
        self.assertEqual(txn.get("Type"), "CHECK")
        self.assertEqual(txn.get("Number"), "5287")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_account
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import unittest

class AccountTests(unittest.TestCase):
    def setUp(self):
        self.institution = ofx.Institution(name="Test Bank", 
                                           ofx_org="Test Bank", 
                                           ofx_url="https://ofx.example.com", 
                                           ofx_fid="9999999")
        self.good_acct = ofx.Account(acct_type="CHECKING", 
                                     acct_number="1122334455", 
                                     aba_number="123456789", 
                                     institution=self.institution)
        self.bad_acct  = ofx.Account(acct_type="Fnargle",
                                     acct_number="", aba_number="", 
                                     institution=None)
    
    def test_account_complete(self):
        self.assertEqual(self.good_acct.is_complete(), True)
        self.assertEqual(self.bad_acct.is_complete(), False)
    
    def test_as_dict(self):
        testdict = self.good_acct.as_dict()
        self.assertEqual(testdict["acct_type"], "CHECKING")
        self.assertEqual(testdict["acct_number"], "1122334455")
        self.assertEqual(testdict["aba_number"], "123456789")
        self.assertEqual(testdict["desc"], None)
        self.assertEqual(testdict["balance"], None)
        
        fi_dict = testdict["institution"]
        self.assertEqual(fi_dict["name"], "Test Bank")
        self.assertEqual(fi_dict["ofx_org"], "Test Bank")
        self.assertEqual(fi_dict["ofx_url"], "https://ofx.example.com")
        self.assertEqual(fi_dict["ofx_fid"], "9999999")
    
    def test_load_from_dict(self):
        testdict = self.good_acct.as_dict()
        new_acct = ofx.Account.load_from_dict(testdict)
        self.assertEqual(new_acct.acct_type, "CHECKING")
        self.assertEqual(new_acct.acct_number, "1122334455")
        self.assertEqual(new_acct.aba_number, "123456789")
        self.assertEqual(new_acct.desc, None)
        self.assertEqual(new_acct.balance, None)
        
        new_fi = ofx.Institution.load_from_dict(testdict['institution'])
        self.assertEqual(new_fi.name, "Test Bank")
        self.assertEqual(new_fi.ofx_org, "Test Bank")
        self.assertEqual(new_fi.ofx_url, "https://ofx.example.com")
        self.assertEqual(new_fi.ofx_fid, "9999999")
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_builder
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

from ofx.builder import *
from ofx.builder import Tag  # not exported by default
import unittest

class BuilderTests(unittest.TestCase):
    def test_blank_node(self):
        """Test generation of a blank node tag."""
        BLANK = Tag("BLANK")
        self.assertEqual("<BLANK>\r\n", BLANK())
    
    def test_node(self):
        """Test generation of a node tag."""
        NODE = Tag("NODE")
        self.assertEqual("<NODE>text\r\n", NODE("text"))
    
    def test_blank_aggregate_node(self):
        """Test generation of an empty aggregate tag."""
        AGGREGATE = Tag("AGGREGATE", aggregate=True)
        self.assertEqual("<AGGREGATE>\r\n</AGGREGATE>\r\n", AGGREGATE())
    
    def test_nested_tags(self):
        """Test generation of an aggregate containing three nodes."""
        ONE = Tag("ONE")
        TWO = Tag("TWO")
        THREE = Tag("THREE")
        CONTAINER = Tag("CONTAINER", aggregate=True)
        self.assertEqual(
            "<CONTAINER>\r\n<ONE>one\r\n<TWO>two\r\n<THREE>three\r\n</CONTAINER>\r\n",
            CONTAINER(ONE("one"), TWO("two"), THREE("three")))
    
    def test_blank_header(self):
        """Test generation of a blank header."""
        HEADER = Tag("HEADER", header=True)
        self.assertEqual("HEADER:\r\n", HEADER())
    
    def test_header(self):
        """Test generation of a header."""
        ONE = Tag("ONE", header=True)
        self.assertEqual("ONE:value\r\n", ONE("value"))
    
    def test_blank_header_block(self):
        """Stupid test of a blank header block."""
        BLOCK = Tag("", header_block=True)
        self.assertEqual("\r\n", BLOCK())
    
    def test_header_block(self):
        ONE = Tag("ONE", header=True)
        TWO = Tag("TWO", header=True)
        THREE = Tag("THREE", header=True)
        BLOCK = Tag("", header_block=True)
        self.assertEqual("ONE:one\r\nTWO:two\r\nTHREE:three\r\n\r\n",
            BLOCK(ONE("one"), TWO("two"), THREE("three")))
    
    def test_bankaccount_request(self):
        """Generate a full, real OFX message, and compare it to static
        test data."""
        testquery = DOCUMENT(
            HEADER(
                OFXHEADER("100"),
                DATA("OFXSGML"),
                VERSION("102"),
                SECURITY("NONE"),
                ENCODING("USASCII"),
                CHARSET("1252"),
                COMPRESSION("NONE"),
                OLDFILEUID("NONE"),
                NEWFILEUID("9B33CA3E-C237-4577-8F00-7AFB0B827B5E")),
            OFX(
                SIGNONMSGSRQV1(
                    SONRQ(
                        DTCLIENT("20060221150810"),
                        USERID("username"),
                        USERPASS("userpass"),
                        LANGUAGE("ENG"),
                        FI(
                            ORG("FAKEOFX"),
                            FID("1000")),
                        APPID("MONEY"),
                        APPVER("1200"))),
                BANKMSGSRQV1(
                    STMTTRNRQ(
                        TRNUID("9B33CA3E-C237-4577-8F00-7AFB0B827B5E"),
                        CLTCOOKIE("4"),
                        STMTRQ(
                            BANKACCTFROM(
                                BANKID("2000"),
                                ACCTID("12345678"),
                                ACCTTYPE("CHECKING")),
                            INCTRAN(
                                DTSTART("20060221150810"),
                                INCLUDE("Y")))))))
        
        controlquery = "OFXHEADER:100\r\nDATA:OFXSGML\r\nVERSION:102\r\nSECURITY:NONE\r\nENCODING:USASCII\r\nCHARSET:1252\r\nCOMPRESSION:NONE\r\nOLDFILEUID:NONE\r\nNEWFILEUID:9B33CA3E-C237-4577-8F00-7AFB0B827B5E\r\n\r\n<OFX>\r\n<SIGNONMSGSRQV1>\r\n<SONRQ>\r\n<DTCLIENT>20060221150810\r\n<USERID>username\r\n<USERPASS>userpass\r\n<LANGUAGE>ENG\r\n<FI>\r\n<ORG>FAKEOFX\r\n<FID>1000\r\n</FI>\r\n<APPID>MONEY\r\n<APPVER>1200\r\n</SONRQ>\r\n</SIGNONMSGSRQV1>\r\n<BANKMSGSRQV1>\r\n<STMTTRNRQ>\r\n<TRNUID>9B33CA3E-C237-4577-8F00-7AFB0B827B5E\r\n<CLTCOOKIE>4\r\n<STMTRQ>\r\n<BANKACCTFROM>\r\n<BANKID>2000\r\n<ACCTID>12345678\r\n<ACCTTYPE>CHECKING\r\n</BANKACCTFROM>\r\n<INCTRAN>\r\n<DTSTART>20060221150810\r\n<INCLUDE>Y\r\n</INCTRAN>\r\n</STMTRQ>\r\n</STMTTRNRQ>\r\n</BANKMSGSRQV1>\r\n</OFX>"
        self.assertEqual(testquery, controlquery)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_client
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx_test_utils
import ofx
from mock_ofx_server import MockOfxServer

import unittest

class ClientTests(unittest.TestCase):
    def setUp(self):
        self.port    = 9486
        self.server  = MockOfxServer(port=self.port)
        self.mockurl = "http://localhost:" + str(self.port) + "/"
        self.institution = ofx.Institution(ofx_org="Test Bank", 
                                           ofx_fid="99999",
                                           ofx_url=self.mockurl)
        self.checking_account = ofx.Account(acct_number="1122334455", 
                                            aba_number="12345678", 
                                            acct_type="Checking",
                                            institution=self.institution)
        self.savings_account = ofx.Account(acct_number="1122334455", 
                                           aba_number="12345678", 
                                           acct_type="Savings",
                                           institution=self.institution)
        self.creditcard_account = ofx.Account(acct_number="1122334455", 
                                              aba_number="12345678", 
                                              acct_type="Credit Card",
                                              institution=self.institution)
        self.username = "username"
        self.password = "password"
        self.client  = ofx.Client()
        self.checking_stmt = ofx_test_utils.get_checking_stmt()
        self.savings_stmt = ofx_test_utils.get_savings_stmt()
        self.creditcard_stmt = ofx_test_utils.get_creditcard_stmt()
    
    def test_checking_stmt_request(self):
        response = self.client.get_bank_statement(self.checking_account,
                                                  self.username,
                                                  self.password)
        self.assertEqual(response.as_string(), self.checking_stmt)
    
    def test_savings_stmt_request(self):
        response = self.client.get_bank_statement(self.savings_account,
                                                  self.username,
                                                  self.password)
        self.assertEqual(response.as_string(), self.savings_stmt)
    
    def test_creditcard_stmt_request(self):
        response = self.client.get_creditcard_statement(self.creditcard_account,
                                                        self.username,
                                                        self.password)
        self.assertEqual(response.as_string(), self.creditcard_stmt)
    
    def test_unknown_stmt_request(self):
        checking_response = self.client.get_statement(self.checking_account,
                                                      self.username,
                                                      self.password)
        self.assertEqual(checking_response.as_string(), self.checking_stmt)
        
        savings_response = self.client.get_statement(self.savings_account, 
                                                     self.username,
                                                     self.password)
        self.assertEqual(savings_response.as_string(), self.savings_stmt)
        
        creditcard_response = self.client.get_statement(self.creditcard_account,
                                                        self.username,
                                                        self.password)
        self.assertEqual(creditcard_response.as_string(), self.creditcard_stmt)
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_document
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import ofx_test_utils

import unittest

class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.checking = ofx_test_utils.get_checking_stmt()        
    
    def test_statement_as_xml(self):
        response = ofx.Response(self.checking)
        self.assertEqual('<?xml version="1.0"', response.as_xml()[:19])
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_error
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import unittest

class ErrorTests(unittest.TestCase):    
    def test_ofx_error_to_str(self):
        error = ofx.Error("test", code=9999, severity="ERROR", message="Test")
        expected = "Test\n(ERROR 9999: Unknown error code)"
        self.assertEqual(expected, error.str())
        self.assertEqual(expected, str(error))
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_parser
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import ofx_test_utils

import os
import unittest

class ParserTests(unittest.TestCase):
    def setUp(self):
        parser = ofx.Parser()
        checking_stmt = ofx_test_utils.get_checking_stmt()
        creditcard_stmt = ofx_test_utils.get_creditcard_stmt()
        self.checkparse = parser.parse(checking_stmt)
        self.creditcardparse = parser.parse(creditcard_stmt)
    
    def test_successful_parse(self):
        """Test parsing a valid OFX document containing a 'success' message."""
        self.assertEqual("SUCCESS",
            self.checkparse["body"]["OFX"]["SIGNONMSGSRSV1"]["SONRS"]["STATUS"]["MESSAGE"])
    
    def test_body_read(self):
        """Test reading a value from deep in the body of the OFX document."""
        self.assertEqual("-5128.16",
            self.creditcardparse["body"]["OFX"]["CREDITCARDMSGSRSV1"]["CCSTMTTRNRS"]["CCSTMTRS"]["LEDGERBAL"]["BALAMT"])
    
    def test_header_read(self):
        """Test reading a header from the OFX document."""
        self.assertEqual("100", self.checkparse["header"]["OFXHEADER"])
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_request
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import unittest

class RequestTests(unittest.TestCase):
    def setUp(self):
        self.request = ofx.Request()
        self.institution = ofx.Institution(ofx_org="fi_name", ofx_fid="1000")
        self.account = ofx.Account(acct_number="00112233",
                                   aba_number="12345678",
                                   acct_type="Checking",
                                   institution=self.institution)
        self.username = "joeuser"
        self.password = "mypasswd"
        self.parser  = ofx.Parser()

    # FIXME: Need to add tests for date formatting.

    def test_header(self):
        """Test the correctness of an OFX document header by examining
        some of the dynamically-generated values at the bottom of the
        header.  This test uses a bank statement request, since that
        is our most common use, and since that will build a full, parsable
        document, including the header."""
        parsetree = self.parser.parse(self.request.bank_stmt(self.account,
                                                             self.username,
                                                             self.password))
        self.assertEqual("NONE", parsetree["header"]["OLDFILEUID"])
        self.assertNotEqual("NONE", parsetree["header"]["NEWFILEUID"])

    def test_sign_on(self):
        """Test the OFX document sign-on block, using a bank statement
        request again."""
        parsetree = self.parser.parse(self.request.bank_stmt(self.account,
                                                             self.username,
                                                             self.password))
        # FIXME: add DTCLIENT test here.
        signon = parsetree["body"]["OFX"]["SIGNONMSGSRQV1"]["SONRQ"]
        self.assertEqual("joeuser", signon["USERID"])
        self.assertEqual("mypasswd", signon["USERPASS"])
        self.assertEqual("fi_name", signon["FI"]["ORG"])
        self.assertEqual("1000", signon["FI"]["FID"])
        self.assertEqual("Money", signon["APPID"])
        self.assertEqual("1400", signon["APPVER"])

    def test_account_info(self):
        """Test the values sent for an account info request."""
        parsetree = self.parser.parse(self.request.account_info(self.institution,
                                                                self.username,
                                                                self.password))
        info = parsetree["body"]["OFX"]["SIGNUPMSGSRQV1"]["ACCTINFOTRNRQ"]
        self.assertNotEqual("NONE", info["TRNUID"])
        self.assertEqual("4", info["CLTCOOKIE"])
        self.assertEqual("19980101", info["ACCTINFORQ"]["DTACCTUP"])

    def test_bank_stmt(self):
        """Test the specific values for a bank statement request."""
        parsetree = self.parser.parse(self.request.bank_stmt(self.account,
                                                             self.username,
                                                             self.password))
        stmt = parsetree["body"]["OFX"]["BANKMSGSRQV1"]["STMTTRNRQ"]
        self.assertNotEqual("NONE", stmt["TRNUID"])
        self.assertEqual("4", stmt["CLTCOOKIE"])
        self.assertEqual("12345678", stmt["STMTRQ"]["BANKACCTFROM"]["BANKID"])
        self.assertEqual("00112233", stmt["STMTRQ"]["BANKACCTFROM"]["ACCTID"])
        self.assertEqual("CHECKING",stmt["STMTRQ"]["BANKACCTFROM"]["ACCTTYPE"])
        # FIXME: Add DTSTART and DTEND tests here.

    def test_creditcard_stmt(self):
        """Test the specific values for a credit card statement request."""
        self.account.acct_number = "412345678901"
        parsetree = self.parser.parse(self.request.creditcard_stmt(self.account,
                                                                   self.username,
                                                                   self.password))
        stmt = parsetree["body"]["OFX"]["CREDITCARDMSGSRQV1"]["CCSTMTTRNRQ"]
        self.assertNotEqual("NONE", stmt["TRNUID"])
        self.assertEqual("4", stmt["CLTCOOKIE"])
        self.assertEqual("412345678901", stmt["CCSTMTRQ"]["CCACCTFROM"]["ACCTID"])
        # FIXME: Add DTSTART and DTEND tests here.

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_response
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import ofx_test_utils

import os
import pprint
import unittest
from xml.parsers.expat import ExpatError
import xml.etree.ElementTree as ElementTree 

class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.response_text = ofx_test_utils.get_checking_stmt()
        self.response = ofx.Response(self.response_text)

    def test_signon_success(self):
        status = self.response.check_signon_status()
        self.assertTrue(status)

    def test_account_list(self):
        statements = self.response.get_statements()
        self.assertEqual(1, len(statements))

        for stmt in statements:
            self.assertEqual("USD", stmt.get_currency())
            self.assertEqual("20100424", stmt.get_begin_date())
            self.assertEqual("20100723", stmt.get_end_date())
            self.assertEqual("1129.49",        stmt.get_balance())
            self.assertEqual("20100723", stmt.get_balance_date())

            account = stmt.get_account()
            self.assertEqual("987987987", account.aba_number)
            self.assertEqual("58152460", account.acct_number)
            self.assertEqual("CHECKING", account.get_ofx_accttype())

    def test_as_xml(self):
        # First just sanity-check that ElementTree will throw an error
        # if given a non-XML document.
        try:
            response_elem = ElementTree.fromstring(self.response_text)
            self.fail("Expected parse exception but did not get one.")
        except ExpatError:
            pass

        # Then see if we can get a real parse success, with no ExpatError.
        xml = self.response.as_xml()
        xml_elem = ElementTree.fromstring(xml)
        self.assertTrue(isinstance(xml_elem, ElementTree._ElementInterface))

        # Finally, for kicks, try to get a value out of it.
        org_iter = xml_elem.getiterator("ORG")
        for org in org_iter:
            self.assertEqual("FAKEOFX", org.text)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = ofx_test_utils
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

fixtures = os.path.join(os.path.dirname(__file__) or '.', "fixtures")

def get_checking_stmt():
    return open(os.path.join(fixtures, "checking.ofx"), 'rU').read()
    
def get_savings_stmt():
    return open(os.path.join(fixtures, "savings.ofx"), 'rU').read()

def get_creditcard_stmt():
    return open(os.path.join(fixtures, "creditcard.ofx"), 'rU').read()


########NEW FILE########
__FILENAME__ = ofx_validators
# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import ofx
import unittest

class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.good_aba = ofx.RoutingNumber("314074269")
        self.bad_aba  = ofx.RoutingNumber("123456789")
    
    def test_not_a_number(self):
        nan = ofx.RoutingNumber("123abd")
        self.assertEqual(nan.is_valid(), False)
        self.assertEqual(nan.get_type(), None)
        self.assertEqual(nan.get_region(), None)
        self.assertEqual(str(nan),
                         "123abd (valid: False; type: None; region: None)")
    
    def test_valid_aba(self):
        self.assertEqual(self.good_aba.is_valid(), True)
        self.assertEqual(self.bad_aba.is_valid(), False)
    
    def test_aba_types(self):
        self.assertEqual(ofx.RoutingNumber("001234567").get_type(), 
                         "United States Government")
        self.assertEqual(ofx.RoutingNumber("011234567").get_type(), 
                         "Primary")
        self.assertEqual(ofx.RoutingNumber("071234567").get_type(), 
                         "Primary")
        self.assertEqual(ofx.RoutingNumber("121234567").get_type(), 
                         "Primary")
        self.assertEqual(ofx.RoutingNumber("131234567").get_type(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("201234567").get_type(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("211234567").get_type(), 
                         "Thrift")
        self.assertEqual(ofx.RoutingNumber("251234567").get_type(), 
                         "Thrift")
        self.assertEqual(ofx.RoutingNumber("321234567").get_type(), 
                         "Thrift")
        self.assertEqual(ofx.RoutingNumber("331234567").get_type(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("601234567").get_type(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("611234567").get_type(), 
                         "Electronic")
        self.assertEqual(ofx.RoutingNumber("641234567").get_type(), 
                         "Electronic")
        self.assertEqual(ofx.RoutingNumber("721234567").get_type(), 
                         "Electronic")
        self.assertEqual(ofx.RoutingNumber("731234567").get_type(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("791234567").get_type(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("801234567").get_type(), 
                         "Traveller's Cheque")
        self.assertEqual(ofx.RoutingNumber("811234567").get_type(), 
                         None)
    
    def test_aba_regions(self):
        self.assertEqual(ofx.RoutingNumber("001234567").get_region(), 
                         "United States Government")
        self.assertEqual(ofx.RoutingNumber("011234567").get_region(), 
                         "Boston")
        self.assertEqual(ofx.RoutingNumber("071234567").get_region(), 
                         "Chicago")
        self.assertEqual(ofx.RoutingNumber("121234567").get_region(), 
                         "San Francisco")
        self.assertEqual(ofx.RoutingNumber("131234567").get_region(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("201234567").get_region(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("211234567").get_region(), 
                         "Boston")
        self.assertEqual(ofx.RoutingNumber("251234567").get_region(), 
                         "Richmond")
        self.assertEqual(ofx.RoutingNumber("321234567").get_region(), 
                         "San Francisco")
        self.assertEqual(ofx.RoutingNumber("331234567").get_region(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("601234567").get_region(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("611234567").get_region(), 
                         "Boston")
        self.assertEqual(ofx.RoutingNumber("641234567").get_region(), 
                         "Cleveland")
        self.assertEqual(ofx.RoutingNumber("721234567").get_region(), 
                         "San Francisco")
        self.assertEqual(ofx.RoutingNumber("731234567").get_region(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("791234567").get_region(), 
                         None)
        self.assertEqual(ofx.RoutingNumber("801234567").get_region(), 
                         "Traveller's Cheque")
        self.assertEqual(ofx.RoutingNumber("811234567").get_region(), 
                         None)
    
    def test_aba_string(self):
        self.assertEqual(str(self.good_aba), 
                         "314074269 (valid: True; type: Thrift; region: Dallas)")
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_suite
#!/usr/bin/env python

# Copyright 2005-2010 Wesabe, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
#  test/suite - controller for all fixofx tests.
#

import sys
sys.path.insert(0, '../3rdparty')
sys.path.insert(0, '../lib')

import unittest

def suite():
    modules_to_test = ['ofxtools_qif_converter', 'mock_ofx_server', 
                       'ofx_account', 'ofx_builder', 'ofx_client', 
                       'ofx_document', 'ofx_error', 'ofx_parser', 
                       'ofx_request', 'ofx_response', 'ofx_validators']
    alltests = unittest.TestSuite()
    
    for module in map(__import__, modules_to_test):
        alltests.addTest(unittest.findTestCases(module))
    
    return alltests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

########NEW FILE########
