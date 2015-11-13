__FILENAME__ = default_conf
# -*- coding: utf-8 -*-
"""
------------------------
volt.config.default_conf
------------------------

Volt default configurations.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from volt.config import Config


# Changing values in this Config is allowed but not recommended
VOLT = Config(

    # User config file name
    # Used to determine project root
    USER_CONF = 'voltconf.py',

    # User widget file name
    USER_WIDGET = 'widgets.py',

    # Directory paths for content files, templates, assets, 
    # and generated site relative to a project root
    CONTENT_DIR = 'contents',
    TEMPLATE_DIR = 'templates',
    ASSET_DIR = 'assets',
    SITE_DIR = 'site',
)


# Default site configurations
SITE = Config(

    # Site name
    TITLE = 'My Volt Site',

    # Site URL, used for generating absolute URLs
    URL = 'http://mysite.com',

    # Engines used in generating the site
    # Defaults to none
    ENGINES = (),

    # Extra pages to write that are not controlled by an engine
    # Examples: 404.html, index.html (if not already written by an engine)
    # The tuple should list template names of these pages, which should
    # be present in the default template directory
    PAGES = (),

    # URL to use for pagination
    # This will be used for paginated items after the first one
    # For example, if the pagination URL is 'page', then the second
    # pagination page will have '.../page/2/', the third '.../page/3/', etc.
    PAGINATION_URL = '',

    # Boolean to set if output file names should all be 'index.html' or vary
    # according to the last token in its self.permalist attribute
    # index.html-only outputs allows for nice URLS without fiddling too much
    # with .htaccess
    INDEX_HTML_ONLY = True,

    # Logging level
    # If set to 10, Volt will write logs to a file
    # 30 is logging.WARNING
    LOG_LEVEL = 30,

    # Ignore patterns
    # Filenames that match this pattern will not be copied from asset directory
    # to site directory
    IGNORE_PATTERN = '',

    # String replacement scheme for slugs
    # Dictionary, key is the string to replace, value is the replacement string
    # This is used to replace non-ascii consonants or vowels in a slug with
    # their ascii equivalents, so the slug meaning is preserved.
    # For example {u'ß': 'ss'}, would transfrom the slug "viel-Spaß" to
    # "viel-spass" instead of "viel-spa", preserving its meaning
    SLUG_CHAR_MAP = {},

    # Site plugins
    # These are plugins that work on the whole site
    PLUGINS = (),

    # Site widgets
    # These are widgets that work on the whole site
    WIDGETS = (),

    # Jinja2 filter function names
    FILTERS = ('displaytime',),

    # Jinja2 test function names
    TESTS = ('activatedin', ),
)

########NEW FILE########
__FILENAME__ = default_widgets
# -*- coding: utf-8 -*-
"""
---------------------------
volt.config.default_widgets
---------------------------

Volt default widgets, and jinja2 filters and tests.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

def displaytime(datetime_obj, format):
    """Jinja2 filter for displaying datetime objects according to format.

    datetime_obj -- Datetime object.
    format -- String of datetime format.

    Example usage:
        {{ page.time|displaytime("%Y") }} will output, for example "2012".
    """
    return datetime_obj.strftime(format)


def activatedin(name, config):
    """Jinja2 test for checking whether an engine, plugin, or widget is active.
    
    name -- Name of engine, plugin, or widget.
    config -- UnifiedConfigContainer instance, passed as an argument at render
        time so the values are already primed.

    Example usage:
        {{ if "css_minifier" is activatedin CONFIG }}
            <p>CSS Minifier plugin is active</p>
        {{ endif }}

    or, to check whether several engines/plugins/widgets are active:
        {{ if ["css_minifier", "blog"] is activatedin CONFIG }}
            <p>CSS Minifier plugin and Blog engine are active</p>
        {{ endif }}
    """
    # no need to collect _actives if it's already set
    try:
        actives = config._actives
    # _actives not set, then compute it and do a setattr
    except AttributeError:
        engines = config.SITE.ENGINES
        plugins = config.SITE.PLUGINS
        widgets = config.SITE.WIDGETS

        for conf in config:
            try:
                plugins += getattr(conf, 'PLUGINS')
                widgets += getattr(conf, 'WIDGETS')
            # we don't care if the Config object doesn't have any plugins
            # or widgets (e.g. CONFIG.VOLT)
            except AttributeError:
                pass

        actives = set(engines + plugins + widgets)
        setattr(config, '_actives', actives)

    if isinstance(name, basestring):
        return any([name in x for x in actives])
    else:
        results = []
        for item in name:
            results.append(any([item in x for x in actives]))
        return all(results)


########NEW FILE########
__FILENAME__ = blog
# -*- coding: utf-8 -*-
"""
-------------------------
volt.engine.builtins.blog
-------------------------

Volt Blog Engine.

The blog engine takes text files as resources and writes the static files
constituting a simple blog.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from volt.config import Config
from volt.engine.builtins import TextEngine


ENGINE = 'Blog'


class Blog(TextEngine):

    """Engine for processing text files into a blog.

    This engine uses the TextUnit class to represent its resource. Prior to
    writing the output, the TextUnit objects are sorted according to the
    configuration. They are then chained together by adding to each unit
    permalinks that link to the previous and/or next units.

    It also creates paginations according to the settings in voltconf.py

    """

    # Default configurations for the blog engine
    DEFAULTS = Config(

        # URL for all blog content relative to root URL
        URL = '/blog',

        # Blog post permalink, relative to blog URL
        PERMALINK = '{time:%Y/%m/%d}/{slug}',

        # Date and time format used in blog content headers
        # Used for parsing the headers
        # Default is e.g. '2004-03-13 22:10'
        DATETIME_FORMAT = '%Y/%m/%d %H:%M',

        # Dictionary containing default fields and their values for all units
        DEFAULT_FIELDS = {},

        # Directory path for storing blog content 
        # relative to the default Volt content directory
        CONTENT_DIR = 'blog',

        # Unit filename pattern to match
        # Defaults to '*' (match all files)
        UNIT_FNAME_PATTERN = '*',

        # File paths of blog template files
        # relative to the default Volt template directory
        UNIT_TEMPLATE = 'blog_unit.html',
        PAGINATION_TEMPLATE = 'blog_pagination.html',

        # Sort order for paginated posts display
        # Valid options are any field present in all units
        # Default order is A-Z (for alphabets) and past-present (for dates)
        # To reverse order just add '-' in front, e.g. '-time'
        SORT_KEY = '-time',

        # The number of displayed posts per pagination page
        UNITS_PER_PAGINATION = 10,

        # Excerpt length (in characters) for paginated items
        EXCERPT_LENGTH = 400,

        # Pagination to build for the static site
        # Items in this tuple will be used to set the paginations relative to
        # the blog URL. Items enclosed in '{}' are pulled from the unit values,
        # e.g. 'tag/{tags}' will be expanded to 'tag/x' for x in each tags in the
        # site. These field tokens must be the last token of the pattern.
        # Use an empty string ('') to apply packing to all blog units
        PAGINATIONS = ('',),

        # Protected properties
        # These properties must not be defined by any individual blog post header,
        # since they are used internally
        PROTECTED = ('id', 'content', ),

        # Required properties
        # These properties must be defined in each individual blog post header
        REQUIRED = ('title', 'time', ),

        # Fields that would be transformed from string into datetime objects using
        # DATETIME_FORMAT as the pattern
        FIELDS_AS_DATETIME = ('time', ),

        # Fields that would be transformed from string into list objects using
        # LIST_SEP as a separator
        FIELDS_AS_LIST = ('tags', 'categories', ),
        LIST_SEP = ', '
    )

    # Config instance name in voltconf.py
    USER_CONF_ENTRY = 'ENGINE_BLOG'

    def preprocess(self):
        # sort units
        self.sort_units()
        # add prev and next permalinks so blog posts can link to each other
        self.chain_units()

    def dispatch(self):
        # write output files
        self.write_units()
        self.write_paginations()

########NEW FILE########
__FILENAME__ = plain
# -*- coding: utf-8 -*-
"""
--------------------------
volt.engine.builtins.plain
--------------------------

Volt Plain Engine.

The plain engine takes text files as resources and writes single web pages.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from volt.config import Config
from volt.engine.builtins import TextEngine


ENGINE = 'Plain'


class Plain(TextEngine):

    """Class for processing plain web pages."""

    # Default configurations for the plain engine
    DEFAULTS = Config(
        # URL for all plain page content relative to root URL
        URL = '/plain',

        # Plain page permalink, relative to plain page URL
        PERMALINK = '{slug}',

        # Date and time format used in plain page content headers
        # Used for parsing the headers
        # Default is e.g. '2004-03-13 22:10'
        DATETIME_FORMAT = '%Y/%m/%d %H:%M',

        # Directory path for storing plain page content
        # relative to the default Volt content directory
        CONTENT_DIR = 'plain',

        # Unit filename pattern to match
        # Defaults to '*' (match all files)
        UNIT_FNAME_PATTERN = '*',

        # File paths of plain page template files
        # relative to the default Volt template directory
        UNIT_TEMPLATE = 'plain_unit.html',

        # Required properties
        # These properties must be defined in each individual plain page unit header
        REQUIRED = ('title', ),

        # Dictionary containing default fields and their values for all units
        DEFAULT_FIELDS = {},

        # Protected properties
        # These properties must not be defined by any individual plain page header,
        # since they are used internally
        PROTECTED = ('id', 'content', ),

        # Fields that would be transformed from string into datetime objects using
        # DATETIME_FORMAT as the pattern
        FIELDS_AS_DATETIME = ('time', ),

        # Fields that would be transformed from string into list objects using
        # LIST_SEP as a separator
        FIELDS_AS_LIST = ('tags', 'categories', ),
        LIST_SEP = ', ',
    )

    # Config instance name in voltconf.py
    USER_CONF_ENTRY = 'ENGINE_PLAIN'

    def dispatch(self):
        # write them according to template
        self.write_units()

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
----------------
volt.engine.core
----------------

Volt core engine classes.

Contains the Engine, Page, Unit, and Pagination classes.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from __future__ import with_statement
import abc
import codecs
import os
import re
import sys
import warnings
from datetime import datetime
from functools import partial, reduce
from traceback import format_exc

from volt.config import CONFIG, Config
from volt.exceptions import EmptyUnitsWarning
from volt.utils import LoggableMixin, cachedproperty, path_import, write_file


# required engine config values
_REQUIRED_ENGINE_CONFIG = ('URL', 'CONTENT_DIR', 'PERMALINK',)

# required engine config for paginations
_REQUIRED_ENGINE_PAGINATIONS = ('PAGINATIONS', 'UNITS_PER_PAGINATION',)

# regex objects for unit header and permalink processing
_RE_DELIM = re.compile(r'^---$', re.MULTILINE)
_RE_SPACES = re.compile(r'\s([A|a]n??)\s|_|\s+')
_RE_PRUNE = re.compile(r'A-|An-|[^a-zA-Z0-9_-]')
_RE_MULTIPLE = re.compile(r'-+')
_RE_PERMALINK = re.compile(r'(.+?)/+(?!%)')


# chain item permalinks, for Engine.units and Engine.paginations
def chain_item_permalinks(items):
    """Sets the previous and next permalink attributes of items.

    items -- List containing item to chain.

    This method sets a 'permalink_prev' and 'permalink_next' attribute
    for each item in the given list, which are permalinks to the previous
    and next items.

    """
    for idx, item in enumerate(items):
        if idx != 0:
            setattr(item, 'permalink_prev', items[idx-1].permalink)
        if idx != len(items) - 1:
            setattr(item, 'permalink_next', items[idx+1].permalink)


