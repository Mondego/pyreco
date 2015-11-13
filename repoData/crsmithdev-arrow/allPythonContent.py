__FILENAME__ = api
# -*- coding: utf-8 -*-
'''
Provides the default implementation of :class:`ArrowFactory <arrow.factory.ArrowFactory>`
methods for use as a module API.

'''

from __future__ import absolute_import

from arrow.factory import ArrowFactory


# internal default factory.
_factory = ArrowFactory()


def get(*args, **kwargs):
    ''' Implements the default :class:`ArrowFactory <arrow.factory.ArrowFactory>`
    ``get`` method.

    '''

    return _factory.get(*args, **kwargs)

def utcnow():
    ''' Implements the default :class:`ArrowFactory <arrow.factory.ArrowFactory>`
    ``utcnow`` method.

    '''

    return _factory.utcnow()


def now(tz=None):
    ''' Implements the default :class:`ArrowFactory <arrow.factory.ArrowFactory>`
    ``now`` method.

    '''

    return _factory.now(tz)


def factory(type):
    ''' Returns an :class:`.ArrowFactory` for the specified :class:`Arrow <arrow.arrow.Arrow>`
    or derived type.

    :param type: the type, :class:`Arrow <arrow.arrow.Arrow>` or derived.

    '''

    return ArrowFactory(type)


__all__ = ['get', 'utcnow', 'now', 'factory', 'iso']


########NEW FILE########
__FILENAME__ = arrow
# -*- coding: utf-8 -*-
'''
Provides the :class:`Arrow <arrow.arrow.Arrow>` class, an enhanced ``datetime``
replacement.

'''

from __future__ import absolute_import

from datetime import datetime, timedelta, tzinfo
from dateutil import tz as dateutil_tz
from dateutil.relativedelta import relativedelta
import calendar
import sys

from arrow import util, locales, parser, formatter


class Arrow(object):
    '''An :class:`Arrow <arrow.arrow.Arrow>` object.

    Implements the ``datetime`` interface, behaving as an aware ``datetime`` while implementing
    additional functionality.

    :param year: the calendar year.
    :param month: the calendar month.
    :param day: the calendar day.
    :param hour: (optional) the hour. Defaults to 0.
    :param minute: (optional) the minute, Defaults to 0.
    :param second: (optional) the second, Defaults to 0.
    :param microsecond: (optional) the microsecond. Defaults 0.
    :param tzinfo: (optional) the ``tzinfo`` object.  Defaults to ``None``.

    If tzinfo is None, it is assumed to be UTC on creation.

    Usage::

        >>> import arrow
        >>> arrow.Arrow(2013, 5, 5, 12, 30, 45)
        <Arrow [2013-05-05T12:30:45+00:00]>

    '''

    resolution = datetime.resolution

    _ATTRS = ['year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond']
    _ATTRS_PLURAL = ['{0}s'.format(a) for a in _ATTRS]

    def __init__(self, year, month, day, hour=0, minute=0, second=0, microsecond=0,
                 tzinfo=None):

        if util.isstr(tzinfo):
            tzinfo = parser.TzinfoParser.parse(tzinfo)
        tzinfo = tzinfo or dateutil_tz.tzutc()

        self._datetime = datetime(year, month, day, hour, minute, second,
            microsecond, tzinfo)


    # factories: single object, both original and from datetime.

    @classmethod
    def now(cls, tzinfo=None):
        '''Constructs an :class:`Arrow <arrow.arrow.Arrow>` object, representing "now".

        :param tzinfo: (optional) a ``tzinfo`` object. Defaults to local time.

        '''

        utc = datetime.utcnow().replace(tzinfo=dateutil_tz.tzutc())
        dt = utc.astimezone(dateutil_tz.tzlocal() if tzinfo is None else tzinfo)

        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, dt.tzinfo)

    @classmethod
    def utcnow(cls):
        ''' Constructs an :class:`Arrow <arrow.arrow.Arrow>` object, representing "now" in UTC
        time.

        '''

        dt = datetime.utcnow()

        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, dateutil_tz.tzutc())

    @classmethod
    def fromtimestamp(cls, timestamp, tzinfo=None):
        ''' Constructs an :class:`Arrow <arrow.arrow.Arrow>` object from a timestamp.

        :param timestamp: an ``int`` or ``float`` timestamp, or a ``str`` that converts to either.
        :param tzinfo: (optional) a ``tzinfo`` object.  Defaults to local time.

        '''

        tzinfo = tzinfo or dateutil_tz.tzlocal()
        timestamp = cls._get_timestamp_from_input(timestamp)
        dt = datetime.fromtimestamp(timestamp, tzinfo)

        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo)

    @classmethod
    def utcfromtimestamp(cls, timestamp):
        '''Constructs an :class:`Arrow <arrow.arrow.Arrow>` object from a timestamp, in UTC time.

        :param timestamp: an ``int`` or ``float`` timestamp, or a ``str`` that converts to either.

        '''

        timestamp = cls._get_timestamp_from_input(timestamp)
        dt = datetime.utcfromtimestamp(timestamp)

        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, dateutil_tz.tzutc())

    @classmethod
    def fromdatetime(cls, dt, tzinfo=None):
        ''' Constructs an :class:`Arrow <arrow.arrow.Arrow>` object from a ``datetime`` and optional
        ``tzinfo`` object.

        :param dt: the ``datetime``
        :param tzinfo: (optional) a ``tzinfo`` object.  Defaults to UTC.

        '''

        tzinfo = tzinfo or dt.tzinfo or dateutil_tz.tzutc()

        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo)

    @classmethod
    def fromdate(cls, date, tzinfo=None):
        ''' Constructs an :class:`Arrow <arrow.arrow.Arrow>` object from a ``date`` and optional
        ``tzinfo`` object.  Time values are set to 0.

        :param date: the ``date``
        :param tzinfo: (optional) a ``tzinfo`` object.  Defaults to UTC.
        '''

        tzinfo = tzinfo or dateutil_tz.tzutc()

        return cls(date.year, date.month, date.day, tzinfo=tzinfo)

    @classmethod
    def strptime(cls, date_str, fmt, tzinfo=None):
        ''' Constructs an :class:`Arrow <arrow.arrow.Arrow>` object from a date string and format,
        in the style of ``datetime.strptime``.

        :param date_str: the date string.
        :param fmt: the format string.
        :param tzinfo: (optional) an optional ``tzinfo``
        '''

        dt = datetime.strptime(date_str, fmt)
        tzinfo = tzinfo or dt.tzinfo

        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo)


    # factories: ranges and spans

    @classmethod
    def range(cls, frame, start, end=None, tz=None, limit=None):
        ''' Returns an array of :class:`Arrow <arrow.arrow.Arrow>` objects, representing
        an iteration of time between two inputs.

        :param frame: the timeframe.  Can be any ``datetime`` property (day, hour, minute...).
        :param start: A datetime expression, the start of the range.
        :param end: (optional) A datetime expression, the end of the range.
        :param tz: (optional) A timezone expression.  Defaults to UTC.
        :param limit: (optional) A maximum number of tuples to return.

        **NOTE**: the **end** or **limit** must be provided.  Call with **end** alone to
        return the entire range, with **limit** alone to return a maximum # of results from the
        start, and with both to cap a range at a maximum # of results.

        Recognized datetime expressions:

            - An :class:`Arrow <arrow.arrow.Arrow>` object.
            - A ``datetime`` object.

        Recognized timezone expressions:

            - A ``tzinfo`` object.
            - A ``str`` describing a timezone, similar to 'US/Pacific', or 'Europe/Berlin'.
            - A ``str`` in ISO-8601 style, as in '+07:00'.
            - A ``str``, one of the following:  'local', 'utc', 'UTC'.

        Usage:

            >>> start = datetime(2013, 5, 5, 12, 30)
            >>> end = datetime(2013, 5, 5, 17, 15)
            >>> for r in arrow.Arrow.range('hour', start, end):
            ...     print repr(r)
            ...
            <Arrow [2013-05-05T12:30:00+00:00]>
            <Arrow [2013-05-05T13:30:00+00:00]>
            <Arrow [2013-05-05T14:30:00+00:00]>
            <Arrow [2013-05-05T15:30:00+00:00]>
            <Arrow [2013-05-05T16:30:00+00:00]>

        '''

        frame_relative = cls._get_frames(frame)[1]
        tzinfo = cls._get_tzinfo(start.tzinfo if tz is None else tz)

        start = cls._get_datetime(start).replace(tzinfo=tzinfo)
        end, limit = cls._get_iteration_params(end, limit)
        end = cls._get_datetime(end).replace(tzinfo=tzinfo)

        current = cls.fromdatetime(start)
        results = []

        while current <= end and len(results) < limit:
            results.append(current)

            values = [getattr(current, f) for f in cls._ATTRS]
            current = cls(*values, tzinfo=tzinfo) + relativedelta(**{frame_relative: 1})

        return results


    @classmethod
    def span_range(cls, frame, start, end, tz=None, limit=None):
        ''' Returns an array of tuples, each :class:`Arrow <arrow.arrow.Arrow>` objects,
        representing a series of timespans between two inputs.

        :param frame: the timeframe.  Can be any ``datetime`` property (day, hour, minute...).
        :param start: A datetime expression, the start of the range.
        :param end: (optional) A datetime expression, the end of the range.
        :param tz: (optional) A timezone expression.  Defaults to UTC.
        :param limit: (optional) A maximum number of tuples to return.

        **NOTE**: the **end** or **limit** must be provided.  Call with **end** alone to
        return the entire range, with **limit** alone to return a maximum # of results from the
        start, and with both to cap a range at a maximum # of results.

        Recognized datetime expressions:

            - An :class:`Arrow <arrow.arrow.Arrow>` object.
            - A ``datetime`` object.

        Recognized timezone expressions:

            - A ``tzinfo`` object.
            - A ``str`` describing a timezone, similar to 'US/Pacific', or 'Europe/Berlin'.
            - A ``str`` in ISO-8601 style, as in '+07:00'.
            - A ``str``, one of the following:  'local', 'utc', 'UTC'.

        Usage:

            >>> start = datetime(2013, 5, 5, 12, 30)
            >>> end = datetime(2013, 5, 5, 17, 15)
            >>> for r in arrow.Arrow.span_range('hour', start, end):
            ...     print r
            ...
            (<Arrow [2013-05-05T12:00:00+00:00]>, <Arrow [2013-05-05T12:59:59.999999+00:00]>)
            (<Arrow [2013-05-05T13:00:00+00:00]>, <Arrow [2013-05-05T13:59:59.999999+00:00]>)
            (<Arrow [2013-05-05T14:00:00+00:00]>, <Arrow [2013-05-05T14:59:59.999999+00:00]>)
            (<Arrow [2013-05-05T15:00:00+00:00]>, <Arrow [2013-05-05T15:59:59.999999+00:00]>)
            (<Arrow [2013-05-05T16:00:00+00:00]>, <Arrow [2013-05-05T16:59:59.999999+00:00]>)

        '''

        _range = cls.range(frame, start, end, tz, limit)
        return [r.span(frame) for r in _range]


    # representations

    def __repr__(self):

        dt = self._datetime
        attrs = ', '.join([str(i) for i in [dt.year, dt.month, dt.day, dt.hour, dt.minute,
            dt.second, dt.microsecond]])

        return '<{0} [{1}]>'.format(self.__class__.__name__, self.__str__())

    def __str__(self):
        return self._datetime.isoformat()

    def __format__(self, formatstr):

        if len(formatstr) > 0:
            return self.format(formatstr)

        return str(self)

    def __hash__(self):
        return self._datetime.__hash__()


    # attributes & properties

    def __getattr__(self, name):

        if name == 'week':
            return self.isocalendar()[1]

        if not name.startswith('_'):
            value = getattr(self._datetime, name, None)

            if value is not None:
                return value

        return object.__getattribute__(self, name)

    @property
    def tzinfo(self):
        ''' Gets the ``tzinfo`` of the :class:`Arrow <arrow.arrow.Arrow>` object. '''

        return self._datetime.tzinfo

    @tzinfo.setter
    def tzinfo(self, tzinfo):
        ''' Sets the ``tzinfo`` of the :class:`Arrow <arrow.arrow.Arrow>` object. '''

        self._datetime = self._datetime.replace(tzinfo=tzinfo)

    @property
    def datetime(self):
        ''' Returns a datetime representation of the :class:`Arrow <arrow.arrow.Arrow>` object. '''

        return self._datetime

    @property
    def naive(self):
        ''' Returns a naive datetime representation of the :class:`Arrow <arrow.arrow.Arrow>` object. '''

        return self._datetime.replace(tzinfo=None)

    @property
    def timestamp(self):
        ''' Returns a timestamp representation of the :class:`Arrow <arrow.arrow.Arrow>` object. '''

        return calendar.timegm(self._datetime.utctimetuple())

    @property
    def float_timestamp(self):
        ''' Returns a floating-point representation of the :class:`Arrow <arrow.arrow.Arrow>` object. '''

        return self.timestamp + float(self.microsecond) / 1000000


    # mutation and duplication.

    def clone(self):
        ''' Returns a new :class:`Arrow <arrow.arrow.Arrow>` object, cloned from the current one.

        Usage:

            >>> arw = arrow.utcnow()
            >>> cloned = arw.clone()

        '''

        return self.fromdatetime(self._datetime)

    def replace(self, **kwargs):
        ''' Returns a new :class:`Arrow <arrow.arrow.Arrow>` object with attributes updated
        according to inputs.

        Use single property names to set their value absolutely:

        >>> import arrow
        >>> arw = arrow.utcnow()
        >>> arw
        <Arrow [2013-05-11T22:27:34.787885+00:00]>
        >>> arw.replace(year=2014, month=6)
        <Arrow [2014-06-11T22:27:34.787885+00:00]>

        Use plural property names to shift their current value relatively:

        >>> arw.replace(years=1, months=-1)
        <Arrow [2014-04-11T22:27:34.787885+00:00]>

        You can also provide a tzimezone expression can also be replaced:

        >>> arw.replace(tzinfo=tz.tzlocal())
        <Arrow [2013-05-11T22:27:34.787885-07:00]>

        Recognized timezone expressions:

            - A ``tzinfo`` object.
            - A ``str`` describing a timezone, similar to 'US/Pacific', or 'Europe/Berlin'.
            - A ``str`` in ISO-8601 style, as in '+07:00'.
            - A ``str``, one of the following:  'local', 'utc', 'UTC'.

        '''

        absolute_kwargs = {}
        relative_kwargs = {}

        for key, value in kwargs.items():

            if key in self._ATTRS:
                absolute_kwargs[key] = value
            elif key in self._ATTRS_PLURAL or key == 'weeks':
                relative_kwargs[key] = value
            elif key == 'week':
                raise AttributeError('setting absolute week is not supported')
            elif key !='tzinfo':
                raise AttributeError()

        current = self._datetime.replace(**absolute_kwargs)
        current += relativedelta(**relative_kwargs)

        tzinfo = kwargs.get('tzinfo')

        if tzinfo is not None:
            tzinfo = self._get_tzinfo(tzinfo)
            current = current.replace(tzinfo=tzinfo)

        return self.fromdatetime(current)

    def to(self, tz):
        ''' Returns a new :class:`Arrow <arrow.arrow.Arrow>` object, converted to the target
        timezone.

        :param tz: an expression representing a timezone.

        Recognized timezone expressions:

            - A ``tzinfo`` object.
            - A ``str`` describing a timezone, similar to 'US/Pacific', or 'Europe/Berlin'.
            - A ``str`` in ISO-8601 style, as in '+07:00'.
            - A ``str``, one of the following:  'local', 'utc', 'UTC'.

        Usage::

            >>> utc = arrow.utcnow()
            >>> utc
            <Arrow [2013-05-09T03:49:12.311072+00:00]>

            >>> utc.to('US/Pacific')
            <Arrow [2013-05-08T20:49:12.311072-07:00]>

            >>> utc.to(tz.tzlocal())
            <Arrow [2013-05-08T20:49:12.311072-07:00]>

            >>> utc.to('-07:00')
            <Arrow [2013-05-08T20:49:12.311072-07:00]>

            >>> utc.to('local')
            <Arrow [2013-05-08T20:49:12.311072-07:00]>

            >>> utc.to('local').to('utc')
            <Arrow [2013-05-09T03:49:12.311072+00:00]>

        '''

        if not isinstance(tz, tzinfo):
            tz = parser.TzinfoParser.parse(tz)

        dt = self._datetime.astimezone(tz)

        return self.__class__(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tz)

    def span(self, frame):
        ''' Returns two new :class:`Arrow <arrow.arrow.Arrow>` objects, representing the timespan
        of the :class:`Arrow <arrow.arrow.Arrow>` object in a given timeframe.

        :param frame: the timeframe.  Can be any ``datetime`` property (day, hour, minute...).

        Usage::

            >>> arrow.utcnow()
            <Arrow [2013-05-09T03:32:36.186203+00:00]>

            >>> arrow.utcnow().span('hour')
            (<Arrow [2013-05-09T03:00:00+00:00]>, <Arrow [2013-05-09T03:59:59.999999+00:00]>)

            >>> arrow.utcnow().span('day')
            (<Arrow [2013-05-09T00:00:00+00:00]>, <Arrow [2013-05-09T23:59:59.999999+00:00]>)

        '''

        frame_absolute, frame_relative = self._get_frames(frame)

        index = self._ATTRS.index('day' if frame_absolute == 'week' else frame_absolute)
        frames = self._ATTRS[:index + 1]

        values = [getattr(self, f) for f in frames]

        for i in range(3 - len(values)):
            values.append(1)

        floor = self.__class__(*values, tzinfo=self.tzinfo)

        if frame_absolute == 'week':
            floor = floor + relativedelta(days=-(self.isoweekday() - 1))

        ceil = floor + relativedelta(**{frame_relative: 1}) + relativedelta(microseconds=-1)

        return floor, ceil

    def floor(self, frame):
        ''' Returns a new :class:`Arrow <arrow.arrow.Arrow>` object, representing the "floor"
        of the timespan of the :class:`Arrow <arrow.arrow.Arrow>` object in a given timeframe.
        Equivalent to the first element in the 2-tuple returned by
        :func:`span <arrow.arrow.Arrow.span>`.

        :param frame: the timeframe.  Can be any ``datetime`` property (day, hour, minute...).

        Usage::

            >>> arrow.utcnow().ceil('hour')
            <Arrow [2013-05-09T03:00:00+00:00]>
        '''

        return self.span(frame)[0]

    def ceil(self, frame):
        ''' Returns a new :class:`Arrow <arrow.arrow.Arrow>` object, representing the "ceiling"
        of the timespan of the :class:`Arrow <arrow.arrow.Arrow>` object in a given timeframe.
        Equivalent to the second element in the 2-tuple returned by
        :func:`span <arrow.arrow.Arrow.span>`.

        :param frame: the timeframe.  Can be any ``datetime`` property (day, hour, minute...).

        Usage::

            >>> arrow.utcnow().ceil('hour')
            <Arrow [2013-05-09T03:59:59.999999+00:00]>
        '''

        return self.span(frame)[1]


    # string output and formatting.

    def format(self, fmt, locale='en_us'):
        ''' Returns a string representation of the :class:`Arrow <arrow.arrow.Arrow>` object,
        formatted according to a format string.

        :param fmt: the format string.

        Usage::

            >>> arrow.utcnow().format('YYYY-MM-DD HH:mm:ss ZZ')
            '2013-05-09 03:56:47 -00:00'

            >>> arrow.utcnow().format('X')
            '1368071882'

            >>> arrow.utcnow().format('MMMM DD, YYYY')
            'May 09, 2013'
        '''

        return formatter.DateTimeFormatter(locale).format(self._datetime, fmt)


    def humanize(self, other=None, locale='en_us'):
        ''' Returns a localized, humanized representation of a relative difference in time.

        :param other: (optional) an :class:`Arrow <arrow.arrow.Arrow>` or ``datetime`` object.
            Defaults to now in the current :class:`Arrow <arrow.arrow.Arrow>` objet's timezone.
        :param locale: (optional) a ``str`` specifying a locale.  Defaults to 'en_us'.

        Usage::

            >>> earlier = arrow.utcnow().replace(hours=-2)
            >>> earlier.humanize()
            '2 hours ago'

            >>> later = later = earlier.replace(hours=4)
            >>> later.humanize(earlier)
            'in 4 hours'

        '''

        locale = locales.get_locale(locale)

        if other is None:
            utc = datetime.utcnow().replace(tzinfo=dateutil_tz.tzutc())
            dt = utc.astimezone(self._datetime.tzinfo)

        elif isinstance(other, Arrow):
            dt = other._datetime

        elif isinstance(other, datetime):
            if other.tzinfo is None:
                dt = other.replace(tzinfo=self._datetime.tzinfo)
            else:
                dt = other.astimezone(self._datetime.tzinfo)

        else:
            raise TypeError()

        delta = int(util.total_seconds(self._datetime - dt))
        sign = -1 if delta < 0 else 1
        diff = abs(delta)
        delta = diff

        if diff < 10:
            return locale.describe('now')

        if diff < 45:
            return locale.describe('seconds', sign)

        elif diff < 90:
            return locale.describe('minute', sign)
        elif diff < 2700:
            minutes = sign * int(max(delta / 60, 2))
            return locale.describe('minutes', minutes)

        elif diff < 5400:
            return locale.describe('hour', sign)
        elif diff < 79200:
            hours = sign * int(max(delta / 3600, 2))
            return locale.describe('hours', hours)

        elif diff < 129600:
            return locale.describe('day', sign)
        elif diff < 2160000:
            days = sign * int(max(delta / 86400, 2))
            return locale.describe('days', days)

        elif diff < 3888000:
            return locale.describe('month', sign)
        elif diff < 29808000:
            self_months = self._datetime.year * 12 + self._datetime.month
            other_months = dt.year * 12 + dt.month
            months = sign * abs(other_months - self_months)

            return locale.describe('months', months)

        elif diff < 47260800:
            return locale.describe('year', sign)
        else:
            years = sign * int(max(delta / 31536000, 2))
            return locale.describe('years', years)


    # math

    def __add__(self, other):

        if isinstance(other, (timedelta, relativedelta)):
            return self.fromdatetime(self._datetime + other, self._datetime.tzinfo)

        raise NotImplementedError()

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):

        if isinstance(other, timedelta):
            return self.fromdatetime(self._datetime - other, self._datetime.tzinfo)

        elif isinstance(other, datetime):
            return self._datetime - other

        elif isinstance(other, Arrow):
            return self._datetime - other._datetime

        raise NotImplementedError()

    def __rsub__(self, other):
        return self.__sub__(other)


    # comparisons

    def __eq__(self, other):

        if not isinstance(other, (Arrow, datetime)):
            return False

        other = self._get_datetime(other)

        return self._datetime == self._get_datetime(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):

        if not isinstance(other, (Arrow, datetime)):
            return False

        return self._datetime > self._get_datetime(other)

    def __ge__(self, other):

        if not isinstance(other, (Arrow, datetime)):
            return False

        return self._datetime >= self._get_datetime(other)

    def __lt__(self, other):

        if not isinstance(other, (Arrow, datetime)):
            return False

        return self._datetime < self._get_datetime(other)

    def __le__(self, other):

        if not isinstance(other, (Arrow, datetime)):
            return False

        return self._datetime <= self._get_datetime(other)


    # datetime methods

    def date(self):
        ''' Returns a ``date`` object with the same year, month and day. '''

        return self._datetime.date()

    def time(self):
        ''' Returns a ``time`` object with the same hour, minute, second, microsecond. '''

        return self._datetime.time()

    def timetz(self):
        ''' Returns a ``time`` object with the same hour, minute, second, microsecond and tzinfo. '''

        return self._datetime.timetz()

    def astimezone(self, tz):
        ''' Returns a ``datetime`` object, adjusted to the specified tzinfo.

        :param tz: a ``tzinfo`` object.

        '''

        return self._datetime.astimezone(tz)

    def utcoffset(self):
        ''' Returns a ``timedelta`` object representing the whole number of minutes difference from UTC time. '''

        return self._datetime.utcoffset()

    def dst(self):
        ''' Returns the daylight savings time adjustment. '''
        return self._datetime.dst()

    def timetuple(self):
        ''' Returns a ``time.struct_time``, in the current timezone. '''

        return self._datetime.timetuple()

    def utctimetuple(self):
        ''' Returns a ``time.struct_time``, in UTC time. '''

        return self._datetime.utctimetuple()

    def toordinal(self):
        ''' Returns the proleptic Gregorian ordinal of the date. '''

        return self._datetime.toordinal()

    def weekday(self):
        ''' Returns the day of the week as an integer (0-6). '''

        return self._datetime.weekday()

    def isoweekday(self):
        ''' Returns the ISO day of the week as an integer (1-7). '''

        return self._datetime.isoweekday()

    def isocalendar(self):
        ''' Returns a 3-tuple, (ISO year, ISO week number, ISO weekday). '''

        return self._datetime.isocalendar()

    def isoformat(self, sep='T'):
        '''Returns an ISO 8601 formatted representation of the date and time. '''

        return self._datetime.isoformat(sep)

    def ctime(self):
        ''' Returns a ctime formatted representation of the date and time. '''

        return self._datetime.ctime()

    def strftime(self, format):
        ''' Formats in the style of ``datetime.strptime``.

        :param format: the format string.

        '''

        return self._datetime.strftime(format)


    # internal tools.

    @classmethod
    def _get_tzinfo(cls, tz_expr):

        if tz_expr is None:
            return dateutil_tz.tzutc()
        if isinstance(tz_expr, tzinfo):
            return tz_expr
        else:
            try:
                return parser.TzinfoParser.parse(tz_expr)
            except parser.ParserError:
                raise ValueError('\'{0}\' not recognized as a timezone')

    @classmethod
    def _get_datetime(cls, expr):

        if isinstance(expr, Arrow):
            return expr.datetime

        if isinstance(expr, datetime):
            return expr

        try:
            expr = float(expr)
            return cls.utcfromtimestamp(expr).datetime
        except:
            raise ValueError('\'{0}\' not recognized as a timestamp or datetime')

    @classmethod
    def _get_frames(cls, name):

        if name in cls._ATTRS:
            return name, '{0}s'.format(name)

        elif name in ['week', 'weeks']:
            return 'week', 'weeks'

        raise AttributeError()

    @classmethod
    def _get_iteration_params(cls, end, limit):

        if end is None:

            if limit is None:
                raise Exception('one of \'end\' or \'limit\' is required')

            return cls.max, limit

        else:
            return end, sys.maxsize

    @classmethod
    def _get_timestamp_from_input(cls, timestamp):

        try:
            return float(timestamp)
        except:
            raise ValueError('cannot parse \'{0}\' as a timestamp'.format(timestamp))

