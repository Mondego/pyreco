__FILENAME__ = compat
from __future__ import division, absolute_import

import sys


if sys.version_info < (3, 0):
    _PY3 = False
    xrange = xrange

    def dict_item_iter(d):
        """
        Return an iterator over the dict items.
        """
        return d.iteritems()
else:
    _PY3 = True
    xrange = range

    def dict_item_iter(d):
        """
        Return an iterator over the dict items.
        """
        return d.items()


__all__ = [
    _PY3, xrange, dict_item_iter
]

########NEW FILE########
__FILENAME__ = counter
from __future__ import division, absolute_import

class Counter(object):
    """
    A counter method that increments and decrements.
    """
    def __init__(self):
        """
        Create a new instance of a L{Counter}.
        """
        self._count = 0

    def inc(self, n = 1):
        """
        Increment the counter by I{n}.

        @type n: C{int}
        @param n: the amount to be incremented
        """
        self._count += n

    def dec(self, n = 1):
        """
        Decrement the counter by I{n}.

        @type n: C{int}
        @param n: the amount to be decrement
        """
        self._count -= n

    def get_count(self):
        """
        Returns the count

        @rtype: C{int}
        @return: the count
        """
        return self._count

    def clear(self):
        """
        Resets the count back to 0.
        """
        self._count = 0

########NEW FILE########
__FILENAME__ = histogram
from __future__ import division, absolute_import

from math import sqrt

from yunomi.stats.exp_decay_sample import ExponentiallyDecayingSample
from yunomi.stats.uniform_sample import UniformSample


class Histogram(object):
    """
    A metric which calculates the distribution of a value.

    @see: <a href="http://www.johndcook.com/standard_deviation.html">Accurately computing running variance</a>
    """
    DEFAULT_SAMPLE_SIZE = 1028
    DEFAULT_ALPHA = 0.015
    count = 0
    mean = 0
    sum_of_squares = -1.0

    def __init__(self, sample):
        """
        Creates a new instance of a L{Histogram}.

        @type sample: L{ExponentiallyDecayingSample} or L{UniformSample}
        @param sample: an instance of L{ExponentiallyDecayingSample} or
                       L{UniformSample}
        """
        self.sample = sample
        self.clear()

    @classmethod
    def get_biased(klass):
        """
        Create a new instance of L{Histogram} that uses an L{ExponentiallyDecayingSample}
        with sample size L{DEFAULT_SAMPLE_SIZE} and alpha L{DEFAULT_ALPHA}.

        @return: L{Histogram}
        """
        return klass(ExponentiallyDecayingSample(klass.DEFAULT_SAMPLE_SIZE, klass.DEFAULT_ALPHA))

    @classmethod
    def get_uniform(klass):
        """
        Create a new instance of L{Histogram} that uses an L{UniformSample}
        with sample size L{DEFAULT_SAMPLE_SIZE}.

        """
        return klass(UniformSample(klass.DEFAULT_SAMPLE_SIZE))

    def clear(self):
        """
        Resets the values to default.
        """
        self.sample.clear()
        self.max_ = -2147483647.0
        self.min_ = 2147483647.0
        self.sum_ = 0.0
        self.count = 0
        self.mean = 0
        self.sum_of_squares = -1.0

    def update(self, value):
        """
        Updates all the fields with the new value (if applicable).

        @type value: C{int}
        @param value: the value to update the fields with
        """
        self.count += 1
        self.sample.update(value)
        self.set_max(value)
        self.set_min(value)
        self.sum_ += value
        self.update_variance_info(value)

    def get_count(self):
        """
        The number of values put into the histogram.
        """
        return self.count

    def get_max(self):
        """
        The maximum value that has been updated into the histogram.

        @rtype: C{int} or C{float}
        @return: the max value
        """
        if self.get_count() > 0:
            return self.max_
        return 0.0

    def get_min(self):
        """
        The minimum value that has been updated into the histogram.

        @rtype: C{int} or C{float}
        @return: the min value
        """
        if self.get_count() > 0:
            return self.min_
        return 0.0

    def get_mean(self):
        """
        The average of all the values that have been updated into the
        historgram.

        @rtype: C{float}
        @return: the average of all the values updated
        """
        if self.get_count() > 0:
            return float(self.sum_) / self.get_count()
        return 0.0

    def get_std_dev(self):
        """
        Returns the standard devation calculated by taking the square root of
        the variance, which is updated whenever a new value is added.

        @rtype: C{float}
        @return: the standard deviation
        """
        if self.get_count() > 0:
            return sqrt(self.get_variance())
        return 0.0

    def get_variance(self):
        """
        Returns the variance calculated using the sum of squares of deviations
        from the mean and the total count, which are both updated whenever a
        new value is added.

        @rtype: C{float}
        @return: the variance
        """
        if self.get_count() <= 1:
            return 0.0
        return self.sum_of_squares / (self.get_count() - 1)

    def get_sum(self):
        """
        The sum of all the values, updated whenever a value is added. Useful
        for computing the mean quickly.

        @rtype: C{int} or C{float}
        @return: the sum of all the values
        """
        return self.sum_

    def get_snapshot(self):
        """
        Returns a snapshot of the current set of values in the histogram.

        @rtype: L{Snapshot}
        @return: the snapshot of the current values
        """
        return self.sample.get_snapshot()

    def set_max(self, new_max):
        """
        Checks if a value is greater than the current max. If so, update
        I{max_}.

        @type new_max: C{int} or C{float}
        @param new_max: the potential new maximum value to check
        """
        if self.max_ < new_max:
            self.max_ = new_max

    def set_min(self, new_min):
        """
        Checks if a value is less than the current min. If so, update I{min_}.

        @type new_min: C{int} or C{float}
        @param new_min: the potential new minimum value to check
        """
        if self.min_ > new_min:
            self.min_ = new_min

    def update_variance_info(self, value):
        """
        Updates the I{sum_of_squares} and I{mean} whenever a new value is
        updated. This makes computing the variance more computationally
        efficient.

        @type value: C{int} or C{float}
        @param value: the value being added to the histogram
        """
        old_mean = self.mean
        delta = value - old_mean
        if self.sum_of_squares == -1.0:
            self.mean = value
            self.sum_of_squares = 0.0
        else:
            self.mean += (float(delta) / self.get_count())
            self.sum_of_squares += (float(delta) * (value - self.mean))

########NEW FILE########
__FILENAME__ = meter
from __future__ import division, absolute_import

from time import time

from yunomi.stats.ewma import EWMA


