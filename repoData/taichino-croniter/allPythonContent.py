__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os
import shutil
import sys
import tempfile

from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --find-links to point to local resources, you can keep 
this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                  help=("Specify the path to the buildout configuration "
                        "file to be used."))
parser.add_option("-f", "--find-links",
                  help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install setuptools

to_reload = False
try:
    import pkg_resources
    import setuptools
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    # XXX use a more permanent ez_setup.py URL when available.
    exec(urlopen('https://bitbucket.org/pypa/setuptools/raw/0.7.2/ez_setup.py'
                ).read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

setuptools_path = ws.find(
    pkg_resources.Requirement.parse('setuptools')).location

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setuptools_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=setuptools_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = croniter
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function
import re
from time import time, mktime
import datetime
from dateutil.relativedelta import relativedelta

search_re = re.compile(r'^([^-]+)-([^-/]+)(/(.*))?$')
only_int_re = re.compile(r'^\d+$')
any_int_re = re.compile(r'^\d+')
star_or_int_re = re.compile(r'^(\d+|\*)$')

__all__ = ('croniter',)


class croniter(object):
    MONTHS_IN_YEAR = 12
    RANGES = (
        (0, 59),
        (0, 23),
        (1, 31),
        (1, 12),
        (0, 6),
        (0, 59)
    )
    DAYS = (
        31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    )

    ALPHACONV = (
        {},
        {},
        {},
        {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
         'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12},
        {'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6},
        {}
    )

    LOWMAP = (
        {},
        {},
        {0: 1},
        {0: 1},
        {7: 0},
        {},
    )

    bad_length = 'Exactly 5 or 6 columns has to be specified for iterator' \
                 'expression.'

    def __init__(self, expr_format, start_time=time()):
        self.tzinfo = None
        if isinstance(start_time, datetime.datetime):
            self.tzinfo = start_time.tzinfo
            start_time = mktime(start_time.timetuple())

        self.cur = start_time
        self.exprs = expr_format.split()

        if len(self.exprs) != 5 and len(self.exprs) != 6:
            raise ValueError(self.bad_length)

        expanded = []

        for i, expr in enumerate(self.exprs):
            e_list = expr.split(',')
            res = []

            while len(e_list) > 0:
                e = e_list.pop()
                t = re.sub(r'^\*(/.+)$', r'%d-%d\1' % (
                    self.RANGES[i][0],
                    self.RANGES[i][1]),
                    str(e))
                m = search_re.search(t)

                if m:
                    (low, high, step) = m.group(1), m.group(2), m.group(4) or 1

                    if not any_int_re.search(low):
                        low = self.ALPHACONV[i][low.lower()]

                    if not any_int_re.search(high):
                        high = self.ALPHACONV[i][high.lower()]

                    if (
                        not low or not high or int(low) > int(high)
                        or not only_int_re.search(str(step))
                    ):
                        raise ValueError(
                            "[{0}] is not acceptable".format(expr_format))

                    low, high, step = map(int, [low, high, step])
                    e_list += range(low, high + 1, step)
                    # other solution
                    #try:
                    #    for j in xrange(int(low), int(high) + 1):
                    #        if j % int(step) == 0:
                    #            e_list.append(j)
                    #except NameError:
                    #    for j in range(int(low), int(high) + 1):
                    #        if j % int(step) == 0:
                    #            e_list.append(j)
                else:
                    if not star_or_int_re.search(t):
                        t = self.ALPHACONV[i][t.lower()]

                    try:
                        t = int(t)
                    except:
                        pass

                    if t in self.LOWMAP[i]:
                        t = self.LOWMAP[i][t]

                    if t != '*' and (int(t) < self.RANGES[i][0] or
                                     int(t) > self.RANGES[i][1]):
                        raise ValueError(
                            "[{0}] is not acceptable, out of range".format(
                                expr_format))

                    res.append(t)

            res.sort()
            expanded.append(['*'] if (len(res) == 1
                                      and res[0] == '*')
                            else res)
        self.expanded = expanded

    def get_next(self, ret_type=float):
        return self._get_next(ret_type, is_prev=False)

    def get_prev(self, ret_type=float):
        return self._get_next(ret_type, is_prev=True)

    def get_current(self, ret_type=float):
        if ret_type == datetime.datetime:
            return datetime.datetime.fromtimestamp(self.cur)
        return self.cur

    # iterator protocol, to enable direct use of croniter
    # objects in a loop, like "for dt in croniter('5 0 * * *'): ..."
    # or for combining multiple croniters into single
    # dates feed using 'itertools' module
    def __iter__(self):
        return self
    __next__ = next = get_next

    def all_next(self, ret_type=float):
        '''Generator of all consecutive dates. Can be used instead of
        implicit call to __iter__, whenever non-default
        'ret_type' has to be specified.
        '''
        while True:
            yield self._get_next(ret_type, is_prev=False)

    def all_prev(self, ret_type=float):
        '''Generator of all previous dates.'''
        while True:
            yield self._get_next(ret_type, is_prev=True)

    iter = all_next  # alias, you can call .iter() instead of .all_next()

    def _get_next(self, ret_type=float, is_prev=False):
        expanded = self.expanded[:]

        if ret_type not in (float, datetime.datetime):
            raise TypeError("Invalid ret_type, only 'float' or 'datetime' "
                            "is acceptable.")

        if expanded[2][0] != '*' and expanded[4][0] != '*':
            bak = expanded[4]
            expanded[4] = ['*']
            t1 = self._calc(self.cur, expanded, is_prev)
            expanded[4] = bak
            expanded[2] = ['*']

            t2 = self._calc(self.cur, expanded, is_prev)
            if not is_prev:
                result = t1 if t1 < t2 else t2
            else:
                result = t1 if t1 > t2 else t2
        else:
            result = self._calc(self.cur, expanded, is_prev)
        self.cur = result

        if ret_type == datetime.datetime:
            result = datetime.datetime.fromtimestamp(result)
            if self.tzinfo:
                result = self.tzinfo.localize(result)
        return result

    def _calc(self, now, expanded, is_prev):
        if is_prev:
            nearest_diff_method = self._get_prev_nearest_diff
            sign = -1
        else:
            nearest_diff_method = self._get_next_nearest_diff
            sign = 1

        offset = len(expanded) == 6 and 1 or 60
        dst = now = datetime.datetime.fromtimestamp(now + sign * offset)

        day, month, year = dst.day, dst.month, dst.year
        current_year = now.year
        DAYS = self.DAYS

        def proc_month(d):
            if expanded[3][0] != '*':
                diff_month = nearest_diff_method(
                    d.month, expanded[3], self.MONTHS_IN_YEAR)
                days = DAYS[month - 1]
                if month == 2 and self.is_leap(year) is True:
                    days += 1

                reset_day = 1

                if diff_month is not None and diff_month != 0:
                    if is_prev:
                        d += relativedelta(months=diff_month)
                        reset_day = DAYS[d.month - 1]
                        d += relativedelta(
                            day=reset_day, hour=23, minute=59, second=59)
                    else:
                        d += relativedelta(months=diff_month, day=reset_day,
                                           hour=0, minute=0, second=0)
                    return True, d
            return False, d

        def proc_day_of_month(d):
            if expanded[2][0] != '*':
                days = DAYS[month - 1]
                if month == 2 and self.is_leap(year) is True:
                    days += 1

                if is_prev:
                    days_in_prev_month = DAYS[
                        (month - 2) % self.MONTHS_IN_YEAR]
                    diff_day = nearest_diff_method(
                        d.day, expanded[2], days_in_prev_month)
                else:
                    diff_day = nearest_diff_method(d.day, expanded[2], days)

                if diff_day is not None and diff_day != 0:
                    if is_prev:
                        d += relativedelta(
                            days=diff_day, hour=23, minute=59, second=59)
                    else:
                        d += relativedelta(
                            days=diff_day, hour=0, minute=0, second=0)
                    return True, d
            return False, d

        def proc_day_of_week(d):
            if expanded[4][0] != '*':
                diff_day_of_week = nearest_diff_method(
                    d.isoweekday() % 7, expanded[4], 7)
                if diff_day_of_week is not None and diff_day_of_week != 0:
                    if is_prev:
                        d += relativedelta(days=diff_day_of_week,
                                           hour=23, minute=59, second=59)
                    else:
                        d += relativedelta(days=diff_day_of_week,
                                           hour=0, minute=0, second=0)
                    return True, d
            return False, d

        def proc_hour(d):
            if expanded[1][0] != '*':
                diff_hour = nearest_diff_method(d.hour, expanded[1], 24)
                if diff_hour is not None and diff_hour != 0:
                    if is_prev:
                        d += relativedelta(
                            hours=diff_hour, minute=59, second=59)
                    else:
                        d += relativedelta(hours=diff_hour, minute=0, second=0)
                    return True, d
            return False, d

        def proc_minute(d):
            if expanded[0][0] != '*':
                diff_min = nearest_diff_method(d.minute, expanded[0], 60)
                if diff_min is not None and diff_min != 0:
                    if is_prev:
                        d += relativedelta(minutes=diff_min, second=59)
                    else:
                        d += relativedelta(minutes=diff_min, second=0)
                    return True, d
            return False, d

        def proc_second(d):
            if len(expanded) == 6:
                if expanded[5][0] != '*':
                    diff_sec = nearest_diff_method(d.second, expanded[5], 60)
                    if diff_sec is not None and diff_sec != 0:
                        d += relativedelta(seconds=diff_sec)
                        return True, d
            else:
                d += relativedelta(second=0)
            return False, d

        procs = [proc_month,
                 proc_day_of_month,
                 proc_day_of_week,
                 proc_hour,
                 proc_minute,
                 proc_second]

        while abs(year - current_year) <= 1:
            next = False
            for proc in procs:
                (changed, dst) = proc(dst)
                if changed:
                    next = True
                    break
            if next:
                continue
            return mktime(dst.timetuple())

        raise Exception("failed to find prev date")

    def _get_next_nearest(self, x, to_check):
        small = [item for item in to_check if item < x]
        large = [item for item in to_check if item >= x]
        large.extend(small)
        return large[0]

    def _get_prev_nearest(self, x, to_check):
        small = [item for item in to_check if item <= x]
        large = [item for item in to_check if item > x]
        small.reverse()
        large.reverse()
        small.extend(large)
        return small[0]

    def _get_next_nearest_diff(self, x, to_check, range_val):
        for i, d in enumerate(to_check):
            if d >= x:
                return d - x
        return to_check[0] - x + range_val

    def _get_prev_nearest_diff(self, x, to_check, range_val):
        candidates = to_check[:]
        candidates.reverse()
        for d in candidates:
            if d <= x:
                return d - x
        candidate = candidates[0]
        for c in candidates:
            if c < range_val:
                candidate = c
                break

        return (candidate - x - range_val)

    def is_leap(self, year):
        if year % 400 == 0 or (year % 4 == 0 and year % 100 != 0):
            return True
        else:
            return False

if __name__ == '__main__':

    base = datetime.datetime(2010, 1, 25)
    itr = croniter('0 0 1 * *', base)
    n1 = itr.get_next(datetime.datetime)
    print(n1)

########NEW FILE########
__FILENAME__ = base
try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestCase(unittest.TestCase):
    '''
    We use this base class for all the tests in this package.
    If necessary, we can put common utility or setup code in here.
    '''

# vim:set ft=python:

########NEW FILE########
__FILENAME__ = test_croniter
#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from datetime import datetime
import pytz
from croniter import croniter

from croniter.tests import base


class CroniterTest(base.TestCase):

    def testSecond(self):
        base = datetime(2012, 4, 6, 13, 26, 10)
        itr = croniter('*/1 * * * * *', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(base.year, n1.year)
        self.assertEqual(base.month, n1.month)
        self.assertEqual(base.day, n1.day)
        self.assertEqual(base.hour, n1.hour)
        self.assertEqual(base.minute, n1.minute)
        self.assertEqual(base.second + 1, n1.second)

    def testSecondRepeat(self):
        base = datetime(2012, 4, 6, 13, 26, 36)
        itr = croniter('* * * * * */15', base)
        n1 = itr.get_next(datetime)
        n2 = itr.get_next(datetime)
        n3 = itr.get_next(datetime)
        self.assertEqual(base.year, n1.year)
        self.assertEqual(base.month, n1.month)
        self.assertEqual(base.day, n1.day)
        self.assertEqual(base.hour, n1.hour)
        self.assertEqual(base.minute, n1.minute)
        self.assertEqual(45, n1.second)
        self.assertEqual(base.year, n2.year)
        self.assertEqual(base.month, n2.month)
        self.assertEqual(base.day, n2.day)
        self.assertEqual(base.hour, n2.hour)
        self.assertEqual(base.minute + 1, n2.minute)
        self.assertEqual(0, n2.second)
        self.assertEqual(base.year, n3.year)
        self.assertEqual(base.month, n3.month)
        self.assertEqual(base.day, n3.day)
        self.assertEqual(base.hour, n3.hour)
        self.assertEqual(base.minute + 1, n3.minute)
        self.assertEqual(15, n3.second)

    def testMinute(self):
        # minute asterisk
        base = datetime(2010, 1, 23, 12, 18)
        itr = croniter('*/1 * * * *', base)
        n1 = itr.get_next(datetime)    # 19
        self.assertEqual(base.year, n1.year)
        self.assertEqual(base.month, n1.month)
        self.assertEqual(base.day, n1.day)
        self.assertEqual(base.hour, n1.hour)
        self.assertEqual(base.minute, n1.minute - 1)
        for i in range(39):  # ~ 58
            itr.get_next()
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.minute, 59)
        n3 = itr.get_next(datetime)
        self.assertEqual(n3.minute, 0)
        self.assertEqual(n3.hour, 13)

        itr = croniter('*/5 * * * *', base)
        n4 = itr.get_next(datetime)
        self.assertEqual(n4.minute, 20)
        for i in range(6):
            itr.get_next()
        n5 = itr.get_next(datetime)
        self.assertEqual(n5.minute, 55)
        n6 = itr.get_next(datetime)
        self.assertEqual(n6.minute, 0)
        self.assertEqual(n6.hour, 13)

    def testHour(self):
        base = datetime(2010, 1, 24, 12, 2)
        itr = croniter('0 */3 * * *', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.hour, 15)
        self.assertEqual(n1.minute, 0)
        for i in range(2):
            itr.get_next()
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.hour, 0)
        self.assertEqual(n2.day, 25)

    def testDay(self):
        base = datetime(2010, 2, 24, 12, 9)
        itr = croniter('0 0 */3 * *', base)
        n1 = itr.get_next(datetime)
        # 1 4 7 10 13 16 19 22 25 28
        self.assertEqual(n1.day, 25)
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.day, 28)
        n3 = itr.get_next(datetime)
        self.assertEqual(n3.day, 1)
        self.assertEqual(n3.month, 3)

        # test leap year
        base = datetime(1996, 2, 27)
        itr = croniter('0 0 * * *', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.day, 28)
        self.assertEqual(n1.month, 2)
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.day, 29)
        self.assertEqual(n2.month, 2)

        base2 = datetime(2000, 2, 27)
        itr2 = croniter('0 0 * * *', base2)
        n3 = itr2.get_next(datetime)
        self.assertEqual(n3.day, 28)
        self.assertEqual(n3.month, 2)
        n4 = itr2.get_next(datetime)
        self.assertEqual(n4.day, 29)
        self.assertEqual(n4.month, 2)

    def testWeekDay(self):
        base = datetime(2010, 2, 25)
        itr = croniter('0 0 * * sat', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.isoweekday(), 6)
        self.assertEqual(n1.day, 27)
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.isoweekday(), 6)
        self.assertEqual(n2.day, 6)
        self.assertEqual(n2.month, 3)

        base = datetime(2010, 1, 25)
        itr = croniter('0 0 1 * wed', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.month, 1)
        self.assertEqual(n1.day, 27)
        self.assertEqual(n1.year, 2010)
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.month, 2)
        self.assertEqual(n2.day, 1)
        self.assertEqual(n2.year, 2010)
        n3 = itr.get_next(datetime)
        self.assertEqual(n3.month, 2)
        self.assertEqual(n3.day, 3)
        self.assertEqual(n3.year, 2010)

    def testMonth(self):
        base = datetime(2010, 1, 25)
        itr = croniter('0 0 1 * *', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.month, 2)
        self.assertEqual(n1.day, 1)
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, 1)
        for i in range(8):
            itr.get_next()
        n3 = itr.get_next(datetime)
        self.assertEqual(n3.month, 12)
        self.assertEqual(n3.year, 2010)
        n4 = itr.get_next(datetime)
        self.assertEqual(n4.month, 1)
        self.assertEqual(n4.year, 2011)

    def testError(self):
        itr = croniter('* * * * *')
        self.assertRaises(TypeError, itr.get_next, str)
        self.assertRaises(ValueError, croniter, '* * * *')
        self.assertRaises(ValueError, croniter, '* * 5-1 * *')
        self.assertRaises(KeyError, croniter, '* * * janu-jun *')

    def testPrevMinute(self):
        base = datetime(2010, 8, 25, 15, 56)
        itr = croniter('*/1 * * * *', base)
        prev = itr.get_prev(datetime)
        self.assertEqual(base.year, prev.year)
        self.assertEqual(base.month, prev.month)
        self.assertEqual(base.day, prev.day)
        self.assertEqual(base.hour, prev.hour)
        self.assertEqual(base.minute, prev.minute + 1)

        base = datetime(2010, 8, 25, 15, 0)
        itr = croniter('*/1 * * * *', base)
        prev = itr.get_prev(datetime)
        self.assertEqual(base.year, prev.year)
        self.assertEqual(base.month, prev.month)
        self.assertEqual(base.day, prev.day)
        self.assertEqual(base.hour, prev.hour + 1)
        self.assertEqual(59, prev.minute)

        base = datetime(2010, 8, 25, 0, 0)
        itr = croniter('*/1 * * * *', base)
        prev = itr.get_prev(datetime)
        self.assertEqual(base.year, prev.year)
        self.assertEqual(base.month, prev.month)
        self.assertEqual(base.day, prev.day + 1)
        self.assertEqual(23, prev.hour)
        self.assertEqual(59, prev.minute)

    def testPrevDayOfMonthWithCrossing(self):
        """
        Test getting previous occurrence that crosses into previous month.
        """
        base = datetime(2012, 3, 15, 0, 0)
        itr = croniter('0 0 22 * *', base)
        prev = itr.get_prev(datetime)
        self.assertEqual(prev.year, 2012)
        self.assertEqual(prev.month, 2)
        self.assertEqual(prev.day, 22)
        self.assertEqual(prev.hour, 0)
        self.assertEqual(prev.minute, 0)

    def testPrevWeekDay(self):
        base = datetime(2010, 8, 25, 15, 56)
        itr = croniter('0 0 * * sat,sun', base)
        prev1 = itr.get_prev(datetime)
        self.assertEqual(prev1.year, base.year)
        self.assertEqual(prev1.month, base.month)
        self.assertEqual(prev1.day, 22)
        self.assertEqual(prev1.hour, 0)
        self.assertEqual(prev1.minute, 0)

        prev2 = itr.get_prev(datetime)
        self.assertEqual(prev2.year, base.year)
        self.assertEqual(prev2.month, base.month)
        self.assertEqual(prev2.day, 21)
        self.assertEqual(prev2.hour, 0)
        self.assertEqual(prev2.minute, 0)

        prev3 = itr.get_prev(datetime)
        self.assertEqual(prev3.year, base.year)
        self.assertEqual(prev3.month, base.month)
        self.assertEqual(prev3.day, 15)
        self.assertEqual(prev3.hour, 0)
        self.assertEqual(prev3.minute, 0)

    def testPrevWeekDay2(self):
        base = datetime(2010, 8, 25, 15, 56)
        itr = croniter('10 0 * * 0', base)
        prev = itr.get_prev(datetime)
        self.assertEqual(prev.day, 22)
        self.assertEqual(prev.hour, 0)
        self.assertEqual(prev.minute, 10)

    def testISOWeekday(self):
        base = datetime(2010, 2, 25)
        itr = croniter('0 0 * * 7', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.isoweekday(), 7)
        self.assertEqual(n1.day, 28)
        n2 = itr.get_next(datetime)
        self.assertEqual(n2.isoweekday(), 7)
        self.assertEqual(n2.day, 7)
        self.assertEqual(n2.month, 3)

    def testBug1(self):
        base = datetime(2012, 2, 24)
        itr = croniter('5 0 */2 * *', base)
        n1 = itr.get_prev(datetime)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 5)
        self.assertEqual(n1.month, 2)
        # month starts from 1, 3 .... then 21, 23
        # so correct is not 22  but 23
        self.assertEqual(n1.day, 23)

    def testBug2(self):
        base = datetime(2012, 1, 1, 0, 0)
        iter = croniter('0 * * 3 *', base)
        n1 = iter.get_next(datetime)
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.month, 3)
        self.assertEqual(n1.day, base.day)
        self.assertEqual(n1.hour, base.hour)
        self.assertEqual(n1.minute, base.minute)

        n2 = iter.get_next(datetime)
        self.assertEqual(n2.year, base.year)
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, base.day)
        self.assertEqual(n2.hour, base.hour + 1)
        self.assertEqual(n2.minute, base.minute)

        n3 = iter.get_next(datetime)
        self.assertEqual(n3.year, base.year)
        self.assertEqual(n3.month, 3)
        self.assertEqual(n3.day, base.day)
        self.assertEqual(n3.hour, base.hour + 2)
        self.assertEqual(n3.minute, base.minute)

    def testBug3(self):
        base = datetime(2013, 3, 1, 12, 17, 34, 257877)
        c = croniter('00 03 16,30 * *', base)

        n1 = c.get_next(datetime)
        self.assertEqual(n1.month, 3)
        self.assertEqual(n1.day, 16)

        n2 = c.get_next(datetime)
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, 30)

        n3 = c.get_next(datetime)
        self.assertEqual(n3.month, 4)
        self.assertEqual(n3.day, 16)

        n4 = c.get_prev(datetime)
        self.assertEqual(n4.month, 3)
        self.assertEqual(n4.day, 30)

        n5 = c.get_prev(datetime)
        self.assertEqual(n5.month, 3)
        self.assertEqual(n5.day, 16)

        n6 = c.get_prev(datetime)
        self.assertEqual(n6.month, 2)
        self.assertEqual(n6.day, 16)

    def test_rangeGenerator(self):
        base = datetime(2013, 3, 4, 0, 0)
        itr = croniter('1-9/2 0 1 * *', base)
        n1 = itr.get_next(datetime)
        n2 = itr.get_next(datetime)
        n3 = itr.get_next(datetime)
        n4 = itr.get_next(datetime)
        n5 = itr.get_next(datetime)
        self.assertEqual(n1.minute, 1)
        self.assertEqual(n2.minute, 3)
        self.assertEqual(n3.minute, 5)
        self.assertEqual(n4.minute, 7)
        self.assertEqual(n5.minute, 9)

    def testPreviousHour(self):
        base = datetime(2012, 6, 23, 17, 41)
        itr = croniter('* 10 * * *', base)
        prev1 = itr.get_prev(datetime)
        self.assertEqual(prev1.year, base.year)
        self.assertEqual(prev1.month, base.month)
        self.assertEqual(prev1.day, base.day)
        self.assertEqual(prev1.hour, 10)
        self.assertEqual(prev1.minute, 59)

    def testPreviousDay(self):
        base = datetime(2012, 6, 27, 0, 15)
        itr = croniter('* * 26 * *', base)
        prev1 = itr.get_prev(datetime)
        self.assertEqual(prev1.year, base.year)
        self.assertEqual(prev1.month, base.month)
        self.assertEqual(prev1.day, 26)
        self.assertEqual(prev1.hour, 23)
        self.assertEqual(prev1.minute, 59)

    def testPreviousMonth(self):
        base = datetime(2012, 6, 18, 0, 15)
        itr = croniter('* * * 5 *', base)
        prev1 = itr.get_prev(datetime)
        self.assertEqual(prev1.year, base.year)
        self.assertEqual(prev1.month, 5)
        self.assertEqual(prev1.day, 31)
        self.assertEqual(prev1.hour, 23)
        self.assertEqual(prev1.minute, 59)

    def testPreviousDow(self):
        base = datetime(2012, 5, 13, 18, 48)
        itr = croniter('* * * * sat', base)
        prev1 = itr.get_prev(datetime)
        self.assertEqual(prev1.year, base.year)
        self.assertEqual(prev1.month, base.month)
        self.assertEqual(prev1.day, 12)
        self.assertEqual(prev1.hour, 23)
        self.assertEqual(prev1.minute, 59)

    def testGetCurrent(self):
        base = datetime(2012, 9, 25, 11, 24)
        itr = croniter('* * * * *', base)
        res = itr.get_current(datetime)
        self.assertEqual(base.year, res.year)
        self.assertEqual(base.month, res.month)
        self.assertEqual(base.day, res.day)
        self.assertEqual(base.hour, res.hour)
        self.assertEqual(base.minute, res.minute)

    def testTimezone(self):
        base = datetime(2013, 3, 4, 12, 15)
        itr = croniter('* * * * *', base)
        n1 = itr.get_next(datetime)
        self.assertEqual(n1.tzinfo, None)

        tokyo = pytz.timezone('Asia/Tokyo')
        itr2 = croniter('* * * * *', tokyo.localize(base))
        n2 = itr2.get_next(datetime)
        self.assertEqual(n2.tzinfo.zone, 'Asia/Tokyo')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_speed
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function
from datetime import datetime
from croniter import croniter