Arrow.min = Arrow.fromdatetime(datetime.min)
Arrow.max = Arrow.fromdatetime(datetime.max)

########NEW FILE########
__FILENAME__ = factory
# -*- coding: utf-8 -*-
'''
Implements the :class:`ArrowFactory <arrow.factory.ArrowFactory>` class,
providing factory methods for common :class:`Arrow <arrow.arrow.Arrow>`
contruction scenarios.

'''

from __future__ import absolute_import

from arrow.arrow import Arrow
from arrow import parser
from arrow.util import isstr

from datetime import datetime, tzinfo
from dateutil import tz as dateutil_tz


class ArrowFactory(object):
    ''' A factory for generating :class:`Arrow <arrow.arrow.Arrow>` objects.

    :param type: (optional) the :class:`Arrow <arrow.arrow.Arrow>`-based class to construct from.
        Defaults to :class:`Arrow <arrow.arrow.Arrow>`.

    '''

    def __init__(self, type=Arrow):
        self.type = type

    def get(self, *args, **kwargs):
        ''' Returns an :class:`Arrow <arrow.arrow.Arrow>` object based on flexible inputs.

        Usage::

            >>> import arrow

        **No inputs** to get current UTC time::

            >>> arrow.get()
            <Arrow [2013-05-08T05:51:43.316458+00:00]>

        **None** to also get current UTC time::

            >>> arrow.get(None)
            <Arrow [2013-05-08T05:51:43.316458+00:00]>

        **One** :class:`Arrow <arrow.arrow.Arrow>` object, to get a copy.

            >>> arw = arrow.utcnow()
            >>> arrow.get(arw)
            <Arrow [2013-10-23T15:21:54.354846+00:00]>

        **One** ``str``, ``float``, or ``int``, convertible to a floating-point timestamp, to get that timestamp in UTC::

            >>> arrow.get(1367992474.293378)
            <Arrow [2013-05-08T05:54:34.293378+00:00]>

            >>> arrow.get(1367992474)
            <Arrow [2013-05-08T05:54:34+00:00]>

            >>> arrow.get('1367992474.293378')
            <Arrow [2013-05-08T05:54:34.293378+00:00]>

            >>> arrow.get('1367992474')
            <Arrow [2013-05-08T05:54:34+00:00]>

        **One** ISO-8601-formatted ``str``, to parse it::

            >>> arrow.get('2013-09-29T01:26:43.830580')
            <Arrow [2013-09-29T01:26:43.830580+00:00]>

        **One** ``tzinfo``, to get the current time in that timezone::

            >>> arrow.get(tz.tzlocal())
            <Arrow [2013-05-07T22:57:28.484717-07:00]>

        **One** naive ``datetime``, to get that datetime in UTC::

            >>> arrow.get(datetime(2013, 5, 5))
            <Arrow [2013-05-05T00:00:00+00:00]>

        **One** aware ``datetime``, to get that datetime::

            >>> arrow.get(datetime(2013, 5, 5, tzinfo=tz.tzlocal()))
            <Arrow [2013-05-05T00:00:00-07:00]>

        **Two** arguments, a naive or aware ``datetime``, and a timezone expression (as above)::

            >>> arrow.get(datetime(2013, 5, 5), 'US/Pacific')
            <Arrow [2013-05-05T00:00:00-07:00]>

        **Two** arguments, both ``str``, to parse the first according to the format of the second::

            >>> arrow.get('2013-05-05 12:30:45', 'YYYY-MM-DD HH:mm:ss')
            <Arrow [2013-05-05T12:30:45+00:00]>

        **Two** arguments, first a ``str`` to parse and second a ``list`` of formats to try::

            >>> arrow.get('2013-05-05 12:30:45', ['MM/DD/YYYY', 'YYYY-MM-DD HH:mm:ss'])
            <Arrow [2013-05-05T12:30:45+00:00]>

        **Three or more** arguments, as for the constructor of a ``datetime``::

            >>> arrow.get(2013, 5, 5, 12, 30, 45)
            <Arrow [2013-05-05T12:30:45+00:00]>
        '''

        arg_count = len(args)
        locale = kwargs.get('locale', 'en_us')

        # () -> now, @ utc.
        if arg_count == 0:
            return self.type.utcnow()

        if arg_count == 1:
            arg = args[0]

            # (None) -> now, @ utc.
            if arg is None:
                return self.type.utcnow()

            # try (int, float, str(int), str(float)) -> utc, from timestamp.
            try:
                return self.type.utcfromtimestamp(arg)
            except:
                pass

            # (Arrow) -> from the object's datetime.
            if isinstance(arg, Arrow):
                return self.type.fromdatetime(arg.datetime)

            # (datetime) -> from datetime.
            if isinstance(arg, datetime):
                return self.type.fromdatetime(arg)

            # (tzinfo) -> now, @ tzinfo.
            elif isinstance(arg, tzinfo):
                return self.type.now(arg)

            # (str) -> now, @ tzinfo.
            elif isstr(arg):
                dt = parser.DateTimeParser(locale).parse_iso(arg)
                return self.type.fromdatetime(dt)

            else:
                raise TypeError('Can\'t parse single argument type of \'{0}\''.format(type(arg)))

        elif arg_count == 2:

            arg_1, arg_2 = args[0], args[1]

            if isinstance(arg_1, datetime):

                # (datetime, tzinfo) -> fromdatetime @ tzinfo/string.
                if isinstance(arg_2, tzinfo) or isstr(arg_2):
                    return self.type.fromdatetime(arg_1, arg_2)
                else:
                    raise TypeError('Can\'t parse two arguments of types \'datetime\', \'{0}\''.format(
                        type(arg_2)))

            # (str, format) -> parse.
            elif isstr(arg_1) and (isstr(arg_2) or isinstance(arg_2, list)):
                dt = parser.DateTimeParser(locale).parse(args[0], args[1])
                return self.type.fromdatetime(dt)

            else:
                raise TypeError('Can\'t parse two arguments of types \'{0}\', \'{1}\''.format(
                    type(arg_1), type(arg_2)))

        # 3+ args -> datetime-like via constructor.
        else:
            return self.type(*args, **kwargs)

    def utcnow(self):
        '''Returns an :class:`Arrow <arrow.arrow.Arrow>` object, representing "now" in UTC time.

        Usage::

            >>> import arrow
            >>> arrow.utcnow()
            <Arrow [2013-05-08T05:19:07.018993+00:00]>
        '''

        return self.type.utcnow()

    def now(self, tz=None):
        '''Returns an :class:`Arrow <arrow.arrow.Arrow>` object, representing "now".

        :param tz: (optional) An expression representing a timezone.  Defaults to local time.

        Recognized timezone expressions:

            - A ``tzinfo`` object.
            - A ``str`` describing a timezone, similar to 'US/Pacific', or 'Europe/Berlin'.
            - A ``str`` in ISO-8601 style, as in '+07:00'.
            - A ``str``, one of the following:  'local', 'utc', 'UTC'.

        Usage::

            >>> import arrow
            >>> arrow.now()
            <Arrow [2013-05-07T22:19:11.363410-07:00]>

            >>> arrow.now('US/Pacific')
            <Arrow [2013-05-07T22:19:15.251821-07:00]>

            >>> arrow.now('+02:00')
            <Arrow [2013-05-08T07:19:25.618646+02:00]>

            >>> arrow.now('local')
            <Arrow [2013-05-07T22:19:39.130059-07:00]>
        '''

        if tz is None:
            tz = dateutil_tz.tzlocal()
        elif not isinstance(tz, tzinfo):
            tz = parser.TzinfoParser.parse(tz)

        return self.type.now(tz)

