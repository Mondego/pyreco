__FILENAME__ = settings
import os
import sys
try:
    # dateutil is an absolute requirement
    import dateutil
except ImportError:
    raise ImportError(
        'django-swingtime requires the "dateutil" package '
        '(http://labix.org/python-dateutil)'
    )

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([
    os.path.abspath('..'),    # relative path to karate app
    os.path.abspath('../..'), # relative location of swingtime app
])

DEBUG = TEMPLATE_DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'karate.db',
    }
}

TIME_ZONE = 'America/New_York'
SITE_ID = 1
USE_I18N = True

MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
STATIC_URL = '/static/'

SECRET_KEY = 'j#_e3y&h=a4)hrmj=)bqo@$6qoz6(hrf9wz@uqq@uy*0uzl#ew'
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'swingtime.context_processors.current_datetime',
)

ROOT_URLCONF = 'demo_site.urls'
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.staticfiles',
    
    'swingtime',
    'karate',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

SWINGTIME_SETTINGS_MODULE = 'demo_site.swingtime_settings'

try:
    import django_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS += ('django_extensions',)

try:
    from local_settings import *
except ImportError:
    pass



########NEW FILE########
__FILENAME__ = swingtime_settings
import datetime
TIMESLOT_START_TIME = datetime.time(14)
TIMESLOT_END_TIME_DURATION = datetime.timedelta(hours=6.5)

########NEW FILE########
__FILENAME__ = urls
import os
from django.conf import settings
from django.contrib import admin
from django.views.static import serve
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView, RedirectView

admin.autodiscover()
site_dir = os.path.dirname(settings.PROJECT_DIR)
doc_root = os.path.join(os.path.dirname(site_dir), 'docs/build/html')

urlpatterns = patterns('',
    url(r'^$',               TemplateView.as_view(template_name='intro.html'), name='demo-home'),
    (r'^karate/',            include('karate.urls')),
    (r'^admin/docs/',        include('django.contrib.admindocs.urls')),
    (r'^admin/',             include(admin.site.urls)),
    (r'^docs/?$',            RedirectView.as_view(url='/docs/index.html')),
    (r'^docs/(?P<path>.*)$', serve, dict(document_root=doc_root, show_indexes=False))
)

if settings.DEBUG:
    data = dict(document_root=settings.MEDIA_ROOT, show_indexes=True)
    urlpatterns += patterns ('',
        (r'^media/(?P<path>.*)$', serve, data),
    )

########NEW FILE########
__FILENAME__ = wsgi
import os, sys
sys.stdout = sys.stderr
sys.path.extend(['/var/www/swingtime'])
os.environ['DJANGO_SETTINGS_MODULE'] = 'demo.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()


########NEW FILE########
__FILENAME__ = loaddemo
'''
================================================================================
Welcome to the django-swingtime demo project. This project's' is theme is a
Karate dojo and the database will be pre-populated with some data relative to
today's date. 
================================================================================
'''
from django.core.management import call_command
from django.core.management.base import NoArgsCommand
from datetime import datetime, date, time, timedelta
from django.conf import settings
from django.db.models import signals
from dateutil import rrule
from swingtime import models as swingtime


#-------------------------------------------------------------------------------
def create_sample_data():
    
    # Create the studio's event types
    ets = dict((
        (abbr, swingtime.EventType.objects.create(abbr=abbr, label=label))
        for abbr, label in (
            ('prv',  'Private Lesson'),
            ('bgn',  'Beginner Class'),
            ('adv',  'Advanced Class'),
            ('bbc',  'Black Belt Class'),
            ('spr',  'Sparring'),
            ('open', 'Open Dojo'),
            ('spc',  'Special Event'),
        )
    ))
    print __doc__
    print 'Created event types: %s' % (
        ', '.join(['%s' % et for et in swingtime.EventType.objects.all()]),
    )
    
    now = datetime.now()
    
    # create a single occurrence event
    evt = swingtime.create_event(
        'Grand Opening',
        ets['spc'],
        description='Open house',
        start_time=datetime.combine(now.date(), time(16)),
        end_time=datetime.combine(now.date(), time(18)),
        note='Free tea, sushi, and sake'
    )
    print 'Created event "%s" with %d occurrences' % (evt, evt.occurrence_set.count())
    
    # create an event with multiple occurrences by fixed count
    evt = swingtime.create_event(
        'Beginner Class',
        ets['bgn'],
        description='Open to all white and yellow belts',
        start_time=datetime.combine(now.date(), time(19)),
        count=30,
        byweekday=(rrule.MO, rrule.WE, rrule.FR)
    )
    print 'Created event "%s" with %d occurrences' % (evt, evt.occurrence_set.count())

    # create an event with multiple occurrences by ending date (until)
    evt = swingtime.create_event(
        'Advance Class',
        ets['adv'],
        description='Open to all green and brown belts',
        start_time=datetime.combine(now.date(), time(18)),
        until=now + timedelta(days=+70),
        byweekday=(rrule.MO, rrule.WE, rrule.FR)
    )
    print 'Created event "%s" with %d occurrences' % (evt, evt.occurrence_set.count())

    # create an event with multiple occurrences by fixed count on monthly basis
    evt = swingtime.create_event(
        'Black Belt Class',
        ets['bbc'],
        description='Open to all black belts',
        start_time=datetime.combine(now.date(), time(18, 30)),
        end_time=datetime.combine(now.date(), time(20, 30)),
        count=6,
        freq=rrule.MONTHLY,
        byweekday=(rrule.TH(+1), rrule.TH(+3))
    )
    print 'Created event "%s" with %d occurrences' % (evt, evt.occurrence_set.count())

    # create an event with multiple occurrences and alternate intervale
    evt = swingtime.create_event(
        'Open Dojo',
        ets['open'],
        description='Open to all students',
        start_time=datetime.combine(now.date(), time(12)),
        end_time=datetime.combine(now.date(), time(16)),
        interval=2,
        count=6,
        byweekday=(rrule.SU)
    )
    print 'Created event "%s" with %d occurrences' % (evt, evt.occurrence_set.count())
    print



#===============================================================================
class Command(NoArgsCommand):
    help = 'Run the swingtime demo. If an existing demo database exists, it will recreated.'
    
    #---------------------------------------------------------------------------
    def handle_noargs(self, **options):
        import os
        
        dbpath = os.path.join(settings.PROJECT_DIR, settings.DATABASES['default']['NAME'])
        if os.path.exists(dbpath):
            print 'Removing', dbpath
            os.remove(dbpath)

        call_command('syncdb', noinput=True)
        create_sample_data()


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView

from karate import views

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='karate.html'), name='karate-home'),
    url(r'^swingtime/events/type/([^/]+)/$', views.event_type, name='karate-event'),
    (r'^swingtime/', include('swingtime.urls')),
)


########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from django.template.context import RequestContext
from django.shortcuts import get_object_or_404, render_to_response

from swingtime import models as swingtime

#-------------------------------------------------------------------------------
def event_type(request, abbr):
    event_type = get_object_or_404(swingtime.EventType, abbr=abbr)
    now = datetime.now()
    occurrences = swingtime.Occurrence.objects.filter(
        event__event_type=event_type,
        start_time__gte=now,
        start_time__lte=now+timedelta(days=+30)
    )
    return render_to_response(
        'karate/upcoming_by_event_type.html', 
        dict(occurrences=occurrences, event_type=event_type),
        context_instance=RequestContext(request)
    )

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_site.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Swingtime documentation build configuration file, created by
# sphinx-quickstart on Fri Dec 12 18:48:37 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Swingtime'
copyright = u'2013, David Krauth'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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


# Options for HTML output
# -----------------------

html_theme = "nature"

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'default.css'

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
# html_static_path = ['_static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Swingtimedoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Swingtime.tex', ur'Swingtime Documentation',
   ur'David Krauth', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = admin
from django.contrib.contenttypes import generic
from django.contrib import admin
from swingtime.models import *

#===============================================================================
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('label', 'abbr')


#===============================================================================
class NoteAdmin(admin.ModelAdmin):
    list_display = ('note', 'created')


#===============================================================================
class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 1


#===============================================================================
class EventNoteInline(generic.GenericTabularInline):
    model = Note
    extra = 1


#===============================================================================
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'description')
    list_filter = ('event_type', )
    search_fields = ('title', 'description')
    inlines = [EventNoteInline, OccurrenceInline]


admin.site.register(Event, EventAdmin)
admin.site.register(EventType, EventTypeAdmin)
admin.site.register(Note, NoteAdmin)

########NEW FILE########
__FILENAME__ = swingtime_settings
import datetime

# A "strftime" string for formatting start and end time selectors in forms
TIMESLOT_TIME_FORMAT = '%I:%M %p'

# Used for creating start and end time form selectors as well as time slot grids.
# Value should be datetime.timedelta value representing the incremental 
# differences between temporal options
TIMESLOT_INTERVAL = datetime.timedelta(minutes=15)

# A datetime.time value indicting the starting time for time slot grids and form
# selectors
TIMESLOT_START_TIME = datetime.time(9)

# A datetime.timedelta value indicating the offset value from 
# TIMESLOT_START_TIME for creating time slot grids and form selectors. The for
# using a time delta is that it possible to span dates. For instance, one could
# have a starting time of 3pm (15:00) and wish to indicate a ending value 
# 1:30am (01:30), in which case a value of datetime.timedelta(hours=10.5) 
# could be specified to indicate that the 1:30 represents the following date's
# time and not the current date.
TIMESLOT_END_TIME_DURATION = datetime.timedelta(hours=+8)

# Indicates a minimum value for the number grid columns to be shown in the time
# slot table.
TIMESLOT_MIN_COLUMNS = 4

# Indicate the default length in time for a new occurrence, specifed by using
# a datetime.timedelta object
DEFAULT_OCCURRENCE_DURATION = datetime.timedelta(hours=+1)

# If not None, passed to the calendar module's setfirstweekday function.
CALENDAR_FIRST_WEEKDAY = 6
########NEW FILE########
__FILENAME__ = context_processors
from datetime import datetime

#-------------------------------------------------------------------------------
def current_datetime(request):
    return dict(current_datetime=datetime.now())
########NEW FILE########
__FILENAME__ = forms
'''
Convenience forms for adding and updating ``Event`` and ``Occurrence``s.

'''
from datetime import datetime, date, time, timedelta

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.forms.extras.widgets import SelectDateWidget

from dateutil import rrule
from swingtime.conf import settings as swingtime_settings
from swingtime import utils
from swingtime.models import *

WEEKDAY_SHORT = (
    (7, _(u'Sun')),
    (1, _(u'Mon')),
    (2, _(u'Tue')),
    (3, _(u'Wed')),
    (4, _(u'Thu')),
    (5, _(u'Fri')),
    (6, _(u'Sat'))
)

WEEKDAY_LONG = (
    (7, _(u'Sunday')),
    (1, _(u'Monday')),
    (2, _(u'Tuesday')),
    (3, _(u'Wednesday')),
    (4, _(u'Thursday')),
    (5, _(u'Friday')),
    (6, _(u'Saturday'))
)

MONTH_LONG = (
    (1,  _(u'January')),
    (2,  _(u'February')),
    (3,  _(u'March')),
    (4,  _(u'April')),
    (5,  _(u'May')),
    (6,  _(u'June')),
    (7,  _(u'July')),
    (8,  _(u'August')),
    (9,  _(u'September')),
    (10, _(u'October')),
    (11, _(u'November')),
    (12, _(u'December')),
)

MONTH_SHORT = (
    (1,  _(u'Jan')),
    (2,  _(u'Feb')),
    (3,  _(u'Mar')),
    (4,  _(u'Apr')),
    (5,  _(u'May')),
    (6,  _(u'Jun')),
    (7,  _(u'Jul')),
    (8,  _(u'Aug')),
    (9,  _(u'Sep')),
    (10, _(u'Oct')),
    (11, _(u'Nov')),
    (12, _(u'Dec')),
)


ORDINAL = (
    (1,  _(u'first')),
    (2,  _(u'second')),
    (3,  _(u'third')),
    (4,  _(u'fourth')),
    (-1, _(u'last'))
)

FREQUENCY_CHOICES = (
    (rrule.DAILY,   _(u'Day(s)')),
    (rrule.WEEKLY,  _(u'Week(s)')),
    (rrule.MONTHLY, _(u'Month(s)')),
    (rrule.YEARLY,  _(u'Year(s)')),
)

REPEAT_CHOICES = (
    ('count', _(u'By count')),
    ('until', _(u'Until date')),
)

ISO_WEEKDAYS_MAP = (
    None,
    rrule.MO,
    rrule.TU,
    rrule.WE,
    rrule.TH,
    rrule.FR,
    rrule.SA,
    rrule.SU
)

MINUTES_INTERVAL = swingtime_settings.TIMESLOT_INTERVAL.seconds // 60
SECONDS_INTERVAL = utils.time_delta_total_seconds(swingtime_settings.DEFAULT_OCCURRENCE_DURATION)

