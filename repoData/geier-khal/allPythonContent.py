__FILENAME__ = pelican.conf
#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = u"Christian Geier"
SITENAME = u"khal"
SITEURL = '/khal'

TIMEZONE = 'Europe/Berlin'

DEFAULT_LANG='en'

# Blogroll
LINKS =  (
         )

# Social widget
SOCIAL = (
         )

TAG_FEED_ATOM=('feeds/%s.atom.xml')

DEFAULT_PAGINATION = 10

########NEW FILE########
__FILENAME__ = calendar_display
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from __future__ import print_function

import calendar
import datetime

from .terminal import bstring, rstring


def getweeknumber(date):
    """return iso week number for datetime.date object
    :param date: date
    :type date: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return datetime.date.isocalendar(date)[1]


def str_week(week, today):
    """returns a string representing one week,
    if for day == today colour is reversed

    :param week: list of 7 datetime.date objects (one week)
    :type day: list()
    :param today: the date of today
    :type today: datetime.date
    :return: string, which if printed on terminal appears to have length 20,
             but may contain ascii escape sequences
    :rtype: str
    """
    strweek = ''
    for day in week:
        if day == today:
            day = rstring(str(day.day).rjust(2))
        else:
            day = str(day.day).rjust(2)
        strweek = strweek + day + ' '
    return strweek


def vertical_month(month=datetime.date.today().month,
                   year=datetime.date.today().year,
                   today=datetime.date.today(),
                   weeknumber=False,
                   count=3,
                   firstweekday=0):
    """
    returns a list() of str() of weeks for a vertical arranged calendar

    :param month: first month of the calendar,
                  if non given, current month is assumed
    :type month: int
    :param year: year of the first month included,
                 if non given, current year is assumed
    :type year: int
    :param today: day highlighted, if non is given, current date is assumed
    :type today: datetime.date()
    :returns: calendar strings,  may also include some
              ANSI (color) escape strings
    :rtype: list() of str()
    """

    khal = list()
    w_number = '    ' if weeknumber else ''
    calendar.setfirstweekday(firstweekday)
    khal.append(bstring('    ' + calendar.weekheader(2) + ' ' + w_number))
    for _ in range(count):
        for week in calendar.Calendar(firstweekday).monthdatescalendar(year, month):
            new_month = len([day for day in week if day.day == 1])
            strweek = str_week(week, today)
            if new_month:
                m_name = bstring(calendar.month_abbr[week[6].month].ljust(4))
            else:
                m_name = '    '
            w_number = bstring(
                ' ' + str(getweeknumber(week[0]))) if weeknumber else ''
            sweek = m_name + strweek + w_number
            if sweek != khal[-1]:
                khal.append(sweek)
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    return khal

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2013-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
"""khal

Usage:
  khal calendar [-vc CONF] [ (-a CAL ... | -d CAL ... ) ] [DATE ...]
  khal agenda   [-vc CONF] [ (-a CAL ... | -d CAL ... ) ] [DATE ...]
  khal interactive [-vc CONF] [ (-a CAL ... | -d CAL ... ) ]
  khal new [-vc CONF] [-a cal] DESCRIPTION...
  khal printcalendars [-vc CONF]
  khal [-vc CONF] [ (-a CAL ... | -d CAL ... ) ] [DATE ...]
  khal (-h | --help)
  khal --version


Options:
  -h --help    Show this help.
  --version    Print version information.
  -a CAL       Use this calendars (can be used several times)
  -d CAL       Do not use this calendar (can be used several times)
  -v           Be extra verbose.
  -c CONF      Use this config file.

"""
import logging
import os
import re
import signal
import sys

try:
    from ConfigParser import RawConfigParser
    from ConfigParser import Error as ConfigParserError

except ImportError:
    from configparser import RawConfigParser
    from configparser import Error as ConfigParserError

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

from docopt import docopt
import pytz
import xdg

from khal import controllers
from khal import khalendar
from khal import __version__, __productname__
from khal.log import logger


def capture_user_interruption():
    """
    Tries to hide to the user the ugly python backtraces generated by
    pressing Ctrl-C.
    """
    signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))


def _find_configuration_file():
    """Return the configuration filename.

    This function builds the list of paths known by khal and
    then return the first one which exists. The first paths
    searched are the ones described in the XDG Base Directory
    Standard. Each one of this path ends with
    DEFAULT_PATH/DEFAULT_FILE.

    On failure, the path DEFAULT_PATH/DEFAULT_FILE, prefixed with
    a dot, is searched in the home user directory. Ultimately,
    DEFAULT_FILE is searched in the current directory.
    """
    DEFAULT_FILE = __productname__ + '.conf'
    DEFAULT_PATH = __productname__
    resource = os.path.join(DEFAULT_PATH, DEFAULT_FILE)

    paths = []
    paths.extend([os.path.join(path, resource)
                  for path in xdg.BaseDirectory.xdg_config_dirs])
    paths.append(os.path.expanduser(os.path.join('~', '.' + resource)))
    paths.append(os.path.expanduser(DEFAULT_FILE))

    for path in paths:
        if os.path.exists(path):
            return path

    return None


class Namespace(dict):

    """The khal configuration holder.

    Mostly taken from pycarddav.

    This holder is a dict subclass that exposes its items as attributes.
    Inspired by NameSpace from argparse, Configuration is a simple
    object providing equality by attribute names and values, and a
    representation.

    Warning: Namespace instances do not have direct access to the dict
    methods. But since it is a dict object, it is possible to call
    these methods the following way: dict.get(ns, 'key')

    See http://code.activestate.com/recipes/577887-a-simple-namespace-class/
    """

    def __init__(self, obj=None):
        dict.__init__(self, obj if obj else {})

    def __dir__(self):
        return list(self)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict.__repr__(self))

    def __getattribute__(self, name):
        try:
            return self[name]
        except KeyError:
            msg = "'%s' object has no attribute '%s'"
            raise AttributeError(msg % (type(self).__name__, name))

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]


class Section(object):

    def __init__(self, parser, group):
        self._parser = parser
        self._group = group
        self._schema = None
        self._parsed = {}

    def matches(self, name):
        return self._group == name.lower()

    def is_collection(self):
        return False

    def parse(self, section):
        failed = False
        if self._schema is None:
            return None

        for option, default, filter_ in self._schema:
            if filter_ is None:
                filter_ = lambda x: x
            try:
                self._parsed[option] = filter_(
                    self._parser.get(section, option)
                )
                self._parser.remove_option(section, option)
            except ConfigParserError:
                if default is None:
                    logger.error(
                        "Missing required option '{option}' in section "
                        "'{section}'".format(option=option, section=section))
                    failed = True
                self._parsed[option] = default
                # Remove option once handled (see the check function).
                self._parser.remove_option(section, option)

        if failed:
            return None
        else:
            return Namespace(self._parsed)

    @property
    def group(self):
        return self._group

    def _parse_bool_string(self, value):
        """if value is either 'True' or 'False' it returns that value as a
        bool, otherwise it returns the value"""
        value = value.strip().lower()
        if value in ['true', 'yes', '1']:
            return True
        else:
            return False

    def _parse_time_zone(self, value):
        """returns pytz timezone"""
        return pytz.timezone(value)

    def _parse_commands(self, command):
        commands = [
            'agenda', 'calendar', 'new', 'interactive', 'printcalendars']
        if command not in commands:
            logger.error("Invalid value '{}' for option 'default_command' in "
                         "section 'default'".format(command))
            return None
        else:
            return command


class CalendarSection(Section):

    def __init__(self, parser):
        Section.__init__(self, parser, 'calendars')
        self._schema = [
            ('path', None, os.path.expanduser),
            ('readonly', False, self._parse_bool_string),
            ('color', '', None)
        ]

    def is_collection(self):
        return True

    def matches(self, name):
        match = re.match('calendar (?P<name>.*)', name, re.I)
        if match:
            self._parsed['name'] = match.group('name')
        return match is not None


class SQLiteSection(Section):

    def __init__(self, parser):
        Section.__init__(self, parser, 'sqlite')
        default_path = xdg.BaseDirectory.xdg_cache_home + '/khal/khal.db'
        self._schema = [
            ('path', default_path, os.path.expanduser),
        ]


class LocaleSection(Section):
    def __init__(self, parser):
        Section.__init__(self, parser, 'locale')
        self._schema = [
            ('local_timezone', None, self._parse_time_zone),
            ('default_timezone', None, self._parse_time_zone),
            ('timeformat', None, None),
            ('dateformat', None, None),
            ('longdateformat', None, None),
            ('datetimeformat', None, None),
            ('longdatetimeformat', None, None),
            ('firstweekday', 0, int),
            ('encoding', 'utf-8', None),
            ('unicode_symbols', True, self._parse_bool_string),
        ]


class DefaultSection(Section):
    def __init__(self, parser):
        Section.__init__(self, parser, 'default')
        self._schema = [
            ('debug', False, self._parse_bool_string),
            ('default_command', 'calendar', self._parse_commands),
            ('default_calendar', True, None),
        ]


class ConfigParser(object):
    _sections = [
        DefaultSection, LocaleSection, SQLiteSection, CalendarSection
    ]

    _required_sections = [DefaultSection, LocaleSection, CalendarSection]

    def _get_section_parser(self, section):
        for cls in self._sections:
            parser = cls(self._conf_parser)
            if parser.matches(section):
                return parser
        return None

    def parse_config(self, cfile):
        self._conf_parser = RawConfigParser()
        try:
            if not self._conf_parser.read(cfile):
                logger.error("Cannot read config file' {}'".format(cfile))
                return None
        except ConfigParserError as error:
            logger.error("Could not parse config file "
                         "'{}': {}".format(cfile, error))
            return None
        items = dict()
        failed = False
        for section in self._conf_parser.sections():
            parser = self._get_section_parser(section)
            if parser is None:
                logger.warning(
                    "Found unknown section '{}' in config file".format(section)
                )
                continue

            values = parser.parse(section)
            if values is None:
                failed = True
                continue
            if parser.is_collection():
                if parser.group not in items:
                    items[parser.group] = []
                items[parser.group].append(values)
            else:
                items[parser.group] = values

        failed = self.check_required(items) or failed
        self.warn_leftovers()
        self.dump(items)

        if failed:
            return None
        else:
            return Namespace(items)

    def check_required(self, items):
        groupnames = [sec(None).group for sec in self._required_sections]
        failed = False
        for group in groupnames:
            if group not in items:
                logger.error(
                    "Missing required section '{}'".format(group))
                failed = True
        return failed

    def warn_leftovers(self):
        for section in self._conf_parser.sections():
            for option in self._conf_parser.options(section):
                logger.warn("Ignoring unknow option '{}' in section "
                            "'{}'".format(option, section))

    def dump(self, conf, intro='Using configuration:', tab=0):
        """Dump the loaded configuration using the logging framework.

        The values displayed here are the exact values which are seen by
        the program, and not the raw values as they are read in the
        configuration file.
        """
        # TODO while this is fully functional it could be prettier
        logger.debug('{0}{1}'.format('\t' * tab, intro))

        if isinstance(conf, (Namespace, dict)):
            for name, value in sorted(dict.copy(conf).items()):
                if isinstance(value, (Namespace, dict, list)):
                    self.dump(value, '[' + name + ']', tab=tab + 1)
                else:
                    logger.debug('{0}{1}: {2}'.format('\t' * (tab + 1), name,
                                                      value))
        elif isinstance(conf, list):
            for o in conf:
                self.dump(o, '\t' * tab + intro + ':', tab + 1)


def validate(conf, logger):
    """
    validate the config
    """
    rval = True
    cal_name = conf.default.default_calendar
    if cal_name is True:
        conf.default.default_calendar = conf.calendars[0].name

    else:
        if cal_name not in [cal.name for cal in conf.calendars]:
            logger.fatal('{} is not a valid calendar'.format(cal_name))
            rval = False
    if rval:
        return conf
    else:
        return None


def main_khal():
    capture_user_interruption()

    # setting the process title so it looks nicer in ps
    # shows up as 'khal' under linux and as 'python: khal (python2.7)'
    # under FreeBSD, which is still nicer than the default
    setproctitle('khal')

    arguments = docopt(__doc__, version=__productname__ + ' ' + __version__,
                       options_first=False)

    if arguments['-c'] is None:
        arguments['-c'] = _find_configuration_file()
    if arguments['-c'] is None:
        sys.exit('Cannot find any config file, exiting')
    if arguments['-v']:
        logger.setLevel(logging.DEBUG)

    conf = ConfigParser().parse_config(arguments['-c'])

    # TODO use some existing lib and move all the validation from ConfigParse
    # into validate as well
    conf = validate(conf, logger)

    if conf is None:
        sys.exit('Invalid config file, exiting.')

    collection = khalendar.CalendarCollection()
    for cal in conf.calendars:
        if (cal.name in arguments['-a'] and arguments['-d'] == list()) or \
           (cal.name not in arguments['-d'] and arguments['-a'] == list()):
            collection.append(khalendar.Calendar(
                name=cal.name,
                dbpath=conf.sqlite.path,
                path=cal.path,
                readonly=cal.readonly,
                color=cal.color,
                unicode_symbols=conf.locale.unicode_symbols,
                local_tz=conf.locale.local_timezone,
                default_tz=conf.locale.default_timezone
            ))
    collection._default_calendar_name = conf.default.default_calendar
    commands = ['agenda', 'calendar', 'new', 'interactive', 'printcalendars']

    if not any([arguments[com] for com in commands]):

        arguments = docopt(__doc__,
                           version=__productname__ + ' ' + __version__,
                           argv=[conf.default.default_command] + sys.argv[1:])

        # arguments[conf.default.default_command] = True  # TODO

    if arguments['calendar']:
        controllers.Calendar(collection,
                             date=arguments['DATE'],
                             firstweekday=conf.locale.firstweekday,
                             encoding=conf.locale.encoding,
                             dateformat=conf.locale.dateformat,
                             longdateformat=conf.locale.longdateformat,
                             )
    elif arguments['agenda']:
        controllers.Agenda(collection,
                           date=arguments['DATE'],
                           firstweekday=conf.locale.firstweekday,
                           encoding=conf.locale.encoding,
                           dateformat=conf.locale.dateformat,
                           longdateformat=conf.locale.longdateformat,
                           )
    elif arguments['new']:
        controllers.NewFromString(collection, conf, arguments['DESCRIPTION'])
    elif arguments['interactive']:
        controllers.Interactive(collection, conf)
    elif arguments['printcalendars']:
        print('\n'.join(collection.names))


def main_ikhal():
    sys.argv = [sys.argv[0], 'interactive'] + sys.argv[1:]
    main_khal()

########NEW FILE########
__FILENAME__ = compat
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys


if sys.version_info[0] == 2:
    unicode_type = unicode
    bytes_type = str
    iteritems = lambda d, *args, **kwargs: iter(d.iteritems(*args, **kwargs))
else:
    unicode_type = str
    bytes_type = bytes
    iteritems = lambda d, *args, **kwargs: iter(d.items(*args, **kwargs))

########NEW FILE########
__FILENAME__ = controllers
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import datetime
import logging
import sys
import textwrap

from khal import aux, calendar_display
from khal import __version__, __productname__
from .terminal import bstring, colored, get_terminal_size, merge_columns


def get_agenda(collection, dateformat, longdateformat, dates=[], width=45):
    """returns a list of events scheduled for all days in daylist

    included are header "rows"
    :param collection:
    :type collection: khalendar.CalendarCollection
    :param dates: a list of all dates for which the events should be return,
                    including what should be printed as a header
    :type collection: list(str)
    :returns: a list to be printed as the agenda for the given days
    :rtype: list(str)

    """
    event_column = list()

    if dates == []:
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        daylist = [(today, 'Today:'), (tomorrow, 'Tomorrow:')]
    else:
        try:
            daylist = [aux.datefstr(date, dateformat, longdateformat)
                       for date in dates]
        except aux.InvalidDate as error:
            logging.fatal(error)
            sys.exit(1)
        daynames = [date.strftime(longdateformat) for date in daylist]

        daylist = zip(daylist, daynames)

    for day, dayname in daylist:
        # TODO unify allday and datetime events
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)

        event_column.append(bstring(dayname))

        all_day_events = collection.get_allday_by_time_range(day)
        events = collection.get_datetime_by_time_range(start, end)
        for event in all_day_events:
            desc = textwrap.wrap(event.compact(day), width)
            event_column.extend([colored(d, event.color) for d in desc])

        events.sort(key=lambda e: e.start)
        for event in events:
            desc = textwrap.wrap(event.compact(day), width)
            event_column.extend([colored(d, event.color) for d in desc])
    return event_column


class Calendar(object):
    def __init__(self, collection, date=[], firstweekday=0, encoding='utf-8',
                 **kwargs):
        term_width, _ = get_terminal_size()
        lwidth = 25
        rwidth = term_width - lwidth - 4
        event_column = get_agenda(collection, dates=date, width=rwidth,
                                  **kwargs)
        calendar_column = calendar_display.vertical_month(
            firstweekday=firstweekday)

        rows = merge_columns(calendar_column, event_column)
        print('\n'.join(rows).encode(encoding))


class Agenda(object):
    def __init__(self, collection, date=None, firstweekday=0, encoding='utf-8',
                 **kwargs):
        term_width, _ = get_terminal_size()
        event_column = get_agenda(collection, dates=date, width=term_width,
                                  **kwargs)
        print('\n'.join(event_column).encode(encoding))


class NewFromString(object):
    def __init__(self, collection, conf, date_list):
        event = aux.construct_event(date_list,
                                    conf.locale.timeformat,
                                    conf.locale.dateformat,
                                    conf.locale.longdateformat,
                                    conf.locale.datetimeformat,
                                    conf.locale.longdatetimeformat,
                                    conf.locale.local_timezone,
                                    encoding=conf.locale.encoding)
        event = collection.new_event(event,
                                     collection.default_calendar_name,
                                     conf.locale.local_timezone,
                                     conf.locale.default_timezone,
                                     )

        collection.new(event)


class Interactive(object):

    def __init__(self, collection, conf):
        import ui
        pane = ui.ClassicView(collection,
                              conf,
                              title='select an event',
                              description='do something')
        ui.start_pane(pane, pane.cleanup,
                      header=u'{0} v{1}'.format(__productname__, __version__))

########NEW FILE########
__FILENAME__ = backend
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The SQLite backend implementation.

Database Layout
===============

current version number: 2
tables: version, accounts, account_$ACCOUNTNAME

version:
    version (INT): only one line: current db version

account:
    account (TEXT): name of the account
    resource (TEXT)
    last_sync (TEXT)
    etag (TEX)

$ACCOUNTNAME_m:  # as in master
    href (TEXT)
    href (TEXT)
    etag (TEXT)
    start (INT): start date of event (unix time)
    end (INT): start date of event (unix time)
    all_day (INT): 1 if event is 'all day event', 0 otherwise
    vevent (TEXT): the actual vcard

$ACCOUNTNAME_d: #all day events
    # keeps start and end dates of all events, incl. recurrent dates
    dtstart (INT)
    dtend (INT)
    href (TEXT)

$ACCOUNTNAME_dt: #other events, same as above
    dtstart (INT)
    dtend (INT)
    href (TEXT)

"""