########NEW FILE########
__FILENAME__ = formatter
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import calendar
import re
from dateutil import tz as dateutil_tz
from arrow import util, locales


class DateTimeFormatter(object):

    _FORMAT_RE = re.compile('(YYY?Y?|MM?M?M?|DD?D?D?|d?dd?d?|HH?|hh?|mm?|ss?|SS?S?S?S?S?|ZZ?|a|A|X)')

    def __init__(self, locale='en_us'):

        self.locale = locales.get_locale(locale)

    def format(cls, dt, fmt):

        return cls._FORMAT_RE.sub(lambda m: cls._format_token(dt, m.group(0)), fmt)

    def _format_token(self, dt, token):

        if token == 'YYYY':
            return '{0:04d}'.format(dt.year)
        if token == 'YY':
            return '{0:04d}'.format(dt.year)[2:]

        if token == 'MMMM':
            return self.locale.month_name(dt.month)
        if token == 'MMM':
            return self.locale.month_abbreviation(dt.month)
        if token == 'MM':
            return '{0:02d}'.format(dt.month)
        if token == 'M':
            return str(dt.month)

        if token == 'DDDD':
            return '{0:03d}'.format(dt.timetuple().tm_yday)
        if token == 'DDD':
            return str(dt.timetuple().tm_yday)
        if token == 'DD':
            return '{0:02d}'.format(dt.day)
        if token == 'D':
            return str(dt.day)

        if token == 'dddd':
            return self.locale.day_name(dt.isoweekday())
        if token == 'ddd':
            return self.locale.day_abbreviation(dt.isoweekday())
        if token == 'd':
            return str(dt.isoweekday())

        if token == 'HH':
            return '{0:02d}'.format(dt.hour)
        if token == 'H':
            return str(dt.hour)
        if token == 'hh':
            return '{0:02d}'.format(dt.hour if 0 < dt.hour < 13 else abs(dt.hour - 12))
        if token == 'h':
            return str(dt.hour if 0 < dt.hour < 13 else abs(dt.hour - 12))

        if token == 'mm':
            return '{0:02d}'.format(dt.minute)
        if token == 'm':
            return str(dt.minute)

        if token == 'ss':
            return '{0:02d}'.format(dt.second)
        if token == 's':
            return str(dt.second)

        if token == 'SSSSSS':
            return str(dt.microsecond)
        if token == 'SSSSS':
            return str(int(dt.microsecond / 10))
        if token == 'SSSS':
            return str(int(dt.microsecond / 100))
        if token == 'SSS':
            return str(int(dt.microsecond / 1000))
        if token == 'SS':
            return str(int(dt.microsecond / 10000))
        if token == 'S':
            return str(int(dt.microsecond / 100000))

        if token == 'X':
            return str(calendar.timegm(dt.utctimetuple()))

        if token in ['ZZ', 'Z']:
            separator = ':' if token == 'ZZ' else ''
            tz = dateutil_tz.tzutc() if dt.tzinfo is None else dt.tzinfo
            total_minutes = int(util.total_seconds(tz.utcoffset(dt)) / 60)

            sign = '+' if total_minutes > 0 else '-'
            total_minutes = abs(total_minutes)
            hour, minute = divmod(total_minutes, 60)

            return '{0}{1:02d}{2}{3:02d}'.format(sign, hour, separator, minute)

        if token in ('a', 'A'):
            return self.locale.meridian(dt.hour, token)


########NEW FILE########
__FILENAME__ = locales
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import calendar
import inspect
import sys


def get_locale(name):
    '''Returns an appropriate :class:`Locale <locale.Locale>` corresponding
    to an inpute locale name.

    :param name: the name of the locale.

    '''

    locale_cls = _locales.get(name.lower())

    if locale_cls is None:
        raise ValueError('Unsupported locale \'{0}\''.format(name))

    return locale_cls()


# base locale type.

class Locale(object):
    ''' Represents locale-specific data and functionality. '''

    names = []

    timeframes = {
        'now': '',
        'seconds': '',
        'minute': '',
        'minutes': '',
        'hour': '',
        'hours': '',
        'day': '',
        'days': '',
        'month': '',
        'months': '',
        'year': '',
        'years': '',
    }

    meridians = {
        'am': '',
        'pm': '',
        'AM': '',
        'PM': '',
    }

    past = None
    future = None

    month_names = []
    month_abbreviations = []

    day_names = []
    day_abbreviations = []

    def __init__(self):

        self._month_name_to_ordinal = None

    def describe(self, timeframe, delta=0):
        ''' Describes a delta within a timeframe in plain language.

        :param timeframe: a string representing a timeframe.
        :param delta: a quantity representing a delta in a timeframe.

        '''

        humanized = self._format_timeframe(timeframe, delta)
        humanized = self._format_relative(humanized, timeframe, delta)

        return humanized

    def day_name(self, day):
        ''' Returns the day name for a specified day of the week.

        :param day: the ``int`` day of the week (1-7).

        '''

        return self.day_names[day]

    def day_abbreviation(self, day):
        ''' Returns the day abbreviation for a specified day of the week.

        :param day: the ``int`` day of the week (1-7).

        '''

        return self.day_abbreviations[day]

    def month_name(self, month):
        ''' Returns the month name for a specified month of the year.

        :param month: the ``int`` month of the year (1-12).

        '''

        return self.month_names[month]

    def month_abbreviation(self, month):
        ''' Returns the month abbreviation for a specified month of the year.

        :param month: the ``int`` month of the year (1-12).

        '''

        return self.month_abbreviations[month]

    def month_number(self, name):
        ''' Returns the month number for a month specified by name or abbreviation.

        :param name: the month name or abbreviation.

        '''

        if self._month_name_to_ordinal is None:
            self._month_name_to_ordinal = self._name_to_ordinal(self.month_names)
            self._month_name_to_ordinal.update(self._name_to_ordinal(self.month_abbreviations))

        return self._month_name_to_ordinal.get(name)

    def meridian(self, hour, token):
        ''' Returns the meridian indicator for a specified hour and format token.

        :param hour: the ``int`` hour of the day.
        :param token: the format token.
        '''

        if token == 'a':
            return self.meridians['am'] if hour < 12 else self.meridians['pm']
        if token == 'A':
            return self.meridians['AM'] if hour < 12 else self.meridians['PM']


    def _name_to_ordinal(self, lst):
        return dict(map(lambda i: (i[1], i[0] + 1), enumerate(lst[1:])))

    def _format_timeframe(self, timeframe, delta):

        return self.timeframes[timeframe].format(abs(delta))

    def _format_relative(self, humanized, timeframe, delta):

        if timeframe == 'now':
            return humanized

        direction = self.past if delta < 0 else self.future

        return direction.format(humanized)


# base locale type implementations.

