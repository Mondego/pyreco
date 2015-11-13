__FILENAME__ = new_version
#!/usr/bin/env python
import subprocess

def call(args):
    cmd = ' '.join(args)
    print("== attempting == %s =="%cmd)
    if subprocess.call(args):
        print("== !problem!  == %s ==" % cmd)
        exit(1)
    print("== done       == %s ==" % cmd)
    print

version = [line for line in open('setup.py').read().split('\n') if line.startswith('__VERSION__ = ')][0].split(' ')[-1].strip('"').strip("'")

call(['git', 'commit', '-v'])
call(['git', 'push'])
call(['git', 'tag', '-a', 'v%s'%version, '-m="version bump"'])
call(['git', 'push', '--tags'])
call(['python', 'setup.py', 'sdist', 'upload'])


########NEW FILE########
__FILENAME__ = constants
MILLI_MICROS = 10**3
SECOND_MICROS = MILLI_MICROS * 10**3
MINUTE_MICROS = SECOND_MICROS * 60
HOUR_MICROS = MINUTE_MICROS * 60
MEAN_DAY_MICROS = HOUR_MICROS * 24
MEAN_WEEK_MICROS = MEAN_DAY_MICROS * 7
MEAN_MONTH_MICROS = (MEAN_DAY_MICROS * (365*4+1)) / (12*4)
MEAN_YEAR_MICROS = (MEAN_DAY_MICROS * (365*4+1)) / 4

HALF_MILLI_MICROS = MILLI_MICROS / 2
HALF_SECOND_MICROS = SECOND_MICROS / 2
HALF_MINUTE_MICROS = MINUTE_MICROS / 2
HALF_HOUR_MICROS = HOUR_MICROS / 2
HALF_MEAN_DAY_MICROS = MEAN_DAY_MICROS / 2
HALF_MEAN_WEEK_MICROS = MEAN_WEEK_MICROS / 2
HALF_MEAN_MONTH_MICROS = MEAN_MONTH_MICROS / 2
HALF_MEAN_YEAR_MICROS = MEAN_YEAR_MICROS / 2


########NEW FILE########
__FILENAME__ = dj
from sanetime import time,SaneTime
try:
    from django.db import models
    from django import forms
except ImportError:
    raise RuntimeError('Django is required for sanetime.dj.')

class SaneTimeFormField(forms.DateTimeField):
    pass

