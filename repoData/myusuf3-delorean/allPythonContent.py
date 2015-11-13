__FILENAME__ = dates
import sys
from datetime import datetime
from functools import partial, update_wrapper

import pytz
from pytz import timezone
from dateutil.relativedelta import relativedelta

from .exceptions import DeloreanInvalidTimezone

UTC = "UTC"
utc = timezone("UTC")


def get_total_second(td):
    """
    This method takes a timedelta and return the number of seconds it
    represents with the resolution of 10 **6
    """
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6


def is_datetime_naive(dt):
    """
    This method returns true if the datetime is naive else returns false
    """
    if dt is None:
        return True

    if dt.tzinfo is None:
        return True
    else:
        return False


def _move_datetime(dt, direction, delta):
    """
    Move datetime given delta by given direction
    """
    if direction == 'next':
        dt = dt + delta
    elif direction == 'last':
        dt = dt - delta
    else:
        pass
        # raise some delorean error here
    return dt


def move_datetime_day(dt, direction, num_shifts):
    delta = relativedelta(days=+num_shifts)
    return _move_datetime(dt, direction, delta)


def move_datetime_namedday(dt, direction, unit):
    TOTAL_DAYS = 7
    days = {
        'monday': 1,
        'tuesday': 2,
        'wednesday': 3,
        'thursday': 4,
        'friday': 5,
        'saturday': 6,
        'sunday': 7,
    }

    current_day = days[dt.strftime('%A').lower()]
    target_day = days[unit.lower()]

    if direction == 'next':
        if current_day < target_day:
            delta_days = target_day - current_day
        else:
            delta_days = (target_day - current_day) + TOTAL_DAYS
    elif direction == 'last':

        if current_day <= target_day:
            delta_days = (current_day - target_day) + TOTAL_DAYS
        else:
            delta_days = current_day - target_day

    delta = relativedelta(days=+delta_days)
    return _move_datetime(dt, direction, delta)


def move_datetime_month(dt, direction, num_shifts):
    """
    Move datetime 1 month in the chosen direction.
    unit is a no-op, to keep the API the same as the day case
    """
    delta = relativedelta(months=+num_shifts)
    return _move_datetime(dt, direction, delta)


def move_datetime_week(dt, direction, num_shifts):
    """
    Move datetime 1 week in the chosen direction.
    unit is a no-op, to keep the API the same as the day case
    """
    delta = relativedelta(weeks=+num_shifts)
    return _move_datetime(dt, direction, delta)


def move_datetime_year(dt, direction, num_shifts):
    """
    Move datetime 1 year in the chosen direction.
    unit is a no-op, to keep the API the same as the day case
    """
    delta = relativedelta(years=+num_shifts)
    return _move_datetime(dt, direction, delta)

def move_datetime_hour(dt, direction, num_shifts):
    delta = relativedelta(hours=+num_shifts)
    return _move_datetime(dt, direction, delta)

def move_datetime_minute(dt, direction, num_shifts):
    delta = relativedelta(minutes=+num_shifts)
    return _move_datetime(dt, direction, delta)

def move_datetime_second(dt, direction, num_shifts):
    delta = relativedelta(seconds=+num_shifts)
    return _move_datetime(dt, direction, delta)

def datetime_timezone(tz):
    """
    This method given a timezone returns a localized datetime object.
    """
    utc_datetime_naive = datetime.utcnow()
    # return a localized datetime to UTC
    utc_localized_datetime = localize(utc_datetime_naive, UTC)
    # normalize the datetime to given timezone
    normalized_datetime = normalize(utc_localized_datetime, tz)
    return normalized_datetime


def localize(dt, tz):
    """
    Given a naive datetime object this method will return a localized
    datetime object
    """
    tz = timezone(tz)
    return tz.localize(dt)


def normalize(dt, tz):
    """
    Given a object with a timezone return a datetime object
    normalized to the proper timezone.

    This means take the give localized datetime and returns the
    datetime normalized to match the specificed timezone.
    """
    tz = timezone(tz)
    dt = tz.normalize(dt)
    return dt