class EnglishLocale(Locale):

    names = ['en', 'en_us']

    past = '{0} ago'
    future = 'in {0}'

    timeframes = {
        'now': 'just now',
        'seconds': 'seconds',
        'minute': 'a minute',
        'minutes': '{0} minutes',
        'hour': 'an hour',
        'hours': '{0} hours',
        'day': 'a day',
        'days': '{0} days',
        'month': 'a month',
        'months': '{0} months',
        'year': 'a year',
        'years': '{0} years',
    }

    meridians = {
        'am': 'am',
        'pm': 'pm',
        'AM': 'AM',
        'PM': 'PM',
    }

    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December']
    month_abbreviations = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
        'Sep', 'Oct', 'Nov', 'Dec']

    day_names = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_abbreviations = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class ItalianLocale(Locale):
    names = ['it', 'it_it']
    past = '{0} fa'
    future = 'tra {0}'

    timeframes = {
        'now': 'adesso',
        'seconds': 'qualche secondo',
        'minute': 'un minuto',
        'minutes': '{0} minuti',
        'hour': 'un\'ora',
        'hours': '{0} ore',
        'day': 'un giorno',
        'days': '{0} giorni',
        'month': 'un mese',
        'months': '{0} mesi',
        'year': 'un anno',
        'years': '{0} anni',
    }

    month_names = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio',
        'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    month_abbreviations = ['', 'Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago',
        'Set', 'Ott', 'Nov', 'Dic']

    day_names = ['', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    day_abbreviations = ['', 'Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

class SpanishLocale(Locale):
    names = ['es', 'es_es']
    past = 'hace {0}'
    future = 'en {0}'

    timeframes = {
        'now': 'ahora',
        'seconds': 'segundos',
        'minute': 'un minuto',
        'minutes': '{0} minutos',
        'hour': 'una hora',
        'hours': '{0} horas',
        'day': 'un día',
        'days': '{0} días',
        'month': 'un mes',
        'months': '{0} meses',
        'year': 'un año',
        'years': '{0} años',
    }

    month_names = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
        'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    month_abbreviations = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago',
        'Sep', 'Oct', 'Nov', 'Dic']

    day_names = ['', 'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    day_abbreviations = ['', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']


class FrenchLocale(Locale):
    names = ['fr', 'fr_fr']
    past = 'il y a {0}'
    future = 'dans {0}'

    timeframes = {
        'now': 'maintenant',
        'seconds': 'quelques secondes',
        'minute': 'une minute',
        'minutes': '{0} minutes',
        'hour': 'une heure',
        'hours': '{0} heures',
        'day': 'un jour',
        'days': '{0} jours',
        'month': 'un mois',
        'months': '{0} mois',
        'year': 'un an',
        'years': '{0} ans',
    }

    month_names = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet',
        'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    month_abbreviations = ['', 'Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août',
        'Sept', 'Oct', 'Nov', 'Déc']

    day_names = ['', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    day_abbreviations = ['', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']


class GreekLocale(Locale):

    names = ['el', 'el_gr']

    past = '{0} πριν'
    future = 'σε {0}'

    timeframes = {
        'now': 'τώρα',
        'seconds': 'δευτερόλεπτα',
        'minute': 'ένα λεπτό',
        'minutes': '{0} λεπτά',
        'hour': 'μια ώρα',
        'hours': '{0} ώρες',
        'day': 'μια μέρα',
        'days': '{0} μέρες',
        'month': 'ένα μήνα',
        'months': '{0} μήνες',
        'year': 'ένα χρόνο',
        'years': '{0} χρόνια',
    }

    month_names = ['', 'Ιανουαρίου', 'Φεβρουαρίου', 'Μαρτίου', 'Απριλίου', 'Μαΐου', 'Ιουνίου',
        'Ιουλίου', 'Αυγούστου', 'Σεπτεμβρίου', 'Οκτωβρίου', 'Νοεμβρίου', 'Δεκεμβρίου']
    month_abbreviations = ['', 'Ιαν', 'Φεβ', 'Μαρ', 'Απρ', 'Μαϊ', 'Ιον', 'Ιολ', 'Αυγ',
        'Σεπ', 'Οκτ', 'Νοε', 'Δεκ']

    day_names = ['', 'Δευτέρα', 'Τρίτη', 'Τετάρτη', 'Πέμπτη', 'Παρασκευή', 'Σάββατο', 'Κυριακή']
    day_abbreviations = ['', 'Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']


class JapaneseLocale(Locale):

    names = ['ja', 'ja_jp']

    past = '{0}前'
    future = '{0}後'

    timeframes = {
        'now': '現在',
        'seconds': '秒',
        'minute': '1分',
        'minutes': '{0}分',
        'hour': '1時間',
        'hours': '{0}時間',
        'day': '1日',
        'days': '{0}日',
        'month': '1ヶ月',
        'months': '{0}ヶ月',
        'year': '1年',
        'years': '{0}年',
    }

    month_names = ['', '1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月',
        '9月', '10月', '11月', '12月']
    month_abbreviations = ['', ' 1', ' 2', ' 3', ' 4', ' 5', ' 6', ' 7', ' 8',
        ' 9', '10', '11', '12']

    day_names = ['', '月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    day_abbreviations = ['', '月', '火', '水', '木', '金', '土', '日']


class SwedishLocale(Locale):

    names = ['sv', 'sv_se']

    past = 'för {0} sen'
    future = 'om {0}'

    timeframes = {
        'now': 'just nu',
        'seconds': 'några sekunder',
        'minute': 'en minut',
        'minutes': '{0} minuter',
        'hour': 'en timme',
        'hours': '{0} timmar',
        'day': 'en dag',
        'days': '{0} dagar',
        'month': 'en månad',
        'months': '{0} månader',
        'year': 'ett år',
        'years': '{0} år',
    }

    month_names = ['', 'Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni', 'Juli',
        'Augusti', 'September', 'Oktober', 'November', 'December']
    month_abbreviations = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul',
        'Aug', 'Sep', 'Okt', 'Nov', 'Dec']

    day_names = ['', 'Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag', 'Söndag']
    day_abbreviations = ['', 'Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör', 'Sön']


class ChineseCNLocale(Locale):

    names = ['zh', 'zh_cn']

    past = '{0}前'
    future = '{0}后'

    timeframes = {
        'now': '刚才',
        'seconds': '秒',
        'minute': '1分钟',
        'minutes': '{0}分钟',
        'hour': '1小时',
        'hours': '{0}小时',
        'day': '1天',
        'days': '{0}天',
        'month': '1个月',
        'months': '{0}个月',
        'year': '1年',
        'years': '{0}年',
    }

    month_names = ['', '一月', '二月', '三月', '四月', '五月', '六月', '七月',
        '八月', '九月', '十月', '十一月', '十二月']
    month_abbreviations = ['', ' 1', ' 2', ' 3', ' 4', ' 5', ' 6', ' 7', ' 8',
        ' 9', '10', '11', '12']

    day_names = ['', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    day_abbreviations = ['', '一', '二', '三', '四', '五', '六', '日']


class ChineseTWLocale(Locale):

    names = ['zh_tw']

    past = '{0}前'
    future = '{0}後'

    timeframes = {
        'now': '剛才',
        'seconds': '秒',
        'minute': '1分鐘',
        'minutes': '{0}分鐘',
        'hour': '1小時',
        'hours': '{0}小時',
        'day': '1天',
        'days': '{0}天',
        'month': '1個月',
        'months': '{0}個月',
        'year': '1年',
        'years': '{0}年',
    }

    month_names = ['', '1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月',
        '9月', '10月', '11月', '12月']
    month_abbreviations = ['', ' 1', ' 2', ' 3', ' 4', ' 5', ' 6', ' 7', ' 8',
        ' 9', '10', '11', '12']

    day_names = ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日']
    day_abbreviations = ['', '一', '二', '三', '四', '五', '六', '日']


class KoreanLocale(Locale):

    names = ['ko', 'ko_kr']

    past = '{0} 전'
    future = '{0} 후'

    timeframes = {
        'now': '지금',
        'seconds': '몇초',
        'minute': '일 분',
        'minutes': '{0}분',
        'hour': '1시간',
        'hours': '{0}시간',
        'day': '1일',
        'days': '{0}일',
        'month': '1개월',
        'months': '{0}개월',
        'year': '1년',
        'years': '{0}년',
    }

    month_names = ['', '1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월',
        '9월', '10월', '11월', '12월']
    month_abbreviations = ['', ' 1', ' 2', ' 3', ' 4', ' 5', ' 6', ' 7', ' 8',
        ' 9', '10', '11', '12']

    day_names = ['', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    day_abbreviations = ['', '월', '화', '수', '목', '금', '토', '일']


# derived locale types & implementations.
class DutchLocale(Locale):

    names = ['nl', 'nl_nl']

    past = '{0} geleden'
    future = 'over {0}'

    timeframes = {
        'now': 'nu',
        'seconds': 'seconden',
        'minute': 'een minuut',
        'minutes': '{0} minuten',
        'hour': 'een uur',
        'hours': '{0} uren',
        'day': 'een dag',
        'days': '{0} dagen',
        'month': 'een maand',
        'months': '{0} maanden',
        'year': 'een jaar',
        'years': '{0} jaren',
    }

    # In Dutch names of months and days are not starting with a capital letter
    # like in the English language.
    month_names = ['', 'januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
        'augustus', 'september', 'oktober', 'november', 'december']
    month_abbreviations = ['', 'jan', 'feb', 'maa', 'apr', 'mei', 'jun', 'jul', 'aug',
        'sep', 'okt', 'nov', 'dec']

    day_names = ['', 'maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag']
    day_abbreviations = ['', 'ma', 'di', 'wo', 'do', 'vr', 'za', 'zo']


class SlavicBaseLocale(Locale):

    def _format_timeframe(self, timeframe, delta):

        form = self.timeframes[timeframe]
        delta = abs(delta)

        if isinstance(form, list):

            if delta % 10 == 1 and delta % 100 != 11:
                form = form[0]
            elif 2 <= delta % 10 <= 4 and (delta % 100 < 10 or delta % 100 >= 20):
                form = form[1]
            else:
                form = form[2]

        return form.format(delta)


class PolishLocale(SlavicBaseLocale):

    names = ['pl', 'pl_pl']

    past = '{0} temu'
    future = 'za {0}'

    timeframes = {
        'now': 'teraz',
        'seconds': 'kilka sekund',
        'minute': 'minuta',
        'minutes': ['{0} minut', '{0} minuty', '{0} minut'],
        'hour': 'godzina',
        'hours': ['{0} godzin', '{0} godziny', '{0} godzin'],
        'day': 'dzień',
        'days': ['{0} dzień', '{0} dni', '{0} dni'],
        'month': 'miesiąc',
        'months': ['{0} miesiąc', '{0} miesiące', '{0} miesięcy'],
        'year': 'rok',
        'years': ['{0} rok', '{0} lata', '{0} lat'],
    }

    month_names = ['', 'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj',
        'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik',
        'Listopad', 'Grudzień']
    month_abbreviations = ['', 'sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip',
        'sie', 'wrz', 'paź', 'lis', 'gru']

    day_names = ['', 'Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek',
        'Sobota', 'Niedziela']
    day_abbreviations = ['', 'Pn', 'Wt', 'Śr', 'Czw', 'Pt', 'So', 'Nd']


class RussianLocale(SlavicBaseLocale):

    names = ['ru', 'ru_ru']

    past = '{0} назад'
    future = 'через {0}'

    timeframes = {
        'now': 'сейчас',
        'seconds': 'несколько секунд',
        'minute': 'минуту',
        'minutes': ['{0} минуту', '{0} минуты', '{0} минут'],
        'hour': 'час',
        'hours': ['{0} час', '{0} часа', '{0} часов'],
        'day': 'день',
        'days': ['{0} день', '{0} дня', '{0} дней'],
        'month': 'месяц',
        'months': ['{0} месяц', '{0} месяца', '{0} месяцев'],
        'year': 'год',
        'years': ['{0} год', '{0} года', '{0} лет'],
    }

    month_names = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    month_abbreviations = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл',
        'авг', 'сен', 'окт', 'ноя', 'дек']

    day_names = ['', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница',
        'суббота', 'воскресенье']
    day_abbreviations = ['', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']


class UkrainianLocale(SlavicBaseLocale):

    names = ['ua', 'uk_ua']

    past = '{0} тому'
    future = 'за {0}'

    timeframes = {
        'now': 'зараз',
        'seconds': 'кілька секунд',
        'minute': 'хвилину',
        'minutes': ['{0} хвилину', '{0} хвилини', '{0} хвилин'],
        'hour': 'годину',
        'hours': ['{0} годину', '{0} години', '{0} годин'],
        'day': 'день',
        'days': ['{0} день', '{0} дні', '{0} днів'],
        'month': 'місяць',
        'months': ['{0} місяць', '{0} місяці', '{0} місяців'],
        'year': 'рік',
        'years': ['{0} рік', '{0} роки', '{0} років'],
    }

    month_names = ['', 'січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
        'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня']
    month_abbreviations = ['', 'січ', 'лют', 'бер', 'кві', 'тра', 'чер', 'лип', 'сер',
        'вер', 'жов', 'лис', 'гру']

    day_names = ['', 'понеділок', 'вівторок', 'середа', 'четвер', 'п\'ятниця', 'субота', 'неділя']
    day_abbreviations = ['', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'нд']


class GermanLocale(Locale):

    names = ['de', 'de_de']

    past = 'vor {0}'
    future = 'in {0}'

    timeframes = {
        'now': 'gerade eben',
        'seconds': 'Sekunden',
        'minute': 'einer Minute',
        'minutes': '{0} Minuten',
        'hour': 'einer Stunde',
        'hours': '{0} Stunden',
        'day': 'einem Tag',
        'days': '{0} Tagen',
        'month': 'einem Monat',
        'months': '{0} Monaten',
        'year': 'einem Jahr',
        'years': '{0} Jahren',
    }

    month_names = [
        '', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
        'August', 'September', 'Oktober', 'November', 'Dezember'
    ]
    month_abbreviations = [
        '', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep',
        'Okt', 'Nov', 'Dez'
    ]

    day_names = [
       '', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag',
       'Samstag', 'Sonntag'
    ]

    day_abbreviations = ['', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']


class AustriaLocale(Locale):

    names = ['de', 'de_at']

    past = 'vor {0}'
    future = 'in {0}'

    timeframes = {
            'now': 'gerade eben',
            'seconds':  'Sekunden',
            'minute': 'einer Minute',
            'minutes': '{0} Minuten',
            'hour': 'einer Stunde',
            'hours': '{0} Stunden',
            'day': 'einem Tag',
            'days': '{0} Tage',
            'month': 'einem Monat',
            'months': '{0} Monaten',
            'year': 'einem Jahr',
            'years': '{0} Jahren',
        }

    month_names = [
            '', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
            'August', 'September', 'Oktober', 'November', 'Dezember'
        ]

    month_abbreviations = [
            '', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep',
            'Okt', 'Nov', 'Dez'
        ]

    day_names = [
            '', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag',
            'Samstag', 'Sonntag'
        ]

    day_abbreviations = [
            '', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'
        ]

class NorwegianLocale(Locale):

    names = ['nb', 'nb_no']

    past = 'for {0} siden'
    future = 'om {0}'

    timeframes = {
        'now': 'nå nettopp',
        'seconds': 'noen sekunder',
        'minute': 'ett minutt',
        'minutes': '{0} minutter',
        'hour': 'en time',
        'hours': '{0} timer',
        'day': 'en dag',
        'days': '{0} dager',
        'month': 'en måned',
        'months': '{0} måneder',
        'year': 'ett år',
        'years': '{0} år',
    }

    month_names = ['', 'Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
                   'Juli', 'August', 'September', 'Oktober', 'November',
                   'Desember']
    month_abbreviations = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul',
                           'Aug', 'Sep', 'Okt', 'Nov', 'Des']

    day_names = ['', 'Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag',
                 'Lørdag', 'Søndag']
    day_abbreviations = ['', 'Ma', 'Ti', 'On', 'To', 'Fr', 'Lø', 'Sø']


class NewNorwegianLocale(Locale):

    names = ['nn', 'nn_no']

    past = 'for {0} sidan'
    future = 'om {0}'

    timeframes = {
        'now': 'no nettopp',
        'seconds': 'nokre sekund',
        'minute': 'ett minutt',
        'minutes': '{0} minutt',
        'hour': 'ein time',
        'hours': '{0} timar',
        'day': 'ein dag',
        'days': '{0} dagar',
        'month': 'en månad',
        'months': '{0} månader',
        'year': 'Eit år',
        'years': '{0} år',
    }

    month_names = ['', 'Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
                   'Juli', 'August', 'September', 'Oktober', 'November',
                   'Desember']
    month_abbreviations = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul',
                           'Aug', 'Sep', 'Okt', 'Nov', 'Des']

    day_names = ['', 'Måndag', 'Tysdag', 'Onsdag', 'Torsdag', 'Fredag',
                 'Laurdag', 'Sundag']
    day_abbreviations = ['', 'Må', 'Ty', 'On', 'To', 'Fr', 'La', 'Su']


class BrazilianLocale(Locale):
    names = ['pt_br']

    past = 'fazem {0}'
    future = 'em {0}'

    timeframes = {
        'now': 'agora',
        'seconds': 'segundos',
        'minute': 'um minuto',
        'minutes': '{0} minutos',
        'hour': 'uma hora',
        'hours': '{0} horas',
        'day': 'um dia',
        'days': '{0} dias',
        'month': 'um mês',
        'months': '{0} meses',
        'year': 'um ano',
        'years': '{0} anos',
    }

    month_names = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
        'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    month_abbreviations = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Maio', 'Jun', 'Jul', 'Ago',
        'Set', 'Out', 'Nov', 'Dez']

    day_names = ['', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira',
        'Sábado', 'Domingo']
    day_abbreviations = ['', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']


class TagalogLocale(Locale):

    names = ['tl']

    past = 'nakaraang {0}'
    future = '{0} mula ngayon'

    timeframes = {
        'now': 'ngayon lang',
        'seconds': 'segundo',
        'minute': 'isang minuto',
        'minutes': '{0} minuto',
        'hour': 'isang oras',
        'hours': '{0} oras',
        'day': 'isang araw',
        'days': '{0} araw',
        'month': 'isang buwan',
        'months': '{0} buwan',
        'year': 'isang taon',
        'years': '{0} taon',
    }

    month_names = ['', 'Enero', 'Pebrero', 'Marso', 'Abril', 'Mayo', 'Hunyo', 'Hulyo',
        'Agosto', 'Setyembre', 'Oktubre', 'Nobyembre', 'Disyembre']
    month_abbreviations = ['', 'Ene', 'Peb', 'Mar', 'Abr', 'May', 'Hun', 'Hul', 'Ago',
        'Set', 'Okt', 'Nob', 'Dis']

    day_names = ['', 'Lunes', 'Martes', 'Miyerkules', 'Huwebes', 'Biyernes', 'Sabado', 'Linggo']
    day_abbreviations = ['', 'Lun', 'Mar', 'Miy', 'Huw', 'Biy', 'Sab', 'Lin']


class VietnameseLocale(Locale):

    names = ['vi', 'vi_vn']

    past = '{0} trước'
    future = '{0} nữa'

    timeframes = {
        'now': 'hiện tại',
        'seconds': 'giây',
        'minute': 'một phút',
        'minutes': '{0} phút',
        'hour': 'một giờ',
        'hours': '{0} giờ',
        'day': 'một ngày',
        'days': '{0} ngày',
        'month': 'một tháng',
        'months': '{0} tháng',
        'year': 'một năm',
        'years': '{0} năm',
    }

    month_names = ['', 'Tháng Một', 'Tháng Hai', 'Tháng Ba', 'Tháng Tư', 'Tháng Năm', 'Tháng Sáu', 'Tháng Bảy',
        'Tháng Tám', 'Tháng Chín', 'Tháng Mười', 'Tháng Mười Một', 'Tháng Mười Hai']
    month_abbreviations = ['', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8',
        'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12']

    day_names = ['', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']
    day_abbreviations = ['', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'CN']


class TurkishLocale(Locale):

    names = ['tr', 'tr_TR']

    past = '{0} önce'
    future = '{0} sonra'

    timeframes = {
        'now': 'şimdi',
        'seconds': 'saniye',
        'minute': 'bir dakika',
        'minutes': '{0} dakika',
        'hour': 'bir saat',
        'hours': '{0} saat',
        'day': 'bir gün',
        'days': '{0} gün',
        'month': 'bir ay',
        'months': '{0} ay',
        'year': 'a yıl',
        'years': '{0} yıl',
    }

    month_names = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz',
        'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
    month_abbreviations = ['', 'Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu',
        'Eyl', 'Eki', 'Kas', 'Ara']

    day_names = ['', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    day_abbreviations = ['', 'Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']


class ArabicLocale(Locale):

    names = ['ar', 'ar_EG']

    past = 'منذ {0}'
    future = 'خلال {0}'

    timeframes = {
        'now': 'الآن',
        'seconds': 'ثوان',
        'minute': 'دقيقة',
        'minutes': '{0} دقائق',
        'hour': 'ساعة',
        'hours': '{0} ساعات',
        'day': 'يوم',
        'days': '{0} أيام',
        'month': 'شهر',
        'months': '{0} شهور',
        'year': 'سنة',
        'years': '{0} سنوات',
    }

    month_names = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو',
        'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    month_abbreviations = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو',
        'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

    day_names = ['', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    day_abbreviations = ['', 'اثنين', 'ثلاثاء', 'أربعاء', 'خميس', 'جمعة', 'سبت', 'أحد']


class IcelandicLocale(Locale):

    def _format_timeframe(self, timeframe, delta):

        timeframe = self.timeframes[timeframe]
        if delta < 0:
            timeframe = timeframe[0]
        elif delta > 0:
            timeframe = timeframe[1]

        return timeframe.format(abs(delta))

    names = ['is', 'is_is']

    past = 'fyrir {0} síðan'
    future = 'eftir {0}'

    timeframes = {
        'now':     'rétt í þessu',
        'seconds': ('nokkrum sekúndum', 'nokkrar sekúndur'),
        'minute':  ('einni mínútu', 'eina mínútu'),
        'minutes': ('{0} mínútum', '{0} mínútur'),
        'hour':    ('einum tíma', 'einn tíma'),
        'hours':   ('{0} tímum', '{0} tíma'),
        'day':     ('einum degi', 'einn dag'),
        'days':    ('{0} dögum', '{0} daga'),
        'month':   ('einum mánuði', 'einn mánuð'),
        'months':  ('{0} mánuðum', '{0} mánuði'),
        'year':    ('einu ári', 'eitt ár'),
        'years':   ('{0} árum', '{0} ár'),
    }

    meridians = {
        'am': 'f.h.',
        'pm': 'e.h.',
        'AM': 'f.h.',
        'PM': 'e.h.',
    }

    month_names = ['', 'janúar', 'febrúar', 'mars', 'apríl', 'maí', 'júní',
        'júlí', 'ágúst', 'september', 'október', 'nóvember', 'desember']
    month_abbreviations = ['', 'jan', 'feb', 'mar', 'apr', 'maí', 'jún',
        'júl', 'ágú', 'sep', 'okt', 'nóv', 'des']

    day_names = ['', 'mánudagur', 'þriðjudagur', 'miðvikudagur', 'fimmtudagur',
        'föstudagur', 'laugardagur', 'sunnudagur']
    day_abbreviations = ['', 'mán', 'þri', 'mið', 'fim', 'fös', 'lau', 'sun']


class DanishLocale(Locale):

    names = ['da', 'da_dk']

    past = 'for {0} siden'
    future = 'efter {0}'

    timeframes = {
        'now':     'lige nu',
        'seconds': 'et par sekunder',
        'minute':  'et minut',
        'minutes': '{0} minutter',
        'hour':    'en time',
        'hours':   '{0} timer',
        'day':     'en dag',
        'days':    '{0} dage',
        'month':   'en måned',
        'months':  '{0} måneder',
        'year':    'et år',
        'years':   '{0} år',
    }

    month_names = ['', 'januar', 'februar', 'marts', 'april', 'maj', 'juni',
        'juli', 'august', 'september', 'oktober', 'november', 'december']
    month_abbreviations = ['', 'jan', 'feb', 'mar', 'apr', 'maj', 'jun',
        'jul', 'aug', 'sep', 'okt', 'nov', 'dec']

    day_names = ['', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag',
        'lørdag', 'søndag']
    day_abbreviations = ['', 'man', 'tir', 'ons', 'tor', 'fre', 'lør', 'søn']

def _map_locales():

    locales = {}

    for cls_name, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if issubclass(cls, Locale):
            for name in cls.names:
                locales[name] = cls

    return locales

_locales = _map_locales()

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from datetime import datetime
from dateutil import tz

import calendar
import re

from arrow import locales


class ParserError(RuntimeError):
    pass


class DateTimeParser(object):

    _FORMAT_RE = re.compile('(YYY?Y?|MM?M?M?|DD?D?D?|HH?|hh?|mm?|ss?|SS?S?S?S?S?|ZZ?|a|A|X)')

    _ONE_THROUGH_SIX_DIGIT_RE = re.compile('\d{1,6}')
    _ONE_THROUGH_FIVE_DIGIT_RE = re.compile('\d{1,5}')
    _ONE_THROUGH_FOUR_DIGIT_RE = re.compile('\d{1,4}')
    _ONE_TWO_OR_THREE_DIGIT_RE = re.compile('\d{1,3}')
    _ONE_OR_TWO_DIGIT_RE = re.compile('\d{1,2}')
    _FOUR_DIGIT_RE = re.compile('\d{4}')
    _TWO_DIGIT_RE = re.compile('\d{2}')
    _TZ_RE = re.compile('[+\-]?\d{2}:?\d{2}')

    _INPUT_RE_MAP = {
        'YYYY': _FOUR_DIGIT_RE,
        'YY': _TWO_DIGIT_RE,
        'MMMM': re.compile('({0})'.format('|'.join(calendar.month_name[1:]))),
        'MMM': re.compile('({0})'.format('|'.join(calendar.month_abbr[1:]))),
        'MM': _TWO_DIGIT_RE,
        'M': _ONE_OR_TWO_DIGIT_RE,
        'DD': _TWO_DIGIT_RE,
        'D': _ONE_OR_TWO_DIGIT_RE,
        'HH': _TWO_DIGIT_RE,
        'H': _ONE_OR_TWO_DIGIT_RE,
        'hh': _TWO_DIGIT_RE,
        'h': _ONE_OR_TWO_DIGIT_RE,
        'mm': _TWO_DIGIT_RE,
        'm': _ONE_OR_TWO_DIGIT_RE,
        'ss': _TWO_DIGIT_RE,
        's': _ONE_OR_TWO_DIGIT_RE,
        'a': re.compile('(a|A|p|P)'),
        'A': re.compile('(am|AM|pm|PM)'),
        'X': re.compile('\d+'),
        'ZZ': _TZ_RE,
        'Z': _TZ_RE,
        'SSSSSS': _ONE_THROUGH_SIX_DIGIT_RE,
        'SSSSS': _ONE_THROUGH_FIVE_DIGIT_RE,
        'SSSS': _ONE_THROUGH_FOUR_DIGIT_RE,
        'SSS': _ONE_TWO_OR_THREE_DIGIT_RE,
        'SS': _ONE_OR_TWO_DIGIT_RE,
        'S': re.compile('\d'),
    }

    def __init__(self, locale='en_us'):

        self.locale = locales.get_locale(locale)

    def parse_iso(self, string):

        has_time = 'T' in string

        if has_time:
            date_string, time_string = string.split('T', 1)
            time_parts = re.split('[+-]', time_string, 1)
            has_tz = len(time_parts) > 1
            has_seconds = time_parts[0].count(':') > 1
            has_subseconds = '.' in time_parts[0]

        else:
            has_tz = has_seconds = has_subseconds = False

        if has_time:

            if has_subseconds:
                formats = ['YYYY-MM-DDTHH:mm:ss.SSSSSS']
            elif has_seconds:
                formats = ['YYYY-MM-DDTHH:mm:ss']
            else:
                formats = ['YYYY-MM-DDTHH:mm']

        else:
            formats = [
                'YYYY-MM-DD',
                'YYYY-MM',
                'YYYY',
            ]

        if has_time and has_tz:
            formats = [f + 'Z' for f in formats]

        return self._parse_multiformat(string, formats)

    def parse(self, string, fmt):

        if isinstance(fmt, list):
            return self._parse_multiformat(string, fmt)

        tokens = self._FORMAT_RE.findall(fmt)
        parts = {}

        for token in tokens:

            try:
                input_re = self._INPUT_RE_MAP[token]
            except KeyError:
                raise ParserError('Unrecognized token \'{0}\''.format(token))

            match = input_re.search(string)

            if match:

                self._parse_token(token, match.group(0), parts)

                index = match.span(0)[1]
                string = string[index:]

            else:
                raise ParserError('Failed to match token \'{0}\''.format(token))

        return self._build_datetime(parts)

    def _parse_token(self, token, value, parts):

        if token == 'YYYY':
            parts['year'] = int(value)
        elif token == 'YY':
            value = int(value)
            parts['year'] = 1900 + value if value > 68 else 2000 + value

        elif token in ['MMMM', 'MMM']:
            parts['month'] = self.locale.month_number(value)
        elif token in ['MM', 'M']:
            parts['month'] = int(value)

        elif token in ['DD', 'D']:
            parts['day'] = int(value)

        elif token in ['HH', 'H']:
            parts['hour'] = int(value)

        elif token in ['mm', 'm']:
            parts['minute'] = int(value)

        elif token in ['ss', 's']:
            parts['second'] = int(value)

        elif token == 'SSSSSS':
            parts['microsecond'] = int(value)
        elif token == 'SSSSS':
            parts['microsecond'] = int(value) * 10
        elif token == 'SSSS':
            parts['microsecond'] = int(value) * 100
        elif token == 'SSS':
            parts['microsecond'] = int(value) * 1000
        elif token == 'SS':
            parts['microsecond'] = int(value) * 10000
        elif token == 'S':
            parts['microsecond'] = int(value) * 100000

        elif token == 'X':
            parts['timestamp'] = int(value)

        elif token in ['ZZ', 'Z']:
            parts['tzinfo'] = TzinfoParser.parse(value)

        elif token in ['a', 'A']:
            if value in ['a', 'A', 'am', 'AM']:
                parts['am_pm'] = 'am'
            elif value in ['p', 'P', 'pm', 'PM']:
                parts['am_pm'] = 'pm'

    @classmethod
    def _build_datetime(cls, parts):

        timestamp = parts.get('timestamp')

        if timestamp:
            return datetime.fromtimestamp(timestamp)

        am_pm = parts.get('am_pm')
        hour = parts.get('hour', 0)

        if am_pm == 'pm' and hour < 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0

        return datetime(year=parts.get('year', 1), month=parts.get('month', 1),
            day=parts.get('day', 1), hour=hour, minute=parts.get('minute', 0),
            second=parts.get('second', 0), microsecond=parts.get('microsecond', 0),
            tzinfo=parts.get('tzinfo'))

    def _parse_multiformat(self, string, formats):

        _datetime = None

        for fmt in formats:
            try:
                _datetime = self.parse(string, fmt)
                break
            except:
                pass

        if _datetime is None:
            raise ParserError('Could not match input to any of {0}'.format(formats))

        return _datetime

    @classmethod
    def _map_lookup(cls, input_map, key):

        try:
            return input_map[key]
        except KeyError:
            raise ParserError('Could not match "{0}" to {1}'.format(key, input_map))

    @classmethod
    def _try_timestamp(cls, string):

        try:
            return float(string)
        except:
            return None


class TzinfoParser(object):

    _TZINFO_RE = re.compile('([+\-])?(\d\d):?(\d\d)')

    @classmethod
    def parse(cls, string):

        tzinfo = None

        if string == 'local':
            tzinfo = tz.tzlocal()

        elif string in ['utc', 'UTC']:
            tzinfo = tz.tzutc()

        else:

            iso_match = cls._TZINFO_RE.match(string)

            if iso_match:
                sign, hours, minutes = iso_match.groups()
                seconds = int(hours) * 3600 + int(minutes) * 60

                if sign == '-':
                    seconds *= -1

                tzinfo = tz.tzoffset(None, seconds)

            else:
                tzinfo = tz.gettz(string)

        if tzinfo is None:
            raise ParserError('Could not parse timezone expression "{0}"', string)

        return tzinfo

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from datetime import timedelta
import sys

# python 2.6 / 2.7 definitions for total_seconds function.

def _total_seconds_27(td): # pragma: no cover
    return td.total_seconds()

def _total_seconds_26(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6


# get version info and assign correct total_seconds function.

version = '{0}.{1}.{2}'.format(*sys.version_info[:3])

if version < '2.7': # pragma: no cover
    total_seconds = _total_seconds_26
else: # pragma: no cover
    total_seconds = _total_seconds_27


# python 2.7 / 3.0+ definitions for isstr function.

try: # pragma: no cover
    basestring

    def isstr(s):
        return isinstance(s, basestring)

except NameError: #pragma: no cover

    def isstr(s):
        return isinstance(s, str)


__all__ = ['total_seconds', 'isstr']

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Arrow documentation build configuration file, created by
# sphinx-quickstart on Mon May  6 15:25:39 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Arrow'
copyright = u'2013, Chris Smith'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4.2'
# The full version, including alpha/beta/rc tags.
release = '0.4.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'f6'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Arrowdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Arrow.tex', u'Arrow Documentation',
   u'Chris Smith', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'arrow', u'Arrow Documentation',
     [u'Chris Smith'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Arrow', u'Arrow Documentation',
   u'Chris Smith', 'Arrow', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

autodoc_member_order = 'bysource'

########NEW FILE########
__FILENAME__ = api_tests
from chai import Chai
from datetime import datetime
from dateutil import tz
import time

from arrow import api, factory, arrow, util


class ModuleTests(Chai):

    def test_get(self):

        expect(api._factory.get).args(1, b=2).returns('result')

        assertEqual(api.get(1, b=2), 'result')

    def test_utcnow(self):

        expect(api._factory.utcnow).returns('utcnow')

        assertEqual(api.utcnow(), 'utcnow')

    def test_now(self):

        expect(api._factory.now).args('tz').returns('now')

        assertEqual(api.now('tz'), 'now')

    def test_factory(self):

        class MockCustomArrowClass(arrow.Arrow):
            pass

        result = api.factory(MockCustomArrowClass)

        assertIsInstance(result, factory.ArrowFactory)
        assertIsInstance(result.utcnow(), MockCustomArrowClass)


########NEW FILE########
__FILENAME__ = arrow_tests
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from chai import Chai

from datetime import date, datetime, timedelta
from dateutil import tz
import calendar
import pickle
import time
import sys

from arrow import arrow, util


def assertDtEqual(dt1, dt2, within=10):
    assertEqual(dt1.tzinfo, dt2.tzinfo)
    assertTrue(abs(util.total_seconds(dt1 - dt2)) < within)


class ArrowInitTests(Chai):

    def test_init(self):

        result = arrow.Arrow(2013, 2, 2, 12, 30, 45, 999999)
        expected = datetime(2013, 2, 2, 12, 30, 45, 999999, tzinfo=tz.tzutc())

        assertEqual(result._datetime, expected)


class ArrowFactoryTests(Chai):

    def test_now(self):

        result = arrow.Arrow.now()

        assertDtEqual(result._datetime, datetime.now().replace(tzinfo=tz.tzlocal()))

    def test_utcnow(self):

        result = arrow.Arrow.utcnow()

        assertDtEqual(result._datetime, datetime.utcnow().replace(tzinfo=tz.tzutc()))

    def test_formtimestamp(self):

        timestamp = time.time()

        result = arrow.Arrow.fromtimestamp(timestamp)

        assertDtEqual(result._datetime, datetime.now().replace(tzinfo=tz.tzlocal()))

    def test_fromdatetime(self):

        dt = datetime(2013, 2, 3, 12, 30, 45, 1)

        result = arrow.Arrow.fromdatetime(dt)

        assertEqual(result._datetime, dt.replace(tzinfo=tz.tzutc()))

    def test_fromdatetime_dt_tzinfo(self):

        dt = datetime(2013, 2, 3, 12, 30, 45, 1, tzinfo=tz.gettz('US/Pacific'))

        result = arrow.Arrow.fromdatetime(dt)

        assertEqual(result._datetime, dt.replace(tzinfo=tz.gettz('US/Pacific')))

    def test_fromdatetime_tzinfo_arg(self):

        dt = datetime(2013, 2, 3, 12, 30, 45, 1)

        result = arrow.Arrow.fromdatetime(dt, tz.gettz('US/Pacific'))

        assertEqual(result._datetime, dt.replace(tzinfo=tz.gettz('US/Pacific')))

    def test_fromdate(self):

        dt = date(2013, 2, 3)

        result = arrow.Arrow.fromdate(dt, tz.gettz('US/Pacific'))

        assertEqual(result._datetime, datetime(2013, 2, 3, tzinfo=tz.gettz('US/Pacific')))

    def test_strptime(self):

        formatted = datetime(2013, 2, 3, 12, 30, 45).strftime('%Y-%m-%d %H:%M:%S')

        result = arrow.Arrow.strptime(formatted, '%Y-%m-%d %H:%M:%S')

        assertEqual(result._datetime, datetime(2013, 2, 3, 12, 30, 45, tzinfo=tz.tzutc()))


class ArrowRepresentationTests(Chai):

    def setUp(self):
        super(ArrowRepresentationTests, self).setUp()

        self.arrow = arrow.Arrow(2013, 2, 3, 12, 30, 45, 1)

    def test_repr(self):

        result = self.arrow.__repr__()

        assertEqual(result, '<Arrow [{0}]>'.format(self.arrow._datetime.isoformat()))

    def test_str(self):

        result = self.arrow.__str__()

        assertEqual(result, self.arrow._datetime.isoformat())

    def test_hash(self):

        result = self.arrow.__hash__()

        assertEqual(result, self.arrow._datetime.__hash__())

    def test_format(self):

        result = '{0:YYYY-MM-DD}'.format(self.arrow)

        assertEqual(result, '2013-02-03')

    def test_format_no_format_string(self):

        result = '{0}'.format(self.arrow)

        assertEqual(result, str(self.arrow))

    def test_clone(self):

        result = self.arrow.clone()

        assertTrue(result is not self.arrow)
        assertEqual(result._datetime, self.arrow._datetime)


class ArrowAttributeTests(Chai):

    def setUp(self):
        super(ArrowAttributeTests, self).setUp()

        self.arrow = arrow.Arrow(2013, 1, 1)

    def test_getattr_base(self):

        with assertRaises(AttributeError):
            self.arrow.prop

    def test_getattr_week(self):

        assertEqual(self.arrow.week, 1)

    def test_getattr_dt_value(self):

        assertEqual(self.arrow.year, 2013)

    def test_tzinfo(self):

        self.arrow.tzinfo = tz.gettz('PST')
        assertEqual(self.arrow.tzinfo, tz.gettz('PST'))

    def test_naive(self):

        assertEqual(self.arrow.naive, self.arrow._datetime.replace(tzinfo=None))

    def test_timestamp(self):

        assertEqual(self.arrow.timestamp, calendar.timegm(self.arrow._datetime.utctimetuple()))

    def test_float_timestamp(self):

        result = self.arrow.float_timestamp - self.arrow.timestamp

        assertEqual(result, self.arrow.microsecond)


class ArrowComparisonTests(Chai):

    def setUp(self):
        super(ArrowComparisonTests, self).setUp()

        self.arrow = arrow.Arrow.utcnow()

    def test_eq(self):

        assertTrue(self.arrow == self.arrow)
        assertTrue(self.arrow == self.arrow.datetime)
        assertFalse(self.arrow == 'abc')

    def test_ne(self):

        assertFalse(self.arrow != self.arrow)
        assertFalse(self.arrow != self.arrow.datetime)
        assertTrue(self.arrow != 'abc')

    def test_gt(self):

        arrow_cmp = self.arrow.replace(minutes=1)

        assertFalse(self.arrow > self.arrow)
        assertFalse(self.arrow > self.arrow.datetime)
        assertFalse(self.arrow > 'abc')
        assertTrue(self.arrow < arrow_cmp)
        assertTrue(self.arrow < arrow_cmp.datetime)

    def test_ge(self):

        assertFalse(self.arrow >= 'abc')
        assertTrue(self.arrow >= self.arrow)
        assertTrue(self.arrow >= self.arrow.datetime)

    def test_lt(self):

        arrow_cmp = self.arrow.replace(minutes=1)

        assertFalse(self.arrow < self.arrow)
        assertFalse(self.arrow < self.arrow.datetime)
        assertFalse(self.arrow < 'abc')
        assertTrue(self.arrow < arrow_cmp)
        assertTrue(self.arrow < arrow_cmp.datetime)

    def test_le(self):

        assertFalse(self.arrow <= 'abc')
        assertTrue(self.arrow <= self.arrow)
        assertTrue(self.arrow <= self.arrow.datetime)


class ArrowMathTests(Chai):

    def setUp(self):
        super(ArrowMathTests, self).setUp()

        self.arrow = arrow.Arrow(2013, 1, 1)

    def test_add_timedelta(self):

        result = self.arrow.__add__(timedelta(days=1))

        assertEqual(result._datetime, datetime(2013, 1, 2, tzinfo=tz.tzutc()))

    def test_add_other(self):

        with assertRaises(NotImplementedError):
            self.arrow.__add__(1)

    def test_radd(self):

        result = self.arrow.__radd__(timedelta(days=1))

        assertEqual(result._datetime, datetime(2013, 1, 2, tzinfo=tz.tzutc()))

    def test_sub_timedelta(self):

        result = self.arrow.__sub__(timedelta(days=1))

        assertEqual(result._datetime, datetime(2012, 12, 31, tzinfo=tz.tzutc()))

    def test_sub_datetime(self):

        result = self.arrow.__sub__(datetime(2012, 12, 21, tzinfo=tz.tzutc()))

        assertEqual(result, timedelta(days=11))

    def test_sub_arrow(self):

        result = self.arrow.__sub__(arrow.Arrow(2012, 12, 21, tzinfo=tz.tzutc()))

        assertEqual(result, timedelta(days=11))

    def test_sub_other(self):

        with assertRaises(NotImplementedError):
            self.arrow.__sub__(object())

    def test_rsub(self):

        result = self.arrow.__rsub__(timedelta(days=1))

        assertEqual(result._datetime, datetime(2012, 12, 31, tzinfo=tz.tzutc()))


class ArrowDatetimeInterfaceTests(Chai):

    def setUp(self):
        super(ArrowDatetimeInterfaceTests, self).setUp()

        self.arrow = arrow.Arrow.utcnow()

    def test_date(self):

        result = self.arrow.date()

        assertEqual(result, self.arrow._datetime.date())

    def test_time(self):

        result = self.arrow.time()

        assertEqual(result, self.arrow._datetime.time())

    def test_timetz(self):

        result = self.arrow.timetz()

        assertEqual(result, self.arrow._datetime.timetz())

    def test_astimezone(self):

        other_tz = tz.gettz('US/Pacific')

        result = self.arrow.astimezone(other_tz)

        assertEqual(result, self.arrow._datetime.astimezone(other_tz))

    def test_utcoffset(self):

        result = self.arrow.utcoffset()

        assertEqual(result, self.arrow._datetime.utcoffset())

    def test_dst(self):

        result = self.arrow.dst()

        assertEqual(result, self.arrow._datetime.dst())

    def test_timetuple(self):

        result = self.arrow.timetuple()

        assertEqual(result, self.arrow._datetime.timetuple())

    def test_utctimetuple(self):

        result = self.arrow.utctimetuple()

        assertEqual(result, self.arrow._datetime.utctimetuple())

    def test_toordinal(self):

        result = self.arrow.toordinal()

        assertEqual(result, self.arrow._datetime.toordinal())

    def test_weekday(self):

        result = self.arrow.weekday()

        assertEqual(result, self.arrow._datetime.weekday())

    def test_isoweekday(self):

        result = self.arrow.isoweekday()

        assertEqual(result, self.arrow._datetime.isoweekday())

    def test_isocalendar(self):

        result = self.arrow.isocalendar()

        assertEqual(result, self.arrow._datetime.isocalendar())

    def test_isoformat(self):

        result = self.arrow.isoformat()

        assertEqual(result, self.arrow._datetime.isoformat())

    def test_ctime(self):

        result = self.arrow.ctime()

        assertEqual(result, self.arrow._datetime.ctime())

    def test_strftime(self):

        result = self.arrow.strftime('%Y')

        assertEqual(result, self.arrow._datetime.strftime('%Y'))


class ArrowConversionTests(Chai):

    def test_to(self):

        dt_from = datetime.now()
        arrow_from = arrow.Arrow.fromdatetime(dt_from, tz.gettz('US/Pacific'))

        result = arrow_from.to('UTC')

        expected = dt_from.replace(tzinfo=tz.gettz('US/Pacific')).astimezone(tz.tzutc())

        assertEqual(result.datetime, expected)


class ArrowPicklingTests(Chai):

    def test_pickle_and_unpickle(self):

        dt = arrow.Arrow.utcnow()

        pickled = pickle.dumps(dt)

        unpickled = pickle.loads(pickled)

        assertEqual(unpickled, dt)


class ArrowReplaceTests(Chai):

    def test_not_attr(self):

        with assertRaises(AttributeError):
            arrow.Arrow.utcnow().replace(abc=1)

    def test_replace_absolute(self):

        arw = arrow.Arrow(2013, 5, 5, 12, 30, 45)

        assertEqual(arw.replace(year=2012), arrow.Arrow(2012, 5, 5, 12, 30, 45))
        assertEqual(arw.replace(month=1), arrow.Arrow(2013, 1, 5, 12, 30, 45))
        assertEqual(arw.replace(day=1), arrow.Arrow(2013, 5, 1, 12, 30, 45))
        assertEqual(arw.replace(hour=1), arrow.Arrow(2013, 5, 5, 1, 30, 45))
        assertEqual(arw.replace(minute=1), arrow.Arrow(2013, 5, 5, 12, 1, 45))
        assertEqual(arw.replace(second=1), arrow.Arrow(2013, 5, 5, 12, 30, 1))

    def test_replace_relative(self):

        arw = arrow.Arrow(2013, 5, 5, 12, 30, 45)

        assertEqual(arw.replace(years=1), arrow.Arrow(2014, 5, 5, 12, 30, 45))
        assertEqual(arw.replace(months=1), arrow.Arrow(2013, 6, 5, 12, 30, 45))
        assertEqual(arw.replace(weeks=1), arrow.Arrow(2013, 5, 12, 12, 30, 45))
        assertEqual(arw.replace(days=1), arrow.Arrow(2013, 5, 6, 12, 30, 45))
        assertEqual(arw.replace(hours=1), arrow.Arrow(2013, 5, 5, 13, 30, 45))
        assertEqual(arw.replace(minutes=1), arrow.Arrow(2013, 5, 5, 12, 31, 45))
        assertEqual(arw.replace(seconds=1), arrow.Arrow(2013, 5, 5, 12, 30, 46))

    def test_replace_relative_negative(self):

        arw = arrow.Arrow(2013, 5, 5, 12, 30, 45)

        assertEqual(arw.replace(years=-1), arrow.Arrow(2012, 5, 5, 12, 30, 45))
        assertEqual(arw.replace(months=-1), arrow.Arrow(2013, 4, 5, 12, 30, 45))
        assertEqual(arw.replace(weeks=-1), arrow.Arrow(2013, 4, 28, 12, 30, 45))
        assertEqual(arw.replace(days=-1), arrow.Arrow(2013, 5, 4, 12, 30, 45))
        assertEqual(arw.replace(hours=-1), arrow.Arrow(2013, 5, 5, 11, 30, 45))
        assertEqual(arw.replace(minutes=-1), arrow.Arrow(2013, 5, 5, 12, 29, 45))
        assertEqual(arw.replace(seconds=-1), arrow.Arrow(2013, 5, 5, 12, 30, 44))
        assertEqual(arw.replace(microseconds=-1), arrow.Arrow(2013, 5, 5, 12, 30, 44, 999999))


    def test_replace_tzinfo(self):

        arw = arrow.Arrow.utcnow().to('US/Eastern')

        result = arw.replace(tzinfo=tz.gettz('US/Pacific'))

        assertEqual(result, arw.datetime.replace(tzinfo=tz.gettz('US/Pacific')))

    def test_replace_week(self):

        with assertRaises(AttributeError):
            arrow.Arrow.utcnow().replace(week=1)

    def test_replace_other_kwargs(self):

        with assertRaises(AttributeError):
            arrow.utcnow().replace(abc='def')


class ArrowRangeTests(Chai):

    def test_year(self):

        result = arrow.Arrow.range('year', datetime(2013, 1, 2, 3, 4, 5),
            datetime(2016, 4, 5, 6, 7, 8))

        assertEqual(result, [
            arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2014, 1, 2, 3, 4, 5),
            arrow.Arrow(2015, 1, 2, 3, 4, 5),
            arrow.Arrow(2016, 1, 2, 3, 4, 5),
        ])

    def test_month(self):

        result = arrow.Arrow.range('month', datetime(2013, 2, 3, 4, 5, 6),
            datetime(2013, 5, 6, 7, 8, 9))

        assertEqual(result, [
            arrow.Arrow(2013, 2, 3, 4, 5, 6),
            arrow.Arrow(2013, 3, 3, 4, 5, 6),
            arrow.Arrow(2013, 4, 3, 4, 5, 6),
            arrow.Arrow(2013, 5, 3, 4, 5, 6),
        ])

    def test_week(self):

        result = arrow.Arrow.range('week', datetime(2013, 9, 1, 2, 3, 4),
            datetime(2013, 10, 1, 2, 3, 4))

        assertEqual(result, [
            arrow.Arrow(2013, 9, 1, 2, 3, 4),
            arrow.Arrow(2013, 9, 8, 2, 3, 4),
            arrow.Arrow(2013, 9, 15, 2, 3, 4),
            arrow.Arrow(2013, 9, 22, 2, 3, 4),
            arrow.Arrow(2013, 9, 29, 2, 3, 4)
        ])

    def test_day(self):

        result = arrow.Arrow.range('day', datetime(2013, 1, 2, 3, 4, 5),
            datetime(2013, 1, 5, 6, 7, 8))

        assertEqual(result, [
            arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2013, 1, 3, 3, 4, 5),
            arrow.Arrow(2013, 1, 4, 3, 4, 5),
            arrow.Arrow(2013, 1, 5, 3, 4, 5),
        ])

    def test_hour(self):

        result = arrow.Arrow.range('hour', datetime(2013, 1, 2, 3, 4, 5),
            datetime(2013, 1, 2, 6, 7, 8))

        assertEqual(result, [
            arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2013, 1, 2, 4, 4, 5),
            arrow.Arrow(2013, 1, 2, 5, 4, 5),
            arrow.Arrow(2013, 1, 2, 6, 4, 5),
        ])

    def test_minute(self):

        result = arrow.Arrow.range('minute', datetime(2013, 1, 2, 3, 4, 5),
            datetime(2013, 1, 2, 3, 7, 8))

        assertEqual(result, [
            arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2013, 1, 2, 3, 5, 5),
            arrow.Arrow(2013, 1, 2, 3, 6, 5),
            arrow.Arrow(2013, 1, 2, 3, 7, 5),
        ])

    def test_second(self):

        result = arrow.Arrow.range('second', datetime(2013, 1, 2, 3, 4, 5),
            datetime(2013, 1, 2, 3, 4, 8))

        assertEqual(result, [
            arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2013, 1, 2, 3, 4, 6),
            arrow.Arrow(2013, 1, 2, 3, 4, 7),
            arrow.Arrow(2013, 1, 2, 3, 4, 8),
        ])

    def test_arrow(self):

        result = arrow.Arrow.range('day', arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2013, 1, 5, 6, 7, 8))

        assertEqual(result, [
            arrow.Arrow(2013, 1, 2, 3, 4, 5),
            arrow.Arrow(2013, 1, 3, 3, 4, 5),
            arrow.Arrow(2013, 1, 4, 3, 4, 5),
            arrow.Arrow(2013, 1, 5, 3, 4, 5),
        ])

    def test_naive_tz(self):

        result = arrow.Arrow.range('year', datetime(2013, 1, 2, 3), datetime(2016, 4, 5, 6),
            'US/Pacific')

        [assertEqual(r.tzinfo, tz.gettz('US/Pacific')) for r in result]

    def test_aware_same_tz(self):

        result = arrow.Arrow.range('day',
            arrow.Arrow(2013, 1, 1, tzinfo=tz.gettz('US/Pacific')),
            arrow.Arrow(2013, 1, 3, tzinfo=tz.gettz('US/Pacific')))

        [assertEqual(r.tzinfo, tz.gettz('US/Pacific')) for r in result]

    def test_aware_different_tz(self):

        result = arrow.Arrow.range('day',
            datetime(2013, 1, 1, tzinfo=tz.gettz('US/Eastern')),
            datetime(2013, 1, 3, tzinfo=tz.gettz('US/Pacific')))

        [assertEqual(r.tzinfo, tz.gettz('US/Eastern')) for r in result]

    def test_aware_tz(self):

        result = arrow.Arrow.range('day',
            datetime(2013, 1, 1, tzinfo=tz.gettz('US/Eastern')),
            datetime(2013, 1, 3, tzinfo=tz.gettz('US/Pacific')),
            tz=tz.gettz('US/Central'))

        [assertEqual(r.tzinfo, tz.gettz('US/Central')) for r in result]

    def test_unsupported(self):

        with assertRaises(AttributeError):
            arrow.Arrow.range('abc', datetime.utcnow(), datetime.utcnow())


class ArrowSpanRangeTests(Chai):

    def test_year(self):

        result = arrow.Arrow.span_range('year', datetime(2013, 2, 1), datetime(2016, 3, 31))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 1), arrow.Arrow(2013, 12, 31, 23, 59, 59, 999999)),
            (arrow.Arrow(2014, 1, 1), arrow.Arrow(2014, 12, 31, 23, 59, 59, 999999)),
            (arrow.Arrow(2015, 1, 1), arrow.Arrow(2015, 12, 31, 23, 59, 59, 999999)),
            (arrow.Arrow(2016, 1, 1), arrow.Arrow(2016, 12, 31, 23, 59, 59, 999999)),
        ])

    def test_month(self):

        result = arrow.Arrow.span_range('month', datetime(2013, 1, 2), datetime(2013, 4, 15))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 1), arrow.Arrow(2013, 1, 31, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 2, 1), arrow.Arrow(2013, 2, 28, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 3, 1), arrow.Arrow(2013, 3, 31, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 4, 1), arrow.Arrow(2013, 4, 30, 23, 59, 59, 999999)),
        ])

    def test_week(self):

        result = arrow.Arrow.span_range('week', datetime(2013, 2, 2), datetime(2013, 2, 28))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 28), arrow.Arrow(2013, 2, 3, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 2, 4), arrow.Arrow(2013, 2, 10, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 2, 11), arrow.Arrow(2013, 2, 17, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 2, 18), arrow.Arrow(2013, 2, 24, 23, 59, 59, 999999)),
        ])


    def test_day(self):

        result = arrow.Arrow.span_range('day', datetime(2013, 1, 1, 12),
            datetime(2013, 1, 4, 12))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 1, 0), arrow.Arrow(2013, 1, 1, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 1, 2, 0), arrow.Arrow(2013, 1, 2, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 1, 3, 0), arrow.Arrow(2013, 1, 3, 23, 59, 59, 999999)),
            (arrow.Arrow(2013, 1, 4, 0), arrow.Arrow(2013, 1, 4, 23, 59, 59, 999999)),
        ])

    def test_hour(self):

        result = arrow.Arrow.span_range('hour', datetime(2013, 1, 1, 0, 30),
            datetime(2013, 1, 1, 3, 30))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 1, 0), arrow.Arrow(2013, 1, 1, 0, 59, 59, 999999)),
            (arrow.Arrow(2013, 1, 1, 1), arrow.Arrow(2013, 1, 1, 1, 59, 59, 999999)),
            (arrow.Arrow(2013, 1, 1, 2), arrow.Arrow(2013, 1, 1, 2, 59, 59, 999999)),
            (arrow.Arrow(2013, 1, 1, 3), arrow.Arrow(2013, 1, 1, 3, 59, 59, 999999)),
        ])

    def test_minute(self):

        result = arrow.Arrow.span_range('minute', datetime(2013, 1, 1, 0, 0, 30),
            datetime(2013, 1, 1, 0, 3, 30))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 1, 0, 0), arrow.Arrow(2013, 1, 1, 0, 0, 59, 999999)),
            (arrow.Arrow(2013, 1, 1, 0, 1), arrow.Arrow(2013, 1, 1, 0, 1, 59, 999999)),
            (arrow.Arrow(2013, 1, 1, 0, 2), arrow.Arrow(2013, 1, 1, 0, 2, 59, 999999)),
            (arrow.Arrow(2013, 1, 1, 0, 3), arrow.Arrow(2013, 1, 1, 0, 3, 59, 999999)),
        ])

    def test_second(self):

        result = arrow.Arrow.span_range('second', datetime(2013, 1, 1),
            datetime(2013, 1, 1, 0, 0, 3))

        assertEqual(result, [
            (arrow.Arrow(2013, 1, 1, 0, 0, 0), arrow.Arrow(2013, 1, 1, 0, 0, 0, 999999)),
            (arrow.Arrow(2013, 1, 1, 0, 0, 1), arrow.Arrow(2013, 1, 1, 0, 0, 1, 999999)),
            (arrow.Arrow(2013, 1, 1, 0, 0, 2), arrow.Arrow(2013, 1, 1, 0, 0, 2, 999999)),
            (arrow.Arrow(2013, 1, 1, 0, 0, 3), arrow.Arrow(2013, 1, 1, 0, 0, 3, 999999)),
        ])

    def test_naive_tz(self):

        tzinfo = tz.gettz('US/Pacific')

        result = arrow.Arrow.span_range('hour', datetime(2013, 1, 1, 0),
            datetime(2013, 1, 1, 3, 59), 'US/Pacific')

        for f, c in result:
            assertEqual(f.tzinfo, tzinfo)
            assertEqual(c.tzinfo, tzinfo)

    def test_aware_same_tz(self):

        tzinfo = tz.gettz('US/Pacific')

        result = arrow.Arrow.span_range('hour', datetime(2013, 1, 1, 0, tzinfo=tzinfo),
            datetime(2013, 1, 1, 2, 59, tzinfo=tzinfo))

        for f, c in result:
            assertEqual(f.tzinfo, tzinfo)
            assertEqual(c.tzinfo, tzinfo)

    def test_aware_different_tz(self):

        tzinfo1 = tz.gettz('US/Pacific')
        tzinfo2 = tz.gettz('US/Eastern')

        result = arrow.Arrow.span_range('hour', datetime(2013, 1, 1, 0, tzinfo=tzinfo1),
            datetime(2013, 1, 1, 2, 59, tzinfo=tzinfo2))

        for f, c in result:
            assertEqual(f.tzinfo, tzinfo1)
            assertEqual(c.tzinfo, tzinfo1)

    def test_aware_tz(self):

        result = arrow.Arrow.span_range('hour',
            datetime(2013, 1, 1, 0, tzinfo=tz.gettz('US/Eastern')),
            datetime(2013, 1, 1, 2, 59, tzinfo=tz.gettz('US/Eastern')),
            tz='US/Central')

        for f, c in result:
            assertEqual(f.tzinfo, tz.gettz('US/Central'))
            assertEqual(c.tzinfo, tz.gettz('US/Central'))


