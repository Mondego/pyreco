__FILENAME__ = context_processors
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from models import ViewTracker

def most_popular(request):
    return {'most_popular' : ViewTracker.objects.get_most_popular() }

def recently_added(request):
    return {'recently_added' : ViewTracker.objects.get_recently_added() }

def recently_viewed(request):
    return {'recently_viewed' : ViewTracker.objects.get_recently_viewed() }

def most_viewed(request):
    return {'most_viewed' : ViewTracker.objects.get_most_viewed() }

########NEW FILE########
__FILENAME__ = forms
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms

# place form definition here
########NEW FILE########
__FILENAME__ = models
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from datetime import datetime

from math import log

from django.db import models, connection
from django.db.models.expressions import F
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

# Settings for popularity:
# - POPULARITY_LISTSIZE; default size of the lists returned by get_most_popular etc.
# - POPULARITY_CHARAGE; characteristic age used for measuring the popularity

from django.conf import settings
POPULARITY_CHARAGE = float(getattr(settings, 'POPULARITY_CHARAGE', 3600))
POPULARITY_LISTSIZE = int(getattr(settings, 'POPULARITY_LISTSIZE', 10))

# Maybe they wrote their own mysql backend that *is* mysql?
COMPATIBLE_DATABASES = getattr(settings, 'POPULARITY_COMPATABILITY_OVERRIDE',None) or ('django.db.backends.mysql', )