class Delorean(object):
    """
    The class `Delorean <Delorean>` object. This method accepts naive
    datetime objects, with a string timezone.
    """
    _VALID_SHIFT_DIRECTIONS = ('last', 'next')
    _VALID_SHIFT_UNITS = ('second', 'minute', 'hour', 'day', 'week', 
                          'month', 'year', 'monday', 'tuesday', 'wednesday',
                          'thursday', 'friday', 'saturday','sunday')

    def __init__(self, datetime=None, timezone=None):
        # maybe set timezone on the way in here. if here set it if not
        # use UTC
        naive = True
        self._tz = timezone
        self._dt = datetime

        if not is_datetime_naive(datetime):
            # if already localized find the zone
            # once zone is found set _tz and the localized datetime
            # to _dt
            naive = False
            zone = datetime.tzinfo.tzname(None)
            self._tz = zone
            self._dt = datetime

        if naive:
            if timezone is None and datetime is None:
                self._tz = UTC
                self._dt = datetime_timezone(UTC)
            elif timezone is not None and datetime is None:
                # create utctime then normalize to tz
                self._tz = timezone
                self._dt = datetime_timezone(timezone)
            elif timezone is None and datetime is not None:
                raise DeloreanInvalidTimezone('Provide a valid timezone')
            else:
                # passed in naive datetime and timezone
                # that correspond accordingly
                self._tz = timezone
                self._dt = localize(datetime, timezone)

    def __repr__(self):
        return 'Delorean(datetime=%s, timezone=%s)' % (self._dt, self._tz)

    def __eq__(self, other):
        if isinstance(other, Delorean):
            return self._dt == other._dt and self._tz == other._tz
        return False

    def __lt__(self, other):
        return self.epoch() < other.epoch()

    def __gt__(self, other):
        return self.epoch() > other.epoch()

    def __ge__(self, other):
        return self.epoch() >= other.epoch()

    def __le__(self, other):
        return self.epoch() <= other.epoch()

    def __ne__(self, other):
        return not self == other

    def __getattr__(self, name):
        """
        Implement __getattr__ to call `shift_date` function when function
        called does not exist
        """
        func_parts = name.split('_')
        # is the func we are trying to call the right length?
        if len(func_parts) != 2:
            raise AttributeError

        # is the function we are trying to call valid?
        if (func_parts[0] not in self._VALID_SHIFT_DIRECTIONS or
                func_parts[1] not in self._VALID_SHIFT_UNITS):
            return AttributeError

        # dispatch our function
        func = partial(self._shift_date, func_parts[0], func_parts[1])
        # update our partial with self.shift_date attributes
        update_wrapper(func, self._shift_date)
        return func

    def _shift_date(self, direction, unit, *args):
        """
        Shift datetime in `direction` in _VALID_SHIFT_DIRECTIONS and by some
        unit in _VALID_SHIFTS and shift that amount by some multiple,
        defined by by args[0] if it exists
        """
        this_module = sys.modules[__name__]

        num_shifts = 1
        if len(args) > 0:
            num_shifts = int(args[0])

        if unit in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                    'saturday', 'sunday']:
            shift_func = move_datetime_namedday
            dt = shift_func(self._dt, direction, unit)
            if num_shifts > 1:
                for n in range(num_shifts - 1):
                    dt = shift_func(dt, direction, unit)
        else:
            shift_func = getattr(this_module, 'move_datetime_%s' % unit)
            dt = shift_func(self._dt, direction, num_shifts)

        return Delorean(datetime=dt.replace(tzinfo=None), timezone=self._tz)

    def timezone(self):
        """
        This method return a valid pytz timezone object associated with
        the Delorean object or raises Invalid Timezone error.
        """
        if self._tz is None:
            return None
        try:
            return timezone(self._tz)
        except pytz.exceptions.UnknownTimeZoneError:
            # raise some delorean error
            raise DeloreanInvalidTimezone('Provide a valid timezone')

    def truncate(self, s):
        """
        Truncate the delorian object to the nearest s
        (second, minute, hour, day, month, year)

        This is a destructive method, modifies the internal datetime
        object associated with the Delorean object.

        """
        if s == 'second':
            self._dt = self._dt.replace(microsecond=0)
        elif s == 'minute':
            self._dt = self._dt.replace(second=0, microsecond=0)
        elif s == 'hour':
            self._dt = self._dt.replace(minute=0, second=0, microsecond=0)
        elif s == 'day':
            self._dt = self._dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif s == 'month':
            self._dt = self._dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif s == 'year':
            self._dt = self._dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError("Invalid truncation level")

        return self

    def next_day(self, days):
        dt = self._dt + relativedelta(days=+days)
        dt = dt.replace(tzinfo=None)
        return Delorean(datetime=dt, timezone=self._tz)

    def naive(self):
        """
        Returns a naive datetime object associated with the Delorean
        object, this method simply converts the localize datetime to UTC
        and removes the tzinfo that is associated with it.
        """
        return utc.normalize(self._dt).replace(tzinfo=None)

    def midnight(self):
        """
        This method returns midnight for datetime associated with
        the Delorean object.
        """
        return self._dt.replace(hour=0, minute=0, second=0, microsecond=0)

    def shift(self, tz):
        """
        This method shifts the timezone from the current timezone to the
        specified timezone associated with the Delorean object
        """
        try:
            zone = timezone(tz)
        except pytz.UnknownTimeZoneError:
            raise DeloreanInvalidTimezone('Provide a valid timezone')
        self._tz = tz
        self._dt = zone.normalize(self._dt)
        return self

    def epoch(self):
        """
        This method returns the total seconds since epoch associated with
        the Delorean object.
        """
        utc = timezone(UTC)
        epoch = utc.localize(datetime.utcfromtimestamp(0))
        dt = utc.normalize(self._dt)
        delta = dt - epoch
        return get_total_second(delta)

    @property
    def date(self):
        """
        This method returns the actual date object associated with
        the Delorean object.
        """
        return self._dt.date()

    @property
    def datetime(self):
        """
        This method returns the actual datetime object associated with
        the Delorean object.
        """
        return self._dt

