__FILENAME__ = activities
from model import YoutifyUser
from model import FollowRelation
from model import Activity
from model import get_youtify_user_struct
from model import get_playlist_struct_from_playlist_model
from model import get_external_user_subscription_struct
import json as simplejson

def create_follow_activity(owner, other_user):
    """ owner started following other_user 

    Both owner and other_user gets a new activity
    """
    target = simplejson.dumps(get_youtify_user_struct(other_user))
    actor = simplejson.dumps(get_youtify_user_struct(owner))

    m = Activity(owner=owner, verb='follow', actor=actor, target=target, type='outgoing')
    m.put()

    m = Activity(owner=other_user, verb='follow', actor=actor, target=target, type='incoming')
    m.put()

def create_subscribe_activity(youtify_user_model, playlist_model):
    """ user subscribed to playlist

    Both user and playlists owner gets a new activity
    """
    target = simplejson.dumps(get_playlist_struct_from_playlist_model(playlist_model))
    actor = simplejson.dumps(get_youtify_user_struct(youtify_user_model))

    m = Activity(owner=youtify_user_model, verb='subscribe', actor=actor, target=target, type='outgoing')
    m.put()

    m = Activity(owner=playlist_model.owner, verb='subscribe', actor=actor, target=target, type='incoming')
    m.put()

def create_signup_activity(youtify_user_model):
    target = simplejson.dumps({})
    actor = simplejson.dumps(get_youtify_user_struct(youtify_user_model))

    m = Activity(owner=youtify_user_model, verb='signup', actor=actor, target=target, type='outgoing')
    m.put()

def create_flattr_activity(youtify_user_model, thing_id, thing_title):
    target = simplejson.dumps({
        'thing_id': thing_id,
        'thing_title': thing_title,
    })
    actor = simplejson.dumps(get_youtify_user_struct(youtify_user_model))

    m = Activity(owner=youtify_user_model, verb='flattr', actor=actor, target=target, type='outgoing')
    m.put()

    for relation in FollowRelation.all().filter('user2 =', youtify_user_model.key().id()):
        m = Activity(owner=YoutifyUser.get_by_id(relation.user1), verb='flattr', actor=actor, target=target, type='incoming')
        m.put()

def create_external_subscribe_activity(youtify_user_model, external_user_model):
    target = simplejson.dumps(get_external_user_subscription_struct(external_user_model))
    actor = simplejson.dumps(get_youtify_user_struct(youtify_user_model))

    m = Activity(owner=youtify_user_model, verb='external_subscribe', actor=actor, target=target, type='outgoing')
    m.put()

    for relation in FollowRelation.all().filter('user2 =', youtify_user_model.key().id()):
        m = Activity(owner=YoutifyUser.get_by_id(relation.user1), verb='external_subscribe', actor=actor, target=target, type='incoming')
        m.put()

########NEW FILE########
__FILENAME__ = alternatives
import logging
import webapp2
from google.appengine.ext.webapp import util
from google.appengine.ext import db
import json as simplejson
from model import AlternativeTrack, get_alternative_struct

class AlternativesHandler(webapp2.RequestHandler):

    def get(self, track_type, track_id):
        """ get alternatives for a track """
        alternatives = AlternativeTrack.all().filter('replacement_for_id = ', track_id).filter('replacement_type = ', track_type)
        json = []

        for alternative in alternatives:
            json.append(get_alternative_struct(alternative))

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

    def post(self, track_type, track_id):
        """ change rating or add a new alternative track """
        replacement_for_id = self.request.get('replacement_for_id')
        replacement_track_type = self.request.get('replacement_track_type')
        vote = int(self.request.get('vote'))

        if replacement_for_id == track_id and replacement_track_type == track_type:
            self.response.out.write('replacement cannot be the same as the track')
            self.error(400)
            return

        if vote < -1 or vote > 1:
            self.response.out.write('Rating must be in range -1 to 1')
            self.error(400)
            return

        alternative = AlternativeTrack.all() \
            .filter('track_id = ', track_id) \
            .filter('track_type = ', track_type) \
            .filter('replacement_for_id = ', replacement_for_id) \
            .filter('replacement_for_type = ', replacement_track_type) \
            .get()

        if alternative is not None:
            alternative.vote += vote
            alternative.save()
        else:
            alternative = AlternativeTrack(track_id=track_id, track_type=track_type, replacement_for_id=replacement_for_id, replacement_for_type=replacement_track_type, vote=vote)
            alternative.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')


