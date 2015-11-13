__FILENAME__ = admin
from django.contrib import admin

from django.utils.translation import ugettext as _

from models import *

class LocationAdmin(admin.ModelAdmin):
    list_display = ('title', )
    
    prepopulated_fields = {"slug": ("title",)}
    
admin.site.register(Location, LocationAdmin)

class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'event_date', 'start_time', 'location', 'publish', 'calendar')
    list_display_links = ('title', )
    list_filter = ('event_date', 'publish', 'author', 'location', 'calendar')

    date_hierarchy = 'event_date'
    
    prepopulated_fields = {"slug": ("title",)}
    
    search_fields = ('title', 'location__title', 'author__username', 'author__first_name', 'author__last_name', 'calendar')        

    fieldsets =  ((None, {'fields': ['title', 'slug', 'event_date', 'start_time', 'end_time', 'location', 'description', 'calendar',]}),
                  (_('Advanced options'), {'classes' : ('collapse',),
                                           'fields'  : ('publish_date', 'publish', 'sites', 'author', 'allow_comments')}))
    
    # This is a dirty hack, this belongs inside of the model but defaults don't work on M2M
    def formfield_for_dbfield(self, db_field, **kwargs):
        """ Makes sure that by default all sites are selected. """
        if db_field.name == 'sites': # Check if it's the one you want
            kwargs.update({'initial': Site.objects.all()})
         
        return super(EventAdmin, self).formfield_for_dbfield(db_field, **kwargs)
    
admin.site.register(Event, EventAdmin)

admin.site.register(Calendar)

########NEW FILE########
__FILENAME__ = feeds
import logging

from datetime import datetime, timedelta

from django.contrib.syndication.feeds import Feed
from django.contrib.sites.models import Site

from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from models import Event

class EventFeed(Feed):
    title = _('%s agenda' % Site.objects.get_current())
    description = _('Upcoming events in the agenda.')
    
    def link(self):
        return reverse('agenda-index')
    
    def items(self):
        return Event.published.filter(event_date__gte=datetime.now() - timedelta(days=1))
    
    def item_pubdate(self, item):
        return item.publish_date
    

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from django.conf import settings

from django.contrib.auth.models import User

from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager

from django.contrib.sitemaps import ping_google

class Location(models.Model):
    class Meta:
        verbose_name = _('location')
        verbose_name_plural = _('locations')
        ordering = ('title',)
    
    def __unicode__(self):
        return self.title
        
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'), db_index=True)
    
    address = models.CharField(_('address'), max_length=255, blank=True)

class PublicationManager(CurrentSiteManager):
    def get_query_set(self):
        return super(CurrentSiteManager, self).get_query_set().filter(publish=True, publish_date__lte=datetime.now())

class Event(models.Model):
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        ordering = ['-event_date', '-start_time', '-title']
        get_latest_by = 'event_date'
        permissions = (("change_author", ugettext("Change author")),)
        unique_together = ("event_date", "slug")

    def __unicode__(self):
        return _("%(title)s on %(event_date)s") % { 'title'      : self.title,
                                                    'event_date' : self.event_date }

    @models.permalink                                               
    def get_absolute_url(self):
        return ('agenda-detail', (), {
                  'year'  : self.event_date.year, 
                  'month' : self.event_date.month, 
                  'day'   : self.event_date.day, 
                  'slug'  : self.slug })
        
    objects = models.Manager()
    on_site = CurrentSiteManager()
    published = PublicationManager()

    # Core fields
    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(_('slug'), db_index=True)
    
    event_date = models.DateField(_('date'))
    
    start_time = models.TimeField(_('start time'), blank=True, null=True)
    end_time = models.TimeField(_('end time'), blank=True, null=True)
    
    location = models.ForeignKey(Location, blank=True, null=True)

    description = models.TextField(_('description'))

    calendar = models.ForeignKey("Calendar", blank=True, null=True, related_name='events')

    # Extra fields
    add_date = models.DateTimeField(_('add date'),auto_now_add=True)
    mod_date = models.DateTimeField(_('modification date'), auto_now=True)
    
    author = models.ForeignKey(User, verbose_name=_('author'), db_index=True, blank=True, null=True)

    publish_date = models.DateTimeField(_('publication date'), default=datetime.now())
    publish = models.BooleanField(_('publish'), default=True)
    
    allow_comments = models.BooleanField(_('Allow comments'), default=True)

    sites = models.ManyToManyField(Site)
    
    def save(self):
        super(Event, self).save()
        if not settings.DEBUG:
            try:
                ping_google()
            except Exception:
                import logging
                logging.warn('Google ping on save did not work.')