class ViewTrackerQuerySet(models.query.QuerySet):
    _LOGSCALING = log(0.5)
    
    def __init__ (self, model = None, *args, **kwargs):
        super(self.__class__, self).__init__ (model, *args, **kwargs)

        self._DATABASE_ENGINE = settings.DATABASES.get(kwargs.get('using',None) or 'default')['ENGINE']
        self._SQL_NOW = "'%s'"
        self._SQL_AGE = 'TIMESTAMPDIFF(SECOND, added, %(now)s)'
        self._SQL_RELVIEWS = '(views/%(maxviews)d)'
        self._SQL_RELAGE = '(%(age)s/%(maxage)d)'
        self._SQL_NOVELTY = '(%(factor)s * EXP(%(logscaling)s * %(age)s/%(charage)s) + %(offset)s)'
        self._SQL_POPULARITY = '(views/%(age)s)'
        self._SQL_RELPOPULARITY = '(%(popularity)s/%(maxpopularity)s)'
        self._SQL_RANDOM = connection.ops.random_function_sql()
        self._SQL_RELEVANCE = '%(relpopularity)s * %(novelty)s'
        self._SQL_ORDERING = '%(relview)f * %(relview_sql)s + \
                              %(relage)f  * %(relage_sql)s + \
                              %(novelty)f * %(novelty_sql)s + \
                              %(relpopularity)f * %(relpopularity_sql)s + \
                              %(random)f * %(random_sql)s + \
                              %(relevance)f * %(relevance_sql)s + \
                              %(offset)f'
    
    def _get_db_datetime(self, value=None):
        """ Retrieve an SQL-interpretable representation of the datetime value, or
            now if no value is specified. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        if not value:
            value = datetime.now()
        
        _SQL_NOW = self._SQL_NOW % connection.ops.value_to_db_datetime(value)
        return  _SQL_NOW
    
    def _add_extra(self, field, sql):
        """ Add the extra parameter 'field' with value 'sql' to the queryset (without
            removing previous parameters, as oppsoed to the normal .extra method). """
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken"

        logging.debug(sql)   
        clone = self._clone()
        clone.query.add_extra({field:sql}, None, None, None, None, None)
        return clone
        
    def select_age(self):
        """ Adds age with regards to NOW to the QuerySet
            fields. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }
        
        return self._add_extra('age', _SQL_AGE)
        
    def select_relviews(self, relative_to=None):
        """ Adds 'relview', a normalized viewcount, to the QuerySet.
            The normalization occcurs relative to the maximum number of views
            in the current QuerySet, unless specified in 'relative_to'.
            
            The relative number of views should always in the range [0, 1]. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        if not relative_to:
            relative_to = self
        
        assert relative_to.__class__ == self.__class__, \
                'relative_to should be of type %s but is of type %s' % (self.__class__, relative_to.__class__)
            
        maxviews = relative_to.aggregate(models.Max('views'))['views__max']
        
        SQL_RELVIEWS = self._SQL_RELVIEWS % {'maxviews' : maxviews}
        
        return self._add_extra('relviews', SQL_RELVIEWS)

    def select_relage(self, relative_to=None):
        """ Adds 'relage', a normalized age, relative to the QuerySet.
            The normalization occcurs relative to the maximum age
            in the current QuerySet, unless specified in 'relative_to'.

            The relative age should always in the range [0, 1]. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        if not relative_to:
            relative_to = self

        assert relative_to.__class__ == self.__class__, \
                'relative_to should be of type %s but is of type %s' % (self.__class__, relative_to.__class__)

        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }

        maxage = relative_to.extra(select={'maxage':'MAX(%s)' % _SQL_AGE}).values('maxage')[0]['maxage']

        SQL_RELAGE = self._SQL_RELAGE % {'age'    : _SQL_AGE,
                                         'maxage' : maxage}

        return self._add_extra('relage', SQL_RELAGE)


    def select_novelty(self, minimum=0.0, charage=None):
        """ Compute novelty - this is the age muliplied by a characteristic time.
            After a this characteristic age, the novelty will be half its original
            value (if the minimum is 0). The minimum is needed when this value 
            is used in multiplication.
            
            The novelty value is always in the range [0, 1]. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        offset = minimum
        factor = 1/(1-offset)
        
        # Characteristic age, default one hour
        # After this amount (in seconds) the novelty is exactly 0.5
        if not charage:
            charage = POPULARITY_CHARAGE
            
        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }
        
        SQL_NOVELTY =  self._SQL_NOVELTY % {'logscaling' : self._LOGSCALING, 
                                            'age'        : _SQL_AGE,
                                            'charage'    : charage,
                                            'offset'     : offset, 
                                            'factor'     : factor }

        return self._add_extra('novelty', SQL_NOVELTY)
    
    def select_popularity(self):
        """ Compute popularity, which is defined as: views/age. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }
        
        SQL_POPULARITY = self._SQL_POPULARITY % {'age' : _SQL_AGE }

        return self._add_extra('popularity', SQL_POPULARITY)
    
    def select_relpopularity(self, relative_to=None):
        """ Compute relative popularity, which is defined as: (views/age)/MAX(views/age).
            
            The relpopularity value should always be in the range [0, 1]. """

        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        if not relative_to:
            relative_to = self

        assert relative_to.__class__ == self.__class__, \
                'relative_to should be of type %s but is of type %s' % (self.__class__, relative_to.__class__)

        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }

        SQL_POPULARITY = self._SQL_POPULARITY % {'age' : _SQL_AGE }

        maxpopularity = relative_to.extra(select={'popularity' : SQL_POPULARITY}).aggregate(models.Max('popularity'))['popularity__max']
        
        SQL_RELPOPULARITY = self._SQL_RELPOPULARITY % {'popularity'    : SQL_POPULARITY,
                                                       'maxpopularity' : maxpopularity }

        return self._add_extra('relpopularity', SQL_POPULARITY)
    
    def select_random(self):
        """ Returns the original QuerySet with an extra field 'random' containing a random
            value in the range [0,1] to use for ordering.
        """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        SQL_RANDOM = self.RANDOM
        
        return self._add_extra('random', SQL_RANDOM)
    
    def select_relevance(relative_to=None, minimum_novelty=0.1, charage_novelty=None):
        """ This adds the multiplication of novelty and relpopularity to the QuerySet, as 'relevance'. """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        if not relative_to:
            relative_to = self
        
        assert relative_to.__class__ == self.__class__, \
                'relative_to should be of type %s but is of type %s' % (self.__class__, relative_to.__class__)
        
        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }
        
        SQL_POPULARITY = self._SQL_POPULARITY % {'age' : _SQL_AGE }
        
        maxpopularity = relative_to.extra(select={'popularity' : SQL_POPULARITY}).aggregate(models.Max('popularity'))['popularity__max']
        
        SQL_RELPOPULARITY = self._SQL_RELPOPULARITY % {'popularity'    : SQL_POPULARITY,
                                                       'maxpopularity' : maxpopularity }
        
        # Characteristic age, default one hour
        # After this amount (in seconds) the novelty is exactly 0.5
        if not charage_novelty:
           charage_novelty = POPULARITY_CHARAGE
        
        offset = minimum_novelty
        factor = 1/(1-offset)
        
        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }
        
        SQL_NOVELTY =  self._SQL_NOVELTY % {'logscaling' : self._LOGSCALING, 
                                            'age'        : _SQL_AGE,
                                            'charage'    : charage_novelty,
                                            'offset'     : offset, 
                                            'factor'     : factor }
        
        SQL_RELEVANCE = self._SQL_RELEVANCE % {'novelty'       : SQL_NOVELTY,
                                               'relpopularity' : SQL_RELPOPULARITY }

        return self._add_extra('relevance', SQL_RELEVANCE)

    def select_ordering(relview=0.0, relage=0.0, novelty=0.0, relpopularity=0.0, random=0.0, relevance=0.0, offset=0.0, charage_novelty=None, relative_to=None):
        """ Creates an 'ordering' field used for sorting the current QuerySet according to
            specified criteria, given by the parameters. 
            
            All the parameters given here are relative to one another, so if you specify 
            random=1.0 and relage=3.0 then the relative age is 3 times as important. 
            
            Please do note that the relative age is the only value here that INCREASES over time so
            you might want to specify a NEGATIVE value here and use an offset, just to compensate. 
        """
        assert self._DATABASE_ENGINE in COMPATIBLE_DATABASES, 'Database engine %s is not compatible with this functionality.'
        
        if not relative_to:
            relative_to = self
        
        assert relative_to.__class__ == self.__class__, \
                'relative_to should be of type %s but is of type %s' % (self.__class__, relative_to.__class__)
        
        assert abs(relview+relage+novelty+relpopularity+random+relevance) > 0, 'You should at least give me something to order by!'
        
        maxviews = relative_to.aggregate(models.Max('views'))['views__max']
        
        SQL_RELVIEWS = self._SQL_RELVIEWS % {'maxviews' : maxviews}
        
        _SQL_AGE = self._SQL_AGE % {'now' : self._get_db_datetime() }
        
        maxage = relative_to_extra(select={'age':_SQL_AGE}).aggregate(Max('age'))['age__max']

        SQL_RELAGE = self._SQL_RELAGE % {'age'    : _SQL_AGE,
                                         'maxage' : maxage}

        # Characteristic age, default one hour
        # After this amount (in seconds) the novelty is exactly 0.5
        if not charage_novelty:
            charage_novelty = POPULARITY_CHARAGE
            
        # Here, because the ordering field is not normalize, we don't have to bother about a minimum for the novelty
        SQL_NOVELTY =  self._SQL_NOVELTY % {'logscaling' : self._LOGSCALING, 
                                            'age'        : _SQL_AGE,
                                            'charage'    : charage_novelty,
                                            'offset'     : 0.0, 
                                            'factor'     : 1.0 }
                                            
        SQL_POPULARITY = self._SQL_POPULARITY % {'age' : _SQL_AGE }

        maxpopularity = relative_to.extra(select={'popularity':SQL_POPULARITY}).aggregate(Max('popularity'))['popularity__max']

        SQL_RELPOPULARITY = self._SQL_RELPOPULARITY % {'popularity'    : SQL_POPULARITY,
                                                       'maxpopularity' : maxpopularity }
        
        SQL_RANDOM = self.RANDOM
        
        SQL_RELEVANCE = self._SQL_RELEVANCE % {'novelty'       : SQL_NOVELTY,
                                               'relpopularity' : SQL_RELPOPULARITY }
                                      
        SQL_ORDERING = self._SQL_ORDERING % {'relview'           : relview,
                                             'relage'            : relage,
                                             'novelty'           : novelty,
                                             'relpopularity'     : relpopularity,
                                             'relevance'         : relevance,
                                             'random'            : random,
                                             'relview_sql'       : SQL_RELVIEWS,
                                             'relage_sql'        : SQL_RELAGE,
                                             'novelty_sql'       : SQL_NOVELTY,
                                             'relpopularity_sql' : SQL_RELPOPULARITY,
                                             'random_sql'        : SQL_RANDOM,
                                             'relevance_sql'     : SQL_RELEVANCE }
        
        return self._add_extra('ordering', SQL_ORDERING)
        
    def get_recently_viewed(self, limit=None):
        """ Returns the most recently viewed objects. """
        if not limit:
            limit = POPULARITY_LISTSIZE
            
        return self.order_by('-viewed')[:limit]
    
    def get_recently_added(self, limit=None):
        """ Returns the objects with the most rcecent added. """
        if not limit:
            limit = POPULARITY_LISTSIZE
            
        return self.order_by('-added')[:limit]
    
    def get_most_popular(self, limit=None):
        """ Returns the most popular objects. """
        if not limit:
            limit = POPULARITY_LISTSIZE
            
        return self.select_popularity().order_by('-popularity')[:limit]
    
    def get_most_viewed(self, limit=None):
        """ Returns the most viewed objects. """
        if not limit:
            limit = POPULARITY_LISTSIZE
            
        return self.order_by('-views')[:limit]
        
    def get_for_model(self, model):
        """ Returns the objects and its views for a certain model. """
        return self.get_for_models([model])
    
    def get_for_models(self, models):
        """ Returns the objects and its views for specified models. """

        cts = []
        for model in models:
            cts.append(ContentType.objects.get_for_model(model))
        
        return self.filter(content_type__in=cts)
    
    def get_for_object(self, content_object, create=False):
        """ Gets the viewtracker for specified object, or creates one 
            if requested. """
        
        ct = ContentType.objects.get_for_model(content_object)
        
        if create:
            [viewtracker, created] = self.get_or_create(content_type=ct, object_id=content_object.pk)
        else:
            viewtracker = self.get(content_type=ct, object_id=content_object.pk)
        
        return viewtracker
    
    def get_for_objects(self, objects):
        """ Gets the viewtrackers for specified objects, or creates them 
            if requested. """
        
        qs = self.none()
        for obj in objects:
            ct = ContentType.objects.get_for_model(obj.__class__)
            
            qs = qs | self.filter(content_type=ct, object_id=obj.pk)
        
        return self & qs
    
    def get_for_queryset(self, qs):
        """ Gets the viewtrackers for the objects in a specified queryset. """
        
        ct = ContentType.objects.get_for_model(qs.model)
            
        return self.filter(content_type=ct, object_id__in=qs.values('pk'))
    
    def get_object_list(self):
        """ Gets a list with all the objects tracked in the current queryset. """
        
        obj_list = []
        for obj in self:
            obj_list.append(obj.content_object)
        
        return obj_list
    
    def get_querysets(self):
        """ Gets a list of all the querysets for the objects tracked in the current queryset. """
        
        qs_list = []
        for ct_id in self.values('content_type').distinct():
            ct = ContentType.objects.get_for_id(ct_id)
            qs_inner = self.filter(content_type=ct_id).values('object_id')
            qs = ct.model_class().objects.filter(pk__in=qs_inner)
            
            qs_list.append(qs)
        
        return qs_list

