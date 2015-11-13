__FILENAME__ = fields
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple

from django import forms

from .widgets import RangeWidget, LookupTypeWidget


class RangeField(forms.MultiValueField):
    widget = RangeWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.DecimalField(),
            forms.DecimalField(),
        )
        super(RangeField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return slice(*data_list)
        return None

Lookup = namedtuple('Lookup', ('value', 'lookup_type'))
class LookupTypeField(forms.MultiValueField):
    def __init__(self, field, lookup_choices, *args, **kwargs):
        fields = (
            field,
            forms.ChoiceField(choices=lookup_choices)
        )
        defaults = {
            'widgets': [f.widget for f in fields],
        }
        widget = LookupTypeWidget(**defaults)
        kwargs['widget'] = widget
        super(LookupTypeField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if len(data_list)==2:
            return Lookup(value=data_list[0], lookup_type=data_list[1] or 'exact')
        return Lookup(value=None, lookup_type='exact')

########NEW FILE########
__FILENAME__ = filters
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import timedelta


from django import forms
from django.db.models import Q
from django.db.models.sql.constants import QUERY_TERMS
from django.utils import six
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from .fields import RangeField, LookupTypeField, Lookup


__all__ = [
    'Filter', 'CharFilter', 'BooleanFilter', 'ChoiceFilter',
    'MultipleChoiceFilter', 'DateFilter', 'DateTimeFilter', 'TimeFilter',
    'ModelChoiceFilter', 'ModelMultipleChoiceFilter', 'NumberFilter',
    'RangeFilter', 'DateRangeFilter', 'AllValuesFilter',
]


LOOKUP_TYPES = sorted(QUERY_TERMS)


class Filter(object):
    creation_counter = 0
    field_class = forms.Field

    def __init__(self, name=None, label=None, widget=None, action=None,
        lookup_type='exact', required=False, distinct=False, exclude=False, **kwargs):
        self.name = name
        self.label = label
        if action:
            self.filter = action
        self.lookup_type = lookup_type
        self.widget = widget
        self.required = required
        self.extra = kwargs
        self.distinct = distinct
        self.exclude = exclude

        self.creation_counter = Filter.creation_counter
        Filter.creation_counter += 1

    @property
    def field(self):
        if not hasattr(self, '_field'):
            help_text = _('This is an exclusion filter') if self.exclude else ''
            if (self.lookup_type is None or
                    isinstance(self.lookup_type, (list, tuple))):
                if self.lookup_type is None:
                    lookup = [(x, x) for x in LOOKUP_TYPES]
                else:
                    lookup = [
                        (x, x) for x in LOOKUP_TYPES if x in self.lookup_type]
                self._field = LookupTypeField(self.field_class(
                    required=self.required, widget=self.widget, **self.extra),
                    lookup, required=self.required, label=self.label, help_text=help_text)
            else:
                self._field = self.field_class(required=self.required,
                    label=self.label, widget=self.widget,
                    help_text=help_text, **self.extra)
        return self._field

    def filter(self, qs, value):
        if isinstance(value, Lookup):
            lookup = six.text_type(value.lookup_type)
            value = value.value
        else:
            lookup = self.lookup_type
        if value in ([], (), {}, None, ''):
            return qs
        method = qs.exclude if self.exclude else qs.filter
        qs = method(**{'%s__%s' % (self.name, lookup): value})
        if self.distinct:
            qs = qs.distinct()
        return qs


class CharFilter(Filter):
    field_class = forms.CharField


class BooleanFilter(Filter):
    field_class = forms.NullBooleanField

    def filter(self, qs, value):
        if value is not None:
            return qs.filter(**{self.name: value})
        return qs


class ChoiceFilter(Filter):
    field_class = forms.ChoiceField


class MultipleChoiceFilter(Filter):
    """
    This filter preforms an OR query on the selected options.
    """
    field_class = forms.MultipleChoiceField

    def filter(self, qs, value):
        value = value or ()
        if len(value) == len(self.field.choices):
            return qs
        q = Q()
        for v in value:
            q |= Q(**{self.name: v})
        return qs.filter(q).distinct()


class DateFilter(Filter):
    field_class = forms.DateField


class DateTimeFilter(Filter):
    field_class = forms.DateTimeField


class TimeFilter(Filter):
    field_class = forms.TimeField


class ModelChoiceFilter(Filter):
    field_class = forms.ModelChoiceField


class ModelMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = forms.ModelMultipleChoiceField


class NumberFilter(Filter):
    field_class = forms.DecimalField


class RangeFilter(Filter):
    field_class = RangeField

    def filter(self, qs, value):
        if value:
            lookup = '%s__range' % self.name
            return qs.filter(**{lookup: (value.start, value.stop)})
        return qs


_truncate = lambda dt: dt.replace(hour=0, minute=0, second=0)


class DateRangeFilter(ChoiceFilter):
    options = {
        '': (_('Any date'), lambda qs, name: qs.all()),
        1: (_('Today'), lambda qs, name: qs.filter(**{
            '%s__year' % name: now().year,
            '%s__month' % name: now().month,
            '%s__day' % name: now().day
        })),
        2: (_('Past 7 days'), lambda qs, name: qs.filter(**{
            '%s__gte' % name: _truncate(now() - timedelta(days=7)),
            '%s__lt' % name: _truncate(now() + timedelta(days=1)),
        })),
        3: (_('This month'), lambda qs, name: qs.filter(**{
            '%s__year' % name: now().year,
            '%s__month' % name: now().month
        })),
        4: (_('This year'), lambda qs, name: qs.filter(**{
            '%s__year' % name: now().year,
        })),
    }

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = [
            (key, value[0]) for key, value in six.iteritems(self.options)]
        super(DateRangeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = ''
        return self.options[value][1](qs, self.name)


class AllValuesFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.name).values_list(self.name, flat=True)
        self.extra['choices'] = [(o, o) for o in qs]
        return super(AllValuesFilter, self).field

########NEW FILE########
__FILENAME__ = filterset
from __future__ import absolute_import
from __future__ import unicode_literals

from copy import deepcopy

from django import forms
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.related import RelatedObject
from django.utils import six
from django.utils.datastructures import SortedDict
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

try:
    from django.db.models.constants import LOOKUP_SEP
except ImportError:  # pragma: nocover
    # Django < 1.5 fallback
    from django.db.models.sql.constants import LOOKUP_SEP  # noqa

from .filters import (Filter, CharFilter, BooleanFilter,
    ChoiceFilter, DateFilter, DateTimeFilter, TimeFilter, ModelChoiceFilter,
    ModelMultipleChoiceFilter, NumberFilter)


ORDER_BY_FIELD = 'o'


def get_declared_filters(bases, attrs, with_base_filters=True):
    filters = []
    for filter_name, obj in list(attrs.items()):
        if isinstance(obj, Filter):
            obj = attrs.pop(filter_name)
            if getattr(obj, 'name', None) is None:
                obj.name = filter_name
            filters.append((filter_name, obj))
    filters.sort(key=lambda x: x[1].creation_counter)

    if with_base_filters:
        for base in bases[::-1]:
            if hasattr(base, 'base_filters'):
                filters = list(base.base_filters.items()) + filters
    else:
        for base in bases[::-1]:
            if hasattr(base, 'declared_filters'):
                filters = list(base.declared_filters.items()) + filters

    return SortedDict(filters)


def get_model_field(model, f):
    parts = f.split(LOOKUP_SEP)
    opts = model._meta
    for name in parts[:-1]:
        try:
            rel = opts.get_field_by_name(name)[0]
        except FieldDoesNotExist:
            return None
        if isinstance(rel, RelatedObject):
            model = rel.model
            opts = rel.opts
        else:
            model = rel.rel.to
            opts = model._meta
    try:
        rel, model, direct, m2m = opts.get_field_by_name(parts[-1])
    except FieldDoesNotExist:
        return None
    return rel


def filters_for_model(model, fields=None, exclude=None, filter_for_field=None,
                      filter_for_reverse_field=None):
    field_dict = SortedDict()
    opts = model._meta
    if fields is None:
        fields = [f.name for f in sorted(opts.fields + opts.many_to_many)
            if not isinstance(f, models.AutoField)]
    for f in fields:
        if exclude is not None and f in exclude:
            continue
        field = get_model_field(model, f)
        if field is None:
            field_dict[f] = None
            continue
        if isinstance(field, RelatedObject):
            filter_ = filter_for_reverse_field(field, f)
        else:
            filter_ = filter_for_field(field, f)
        if filter_:
            field_dict[f] = filter_
    return field_dict


class FilterSetOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)

        self.order_by = getattr(options, 'order_by', False)

        self.form = getattr(options, 'form', forms.Form)


class FilterSetMetaclass(type):
    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, FilterSet)]
        except NameError:
            # We are defining FilterSet itself here
            parents = None
        declared_filters = get_declared_filters(bases, attrs, False)
        new_class = super(
            FilterSetMetaclass, cls).__new__(cls, name, bases, attrs)

        if not parents:
            return new_class

        opts = new_class._meta = FilterSetOptions(
            getattr(new_class, 'Meta', None))
        if opts.model:
            filters = filters_for_model(opts.model, opts.fields, opts.exclude,
                                        new_class.filter_for_field,
                                        new_class.filter_for_reverse_field)
            filters.update(declared_filters)
        else:
            filters = declared_filters

        if None in filters.values():
            raise TypeError("Meta.fields contains a field that isn't defined "
                "on this FilterSet")

        new_class.declared_filters = declared_filters
        new_class.base_filters = filters
        return new_class


FILTER_FOR_DBFIELD_DEFAULTS = {
    models.AutoField: {
        'filter_class': NumberFilter
    },
    models.CharField: {
        'filter_class': CharFilter
    },
    models.TextField: {
        'filter_class': CharFilter
    },
    models.BooleanField: {
        'filter_class': BooleanFilter
    },
    models.DateField: {
        'filter_class': DateFilter
    },
    models.DateTimeField: {
        'filter_class': DateTimeFilter
    },
    models.TimeField: {
        'filter_class': TimeFilter
    },
    models.OneToOneField: {
        'filter_class': ModelChoiceFilter,
        'extra': lambda f: {
            'queryset': f.rel.to._default_manager.complex_filter(
                f.rel.limit_choices_to),
            'to_field_name': f.rel.field_name,
        }
    },
    models.ForeignKey: {
        'filter_class': ModelChoiceFilter,
        'extra': lambda f: {
            'queryset': f.rel.to._default_manager.complex_filter(
                f.rel.limit_choices_to),
            'to_field_name': f.rel.field_name
        }
    },
    models.ManyToManyField: {
        'filter_class': ModelMultipleChoiceFilter,
        'extra': lambda f: {
            'queryset': f.rel.to._default_manager.complex_filter(
                f.rel.limit_choices_to),
        }
    },
    models.DecimalField: {
        'filter_class': NumberFilter,
    },
    models.SmallIntegerField: {
        'filter_class': NumberFilter,
    },
    models.IntegerField: {
        'filter_class': NumberFilter,
    },
    models.PositiveIntegerField: {
        'filter_class': NumberFilter,
    },
    models.PositiveSmallIntegerField: {
        'filter_class': NumberFilter,
    },
    models.FloatField: {
        'filter_class': NumberFilter,
    },
    models.NullBooleanField: {
        'filter_class': BooleanFilter,
    },
    models.SlugField: {
        'filter_class': CharFilter,
    },
    models.EmailField: {
        'filter_class': CharFilter,
    },
    models.FilePathField: {
        'filter_class': CharFilter,
    },
    models.URLField: {
        'filter_class': CharFilter,
    },
    models.IPAddressField: {
        'filter_class': CharFilter,
    },
    models.CommaSeparatedIntegerField: {
        'filter_class': CharFilter,
    },
}