class Engine(LoggableMixin):

    """Base Volt Engine class.

    Engine is the core component of Volt that performs initial processing
    of each unit. This base engine class does not perform any processing by
    itself, but provides convenient unit processing methods for the
    subclassing engine.

    Any subclass of Engine must create a 'units' property and override the
    dispatch method. Optionally, the preprocess method may be overridden if any
    unit processing prior to plugin run needs to be performed.

    """

    __metaclass__ = abc.ABCMeta

    DEFAULTS = Config()

    def __init__(self):
        self.config = Config(self.DEFAULTS)
        self.logger.debug('created: %s' % type(self).__name__)
        self._templates = {}
        # attributes below are placeholders for template access later on
        self.widgets = {}

    def preprocess(self):
        """Performs initial processing of units before plugins are run."""
        pass

    @abc.abstractmethod
    def dispatch(self):
        """Performs final processing after all plugins are run."""

    @abc.abstractmethod
    def units(self):
        """Units of the engine."""

    def prime(self):
        """Consolidates default engine Config and user-defined Config.

        In addition to consolidating Config values, this method also sets
        the values of CONTENT_DIR, and *_TEMPLATE to absolute directory paths.

        """
        # get user config object
        conf_name = os.path.splitext(os.path.basename(CONFIG.VOLT.USER_CONF))[0]
        user_conf = path_import(conf_name, CONFIG.VOLT.ROOT_DIR)

        # custom engines must define an entry name for the user's voltconf
        if not hasattr (self, 'USER_CONF_ENTRY'):
            message = "%s must define a %s value as a class attribute." % \
                    (type(self).__name__, 'USER_CONF_ENTRY')
            self.logger.error(message)

        # use default config if the user does not specify any
        try:
            user_config = getattr(user_conf, self.USER_CONF_ENTRY)
        except AttributeError:
            user_config = Config()

        # to ensure proper Config consolidation
        if not isinstance(user_config, Config):
            message = "User Config object '%s' must be a Config instance." % \
                    self.USER_CONF_ENTRY
            self.logger.error(message)
            raise TypeError(message)
        else:
            self.config.update(user_config)

        # check attributes that must exist
        for attr in _REQUIRED_ENGINE_CONFIG:
            try:
                getattr(self.config, attr)
            except AttributeError:
                message = "%s Config '%s' value is undefined." % \
                        (type(self).__name__, attr)
                self.logger.error(message)
                self.logger.debug(format_exc())
                raise

        # set engine config paths to absolute paths
        self.config.CONTENT_DIR = os.path.join(CONFIG.VOLT.CONTENT_DIR, \
                self.config.CONTENT_DIR)
        for template in [x for x in self.config.keys() if x.endswith('_TEMPLATE')]:
                self.config[template] = os.path.join(CONFIG.VOLT.TEMPLATE_DIR, \
                        self.config[template])

    def chain_units(self):
        """Sets the previous and next permalink attributes of each unit."""
        chain_item_permalinks(self.units)
        self.logger.debug('done: chaining units')

    def sort_units(self):
        """Sorts a list of units according to the given header field name."""
        sort_key = self.config.SORT_KEY
        reversed = sort_key.startswith('-')
        sort_key = sort_key.strip('-')
        try:
            self.units.sort(key=lambda x: getattr(x, sort_key), reverse=reversed)
        except AttributeError:
            message = "Sort key '%s' not present in all units." % sort_key
            self.logger.error(message)
            self.logger.debug(format_exc())
            raise

        self.logger.debug("done: sorting units based on '%s'" % self.config.SORT_KEY)

    @cachedproperty
    def paginations(self):
        """Paginations of engine units in a dictionary.

        The computation will expand the supplied patterns according to the values
        present in all units. For example, if the pattern is '{time:%Y}' and
        there are five units with a datetime.year attribute 2010 and another
        five with 2011, create_paginations will return a dictionary with one key
        pointing to a list containing paginations for 'time/2010' and
        'time/2011'. The number of actual paginations vary, depending on how
        many units are in one pagination.

        """
        # check attributes that must exist
        for attr in _REQUIRED_ENGINE_PAGINATIONS:
            try:
                getattr(self.config, attr)
            except AttributeError:
                message = "%s Config '%s' value is undefined." % \
                        (type(self).__name__, attr)
                self.logger.error(message)
                self.logger.debug(format_exc())
                raise

        base_url = self.config.URL.strip('/')
        units_per_pagination = self.config.UNITS_PER_PAGINATION
        pagination_patterns = self.config.PAGINATIONS

        # create_paginations operates on self.units
        units = self.units
        if not units:
            warnings.warn("%s has no units to paginate." % type(self).__name__, \
                    EmptyUnitsWarning)
            # exit function if there's no units to process
            return {}

        paginator_map = {
                'all': self._paginate_all,
                'str': self._paginate_single,
                'int': self._paginate_single,
                'float': self._paginate_single,
                'list': self._paginate_multiple,
                'tuple': self._paginate_multiple,
                'datetime': self._paginate_datetime,
        }

        paginations = {}
        for pattern in pagination_patterns:

            perm_tokens = re.findall(_RE_PERMALINK, pattern.strip('/') + '/')
            base_permalist = [base_url] + perm_tokens

            # only the last token is allowed to be enclosed in '{}'
            for token in base_permalist[:-1]:
                if '{%s}' % token[1:-1] == token:
                    message = "Pagination pattern %s is invalid." % pattern
                    self.logger.error(message)
                    raise ValueError(message)

            # determine which paginate method to use based on field type
            last_token = base_permalist[-1]
            field = last_token[1:-1]
            if '{%s}' % field != last_token:
                field_type = 'all'
            else:
                sample = getattr(units[0], field.split(':')[0])
                field_type = sample.__class__.__name__

            try:
                paginate = paginator_map[field_type]
            except KeyError:
                message = "Pagination method for '%s' has not been " \
                          "implemented." % field_type
                self.logger.error(message)
                self.logger.debug(format_exc())
                raise
            else:
                args = [field, base_permalist, units_per_pagination]
                # if pagination_patterns is a dict, then use the supplied
                # title pattern
                if isinstance(pagination_patterns, dict):
                    args.append(pagination_patterns[pattern])

                pagination_in_pattern = paginate(*args)
                key = '/'.join(base_permalist)
                paginations[key] = pagination_in_pattern

        return paginations

    def _paginate_all(self, field, base_permalist, units_per_pagination, \
            title_pattern=''):
        """Create paginations for all field values (PRIVATE)."""
        paginated = self._paginator(self.units, base_permalist, \
                units_per_pagination, title_pattern)

        self.logger.debug('created: %d %s paginations' % (len(paginated), 'all'))
        return paginated

    def _paginate_single(self, field, base_permalist, units_per_pagination, \
            title_pattern=''):
        """Create paginations for string/int/float header field values (PRIVATE)."""
        units = self.units
        str_set = set([getattr(x, field) for x in units])

        paginated = []
        for item in str_set:
            matches = [x for x in units if item == getattr(x, field)]
            base_permalist = base_permalist[:-1] + [str(item)]
            if title_pattern:
                title = title_pattern % str(item)
            else:
                title = title_pattern
            pagin = self._paginator(matches, base_permalist, \
                    units_per_pagination, title)
            paginated.extend(pagin)

        self.logger.debug('created: %d %s paginations' % (len(paginated), field))
        return paginated

    def _paginate_multiple(self, field, base_permalist, units_per_pagination, \
            title_pattern=''):
        """Create paginations for list or tuple header field values (PRIVATE)."""
        units = self.units
        item_list_per_unit = (getattr(x, field) for x in units)
        item_set = reduce(set.union, [set(x) for x in item_list_per_unit])

        paginated = []
        for item in item_set:
            matches = [x for x in units if item in getattr(x, field)]
            base_permalist = base_permalist[:-1] + [str(item)]
            if title_pattern:
                title = title_pattern % str(item)
            else:
                title = title_pattern
            pagin = self._paginator(matches, base_permalist, \
                    units_per_pagination, title)
            paginated.extend(pagin)

        self.logger.debug('created: %d %s paginations' % (len(paginated), field))
        return paginated

    def _paginate_datetime(self, field, base_permalist, \
            units_per_pagination, title_pattern=''):
        """Create paginations for datetime header field values (PRIVATE)."""
        units = self.units
        # separate the field name from the datetime formatting
        field, time_fmt = field.split(':')
        time_tokens = time_fmt.strip('/').split('/')
        unit_times = [getattr(x, field) for x in units]
        # construct set of all datetime combinations in units according to
        # the user's supplied pagination URL; e.g. if URL == '%Y/%m' and
        # there are two units with 2009/10 and one with 2010/03 then
        # time_set == set([('2009', '10), ('2010', '03'])
        time_strs = [[x.strftime(y) for x in unit_times] for y in time_tokens]
        time_set = set(zip(*time_strs))

        paginated = []
        # create placeholders for new tokens
        base_permalist = base_permalist[:-1] + [None] * len(time_tokens)
        for item in time_set:
            # get all units whose datetime values match 'item'
            matches = []
            for unit in units:
                val = getattr(unit, field)
                time_str = [[val.strftime(y)] for y in time_tokens]
                time_tuple = zip(*time_str)
                assert len(time_tuple) == 1
                if item in time_tuple:
                    matches.append(unit)

            base_permalist = base_permalist[:-(len(time_tokens))] + list(item)
            if title_pattern:
                title = getattr(matches[0], field).strftime(title_pattern)
            else:
                title = title_pattern
            pagin = self._paginator(matches, base_permalist, \
                    units_per_pagination, title)
            paginated.extend(pagin)

        self.logger.debug('created: %d %s paginations' % (len(paginated), field))
        return paginated

    def _paginator(self, units, base_permalist, units_per_pagination, title=''):
        """Create paginations from units (PRIVATE).

        units -- List of all units which will be paginated.
        base_permalist -- List of permalink tokens that will be used by all
                          paginations of the given units.
        units_per_pagination -- Number of units to show per pagination.
        title -- String to use as the pagination title.

        """
        paginations = []

        # count how many paginations we need
        is_last = len(units) % units_per_pagination != 0
        pagination_len = len(units) // units_per_pagination + int(is_last)

        # construct pagination objects for each pagination page
        for idx in range(pagination_len):
            start = idx * units_per_pagination
            if idx != pagination_len - 1:
                stop = (idx + 1) * units_per_pagination
                units_in_pagination = units[start:stop]
            else:
                units_in_pagination = units[start:]

            pagination = Pagination(units_in_pagination, idx, base_permalist, \
                    title)
            paginations.append(pagination)

        if len(paginations) > 1:
            chain_item_permalinks(paginations)
            self.logger.debug('done: chaining paginations')

        return paginations

    def write_units(self):
        """Writes units using the unit template file."""
        self._write_items(self.units, self.config.UNIT_TEMPLATE)
        self.logger.debug('written: %d %s unit(s)' % (len(self.units), \
                type(self).__name__[:-len('Engine')]))

    def write_paginations(self):
        """Writes paginations using the pagination template file."""
        for pattern in self.paginations:
            self._write_items(self.paginations[pattern], self.config.PAGINATION_TEMPLATE)
            self.logger.debug("written: '%s' pagination(s)" % pattern)

    def _write_items(self, items, template_path):
        """Writes Page objects using the given template file (PRIVATE).

        items -- List of Page objects to be written.
        template_path -- Template file name, must exist in the defined
                         template directory.

        """
        template_env = CONFIG.SITE.TEMPLATE_ENV
        template_file = os.path.basename(template_path)

        # get template from cache if it's already loaded
        if template_file not in self._templates:
            template = template_env.get_template(template_file)
            self._templates[template_file] = template
        else:
            template = self._templates[template_file]

        for item in items:
            # warn if files are overwritten
            # this indicates a duplicate post, which could result in
            # unexpected results
            if os.path.exists(item.path):
                message = "File %s already exists. Make sure there are no "\
                          "other entries leading to this file path." % item.path
                self.logger.error(message)
                raise IOError(message)
            else:
                rendered = template.render(page=item, CONFIG=CONFIG, \
                        widgets=self.widgets)
                if sys.version_info[0] < 3:
                    rendered = rendered.encode('utf-8')
                write_file(item.path, rendered)


class Page(LoggableMixin):

    """Class representing resources that may have its own web page, such as
    a Unit or a Pagination."""

    __metaclass__ = abc.ABCMeta

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, self.id)

    @abc.abstractproperty
    def permalist(self):
        """List of tokens used to construct permalink and path."""

    @abc.abstractproperty
    def id(self):
        """Unique string that identifies the Page object."""

    @cachedproperty
    def path(self):
        """Filesystem path to Page object file."""
        base_path = [CONFIG.VOLT.SITE_DIR]
        base_path.extend(self.permalist)

        if CONFIG.SITE.INDEX_HTML_ONLY:
            base_path.append('index.html')
        else:
            base_path[-1] += '.html'

        return os.path.join(*base_path)

    @cachedproperty
    def permalink(self):
        """Relative URL to the Page object."""
        rel_url = ['']
        rel_url.extend(filter(None, self.permalist))

        if CONFIG.SITE.INDEX_HTML_ONLY:
            rel_url[-1] += '/'
        else:
            rel_url[-1] += '.html'

        return '/'.join(rel_url)

    @cachedproperty
    def permalink_abs(self):
        """Absolute URL to the Page object."""
        return '/'.join([CONFIG.SITE.URL, self.permalink[1:]]).strip('/')

    def slugify(self, string):
        """Returns a slugified version of the given string."""
        string = string.strip()

        # perform user-defined character mapping
        for target in CONFIG.SITE.SLUG_CHAR_MAP:
            string = string.replace(target, CONFIG.SITE.SLUG_CHAR_MAP[target])

        # replace spaces, etc with dash
        string = re.sub(_RE_SPACES, '-', string)

        # remove english articles, and non-ascii characters
        string = re.sub(_RE_PRUNE, '', string)

        # slug should not begin or end with dash or contain multiple dashes
        string = re.sub(_RE_MULTIPLE, '-', string)

        # and finally, we string preceeding and succeeding dashes
        string = string.lower().strip('-')

        # error if slug is empty
        if not string:
            message = "Slug for '%s' is an empty string." % self.id
            self.logger.error(message)
            raise ValueError(message)

        return string


class Unit(Page):

    """Base Volt Unit class.

    The unit class represent a single resource used for generating the site,
    such as a blog post, an image, or a regular plain text file.

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """Initializes a unit instance.

        id -- Unique string to identify the unit.
        config -- Config object of the calling Engine.

        Config objects are required to instantiate the Unit since some unit
        configuration values depends on the calling Engine configuration
        values.

        """
        if not isinstance(config, Config):
            message = "Units must be instantiated with their engine's " \
                    "Config object."
            self.logger.error(message)
            raise TypeError(message)
        self.config = config

    @cachedproperty
    def permalist(self):
        """Returns a list of strings which will be used to construct permalinks.

        For the permalist to be constructed, the calling Engine must define a
        'PERMALINK' string in its Config object.

        The permalink string pattern may refer to the current unit's attributes
        by enclosing them in square brackets. If the referred instance attribute
        is a datetime object, it must be formatted by specifying a string format
        argument.

        Several examples of a valid permalink pattern:

        '{time:%Y/%m/%d}/{slug}'
            Returns, for example, ['2009', '10', '04', 'the-slug']

        'post/{time:%d}/{id}'
            Returns, for example,  ['post', '04', 'item-103']

        """
        # strip preceeding '/' but make sure ends with '/'
        pattern = self.config.PERMALINK.strip('/') + '/'
        unit_base_url = self.config.URL

        # get all permalink components and store into list
        perm_tokens = re.findall(_RE_PERMALINK, pattern)

        # process components that are enclosed in {}
        permalist = []
        for token in perm_tokens:
            if '{%s}' % token[1:-1] == token:
                field = token[1:-1]
                if ':' in field:
                    field, fmt = field.split(':')

                try:
                    attr = getattr(self, field)
                except AttributeError:
                    message = "'%s' has no '%s' attribute." % (self.id, field)
                    self.logger.error(message)
                    self.logger.debug(format_exc())
                    raise

                if isinstance(attr, datetime):
                    strftime = datetime.strftime(attr, fmt)
                    permalist.extend(filter(None, strftime.split('/')))
                else:
                    permalist.append(self.slugify(attr))
            else:
                permalist.append(self.slugify(token))

        return [unit_base_url.strip('/')] + filter(None, permalist)

    # convenience methods
    open_text = partial(codecs.open, encoding='utf-8')
    as_datetime = datetime.strptime

    def parse_header(self, header_string):
        """Returns a dictionary of header field values.

        header_string -- String of header lines.

        """
        header_lines = [x.strip() for x in header_string.strip().split('\n')]
        for line in header_lines:
            if not ':' in line:
                    raise ValueError("Line '%s' in '%s' is not a proper "
                            "header entry." % (line, self.id))
            field, value = [x.strip() for x in line.split(':', 1)]

            self.check_protected(field, self.config.PROTECTED)

            if field == 'slug':
                value = self.slugify(value)

            elif field in self.config.FIELDS_AS_LIST:
                value = self.as_list(value, self.config.LIST_SEP)

            elif field in self.config.FIELDS_AS_DATETIME:
                value = self.as_datetime(value, \
                        self.config.DATETIME_FORMAT)

            setattr(self, field.lower(), value)

    def check_protected(self, field, prot):
        """Checks if the given field can be set by the user or not.
        
        field -- String to check against the list containing protected fields.
        prot -- Iterable returning string of protected fields.

        """
        if field in prot:
            message = "'%s' should not define the protected header field " \
                    "'%s'" % (self.id, field)
            self.logger.error(message)
            raise ValueError(message)

    def check_required(self, req):
        """Checks if all the required header fields are present.

        req -- Iterable returning string of required header fields.

        """
        if isinstance(req, str):
            req = [req]
        for field in req:
            if not hasattr(self, field):
                message = "Required header field '%s' is missing in '%s'." % \
                        (field, self.id)
                self.logger.error(message)
                raise NameError(message)

    def as_list(self, field, sep):
        """Transforms a character-separated string field into a list.

        fields -- String to transform into list.
        sep -- String used to split fields into list.

        """
        return list(set(filter(None, field.strip().split(sep))))


class Pagination(Page):

    """Class representing a single paginated HTML file.

    The pagination class computes the necessary attributes required to write
    a single HTML file containing the desired units. It is the __dict__ object
    of this Pagination class that will be passed on to the template writing
    environment. The division of which units go to which pagination
    page is done by another method.

    """

    def __init__(self, units, pagin_idx, base_permalist=[], title=None):
        """Initializes a Pagination instance.

        units -- List containing units to paginate.
        pagin_idx -- Number of current pagination object index.
        base_permalist -- List of URL components common to all pagination
                          permalinks.
        title -- String denoting the title of the pagination page.

        """
        self.units = units
        self.title = title

        # since paginations are 1-indexed
        self.pagin_idx = pagin_idx + 1
        # precautions for empty string, so double '/'s are not introduced
        self.base_permalist = filter(None, base_permalist)
        self.logger.debug('created: %s' % self.id)

    @cachedproperty
    def id(self):
        return self.permalink

    @cachedproperty
    def permalist(self):
        """Returns a list of strings which will be used to construct permalinks."""
        permalist = self.base_permalist
        # add pagination url and index if it's not the first pagination page
        if self.pagin_idx > 1:
            permalist += filter(None, [CONFIG.SITE.PAGINATION_URL, \
                    str(self.pagin_idx)])

        return permalist

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""
---------------
volt.exceptions
---------------

Volt exception classes.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

# Volt config exceptions
class ConfigNotFoundError(Exception):
    """Raised when Volt fails to find voltconf.py."""

# Volt engine warning and exceptions
class EmptyUnitsWarning(RuntimeWarning):
    """Issued when paginations is called without any units to pack in self.units."""

########NEW FILE########
__FILENAME__ = generator
# -*- coding: utf-8 -*-
"""
--------------
volt.generator
--------------

