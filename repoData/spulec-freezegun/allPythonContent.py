__FILENAME__ = api
import time
import datetime
import functools
import sys
import inspect
import unittest

from dateutil import parser

real_time = time.time
real_date = datetime.date
real_datetime = datetime.datetime


# Stolen from six
def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})


class FakeTime(object):

    def __init__(self, time_to_freeze):
        self.time_to_freeze = time_to_freeze

    def __call__(self):
        shifted_time = self.time_to_freeze - datetime.timedelta(seconds=time.timezone)
        return time.mktime(shifted_time.timetuple()) + shifted_time.microsecond / 1000000.0


class FakeDateMeta(type):
    @classmethod
    def __instancecheck__(self, obj):
        return isinstance(obj, real_date)


def datetime_to_fakedatetime(datetime):
    return FakeDatetime(datetime.year,
                        datetime.month,
                        datetime.day,
                        datetime.hour,
                        datetime.minute,
                        datetime.second,
                        datetime.microsecond,
                        datetime.tzinfo)


def date_to_fakedate(date):
    return FakeDate(date.year,
                    date.month,
                    date.day)


class FakeDate(with_metaclass(FakeDateMeta, real_date)):
    date_to_freeze = None

    def __new__(cls, *args, **kwargs):
        return real_date.__new__(cls, *args, **kwargs)

    def __add__(self, other):
        result = real_date.__add__(self, other)
        if result is NotImplemented:
            return result
        return date_to_fakedate(result)

    def __sub__(self, other):
        result = real_date.__sub__(self, other)
        if result is NotImplemented:
            return result
        if isinstance(result, real_date):
            return date_to_fakedate(result)
        else:
            return result

    @classmethod
    def today(cls):
        result = cls.date_to_freeze
        return date_to_fakedate(result)

FakeDate.min = date_to_fakedate(real_date.min)
FakeDate.max = date_to_fakedate(real_date.max)


class FakeDatetimeMeta(FakeDateMeta):
    @classmethod
    def __instancecheck__(self, obj):
        return isinstance(obj, real_datetime)


class FakeDatetime(with_metaclass(FakeDatetimeMeta, real_datetime, FakeDate)):
    time_to_freeze = None
    tz_offset = None

    def __new__(cls, *args, **kwargs):
        return real_datetime.__new__(cls, *args, **kwargs)

    def __add__(self, other):
        result = real_datetime.__add__(self, other)
        if result is NotImplemented:
            return result
        return datetime_to_fakedatetime(result)

    def __sub__(self, other):
        result = real_datetime.__sub__(self, other)
        if result is NotImplemented:
            return result
        if isinstance(result, real_datetime):
            return datetime_to_fakedatetime(result)
        else:
            return result

    @classmethod
    def now(cls, tz=None):
        if tz:
            result = tz.fromutc(cls.time_to_freeze.replace(tzinfo=tz)) + datetime.timedelta(hours=cls.tz_offset)
        else:
            result = cls.time_to_freeze + datetime.timedelta(hours=cls.tz_offset)
        return datetime_to_fakedatetime(result)

    @classmethod
    def utcnow(cls):
        result = cls.time_to_freeze
        return datetime_to_fakedatetime(result)

FakeDatetime.min = datetime_to_fakedatetime(real_datetime.min)
FakeDatetime.max = datetime_to_fakedatetime(real_datetime.max)


class FreezeMixin(object):
    """
    With unittest.TestCase subclasses, we must return the class from our
    freeze_time decorator, else test discovery tools may not discover the
    test. Instead, we inject this mixin, which starts and stops the freezer
    before and after each test.
    """
    def setUp(self):
        self._freezer.start()
        super(FreezeMixin, self).setUp()

    def tearDown(self):
        super(FreezeMixin, self).tearDown()
        self._freezer.stop()