class ArrowSpanTests(Chai):

    def setUp(self):
        super(ArrowSpanTests, self).setUp()

        self.datetime = datetime(2013, 2, 15, 3, 41, 22, 8923)
        self.arrow = arrow.Arrow.fromdatetime(self.datetime)

    def test_span_attribute(self):

        with assertRaises(AttributeError):
            self.arrow.span('span')

    def test_span_year(self):

        floor, ceil = self.arrow.span('year')

        assertEqual(floor, datetime(2013, 1, 1, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 12, 31, 23, 59, 59, 999999, tzinfo=tz.tzutc()))

    def test_span_month(self):

        floor, ceil = self.arrow.span('month')

        assertEqual(floor, datetime(2013, 2, 1, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 28, 23, 59, 59, 999999, tzinfo=tz.tzutc()))

    def test_span_week(self):

        floor, ceil = self.arrow.span('week')

        assertEqual(floor, datetime(2013, 2, 11, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 17, 23, 59, 59, 999999, tzinfo=tz.tzutc()))

    def test_span_day(self):

        floor, ceil = self.arrow.span('day')

        assertEqual(floor, datetime(2013, 2, 15, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 15, 23, 59, 59, 999999, tzinfo=tz.tzutc()))

    def test_span_hour(self):

        floor, ceil = self.arrow.span('hour')

        assertEqual(floor, datetime(2013, 2, 15, 3, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 15, 3, 59, 59, 999999, tzinfo=tz.tzutc()))

    def test_span_minute(self):

        floor, ceil = self.arrow.span('minute')

        assertEqual(floor, datetime(2013, 2, 15, 3, 41, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 15, 3, 41, 59, 999999, tzinfo=tz.tzutc()))

    def test_span_second(self):

        floor, ceil = self.arrow.span('second')

        assertEqual(floor, datetime(2013, 2, 15, 3, 41, 22, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 15, 3, 41, 22, 999999, tzinfo=tz.tzutc()))

    def test_span_hour(self):

        floor, ceil = self.arrow.span('microsecond')

        assertEqual(floor, datetime(2013, 2, 15, 3, 41, 22, 8923, tzinfo=tz.tzutc()))
        assertEqual(ceil, datetime(2013, 2, 15, 3, 41, 22, 8923, tzinfo=tz.tzutc()))

    def test_floor(self):

        floor, ceil = self.arrow.span('month')

        assertEqual(floor, self.arrow.floor('month'))
        assertEqual(ceil, self.arrow.ceil('month'))