########NEW FILE########
__FILENAME__ = exceptions
class DeloreanError(Exception):
    """
    Base Delorean Exception class
    """

    def __init__(self, msg):
        self.msg = str(msg)
        Exception.__init__(self, msg)

    def __str__(self):
        return self.msg


class DeloreanInvalidTimezone(DeloreanError):
    """
    Exception that is raised when an invalid timezone is passed in.
    """
    pass


class DeloreanInvalidDatetime(DeloreanError):
    """
    Exception that is raised when an improper datetime object is passed
    in.
    """
    pass

########NEW FILE########
__FILENAME__ = interface
from datetime import datetime

from pytz import timezone
from dateutil.rrule import rrule, DAILY, HOURLY, MONTHLY, YEARLY
from dateutil.parser import parse as capture

from .exceptions import DeloreanInvalidDatetime
from .dates import Delorean, is_datetime_naive, datetime_timezone

UTC = "UTC"
utc = timezone("utc")


def parse(s, dayfirst=True, yearfirst=True):
    """
    Parses a datetime string in it and returns a `Delorean` object.

    If a timezone is detected in the datetime string it will be
    normalized to UTC, and a Delorean object with that datetime and
    timezone will be returned.
    """
    try:
        dt = capture(s, dayfirst=dayfirst, yearfirst=yearfirst)
    except:
        # raise a parsing error.
        raise ValueError("Unknown string format")
    if dt.tzinfo is None:
        # assuming datetime object passed in is UTC
        do = Delorean(datetime=dt, timezone=UTC)
    else:
        dt = utc.normalize(dt)
        # makeing dt naive so we can pass it to Delorean
        dt = dt.replace(tzinfo=None)
        # if parse string has tzinfo we return a normalized UTC
        # delorean object that represents the time.
        do = Delorean(datetime=dt, timezone=UTC)
    return do


def range_daily(start=None, stop=None, timezone=UTC, count=None):
    """
    This an alternative way to generating sets of Delorean objects with
    DAILY stops
    """
    return stops(start=start, stop=stop, freq=DAILY, timezone=timezone, count=count)


