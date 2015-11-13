__FILENAME__ = axis
from staste import redis

class Axis(object):
    def __init__(self, choices):
        self.choices = choices

    def get_field_id_parts(self, value):
        if not value in self.choices:
            raise ValueError('Invalid value: %s, choices are: %s'
                             % (value, self.choices))
        
        return ['__all__', str(value)]
    

    def get_field_main_id(self, value):
        if not value:
            return '__all__'

        return str(value)

    def get_choices(self, key):
        return self.choices



class StoredChoiceAxis(Axis):
    """An Axis for which you don't know values in advance

    Stores all values in a set at some key in Redis"""

    store_choice = True

    def __init__(self):
        pass

    def get_field_id_parts(self, value):
        return ['__all__', str(value)]

    def get_choices(self, key):
        return redis.smembers(key)

########NEW FILE########
__FILENAME__ = views
import datetime

from django.views.generic import TemplateView

from staste.dateaxis import DATE_SCALES_AND_EXPIRATIONS



TIMESCALES = ['day', 'hour', 'minute']

DEFAULT_TIMESCALE = 'hour'


class Chart(TemplateView):
    metrica = None

    def timespan(self, vs):
        for scale, _ in DATE_SCALES_AND_EXPIRATIONS:
            try:
                timespan_val = int(self.request.GET.get('timespan__%s' % scale))
            except TypeError:
                break

            vs = vs.timespan(**{scale: timespan_val})

        return vs
    
    def get_metrica_values(self):
        vs = self.metrica.values()

        vs = self.timespan(vs)        
        
        return vs

    
class PieChart(Chart):
    template_name = 'staste/charts/pie.html'
    axis_keyword = None

    def get_context_data(self):
        values = self.get_metrica_values().iterate(self.axis_keyword)

        axis_data = {'name': self.axis_keyword,
                     'values': list(values)}
        
        return {'axis': axis_data}

        
class TimelineChart(Chart):
    template_name = 'staste/charts/timeline.html'

    def get_context_data(self):
        values = self.get_metrica_values().iterate()

        axis_data = {'name': 'Timeline',
                     'values': list(values)}
        
        return {'axis': axis_data}

   
class TimeserieChart(Chart):
    """
    Shows the current metric's chosen axis in the context of the specified time period (from somewhen back untill now).
    Defining view's class parameters:
        TimeserieChart.metrica                            - an instance of staste.metrica.Metrica class - 
                                             specifies the metric the view is dealing with;
        TimeserieChart.template_name                      - specifies the template the output would be rendered with.
    Context:
       {{ axis.name }}                         - the name of presented axis (described below);
       {{ axis.data }}                         - a dict, where keys are current axis' possible choices and values are lists of tuples
                                             of time-marked results
                                             (e.g. {
                                                    'male':   [
                                                                (datetime.datetime(2007, 1, 2, 3, 4, 5), 12),
                                                                (datetime.datetime(2007, 1, 2, 4, 4, 5), 7),
                                                              ],
                                                    'female': [
                                                                (datetime.datetime(2007, 1, 2, 3, 4, 5), 9),
                                                                (datetime.datetime(2007, 1, 2, 4, 4, 5), 21),
                                                              ],
                                                    }
                                             );
    Accepts GET-parameters:
        'show_axis'                        - specifies the metric's axis to present (e.g. '?show_axis=gender'.);
                                             default = current metric's first axis;
        a set of '{timescale}__ago' params - where {timescale} in ['year', 'month', 'day', 'hour', 'minute'] - 
                                             defines a period of time 'ago' for which the results would be aggregated
                                            (e.g. '?day__ago=2' would provide you with data regarding the past two years);
                                            default is 5 minutes;
        'timescale'                        - a timescale parameter, defines the discreteness of aggregated data
                                            (e.g. '?timescale=minute' will provide you with 'per-minute' statistic);
                                            default = 'hour'.
        'hide_total'                       - defines if the 'total' value over all choices is concealed.
        'clean_date'                       - defines the format of chart dateaxis points annotation (e.g. "7 hrs ago" or "5th Jan 2007");
                                             minute is the smallest unit to show.
                                            
        A full example:
            http://mysite.com/path_to_this_view/?show_axis=age&day_ago=3&hour_ago=1&timescale=hour
            will show you frequency of inclision of all visitors' ages over the past 73 hours.
        
        Note, that you don't want to use some highly distributed value as 'show_axis' parameter, due to all of those cases would be drawn in your chart and would
        certainly flood it over.      
    """
    template_name = 'staste/charts/timeserie.html'

    def get_context_data(self):       
        axis_displayed = self.get_axis_displayed()  
        
        values = self.get_timeserie(axis_displayed)
        
        clean_date = self.request.GET.get('clean_date', False) != False
        
        axis_data = {'name': 'Timeline: %s statistic.' % axis_displayed,
                     'data': values,}
                     
        return {
                'axis': axis_data,
                'axes': dict(self.metrica.axes).keys(),
                'current_axis': axis_displayed,
                'clean_date': clean_date,
                'scales': TIMESCALES,
                'current_scale': self.timescale,
                'time_since_params': '&'.join(['%s__ago=%i' % (k[:-1], v) for k, v in self.time_since_kwargs.items()]),
                }
        
    def get_timescale(self):
        time_scale = self.request.GET.get('timescale')    
        if time_scale in TIMESCALES:
            return time_scale        
        return DEFAULT_TIMESCALE
        
    def get_axis_displayed(self):
        axis_displayed = self.request.GET.get('show_axis')
        if axis_displayed in dict(self.metrica.axes).keys():
            return axis_displayed
        return self.metrica.axes[0][0]
        
    def get_time_since_kwargs(self):
        time_since_kwargs = {}
        for scale in TIMESCALES:
            try:      
                time_since_for_scale = int(self.request.GET.get('%s__ago' % scale))
                time_since_kwargs.update({'%ss' % scale: time_since_for_scale})
            except (TypeError, ValueError):
                pass
        return time_since_kwargs or {'%ss' % self.timescale: 5,}
        
    def get_timeserie(self, axis_displayed):
        time_until = datetime.datetime.now()
        self.timescale = self.get_timescale()
        self.time_since_kwargs = self.get_time_since_kwargs()
        timeserie_params = {                            
                            'since': time_until - datetime.timedelta(**self.time_since_kwargs),
                            'until': time_until,
                            'scale': self.timescale,  
                           }
       
        values = {}
        if not self.request.GET.get('hide_total', False):
            values.update({'total': self.get_metrica_values().timeserie(**timeserie_params)})
        for item in self.metrica.choices(axis_displayed):
            values.update({item: self.get_metrica_values()\
                                    .filter(**{axis_displayed: item})\
                                    .timeserie(**timeserie_params)})
        return values