class ArrowHumanizeTests(Chai):

    def setUp(self):
        super(ArrowHumanizeTests, self).setUp()

        self.datetime = datetime(2013, 1, 1)
        self.now = arrow.Arrow.utcnow()

    def test_seconds(self):

        later = self.now.replace(seconds=10)

        assertEqual(self.now.humanize(later), 'seconds ago')
        assertEqual(later.humanize(self.now), 'in seconds')

    def test_minute(self):

        later = self.now.replace(minutes=1)

        assertEqual(self.now.humanize(later), 'a minute ago')
        assertEqual(later.humanize(self.now), 'in a minute')

    def test_minutes(self):

        later = self.now.replace(minutes=2)

        assertEqual(self.now.humanize(later), '2 minutes ago')
        assertEqual(later.humanize(self.now), 'in 2 minutes')

    def test_hour(self):

        later = self.now.replace(hours=1)

        assertEqual(self.now.humanize(later), 'an hour ago')
        assertEqual(later.humanize(self.now), 'in an hour')

    def test_hours(self):

        later = self.now.replace(hours=2)

        assertEqual(self.now.humanize(later), '2 hours ago')
        assertEqual(later.humanize(self.now), 'in 2 hours')

    def test_day(self):

        later = self.now.replace(days=1)

        assertEqual(self.now.humanize(later), 'a day ago')
        assertEqual(later.humanize(self.now), 'in a day')

    def test_days(self):

        later = self.now.replace(days=2)

        assertEqual(self.now.humanize(later), '2 days ago')
        assertEqual(later.humanize(self.now), 'in 2 days')

    def test_month(self):

        later = self.now.replace(months=1)

        assertEqual(self.now.humanize(later), 'a month ago')
        assertEqual(later.humanize(self.now), 'in a month')

    def test_months(self):

        later = self.now.replace(months=2)

        assertEqual(self.now.humanize(later), '2 months ago')
        assertEqual(later.humanize(self.now), 'in 2 months')

    def test_year(self):

        later = self.now.replace(years=1)

        assertEqual(self.now.humanize(later), 'a year ago')
        assertEqual(later.humanize(self.now), 'in a year')

    def test_years(self):

        later = self.now.replace(years=2)

        assertEqual(self.now.humanize(later), '2 years ago')
        assertEqual(later.humanize(self.now), 'in 2 years')

        arw = arrow.Arrow(2014, 7, 2)

        result = arw.humanize(self.datetime)

        assertEqual(result, 'in 2 years')

    def test_arrow(self):

        arw = arrow.Arrow.fromdatetime(self.datetime)

        result = arw.humanize(arrow.Arrow.fromdatetime(self.datetime))

        assertEqual(result, 'just now')

    def test_datetime_tzinfo(self):

        arw = arrow.Arrow.fromdatetime(self.datetime)

        result = arw.humanize(self.datetime.replace(tzinfo=tz.tzutc()))

        assertEqual(result, 'just now')

    def test_other(self):

        arw = arrow.Arrow.fromdatetime(self.datetime)

        with assertRaises(TypeError):
            arw.humanize(object())

    def test_invalid_locale(self):

        arw = arrow.Arrow.fromdatetime(self.datetime)

        with assertRaises(ValueError):
            arw.humanize(locale='klingon')

    def test_none(self):

        arw = arrow.Arrow.utcnow()

        result = arw.humanize()

        assertEqual(result, 'just now')