class Meter(object):
    """
    A meter metric which measures mean throughput and one-, five-, and fifteen-
    minute exponentially-weighted moving average throughputs.

    @see: <a href="http://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average">EMA</a>
    """
    INTERVAL = 5

    def __init__(self, event_type=""):
        """
        Creates a new L{Meter} instance.

        @type event_type: C{str}
        @param event_type: the plural name of the event the meter is measuring
                           (e.g., I{"requests"})
        """
        self.event_type = event_type
        self.start_time = time()
        self._m1_rate = EWMA.one_minute_EWMA()
        self._m5_rate = EWMA.five_minute_EWMA()
        self._m15_rate = EWMA.fifteen_minute_EWMA()
        self._count = 0

    def clear(self):
        """
        Resets the meter.
        """
        self.start_time = time()
        self._count = 0
        self._m1_rate = EWMA.one_minute_EWMA()
        self._m5_rate = EWMA.five_minute_EWMA()
        self._m15_rate = EWMA.fifteen_minute_EWMA()

    def get_event_type(self):
        """
        Returns the event type.

        @rtype: C{str}
        @return: the event type
        """
        return self.event_type

    def _tick(self):
        """
        Updates the moving averages.
        """
        self._m1_rate.tick()
        self._m15_rate.tick()
        self._m5_rate.tick()

    def mark(self, n = 1):
        """
        Mark the occurrence of a given number of events.

        @type n: C{int}
        @param n: number of events
        """
        self._count += n
        self._m1_rate.update(n)
        self._m15_rate.update(n)
        self._m5_rate.update(n)

    def get_count(self):
        """
        Return the number of events that have been counted.

        @rtype: C{int}
        @return: the total number of events
        """
        return self._count

    def get_fifteen_minute_rate(self):
        """
        Get the rate of the L{EWMA} equivalent to a fifteen minute load average.

        @rtype: C{float}
        @return: the fifteen minute rate
        """
        return self._m15_rate.get_rate()

    def get_five_minute_rate(self):
        """
        Get the rate of the L{EWMA} equivalent to a five minute load average.

        @rtype: C{float}
        @return: the five minute rate
        """
        return self._m5_rate.get_rate()

    def get_one_minute_rate(self):
        """
        Get the rate of the L{EWMA} equivalent to a one minute load average.

        @rtype: C{float}
        @return: the one minute rate
        """
        return self._m1_rate.get_rate()

    def get_mean_rate(self):
        """
        Get the overall rate, the total number of events over the time since
        the beginning.

        @rtype: C{float}
        @return: the mean minute rate
        """
        if self._count == 0:
            return 0.0
        else:
            elapsed = time() - self.start_time
            return float(self._count) / elapsed

########NEW FILE########
__FILENAME__ = metrics_registry
from __future__ import division, absolute_import

from time import time
from functools import wraps

from yunomi.compat import dict_item_iter
from yunomi.core.counter import Counter
from yunomi.core.histogram import Histogram
from yunomi.core.meter import Meter
from yunomi.core.timer import Timer


class MetricsRegistry(object):
    """
    A single interface used to gather metrics on a service. It keeps track of
    all the relevant Counters, Meters, Histograms, and Timers. It does not have
    a reference back to its service. The service would create a
    L{MetricsRegistry} to manage all of its metrics tools.
    """
    def __init__(self, clock=time):
        """
        Creates a new L{MetricsRegistry} instance.
        """
        self._timers = {}
        self._meters = {}
        self._counters = {}
        self._histograms = {}

        self._clock = clock

    def counter(self, key):
        """
        Gets a counter based on a key, creates a new one if it does not exist.

        @param key: name of the metric
        @type key: C{str}

        @return: L{Counter}
        """
        if key not in self._counters:
            self._counters[key] = Counter()
        return self._counters[key]

    def histogram(self, key, biased=False):
        """
        Gets a histogram based on a key, creates a new one if it does not exist.

        @param key: name of the metric
        @type key: C{str}

        @return: L{Histogram}
        """
        if key not in self._histograms:
            if biased:
                self._histograms[key] = Histogram.get_biased()
            else:
                self._histograms[key] = Histogram.get_uniform()

        return self._histograms[key]

    def meter(self, key):
        """
        Gets a meter based on a key, creates a new one if it does not exist.

        @param key: name of the metric
        @type key: C{str}

        @return: L{Meter}
        """
        if key not in self._meters:
            self._meters[key] = Meter()
        return self._meters[key]

    def timer(self, key):
        """
        Gets a timer based on a key, creates a new one if it does not exist.

        @param key: name of the metric
        @type key: C{str}

        @return: L{Timer}
        """
        if key not in self._timers:
            self._timers[key] = Timer()
        return self._timers[key]

    def dump_metrics(self):
        """
        Formats all the metrics into dicts, and returns a list of all of them

        @return: C{list} of C{dict} of metrics
        """
        metrics = []

        # format timed stats
        for key, timer in dict_item_iter(self._timers):
            snapshot = timer.get_snapshot()
            for suffix, val in (("avg", timer.get_mean()),
                                ("max", timer.get_max()),
                                ("min", timer.get_min()),
                                ("std_dev", timer.get_std_dev()),
                                ("15m_rate", timer.get_fifteen_minute_rate()),
                                ("5m_rate", timer.get_five_minute_rate()),
                                ("1m_rate", timer.get_one_minute_rate()),
                                ("mean_rate", timer.get_mean_rate()),
                                ("75_percentile", snapshot.get_75th_percentile()),
                                ("98_percentile", snapshot.get_98th_percentile()),
                                ("99_percentile", snapshot.get_99th_percentile()),
                                ("999_percentile", snapshot.get_999th_percentile())):
                k = "_".join([key, suffix])
                _new_metric = {
                    "type": "float",
                    "name": k,
                    "value": val,
                }
                metrics.append(_new_metric)

        # format meter stats
        for key, meter in dict_item_iter(self._meters):
            for suffix, val in (("15m_rate", meter.get_fifteen_minute_rate()),
                                ("5m_rate", meter.get_five_minute_rate()),
                                ("1m_rate", meter.get_one_minute_rate()),
                                ("mean_rate", meter.get_mean_rate())):
                k = "_".join([key, suffix])
                _new_metric = {
                    "type": "float",
                    "name": k,
                    "value": val,
                }
                metrics.append(_new_metric)

        # format histogram stats
        for key, histogram in dict_item_iter(self._histograms):
            snapshot = histogram.get_snapshot()
            for suffix, val in (("avg", histogram.get_mean()),
                                ("max", histogram.get_max()),
                                ("min", histogram.get_min()),
                                ("std_dev", histogram.get_std_dev()),
                                ("75_percentile", snapshot.get_75th_percentile()),
                                ("98_percentile", snapshot.get_98th_percentile()),
                                ("99_percentile", snapshot.get_99th_percentile()),
                                ("999_percentile", snapshot.get_999th_percentile())):
                k = "_".join([key, suffix])
                _new_metric = {
                    "type": "float",
                    "name": k,
                    "value": val,
                }
                metrics.append(_new_metric)

        # format counter stats
        for key, counter in dict_item_iter(self._counters):
            k = "_".join([key, "count"])
            val = counter.get_count()
            _new_metric = {
                "type": "int",
                "name": k,
                "value": val
            }
            metrics.append(_new_metric)

        # alphabetize
        metrics.sort(key=lambda x: x["name"])
        return metrics