class LatestCountAndAverageChart(Chart):
    template_name = 'staste/charts/latest_count_and_average.html'

    title = 'Counts and Averages'

    scales = [#'year', 'month', 'day',
        'hour', 'minute']

    scale_deltas = {'year': datetime.timedelta(days=365*5),
                    'month': datetime.timedelta(days=730),
                    'day': datetime.timedelta(days=31),
                    'hour': datetime.timedelta(days=2),
                    'minute': datetime.timedelta(minutes=30)}

    def get_context_data(self):

        # parameters
        scale = self.request.GET.get('scale')
        if scale not in self.scales:
            scale = 'minute'

        views = list(self.metrica.choices('view'))
            
        view = self.request.GET.get('view')
        if view not in views:
            view = ''


        # values
        vs = self.metrica.values()

        if view:
            vs = vs.filter(view=view)

        since = datetime.datetime.now() - self.scale_deltas[scale]

        data = list(vs.timeserie_counts_and_averages(since,
                                                     datetime.datetime.now(),
                                                     scale=scale))
        
        return {'title': self.title,
                'axis': {'data': data},
                'scales': self.scales,
                'current_scale': scale,
                'views': views,
                'current_view': view
                }

########NEW FILE########
__FILENAME__ = dateaxis
"""DateTime axis is special-cased because it's simpler to build everything around date

For example, using separate hash keys for dates allows to set different expiration datees for keys."""
import datetime
import calendar

from dateutil import rrule

from collections import namedtuple

from staste import redis


def days_to_seconds(days):
    """Converts days to seconds. No ".total_seconds()" in 2.6"""
    return days * 24 * 60 * 60


# Please keep in mind that years are special-cased (I got to think about it)
# cause their range is not hard specified, but stored in Redis instead.

DATE_SCALES_AND_EXPIRATIONS = [('year', 0),
                               ('month', days_to_seconds(3*365)),
                               ('day', days_to_seconds(185)),
                               ('hour', days_to_seconds(14)),
                               ('minute', days_to_seconds(1))]

DATE_SCALES_DICT = dict(DATE_SCALES_AND_EXPIRATIONS)

DATE_SCALES_RANGES = {'month': lambda **t: (1, 12),
                      'day': lambda year, month, **t: (1, calendar.monthrange(year, month)[1]),
                      'hour': lambda **t: (0, 23),
                      'minute': lambda **t: (0, 59)}

DATE_SCALES_RRULE_KWARGS = {'year': {'freq': rrule.YEARLY,
                                     'bymonthday': 1},
                           'month': {'freq': rrule.MONTHLY,
                                     'bymonthday': 1},
                           'day': {'freq': rrule.DAILY},
                           'hour': {'freq': rrule.HOURLY},
                           'minute': {'freq': rrule.MINUTELY}}


# can be average
DATE_SCALES_DELTAS = {'year': datetime.timedelta(days=365),
                      'month': datetime.timedelta(days=30),
                      'day': datetime.timedelta(days=1),
                      'hour': datetime.timedelta(hours=1),
                      'minute': datetime.timedelta(minutes=1)}

DATE_SCALES_SCALE = {'year': lambda dt: datetime.datetime(dt.year, 1, 1),
                     'month': lambda dt: datetime.datetime(dt.year,
                                                           dt.month, 1),
                     'day': lambda dt: datetime.datetime(year=dt.year,
                                                         month=dt.month,
                                                         day=dt.day),
                     'hour': lambda dt: datetime.datetime(year=dt.year,
                                                          month=dt.month,
                                                          day=dt.day,
                                                          hour=dt.hour),
                     'minute': lambda dt: datetime.datetime(year=dt.year,
                                                          month=dt.month,
                                                          day=dt.day,
                                                          hour=dt.hour,
                                                          minute=dt.minute)}

# This is a tuple which is used by Metric.kick()
# to understand that it should be doing with a scale
DateScale = namedtuple('DateScale', ['id', 'expiration', 'value', 'store'])