app = webapp2.WSGIApplication([
        ('/api/alternatives/(.*)/(.*)', AlternativesHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = appengine_config
ï»¿def webapp_add_wsgi_middleware(app):
    from google.appengine.ext.appstats import recording
    app = recording.appstats_wsgi_middleware(app)
    return app
########NEW FILE########
__FILENAME__ = config_template
import os

EMAIL_UNSUBSCRIBE_SALT = 'abc'

CLIENT_ID = ''
CLIENT_SECRET = ''
DROPBOX_APP_KEY = ''
DROPBOX_APP_SECRET = ''
DROPBOX_CALLBACK_URL = ''
DROPBOX_ACCESS_TYPE = 'app_folder'

ON_PRODUCTION = os.environ['SERVER_SOFTWARE'].startswith('Google App Engine') # http://stackoverflow.com/questions/1916579/in-python-how-can-i-test-if-im-in-google-app-engine-sdk

if ON_PRODUCTION:
    REDIRECT_URL = 'http://www.youtify.com/flattrback'
    LASTFM_REDIRECT_URL = 'http://www.youtify.com/lastfm/callback'
    DROPBOX_CALLBACK_URL = 'http://www.youtify.com/api/dropbox/callback'
else:
    REDIRECT_URL = 'http://localhost:8080/flattrback'
    LASTFM_REDIRECT_URL = 'http://localhost:8080/lastfm/callback'
    DROPBOX_CALLBACK_URL = 'http://localhost:8080/api/dropbox/callback'

########NEW FILE########
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
            elif i > 0 and line[0] == " ":
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
__FILENAME__ = client
"""
The main client API you'll be working with most often.  You'll need to
configure a dropbox.session.DropboxSession for this to work, but otherwise
it's fairly self-explanatory.
"""

import re
import json

from dropbox.rest import ErrorResponse
from dropbox.rest import RESTClient

def format_path(path):
    """Normalize path for use with the Dropbox API.

    This function turns multiple adjacent slashes into single
    slashes, then ensures that there's a leading slash but
    not a trailing slash.
    """
    if not path:
        return path

    path = re.sub(r'/+', '/', path)

    if path == '/':
        return ""
    else:
        return '/' + path.strip('/')

class DropboxClient(object):
    """
    The main access point of doing REST calls on Dropbox. You should
    first create and configure a dropbox.session.DropboxSession object,
    and then pass it into DropboxClient's constructor. DropboxClient
    then does all the work of properly calling each API method
    with the correct OAuth authentication.

    You should be aware that any of these methods can raise a
    rest.ErrorResponse exception if the server returns a non-200
    or invalid HTTP response. Note that a 401 return status at any
    point indicates that the user needs to be reauthenticated.
    """

    def __init__(self, session):
        """Initialize the DropboxClient object.

        Args:
            session: A dropbox.session.DropboxSession object to use for making requests.
        """
        self.session = session

    def request(self, target, params=None, method='POST', content_server=False):
        """Make an HTTP request to a target API method.

        This is an internal method used to properly craft the url, headers, and
        params for a Dropbox API request.  It is exposed for you in case you
        need craft other API calls not in this library or if you want to debug it.

        Args:
            target: The target URL with leading slash (e.g. '/files')
            params: A dictionary of parameters to add to the request
            method: An HTTP method (e.g. 'GET' or 'POST')
            content_server: A boolean indicating whether the request is to the
               API content server, for example to fetch the contents of a file
               rather than its metadata.

        Returns:
            A tuple of (url, params, headers) that should be used to make the request.
            OAuth authentication information will be added as needed within these fields.
        """
        assert method in ['GET','POST', 'PUT'], "Only 'GET', 'POST', and 'PUT' are allowed."
        if params is None:
            params = {}

        host = self.session.API_CONTENT_HOST if content_server else self.session.API_HOST
        base = self.session.build_url(host, target)
        headers, params = self.session.build_access_headers(method, base, params)

        if method in ('GET', 'PUT'):
            url = self.session.build_url(host, target, params)
        else:
            url = self.session.build_url(host, target)

        return url, params, headers


    def account_info(self):
        """Retrieve information about the user's account.

        Returns:
            A dictionary containing account information.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#account-info
        """
        url, params, headers = self.request("/account/info", method='GET')

        return RESTClient.GET(url, headers)


    def put_file(self, full_path, file_obj, overwrite=False, parent_rev=None):
        """Upload a file.

        Args:
            full_path: The full path to upload the file to, *including the file name*.
                If the destination directory does not yet exist, it will be created.
            file_obj: A file-like object to upload. If you would like, you can pass a string as file_obj.
            overwrite: Whether to overwrite an existing file at the given path. [default False]
                If overwrite is False and a file already exists there, Dropbox
                will rename the upload to make sure it doesn't overwrite anything.
                You need to check the metadata returned for the new name.
                This field should only be True if your intent is to potentially
                clobber changes to a file that you don't know about.
            parent_rev: The rev field from the 'parent' of this upload. [optional]
                If your intent is to update the file at the given path, you should
                pass the parent_rev parameter set to the rev value from the most recent
                metadata you have of the existing file at that path. If the server
                has a more recent version of the file at the specified path, it will
                automatically rename your uploaded file, spinning off a conflict.
                Using this parameter effectively causes the overwrite parameter to be ignored.
                The file will always be overwritten if you send the most-recent parent_rev,
                and it will never be overwritten if you send a less-recent one.

        Returns:
            A dictionary containing the metadata of the newly uploaded file.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#files-put

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of
               400: Bad request (may be due to many things; check e.error for details)
               503: User over quota

        Note: In Python versions below version 2.6, httplib doesn't handle file-like objects.
            In that case, this code will read the entire file into memory (!).
        """
        path = "/files_put/%s%s" % (self.session.root, format_path(full_path))

        params = {
            'overwrite': bool(overwrite),
            }

        if parent_rev is not None:
            params['parent_rev'] = parent_rev

        url, params, headers = self.request(path, params, method='PUT', content_server=True)

        return RESTClient.PUT(url, file_obj, headers)

    def get_file(self, from_path, rev=None):
        """Download a file.

        Unlike most other calls, get_file returns a raw HTTPResponse with the connection open.
        You should call .read() and perform any processing you need, then close the HTTPResponse.

        Args:
            from_path: The path to the file to be downloaded.
            rev: A previous rev value of the file to be downloaded. [optional]

        Returns:
            An httplib.HTTPResponse that is the result of the request.

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of
               400: Bad request (may be due to many things; check e.error for details)
               404: No file was found at the given path, or the file that was there was deleted.
               200: Request was okay but response was malformed in some way.
        """
        path = "/files/%s%s" % (self.session.root, format_path(from_path))

        params = {}
        if rev is not None:
            params['rev'] = rev

        url, params, headers = self.request(path, params, method='GET', content_server=True)
        return RESTClient.request("GET", url, headers=headers, raw_response=True)

    def get_file_and_metadata(self, from_path, rev=None):
        """Download a file alongwith its metadata.

        Acts as a thin wrapper around get_file() (see get_file() comments for
        more details)

        Args:
            from_path: The path to the file to be downloaded.
            rev: A previous rev value of the file to be downloaded. [optional]

        Returns:
            - An httplib.HTTPResponse that is the result of the request.
            - A dictionary containing the metadata of the file (see
              https://www.dropbox.com/developers/reference/api#metadata for details).

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of
               400: Bad request (may be due to many things; check e.error for details)
               404: No file was found at the given path, or the file that was there was deleted.
               200: Request was okay but response was malformed in some way.
        """
        file_res = self.get_file(from_path, rev)
        metadata = DropboxClient.__parse_metadata_as_dict(file_res)

        return file_res, metadata

    @staticmethod
    def __parse_metadata_as_dict(dropbox_raw_response):
        """Parses file metadata from a raw dropbox HTTP response, raising a
        dropbox.rest.ErrorResponse if parsing fails.
        """
        metadata = None
        for header, header_val in dropbox_raw_response.getheaders():
            if header.lower() == 'x-dropbox-metadata':
                try:
                    metadata = json.loads(header_val)
                except ValueError:
                    raise ErrorResponse(dropbox_raw_response)
        if not metadata: raise ErrorResponse(dropbox_raw_response)
        return metadata

    def delta(self, cursor=None):
        """A way of letting you keep up with changes to files and folders in a
        user's Dropbox.  You can periodically call delta() to get a list of "delta
        entries", which are instructions on how to update your local state to
        match the server's state.

        Arguments:
          - ``cursor``: On the first call, omit this argument (or pass in ``None``).  On
            subsequent calls, pass in the ``cursor`` string returned by the previous
            call.

        Returns: A dict with three fields.
          - ``entries``: A list of "delta entries" (described below)
          - ``reset``: If ``True``, you should your local state to be an empty folder
            before processing the list of delta entries.  This is only ``True`` only
            in rare situations.
          - ``cursor``: A string that is used to keep track of your current state.
            On the next call to delta(), pass in this value to return entries
            that were recorded since the cursor was returned.
          - ``has_more``: If ``True``, then there are more entries available; you can
            call delta() again immediately to retrieve those entries.  If ``False``,
            then wait at least 5 minutes (preferably longer) before checking again.

        Delta Entries: Each entry is a 2-item list of one of following forms:
          - [*path*, *metadata*]: Indicates that there is a file/folder at the given
            path.  You should add the entry to your local path.  (The *metadata*
            value is the same as what would be returned by the ``metadata()`` call.)
              - If the new entry includes parent folders that don't yet exist in your
                local state, create those parent folders in your local state.  You
                will eventually get entries for those parent folders.
              - If the new entry is a file, replace whatever your local state has at
                *path* with the new entry.
              - If the new entry is a folder, check what your local state has at
                *path*.  If it's a file, replace it with the new entry.  If it's a
                folder, apply the new *metadata* to the folder, but do not modify
                the folder's children.
          - [*path*, ``nil``]: Indicates that there is no file/folder at the *path* on
            Dropbox.  To update your local state to match, delete whatever is at *path*,
            including any children (you will sometimes also get "delete" delta entries
            for the children, but this is not guaranteed).  If your local state doesn't
            have anything at *path*, ignore this entry.

        Remember: Dropbox treats file names in a case-insensitive but case-preserving
        way.  To facilitate this, the *path* strings above are lower-cased versions of
        the actual path.  The *metadata* dicts have the original, case-preserved path.
        """
        path = "/delta"

        params = {}
        if cursor is not None:
            params['cursor'] = cursor

        url, params, headers = self.request(path, params)

        return RESTClient.POST(url, params, headers)


    def create_copy_ref(self, from_path):
        """Creates and returns a copy ref for a specific file.  The copy ref can be
        used to instantly copy that file to the Dropbox of another account.

        Args:
         - path: The path to the file for a copy ref to be created on.

        Returns:
            A dictionary that looks like the following example:

            ``{"expires":"Fri, 31 Jan 2042 21:01:05 +0000", "copy_ref":"z1X6ATl6aWtzOGq0c3g5Ng"}``

        """
        path = "/copy_ref/%s%s" % (self.session.root, format_path(from_path))

        url, params, headers = self.request(path, {})

        return RESTClient.GET(url, headers)

    def add_copy_ref(self, copy_ref, to_path):
        """Adds the file referenced by the copy ref to the specified path

        Args:
         - copy_ref: A copy ref string that was returned from a create_copy_ref call.
           The copy_ref can be created from any other Dropbox account, or from the same account.
         - path: The path to where the file will be created.

        Returns:
            A dictionary containing the metadata of the new copy of the file.
         """
        path = "/fileops/copy"

        params = {'from_copy_ref': copy_ref,
                  'to_path': format_path(to_path),
                  'root': self.session.root}

        url, params, headers = self.request(path, params)

        return RESTClient.POST(url, params, headers)

    def file_copy(self, from_path, to_path):
        """Copy a file or folder to a new location.

        Args:
            from_path: The path to the file or folder to be copied.

            to_path: The destination path of the file or folder to be copied.
                This parameter should include the destination filename (e.g.
                from_path: '/test.txt', to_path: '/dir/test.txt'). If there's
                already a file at the to_path, this copy will be renamed to
                be unique.

        Returns:
            A dictionary containing the metadata of the new copy of the file or folder.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#fileops-copy

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of:

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No file was found at given from_path.
            - 503: User over storage quota.
        """
        params = {'root': self.session.root,
                  'from_path': format_path(from_path),
                  'to_path': format_path(to_path),
                  }

        url, params, headers = self.request("/fileops/copy", params)

        return RESTClient.POST(url, params, headers)


    def file_create_folder(self, path):
        """Create a folder.

        Args:
            path: The path of the new folder.

        Returns:
            A dictionary containing the metadata of the newly created folder.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#fileops-create-folder

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of
               400: Bad request (may be due to many things; check e.error for details)
               403: A folder at that path already exists.
        """
        params = {'root': self.session.root, 'path': format_path(path)}

        url, params, headers = self.request("/fileops/create_folder", params)

        return RESTClient.POST(url, params, headers)


    def file_delete(self, path):
        """Delete a file or folder.

        Args:
            path: The path of the file or folder.

        Returns:
            A dictionary containing the metadata of the just deleted file.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#fileops-delete

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No file was found at the given path.
        """
        params = {'root': self.session.root, 'path': format_path(path)}

        url, params, headers = self.request("/fileops/delete", params)

        return RESTClient.POST(url, params, headers)


    def file_move(self, from_path, to_path):
        """Move a file or folder to a new location.

        Args:
            from_path: The path to the file or folder to be moved.
            to_path: The destination path of the file or folder to be moved.
            This parameter should include the destination filename (e.g.
            from_path: '/test.txt', to_path: '/dir/test.txt'). If there's
            already a file at the to_path, this file or folder will be renamed to
            be unique.

        Returns:
            A dictionary containing the metadata of the new copy of the file or folder.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#fileops-move

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No file was found at given from_path.
            - 503: User over storage quota.
        """
        params = {'root': self.session.root, 'from_path': format_path(from_path), 'to_path': format_path(to_path)}

        url, params, headers = self.request("/fileops/move", params)

        return RESTClient.POST(url, params, headers)


    def metadata(self, path, list=True, file_limit=10000, hash=None, rev=None, include_deleted=False):
        """Retrieve metadata for a file or folder.

        Args:
            path: The path to the file or folder.

            list: Whether to list all contained files (only applies when
                path refers to a folder).
            file_limit: The maximum number of file entries to return within
                a folder. If the number of files in the directory exceeds this
                limit, an exception is raised. The server will return at max
                10,000 files within a folder.
            hash: Every directory listing has a hash parameter attached that
                can then be passed back into this function later to save on\
                bandwidth. Rather than returning an unchanged folder's contents,\
                the server will instead return a 304.\
            rev: The revision of the file to retrieve the metadata for. [optional]
                This parameter only applies for files. If omitted, you'll receive
                the most recent revision metadata.

        Returns:
            A dictionary containing the metadata of the file or folder
            (and contained files if appropriate).

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#metadata

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 304: Current directory hash matches hash parameters, so contents are unchanged.
            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No file was found at given path.
            - 406: Too many file entries to return.
        """
        path = "/metadata/%s%s" % (self.session.root, format_path(path))

        params = {'file_limit': file_limit,
                  'list': 'true',
                  'include_deleted': include_deleted,
                  }

        if not list:
            params['list'] = 'false'
        if hash is not None:
            params['hash'] = hash
        if rev:
            params['rev'] = rev

        url, params, headers = self.request(path, params, method='GET')

        return RESTClient.GET(url, headers)

    def thumbnail(self, from_path, size='large', format='JPEG'):
        """Download a thumbnail for an image.

        Unlike most other calls, thumbnail returns a raw HTTPResponse with the connection open.
        You should call .read() and perform any processing you need, then close the HTTPResponse.

        Args:
            from_path: The path to the file to be thumbnailed.
            size: A string describing the desired thumbnail size.
               At this time, 'small', 'medium', and 'large' are
               officially supported sizes (32x32, 64x64, and 128x128
               respectively), though others may be available. Check
               https://www.dropbox.com/developers/reference/api#thumbnails for
               more details.

        Returns:
            An httplib.HTTPResponse that is the result of the request.

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No file was found at the given from_path, or files of that type cannot be thumbnailed.
            - 415: Image is invalid and cannot be thumbnailed.
        """
        assert format in ['JPEG', 'PNG'], "expected a thumbnail format of 'JPEG' or 'PNG', got %s" % format

        path = "/thumbnails/%s%s" % (self.session.root, format_path(from_path))

        url, params, headers = self.request(path, {'size': size, 'format': format}, method='GET', content_server=True)
        return RESTClient.request("GET", url, headers=headers, raw_response=True)

    def thumbnail_and_metadata(self, from_path, size='large', format='JPEG'):
        """Download a thumbnail for an image alongwith its metadata.

        Acts as a thin wrapper around thumbnail() (see thumbnail() comments for
        more details)

        Args:
            from_path: The path to the file to be thumbnailed.
            size: A string describing the desired thumbnail size. See thumbnail()
               for details.

        Returns:
            - An httplib.HTTPResponse that is the result of the request.
            - A dictionary containing the metadata of the file whose thumbnail
              was downloaded (see https://www.dropbox.com/developers/reference/api#metadata
              for details).

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No file was found at the given from_path, or files of that type cannot be thumbnailed.
            - 415: Image is invalid and cannot be thumbnailed.
            - 200: Request was okay but response was malformed in some way.
        """
        thumbnail_res = self.thumbnail(from_path, size, format)
        metadata = DropboxClient.__parse_metadata_as_dict(thumbnail_res)

        return thumbnail_res, metadata

    def search(self, path, query, file_limit=1000, include_deleted=False):
        """Search directory for filenames matching query.

        Args:
            path: The directory to search within.

            query: The query to search on (minimum 3 characters).

            file_limit: The maximum number of file entries to return within a folder.
               The server will return at max 1,000 files.

            include_deleted: Whether to include deleted files in search results.

        Returns:
            A list of the metadata of all matching files (up to
            file_limit entries).  For a detailed description of what
            this call returns, visit:
            https://www.dropbox.com/developers/reference/api#search

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of
            400: Bad request (may be due to many things; check e.error
            for details)
        """
        path = "/search/%s%s" % (self.session.root, format_path(path))

        params = {
            'query': query,
            'file_limit': file_limit,
            'include_deleted': include_deleted,
            }

        url, params, headers = self.request(path, params)

        print "--- URL: %r" % url
        print "       : %r" % params

        return RESTClient.POST(url, params, headers)

    def revisions(self, path, rev_limit=1000):
        """Retrieve revisions of a file.

        Args:
            path: The file to fetch revisions for. Note that revisions
                are not available for folders.
            rev_limit: The maximum number of file entries to return within
                a folder. The server will return at max 1,000 revisions.

        Returns:
            A list of the metadata of all matching files (up to rev_limit entries).

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#revisions

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: No revisions were found at the given path.
        """
        path = "/revisions/%s%s" % (self.session.root, format_path(path))

        params = {
            'rev_limit': rev_limit,
            }

        url, params, headers = self.request(path, params, method='GET')

        return RESTClient.GET(url, headers)

    def restore(self, path, rev):
        """Restore a file to a previous revision.

        Args:
            path: The file to restore. Note that folders can't be restored.
            rev: A previous rev value of the file to be restored to.

        Returns:
            A dictionary containing the metadata of the newly restored file.

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#restore

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: Unable to find the file at the given revision.
        """
        path = "/restore/%s%s" % (self.session.root, format_path(path))

        params = {
            'rev': rev,
            }

        url, params, headers = self.request(path, params)

        return RESTClient.POST(url, params, headers)

    def media(self, path):
        """Get a temporary unauthenticated URL for a media file.

        All of Dropbox's API methods require OAuth, which may cause problems in
        situations where an application expects to be able to hit a URL multiple times
        (for example, a media player seeking around a video file). This method
        creates a time-limited URL that can be accessed without any authentication,
        and returns that to you, along with an expiration time.

        Args:
            path: The file to return a URL for. Folders are not supported.

        Returns:
            A dictionary that looks like the following example:

            ``{'url': 'https://dl.dropbox.com/0/view/wvxv1fw6on24qw7/file.mov', 'expires': 'Thu, 16 Sep 2011 01:01:25 +0000'}``

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#media

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: Unable to find the file at the given path.
        """
        path = "/media/%s%s" % (self.session.root, format_path(path))

        url, params, headers = self.request(path, method='GET')

        return RESTClient.GET(url, headers)

    def share(self, path):
        """Create a shareable link to a file or folder.

        Shareable links created on Dropbox are time-limited, but don't require any
        authentication, so they can be given out freely. The time limit should allow
        at least a day of shareability, though users have the ability to disable
        a link from their account if they like.

        Args:
            path: The file or folder to share.

        Returns:
            A dictionary that looks like the following example:

            ``{'url': 'http://www.dropbox.com/s/m/a2mbDa2', 'expires': 'Thu, 16 Sep 2011 01:01:25 +0000'}``

            For a detailed description of what this call returns, visit:
            https://www.dropbox.com/developers/reference/api#shares

        Raises:
            A dropbox.rest.ErrorResponse with an HTTP status of

            - 400: Bad request (may be due to many things; check e.error for details)
            - 404: Unable to find the file at the given path.
        """
        path = "/shares/%s%s" % (self.session.root, format_path(path))

        url, params, headers = self.request(path, method='GET')

        return RESTClient.GET(url, headers)

########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = rest
"""
A simple JSON REST request abstraction layer that is used by the
dropbox.client and dropbox.session modules. You shouldn't need to use this.
"""

import httplib
import os
#import pkg_resources
import re
import json
import socket
#import ssl
import urllib
import urlparse

SDK_VERSION = "1.4"

class RESTClient(object):
    """
    An class with all static methods to perform JSON REST requests that is used internally
    by the Dropbox Client API. It provides just enough gear to make requests
    and get responses as JSON data (when applicable). All requests happen over SSL.
    """

    @staticmethod
    def request(method, url, post_params=None, body=None, headers=None, raw_response=False):
        """Perform a REST request and parse the response.

        Args:
            method: An HTTP method (e.g. 'GET' or 'POST').
            url: The URL to make a request to.
            post_params: A dictionary of parameters to put in the body of the request.
                This option may not be used if the body parameter is given.
            body: The body of the request. Typically, this value will be a string.
                It may also be a file-like object in Python 2.6 and above. The body
                parameter may not be used with the post_params parameter.
            headers: A dictionary of headers to send with the request.
            raw_response: Whether to return the raw httplib.HTTPReponse object. [default False]
                It's best enabled for requests that return large amounts of data that you
                would want to .read() incrementally rather than loading into memory. Also
                use this for calls where you need to read metadata like status or headers,
                or if the body is not JSON.

        Returns:
            The JSON-decoded data from the server, unless raw_response is
            specified, in which case an httplib.HTTPReponse object is returned instead.

        Raises:
            dropbox.rest.ErrorResponse: The returned HTTP status is not 200, or the body was
                not parsed from JSON successfully.
            dropbox.rest.RESTSocketError: A socket.error was raised while contacting Dropbox.
        """
        post_params = post_params or {}
        headers = headers or {}
        headers['User-Agent'] = 'OfficialDropboxPythonSDK/' + SDK_VERSION

        if post_params:
            if body:
                raise ValueError("body parameter cannot be used with post_params parameter")
            body = urllib.urlencode(post_params)
            headers["Content-type"] = "application/x-www-form-urlencoded"

        host = urlparse.urlparse(url).hostname
        conn = ProperHTTPSConnection(host, 443)

        try:

            # This code is here because httplib in pre-2.6 Pythons
            # doesn't handle file-like objects as HTTP bodies and
            # thus requires manual buffering
            if not hasattr(body, 'read'):
                conn.request(method, url, body, headers)
            else:

                #We need to get the size of what we're about to send for the Content-Length
                #Must support len() or have a len or fileno(), otherwise we go back to what we were doing!
                clen = None

                try:
                    clen = len(body)
                except (TypeError, AttributeError):
                    try:
                        clen = body.len
                    except AttributeError:
                        try:
                            clen = os.fstat(body.fileno()).st_size
                        except AttributeError:
                            # fine, lets do this the hard way
                            # load the whole file at once using readlines if we can, otherwise
                            # just turn it into a string
                            if hasattr(body, 'readlines'):
                                body = body.readlines()
                            conn.request(method, url, str(body), headers)

                if clen != None:  #clen == 0 is perfectly valid. Must explicitly check for None
                    clen = str(clen)
                    headers["Content-Length"] = clen
                    conn.request(method, url, "", headers)
                    BLOCKSIZE = 4096 #4MB buffering just because

                    data=body.read(BLOCKSIZE)
                    while data:
                        conn.send(data)
                        data=body.read(BLOCKSIZE)

        except socket.error, e:
            raise RESTSocketError(host, e)
        except CertificateError, e:
            raise RESTSocketError(host, "SSL certificate error: " + e)

        r = conn.getresponse()
        if r.status != 200:
            raise ErrorResponse(r)

        if raw_response:
            return r
        else:
            try:
                resp = json.loads(r.read())
            except ValueError:
                raise ErrorResponse(r)
            finally:
                conn.close()

        return resp

    @classmethod
    def GET(cls, url, headers=None, raw_response=False):
        """Perform a GET request using RESTClient.request"""
        assert type(raw_response) == bool
        return cls.request("GET", url, headers=headers, raw_response=raw_response)

    @classmethod
    def POST(cls, url, params=None, headers=None, raw_response=False):
        """Perform a POST request using RESTClient.request"""
        assert type(raw_response) == bool
        if params is None:
            params = {}

        return cls.request("POST", url, post_params=params, headers=headers, raw_response=raw_response)

    @classmethod
    def PUT(cls, url, body, headers=None, raw_response=False):
        """Perform a PUT request using RESTClient.request"""
        assert type(raw_response) == bool
        return cls.request("PUT", url, body=body, headers=headers, raw_response=raw_response)

class RESTSocketError(socket.error):
    """
    A light wrapper for socket.errors raised by dropbox.rest.RESTClient.request
    that adds more information to the socket.error.
    """

    def __init__(self, host, e):
        msg = "Error connecting to \"%s\": %s" % (host, str(e))
        socket.error.__init__(self, msg)

class ErrorResponse(Exception):
    """
    Raised by dropbox.rest.RESTClient.request for requests that:
    - Return a non-200 HTTP response, or
    - Have a non-JSON response body, or
    - Have a malformed/missing header in the response.

    Most errors that Dropbox returns will have a error field that is unpacked and
    placed on the ErrorResponse exception. In some situations, a user_error field
    will also come back. Messages under user_error are worth showing to an end-user
    of your app, while other errors are likely only useful for you as the developer.
    """

    def __init__(self, http_resp):
        self.status = http_resp.status
        self.reason = http_resp.reason
        self.body = http_resp.read()
        self.headers = http_resp.getheaders()

        try:
            body = json.loads(self.body)
            self.error_msg = body.get('error')
            self.user_error_msg = body.get('user_error')
        except ValueError:
            self.error_msg = None
            self.user_error_msg = None

    def __str__(self):
        if self.user_error_msg and self.user_error_msg != self.error_msg:
            # one is translated and the other is English
            msg = "%s (%s)" % (self.user_error_msg, self.error_msg)
        elif self.error_msg:
            msg = self.error_msg
        elif not self.body:
            msg = self.reason
        else:
            msg = "Error parsing response body or headers: " +\
                  "Body - %s Headers - %s" % (self.body, self.headers)

        return "[%d] %s" % (self.status, repr(msg))

TRUSTED_CERT_FILE = 'trusted-certs.crt' # pkg_resources.resource_filename(__name__, 'trusted-certs.crt')

class ProperHTTPSConnection(httplib.HTTPConnection):
    """
    httplib.HTTPSConnection is broken because it doesn't do server certificate
    validation.  This class does certificate validation by ensuring:
       1. The certificate sent down by the server has a signature chain to one of
          the certs in our 'trusted-certs.crt' (this is mostly handled by the 'ssl'
          module).
       2. The hostname in the certificate matches the hostname we're connecting to.
    """

    def __init__(self, host, port):
        httplib.HTTPConnection.__init__(self, host, port)
        self.ca_certs = TRUSTED_CERT_FILE
        self.cert_reqs = 2 # ssl.CERT_REQUIRED

    def connect(self):
        sock = create_connection((self.host, self.port))
        self.sock = ssl.wrap_socket(sock, cert_reqs=self.cert_reqs, ca_certs=self.ca_certs)
        cert = self.sock.getpeercert()
        hostname = self.host.split(':', 0)[0]
        match_hostname(cert, hostname)

class CertificateError(ValueError):
    pass

def _dnsname_to_pat(dn):
    pats = []
    for frag in dn.split(r'.'):
        if frag == '*':
            # When '*' is a fragment by itself, it matches a non-empty dotless
            # fragment.
            pats.append('[^.]+')
        else:
            # Otherwise, '*' matches any dotless fragment.
            frag = re.escape(frag)
            pats.append(frag.replace(r'\*', '[^.]*'))
    return re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)

def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 rules
    are mostly followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """
    if not cert:
        raise ValueError("empty or no certificate")
    dnsnames = []
    san = cert.get('subjectAltName', ())
    for key, value in san:
        if key == 'DNS':
            if _dnsname_to_pat(value).match(hostname):
                return
            dnsnames.append(value)
    if not san:
        # The subject is only checked when subjectAltName is empty
        for sub in cert.get('subject', ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == 'commonName':
                    if _dnsname_to_pat(value).match(hostname):
                        return
                    dnsnames.append(value)
    if len(dnsnames) > 1:
        raise CertificateError("hostname %r doesn't match either of %s" % (hostname, ', '.join(map(repr, dnsnames))))
    elif len(dnsnames) == 1:
        raise CertificateError("hostname %r doesn't match %r" % (hostname, dnsnames[0]))
    else:
        raise CertificateError("no appropriate commonName or subjectAltName fields were found")

def create_connection(address):
    host, port = address
    err = None
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            sock.connect(sa)
            return sock

        except socket.error, _:
            err = _
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    else:
        raise socket.error("getaddrinfo returns an empty list")

########NEW FILE########
__FILENAME__ = session
"""
dropbox.session.DropboxSession is responsible for holding OAuth authentication info
(app key/secret, request key/secret,  access key/secret) as well as configuration information for your app
('app_folder' or 'dropbox' access type, optional locale preference). It knows how to
use all of this information to craft properly constructed requests to Dropbox.

A DropboxSession object must be passed to a dropbox.client.DropboxClient object upon
initialization.
"""

import urllib
# import oauth.oauth as oauth
import oauth

from dropbox import rest

class DropboxSession(object):
    API_VERSION = 1

    API_HOST = "api.dropbox.com"
    WEB_HOST = "www.dropbox.com"
    API_CONTENT_HOST = "api-content.dropbox.com"

    def __init__(self, consumer_key, consumer_secret, access_type, locale=None):
        """Initialize a DropboxSession object.

        Your consumer key and secret are available
        at https://www.dropbox.com/developers/apps

        Args:
            access_type: Either 'dropbox' or 'app_folder'. All path-based operations
                will occur relative to either the user's Dropbox root directory
                or your application's app folder.
            locale: A locale string ('en', 'pt_PT', etc.) [optional]
                The locale setting will be used to translate any user-facing error
                messages that the server generates. At this time Dropbox supports
                'en', 'es', 'fr', 'de', and 'ja', though we will be supporting more
                languages in the future. If you send a language the server doesn't
                support, messages will remain in English. Look for these translated
                messages in rest.ErrorResponse exceptions as e.user_error_msg.
        """
        assert access_type in ['dropbox', 'app_folder'], "expected access_type of 'dropbox' or 'app_folder'"
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self.token = None
        self.request_token = None
        self.signature_method = oauth.OAuthSignatureMethod_PLAINTEXT()
        self.root = 'sandbox' if access_type == 'app_folder' else 'dropbox'
        self.locale = locale

    def is_linked(self):
        """Return whether the DropboxSession has an access token attached."""
        return bool(self.token)

    def unlink(self):
        """Remove any attached access token from the DropboxSession."""
        self.token = None

    def set_token(self, access_token, access_token_secret):
        """Attach an access token to the DropboxSession.

        Note that the access 'token' is made up of both a token string
        and a secret string.
        """
        self.token = oauth.OAuthToken(access_token, access_token_secret)

    def set_request_token(self, request_token, request_token_secret):
        """Attach an request token to the DropboxSession.

        Note that the reuest 'token' is made up of both a token string
        and a secret string.
        """
        self.token = oauth.OAuthToken(request_token, request_token_secret)

    def build_path(self, target, params=None):
        """Build the path component for an API URL.

        This method urlencodes the parameters, adds them
        to the end of the target url, and puts a marker for the API
        version in front.

        Args:
            target: A target url (e.g. '/files') to build upon.
            params: A dictionary of parameters (name to value). [optional]

        Returns:
            The path and parameters components of an API URL.
        """
        if type(target) == unicode:
            target = target.encode("utf8")

        target_path = urllib.quote(target)
        params = params or {}
        params = params.copy()

        if self.locale:
            params['locale'] = self.locale

        if params:
            return "/%d%s?%s" % (self.API_VERSION, target_path, urllib.urlencode(params))
        else:
            return "/%d%s" % (self.API_VERSION, target_path)

    def build_url(self, host, target, params=None):
        """Build an API URL.

        This method adds scheme and hostname to the path
        returned from build_path.

        Args:
            target: A target url (e.g. '/files') to build upon.
            params: A dictionary of parameters (name to value). [optional]

        Returns:
            The full API URL.
        """
        return "https://%s%s" % (host, self.build_path(target, params))

    def build_authorize_url(self, request_token, oauth_callback=None):
        """Build a request token authorization URL.

        After obtaining a request token, you'll need to send the user to
        the URL returned from this function so that they can confirm that
        they want to connect their account to your app.

        Args:
            request_token: A request token from obtain_request_token.
            oauth_callback: A url to redirect back to with the authorized
                request token.

        Returns:
            An authorization for the given request token.
        """
        params = {'oauth_token': request_token.key,
                  }

        if oauth_callback:
            params['oauth_callback'] = oauth_callback

        return self.build_url(self.WEB_HOST, '/oauth/authorize', params)

    def obtain_request_token(self):
        """Obtain a request token from the Dropbox API.

        This is your first step in the OAuth process.  You call this to get a
        request_token from the Dropbox server that you can then use with
        DropboxSession.build_authorize_url() to get the user to authorize it.
        After it's authorized you use this token with
        DropboxSession.obtain_access_token() to get an access token.

        NOTE:  You should only need to do this once for each user, and then you
        can store the access token for that user for later operations.

        Returns:
            An oauth.OAuthToken representing the request token Dropbox assigned
            to this app. Also attaches the request token as self.request_token.
        """
        self.token = None # clear any token currently on the request
        url = self.build_url(self.API_HOST, '/oauth/request_token')
        headers, params = self.build_access_headers('POST', url)

        response = rest.RESTClient.POST(url, headers=headers, params=params, raw_response=True)
        self.request_token = oauth.OAuthToken.from_string(response.read())
        return self.request_token

    def obtain_access_token(self, request_token=None):
        """Obtain an access token for a user.

        After you get a request token, and then send the user to the authorize
        URL, you can use the authorized request token with this method to get the
        access token to use for future operations. The access token is stored on
        the session object.

        Args:
            request_token: A request token from obtain_request_token. [optional]
                The request_token should have been authorized via the
                authorization url from build_authorize_url. If you don't pass
                a request_token, the fallback is self.request_token, which
                will exist if you previously called obtain_request_token on this
                DropboxSession instance.

        Returns:
            An oauth.OAuthToken representing the access token Dropbox assigned
            to this app and user. Also attaches the access token as self.token.
        """
        request_token = request_token or self.request_token
        assert request_token, "No request_token available on the session. Please pass one."
        url = self.build_url(self.API_HOST, '/oauth/access_token')
        headers, params = self.build_access_headers('POST', url, request_token=request_token)

        response = rest.RESTClient.POST(url, headers=headers, params=params, raw_response=True)
        self.token = oauth.OAuthToken.from_string(response.read())
        return self.token

    def build_access_headers(self, method, resource_url, params=None, request_token=None):
        """Build OAuth access headers for a future request.

        Args:
            method: The HTTP method being used (e.g. 'GET' or 'POST').
            resource_url: The full url the request will be made to.
            params: A dictionary of parameters to add to what's already on the url.
                Typically, this would consist of POST parameters.

        Returns:
            A tuple of (header_dict, params) where header_dict is a dictionary
            of header names and values appropriate for passing into dropbox.rest.RESTClient
            and params is a dictionary like the one that was passed in, but augmented with
            oauth-related parameters as appropriate.
        """
        if params is None:
            params = {}
        else:
            params = params.copy()

        oauth_params = {
            'oauth_consumer_key': self.consumer.key,
            'oauth_timestamp': oauth.generate_timestamp(),
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_version': oauth.OAuthRequest.version,
        }

        token = request_token if request_token else self.token

        if token:
            oauth_params['oauth_token'] = token.key

        params.update(oauth_params)

        oauth_request = oauth.OAuthRequest.from_request(method, resource_url, parameters=params)
        oauth_request.sign_request(self.signature_method, self.consumer, token)

        return oauth_request.to_header(), params

########NEW FILE########
__FILENAME__ = dropbox-handler
import logging
import webapp2
from google.appengine.ext.webapp import util
from google.appengine.ext import db
import json as simplejson
from urllib import unquote
from model import YoutifyUser
from model import get_current_youtify_user_model
from dropbox.oauth import OAuthToken
try:
    import config
except ImportError:
    import config_template as config

import dropbox

class DropboxConnectHandler(webapp2.RequestHandler):

    def get(self):
        """Callback for connecting to a dropbox account"""
        sess = dropbox.session.DropboxSession(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET, config.DROPBOX_ACCESS_TYPE)
        request_token = sess.obtain_request_token()
        url = sess.build_authorize_url(request_token, config.DROPBOX_CALLBACK_URL)

        user = get_current_youtify_user_model()
        if user:
            user.dropbox_access_token = request_token.to_string()
            user.save()
            self.redirect(url)
        else:
            self.error(403)
            self.response.out.write('User not logged in')

class DropboxDisconnectHandler(webapp2.RequestHandler):

    def get(self):
        """Delete a dropbox connection"""
        user = get_current_youtify_user_model()
        if user:
            user.dropbox_access_token = None
            user.dropbox_user_name = None
            user.save()
        else:
            self.error(403)
            self.response.out.write('User not logged in')
            return

        self.redirect('/')

class DropboxCallbackHandler(webapp2.RequestHandler):

    def get(self):
        # Maybe the user pressed cancel
        if self.request.path.lower().find('not_approved=true') > 0:
            self.redirect('/')
            return

        session = dropbox.session.DropboxSession(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET, config.DROPBOX_ACCESS_TYPE)
        user = get_current_youtify_user_model()
        if user:
            # get access token
            request_token = OAuthToken.from_string(user.dropbox_access_token)
            session.request_token = request_token
            access_token = session.obtain_access_token(request_token)
            user.dropbox_access_token = access_token.to_string()

            # get user name
            session.token = access_token
            client = dropbox.client.DropboxClient(session)
            info = client.account_info()
            user.dropbox_user_name = info['display_name']
            user.save()
            self.redirect('/')
        else:
            self.error(403)
            self.response.out.write('User not logged in')

class DropboxListingHandler(webapp2.RequestHandler):

    def get(self, path):
        """List content in path"""
        filetypes = ['.mp3', '.mp4', '.ogg', '.wav']
        user = get_current_youtify_user_model()
        if user is None:
            self.error(403)
            self.response.out.write('User not logged in')
            return
        access_token = OAuthToken.from_string(user.dropbox_access_token)
        session = dropbox.session.DropboxSession(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET, config.DROPBOX_ACCESS_TYPE)
        session.token = access_token
        client = dropbox.client.DropboxClient(session)

        path = '/' + path
        dirs = []
        mediafiles = []

        try:
            metadata = client.metadata(path)
            if 'contents' in metadata:
                for item in metadata['contents']:
                    if item['is_dir']:
                        dirs.append(item['path'])
                    else:
                        for filetype in filetypes:
                            if item['path'].lower().endswith(filetype):
                                # all currently supported filetypes are 4 chars long
                                title = ' - '.join(item['path'].split('/'))[3:-4]
                                track = { 'videoId': item['path'], 'title': title, 'type': 'dropbox' }
                                mediafiles.append(track)
                                break
        except:
            pass
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps({'dirs': dirs, 'media': mediafiles}))

class DropboxStreamHandler(webapp2.RequestHandler):

    def get(self):
        """Get the dropbox stream path, which is valid for 4 hours"""
        path = self.request.path
        path_separator = '/api/dropbox/stream/'
        path = path[path.find(path_separator) + len(path_separator):]
        filetypes = ['.mp3', '.mp4', '.ogg', '.wav']
        user = get_current_youtify_user_model()
        if user is None:
            self.error(403)
            self.response.out.write('User not logged in')
            return
        if user.dropbox_access_token is None:
            self.error(401)
            self.response.out.write('User has not connected to dropbox.')
            return
        access_token = OAuthToken.from_string(user.dropbox_access_token)
        session = dropbox.session.DropboxSession(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET, config.DROPBOX_ACCESS_TYPE)
        session.token = access_token
        client = dropbox.client.DropboxClient(session)
        stream = client.media(unquote(path))
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(stream))

app = webapp2.WSGIApplication([
        ('/api/dropbox/connect', DropboxConnectHandler),
        ('/api/dropbox/disconnect', DropboxDisconnectHandler),
        ('/api/dropbox/callback', DropboxCallbackHandler),
        ('/api/dropbox/list/(.*)', DropboxListingHandler),
        ('/api/dropbox/stream/.*', DropboxStreamHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = external_users
import logging
import webapp2
from datetime import datetime
from dateutil import parser
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import urlfetch
import json as simplejson
from activities import create_external_subscribe_activity
from model import get_current_youtify_user_model
from model import get_youtify_user_struct
from model import ExternalUser
from model import ExternalUserTimestamp
from model import get_external_user_subscription_struct

class TopExternalUsers(webapp2.RequestHandler):

    def get(self, max):
        """Gets a list of external users"""
        page = int(self.request.get('page', '0'))
        page_size = int(max)

        json = memcache.get('TopExternalUsers-' + str(page_size) + '*' + str(page))

        if json is None:
            users = ExternalUser.all().order('-nr_of_subscribers').fetch(page_size, page_size * page)
            json = []
            for user in users:
                json.append(get_external_user_subscription_struct(user))
            json = simplejson.dumps(json)
            memcache.set('TopExternalUsers-' + str(page_size) + '*' + str(page), json, 60*5)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json)

class SubscribersHandler(webapp2.RequestHandler):

    def get(self, type, external_user_id):
        """Gets the subscribers of an external user"""
        external_user_model = ExternalUser.all().filter('type =', type).filter('external_user_id =', external_user_id).get()
        json = []

        if external_user_model is not None:
            for key in external_user_model.subscribers:
                youtify_user_model = db.get(key)
                json.append(get_youtify_user_struct(youtify_user_model))

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

    def post(self, type, external_user_id):
        """Subscribes to an external user"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        external_user_model = ExternalUser.all().filter('type =', type).filter('external_user_id =', external_user_id).get()
        if external_user_model is None:
            external_user_model = ExternalUser(type=type, external_user_id=external_user_id)

            # @XXX should not trust client with this information, fetch from server instead
            external_user_model.username = self.request.get('username')
            external_user_model.avatar_url = self.request.get('avatar_url')
            external_user_model.get_last_updated = True

            external_user_model.save()

        if external_user_model.key() in youtify_user_model.external_user_subscriptions:
            self.error(400)
            self.response.out.write('You already subscribe to this external user')
            return

        youtify_user_model.external_user_subscriptions.append(external_user_model.key())
        youtify_user_model.save()

        external_user_model.subscribers.append(youtify_user_model.key())
        external_user_model.nr_of_subscribers = len(external_user_model.subscribers)
        external_user_model.get_last_updated = True
        external_user_model.save()

        create_external_subscribe_activity(youtify_user_model, external_user_model)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

    def delete(self, type, external_user_id):
        """Unsubscribes from an external user"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        external_user_model = ExternalUser.all().filter('type =', type).filter('external_user_id =', external_user_id).get()

        youtify_user_model.external_user_subscriptions.remove(external_user_model.key())
        youtify_user_model.save()

        external_user_model.subscribers.remove(youtify_user_model.key())
        external_user_model.nr_of_subscribers = len(external_user_model.subscribers)

        if external_user_model.nr_of_subscribers > 0:
            external_user_model.get_last_updated = True
        else:
            external_user_model.get_last_updated = False
        external_user_model.save()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

class MarkAsViewedHandler(webapp2.RequestHandler):

    def post(self, type, external_user_id):
        """Marks the external user as viewed"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.response.out.write('user not logged in')
            logging.info('user not logged in')
            self.error(403)
            return

        external_user_model = ExternalUser.all().filter('type =', type).filter('external_user_id =', external_user_id).get()
        if external_user_model == None:
            logging.info('external user ' + external_user_id + ' not found')
            self.response.out.write('external user ' + external_user_id + ' not found')
            self.error(404)
            return
        external_user_timestamp = ExternalUserTimestamp.all().filter('external_user =', external_user_model).filter('user =', youtify_user_model).get()

        if external_user_timestamp == None:
            external_user_timestamp = ExternalUserTimestamp(external_user = external_user_model.key(), user = youtify_user_model.key())

        external_user_timestamp.last_viewed = datetime.now()
        external_user_timestamp.save()

        self.response.out.write('ok')

class ExternalUserCronHandler(webapp2.RequestHandler):
    """ Update last_updated on ExternalUsers """

    def get(self):
        external_users = ExternalUser.all().filter('get_last_updated =', True).order('last_checked').order('-nr_of_subscribers').fetch(50)
        for external_user in external_users:
            external_user.last_checked = datetime.now()
            external_user.save()

            if external_user.type == 'soundcloud':
                try:
                    last_date = datetime.fromtimestamp(0)
                    url = 'http://api.soundcloud.com/users/' + external_user.external_user_id + '/tracks.json?consumer_key=206f38d9623048d6de0ef3a89fea1c4d'
                    response = urlfetch.fetch(url=url, method=urlfetch.GET)
                    if response.status_code == 200:
                        tracks = simplejson.loads(response.content)
                        for track in tracks:
                            date_temp = datetime.fromtimestamp(0)
                            if 'created_at' in track:
                                date_temp = parser.parse(track['created_at'])
                            if date_temp.time() > last_date.time():
                                last_date = date_temp
                        if last_date.time() > datetime.fromtimestamp(0).time() and last_date.time() != external_user.last_updated.time():
                            external_user.last_updated = last_date
                            external_user.save()
                except:
                    pass

            if external_user.type == 'youtube':
                try:
                    url = 'https://gdata.youtube.com/feeds/api/users/' + external_user.external_user_id + '/uploads?alt=json&v=2'
                    response = urlfetch.fetch(url=url, method=urlfetch.GET)
                    logging.info(response.status_code)
                    if response.status_code == 200:
                        tracks = simplejson.loads(response.content)
                        updated = tracks['feed']['published']['$t']
                        last_date = parser.parse(updated)
                        if last_date.time() != external_user.last_updated.time():
                            external_user.last_updated = last_date
                            external_user.save()
                except:
                    pass

app = webapp2.WSGIApplication([
        ('/api/external_users/(.*)/(.*)/subscribers', SubscribersHandler),
        ('/api/external_users/top/(.*)', TopExternalUsers),
        ('/api/external_users/(.*)/(.*)/markasviewed', MarkAsViewedHandler),
        ('/cron/update_external_users', ExternalUserCronHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = favorites
import logging
import webapp2
from google.appengine.ext.webapp import util
import json as simplejson
from model import get_current_youtify_user_model
from model import get_display_name_for_youtify_user_model
from model import get_playlist_struct_from_playlist_model
from model import get_playlist_structs_by_id
from model import Playlist

class FavoriteHandler(webapp2.RequestHandler):

    def post(self):
        """Add a track to the favorite list"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        playlist_id = self.request.path.split('/')[-1]
        playlist_model = Playlist.get_by_id(int(playlist_id))
        json = self.request.get('json', None)
        device = self.request.get('device')

        if json is None:
            self.error(400)
            return

        if playlist_model.owner.key() == youtify_user_model.key():
            if youtify_user_model.device != device:
                self.error(409)
                self.response.out.write('wrong_device')
                return
            else:
                old_playlist = simplejson.loads(json)
                playlist_model.private = old_playlist.get('isPrivate', False)
                playlist_model.tracks_json = simplejson.dumps(old_playlist['videos'])
                playlist_model.owner = youtify_user_model
                playlist_model.title = old_playlist['title']
                playlist_model.remote_id = old_playlist['remoteId']
                playlist_model.json = None
                playlist_model.save()

                self.response.out.write(str(playlist_model.key().id()))
        else:
            self.error(403)

    def delete(self):
        """Remove a track from favorites"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        playlist_id = self.request.path.split('/')[-1]
        playlist_model = Playlist.get_by_id(int(playlist_id))

        if playlist_model.owner.key() == youtify_user_model.key():
            youtify_user_model.playlists.remove(playlist_model.key())
            youtify_user_model.save()

            playlist_model.delete()
        else:
            self.error(403)

app = webapp2.WSGIApplication([
        ('/api/favorites/.*', FavoriteHandler)
    ], debug=False)

########NEW FILE########
__FILENAME__ = flattr
import logging
import urllib
import base64
from google.appengine.api import urlfetch
import webapp2
from google.appengine.ext.webapp import util
import json as simplejson
from model import get_current_youtify_user_model
from activities import create_flattr_activity
try:
    import config
except ImportError:
    import config_template as config

VALIDATE_CERTIFICATE = True
FLATTR_SCOPE = 'flattr thing'

class ClickHandler(webapp2.RequestHandler):
    """Flattrs a specified thing"""
    def post(self):
        thing_id = self.request.get('thing_id')
        video_title = self.request.get('videoTitle')
        url = 'https://api.flattr.com/rest/v2/things/' + thing_id + '/flattr'
        user = get_current_youtify_user_model()

        headers = {
            'Authorization': 'Bearer %s' % user.flattr_access_token
        }

        response = urlfetch.fetch(url=url, method=urlfetch.POST, headers=headers, validate_certificate=VALIDATE_CERTIFICATE)
        json = simplejson.loads(response.content)

        if json.get('message') == 'ok' and 'thing' in json:
            thing_id = str(json['thing'].get('id'))
            create_flattr_activity(user, thing_id, video_title)
            user.nr_of_flattrs += 1
            user.save()
        else:
            logging.error('Error creating flattr click. Response: %s' % response.content)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(response.content)

class AutoSubmitHandler(webapp2.RequestHandler):
    """Flattrs a specified URL even though it may not be on flattr yet"""
    def post(self):
        url_to_submit = self.request.get('url')
        video_title = self.request.get('videoTitle')
        url = 'https://api.flattr.com/rest/v2/flattr'
        user = get_current_youtify_user_model()

        headers = {
            'Authorization': 'Bearer %s' % user.flattr_access_token,
            'Content-Type': 'application/json',
        }

        data = simplejson.dumps({
            'url': url_to_submit,
        })

        response = urlfetch.fetch(url=url, payload=data, method=urlfetch.POST, headers=headers, validate_certificate=VALIDATE_CERTIFICATE)
        json = simplejson.loads(response.content)

        if json.get('message') == 'ok' and 'thing' in json:
            thing_id = str(json['thing'].get('id'))
            create_flattr_activity(user, thing_id, video_title)
            user.nr_of_flattrs += 1
            user.save()
        elif json.get('error') == 'flattr_once':
            pass
        else:
            logging.error('Error creating flattr click. Response: %s' % response.content)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(response.content)

class DisconnectHandler(webapp2.RequestHandler):
    """Remove the current users access token"""
    def get(self):
        redirect_uri = self.request.get('redirect_uri', '/')
        user = get_current_youtify_user_model()
        user.flattr_access_token = None
        user.flattr_user_name = None
        user.save()
        self.redirect(redirect_uri)

class ConnectHandler(webapp2.RequestHandler):
    """Initiate the OAuth dance"""
    def get(self):
        redirect_uri = self.request.get('redirect_uri')
        if redirect_uri and redirect_uri != 'deleted':
            self.response.headers['Set-Cookie'] = 'redirect_uri=' + redirect_uri
        url = 'https://flattr.com/oauth/authorize?response_type=code&client_id=%s&redirect_uri=%s&scope=%s' % (config.CLIENT_ID, urllib.quote(config.REDIRECT_URL), urllib.quote(FLATTR_SCOPE))
        self.redirect(url)

def update_fattr_user_info(user):
    """Note, this function does not save the user model"""
    url = 'https://api.flattr.com/rest/v2/user'
    headers = {
        'Authorization': 'Bearer %s' % user.flattr_access_token,
    }
    response = urlfetch.fetch(url=url, method=urlfetch.GET, headers=headers, validate_certificate=VALIDATE_CERTIFICATE)
    response = simplejson.loads(response.content)

    if 'error_description' in response:
        raise Exception('Failed to update flattr user info for user %s - %s' % (user.google_user2.email(), response['error_description']))
    else:
        user.flattr_user_name = response['username']

class BackHandler(webapp2.RequestHandler):
    """Retrieve the access token"""
    def get(self):
        code = self.request.get('code')

        url = 'https://flattr.com/oauth/token'

        headers = {
            'Authorization': 'Basic %s' % base64.b64encode(config.CLIENT_ID + ":" + config.CLIENT_SECRET),
            'Content-Type': 'application/json',
        }

        data = simplejson.dumps({
            'code': code,
            'redirect_uri': config.REDIRECT_URL,
            'grant_type': 'authorization_code',
        })

        response = urlfetch.fetch(url=url, payload=data, method=urlfetch.POST, headers=headers, validate_certificate=VALIDATE_CERTIFICATE)
        response = simplejson.loads(response.content)

        if 'access_token' in response:
            user = get_current_youtify_user_model()
            user.flattr_access_token = response['access_token']
            user.flattr_scope = FLATTR_SCOPE

            update_fattr_user_info(user)

            user.save()

            redirect_uri = self.request.cookies.get('redirect_uri')
            if redirect_uri:
                self.response.headers['Set-Cookie'] = 'redirect_uri=deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT'
                self.redirect(redirect_uri)
            else:
                self.redirect('/')
        else:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('Flattr connection failed')
            self.response.out.write('\n\n')
            self.response.out.write(str(response))

app = webapp2.WSGIApplication([
        ('/flattrdisconnect', DisconnectHandler),
        ('/flattrconnect', ConnectHandler),
        ('/flattrback', BackHandler),
        ('/flattrclick', ClickHandler),
        ('/flattrautosubmit', AutoSubmitHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = happytranslate
import webapp2
import json

_cache = {}

# This map is used to translate the user agent provided lang code
# to the format we use for our translations.
LANG_CODE_MAP = {
    'sv': 'sv_SE',
    'fi': 'fi_FI',
    'en': 'en_US',
    'de': 'de_DE',
}

def auto_detect_language(request):
    header = request.headers.get('Accept-Language', '')
    header = header.lower()

    accepted_languages = header.split(';')[0]
    accepted_languages = accepted_languages.split(',')

    for lang in accepted_languages:
        if lang in LANG_CODE_MAP:
            return LANG_CODE_MAP[lang]

        lang = lang.split('-')[0]
        if lang in LANG_CODE_MAP:
            return LANG_CODE_MAP[lang]

    return 'en_US'

def _get_translations_from_cache_or_file():
    global _cache

    if _cache:
        return _cache

    f = open('translations.json', 'r')

    _cache = json.loads(f.read())

    f.close()

    return _cache

def get_translations_for_lang(lang_code):
    data = _get_translations_from_cache_or_file()
    return data.get(lang_code, {}).get('translations', {})

def get_languages():
    ret = []
    data = _get_translations_from_cache_or_file()

    for lang_code in data.keys():
        ret.append({
            'code': lang_code,
            'label': data[lang_code]['label'],
        })

    return ret

class Handler(webapp2.RequestHandler):

    def get(self, lang_code):
        data = get_translations_for_lang(lang_code)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(data))

app = webapp2.WSGIApplication([
        ('/happytranslate/(.*)', Handler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = lastfm
import logging
import urllib
import base64

from hashlib import md5
from urllib import quote
from google.appengine.api import urlfetch
import webapp2
from google.appengine.ext.webapp import util
import json as simplejson
from model import get_current_youtify_user_model

try:
    import config
except ImportError:
    import config_template as config

VALIDATE_CERTIFICATE = True

def lastfm_request(method, t, options, user = None):
    options.update({
        'method': method,
        'api_key': 'db8b8dccb3afd186b6df786775a62cb5'
    })

    if user:
        options['sk'] = user.lastfm_access_token

    keys = options.keys()

    keys.sort()

    signature = reduce(lambda s, v: s + v, [k + options[k].encode('utf8') for k in keys]) + '75dada4b3f3794de3be2db291c20528b'

    signature = md5(signature).hexdigest()

    options = reduce(lambda s, v: '%s&%s' % (s, v), ['%s=%s' % (k, quote(options[k].encode('utf8'))) for k in keys])

    url = 'http://ws.audioscrobbler.com/2.0/?%s&format=json&api_sig=%s' % (options, signature)

    http_method = urlfetch.GET if t == 'GET' else urlfetch.POST # TODO: Fix this

    try:
        response = urlfetch.fetch(url=url, method=http_method, deadline=10, validate_certificate=VALIDATE_CERTIFICATE)
        return simplejson.loads(response.content)
    except Exception:
        return simplejson.loads({
            'message': 'urlfetch failed'
        })

class ConnectHandler(webapp2.RequestHandler):
    """Initiate the Last.fm authentication dance"""
    def get(self):
        redirect_uri = self.request.get('redirect_uri')

        if redirect_uri and redirect_uri != 'deleted':
            self.response.headers['Set-Cookie'] = 'redirect_uri=' + redirect_uri

        url = 'http://www.last.fm/api/auth/?api_key=db8b8dccb3afd186b6df786775a62cb5&cb=' + config.LASTFM_REDIRECT_URL

        self.redirect(url)

class DisconnectHandler(webapp2.RequestHandler):
    """Remove the current user's Last.fm access token"""
    def get(self):
        redirect_uri = self.request.get('redirect_uri', '/')

        user = get_current_youtify_user_model()

        user.lastfm_user_name = None
        user.lastfm_subscriber = None
        user.lastfm_access_token = None

        user.save()

        self.redirect(redirect_uri)

class CallbackHandler(webapp2.RequestHandler):
    """Retrieve the access token"""
    def get(self):
        session = lastfm_request('auth.getSession', 'GET', { 'token': self.request.get('token') })

        if 'session' in session:
            user = get_current_youtify_user_model()

            user.lastfm_user_name = session['session']['name']
            user.lastfm_access_token = session['session']['key']

            user.save()

            redirect_uri = self.request.cookies.get('redirect_uri') or '/'

            self.response.headers['Set-Cookie'] = 'redirect_uri=deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT'

            self.redirect('/')
        else:
            self.response.headers['Content-Type'] = 'text/plain'

            self.response.out.write('Last.fm connection failed')
            self.response.out.write('\n\n')

            self.response.out.write(str(session))

class ScrobbleHandler(webapp2.RequestHandler):
    """Scrobble a track"""
    def post(self):
        options = {
            'artist': self.request.get('artist'),
            'track': self.request.get('track'),
            'timestamp': self.request.get('timestamp')
        }

        session = lastfm_request('track.scrobble', 'POST', options, get_current_youtify_user_model())

        self.response.headers['Content-Type'] = 'application/json'

        if 'scrobbles' in session:
            self.response.out.write(simplejson.dumps({ 'success': True, 'result': session['scrobbles']['scrobble'] }))
        else:
            self.response.out.write(simplejson.dumps({ 'success': False }))

class RecommendationsHandler(webapp2.RequestHandler):
    """Recommended artists for the user"""
    def get(self):
        self.response.headers['Content-Type'] = 'application/json'

        try:
            session = lastfm_request('user.getRecommendedArtists', 'GET', { 'limit': '30' }, get_current_youtify_user_model())
            if 'recommendations' in session:
                self.response.out.write(simplejson.dumps({ 'success': True, 'artists': session['recommendations']['artist'] }))
            else:
                self.response.out.write(simplejson.dumps({ 'success': False }))
        except:
            self.response.out.write(simplejson.dumps({ 'success': False }))

app = webapp2.WSGIApplication([
        ('/lastfm/connect', ConnectHandler),
        ('/lastfm/disconnect', DisconnectHandler),
        ('/lastfm/callback', CallbackHandler),
        ('/lastfm/scrobble', ScrobbleHandler),
        ('/lastfm/recommendations', RecommendationsHandler)
    ], debug=False)

########NEW FILE########
__FILENAME__ = mail
from datetime import datetime
from hashlib import md5
from string import Template
from google.appengine.api import mail
import webapp2
from google.appengine.ext.webapp import util
from model import get_youtify_user_model_by_id_or_nick
from model import get_display_name_for_youtify_user_model
from model import get_url_for_youtify_user_model
try:
    from config import EMAIL_UNSUBSCRIBE_SALT
except ImportError:
    from config_template import EMAIL_UNSUBSCRIBE_SALT

# GAE developer doc: https://developers.google.com/appengine/docs/python/mail/

FOLLOW_MAIL_TEMPLATE =  """
$user1_display_name is now following you ($user2_display_name)

$user1_profile_url

Unsubscribe from further email notifications: $unsubscribe_link
"""

SUBSCRIBE_MAIL_TEMPLATE =  """
$user1_display_name subscribed to your playlist ($playlist_title)

$user1_profile_url

Unsubscribe from further email notifications: $unsubscribe_link
"""

# user1 started following user2
def send_new_follower_email(user1, user2):
    if not user2.send_new_follower_email:
        return

    if user2.last_emailed:
        delta = datetime.now() - user2.last_emailed
        if delta.seconds < 60:
            return

    user1_display_name = get_display_name_for_youtify_user_model(user1)
    user2_display_name = get_display_name_for_youtify_user_model(user2)
    user1_profile_url = get_url_for_youtify_user_model(user1)
    unsubscribe_link = 'http://www.youtify.com/unsubscribe?uid=%s&token=%s' % (user2.key().id(), md5(EMAIL_UNSUBSCRIBE_SALT + str(user2.key().id())).hexdigest())

    body = Template(FOLLOW_MAIL_TEMPLATE).substitute({
        'user1_display_name': user1_display_name,
        'user2_display_name': user2_display_name,
        'user1_profile_url': user1_profile_url,
        'unsubscribe_link': unsubscribe_link,
    })

    subject="%s is now following you on Youtify!" % user1_display_name

    mail.send_mail(sender="Youtify <noreply@youtify.com>",
                  to="%s <%s>" % (user2_display_name, user2.google_user2.email()),
                  subject=subject,
                  body=body)

    user2.last_emailed = datetime.now()
    user2.save()

# user1 subscribed to playlist
def send_new_subscriber_email(user1, playlist_model):
    user2 = playlist_model.owner

    if not user2.send_new_follower_email:
        return

    if user2.last_emailed:
        delta = datetime.now() - user2.last_emailed
        if delta.seconds < 60:
            return

    user1_display_name = get_display_name_for_youtify_user_model(user1)
    user2_display_name = get_display_name_for_youtify_user_model(user2)
    user1_profile_url = get_url_for_youtify_user_model(user1)
    unsubscribe_link = 'http://www.youtify.com/unsubscribe?uid=%s&token=%s' % (user2.key().id(), md5(EMAIL_UNSUBSCRIBE_SALT + str(user2.key().id())).hexdigest())

    body = Template(SUBSCRIBE_MAIL_TEMPLATE).substitute({
        'user1_display_name': user1_display_name,
        'user2_display_name': user2_display_name,
        'user1_profile_url': user1_profile_url,
        'playlist_title': playlist_model.title,
        'unsubscribe_link': unsubscribe_link,
    })

    subject="%s now subscribes to one of your playlists!" % user1_display_name

    mail.send_mail(sender="Youtify <noreply@youtify.com>",
                  to="%s <%s>" % (user2_display_name, user2.google_user2.email()),
                  subject=subject,
                  body=body)

    user2.last_emailed = datetime.now()
    user2.save()

class UnsubscribeHandler(webapp2.RequestHandler):

    def get(self):
        user = get_youtify_user_model_by_id_or_nick(self.request.get('uid'))
        if user is None:
            self.response.out.write('No such user found')
            return

        if md5(EMAIL_UNSUBSCRIBE_SALT + str(user.key().id())).hexdigest() == self.request.get('token'):
            user.send_new_follower_email = False
            user.send_new_subscriber_email = False
            user.save()
            self.response.out.write('You are now unsubscribed.')
        else:
            self.response.out.write('Wrong token.')

app = webapp2.WSGIApplication([
        ('/unsubscribe', UnsubscribeHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = main
import os
import re
from datetime import datetime
from google.appengine.api import users
from google.appengine.api import urlfetch
import webapp2
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
import json as simplejson
from model import get_current_youtify_user_model
from model import create_youtify_user_model
from model import get_youtify_user_struct
from model import get_followers_for_youtify_user_model
from model import get_followings_for_youtify_user_model
from model import get_settings_struct_for_youtify_user_model
from model import generate_device_token
from happytranslate import get_translations_for_lang
from happytranslate import get_languages
from happytranslate import auto_detect_language
try:
    import config
except ImportError:
    import config_template as config

class NotFoundHandler(webapp2.RequestHandler):

    def get(self):
        self.response.set_status(404)
        self.response.out.write("404 Not found")

class MainHandler(webapp2.RequestHandler):

    def get(self):

        og_title = '<meta property="og:title" content="Youtify"/>'
        og_description = '<meta property="og:description" content="The Web Music Player"/>'
        og_tag = ''
        # Find videotag and generate open graph meta tags
        match = re.compile(r'tracks/youtube/(.*)').search(self.request.url)
        if match:
            videoID = match.groups()[0]
            try:
                response = urlfetch.fetch(url='http://gdata.youtube.com/feeds/api/videos/' + videoID + '?alt=json', deadline=15)
                json = simplejson.loads(response.content)
                title = json['entry'].get('title').get('$t')
                og_title = '<meta property="og:title" content="' + title + ' | Youtify" />'
                og_description = '<meta property="og:description" content="Listen to ' + title + ' on Youtify - The Web Music Player" />'
            except:
                pass
            og_tag = '<meta property="og:video" content="http://www.youtube.com/v/' + videoID + '?version=3&amp;autohide=1"/><meta property="og:video:type" content="application/x-shockwave-flash"/><meta property="og:video:width" content="396"/><meta property="og:video:height" content="297"/>'

        # TODO add og_tag for SoundCloud & Official.fm tracks

        # Let's not be embedded to other youtify clones
        if self.request.host.find('youtify') >= 0 and self.request.host.find('youtify.com') == -1:
            self.response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        path = os.path.join(os.path.dirname(__file__), 'html', 'index.html')
        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.response.out.write(template.render(path, {
            'CURRENT_VERSION_ID': os.environ['CURRENT_VERSION_ID'],
            'USE_PRODUCTION_JAVASCRIPT': config.ON_PRODUCTION,
            'INCLUDE_GOOGLE_ANALYTICS': config.ON_PRODUCTION,
			'url': self.request.url,
            'og_title': og_title,
            'og_description': og_description,
            'og_tag': og_tag,
            'DO_FEATURE_DETECTION': True,
        }))

class ApiMainHandler(webapp2.RequestHandler):

    def get(self):
        my_followers_struct = []
        my_followings_struct = []
        settings_struct = {}
        youtify_user_struct = None

        current_user = users.get_current_user()
        youtify_user_model = get_current_youtify_user_model()

        if (current_user is not None) and (youtify_user_model is None):
            youtify_user_model = create_youtify_user_model()

        if youtify_user_model is not None:
            youtify_user_model.device = generate_device_token()
            youtify_user_model.last_login = datetime.now()
            youtify_user_struct = get_youtify_user_struct(youtify_user_model, include_private_data=True)

            # https://developers.google.com/appengine/docs/python/runtime#Request_Headers
            youtify_user_model.country = self.request.headers.get('X-AppEngine-Country', None)
            youtify_user_model.reqion = self.request.headers.get('X-AppEngine-Region', None)
            youtify_user_model.city = self.request.headers.get('X-AppEngine-City', None)
            youtify_user_model.latlon = self.request.headers.get('X-AppEngine-CityLatLong', None)

            youtify_user_model.save()

            my_followers_struct = get_followers_for_youtify_user_model(youtify_user_model)
            my_followings_struct = get_followings_for_youtify_user_model(youtify_user_model)
            settings_struct = get_settings_struct_for_youtify_user_model(youtify_user_model)

        lang_code = auto_detect_language(self.request)

        json = {
            'ON_PRODUCTION': config.ON_PRODUCTION,
            'languagesFromServer': get_languages(),
            'device': youtify_user_model is not None and youtify_user_model.device,
            'user': youtify_user_struct,
            'lastNotificationSeenTimestamp': youtify_user_model is not None and youtify_user_model.last_notification_seen_timestamp,
            'myFollowers': my_followers_struct,
            'myFollowings': my_followings_struct,
            'settingsFromServer': settings_struct,
            'autoDetectedLanguageByServer': lang_code,
            'autoDetectedTranslations': get_translations_for_lang(lang_code),
            'loginUrl': users.create_login_url('/'),
            'logoutUrl': users.create_logout_url('/'),
        }

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json));

app = webapp2.WSGIApplication([
        ('/api/main', ApiMainHandler),
        ('/.*\.(?:png|ico|jpg|gif|xml|css|swf|js|yaml|py|pyc|woff|eot|svg|ttf)$', NotFoundHandler),
        ('/.*', MainHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = build_chrome_webapp
import os.path
from shutil import copyfile
from shutil import copytree
from shutil import rmtree
try:
    from jinja2 import Template
except:
    print "Could not import Jinja2, run 'easy_install Jinja2'"
    exit()

output_dir = os.path.join('./', 'chrome_webstore')

if os.path.exists(output_dir):
    print "Removing existing build output directory"
    rmtree(output_dir)

os.makedirs(output_dir)

def render_template(src, dst, args):
    f = open(src)
    template = Template(f.read().decode('utf-8'))
    f.close()

    html = template.render(args)

    f = open(dst, 'w')
    f.write(html.encode('utf-8'))
    f.close()

def add_background_script():
    render_template('./chrome_webstore_background.js', os.path.join(output_dir, 'background.js'), {
        'API_HOST': 'http://localhost:8080',
    })

    print "Background script copied"

def copy_static_dirs():
    copytree('images', os.path.join(output_dir, 'images'))
    copytree('styles', os.path.join(output_dir, 'styles'))
    copytree('scripts', os.path.join(output_dir, 'scripts'))

    print "Static directories copied"

def add_manifest():
    copyfile('chrome_webstore_manifest.json', os.path.join(output_dir, 'manifest.json'))

    print "Manifest copied"

def render_main_template():
    render_template('./html/index.html', os.path.join(output_dir, 'index.html'), {
        'og_tag': '',
        'url': '',
        'CURRENT_VERSION_ID': '12345',
        'INCLUDE_GOOGLE_ANALYTICS': False,
        'USE_SELF_HOSTED_FONT': True,
        'DO_FEATURE_DETECTION': False,
        'USE_PRODUCTION_JAVASCRIPT': True,
    })

    print "Template rendered"

add_manifest()
add_background_script()
render_main_template()
copy_static_dirs()

print "Done, see " + os.path.abspath(output_dir)

########NEW FILE########
__FILENAME__ = me
import re
import logging
import webapp2
from google.appengine.ext.webapp import util
import json as simplejson
from model import get_current_youtify_user_model
from model import get_youtify_user_model_by_id_or_nick
from model import get_youtify_user_struct
from model import YoutifyUser
from model import FollowRelation
from model import get_activities_structs
from model import get_display_name_for_youtify_user_model
from model import get_external_user_subscriptions_struct_for_youtify_user_model
from model import get_settings_struct_for_youtify_user_model
from model import get_playlist_overview_structs
from model import generate_device_token
from activities import create_follow_activity
from mail import send_new_follower_email

BLOCKED_NICKNAMES = [
    'admin',
    'stats',
    'import',
    'export',
    'translations',
    'settings',
    'preferences',
    'yourbrowsersucks',
    'yourdecisionrocks',
    'me',
    'news',
    'feed',
    'newsfeed',
    'activities',
    'toplist',
    'recommendations',
    'queue',
    'search',
    'users',
    'playlists',
    'api',
    'about',
    'support',
    'faq',
]

class ProfileHandler(webapp2.RequestHandler):
    def get(self):
        user = get_current_youtify_user_model()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(get_youtify_user_struct(get_current_youtify_user_model())))

    def post(self):
        user = get_current_youtify_user_model()
        nickname = self.request.get('nickname', user.nickname)
        first_name = self.request.get('first_name', user.first_name)
        last_name = self.request.get('last_name', user.first_name)
        tagline = self.request.get('tagline', user.tagline)

        if nickname and not re.match('^[A-Za-z0-9_]{1,36}$', nickname):
            self.error(400)
            self.response.out.write('Nickname must be 1-36 alphanumerical characters (no whitespace)')
            return

        if nickname and nickname in BLOCKED_NICKNAMES:
            self.error(400)
            self.response.out.write('That nickname is not allowed.')
            return

        for u in YoutifyUser.all().filter('nickname_lower = ', nickname.lower()):
            if str(u.key().id()) != str(user.key().id()):
                self.error(409)
                self.response.out.write('Nickname is already taken')
                return

        user.nickname = nickname
        user.nickname_lower = nickname.lower()
        user.first_name = first_name
        user.last_name = last_name
        user.tagline = tagline

        user.save()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(get_display_name_for_youtify_user_model(user))

class SettingsHandler(webapp2.RequestHandler):

    def get(self):
        user = get_current_youtify_user_model()
        settings = get_settings_struct_for_youtify_user_model(user)
        self.response.out.write(simplejson.dumps(settings))

    def post(self):
        user = get_current_youtify_user_model()
        user.send_new_follower_email = self.request.get('send_new_follower_email') == 'true'
        user.send_new_subscriber_email = self.request.get('send_new_subscriber_email') == 'true'
        user.flattr_automatically = self.request.get('flattr_automatically') == 'true'
        user.lastfm_scrobble_automatically = self.request.get('lastfm_scrobble_automatically') == 'true'
        user.save()

        logging.info(self.request)

        settings = get_settings_struct_for_youtify_user_model(user)
        self.response.out.write(simplejson.dumps(settings))

class FollowingsHandler(webapp2.RequestHandler):

    def delete(self, uid):
        me = get_current_youtify_user_model()
        other_user = get_youtify_user_model_by_id_or_nick(uid)

        if other_user is None:
            self.error(400)
            self.response.out.write('Other user not found')
            return

        m = FollowRelation.all().filter('user1 =', me.key().id()).filter('user2 =', int(uid)).get()
        if m:
            m.delete()

        me.nr_of_followings -= 1
        other_user.nr_of_followers -= 1

        me.save()
        other_user.save()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

    def post(self, uid):
        other_user = YoutifyUser.get_by_id(int(uid))
        me = get_current_youtify_user_model()

        if other_user is None:
            self.error(400)
            self.response.out.write('Other user not found')
            return

        if me.key().id() == other_user.key().id():
            self.error(400)
            self.response.out.write('You can not follow yourself')
            return

        if FollowRelation.all().filter('user1 =', me).filter('user2 =', other_user).get():
            self.error(400)
            self.response.out.write('You already follow that user')
            return

        me.nr_of_followings += 1
        other_user.nr_of_followers += 1

        me.save()
        other_user.save()

        m = FollowRelation(user1=me.key().id(), user2=other_user.key().id())
        m.put()

        create_follow_activity(me, other_user)
        send_new_follower_email(me, other_user)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

class YouTubeUserNameHandler(webapp2.RequestHandler):
    def get(self):
        user = get_current_youtify_user_model()
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(user.youtube_username)

    def post(self):
        username = self.request.get('username')

        user = get_current_youtify_user_model()
        user.youtube_username = username
        user.save()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

class ExternalUserSubscriptionsHandler(webapp2.RequestHandler):
    def get(self):
        user = get_current_youtify_user_model()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(get_external_user_subscriptions_struct_for_youtify_user_model(user)))

class PlaylistsHandler(webapp2.RequestHandler):

    def get(self):
        """Get the users playlists, including private ones"""
        user = get_current_youtify_user_model()
        if user:
            json = get_playlist_overview_structs(user, True)
        else:
            json = []
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

class MeHandler(webapp2.RequestHandler):

    def get(self):
        """Get the currnet user, incuding private data"""
        user = get_current_youtify_user_model()
        if user:
            json = get_youtify_user_struct(user, include_private_data=True)
        else:
            json = {
            }
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

class DeviceTokenHandler(webapp2.RequestHandler):

    def get(self):
        """Set a new device token for the user"""
        user = get_current_youtify_user_model()
        user.device = generate_device_token()
        user.save()
        json = {
            'device': user.device
        }
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

class LastNotificationSeenTimestampHandler(webapp2.RequestHandler):

    def post(self):
        user = get_current_youtify_user_model()
        val = self.request.get('val')
        json = {
            'message': '',
        }
        if user:
            if val > user.last_notification_seen_timestamp:
                user.last_notification_seen_timestamp = val
                user.save()
                json['message'] = 'timestamp updated'
            else:
                json['message'] = 'newer timestamp already set'
        else:
            json['message'] = 'no user found'
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

app = webapp2.WSGIApplication([
        ('/me', MeHandler),
        ('/me/last-notification-seen-timestamp', LastNotificationSeenTimestampHandler),
        ('/me/external_user_subscriptions', ExternalUserSubscriptionsHandler),
        ('/me/youtube_username', YouTubeUserNameHandler),
        ('/me/profile', ProfileHandler),
        ('/me/playlists', PlaylistsHandler),
        ('/me/request_new_device_token', DeviceTokenHandler),
        ('/me/settings', SettingsHandler),
        ('/me/followings/(.*)', FollowingsHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = migrations
import webapp2
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from model import FollowRelation
from model import YoutifyUser
from model import Activity
from model import Playlist
from model import ExternalUser
from string import Template
import json as simplejson
from datetime import datetime

TEMPLATE = """
<html>
<body>
</body>
Progress: $progress
<script type="text/javascript">
setTimeout(function() { location.href = '?page=$next'; }, 100);
</script>
</html>
"""

COMPLETE = """
<html>
<body>
<h1 style="color:green">DONE, $count iterations</h1>
</body>
</html>
"""

flattr_thing_cache = {}


class MigrationStepHandler(webapp2.RequestHandler):

    def get(self):
        global flattr_thing_cache
        page = int(self.request.get('page', '0'))
        page_size = 30
        count = 0

        #### START MIGRATION CODE ####

        for m in ExternalUser.all().fetch(page_size, page_size * page):
            count += 1
            m.last_checked = datetime.now()
            if m.nr_of_subscribers > 0:
                m.get_last_updated = True
            else:
                m.get_last_updated = False
            m.save()

        #### END MIGRATION CODE ####

        self.response.headers['Content-Type'] = 'text/html'
        if (count < page_size):
            self.response.out.write(Template(COMPLETE).substitute({
                'count': count,
            }))
        else:
            self.response.out.write(Template(TEMPLATE).substitute({
                'progress': page_size * page,
                'next': page + 1,
            }))

app = webapp2.WSGIApplication([
        ('/admin/migrations/set_last_checked', MigrationStepHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = model
import logging
import os
import random
import urllib
import hashlib
from google.appengine.ext import db
from google.appengine.api import users
from time import mktime

class ExternalUser(db.Model):
    type = db.StringProperty(required=True)
    external_user_id = db.StringProperty(required=True)
    username = db.StringProperty()
    avatar_url = db.StringProperty()
    subscribers = db.ListProperty(db.Key)
    nr_of_subscribers = db.IntegerProperty(default=0)
    last_updated = db.DateTimeProperty(auto_now_add=True)
    get_last_updated = db.BooleanProperty(default=True)
    last_checked = db.DateTimeProperty(auto_now_add=True)

class YoutifyUser(db.Model):
    created = db.DateTimeProperty(auto_now_add=True)
    last_login = db.DateTimeProperty()
    device = db.StringProperty()

    google_user = db.UserProperty()
    google_user2 = db.UserProperty()
    flattr_access_token = db.StringProperty()
    flattr_user_name = db.StringProperty()
    flattr_scope = db.StringProperty()
    flattr_automatically = db.BooleanProperty(default=True)
    lastfm_user_name = db.StringProperty()
    lastfm_access_token = db.StringProperty()
    lastfm_scrobble_automatically = db.BooleanProperty(default=True)
    youtube_username = db.StringProperty()
    dropbox_access_token = db.StringProperty()
    dropbox_user_name = db.StringProperty()

    nickname = db.StringProperty()
    nickname_lower = db.StringProperty()
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    tagline = db.StringProperty()
    playlists = db.ListProperty(db.Key)
    playlist_subscriptions = db.ListProperty(db.Key)
    last_notification_seen_timestamp = db.StringProperty()
    external_user_subscriptions = db.ListProperty(db.Key)
    nr_of_followers = db.IntegerProperty(default=0)
    nr_of_followings = db.IntegerProperty(default=0)
    nr_of_flattrs = db.IntegerProperty(default=0)
    migrated_playlists = db.BooleanProperty(default=False)

    last_emailed = db.DateTimeProperty()
    send_new_follower_email = db.BooleanProperty(default=True)
    send_new_subscriber_email = db.BooleanProperty(default=True)

    region = db.StringProperty()
    country = db.StringProperty()
    city = db.StringProperty()
    latlon = db.StringProperty()

class FollowRelation(db.Model):
    """ user1 follows user2 """
    user1 = db.IntegerProperty()
    user2 = db.IntegerProperty()

class Activity(db.Model):
    """
    Loosely follows the http://activitystrea.ms standard

    From the spec:

    "In its simplest form, an activity consists of an actor, a verb, an
    object, and a target."

    Implemented activities:

    actor signed up
    actor flattred <thing>
    actor subscribed to <playlist>
    actor followed <user>
    """
    owner = db.ReferenceProperty(reference_class=YoutifyUser)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    verb = db.StringProperty()
    actor = db.TextProperty()
    type = db.StringProperty()
    target = db.TextProperty()

class Playlist(db.Model):
    owner = db.ReferenceProperty(reference_class=YoutifyUser)
    json = db.TextProperty()
    private = db.BooleanProperty(default=False)
    tracks_json = db.TextProperty()
    title = db.StringProperty()
    followers = db.ListProperty(db.Key)
    nr_of_followers = db.IntegerProperty(default=0)
    favorite = db.BooleanProperty(default=False)

class PingStats(db.Model):
    date = db.DateTimeProperty(auto_now_add=True)
    pings = db.IntegerProperty(required=True)

class ExternalUserTimestamp(db.Model):
    external_user = db.ReferenceProperty(reference_class=ExternalUser)
    user = db.ReferenceProperty(reference_class=YoutifyUser)
    last_viewed = db.DateTimeProperty()

class AlternativeTrack(db.Model):
    track_id = db.StringProperty(required=True)
    track_type = db.StringProperty(required=True)
    replacement_for_id = db.StringProperty(required=True)
    replacement_for_type = db.StringProperty(required=True)
    vote = db.IntegerProperty(required=True)


# HELPERS
##############################################################################

def get_current_youtify_user_model():
    return get_youtify_user_model_for(users.get_current_user())

def get_youtify_user_model_for(user=None):
    return YoutifyUser.all().filter('google_user2 = ',user).get()

def get_youtify_user_model_by_nick(nick=None):
    return YoutifyUser.all().filter('nickname_lower = ', nick.lower()).get()

def get_youtify_user_model_by_id_or_nick(id_or_nick):
    if id_or_nick.isdigit():
        return YoutifyUser.get_by_id(int(id_or_nick))
    else:
        return get_youtify_user_model_by_nick(id_or_nick)

def create_youtify_user_model():
    m = YoutifyUser(google_user2=users.get_current_user(), device=str(random.random()), migrated_playlists=True)
    m.put()

    from activities import create_signup_activity # hack to avoid recursive dependency
    create_signup_activity(m)

    return m

def get_followings_for_youtify_user_model(youtify_user_model):
    ret = []
    for follow_relation_model in FollowRelation.all().filter('user1 =', youtify_user_model.key().id()):
        user = YoutifyUser.get_by_id(follow_relation_model.user2)
        ret.append(get_youtify_user_struct(user))
    return ret

def get_followers_for_youtify_user_model(youtify_user_model):
    ret = []
    for follow_relation_model in FollowRelation.all().filter('user2 =', youtify_user_model.key().id()):
        user = YoutifyUser.get_by_id(follow_relation_model.user1)
        ret.append(get_youtify_user_struct(user))
    return ret

def get_youtify_user_struct(youtify_user_model, include_private_data=False):
    if youtify_user_model.google_user2:
        email = youtify_user_model.google_user2.email()
    else:
        email = youtify_user_model.google_user.email()

    gravatar_email = email
    default_image = 'http://' + os.environ['HTTP_HOST'] + '/images/user.png'
    small_size = 64
    large_size = 208
    user = {
        'id': str(youtify_user_model.key().id()),
        'email': None,
        'flattr_user_name': youtify_user_model.flattr_user_name,
        'lastfm_user_name': youtify_user_model.lastfm_user_name,
        'dropbox_user_name': youtify_user_model.dropbox_user_name,
        'displayName': get_display_name_for_youtify_user_model(youtify_user_model),
        'nr_of_followers': youtify_user_model.nr_of_followers,
        'nr_of_followings': youtify_user_model.nr_of_followings,
        'nr_of_playlists': len(youtify_user_model.playlists) + len(youtify_user_model.playlist_subscriptions),
        'nr_of_flattrs': youtify_user_model.nr_of_flattrs,
        'nickname': youtify_user_model.nickname,
        'firstName': youtify_user_model.first_name,
        'lastName': youtify_user_model.last_name,
        'tagline': youtify_user_model.tagline,
        'smallImageUrl': "http://www.gravatar.com/avatar/" + hashlib.md5(gravatar_email.lower()).hexdigest() + "?" + urllib.urlencode({'d':default_image, 's':str(small_size)}),
        'largeImageUrl': "http://www.gravatar.com/avatar/" + hashlib.md5(gravatar_email.lower()).hexdigest() + "?" + urllib.urlencode({'d':default_image, 's':str(large_size)})
    }
    if include_private_data:
        user['email'] = email

    return user

def get_display_name_for_youtify_user_model(youtify_user_model):
    if youtify_user_model.first_name and youtify_user_model.last_name:
        return youtify_user_model.first_name + ' ' + youtify_user_model.last_name
    elif youtify_user_model.first_name:
        return youtify_user_model.first_name
    elif youtify_user_model.nickname:
        return youtify_user_model.nickname
    elif youtify_user_model.flattr_user_name:
        return youtify_user_model.flattr_user_name
    if youtify_user_model.google_user2:
        return youtify_user_model.google_user2.nickname().split('@')[0] # don't leak users email
    else:
        return youtify_user_model.google_user.nickname().split('@')[0] # don't leak users email

def get_url_for_youtify_user_model(youtify_user_model):
    if youtify_user_model.nickname:
        return 'http://www.youtify.com/' + youtify_user_model.nickname
    return 'http://www.youtify.com/users/' + str(youtify_user_model.key().id())

def get_playlist_structs_for_youtify_user_model(youtify_user_model, include_private_playlists=False):
    playlist_structs = []

    for playlist_model in db.get(youtify_user_model.playlists):
        if (not playlist_model.private) or include_private_playlists:
            playlist_structs.append(get_playlist_struct_from_playlist_model(playlist_model))

    for playlist_model in db.get(youtify_user_model.playlist_subscriptions):
        if playlist_model is not None:
            playlist_structs.append(get_playlist_struct_from_playlist_model(playlist_model))
        else:
            logging.error('User %s subscribes to deleted playlist' % (youtify_user_model.key().id()))

    return playlist_structs

def get_playlist_overview_structs(youtify_user_model, include_private_playlists=False):
    playlist_structs = []
    owner = get_youtify_user_struct(youtify_user_model)

    for playlist_model in db.get(youtify_user_model.playlists):
        if (not playlist_model.private) or include_private_playlists:
            playlist_structs.append({
                'title': playlist_model.title,
                'remoteId': playlist_model.key().id(),
                'isPrivate': playlist_model.private,
                'owner': owner,
                'isLoaded': False
            })

    for playlist_model in db.get(youtify_user_model.playlist_subscriptions):
        if playlist_model is not None:
            playlist_structs.append({
                'title': playlist_model.title,
                'remoteId': playlist_model.key().id(),
                'isPrivate': playlist_model.private,
                'owner': get_youtify_user_struct(playlist_model.owner),
                'isLoaded': False
            })

    return playlist_structs

def get_playlist_structs_by_id(playlist_id):
    playlist_model = Playlist.get_by_id(int(playlist_id))
    return get_playlist_struct_from_playlist_model(playlist_model)

def get_playlist_struct_from_playlist_model(playlist_model):
    playlist_struct = {
        'title': playlist_model.title,
        'videos': playlist_model.tracks_json,
        'remoteId': playlist_model.key().id(),
        'isPrivate': playlist_model.private,
        'owner': get_youtify_user_struct(playlist_model.owner),
        'followers': [],
        'favorite': playlist_model.favorite
    }

    for key in playlist_model.followers:
        youtify_user_model = db.get(key)
        playlist_struct['followers'].append(get_youtify_user_struct(youtify_user_model))

    return playlist_struct

def get_activities_structs(youtify_user_model, verbs=None, type=None, count=None):
    query = Activity.all()

    if youtify_user_model:
        query = query.filter('owner =', youtify_user_model)

    if verbs:
        query = query.filter('verb IN', verbs)

    if type:
        query = query.filter('type =', type)

    query = query.order('-timestamp')

    if count is not None:
        query = query.fetch(count)

    ret = []

    for m in query:
        ret.append({
            'timestamp': m.timestamp.strftime('%s'),
            'verb': m.verb,
            'type': m.type,
            'actor': m.actor,
            'target': m.target,
        })

    return ret

def get_settings_struct_for_youtify_user_model(youtify_user_model):
    return {
        'flattr_automatically': youtify_user_model.flattr_automatically,
        'lastfm_scrobble_automatically': youtify_user_model.lastfm_scrobble_automatically,
        'send_new_follower_email': youtify_user_model.send_new_follower_email,
        'send_new_subscriber_email': youtify_user_model.send_new_subscriber_email
    }

def get_external_user_subscription_struct(m, last_viewed=0):
    return {
        'type': m.type,
        'external_user_id': m.external_user_id,
        'username': m.username,
        'avatar_url': m.avatar_url,
        'last_updated': mktime(m.last_updated.timetuple()),
        'last_viewed': last_viewed,
    }

def get_external_user_subscriptions_struct_for_youtify_user_model(youtify_user_model):
    ret = []

    for external_user_model in db.get(youtify_user_model.external_user_subscriptions):
        last_viewed = ExternalUserTimestamp.all().filter('external_user =', external_user_model).filter('user =', youtify_user_model).get();
        last_viewed_ms = 0
        if last_viewed:
            last_viewed_ms = mktime(last_viewed.last_viewed.timetuple())
        ret.append(get_external_user_subscription_struct(external_user_model, last_viewed_ms))

    return ret

def generate_device_token():
    return str(random.random())

def get_alternative_struct(alternative_model):
    return {
        'track_id': alternative_model.track_id,
        'track_type': alternative_model.track_type,
        'replacement_for_id': alternative_model.replacement_for_id,
        'replacement_for_type': alternative_model.replacement_for_type,
        'vote': alternative_model.vote
    }
########NEW FILE########
__FILENAME__ = ping
# http://blog.notdot.net/2010/11/Storage-options-on-App-Engine

import os

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
import webapp2
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
import json as simplejson
from model import PingStats

def get_or_create_pings():
    pings = memcache.get('pings')
    if pings is None:
        pings = 0
        memcache.add('pings', pings)
    return pings

class PingHandler(webapp2.RequestHandler):
    """ Increment pings """
    def post(self):
        get_or_create_pings()
        memcache.incr('pings');
        current_user = users.get_current_user()
        if current_user == None:
            self.response.out.write('logged_out')
        else:
            self.response.out.write('ok')

    def get(self):
        get_or_create_pings()
        memcache.incr('pings');
        self.response.out.write('')

class PingCronHandler(webapp2.RequestHandler):
    """ Move pings from memcache to DB """

    def get(self):
        m = PingStats(pings=get_or_create_pings())
        m.put()
        memcache.set('pings', 0)

class PingGraphHandler(webapp2.RequestHandler):
    """ Get pings for the last 24h """

    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'html', 'usersonline.html')
        json = []

        for m in PingStats.all().order('-date').fetch(6*24*7):
            json.append({
                'date': str(m.date),
                'pings': m.pings,
            })

        self.response.out.write(template.render(path, {
            'pings': simplejson.dumps(json),
            'npings': len(json),
        }))

app = webapp2.WSGIApplication([
        ('/cron/store_pings', PingCronHandler),
        ('/stats', PingGraphHandler),
        ('/ping', PingHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = playlists
import logging
import webapp2
from google.appengine.ext.webapp import util
from google.appengine.ext import db
import json as simplejson
from activities import create_subscribe_activity
from model import get_current_youtify_user_model
from model import get_playlist_struct_from_playlist_model
from model import get_playlist_structs_by_id
from model import get_youtify_user_struct
from model import Playlist
from mail import send_new_subscriber_email

class PlaylistFollowersHandler(webapp2.RequestHandler):

    def get(self, playlist_id):
        """Gets the list of users that follow a playlist"""
        playlist_model = Playlist.get_by_id(int(playlist_id))
        json = []

        for key in playlist_model.followers:
            youtify_user_model = db.get(key)
            json.append(get_youtify_user_struct(youtify_user_model))

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(json))

    def post(self, playlist_id):
        """Follows a playlist"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        playlist_model = Playlist.get_by_id(int(playlist_id))
        if playlist_model is None:
            self.error(404)
            return

        if playlist_model.owner.key().id() == youtify_user_model.key().id():
            self.error(400)
            self.response.out.write('You can not subscribe to your own playlists')
            return

        if playlist_model.key() in youtify_user_model.playlist_subscriptions:
            self.error(400)
            self.response.out.write('You already subscribe to this playlist')
            return

        youtify_user_model.playlist_subscriptions.append(playlist_model.key())
        youtify_user_model.save()

        playlist_model.followers.append(youtify_user_model.key())
        playlist_model.nr_of_followers = len(playlist_model.followers)
        playlist_model.save()

        create_subscribe_activity(youtify_user_model, playlist_model)
        send_new_subscriber_email(youtify_user_model, playlist_model)

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

    def delete(self, playlist_id):
        """Unfollows a playlist"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        playlist_model = Playlist.get_by_id(int(playlist_id))

        youtify_user_model.playlist_subscriptions.remove(playlist_model.key())
        youtify_user_model.save()

        playlist_model.followers.remove(youtify_user_model.key())
        playlist_model.nr_of_followers = len(playlist_model.followers)
        playlist_model.save()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('ok')

class SpecificPlaylistHandler(webapp2.RequestHandler):

    def get(self):
        """Get playlist"""
        playlist_id = self.request.path.split('/')[-1]
        playlist_model = Playlist.get_by_id(int(playlist_id))
        playlist_struct = get_playlist_struct_from_playlist_model(playlist_model)

        if playlist_model.private and playlist_model.owner.key() != get_current_youtify_user_model().key():
            self.error(403)
            return

        if playlist_struct:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Access-Control-Allow-Origin'] = '*'

            self.response.out.write(simplejson.dumps(playlist_struct))
        else:
            self.error(404)

    def post(self):
        """Update playlist"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        playlist_id = self.request.path.split('/')[-1]
        playlist_model = Playlist.get_by_id(int(playlist_id))
        json = self.request.get('json', None)
        device = self.request.get('device')

        if json is None:
            self.error(400)
            return

        if playlist_model.owner.key() == youtify_user_model.key():
            if youtify_user_model.device != device:
                self.error(409)
                self.response.out.write('wrong_device')
                return
            else:
                old_playlist = simplejson.loads(json)
                if old_playlist.get('isLoaded', False) is False:
                    self.error(412)
                    self.response.out.write('cannot save a playlist that isn\'t loaded')
                    return

                playlist_model.private = old_playlist.get('isPrivate', False)
                playlist_model.tracks_json = simplejson.dumps(old_playlist['videos'])
                playlist_model.owner = youtify_user_model
                playlist_model.title = old_playlist['title']
                playlist_model.remote_id = old_playlist['remoteId']
                playlist_model.json = None
                playlist_model.save()

                self.response.out.write(str(playlist_model.key().id()))
        else:
            self.error(403)

    def delete(self):
        """Delete playlist"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        playlist_id = self.request.path.split('/')[-1]
        playlist_model = Playlist.get_by_id(int(playlist_id))

        if playlist_model.owner.key() == youtify_user_model.key():
            youtify_user_model.playlists.remove(playlist_model.key())
            youtify_user_model.save()

            playlist_model.delete()
        else:
            self.error(403)

class PlaylistsHandler(webapp2.RequestHandler):

    def post(self):
        """Create new playlist"""
        youtify_user_model = get_current_youtify_user_model()
        if youtify_user_model == None:
            self.error(403)
            return

        json_playlist = simplejson.loads(self.request.get('json'))

        if json_playlist is None:
            self.error(500)

        playlist_model = Playlist(owner=youtify_user_model, json=None)
        playlist_model.private = json_playlist.get('isPrivate', False)
        playlist_model.tracks_json = simplejson.dumps(json_playlist['videos'])
        playlist_model.title = json_playlist['title']
        playlist_model.put()

        youtify_user_model.playlists.append(playlist_model.key())
        youtify_user_model.save()

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(get_playlist_struct_from_playlist_model(playlist_model)))

app = webapp2.WSGIApplication([
        ('/api/playlists/(.*)/followers', PlaylistFollowersHandler),
        ('/api/playlists/.*', SpecificPlaylistHandler),
        ('/api/playlists', PlaylistsHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = playlists_toplist
import logging
from google.appengine.api import memcache
import webapp2
from google.appengine.ext.webapp import util
import json as simplejson
from model import Playlist
from model import get_playlist_struct_from_playlist_model

MEMCACHE_KEY = 'playlists_toplist'

def fetch_toplist():
    """Fetch the most popular playlists"""
    json = []
    for m in Playlist.all().filter('private =', False).order('-nr_of_followers').fetch(100):
        json.append(get_playlist_struct_from_playlist_model(m))
    return simplejson.dumps(json)

def get_playlists_toplist_json():
    """ Returns an empty playlist if anything goes wrong """
    cache = memcache.get(MEMCACHE_KEY)
    if cache is None:
        return '[]'
    return cache

class CronJobHandler(webapp2.RequestHandler):

    def get(self):
        json = fetch_toplist()

        memcache.delete(MEMCACHE_KEY)
        memcache.add(MEMCACHE_KEY, json, 3600*25)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json)

class ApiHandler(webapp2.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(get_playlists_toplist_json())

app = webapp2.WSGIApplication([
        ('/cron/generate_playlists_toplist', CronJobHandler),
        ('/api/toplists/playlists', ApiHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = soundcloud_id_to_permalink
import webapp2
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
import json as simplejson

class Handler(webapp2.RequestHandler):

    def get(self):
        id = self.request.get('id')
        response = urlfetch.fetch('https://api.soundcloud.com/tracks/' + id + '.json?consumer_key=206f38d9623048d6de0ef3a89fea1c4d')
        json = simplejson.loads(response.content)
        self.redirect(str(json['permalink_url']))

app = webapp2.WSGIApplication([
        ('/soundcloud_id_to_permalink', Handler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = sucks
import os
import webapp2
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

class SuckyBrowserHandler(webapp2.RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'html', 'yourbrowsersucks.html')

        self.response.out.write(template.render(path, {
            'ON_PRODUCTION': os.environ['SERVER_SOFTWARE'].startswith('Google App Engine'), # http://stackoverflow.com/questions/1916579/in-python-how-can-i-test-if-im-in-google-app-engine-sdk
        }))

class RockyDecisionHandler(webapp2.RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'html', 'yourdecisionrocks.html')

        self.response.out.write(template.render(path, {
            'ON_PRODUCTION': os.environ['SERVER_SOFTWARE'].startswith('Google App Engine'), # http://stackoverflow.com/questions/1916579/in-python-how-can-i-test-if-im-in-google-app-engine-sdk
        }))

app = webapp2.WSGIApplication([
        ('/yourbrowsersucks', SuckyBrowserHandler),
        ('/yourdecisionrocks', RockyDecisionHandler),
    ], debug=False)

########NEW FILE########
__FILENAME__ = users
import webapp2
from google.appengine.ext.webapp import util
from model import get_youtify_user_model_by_id_or_nick
from model import get_youtify_user_struct
from model import get_playlist_overview_structs
from model import get_followers_for_youtify_user_model
from model import get_followings_for_youtify_user_model
from model import get_activities_structs
import json as simplejson

class ActivitiesHandler(webapp2.RequestHandler):

    def get(self, id_or_nick):
        """Get activities for user as JSON"""
        youtify_user_model = get_youtify_user_model_by_id_or_nick(id_or_nick)

        verbs = self.request.get('verbs', None)
        type = self.request.get('type', None)
        count = self.request.get('count', None)

        if verbs:
            verbs = verbs.split(',')

        if count:
            count = int(count)

        if youtify_user_model is None:
            self.error(404)
            return

        ret = get_activities_structs(youtify_user_model, verbs, type, count)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(ret))

class FollowersHandler(webapp2.RequestHandler):

    def get(self, id_or_nick):
        """Get followers for user as JSON"""
        youtify_user_model = get_youtify_user_model_by_id_or_nick(id_or_nick)

        if youtify_user_model is None:
            self.error(404)
            return

        ret = get_followers_for_youtify_user_model(youtify_user_model)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(ret))

class FollowingsHandler(webapp2.RequestHandler):

    def get(self, id_or_nick):
        """Get followings for user as JSON"""
        youtify_user_model = get_youtify_user_model_by_id_or_nick(id_or_nick)

        if youtify_user_model is None:
            self.error(404)
            return

        ret = get_followings_for_youtify_user_model(youtify_user_model)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(ret))

class PlaylistsHandler(webapp2.RequestHandler):

    def get(self, id_or_nick):
        """Get playlists for user as JSON"""
        youtify_user_model = get_youtify_user_model_by_id_or_nick(id_or_nick)

        if youtify_user_model is None:
            self.error(404)
            return

        ret = get_playlist_overview_structs(youtify_user_model, False)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(ret))

class UserHandler(webapp2.RequestHandler):

    def get(self, id_or_nick):
        """Get user as JSON"""
        youtify_user_model = get_youtify_user_model_by_id_or_nick(id_or_nick)
        youtify_user_struct = None

        if youtify_user_model is None:
            self.error(404)
            return

        youtify_user_struct = get_youtify_user_struct(youtify_user_model)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(simplejson.dumps(youtify_user_struct))

    def post(self):
        """Update user"""
        self.error(500)

app = webapp2.WSGIApplication([
        ('/api/users/(.*)/activities', ActivitiesHandler),
        ('/api/users/(.*)/followers', FollowersHandler),
        ('/api/users/(.*)/followings', FollowingsHandler),
        ('/api/users/(.*)/playlists', PlaylistsHandler),
        ('/api/users/(.*)', UserHandler),
    ], debug=False)

########NEW FILE########
