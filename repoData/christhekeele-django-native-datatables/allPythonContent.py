__FILENAME__ = features
from django.utils.text import capfirst
from django.forms.forms import pretty_name
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import get_template
from django.template import Template, Context
from django.utils.encoding import StrAndUnicode
from django.utils.safestring import mark_safe

class BaseFeature(StrAndUnicode):
    "A base class used to identify Feature instances"
    creation_counter = 0
    name = None
    label=None
    default_template = None
    template = None
    context = None

    def __init__(self,**kwargs):
        self.label = kwargs.get('label',None)
        # Increase the creation counter, and save our local copy.
        self.creation_counter = BaseFeature.creation_counter
        self.context = {}
        BaseFeature.creation_counter += 1

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        return cmp(self.creation_counter, other.creation_counter)
    
    def set_name(self, name):
        self.name = name
        if self.label is None:
            self.label = capfirst(pretty_name(name))
    
    def __unicode__(self):
        self.context['name']=self.name
        self.context['label']=self.label
        named_context = Context(self.context)
        return mark_safe(get_template(self.template).render(named_context))

class BaseFilter(BaseFeature):
    choices = None
    "A base class used to identify Filter instances"
    def __init__(self, **kwargs):
        super(BaseFilter, self).__init__(**kwargs)

class BooleanFilter(BaseFilter):
    true_label = None
    false_label = None
    def __init__(self, **kwargs):
        super(BooleanFilter, self).__init__(**kwargs)
        self.context['true_label'] = self.true_label = kwargs.get('true_label', 'True')
        self.context['false_label'] = self.false_label = kwargs.get('false_label', 'False')
        self.default_template = 'bool_filter.html'
        self.template = kwargs.get('template', self.default_template)
        
class BaseModelFilter(BaseFilter):
    '''A Feature that filters model instances against a developer-provided model property pointing to another table'''
    model = None
    queryset = None
    filter_list = None
    name_field = None
    
    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        if self.queryset is not None:
            queryset = self.queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(u"'%s' must define 'queryset' or 'model'"
                                       % self.__class__.__name__)
        return queryset
        
    def __init__(self, **kwargs):
        super(BaseModelFilter, self).__init__(**kwargs)
        self.model = kwargs.get('model',None)
        self.queryset = kwargs.get('queryset',None)
        self.filter_list = self.get_queryset()
        self.name_field = kwargs.get('name_field',None)
        if self.name_field:
            self.choices = { item.id : getattr(item, self.name_field) for item in self.filter_list.only('id',self.name_field) }
        else:
            self.choices = { item.id : item for item in self.filter_list.only('pk') }
        self.context = dict(choices=self.choices)

class SingleModelFilter(BaseModelFilter):
    def __init__(self, **kwargs):
        super(SingleModelFilter, self).__init__(**kwargs)
        self.default_template = 'single_filter.html'
        self.template = kwargs.get('template', self.default_template)

class MultiModelFilter(BaseModelFilter):
    def __init__(self, **kwargs):
        super(MultiModelFilter, self).__init__(**kwargs)
        self.default_template = 'multi_filter.html'
        self.template = kwargs.get('template', self.default_template)

class SelectModelFilter(BaseModelFilter):
    def __init__(self, **kwargs):
        super(SelectModelFilter, self).__init__(**kwargs)
        self.default_template = 'select_filter.html'
        self.template = kwargs.get('template', self.default_template)

class MultiSelectModelFilter(BaseModelFilter):
    def __init__(self, **kwargs):
        super(MultiSelectModelFilter, self).__init__(**kwargs)
        self.default_template = 'multi_select_filter.html'
        self.template = kwargs.get('template', self.default_template)

class BaseSearch(BaseFeature):
    search_fields = None
    def __init__(self, **kwargs):
        super(BaseSearch, self).__init__(**kwargs)
        self.search_fields = kwargs.get('search_fields', None)
        
class Search(BaseSearch):
    def __init__(self, **kwargs):
        super(Search, self).__init__(**kwargs)
        self.default_template = 'search.html'
        self.template = kwargs.get('template', self.default_template)
########NEW FILE########
__FILENAME__ = models
# EXAMPLE MODEL