class ArrowHumanizeTestsWithLocale(Chai):

    def setUp(self):
        super(ArrowHumanizeTestsWithLocale, self).setUp()

        self.datetime = datetime(2013, 1, 1)

    def test_now(self):

        arw = arrow.Arrow(2013, 1, 1, 0, 0, 0)

        result = arw.humanize(self.datetime, locale='ru')

        assertEqual(result, 'сейчас')

    def test_seconds(self):
        arw = arrow.Arrow(2013, 1, 1, 0, 0, 44)

        result = arw.humanize(self.datetime, locale='ru')

        assertEqual(result, 'через несколько секунд')

    def test_years(self):

        arw = arrow.Arrow(2011, 7, 2)

        result = arw.humanize(self.datetime, locale='ru')

        assertEqual(result, '2 года назад')


class ArrowUtilTests(Chai):

    def test_get_datetime(self):

        get_datetime = arrow.Arrow._get_datetime

        arw = arrow.Arrow.utcnow()
        dt = datetime.utcnow()
        timestamp = time.time()

        assertEqual(get_datetime(arw), arw.datetime)
        assertEqual(get_datetime(dt), dt)
        assertEqual(get_datetime(timestamp), arrow.Arrow.utcfromtimestamp(timestamp).datetime)

        with assertRaises(ValueError):
            get_datetime('abc')

    def test_get_tzinfo(self):

        get_tzinfo = arrow.Arrow._get_tzinfo

        with assertRaises(ValueError):
            get_tzinfo('abc')

    def test_get_timestamp_from_input(self):

        assertEqual(arrow.Arrow._get_timestamp_from_input(123), 123)
        assertEqual(arrow.Arrow._get_timestamp_from_input(123.4), 123.4)
        assertEqual(arrow.Arrow._get_timestamp_from_input('123'), 123.0)
        assertEqual(arrow.Arrow._get_timestamp_from_input('123.4'), 123.4)

        with assertRaises(ValueError):
            arrow.Arrow._get_timestamp_from_input('abc')

    def test_get_iteration_params(self):

        assertEqual(arrow.Arrow._get_iteration_params('end', None), ('end', sys.maxsize))
        assertEqual(arrow.Arrow._get_iteration_params(None, 100), (arrow.Arrow.max, 100))

        with assertRaises(Exception):
            arrow.Arrow._get_iteration_params(None, None)


########NEW FILE########
__FILENAME__ = factory_tests
from chai import Chai
from datetime import datetime
from dateutil import tz
import time

from arrow import factory, util


def assertDtEqual(dt1, dt2, within=10):
    assertEqual(dt1.tzinfo, dt2.tzinfo)
    assertTrue(abs(util.total_seconds(dt1 - dt2)) < within)


class GetTests(Chai):

    def setUp(self):
        super(GetTests, self).setUp()

        self.factory = factory.ArrowFactory()

    def test_no_args(self):

        assertDtEqual(self.factory.get(), datetime.utcnow().replace(tzinfo=tz.tzutc()))

    def test_one_arg_non(self):

        assertDtEqual(self.factory.get(None), datetime.utcnow().replace(tzinfo=tz.tzutc()))

    def test_one_arg_timestamp(self):

        timestamp = 12345
        timestamp_dt = datetime.utcfromtimestamp(timestamp).replace(tzinfo=tz.tzutc())

        assertEqual(self.factory.get(timestamp), timestamp_dt)
        assertEqual(self.factory.get(str(timestamp)), timestamp_dt)

        timestamp = 123.45
        timestamp_dt = datetime.utcfromtimestamp(timestamp).replace(tzinfo=tz.tzutc())

        assertEqual(self.factory.get(timestamp), timestamp_dt)
        assertEqual(self.factory.get(str(timestamp)), timestamp_dt)

    def test_one_arg_arrow(self):

        arw = self.factory.utcnow()
        result = self.factory.get(arw)

        assertEqual(arw, result)

    def test_one_arg_datetime(self):

        dt = datetime.utcnow().replace(tzinfo=tz.tzutc())

        assertEqual(self.factory.get(dt), dt)

    def test_one_arg_tzinfo(self):

        expected = datetime.utcnow().replace(tzinfo=tz.tzutc()).astimezone(tz.gettz('US/Pacific'))

        assertDtEqual(self.factory.get(tz.gettz('US/Pacific')), expected)

    def test_one_arg_iso_str(self):

        dt = datetime.utcnow()

        assertDtEqual(self.factory.get(dt.isoformat()), dt.replace(tzinfo=tz.tzutc()))

    def test_one_arg_other(self):

        with assertRaises(TypeError):
            self.factory.get(object())

    def test_two_args_datetime_tzinfo(self):

        result = self.factory.get(datetime(2013, 1, 1), tz.gettz('US/Pacific'))

        assertEqual(result._datetime, datetime(2013, 1, 1, tzinfo=tz.gettz('US/Pacific')))

    def test_two_args_datetime_tz_str(self):

        result = self.factory.get(datetime(2013, 1, 1), 'US/Pacific')

        assertEqual(result._datetime, datetime(2013, 1, 1, tzinfo=tz.gettz('US/Pacific')))

    def test_two_args_datetime_other(self):

        with assertRaises(TypeError):
            self.factory.get(datetime.utcnow(), object())

    def test_two_args_str_str(self):

        result = self.factory.get('2013-01-01', 'YYYY-MM-DD')

        assertEqual(result._datetime, datetime(2013, 1, 1, tzinfo=tz.tzutc()))

    def test_two_args_str_list(self):

        result = self.factory.get('2013-01-01', ['MM/DD/YYYY', 'YYYY-MM-DD'])

        assertEqual(result._datetime, datetime(2013, 1, 1, tzinfo=tz.tzutc()))

    def test_two_args_unicode_unicode(self):

        result = self.factory.get(u'2013-01-01', u'YYYY-MM-DD')

        assertEqual(result._datetime, datetime(2013, 1, 1, tzinfo=tz.tzutc()))

    def test_two_args_other(self):

        with assertRaises(TypeError):
            self.factory.get(object(), object())

    def test_three_args(self):

        assertEqual(self.factory.get(2013, 1, 1), datetime(2013, 1, 1, tzinfo=tz.tzutc()))


def UtcNowTests(Chai):

    def test_utcnow(self):

        assertDtEqual(self.factory.utcnow()._datetime, datetime.utcnow().replace(tzinfo=tz.tzutc()))


class NowTests(Chai):

    def setUp(self):
        super(NowTests, self).setUp()

        self.factory = factory.ArrowFactory()

    def test_no_tz(self):

        assertDtEqual(self.factory.now(), datetime.now(tz.tzlocal()))

    def test_tzinfo(self):

        assertDtEqual(self.factory.now(tz.gettz('EST')), datetime.now(tz.gettz('EST')))

    def test_tz_str(self):

        assertDtEqual(self.factory.now('EST'), datetime.now(tz.gettz('EST')))


########NEW FILE########
__FILENAME__ = formatter_tests
from chai import Chai

from arrow import formatter

from datetime import datetime
from dateutil import tz as dateutil_tz
import time

class DateTimeFormatterFormatTokenTests(Chai):

    def setUp(self):
        super(DateTimeFormatterFormatTokenTests, self).setUp()

        self.formatter = formatter.DateTimeFormatter()

    def test_format(self):

        dt = datetime(2013, 2, 5, 12, 32, 51)

        result = self.formatter.format(dt, 'MM-DD-YYYY hh:mm:ss a')

        assertEqual(result, '02-05-2013 12:32:51 pm')

    def test_year(self):

        dt = datetime(2013, 1, 1)
        assertEqual(self.formatter._format_token(dt, 'YYYY'), '2013')
        assertEqual(self.formatter._format_token(dt, 'YY'), '13')

    def test_month(self):

        dt = datetime(2013, 1, 1)
        assertEqual(self.formatter._format_token(dt, 'MMMM'), 'January')
        assertEqual(self.formatter._format_token(dt, 'MMM'), 'Jan')
        assertEqual(self.formatter._format_token(dt, 'MM'), '01')
        assertEqual(self.formatter._format_token(dt, 'M'), '1')

    def test_day(self):

        dt = datetime(2013, 2, 1)
        assertEqual(self.formatter._format_token(dt, 'DDDD'), '032')
        assertEqual(self.formatter._format_token(dt, 'DDD'), '32')
        assertEqual(self.formatter._format_token(dt, 'DD'), '01')
        assertEqual(self.formatter._format_token(dt, 'D'), '1')

        assertEqual(self.formatter._format_token(dt, 'dddd'), 'Friday')
        assertEqual(self.formatter._format_token(dt, 'ddd'), 'Fri')
        assertEqual(self.formatter._format_token(dt, 'd'), '5')

    def test_hour(self):

        dt = datetime(2013, 1, 1, 2)
        assertEqual(self.formatter._format_token(dt, 'HH'), '02')
        assertEqual(self.formatter._format_token(dt, 'H'), '2')

        dt = datetime(2013, 1, 1, 13)
        assertEqual(self.formatter._format_token(dt, 'HH'), '13')
        assertEqual(self.formatter._format_token(dt, 'H'), '13')

        dt = datetime(2013, 1, 1, 2)
        assertEqual(self.formatter._format_token(dt, 'hh'), '02')
        assertEqual(self.formatter._format_token(dt, 'h'), '2')

        dt = datetime(2013, 1, 1, 13)
        assertEqual(self.formatter._format_token(dt, 'hh'), '01')
        assertEqual(self.formatter._format_token(dt, 'h'), '1')

        # test that 12-hour time converts to '12' at midnight
        dt = datetime(2013, 1, 1, 0)
        assertEqual(self.formatter._format_token(dt, 'hh'), '12')
        assertEqual(self.formatter._format_token(dt, 'h'), '12')

    def test_minute(self):

        dt = datetime(2013, 1, 1, 0, 1)
        assertEqual(self.formatter._format_token(dt, 'mm'), '01')
        assertEqual(self.formatter._format_token(dt, 'm'), '1')

    def test_second(self):

        dt = datetime(2013, 1, 1, 0, 0, 1)
        assertEqual(self.formatter._format_token(dt, 'ss'), '01')
        assertEqual(self.formatter._format_token(dt, 's'), '1')

    def test_sub_second(self):

        dt = datetime(2013, 1, 1, 0, 0, 0, 123456)
        assertEqual(self.formatter._format_token(dt, 'SSSSSS'), '123456')
        assertEqual(self.formatter._format_token(dt, 'SSSSS'), '12345')
        assertEqual(self.formatter._format_token(dt, 'SSSS'), '1234')
        assertEqual(self.formatter._format_token(dt, 'SSS'), '123')
        assertEqual(self.formatter._format_token(dt, 'SS'), '12')
        assertEqual(self.formatter._format_token(dt, 'S'), '1')

    def test_timestamp(self):

        timestamp = time.time()
        dt = datetime.utcfromtimestamp(timestamp)
        assertEqual(self.formatter._format_token(dt, 'X'), str(int(timestamp)))

    def test_timezone(self):

        dt = datetime.utcnow().replace(tzinfo=dateutil_tz.gettz('US/Pacific'))

        result = self.formatter._format_token(dt, 'ZZ')
        assertTrue(result == '-07:00' or result == '-08:00')

        result = self.formatter._format_token(dt, 'Z')
        assertTrue(result == '-0700' or result == '-0800')

    def test_am_pm(self):

        dt = datetime(2012, 1, 1, 11)
        assertEqual(self.formatter._format_token(dt, 'a'), 'am')
        assertEqual(self.formatter._format_token(dt, 'A'), 'AM')

        dt = datetime(2012, 1, 1, 13)
        assertEqual(self.formatter._format_token(dt, 'a'), 'pm')
        assertEqual(self.formatter._format_token(dt, 'A'), 'PM')