class SaneTimeField(models.BigIntegerField):

    description = "A field to hold sanetimes (i.e. microseconds since epoch)."

    __metaclass__ = models.SubfieldBase

    def __init__(self, verbose_name=None, name=None, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now, self.auto_now_add = auto_now, auto_now_add
        if auto_now or auto_now_add:
            kwargs['editable'] = False
            kwargs['blank'] = True
        super(SaneTimeField, self).__init__(verbose_name, name, **kwargs)

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = time()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(SaneTimeField, self).pre_save(model_instance, add)

    def to_python(self, value):
        if value is not None:
            if not isinstance(value, SaneTime):
                value = time(value)
            return value
        return super(SaneTimeField,self).to_python(value)

    def get_prep_value(self, value):
        if value is not None:
            return int(value)
        return super(SaneTimeField,self).get_prep_value(value)


from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^sanetime\.dj\.SaneTimeField"])
    


########NEW FILE########
__FILENAME__ = error
class Error(ValueError): pass

class TimeConstructionError(Error): pass

########NEW FILE########
__FILENAME__ = sanedelta
from .constants import MILLI_MICROS,SECOND_MICROS,MINUTE_MICROS,HOUR_MICROS,MEAN_DAY_MICROS,MEAN_WEEK_MICROS,MEAN_MONTH_MICROS,MEAN_YEAR_MICROS,HALF_MILLI_MICROS,HALF_SECOND_MICROS,HALF_MINUTE_MICROS,HALF_HOUR_MICROS,HALF_MEAN_DAY_MICROS,HALF_MEAN_WEEK_MICROS,HALF_MEAN_MONTH_MICROS,HALF_MEAN_YEAR_MICROS
import time

TRANSLATIONS = (
        (('my','mean_years'),MEAN_YEAR_MICROS),
        (('mm','mean_months'),MEAN_MONTH_MICROS),
        (('mw','mean_weeks'),MEAN_WEEK_MICROS),
        (('md','mean_days'),MEAN_DAY_MICROS),
        (('h','hours'),HOUR_MICROS),
        (('m','mins','minutes'),MINUTE_MICROS),
        (('s','secs','seconds'),SECOND_MICROS),
        (('ms','millis','milliseconds'),MILLI_MICROS),
        (('us','micros','microseconds'),1) )
TRANSLATION_HASH = dict((alt,v) for k,v in TRANSLATIONS for alt in k)

class SaneDelta(object):
    def __init__(self, *args, **kwargs):
        if args:
            self.us = int(args[0])
        else:
            self.us = sum(TRANSLATION_HASH[k]*(v or 0) for k,v in kwargs.iteritems())

    # rounded amounts
    @property
    def rounded_microseconds(self): return self.us
    @property
    def rounded_milliseconds(self): return (self.us + HALF_MILLI_MICROS) / MILLI_MICROS
    @property
    def rounded_seconds(self): return (self.us + HALF_SECOND_MICROS) / SECOND_MICROS
    @property
    def rounded_minutes(self): return (self.us + HALF_MINUTE_MICROS) / MINUTE_MICROS
    @property
    def rounded_hours(self): return (self.us + HALF_HOUR_MICROS) / HOUR_MICROS
    @property
    def rounded_mean_days(self): return (self.us + HALF_MEAN_DAY_MICROS) / MEAN_DAY_MICROS
    @property
    def rounded_mean_weeks(self): return (self.us + HALF_MEAN_WEEK_MICROS) / MEAN_WEEK_MICROS
    @property
    def rounded_mean_months(self): return (self.us + HALF_MEAN_MONTH_MICROS) / MEAN_MONTH_MICROS
    @property
    def rounded_mean_years(self): return (self.us + HALF_MEAN_YEAR_MICROS) / MEAN_YEAR_MICROS

    # aliases
    rus = rounded_micros = rounded_microseconds
    rms = rounded_millis = rounded_milliseconds
    rs = rounded_secs = rounded_seconds
    rm = rounded_mins = rounded_minutes
    rh = rounded_hours
    rmd = rounded_mean_days
    rmw = rounded_mean_weeks
    rmm = rounded_mean_months
    rmy = rounded_mean_years

    #rounded amounts are default aliases
    micros = microseconds = rus
    ms = millis = milliseconds = rms
    s = secs = seconds = rs
    m = mins = minutes = rm
    h = hours = rh
    md = mean_days = rmd
    mw = mean_weeks = rmw
    mm = mean_months = rmm
    my = mean_years = rmy

    # unrounded amounts
    @property
    def whole_microseconds(self): return self.us
    @property
    def whole_milliseconds(self): return self.us / MILLI_MICROS
    @property
    def whole_seconds(self): return self.us / SECOND_MICROS
    @property
    def whole_minutes(self): return self.us / MINUTE_MICROS
    @property
    def whole_hours(self): return self.us / HOUR_MICROS
    @property
    def whole_mean_days(self): return self.us / MEAN_DAY_MICROS
    @property
    def whole_mean_weeks(self): return self.us / MEAN_WEEK_MICROS
    @property
    def whole_mean_months(self): return self.us / MEAN_MONTH_MICROS
    @property
    def whole_mean_years(self): return self.us / MEAN_YEAR_MICROS

    # aliases
    wus = whole_micros = whole_microseconds
    wms = whole_millis = whole_milliseconds
    ws = whole_secs = whole_seconds
    wm = whole_mins = whole_minutes
    wh = whole_hours
    wmd = whole_mean_days
    wmw = whole_mean_weeks
    wmm = whole_mean_months
    wmy = whole_mean_years

    # float amounts
    @property
    def float_microseconds(self): return float(self.us)
    @property
    def float_milliseconds(self): return float(self.us) / MILLI_MICROS
    @property
    def float_seconds(self): return float(self.us) / SECOND_MICROS
    @property
    def float_minutes(self): return float(self.us)/ MINUTE_MICROS
    @property
    def float_hours(self): return float(self.us) / HOUR_MICROS
    @property
    def float_mean_days(self): return float(self.us) / MEAN_DAY_MICROS
    @property
    def float_mean_weeks(self): return float(self.us) / MEAN_WEEK_MICROS
    @property
    def float_mean_months(self): return float(self.us) / MEAN_MONTH_MICROS
    @property
    def float_mean_years(self): return float(self.us) / MEAN_YEAR_MICROS

    # aliases
    fus = float_micros = float_microseconds
    fms = float_millis = float_milliseconds
    fs = float_secs = float_seconds
    fm = float_mins = float_minutes
    fh = float_hours
    fmd = float_mean_days
    fmw = float_mean_weeks
    fmm = float_mean_months
    fmy = float_mean_years

    # positional amounts
    @property
    def positional_microseconds(self): return self.us % SECOND_MICROS
    @property
    def positional_milliseconds(self): return self.us % SECOND_MICROS / MILLI_MICROS
    @property
    def positional_seconds(self): return self.us % MINUTE_MICROS / SECOND_MICROS
    @property
    def positional_minutes(self): return self.us % HOUR_MICROS / MINUTE_MICROS
    @property
    def positional_hours(self): return self.us % MEAN_DAY_MICROS / HOUR_MICROS

    #aliases
    pus = positional_micros = positional_microseconds
    pms = positional_millis = positional_milliseconds
    ps = positional_secs = positional_seconds
    pm = positional_mins = positional_minutes
    ph = positional_hours

    # positional rounded amounts
    @property
    def positional_rounded_microseconds(self): return self.us % SECOND_MICROS
    @property
    def positional_rounded_milliseconds(self): return (self.us % SECOND_MICROS + HALF_MILLI_MICROS) / MILLI_MICROS
    @property
    def positional_rounded_seconds(self): return (self.us % MINUTE_MICROS + HALF_SECOND_MICROS) / SECOND_MICROS
    @property
    def positional_rounded_minutes(self): return (self.us % HOUR_MICROS + HALF_MINUTE_MICROS) / MINUTE_MICROS
    @property
    def positional_rounded_hours(self): return (self.us % MEAN_DAY_MICROS + HALF_HOUR_MICROS) / HOUR_MICROS

    #aliases
    prus = positional_rounded_micros = positional_rounded_microseconds
    prms = positional_rounded_millis = positional_rounded_milliseconds
    prs = positional_rounded_secs = positional_rounded_seconds
    prm = positional_rounded_mins = positional_rounded_minutes
    prh = positional_rounded_hours

    def clone(self): return SaneDelta(self.us)

    def __cmp__(self, other): return cmp(self.us, int(other))
    def __hash__(self): return hash(self.us)

    def __int__(self): return self.us
    def __long__(self): return long(self.us)

    def __add__(self, operand): return SaneDelta(self.us + int(operand))
    def __sub__(self, operand): return SaneDelta(self.us - int(operand))
    def __mul__(self, operand): return SaneDelta(self.us * int(operand))
    def __div__(self, operand): return SaneDelta(self.us / int(operand))
    def __rmul__(self, operand): return int(operand) * self.us
    def __rdiv__(self, operand): return int(operand) / self.us

    def __neg__(self): return SaneDelta(-self.us)
    def __pos__(self): return SaneDelta(+self.us)
    def __abs__(self): return SaneDelta(abs(self.us))

    def __repr__(self): return 'SaneDelta(%s)'%self.us
    def __str__(self): return unicode(self).encode('utf-8')
    def __unicode__(self): return self.construct_str()


    @property
    def abbr(self): return self.construct_str(max_positions=2, final_position='s', separator='', no_zero_positions=True)

    #TODO: test this sucker
    #TODO; test negative deltas
    def construct_str(self, max_positions=None, final_position='us', separator=' ', no_zero_positions=False):
        parts = []
        delta = abs(self)
        max_positions = max_positions or 6
        if final_position == 'md' or len(parts)==max_positions-1 and delta.wmd:
            parts.append((delta.rmd,"%sd"%delta.rmd))
        else:
            if delta.wmd: parts.append((delta.wmd,"%sd"%delta.wmd))
            if final_position == 'h' or len(parts)==max_positions-1 and (delta.ph or len(parts)):
                parts.append((delta.prh,"%sh"%delta.prh))
            else:
                if delta.ph or len(parts): parts.append((delta.ph,"%sh"%delta.ph))
                if final_position == 'm' or len(parts)==max_positions-1 and (delta.pm or len(parts)):
                    parts.append((delta.prm,"%sm"%delta.prm))
                else:
                    if delta.pm or len(parts): parts.append((delta.pm,"%sm"%delta.pm))
                    if final_position == 's' or len(parts)==max_positions-1 and (delta.ps or len(parts)):
                        parts.append((delta.prs,"%ss"%delta.prs))
                    else:
                        parts.append((delta.ps,'%s'%delta.ps))
                        if final_position == 'ms' or len(parts)==max_positions and (delta.pms or len(parts)):
                            parts.append((delta.prms,".%03ds"%delta.prms,True))
                        else:
                            parts.append((delta.pus,".%06ds"%delta.pus,True))
        while no_zero_positions and len(parts)>1 and not parts[-1][0]: parts.pop()
        return ("%s%s%s%s" % ('' if self>=0 else '-', separator.join([p[1] for p in parts[:-1]]), '' if len(parts[-1])==3 else separator, parts[-1][1])).strip()

    def sleep(self): return time.sleep(self.float_seconds)

 


#TODO: implement
    #def ago(self):
        #"""
        #Get a datetime object or a int() Epoch timestamp and return a
        #pretty string like 'an hour ago', 'Yesterday', '3 months ago',
        #'just now', etc

        #copied from http://stackoverflow.com/questions/1551382/python-user-friendly-time-format
        #and then tweaked
        #"""
        #micro_delta = SaneTime().us - self.us
        #second_delta = (micro_delta+500*1000)/1000**2
        #day_delta = (micro_delta+1000**2*60**2*12)/(1000**2*60**2*24)

        #if micro_delta < 0:
            ## TODO: implement future times
            #return ''

        #if day_delta == 0:
            #if second_delta < 10:
                #return "just now"
            #if second_delta < 30:
                #return "%s seconds ago" % second_delta
            #if second_delta < 90:
                #return "a minute ago"
            #if second_delta < 30*60:
                #return "%s minutes ago" % ((second_delta+30)/60)
            #if second_delta < 90*60:
                #return "an hour ago"
            #return "%s hours ago" % ((second_delta+30*60)/60**2)
        #if day_delta < 2:
            #return "yesterday"
        #if day_delta < 7:
            #return "%s days ago" % day_delta
        #if day_delta < 11:
            #return "a week ago" % day_delta
        #if day_delta < 45:
            #return "%s weeks ago" % ((day_delta+3)/7)
        #if day_delta < 400:
            #return "%s months ago" % ((day_delta+15)/30)
        #return "%s years ago" % ((day_delta+182)/365)


def nsanedelta(*args, **kwargs): 
    if args:
        if args[0] is None: return None
    elif kwargs:
        if set(kwargs.values()) == set([None]): return None
    return SaneDelta(*args, **kwargs)

#aliases:
delta = sanedelta = SaneDelta
ndelta = nsanedelta

########NEW FILE########
__FILENAME__ = sanespan
from . import time

class SaneSpan(object):
    def __init__(self, start, delta=None, end=None):
        super(SaneSpan,self).__init__()
        self.start = time(start)
        if delta is None:
            end = time(end or 0)
            self.start = min(self.start,end)
            self.delta = end-self.start
        else:
            self.delta = delta

    @property
    def end(self): return self.start+self.delta

    def overlaps(self, other):
        return self.start < other.end and self.end > other.start

    def __repr__(self): return 'SaneSpan(start=%s,delta=%s)'%(repr(self.start),repr(self.delta))
    def __str__(self): return unicode(self).encode('utf-8')
    def __unicode__(self): u"%s +%s" % (unicode(self.start), unicode(self.delta))

def nsanespan(*args, **kwargs): 
    if args and (args[0] is None or args[-1] is None): return None
    return SaneSpan(*args, **kwargs)

#aliases:
span = sanespan = SaneSpan
nspan = nsanespan


########NEW FILE########
__FILENAME__ = sanetime
from .constants import MILLI_MICROS,SECOND_MICROS,MINUTE_MICROS
import calendar
from datetime import datetime
from dateutil import parser
from dateutil.tz import tzlocal
from .error import TimeConstructionError
from .sanedelta import SaneDelta
import pytz


#TODO: ensure that this is immutable, and that addiiton,etc always producesa  new object!!!
 
MICROS_TRANSLATIONS = (
        (('m','mins','minutes','epoch_mins','epoch_minutes'),MINUTE_MICROS),
        (('s','secs','seconds','epoch_secs','epoch_seconds'),SECOND_MICROS),
        (('ms','millis','milliseconds','epoch_millis','epoch_milliseconds'),MILLI_MICROS),
        (('us','micros','microseconds','epoch_micros','epoch_microseconds'),1) )
MICROS_TRANSLATION_HASH = dict((alt,v) for k,v in MICROS_TRANSLATIONS for alt in k)

class SaneTime(object):
    """
    A time stored in epoch microseconds, and optionally decorated with a timezone.
    An object of this class represents a moment in time.
    A moment in time experience in America/New_York is equal to the same moment in time experienced in Europe/Dublin
    """



    """
    Why not store in millis or seconds?
    datetime stores things in micros, and since millis already crosses over the 32bit boundary, we
    might as well store everything we got in the 64 bit numbers.  This will force 32bit machines to
    go to long's, so maybe a little reduced performance there, but isn't everything on 64 bit now?
    This also avoids the unexpected scenario where two different datetimes would compare as equal
    when they were converted to sanetimes.  As to why-not-seconds, well that's just lame.  You can
    easily go to seconds or millis from sanetime by using the .s or .ms properties.

    When you do arithmetic with sanetime you are operating on microseconds.  st + 1 creates a new
    sanetime that is 1 microsecond in the future from the st sanetime.

    When you do comparisons, all comparisons are happening at the microsecond level.  You are
    comparing microseconds in time.
    """

    def __init__(self, *args, **kwargs):
        """
        acceptable arg inputs:
          1) epoch micros integer (or int like)
          2) a datetime
            NOTE!! a naive datetime is assumed to be in UTC, unless you tell this
            method otherwise by also passing in a tz paramter.  A timezoned datetime is 
            preserved with the timezone it has
          3) a string representation that the dateutil parser can deal with
          4) multiple args just as datetime would accept

        acceptable keyworded inputs:
          1) us = an int/long in epoch micros
          2) ms = an int/long in epoch millis
          3) s = an int/long in epoch seconds
          4) m = an int/long in epoch minutes
          5) tz = a timezone (either a pytz timezone object, a recognizeable pytz timezone string, or a dateutil tz object)
        """
        super(time,self).__init__()
        uss = set()
        tzs = set()
        naive_dt = None
        avoid_localize = False

        for k,v in kwargs.iteritems():
            if k in ('tz','timezone'):
                tzs.add(SaneTime.to_timezone(v))
            elif k in MICROS_TRANSLATION_HASH:
                uss.add(MICROS_TRANSLATION_HASH[k]*v)
            else:
                raise TimeConstructionError("Unexpected kwarg in SaneTime constructor! (%s = %s)" % (k,v))

        args = list(args)
        if len(args)>2 and len(args)<=8:
            args = [datetime(*args)]
        if len(args)==2:
            tzs.add(SaneTime.to_timezone(args.pop()))
        if len(args)==1:
#            import pdb; pdb.set_trace()
            arg = args.pop()
            if hasattr(arg,'__int__'):
                uss.add(int(arg))
                if hasattr(arg,'tz'): tzs.add(arg.tz)
            elif isinstance(arg, basestring):
                parts = arg.strip().split(' ')
                if len(parts)>1 and parts[-1].startswith('+'):
                    try:
                        tzs.add(SaneTime.to_timezone(parts[-1][1:]))
                        arg = ' '.join(parts[:-1])
                    except: pass
                utc = arg.endswith('Z') or arg.endswith('+00:00')  # to deal with strange gunicorn issue -- doesn't want to use UTC time in these cases
                arg = parser.parse(arg)
                if arg.tzinfo:  # parsed timezones are a special breed of retard
                    if utc:  # put this in place to guard against wierd gunicorn issue -- gunicorn will attempt to force local timezone when there's an explicit UTC timezone associated! not sure where that's coming from.
                        tzs.add(pytz.utc)
                        arg = arg.replace(tzinfo=None)
                    elif isinstance(arg.tzinfo, tzlocal):  # in case the parser decides to use tzlocal instead of a tzoffset
                        arg = arg.replace(tzinfo=None)
                    else:
                        # can't rely on the dateutil parser for timezone stuff-- so we go back to UTC and force tz to be set in other ways
                        avoid_localize = True # but we'll still convert back to UTC and allow timezone decoration
                        arg = arg.astimezone(pytz.utc).replace(tzinfo=None)
            if type(arg) == datetime:
                naive_dt = arg
                if naive_dt.tzinfo:
                    tzs.add(SaneTime.to_timezone(str(naive_dt.tzinfo)))
                    naive_dt = naive_dt.replace(tzinfo=None)

        if len(tzs)>1:
            raise TimeConstructionError("constructor arguments seem to specify more than one different timezone!  I can't possibly resolve that!  (timezones implied = %s)"%(tzs))

        # now we have enough info to figure out the tz:
        self.tz = len(tzs) and tzs.pop() or pytz.utc

        # and now that we've figured out tz, we can fully deconstruct the dt
        if naive_dt:
            if avoid_localize:
                uss.add(SaneTime.utc_datetime_to_us(naive_dt))
            else:
                uss.add(SaneTime.utc_datetime_to_us(self.tz.localize(naive_dt).astimezone(pytz.utc)))

        # if we got nothing yet for micros, then make it now
        if len(uss)==0:
            uss.add(SaneTime.utc_datetime_to_us(datetime.utcnow()))

        if len(uss)>1:
            raise TimeConstructionError("constructor arguments seem to specify more than one different time!  I can't possibly resolve that!  (micro times implied = %s)"%(uss))

        self.us = uss.pop()
        
        if len(args)>0:
            raise TimeConstructionError("Unexpected constructor arguments")

        
    @property
    def ms(self): return self.us/MILLI_MICROS 
    epoch_milliseconds = epoch_millis = milliseconds = millis = ms
    @property
    def s(self): return self.us/SECOND_MICROS
    epoch_seconds = epoch_secs = seconds = secs = s
    @property
    def m(self): return self.us/MINUTE_MICROS
    epoch_minutes = epoch_mins = minutes = mins = m
    @property
    def micros(self): return self.us
    epoch_microseconds = epoch_micros = microseconds = micros

    @property
    def tz_name(self): return self.tz.zone
    @property
    def tz_abbr(self): return self.tz._tzname

    def set_tz(self, tz): 
        self.tz = self.__class__.to_timezone(tz); return self
    def with_tz(self, tz):
        return self.__class__(self.us,tz)


    @property
    def _tuple(self): return (self.us, self.tz)

    def strftime(self, *args, **kwargs): return self.datetime.strftime(*args, **kwargs)

    def __cmp__(self, other): 
        if not hasattr(other, '__int__'): other = SaneTime(other)
        return cmp(self.us, int(other))
    def __hash__(self): return self.us.__hash__()

    def __add__(self, operand): 
        if not hasattr(operand, '__int__'): operand = SaneTime(operand)
        return self.__class__(self.us + int(operand),tz=self.tz)
    def __sub__(self, operand):
        if not hasattr(operand, '__int__'): operand = SaneTime(operand)
        if isinstance(operand, SaneTime): return SaneDelta(self.us - int(operand))
        return self.__add__(-int(operand))
    def __mul__(self, operand):
        return self.us * int(operand)
    def __div__(self, operand):
        return self.us / int(operand)
    
    def __int__(self): return int(self.us)
    def __long__(self): return long(self.us)

    def __repr__(self): return u"SaneTime(%s,%s)" % (self.us,repr(self.tz))
    def __str__(self): return unicode(self).encode('utf-8')
    def __unicode__(self): 
        dt = self.datetime
        micros = u".%06d"%dt.microsecond if dt.microsecond else ''
        time = u" %02d:%02d:%02d%s"%(dt.hour,dt.minute,dt.second,micros) if dt.microsecond or dt.second or dt.minute or dt.hour else ''
        return u"%04d-%02d-%02d%s +%s" % (dt.year, dt.month, dt.day, time, dt.tzinfo.zone)

    def clone(self): 
        """ cloning stuff """
        return self.__class__(self.us,self.tz)

    @property
    def ny_str(self): 
        """ a ny string """
        return self.ny_ndt.strftime('%I:%M:%S%p %m/%d/%Y')
    
    @property
    def utc_datetime(self): return SaneTime.us_to_utc_datetime(self.us)
    utc_dt = utc_datetime
    @property
    def utc_naive_datetime(self): return self.utc_datetime.replace(tzinfo=None)
    utc_ndt = utc_naive_datetime
    
    def to_timezoned_datetime(self, tz): return self.utc_datetime.astimezone(SaneTime.to_timezone(tz))
    def to_timezoned_naive_datetime(self, tz): return self.to_timezoned_datetime(tz).replace(tzinfo=None)

    @property
    def datetime(self): return self.to_timezoned_datetime(self.tz)
    dt = datetime
    @property
    def naive_datetime(self): return self.to_timezoned_naive_datetime(self.tz)
    ndt = naive_datetime

    @property
    def ny_datetime(self): return self.to_timezoned_datetime('America/New_York')
    ny_dt = ny_datetime
    @property
    def ny_naive_datetime(self): return self.to_timezoned_naive_datetime('America/New_York')
    ny_ndt = ny_naive_datetime



    @property
    def year(self): return self.dt.year
    @property
    def month(self): return self.dt.month
    @property
    def day(self): return self.dt.day
    @property
    def hour(self): return self.dt.hour
    @property
    def minute(self): return self.dt.minute
    @property
    def second(self): return self.dt.second
    @property
    def microsecond(self): return self.dt.microsecond

    #def add_datepart(self, months=None, years=None, auto_day_adjust=True):
        #months = (months or 0) + (years or 0) * 12
        #dt = self.utc_dt
        #day = dt.day
        #month = dt.month + months%12
        #year = dt.year + months/12
        #if auto_day_adjust:
            #if day>=29 and month==2:
                #leap_year = year%4==0 and (not year%100==0 or year%400==0)
                #day = 29 if leap_year else 28
            #elif day==31 and month in (4,6,9,11):
                #day = 30
        #return SaneTime(fucked_datetime(year,month,day,dt.hour,dt.minute,dt.second,dt.microsecond,tz=pytz.utc))

    @classmethod
    def utc_datetime_to_us(kls, dt):
        return calendar.timegm(dt.timetuple())*1000**2+dt.microsecond

    @classmethod
    def us_to_utc_datetime(kls, us):
        return pytz.utc.localize(datetime.utcfromtimestamp(us/10**6)).replace(microsecond = us%10**6)

    @classmethod
    def to_timezone(kls, tz):
        if not isinstance(tz, basestring): return tz
        return pytz.timezone(tz)


# null passthru utility
def ntime(*args, **kwargs): 
    if args:
        if args[0] is None: return None
    elif kwargs:
        if None in [v for k,v in kwargs.iteritems() if k!='tz']: return None
    return SaneTime(*args, **kwargs)

#primary aliases
time = sanetime = SaneTime
nsanetime = ntime


########NEW FILE########
__FILENAME__ = sanetztime
from sanetime import SaneTime

"""
Sane wrappers around the python's datetime / time / date / timetuple / pytz / timezone / calendar /
timedelta / utc shitshow.  This takes care of most of the ridiculous shit so you don't have to
flush precious brain cells down the toilet trying to figure all this out.  You owe me a beer.  At
least.

There are two classes that you mind find useful here, and you should understand the difference:

* sanetime:  this class is only concerned with a particular moment in time, NOT where that moment
        was experienced.
* sanetztime:  this class is concerned with a particular moment in time AND in what timezone that
        moment was experienced.
"""

class SaneTzTime(SaneTime):
    """
    sanetztime is concerned with a particular moment in time AND which timezone that moment in time
    was experienced.  Two sanetztimes are not equal unless they are the same moment in time and
    they are in the same timezone as identified by the pytz timezone.  Even if these timezones
    appear to have the same definition, but have a different label they are considered different.
    They must have the same structure and the same label.

    In most other respects sanetztime is just like sanetime.
    """

    def __cmp__(self, other): 
        if not hasattr(other, '_tuple'): other = SaneTzTime(other)
        return cmp(self._tuple, other._tuple)
    def __hash__(self): return self._tuple.__hash__()
    def __repr__(self): return u"SaneTzTime(%s,%s)" % (self.us,repr(self.tz))

    @property
    def time(self): return SaneTime(self.us,self.tz)
    sanetime=time
    
# null passthrough utility
def nsanetztime(*args, **kwargs): 
    if not args or args[0] is None: return None
    return SaneTzTime(*args, **kwargs)

#primary aliases
tztime = sanetztime = SaneTzTime
ntztime = nsanetztime

########NEW FILE########
__FILENAME__ = test_delta
import unittest2 as unittest
from .. import time,delta

class SaneDeltaTest(unittest.TestCase):
    def test_construction(self):
        self.assertEquals(1+1000*(2+1000*(3+60*(4+60*(5+24*(6+7*7))))),delta(us=1,ms=2,s=3,m=4,h=5,md=6,mw=7))
        self.assertEquals(1,time(10)-time(9))
        self.assertEquals(-1,time(9)-time(10))

    def test_copy_construction(self):
        self.assertEquals(123, delta(delta(123)))

    def test_clone(self):
        self.assertEquals(123, delta(123).clone())

    def test_casting(self):
        self.assertEquals(123, int(delta(123)))
        self.assertEquals(123, long(delta(123)))
        self.assertEquals('6d 5h 4m 3.002001s', str(delta(us=1,ms=2,s=3,m=4,h=5,md=6)))
        self.assertEquals(u'6d 5h 4m 3.002001s', unicode(delta(us=1,ms=2,s=3,m=4,h=5,md=6)))
        self.assertEquals(hash(123), hash(delta(123)))

    def test_add(self):
        self.assertEquals(time(2012,1,1,0,0,0,1), time(2012,1,1)+delta(us=1))
        self.assertEquals(time(2012,1,1,0,0,0,1000), time(2012,1,1)+delta(ms=1))
        self.assertEquals(time(2012,1,1,0,0,1), time(2012,1,1)+delta(s=1))
        self.assertEquals(time(2012,1,1,0,1), time(2012,1,1)+delta(m=1))
        self.assertEquals(time(2012,1,1,1), time(2012,1,1)+delta(h=1))
        self.assertEquals(time(2012,1,2), time(2012,1,1)+delta(md=1))
        self.assertEquals(time(2012,1,8), time(2012,1,1)+delta(mw=1))
        self.assertEquals(time(2012,1,31,10,30), time(2012,1,1)+delta(mm=1))
        self.assertEquals(time(2012,12,31,6), time(2012,1,1)+delta(my=1))

    def test_construct_str(self):
        self.assertEquals('0.000001s', delta(us=1).construct_str())
        self.assertEquals('0.001000s', delta(ms=1).construct_str())
        self.assertEquals('0.001s', delta(ms=1).construct_str(max_positions=1))
        self.assertEquals('0.001s', delta(ms=1).construct_str(final_position='ms'))
        self.assertEquals('0.001002s', delta(ms=1,us=2).construct_str())
        self.assertEquals('3.001002s', delta(s=3,ms=1,us=2).construct_str())
        self.assertEquals('-3.001002s', (-delta(s=3,ms=1,us=2)).construct_str())
        self.assertEquals('3.001s', delta(s=3,ms=1,us=2).construct_str(final_position='ms'))
        self.assertEquals('3.002s', delta(s=3,ms=1,us=500).construct_str(final_position='ms'))
        self.assertEquals('3s', delta(s=3,ms=499,us=500).construct_str(final_position='s'))
        self.assertEquals('4s', delta(s=3,ms=500).construct_str(final_position='s'))
        self.assertEquals('4m 4s', delta(m=4,s=3,ms=500).construct_str(final_position='s'))
        self.assertEquals('4m4s', delta(m=4,s=3,ms=500).construct_str(final_position='s',separator=''))
        self.assertEquals('4m4s', delta(m=4,s=3,ms=500).construct_str(final_position='s',max_positions=2, separator=''))
        self.assertEquals('4m0s', delta(m=4).construct_str(final_position='s',max_positions=2, separator='',no_zero_positions=False))
        self.assertEquals('4m', delta(m=4).construct_str(final_position='s',max_positions=2, separator='',no_zero_positions=True))

    def test_arithmetic(self):
        self.assertEquals(delta(15), delta(3) * 5)
        self.assertEquals(15, 5 * delta(3))
        self.assertEquals(delta(3), delta(15)/5)
        self.assertEquals(3, 15 / delta(5))

    def test_unaries(self):
        self.assertEquals(-1, delta(-1).us)
        self.assertEquals(1, abs(delta(1)).us)
        self.assertEquals(1, abs(delta(-1)).us)
        self.assertEquals(-1, (-delta(1)).us)
        self.assertEquals(+1, (+delta(1)).us)


    def test_date_subtraction(self):
        self.assertEquals(24*60**2*10**6, time(2012,1,2) - time(2012,1,1))


    def test_sleep(self):
        t1 = time()
        t2 = time()
        self.assertTrue(t2-t1 < delta(ms=10))
        t1 = time()
        delta(ms=10).sleep()
        t2 = time()
        self.assertTrue(t2-t1 >= delta(ms=10))


########NEW FILE########
__FILENAME__ = test_time
import unittest2 as unittest
from datetime import datetime
import pytz
from .. import time
from ..error import TimeConstructionError

# IMPORTANT -- note to self -- you CANNOT use tzinfo on datetime-- ever! -- just pytz.timezone.localize everything to be safe

JAN_MICROS = 1325376000*1000**2
JAN_MILLIS = JAN_MICROS/1000
JAN_SECS = JAN_MILLIS/1000
JAN_MINS = JAN_SECS/60
JUL_MICROS = 1338508800*1000**2
HOUR_MICROS = 60**2*1000**2

NY_JAN_MICROS = JAN_MICROS + HOUR_MICROS * 5
NY_JUL_MICROS = JUL_MICROS + HOUR_MICROS * 4

LA_JAN_MICROS = JAN_MICROS + HOUR_MICROS * 8
LA_JUL_MICROS = JUL_MICROS + HOUR_MICROS * 7

TZ_UTC = pytz.utc
TZ_NY = pytz.timezone('America/New_York')
TZ_LA = pytz.timezone('America/Los_Angeles')
TZ_AC = pytz.timezone('Africa/Cairo')

class SaneTimeTest(unittest.TestCase):

    def assertSaneTimeEquals(self, st1, st2):
        self.assertInnards(st1.us, st1.tz, st2)

    def setUp(self):
        pass


    def test_microsecond_construction(self):
        self.assertEquals((JAN_MICROS,TZ_UTC), time(JAN_MICROS)._tuple)
        for kwarg in ('us','micros','microseconds','epoch_micros','epoch_microseconds'):
            self.assertEquals((JAN_MICROS,TZ_UTC), time(**{kwarg:JAN_MICROS})._tuple)
            self.assertEquals(JAN_MICROS, getattr(time(**{kwarg:JAN_MICROS}),kwarg))
        for kwarg in ('ms','millis','milliseconds','epoch_millis','epoch_milliseconds'):
            self.assertEquals((JAN_MICROS,TZ_UTC), time(**{kwarg:JAN_MILLIS})._tuple)
            self.assertEquals(JAN_MILLIS, getattr(time(**{kwarg:JAN_MILLIS}),kwarg))
        for kwarg in ('s','secs','seconds','epoch_secs','epoch_seconds'):
            self.assertEquals((JAN_MICROS,TZ_UTC), time(**{kwarg:JAN_SECS})._tuple)
            self.assertEquals(JAN_SECS, getattr(time(**{kwarg:JAN_SECS}),kwarg))
        for kwarg in ('m','mins','minutes','epoch_mins','epoch_minutes'):
            self.assertEquals((JAN_MICROS,TZ_UTC), time(**{kwarg:JAN_MINS})._tuple)
            self.assertEquals(JAN_MINS, getattr(time(**{kwarg:JAN_MINS}),kwarg))

    def test_timezone_construction(self):
        self.assertEquals((JAN_MICROS,TZ_NY), time(JAN_MICROS,'America/New_York')._tuple)
        self.assertEquals((JAN_MICROS,TZ_NY), time(JAN_MICROS,TZ_NY)._tuple)
        self.assertEquals((JAN_MICROS,TZ_NY), time(JAN_MICROS,tz=TZ_NY)._tuple)
        self.assertEquals((JAN_MICROS,TZ_NY), time(s=JAN_SECS,timezone='America/New_York')._tuple)
        self.assertEquals(TZ_UTC, time(tz=TZ_UTC).tz)
        self.assertEquals(TZ_NY, time(tz='America/New_York').tz)

        # nomal string
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00')._tuple)
        self.assertEquals((JUL_MICROS,TZ_UTC), time('2012-06-01 00:00:00')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00','UTC')._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time('2012-01-01 00:00:00','America/New_York')._tuple)

        # Z terminus
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01T00:00:00Z')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01T00:00:00Z','UTC')._tuple)
        with self.assertRaises(TimeConstructionError): time('2012-01-01T00:00:00Z','America/New_York') # conflicting timezones

        # offset terminus
        self.assertEquals((NY_JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00-05:00')._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00-05:00','UTC')._tuple) # conflicting timezones
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time('2012-01-01 00:00:00-05:00','America/New_York')._tuple)

        # tz abbr -- parse can't handle these, so we have to rely on timezones entirely
        self.assertEquals((JUL_MICROS,TZ_UTC), time('2012-06-01 00:00:00 EDT')._tuple)
        self.assertEquals((NY_JUL_MICROS,TZ_NY), time('2012-06-01 00:00:00 EDT','America/New_York')._tuple)
        self.assertEquals((JUL_MICROS,TZ_UTC), time('2012-06-01 00:00:00 PDT')._tuple)
        self.assertEquals((LA_JUL_MICROS,TZ_LA), time('2012-06-01 00:00:00 PDT','America/Los_Angeles')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00 EST','UTC')._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time('2012-01-01 00:00:00 EST','America/New_York')._tuple)

    def test_now_construction(self):
        self.assertTrue(time('2012-04-28') < time() < time('2038-01-01'))  # i'm assuming this library will no longer be needed after 2038 cuz we'll have flying cars by then, finally!
        self.assertTrue(time() < time(tz=TZ_UTC) < time(tz=TZ_NY) < time(tz=TZ_UTC) < time())

    def test_string_parsing(self):
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01T00:00Z')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00+00:00')._tuple)
        self.assertEquals((JAN_MICROS-HOUR_MICROS,TZ_UTC), time('2012-01-01 00:00:00+01:00')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('Sunday, January 1st 2012, at 12:00am')._tuple)

        # tz included
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 +UTC')._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time('2012-01-01 +America/New_York')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00 +UTC')._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time('2012-01-01 00:00:00 +America/New_York')._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time('2012-01-01 00:00:00.000000 +UTC')._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time('2012-01-01 00:00:00.000000 +America/New_York')._tuple)

    def test_bad_construction(self):
        with self.assertRaises(TimeConstructionError): self.assertTrue(JAN_MICROS, time(unknown=None))

    def test_datetime_construction(self):
        self.assertEquals((JAN_MICROS,TZ_UTC), time(datetime(2012,1,1))._tuple)
        self.assertEquals((JAN_MICROS+10**6*60**2,TZ_UTC), time(datetime(2012,1,1,1))._tuple)
        self.assertEquals((JAN_MICROS+10**6*60,TZ_UTC), time(datetime(2012,1,1,0,1))._tuple)
        self.assertEquals((JAN_MICROS+10**6,TZ_UTC), time(datetime(2012,1,1,0,0,1))._tuple)
        self.assertEquals((JAN_MICROS+1,TZ_UTC), time(datetime(2012,1,1,0,0,0,1))._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time(datetime(2012,1,1,0,0,0,0,None))._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time(datetime(2012,1,1,0,0,0,0,TZ_NY))._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time(datetime(2012,1,1,0,0,0,0,TZ_UTC))._tuple)

        # mimic datetime constructor as well
        self.assertEquals((JAN_MICROS,TZ_UTC), time(2012,1,1)._tuple)
        self.assertEquals((JAN_MICROS+10**6*60**2,TZ_UTC), time(2012,1,1,1)._tuple)
        self.assertEquals((JAN_MICROS+10**6*60,TZ_UTC), time(2012,1,1,0,1)._tuple)
        self.assertEquals((JAN_MICROS+10**6,TZ_UTC), time(2012,1,1,0,0,1)._tuple)
        self.assertEquals((JAN_MICROS+1,TZ_UTC), time(2012,1,1,0,0,0,1)._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time(2012,1,1,0,0,0,0,None)._tuple)
        self.assertEquals((NY_JAN_MICROS,TZ_NY), time(2012,1,1,0,0,0,0,TZ_NY)._tuple)
        self.assertEquals((JAN_MICROS,TZ_UTC), time(2012,1,1,0,0,0,0,TZ_UTC)._tuple)

    def test_copy_construction(self):
        self.assertEquals((JAN_MICROS,TZ_UTC), time(time(JAN_MICROS,TZ_UTC))._tuple)
        self.assertEquals((JAN_MICROS,TZ_NY), time(time(JAN_MICROS,TZ_NY))._tuple)

    def test_clone(self):
        self.assertEquals((JAN_MICROS,TZ_UTC), time(JAN_MICROS,TZ_UTC).clone()._tuple)
        self.assertEquals((JAN_MICROS,TZ_NY), time(JAN_MICROS,TZ_NY).clone()._tuple)

    def test_casting(self):
        self.assertEquals(JAN_MICROS, int(time(JAN_MICROS)))
        self.assertEquals(JAN_MICROS, long(time(JAN_MICROS)))
        self.assertEquals('2012-01-01 +UTC', str(time(JAN_MICROS)))
        self.assertEquals('2012-01-01 +UTC', unicode(time(JAN_MICROS)))
        self.assertEquals('2012-01-01 00:00:01 +UTC', unicode(time(JAN_MICROS+10**6)))
        self.assertEquals('2012-01-01 00:00:00.000001 +UTC', unicode(time(JAN_MICROS+1)))
        self.assertEquals(hash(JAN_MICROS), hash(time(JAN_MICROS)))

    def test_equality(self):
        t1 = time(JAN_MICROS, tz='UTC')
        t2 = time(JAN_MICROS, tz='America/New_York')
        t3 = time(JAN_MICROS+1)
        self.assertTrue(t1==t2)
        self.assertTrue(t2==t1)
        self.assertTrue(t1!=t3)
        self.assertTrue(t3!=t1)

        self.assertFalse(t1!=t2)
        self.assertFalse(t2!=t1)
        self.assertFalse(t1==t3)
        self.assertFalse(t3==t1)

        self.assertTrue(t1!=None)
        self.assertFalse(t1==None)
        self.assertTrue(None!=t1)
        self.assertFalse(None==t1)

        self.assertTrue(t1==t1.us)

    def test_comparisons(self):
        t1 = time(JAN_MICROS)
        t2 = time(JAN_MICROS+1)

        self.assertFalse(t1 > t1)
        self.assertTrue(t2 > t1)
        self.assertFalse(t1 > t2)

        self.assertTrue(t1 >= t1)
        self.assertTrue(t2 >= t1)
        self.assertFalse(t1 >= t2)

        self.assertFalse(t1 < t1)
        self.assertFalse(t2 < t1)
        self.assertTrue(t1 < t2)

        self.assertTrue(t1 <= t1)
        self.assertFalse(t2 <= t1)
        self.assertTrue(t1 <= t2)

    def test_transitives(self):
        st = time(tz='America/New_York')
        self.assertEquals(st._tuple, time(st.datetime)._tuple)
        self.assertEquals(st.us, time(int(st)).us)
        self.assertEquals(st._tuple, time(str(st))._tuple)
        self.assertEquals(st._tuple, time(st)._tuple)

    def test_hashability(self):
        t1 = time(JAN_MICROS, tz='UTC')
        t2 = time(JAN_MICROS, tz='America/New_York')
        t3 = time(JAN_MICROS+1)
        s = set([t1,t2,t3])
        self.assertEquals(2, len(s))
        self.assertIn(t1, s)
        self.assertIn(t2, s)
        self.assertIn(t3, s)

    def test_arithmetic(self):
        t1 = time(JAN_MICROS)
        t2 = time(JAN_MICROS+1)

        self.assertEquals(t2.us, (t1+1).us)
        self.assertEquals(t1.us,(t2-1).us)

        self.assertEquals(1, t2 - t1)
        self.assertEquals(-1, t1 - t2)

        self.assertEquals(t1.us,t1*1)
        self.assertEquals(t1.us,t1/1)

    def test_datetime_properties(self):
        self.assertEquals(datetime(2012,1,1,tzinfo=TZ_UTC),time(JAN_MICROS,TZ_UTC).datetime)
        self.assertEquals(datetime(2012,1,1,tzinfo=TZ_NY),time(NY_JAN_MICROS,TZ_NY).datetime)

        self.assertEquals(datetime(2012,1,1),time(JAN_MICROS,TZ_UTC).naive_datetime)
        self.assertEquals(datetime(2012,1,1),time(NY_JAN_MICROS,TZ_NY).naive_datetime)

        self.assertEquals(datetime(2012,1,1,tzinfo=TZ_UTC),time(JAN_MICROS,TZ_UTC).utc_datetime)
        self.assertEquals(datetime(2012,1,1,tzinfo=TZ_UTC),time(JAN_MICROS,TZ_NY).utc_datetime)

        self.assertEquals(datetime(2012,1,1),time(JAN_MICROS,TZ_UTC).utc_naive_datetime)
        self.assertEquals(datetime(2012,1,1),time(JAN_MICROS,TZ_NY).utc_naive_datetime)

        self.assertEquals(datetime(2012,1,1,tzinfo=TZ_NY),time(NY_JAN_MICROS,TZ_UTC).ny_datetime)
        self.assertEquals(datetime(2012,1,1,tzinfo=TZ_NY),time(NY_JAN_MICROS,TZ_NY).ny_datetime)

        self.assertEquals(datetime(2012,1,1),time(NY_JAN_MICROS,TZ_UTC).ny_naive_datetime)
        self.assertEquals(datetime(2012,1,1),time(NY_JAN_MICROS,TZ_NY).ny_naive_datetime)

    def test_switching_timezones(self):
        t1 = time(JAN_MICROS)
        self.assertEquals(pytz.timezone('America/New_York'), t1.with_tz('America/New_York').tz)
        self.assertEquals(t1, time(t1).set_tz('America/New_York'))
        self.assertEquals(t1, t1.with_tz('America/New_York'))
        self.assertNotEquals(t1.tz, time(t1).set_tz('America/New_York').tz)
        self.assertNotEquals(t1.tz, t1.with_tz('America/New_York').tz)
        self.assertEquals(pytz.timezone('America/New_York'), time(t1).set_tz('America/New_York').tz)
        self.assertEquals(pytz.timezone('America/New_York'), t1.with_tz('America/New_York').tz)
        t1_id = id(t1)
        self.assertEquals(t1_id, id(t1.set_tz('America/New_York')))
        self.assertNotEquals(t1_id, id(t1.with_tz('America/New_York')))