class ViewTrackerManager(models.Manager):
    """ Manager methods to do stuff like:
        ViewTracker.objects.get_views_for_model(MyModel).
        
        For documentation, please refer the ViewTrackerQuerySet object.
    """
    
    def get_query_set(self):
		return ViewTrackerQuerySet(self.model)
        
    def select_age(self, *args, **kwargs):
        return self.get_query_set().select_age(*args, **kwargs)

    def select_relage(self, *args, **kwargs):
        return self.get_query_set().select_relage(*args, **kwargs)
                    
    def select_relviews(self, *args, **kwargs):
        return self.get_query_set().select_relviews(*args, **kwargs)

    def select_novelty(self, *args, **kwargs):
        return self.get_query_set().select_novelty(*args, **kwargs)
    
    def select_popularity(self, *args, **kwargs):
        return self.get_query_set().select_popularity(*args, **kwargs)

    def select_relpopularity(self, *args, **kwargs):
        return self.get_query_set().select_relpopularity(*args, **kwargs)

    def select_random(self, *args, **kwargs):
        return self.get_query_set().select_random(*args, **kwargs)

    def select_ordering(self, *args, **kwargs):
        return self.get_query_set().select_ordering(*args, **kwargs)

    def get_recently_added(self, *args, **kwargs):
        return self.get_query_set().get_recently_added(*args, **kwargs)
    
    def get_recently_viewed(self, *args, **kwargs):
        return self.get_query_set().get_recently_viewed(*args, **kwargs)
    
    def get_most_viewed(self, *args, **kwargs):
        return self.get_query_set().get_most_viewed(*args, **kwargs)
    
    def get_most_popular(self, *args, **kwargs):
            return self.get_query_set().get_most_popular(*args, **kwargs)
    
    def get_for_model(self, *args, **kwargs):
        return self.get_query_set().get_for_model(*args, **kwargs)
    
    def get_for_models(self, *args, **kwargs):
        return self.get_query_set().get_for_models(*args, **kwargs)
    
    def get_for_object(self, *args, **kwargs):
        return self.get_query_set().get_for_object(*args, **kwargs)
    
    def get_for_objects(self, *args, **kwargs):
        return self.get_query_set().get_for_objects(*args, **kwargs)
    
    def get_for_queryset(self, *args, **kwargs):
        return self.get_query_set().get_for_queryset(*args, **kwargs)
    
    def get_object_list(self, *args, **kwargs):
        return self.get_query_set().get_object_list(*args, **kwargs)