########NEW FILE########
__FILENAME__ = locales_tests
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from chai import Chai

from arrow import locales


class ModuleTests(Chai):

    def test_get_locale(self):

        mock_locales = mock(locales, '_locales')
        mock_locale_cls = mock()
        mock_locale = mock()

        expect(mock_locales.get).args('name').returns(mock_locale_cls)
        expect(mock_locale_cls).returns(mock_locale)

        result = locales.get_locale('name')

        assertEqual(result, mock_locale)

    def test_locales(self):

        assertTrue(len(locales._locales) > 0)


class LocaleTests(Chai):

    def setUp(self):
        super(LocaleTests, self).setUp()

        self.locale = locales.EnglishLocale()

    def test_format_timeframe(self):

        assertEqual(self.locale._format_timeframe('hours', 2), '2 hours')
        assertEqual(self.locale._format_timeframe('hour', 0), 'an hour')

    def test_format_relative_now(self):

        result = self.locale._format_relative('just now', 'now', 0)

        assertEqual(result, 'just now')

    def test_format_relative_past(self):

        result = self.locale._format_relative('an hour', 'hour', 1)

        assertEqual(result, 'in an hour')

    def test_format_relative_future(self):

        result = self.locale._format_relative('an hour', 'hour', -1)

        assertEqual(result, 'an hour ago')


class RussianLocalesTests(Chai):

    def test_plurals2(self):

        locale = locales.RussianLocale()

        assertEqual(locale._format_timeframe('hours', 0), '0 часов')
        assertEqual(locale._format_timeframe('hours', 1), '1 час')
        assertEqual(locale._format_timeframe('hours', 2), '2 часа')
        assertEqual(locale._format_timeframe('hours', 4), '4 часа')
        assertEqual(locale._format_timeframe('hours', 5), '5 часов')
        assertEqual(locale._format_timeframe('hours', 21), '21 час')
        assertEqual(locale._format_timeframe('hours', 22), '22 часа')
        assertEqual(locale._format_timeframe('hours', 25), '25 часов')

        # feminine grammatical gender should be tested separately
        assertEqual(locale._format_timeframe('minutes', 0), '0 минут')
        assertEqual(locale._format_timeframe('minutes', 1), '1 минуту')
        assertEqual(locale._format_timeframe('minutes', 2), '2 минуты')
        assertEqual(locale._format_timeframe('minutes', 4), '4 минуты')
        assertEqual(locale._format_timeframe('minutes', 5), '5 минут')
        assertEqual(locale._format_timeframe('minutes', 21), '21 минуту')
        assertEqual(locale._format_timeframe('minutes', 22), '22 минуты')
        assertEqual(locale._format_timeframe('minutes', 25), '25 минут')


class PolishLocalesTests(Chai):

    def test_plurals(self):

        locale = locales.PolishLocale()

        assertEqual(locale._format_timeframe('hours', 0), '0 godzin')
        assertEqual(locale._format_timeframe('hours', 1), '1 godzin')
        assertEqual(locale._format_timeframe('hours', 2), '2 godziny')
        assertEqual(locale._format_timeframe('hours', 4), '4 godziny')
        assertEqual(locale._format_timeframe('hours', 5), '5 godzin')
        assertEqual(locale._format_timeframe('hours', 21), '21 godzin')
        assertEqual(locale._format_timeframe('hours', 22), '22 godziny')
        assertEqual(locale._format_timeframe('hours', 25), '25 godzin')


class IcelandicLocalesTests(Chai):

    def setUp(self):
        super(IcelandicLocalesTests, self).setUp()

        self.locale = locales.IcelandicLocale()

    def test_format_timeframe(self):

        assertEqual(self.locale._format_timeframe('minute', -1), 'einni mínútu')
        assertEqual(self.locale._format_timeframe('minute', 1), 'eina mínútu')

        assertEqual(self.locale._format_timeframe('hours', -2), '2 tímum')
        assertEqual(self.locale._format_timeframe('hours', 2), '2 tíma')

########NEW FILE########
__FILENAME__ = parser_tests
from chai import Chai
from datetime import datetime
from dateutil import tz
import calendar
import time

from arrow import parser

class DateTimeParserTests(Chai):

    def setUp(self):
        super(DateTimeParserTests, self).setUp()

        self.parser = parser.DateTimeParser()

    def test_parse_multiformat(self):

        mock_datetime = mock()

        expect(self.parser.parse).args('str', 'fmt_a').raises(Exception)
        expect(self.parser.parse).args('str', 'fmt_b').returns(mock_datetime)

        result = self.parser._parse_multiformat('str', ['fmt_a', 'fmt_b'])

        assertEqual(result, mock_datetime)

    def test_parse_multiformat_all_fail(self):

        expect(self.parser.parse).args('str', 'fmt_a').raises(Exception)
        expect(self.parser.parse).args('str', 'fmt_b').raises(Exception)

        with assertRaises(Exception):
            self.parser._parse_multiformat('str', ['fmt_a', 'fmt_b'])


class DateTimeParserParseTests(Chai):

    def setUp(self):
        super(DateTimeParserParseTests, self).setUp()

        self.parser = parser.DateTimeParser()

    def test_parse_list(self):

        expect(self.parser._parse_multiformat).args('str', ['fmt_a', 'fmt_b']).returns('result')

        result = self.parser.parse('str', ['fmt_a', 'fmt_b'])

        assertEqual(result, 'result')

    def test_parse_unrecognized_token(self):

        mock_input_re_map = mock(parser.DateTimeParser, '_INPUT_RE_MAP')

        expect(mock_input_re_map.__getitem__).args('YYYY').raises(KeyError)

        with assertRaises(parser.ParserError):
            self.parser.parse('2013-01-01', 'YYYY-MM-DD')

    def test_parse_parse_no_match(self):

        with assertRaises(parser.ParserError):
            self.parser.parse('01-01', 'YYYY-MM-DD')

    def test_parse_numbers(self):

        expected = datetime(2012, 1, 1, 12, 5, 10)
        assertEqual(self.parser.parse('2012-01-01 12:05:10', 'YYYY-MM-DD HH:mm:ss'), expected)

    def test_parse_year_two_digit(self):

        expected = datetime(1979, 1, 1, 12, 5, 10)
        assertEqual(self.parser.parse('79-01-01 12:05:10', 'YY-MM-DD HH:mm:ss'), expected)

    def test_parse_timestamp(self):

        timestamp = int(time.time())
        expected = datetime.fromtimestamp(timestamp)
        assertEqual(self.parser.parse(str(timestamp), 'X'), expected)

    def test_parse_names(self):

        expected = datetime(2012, 1, 1)

        assertEqual(self.parser.parse('January 1, 2012', 'MMMM D, YYYY'), expected)
        assertEqual(self.parser.parse('Jan 1, 2012', 'MMM D, YYYY'), expected)

    def test_parse_pm(self):

        expected = datetime(1, 1, 1, 13, 0, 0)
        assertEqual(self.parser.parse('1 pm', 'H a'), expected)

        expected = datetime(1, 1, 1, 1, 0, 0)
        assertEqual(self.parser.parse('1 am', 'H A'), expected)

        expected = datetime(1, 1, 1, 0, 0, 0)
        assertEqual(self.parser.parse('12 am', 'H A'), expected)

        expected = datetime(1, 1, 1, 12, 0, 0)
        assertEqual(self.parser.parse('12 pm', 'H A'), expected)

    def test_parse_tz(self):

        expected = datetime(2013, 1, 1, tzinfo=tz.tzoffset(None, -7 * 3600))
        assertEqual(self.parser.parse('2013-01-01 -07:00', 'YYYY-MM-DD ZZ'), expected)

    def test_parse_subsecond(self):

        expected = datetime(2013, 1, 1, 12, 30, 45, 900000)
        assertEqual(self.parser.parse('2013-01-01 12:30:45:9', 'YYYY-MM-DD HH:mm:ss:S'), expected)

        expected = datetime(2013, 1, 1, 12, 30, 45, 990000)
        assertEqual(self.parser.parse('2013-01-01 12:30:45:99', 'YYYY-MM-DD HH:mm:ss:SS'), expected)

        expected = datetime(2013, 1, 1, 12, 30, 45, 999000)
        assertEqual(self.parser.parse('2013-01-01 12:30:45:999', 'YYYY-MM-DD HH:mm:ss:SSS'), expected)

        expected = datetime(2013, 1, 1, 12, 30, 45, 999900)
        assertEqual(self.parser.parse('2013-01-01 12:30:45:9999', 'YYYY-MM-DD HH:mm:ss:SSSS'), expected)

        expected = datetime(2013, 1, 1, 12, 30, 45, 999990)
        assertEqual(self.parser.parse('2013-01-01 12:30:45:99999', 'YYYY-MM-DD HH:mm:ss:SSSSS'), expected)

        expected = datetime(2013, 1, 1, 12, 30, 45, 999999)
        assertEqual(self.parser.parse('2013-01-01 12:30:45:999999', 'YYYY-MM-DD HH:mm:ss:SSSSSS'), expected)

    def test_map_lookup_keyerror(self):

        with assertRaises(parser.ParserError):
            parser.DateTimeParser._map_lookup({'a': '1'}, 'b')

    def test_try_timestamp(self):

        assertEqual(parser.DateTimeParser._try_timestamp('1.1'), 1.1)
        assertEqual(parser.DateTimeParser._try_timestamp('1'), 1)
        assertEqual(parser.DateTimeParser._try_timestamp('abc'), None)


class DateTimeParserRegexTests(Chai):

    def setUp(self):
        super(DateTimeParserRegexTests, self).setUp()

        self.format_regex = parser.DateTimeParser._FORMAT_RE

    def test_format_year(self):

        assertEqual(self.format_regex.findall('YYYY-YY'), ['YYYY', 'YY'])

    def test_format_month(self):

        assertEqual(self.format_regex.findall('MMMM-MMM-MM-M'), ['MMMM', 'MMM', 'MM', 'M'])

    def test_format_day(self):

        assertEqual(self.format_regex.findall('DDDD-DDD-DD-D'), ['DDDD', 'DDD', 'DD', 'D'])

    def test_format_hour(self):

        assertEqual(self.format_regex.findall('HH-H-hh-h'), ['HH', 'H', 'hh', 'h'])

    def test_format_minute(self):

        assertEqual(self.format_regex.findall('mm-m'), ['mm', 'm'])

    def test_format_second(self):

        assertEqual(self.format_regex.findall('ss-s'), ['ss', 's'])

    def test_format_subsecond(self):

        assertEqual(self.format_regex.findall('SSSSSS-SSSSS-SSSS-SSS-SS-S'),
                ['SSSSSS', 'SSSSS', 'SSSS', 'SSS', 'SS', 'S'])

    def test_format_tz(self):

        assertEqual(self.format_regex.findall('ZZ-Z'), ['ZZ', 'Z'])

    def test_format_am_pm(self):

        assertEqual(self.format_regex.findall('A-a'), ['A', 'a'])

    def test_format_timestamp(self):

        assertEqual(self.format_regex.findall('X'), ['X'])

    def test_month_names(self):

        text = '_'.join(calendar.month_name[1:])

        result = parser.DateTimeParser._INPUT_RE_MAP['MMMM'].findall(text)

        assertEqual(result, calendar.month_name[1:])

    def test_month_abbreviations(self):

        text = '_'.join(calendar.month_abbr[1:])

        result = parser.DateTimeParser._INPUT_RE_MAP['MMM'].findall(text)

        assertEqual(result, calendar.month_abbr[1:])

    def test_digits(self):

        assertEqual(parser.DateTimeParser._TWO_DIGIT_RE.findall('12-3-45'), ['12', '45'])
        assertEqual(parser.DateTimeParser._FOUR_DIGIT_RE.findall('1234-56'), ['1234'])
        assertEqual(parser.DateTimeParser._ONE_OR_TWO_DIGIT_RE.findall('4-56'), ['4', '56'])


class DateTimeParserISOTests(Chai):

    def setUp(self):
        super(DateTimeParserISOTests, self).setUp()

        self.parser = parser.DateTimeParser('en_us')

    def test_YYYY(self):

        assertEqual(
            self.parser.parse_iso('2013'),
            datetime(2013, 1, 1)
        )

    def test_YYYY_MM(self):

        assertEqual(
            self.parser.parse_iso('2013-02'),
            datetime(2013, 2, 1)
        )

    def test_YYYY_MM_DD(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03'),
            datetime(2013, 2, 3)
        )

    def test_YYYY_MM_DDTHH_mmZ(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05+01:00'),
            datetime(2013, 2, 3, 4, 5, tzinfo=tz.tzoffset(None, 3600))
        )

    def test_YYYY_MM_DDTHH_mm(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05'),
            datetime(2013, 2, 3, 4, 5)
        )

    def test_YYYY_MM_DDTHH_mm_ssZ(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06+01:00'),
            datetime(2013, 2, 3, 4, 5, 6, tzinfo=tz.tzoffset(None, 3600))
        )

    def test_YYYY_MM_DDTHH_mm_ss(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06'),
            datetime(2013, 2, 3, 4, 5, 6)
        )

    def test_YYYY_MM_DDTHH_mm_ss_S(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.7'),
            datetime(2013, 2, 3, 4, 5, 6, 7)
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.78'),
            datetime(2013, 2, 3, 4, 5, 6, 78)
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.789'),
            datetime(2013, 2, 3, 4, 5, 6, 789)
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.7891'),
            datetime(2013, 2, 3, 4, 5, 6, 7891)
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.78912'),
            datetime(2013, 2, 3, 4, 5, 6, 78912)
        )

    def test_YYYY_MM_DDTHH_mm_ss_SZ(self):

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.7+01:00'),
            datetime(2013, 2, 3, 4, 5, 6, 7, tzinfo=tz.tzoffset(None, 3600))
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.78+01:00'),
            datetime(2013, 2, 3, 4, 5, 6, 78, tzinfo=tz.tzoffset(None, 3600))
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.789+01:00'),
            datetime(2013, 2, 3, 4, 5, 6, 789, tzinfo=tz.tzoffset(None, 3600))
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.7891+01:00'),
            datetime(2013, 2, 3, 4, 5, 6, 7891, tzinfo=tz.tzoffset(None, 3600))
        )

        assertEqual(
            self.parser.parse_iso('2013-02-03T04:05:06.78912+01:00'),
            datetime(2013, 2, 3, 4, 5, 6, 78912, tzinfo=tz.tzoffset(None, 3600))
        )

    def test_isoformat(self):

        dt = datetime.utcnow()

        assertEqual(self.parser.parse_iso(dt.isoformat()), dt)


class TzinfoParserTests(Chai):

    def setUp(self):
        super(TzinfoParserTests, self).setUp()

        self.parser = parser.TzinfoParser()

    def test_parse_local(self):

        assertEqual(self.parser.parse('local'), tz.tzlocal())

    def test_parse_utc(self):

        assertEqual(self.parser.parse('utc'), tz.tzutc())
        assertEqual(self.parser.parse('UTC'), tz.tzutc())

    def test_parse_iso(self):

        assertEqual(self.parser.parse('01:00'), tz.tzoffset(None, 3600))
        assertEqual(self.parser.parse('+01:00'), tz.tzoffset(None, 3600))
        assertEqual(self.parser.parse('-01:00'), tz.tzoffset(None, -3600))

    def test_parse_str(self):

        assertEqual(self.parser.parse('US/Pacific'), tz.gettz('US/Pacific'))

    def test_parse_fails(self):

        with assertRaises(parser.ParserError):
            self.parser.parse('fail')

########NEW FILE########
__FILENAME__ = util_tests
# -*- coding: utf-8 -*-

from chai import Chai
from datetime import timedelta
import sys

from arrow import util


class UtilTests(Chai):

    def setUp(self):
        super(UtilTests, self).setUp()

    def test_total_seconds_26(self):

        td = timedelta(seconds=30)

        assertEqual(util._total_seconds_26(td), 30)

    if util.version >= '2.7':

        def test_total_seconds_27(self):

            td = timedelta(seconds=30)

            assertEqual(util._total_seconds_27(td), 30)


########NEW FILE########