Volt main site generator.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from __future__ import with_statement
import logging
import os
import shutil
import sys
from functools import partial
from time import time
from traceback import format_exc

from volt import __version__
from volt.config import CONFIG
from volt.utils import cachedproperty, console, path_import, write_file, LoggableMixin


console = partial(console, format="[gen] %s  %s\n")


class Site(LoggableMixin):

    """Class representing a Volt site generation run."""

    def __init__(self):
        self.engines = {}
        self.plugins = {}
        self.widgets = {}

    @cachedproperty
    def config(self):
        return CONFIG

    def create(self):
        """Generates the static site.

        This method consists of five distinct steps that results in the final
        site generation:

            1. Output directory preparation: contents from the 'asset'
               directory are copied into a new 'site' directory. If a 'site'
               directory exists prior to the copying, it will be removed.

            2. Engine activation: see the activate_engines method.

            3. Site plugin run and site widget creation: all site plugins are
               run and all site widgets are created

            4. Engine dispatch: see the dispatch_engines method.

            5. Non-engine template processing: site pages that do not belong to
               any engines are then processed. Examples of pages in this
               category are the main index.html and the 404 page. If any engine
               has defined a main index.html, this method will not write
               another index.html.

        """
        self.prepare_output()
        self.activate_engines()
        self.run_plugins()
        self.create_widgets()
        self.dispatch_engines()
        self.write_site_pages()

    def get_processor(self, processor_name, processor_type, \
            volt_dir=os.path.dirname(__file__)):
        """Returns the engine or plugin class used in site generation.

        processor_name -- String denoting engine or plugin name.
        processor_type -- String denoting processor type. Must be 'engines'
                          or 'plugins'.
        volt_dir -- String denoting absolute path to Volt's installation
                    directory.
        
        This method tries to load engines or plugins from the user's Volt
        project directory first. Failing that, it will try to import engines
        or plugins from Volt's installation directory.

        """
        # check first if processor type is 'plugins' or 'engines'
        assert processor_type in ['engines', 'plugins'], \
            "Processor type must be 'engines' or 'plugins'"

        # load engine or plugin
        # user_path has priority over volt_path
        user_dir = self.config.VOLT.ROOT_DIR
        user_path = os.path.join(user_dir, processor_type)
        volt_path = os.path.join(volt_dir, processor_type[:-1], 'builtins')

        mod = path_import(processor_name, [user_path, volt_path])

        if processor_type == 'engines':
            cls_name = getattr(mod, 'ENGINE')
        else:
            cls_name = getattr(mod, 'PLUGIN')

        return getattr(mod, cls_name)

    def prepare_output(self):
        """Copies the asset directory contents to site directory."""
        message = "Preparing output directory: %s" % self.config.VOLT.SITE_DIR
        console(message)
        self.logger.debug(message)
        if os.path.exists(self.config.VOLT.SITE_DIR):
            shutil.rmtree(self.config.VOLT.SITE_DIR)
        shutil.copytree(self.config.VOLT.ASSET_DIR, self.config.VOLT.SITE_DIR, \
                ignore=shutil.ignore_patterns(self.config.SITE.IGNORE_PATTERN))

    def activate_engines(self):
        """Activates all engines according to the configurations.

        This method consists of four steps:

            1. Engine priming: all engines listed in CONFIG.SITE.ENGINES are
               loaded. Any engines found in the user directory takes
               precedence over built-in engines. The default settings in each
               engine are then consolidated with the user's setting in
               voltconf.py to yield the final configurations that will be used
               in subsequent engine methods.

            2. Engine preprocessing: all the engines' preprocess() method are
               then run. Any unit processing that happens before the plugins
               are run is done by the preprocess method.

            3. Plugin run: plugins targeting each engine are run to process the
               the target engines' units. Similar to engines, plugins are also
               primed to consolidate the default and user configurations.

            4. Widget creation: widgets for each engine are created and made
               accessible from the any templates.
        """
        for engine_name in self.config.SITE.ENGINES:
            engine_class = self.get_processor(engine_name, 'engines')
            engine = engine_class()
            message = "Engine loaded: %s" % engine_name.capitalize()
            console(message, color='cyan')
            self.logger.debug(message)

            engine.prime()
            self.logger.debug('done: priming %s' % engine_class.__name__)

            engine.preprocess()
            self.logger.debug('done: preprocessing %s' % engine_class.__name__)

            self.run_plugins(engine)
            self.create_widgets(engine)
            self.engines[engine_name] = engine

            # attach engine config values for access in templates
            setattr(self.config, self.engines[engine_name].USER_CONF_ENTRY, \
                    self.engines[engine_name].config)

    def run_plugins(self, engine=None):
        """Runs plugins on engine or site."""
        if engine is not None:
            try:
                plugins = engine.config.PLUGINS
            except AttributeError:
                return
        else:
            plugins = self.config.SITE.PLUGINS

        for plugin in plugins:
            if engine is not None:
                message = "Running engine plugin: %s" % (plugin)
            else:
                message = "Running site plugin: %s" % plugin
            console(message)
            self.logger.debug(message)

            if not plugin in self.plugins:
                try:
                    plugin_class = self.get_processor(plugin, 'plugins')
                except ImportError:
                    message = "Plugin %s not found." % plugin
                    self.logger.error(message)
                    self.logger.debug(format_exc())
                    raise

                self.plugins[plugin] = plugin_class()
                self.plugins[plugin].prime()

            if engine is not None:
                # engine plugins work on their engine instances
                self.plugins[plugin].run(engine)
            else:
                # site plugins work on this site instance
                self.plugins[plugin].run(self)

            # attach plugin config values (if defined) for access in templates
            if self.plugins[plugin].USER_CONF_ENTRY is not None:
                setattr(self.config, self.plugins[plugin].USER_CONF_ENTRY, \
                        self.plugins[plugin].config)

            self.logger.debug("ran: %s plugin" % plugin)

    @cachedproperty
    def widgets_mod(self):
        self.logger.debug('imported: widgets module')
        return path_import('widgets', self.config.VOLT.ROOT_DIR)

    def create_widgets(self, engine=None):
        """Create widgets from engine or site."""
        if engine is not None:
            try:
                widgets = engine.config.WIDGETS
            except AttributeError:
                return
        else:
            widgets = self.config.SITE.WIDGETS

        for widget in widgets:
            if engine is not None:
                message = "Creating engine widget: %s" % widget
            else:
                message = "Creating site widget: %s" % widget
            console(message)
            self.logger.debug(message)

            try:
                widget_func = getattr(self.widgets_mod, widget)
            except AttributeError:
                message = "Widget %s not found." % widget
                self.logger.error(message)
                self.logger.debug(format_exc())
                raise

            if engine is not None:
                # engine widgets work on their engine instances
                self.widgets[widget] = widget_func(engine)
            else:
                # site widgets work on this site instance
                self.widgets[widget] = widget_func(self)
            self.logger.debug("created: %s widget" % widget)

    def dispatch_engines(self):
        """Runs the engines' dispatch method."""
        for engine in self.engines:
            message = "Dispatching %s engine to URL '%s'" % \
                    (engine.lower(), self.engines[engine].config.URL)
            console(message)
            self.logger.debug(message)
            # attach all widgets to each engine, so they're accessible in templates
            self.engines[engine].widgets = self.widgets
            # dispatch them
            self.engines[engine].dispatch()

    def write_site_pages(self):
        """Write site pages, such as a separate index.html or 404.html."""
        for filename in self.config.SITE.PAGES:
            message = "Writing site page: '%s'" % filename
            console(message)
            self.logger.debug(message)

            template = self.config.SITE.TEMPLATE_ENV.get_template(filename)
            path = os.path.join(self.config.VOLT.SITE_DIR, filename)
            if os.path.exists(path):
                message = "File %s already exists. Make sure there are no "\
                          "other entries leading to this file path." % path
                console("Error: %s" % message, is_bright=True, color='red')
                self.logger.error(message)
                sys.exit(1)

            rendered = template.render(page={}, CONFIG=self.config, \
                    widgets=self.widgets)
            if sys.version_info[0] < 3:
                rendered = rendered.encode('utf-8')
            write_file(path, rendered)


def run():
    """Generates the site."""
    logger = logging.getLogger('gen')

    sys.stdout.write("\n")
    message = "Volt %s Static Site Generator" % __version__
    console(message, is_bright=True)
    logger.debug(message)

    # generate the site!
    start_time = time()
    Site().create()

    message = "Site generated in %.3fs" % (time() - start_time)
    console(message, color='yellow')
    logger.debug(message)
    sys.stdout.write('\n')

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
"""
---------
volt.main
---------

Entry point for Volt run.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>

"""

import argparse
import logging
import os
import shutil
import sys
from functools import partial
from datetime import datetime

from volt import __version__, generator, server
from volt.config import CONFIG
from volt.exceptions import ConfigNotFoundError
from volt.utils import console, LoggableMixin


console = partial(console, format="%s\n", log_time=False)


class ArgParser(argparse.ArgumentParser):
    """Custom parser that prints help message when an error occurs."""
    def error(self, message):
        console("\nError: %s" % message, color='red', is_bright=True)
        self.print_usage()
        sys.stdout.write("\n")
        sys.exit(1)


class Runner(LoggableMixin):

    """ Class representing Volt run."""

    def build_logger(self):
        """Initializes package-wide logger."""
        file_format = '[%(asctime)s.%(msecs)03d] %(levelname)-8s %(name)s.%(funcName)s  %(message)s'
        date_format = '%H:%M:%S'
        stderr_format = 'Error: %(message)s'
        if os.name != 'nt':
            stderr_format = '\033[01;31m%s\033[m' % stderr_format

        logger = logging.getLogger('')
        logger.setLevel(CONFIG.SITE.LOG_LEVEL)

        stderr = logging.StreamHandler(sys.stderr)
        stderr.setLevel(logging.ERROR)
        formatter = logging.Formatter(stderr_format, datefmt=date_format)
        stderr.setFormatter(formatter)
        logger.addHandler(stderr)

        if CONFIG.SITE.LOG_LEVEL <= logging.DEBUG:
            # setup file logging
            logfile = logging.FileHandler('volt.log')
            logfile.setLevel(logging.DEBUG)
            formatter = logging.Formatter(file_format, datefmt=date_format)
            logfile.setFormatter(formatter)
            logger.addHandler(logfile)

            with open('volt.log', 'w') as log:
                log.write("#Volt %s Log\n" % __version__)
                log.write("#Date: %s\n" % datetime.now().strftime("%Y-%m-%d"))
                log.write("#Fields: time, log-level, caller, log-message\n")

    def build_parsers(self):
        """Build parser for arguments."""
        parser = ArgParser()
        subparsers = parser.add_subparsers(title='subcommands')

        # parser for demo
        demo_parser = subparsers.add_parser('demo',
                help="quick Volt demo")

        # parser for ext
        ext_parser = subparsers.add_parser('ext',
                help="adds template for custom engine, plugin, or widget")
        ext_parser.add_argument('template', type=str,
                choices=['engine', 'plugin', 'widget'],
                help="extension type")
        ext_parser.add_argument('--builtin', type=str, dest='builtin', 
                default='', metavar='NAME', help='builtin extension name')

        # parser for gen
        gen_parser = subparsers.add_parser('gen',
                help="generates Volt site using the specified engines")

        # parser for init
        init_parser = subparsers.add_parser('init',
                help="starts a bare Volt project")

        # parser for serve
        serve_parser = subparsers.add_parser('serve',
                help="serve generated volt site")
        serve_parser.add_argument('-p', '--port', dest='server_port',
                                   default='8000', type=int,
                                   metavar='PORT',
                                   help='server port')

        # parser for version
        # bit of a hack, so version can be shown without the "--"
        version_parser = subparsers.add_parser('version',
                                               help="show version number and exit")

        # sets the function to run for each subparser option
        # e.g. subcmd = 'server', it will set the function to run_server
        for subcmd in subparsers.choices.keys():
            eval('%s_parser' % subcmd).set_defaults(run=eval('self.run_%s' % subcmd), name=subcmd)

        return parser

    def run_ext(self):
        """Adds template for engine, plugin, or widget."""
        builtin = CONFIG.CMD.builtin
        template = CONFIG.CMD.template
        volt_dir = os.path.dirname(__file__)
        template_source = os.path.join(volt_dir, 'templates')

        if template == 'widget':
            # if template type is widget, only copy / create if it's not
            # present already
            if not os.path.exists(CONFIG.VOLT.USER_WIDGET):

                # if builtin is not an empty string, get the default widgets
                if builtin:
                    builtin_dir = os.path.join(volt_dir, 'config')
                    shutil.copy2(os.path.join(builtin_dir, 'default_widgets.py'),
                        os.path.join(os.curdir, 'widgets.py'))
                # otherwise get the widget template
                else:
                    shutil.copy2(os.path.join(template_source, 'widgets.py'),
                        os.curdir)
        else:
            template_dir = os.path.join(os.getcwd(), template + 's')

            # create plugin / engine dir in the root dir
            # unless it's there already
            if not os.path.exists(template_dir):
                os.mkdir(template_dir)

            # if builtin is specified, try to get the builtin plugin/engine
            if builtin:
                builtin_dir = os.path.join(volt_dir, template, 'builtins')
                try:
                    if builtin == 'atomic':
                        shutil.copytree(os.path.join(builtin_dir, builtin), \
                                os.path.join(template_dir, builtin))
                    else:
                        shutil.copy2(os.path.join(builtin_dir, builtin + '.py'), \
                                template_dir)
                except IOError:
                    message = "Builtin %s '%s' not found." % (template, builtin)
                    console("Error: %s" % message, color='red', is_bright=True)
                    sys.exit(1)

            # otherwise copy the plugin/engine template
            else:
                template_file = template + '.py'
                if not os.path.exists(os.path.join(template_dir, template_file)):
                    shutil.copy2(os.path.join(template_source, template_file), \
                            template_dir)


    def run_init(self, is_demo=False):
        """Starts a new Volt project.

        init -- String, must be 'init' or 'demo', denotes which starting files
                will be copied into the current directory.

        """
        cmd_name = 'init' if not is_demo else 'demo'
        dir_content = os.listdir(os.curdir)
        if dir_content != [] and dir_content != ['volt.log']:
            message = "'volt %s' must be run inside an empty directory." % cmd_name
            console("Error: %s" % message, color='red', is_bright=True)
            sys.exit(1)

        # get volt installation directory and demo dir
        target_path = os.path.join(os.path.dirname(__file__), 'templates', cmd_name)

        # we only need the first layer to do the copying
        parent_dir, child_dirs, top_files = os.walk(target_path).next()

        # copy all files in parent that's not a .pyc file
        for top in [x for x in top_files if not x.endswith('.pyc')]:
            shutil.copy2(os.path.join(parent_dir, top), os.curdir)
        # copy all child directories
        for child in child_dirs:
            shutil.copytree(os.path.join(parent_dir, child), child)

        if not is_demo:
            console("\nVolt project started. Have fun!\n", is_bright=True)

    def run_demo(self):
        """Runs a quick demo of Volt."""
        # copy demo files
        self.run_init(is_demo=True)
        console("\nPreparing your lightning-speed Volt tour...",  is_bright=True)
        # need to pass arglist to serve, so we'll call main
        main(['serve'])

    def run_gen(self):
        """Generates the static site."""
        if not CONFIG.SITE.ENGINES:
            message = "All engines are inactive -- nothing to generate."
            console(message, is_bright=True, color='red')
        else:
            generator.run()

    def run_serve(self):
        """Generates the static site, and if successful, runs the Volt server."""
        self.run_gen()
        if not os.path.exists(CONFIG.VOLT.SITE_DIR):
            message = "Site directory not found -- nothing to serve."
            console(message, is_bright=True, color='red')
        else:
            server.run()

    def run_version(self):
        """Shows version number."""
        console("Volt %s" % __version__)