def range_hourly(start=None, stop=None, timezone=UTC, count=None):
    """
    This an alternative way to generating sets of Delorean objects with
    HOURLY stops
    """
    return stops(start=start, stop=stop, freq=HOURLY, timezone=timezone, count=count)


def range_monthly(start=None, stop=None, timezone=UTC, count=None):
    """
    This an alternative way to generating sets of Delorean objects with
    MONTHLY stops
    """
    return stops(start=start, stop=stop, freq=MONTHLY, timezone=timezone, count=count)


def range_yearly(start=None, stop=None, timezone=UTC, count=None):
    """
    This an alternative way to generating sets of Delorean objects with
    YEARLY stops
    """
    return stops(start=start, stop=stop, freq=YEARLY, timezone=timezone, count=count)


def stops(freq, interval=1, count=None, wkst=None, bysetpos=None,
          bymonth=None, bymonthday=None, byyearday=None, byeaster=None,
          byweekno=None, byweekday=None, byhour=None, byminute=None,
          bysecond=None, timezone=UTC, start=None, stop=None):
    """
    This will create a list of delorean objects the apply to
    setting possed in.
    """
    # check to see if datetimees passed in are naive if so process them
    # with given timezone.
    if is_datetime_naive(start) and is_datetime_naive(stop):
        pass
    else:
        raise DeloreanInvalidDatetime('Provide a naive datetime object')

    # if no datetimes are passed in create a proper datetime object for
    # start default because default in dateutil is datetime.now() :(
    if start is None:
        start = datetime_timezone(timezone)

    for dt in rrule(freq, interval=interval, count=count, wkst=None, bysetpos=None,
          bymonth=None, bymonthday=None, byyearday=None, byeaster=None,
          byweekno=None, byweekday=None, byhour=None, byminute=None,
          bysecond=None, until=stop, dtstart=start):
        # make the delorean object
        # yield it.
        # doing this to make sure delorean receives a naive datetime.
        dt = dt.replace(tzinfo=None)
        d = Delorean(datetime=dt, timezone=timezone)
        yield d


def epoch(s):
    dt = datetime.utcfromtimestamp(s)
    return Delorean(datetime=dt, timezone=UTC)


def flux():
    print("If you put your mind to it, you can accomplish anything.")


def utcnow():
    """
    Return a delorean object, with utcnow as the datetime
    """
    return Delorean()


def now():
    """
    Return a delorean object, with utcnow as the datetime
    """
    return utcnow()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# delorean documentation build configuration file, created by
# sphinx-quickstart on Tue Jan  8 00:44:25 2013.
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

sys.path.insert(0, os.path.abspath('..'))
import delorean
from version import __version__

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']


