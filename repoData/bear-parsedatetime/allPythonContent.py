__FILENAME__ = basic
"""
Basic examples of how to use parsedatetime
"""

__license__ = """
Copyright (c) 2004-2006 Mike Taylor
Copyright (c) 2006 Darshana Chhajed
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import parsedatetime as pdt

# create an instance of Constants class so we can override some of the defaults

c = pdt.Constants()

c.BirthdayEpoch = 80    # BirthdayEpoch controls how parsedatetime
                        # handles two digit years.  If the parsed
                        # value is less than this value then the year
                        # is set to 2000 + the value, otherwise
                        # it's set to 1900 + the value

# create an instance of the Calendar class and pass in our Constants
# object instead of letting it create a default

p = pdt.Calendar(c)

# parse "tomorrow" and return the result

result = p.parse("tomorrow")

# parseDate() is a helper function that bypasses all of the
# natural language stuff and just tries to parse basic dates
# but using the locale information

result = p.parseDate("4/4/80")

# parseDateText() is a helper function that tries to parse
# long-form dates using the locale information

result = p.parseDateText("March 5th, 1980")


########NEW FILE########
__FILENAME__ = with_locale
"""
Examples of how to use parsedatetime with locale information provided.

Locale information can come from either PyICU (if available) or from
the more basic internal locale classes that are included in the
`Constants` class.
"""

__license__ = """
Copyright (c) 2004-2006 Mike Taylor
Copyright (c) 2006 Darshana Chhajed
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import parsedatetime as pdt

# create an instance of Constants class so we can specify the locale

c = pdt.Constants("en")
p = pdt.Calendar(c)

# print out the values from Constants to show how the locale information
# is being used/stored internally

print c.uses24, c.usesMeridian      # 24hr clock? AM/PM used?
print c.usePyICU                    # was PyICU found/enabled?
print c.meridian                    # list of the am and pm values
print c.am                          # list of the lowercased and stripped am string
print c.pm                          # list of the lowercased and stripped pm string
print c.dateFormats                 # dictionary of available date format strings
print c.timeFormats                 # dictionary of available time format strings
print c.timeSep                     # list of time separator, e.g. the ':' in '12:45'
print c.dateSep                     # list of date serarator, e.g. the '/' in '11/23/2006'
print c.Months                      # list of full month names
print c.shortMonths                 # list of the short month names
print c.Weekdays                    # list of the full week day names
print c.localeID                    # the locale identifier

result = p.parse("March 24th")


# create an instance of Constants class and force it to no use PyICU
# and to use the internal Spanish locale class

c = pdt.Constants(localeID="es", usePyICU=False)
p = pdt.Calendar(c)

result = p.parse("Marzo 24")


########NEW FILE########
__FILENAME__ = parsedatetime
# Backward compatibility fix.
from . import *    

########NEW FILE########
__FILENAME__ = pdt_locales

"""
pdt_locales

All of the included locale classes shipped with pdt.
"""

__author__       = 'Mike Taylor (bear@code-bear.com)'
__copyright__    = 'Copyright (c) 2004 Mike Taylor'
__license__      = 'Apache v2.0'
__version__      = '1.0.0'
__contributors__ = [ 'Darshana Chhajed',
                     'Michael Lim (lim.ck.michael@gmail.com)',
                     'Bernd Zeimetz (bzed@debian.org)',
                   ]


import datetime

try:
   import PyICU as pyicu
except:
   pyicu = None


def lcase(x):
    return x.lower()


class pdtLocale_base(object):
    """
    default values for Locales
    """
    locale_keys = [ 'MonthOffsets', 'Months', 'WeekdayOffsets', 'Weekdays', 
                    'dateFormats', 'dateSep', 'dayOffsets', 'dp_order', 
                    'localeID', 'meridian', 'Modifiers', 're_sources', 're_values', 
                    'shortMonths', 'shortWeekdays', 'timeFormats', 'timeSep', 'units', 
                    'uses24', 'usesMeridian', 'numbers' ]

    def __init__(self):
        self.localeID      = None   # don't use a unicode string
        self.dateSep       = [ '/', '.' ]
        self.timeSep       = [ ':' ]
        self.meridian      = [ 'AM', 'PM' ]
        self.usesMeridian  = True
        self.uses24        = True

        self.WeekdayOffsets = {}
        self.MonthOffsets   = {}

        # always lowercase any lookup values - helper code expects that
        self.Weekdays      = [ 'monday', 'tuesday', 'wednesday',
                               'thursday', 'friday', 'saturday', 'sunday',
                             ]
        self.shortWeekdays = [ 'mon', 'tues', 'wed',
                               'th', 'fri', 'sat', 'sun',
                             ]
        self.Months        = [ 'january', 'february', 'march',
                               'april',   'may',      'june',
                               'july',    'august',   'september',
                               'october', 'november', 'december',
                             ]
        self.shortMonths   = [ 'jan', 'feb', 'mar',
                               'apr', 'may', 'jun',
                               'jul', 'aug', 'sep',
                               'oct', 'nov', 'dec',
                             ]
        # use the same formats as ICU by default
        self.dateFormats   = { 'full':   'EEEE, MMMM d, yyyy',
                               'long':   'MMMM d, yyyy',
                               'medium': 'MMM d, yyyy',
                               'short':  'M/d/yy',
                             }
        self.timeFormats   = { 'full':   'h:mm:ss a z',
                               'long':   'h:mm:ss a z',
                               'medium': 'h:mm:ss a',
                               'short':  'h:mm a',
                             }

        self.dp_order = [ 'm', 'd', 'y' ]

        # Used to parse expressions like "in 5 hours"
        self.numbers = { 'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
                         'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
                         'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
                         'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
                         'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
                         'twenty': 20 }


          # this will be added to re_values later
        self.units = { 'seconds': [ 'second', 'seconds', 'sec', 's' ],
                       'minutes': [ 'minute', 'minutes', 'min', 'm' ],
                       'hours':   [ 'hour',   'hours',   'hr',  'h' ],
                       'days':    [ 'day',    'days',    'dy',  'd' ],
                       'weeks':   [ 'week',   'weeks',   'wk',  'w' ],
                       'months':  [ 'month',  'months',  'mth'      ],
                       'years':   [ 'year',   'years',   'yr',  'y' ],
                     }

          # text constants to be used by later regular expressions
        self.re_values     = { 'specials':       'in|on|of|at',
                               'timeseperator':  ':',
                               'rangeseperator': '-',
                               'daysuffix':      'rd|st|nd|th',
                               'meridian':       'am|pm|a.m.|p.m.|a|p',
                               'qunits':         'h|m|s|d|w|y',
                               'now':            [ 'now' ],
                             }

          # Used to adjust the returned date before/after the source
        self.Modifiers = { 'from':      1,
                           'before':   -1,
                           'after':     1,
                           'ago':      -1,
                           'prior':    -1,
                           'prev':     -1,
                           'last':     -1,
                           'next':      1,
                           'previous': -1,
                           'in a':      2,
                           'end of':    0,
                           'eod':       1,
                           'eom':       1,
                           'eoy':       1,
                         }

        self.dayOffsets = { 'tomorrow':   1,
                            'today':      0,
                            'yesterday': -1,
                          }

          # special day and/or times, i.e. lunch, noon, evening
          # each element in the dictionary is a dictionary that is used
          # to fill in any value to be replace - the current date/time will
          # already have been populated by the method buildSources
        self.re_sources    = { 'noon':      { 'hr': 12, 'mn': 0, 'sec': 0 },
                               'lunch':     { 'hr': 12, 'mn': 0, 'sec': 0 },
                               'morning':   { 'hr':  6, 'mn': 0, 'sec': 0 },
                               'breakfast': { 'hr':  8, 'mn': 0, 'sec': 0 },
                               'dinner':    { 'hr': 19, 'mn': 0, 'sec': 0 },
                               'evening':   { 'hr': 18, 'mn': 0, 'sec': 0 },
                               'midnight':  { 'hr':  0, 'mn': 0, 'sec': 0 },
                               'night':     { 'hr': 21, 'mn': 0, 'sec': 0 },
                               'tonight':   { 'hr': 21, 'mn': 0, 'sec': 0 },
                               'eod':       { 'hr': 17, 'mn': 0, 'sec': 0 },
                             }