def main(cli_arglist=None):
    """Main execution routine.

    cli_arglist -- List of arguments passed to the command line.

    """
    session = Runner()
    try:
        cmd = session.build_parsers().parse_args(cli_arglist)

        # only build logger if we're not starting a new project
        # or just checking version
        if cmd.name not in ['demo', 'init', 'version']:
            session.build_logger()
            # attach parsed object to the package-wide config
            setattr(CONFIG, 'CMD', cmd)
            os.chdir(CONFIG.VOLT.ROOT_DIR)

        logger = logging.getLogger('main')
        logger.debug("running: %s" % cmd.name)
        cmd.run()
    except ConfigNotFoundError:
        message = "You can only run 'volt %s' inside a Volt project directory." % \
                cmd.name
        console("Error: %s" % message, color='red', is_bright=True)
        console("Start a Volt project by running 'volt init' inside an empty directory.")

        if os.path.exists('volt.log'):
            os.remove('volt.log')

        sys.exit(1)

########NEW FILE########
__FILENAME__ = css_minifier
# -*- coding: utf-8 -*-
"""
---------------------------------
volt.plugin.builtins.css_minifier
---------------------------------

CSS minifier plugin.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from __future__ import with_statement
import os

import cssmin

from volt.config import CONFIG, Config
from volt.plugin.core import Plugin


PLUGIN = 'CssMinifier'


class CssMinifier(Plugin):

    """Site plugin for minifying CSS."""

    DEFAULTS = Config(
       # resulting minified css name
       OUTPUT_FILE = 'minified.css',
       # directory of output file
       OUTPUT_DIR =  CONFIG.VOLT.SITE_DIR,
       # directory to look for input css files
       SOURCE_DIR = CONFIG.VOLT.SITE_DIR,
       # extension for css files, used in determining which files to minify
       CSS_EXT = '.css',

    )

    USER_CONF_ENTRY = 'PLUGIN_CSS_MINIFIER'

    def run(self, site):
        output_name = self.config.OUTPUT_FILE
        source_dir = self.config.SOURCE_DIR
        output_dir = self.config.OUTPUT_DIR
        css_ext = self.config.CSS_EXT

        # get list of source file names
        source_files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) \
                if f != output_name and f.endswith(css_ext)]

        css = ''
        for f in source_files:
            with open(f, 'r') as source_file:
                css += source_file.read()

        with open(os.path.join(output_dir, output_name), 'w') as target_file:
            target_file.write(cssmin.cssmin(css))

########NEW FILE########
__FILENAME__ = js_minifier
# -*- coding: utf-8 -*-
"""
--------------------------------
volt.plugin.builtins.js_minifier
--------------------------------

Javascript minifier plugin.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from __future__ import with_statement
import os

import jsmin

from volt.config import CONFIG, Config
from volt.plugin.core import Plugin


PLUGIN = 'JsMinifier'


class JsMinifier(Plugin):

    """Site plugin for minifying javascript."""

    DEFAULTS = Config(
       # resulting minified js name
       OUTPUT_FILE = 'minified.js',
       # directory of output file
       OUTPUT_DIR =  CONFIG.VOLT.SITE_DIR,
       # directory to look for input js files
       SOURCE_DIR = CONFIG.VOLT.SITE_DIR,
       # extension for js files, used in determining which files to minify
       JS_EXT = '.js',

    )

    USER_CONF_ENTRY = 'PLUGIN_JS_MINIFIER'

    def run(self, site):
        output_name = self.config.OUTPUT_FILE
        source_dir = self.config.SOURCE_DIR
        output_dir = self.config.OUTPUT_DIR
        js_ext = self.config.JS_EXT

        # get list of source file names
        source_files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) \
                if f != output_name and f.endswith(js_ext)]

        js = ''
        for f in source_files:
            with open(f, 'r') as source_file:
                js += source_file.read()

        with open(os.path.join(output_dir, output_name), 'w') as target_file:
            target_file.write(jsmin.jsmin(js))

########NEW FILE########
__FILENAME__ = markdown_parser
# -*- coding: utf-8 -*-
"""
------------------------------------
volt.plugin.builtins.markdown_parser
------------------------------------

Markdown plugin for Volt units.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os

import markdown

from volt.plugin.core import Plugin


PLUGIN = 'MarkdownParser'


class MarkdownParser(Plugin):

    """Plugin for transforming markdown syntax to html.

    The plugin can detect whether a unit is formatted using markdown from
    the file extension ('.md' or '.markdown') or if a 'markup' field
    is defined with 'markdown' in the header field. The header field value
    takes precedence over the file extension.

    """

    def run(self, engine):
        """Process the given engine."""
        for unit in engine.units:
            # markup lookup, in header field first then file extension
            if hasattr(unit, 'markup'):
                is_markdown = ('markdown' == getattr(unit, 'markup').lower())
            else:
                ext = os.path.splitext(unit.id)[1]
                is_markdown = (ext.lower() in ['.md', '.markdown'])

            # if markdown, then process
            if is_markdown:
                string = getattr(unit, 'content')
                setattr(unit, 'content', markdown.markdown(string))

########NEW FILE########
__FILENAME__ = rst_parser
# -*- coding: utf-8 -*-
"""
-------------------------------
volt.plugin.builtins.rst_parser
-------------------------------

reStructuredText plugin for Volt units.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os

from docutils.core import publish_parts

from volt.plugin.core import Plugin


PLUGIN = 'RstParser'


class RstParser(Plugin):

    """Plugin for transforming rST syntax to html."""

    def run(self, engine):
        """Process the given engine."""
        for unit in engine.units:
            if hasattr(unit, 'markup'):
                is_rst = ('rst' == getattr(unit, 'markup').lower())
            else:
                ext = os.path.splitext(unit.id)[1]
                is_rst = (ext.lower() == '.rst')

            if is_rst:
                string = getattr(unit, 'content')
                string = self.get_html(string)
                setattr(unit, 'content', string)

    def get_html(self, string):
        """Returns html string of a restructured text content.

        string -- string to process
        
        """
        rst_contents = publish_parts(string, writer_name='html')
        return rst_contents['html_body']

########NEW FILE########
__FILENAME__ = syntax
# -*- coding: utf-8 -*-
"""
---------------------------
volt.plugin.builtins.syntax
---------------------------

Syntax highlighter plugin for Volt.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

from __future__ import with_statement
import os
import re

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from volt.config import CONFIG, Config
from volt.plugin.core import Plugin


PLUGIN = 'Syntax'


class Syntax(Plugin):

    """Highlights code syntax using pygments.

    This plugin performs syntax highlighting for text enclosed in a <pre> or
    <pre><code> tag. Syntax language can be guessed by the underlying lexer
    (pygments.lexer) or set explicitly using a 'lang' attribute in the
    enclosing <pre> tag.

    For example:

        <pre lang="python">
        print "This is highlighted!"
        </pre>

    will highlight the <pre> tag-enclosed text using a python lexer.

    Ideally, this plugin is run after markup language processing has been done.

    Options for this plugin configurable via voltconf.py are:

        `OUTPUT_FILE`
            String indicating the CSS file output name, defaults to
            syntax_highlight.css in the current directory.

        `OUTPUT_DIR`
            String indicating directory name of output css file, defaults to
            'site'.

        `UNIT_FIELD`
            String indicating which unit field to process, defaults to
            'content'.

        `PYGMENTS_LEXER`
            Dictionary of pygments lexer configurations, as outlined here:
            http://pygments.org/docs/lexers/

        `PYGMENTS_HTML`
            Dictionary of pygments HTMLFormatter configurations, as outlined here:
            http://pygments.org/docs/formatters/

        `EXTRA_CLASS`
            String of list of strings of extra css classes to append to the
            highlighted css selectors.
    """

    DEFAULTS = Config(
            # css output for syntax highlight
            OUTPUT_FILE = 'syntax_highlight.css',
            # directory to output css file
            OUTPUT_DIR = CONFIG.VOLT.SITE_DIR,
            # unit field to process
            UNIT_FIELD =  'content',
            # 
            # options for pygments' lexers, following its defaults
            PYGMENTS_LEXER = {
                'stripall': False,
                'stripnl': True,
                'ensurenl': True,
                'tabsize': 0,
            },
            # options for pygments' HTMLFormatter, following its defaults
            PYGMENTS_HTML = {
                'nowrap': False,
                'full': False,
                'title': '',
                'style': 'default',
                'noclasses': False,
                'classprefix': '',
                'cssclass': 'highlight',
                'csstyles': '',
                'prestyles': '',
                'cssfile': '',
                'noclobber_cssfile': False,
                'linenos': False,
                'hl_lines': [],
                'linenostart': 1,
                'linenostep': 1,
                'linenospecial': 0,
                'nobackground': False,
                'lineseparator': "\n",
                'lineanchors': '',
                'anchorlinenos': False,
            },
            # list of additional css classes for highlighted code
            EXTRA_CLASS = ['.highlight'],
    )

    USER_CONF_ENTRY = 'PLUGIN_SYNTAX'

    def run(self, engine):
        """Process the given units."""
        # build regex patterns
        pattern = re.compile(r'(<pre(.*?)>(?:<code>)?(.*?)(?:</code>)?</pre>)', re.DOTALL)
        lang_pattern = re.compile(r'\s|lang|=|\"|\'')

        output_file = self.config.OUTPUT_FILE
        output_dir = self.config.OUTPUT_DIR
        css_file = os.path.join(output_dir, output_file)

        for unit in engine.units:
            # get content from unit
            string = getattr(unit, self.config.UNIT_FIELD)
            # highlight syntax in content
            string = self.highlight_code(string, pattern, lang_pattern)
            # override original content with syntax highlighted
            setattr(unit, self.config.UNIT_FIELD, string)

        # write syntax highlight css file
        css = HtmlFormatter(**self.config.PYGMENTS_HTML).get_style_defs(self.config.EXTRA_CLASS)
        if not os.path.exists(css_file):
            with open(css_file, 'w') as target:
                target.write(css)

    def highlight_code(self, string, pattern, lang_pattern):
        """Highlights syntaxes in the given string enclosed in a <syntax> tag.

        string -- String containing the code to highlight.
        pattern -- Compiled regex object for highlight pattern matching.
        lang_pattern -- Compiled regex for obtaining language name (if provided)
        
        """
        codeblocks = re.findall(pattern, string)
        # results: list of tuples of 2 or 3 items
        # item[0] is the whole code block (syntax tag + code to highlight)
        # item[1] is the programming language (optional, depends on usage)
        # item[2] is the code to highlight

        if codeblocks:
            for match, lang, code in codeblocks:
                if lang:
                    lang = re.sub(lang_pattern, '', lang)
                    try:
                        lexer = get_lexer_by_name(lang.lower(), **self.config.PYGMENTS_LEXER)
                    # if the lang is not supported or has a typo
                    # let pygments guess the language
                    except ClassNotFound:
                        lexer = guess_lexer(code, **self.config.PYGMENTS_LEXER)
                else:
                    lexer = guess_lexer(code, **self.config.PYGMENTS_LEXER)

                formatter = HtmlFormatter(**self.config.PYGMENTS_HTML)
                highlighted = highlight(code, lexer, formatter)
                # add 1 arg because replacement should only be done
                # once for each match
                string = string.replace(match, highlighted, 1)

        return string

########NEW FILE########
__FILENAME__ = textile_parser
# -*- coding: utf-8 -*-
"""
-----------------------------------
volt.plugin.builtins.textile_parser
-----------------------------------

Textile plugin for Volt units.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os

import textile

from volt.plugin.core import Plugin


PLUGIN = 'TextileParser'


class TextileParser(Plugin):

    """Plugin for transforming textile syntax to html."""

    def run(self, engine):
        """Process the given engine."""
        for unit in engine.units:
            if hasattr(unit, 'markup'):
                is_textile = ('textile' == getattr(unit, 'markup').lower())
            else:
                ext = os.path.splitext(unit.id)[1]
                is_textile = (ext.lower() == '.textile')

            if is_textile:
                string = getattr(unit, 'content')
                string = self.get_html(string)
                setattr(unit, 'content', string)

    def get_html(self, string):
        """Returns html string of a textile content.

        string -- string to process
        
        """
        return textile.textile(string)

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
----------------
volt.plugin.core
----------------

Core Volt plugin.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import abc
import os

from volt.config import CONFIG, Config
from volt.utils import path_import