class Calendar(models.Model):
    name = models.CharField(_('name'), max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = _('calendar')
        verbose_name_plural = _('calendars')

    def __unicode__(self):
        if self.name:
            return self.name
        return _("Unnamed Calendar")

########NEW FILE########
__FILENAME__ = sitemaps
from django.contrib.sitemaps import Sitemap

from models import Event

from django.contrib.comments.models import Comment

from django.conf import settings

class EventSitemap(Sitemap):
    changefreq = "daily"
    
    def items(self):
        return Event.published.all()
    
    def lastmod(self, obj):
        """ The Event 'changes' when there are newer comments, so check for that. """
        
        # Check for comments installation here, otherwise it all goes wrong.
        if 'django.contrib.comments' in settings.INSTALLED_APPS:
            if obj.allow_comments:
                try:
                    comment_date = Comment.objects.for_model(Event).filter(object_pk=obj.id).latest('submit_date').submit_date
                    return comment_date > obj.mod_date and comment_date or obj.mod_date
                except Comment.DoesNotExist:
                    pass
        
        return obj.mod_date
            

########NEW FILE########
__FILENAME__ = agenda
from django import template

from calendar import Calendar
import datetime

import re

register = template.Library()

import logging 

@register.tag(name="get_calendar")
def do_calendar(parser, token):
    syntax_help = "syntax should be \"get_calendar for <month> <year> as <var_name>\""
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments, %s" % (token.contents.split()[0], syntax_help)
    m = re.search(r'for (.*?) (.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments, %s" % (tag_name, syntax_help)
    
    return GetCalendarNode(*m.groups())

class GetCalendarNode(template.Node):
    def __init__(self, month, year, var_name):
        self.year = template.Variable(year)
        self.month = template.Variable(month)
        self.var_name = var_name
        
    def render(self, context):
        mycal = Calendar()
        context[self.var_name] = mycal.monthdatescalendar(int(self.year.resolve(context)), int(self.month.resolve(context)))
        
        return ''
        
class IfInNode(template.Node):
    '''
    Like {% if %} but checks for the first value being in the second value (if a list). Does not work if the second value is not a list.
    '''
    def __init__(self, var1, var2, nodelist_true, nodelist_false, negate):
        self.var1, self.var2 = var1, var2
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.negate = negate

    def __str__(self):
        return "<IfNode>"

    def render(self, context):
        val1 = template.resolve_variable(self.var1, context)
        val2 = template.resolve_variable(self.var2, context)
        try:
            val2 = list(val2)
            if (self.negate and datetime.datetime(*val1.timetuple()[:3]) not in val2) or (not self.negate and datetime.datetime(*val1.timetuple()[:3]) in val2):
                return self.nodelist_true.render(context)
            return self.nodelist_false.render(context)
        except TypeError:
            return self.nodelist_false.render(context)

def ifin(parser, token, negate):
    bits = token.contents.split()
    if len(bits) != 3:
        raise template.TemplateSyntaxError, "%r takes two arguments" % bits[0]
    end_tag = 'end' + bits[0]
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else: nodelist_false = template.NodeList()
    return IfInNode(bits[1], bits[2], nodelist_true, nodelist_false, negate)

register.tag('ifdayin', lambda parser, token: ifin(parser, token, False))


########NEW FILE########
__FILENAME__ = next_previous
import logging

from django import template

register = template.Library()

@register.tag(name="previous")
def do_previous(parser, token):
    # previous in <list> from <object> as <previous_object> 
    bits = token.contents.split()
    if len(bits) != 7:
        raise template.TemplateSyntaxError, "%r takes six arguments" % bits[0]
        
    return PreviousNode(bits[2], bits[4], bits[6])

def get_previous(object_list, object_current):
    logging.debug('Finding previous of %s in %s' % (object_current, object_list))
    assert object_list.contains(object_current)

    index = object_list.index(object_current)    

    if index == 0:
        return None
    
    return object_list[index-1]
    
def get_next(object_list, object_current):
    logging.debug('Finding next of %s in %s' % (object_current, object_list))
    assert object_list.contains(object_current)

    index = object_list.index(object_current)    
    
    if index == len(object_list)-1:
        return None

    return object_list[index+1]
    
class PreviousNode(template.Node):
    def __init__(self, object_list, object_current, previous_name):
        self.object_list = template.Variable(object_list)
        self.object_current = template.Variable(object_current)
        self.previous_name = previous_name

    def render(self, context):
        logging.debug('blaat')
        logging.debug(self.object_list)

        object_list = self.object_list.resolve(context)
        object_current = self.object_current.resolve(context)
    
        from django.db.models.query import QuerySet
        logging.debug(object_list)
        if type(QuerySet()) == type(object_list):
            # This is efficient, but very experimental
            if len(object_list.query.order_by) == 1:
                if object_list.query.order_by[0][0] == '-':
                    date_field = object_list.query.order_by[0][1:]
                    prev_getter = getattr(object_current, 'get_previous_by_%s' % date_field, None)
                    if prev_getter:
                        object_previous = prev_getter()
                else:
                    date_field = object_list.query.order_by[0]
                    prev_getter = getattr(object_current, 'get_next_by_%s' % date_field, None)
                    if prev_getter:
                        object_previous = prev_getter()
                        
            previous_id = get_previous(object_list.values_list('id', flat=True), object_current.id)
            
            object_previous = object_list.get(id=previous_id)
        else:
            object_previous = get_previous(list(object_list), object_current)
            
        context[self.previous_name] = object_previous
        return ''
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
#from django.conf import settings

from models import *

info_dict = {
    'queryset'                  : Event.published.all(),
    'date_field'                : 'event_date',
    'template_object_name'      : 'event',
}

urlpatterns = patterns('agenda.views.date_based',
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$', 'object_detail', info_dict,  name='agenda-detail'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',                  'archive',       info_dict,  name='agenda-archive-day'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$',                                   'archive',       info_dict,  name='agenda-archive-month'),
    url(r'^(?P<year>\d{4})/$',                                                      'archive',       info_dict,  name='agenda-archive-year'),
    url(r'^$',                                                                      'index',         info_dict,  name='agenda-index'),
)

ical_dict = {
    'queryset'                  : info_dict['queryset'],
    'date_field'                : info_dict['date_field'],
    'ical_filename'              : 'calendar.ics',
    'last_modified_field'       : 'mod_date',
    'location_field'            : 'location',
    'start_time_field'          : 'start_time',
    'end_time_field'            : 'end_time',
}

urlpatterns += patterns('agenda.views.vobject_django',
    url(r'^calendar.ics$',                                                          'icalendar',     ical_dict,  name='agenda-icalendar'),
)
########NEW FILE########
__FILENAME__ = date_based
import logging 

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from django.http import Http404, HttpResponse
from django.template import loader, RequestContext

def process_context(context, extra_context):
    for key, value in extra_context.items():
        if callable(value):
            context[key] = value()
        else:
            context[key] = value

def get_object_context(queryset, date_field, year, month=None, day=None, slug=None):
    """ Fetch relevant objects """
    
    logging.debug('Fetching context and objects for %s %s %s of %s.' % (year, month, day, date_field))
    
    objects = queryset.order_by('%s' % date_field)
    
    object_context = { 'years' : objects.dates(date_field, 'year') }
    
    if year:
        year = int(year)
        objects = objects.filter(**{'%s__year' % date_field : year })
    
        object_context.update({'months'         : objects.dates(date_field, 'month'),
                               'year'           : year,
                               'previous_year'  : year-1,
                               'next_year'      : year+1,
                               'days'           : objects.dates(date_field, 'day') })
    logging.debug('Returning context %s' % object_context)

    if month:
        month = int(month)
        objects = objects.filter(**{'%s__month' % date_field : month })
        
        object_context.update({'days'           : objects.dates(date_field, 'day'),
                               'month'          : datetime(year, month, 1),
                               'next_month'     : datetime(year, month, 1) + relativedelta(months=1),
                               'previous_month' : datetime(year, month, 1) + relativedelta(months=-1)})
    logging.debug('Returning context %s' % object_context)

    if day:
        day = int(day)
        objects = objects.filter(**{'%s__day' % date_field : day })
        
        object_context.update({'day'           : datetime(year, month, day),
                               'next_day'      : datetime(year, month, day) + relativedelta(days=1),
                               'previous_day'  : datetime(year, month, day) + relativedelta(days=-1)})
    
    logging.debug('Returning objects %s' % objects)
    logging.debug('Returning context %s' % object_context)

    if slug:
        objects = objects.filter(slug__contains=slug)
    logging.debug('Returning context %s' % object_context)
    return objects, object_context
    
def get_next_object(my_object, date_field):
    get_next = getattr(my_object, 'get_next_by_%s' % date_field)
    try:
        return get_next()
    except my_object.DoesNotExist:
        return None

def get_previous_object(my_object, date_field):
    get_previous = getattr(my_object, 'get_previous_by_%s' % date_field)
    try:
        return get_previous()
    except my_object.__class__.DoesNotExist:
        return None

def archive(request, queryset, date_field, 
            year, month=None, day=None, 
            template_name=None, template_object_name='object', template_loader=loader,
            num_objects=5, extra_context=None, allow_empty=True,
            mimetype=None, context_processors=None):

    # Get our model from the queryset
    model = queryset.model

    # Process parameters
    if not extra_context:
        extra_context = {}
    if not template_name:
        template_name = "%s/%s_archive.html" % (model._meta.app_label, model._meta.object_name.lower())

    # Get relevant context (objects and dates)
    objects, object_context = get_object_context(queryset, date_field, year, month, day)
    if not objects and not allow_empty:
        raise Http404, "No %s available" % model._meta.verbose_name
    
    logging.debug('Objects %s' % objects[:num_objects])
    logging.debug('Context object list name %s ' % ('%s_list' % template_object_name))
    object_context.update({ '%s_list' % template_object_name : objects[:num_objects] })        

    # Get a template, RequestContext and render
    t = template_loader.get_template(template_name)
    c = RequestContext(request, object_context, context_processors)
    
    process_context(c, extra_context)

    return HttpResponse(t.render(c), mimetype=mimetype)

def index(request, queryset, date_field, 
          template_name=None, template_object_name='object', template_loader=loader,
          num_objects=5, extra_context=None,
          mimetype=None, context_processors=None):
    
    now = datetime.now()      
    queryset = queryset.filter(event_date__gte=now - timedelta(days=1))
    logging.debug(queryset)
    return archive(request, queryset, date_field, 
                   None, None, None, 
                   template_name, template_object_name, template_loader,
                   num_objects, extra_context, True,
                   mimetype, context_processors)

def object_detail(request, queryset, date_field, 
                  year, month, day, slug, 
                  template_name=None, template_object_name='object', template_loader=loader,
                  extra_context=None,
                  mimetype=None, context_processors=None):
    # Get our model from the queryset
    model = queryset.model

    # Process parameters
    if not extra_context:
      extra_context = {}
    if not template_name:
      template_name = "%s/%s_archive.html" % (model._meta.app_label, model._meta.object_name.lower())

    # Get relevant context (objects and dates)
    objects, object_context = get_object_context(queryset, date_field, year, month, day, slug)
    if not objects:
      raise Http404, "No %s available" % model._meta.verbose_name

    my_object = objects[0]
    object_context.update({ template_object_name : my_object,
                          'next_%s' % template_object_name : get_next_object(my_object, date_field),
                          'previous_%s' % template_object_name : get_previous_object(my_object, date_field) })        

    # Get a template, RequestContext and render
    t = template_loader.get_template(template_name)
    c = RequestContext(request, object_context, context_processors)

    process_context(c, extra_context)

    return HttpResponse(t.render(c), mimetype=mimetype)

########NEW FILE########
__FILENAME__ = vobject_django
from datetime import datetime, timedelta

from django.utils.html import strip_tags
from django.http import HttpResponse
from django.utils.tzinfo import FixedOffset

import vobject

def icalendar(request, queryset, date_field, ical_filename, 
              title_field='title', description_field='description',
              last_modified_field=None, location_field=None,
              start_time_field=None, end_time_field=None,
              num_objects=15, extra_context=None,
              mimetype=None, context_processors=None):
    
    now = datetime.now()      
    queryset = queryset.filter(event_date__gte=now - timedelta(days=1))
    
    cal = vobject.iCalendar()
    utc = vobject.icalendar.utc
    
    cal.add('method').value = 'PUBLISH'  # IE/Outlook needs this
    
    # Timezone code borrowed from 
    now = datetime.now()
    utcnow = datetime.utcnow()
    # Must always subtract smaller time from larger time here.
    if utcnow > now:
        sign = -1
        tzDifference = (utcnow - now)
    else:
        sign = 1
        tzDifference = (now - utcnow)
    
    # Round the timezone offset to the nearest half hour.
    tzOffsetMinutes = sign * ((tzDifference.seconds / 60 + 15) / 30) * 30
    tzOffset = timedelta(minutes=tzOffsetMinutes)
    
    #cal.add('vtimezone').value = FixedOffset(tzOffset)

    mytz = FixedOffset(tzOffset)
    
    for event in queryset:
        vevent = cal.add('vevent')

        vevent.add('summary').value = strip_tags(getattr(event, title_field))
        vevent.add('description').value = strip_tags(getattr(event, description_field))

        start_time = getattr(event, start_time_field, None)
        if start_time:
            start_date = datetime.combine(getattr(event, date_field), event.start_time)
            
            end_time = getattr(event, end_time_field, None)
            if end_time:
                end_date = datetime.combine(getattr(event, date_field), event.end_time)
                vevent.add('dtend').value = end_date.replace(tzinfo = mytz)
            
        else:
            start_date = getattr(event, date_field)
        
        
        vevent.add('dtstart').value = start_date.replace(tzinfo = mytz)
        
        last_modified = getattr(event, last_modified_field, None)
        if last_modified:
            vevent.add('last-modified').value = last_modified.replace(tzinfo = mytz)
            
        location = getattr(event, location_field, None)
        if location:
            vevent.add('location').value = strip_tags(location)

    icalstream = cal.serialize()
    response = HttpResponse(icalstream, mimetype='text/calendar')
    response['Filename'] = ical_filename  # IE needs this
    response['Content-Disposition'] = 'attachment; filename=%s' % ical_filename

    return response
########NEW FILE########