class pdtLocale_icu(pdtLocale_base):
    """
    Create a locale from pyICU
    """
    def __init__(self, localeID):
        super( pdtLocale_icu, self ).__init__()

        self.icu = None

        if pyicu is not None:
            if localeID is None:
              localeID = 'en_US'
            self.icu = pyicu.Locale(localeID)

        if self.icu is not None:
            # grab spelled out format of all numbers from 0 to 100
            rbnf = pyicu.RuleBasedNumberFormat(pyicu.URBNFRuleSetTag.SPELLOUT, self.icu)
            self.numbers = dict([(rbnf.format(i), i) for i in xrange(0, 100)])

            self.symbols = pyicu.DateFormatSymbols(self.icu)

              # grab ICU list of weekdays, skipping first entry which
              # is always blank
            wd  = list(map(lcase, self.symbols.getWeekdays()[1:]))
            swd = list(map(lcase, self.symbols.getShortWeekdays()[1:]))

              # store them in our list with Monday first (ICU puts Sunday first)
            self.Weekdays      = wd[1:] + wd[0:1]
            self.shortWeekdays = swd[1:] + swd[0:1]
            self.Months        = list(map(lcase, self.symbols.getMonths()))
            self.shortMonths   = list(map(lcase, self.symbols.getShortMonths()))

            self.icu_df      = { 'full':   pyicu.DateFormat.createDateInstance(pyicu.DateFormat.kFull,   self.icu),
                                 'long':   pyicu.DateFormat.createDateInstance(pyicu.DateFormat.kLong,   self.icu),
                                 'medium': pyicu.DateFormat.createDateInstance(pyicu.DateFormat.kMedium, self.icu),
                                 'short':  pyicu.DateFormat.createDateInstance(pyicu.DateFormat.kShort,  self.icu),
                               }
            self.icu_tf      = { 'full':   pyicu.DateFormat.createTimeInstance(pyicu.DateFormat.kFull,   self.icu),
                                 'long':   pyicu.DateFormat.createTimeInstance(pyicu.DateFormat.kLong,   self.icu),
                                 'medium': pyicu.DateFormat.createTimeInstance(pyicu.DateFormat.kMedium, self.icu),
                                 'short':  pyicu.DateFormat.createTimeInstance(pyicu.DateFormat.kShort,  self.icu),
                               }
            self.dateFormats = { 'full':   self.icu_df['full'].toPattern(),
                                 'long':   self.icu_df['long'].toPattern(),
                                 'medium': self.icu_df['medium'].toPattern(),
                                 'short':  self.icu_df['short'].toPattern(),
                               }
            self.timeFormats = { 'full':   self.icu_tf['full'].toPattern(),
                                 'long':   self.icu_tf['long'].toPattern(),
                                 'medium': self.icu_tf['medium'].toPattern(),
                                 'short':  self.icu_tf['short'].toPattern(),
                               }

            am = ''
            pm = ''
            ts = ''

              # ICU doesn't seem to provide directly the date or time seperator
              # so we have to figure it out
            o = self.icu_tf['short']
            s = self.timeFormats['short']

            self.usesMeridian = 'a' in s
            self.uses24       = 'H' in s

              # '11:45 AM' or '11:45'
            s = o.format(datetime.datetime(2003, 10, 30, 11, 45))

              # ': AM' or ':'
            s = s.replace('11', '').replace('45', '')

            if len(s) > 0:
               ts = s[0]

            if self.usesMeridian:
                 # '23:45 AM' or '23:45'
               am = s[1:].strip()
               s  = o.format(datetime.datetime(2003, 10, 30, 23, 45))

               if self.uses24:
                   s = s.replace('23', '')
               else:
                   s = s.replace('11', '')

                 # 'PM' or ''
               pm = s.replace('45', '').replace(ts, '').strip()

            self.timeSep  = [ ts ]
            self.meridian = [ am, pm ]

            o = self.icu_df['short']
            s = o.format(datetime.datetime(2003, 10, 30, 11, 45))
            s = s.replace('10', '').replace('30', '').replace('03', '').replace('2003', '')

            if len(s) > 0:
               ds = s[0]
            else:
               ds = '/'

            self.dateSep = [ ds ]
            s            = self.dateFormats['short']
            l            = s.lower().split(ds)
            dp_order     = []

            for s in l:
               if len(s) > 0:
                   dp_order.append(s[:1])

            self.dp_order = dp_order



class pdtLocale_en(pdtLocale_base):
    """
    en_US Locale
    """
    def __init__(self):
        super( pdtLocale_en, self ).__init__()

        self.localeID = 'en_US'  # don't use a unicode string
        self.uses24   = False


class pdtLocale_au(pdtLocale_base):
    """
    en_AU Locale
    """
    def __init__(self):
        super( pdtLocale_au, self ).__init__()

        self.localeID = 'en_A'   # don't use a unicode string
        self.dateSep  = [ '-', '/' ]
        self.uses24   = False

        self.dateFormats['full']   = 'EEEE, d MMMM yyyy'
        self.dateFormats['long']   = 'd MMMM yyyy'
        self.dateFormats['medium'] = 'dd/MM/yyyy'
        self.dateFormats['short']  = 'd/MM/yy'

        self.timeFormats['long']   = self.timeFormats['full']

        self.dp_order = [ 'd', 'm', 'y' ]