from __future__ import print_function

import calendar
import datetime
from os import makedirs, path
import sys
import sqlite3
import time

import icalendar
import pytz
import xdg.BaseDirectory

from .event import Event
from . import datetimehelper
from .. import log

logger = log.logger


# TODO fix that event/vevent mess


class UpdateFailed(Exception):

    """raised if update not possible"""
    pass


class SQLiteDb(object):

    """Querying the addressbook database

    the type() of parameters named "account" should be something like str()
    and of parameters named "accountS" should be an iterable like list()
    """

    def __init__(self, db_path, local_tz, default_tz, debug=False):

        if db_path is None:
            db_path = xdg.BaseDirectory.save_data_path('khal') + '/khal.db'
        self.db_path = path.expanduser(db_path)
        self._create_dbdir()
        self.local_tz = local_tz
        self.default_tz = default_tz
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.debug = debug
        self._create_default_tables()
        self._check_table_version()
        self._accounts = []

    def __del__(self):
        self.conn.close()

    def _dump(self, account):
        """return table self.account, used for testing"""
        sql_s = 'SELECT * FROM {0}'.format(account + '_m')
        result = self.sql_ex(sql_s)
        return result

    def _create_dbdir(self):
        """create the dbdir if it doesn't exist"""
        dbdir = self.db_path.rsplit('/', 1)[0]
        if not path.isdir(dbdir):
            try:
                logger.debug('trying to create the directory for the db')
                makedirs(dbdir, mode=0770)
                logger.debug('success')
            except OSError as error:
                logger.fatal('failed to create {0}: {1}'.format(dbdir, error))
                raise CouldNotCreateDbDir

    def _check_table_version(self):
        """tests for curent db Version
        if the table is still empty, insert db_version
        """
        database_version = 2  # the current db VERSION
        self.cursor.execute('SELECT version FROM version')
        result = self.cursor.fetchone()
        if result is None:
            stuple = (database_version, )  # database version db Version
            self.cursor.execute('INSERT INTO version (version) VALUES (?)',
                                stuple)
            self.conn.commit()
        elif not result[0] == database_version:
            raise Exception(str(self.db_path) +
                            " is probably an invalid or outdated database.\n"
                            "You should consider to remove it and sync again.")

    def _create_default_tables(self):
        """creates version and account tables and inserts table version number
        """
        try:
            self.sql_ex('CREATE TABLE IF NOT EXISTS version (version INTEGER)')
            logger.debug("created version table")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()

        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                account TEXT NOT NULL UNIQUE,
                resource TEXT NOT NULL,
                last_sync TEXT,
                ctag FLOAT
                )''')
            logger.debug("created accounts table")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()
        self._check_table_version()  # insert table version

    def _check_account(self, account):
        if account in self._accounts:
            return
        else:
            self.create_account_table(account)
            self._accounts.append(account)

    def sql_ex(self, statement, stuple='', commit=True):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        if commit:
            self.conn.commit()
        return result

    def create_account_table(self, account):
        count_sql_s = """SELECT count(*) FROM accounts
                WHERE account = ? AND resource = ?"""
        stuple = (account, '')
        self.cursor.execute(count_sql_s, stuple)
        result = self.cursor.fetchone()

        if(result[0] != 0):
            return
        sql_s = """CREATE TABLE IF NOT EXISTS {0} (
                href TEXT UNIQUE,
                etag TEXT,
                vevent TEXT
                )""".format(account + '_m')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(account + '_dt')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(account + '_d')
        self.sql_ex(sql_s)
        sql_s = 'INSERT INTO accounts (account, resource) VALUES (?, ?)'
        stuple = (account, '')
        self.sql_ex(sql_s, stuple)
        logger.debug("made sure tables for {0} exists".format(account))

    def needs_update(self, account, href_etag_list):
        """checks if we need to update this vcard
        :param account: account
        :param account: string
        :param href_etag_list: list of tuples of (hrefs and etags)
        :return: list of hrefs that need an update
        """
        self._check_account(account)
        needs_update = list()
        for href, etag in href_etag_list:
            stuple = (href,)
            sql_s = 'SELECT etag FROM {0} WHERE href = ?'.format(
                account + '_m')
            result = self.sql_ex(sql_s, stuple)
            if not result or etag != result[0][0]:
                needs_update.append(href)
        return needs_update

    def update(self, vevent, account, href=None, etag='',
               ignore_invalid_items=False):
        """insert a new or update an existing card in the db

        This is mostly a wrapper around two SQL statements, doing some cleanup
        before.

        :param vevent: event to be inserted or updated. If this is a calendar
                       object, it will be searched for an event.
        :type vevent: unicode
        :param ignore_invalid_items: If true, raise UpdateFailed if given
                                     vevent is not a valid event or calendar
                                     object. If false, don't do anything.
        :type ignore_invalid_items: bool
        :param href: href of the card on the server, if this href already
                     exists in the db the card gets updated. If no href is
                     given, a random href is chosen and it is implied that this
                     card does not yet exist on the server, but will be
                     uploaded there on next sync.
        :type href: str()
        :param etag: the etag of the vcard, if this etag does not match the
                     remote etag on next sync, this card will be updated from
                     the server. For locally created vcards this should not be
                     set
        :type etag: str()
        """
        if href is None:
            raise ValueError('href may not be one')
        self._check_account(account)
        if not isinstance(vevent, icalendar.cal.Event):
            ical = icalendar.Event.from_ical(vevent)
            vevent = None
            for component in ical.walk():
                if component.name == 'VEVENT':
                    vevent = component
                    break

        if vevent is None:
            if ignore_invalid_items:
                return
            else:
                raise UpdateFailed(u'Could not find event in {}'.format(ical))

        all_day_event = False
        if href == '' or href is None:
            href = get_random_href()
        if 'VALUE' in vevent['DTSTART'].params:
            if vevent['DTSTART'].params['VALUE'] == 'DATE':
                all_day_event = True

        dtstartend = datetimehelper.expand(vevent,
                                           self.default_tz,
                                           href)

        for dbname in [account + '_d', account + '_dt']:
            sql_s = ('DELETE FROM {0} WHERE href == ?'.format(dbname))
            self.sql_ex(sql_s, (href, ), commit=False)

        for dtstart, dtend in dtstartend:
            if all_day_event:
                dbstart = dtstart.strftime('%Y%m%d')
                dbend = dtend.strftime('%Y%m%d')
                dbname = account + '_d'
            else:
                # TODO: extract strange (aka non Olson) TZs from params['TZID']
                # perhaps better done in event/vevent
                if dtstart.tzinfo is None:
                    dtstart = self.default_tz.localize(dtstart)
                if dtend.tzinfo is None:
                    dtend = self.default_tz.localize(dtend)

                dtstart_utc = dtstart.astimezone(pytz.UTC)
                dtend_utc = dtend.astimezone(pytz.UTC)
                dbstart = calendar.timegm(dtstart_utc.timetuple())
                dbend = calendar.timegm(dtend_utc.timetuple())
                dbname = account + '_dt'

            sql_s = ('INSERT INTO {0} '
                     '(dtstart, dtend, href) '
                     'VALUES (?, ?, ?);'.format(dbname))
            stuple = (dbstart,
                      dbend,
                      href)
            self.sql_ex(sql_s, stuple, commit=False)

        sql_s = ('INSERT OR REPLACE INTO {0} '
                 '(vevent, etag, href) '
                 'VALUES (?, ?, '
                 'COALESCE((SELECT href FROM {0} WHERE href = ?), ?)'
                 ');'.format(account + '_m'))

        stuple = (vevent.to_ical().decode('utf-8'),
                  etag,
                  href,
                  href)
        self.sql_ex(sql_s, stuple, commit=False)
        self.conn.commit()

    def get_ctag(self, account):
        stuple = (account, )
        sql_s = 'SELECT ctag FROM accounts WHERE account = ?'
        try:
            ctag = self.sql_ex(sql_s, stuple)[0][0]
            return ctag
        except IndexError:
            return None

    def set_ctag(self, account, ctag):
        stuple = (ctag, account, )
        sql_s = 'UPDATE accounts SET ctag = ? WHERE account = ?'
        self.sql_ex(sql_s, stuple)
        self.conn.commit()

    def update_href(self, oldhref, newhref, account, etag=''):
        """updates old_href to new_href, can also alter etag,
        see update() for an explanation of these parameters"""
        self._check_account(account)
        stuple = (newhref, etag, oldhref)
        sql_s = 'UPDATE {0} SET href = ?, etag = ?, \
             WHERE href = ?;'.format(account + '_m')
        self.sql_ex(sql_s, stuple)
        for dbname in [account + '_d', account + '_dt']:
            sql_s = 'UPDATE {0} SET href = ? WHERE href = ?;'.format(dbname)
            self.sql_ex(sql_s, (newhref, oldhref))

    def href_exists(self, href, account):
        """returns True if href already exists in db

        :param href: href
        :type href: str()
        :returns: True or False
        """
        self._check_account(account)
        sql_s = 'SELECT href FROM {1} WHERE href = ?;'.format(account)
        if len(self.sql_ex(sql_s, (href, ))) == 0:
            return False
        else:
            return True

    def get_etag(self, href, account):
        """get etag for href

        type href: str()
        return: etag
        rtype: str()
        """
        self._check_account(account)
        sql_s = 'SELECT etag FROM {0} WHERE href=(?);'.format(account + '_m')
        try:
            etag = self.sql_ex(sql_s, (href,))[0][0]
            return etag
        except IndexError:
            return None

    def delete(self, href, account):
        """
        removes the event from the db,
        returns nothing
        """
        self._check_account(account)
        for dbname in [account + '_d', account + '_dt', account + '_m']:
            sql_s = 'DELETE FROM {0} WHERE href = ? ;'.format(dbname)
            self.sql_ex(sql_s, (href, ))

    def get_all_href_from_db(self, accounts):
        """returns a list with all hrefs
        """
        result = list()
        for account in accounts:
            self._check_account(account)
            hrefs = self.sql_ex('SELECT href FROM {0}'.format(account + '_m'))
            result = result + [(href[0], account) for href in hrefs]
        return result

    def get_time_range(self, start, end, account, color='', readonly=False,
                       unicode_symbols=True, show_deleted=True):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        :param deleted: include deleted events in returned lsit
        """
        self._check_account(account)
        start = time.mktime(start.timetuple())
        end = time.mktime(end.timetuple())
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart <= ? OR '
                 'dtend >= ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend >= ?').format(account + '_dt')
        stuple = (start, end, start, end, start, end)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, start, end in result:
            start = pytz.UTC.localize(
                datetime.datetime.utcfromtimestamp(start))
            end = pytz.UTC.localize(datetime.datetime.utcfromtimestamp(end))
            event = self.get_vevent_from_db(href, account,
                                            start=start, end=end,
                                            color=color,
                                            readonly=readonly,
                                            unicode_symbols=unicode_symbols)
            event_list.append(event)
        return event_list

    def get_allday_range(self, start, end=None, account=None, color='',
                         readonly=False, unicode_symbols=True,
                         show_deleted=True):
        self._check_account(account)
        if account is None:
            raise Exception('need to specify an account')
        strstart = start.strftime('%Y%m%d')
        if end is None:
            end = start + datetime.timedelta(days=1)
        strend = end.strftime('%Y%m%d')
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart < ? OR '
                 'dtend > ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend > ? ').format(account + '_d')
        stuple = (strstart, strend, strstart, strend, strstart, strend)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, start, end in result:
            start = time.strptime(str(start), '%Y%m%d')
            end = time.strptime(str(end), '%Y%m%d')
            start = datetime.date(start.tm_year, start.tm_mon, start.tm_mday)
            end = datetime.date(end.tm_year, end.tm_mon, end.tm_mday)
            event = self.get_vevent_from_db(href, account,
                                            start=start, end=end,
                                            color=color,
                                            readonly=readonly,
                                            unicode_symbols=unicode_symbols)
            event_list.append(event)
        return event_list

    def hrefs_by_time_range_datetime(self, start, end, account, color=''):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        """
        self._check_account(account)
        start = time.mktime(start.timetuple())
        end = time.mktime(end.timetuple())
        sql_s = ('SELECT href FROM {0} WHERE '
                 'dtstart >= ? AND dtstart <= ? OR '
                 'dtend >= ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend >= ?').format(account + '_dt')
        stuple = (start, end, start, end, start, end)
        result = self.sql_ex(sql_s, stuple)
        return [one[0] for one in result]

    def hrefs_by_time_range_date(self, start, end=None, account=None):
        self._check_account(account)
        if account is None:
            raise Exception('need to specify an account')
        strstart = start.strftime('%Y%m%d')
        if end is None:
            end = start + datetime.timedelta(days=1)
        strend = end.strftime('%Y%m%d')
        sql_s = ('SELECT href FROM {0} WHERE '
                 'dtstart >= ? AND dtstart < ? OR '
                 'dtend > ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend > ? ').format(account + '_d')
        stuple = (strstart, strend, strstart, strend, strstart, strend)
        result = self.sql_ex(sql_s, stuple)
        return [one[0] for one in result]

    def hrefs_by_time_range(self, start, end, account):
        return list(set(self.hrefs_by_time_range_date(start, end, account) +
                    self.hrefs_by_time_range_datetime(start, end, account)))

    def get_vevent_from_db(self, href, account, start=None, end=None,
                           readonly=False, color=lambda x: x,
                           unicode_symbols=True):
        """returns the Event matching href, if start and end are given, a
        specific Event from a Recursion set is returned, the Event as saved in
        the db

        All other parameters given to this function are handed over to the
        Event.
        """
        self._check_account(account)
        sql_s = 'SELECT vevent, etag FROM {0} WHERE href=(?)'.format(
            account + '_m')
        result = self.sql_ex(sql_s, (href, ))
        return Event(result[0][0],
                     local_tz=self.local_tz,
                     default_tz=self.default_tz,
                     start=start,
                     end=end,
                     color=color,
                     href=href,
                     account=account,
                     readonly=readonly,
                     etag=result[0][1],
                     unicode_symbols=unicode_symbols)


def get_random_href():
    """returns a random href
    """
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()


class Failure(Exception):
    pass


class CouldNotCreateDbDir(Failure):
    pass

########NEW FILE########
__FILENAME__ = datetimehelper
from datetime import date, datetime, timedelta

import dateutil.rrule
import pytz

from .. import log

logger = log.logger


class UnsupportedRecursion(Exception):
    """raised if the RRULE is not understood by dateutil.rrule"""
    pass


def expand(vevent, default_tz, href=''):
    """

    :param vevent: vevent to be expanded
    :type vevent: icalendar.cal.Event
    :param default_tz: the default timezone used when we (icalendar)
                       don't understand the embedded timezone
    :type default_tz: pytz.timezone
    :param href: the href of the vevent, used for more informative logging
    :type href: str
    :returns: list of start and end (date)times of the expanded event
    :rtyped list(tuple(datetime, datetime))
    """
    # we do this now and than never care about the "real" end time again
    if 'DURATION' in vevent:
        duration = vevent['DURATION'].dt
    else:
        duration = vevent['DTEND'].dt - vevent['DTSTART'].dt

    # dateutil.rrule converts everything to datetime
    allday = not isinstance(vevent['DTSTART'].dt, datetime)

    # icalendar did not understand the defined timezone
    if (not allday and 'TZID' in vevent['DTSTART'].params and
            vevent['DTSTART'].dt.tzinfo is None):
        vevent['DTSTART'].dt = default_tz.localize(vevent['DTSTART'].dt)

    if 'RRULE' not in vevent.keys():
        return [(vevent['DTSTART'].dt, vevent['DTSTART'].dt + duration)]

    events_tz = None
    if getattr(vevent['DTSTART'].dt, 'tzinfo', False):
        # dst causes problem while expanding the rrule, therefor we transform
        # everything to naive datetime objects and tranform back after
        # expanding
        events_tz = vevent['DTSTART'].dt.tzinfo
        vevent['DTSTART'].dt = vevent['DTSTART'].dt.replace(tzinfo=None)

    rrulestr = vevent['RRULE'].to_ical()
    rrule = dateutil.rrule.rrulestr(rrulestr, dtstart=vevent['DTSTART'].dt)

    if not set(['UNTIL', 'COUNT']).intersection(vevent['RRULE'].keys()):
        # rrule really doesn't like to calculate all recurrences until
        # eternity, so we only do it 15 years into the future
        dtstart = vevent['DTSTART'].dt
        if isinstance(dtstart, date):
            dtstart = datetime(*list(dtstart.timetuple())[:-3])
        rrule._until = dtstart + timedelta(days=15 * 365)

    if getattr(rrule._until, 'tzinfo', False):
        rrule._until = rrule._until.astimezone(events_tz)
        rrule._until = rrule._until.replace(tzinfo=None)

    logger.debug('calculating recurrence dates for {0}, '
                 'this might take some time.'.format(href))
    dtstartl = list(rrule)

    if len(dtstartl) == 0:
        raise UnsupportedRecursion

    if events_tz is not None:
        dtstartl = [events_tz.localize(start) for start in dtstartl]
    elif allday:
        dtstartl = [start.date() for start in dtstartl]

    dtstartend = [(start, start + duration) for start in dtstartl]
    return dtstartend

########NEW FILE########
__FILENAME__ = event
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""this module will the event model, hopefully soon in a cleaned up version"""

import datetime

import icalendar

from ..compat import unicode_type, bytes_type


class Event(object):

    """the base event class"""

    def __init__(self, ical, account, href=None, local_tz=None,
                 default_tz=None, start=None, end=None, color=None,
                 readonly=False, unicode_symbols=True, etag=None):
        """
        :param ical: the icalendar VEVENT this event is based on
        :type ical: str or icalendar.cal.EVent
        :param account: the account/calendar this event belongs to
        :type account: str
        :param href: the href of the event, treated like a UID
        :type href: str
        :param local_tz: the local timezone the user wants event's times
                         displayed in
        :type local_tz: datetime.tzinfo
        :param default_tz: the timezone used if the start and end time
                           of the event have no timezone information
                           (or none that icalendar understands)
        :type default_tz: datetime.tzinfo
        :param start: start date[time] of this event, this will override the
                      start date from the vevent. This is useful for recurring
                      events, since we only save the original event once and
                      that original events start and end times might not be
                      *this* event's start and end time.
        :type start: datetime.date or datetime.datetime
        :param end: see :param start:
        :type end: datetime.date or datetime.datetime
        :param color: the color this event should be shown in ikhal and khal,
                      Supported color names are :
                      black, white, brown, yellow, dark grey, dark green,
                      dark blue, light grey, light green, light blue,
                      dark magenta, dark cyan, dark red, light magenta,
                      light cyan, light red
        :type color: str
        :param readonly: flag to show if this event may be modified or not
        :type readonly: bool
        :param unicode_symbols: some terminal fonts to not support fancey
                                unicode symbols, if set to False pure ascii
                                alternatives will be shown
        :type unicode_symbols: bool
        :param etag: the event's etag, will not be modified
        :type etag: str
        """
        if isinstance(ical, unicode_type):
            self.vevent = icalendar.Event.from_ical(ical)
        elif isinstance(ical, bytes_type):
            self.vevent = icalendar.Event.from_ical(ical.decode('utf-8'))
        elif isinstance(ical, icalendar.cal.Event):
            self.vevent = ical
        else:
            raise ValueError

        self.allday = True
        self.color = color

        if href is None:
            uid = self.vevent['UID']
            href = uid + '.ics'

        # if uid is None and self.vevent.get('UID', '') == '':

        self.account = account
        self.readonly = readonly
        self.unicode_symbols = unicode_symbols
        self.etag = etag
        self.href = href

        if unicode_symbols:
            self.recurstr = u' \N{Clockwise gapped circle arrow}'
            self.rangestr = u'\N{Left right arrow} '
            self.rangestopstr = u'\N{Rightwards arrow to bar} '
            self.rangestartstr = u'\N{Rightwards arrow from bar} '
        else:
            self.recurstr = u' R'
            self.rangestr = u' <->'
            self.rangestopstr = u' ->|'
            self.rangestartstr = u' |->'

        if start is not None:
            if isinstance(self.vevent['dtstart'].dt, datetime.datetime):
                self.allday = False  # TODO detect allday even if start is None
                start = start.astimezone(local_tz)
                end = end.astimezone(local_tz)
            self.vevent['DTSTART'].dt = start
        if start is not None:
            if 'DTEND' in self.vevent.keys():
                self.vevent['DTEND'].dt = end
        self.local_tz = local_tz
        self.default_tz = default_tz

    @property
    def uid(self):
        return self.vevent['UID']

    @property
    def ident(self):
        return self.vevent['UID']

    # @uid.setter
    # def uid(self, value):
    #     self.vevent['UID'] = value

    @property
    def start(self):
        start = self.vevent['DTSTART'].dt
        if self.allday:
            return start
        if start.tzinfo is None:
            start = self.default_tz.localize(start)
        start = start.astimezone(self.local_tz)
        return start

    @property
    def end(self):
        # TODO take care of events with neither DTEND nor DURATION
        try:
            end = self.vevent['DTEND'].dt
        except KeyError:
            duration = self.vevent['DURATION']
            end = self.start + duration.dt
        if self.allday:
            return end
        if end.tzinfo is None:
            end = self.default_tz.localize(end)
        end = end.astimezone(self.local_tz)
        return end

    @property
    def summary(self):
        return self.vevent['SUMMARY']

    @property
    def recur(self):
        return 'RRULE' in self.vevent.keys()

    @property
    def raw(self):
        return self.to_ical().decode('utf-8')

    def to_ical(self):
        calendar = self._create_calendar()
        if hasattr(self.start, 'tzinfo'):
            tzs = [self.start.tzinfo]
            if self.end.tzinfo != self.start.tzinfo:
                tzs.append(self.end.tzinfo)
            for tzinfo in tzs:
                timezone = self._create_timezone(tzinfo)
                calendar.add_component(timezone)

        calendar.add_component(self.vevent)
        return calendar.to_ical()

    def compact(self, day, timeformat='%H:%M'):
        if self.allday:
            compact = self._compact_allday(day)
        else:
            compact = self._compact_datetime(day, timeformat)
        return compact

    def _compact_allday(self, day):
        if 'RRULE' in self.vevent.keys():
            recurstr = self.recurstr
        else:
            recurstr = ''
        if self.start < day and self.end > day + datetime.timedelta(days=1):
            # event started in the past and goes on longer than today:
            rangestr = self.rangestr
            pass
        elif self.start < day:
            # event started in past
            rangestr = self.rangestopstr
            pass

        elif self.end > day + datetime.timedelta(days=1):
            # event goes on longer than today
            rangestr = self.rangestartstr
        else:
            rangestr = ''
        return rangestr + self.summary + recurstr

    def _compact_datetime(self, day, timeformat='%M:%H'):
        """compact description of this event

        TODO: explain day param

        :param day:
        :type day: datetime.date

        :return: compact description of Event
        :rtype: unicode()
        """
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)
        local_start = self.local_tz.localize(start)
        local_end = self.local_tz.localize(end)
        if 'RRULE' in self.vevent.keys():
            recurstr = self.recurstr
        else:
            recurstr = ''
        tostr = '-'
        if self.start < local_start:
            startstr = u'→ '
            tostr = ''
        else:
            startstr = self.start.strftime(timeformat)
        if self.end > local_end:
            endstr = u' → '
            tostr = ''
        else:
            endstr = self.end.strftime(timeformat)

        return startstr + tostr + endstr + ': ' + self.summary + recurstr

    def _create_calendar(self):
        """
        create the calendar

        :returns: calendar
        :rtype: icalendar.Calendar()
        """
        calendar = icalendar.Calendar()
        calendar.add('version', '2.0')
        calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')

        return calendar

    def _create_timezone(self, tz):
        """
        create an icalendar timezone from a pytz.tzinfo

        :param tz: the timezone
        :type tz: pytz.tzinfo
        :returns: timezone information set
        :rtype: icalendar.Timezone()
        """
        timezone = icalendar.Timezone()
        timezone.add('TZID', tz)

        # FIXME should match year of the event, not this year
        this_year = datetime.datetime.today().year
        daylight, standard = [(num, dt) for num, dt
                              in enumerate(tz._utc_transition_times)
                              if dt.year == this_year]

        timezone_daylight = icalendar.TimezoneDaylight()
        timezone_daylight.add('TZNAME', tz._transition_info[daylight[0]][2])
        timezone_daylight.add('DTSTART', daylight[1])
        timezone_daylight.add(
            'TZOFFSETFROM', tz._transition_info[daylight[0]][0])
        timezone_daylight.add(
            'TZOFFSETTO', tz._transition_info[standard[0]][0])

        timezone_standard = icalendar.TimezoneStandard()
        timezone_standard.add('TZNAME', tz._transition_info[standard[0]][2])
        timezone_standard.add('DTSTART', standard[1])
        timezone_standard.add(
            'TZOFFSETFROM', tz._transition_info[standard[0]][0])
        timezone_standard.add(
            'TZOFFSETTO', tz._transition_info[daylight[0]][0])

        timezone.add_component(timezone_daylight)
        timezone.add_component(timezone_standard)

        return timezone

########NEW FILE########
__FILENAME__ = khalendar
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""
khalendar.Calendar and CalendarCollection should be a nice, abstract interface
to a calendar (collection). Calendar operates on vdirs but uses an sqlite db
for caching (see backend if you're interested).

If you want to see how the sausage is made:
    Welcome to the sausage factory!
"""
import os
import os.path
import traceback

from vdirsyncer.storage import FilesystemStorage

from . import backend
from .event import Event
from .. import log

logger = log.logger


class BaseCalendar(object):

    """base class for Calendar and CalendarCollection"""

    def get_by_time_range(self, start, end):
        raise NotImplementedError

    def get_allday_by_time_range(self, start, end):
        raise NotImplementedError

    def get_datetime_by_time_range(self, start, end):
        raise NotImplementedError

    def sync(self):
        raise NotImplementedError


class Calendar(object):

    def __init__(self, name, dbpath, path, readonly=False, color='',
                 unicode_symbols=True, default_tz=None,
                 local_tz=None, debug=True):

        self._default_tz = default_tz
        self._local_tz = default_tz if local_tz is None else local_tz
        self.name = name
        self.color = color
        self.path = path
        self._debug = debug
        self._dbtool = backend.SQLiteDb(
            dbpath,
            default_tz=self._default_tz,
            local_tz=self._local_tz,
            debug=self._debug)
        self._storage = FilesystemStorage(path, '.ics')
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols

        if self._db_needs_update():
            self.db_update()

    def local_ctag(self):
        return os.path.getmtime(self.path)

    def get_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(start,
                                           end,
                                           self.name,
                                           self.color,
                                           self._readonly,
                                           self._unicode_symbols,
                                           show_deleted)

    def get_allday_by_time_range(self, start, end=None, show_deleted=False):
        return self._dbtool.get_allday_range(
            start, end, self.name, self.color, self._readonly,
            self._unicode_symbols, show_deleted)

    def get_datetime_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(
            start, end, self.name, self.color, self._readonly,
            self._unicode_symbols, show_deleted)

    def get_event(self, href):
        return self._dbtool.get_vevent_from_db(
            href, self.name, color=self.color, readonly=self._readonly,
            unicode_symbols=self._unicode_symbols)

    def update(self, event):
        """update an event in the database

        param event: the event that should be updated
        type event: event.Event
        """
        if event.etag is None:
            self.new(event)
        else:
            try:
                self._storage.update(event.href, event, event.etag)
                self._dbtool.update(event.vevent.to_ical(),
                                    self.name,
                                    event.href,
                                    etag=event.etag)
            except Exception as error:
                logger.error('Failed to parse vcard {} from collection {} '
                             'during update'.format(event.href, self.name))
                logger.debug(traceback.format_exc(error))

    def new(self, event):
        """save a new event to the database

        param event: the event that should be updated
        type event: event.Event
        """
        href, etag = self._storage.upload(event)
        event.href = href
        event.etag = etag
        try:
            self._dbtool.update(event.to_ical(),
                                self.name,
                                href=href,
                                etag=etag)
            self._dbtool.set_ctag(self.name, self.local_ctag())
        except Exception as error:
            logger.error(
                'Failed to parse vcard {} during new in collection '
                '{}'.format(event.href, self.name))
            logger.debug(traceback.format_exc(error))

    def delete(self, event):
        """delete event from this collection
        """
        self._storage.delete(event.href, event.etag)
        self._dbtool.delete(event.href, event.account)

    def _db_needs_update(self):
        if self.local_ctag() == self._dbtool.get_ctag(self.name):
            return False
        else:
            return True

    def db_update(self):
        """update the db from the vdir,

        should be called after every change to the vdir
        """
        status = True
        for href, etag in self._storage.list():
            if etag != self._dbtool.get_etag(href, self.name):
                status = status and self.update_vevent(href)
        if status:
            self._dbtool.set_ctag(self.name, self.local_ctag())

    def update_vevent(self, href):
        event, etag = self._storage.get(href)
        try:
            self._dbtool.update(event.raw, self.name, href=href, etag=etag,
                                ignore_invalid_items=True)
            return True
        except Exception as error:
            logger.error(
                'Failed to parse vcard {} during '
                'update_vevent in collection ''{}'.format(href, self.name))
            logger.debug(traceback.format_exc(error))
            return False

    def new_event(self, ical, local_tz, default_tz):
        """creates new event form ical string"""
        return Event(ical=ical, account=self.name, local_tz=local_tz,
                     default_tz=default_tz)


class CalendarCollection(object):

    def __init__(self):
        self._calnames = dict()
        self._default_calendar_name = None

    @property
    def calendars(self):
        return self._calnames.values()

    @property
    def names(self):
        return self._calnames.keys()

    @property
    def default_calendar_name(self):
        if self._default_calendar_name in self.names:
            return self._default_calendar_name
        else:
            return self.names[0]

    def append(self, calendar):
        self._calnames[calendar.name] = calendar
        self.calendars.append(calendar)

    def get_by_time_range(self, start, end):
        events = list()
        for one in self.calendars:
            events.extend(one.get_by_time_range(start, end))

        return events

    def get_allday_by_time_range(self, start, end=None):
        events = list()
        for one in self.calendars:
            events.extend(one.get_allday_by_time_range(start, end))
        return events

    def get_datetime_by_time_range(self, start, end):
        events = list()
        for one in self.calendars:
            events.extend(one.get_datetime_by_time_range(start, end))
        return events

    def update(self, event):
        self._calnames[event.account].update(event)

    def new(self, event, collection=None):
        if collection:
            self._calnames[collection].new(event)
        else:
            self._calnames[event.account].new(event)

    def delete(self, event):
        self._calnames[event.account].delete(event)

    def get_event(self, href, account):
        return self._calnames[account].get_event(href)

    def change_collection(self, event, new_collection):
        self._calnames[event.account].delete(event)
        self._calnames[new_collection].new(event)
        # TODO would be better to first add to new collection, then delete
        # currently not possible since new modifies event.etag

    def new_event(self, ical, collection, local_tz, default_tz):
        """returns a new event"""
        return self._calnames[collection].new_event(ical, local_tz, default_tz)

    def _db_needs_update(self):
        any([one._db_needs_update() for one in self.calendars])

    def db_update(self):
        for one in self.calendars:
            one.db_update()

########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import sys

from khal import __productname__

stdout_handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__productname__)
logger.setLevel(logging.INFO)
logger.addHandler(stdout_handler)

########NEW FILE########
__FILENAME__ = terminal
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
"""all functions related to terminal display are collected here"""

try:
    from itertools import izip_longest
except ImportError:
    from itertools import zip_longest as izip_longest

try:
    # python 3.3+
    import shutil.get_terminal_size as get_terminal_size
except ImportError:
    def get_terminal_size():
        import fcntl
        import struct
        import termios
        try:
            h, w, hp, wp = struct.unpack(
                'HHHH',
                fcntl.ioctl(0, termios.TIOCGWINSZ,
                            struct.pack('HHHH', 0, 0, 0, 0)))
        except IOError:
            w, h = 80, 24
        return w, h

RTEXT = '\x1b[7m'  # reverse
NTEXT = '\x1b[0m'  # normal
BTEXT = '\x1b[1m'  # bold
RESET = '\33[0m'
COLORS = {
    'black': '\33[30m',
    'dark red': '\33[31m',
    'dark green': '\33[32m',
    'brown': '\33[33m',
    'dark blue': '\33[34m',
    'dark magenta': '\33[35m',
    'dark cyan': '\33[36m',
    'white': '\33[37m',
    'light grey': '\33[1;37m',
    'dark grey': '\33[1;30m',
    'light red': '\33[1;31m',
    'light green': '\33[1;32m',
    'yellow': '\33[1;33m',
    'light blue': '\33[1;34m',
    'light magenta': '\33[1;35m',
    'light cyan': '\33[1;36m'
}


def rstring(string):
    """returns string as reverse color string (ANSI escape codes)

    >>> rstring('test')
    '\\x1b[7mtest\\x1b[0m'
    """
    return RTEXT + string + NTEXT


def bstring(string):
    """returns string as bold string (ANSI escape codes)
    >>> bstring('test')
    '\\x1b[1mtest\\x1b[0m'
    """
    return BTEXT + string + NTEXT


def colored(string, colorstring):
    try:
        color = COLORS[colorstring]
    except KeyError:
        color = ''
    return color + string + RESET


def merge_columns(lcolumn, rcolumn, width=25):
    """merge two lists elementwise together

    Wrap right columns to terminal width.
    If the right list(column) is longer, first lengthen the left one.
    We assume that the left column has width `width`, we cannot find
    out its (real) width automatically since it might contain ANSI
    escape sequences.
    """

    missing = len(rcolumn) - len(lcolumn)
    if missing > 0:
        lcolumn = lcolumn + missing * [width * ' ']

    rows = ['    '.join(one) for one in izip_longest(
        lcolumn, rcolumn, fillvalue='')]
    return rows

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import urwid


def vimify(key):
    if key == 'h':
        return 'left'
    elif key == 'j':
        return 'down'
    elif key == 'k':
        return 'up'
    elif key == 'l':
        return 'right'
    # not really sure if these last to make any sense (not yet at least)
    # at least for the time being, they are more trouble, than they are worth
    # elif key == '0':
        # return 'home'
    # elif key == '$':
        # return 'end'
    else:
        return key


class CColumns(urwid.Columns):

    def keypress(self, size, key):
        # key = vimify(key)
        return urwid.Columns.keypress(self, size, key)


class CPile(urwid.Pile):

    def keypress(self, size, key):
        # key = vimify(key)
        return urwid.Pile.keypress(self, size, key)


class CSimpleFocusListWalker(urwid.SimpleFocusListWalker):

    def keypress(self, size, key):
        # key = vimify(key)
        return urwid.SimpleFocusListWalker.keypress(self, size, key)


class Pane(urwid.WidgetWrap):

    """An abstract Pane to be used in a Window object."""

    def __init__(self, widget, title=None, description=None):
        self.widget = widget
        urwid.WidgetWrap.__init__(self, widget)
        self._title = title or ''
        self._description = description or ''
        self.window = None

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    def get_keys(self):
        """Return a description of the keystrokes recognized by this pane.

        This method returns a list of tuples describing the keys
        handled by a pane. This list is used to build a contextual
        pane help. Each tuple is a pair of a list of keys and a
        description.

        The abstract pane returns the default keys handled by the
        window. Panes which do not override these keys should extend
        this list.
        """
        return [(['up', 'down', 'pg.up', 'pg.down'],
                 'navigate through the fields.'),
                (['esc'], 'backtrack to the previous pane or exit.'),
                (['F1', '?'], 'open this pane help.')]


class HelpPane(Pane):

    """A contextual help screen."""

    def __init__(self, pane):
        content = []
        for key_list, description in pane.get_keys():
            key_text = []
            for key in key_list:
                if key_text:
                    key_text.append(', ')
                key_text.append(('bright', key))
            content.append(
                urwid.Columns(
                    [urwid.Padding(urwid.Text(key_text), left=10),
                     urwid.Padding(urwid.Text(description), right=10)]))

        Pane.__init__(self, urwid.ListBox(urwid.SimpleListWalker(content)),
                      'Help')


class Window(urwid.Frame):

    """The main user interface frame.

    A window is a frame which displays a header, a footer and a body.
    The header and the footer are handled by this object, and the body
    is the space where Panes can be displayed.

    Each Pane is an interface to interact with the database in one
    way: list the VCards, edit one VCard, and so on. The Window
    provides a mechanism allowing the panes to chain themselves, and
    to carry data between them.
    """
    PALETTE = [('header', 'white', 'black'),
               ('footer', 'white', 'black'),
               ('line header', 'black', 'white', 'bold'),
               ('bright', 'dark blue', 'white', ('bold', 'standout')),
               ('list', 'black', 'white'),
               ('list focused', 'white', 'light blue', 'bold'),
               ('edit', 'black', 'white'),
               ('edit focused', 'white', 'light blue', 'bold'),
               ('button', 'black', 'dark cyan'),
               ('button focused', 'white', 'light blue', 'bold'),
               ('reveal focus', 'black', 'dark cyan', 'standout'),
               ('today_focus', 'white', 'black', 'standout'),
               ('today', 'black', 'white', 'dark cyan'),
               ('edit', 'white', 'dark blue'),
               ('alert', 'white', 'dark red'),

               ('editfc', 'white', 'dark blue', 'bold'),
               ('editbx', 'light gray', 'dark blue'),
               ('editcp', 'black', 'light gray', 'standout'),
               ('popupbg', 'white', 'black', 'bold'),

               ('black', 'black', ''),
               ('dark red', 'dark red', ''),
               ('dark green', 'dark green', ''),
               ('brown', 'brown', ''),
               ('dark blue', 'dark blue', ''),
               ('dark magenta', 'dark magenta', ''),
               ('dark cyan', 'dark cyan', ''),
               ('light gray', 'light gray', ''),
               ('dark gray', 'dark gray', ''),
               ('light red', 'light red', ''),
               ('light green', 'light green', ''),
               ('yellow', 'yellow', ''),
               ('light blue', 'light blue', ''),
               ('light magenta', 'light magenta', ''),
               ('light cyan', 'light cyan', ''),
               ('white', 'white', ''),
               ]

    def __init__(self, header='', footer=''):
        self._track = []
        self._title = header
        self._footer = footer

        header = urwid.AttrWrap(urwid.Text(self._title), 'header')
        footer = urwid.AttrWrap(urwid.Text(self._footer), 'footer')
        urwid.Frame.__init__(self, urwid.Text(''),
                             header=header,
                             footer=footer)
        self._original_w = None

    def open(self, pane, callback=None):
        """Open a new pane.

        The given pane is added to the track and opened. If the given
        callback is not None, it will be called when this new pane
        will be closed.
        """
        pane.window = self
        self._track.append((pane, callback))
        self._update(pane)

    def overlay(self, overlay_w, title):
        """put overlay_w as an overlay over the currently active pane
        """
        overlay = Pane(urwid.Overlay(urwid.Filler(overlay_w),
                                     self._get_current_pane(),
                                     'center', 60,
                                     'middle', 5), title)
        self.open(overlay)

    def backtrack(self, data=None):
        """Unstack the displayed pane.

        The current pane is discarded, and the previous one is
        displayed. If the current pane was opened with a callback,
        this callback is called with the given data (if any) before
        the previous pane gets redrawn.
        """
        _, cb = self._track.pop()
        if cb:
            cb(data)

        if self._track:
            self._update(self._get_current_pane())
        else:
            raise urwid.ExitMainLoop()

    def on_key_press(self, key):
        """Handle application-wide key strokes."""
        if key in ['esc', 'q']:
            self.backtrack()
        elif key in ['f1', '?']:
            self.open(HelpPane(self._get_current_pane()))

    def _update(self, pane):
        self.header.w.set_text(u'%s | %s' % (self._title, pane.title))
        self.set_body(pane)

    def _get_current_pane(self):
        return self._track[-1][0] if self._track else None

########NEW FILE########
__FILENAME__ = startendeditor
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime

import urwid

from .base import CColumns, CPile
from .widgets import DateWidget, TimeWidget


class DateConversionError(Exception):
    pass


class StartEnd(object):
    # TODO convert to namespace
    def __init__(self, startdate, starttime, enddate, endtime):
        """collecting some common properties"""
        self.startdate = startdate
        self.starttime = starttime
        self.enddate = enddate
        self.endtime = endtime


class StartEndEditor(urwid.WidgetWrap):

    """
    editing start and nd times of the event

    we cannot change timezones ATM  # TODO
    pop up on strings not matching timeformat # TODO
    """

    def __init__(self, start, end, conf):
        self.allday = False
        if not isinstance(start, datetime):
            self.allday = True

        self.conf = conf
        self.startdt = start
        self.enddt = end
        self.dts = StartEnd(
            startdate=start.strftime(self.conf.locale.longdateformat),
            starttime=start.strftime(self.conf.locale.timeformat),
            enddate=end.strftime(self.conf.locale.longdateformat),
            endtime=end.strftime(self.conf.locale.timeformat))
        # this will contain the widgets for [start|end] [date|time]
        self.widgets = StartEnd(None, None, None, None)
        # and these are their background colors
        self.bgs = StartEnd('edit', 'edit', 'edit', 'edit')

        self.checkallday = urwid.CheckBox('Allday', state=self.allday,
                                          on_state_change=self.toggle)
        self.toggle(None, self.allday)

    def toggle(self, checkbox, state):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: state the event will toggle to;
                      True if allday event, False if datetime
        :type state: bool
        """
        self.allday = state

        datewidth = len(self.dts.startdate) + 7

        edit = DateWidget(
            self.conf.locale.longdateformat,
            caption=('', 'From: '), edit_text=self.dts.startdate)
        edit = urwid.AttrMap(edit, self.bgs.startdate, 'editcp', )
        edit = urwid.Padding(
            edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.startdate = edit

        edit = DateWidget(
            self.conf.locale.longdateformat,
            caption=('', 'To:   '), edit_text=self.dts.enddate)
        edit = urwid.AttrMap(edit, self.bgs.enddate, 'editcp', )
        edit = urwid.Padding(
            edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.enddate = edit
        if state is True:
            timewidth = 1
            self.widgets.starttime = urwid.Text('')
            self.widgets.endtime = urwid.Text('')
        elif state is False:
            timewidth = len(self.dts.starttime) + 1
            edit = TimeWidget(
                self.conf.locale.timeformat,
                edit_text=self.dts.starttime)
            edit = urwid.AttrMap(edit, self.bgs.starttime, 'editcp', )
            edit = urwid.Padding(
                edit, align='left', width=len(self.dts.starttime) + 1, left=1)
            self.widgets.starttime = edit

            edit = TimeWidget(
                self.conf.locale.timeformat,
                edit_text=self.dts.endtime)
            edit = urwid.AttrMap(edit, self.bgs.endtime, 'editcp', )
            edit = urwid.Padding(
                edit, align='left', width=len(self.dts.endtime) + 1, left=1)
            self.widgets.endtime = edit

        columns = CPile([
            CColumns([(datewidth, self.widgets.startdate), (
                timewidth, self.widgets.starttime)], dividechars=1),
            CColumns(
                [(datewidth, self.widgets.enddate),
                 (timewidth, self.widgets.endtime)],
                dividechars=1),
            self.checkallday
            ], focus_item=2)
        urwid.WidgetWrap.__init__(self, columns)

    @property
    def changed(self):
        """
        returns True if content has been edited, False otherwise
        """
        return ((self.startdt != self.newstart) or
                (self.enddt != self.newend))

    @property
    def newstart(self):
        newstartdatetime = self._newstartdate
        if not self.checkallday.state:
            if getattr(self.startdt, 'tzinfo', None) is None:
                tzinfo = self.conf.locale.default_timezone
            else:
                tzinfo = self.startdt.tzinfo
            try:
                newstarttime = self._newstarttime
                newstartdatetime = datetime.combine(
                    newstartdatetime, newstarttime)
                newstartdatetime = tzinfo.localize(newstartdatetime)
            except TypeError:
                return None
        return newstartdatetime

    @property
    def _newstartdate(self):
        try:
            self.dts.startdate = \
                self.widgets.startdate. \
                original_widget.original_widget.get_edit_text()

            newstartdate = datetime.strptime(
                self.dts.startdate,
                self.conf.locale.longdateformat).date()
            self.bgs.startdate = 'edit'
            return newstartdate
        except ValueError:
            self.bgs.startdate = 'alert'
            return None

    @property
    def _newstarttime(self):
        try:
            self.dts.starttime = \
                self.widgets.starttime. \
                original_widget.original_widget.get_edit_text()

            newstarttime = datetime.strptime(
                self.dts.starttime,
                self.conf.locale.timeformat).time()
            self.bgs.startime = 'edit'
            return newstarttime
        except ValueError:
            self.bgs.starttime = 'alert'
            return None

    @property
    def newend(self):
        newenddatetime = self._newenddate
        if not self.checkallday.state:
            if not hasattr(self.enddt, 'tzinfo') or self.enddt.tzinfo is None:
                tzinfo = self.conf.locale.default_timezone
            else:
                tzinfo = self.enddt.tzinfo
            try:
                newendtime = self._newendtime
                newenddatetime = datetime.combine(newenddatetime, newendtime)
                newenddatetime = tzinfo.localize(newenddatetime)
            except TypeError:
                return None
        return newenddatetime

    @property
    def _newenddate(self):
        try:
            self.dts.enddate = self.widgets.enddate. \
                original_widget.original_widget.get_edit_text()

            newenddate = datetime.strptime(
                self.dts.enddate,
                self.conf.locale.longdateformat).date()
            self.bgs.enddate = 'edit'
            return newenddate
        except ValueError:
            self.bgs.enddate = 'alert'
            return None

    @property
    def _newendtime(self):
        try:
            self.endtime = self.widgets.endtime. \
                original_widget.original_widget.get_edit_text()

            newendtime = datetime.strptime(
                self.endtime,
                self.conf.locale.timeformat).time()
            self.bgs.endtime = 'edit'
            return newendtime
        except ValueError:
            self.bgs.endtime = 'alert'
            return None

########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import datetime
from datetime import timedelta

import urwid


class DateTimeWidget(urwid.Edit):
    def __init__(self, dateformat, **kwargs):
        self.dateformat = dateformat
        super(DateTimeWidget, self).__init__(wrap='any', **kwargs)

    def keypress(self, size, key):
        if key == 'ctrl x':
            self.decrease()
        elif key == 'ctrl a':
            self.increase()
        else:
            return super(DateTimeWidget, self).keypress(size, key)

    def _get_dt(self):
        date = self.get_edit_text()
        return datetime.datetime.strptime(date, self.dateformat)

    def increase(self):
        try:
            date = self._get_dt() + self.timedelta
            self.set_edit_text(date.strftime(self.dateformat))
        except ValueError:
            pass

    def decrease(self):
        try:
            date = self._get_dt() - self.timedelta
            self.set_edit_text(date.strftime(self.dateformat))
        except ValueError:
            pass


class DateWidget(DateTimeWidget):
    timedelta = timedelta(days=1)


class TimeWidget(DateTimeWidget):
    timedelta = timedelta(minutes=15)

########NEW FILE########
__FILENAME__ = cal_display_test
import datetime

import pytest

from khal.calendar_display import vertical_month, getweeknumber, str_week


today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)


def test_getweeknumber():
    assert getweeknumber(datetime.date(2011,12,12)) == 50
    assert getweeknumber(datetime.date(2011,12,31)) == 52
    assert getweeknumber(datetime.date(2012,1,1)) == 52
    assert getweeknumber(datetime.date(2012,1,2)) == 1


def test_str_week():
    aday = datetime.date(2012, 6, 1)
    bday = datetime.date(2012, 6, 8)
    week = [datetime.date(2012, 6, 6),
            datetime.date(2012, 6, 7),
            datetime.date(2012, 6, 8),
            datetime.date(2012, 6, 9),
            datetime.date(2012, 6, 10),
            datetime.date(2012, 6, 11),
            datetime.date(2012, 6, 12),
            datetime.date(2012, 6, 13)]
    assert str_week(week, aday) == ' 6  7  8  9 10 11 12 13 '
    assert str_week(week, bday) == ' 6  7 \x1b[7m 8\x1b[0m  9 10 11 12 13 '



example1 =  [
    '\x1b[1m    Mo Tu We Th Fr Sa Su \x1b[0m',
    '\x1b[1mDec \x1b[0m28 29 30  1  2  3  4 ',
    '     5  6  7  8  9 10 11 ',
    '    \x1b[7m12\x1b[0m 13 14 15 16 17 18 ',
    '    19 20 21 22 23 24 25 ',
    '\x1b[1mJan \x1b[0m26 27 28 29 30 31  1 ',
    '     2  3  4  5  6  7  8 ',
    '     9 10 11 12 13 14 15 ',
    '    16 17 18 19 20 21 22 ',
    '    23 24 25 26 27 28 29 ',
    '\x1b[1mFeb \x1b[0m30 31  1  2  3  4  5 ',
    '     6  7  8  9 10 11 12 ',
    '    13 14 15 16 17 18 19 ',
    '    20 21 22 23 24 25 26 ',
    '\x1b[1mMar \x1b[0m27 28 29  1  2  3  4 ']

example_weno = [
    '\x1b[1m    Mo Tu We Th Fr Sa Su     \x1b[0m',
    '\x1b[1mDec \x1b[0m28 29 30  1  2  3  4 \x1b[1m 48\x1b[0m',
    '     5  6  7  8  9 10 11 \x1b[1m 49\x1b[0m',
    '    \x1b[7m12\x1b[0m 13 14 15 16 17 18 \x1b[1m 50\x1b[0m',
    '    19 20 21 22 23 24 25 \x1b[1m 51\x1b[0m',
    '\x1b[1mJan \x1b[0m26 27 28 29 30 31  1 \x1b[1m 52\x1b[0m',
    '     2  3  4  5  6  7  8 \x1b[1m 1\x1b[0m',
    '     9 10 11 12 13 14 15 \x1b[1m 2\x1b[0m',
    '    16 17 18 19 20 21 22 \x1b[1m 3\x1b[0m',
    '    23 24 25 26 27 28 29 \x1b[1m 4\x1b[0m',
    '\x1b[1mFeb \x1b[0m30 31  1  2  3  4  5 \x1b[1m 5\x1b[0m',
    '     6  7  8  9 10 11 12 \x1b[1m 6\x1b[0m',
    '    13 14 15 16 17 18 19 \x1b[1m 7\x1b[0m',
    '    20 21 22 23 24 25 26 \x1b[1m 8\x1b[0m',
    '\x1b[1mMar \x1b[0m27 28 29  1  2  3  4 \x1b[1m 9\x1b[0m']

example_we_start_su = [
    '\x1b[1m    Su Mo Tu We Th Fr Sa \x1b[0m',
    '\x1b[1mDec \x1b[0m27 28 29 30  1  2  3 ',
    '     4  5  6  7  8  9 10 ',
    '    11 \x1b[7m12\x1b[0m 13 14 15 16 17 ',
    '    18 19 20 21 22 23 24 ',
    '    25 26 27 28 29 30 31 ',
    '\x1b[1mJan \x1b[0m 1  2  3  4  5  6  7 ',
    '     8  9 10 11 12 13 14 ',
    '    15 16 17 18 19 20 21 ',
    '    22 23 24 25 26 27 28 ',
    '\x1b[1mFeb \x1b[0m29 30 31  1  2  3  4 ',
    '     5  6  7  8  9 10 11 ',
    '    12 13 14 15 16 17 18 ',
    '    19 20 21 22 23 24 25 ',
    '\x1b[1mMar \x1b[0m26 27 28 29  1  2  3 ']



def test_vertical_month():
    vert_str = vertical_month(month=12, year=2011,
                              today=datetime.date(2011, 12, 12))
    assert vert_str == example1

    weno_str = vertical_month(month=12, year=2011,
                              today=datetime.date(2011, 12, 12),
                              weeknumber=True)
    assert weno_str == example_weno


    we_start_su_str = vertical_month(
        month=12, year=2011,
        today=datetime.date(2011, 12, 12),
        firstweekday=6)
    assert we_start_su_str == example_we_start_su

########NEW FILE########
__FILENAME__ = cli_test
import pytz

from khal.cli import ConfigParser
from khal.cli import Namespace

str_calendars_good = """
[Calendar home]
path = /home/user/somewhere
color = dark blue

[Calendar work]
path = /home/user/somewhereelse
color = dark green
readonly = 0

[Calendar workagain]
path = /home/user/here
readonly = True
"""

str_sqlite_good = """
[sqlite]
path = /home/user/.khal/khal.db
"""

str_locale_good = """
[locale]
local_timezone: Europe/Berlin
default_timezone: America/New_York

timeformat: %H:%M
dateformat: %d.%m.
longdateformat: %d.%m.%Y
datetimeformat: %d.%m. %H:%M
longdatetimeformat: %d.%m.%Y %H:%M

firstweekday: 0
"""

str_default_good = """
[default]
default_command: calendar
debug: 0
"""


goodlocale = Namespace(
    {'dateformat': '%d.%m.',
     'local_timezone': pytz.timezone('Europe/Berlin'),
     'unicode_symbols': True,
     'longdateformat': '%d.%m.%Y',
     'longdatetimeformat': '%d.%m.%Y %H:%M',
     'default_timezone': pytz.timezone('America/New_York'),
     'encoding': 'utf-8',
     'timeformat': '%H:%M',
     'datetimeformat': '%d.%m. %H:%M',
     'firstweekday': 0
     }
)

gooddefault = Namespace(
    {'default_command': 'calendar',
     'debug': 0,
     'default_calendar': True,

     }
)

goodsqlite = Namespace(
    {'path': '/home/user/.khal/khal.db'
     }
)

goodcalendars = [
    Namespace({
        'name': 'home',
        'path': '/home/user/somewhere',
        'color': 'dark blue',
        'readonly': False
    }),
    Namespace({
        'name': 'work',
        'path': '/home/user/somewhereelse',
        'color': 'dark green',
        'readonly': False
    }),

    Namespace({
        'name': 'workagain',
        'path': '/home/user/here',
        'color': '',
        'readonly': True
    })
]


class TestConfigParser(object):
    def test_easy(self, tmpdir):
        goodconf = Namespace(
            {'locale': goodlocale,
             'sqlite': goodsqlite,
             'default': gooddefault,
             'calendars': goodcalendars
             }
        )

        basic_config = (str_calendars_good +
                        str_locale_good +
                        str_sqlite_good +
                        str_default_good)
        tmpdir.join('config').write(basic_config)
        conf_parser = ConfigParser()
        config = conf_parser.parse_config(str(tmpdir) + '/config')
        assert config == goodconf

    def test_no_cal(self, tmpdir, caplog):
        no_cal_config = (str_locale_good +
                         str_sqlite_good +
                         str_default_good)
        tmpdir.join('config').write(no_cal_config)
        conf_parser = ConfigParser()
        config = conf_parser.parse_config(str(tmpdir) + '/config')
        assert "Missing required section 'calendars'" in caplog.text()
        assert config is None

########NEW FILE########
__FILENAME__ = datetimehelper_test
import datetime
import icalendar

import pytest
import pytz

from khal.khalendar import datetimehelper

# datetime
event_dt = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T140000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
UID:datetime123
END:VEVENT
END:VCALENDAR"""

event_dt_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T140000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T160000
UID:datetime123
END:VEVENT
END:VCALENDAR"""

# datetime zulu (in utc time)
event_dttz = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Zulu Event
DTSTART;VALUE=DATE-TIME:20130301T140000Z
DTEND;VALUE=DATE-TIME:20130301T160000Z
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
UID:datetimezulu123
END:VEVENT
END:VCALENDAR"""

event_dttz_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Zulu Event
DTSTART;VALUE=DATE-TIME:20130301T140000Z
DTEND;VALUE=DATE-TIME:20130301T160000Z
UID:datetimezulu123
END:VEVENT
END:VCALENDAR"""

# datetime floating (no time zone information)
event_dtf = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime floating Event
DTSTART;VALUE=DATE-TIME:20130301T140000
DTEND;VALUE=DATE-TIME:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
UID:datetimefloating123
END:VEVENT
END:VCALENDAR"""

event_dtf_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime floating Event
DTSTART;VALUE=DATE-TIME:20130301T140000
DTEND;VALUE=DATE-TIME:20130301T160000
UID:datetimefloating123
END:VEVENT
END:VCALENDAR"""

# datetime broken (as in we don't understand the timezone information)
event_dtb = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VTIMEZONE
TZID:/freeassociation.sourceforge.net/Tzfile/Europe/Berlin
X-LIC-LOCATION:Europe/Berlin
BEGIN:STANDARD
TZNAME:CET
DTSTART:19701027T030000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:STANDARD
BEGIN:DAYLIGHT
TZNAME:CEST
DTSTART:19700331T020000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:broken123
DTSTART;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T140000
DTEND;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
TRANSP:OPAQUE
SEQUENCE:2
SUMMARY:Broken Event
END:VEVENT
END:VCALENDAR
"""

event_dtb_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VTIMEZONE
TZID:/freeassociation.sourceforge.net/Tzfile/Europe/Berlin
X-LIC-LOCATION:Europe/Berlin
BEGIN:STANDARD
TZNAME:CET
DTSTART:19701027T030000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:STANDARD
BEGIN:DAYLIGHT
TZNAME:CEST
DTSTART:19700331T020000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:broken123
DTSTART;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T140000
DTEND;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T160000
TRANSP:OPAQUE
SEQUENCE:2
SUMMARY:Broken Event
END:VEVENT
END:VCALENDAR
"""

# all day (date) event
event_d = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
UID:date123
DTSTART;VALUE=DATE:20130301
DTEND;VALUE=DATE:20130302
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
SUMMARY:Event
END:VEVENT
END:VCALENDAR
"""

# all day (date) event with timezone information
event_dtz = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
UID:datetz123
DTSTART;TZID=Berlin/Europe;VALUE=DATE:20130301
DTEND;TZID=Berlin/Europe;VALUE=DATE:20130302
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
SUMMARY:Event
END:VEVENT
END:VCALENDAR
"""

event_dtzb = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VTIMEZONE
TZID:Pacific Time (US & Canada), Tijuana
BEGIN:STANDARD
DTSTART:20071104T020000
TZOFFSETTO:-0800
TZOFFSETFROM:-0700
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:20070311T020000
TZOFFSETTO:-0700
TZOFFSETFROM:-0800
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
DTSTART;VALUE=DATE;TZID="Pacific Time (US & Canada), Tijuana":20130301
DTEND;VALUE=DATE;TZID="Pacific Time (US & Canada), Tijuana":20130302
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
SUMMARY:Event
UID:eventdtzb123
END:VEVENT
END:VCALENDAR
"""

event_d_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
UID:date123
DTSTART;VALUE=DATE:20130301
DTEND;VALUE=DATE:20130302
SUMMARY:Event
END:VEVENT
END:VCALENDAR
"""
berlin = pytz.timezone('Europe/Berlin')


def _get_vevent(event):
    ical = icalendar.Event.from_ical(event)
    for component in ical.walk():
        if component.name == 'VEVENT':
            return component


class TestExpand(object):
    dtstartend_berlin = [
        (berlin.localize(datetime.datetime(2013, 3, 1, 14, 0, )),
         berlin.localize(datetime.datetime(2013, 3, 1, 16, 0, ))),
        (berlin.localize(datetime.datetime(2013, 5, 1, 14, 0, )),
         berlin.localize(datetime.datetime(2013, 5, 1, 16, 0, ))),
        (berlin.localize(datetime.datetime(2013, 7, 1, 14, 0, )),
         berlin.localize(datetime.datetime(2013, 7, 1, 16, 0, ))),
        (berlin.localize(datetime.datetime(2013, 9, 1, 14, 0, )),
         berlin.localize(datetime.datetime(2013, 9, 1, 16, 0, ))),
        (berlin.localize(datetime.datetime(2013, 11, 1, 14, 0,)),
         berlin.localize(datetime.datetime(2013, 11, 1, 16, 0,))),
        (berlin.localize(datetime.datetime(2014, 1, 1, 14, 0, )),
         berlin.localize(datetime.datetime(2014, 1, 1, 16, 0, )))
    ]

    dtstartend_utc = [
        (datetime.datetime(2013, 3, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 3, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 5, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 5, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 7, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 7, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 9, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 9, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 11, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 11, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2014, 1, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2014, 1, 1, 16, 0, tzinfo=pytz.utc))
    ]

    dtstartend_float = [
        (datetime.datetime(2013, 3, 1, 14, 0),
         datetime.datetime(2013, 3, 1, 16, 0)),
        (datetime.datetime(2013, 5, 1, 14, 0),
         datetime.datetime(2013, 5, 1, 16, 0)),
        (datetime.datetime(2013, 7, 1, 14, 0),
         datetime.datetime(2013, 7, 1, 16, 0)),
        (datetime.datetime(2013, 9, 1, 14, 0),
         datetime.datetime(2013, 9, 1, 16, 0)),
        (datetime.datetime(2013, 11, 1, 14, 0),
         datetime.datetime(2013, 11, 1, 16, 0)),
        (datetime.datetime(2014, 1, 1, 14, 0),
         datetime.datetime(2014, 1, 1, 16, 0))
    ]
    dstartend = [
        (datetime.date(2013, 3, 1,),
         datetime.date(2013, 3, 2,)),
        (datetime.date(2013, 5, 1,),
         datetime.date(2013, 5, 2,)),
        (datetime.date(2013, 7, 1,),
         datetime.date(2013, 7, 2,)),
        (datetime.date(2013, 9, 1,),
         datetime.date(2013, 9, 2,)),
        (datetime.date(2013, 11, 1),
         datetime.date(2013, 11, 2)),
        (datetime.date(2014, 1, 1,),
         datetime.date(2014, 1, 2,))
    ]
    offset_berlin = [
        datetime.timedelta(0, 3600),
        datetime.timedelta(0, 7200),
        datetime.timedelta(0, 7200),
        datetime.timedelta(0, 7200),
        datetime.timedelta(0, 3600),
        datetime.timedelta(0, 3600)
    ]

    offset_utc = [
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
    ]

    offset_none = [None, None, None, None, None, None]

    def test_expand_dt(self):
        vevent = _get_vevent(event_dt)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dtb(self):
        vevent = _get_vevent(event_dtb)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dttz(self):
        vevent = _get_vevent(event_dttz)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_utc
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_utc
        assert [end.utcoffset() for _, end in dtstart] == self.offset_utc

    def test_expand_dtf(self):
        vevent = _get_vevent(event_dtf)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_float
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_none
        assert [end.utcoffset() for _, end in dtstart] == self.offset_none

    def test_expand_d(self):
        vevent = _get_vevent(event_d)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_dtz(self):
        vevent = _get_vevent(event_dtz)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_dtzb(self):
        vevent = _get_vevent(event_dtzb)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dstartend


class TestExpandNoRR(object):
    dtstartend_berlin = [
        (berlin.localize(datetime.datetime(2013, 3, 1, 14, 0)),
         berlin.localize(datetime.datetime(2013, 3, 1, 16, 0))),
    ]

    dtstartend_utc = [
        (datetime.datetime(2013, 3, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 3, 1, 16, 0, tzinfo=pytz.utc)),
    ]

    dtstartend_float = [
        (datetime.datetime(2013, 3, 1, 14, 0),
         datetime.datetime(2013, 3, 1, 16, 0)),
    ]
    offset_berlin = [
        datetime.timedelta(0, 3600),
    ]

    offset_utc = [
        datetime.timedelta(0, 0),
    ]

    offset_none = [None]

    def test_expand_dt(self):
        vevent = _get_vevent(event_dt_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dtb(self):
        vevent = _get_vevent(event_dtb_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dttz(self):
        vevent = _get_vevent(event_dttz_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_utc
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_utc
        assert [end.utcoffset() for _, end in dtstart] == self.offset_utc

    def test_expand_dtf(self):
        vevent = _get_vevent(event_dtf_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_float
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_none
        assert [end.utcoffset() for _, end in dtstart] == self.offset_none

    def test_expand_d(self):
        vevent = _get_vevent(event_d_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == [
            (datetime.date(2013, 3, 1,),
             datetime.date(2013, 3, 2,)),
        ]


vevent_until_notz = """BEGIN:VEVENT
SUMMARY:until 20. Februar
DTSTART;TZID=Europe/Berlin:20140203T070000
DTEND;TZID=Europe/Berlin:20140203T090000
UID:until_notz
RRULE:FREQ=DAILY;UNTIL=20140220T060000Z;WKST=SU
END:VEVENT
"""

vevent_count = """BEGIN:VEVENT
SUMMARY:until 20. Februar
DTSTART:20140203T070000
DTEND:20140203T090000
UID:until_notz
RRULE:FREQ=DAILY;UNTIL=20140220;WKST=SU
END:VEVENT
"""

event_until_d_notz = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:d470ef6d08
DTSTART;VALUE=DATE:20140110
DURATION:P1D
RRULE:FREQ=WEEKLY;UNTIL=20140215;INTERVAL=1;BYDAY=FR
SUMMARY:Fri
END:VEVENT
END:VCALENDAR
"""


latest_bug = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Reformationstag
RRULE:FREQ=YEARLY;BYMONTHDAY=31;BYMONTH=10
DTSTART;VALUE=DATE:20091031
DTEND;VALUE=DATE:20091101
END:VEVENT
END:VCALENDAR
"""

another_problem = """BEGIN:VEVENT
SUMMARY:PyCologne
DTSTART;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20131113T190000
DTEND;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20131113T210000
DTSTAMP:20130610T160635Z
UID:another_problem
RECURRENCE-ID;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20131113T190000
RRULE:FREQ=MONTHLY;BYDAY=2WE;WKST=SU
TRANSP:OPAQUE
END:VEVENT
"""


class TestSpecial(object):
    @pytest.mark.xfail(reason='')
    def test_count(self):
        vevent = _get_vevent(vevent_count)
        dtstart = datetimehelper.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 18
        assert dtstart[0][0] == datetime.datetime(2014, 2, 3, 7, 0)
        assert dtstart[-1][0] == datetime.datetime(2014, 2, 20, 7, 0)

    def test_until_notz(self):
        vevent = _get_vevent(vevent_until_notz)
        dtstart = datetimehelper.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 18
        assert dtstart[0][0] == berlin.localize(
            datetime.datetime(2014, 2, 3, 7, 0))
        assert dtstart[-1][0] == berlin.localize(
            datetime.datetime(2014, 2, 20, 7, 0))

    def test_until_d_notz(self):
        vevent = _get_vevent(event_until_d_notz)
        dtstart = datetimehelper.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 6
        assert dtstart[0][0] == datetime.date(2014, 1, 10)
        assert dtstart[-1][0] == datetime.date(2014, 2, 14)

    def test_latest_bug(self):
        vevent = _get_vevent(latest_bug)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart[0][0] == datetime.date(2009, 10, 31)
        assert dtstart[-1][0] == datetime.date(2023, 10, 31)

    def test_another_problem(self):
        vevent = _get_vevent(another_problem)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart[0][0] == berlin.localize(
            datetime.datetime(2013, 11, 13, 19, 0))
        assert dtstart[-1][0] == berlin.localize(
            datetime.datetime(2028, 11, 8, 19, 0))

########NEW FILE########
__FILENAME__ = event_from_string_test
# vim: set fileencoding=utf-8:
from datetime import date, datetime, timedelta
import random

import pytz

from khal.aux import construct_event


def _now():
    return datetime(2014, 2, 16, 12, 0, 0, 0)


today = date.today()
tomorrow = today + timedelta(days=1)
today_s = '{0:02}{1:02}{2:02}'.format(*today.timetuple()[0:3])
tomorrow_s = '{0:02}{1:02}{2:02}'.format(*tomorrow.timetuple()[0:3])
this_year_s = str(today.year)

test_set_format_de = [
    # all-day-events
    # one day only
    ('25.10.2013 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20131025',
                  'DTEND;VALUE=DATE:20131026',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # 2 day
    ('15.08.2014 16.08. Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20140815',
                  'DTEND;VALUE=DATE:20140817',  # XXX
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # end date in next year and not specified
    ('29.12.2014 03.01. Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20141229',
                  'DTEND;VALUE=DATE:20150104',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # end date in next year
    ('29.12.2014 03.01.2015 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20141229',
                  'DTEND;VALUE=DATE:20150104',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # datetime events
    # start and end date same, no explicit end date given
    ('25.10.2013 18:00 20:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T200000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # start and end date same, explicit end date (but no year) given
    ('25.10.2013 18:00 26.10. 20:00 Äwesöme Event',   # XXX FIXME: if no explicit year is given for the end, this_year is used
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T200000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # date ends next day, but end date not given
    ('25.10.2013 23:00 0:30 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T230000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T003000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # only start datetime given
    ('25.10.2013 06:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T060000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T070000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # timezone given
    ('25.10.2013 06:00 America/New_York Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:20131025T060000',
                  'DTEND;TZID=America/New_York;VALUE=DATE-TIME:20131025T070000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
]


def test_construct_event_format_de():
    timeformat = '%H:%M'
    dateformat = '%d.%m.'
    longdateformat = '%d.%m.%Y'
    datetimeformat = '%d.%m. %H:%M'
    longdatetimeformat = '%d.%m.%Y %H:%M'
    DEFAULTTZ = pytz.timezone('Europe/Berlin')
    for data_list, vevent in test_set_format_de:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent


test_set_format_us = [
    ('12/31/1999 06:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:19991231T060000',
                  'DTEND;TZID=America/New_York;VALUE=DATE-TIME:19991231T070000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',

                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    ('12/18 12/20 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:{0}1218',
                  'DTEND;VALUE=DATE:{0}1221',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(this_year_s)),
]


def test_construct_event_format_us():
    timeformat = '%H:%M'
    dateformat = '%m/%d'
    longdateformat = '%m/%d/%Y'
    datetimeformat = '%m/%d %H:%M'
    longdatetimeformat = '%m/%d/%Y %H:%M'
    DEFAULTTZ = pytz.timezone('America/New_York')
    for data_list, vevent in test_set_format_us:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent


test_set_format_de_complexer = [
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T080000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T090000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(today_s)),
    # today until tomorrow
    ('22:00  1:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T220000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{1}T010000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(today_s, tomorrow_s)),
    ('15.06. Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:{0}0615',
                  'DTEND;VALUE=DATE:{0}0616',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(this_year_s)),
]


def test_construct_event_format_de_complexer():
    timeformat = '%H:%M'
    dateformat = '%d.%m.'
    longdateformat = '%d.%m.%Y'
    datetimeformat = '%d.%m. %H:%M'
    longdatetimeformat = '%d.%m.%Y %H:%M'
    DEFAULTTZ = pytz.timezone('Europe/Berlin')
    for data_list, vevent in test_set_format_de_complexer:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent


test_set_description = [
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event :: this is going to be awesome',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T080000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T090000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'DESCRIPTION:this is going to be awesome',
                  'END:VEVENT',
                  '']).format(today_s)),
    # today until tomorrow
    ('22:00  1:00 Äwesöme Event :: Will be even better',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T220000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{1}T010000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'DESCRIPTION:Will be even better',
                  'END:VEVENT',
                  '']).format(today_s, tomorrow_s)),
    ('15.06. Äwesöme Event :: and again',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:{0}0615',
                  'DTEND;VALUE=DATE:{0}0616',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'DESCRIPTION:and again',
                  'END:VEVENT',
                  '']).format(this_year_s)),
]

def test_description():
    timeformat = '%H:%M'
    dateformat = '%d.%m.'
    longdateformat = '%d.%m.%Y'
    datetimeformat = '%d.%m. %H:%M'
    longdatetimeformat = '%d.%m.%Y %H:%M'
    DEFAULTTZ = pytz.timezone('Europe/Berlin')
    for data_list, vevent in test_set_description:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent


########NEW FILE########
__FILENAME__ = event_test
import datetime

import pytest

from khal.khalendar.event import Event


today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""


event_dt = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

cal_dt = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN
BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
DTSTART;VALUE=DATE-TIME:20140330T010000
TZNAME:CEST
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:DAYLIGHT
BEGIN:STANDARD
DTSTART;VALUE=DATE-TIME:20141026T010000
TZNAME:CET
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT
END:VCALENDAR
""".split('\n')


event_d = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140409
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

cal_d = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN
BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140409
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT
END:VCALENDAR
""".split('\n')

event_kwargs = {'account': 'foobar',
                'local_tz': None,
                'default_tz': None}


class TestEvent(object):
    def test_raw_dt(self):
        assert Event(event_dt, **event_kwargs).raw.split('\r\n') == cal_dt

    def test_raw_d(self):
        assert Event(event_d, **event_kwargs).raw.split('\r\n') == cal_d

########NEW FILE########
__FILENAME__ = khalendar_test
import datetime
import os

import pytest
import pytz

from vdirsyncer.storage import FilesystemStorage
from vdirsyncer.storage.base import Item

from khal.khalendar import Calendar, CalendarCollection
from khal.khalendar.event import Event

from khal.khalendar.backend import CouldNotCreateDbDir



today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""

event_today = event_allday_template.format(today.strftime('%Y%m%d'),
                                           tomorrow.strftime('%Y%m%d'))
item_today = Item(event_today)

cal1 = 'foobar'
cal2 = 'work'
cal3 = 'private'

example_cals = [cal1, cal2, cal3]

KWARGS = {
    'default_tz': pytz.timezone('Europe/Berlin'),
    'local_tz': pytz.timezone('Europe/Berlin'),
}


@pytest.fixture
def cal_vdir(tmpdir):
    cal = Calendar(cal1, ':memory:', str(tmpdir), **KWARGS)
    vdir = FilesystemStorage(str(tmpdir), '.ics')
    return cal, vdir


@pytest.fixture
def coll_vdirs(tmpdir):
    coll = CalendarCollection()
    vdirs = dict()
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        coll.append(Calendar(name, ':memory:', path, **KWARGS))
        vdirs[name] = FilesystemStorage(path, '.ics')
    return coll, vdirs


class TestCalendarTest(object):
    def test_create(self, cal_vdir):
        assert True

    def test_empty(self, cal_vdir):
        cal, vdir = cal_vdir
        events = cal.get_allday_by_time_range(today)
        assert events == list()
        assert list(vdir.list()) == list()

    def test_new_event(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today, **KWARGS)
        assert event.account == cal1
        cal.new(event)
        events = cal.get_allday_by_time_range(today)
        assert len(events) == 1
        events = cal.get_allday_by_time_range(tomorrow)
        assert len(events) == 0
        events = cal.get_allday_by_time_range(yesterday)
        assert len(events) == 0
        assert len(list(vdir.list())) == 1

    def test_db_needs_update(self, cal_vdir):
        cal, vdir = cal_vdir
        vdir.upload(item_today)
        cal.db_update()
        assert cal._db_needs_update() is False

    def test_db_needs_update_after_insert(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today, **KWARGS)
        cal.new(event)
        assert cal._db_needs_update() is False

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

aday = datetime.date(2014, 04, 9)
bday = datetime.date(2014, 04, 10)


event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""


event_dt = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_d = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140409
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""


class TestCollection(object):

    astart = datetime.datetime.combine(aday, datetime.time.min)
    aend = datetime.datetime.combine(aday, datetime.time.max)
    bstart = datetime.datetime.combine(bday, datetime.time.min)
    bend = datetime.datetime.combine(bday, datetime.time.max)

    def test_empty(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        start = datetime.datetime.combine(today, datetime.time.min)
        end = datetime.datetime.combine(today, datetime.time.max)
        assert coll.get_allday_by_time_range(today) == list()
        assert coll.get_datetime_by_time_range(start, end) == list()

    def test_insert(self, coll_vdirs):
        coll, vdirs = coll_vdirs

        event = Event(event_dt, account='foo', **KWARGS)
        coll.new(event, cal1)
        events = coll.get_datetime_by_time_range(self.astart, self.aend)
        assert len(events) == 1
        assert events[0].account == cal1

        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0

        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_change(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = Event(event_dt, account='foo', **KWARGS)
        coll.new(event, cal1)
        event = coll.get_datetime_by_time_range(self.astart, self.aend)[0]
        assert event.account == cal1

        coll.change_collection(event, cal2)
        events = coll.get_datetime_by_time_range(self.astart, self.aend)
        assert len(events) == 1
        assert events[0].account == cal2


@pytest.fixture
def cal_dbpath(tmpdir):
    name = 'testcal'
    vdirpath = str(tmpdir) + '/' + name
    dbpath = str(tmpdir) + '/subdir/' + 'khal.db'
    cal = Calendar(name, dbpath, vdirpath, **KWARGS)

    return cal, dbpath


class TestDbCreation(object):

    def test_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        assert not os.path.isdir(dbdir)
        Calendar(name, dbpath, vdirpath, **KWARGS)
        assert os.path.isdir(dbdir)

    def test_failed_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        os.chmod(str(tmpdir), 400)

        with pytest.raises(CouldNotCreateDbDir):
            Calendar(name, dbpath, vdirpath, **KWARGS)

########NEW FILE########
__FILENAME__ = terminal_test
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:


import datetime

import pytest

from khal.calendar_display import vertical_month, getweeknumber, str_week
from khal.terminal import merge_columns, colored, bstring, rstring


def test_rstring():
    assert rstring('test') == '\x1b[7mtest\x1b[0m'
    assert rstring(u'täst') == u'\x1b[7mtäst\x1b[0m'


def test_bstring():
    assert bstring('test') == '\x1b[1mtest\x1b[0m'
    assert bstring(u'täst') == u'\x1b[1mtäst\x1b[0m'


def test_colored():
    assert colored('test', 'light cyan') == '\33[1;36mtest\x1b[0m'
    assert colored(u'täst', 'white') == u'\33[37mtäst\x1b[0m'



class TestMergeColumns(object):
    def test_longer_right(self):
        left = ['uiae', 'nrtd']
        right = ['123456', '234567', '345678']
        out = ['uiae    123456',
               'nrtd    234567',
               '        345678']
        assert merge_columns(left, right, width=4) == out

    def test_longer_left(self):
        left = ['uiae', 'nrtd', 'xvlc']
        right = ['123456', '234567']
        out = ['uiae    123456', 'nrtd    234567', 'xvlc    ']
        assert merge_columns(left, right, width=4) == out

########NEW FILE########