_global_registry = MetricsRegistry()

counter = _global_registry.counter
histogram = _global_registry.histogram
meter = _global_registry.meter
timer = _global_registry.timer
dump_metrics = _global_registry.dump_metrics

def count_calls(fn):
    """
    Decorator to track the number of times a function is called.

    @param fn: the function to be decorated
    @type fn: C{func}

    @return: the decorated function
    @rtype: C{func}
    """
    @wraps(fn)
    def wrapper(*args):
        counter("%s_calls" % fn.__name__).inc()
        try:
            return fn(*args)
        except:
            raise
    return wrapper

def meter_calls(fn):
    """
    Decorator to the rate at which a function is called.

    @param fn: the function to be decorated
    @type fn: C{func}

    @return: the decorated function
    @rtype: C{func}
    """
    @wraps(fn)
    def wrapper(*args):
        meter("%s_calls" % fn.__name__).mark()
        try:
            return fn(*args)
        except:
            raise
    return wrapper

def hist_calls(fn):
    """
    Decorator to check the distribution of return values of a function.

    @param fn: the function to be decorated
    @type fn: C{func}

    @return: the decorated function
    @rtype: C{func}
    """
    @wraps(fn)
    def wrapper(*args):
        _histogram = histogram("%s_calls" % fn.__name__)
        try:
            rtn = fn(*args)
            if type(rtn) in (int, float):
                _histogram.update(rtn)
            return rtn
        except:
            raise
    return wrapper

def time_calls(fn):
    """
    Decorator to time the execution of the function.

    @param fn: the function to be decorated
    @type fn: C{func}

    @return: the decorated function
    @rtype: C{func}
    """
    @wraps(fn)
    def wrapper(*args):
        _timer = timer("%s_calls" % fn.__name__)
        start = time()
        try:
            return fn(*args)
        except:
            raise
        finally:
            _timer.update(time() - start)
    return wrapper

########NEW FILE########
__FILENAME__ = timer
from __future__ import division, absolute_import

from yunomi.stats.snapshot import Snapshot
from yunomi.core.histogram import Histogram
from yunomi.core.meter import Meter


class Timer(object):
    """
    A timer metric which aggregates timing durations and provides duration
    statistics, plus throughput statistics via L{Meter}.
    """

    def __init__(self):
        """
        Creates a new L{Timer} instance.
        """
        self.histogram = Histogram.get_biased()
        self.meter = Meter("calls")

    def clear(self):
        """
        Clears all recorded durations in the histogram.
        """
        self.histogram.clear()

    def update(self, duration):
        """
        Updates the L{Histogram} and marks the L{Meter}.

        @type duration: C{int}
        @param duration: the duration of an event
        """
        if duration >= 0:
            self.histogram.update(duration)
            self.meter.mark()

    def get_count(self):
        """
        L{Histogram.get_count}
        """
        return self.histogram.get_count()

    def get_fifteen_minute_rate(self):
        """
        L{Meter.get_fifteen_minute_rate}
        """
        return self.meter.get_fifteen_minute_rate()

    def get_five_minute_rate(self):
        """
        L{Meter.get_five_minute_rate}
        """
        return self.meter.get_five_minute_rate()

    def get_one_minute_rate(self):
        """
        L{Meter.get_one_minute_rate}
        """
        return self.meter.get_one_minute_rate()

    def get_mean_rate(self):
        """
        L{Meter.get_mean_rate}
        """
        return self.meter.get_mean_rate()

    def get_max(self):
        """
        L{Histogram.get_max}
        """
        return self.histogram.get_max()

    def get_min(self):
        """
        L{Histogram.get_min}
        """
        return self.histogram.get_min()

    def get_mean(self):
        """
        L{Histogram.get_mean}
        """
        return self.histogram.get_mean()

    def get_std_dev(self):
        """
        L{Histogram.get_std_dev}
        """
        return self.histogram.get_std_dev()

    def get_sum(self):
        """
        L{Histogram.get_sum}
        """
        return self.histogram.get_sum()

    def get_snapshot(self):
        """
        L{Histogram.get_snapshot}
        """
        values = self.histogram.get_snapshot().get_values()
        return Snapshot(values)

    def get_event_type(self):
        """
        L{Meter.get_event_type}
        """
        return self.meter.get_event_type()

########NEW FILE########
__FILENAME__ = ewma
from __future__ import division, absolute_import

from math import exp
from time import time


class EWMA(object):
    """
    An exponentially-weighted moving average.

    @see: <a href="http://www.teamquest.com/pdfs/whitepaper/ldavg1.pdf">UNIX Load Average Part 1: How It Works</a>
    @see: <a href="http://www.teamquest.com/pdfs/whitepaper/ldavg2.pdf">UNIX Load Average Part 2: Not Your Average Average</a>
    """
    INTERVAL = 5

    def __init__(self, period, interval=None):
        """
        Create a new EWMA with a specific smoothing constant.

        @type period: C{int}
        @param period: the time it takes to reach a given significance level
        @type interval: C{int}
        @param interval: the expected tick interval, defaults to 5s
        """
        self.initialized = False
        self._period = period
        self._interval = (interval or EWMA.INTERVAL)
        self._uncounted = 0.0
        self._rate = 0.0
        self._last_tick = time()

    @classmethod
    def one_minute_EWMA(klass):
        """
        Creates a new EWMA which is equivalent to the UNIX one minute load
        average.

        @rtype: L{EWMA}
        @return: a one-minute EWMA
        """
        return klass(60)

    @classmethod
    def five_minute_EWMA(klass):
        """
        Creates a new EWMA which is equivalent to the UNIX five minute load
        average.

        @rtype: L{EWMA}
        @return: a five-minute EWMA
        """
        return klass(300)

    @classmethod
    def fifteen_minute_EWMA(klass):
        """
        Creates a new EWMA which is equivalent to the UNIX fifteen minute load
        average.

        @rtype: L{EWMA}
        @return: a fifteen-minute EWMA
        """
        return klass(900)

    def update(self, value):
        """
        Increment the moving average with a new value.

        @type value: C{int} or C{float}
        @param value: the new value
        """
        self._uncounted += value

    def tick(self):
        """
        Mark the passage of time and decay the current rate accordingly.
        """
        prev = self._last_tick
        now = time()
        interval = now - prev

        instant_rate = self._uncounted / interval
        self._uncounted = 0

        if self.initialized:
            self._rate += (self._alpha(interval) * (instant_rate - self._rate))
        else:
            self._rate = instant_rate
            self.initialized = True

        self._last_tick = now

    def get_rate(self):
        """
        Returns the rate in counts per second. Calls L{EWMA.tick} when the
        elapsed time is greater than L{EWMA.INTERVAL}.

        @rtype: C{float}
        @return: the rate
        """
        if time() - self._last_tick >= self._interval:
            self.tick()
        return self._rate

    def _alpha(self, interval):
        """
        Calculate the alpha based on the time since the last tick. This is
        necessary because a single threaded Python program loses precision  
        under high load, so we can't assume a consistant I{EWMA._interval}.

        @type interval: C{float}
        @param interval: the interval we use to calculate the alpha
        """
        return 1 - exp(-interval / self._period)