class DateAxis(object):
    """This is a special-cased axis of DateTime"""
    
    def scales(self, date):
        """Yields DateScale objects for all scales on which the event should be stored"""
        yield DateScale('__all__', 0, '', False)

        id_parts = []
        for scale, scale_expiration in DATE_SCALES_AND_EXPIRATIONS:
            value = getattr(date, scale)
            
            id_parts += [scale, str(value)]
            yield DateScale(':'.join(id_parts),
                            scale_expiration,
                            value,
                            'years' if scale == 'year' else False)
            

    def timespan_to_id(self, **timespan):
        """Returns an string part of the hash key for a timespan

        A timespan is a dict of date scales"""

        if not timespan:
            return '__all__'
        
        id_parts = self._timespan_to_id_parts(**timespan)

        return ':'.join(id_parts)
    

    def iterate(self, mv):
        """Iterates on all date values for scale of MetricaValues. Yields a number and an id (string part of the hash key)

        For example, if MetricaValues is filtered by month (like .timespan(month=2)), this will iterate by month days."""
        
        id_parts = self._timespan_to_id_parts(**mv._timespan)

        scale_n = len(id_parts) / 2        
        try:
            scale_ = DATE_SCALES_AND_EXPIRATIONS[scale_n]
        except IndexError:
            raise ValueError("Can't iterate further than %s"
                             % DATE_SCALES_AND_EXPIRATIONS[-1][0])
        scale = scale_[0]

        for i in self.get_scale_range(scale, mv):
            yield int(i), ':'.join(id_parts + [scale, str(i)])
            

    def get_scale_range(self, scale, mv):
        """Returns a range of values for a scale, within some space of statistical values"""
        
        # okay, it's not very configurable, but I tried
        if scale == 'year':
            set_key = '%s:years' % mv.metrica.key_prefix()
            return redis.smembers(set_key)
        
        return xrange(*DATE_SCALES_RANGES[scale](**mv._timespan))


    def timeserie(self, since, until, max_scale=None):
        """Returns a list of time points and scales we can have information about"""

        now = datetime.datetime.now()

        points = []
        
        for scale, expiration in reversed(DATE_SCALES_AND_EXPIRATIONS):
            if max_scale:
                if scale == max_scale:
                    max_scale = None
                else:
                    continue
                
            if expiration:
                scale_since = now - datetime.timedelta(seconds=expiration)

                if scale_since >= until:
                    continue

                if scale_since < since:
                    scale_since = since

            else:
                scale_since = since

            points = list(self.scale_timeserie(scale, scale_since, until)) + points

            until = scale_since

            if until <= since:
                break

        for scale, point in points:
            yield point, ':'.join(self._datetime_to_id_parts(scale, point))
            

    def scale_timeserie(self, scale, since, until):
        rr = rrule.rrule(dtstart=since,
                         until=until,
                         **DATE_SCALES_RRULE_KWARGS[scale])

        for point in rr:
            yield scale, self.scale_point(scale, point)

    def scale_point(self, scale, point):
        return DATE_SCALES_SCALE[scale](point) + DATE_SCALES_DELTAS[scale]/2
    

    def _datetime_to_id_parts(self, max_scale, dt):
        id_parts = []
        
        for scale, scale_expiration in DATE_SCALES_AND_EXPIRATIONS:
            val = getattr(dt, scale)
            id_parts += [scale, str(val)]

            if scale == max_scale:
                return id_parts

        raise ValueError('Invalid scale: %s' % scale)

    
    def _timespan_to_id_parts(self, **timespan):
        """Converts timespan (a dict of date scales) to a joinable list of id parts.

        {'year': 2011, 'month': 10} => ['year', '2011', 'month': 10]"""
        
        for k in timespan:
            if k not in DATE_SCALES_DICT:
                raise TypeError('Invalid date argument: "%s"' % k)

        id_parts = []
        for scale, scale_expiration in DATE_SCALES_AND_EXPIRATIONS:
            try:
                val = timespan.pop(scale)
            except KeyError:
                if timespan:
                    raise TypeError("You should have specified %s" % scale)

                # all kwargs are gone!
                break
                
            id_parts += [scale, str(val)]

        return id_parts


# We need only one such Axis object, and it's completely thread-safe
DATE_AXIS = DateAxis()
                

########NEW FILE########
__FILENAME__ = metrica
import datetime
import itertools

from django.conf import settings

from staste import redis
from staste.dateaxis import DATE_AXIS