class pdtLocale_es(pdtLocale_base):
    """
    es Locale

    Note that I don't speak Spanish so many of the items below are still in English
    """
    def __init__(self):
        super( pdtLocale_es, self ).__init__()

        self.localeID     = 'es'   # don't use a unicode string
        self.dateSep      = [ '/' ]
        self.usesMeridian = False
        self.uses24       = True

        self.Weekdays      = [ 'lunes', 'martes', 'mi\xe9rcoles',
                               'jueves', 'viernes', 's\xe1bado', 'domingo',
                             ]
        self.shortWeekdays = [ 'lun', 'mar', 'mi\xe9',
                               'jue', 'vie', 's\xe1b', 'dom',
                             ]
        self.Months        = [ 'enero', 'febrero', 'marzo',
                               'abril', 'mayo', 'junio',
                               'julio', 'agosto', 'septiembre',
                               'octubre', 'noviembre', 'diciembre'
                             ]
        self.shortMonths   = [ 'ene', 'feb', 'mar',
                               'abr', 'may', 'jun',
                               'jul', 'ago', 'sep',
                               'oct', 'nov', 'dic'
                             ]
        self.dateFormats['full']   = "EEEE d' de 'MMMM' de 'yyyy"
        self.dateFormats['long']   = "d' de 'MMMM' de 'yyyy"
        self.dateFormats['medium'] = "dd-MMM-yy"
        self.dateFormats['short']  = "d/MM/yy"

        self.timeFormats['full']   = "HH'H'mm' 'ss z"
        self.timeFormats['long']   = "HH:mm:ss z"
        self.timeFormats['medium'] = "HH:mm:ss"
        self.timeFormats['short']  = "HH:mm"

        self.dp_order = [ 'd', 'm', 'y' ]


class pdtLocale_de(pdtLocale_base):
    """
    de_DE Locale constants

    Contributed by Debian parsedatetime package maintainer Bernd Zeimetz <bzed@debian.org>
    """
    def __init__(self):
        super( pdtLocale_de, self ).__init__()

        self.localeID      = 'de_DE'   # don't use a unicode string
        self.dateSep       = [ '.' ]
        self.timeSep       = [ ':' ]
        self.meridian      = [ ]
        self.usesMeridian  = False
        self.uses24        = True

        self.Weekdays      = [ 'montag', 'dienstag', 'mittwoch',
                               'donnerstag', 'freitag', 'samstag', 'sonntag',
                             ]
        self.shortWeekdays = [ 'mo', 'di', 'mi',
                               'do', 'fr', 'sa', 'so',
                             ]
        self.Months        = [ 'januar',  'februar',  'm\xe4rz',
                               'april',   'mai',      'juni',
                               'juli',    'august',   'september',
                               'oktober', 'november', 'dezember',
                             ]
        self.shortMonths   = [ 'jan', 'feb', 'mrz',
                               'apr', 'mai', 'jun',
                               'jul', 'aug', 'sep',
                               'okt', 'nov', 'dez',
                             ]
        self.dateFormats['full']   = 'EEEE, d. MMMM yyyy'
        self.dateFormats['long']   = 'd. MMMM yyyy'
        self.dateFormats['medium'] = 'dd.MM.yyyy'
        self.dateFormats['short']  = 'dd.MM.yy'

        self.timeFormats['full']   = 'HH:mm:ss v'
        self.timeFormats['long']   = 'HH:mm:ss z'
        self.timeFormats['medium'] = 'HH:mm:ss'
        self.timeFormats['short']  = 'HH:mm'

        self.dp_order = [ 'd', 'm', 'y' ]

        self.units['seconds'] = [ 'sekunden', 'sek',  's' ]
        self.units['minutes'] = [ 'minuten',  'min' , 'm' ]
        self.units['hours']   = [ 'stunden',  'std',  'h' ]
        self.units['days']    = [ 'tag',  'tage',     't' ]
        self.units['weeks']   = [ 'wochen',           'w' ]
        self.units['months']  = [ 'monat', 'monate' ]  #the short version would be a capital M,
                                                       #as I understand it we can't distinguis
                                                       #between m for minutes and M for months.
        self.units['years']   = [ 'jahr', 'jahre',    'j' ]

        self.re_values['specials']       = 'am|dem|der|im|in|den|zum'
        self.re_values['timeseperator']  = ':'
        self.re_values['rangeseperator'] = '-'
        self.re_values['daysuffix']      = ''
        self.re_values['qunits']         = 'h|m|s|t|w|m|j'
        self.re_values['now']            = [ 'jetzt' ]

          # Used to adjust the returned date before/after the source
          #still looking for insight on how to translate all of them to german.
        self.Modifiers['from']        =  1
        self.Modifiers['before']      = -1
        self.Modifiers['after']       =  1
        self.Modifiers['vergangener'] = -1
        self.Modifiers['vorheriger']  = -1
        self.Modifiers['prev']        = -1
        self.Modifiers['letzter']     = -1
        self.Modifiers['n\xe4chster'] =  1
        self.Modifiers['dieser']      =  0
        self.Modifiers['previous']    = -1
        self.Modifiers['in a']        =  2
        self.Modifiers['end of']      =  0
        self.Modifiers['eod']         =  0
        self.Modifiers['eo']          =  0

          #morgen/abermorgen does not work, see http://code.google.com/p/parsedatetime/issues/detail?id=19
        self.dayOffsets['morgen']        =  1
        self.dayOffsets['heute']         =  0
        self.dayOffsets['gestern']       = -1
        self.dayOffsets['vorgestern']    = -2
        self.dayOffsets['\xfcbermorgen'] =  2

          # special day and/or times, i.e. lunch, noon, evening
          # each element in the dictionary is a dictionary that is used
          # to fill in any value to be replace - the current date/time will
          # already have been populated by the method buildSources
        self.re_sources['mittag']         = { 'hr': 12, 'mn': 0, 'sec': 0 }
        self.re_sources['mittags']        = { 'hr': 12, 'mn': 0, 'sec': 0 }
        self.re_sources['mittagessen']    = { 'hr': 12, 'mn': 0, 'sec': 0 }
        self.re_sources['morgen']         = { 'hr':  6, 'mn': 0, 'sec': 0 }
        self.re_sources['morgens']        = { 'hr':  6, 'mn': 0, 'sec': 0 }
        self.re_sources['fr\e4hst\xe4ck'] = { 'hr':  8, 'mn': 0, 'sec': 0 }
        self.re_sources['abendessen']     = { 'hr': 19, 'mn': 0, 'sec': 0 }
        self.re_sources['abend']          = { 'hr': 18, 'mn': 0, 'sec': 0 }
        self.re_sources['abends']         = { 'hr': 18, 'mn': 0, 'sec': 0 }
        self.re_sources['mitternacht']    = { 'hr':  0, 'mn': 0, 'sec': 0 }
        self.re_sources['nacht']          = { 'hr': 21, 'mn': 0, 'sec': 0 }
        self.re_sources['nachts']         = { 'hr': 21, 'mn': 0, 'sec': 0 }
        self.re_sources['heute abend']    = { 'hr': 21, 'mn': 0, 'sec': 0 }
        self.re_sources['heute nacht']    = { 'hr': 21, 'mn': 0, 'sec': 0 }
        self.re_sources['feierabend']     = { 'hr': 17, 'mn': 0, 'sec': 0 }


########NEW FILE########
__FILENAME__ = TestAustralianLocale