########NEW FILE########
__FILENAME__ = exp_decay_sample
from __future__ import division, absolute_import

from math import exp
from time import time
from random import random

from yunomi.stats.snapshot import Snapshot


class ExponentiallyDecayingSample(object):
    """
    An exponentially-decaying random sample of longs. Uses Cormode et al's
    forward-decaying priority reservoir sampling method to produce a
    statistically representative sample, exponentially biased towards newer
    entries.

    @see: <a href="http://www.research.att.com/people/Cormode_Graham/library/publications/CormodeShkapenyukSrivastavaXu09.pdf">
          Cormode et al. Forward Decay: A Practical Time Decay Model for
          Streaming Systems. ICDE '09: Proceedings of the 2009 IEEE
          International Conference on Data Engineering (2009)</a>
    """
    RESCALE_THRESHOLD = 3600
    count = 0
    values = {}
    next_scale_time = 0

    def __init__(self, reservoir_size, alpha, clock=time):
        """
        Creates a new L{ExponentiallyDecayingSample}.

        @type reservoir_size: C{int}
        @param reservoir_size: the number of samples to keep in the sampling
                               reservoir
        @type alpha: C{float}
        @param alpha: the exponential decay factor; the higher this is, the more
                      biased the sample will be towards newer values
        @type clock: C{function}
        @param clock: the function used to return the current time, default to
                      seconds since the epoch; to be used with other time
                      units, or with the twisted clock for our testing purposes
        """
        self.reservoir_size = reservoir_size
        self.alpha = alpha
        self.clock = clock
        self.clear()

    def clear(self):
        """
        Clears the values in the sample and resets the clock.
        """
        self.count = 0
        self.values = {}
        self.start_time = self.clock()
        self.next_scale_time = self.clock() + self.RESCALE_THRESHOLD

    def size(self):
        """
        Returns the size of the exponentially decaying sample. The size does not
        increase if the I{count} exceeds the I{reservoir_size}. Instead, we
        wait until it is time for the sample rescale.

        @rtype: C{int}
        @return: the size of the sample
        """
        return min(self.reservoir_size, self.count)

    def update(self, value, timestamp=None):
        """
        Adds an old value with a fixed timestamp to the sample.

        @type value: C{int} or C{float}
        @param value: the value to be added
        @type timestamp: C{int}
        @param timestamp: the epoch timestamp of I{value} in seconds
        """
        if not timestamp:
            timestamp = self.clock()
        self._rescale_if_needed()
        priority = self._weight(timestamp - self.start_time) / random()
        self.count += 1

        if self.count <= self.reservoir_size:
            self.values[priority] = value
        else:
            first = min(self.values)
            if first < priority:
                if priority not in self.values:
                    self.values[priority] = value
                    while first not in self.values:
                        first = min(self.values)
                    del self.values[first]

    def _rescale_if_needed(self):
        """
        Checks the current time and rescales the sample if it time to do so.
        """
        now = self.clock()
        next_ = self.next_scale_time
        if now >= next_:
            self._rescale(now, next_)

    def get_snapshot(self):
        """
        Creates a statistical snapshot from the current set of values.
        """
        return Snapshot(self.values.values())

    def _weight(self, t):
        """
        Assigns a weight based on a specific timer interval, used to calculate
        priority for each value.
        """
        return exp(self.alpha * t)

    def _rescale(self, now, next_):
        """
        Rescales the I{values}, assigning new priorities for each value.

        @type now: C{int}
        @param now: the time right now
        @type next_: C{int}
        @param next_: the scheduled time for the next rescale
        """
        if self.next_scale_time == next_:
            self.next_scale_time = now + self.RESCALE_THRESHOLD
            old_start_time = self.start_time
            self.start_time = self.clock()

            for key in sorted(self.values.keys()):
                value = self.values[key]
                del self.values[key]
                self.values[key * exp(-self.alpha * (self.start_time - old_start_time))] = value

            self.count = len(self.values)

########NEW FILE########
__FILENAME__ = snapshot
from __future__ import division, absolute_import

from math import floor


class Snapshot(object):
    """
    A statistical snapshot of a set of values.
    """
    MEDIAN_Q = 0.5
    P75_Q = 0.75
    P95_Q = 0.95
    P98_Q = .98
    P99_Q = .99
    P999_Q = .999

    def __init__(self, values):
        """
        Create a new L{Snapshot} with the given values.

        @type values: C{dict}
        @param values: an unordered set of values in the sample
        """
        self.values = list(values)
        self.values.sort()

    def get_value(self, quantile):
        """
        Returns the value at the given quantile.

        @type quantile: C{float}
        @param quantile: a given quantile in M{[0...1]}

        @rtype: C{int} or C{float}
        @return: the value in the distribution at the specified I{quantile}
        """
        assert quantile >= 0.0 and quantile <= 1.0,\
            "{0} is not in [0...1]".format(quantile)
        if len(self.values) == 0:
            return 0.0

        pos = quantile * (len(self.values) + 1)

        if pos < 1:
            return self.values[0]
        if pos >= len(self.values):
            return self.values[len(self.values) -1]

        lower = self.values[int(pos) - 1]
        upper = self.values[int(pos)]
        return lower + (pos - floor(pos)) * (upper - lower)

    def size(self):
        """
        Return the size of the given distribution.

        @rtype: C{int}
        @return: the size of the given distribution
        """
        return len(self.values)

    def get_median(self):
        """
        Return the median of the given distribution.

        @rtype: C{int}
        @return: the median
        """
        return self.get_value(self.MEDIAN_Q)

    def get_75th_percentile(self):
        """
        Return the 75th percentile value of the given distribution.

        @rtype: C{int}
        @return: the 99.9th percentile value
        """
        return self.get_value(self.P75_Q)

    def get_98th_percentile(self):
        """
        Return the 98th percentile value of the given distribution.

        @rtype: C{int}
        @return: the 98th percentile value
        """
        return self.get_value(self.P98_Q)

    def get_99th_percentile(self):
        """
        Return the 99th percentile value of the given distribution.

        @rtype: C{int}
        @return: the 99th percentile value
        """
        return self.get_value(self.P99_Q)

    def get_999th_percentile(self):
        """
        Return the 99.9th percentile value of the given distribution.

        @rtype: C{int}
        @return: the 99.9th percentile value
        """
        return self.get_value(self.P999_Q)

    def get_values(self):
        """
        Returns a copy of the current distribution of values

        @rtype: C{list}
        @return: a copy of the list of values
        """
        return self.values[:]

    def dump(output):
        """
        Write all the values to a file

        @todo: actually test this to see if it works...
        """
        assert type(output) == file, "Argument must be of 'file' type"

        for value in self.values:
            output.write("{0}\n".format(value))
        output.close()