class Metrica(object):
    """Metrica is some class of events you want to count, like "site visits".

    Metrica is actually a space of all such countable events.

    It consists of Axes, which represent some parameters of an event: for example, a page URL, or whether the visitor was logged in. Please take a look at staste.axes.Axis.

    Every time the event happens, you call Metrica.kick() function with all the parameters for all axes specified.
    """

    def __init__(self, name, axes, multiplier=None):
        """Constructor of a Metrica

        name - should be a unique (among your metrics) string, it will be used in Redis identifiers (lots of them)
        axes - a list/iterable of tuples: (keyword, staste.axes.Axis object). can be empty
        multiplier - you can multiply all values you provide. it's useful since Redis does not understand floating point increments. (all totals() will be divided back by this)"""
        self.name = str(name)
        self.axes = list(axes)
        self.date_axis = DATE_AXIS
        self.multiplier = float(multiplier) if multiplier else 1
        # don't produce float output in the simple case
        

    def kick(self, value=1, date=None, **kwargs):
        """Registers an event with parameters (for each of axis)"""
        date = date or datetime.datetime.now()
        value = int(self.multiplier * value)
        
        hash_key_prefix = self.key_prefix()

        choices_sets_to_append = []
        hash_field_id_parts = []

        for axis_kw, axis in self.axes:
            param_value = kwargs.pop(axis_kw, None)
            
            hash_field_id_parts.append(
                list(axis.get_field_id_parts(param_value))
                )

            try:
                if axis.store_choice:
                    set_key = '__choices__:%s' % axis_kw
                    choices_sets_to_append.append((set_key, param_value))
            except AttributeError: # 'duck typing'
                pass
                

        if kwargs:
            raise TypeError("Invalid kwargs left: %s" % kwargs)

        choices_sets_to_append = filter(None, choices_sets_to_append)
            
        # Here we go: bumping all counters out there
        pipe = redis.pipeline(transaction=False)

        for date_scale in self.date_axis.scales(date):
            hash_key = '%s:%s' % (hash_key_prefix, date_scale.id)
            
            for parts in itertools.product(*hash_field_id_parts):
                hash_field_id = ':'.join(parts)

                self._increment(pipe, hash_key, hash_field_id, value)
            
            if date_scale.expiration:
                pipe.expire(hash_key, date_scale.expiration)

            if date_scale.store:
                choices_sets_to_append.append((date_scale.store, date_scale.value))

        for key, s_value in choices_sets_to_append:
            pipe.sadd('%s:%s' % (hash_key_prefix, key),
                      s_value)

        pipe.execute()

    def choices(self, axis_kw):
        return dict(self.axes)[axis_kw].get_choices(
            self.key_for_axis_choices(axis_kw)
            )

    # STATISTICS

    def values(self):
        """Returns a MetricaValues object for all the data out there"""
        return MetricaValues(self)

    def timespan(self, **kwargs):
        """Returns a MetricaValues object limited to the spefic period in time

        Please keep in mind that the timespan can't be arbitraty, it can be only a specific year, month, day, hour or minute

        Example: mymetric.timespan(year=2011, month=3, day=2)"""
        return self.values().timespan(**kwargs)

    
    def filter(self, **kwargs):
        """Returns a MetricaValues object filtered by one or several axes"""
        return self.values().filter(**kwargs)

    def total(self, **kwargs):
        """Total count of events"""
        return self.values().total()

    # UTILS

    def key_prefix(self):
        metrics_prefix = settings.STASTE_METRICS_PREFIX
        
        return '%s:%s' % (metrics_prefix, self.name)

    def hash_field_id(self, **kwargs):
        hash_field_id_parts = []
        
        for axis_kw, axis in self.axes:
            hash_field_id_parts.append(
                axis.get_field_main_id(kwargs.pop(axis_kw, None))
                )

        if kwargs:
            raise TypeError("Invalid kwargs left: %s" % kwargs)

        return ':'.join(hash_field_id_parts)

    def get_axis(self, axis_kw):
        return dict(self.axes)[axis_kw]

    def key_for_axis_choices(self, axis_kw):
        return '%s:__choices__:%s' % (self.key_prefix(), axis_kw)

    def _increment(self, pipe, hash_key, hash_field_id, value):
        pipe.hincrby(hash_key, hash_field_id, value)

    




class MetricaValues(object):
    """A representation of a subset of Metrica statistical values

    Used for filtering"""
    
    def __init__(self, metrica, timespan=None, filter=None):
        """Constructor. You probably don't want to call it directly"""
        self.metrica = metrica
        self._timespan = timespan or {}
        self._filter = filter or {}

        # we should do it now to raise an error eagerly
        tp_id = self.metrica.date_axis.timespan_to_id(**self._timespan)
        self._hash_key = '%s:%s' % (self.metrica.key_prefix(),
                                    tp_id)
        self._hash_field_id = self.metrica.hash_field_id(**self._filter)


    # FILTERING
        
    def timespan(self, **kwargs):
        """Filter by timespan. Returns a new MetricaValues object"""
        
        tp = dict(self._timespan, **kwargs)
        return self.__class__(self.metrica, timespan=tp, filter=self._filter)

    def filter(self, **kwargs):
        fl = dict(self._filter, **kwargs)
        return self.__class__(self.metrica, timespan=self._timespan, filter=fl)

    # GETTING VALUES

    def total(self):
        """Total events count in the subset"""
        return int(redis.hget(self._hash_key, self._hash_field_id) or 0) / self.metrica.multiplier

    def timeserie(self, since, until, scale=None,
                  _hash_key_postfix='', _mult=None):
        mult = _mult or self.metrica.multiplier
        prefix = self.metrica.key_prefix()

        ts_points = self.metrica.date_axis.timeserie(since, until, scale)

        points = []
        pipe = redis.pipeline(transaction=False)

        for point, tp_id in ts_points:
            points.append(point)
            
            hash_key = '%s:%s%s' % (prefix, tp_id, _hash_key_postfix)
            pipe.hget(hash_key, self._hash_field_id)            

        values = pipe.execute()

        return zip(points, [int(v or 0) / mult for v in values])

    def iterate(self, axis=None):
        """Iterates on a MetricaValues set. Returns a list of (key, value) tuples.

        If axis is not specified, iterates on the next scale of a date axis. I.e. mymetric.timespan(year=2011).iterate() will iterate months."""
        if not axis:
            return self.iterate_on_dateaxis()

        return self._iterate(axis, self._hash_key, self.metrica.multiplier)

    def _iterate(self, axis, _hash_key, mult):
        keys = self.metrica.choices(axis)

        pipe = redis.pipeline(transaction=False)
        
        for key in keys:
            fl = dict(self._filter, **{axis: key})
            hash_field_id = self.metrica.hash_field_id(**fl)
            
            pipe.hget(_hash_key, hash_field_id)

        values = pipe.execute()

        return zip(keys, [int(v or 0) / mult for v in values])


    def iterate_on_dateaxis(self):
        """Iterates on the next scale of a date axis.

        I.e. mymetric.timespan(year=2011).iterate() will iterate months"""
        return self._iterate_on_dateaxis('', self.metrica.multiplier)

    def _iterate_on_dateaxis(self, _hash_key_postfix, mult):
        prefix = self.metrica.key_prefix()
        keys = []

        pipe = redis.pipeline(transaction=False)
        
        for key, tp_id in self.metrica.date_axis.iterate(self):
            keys.append(key)
            
            hash_key = '%s:%s' % (prefix, tp_id) + _hash_key_postfix
            
            pipe.hget(hash_key, self._hash_field_id)

        values = pipe.execute()

        return zip(keys, [int(v or 0) / mult for v in values])
            

    