class ViewTracker(models.Model):
    """ The ViewTracker object does exactly what it's supposed to do:
        track the amount of views for an object in order to create make 
        a popularity rating."""
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    added = models.DateTimeField(auto_now_add=True)
    viewed = models.DateTimeField(auto_now=True)
    
    views = models.PositiveIntegerField(default=0)
    
    objects = ViewTrackerManager()
    
    class Meta:
        get_latest_by = 'viewed'
        ordering = ['-views', '-viewed', 'added']
        unique_together = ('content_type', 'object_id')
    
    def __unicode__(self):
        return u"%s, %d views" % (self.content_object, self.views)
            
    @classmethod
    def add_view_for(cls, content_object):
        """ This increments the viewcount for a given object. """
        
        ct = ContentType.objects.get_for_model(content_object)
        assert ct != ContentType.objects.get_for_model(cls), 'Cannot add ViewTracker for ViewTracker.'
        
        qs = cls.objects.filter(content_type=ct, object_id=content_object.pk)
        
        assert qs.count() == 0 or qs.count() == 1, 'More than one ViewTracker for object %s' % content_object
        
        rows = qs.update(views=F('views') + 1, viewed=datetime.now())
        
        # This is here mainly for compatibility reasons
        if not rows:
            qs.create(content_type=ct, object_id=content_object.pk, views=1, viewed=datetime.now())
            logging.debug('ViewTracker created for object %s' % content_object)
        else:
            logging.debug('Views updated to %d for %s' % (qs[0].views, content_object))
        
        return qs[0]
    
    @classmethod
    def get_views_for(cls, content_object):
        """ Gets the total number of views for content_object. """
        
        """ If we don't have any views, return 0. """
        try:
            viewtracker = cls.objects.get_for_object(content_object)
        except ViewTracker.DoesNotExist:
            return 0 
        
        return viewtracker.views


########NEW FILE########
__FILENAME__ = signals
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import django.dispatch

from models import ViewTracker

view = django.dispatch.Signal()

def view_handler(signal, sender, **kwargs):
    ViewTracker.add_view_for(sender)

view.connect(view_handler)

# Use this in the following way:
# from popularity.signals import view
# view.send(myinstance)

########NEW FILE########
__FILENAME__ = popularity_tags
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import template
from django.db.models import get_model

from popularity.models import ViewTracker
from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.filter
def viewtrack(value):
    ''' Add reference to script for adding a view to an object's tracker. 
        Usage: {{ object|viewtrack }}
        This will be substituted by: 'add_view_for(content_type_id, object_id)'
    '''
    ct = ContentType.objects.get_for_model(value)
    return 'add_view_for(%d,%d)' % (ct.pk, value.pk)