########NEW FILE########
__FILENAME__ = uniform_sample
from __future__ import division, absolute_import

from random import randint

from yunomi.compat import xrange
from yunomi.stats.snapshot import Snapshot


class UniformSample(object):
    """
    A random sample of a stream of {@code long}s. Uses Vitter's Algorithm R to
    produce a statistically representative sample.

    @see: <a href="http://www.cs.umd.edu/~samir/498/vitter.pdf">Random Sampling with a Reservoir</a>
    """
    BITS_PER_LONG = 63
    values = []

    def __init__(self, reservoir_size):
        """
        Create a new L{UniformSample}.

        @type reservoir_size: C{int}
        @param reservoir_size: the number of params to keep in the sampling reservoir
        """
        self.values = [0 for x in xrange(reservoir_size)]
        self.clear()

    def clear(self):
        """
        Clears the sample, setting all values to zero.
        """
        self.values = [0 for x in xrange(len(self.values))]
        self.count = 0

    def size(self):
        """
        Returns the size of the uniform sample. The size will never be bigger
        than the reservoir_size (ie. the size of the list of values).

        @rtype: C{int}
        @return: the size of the sample
        """
        
        if self.count > len(self.values):
            return len(self.values)
        return self.count

    def update(self, value):
        """
        Updates the I{self.values} at a random index with the given value.

        @type value: C{int} or C{float}
        @param value: the new value to be added
        """
        self.count += 1
        if self.count <= len(self.values):
            self.values[self.count - 1] = value
        else:
            r = UniformSample.next_long(self.count)
            if r < len(self.values):
                self.values[r] = value

    @classmethod
    def next_long(klass, n):
        """
        Randomly assigns a new number in [0...n]. Used to randomly update an
        index in I{self.values} with a new value.
        """
        return randint(0, n-1)

    def get_snapshot(self):
        """
        Creates a statistical snapshot from the current set of values.
        """
        copy = []
        for i in xrange(self.size()):
            copy.append(self.values[i])
        return Snapshot(copy)

########NEW FILE########
__FILENAME__ = test_counter
from __future__ import division, absolute_import

from unittest2 import TestCase

from yunomi.core.counter import Counter


class CounterTests(TestCase):
    _counter = Counter()

    def test_starts_at_zero(self):
        self.assertEqual(self._counter.get_count(), 0)

    def test_increments_by_one(self):
        self._counter.inc()
        self.assertEqual(self._counter.get_count(), 1)
        self._counter.clear()

    def test_increments_by_arbitrary_delta(self):
        self._counter.inc(12)
        self.assertEqual(self._counter.get_count(), 12)
        self._counter.clear()

    def test_decrements_by_one(self):
        self._counter.dec()
        self.assertEqual(self._counter.get_count(), -1)
        self._counter.clear()

    def test_decrements_by_arbitrary_delta(self):
        self._counter.dec(12)
        self.assertEqual(self._counter.get_count(), -12)
        self._counter.clear()

    def test_is_zero_after_being_cleared(self):
        self._counter.clear()
        self.assertEqual(self._counter.get_count(), 0)

########NEW FILE########
__FILENAME__ = test_EWMA
from __future__ import division, absolute_import

import mock
from unittest2 import TestCase

from yunomi.compat import xrange
from yunomi.stats.ewma import EWMA


class EWMATests(TestCase):

    def elapse_minute(self, time_mock):
        for i in xrange(0, 12):
            time_mock.return_value += 5
            self.ewma.tick()

    @mock.patch("yunomi.stats.ewma.time")
    def test_one_minute_EWMA_five_sec_tick(self, time_mock):
        time_mock.return_value = 0.0
        self.ewma = EWMA.one_minute_EWMA()

        self.ewma.update(3)
        time_mock.return_value += 5
        self.ewma.tick()

        for expected_rate in [0.6, 0.22072766, 0.08120117, 0.02987224,
                              0.01098938, 0.00404277, 0.00148725,
                              0.00054713, 0.00020128, 0.00007405]:
            self.assertAlmostEqual(self.ewma.get_rate(), expected_rate)
            self.elapse_minute(time_mock)

    @mock.patch("yunomi.stats.ewma.time")
    def test_five_minute_EWMA_five_sec_tick(self, time_mock):
        time_mock.return_value = 0.0
        self.ewma = EWMA.five_minute_EWMA()

        self.ewma.update(3)
        time_mock.return_value += 5
        self.ewma.tick()

        for expected_rate in [0.6, 0.49123845, 0.40219203, 0.32928698,
                              0.26959738, 0.22072766, 0.18071653,
                              0.14795818, 0.12113791, 0.09917933]:
            self.assertAlmostEqual(self.ewma.get_rate(), expected_rate)
            self.elapse_minute(time_mock)

    @mock.patch("yunomi.stats.ewma.time")
    def test_fifteen_minute_EWMA_five_sec_tick(self, time_mock):
        time_mock.return_value = 0.0
        self.ewma = EWMA.fifteen_minute_EWMA()

        self.ewma.update(3)
        time_mock.return_value += 5
        self.ewma.tick()

        for expected_rate in [0.6, 0.56130419, 0.52510399, 0.49123845,
                              0.45955700, 0.42991879, 0.40219203,
                              0.37625345, 0.35198773, 0.32928698]:
            self.assertAlmostEqual(self.ewma.get_rate(), expected_rate)
            self.elapse_minute(time_mock)

    @mock.patch("yunomi.stats.ewma.time")
    def test_one_minute_EWMA_one_minute_tick(self, time_mock):
        time_mock.return_value = 0.0
        self.ewma = EWMA.one_minute_EWMA()

        self.ewma.update(3)
        time_mock.return_value += 5
        self.ewma.tick()

        for expected_rate in [0.6, 0.22072766, 0.08120117, 0.02987224,
                              0.01098938, 0.00404277, 0.00148725,
                              0.00054713, 0.00020128, 0.00007405]:
            self.assertAlmostEqual(self.ewma.get_rate(), expected_rate)
            time_mock.return_value += 60

    @mock.patch("yunomi.stats.ewma.time")
    def test_five_minute_EWMA_one_minute_tick(self, time_mock):
        time_mock.return_value = 0.0
        self.ewma = EWMA.five_minute_EWMA()

        self.ewma.update(3)
        time_mock.return_value += 5
        self.ewma.tick()

        for expected_rate in [0.6, 0.49123845, 0.40219203, 0.32928698,
                              0.26959738, 0.22072766, 0.18071653,
                              0.14795818, 0.12113791, 0.09917933]:
            self.assertAlmostEqual(self.ewma.get_rate(), expected_rate)
            time_mock.return_value += 60

    @mock.patch("yunomi.stats.ewma.time")
    def test_fifteen_minute_EWMA_one_minute_tick(self, time_mock):
        time_mock.return_value = 0.0
        self.ewma = EWMA.fifteen_minute_EWMA()

        self.ewma.update(3)
        time_mock.return_value += 5
        self.ewma.tick()

        for expected_rate in [0.6, 0.56130419, 0.52510399, 0.49123845,
                              0.45955700, 0.42991879, 0.40219203,
                              0.37625345, 0.35198773, 0.32928698]:
            self.assertAlmostEqual(self.ewma.get_rate(), expected_rate)
            time_mock.return_value += 60