class AveragedMetrica(Metrica):
    """AveragedMetrica works like a normal metrica, but also stores counts of the events. So you can ask for .average or .count"""
    
    def values(self):
        """Returns a MetricaValues object for all the data out there"""
        return AveragedMetricaValues(self)

    def average(self):
        return self.values().average()

    def count(self):
        return self.values().count()

    def _increment(self, pipe, hash_key, hash_field_id, value):
        super(AveragedMetrica, self)._increment(pipe, hash_key, hash_field_id, value)
        pipe.hincrby('%s:__len__' % hash_key, hash_field_id, 1)
                
    
        
class AveragedMetricaValues(MetricaValues):
    def average(self):
        return self.total() / self.count()

    def count(self):
        return int(redis.hget('%s:__len__' % self._hash_key,
                              self._hash_field_id) or 0)

    def iterate_counts(self, axis=None):
        if not axis:
            return self._iterate_on_dateaxis(':__len__', 1)

        hash_key = '%s:__len__' % self._hash_key
        
        return self._iterate(axis, hash_key, 1)

    def iterate_averages(self, axis=None):
        vals = self.iterate(axis)
        counts = self.iterate_counts(axis)

        for (k1, v1), (k2, v2) in zip(vals, counts):
            assert k1 == k2

            if not v2:
                yield k1, None
            else:
                yield k1, v1 / v2

    def timeserie_counts(self, since, until, scale=None):
        return self.timeserie(since, until, scale,
                              _hash_key_postfix=':__len__',
                              _mult=1)

    def timeserie_counts_and_averages(self, since, until, scale=None):

        vals = self.timeserie(since, until, scale)
        counts = self.timeserie_counts(since, until, scale)
        
        for (k1, total), (k2, count) in zip(vals, counts):
            assert k1 == k2

            try:
                avg = total / count
            except ZeroDivisionError:
                avg = 0

            yield k1, count, avg
        
    def timeserie_averages(self, since, until, scale=None):
        count_avgs = self.timeserie_counts_and_averages(self, since, until, scale)
        for k, count, avg in count_avgs:
            yield k, avg
            

########NEW FILE########
__FILENAME__ = middleware
import time

from staste.metrica import AveragedMetrica
from staste.axis import StoredChoiceAxis

response_time_metrica = AveragedMetrica('response_time_metrica',
                                        [('view', StoredChoiceAxis()),
                                         ('exception', StoredChoiceAxis())],
                                        multiplier=10000)

class ResponseTimeMiddleware(object):
    def process_request(self, request):
        request._staste_kicked = False
        request._staste_time_start = time.time()
        request._staste_params = {'view': None,
                                  'exception': None} 
        

    def process_view(self, request, view_func, view_args, view_kwargs):
        module = view_func.__module__
        try:
            func = getattr(view_func, '__name__', view_func.__class__.__name__)
        except AttributeError:
            func = 'unknown'
        
        request._staste_params['view'] = '%s.%s' % (module, func)

    def process_response(self, request, response):
        self._kick(request)

        return response

    def process_exception(self, request, exception):
        request._staste_params['exception'] = exception.__class__.__name__

        self._kick(request)
        

    def _kick(self, request):
        """In my experience, both process_exception and process_response can be called, or only process_exception"""

        if request._staste_kicked:
            return
        request._staste_kicked = True
        
        total_time = time.time() - request._staste_time_start

        response_time_metrica.kick(value=total_time,
                                   **request._staste_params)
        

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = staste_charts
from django import template
from django.utils.numberformat import format

register = template.Library()


@register.filter
def dotted_number(number):
    if type(number) == float:
        number = format(number, '.', 6)
    return number
    

########NEW FILE########
__FILENAME__ = tests
import datetime

from django.test import TestCase
from django.conf import settings