def validate_template_tag_params(bits, arguments_count, keyword_positions):
    '''
        Raises exception if passed params (`bits`) do not match signature.
        Signature is defined by `bits_len` (acceptible number of params) and
        keyword_positions (dictionary with positions in keys and keywords in values,
        for ex. {2:'by', 4:'of', 5:'type', 7:'as'}).            
    '''    
    
    if len(bits) != arguments_count+1:
        raise template.TemplateSyntaxError("'%s' tag takes %d arguments" % (bits[0], arguments_count,))
    
    for pos in keyword_positions:
        value = keyword_positions[pos]
        if bits[pos] != value:
            raise template.TemplateSyntaxError("argument #%d to '%s' tag must be '%s'" % (pos, bits[0], value))

# Nodes

class ViewsForObjectNode(template.Node):
    def __init__(self, object, context_var):
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = ViewTracker.get_views_for(object)
        return ''

class ViewsForObjectsNode(template.Node):
    def __init__(self, objects, var_name):
        self.objects = objects
        self.var_name = var_name

    def render(self, context):
        try:
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''

        queryset = ViewTracker.objects.get_for_objects(objects)
        view_dict = {}
        for row in queryset:
            view_dict[row.object_id] = row.views
        for object in objects:
            object.__setattr__(self.var_name, view_dict.get(object.id,0))
        return ''

class MostPopularForModelNode(template.Node):
    def __init__(self, model, context_var, limit=None):
        self.model = model
        self.context_var = context_var
        self.limit = limit

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError('most_popular_for_model tag was given an invalid model: %s' % self.model)
        context[self.context_var] = ViewTracker.objects.get_for_model(model=model).get_most_popular(limit=self.limit)
        return ''

class MostViewedForModelNode(template.Node):
    def __init__(self, model, context_var, limit=None):
        self.model = model
        self.context_var = context_var
        self.limit = limit

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError('most_viewed_for_model tag was given an invalid model: %s' % self.model)
        context[self.context_var] = ViewTracker.objects.get_for_model(model=model).get_most_viewed(limit=self.limit)
        return ''

class RecentlyViewedForModelNode(template.Node):
    def __init__(self, model, context_var, limit=None):
        self.model = model
        self.context_var = context_var
        self.limit = limit

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError('recently_viewed_for_model tag was given an invalid model: %s' % self.model)
        context[self.context_var] = ViewTracker.objects.get_for_model(model=model).get_recently_viewed(limit=self.limit)
        return ''

class RecentlyAddedForModelNode(template.Node):
    def __init__(self, model, context_var, limit=None):
        self.model = model
        self.context_var = context_var
        self.limit = limit

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError('recently_added_for_model tag was given an invalid model: %s' % self.model)
        context[self.context_var] = ViewTracker.objects.get_for_model(model=model).get_recently_added(limit=self.limit)
        return ''

# Tags
@register.tag
def views_for_object(parser, token):
    """
    Retrieves the number of views and stores them in a context variable.

    Example usage::

        {% views_for_object widget as views %}

    """
    bits = token.contents.split()
    validate_template_tag_params(bits, 3, {2:'as'})

    return ViewsForObjectNode(bits[1], bits[3])

@register.tag
def views_for_objects(parser, token):
    """
    Retrieves the number of views for each object and stores them in an attribute.

    Example usage::

        {% views_for_objects widget_list as view_count %}
        {% for object in widget_list %}
            Object Id {{object.id}} - Views {{object.view_count}}
        {% endfor %}
    """
    bits = token.contents.split()
    validate_template_tag_params(bits, 3, {2:'as'})

    return ViewsForObjectsNode(bits[1], bits[3])

@register.tag
def most_popular_for_model(parser, token):
    """
    Retrieves the ViewTrackers for the most popular instances of the given model.
    If the limit is not given it will use settings.POPULARITY_LISTSIZE

    Example usage::

        {% most_popular_for_model main.model_name as popular_models %}
        {% most_popular_for_model main.model_name as popular_models limit 20 %}

    """
    bits = token.contents.split()
    if len(bits) > 4:
        validate_template_tag_params(bits, 5, {2:'as', 4:'limit'})
        return MostPopularForModelNode(bits[1], bits[3], bits[5])
    else:
        validate_template_tag_params(bits, 3, {2:'as'})
        return MostPopularForModelNode(bits[1], bits[3])

@register.tag
def most_viewed_for_model(parser, token):
    """
    Retrieves the ViewTrackers for the most viewed instances of the given model.
    If the limit is not given it will use settings.POPULARITY_LISTSIZE

    Example usage::

        {% most_viewed_for_model main.model_name as viewed_models %}
        {% most_viewed_for_model main.model_name as viewed_models limit 20 %}

    """
    bits = token.contents.split()
    if len(bits) > 4:
        validate_template_tag_params(bits, 5, {2:'as', 4:'limit'})
        return MostViewedForModelNode(bits[1], bits[3], bits[5])
    else:
        validate_template_tag_params(bits, 3, {2:'as'})
        return MostViewedForModelNode(bits[1], bits[3])