########NEW FILE########
__FILENAME__ = test_exp_decay_sample_test
from __future__ import division, absolute_import

from unittest2 import TestCase

from yunomi.compat import xrange
from yunomi.stats.exp_decay_sample import ExponentiallyDecayingSample
from yunomi.tests.util import Clock


class ExponentiallyDecayingSampleTests(TestCase):

    def test_a_sample_of_100_out_of_1000_elements(self):
        sample = ExponentiallyDecayingSample(100, 0.99)
        for i in xrange(1000):
            sample.update(i)
        snapshot = sample.get_snapshot()

        self.assertEqual(sample.size(), 100)
        self.assertEqual(snapshot.size(), 100)

        for i in snapshot.get_values():
            self.assertTrue(i < 1000 and i >= 0)

    def test_a_sample_of_100_out_of_10_elements(self):
        sample = ExponentiallyDecayingSample(100, 0.99)
        for i in xrange(10):
            sample.update(i)
        snapshot = sample.get_snapshot()

        self.assertEqual(sample.size(), 10)
        self.assertEqual(snapshot.size(), 10)
        self.assertAlmostEqual(snapshot.get_median(), 4.5)

        for i in snapshot.get_values():
            self.assertTrue(i < 10 and i >= 0)

    def test_a_heavily_biased_sample_of_100_out_of_1000_elements(self):
        sample = ExponentiallyDecayingSample(1000, 0.01)
        for i in xrange(100):
            sample.update(i)
        snapshot = sample.get_snapshot()

        self.assertEqual(sample.size(), 100)
        self.assertEqual(snapshot.size(), 100)

        for i in snapshot.get_values():
            self.assertTrue(i < 100 and i >= 0)

    def test_long_period_of_inactivity_should_not_corrupt_sampling_state(self):
        twisted_clock = Clock()
        sample = ExponentiallyDecayingSample(10, 0.015, twisted_clock.seconds)
        for i in xrange(1000):
            sample.update(1000 + i)
            twisted_clock.advance(0.1)

        self.assertTrue(sample.get_snapshot().size() == 10)
        self._assert_all_values_between(sample, 1000, 2000)

        twisted_clock.advance(15*3600)
        sample.update(2000)
        self.assertTrue(sample.get_snapshot().size() == 2)
        self._assert_all_values_between(sample, 1000, 3000)

        for i in xrange(1000):
            sample.update(3000 + i)
            twisted_clock.advance(0.1)

        self.assertTrue(sample.get_snapshot().size() == 10)
        self._assert_all_values_between(sample, 3000, 4000)

    def _assert_all_values_between(self, sample, lower, upper):
        for value in sample.get_snapshot().get_values():
            self.assertTrue(value >= lower and value < upper)

########NEW FILE########
__FILENAME__ = test_histogram
from __future__ import division, absolute_import

from unittest2 import TestCase

from yunomi.compat import xrange
from yunomi.core.histogram import Histogram


class HistogramTests(TestCase):

    def setUp(self):
        self.histogram_b = Histogram.get_biased()
        self.histogram_u = Histogram.get_uniform()

    def test_unique_biased_histogram(self):
        new_histogram = Histogram.get_biased()
        self.assertIsNot(new_histogram.sample, self.histogram_b.sample)

    def test_unique_uniform_histogram(self):
        new_histogram = Histogram.get_uniform()
        self.assertIsNot(new_histogram.sample, self.histogram_u.sample)

    def test_empty_histogram(self):
        for histogram in self.histogram_b, self.histogram_u:
            histogram.clear()
            self.assertEqual(histogram.get_count(), 0)
            self.assertAlmostEqual(histogram.get_max(), 0)
            self.assertAlmostEqual(histogram.get_min(), 0)
            self.assertAlmostEqual(histogram.get_mean(), 0)
            self.assertAlmostEqual(histogram.get_std_dev(), 0)
            self.assertAlmostEqual(histogram.get_sum(), 0)

            snapshot = histogram.get_snapshot()
            self.assertAlmostEqual(snapshot.get_median(), 0)
            self.assertAlmostEqual(snapshot.get_75th_percentile(), 0)
            self.assertAlmostEqual(snapshot.get_99th_percentile(), 0)
            self.assertAlmostEqual(snapshot.size(), 0)

    def test_histogram_with_1000_elements(self):
        for histogram in self.histogram_b, self.histogram_u:
            histogram.clear()
            for i in xrange(1, 1001):
                histogram.update(i)

            self.assertEqual(histogram.get_count(), 1000)
            self.assertAlmostEqual(histogram.get_max(), 1000)
            self.assertAlmostEqual(histogram.get_min(), 1)
            self.assertAlmostEqual(histogram.get_mean(), 500.5)
            self.assertAlmostEqual(histogram.get_std_dev(), 288.8194360957494, places=3)
            self.assertAlmostEqual(histogram.get_sum(), 500500)

            snapshot = histogram.get_snapshot()
            self.assertAlmostEqual(snapshot.get_median(), 500.5)
            self.assertAlmostEqual(snapshot.get_75th_percentile(), 750.75)
            self.assertAlmostEqual(snapshot.get_99th_percentile(), 990.99)
            self.assertAlmostEqual(snapshot.size(), 1000)