from croniter.tests import base


class timerTest(object):
    def __init__(self):
        self.tests = tuple(getattr(self, m)
                           for m in dir(self)
                           if m.lower().startswith('test'))

    def run(self):
        for test in self.tests:
            test()


class CroniterTest(timerTest):
    def testMinute(self):
        # minute asterisk
        base = datetime(2010, 1, 23, 12, 18)
        itr = croniter('*/1 * * * *', base)
        n1 = itr.get_next(datetime)    # 19
        base.year == n1.year
        base.month == n1.month
        base.day == n1.day
        base.hour == n1.hour
        base.minute == n1.minute - 1
        for i in range(39):  # ~ 58
            itr.get_next()

        n2 = itr.get_next(datetime)
        n2.minute == 59

        n3 = itr.get_next(datetime)

        n3.minute == 0
        n3.hour == 13

        itr = croniter('*/5 * * * *', base)
        n4 = itr.get_next(datetime)
        n4.minute == 20
        for i in range(6):
            itr.get_next()
        n5 = itr.get_next(datetime)
        n5.minute == 55

        n6 = itr.get_next(datetime)
        n6.minute == 0
        n6.hour == 13

    def testHour(self):
        base = datetime(2010, 1, 24, 12, 2)
        itr = croniter('0 */3 * * *', base)
        n1 = itr.get_next(datetime)

        n1.hour == 15
        n1.minute == 0

        for i in range(2):
            itr.get_next()

        n2 = itr.get_next(datetime)
        n2.hour == 0
        n2.day == 25

    def testDay(self):
        base = datetime(2010, 2, 24, 12, 9)
        itr = croniter('0 0 */3 * *', base)
        n1 = itr.get_next(datetime)
        n1.day == 27
        n2 = itr.get_next(datetime)
        n2.day == 3

        # test leap year
        base = datetime(1996, 2, 27)
        itr = croniter('0 0 * * *', base)
        n1 = itr.get_next(datetime)
        n1.day == 28
        n1.month == 2
        n2 = itr.get_next(datetime)
        n2.day == 29
        n2.month == 2

        base2 = datetime(2000, 2, 27)
        itr2 = croniter('0 0 * * *', base2)
        n3 = itr2.get_next(datetime)
        n3.day == 28
        n3.month == 2
        n4 = itr2.get_next(datetime)
        n4.day == 29
        n4.month == 2

    def testWeekDay(self):
        base = datetime(2010, 2, 25)
        itr = croniter('0 0 * * sat', base)
        n1 = itr.get_next(datetime)
        n1.isoweekday() == 6
        n1.day == 27

        n2 = itr.get_next(datetime)
        n2.isoweekday() == 6
        n2.day == 6
        n2.month == 3

        base = datetime(2010, 1, 25)
        itr = croniter('0 0 1 * wed', base)
        n1 = itr.get_next(datetime)
        n1.month == 1
        n1.day == 27
        n1.year == 2010

        n2 = itr.get_next(datetime)
        n2.month == 2
        n2.day == 1
        n2.year == 2010

        n3 = itr.get_next(datetime)
        n3.month == 2
        n3.day == 3
        n3.year == 2010

    def testMonth(self):
        base = datetime(2010, 1, 25)
        itr = croniter('0 0 1 * *', base)
        n1 = itr.get_next(datetime)

        n1.month == 2
        n1.day == 1

        n2 = itr.get_next(datetime)
        n2.month == 3
        n2.day == 1

        for i in range(8):
            itr.get_next()

        n3 = itr.get_next(datetime)
        n3.month == 12
        n3.year == 2010

        n4 = itr.get_next(datetime)
        n4.month == 1
        n4.year == 2011

    def testPrevMinute(self):
        base = datetime(2010, 8, 25, 15, 56)
        itr = croniter('*/1 * * * *', base)
        prev = itr.get_prev(datetime)
        base.year == prev.year
        base.month == prev.month
        base.day == prev.day
        base.hour == prev.hour
        base.minute, prev.minute + 1

        base = datetime(2010, 8, 25, 15, 0)
        itr = croniter('*/1 * * * *', base)
        prev = itr.get_prev(datetime)
        base.year == prev.year
        base.month == prev.month
        base.day == prev.day
        base.hour == prev.hour + 1
        59 == prev.minute

        base = datetime(2010, 8, 25, 0, 0)
        itr = croniter('*/1 * * * *', base)
        prev = itr.get_prev(datetime)
        base.year == prev.year
        base.month == prev.month
        base.day == prev.day + 1
        23 == prev.hour
        59 == prev.minute

    def testPrevWeekDay(self):
        base = datetime(2010, 8, 25, 15, 56)
        itr = croniter('0 0 * * sat,sun', base)
        prev1 = itr.get_prev(datetime)
        prev1.year == base.year
        prev1.month == base.month
        prev1.day == 22
        prev1.hour == 0
        prev1.minute == 0

        prev2 = itr.get_prev(datetime)
        prev2.year == base.year
        prev2.month == base.month
        prev2.day == 21
        prev2.hour == 0
        prev2.minute == 0

        prev3 = itr.get_prev(datetime)
        prev3.year == base.year
        prev3.month == base.month
        prev3.day == 15
        prev3.hour == 0
        prev3.minute == 0

    def testISOWeekday(self):
        base = datetime(2010, 2, 25)
        itr = croniter('0 0 * * 7', base)
        n1 = itr.get_next(datetime)
        n1.isoweekday() == 7
        n1.day == 28

        n2 = itr.get_next(datetime)
        n2.isoweekday() == 7
        n2.day == 7
        n2.month == 3


class TestCase(base.TestCase):
    """make zope.testrunner happy"""

    def test_Noop(self):
        self.assertEqual(1, 1)


if __name__ == '__main__':
    from timeit import Timer
    t = Timer('c=CroniterTest();c.run()', 'from __main__ import CroniterTest')
    print(t.timeit(200))

########NEW FILE########