# from django.db import models
# from django.contrib.localflavor.us.models import PhoneNumberField
# 
# from django.db.models import Manager
# from company.tables import CompanyDatatable
# 
# from datetime import datetime
# 
# class Company(models.Model):
#     # datatable is secretly a manager, so we have to set the default first.
#     objects = Manager()
#     datatable = CompanyDatatable()
#     
#     name = models.CharField(max_length=150)
#     parent = models.ForeignKey('self', related_name="children", null=True, blank=True);
#     
#     website = models.URLField(null=True, blank=True)
#     email = models.EmailField()
#     phone = PhoneNumberField()
#     extension = models.PositiveIntegerField(null=True, blank=True)
#     fax = PhoneNumberField(null=True, blank=True)
#     
#     active = models.BooleanField()
#     priority = models.CharField(max_length=2, choices=(('H', 'High'),('M', 'Medium'),('L', 'Low'),), default='L')
#     
#     acquired_on = models.DateField(default=datetime.now().date())
#     
#     def __unicode__(self):
#         return u"%s" % (self.name)
#         
#     class Meta:
#         ordering = ['name']
########NEW FILE########
__FILENAME__ = tables
from bisect import bisect
import sys
from collections import OrderedDict
import inspect 
from .features import BaseFeature, BaseFilter, BaseSearch
from django.db.models import Manager, Q
from django.db.models.query import QuerySet
from django.core.paginator import Paginator
from django.utils.encoding import smart_unicode
from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict

class FeatureDict(OrderedDict):
    def __unicode__(self):
        return mark_safe(''.join([item.__unicode__() for item in self.values()]))

class DatatableOptions(object):
    def __init__(self, options=None):
        self.name = getattr(options, 'name', 'datatable')
        self.model = getattr(options, 'model', None)
        
class DatatableState(object):
    def __init__(self, state, paginate):
        self.search_values = getattr(state, 'search_values', {})
        self.filter_values = getattr(state, 'filter_values', {'active':True})
        self.ordering = getattr(state, 'ordering', {})
        if paginate:
            self.page_number = getattr(state, 'page_number', 1)
            self.per_page = getattr(state, 'per_page', 20)
        self.is_changed = True
    
def get_declared_features(bases, attrs, with_base_features=True):
    features = [(feature_name, attrs.pop(feature_name)) for feature_name, obj in attrs.items() if isinstance(obj, BaseFeature)]
    features.sort(key=lambda x: x[1].creation_counter)

    if with_base_features:
        for base in bases[::-1]:
            if hasattr(base, 'base_features'):
                features = base.base_features.items() + features
    else:
        for base in bases[::-1]:
            if hasattr(base, 'declared_features'):
                features = base.declared_features.items() + features

    return SortedDict(features)
    