class _freeze_time(object):

    def __init__(self, time_to_freeze_str, tz_offset):
        time_to_freeze = parser.parse(time_to_freeze_str)

        self.time_to_freeze = time_to_freeze
        self.tz_offset = tz_offset

    def __call__(self, func):
        if inspect.isclass(func) and issubclass(func, unittest.TestCase):
            # Inject a mixin that does what we want, as otherwise we
            # would not be found by the test discovery tool.
            func.__bases__ = (FreezeMixin,) + func.__bases__
            # And, we need a reference to this object...
            func._freezer = self
            return func
        return self.decorate_callable(func)

    def __enter__(self):
        self.start()

    def __exit__(self, *args):
        self.stop()

    def start(self):
        datetime.datetime = FakeDatetime
        datetime.date = FakeDate
        fake_time = FakeTime(self.time_to_freeze)
        time.time = fake_time

        for mod_name, module in list(sys.modules.items()):
            if module is None:
                continue
            if mod_name.startswith(('six.moves.', 'django.utils.six.moves.')):
                continue
            if hasattr(module, "__name__") and module.__name__ != 'datetime':
                if hasattr(module, 'datetime') and module.datetime == real_datetime:
                    module.datetime = FakeDatetime
                if hasattr(module, 'date') and module.date == real_date:
                    module.date = FakeDate
            if hasattr(module, "__name__") and module.__name__ != 'time':
                if hasattr(module, 'time') and module.time == real_time:
                    module.time = fake_time

        datetime.datetime.time_to_freeze = self.time_to_freeze
        datetime.datetime.tz_offset = self.tz_offset

        # Since datetime.datetime has already been mocked, just use that for
        # calculating the date
        datetime.date.date_to_freeze = datetime.datetime.now().date()

    def stop(self):
        datetime.datetime = real_datetime
        datetime.date = real_date
        time.time = real_time

        for mod_name, module in list(sys.modules.items()):
            if mod_name.startswith(('six.moves.', 'django.utils.six.moves.')):
                continue
            if mod_name != 'datetime':
                if hasattr(module, 'datetime') and module.datetime == FakeDatetime:
                    module.datetime = real_datetime
                if hasattr(module, 'date') and module.date == FakeDate:
                    module.date = real_date
            if mod_name != 'time':
                if hasattr(module, 'time') and isinstance(module.time, FakeTime):
                    module.time = real_time

    def decorate_callable(self, func):
        def wrapper(*args, **kwargs):
            with self:
                result = func(*args, **kwargs)
            return result
        functools.update_wrapper(wrapper, func)
        return wrapper


def freeze_time(time_to_freeze, tz_offset=0):
    if isinstance(time_to_freeze, datetime.datetime):
        time_to_freeze = time_to_freeze.isoformat()
    elif isinstance(time_to_freeze, datetime.date):
        time_to_freeze = time_to_freeze.isoformat()

    # Python3 doesn't have basestring, but it does have str.
    try:
        string_type = basestring
    except NameError:
        string_type = str

    if not isinstance(time_to_freeze, string_type):
        raise TypeError(('freeze_time() expected a string, date instance, or '
                         'datetime instance, but got type {0}.').format(type(time_to_freeze)))

    return _freeze_time(time_to_freeze, tz_offset)


# Setup adapters for sqlite
try:
    import sqlite3
except ImportError:
    # Some systems have trouble with this
    pass
else:
    # These are copied from Python sqlite3.dbapi2
    def adapt_date(val):
        return val.isoformat()


    def adapt_datetime(val):
        return val.isoformat(" ")

    sqlite3.register_adapter(FakeDate, adapt_date)
    sqlite3.register_adapter(FakeDatetime, adapt_datetime)

########NEW FILE########
__FILENAME__ = fake_module
from datetime import datetime
from datetime import date
from time import time


def fake_datetime_function():
    return datetime.now()


def fake_date_function():
    return date.today()


def fake_time_function():
    return time()

########NEW FILE########
__FILENAME__ = test_class_import
import sure
import time
from .fake_module import fake_datetime_function, fake_date_function, fake_time_function
from freezegun import freeze_time
from freezegun.api import FakeDatetime
import datetime



@freeze_time("2012-01-14")
def test_import_datetime_works():
    fake_datetime_function().day.should.equal(14)


@freeze_time("2012-01-14")
def test_import_date_works():
    fake_date_function().day.should.equal(14)


@freeze_time("2012-01-14")
def test_import_time():
    local_time = datetime.datetime(2012, 1, 14)
    utc_time = local_time - datetime.timedelta(seconds=time.timezone)
    expected_timestamp = time.mktime(utc_time.timetuple())
    fake_time_function().should.equal(expected_timestamp)


def test_start_and_stop_works():
    freezer = freeze_time("2012-01-14")

    result = fake_datetime_function()
    result.__class__.should.equal(datetime.datetime)
    result.__class__.shouldnt.equal(FakeDatetime)

    freezer.start()
    fake_datetime_function().day.should.equal(14)
    fake_datetime_function().should.be.a(datetime.datetime)
    fake_datetime_function().should.be.a(FakeDatetime)

    freezer.stop()
    result = fake_datetime_function()
    result.__class__.should.equal(datetime.datetime)
    result.__class__.shouldnt.equal(FakeDatetime)