@register.tag
def recently_viewed_for_model(parser, token):
    """
    Retrieves the ViewTrackers for the most recently viewed instances of the given model.
    If the limit is not given it will use settings.POPULARITY_LISTSIZE

    Example usage::

        {% recently_viewed_for_model main.model_name as recent_models %}
        {% recently_viewed_for_model main.model_name as recent_models limit 20 %}

    """
    bits = token.contents.split()
    if len(bits) > 4:
        validate_template_tag_params(bits, 5, {2:'as', 4:'limit'})
        return RecentlyViewedForModelNode(bits[1], bits[3], bits[5])
    else:
        validate_template_tag_params(bits, 3, {2:'as'})
        return RecentlyViewedForModelNode(bits[1], bits[3])

@register.tag
def recently_added_for_model(parser, token):
    """
    Retrieves the ViewTrackers for the most recently added instances of the given model.
    If the limit is not given it will use settings.POPULARITY_LISTSIZE

    Example usage::

        {% recently_added_for_model main.model_name as recent_models %}
        {% recently_added_for_model main.model_name as recent_models limit 20 %}

    """
    bits = token.contents.split()
    if len(bits) > 4:
        validate_template_tag_params(bits, 5, {2:'as', 4:'limit'})
        return RecentlyAddedForModelNode(bits[1], bits[3], bits[5])
    else:
        validate_template_tag_params(bits, 3, {2:'as'})
        return RecentlyAddedForModelNode(bits[1], bits[3])

########NEW FILE########
__FILENAME__ = tests
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
import unittest

from time import sleep
from datetime import datetime

from django.template import Context, Template
from django.contrib.contenttypes.models import ContentType

from popularity.models import *

REPEAT_COUNT = 3
MAX_SECONDS = 2
NUM_TESTOBJECTS = 21

from django.db import models

POPULARITY_LISTSIZE = int(getattr(settings, 'POPULARITY_LISTSIZE', 10))

class TestObject(models.Model):
    title = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.title

import popularity
popularity.register(TestObject)