class Plugin(object):

    """Plugin base class.

    Volt plugins are subclasses of Plugin that perform a set of operations
    to Unit objects of a given engine. They are executed after all
    Engines finish parsing their units and before any output files are
    written. Plugin execution is handled by the Generator object in
    volt.gen.

    During a Generator run, Volt tries first to look up a given plugin
    in the plugins directory in the project's root folder. Failing that,
    Volt will try to load the plugin from volt.plugins.

    Default settings for a Plugin object should be stored as a Config object
    set as a class attribute with the name DEFAULTS. Another class attribute
    named USER_CONF_ENTRY may also be defined. This tells the Plugin which
    Config object in the user's voltconf.py will be consolidated with the
    default configurations in DEFAULTS. Finally, all Plugin subclasses must
    implement a run method, which is the entry point for plugin execution
    by the Generator class.

    """

    __metaclass__ = abc.ABCMeta

    DEFAULTS = Config()

    USER_CONF_ENTRY = None

    def __init__(self):
        """Initializes Plugin."""

        self.config = Config(self.DEFAULTS)

    def prime(self):
        """Consolidates default plugin Config and user-defined Config."""

        # only override defaults if USER_CONF_ENTRY is defined
        if self.USER_CONF_ENTRY is not None:
            # get user config object
            conf_name = os.path.splitext(os.path.basename(CONFIG.VOLT.USER_CONF))[0]
            voltconf = path_import(conf_name, CONFIG.VOLT.ROOT_DIR)

            # use default Config if the user does not list any
            try:
                user_config = getattr(voltconf, self.USER_CONF_ENTRY)
            except AttributeError:
                user_config = Config()

            # to ensure proper Config consolidation
            if not isinstance(user_config, Config):
                raise TypeError("User Config object '%s' must be a Config instance." % \
                        self.USER_CONF_ENTRY)
            else:
                self.config.update(user_config)

    @abc.abstractmethod
    def run(self):
        """Runs the plugin."""

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
"""
-----------
volt.server
-----------

Development server for Volt.

This module provides a multithreading HTTP server that subclasses
SocketServer.ThreadingTCPServer. The server can auto-regenerate the Volt site
after any file inside it is changed and a new HTTP request is sent. It can be
run from any directory inside a Volt project directory and will always return
resources relative to the Volt output site directory. If it is run outside of
a Volt directory, an error will be raised.

A custom HTTP request handler subclassing
SimpleHTTPServer.SimpleHTTPRequestHandler is also provided. The methods defined
in this class mostly alters the command line output. Processing logic is similar
to the parent class.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import logging
import os
import posixpath
import sys
import urllib
from functools import partial
from itertools import chain
from socket import getfqdn
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingTCPServer

from volt import __version__
from volt import generator
from volt.config import CONFIG
from volt.utils import console, LoggableMixin


console = partial(console, format="[srv] %s  %s\n")


class VoltHTTPServer(ThreadingTCPServer, LoggableMixin):

    """A simple multithreading HTTP server for Volt development."""

    # copied from BaseHTTPServer.py since ThreadingTCPServer is used
    # instead of TCPServer
    allow_reuse_address = 1

    def __init__(self, *args, **kwargs):
        """Initializes Volt HTTP server.

        In addition to performing BaseServer initialization, this method
        also polls the timestamp of all directories inside the Volt project
        directory except the site output directory. This is set as a self
        atttribute and will be used later to generate the site everytime
        a file inside these directories are modified.

        """
        self.last_mtime = self.check_dirs_mtime()
        ThreadingTCPServer.__init__(self, *args, **kwargs)
        self.logger.debug('created: %s' % type(self).__name__)

    def process_request(self, request, client_address):
        """Finishes one request by instantiating the handler class.

        Prior to handler class initialization, this method checks the latest
        timestamp of all directories inside the Volt project. If the result
        is higher than the prior timestamp (self.last_mtime), then the entire
        site will be regenerated.

        """
        latest_mtime = self.check_dirs_mtime()

        if self.last_mtime < latest_mtime:
            message = "Source file modification detected -- regenerating site"
            console(message, color='yellow')
            self.logger.debug(message)

            self.last_mtime = latest_mtime
            CONFIG.reset()
            generator.run()
            self.logger.debug('done: regenerating site')

        ThreadingTCPServer.process_request(self, request, client_address)

    def check_dirs_mtime(self):
        """Returns the latest timestamp of directories in a Volt project.

        This method does not check the site output directory since the user
        is not supposed to change the contents inside manually.

        """
        # we don't include the output site directory because it will have
        # higher mtime than the user-modified file
        # the root directory is also not included since it will have higher
        # mtime due to the newly created output site directory
        # but we do want to add voltconf.py, since the user might want to
        # check the effects of changing certain configs
        dirs = (x[0] for x in os.walk(CONFIG.VOLT.ROOT_DIR) if
                CONFIG.VOLT.SITE_DIR not in x[0] and CONFIG.VOLT.ROOT_DIR != x[0])

        files = [CONFIG.VOLT.USER_CONF]
        if os.path.exists(CONFIG.VOLT.USER_WIDGET):
            files.append(CONFIG.VOLT.USER_WIDGET)

        return max(os.stat(x).st_mtime for x in chain(dirs, files))

    def server_bind(self):
        # overrides server_bind to store the server name.
        ThreadingTCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = getfqdn(host)
        self.server_port = port
                                                    

class VoltHTTPRequestHandler(SimpleHTTPRequestHandler, LoggableMixin):

    """HTTP request handler of the Volt HTTP server.

    This request handler can only be used for serving files inside a Volt
    site directory, since its path resolution is relative to that  directory.
    In addition to that, the handler can display colored text output according
    to the settings in voltconf.py and outputs the size of the returned file
    in its HTTP log line. 404 error messages are suppressed to allow for more
    compact output.

    Consult the SimpleHTTPRequestHandler documentation for more information.

    """

    server_version = 'VoltHTTPServer/' + __version__

    def log_error(self, format, *args):
        # overwritten to unclutter log message.
        pass

    def log_message(self, format, *args):
        # overrides parent log_message to provide a more compact output.
        message = format % args

        if int(args[1]) >= 400:
            console(message, color='red')
        elif int(args[1]) >= 300:
            console(message, color='cyan')
        else:
            console(message)
        
        self.logger.debug(message)

    def log_request(self, code='-', size='-'):
        # overrides parent log_request so 'size' can be set dynamically.
        ### HACK, add code for 404 processing later
        if code <= 200:
            actual_file = os.path.join(self.file_path, 'index.html')
            if os.path.isdir(self.file_path):
                if os.path.exists(actual_file) or \
                   os.path.exists(actual_file[:-1]):
                    size = os.path.getsize(actual_file)
            else:
                size = os.path.getsize(self.file_path)

        format = '"%s" %s %s'
        args = (self.requestline[:-9], str(code), str(size))
        self.log_message(format, *args)

    def translate_path(self, path):
        # overrides parent translate_path to enable custom directory setting.
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = CONFIG.VOLT.SITE_DIR
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): 
                continue
            path = os.path.join(path, word)
        # set file path as attribute, to get size in log_request()
        self.file_path = path
        return self.file_path


def run():
    """Runs the HTTP server using options parsed by argparse, accessible
    via CONFIG.CMD."""

    logger = logging.getLogger('server')

    address = ('127.0.0.1', CONFIG.CMD.server_port)
    try:
        server = VoltHTTPServer(address, VoltHTTPRequestHandler)
    except Exception, e:
        ERRORS = { 2: "Site directory '%s' not found" % CONFIG.VOLT.SITE_DIR,
                  13: "You don't have permission to access port %s" % 
                      (CONFIG.CMD.server_port),
                  98: "Port %s already in use" % (CONFIG.CMD.server_port)}
        try:
            message = ERRORS[e.args[0]]
        except (AttributeError, KeyError):
            message = str(e)
        logger.error(message)
        sys.exit(1)

    run_address, run_port = server.socket.getsockname()
    if run_address == '127.0.0.1':
        run_address = 'localhost'

    message = "Volt %s Development Server" % __version__
    console(message, is_bright=True)
    logger.debug(message)

    message = "Serving %s" % CONFIG.VOLT.SITE_DIR
    console(message)
    logger.debug(message)

    message = "Running at http://%s:%s" % (run_address, run_port)
    console(message)
    logger.debug(message)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    finally:
        sys.stdout.write("\n")
        message = "Server stopped"
        console(message)
        logger.debug(message)
        sys.stdout.write("\n")
        sys.exit(0)

########NEW FILE########
__FILENAME__ = voltconf
# -*- coding: utf-8 -*-
# Volt configurations file

import os
from volt.config import Config


# General project configurations
SITE = Config(

    # Your site name
    TITLE = 'My First Volt Site',

    # Your site URL (must be preceeded with 'http://')
    URL = 'http://localhost',

    # Engines used in generating the site
    # These represent different sections of your site
    # Available built-in engines are 'blog' and 'plain'
    # The blog engine generates blogs from text files, while the
    # plain engine generates plain web pages
    # To disable an engine, just remove its name from this list
    ENGINES = ('blog', 'plain', ),

    # Non-engine widgets
    WIDGETS = (
        'active_engines',
        #'github_search',
    ),

    # Jinja2 filters
    FILTERS = ('taglist', ),
)


# Plain engine configurations
ENGINE_PLAIN = Config(

    # URL for all page content relative to root URL
    URL = '/page',

    # Plain page permalink, relative to page URL
    PERMALINK = '{slug}',

    # Plugins to be run on plain units
    PLUGINS = (
        'markdown_parser',
    ),
)


# Blog engine configurations
ENGINE_BLOG = Config(

    # URL for all blog content relative to root URL
    URL = '/',

    # Blog posts permalink, relative to blog URL
    PERMALINK = '{time:%Y/%m/%d}/{slug}',

    # Plugins to be run on blog units
    PLUGINS = (
        'markdown_parser',
        #'atomic',
    ),

    # Widgets to be created from blog units
    WIDGETS = (
        'monthly_archive',
        #'latest_posts',
    ),

    # The number of displayed posts per pagination page
    UNITS_PER_PAGINATION = 10,

    # Excerpt length (in characters) for paginated items
    EXCERPT_LENGTH = 400,

    # Paginations to build for the static site
    # Items in this tuple will be used to set the paginations relative to
    # the blog URL. Items enclosed in '{}' are pulled from the unit values,
    # e.g. 'tag/{tags}' will be expanded to 'tag/x' for x in each tags in the
    # site. These field tokens must be the last token of the pattern.
    # Use an empty string ('') to apply pagination to all blog units
    PAGINATIONS = ('','tag/{tags}', '{time:%Y/%m/%d}', '{time:%Y/%m}', '{time:%Y}'),
)


# Plugin configurations
PLUGIN_ATOMIC = Config(
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'site'),
)

########NEW FILE########
__FILENAME__ = widgets
# Volt custom widgets


def taglist(tags):
    """Jinja2 filter for displaying blog tags."""
    # html string format for each tag
    format = '<a href="/tag/%s/" class="button red">%s</a>'
    # return a comma-separated html string containing all tags
    return ', '.join([format % (tag, tag) for tag in tags])


def latest_posts(engine):
    """Engine widget for showing the latest posts.
    
    Example usage:
        {% for item in widgets.latest_posts %}
            <a href="{{ item.permalink }}">{{ item.title }}</a>
        {% endfor %}
    """
    # get title and permalink of the five most recent posts
    posts = [(x.title, x.permalink) for x in engine.units[:5]]

    # create title, permalink dict for each post
    results = []
    for title, permalink in posts:
        results.append({'title': title,
                        'permalink': permalink
                       })
    return results


def monthly_archive(engine):
    """Engine widget for monthly archive.

    Example usage:
        {% for item in widgets.monthly_archive %}
            <a href="{{ item.link }}">{{ item.name }} ({{ item.size }})</a>
        {% endfor %}
    """
    # get string containing time elements to use
    times = set([x.time.strftime("%Y|%m|%B") for x in engine.units])

    # create dicts containing year, month number (for constructing links)
    # and the month name (for display on the page)
    results = []
    for timestring in times:
        year, month, month_name = timestring.split("|")
        link = "/blog/%s/%s" % (year, month)
        name = "%s %s" % (month_name, year)
        size = len([x for x in engine.units if \
                x.time.strftime("%Y%m") == '%s%s' % (year, month)])

        results.append({'name': name, 
                        'link': link,
                        'size': size
                       })
    return results


def active_engines(site):
    """Site widget for listing all active engines.

    Example usage:
        {% for item in widgets.active_engines %}
            <a href="{{ item.link }}">{{ item.name }}</a>
        {% endfor %}

    Useful for creating dynamic main site navigation, for example.
    """
    # retrieve engine URLs from its config and create name from its class name
    results = []
    for engine in site.engines.values():
        link = engine.config.URL
        name = type(engine).__name__.replace('Engine', '')
        results.append({'name': name,
                        'link': link,
                       })
    return results

def github_search(site):
    """Site widget for returning github repo search, sorted on last push time.
    
    Example usage:
        {% for item in widgets.github_search %}
            <a href="{{ item.url }}">{{ item.name }} ({{ item.watchers }})</a>
        {% endfor %}
    """
    import json
    try: #try python3 first
        from urllib.request import urlopen
        from urllib.parse import urlencode
    except ImportError: # fallback to python2
        from urllib import urlencode, urlopen
    from datetime import datetime
    from volt.utils import console

    # set our search parameters
    query_string = 'static website'
    args = {'language': 'Python'}
    base_url = 'http://github.com/api/v2/json/repos/search/'

    # retrieve search results using urllib and json
    query = '%s%s' % (query_string.replace(' ', '+'), '?' + urlencode(args))
    try:
        response = urlopen(base_url + query).read().decode('utf-8')
    except IOError:
        console("WARNING: github_search can not connect to the internet.\n", \
                color='red', is_bright=True)
        return []
    data = json.loads(response)['repositories']

    # get repos with at least 10 watchers
    results = [repo for repo in data if repo['watchers'] >= 10]

    # finally, we'll sort our selection ~ most recent push time first
    def gettime(datestr, format="%Y/%m/%d %H:%M:%S"):
        return datetime.strptime(datestr[:-6], format)
    results.sort(key=lambda x: gettime(x['pushed_at']), reverse=True)

    return results

########NEW FILE########
__FILENAME__ = engine
# Volt custom engine

from volt.config import Config
from volt.utils import cachedproperty
from volt.engine.core import Engine


ENGINE = 'MyEngine'


class MyEngine(Engine):

    # Default engine configurations
    DEFAULTS = Config(
        # URL for all engine content relative to root site URL
        URL = '',

        # Permalink pattern for engine units relative to engine URL
        PERMALINK = '',

        # Directory path for storing engine content
        # relative to the default Volt content directory
        CONTENT_DIR = '',
    )

    # Config instance name in voltconf.py
    USER_CONF_ENTRY = ''

    @cachedproperty
    def units(self):
        pass

    def dispatch(self):
        pass

########NEW FILE########
__FILENAME__ = voltconf
# -*- coding: utf-8 -*-
# Volt configurations

from volt.config import Config


# Default site configurations
SITE = Config(

    # Site name
    TITLE = 'My Volt Site',

    # Site URL, used for generating absolute URLs
    URL = 'http://mysite.com',

    # Engines used in generating the site
    # Defaults to none
    ENGINES = (),

    # Extra pages to write that are not controlled by an engine
    # Examples: 404.html, index.html (if not already written by an engine)
    # The tuple should list template names of these pages, which should
    # be present in the default template directory
    PAGES = (),

    # URL to use for pagination
    # This will be used for paginated items after the first one
    # For example, if the pagination URL is 'page', then the second
    # pagination page will have '.../page/2/', the third '.../page/3/', etc.
    PAGINATION_URL = '',

    # Boolean to set if output file names should all be 'index.html' or vary
    # according to the last token in its self.permalist attribute
    # index.html-only outputs allows for nice URLS without fiddling too much
    # with .htaccess
    INDEX_HTML_ONLY = True,

    # Logging level
    # If set to 10, Volt will write logs to a file
    # 30 is logging.WARNING
    LOG_LEVEL = 30,

    # Ignore patterns
    # Filenames that match this pattern will not be copied from asset directory
    # to site directory
    IGNORE_PATTERN = '',

    # String replacement scheme for slugs
    # Dictionary, key is the string to replace, value is the replacement string
    # This is used to replace non-ascii consonants or vowels in a slug with
    # their ascii equivalents, so the slug meaning is preserved.
    # For example {u'ß': 'ss'}, would transfrom the slug "viel-Spaß" to
    # "viel-spass" instead of "viel-spa", preserving its meaning
    SLUG_CHAR_MAP = {},

    # Site plugins
    # These are plugins that work on the whole site
    PLUGINS = (),

    # Site widgets
    # These are widgets that work on the whole site
    WIDGETS = (),

    # Jinja2 filter function names
    FILTERS = (),

    # Jinja2 test function names
    TESTS = (),
)

########NEW FILE########
__FILENAME__ = plugin
# Volt custom plugin

from volt.plugin.core import Plugin


PLUGIN = 'MyPlugin'


class MyPlugin(Plugin):

    # Uncomment to set a default set of plugin configuration values
    #DEFAULTS = Config(
    #)

    # Uncomment to set the plugin entry name in voltconf
    #USER_CONF_ENTRY = ''

    def run(self):
        pass

########NEW FILE########
__FILENAME__ = widgets
# Volt custom widgets

def my_widget(units):
    pass

########NEW FILE########
__FILENAME__ = default_conf
from volt.config import Config

VOLT = Config(
    USER_CONF = 'voltconf.py',
    USER_WIDGET = 'widgets.py',
    CONTENT_DIR = 'contents',
    ASSET_DIR = 'assets',
    TEMPLATE_DIR = 'templates',
)

SITE = Config(
    TITLE = 'Title in default',
    DESC = 'Desc in default', 
    A_URL = 'http://foo.com',
    B_URL = 'http://foo.com/',
    C_URL = '/',
    D_URL = '',
    FILTERS = ('foo', 'bar'),
    TESTS = (),
)

########NEW FILE########
__FILENAME__ = default_widgets
def foo(): return "foo in default"
def bar(): pass

########NEW FILE########
__FILENAME__ = in_both
from volt.engine.core import Engine

ENGINE = 'TestBuiltin'

class TestBuiltin(Engine):
    def activate(self): pass
    def dispatch(self): pass
    def create_units(self): pass

########NEW FILE########
__FILENAME__ = in_install
from volt.engine.core import Engine

ENGINE = 'TestBuiltin'

class TestBuiltin(Engine):
    def activate(self): pass
    def dispatch(self): pass
    def create_units(self): pass

########NEW FILE########
__FILENAME__ = in_both
from volt.plugin.core import Plugin

PLUGIN = 'TestBuiltin'

class TestBuiltin(Plugin):
    def run(self): pass

########NEW FILE########
__FILENAME__ = in_install
from volt.plugin.core import Plugin

PLUGIN = 'TestBuiltin'

class TestBuiltin(Plugin):
    def run(self): pass

########NEW FILE########
__FILENAME__ = in_both
from volt.engine.core import Engine

ENGINE = 'TestUser'

class TestUser(Engine):
    def activate(self): pass
    def dispatch(self): pass
    def create_units(self): pass

########NEW FILE########
__FILENAME__ = in_user
from volt.engine.core import Engine

ENGINE = 'TestUser'

class TestUser(Engine):
    def activate(self): pass
    def dispatch(self): pass
    def create_units(self): pass

########NEW FILE########
__FILENAME__ = in_both
from volt.plugin.core import Plugin

PLUGIN = 'TestUser'

class TestUser(Plugin):
    def run(self): pass

########NEW FILE########
__FILENAME__ = in_user
from volt.plugin.core import Plugin

PLUGIN = 'TestUser'

class TestUser(Plugin):
    def run(self): pass

########NEW FILE########
__FILENAME__ = voltconf
from volt.config import Config

VOLT = Config(
    TEMPLATE_DIR = "mytemplates",
)

SITE = Config(
    CUSTOM_OPT = "custom_opt_user",
    TITLE = "Title in user",
    FILTERS = ('foo',),
)

ENGINE_TEST = Config(
    FOO = 'engine foo in user',
    BAR = 'engine bar in user',
)       

ENGINE_TEST_BAD = 'not a Config'

########NEW FILE########
__FILENAME__ = widgets
def foo(): return "foo in user"

########NEW FILE########
__FILENAME__ = test_config
# -*- coding: utf-8 -*-
"""
---------------------
volt.test.test_config
---------------------