def test_isinstance_works():
    date = datetime.date.today()
    now = datetime.datetime.now()

    freezer = freeze_time('2011-01-01')
    freezer.start()
    isinstance(date, datetime.date).should.equal(True)
    isinstance(date, datetime.datetime).should.equal(False)
    isinstance(now, datetime.datetime).should.equal(True)
    isinstance(now, datetime.date).should.equal(True)
    freezer.stop()

########NEW FILE########
__FILENAME__ = test_datetimes
import pickle
import time
import datetime
import unittest
import locale

from nose.plugins import skip

from freezegun import freeze_time
from freezegun.api import FakeDatetime, FakeDate, real_datetime, real_date


class temp_locale(object):
    """Temporarily change the locale."""

    def __init__(self, *targets):
        self.targets = targets

    def __enter__(self):
        self.old = locale.setlocale(locale.LC_ALL)
        for target in self.targets:
            try:
                locale.setlocale(locale.LC_ALL, target)
                return
            except locale.Error:
                pass
        msg = 'could not set locale to any of: %s' % ', '.join(self.targets)
        raise skip.SkipTest(msg)

    def __exit__(self, *args):
        locale.setlocale(locale.LC_ALL, self.old)

# Small sample of locales where '%x' expands to a dd/mm/yyyy string,
# which can cause trouble when parsed with dateutil.
_dd_mm_yyyy_locales = ['da_DK.UTF-8', 'de_DE.UTF-8', 'fr_FR.UTF-8']


def test_simple_api():
    # time to freeze is always provided in UTC
    freezer = freeze_time("2012-01-14")
    # expected timestamp must be a timestamp, corresponding to 2012-01-14 UTC
    local_time = datetime.datetime(2012, 1, 14)
    utc_time = local_time - datetime.timedelta(seconds=time.timezone)
    expected_timestamp = time.mktime(utc_time.timetuple())

    freezer.start()
    assert time.time() == expected_timestamp
    assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)
    assert datetime.datetime.utcnow() == datetime.datetime(2012, 1, 14)
    assert datetime.date.today() == datetime.date(2012, 1, 14)
    assert datetime.datetime.now().today() == datetime.date(2012, 1, 14)
    freezer.stop()
    assert time.time() != expected_timestamp
    assert datetime.datetime.now() != datetime.datetime(2012, 1, 14)
    assert datetime.datetime.utcnow() != datetime.datetime(2012, 1, 14)
    freezer = freeze_time("2012-01-10 13:52:01")
    freezer.start()
    assert datetime.datetime.now() == datetime.datetime(2012, 1, 10, 13, 52, 1)
    freezer.stop()


def test_tz_offset():
    freezer = freeze_time("2012-01-14 03:21:34", tz_offset=-4)
    # expected timestamp must be a timestamp,
    # corresponding to 2012-01-14 03:21:34 UTC
    # and it doesn't depend on tz_offset
    local_time = datetime.datetime(2012, 1, 14, 3, 21, 34)
    utc_time = local_time - datetime.timedelta(seconds=time.timezone)
    expected_timestamp = time.mktime(utc_time.timetuple())

    freezer.start()
    assert datetime.datetime.now() == datetime.datetime(2012, 1, 13, 23, 21, 34)
    assert datetime.datetime.utcnow() == datetime.datetime(2012, 1, 14, 3, 21, 34)
    assert time.time() == expected_timestamp
    freezer.stop()


def test_tz_offset_with_today():
    freezer = freeze_time("2012-01-14", tz_offset=-4)
    freezer.start()
    assert datetime.date.today() == datetime.date(2012, 1, 13)
    freezer.stop()
    assert datetime.date.today() != datetime.date(2012, 1, 13)


def test_tz_offset_with_time():
    # we expect the system to behave like a system with UTC timezone
    # at the beginning of the Epoch
    freezer = freeze_time('1970-01-01')
    freezer.start()
    assert datetime.date.today() == datetime.date(1970, 1, 1)
    assert datetime.datetime.now() == datetime.datetime(1970, 1, 1)
    assert datetime.datetime.utcnow() == datetime.datetime(1970, 1, 1)
    assert time.time() == 0.0
    freezer.stop()