########NEW FILE########
__FILENAME__ = test_meter
from __future__ import division, absolute_import

import mock
from unittest2 import TestCase

from yunomi.compat import xrange
from yunomi.core.meter import Meter


class MeterTests(TestCase):

    def test_a_blankmeter(self):
        self.meter = Meter("test")
        self.assertEqual(self.meter.get_count(), 0)
        self.assertAlmostEqual(self.meter.get_mean_rate(), 0.0)

    def test_meter_with_three_events(self):
        self.meter = Meter("test")
        self.meter.mark(3)
        self.assertEqual(self.meter.get_count(), 3)

    @mock.patch("yunomi.core.meter.time")
    def test_mean_rate_one_per_second(self, time_mock):
        time_mock.return_value = 0.0
        self.meter = Meter("test")
        for i in xrange(10):
            self.meter.mark()
            time_mock.return_value += 1

        self.meter._tick()
        self.assertAlmostEqual(self.meter.get_mean_rate(), 1)

    @mock.patch("yunomi.stats.ewma.time")
    def test_meter_EWMA_rates(self, time_mock):
        time_mock.return_value = 0.0
        self.meter = Meter("test")
        self.meter.mark(3)
        time_mock.return_value += 5

        for one, five, fifteen in [(0.6, 0.6, 0.6),
                                   (0.22072766, 0.49123845, 0.56130419),
                                   (0.08120117, 0.40219203, 0.52510399),
                                   (0.02987224, 0.32928698, 0.49123845),
                                   (0.01098938, 0.26959738, 0.45955700),
                                   (0.00404277, 0.22072766, 0.42991879),
                                   (0.00148725, 0.18071653, 0.40219203),
                                   (0.00054713, 0.14795818, 0.37625345),
                                   (0.00020128, 0.12113791, 0.35198773),
                                   (0.00007405, 0.09917933, 0.32928698)]:
            self.assertAlmostEqual(self.meter.get_one_minute_rate(), one)
            self.assertAlmostEqual(self.meter.get_five_minute_rate(), five)
            self.assertAlmostEqual(self.meter.get_fifteen_minute_rate(), fifteen)
            time_mock.return_value += 60

########NEW FILE########
__FILENAME__ = test_metrics_registry
from __future__ import division, absolute_import

import mock
from unittest2 import TestCase

from yunomi.compat import xrange
from yunomi.core.metrics_registry import (MetricsRegistry, counter, histogram,
                                          meter, timer, count_calls,
                                          meter_calls, hist_calls, time_calls)
from yunomi.tests.util import Clock


class MetricsRegistryTests(TestCase):

    def setUp(self):
        self.twisted_clock = Clock()
        self.registry = MetricsRegistry(clock=self.twisted_clock.seconds)

    def test_empty_registry(self):
        self.assertEqual(len(self.registry.dump_metrics()), 0)

    def test_getters_create_metrics(self):
        self.registry.counter("counter")
        self.registry.histogram("histogram")
        self.registry.meter("meter")
        self.registry.timer("timer")

        dump = self.registry.dump_metrics()

        self.assertEqual(len(dump), 25)
        metric_names = ("counter_count", "histogram_avg", "histogram_max",
                        "histogram_min", "histogram_std_dev",
                        "histogram_75_percentile", "histogram_98_percentile",
                        "histogram_99_percentile", "histogram_999_percentile",
                        "meter_15m_rate", "meter_5m_rate", "meter_1m_rate",
                        "meter_mean_rate", "timer_avg", "timer_max",
                        "timer_min", "timer_std_dev", "timer_75_percentile",
                        "timer_98_percentile", "timer_99_percentile",
                        "timer_999_percentile", "timer_15m_rate",
                        "timer_5m_rate", "timer_1m_rate", "timer_mean_rate")
        for stat in dump:
            self.assertTrue(stat["name"] in metric_names)
            self.assertEqual(stat["value"], 0)

    def test_count_calls_decorator(self):
        @count_calls
        def test():
            pass

        for i in xrange(10):
            test()
        self.assertEqual(counter("test_calls").get_count(), 10)

    @mock.patch("yunomi.core.meter.time")
    def test_meter_calls_decorator(self, time_mock):
        time_mock.return_value = 0
        @meter_calls
        def test():
            pass

        for i in xrange(10):
            test()
        time_mock.return_value = 10
        self.assertAlmostEqual(meter("test_calls").get_mean_rate(), 1.0)


    def test_hist_calls_decorator(self):
        @hist_calls
        def test(n):
            return n

        for i in xrange(1, 11):
            test(i)

        _histogram = histogram("test_calls")
        snapshot = _histogram.get_snapshot()
        self.assertAlmostEqual(_histogram.get_mean(), 5.5)
        self.assertEqual(_histogram.get_max(), 10)
        self.assertEqual(_histogram.get_min(), 1)
        self.assertAlmostEqual(_histogram.get_std_dev(), 3.02765, places=5)
        self.assertAlmostEqual(_histogram.get_variance(), 9.16667, places=5)
        self.assertAlmostEqual(snapshot.get_75th_percentile(), 8.25)
        self.assertAlmostEqual(snapshot.get_98th_percentile(), 10.0)
        self.assertAlmostEqual(snapshot.get_99th_percentile(), 10.0)
        self.assertAlmostEqual(snapshot.get_999th_percentile(), 10.0)

    @mock.patch("yunomi.core.metrics_registry.time")
    def test_time_calls_decorator(self, time_mock):
        time_mock.return_value = 0.0
        @time_calls
        def test():
            time_mock.return_value += 1.0

        for i in xrange(10):
            test()
        _timer = timer("test_calls")
        snapshot = _timer.get_snapshot()
        self.assertEqual(_timer.get_count(), 10)
        self.assertEqual(_timer.get_max(), 1)
        self.assertEqual(_timer.get_min(), 1)
        self.assertAlmostEqual(_timer.get_std_dev(), 0)
        self.assertAlmostEqual(snapshot.get_75th_percentile(), 1.0)
        self.assertAlmostEqual(snapshot.get_98th_percentile(), 1.0)
        self.assertAlmostEqual(snapshot.get_99th_percentile(), 1.0)
        self.assertAlmostEqual(snapshot.get_999th_percentile(), 1.0)

    def test_count_calls_decorator_returns_original_return_value(self):
        @count_calls
        def test():
            return 1
        self.assertEqual(test(), 1)

    def test_meter_calls_decorator_returns_original_return_value(self):
        @meter_calls
        def test():
            return 1
        self.assertEqual(test(), 1)

    def test_hist_calls_decorator_returns_original_return_value(self):
        @hist_calls
        def test():
            return 1
        self.assertEqual(test(), 1)

    def test_time_calls_decorator_returns_original_return_value(self):
        @time_calls
        def test():
            return 1
        self.assertEqual(test(), 1)

    def test_count_calls_decorator_keeps_function_name(self):
        @count_calls
        def test():
            pass
        self.assertEqual(test.__name__, 'test')

    def test_meter_calls_decorator_keeps_function_name(self):
        @meter_calls
        def test():
            pass
        self.assertEqual(test.__name__, 'test')

    def test_hist_calls_decorator_keeps_function_name(self):
        @hist_calls
        def test():
            pass
        self.assertEqual(test.__name__, 'test')

    def test_time_calls_decorator_keeps_function_name(self):
        @time_calls
        def test():
            pass
        self.assertEqual(test.__name__, 'test')

    def test_count_calls_decorator_propagates_errors(self):
        @count_calls
        def test():
            raise Exception('what')
        self.assertRaises(Exception, test)

    def test_meter_calls_decorator_propagates_errors(self):
        @meter_calls
        def test():
            raise Exception('what')
        self.assertRaises(Exception, test)

    def test_hist_calls_decorator_propagates_errors(self):
        @hist_calls
        def test():
            raise Exception('what')
        self.assertRaises(Exception, test)

    def test_time_calls_decorator_propagates_errors(self):
        @time_calls
        def test():
            raise Exception('what')
        self.assertRaises(Exception, test)