# 'releases' (changelog) settings
releases_issue_uri = "https://github.com/myusuf3/delorean/issues/%s"
releases_release_uri = "https://github.com/myusuf3/delorean/tree/%s"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'delorean'
copyright = u'2013, Mahdi Yusuf'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(str(x) for x in __version__)
# The full version, including alpha/beta/rc tags.
release = '.'.join(str(x) for x in __version__)

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
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index':    ['side-primary.html', 'searchbox.html'],
    '**':       ['side-secondary.html', 'localtoc.html',
                 'relations.html', 'searchbox.html']
}

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
htmlhelp_basename = 'deloreandoc'


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
  ('index', 'Delorean.tex', u'Delorean Documentation',
   u'Mahdi Yusuf', 'manual'),
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
    ('index', 'Delorean', u'Delorean Documentation',
     [u'Mahdi Yusuf'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Delorean', u'Delorean Documentation',
   u'Mahdi Yusuf', 'Delorean', 'Delorean is a library provides easy and convenient datetime conversions in Python.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'kr'

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
__FILENAME__ = test_data
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testing for Delorean
"""

from unittest import TestCase, main
from datetime import tzinfo, datetime, date, timedelta
from copy import deepcopy

from pytz import timezone
import delorean


class GenericUTC(tzinfo):
    """GenericUTC"""
    ZERO = timedelta(0)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "GenericUTC"

    def dst(self, dt):
        return self.ZERO

UTC = "UTC"
utc = timezone(UTC)
generic_utc = GenericUTC()
est = timezone("US/Eastern")


class DeloreanTests(TestCase):

    def setUp(self):
        self.naive_dt = datetime(2013, 1, 3, 4, 31, 14, 148546)
        self.do = delorean.Delorean(datetime=self.naive_dt, timezone="UTC")

    def test_initialize_from_datetime_naive(self):
        self.assertRaises(delorean.DeloreanInvalidTimezone, delorean.Delorean, datetime=self.naive_dt)

    def test_initialize_with_tzinfo_generic(self):
        self.aware_dt_generic = datetime(2013, 1, 3, 4, 31, 14, 148546, tzinfo=generic_utc)
        do = delorean.Delorean(datetime=self.aware_dt_generic)
        self.assertTrue(type(do) is delorean.Delorean)

    def test_initialize_with_tzinfo_pytz(self):
        self.aware_dt_pytz = datetime(2013, 1, 3, 4, 31, 14, 148546, tzinfo=utc)
        do = delorean.Delorean(datetime=self.aware_dt_pytz)
        self.assertTrue(type(do) is delorean.Delorean)

    def test_truncation_hour(self):
        self.do.truncate('hour')
        self.assertEqual(self.do.naive(), datetime(2013, 1, 3, 4, 0))

    def test_truncation_second(self):
        self.do.truncate('second')
        self.assertEqual(self.do.naive(), datetime(2013, 1, 3, 4, 31, 14, 0))

    def test_truncation_minute(self):
        self.do.truncate('minute')
        self.assertEqual(self.do.naive(), datetime(2013, 1, 3, 4, 31, 0, 0))

    def test_truncation_day(self):
        self.do.truncate('day')
        self.assertEqual(self.do.naive(), datetime(2013, 1, 3, 0, 0, 0, 0))

    def test_truncation_month(self):
        self.do.truncate('month')
        self.assertEqual(self.do.naive(), datetime(2013, 1, 1, 0, 0, 0, 0))

    def test_truncation_year(self):
        self.do.truncate('year')
        self.assertEqual(self.do.naive(), datetime(2013, 1, 1, 0, 0, 0, 0))

    def test_date(self):
        self.assertEqual(self.do.date, date(2013, 1, 3))

    def test_datetime(self):
        self.assertEqual(self.do.naive(), datetime(2013, 1, 3, 4, 31, 14, 148546))

    def test_naive(self):
        dt1 = delorean.Delorean()
        dt_naive = dt1.naive()
        self.assertEqual(dt_naive.tzinfo, None)

    def test_naive_timezone(self):
        dt1 = delorean.Delorean(timezone="US/Eastern").truncate('second').naive()
        dt2 = delorean.Delorean().truncate('second').naive()
        self.assertEqual(dt2, dt1)
        self.assertEqual(dt1.tzinfo, None)

    def test_localize(self):
        dt = datetime.today()
        utc = timezone("UTC")
        dt = delorean.localize(dt, "UTC")
        self.assertEqual(dt.tzinfo, utc)

    def test_failure_truncation(self):
        self.assertRaises(ValueError, self.do.truncate, "century")

    def test_normalize(self):
        dt1 = delorean.Delorean()
        dt2 = delorean.Delorean(timezone="US/Eastern")
        dt1.truncate('minute')
        dt2.truncate('minute')
        dt_normalized = delorean.normalize(dt1.datetime, "US/Eastern")
        self.assertEqual(dt2.datetime, dt_normalized)

    def test_normalize_failure(self):
        naive_datetime = datetime.today()
        self.assertRaises(ValueError, delorean.normalize, naive_datetime, "US/Eastern")

    def test_localize_failure(self):
        dt1 = delorean.localize(datetime.utcnow(), "UTC")
        self.assertRaises(ValueError, delorean.localize, dt1, "UTC")

    def test_timezone(self):
        utc = timezone('UTC')
        do_timezone = delorean.Delorean().timezone()
        self.assertEqual(utc, do_timezone)

    def test_datetime_timezone_default(self):
        do = delorean.Delorean()
        do.truncate('minute')
        dt1 = delorean.datetime_timezone(UTC)
        self.assertEqual(dt1.replace(second=0, microsecond=0), do.datetime)

    def test_datetime_timezone(self):
        do = delorean.Delorean(timezone="US/Eastern")
        do.truncate("minute")
        dt1 = delorean.datetime_timezone(tz="US/Eastern")
        self.assertEqual(dt1.replace(second=0, microsecond=0), do.datetime)

    def test_parse(self):
        do = delorean.parse('Thu Sep 25 10:36:28 BRST 2003')
        dt1 = utc.localize(datetime(2003, 9, 25, 10, 36, 28))
        self.assertEqual(do.datetime, dt1)

    def test_parse_with_utc_year_fill(self):
        do = delorean.parse('Thu Sep 25 10:36:28')
        dt1 = utc.localize(datetime(date.today().year, 9, 25, 10, 36, 28))
        self.assertEqual(do.datetime, dt1)

    def test_parse_with_timezone_year_fill(self):
        do = delorean.parse('Thu Sep 25 10:36:28')
        dt1 = utc.localize(datetime(date.today().year, 9, 25, 10, 36, 28))
        self.assertEqual(do.datetime, dt1)
        self.assertEqual(do._tz, "UTC")

    def test_move_namedday(self):
        dt_next = datetime(2013, 1, 4, 4, 31, 14, 148546, tzinfo=utc)
        dt_next_2 = datetime(2013, 1, 11, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 12, 28, 4, 31, 14, 148546, tzinfo=utc)
        dt_last_2 = datetime(2012, 12, 21, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = self.do.next_friday()
        d_obj_next_2 = self.do.next_friday(2)
        d_obj_last = self.do.last_friday()
        d_obj_last_2 = self.do.last_friday(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_namedday_function(self):
        dt_next = datetime(2013, 1, 4, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 12, 28, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_namedday(self.do.datetime, 'next', 'friday')
        d_obj_last = delorean.move_datetime_namedday(self.do.datetime, 'last', 'friday')

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_week(self):
        dt_next = datetime(2013, 1, 10, 4, 31, 14, 148546, tzinfo=utc)
        dt_next_2 = datetime(2013, 1, 17, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 12, 27, 4, 31, 14, 148546, tzinfo=utc)
        dt_last_2 = datetime(2012, 12, 20, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = self.do.next_week()
        d_obj_next_2 = self.do.next_week(2)
        d_obj_last = self.do.last_week()
        d_obj_last_2 = self.do.last_week(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_week_function(self):
        dt_next = datetime(2013, 1, 10, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 12, 27, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_week(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_week(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_month(self):
        dt_next = datetime(2013, 2, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_next_2 = datetime(2013, 3, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 12, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_last_2 = datetime(2012, 11, 3, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = self.do.next_month()
        d_obj_next_2 = self.do.next_month(2)
        d_obj_last = self.do.last_month()
        d_obj_last_2 = self.do.last_month(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_month_function(self):
        dt_next = datetime(2013, 2, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 12, 3, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_month(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_month(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_day_function(self):
        dt_next = datetime(2013, 1, 4, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 2, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_day(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_day(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_year(self):
        dt_next = datetime(2014, 1, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_next_2 = datetime(2015, 1, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 1, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_last_2 = datetime(2011, 1, 3, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = self.do.next_year()
        d_obj_next_2 = self.do.next_year(2)
        d_obj_last = self.do.last_year()
        d_obj_last_2 = self.do.last_year(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_year_function(self):
        dt_next = datetime(2014, 1, 3, 4, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2012, 1, 3, 4, 31, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_year(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_year(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_hour(self):
        dt_next   = datetime(2013, 1, 3, 5, 31, 14, 148546, tzinfo=utc)
        dt_next_2 = datetime(2013, 1, 3, 6, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 3, 3, 31, 14, 148546, tzinfo=utc)
        dt_last_2 = datetime(2013, 1, 3, 2, 31, 14, 148546, tzinfo=utc)

        d_obj_next = self.do.next_hour()
        d_obj_next_2 = self.do.next_hour(2)
        d_obj_last = self.do.last_hour()
        d_obj_last_2 = self.do.last_hour(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_hour_function(self):
        dt_next = datetime(2013, 1, 3, 5, 31, 14, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 3, 3, 31, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_hour(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_hour(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_minute(self):
        dt_next   = datetime(2013, 1, 3, 4, 32, 14, 148546, tzinfo=utc)
        dt_next_2 = datetime(2013, 1, 3, 4, 33, 14, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 3, 4, 30, 14, 148546, tzinfo=utc)
        dt_last_2 = datetime(2013, 1, 3, 4, 29, 14, 148546, tzinfo=utc)

        d_obj_next = self.do.next_minute()
        d_obj_next_2 = self.do.next_minute(2)
        d_obj_last = self.do.last_minute()
        d_obj_last_2 = self.do.last_minute(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_minute_function(self):
        dt_next = datetime(2013, 1, 3, 4, 32, 14, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 3, 4, 30, 14, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_minute(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_minute(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_move_minute(self):
        dt_next   = datetime(2013, 1, 3, 4, 31, 15, 148546, tzinfo=utc)
        dt_next_2 = datetime(2013, 1, 3, 4, 31, 16, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 3, 4, 31, 13, 148546, tzinfo=utc)
        dt_last_2 = datetime(2013, 1, 3, 4, 31, 12, 148546, tzinfo=utc)

        d_obj_next = self.do.next_second()
        d_obj_next_2 = self.do.next_second(2)
        d_obj_last = self.do.last_second()
        d_obj_last_2 = self.do.last_second(2)

        self.assertEqual(dt_next, d_obj_next.datetime)
        self.assertEqual(dt_last, d_obj_last.datetime)
        self.assertEqual(dt_next_2, d_obj_next_2.datetime)
        self.assertEqual(dt_last_2, d_obj_last_2.datetime)

    def test_move_second_function(self):
        dt_next = datetime(2013, 1, 3, 4, 31, 15, 148546, tzinfo=utc)
        dt_last = datetime(2013, 1, 3, 4, 31, 13, 148546, tzinfo=utc)

        d_obj_next = delorean.move_datetime_second(self.do.datetime, 'next', 1)
        d_obj_last = delorean.move_datetime_second(self.do.datetime, 'last', 1)

        self.assertEqual(dt_next, d_obj_next)
        self.assertEqual(dt_last, d_obj_last)

    def test_range_count(self):
        """
        tests the range method with count used
        """
        count = list(delorean.stops(delorean.DAILY, count=5))
        self.assertEqual(len(count), 5)

    def test_range_with_start(self):
        dates1 = []
        for do in delorean.stops(delorean.DAILY, count=5, start=datetime.utcnow()):
            do.truncate('minute')
            dates1.append(do)
        do = delorean.Delorean().truncate('minute')
        dates2 = []
        for x in range(5):
            dates2.append(do.next_day(x))
        self.assertEqual(dates1, dates2)

    def test_range_with_start_and_stop(self):
        dates1 = []
        tomorrow = datetime.utcnow() + timedelta(days=1)
        for do in delorean.stops(delorean.DAILY, start=datetime.utcnow(), stop=tomorrow):
            do.truncate('minute')
            dates1.append(do)
        do = delorean.Delorean().truncate('minute')
        dates2 = []
        for x in range(2):
            dates2.append(do.next_day(x))
        self.assertEqual(dates1, dates2)

    def test_range_with_interval(self):
        dates1 = []
        for do in delorean.stops(delorean.DAILY, interval=2, count=3, start=datetime.utcnow()):
            do.truncate('minute')
            dates1.append(do)
        do = delorean.Delorean().truncate('minute')
        dates2 = []
        for x in range(6):
            if (x % 2) == 0:
                dates2.append(do.next_day(x))
        self.assertEqual(dates1, dates2)

    def test_delorean_with_datetime(self):
        dt = datetime.utcnow()
        d = delorean.Delorean(datetime=dt, timezone=UTC)
        dt = utc.localize(dt)
        self.assertEqual(dt, d._dt)
        self.assertEqual(UTC, d._tz)

    def test_delorean_with_timezone(self):
        dt = datetime.utcnow()
        d = delorean.Delorean(datetime=dt, timezone=UTC)
        d = d.shift("US/Eastern")
        dt = utc.localize(dt)
        dt = est.normalize(dt)
        self.assertEqual(dt, d._dt)
        self.assertEqual(est, timezone(d._tz))

    def test_delorean_with_only_timezone(self):
        dt = datetime.utcnow()
        dt = utc.localize(dt)
        dt = est.normalize(dt)
        dt = dt.replace(second=0, microsecond=0)
        d = delorean.Delorean(timezone="US/Eastern")
        d.truncate('minute')
        self.assertEqual(est, timezone(d._tz))
        self.assertEqual(dt, d._dt)

    def testparse_with_timezone(self):
        d1 = delorean.parse("2011/01/01 00:00:00 -0700")
        d2 = datetime(2011, 1, 1, 7, 0)
        d2 = utc.localize(d2)
        self.assertEqual(d2, d1.datetime)
        self.assertEqual(utc, timezone(d1._tz))

    def test_shift_failure(self):
        self.assertRaises(delorean.DeloreanInvalidTimezone, self.do.shift, "US/Westerrn")

    def test_datetime_localization(self):
        dt1 = self.do.datetime
        dt2 = delorean.Delorean(dt1).datetime
        self.assertEquals(dt1, dt2)

    def test_localize_datetime(self):
        dt = datetime.utcnow()
        tz = timezone("US/Pacific")
        dt = tz.localize(dt)
        d = delorean.Delorean(dt)
        d2 = d.shift('US/Pacific')

        self.assertEquals(d._tz, "US/Pacific")
        self.assertEquals(d.datetime, dt)
        self.assertEqual(d.datetime, d2.datetime)

    def test_lt(self):
        dt1 = self.do
        dt2 = delorean.Delorean()
        self.assertTrue(dt1 < dt2)

    def test_gt(self):
        dt1 = self.do
        dt2 = delorean.Delorean()
        self.assertTrue(dt2 > dt1)

    def test_ge(self):
        dt = datetime.utcnow()
        dt1 = delorean.Delorean(dt, timezone="UTC")
        dt2 = delorean.Delorean(dt, timezone="UTC")
        dt3 = self.do
        self.assertTrue(dt2 >= dt1)
        self.assertTrue(dt1 >= dt3)

    def test_le(self):
        dt = datetime.utcnow()
        dt1 = delorean.Delorean(dt, timezone="UTC")
        dt2 = delorean.Delorean(dt, timezone="UTC")
        dt3 = self.do
        self.assertTrue(dt2 <= dt1)
        self.assertTrue(dt3 <= dt2)

    def test_epoch(self):
        unix_time = self.do.epoch()
        self.assertEqual(unix_time, 1357187474.148546)

    def test_epoch_creation(self):
        do = delorean.epoch(1357187474.148546)
        self.assertEqual(self.do, do)

    def test_not_equal(self):
        d = delorean.Delorean()
        self.assertNotEqual(d, None)

    def test_equal(self):
        d1 = delorean.Delorean()
        d2 = deepcopy(d1)
        self.assertEqual(d1, d2)
        self.assertFalse(d1 != d2, 'Overloaded __ne__ is not correct')

    def test_timezone_delorean_to_datetime_to_delorean_utc(self):
        d1 = delorean.Delorean()
        d2 = delorean.Delorean(d1.datetime)

        #these deloreans should be the same
        self.assertEqual(d1.next_day(1), d2.next_day(1))
        self.assertEqual(d2.last_week(), d2.last_week())
        self.assertEqual(d1.timezone(), d2.timezone())
        self.assertEqual(d1, d2)

    def test_timezone_delorean_to_datetime_to_delorean_non_utc(self):
        """Test if when you create Delorean object from Delorean's datetime
        it still behaves the same
        """
        d1 = delorean.Delorean(timezone='America/Chicago')
        d2 = delorean.Delorean(d1.datetime)

        #these deloreans should be the same
        self.assertEqual(d1.next_day(1), d2.next_day(1))
        self.assertEqual(d2.last_week(), d2.last_week())
        self.assertEqual(d1.timezone(), d2.timezone())
        self.assertEqual(d1, d2)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = version
__version__ = (0, 4, 2)

########NEW FILE########