from staste import redis
from staste.metrica import Metrica, AveragedMetrica
from staste.axis import Axis, StoredChoiceAxis

def dtt(*args, **kwargs):
    return datetime.datetime(*args, **kwargs)

def dtp(**kwargs):
    return datetime.datetime.now() + datetime.timedelta(**kwargs)

def dtm(**kwargs):
    return datetime.datetime.now() - datetime.timedelta(**kwargs)


class TestStatsApi(TestCase):
    def removeAllKeys(self):
        # be careful.

        assert settings.STASTE_METRICS_PREFIX.endswith('_test')
        
        for k in redis.keys(settings.STASTE_METRICS_PREFIX + '*'):
            redis.delete(k)

    def setUp(self):
        self.old_prefix = getattr(settings, 'STASTE_METRICS_PREFIX', 'metrica')
        settings.STASTE_METRICS_PREFIX = self.old_prefix + '_test'
        
        self.removeAllKeys()

    def tearDown(self):
        self.removeAllKeys()
        
        settings.STASTE_METRICS_PREFIX = self.old_prefix
            
    def testTheSimplestCase(self):
        # so we want to count my guests
        # and they all alike to me, I'm a sociopath
        # so we want only to count them in time

        metrica = Metrica(name='guest_visits', axes=[])

        my_birthday = datetime.datetime(2006, 2, 7) # my 14th birthday. sorry for that
        day = datetime.timedelta(days=1)
        month = datetime.timedelta(days=31)

        yesterday = my_birthday - day
        before_yesterday = yesterday - day

        prev_month = my_birthday - month
        prev_month_and_a_day_back = prev_month - day

        metrica.kick(date=prev_month_and_a_day_back)
        for i in xrange(2):
            metrica.kick(date=prev_month)

            
        for i in xrange(5):
            metrica.kick(date=before_yesterday)

        for i in xrange(8):
            metrica.kick(date=yesterday)

        for i in xrange(20): # all my friends have come
            metrica.kick(date=my_birthday)


        # so, how many of them have visited me?

        self.assertEquals(metrica.timespan(year=2006, month=1).total(), 3)
        self.assertEquals(metrica.timespan(year=2006, month=2).total(), 33)
        self.assertEquals(metrica.timespan(year=2006).timespan(month=2).total(), 33)
        self.assertEquals(metrica.timespan(year=2006, month=3).total(), 0)
        self.assertEquals(metrica.timespan(year=2006, month=2, day=7).total(), 20)
        self.assertEquals(metrica.timespan(year=2006).total(), 36)
        self.assertEquals(metrica.total(), 36)
                

        # looks like that


        # and also an iterator

        months = list(metrica.timespan(year=2006).iterate())[:3]
        self.assertEquals(months, [(1, 3), (2, 33), (3, 0)])
            

        years = list(metrica.timespan().iterate())
        self.assertEquals(years, [(2006, 36)])

    def testSimpleAxis(self):
        # so I grew older, and I had learned
        # how to tell if it's a boy or a girl

        gender_axis = Axis(choices=['boy', 'girl'])
        metrica = Metrica(name='guest_visits_gender', axes=[('gender', gender_axis)])

        my_birthday = datetime.datetime(2007, 2, 7)
        # my 15th birthday.
        # you know what? I hated that year

        
        day = datetime.timedelta(days=1)
        month = datetime.timedelta(days=31)

        yesterday = my_birthday - day
        before_yesterday = yesterday - day

        prev_month = my_birthday - month
        prev_month_and_a_day_back = prev_month - day

        # my best friend came, we were playing video games
        metrica.kick(date=prev_month_and_a_day_back, gender='boy')
        
        metrica.kick(date=prev_month, gender='girl')
        metrica.kick(date=prev_month, gender='girl') # I got lucky
            
        for i in xrange(5):
            metrica.kick(date=before_yesterday, gender='boy')
            # we got really drunk

        for i in xrange(4):
            metrica.kick(date=yesterday, gender='girl')
            metrica.kick(date=yesterday, gender='boy')
            # they came in pairs. I was FOREVER ALONE
            
        for i in xrange(18): # all my friends have come
            metrica.kick(date=my_birthday, gender='boy')
        for i in xrange(2): # and two girls
            metrica.kick(date=my_birthday, gender='girl')

        # let's count them!
        
        self.assertEquals(metrica.timespan(year=2007).total(), 36)
        self.assertEquals(metrica.filter(gender='girl').total(), 8)
        self.assertEquals(metrica.timespan(year=2007, month=2).filter(gender='boy').total(), 27)

        genders = set(metrica.timespan().iterate('gender'))
        self.assertEquals(genders, set([('girl', 8), ('boy', 28)]))

        

    def testMultipleAndStrangeAxis(self):
        # I'm eighteen, and I don't want problems with laws
        # so I ask everyone at my parties about their age
        # and I don't give them choices
        
        gender_axis = Axis(choices=['boy', 'girl'])
        age_axis = StoredChoiceAxis()
        metrica = Metrica(name='guest_visits_gender_age',
                          axes=[('gender', gender_axis),
                                ('age', age_axis)])


        my_birthday = datetime.datetime(2010, 2, 7)

        day = datetime.timedelta(days=1)
        month = datetime.timedelta(days=31)

        yesterday = my_birthday - day
        before_yesterday = yesterday - day

        prev_month = my_birthday - month
        prev_month_and_a_day_back = prev_month - day


        # my best friend came, we were playing video games
        metrica.kick(date=prev_month_and_a_day_back,
                     gender='boy',
                     age=17)
        
        metrica.kick(date=prev_month,
                     gender='girl',
                     age=18)
        metrica.kick(date=prev_month,
                     gender='girl',
                     age=19) # I got lucky
            
        for i in xrange(5):
            metrica.kick(date=before_yesterday, gender='boy', age=18)
            # as always

        for i in xrange(4):
            metrica.kick(date=yesterday, gender='girl', age=17)
            metrica.kick(date=yesterday, gender='boy', age=17)
            # they came in pairs. oh young people
            
        for i in xrange(12): # all my friends have come
            metrica.kick(date=my_birthday, gender='boy', age=18)
        for i in xrange(6):
            metrica.kick(date=my_birthday, gender='boy', age=17)
        for i in xrange(2): # and two girls. they were old
            metrica.kick(date=my_birthday, gender='girl', age=19)
        # also, granddaddy. big boy
        metrica.kick(date=my_birthday, gender='boy', age=120)
        
            

        # let's count them!
        self.assertEquals(metrica.timespan(year=2010).total(), 37)
        self.assertEquals(metrica.filter(gender='girl').total(), 8)
        self.assertEquals(metrica.filter(gender='girl', age=19).total(), 3)
        self.assertEquals(metrica.filter(gender='boy').timespan(year=2010, month=2).filter(age=17).total(), 10)

        ages = metrica.timespan(year=2010, month=2).filter(gender='boy').iterate('age')
        self.assertEquals(set(ages), set([('120', 1), ('19', 0), ('17', 10), ('18', 17)]))



    def testWeighedMetrics(self):
        metrica = Metrica(name='some_weighed_metrics', axes=[], multiplier=100)

        d1 = datetime.datetime(2010, 2, 7)
        d2 = datetime.datetime(2010, 2, 8)
        d3 = datetime.datetime(2010, 2, 9)
        
        metrica.kick(date=d1, value=12)
        metrica.kick(date=d1, value=2)
        metrica.kick(date=d2, value=7.5)
        metrica.kick(date=d2, value=0.16)
        metrica.kick(date=d3)

        self.assertEquals(metrica.total(), 22.66)
        self.assertEquals(metrica.timespan(year=2010, month=2, day=8).total(), 7.66)

    def testAveragedMetrica(self):
        axis = Axis(choices=['a', 'b'])

        metrica = AveragedMetrica(name='some_averaged_metrica', axes=[('c', axis)], multiplier=100)

        d1 = datetime.datetime(2010, 2, 7)
        d2 = datetime.datetime(2010, 2, 8)
        d3 = datetime.datetime(2010, 2, 9)
        
        metrica.kick(date=d1, value=12, c='a')
        metrica.kick(date=d1, value=2, c='b')
        metrica.kick(date=d2, value=7.5, c='a')
        metrica.kick(date=d2, value=0.16, c='a')
        metrica.kick(date=d3, c='b')

        self.assertEquals(metrica.total(), 22.66)
        self.assertEquals(metrica.timespan(year=2010, month=2, day=8).total(), 7.66)
        self.assertEquals(metrica.count(), 5)
        self.assertEquals(metrica.timespan(year=2010, month=2, day=8).count(), 2)
        self.assertEquals(metrica.average(), 4.532)
        self.assertEquals(metrica.timespan(year=2010, month=2, day=8).average(), 3.83)

        days = list(metrica.timespan(year=2010, month=2).iterate_counts())[5:10]
        self.assertEquals(days, [(6, 0), (7, 2), (8, 2), (9, 1), (10, 0)])

        days = list(metrica.timespan(year=2010, month=2).iterate_averages())[5:10]
        self.assertEquals(days, [(6, None), (7, 7), (8, 3.83), (9, 1), (10, None)])

        chars = list(metrica.filter().iterate_counts('c'))
        self.assertEquals(chars, [('a', 3), ('b', 2)])

        chars = list(metrica.filter().iterate_averages('c'))
        self.assertEquals(chars, [('a', (12+7.5+0.16)/3), ('b', 1.5)])
        
    def testNewTimespans(self):
    
        metrica = Metrica(name='guest_visits', axes=[])

        my_birthday = datetime.datetime(2011, 2, 7)
        day = datetime.timedelta(days=1)
        month = datetime.timedelta(days=31)

        yesterday = my_birthday - day
        before_yesterday = yesterday - day

        prev_month = my_birthday - month
        prev_month_and_a_day_back = prev_month - day

        metrica.kick(date=prev_month_and_a_day_back)
        for i in xrange(2):
            metrica.kick(date=prev_month)
            
        for i in xrange(5):
            metrica.kick(date=before_yesterday)

        for i in xrange(8):
            metrica.kick(date=yesterday)

        for i in xrange(20):
            metrica.kick(date=my_birthday)

        print metrica.values().timeserie(dtt(2006, 1, 1), dtt(2011, 3, 1))