class BaseFilterSet(object):
    filter_overrides = {}
    order_by_field = ORDER_BY_FIELD
    strict = True

    def __init__(self, data=None, queryset=None, prefix=None, strict=None):
        self.is_bound = data is not None
        self.data = data or {}
        if queryset is None:
            queryset = self._meta.model._default_manager.all()
        self.queryset = queryset
        self.form_prefix = prefix
        if strict is not None:
            self.strict = strict

        self.filters = deepcopy(self.base_filters)
        # propagate the model being used through the filters
        for filter_ in self.filters.values():
            filter_.model = self._meta.model

    def __iter__(self):
        for obj in self.qs:
            yield obj

    def __len__(self):
        return len(self.qs)

    def __getitem__(self, key):
        return self.qs[key]

    @property
    def qs(self):
        if not hasattr(self, '_qs'):
            valid = self.is_bound and self.form.is_valid()

            if self.strict and self.is_bound and not valid:
                self._qs = self.queryset.none()
                return self._qs

            # start with all the results and filter from there
            qs = self.queryset.all()
            for name, filter_ in six.iteritems(self.filters):
                value = None
                if valid:
                    value = self.form.cleaned_data[name]
                else:
                    raw_value = self.form[name].value()
                    try:
                        value = self.form.fields[name].clean(raw_value)
                    except forms.ValidationError:
                        # for invalid values either:
                        # strictly "apply" filter yielding no results and get outta here
                        if self.strict:
                            self._qs = self.queryset.none()
                            return self._qs
                        else:  # or ignore this filter altogether
                            pass

                if value is not None:  # valid & clean data
                    qs = filter_.filter(qs, value)

            if self._meta.order_by:
                order_field = self.form.fields[self.order_by_field]
                data = self.form[self.order_by_field].data
                ordered_value = None
                try:
                    ordered_value = order_field.clean(data)
                except forms.ValidationError:
                    pass

                if ordered_value in EMPTY_VALUES and self.strict:
                    ordered_value = self.form.fields[self.order_by_field].choices[0][0]

                if ordered_value:
                    qs = qs.order_by(*self.get_order_by(ordered_value))

            self._qs = qs

        return self._qs

    def count(self):
        return self.qs.count()

    @property
    def form(self):
        if not hasattr(self, '_form'):
            fields = SortedDict([
                (name, filter_.field)
                for name, filter_ in six.iteritems(self.filters)])
            fields[self.order_by_field] = self.ordering_field
            Form = type(str('%sForm' % self.__class__.__name__),
                        (self._meta.form,), fields)
            if self.is_bound:
                self._form = Form(self.data, prefix=self.form_prefix)
            else:
                self._form = Form(prefix=self.form_prefix)
        return self._form

    def get_ordering_field(self):
        if self._meta.order_by:
            if isinstance(self._meta.order_by, (list, tuple)):
                if isinstance(self._meta.order_by[0], (list, tuple)):
                    # e.g. (('field', 'Display name'), ...)
                    choices = [(f[0], f[1]) for f in self._meta.order_by]
                else:
                    choices = [(f, _('%s (descending)' % capfirst(f[1:])) if f[0] == '-' else capfirst(f))
                               for f in self._meta.order_by]
            else:
                # add asc and desc field names
                # use the filter's label if provided
                choices = []
                for f, fltr in self.filters.items():
                    choices.extend([
                        (fltr.name or f, fltr.label or capfirst(f)),
                        ("-%s" % (fltr.name or f), _('%s (descending)' % (fltr.label or capfirst(f))))
                    ])
            return forms.ChoiceField(label="Ordering", required=False,
                                     choices=choices)

    @property
    def ordering_field(self):
        if not hasattr(self, '_ordering_field'):
            self._ordering_field = self.get_ordering_field()
        return self._ordering_field

    def get_order_by(self, order_choice):
        return [order_choice]

    @classmethod
    def filter_for_field(cls, f, name):
        filter_for_field = dict(FILTER_FOR_DBFIELD_DEFAULTS)
        filter_for_field.update(cls.filter_overrides)

        default = {
            'name': name,
            'label': capfirst(f.verbose_name)
        }

        if f.choices:
            default['choices'] = f.choices
            return ChoiceFilter(**default)

        data = filter_for_field.get(f.__class__)
        if data is None:
            # could be a derived field, inspect parents
            for class_ in f.__class__.mro():
                # skip if class_ is models.Field or object
                # 1st item in mro() is original class
                if class_ in (f.__class__, models.Field, object):
                    continue
                data = filter_for_field.get(class_)
                if data:
                    break
            if data is None:
                return
        filter_class = data.get('filter_class')
        default.update(data.get('extra', lambda f: {})(f))
        if filter_class is not None:
            return filter_class(**default)

    @classmethod
    def filter_for_reverse_field(cls, f, name):
        rel = f.field.rel
        queryset = f.model._default_manager.all()
        default = {
            'name': name,
            'label': capfirst(rel.related_name),
            'queryset': queryset,
        }
        if rel.multiple:
            return ModelMultipleChoiceFilter(**default)
        else:
            return ModelChoiceFilter(**default)


class FilterSet(six.with_metaclass(FilterSetMetaclass, BaseFilterSet)):
    pass


def filterset_factory(model):
    meta = type(str('Meta'), (object,), {'model': model})
    filterset = type(str('%sFilterSet' % model._meta.object_name),
                     (FilterSet,), {'Meta': meta})
    return filterset

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import
from __future__ import unicode_literals
from django.core.exceptions import ImproperlyConfigured
from django.views.generic import View
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.list import MultipleObjectTemplateResponseMixin
from .filterset import filterset_factory


class FilterMixin(object):
    """
    A mixin that provides a way to show and handle a FilterSet in a request.
    """
    filterset_class = None

    def get_filterset_class(self):
        """
        Returns the filterset class to use in this view
        """
        if self.filterset_class:
            return self.filterset_class
        elif self.model:
            return filterset_factory(self.model)
        else:
            msg = "'%s' must define 'filterset_class' or 'model'"
            raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_filterset(self, filterset_class):
        """
        Returns an instance of the filterset to be used in this view.
        """
        kwargs = self.get_filterset_kwargs(filterset_class)
        return filterset_class(**kwargs)

    def get_filterset_kwargs(self, filterset_class):
        """
        Returns the keyword arguments for instanciating the filterset.
        """
        kwargs = {'data': self.request.GET or None}
        try:
            kwargs.update({
                'queryset': self.get_queryset(),
            })
        except ImproperlyConfigured:
            # ignore the error here if the filterset has a model defined
            # to acquire a queryset from
            if filterset_class._meta.model is None:
                msg = ("'%s' does not define a 'model' and the view '%s' does "
                       "not return a valid queryset from 'get_queryset'.  You "
                       "must fix one of them.")
                args = (filterset_class.__name__, self.__class__.__name__)
                raise ImproperlyConfigured(msg % args)
        return kwargs


class BaseFilterView(FilterMixin, MultipleObjectMixin, View):

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        self.object_list = self.filterset.qs
        context = self.get_context_data(filter=self.filterset,
                                        object_list=self.object_list)
        return self.render_to_response(context)


class FilterView(MultipleObjectTemplateResponseMixin, BaseFilterView):
    """
    Render some list of objects with filter, set by `self.model` or
    `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """
    template_name_suffix = '_filter'


def object_filter(request, model=None, queryset=None, template_name=None,
                  extra_context=None, context_processors=None,
                  filter_class=None):
    class ECFilterView(FilterView):
        """Handle the extra_context from the functional object_filter view"""
        def get_context_data(self, **kwargs):
            context = super(ECFilterView, self).get_context_data(**kwargs)
            extra_context = self.kwargs.get('extra_context') or {}
            for k, v in extra_context.items():
                if callable(v):
                    v = v()
                context[k] = v
            return context

    kwargs = dict(model=model, queryset=queryset, template_name=template_name,
                  filterset_class=filter_class)
    view = ECFilterView.as_view(**kwargs)
    return view(request, extra_context=extra_context)

########NEW FILE########
__FILENAME__ = widgets
from __future__ import absolute_import
from __future__ import unicode_literals

from itertools import chain
try:
    from urllib.parse import urlencode
except:
    from urllib import urlencode  # noqa

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.forms.widgets import flatatt
try:
    from django.utils.encoding import force_text
except:  # pragma: nocover
    from django.utils.encoding import force_unicode as force_text  # noqa
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


class LinkWidget(forms.Widget):
    def __init__(self, attrs=None, choices=()):
        super(LinkWidget, self).__init__(attrs)

        self.choices = choices

    def value_from_datadict(self, data, files, name):
        value = super(LinkWidget, self).value_from_datadict(data, files, name)
        self.data = data
        return value

    def render(self, name, value, attrs=None, choices=()):
        if not hasattr(self, 'data'):
            self.data = {}
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs)
        output = ['<ul%s>' % flatatt(final_attrs)]
        options = self.render_options(choices, [value], name)
        if options:
            output.append(options)
        output.append('</ul>')
        return mark_safe('\n'.join(output))

    def render_options(self, choices, selected_choices, name):
        selected_choices = set(force_text(v) for v in selected_choices)
        output = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                for option in option_label:
                    output.append(
                        self.render_option(name, selected_choices, *option))
            else:
                output.append(
                    self.render_option(name, selected_choices,
                                       option_value, option_label))
        return '\n'.join(output)

    def render_option(self, name, selected_choices,
                      option_value, option_label):
        option_value = force_text(option_value)
        if option_label == BLANK_CHOICE_DASH[0][1]:
            option_label = _("All")
        data = self.data.copy()
        data[name] = option_value
        selected = data == self.data or option_value in selected_choices
        try:
            url = data.urlencode()
        except AttributeError:
            url = urlencode(data)
        return self.option_string() % {
             'attrs': selected and ' class="selected"' or '',
             'query_string': url,
             'label': force_text(option_label)
        }

    def option_string(self):
        return '<li><a%(attrs)s href="?%(query_string)s">%(label)s</a></li>'


class RangeWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = (forms.TextInput(attrs=attrs), forms.TextInput(attrs=attrs))
        super(RangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.start, value.stop]
        return [None, None]

    def format_output(self, rendered_widgets):
        return '-'.join(rendered_widgets)


class LookupTypeWidget(forms.MultiWidget):
    def decompress(self, value):
        if value is None:
            return [None, None]
        return value

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-filter documentation build configuration file, created by
# sphinx-quickstart on Mon Sep 17 11:25:20 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-filter'
copyright = u'2013, Alex Gaynor and others.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.0'
# The full version, including alpha/beta/rc tags.
release = '0.6.0'

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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
#html_static_path = ['_static']

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
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

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
htmlhelp_basename = 'django-filterdoc'


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
  ('asd', 'django-filter.tex', u'django-filter Documentation',
   u'Alex Gaynor and others.', 'manual'),
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
    ('asd', 'django-filter', u'django-filter Documentation',
     [u'Alex Gaynor and others.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('asd', 'django-filter', u'django-filter Documentation',
   u'Alex Gaynor and others.', 'django-filter', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = runshell
#!/usr/bin/env python
import sys
from django.conf import settings
from django.core.management import call_command
from django.core.management import execute_from_command_line

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            },
        },
        INSTALLED_APPS=(
            'django_filters',
            'tests',
        ),
        ROOT_URLCONF=None,
        USE_TZ=True,
        SECRET_KEY='foobar'
    )


def runshell():
    call_command('syncdb', interactive=False)
    argv = sys.argv[:1] + ['shell'] + sys.argv[1:]
    execute_from_command_line(argv)

if __name__ == '__main__':
    runshell()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from django import VERSION
from django.conf import settings
from django.core.management import execute_from_command_line

if not settings.configured:
    test_runners_args = {}
    if VERSION[1] < 6:
        test_runners_args = {
            'TEST_RUNNER': 'discover_runner.DiscoverRunner',
        }
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            },
        },
        INSTALLED_APPS=(
            'django_filters',
            'tests',
        ),
        ROOT_URLCONF=None,
        USE_TZ=True,
        SECRET_KEY='foobar',
        **test_runners_args
    )


def runtests():
    argv = sys.argv[:1] + ['test'] + sys.argv[1:]
    execute_from_command_line(argv)


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


STATUS_CHOICES = (
    (0, 'Regular'),
    (1, 'Manager'),
    (2, 'Admin'),
)


# classes for testing filters with inherited fields
class SubCharField(models.CharField):
    pass


class SubSubCharField(SubCharField):
    pass


class SubnetMaskField(models.Field):
    empty_strings_allowed = False
    description = "Subnet Mask"

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 15
        models.Field.__init__(self, *args, **kwargs)

    def get_internal_type(self):
        return "IPAddressField"

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.IPAddressField}
        defaults.update(kwargs)
        return super(SubnetMaskField, self).formfield(**defaults)


@python_2_unicode_compatible
class User(models.Model):
    username = models.CharField(max_length=255)
    first_name = SubCharField(max_length=100)
    last_name = SubSubCharField(max_length=100)

    status = models.IntegerField(choices=STATUS_CHOICES, default=0)

    is_active = models.BooleanField(default=False)

    favorite_books = models.ManyToManyField('Book', related_name='lovers')

    def __str__(self):
        return self.username


@python_2_unicode_compatible
class AdminUser(User):
    class Meta:
        proxy = True

    def __str__(self):
        return "%s (ADMIN)" % self.username


@python_2_unicode_compatible
class Comment(models.Model):
    text = models.TextField()
    author = models.ForeignKey(User, related_name='comments')

    date = models.DateField()
    time = models.TimeField()

    def __str__(self):
        return "%s said %s" % (self.author, self.text[:25])


class Article(models.Model):
    published = models.DateTimeField()
    author = models.ForeignKey(User, null=True)


@python_2_unicode_compatible
class Book(models.Model):
    title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    average_rating = models.FloatField()

    def __str__(self):
        return self.title