Tests for the volt.config module.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os
import unittest

from mock import patch

from volt.config import UnifiedConfig, ConfigNotFoundError
from volt.test import INSTALL_DIR, USER_DIR


def get_root_dir_mock(x, y):
    return USER_DIR


class UnifiedConfigLoadCases(unittest.TestCase):

    @patch('volt.config.DEFAULT_CONF_DIR', INSTALL_DIR)
    @patch.object(UnifiedConfig, 'get_root_dir', get_root_dir_mock)
    def setUp(self):
        self.CONFIG = UnifiedConfig()

    def test_load_consolidation(self):
        # user config overriding
        self.assertEqual(self.CONFIG.SITE.TITLE, 'Title in user')
        # default config preservation
        self.assertEqual(self.CONFIG.SITE.DESC, 'Desc in default')
        # arbitrary user config
        self.assertEqual(self.CONFIG.SITE.CUSTOM_OPT, 'custom_opt_user')
    
    def test_load_dir_resolution(self):
        # default.py dir resolution
        self.assertEqual(self.CONFIG.VOLT.CONTENT_DIR, os.path.join(USER_DIR, \
                'contents'))
        # voltconf.py dir resolution
        self.assertEqual(self.CONFIG.VOLT.TEMPLATE_DIR, os.path.join(USER_DIR, \
                'mytemplates'))

    def test_load_url(self):
        # test for different URL possibilities
        self.assertEqual(self.CONFIG.SITE.A_URL, 'http://foo.com')
        self.assertEqual(self.CONFIG.SITE.B_URL, 'http://foo.com')
        self.assertEqual(self.CONFIG.SITE.C_URL, '')
        self.assertEqual(self.CONFIG.SITE.D_URL, '')

    def test_load_root_dir(self):
        self.assertEqual(self.CONFIG.VOLT.ROOT_DIR, USER_DIR)

    def test_load_jinja2_env_default(self):
        self.assertTrue('bar' in self.CONFIG.SITE.TEMPLATE_ENV.filters)

    def test_load_jinja2_env_user(self):
        self.assertEqual(self.CONFIG.SITE.TEMPLATE_ENV.filters['foo'](), \
                "foo in user")


class UnifiedConfigRootDirCases(unittest.TestCase):

    def setUp(self):
        self.get_root_dir = UnifiedConfig.get_root_dir

    def test_get_root_dir_current(self):
        self.assertEqual(self.get_root_dir('voltconf.py', USER_DIR), USER_DIR)

    def test_get_root_dir_child(self):
        start_dir = os.path.join(USER_DIR, "contents", "foo", "bar", "baz")
        self.assertEqual(self.get_root_dir('voltconf.py', start_dir), USER_DIR)

    def test_get_root_dir_error(self):
        os.chdir(INSTALL_DIR)
        self.assertRaises(ConfigNotFoundError, self.get_root_dir, \
                'voltconf.py', INSTALL_DIR)

########NEW FILE########
__FILENAME__ = test_engine_builtins
# -*- coding: utf-8 -*-
"""
------------------------------
volt.test.test_engine_builtins
------------------------------

Tests for built-in volt.engine components.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import glob
import os
import unittest
from datetime import datetime

from mock import MagicMock, patch, call

from volt.config import Config
from volt.engine.builtins import TextEngine, TextUnit
from volt.test import FIXTURE_DIR
from volt.test.test_engine_core import TestUnit


class TestTextEngine(TextEngine):
    def activate(self): pass
    def dispatch(self): pass

class TestTextUnit(TestUnit, TextUnit): pass


class TextEngineCases(unittest.TestCase):

    @patch('volt.engine.builtins.TextUnit')
    def test_units(self, TextUnit_mock):
        engine = TestTextEngine()
        content_dir = os.path.join(FIXTURE_DIR, 'engines', 'engine_pass')
        engine.config.CONTENT_DIR = content_dir
        fnames = [os.path.join('2010', '01_radical-notion.md'),
                  os.path.join('2010', '02_one-simple-idea.rst'),
                  os.path.join('2011', '03_dream-is-collapsing.md'),
                  '04_dream-within-a-dream.md',
                  '05_528491.rst']
        abs_fnames = [os.path.join(content_dir, x) for x in fnames]

        call_args = zip(abs_fnames, [engine.config] * len(fnames))
        calls = [call(*x) for x in call_args]

        engine.units
        TextUnit_mock.assert_has_calls(calls, any_order=True)

    @patch('volt.engine.builtins.TextUnit')
    def test_units_fname_pattern(self, TextUnit_mock):
        engine = TestTextEngine()
        engine.config.UNIT_FNAME_PATTERN = '*.rst'
        content_dir = os.path.join(FIXTURE_DIR, 'engines', 'engine_pass')
        engine.config.CONTENT_DIR = content_dir
        fnames = [os.path.join('2010', '02_one-simple-idea.rst'),
                  '05_528491.rst']
        abs_fnames = [os.path.join(content_dir, x) for x in fnames]

        call_args = zip(abs_fnames, [engine.config] * len(fnames))
        calls = [call(*x) for x in call_args]

        engine.units
        TextUnit_mock.assert_has_calls(calls, any_order=True)


@patch('volt.engine.core.CONFIG', MagicMock())
class TextUnitCases(unittest.TestCase):

    @patch.object(TestTextUnit, 'check_required', MagicMock())
    @patch.object(TestTextUnit, 'slugify')
    def setUp(self, slugify_mock):
        slugify_mock.return_value = u'3.14159265'
        self.config = MagicMock(spec=Config)
        self.content_dir = os.path.join(FIXTURE_DIR, 'units')

    def test_parse_source_header_missing(self):
        fname = glob.glob(os.path.join(self.content_dir, 'unit_fail', '02*'))[0]
        self.assertRaises(ValueError, TestTextUnit, fname, self.config)

    def test_parse_source_header_typo(self):
        fname = glob.glob(os.path.join(self.content_dir, 'unit_fail', '03*'))[0]
        self.assertRaises(ValueError, TestTextUnit, fname, self.config)

    def test_parse_source_global_fields_ok(self):
        fname = glob.glob(os.path.join(self.content_dir, 'unit_pass', '01*'))[0]
        self.config.DEFAULT_FIELDS = {'foo': 'bar'}
        unit = TestTextUnit(fname, self.config)
        self.assertEqual(unit.foo, 'bar')

    def test_parse_source_slug_ok(self):
        fname = glob.glob(os.path.join(self.content_dir, 'unit_pass', '01*'))[0]
        unit = TestTextUnit(fname, self.config)
        self.assertEqual(unit.title, u'3.14159265')

    def test_parse_source_ok(self):
        fname = glob.glob(os.path.join(self.content_dir, 'unit_pass', '01*'))[0]
        unit = TestTextUnit(fname, self.config)
        unit.content = u'Should be parsed correctly.\n\n\u042e\u043d\u0438\u043a\u043e\u0434'

########NEW FILE########
__FILENAME__ = test_engine_core
# -*- coding: utf-8 -*-
"""
--------------------------
volt.test.test_engine_core
--------------------------

Tests for volt.engine.core.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os
import sys
import unittest
import warnings
from datetime import datetime

from mock import MagicMock, patch, call

from volt.config import Config
from volt.engine.core import Engine, Page, Unit, Pagination, \
        chain_item_permalinks
from volt.exceptions import EmptyUnitsWarning
from volt.test import USER_DIR, make_units_mock, make_uniconfig_mock


UniConfig_mock = make_uniconfig_mock()


class TestEngine(Engine):
    def dispatch(self): pass
    @property
    def units(self):
        if not hasattr(self, '_lazy_units'):
            setattr(self, '_lazy_units', make_units_mock())
        return self._lazy_units
    @units.setter
    def units(self, units): self._lazy_units = units

class TestPage(Page):
    @property
    def id(self): return 'test'
    @property
    def permalist(self): return self._lazy_permalist
    @permalist.setter
    def permalist(self, permalist): self._lazy_permalist = permalist

class TestUnit(Unit, TestPage): pass


class EngineCoreMethodsCases(unittest.TestCase):

    def test_chain_item_permalinks_ok(self):
        units = make_units_mock()[1:-1]
        assert [unit.id for unit in units] == ['2', '3', '4']
        chain_item_permalinks(units)

        self.assertEqual(units[0].permalink_next, units[1].permalink)
        self.assertFalse(hasattr(units[0], 'permalink_prev'))

        self.assertEqual(units[1].permalink_next, units[2].permalink)
        self.assertEqual(units[1].permalink_prev, units[0].permalink)

        self.assertFalse(hasattr(units[-1], 'permalink_next'))
        self.assertEqual(units[-1].permalink_prev, units[1].permalink)


@patch('volt.engine.core.CONFIG', UniConfig_mock)
class EngineCases(unittest.TestCase):

    def setUp(self):
        self.engine = TestEngine()

    def test_dispatch(self):
        class TestEngine(Engine):
            def activate(self): pass
            def units(self): return
        self.assertRaises(TypeError, TestEngine.__init__, )

    def test_units(self):
        class TestEngine(Engine):
            def activate(self): pass
            def dispatch(self): pass
        self.assertRaises(TypeError, TestEngine.__init__, )

    def test_prime_user_conf_entry_none(self):
        self.assertRaises(AttributeError, self.engine.prime, )

    def test_prime_content_dir_undefined(self):
        self.engine.USER_CONF_ENTRY = 'ENGINE_TEST'
        self.assertRaises(AttributeError, self.engine.prime, )

    def test_prime_user_conf_not_config(self):
        self.engine.USER_CONF_ENTRY = 'ENGINE_TEST_BAD'
        self.engine.config.CONTENT_DIR = 'engine_test'
        self.assertRaises(TypeError, self.engine.prime, )

    def test_prime_consolidation(self):
        defaults = Config(
            BAR = 'engine bar in default',
            QUX = 'engine qux in default',
            UNIT_TEMPLATE = 'template.html',
            URL = 'test',
            CONTENT_DIR = 'engine_test',
            PERMALINK = '',
        )
        self.engine.config = defaults
        self.engine.USER_CONF_ENTRY = 'ENGINE_TEST'

        self.engine.prime()

        self.assertEqual(self.engine.config.FOO, 'engine foo in user')
        self.assertEqual(self.engine.config.BAR, 'engine bar in user')
        self.assertEqual(self.engine.config.QUX, 'engine qux in default')
        self.assertEqual(self.engine.config.CONTENT_DIR, os.path.join(\
                USER_DIR, 'contents', 'engine_test'))
        self.assertEqual(self.engine.config.UNIT_TEMPLATE, os.path.join(\
                USER_DIR, 'templates', 'template.html'))

    def test_sort_units_bad_key(self):
        self.engine.config.SORT_KEY = 'date'
        self.assertRaises(AttributeError, self.engine.sort_units, )

    def test_sort_units_ok(self):
        self.engine.config.SORT_KEY = '-time'
        titles = ['Dream is Collapsing', 'Radical Notion', 'One Simple Idea', \
                  '528491', 'Dream Within A Dream',]
        self.assertNotEqual([x.title for x in self.engine.units], titles)
        self.engine.sort_units()
        self.assertEqual([x.title for x in self.engine.units], titles)

    @patch('volt.engine.core.write_file')
    def test_write_items_duplicate(self, write_mock):
        template_path = 'item.html'
        units = make_units_mock()[:2]
        units[1].path = units[0].path

        assert units[0].path == units[1].path
        with open(units[1].path, 'w'):
            self.assertRaises(IOError, self.engine._write_items, \
                    units, template_path)
        os.remove(units[1].path)

    @patch('volt.engine.core.write_file')
    def test_write_items_ok(self, write_mock):
        template_path = 'item.html'
        units = make_units_mock()[:2]
        self.engine._write_items(units, template_path)

        if sys.version_info[0] < 3:
            rendered = '\xd1\x8e\xd0\xbd\xd0\xb8\xd0\xba\xd0\xbe\xd0\xb4\xd0\xb0'
        else:
            rendered = 'юникода'

        call1 = call(os.path.join(USER_DIR, '1'), rendered + '|1')
        call2 = call(os.path.join(USER_DIR, '2'), rendered + '|2')
        self.assertEqual([call1, call2], write_mock.call_args_list)