########NEW FILE########
__FILENAME__ = utils
    

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = deploy
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = base
from defaults import *

INSTALLED_APPS += ('staste',
                   'test_app')

STASTE_METRICS_PREFIX = 'staste'

try:
    from local_settings import *
    
    STASTE_REDIS_CONNECTION = {'host': GONDOR_REDIS_HOST,
                               'port': GONDOR_REDIS_PORT,
                               'password': GONDOR_REDIS_PASSWORD}


except ImportError:
    pass


DEBUG = True
TEMPLATE_DEBUG = True


MIDDLEWARE_CLASSES = (
    'staste.middleware.ResponseTimeMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',)

########NEW FILE########
__FILENAME__ = defaults
import os
here = lambda * x: os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)

PROJECT_ROOT = here('..')

root = lambda * x: os.path.join(os.path.abspath(PROJECT_ROOT), *x)

PROJECT_MODULE = '.'.join(__name__.split('.')[:-2])  # cut .settings.base


DEBUG = True

TEMPLATE_DEBUG = DEBUG


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': root('etc', 'development.db'),
    }
}

MEDIA_ROOT = root('static', 'uploads')
MEDIA_URL = '/static/uploads/'

STATIC_ROOT = root('static', 'assets')
STATIC_URL = '/static/assets/'