class PopularityTestCase(unittest.TestCase):
    def random_view(self):
        ViewTracker.add_view_for(random.choice(self.objs))
        
    def setUp(self):        
        TestObject(title='Obj a').save()
        TestObject(title='Obj b').save()
        TestObject(title='Obj c').save()
        TestObject(title='Obj d').save()
        TestObject(title='Obj e').save()
        TestObject(title='Obj f').save()
        TestObject(title='Obj g').save()
        TestObject(title='Obj h').save()
        TestObject(title='Obj i').save()
        TestObject(title='Obj j').save()
        TestObject(title='Obj k').save()
        TestObject(title='Obj l').save()
        TestObject(title='Obj m').save()
        TestObject(title='Obj n').save()
        
        self.objs = TestObject.objects.all()
    
    def testViews(self):
        views = {}
        for obj in self.objs:
            views.update({obj :ViewTracker.get_views_for(obj)})

        for obj in self.objs:
            ViewTracker.add_view_for(obj)
            self.assertEquals(ViewTracker.get_views_for(obj), views[obj]+1)

        for obj in self.objs:
            ViewTracker.add_view_for(obj)
            self.assertEquals(ViewTracker.get_views_for(obj), views[obj]+2)
    
    def testViewTrackers(self):
        for obj in self.objs:
            ViewTracker.add_view_for(obj)
        
        viewtrackers = ViewTracker.objects.get_for_objects(self.objs)
        
        self.assertEqual(len(viewtrackers), len(self.objs))
    
    def testLastViewed(self):
        for i in xrange(0, REPEAT_COUNT):
            for obj in self.objs:
                ViewTracker.add_view_for(obj)
        
            sleep(random.randint(1,MAX_SECONDS))
        
            for obj in self.objs:
                ViewTracker.add_view_for(obj)
        
            viewtrackers = ViewTracker.objects.get_for_objects(self.objs)
        
            for tracker in viewtrackers:
                self.assert_(tracker.viewed > tracker.added)
    
    def testAge(self):
        from django.conf import settings
        if settings.DATABASE_ENGINE == 'mysql':
            for i in xrange(0,REPEAT_COUNT):
                new = TestObject(title='Obj q')
                new.save()
                
                # This sets the first view for our test object
                viewtracker = ViewTracker.add_view_for(new)
                
                # Note down the initial time
                # Request the initial time from the database
                old_time = datetime.now()
                added = viewtracker.added
                
                #import ipdb; ipdb.set_trace()
                
                # These should be the same with at most a 1 second difference
                self.assert_(abs((old_time-added).seconds) <= 1, "old_time=%s, added=%s" % (old_time, added))
                
                # Wait a random number of seconds
                wait = random.randint(1,MAX_SECONDS)
                sleep(wait)
                
                # This sets the last view for the same object
                viewtracker = ViewTracker.add_view_for(new)
                
                # Do the same checks
                new_time = datetime.now()
                viewed = viewtracker.viewed
                
                # These should be the same with at most a 1 second difference
                self.assert_(abs((new_time-viewed).seconds) <= 1, "new_time=%s, viewed=%s" % (new_time, viewed))
                                
                # Now see if we have calculated the age right, using previous queries
                calc_age = (new_time - old_time).seconds
                db_age = (viewed - added).seconds
                self.assert_(abs(db_age - calc_age) <= 1, "db_age=%d, calc_age=%d" % (db_age, calc_age))
                
                # Check if we indeed waited the righ amount of time 'test the test'
                self.assert_(abs(wait - calc_age) <= 1, "wait=%d, calc_age=%d" % (wait, calc_age))
                
                # Now rqeuest the age from the QuerySet
                age = ViewTracker.objects.select_age().filter(pk=viewtracker.pk)[0].age
                
                # See whether it matches
                self.assert_(abs(age - db_age) <= 1, "age=%d, db_age=%d" % (age, db_age))
                self.assert_(abs(age - calc_age) <= 1, "age=%d, calc_age=%d" % (age, calc_age))    
            
            # Just a retarded test to see if we have no negative ages for objects    
            for o in ViewTracker.objects.select_age():
                self.assert_(o.age >= 0, "Negative age %f for object <%s>." % (o.age, o))
                    
    
    def testRelviews(self):
        from django.conf import settings
        if settings.DATABASE_ENGINE == 'mysql':
            for i in xrange(0,REPEAT_COUNT):
                self.random_view()
                
                maxviews = 0
            
                for obj in ViewTracker.objects.all():
                    if obj.views > maxviews:
                        maxviews = obj.views
            
                for obj in ViewTracker.objects.select_relviews():
                    relviews_expected = float(obj.views)/maxviews
                    self.assertAlmostEquals(float(obj.relviews), relviews_expected, 3, 'views=%d, relviews=%f, expected=%f' % (obj.views, obj.relviews, relviews_expected))
    
    def testNovelty(self):
        from django.conf import settings
        if settings.DATABASE_ENGINE == 'mysql':
            new = TestObject(title='Obj q')
            new.save()
            
            viewtracker = ViewTracker.add_view_for(new)
            added = viewtracker.added
            
            novelty = ViewTracker.objects.select_novelty(charage=MAX_SECONDS).filter(pk=viewtracker.pk)[0].novelty
            self.assertAlmostEquals(float(novelty), 1.0, 1, 'novelty=%f != 1.0' % novelty)
            
            sleep(MAX_SECONDS)
            
            novelty = ViewTracker.objects.select_novelty(charage=MAX_SECONDS).filter(pk=viewtracker.pk)[0].novelty
            self.assertAlmostEquals(float(novelty), 0.5, 1, 'novelty=%f != 0.5' % novelty)
    
    def testRelage(self):
        from django.conf import settings
        if settings.DATABASE_ENGINE == 'mysql':
            for x in xrange(REPEAT_COUNT):
                new = TestObject(title='Obj q')
                new.save()

                viewtracker = ViewTracker.add_view_for(new)
        
                relage = ViewTracker.objects.select_relage()
                youngest = relage.order_by('relage')[0]
        
                self.assertEqual(viewtracker, youngest)
                self.assertAlmostEquals(float(youngest.relage), 0.0, 2)
        
                oldest_age = ViewTracker.objects.select_age().order_by('-age')[0]
                oldest_relage = relage.order_by('-relage')[0]
        
                self.assertEqual(oldest_relage, oldest_age)
                self.assertAlmostEquals(float(oldest_relage.relage), 1.0, 2)
            
                sleep(random.randint(1,MAX_SECONDS))
    
    def testRelrange(self):
        """ Very simple test for relative counts: just
            checks whether the value is between 0 and 1. 
        """
        from django.conf import settings
        if settings.DATABASE_ENGINE == 'mysql':
            for x in xrange(REPEAT_COUNT):
                new = TestObject(title='Obj q')
                new.save()
                
                for y in xrange(REPEAT_COUNT):
                    viewtracker = ViewTracker.add_view_for(new)
            
            for tracker in ViewTracker.objects.select_relviews().select_relpopularity().select_relage():
                self.assert_(tracker.relviews >= 0.)
                self.assert_(tracker.relviews <= 1.)
                
                self.assert_(tracker.relpopularity >= 0.)
                self.assert_(tracker.relpopularity <= 1.)

                self.assert_(tracker.relage >= 0.)
                self.assert_(tracker.relage <= 1.)

        