class EnginePaginationCases(unittest.TestCase):

    def setUp(self):
        self.engine = TestEngine()
        self.engine.config.URL = 'test'
        self.engine.config.UNITS_PER_PAGINATION = 2

    def test_url_undefined(self):
        del self.engine.config.URL
        self.engine.config.PAGINATIONS = ('',)
        self.assertRaises(AttributeError, getattr, self.engine, 'paginations')

    def test_units_per_pagination_undefined(self):
        del self.engine.config.UNITS_PER_PAGINATION
        self.engine.config.PAGINATIONS = ('',)
        self.assertRaises(AttributeError, getattr, self.engine, 'paginations')

    def test_pagination_patterns_undefined(self):
        self.assertRaises(AttributeError, getattr, self.engine, 'paginations')

    @patch.object(warnings, 'warn')
    def test_empty_units_warning(self, warn_mock):
        self.engine.units = []
        self.engine.config.PAGINATIONS = ('',)
        getattr(self.engine, 'paginations')
        args = [call('TestEngine has no units to paginate.', EmptyUnitsWarning)]
        self.assertEqual(warn_mock.call_args_list, args)

    def test_bad_pagination_pattern(self):
        self.engine.config.PAGINATIONS = ('{bad}/pattern',)
        self.assertRaises(ValueError, getattr, self.engine, 'paginations')

    def test_paginate_not_implemented(self):
        self.engine.config.PAGINATIONS = ('unimplemented/{newtype}',)
        for unit in self.engine.units:
            setattr(unit, 'newtype', dict(foo='bar'))
        self.assertRaises(KeyError, getattr, self.engine, 'paginations')

    @patch('volt.engine.core.Pagination')
    def test_paginations_ok(self, Pagination_mock):
        pagination_patterns = ('',
                               'tag/{tags}',
                               'author/{author}',
                               '{time:%Y}',
                               '{time:%Y/%m}',)
        expected = ['', '2', '3',
                    'tag/arthur', 'tag/arthur/2', 'tag/arthur/3',
                    'tag/eames', 'tag/eames/2', 'tag/ariadne', 'tag/cobb',
                    'author/Smith', 'author/Smith/2', 'author/Johnson',
                    '2011', '2010', '2002', '1998',
                    '2011/09', '2010/09', '2010/07', '2002/08', '1998/04',]

        self.engine.config.PAGINATIONS = pagination_patterns
        observed = sum([len(x) for x in self.engine.paginations.values()])
        self.assertEqual(observed, len(expected))

    @patch('volt.engine.core.Engine._paginator')
    def test_paginate_all(self, paginator_mock):
        base_permalist = ['test']
        field = base_permalist[-1][1:-1]
        [x for x in self.engine._paginate_all(field, base_permalist, 2)]

        self.assertEqual(paginator_mock.call_count, 1)
        expected = call(self.engine.units, ['test'], 2, '')
        self.assertEqual(paginator_mock.call_args, expected)

    @patch('volt.engine.core.Engine._paginator')
    def test_paginate_single(self, paginator_mock):
        base_permalist = ['test', 'author', '{author}']
        field = base_permalist[-1][1:-1]
        [x for x in self.engine._paginate_single(field, base_permalist, 2)]

        self.assertEqual(2, paginator_mock.call_count)
        call1 = call(self.engine.units[:2] + [self.engine.units[3]], \
                ['test', 'author', 'Smith'], 2, '')
        call2 = call([self.engine.units[2], self.engine.units[4]], \
                ['test', 'author', 'Johnson'], 2, '')
        paginator_mock.assert_has_calls([call1, call2], any_order=True)

    @patch('volt.engine.core.Engine._paginator')
    def test_paginate_multiple(self, paginator_mock):
        base_permalist = ['test', 'tag', '{tags}']
        field = base_permalist[-1][1:-1]
        [x for x in self.engine._paginate_multiple(field, base_permalist, 2)]

        self.assertEqual(4, paginator_mock.call_count)
        call1 = call([self.engine.units[4]], ['test', 'tag', 'ariadne'], 2, '')
        call2 = call(self.engine.units[2:4], ['test', 'tag', 'cobb'], 2, '')
        call3 = call(self.engine.units[:3], ['test', 'tag', 'eames'], 2, '')
        call4 = call(self.engine.units, ['test', 'tag', 'arthur'], 2, '')
        paginator_mock.assert_has_calls([call1, call2, call3, call4], any_order=True)

    @patch('volt.engine.core.Engine._paginator')
    def test_paginate_datetime_single_time_token(self, paginator_mock):
        base_permalist = ['test', '{time:%Y}']
        field = base_permalist[-1][1:-1]
        [x for x in self.engine._paginate_datetime(field, base_permalist, 2)]

        self.assertEqual(4, paginator_mock.call_count)
        call1 = call(self.engine.units[:2], ['test', '2010'], 2, '')
        call2 = call([self.engine.units[2]], ['test', '1998'], 2, '')
        call3 = call([self.engine.units[3]], ['test', '2002'], 2, '')
        call4 = call([self.engine.units[4]], ['test', '2011'], 2, '')
        paginator_mock.assert_has_calls([call1, call2, call3, call4], any_order=True)

    @patch('volt.engine.core.Engine._paginator')
    def test_paginate_datetime_multiple_time_tokens(self, paginator_mock):
        base_permalist = ['test', '{time:%Y/%m}']
        field = base_permalist[-1][1:-1]
        [x for x in self.engine._paginate_datetime(field, base_permalist, 2)]

        self.assertEqual(paginator_mock.call_count, 5)
        call1 = call([self.engine.units[0]], ['test', '2010', '09'], 2, '')
        call2 = call([self.engine.units[1]], ['test', '2010', '07'], 2, '')
        call3 = call([self.engine.units[2]], ['test', '1998', '04'], 2, '')
        call4 = call([self.engine.units[3]], ['test', '2002', '08'], 2, '')
        call5 = call([self.engine.units[4]], ['test', '2011', '09'], 2, '')
        paginator_mock.assert_has_calls([call1, call2, call3, call4, call5], \
                any_order=True)

    @patch('volt.engine.core.Pagination')
    def test_paginator(self, Pagination_mock):
        pagins = [p for p in self.engine._paginator(self.engine.units, ['base'], 2)]

        self.assertEqual(3, len(pagins))
        call1 = call(self.engine.units[:2], 0, ['base'], '')
        call2 = call(self.engine.units[2:4], 1, ['base'], '')
        call3 = call(self.engine.units[4:], 2, ['base'], '')
        Pagination_mock.assert_has_calls([call1, call2, call3], any_order=True)


class PageCases(unittest.TestCase):

    def setUp(self):
        self.page = TestPage()

    def test_repr(self):
        repr = self.page.__repr__()
        self.assertEqual(repr, 'TestPage(test)')

    @patch('volt.engine.core.CONFIG', MagicMock())
    def test_slugify_empty(self):
        slugify = self.page.slugify
        cases = ['宇多田ヒカル', '&**%&^%&$-', u'ßÀœø']
        for case in cases:
            self.assertRaises(ValueError, slugify, case)

    @patch('volt.engine.core.CONFIG')
    def test_slugify_char_map_ok(self, config_mock):
        slugify = self.page.slugify
        setattr(config_mock, 'SITE', Config())
        config_mock.SITE.SLUG_CHAR_MAP = {u'ß': 'ss', u'ø': 'o'}
        self.assertEqual(slugify(u'viel-spaß'), 'viel-spass')
        self.assertEqual(slugify(u'Røyksopp'), 'royksopp')
        self.assertEqual(slugify(u'ßnakeørama'), 'ssnakeorama')

    @patch('volt.engine.core.CONFIG', MagicMock())
    def test_slugify_ok(self):
        slugify = self.page.slugify
        self.assertEqual(slugify('Move along people, this is just a test'),
                'move-along-people-this-is-just-test')
        self.assertEqual(slugify('What does it mean to say !&^#*&@$))*((&?'),
                'what-does-it-mean-to-say')
        self.assertEqual(slugify('What about the A* search algorithm?'),
                'what-about-the-a-search-algorithm')
        self.assertEqual(slugify('--This- is a bad -- -*&( ---___- title---'),
                'this-is-bad-title')
        self.assertEqual(slugify("Hors d'oeuvre, a fully-loaded MP5, and an astronaut from Ann Arbor."),
                'hors-doeuvre-fully-loaded-mp5-and-astronaut-from-ann-arbor')
        self.assertEqual(slugify('Kings of Convenience - Know How (feat. Feist)'),
                'kings-of-convenience-know-how-feat-feist')
        self.assertEqual(slugify('A Journey Through the Himalayan Mountains. Part 1: An Unusual Guest'),
                'journey-through-the-himalayan-mountains-part-1-unusual-guest')

    @patch('volt.engine.core.CONFIG.SITE.INDEX_HTML_ONLY', True)
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_path_permalinks_index_html_true(self):
        self.page.permalist = ['blog', 'not', 'string']
        self.page.slugify = lambda x: x

        self.assertEqual(self.page.path, os.path.join(USER_DIR, 'site', \
                'blog', 'not', 'string', 'index.html'))
        self.assertEqual(self.page.permalink, '/blog/not/string/')
        self.assertEqual(self.page.permalink_abs, 'http://foo.com/blog/not/string')

    @patch('volt.engine.core.CONFIG.SITE.INDEX_HTML_ONLY', False)
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_path_permalinks_index_html_false(self):
        self.page.permalist = ['blog', 'not', 'string']
        self.page.slugify = lambda x: x

        self.assertEqual(self.page.path, os.path.join(USER_DIR, 'site', \
                'blog', 'not', 'string.html'))
        self.assertEqual(self.page.permalink, '/blog/not/string.html')
        self.assertEqual(self.page.permalink_abs, 'http://foo.com/blog/not/string.html')


class UnitCases(unittest.TestCase):

    def setUp(self):
        self.unit = TestUnit(Engine.DEFAULTS)
        self.unit.config.URL = '/'

    def test_init(self):
        self.assertRaises(TypeError, TestUnit.__init__, 'foo')

    def test_check_required(self):
        req = ('title', 'surprise', )
        self.assertRaises(NameError, self.unit.check_required, req)

    def test_check_protected(self):
        prot = ('cats', )
        self.assertRaises(ValueError, self.unit.check_protected, 'cats', prot)

    def test_as_list_trailing(self):
        tags = 'ripley, ash, kane   '
        taglist = ['ripley', 'ash', 'kane'].sort()
        self.assertEqual(self.unit.as_list(tags, ', ').sort(), taglist)

    def test_as_list_extra_separator(self):
        tags = 'wickus;christopher;koobus;'
        taglist = ['wickus', 'christopher', 'koobus'].sort()
        self.assertEqual(self.unit.as_list(tags, ';').sort(), taglist)

    def test_as_list_duplicate_item(self):
        tags = 'trinity, twin, twin, morpheus'
        taglist = ['trinity', 'twin', 'morpheus'].sort()
        self.assertEqual(self.unit.as_list(tags, ', ').sort(), taglist)

    def test_permalist_missing_permalink(self):
        self.unit.config.URL = '/'
        del self.unit.config.PERMALINK
        self.assertRaises(AttributeError, getattr, self.unit, 'permalist')

    def test_permalist_missing_url(self):
        self.unit.config.PERMALINK = 'foo'
        del self.unit.config.URL
        self.assertRaises(AttributeError, getattr, self.unit, 'permalist')

    @patch('volt.engine.core.CONFIG', MagicMock())
    def test_permalist_error(self):
        self.unit.config.PERMALINK = 'bali/{beach}/party'
        self.assertRaises(AttributeError, getattr, self.unit, 'permalist')

    @patch('volt.engine.core.CONFIG', MagicMock())
    def test_permalist_ok_all_token_is_attrib(self):
        self.unit.slug = 'yo-dawg'
        self.unit.time = datetime(2009, 1, 28, 16, 47)
        self.unit.config.PERMALINK = '{time:%Y/%m/%d}/{slug}'
        self.assertEqual(self.unit.permalist, \
                ['', '2009', '01', '28', 'yo-dawg'])

    @patch('volt.engine.core.CONFIG', MagicMock())
    def test_permalist_ok_nonattrib_token(self):
        self.unit.slug = 'yo-dawg'
        self.unit.time = datetime(2009, 1, 28, 16, 47)
        self.unit.config.PERMALINK = '{time:%Y}/mustard/{time:%m}/{slug}/'
        self.assertEqual(self.unit.permalist, \
                ['', '2009', 'mustard', '01', 'yo-dawg'])

    @patch('volt.engine.core.CONFIG', MagicMock())
    def test_permalist_ok_space_in_token(self):
        self.unit.config.PERMALINK = 'i/love /mustard'
        self.assertEqual(self.unit.permalist, \
                ['', 'i', 'love', 'mustard'])


class UnitHeaderCases(unittest.TestCase):

    def setUp(self):
        config = MagicMock(spec=Config)
        config.DEFAULT_FIELDS = {}
        TestUnit.title = 'a'
        self.unit = TestUnit(config)

    def test_parse_header_protected(self):
        header_string = "content: this is a protected field"
        self.unit.config.PROTECTED = ('content', )
        self.assertRaises(ValueError, self.unit.parse_header, header_string)

    @patch.object(TestUnit, 'slugify')
    def test_parse_header_slug(self, slugify_mock):
        slugify_mock.return_value = 'foo-slug'
        header_string = "slug: foo-slug"
        self.unit.parse_header(header_string)
        self.assertEqual(self.unit.slug, 'foo-slug')

    def test_parse_header_as_list(self):
        self.unit.config.FIELDS_AS_LIST = 'tags'
        self.unit.config.LIST_SEP = ', '
        header_string = "tags: foo, bar, baz"
        self.unit.parse_header(header_string)
        expected = ['bar', 'baz', 'foo']
        self.unit.tags.sort()
        self.assertEqual(self.unit.tags, expected)

    def test_parse_header_as_datetime(self):
        self.unit.config.DATETIME_FORMAT = '%Y/%m/%d %H:%M'
        self.unit.config.FIELDS_AS_DATETIME = ('time', )
        header_string = "time: 2004/03/13 22:10"
        self.unit.parse_header(header_string)
        self.assertEqual(self.unit.time, datetime(2004, 3, 13, 22, 10))

    def test_parse_header_extra_field(self):
        header_string = "extra: surprise!"
        self.unit.parse_header(header_string)
        self.assertEqual(self.unit.extra, "surprise!")

    def test_parse_header_empty_field(self):
        header_string = "empty: "
        self.unit.parse_header(header_string)
        self.assertEqual(self.unit.empty, '')

    def test_repr(self):
        self.assertEqual(self.unit.__repr__(), 'TestUnit(test)')


@patch('volt.engine.core.CONFIG.SITE.INDEX_HTML_ONLY', True)
class PaginationCases(unittest.TestCase):

    def setUp(self):
        self.units = [MagicMock(Spec=Unit)] * 5
        self.site_dir = os.path.join(USER_DIR, 'site')

    @patch('volt.engine.core.CONFIG.SITE.PAGINATION_URL', 'page')
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_id(self):
        pagin = Pagination(self.units, 0, )
        self.assertEqual(pagin.id, '/')

    @patch('volt.engine.core.CONFIG.SITE.PAGINATION_URL', 'page')
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_init_idx_0(self):
        pagin = Pagination(self.units, 0, )
        self.assertEqual(pagin.path, os.path.join(self.site_dir, 'index.html'))
        self.assertEqual(pagin.permalink, '/')

    @patch('volt.engine.core.CONFIG.SITE.PAGINATION_URL', 'page')
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_init_idx_1(self):
        pagin = Pagination(self.units, 1, )
        self.assertEqual(pagin.path, os.path.join(self.site_dir, 'page', '2', 'index.html'))
        self.assertEqual(pagin.permalink, '/page/2/')

    @patch('volt.engine.core.CONFIG.SITE.PAGINATION_URL', 'page')
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_init_permalist(self):
        pagin = Pagination(self.units, 1, ['tech'])
        self.assertEqual(pagin.path, os.path.join(self.site_dir, 'tech', 'page', '2', 'index.html'))
        self.assertEqual(pagin.permalink, '/tech/page/2/')

    @patch('volt.engine.core.CONFIG.SITE.PAGINATION_URL', '')
    @patch('volt.engine.core.CONFIG', UniConfig_mock)
    def test_init_pagination_url(self):
        pagin = Pagination(self.units, 1, )
        self.assertEqual(pagin.path, os.path.join(self.site_dir, '2', 'index.html'))
        self.assertEqual(pagin.permalink, '/2/')

