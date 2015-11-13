__FILENAME__ = glow
import cPickle as pickle
import os
import json
import logging
import shutil
import time
from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter

import hb
import settings_local as settings

log = logging.getLogger('glow')


# The default version number we look for.
FX = settings.FIREFOX_VERSION
JSON_DIR = os.path.join(settings.BASE_DIR, 'json')
PICKLE = settings.path('glow.pickle')
BACKUP = PICKLE + '.bak'

hbase = hb.Client(settings.HBASE_HOST, settings.HBASE_PORT,
                  settings.HBASE_TABLES['realtime'])

# Maps {country: continent}.
continents = json.load(open(settings.path('continents.json')))

# Maps {country code: name}.
countries = json.load(open(settings.path('countries.json')))

# Maps {country code: {region code: name}}.
regions = json.load(open(settings.path('regions.json')))
geo = (continents, countries, regions)

# We're not supposed to show downloads for these countries (607127#c10):
# Cuba, Iran, Syria, N. Korea, Myanmar, Sudan. Go figure.
REDACTED = ('CU', 'IR', 'SY', 'KP', 'MM', 'SD')

##
## 1. The part that talks to Hbase and collects data.
##

# These contain global download totals that get updated every time we process a
# new chunk of data.
G = {
    'total': 0,
    'counts': [],
    'arc': {},
    'version': 8,
}

# This should be a lambda but pickle can't pickle a lambda.
def defaultdict_int():
    return defaultdict(int)

# The global locale count aggregator.
# {continent: {country: {region: {city: total}}}}
G['arc'] = dict((k, {}) for k in continents.values())
for country, continent in continents.items():
    G['arc'][continent][country] = defaultdict(defaultdict_int)
for country, regions in regions.items():
    continent = continents[country]
    for region in regions:
        G['arc'][continent][country][region] = defaultdict(int)


def row_name(dt):
    """Convert a datetime into the Hbase timestamp format."""
    # TODO: mobile.
    return 'firefox::%s:%s' % (FX, dt.strftime('%Y-%m-%dT%H:%M:00.000'))


def time_sequence(dt, num=100):
    for i in xrange(num):
        yield dt + timedelta(minutes=i)


def row_sum(row):
    return sum(row.columns.itervalues()) if row else 0


def get_counts(dt, num=1):
    """Get `num` minutes of download counts starting at `dt`."""
    if num == 1:
        rows = hbase.row(row_name(dt), ['product'])
    else:
        rows = hbase.scanner(row_name(dt), ['product']).list(num)
    return [(t.utctimetuple()[:5], row_sum(row))
            for t, row in zip(time_sequence(dt, num), rows)]


def extend_counts(counts):
    for t, count in counts:
        G['total'] += count
        G['counts'].append((t, G['total']))
    G['counts'] = G['counts'][-60:]
    if len(G['counts']) == 1:
        t = datetime(*G['counts'][0][0])
        G['counts'].insert(0, (t.utctimetuple()[:5], 0))


def process_locations(rows):
    """
    Break up the hbase rows into a list of
    [(continent, country, region, city, lat, lon, num_downloads)].

    The cumulative count in `arc` is updated inline.
    """
    # Get local names for fast lookups in the loop.
    arc = G['arc']
    continents, countries, regions = geo
    rv = []
    total = 0
    alfred = 0
    for row in rows:
        new = []
        # We localize country names on the client.
        for key, val in row.columns.iteritems():
            total += val
            country, region, city, lat, lon = key.split(':')[-5:]
            if country in REDACTED:
                continue
            try:
                # Sometimes maxmind gives us regions named '  ' or '00'. Those
                # are invalid. The frontend expects invalid regions named ''.
                if region.strip() in ('', '00'):
                    region = ''
                    log.debug('Renaming region: %s.' % key)
                # (0, 0) means the download is from a satellite/proxy.
                if float(lat) == float(lon) == 0:
                    continue
                if (country, region, city) == ('US', 'NY', 'Alfred'):
                    alfred += 1
                    continue
                continent = continents[country]
                arc[continent][country][region][city] += val
                new.append((continent, country, region, city,
                            lat, lon, val))
            except (KeyError, ValueError):
                log.error('skipping key: %s' % key, exc_info=True)
                pass
        rv.append((total, new))
    log.info('Skipping Alfred, NY: %s.' % alfred)
    return rv


def _get_locations(dt, num=1):
    """Get `num` minutes of download locations starting at `dt`."""
    if num == 1:
        rows = hbase.row(row_name(dt), ['location:'])
    else:
        rows = hbase.scanner(row_name(dt), ['location:']).list(num)
    locs = process_locations(rows)
    return [(t.utctimetuple()[:5], r)
            for t, r in zip(time_sequence(dt, num), locs)]


def get_map(dt, num=1):
    """Get a list of [`dt`, num_rows, [(lat, long, num_downloads)]]."""
    # Get (time, num_rows, [(lat, long, hits)]) for each datetime.
    times = [(t, (num, [r[-3:] for r in rows]))
             for t, (num, rows) in _get_locations(dt, num)]
    hits = [row for t in times for row in t[1][1]]
    return (times[0][0], len(hits), hits)


def get_arc():
    """
    Aggregate the location data into an easy json structure:

        (None, total,
         [continent, total, [country, total, [region, total, [city, total]]]])

    The expected format of `data` is:

        {continent: {country: {region: {city: total}}}}

    Each outer total is the sum of its childrens' inner totals.
    """
    def unpack(dict_):
        """Unpack a (key, (v1, v2)) structure into (key, v1, v2)."""
        return revsort((a.strip(), b, c) for a, (b, c) in dict_.iteritems())

    revsort = lambda xs: sorted(xs, key=itemgetter(1), reverse=True)
    continents, world_sum = {}, 0
    for continent, country_dict in G['arc'].iteritems():
        countries, continent_sum = {}, 0
        for country, region_dict in country_dict.iteritems():
            regions, country_sum = {}, 0
            for region, cities in region_dict.iteritems():
                total = sum(cities.itervalues())
                if total:
                    cs = [(k.strip(), v) for k, v in cities.iteritems()]
                    regions[region] = [total, revsort(cs)]
                    country_sum += total
            if country_sum:
                countries[country] = [country_sum, unpack(regions)]
                continent_sum += country_sum
        if continent_sum:
            continents[continent] = [continent_sum, unpack(countries)]
            world_sum += continent_sum
    return (None, world_sum, unpack(continents))


##
## 2. The main loop.
##

def makedirs(d):
    if not os.path.exists(d):
        log.info('Making dir %s.' % d)
        os.makedirs(d)


def write_files(dt, count_data=None, map_data=None, arc_data=None,
                interval=60):
    """Write all the data dicts we were given to their files."""
    log.info('Writing data for %s.' % dt)
    xs = {'count': count_data, 'map': map_data, 'arc': arc_data}
    for name, data in xs.items():
        if not data:
            continue
        fmt = '%Y/%m/%d/%H/%M/{name}.json'.format(name=name)
        path = os.path.join(JSON_DIR, dt.strftime(fmt))
        next = (dt + timedelta(seconds=interval)).strftime(fmt)
        makedirs(os.path.dirname(path))
        d = {'next': next, 'interval': interval, 'data': data}
        json.dump(d, open(path, 'w'), separators=(',', ':'))


def collect(dt):
    """Grab Hbase data, write json files, save internal state."""
    log.info('Fetching data for %s.' % dt)
    extend_counts(get_counts(dt))
    write_files(dt, G['counts'], get_map(dt), get_arc())
    dump_state(dt)


def now():
    # Live one minute in the past so Hbase has time to collect a full minute of
    # data before we start talking to it.
    return datetime.utcnow() - timedelta(minutes=1)


def do_the_stuff_to_the_thing():
    dt = now()
    next = dt + timedelta(minutes=1)
    # Wait until :15 to give Hbase some processing time.
    if dt.second < 15:
        log.info('Waiting until :15 past.')
        time.sleep(15 - dt.second)

    collect(dt)

    # Sleep until the next minute comes around.
    wait = next.replace(second=15) - now().replace(microsecond=0)
    # The delta will be around -1 days, 86400 seconds if we're into the next
    # minute already.
    if wait.seconds <= 60:
        log.info('Sleeping for %s seconds.' % wait.seconds)
        time.sleep(wait.seconds)
    else:
        log.info('Skipping sleep.')


def main():
    load_state()
    log.info('Looping, infinitely.')
    while 1:
        try:
            do_the_stuff_to_the_thing()
        except hb.exceptions:
            log.error('Recycling Hbase connection.', exc_info=True)
            hbase.recycle()


#
# 3. Saving and loading application state.
#

def dump_state(dt):
    """Dump all the global aggregators so we can pick at the same spot."""
    log.info('Saving state for %s.' % dt)
    if os.path.exists(PICKLE):
        shutil.copyfile(PICKLE, BACKUP)
    d = {'G': G, 'last_update': dt}
    pickle.dump(d, open(PICKLE, 'w'))


def load_state():
    """Figure out where we left off, catch up on old data if needed."""
    if not (os.path.exists(PICKLE) or os.path.exists(BACKUP)):
        return
    log.info('Found a pickle, picking it up.')
    try:
        d = pickle.load(open(PICKLE))
    except Exception:
        log.error('Trouble opening pickle.', exc_info=True)
        if os.path.exists(BACKUP):
            log.info('Loading backup pickle.')
            d = pickle.load(open(BACKUP))

    if d['G'].get('version') == 7:
        upgrade_7to8(d['G'])

    if d['G'].get('version') == G['version']:
        for k, v in d['G'].items():
            G[k] = v
    else:
        log.info('Skipping out of date pickle (want v%s).' % G['version'])

    dt = now()
    delta = dt - d['last_update'].replace(second=0)
    if delta.seconds > 60:
        log.info('Missing %s minutes. Catching up.' % (delta.seconds / 60))
        for i in xrange(1, delta.seconds / 60):
            collect(d['last_update'] + timedelta(minutes=i))

    # Collect once more if the clock rolled over during catchup.
    if now().minute != dt.minute:
        log.info('Rollover!')
        load_state()

    # Wait until the next minute if the last update was at 1:15:00 and the
    # current time is less than 1:16:00 so we don't count twice.
    if now().minute == d['last_update'].minute:
        log.info('Waiting for the minute to roll over.')
        time.sleep(60 - now().second)


def upgrade_7to8(d):
    d['version'] = 8
    alfred = d['arc']['NA']['US']['NY']['Alfred']
    log.info('Removing %s downloads from Alfred.' % alfred)
    d['counts'] = [(a, b - alfred) for a, b in d['counts']]
    log.info('Adjusting count: %s => %s' % (d['total'], d['total'] - alfred))
    d['total'] -= alfred
    d['arc']['NA']['US']['NY']['Alfred'] = 0

#
# 4. Cleanup.
#


def cleanup():
    # Delete all the data from two days ago. This expects to run in cron daily
    # so there won't be any data older than two days.
    d = (now() - timedelta(days=2)).strftime('%Y/%m/%d')
    path = os.path.join(JSON_DIR, d)
    if os.path.exists(path):
        log.info('Dropping %s.' % path)
        shutil.rmtree(path)
        # Try to delete the month and year directories. rmdir only works if the
        # directory is empty, so this will clean up empty directories.
        try:
            os.rmdir(os.path.dirname(path))
            os.rmdir(os.path.dirname(os.path.dirname(path)))
        except OSError:
            pass

########NEW FILE########
__FILENAME__ = hb
"""
An abstraction layer for pulling download metrics out of hbase.

The Thrift/Hbase API is a mess only a Java programmer could love. This is not a
complete wrapper; pieces are implemented as needed.

It's assumed that the value of TCells (which are returned as byte arrays)
should be converted to unsigned long longs.

"""
import struct


from thrift import Thrift
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from hbase import Hbase, ttypes


exceptions = (Thrift.TException, ttypes.IOError, ttypes.IllegalArgument,
              ttypes.AlreadyExists)


def convert(rows):
    """Unpack each value in the TCell to an unsigned long long."""
    # It may be wiser to do this lazily.
    for row in rows:
        columns = row.columns
        for key, tcell in columns.iteritems():
            columns[key] = struct.unpack('!Q', tcell.value)[0]
    return rows


class Client(object):

    def __init__(self, host, port, table):
        self.host = host
        self.port = port
        self.table = table
        self.open()

    def open(self):
        socket = TSocket.TSocket(self.host, self.port)
        self.transport = TTransport.TBufferedTransport(socket)
        protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
        self.client = Hbase.Client(protocol)
        self.transport.open()

    def close(self):
        self.transport.close()

    def recycle(self):
        self.close()
        self.open()

    def __del__(self):
        self.close()

    def scanner(self, start='', columns=None):
        """Get a new scanner on the table."""
        id = self.client.scannerOpen(self.table, start, columns)
        return Scanner(self, id)

    def row(self, row_, columns=None):
        """Fetch the row_, optionally constrained to a list of columns."""
        rv = self.client.getRowWithColumns(self.table, row_, columns)
        return convert(rv) if rv else []


class Scanner(object):

    def __init__(self, client, id):
        self.client = client
        self.id = id

    def next(self):
        """Fetch the next row from the scanner."""
        return convert(self.client.client.scannerGet(self.id))[0]

    def list(self, num):
        """Fetch the next ``num`` rows from the scanner."""
        return convert(self.client.client.scannerGetList(self.id, num))

########NEW FILE########
__FILENAME__ = log_settings
import logging
import logging.handlers

import dictconfig

import settings_local as settings


fmt = '[%(asctime)s] %(name)s:%(levelname)s %(message)s'


cfg = {
    'version': 1,
    'filters': {},
    'formatters': {
        'file': {'format': fmt},
        'syslog': {'format': '%s: %s' % (settings.SYSLOG_TAG, fmt)},
    },
    'handlers': {
        'file': {
            '()': logging.FileHandler,
            'filename': settings.path('glow.log'),
            'mode': 'a',
            'formatter': 'file',
        },
        'syslog': {
            '()': logging.handlers.SysLogHandler,
            'facility': logging.handlers.SysLogHandler.LOG_USER,
            'formatter': 'syslog',
        },
    },
    'root': {
        'level': logging.DEBUG,
        'handlers': ['file'],
    },
}


if settings.USE_SYSLOG:
    cfg['root']['handlers'].append('syslog')


dictconfig.dictConfig(cfg)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import site
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

# Add vendor so we can import 3rd-party libs.
site.addsitedir(ROOT)
site.addsitedir(path('vendor'))

import argparse

import log_settings
import glow
import po2js


def shell():
    try:
        import IPython
        IPython.Shell.IPShell(argv=[], user_ns={'g': glow}).mainloop()
    except ImportError:
        import code
        code.interact()


COMMANDS = {
    'shell': shell,
    'glow': glow.main,
    'cleanup': glow.cleanup,
    'po': po2js.main,
}


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=sorted(COMMANDS),
                    help='what should I do?')


if __name__ == '__main__':
    args = parser.parse_args(sys.argv[1:2])
    try:
        COMMANDS[args.command](*sys.argv[2:])
    except KeyboardInterrupt:
        raise
        pass  # Die quietly.

########NEW FILE########
__FILENAME__ = po2js
"""
Take a messages.po file and turn it into a javascript file.

All the strings end up in a variable called catalog. That locale's short time
format is in _timefmt and the numeric separator is in _group.

Call the function with the source directory of messages.po files and the
destination directory for the l10n.js files.
"""
import codecs
import json

import path
from babel.core import Locale, UnknownLocaleError
from babel.messages import pofile


ROOT = path.path('locale')
DOMAIN = 'messages.po'
DEFAULT = 'en_US'


def steal():
    for f in path.path('locale').walkfiles('messages.po'):
        lang = f.split('/')[1]
        django = path.path('django') / lang / 'LC_MESSAGES' / 'django.po'
        if django.exists():
            d = po_to_dict(django)
            with codecs.open(f, 'a', 'utf-8') as fd:
                for k in 'AM', 'PM':
                    fd.write('\nmsgid: "%s"\nmsgstr: "%s"\n' % (k, d.get(k, k)))


def po_to_dict(path):
    return dict((p.id, p.string) for p in pofile.read_po(open(path))
                if p.id and p.string)


def main(src, dst):
    locales = []
    for f in path.path(src).walkfiles('messages.po'):
        print f
        lang = f.split('/')[1]
        locales.append(lang.replace('_', '-'))
        print lang
        try:
            locale = Locale(lang)
        except UnknownLocaleError:
            print 'Unknown locale:', lang
            locale = Locale(DEFAULT)
        out = path.path(dst) / lang
        if not out.exists():
            out.makedirs()
        d = {'po': json.dumps(po_to_dict(f), separators=(',', ':')),
             'timefmt': locale.time_formats['short'].pattern,
             'numfmt': locale.decimal_formats[None].pattern,
             'group': locale.number_symbols['group']}
        print '% 5s %8s %s %s' % (lang, d['timefmt'], d['group'], d['numfmt'])
        with codecs.open(out / 'l10n.js', 'w', 'utf-8') as fd:
            fd.write(template % d)

        default = path.path('locale/countries/en-US.json')
        countries = path.path('locale/countries/%s.json' %
                              lang.replace('_', '-'))
        regions = path.path('locale/%s/regions.json' % lang)
        cities = path.path('locale/%s/cities.json' % lang)
        if not countries.exists():
            print '*' * 30, 'missing', lang
            countries = default
        with codecs.open(out / 'countries.js', 'w', 'utf-8') as fd:
            d = dict((k.upper(), v)
                     for k, v in json.load(countries.open()).items())
            if regions.exists():
                print 'Adding regions for', lang
                d.update(json.load(regions.open()))
            if cities.exists():
                print 'Adding cities for', lang
                d.update(json.load(cities.open()))
            fd.write('var _countries = %s;' % json.dumps(d, separators=(',', ':')))
    lo = ["'%s'" % x.lower() for x in locales]
    print '$locales = array(%s);' % ', '.join(lo)


template = """\
var catalog = %(po)s,
    _timefmt = "%(timefmt)s",
    _group = "%(group)s",
    _numfmt = "%(numfmt)s";
"""

########NEW FILE########
__FILENAME__ = settings
import os

HBASE_HOST = 'node1.research.hadoop.sjc1.mozilla.com'
HBASE_HOST = '10.2.72.102'
HBASE_PORT = 9090

HBASE_TABLES = {
    'realtime': 'dmo_metrics_realtime',
    'hourly': 'dmo_metrics_hourly',
    'new': 'dmo_metrics_realtime_newschema',
}

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

BASE_DIR = path('data')

USE_SYSLOG = False
SYSLOG_TAG = 'http_app_glow'

FIREFOX_VERSION = '4.0'

########NEW FILE########
__FILENAME__ = argparse
# -*- coding: utf-8 -*-

# Copyright © 2006-2009 Steven J. Bethard <steven.bethard@gmail.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Command-line parsing library

This module is an optparse-inspired command-line parsing library that:

    - handles both optional and positional arguments
    - produces highly informative usage messages
    - supports parsers that dispatch to sub-parsers

The following is a simple usage example that sums integers from the
command-line and writes the result to a file::

    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')
    parser.add_argument(
        'integers', metavar='int', nargs='+', type=int,
        help='an integer to be summed')
    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()
    args.log.write('%s' % sum(args.integers))
    args.log.close()

The module contains the following public classes:

    - ArgumentParser -- The main entry point for command-line parsing. As the
        example above shows, the add_argument() method is used to populate
        the parser with actions for optional and positional arguments. Then
        the parse_args() method is invoked to convert the args at the
        command-line into an object with attributes.

    - ArgumentError -- The exception raised by ArgumentParser objects when
        there are errors with the parser's actions. Errors raised while
        parsing the command-line are caught by ArgumentParser and emitted
        as command-line messages.

    - FileType -- A factory for defining types of files to be created. As the
        example above shows, instances of FileType are typically passed as
        the type= argument of add_argument() calls.

    - Action -- The base class for parser actions. Typically actions are
        selected by passing strings like 'store_true' or 'append_const' to
        the action= argument of add_argument(). However, for greater
        customization of ArgumentParser actions, subclasses of Action may
        be defined and passed as the action= argument.

    - HelpFormatter, RawDescriptionHelpFormatter, RawTextHelpFormatter,
        ArgumentDefaultsHelpFormatter -- Formatter classes which
        may be passed as the formatter_class= argument to the
        ArgumentParser constructor. HelpFormatter is the default,
        RawDescriptionHelpFormatter and RawTextHelpFormatter tell the parser
        not to change the formatting for help text, and
        ArgumentDefaultsHelpFormatter adds information about argument defaults
        to the help.

All other classes in this module are considered implementation details.
(Also note that HelpFormatter and RawDescriptionHelpFormatter are only
considered public as object names -- the API of the formatter objects is
still considered an implementation detail.)
"""

__version__ = '1.1'
__all__ = [
    'ArgumentParser',
    'ArgumentError',
    'Namespace',
    'Action',
    'FileType',
    'HelpFormatter',
    'RawDescriptionHelpFormatter',
    'RawTextHelpFormatter',
    'ArgumentDefaultsHelpFormatter',
]


import copy as _copy
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from gettext import gettext as _

try:
    _set = set
except NameError:
    from sets import Set as _set

try:
    _basestring = basestring
except NameError:
    _basestring = str

try:
    _sorted = sorted
except NameError:

    def _sorted(iterable, reverse=False):
        result = list(iterable)
        result.sort()
        if reverse:
            result.reverse()
        return result


def _callable(obj):
    return hasattr(obj, '__call__') or hasattr(obj, '__bases__')

# silence Python 2.6 buggy warnings about Exception.message
if _sys.version_info[:2] == (2, 6):
    import warnings
    warnings.filterwarnings(
        action='ignore',
        message='BaseException.message has been deprecated as of Python 2.6',
        category=DeprecationWarning,
        module='argparse')


SUPPRESS = '==SUPPRESS=='

OPTIONAL = '?'
ZERO_OR_MORE = '*'
ONE_OR_MORE = '+'
PARSER = 'A...'
REMAINDER = '...'

# =============================
# Utility functions and classes
# =============================

class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            arg_strings.append('%s=%r' % (name, value))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return _sorted(self.__dict__.items())

    def _get_args(self):
        return []


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)


# ===============
# Formatting Help
# ===============

class HelpFormatter(object):
    """Formatter for generating usage messages and argument help strings.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        # default setting for width
        if width is None:
            try:
                width = int(_os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2

        self._prog = prog
        self._indent_increment = indent_increment
        self._max_help_position = max_help_position
        self._width = width

        self._current_indent = 0
        self._level = 0
        self._action_max_length = 0

        self._root_section = self._Section(self, None)
        self._current_section = self._root_section

        self._whitespace_matcher = _re.compile(r'\s+')
        self._long_break_matcher = _re.compile(r'\n\n\n+')

    # ===============================
    # Section and indentation methods
    # ===============================
    def _indent(self):
        self._current_indent += self._indent_increment
        self._level += 1

    def _dedent(self):
        self._current_indent -= self._indent_increment
        assert self._current_indent >= 0, 'Indent decreased below 0.'
        self._level -= 1

    class _Section(object):

        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            for func, args in self.items:
                func(*args)
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not SUPPRESS and self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = '%*s%s:\n' % (current_indent, '', self.heading)
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _add_item(self, func, args):
        self._current_section.items.append((func, args))

    # ========================
    # Message building methods
    # ========================
    def start_section(self, heading):
        self._indent()
        section = self._Section(self, self._current_section, heading)
        self._add_item(section.format_help, [])
        self._current_section = section

    def end_section(self):
        self._current_section = self._current_section.parent
        self._dedent()

    def add_text(self, text):
        if text is not SUPPRESS and text is not None:
            self._add_item(self._format_text, [text])

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is not SUPPRESS:
            args = usage, actions, groups, prefix
            self._add_item(self._format_usage, args)

    def add_argument(self, action):
        if action.help is not SUPPRESS:

            # find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))

            # update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)

            # add the item to the list
            self._add_item(self._format_action, [action])

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    # =======================
    # Help-formatting methods
    # =======================
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n') + '\n'
        return help

    def _join_parts(self, part_strings):
        return ''.join([part
                        for part in part_strings
                        if part and part is not SUPPRESS])

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = _('usage: ')

        # if usage is specified, use that
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = '%(prog)s' % dict(prog=self._prog)

        # if optionals and positionals are available, calculate usage
        elif usage is None:
            prog = '%(prog)s' % dict(prog=self._prog)

            # split optionals from positionals
            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)

            # build full usage string
            format = self._format_actions_usage
            action_usage = format(optionals + positionals, groups)
            usage = ' '.join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                # break usage into wrappable parts
                part_regexp = r'\(.*?\)+|\[.*?\]+|\S+'
                opt_usage = format(optionals, groups)
                pos_usage = format(positionals, groups)
                opt_parts = _re.findall(part_regexp, opt_usage)
                pos_parts = _re.findall(part_regexp, pos_usage)
                assert ' '.join(opt_parts) == opt_usage
                assert ' '.join(pos_parts) == pos_usage

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width:
                            lines.append(indent + ' '.join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + ' '.join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent):]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = ' ' * (len(prefix) + len(prog) + 1)
                    if opt_parts:
                        lines = get_lines([prog] + opt_parts, indent, prefix)
                        lines.extend(get_lines(pos_parts, indent))
                    elif pos_parts:
                        lines = get_lines([prog] + pos_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = ' ' * len(prefix)
                    parts = opt_parts + pos_parts
                    lines = get_lines(parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(opt_parts, indent))
                        lines.extend(get_lines(pos_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = '\n'.join(lines)

        # prefix with 'usage:'
        return '%s%s\n\n' % (prefix, usage)

    def _format_actions_usage(self, actions, groups):
        # find group indices and identify actions in groups
        group_actions = _set()
        inserts = {}
        for group in groups:
            try:
                start = actions.index(group._group_actions[0])
            except ValueError:
                continue
            else:
                end = start + len(group._group_actions)
                if actions[start:end] == group._group_actions:
                    for action in group._group_actions:
                        group_actions.add(action)
                    if not group.required:
                        inserts[start] = '['
                        inserts[end] = ']'
                    else:
                        inserts[start] = '('
                        inserts[end] = ')'
                    for i in range(start + 1, end):
                        inserts[i] = '|'

        # collect all actions format strings
        parts = []
        for i, action in enumerate(actions):

            # suppressed arguments are marked with None
            # remove | separators for suppressed arguments
            if action.help is SUPPRESS:
                parts.append(None)
                if inserts.get(i) == '|':
                    inserts.pop(i)
                elif inserts.get(i + 1) == '|':
                    inserts.pop(i + 1)

            # produce all arg strings
            elif not action.option_strings:
                part = self._format_args(action, action.dest)

                # if it's in a group, strip the outer []
                if action in group_actions:
                    if part[0] == '[' and part[-1] == ']':
                        part = part[1:-1]

                # add the action string to the list
                parts.append(part)

            # produce the first way to invoke the option in brackets
            else:
                option_string = action.option_strings[0]

                # if the Optional doesn't take a value, format is:
                #    -s or --long
                if action.nargs == 0:
                    part = '%s' % option_string

                # if the Optional takes a value, format is:
                #    -s ARGS or --long ARGS
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    part = '%s %s' % (option_string, args_string)

                # make it look optional if it's not required or in a group
                if not action.required and action not in group_actions:
                    part = '[%s]' % part

                # add the action string to the list
                parts.append(part)

        # insert things at the necessary indices
        for i in _sorted(inserts, reverse=True):
            parts[i:i] = [inserts[i]]

        # join all the action items with spaces
        text = ' '.join([item for item in parts if item is not None])

        # clean up separators for mutually exclusive groups
        open = r'[\[(]'
        close = r'[\])]'
        text = _re.sub(r'(%s) ' % open, r'\1', text)
        text = _re.sub(r' (%s)' % close, r'\1', text)
        text = _re.sub(r'%s *%s' % (open, close), r'', text)
        text = _re.sub(r'\(([^|]*)\)', r'\1', text)
        text = text.strip()

        # return the text
        return text

    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        text_width = self._width - self._current_indent
        indent = ' ' * self._current_indent
        return self._fill_text(text, text_width, indent) + '\n\n'

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0]))
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    def _metavar_formatter(self, action, default_metavar):
        if action.metavar is not None:
            result = action.metavar
        elif action.choices is not None:
            choice_strs = [str(choice) for choice in action.choices]
            result = '{%s}' % ','.join(choice_strs)
        else:
            result = default_metavar

        def format(tuple_size):
            if isinstance(result, tuple):
                return result
            else:
                return (result, ) * tuple_size
        return format

    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif action.nargs == OPTIONAL:
            result = '[%s]' % get_metavar(1)
        elif action.nargs == ZERO_OR_MORE:
            result = '[%s [%s ...]]' % get_metavar(2)
        elif action.nargs == ONE_OR_MORE:
            result = '%s [%s ...]' % get_metavar(2)
        elif action.nargs == REMAINDER:
            result = '...'
        elif action.nargs == PARSER:
            result = '%s ...' % get_metavar(1)
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    def _expand_help(self, action):
        params = dict(vars(action), prog=self._prog)
        for name in list(params):
            if params[name] is SUPPRESS:
                del params[name]
        for name in list(params):
            if hasattr(params[name], '__name__'):
                params[name] = params[name].__name__
        if params.get('choices') is not None:
            choices_str = ', '.join([str(c) for c in params['choices']])
            params['choices'] = choices_str
        return self._get_help_string(action) % params

    def _iter_indented_subactions(self, action):
        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            self._indent()
            for subaction in get_subactions():
                yield subaction
            self._dedent()

    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.fill(text, width, initial_indent=indent,
                                           subsequent_indent=indent)

    def _get_help_string(self, action):
        return action.help


class RawDescriptionHelpFormatter(HelpFormatter):
    """Help message formatter which retains any formatting in descriptions.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])


class RawTextHelpFormatter(RawDescriptionHelpFormatter):
    """Help message formatter which retains formatting of all help text.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _split_lines(self, text, width):
        return text.splitlines()


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not SUPPRESS:
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


# =====================
# Options and Arguments
# =====================

def _get_action_name(argument):
    if argument is None:
        return None
    elif argument.option_strings:
        return  '/'.join(argument.option_strings)
    elif argument.metavar not in (None, SUPPRESS):
        return argument.metavar
    elif argument.dest not in (None, SUPPRESS):
        return argument.dest
    else:
        return None


class ArgumentError(Exception):
    """An error from creating or using an argument (optional or positional).

    The string value of this exception is the message, augmented with
    information about the argument that caused it.
    """

    def __init__(self, argument, message):
        self.argument_name = _get_action_name(argument)
        self.message = message

    def __str__(self):
        if self.argument_name is None:
            format = '%(message)s'
        else:
            format = 'argument %(argument_name)s: %(message)s'
        return format % dict(message=self.message,
                             argument_name=self.argument_name)


class ArgumentTypeError(Exception):
    """An error from trying to convert a command line string to a type."""
    pass


# ==============
# Action classes
# ==============

class Action(_AttributeHolder):
    """Information about how to convert command line strings to Python objects.

    Action objects are used by an ArgumentParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - option_strings -- A list of command-line option strings which
            should be associated with this action.

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - const -- The value to be produced if the option is specified and the
            option uses an action that takes no values.

        - default -- The value to be produced if the option is not specified.

        - type -- The type which the command-line arguments should be converted
            to, should be one of 'string', 'int', 'float', 'complex' or a
            callable object that accepts a single string argument. If None,
            'string' is assumed.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - required -- True if the action must always be specified at the
            command line. This is only meaningful for optional command-line
            arguments.

        - help -- The help string describing the argument.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        self.option_strings = option_strings
        self.dest = dest
        self.nargs = nargs
        self.const = const
        self.default = default
        self.type = type
        self.choices = choices
        self.required = required
        self.help = help
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace, values, option_string=None):
        raise NotImplementedError(_('.__call__() not defined'))


class _StoreAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for store actions must be > 0; if you '
                             'have nothing to store, actions such as store '
                             'true or store const may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_StoreAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class _StoreConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_StoreConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, self.const)


class _StoreTrueAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=False,
                 required=False,
                 help=None):
        super(_StoreTrueAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=True,
            default=default,
            required=required,
            help=help)


class _StoreFalseAction(_StoreConstAction):

    def __init__(self,
                 option_strings,
                 dest,
                 default=True,
                 required=False,
                 help=None):
        super(_StoreFalseAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            const=False,
            default=default,
            required=required,
            help=help)


class _AppendAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if nargs == 0:
            raise ValueError('nargs for append actions must be > 0; if arg '
                             'strings are not supplying the value to append, '
                             'the append const action may be more appropriate')
        if const is not None and nargs != OPTIONAL:
            raise ValueError('nargs must be %r to supply const' % OPTIONAL)
        super(_AppendAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)


class _AppendConstAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 const,
                 default=None,
                 required=False,
                 help=None,
                 metavar=None):
        super(_AppendConstAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(self.const)
        setattr(namespace, self.dest, items)


class _CountAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 required=False,
                 help=None):
        super(_CountAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = _ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class _HelpAction(Action):

    def __init__(self,
                 option_strings,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit()


class _VersionAction(Action):

    def __init__(self,
                 option_strings,
                 version=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help=None):
        super(_VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser.exit(message=formatter.format_help())


class _SubParsersAction(Action):

    class _ChoicesPseudoAction(Action):

        def __init__(self, name, help):
            sup = super(_SubParsersAction._ChoicesPseudoAction, self)
            sup.__init__(option_strings=[], dest=name, help=help)

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest=SUPPRESS,
                 help=None,
                 metavar=None):

        self._prog_prefix = prog
        self._parser_class = parser_class
        self._name_parser_map = {}
        self._choices_actions = []

        super(_SubParsersAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=PARSER,
            choices=self._name_parser_map,
            help=help,
            metavar=metavar)

    def add_parser(self, name, **kwargs):
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = '%s %s' % (self._prog_prefix, name)

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help = kwargs.pop('help')
            choice_action = self._ChoicesPseudoAction(name, help)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser
        return parser

    def _get_subactions(self):
        return self._choices_actions

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            tup = parser_name, ', '.join(self._name_parser_map)
            msg = _('unknown parser %r (choices: %s)' % tup)
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        parser.parse_args(arg_strings, namespace)


# ==============
# Type classes
# ==============

class FileType(object):
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
    """

    def __init__(self, mode='r', bufsize=None):
        self._mode = mode
        self._bufsize = bufsize

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return _sys.stdin
            elif 'w' in self._mode:
                return _sys.stdout
            else:
                msg = _('argument "-" with mode %r' % self._mode)
                raise ValueError(msg)

        # all other arguments are used as file names
        if self._bufsize:
            return open(string, self._mode, self._bufsize)
        else:
            return open(string, self._mode)

    def __repr__(self):
        args = [self._mode, self._bufsize]
        args_str = ', '.join([repr(arg) for arg in args if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)

# ===========================
# Optional and Positional Parsing
# ===========================

class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)

    def __contains__(self, key):
        return key in self.__dict__


class _ActionsContainer(object):

    def __init__(self,
                 description,
                 prefix_chars,
                 argument_default,
                 conflict_handler):
        super(_ActionsContainer, self).__init__()

        self.description = description
        self.argument_default = argument_default
        self.prefix_chars = prefix_chars
        self.conflict_handler = conflict_handler

        # set up registries
        self._registries = {}

        # register actions
        self.register('action', None, _StoreAction)
        self.register('action', 'store', _StoreAction)
        self.register('action', 'store_const', _StoreConstAction)
        self.register('action', 'store_true', _StoreTrueAction)
        self.register('action', 'store_false', _StoreFalseAction)
        self.register('action', 'append', _AppendAction)
        self.register('action', 'append_const', _AppendConstAction)
        self.register('action', 'count', _CountAction)
        self.register('action', 'help', _HelpAction)
        self.register('action', 'version', _VersionAction)
        self.register('action', 'parsers', _SubParsersAction)

        # raise an exception if the conflict handler is invalid
        self._get_handler()

        # action storage
        self._actions = []
        self._option_string_actions = {}

        # groups
        self._action_groups = []
        self._mutually_exclusive_groups = []

        # defaults storage
        self._defaults = {}

        # determines whether an "option" looks like a negative number
        self._negative_number_matcher = _re.compile(r'^-\d+$|^-\d*\.\d+$')

        # whether or not there are any optionals that look like negative
        # numbers -- uses a list so it can be shared and edited
        self._has_negative_number_optionals = []

    # ====================
    # Registration methods
    # ====================
    def register(self, registry_name, value, object):
        registry = self._registries.setdefault(registry_name, {})
        registry[value] = object

    def _registry_get(self, registry_name, value, default=None):
        return self._registries[registry_name].get(value, default)

    # ==================================
    # Namespace default accessor methods
    # ==================================
    def set_defaults(self, **kwargs):
        self._defaults.update(kwargs)

        # if these defaults match any existing arguments, replace
        # the previous default on the object with the new one
        for action in self._actions:
            if action.dest in kwargs:
                action.default = kwargs[action.dest]

    def get_default(self, dest):
        for action in self._actions:
            if action.dest == dest and action.default is not None:
                return action.default
        return self._defaults.get(dest, None)


    # =======================
    # Adding argument actions
    # =======================
    def add_argument(self, *args, **kwargs):
        """
        add_argument(dest, ..., name=value, ...)
        add_argument(option_string, option_string, ..., name=value, ...)
        """

        # if no positional args are supplied or only one is supplied and
        # it doesn't look like an option string, parse a positional
        # argument
        chars = self.prefix_chars
        if not args or len(args) == 1 and args[0][0] not in chars:
            if args and 'dest' in kwargs:
                raise ValueError('dest supplied twice for positional argument')
            kwargs = self._get_positional_kwargs(*args, **kwargs)

        # otherwise, we're adding an optional argument
        else:
            kwargs = self._get_optional_kwargs(*args, **kwargs)

        # if no default was supplied, use the parser-level default
        if 'default' not in kwargs:
            dest = kwargs['dest']
            if dest in self._defaults:
                kwargs['default'] = self._defaults[dest]
            elif self.argument_default is not None:
                kwargs['default'] = self.argument_default

        # create the action object, and add it to the parser
        action_class = self._pop_action_class(kwargs)
        if not _callable(action_class):
            raise ValueError('unknown action "%s"' % action_class)
        action = action_class(**kwargs)

        # raise an error if the action type is not callable
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            raise ValueError('%r is not callable' % type_func)

        return self._add_action(action)

    def add_argument_group(self, *args, **kwargs):
        group = _ArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def add_mutually_exclusive_group(self, **kwargs):
        group = _MutuallyExclusiveGroup(self, **kwargs)
        self._mutually_exclusive_groups.append(group)
        return group

    def _add_action(self, action):
        # resolve any conflicts
        self._check_conflict(action)

        # add to actions list
        self._actions.append(action)
        action.container = self

        # index the action by any option strings it has
        for option_string in action.option_strings:
            self._option_string_actions[option_string] = action

        # set the flag if any option strings look like negative numbers
        for option_string in action.option_strings:
            if self._negative_number_matcher.match(option_string):
                if not self._has_negative_number_optionals:
                    self._has_negative_number_optionals.append(True)

        # return the created action
        return action

    def _remove_action(self, action):
        self._actions.remove(action)

    def _add_container_actions(self, container):
        # collect groups by titles
        title_group_map = {}
        for group in self._action_groups:
            if group.title in title_group_map:
                msg = _('cannot merge actions - two groups are named %r')
                raise ValueError(msg % (group.title))
            title_group_map[group.title] = group

        # map each action to its group
        group_map = {}
        for group in container._action_groups:

            # if a group with the title exists, use that, otherwise
            # create a new group matching the container's group
            if group.title not in title_group_map:
                title_group_map[group.title] = self.add_argument_group(
                    title=group.title,
                    description=group.description,
                    conflict_handler=group.conflict_handler)

            # map the actions to their new group
            for action in group._group_actions:
                group_map[action] = title_group_map[group.title]

        # add container's mutually exclusive groups
        # NOTE: if add_mutually_exclusive_group ever gains title= and
        # description= then this code will need to be expanded as above
        for group in container._mutually_exclusive_groups:
            mutex_group = self.add_mutually_exclusive_group(
                required=group.required)

            # map the actions to their new mutex group
            for action in group._group_actions:
                group_map[action] = mutex_group

        # add all actions to this container or their group
        for action in container._actions:
            group_map.get(action, self)._add_action(action)

    def _get_positional_kwargs(self, dest, **kwargs):
        # make sure required is not specified
        if 'required' in kwargs:
            msg = _("'required' is an invalid argument for positionals")
            raise TypeError(msg)

        # mark positional arguments as required if at least one is
        # always required
        if kwargs.get('nargs') not in [OPTIONAL, ZERO_OR_MORE]:
            kwargs['required'] = True
        if kwargs.get('nargs') == ZERO_OR_MORE and 'default' not in kwargs:
            kwargs['required'] = True

        # return the keyword arguments with no option strings
        return dict(kwargs, dest=dest, option_strings=[])

    def _get_optional_kwargs(self, *args, **kwargs):
        # determine short and long option strings
        option_strings = []
        long_option_strings = []
        for option_string in args:
            # error on strings that don't start with an appropriate prefix
            if not option_string[0] in self.prefix_chars:
                msg = _('invalid option string %r: '
                        'must start with a character %r')
                tup = option_string, self.prefix_chars
                raise ValueError(msg % tup)

            # strings starting with two prefix characters are long options
            option_strings.append(option_string)
            if option_string[0] in self.prefix_chars:
                if len(option_string) > 1:
                    if option_string[1] in self.prefix_chars:
                        long_option_strings.append(option_string)

        # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
        dest = kwargs.pop('dest', None)
        if dest is None:
            if long_option_strings:
                dest_option_string = long_option_strings[0]
            else:
                dest_option_string = option_strings[0]
            dest = dest_option_string.lstrip(self.prefix_chars)
            if not dest:
                msg = _('dest= is required for options like %r')
                raise ValueError(msg % option_string)
            dest = dest.replace('-', '_')

        # return the updated keyword arguments
        return dict(kwargs, dest=dest, option_strings=option_strings)

    def _pop_action_class(self, kwargs, default=None):
        action = kwargs.pop('action', default)
        return self._registry_get('action', action, action)

    def _get_handler(self):
        # determine function from conflict handler string
        handler_func_name = '_handle_conflict_%s' % self.conflict_handler
        try:
            return getattr(self, handler_func_name)
        except AttributeError:
            msg = _('invalid conflict_resolution value: %r')
            raise ValueError(msg % self.conflict_handler)

    def _check_conflict(self, action):

        # find all options that conflict with this option
        confl_optionals = []
        for option_string in action.option_strings:
            if option_string in self._option_string_actions:
                confl_optional = self._option_string_actions[option_string]
                confl_optionals.append((option_string, confl_optional))

        # resolve any conflicts
        if confl_optionals:
            conflict_handler = self._get_handler()
            conflict_handler(action, confl_optionals)

    def _handle_conflict_error(self, action, conflicting_actions):
        message = _('conflicting option string(s): %s')
        conflict_string = ', '.join([option_string
                                     for option_string, action
                                     in conflicting_actions])
        raise ArgumentError(action, message % conflict_string)

    def _handle_conflict_resolve(self, action, conflicting_actions):

        # remove all conflicting options
        for option_string, action in conflicting_actions:

            # remove the conflicting option
            action.option_strings.remove(option_string)
            self._option_string_actions.pop(option_string, None)

            # if the option now has no option string, remove it from the
            # container holding it
            if not action.option_strings:
                action.container._remove_action(action)


class _ArgumentGroup(_ActionsContainer):

    def __init__(self, container, title=None, description=None, **kwargs):
        # add any missing keyword arguments by checking the container
        update = kwargs.setdefault
        update('conflict_handler', container.conflict_handler)
        update('prefix_chars', container.prefix_chars)
        update('argument_default', container.argument_default)
        super_init = super(_ArgumentGroup, self).__init__
        super_init(description=description, **kwargs)

        # group attributes
        self.title = title
        self._group_actions = []

        # share most attributes with the container
        self._registries = container._registries
        self._actions = container._actions
        self._option_string_actions = container._option_string_actions
        self._defaults = container._defaults
        self._has_negative_number_optionals = \
            container._has_negative_number_optionals

    def _add_action(self, action):
        action = super(_ArgumentGroup, self)._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        super(_ArgumentGroup, self)._remove_action(action)
        self._group_actions.remove(action)


class _MutuallyExclusiveGroup(_ArgumentGroup):

    def __init__(self, container, required=False):
        super(_MutuallyExclusiveGroup, self).__init__(container)
        self.required = required
        self._container = container

    def _add_action(self, action):
        if action.required:
            msg = _('mutually exclusive arguments must be optional')
            raise ValueError(msg)
        action = self._container._add_action(action)
        self._group_actions.append(action)
        return action

    def _remove_action(self, action):
        self._container._remove_action(action)
        self._group_actions.remove(action)


class ArgumentParser(_AttributeHolder, _ActionsContainer):
    """Object for parsing command line strings into Python objects.

    Keyword Arguments:
        - prog -- The name of the program (default: sys.argv[0])
        - usage -- A usage message (default: auto-generated from arguments)
        - description -- A description of what the program does
        - epilog -- Text following the argument descriptions
        - parents -- Parsers whose arguments should be copied into this one
        - formatter_class -- HelpFormatter class for printing help messages
        - prefix_chars -- Characters that prefix optional arguments
        - fromfile_prefix_chars -- Characters that prefix files containing
            additional arguments
        - argument_default -- The default value for all arguments
        - conflict_handler -- String indicating how to handle conflicts
        - add_help -- Add a -h/-help option
    """

    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 formatter_class=HelpFormatter,
                 prefix_chars='-',
                 fromfile_prefix_chars=None,
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True):

        if version is not None:
            import warnings
            warnings.warn(
                """The "version" argument to ArgumentParser is deprecated. """
                """Please use """
                """"add_argument(..., action='version', version="N", ...)" """
                """instead""", DeprecationWarning)

        superinit = super(ArgumentParser, self).__init__
        superinit(description=description,
                  prefix_chars=prefix_chars,
                  argument_default=argument_default,
                  conflict_handler=conflict_handler)

        # default setting for prog
        if prog is None:
            prog = _os.path.basename(_sys.argv[0])

        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version
        self.formatter_class = formatter_class
        self.fromfile_prefix_chars = fromfile_prefix_chars
        self.add_help = add_help

        add_group = self.add_argument_group
        self._positionals = add_group(_('positional arguments'))
        self._optionals = add_group(_('optional arguments'))
        self._subparsers = None

        # register types
        def identity(string):
            return string
        self.register('type', None, identity)

        # add help and version arguments if necessary
        # (using explicit default to override global argument_default)
        if self.add_help:
            self.add_argument(
                '-h', '--help', action='help', default=SUPPRESS,
                help=_('show this help message and exit'))
        if self.version:
            self.add_argument(
                '-v', '--version', action='version', default=SUPPRESS,
                version=self.version,
                help=_("show program's version number and exit"))

        # add parent arguments and defaults
        for parent in parents:
            self._add_container_actions(parent)
            try:
                defaults = parent._defaults
            except AttributeError:
                pass
            else:
                self._defaults.update(defaults)

    # =======================
    # Pretty __repr__ methods
    # =======================
    def _get_kwargs(self):
        names = [
            'prog',
            'usage',
            'description',
            'version',
            'formatter_class',
            'conflict_handler',
            'add_help',
        ]
        return [(name, getattr(self, name)) for name in names]

    # ==================================
    # Optional/Positional adding methods
    # ==================================
    def add_subparsers(self, **kwargs):
        if self._subparsers is not None:
            self.error(_('cannot have multiple subparser arguments'))

        # add the parser class to the arguments if it's not present
        kwargs.setdefault('parser_class', type(self))

        if 'title' in kwargs or 'description' in kwargs:
            title = _(kwargs.pop('title', 'subcommands'))
            description = _(kwargs.pop('description', None))
            self._subparsers = self.add_argument_group(title, description)
        else:
            self._subparsers = self._positionals

        # prog defaults to the usage message of this parser, skipping
        # optional arguments and with no "usage:" prefix
        if kwargs.get('prog') is None:
            formatter = self._get_formatter()
            positionals = self._get_positional_actions()
            groups = self._mutually_exclusive_groups
            formatter.add_usage(self.usage, positionals, groups, '')
            kwargs['prog'] = formatter.format_help().strip()

        # create the parsers action and add it to the positionals list
        parsers_class = self._pop_action_class(kwargs, 'parsers')
        action = parsers_class(option_strings=[], **kwargs)
        self._subparsers._add_action(action)

        # return the created parsers action
        return action

    def _add_action(self, action):
        if action.option_strings:
            self._optionals._add_action(action)
        else:
            self._positionals._add_action(action)
        return action

    def _get_optional_actions(self):
        return [action
                for action in self._actions
                if action.option_strings]

    def _get_positional_actions(self):
        return [action
                for action in self._actions
                if not action.option_strings]

    # =====================================
    # Command line argument parsing methods
    # =====================================
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _('unrecognized arguments: %s')
            self.error(msg % ' '.join(argv))
        return args

    def parse_known_args(self, args=None, namespace=None):
        # args default to the system args
        if args is None:
            args = _sys.argv[1:]

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not SUPPRESS:
                        default = action.default
                        if isinstance(action.default, _basestring):
                            default = self._get_value(action, default)
                        setattr(namespace, action.dest, default)

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self._defaults[dest])

        # parse the arguments and exit if there are any errors
        try:
            return self._parse_known_args(args, namespace)
        except ArgumentError:
            err = _sys.exc_info()[1]
            self.error(str(err))

    def _parse_known_args(self, arg_strings, namespace):
        # replace arg strings that are file references
        if self.fromfile_prefix_chars is not None:
            arg_strings = self._read_args_from_files(arg_strings)

        # map all mutually exclusive arguments to the other arguments
        # they can't occur with
        action_conflicts = {}
        for mutex_group in self._mutually_exclusive_groups:
            group_actions = mutex_group._group_actions
            for i, mutex_action in enumerate(mutex_group._group_actions):
                conflicts = action_conflicts.setdefault(mutex_action, [])
                conflicts.extend(group_actions[:i])
                conflicts.extend(group_actions[i + 1:])

        # find all option indices, and determine the arg_string_pattern
        # which has an 'O' if there is an option at an index,
        # an 'A' if there is an argument, or a '-' if there is a '--'
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuple = self._parse_optional(arg_string)
                if option_tuple is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuple
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)

        # converts arg strings to the appropriate and then takes the action
        seen_actions = _set()
        seen_non_default_actions = _set()

        def take_action(action, argument_strings, option_string=None):
            seen_actions.add(action)
            argument_values = self._get_values(action, argument_strings)

            # error if this argument is not allowed with other previously
            # seen arguments, assuming that actions that use the default
            # value don't really count as "present"
            if argument_values is not action.default:
                seen_non_default_actions.add(action)
                for conflict_action in action_conflicts.get(action, []):
                    if conflict_action in seen_non_default_actions:
                        msg = _('not allowed with argument %s')
                        action_name = _get_action_name(conflict_action)
                        raise ArgumentError(action, msg % action_name)

            # take the action if we didn't receive a SUPPRESS value
            # (e.g. from a default)
            if argument_values is not SUPPRESS:
                action(self, namespace, argument_values, option_string)

        # function to convert arg_strings into an optional action
        def consume_optional(start_index):

            # get the optional identified at this index
            option_tuple = option_string_indices[start_index]
            action, option_string, explicit_arg = option_tuple

            # identify additional optionals in the same arg string
            # (e.g. -xyz is the same as -x -y -z if no args are required)
            match_argument = self._match_argument
            action_tuples = []
            while True:

                # if we found no optional action, skip it
                if action is None:
                    extras.append(arg_strings[start_index])
                    return start_index + 1

                # if there is an explicit argument, try to match the
                # optional's string arguments to only this
                if explicit_arg is not None:
                    arg_count = match_argument(action, 'A')

                    # if the action is a single-dash option and takes no
                    # arguments, try to parse more single-dash options out
                    # of the tail of the option string
                    chars = self.prefix_chars
                    if arg_count == 0 and option_string[1] not in chars:
                        action_tuples.append((action, [], option_string))
                        for char in self.prefix_chars:
                            option_string = char + explicit_arg[0]
                            explicit_arg = explicit_arg[1:] or None
                            optionals_map = self._option_string_actions
                            if option_string in optionals_map:
                                action = optionals_map[option_string]
                                break
                        else:
                            msg = _('ignored explicit argument %r')
                            raise ArgumentError(action, msg % explicit_arg)

                    # if the action expect exactly one argument, we've
                    # successfully matched the option; exit the loop
                    elif arg_count == 1:
                        stop = start_index + 1
                        args = [explicit_arg]
                        action_tuples.append((action, args, option_string))
                        break

                    # error if a double-dash option did not use the
                    # explicit argument
                    else:
                        msg = _('ignored explicit argument %r')
                        raise ArgumentError(action, msg % explicit_arg)

                # if there is no explicit argument, try to match the
                # optional's string arguments with the following strings
                # if successful, exit the loop
                else:
                    start = start_index + 1
                    selected_patterns = arg_strings_pattern[start:]
                    arg_count = match_argument(action, selected_patterns)
                    stop = start + arg_count
                    args = arg_strings[start:stop]
                    action_tuples.append((action, args, option_string))
                    break

            # add the Optional to the list and return the index at which
            # the Optional's string args stopped
            assert action_tuples
            for action, args, option_string in action_tuples:
                take_action(action, args, option_string)
            return stop

        # the list of Positionals left to be parsed; this is modified
        # by consume_positionals()
        positionals = self._get_positional_actions()

        # function to convert arg_strings into positional actions
        def consume_positionals(start_index):
            # match as many Positionals as possible
            match_partial = self._match_arguments_partial
            selected_pattern = arg_strings_pattern[start_index:]
            arg_counts = match_partial(positionals, selected_pattern)

            # slice off the appropriate arg strings for each Positional
            # and add the Positional and its args to the list
            for action, arg_count in zip(positionals, arg_counts):
                args = arg_strings[start_index: start_index + arg_count]
                start_index += arg_count
                take_action(action, args)

            # slice off the Positionals that we just parsed and return the
            # index at which the Positionals' string args stopped
            positionals[:] = positionals[len(arg_counts):]
            return start_index

        # consume Positionals and Optionals alternately, until we have
        # passed the last option string
        extras = []
        start_index = 0
        if option_string_indices:
            max_option_string_index = max(option_string_indices)
        else:
            max_option_string_index = -1
        while start_index <= max_option_string_index:

            # consume any Positionals preceding the next option
            next_option_string_index = min([
                index
                for index in option_string_indices
                if index >= start_index])
            if start_index != next_option_string_index:
                positionals_end_index = consume_positionals(start_index)

                # only try to parse the next optional if we didn't consume
                # the option string during the positionals parsing
                if positionals_end_index > start_index:
                    start_index = positionals_end_index
                    continue
                else:
                    start_index = positionals_end_index

            # if we consumed all the positionals we could and we're not
            # at the index of an option string, there were extra arguments
            if start_index not in option_string_indices:
                strings = arg_strings[start_index:next_option_string_index]
                extras.extend(strings)
                start_index = next_option_string_index

            # consume the next optional and any arguments for it
            start_index = consume_optional(start_index)

        # consume any positionals following the last Optional
        stop_index = consume_positionals(start_index)

        # if we didn't consume all the argument strings, there were extras
        extras.extend(arg_strings[stop_index:])

        # if we didn't use all the Positional objects, there were too few
        # arg strings supplied.
        if positionals:
            self.error(_('too few arguments'))

        # make sure all required actions were present
        for action in self._actions:
            if action.required:
                if action not in seen_actions:
                    name = _get_action_name(action)
                    self.error(_('argument %s is required') % name)

        # make sure all required groups had one option present
        for group in self._mutually_exclusive_groups:
            if group.required:
                for action in group._group_actions:
                    if action in seen_non_default_actions:
                        break

                # if no actions were used, report the error
                else:
                    names = [_get_action_name(action)
                             for action in group._group_actions
                             if action.help is not SUPPRESS]
                    msg = _('one of the arguments %s is required')
                    self.error(msg % ' '.join(names))

        # return the updated namespace and the extra arguments
        return namespace, extras

    def _read_args_from_files(self, arg_strings):
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:

            # for regular arguments, just add them back into the list
            if arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                try:
                    args_file = open(arg_string[1:])
                    try:
                        arg_strings = []
                        for arg_line in args_file.read().splitlines():
                            for arg in self.convert_arg_line_to_args(arg_line):
                                arg_strings.append(arg)
                        arg_strings = self._read_args_from_files(arg_strings)
                        new_arg_strings.extend(arg_strings)
                    finally:
                        args_file.close()
                except IOError:
                    err = _sys.exc_info()[1]
                    self.error(str(err))

        # return the modified argument list
        return new_arg_strings

    def convert_arg_line_to_args(self, arg_line):
        return [arg_line]

    def _match_argument(self, action, arg_strings_pattern):
        # match the pattern for this action to the arg strings
        nargs_pattern = self._get_nargs_pattern(action)
        match = _re.match(nargs_pattern, arg_strings_pattern)

        # raise an exception if we weren't able to find a match
        if match is None:
            nargs_errors = {
                None: _('expected one argument'),
                OPTIONAL: _('expected at most one argument'),
                ONE_OR_MORE: _('expected at least one argument'),
            }
            default = _('expected %s argument(s)') % action.nargs
            msg = nargs_errors.get(action.nargs, default)
            raise ArgumentError(action, msg)

        # return the number of arguments matched
        return len(match.group(1))

    def _match_arguments_partial(self, actions, arg_strings_pattern):
        # progressively shorten the actions list by slicing off the
        # final actions until we find a match
        result = []
        for i in range(len(actions), 0, -1):
            actions_slice = actions[:i]
            pattern = ''.join([self._get_nargs_pattern(action)
                               for action in actions_slice])
            match = _re.match(pattern, arg_strings_pattern)
            if match is not None:
                result.extend([len(string) for string in match.groups()])
                break

        # return the list of arg string counts
        return result

    def _parse_optional(self, arg_string):
        # if it's an empty string, it was meant to be a positional
        if not arg_string:
            return None

        # if it doesn't start with a prefix, it was meant to be positional
        if not arg_string[0] in self.prefix_chars:
            return None

        # if the option string is present in the parser, return the action
        if arg_string in self._option_string_actions:
            action = self._option_string_actions[arg_string]
            return action, arg_string, None

        # if it's just a single character, it was meant to be positional
        if len(arg_string) == 1:
            return None

        # if the option string before the "=" is present, return the action
        if '=' in arg_string:
            option_string, explicit_arg = arg_string.split('=', 1)
            if option_string in self._option_string_actions:
                action = self._option_string_actions[option_string]
                return action, option_string, explicit_arg

        # search through all possible prefixes of the option string
        # and all actions in the parser for possible interpretations
        option_tuples = self._get_option_tuples(arg_string)

        # if multiple actions match, the option string was ambiguous
        if len(option_tuples) > 1:
            options = ', '.join([option_string
                for action, option_string, explicit_arg in option_tuples])
            tup = arg_string, options
            self.error(_('ambiguous option: %s could match %s') % tup)

        # if exactly one action matched, this segmentation is good,
        # so return the parsed action
        elif len(option_tuples) == 1:
            option_tuple, = option_tuples
            return option_tuple

        # if it was not found as an option, but it looks like a negative
        # number, it was meant to be positional
        # unless there are negative-number-like options
        if self._negative_number_matcher.match(arg_string):
            if not self._has_negative_number_optionals:
                return None

        # if it contains a space, it was meant to be a positional
        if ' ' in arg_string:
            return None

        # it was meant to be an optional but there is no such option
        # in this parser (though it might be a valid option in a subparser)
        return None, arg_string, None

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '='
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if '=' in option_string:
                option_prefix, explicit_arg = option_string.split('=', 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            self.error(_('unexpected option string: %s') % option_string)

        # return the collected option tuples
        return result

    def _get_nargs_pattern(self, action):
        # in all examples below, we have to allow for '--' args
        # which are represented as '-' in the pattern
        nargs = action.nargs

        # the default (None) is assumed to be a single argument
        if nargs is None:
            nargs_pattern = '(-*A-*)'

        # allow zero or one arguments
        elif nargs == OPTIONAL:
            nargs_pattern = '(-*A?-*)'

        # allow zero or more arguments
        elif nargs == ZERO_OR_MORE:
            nargs_pattern = '(-*[A-]*)'

        # allow one or more arguments
        elif nargs == ONE_OR_MORE:
            nargs_pattern = '(-*A[A-]*)'

        # allow any number of options or arguments
        elif nargs == REMAINDER:
            nargs_pattern = '([-AO]*)'

        # allow one argument followed by any number of options or arguments
        elif nargs == PARSER:
            nargs_pattern = '(-*A[-AO]*)'

        # all others should be integers
        else:
            nargs_pattern = '(-*%s-*)' % '-*'.join('A' * nargs)

        # if this is an optional action, -- is not allowed
        if action.option_strings:
            nargs_pattern = nargs_pattern.replace('-*', '')
            nargs_pattern = nargs_pattern.replace('-', '')

        # return the pattern
        return nargs_pattern

    # ========================
    # Value conversion methods
    # ========================
    def _get_values(self, action, arg_strings):
        # for everything but PARSER args, strip out '--'
        if action.nargs not in [PARSER, REMAINDER]:
            arg_strings = [s for s in arg_strings if s != '--']

        # optional argument produces a default when not present
        if not arg_strings and action.nargs == OPTIONAL:
            if action.option_strings:
                value = action.const
            else:
                value = action.default
            if isinstance(value, _basestring):
                value = self._get_value(action, value)
                self._check_value(action, value)

        # when nargs='*' on a positional, if there were no command-line
        # args, use the default if it is anything other than None
        elif (not arg_strings and action.nargs == ZERO_OR_MORE and
              not action.option_strings):
            if action.default is not None:
                value = action.default
            else:
                value = arg_strings
            self._check_value(action, value)

        # single argument or optional argument produces a single value
        elif len(arg_strings) == 1 and action.nargs in [None, OPTIONAL]:
            arg_string, = arg_strings
            value = self._get_value(action, arg_string)
            self._check_value(action, value)

        # REMAINDER arguments convert all values, checking none
        elif action.nargs == REMAINDER:
            value = [self._get_value(action, v) for v in arg_strings]

        # PARSER arguments convert all values, but check only the first
        elif action.nargs == PARSER:
            value = [self._get_value(action, v) for v in arg_strings]
            self._check_value(action, value[0])

        # all other types of nargs produce a list
        else:
            value = [self._get_value(action, v) for v in arg_strings]
            for v in value:
                self._check_value(action, v)

        # return the converted value
        return value

    def _get_value(self, action, arg_string):
        type_func = self._registry_get('type', action.type, action.type)
        if not _callable(type_func):
            msg = _('%r is not callable')
            raise ArgumentError(action, msg % type_func)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except ArgumentTypeError:
            name = getattr(action.type, '__name__', repr(action.type))
            msg = str(_sys.exc_info()[1])
            raise ArgumentError(action, msg)

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError):
            name = getattr(action.type, '__name__', repr(action.type))
            msg = _('invalid %s value: %r')
            raise ArgumentError(action, msg % (name, arg_string))

        # return the converted value
        return result

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join(map(repr, action.choices))
            msg = _('invalid choice: %r (choose from %s)') % tup
            raise ArgumentError(action, msg)

    # =======================
    # Help-formatting methods
    # =======================
    def format_usage(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        return formatter.format_help()

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def format_version(self):
        import warnings
        warnings.warn(
            'The format_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        formatter = self._get_formatter()
        formatter.add_text(self.version)
        return formatter.format_help()

    def _get_formatter(self):
        return self.formatter_class(prog=self.prog)

    # =====================
    # Help-printing methods
    # =====================
    def print_usage(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        if file is None:
            file = _sys.stdout
        self._print_message(self.format_help(), file)

    def print_version(self, file=None):
        import warnings
        warnings.warn(
            'The print_version method is deprecated -- the "version" '
            'argument to ArgumentParser is no longer supported.',
            DeprecationWarning)
        self._print_message(self.format_version(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = _sys.stderr
            file.write(message)

    # ===============
    # Exiting methods
    # ===============
    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, _sys.stderr)
        _sys.exit(status)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(_sys.stderr)
        self.exit(2, _('%s: error: %s\n') % (self.prog, message))

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Core locale representation and locale data access."""

import os
import pickle

from babel import localedata

__all__ = ['UnknownLocaleError', 'Locale', 'default_locale', 'negotiate_locale',
           'parse_locale']
__docformat__ = 'restructuredtext en'

_global_data = None

def get_global(key):
    """Return the dictionary for the given key in the global data.
    
    The global data is stored in the ``babel/global.dat`` file and contains
    information independent of individual locales.
    
    >>> get_global('zone_aliases')['UTC']
    'Etc/GMT'
    >>> get_global('zone_territories')['Europe/Berlin']
    'DE'
    
    :param key: the data key
    :return: the dictionary found in the global data under the given key
    :rtype: `dict`
    :since: version 0.9
    """
    global _global_data
    if _global_data is None:
        dirname = os.path.join(os.path.dirname(__file__))
        filename = os.path.join(dirname, 'global.dat')
        fileobj = open(filename, 'rb')
        try:
            _global_data = pickle.load(fileobj)
        finally:
            fileobj.close()
    return _global_data.get(key, {})


LOCALE_ALIASES = {
    'ar': 'ar_SY', 'bg': 'bg_BG', 'bs': 'bs_BA', 'ca': 'ca_ES', 'cs': 'cs_CZ', 
    'da': 'da_DK', 'de': 'de_DE', 'el': 'el_GR', 'en': 'en_US', 'es': 'es_ES', 
    'et': 'et_EE', 'fa': 'fa_IR', 'fi': 'fi_FI', 'fr': 'fr_FR', 'gl': 'gl_ES', 
    'he': 'he_IL', 'hu': 'hu_HU', 'id': 'id_ID', 'is': 'is_IS', 'it': 'it_IT', 
    'ja': 'ja_JP', 'km': 'km_KH', 'ko': 'ko_KR', 'lt': 'lt_LT', 'lv': 'lv_LV', 
    'mk': 'mk_MK', 'nl': 'nl_NL', 'nn': 'nn_NO', 'no': 'nb_NO', 'pl': 'pl_PL', 
    'pt': 'pt_PT', 'ro': 'ro_RO', 'ru': 'ru_RU', 'sk': 'sk_SK', 'sl': 'sl_SI', 
    'sv': 'sv_SE', 'th': 'th_TH', 'tr': 'tr_TR', 'uk': 'uk_UA'
}


class UnknownLocaleError(Exception):
    """Exception thrown when a locale is requested for which no locale data
    is available.
    """

    def __init__(self, identifier):
        """Create the exception.
        
        :param identifier: the identifier string of the unsupported locale
        """
        Exception.__init__(self, 'unknown locale %r' % identifier)
        self.identifier = identifier


class Locale(object):
    """Representation of a specific locale.
    
    >>> locale = Locale('en', 'US')
    >>> repr(locale)
    '<Locale "en_US">'
    >>> locale.display_name
    u'English (United States)'
    
    A `Locale` object can also be instantiated from a raw locale string:
    
    >>> locale = Locale.parse('en-US', sep='-')
    >>> repr(locale)
    '<Locale "en_US">'
    
    `Locale` objects provide access to a collection of locale data, such as
    territory and language names, number and date format patterns, and more:
    
    >>> locale.number_symbols['decimal']
    u'.'
    
    If a locale is requested for which no locale data is available, an
    `UnknownLocaleError` is raised:
    
    >>> Locale.parse('en_DE')
    Traceback (most recent call last):
        ...
    UnknownLocaleError: unknown locale 'en_DE'
    
    :see: `IETF RFC 3066 <http://www.ietf.org/rfc/rfc3066.txt>`_
    """

    def __init__(self, language, territory=None, script=None, variant=None):
        """Initialize the locale object from the given identifier components.
        
        >>> locale = Locale('en', 'US')
        >>> locale.language
        'en'
        >>> locale.territory
        'US'
        
        :param language: the language code
        :param territory: the territory (country or region) code
        :param script: the script code
        :param variant: the variant code
        :raise `UnknownLocaleError`: if no locale data is available for the
                                     requested locale
        """
        self.language = language
        self.territory = territory
        self.script = script
        self.variant = variant
        self.__data = None

        identifier = str(self)
        if not localedata.exists(identifier):
            raise UnknownLocaleError(identifier)

    def default(cls, category=None, aliases=LOCALE_ALIASES):
        """Return the system default locale for the specified category.
        
        >>> for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE']:
        ...     os.environ[name] = ''
        >>> os.environ['LANG'] = 'fr_FR.UTF-8'
        >>> Locale.default('LC_MESSAGES')
        <Locale "fr_FR">

        :param category: one of the ``LC_XXX`` environment variable names
        :param aliases: a dictionary of aliases for locale identifiers
        :return: the value of the variable, or any of the fallbacks
                 (``LANGUAGE``, ``LC_ALL``, ``LC_CTYPE``, and ``LANG``)
        :rtype: `Locale`
        :see: `default_locale`
        """
        return cls(default_locale(category, aliases=aliases))
    default = classmethod(default)

    def negotiate(cls, preferred, available, sep='_', aliases=LOCALE_ALIASES):
        """Find the best match between available and requested locale strings.
        
        >>> Locale.negotiate(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
        <Locale "de_DE">
        >>> Locale.negotiate(['de_DE', 'en_US'], ['en', 'de'])
        <Locale "de">
        >>> Locale.negotiate(['de_DE', 'de'], ['en_US'])
        
        You can specify the character used in the locale identifiers to separate
        the differnet components. This separator is applied to both lists. Also,
        case is ignored in the comparison:
        
        >>> Locale.negotiate(['de-DE', 'de'], ['en-us', 'de-de'], sep='-')
        <Locale "de_DE">
        
        :param preferred: the list of locale identifers preferred by the user
        :param available: the list of locale identifiers available
        :param aliases: a dictionary of aliases for locale identifiers
        :return: the `Locale` object for the best match, or `None` if no match
                 was found
        :rtype: `Locale`
        :see: `negotiate_locale`
        """
        identifier = negotiate_locale(preferred, available, sep=sep,
                                      aliases=aliases)
        if identifier:
            return Locale.parse(identifier, sep=sep)
    negotiate = classmethod(negotiate)

    def parse(cls, identifier, sep='_'):
        """Create a `Locale` instance for the given locale identifier.
        
        >>> l = Locale.parse('de-DE', sep='-')
        >>> l.display_name
        u'Deutsch (Deutschland)'
        
        If the `identifier` parameter is not a string, but actually a `Locale`
        object, that object is returned:
        
        >>> Locale.parse(l)
        <Locale "de_DE">
        
        :param identifier: the locale identifier string
        :param sep: optional component separator
        :return: a corresponding `Locale` instance
        :rtype: `Locale`
        :raise `ValueError`: if the string does not appear to be a valid locale
                             identifier
        :raise `UnknownLocaleError`: if no locale data is available for the
                                     requested locale
        :see: `parse_locale`
        """
        if isinstance(identifier, basestring):
            return cls(*parse_locale(identifier, sep=sep))
        return identifier
    parse = classmethod(parse)

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return '<Locale "%s">' % str(self)

    def __str__(self):
        return '_'.join(filter(None, [self.language, self.script,
                                      self.territory, self.variant]))

    def _data(self):
        if self.__data is None:
            self.__data = localedata.LocaleDataDict(localedata.load(str(self)))
        return self.__data
    _data = property(_data)

    def get_display_name(self, locale=None):
        """Return the display name of the locale using the given locale.
        
        The display name will include the language, territory, script, and
        variant, if those are specified.
        
        >>> Locale('zh', 'CN', script='Hans').get_display_name('en')
        u'Chinese (Simplified Han, China)'
        
        :param locale: the locale to use
        :return: the display name
        """
        if locale is None:
            locale = self
        locale = Locale.parse(locale)
        retval = locale.languages.get(self.language)
        if self.territory or self.script or self.variant:
            details = []
            if self.script:
                details.append(locale.scripts.get(self.script))
            if self.territory:
                details.append(locale.territories.get(self.territory))
            if self.variant:
                details.append(locale.variants.get(self.variant))
            details = filter(None, details)
            if details:
                retval += ' (%s)' % u', '.join(details)
        return retval

    display_name = property(get_display_name, doc="""\
        The localized display name of the locale.
        
        >>> Locale('en').display_name
        u'English'
        >>> Locale('en', 'US').display_name
        u'English (United States)'
        >>> Locale('sv').display_name
        u'svenska'
        
        :type: `unicode`
        """)

    def english_name(self):
        return self.get_display_name(Locale('en'))
    english_name = property(english_name, doc="""\
        The english display name of the locale.
        
        >>> Locale('de').english_name
        u'German'
        >>> Locale('de', 'DE').english_name
        u'German (Germany)'
        
        :type: `unicode`
        """)

    #{ General Locale Display Names

    def languages(self):
        return self._data['languages']
    languages = property(languages, doc="""\
        Mapping of language codes to translated language names.
        
        >>> Locale('de', 'DE').languages['ja']
        u'Japanisch'
        
        :type: `dict`
        :see: `ISO 639 <http://www.loc.gov/standards/iso639-2/>`_
        """)

    def scripts(self):
        return self._data['scripts']
    scripts = property(scripts, doc="""\
        Mapping of script codes to translated script names.
        
        >>> Locale('en', 'US').scripts['Hira']
        u'Hiragana'
        
        :type: `dict`
        :see: `ISO 15924 <http://www.evertype.com/standards/iso15924/>`_
        """)

    def territories(self):
        return self._data['territories']
    territories = property(territories, doc="""\
        Mapping of script codes to translated script names.
        
        >>> Locale('es', 'CO').territories['DE']
        u'Alemania'
        
        :type: `dict`
        :see: `ISO 3166 <http://www.iso.org/iso/en/prods-services/iso3166ma/>`_
        """)

    def variants(self):
        return self._data['variants']
    variants = property(variants, doc="""\
        Mapping of script codes to translated script names.
        
        >>> Locale('de', 'DE').variants['1901']
        u'Alte deutsche Rechtschreibung'
        
        :type: `dict`
        """)

    #{ Number Formatting

    def currencies(self):
        return self._data['currency_names']
    currencies = property(currencies, doc="""\
        Mapping of currency codes to translated currency names.
        
        >>> Locale('en').currencies['COP']
        u'Colombian Peso'
        >>> Locale('de', 'DE').currencies['COP']
        u'Kolumbianischer Peso'
        
        :type: `dict`
        """)

    def currency_symbols(self):
        return self._data['currency_symbols']
    currency_symbols = property(currency_symbols, doc="""\
        Mapping of currency codes to symbols.
        
        >>> Locale('en', 'US').currency_symbols['USD']
        u'$'
        >>> Locale('es', 'CO').currency_symbols['USD']
        u'US$'
        
        :type: `dict`
        """)

    def number_symbols(self):
        return self._data['number_symbols']
    number_symbols = property(number_symbols, doc="""\
        Symbols used in number formatting.
        
        >>> Locale('fr', 'FR').number_symbols['decimal']
        u','
        
        :type: `dict`
        """)

    def decimal_formats(self):
        return self._data['decimal_formats']
    decimal_formats = property(decimal_formats, doc="""\
        Locale patterns for decimal number formatting.
        
        >>> Locale('en', 'US').decimal_formats[None]
        <NumberPattern u'#,##0.###'>
        
        :type: `dict`
        """)

    def currency_formats(self):
        return self._data['currency_formats']
    currency_formats = property(currency_formats, doc=r"""\
        Locale patterns for currency number formatting.
        
        >>> print Locale('en', 'US').currency_formats[None]
        <NumberPattern u'\xa4#,##0.00'>
        
        :type: `dict`
        """)

    def percent_formats(self):
        return self._data['percent_formats']
    percent_formats = property(percent_formats, doc="""\
        Locale patterns for percent number formatting.
        
        >>> Locale('en', 'US').percent_formats[None]
        <NumberPattern u'#,##0%'>
        
        :type: `dict`
        """)

    def scientific_formats(self):
        return self._data['scientific_formats']
    scientific_formats = property(scientific_formats, doc="""\
        Locale patterns for scientific number formatting.
        
        >>> Locale('en', 'US').scientific_formats[None]
        <NumberPattern u'#E0'>
        
        :type: `dict`
        """)

    #{ Calendar Information and Date Formatting

    def periods(self):
        return self._data['periods']
    periods = property(periods, doc="""\
        Locale display names for day periods (AM/PM).
        
        >>> Locale('en', 'US').periods['am']
        u'AM'
        
        :type: `dict`
        """)

    def days(self):
        return self._data['days']
    days = property(days, doc="""\
        Locale display names for weekdays.
        
        >>> Locale('de', 'DE').days['format']['wide'][3]
        u'Donnerstag'
        
        :type: `dict`
        """)

    def months(self):
        return self._data['months']
    months = property(months, doc="""\
        Locale display names for months.
        
        >>> Locale('de', 'DE').months['format']['wide'][10]
        u'Oktober'
        
        :type: `dict`
        """)

    def quarters(self):
        return self._data['quarters']
    quarters = property(quarters, doc="""\
        Locale display names for quarters.
        
        >>> Locale('de', 'DE').quarters['format']['wide'][1]
        u'1. Quartal'
        
        :type: `dict`
        """)

    def eras(self):
        return self._data['eras']
    eras = property(eras, doc="""\
        Locale display names for eras.
        
        >>> Locale('en', 'US').eras['wide'][1]
        u'Anno Domini'
        >>> Locale('en', 'US').eras['abbreviated'][0]
        u'BC'
        
        :type: `dict`
        """)

    def time_zones(self):
        return self._data['time_zones']
    time_zones = property(time_zones, doc="""\
        Locale display names for time zones.
        
        >>> Locale('en', 'US').time_zones['Europe/London']['long']['daylight']
        u'British Summer Time'
        >>> Locale('en', 'US').time_zones['America/St_Johns']['city']
        u"St. John's"
        
        :type: `dict`
        """)

    def meta_zones(self):
        return self._data['meta_zones']
    meta_zones = property(meta_zones, doc="""\
        Locale display names for meta time zones.
        
        Meta time zones are basically groups of different Olson time zones that
        have the same GMT offset and daylight savings time.
        
        >>> Locale('en', 'US').meta_zones['Europe_Central']['long']['daylight']
        u'Central European Summer Time'
        
        :type: `dict`
        :since: version 0.9
        """)

    def zone_formats(self):
        return self._data['zone_formats']
    zone_formats = property(zone_formats, doc=r"""\
        Patterns related to the formatting of time zones.
        
        >>> Locale('en', 'US').zone_formats['fallback']
        u'%(1)s (%(0)s)'
        >>> Locale('pt', 'BR').zone_formats['region']
        u'Hor\xe1rio %s'
        
        :type: `dict`
        :since: version 0.9
        """)

    def first_week_day(self):
        return self._data['week_data']['first_day']
    first_week_day = property(first_week_day, doc="""\
        The first day of a week, with 0 being Monday.
        
        >>> Locale('de', 'DE').first_week_day
        0
        >>> Locale('en', 'US').first_week_day
        6
        
        :type: `int`
        """)

    def weekend_start(self):
        return self._data['week_data']['weekend_start']
    weekend_start = property(weekend_start, doc="""\
        The day the weekend starts, with 0 being Monday.
        
        >>> Locale('de', 'DE').weekend_start
        5
        
        :type: `int`
        """)

    def weekend_end(self):
        return self._data['week_data']['weekend_end']
    weekend_end = property(weekend_end, doc="""\
        The day the weekend ends, with 0 being Monday.
        
        >>> Locale('de', 'DE').weekend_end
        6
        
        :type: `int`
        """)

    def min_week_days(self):
        return self._data['week_data']['min_days']
    min_week_days = property(min_week_days, doc="""\
        The minimum number of days in a week so that the week is counted as the
        first week of a year or month.
        
        >>> Locale('de', 'DE').min_week_days
        4
        
        :type: `int`
        """)

    def date_formats(self):
        return self._data['date_formats']
    date_formats = property(date_formats, doc="""\
        Locale patterns for date formatting.
        
        >>> Locale('en', 'US').date_formats['short']
        <DateTimePattern u'M/d/yy'>
        >>> Locale('fr', 'FR').date_formats['long']
        <DateTimePattern u'd MMMM yyyy'>
        
        :type: `dict`
        """)

    def time_formats(self):
        return self._data['time_formats']
    time_formats = property(time_formats, doc="""\
        Locale patterns for time formatting.
        
        >>> Locale('en', 'US').time_formats['short']
        <DateTimePattern u'h:mm a'>
        >>> Locale('fr', 'FR').time_formats['long']
        <DateTimePattern u'HH:mm:ss z'>
        
        :type: `dict`
        """)

    def datetime_formats(self):
        return self._data['datetime_formats']
    datetime_formats = property(datetime_formats, doc="""\
        Locale patterns for datetime formatting.
        
        >>> Locale('en').datetime_formats[None]
        u'{1} {0}'
        >>> Locale('th').datetime_formats[None]
        u'{1}, {0}'
        
        :type: `dict`
        """)


def default_locale(category=None, aliases=LOCALE_ALIASES):
    """Returns the system default locale for a given category, based on
    environment variables.
    
    >>> for name in ['LANGUAGE', 'LC_ALL', 'LC_CTYPE']:
    ...     os.environ[name] = ''
    >>> os.environ['LANG'] = 'fr_FR.UTF-8'
    >>> default_locale('LC_MESSAGES')
    'fr_FR'

    The "C" or "POSIX" pseudo-locales are treated as aliases for the
    "en_US_POSIX" locale:

    >>> os.environ['LC_MESSAGES'] = 'POSIX'
    >>> default_locale('LC_MESSAGES')
    'en_US_POSIX'

    :param category: one of the ``LC_XXX`` environment variable names
    :param aliases: a dictionary of aliases for locale identifiers
    :return: the value of the variable, or any of the fallbacks (``LANGUAGE``,
             ``LC_ALL``, ``LC_CTYPE``, and ``LANG``)
    :rtype: `str`
    """
    varnames = (category, 'LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LANG')
    for name in filter(None, varnames):
        locale = os.getenv(name)
        if locale:
            if name == 'LANGUAGE' and ':' in locale:
                # the LANGUAGE variable may contain a colon-separated list of
                # language codes; we just pick the language on the list
                locale = locale.split(':')[0]
            if locale in ('C', 'POSIX'):
                locale = 'en_US_POSIX'
            elif aliases and locale in aliases:
                locale = aliases[locale]
            return '_'.join(filter(None, parse_locale(locale)))

def negotiate_locale(preferred, available, sep='_', aliases=LOCALE_ALIASES):
    """Find the best match between available and requested locale strings.
    
    >>> negotiate_locale(['de_DE', 'en_US'], ['de_DE', 'de_AT'])
    'de_DE'
    >>> negotiate_locale(['de_DE', 'en_US'], ['en', 'de'])
    'de'
    
    Case is ignored by the algorithm, the result uses the case of the preferred
    locale identifier:
    
    >>> negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at'])
    'de_DE'
    
    >>> negotiate_locale(['de_DE', 'en_US'], ['de_de', 'de_at'])
    'de_DE'
    
    By default, some web browsers unfortunately do not include the territory
    in the locale identifier for many locales, and some don't even allow the
    user to easily add the territory. So while you may prefer using qualified
    locale identifiers in your web-application, they would not normally match
    the language-only locale sent by such browsers. To workaround that, this
    function uses a default mapping of commonly used langauge-only locale
    identifiers to identifiers including the territory:
    
    >>> negotiate_locale(['ja', 'en_US'], ['ja_JP', 'en_US'])
    'ja_JP'
    
    Some browsers even use an incorrect or outdated language code, such as "no"
    for Norwegian, where the correct locale identifier would actually be "nb_NO"
    (Bokmål) or "nn_NO" (Nynorsk). The aliases are intended to take care of
    such cases, too:
    
    >>> negotiate_locale(['no', 'sv'], ['nb_NO', 'sv_SE'])
    'nb_NO'
    
    You can override this default mapping by passing a different `aliases`
    dictionary to this function, or you can bypass the behavior althogher by
    setting the `aliases` parameter to `None`.
    
    :param preferred: the list of locale strings preferred by the user
    :param available: the list of locale strings available
    :param sep: character that separates the different parts of the locale
                strings
    :param aliases: a dictionary of aliases for locale identifiers
    :return: the locale identifier for the best match, or `None` if no match
             was found
    :rtype: `str`
    """
    available = [a.lower() for a in available if a]
    for locale in preferred:
        ll = locale.lower()
        if ll in available:
            return locale
        if aliases:
            alias = aliases.get(ll)
            if alias:
                alias = alias.replace('_', sep)
                if alias.lower() in available:
                    return alias
        parts = locale.split(sep)
        if len(parts) > 1 and parts[0].lower() in available:
            return parts[0]
    return None

def parse_locale(identifier, sep='_'):
    """Parse a locale identifier into a tuple of the form::
    
      ``(language, territory, script, variant)``
    
    >>> parse_locale('zh_CN')
    ('zh', 'CN', None, None)
    >>> parse_locale('zh_Hans_CN')
    ('zh', 'CN', 'Hans', None)
    
    The default component separator is "_", but a different separator can be
    specified using the `sep` parameter:
    
    >>> parse_locale('zh-CN', sep='-')
    ('zh', 'CN', None, None)
    
    If the identifier cannot be parsed into a locale, a `ValueError` exception
    is raised:
    
    >>> parse_locale('not_a_LOCALE_String')
    Traceback (most recent call last):
      ...
    ValueError: 'not_a_LOCALE_String' is not a valid locale identifier
    
    Encoding information and locale modifiers are removed from the identifier:
    
    >>> parse_locale('it_IT@euro')
    ('it', 'IT', None, None)
    >>> parse_locale('en_US.UTF-8')
    ('en', 'US', None, None)
    >>> parse_locale('de_DE.iso885915@euro')
    ('de', 'DE', None, None)
    
    :param identifier: the locale identifier string
    :param sep: character that separates the different components of the locale
                identifier
    :return: the ``(language, territory, script, variant)`` tuple
    :rtype: `tuple`
    :raise `ValueError`: if the string does not appear to be a valid locale
                         identifier
    
    :see: `IETF RFC 4646 <http://www.ietf.org/rfc/rfc4646.txt>`_
    """
    if '.' in identifier:
        # this is probably the charset/encoding, which we don't care about
        identifier = identifier.split('.', 1)[0]
    if '@' in identifier:
        # this is a locale modifier such as @euro, which we don't care about
        # either
        identifier = identifier.split('@', 1)[0]

    parts = identifier.split(sep)
    lang = parts.pop(0).lower()
    if not lang.isalpha():
        raise ValueError('expected only letters, got %r' % lang)

    script = territory = variant = None
    if parts:
        if len(parts[0]) == 4 and parts[0].isalpha():
            script = parts.pop(0).title()

    if parts:
        if len(parts[0]) == 2 and parts[0].isalpha():
            territory = parts.pop(0).upper()
        elif len(parts[0]) == 3 and parts[0].isdigit():
            territory = parts.pop(0)

    if parts:
        if len(parts[0]) == 4 and parts[0][0].isdigit() or \
                len(parts[0]) >= 5 and parts[0][0].isalpha():
            variant = parts.pop()

    if parts:
        raise ValueError('%r is not a valid locale identifier' % identifier)

    return lang, territory, script, variant

########NEW FILE########
__FILENAME__ = dates
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Locale dependent formatting and parsing of dates and times.

The default locale for the functions in this module is determined by the
following environment variables, in that order:

 * ``LC_TIME``,
 * ``LC_ALL``, and
 * ``LANG``
"""

from datetime import date, datetime, time, timedelta, tzinfo
import re

from babel.core import default_locale, get_global, Locale
from babel.util import UTC

__all__ = ['format_date', 'format_datetime', 'format_time',
           'get_timezone_name', 'parse_date', 'parse_datetime', 'parse_time']
__docformat__ = 'restructuredtext en'

LC_TIME = default_locale('LC_TIME')

# Aliases for use in scopes where the modules are shadowed by local variables
date_ = date
datetime_ = datetime
time_ = time

def get_period_names(locale=LC_TIME):
    """Return the names for day periods (AM/PM) used by the locale.
    
    >>> get_period_names(locale='en_US')['am']
    u'AM'
    
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of period names
    :rtype: `dict`
    """
    return Locale.parse(locale).periods

def get_day_names(width='wide', context='format', locale=LC_TIME):
    """Return the day names used by the locale for the specified format.
    
    >>> get_day_names('wide', locale='en_US')[1]
    u'Tuesday'
    >>> get_day_names('abbreviated', locale='es')[1]
    u'mar'
    >>> get_day_names('narrow', context='stand-alone', locale='de_DE')[1]
    u'D'
    
    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of day names
    :rtype: `dict`
    """
    return Locale.parse(locale).days[context][width]

def get_month_names(width='wide', context='format', locale=LC_TIME):
    """Return the month names used by the locale for the specified format.
    
    >>> get_month_names('wide', locale='en_US')[1]
    u'January'
    >>> get_month_names('abbreviated', locale='es')[1]
    u'ene'
    >>> get_month_names('narrow', context='stand-alone', locale='de_DE')[1]
    u'J'
    
    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of month names
    :rtype: `dict`
    """
    return Locale.parse(locale).months[context][width]

def get_quarter_names(width='wide', context='format', locale=LC_TIME):
    """Return the quarter names used by the locale for the specified format.
    
    >>> get_quarter_names('wide', locale='en_US')[1]
    u'1st quarter'
    >>> get_quarter_names('abbreviated', locale='de_DE')[1]
    u'Q1'
    
    :param width: the width to use, one of "wide", "abbreviated", or "narrow"
    :param context: the context, either "format" or "stand-alone"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of quarter names
    :rtype: `dict`
    """
    return Locale.parse(locale).quarters[context][width]

def get_era_names(width='wide', locale=LC_TIME):
    """Return the era names used by the locale for the specified format.
    
    >>> get_era_names('wide', locale='en_US')[1]
    u'Anno Domini'
    >>> get_era_names('abbreviated', locale='de_DE')[1]
    u'n. Chr.'
    
    :param width: the width to use, either "wide", "abbreviated", or "narrow"
    :param locale: the `Locale` object, or a locale string
    :return: the dictionary of era names
    :rtype: `dict`
    """
    return Locale.parse(locale).eras[width]

def get_date_format(format='medium', locale=LC_TIME):
    """Return the date formatting patterns used by the locale for the specified
    format.
    
    >>> get_date_format(locale='en_US')
    <DateTimePattern u'MMM d, yyyy'>
    >>> get_date_format('full', locale='de_DE')
    <DateTimePattern u'EEEE, d. MMMM yyyy'>
    
    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    :return: the date format pattern
    :rtype: `DateTimePattern`
    """
    return Locale.parse(locale).date_formats[format]

def get_datetime_format(format='medium', locale=LC_TIME):
    """Return the datetime formatting patterns used by the locale for the
    specified format.
    
    >>> get_datetime_format(locale='en_US')
    u'{1} {0}'
    
    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    :return: the datetime format pattern
    :rtype: `unicode`
    """
    patterns = Locale.parse(locale).datetime_formats
    if format not in patterns:
        format = None
    return patterns[format]

def get_time_format(format='medium', locale=LC_TIME):
    """Return the time formatting patterns used by the locale for the specified
    format.
    
    >>> get_time_format(locale='en_US')
    <DateTimePattern u'h:mm:ss a'>
    >>> get_time_format('full', locale='de_DE')
    <DateTimePattern u'HH:mm:ss v'>
    
    :param format: the format to use, one of "full", "long", "medium", or
                   "short"
    :param locale: the `Locale` object, or a locale string
    :return: the time format pattern
    :rtype: `DateTimePattern`
    """
    return Locale.parse(locale).time_formats[format]

def get_timezone_gmt(datetime=None, width='long', locale=LC_TIME):
    """Return the timezone associated with the given `datetime` object formatted
    as string indicating the offset from GMT.
    
    >>> dt = datetime(2007, 4, 1, 15, 30)
    >>> get_timezone_gmt(dt, locale='en')
    u'GMT+00:00'
    
    >>> from pytz import timezone
    >>> tz = timezone('America/Los_Angeles')
    >>> dt = datetime(2007, 4, 1, 15, 30, tzinfo=tz)
    >>> get_timezone_gmt(dt, locale='en')
    u'GMT-08:00'
    >>> get_timezone_gmt(dt, 'short', locale='en')
    u'-0800'
    
    The long format depends on the locale, for example in France the acronym
    UTC string is used instead of GMT:
    
    >>> get_timezone_gmt(dt, 'long', locale='fr_FR')
    u'UTC-08:00'
    
    :param datetime: the ``datetime`` object; if `None`, the current date and
                     time in UTC is used
    :param width: either "long" or "short"
    :param locale: the `Locale` object, or a locale string
    :return: the GMT offset representation of the timezone
    :rtype: `unicode`
    :since: version 0.9
    """
    if datetime is None:
        datetime = datetime_.utcnow()
    elif isinstance(datetime, (int, long)):
        datetime = datetime_.utcfromtimestamp(datetime).time()
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=UTC)
    locale = Locale.parse(locale)

    offset = datetime.tzinfo.utcoffset(datetime)
    seconds = offset.days * 24 * 60 * 60 + offset.seconds
    hours, seconds = divmod(seconds, 3600)
    if width == 'short':
        pattern = u'%+03d%02d'
    else:
        pattern = locale.zone_formats['gmt'] % '%+03d:%02d'
    return pattern % (hours, seconds // 60)

def get_timezone_location(dt_or_tzinfo=None, locale=LC_TIME):
    """Return a representation of the given timezone using "location format".
    
    The result depends on both the local display name of the country and the
    city assocaited with the time zone:
    
    >>> from pytz import timezone
    >>> tz = timezone('America/St_Johns')
    >>> get_timezone_location(tz, locale='de_DE')
    u"Kanada (St. John's)"
    >>> tz = timezone('America/Mexico_City')
    >>> get_timezone_location(tz, locale='de_DE')
    u'Mexiko (Mexiko-Stadt)'
    
    If the timezone is associated with a country that uses only a single
    timezone, just the localized country name is returned:
    
    >>> tz = timezone('Europe/Berlin')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Deutschland'
    
    :param dt_or_tzinfo: the ``datetime`` or ``tzinfo`` object that determines
                         the timezone; if `None`, the current date and time in
                         UTC is assumed
    :param locale: the `Locale` object, or a locale string
    :return: the localized timezone name using location format
    :rtype: `unicode`
    :since: version 0.9
    """
    if dt_or_tzinfo is None or isinstance(dt_or_tzinfo, (int, long)):
        dt = None
        tzinfo = UTC
    elif isinstance(dt_or_tzinfo, (datetime, time)):
        dt = dt_or_tzinfo
        if dt.tzinfo is not None:
            tzinfo = dt.tzinfo
        else:
            tzinfo = UTC
    else:
        dt = None
        tzinfo = dt_or_tzinfo
    locale = Locale.parse(locale)

    if hasattr(tzinfo, 'zone'):
        zone = tzinfo.zone
    else:
        zone = tzinfo.tzname(dt or datetime.utcnow())

    # Get the canonical time-zone code
    zone = get_global('zone_aliases').get(zone, zone)

    info = locale.time_zones.get(zone, {})

    # Otherwise, if there is only one timezone for the country, return the
    # localized country name
    region_format = locale.zone_formats['region']
    territory = get_global('zone_territories').get(zone)
    if territory not in locale.territories:
        territory = 'ZZ' # invalid/unknown
    territory_name = locale.territories[territory]
    if territory and len(get_global('territory_zones').get(territory, [])) == 1:
        return region_format % (territory_name)

    # Otherwise, include the city in the output
    fallback_format = locale.zone_formats['fallback']
    if 'city' in info:
        city_name = info['city']
    else:
        metazone = get_global('meta_zones').get(zone)
        metazone_info = locale.meta_zones.get(metazone, {})
        if 'city' in metazone_info:
            city_name = metainfo['city']
        elif '/' in zone:
            city_name = zone.split('/', 1)[1].replace('_', ' ')
        else:
            city_name = zone.replace('_', ' ')

    return region_format % (fallback_format % {
        '0': city_name,
        '1': territory_name
    })

def get_timezone_name(dt_or_tzinfo=None, width='long', uncommon=False,
                      locale=LC_TIME):
    r"""Return the localized display name for the given timezone. The timezone
    may be specified using a ``datetime`` or `tzinfo` object.
    
    >>> from pytz import timezone
    >>> dt = time(15, 30, tzinfo=timezone('America/Los_Angeles'))
    >>> get_timezone_name(dt, locale='en_US')
    u'Pacific Standard Time'
    >>> get_timezone_name(dt, width='short', locale='en_US')
    u'PST'
    
    If this function gets passed only a `tzinfo` object and no concrete
    `datetime`,  the returned display name is indenpendent of daylight savings
    time. This can be used for example for selecting timezones, or to set the
    time of events that recur across DST changes:
    
    >>> tz = timezone('America/Los_Angeles')
    >>> get_timezone_name(tz, locale='en_US')
    u'Pacific Time'
    >>> get_timezone_name(tz, 'short', locale='en_US')
    u'PT'
    
    If no localized display name for the timezone is available, and the timezone
    is associated with a country that uses only a single timezone, the name of
    that country is returned, formatted according to the locale:
    
    >>> tz = timezone('Europe/Berlin')
    >>> get_timezone_name(tz, locale='de_DE')
    u'Deutschland'
    >>> get_timezone_name(tz, locale='pt_BR')
    u'Hor\xe1rio Alemanha'
    
    On the other hand, if the country uses multiple timezones, the city is also
    included in the representation:
    
    >>> tz = timezone('America/St_Johns')
    >>> get_timezone_name(tz, locale='de_DE')
    u"Kanada (St. John's)"
    
    The `uncommon` parameter can be set to `True` to enable the use of timezone
    representations that are not commonly used by the requested locale. For
    example, while in frensh the central europian timezone is usually
    abbreviated as "HEC", in Canadian French, this abbreviation is not in
    common use, so a generic name would be chosen by default:
    
    >>> tz = timezone('Europe/Paris')
    >>> get_timezone_name(tz, 'short', locale='fr_CA')
    u'France'
    >>> get_timezone_name(tz, 'short', uncommon=True, locale='fr_CA')
    u'HEC'
    
    :param dt_or_tzinfo: the ``datetime`` or ``tzinfo`` object that determines
                         the timezone; if a ``tzinfo`` object is used, the
                         resulting display name will be generic, i.e.
                         independent of daylight savings time; if `None`, the
                         current date in UTC is assumed
    :param width: either "long" or "short"
    :param uncommon: whether even uncommon timezone abbreviations should be used
    :param locale: the `Locale` object, or a locale string
    :return: the timezone display name
    :rtype: `unicode`
    :since: version 0.9
    :see:  `LDML Appendix J: Time Zone Display Names
            <http://www.unicode.org/reports/tr35/#Time_Zone_Fallback>`_
    """
    if dt_or_tzinfo is None or isinstance(dt_or_tzinfo, (int, long)):
        dt = None
        tzinfo = UTC
    elif isinstance(dt_or_tzinfo, (datetime, time)):
        dt = dt_or_tzinfo
        if dt.tzinfo is not None:
            tzinfo = dt.tzinfo
        else:
            tzinfo = UTC
    else:
        dt = None
        tzinfo = dt_or_tzinfo
    locale = Locale.parse(locale)

    if hasattr(tzinfo, 'zone'):
        zone = tzinfo.zone
    else:
        zone = tzinfo.tzname(dt)

    # Get the canonical time-zone code
    zone = get_global('zone_aliases').get(zone, zone)

    info = locale.time_zones.get(zone, {})
    # Try explicitly translated zone names first
    if width in info:
        if dt is None:
            field = 'generic'
        else:
            dst = tzinfo.dst(dt)
            if dst is None:
                field = 'generic'
            elif dst == 0:
                field = 'standard'
            else:
                field = 'daylight'
        if field in info[width]:
            return info[width][field]

    metazone = get_global('meta_zones').get(zone)
    if metazone:
        metazone_info = locale.meta_zones.get(metazone, {})
        if width in metazone_info and (uncommon or metazone_info.get('common')):
            if dt is None:
                field = 'generic'
            else:
                field = tzinfo.dst(dt) and 'daylight' or 'standard'
            if field in metazone_info[width]:
                return metazone_info[width][field]

    # If we have a concrete datetime, we assume that the result can't be
    # independent of daylight savings time, so we return the GMT offset
    if dt is not None:
        return get_timezone_gmt(dt, width=width, locale=locale)

    return get_timezone_location(dt_or_tzinfo, locale=locale)

def format_date(date=None, format='medium', locale=LC_TIME):
    """Return a date formatted according to the given pattern.
    
    >>> d = date(2007, 04, 01)
    >>> format_date(d, locale='en_US')
    u'Apr 1, 2007'
    >>> format_date(d, format='full', locale='de_DE')
    u'Sonntag, 1. April 2007'
    
    If you don't want to use the locale default formats, you can specify a
    custom date pattern:
    
    >>> format_date(d, "EEE, MMM d, ''yy", locale='en')
    u"Sun, Apr 1, '07"
    
    :param date: the ``date`` or ``datetime`` object; if `None`, the current
                 date is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param locale: a `Locale` object or a locale identifier
    :rtype: `unicode`
    
    :note: If the pattern contains time fields, an `AttributeError` will be
           raised when trying to apply the formatting. This is also true if
           the value of ``date`` parameter is actually a ``datetime`` object,
           as this function automatically converts that to a ``date``.
    """
    if date is None:
        date = date_.today()
    elif isinstance(date, datetime):
        date = date.date()

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        format = get_date_format(format, locale=locale)
    pattern = parse_pattern(format)
    return parse_pattern(format).apply(date, locale)

def format_datetime(datetime=None, format='medium', tzinfo=None,
                    locale=LC_TIME):
    """Return a date formatted according to the given pattern.
    
    >>> dt = datetime(2007, 04, 01, 15, 30)
    >>> format_datetime(dt, locale='en_US')
    u'Apr 1, 2007 3:30:00 PM'
    
    For any pattern requiring the display of the time-zone, the third-party
    ``pytz`` package is needed to explicitly specify the time-zone:
    
    >>> from pytz import timezone
    >>> format_datetime(dt, 'full', tzinfo=timezone('Europe/Paris'),
    ...                 locale='fr_FR')
    u'dimanche 1 avril 2007 17:30:00 HEC'
    >>> format_datetime(dt, "yyyy.MM.dd G 'at' HH:mm:ss zzz",
    ...                 tzinfo=timezone('US/Eastern'), locale='en')
    u'2007.04.01 AD at 11:30:00 EDT'
    
    :param datetime: the `datetime` object; if `None`, the current date and
                     time is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the timezone to apply to the time for display
    :param locale: a `Locale` object or a locale identifier
    :rtype: `unicode`
    """
    if datetime is None:
        datetime = datetime_.utcnow()
    elif isinstance(datetime, (int, long)):
        datetime = datetime_.utcfromtimestamp(datetime)
    elif isinstance(datetime, time):
        datetime = datetime_.combine(date.today(), datetime)
    if datetime.tzinfo is None:
        datetime = datetime.replace(tzinfo=UTC)
    if tzinfo is not None:
        datetime = datetime.astimezone(tzinfo)
        if hasattr(tzinfo, 'normalize'): # pytz
            datetime = tzinfo.normalize(datetime)

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        return get_datetime_format(format, locale=locale) \
            .replace('{0}', format_time(datetime, format, tzinfo=None,
                                        locale=locale)) \
            .replace('{1}', format_date(datetime, format, locale=locale))
    else:
        return parse_pattern(format).apply(datetime, locale)

def format_time(time=None, format='medium', tzinfo=None, locale=LC_TIME):
    """Return a time formatted according to the given pattern.
    
    >>> t = time(15, 30)
    >>> format_time(t, locale='en_US')
    u'3:30:00 PM'
    >>> format_time(t, format='short', locale='de_DE')
    u'15:30'
    
    If you don't want to use the locale default formats, you can specify a
    custom time pattern:
    
    >>> format_time(t, "hh 'o''clock' a", locale='en')
    u"03 o'clock PM"
    
    For any pattern requiring the display of the time-zone, the third-party
    ``pytz`` package is needed to explicitly specify the time-zone:
    
    >>> from pytz import timezone
    >>> t = datetime(2007, 4, 1, 15, 30)
    >>> tzinfo = timezone('Europe/Paris')
    >>> t = tzinfo.localize(t)
    >>> format_time(t, format='full', tzinfo=tzinfo, locale='fr_FR')
    u'15:30:00 HEC'
    >>> format_time(t, "hh 'o''clock' a, zzzz", tzinfo=timezone('US/Eastern'),
    ...             locale='en')
    u"09 o'clock AM, Eastern Daylight Time"
    
    As that example shows, when this function gets passed a
    ``datetime.datetime`` value, the actual time in the formatted string is
    adjusted to the timezone specified by the `tzinfo` parameter. If the
    ``datetime`` is "naive" (i.e. it has no associated timezone information),
    it is assumed to be in UTC.
    
    These timezone calculations are **not** performed if the value is of type
    ``datetime.time``, as without date information there's no way to determine
    what a given time would translate to in a different timezone without
    information about whether daylight savings time is in effect or not. This
    means that time values are left as-is, and the value of the `tzinfo`
    parameter is only used to display the timezone name if needed:
    
    >>> t = time(15, 30)
    >>> format_time(t, format='full', tzinfo=timezone('Europe/Paris'),
    ...             locale='fr_FR')
    u'15:30:00 HEC'
    >>> format_time(t, format='full', tzinfo=timezone('US/Eastern'),
    ...             locale='en_US')
    u'3:30:00 PM ET'
    
    :param time: the ``time`` or ``datetime`` object; if `None`, the current
                 time in UTC is used
    :param format: one of "full", "long", "medium", or "short", or a custom
                   date/time pattern
    :param tzinfo: the time-zone to apply to the time for display
    :param locale: a `Locale` object or a locale identifier
    :rtype: `unicode`
    
    :note: If the pattern contains date fields, an `AttributeError` will be
           raised when trying to apply the formatting. This is also true if
           the value of ``time`` parameter is actually a ``datetime`` object,
           as this function automatically converts that to a ``time``.
    """
    if time is None:
        time = datetime.utcnow()
    elif isinstance(time, (int, long)):
        time = datetime.utcfromtimestamp(time)
    if time.tzinfo is None:
        time = time.replace(tzinfo=UTC)
    if isinstance(time, datetime):
        if tzinfo is not None:
            time = time.astimezone(tzinfo)
            if hasattr(tzinfo, 'localize'): # pytz
                time = tzinfo.normalize(time)
        time = time.timetz()
    elif tzinfo is not None:
        time = time.replace(tzinfo=tzinfo)

    locale = Locale.parse(locale)
    if format in ('full', 'long', 'medium', 'short'):
        format = get_time_format(format, locale=locale)
    return parse_pattern(format).apply(time, locale)

def parse_date(string, locale=LC_TIME):
    """Parse a date from a string.
    
    This function uses the date format for the locale as a hint to determine
    the order in which the date fields appear in the string.
    
    >>> parse_date('4/1/04', locale='en_US')
    datetime.date(2004, 4, 1)
    >>> parse_date('01.04.2004', locale='de_DE')
    datetime.date(2004, 4, 1)
    
    :param string: the string containing the date
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed date
    :rtype: `date`
    """
    # TODO: try ISO format first?
    format = get_date_format(locale=locale).pattern.lower()
    year_idx = format.index('y')
    month_idx = format.index('m')
    if month_idx < 0:
        month_idx = format.index('l')
    day_idx = format.index('d')

    indexes = [(year_idx, 'Y'), (month_idx, 'M'), (day_idx, 'D')]
    indexes.sort()
    indexes = dict([(item[1], idx) for idx, item in enumerate(indexes)])

    # FIXME: this currently only supports numbers, but should also support month
    #        names, both in the requested locale, and english

    numbers = re.findall('(\d+)', string)
    year = numbers[indexes['Y']]
    if len(year) == 2:
        year = 2000 + int(year)
    else:
        year = int(year)
    month = int(numbers[indexes['M']])
    day = int(numbers[indexes['D']])
    if month > 12:
        month, day = day, month
    return date(year, month, day)

def parse_datetime(string, locale=LC_TIME):
    """Parse a date and time from a string.
    
    This function uses the date and time formats for the locale as a hint to
    determine the order in which the time fields appear in the string.
    
    :param string: the string containing the date and time
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed date/time
    :rtype: `datetime`
    """
    raise NotImplementedError

def parse_time(string, locale=LC_TIME):
    """Parse a time from a string.
    
    This function uses the time format for the locale as a hint to determine
    the order in which the time fields appear in the string.
    
    >>> parse_time('15:30:00', locale='en_US')
    datetime.time(15, 30)
    
    :param string: the string containing the time
    :param locale: a `Locale` object or a locale identifier
    :return: the parsed time
    :rtype: `time`
    """
    # TODO: try ISO format first?
    format = get_time_format(locale=locale).pattern.lower()
    hour_idx = format.index('h')
    if hour_idx < 0:
        hour_idx = format.index('k')
    min_idx = format.index('m')
    sec_idx = format.index('s')

    indexes = [(hour_idx, 'H'), (min_idx, 'M'), (sec_idx, 'S')]
    indexes.sort()
    indexes = dict([(item[1], idx) for idx, item in enumerate(indexes)])

    # FIXME: support 12 hour clock, and 0-based hour specification
    #        and seconds should be optional, maybe minutes too
    #        oh, and time-zones, of course

    numbers = re.findall('(\d+)', string)
    hour = int(numbers[indexes['H']])
    minute = int(numbers[indexes['M']])
    second = int(numbers[indexes['S']])
    return time(hour, minute, second)


class DateTimePattern(object):

    def __init__(self, pattern, format):
        self.pattern = pattern
        self.format = format

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.pattern)

    def __unicode__(self):
        return self.pattern

    def __mod__(self, other):
        assert type(other) is DateTimeFormat
        return self.format % other

    def apply(self, datetime, locale):
        return self % DateTimeFormat(datetime, locale)


class DateTimeFormat(object):

    def __init__(self, value, locale):
        assert isinstance(value, (date, datetime, time))
        if isinstance(value, (datetime, time)) and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        self.value = value
        self.locale = Locale.parse(locale)

    def __getitem__(self, name):
        char = name[0]
        num = len(name)
        if char == 'G':
            return self.format_era(char, num)
        elif char in ('y', 'Y', 'u'):
            return self.format_year(char, num)
        elif char in ('Q', 'q'):
            return self.format_quarter(char, num)
        elif char in ('M', 'L'):
            return self.format_month(char, num)
        elif char in ('w', 'W'):
            return self.format_week(char, num)
        elif char == 'd':
            return self.format(self.value.day, num)
        elif char == 'D':
            return self.format_day_of_year(num)
        elif char == 'F':
            return self.format_day_of_week_in_month()
        elif char in ('E', 'e', 'c'):
            return self.format_weekday(char, num)
        elif char == 'a':
            return self.format_period(char)
        elif char == 'h':
            if self.value.hour % 12 == 0:
                return self.format(12, num)
            else:
                return self.format(self.value.hour % 12, num)
        elif char == 'H':
            return self.format(self.value.hour, num)
        elif char == 'K':
            return self.format(self.value.hour % 12, num)
        elif char == 'k':
            if self.value.hour == 0:
                return self.format(24, num)
            else:
                return self.format(self.value.hour, num)
        elif char == 'm':
            return self.format(self.value.minute, num)
        elif char == 's':
            return self.format(self.value.second, num)
        elif char == 'S':
            return self.format_frac_seconds(num)
        elif char == 'A':
            return self.format_milliseconds_in_day(num)
        elif char in ('z', 'Z', 'v', 'V'):
            return self.format_timezone(char, num)
        else:
            raise KeyError('Unsupported date/time field %r' % char)

    def format_era(self, char, num):
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[max(3, num)]
        era = int(self.value.year >= 0)
        return get_era_names(width, self.locale)[era]

    def format_year(self, char, num):
        value = self.value.year
        if char.isupper():
            week = self.get_week_number(self.get_day_of_year())
            if week == 0:
                value -= 1
        year = self.format(value, num)
        if num == 2:
            year = year[-2:]
        return year

    def format_quarter(self, char, num):
        quarter = (self.value.month - 1) // 3 + 1
        if num <= 2:
            return ('%%0%dd' % num) % quarter
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {'Q': 'format', 'q': 'stand-alone'}[char]
        return get_quarter_names(width, context, self.locale)[quarter]

    def format_month(self, char, num):
        if num <= 2:
            return ('%%0%dd' % num) % self.value.month
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {'M': 'format', 'L': 'stand-alone'}[char]
        return get_month_names(width, context, self.locale)[self.value.month]

    def format_week(self, char, num):
        if char.islower(): # week of year
            day_of_year = self.get_day_of_year()
            week = self.get_week_number(day_of_year)
            if week == 0:
                date = self.value - timedelta(days=day_of_year)
                week = self.get_week_number(self.get_day_of_year(date),
                                            date.weekday())
            return self.format(week, num)
        else: # week of month
            week = self.get_week_number(self.value.day)
            if week == 0:
                date = self.value - timedelta(days=self.value.day)
                week = self.get_week_number(date.day, date.weekday())
                pass
            return '%d' % week

    def format_weekday(self, char, num):
        if num < 3:
            if char.islower():
                value = 7 - self.locale.first_week_day + self.value.weekday()
                return self.format(value % 7 + 1, num)
            num = 3
        weekday = self.value.weekday()
        width = {3: 'abbreviated', 4: 'wide', 5: 'narrow'}[num]
        context = {3: 'format', 4: 'format', 5: 'stand-alone'}[num]
        return get_day_names(width, context, self.locale)[weekday]

    def format_day_of_year(self, num):
        return self.format(self.get_day_of_year(), num)

    def format_day_of_week_in_month(self):
        return '%d' % ((self.value.day - 1) / 7 + 1)

    def format_period(self, char):
        period = {0: 'am', 1: 'pm'}[int(self.value.hour >= 12)]
        return get_period_names(locale=self.locale)[period]

    def format_frac_seconds(self, num):
        value = str(self.value.microsecond)
        return self.format(round(float('.%s' % value), num) * 10**num, num)

    def format_milliseconds_in_day(self, num):
        msecs = self.value.microsecond // 1000 + self.value.second * 1000 + \
                self.value.minute * 60000 + self.value.hour * 3600000
        return self.format(msecs, num)

    def format_timezone(self, char, num):
        width = {3: 'short', 4: 'long'}[max(3, num)]
        if char == 'z':
            return get_timezone_name(self.value, width, locale=self.locale)
        elif char == 'Z':
            return get_timezone_gmt(self.value, width, locale=self.locale)
        elif char == 'v':
            return get_timezone_name(self.value.tzinfo, width,
                                     locale=self.locale)
        elif char == 'V':
            if num == 1:
                return get_timezone_name(self.value.tzinfo, width,
                                         uncommon=True, locale=self.locale)
            return get_timezone_location(self.value.tzinfo, locale=self.locale)

    def format(self, value, length):
        return ('%%0%dd' % length) % value

    def get_day_of_year(self, date=None):
        if date is None:
            date = self.value
        return (date - date_(date.year, 1, 1)).days + 1

    def get_week_number(self, day_of_period, day_of_week=None):
        """Return the number of the week of a day within a period. This may be
        the week number in a year or the week number in a month.
        
        Usually this will return a value equal to or greater than 1, but if the
        first week of the period is so short that it actually counts as the last
        week of the previous period, this function will return 0.
        
        >>> format = DateTimeFormat(date(2006, 1, 8), Locale.parse('de_DE'))
        >>> format.get_week_number(6)
        1
        
        >>> format = DateTimeFormat(date(2006, 1, 8), Locale.parse('en_US'))
        >>> format.get_week_number(6)
        2
        
        :param day_of_period: the number of the day in the period (usually
                              either the day of month or the day of year)
        :param day_of_week: the week day; if ommitted, the week day of the
                            current date is assumed
        """
        if day_of_week is None:
            day_of_week = self.value.weekday()
        first_day = (day_of_week - self.locale.first_week_day -
                     day_of_period + 1) % 7
        if first_day < 0:
            first_day += 7
        week_number = (day_of_period + first_day - 1) / 7
        if 7 - first_day >= self.locale.min_week_days:
            week_number += 1
        return week_number


PATTERN_CHARS = {
    'G': [1, 2, 3, 4, 5],                                           # era
    'y': None, 'Y': None, 'u': None,                                # year
    'Q': [1, 2, 3, 4], 'q': [1, 2, 3, 4],                           # quarter
    'M': [1, 2, 3, 4, 5], 'L': [1, 2, 3, 4, 5],                     # month
    'w': [1, 2], 'W': [1],                                          # week
    'd': [1, 2], 'D': [1, 2, 3], 'F': [1], 'g': None,               # day
    'E': [1, 2, 3, 4, 5], 'e': [1, 2, 3, 4, 5], 'c': [1, 3, 4, 5],  # week day
    'a': [1],                                                       # period
    'h': [1, 2], 'H': [1, 2], 'K': [1, 2], 'k': [1, 2],             # hour
    'm': [1, 2],                                                    # minute
    's': [1, 2], 'S': None, 'A': None,                              # second
    'z': [1, 2, 3, 4], 'Z': [1, 2, 3, 4], 'v': [1, 4], 'V': [1, 4]  # zone
}

def parse_pattern(pattern):
    """Parse date, time, and datetime format patterns.
    
    >>> parse_pattern("MMMMd").format
    u'%(MMMM)s%(d)s'
    >>> parse_pattern("MMM d, yyyy").format
    u'%(MMM)s %(d)s, %(yyyy)s'
    
    Pattern can contain literal strings in single quotes:
    
    >>> parse_pattern("H:mm' Uhr 'z").format
    u'%(H)s:%(mm)s Uhr %(z)s'
    
    An actual single quote can be used by using two adjacent single quote
    characters:
    
    >>> parse_pattern("hh' o''clock'").format
    u"%(hh)s o'clock"
    
    :param pattern: the formatting pattern to parse
    """
    if type(pattern) is DateTimePattern:
        return pattern

    result = []
    quotebuf = None
    charbuf = []
    fieldchar = ['']
    fieldnum = [0]

    def append_chars():
        result.append(''.join(charbuf).replace('%', '%%'))
        del charbuf[:]

    def append_field():
        limit = PATTERN_CHARS[fieldchar[0]]
        if limit and fieldnum[0] not in limit:
            raise ValueError('Invalid length for field: %r'
                             % (fieldchar[0] * fieldnum[0]))
        result.append('%%(%s)s' % (fieldchar[0] * fieldnum[0]))
        fieldchar[0] = ''
        fieldnum[0] = 0

    for idx, char in enumerate(pattern.replace("''", '\0')):
        if quotebuf is None:
            if char == "'": # quote started
                if fieldchar[0]:
                    append_field()
                elif charbuf:
                    append_chars()
                quotebuf = []
            elif char in PATTERN_CHARS:
                if charbuf:
                    append_chars()
                if char == fieldchar[0]:
                    fieldnum[0] += 1
                else:
                    if fieldchar[0]:
                        append_field()
                    fieldchar[0] = char
                    fieldnum[0] = 1
            else:
                if fieldchar[0]:
                    append_field()
                charbuf.append(char)

        elif quotebuf is not None:
            if char == "'": # end of quote
                charbuf.extend(quotebuf)
                quotebuf = None
            else: # inside quote
                quotebuf.append(char)

    if fieldchar[0]:
        append_field()
    elif charbuf:
        append_chars()

    return DateTimePattern(pattern, u''.join(result).replace('\0', "'"))

########NEW FILE########
__FILENAME__ = localedata
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Low-level locale data access.

:note: The `Locale` class, which uses this module under the hood, provides a
       more convenient interface for accessing the locale data.
"""

import os
import pickle
try:
    import threading
except ImportError:
    import dummy_threading as threading
from UserDict import DictMixin

__all__ = ['exists', 'list', 'load']
__docformat__ = 'restructuredtext en'

_cache = {}
_cache_lock = threading.RLock()
_dirname = os.path.join(os.path.dirname(__file__), 'localedata')


def exists(name):
    """Check whether locale data is available for the given locale.
    
    :param name: the locale identifier string
    :return: `True` if the locale data exists, `False` otherwise
    :rtype: `bool`
    """
    if name in _cache:
        return True
    return os.path.exists(os.path.join(_dirname, '%s.dat' % name))


def list():
    """Return a list of all locale identifiers for which locale data is
    available.
    
    :return: a list of locale identifiers (strings)
    :rtype: `list`
    :since: version 0.8.1
    """
    return [stem for stem, extension in [
        os.path.splitext(filename) for filename in os.listdir(_dirname)
    ] if extension == '.dat' and stem != 'root']


def load(name, merge_inherited=True):
    """Load the locale data for the given locale.
    
    The locale data is a dictionary that contains much of the data defined by
    the Common Locale Data Repository (CLDR). This data is stored as a
    collection of pickle files inside the ``babel`` package.
    
    >>> d = load('en_US')
    >>> d['languages']['sv']
    u'Swedish'
    
    Note that the results are cached, and subsequent requests for the same
    locale return the same dictionary:
    
    >>> d1 = load('en_US')
    >>> d2 = load('en_US')
    >>> d1 is d2
    True
    
    :param name: the locale identifier string (or "root")
    :param merge_inherited: whether the inherited data should be merged into
                            the data of the requested locale
    :return: the locale data
    :rtype: `dict`
    :raise `IOError`: if no locale data file is found for the given locale
                      identifer, or one of the locales it inherits from
    """
    _cache_lock.acquire()
    try:
        data = _cache.get(name)
        if not data:
            # Load inherited data
            if name == 'root' or not merge_inherited:
                data = {}
            else:
                parts = name.split('_')
                if len(parts) == 1:
                    parent = 'root'
                else:
                    parent = '_'.join(parts[:-1])
                data = load(parent).copy()
            filename = os.path.join(_dirname, '%s.dat' % name)
            fileobj = open(filename, 'rb')
            try:
                if name != 'root' and merge_inherited:
                    merge(data, pickle.load(fileobj))
                else:
                    data = pickle.load(fileobj)
                _cache[name] = data
            finally:
                fileobj.close()
        return data
    finally:
        _cache_lock.release()


def merge(dict1, dict2):
    """Merge the data from `dict2` into the `dict1` dictionary, making copies
    of nested dictionaries.
    
    >>> d = {1: 'foo', 3: 'baz'}
    >>> merge(d, {1: 'Foo', 2: 'Bar'})
    >>> d
    {1: 'Foo', 2: 'Bar', 3: 'baz'}
    
    :param dict1: the dictionary to merge into
    :param dict2: the dictionary containing the data that should be merged
    """
    for key, val2 in dict2.items():
        if val2 is not None:
            val1 = dict1.get(key)
            if isinstance(val2, dict):
                if val1 is None:
                    val1 = {}
                if isinstance(val1, Alias):
                    val1 = (val1, val2)
                elif isinstance(val1, tuple):
                    alias, others = val1
                    others = others.copy()
                    merge(others, val2)
                    val1 = (alias, others)
                else:
                    val1 = val1.copy()
                    merge(val1, val2)
            else:
                val1 = val2
            dict1[key] = val1


class Alias(object):
    """Representation of an alias in the locale data.
    
    An alias is a value that refers to some other part of the locale data,
    as specified by the `keys`.
    """

    def __init__(self, keys):
        self.keys = tuple(keys)

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.keys)

    def resolve(self, data):
        """Resolve the alias based on the given data.
        
        This is done recursively, so if one alias resolves to a second alias,
        that second alias will also be resolved.
        
        :param data: the locale data
        :type data: `dict`
        """
        base = data
        for key in self.keys:
            data = data[key]
        if isinstance(data, Alias):
            data = data.resolve(base)
        elif isinstance(data, tuple):
            alias, others = data
            data = alias.resolve(base)
        return data


class LocaleDataDict(DictMixin, dict):
    """Dictionary wrapper that automatically resolves aliases to the actual
    values.
    """

    def __init__(self, data, base=None):
        dict.__init__(self, data)
        if base is None:
            base = data
        self.base = base

    def __getitem__(self, key):
        orig = val = dict.__getitem__(self, key)
        if isinstance(val, Alias): # resolve an alias
            val = val.resolve(self.base)
        if isinstance(val, tuple): # Merge a partial dict with an alias
            alias, others = val
            val = alias.resolve(self.base).copy()
            merge(val, others)
        if type(val) is dict: # Return a nested alias-resolving dict
            val = LocaleDataDict(val, base=self.base)
        if val is not orig:
            self[key] = val
        return val

    def copy(self):
        return LocaleDataDict(dict.copy(self), base=self.base)

########NEW FILE########
__FILENAME__ = catalog
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Data structures for message catalogs."""

from cgi import parse_header
from datetime import datetime
from difflib import get_close_matches
from email import message_from_string
from copy import copy
import re
try:
    set
except NameError:
    from sets import Set as set
import time

from babel import __version__ as VERSION
from babel.core import Locale
from babel.dates import format_datetime
from babel.messages.plurals import get_plural
from babel.util import odict, distinct, LOCALTZ, UTC, FixedOffsetTimezone

__all__ = ['Message', 'Catalog', 'TranslationError']
__docformat__ = 'restructuredtext en'


PYTHON_FORMAT = re.compile(r'''(?x)
    \%
        (?:\(([\w]*)\))?
        (
            [-#0\ +]?(?:\*|[\d]+)?
            (?:\.(?:\*|[\d]+))?
            [hlL]?
        )
        ([diouxXeEfFgGcrs%])
''')


class Message(object):
    """Representation of a single message in a catalog."""

    def __init__(self, id, string=u'', locations=(), flags=(), auto_comments=(),
                 user_comments=(), previous_id=(), lineno=None):
        """Create the message object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filenname, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments for the message
        :param user_comments: a sequence of user comments for the message
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        """
        self.id = id #: The message ID
        if not string and self.pluralizable:
            string = (u'', u'')
        self.string = string #: The message translation
        self.locations = list(distinct(locations))
        self.flags = set(flags)
        if id and self.python_format:
            self.flags.add('python-format')
        else:
            self.flags.discard('python-format')
        self.auto_comments = list(distinct(auto_comments))
        self.user_comments = list(distinct(user_comments))
        if isinstance(previous_id, basestring):
            self.previous_id = [previous_id]
        else:
            self.previous_id = list(previous_id)
        self.lineno = lineno

    def __repr__(self):
        return '<%s %r (flags: %r)>' % (type(self).__name__, self.id,
                                        list(self.flags))

    def __cmp__(self, obj):
        """Compare Messages, taking into account plural ids"""
        if isinstance(obj, Message):
            plural = self.pluralizable
            obj_plural = obj.pluralizable
            if plural and obj_plural:
                return cmp(self.id[0], obj.id[0])
            elif plural:
                return cmp(self.id[0], obj.id)
            elif obj_plural:
                return cmp(self.id, obj.id[0])
        return cmp(self.id, obj.id)

    def clone(self):
        return Message(*map(copy, (self.id, self.string, self.locations,
                                   self.flags, self.auto_comments,
                                   self.user_comments, self.previous_id,
                                   self.lineno)))

    def check(self, catalog=None):
        """Run various validation checks on the message.  Some validations
        are only performed if the catalog is provided.  This method returns
        a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        :param catalog: A catalog instance that is passed to the checkers
        :see: `Catalog.check` for a way to perform checks for all messages
              in a catalog.
        """
        from babel.messages.checkers import checkers
        errors = []
        for checker in checkers:
            try:
                checker(catalog, self)
            except TranslationError, e:
                errors.append(e)
        return errors

    def fuzzy(self):
        return 'fuzzy' in self.flags
    fuzzy = property(fuzzy, doc="""\
        Whether the translation is fuzzy.

        >>> Message('foo').fuzzy
        False
        >>> msg = Message('foo', 'foo', flags=['fuzzy'])
        >>> msg.fuzzy
        True
        >>> msg
        <Message 'foo' (flags: ['fuzzy'])>

        :type:  `bool`
        """)

    def pluralizable(self):
        return isinstance(self.id, (list, tuple))
    pluralizable = property(pluralizable, doc="""\
        Whether the message is plurizable.

        >>> Message('foo').pluralizable
        False
        >>> Message(('foo', 'bar')).pluralizable
        True

        :type:  `bool`
        """)

    def python_format(self):
        ids = self.id
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        return bool(filter(None, [PYTHON_FORMAT.search(id) for id in ids]))
    python_format = property(python_format, doc="""\
        Whether the message contains Python-style parameters.

        >>> Message('foo %(name)s bar').python_format
        True
        >>> Message(('foo %(name)s', 'foo %(name)s')).python_format
        True

        :type:  `bool`
        """)


class TranslationError(Exception):
    """Exception thrown by translation checkers when invalid message
    translations are encountered."""


DEFAULT_HEADER = u"""\
# Translations template for PROJECT.
# Copyright (C) YEAR ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#"""


class Catalog(object):
    """Representation of a message catalog."""

    def __init__(self, locale=None, domain=None, header_comment=DEFAULT_HEADER,
                 project=None, version=None, copyright_holder=None,
                 msgid_bugs_address=None, creation_date=None,
                 revision_date=None, last_translator=None, language_team=None,
                 charset='utf-8', fuzzy=True):
        """Initialize the catalog object.

        :param locale: the locale identifier or `Locale` object, or `None`
                       if the catalog is not bound to a locale (which basically
                       means it's a template)
        :param domain: the message domain
        :param header_comment: the header comment as string, or `None` for the
                               default header
        :param project: the project's name
        :param version: the project's version
        :param copyright_holder: the copyright holder of the catalog
        :param msgid_bugs_address: the email address or URL to submit bug
                                   reports to
        :param creation_date: the date the catalog was created
        :param revision_date: the date the catalog was revised
        :param last_translator: the name and email of the last translator
        :param language_team: the name and email of the language team
        :param charset: the encoding to use in the output
        :param fuzzy: the fuzzy bit on the catalog header
        """
        self.domain = domain #: The message domain
        if locale:
            locale = Locale.parse(locale)
        self.locale = locale #: The locale or `None`
        self._header_comment = header_comment
        self._messages = odict()

        self.project = project or 'PROJECT' #: The project name
        self.version = version or 'VERSION' #: The project version
        self.copyright_holder = copyright_holder or 'ORGANIZATION'
        self.msgid_bugs_address = msgid_bugs_address or 'EMAIL@ADDRESS'

        self.last_translator = last_translator or 'FULL NAME <EMAIL@ADDRESS>'
        """Name and email address of the last translator."""
        self.language_team = language_team or 'LANGUAGE <LL@li.org>'
        """Name and email address of the language team."""

        self.charset = charset or 'utf-8'

        if creation_date is None:
            creation_date = datetime.now(LOCALTZ)
        elif isinstance(creation_date, datetime) and not creation_date.tzinfo:
            creation_date = creation_date.replace(tzinfo=LOCALTZ)
        self.creation_date = creation_date #: Creation date of the template
        if revision_date is None:
            revision_date = datetime.now(LOCALTZ)
        elif isinstance(revision_date, datetime) and not revision_date.tzinfo:
            revision_date = revision_date.replace(tzinfo=LOCALTZ)
        self.revision_date = revision_date #: Last revision date of the catalog
        self.fuzzy = fuzzy #: Catalog header fuzzy bit (`True` or `False`)

        self.obsolete = odict() #: Dictionary of obsolete messages
        self._num_plurals = None
        self._plural_expr = None

    def _get_header_comment(self):
        comment = self._header_comment
        comment = comment.replace('PROJECT', self.project) \
                         .replace('VERSION', self.version) \
                         .replace('YEAR', self.revision_date.strftime('%Y')) \
                         .replace('ORGANIZATION', self.copyright_holder)
        if self.locale:
            comment = comment.replace('Translations template', '%s translations'
                                      % self.locale.english_name)
        return comment

    def _set_header_comment(self, string):
        self._header_comment = string

    header_comment = property(_get_header_comment, _set_header_comment, doc="""\
    The header comment for the catalog.

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> print catalog.header_comment #doctest: +ELLIPSIS
    # Translations template for Foobar.
    # Copyright (C) ... Foo Company
    # This file is distributed under the same license as the Foobar project.
    # FIRST AUTHOR <EMAIL@ADDRESS>, ....
    #

    The header can also be set from a string. Any known upper-case variables
    will be replaced when the header is retrieved again:

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> catalog.header_comment = '''\\
    ... # The POT for my really cool PROJECT project.
    ... # Copyright (C) 1990-2003 ORGANIZATION
    ... # This file is distributed under the same license as the PROJECT
    ... # project.
    ... #'''
    >>> print catalog.header_comment
    # The POT for my really cool Foobar project.
    # Copyright (C) 1990-2003 Foo Company
    # This file is distributed under the same license as the Foobar
    # project.
    #

    :type: `unicode`
    """)

    def _get_mime_headers(self):
        headers = []
        headers.append(('Project-Id-Version',
                        '%s %s' % (self.project, self.version)))
        headers.append(('Report-Msgid-Bugs-To', self.msgid_bugs_address))
        headers.append(('POT-Creation-Date',
                        format_datetime(self.creation_date, 'yyyy-MM-dd HH:mmZ',
                                        locale='en')))
        if self.locale is None:
            headers.append(('PO-Revision-Date', 'YEAR-MO-DA HO:MI+ZONE'))
            headers.append(('Last-Translator', 'FULL NAME <EMAIL@ADDRESS>'))
            headers.append(('Language-Team', 'LANGUAGE <LL@li.org>'))
        else:
            headers.append(('PO-Revision-Date',
                            format_datetime(self.revision_date,
                                            'yyyy-MM-dd HH:mmZ', locale='en')))
            headers.append(('Last-Translator', self.last_translator))
            headers.append(('Language-Team',
                           self.language_team.replace('LANGUAGE',
                                                      str(self.locale))))
            headers.append(('Plural-Forms', self.plural_forms))
        headers.append(('MIME-Version', '1.0'))
        headers.append(('Content-Type',
                        'text/plain; charset=%s' % self.charset))
        headers.append(('Content-Transfer-Encoding', '8bit'))
        headers.append(('Generated-By', 'Babel %s\n' % VERSION))
        return headers

    def _set_mime_headers(self, headers):
        for name, value in headers:
            if name.lower() == 'content-type':
                mimetype, params = parse_header(value)
                if 'charset' in params:
                    self.charset = params['charset'].lower()
                break
        for name, value in headers:
            name = name.lower().decode(self.charset)
            value = value.decode(self.charset)
            if name == 'project-id-version':
                parts = value.split(' ')
                self.project = u' '.join(parts[:-1])
                self.version = parts[-1]
            elif name == 'report-msgid-bugs-to':
                self.msgid_bugs_address = value
            elif name == 'last-translator':
                self.last_translator = value
            elif name == 'language-team':
                self.language_team = value
            elif name == 'plural-forms':
                _, params = parse_header(' ;' + value)
                self._num_plurals = int(params.get('nplurals', 2))
                self._plural_expr = params.get('plural', '(n != 1)')
            elif name == 'pot-creation-date':
                # FIXME: this should use dates.parse_datetime as soon as that
                #        is ready
                value, tzoffset, _ = re.split('[+-](\d{4})$', value, 1)
                tt = time.strptime(value, '%Y-%m-%d %H:%M')
                ts = time.mktime(tt)
                tzoffset = FixedOffsetTimezone(int(tzoffset[:2]) * 60 +
                                               int(tzoffset[2:]))
                dt = datetime.fromtimestamp(ts)
                self.creation_date = dt.replace(tzinfo=tzoffset)

    mime_headers = property(_get_mime_headers, _set_mime_headers, doc="""\
    The MIME headers of the catalog, used for the special ``msgid ""`` entry.

    The behavior of this property changes slightly depending on whether a locale
    is set or not, the latter indicating that the catalog is actually a template
    for actual translations.

    Here's an example of the output for such a catalog template:

    >>> created = datetime(1990, 4, 1, 15, 30, tzinfo=UTC)
    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   creation_date=created)
    >>> for name, value in catalog.mime_headers:
    ...     print '%s: %s' % (name, value)
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    And here's an example of the output when the locale is set:

    >>> revised = datetime(1990, 8, 3, 12, 0, tzinfo=UTC)
    >>> catalog = Catalog(locale='de_DE', project='Foobar', version='1.0',
    ...                   creation_date=created, revision_date=revised,
    ...                   last_translator='John Doe <jd@example.com>',
    ...                   language_team='de_DE <de@example.com>')
    >>> for name, value in catalog.mime_headers:
    ...     print '%s: %s' % (name, value)
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: 1990-08-03 12:00+0000
    Last-Translator: John Doe <jd@example.com>
    Language-Team: de_DE <de@example.com>
    Plural-Forms: nplurals=2; plural=(n != 1)
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    :type: `list`
    """)

    def num_plurals(self):
        if self._num_plurals is None:
            num = 2
            if self.locale:
                num = get_plural(self.locale)[0]
            self._num_plurals = num
        return self._num_plurals
    num_plurals = property(num_plurals, doc="""\
    The number of plurals used by the catalog or locale.

    >>> Catalog(locale='en').num_plurals
    2
    >>> Catalog(locale='ga').num_plurals
    3

    :type: `int`
    """)

    def plural_expr(self):
        if self._plural_expr is None:
            expr = '(n != 1)'
            if self.locale:
                expr = get_plural(self.locale)[1]
            self._plural_expr = expr
        return self._plural_expr
    plural_expr = property(plural_expr, doc="""\
    The plural expression used by the catalog or locale.

    >>> Catalog(locale='en').plural_expr
    '(n != 1)'
    >>> Catalog(locale='ga').plural_expr
    '(n==1 ? 0 : n==2 ? 1 : 2)'

    :type: `basestring`
    """)

    def plural_forms(self):
        return 'nplurals=%s; plural=%s' % (self.num_plurals, self.plural_expr)
    plural_forms = property(plural_forms, doc="""\
    Return the plural forms declaration for the locale.

    >>> Catalog(locale='en').plural_forms
    'nplurals=2; plural=(n != 1)'
    >>> Catalog(locale='pt_BR').plural_forms
    'nplurals=2; plural=(n > 1)'

    :type: `str`
    """)

    def __contains__(self, id):
        """Return whether the catalog has a message with the specified ID."""
        return self._key_for(id) in self._messages

    def __len__(self):
        """The number of messages in the catalog.

        This does not include the special ``msgid ""`` entry.
        """
        return len(self._messages)

    def __iter__(self):
        """Iterates through all the entries in the catalog, in the order they
        were added, yielding a `Message` object for every entry.

        :rtype: ``iterator``
        """
        buf = []
        for name, value in self.mime_headers:
            buf.append('%s: %s' % (name, value))
        flags = set()
        if self.fuzzy:
            flags |= set(['fuzzy'])
        yield Message(u'', '\n'.join(buf), flags=flags)
        for key in self._messages:
            yield self._messages[key]

    def __repr__(self):
        locale = ''
        if self.locale:
            locale = ' %s' % self.locale
        return '<%s %r%s>' % (type(self).__name__, self.domain, locale)

    def __delitem__(self, id):
        """Delete the message with the specified ID."""
        key = self._key_for(id)
        if key in self._messages:
            del self._messages[key]

    def __getitem__(self, id):
        """Return the message with the specified ID.

        :param id: the message ID
        :return: the message with the specified ID, or `None` if no such message
                 is in the catalog
        :rtype: `Message`
        """
        return self._messages.get(self._key_for(id))

    def __setitem__(self, id, message):
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo')
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        If a message with that ID is already in the catalog, it is updated
        to include the locations and flags of the new message.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo', locations=[('main.py', 1)])
        >>> catalog[u'foo'].locations
        [('main.py', 1)]
        >>> catalog[u'foo'] = Message(u'foo', locations=[('utils.py', 5)])
        >>> catalog[u'foo'].locations
        [('main.py', 1), ('utils.py', 5)]

        :param id: the message ID
        :param message: the `Message` object
        """
        assert isinstance(message, Message), 'expected a Message object'
        key = self._key_for(id)
        current = self._messages.get(key)
        if current:
            if message.pluralizable and not current.pluralizable:
                # The new message adds pluralization
                current.id = message.id
                current.string = message.string
            current.locations = list(distinct(current.locations +
                                              message.locations))
            current.auto_comments = list(distinct(current.auto_comments +
                                                  message.auto_comments))
            current.user_comments = list(distinct(current.user_comments +
                                                  message.user_comments))
            current.flags |= message.flags
            message = current
        elif id == '':
            # special treatment for the header message
            headers = message_from_string(message.string.encode(self.charset))
            self.mime_headers = headers.items()
            self.header_comment = '\n'.join(['# %s' % comment for comment
                                             in message.user_comments])
            self.fuzzy = message.fuzzy
        else:
            if isinstance(id, (list, tuple)):
                assert isinstance(message.string, (list, tuple)), \
                    'Expected sequence but got %s' % type(message.string)
            self._messages[key] = message

    def add(self, id, string=None, locations=(), flags=(), auto_comments=(),
            user_comments=(), previous_id=(), lineno=None):
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog.add(u'foo')
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        This method simply constructs a `Message` object with the given
        arguments and invokes `__setitem__` with that object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filenname, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments
        :param user_comments: a sequence of user comments
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        """
        self[id] = Message(id, string, list(locations), flags, auto_comments,
                           user_comments, previous_id, lineno=lineno)

    def check(self):
        """Run various validation checks on the translations in the catalog.

        For every message which fails validation, this method yield a
        ``(message, errors)`` tuple, where ``message`` is the `Message` object
        and ``errors`` is a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        """
        for message in self._messages.values():
            errors = message.check(catalog=self)
            if errors:
                yield message, errors

    def update(self, template, no_fuzzy_matching=False):
        """Update the catalog based on the given template catalog.

        >>> from babel.messages import Catalog
        >>> template = Catalog()
        >>> template.add('green', locations=[('main.py', 99)])
        >>> template.add('blue', locations=[('main.py', 100)])
        >>> template.add(('salad', 'salads'), locations=[('util.py', 42)])
        >>> catalog = Catalog(locale='de_DE')
        >>> catalog.add('blue', u'blau', locations=[('main.py', 98)])
        >>> catalog.add('head', u'Kopf', locations=[('util.py', 33)])
        >>> catalog.add(('salad', 'salads'), (u'Salat', u'Salate'),
        ...             locations=[('util.py', 38)])

        >>> catalog.update(template)
        >>> len(catalog)
        3

        >>> msg1 = catalog['green']
        >>> msg1.string
        >>> msg1.locations
        [('main.py', 99)]

        >>> msg2 = catalog['blue']
        >>> msg2.string
        u'blau'
        >>> msg2.locations
        [('main.py', 100)]

        >>> msg3 = catalog['salad']
        >>> msg3.string
        (u'Salat', u'Salate')
        >>> msg3.locations
        [('util.py', 42)]

        Messages that are in the catalog but not in the template are removed
        from the main collection, but can still be accessed via the `obsolete`
        member:

        >>> 'head' in catalog
        False
        >>> catalog.obsolete.values()
        [<Message 'head' (flags: [])>]

        :param template: the reference catalog, usually read from a POT file
        :param no_fuzzy_matching: whether to use fuzzy matching of message IDs
        """
        messages = self._messages
        remaining = messages.copy()
        self._messages = odict()

        # Prepare for fuzzy matching
        fuzzy_candidates = []
        if not no_fuzzy_matching:
            fuzzy_candidates = [
                self._key_for(msgid) for msgid in messages
                if msgid and messages[msgid].string
            ]
        fuzzy_matches = set()

        def _merge(message, oldkey, newkey):
            message = message.clone()
            fuzzy = False
            if oldkey != newkey:
                fuzzy = True
                fuzzy_matches.add(oldkey)
                oldmsg = messages.get(oldkey)
                if isinstance(oldmsg.id, basestring):
                    message.previous_id = [oldmsg.id]
                else:
                    message.previous_id = list(oldmsg.id)
            else:
                oldmsg = remaining.pop(oldkey, None)
            message.string = oldmsg.string
            if isinstance(message.id, (list, tuple)):
                if not isinstance(message.string, (list, tuple)):
                    fuzzy = True
                    message.string = tuple(
                        [message.string] + ([u''] * (len(message.id) - 1))
                    )
                elif len(message.string) != self.num_plurals:
                    fuzzy = True
                    message.string = tuple(message.string[:len(oldmsg.string)])
            elif isinstance(message.string, (list, tuple)):
                fuzzy = True
                message.string = message.string[0]
            message.flags |= oldmsg.flags
            if fuzzy:
                message.flags |= set([u'fuzzy'])
            self[message.id] = message

        for message in template:
            if message.id:
                key = self._key_for(message.id)
                if key in messages:
                    _merge(message, key, key)
                else:
                    if no_fuzzy_matching is False:
                        # do some fuzzy matching with difflib
                        matches = get_close_matches(key.lower().strip(),
                                                    fuzzy_candidates, 1)
                        if matches:
                            _merge(message, matches[0], key)
                            continue

                    self[message.id] = message

        self.obsolete = odict()
        for msgid in remaining:
            if no_fuzzy_matching or msgid not in fuzzy_matches:
                self.obsolete[msgid] = remaining[msgid]

    def _key_for(self, id):
        """The key for a message is just the singular ID even for pluralizable
        messages.
        """
        key = id
        if isinstance(key, (list, tuple)):
            key = id[0]
        return key

########NEW FILE########
__FILENAME__ = checkers
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Various routines that help with validation of translations.

:since: version 0.9
"""

from itertools import izip
from babel.messages.catalog import TranslationError, PYTHON_FORMAT

#: list of format chars that are compatible to each other
_string_format_compatibilities = [
    set(['i', 'd', 'u']),
    set(['x', 'X']),
    set(['f', 'F', 'g', 'G'])
]


def num_plurals(catalog, message):
    """Verify the number of plurals in the translation."""
    if not message.pluralizable:
        if not isinstance(message.string, basestring):
            raise TranslationError("Found plural forms for non-pluralizable "
                                   "message")
        return

    # skip further tests if no catalog is provided.
    elif catalog is None:
        return

    msgstrs = message.string
    if not isinstance(msgstrs, (list, tuple)):
        msgstrs = (msgstrs,)
    if len(msgstrs) != catalog.num_plurals:
        raise TranslationError("Wrong number of plural forms (expected %d)" %
                               catalog.num_plurals)


def python_format(catalog, message):
    """Verify the format string placeholders in the translation."""
    if 'python-format' not in message.flags:
        return
    msgids = message.id
    if not isinstance(msgids, (list, tuple)):
        msgids = (msgids,)
    msgstrs = message.string
    if not isinstance(msgstrs, (list, tuple)):
        msgstrs = (msgstrs,)

    for msgid, msgstr in izip(msgids, msgstrs):
        if msgstr:
            _validate_format(msgid, msgstr)


def _validate_format(format, alternative):
    """Test format string `alternative` against `format`.  `format` can be the
    msgid of a message and `alternative` one of the `msgstr`\s.  The two
    arguments are not interchangeable as `alternative` may contain less
    placeholders if `format` uses named placeholders.

    If `format` does not use string formatting a `ValueError` is raised.

    If the string formatting of `alternative` is compatible to `format` the
    function returns `None`, otherwise a `TranslationError` is raised.

    Examples for compatible format strings:

    >>> _validate_format('Hello %s!', 'Hallo %s!')
    >>> _validate_format('Hello %i!', 'Hallo %d!')

    Example for an incompatible format strings:

    >>> _validate_format('Hello %(name)s!', 'Hallo %s!')
    Traceback (most recent call last):
      ...
    TranslationError: the format strings are of different kinds

    This function is used by the `python_format` checker.

    :param format: The original format string
    :param alternative: The alternative format string that should be checked
                        against format
    :return: None on success
    :raises TranslationError: on formatting errors
    """

    def _parse(string):
        result = []
        for match in PYTHON_FORMAT.finditer(string):
            name, format, typechar = match.groups()
            if typechar == '%' and name is None:
                continue
            result.append((name, str(typechar)))
        return result

    def _compatible(a, b):
        if a == b:
            return True
        for set in _string_format_compatibilities:
            if a in set and b in set:
                return True
        return False

    def _check_positional(results):
        positional = None
        for name, char in results:
            if positional is None:
                positional = name is None
            else:
                if (name is None) != positional:
                    raise TranslationError('format string mixes positional '
                                           'and named placeholders')
        return bool(positional)

    a, b = map(_parse, (format, alternative))

    # if a does not use string formattings, we are dealing with invalid
    # input data.  This function only works if the first string provided
    # does contain string format chars
    if not a:
        raise ValueError('original string provided does not use string '
                         'formatting.')

    # now check if both strings are positional or named
    a_positional, b_positional = map(_check_positional, (a, b))
    if a_positional and not b_positional and not b:
        raise TranslationError('placeholders are incompatible')
    elif a_positional != b_positional:
        raise TranslationError('the format strings are of different kinds')

    # if we are operating on positional strings both must have the
    # same number of format chars and those must be compatible
    if a_positional:
        if len(a) != len(b):
            raise TranslationError('positional format placeholders are '
                                   'unbalanced')
        for idx, ((_, first), (_, second)) in enumerate(izip(a, b)):
            if not _compatible(first, second):
                raise TranslationError('incompatible format for placeholder '
                                       '%d: %r and %r are not compatible' %
                                       (idx + 1, first, second))

    # otherwise the second string must not have names the first one
    # doesn't have and the types of those included must be compatible
    else:
        type_map = dict(a)
        for name, typechar in b:
            if name not in type_map:
                raise TranslationError('unknown named placeholder %r' % name)
            elif not _compatible(typechar, type_map[name]):
                raise TranslationError('incompatible format for '
                                       'placeholder %r: '
                                       '%r and %r are not compatible' %
                                       (name, typechar, type_map[name]))


def _find_checkers():
    try:
        from pkg_resources import working_set
    except ImportError:
        return [num_plurals, python_format]
    checkers = []
    for entry_point in working_set.iter_entry_points('babel.checkers'):
        checkers.append(entry_point.load())
    return checkers


checkers = _find_checkers()

########NEW FILE########
__FILENAME__ = extract
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Basic infrastructure for extracting localizable messages from source files.

This module defines an extensible system for collecting localizable message
strings from a variety of sources. A native extractor for Python source files
is builtin, extractors for other sources can be added using very simple plugins.

The main entry points into the extraction functionality are the functions
`extract_from_dir` and `extract_from_file`.
"""

import os
try:
    set
except NameError:
    from sets import Set as set
import sys
from tokenize import generate_tokens, COMMENT, NAME, OP, STRING

from babel.util import parse_encoding, pathmatch, relpath
from textwrap import dedent

__all__ = ['extract', 'extract_from_dir', 'extract_from_file']
__docformat__ = 'restructuredtext en'

GROUP_NAME = 'babel.extractors'

DEFAULT_KEYWORDS = {
    '_': None,
    'gettext': None,
    'ngettext': (1, 2),
    'ugettext': None,
    'ungettext': (1, 2),
    'dgettext': (2,),
    'dngettext': (2, 3),
    'N_': None
}

DEFAULT_MAPPING = [('**.py', 'python')]

empty_msgid_warning = (
'%s: warning: Empty msgid.  It is reserved by GNU gettext: gettext("") '
'returns the header entry with meta information, not the empty string.')


def _strip_comment_tags(comments, tags):
    """Helper function for `extract` that strips comment tags from strings
    in a list of comment lines.  This functions operates in-place.
    """
    def _strip(line):
        for tag in tags:
            if line.startswith(tag):
                return line[len(tag):].strip()
        return line
    comments[:] = map(_strip, comments)


def extract_from_dir(dirname=os.getcwd(), method_map=DEFAULT_MAPPING,
                     options_map=None, keywords=DEFAULT_KEYWORDS,
                     comment_tags=(), callback=None, strip_comment_tags=False):
    """Extract messages from any source files found in the given directory.

    This function generates tuples of the form:

        ``(filename, lineno, message, comments)``

    Which extraction method is used per file is determined by the `method_map`
    parameter, which maps extended glob patterns to extraction method names.
    For example, the following is the default mapping:

    >>> method_map = [
    ...     ('**.py', 'python')
    ... ]

    This basically says that files with the filename extension ".py" at any
    level inside the directory should be processed by the "python" extraction
    method. Files that don't match any of the mapping patterns are ignored. See
    the documentation of the `pathmatch` function for details on the pattern
    syntax.

    The following extended mapping would also use the "genshi" extraction
    method on any file in "templates" subdirectory:

    >>> method_map = [
    ...     ('**/templates/**.*', 'genshi'),
    ...     ('**.py', 'python')
    ... ]

    The dictionary provided by the optional `options_map` parameter augments
    these mappings. It uses extended glob patterns as keys, and the values are
    dictionaries mapping options names to option values (both strings).

    The glob patterns of the `options_map` do not necessarily need to be the
    same as those used in the method mapping. For example, while all files in
    the ``templates`` folders in an application may be Genshi applications, the
    options for those files may differ based on extension:

    >>> options_map = {
    ...     '**/templates/**.txt': {
    ...         'template_class': 'genshi.template:TextTemplate',
    ...         'encoding': 'latin-1'
    ...     },
    ...     '**/templates/**.html': {
    ...         'include_attrs': ''
    ...     }
    ... }

    :param dirname: the path to the directory to extract messages from
    :param method_map: a list of ``(pattern, method)`` tuples that maps of
                       extraction method names to extended glob patterns
    :param options_map: a dictionary of additional options (optional)
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of tags of translator comments to search for
                         and include in the results
    :param callback: a function that is called for every file that message are
                     extracted from, just before the extraction itself is
                     performed; the function is passed the filename, the name
                     of the extraction method and and the options dictionary as
                     positional arguments, in that order
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :return: an iterator over ``(filename, lineno, funcname, message)`` tuples
    :rtype: ``iterator``
    :see: `pathmatch`
    """
    if options_map is None:
        options_map = {}

    absname = os.path.abspath(dirname)
    for root, dirnames, filenames in os.walk(absname):
        for subdir in dirnames:
            if subdir.startswith('.') or subdir.startswith('_'):
                dirnames.remove(subdir)
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            filename = relpath(
                os.path.join(root, filename).replace(os.sep, '/'),
                dirname
            )
            for pattern, method in method_map:
                if pathmatch(pattern, filename):
                    filepath = os.path.join(absname, filename)
                    options = {}
                    for opattern, odict in options_map.items():
                        if pathmatch(opattern, filename):
                            options = odict
                    if callback:
                        callback(filename, method, options)
                    for lineno, message, comments in \
                          extract_from_file(method, filepath,
                                            keywords=keywords,
                                            comment_tags=comment_tags,
                                            options=options,
                                            strip_comment_tags=
                                                strip_comment_tags):
                        yield filename, lineno, message, comments
                    break


def extract_from_file(method, filename, keywords=DEFAULT_KEYWORDS,
                      comment_tags=(), options=None, strip_comment_tags=False):
    """Extract messages from a specific file.

    This function returns a list of tuples of the form:

        ``(lineno, funcname, message)``

    :param filename: the path to the file to extract messages from
    :param method: a string specifying the extraction method (.e.g. "python")
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :param options: a dictionary of additional options (optional)
    :return: the list of extracted messages
    :rtype: `list`
    """
    fileobj = open(filename, 'U')
    try:
        return list(extract(method, fileobj, keywords, comment_tags, options,
                            strip_comment_tags))
    finally:
        fileobj.close()


def extract(method, fileobj, keywords=DEFAULT_KEYWORDS, comment_tags=(),
            options=None, strip_comment_tags=False):
    """Extract messages from the given file-like object using the specified
    extraction method.

    This function returns a list of tuples of the form:

        ``(lineno, message, comments)``

    The implementation dispatches the actual extraction to plugins, based on the
    value of the ``method`` parameter.

    >>> source = '''# foo module
    ... def run(argv):
    ...    print _('Hello, world!')
    ... '''

    >>> from StringIO import StringIO
    >>> for message in extract('python', StringIO(source)):
    ...     print message
    (3, u'Hello, world!', [])

    :param method: a string specifying the extraction method (.e.g. "python");
                   if this is a simple name, the extraction function will be
                   looked up by entry point; if it is an explicit reference
                   to a function (of the form ``package.module:funcname`` or
                   ``package.module.funcname``), the corresponding function
                   will be imported and used
    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a dictionary mapping keywords (i.e. names of functions
                     that should be recognized as translation functions) to
                     tuples that specify which of their arguments contain
                     localizable strings
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :param strip_comment_tags: a flag that if set to `True` causes all comment
                               tags to be removed from the collected comments.
    :return: the list of extracted messages
    :rtype: `list`
    :raise ValueError: if the extraction method is not registered
    """
    func = None
    if ':' in method or '.' in method:
        if ':' not in method:
            lastdot = method.rfind('.')
            module, attrname = method[:lastdot], method[lastdot + 1:]
        else:
            module, attrname = method.split(':', 1)
        func = getattr(__import__(module, {}, {}, [attrname]), attrname)
    else:
        try:
            from pkg_resources import working_set
        except ImportError:
            # pkg_resources is not available, so we resort to looking up the
            # builtin extractors directly
            builtin = {'ignore': extract_nothing, 'python': extract_python}
            func = builtin.get(method)
        else:
            for entry_point in working_set.iter_entry_points(GROUP_NAME,
                                                             method):
                func = entry_point.load(require=True)
                break
    if func is None:
        raise ValueError('Unknown extraction method %r' % method)

    results = func(fileobj, keywords.keys(), comment_tags,
                   options=options or {})

    for lineno, funcname, messages, comments in results:
        if funcname:
            spec = keywords[funcname] or (1,)
        else:
            spec = (1,)
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        if not messages:
            continue

        # Validate the messages against the keyword's specification
        msgs = []
        invalid = False
        # last_index is 1 based like the keyword spec
        last_index = len(messages)
        for index in spec:
            if last_index < index:
                # Not enough arguments
                invalid = True
                break
            message = messages[index - 1]
            if message is None:
                invalid = True
                break
            msgs.append(message)
        if invalid:
            continue

        first_msg_index = spec[0] - 1
        if not messages[first_msg_index]:
            # An empty string msgid isn't valid, emit a warning
            where = '%s:%i' % (hasattr(fileobj, 'name') and \
                                   fileobj.name or '(unknown)', lineno)
            print >> sys.stderr, empty_msgid_warning % where
            continue

        messages = tuple(msgs)
        if len(messages) == 1:
            messages = messages[0]

        if strip_comment_tags:
            _strip_comment_tags(comments, comment_tags)
        yield lineno, messages, comments


def extract_nothing(fileobj, keywords, comment_tags, options):
    """Pseudo extractor that does not actually extract anything, but simply
    returns an empty list.
    """
    return []


def extract_python(fileobj, keywords, comment_tags, options):
    """Extract messages from Python source code.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    funcname = lineno = message_lineno = None
    call_stack = -1
    buf = []
    messages = []
    translator_comments = []
    in_def = in_translator_comments = False
    comment_tag = None

    encoding = parse_encoding(fileobj) or options.get('encoding', 'iso-8859-1')

    tokens = generate_tokens(fileobj.readline)
    for tok, value, (lineno, _), _, _ in tokens:
        if call_stack == -1 and tok == NAME and value in ('def', 'class'):
            in_def = True
        elif tok == OP and value == '(':
            if in_def:
                # Avoid false positives for declarations such as:
                # def gettext(arg='message'):
                in_def = False
                continue
            if funcname:
                message_lineno = lineno
                call_stack += 1
        elif in_def and tok == OP and value == ':':
            # End of a class definition without parens
            in_def = False
            continue
        elif call_stack == -1 and tok == COMMENT:
            # Strip the comment token from the line
            value = value.decode(encoding)[1:].strip()
            if in_translator_comments and \
                    translator_comments[-1][0] == lineno - 1:
                # We're already inside a translator comment, continue appending
                translator_comments.append((lineno, value))
                continue
            # If execution reaches this point, let's see if comment line
            # starts with one of the comment tags
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    translator_comments.append((lineno, value))
                    break
        elif funcname and call_stack == 0:
            if tok == OP and value == ')':
                if buf:
                    messages.append(''.join(buf))
                    del buf[:]
                else:
                    messages.append(None)

                if len(messages) > 1:
                    messages = tuple(messages)
                else:
                    messages = messages[0]
                # Comments don't apply unless they immediately preceed the
                # message
                if translator_comments and \
                        translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                yield (message_lineno, funcname, messages,
                       [comment[1] for comment in translator_comments])

                funcname = lineno = message_lineno = None
                call_stack = -1
                messages = []
                translator_comments = []
                in_translator_comments = False
            elif tok == STRING:
                # Unwrap quotes in a safe manner, maintaining the string's
                # encoding
                # https://sourceforge.net/tracker/?func=detail&atid=355470&
                # aid=617979&group_id=5470
                value = eval('# coding=%s\n%s' % (encoding, value),
                             {'__builtins__':{}}, {})
                if isinstance(value, str):
                    value = value.decode(encoding)
                buf.append(value)
            elif tok == OP and value == ',':
                if buf:
                    messages.append(''.join(buf))
                    del buf[:]
                else:
                    messages.append(None)
                if translator_comments:
                    # We have translator comments, and since we're on a
                    # comma(,) user is allowed to break into a new line
                    # Let's increase the last comment's lineno in order
                    # for the comment to still be a valid one
                    old_lineno, old_comment = translator_comments.pop()
                    translator_comments.append((old_lineno+1, old_comment))
        elif call_stack > 0 and tok == OP and value == ')':
            call_stack -= 1
        elif funcname and call_stack == -1:
            funcname = None
        elif tok == NAME and value in keywords:
            funcname = value


def extract_javascript(fileobj, keywords, comment_tags, options):
    """Extract messages from JavaScript source code.

    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    from babel.messages.jslexer import tokenize, unquote_string
    funcname = message_lineno = None
    messages = []
    last_argument = None
    translator_comments = []
    concatenate_next = False
    encoding = options.get('encoding', 'utf-8')
    last_token = None
    call_stack = -1

    for token in tokenize(fileobj.read().decode(encoding)):
        if token.type == 'operator' and token.value == '(':
            if funcname:
                message_lineno = token.lineno
                call_stack += 1

        elif call_stack == -1 and token.type == 'linecomment':
            value = token.value[2:].strip()
            if translator_comments and \
               translator_comments[-1][0] == token.lineno - 1:
                translator_comments.append((token.lineno, value))
                continue

            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    translator_comments.append((token.lineno, value.strip()))
                    break

        elif token.type == 'multilinecomment':
            # only one multi-line comment may preceed a translation
            translator_comments = []
            value = token.value[2:-2].strip()
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    lines = value.splitlines()
                    if lines:
                        lines[0] = lines[0].strip()
                        lines[1:] = dedent('\n'.join(lines[1:])).splitlines()
                        for offset, line in enumerate(lines):
                            translator_comments.append((token.lineno + offset,
                                                        line))
                    break

        elif funcname and call_stack == 0:
            if token.type == 'operator' and token.value == ')':
                if last_argument is not None:
                    messages.append(last_argument)
                if len(messages) > 1:
                    messages = tuple(messages)
                elif messages:
                    messages = messages[0]
                else:
                    messages = None

                # Comments don't apply unless they immediately preceed the
                # message
                if translator_comments and \
                   translator_comments[-1][0] < message_lineno - 1:
                    translator_comments = []

                if messages is not None:
                    yield (message_lineno, funcname, messages,
                           [comment[1] for comment in translator_comments])

                funcname = message_lineno = last_argument = None
                concatenate_next = False
                translator_comments = []
                messages = []
                call_stack = -1

            elif token.type == 'string':
                new_value = unquote_string(token.value)
                if concatenate_next:
                    last_argument = (last_argument or '') + new_value
                    concatenate_next = False
                else:
                    last_argument = new_value

            elif token.type == 'operator':
                if token.value == ',':
                    if last_argument is not None:
                        messages.append(last_argument)
                        last_argument = None
                    else:
                        messages.append(None)
                    concatenate_next = False
                elif token.value == '+':
                    concatenate_next = True

        elif call_stack > 0 and token.type == 'operator' \
             and token.value == ')':
            call_stack -= 1

        elif funcname and call_stack == -1:
            funcname = None

        elif call_stack == -1 and token.type == 'name' and \
             token.value in keywords and \
             (last_token is None or last_token.type != 'name' or
              last_token.value != 'function'):
            funcname = token.value

        last_token = token

########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Frontends for the message extraction functionality."""

from ConfigParser import RawConfigParser
from datetime import datetime
from distutils import log
from distutils.cmd import Command
from distutils.errors import DistutilsOptionError, DistutilsSetupError
from locale import getpreferredencoding
import logging
from optparse import OptionParser
import os
import re
import shutil
from StringIO import StringIO
import sys
import tempfile

from babel import __version__ as VERSION
from babel import Locale, localedata
from babel.core import UnknownLocaleError
from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir, DEFAULT_KEYWORDS, \
                                   DEFAULT_MAPPING
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from babel.messages.plurals import PLURALS
from babel.util import odict, LOCALTZ

__all__ = ['CommandLineInterface', 'compile_catalog', 'extract_messages',
           'init_catalog', 'check_message_extractors', 'update_catalog']
__docformat__ = 'restructuredtext en'


class compile_catalog(Command):
    """Catalog compilation command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import compile_catalog

        setup(
            ...
            cmdclass = {'compile_catalog': compile_catalog}
        )

    :since: version 0.9
    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'compile message catalogs to binary MO files'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('directory=', 'd',
         'path to base directory containing the catalogs'),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('use-fuzzy', 'f',
         'also include fuzzy translations'),
        ('statistics', None,
         'print statistics about translations')
    ]
    boolean_options = ['use-fuzzy', 'statistics']

    def initialize_options(self):
        self.domain = 'messages'
        self.directory = None
        self.input_file = None
        self.output_file = None
        self.locale = None
        self.use_fuzzy = False
        self.statistics = False

    def finalize_options(self):
        if not self.input_file and not self.directory:
            raise DistutilsOptionError('you must specify either the input file '
                                       'or the base directory')
        if not self.output_file and not self.directory:
            raise DistutilsOptionError('you must specify either the input file '
                                       'or the base directory')

    def run(self):
        po_files = []
        mo_files = []

        if not self.input_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.directory, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.mo'))
            else:
                for locale in os.listdir(self.directory):
                    po_file = os.path.join(self.directory, locale,
                                           'LC_MESSAGES', self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(self.directory, locale,
                                                     'LC_MESSAGES',
                                                     self.domain + '.mo'))
        else:
            po_files.append((self.locale, self.input_file))
            if self.output_file:
                mo_files.append(self.output_file)
            else:
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             self.domain + '.mo'))

        if not po_files:
            raise DistutilsOptionError('no message catalogs found')

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            infile = open(po_file, 'r')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if self.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated +=1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                log.info('%d of %d messages (%d%%) translated in %r',
                         translated, len(catalog), percentage, po_file)

            if catalog.fuzzy and not self.use_fuzzy:
                log.warn('catalog %r is marked as fuzzy, skipping', po_file)
                continue

            for message, errors in catalog.check():
                for error in errors:
                    log.error('error: %s:%d: %s', po_file, message.lineno,
                              error)

            log.info('compiling catalog %r to %r', po_file, mo_file)

            outfile = open(mo_file, 'wb')
            try:
                write_mo(outfile, catalog, use_fuzzy=self.use_fuzzy)
            finally:
                outfile.close()


class extract_messages(Command):
    """Message extraction command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import extract_messages

        setup(
            ...
            cmdclass = {'extract_messages': extract_messages}
        )

    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'extract localizable strings from the project code'
    user_options = [
        ('charset=', None,
         'charset to use in the output file'),
        ('keywords=', 'k',
         'space-separated list of keywords to look for in addition to the '
         'defaults'),
        ('no-default-keywords', None,
         'do not include the default keywords'),
        ('mapping-file=', 'F',
         'path to the mapping configuration file'),
        ('no-location', None,
         'do not include location comments with filename and line number'),
        ('omit-header', None,
         'do not include msgid "" entry in header'),
        ('output-file=', 'o',
         'name of the output file'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
        ('sort-output', None,
         'generate sorted output (default False)'),
        ('sort-by-file', None,
         'sort output by file location (default False)'),
        ('msgid-bugs-address=', None,
         'set report address for msgid'),
        ('copyright-holder=', None,
         'set copyright holder in output'),
        ('add-comments=', 'c',
         'place comment block with TAG (or those preceding keyword lines) in '
         'output file. Seperate multiple TAGs with commas(,)'),
        ('strip-comments', None,
         'strip the comment TAGs from the comments.'),
        ('input-dirs=', None,
         'directories that should be scanned for messages'),
    ]
    boolean_options = [
        'no-default-keywords', 'no-location', 'omit-header', 'no-wrap',
        'sort-output', 'sort-by-file', 'strip-comments'
    ]

    def initialize_options(self):
        self.charset = 'utf-8'
        self.keywords = ''
        self._keywords = DEFAULT_KEYWORDS.copy()
        self.no_default_keywords = False
        self.mapping_file = None
        self.no_location = False
        self.omit_header = False
        self.output_file = None
        self.input_dirs = None
        self.width = 76
        self.no_wrap = False
        self.sort_output = False
        self.sort_by_file = False
        self.msgid_bugs_address = None
        self.copyright_holder = None
        self.add_comments = None
        self._add_comments = []
        self.strip_comments = False

    def finalize_options(self):
        if self.no_default_keywords and not self.keywords:
            raise DistutilsOptionError('you must specify new keywords if you '
                                       'disable the default ones')
        if self.no_default_keywords:
            self._keywords = {}
        if self.keywords:
            self._keywords.update(parse_keywords(self.keywords.split()))

        if not self.output_file:
            raise DistutilsOptionError('no output file specified')
        if self.no_wrap and self.width:
            raise DistutilsOptionError("'--no-wrap' and '--width' are mutually "
                                       "exclusive")
        if self.no_wrap:
            self.width = None
        else:
            self.width = int(self.width)

        if self.sort_output and self.sort_by_file:
            raise DistutilsOptionError("'--sort-output' and '--sort-by-file' "
                                       "are mutually exclusive")

        if not self.input_dirs:
            self.input_dirs = dict.fromkeys([k.split('.',1)[0]
                for k in self.distribution.packages
            ]).keys()

        if self.add_comments:
            self._add_comments = self.add_comments.split(',')

    def run(self):
        mappings = self._get_mappings()
        outfile = open(self.output_file, 'w')
        try:
            catalog = Catalog(project=self.distribution.get_name(),
                              version=self.distribution.get_version(),
                              msgid_bugs_address=self.msgid_bugs_address,
                              copyright_holder=self.copyright_holder,
                              charset=self.charset)

            for dirname, (method_map, options_map) in mappings.items():
                def callback(filename, method, options):
                    if method == 'ignore':
                        return
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    optstr = ''
                    if options:
                        optstr = ' (%s)' % ', '.join(['%s="%s"' % (k, v) for
                                                      k, v in options.items()])
                    log.info('extracting messages from %s%s', filepath, optstr)

                extracted = extract_from_dir(dirname, method_map, options_map,
                                             keywords=self._keywords,
                                             comment_tags=self._add_comments,
                                             callback=callback,
                                             strip_comment_tags=
                                                self.strip_comments)
                for filename, lineno, message, comments in extracted:
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    catalog.add(message, None, [(filepath, lineno)],
                                auto_comments=comments)

            log.info('writing PO template file to %s' % self.output_file)
            write_po(outfile, catalog, width=self.width,
                     no_location=self.no_location,
                     omit_header=self.omit_header,
                     sort_output=self.sort_output,
                     sort_by_file=self.sort_by_file)
        finally:
            outfile.close()

    def _get_mappings(self):
        mappings = {}

        if self.mapping_file:
            fileobj = open(self.mapping_file, 'U')
            try:
                method_map, options_map = parse_mapping(fileobj)
                for dirname in self.input_dirs:
                    mappings[dirname] = method_map, options_map
            finally:
                fileobj.close()

        elif getattr(self.distribution, 'message_extractors', None):
            message_extractors = self.distribution.message_extractors
            for dirname, mapping in message_extractors.items():
                if isinstance(mapping, basestring):
                    method_map, options_map = parse_mapping(StringIO(mapping))
                else:
                    method_map, options_map = [], {}
                    for pattern, method, options in mapping:
                        method_map.append((pattern, method))
                        options_map[pattern] = options or {}
                mappings[dirname] = method_map, options_map

        else:
            for dirname in self.input_dirs:
                mappings[dirname] = DEFAULT_MAPPING, {}

        return mappings


def check_message_extractors(dist, name, value):
    """Validate the ``message_extractors`` keyword argument to ``setup()``.

    :param dist: the distutils/setuptools ``Distribution`` object
    :param name: the name of the keyword argument (should always be
                 "message_extractors")
    :param value: the value of the keyword argument
    :raise `DistutilsSetupError`: if the value is not valid
    :see: `Adding setup() arguments
           <http://peak.telecommunity.com/DevCenter/setuptools#adding-setup-arguments>`_
    """
    assert name == 'message_extractors'
    if not isinstance(value, dict):
        raise DistutilsSetupError('the value of the "message_extractors" '
                                  'parameter must be a dictionary')


class init_catalog(Command):
    """New catalog initialization command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import init_catalog

        setup(
            ...
            cmdclass = {'init_catalog': init_catalog}
        )

    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'create a new catalog based on a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to output directory'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale for the new localized catalog'),
    ]

    def initialize_options(self):
        self.output_dir = None
        self.output_file = None
        self.input_file = None
        self.locale = None
        self.domain = 'messages'

    def finalize_options(self):
        if not self.input_file:
            raise DistutilsOptionError('you must specify the input file')

        if not self.locale:
            raise DistutilsOptionError('you must provide a locale for the '
                                       'new catalog')
        try:
            self._locale = Locale.parse(self.locale)
        except UnknownLocaleError, e:
            raise DistutilsOptionError(e)

        if not self.output_file and not self.output_dir:
            raise DistutilsOptionError('you must specify the output directory')
        if not self.output_file:
            self.output_file = os.path.join(self.output_dir, self.locale,
                                            'LC_MESSAGES', self.domain + '.po')

        if not os.path.exists(os.path.dirname(self.output_file)):
            os.makedirs(os.path.dirname(self.output_file))

    def run(self):
        log.info('creating catalog %r based on %r', self.output_file,
                 self.input_file)

        infile = open(self.input_file, 'r')
        try:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correcly calculate plurals
            catalog = read_po(infile, locale=self.locale)
        finally:
            infile.close()

        catalog.locale = self._locale
        catalog.fuzzy = False

        outfile = open(self.output_file, 'w')
        try:
            write_po(outfile, catalog)
        finally:
            outfile.close()


class update_catalog(Command):
    """Catalog merging command for use in ``setup.py`` scripts.

    If correctly installed, this command is available to Setuptools-using
    setup scripts automatically. For projects using plain old ``distutils``,
    the command needs to be registered explicitly in ``setup.py``::

        from babel.messages.frontend import update_catalog

        setup(
            ...
            cmdclass = {'update_catalog': update_catalog}
        )

    :since: version 0.9
    :see: `Integrating new distutils commands <http://docs.python.org/dist/node32.html>`_
    :see: `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
    """

    description = 'update message catalogs from a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to base directory containing the catalogs'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('ignore-obsolete=', None,
         'whether to omit obsolete messages from the output'),
        ('no-fuzzy-matching', 'N',
         'do not use fuzzy matching'),
        ('previous', None,
         'keep previous msgids of translated messages')
    ]
    boolean_options = ['ignore_obsolete', 'no_fuzzy_matching', 'previous']

    def initialize_options(self):
        self.domain = 'messages'
        self.input_file = None
        self.output_dir = None
        self.output_file = None
        self.locale = None
        self.ignore_obsolete = False
        self.no_fuzzy_matching = False
        self.previous = False

    def finalize_options(self):
        if not self.input_file:
            raise DistutilsOptionError('you must specify the input file')
        if not self.output_file and not self.output_dir:
            raise DistutilsOptionError('you must specify the output file or '
                                       'directory')
        if self.output_file and not self.locale:
            raise DistutilsOptionError('you must specify the locale')
        if self.no_fuzzy_matching and self.previous:
            self.previous = False

    def run(self):
        po_files = []
        if not self.output_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.output_dir, self.locale,
                                              'LC_MESSAGES',
                                              self.domain + '.po')))
            else:
                for locale in os.listdir(self.output_dir):
                    po_file = os.path.join(self.output_dir, locale,
                                           'LC_MESSAGES',
                                           self.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((self.locale, self.output_file))

        domain = self.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(self.input_file))[0]

        infile = open(self.input_file, 'U')
        try:
            template = read_po(infile)
        finally:
            infile.close()

        if not po_files:
            raise DistutilsOptionError('no message catalogs found')

        for locale, filename in po_files:
            log.info('updating catalog %r based on %r', filename,
                     self.input_file)
            infile = open(filename, 'U')
            try:
                catalog = read_po(infile, locale=locale, domain=domain)
            finally:
                infile.close()

            catalog.update(template, self.no_fuzzy_matching)

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            tmpfile = open(tmpname, 'w')
            try:
                try:
                    write_po(tmpfile, catalog,
                             ignore_obsolete=self.ignore_obsolete,
                             include_previous=self.previous)
                finally:
                    tmpfile.close()
            except:
                os.remove(tmpname)
                raise

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)


class CommandLineInterface(object):
    """Command-line interface.

    This class provides a simple command-line interface to the message
    extraction and PO file generation functionality.
    """

    usage = '%%prog %s [options] %s'
    version = '%%prog %s' % VERSION
    commands = {
        'compile': 'compile message catalogs to MO files',
        'extract': 'extract messages from source files and generate a POT file',
        'init':    'create new message catalogs from a POT file',
        'update':  'update existing message catalogs from a POT file'
    }

    def run(self, argv=sys.argv):
        """Main entry point of the command-line interface.

        :param argv: list of arguments passed on the command-line
        """
        self.parser = OptionParser(usage=self.usage % ('command', '[args]'),
                                   version=self.version)
        self.parser.disable_interspersed_args()
        self.parser.print_help = self._help
        self.parser.add_option('--list-locales', dest='list_locales',
                               action='store_true',
                               help="print all known locales and exit")
        self.parser.add_option('-v', '--verbose', action='store_const',
                               dest='loglevel', const=logging.DEBUG,
                               help='print as much as possible')
        self.parser.add_option('-q', '--quiet', action='store_const',
                               dest='loglevel', const=logging.ERROR,
                               help='print as little as possible')
        self.parser.set_defaults(list_locales=False, loglevel=logging.INFO)

        options, args = self.parser.parse_args(argv[1:])

        # Configure logging
        self.log = logging.getLogger('babel')
        self.log.setLevel(options.loglevel)
        handler = logging.StreamHandler()
        handler.setLevel(options.loglevel)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        if options.list_locales:
            identifiers = localedata.list()
            longest = max([len(identifier) for identifier in identifiers])
            format = u'%%-%ds %%s' % (longest + 1)
            for identifier in localedata.list():
                locale = Locale.parse(identifier)
                output = format % (identifier, locale.english_name)
                print output.encode(sys.stdout.encoding or
                                    getpreferredencoding() or
                                    'ascii', 'replace')
            return 0

        if not args:
            self.parser.error('incorrect number of arguments')

        cmdname = args[0]
        if cmdname not in self.commands:
            self.parser.error('unknown command "%s"' % cmdname)

        return getattr(self, cmdname)(args[1:])

    def _help(self):
        print self.parser.format_help()
        print "commands:"
        longest = max([len(command) for command in self.commands])
        format = "  %%-%ds %%s" % max(8, longest + 1)
        commands = self.commands.items()
        commands.sort()
        for name, description in commands:
            print format % (name, description)

    def compile(self, argv):
        """Subcommand for compiling a message catalog to a MO file.

        :param argv: the command arguments
        :since: version 0.9
        """
        parser = OptionParser(usage=self.usage % ('compile', ''),
                              description=self.commands['compile'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of MO and PO files (default '%default')")
        parser.add_option('--directory', '-d', dest='directory',
                          metavar='DIR', help='base directory of catalog files')
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale of the catalog')
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.mo')")
        parser.add_option('--use-fuzzy', '-f', dest='use_fuzzy',
                          action='store_true',
                          help='also include fuzzy translations (default '
                               '%default)')
        parser.add_option('--statistics', dest='statistics',
                          action='store_true',
                          help='print statistics about translations')

        parser.set_defaults(domain='messages', use_fuzzy=False,
                            compile_all=False, statistics=False)
        options, args = parser.parse_args(argv)

        po_files = []
        mo_files = []
        if not options.input_file:
            if not options.directory:
                parser.error('you must specify either the input file or the '
                             'base directory')
            if options.locale:
                po_files.append((options.locale,
                                 os.path.join(options.directory,
                                              options.locale, 'LC_MESSAGES',
                                              options.domain + '.po')))
                mo_files.append(os.path.join(options.directory, options.locale,
                                             'LC_MESSAGES',
                                             options.domain + '.mo'))
            else:
                for locale in os.listdir(options.directory):
                    po_file = os.path.join(options.directory, locale,
                                           'LC_MESSAGES', options.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(options.directory, locale,
                                                     'LC_MESSAGES',
                                                     options.domain + '.mo'))
        else:
            po_files.append((options.locale, options.input_file))
            if options.output_file:
                mo_files.append(options.output_file)
            else:
                if not options.directory:
                    parser.error('you must specify either the input file or '
                                 'the base directory')
                mo_files.append(os.path.join(options.directory, options.locale,
                                             'LC_MESSAGES',
                                             options.domain + '.mo'))
        if not po_files:
            parser.error('no message catalogs found')

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            infile = open(po_file, 'r')
            try:
                catalog = read_po(infile, locale)
            finally:
                infile.close()

            if options.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated +=1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                self.log.info("%d of %d messages (%d%%) translated in %r",
                              translated, len(catalog), percentage, po_file)

            if catalog.fuzzy and not options.use_fuzzy:
                self.log.warn('catalog %r is marked as fuzzy, skipping',
                              po_file)
                continue

            for message, errors in catalog.check():
                for error in errors:
                    self.log.error('error: %s:%d: %s', po_file, message.lineno,
                                   error)

            self.log.info('compiling catalog %r to %r', po_file, mo_file)

            outfile = open(mo_file, 'wb')
            try:
                write_mo(outfile, catalog, use_fuzzy=options.use_fuzzy)
            finally:
                outfile.close()

    def extract(self, argv):
        """Subcommand for extracting messages from source files and generating
        a POT file.

        :param argv: the command arguments
        """
        parser = OptionParser(usage=self.usage % ('extract', 'dir1 <dir2> ...'),
                              description=self.commands['extract'])
        parser.add_option('--charset', dest='charset',
                          help='charset to use in the output (default '
                               '"%default")')
        parser.add_option('-k', '--keyword', dest='keywords', action='append',
                          help='keywords to look for in addition to the '
                               'defaults. You can specify multiple -k flags on '
                               'the command line.')
        parser.add_option('--no-default-keywords', dest='no_default_keywords',
                          action='store_true',
                          help="do not include the default keywords")
        parser.add_option('--mapping', '-F', dest='mapping_file',
                          help='path to the extraction mapping file')
        parser.add_option('--no-location', dest='no_location',
                          action='store_true',
                          help='do not include location comments with filename '
                               'and line number')
        parser.add_option('--omit-header', dest='omit_header',
                          action='store_true',
                          help='do not include msgid "" entry in header')
        parser.add_option('-o', '--output', dest='output',
                          help='path to the output POT file')
        parser.add_option('-w', '--width', dest='width', type='int',
                          help="set output line width (default %default)")
        parser.add_option('--no-wrap', dest='no_wrap', action = 'store_true',
                          help='do not break long message lines, longer than '
                               'the output line width, into several lines')
        parser.add_option('--sort-output', dest='sort_output',
                          action='store_true',
                          help='generate sorted output (default False)')
        parser.add_option('--sort-by-file', dest='sort_by_file',
                          action='store_true',
                          help='sort output by file location (default False)')
        parser.add_option('--msgid-bugs-address', dest='msgid_bugs_address',
                          metavar='EMAIL@ADDRESS',
                          help='set report address for msgid')
        parser.add_option('--copyright-holder', dest='copyright_holder',
                          help='set copyright holder in output')
        parser.add_option('--add-comments', '-c', dest='comment_tags',
                          metavar='TAG', action='append',
                          help='place comment block with TAG (or those '
                               'preceding keyword lines) in output file. One '
                               'TAG per argument call')
        parser.add_option('--strip-comment-tags', '-s',
                          dest='strip_comment_tags', action='store_true',
                          help='Strip the comment tags from the comments.')

        parser.set_defaults(charset='utf-8', keywords=[],
                            no_default_keywords=False, no_location=False,
                            omit_header = False, width=76, no_wrap=False,
                            sort_output=False, sort_by_file=False,
                            comment_tags=[], strip_comment_tags=False)
        options, args = parser.parse_args(argv)
        if not args:
            parser.error('incorrect number of arguments')

        if options.output not in (None, '-'):
            outfile = open(options.output, 'w')
        else:
            outfile = sys.stdout

        keywords = DEFAULT_KEYWORDS.copy()
        if options.no_default_keywords:
            if not options.keywords:
                parser.error('you must specify new keywords if you disable the '
                             'default ones')
            keywords = {}
        if options.keywords:
            keywords.update(parse_keywords(options.keywords))

        if options.mapping_file:
            fileobj = open(options.mapping_file, 'U')
            try:
                method_map, options_map = parse_mapping(fileobj)
            finally:
                fileobj.close()
        else:
            method_map = DEFAULT_MAPPING
            options_map = {}

        if options.width and options.no_wrap:
            parser.error("'--no-wrap' and '--width' are mutually exclusive.")
        elif not options.width and not options.no_wrap:
            options.width = 76
        elif not options.width and options.no_wrap:
            options.width = 0

        if options.sort_output and options.sort_by_file:
            parser.error("'--sort-output' and '--sort-by-file' are mutually "
                         "exclusive")

        try:
            catalog = Catalog(msgid_bugs_address=options.msgid_bugs_address,
                              copyright_holder=options.copyright_holder,
                              charset=options.charset)

            for dirname in args:
                if not os.path.isdir(dirname):
                    parser.error('%r is not a directory' % dirname)

                def callback(filename, method, options):
                    if method == 'ignore':
                        return
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    optstr = ''
                    if options:
                        optstr = ' (%s)' % ', '.join(['%s="%s"' % (k, v) for
                                                      k, v in options.items()])
                    self.log.info('extracting messages from %s%s', filepath,
                                  optstr)

                extracted = extract_from_dir(dirname, method_map, options_map,
                                             keywords, options.comment_tags,
                                             callback=callback,
                                             strip_comment_tags=
                                                options.strip_comment_tags)
                for filename, lineno, message, comments in extracted:
                    filepath = os.path.normpath(os.path.join(dirname, filename))
                    catalog.add(message, None, [(filepath, lineno)],
                                auto_comments=comments)

            if options.output not in (None, '-'):
                self.log.info('writing PO template file to %s' % options.output)
            write_po(outfile, catalog, width=options.width,
                     no_location=options.no_location,
                     omit_header=options.omit_header,
                     sort_output=options.sort_output,
                     sort_by_file=options.sort_by_file)
        finally:
            if options.output:
                outfile.close()

    def init(self, argv):
        """Subcommand for creating new message catalogs from a template.

        :param argv: the command arguments
        """
        parser = OptionParser(usage=self.usage % ('init', ''),
                              description=self.commands['init'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of PO file (default '%default')")
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-dir', '-d', dest='output_dir',
                          metavar='DIR', help='path to output directory')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.po')")
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale for the new localized catalog')

        parser.set_defaults(domain='messages')
        options, args = parser.parse_args(argv)

        if not options.locale:
            parser.error('you must provide a locale for the new catalog')
        try:
            locale = Locale.parse(options.locale)
        except UnknownLocaleError, e:
            parser.error(e)

        if not options.input_file:
            parser.error('you must specify the input file')

        if not options.output_file and not options.output_dir:
            parser.error('you must specify the output file or directory')

        if not options.output_file:
            options.output_file = os.path.join(options.output_dir,
                                               options.locale, 'LC_MESSAGES',
                                               options.domain + '.po')
        if not os.path.exists(os.path.dirname(options.output_file)):
            os.makedirs(os.path.dirname(options.output_file))

        infile = open(options.input_file, 'r')
        try:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correcly calculate plurals
            catalog = read_po(infile, locale=options.locale)
        finally:
            infile.close()

        catalog.locale = locale
        catalog.revision_date = datetime.now(LOCALTZ)

        self.log.info('creating catalog %r based on %r', options.output_file,
                      options.input_file)

        outfile = open(options.output_file, 'w')
        try:
            write_po(outfile, catalog)
        finally:
            outfile.close()

    def update(self, argv):
        """Subcommand for updating existing message catalogs from a template.

        :param argv: the command arguments
        :since: version 0.9
        """
        parser = OptionParser(usage=self.usage % ('update', ''),
                              description=self.commands['update'])
        parser.add_option('--domain', '-D', dest='domain',
                          help="domain of PO file (default '%default')")
        parser.add_option('--input-file', '-i', dest='input_file',
                          metavar='FILE', help='name of the input file')
        parser.add_option('--output-dir', '-d', dest='output_dir',
                          metavar='DIR', help='path to output directory')
        parser.add_option('--output-file', '-o', dest='output_file',
                          metavar='FILE',
                          help="name of the output file (default "
                               "'<output_dir>/<locale>/LC_MESSAGES/"
                               "<domain>.po')")
        parser.add_option('--locale', '-l', dest='locale', metavar='LOCALE',
                          help='locale of the translations catalog')
        parser.add_option('--ignore-obsolete', dest='ignore_obsolete',
                          action='store_true',
                          help='do not include obsolete messages in the output '
                               '(default %default)'),
        parser.add_option('--no-fuzzy-matching', '-N', dest='no_fuzzy_matching',
                          action='store_true',
                          help='do not use fuzzy matching (default %default)'),
        parser.add_option('--previous', dest='previous', action='store_true',
                          help='keep previous msgids of translated messages '
                               '(default %default)'),

        parser.set_defaults(domain='messages', ignore_obsolete=False,
                            no_fuzzy_matching=False, previous=False)
        options, args = parser.parse_args(argv)

        if not options.input_file:
            parser.error('you must specify the input file')
        if not options.output_file and not options.output_dir:
            parser.error('you must specify the output file or directory')
        if options.output_file and not options.locale:
            parser.error('you must specify the loicale')
        if options.no_fuzzy_matching and options.previous:
            options.previous = False

        po_files = []
        if not options.output_file:
            if options.locale:
                po_files.append((options.locale,
                                 os.path.join(options.output_dir,
                                              options.locale, 'LC_MESSAGES',
                                              options.domain + '.po')))
            else:
                for locale in os.listdir(options.output_dir):
                    po_file = os.path.join(options.output_dir, locale,
                                           'LC_MESSAGES',
                                           options.domain + '.po')
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((options.locale, options.output_file))

        domain = options.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(options.input_file))[0]

        infile = open(options.input_file, 'U')
        try:
            template = read_po(infile)
        finally:
            infile.close()

        if not po_files:
            parser.error('no message catalogs found')

        for locale, filename in po_files:
            self.log.info('updating catalog %r based on %r', filename,
                          options.input_file)
            infile = open(filename, 'U')
            try:
                catalog = read_po(infile, locale=locale, domain=domain)
            finally:
                infile.close()

            catalog.update(template, options.no_fuzzy_matching)

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            tmpfile = open(tmpname, 'w')
            try:
                try:
                    write_po(tmpfile, catalog,
                             ignore_obsolete=options.ignore_obsolete,
                             include_previous=options.previous)
                finally:
                    tmpfile.close()
            except:
                os.remove(tmpname)
                raise

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)


def main():
    return CommandLineInterface().run(sys.argv)

def parse_mapping(fileobj, filename=None):
    """Parse an extraction method mapping from a file-like object.

    >>> buf = StringIO('''
    ... [extractors]
    ... custom = mypackage.module:myfunc
    ... 
    ... # Python source files
    ... [python: **.py]
    ...
    ... # Genshi templates
    ... [genshi: **/templates/**.html]
    ... include_attrs =
    ... [genshi: **/templates/**.txt]
    ... template_class = genshi.template:TextTemplate
    ... encoding = latin-1
    ... 
    ... # Some custom extractor
    ... [custom: **/custom/*.*]
    ... ''')

    >>> method_map, options_map = parse_mapping(buf)
    >>> len(method_map)
    4

    >>> method_map[0]
    ('**.py', 'python')
    >>> options_map['**.py']
    {}
    >>> method_map[1]
    ('**/templates/**.html', 'genshi')
    >>> options_map['**/templates/**.html']['include_attrs']
    ''
    >>> method_map[2]
    ('**/templates/**.txt', 'genshi')
    >>> options_map['**/templates/**.txt']['template_class']
    'genshi.template:TextTemplate'
    >>> options_map['**/templates/**.txt']['encoding']
    'latin-1'

    >>> method_map[3]
    ('**/custom/*.*', 'mypackage.module:myfunc')
    >>> options_map['**/custom/*.*']
    {}

    :param fileobj: a readable file-like object containing the configuration
                    text to parse
    :return: a `(method_map, options_map)` tuple
    :rtype: `tuple`
    :see: `extract_from_directory`
    """
    extractors = {}
    method_map = []
    options_map = {}

    parser = RawConfigParser()
    parser._sections = odict(parser._sections) # We need ordered sections
    parser.readfp(fileobj, filename)
    for section in parser.sections():
        if section == 'extractors':
            extractors = dict(parser.items(section))
        else:
            method, pattern = [part.strip() for part in section.split(':', 1)]
            method_map.append((pattern, method))
            options_map[pattern] = dict(parser.items(section))

    if extractors:
        for idx, (pattern, method) in enumerate(method_map):
            if method in extractors:
                method = extractors[method]
            method_map[idx] = (pattern, method)

    return (method_map, options_map)

def parse_keywords(strings=[]):
    """Parse keywords specifications from the given list of strings.

    >>> kw = parse_keywords(['_', 'dgettext:2', 'dngettext:2,3'])
    >>> for keyword, indices in sorted(kw.items()):
    ...     print (keyword, indices)
    ('_', None)
    ('dgettext', (2,))
    ('dngettext', (2, 3))
    """
    keywords = {}
    for string in strings:
        if ':' in string:
            funcname, indices = string.split(':')
        else:
            funcname, indices = string, None
        if funcname not in keywords:
            if indices:
                indices = tuple([(int(x)) for x in indices.split(',')])
            keywords[funcname] = indices
    return keywords


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = jslexer
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""A simple JavaScript 1.5 lexer which is used for the JavaScript
extractor.
"""

import re
from operator import itemgetter


operators = [
    '+', '-', '*', '%', '!=', '==', '<', '>', '<=', '>=', '=',
    '+=', '-=', '*=', '%=', '<<', '>>', '>>>', '<<=', '>>=',
    '>>>=', '&', '&=', '|', '|=', '&&', '||', '^', '^=', '(', ')',
    '[', ']', '{', '}', '!', '--', '++', '~', ',', ';', '.', ':'
]
operators.sort(lambda a, b: cmp(-len(a), -len(b)))

escapes = {'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}

rules = [
    (None, re.compile(r'\s+(?u)')),
    (None, re.compile(r'<!--.*')),
    ('linecomment', re.compile(r'//.*')),
    ('multilinecomment', re.compile(r'/\*.*?\*/(?us)')),
    ('name', re.compile(r'(\$+\w*|[^\W\d]\w*)(?u)')),
    ('number', re.compile(r'''(?x)(
        (?:0|[1-9]\d*)
        (\.\d+)?
        ([eE][-+]?\d+)? |
        (0x[a-fA-F0-9]+)
    )''')),
    ('operator', re.compile(r'(%s)' % '|'.join(map(re.escape, operators)))),
    ('string', re.compile(r'''(?xs)(
        '(?:[^'\\]*(?:\\.[^'\\]*)*)'  |
        "(?:[^"\\]*(?:\\.[^"\\]*)*)"
    )'''))
]

division_re = re.compile(r'/=?')
regex_re = re.compile(r'/(?:[^/\\]*(?:\\.[^/\\]*)*)/[a-zA-Z]*(?s)')
line_re = re.compile(r'(\r\n|\n|\r)')
line_join_re = re.compile(r'\\' + line_re.pattern)
uni_escape_re = re.compile(r'[a-fA-F0-9]{1,4}')


class Token(tuple):
    """Represents a token as returned by `tokenize`."""
    __slots__ = ()

    def __new__(cls, type, value, lineno):
        return tuple.__new__(cls, (type, value, lineno))

    type = property(itemgetter(0))
    value = property(itemgetter(1))
    lineno = property(itemgetter(2))


def indicates_division(token):
    """A helper function that helps the tokenizer to decide if the current
    token may be followed by a division operator.
    """
    if token.type == 'operator':
        return token.value in (')', ']', '}', '++', '--')
    return token.type in ('name', 'number', 'string', 'regexp')


def unquote_string(string):
    """Unquote a string with JavaScript rules.  The string has to start with
    string delimiters (``'`` or ``"``.)

    :return: a string
    """
    assert string and string[0] == string[-1] and string[0] in '"\'', \
        'string provided is not properly delimited'
    string = line_join_re.sub('\\1', string[1:-1])
    result = []
    add = result.append
    pos = 0

    while 1:
        # scan for the next escape
        escape_pos = string.find('\\', pos)
        if escape_pos < 0:
            break
        add(string[pos:escape_pos])

        # check which character is escaped
        next_char = string[escape_pos + 1]
        if next_char in escapes:
            add(escapes[next_char])

        # unicode escapes.  trie to consume up to four characters of
        # hexadecimal characters and try to interpret them as unicode
        # character point.  If there is no such character point, put
        # all the consumed characters into the string.
        elif next_char in 'uU':
            escaped = uni_escape_re.match(string, escape_pos + 2)
            if escaped is not None:
                escaped_value = escaped.group()
                if len(escaped_value) == 4:
                    try:
                        add(unichr(int(escaped_value, 16)))
                    except ValueError:
                        pass
                    else:
                        pos = escape_pos + 6
                        continue
                add(next_char + escaped_value)
                pos = escaped.end()
                continue
            else:
                add(next_char)

        # bogus escape.  Just remove the backslash.
        else:
            add(next_char)
        pos = escape_pos + 2

    if pos < len(string):
        add(string[pos:])

    return u''.join(result)


def tokenize(source):
    """Tokenize a JavaScript source.

    :return: generator of `Token`\s
    """
    may_divide = False
    pos = 0
    lineno = 1
    end = len(source)

    while pos < end:
        # handle regular rules first
        for token_type, rule in rules:
            match = rule.match(source, pos)
            if match is not None:
                break
        # if we don't have a match we don't give up yet, but check for
        # division operators or regular expression literals, based on
        # the status of `may_divide` which is determined by the last
        # processed non-whitespace token using `indicates_division`.
        else:
            if may_divide:
                match = division_re.match(source, pos)
                token_type = 'operator'
            else:
                match = regex_re.match(source, pos)
                token_type = 'regexp'
            if match is None:
                # woops. invalid syntax. jump one char ahead and try again.
                pos += 1
                continue

        token_value = match.group()
        if token_type is not None:
            token = Token(token_type, token_value, lineno)
            may_divide = indicates_division(token)
            yield token
        lineno += len(line_re.findall(token_value))
        pos = match.end()

########NEW FILE########
__FILENAME__ = mofile
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Writing of files in the ``gettext`` MO (machine object) format.

:since: version 0.9
:see: `The Format of MO Files
       <http://www.gnu.org/software/gettext/manual/gettext.html#MO-Files>`_
"""

import array
import struct

__all__ = ['write_mo']
__docformat__ = 'restructuredtext en'

def write_mo(fileobj, catalog, use_fuzzy=False):
    """Write a catalog to the specified file-like object using the GNU MO file
    format.
    
    >>> from babel.messages import Catalog
    >>> from gettext import GNUTranslations
    >>> from StringIO import StringIO
    
    >>> catalog = Catalog(locale='en_US')
    >>> catalog.add('foo', 'Voh')
    >>> catalog.add((u'bar', u'baz'), (u'Bahr', u'Batz'))
    >>> catalog.add('fuz', 'Futz', flags=['fuzzy'])
    >>> catalog.add('Fizz', '')
    >>> catalog.add(('Fuzz', 'Fuzzes'), ('', ''))
    >>> buf = StringIO()
    
    >>> write_mo(buf, catalog)
    >>> buf.seek(0)
    >>> translations = GNUTranslations(fp=buf)
    >>> translations.ugettext('foo')
    u'Voh'
    >>> translations.ungettext('bar', 'baz', 1)
    u'Bahr'
    >>> translations.ungettext('bar', 'baz', 2)
    u'Batz'
    >>> translations.ugettext('fuz')
    u'fuz'
    >>> translations.ugettext('Fizz')
    u'Fizz'
    >>> translations.ugettext('Fuzz')
    u'Fuzz'
    >>> translations.ugettext('Fuzzes')
    u'Fuzzes'
    
    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param use_fuzzy: whether translations marked as "fuzzy" should be included
                      in the output
    """
    messages = list(catalog)
    if not use_fuzzy:
        messages[1:] = [m for m in messages[1:] if not m.fuzzy]
    messages.sort()

    ids = strs = ''
    offsets = []

    for message in messages:
        # For each string, we need size and file offset.  Each string is NUL
        # terminated; the NUL does not count into the size.
        if message.pluralizable:
            msgid = '\x00'.join([
                msgid.encode(catalog.charset) for msgid in message.id
            ])
            msgstrs = []
            for idx, string in enumerate(message.string):
                if not string:
                    msgstrs.append(message.id[min(int(idx), 1)])
                else:
                    msgstrs.append(string)
            msgstr = '\x00'.join([
                msgstr.encode(catalog.charset) for msgstr in msgstrs
            ])
        else:
            msgid = message.id.encode(catalog.charset)
            if not message.string:
                msgstr = message.id.encode(catalog.charset)
            else:
                msgstr = message.string.encode(catalog.charset)
        offsets.append((len(ids), len(msgid), len(strs), len(msgstr)))
        ids += msgid + '\x00'
        strs += msgstr + '\x00'

    # The header is 7 32-bit unsigned integers.  We don't use hash tables, so
    # the keys start right after the index tables.
    keystart = 7 * 4 + 16 * len(messages)
    valuestart = keystart + len(ids)

    # The string table first has the list of keys, then the list of values.
    # Each entry has first the size of the string, then the file offset.
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    offsets = koffsets + voffsets

    fileobj.write(struct.pack('Iiiiiii',
        0x950412deL,                # magic
        0,                          # version
        len(messages),              # number of entries
        7 * 4,                      # start of key index
        7 * 4 + len(messages) * 8,  # start of value index
        0, 0                        # size and offset of hash table
    ) + array.array("i", offsets).tostring() + ids + strs)

########NEW FILE########
__FILENAME__ = plurals
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Plural form definitions."""


from operator import itemgetter
from babel.core import default_locale, Locale


LC_CTYPE = default_locale('LC_CTYPE')


PLURALS = {
    # Afar
    # 'aa': (),
    # Abkhazian
    # 'ab': (),
    # Avestan
    # 'ae': (),
    # Afrikaans - From Pootle's PO's
    'af': (2, '(n != 1)'),
    # Akan
    # 'ak': (),
    # Amharic
    # 'am': (),
    # Aragonese
    # 'an': (),
    # Arabic - From Pootle's PO's
    'ar': (6, '(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n>=3 && n<=10 ? 3 : n>=11 && n<=99 ? 4 : 5)'),
    # Assamese
    # 'as': (),
    # Avaric
    # 'av': (),
    # Aymara
    # 'ay': (),
    # Azerbaijani
    # 'az': (),
    # Bashkir
    # 'ba': (),
    # Belarusian
    # 'be': (),
    # Bulgarian - From Pootle's PO's
    'bg': (2, '(n != 1)'),
    # Bihari
    # 'bh': (),
    # Bislama
    # 'bi': (),
    # Bambara
    # 'bm': (),
    # Bengali - From Pootle's PO's
    'bn': (2, '(n != 1)'),
    # Tibetan - as discussed in private with Andrew West
    'bo': (1, '0'),
    # Breton
    # 'br': (),
    # Bosnian
    # 'bs': (),
    # Catalan - From Pootle's PO's
    'ca': (2, '(n != 1)'),
    # Chechen
    # 'ce': (),
    # Chamorro
    # 'ch': (),
    # Corsican
    # 'co': (),
    # Cree
    # 'cr': (),
    # Czech
    'cs': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Church Slavic
    # 'cu': (),
    # Chuvash
    'cv': (1, '0'),
    # Welsh
    'cy': (5, '(n==1 ? 1 : n==2 ? 2 : n==3 ? 3 : n==6 ? 4 : 0)'),
    # Danish
    'da': (2, '(n != 1)'),
    # German
    'de': (2, '(n != 1)'),
    # Divehi
    # 'dv': (),
    # Dzongkha
    'dz': (1, '0'),
    # Greek
    'el': (2, '(n != 1)'),
    # English
    'en': (2, '(n != 1)'),
    # Esperanto
    'eo': (2, '(n != 1)'),
    # Spanish
    'es': (2, '(n != 1)'),
    # Estonian
    'et': (2, '(n != 1)'),
    # Basque - From Pootle's PO's
    'eu': (2, '(n != 1)'),
    # Persian - From Pootle's PO's
    'fa': (1, '0'),
    # Finnish
    'fi': (2, '(n != 1)'),
    # French
    'fr': (2, '(n > 1)'),
    # Friulian - From Pootle's PO's
    'fur': (2, '(n > 1)'),
    # Irish
    'ga': (3, '(n==1 ? 0 : n==2 ? 1 : 2)'),
    # Galician - From Pootle's PO's
    'gl': (2, '(n != 1)'),
    # Hausa - From Pootle's PO's
    'ha': (2, '(n != 1)'),
    # Hebrew
    'he': (2, '(n != 1)'),
    # Hindi - From Pootle's PO's
    'hi': (2, '(n != 1)'),
    # Croatian
    'hr': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Hungarian
    'hu': (1, '0'),
    # Armenian - From Pootle's PO's
    'hy': (1, '0'),
    # Icelandic - From Pootle's PO's
    'is': (2, '(n != 1)'),
    # Italian
    'it': (2, '(n != 1)'),
    # Japanese
    'ja': (1, '0'),
    # Georgian - From Pootle's PO's
    'ka': (1, '0'),
    # Kongo - From Pootle's PO's
    'kg': (2, '(n != 1)'),
    # Khmer - From Pootle's PO's
    'km': (1, '0'),
    # Korean
    'ko': (1, '0'),
    # Kurdish - From Pootle's PO's
    'ku': (2, '(n != 1)'),
    # Lao - Another member of the Tai language family, like Thai.
    'lo': (1, '0'),
    # Lithuanian
    'lt': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Latvian
    'lv': (3, '(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2)'),
    # Maltese - From Pootle's PO's
    'mt': (4, '(n==1 ? 0 : n==0 || ( n%100>1 && n%100<11) ? 1 : (n%100>10 && n%100<20 ) ? 2 : 3)'),
    # Norwegian Bokmål
    'nb': (2, '(n != 1)'),
    # Dutch
    'nl': (2, '(n != 1)'),
    # Norwegian Nynorsk
    'nn': (2, '(n != 1)'),
    # Norwegian
    'no': (2, '(n != 1)'),
    # Punjabi - From Pootle's PO's
    'pa': (2, '(n != 1)'),
    # Polish
    'pl': (3, '(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Portuguese
    'pt': (2, '(n != 1)'),
    # Brazilian
    'pt_BR': (2, '(n > 1)'),
    # Romanian - From Pootle's PO's
    'ro': (3, '(n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2)'),
    # Russian
    'ru': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Slovak
    'sk': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Slovenian
    'sl': (4, '(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3)'),
    # Serbian - From Pootle's PO's
    'sr': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10< =4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Southern Sotho - From Pootle's PO's
    'st': (2, '(n != 1)'),
    # Swedish
    'sv': (2, '(n != 1)'),
    # Thai
    'th': (1, '0'),
    # Turkish
    'tr': (1, '0'),
    # Ukrainian
    'uk': (3, '(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'),
    # Venda - From Pootle's PO's
    've': (2, '(n != 1)'),
    # Vietnamese - From Pootle's PO's
    'vi': (1, '0'),
    # Xhosa - From Pootle's PO's
    'xh': (2, '(n != 1)'),
    # Chinese - From Pootle's PO's
    'zh_CN': (1, '0'),
    'zh_HK': (1, '0'),
    'zh_TW': (1, '0'),
}


DEFAULT_PLURAL = (2, '(n != 1)')


class _PluralTuple(tuple):
    """A tuple with plural information."""

    __slots__ = ()
    num_plurals = property(itemgetter(0), doc="""
    The number of plurals used by the locale.""")
    plural_expr = property(itemgetter(1), doc="""
    The plural expression used by the locale.""")
    plural_forms = property(lambda x: 'npurals=%s; plural=%s' % x, doc="""
    The plural expression used by the catalog or locale.""")

    def __str__(self):
        return self.plural_forms


def get_plural(locale=LC_CTYPE):
    """A tuple with the information catalogs need to perform proper
    pluralization.  The first item of the tuple is the number of plural
    forms, the second the plural expression.

    >>> get_plural(locale='en')
    (2, '(n != 1)')
    >>> get_plural(locale='ga')
    (3, '(n==1 ? 0 : n==2 ? 1 : 2)')

    The object returned is a special tuple with additional members:

    >>> tup = get_plural("ja")
    >>> tup.num_plurals
    1
    >>> tup.plural_expr
    '0'
    >>> tup.plural_forms
    'npurals=1; plural=0'

    Converting the tuple into a string prints the plural forms for a
    gettext catalog:

    >>> str(tup)
    'npurals=1; plural=0'
    """
    locale = Locale.parse(locale)
    try:
        tup = PLURALS[str(locale)]
    except KeyError:
        try:
            tup = PLURALS[locale.language]
        except KeyError:
            tup = DEFAULT_PLURAL
    return _PluralTuple(tup)

########NEW FILE########
__FILENAME__ = pofile
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Reading and writing of files in the ``gettext`` PO (portable object)
format.

:see: `The Format of PO Files
       <http://www.gnu.org/software/gettext/manual/gettext.html#PO-Files>`_
"""

from datetime import date, datetime
import os
import re
try:
    set
except NameError:
    from sets import Set as set

from babel import __version__ as VERSION
from babel.messages.catalog import Catalog, Message
from babel.util import wraptext, LOCALTZ

__all__ = ['read_po', 'write_po']
__docformat__ = 'restructuredtext en'

def unescape(string):
    r"""Reverse `escape` the given string.

    >>> print unescape('"Say:\\n  \\"hello, world!\\"\\n"')
    Say:
      "hello, world!"
    <BLANKLINE>

    :param string: the string to unescape
    :return: the unescaped string
    :rtype: `str` or `unicode`
    """
    return string[1:-1].replace('\\\\', '\\') \
                       .replace('\\t', '\t') \
                       .replace('\\r', '\r') \
                       .replace('\\n', '\n') \
                       .replace('\\"', '\"')

def denormalize(string):
    r"""Reverse the normalization done by the `normalize` function.

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"hello, world!\"\n"''')
    Say:
      "hello, world!"
    <BLANKLINE>

    >>> print denormalize(r'''""
    ... "Say:\n"
    ... "  \"Lorem ipsum dolor sit "
    ... "amet, consectetur adipisicing"
    ... " elit, \"\n"''')
    Say:
      "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    <BLANKLINE>

    :param string: the string to denormalize
    :return: the denormalized string
    :rtype: `unicode` or `str`
    """
    if string.startswith('""'):
        lines = []
        for line in string.splitlines()[1:]:
            lines.append(unescape(line))
        return ''.join(lines)
    else:
        return unescape(string)

def read_po(fileobj, locale=None, domain=None, ignore_obsolete=False):
    """Read messages from a ``gettext`` PO (portable object) file from the given
    file-like object and return a `Catalog`.

    >>> from StringIO import StringIO
    >>> buf = StringIO('''
    ... #: main.py:1
    ... #, fuzzy, python-format
    ... msgid "foo %(name)s"
    ... msgstr ""
    ...
    ... # A user comment
    ... #. An auto comment
    ... #: main.py:3
    ... msgid "bar"
    ... msgid_plural "baz"
    ... msgstr[0] ""
    ... msgstr[1] ""
    ... ''')
    >>> catalog = read_po(buf)
    >>> catalog.revision_date = datetime(2007, 04, 01)

    >>> for message in catalog:
    ...     if message.id:
    ...         print (message.id, message.string)
    ...         print ' ', (message.locations, message.flags)
    ...         print ' ', (message.user_comments, message.auto_comments)
    (u'foo %(name)s', '')
      ([(u'main.py', 1)], set([u'fuzzy', u'python-format']))
      ([], [])
    ((u'bar', u'baz'), ('', ''))
      ([(u'main.py', 3)], set([]))
      ([u'A user comment'], [u'An auto comment'])

    :param fileobj: the file-like object to read the PO file from
    :param locale: the locale identifier or `Locale` object, or `None`
                   if the catalog is not bound to a locale (which basically
                   means it's a template)
    :param domain: the message domain
    :param ignore_obsolete: whether to ignore obsolete messages in the input
    :return: an iterator over ``(message, translation, location)`` tuples
    :rtype: ``iterator``
    """
    catalog = Catalog(locale=locale, domain=domain)

    counter = [0]
    offset = [0]
    messages = []
    translations = []
    locations = []
    flags = []
    user_comments = []
    auto_comments = []
    obsolete = [False]
    in_msgid = [False]
    in_msgstr = [False]

    def _add_message():
        translations.sort()
        if len(messages) > 1:
            msgid = tuple([denormalize(m) for m in messages])
        else:
            msgid = denormalize(messages[0])
        if isinstance(msgid, (list, tuple)):
            string = []
            for idx in range(catalog.num_plurals):
                try:
                    string.append(translations[idx])
                except IndexError:
                    string.append((idx, ''))
            string = tuple([denormalize(t[1]) for t in string])
        else:
            string = denormalize(translations[0][1])
        message = Message(msgid, string, list(locations), set(flags),
                          auto_comments, user_comments, lineno=offset[0] + 1)
        if obsolete[0]:
            if not ignore_obsolete:
                catalog.obsolete[msgid] = message
        else:
            catalog[msgid] = message
        del messages[:]; del translations[:]; del locations[:];
        del flags[:]; del auto_comments[:]; del user_comments[:]
        obsolete[0] = False
        counter[0] += 1

    def _process_message_line(lineno, line):
        if line.startswith('msgid_plural'):
            in_msgid[0] = True
            msg = line[12:].lstrip()
            messages.append(msg)
        elif line.startswith('msgid'):
            in_msgid[0] = True
            offset[0] = lineno
            txt = line[5:].lstrip()
            if messages:
                _add_message()
            messages.append(txt)
        elif line.startswith('msgstr'):
            in_msgid[0] = False
            in_msgstr[0] = True
            msg = line[6:].lstrip()
            if msg.startswith('['):
                idx, msg = msg[1:].split(']', 1)
                translations.append([int(idx), msg.lstrip()])
            else:
                translations.append([0, msg])
        elif line.startswith('"'):
            if in_msgid[0]:
                messages[-1] += u'\n' + line.rstrip()
            elif in_msgstr[0]:
                translations[-1][1] += u'\n' + line.rstrip()

    for lineno, line in enumerate(fileobj.readlines()):
        line = line.strip().decode(catalog.charset)
        if line.startswith('#'):
            in_msgid[0] = in_msgstr[0] = False
            if messages and translations:
                _add_message()
            if line[1:].startswith(':'):
                for location in line[2:].lstrip().split():
                    pos = location.rfind(':')
                    if pos >= 0:
                        try:
                            lineno = int(location[pos + 1:])
                        except ValueError:
                            continue
                        locations.append((location[:pos], lineno))
            elif line[1:].startswith(','):
                for flag in line[2:].lstrip().split(','):
                    flags.append(flag.strip())
            elif line[1:].startswith('~'):
                obsolete[0] = True
                _process_message_line(lineno, line[2:].lstrip())
            elif line[1:].startswith('.'):
                # These are called auto-comments
                comment = line[2:].strip()
                if comment: # Just check that we're not adding empty comments
                    auto_comments.append(comment)
            else:
                # These are called user comments
                user_comments.append(line[1:].strip())
        else:
            _process_message_line(lineno, line)

    if messages:
        _add_message()

    # No actual messages found, but there was some info in comments, from which
    # we'll construct an empty header message
    elif not counter[0] and (flags or user_comments or auto_comments):
        messages.append(u'')
        translations.append([0, u''])
        _add_message()

    return catalog

WORD_SEP = re.compile('('
    r'\s+|'                                 # any whitespace
    r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|' # hyphenated words
    r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w)'   # em-dash
')')

def escape(string):
    r"""Escape the given string so that it can be included in double-quoted
    strings in ``PO`` files.

    >>> escape('''Say:
    ...   "hello, world!"
    ... ''')
    '"Say:\\n  \\"hello, world!\\"\\n"'

    :param string: the string to escape
    :return: the escaped string
    :rtype: `str` or `unicode`
    """
    return '"%s"' % string.replace('\\', '\\\\') \
                          .replace('\t', '\\t') \
                          .replace('\r', '\\r') \
                          .replace('\n', '\\n') \
                          .replace('\"', '\\"')

def normalize(string, prefix='', width=76):
    r"""Convert a string into a format that is appropriate for .po files.

    >>> print normalize('''Say:
    ...   "hello, world!"
    ... ''', width=None)
    ""
    "Say:\n"
    "  \"hello, world!\"\n"

    >>> print normalize('''Say:
    ...   "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    ... ''', width=32)
    ""
    "Say:\n"
    "  \"Lorem ipsum dolor sit "
    "amet, consectetur adipisicing"
    " elit, \"\n"

    :param string: the string to normalize
    :param prefix: a string that should be prepended to every line
    :param width: the maximum line width; use `None`, 0, or a negative number
                  to completely disable line wrapping
    :return: the normalized string
    :rtype: `unicode`
    """
    if width and width > 0:
        prefixlen = len(prefix)
        lines = []
        for idx, line in enumerate(string.splitlines(True)):
            if len(escape(line)) + prefixlen > width:
                chunks = WORD_SEP.split(line)
                chunks.reverse()
                while chunks:
                    buf = []
                    size = 2
                    while chunks:
                        l = len(escape(chunks[-1])) - 2 + prefixlen
                        if size + l < width:
                            buf.append(chunks.pop())
                            size += l
                        else:
                            if not buf:
                                # handle long chunks by putting them on a
                                # separate line
                                buf.append(chunks.pop())
                            break
                    lines.append(u''.join(buf))
            else:
                lines.append(line)
    else:
        lines = string.splitlines(True)

    if len(lines) <= 1:
        return escape(string)

    # Remove empty trailing line
    if lines and not lines[-1]:
        del lines[-1]
        lines[-1] += '\n'
    return u'""\n' + u'\n'.join([(prefix + escape(l)) for l in lines])

def write_po(fileobj, catalog, width=76, no_location=False, omit_header=False,
             sort_output=False, sort_by_file=False, ignore_obsolete=False,
             include_previous=False):
    r"""Write a ``gettext`` PO (portable object) template file for a given
    message catalog to the provided file-like object.

    >>> catalog = Catalog()
    >>> catalog.add(u'foo %(name)s', locations=[('main.py', 1)],
    ...             flags=('fuzzy',))
    >>> catalog.add((u'bar', u'baz'), locations=[('main.py', 3)])
    >>> from StringIO import StringIO
    >>> buf = StringIO()
    >>> write_po(buf, catalog, omit_header=True)
    >>> print buf.getvalue()
    #: main.py:1
    #, fuzzy, python-format
    msgid "foo %(name)s"
    msgstr ""
    <BLANKLINE>
    #: main.py:3
    msgid "bar"
    msgid_plural "baz"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    <BLANKLINE>

    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param width: the maximum line width for the generated output; use `None`,
                  0, or a negative number to completely disable line wrapping
    :param no_location: do not emit a location comment for every message
    :param omit_header: do not include the ``msgid ""`` entry at the top of the
                        output
    :param sort_output: whether to sort the messages in the output by msgid
    :param sort_by_file: whether to sort the messages in the output by their
                         locations
    :param ignore_obsolete: whether to ignore obsolete messages and not include
                            them in the output; by default they are included as
                            comments
    :param include_previous: include the old msgid as a comment when
                             updating the catalog
    """
    def _normalize(key, prefix=''):
        return normalize(key, prefix=prefix, width=width) \
            .encode(catalog.charset, 'backslashreplace')

    def _write(text):
        if isinstance(text, unicode):
            text = text.encode(catalog.charset)
        fileobj.write(text)

    def _write_comment(comment, prefix=''):
        lines = comment
        if width and width > 0:
            lines = wraptext(comment, width)
        for line in lines:
            _write('#%s %s\n' % (prefix, line.strip()))

    def _write_message(message, prefix=''):
        if isinstance(message.id, (list, tuple)):
            _write('%smsgid %s\n' % (prefix, _normalize(message.id[0], prefix)))
            _write('%smsgid_plural %s\n' % (
                prefix, _normalize(message.id[1], prefix)
            ))

            for idx in range(catalog.num_plurals):
                try:
                    string = message.string[idx]
                except IndexError:
                    string = ''
                _write('%smsgstr[%d] %s\n' % (
                    prefix, idx, _normalize(string, prefix)
                ))
        else:
            _write('%smsgid %s\n' % (prefix, _normalize(message.id, prefix)))
            _write('%smsgstr %s\n' % (
                prefix, _normalize(message.string or '', prefix)
            ))

    messages = list(catalog)
    if sort_output:
        messages.sort()
    elif sort_by_file:
        messages.sort(lambda x,y: cmp(x.locations, y.locations))

    for message in messages:
        if not message.id: # This is the header "message"
            if omit_header:
                continue
            comment_header = catalog.header_comment
            if width and width > 0:
                lines = []
                for line in comment_header.splitlines():
                    lines += wraptext(line, width=width,
                                      subsequent_indent='# ')
                comment_header = u'\n'.join(lines) + u'\n'
            _write(comment_header)

        for comment in message.user_comments:
            _write_comment(comment)
        for comment in message.auto_comments:
            _write_comment(comment, prefix='.')

        if not no_location:
            locs = u' '.join([u'%s:%d' % (filename.replace(os.sep, '/'), lineno)
                              for filename, lineno in message.locations])
            _write_comment(locs, prefix=':')
        if message.flags:
            _write('#%s\n' % ', '.join([''] + list(message.flags)))

        if message.previous_id and include_previous:
            _write_comment('msgid %s' % _normalize(message.previous_id[0]),
                           prefix='|')
            if len(message.previous_id) > 1:
                _write_comment('msgid_plural %s' % _normalize(
                    message.previous_id[1]
                ), prefix='|')

        _write_message(message)
        _write('\n')

    if not ignore_obsolete:
        for message in catalog.obsolete.values():
            for comment in message.user_comments:
                _write_comment(comment)
            _write_message(message, prefix='#~ ')
            _write('\n')

########NEW FILE########
__FILENAME__ = numbers
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Locale dependent formatting and parsing of numeric data.

The default locale for the functions in this module is determined by the
following environment variables, in that order:

 * ``LC_NUMERIC``,
 * ``LC_ALL``, and
 * ``LANG``
"""
# TODO:
#  Padding and rounding increments in pattern:
#  - http://www.unicode.org/reports/tr35/ (Appendix G.6)
import math
import re
try:
    from decimal import Decimal
    have_decimal = True
except ImportError:
    have_decimal = False

from babel.core import default_locale, Locale

__all__ = ['format_number', 'format_decimal', 'format_currency',
           'format_percent', 'format_scientific', 'parse_number',
           'parse_decimal', 'NumberFormatError']
__docformat__ = 'restructuredtext en'

LC_NUMERIC = default_locale('LC_NUMERIC')

def get_currency_name(currency, locale=LC_NUMERIC):
    """Return the name used by the locale for the specified currency.
    
    >>> get_currency_name('USD', 'en_US')
    u'US Dollar'
    
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    :return: the currency symbol
    :rtype: `unicode`
    :since: version 0.9.4
    """
    return Locale.parse(locale).currencies.get(currency, currency)

def get_currency_symbol(currency, locale=LC_NUMERIC):
    """Return the symbol used by the locale for the specified currency.
    
    >>> get_currency_symbol('USD', 'en_US')
    u'$'
    
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    :return: the currency symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).currency_symbols.get(currency, currency)

def get_decimal_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate decimal fractions.
    
    >>> get_decimal_symbol('en_US')
    u'.'
    
    :param locale: the `Locale` object or locale identifier
    :return: the decimal symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('decimal', u'.')

def get_plus_sign_symbol(locale=LC_NUMERIC):
    """Return the plus sign symbol used by the current locale.
    
    >>> get_plus_sign_symbol('en_US')
    u'+'
    
    :param locale: the `Locale` object or locale identifier
    :return: the plus sign symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('plusSign', u'+')

def get_minus_sign_symbol(locale=LC_NUMERIC):
    """Return the plus sign symbol used by the current locale.
    
    >>> get_minus_sign_symbol('en_US')
    u'-'
    
    :param locale: the `Locale` object or locale identifier
    :return: the plus sign symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('minusSign', u'-')

def get_exponential_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate mantissa and exponent.
    
    >>> get_exponential_symbol('en_US')
    u'E'
    
    :param locale: the `Locale` object or locale identifier
    :return: the exponential symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('exponential', u'E')

def get_group_symbol(locale=LC_NUMERIC):
    """Return the symbol used by the locale to separate groups of thousands.
    
    >>> get_group_symbol('en_US')
    u','
    
    :param locale: the `Locale` object or locale identifier
    :return: the group symbol
    :rtype: `unicode`
    """
    return Locale.parse(locale).number_symbols.get('group', u',')

def format_number(number, locale=LC_NUMERIC):
    """Return the given number formatted for a specific locale.
    
    >>> format_number(1099, locale='en_US')
    u'1,099'
    
    :param number: the number to format
    :param locale: the `Locale` object or locale identifier
    :return: the formatted number
    :rtype: `unicode`
    """
    # Do we really need this one?
    return format_decimal(number, locale=locale)

def format_decimal(number, format=None, locale=LC_NUMERIC):
    """Return the given decimal number formatted for a specific locale.
    
    >>> format_decimal(1.2345, locale='en_US')
    u'1.234'
    >>> format_decimal(1.2346, locale='en_US')
    u'1.235'
    >>> format_decimal(-1.2346, locale='en_US')
    u'-1.235'
    >>> format_decimal(1.2345, locale='sv_SE')
    u'1,234'
    >>> format_decimal(12345, locale='de')
    u'12.345'

    The appropriate thousands grouping and the decimal separator are used for
    each locale:
    
    >>> format_decimal(12345.5, locale='en_US')
    u'12,345.5'

    :param number: the number to format
    :param format: 
    :param locale: the `Locale` object or locale identifier
    :return: the formatted decimal number
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.decimal_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)

def format_currency(number, currency, format=None, locale=LC_NUMERIC):
    u"""Return formatted currency value.
    
    >>> format_currency(1099.98, 'USD', locale='en_US')
    u'$1,099.98'
    >>> format_currency(1099.98, 'USD', locale='es_CO')
    u'US$\\xa01.099,98'
    >>> format_currency(1099.98, 'EUR', locale='de_DE')
    u'1.099,98\\xa0\\u20ac'
    
    The pattern can also be specified explicitly:
    
    >>> format_currency(1099.98, 'EUR', u'\xa4\xa4 #,##0.00', locale='en_US')
    u'EUR 1,099.98'
    
    :param number: the number to format
    :param currency: the currency code
    :param locale: the `Locale` object or locale identifier
    :return: the formatted currency value
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.currency_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale, currency=currency)

def format_percent(number, format=None, locale=LC_NUMERIC):
    """Return formatted percent value for a specific locale.
    
    >>> format_percent(0.34, locale='en_US')
    u'34%'
    >>> format_percent(25.1234, locale='en_US')
    u'2,512%'
    >>> format_percent(25.1234, locale='sv_SE')
    u'2\\xa0512\\xa0%'

    The format pattern can also be specified explicitly:
    
    >>> format_percent(25.1234, u'#,##0\u2030', locale='en_US')
    u'25,123\u2030'

    :param number: the percent number to format
    :param format: 
    :param locale: the `Locale` object or locale identifier
    :return: the formatted percent number
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.percent_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)

def format_scientific(number, format=None, locale=LC_NUMERIC):
    """Return value formatted in scientific notation for a specific locale.
    
    >>> format_scientific(10000, locale='en_US')
    u'1E4'

    The format pattern can also be specified explicitly:
    
    >>> format_scientific(1234567, u'##0E00', locale='en_US')
    u'1.23E06'

    :param number: the number to format
    :param format: 
    :param locale: the `Locale` object or locale identifier
    :return: value formatted in scientific notation.
    :rtype: `unicode`
    """
    locale = Locale.parse(locale)
    if not format:
        format = locale.scientific_formats.get(format)
    pattern = parse_pattern(format)
    return pattern.apply(number, locale)


class NumberFormatError(ValueError):
    """Exception raised when a string cannot be parsed into a number."""


def parse_number(string, locale=LC_NUMERIC):
    """Parse localized number string into a long integer.
    
    >>> parse_number('1,099', locale='en_US')
    1099L
    >>> parse_number('1.099', locale='de_DE')
    1099L
    
    When the given string cannot be parsed, an exception is raised:
    
    >>> parse_number('1.099,98', locale='de')
    Traceback (most recent call last):
        ...
    NumberFormatError: '1.099,98' is not a valid number
    
    :param string: the string to parse
    :param locale: the `Locale` object or locale identifier
    :return: the parsed number
    :rtype: `long`
    :raise `NumberFormatError`: if the string can not be converted to a number
    """
    try:
        return long(string.replace(get_group_symbol(locale), ''))
    except ValueError:
        raise NumberFormatError('%r is not a valid number' % string)

def parse_decimal(string, locale=LC_NUMERIC):
    """Parse localized decimal string into a float.
    
    >>> parse_decimal('1,099.98', locale='en_US')
    1099.98
    >>> parse_decimal('1.099,98', locale='de')
    1099.98
    
    When the given string cannot be parsed, an exception is raised:
    
    >>> parse_decimal('2,109,998', locale='de')
    Traceback (most recent call last):
        ...
    NumberFormatError: '2,109,998' is not a valid decimal number
    
    :param string: the string to parse
    :param locale: the `Locale` object or locale identifier
    :return: the parsed decimal number
    :rtype: `float`
    :raise `NumberFormatError`: if the string can not be converted to a
                                decimal number
    """
    locale = Locale.parse(locale)
    try:
        return float(string.replace(get_group_symbol(locale), '')
                           .replace(get_decimal_symbol(locale), '.'))
    except ValueError:
        raise NumberFormatError('%r is not a valid decimal number' % string)


PREFIX_END = r'[^0-9@#.,]'
NUMBER_TOKEN = r'[0-9@#.\-,E+]'

PREFIX_PATTERN = r"(?P<prefix>(?:'[^']*'|%s)*)" % PREFIX_END
NUMBER_PATTERN = r"(?P<number>%s+)" % NUMBER_TOKEN
SUFFIX_PATTERN = r"(?P<suffix>.*)"

number_re = re.compile(r"%s%s%s" % (PREFIX_PATTERN, NUMBER_PATTERN,
                                    SUFFIX_PATTERN))

def split_number(value):
    """Convert a number into a (intasstring, fractionasstring) tuple"""
    if have_decimal and isinstance(value, Decimal):
        text = str(value)
    else:
        text = ('%.9f' % value).rstrip('0')
    if '.' in text:
        a, b = text.split('.', 1)
        if b == '0':
            b = ''
    else:
        a, b = text, ''
    return a, b

def bankersround(value, ndigits=0):
    """Round a number to a given precision.

    Works like round() except that the round-half-even (banker's rounding)
    algorithm is used instead of round-half-up.

    >>> bankersround(5.5, 0)
    6.0
    >>> bankersround(6.5, 0)
    6.0
    >>> bankersround(-6.5, 0)
    -6.0
    >>> bankersround(1234.0, -2)
    1200.0
    """
    sign = int(value < 0) and -1 or 1
    value = abs(value)
    a, b = split_number(value)
    digits = a + b
    add = 0
    i = len(a) + ndigits
    if i < 0 or i >= len(digits):
        pass
    elif digits[i] > '5':
        add = 1
    elif digits[i] == '5' and digits[i-1] in '13579':
        add = 1
    scale = 10**ndigits
    if have_decimal and isinstance(value, Decimal):
        return Decimal(int(value * scale + add)) / scale * sign
    else:
        return float(int(value * scale + add)) / scale * sign

def parse_pattern(pattern):
    """Parse number format patterns"""
    if isinstance(pattern, NumberPattern):
        return pattern

    # Do we have a negative subpattern?
    if ';' in pattern:
        pattern, neg_pattern = pattern.split(';', 1)
        pos_prefix, number, pos_suffix = number_re.search(pattern).groups()
        neg_prefix, _, neg_suffix = number_re.search(neg_pattern).groups()
    else:
        pos_prefix, number, pos_suffix = number_re.search(pattern).groups()
        neg_prefix = '-' + pos_prefix
        neg_suffix = pos_suffix
    if 'E' in number:
        number, exp = number.split('E', 1)
    else:
        exp = None
    if '@' in number:
        if '.' in number and '0' in number:
            raise ValueError('Significant digit patterns can not contain '
                             '"@" or "0"')
    if '.' in number:
        integer, fraction = number.rsplit('.', 1)
    else:
        integer = number
        fraction = ''
    min_frac = max_frac = 0

    def parse_precision(p):
        """Calculate the min and max allowed digits"""
        min = max = 0
        for c in p:
            if c in '@0':
                min += 1
                max += 1
            elif c == '#':
                max += 1
            elif c == ',':
                continue
            else:
                break
        return min, max

    def parse_grouping(p):
        """Parse primary and secondary digit grouping

        >>> parse_grouping('##')
        0, 0
        >>> parse_grouping('#,###')
        3, 3
        >>> parse_grouping('#,####,###')
        3, 4
        """
        width = len(p)
        g1 = p.rfind(',')
        if g1 == -1:
            return 1000, 1000
        g1 = width - g1 - 1
        g2 = p[:-g1 - 1].rfind(',')
        if g2 == -1:
            return g1, g1
        g2 = width - g1 - g2 - 2
        return g1, g2

    int_prec = parse_precision(integer)
    frac_prec = parse_precision(fraction)
    if exp:
        frac_prec = parse_precision(integer+fraction)
        exp_plus = exp.startswith('+')
        exp = exp.lstrip('+')
        exp_prec = parse_precision(exp)
    else:
        exp_plus = None
        exp_prec = None
    grouping = parse_grouping(integer)
    return NumberPattern(pattern, (pos_prefix, neg_prefix), 
                         (pos_suffix, neg_suffix), grouping,
                         int_prec, frac_prec, 
                         exp_prec, exp_plus)


class NumberPattern(object):

    def __init__(self, pattern, prefix, suffix, grouping,
                 int_prec, frac_prec, exp_prec, exp_plus):
        self.pattern = pattern
        self.prefix = prefix
        self.suffix = suffix
        self.grouping = grouping
        self.int_prec = int_prec
        self.frac_prec = frac_prec
        self.exp_prec = exp_prec
        self.exp_plus = exp_plus
        if '%' in ''.join(self.prefix + self.suffix):
            self.scale = 100
        elif u'‰' in ''.join(self.prefix + self.suffix):
            self.scale = 1000
        else:
            self.scale = 1

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.pattern)

    def apply(self, value, locale, currency=None):
        value *= self.scale
        is_negative = int(value < 0)
        if self.exp_prec: # Scientific notation
            value = abs(value)
            if value:
                exp = int(math.floor(math.log(value, 10)))
            else:
                exp = 0
            # Minimum number of integer digits
            if self.int_prec[0] == self.int_prec[1]:
                exp -= self.int_prec[0] - 1
            # Exponent grouping
            elif self.int_prec[1]:
                exp = int(exp) / self.int_prec[1] * self.int_prec[1]
            if not have_decimal or not isinstance(value, Decimal):
                value = float(value)
            if exp < 0:
                value = value * 10**(-exp)
            else:
                value = value / 10**exp
            exp_sign = ''
            if exp < 0:
                exp_sign = get_minus_sign_symbol(locale)
            elif self.exp_plus:
                exp_sign = get_plus_sign_symbol(locale)
            exp = abs(exp)
            number = u'%s%s%s%s' % \
                 (self._format_sigdig(value, self.frac_prec[0], 
                                     self.frac_prec[1]), 
                  get_exponential_symbol(locale),  exp_sign,
                  self._format_int(str(exp), self.exp_prec[0],
                                   self.exp_prec[1], locale))
        elif '@' in self.pattern: # Is it a siginificant digits pattern?
            text = self._format_sigdig(abs(value),
                                      self.int_prec[0],
                                      self.int_prec[1])
            if '.' in text:
                a, b = text.split('.')
                a = self._format_int(a, 0, 1000, locale)
                if b:
                    b = get_decimal_symbol(locale) + b
                number = a + b
            else:
                number = self._format_int(text, 0, 1000, locale)
        else: # A normal number pattern
            a, b = split_number(bankersround(abs(value), 
                                             self.frac_prec[1]))
            b = b or '0'
            a = self._format_int(a, self.int_prec[0],
                                 self.int_prec[1], locale)
            b = self._format_frac(b, locale)
            number = a + b
        retval = u'%s%s%s' % (self.prefix[is_negative], number,
                                self.suffix[is_negative])
        if u'¤' in retval:
            retval = retval.replace(u'¤¤', currency.upper())
            retval = retval.replace(u'¤', get_currency_symbol(currency, locale))
        return retval

    def _format_sigdig(self, value, min, max):
        """Convert value to a string.

        The resulting string will contain between (min, max) number of
        significant digits.
        """
        a, b = split_number(value)
        ndecimals = len(a)
        if a == '0' and b != '':
            ndecimals = 0
            while b.startswith('0'):
                b = b[1:]
                ndecimals -= 1
        a, b = split_number(bankersround(value, max - ndecimals))
        digits = len((a + b).lstrip('0'))
        if not digits:
            digits = 1
        # Figure out if we need to add any trailing '0':s
        if len(a) >= max and a != '0':
            return a
        if digits < min:
            b += ('0' * (min - digits))
        if b:
            return '%s.%s' % (a, b)
        return a

    def _format_int(self, value, min, max, locale):
        width = len(value)
        if width < min:
            value = '0' * (min - width) + value
        gsize = self.grouping[0]
        ret = ''
        symbol = get_group_symbol(locale)
        while len(value) > gsize:
            ret = symbol + value[-gsize:] + ret
            value = value[:-gsize]
            gsize = self.grouping[1]
        return value + ret

    def _format_frac(self, value, locale):
        min, max = self.frac_prec
        if len(value) < min:
            value += ('0' * (min - len(value)))
        if max == 0 or (min == 0 and int(value) == 0):
            return ''
        width = len(value)
        while len(value) > min and value[-1] == '0':
            value = value[:-1]
        return get_decimal_symbol(locale) + value

########NEW FILE########
__FILENAME__ = support
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Several classes and functions that help with integrating and using Babel
in applications.

.. note: the code in this module is not used by Babel itself
"""

from datetime import date, datetime, time
import gettext

try:
    set
except NameError:
    from sets import set

from babel.core import Locale
from babel.dates import format_date, format_datetime, format_time, LC_TIME
from babel.numbers import format_number, format_decimal, format_currency, \
                          format_percent, format_scientific, LC_NUMERIC
from babel.util import UTC

__all__ = ['Format', 'LazyProxy', 'Translations']
__docformat__ = 'restructuredtext en'


class Format(object):
    """Wrapper class providing the various date and number formatting functions
    bound to a specific locale and time-zone.
    
    >>> fmt = Format('en_US', UTC)
    >>> fmt.date(date(2007, 4, 1))
    u'Apr 1, 2007'
    >>> fmt.decimal(1.2345)
    u'1.234'
    """

    def __init__(self, locale, tzinfo=None):
        """Initialize the formatter.
        
        :param locale: the locale identifier or `Locale` instance
        :param tzinfo: the time-zone info (a `tzinfo` instance or `None`)
        """
        self.locale = Locale.parse(locale)
        self.tzinfo = tzinfo

    def date(self, date=None, format='medium'):
        """Return a date formatted according to the given pattern.
        
        >>> fmt = Format('en_US')
        >>> fmt.date(date(2007, 4, 1))
        u'Apr 1, 2007'
        
        :see: `babel.dates.format_date`
        """
        return format_date(date, format, locale=self.locale)

    def datetime(self, datetime=None, format='medium'):
        """Return a date and time formatted according to the given pattern.
        
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.datetime(datetime(2007, 4, 1, 15, 30))
        u'Apr 1, 2007 11:30:00 AM'
        
        :see: `babel.dates.format_datetime`
        """
        return format_datetime(datetime, format, tzinfo=self.tzinfo,
                               locale=self.locale)

    def time(self, time=None, format='medium'):
        """Return a time formatted according to the given pattern.
        
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.time(datetime(2007, 4, 1, 15, 30))
        u'11:30:00 AM'
        
        :see: `babel.dates.format_time`
        """
        return format_time(time, format, tzinfo=self.tzinfo, locale=self.locale)

    def number(self, number):
        """Return an integer number formatted for the locale.
        
        >>> fmt = Format('en_US')
        >>> fmt.number(1099)
        u'1,099'
        
        :see: `babel.numbers.format_number`
        """
        return format_number(number, locale=self.locale)

    def decimal(self, number, format=None):
        """Return a decimal number formatted for the locale.
        
        >>> fmt = Format('en_US')
        >>> fmt.decimal(1.2345)
        u'1.234'
        
        :see: `babel.numbers.format_decimal`
        """
        return format_decimal(number, format, locale=self.locale)

    def currency(self, number, currency):
        """Return a number in the given currency formatted for the locale.
        
        :see: `babel.numbers.format_currency`
        """
        return format_currency(number, currency, locale=self.locale)

    def percent(self, number, format=None):
        """Return a number formatted as percentage for the locale.
        
        >>> fmt = Format('en_US')
        >>> fmt.percent(0.34)
        u'34%'
        
        :see: `babel.numbers.format_percent`
        """
        return format_percent(number, format, locale=self.locale)

    def scientific(self, number):
        """Return a number formatted using scientific notation for the locale.
        
        :see: `babel.numbers.format_scientific`
        """
        return format_scientific(number, locale=self.locale)


class LazyProxy(object):
    """Class for proxy objects that delegate to a specified function to evaluate
    the actual object.
    
    >>> def greeting(name='world'):
    ...     return 'Hello, %s!' % name
    >>> lazy_greeting = LazyProxy(greeting, name='Joe')
    >>> print lazy_greeting
    Hello, Joe!
    >>> u'  ' + lazy_greeting
    u'  Hello, Joe!'
    >>> u'(%s)' % lazy_greeting
    u'(Hello, Joe!)'
    
    This can be used, for example, to implement lazy translation functions that
    delay the actual translation until the string is actually used. The
    rationale for such behavior is that the locale of the user may not always
    be available. In web applications, you only know the locale when processing
    a request.
    
    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting:
    
    >>> greetings = [
    ...     LazyProxy(greeting, 'world'),
    ...     LazyProxy(greeting, 'Joe'),
    ...     LazyProxy(greeting, 'universe'),
    ... ]
    >>> greetings.sort()
    >>> for greeting in greetings:
    ...     print greeting
    Hello, Joe!
    Hello, universe!
    Hello, world!
    """
    __slots__ = ['_func', '_args', '_kwargs', '_value']

    def __init__(self, func, *args, **kwargs):
        # Avoid triggering our own __setattr__ implementation
        object.__setattr__(self, '_func', func)
        object.__setattr__(self, '_args', args)
        object.__setattr__(self, '_kwargs', kwargs)
        object.__setattr__(self, '_value', None)

    def value(self):
        if self._value is None:
            value = self._func(*self._args, **self._kwargs)
            object.__setattr__(self, '_value', value)
        return self._value
    value = property(value)

    def __contains__(self, key):
        return key in self.value

    def __nonzero__(self):
        return bool(self.value)

    def __dir__(self):
        return dir(self.value)

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __add__(self, other):
        return self.value + other

    def __radd__(self, other):
        return other + self.value

    def __mod__(self, other):
        return self.value % other

    def __rmod__(self, other):
        return other % self.value

    def __mul__(self, other):
        return self.value * other

    def __rmul__(self, other):
        return other * self.value

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    def __delattr__(self, name):
        delattr(self.value, name)

    def __getattr__(self, name):
        return getattr(self.value, name)

    def __setattr__(self, name, value):
        setattr(self.value, name, value)

    def __delitem__(self, key):
        del self.value[key]

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    
class Translations(gettext.GNUTranslations, object):
    """An extended translation catalog class."""

    DEFAULT_DOMAIN = 'messages'

    def __init__(self, fileobj=None, domain=DEFAULT_DOMAIN):
        """Initialize the translations catalog.

        :param fileobj: the file-like object the translation should be read
                        from
        """
        gettext.GNUTranslations.__init__(self, fp=fileobj)
        self.files = filter(None, [getattr(fileobj, 'name', None)])
        self.domain = domain
        self._domains = {}

    def load(cls, dirname=None, locales=None, domain=DEFAULT_DOMAIN):
        """Load translations from the given directory.

        :param dirname: the directory containing the ``MO`` files
        :param locales: the list of locales in order of preference (items in
                        this list can be either `Locale` objects or locale
                        strings)
        :param domain: the message domain
        :return: the loaded catalog, or a ``NullTranslations`` instance if no
                 matching translations were found
        :rtype: `Translations`
        """
        if locales is not None:
            if not isinstance(locales, (list, tuple)):
                locales = [locales]
            locales = [str(locale) for locale in locales]
        if not domain:
            domain = cls.DEFAULT_DOMAIN
        filename = gettext.find(domain, dirname, locales)
        if not filename:
            return gettext.NullTranslations()
        return cls(fileobj=open(filename, 'rb'), domain=domain)
    load = classmethod(load)

    def __repr__(self):
        return '<%s: "%s">' % (type(self).__name__,
                               self._info.get('project-id-version'))

    def add(self, translations, merge=True):
        """Add the given translations to the catalog.

        If the domain of the translations is different than that of the
        current catalog, they are added as a catalog that is only accessible
        by the various ``d*gettext`` functions.

        :param translations: the `Translations` instance with the messages to
                             add
        :param merge: whether translations for message domains that have
                      already been added should be merged with the existing
                      translations
        :return: the `Translations` instance (``self``) so that `merge` calls
                 can be easily chained
        :rtype: `Translations`
        """
        domain = getattr(translations, 'domain', self.DEFAULT_DOMAIN)
        if merge and domain == self.domain:
            return self.merge(translations)

        existing = self._domains.get(domain)
        if merge and existing is not None:
            existing.merge(translations)
        else:
            translations.add_fallback(self)
            self._domains[domain] = translations

        return self

    def merge(self, translations):
        """Merge the given translations into the catalog.

        Message translations in the specified catalog override any messages
        with the same identifier in the existing catalog.

        :param translations: the `Translations` instance with the messages to
                             merge
        :return: the `Translations` instance (``self``) so that `merge` calls
                 can be easily chained
        :rtype: `Translations`
        """
        if isinstance(translations, gettext.GNUTranslations):
            self._catalog.update(translations._catalog)
            if isinstance(translations, Translations):
                self.files.extend(translations.files)

        return self

    def dgettext(self, domain, message):
        """Like ``gettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).gettext(message)
    
    def ldgettext(self, domain, message):
        """Like ``lgettext()``, but look the message up in the specified 
        domain.
        """ 
        return self._domains.get(domain, self).lgettext(message)
    
    def dugettext(self, domain, message):
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ugettext(message)
    
    def dngettext(self, domain, singular, plural, num):
        """Like ``ngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ngettext(singular, plural, num)
    
    def ldngettext(self, domain, singular, plural, num):
        """Like ``lngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).lngettext(singular, plural, num)
    
    def dungettext(self, domain, singular, plural, num):
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ungettext(singular, plural, num)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

"""Various utility classes and functions."""

import codecs
from datetime import timedelta, tzinfo
import os
import re
try:
    set
except NameError:
    from sets import Set as set
import textwrap
import time
from itertools import izip, imap
missing = object()

__all__ = ['distinct', 'pathmatch', 'relpath', 'wraptext', 'odict', 'UTC',
           'LOCALTZ']
__docformat__ = 'restructuredtext en'


def distinct(iterable):
    """Yield all items in an iterable collection that are distinct.

    Unlike when using sets for a similar effect, the original ordering of the
    items in the collection is preserved by this function.

    >>> print list(distinct([1, 2, 1, 3, 4, 4]))
    [1, 2, 3, 4]
    >>> print list(distinct('foobar'))
    ['f', 'o', 'b', 'a', 'r']

    :param iterable: the iterable collection providing the data
    :return: the distinct items in the collection
    :rtype: ``iterator``
    """
    seen = set()
    for item in iter(iterable):
        if item not in seen:
            yield item
            seen.add(item)

# Regexp to match python magic encoding line
PYTHON_MAGIC_COMMENT_re = re.compile(
    r'[ \t\f]* \# .* coding[=:][ \t]*([-\w.]+)', re.VERBOSE)
def parse_encoding(fp):
    """Deduce the encoding of a source file from magic comment.

    It does this in the same way as the `Python interpreter`__

    .. __: http://docs.python.org/ref/encodings.html

    The ``fp`` argument should be a seekable file object.

    (From Jeff Dairiki)
    """
    pos = fp.tell()
    fp.seek(0)
    try:
        line1 = fp.readline()
        has_bom = line1.startswith(codecs.BOM_UTF8)
        if has_bom:
            line1 = line1[len(codecs.BOM_UTF8):]

        m = PYTHON_MAGIC_COMMENT_re.match(line1)
        if not m:
            try:
                import parser
                parser.suite(line1)
            except (ImportError, SyntaxError):
                # Either it's a real syntax error, in which case the source is
                # not valid python source, or line2 is a continuation of line1,
                # in which case we don't want to scan line2 for a magic
                # comment.
                pass
            else:
                line2 = fp.readline()
                m = PYTHON_MAGIC_COMMENT_re.match(line2)

        if has_bom:
            if m:
                raise SyntaxError(
                    "python refuses to compile code with both a UTF8 "
                    "byte-order-mark and a magic encoding comment")
            return 'utf_8'
        elif m:
            return m.group(1)
        else:
            return None
    finally:
        fp.seek(pos)

def pathmatch(pattern, filename):
    """Extended pathname pattern matching.
    
    This function is similar to what is provided by the ``fnmatch`` module in
    the Python standard library, but:
    
     * can match complete (relative or absolute) path names, and not just file
       names, and
     * also supports a convenience pattern ("**") to match files at any
       directory level.
    
    Examples:
    
    >>> pathmatch('**.py', 'bar.py')
    True
    >>> pathmatch('**.py', 'foo/bar/baz.py')
    True
    >>> pathmatch('**.py', 'templates/index.html')
    False
    
    >>> pathmatch('**/templates/*.html', 'templates/index.html')
    True
    >>> pathmatch('**/templates/*.html', 'templates/foo/bar.html')
    False
    
    :param pattern: the glob pattern
    :param filename: the path name of the file to match against
    :return: `True` if the path name matches the pattern, `False` otherwise
    :rtype: `bool`
    """
    symbols = {
        '?':   '[^/]',
        '?/':  '[^/]/',
        '*':   '[^/]+',
        '*/':  '[^/]+/',
        '**/': '(?:.+/)*?',
        '**':  '(?:.+/)*?[^/]+',
    }
    buf = []
    for idx, part in enumerate(re.split('([?*]+/?)', pattern)):
        if idx % 2:
            buf.append(symbols[part])
        elif part:
            buf.append(re.escape(part))
    match = re.match(''.join(buf) + '$', filename.replace(os.sep, '/'))
    return match is not None


class TextWrapper(textwrap.TextWrapper):
    wordsep_re = re.compile(
        r'(\s+|'                                  # any whitespace
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))'    # em-dash
    )


def wraptext(text, width=70, initial_indent='', subsequent_indent=''):
    """Simple wrapper around the ``textwrap.wrap`` function in the standard
    library. This version does not wrap lines on hyphens in words.
    
    :param text: the text to wrap
    :param width: the maximum line width
    :param initial_indent: string that will be prepended to the first line of
                           wrapped output
    :param subsequent_indent: string that will be prepended to all lines save
                              the first of wrapped output
    :return: a list of lines
    :rtype: `list`
    """
    wrapper = TextWrapper(width=width, initial_indent=initial_indent,
                          subsequent_indent=subsequent_indent,
                          break_long_words=False)
    return wrapper.wrap(text)


class odict(dict):
    """Ordered dict implementation.
    
    :see: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747
    """
    def __init__(self, data=None):
        dict.__init__(self, data or {})
        self._keys = dict.keys(self)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        if key not in self._keys:
            self._keys.append(key)

    def __iter__(self):
        return iter(self._keys)
    iterkeys = __iter__

    def clear(self):
        dict.clear(self)
        self._keys = []

    def copy(self):
        d = odict()
        d.update(self)
        return d

    def items(self):
        return zip(self._keys, self.values())

    def iteritems(self):
        return izip(self._keys, self.itervalues())

    def keys(self):
        return self._keys[:]

    def pop(self, key, default=missing):
        if default is missing:
            return dict.pop(self, key)
        elif key not in self:
            return default
        self._keys.remove(key)
        return dict.pop(self, key, default)

    def popitem(self, key):
        self._keys.remove(key)
        return dict.popitem(key)

    def setdefault(self, key, failobj = None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, dict):
        for (key, val) in dict.items():
            self[key] = val

    def values(self):
        return map(self.get, self._keys)

    def itervalues(self):
        return imap(self.get, self._keys)


try:
    relpath = os.path.relpath
except AttributeError:
    def relpath(path, start='.'):
        """Compute the relative path to one path from another.
        
        >>> relpath('foo/bar.txt', '').replace(os.sep, '/')
        'foo/bar.txt'
        >>> relpath('foo/bar.txt', 'foo').replace(os.sep, '/')
        'bar.txt'
        >>> relpath('foo/bar.txt', 'baz').replace(os.sep, '/')
        '../foo/bar.txt'
        
        :return: the relative path
        :rtype: `basestring`
        """
        start_list = os.path.abspath(start).split(os.sep)
        path_list = os.path.abspath(path).split(os.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list) - i) + path_list[i:]
        return os.path.join(*rel_list)

ZERO = timedelta(0)


class FixedOffsetTimezone(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name=None):
        self._offset = timedelta(minutes=offset)
        if name is None:
            name = 'Etc/GMT+%d' % offset
        self.zone = name

    def __str__(self):
        return self.zone

    def __repr__(self):
        return '<FixedOffset "%s" %s>' % (self.zone, self._offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self.zone

    def dst(self, dt):
        return ZERO


try:
    from pytz import UTC
except ImportError:
    UTC = FixedOffsetTimezone(0, 'UTC')
    """`tzinfo` object for UTC (Universal Time).
    
    :type: `tzinfo`
    """

STDOFFSET = timedelta(seconds = -time.timezone)
if time.daylight:
    DSTOFFSET = timedelta(seconds = -time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET


class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0


LOCALTZ = LocalTimezone()
"""`tzinfo` object for local time-zone.

:type: `tzinfo`
"""

########NEW FILE########
__FILENAME__ = dictconfig
# Copyright 2009-2010 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import logging.handlers
import re
import sys
import types

IDENTIFIER = re.compile('^[a-z_][a-z0-9_]*$', re.I)

def valid_ident(s):
    m = IDENTIFIER.match(s)
    if not m:
        raise ValueError('Not a valid Python identifier: %r' % s)
    return True

#
# This function is defined in logging only in recent versions of Python
#
try:
    from logging import _checkLevel
except ImportError:
    def _checkLevel(level):
        if isinstance(level, int):
            rv = level
        elif str(level) == level:
            if level not in logging._levelNames:
                raise ValueError('Unknown level: %r' % level)
            rv = logging._levelNames[level]
        else:
            raise TypeError('Level not an integer or a '
                            'valid string: %r' % level)
        return rv

# The ConvertingXXX classes are wrappers around standard Python containers,
# and they serve to convert any suitable values in the container. The
# conversion converts base dicts, lists and tuples to their wrapped
# equivalents, whereas strings which match a conversion format are converted
# appropriately.
#
# Each wrapper should have a configurator attribute holding the actual
# configurator to use for conversion.

class ConvertingDict(dict):
    """A converting dictionary wrapper."""

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result
        
    def get(self, key, default=None):
        value = dict.get(self, key, default)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result
        
    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

class ConvertingList(list):
    """A converting list wrapper."""
    def __getitem__(self, key):
        value = list.__getitem__(self, key)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def pop(self, idx=-1):
        value = list.pop(self, idx)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
        return result

class ConvertingTuple(tuple):
    """A converting tuple wrapper."""
    def __getitem__(self, key):
        value = tuple.__getitem__(self, key)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

class BaseConfigurator(object):
    """
    The configurator base class which defines some useful defaults.
    """
    
    CONVERT_PATTERN = re.compile(r'^(?P<prefix>[a-z]+)://(?P<suffix>.*)$')

    WORD_PATTERN = re.compile(r'^\s*(\w+)\s*')
    DOT_PATTERN = re.compile(r'^\.\s*(\w+)\s*')
    INDEX_PATTERN = re.compile(r'^\[\s*(\w+)\s*\]\s*')
    DIGIT_PATTERN = re.compile(r'^\d+$')

    value_converters = {
        'ext' : 'ext_convert',
        'cfg' : 'cfg_convert',
    }

    # We might want to use a different one, e.g. importlib
    importer = __import__

    def __init__(self, config):
        self.config = ConvertingDict(config)
        self.config.configurator = self

    def resolve(self, s):
        """
        Resolve strings to objects using standard import and attribute
        syntax.
        """
        name = s.split('.')
        used = name.pop(0)
        try:
            found = self.importer(used)
            for frag in name:
                used += '.' + frag
                try:
                    found = getattr(found, frag)
                except AttributeError:
                    self.importer(used)
                    found = getattr(found, frag)
            return found
        except ImportError:
            e, tb = sys.exc_info()[1:]
            v = ValueError('Cannot resolve %r: %s' % (s, e))
            v.__cause__, v.__traceback__ = e, tb
            raise v

    def ext_convert(self, value):
        """Default converter for the ext:// protocol."""
        return self.resolve(value)
    
    def cfg_convert(self, value):
        """Default converter for the cfg:// protocol."""
        rest = value
        m = self.WORD_PATTERN.match(rest)
        if m is None:
            raise ValueError("Unable to convert %r" % value)
        else:
            rest = rest[m.end():]
            d = self.config[m.groups()[0]]
            #print d, rest
            while rest:
                m = self.DOT_PATTERN.match(rest)
                if m:
                    d = d[m.groups()[0]]
                else:
                    m = self.INDEX_PATTERN.match(rest)
                    if m:
                        idx = m.groups()[0]
                        if not self.DIGIT_PATTERN.match(idx):
                            d = d[idx]
                        else:
                            try:
                                n = int(idx) # try as number first (most likely)
                                d = d[n]
                            except TypeError:
                                d = d[idx]
                if m:
                    rest = rest[m.end():]
                else:
                    raise ValueError('Unable to convert '
                                     '%r at %r' % (value, rest))
        #rest should be empty
        return d

    def convert(self, value):
        """
        Convert values to an appropriate type. dicts, lists and tuples are
        replaced by their converting alternatives. Strings are checked to
        see if they have a conversion format and are converted if they do.
        """
        if not isinstance(value, ConvertingDict) and isinstance(value, dict):
            value = ConvertingDict(value)
            value.configurator = self
        elif not isinstance(value, ConvertingList) and isinstance(value, list):
            value = ConvertingList(value)
            value.configurator = self
        elif not isinstance(value, ConvertingTuple) and\
                 isinstance(value, tuple):
            value = ConvertingTuple(value)
            value.configurator = self
        elif isinstance(value, basestring): # str for py3k
            m = self.CONVERT_PATTERN.match(value)
            if m:
                d = m.groupdict()
                prefix = d['prefix']
                converter = self.value_converters.get(prefix, None)
                if converter:
                    suffix = d['suffix']
                    converter = getattr(self, converter)
                    value = converter(suffix)
        return value
    
    def configure_custom(self, config):
        """Configure an object with a user-supplied factory."""
        c = config.pop('()')
        if not hasattr(c, '__call__') and hasattr(types, 'ClassType') and type(c) != types.ClassType:
            c = self.resolve(c)
        props = config.pop('.', None)
        # Check for valid identifiers
        kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
        result = c(**kwargs)
        if props:
            for name, value in props.items():
                setattr(result, name, value)
        return result

    def as_tuple(self, value):
        """Utility function which converts lists to tuples."""
        if isinstance(value, list):
            value = tuple(value)
        return value

class DictConfigurator(BaseConfigurator):
    """
    Configure logging using a dictionary-like object to describe the
    configuration.
    """

    def configure(self):
        """Do the configuration."""

        config = self.config
        if 'version' not in config:
            raise ValueError("dictionary doesn't specify a version")
        if config['version'] != 1:
            raise ValueError("Unsupported version: %s" % config['version'])
        incremental = config.pop('incremental', False)
        EMPTY_DICT = {}
        logging._acquireLock()
        try:
            if incremental:
                handlers = config.get('handlers', EMPTY_DICT)
                # incremental handler config only if handler name
                # ties in to logging._handlers (Python 2.7)
                if sys.version_info[:2] == (2, 7):
                    for name in handlers:
                        if name not in logging._handlers:
                            raise ValueError('No handler found with '
                                             'name %r'  % name)
                        else:
                            try:
                                handler = logging._handlers[name]
                                handler_config = handlers[name]
                                level = handler_config.get('level', None)
                                if level:
                                    handler.setLevel(_checkLevel(level))
                            except StandardError, e:
                                raise ValueError('Unable to configure handler '
                                                 '%r: %s' % (name, e))
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    try:
                        self.configure_logger(name, loggers[name], True)
                    except StandardError, e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root, True)
                    except StandardError, e:
                        raise ValueError('Unable to configure root '
                                         'logger: %s' % e)
            else:
                disable_existing = config.pop('disable_existing_loggers', True)
                
                logging._handlers.clear()
                del logging._handlerList[:]
                    
                # Do formatters first - they don't refer to anything else
                formatters = config.get('formatters', EMPTY_DICT)
                for name in formatters:
                    try:
                        formatters[name] = self.configure_formatter(
                                                            formatters[name])
                    except StandardError, e:
                        raise ValueError('Unable to configure '
                                         'formatter %r: %s' % (name, e))
                # Next, do filters - they don't refer to anything else, either
                filters = config.get('filters', EMPTY_DICT)
                for name in filters:
                    try:
                        filters[name] = self.configure_filter(filters[name])
                    except StandardError, e:
                        raise ValueError('Unable to configure '
                                         'filter %r: %s' % (name, e))

                # Next, do handlers - they refer to formatters and filters
                # As handlers can refer to other handlers, sort the keys
                # to allow a deterministic order of configuration
                handlers = config.get('handlers', EMPTY_DICT)
                for name in sorted(handlers):
                    try:
                        handler = self.configure_handler(handlers[name])
                        handler.name = name
                        handlers[name] = handler
                    except StandardError, e:
                        raise ValueError('Unable to configure handler '
                                         '%r: %s' % (name, e))
                # Next, do loggers - they refer to handlers and filters
                
                #we don't want to lose the existing loggers,
                #since other threads may have pointers to them.
                #existing is set to contain all existing loggers,
                #and as we go through the new configuration we
                #remove any which are configured. At the end,
                #what's left in existing is the set of loggers
                #which were in the previous configuration but
                #which are not in the new configuration.
                root = logging.root
                existing = root.manager.loggerDict.keys()
                #The list needs to be sorted so that we can
                #avoid disabling child loggers of explicitly
                #named loggers. With a sorted list it is easier
                #to find the child loggers.
                existing.sort()
                #We'll keep the list of existing loggers
                #which are children of named loggers here...
                child_loggers = []
                #now set up the new ones...
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    if name in existing:
                        i = existing.index(name)
                        prefixed = name + "."
                        pflen = len(prefixed)
                        num_existing = len(existing)
                        i = i + 1 # look at the entry after name
                        while (i < num_existing) and\
                              (existing[i][:pflen] == prefixed):
                            child_loggers.append(existing[i])
                            i = i + 1
                        existing.remove(name)
                    try:
                        self.configure_logger(name, loggers[name])
                    except StandardError, e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))
                    
                #Disable any old loggers. There's no point deleting
                #them as other threads may continue to hold references
                #and by disabling them, you stop them doing any logging.
                #However, don't disable children of named loggers, as that's
                #probably not what was intended by the user.
                for log in existing:
                    logger = root.manager.loggerDict[log]
                    if log in child_loggers:
                        logger.level = logging.NOTSET
                        logger.handlers = []
                        logger.propagate = True
                    elif disable_existing:
                        logger.disabled = True
    
                # And finally, do the root logger
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root)                        
                    except StandardError, e:
                        raise ValueError('Unable to configure root '
                                         'logger: %s' % e)
        finally:
            logging._releaseLock()

    def configure_formatter(self, config):
        """Configure a formatter from a dictionary."""
        if '()' in config:
            factory = config['()'] # for use in exception handler
            try:
                result = self.configure_custom(config)
            except TypeError, te:
                if "'format'" not in str(te):
                    raise
                #Name of parameter changed from fmt to format.
                #Retry with old name.
                #This is so that code can be used with older Python versions
                #(e.g. by Django)
                config['fmt'] = config.pop('format')
                config['()'] = factory
                result = self.configure_custom(config)
        else:
            fmt = config.get('format', None)
            dfmt = config.get('datefmt', None)
            result = logging.Formatter(fmt, dfmt)
        return result
    
    def configure_filter(self, config):
        """Configure a filter from a dictionary."""
        if '()' in config:
            result = self.configure_custom(config)
        else:
            name = config.get('name', '')
            result = logging.Filter(name)
        return result

    def add_filters(self, filterer, filters):
        """Add filters to a filterer from a list of names."""
        for f in filters:
            try:
                filterer.addFilter(self.config['filters'][f])
            except StandardError, e:
                raise ValueError('Unable to add filter %r: %s' % (f, e))

    def configure_handler(self, config):
        """Configure a handler from a dictionary."""
        formatter = config.pop('formatter', None)
        if formatter:
            try:
                formatter = self.config['formatters'][formatter]
            except StandardError, e:
                raise ValueError('Unable to set formatter '
                                 '%r: %s' % (formatter, e))
        level = config.pop('level', None)
        filters = config.pop('filters', None)
        if '()' in config:
            c = config.pop('()')
            if not hasattr(c, '__call__') and hasattr(types, 'ClassType') and type(c) != types.ClassType:
                c = self.resolve(c)
            factory = c
        else:
            klass = self.resolve(config.pop('class'))
            #Special case for handler which refers to another handler
            if issubclass(klass, logging.handlers.MemoryHandler) and\
                'target' in config:
                try:
                    config['target'] = self.config['handlers'][config['target']]
                except StandardError, e:
                    raise ValueError('Unable to set target handler '
                                     '%r: %s' % (config['target'], e))
            elif issubclass(klass, logging.handlers.SMTPHandler) and\
                'mailhost' in config:
                config['mailhost'] = self.as_tuple(config['mailhost'])
            elif issubclass(klass, logging.handlers.SysLogHandler) and\
                'address' in config:
                config['address'] = self.as_tuple(config['address'])
            factory = klass
        kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
        try:
            result = factory(**kwargs)
        except TypeError, te:
            if "'stream'" not in str(te):
                raise
            #The argument name changed from strm to stream
            #Retry with old name.
            #This is so that code can be used with older Python versions
            #(e.g. by Django)
            kwargs['strm'] = kwargs.pop('stream')
            result = factory(**kwargs)
        if formatter:
            result.setFormatter(formatter)
        if level is not None:
            result.setLevel(_checkLevel(level))
        if filters:
            self.add_filters(result, filters)
        return result

    def add_handlers(self, logger, handlers):
        """Add handlers to a logger from a list of names."""
        for h in handlers:
            try:
                logger.addHandler(self.config['handlers'][h])
            except StandardError, e:
                raise ValueError('Unable to add handler %r: %s' % (h, e))

    def common_logger_config(self, logger, config, incremental=False):
        """
        Perform configuration which is common to root and non-root loggers.
        """
        level = config.get('level', None)
        if level is not None:
            logger.setLevel(_checkLevel(level))
        if not incremental:
            #Remove any existing handlers
            for h in logger.handlers[:]:
                logger.removeHandler(h)
            handlers = config.get('handlers', None)
            if handlers:
                self.add_handlers(logger, handlers)
            filters = config.get('filters', None)
            if filters:
                self.add_filters(logger, filters)
        
    def configure_logger(self, name, config, incremental=False):
        """Configure a non-root logger from a dictionary."""
        logger = logging.getLogger(name)
        self.common_logger_config(logger, config, incremental)
        propagate = config.get('propagate', None)
        if propagate is not None:
            logger.propagate = propagate
            
    def configure_root(self, config, incremental=False):
        """Configure a root logger from a dictionary."""
        root = logging.getLogger()
        self.common_logger_config(root, config, incremental)

dictConfigClass = DictConfigurator

def dictConfig(config):
    """Configure logging using a dictionary."""
    dictConfigClass(config).configure()

########NEW FILE########
__FILENAME__ = constants
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *
from ttypes import *


########NEW FILE########
__FILENAME__ = Hbase
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *
from ttypes import *
from thrift.Thrift import TProcessor
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None


class Iface:
  def enableTable(self, tableName):
    """
    Brings a table on-line (enables it)

    Parameters:
     - tableName: name of the table
    """
    pass

  def disableTable(self, tableName):
    """
    Disables a table (takes it off-line) If it is being served, the master
    will tell the servers to stop serving it.

    Parameters:
     - tableName: name of the table
    """
    pass

  def isTableEnabled(self, tableName):
    """
    @return true if table is on-line

    Parameters:
     - tableName: name of the table to check
    """
    pass

  def compact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    pass

  def majorCompact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    pass

  def getTableNames(self, ):
    """
    List all the userspace tables.

    @return returns a list of names
    """
    pass

  def getColumnDescriptors(self, tableName):
    """
    List all the column families assoicated with a table.

    @return list of column family descriptors

    Parameters:
     - tableName: table name
    """
    pass

  def getTableRegions(self, tableName):
    """
    List the regions associated with a table.

    @return list of region descriptors

    Parameters:
     - tableName: table name
    """
    pass

  def createTable(self, tableName, columnFamilies):
    """
    Create a table with the specified column families.  The name
    field for each ColumnDescriptor must be set and must end in a
    colon (:). All other fields are optional and will get default
    values if not explicitly specified.

    @throws IllegalArgument if an input parameter is invalid

    @throws AlreadyExists if the table name already exists

    Parameters:
     - tableName: name of table to create
     - columnFamilies: list of column family descriptors
    """
    pass

  def deleteTable(self, tableName):
    """
    Deletes a table

    @throws IOError if table doesn't exist on server or there was some other
    problem

    Parameters:
     - tableName: name of table to delete
    """
    pass

  def get(self, tableName, row, column):
    """
    Get a single TCell for the specified table, row, and column at the
    latest timestamp. Returns an empty list if no such value exists.

    @return value for specified row/column

    Parameters:
     - tableName: name of table
     - row: row key
     - column: column name
    """
    pass

  def getVer(self, tableName, row, column, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.

    @return list of cells for specified row/column

    Parameters:
     - tableName: name of table
     - row: row key
     - column: column name
     - numVersions: number of versions to retrieve
    """
    pass

  def getVerTs(self, tableName, row, column, timestamp, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.  Only versions less than or equal to the specified
    timestamp will be returned.

    @return list of cells for specified row/column

    Parameters:
     - tableName: name of table
     - row: row key
     - column: column name
     - timestamp: timestamp
     - numVersions: number of versions to retrieve
    """
    pass

  def getRow(self, tableName, row):
    """
    Get all the data for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of table
     - row: row key
    """
    pass

  def getRowWithColumns(self, tableName, row, columns):
    """
    Get the specified columns for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of table
     - row: row key
     - columns: List of columns to return, null for all columns
    """
    pass

  def getRowTs(self, tableName, row, timestamp):
    """
    Get all the data for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of the table
     - row: row key
     - timestamp: timestamp
    """
    pass

  def getRowWithColumnsTs(self, tableName, row, columns, timestamp):
    """
    Get the specified columns for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of table
     - row: row key
     - columns: List of columns to return, null for all columns
     - timestamp
    """
    pass

  def mutateRow(self, tableName, row, mutations):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - row: row key
     - mutations: list of mutation commands
    """
    pass

  def mutateRowTs(self, tableName, row, mutations, timestamp):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - row: row key
     - mutations: list of mutation commands
     - timestamp: timestamp
    """
    pass

  def mutateRows(self, tableName, rowBatches):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - rowBatches: list of row batches
    """
    pass

  def mutateRowsTs(self, tableName, rowBatches, timestamp):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - rowBatches: list of row batches
     - timestamp: timestamp
    """
    pass

  def atomicIncrement(self, tableName, row, column, value):
    """
    Atomically increment the column value specified.  Returns the next value post increment.

    Parameters:
     - tableName: name of table
     - row: row to increment
     - column: name of column
     - value: amount to increment by
    """
    pass

  def deleteAll(self, tableName, row, column):
    """
    Delete all cells that match the passed row and column.

    Parameters:
     - tableName: name of table
     - row: Row to update
     - column: name of column whose value is to be deleted
    """
    pass

  def deleteAllTs(self, tableName, row, column, timestamp):
    """
    Delete all cells that match the passed row and column and whose
    timestamp is equal-to or older than the passed timestamp.

    Parameters:
     - tableName: name of table
     - row: Row to update
     - column: name of column whose value is to be deleted
     - timestamp: timestamp
    """
    pass

  def deleteAllRow(self, tableName, row):
    """
    Completely delete the row's cells.

    Parameters:
     - tableName: name of table
     - row: key of the row to be completely deleted.
    """
    pass

  def deleteAllRowTs(self, tableName, row, timestamp):
    """
    Completely delete the row's cells marked with a timestamp
    equal-to or older than the passed timestamp.

    Parameters:
     - tableName: name of table
     - row: key of the row to be completely deleted.
     - timestamp: timestamp
    """
    pass

  def scannerOpen(self, tableName, startRow, columns):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
    """
    pass

  def scannerOpenWithStop(self, tableName, startRow, stopRow, columns):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - stopRow: row to stop scanning on. This row is *not* included in the
    scanner's results
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
    """
    pass

  def scannerOpenWithPrefix(self, tableName, startAndPrefix, columns):
    """
    Open a scanner for a given prefix.  That is all rows will have the specified
    prefix. No other rows will be returned.

    @return scanner id to use with other scanner calls

    Parameters:
     - tableName: name of table
     - startAndPrefix: the prefix (and thus start row) of the keys you want
     - columns: the columns you want returned
    """
    pass

  def scannerOpenTs(self, tableName, startRow, columns, timestamp):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.
    Only values with the specified timestamp are returned.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
     - timestamp: timestamp
    """
    pass

  def scannerOpenWithStopTs(self, tableName, startRow, stopRow, columns, timestamp):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.  Only values with the specified timestamp are
    returned.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - stopRow: row to stop scanning on. This row is *not* included in the
    scanner's results
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
     - timestamp: timestamp
    """
    pass

  def scannerGet(self, id):
    """
    Returns the scanner's current row value and advances to the next
    row in the table.  When there are no more rows in the table, or a key
    greater-than-or-equal-to the scanner's specified stopRow is reached,
    an empty list is returned.

    @return a TRowResult containing the current row and a map of the columns to TCells.

    @throws IllegalArgument if ScannerID is invalid

    @throws NotFound when the scanner reaches the end

    Parameters:
     - id: id of a scanner returned by scannerOpen
    """
    pass

  def scannerGetList(self, id, nbRows):
    """
    Returns, starting at the scanner's current row value nbRows worth of
    rows and advances to the next row in the table.  When there are no more
    rows in the table, or a key greater-than-or-equal-to the scanner's
    specified stopRow is reached,  an empty list is returned.

    @return a TRowResult containing the current row and a map of the columns to TCells.

    @throws IllegalArgument if ScannerID is invalid

    @throws NotFound when the scanner reaches the end

    Parameters:
     - id: id of a scanner returned by scannerOpen
     - nbRows: number of results to return
    """
    pass

  def scannerClose(self, id):
    """
    Closes the server-state associated with an open scanner.

    @throws IllegalArgument if ScannerID is invalid

    Parameters:
     - id: id of a scanner returned by scannerOpen
    """
    pass


class Client(Iface):
  def __init__(self, iprot, oprot=None):
    self._iprot = self._oprot = iprot
    if oprot != None:
      self._oprot = oprot
    self._seqid = 0

  def enableTable(self, tableName):
    """
    Brings a table on-line (enables it)

    Parameters:
     - tableName: name of the table
    """
    self.send_enableTable(tableName)
    self.recv_enableTable()

  def send_enableTable(self, tableName):
    self._oprot.writeMessageBegin('enableTable', TMessageType.CALL, self._seqid)
    args = enableTable_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_enableTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = enableTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def disableTable(self, tableName):
    """
    Disables a table (takes it off-line) If it is being served, the master
    will tell the servers to stop serving it.

    Parameters:
     - tableName: name of the table
    """
    self.send_disableTable(tableName)
    self.recv_disableTable()

  def send_disableTable(self, tableName):
    self._oprot.writeMessageBegin('disableTable', TMessageType.CALL, self._seqid)
    args = disableTable_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_disableTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = disableTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def isTableEnabled(self, tableName):
    """
    @return true if table is on-line

    Parameters:
     - tableName: name of the table to check
    """
    self.send_isTableEnabled(tableName)
    return self.recv_isTableEnabled()

  def send_isTableEnabled(self, tableName):
    self._oprot.writeMessageBegin('isTableEnabled', TMessageType.CALL, self._seqid)
    args = isTableEnabled_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_isTableEnabled(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = isTableEnabled_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "isTableEnabled failed: unknown result");

  def compact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    self.send_compact(tableNameOrRegionName)
    self.recv_compact()

  def send_compact(self, tableNameOrRegionName):
    self._oprot.writeMessageBegin('compact', TMessageType.CALL, self._seqid)
    args = compact_args()
    args.tableNameOrRegionName = tableNameOrRegionName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_compact(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = compact_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def majorCompact(self, tableNameOrRegionName):
    """
    Parameters:
     - tableNameOrRegionName
    """
    self.send_majorCompact(tableNameOrRegionName)
    self.recv_majorCompact()

  def send_majorCompact(self, tableNameOrRegionName):
    self._oprot.writeMessageBegin('majorCompact', TMessageType.CALL, self._seqid)
    args = majorCompact_args()
    args.tableNameOrRegionName = tableNameOrRegionName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_majorCompact(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = majorCompact_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def getTableNames(self, ):
    """
    List all the userspace tables.

    @return returns a list of names
    """
    self.send_getTableNames()
    return self.recv_getTableNames()

  def send_getTableNames(self, ):
    self._oprot.writeMessageBegin('getTableNames', TMessageType.CALL, self._seqid)
    args = getTableNames_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getTableNames(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getTableNames_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getTableNames failed: unknown result");

  def getColumnDescriptors(self, tableName):
    """
    List all the column families assoicated with a table.

    @return list of column family descriptors

    Parameters:
     - tableName: table name
    """
    self.send_getColumnDescriptors(tableName)
    return self.recv_getColumnDescriptors()

  def send_getColumnDescriptors(self, tableName):
    self._oprot.writeMessageBegin('getColumnDescriptors', TMessageType.CALL, self._seqid)
    args = getColumnDescriptors_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getColumnDescriptors(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getColumnDescriptors_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getColumnDescriptors failed: unknown result");

  def getTableRegions(self, tableName):
    """
    List the regions associated with a table.

    @return list of region descriptors

    Parameters:
     - tableName: table name
    """
    self.send_getTableRegions(tableName)
    return self.recv_getTableRegions()

  def send_getTableRegions(self, tableName):
    self._oprot.writeMessageBegin('getTableRegions', TMessageType.CALL, self._seqid)
    args = getTableRegions_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getTableRegions(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getTableRegions_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getTableRegions failed: unknown result");

  def createTable(self, tableName, columnFamilies):
    """
    Create a table with the specified column families.  The name
    field for each ColumnDescriptor must be set and must end in a
    colon (:). All other fields are optional and will get default
    values if not explicitly specified.

    @throws IllegalArgument if an input parameter is invalid

    @throws AlreadyExists if the table name already exists

    Parameters:
     - tableName: name of table to create
     - columnFamilies: list of column family descriptors
    """
    self.send_createTable(tableName, columnFamilies)
    self.recv_createTable()

  def send_createTable(self, tableName, columnFamilies):
    self._oprot.writeMessageBegin('createTable', TMessageType.CALL, self._seqid)
    args = createTable_args()
    args.tableName = tableName
    args.columnFamilies = columnFamilies
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_createTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = createTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    if result.exist != None:
      raise result.exist
    return

  def deleteTable(self, tableName):
    """
    Deletes a table

    @throws IOError if table doesn't exist on server or there was some other
    problem

    Parameters:
     - tableName: name of table to delete
    """
    self.send_deleteTable(tableName)
    self.recv_deleteTable()

  def send_deleteTable(self, tableName):
    self._oprot.writeMessageBegin('deleteTable', TMessageType.CALL, self._seqid)
    args = deleteTable_args()
    args.tableName = tableName
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteTable(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteTable_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def get(self, tableName, row, column):
    """
    Get a single TCell for the specified table, row, and column at the
    latest timestamp. Returns an empty list if no such value exists.

    @return value for specified row/column

    Parameters:
     - tableName: name of table
     - row: row key
     - column: column name
    """
    self.send_get(tableName, row, column)
    return self.recv_get()

  def send_get(self, tableName, row, column):
    self._oprot.writeMessageBegin('get', TMessageType.CALL, self._seqid)
    args = get_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get failed: unknown result");

  def getVer(self, tableName, row, column, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.

    @return list of cells for specified row/column

    Parameters:
     - tableName: name of table
     - row: row key
     - column: column name
     - numVersions: number of versions to retrieve
    """
    self.send_getVer(tableName, row, column, numVersions)
    return self.recv_getVer()

  def send_getVer(self, tableName, row, column, numVersions):
    self._oprot.writeMessageBegin('getVer', TMessageType.CALL, self._seqid)
    args = getVer_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.numVersions = numVersions
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getVer(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getVer_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getVer failed: unknown result");

  def getVerTs(self, tableName, row, column, timestamp, numVersions):
    """
    Get the specified number of versions for the specified table,
    row, and column.  Only versions less than or equal to the specified
    timestamp will be returned.

    @return list of cells for specified row/column

    Parameters:
     - tableName: name of table
     - row: row key
     - column: column name
     - timestamp: timestamp
     - numVersions: number of versions to retrieve
    """
    self.send_getVerTs(tableName, row, column, timestamp, numVersions)
    return self.recv_getVerTs()

  def send_getVerTs(self, tableName, row, column, timestamp, numVersions):
    self._oprot.writeMessageBegin('getVerTs', TMessageType.CALL, self._seqid)
    args = getVerTs_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.timestamp = timestamp
    args.numVersions = numVersions
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getVerTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getVerTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getVerTs failed: unknown result");

  def getRow(self, tableName, row):
    """
    Get all the data for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of table
     - row: row key
    """
    self.send_getRow(tableName, row)
    return self.recv_getRow()

  def send_getRow(self, tableName, row):
    self._oprot.writeMessageBegin('getRow', TMessageType.CALL, self._seqid)
    args = getRow_args()
    args.tableName = tableName
    args.row = row
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRow(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRow_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRow failed: unknown result");

  def getRowWithColumns(self, tableName, row, columns):
    """
    Get the specified columns for the specified table and row at the latest
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of table
     - row: row key
     - columns: List of columns to return, null for all columns
    """
    self.send_getRowWithColumns(tableName, row, columns)
    return self.recv_getRowWithColumns()

  def send_getRowWithColumns(self, tableName, row, columns):
    self._oprot.writeMessageBegin('getRowWithColumns', TMessageType.CALL, self._seqid)
    args = getRowWithColumns_args()
    args.tableName = tableName
    args.row = row
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRowWithColumns(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRowWithColumns_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRowWithColumns failed: unknown result");

  def getRowTs(self, tableName, row, timestamp):
    """
    Get all the data for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of the table
     - row: row key
     - timestamp: timestamp
    """
    self.send_getRowTs(tableName, row, timestamp)
    return self.recv_getRowTs()

  def send_getRowTs(self, tableName, row, timestamp):
    self._oprot.writeMessageBegin('getRowTs', TMessageType.CALL, self._seqid)
    args = getRowTs_args()
    args.tableName = tableName
    args.row = row
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRowTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRowTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRowTs failed: unknown result");

  def getRowWithColumnsTs(self, tableName, row, columns, timestamp):
    """
    Get the specified columns for the specified table and row at the specified
    timestamp. Returns an empty list if the row does not exist.

    @return TRowResult containing the row and map of columns to TCells

    Parameters:
     - tableName: name of table
     - row: row key
     - columns: List of columns to return, null for all columns
     - timestamp
    """
    self.send_getRowWithColumnsTs(tableName, row, columns, timestamp)
    return self.recv_getRowWithColumnsTs()

  def send_getRowWithColumnsTs(self, tableName, row, columns, timestamp):
    self._oprot.writeMessageBegin('getRowWithColumnsTs', TMessageType.CALL, self._seqid)
    args = getRowWithColumnsTs_args()
    args.tableName = tableName
    args.row = row
    args.columns = columns
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_getRowWithColumnsTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = getRowWithColumnsTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "getRowWithColumnsTs failed: unknown result");

  def mutateRow(self, tableName, row, mutations):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - row: row key
     - mutations: list of mutation commands
    """
    self.send_mutateRow(tableName, row, mutations)
    self.recv_mutateRow()

  def send_mutateRow(self, tableName, row, mutations):
    self._oprot.writeMessageBegin('mutateRow', TMessageType.CALL, self._seqid)
    args = mutateRow_args()
    args.tableName = tableName
    args.row = row
    args.mutations = mutations
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRow(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRow_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def mutateRowTs(self, tableName, row, mutations, timestamp):
    """
    Apply a series of mutations (updates/deletes) to a row in a
    single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - row: row key
     - mutations: list of mutation commands
     - timestamp: timestamp
    """
    self.send_mutateRowTs(tableName, row, mutations, timestamp)
    self.recv_mutateRowTs()

  def send_mutateRowTs(self, tableName, row, mutations, timestamp):
    self._oprot.writeMessageBegin('mutateRowTs', TMessageType.CALL, self._seqid)
    args = mutateRowTs_args()
    args.tableName = tableName
    args.row = row
    args.mutations = mutations
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRowTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRowTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def mutateRows(self, tableName, rowBatches):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  Default current timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - rowBatches: list of row batches
    """
    self.send_mutateRows(tableName, rowBatches)
    self.recv_mutateRows()

  def send_mutateRows(self, tableName, rowBatches):
    self._oprot.writeMessageBegin('mutateRows', TMessageType.CALL, self._seqid)
    args = mutateRows_args()
    args.tableName = tableName
    args.rowBatches = rowBatches
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRows(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRows_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def mutateRowsTs(self, tableName, rowBatches, timestamp):
    """
    Apply a series of batches (each a series of mutations on a single row)
    in a single transaction.  If an exception is thrown, then the
    transaction is aborted.  The specified timestamp is used, and
    all entries will have an identical timestamp.

    Parameters:
     - tableName: name of table
     - rowBatches: list of row batches
     - timestamp: timestamp
    """
    self.send_mutateRowsTs(tableName, rowBatches, timestamp)
    self.recv_mutateRowsTs()

  def send_mutateRowsTs(self, tableName, rowBatches, timestamp):
    self._oprot.writeMessageBegin('mutateRowsTs', TMessageType.CALL, self._seqid)
    args = mutateRowsTs_args()
    args.tableName = tableName
    args.rowBatches = rowBatches
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_mutateRowsTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = mutateRowsTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return

  def atomicIncrement(self, tableName, row, column, value):
    """
    Atomically increment the column value specified.  Returns the next value post increment.

    Parameters:
     - tableName: name of table
     - row: row to increment
     - column: name of column
     - value: amount to increment by
    """
    self.send_atomicIncrement(tableName, row, column, value)
    return self.recv_atomicIncrement()

  def send_atomicIncrement(self, tableName, row, column, value):
    self._oprot.writeMessageBegin('atomicIncrement', TMessageType.CALL, self._seqid)
    args = atomicIncrement_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.value = value
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_atomicIncrement(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = atomicIncrement_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    raise TApplicationException(TApplicationException.MISSING_RESULT, "atomicIncrement failed: unknown result");

  def deleteAll(self, tableName, row, column):
    """
    Delete all cells that match the passed row and column.

    Parameters:
     - tableName: name of table
     - row: Row to update
     - column: name of column whose value is to be deleted
    """
    self.send_deleteAll(tableName, row, column)
    self.recv_deleteAll()

  def send_deleteAll(self, tableName, row, column):
    self._oprot.writeMessageBegin('deleteAll', TMessageType.CALL, self._seqid)
    args = deleteAll_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAll(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAll_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def deleteAllTs(self, tableName, row, column, timestamp):
    """
    Delete all cells that match the passed row and column and whose
    timestamp is equal-to or older than the passed timestamp.

    Parameters:
     - tableName: name of table
     - row: Row to update
     - column: name of column whose value is to be deleted
     - timestamp: timestamp
    """
    self.send_deleteAllTs(tableName, row, column, timestamp)
    self.recv_deleteAllTs()

  def send_deleteAllTs(self, tableName, row, column, timestamp):
    self._oprot.writeMessageBegin('deleteAllTs', TMessageType.CALL, self._seqid)
    args = deleteAllTs_args()
    args.tableName = tableName
    args.row = row
    args.column = column
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAllTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAllTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def deleteAllRow(self, tableName, row):
    """
    Completely delete the row's cells.

    Parameters:
     - tableName: name of table
     - row: key of the row to be completely deleted.
    """
    self.send_deleteAllRow(tableName, row)
    self.recv_deleteAllRow()

  def send_deleteAllRow(self, tableName, row):
    self._oprot.writeMessageBegin('deleteAllRow', TMessageType.CALL, self._seqid)
    args = deleteAllRow_args()
    args.tableName = tableName
    args.row = row
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAllRow(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAllRow_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def deleteAllRowTs(self, tableName, row, timestamp):
    """
    Completely delete the row's cells marked with a timestamp
    equal-to or older than the passed timestamp.

    Parameters:
     - tableName: name of table
     - row: key of the row to be completely deleted.
     - timestamp: timestamp
    """
    self.send_deleteAllRowTs(tableName, row, timestamp)
    self.recv_deleteAllRowTs()

  def send_deleteAllRowTs(self, tableName, row, timestamp):
    self._oprot.writeMessageBegin('deleteAllRowTs', TMessageType.CALL, self._seqid)
    args = deleteAllRowTs_args()
    args.tableName = tableName
    args.row = row
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_deleteAllRowTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = deleteAllRowTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    return

  def scannerOpen(self, tableName, startRow, columns):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
    """
    self.send_scannerOpen(tableName, startRow, columns)
    return self.recv_scannerOpen()

  def send_scannerOpen(self, tableName, startRow, columns):
    self._oprot.writeMessageBegin('scannerOpen', TMessageType.CALL, self._seqid)
    args = scannerOpen_args()
    args.tableName = tableName
    args.startRow = startRow
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpen(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpen_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpen failed: unknown result");

  def scannerOpenWithStop(self, tableName, startRow, stopRow, columns):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - stopRow: row to stop scanning on. This row is *not* included in the
    scanner's results
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
    """
    self.send_scannerOpenWithStop(tableName, startRow, stopRow, columns)
    return self.recv_scannerOpenWithStop()

  def send_scannerOpenWithStop(self, tableName, startRow, stopRow, columns):
    self._oprot.writeMessageBegin('scannerOpenWithStop', TMessageType.CALL, self._seqid)
    args = scannerOpenWithStop_args()
    args.tableName = tableName
    args.startRow = startRow
    args.stopRow = stopRow
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenWithStop(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenWithStop_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenWithStop failed: unknown result");

  def scannerOpenWithPrefix(self, tableName, startAndPrefix, columns):
    """
    Open a scanner for a given prefix.  That is all rows will have the specified
    prefix. No other rows will be returned.

    @return scanner id to use with other scanner calls

    Parameters:
     - tableName: name of table
     - startAndPrefix: the prefix (and thus start row) of the keys you want
     - columns: the columns you want returned
    """
    self.send_scannerOpenWithPrefix(tableName, startAndPrefix, columns)
    return self.recv_scannerOpenWithPrefix()

  def send_scannerOpenWithPrefix(self, tableName, startAndPrefix, columns):
    self._oprot.writeMessageBegin('scannerOpenWithPrefix', TMessageType.CALL, self._seqid)
    args = scannerOpenWithPrefix_args()
    args.tableName = tableName
    args.startAndPrefix = startAndPrefix
    args.columns = columns
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenWithPrefix(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenWithPrefix_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenWithPrefix failed: unknown result");

  def scannerOpenTs(self, tableName, startRow, columns, timestamp):
    """
    Get a scanner on the current table starting at the specified row and
    ending at the last row in the table.  Return the specified columns.
    Only values with the specified timestamp are returned.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
     - timestamp: timestamp
    """
    self.send_scannerOpenTs(tableName, startRow, columns, timestamp)
    return self.recv_scannerOpenTs()

  def send_scannerOpenTs(self, tableName, startRow, columns, timestamp):
    self._oprot.writeMessageBegin('scannerOpenTs', TMessageType.CALL, self._seqid)
    args = scannerOpenTs_args()
    args.tableName = tableName
    args.startRow = startRow
    args.columns = columns
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenTs failed: unknown result");

  def scannerOpenWithStopTs(self, tableName, startRow, stopRow, columns, timestamp):
    """
    Get a scanner on the current table starting and stopping at the
    specified rows.  ending at the last row in the table.  Return the
    specified columns.  Only values with the specified timestamp are
    returned.

    @return scanner id to be used with other scanner procedures

    Parameters:
     - tableName: name of table
     - startRow: Starting row in table to scan.
    Send "" (empty string) to start at the first row.
     - stopRow: row to stop scanning on. This row is *not* included in the
    scanner's results
     - columns: columns to scan. If column name is a column family, all
    columns of the specified column family are returned. It's also possible
    to pass a regex in the column qualifier.
     - timestamp: timestamp
    """
    self.send_scannerOpenWithStopTs(tableName, startRow, stopRow, columns, timestamp)
    return self.recv_scannerOpenWithStopTs()

  def send_scannerOpenWithStopTs(self, tableName, startRow, stopRow, columns, timestamp):
    self._oprot.writeMessageBegin('scannerOpenWithStopTs', TMessageType.CALL, self._seqid)
    args = scannerOpenWithStopTs_args()
    args.tableName = tableName
    args.startRow = startRow
    args.stopRow = stopRow
    args.columns = columns
    args.timestamp = timestamp
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerOpenWithStopTs(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerOpenWithStopTs_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerOpenWithStopTs failed: unknown result");

  def scannerGet(self, id):
    """
    Returns the scanner's current row value and advances to the next
    row in the table.  When there are no more rows in the table, or a key
    greater-than-or-equal-to the scanner's specified stopRow is reached,
    an empty list is returned.

    @return a TRowResult containing the current row and a map of the columns to TCells.

    @throws IllegalArgument if ScannerID is invalid

    @throws NotFound when the scanner reaches the end

    Parameters:
     - id: id of a scanner returned by scannerOpen
    """
    self.send_scannerGet(id)
    return self.recv_scannerGet()

  def send_scannerGet(self, id):
    self._oprot.writeMessageBegin('scannerGet', TMessageType.CALL, self._seqid)
    args = scannerGet_args()
    args.id = id
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerGet(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerGet_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerGet failed: unknown result");

  def scannerGetList(self, id, nbRows):
    """
    Returns, starting at the scanner's current row value nbRows worth of
    rows and advances to the next row in the table.  When there are no more
    rows in the table, or a key greater-than-or-equal-to the scanner's
    specified stopRow is reached,  an empty list is returned.

    @return a TRowResult containing the current row and a map of the columns to TCells.

    @throws IllegalArgument if ScannerID is invalid

    @throws NotFound when the scanner reaches the end

    Parameters:
     - id: id of a scanner returned by scannerOpen
     - nbRows: number of results to return
    """
    self.send_scannerGetList(id, nbRows)
    return self.recv_scannerGetList()

  def send_scannerGetList(self, id, nbRows):
    self._oprot.writeMessageBegin('scannerGetList', TMessageType.CALL, self._seqid)
    args = scannerGetList_args()
    args.id = id
    args.nbRows = nbRows
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerGetList(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerGetList_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success != None:
      return result.success
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    raise TApplicationException(TApplicationException.MISSING_RESULT, "scannerGetList failed: unknown result");

  def scannerClose(self, id):
    """
    Closes the server-state associated with an open scanner.

    @throws IllegalArgument if ScannerID is invalid

    Parameters:
     - id: id of a scanner returned by scannerOpen
    """
    self.send_scannerClose(id)
    self.recv_scannerClose()

  def send_scannerClose(self, id):
    self._oprot.writeMessageBegin('scannerClose', TMessageType.CALL, self._seqid)
    args = scannerClose_args()
    args.id = id
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_scannerClose(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = scannerClose_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.io != None:
      raise result.io
    if result.ia != None:
      raise result.ia
    return


class Processor(Iface, TProcessor):
  def __init__(self, handler):
    self._handler = handler
    self._processMap = {}
    self._processMap["enableTable"] = Processor.process_enableTable
    self._processMap["disableTable"] = Processor.process_disableTable
    self._processMap["isTableEnabled"] = Processor.process_isTableEnabled
    self._processMap["compact"] = Processor.process_compact
    self._processMap["majorCompact"] = Processor.process_majorCompact
    self._processMap["getTableNames"] = Processor.process_getTableNames
    self._processMap["getColumnDescriptors"] = Processor.process_getColumnDescriptors
    self._processMap["getTableRegions"] = Processor.process_getTableRegions
    self._processMap["createTable"] = Processor.process_createTable
    self._processMap["deleteTable"] = Processor.process_deleteTable
    self._processMap["get"] = Processor.process_get
    self._processMap["getVer"] = Processor.process_getVer
    self._processMap["getVerTs"] = Processor.process_getVerTs
    self._processMap["getRow"] = Processor.process_getRow
    self._processMap["getRowWithColumns"] = Processor.process_getRowWithColumns
    self._processMap["getRowTs"] = Processor.process_getRowTs
    self._processMap["getRowWithColumnsTs"] = Processor.process_getRowWithColumnsTs
    self._processMap["mutateRow"] = Processor.process_mutateRow
    self._processMap["mutateRowTs"] = Processor.process_mutateRowTs
    self._processMap["mutateRows"] = Processor.process_mutateRows
    self._processMap["mutateRowsTs"] = Processor.process_mutateRowsTs
    self._processMap["atomicIncrement"] = Processor.process_atomicIncrement
    self._processMap["deleteAll"] = Processor.process_deleteAll
    self._processMap["deleteAllTs"] = Processor.process_deleteAllTs
    self._processMap["deleteAllRow"] = Processor.process_deleteAllRow
    self._processMap["deleteAllRowTs"] = Processor.process_deleteAllRowTs
    self._processMap["scannerOpen"] = Processor.process_scannerOpen
    self._processMap["scannerOpenWithStop"] = Processor.process_scannerOpenWithStop
    self._processMap["scannerOpenWithPrefix"] = Processor.process_scannerOpenWithPrefix
    self._processMap["scannerOpenTs"] = Processor.process_scannerOpenTs
    self._processMap["scannerOpenWithStopTs"] = Processor.process_scannerOpenWithStopTs
    self._processMap["scannerGet"] = Processor.process_scannerGet
    self._processMap["scannerGetList"] = Processor.process_scannerGetList
    self._processMap["scannerClose"] = Processor.process_scannerClose

  def process(self, iprot, oprot):
    (name, type, seqid) = iprot.readMessageBegin()
    if name not in self._processMap:
      iprot.skip(TType.STRUCT)
      iprot.readMessageEnd()
      x = TApplicationException(TApplicationException.UNKNOWN_METHOD, 'Unknown function %s' % (name))
      oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
      x.write(oprot)
      oprot.writeMessageEnd()
      oprot.trans.flush()
      return
    else:
      self._processMap[name](self, seqid, iprot, oprot)
    return True

  def process_enableTable(self, seqid, iprot, oprot):
    args = enableTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = enableTable_result()
    try:
      self._handler.enableTable(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("enableTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_disableTable(self, seqid, iprot, oprot):
    args = disableTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = disableTable_result()
    try:
      self._handler.disableTable(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("disableTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_isTableEnabled(self, seqid, iprot, oprot):
    args = isTableEnabled_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = isTableEnabled_result()
    try:
      result.success = self._handler.isTableEnabled(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("isTableEnabled", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_compact(self, seqid, iprot, oprot):
    args = compact_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = compact_result()
    try:
      self._handler.compact(args.tableNameOrRegionName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("compact", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_majorCompact(self, seqid, iprot, oprot):
    args = majorCompact_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = majorCompact_result()
    try:
      self._handler.majorCompact(args.tableNameOrRegionName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("majorCompact", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getTableNames(self, seqid, iprot, oprot):
    args = getTableNames_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getTableNames_result()
    try:
      result.success = self._handler.getTableNames()
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getTableNames", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getColumnDescriptors(self, seqid, iprot, oprot):
    args = getColumnDescriptors_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getColumnDescriptors_result()
    try:
      result.success = self._handler.getColumnDescriptors(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getColumnDescriptors", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getTableRegions(self, seqid, iprot, oprot):
    args = getTableRegions_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getTableRegions_result()
    try:
      result.success = self._handler.getTableRegions(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getTableRegions", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_createTable(self, seqid, iprot, oprot):
    args = createTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = createTable_result()
    try:
      self._handler.createTable(args.tableName, args.columnFamilies)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    except AlreadyExists, exist:
      result.exist = exist
    oprot.writeMessageBegin("createTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteTable(self, seqid, iprot, oprot):
    args = deleteTable_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteTable_result()
    try:
      self._handler.deleteTable(args.tableName)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteTable", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get(self, seqid, iprot, oprot):
    args = get_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_result()
    try:
      result.success = self._handler.get(args.tableName, args.row, args.column)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("get", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getVer(self, seqid, iprot, oprot):
    args = getVer_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getVer_result()
    try:
      result.success = self._handler.getVer(args.tableName, args.row, args.column, args.numVersions)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getVer", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getVerTs(self, seqid, iprot, oprot):
    args = getVerTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getVerTs_result()
    try:
      result.success = self._handler.getVerTs(args.tableName, args.row, args.column, args.timestamp, args.numVersions)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getVerTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRow(self, seqid, iprot, oprot):
    args = getRow_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRow_result()
    try:
      result.success = self._handler.getRow(args.tableName, args.row)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRow", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRowWithColumns(self, seqid, iprot, oprot):
    args = getRowWithColumns_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRowWithColumns_result()
    try:
      result.success = self._handler.getRowWithColumns(args.tableName, args.row, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRowWithColumns", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRowTs(self, seqid, iprot, oprot):
    args = getRowTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRowTs_result()
    try:
      result.success = self._handler.getRowTs(args.tableName, args.row, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRowTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_getRowWithColumnsTs(self, seqid, iprot, oprot):
    args = getRowWithColumnsTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = getRowWithColumnsTs_result()
    try:
      result.success = self._handler.getRowWithColumnsTs(args.tableName, args.row, args.columns, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("getRowWithColumnsTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRow(self, seqid, iprot, oprot):
    args = mutateRow_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRow_result()
    try:
      self._handler.mutateRow(args.tableName, args.row, args.mutations)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRow", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRowTs(self, seqid, iprot, oprot):
    args = mutateRowTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRowTs_result()
    try:
      self._handler.mutateRowTs(args.tableName, args.row, args.mutations, args.timestamp)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRowTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRows(self, seqid, iprot, oprot):
    args = mutateRows_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRows_result()
    try:
      self._handler.mutateRows(args.tableName, args.rowBatches)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRows", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_mutateRowsTs(self, seqid, iprot, oprot):
    args = mutateRowsTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = mutateRowsTs_result()
    try:
      self._handler.mutateRowsTs(args.tableName, args.rowBatches, args.timestamp)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("mutateRowsTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_atomicIncrement(self, seqid, iprot, oprot):
    args = atomicIncrement_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = atomicIncrement_result()
    try:
      result.success = self._handler.atomicIncrement(args.tableName, args.row, args.column, args.value)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("atomicIncrement", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAll(self, seqid, iprot, oprot):
    args = deleteAll_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAll_result()
    try:
      self._handler.deleteAll(args.tableName, args.row, args.column)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAll", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAllTs(self, seqid, iprot, oprot):
    args = deleteAllTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAllTs_result()
    try:
      self._handler.deleteAllTs(args.tableName, args.row, args.column, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAllTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAllRow(self, seqid, iprot, oprot):
    args = deleteAllRow_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAllRow_result()
    try:
      self._handler.deleteAllRow(args.tableName, args.row)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAllRow", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_deleteAllRowTs(self, seqid, iprot, oprot):
    args = deleteAllRowTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = deleteAllRowTs_result()
    try:
      self._handler.deleteAllRowTs(args.tableName, args.row, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("deleteAllRowTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpen(self, seqid, iprot, oprot):
    args = scannerOpen_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpen_result()
    try:
      result.success = self._handler.scannerOpen(args.tableName, args.startRow, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpen", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenWithStop(self, seqid, iprot, oprot):
    args = scannerOpenWithStop_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenWithStop_result()
    try:
      result.success = self._handler.scannerOpenWithStop(args.tableName, args.startRow, args.stopRow, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenWithStop", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenWithPrefix(self, seqid, iprot, oprot):
    args = scannerOpenWithPrefix_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenWithPrefix_result()
    try:
      result.success = self._handler.scannerOpenWithPrefix(args.tableName, args.startAndPrefix, args.columns)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenWithPrefix", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenTs(self, seqid, iprot, oprot):
    args = scannerOpenTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenTs_result()
    try:
      result.success = self._handler.scannerOpenTs(args.tableName, args.startRow, args.columns, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerOpenWithStopTs(self, seqid, iprot, oprot):
    args = scannerOpenWithStopTs_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerOpenWithStopTs_result()
    try:
      result.success = self._handler.scannerOpenWithStopTs(args.tableName, args.startRow, args.stopRow, args.columns, args.timestamp)
    except IOError, io:
      result.io = io
    oprot.writeMessageBegin("scannerOpenWithStopTs", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerGet(self, seqid, iprot, oprot):
    args = scannerGet_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerGet_result()
    try:
      result.success = self._handler.scannerGet(args.id)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("scannerGet", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerGetList(self, seqid, iprot, oprot):
    args = scannerGetList_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerGetList_result()
    try:
      result.success = self._handler.scannerGetList(args.id, args.nbRows)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("scannerGetList", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_scannerClose(self, seqid, iprot, oprot):
    args = scannerClose_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = scannerClose_result()
    try:
      self._handler.scannerClose(args.id)
    except IOError, io:
      result.io = io
    except IllegalArgument, ia:
      result.ia = ia
    oprot.writeMessageBegin("scannerClose", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()


# HELPER FUNCTIONS AND STRUCTURES

class enableTable_args:
  """
  Attributes:
   - tableName: name of the table
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('enableTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class enableTable_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('enableTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class disableTable_args:
  """
  Attributes:
   - tableName: name of the table
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('disableTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class disableTable_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('disableTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class isTableEnabled_args:
  """
  Attributes:
   - tableName: name of the table to check
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('isTableEnabled_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class isTableEnabled_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.BOOL, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.BOOL:
          self.success = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('isTableEnabled_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.BOOL, 0)
      oprot.writeBool(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class compact_args:
  """
  Attributes:
   - tableNameOrRegionName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableNameOrRegionName', None, None, ), # 1
  )

  def __init__(self, tableNameOrRegionName=None,):
    self.tableNameOrRegionName = tableNameOrRegionName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableNameOrRegionName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('compact_args')
    if self.tableNameOrRegionName != None:
      oprot.writeFieldBegin('tableNameOrRegionName', TType.STRING, 1)
      oprot.writeString(self.tableNameOrRegionName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class compact_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('compact_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class majorCompact_args:
  """
  Attributes:
   - tableNameOrRegionName
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableNameOrRegionName', None, None, ), # 1
  )

  def __init__(self, tableNameOrRegionName=None,):
    self.tableNameOrRegionName = tableNameOrRegionName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableNameOrRegionName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('majorCompact_args')
    if self.tableNameOrRegionName != None:
      oprot.writeFieldBegin('tableNameOrRegionName', TType.STRING, 1)
      oprot.writeString(self.tableNameOrRegionName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class majorCompact_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('majorCompact_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableNames_args:

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableNames_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableNames_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRING,None), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype19, _size16) = iprot.readListBegin()
          for _i20 in xrange(_size16):
            _elem21 = iprot.readString();
            self.success.append(_elem21)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableNames_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRING, len(self.success))
      for iter22 in self.success:
        oprot.writeString(iter22)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getColumnDescriptors_args:
  """
  Attributes:
   - tableName: table name
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getColumnDescriptors_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getColumnDescriptors_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING,None,TType.STRUCT,(ColumnDescriptor, ColumnDescriptor.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.MAP:
          self.success = {}
          (_ktype24, _vtype25, _size23 ) = iprot.readMapBegin() 
          for _i27 in xrange(_size23):
            _key28 = iprot.readString();
            _val29 = ColumnDescriptor()
            _val29.read(iprot)
            self.success[_key28] = _val29
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getColumnDescriptors_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.MAP, 0)
      oprot.writeMapBegin(TType.STRING, TType.STRUCT, len(self.success))
      for kiter30,viter31 in self.success.items():
        oprot.writeString(kiter30)
        viter31.write(oprot)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableRegions_args:
  """
  Attributes:
   - tableName: table name
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableRegions_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getTableRegions_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRegionInfo, TRegionInfo.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype35, _size32) = iprot.readListBegin()
          for _i36 in xrange(_size32):
            _elem37 = TRegionInfo()
            _elem37.read(iprot)
            self.success.append(_elem37)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getTableRegions_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter38 in self.success:
        iter38.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class createTable_args:
  """
  Attributes:
   - tableName: name of table to create
   - columnFamilies: list of column family descriptors
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.LIST, 'columnFamilies', (TType.STRUCT,(ColumnDescriptor, ColumnDescriptor.thrift_spec)), None, ), # 2
  )

  def __init__(self, tableName=None, columnFamilies=None,):
    self.tableName = tableName
    self.columnFamilies = columnFamilies

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.columnFamilies = []
          (_etype42, _size39) = iprot.readListBegin()
          for _i43 in xrange(_size39):
            _elem44 = ColumnDescriptor()
            _elem44.read(iprot)
            self.columnFamilies.append(_elem44)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('createTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.columnFamilies != None:
      oprot.writeFieldBegin('columnFamilies', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.columnFamilies))
      for iter45 in self.columnFamilies:
        iter45.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class createTable_result:
  """
  Attributes:
   - io
   - ia
   - exist
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'exist', (AlreadyExists, AlreadyExists.thrift_spec), None, ), # 3
  )

  def __init__(self, io=None, ia=None, exist=None,):
    self.io = io
    self.ia = ia
    self.exist = exist

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.exist = AlreadyExists()
          self.exist.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('createTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    if self.exist != None:
      oprot.writeFieldBegin('exist', TType.STRUCT, 3)
      self.exist.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteTable_args:
  """
  Attributes:
   - tableName: name of table to delete
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
  )

  def __init__(self, tableName=None,):
    self.tableName = tableName

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteTable_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteTable_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteTable_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - column: column name
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, column=None,):
    self.tableName = tableName
    self.row = row
    self.column = column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype49, _size46) = iprot.readListBegin()
          for _i50 in xrange(_size46):
            _elem51 = TCell()
            _elem51.read(iprot)
            self.success.append(_elem51)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter52 in self.success:
        iter52.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVer_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - column: column name
   - numVersions: number of versions to retrieve
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I32, 'numVersions', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, column=None, numVersions=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.numVersions = numVersions

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.numVersions = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVer_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.numVersions != None:
      oprot.writeFieldBegin('numVersions', TType.I32, 4)
      oprot.writeI32(self.numVersions)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVer_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype56, _size53) = iprot.readListBegin()
          for _i57 in xrange(_size53):
            _elem58 = TCell()
            _elem58.read(iprot)
            self.success.append(_elem58)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVer_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter59 in self.success:
        iter59.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVerTs_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - column: column name
   - timestamp: timestamp
   - numVersions: number of versions to retrieve
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
    (5, TType.I32, 'numVersions', None, None, ), # 5
  )

  def __init__(self, tableName=None, row=None, column=None, timestamp=None, numVersions=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.timestamp = timestamp
    self.numVersions = numVersions

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.I32:
          self.numVersions = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVerTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    if self.numVersions != None:
      oprot.writeFieldBegin('numVersions', TType.I32, 5)
      oprot.writeI32(self.numVersions)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getVerTs_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype63, _size60) = iprot.readListBegin()
          for _i64 in xrange(_size60):
            _elem65 = TCell()
            _elem65.read(iprot)
            self.success.append(_elem65)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getVerTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter66 in self.success:
        iter66.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRow_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
  )

  def __init__(self, tableName=None, row=None,):
    self.tableName = tableName
    self.row = row

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRow_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRow_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype70, _size67) = iprot.readListBegin()
          for _i71 in xrange(_size67):
            _elem72 = TRowResult()
            _elem72.read(iprot)
            self.success.append(_elem72)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRow_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter73 in self.success:
        iter73.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumns_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - columns: List of columns to return, null for all columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
  )

  def __init__(self, tableName=None, row=None, columns=None,):
    self.tableName = tableName
    self.row = row
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype77, _size74) = iprot.readListBegin()
          for _i78 in xrange(_size74):
            _elem79 = iprot.readString();
            self.columns.append(_elem79)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumns_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter80 in self.columns:
        oprot.writeString(iter80)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumns_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype84, _size81) = iprot.readListBegin()
          for _i85 in xrange(_size81):
            _elem86 = TRowResult()
            _elem86.read(iprot)
            self.success.append(_elem86)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumns_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter87 in self.success:
        iter87.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowTs_args:
  """
  Attributes:
   - tableName: name of the table
   - row: row key
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowTs_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype91, _size88) = iprot.readListBegin()
          for _i92 in xrange(_size88):
            _elem93 = TRowResult()
            _elem93.read(iprot)
            self.success.append(_elem93)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter94 in self.success:
        iter94.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumnsTs_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - columns: List of columns to return, null for all columns
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, columns=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.columns = columns
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype98, _size95) = iprot.readListBegin()
          for _i99 in xrange(_size95):
            _elem100 = iprot.readString();
            self.columns.append(_elem100)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumnsTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter101 in self.columns:
        oprot.writeString(iter101)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class getRowWithColumnsTs_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype105, _size102) = iprot.readListBegin()
          for _i106 in xrange(_size102):
            _elem107 = TRowResult()
            _elem107.read(iprot)
            self.success.append(_elem107)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('getRowWithColumnsTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter108 in self.success:
        iter108.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRow_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - mutations: list of mutation commands
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'mutations', (TType.STRUCT,(Mutation, Mutation.thrift_spec)), None, ), # 3
  )

  def __init__(self, tableName=None, row=None, mutations=None,):
    self.tableName = tableName
    self.row = row
    self.mutations = mutations

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.mutations = []
          (_etype112, _size109) = iprot.readListBegin()
          for _i113 in xrange(_size109):
            _elem114 = Mutation()
            _elem114.read(iprot)
            self.mutations.append(_elem114)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRow_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.mutations != None:
      oprot.writeFieldBegin('mutations', TType.LIST, 3)
      oprot.writeListBegin(TType.STRUCT, len(self.mutations))
      for iter115 in self.mutations:
        iter115.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRow_result:
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRow_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowTs_args:
  """
  Attributes:
   - tableName: name of table
   - row: row key
   - mutations: list of mutation commands
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.LIST, 'mutations', (TType.STRUCT,(Mutation, Mutation.thrift_spec)), None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, mutations=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.mutations = mutations
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.mutations = []
          (_etype119, _size116) = iprot.readListBegin()
          for _i120 in xrange(_size116):
            _elem121 = Mutation()
            _elem121.read(iprot)
            self.mutations.append(_elem121)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.mutations != None:
      oprot.writeFieldBegin('mutations', TType.LIST, 3)
      oprot.writeListBegin(TType.STRUCT, len(self.mutations))
      for iter122 in self.mutations:
        iter122.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowTs_result:
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRows_args:
  """
  Attributes:
   - tableName: name of table
   - rowBatches: list of row batches
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.LIST, 'rowBatches', (TType.STRUCT,(BatchMutation, BatchMutation.thrift_spec)), None, ), # 2
  )

  def __init__(self, tableName=None, rowBatches=None,):
    self.tableName = tableName
    self.rowBatches = rowBatches

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.rowBatches = []
          (_etype126, _size123) = iprot.readListBegin()
          for _i127 in xrange(_size123):
            _elem128 = BatchMutation()
            _elem128.read(iprot)
            self.rowBatches.append(_elem128)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRows_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.rowBatches != None:
      oprot.writeFieldBegin('rowBatches', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.rowBatches))
      for iter129 in self.rowBatches:
        iter129.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRows_result:
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRows_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowsTs_args:
  """
  Attributes:
   - tableName: name of table
   - rowBatches: list of row batches
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.LIST, 'rowBatches', (TType.STRUCT,(BatchMutation, BatchMutation.thrift_spec)), None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
  )

  def __init__(self, tableName=None, rowBatches=None, timestamp=None,):
    self.tableName = tableName
    self.rowBatches = rowBatches
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.rowBatches = []
          (_etype133, _size130) = iprot.readListBegin()
          for _i134 in xrange(_size130):
            _elem135 = BatchMutation()
            _elem135.read(iprot)
            self.rowBatches.append(_elem135)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowsTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.rowBatches != None:
      oprot.writeFieldBegin('rowBatches', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.rowBatches))
      for iter136 in self.rowBatches:
        iter136.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class mutateRowsTs_result:
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('mutateRowsTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class atomicIncrement_args:
  """
  Attributes:
   - tableName: name of table
   - row: row to increment
   - column: name of column
   - value: amount to increment by
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I64, 'value', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, column=None, value=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.value = value

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.value = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('atomicIncrement_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.value != None:
      oprot.writeFieldBegin('value', TType.I64, 4)
      oprot.writeI64(self.value)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class atomicIncrement_result:
  """
  Attributes:
   - success
   - io
   - ia
  """

  thrift_spec = (
    (0, TType.I64, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, io=None, ia=None,):
    self.success = success
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I64:
          self.success = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('atomicIncrement_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I64, 0)
      oprot.writeI64(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAll_args:
  """
  Attributes:
   - tableName: name of table
   - row: Row to update
   - column: name of column whose value is to be deleted
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, column=None,):
    self.tableName = tableName
    self.row = row
    self.column = column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAll_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAll_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAll_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllTs_args:
  """
  Attributes:
   - tableName: name of table
   - row: Row to update
   - column: name of column whose value is to be deleted
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.STRING, 'column', None, None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, row=None, column=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.column = column
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 3)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllTs_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRow_args:
  """
  Attributes:
   - tableName: name of table
   - row: key of the row to be completely deleted.
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
  )

  def __init__(self, tableName=None, row=None,):
    self.tableName = tableName
    self.row = row

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRow_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRow_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRow_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRowTs_args:
  """
  Attributes:
   - tableName: name of table
   - row: key of the row to be completely deleted.
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'row', None, None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
  )

  def __init__(self, tableName=None, row=None, timestamp=None,):
    self.tableName = tableName
    self.row = row
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRowTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 2)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class deleteAllRowTs_result:
  """
  Attributes:
   - io
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, io=None,):
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('deleteAllRowTs_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpen_args:
  """
  Attributes:
   - tableName: name of table
   - startRow: Starting row in table to scan.
  Send "" (empty string) to start at the first row.
   - columns: columns to scan. If column name is a column family, all
  columns of the specified column family are returned. It's also possible
  to pass a regex in the column qualifier.
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
  )

  def __init__(self, tableName=None, startRow=None, columns=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype140, _size137) = iprot.readListBegin()
          for _i141 in xrange(_size137):
            _elem142 = iprot.readString();
            self.columns.append(_elem142)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpen_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter143 in self.columns:
        oprot.writeString(iter143)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpen_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpen_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStop_args:
  """
  Attributes:
   - tableName: name of table
   - startRow: Starting row in table to scan.
  Send "" (empty string) to start at the first row.
   - stopRow: row to stop scanning on. This row is *not* included in the
  scanner's results
   - columns: columns to scan. If column name is a column family, all
  columns of the specified column family are returned. It's also possible
  to pass a regex in the column qualifier.
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.STRING, 'stopRow', None, None, ), # 3
    (4, TType.LIST, 'columns', (TType.STRING,None), None, ), # 4
  )

  def __init__(self, tableName=None, startRow=None, stopRow=None, columns=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.stopRow = stopRow
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.stopRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.LIST:
          self.columns = []
          (_etype147, _size144) = iprot.readListBegin()
          for _i148 in xrange(_size144):
            _elem149 = iprot.readString();
            self.columns.append(_elem149)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStop_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.stopRow != None:
      oprot.writeFieldBegin('stopRow', TType.STRING, 3)
      oprot.writeString(self.stopRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 4)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter150 in self.columns:
        oprot.writeString(iter150)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStop_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStop_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithPrefix_args:
  """
  Attributes:
   - tableName: name of table
   - startAndPrefix: the prefix (and thus start row) of the keys you want
   - columns: the columns you want returned
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startAndPrefix', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
  )

  def __init__(self, tableName=None, startAndPrefix=None, columns=None,):
    self.tableName = tableName
    self.startAndPrefix = startAndPrefix
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startAndPrefix = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype154, _size151) = iprot.readListBegin()
          for _i155 in xrange(_size151):
            _elem156 = iprot.readString();
            self.columns.append(_elem156)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithPrefix_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startAndPrefix != None:
      oprot.writeFieldBegin('startAndPrefix', TType.STRING, 2)
      oprot.writeString(self.startAndPrefix)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter157 in self.columns:
        oprot.writeString(iter157)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithPrefix_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithPrefix_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenTs_args:
  """
  Attributes:
   - tableName: name of table
   - startRow: Starting row in table to scan.
  Send "" (empty string) to start at the first row.
   - columns: columns to scan. If column name is a column family, all
  columns of the specified column family are returned. It's also possible
  to pass a regex in the column qualifier.
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.LIST, 'columns', (TType.STRING,None), None, ), # 3
    (4, TType.I64, 'timestamp', None, None, ), # 4
  )

  def __init__(self, tableName=None, startRow=None, columns=None, timestamp=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.columns = columns
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.columns = []
          (_etype161, _size158) = iprot.readListBegin()
          for _i162 in xrange(_size158):
            _elem163 = iprot.readString();
            self.columns.append(_elem163)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter164 in self.columns:
        oprot.writeString(iter164)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 4)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenTs_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStopTs_args:
  """
  Attributes:
   - tableName: name of table
   - startRow: Starting row in table to scan.
  Send "" (empty string) to start at the first row.
   - stopRow: row to stop scanning on. This row is *not* included in the
  scanner's results
   - columns: columns to scan. If column name is a column family, all
  columns of the specified column family are returned. It's also possible
  to pass a regex in the column qualifier.
   - timestamp: timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'tableName', None, None, ), # 1
    (2, TType.STRING, 'startRow', None, None, ), # 2
    (3, TType.STRING, 'stopRow', None, None, ), # 3
    (4, TType.LIST, 'columns', (TType.STRING,None), None, ), # 4
    (5, TType.I64, 'timestamp', None, None, ), # 5
  )

  def __init__(self, tableName=None, startRow=None, stopRow=None, columns=None, timestamp=None,):
    self.tableName = tableName
    self.startRow = startRow
    self.stopRow = stopRow
    self.columns = columns
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.tableName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.startRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.stopRow = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.LIST:
          self.columns = []
          (_etype168, _size165) = iprot.readListBegin()
          for _i169 in xrange(_size165):
            _elem170 = iprot.readString();
            self.columns.append(_elem170)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStopTs_args')
    if self.tableName != None:
      oprot.writeFieldBegin('tableName', TType.STRING, 1)
      oprot.writeString(self.tableName)
      oprot.writeFieldEnd()
    if self.startRow != None:
      oprot.writeFieldBegin('startRow', TType.STRING, 2)
      oprot.writeString(self.startRow)
      oprot.writeFieldEnd()
    if self.stopRow != None:
      oprot.writeFieldBegin('stopRow', TType.STRING, 3)
      oprot.writeString(self.stopRow)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.LIST, 4)
      oprot.writeListBegin(TType.STRING, len(self.columns))
      for iter171 in self.columns:
        oprot.writeString(iter171)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 5)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerOpenWithStopTs_result:
  """
  Attributes:
   - success
   - io
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, io=None,):
    self.success = success
    self.io = io

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerOpenWithStopTs_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGet_args:
  """
  Attributes:
   - id: id of a scanner returned by scannerOpen
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'id', None, None, ), # 1
  )

  def __init__(self, id=None,):
    self.id = id

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGet_args')
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I32, 1)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGet_result:
  """
  Attributes:
   - success
   - io
   - ia
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, io=None, ia=None,):
    self.success = success
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype175, _size172) = iprot.readListBegin()
          for _i176 in xrange(_size172):
            _elem177 = TRowResult()
            _elem177.read(iprot)
            self.success.append(_elem177)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGet_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter178 in self.success:
        iter178.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGetList_args:
  """
  Attributes:
   - id: id of a scanner returned by scannerOpen
   - nbRows: number of results to return
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'id', None, None, ), # 1
    (2, TType.I32, 'nbRows', None, None, ), # 2
  )

  def __init__(self, id=None, nbRows=None,):
    self.id = id
    self.nbRows = nbRows

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.nbRows = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGetList_args')
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I32, 1)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    if self.nbRows != None:
      oprot.writeFieldBegin('nbRows', TType.I32, 2)
      oprot.writeI32(self.nbRows)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerGetList_result:
  """
  Attributes:
   - success
   - io
   - ia
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TRowResult, TRowResult.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, io=None, ia=None,):
    self.success = success
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype182, _size179) = iprot.readListBegin()
          for _i183 in xrange(_size179):
            _elem184 = TRowResult()
            _elem184.read(iprot)
            self.success.append(_elem184)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerGetList_result')
    if self.success != None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter185 in self.success:
        iter185.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerClose_args:
  """
  Attributes:
   - id: id of a scanner returned by scannerOpen
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'id', None, None, ), # 1
  )

  def __init__(self, id=None,):
    self.id = id

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerClose_args')
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I32, 1)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class scannerClose_result:
  """
  Attributes:
   - io
   - ia
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'io', (IOError, IOError.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ia', (IllegalArgument, IllegalArgument.thrift_spec), None, ), # 2
  )

  def __init__(self, io=None, ia=None,):
    self.io = io
    self.ia = ia

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.io = IOError()
          self.io.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ia = IllegalArgument()
          self.ia.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('scannerClose_result')
    if self.io != None:
      oprot.writeFieldBegin('io', TType.STRUCT, 1)
      self.io.write(oprot)
      oprot.writeFieldEnd()
    if self.ia != None:
      oprot.writeFieldBegin('ia', TType.STRUCT, 2)
      self.ia.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = ttypes
#
# Autogenerated by Thrift
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#

from thrift.Thrift import *

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None



class TCell:
  """
  TCell - Used to transport a cell value (byte[]) and the timestamp it was
  stored with together as a result for get and getRow methods. This promotes
  the timestamp of a cell to a first-class value, making it easy to take
  note of temporal data. Cell is used all the way from HStore up to HTable.

  Attributes:
   - value
   - timestamp
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'value', None, None, ), # 1
    (2, TType.I64, 'timestamp', None, None, ), # 2
  )

  def __init__(self, value=None, timestamp=None,):
    self.value = value
    self.timestamp = timestamp

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.value = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TCell')
    if self.value != None:
      oprot.writeFieldBegin('value', TType.STRING, 1)
      oprot.writeString(self.value)
      oprot.writeFieldEnd()
    if self.timestamp != None:
      oprot.writeFieldBegin('timestamp', TType.I64, 2)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class ColumnDescriptor:
  """
  An HColumnDescriptor contains information about a column family
  such as the number of versions, compression settings, etc. It is
  used as input when creating a table or adding a column.

  Attributes:
   - name
   - maxVersions
   - compression
   - inMemory
   - bloomFilterType
   - bloomFilterVectorSize
   - bloomFilterNbHashes
   - blockCacheEnabled
   - timeToLive
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.I32, 'maxVersions', None, 3, ), # 2
    (3, TType.STRING, 'compression', None, "NONE", ), # 3
    (4, TType.BOOL, 'inMemory', None, False, ), # 4
    (5, TType.STRING, 'bloomFilterType', None, "NONE", ), # 5
    (6, TType.I32, 'bloomFilterVectorSize', None, 0, ), # 6
    (7, TType.I32, 'bloomFilterNbHashes', None, 0, ), # 7
    (8, TType.BOOL, 'blockCacheEnabled', None, False, ), # 8
    (9, TType.I32, 'timeToLive', None, -1, ), # 9
  )

  def __init__(self, name=None, maxVersions=thrift_spec[2][4], compression=thrift_spec[3][4], inMemory=thrift_spec[4][4], bloomFilterType=thrift_spec[5][4], bloomFilterVectorSize=thrift_spec[6][4], bloomFilterNbHashes=thrift_spec[7][4], blockCacheEnabled=thrift_spec[8][4], timeToLive=thrift_spec[9][4],):
    self.name = name
    self.maxVersions = maxVersions
    self.compression = compression
    self.inMemory = inMemory
    self.bloomFilterType = bloomFilterType
    self.bloomFilterVectorSize = bloomFilterVectorSize
    self.bloomFilterNbHashes = bloomFilterNbHashes
    self.blockCacheEnabled = blockCacheEnabled
    self.timeToLive = timeToLive

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.maxVersions = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.compression = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.BOOL:
          self.inMemory = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.STRING:
          self.bloomFilterType = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 6:
        if ftype == TType.I32:
          self.bloomFilterVectorSize = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 7:
        if ftype == TType.I32:
          self.bloomFilterNbHashes = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 8:
        if ftype == TType.BOOL:
          self.blockCacheEnabled = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 9:
        if ftype == TType.I32:
          self.timeToLive = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('ColumnDescriptor')
    if self.name != None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.maxVersions != None:
      oprot.writeFieldBegin('maxVersions', TType.I32, 2)
      oprot.writeI32(self.maxVersions)
      oprot.writeFieldEnd()
    if self.compression != None:
      oprot.writeFieldBegin('compression', TType.STRING, 3)
      oprot.writeString(self.compression)
      oprot.writeFieldEnd()
    if self.inMemory != None:
      oprot.writeFieldBegin('inMemory', TType.BOOL, 4)
      oprot.writeBool(self.inMemory)
      oprot.writeFieldEnd()
    if self.bloomFilterType != None:
      oprot.writeFieldBegin('bloomFilterType', TType.STRING, 5)
      oprot.writeString(self.bloomFilterType)
      oprot.writeFieldEnd()
    if self.bloomFilterVectorSize != None:
      oprot.writeFieldBegin('bloomFilterVectorSize', TType.I32, 6)
      oprot.writeI32(self.bloomFilterVectorSize)
      oprot.writeFieldEnd()
    if self.bloomFilterNbHashes != None:
      oprot.writeFieldBegin('bloomFilterNbHashes', TType.I32, 7)
      oprot.writeI32(self.bloomFilterNbHashes)
      oprot.writeFieldEnd()
    if self.blockCacheEnabled != None:
      oprot.writeFieldBegin('blockCacheEnabled', TType.BOOL, 8)
      oprot.writeBool(self.blockCacheEnabled)
      oprot.writeFieldEnd()
    if self.timeToLive != None:
      oprot.writeFieldBegin('timeToLive', TType.I32, 9)
      oprot.writeI32(self.timeToLive)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class TRegionInfo:
  """
  A TRegionInfo contains information about an HTable region.

  Attributes:
   - startKey
   - endKey
   - id
   - name
   - version
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'startKey', None, None, ), # 1
    (2, TType.STRING, 'endKey', None, None, ), # 2
    (3, TType.I64, 'id', None, None, ), # 3
    (4, TType.STRING, 'name', None, None, ), # 4
    (5, TType.BYTE, 'version', None, None, ), # 5
  )

  def __init__(self, startKey=None, endKey=None, id=None, name=None, version=None,):
    self.startKey = startKey
    self.endKey = endKey
    self.id = id
    self.name = name
    self.version = version

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.startKey = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.endKey = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.id = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.BYTE:
          self.version = iprot.readByte();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TRegionInfo')
    if self.startKey != None:
      oprot.writeFieldBegin('startKey', TType.STRING, 1)
      oprot.writeString(self.startKey)
      oprot.writeFieldEnd()
    if self.endKey != None:
      oprot.writeFieldBegin('endKey', TType.STRING, 2)
      oprot.writeString(self.endKey)
      oprot.writeFieldEnd()
    if self.id != None:
      oprot.writeFieldBegin('id', TType.I64, 3)
      oprot.writeI64(self.id)
      oprot.writeFieldEnd()
    if self.name != None:
      oprot.writeFieldBegin('name', TType.STRING, 4)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.version != None:
      oprot.writeFieldBegin('version', TType.BYTE, 5)
      oprot.writeByte(self.version)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class Mutation:
  """
  A Mutation object is used to either update or delete a column-value.

  Attributes:
   - isDelete
   - column
   - value
  """

  thrift_spec = (
    None, # 0
    (1, TType.BOOL, 'isDelete', None, False, ), # 1
    (2, TType.STRING, 'column', None, None, ), # 2
    (3, TType.STRING, 'value', None, None, ), # 3
  )

  def __init__(self, isDelete=thrift_spec[1][4], column=None, value=None,):
    self.isDelete = isDelete
    self.column = column
    self.value = value

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.BOOL:
          self.isDelete = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.value = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('Mutation')
    if self.isDelete != None:
      oprot.writeFieldBegin('isDelete', TType.BOOL, 1)
      oprot.writeBool(self.isDelete)
      oprot.writeFieldEnd()
    if self.column != None:
      oprot.writeFieldBegin('column', TType.STRING, 2)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    if self.value != None:
      oprot.writeFieldBegin('value', TType.STRING, 3)
      oprot.writeString(self.value)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class BatchMutation:
  """
  A BatchMutation object is used to apply a number of Mutations to a single row.

  Attributes:
   - row
   - mutations
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'row', None, None, ), # 1
    (2, TType.LIST, 'mutations', (TType.STRUCT,(Mutation, Mutation.thrift_spec)), None, ), # 2
  )

  def __init__(self, row=None, mutations=None,):
    self.row = row
    self.mutations = mutations

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.mutations = []
          (_etype3, _size0) = iprot.readListBegin()
          for _i4 in xrange(_size0):
            _elem5 = Mutation()
            _elem5.read(iprot)
            self.mutations.append(_elem5)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('BatchMutation')
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 1)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.mutations != None:
      oprot.writeFieldBegin('mutations', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.mutations))
      for iter6 in self.mutations:
        iter6.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class TRowResult:
  """
  Holds row name and then a map of columns to cells.

  Attributes:
   - row
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'row', None, None, ), # 1
    (2, TType.MAP, 'columns', (TType.STRING,None,TType.STRUCT,(TCell, TCell.thrift_spec)), None, ), # 2
  )

  def __init__(self, row=None, columns=None,):
    self.row = row
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.row = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.MAP:
          self.columns = {}
          (_ktype8, _vtype9, _size7 ) = iprot.readMapBegin() 
          for _i11 in xrange(_size7):
            _key12 = iprot.readString();
            _val13 = TCell()
            _val13.read(iprot)
            self.columns[_key12] = _val13
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TRowResult')
    if self.row != None:
      oprot.writeFieldBegin('row', TType.STRING, 1)
      oprot.writeString(self.row)
      oprot.writeFieldEnd()
    if self.columns != None:
      oprot.writeFieldBegin('columns', TType.MAP, 2)
      oprot.writeMapBegin(TType.STRING, TType.STRUCT, len(self.columns))
      for kiter14,viter15 in self.columns.items():
        oprot.writeString(kiter14)
        viter15.write(oprot)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class IOError(Exception):
  """
  An IOError exception signals that an error occurred communicating
  to the Hbase master or an Hbase region server.  Also used to return
  more general Hbase error conditions.

  Attributes:
   - message
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'message', None, None, ), # 1
  )

  def __init__(self, message=None,):
    self.message = message

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.message = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('IOError')
    if self.message != None:
      oprot.writeFieldBegin('message', TType.STRING, 1)
      oprot.writeString(self.message)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class IllegalArgument(Exception):
  """
  An IllegalArgument exception indicates an illegal or invalid
  argument was passed into a procedure.

  Attributes:
   - message
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'message', None, None, ), # 1
  )

  def __init__(self, message=None,):
    self.message = message

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.message = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('IllegalArgument')
    if self.message != None:
      oprot.writeFieldBegin('message', TType.STRING, 1)
      oprot.writeString(self.message)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class AlreadyExists(Exception):
  """
  An AlreadyExists exceptions signals that a table with the specified
  name already exists

  Attributes:
   - message
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'message', None, None, ), # 1
  )

  def __init__(self, message=None,):
    self.message = message

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.message = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('AlreadyExists')
    if self.message != None:
      oprot.writeFieldBegin('message', TType.STRING, 1)
      oprot.writeString(self.message)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()
    def validate(self):
      return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = path
""" path.py - An object representing a path to a file or directory.

Authors:
 Jason Orendorff <jason.orendorff\x40gmail\x2ecom>
 Mikhail Gusarov <dottedmag@dottedmag.net>
 Others - unfortunately attribution is lost

Example:

from path import path
d = path('/home/guido/bin')
for f in d.files('*.py'):
    f.chmod(0755)

This module requires Python 2.2 or later.
"""


# TODO
#   - Tree-walking functions don't avoid symlink loops.  Matt Harrison
#     sent me a patch for this.
#   - Bug in write_text().  It doesn't support Universal newline mode.
#   - Better error message in listdir() when self isn't a
#     directory. (On Windows, the error message really sucks.)
#   - Make sure everything has a good docstring.
#   - Add methods for regex find and replace.
#   - guess_content_type() method?
#   - Perhaps support arguments to touch().

from __future__ import generators

import sys, warnings, os, fnmatch, glob, shutil, codecs, hashlib, errno

__version__ = '2.2.2.990'
__all__ = ['path']

# Platform-specific support for path.owner
if os.name == 'nt':
    try:
        import win32security
    except ImportError:
        win32security = None
else:
    try:
        import pwd
    except ImportError:
        pwd = None

# Pre-2.3 support.  Are unicode filenames supported?
_base = str
_getcwd = os.getcwd
try:
    if os.path.supports_unicode_filenames:
        _base = unicode
        _getcwd = os.getcwdu
except AttributeError:
    pass

# Pre-2.3 workaround for booleans
try:
    True, False
except NameError:
    True, False = 1, 0

# Pre-2.3 workaround for basestring.
try:
    basestring
except NameError:
    basestring = (str, unicode)

# Universal newline support
_textmode = 'r'
if hasattr(file, 'newlines'):
    _textmode = 'U'


class TreeWalkWarning(Warning):
    pass

class path(_base):
    """ Represents a filesystem path.

    For documentation on individual methods, consult their
    counterparts in os.path.
    """

    # --- Special Python methods.

    def __repr__(self):
        return 'path(%s)' % _base.__repr__(self)

    # Adding a path and a string yields a path.
    def __add__(self, more):
        try:
            resultStr = _base.__add__(self, more)
        except TypeError:  #Python bug
            resultStr = NotImplemented
        if resultStr is NotImplemented:
            return resultStr
        return self.__class__(resultStr)

    def __radd__(self, other):
        if isinstance(other, basestring):
            return self.__class__(other.__add__(self))
        else:
            return NotImplemented

    # The / operator joins paths.
    def __div__(self, rel):
        """ fp.__div__(rel) == fp / rel == fp.joinpath(rel)

        Join two path components, adding a separator character if
        needed.
        """
        return self.__class__(os.path.join(self, rel))

    # Make the / operator work even when true division is enabled.
    __truediv__ = __div__

    def getcwd(cls):
        """ Return the current working directory as a path object. """
        return cls(_getcwd())
    getcwd = classmethod(getcwd)


    # --- Operations on path strings.

    isabs = os.path.isabs
    def abspath(self):       return self.__class__(os.path.abspath(self))
    def normcase(self):      return self.__class__(os.path.normcase(self))
    def normpath(self):      return self.__class__(os.path.normpath(self))
    def realpath(self):      return self.__class__(os.path.realpath(self))
    def expanduser(self):    return self.__class__(os.path.expanduser(self))
    def expandvars(self):    return self.__class__(os.path.expandvars(self))
    def dirname(self):       return self.__class__(os.path.dirname(self))
    basename = os.path.basename

    def expand(self):
        """ Clean up a filename by calling expandvars(),
        expanduser(), and normpath() on it.

        This is commonly everything needed to clean up a filename
        read from a configuration file, for example.
        """
        return self.expandvars().expanduser().normpath()

    def _get_namebase(self):
        base, ext = os.path.splitext(self.name)
        return base

    def _get_ext(self):
        f, ext = os.path.splitext(_base(self))
        return ext

    def _get_drive(self):
        drive, r = os.path.splitdrive(self)
        return self.__class__(drive)

    parent = property(
        dirname, None, None,
        """ This path's parent directory, as a new path object.

        For example, path('/usr/local/lib/libpython.so').parent == path('/usr/local/lib')
        """)

    name = property(
        basename, None, None,
        """ The name of this file or directory without the full path.

        For example, path('/usr/local/lib/libpython.so').name == 'libpython.so'
        """)

    namebase = property(
        _get_namebase, None, None,
        """ The same as path.name, but with one file extension stripped off.

        For example, path('/home/guido/python.tar.gz').name     == 'python.tar.gz',
        but          path('/home/guido/python.tar.gz').namebase == 'python.tar'
        """)

    ext = property(
        _get_ext, None, None,
        """ The file extension, for example '.py'. """)

    drive = property(
        _get_drive, None, None,
        """ The drive specifier, for example 'C:'.
        This is always empty on systems that don't use drive specifiers.
        """)

    def splitpath(self):
        """ p.splitpath() -> Return (p.parent, p.name). """
        parent, child = os.path.split(self)
        return self.__class__(parent), child

    def splitdrive(self):
        """ p.splitdrive() -> Return (p.drive, <the rest of p>).

        Split the drive specifier from this path.  If there is
        no drive specifier, p.drive is empty, so the return value
        is simply (path(''), p).  This is always the case on Unix.
        """
        drive, rel = os.path.splitdrive(self)
        return self.__class__(drive), rel

    def splitext(self):
        """ p.splitext() -> Return (p.stripext(), p.ext).

        Split the filename extension from this path and return
        the two parts.  Either part may be empty.

        The extension is everything from '.' to the end of the
        last path segment.  This has the property that if
        (a, b) == p.splitext(), then a + b == p.
        """
        filename, ext = os.path.splitext(self)
        return self.__class__(filename), ext

    def stripext(self):
        """ p.stripext() -> Remove one file extension from the path.

        For example, path('/home/guido/python.tar.gz').stripext()
        returns path('/home/guido/python.tar').
        """
        return self.splitext()[0]

    if hasattr(os.path, 'splitunc'):
        def splitunc(self):
            unc, rest = os.path.splitunc(self)
            return self.__class__(unc), rest

        def _get_uncshare(self):
            unc, r = os.path.splitunc(self)
            return self.__class__(unc)

        uncshare = property(
            _get_uncshare, None, None,
            """ The UNC mount point for this path.
            This is empty for paths on local drives. """)

    def joinpath(self, *args):
        """ Join two or more path components, adding a separator
        character (os.sep) if needed.  Returns a new path
        object.
        """
        return self.__class__(os.path.join(self, *args))

    def splitall(self):
        r""" Return a list of the path components in this path.

        The first item in the list will be a path.  Its value will be
        either os.curdir, os.pardir, empty, or the root directory of
        this path (for example, '/' or 'C:\\').  The other items in
        the list will be strings.

        path.path.joinpath(*result) will yield the original path.
        """
        parts = []
        loc = self
        while loc != os.curdir and loc != os.pardir:
            prev = loc
            loc, child = prev.splitpath()
            if loc == prev:
                break
            parts.append(child)
        parts.append(loc)
        parts.reverse()
        return parts

    def relpath(self):
        """ Return this path as a relative path,
        based from the current working directory.
        """
        cwd = self.__class__(os.getcwd())
        return cwd.relpathto(self)

    def relpathto(self, dest):
        """ Return a relative path from self to dest.

        If there is no relative path from self to dest, for example if
        they reside on different drives in Windows, then this returns
        dest.abspath().
        """
        origin = self.abspath()
        dest = self.__class__(dest).abspath()

        orig_list = origin.normcase().splitall()
        # Don't normcase dest!  We want to preserve the case.
        dest_list = dest.splitall()

        if orig_list[0] != os.path.normcase(dest_list[0]):
            # Can't get here from there.
            return dest

        # Find the location where the two paths start to differ.
        i = 0
        for start_seg, dest_seg in zip(orig_list, dest_list):
            if start_seg != os.path.normcase(dest_seg):
                break
            i += 1

        # Now i is the point where the two paths diverge.
        # Need a certain number of "os.pardir"s to work up
        # from the origin to the point of divergence.
        segments = [os.pardir] * (len(orig_list) - i)
        # Need to add the diverging part of dest_list.
        segments += dest_list[i:]
        if len(segments) == 0:
            # If they happen to be identical, use os.curdir.
            relpath = os.curdir
        else:
            relpath = os.path.join(*segments)
        return self.__class__(relpath)

    # --- Listing, searching, walking, and matching

    def listdir(self, pattern=None):
        """ D.listdir() -> List of items in this directory.

        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(self)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [self / child for child in names]

    def dirs(self, pattern=None):
        """ D.dirs() -> List of this directory's subdirectories.

        The elements of the list are path objects.
        This does not walk recursively into subdirectories
        (but see path.walkdirs).

        With the optional 'pattern' argument, this only lists
        directories whose names match the given pattern.  For
        example, d.dirs('build-*').
        """
        return [p for p in self.listdir(pattern) if p.isdir()]

    def files(self, pattern=None):
        """ D.files() -> List of the files in this directory.

        The elements of the list are path objects.
        This does not walk into subdirectories (see path.walkfiles).

        With the optional 'pattern' argument, this only lists files
        whose names match the given pattern.  For example,
        d.files('*.pyc').
        """
        
        return [p for p in self.listdir(pattern) if p.isfile()]

    def walk(self, pattern=None, errors='strict'):
        """ D.walk() -> iterator over files and subdirs, recursively.

        The iterator yields path objects naming each child item of
        this directory and its descendants.  This requires that
        D.isdir().

        This performs a depth-first traversal of the directory tree.
        Each directory is returned just before all its children.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            if pattern is None or child.fnmatch(pattern):
                yield child
            try:
                isdir = child.isdir()
            except Exception:
                if errors == 'ignore':
                    isdir = False
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (child, sys.exc_info()[1]),
                        TreeWalkWarning)
                    isdir = False
                else:
                    raise

            if isdir:
                for item in child.walk(pattern, errors):
                    yield item

    def walkdirs(self, pattern=None, errors='strict'):
        """ D.walkdirs() -> iterator over subdirs, recursively.

        With the optional 'pattern' argument, this yields only
        directories whose names match the given pattern.  For
        example, mydir.walkdirs('*test') yields only directories
        with names ending in 'test'.

        The errors= keyword argument controls behavior when an
        error occurs.  The default is 'strict', which causes an
        exception.  The other allowed values are 'warn', which
        reports the error via warnings.warn(), and 'ignore'.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            dirs = self.dirs()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in dirs:
            if pattern is None or child.fnmatch(pattern):
                yield child
            for subsubdir in child.walkdirs(pattern, errors):
                yield subsubdir

    def walkfiles(self, pattern=None, errors='strict'):
        """ D.walkfiles() -> iterator over files in D, recursively.

        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
        extension.
        """
        if errors not in ('strict', 'warn', 'ignore'):
            raise ValueError("invalid errors parameter")

        try:
            childList = self.listdir()
        except Exception:
            if errors == 'ignore':
                return
            elif errors == 'warn':
                warnings.warn(
                    "Unable to list directory '%s': %s"
                    % (self, sys.exc_info()[1]),
                    TreeWalkWarning)
                return
            else:
                raise

        for child in childList:
            try:
                isfile = child.isfile()
                isdir = not isfile and child.isdir()
            except:
                if errors == 'ignore':
                    continue
                elif errors == 'warn':
                    warnings.warn(
                        "Unable to access '%s': %s"
                        % (self, sys.exc_info()[1]),
                        TreeWalkWarning)
                    continue
                else:
                    raise

            if isfile:
                if pattern is None or child.fnmatch(pattern):
                    yield child
            elif isdir:
                for f in child.walkfiles(pattern, errors):
                    yield f

    def fnmatch(self, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards,
            for example '*.py'.
        """
        return fnmatch.fnmatch(self.name, pattern)

    def glob(self, pattern):
        """ Return a list of path objects that match the pattern.

        pattern - a path relative to this directory, with wildcards.

        For example, path('/users').glob('*/bin/*') returns a list
        of all the files users have in their bin directories.
        """
        cls = self.__class__
        return [cls(s) for s in glob.glob(_base(self / pattern))]


    # --- Reading or writing an entire file at once.

    def open(self, mode='r'):
        """ Open this file.  Return a file object. """
        return file(self, mode)

    def bytes(self):
        """ Open this file, read all bytes, return them as a string. """
        f = self.open('rb')
        try:
            return f.read()
        finally:
            f.close()

    def write_bytes(self, bytes, append=False):
        """ Open this file and write the given bytes to it.

        Default behavior is to overwrite any existing file.
        Call p.write_bytes(bytes, append=True) to append instead.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            f.write(bytes)
        finally:
            f.close()

    def text(self, encoding=None, errors='strict'):
        r""" Open this file, read it in, return the content as a string.

        This uses 'U' mode in Python 2.3 and later, so '\r\n' and '\r'
        are automatically translated to '\n'.

        Optional arguments:

        encoding - The Unicode encoding (or character set) of
            the file.  If present, the content of the file is
            decoded and returned as a unicode object; otherwise
            it is returned as an 8-bit str.
        errors - How to handle Unicode errors; see help(str.decode)
            for the options.  Default is 'strict'.
        """
        if encoding is None:
            # 8-bit
            f = self.open(_textmode)
            try:
                return f.read()
            finally:
                f.close()
        else:
            # Unicode
            f = codecs.open(self, 'r', encoding, errors)
            # (Note - Can't use 'U' mode here, since codecs.open
            # doesn't support 'U' mode, even in Python 2.3.)
            try:
                t = f.read()
            finally:
                f.close()
            return (t.replace(u'\r\n', u'\n')
                     .replace(u'\r\x85', u'\n')
                     .replace(u'\r', u'\n')
                     .replace(u'\x85', u'\n')
                     .replace(u'\u2028', u'\n'))

    def write_text(self, text, encoding=None, errors='strict', linesep=os.linesep, append=False):
        r""" Write the given text to this file.

        The default behavior is to overwrite any existing file;
        to append instead, use the 'append=True' keyword argument.

        There are two differences between path.write_text() and
        path.write_bytes(): newline handling and Unicode handling.
        See below.

        Parameters:

          - text - str/unicode - The text to be written.

          - encoding - str - The Unicode encoding that will be used.
            This is ignored if 'text' isn't a Unicode string.

          - errors - str - How to handle Unicode encoding errors.
            Default is 'strict'.  See help(unicode.encode) for the
            options.  This is ignored if 'text' isn't a Unicode
            string.

          - linesep - keyword argument - str/unicode - The sequence of
            characters to be used to mark end-of-line.  The default is
            os.linesep.  You can also specify None; this means to
            leave all newlines as they are in 'text'.

          - append - keyword argument - bool - Specifies what to do if
            the file already exists (True: append to the end of it;
            False: overwrite it.)  The default is False.


        --- Newline handling.

        write_text() converts all standard end-of-line sequences
        ('\n', '\r', and '\r\n') to your platform's default end-of-line
        sequence (see os.linesep; on Windows, for example, the
        end-of-line marker is '\r\n').

        If you don't like your platform's default, you can override it
        using the 'linesep=' keyword argument.  If you specifically want
        write_text() to preserve the newlines as-is, use 'linesep=None'.

        This applies to Unicode text the same as to 8-bit text, except
        there are three additional standard Unicode end-of-line sequences:
        u'\x85', u'\r\x85', and u'\u2028'.

        (This is slightly different from when you open a file for
        writing with fopen(filename, "w") in C or file(filename, 'w')
        in Python.)


        --- Unicode

        If 'text' isn't Unicode, then apart from newline handling, the
        bytes are written verbatim to the file.  The 'encoding' and
        'errors' arguments are not used and must be omitted.

        If 'text' is Unicode, it is first converted to bytes using the
        specified 'encoding' (or the default encoding if 'encoding'
        isn't specified).  The 'errors' argument applies only to this
        conversion.

        """
        if isinstance(text, unicode):
            if linesep is not None:
                # Convert all standard end-of-line sequences to
                # ordinary newline characters.
                text = (text.replace(u'\r\n', u'\n')
                            .replace(u'\r\x85', u'\n')
                            .replace(u'\r', u'\n')
                            .replace(u'\x85', u'\n')
                            .replace(u'\u2028', u'\n'))
                text = text.replace(u'\n', linesep)
            if encoding is None:
                encoding = sys.getdefaultencoding()
            bytes = text.encode(encoding, errors)
        else:
            # It is an error to specify an encoding if 'text' is
            # an 8-bit string.
            assert encoding is None

            if linesep is not None:
                text = (text.replace('\r\n', '\n')
                            .replace('\r', '\n'))
                bytes = text.replace('\n', linesep)

        self.write_bytes(bytes, append)

    def lines(self, encoding=None, errors='strict', retain=True):
        r""" Open this file, read all lines, return them in a list.

        Optional arguments:
            encoding - The Unicode encoding (or character set) of
                the file.  The default is None, meaning the content
                of the file is read as 8-bit characters and returned
                as a list of (non-Unicode) str objects.
            errors - How to handle Unicode errors; see help(str.decode)
                for the options.  Default is 'strict'
            retain - If true, retain newline characters; but all newline
                character combinations ('\r', '\n', '\r\n') are
                translated to '\n'.  If false, newline characters are
                stripped off.  Default is True.

        This uses 'U' mode in Python 2.3 and later.
        """
        if encoding is None and retain:
            f = self.open(_textmode)
            try:
                return f.readlines()
            finally:
                f.close()
        else:
            return self.text(encoding, errors).splitlines(retain)

    def write_lines(self, lines, encoding=None, errors='strict',
                    linesep=os.linesep, append=False):
        r""" Write the given lines of text to this file.

        By default this overwrites any existing file at this path.

        This puts a platform-specific newline sequence on every line.
        See 'linesep' below.

        lines - A list of strings.

        encoding - A Unicode encoding to use.  This applies only if
            'lines' contains any Unicode strings.

        errors - How to handle errors in Unicode encoding.  This
            also applies only to Unicode strings.

        linesep - The desired line-ending.  This line-ending is
            applied to every line.  If a line already has any
            standard line ending ('\r', '\n', '\r\n', u'\x85',
            u'\r\x85', u'\u2028'), that will be stripped off and
            this will be used instead.  The default is os.linesep,
            which is platform-dependent ('\r\n' on Windows, '\n' on
            Unix, etc.)  Specify None to write the lines as-is,
            like file.writelines().

        Use the keyword argument append=True to append lines to the
        file.  The default is to overwrite the file.  Warning:
        When you use this with Unicode data, if the encoding of the
        existing data in the file is different from the encoding
        you specify with the encoding= parameter, the result is
        mixed-encoding data, which can really confuse someone trying
        to read the file later.
        """
        if append:
            mode = 'ab'
        else:
            mode = 'wb'
        f = self.open(mode)
        try:
            for line in lines:
                isUnicode = isinstance(line, unicode)
                if linesep is not None:
                    # Strip off any existing line-end and add the
                    # specified linesep string.
                    if isUnicode:
                        if line[-2:] in (u'\r\n', u'\x0d\x85'):
                            line = line[:-2]
                        elif line[-1:] in (u'\r', u'\n',
                                           u'\x85', u'\u2028'):
                            line = line[:-1]
                    else:
                        if line[-2:] == '\r\n':
                            line = line[:-2]
                        elif line[-1:] in ('\r', '\n'):
                            line = line[:-1]
                    line += linesep
                if isUnicode:
                    if encoding is None:
                        encoding = sys.getdefaultencoding()
                    line = line.encode(encoding, errors)
                f.write(line)
        finally:
            f.close()

    def read_md5(self):
        """ Calculate the md5 hash for this file.

        This reads through the entire file.
        """
        return self.read_hash('md5')

    def _hash(self, hash_name):
        f = self.open('rb')
        try:
            m = hashlib.new(hash_name)
            while True:
                d = f.read(8192)
                if not d:
                    break
                m.update(d)
            return m
        finally:
            f.close()

    def read_hash(self, hash_name):
        """ Calculate given hash for this file.

        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
        """
        return self._hash(hash_name).digest()

    def read_hexhash(self, hash_name):
        """ Calculate given hash for this file, returning hexdigest.

        List of supported hashes can be obtained from hashlib package. This
        reads the entire file.
        """
        return self._hash(hash_name).hexdigest()

    # --- Methods for querying the filesystem.

    exists = os.path.exists
    isdir = os.path.isdir
    isfile = os.path.isfile
    islink = os.path.islink
    ismount = os.path.ismount

    if hasattr(os.path, 'samefile'):
        samefile = os.path.samefile

    getatime = os.path.getatime
    atime = property(
        getatime, None, None,
        """ Last access time of the file. """)

    getmtime = os.path.getmtime
    mtime = property(
        getmtime, None, None,
        """ Last-modified time of the file. """)

    if hasattr(os.path, 'getctime'):
        getctime = os.path.getctime
        ctime = property(
            getctime, None, None,
            """ Creation time of the file. """)

    getsize = os.path.getsize
    size = property(
        getsize, None, None,
        """ Size of the file, in bytes. """)

    if hasattr(os, 'access'):
        def access(self, mode):
            """ Return true if current user has access to this path.

            mode - One of the constants os.F_OK, os.R_OK, os.W_OK, os.X_OK
            """
            return os.access(self, mode)

    def stat(self):
        """ Perform a stat() system call on this path. """
        return os.stat(self)

    def lstat(self):
        """ Like path.stat(), but do not follow symbolic links. """
        return os.lstat(self)

    def get_owner(self):
        r""" Return the name of the owner of this file or directory.

        This follows symbolic links.

        On Windows, this returns a name of the form ur'DOMAIN\User Name'.
        On Windows, a group can own a file or directory.
        """
        if os.name == 'nt':
            if win32security is None:
                raise Exception("path.owner requires win32all to be installed")
            desc = win32security.GetFileSecurity(
                self, win32security.OWNER_SECURITY_INFORMATION)
            sid = desc.GetSecurityDescriptorOwner()
            account, domain, typecode = win32security.LookupAccountSid(None, sid)
            return domain + u'\\' + account
        else:
            if pwd is None:
                raise NotImplementedError("path.owner is not implemented on this platform.")
            st = self.stat()
            return pwd.getpwuid(st.st_uid).pw_name

    owner = property(
        get_owner, None, None,
        """ Name of the owner of this file or directory. """)

    if hasattr(os, 'statvfs'):
        def statvfs(self):
            """ Perform a statvfs() system call on this path. """
            return os.statvfs(self)

    if hasattr(os, 'pathconf'):
        def pathconf(self, name):
            return os.pathconf(self, name)


    # --- Modifying operations on files and directories

    def utime(self, times):
        """ Set the access and modified times of this file. """
        os.utime(self, times)

    def chmod(self, mode):
        os.chmod(self, mode)

    if hasattr(os, 'chown'):
        def chown(self, uid, gid):
            os.chown(self, uid, gid)

    def rename(self, new):
        os.rename(self, new)

    def renames(self, new):
        os.renames(self, new)


    # --- Create/delete operations on directories

    def mkdir(self, mode=0777):
        os.mkdir(self, mode)

    def mkdir_p(self, mode=0777):
        try:
            self.mkdir(mode)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def makedirs(self, mode=0777):
        os.makedirs(self, mode)

    def makedirs_p(self, mode=0777):
        try:
            self.makedirs(mode)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def rmdir(self):
        os.rmdir(self)

    def removedirs(self):
        os.removedirs(self)


    # --- Modifying operations on files

    def touch(self):
        """ Set the access/modified times of this file to the current time.
        Create the file if it does not exist.
        """
        fd = os.open(self, os.O_WRONLY | os.O_CREAT, 0666)
        os.close(fd)
        os.utime(self, None)

    def remove(self):
        os.remove(self)

    def remove_p(self):
        try:
            self.unlink()
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def unlink(self):
        os.unlink(self)

    def unlink_p(self):
        self.remove_p()

    # --- Links

    if hasattr(os, 'link'):
        def link(self, newpath):
            """ Create a hard link at 'newpath', pointing to this file. """
            os.link(self, newpath)

    if hasattr(os, 'symlink'):
        def symlink(self, newlink):
            """ Create a symbolic link at 'newlink', pointing here. """
            os.symlink(self, newlink)

    if hasattr(os, 'readlink'):
        def readlink(self):
            """ Return the path to which this symbolic link points.

            The result may be an absolute or a relative path.
            """
            return self.__class__(os.readlink(self))

        def readlinkabs(self):
            """ Return the path to which this symbolic link points.

            The result is always an absolute path.
            """
            p = self.readlink()
            if p.isabs():
                return p
            else:
                return (self.parent / p).abspath()


    # --- High-level functions from shutil

    copyfile = shutil.copyfile
    copymode = shutil.copymode
    copystat = shutil.copystat
    copy = shutil.copy
    copy2 = shutil.copy2
    copytree = shutil.copytree
    if hasattr(shutil, 'move'):
        move = shutil.move
    rmtree = shutil.rmtree


    # --- Special stuff from os

    if hasattr(os, 'chroot'):
        def chroot(self):
            os.chroot(self)

    if hasattr(os, 'startfile'):
        def startfile(self):
            os.startfile(self)


########NEW FILE########