ADMIN_MEDIA_PREFIX = '/static/assets/admin/'

STATICFILES_DIRS = (
    root('staticfiles'),
)

ROOT_URLCONF = 'settings.urls'

TEMPLATE_DIRS = (
    root('templates'),
)


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',

    # external
    'south',

)

SITE_ID = 1

TEST_EXCLUDE = ('django',)
TEST_RUNNER = 'settings.test_suite.AdvancedTestSuiteRunner'




########NEW FILE########
__FILENAME__ = test_suite
import logging

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings


EXCLUDED_APPS = getattr(settings, 'TEST_EXCLUDE', [])

class AdvancedTestSuiteRunner(DjangoTestSuiteRunner):
    def __init__(self, *args, **kwargs):
        from django.conf import settings
        
        settings.TESTING = True
        
        super(AdvancedTestSuiteRunner, self).__init__(*args, **kwargs)

    
    def build_suite(self, *args, **kwargs):
        suite = super(AdvancedTestSuiteRunner, self).build_suite(*args, **kwargs)
        if not args[0] and not getattr(settings, 'RUN_ALL_TESTS', False):
            tests = []
            for case in suite:
                pkg = case.__class__.__module__.split('.')[0]
                if pkg not in EXCLUDED_APPS:
                    tests.append(case)
            suite._tests = tests 
        return suite
    

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^', include('test_app.urls', namespace="test_app")),                       
)

urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^static/media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
    )



########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _



GENDERS = {
            'male': _(u'Male'),
            'female': _(u'Female'),
            'unknown': _(u'None of your business!'),
          }
          
          
class ParticipantForm(forms.Form):
    """
    A simple form to get some simple data.
    """
    gender = forms.ChoiceField(label=_(u'gender'), choices=GENDERS.items())
    age = forms.IntegerField(label=_(u'age'), max_value=100, min_value=1, required=False)

########NEW FILE########
__FILENAME__ = metrics
from staste.metrica import Metrica
from staste.axis import Axis, StoredChoiceAxis

from .forms import GENDERS



gender_axis = Axis(choices=GENDERS.keys())

age_axis = StoredChoiceAxis()

gender_age_metrica = Metrica(name='visitors_gender_and_age',
                             axes=[('gender', gender_axis),
                                   ('age', age_axis),])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from staste.charts.views import PieChart, TimeserieChart, LatestCountAndAverageChart
from staste.middleware import response_time_metrica

from .views import IndexView
from .metrics import gender_age_metrica


urlpatterns = patterns('',
                       url(r'^$', IndexView.as_view(), name="index"),

                       url(r'^pie/$',
                           PieChart.as_view(metrica=gender_age_metrica,
                                            axis_keyword='gender'),
                           name='gender_pie'),

                       url(r'^timeline/$',
                           TimeserieChart.as_view(metrica=gender_age_metrica),
                           name='gender_timeline'),

                       url(r'^requests/pie/$',
                           PieChart.as_view(metrica=response_time_metrica,
                                            axis_keyword='view'),
                          name='requests_pie'),

                       url(r'^requests/$',
                           LatestCountAndAverageChart.as_view(metrica=response_time_metrica,
                                                              title='Requests count and average response time'),
                           name='requests_timeserie')
                      )

########NEW FILE########
__FILENAME__ = utils
import random
import datetime

from .metrics import gender_age_metrica, GENDERS

def lots_of_dummy_stats():
    for i in xrange(2000):
        minutes_ago = random.randint(1, 1600)

        dt = datetime.datetime.now() - datetime.timedelta(minutes=minutes_ago)

        gender_age_metrica.kick(date=dt,
                                gender=random.choice(GENDERS.keys()),
                                age=random.randint(1, 100))

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.views.generic import FormView

from staste import redis

from .forms import ParticipantForm, GENDERS
from .metrics import gender_age_metrica


class IndexView(FormView):
    form_class = ParticipantForm
    template_name = 'test_app/index.html'

    def get_context_data(self, *args, **kwargs):
        data = super(IndexView, self).get_context_data(*args, **kwargs)
        data['redis_memory'] = redis.info()['used_memory_human']
        return data
      
    def form_valid(self, form):
        gender_age_metrica.kick(
                            gender=form.cleaned_data['gender'],
                            age=form.cleaned_data['age']
                         )
        return HttpResponseRedirect(self.request.META.get('HTTP_REFERER', '/')) 

########NEW FILE########