########NEW FILE########
__FILENAME__ = test_generator
# -*- coding: utf-8 -*-
"""
------------------------
volt.test.test_generator
------------------------

Tests for volt.generator.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""


import unittest

from mock import patch

from volt.engine.core import Engine
from volt.generator import Site
from volt.plugin.core import Plugin
from volt.test import INSTALL_DIR, make_uniconfig_mock


@patch.object(Site, 'config', make_uniconfig_mock())
class SiteCases(unittest.TestCase):

    def setUp(self):
        self.site = Site()

    @patch('volt.generator.path_import')
    def test_get_processor_unknown_type(self, path_import_mock):
        builtin_engine_name = 'volt.test.fixtures.install_dir.engine.builtins.in_install'
        path_import_mock.return_value = __import__(builtin_engine_name)
        self.assertRaises(AssertionError, self.site.get_processor, \
                'in_install', 'foo', INSTALL_DIR)

    def test_get_processor_unknown_name(self):
        self.assertRaises(ImportError, self.site.get_processor, \
                'foo', 'engines', INSTALL_DIR)

    def test_get_processor_builtin_engine(self):
        returned = self.site.get_processor('in_install', 'engines', \
                INSTALL_DIR)
        self.assertEqual(returned.__name__, 'TestBuiltin')
        self.assertTrue(issubclass(returned, Engine))

    def test_get_processor_user_engine(self):
        returned = self.site.get_processor('in_user', 'engines', \
                INSTALL_DIR)
        self.assertEqual(returned.__name__, 'TestUser')
        self.assertTrue(issubclass(returned, Engine))

    def test_get_processor_both_engine(self):
        returned = self.site.get_processor('in_both', 'engines', \
                INSTALL_DIR)
        self.assertEqual(returned.__name__, 'TestUser')
        self.assertTrue(issubclass(returned, Engine))

    def test_get_processor_builtin_plugin(self):
        returned = self.site.get_processor('in_install', 'plugins', \
                INSTALL_DIR)
        self.assertEqual(returned.__name__, 'TestBuiltin')
        self.assertTrue(issubclass(returned, Plugin))

    def test_get_processor_user_plugin(self):
        returned = self.site.get_processor('in_user', 'plugins', \
                INSTALL_DIR)
        self.assertEqual(returned.__name__, 'TestUser')
        self.assertTrue(issubclass(returned, Plugin))

    def test_get_processor_both_plugin(self):
        returned = self.site.get_processor('in_both', 'plugins', \
                INSTALL_DIR)
        self.assertEqual(returned.__name__, 'TestUser')
        self.assertTrue(issubclass(returned, Plugin))

########NEW FILE########
__FILENAME__ = test_main
# -*- coding: utf-8 -*-
"""
-------------------
volt.test.test_main
-------------------

Tests for the volt.main module.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os
import shutil
import sys
import unittest

from mock import patch, call, MagicMock

from volt import __version__, main
from volt.config import UnifiedConfigContainer
from volt.test import make_uniconfig_mock, FIXTURE_DIR, USER_DIR, INSTALL_DIR


COMMANDS = ['demo', 'ext', 'gen', 'init', 'serve', 'version']
CMD_INIT_DIR = os.path.join(FIXTURE_DIR, 'test_init')
CMD_DEMO_DIR = os.path.join(FIXTURE_DIR, 'test_demo')

UniConfig_mock = make_uniconfig_mock()


@patch.object(main, 'logging', MagicMock())
@patch.object(main.Runner, 'build_logger', MagicMock())
@patch.object(main, 'CONFIG', UniConfig_mock)
@patch.object(main, 'console')
class MainCases(unittest.TestCase):

    def test_cmd_ok(self, console_mock):
        commands = ['init', 'demo', 'gen', 'serve', 'version']
        for cmd in commands:
            with patch.object(main.Runner, 'run_%s' % cmd) as run_cmd:
                main.main([cmd])
                self.assertEqual([call()], run_cmd.call_args_list)

    #FIXME
    # skip testing if python version is <= 2.6, since argparser subparser
    # addition seems to be in random order
    if not sys.version_info[:2] <= (2, 6):
        def test_cmd_invalid(self, console_mock):
            commands = ['engines', 'foo', '']
            for cmd in commands:
                exp_call = call(\
                        "\nError: invalid choice: '%s' (choose from '%s')" % \
                        (cmd, "', '".join(COMMANDS)), color='red', is_bright=True)
                self.assertRaises(SystemExit, main.main, [cmd])
                self.assertEqual(exp_call, console_mock.call_args)

    def test_cmd_subcmd_ok(self, console_mock):
        commands = {'ext': ['engine', 'plugin', 'widget']}
        for cmd in commands:
            with patch.object(main.Runner, 'run_%s' % cmd) as run_cmd:
                for subcmd in commands[cmd]:
                    main.main([cmd, subcmd])
                self.assertEqual(call(), run_cmd.call_args)
                self.assertRaises(SystemExit, main.main, [cmd])

    def test_version_ok(self, console_mock):
        for path in (FIXTURE_DIR, USER_DIR, INSTALL_DIR):
            os.chdir(path)
            before = os.listdir(path)
            main.main(['version'])
            self.assertEqual(before, os.listdir(path))
            self.assertEqual(call('Volt %s' % __version__), console_mock.call_args)

    @patch('volt.config.os.getcwd', return_value=FIXTURE_DIR)
    def test_init_demo_nonempty_dir(self, getcwd_mock, console_mock):
        before = os.listdir(FIXTURE_DIR)

        for cmd in ('init', 'demo'):
            self.assertRaises(SystemExit, main.main, [cmd])
            exp_call = call("Error: 'volt %s' must be "
                    "run inside an empty directory." % cmd, \
                    color='red', is_bright=True)
            self.assertEqual(exp_call, console_mock.call_args)
            self.assertEqual(before, os.listdir(FIXTURE_DIR))


@patch.object(main, 'logging', MagicMock())
@patch.object(main.Runner, 'build_logger', MagicMock())
@patch.object(main, 'console')
class MainNoConfigCases(unittest.TestCase):

    def test_cmd_nonvolt_dir(self, console_mock):
        cmds = ['gen', 'serve']
        call2 = call("Start a Volt project by running 'volt init' inside an "
                     "empty directory.")

        for cmd in cmds:
            call1 = call("Error: You can only run 'volt %s' inside a Volt "
                         "project directory." % cmd, color='red', is_bright=True)
            before = os.listdir(FIXTURE_DIR)
            os.chdir(FIXTURE_DIR)
            self.assertRaises(SystemExit, main.main, [cmd])
            self.assertEqual(before, os.listdir(FIXTURE_DIR))
            self.assertEqual([call1, call2], console_mock.call_args_list)
            console_mock.reset_mock()


@patch.object(main, 'logging', MagicMock())
@patch.object(main.Runner, 'build_logger', MagicMock())
@patch.object(main, 'console')
class MainInitCases(unittest.TestCase):

    def setUp(self):
        self.console_call = call('\nVolt project started. Have fun!\n', is_bright=True)

    def tearDown(self):
        if os.path.exists(CMD_INIT_DIR):
            shutil.rmtree(CMD_INIT_DIR)
        # to reset main.CONFIG since it has been loaded with init's voltconf.py
        setattr(main, 'CONFIG', UnifiedConfigContainer())

    def run_init(self):
        if os.path.exists(CMD_INIT_DIR):
            shutil.rmtree(CMD_INIT_DIR)
        os.mkdir(CMD_INIT_DIR)
        os.chdir(CMD_INIT_DIR)
        main.main(['init'])

    def test_init_ok(self, console_mock):
        before = ['voltconf.py', 'contents/.placeholder', 'templates/base.html',
                  'templates/index.html', 'templates/assets/.placeholder',]
        before = [os.path.abspath(os.path.join(CMD_INIT_DIR, x)) for x in before]

        self.run_init()

        walk = list(os.walk(CMD_INIT_DIR))
        after = [os.path.join(d[0], f) for d in walk for f in d[2] if not f.endswith('.pyc')]
        [x.sort() for x in before, after]

        self.assertEqual(before, after)
        self.assertEqual([self.console_call], console_mock.call_args_list)

    @patch.object(main, 'generator', MagicMock())
    def test_init_gen_ok(self, console_mock):
        call2 = call('All engines are inactive -- nothing to generate.', \
                color='red', is_bright=True)

        self.run_init()
        before = [x for x in os.listdir(CMD_INIT_DIR) if \
                not (x.endswith('.pyc') or x == '__pycache__')]
        main.main(['gen'])
        after = [x for x in os.listdir(CMD_INIT_DIR) if \
                not (x.endswith('.pyc') or x == '__pycache__')]

        [x.sort() for x in before, after]

        self.assertEqual(before, after)
        self.assertEqual([self.console_call, call2], console_mock.call_args_list)

    @patch.object(main, 'server', MagicMock())
    @patch.object(main, 'generator', MagicMock())
    def test_init_serve_ok(self, console_mock):
        call2 = call('All engines are inactive -- nothing to generate.', \
                color='red', is_bright=True)
        call3 = call('Site directory not found -- nothing to serve.', \
                color='red', is_bright=True)

        self.run_init()
        before = [x for x in os.listdir(CMD_INIT_DIR) if \
                not (x.endswith('.pyc') or x == '__pycache__')]
        main.main(['serve'])
        after = [x for x in os.listdir(CMD_INIT_DIR) if \
                not (x.endswith('.pyc') or x == '__pycache__')]

        [x.sort() for x in before, after]

        self.assertEqual(before, after)
        self.assertEqual([self.console_call, call2, call3], console_mock.call_args_list)


@patch.object(main, 'logging', MagicMock())
@patch.object(main.Runner, 'build_logger', MagicMock())
@patch.object(main, 'console')
class MainDemoCases(unittest.TestCase):

    def tearDown(self):
        if os.path.exists(CMD_DEMO_DIR):
            shutil.rmtree(CMD_DEMO_DIR)
        # to reset main.CONFIG since it has been loaded with demo's voltconf.py
        setattr(main, 'CONFIG', UnifiedConfigContainer())

    def prep_demo(self):
        if os.path.exists(CMD_DEMO_DIR):
            shutil.rmtree(CMD_DEMO_DIR)
        os.mkdir(CMD_DEMO_DIR)
        os.chdir(CMD_DEMO_DIR)

    @patch.object(main.server.VoltHTTPServer, 'serve_forever')
    def test_demo_ok(self, serveforever_mock, console_mock):
        exp_call = call('\nPreparing your lightning-speed Volt tour...', is_bright=True)

        self.prep_demo()
        self.assertFalse(os.path.exists(os.path.join(CMD_DEMO_DIR, 'site')))
        self.assertRaises(SystemExit, main.main, ['demo'])
        self.assertTrue(os.path.exists(os.path.join(CMD_DEMO_DIR, 'site')))

        self.assertEqual([exp_call], console_mock.call_args_list)
        self.assertEqual([call()], serveforever_mock.call_args_list)

########NEW FILE########
__FILENAME__ = test_plugin
# -*- coding: utf-8 -*-
"""
---------------------
volt.test.test_plugin
---------------------

Tests for the volt.plugin package.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""


import unittest

from volt.plugin.core import Plugin


class TestPlugin(unittest.TestCase):

    def test_run(self):
        self.assertRaises(TypeError, Plugin.__init__, )

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
"""
--------------------
volt.test.test_utils
--------------------

Tests for the volt.utils module.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import os
import unittest
from inspect import getabsfile

from volt.utils import path_import
from volt.test import INSTALL_DIR, USER_DIR


class PathImportCases(unittest.TestCase):

    def test_path_import_string(self):
        path = os.path.join(INSTALL_DIR, 'engine', 'builtins')
        mod = path_import('in_install', path)
        mod_path = os.path.join(INSTALL_DIR, 'engine', 'builtins', 'in_install.py')
        self.assertEqual(getabsfile(mod), mod_path)

    def test_path_import_list(self):
        user_path = os.path.join(USER_DIR, 'engines')
        install_path = os.path.join(INSTALL_DIR, 'engine', 'builtins')
        paths = [user_path, install_path]
        mod = path_import('in_both', paths)
        mod_path = os.path.join(USER_DIR, 'engines', 'in_both.py')
        self.assertEqual(getabsfile(mod), mod_path)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
----------
volt.utils
----------

Collection of general handy methods used throughout Volt.

:copyright: (c) 2012 Wibowo Arindrarto <bow@bow.web.id>
:license: BSD

"""

import imp
import logging
import os
import sys
from datetime import datetime


COLOR_MAP = {'black': '30', 'red': '31',
             'green': '32', 'yellow': '33',
             'blue': '34', 'violet': '35',
             'cyan': '36', 'grey': '37'}

BRIGHTNESS_MAP = {'normal': '00', 'bold': '01'}

logger = logging.getLogger('util')


def cachedproperty(func):
    """Decorator for cached property loading."""
    attr_name = func.__name__
    @property
    def cached(self):
        if not hasattr(self, '_cache'):
            setattr(self, '_cache', {})
        try:
            return self._cache[attr_name]
        except KeyError:
            result = self._cache[attr_name] = func(self)
            return result
    return cached


class LoggableMixin(object):
    """Mixin for adding logging capabilities to classes."""
    @cachedproperty
    def logger(self):
        return logging.getLogger(type(self).__name__)


def time_string():
    """Returns string for logging time."""
    time = datetime.now()
    format = "%02d:%02d:%02d.%03.0f"
    return format % (time.hour, time.minute, time.second, \
            (time.microsecond / 1000.0 + 0.5))


def path_import(name, paths):
    """Imports a module from the specified path.

    name -- String denoting target module name.
    paths -- List of possible absolute directory paths or string of an
        absolute directory path that may contain the target module.

    """
    # convert to list if paths is string
    if isinstance(paths, basestring):
        paths = [paths]
    # force reload
    if name in sys.modules:
        del sys.modules[name]
    mod_tuple = imp.find_module(name, paths)
    return imp.load_module(name, *mod_tuple)


def console(string, format=None, color='grey', is_bright=False, log_time=True):
    """Formats the given string for console display.

    string -- String to display.
    format -- String to format the given string. Must include an extra '%s'
              for log_time() value if 'log_time' is True.
    color -- String indicating color.
    is_bright -- Boolean indicating whether to return a bright version of the
                 colored string or not.
    log_time -- Boolean indicating whether to log time or not.

    """
    if format is not None:
        if log_time:
            string = format % (time_string(), string)
        else:
            string = format % string

    if os.name != 'nt':
        brg = 'bold' if is_bright else 'normal'
        string = "\033[%s;%sm%s\033[m" % (BRIGHTNESS_MAP[brg], \
                COLOR_MAP[color], string)

    sys.stdout.write(string)


def write_file(file_path, string):
    """Writes string to the open file object."""
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, 'w') as target:
        target.write(string)
    message = "written: %s" % file_path
    logger.debug(message)

########NEW FILE########