def test_tz_offset_with_time():
    # we expect the system to behave like a system with UTC-4 timezone
    # at the beginning of the Epoch (wall clock should be 4 hrs late)
    freezer = freeze_time('1970-01-01', tz_offset=-4)
    freezer.start()
    assert datetime.date.today() == datetime.date(1969, 12, 31)
    assert datetime.datetime.now() == datetime.datetime(1969, 12, 31, 20)
    assert datetime.datetime.utcnow() == datetime.datetime(1970, 1, 1)
    assert time.time() == 0.0
    freezer.stop()


def test_time_with_microseconds():
    freezer = freeze_time(datetime.datetime(1970, 1, 1, 0, 0, 1, 123456))
    freezer.start()
    assert time.time() == 1.123456
    freezer.stop()

def test_bad_time_argument():
    try:
        freeze_time("2012-13-14", tz_offset=-4)
    except ValueError:
        pass
    else:
        assert False, "Bad values should raise a ValueError"


def test_date_object():
    frozen_date = datetime.date(year=2012, month=11, day=10)
    date_freezer = freeze_time(frozen_date)
    regular_freezer = freeze_time('2012-11-10')
    assert date_freezer.time_to_freeze == regular_freezer.time_to_freeze

def test_date_with_locale():
    with temp_locale(*_dd_mm_yyyy_locales):
        frozen_date = datetime.date(year=2012, month=1, day=2)
        date_freezer = freeze_time(frozen_date)
        assert date_freezer.time_to_freeze.date() == frozen_date

def test_invalid_type():
    try:
        freeze_time(int(4))
    except TypeError:
        pass
    else:
        assert False, "Bad types should raise a TypeError"


def test_datetime_object():
    frozen_datetime = datetime.datetime(year=2012, month=11, day=10,
                                        hour=4, minute=15, second=30)
    datetime_freezer = freeze_time(frozen_datetime)
    regular_freezer = freeze_time('2012-11-10 04:15:30')
    assert datetime_freezer.time_to_freeze == regular_freezer.time_to_freeze

def test_datetime_with_locale():
    with temp_locale(*_dd_mm_yyyy_locales):
        frozen_datetime = datetime.datetime(year=2012, month=1, day=2)
        date_freezer = freeze_time(frozen_datetime)
        assert date_freezer.time_to_freeze == frozen_datetime

@freeze_time("2012-01-14")
def test_decorator():
    assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)


@freeze_time("2012-01-14")
class Tester(object):
    def test_the_class(self):
        assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)

    def test_still_the_same(self):
        assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)


@freeze_time("Jan 14th, 2012")
def test_nice_datetime():
    assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)


def test_context_manager():
    with freeze_time("2012-01-14"):
        assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)
    assert datetime.datetime.now() != datetime.datetime(2012, 1, 14)


@freeze_time("Jan 14th, 2012")
def test_isinstance_with_active():
    now = datetime.datetime.now()
    assert isinstance(now, datetime.datetime)

    today = datetime.date.today()
    assert isinstance(today, datetime.date)


def test_isinstance_without_active():
    now = datetime.datetime.now()
    assert isinstance(now, datetime.datetime)
    assert isinstance(now, datetime.date)

    today = datetime.date.today()
    assert isinstance(today, datetime.date)

@freeze_time('2013-04-09')
class TestUnitTestClassDecorator(unittest.TestCase):
    def test_class_decorator_works_on_unittest(self):
        self.assertEqual(datetime.date(2013,4,9), datetime.date.today())


def assert_class_of_datetimes(right_class, wrong_class):
    datetime.datetime.min.__class__.should.equal(right_class)
    datetime.datetime.max.__class__.should.equal(right_class)
    datetime.date.min.__class__.should.equal(right_class)
    datetime.date.max.__class__.should.equal(right_class)
    datetime.datetime.min.__class__.shouldnt.equal(wrong_class)
    datetime.datetime.max.__class__.shouldnt.equal(wrong_class)
    datetime.date.min.__class__.shouldnt.equal(wrong_class)
    datetime.date.max.__class__.shouldnt.equal(wrong_class)