"""
Test parsing of simple date and times using the Australian locale
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.ptc = pdt.Constants('en_AU', usePyICU=False)
        self.cal = pdt.Calendar(self.ptc)

        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testTimes(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 23, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('11:00:00 PM', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00 PM',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11 PM',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11PM',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('2300',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('23:00',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11p',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11pm',        start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 11, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('11:00:00 AM', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00 AM',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11 AM',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11AM',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1100',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11a',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11am',        start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 7, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('730',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('0730', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 17, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1730',   start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('173000', start), (target, 2)))

    def testDates(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(2006, 8, 25,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('25-08-2006', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25/08/2006', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25.08.2006', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25-8-06',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25/8/06',    start), (target, 1)))

        if self.mth > 8 or (self.mth == 8 and self.dy > 25):
            target = datetime.datetime(self.yr+1, 8, 25,  self.hr, self.mn, self.sec).timetuple()
        else:
            target = datetime.datetime(self.yr, 8, 25,  self.hr, self.mn, self.sec).timetuple()
            
        self.assertTrue(_compareResults(self.cal.parse('25-8',       start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25/8',       start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25.8',       start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25-08',      start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25/08',      start), (target, 1)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestComplexDateTimes

"""
Test parsing of complex date and times
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testDates(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(2006, 8, 25,  17, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('08/25/2006 5pm',        start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm on 08.25.2006',     start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm August 25, 2006',   start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm August 25th, 2006', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm 25 August, 2006',   start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm 25th August, 2006', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25, 2006 5pm',      start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25th, 2006 5pm',    start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('25 Aug, 2006 5pm',      start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('25th Aug 2006, 5pm',    start), (target, 3)))

        if self.mth > 8 or (self.mth == 8 and self.dy > 5):
            target = datetime.datetime(self.yr + 1, 8, 5, 17, 0, 0).timetuple()
        else:
            target = datetime.datetime(self.yr, 8, 5, 17, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('8/5 at 5pm',     start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm 8.5',        start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('08/05 5pm',      start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('August 5 5pm',   start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('August 5th 5pm', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm Aug 05',     start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 05 5pm',     start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 05th 5pm',   start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5 August 5pm',   start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5th August 5pm', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('5pm 05 Aug',     start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('05 Aug 5pm',     start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('05th Aug 5pm',   start), (target, 3)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestErrors

"""
Test parsing of units
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


def _compareResultsErrorFlag(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, _, _, _, _, _, _ = target
    v_yr, v_mth, v_dy, _, _, _, _, _, _ = value

    return (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testErrors(self):
        s     = datetime.datetime.now()
        start = s.timetuple()

        # These tests all return current date/time as they are out of range
        self.assertTrue(_compareResults(self.cal.parse('01/0',   start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('08/35',  start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('18/35',  start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('1799',   start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('781',    start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('2702',   start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('78',     start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('11',     start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('1',      start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('174565', start), (start, 0)))
        self.assertTrue(_compareResults(self.cal.parse('177505', start), (start, 0)))
        # ensure short month names do not cause false positives within a word - jun (june)
        self.assertTrue(_compareResults(self.cal.parse('injunction', start), (start, 0)))
        # ensure short month names do not cause false positives at the start of a word - jul (juuly)
        self.assertTrue(_compareResults(self.cal.parse('julius', start), (start, 0)))
        # ensure short month names do not cause false positives at the end of a word - mar (march)
        self.assertTrue(_compareResults(self.cal.parse('lamar', start), (start, 0)))
        # ensure short weekday names do not cause false positives within a word - mon (monday)
        self.assertTrue(_compareResults(self.cal.parse('demonize', start), (start, 0)))
        # ensure short weekday names do not cause false positives at the start of a word - mon (monday)
        self.assertTrue(_compareResults(self.cal.parse('money', start), (start, 0)))
        # ensure short weekday names do not cause false positives at the end of a word - th (thursday)
        self.assertTrue(_compareResults(self.cal.parse('month', start), (start, 0)))

        # This test actually parses into *something* for some locales, so need to check the error flag
        self.assertTrue(_compareResultsErrorFlag(self.cal.parse('30/030/01/071/07', start), (start, 1)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestFrenchLocale

"""
Test parsing of simple date and times using the French locale

Note: requires PyICU
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.ptc = pdt.Constants('fr_FR', usePyICU=True)
        self.cal = pdt.Calendar(self.ptc)

        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testTimes(self):
        if self.ptc.localeID == 'fr_FR':
            start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
            target = datetime.datetime(self.yr, self.mth, self.dy, 23, 0, 0).timetuple()

            self.assertTrue(_compareResults(self.cal.parse('2300',  start), (target, 2)))
            self.assertTrue(_compareResults(self.cal.parse('23:00', start), (target, 2)))

            target = datetime.datetime(self.yr, self.mth, self.dy, 11, 0, 0).timetuple()

            self.assertTrue(_compareResults(self.cal.parse('1100',  start), (target, 2)))
            self.assertTrue(_compareResults(self.cal.parse('11:00', start), (target, 2)))

            target = datetime.datetime(self.yr, self.mth, self.dy, 7, 30, 0).timetuple()

            self.assertTrue(_compareResults(self.cal.parse('730',  start), (target, 2)))
            self.assertTrue(_compareResults(self.cal.parse('0730', start), (target, 2)))

            target = datetime.datetime(self.yr, self.mth, self.dy, 17, 30, 0).timetuple()

            self.assertTrue(_compareResults(self.cal.parse('1730',   start), (target, 2)))
            self.assertTrue(_compareResults(self.cal.parse('173000', start), (target, 2)))

    def testDates(self):
        if self.ptc.localeID == 'fr_FR':
            start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
            target = datetime.datetime(2006, 8, 25, self.hr, self.mn, self.sec).timetuple()

            self.assertTrue(_compareResults(self.cal.parse('25/08/2006',       start), (target, 1)))
            self.assertTrue(_compareResults(self.cal.parse('25/8/06',          start), (target, 1)))
            self.assertTrue(_compareResults(self.cal.parse('ao\xfbt 25, 2006', start), (target, 1)))
            self.assertTrue(_compareResults(self.cal.parse('ao\xfbt 25 2006',  start), (target, 1)))

            if self.mth > 8 or (self.mth == 8 and self.dy > 25):
                target = datetime.datetime(self.yr+1, 8, 25, self.hr, self.mn, self.sec).timetuple()
            else:
                target = datetime.datetime(self.yr, 8, 25,  self.hr, self.mn, self.sec).timetuple()

            self.assertTrue(_compareResults(self.cal.parse('25/8',  start), (target, 1)))
            self.assertTrue(_compareResults(self.cal.parse('25/08', start), (target, 1)))

    def testWeekDays(self):
        if self.ptc.localeID == 'fr_FR':
            start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()

            o1 = self.ptc.CurrentDOWParseStyle
            o2 = self.ptc.DOWParseStyle

              # set it up so the current dow returns current day
            self.ptc.CurrentDOWParseStyle = True
            self.ptc.DOWParseStyle        = 1

            for i in range(0,7):
                dow = self.ptc.shortWeekdays[i]

                result = self.cal.parse(dow, start)

                yr, mth, dy, hr, mn, sec, wd, yd, isdst = result[0]

                self.assertTrue(wd == i)

            self.ptc.CurrentDOWParseStyle = o1
            self.ptc.DOWParseStyle        = o2


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestGermanLocale

"""
Test parsing of simple date and times using the German locale
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.ptc = pdt.Constants('de_DE', usePyICU=False)
        self.cal = pdt.Calendar(self.ptc)

        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testTimes(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 23, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('23:00:00', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('23:00',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('2300',     start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 11, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('11:00:00', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1100',     start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 7, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('730',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('0730', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 17, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1730',   start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('173000', start), (target, 2)))

    def testDates(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(2006, 8, 25,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('25.08.2006', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25.8.06',    start), (target, 1)))

        if self.mth > 8 or (self.mth == 8 and self.dy > 25):
            target = datetime.datetime(self.yr+1, 8, 25,  self.hr, self.mn, self.sec).timetuple()
        else:
            target = datetime.datetime(self.yr, 8, 25,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('25.8',       start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25.08',      start), (target, 1)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestInc

"""
Test Calendar.Inc() routine
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(target, value):
    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) #and (t_wd == v_wd) and (t_yd == v_yd))


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testIncMonths(self):
        s = datetime.datetime(2006, 1, 1, 12, 0, 0)
        t = datetime.datetime(2006, 2, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, month=1).timetuple(), t.timetuple()))

        s = datetime.datetime(2006, 12, 1, 12, 0, 0)
        t = datetime.datetime(2007,  1, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, month=1).timetuple(), t.timetuple()))

        # leap year, Feb 1
        s = datetime.datetime(2008, 2, 1, 12, 0, 0)
        t = datetime.datetime(2008, 3, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, month=1).timetuple(), t.timetuple()))

        # leap year, Feb 29
        s = datetime.datetime(2008, 2, 29, 12, 0, 0)
        t = datetime.datetime(2008, 3, 29, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, month=1).timetuple(), t.timetuple()))

        s = datetime.datetime(2006,  1, 1, 12, 0, 0)
        t = datetime.datetime(2005, 12, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, month=-1).timetuple(), t.timetuple()))

        # End of month Jan 31 to Feb - Febuary only has 28 days
        s = datetime.datetime(2006, 1, 31, 12, 0, 0)
        t = datetime.datetime(2006, 2, 28, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, month=1).timetuple(), t.timetuple()))

        # walk thru months and make sure month increment doesn't set the day
        # to be past the last day of the new month
        # think Jan transition to Feb - 31 days to 28 days
        for m in range(1, 11):
            d = self.cal.ptc.daysInMonth(m, 2006)
            s = datetime.datetime(2006, m, d, 12, 0, 0)

            if d > self.cal.ptc.daysInMonth(m + 1, 2006):
                d = self.cal.ptc.daysInMonth(m + 1, 2006)

            t = datetime.datetime(2006, m + 1, d, 12, 0, 0)

            self.assertTrue(_compareResults(self.cal.inc(s, month=1).timetuple(), t.timetuple()))

    def testIncYears(self):
        s = datetime.datetime(2006, 1, 1, 12, 0, 0)
        t = datetime.datetime(2007, 1, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, year=1).timetuple(), t.timetuple()))

        s = datetime.datetime(2006, 1, 1, 12, 0, 0)
        t = datetime.datetime(2008, 1, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, year=2).timetuple(), t.timetuple()))

        s = datetime.datetime(2006, 12, 31, 12, 0, 0)
        t = datetime.datetime(2007, 12, 31, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, year=1).timetuple(), t.timetuple()))

        s = datetime.datetime(2006, 12, 31, 12, 0, 0)
        t = datetime.datetime(2005, 12, 31, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, year=-1).timetuple(), t.timetuple()))

        s = datetime.datetime(2008, 3, 1, 12, 0, 0)
        t = datetime.datetime(2009, 3, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, year=1).timetuple(), t.timetuple()))

        s = datetime.datetime(2008, 3, 1, 12, 0, 0)
        t = datetime.datetime(2007, 3, 1, 12, 0, 0)
        self.assertTrue(_compareResults(self.cal.inc(s, year=-1).timetuple(), t.timetuple()))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestMultiple

"""
Test parsing of strings with multiple chunks
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testSimpleMultipleItems(self):
        s = datetime.datetime.now()
        t = self.cal.inc(s, year=3) + datetime.timedelta(days=5, weeks=2)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('3 years 2 weeks 5 days', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('3years 2weeks 5days',    start), (target, 1)))

    def testMultipleItemsSingleCharUnits(self):
        s = datetime.datetime.now()
        t = self.cal.inc(s, year=3) + datetime.timedelta(days=5, weeks=2)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('3 y 2 w 5 d', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('3y 2w 5d',    start), (target, 1)))

        t      = self.cal.inc(s, year=3) + datetime.timedelta(hours=5, minutes=50)
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('3y 5h 50m', start), (target, 3)))

    def testMultipleItemsWithPunctuation(self):
        s = datetime.datetime.now()
        t = self.cal.inc(s, year=3) + datetime.timedelta(days=5, weeks=2)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('3 years, 2 weeks, 5 days',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('3 years, 2 weeks and 5 days', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('3y, 2w, 5d ',                 start), (target, 1)))

    def testUnixATStyle(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(days=3)

        t = t.replace(hour=16, minute=0, second=0)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('4pm + 3 days', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('4pm +3 days',  start), (target, 3)))

    def testUnixATStyleNegative(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(days=-3)

        t = t.replace(hour=16, minute=0, second=0)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('4pm - 3 days', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('4pm -3 days',  start), (target, 3)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestNlp

"""
Test parsing of strings that are phrases
"""

import unittest, time, datetime
import parsedatetime as pdt


# a special compare function for nlp returned data
def _compareResults(result, check, dateOnly=False, debug=False):
    target = result
    value = check

    if target is None and value is None:
        return True

    if (target is None and value is not None) or (target is not None and value is None):
        return False

    if len(target) != len(value):
        return False

    for i in range(0, len(target)):
        target_date = target[i][0]
        value_date = value[i][0]

        if target_date.year != value_date.year or target_date.month != value_date.month or target_date.day != value_date.day or target_date.hour != value_date.hour or target_date.minute != value_date.minute:
            return False
        if target[i][1] != value[i][1]:
            return False
        if target[i][2] != value[i][2]:
            return False
        if target[i][3] != value[i][3]:
            return False
        if target[i][4] != value[i][4]:
            return False

    return True

class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testNlp(self):
        # note: these tests do not need to be as dynamic as the others because this is still based
        #       on the parse() function, so all tests of the actual processing of the datetime
        #       value returned are applicable to this. Here we are concerned with ensuring the
        #       correct portions of text and their positions are extracted and processed.
        start  = datetime.datetime(2013, 8, 1, 21, 25, 0).timetuple()
        target = ((datetime.datetime(2013, 8, 5, 20, 0), 3, 17, 37, 'At 8PM on August 5th'),
                  (datetime.datetime(2013, 8, 9, 21, 0), 2, 72, 90, 'next Friday at 9PM'),
                  (datetime.datetime(2013, 8, 1, 21, 30, 0), 2, 120, 132, 'in 5 minutes'))

        # positive testing
        self.assertTrue(_compareResults(self.cal.nlp("I'm so excited!! At 8PM on August 5th i'm going to fly to Florida"
                                                     ". Then next Friday at 9PM i'm going to Dog n Bone! And in 5 "
                                                     "minutes I'm going to eat some food!", start), target))

        target = datetime.datetime(self.yr, self.mth, self.dy, 17, 0, 0).timetuple()

        # negative testing - no matches should return None
        self.assertTrue(_compareResults(self.cal.nlp("I'm so excited!! So many things that are going to happen!!", start), None))

        # quotes should not interfere with datetime language recognition
        target = self.cal.nlp("I'm so excited!! At '8PM on August 5th' i'm going to fly to Florida"
                                                     ". Then 'next Friday at 9PM' i'm going to Dog n Bone! And in '5 "
                                                     "minutes' I'm going to eat some food!", start)

        self.assertTrue(target[0][4] == "At '8PM on August 5th")
        self.assertTrue(target[1][4] == "next Friday at 9PM")
        self.assertTrue(target[2][4] == "in '5 minutes")
########NEW FILE########
__FILENAME__ = TestPhrases

"""
Test parsing of strings that are phrases
"""

import unittest, time, datetime
import parsedatetime as pdt

  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check, dateOnly=False, debug=False):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    if dateOnly:
        return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy)) and (t_flag == v_flag)
    else:
        return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
                (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testPhrases(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 16, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('flight from SFO at 4pm', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 17, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('eod',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('meeting eod', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('eod meeting', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 17, 0, 0) + datetime.timedelta(days=1)
        target = target.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('tomorrow eod', start), (target, 3)))
        self.assertTrue(_compareResults(self.cal.parse('eod tomorrow', start), (target, 3)))

    def testPhraseWithDays_DOWStyle_1_False(self):
        s = datetime.datetime.now()

          # find out what day we are currently on
          # and determine what the next day of week is
        t      = s + datetime.timedelta(days=1)
        start  = s.timetuple()

        (yr, mth, dy, _, _, _, wd, yd, isdst) = t.timetuple()

        target = (yr, mth, dy, 17, 0, 0, wd, yd, isdst)

        d = self.wd + 1
        if d > 6:
            d = 0

        day = self.cal.ptc.Weekdays[d]

        self.assertTrue(_compareResults(self.cal.parse('eod %s' % day, start), (target, 3)))

          # find out what day we are currently on
          # and determine what the previous day of week is
        t = s + datetime.timedelta(days=6)

        (yr, mth, dy, hr, mn, sec, wd, yd, isdst) = t.timetuple()

        target = (yr, mth, dy, 17, 0, 0, wd, yd, isdst)

        d = self.wd - 1
        if d < 0:
            d = 6

        day = self.cal.ptc.Weekdays[d]

        self.assertTrue(_compareResults(self.cal.parse('eod %s' % day, start), (target, 3)))

    def testEndOfPhrases(self):
        s = datetime.datetime.now()

          # find out what month we are currently on
          # set the day to 1 and then go back a day
          # to get the end of the current month
        (yr, mth, _, hr, mn, sec, _, _, _) = s.timetuple()

        mth += 1
        if mth > 12:
            mth = 1
            yr += 1

        t = datetime.datetime(yr, mth, 1, 9, 0, 0) + datetime.timedelta(days=-1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('eom',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('meeting eom', start), (target, 2)))

        s = datetime.datetime.now()

        (yr, mth, dy, hr, mn, sec, wd, yd, isdst) = s.timetuple()

        t = datetime.datetime(yr, 12, 31, 9, 0, 0)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('eoy',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('meeting eoy', start), (target, 2)))

    def testLastPhrases(self):
        for day in (11, 12, 13, 14, 15, 16, 17):
            start  = datetime.datetime(2012, 11, day, 9, 0, 0)

            (yr, mth, dy, _, _, _, wd, yd, isdst) = start.timetuple()

            n = 4 - wd
            if n >= 0:
                n -= 7

            target = start + datetime.timedelta(days=n)

            #print '*********', start, target, n, self.cal.parse('last friday', start.timetuple())

            self.assertTrue(_compareResults(self.cal.parse('last friday', start.timetuple()), (target.timetuple(), 1), dateOnly=True))
########NEW FILE########
__FILENAME__ = TestRanges

"""
Test parsing of simple date and times
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    targetStart, targetEnd, t_flag = result
    valueStart, valueEnd,  v_flag = check

    t1_yr, t1_mth, t1_dy, t1_hr, t1_min, _, _, _, _ = targetStart
    v1_yr, v1_mth, v1_dy, v1_hr, v1_min, _, _, _, _ = valueStart

    t2_yr, t2_mth, t2_dy, t2_hr, t2_min, _, _, _, _ = targetEnd
    v2_yr, v2_mth, v2_dy, v2_hr, v2_min, _, _, _, _ = valueEnd

    return ((t1_yr == v1_yr) and (t1_mth == v1_mth) and (t1_dy == v1_dy) and (t1_hr == v1_hr) and
            (t1_min == v1_min) and (t2_yr == v2_yr) and (t2_mth == v2_mth) and (t2_dy == v2_dy) and
            (t2_hr == v2_hr) and (t2_min == v2_min) and (t_flag == v_flag))


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testTimes(self):
        start = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()

        targetStart = datetime.datetime(self.yr, self.mth, self.dy, 14, 0, 0).timetuple()
        targetEnd   = datetime.datetime(self.yr, self.mth, self.dy, 17, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.evalRanges("2 pm - 5:30 pm",          start), (targetStart, targetEnd, 2)))
        self.assertTrue(_compareResults(self.cal.evalRanges("2pm - 5:30pm",            start), (targetStart, targetEnd, 2)))
        self.assertTrue(_compareResults(self.cal.evalRanges("2:00:00 pm - 5:30:00 pm", start), (targetStart, targetEnd, 2)))
        self.assertTrue(_compareResults(self.cal.evalRanges("2 - 5:30pm",              start), (targetStart, targetEnd, 2)))
        self.assertTrue(_compareResults(self.cal.evalRanges("14:00 - 17:30",           start), (targetStart, targetEnd, 2)))

        targetStart = datetime.datetime(self.yr, self.mth, self.dy, 10, 0, 0).timetuple()
        targetEnd   = datetime.datetime(self.yr, self.mth, self.dy, 13, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.evalRanges("10AM - 1:30PM",            start), (targetStart, targetEnd, 2)))
        self.assertTrue(_compareResults(self.cal.evalRanges("10:00:00 am - 1:30:00 pm", start), (targetStart, targetEnd, 2)))
        self.assertTrue(_compareResults(self.cal.evalRanges("10:00 - 13:30",            start), (targetStart, targetEnd, 2)))

        targetStart = datetime.datetime(self.yr, self.mth, self.dy, 15, 30, 0).timetuple()
        targetEnd   = datetime.datetime(self.yr, self.mth, self.dy, 17, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.evalRanges("today 3:30-5PM", start), (targetStart, targetEnd, 2)))

    def testDates(self):
        start = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()

        targetStart = datetime.datetime(2006, 8, 29, self.hr, self.mn, self.sec).timetuple()
        targetEnd   = datetime.datetime(2006, 9, 2,self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.evalRanges("August 29, 2006 - September 2, 2006", start), (targetStart, targetEnd, 1)))
        self.assertTrue(_compareResults(self.cal.evalRanges("August 29 - September 2, 2006",       start), (targetStart, targetEnd, 1)))

        targetStart = datetime.datetime(2006, 8, 29, self.hr, self.mn, self.sec).timetuple()
        targetEnd   = datetime.datetime(2006, 9, 2, self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.evalRanges("08/29/06 - 09/02/06", start), (targetStart, targetEnd, 1)))


    #def testSubRanges(self):
    #    start = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()

    #    targetStart = datetime.datetime(2006, 8, 1, 9, 0, 0).timetuple()
    #    targetEnd   = datetime.datetime(2006, 8, 15, 9, 0, 0).timetuple()

    #    self.assertTrue(_compareResults(self.cal.evalRanges("August 1-15, 2006", start), (targetStart, targetEnd, 1)))


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = TestSimpleDateTimes