class TemplateTagsTestCase(unittest.TestCase):        
    def setUp(self):
        TestObject.objects.all().delete()
        ViewTracker.objects.all().delete()

        self.objs = []
        for i in xrange(1,NUM_TESTOBJECTS):
            self.objs.append(TestObject.objects.create(pk=i, title='Obj %s' % i))

        for obj in self.objs:          
            for i in xrange(int(obj.pk)):            
                ViewTracker.add_view_for(obj)

        # i.e obj 1 has 1 view, obj 2 has 2 views, etc
        # making obj 20 most viewed/popular and obj 1 the least

    def testViewsForOjbect(self):
        views = {self.objs[0]:ViewTracker.get_views_for(self.objs[0])}

        t = Template('{% load popularity_tags %}{% views_for_object obj as views %}')
        c = Context({"obj": self.objs[0]})
        t.render(c)
        self.assertEqual(c['views'], views[self.objs[0]])

    def testViewsForOjbects(self):
        views = {}

        for obj in self.objs:
            views.update({obj :ViewTracker.get_views_for(obj)})

        t = Template('{% load popularity_tags %}{% views_for_objects objs as views %}')
        c = Context({"objs": self.objs})
        t.render(c)
        for obj in c['objs']:
            self.assertEqual(obj.views, views[obj])

        t = Template('{% load popularity_tags %}{% views_for_objects objs as view_count %}')
        c = Context({"objs": self.objs})
        t.render(c)
        for obj in c['objs']:
            self.assertEqual(obj.view_count, views[obj])

    def testMostPopularForModel(self):
        t = Template('{% load popularity_tags %}{% most_popular_for_model popularity.TestObject as popular_objs %}')
        c = Context({})
        t.render(c)       

        self.assertEqual(c['popular_objs'].count(), POPULARITY_LISTSIZE)

        count = 20
        for obj_view in c['popular_objs']:
            self.assertEqual(obj_view.object_id, count)
            self.assertEqual(obj_view.views, obj_view.object_id)
            count -= 1        

        t = Template('{% load popularity_tags %}{% most_popular_for_model popularity.TestObject as popular_objs limit 2 %}')
        c = Context({})
        t.render(c)
    
        self.assertEqual(c['popular_objs'].count(), 2)        
        count = 20
        for obj_view in c['popular_objs']:
            self.assertEqual(obj_view.object_id, count)
            self.assertEqual(obj_view.views, obj_view.object_id)
            count -= 1 

    def testMostViewedForModel(self):
        t = Template('{% load popularity_tags %}{% most_viewed_for_model popularity.TestObject as viewed_objs %}')
        c = Context({})
        t.render(c)       

        self.assertEqual(c['viewed_objs'].count(), POPULARITY_LISTSIZE)

        count = 20
        for obj_view in c['viewed_objs']:
            self.assertEqual(obj_view.object_id, count)
            self.assertEqual(obj_view.views, obj_view.object_id)
            count -= 1        

        t = Template('{% load popularity_tags %}{% most_viewed_for_model popularity.TestObject as viewed_objs limit 2 %}')
        c = Context({})
        t.render(c)
    
        self.assertEqual(c['viewed_objs'].count(), 2)        
        count = 20
        for obj_view in c['viewed_objs']:
            self.assertEqual(obj_view.object_id, count)
            self.assertEqual(obj_view.views, obj_view.object_id)
            count -= 1 

    def testRecentlyViewedForModel(self):   
        for obj in self.objs:
            ViewTracker.add_view_for(obj)        
            sleep(1)
        # Need some seperation between the view times

        t = Template('{% load popularity_tags %}{% recently_viewed_for_model popularity.TestObject as viewed_objs %}')
        c = Context({})
        t.render(c)       

        self.assertEqual(c['viewed_objs'].count(), POPULARITY_LISTSIZE)

        count = 20
        for obj_view in c['viewed_objs']:
            self.assertEqual(obj_view.object_id, count)
            count -= 1        

        t = Template('{% load popularity_tags %}{% recently_viewed_for_model popularity.TestObject as viewed_objs limit 2 %}')
        c = Context({})
        t.render(c)
    
        self.assertEqual(c['viewed_objs'].count(), 2)        
        count = 20
        for obj_view in c['viewed_objs']:
            self.assertEqual(obj_view.object_id, count)
            count -= 1

    def testRecentlyAddedForModel(self):
        TestObject.objects.all().delete()
        ViewTracker.objects.all().delete()
        self.objs = []
        for i in xrange(1,21):
            self.objs.append(TestObject.objects.create(pk=i, title='Obj %s' % i))
            sleep(1)
        # Need some seperation between the creation time

        t = Template('{% load popularity_tags %}{% recently_added_for_model popularity.TestObject as added_objs %}')
        c = Context({})
        t.render(c)       

        self.assertEqual(c['added_objs'].count(), POPULARITY_LISTSIZE)

        count = 20
        for obj_view in c['added_objs']:
            self.assertEqual(obj_view.object_id, count)
            count -= 1        

        t = Template('{% load popularity_tags %}{% recently_added_for_model popularity.TestObject as added_objs limit 2 %}')
        c = Context({})
        t.render(c)
    
        self.assertEqual(c['added_objs'].count(), 2)        
        count = 20
        for obj_view in c['added_objs']:
            self.assertEqual(obj_view.object_id, count)
            count -= 1
    
    def testViewTrack(self):
        ct = ContentType.objects.get_for_model(TestObject)
        for myobject in self.objs:
            t = Template('{% load popularity_tags %}{{ myobject|viewtrack }}')
            c = Context({'myobject' : myobject})
            res = t.render(c)
            
            self.assertEqual(res, 'add_view_for(%d,%d)' % (ct.pk, myobject.pk))
        
########NEW FILE########
__FILENAME__ = urls
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *

from views import add_view_for

urlpatterns = patterns('',
    url(r'^(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', add_view_for, name="popularity-add-view-for"),
)
########NEW FILE########
__FILENAME__ = views
# This file is part of django-popularity.
# 
# django-popularity: A generic view- and popularity tracking pluggable for Django. 
# Copyright (C) 2008-2010 Mathijs de Bruin
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse

from models import ViewTracker

def add_view_for(request, content_type_id, object_id):
    ct = ContentType.objects.get(pk=content_type_id)
    myobject = ct.get_object_for_this_type(pk=object_id)
    
    logging.debug('Adding view for %s through web.', myobject)
    
    ViewTracker.add_view_for(myobject)
    
    return HttpResponse()
    
########NEW FILE########