def test_min_and_max():
    freezer = freeze_time("2012-01-14")
    real_datetime = datetime

    freezer.start()
    datetime.datetime.min.__class__.should.equal(FakeDatetime)
    datetime.datetime.max.__class__.should.equal(FakeDatetime)
    datetime.date.min.__class__.should.equal(FakeDate)
    datetime.date.max.__class__.should.equal(FakeDate)
    datetime.datetime.min.__class__.shouldnt.equal(real_datetime)
    datetime.datetime.max.__class__.shouldnt.equal(real_datetime)
    datetime.date.min.__class__.shouldnt.equal(real_date)
    datetime.date.max.__class__.shouldnt.equal(real_date)

    freezer.stop()
    datetime.datetime.min.__class__.should.equal(datetime.datetime)
    datetime.datetime.max.__class__.should.equal(datetime.datetime)
    datetime.date.min.__class__.should.equal(datetime.date)
    datetime.date.max.__class__.should.equal(datetime.date)
    datetime.datetime.min.__class__.shouldnt.equal(FakeDatetime)
    datetime.datetime.max.__class__.shouldnt.equal(FakeDatetime)
    datetime.date.min.__class__.shouldnt.equal(FakeDate)
    datetime.date.max.__class__.shouldnt.equal(FakeDate)


def assert_pickled_datetimes_equal_original():
    min_datetime = datetime.datetime.min
    max_datetime = datetime.datetime.max
    min_date = datetime.date.min
    max_date = datetime.date.max
    now = datetime.datetime.now()
    today = datetime.date.today()
    utc_now = datetime.datetime.utcnow()
    assert pickle.loads(pickle.dumps(min_datetime)) == min_datetime
    assert pickle.loads(pickle.dumps(max_datetime)) == max_datetime
    assert pickle.loads(pickle.dumps(min_date)) == min_date
    assert pickle.loads(pickle.dumps(max_date)) == max_date
    assert pickle.loads(pickle.dumps(now)) == now
    assert pickle.loads(pickle.dumps(today)) == today
    assert pickle.loads(pickle.dumps(utc_now)) == utc_now


def test_pickle():
    freezer = freeze_time("2012-01-14")

    freezer.start()
    assert_pickled_datetimes_equal_original()

    freezer.stop()
    assert_pickled_datetimes_equal_original()

########NEW FILE########
__FILENAME__ = test_operations
import datetime
import sure
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta
from datetime import timedelta, tzinfo


@freeze_time("2012-01-14")
def test_addition():
    now = datetime.datetime.now()
    later = now + datetime.timedelta(days=1)
    other_later = now + relativedelta(days=1)
    assert isinstance(later, datetime.datetime)
    assert isinstance(other_later, datetime.datetime)

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    other_tomorrow = today + relativedelta(days=1)
    assert isinstance(tomorrow, datetime.date)
    assert isinstance(other_tomorrow, datetime.date)


@freeze_time("2012-01-14")
def test_subtraction():
    now = datetime.datetime.now()
    before = now - datetime.timedelta(days=1)
    other_before = now - relativedelta(days=1)
    how_long = now - before
    assert isinstance(before, datetime.datetime)
    assert isinstance(other_before, datetime.datetime)
    assert isinstance(how_long, datetime.timedelta)

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    other_yesterday = today - relativedelta(days=1)
    how_long = today - yesterday
    assert isinstance(yesterday, datetime.date)
    assert isinstance(other_yesterday, datetime.date)
    assert isinstance(how_long, datetime.timedelta)


@freeze_time("2012-01-14")
def test_datetime_timezone_none():
    now = datetime.datetime.now(tz=None)
    now.should.equal(datetime.datetime(2012, 1, 14))


class GMT5(tzinfo):
    def utcoffset(self,dt):
        return timedelta(hours=5)
    def tzname(self,dt):
        return "GMT +5"
    def dst(self,dt):
        return timedelta(0)


@freeze_time("2012-01-14 2:00:00")
def test_datetime_timezone_real():
    now = datetime.datetime.now(tz=GMT5())
    now.should.equal(datetime.datetime(2012, 1, 14, 7, tzinfo=GMT5()))
    now.utcoffset().should.equal(timedelta(0, 60 * 60 * 5))


@freeze_time("2012-01-14 2:00:00", tz_offset=-4)
def test_datetime_timezone_real_with_offset():
    now = datetime.datetime.now(tz=GMT5())
    now.should.equal(datetime.datetime(2012, 1, 14, 3, tzinfo=GMT5()))
    now.utcoffset().should.equal(timedelta(0, 60 * 60 * 5))

########NEW FILE########
__FILENAME__ = test_sqlite3
import datetime
from freezegun import freeze_time
import sqlite3


@freeze_time("2013-01-01")
def test_fake_datetime_select():
    db = sqlite3.connect("/tmp/foo")
    db.execute("""select ?""", (datetime.datetime.now(),))


@freeze_time("2013-01-01")
def test_fake_date_select():
    db = sqlite3.connect("/tmp/foo")
    db.execute("""select ?""", (datetime.date.today(),))

########NEW FILE########