########NEW FILE########
__FILENAME__ = test_tztime
import unittest2 as unittest
import pytz
from .. import tztime

JAN_MICROS = 1325376000*1000**2
JAN_MILLIS = JAN_MICROS/1000
JAN_SECS = JAN_MILLIS/1000
JUL_MICROS = 1338508800*1000**2
HOUR_MICROS = 60**2*1000**2

NY_JAN_MICROS = JAN_MICROS + HOUR_MICROS * 5
NY_JUL_MICROS = JUL_MICROS + HOUR_MICROS * 4

TZ_UTC = pytz.utc
TZ_NY = pytz.timezone('America/New_York')
TZ_AC = pytz.timezone('Africa/Cairo')

class SaneTzTimeTest(unittest.TestCase):

    def setUp(self): pass

    def test_clone(self):
        self.assertEquals(tztime, type(tztime(JAN_MICROS,TZ_UTC).clone()))

    def test_equality(self):
        t1 = tztime(JAN_MICROS, tz='UTC')
        t2 = tztime(JAN_MICROS, tz='America/New_York')
        t3 = tztime(JAN_MICROS+1)
        self.assertTrue(t1==t1)
        self.assertTrue(t2==t2)
        self.assertTrue(t3==t3)
        self.assertFalse(t1!=t1)
        self.assertFalse(t2!=t2)
        self.assertFalse(t3!=t3)

        self.assertTrue(t1!=t2)
        self.assertTrue(t2!=t1)
        self.assertTrue(t1!=t3)
        self.assertTrue(t3!=t1)
        self.assertTrue(t2!=t3)
        self.assertTrue(t3!=t2)

        self.assertFalse(t1==t2)
        self.assertFalse(t2==t1)
        self.assertFalse(t1==t3)
        self.assertFalse(t3==t1)
        self.assertFalse(t2==t3)
        self.assertFalse(t3==t2)

        self.assertTrue(t1!=None)
        self.assertFalse(t1==None)
        self.assertTrue(None!=t1)
        self.assertFalse(None==t1)

        self.assertTrue(t1==t1.us)

    def test_comparisons(self):
        t1 = tztime(JAN_MICROS,'UTC')
        t2 = tztime(JAN_MICROS,'America/New_York')
        t3 = tztime(JAN_MICROS+1,'UTC')

        self.assertFalse(t1 > t1)
        self.assertFalse(t2 > t2)
        self.assertFalse(t3 > t3)
        self.assertTrue(t1 > t2)
        self.assertFalse(t2 > t1)
        self.assertFalse(t1 > t3)
        self.assertTrue(t3 > t1)
        self.assertFalse(t2 > t3)
        self.assertTrue(t3 > t2)

        self.assertTrue(t1 >= t1)
        self.assertTrue(t2 >= t2)
        self.assertTrue(t3 >= t3)
        self.assertTrue(t1 >= t2)
        self.assertFalse(t2 >= t1)
        self.assertFalse(t1 >= t3)
        self.assertTrue(t3 >= t1)
        self.assertFalse(t2 >= t3)
        self.assertTrue(t3 >= t2)

        self.assertTrue(t1 <= t1)
        self.assertTrue(t2 <= t2)
        self.assertTrue(t3 <= t3)
        self.assertFalse(t1 <= t2)
        self.assertTrue(t2 <= t1)
        self.assertTrue(t1 <= t3)
        self.assertFalse(t3 <= t1)
        self.assertTrue(t2 <= t3)
        self.assertFalse(t3 <= t2)

        self.assertFalse(t1 < t1)
        self.assertFalse(t2 < t2)
        self.assertFalse(t3 < t3)
        self.assertFalse(t1 < t2)
        self.assertTrue(t2 < t1)
        self.assertTrue(t1 < t3)
        self.assertFalse(t3 < t1)
        self.assertTrue(t2 < t3)
        self.assertFalse(t3 < t2)

    def test_hashability(self):
        t1 = tztime(JAN_MICROS, tz='UTC')
        t2 = tztime(JAN_MICROS, tz='America/New_York')
        t3 = tztime(JAN_MICROS+1)
        s = set([t1,t2,t3])
        self.assertEquals(3, len(s))
        self.assertIn(t1, s)
        self.assertIn(t2, s)
        self.assertIn(t3, s)


########NEW FILE########