########NEW FILE########
__FILENAME__ = test_snapshot
from __future__ import division, absolute_import

from unittest2 import TestCase

from yunomi.stats.snapshot import Snapshot


class SnapshotTests(TestCase):
    def setUp(self):
        self.snapshot = Snapshot([5, 1, 2, 3, 4])

    def test_small_quantiles_are_the_first_value(self):
        self.assertAlmostEqual(self.snapshot.get_value(0.0), 1)

    def test_big_quantiles_are_the_last_value(self):
        self.assertAlmostEqual(self.snapshot.get_value(1.0), 5)

    def test_has_a_median(self):
        self.assertAlmostEqual(self.snapshot.get_median(), 3)

    def test_percentiles(self):
        percentiles = [(4.5, self.snapshot.get_75th_percentile),
                    (5, self.snapshot.get_98th_percentile),
                    (5, self.snapshot.get_99th_percentile),
                    (5, self.snapshot.get_999th_percentile)]

        for val, func in percentiles:
            self.assertAlmostEqual(func(), val)

    def test_has_values(self):
        self.assertEquals(self.snapshot.get_values(), [1, 2, 3, 4, 5])

    def test_has_a_size(self):
        self.assertEquals(self.snapshot.size(), 5)

########NEW FILE########
__FILENAME__ = test_timer
from __future__ import division, absolute_import

from unittest2 import TestCase

from yunomi.core.timer import Timer


class TimerTests(TestCase):

    def setUp(self):
        self.timer = Timer()

    def test_blank_timer(self):
        self.assertEqual(self.timer.get_count(), 0)
        self.assertAlmostEqual(self.timer.get_max(), 0.0)
        self.assertAlmostEqual(self.timer.get_min(), 0.0)
        self.assertAlmostEqual(self.timer.get_mean(), 0.0)
        self.assertAlmostEqual(self.timer.get_std_dev(), 0.0)

        snapshot = self.timer.get_snapshot()
        self.assertAlmostEqual(snapshot.get_median(), 0.0)
        self.assertAlmostEqual(snapshot.get_75th_percentile(), 0.0)
        self.assertAlmostEqual(snapshot.get_99th_percentile(), 0.0)
        self.assertEqual(self.timer.get_snapshot().size(), 0)

        self.assertAlmostEqual(self.timer.get_mean_rate(), 0.0)
        self.assertAlmostEqual(self.timer.get_one_minute_rate(), 0.0)
        self.assertAlmostEqual(self.timer.get_five_minute_rate(), 0.0)
        self.assertAlmostEqual(self.timer.get_fifteen_minute_rate(), 0.0)

    def test_timing_a_series_of_events(self):
        self.timer = Timer()
        self.timer.update(10)
        self.timer.update(20)
        self.timer.update(20)
        self.timer.update(30)
        self.timer.update(40)

        self.assertEqual(self.timer.get_count(), 5)
        self.assertAlmostEqual(self.timer.get_max(), 40.0)
        self.assertAlmostEqual(self.timer.get_min(), 10.0)
        self.assertAlmostEqual(self.timer.get_mean(), 24.0)
        self.assertAlmostEqual(self.timer.get_std_dev(), 11.401, places=2)

        snapshot = self.timer.get_snapshot()
        self.assertAlmostEqual(snapshot.get_median(), 20.0)
        self.assertAlmostEqual(snapshot.get_75th_percentile(), 35.0)
        self.assertAlmostEqual(snapshot.get_99th_percentile(), 40.0)
        self.assertEqual(self.timer.get_snapshot().get_values(),
                         [10.0, 20.0, 20.0, 30.0, 40.0])

    def test_timing_variant_values(self):
        self.timer.clear()
        self.timer.update(9223372036854775807)
        self.timer.update(0)
        self.assertAlmostEqual(self.timer.get_std_dev(), 6521908912666392000)

########NEW FILE########
__FILENAME__ = test_uniform_sample
from __future__ import division, absolute_import

from unittest2 import TestCase

from yunomi.compat import xrange
from yunomi.stats.uniform_sample import UniformSample


class UniformSampleTests(TestCase):

    def test_a_sample_of_100_out_of_1000_elements(self):
        sample = UniformSample(100)
        for i in xrange(1000):
            sample.update(i)
        snapshot = sample.get_snapshot()

        self.assertEqual(sample.size(), 100)
        self.assertEqual(snapshot.size(), 100)

        for i in snapshot.get_values():
            self.assertTrue(i < 1000 and i >= 0)

########NEW FILE########
__FILENAME__ = util
from __future__ import division, absolute_import


class Clock(object):
    """
    Stripped down version of C{twisted.internet.task.Clock} from Twisted 13.0.0
    """
    rightNow = 0.0

    def seconds(self):
        """
        Pretend to be time.time().

        @rtype: C{float}
        @return: The time which should be considered the current time.
        """
        return self.rightNow

    def advance(self, amount):
        """
        Move time on this clock forward by the given amount.

        @type amount: C{float}
        @param amount: The number of seconds which to advance this clock's
        time.
        """
        self.rightNow += amount


__all__ = [
    Clock
]

########NEW FILE########