class DatatableMetaclass(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(DatatableMetaclass, cls).__new__
        parents = [b for b in bases if isinstance(b, DatatableMetaclass)]
        if not parents:
            # If this isn't a subclass of Datatable, don't do anything special.
            return super_new(cls, name, bases, attrs)
        
        # Get features from parent classes
        attrs['base_features']=get_declared_features(bases, attrs)
        # Add them in while mantaining 'base_features' for iteration
        attrs = dict(attrs, **attrs['base_features'])
        # Create the class w/attrs
        new_class = super(DatatableMetaclass, cls).__new__(cls, name, bases, attrs)
        
        attr_meta = attrs.pop('Meta', None)
        new_class._meta=DatatableOptions(attr_meta)
        
        attr_state = attrs.pop('Initial', None)
        attr_paginate = attrs.pop('paginate', True)
        new_class._state=DatatableState(state=attr_state, paginate=attr_paginate)
        
        features = attrs.get('features', FeatureDict({}))
        filters = attrs.get('filters', FeatureDict({}))
        searches = attrs.get('searches', FeatureDict({}))
        for key, attr in attrs.items():
            if isinstance(attr, BaseFeature):
                # Populate a list of features that were declared
                attr.set_name(key)
                features[key] = attr
                if isinstance(attr, BaseFilter):
                    filters[key] = attr
                if isinstance(attr, BaseSearch):
                    searches[key] = attr
        
        new_class.features=features
        new_class.filters=filters
        new_class.searches=searches
        new_class.order_fields = attrs.get('order_fields',None)
        return new_class
        
class Datatable(Manager):
    __metaclass__ = DatatableMetaclass
    paginator = None
    
    def __init__(self, *args, **kwargs):
        super(Datatable, self).__init__()
        self.keys=['id','features','filters','searches','order_fields','pagination','paginate','paginator','_state']
        for key in self.keys:
            if not hasattr(self,key):
                setattr(self,key,None)
        if self.paginator is None:
            self.paginator = Paginator
        if self.paginate is None:
            self.paginate = True
        if self.order_fields is None:
            self.order_fields = []
            
        # Pin Datatable to associated model
        self._meta.model.add_to_class(self._meta.name, self)
        # Give datatable model info for abstraction
        self.model = self._meta.model
            
    def get_query_set(self):
        return DataSet(model=self.model, query=None, using=None,
                        keys=self.keys,
                        **{ key:getattr(self, key) for key in self.keys }
        )
        
class DataSet(QuerySet):
    ##########
    # Override base QuerySet methods to keep track of DataSet meta
    ##########
    def __init__(self, model, keys, query=None, using=None, **kwargs):
        super(DataSet, self).__init__(model, query, using)
        self.model = model
        self.keys=keys
        for key in keys:
            setattr(self,key,kwargs[key])
    
    def __getitem__(self, k):
        result = super(DataSet, self).__getitem__(k)
        return DataList(model=self.model, keys=self.keys, result=result, **{ key:getattr(self, key) for key in self.keys })
    
    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        query = self.query.clone()
        if self._sticky_filter:
            query.filter_is_sticky = True
        c = klass(model=self.model, query=query, using=self._db, keys=self.keys, **{ key:getattr(self, key) for key in self.keys })
        c._for_write = self._for_write
        c._prefetch_related_lookups = self._prefetch_related_lookups[:]
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c
    ##########
    # End overrides
    ##########
    
    # Modify datatable.state from a dict of options
    def update_state(self, action, target, value):
        # print action, target, value
        if action == 'search':
            if target in self._state.search_values and not value: del self._state.search_values[target]
            elif not hasattr(self._state.search_values, target) or value != getattr(self._state.search_values, target, None):
                self._state.search_values[target] = value
                
        elif action == 'single_filter':
            # Deal with boolean filters
            if value == 'True': value = True
            elif value == 'False': value = False
            # IF the filter was set to empty
            if target in self._state.filter_values and value is None: del self._state.filter_values[target]
            # IF filter is applied for the first time or the filter isn't currently applied
            elif not target in self._state.filter_values or value != getattr(self._state.filter_values, target, None): self._state.filter_values[target] = value
                
        elif action == 'multi_filter':
            if target in self._state.filter_values and value is None: del self._state.filter_values[target]
            else: self._state.filter_values[target] = value
                
        elif action == 'order':
            if not target in self._state.ordering: self._state.ordering[target] = {}
            
            if self._state.ordering[target] == "desc": self._state.ordering = {target:"asc"}
            elif self._state.ordering[target] == "asc": self._state.ordering = {target:"desc"}
            else: self._state.ordering = {target:value}
                
        elif action == 'per_page':
            if self._state.per_page != value:
                self._state.per_page = value
                
        elif action == 'page':
            if self._state.page_number != value:
                self._state.page_number = value
        
        else:
            raise AttributeError, "'%s' datatable action is not supported. Refer to nativetables documentation for a list of valid options." % action
            
        if not action in ['order', 'page']:
            self._state.page_number = 1
            
        return self
        
    def get_transformation(self):
        chain = self._clone()
        if getattr(self,'filters', False):
            chain = chain.filter_data()
        if getattr(self,'searches', False):
            chain = chain.search()
        if getattr(self,'order_fields', False):
            chain = chain.order()
        return chain
    
    def filter_data(self):
        print self._state.filter_values
        filter_args = {}
        for filter_field, selection in self._state.filter_values.iteritems():
            if filter_field in [f for f in self.filters] and not selection is None:
                if isinstance(selection, list):
                    filter_args[filter_field+"__in"]=selection
                else:
                    filter_args[filter_field]=selection
        print filter_args
        return self.filter(**filter_args) if filter_args else self
        
    def search(self):
        queries = []
        for search_name, search_param in self._state.search_values.iteritems():
            if search_name in [s for s in self.searches]:
                for search_field in self.searches[search_name].search_fields:
                    queries.append( Q(**{search_field+"__icontains"  : search_param}) )
        if queries:
            search_args = queries.pop()
            for query in queries:
                search_args |= query
            return self.filter(search_args)
        else:
            return self
        
    def order(self):
        order_args = ""
        for order_field, direction in self._state.ordering.iteritems():
            if order_field in self.order_fields:
                order_args = ("-" if direction=="desc" else "")+order_field
        return self.order_by(order_args) if order_args else self
        
    def paginate_data(self):
        return self.paginator(self, self._state.per_page).page(self._state.page_number)
            

class DataList(list):
    ##########
    ## Override base list methods to keep track of DataList meta
    ##########
    def __init__(self, model, keys, result, **kwargs):
        list.__init__(self, result)
        self.model=model
        self.keys=keys
        for key in keys:
            setattr(self,key,kwargs[key])

    def __getitem__(self, k):
        result = super(DataList, self).__getitem__(k)
        return DataList(*result, keys=self.keys, **{ key:getattr(self, key) for key in self.keys })
        

def default_datatable(model):
    pass
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
# EXAMPLE URL

# from django.conf.urls import patterns, url
# from company.models import Company,
# 
# from nativetables.views import DatatableView
# 
# urlpatterns = patterns('company.views',
#     url(r'^table/$',
#         DatatableView.as_view(
#             template_name="companies/index.html",
#             datatable=Company.datatable,
#         ),
#         name='company_table'
#     ),
########NEW FILE########
__FILENAME__ = views
from django.core.exceptions import ImproperlyConfigured
from django.views.generic.list import MultipleObjectMixin, ListView
from django.core.paginator import Page

from django.utils import simplejson
import re

from .tables import default_datatable

class DatatableMixin(object):
    '''
    Requires MultipleObjectMixin derivative
    '''
    datatable = None
    context_datatable_name = None

    def get_queryset(self):
        """
        Return the datatable queryset class, transformed appropriately.
        """
        if self.datatable is not None:
            datatable_instance = self.datatable()
        # elif self.model is not None:
        #     datatable = default_datatable(self.model).all()
        else:
            raise ImproperlyConfigured(u"A datatable class was not specified. Define "
                                       u"%(cls)s.model to use the default or pass in your custom datatable through "
                                       u"%(cls)s.datatable"
                                       % {"cls": type(self).__name__})
        # Give datatable id so it can be referenced in html DOM elements
        datatable_instance.id = self.get_context_datatable_name(datatable_instance)
        return datatable_instance.all()

    def get_context_datatable_name(self, queryset):
        """
        Get the name to use for the table's template variable.
        If not provided, use underscored version of datatable class name
        """
        if self.context_datatable_name:
            context_datatable_name = self.context_datatable_name
        else:
            if hasattr(queryset,"object_list"):
                model = queryset.object_list.model
            else:
                model = queryset.model
            context_datatable_name = re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', model.__name__).lower().strip('_') + "_table"
        return context_datatable_name
        
    def get_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        queryset = kwargs.pop('object_list')
        context_datatable_name = self.get_context_datatable_name(queryset)
        if queryset.paginate:
            page_obj = queryset.paginate_data()
            context = {
                'paginator': page_obj.paginator,
                'page_obj': page_obj,
                'is_paginated': True,
            }
            object_list = page_obj.object_list
            
            allow_empty = self.get_allow_empty()        
            if not allow_empty:
                # When pagination is enabled and object_list is a queryset,
                # it's better to do a cheap query than to load the unpaginated
                # queryset in memory.
                if (self.get_paginate_by(self.object_list) is not None
                    and hasattr(self.object_list, 'exists')):
                    is_empty = not self.object_list.exists()
                else:
                    is_empty = len(self.object_list) == 0
                if is_empty:
                    raise Http404(_(u"Empty list and '%(class_name)s.allow_empty' is False.")
                            % {'class_name': self.__class__.__name__})
        else:
            context = {
                'paginator': None,
                'page_obj': None,
                'is_paginated': False,
                'object_list': queryset
            }
            object_list = queryset

        if context_datatable_name is not None:
            context[context_datatable_name] = context['object_list'] = object_list
            
        context.update(kwargs)
        return context
        
        # return super(DatatableMixin, self).get_context_data(**context)
       
       
from base.helpers.django_utils import get_current_user
from company.models import Employee
class DatatableView(DatatableMixin, ListView):
    """
    Generic view that renders a template and passes in a ``Datatable`` object.
    """
    def get(self, request, *args, **kwargs):
        # If this is a page_load, inject a clean datatable into the session
        if not request.is_ajax():
            request.session['datatable'] = self.get_queryset()
        # Else, if there are ajax-requested changes in the GET data, update the table's state
        elif request.GET:
            # Pop the only table's changes from dict since datatableview only supports one datatable
            changes = simplejson.loads(request.GET.copy()['datatable_changes']).popitem()[1]
            print changes
            request.session['datatable'] = request.session['datatable'].update_state(**changes)

        current_user = get_current_user()
        if current_user.is_authenticated() and not current_user.is_superuser:
            request.session['datatable']._state.filter_values['representative__employee'] = Employee.objects.get(user=current_user)
        else:
            request.session['datatable']._state.filter_values['representative__employee'] = None
            
        self.object_list = request.session['datatable'].get_transformation()
        
        context = self.get_context_data(object_list=self.object_list)
        return self.render_to_response(context)
########NEW FILE########