#-------------------------------------------------------------------------------
def timeslot_options(
    interval=swingtime_settings.TIMESLOT_INTERVAL,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_delta=swingtime_settings.TIMESLOT_END_TIME_DURATION,
    fmt=swingtime_settings.TIMESLOT_TIME_FORMAT
):
    '''
    Create a list of time slot options for use in swingtime forms.
    
    The list is comprised of 2-tuples containing a 24-hour time value and a 
    12-hour temporal representation of that offset.
    
    '''
    dt = datetime.combine(date.today(), time(0))
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_delta
    options = []

    while dtstart <= dtend:
        options.append((str(dtstart.time()), dtstart.strftime(fmt)))
        dtstart += interval
    
    return options

#-------------------------------------------------------------------------------
def timeslot_offset_options(
    interval=swingtime_settings.TIMESLOT_INTERVAL,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_delta=swingtime_settings.TIMESLOT_END_TIME_DURATION,
    fmt=swingtime_settings.TIMESLOT_TIME_FORMAT
):
    '''
    Create a list of time slot options for use in swingtime forms.
    
    The list is comprised of 2-tuples containing the number of seconds since the
    start of the day and a 12-hour temporal representation of that offset.
    
    '''
    dt = datetime.combine(date.today(), time(0))
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_delta
    options = []

    delta = utils.time_delta_total_seconds(dtstart - dt)
    seconds = utils.time_delta_total_seconds(interval)
    while dtstart <= dtend:
        options.append((delta, dtstart.strftime(fmt)))
        dtstart += interval
        delta += seconds
    
    return options

default_timeslot_options = timeslot_options()
default_timeslot_offset_options = timeslot_offset_options()


#===============================================================================
class MultipleIntegerField(forms.MultipleChoiceField):
    '''
    A form field for handling multiple integers.
    
    '''
    
    #---------------------------------------------------------------------------
    def __init__(self, choices, size=None, label=None, widget=None):
        if widget is None:
            widget = forms.SelectMultiple(attrs={'size' : size or len(choices)})
        super(MultipleIntegerField, self).__init__(
            required=False,
            choices=choices,
            label=label,
            widget=widget,
        )

    #---------------------------------------------------------------------------
    def clean(self, value):
        return [int(i) for i in super(MultipleIntegerField, self).clean(value)]


#===============================================================================
class SplitDateTimeWidget(forms.MultiWidget):
    '''
    A Widget that splits datetime input into a SelectDateWidget for dates and
    Select widget for times.
    
    '''
    #---------------------------------------------------------------------------
    def __init__(self, attrs=None):
        widgets = (
            SelectDateWidget(attrs=attrs), 
            forms.Select(choices=default_timeslot_options, attrs=attrs)
        )
        super(SplitDateTimeWidget, self).__init__(widgets, attrs)

    #---------------------------------------------------------------------------
    def decompress(self, value):
        if value:
            return [value.date(), value.time().replace(microsecond=0)]
        
        return [None, None]