class Place(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True


class Restaurant(Place):
    serves_pizza = models.BooleanField()


class NetworkSetting(models.Model):
    ip = models.IPAddressField()
    mask = SubnetMaskField()


@python_2_unicode_compatible
class Company(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Location(models.Model):
    company = models.ForeignKey(Company, related_name='locations')
    name = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    open_days = models.CharField(max_length=7)

    def __str__(self):
        return '%s: %s' % (self.company.name, self.name)


class Account(models.Model):
    name = models.CharField(max_length=100)
    in_good_standing = models.BooleanField()
    friendly = models.BooleanField()


class Profile(models.Model):
    account = models.OneToOneField(Account, related_name='profile')
    likes_coffee = models.BooleanField()
    likes_tea = models.BooleanField()


class BankAccount(Account):
    amount_saved = models.IntegerField(default=0)


class Node(models.Model):
    name = models.CharField(max_length=20)
    adjacents = models.ManyToManyField('self')


class DirectedNode(models.Model):
    name = models.CharField(max_length=20)
    outbound_nodes = models.ManyToManyField('self',
                                            symmetrical=False,
                                            related_name='inbound_nodes')


class Worker(models.Model):
    name = models.CharField(max_length=100)


class HiredWorker(models.Model):
    salary = models.IntegerField()
    hired_on = models.DateField()
    worker = models.ForeignKey(Worker)
    business = models.ForeignKey('Business')


class Business(models.Model):
    name = models.CharField(max_length=100)
    employees = models.ManyToManyField(Worker,
                                       through=HiredWorker,
                                       related_name='employers')


########NEW FILE########
__FILENAME__ = test_fields
from __future__ import absolute_import
from __future__ import unicode_literals

import decimal

import django
from django import forms
from django.utils import unittest
from django.test import TestCase

from django_filters.widgets import RangeWidget
from django_filters.fields import RangeField
from django_filters.fields import LookupTypeField
from django_filters.fields import Lookup

def to_d(float_value):
    return decimal.Decimal('%.2f' % float_value)


class RangeFieldTests(TestCase):

    def test_field(self):
        f = RangeField()
        self.assertEqual(len(f.fields), 2)

    def test_clean(self):
        w = RangeWidget()
        f = RangeField(widget=w)

        self.assertEqual(
            f.clean(['12.34', '55']),
            slice(to_d(12.34), to_d(55)))


class LookupTypeFieldTests(TestCase):

    def test_field(self):
        inner = forms.DecimalField()
        f = LookupTypeField(inner, [('gt', 'gt'), ('lt', 'lt')])
        self.assertEqual(len(f.fields), 2)

    def test_clean(self):
        inner = forms.DecimalField()
        f = LookupTypeField(inner, [('gt', 'gt'), ('lt', 'lt')])
        self.assertEqual(
            f.clean(['12.34', 'lt']),
            Lookup(to_d(12.34), 'lt'))

    @unittest.skipIf(django.VERSION >= (1, 6),
                     'Django 1.6 uses html5 fields')
    def test_render(self):
        inner = forms.DecimalField()
        f = LookupTypeField(inner, [('gt', 'gt'), ('lt', 'lt')])
        self.assertHTMLEqual(f.widget.render('price', ''), """
            <input type="text" name="price_0" />
            <select name="price_1">
                <option value="gt">gt</option>
                <option value="lt">lt</option>
            </select>""")
        self.assertHTMLEqual(f.widget.render('price', ['abc', 'lt']), """
            <input type="text" name="price_0" value="abc" />
            <select name="price_1">
                <option value="gt">gt</option>
                <option selected="selected" value="lt">lt</option>
            </select>""")

    @unittest.skipUnless(django.VERSION >= (1, 6),
                         'Django 1.6 uses html5 fields')
    def test_render_used_html5(self):
        inner = forms.DecimalField()
        f = LookupTypeField(inner, [('gt', 'gt'), ('lt', 'lt')])
        self.assertHTMLEqual(f.widget.render('price', ''), """
            <input type="number" step="any" name="price_0" />
            <select name="price_1">
                <option value="gt">gt</option>
                <option value="lt">lt</option>
            </select>""")
        self.assertHTMLEqual(f.widget.render('price', ['abc', 'lt']), """
            <input type="number" step="any" name="price_0" value="abc" />
            <select name="price_1">
                <option value="gt">gt</option>
                <option selected="selected" value="lt">lt</option>
            </select>""")


########NEW FILE########
__FILENAME__ = test_filtering
from __future__ import absolute_import
from __future__ import unicode_literals

import mock
import datetime

from django.utils import unittest
from django.test import TestCase
from django.utils import six
from django.utils.timezone import now
from django.utils import timezone

from django_filters.filterset import FilterSet
from django_filters.filters import AllValuesFilter
from django_filters.filters import CharFilter
from django_filters.filters import ChoiceFilter
from django_filters.filters import DateRangeFilter
# from django_filters.filters import DateTimeFilter
from django_filters.filters import MultipleChoiceFilter
from django_filters.filters import NumberFilter
from django_filters.filters import RangeFilter
# from django_filters.widgets import LinkWidget

from .models import User
from .models import Comment
from .models import Book
# from .models import Restaurant
from .models import Article
# from .models import NetworkSetting
# from .models import SubnetMaskField
from .models import Company
from .models import Location
from .models import Account
from .models import BankAccount
from .models import Profile
from .models import Node
from .models import DirectedNode
from .models import STATUS_CHOICES


class CharFilterTests(TestCase):

    def test_filtering(self):
        b1 = Book.objects.create(
            title="Ender's Game", price='1.00', average_rating=3.0)
        b2 = Book.objects.create(
            title="Rainbow Six", price='1.00', average_rating=3.0)
        b3 = Book.objects.create(
            title="Snowcrash", price='1.00', average_rating=3.0)

        class F(FilterSet):
            class Meta:
                model = Book
                fields = ['title']

        qs = Book.objects.all()
        f = F(queryset=qs)
        self.assertQuerysetEqual(f.qs, [b1.pk, b2.pk, b3.pk],
                                 lambda o: o.pk, ordered=False)
        f = F({'title': 'Snowcrash'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [b3.pk], lambda o: o.pk)


class IntegerFilterTest(TestCase):

    def test_filtering(self):
        default_values = {
            'in_good_standing': True,
            'friendly': False,
        }
        b1 = BankAccount.objects.create(amount_saved=0, **default_values)
        b2 = BankAccount.objects.create(amount_saved=3, **default_values)
        b3 = BankAccount.objects.create(amount_saved=10, **default_values)

        class F(FilterSet):
            class Meta:
                model = BankAccount
                fields = ['amount_saved']

        qs = BankAccount.objects.all()
        f = F(queryset=qs)
        self.assertQuerysetEqual(f.qs, [b1.pk, b2.pk, b3.pk],
                                 lambda o: o.pk, ordered=False)
        f = F({'amount_saved': '10'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [b3.pk], lambda o: o.pk)
        f = F({'amount_saved': '0'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [b1.pk], lambda o: o.pk)


class BooleanFilterTests(TestCase):

    def test_filtering(self):
        User.objects.create(username='alex', is_active=False)
        User.objects.create(username='jacob', is_active=True)
        User.objects.create(username='aaron', is_active=False)

        class F(FilterSet):
            class Meta:
                model = User
                fields = ['is_active']

        qs = User.objects.all()

        # '2' and '3' are how the field expects the data from the browser
        f = F({'is_active': '2'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['jacob'], lambda o: o.username, False)

        f = F({'is_active': '3'}, queryset=qs)
        self.assertQuerysetEqual(f.qs,
                                 ['alex', 'aaron'],
                                 lambda o: o.username, False)

        f = F({'is_active': '1'}, queryset=qs)
        self.assertQuerysetEqual(f.qs,
                                 ['alex', 'aaron', 'jacob'],
                                 lambda o: o.username, False)


class ChoiceFilterTests(TestCase):

    def test_filtering(self):
        User.objects.create(username='alex', status=1)
        User.objects.create(username='jacob', status=2)
        User.objects.create(username='aaron', status=2)
        User.objects.create(username='carl', status=0)

        class F(FilterSet):
            class Meta:
                model = User
                fields = ['status']

        f = F()
        self.assertQuerysetEqual(f.qs,
                                 ['aaron', 'alex', 'jacob', 'carl'],
                                 lambda o: o.username, False)
        f = F({'status': '1'})
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username, False)

        f = F({'status': '2'})
        self.assertQuerysetEqual(f.qs, ['jacob', 'aaron'],
                                 lambda o: o.username, False)

        f = F({'status': '0'})
        self.assertQuerysetEqual(f.qs, ['carl'], lambda o: o.username, False)


class MultipleChoiceFilterTests(TestCase):

    def test_filtering(self):
        User.objects.create(username='alex', status=1)
        User.objects.create(username='jacob', status=2)
        User.objects.create(username='aaron', status=2)
        User.objects.create(username='carl', status=0)

        class F(FilterSet):
            status = MultipleChoiceFilter(choices=STATUS_CHOICES)

            class Meta:
                model = User
                fields = ['status']

        qs = User.objects.all().order_by('username')
        f = F(queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ['aaron', 'jacob', 'alex', 'carl'],
            lambda o: o.username, False)

        f = F({'status': ['0']}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ['carl'], lambda o: o.username)

        f = F({'status': ['0', '1']}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ['alex', 'carl'], lambda o: o.username)

        f = F({'status': ['0', '1', '2']}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ['aaron', 'alex', 'carl', 'jacob'], lambda o: o.username)


class DateFilterTests(TestCase):

    def test_filtering(self):
        today = now().date()
        timestamp = now().time().replace(microsecond=0)
        last_week = today - datetime.timedelta(days=7)
        check_date = six.text_type(last_week)
        u = User.objects.create(username='alex')
        Comment.objects.create(author=u, time=timestamp, date=today)
        Comment.objects.create(author=u, time=timestamp, date=last_week)
        Comment.objects.create(author=u, time=timestamp, date=today)
        Comment.objects.create(author=u, time=timestamp, date=last_week)

        class F(FilterSet):
            class Meta:
                model = Comment
                fields = ['date']

        f = F({'date': check_date}, queryset=Comment.objects.all())
        self.assertEqual(len(f.qs), 2)
        self.assertQuerysetEqual(f.qs, [2, 4], lambda o: o.pk, False)


class TimeFilterTests(TestCase):

    def test_filtering(self):
        today = now().date()
        now_time = now().time().replace(microsecond=0)
        ten_min_ago = (now() - datetime.timedelta(minutes=10))
        fixed_time = ten_min_ago.time().replace(microsecond=0)
        check_time = six.text_type(fixed_time)
        u = User.objects.create(username='alex')
        Comment.objects.create(author=u, time=now_time, date=today)
        Comment.objects.create(author=u, time=fixed_time, date=today)
        Comment.objects.create(author=u, time=now_time, date=today)
        Comment.objects.create(author=u, time=fixed_time, date=today)

        class F(FilterSet):
            class Meta:
                model = Comment
                fields = ['time']

        f = F({'time': check_time}, queryset=Comment.objects.all())
        self.assertEqual(len(f.qs), 2)
        self.assertQuerysetEqual(f.qs, [2, 4], lambda o: o.pk, False)


class DateTimeFilterTests(TestCase):

    def test_filtering(self):
        now_dt = now()
        ten_min_ago = now_dt - datetime.timedelta(minutes=10)
        one_day_ago = now_dt - datetime.timedelta(days=1)
        u = User.objects.create(username='alex')
        Article.objects.create(author=u, published=now_dt)
        Article.objects.create(author=u, published=ten_min_ago)
        Article.objects.create(author=u, published=one_day_ago)

        tz = timezone.get_current_timezone()
        # make naive, like a browser would send
        local_ten_min_ago = timezone.make_naive(ten_min_ago, tz)
        check_dt = six.text_type(local_ten_min_ago)

        class F(FilterSet):
            class Meta:
                model = Article
                fields = ['published']

        qs = Article.objects.all()
        f = F({'published': ten_min_ago}, queryset=qs)
        self.assertEqual(len(f.qs), 1)
        self.assertQuerysetEqual(f.qs, [2], lambda o: o.pk)

        # this is how it would come through a browser
        f = F({'published': check_dt}, queryset=qs)
        self.assertEqual(
            len(f.qs),
            1,
            "%s isn't matching %s when cleaned" % (check_dt, ten_min_ago))
        self.assertQuerysetEqual(f.qs, [2], lambda o: o.pk)


class ModelChoiceFilterTests(TestCase):

    def test_filtering(self):
        alex = User.objects.create(username='alex')
        jacob = User.objects.create(username='jacob')
        date = now().date()
        time = now().time()
        Comment.objects.create(author=jacob, time=time, date=date)
        Comment.objects.create(author=alex, time=time, date=date)
        Comment.objects.create(author=jacob, time=time, date=date)

        class F(FilterSet):
            class Meta:
                model = Comment
                fields = ['author']

        qs = Comment.objects.all()
        f = F({'author': jacob.pk}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [1, 3], lambda o: o.pk, False)


class ModelMultipleChoiceFilterTests(TestCase):

    def setUp(self):
        alex = User.objects.create(username='alex')
        User.objects.create(username='jacob')
        aaron = User.objects.create(username='aaron')
        b1 = Book.objects.create(title="Ender's Game", price='1.00',
                                 average_rating=3.0)
        b2 = Book.objects.create(title="Rainbow Six", price='1.00',
                                 average_rating=3.0)
        b3 = Book.objects.create(title="Snowcrash", price='1.00',
                                 average_rating=3.0)
        Book.objects.create(title="Stranger in a Strage Land", price='1.00',
                            average_rating=3.0)
        alex.favorite_books = [b1, b2]
        aaron.favorite_books = [b1, b3]

    def test_filtering(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['favorite_books']

        qs = User.objects.all().order_by('username')
        f = F({'favorite_books': ['1']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron', 'alex'], lambda o: o.username)

        f = F({'favorite_books': ['1', '3']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron', 'alex'], lambda o: o.username)

        f = F({'favorite_books': ['2']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        f = F({'favorite_books': ['4']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [], lambda o: o.username)


class NumberFilterTests(TestCase):

    def setUp(self):
        Book.objects.create(title="Ender's Game", price='10.0',
                            average_rating=4.7999999999999998)
        Book.objects.create(title="Rainbow Six", price='15.0',
                            average_rating=4.5999999999999996)
        Book.objects.create(title="Snowcrash", price='20.0',
                            average_rating=4.2999999999999998)

    def test_filtering(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ['price']

        f = F({'price': 10}, queryset=Book.objects.all())
        self.assertQuerysetEqual(f.qs, ['Ender\'s Game'], lambda o: o.title)

    def test_filtering_with_single_lookup_type(self):
        class F(FilterSet):
            price = NumberFilter(lookup_type='lt')

            class Meta:
                model = Book
                fields = ['price']

        f = F({'price': 16}, queryset=Book.objects.all().order_by('title'))
        self.assertQuerysetEqual(
            f.qs, ['Ender\'s Game', 'Rainbow Six'], lambda o: o.title)

    def test_filtering_with_multiple_lookup_types(self):
        class F(FilterSet):
            price = NumberFilter(lookup_type=['lt', 'gt'])

            class Meta:
                model = Book
                fields = ['price']

        qs = Book.objects.all()
        f = F({'price_0': '15', 'price_1': 'lt'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['Ender\'s Game'], lambda o: o.title)
        f = F({'price_0': '15', 'price_1': 'lt'})
        self.assertQuerysetEqual(f.qs, ['Ender\'s Game'], lambda o: o.title)
        f = F({'price_0': '', 'price_1': 'lt'})
        self.assertQuerysetEqual(f.qs,
                                 ['Ender\'s Game', 'Rainbow Six', 'Snowcrash'],
                                 lambda o: o.title, ordered=False)

        class F(FilterSet):
            price = NumberFilter(lookup_type=['lt', 'gt', 'exact'])

            class Meta:
                model = Book
                fields = ['price']

        f = F({'price_0': '15'})
        self.assertQuerysetEqual(f.qs, ['Rainbow Six'], lambda o: o.title)


class RangeFilterTests(TestCase):

    def setUp(self):
        Book.objects.create(title="Ender's Game", price='10.0',
                            average_rating=4.7999999999999998)
        Book.objects.create(title="Rainbow Six", price='15.0',
                            average_rating=4.5999999999999996)
        Book.objects.create(title="Snowcrash", price='20.0',
                            average_rating=4.2999999999999998)

    def test_filtering(self):
        class F(FilterSet):
            price = RangeFilter()

            class Meta:
                model = Book
                fields = ['price']

        qs = Book.objects.all().order_by('title')
        f = F(queryset=qs)
        self.assertQuerysetEqual(f.qs,
                                 ['Ender\'s Game', 'Rainbow Six', 'Snowcrash'],
                                 lambda o: o.title)
        f = F({'price_0': '5', 'price_1': '15'}, queryset=qs)
        self.assertQuerysetEqual(f.qs,
                                 ['Ender\'s Game', 'Rainbow Six'],
                                 lambda o: o.title)


@unittest.skip('date-range is funky')
class DateRangeFilterTests(TestCase):

    def setUp(self):
        today = now().date()
        five_days_ago = today - datetime.timedelta(days=5)
        two_weeks_ago = today - datetime.timedelta(days=14)
        two_months_ago = today - datetime.timedelta(days=62)
        two_years_ago = today - datetime.timedelta(days=800)
        alex = User.objects.create(username='alex')
        time = now().time()
        Comment.objects.create(date=two_weeks_ago, author=alex, time=time)
        Comment.objects.create(date=two_years_ago, author=alex, time=time)
        Comment.objects.create(date=five_days_ago, author=alex, time=time)
        Comment.objects.create(date=today, author=alex, time=time)
        Comment.objects.create(date=two_months_ago, author=alex, time=time)

    def test_filtering_for_year(self):
        class F(FilterSet):
            date = DateRangeFilter()

            class Meta:
                model = Comment
                fields = ['date']

        f = F({'date': '4'})  # this year
        self.assertQuerysetEqual(f.qs, [1, 3, 4, 5], lambda o: o.pk, False)

    def test_filtering_for_month(self):
        class F(FilterSet):
            date = DateRangeFilter()

            class Meta:
                model = Comment
                fields = ['date']

        f = F({'date': '3'})  # this month
        self.assertQuerysetEqual(f.qs, [1, 3, 4], lambda o: o.pk, False)

    @unittest.expectedFailure
    def test_filtering_for_week(self):
        class F(FilterSet):
            date = DateRangeFilter()

            class Meta:
                model = Comment
                fields = ['date']

        f = F({'date': '2'})  # this week
        self.assertQuerysetEqual(f.qs, [3, 4], lambda o: o.pk, False)

    def test_filtering_for_today(self):
        class F(FilterSet):
            date = DateRangeFilter()

            class Meta:
                model = Comment
                fields = ['date']

        f = F({'date': '1'})  # today
        self.assertQuerysetEqual(f.qs, [4], lambda o: o.pk, False)

    # it will be difficult to test for TZ related issues, where "today" means
    # different things to both user and server.


class AllValuesFilterTests(TestCase):

    def test_filtering(self):
        User.objects.create(username='alex')
        User.objects.create(username='jacob')
        User.objects.create(username='aaron')

        class F(FilterSet):
            username = AllValuesFilter()

            class Meta:
                model = User
                fields = ['username']

        self.assertEqual(list(F().qs), list(User.objects.all()))
        self.assertEqual(list(F({'username': 'alex'})),
                         [User.objects.get(username='alex')])
        self.assertEqual(list(F({'username': 'jose'})),
                         list())

    def test_filtering_without_strict(self):
        User.objects.create(username='alex')
        User.objects.create(username='jacob')
        User.objects.create(username='aaron')

        class F(FilterSet):
            username = AllValuesFilter()
            strict = False

            class Meta:
                model = User
                fields = ['username']

        self.assertEqual(list(F().qs), list(User.objects.all()))
        self.assertEqual(list(F({'username': 'alex'})),
                         [User.objects.get(username='alex')])
        self.assertEqual(list(F({'username': 'jose'})),
                         list(User.objects.all()))

class O2ORelationshipTests(TestCase):

    def setUp(self):
        a1 = Account.objects.create(
            name='account1', in_good_standing=False, friendly=False)
        a2 = Account.objects.create(
            name='account2', in_good_standing=True, friendly=True)
        a3 = Account.objects.create(
            name='account3', in_good_standing=True, friendly=False)
        a4 = Account.objects.create(
            name='account4', in_good_standing=False, friendly=True)
        Profile.objects.create(account=a1, likes_coffee=True, likes_tea=False)
        Profile.objects.create(account=a2, likes_coffee=False, likes_tea=True)
        Profile.objects.create(account=a3, likes_coffee=True, likes_tea=True)
        Profile.objects.create(account=a4, likes_coffee=False, likes_tea=False)

    def test_o2o_relation(self):

        class F(FilterSet):
            class Meta:
                model = Profile
                fields = ('account',)

        f = F()
        self.assertEqual(f.qs.count(), 4)

        f = F({'account': 1})
        self.assertEqual(f.qs.count(), 1)
        self.assertQuerysetEqual(f.qs, [1], lambda o: o.pk)

    def test_reverse_o2o_relation(self):
        class F(FilterSet):
            class Meta:
                model = Account
                fields = ('profile',)

        f = F()
        self.assertEqual(f.qs.count(), 4)

        f = F({'profile': 1})
        self.assertEqual(f.qs.count(), 1)
        self.assertQuerysetEqual(f.qs, [1], lambda o: o.pk)

    def test_o2o_relation_attribute(self):
        class F(FilterSet):
            class Meta:
                model = Profile
                fields = ('account__in_good_standing',)

        f = F()
        self.assertEqual(f.qs.count(), 4)

        f = F({'account__in_good_standing': '2'})
        self.assertEqual(f.qs.count(), 2)
        self.assertQuerysetEqual(f.qs, [2, 3], lambda o: o.pk, False)

    def test_o2o_relation_attribute2(self):
        class F(FilterSet):
            class Meta:
                model = Profile
                fields = ('account__in_good_standing', 'account__friendly',)

        f = F()
        self.assertEqual(f.qs.count(), 4)

        f = F({'account__in_good_standing': '2', 'account__friendly': '2'})
        self.assertEqual(f.qs.count(), 1)
        self.assertQuerysetEqual(f.qs, [2], lambda o: o.pk)

    def test_reverse_o2o_relation_attribute(self):
        class F(FilterSet):
            class Meta:
                model = Account
                fields = ('profile__likes_coffee',)

        f = F()
        self.assertEqual(f.qs.count(), 4)

        f = F({'profile__likes_coffee': '2'})
        self.assertEqual(f.qs.count(), 2)
        self.assertQuerysetEqual(f.qs, [1, 3], lambda o: o.pk, False)

    def test_reverse_o2o_relation_attribute2(self):
        class F(FilterSet):
            class Meta:
                model = Account
                fields = ('profile__likes_coffee', 'profile__likes_tea')

        f = F()
        self.assertEqual(f.qs.count(), 4)

        f = F({'profile__likes_coffee': '2', 'profile__likes_tea': '2'})
        self.assertEqual(f.qs.count(), 1)
        self.assertQuerysetEqual(f.qs, [3], lambda o: o.pk)


class FKRelationshipTests(TestCase):

    def test_fk_relation(self):
        company1 = Company.objects.create(name='company1')
        company2 = Company.objects.create(name='company2')
        Location.objects.create(
            company=company1, open_days="some", zip_code="90210")
        Location.objects.create(
            company=company2, open_days="WEEKEND", zip_code="11111")
        Location.objects.create(
            company=company1, open_days="monday", zip_code="12345")

        class F(FilterSet):
            class Meta:
                model = Location
                fields = ('company',)

        f = F()
        self.assertEqual(f.qs.count(), 3)

        f = F({'company': 1})
        self.assertEqual(f.qs.count(), 2)
        self.assertQuerysetEqual(f.qs, [1, 3], lambda o: o.pk, False)

    def test_reverse_fk_relation(self):
        alex = User.objects.create(username='alex')
        jacob = User.objects.create(username='jacob')
        date = now().date()
        time = now().time()
        Comment.objects.create(text='comment 1',
                               author=jacob, time=time, date=date)
        Comment.objects.create(text='comment 2',
                               author=alex, time=time, date=date)
        Comment.objects.create(text='comment 3',
                               author=jacob, time=time, date=date)

        class F(FilterSet):
            class Meta:
                model = User
                fields = ['comments']

        qs = User.objects.all()
        f = F({'comments': [2]}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        class F(FilterSet):
            comments = AllValuesFilter()

            class Meta:
                model = User
                fields = ['comments']

        f = F({'comments': 2}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

    def test_fk_relation_attribute(self):
        now_dt = now()
        alex = User.objects.create(username='alex')
        jacob = User.objects.create(username='jacob')
        User.objects.create(username='aaron')

        Article.objects.create(author=alex, published=now_dt)
        Article.objects.create(author=jacob, published=now_dt)
        Article.objects.create(author=alex, published=now_dt)

        class F(FilterSet):
            class Meta:
                model = Article
                fields = ['author__username']

        self.assertEqual(list(F.base_filters), ['author__username'])
        self.assertEqual(F({'author__username': 'alex'}).qs.count(), 2)
        self.assertEqual(F({'author__username': 'jacob'}).qs.count(), 1)

        class F(FilterSet):
            author__username = AllValuesFilter()

            class Meta:
                model = Article
                fields = ['author__username']

        self.assertEqual(F({'author__username': 'alex'}).qs.count(), 2)

    def test_reverse_fk_relation_attribute(self):
        alex = User.objects.create(username='alex')
        jacob = User.objects.create(username='jacob')
        date = now().date()
        time = now().time()
        Comment.objects.create(text='comment 1',
                               author=jacob, time=time, date=date)
        Comment.objects.create(text='comment 2',
                               author=alex, time=time, date=date)
        Comment.objects.create(text='comment 3',
                               author=jacob, time=time, date=date)

        class F(FilterSet):
            class Meta:
                model = User
                fields = ['comments__text']

        qs = User.objects.all()
        f = F({'comments__text': 'comment 2'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        class F(FilterSet):
            comments__text = AllValuesFilter()

            class Meta:
                model = User
                fields = ['comments__text']

        f = F({'comments__text': 'comment 2'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

    @unittest.skip('todo - need correct models')
    def test_fk_relation_multiple_attributes(self):
        pass

    @unittest.expectedFailure
    def test_reverse_fk_relation_multiple_attributes(self):
        company = Company.objects.create(name='company')
        Location.objects.create(
            company=company, open_days="some", zip_code="90210")
        Location.objects.create(
            company=company, open_days="WEEKEND", zip_code="11111")

        class F(FilterSet):
            class Meta:
                model = Company
                fields = ('locations__zip_code', 'locations__open_days')

        f = F({'locations__zip_code': '90210',
               'locations__open_days': 'WEEKEND'})
        self.assertEqual(f.qs.count(), 0)


class M2MRelationshipTests(TestCase):

    def setUp(self):
        alex = User.objects.create(username='alex', status=1)
        User.objects.create(username='jacob', status=1)
        aaron = User.objects.create(username='aaron', status=1)
        b1 = Book.objects.create(title="Ender's Game", price='1.00',
                                 average_rating=3.0)
        b2 = Book.objects.create(title="Rainbow Six", price='2.00',
                                 average_rating=4.0)
        b3 = Book.objects.create(title="Snowcrash", price='1.00',
                                 average_rating=4.0)
        Book.objects.create(title="Stranger in a Strage Land", price='2.00',
                            average_rating=3.0)
        alex.favorite_books = [b1, b2]
        aaron.favorite_books = [b1, b3]

    def test_m2m_relation(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['favorite_books']

        qs = User.objects.all().order_by('username')
        f = F({'favorite_books': ['1']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron', 'alex'], lambda o: o.username)

        f = F({'favorite_books': ['1', '3']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron', 'alex'], lambda o: o.username)

        f = F({'favorite_books': ['2']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        f = F({'favorite_books': ['4']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [], lambda o: o.username)

    def test_reverse_m2m_relation(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ['lovers']

        qs = Book.objects.all().order_by('title')
        f = F({'lovers': [1]}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ["Ender's Game", "Rainbow Six"], lambda o: o.title)

        class F(FilterSet):
            lovers = AllValuesFilter()

            class Meta:
                model = Book
                fields = ['lovers']

        f = F({'lovers': 1}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ["Ender's Game", "Rainbow Six"], lambda o: o.title)

    def test_m2m_relation_attribute(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['favorite_books__title']

        qs = User.objects.all().order_by('username')
        f = F({'favorite_books__title': "Ender's Game"}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron', 'alex'], lambda o: o.username)

        f = F({'favorite_books__title': 'Rainbow Six'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        class F(FilterSet):
            favorite_books__title = MultipleChoiceFilter()

            class Meta:
                model = User
                fields = ['favorite_books__title']

        f = F()
        self.assertEqual(
            len(f.filters['favorite_books__title'].field.choices), 0)
        # f = F({'favorite_books__title': ['1', '3']},
        #     queryset=qs)
        # self.assertQuerysetEqual(
        #     f.qs, ['aaron', 'alex'], lambda o: o.username)

        class F(FilterSet):
            favorite_books__title = AllValuesFilter()

            class Meta:
                model = User
                fields = ['favorite_books__title']

        f = F({'favorite_books__title': "Snowcrash"}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron'], lambda o: o.username)

    def test_reverse_m2m_relation_attribute(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ['lovers__username']

        qs = Book.objects.all().order_by('title')
        f = F({'lovers__username': "alex"}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ["Ender's Game", "Rainbow Six"], lambda o: o.title)

        f = F({'lovers__username': 'jacob'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [], lambda o: o.title)

        class F(FilterSet):
            lovers__username = MultipleChoiceFilter()

            class Meta:
                model = Book
                fields = ['lovers__username']

        f = F()
        self.assertEqual(
            len(f.filters['lovers__username'].field.choices), 0)
        # f = F({'lovers__username': ['1', '3']},
        #     queryset=qs)
        # self.assertQuerysetEqual(
        #     f.qs, ["Ender's Game", "Rainbow Six"], lambda o: o.title)

        class F(FilterSet):
            lovers__username = AllValuesFilter()

            class Meta:
                model = Book
                fields = ['lovers__username']

        f = F({'lovers__username': "alex"}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ["Ender's Game", "Rainbow Six"], lambda o: o.title)

    @unittest.expectedFailure
    def test_m2m_relation_multiple_attributes(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['favorite_books__price',
                          'favorite_books__average_rating']

        qs = User.objects.all().order_by('username')
        f = F({'favorite_books__price': "1.00",
               'favorite_books__average_rating': 4.0},
              queryset=qs)
        self.assertQuerysetEqual(f.qs, ['aaron'], lambda o: o.username)

        f = F({'favorite_books__price': "3.00",
               'favorite_books__average_rating': 4.0},
              queryset=qs)
        self.assertQuerysetEqual(f.qs, [], lambda o: o.username)

    @unittest.expectedFailure
    def test_reverse_m2m_relation_multiple_attributes(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ['lovers__status', 'lovers__username']

        qs = Book.objects.all().order_by('title')
        f = F({'lovers__status': 1, 'lovers__username': "alex"}, queryset=qs)
        self.assertQuerysetEqual(
            f.qs, ["Ender's Game", "Rainbow Six"], lambda o: o.title)

        f = F({'lovers__status': 1, 'lovers__username': 'jacob'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [], lambda o: o.title)

    @unittest.skip('todo')
    def test_fk_relation_on_m2m_relation(self):
        pass

    @unittest.skip('todo')
    def test_fk_relation_attribute_on_m2m_relation(self):
        pass


class SymmetricalSelfReferentialRelationshipTests(TestCase):

    def setUp(self):
        n1 = Node.objects.create(name='one')
        n2 = Node.objects.create(name='two')
        n3 = Node.objects.create(name='three')
        n4 = Node.objects.create(name='four')
        n1.adjacents.add(n2)
        n2.adjacents.add(n3)
        n2.adjacents.add(n4)
        n4.adjacents.add(n1)

    def test_relation(self):
        class F(FilterSet):
            class Meta:
                model = Node
                fields = ['adjacents']

        qs = Node.objects.all().order_by('pk')
        f = F({'adjacents': ['1']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [2, 4], lambda o: o.pk)


class NonSymmetricalSelfReferentialRelationshipTests(TestCase):

    def setUp(self):
        n1 = DirectedNode.objects.create(name='one')
        n2 = DirectedNode.objects.create(name='two')
        n3 = DirectedNode.objects.create(name='three')
        n4 = DirectedNode.objects.create(name='four')
        n1.outbound_nodes.add(n2)
        n2.outbound_nodes.add(n3)
        n2.outbound_nodes.add(n4)
        n4.outbound_nodes.add(n1)

    def test_forward_relation(self):
        class F(FilterSet):
            class Meta:
                model = DirectedNode
                fields = ['outbound_nodes']

        qs = DirectedNode.objects.all().order_by('pk')
        f = F({'outbound_nodes': ['1']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [4], lambda o: o.pk)

    def test_reverse_relation(self):
        class F(FilterSet):
            class Meta:
                model = DirectedNode
                fields = ['inbound_nodes']

        qs = DirectedNode.objects.all().order_by('pk')
        f = F({'inbound_nodes': ['1']}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [2], lambda o: o.pk)


class MiscFilterSetTests(TestCase):

    def setUp(self):
        User.objects.create(username='alex', status=1)
        User.objects.create(username='jacob', status=2)
        User.objects.create(username='aaron', status=2)
        User.objects.create(username='carl', status=0)

    def test_filtering_with_declared_filters(self):
        class F(FilterSet):
            account = CharFilter(name='username')

            class Meta:
                model = User
                fields = ['account']

        qs = mock.MagicMock()
        f = F({'account': 'jdoe'}, queryset=qs)
        result = f.qs
        self.assertNotEqual(qs, result)
        qs.all.return_value.filter.assert_called_with(username__exact='jdoe')

    def test_filtering_with_multiple_filters(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['status', 'username']

        qs = User.objects.all()

        f = F({'username': 'alex', 'status': '1'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        f = F({'username': 'alex', 'status': '2'}, queryset=qs)
        self.assertQuerysetEqual(f.qs, [], lambda o: o.pk)

    def test_filter_with_action(self):
        class F(FilterSet):
            username = CharFilter(action=lambda qs, value: (
                qs.filter(**{'username__startswith': value})))

            class Meta:
                model = User
                fields = ['username']

        f = F({'username': 'a'}, queryset=User.objects.all())
        self.assertQuerysetEqual(
            f.qs, ['alex', 'aaron'], lambda o: o.username, False)

    def test_filter_with_initial(self):
        class F(FilterSet):
            status = ChoiceFilter(choices=STATUS_CHOICES, initial=1)

            class Meta:
                model = User
                fields = ['status']

        qs = User.objects.all()
        f = F(queryset=qs)
        self.assertQuerysetEqual(f.qs, ['alex'], lambda o: o.username)

        f = F({'status': 0}, queryset=qs)
        self.assertQuerysetEqual(f.qs, ['carl'], lambda o: o.username)

    def test_qs_count(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['status']

        qs = User.objects.all()
        f = F(queryset=qs)
        self.assertEqual(len(f.qs), 4)
        self.assertEqual(f.count(), 4)

        f = F({'status': '0'}, queryset=qs)
        self.assertEqual(len(f.qs), 1)
        self.assertEqual(f.count(), 1)

        f = F({'status': '1'}, queryset=qs)
        self.assertEqual(len(f.qs), 1)
        self.assertEqual(f.count(), 1)

        f = F({'status': '2'}, queryset=qs)
        self.assertEqual(len(f.qs), 2)
        self.assertEqual(f.count(), 2)


########NEW FILE########
__FILENAME__ = test_filters
from __future__ import absolute_import
from __future__ import unicode_literals

import mock

from django import forms
from django.utils import unittest
from django.test import TestCase

from django_filters.fields import Lookup
from django_filters.fields import RangeField
from django_filters.fields import LookupTypeField
from django_filters.filters import Filter
from django_filters.filters import CharFilter
from django_filters.filters import BooleanFilter
from django_filters.filters import ChoiceFilter
from django_filters.filters import MultipleChoiceFilter
from django_filters.filters import DateFilter
from django_filters.filters import DateTimeFilter
from django_filters.filters import TimeFilter
from django_filters.filters import ModelChoiceFilter
from django_filters.filters import ModelMultipleChoiceFilter
from django_filters.filters import NumberFilter
from django_filters.filters import RangeFilter
from django_filters.filters import DateRangeFilter
from django_filters.filters import AllValuesFilter
from django_filters.filters import LOOKUP_TYPES


class FilterTests(TestCase):

    def test_creation(self):
        f = Filter()
        self.assertEqual(f.lookup_type, 'exact')
        self.assertEqual(f.exclude, False)

    def test_creation_order(self):
        f = Filter()
        f2 = Filter()
        self.assertTrue(f2.creation_counter > f.creation_counter)

    def test_default_field(self):
        f = Filter()
        field = f.field
        self.assertIsInstance(field, forms.Field)
        self.assertEqual(field.help_text, '')

    def test_field_with_exclusion(self):
        f = Filter(exclude=True)
        field = f.field
        self.assertIsInstance(field, forms.Field)
        self.assertEqual(field.help_text, 'This is an exclusion filter')

    def test_field_with_single_lookup_type(self):
        f = Filter(lookup_type='iexact')
        field = f.field
        self.assertIsInstance(field, forms.Field)

    def test_field_with_none_lookup_type(self):
        f = Filter(lookup_type=None)
        field = f.field
        self.assertIsInstance(field, LookupTypeField)
        choice_field = field.fields[1]
        self.assertEqual(len(choice_field.choices), len(LOOKUP_TYPES))

    def test_field_with_lookup_type_and_exlusion(self):
        f = Filter(lookup_type=None, exclude=True)
        field = f.field
        self.assertIsInstance(field, LookupTypeField)
        self.assertEqual(field.help_text, 'This is an exclusion filter')

    def test_field_with_list_lookup_type(self):
        f = Filter(lookup_type=('istartswith', 'iendswith'))
        field = f.field
        self.assertIsInstance(field, LookupTypeField)
        choice_field = field.fields[1]
        self.assertEqual(len(choice_field.choices), 2)

    def test_field_params(self):
        with mock.patch.object(Filter, 'field_class',
                spec=['__call__']) as mocked:
            f = Filter(name='somefield', label='somelabel',
                widget='somewidget')
            f.field
            mocked.assert_called_once_with(required=False,
                label='somelabel', widget='somewidget', help_text=mock.ANY)

    def test_field_extra_params(self):
        with mock.patch.object(Filter, 'field_class',
                spec=['__call__']) as mocked:
            f = Filter(someattr='someattr')
            f.field
            mocked.assert_called_once_with(required=mock.ANY,
                label=mock.ANY, widget=mock.ANY, help_text=mock.ANY,
                someattr='someattr')

    def test_field_with_required_filter(self):
        with mock.patch.object(Filter, 'field_class',
                spec=['__call__']) as mocked:
            f = Filter(required=True)
            f.field
            mocked.assert_called_once_with(required=True,
                label=mock.ANY, widget=mock.ANY, help_text=mock.ANY)

    def test_filtering(self):
        qs = mock.Mock(spec=['filter'])
        f = Filter()
        result = f.filter(qs, 'value')
        qs.filter.assert_called_once_with(None__exact='value')
        self.assertNotEqual(qs, result)

    def test_filtering_exclude(self):
        qs = mock.Mock(spec=['filter', 'exclude'])
        f = Filter(exclude=True)
        result = f.filter(qs, 'value')
        qs.exclude.assert_called_once_with(None__exact='value')
        self.assertNotEqual(qs, result)

    def test_filtering_uses_name(self):
        qs = mock.Mock(spec=['filter'])
        f = Filter(name='somefield')
        f.filter(qs, 'value')
        result = qs.filter.assert_called_once_with(somefield__exact='value')
        self.assertNotEqual(qs, result)

    def test_filtering_skipped_with_blank_value(self):
        qs = mock.Mock()
        f = Filter()
        result = f.filter(qs, '')
        self.assertListEqual(qs.method_calls, [])
        self.assertEqual(qs, result)

    def test_filtering_skipped_with_none_value(self):
        qs = mock.Mock()
        f = Filter()
        result = f.filter(qs, None)
        self.assertListEqual(qs.method_calls, [])
        self.assertEqual(qs, result)

    def test_filtering_with_list_value(self):
        qs = mock.Mock(spec=['filter'])
        f = Filter(name='somefield', lookup_type=['some_lookup_type'])
        result = f.filter(qs, Lookup('value', 'some_lookup_type'))
        qs.filter.assert_called_once_with(somefield__some_lookup_type='value')
        self.assertNotEqual(qs, result)

    def test_filtering_skipped_with_list_value_with_blank(self):
        qs = mock.Mock()
        f = Filter(name='somefield', lookup_type=['some_lookup_type'])
        result = f.filter(qs, Lookup('', 'some_lookup_type'))
        self.assertListEqual(qs.method_calls, [])
        self.assertEqual(qs, result)

    def test_filtering_skipped_with_list_value_with_blank_lookup(self):
        return # Now field is required to provide valid lookup_type if it provides any
        qs = mock.Mock(spec=['filter'])
        f = Filter(name='somefield', lookup_type=None)
        result = f.filter(qs, Lookup('value', ''))
        qs.filter.assert_called_once_with(somefield__exact='value')
        self.assertNotEqual(qs, result)

    def test_filter_using_action(self):
        qs = mock.NonCallableMock(spec=[])
        action = mock.Mock(spec=['filter'])
        f = Filter(action=action)
        result = f.filter(qs, 'value')
        action.assert_called_once_with(qs, 'value')
        self.assertNotEqual(qs, result)

    def test_filtering_uses_distinct(self):
        qs = mock.Mock(spec=['filter', 'distinct'])
        f = Filter(name='somefield', distinct=True)
        f.filter(qs, 'value')
        result = qs.distinct.assert_called_once()
        self.assertNotEqual(qs, result)


class CharFilterTests(TestCase):

    def test_default_field(self):
        f = CharFilter()
        field = f.field
        self.assertIsInstance(field, forms.CharField)


class BooleanFilterTests(TestCase):

    def test_default_field(self):
        f = BooleanFilter()
        field = f.field
        self.assertIsInstance(field, forms.NullBooleanField)

    def test_filtering(self):
        qs = mock.Mock(spec=['filter'])
        f = BooleanFilter(name='somefield')
        result = f.filter(qs, True)
        qs.filter.assert_called_once_with(somefield=True)
        self.assertNotEqual(qs, result)

    @unittest.expectedFailure
    def test_filtering_skipped_with_blank_value(self):
        qs = mock.Mock()
        f = BooleanFilter(name='somefield')
        result = f.filter(qs, '')
        self.assertListEqual(qs.method_calls, [])
        self.assertEqual(qs, result)

    def test_filtering_skipped_with_none_value(self):
        qs = mock.Mock()
        f = BooleanFilter(name='somefield')
        result = f.filter(qs, None)
        self.assertListEqual(qs.method_calls, [])
        self.assertEqual(qs, result)


class ChoiceFilterTests(TestCase):

    def test_default_field(self):
        f = ChoiceFilter()
        field = f.field
        self.assertIsInstance(field, forms.ChoiceField)


class MultipleChoiceFilterTests(TestCase):

    def test_default_field(self):
        f = MultipleChoiceFilter()
        field = f.field
        self.assertIsInstance(field, forms.MultipleChoiceField)

    def test_filtering_requires_name(self):
        qs = mock.Mock(spec=['filter'])
        f = MultipleChoiceFilter()
        with self.assertRaises(TypeError):
            f.filter(qs, ['value'])

    def test_filtering(self):
        qs = mock.Mock(spec=['filter'])
        f = MultipleChoiceFilter(name='somefield')
        with mock.patch('django_filters.filters.Q') as mockQclass:
            mockQ1, mockQ2 = mock.MagicMock(), mock.MagicMock()
            mockQclass.side_effect = [mockQ1, mockQ2]

            f.filter(qs, ['value'])

            self.assertEqual(mockQclass.call_args_list,
                             [mock.call(), mock.call(somefield='value')])
            mockQ1.__ior__.assert_called_once_with(mockQ2)
            qs.filter.assert_called_once_with(mockQ1.__ior__.return_value)
            qs.filter.return_value.distinct.assert_called_once_with()

    def test_filtering_skipped_when_len_of_value_is_len_of_field_choices(self):
        qs = mock.Mock(spec=[])
        f = MultipleChoiceFilter(name='somefield')
        result = f.filter(qs, [])
        self.assertEqual(len(f.field.choices), 0)
        self.assertEqual(qs, result)

        f.field.choices = ['some', 'values', 'here']
        result = f.filter(qs, ['some', 'values', 'here'])
        self.assertEqual(qs, result)

        result = f.filter(qs, ['other', 'values', 'there'])
        self.assertEqual(qs, result)

    @unittest.expectedFailure
    def test_filtering_skipped_with_empty_list_value_and_some_choices(self):
        qs = mock.Mock(spec=[])
        f = MultipleChoiceFilter(name='somefield')
        f.field.choices = ['some', 'values', 'here']
        result = f.filter(qs, [])
        self.assertEqual(qs, result)


class DateFilterTests(TestCase):

    def test_default_field(self):
        f = DateFilter()
        field = f.field
        self.assertIsInstance(field, forms.DateField)


class DateTimeFilterTests(TestCase):

    def test_default_field(self):
        f = DateTimeFilter()
        field = f.field
        self.assertIsInstance(field, forms.DateTimeField)


class TimeFilterTests(TestCase):

    def test_default_field(self):
        f = TimeFilter()
        field = f.field
        self.assertIsInstance(field, forms.TimeField)


class ModelChoiceFilterTests(TestCase):

    def test_default_field_without_queryset(self):
        f = ModelChoiceFilter()
        with self.assertRaises(TypeError):
            f.field

    def test_default_field_with_queryset(self):
        qs = mock.NonCallableMock(spec=[])
        f = ModelChoiceFilter(queryset=qs)
        field = f.field
        self.assertIsInstance(field, forms.ModelChoiceField)
        self.assertEqual(field.queryset, qs)


class ModelMultipleChoiceFilterTests(TestCase):

    def test_default_field_without_queryset(self):
        f = ModelMultipleChoiceFilter()
        with self.assertRaises(TypeError):
            f.field

    def test_default_field_with_queryset(self):
        qs = mock.NonCallableMock(spec=[])
        f = ModelMultipleChoiceFilter(queryset=qs)
        field = f.field
        self.assertIsInstance(field, forms.ModelMultipleChoiceField)
        self.assertEqual(field.queryset, qs)


class NumberFilterTests(TestCase):

    def test_default_field(self):
        f = NumberFilter()
        field = f.field
        self.assertIsInstance(field, forms.DecimalField)

    def test_filtering(self):
        qs = mock.Mock(spec=['filter'])
        f = NumberFilter()
        f.filter(qs, 1)
        qs.filter.assert_called_once_with(None__exact=1)
        # Also test 0 as it once had a bug
        qs.reset_mock()
        f.filter(qs, 0)
        qs.filter.assert_called_once_with(None__exact=0)


class RangeFilterTests(TestCase):

    def test_default_field(self):
        f = RangeFilter()
        field = f.field
        self.assertIsInstance(field, RangeField)

    def test_filtering(self):
        qs = mock.Mock(spec=['filter'])
        value = mock.Mock(start=20, stop=30)
        f = RangeFilter()
        f.filter(qs, value)
        qs.filter.assert_called_once_with(None__range=(20, 30))

    def test_filtering_skipped_with_none_value(self):
        qs = mock.Mock(spec=['filter'])
        f = RangeFilter()
        result = f.filter(qs, None)
        self.assertEqual(qs, result)

    def test_filtering_ignores_lookup_type(self):
        qs = mock.Mock()
        value = mock.Mock(start=20, stop=30)
        f = RangeFilter(lookup_type='gte')
        f.filter(qs, value)
        qs.filter.assert_called_once_with(None__range=(20, 30))


class DateRangeFilterTests(TestCase):

    def test_creating(self):
        f = DateRangeFilter()
        self.assertIn('choices', f.extra)
        self.assertEqual(len(DateRangeFilter.options), len(f.extra['choices']))

    def test_default_field(self):
        f = DateRangeFilter()
        field = f.field
        self.assertIsInstance(field, forms.ChoiceField)

    def test_filtering(self):
        qs = mock.Mock(spec=['all'])
        f = DateRangeFilter()
        f.filter(qs, '')
        qs.all.assert_called_once_with()

    # the correct behavior fails right now
    @unittest.expectedFailure
    def test_filtering_skipped_with_blank_value(self):
        qs = mock.Mock(spec=[])
        f = DateRangeFilter()
        result = f.filter(qs, '')
        self.assertEqual(qs, result)

    @unittest.expectedFailure
    def test_filtering_skipped_with_out_of_range_value(self):
        qs = mock.Mock(spec=[])
        f = DateRangeFilter()
        result = f.filter(qs, 999)
        self.assertEqual(qs, result)

    def test_filtering_for_this_year(self):
        qs = mock.Mock(spec=['filter'])
        with mock.patch('django_filters.filters.now') as mock_now:
            now_dt = mock_now.return_value
            f = DateRangeFilter()
            f.filter(qs, '4')
            qs.filter.assert_called_once_with(
                None__year=now_dt.year)

    def test_filtering_for_this_month(self):
        qs = mock.Mock(spec=['filter'])
        with mock.patch('django_filters.filters.now') as mock_now:
            now_dt = mock_now.return_value
            f = DateRangeFilter()
            f.filter(qs, '3')
            qs.filter.assert_called_once_with(
                None__year=now_dt.year, None__month=now_dt.month)

    def test_filtering_for_7_days(self):
        qs = mock.Mock(spec=['filter'])
        with mock.patch('django_filters.filters.now'):
            with mock.patch('django_filters.filters.timedelta') as mock_td:
                with mock.patch(
                        'django_filters.filters._truncate') as mock_truncate:
                    mock_dt1, mock_dt2 = mock.MagicMock(), mock.MagicMock()
                    mock_truncate.side_effect = [mock_dt1, mock_dt2]
                    f = DateRangeFilter()
                    f.filter(qs, '2')
                    self.assertEqual(mock_td.call_args_list,
                        [mock.call(days=7), mock.call(days=1)])
                    qs.filter.assert_called_once_with(
                        None__lt=mock_dt2, None__gte=mock_dt1)

    def test_filtering_for_today(self):
        qs = mock.Mock(spec=['filter'])
        with mock.patch('django_filters.filters.now') as mock_now:
            now_dt = mock_now.return_value
            f = DateRangeFilter()
            f.filter(qs, '1')
            qs.filter.assert_called_once_with(
                None__year=now_dt.year,
                None__month=now_dt.month,
                None__day=now_dt.day)


class AllValuesFilterTests(TestCase):

    def test_default_field_without_assigning_model(self):
        f = AllValuesFilter()
        with self.assertRaises(AttributeError):
            f.field

    def test_default_field_with_assigning_model(self):
        mocked = mock.Mock()
        chained_call = '.'.join(['_default_manager', 'distinct.return_value',
            'order_by.return_value', 'values_list.return_value'])
        mocked.configure_mock(**{chained_call: iter([])})
        f = AllValuesFilter()
        f.model = mocked
        field = f.field
        self.assertIsInstance(field, forms.ChoiceField)

########NEW FILE########
__FILENAME__ = test_filterset
from __future__ import absolute_import, unicode_literals

import mock

from django.db import models
from django.utils import unittest
from django.test import TestCase

from django_filters.filterset import FilterSet
from django_filters.filterset import FILTER_FOR_DBFIELD_DEFAULTS
from django_filters.filterset import get_model_field
from django_filters.filters import CharFilter
from django_filters.filters import NumberFilter
from django_filters.filters import ChoiceFilter
from django_filters.filters import ModelChoiceFilter
from django_filters.filters import ModelMultipleChoiceFilter

from .models import User
from .models import AdminUser
from .models import Book
from .models import Profile
from .models import Comment
from .models import Restaurant
from .models import NetworkSetting
from .models import SubnetMaskField
from .models import Account
from .models import BankAccount
from .models import Node
from .models import DirectedNode
from .models import Worker
from .models import Business


class HelperMethodsTests(TestCase):

    @unittest.skip('todo')
    def test_get_declared_filters(self):
        pass

    def test_get_model_field(self):
        result = get_model_field(User, 'unknown__name')
        self.assertIsNone(result)

    @unittest.skip('todo')
    def test_filters_for_model(self):
        pass

    @unittest.skip('todo')
    def test_filterset_factory(self):
        pass


class DbFieldDefaultFiltersTests(TestCase):

    def test_expected_db_fields_get_filters(self):
        to_check = [
            models.BooleanField,
            models.CharField,
            models.CommaSeparatedIntegerField,
            models.DateField,
            models.DateTimeField,
            models.DecimalField,
            models.EmailField,
            models.FilePathField,
            models.FloatField,
            models.IntegerField,
            models.IPAddressField,
            models.NullBooleanField,
            models.PositiveIntegerField,
            models.PositiveSmallIntegerField,
            models.SlugField,
            models.SmallIntegerField,
            models.TextField,
            models.TimeField,
            models.URLField,
            models.ForeignKey,
            models.OneToOneField,
            models.ManyToManyField,
        ]
        msg = "%s expected to be found in FILTER_FOR_DBFIELD_DEFAULTS"

        for m in to_check:
            self.assertIn(m, FILTER_FOR_DBFIELD_DEFAULTS, msg % m.__name__)

    def test_expected_db_fields_do_not_get_filters(self):
        to_check = [
            models.Field,
            models.BigIntegerField,
            models.GenericIPAddressField,
            models.FileField,
            models.ImageField,
        ]
        msg = "%s expected to not be found in FILTER_FOR_DBFIELD_DEFAULTS"

        for m in to_check:
            self.assertNotIn(m, FILTER_FOR_DBFIELD_DEFAULTS, msg % m.__name__)


class FilterSetFilterForFieldTests(TestCase):

    def test_filter_found_for_field(self):
        f = User._meta.get_field('username')
        result = FilterSet.filter_for_field(f, 'username')
        self.assertIsInstance(result, CharFilter)
        self.assertEqual(result.name, 'username')

    def test_filter_found_for_autofield(self):
        f = User._meta.get_field('id')
        result = FilterSet.filter_for_field(f, 'id')
        self.assertIsInstance(result, NumberFilter)
        self.assertEqual(result.name, 'id')

    def test_field_with_extras(self):
        f = User._meta.get_field('favorite_books')
        result = FilterSet.filter_for_field(f, 'favorite_books')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'favorite_books')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, Book)

    def test_field_with_choices(self):
        f = User._meta.get_field('status')
        result = FilterSet.filter_for_field(f, 'status')
        self.assertIsInstance(result, ChoiceFilter)
        self.assertEqual(result.name, 'status')
        self.assertTrue('choices' in result.extra)
        self.assertIsNotNone(result.extra['choices'])

    def test_field_that_is_subclassed(self):
        f = User._meta.get_field('first_name')
        result = FilterSet.filter_for_field(f, 'first_name')
        self.assertIsInstance(result, CharFilter)

    def test_symmetrical_selfref_m2m_field(self):
        f = Node._meta.get_field('adjacents')
        result = FilterSet.filter_for_field(f, 'adjacents')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'adjacents')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, Node)

    def test_non_symmetrical_selfref_m2m_field(self):
        f = DirectedNode._meta.get_field('outbound_nodes')
        result = FilterSet.filter_for_field(f, 'outbound_nodes')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'outbound_nodes')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, DirectedNode)

    def test_m2m_field_with_through_model(self):
        f = Business._meta.get_field('employees')
        result = FilterSet.filter_for_field(f, 'employees')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'employees')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, Worker)

    @unittest.skip('todo')
    def test_filter_overrides(self):
        pass


class FilterSetFilterForReverseFieldTests(TestCase):

    def test_reverse_o2o_relationship(self):
        f = Account._meta.get_field_by_name('profile')[0]
        result = FilterSet.filter_for_reverse_field(f, 'profile')
        self.assertIsInstance(result, ModelChoiceFilter)
        self.assertEqual(result.name, 'profile')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, Profile)

    def test_reverse_fk_relationship(self):
        f = User._meta.get_field_by_name('comments')[0]
        result = FilterSet.filter_for_reverse_field(f, 'comments')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'comments')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, Comment)

    def test_reverse_m2m_relationship(self):
        f = Book._meta.get_field_by_name('lovers')[0]
        result = FilterSet.filter_for_reverse_field(f, 'lovers')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'lovers')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, User)

    def test_reverse_non_symmetrical_selfref_m2m_field(self):
        f = DirectedNode._meta.get_field_by_name('inbound_nodes')[0]
        result = FilterSet.filter_for_reverse_field(f, 'inbound_nodes')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'inbound_nodes')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, DirectedNode)

    def test_reverse_m2m_field_with_through_model(self):
        f = Worker._meta.get_field_by_name('employers')[0]
        result = FilterSet.filter_for_reverse_field(f, 'employers')
        self.assertIsInstance(result, ModelMultipleChoiceFilter)
        self.assertEqual(result.name, 'employers')
        self.assertTrue('queryset' in result.extra)
        self.assertIsNotNone(result.extra['queryset'])
        self.assertEqual(result.extra['queryset'].model, Business)


class FilterSetClassCreationTests(TestCase):

    def test_no_filters(self):
        class F(FilterSet):
            pass

        self.assertEqual(len(F.declared_filters), 0)
        self.assertEqual(len(F.base_filters), 0)

    def test_declaring_filter(self):
        class F(FilterSet):
            username = CharFilter()

        self.assertEqual(len(F.declared_filters), 1)
        self.assertListEqual(list(F.declared_filters), ['username'])
        self.assertEqual(len(F.base_filters), 1)
        self.assertListEqual(list(F.base_filters), ['username'])

    def test_model_derived(self):
        class F(FilterSet):
            class Meta:
                model = Book

        self.assertEqual(len(F.declared_filters), 0)
        self.assertEqual(len(F.base_filters), 3)
        self.assertListEqual(list(F.base_filters),
                             ['title', 'price', 'average_rating'])

    def test_declared_and_model_derived(self):
        class F(FilterSet):
            username = CharFilter()

            class Meta:
                model = Book

        self.assertEqual(len(F.declared_filters), 1)
        self.assertEqual(len(F.base_filters), 4)
        self.assertListEqual(list(F.base_filters),
                             ['title', 'price', 'average_rating', 'username'])

    def test_meta_fields_with_declared_and_model_derived(self):
        class F(FilterSet):
            username = CharFilter()

            class Meta:
                model = Book
                fields = ('username', 'price')

        self.assertEqual(len(F.declared_filters), 1)
        self.assertEqual(len(F.base_filters), 2)
        self.assertListEqual(list(F.base_filters), ['username', 'price'])

    def test_meta_fields_containing_autofield(self):
        class F(FilterSet):
            username = CharFilter()

            class Meta:
                model = Book
                fields = ('id', 'username', 'price')

        self.assertEqual(len(F.declared_filters), 1)
        self.assertEqual(len(F.base_filters), 3)
        self.assertListEqual(list(F.base_filters), ['id', 'username', 'price'])

    def test_meta_fields_containing_unknown(self):
        with self.assertRaises(TypeError):
            class F(FilterSet):
                username = CharFilter()

                class Meta:
                    model = Book
                    fields = ('username', 'price', 'other')

    def test_meta_exlude_with_declared_and_declared_wins(self):
        class F(FilterSet):
            username = CharFilter()

            class Meta:
                model = Book
                exclude = ('username', 'price')

        self.assertEqual(len(F.declared_filters), 1)
        self.assertEqual(len(F.base_filters), 3)
        self.assertListEqual(list(F.base_filters),
                             ['title', 'average_rating', 'username'])

    def test_meta_fields_and_exlude_and_exclude_wins(self):
        class F(FilterSet):
            username = CharFilter()

            class Meta:
                model = Book
                fields = ('username', 'title', 'price')
                exclude = ('title',)

        self.assertEqual(len(F.declared_filters), 1)
        self.assertEqual(len(F.base_filters), 2)
        self.assertListEqual(list(F.base_filters),
                             ['username', 'price'])

    def test_filterset_class_inheritance(self):
        class F(FilterSet):
            class Meta:
                model = Book

        class G(F):
            pass
        self.assertEqual(set(F.base_filters), set(G.base_filters))

        class F(FilterSet):
            other = CharFilter

            class Meta:
                model = Book

        class G(F):
            pass
        self.assertEqual(set(F.base_filters), set(G.base_filters))

    def test_abstract_model_inheritance(self):
        class F(FilterSet):
            class Meta:
                model = Restaurant

        self.assertEqual(set(F.base_filters), set(['name', 'serves_pizza']))

        class F(FilterSet):
            class Meta:
                model = Restaurant
                fields = ['name', 'serves_pizza']

        self.assertEqual(set(F.base_filters), set(['name', 'serves_pizza']))

    def test_custom_field_ignored(self):
        class F(FilterSet):
            class Meta:
                model = NetworkSetting

        self.assertEqual(list(F.base_filters.keys()), ['ip'])

    def test_custom_field_gets_filter_from_override(self):
        class F(FilterSet):
            filter_overrides = {
                SubnetMaskField: {'filter_class': CharFilter}}

            class Meta:
                model = NetworkSetting

        self.assertEqual(list(F.base_filters.keys()), ['ip', 'mask'])

    def test_filterset_for_proxy_model(self):
        class F(FilterSet):
            class Meta:
                model = User

        class ProxyF(FilterSet):
            class Meta:
                model = AdminUser

        self.assertEqual(list(F.base_filters), list(ProxyF.base_filters))

    @unittest.expectedFailure
    def test_filterset_for_mti_model(self):
        class F(FilterSet):
            class Meta:
                model = Account

        class FtiF(FilterSet):
            class Meta:
                model = BankAccount

        # fails due to 'account_ptr' getting picked up
        self.assertEqual(
            list(F.base_filters) + ['amount_saved'],
            list(FtiF.base_filters))


class FilterSetInstantiationTests(TestCase):

    def test_creating_instance(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username']

        f = F()
        self.assertFalse(f.is_bound)
        self.assertIsNotNone(f.queryset)
        self.assertEqual(len(f.filters), len(F.base_filters))
        for name, filter_ in f.filters.items():
            self.assertEqual(
                filter_.model,
                User,
                "%s does not have model set correctly" % name)

    def test_creating_bound_instance(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username']

        f = F({'username': 'username'})
        self.assertTrue(f.is_bound)

    def test_creating_with_queryset(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username']

        m = mock.Mock()
        f = F(queryset=m)
        self.assertEqual(f.queryset, m)


class FilterSetOrderingTests(TestCase):

    def setUp(self):
        self.alex = User.objects.create(username='alex', status=1)
        self.jacob = User.objects.create(username='jacob', status=2)
        self.aaron = User.objects.create(username='aaron', status=2)
        self.carl = User.objects.create(username='carl', status=0)
        # user_ids = list(User.objects.all().values_list('pk', flat=True))
        self.qs = User.objects.all().order_by('id')

    def test_ordering_when_unbound(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status']

        f = F(queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['carl', 'alex', 'jacob', 'aaron'], lambda o: o.username)

    def test_ordering(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['username', 'status']

        f = F({'o': 'username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['aaron', 'alex', 'carl', 'jacob'], lambda o: o.username)

        f = F({'o': 'status'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['carl', 'alex', 'jacob', 'aaron'], lambda o: o.username)

    def test_ordering_on_unknown_value(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status']

        f = F({'o': 'username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, [], lambda o: o.username)

    def test_ordering_on_unknown_value_results_in_default_ordering_without_strict(self):
        class F(FilterSet):
            strict = False

            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status']

        f = F({'o': 'username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['alex', 'jacob', 'aaron', 'carl'], lambda o: o.username)

    def test_ordering_on_different_field(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = True

        f = F({'o': 'username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['aaron', 'alex', 'carl', 'jacob'], lambda o: o.username)

        f = F({'o': 'status'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['carl', 'alex', 'jacob', 'aaron'], lambda o: o.username)

    @unittest.skip('todo')
    def test_ordering_uses_filter_name(self):
        class F(FilterSet):
            account = CharFilter(name='username')

            class Meta:
                model = User
                fields = ['account', 'status']
                order_by = True

        f = F({'o': 'username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['aaron', 'alex', 'carl', 'jacob'], lambda o: o.username)

    def test_ordering_with_overridden_field_name(self):
        """
        Set the `order_by_field` on the queryset and ensure that the
        field name is respected.
        """
        class F(FilterSet):
            order_by_field = 'order'

            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status']

        f = F({'order': 'status'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['carl', 'alex', 'jacob', 'aaron'], lambda o: o.username)

    def test_ordering_descending_set(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['username', '-username']

        f = F({'o': '-username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['jacob', 'carl', 'alex', 'aaron'], lambda o: o.username)

    def test_ordering_descending_unset(self):
        """ Test ordering descending works when order_by=True. """
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = True

        f = F({'o': '-username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['jacob', 'carl', 'alex', 'aaron'], lambda o: o.username)

    def test_custom_ordering(self):

        class F(FilterSet):
            debug = True
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['username', 'status']

            def get_order_by(self, order_choice):
                if order_choice == 'status':
                    return ['status', 'username']
                return super(F, self).get_order_by(order_choice)

        f = F({'o': 'username'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['aaron', 'alex', 'carl', 'jacob'], lambda o: o.username)

        f = F({'o': 'status'}, queryset=self.qs)
        self.assertQuerysetEqual(
            f.qs, ['carl', 'alex', 'aaron', 'jacob'], lambda o: o.username)

########NEW FILE########
__FILENAME__ = test_forms
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.test import TestCase

from django_filters.filterset import FilterSet
from django_filters.filters import CharFilter
from django_filters.filters import ChoiceFilter

from .models import User
from .models import Book
from .models import STATUS_CHOICES


class FilterSetFormTests(TestCase):

    def test_form_from_empty_filterset(self):
        class F(FilterSet):
            pass

        f = F(queryset=Book.objects.all()).form
        self.assertIsInstance(f, forms.Form)

    def test_form(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ('title',)

        f = F().form
        self.assertIsInstance(f, forms.Form)
        self.assertEqual(list(f.fields), ['title'])

    def test_custom_form(self):
        class MyForm(forms.Form):
            pass

        class F(FilterSet):
            class Meta:
                model = Book
                form = MyForm

        f = F().form
        self.assertIsInstance(f, MyForm)

    def test_form_prefix(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ('title',)

        f = F().form
        self.assertIsNone(f.prefix)

        f = F(prefix='prefix').form
        self.assertEqual(f.prefix, 'prefix')

    def test_form_fields(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['status']

        f = F().form
        self.assertEqual(len(f.fields), 1)
        self.assertIn('status', f.fields)
        self.assertEqual(sorted(f.fields['status'].choices),
                         sorted(STATUS_CHOICES))

    def test_form_fields_exclusion(self):
        class F(FilterSet):
            title = CharFilter(exclude=True)

            class Meta:
                model = Book
                fields = ('title',)

        f = F().form
        self.assertEqual(f.fields['title'].help_text, "This is an exclusion filter")

    def test_form_fields_using_widget(self):
        class F(FilterSet):
            status = ChoiceFilter(widget=forms.RadioSelect,
                                  choices=STATUS_CHOICES)

            class Meta:
                model = User
                fields = ['status', 'username']

        f = F().form
        self.assertEqual(len(f.fields), 2)
        self.assertIn('status', f.fields)
        self.assertIn('username', f.fields)
        self.assertEqual(sorted(f.fields['status'].choices),
                         sorted(STATUS_CHOICES))
        self.assertIsInstance(f.fields['status'].widget, forms.RadioSelect)

    def test_form_field_with_custom_label(self):
        class F(FilterSet):
            title = CharFilter(label="Book title")

            class Meta:
                model = Book
                fields = ('title',)

        f = F().form
        self.assertEqual(f.fields['title'].label, "Book title")
        self.assertEqual(f['title'].label, 'Book title')

    def test_form_field_with_manual_name(self):
        class F(FilterSet):
            book_title = CharFilter(name='title')

            class Meta:
                model = Book
                fields = ('book_title',)

        f = F().form
        self.assertEqual(f.fields['book_title'].label, None)
        self.assertEqual(f['book_title'].label, 'Book title')

    def test_form_field_with_manual_name_and_label(self):
        class F(FilterSet):
            f1 = CharFilter(name='title', label="Book title")

            class Meta:
                model = Book
                fields = ('f1',)

        f = F().form
        self.assertEqual(f.fields['f1'].label, "Book title")
        self.assertEqual(f['f1'].label, 'Book title')

    def test_filter_with_initial(self):
        class F(FilterSet):
            status = ChoiceFilter(choices=STATUS_CHOICES, initial=1)

            class Meta:
                model = User
                fields = ['status']

        f = F().form
        self.assertEqual(f.fields['status'].initial, 1)

    def test_form_is_not_bound(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ('title',)

        f = F().form
        self.assertFalse(f.is_bound)
        self.assertEqual(f.data, {})

    def test_form_is_bound(self):
        class F(FilterSet):
            class Meta:
                model = Book
                fields = ('title',)

        f = F({'title': 'Some book'}).form
        self.assertTrue(f.is_bound)
        self.assertEqual(f.data, {'title': 'Some book'})

    def test_ordering(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status']

        f = F().form
        self.assertEqual(len(f.fields), 3)
        self.assertIn('o', f.fields)
        self.assertEqual(f.fields['o'].choices, [('status', 'Status')])

    def test_ordering_uses_all_fields(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = True

        f = F().form
        self.assertEqual(f.fields['o'].choices,
            [('username', 'Username'), ('-username', 'Username (descending)'), ('status', 'Status'), ('-status', 'Status (descending)')])

    def test_ordering_uses_filter_label(self):
        class F(FilterSet):
            username = CharFilter(label='Account')

            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = True

        f = F().form
        self.assertEqual(f.fields['o'].choices,
            [('username', 'Account'), ('-username', 'Account (descending)'), ('status', 'Status'), ('-status', 'Status (descending)')])

    def test_ordering_uses_implicit_filter_name(self):
        class F(FilterSet):
            account = CharFilter(name='username')

            class Meta:
                model = User
                fields = ['account', 'status']
                order_by = True

        f = F().form
        self.assertEqual(f.fields['o'].choices,
            [('username', 'Account'), ('-username', 'Account (descending)'), ('status', 'Status'), ('-status', 'Status (descending)')])

    def test_ordering_with_overridden_field_name(self):
        """
        Set the `order_by_field` on the queryset and ensure that the
        field name is respected.
        """
        class F(FilterSet):
            order_by_field = 'order'

            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status']

        f = F().form
        self.assertNotIn('o', f.fields)
        self.assertIn('order', f.fields)
        self.assertEqual(f.fields['order'].choices, [('status', 'Status')])
    
    def test_ordering_with_overridden_field_name_and_descending(self):
        """
        Set the `order_by_field` on the queryset and ensure that the
        field name is respected.
        """
        class F(FilterSet):
            order_by_field = 'order'

            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = ['status', '-status']

        f = F().form
        self.assertNotIn('o', f.fields)
        self.assertIn('order', f.fields)
        self.assertEqual(f.fields['order'].choices, [('status', 'Status'), ('-status', 'Status (descending)')])

    def test_ordering_with_overridden_field_name_and_using_all_fields(self):
        class F(FilterSet):
            order_by_field = 'order'

            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = True

        f = F().form
        self.assertIn('order', f.fields)
        self.assertEqual(f.fields['order'].choices,
            [('username', 'Username'), ('-username', 'Username (descending)'), ('status', 'Status'), ('-status', 'Status (descending)')])

    def test_ordering_with_custom_display_names(self):
        class F(FilterSet):
            class Meta:
                model = User
                fields = ['username', 'status']
                order_by = [('status', 'Current status')]

        f = F().form
        self.assertEqual(
            f.fields['o'].choices, [('status', 'Current status')])


########NEW FILE########
__FILENAME__ = test_views
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.client import RequestFactory

from django_filters.views import FilterView
from django_filters.filterset import FilterSet, filterset_factory

from .models import Book


class GenericViewTestCase(TestCase):
    urls = 'tests.urls'

    def setUp(self):
        Book.objects.create(
            title="Ender's Game", price='1.00', average_rating=3.0)
        Book.objects.create(
            title="Rainbow Six", price='1.00', average_rating=3.0)
        Book.objects.create(
            title="Snowcrash", price='1.00', average_rating=3.0)


class GenericClassBasedViewTests(GenericViewTestCase):
    base_url = '/books/'

    def test_view(self):
        response = self.client.get(self.base_url)
        for b in ['Ender&#39;s Game', 'Rainbow Six', 'Snowcrash']:
            self.assertContains(response, b)

    def test_view_filtering_on_price(self):
        response = self.client.get(self.base_url + '?title=Snowcrash')
        for b in ['Ender&#39;s Game', 'Rainbow Six']:
            self.assertNotContains(response, b)
        self.assertContains(response, 'Snowcrash')

    def test_view_with_filterset_not_model(self):
        factory = RequestFactory()
        request = factory.get(self.base_url)
        filterset = filterset_factory(Book)
        view = FilterView.as_view(filterset_class=filterset)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        for b in ['Ender&#39;s Game', 'Rainbow Six', 'Snowcrash']:
            self.assertContains(response, b)

    def test_view_without_filterset_or_model(self):
        factory = RequestFactory()
        request = factory.get(self.base_url)
        view = FilterView.as_view()
        with self.assertRaises(ImproperlyConfigured):
            view(request)

    def test_view_with_bad_filterset(self):
        class MyFilterSet(FilterSet):
            pass

        factory = RequestFactory()
        request = factory.get(self.base_url)
        view = FilterView.as_view(filterset_class=MyFilterSet)
        with self.assertRaises(ImproperlyConfigured):
            view(request)


class GenericFunctionalViewTests(GenericViewTestCase):
    base_url = '/books-legacy/'

    def test_view(self):
        response = self.client.get(self.base_url)
        for b in ['Ender&#39;s Game', 'Rainbow Six', 'Snowcrash']:
            self.assertContains(response, b)

    def test_view_filtering_on_price(self):
        response = self.client.get(self.base_url + '?title=Snowcrash')
        for b in ['Ender&#39;s Game', 'Rainbow Six']:
            self.assertNotContains(response, b)
        self.assertContains(response, 'Snowcrash')


########NEW FILE########
__FILENAME__ = test_widgets
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.forms import TextInput, Select

from django_filters.widgets import RangeWidget
from django_filters.widgets import LinkWidget
from django_filters.widgets import LookupTypeWidget


class LookupTypeWidgetTests(TestCase):

    def test_widget_requires_field(self):
        with self.assertRaises(TypeError):
            LookupTypeWidget()

    def test_widget_render(self):
        widgets = [TextInput(), Select(choices=(('a', 'a'), ('b', 'b')))]
        w = LookupTypeWidget(widgets)
        self.assertHTMLEqual(w.render('price', ''), """
            <input name="price_0" type="text" />
            <select name="price_1">
                <option value="a">a</option>
                <option value="b">b</option>
            </select>""")

        self.assertHTMLEqual(w.render('price', None), """
            <input name="price_0" type="text" />
            <select name="price_1">
                <option value="a">a</option>
                <option value="b">b</option>
            </select>""")

        self.assertHTMLEqual(w.render('price', ['2', 'a']), """
            <input name="price_0" type="text" value="2" />
            <select name="price_1">
                <option selected="selected" value="a">a</option>
                <option value="b">b</option>
            </select>""")


class LinkWidgetTests(TestCase):

    def test_widget_without_choices(self):
        w = LinkWidget()
        self.assertEqual(len(w.choices), 0)
        self.assertHTMLEqual(w.render('price', ''), """<ul />""")

    def test_widget(self):
        choices = (
            ('test-val1', 'test-label1'),
            ('test-val2', 'test-label2'),
        )
        w = LinkWidget(choices=choices)
        self.assertEqual(len(w.choices), 2)
        self.assertHTMLEqual(w.render('price', ''), """
            <ul>
                <li><a href="?price=test-val1">test-label1</a></li>
                <li><a href="?price=test-val2">test-label2</a></li>
            </ul>""")

        self.assertHTMLEqual(w.render('price', None), """
            <ul>
                <li><a href="?price=test-val1">test-label1</a></li>
                <li><a href="?price=test-val2">test-label2</a></li>
            </ul>""")

        self.assertHTMLEqual(w.render('price', 'test-val1'), """
            <ul>
                <li><a class="selected"
                       href="?price=test-val1">test-label1</a></li>
                <li><a href="?price=test-val2">test-label2</a></li>
            </ul>""")

    def test_widget_with_option_groups(self):
        choices = (
            ('Audio', (
                    ('vinyl', 'Vinyl'),
                    ('cd', 'CD'),
                )
            ),
            ('Video', (
                    ('vhs', 'VHS Tape'),
                    ('dvd', 'DVD'),
                )
            ),
            ('unknown', 'Unknown'),
        )

        w = LinkWidget(choices=choices)
        self.assertHTMLEqual(w.render('media', ''), """
            <ul>
                <li><a href="?media=vinyl">Vinyl</a></li>
                <li><a href="?media=cd">CD</a></li>
                <li><a href="?media=vhs">VHS Tape</a></li>
                <li><a href="?media=dvd">DVD</a></li>
                <li><a href="?media=unknown">Unknown</a></li>
            </ul>""")

    def test_widget_with_blank_choice(self):
        choices = (
            ('', '---------'),
            ('test-val1', 'test-label1'),
            ('test-val2', 'test-label2'),
        )

        w = LinkWidget(choices=choices)
        self.assertHTMLEqual(w.render('price', ''), """
            <ul>
                <li><a class="selected" href="?price=">All</a></li>
                <li><a href="?price=test-val1">test-label1</a></li>
                <li><a href="?price=test-val2">test-label2</a></li>
            </ul>""")

    def test_widget_value_from_datadict(self):
        w = LinkWidget()
        data = {'price': 'test-val1'}
        result = w.value_from_datadict(data, {}, 'price')
        self.assertEqual(result, 'test-val1')


class RangeWidgetTests(TestCase):

    def test_widget(self):
        w = RangeWidget()
        self.assertEqual(len(w.widgets), 2)
        self.assertHTMLEqual(w.render('price', ''), """
            <input type="text" name="price_0" />
            -
            <input type="text" name="price_1" />""")

        self.assertHTMLEqual(w.render('price', slice(5.99, 9.99)), """
            <input type="text" name="price_0" value="5.99" />
            -
            <input type="text" name="price_1" value="9.99" />""")


########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns

from django_filters.views import FilterView
from .models import Book


urlpatterns = patterns('',
    (r'^books-legacy/$',
        'django_filters.views.object_filter', {'model': Book}),
    (r'^books/$', FilterView.as_view(model=Book)),
)

########NEW FILE########