"""
Test parsing of simple date and times
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):
    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testDays(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(days=1)

        start  = s.timetuple()
        target = t.timetuple()

        d = self.wd + 1

        if d > 6:
            d = 0

        day = self.cal.ptc.Weekdays[d]

        self.assertTrue(_compareResults(self.cal.parse(day, start), (target, 1)))

        t = s + datetime.timedelta(days=6)

        target = t.timetuple()

        d = self.wd - 1

        if d < 0:
            d = 6

        day = self.cal.ptc.Weekdays[d]

        self.assertTrue(_compareResults(self.cal.parse(day, start), (target, 1)))

    def testTimes(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 23, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('11:00:00 PM', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00 PM',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11 PM',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11PM',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('2300',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('23:00',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11p',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11pm',        start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 11, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('11:00:00 AM', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00 AM',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11 AM',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11AM',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1100',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11:00',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11a',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('11am',        start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 7, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('730',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('0730', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 17, 30, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1730',   start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('173000', start), (target, 2)))

    def testDates(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(2006, 8, 25,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('08/25/2006',      start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('08.25.2006',      start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('8/25/06',         start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('August 25, 2006', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25, 2006',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 25, 2006',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('August 25 2006',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25 2006',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 25 2006',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25 August 2006',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('25 Aug 2006',     start), (target, 1)))

        if self.mth > 8 or (self.mth == 8 and self.dy > 25):
            target = datetime.datetime(self.yr + 1, 8, 25,  self.hr, self.mn, self.sec).timetuple()
        else:
            target = datetime.datetime(self.yr, 8, 25,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('8/25',      start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('8.25',      start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('08/25',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('August 25', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 25',   start), (target, 1)))

        # added test to ensure 4-digit year is recognized in the absence of day
        target = datetime.datetime(2013, 8, 1,  self.hr, self.mn, self.sec).timetuple()
        self.assertTrue(_compareResults(self.cal.parse('Aug. 2013',   start), (target, 1)))

    def testLeapDays(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(2000, 2, 29,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('02/29/2000', start), (target, 1)))

        target = datetime.datetime(2004, 2, 29,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('02/29/2004', start), (target, 1)))

        target = datetime.datetime(2008, 2, 29,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('02/29/2008', start), (target, 1)))

        target = datetime.datetime(2012, 2, 29,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('02/29/2012', start), (target, 1)))

        dNormal = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        dLeap   = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

        for i in range(1,12):
            self.assertTrue(self.cal.ptc.daysInMonth(i, 1999), dNormal[i - 1])
            self.assertTrue(self.cal.ptc.daysInMonth(i, 2000), dLeap[i - 1])
            self.assertTrue(self.cal.ptc.daysInMonth(i, 2001), dNormal[i - 1])
            self.assertTrue(self.cal.ptc.daysInMonth(i, 2002), dNormal[i - 1])
            self.assertTrue(self.cal.ptc.daysInMonth(i, 2003), dNormal[i - 1])
            self.assertTrue(self.cal.ptc.daysInMonth(i, 2004), dLeap[i - 1])
            self.assertTrue(self.cal.ptc.daysInMonth(i, 2005), dNormal[i - 1])

    def testDaySuffixes(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(2008, 8, 22,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('August 22nd, 2008', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 22nd, 2008',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 22nd, 2008',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('August 22nd 2008',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 22nd 2008',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 22nd 2008',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('22nd August 2008',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('22nd Aug 2008',     start), (target, 1)))

        target = datetime.datetime(1949, 12, 31,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('December 31st, 1949', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Dec 31st, 1949',      start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('December 31st 1949',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Dec 31st 1949',       start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('31st December 1949',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('31st Dec 1949',       start), (target, 1)))

        target = datetime.datetime(2008, 8, 23,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('August 23rd, 2008', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 23rd, 2008',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 23rd, 2008',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('August 23rd 2008',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 23rd 2008',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 23rd 2008',    start), (target, 1)))

        target = datetime.datetime(2008, 8, 25,  self.hr, self.mn, self.sec).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('August 25th, 2008', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25th, 2008',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 25th, 2008',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('August 25th 2008',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug 25th 2008',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('Aug. 25th 2008',    start), (target, 1)))

    def testSpecialTimes(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 6, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('morning', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 8, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('breakfast', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 12, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('lunch', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 18, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('evening', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 19,0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('dinner', start), (target, 2)))

        target = datetime.datetime(self.yr, self.mth, self.dy, 21, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('night',   start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('tonight', start), (target, 2)))

    def testMidnight(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 0, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('midnight',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12:00:00 AM', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12:00 AM',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12 AM',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12AM',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12am',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12a',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('0000',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('00:00',       start), (target, 2)))

    def testNoon(self):
        start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
        target = datetime.datetime(self.yr, self.mth, self.dy, 12, 0, 0).timetuple()

        self.assertTrue(_compareResults(self.cal.parse('noon',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12:00:00 PM', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12:00 PM',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12 PM',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12PM',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12pm',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12p',         start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1200',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('12:00',       start), (target, 2)))

    # def testMonths(self):
    #
    #     start  = datetime.datetime(self.yr, self.mth, self.dy, self.hr, self.mn, self.sec).timetuple()
    #
    #     target = datetime.datetime(self.yr, self.mth, self.dy, 12, 0, 0).timetuple()
    #
    #     self.assertTrue(_compareResults(self.cal.parse('jun',        start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12:00:00 PM', start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12:00 PM',    start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12 PM',       start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12PM',        start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12pm',        start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12p',         start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('1200',        start), (target, 2)))
    #     self.assertTrue(_compareResults(self.cal.parse('12:00',       start), (target, 2)))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestSimpleOffsets

"""
Test parsing of 'simple' offsets
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testNow(self):
        s = datetime.datetime.now()

        start = s.timetuple()
        target = s.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('now', start), (target, 2)))

    def testMinutesFromNow(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(minutes=5)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('5 minutes from now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 min from now',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5m from now',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in 5 minutes',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in 5 min',           start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 minutes',          start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 min',              start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5m',                 start), (target, 2)))

        self.assertTrue(_compareResults(self.cal.parse('five minutes from now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five min from now',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in five minutes',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in five min',           start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five minutes',          start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five min',              start), (target, 2)))

    def testMinutesBeforeNow(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(minutes=-5)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('5 minutes before now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 min before now',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5m before now',        start), (target, 2)))

        self.assertTrue(_compareResults(self.cal.parse('five minutes before now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five min before now',     start), (target, 2)))

    def testWeekFromNow(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(weeks=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('in 1 week',           start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 week from now',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('in one week',         start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('one week from now',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('in 7 days',           start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('7 days from now',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('in seven days',       start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('seven days from now', start), (target, 1)))
        #self.assertTrue(_compareResults(self.cal.parse('next week',           start), (target, 1)))

    def testWeekBeforeNow(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(weeks=-1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 week before now',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('one week before now',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('7 days before now',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('seven days before now', start), (target, 1)))
        #self.assertTrue(_compareResults(self.cal.parse('last week',              tart), (target, 1)))

    def testSpecials(self):
        s = datetime.datetime.now()
        t = datetime.datetime(self.yr, self.mth, self.dy, 9, 0, 0) + datetime.timedelta(days=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('tomorrow', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('next day', start), (target, 1)))

        t      = datetime.datetime(self.yr, self.mth, self.dy, 9, 0, 0) + datetime.timedelta(days=-1)
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('yesterday', start), (target, 1)))

        t      = datetime.datetime(self.yr, self.mth, self.dy, 9, 0, 0)
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('today', start), (target, 1)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestSimpleOffsetsHours
"""
Test parsing of 'simple' offsets
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testHoursFromNow(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(hours=5)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('5 hours from now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 hour from now',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 hr from now',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in 5 hours',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in 5 hour',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 hours',          start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 hr',             start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5h',               start), (target, 2)))

        self.assertTrue(_compareResults(self.cal.parse('five hours from now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hour from now',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hr from now',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in five hours',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('in five hour',        start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hours',          start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hr',             start), (target, 2)))

    def testHoursBeforeNow(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(hours=-5)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('5 hours before now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 hr before now',    start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5h before now',      start), (target, 2)))

        self.assertTrue(_compareResults(self.cal.parse('five hours before now', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hr before now',    start), (target, 2)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestSimpleOffsetsNoon

"""
Test parsing of 'simple' offsets
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testOffsetAfterNoon(self):
        s = datetime.datetime(self.yr, self.mth, self.dy, 10, 0, 0)
        t = datetime.datetime(self.yr, self.mth, self.dy, 12, 0, 0) + datetime.timedelta(hours=5)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('5 hours after 12pm',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hours after 12pm',  start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours after 12 pm',    start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours after 12:00pm',  start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours after 12:00 pm', start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours after noon',     start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours from noon',      start), (target, 2)))

    def testOffsetBeforeNoon(self):
        s = datetime.datetime.now()
        t = datetime.datetime(self.yr, self.mth, self.dy, 12, 0, 0) + datetime.timedelta(hours=-5)

        start  = s.timetuple()
        target = t.timetuple()

        #self.assertTrue(_compareResults(self.cal.parse('5 hours before noon',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('5 hours before 12pm',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('five hours before 12pm',  start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours before 12 pm',    start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours before 12:00pm',  start), (target, 2)))
        #self.assertTrue(_compareResults(self.cal.parse('5 hours before 12:00 pm', start), (target, 2)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = TestUnits

"""
Test parsing of units
"""

import unittest, time, datetime
import parsedatetime as pdt


  # a special compare function is used to allow us to ignore the seconds as
  # the running of the test could cross a minute boundary
def _compareResults(result, check):
    target, t_flag = result
    value,  v_flag = check

    t_yr, t_mth, t_dy, t_hr, t_min, _, _, _, _ = target
    v_yr, v_mth, v_dy, v_hr, v_min, _, _, _, _ = value

    return ((t_yr == v_yr) and (t_mth == v_mth) and (t_dy == v_dy) and
            (t_hr == v_hr) and (t_min == v_min)) and (t_flag == v_flag)


class test(unittest.TestCase):

    def setUp(self):
        self.cal = pdt.Calendar()
        self.yr, self.mth, self.dy, self.hr, self.mn, self.sec, self.wd, self.yd, self.isdst = time.localtime()

    def testMinutes(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(minutes=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 minute',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1 minutes', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1 min',     start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1min',      start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1 m',       start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1m',        start), (target, 2)))

    def testHours(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(hours=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 hour',  start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1 hours', start), (target, 2)))
        self.assertTrue(_compareResults(self.cal.parse('1 hr',    start), (target, 2)))

    def testDays(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(days=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 day',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 days', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1days',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 dy',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 d',    start), (target, 1)))

    def testNegativeDays(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(days=-1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('-1 day',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('-1 days', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('-1days',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('-1 dy',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('-1 d',    start), (target, 1)))

        self.assertTrue(_compareResults(self.cal.parse('- 1 day',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('- 1 days', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('- 1days',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('- 1 dy',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('- 1 d',    start), (target, 1)))

    def testWeeks(self):
        s = datetime.datetime.now()
        t = s + datetime.timedelta(weeks=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 week',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1week',   start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 weeks', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 wk',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 w',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1w',      start), (target, 1)))

    def testMonths(self):
        s = datetime.datetime.now()
        t = self.cal.inc(s, month=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 month',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 months', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1month',   start), (target, 1)))

    def testYears(self):
        s = datetime.datetime.now()
        t = self.cal.inc(s, year=1)

        start  = s.timetuple()
        target = t.timetuple()

        self.assertTrue(_compareResults(self.cal.parse('1 year',  start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 years', start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 yr',    start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1 y',     start), (target, 1)))
        self.assertTrue(_compareResults(self.cal.parse('1y',      start), (target, 1)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = run_tests
import sys, os

from unittest import TestLoader, main

class ScanningLoader(TestLoader):

    def loadTestsFromModule(self, module):
        """
        Return a suite of all tests cases contained in the given module
        """
        tests = [TestLoader.loadTestsFromModule(self,module)]

        if hasattr(module, "additional_tests"):
            tests.append(module.additional_tests())

        if hasattr(module, '__path__'):
            for dir in module.__path__:
                for file in os.listdir(dir):
                    if file.endswith('.py') and file!='__init__.py':
                        if file.lower().startswith('test'):
                            submodule = module.__name__+'.'+file[:-3]
                        else:
                            continue
                    else:
                        subpkg = os.path.join(dir,file,'__init__.py')

                        if os.path.exists(subpkg):
                            submodule = module.__name__+'.'+file
                        else:
                            continue

                    tests.append(self.loadTestsFromName(submodule))

        if len(tests)>1:
            return self.suiteClass(tests)
        else:
            return tests[0] # don't create a nested suite for only one return


if __name__ == '__main__':
    if len(sys.argv) == 1:
        testname = 'parsedatetime'
    else:
        testname = None

    main(module=testname, testLoader=ScanningLoader())


########NEW FILE########