#===============================================================================
class MultipleOccurrenceForm(forms.Form):
    day = forms.DateField(
        label=_(u'Date'),
        initial=date.today,
        widget=SelectDateWidget()
    )
    
    start_time_delta = forms.IntegerField(
        label=_(u'Start time'),
        widget=forms.Select(choices=default_timeslot_offset_options)
    )
    
    end_time_delta = forms.IntegerField(
        label=_(u'End time'),
        widget=forms.Select(choices=default_timeslot_offset_options)
    )

    # recurrence options
    repeats = forms.ChoiceField(
        choices=REPEAT_CHOICES,
        initial='count',
        label=_(u'Occurrences'),
        widget=forms.RadioSelect()
    )

    count = forms.IntegerField(
        label=_(u'Total Occurrences'),
        initial=1,
        required=False,
        widget=forms.TextInput(attrs=dict(size=2, max_length=2))
    )

    until = forms.DateField(
        required=False,
        initial=date.today,
        widget=SelectDateWidget()
    )
    
    freq = forms.IntegerField(
        label=_(u'Frequency'),
        initial=rrule.WEEKLY,
        widget=forms.RadioSelect(choices=FREQUENCY_CHOICES),
    )

    interval = forms.IntegerField(
        required=False,
        initial='1',
        widget=forms.TextInput(attrs=dict(size=3, max_length=3))
    )
    
    # weekly options
    week_days = MultipleIntegerField(
        WEEKDAY_SHORT, 
        label=_(u'Weekly options'),
        widget=forms.CheckboxSelectMultiple
    )
    
    # monthly  options
    month_option = forms.ChoiceField(
        choices=(('on',_(u'On the')), ('each',_(u'Each:'))),
        initial='each',
        widget=forms.RadioSelect(),
        label=_(u'Monthly options')
    )
    
    month_ordinal = forms.IntegerField(widget=forms.Select(choices=ORDINAL))
    month_ordinal_day = forms.IntegerField(widget=forms.Select(choices=WEEKDAY_LONG))
    each_month_day = MultipleIntegerField(
        [(i,i) for i in range(1,32)], 
        widget=forms.CheckboxSelectMultiple
    )
    
    # yearly options
    year_months = MultipleIntegerField(
        MONTH_SHORT, 
        label=_(u'Yearly options'),
        widget=forms.CheckboxSelectMultiple
    )
    
    is_year_month_ordinal = forms.BooleanField(required=False)
    year_month_ordinal = forms.IntegerField(widget=forms.Select(choices=ORDINAL))
    year_month_ordinal_day = forms.IntegerField(widget=forms.Select(choices=WEEKDAY_LONG))
    
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(MultipleOccurrenceForm, self).__init__(*args, **kws)
        dtstart = self.initial.get('dtstart', None)
        if dtstart:
            dtstart = dtstart.replace(
                minute=((dtstart.minute // MINUTES_INTERVAL) * MINUTES_INTERVAL),
                second=0, 
                microsecond=0
            )

            weekday = dtstart.isoweekday()
            ordinal = dtstart.day // 7
            ordinal = u'%d' % (-1 if ordinal > 3 else ordinal + 1,)
            offset = (dtstart - datetime.combine(dtstart.date(), time(0))).seconds
            
            self.initial.setdefault('day', dtstart)
            self.initial.setdefault('week_days', u'%d' % weekday)
            self.initial.setdefault('month_ordinal', ordinal)
            self.initial.setdefault('month_ordinal_day', u'%d' % weekday)
            self.initial.setdefault('each_month_day', [u'%d' % dtstart.day])
            self.initial.setdefault('year_months', [u'%d' % dtstart.month])
            self.initial.setdefault('year_month_ordinal', ordinal)
            self.initial.setdefault('year_month_ordinal_day', u'%d' % weekday)
            self.initial.setdefault('start_time_delta', u'%d' % offset)
            self.initial.setdefault('end_time_delta', u'%d' % (offset + SECONDS_INTERVAL,))

    #---------------------------------------------------------------------------
    def clean(self):
        day = datetime.combine(self.cleaned_data['day'], time(0))
        self.cleaned_data['start_time'] = day + timedelta(
            seconds=self.cleaned_data['start_time_delta']
        )
        
        self.cleaned_data['end_time'] = day + timedelta(
            seconds=self.cleaned_data['end_time_delta']
        )
        
        return self.cleaned_data

    #---------------------------------------------------------------------------
    def save(self, event):
        if self.cleaned_data['repeats'] == 'no':
            params = {}
        else:
            params = self._build_rrule_params()

        event.add_occurrences(
            self.cleaned_data['start_time'], 
            self.cleaned_data['end_time'],
            **params
        )

        return event

    #---------------------------------------------------------------------------
    def _build_rrule_params(self):
        iso = ISO_WEEKDAYS_MAP
        data = self.cleaned_data
        params = dict(
            freq=data['freq'],
            interval=data['interval'] or 1
        )
        
        if self.cleaned_data['repeats'] == 'count':
            params['count'] = data['count']
        elif self.cleaned_data['repeats'] == 'until':
            params['until'] = data['until']

        if params['freq'] == rrule.WEEKLY:
            params['byweekday'] = [iso[n] for n in data['week_days']]

        elif params['freq'] == rrule.MONTHLY:
            if 'on' == data['month_option']:
                ordinal = data['month_ordinal']
                day = iso[data['month_ordinal_day']]
                params['byweekday'] = day(ordinal)
            else:
                params['bymonthday'] = data['each_month_day']

        elif params['freq'] == rrule.YEARLY:
            params['bymonth'] = data['year_months']
            if data['is_year_month_ordinal']:
                ordinal = data['year_month_ordinal']
                day = iso[data['year_month_ordinal_day']]
                params['byweekday'] = day(ordinal)
                
        elif params['freq'] != rrule.DAILY:
            raise NotImplementedError(_(u'Unknown interval rule %s') % params['freq'])

        return params


#===============================================================================
class EventForm(forms.ModelForm):
    '''
    A simple form for adding and updating Event attributes
    
    '''
    
    #===========================================================================
    class Meta:
        model = Event
        
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(EventForm, self).__init__(*args, **kws)
        self.fields['description'].required = False


#===============================================================================
class SingleOccurrenceForm(forms.ModelForm):
    '''
    A simple form for adding and updating single Occurrence attributes
    
    '''

    start_time = forms.DateTimeField(widget=SplitDateTimeWidget)
    end_time = forms.DateTimeField(widget=SplitDateTimeWidget)
    
    #===========================================================================
    class Meta:
        model = Occurrence
        


########NEW FILE########
__FILENAME__ = models
from datetime import datetime, date, timedelta

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

from dateutil import rrule

__all__ = (
    'Note',
    'EventType',
    'Event',
    'Occurrence',
    'create_event'
)

#===============================================================================
class Note(models.Model):
    '''
    A generic model for adding simple, arbitrary notes to other models such as
    ``Event`` or ``Occurrence``.
    
    '''
    note = models.TextField(_('note'))
    created = models.DateTimeField(_('created'), auto_now_add=True)

    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField(_('object id'))
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    #===========================================================================
    class Meta:
        verbose_name = _('note')
        verbose_name_plural = _('notes')
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.note


#===============================================================================
class EventType(models.Model):
    '''
    Simple ``Event`` classifcation.
    
    '''
    abbr = models.CharField(_(u'abbreviation'), max_length=4, unique=True)
    label = models.CharField(_('label'), max_length=50)

    #===========================================================================
    class Meta:
        verbose_name = _('event type')
        verbose_name_plural = _('event types')
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.label


#===============================================================================
class Event(models.Model):
    '''
    Container model for general metadata and associated ``Occurrence`` entries.
    '''
    title = models.CharField(_('title'), max_length=32)
    description = models.CharField(_('description'), max_length=100)
    event_type = models.ForeignKey(EventType, verbose_name=_('event type'))
    notes = generic.GenericRelation(Note, verbose_name=_('notes'))

    #===========================================================================
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        ordering = ('title', )
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.title

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-event', [str(self.id)])

    #---------------------------------------------------------------------------
    def add_occurrences(self, start_time, end_time, **rrule_params):
        '''
        Add one or more occurences to the event using a comparable API to 
        ``dateutil.rrule``. 
        
        If ``rrule_params`` does not contain a ``freq``, one will be defaulted
        to ``rrule.DAILY``.
        
        Because ``rrule.rrule`` returns an iterator that can essentially be
        unbounded, we need to slightly alter the expected behavior here in order
        to enforce a finite number of occurrence creation.
        
        If both ``count`` and ``until`` entries are missing from ``rrule_params``,
        only a single ``Occurrence`` instance will be created using the exact
        ``start_time`` and ``end_time`` values.
        '''
        rrule_params.setdefault('freq', rrule.DAILY)
        
        if 'count' not in rrule_params and 'until' not in rrule_params:
            self.occurrence_set.create(start_time=start_time, end_time=end_time)
        else:
            delta = end_time - start_time
            for ev in rrule.rrule(dtstart=start_time, **rrule_params):
                self.occurrence_set.create(start_time=ev, end_time=ev + delta)

    #---------------------------------------------------------------------------
    def upcoming_occurrences(self):
        '''
        Return all occurrences that are set to start on or after the current
        time.
        '''
        return self.occurrence_set.filter(start_time__gte=datetime.now())

    #---------------------------------------------------------------------------
    def next_occurrence(self):
        '''
        Return the single occurrence set to start on or after the current time
        if available, otherwise ``None``.
        '''
        upcoming = self.upcoming_occurrences()
        return upcoming and upcoming[0] or None

    #---------------------------------------------------------------------------
    def daily_occurrences(self, dt=None):
        '''
        Convenience method wrapping ``Occurrence.objects.daily_occurrences``.
        '''
        return Occurrence.objects.daily_occurrences(dt=dt, event=self)


#===============================================================================
class OccurrenceManager(models.Manager):
    
    use_for_related_fields = True
    
    #---------------------------------------------------------------------------
    def daily_occurrences(self, dt=None, event=None):
        '''
        Returns a queryset of for instances that have any overlap with a 
        particular day.
        
        * ``dt`` may be either a datetime.datetime, datetime.date object, or
          ``None``. If ``None``, default to the current day.
        
        * ``event`` can be an ``Event`` instance for further filtering.
        '''
        dt = dt or datetime.now()
        start = datetime(dt.year, dt.month, dt.day)
        end = start.replace(hour=23, minute=59, second=59)
        qs = self.filter(
            models.Q(
                start_time__gte=start,
                start_time__lte=end,
            ) |
            models.Q(
                end_time__gte=start,
                end_time__lte=end,
            ) |
            models.Q(
                start_time__lt=start,
                end_time__gt=end
            )
        )
        
        return qs.filter(event=event) if event else qs


#===============================================================================
class Occurrence(models.Model):
    '''
    Represents the start end time for a specific occurrence of a master ``Event``
    object.
    '''
    start_time = models.DateTimeField(_('start time'))
    end_time = models.DateTimeField(_('end time'))
    event = models.ForeignKey(Event, verbose_name=_('event'), editable=False)
    notes = generic.GenericRelation(Note, verbose_name=_('notes'))

    objects = OccurrenceManager()

    #===========================================================================
    class Meta:
        verbose_name = _('occurrence')
        verbose_name_plural = _('occurrences')
        ordering = ('start_time', 'end_time')

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return u'%s: %s' % (self.title, self.start_time.isoformat())

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-occurrence', [str(self.event.id), str(self.id)])

    #---------------------------------------------------------------------------
    def __cmp__(self, other):
        return cmp(self.start_time, other.start_time)

    #---------------------------------------------------------------------------
    @property
    def title(self):
        return self.event.title
        
    #---------------------------------------------------------------------------
    @property
    def event_type(self):
        return self.event.event_type


#-------------------------------------------------------------------------------
def create_event(
    title, 
    event_type,
    description='',
    start_time=None,
    end_time=None,
    note=None,
    **rrule_params
):
    '''
    Convenience function to create an ``Event``, optionally create an 
    ``EventType``, and associated ``Occurrence``s. ``Occurrence`` creation
    rules match those for ``Event.add_occurrences``.
     
    Returns the newly created ``Event`` instance.
    
    Parameters
    
    ``event_type``
        can be either an ``EventType`` object or 2-tuple of ``(abbreviation,label)``, 
        from which an ``EventType`` is either created or retrieved.
    
    ``start_time`` 
        will default to the current hour if ``None``
    
    ``end_time`` 
        will default to ``start_time`` plus swingtime_settings.DEFAULT_OCCURRENCE_DURATION
        hour if ``None``
    
    ``freq``, ``count``, ``rrule_params``
        follow the ``dateutils`` API (see http://labix.org/python-dateutil)
    
    '''
    from swingtime.conf import settings as swingtime_settings
    
    if isinstance(event_type, tuple):
        event_type, created = EventType.objects.get_or_create(
            abbr=event_type[0],
            label=event_type[1]
        )
    
    event = Event.objects.create(
        title=title, 
        description=description,
        event_type=event_type
    )

    if note is not None:
        event.notes.create(note=note)

    start_time = start_time or datetime.now().replace(
        minute=0,
        second=0, 
        microsecond=0
    )
    
    end_time = end_time or start_time + swingtime_settings.DEFAULT_OCCURRENCE_DURATION
    event.add_occurrences(start_time, end_time, **rrule_params)
    return event

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
from pprint import pprint, pformat
from cStringIO import StringIO
from datetime import datetime, timedelta, date, time

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command

from swingtime import utils
from swingtime.models import *

expected_table_1 = '''\
| 15:00 |          |          |          |          |          |
| 15:15 | zelda    |          |          |          |          |
| 15:30 | zelda    | alpha    |          |          |          |
| 15:45 |          | alpha    |          |          |          |
| 16:00 | bravo    | alpha    | foxtrot  |          |          |
| 16:15 | bravo    | alpha    | foxtrot  | charlie  |          |
| 16:30 | bravo    | alpha    | foxtrot  | charlie  | delta    |
| 16:45 |          | alpha    |          | charlie  | delta    |
| 17:00 |          | alpha    |          |          | delta    |
| 17:15 | echo     | alpha    |          |          |          |
| 17:30 | echo     | alpha    |          |          |          |
| 17:45 | echo     |          |          |          |          |
| 18:00 |          |          |          |          |          |
'''

expected_table_2 = '''\
| 15:30 | zelda    | alpha    |          |          |          |
| 15:45 |          | alpha    |          |          |          |
| 16:00 | bravo    | alpha    | foxtrot  |          |          |
| 16:15 | bravo    | alpha    | foxtrot  | charlie  |          |
| 16:30 | bravo    | alpha    | foxtrot  | charlie  | delta    |
| 16:45 |          | alpha    |          | charlie  | delta    |
| 17:00 |          | alpha    |          |          | delta    |
| 17:15 | echo     | alpha    |          |          |          |
| 17:30 | echo     | alpha    |          |          |          |
'''

expected_table_3 = '''\
| 16:00 | alpha    | bravo    | foxtrot  |          |          |
| 16:15 | alpha    | bravo    | foxtrot  | charlie  |          |
| 16:30 | alpha    | bravo    | foxtrot  | charlie  | delta    |
| 16:45 | alpha    |          |          | charlie  | delta    |
| 17:00 | alpha    |          |          |          | delta    |
| 17:15 | alpha    | echo     |          |          |          |
| 17:30 | alpha    | echo     |          |          |          |
'''

expected_table_4 = '''\
| 18:00 |          |          |          |          |
| 18:15 |          |          |          |          |
| 18:30 |          |          |          |          |
| 18:45 |          |          |          |          |
| 19:00 |          |          |          |          |
| 19:15 |          |          |          |          |
| 19:30 |          |          |          |          |
'''

expected_table_5 = '''\
| 16:30 | alpha    | bravo    | foxtrot  | charlie  | delta    |
'''

#===============================================================================
class TableTest(TestCase):

    fixtures = ['swingtime_test']

    #---------------------------------------------------------------------------
    def setUp(self):
        self._dt = dt = datetime(2008,12,11)

    #---------------------------------------------------------------------------
    def table_as_string(self, table):
        timefmt = '| %-5s'
        cellfmt = '| %-8s'
        out = StringIO()
        for tm, cells in table:
            print >> out, timefmt % tm.strftime('%H:%M'),
            for cell in cells:
                if cell:
                    print >> out, cellfmt % cell.event.title,
                else:
                    print >> out, cellfmt % '',
            print >> out, '|'
            
        return out.getvalue()

    #---------------------------------------------------------------------------
    def _do_test(self, start, end, expect):
        import pdb
        start = time(*start)
        dtstart = datetime.combine(self._dt, start)
        etd = datetime.combine(self._dt, time(*end)) - dtstart

        # pdb.set_trace()
        table = utils.create_timeslot_table(self._dt, start_time=start, end_time_delta=etd)

        actual = self.table_as_string(table)
        out = 'Expecting:\n%s\nActual:\n%s' % (expect, actual)
        print out
        self.assertEqual(actual, expect, out)

    #---------------------------------------------------------------------------
    def test_slot_table_1(self):
        self._do_test((15,0), (18,0), expected_table_1)

    #---------------------------------------------------------------------------
    def test_slot_table_2(self):
        self._do_test((15,30), (17,30), expected_table_2)

    #---------------------------------------------------------------------------
    def test_slot_table_3(self):
        self._do_test((16,0), (17,30), expected_table_3)

    #---------------------------------------------------------------------------
    def test_slot_table_4(self):
        self._do_test((18,0), (19,30), expected_table_4)

    #---------------------------------------------------------------------------
    def test_slot_table_5(self):
        self._do_test((16,30), (16,30), expected_table_5)


#===============================================================================
class NewEventFormTest(TestCase):

    fixtures = ['swingtime_test']
    
    #---------------------------------------------------------------------------
    def test_new_event_simple(self):
        from swingtime.forms import EventForm, MultipleOccurrenceForm
        
        data = dict(
            title='QWERTY',
            event_type='1',
            day='2008-12-11',
            start_time_delta='28800',
            end_time_delta='29700',
            year_month_ordinal_day='2',
            month_ordinal_day='2',
            holidays='skip',
            year_month_ordinal='1',
            month_option='each',
            repeats='count',
            freq='2',
            occurences='2',
            month_ordinal='1'
        )
        
        evt_form = EventForm(data)
        occ_form = MultipleOccurrenceForm(data)
        self.assertTrue(evt_form.is_valid(), evt_form.errors.as_text())
        self.assertTrue(occ_form.is_valid(), occ_form.errors.as_text())
        
        self.assertEqual(
            occ_form.cleaned_data['start_time'],
            datetime(2008, 12, 11, 8),
            'Bad start_time: %s' % pformat(occ_form.cleaned_data)
        )

#-------------------------------------------------------------------------------
def doc_tests():
    '''
        >>> from dateutil import rrule
        >>> from datetime import datetime
        >>> from swingtime.models import *
        >>> evt_types = [EventType.objects.create(abbr=l.lower(),label=l) for l in ['Foo', 'Bar', 'Baz']]
        >>> evt_types
        [<EventType: Foo>, <EventType: Bar>, <EventType: Baz>]
        >>> e = Event.objects.create(title='Hello, world', description='Happy New Year', event_type=evt_types[0])
        >>> e
        <Event: Hello, world>
        >>> e.add_occurrences(datetime(2008,1,1), datetime(2008,1,1,1), freq=rrule.YEARLY, count=7)
        >>> e.occurrence_set.all()
        [<Occurrence: Hello, world: 2008-01-01T00:00:00>, <Occurrence: Hello, world: 2009-01-01T00:00:00>, <Occurrence: Hello, world: 2010-01-01T00:00:00>, <Occurrence: Hello, world: 2011-01-01T00:00:00>, <Occurrence: Hello, world: 2012-01-01T00:00:00>, <Occurrence: Hello, world: 2013-01-01T00:00:00>, <Occurrence: Hello, world: 2014-01-01T00:00:00>]
        >>> e = create_event('Bicycle repairman', event_type=evt_types[2])
        >>> e.occurrence_set.count()
        1
        >>> e = create_event(
        ...     'Something completely different',
        ...     event_type=('abbr', 'Abbreviation'),
        ...     start_time=datetime(2008,12,1, 12),
        ...     freq=rrule.WEEKLY,
        ...     byweekday=(rrule.TU, rrule.TH),
        ...     until=datetime(2008,12,31)
        ... )
        >>> for o in e.occurrence_set.all():
        ...     print o.start_time, o.end_time
        ... 
        2008-12-02 12:00:00 2008-12-02 13:00:00
        2008-12-04 12:00:00 2008-12-04 13:00:00
        2008-12-09 12:00:00 2008-12-09 13:00:00
        2008-12-11 12:00:00 2008-12-11 13:00:00
        2008-12-16 12:00:00 2008-12-16 13:00:00
        2008-12-18 12:00:00 2008-12-18 13:00:00
        2008-12-23 12:00:00 2008-12-23 13:00:00
        2008-12-25 12:00:00 2008-12-25 13:00:00
        2008-12-30 12:00:00 2008-12-30 13:00:00
    '''
    pass
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from swingtime import views

urlpatterns = patterns('',
    url(
        r'^(?:calendar/)?$', 
        views.today_view, 
        name='swingtime-today'
    ),

    url(
        r'^calendar/(?P<year>\d{4})/$', 
        views.year_view, 
        name='swingtime-yearly-view'
    ),

    url(
        r'^calendar/(\d{4})/(0?[1-9]|1[012])/$', 
        views.month_view, 
        name='swingtime-monthly-view'
    ),

    url(
        r'^calendar/(\d{4})/(0?[1-9]|1[012])/([0-3]?\d)/$', 
        views.day_view, 
        name='swingtime-daily-view'
    ),

    url(
        r'^events/$',
        views.event_listing,
        name='swingtime-events'
    ),
        
    url(
        r'^events/add/$', 
        views.add_event, 
        name='swingtime-add-event'
    ),
    
    url(
        r'^events/(\d+)/$', 
        views.event_view, 
        name='swingtime-event'
    ),
    
    url(
        r'^events/(\d+)/(\d+)/$', 
        views.occurrence_view, 
        name='swingtime-occurrence'
    ),
)

########NEW FILE########
__FILENAME__ = utils
'''
Common features and functions for swingtime

'''
from collections import defaultdict
from datetime import datetime, date, time, timedelta
import itertools

from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe

from dateutil import rrule
from swingtime.conf import settings as swingtime_settings


#-------------------------------------------------------------------------------
def html_mark_safe(func):
    '''
    Decorator for functions return strings that should be treated as template
    safe.
    
    '''
    def decorator(*args, **kws):
        return mark_safe(func(*args, **kws))
    return decorator


#-------------------------------------------------------------------------------
def time_delta_total_seconds(time_delta):
    '''
    Calculate the total number of seconds represented by a 
    ``datetime.timedelta`` object
    
    '''
    return time_delta.days * 3600 + time_delta.seconds


#-------------------------------------------------------------------------------
def month_boundaries(dt=None):
    '''
    Return a 2-tuple containing the datetime instances for the first and last 
    dates of the current month or using ``dt`` as a reference. 
    
    '''
    import calendar
    dt = dt or date.today()
    wkday, ndays = calendar.monthrange(dt.year, dt.month)
    start = datetime(dt.year, dt.month, 1)
    return (start, start + timedelta(ndays - 1))


#-------------------------------------------------------------------------------
def css_class_cycler():
    '''
    Return a dictionary keyed by ``EventType`` abbreviations, whose values are an
    iterable or cycle of CSS class names.
    
    '''
    from swingtime.models import EventType
    return defaultdict(
        lambda: itertools.cycle(('evt-even', 'evt-odd')).next,
        ((e.abbr, itertools.cycle((
             'evt-%s-even' % e.abbr, 
             'evt-%s-odd' % e.abbr
             )).next) for e in EventType.objects.all()
        )
    )


#===============================================================================
class BaseOccurrenceProxy(object):
    '''
    A simple wrapper class for handling the presentational aspects of an
    ``Occurrence`` instance.
    
    '''
    #---------------------------------------------------------------------------
    def __init__(self, occurrence, col):
        self.column = col
        self._occurrence = occurrence
        self.event_class = ''

    #---------------------------------------------------------------------------
    def __getattr__(self, name):
        return getattr(self._occurrence, name)
        
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.title


#===============================================================================
class DefaultOccurrenceProxy(BaseOccurrenceProxy):

    CONTINUATION_STRING = '^'
    
    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(DefaultOccurrenceProxy, self).__init__(*args, **kws)
        link = '<a href="%s">%s</a>' % (
            self.get_absolute_url(),
            self.title
        )
        
        self._str = itertools.chain(
            (link,),
            itertools.repeat(self.CONTINUATION_STRING)
        ).next
        
    #---------------------------------------------------------------------------
    @html_mark_safe
    def __unicode__(self):
        return self._str()


#-------------------------------------------------------------------------------
def create_timeslot_table(
    dt=None,
    items=None,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_time_delta=swingtime_settings.TIMESLOT_END_TIME_DURATION,
    time_delta=swingtime_settings.TIMESLOT_INTERVAL,
    min_columns=swingtime_settings.TIMESLOT_MIN_COLUMNS,
    css_class_cycles=css_class_cycler,
    proxy_class=DefaultOccurrenceProxy
):
    '''
    Create a grid-like object representing a sequence of times (rows) and 
    columns where cells are either empty or reference a wrapper object for 
    event occasions that overlap a specific time slot.
    
    Currently, there is an assumption that if an occurrence has a ``start_time`` 
    that falls with the temporal scope of the grid, then that ``start_time`` will
    also match an interval in the sequence of the computed row entries.
    
    * ``dt`` - a ``datetime.datetime`` instance or ``None`` to default to now
    * ``items`` - a queryset or sequence of ``Occurrence`` instances. If 
      ``None``, default to the daily occurrences for ``dt``
    * ``start_time`` - a ``datetime.time`` instance 
    * ``end_time_delta`` - a ``datetime.timedelta`` instance
    * ``time_delta`` - a ``datetime.timedelta`` instance
    * ``min_column`` - the minimum number of columns to show in the table
    * ``css_class_cycles`` - if not ``None``, a callable returning a dictionary 
      keyed by desired ``EventType`` abbreviations with values that iterate over 
      progressive CSS class names for the particular abbreviation.
    * ``proxy_class`` - a wrapper class for accessing an ``Occurrence`` object.
      This class should also expose ``event_type`` and ``event_type`` attrs, and
      handle the custom output via its __unicode__ method.
    
    '''
    from swingtime.models import Occurrence
    dt = dt or datetime.now()
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_time_delta
    
    if isinstance(items, QuerySet):
        items = items._clone()
    elif not items:
        items = Occurrence.objects.daily_occurrences(dt).select_related('event')

    # build a mapping of timeslot "buckets"
    timeslots = dict()
    n = dtstart
    while n <= dtend:
        timeslots[n] = {}
        n += time_delta

    # fill the timeslot buckets with occurrence proxies
    for item in sorted(items):
        if item.end_time <= dtstart:
            # this item began before the start of our schedle constraints
            continue

        if item.start_time > dtstart:
            rowkey = current = item.start_time
        else:
            rowkey = current = dtstart

        timeslot = timeslots.get(rowkey, None)
        if timeslot is None:
            # TODO fix atypical interval boundry spans
            # This is rather draconian, we should probably try to find a better
            # way to indicate that this item actually occurred between 2 intervals
            # and to account for the fact that this item may be spanning cells
            # but on weird intervals
            continue

        colkey = 0
        while 1:
            # keep searching for an open column to place this occurrence
            if colkey not in timeslot:
                proxy = proxy_class(item, colkey)
                timeslot[colkey] = proxy

                while current < item.end_time:
                    rowkey = current
                    row = timeslots.get(rowkey, None)
                    if row is None:
                        break
                    
                    # we might want to put a sanity check in here to ensure that
                    # we aren't trampling some other entry, but by virtue of 
                    # sorting all occurrence that shouldn't happen
                    row[colkey] = proxy
                    current += time_delta
                break

            colkey += 1
            
    # determine the number of timeslot columns we should show
    column_lens = [len(x) for x in timeslots.itervalues()]
    column_count = max((min_columns, max(column_lens) if column_lens else 0))
    column_range = range(column_count)
    empty_columns = ['' for x in column_range]
    
    if css_class_cycles:
        column_classes = dict([(i, css_class_cycles()) for i in column_range])
    else:
        column_classes = None

    # create the chronological grid layout
    table = []
    for rowkey in sorted(timeslots.keys()):
        cols = empty_columns[:]
        for colkey in timeslots[rowkey]:
            proxy = timeslots[rowkey][colkey]
            cols[colkey] = proxy
            if not proxy.event_class and column_classes:
                proxy.event_class = column_classes[colkey][proxy.event_type.abbr]()

        table.append((rowkey, cols))

    return table

########NEW FILE########
__FILENAME__ = views
import calendar
import itertools
from datetime import datetime, timedelta, time

from django import http
from django.db import models
from django.template.context import RequestContext
from django.shortcuts import get_object_or_404, render

from swingtime.models import Event, Occurrence
from swingtime import utils, forms
from swingtime.conf import settings as swingtime_settings

from dateutil import parser

if swingtime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(swingtime_settings.CALENDAR_FIRST_WEEKDAY)


#-------------------------------------------------------------------------------
def event_listing(
    request, 
    template='swingtime/event_list.html',
    events=None,
    **extra_context
):
    '''
    View all ``events``. 
    
    If ``events`` is a queryset, clone it. If ``None`` default to all ``Event``s.
    
    Context parameters:
    
    events
        an iterable of ``Event`` objects
        
    ???
        all values passed in via **extra_context
    '''
    return render(
        request,
        template,
        dict(extra_context, events=events or Event.objects.all())
    )


#-------------------------------------------------------------------------------
def event_view(
    request, 
    pk, 
    template='swingtime/event_detail.html', 
    event_form_class=forms.EventForm,
    recurrence_form_class=forms.MultipleOccurrenceForm
):
    '''
    View an ``Event`` instance and optionally update either the event or its
    occurrences.

    Context parameters:

    event
        the event keyed by ``pk``
        
    event_form
        a form object for updating the event
        
    recurrence_form
        a form object for adding occurrences
    '''
    event = get_object_or_404(Event, pk=pk)
    event_form = recurrence_form = None
    if request.method == 'POST':
        if '_update' in request.POST:
            event_form = event_form_class(request.POST, instance=event)
            if event_form.is_valid():
                event_form.save(event)
                return http.HttpResponseRedirect(request.path)
        elif '_add' in request.POST:
            recurrence_form = recurrence_form_class(request.POST)
            if recurrence_form.is_valid():
                recurrence_form.save(event)
                return http.HttpResponseRedirect(request.path)
        else:
            return http.HttpResponseBadRequest('Bad Request')

    data = {
        'event': event,
        'event_form': event_form or event_form_class(instance=event),
        'recurrence_form': recurrence_form or recurrence_form_class(initial={'dtstart': datetime.now()})
    }
    return render(request, template, data)


#-------------------------------------------------------------------------------
def occurrence_view(
    request, 
    event_pk, 
    pk, 
    template='swingtime/occurrence_detail.html',
    form_class=forms.SingleOccurrenceForm
):
    '''
    View a specific occurrence and optionally handle any updates.
    
    Context parameters:
    
    occurrence
        the occurrence object keyed by ``pk``

    form
        a form object for updating the occurrence
    '''
    occurrence = get_object_or_404(Occurrence, pk=pk, event__pk=event_pk)
    if request.method == 'POST':
        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            form.save()
            return http.HttpResponseRedirect(request.path)
    else:
        form = form_class(instance=occurrence)
        
    return render(request, template, {'occurrence': occurrence, 'form': form})


#-------------------------------------------------------------------------------
def add_event(
    request, 
    template='swingtime/add_event.html',
    event_form_class=forms.EventForm,
    recurrence_form_class=forms.MultipleOccurrenceForm
):
    '''
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.
    
    Context parameters:
    
    dtstart
        a datetime.datetime object representing the GET request value if present,
        otherwise None
    
    event_form
        a form object for updating the event

    recurrence_form
        a form object for adding occurrences
    
    '''
    dtstart = None
    if request.method == 'POST':
        event_form = event_form_class(request.POST)
        recurrence_form = recurrence_form_class(request.POST)
        if event_form.is_valid() and recurrence_form.is_valid():
            event = event_form.save()
            recurrence_form.save(event)
            return http.HttpResponseRedirect(event.get_absolute_url())
            
    else:
        if 'dtstart' in request.GET:
            try:
                dtstart = parser.parse(request.GET['dtstart'])
            except:
                # TODO A badly formatted date is passed to add_event
                pass
        
        dtstart = dtstart or datetime.now()
        event_form = event_form_class()
        recurrence_form = recurrence_form_class(initial={'dtstart': dtstart})
            
    return render(
        request,
        template,
        {'dtstart': dtstart, 'event_form': event_form, 'recurrence_form': recurrence_form}
    )


#-------------------------------------------------------------------------------
def _datetime_view(
    request, 
    template, 
    dt, 
    timeslot_factory=None, 
    items=None,
    params=None
):
    '''
    Build a time slot grid representation for the given datetime ``dt``. See
    utils.create_timeslot_table documentation for items and params.
    
    Context parameters:
    
    day
        the specified datetime value (dt)
        
    next_day
        day + 1 day
        
    prev_day
        day - 1 day
        
    timeslots
        time slot grid of (time, cells) rows
        
    '''
    timeslot_factory = timeslot_factory or utils.create_timeslot_table
    params = params or {}
    
    return render(request, template, {
        'day':       dt, 
        'next_day':  dt + timedelta(days=+1),
        'prev_day':  dt + timedelta(days=-1),
        'timeslots': timeslot_factory(dt, items, **params)
    })


#-------------------------------------------------------------------------------
def day_view(request, year, month, day, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.
    
    '''
    dt = datetime(int(year), int(month), int(day))
    return _datetime_view(request, template, dt, **params)


#-------------------------------------------------------------------------------
def today_view(request, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.
    
    '''
    return _datetime_view(request, template, datetime.now(), **params)


#-------------------------------------------------------------------------------
def year_view(request, year, template='swingtime/yearly_view.html', queryset=None):
    '''

    Context parameters:
    
    year
        an integer value for the year in questin
        
    next_year
        year + 1
        
    last_year
        year - 1
        
    by_month
        a sorted list of (month, occurrences) tuples where month is a 
        datetime.datetime object for the first day of a month and occurrences
        is a (potentially empty) list of values for that month. Only months 
        which have at least 1 occurrence is represented in the list
        
    '''
    year = int(year)
    queryset = queryset._clone() if queryset else Occurrence.objects.select_related()
    occurrences = queryset.filter(
        models.Q(start_time__year=year) |
        models.Q(end_time__year=year)
    )

    def group_key(o):
        return datetime(
            year,
            o.start_time.month if o.start_time.year == year else o.end_time.month,
            1
        )

    return render(request, template, {
        'year': year,
        'by_month': [(dt, list(o)) for dt,o in itertools.groupby(occurrences, group_key)],
        'next_year': year + 1,
        'last_year': year - 1
        
    })


#-------------------------------------------------------------------------------
def month_view(
    request, 
    year, 
    month, 
    template='swingtime/monthly_view.html',
    queryset=None
):
    '''
    Render a tradional calendar grid view with temporal navigation variables.

    Context parameters:
    
    today
        the current datetime.datetime value
        
    calendar
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day
        
    this_month
        a datetime.datetime representing the first day of the month
    
    next_month
        this_month + 1 month
    
    last_month
        this_month - 1 month
    
    '''
    year, month = int(year), int(month)
    cal         = calendar.monthcalendar(year, month)
    dtstart     = datetime(year, month, 1)
    last_day    = max(cal[-1])
    dtend       = datetime(year, month, last_day)

    # TODO Whether to include those occurrences that started in the previous
    # month but end in this month?
    queryset = queryset._clone() if queryset else Occurrence.objects.select_related()
    occurrences = queryset.filter(start_time__year=year, start_time__month=month)

    def start_day(o):
        return o.start_time.day
    
    by_day = dict([(dt, list(o)) for dt,o in itertools.groupby(occurrences, start_day)])
    data = {
        'today':      datetime.now(),
        'calendar':   [[(d, by_day.get(d, [])) for d in row] for row in cal], 
        'this_month': dtstart,
        'next_month': dtstart + timedelta(days=+last_day),
        'last_month': dtstart + timedelta(days=-1),
    }

    return render(request, template, data)


########NEW FILE########
