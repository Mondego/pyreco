__FILENAME__ = base
import copy
from django import http
from django.core.exceptions import ImproperlyConfigured
from django.template import RequestContext, loader
from django.utils.translation import ugettext_lazy as _

from utils import coerce_put_post

class View(object):
    """
    Intentionally simple parent class for all views. Only implements 
    dispatch-by-method and simple sanity checking.
    """
    
    method_names = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE']
    
    def __init__(self, *args, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            if key in self.method_names:
                raise TypeError(u"You tried to pass in the %s method name as a "
                                u"keyword argument to %s(). Don't do that." 
                                % (key, self.__class__.__name__))
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    self.__class__.__name__,
                    key,
                ))
    
    @classmethod
    def as_view(cls, *initargs, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        def view(request, *args, **kwargs):
            self = cls(*initargs, **initkwargs)
            return self.dispatch(request, *args, **kwargs)
        return view
    
    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method for that; if it doesn't exist,
        # raise a big error.
        if hasattr(self, request.method.upper()):
            self.request = request
            self.args = args
            self.kwargs = kwargs
            if request.method == "PUT":
                coerce_put_post(request)
            return getattr(self, request.method.upper())(request, *args, **kwargs)
        else:
            allowed_methods = [m for m in self.method_names if hasattr(self, m)]
            return http.HttpResponseNotAllowed(allowed_methods)
    

class TemplateView(View):
    """
    A view which can render itself with a template.
    """
    template_name = None
    
    def render_to_response(self, template_names=None, context=None):
        """
        Returns a response with a template rendered with the given context.
        """
        return self.get_response(self.render(template_names, context))
    
    def get_response(self, content, **httpresponse_kwargs):
        """
        Construct an `HttpResponse` object.
        """
        return http.HttpResponse(content, **httpresponse_kwargs)
    
    def render(self, template_names=None, context=None):
        """
        Render the template with a given context.
        """
        context_instance = self.get_context_instance(context)
        return self.get_template(template_names).render(context_instance)
    
    def get_context_instance(self, context=None):
        """
        Get the template context instance. Must return a Context (or subclass) 
        instance.
        """
        if context is None:
            context = {}
        return RequestContext(self.request, context)
    
    def get_template(self, names=None):
        """
        Get a ``Template`` object for the given request.
        """
        if names is None:
            names = self.get_template_names()
        if not names:
            raise ImproperlyConfigured(u"'%s' must provide template_name." 
                                       % self.__class__.__name__)
        if isinstance(names, basestring):
            names = [names]
        return self.load_template(names)
    
    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        if self.template_name is None:
            return []
        else:
            return [self.template_name]
    
    def load_template(self, names):
        """
        Load a list of templates using the default template loader.
        """
        return loader.select_template(names)
    

########NEW FILE########
__FILENAME__ = dates
import time
import datetime
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from class_based_views import ListView, DetailView

class DateView(ListView):
    """
    Abstract base class for date-based views.
    """
    
    allow_future = False
    date_field = None

    def GET(self, request, *args, **kwargs):
        date_list, items, extra_context = self.get_dated_items(*args, **kwargs)
        context = self.get_context(items, date_list)
        context.update(extra_context)
        return self.render_to_response(self.get_template_names(items), context)

    def get_queryset(self):
        """
        Get the queryset to look an objects up against. May not be called if
        `get_dated_items` is overridden.
        """
        if self.queryset is None:
            raise ImproperlyConfigured(u"%(cls)s is missing a queryset. Define "
                                       u"%(cls)s.queryset, or override "
                                       u"%(cls)s.get_dated_items()."
                                       % {'cls': self.__class__.__name__})
        return self.queryset._clone()

    def get_dated_queryset(self, allow_future=False, **lookup):
        """
        Get a queryset properly filtered according to `allow_future` and any
        extra lookup kwargs.
        """
        qs = self.get_queryset().filter(**lookup)
        date_field = self.get_date_field()
        allow_future = allow_future or self.get_allow_future()
        allow_empty = self.get_allow_empty()

        if not allow_future:
            qs = qs.filter(**{'%s__lte' % date_field: datetime.datetime.now()})

        if not allow_empty and not qs:
            raise Http404(u"No %s available"
                          % qs.model._meta.verbose_name_plural)
        return qs

    def get_date_list(self, queryset, date_type):
        """
        Get a date list by calling `queryset.dates()`, checking along the way
        for empty lists that aren't allowed.
        """
        date_field = self.get_date_field()
        allow_empty = self.get_allow_empty()

        date_list = queryset.dates(date_field, date_type)[::-1]
        if date_list is not None and not date_list and not allow_empty:
            raise Http404(u"No %s available"
                          % queryset.model._meta.verbose_name_plural)

        return date_list

    def get_date_field(self):
        """
        Get the name of the date field to be used to filter by.
        """
        if self.date_field is None:
            raise ImproperlyConfigured(u"%s.date_field is required." 
                                       % self.__class__.__name__)
        return self.date_field

    def get_allow_future(self):
        """
        Returns `True` if the view should be allowed to display objects from
        the future.
        """
        return self.allow_future

    def get_context(self, items, date_list, context=None):
        """
        Get the context. Must return a Context (or subclass) instance.
        """
        context = super(DateView, self).get_context(items)
        context['date_list'] = date_list
        return context

    def get_template_names(self, items):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        return super(DateView, self).get_template_names(
            items,
            suffix=self._template_name_suffix
        )

    def get_dated_items(self, *args, **kwargs):
        """
        Return (date_list, items, extra_context) for this request.
        """
        raise NotImplementedError()

class ArchiveView(DateView):
    """
    Top-level archive of date-based items.
    """
    
    num_latest=15
    _template_name_suffix = 'archive'
    
    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        qs = self.get_dated_queryset()
        date_list = self.get_date_list(qs, 'year')
        num_latest = self.get_num_latest()

        if date_list and num_latest:
            latest = qs.order_by('-'+self.get_date_field())[:num_latest]
        else:
            latest = None

        return (date_list, latest, {})

    def get_num_latest(self):
        """
        Get the number of latest items to show on the archive page.
        """
        return self.num_latest

    def get_template_object_name(self, items):
        """
        Get the name of the item to be used in the context.
        """
        return self.template_object_name or 'latest'

class YearView(DateView):
    """
    List of objects published in a given year.
    """
    
    make_object_list = False
    allow_empty = False
    _template_name_suffix = 'archive_year'

    def get_dated_items(self, year):
        """
        Return (date_list, items, extra_context) for this request.
        """
        # Yes, no error checking: the URLpattern ought to validate this; it's
        # an error if it doesn't.
        year = int(year)
        date_field = self.get_date_field()
        qs = self.get_dated_queryset(**{date_field+'__year': year})
        date_list = self.get_date_list(qs, 'month')

        if self.get_make_object_list():
            object_list = qs.order_by('-'+date_field)
        else:
            # We need this to be a queryset since parent classes introspect it
            # to find information about the model.
            object_list = qs.none()

        return (date_list, object_list, {'year': year})

    def get_make_object_list(self):
        """
        Return `True` if this view should contain the full list of objects in
        the given year.
        """
        return self.make_object_list

class MonthView(DateView):
    """
    List of objects published in a given year.
    """
    
    month_format = '%b'
    allow_empty = False
    _template_name_suffix = 'archive_month'
    
    def get_dated_items(self, year, month):
        """
        Return (date_list, items, extra_context) for this request.
        """
        date_field = self.get_date_field()
        date = _date_from_string(year, '%Y', month, self.get_month_format())

        # Construct a date-range lookup.
        first_day, last_day = _month_bounds(date)
        lookup_kwargs = {
            '%s__gte' % date_field: first_day,
            '%s__lt' % date_field: last_day,
        }

        allow_future = self.get_allow_future()
        qs = self.get_dated_queryset(allow_future=allow_future, **lookup_kwargs)
        date_list = self.get_date_list(qs, 'day')

        return (date_list, qs, {
            'month': date,
            'next_month': self.get_next_month(date),
            'previous_month': self.get_previous_month(date),
        })

    def get_next_month(self, date):
        """
        Get the next valid month.
        """
        first_day, last_day = _month_bounds(date)
        next = (last_day + datetime.timedelta(days=1)).replace(day=1)
        return _get_next_prev_month(self, next, is_previous=False, use_first_day=True)

    def get_previous_month(self, date):
        """
        Get the previous valid month.
        """
        first_day, last_day = _month_bounds(date)
        prev = (first_day - datetime.timedelta(days=1)).replace(day=1)
        return _get_next_prev_month(self, prev, is_previous=True, use_first_day=True)

    def get_month_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.month_format

class WeekView(DateView):
    """
    List of objects published in a given week.
    """
    
    allow_empty = False
    _template_name_suffix = 'archive_year'
    
    def get_dated_items(self, year, week):
        """
        Return (date_list, items, extra_context) for this request.
        """
        date_field = self.get_date_field()
        date = _date_from_string(year, '%Y', '0', '%w', week, '%U')

        # Construct a date-range lookup.
        first_day = date
        last_day = date + datetime.timedelta(days=7)
        lookup_kwargs = {
            '%s__gte' % date_field: first_day,
            '%s__lt' % date_field: last_day,
        }

        allow_future = self.get_allow_future()
        qs = self.get_dated_queryset(allow_future=allow_future, **lookup_kwargs)

        return (None, qs, {'week': date})

class DayView(DateView):
    """
    List of objects published on a given day.
    """
    
    month_format = '%b'
    day_format = '%d'
    allow_empty = False
    _template_name_suffix = "archive_day"
    
    def get_dated_items(self, year, month, day, date=None):
        """
        Return (date_list, items, extra_context) for this request.
        """
        date = _date_from_string(year, '%Y',
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        return self._get_dated_items(date)

    def _get_dated_items(self, date):
        """
        Do the actual heavy lifting of getting the dated items; this accepts a
        date object so that TodayView can be trivial.
        """
        date_field = self.get_date_field()
        allow_future = self.get_allow_future()

        field = self.get_queryset().model._meta.get_field(date_field)
        lookup_kwargs = _date_lookup_for_field(field, date)

        qs = self.get_dated_queryset(allow_future=allow_future, **lookup_kwargs)

        return (None, qs, {
            'day': date,
            'previous_day': self.get_previous_day(date),
            'next_day': self.get_next_day(date)
        })

    def get_next_day(self, date):
        """
        Get the next valid day.
        """
        next = date + datetime.timedelta(days=1)
        return _get_next_prev_month(self, next, is_previous=False, use_first_day=False)

    def get_previous_day(self, date):
        """
        Get the previous valid day.
        """
        prev = date - datetime.timedelta(days=1)
        return _get_next_prev_month(self, prev, is_previous=True, use_first_day=False)

    def get_month_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.month_format

    def get_day_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.day_format

class TodayView(DayView):
    """
    List of objects published today.
    """

    def get_dated_items(self):
        """
        Return (date_list, items, extra_context) for this request.
        """
        return self._get_dated_items(datetime.date.today())
    

class DateDetailView(DetailView):
    """
    Detail view of a single object on a single date; this differs from the
    standard DetailView by accepting a year/month/day in the URL.
    """
    
    date_field = None
    month_format = '%b'
    day_format = '%d'
    allow_future = False
    
    def get_object(self, year, month, day, pk=None, slug=None):
        """
        Get the object this request displays.
        """
        date = _date_from_string(year, '%Y',
                                 month, self.get_month_format(),
                                 day, self.get_day_format())

        qs = self.get_queryset()

        if not self.get_allow_future() and date > datetime.date.today():
            raise Http404(u"Future %s not available because %s.allow_future is "
                          u"False."
                          % (qs.model._meta.verbose_name_plural, self.__class__.__name__))

        # Filter down a queryset from self.queryset using the date from the
        # URL. This'll get passed as the queryset to DetailView.get_object,
        # which'll handle the 404
        date_field = self.get_date_field()
        field = qs.model._meta.get_field(date_field)
        lookup = _date_lookup_for_field(field, date)
        qs = qs.filter(**lookup)

        return super(DateDetailView, self).get_object(pk=pk, slug=slug, queryset=qs)

    def get_date_field(self):
        """
        Get the name of the date field to be used to filter by.
        """
        if self.date_field is None:
            raise ImproperlyConfigured(u"%s.date_field is required." 
                                       % self.__class__.__name__)
        return self.date_field

    def get_month_format(self):
        """
        Get a month format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.month_format

    def get_day_format(self):
        """
        Get a day format string in strptime syntax to be used to parse the
        month from url variables.
        """
        return self.day_format

    def get_allow_future(self):
        """
        Returns `True` if the view should be allowed to display objects from
        the future.
        """
        return self.allow_future

def _date_from_string(year, year_format, month, month_format, day='', day_format='', delim='__'):
    """
    Helper: get a datetime.date object given a format string and a year,
    month, and possibly day; raise a 404 for an invalid date.
    """
    format = delim.join((year_format, month_format, day_format))
    datestr = delim.join((year, month, day))
    try:
        return datetime.date(*time.strptime(datestr, format)[:3])
    except ValueError:
        raise Http404(u"Invalid date string '%s' given format '%s'" 
                      % (datestr, format))

def _month_bounds(date):
    """
    Helper: return the first and last days of the month for the given date.
    """
    first_day = date.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1)

    return first_day, last_day

def _get_next_prev_month(generic_view, naive_result, is_previous, use_first_day):
    """
    Helper: Get the next or the previous valid date. The idea is to allow
    links on month/day views to never be 404s by never providing a date
    that'll be invalid for the given view.

    This is a bit complicated since it handles both next and previous months
    and days (for MonthView and DayView); hence the coupling to generic_view.

    However in essance the logic comes down to:

        * If allow_empty and allow_future are both true, this is easy: just
          return the naive result (just the next/previous day or month,
          reguardless of object existence.)

        * If allow_empty is true, allow_future is false, and the naive month
          isn't in the future, then return it; otherwise return None.

        * If allow_empty is false and allow_future is true, return the next
          date *that contains a valid object*, even if it's in the future. If
          there are no next objects, return None.

        * If allow_empty is false and allow_future is false, return the next
          date that contains a valid object. If that date is in the future, or
          if there are no next objects, return None.

    """
    date_field = generic_view.get_date_field()
    allow_empty = generic_view.get_allow_empty()
    allow_future = generic_view.get_allow_future()

    # If allow_empty is True the naive value will be valid
    if allow_empty:
        result = naive_result

    # Otherwise, we'll need to go to the database to look for an object
    # whose date_field is at least (greater than/less than) the given
    # naive result
    else:
        # Construct a lookup and an ordering depending on weather we're doing
        # a previous date or a next date lookup.
        if is_previous:
            lookup = {'%s__lte' % date_field: naive_result}
            ordering = '-%s' % date_field
        else:
            lookup = {'%s__gte' % date_field: naive_result}
            ordering = date_field

        qs = generic_view.get_queryset().filter(**lookup).order_by(ordering)

        # Snag the first object from the queryset; if it doesn't exist that
        # means there's no next/previous link available.
        try:
            result = getattr(qs[0], date_field)
        except IndexError:
            result = None

    # Convert datetimes to a dates
    if hasattr(result, 'date'):
        result = result.date()

    # For month views, we always want to have a date that's the first of the
    # month for consistancy's sake.
    if result and use_first_day:
        result = result.replace(day=1)

    # Check against future dates.
    if result and (allow_future or result < datetime.date.today()):
        return result
    else:
        return None

def _date_lookup_for_field(field, date):
    """
    Get the lookup kwargs for looking up a date against a given Field. If the
    date field is a DateTimeField, we can't just do filter(df=date) because
    that doesn't take the time into account. So we need to make a range lookup
    in those cases.
    """
    if isinstance(field, models.DateTimeField):
        date_range = (
            datetime.datetime.combine(date, datetime.time.min),
            datetime.datetime.combine(date, datetime.time.max)
        )
        return {'%s__range' % field.name: date_range}
    else:
        return {field.name: date}


########NEW FILE########
__FILENAME__ = detail
from class_based_views import TemplateView
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import Http404
import re

class SingleObjectMixin(object):
    """
    Provides a get_object() method.
    """
    
    queryset = None
    slug_field = 'slug'
    
    def get_object(self, pk=None, slug=None, queryset=None):
        """
        Returns the object the view is displaying.
        
        By default this requires `self.queryset` and a `pk` or `slug` argument 
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object id or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(u"No %s found matching the query"
                          % (queryset.model._meta.verbose_name))
        return obj
    
    def get_queryset(self):
        """
        Get the queryset to look an object up against. May not be called if
        `get_object` is overridden.
        """
        if self.queryset is None:
            raise ImproperlyConfigured(u"%(cls)s is missing a queryset. Define "
                                       u"%(cls)s.queryset, or override "\
                                       u"%(cls)s.get_object()." % {
                                            'cls': self.__class__.__name__
                                        })
        return self.queryset._clone()

    def get_slug_field(self):
        """
        Get the name of a slug field to be used to look up by slug.
        """
        return self.slug_field
    

class DetailView(SingleObjectMixin, TemplateView):
    """
    Render a "detail" view of an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """
    template_object_name = 'object'
    template_name_field = None
    
    def GET(self, request, *args, **kwargs):
        obj = self.get_object(*args, **kwargs)
        context = self.get_context(obj)
        return self.render_to_response(self.get_template_names(obj), context)
    
    def get_context(self, obj):
        return {
            'object': obj,
            self.get_template_object_name(obj): obj
        }
    
    def get_template_names(self, obj):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        names = super(DetailView, self).get_template_names()

        # If self.template_name_field is set, grab the value of the field
        # of that name from the object; this is the most specific template
        # name, if given.
        if self.template_name_field:
            name = getattr(obj, self.template_name_field, None)
            if name:
                names.insert(0, name)

        # The least-specific option is the default <app>/<model>_detail.html;
        # only use this if the object in question is a model.
        if hasattr(obj, '_meta'):
            names.append("%s/%s_detail.html" % (
                obj._meta.app_label,
                obj._meta.object_name.lower()
            ))

        return names

    def get_template_object_name(self, obj):
        """
        Get the name to use for the object.
        """
        if hasattr(obj, '_meta'):
            return re.sub('[^a-zA-Z0-9]+', '_', 
                    obj._meta.verbose_name.lower())
        else:
            return self.template_object_name
    

########NEW FILE########
__FILENAME__ = edit
from django.http import HttpResponseRedirect
from class_based_views import ListView
from class_based_views.base import TemplateView
from class_based_views.detail import SingleObjectMixin, DetailView

class FormMixin(object):
    """
    A mixin that provides a get_form() method.
    """
    
    initial = {}
    form = None
    
    def get_form(self):
        """
        Returns the form to be used in this view.
        """
        if self.request.method in ('POST', 'PUT'):
            return self.form(
                self.request.POST,
                self.request.FILES,
                initial=self.initial,
            )
        else:
            return self.form(
                initial=self.initial,
            )
    

class ModelFormMixin(SingleObjectMixin):
    """
    A derivative of SingleObjectMixin that passes get_object() as an instance 
    to a form.
    """
    
    initial = {}
    form = None
    
    def get_form(self):
        """
        Returns a form instantiated with the model instance from get_object().
        """
        if self.request.method in ('POST', 'PUT'):
            return self.form(
                self.request.POST,
                self.request.FILES,
                initial=self.initial,
                instance=self.get_object(*self.args, **self.kwargs),
            )
        else:
            return self.form(
                initial=self.initial,
                instance=self.get_object(*self.args, **self.kwargs),
            )
    

class ProcessFormView(TemplateView, FormMixin):
    """
    A view that processes a form on POST.
    """
    def POST(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    PUT = POST
    
    def form_valid(self, form):
        """
        Called when the submitted form is verified as valid.
        """
        raise NotImplementedError("You must override form_valid.")

    def form_invalid(self, form):
        """
        Called when the submitted form comes back with errors.
        """
        raise NotImplementedError("You must override form_invalid.")
    

class ProcessModelFormView(ModelFormMixin, ProcessFormView):
    """
    A view that saves a ModelForm on POST.
    """
    

class DisplayFormView(TemplateView, FormMixin):
    """
    Displays a form for the user to edit and submit on GET.
    """
    def GET(self, request, *args, **kwargs):
        form = self.get_form()
        return self.render_to_response(context=self.get_context(form))
    
    def get_context(self, form):
        return {
            'form': form,
        }
    

class DisplayModelFormView(ModelFormMixin, DisplayFormView):
    """
    Displays a ModelForm for the user to edit on GET.
    """
    

class ModelFormMixin(object):
    def form_valid(self, form):
        obj = form.save()
        return HttpResponseRedirect(self.redirect_to(obj))
    
    def redirect_to(self, obj):
        raise NotImplementedError("You must override redirect_to.")
    
    def form_invalid(self, form):
        return self.GET(self.request, form)
    

class CreateView(ModelFormMixin, DisplayFormView, ProcessFormView):
    """
    View for creating an object.
    """
    

class UpdateView(ModelFormMixin, DisplayModelFormView, ProcessModelFormView):
    """
    View for updating an object.
    """
    

class DeleteView(DetailView):
    """
    View for deleting an object retrieved with `self.get_object()`.
    """    
    def DELETE(self, request, *args, **kwargs):
        obj = self.get_object(*args, **kwargs)
        obj.delete()
        return HttpResponseRedirect(self.redirect_to(obj))

    # Add support for browsers which only accept GET and POST for now.
    POST = DELETE

    def redirect_to(self, obj):
        raise NotImplementedError("You must override redirect_to.")
    

########NEW FILE########
__FILENAME__ = list
from class_based_views.base import TemplateView
from django.core.paginator import Paginator, InvalidPage
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import smart_str

class ListView(TemplateView):
    """
    Render some list of objects, set by `self.queryset`. This can be any 
    iterable of items, not just a queryset.
    """
    allow_empty = True
    template_object_name = None
    queryset = None
    
    def GET(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(queryset) == 0:
            raise Http404(u"Empty list and '%s.allow_empty' is False."
                          % self.__class__.__name__)
        context = self.get_context(queryset)
        return self.render_to_response(self.get_template_names(queryset), context)
    
    def get_context(self, queryset):
        """
        Get the context for this view.
        """
        context = {
            'object_list': queryset,
        }
        template_object_name = self.get_template_object_name(queryset)
        if template_object_name is not None:
            context[template_object_name] = queryset
        return context
    
    def get_queryset(self):
        """
        Get the list of items for this view. This must be an interable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        if hasattr(self, 'queryset') and self.queryset is not None:
            queryset = self.queryset
        else:
            raise ImproperlyConfigured(u"'%s' must define 'queryset'"
                                       % self.__class__.__name__)
        if hasattr(queryset, '_clone'):
            queryset = queryset._clone()
        return queryset
    
    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty
    
    def get_template_names(self, queryset, suffix='list'):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """ 
        names = super(ListView, self).get_template_names()
        
        # If the list is a queryset, we'll invent a template name based on the
        # app and model name. This name gets put at the end of the template 
        # name list so that user-supplied names override the automatically-
        # generated ones.
        if hasattr(queryset, 'model'):
            opts = queryset.model._meta
            names.append("%s/%s_%s.html" % (opts.app_label, opts.object_name.lower(), suffix))
        
        return names
    
    def get_template_object_name(self, queryset):
        """
        Get the name of the item to be used in the context.
        """
        if self.template_object_name:
            return '%s_list' % self.template_object_name
        elif hasattr(queryset, 'model'):
            return smart_str(queryset.model._meta.verbose_name_plural)
        else:
            return None
    

class PaginatedListView(ListView):
    paginate_by = None
    
    def get_context(self, queryset):
        page = self.kwargs.get('page', None)
        paginator, page, queryset = self.paginate_queryset(queryset, page)
        context = super(PaginatedListView, self).get_context(queryset)
        context.update({
            'paginator': paginator,
            'page_obj': page,
            'is_paginated': paginator is not None,
        })
        return context
    
    def paginate_queryset(self, queryset, page):
        """
        Paginate the queryset, if needed.
        """
        paginate_by = self.get_paginate_by(queryset)
        paginator = Paginator(queryset, paginate_by, allow_empty_first_page=self.get_allow_empty())
        page = page or self.request.GET.get('page', 1)
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404("Page is not 'last', nor can it be converted to an int.")
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list)
        except InvalidPage:
            raise Http404('Invalid page (%s)' % page_number)
    
    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return self.paginate_by
    

########NEW FILE########
__FILENAME__ = forms
from django import forms
from models import Author

class AuthorForm(forms.ModelForm):
    name = forms.CharField()
    slug = forms.SlugField()
    
    class Meta:
        model = Author

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Author(models.Model):
   name = models.CharField(max_length=100)
   slug = models.SlugField()

   class Meta:
       ordering = ['name']

   def __unicode__(self):
       return self.name

class Book(models.Model):
   name = models.CharField(max_length=300)
   slug = models.SlugField()
   pages = models.IntegerField()
   authors = models.ManyToManyField(Author)
   pubdate = models.DateField()
   
   class Meta:
       ordering = ['-pubdate']
   
   def __unicode__(self):
       return self.name


########NEW FILE########
__FILENAME__ = settings
DATABASE_ENGINE = 'sqlite3'
ROOT_URLCONF = 'class_based_views.tests.urls'
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'class_based_views',
    'class_based_views.tests',
]
SITE_ID = 1
########NEW FILE########
__FILENAME__ = base
from class_based_views.base import View, TemplateView
from class_based_views.tests.utils import RequestFactory
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import TestCase
from django.utils import simplejson
import unittest

class SimpleView(View):
    def GET(self, request):
        return HttpResponse('This is a simple view')
    

class SimplePostView(SimpleView):
    POST = SimpleView.GET
    

class AboutTemplateView(TemplateView):
    def GET(self, request):
        return self.render_to_response('tests/about.html', {})

class AboutTemplateAttributeView(TemplateView):
    template_name = 'tests/about.html'
    
    def GET(self, request):
        return self.render_to_response(context={})
    

class InstanceView(View):
    def GET(self, request):
        return self
    

class ViewTest(unittest.TestCase):
    rf = RequestFactory()
    
    def _assert_simple(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'This is a simple view')
    
    def test_get_only(self):
        """
        Test a view which only allows GET doesn't allow other methods.
        """
        self._assert_simple(SimpleView.as_view()(self.rf.get('/')))
        self.assertEqual(SimpleView.as_view()(self.rf.post('/')).status_code, 405)
        self.assertEqual(SimpleView.as_view()(
            self.rf.get('/', REQUEST_METHOD='FAKE')
        ).status_code, 405)
    
    def test_get_and_post(self):
        """
        Test a view which only allows both GET and POST.
        """
        self._assert_simple(SimplePostView.as_view()(self.rf.get('/')))
        self._assert_simple(SimplePostView.as_view()(self.rf.post('/')))
        self.assertEqual(SimplePostView.as_view()(
            self.rf.get('/', REQUEST_METHOD='FAKE')
        ).status_code, 405)
    
    def test_calling_more_than_once(self):
        """
        Test a view can only be called once.
        """
        request = self.rf.get('/')
        view = InstanceView.as_view()
        self.assertNotEqual(view(request), view(request))
    

class TemplateViewTest(unittest.TestCase):
    rf = RequestFactory()
    
    def _assert_about(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '<h1>About</h1>')
    
    def test_get(self):
        """
        Test a view that simply renders a template on GET
        """
        self._assert_about(AboutTemplateView.as_view()(self.rf.get('/about/')))
    
    def test_get_template_attribute(self):
        """
        Test a view that renders a template on GET with the template name as 
        an attribute on the class.
        """
        self._assert_about(AboutTemplateAttributeView.as_view()(self.rf.get('/about/')))
    

########NEW FILE########
__FILENAME__ = dates
import datetime
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from class_based_views.tests.models import Book

class ArchiveViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_archive_view(self):
        res = self.client.get('/dates/books/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['date_list'], Book.objects.dates('pubdate', 'year')[::-1])
        self.assertEqual(list(res.context['latest']), list(Book.objects.all()))
        self.assertTemplateUsed(res, 'tests/book_archive.html')

    def test_archive_view_invalid(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/dates/books/invalid/')

class YearViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_year_view(self):
        res = self.client.get('/dates/books/2008/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(2008, 10, 1)])
        self.assertEqual(res.context['year'], 2008)
        self.assertTemplateUsed(res, 'tests/book_archive_year.html')

    def test_year_view_make_object_list(self):
        res = self.client.get('/dates/books/2006/make_object_list/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(2006, 5, 1)])
        self.assertEqual(list(res.context['books']), list(Book.objects.filter(pubdate__year=2006)))
        self.assertEqual(list(res.context['object_list']), list(Book.objects.filter(pubdate__year=2006)))
        self.assertTemplateUsed(res, 'tests/book_archive_year.html')

    def test_year_view_empty(self):
        res = self.client.get('/dates/books/1999/')
        self.assertEqual(res.status_code, 404)
        res = self.client.get('/dates/books/1999/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [])
        self.assertEqual(list(res.context['books']), [])

    def test_year_view_allow_future(self):
        # Create a new book in the future
        year = datetime.date.today().year + 1
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=datetime.date(year, 1, 1))
        res = self.client.get('/dates/books/%s/' % year)
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/%s/allow_empty/' % year)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['books']), [])

        res = self.client.get('/dates/books/%s/allow_future/' % year)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(year, 1, 1)])

    def test_year_view_invalid_pattern(self):
        self.assertRaises(TypeError, self.client.get, '/dates/books/no_year/')

class MonthViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_month_view(self):
        res = self.client.get('/dates/books/2008/oct/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/book_archive_month.html')
        self.assertEqual(list(res.context['date_list']), [datetime.datetime(2008, 10, 1)])
        self.assertEqual(list(res.context['books']),
                         list(Book.objects.filter(pubdate=datetime.date(2008, 10, 1))))
        self.assertEqual(res.context['month'], datetime.date(2008, 10, 1))

        # Since allow_empty=False, next/prev months must be valid (#7164)
        self.assertEqual(res.context['next_month'], None)
        self.assertEqual(res.context['previous_month'], datetime.date(2006, 5, 1))

    def test_month_view_allow_empty(self):
        # allow_empty = False, empty month
        res = self.client.get('/dates/books/2000/jan/')
        self.assertEqual(res.status_code, 404)

        # allow_empty = True, empty month
        res = self.client.get('/dates/books/2000/jan/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['date_list']), [])
        self.assertEqual(list(res.context['books']), [])
        self.assertEqual(res.context['month'], datetime.date(2000, 1, 1))

        # Since it's allow empty, next/prev are allowed to be empty months (#7164)
        self.assertEqual(res.context['next_month'], datetime.date(2000, 2, 1))
        self.assertEqual(res.context['previous_month'], datetime.date(1999, 12, 1))

        # allow_empty but not allow_future: next_month should be empty (#7164)
        url = datetime.date.today().strftime('/dates/books/%Y/%b/allow_empty/').lower()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_month'], None)

    def test_month_view_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60)).replace(day=1)
        urlbit = future.strftime('%Y/%b').lower()
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        # allow_future = False, future month
        res = self.client.get('/dates/books/%s/' % urlbit)
        self.assertEqual(res.status_code, 404)

        # allow_future = True, valid future month
        res = self.client.get('/dates/books/%s/allow_future/' % urlbit)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['date_list'][0].date(), b.pubdate)
        self.assertEqual(list(res.context['books']), [b])
        self.assertEqual(res.context['month'], future)

        # Since it's allow_future but not allow_empty, next/prev are not
        # allowed to be empty months (#7164)
        self.assertEqual(res.context['next_month'], None)
        self.assertEqual(res.context['previous_month'], datetime.date(2008, 10, 1))

        # allow_future, but not allow_empty, with a current month. So next
        # should be in the future (yup, #7164, again)
        res = self.client.get('/dates/books/2008/oct/allow_future/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_month'], future)
        self.assertEqual(res.context['previous_month'], datetime.date(2006, 5, 1))

    def test_custom_month_format(self):
        res = self.client.get('/dates/books/2008/10/')
        self.assertEqual(res.status_code, 200)

    def test_month_view_invalid_pattern(self):
        self.assertRaises(TypeError, self.client.get, '/dates/books/2007/no_month/')

class WeekViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_week_view(self):
        res = self.client.get('/dates/books/2008/week/39/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/book_archive_year.html')
        self.assertEqual(res.context['books'][0], Book.objects.get(pubdate=datetime.date(2008, 10, 1)))
        self.assertEqual(res.context['week'], datetime.date(2008, 9, 28))

    def test_week_view_allow_empty(self):
        res = self.client.get('/dates/books/2008/week/12/')
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/2008/week/12/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['books']), [])

    def test_week_view_allow_future(self):
        future = datetime.date(datetime.date.today().year + 1, 1, 1)
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        res = self.client.get('/dates/books/%s/week/0/' % future.year)
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/%s/week/0/allow_future/' % future.year)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['books']), [b])

    def test_week_view_invalid_pattern(self):
        self.assertRaises(TypeError, self.client.get, '/dates/books/2007/week/no_week/')

class DayViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_day_view(self):
        res = self.client.get('/dates/books/2008/oct/01/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/book_archive_day.html')
        self.assertEqual(list(res.context['books']),
                         list(Book.objects.filter(pubdate=datetime.date(2008, 10, 1))))
        self.assertEqual(res.context['day'], datetime.date(2008, 10, 1))

        # Since allow_empty=False, next/prev days must be valid.
        self.assertEqual(res.context['next_day'], None)
        self.assertEqual(res.context['previous_day'], datetime.date(2006, 5, 1))

    def test_day_view_allow_empty(self):
        # allow_empty = False, empty month
        res = self.client.get('/dates/books/2000/jan/1/')
        self.assertEqual(res.status_code, 404)

        # allow_empty = True, empty month
        res = self.client.get('/dates/books/2000/jan/1/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['books']), [])
        self.assertEqual(res.context['day'], datetime.date(2000, 1, 1))

        # Since it's allow empty, next/prev are allowed to be empty months (#7164)
        self.assertEqual(res.context['next_day'], datetime.date(2000, 1, 2))
        self.assertEqual(res.context['previous_day'], datetime.date(1999, 12, 31))

        # allow_empty but not allow_future: next_month should be empty (#7164)
        url = datetime.date.today().strftime('/dates/books/%Y/%b/%d/allow_empty/').lower()
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_day'], None)

    def test_day_view_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60))
        urlbit = future.strftime('%Y/%b/%d').lower()
        b = Book.objects.create(name="The New New Testement", pages=600, pubdate=future)

        # allow_future = False, future month
        res = self.client.get('/dates/books/%s/' % urlbit)
        self.assertEqual(res.status_code, 404)

        # allow_future = True, valid future month
        res = self.client.get('/dates/books/%s/allow_future/' % urlbit)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['books']), [b])
        self.assertEqual(res.context['day'], future)

        # allow_future but not allow_empty, next/prev amust be valid
        self.assertEqual(res.context['next_day'], None)
        self.assertEqual(res.context['previous_day'], datetime.date(2008, 10, 1))

        # allow_future, but not allow_empty, with a current month.
        res = self.client.get('/dates/books/2008/oct/01/allow_future/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['next_day'], future)
        self.assertEqual(res.context['previous_day'], datetime.date(2006, 5, 1))

    def test_next_prev_context(self):
        res = self.client.get('/dates/books/2008/oct/01/')
        self.assertEqual(res.content, "Archive for 2008-10-01. Previous day is 2006-05-01")

    def test_custom_month_format(self):
        res = self.client.get('/dates/books/2008/10/01/')
        self.assertEqual(res.status_code, 200)

    def test_day_view_invalid_pattern(self):
        self.assertRaises(TypeError, self.client.get, '/dates/books/2007/oct/no_day/')

    def test_today_view(self):
        res = self.client.get('/dates/books/today/')
        self.assertEqual(res.status_code, 404)
        res = self.client.get('/dates/books/today/allow_empty/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['day'], datetime.date.today())

class DateDetailViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_date_detail_by_pk(self):
        res = self.client.get('/dates/books/2008/oct/01/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Book.objects.get(pk=1))
        self.assertEqual(res.context['book'], Book.objects.get(pk=1))
        self.assertTemplateUsed(res, 'tests/book_detail.html')

    def test_date_detail_by_slug(self):
        res = self.client.get('/dates/books/2006/may/01/byslug/dreaming-in-code/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['book'], Book.objects.get(slug='dreaming-in-code'))

    def test_date_detail_custom_month_format(self):
        res = self.client.get('/dates/books/2008/10/01/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['book'], Book.objects.get(pk=1))

    def test_date_detail_allow_future(self):
        future = (datetime.date.today() + datetime.timedelta(days=60))
        urlbit = future.strftime('%Y/%b/%d').lower()
        b = Book.objects.create(name="The New New Testement", slug="new-new", pages=600, pubdate=future)

        res = self.client.get('/dates/books/%s/new-new/' % urlbit)
        self.assertEqual(res.status_code, 404)

        res = self.client.get('/dates/books/%s/%s/allow_future/' % (urlbit, b.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['book'], b)
        self.assertTemplateUsed(res, 'tests/book_detail.html')

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, "/dates/books/2008/oct/01/nopk/")
    

########NEW FILE########
__FILENAME__ = detail
from class_based_views.tests.models import Author
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

class DetailViewTest(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_simple_object(self):
        res = self.client.get('/detail/obj/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], {'foo': 'bar'})
        self.assertTemplateUsed(res, 'tests/detail.html')

    def test_detail_by_pk(self):
        res = self.client.get('/detail/author/1/')
        self.assertEqual(res.status_code, 200)
        #self.assertEqual(res.context['object'], Author.objects.get(pk=1))
        self.assertEqual(res.context['author'], Author.objects.get(pk=1))
        self.assertTemplateUsed(res, 'tests/author_detail.html')

    def test_detail_by_slug(self):
        res = self.client.get('/detail/author/byslug/scott-rosenberg/')
        self.assertEqual(res.status_code, 200)
        #self.assertEqual(res.context['object'], Author.objects.get(slug='scott-rosenberg'))
        self.assertEqual(res.context['author'], Author.objects.get(slug='scott-rosenberg'))
        self.assertTemplateUsed(res, 'tests/author_detail.html')

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, '/detail/author/invalid/url/')

    def test_invalid_queryset(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/detail/author/invalid/qs/')

########NEW FILE########
__FILENAME__ = edit
from class_based_views.tests.models import Author
from django.test import TestCase

class EditViewTests(TestCase):
    urls = 'class_based_views.tests.urls'

    def test_create(self):
        res = self.client.get('/edit/authors/create/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')

        res = self.client.post('/edit/authors/create/',
                        {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(str(Author.objects.all()), "[<Author: Randall Munroe>]")
    
    def test_create_invalid(self):
        res = self.client.post('/edit/authors/create/',
                        {'name': 'A' * 101, 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')
        self.assertEqual(len(res.context['form'].errors), 1)
        self.assertEqual(Author.objects.count(), 0)
        
    
    def test_restricted_create_restricted(self):
        res = self.client.get('/edit/authors/create/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')

        res = self.client.post('/edit/authors/create/restricted/',
                        {'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/accounts/login/?next=/edit/authors/create/restricted/')

    def test_update(self):
        Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/1/update/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/detail.html')

        # Modification with both POST and PUT (browser compatible)
        res = self.client.post('/edit/author/1/update/',
                        {'name': 'Randall Munroe (xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(str(Author.objects.all()), "[<Author: Randall Munroe (xkcd)>]")
    
        res = self.client.put('/edit/author/1/update/',
                        {'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(str(Author.objects.all()), "[<Author: Randall Munroe (author of xkcd)>]")
    
    def test_update_invalid(self):
        Author.objects.create(
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/1/update/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/detail.html')

        # Modification with both POST and PUT (browser compatible)
        res = self.client.post('/edit/author/1/update/',
                        {'name': 'A' * 101, 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/detail.html')
        self.assertEqual(len(res.context['form'].errors), 1)
        self.assertEqual(str(Author.objects.all()), "[<Author: Randall Munroe>]")
    
    def test_delete(self):
        Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.get('/edit/author/1/delete/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/detail.html')

        # Deletion with both POST and DELETE (browser compatible)
        res = self.client.post('/edit/author/1/delete/')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(str(Author.objects.all()), '[]')
    
        Author.objects.create(**{'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.delete('/edit/author/1/delete/')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(str(Author.objects.all()), '[]')

########NEW FILE########
__FILENAME__ = list
from class_based_views.tests.models import Author
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

class ListViewTests(TestCase):
    fixtures = ['generic-views-test-data.json']
    urls = 'class_based_views.tests.urls'

    def test_items(self):
        res = self.client.get('/list/dict/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')
        self.assertEqual(res.context['object_list'][0]['first'], 'John')

    def test_queryset(self):
        res = self.client.get('/list/authors/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertEqual(list(res.context['authors']), list(Author.objects.all()))

    def test_paginated_queryset(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')
        self.assertEqual(len(res.context['authors']), 30)
        self.assertNotEqual(res.context['paginator'], None)
        self.assertNotEqual(res.context['page_obj'], None)
        self.assertEqual(res.context['is_paginated'], True)
        self.assertEqual(res.context['page_obj'].number, 1)
        self.assertEqual(res.context['paginator'].num_pages, 4)
        self.assertEqual(res.context['authors'][0].name, 'Author 00')
        self.assertEqual(list(res.context['authors'])[-1].name, 'Author 29')

    def test_paginated_get_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': '2'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')
        self.assertEqual(len(res.context['authors']), 30)
        self.assertEqual(res.context['authors'][0].name, 'Author 30')
        self.assertEqual(res.context['page_obj'].number, 2)

    def test_paginated_get_last_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': 'last'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['authors']), 10)
        self.assertEqual(res.context['authors'][0].name, 'Author 90')
        self.assertEqual(res.context['page_obj'].number, 4)

    def test_paginated_get_page_by_urlvar(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/3/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'tests/list.html')
        self.assertEqual(len(res.context['authors']), 30)
        self.assertEqual(res.context['authors'][0].name, 'Author 60')
        self.assertEqual(res.context['page_obj'].number, 3)

    def test_paginated_page_out_of_range(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/42/')
        self.assertEqual(res.status_code, 404)

    def test_paginated_invalid_page(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/?page=frog')
        self.assertEqual(res.status_code, 404)

    def test_allow_empty_false(self):
        res = self.client.get('/list/authors/notempty/')
        self.assertEqual(res.status_code, 200)
        Author.objects.all().delete()
        res = self.client.get('/list/authors/notempty/')
        self.assertEqual(res.status_code, 404)

    def test_template_object_name(self):
        res = self.client.get('/list/authors/template_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertEqual(list(res.context['author_list']), list(Author.objects.all()))
        self.assert_('authors' not in res.context)

    def test_missing_items(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/list/authors/invalid/')

    def _make_authors(self, n):
        Author.objects.all().delete()
        for i in range(n):
            Author.objects.create(name='Author %02i' % i, slug='a%s' % i)


########NEW FILE########
__FILENAME__ = urls
import views
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # base
    #(r'^about/login-required/$',
    #    views.DecoratedAboutView()),
    
    # DetailView
    (r'^detail/obj/$',
        views.ObjectDetail.as_view()),
    url(r'^detail/author/(?P<pk>\d+)/$',
        views.AuthorDetail.as_view(),
        name="author_detail"),
    (r'^detail/author/byslug/(?P<slug>[\w-]+)/$',
        views.AuthorDetail.as_view()),
    (r'^detail/author/invalid/url/$',
        views.AuthorDetail.as_view()),
    (r'^detail/author/invalid/qs/$',
        views.AuthorDetail.as_view(queryset=None)),

    # EditView
    (r'^edit/authors/create/$',
        views.AuthorCreate.as_view()),
    (r'^edit/authors/create/restricted/$',
        views.AuthorCreateRestricted.as_view()),
    (r'^edit/author/(?P<pk>\d+)/update/$',
        views.AuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/$',
        views.AuthorDelete.as_view()),
    
    # ArchiveView
    (r'^dates/books/$',
        views.BookArchive.as_view()),
    (r'^dates/books/invalid/$',
        views.BookArchive.as_view(queryset=None)),
    
    # ListView
    (r'^list/dict/$',
        views.DictList.as_view()),
    url(r'^list/authors/$',
        views.AuthorList.as_view(),
        name="authors_list"),
    (r'^list/authors/paginated/$', 
        views.PaginatedAuthorList.as_view(paginate_by=30)),
    (r'^list/authors/paginated/(?P<page>\d+)/$', 
        views.PaginatedAuthorList.as_view(paginate_by=30)),
    (r'^list/authors/notempty/$',
        views.AuthorList.as_view(allow_empty=False)),
    (r'^list/authors/template_object_name/$', 
        views.AuthorList.as_view(template_object_name='author')),
    (r'^list/authors/invalid/$',
        views.AuthorList.as_view(queryset=None)),
    
    # YearView
    # Mixing keyword and possitional captures below is intentional; the views
    # ought to be able to accept either.
    (r'^dates/books/(?P<year>\d{4})/$',
        views.BookYearArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/make_object_list/$', 
        views.BookYearArchive.as_view(make_object_list=True)),
    (r'^dates/books/(?P<year>\d{4})/allow_empty/$',
        views.BookYearArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/allow_future/$',
        views.BookYearArchive.as_view(allow_future=True)),
    (r'^dates/books/no_year/$',
        views.BookYearArchive.as_view()),

    # MonthView
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
        views.BookMonthArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        views.BookMonthArchive.as_view(month_format='%m')),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/allow_empty/$',
        views.BookMonthArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/allow_future/$',
        views.BookMonthArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/no_month/$',
        views.BookMonthArchive.as_view()),

    # WeekView
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/$',
        views.BookWeekArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/allow_empty/$',
        views.BookWeekArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/allow_future/$',
        views.BookWeekArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/week/no_week/$',
        views.BookWeekArchive.as_view()),

    # DayView
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/$',
        views.BookDayArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        views.BookDayArchive.as_view(month_format='%m')),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/allow_empty/$',
        views.BookDayArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/allow_future/$',
        views.BookDayArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/no_day/$',
        views.BookDayArchive.as_view()),

    # TodayView
    (r'dates/books/today/$',
        views.BookTodayArchive.as_view()),
    (r'dates/books/today/allow_empty/$',
        views.BookTodayArchive.as_view(allow_empty=True)),

    # DateDetailView
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/(?P<pk>\d+)/$',
        views.BookDetail.as_view()),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<pk>\d+)/$',
        views.BookDetail.as_view(month_format='%m')),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/(?P<pk>\d+)/allow_future/$',
        views.BookDetail.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/nopk/$',
        views.BookDetail.as_view()),

    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/byslug/(?P<slug>[\w-]+)/$',
        views.BookDetail.as_view()),

    # Useful for testing redirects
    (r'^accounts/login/$',  'django.contrib.auth.views.login')
)
########NEW FILE########
__FILENAME__ = utils
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest

class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.
    
    http://djangosnippets.org/snippets/963/
    
    Usage:
    
    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})
    
    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client
    
    Once you have a request object you can pass it to any view function, 
    just as if that view had been hooked up using a URLconf.
    
    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)
    

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator

from class_based_views.tests.models import Author, Book
from class_based_views.tests.forms import AuthorForm
import class_based_views

class ObjectDetail(class_based_views.DetailView):
    template_name = 'tests/detail.html'
    
    def get_object(self):
        return {'foo': 'bar'}


class AuthorDetail(class_based_views.DetailView):
    queryset = Author.objects.all()


class DictList(class_based_views.ListView):
    """A ListView that doesn't use a model."""
    queryset = [
        {'first': 'John', 'last': 'Lennon'},
        {'last': 'Yoko',  'last': 'Ono'}
    ]
    template_name = 'tests/list.html'


class AuthorList(class_based_views.ListView):
    queryset = Author.objects.all()
    template_name = 'tests/list.html'


class PaginatedAuthorList(class_based_views.PaginatedListView):
    queryset = Author.objects.all()
    template_name = 'tests/list.html'


class AuthorCreate(class_based_views.CreateView):
    form = AuthorForm
    template_name = 'tests/list.html'
    
    def redirect_to(self, obj):
        return reverse('authors_list')


class AuthorCreateRestricted(AuthorCreate):
    POST = method_decorator(login_required)(AuthorCreate.POST)


class AuthorUpdate(class_based_views.UpdateView):
    queryset = Author.objects.all()
    form = AuthorForm
    template_name = 'tests/detail.html'

    def redirect_to(self, obj):
        return reverse('author_detail', args=[obj.id,])


class AuthorDelete(class_based_views.DeleteView):
    queryset = Author.objects.all()
    template_name = 'tests/detail.html'

    def redirect_to(self, obj):
        return reverse('authors_list')


class BookConfig(object):
    queryset = Book.objects.all()
    date_field = 'pubdate'

class BookArchive(BookConfig, class_based_views.ArchiveView):
    pass

class BookYearArchive(BookConfig, class_based_views.YearView):
    pass

class BookMonthArchive(BookConfig, class_based_views.MonthView):
    pass

class BookWeekArchive(BookConfig, class_based_views.WeekView):
    pass

class BookDayArchive(BookConfig, class_based_views.DayView):
    pass

class BookTodayArchive(BookConfig, class_based_views.TodayView):
    pass

class BookDetail(BookConfig, class_based_views.DateDetailView):
    pass

########NEW FILE########
__FILENAME__ = utils

# Stolen from piston http://bitbucket.org/jespern/django-piston/src/tip/piston/utils.py
def coerce_put_post(request):
    """
    Django doesn't particularly understand REST.
    In case we send data over PUT, Django won't
    actually look at the data and load it. We need
    to twist its arm here.
    
    The try/except abominiation here is due to a bug
    in mod_python. This should fix it.
    """
    # Bug fix: if _load_post_and_files has already been called, for
    # example by middleware accessing request.POST, the below code to
    # pretend the request is a POST instead of a PUT will be too late
    # to make a difference. Also calling _load_post_and_files will result 
    # in the following exception:
    #   AttributeError: You cannot set the upload handlers after the upload has been processed.
    # The fix is to check for the presence of the _post field which is set 
    # the first time _load_post_and_files is called (both by wsgi.py and 
    # modpython.py). If it's set, the request has to be 'reset' to redo
    # the query value parsing in POST mode.
    if hasattr(request, '_post'):
        del request._post
        del request._files
    
    try:
        request.method = "POST"
        request._load_post_and_files()
        request.method = "PUT"
    except AttributeError:
        request.META['REQUEST_METHOD'] = 'POST'
        request._load_post_and_files()
        request.META['REQUEST_METHOD'] = 'PUT'
        
    request.PUT = request.POST


########NEW FILE########
