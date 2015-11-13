__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

cmd = 'from setuptools.command.easy_install import main; main()'
if sys.platform == 'win32':
    cmd = '"%s"' % cmd # work around spawn lamosity on windows

ws = pkg_resources.working_set
assert os.spawnle(
    os.P_WAIT, sys.executable, sys.executable,
    '-c', cmd, '-mqNxd', tmpeggs, 'zc.buildout',
    dict(os.environ,
         PYTHONPATH=
         ws.find(pkg_resources.Requirement.parse('setuptools')).location
         ),
    ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout')
import zc.buildout.buildout
zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = example
from funkload.MonitorPlugins import MonitorPlugin, Plot
GNUPLOTSTYLE='lines lw 3'
DATALABEL1='EXAMPLE1'
DATATITLE1='example1'
PLOTTITLE1='Example plot1 - single data'

PLOTTITLE2='Example plot2 - multiple data'
DATALABEL21='EXAMPLE21'
DATATITLE21='example21'
DATALABEL22='EXAMPLE22'
DATATITLE22='example22'

class Example(MonitorPlugin):
    plots=[Plot({DATALABEL1: [GNUPLOTSTYLE, DATATITLE1]}, title=PLOTTITLE1),
           Plot({
                  DATALABEL21: [GNUPLOTSTYLE, DATATITLE21],
                  DATALABEL22: [GNUPLOTSTYLE, DATATITLE22]
                }, title=PLOTTITLE2)]
    def getStat(self):
        return {DATALABEL1: 70, DATALABEL21: 80, DATALABEL22: 90}

    def parseStats(self, stats):
        if not (hasattr(stats[0], DATALABEL1) and \
                hasattr(stats[0], DATALABEL21) and \
                hasattr(stats[0], DATALABEL22)):
            return None
        data1=[int(getattr(stats[0], DATALABEL1)) for x in stats]
        data21=[int(getattr(stats[0], DATALABEL21)) for x in stats]
        data22=[int(getattr(stats[0], DATALABEL22)) for x in stats]

        return {DATALABEL1: data1, DATALABEL21: data21, DATALABEL22: data22}

########NEW FILE########
__FILENAME__ = MonitorPluginMunin
import shlex, re, os
from subprocess import *
from funkload.MonitorPlugins import MonitorPlugin, Plot

RE_ENTRY=r'[a-zA-Z_][a-zA-Z0-9_]+\.[a-zA-Z0-9_]+'

""" 
NOTES:
- watch out for plugins running for a long time
- no arguments can be passed to munin plugins (they should not need it anyway)
- munin plugins written as shell scripts may need MUNIN_LIBDIR env defined
- some munin plugins may need root priviledges
in monitor.conf:
[plugins.monitormunin]
command1 = /usr/share/munin/plugins/vmstat;MUNIN_LIBDIR=/usr/share/munin/
command2 = /etc/munin/plugins/if_eth0
commandN = plugin_full_path;ENV_VAR=VALUE ENV_VAR2=VALUE2
"""

class MonitorMunin(MonitorPlugin):
    def __init__(self, conf=None):
        super(MonitorMunin, self).__init__(conf)
        if conf==None or not conf.has_section('plugins.monitormunin'):
            return

        self.commands={}
        for opt in conf.options('plugins.monitormunin'):
            if re.match(r'^command\d+$', opt):
                config=conf.get('plugins.monitormunin', opt).split(";")
                if len(config)==1:
                    config=(config[0], "")
                self.commands[os.path.basename(config[0])]=(config[0], config[1])

        for cmd in self.commands.keys():
            data=self._getConfig(cmd, self.commands[cmd][0], self.commands[cmd][1])
            p={}
            negatives=[]
            counters=[]
            for d in data[1]:
                p[d[0]]=['lines lw 2', d[1]]
                if d[2]:
                    negatives.append(d[2])
                if d[3]:
                    counters.append(d[0])
            if len(p)==0:
                continue

            title=cmd
            if data[0]:
                title=re.sub(r'\$\{graph_period\}', 'second', data[0])

            self.plots.append(Plot(p, title=title, negatives=negatives, counters=counters))

    def _nameResult(self, cmd, label):
        return "%s_%s_%s" % (self.name, cmd, label)

    def _parseOutput(self, output):
        ret={}
        for line in output.split('\n'):
            splited=line.split(' ')
            if len(splited)>=2:
                ret[splited[0]]=" ".join(splited[1:])
        return ret

    def _parseEnv(self, env):
        environment=os.environ
        for entry in env.split(' '):
            splited=entry.split('=')
            if len(splited)>=2:
                environment[splited[0]]="=".join(splited[1:])
        return environment

    def _getConfig(self, name, cmd, env):
        output = Popen('%s config' % cmd, shell=True, stdout=PIPE, env=self._parseEnv(env)).communicate()[0]
        output_parsed=self._parseOutput(output)

        fields=[]
        for entry in output_parsed.keys():
            if re.match(RE_ENTRY, entry):
                field=entry.split('.')[0]
                if field not in fields:
                    fields.append(field)

        ret=[]
        for field in fields:
            label=""
            neg=False
            count=False
            data_name=self._nameResult(name, field)

            if output_parsed.has_key("%s.label"%field):
                label=output_parsed["%s.label"%field]
#            if output_parsed.has_key("%s.info"%field):
#                label=output_parsed["%s.info"%field]
            
            if output_parsed.has_key("%s.negative"%field):
                neg=self._nameResult(name, output_parsed["%s.negative"%field])

            if output_parsed.has_key("%s.type"%field):
                t=output_parsed["%s.type"%field]
                if t=='COUNTER' or t=='DERIVE':
                    count=True

            ret.append((data_name, label, neg, count))

        title=None
        if output_parsed.has_key('graph_vlabel'):
            title=output_parsed['graph_vlabel']
            
        return [title, ret]

    def _parseStat(self, name, cmd, env):
        output = Popen([cmd], shell=True, stdout=PIPE, env=self._parseEnv(env)).communicate()[0]
        ret={}
        for line in output.split('\n'):
            splited=line.split(' ')
            if len(splited)==2 and re.match(RE_ENTRY, splited[0]):
                data_name=self._nameResult(name, splited[0].split('.')[0])
                ret[data_name]=splited[1]

        return ret

    def getStat(self):
        ret={}
        for cmd in self.commands.keys():
            data=self._parseStat(cmd, self.commands[cmd][0], self.commands[cmd][1])
            for key in data.keys():
                ret[key]=data[key]
        return ret
                
    def parseStats(self, stats):
        if len(self.plots)==0:
            return None
        for plot in self.plots:
            for p in plot.plots.keys():
                if not (hasattr(stats[0], p)):
                   return None
        ret={}
        for plot in self.plots:
            for p in plot.plots.keys():
                if p in plot.counters:
                    parsed=[]
                    for i in range(1, len(stats)):
                        delta=float(getattr(stats[i], p))-float(getattr(stats[i-1], p))
                        time=float(stats[i].time)-float(stats[i-1].time)
                        parsed.append(delta/time)
                    ret[p]=parsed
                else:
                    ret[p]=[float(getattr(x, p)) for x in stats]

                if p in plot.negatives:
                    ret[p]=[x*-1 for x in ret[p]]
        return ret

########NEW FILE########
__FILENAME__ = MonitorPluginNagios
import shlex, re
from subprocess import *
from funkload.MonitorPlugins import MonitorPlugin, Plot

""" 
NOTES:
 - all values are converted to float
 - charts unit will be set to the unit of first label returned by nagios plugin
 - nagios plugin name can not contain characters that are invalid for xml attribute name
 - nagios plugins should return data immediately otherwise you may have problems (long running plugins)
 - nagios plugins return codes are ignored

in monitor.conf:
[plugins.monitornagios]
command1 = check_load;/usr/lib/nagios/plugins/check_load -w 5.0,4.0,3.0 -c 10.0,6.0,4.0
command2 = check_ping;/usr/lib/nagios/plugins/check_ping -H localhost -w 10,10% -c 10,10% -p 1
commandN = command_name;full_path [args]
"""

class MonitorNagios(MonitorPlugin):
    def __init__(self, conf=None):
        super(MonitorNagios, self).__init__(conf)
        if conf==None or not conf.has_section('plugins.monitornagios'):
            return

        self.commands={}
        for opt in conf.options('plugins.monitornagios'):
            if re.match(r'^command\d+$', opt):
                config=conf.get('plugins.monitornagios', opt).split(";")
                self.commands[config[0]]=config[1]

        for cmd in self.commands.keys():
            data=self._parsePerf(cmd, self.commands[cmd])
            p={}
            for d in data:
                p[d[1]]=['lines lw 2', d[0]]
            if len(p)!=0:
                self.plots.append(Plot(p, unit=data[0][3], title=cmd))

    def _nameResult(self, cmd, label):
        return "%s_%s_%s" % (self.name, cmd, label)

    def _parsePerf(self, name, cmd):
        output = Popen(shlex.split(cmd), stdout=PIPE).communicate()[0]
        perfs=output.split('|')[-1]
        data=re.findall(r'([^=]+=[^;]+);\S+\s?', perfs)
        ret=[]
        i=0
        for d in data:
            groups=re.match(r"'?([^']+)'?=([\d\.\,]+)(.+)?$", d).groups("")
            ret.append((groups[0], self._nameResult(name, i), groups[1], groups[2]))
            i+=1
        return ret

    def getStat(self):
        ret={}
        for cmd in self.commands.keys():
            data=self._parsePerf(cmd, self.commands[cmd])
            for d in data:
                ret[d[1]]=d[2]
        return ret

    def parseStats(self, stats):
        if len(self.plots)==0:
            return None
        for plot in self.plots:
            for p in plot.plots.keys():
                if not (hasattr(stats[0], p)):
                   return None
        ret={}
        for plot in self.plots:
            for p in plot.plots.keys():
                ret[p]=[float(getattr(x, p)) for x in stats]

        return ret


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# funkload documentation build configuration file, created by
# sphinx-quickstart on Fri Apr 16 14:25:32 2010.
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
sys.path.append(os.path.abspath('../../../src'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'FunkLoad'
copyright = u'2011, Benoit Delbosc'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.16'
# The full version, including alpha/beta/rc tags.
release = '1.16.1'

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
exclude_trees = []

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'sphinxdoc'

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
html_logo = 'funkload-logo-small.png'

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

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'funkloaddoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'funkload.tex', u'funkload Documentation',
   u'Benoit Delbosc', 'manual'),
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
__FILENAME__ = apdex
#! /usr/bin/env python

class Apdex(object):
    """Application Performance Index

    The Apdex score converts many measurements into one number on a
    uniform scale of 0-to-1 (0 = no users satisfied, 1 = all users
    satisfied).

    Visit http://www.apdex.org/ for more information.
    """

    # T "constant" (can be changed by clients)
    T = 1.5 # in seconds


    @classmethod
    def satisfying(cls, duration):
        return duration < cls.T

    @classmethod
    def tolerable(cls, duration):
        return duration < cls.T*4

    @classmethod
    def frustrating(cls, duration):
        return duration >= cls.T*4

    @classmethod
    def score(cls, satisfied_users, tolerating_users, frustrated_users):
        count = sum([satisfied_users, tolerating_users, frustrated_users])
        if count == 0:
            return 0
        numeric_score = (satisfied_users + (tolerating_users/2.0))/count
        klass = cls.get_score_class(numeric_score)
        return klass(numeric_score)


    class Unacceptable(float):
        label = 'UNACCEPTABLE'
        threshold = 0.5
    class Poor(float):
        label = 'POOR'
        threshold = 0.7
    class Fair(float):
        label = 'FAIR'
        threshold = 0.85
    class Good(float):
        label = 'Good'
        threshold = 0.94
    class Excellent(float):
        label = 'Excellent'
        threshold = None # anythin above 0.94 is excellent

    # An ordered list of score classes, worst-to-best
    score_classes = [Unacceptable, Poor, Fair, Good, Excellent]

    @classmethod
    def get_score_class(cls, score):
        '''Given numeric score, return a score class'''
        for klass in cls.score_classes:
            if klass == cls.Excellent or score < klass.threshold:
                return klass

    @classmethod
    def get_label(cls, score):
        return cls.get_score_class(score).label


    description_para = '''\
 Apdex T: Application Performance Index,
  this is a numerical measure of user satisfaction, it is based
  on three zones of application responsiveness:

  - Satisfied: The user is fully productive. This represents the
    time value (T seconds) below which users are not impeded by
    application response time.

  - Tolerating: The user notices performance lagging within
    responses greater than T, but continues the process.

  - Frustrated: Performance with a response time greater than 4*T
    seconds is unacceptable, and users may abandon the process.

    By default T is set to 1.5s. This means that response time between 0
    and 1.5s the user is fully productive, between 1.5 and 6s the
    responsivness is tolerable and above 6s the user is frustrated.

    The Apdex score converts many measurements into one number on a
    uniform scale of 0-to-1 (0 = no users satisfied, 1 = all users
    satisfied).

    Visit http://www.apdex.org/ for more information.'''

    rating_para = '''\
 Rating: To ease interpretation, the Apdex score is also represented
  as a rating:

  - U for UNACCEPTABLE represented in gray for a score between 0 and 0.5

  - P for POOR represented in red for a score between 0.5 and 0.7

  - F for FAIR represented in yellow for a score between 0.7 and 0.85

  - G for Good represented in green for a score between 0.85 and 0.94

  - E for Excellent represented in blue for a score between 0.94 and 1.
'''


########NEW FILE########
__FILENAME__ = BenchRunner
#!/usr/bin/python
# (C) Copyright 2005-2010 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors: Tom Lazar
#               Goutham Bhat
#               Andrew McFague
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad Bench runner.

$Id: BenchRunner.py 24746 2005-08-31 09:59:27Z bdelbosc $
"""
import os
import platform
import sys
import threading
import time
import traceback
import unittest
from datetime import datetime
from optparse import OptionParser, TitledHelpFormatter
from socket import error as SocketError
from thread import error as ThreadError
from xmlrpclib import ServerProxy, Fault
import signal

from FunkLoadTestCase import FunkLoadTestCase
from FunkLoadHTTPServer import FunkLoadHTTPServer
from utils import mmn_encode, set_recording_flag, recording, thread_sleep, \
                  trace, red_str, green_str, get_version
try:
    from funkload.rtfeedback import (FeedbackSender, DEFAULT_ENDPOINT,
                                     DEFAULT_PUBSUB)
    LIVE_FEEDBACK = True
except ImportError:
    LIVE_FEEDBACK = False
    DEFAULT_PUBSUB = DEFAULT_ENDPOINT = None


USAGE = """%prog [options] file class.method

%prog launch a FunkLoad unit test as load test.

A FunkLoad unittest uses a configuration file named [class].conf. This
configuration may be overriden by the command line options.

See http://funkload.nuxeo.org/ for more information.

Examples
========
  %prog myFile.py MyTestCase.testSomething
  %prog my_module MyTestCase.testSomething
                        Bench MyTestCase.testSomething using MyTestCase.conf.
  %prog -u http://localhost:8080 -c 10:20 -D 30 myFile.py \\
      MyTestCase.testSomething
                        Bench MyTestCase.testSomething on localhost:8080
                        with 2 cycles of 10 and 20 users for a duration of 30s.
  %prog -h
                        More options.

Alternative Usage:
  %prog discover [options]
                        Discover test modules in the current directory and
                        bench all of them.
"""

try:
    import psyco
    psyco.full()
except ImportError:
    pass


# ------------------------------------------------------------
# utils
#
g_failures = 0                      # result of the bench
g_errors = 0                        # result of the bench
g_success = 0


def add_cycle_result(status):
    """Count number of result."""
    # XXX use a thread.lock, but we don't mind if it is not accurate
    # as the report use the xml log
    global g_success, g_failures, g_errors
    if status == 'success':
        g_success += 1
    elif status == 'error':
        g_errors += 1
    else:
        g_failures += 1

    return g_success, g_errors, g_failures


def get_cycle_results():
    """Return counters."""
    global g_success, g_failures, g_errors
    return g_success, g_failures, g_errors


def get_status(success, failures, errors, color=False):
    """Return a status and an exit code."""
    if errors:
        status = 'ERROR'
        if color:
            status = red_str(status)
        code = -1
    elif failures:
        status = 'FAILURE'
        if color:
            status = red_str(status)
        code = 1
    else:
        status = 'SUCCESSFUL'
        if color:
            status = green_str(status)
        code = 0
    return status, code


def reset_cycle_results():
    """Clear the previous results."""
    global g_success, g_failures, g_errors
    g_success = g_failures = g_errors = 0


def load_module(test_module):
    module = __import__(test_module)
    parts = test_module.split('.')[1:]
    while parts:
        part = parts.pop()
        module = getattr(module, part)
    return module


def load_unittest(test_module, test_class, test_name, options):
    """instantiate a unittest."""
    module = load_module(test_module)
    klass = getattr(module, test_class)
    return klass(test_name, options)


class ThreadSignaller:
    """
    A simple class to signal whether a thread should continue running or stop.
    """
    def __init__(self):
        self.keep_running = True

    def running(self):
        return self.keep_running

    def set_running(self, val):
        self.keep_running = val


class ThreadData:
    """Container for thread related data."""
    def __init__(self, thread, thread_id, thread_signaller):
        self.thread = thread
        self.thread_id = thread_id
        self.thread_signaller = thread_signaller


# ------------------------------------------------------------
# Classes
#
class LoopTestRunner(threading.Thread):
    """Run a unit test in loop."""

    def __init__(self, test_module, test_class, test_name, options,
                 cycle, cvus, thread_id, thread_signaller, sleep_time,
                 debug=False, feedback=None):
        meta_method_name = mmn_encode(test_name, cycle, cvus, thread_id)
        threading.Thread.__init__(self, target=self.run, name=meta_method_name,
                                  args=())
        self.test = load_unittest(test_module, test_class, meta_method_name,
                                  options)
        if sys.platform.lower().startswith('win'):
            self.color = False
        else:
            self.color = not options.no_color
        self.sleep_time = sleep_time
        self.debug = debug
        self.thread_signaller = thread_signaller
        # this makes threads endings if main stop with a KeyboardInterupt
        self.setDaemon(1)
        self.feedback = feedback

    def run(self):
        """Run a test in loop."""
        while (self.thread_signaller.running()):
            test_result = unittest.TestResult()
            self.test.clearContext()
            self.test(test_result)
            feedback = {}

            if test_result.wasSuccessful():
                if recording():
                    feedback['count'] = add_cycle_result('success')

                if self.color:
                    trace(green_str('.'))
                else:
                    trace('.')

                feedback['result'] = 'success'
            else:
                if len(test_result.errors):
                    if recording():
                        feedback['count'] = add_cycle_result('error')

                    if self.color:
                        trace(red_str('E'))
                    else:
                        trace('E')

                    feedback['result'] = 'error'

                else:
                    if recording():
                        feedback['count'] = add_cycle_result('failure')

                    if self.color:
                        trace(red_str('F'))
                    else:
                        trace('F')

                    feedback['result'] = 'failure'

                if self.debug:
                    feedback['errors'] = test_result.errors
                    feedback['failures'] = test_result.failures

                    for (test, error) in test_result.errors:
                        trace("ERROR %s: %s" % (str(test), str(error)))
                    for (test, error) in test_result.failures:
                        trace("FAILURE %s: %s" % (str(test), str(error)))

            if self.feedback is not None:
                self.feedback.test_done(feedback)

            thread_sleep(self.sleep_time)


class BenchRunner:
    """Run a unit test in bench mode."""

    def __init__(self, module_name, class_name, method_name, options):
        self.module_name = module_name
        self.class_name = class_name
        self.method_name = method_name
        self.options = options
        self.color = not options.no_color
        # create a unittest to get the configuration file
        test = load_unittest(self.module_name, class_name,
                             mmn_encode(method_name, 0, 0, 0), options)
        self.config_path = test._config_path
        self.result_path = test.result_path
        self.class_title = test.conf_get('main', 'title')
        self.class_description = test.conf_get('main', 'description')
        self.test_id = self.method_name
        self.test_description = test.conf_get(self.method_name, 'description',
                                              'No test description')
        self.test_url = test.conf_get('main', 'url')
        self.cycles = map(int, test.conf_getList('bench', 'cycles'))
        self.duration = test.conf_getInt('bench', 'duration')
        self.startup_delay = test.conf_getFloat('bench', 'startup_delay')
        self.cycle_time = test.conf_getFloat('bench', 'cycle_time')
        self.sleep_time = test.conf_getFloat('bench', 'sleep_time')
        self.sleep_time_min = test.conf_getFloat('bench', 'sleep_time_min')
        self.sleep_time_max = test.conf_getFloat('bench', 'sleep_time_max')
        self.threads = []  # Contains list of ThreadData objects
        self.last_thread_id = -1
        self.thread_creation_lock = threading.Lock()

        # setup monitoring
        monitor_hosts = []                  # list of (host, port, descr)
        if not options.is_distributed:
            hosts = test.conf_get('monitor', 'hosts', '', quiet=True).split()
            for host in hosts:
                name = host
                host = test.conf_get(host,'host',host.strip())
                monitor_hosts.append((name, host, test.conf_getInt(name, 'port'),
                                      test.conf_get(name, 'description', '')))
        self.monitor_hosts = monitor_hosts
        # keep the test to use the result logger for monitoring
        # and call setUp/tearDown Cycle
        self.test = test

        # set up the feedback sender
        if LIVE_FEEDBACK and options.is_distributed and options.feedback:
            trace("* Creating Feedback sender")
            self.feedback = FeedbackSender(endpoint=options.feedback_endpoint or
                                           DEFAULT_ENDPOINT)
        else:
            self.feedback = None

    def run(self):
        """Run all the cycles.

        return 0 on success, 1 if there were some failures and -1 on errors."""

        trace(str(self))
        trace("Benching\n")
        trace("========\n\n")
        cycle = total_success = total_failures = total_errors = 0

        self.logr_open()
        trace("* setUpBench hook: ...")
        self.test.setUpBench()
        trace(' done.\n')
        self.getMonitorsConfig()
        trace('\n')
        for cvus in self.cycles:
            t_start = time.time()
            reset_cycle_results()
            text = "Cycle #%i with %s virtual users\n" % (cycle, cvus)
            trace(text)
            trace('-' * (len(text) - 1) + "\n\n")
            monitor_key = '%s:%s:%s' % (self.method_name, cycle, cvus)
            trace("* setUpCycle hook: ...")
            self.test.setUpCycle()
            trace(' done.\n')
            self.startMonitors(monitor_key)
            self.startThreads(cycle, cvus)
            self.logging(cycle, cvus)
            #self.dumpThreads()
            self.stopThreads()
            self.stopMonitors(monitor_key)
            cycle += 1
            trace("* tearDownCycle hook: ...")
            self.test.tearDownCycle()
            trace(' done.\n')
            t_stop = time.time()
            trace("* End of cycle, %.2fs elapsed.\n" % (t_stop - t_start))
            success, failures, errors = get_cycle_results()
            status, code = get_status(success, failures, errors, self.color)
            trace("* Cycle result: **%s**, "
                  "%i success, %i failure, %i errors.\n\n" % (
                status, success, failures, errors))
            total_success += success
            total_failures += failures
            total_errors += errors
        trace("* tearDownBench hook: ...")
        self.test.tearDownBench()
        trace(' done.\n\n')
        self.logr_close()

        # display bench result
        trace("Result\n")
        trace("======\n\n")
        trace("* Success: %s\n" % total_success)
        trace("* Failures: %s\n" % total_failures)
        trace("* Errors: %s\n\n" % total_errors)
        status, code = get_status(total_success, total_failures, total_errors)
        trace("Bench status: **%s**\n" % status)
        return code

    def createThreadId(self):
        self.last_thread_id += 1
        return self.last_thread_id

    def startThreads(self, cycle, number_of_threads):
        """Starts threads."""
        self.thread_creation_lock.acquire()
        try:
            trace("* Current time: %s\n" % datetime.now().isoformat())
            trace("* Starting threads: ")
            set_recording_flag(False)
            threads = self.createThreads(cycle, number_of_threads)
            self.threads.extend(threads)
        finally:
            set_recording_flag(True)
            self.thread_creation_lock.release()

    def addThreads(self, number_of_threads):
        """Adds new threads to existing list. Used to dynamically add new
           threads during a debug bench run."""
        self.thread_creation_lock.acquire()
        try:
            trace("Adding new threads: ")
            set_recording_flag(False)
            # In debug bench, 'cycle' value is irrelevant.
            threads = self.createThreads(0, number_of_threads)
            self.threads.extend(threads)
        finally:
            set_recording_flag(True)
            self.thread_creation_lock.release()

    def createThreads(self, cycle, number_of_threads):
        """Creates number_of_threads threads and returns as a list.

        NOTE: This method is not thread safe. Thread safety must be
        handled by the caller."""
        threads = []
        i = 0
        for i in range(number_of_threads):
            thread_id = self.createThreadId()
            thread_signaller = ThreadSignaller()
            thread = LoopTestRunner(self.module_name, self.class_name,
                                    self.method_name, self.options,
                                    cycle, number_of_threads,
                                    thread_id, thread_signaller,
                                    self.sleep_time,
                                    feedback=self.feedback)
            trace(".")
            try:
                thread.start()
            except ThreadError:
                trace("\nERROR: Can not create more than %i threads, try a "
                      "smaller stack size using: 'ulimit -s 2048' "
                      "for example\n" % (i + 1))
                raise
            thread_data = ThreadData(thread, thread_id, thread_signaller)
            threads.append(thread_data)
            thread_sleep(self.startup_delay)
        trace(' done.\n')
        return threads

    def logging(self, cycle, cvus):
        """Log activity during duration."""
        duration = self.duration
        end_time = time.time() + duration
        mid_time = time.time() + duration / 2
        trace("* Logging for %ds (until %s): " % (
            duration, datetime.fromtimestamp(end_time).isoformat()))
        set_recording_flag(True)
        while time.time() < mid_time:
            time.sleep(1)
        self.test.midCycle(cycle, cvus)
        while time.time() < end_time:
            # wait
            time.sleep(1)
        set_recording_flag(False)
        trace(" done.\n")

    def stopThreads(self):
        """Stops all running threads."""
        self.thread_creation_lock.acquire()
        try:
            trace("* Waiting end of threads: ")
            self.deleteThreads(len(self.threads))
            self.threads = []
            trace(" done.\n")
            trace("* Waiting cycle sleeptime %ds: ..." % self.cycle_time)
            time.sleep(self.cycle_time)
            trace(" done.\n")
            self.last_thread_id = -1
        finally:
            self.thread_creation_lock.release()

    def removeThreads(self, number_of_threads):
        """Removes threads. Used to dynamically remove threads during a
           debug bench run."""
        self.thread_creation_lock.acquire()
        try:
            trace('* Removing threads: ')
            self.deleteThreads(number_of_threads)
            trace(' done.\n')
        finally:
            self.thread_creation_lock.release()

    def deleteThreads(self, number_of_threads):
        """Stops given number of threads and deletes from thread list.

        NOTE: This method is not thread safe. Thread safety must be
        handled by the caller."""
        removed_threads = []
        if number_of_threads > len(self.threads):
            number_of_threads = len(self.threads)
        for i in range(number_of_threads):
            thread_data = self.threads.pop()
            thread_data.thread_signaller.set_running(False)
            removed_threads.append(thread_data)
        for thread_data in removed_threads:
            thread_data.thread.join()
            del thread_data
            trace('.')

    def getNumberOfThreads(self):
        return len(self.threads)

    def dumpThreads(self):
        """Display all different traceback of Threads for debugging.

        Require threadframe module."""
        import threadframe
        stacks = {}
        frames = threadframe.dict()
        for thread_id, frame in frames.iteritems():
            stack = ''.join(traceback.format_stack(frame))
            stacks[stack] = stacks.setdefault(stack, []) + [thread_id]

        def sort_stack(x, y):
            """sort stack by number of thread."""
            return cmp(len(x[1]), len(y[1]))

        stacks = stacks.items()
        stacks.sort(sort_stack)
        for stack, thread_ids in stacks:
            trace('=' * 72 + '\n')
            trace('%i threads : %s\n' % (len(thread_ids), str(thread_ids)))
            trace('-' * 72 + '\n')
            trace(stack + '\n')

    def getMonitorsConfig(self):
        """ Get monitors configuration from hosts """
        if not self.monitor_hosts:
            return
        monitor_hosts = []
        for (name, host, port, desc) in self.monitor_hosts:
            trace("* Getting monitoring config from %s: ..." % name)
            server = ServerProxy("http://%s:%s" % (host, port))
            try:
                config = server.getMonitorsConfig()
                data = []
                for key in config.keys():
                    xml = '<monitorconfig host="%s" key="%s" value="%s" />' % (
                                                        name, key, config[key])
                    data.append(xml)
                self.logr("\n".join(data))
            except Fault:
                trace(' not supported.\n')
                monitor_hosts.append((name, host, port, desc))
            except SocketError:
                trace(' failed, server is down.\n')
            else:
                trace(' done.\n')
                monitor_hosts.append((name, host, port, desc))
        self.monitor_hosts = monitor_hosts

    def startMonitors(self, monitor_key):
        """Start monitoring on hosts list."""
        if not self.monitor_hosts:
            return
        monitor_hosts = []
        for (name, host, port, desc) in self.monitor_hosts:
            trace("* Start monitoring %s: ..." % name)
            server = ServerProxy("http://%s:%s" % (host, port))
            try:
                server.startRecord(monitor_key)
            except SocketError:
                trace(' failed, server is down.\n')
            else:
                trace(' done.\n')
                monitor_hosts.append((name, host, port, desc))
        self.monitor_hosts = monitor_hosts

    def stopMonitors(self, monitor_key):
        """Stop monitoring and save xml result."""
        if not self.monitor_hosts:
            return
        for (name, host, port, desc) in self.monitor_hosts:
            trace('* Stop monitoring %s: ' % name)
            server = ServerProxy("http://%s:%s" % (host, port))
            try:
                server.stopRecord(monitor_key)
                xml = server.getXmlResult(monitor_key)
            except SocketError:
                trace(' failed, server is down.\n')
            else:
                trace(' done.\n')
                self.logr(xml)

    def logr(self, message):
        """Log to the test result file."""
        self.test._logr(message, force=True)

    def logr_open(self):
        """Start logging tag."""
        config = {'id': self.test_id,
                  'description': self.test_description,
                  'class_title': self.class_title,
                  'class_description': self.class_description,
                  'module': self.module_name,
                  'class': self.class_name,
                  'method': self.method_name,
                  'cycles': self.cycles,
                  'duration': self.duration,
                  'sleep_time': self.sleep_time,
                  'startup_delay': self.startup_delay,
                  'sleep_time_min': self.sleep_time_min,
                  'sleep_time_max': self.sleep_time_max,
                  'cycle_time': self.cycle_time,
                  'configuration_file': self.config_path,
                  'server_url': self.test_url,
                  'log_xml': self.result_path,
                  'node': platform.node(),
                  'python_version': platform.python_version()}
        if self.options.label:
            config['label'] = self.options.label

        for (name, host, port, desc) in self.monitor_hosts:
            config[name] = desc
        self.test._open_result_log(**config)

    def logr_close(self):
        """Stop logging tag."""
        self.test._close_result_log()
        self.test.logger_result.handlers = []

    def __repr__(self):
        """Display bench information."""
        text = []
        text.append('=' * 72)
        text.append('Benching %s.%s' % (self.class_name,
                                        self.method_name))
        text.append('=' * 72)
        text.append(self.test_description)
        text.append('-' * 72 + '\n')
        text.append("Configuration")
        text.append("=============\n")
        text.append("* Current time: %s" % datetime.now().isoformat())
        text.append("* Configuration file: %s" % self.config_path)
        text.append("* Log xml: %s" % self.result_path)
        text.append("* Server: %s" % self.test_url)
        text.append("* Cycles: %s" % self.cycles)
        text.append("* Cycle duration: %ss" % self.duration)
        text.append("* Sleeptime between request: from %ss to %ss" % (
            self.sleep_time_min, self.sleep_time_max))
        text.append("* Sleeptime between test case: %ss" % self.sleep_time)
        text.append("* Startup delay between thread: %ss\n\n" %
                    self.startup_delay)
        return '\n'.join(text)


class BenchLoader(unittest.TestLoader):
    suiteClass = list
    def loadTestsFromTestCase(self, testCaseClass):
        if not issubclass(testCaseClass, FunkLoadTestCase):
            trace(red_str("Skipping "+ testCaseClass))
            return []
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']

        return [dict(module_name = testCaseClass.__module__,
                     class_name = testCaseClass.__name__,
                     method_name = x)
                for x in testCaseNames]

def discover(sys_args):
    parser = get_shared_OptionParser()
    options, args = parser.parse_args(sys_args)
    options.label = None

    loader = BenchLoader()
    suite = loader.discover('.')

    def flatten_test_suite(suite):
        if type(suite) != BenchLoader.suiteClass:
            # Wasn't a TestSuite - must have been a Test
            return [suite]
        flat = []
        for x in suite:
            flat += flatten_test_suite(x)
        return flat

    flattened = flatten_test_suite(suite)
    retval = 0
    for test in flattened:
        module_name = test['module_name']
        class_name = test['class_name']
        method_name = test['method_name']
        if options.distribute:
            dist_args = sys_args[:]
            dist_args.append(module_name)
            dist_args.append('%s.%s' % (class_name, method_name))
            ret = run_distributed(options, module_name, class_name,
                                   method_name, dist_args)
        else:
            ret = run_local(options, module_name, class_name, method_name)
        # Handle failures
        if ret != 0:
            retval = ret
            if options.failfast:
                break
    return retval

_manager = None

def shutdown(*args):
    trace('Aborting run...')
    if _manager is not None:
        _manager.abort()
    trace('Aborted')
    sys.exit(0)

def get_runner_class(class_path):
    try:
        module_path, class_name = class_path.rsplit('.', 1)
    except ValueError:
        raise Exception('Invalid class path {0}'.format(class_path))

    _module = __import__(module_path, globals(), locals(), class_name, -1)
    return getattr(_module, class_name)

def parse_sys_args(sys_args):
    parser = get_shared_OptionParser()
    parser.add_option("", "--config",
                      type="string",
                      dest="config",
                      metavar='CONFIG',
                      help="Path to alternative config file")
    parser.add_option("-l", "--label",
                      type="string",
                      help="Add a label to this bench run for easier "
                           "identification (it will be appended to the "
                           "directory name for reports generated from it).")

    options, args = parser.parse_args(sys_args)

    if len(args) != 2:
        parser.error("incorrect number of arguments")

    if not args[1].count('.'):
        parser.error("invalid argument; should be [class].[method]")

    if options.as_fast_as_possible:
        options.bench_sleep_time_min = '0'
        options.bench_sleep_time_max = '0'
        options.bench_sleep_time = '0'

    if os.path.exists(args[0]):
        # We were passed a file for the first argument
        module_name = os.path.basename(os.path.splitext(args[0])[0])
    else:
        # We were passed a module name
        module_name = args[0]

    return options, args, module_name

def get_shared_OptionParser():
    '''Make an OptionParser that can be used in both normal mode and in
    discover mode.
    '''
    parser = OptionParser(USAGE, formatter=TitledHelpFormatter(),
                          version="FunkLoad %s" % get_version())
    parser.add_option("-r", "--runner-class",
                      type="string",
                      dest="bench_runner_class",
                      default="funkload.BenchRunner.BenchRunner",
                      help="Python dotted import path to BenchRunner class to use.")
    parser.add_option("", "--no-color",
                      action="store_true",
                      help="Monochrome output.")
    parser.add_option("", "--accept-invalid-links",
                      action="store_true",
                      help="Do not fail if css/image links are not reachable.")
    parser.add_option("", "--simple-fetch",
                      action="store_true",
                      dest="bench_simple_fetch",
                      help="Don't load additional links like css or images "
                           "when fetching an html page.")
    parser.add_option("--enable-debug-server",
                      action="store_true",
                      dest="debugserver",
                      help="Instantiates a debug HTTP server which exposes an "
                           "interface using which parameters can be modified "
                           "at run-time. Currently supported parameters: "
                           "/cvu?inc=<integer> to increase the number of "
                           "CVUs, /cvu?dec=<integer> to decrease the number "
                           "of CVUs, /getcvu returns number of CVUs ")
    parser.add_option("--debug-server-port",
                      type="string",
                      dest="debugport",
                      help="Port at which debug server should run during the "
                           "test")
    parser.add_option("--distribute",
                      action="store_true",
                      dest="distribute",
                      help="Distributes the CVUs over a group of worker "
                           "machines that are defined in the workers section")
    parser.add_option("--distribute-workers",
                      type="string",
                      dest="workerlist",
                      help="This parameter will  override the list of "
                           "workers defined in the config file. expected "
                           "notation is uname@host,uname:pwd@host or just "
                           "host...")
    parser.add_option("--distribute-python",
                      type="string",
                      dest="python_bin",
                      help="When running in distributed mode, this Python "
                           "binary will be used across all hosts.")
    parser.add_option("--is-distributed",
                      action="store_true",
                      dest="is_distributed",
                      help="This parameter is for internal use only. It "
                           "signals to a worker node that it is in "
                           "distributed mode and shouldn't perform certain "
                           "actions.")
    parser.add_option("--distributed-packages",
                      type="string",
                      dest="distributed_packages",
                      help="Additional packages to be passed to easy_install "
                           "on remote machines when being run in distributed "
                           "mode.")
    parser.add_option("--distributed-log-path",
                      type="string",
                      dest="distributed_log_path",
                      help="Path where all the logs will be stored when "
                           "running a distributed test")
    parser.add_option("--distributed-key-filename",
                      type="string",
                      dest="distributed_key_filename",
                      help=("Path of the SSH key to use when running a "
                            "distributed test"))
    parser.add_option("--feedback-endpoint",
                      type="string",
                      dest="feedback_endpoint",
                      help=("ZMQ push/pull socket used between the master and "
                            "the node to send feedback."))
    parser.add_option("--feedback-pubsub-endpoint",
                      type="string",
                      dest="feedback_pubsub_endpoint",
                      help="ZMQ pub/sub socket use to publish feedback.")
    parser.add_option("--feedback",
                      action="store_true",
                      dest="feedback",
                      help="Activates the realtime feedback")
    parser.add_option("--failfast",
                      action="store_true",
                      dest="failfast",
                      help="Stop on first fail or error. (For discover mode)")
    parser.add_option("-u", "--url",
                      type="string",
                      dest="main_url",
                      help="Base URL to bench.")
    parser.add_option("-c", "--cycles",
                      type="string",
                      dest="bench_cycles",
                      help="Cycles to bench, colon-separated list of "
                           "virtual concurrent users. To run a bench with 3 "
                           "cycles of 5, 10 and 20 users, use: -c 5:10:20")
    parser.add_option("-D", "--duration",
                      type="string",
                      dest="bench_duration",
                      help="Duration of a cycle in seconds.")
    parser.add_option("-m", "--sleep-time-min",
                      type="string",
                      dest="bench_sleep_time_min",
                      help="Minimum sleep time between requests.")
    parser.add_option("-M", "--sleep-time-max",
                      type="string",
                      dest="bench_sleep_time_max",
                      help="Maximum sleep time between requests.")
    parser.add_option("-t", "--test-sleep-time",
                      type="string",
                      dest="bench_sleep_time",
                      help="Sleep time between tests.")
    parser.add_option("-s", "--startup-delay",
                      type="string",
                      dest="bench_startup_delay",
                      help="Startup delay between thread.")
    parser.add_option("-f", "--as-fast-as-possible",
                      action="store_true",
                      help="Remove sleep times between requests and between "
                           "tests, shortcut for -m0 -M0 -t0")
    return parser

def run_distributed(options, module_name, class_name, method_name, sys_args):
    ret = None
    from funkload.Distributed import DistributionMgr
    global _manager
    
    try:
        distmgr = DistributionMgr(
            module_name, class_name, method_name, options, sys_args)
        _manager = distmgr
    except UserWarning, error:
        trace(red_str("Distribution failed with:%s \n" % (error)))
        return 1
    
    try:
        try:
            distmgr.prepare_workers(allow_errors=True)
            ret = distmgr.run()
            distmgr.final_collect()
        except KeyboardInterrupt:
            trace("* ^C received *")
    finally:
        # in any case we want to stop the workers at the end
        distmgr.abort()
    
    _manager = None
    return ret

def run_local(options, module_name, class_name, method_name):
    ret = None
    RunnerClass = get_runner_class(options.bench_runner_class)
    bench = RunnerClass(module_name, class_name, method_name, options)
    
    # Start a HTTP server optionally
    if options.debugserver:
        http_server_thread = FunkLoadHTTPServer(bench, options.debugport)
        http_server_thread.start()
    
    try:
        ret = bench.run()
    except KeyboardInterrupt:
        trace("* ^C received *")
    return ret

def main(sys_args=sys.argv[1:]):
    """Default main."""
    # enable loading of modules in the current path
    cur_path = os.path.abspath(os.path.curdir)
    sys.path.insert(0, cur_path)

    # registering signals
    if not sys.platform.lower().startswith('win'):
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGQUIT, shutdown)

    # special case: 'discover' argument
    if sys_args and sys_args[0].lower() == 'discover':
        return discover(sys_args)

    options, args, module_name = parse_sys_args(sys_args)

    klass, method = args[1].split('.')
    if options.distribute:
        return run_distributed(options, module_name, klass, method, sys_args)
    else:
        return run_local(options, module_name, klass, method)

if __name__ == '__main__':
    ret = main()
    sys.exit(ret)

########NEW FILE########
__FILENAME__ = CredentialBase
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Interface of a Credential Server.

$Id$
"""

class CredentialBaseServer:
    """Interface of a Credential server."""

    def getCredential(self, group=None):
        """Return a credential (login, password).

        If group is not None return a credential that belong to the group.
        """

    def listCredentials(self, group=None):
        """Return a list of all credentials.

        If group is not None return a list of credentials that belong to the
        group.
        """

    def listGroups(self):
        """Return a list of all groups."""

########NEW FILE########
__FILENAME__ = CredentialFile
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""A file credential server/controller.

$Id$
"""
import sys
from ConfigParser import NoOptionError

from XmlRpcBase import XmlRpcBaseServer, XmlRpcBaseController
from CredentialBase import CredentialBaseServer


# ------------------------------------------------------------
# classes
#
class Group:
    """A class to handle groups."""
    def __init__(self, name):
        self.name = name
        self.index = 0
        self.count = 0
        self.users = []

    def add(self, user):
        """Add a user to the group."""
        if not self.users.count(user):
            self.users.append(user)

    def __len__(self):
        """Return the lenght of group."""
        return len(self.users)

    def next(self):
        """Return the next user or the group.

        loop from begining."""
        nb_users = len(self.users)
        if nb_users == 0:
            raise ValueError('No users for group %s' % self.name)
        self.index = self.count % nb_users
        user = self.users[self.index]
        self.count += 1
        return user

    def __repr__(self):
        """Representation."""
        return '<group name="%s" count="%s" index="%s" len="%s" />' % (
            self.name, self.count, self.index, len(self))



# ------------------------------------------------------------
# Server
#
class CredentialFileServer(XmlRpcBaseServer, CredentialBaseServer):
    """A file credential server."""
    server_name = "file_credential"
    method_names = XmlRpcBaseServer.method_names + [
        'getCredential', 'listCredentials', 'listGroups', 'getSeq']

    credential_sep = ':'                    # login:password
    users_sep = ','                         # group_name:user1, user2

    def __init__(self, argv=None):
        self.lofc = 0
        self._groups = {}
        self._passwords = {}
        self.seq = 0
        XmlRpcBaseServer.__init__(self, argv)

    def _init_cb(self, conf, options):
        """init procedure to override in sub classes."""
        credentials_path = conf.get('server', 'credentials_path')
        self.lofc = conf.getint('server', 'loop_on_first_credentials')
        try:
            self.seq = conf.getint('server', 'seq')
        except NoOptionError:
            self.seq = 0
        self._loadPasswords(credentials_path)
        try:
            groups_path = conf.get('server', 'groups_path')
            self._loadGroups(groups_path)
        except NoOptionError:
            pass

    def _loadPasswords(self, file_path):
        """Load a password file."""
        self.logd("CredentialFile use credential file %s." % file_path)
        lines = open(file_path).readlines()
        self._groups = {}
        group = Group('default')
        self._groups[None] = group
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            user, password = [x.strip() for x in line.split(
                self.credential_sep, 1)]
            self._passwords[user] = password
            if not self.lofc or len(group) < self.lofc:
                group.add(user)

    def _loadGroups(self, file_path):
        """Load a group file."""
        self.logd("CredentialFile use group file %s." % file_path)
        lines = open(file_path).readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name, users = [x.strip() for x in line.split(
                self.credential_sep, 1)]
            users = filter(
                None, [user.strip() for user in users.split(self.users_sep)])
            group = self._groups.setdefault(name, Group(name))
            for user in users:
                if self.lofc and len(group) >= self.lofc:
                    break
                if self._passwords.has_key(user):
                    group.add(user)
                else:
                    self.logd('Missing password for %s in group %s' % (user,
                                                                       name))
    #
    # RPC
    def getCredential(self, group=None):
        """Return a credential from group if specified.

        Credential are taken incrementally in a loop.
        """
        user = self._groups[group].next()
        password = self._passwords[user]
        self.logd("getCredential(%s) return (%s, %s)" % (
            group, user, password))
        return (user, password)

    def listCredentials(self, group=None):
        """Return a list of credentials."""
        if group is None:
            ret = list(self._passwords)
        else:
            users = self._groups[group].users
            ret = [(user, self._passwords[user]) for user in users]
        self.logd("listUsers(%s) return (%s)" % (group, ret))
        return ret

    def listGroups(self):
        """Return a list of groups."""
        ret = filter(None, self._groups.keys())
        self.logd("listGroup() return (%s)" % str(ret))
        return ret

    def getSeq(self):
        """Return a sequence."""
        self.seq += 1
        return self.seq


# ------------------------------------------------------------
# Controller
#
class CredentialFileController(XmlRpcBaseController):
    """A file credential controller."""
    server_class = CredentialFileServer

    def test(self):
        """Testing credential server."""
        server = self.server
        self.log(server.listGroups())
        for i in range(10):
            self.log("%s getCredential() ... " % i)
            user, password = server.getCredential()
            self.log(" return (%s, %s)\n" % (user, password))
        for group in server.listGroups():
            self.log("group %s\n" % group)
            self.log("  content: %s\n" % server.listCredentials(group))
        for i in range(5):
            self.log("seq : %d" % server.getSeq())
        return 0

# ------------------------------------------------------------
# main
#
def main():
    """Control credentiald server."""
    ctl = CredentialFileController()
    sys.exit(ctl())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = CredentialRandom
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""A random credential server/controller.

$Id$
"""
import sys

from Lipsum import Lipsum
from XmlRpcBase import XmlRpcBaseServer, XmlRpcBaseController
from CredentialBase import CredentialBaseServer

# ------------------------------------------------------------
# Server
#
class CredentialRandomServer(XmlRpcBaseServer, CredentialBaseServer):
    """A random credential server."""
    server_name = "random_credential"
    method_names = XmlRpcBaseServer.method_names + [
        'getCredential', 'listCredentials', 'listGroups']

    def __init__(self, argv=None):
        XmlRpcBaseServer.__init__(self, argv)
        self.lipsum = Lipsum()

    def getCredential(self, group=None):
        """Return a random (login, password).

        return a random user login, the login is taken from the lipsum
        vocabulary so the number of login is limited to the length of the
        vocabulary. The group asked will prefix the login name.

        The password is just the reverse of the login, this give a coherent
        behaviour if it return twice the same credential.
        """
        self.logd('getCredential(%s) request.' % group)
        # use group as login prefix
        user = (group or 'user') + '_' + self.lipsum.getWord()
        # pwd is the reverse of the login
        tmp = list(user)
        tmp.reverse()
        password = ''.join(tmp)
        self.logd("  return (%s, %s)" % (user, password))
        return (user, password)

    def listCredentials(self, group=None):
        """Return a list of 10 random credentials."""
        self.logd('listCredentials request.')
        return [self.getCredential(group) for x in range(10)]

    def listGroups(self):
        """Retrun a list of 10 random group name."""
        self.logd('listGroups request.')
        lipsum = self.lipsum
        return ['grp' + lipsum.getUniqWord(length_min=2,
                                           length_max=3) for x in range(10)]

# ------------------------------------------------------------
# Controller
#
class CredentialRandomController(XmlRpcBaseController):
    """A random credential controller."""
    server_class = CredentialRandomServer

    def test(self):
        """Testing credential server."""
        server = self.server
        self.log(server.listGroups())
        for i in range(10):
            self.log("%s getCredential() ... " % i)
            user, password = server.getCredential()
            self.log(" return (%s, %s)\n" % (user, password))
        for group in server.listGroups():
            self.log("group %s\n" % group)
            self.log("  content: %s\n" % server.listCredentials(group))
        return 0

# ------------------------------------------------------------
# main
#
def main():
    """Control credentiald server."""
    ctl = CredentialRandomController()
    sys.exit(ctl())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_Cmf
# -*- coding: iso-8859-15 -*-
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""cmf FunkLoad test

$Id$
"""
import unittest
from random import random
from funkload.FunkLoadTestCase import FunkLoadTestCase
from funkload.utils import xmlrpc_get_credential, xmlrpc_list_credentials
from funkload.Lipsum import Lipsum


class CmfTestCase(FunkLoadTestCase):
    """FL TestCase with common cmf tasks.

    self.server_url must be set.
    """
    def cmfLogin(self, login, pwd):
        params = [["__ac_name", login],
                  ["__ac_password", pwd],
                  ["__ac_persistent", "1"],
                  ["submit", " Login "]]
        self.post('%s/logged_in' % self.server_url, params,
                  description="Log xin user %s" % login)
        self.assert_('Login success' in self.getBody(),
                     "Invalid credential %s:%s" % (login, pwd))
        self._cmf_login = login

    def cmfLogout(self):
        self.get('%s/logout' % self.server_url,
                 description="logout %s" % self._cmf_login)


    def cmfCreateNews(self, parent_url):
        # return the doc_url
        lipsum = Lipsum()
        doc_id = lipsum.getUniqWord().lower()
        params = [["type_name", "News Item"],
                  ["id", doc_id],
                  ["add", "Add"]]
        self.post("%s/folder_factories" % parent_url, params,
                  description="Create an empty news")
        params = [["allow_discussion", "default"],
                  ["title", lipsum.getSubject()],
                  ["description:text", lipsum.getParagraph()],
                  ["subject:lines", lipsum.getWord()],
                  ["format", "text/plain"],
                  ["change_and_view", "Change and View"]]
        doc_url = "%s/%s" % (parent_url, doc_id)
        self.post("%s/metadata_edit_form" % doc_url, params,
                  description="Set metadata")
        self.assert_('Metadata changed.' in self.getBody())

        params = [["text_format", "plain"],
                  ["description:text", lipsum.getParagraph()],
                  ["text:text", lipsum.getMessage()],
                  ["change_and_view", "Change and View"]]
        self.post("%s/newsitem_edit_form" % doc_url, params,
                  description="Set news content")
        self.assert_('News Item changed.' in self.getBody())
        return doc_url





class Cmf(CmfTestCase):
    """Simple test of default CMF Site

    This test use a configuration file Cmf.conf.
    """
    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')
        credential_host = self.conf_get('credential', 'host')
        credential_port = self.conf_getInt('credential', 'port')
        self.credential_host = credential_host
        self.credential_port = credential_port
        self.cred_admin = xmlrpc_get_credential(credential_host,
                                                credential_port,
                                                'AdminZope')
        self.cred_member = xmlrpc_get_credential(credential_host,
                                                 credential_port,
                                                 'FL_Member')

    def test_00_verifyCmfSite(self):
        server_url = self.server_url
        if self.exists(server_url):
            self.logd('CMF Site already exists')
            return
        site_id = server_url.split('/')[-1]
        zope_url = server_url[:-(len(site_id)+1)]
        self.setBasicAuth(*self.cred_admin)
        self.get("%s/manage_addProduct/CMFDefault/addPortal" % zope_url)
        params = [["id", site_id],
                  ["title", "FunkLoad CMF Site"],
                  ["create_userfolder", "1"],
                  ["description",
                   "See http://svn.nuxeo.org/pub/funkload/trunk/README.txt "
                   "for more info about FunkLoad"],
                  ["submit", " Add "]]
        self.post("%s/manage_addProduct/CMFDefault/manage_addCMFSite" %
                  zope_url, params, description="Create a CMF Site")
        self.get(server_url, description="View home page")
        self.clearBasicAuth()


    def test_05_verifyUsers(self):
        server_url = self.server_url
        user_mail = self.conf_get('test_05_verifyUsers', 'mail')
        lipsum = Lipsum()
        self.setBasicAuth(*self.cred_admin)
        for user_id, user_pwd in xmlrpc_list_credentials(
            self.credential_host, self.credential_port, 'FL_Member'):
            params = [["member_id", user_id],
                      ["member_email", user_mail],
                      ["password", user_pwd],
                      ["confirm", user_pwd],
                      ["add", "Register"]]
            self.post("%s/join_form" % server_url, params)
            html = self.getBody()
            self.assert_(
                'Member registered' in html or
                'The login name you selected is already in use' in html,
                "Member %s not created" % user_id)
        self.clearBasicAuth()

    def test_anonymous_reader(self):
        server_url = self.server_url
        self.get("%s/Members" % server_url,
                 description="Try to see Members area")
        self.get("%s/recent_news" % server_url,
                 description="Recent news")
        self.get("%s/search_form" % server_url,
                 description="View search form")
        self.get("%s/login_form" % server_url,
                 description="View login form")
        self.get("%s/join_form" % server_url,
                 description="View join form")

    def test_member_reader(self):
        server_url = self.server_url
        self.cmfLogin(*self.cred_member)
        url = '%s/Members/%s/folder_contents' % (server_url,
                                                 self.cred_member[0])
        self.get(url, description="Personal workspace")
        self.get('%s/personalize_form' % server_url,
                 description="Preference page")
        self.cmfLogout()

    def test_10_create_doc(self):
        nb_docs = self.conf_getInt('test_10_create_doc', 'nb_docs')
        server_url = self.server_url
        login = self.cred_member[0]
        self.cmfLogin(*self.cred_member)
        for i in range(nb_docs):
            self.cmfCreateNews("%s/Members/%s" %
                               (server_url, login))
        self.cmfLogout()

        # end of test -----------------------------------------------

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")



if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = CPS338TestCase
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad test case for Nuxeo CPS.

$Id: CPSTestCase.py 24728 2005-08-31 08:13:54Z bdelbosc $
"""
import time
import random
from Lipsum import Lipsum
from ZopeTestCase import ZopeTestCase

class CPSTestCase(ZopeTestCase):
    """Common CPS tasks.

    setUp must set a server_url attribute."""
    cps_test_case_version = (3, 3, 8)
    server_url = None
    _lipsum = Lipsum()
    _all_langs = ['en', 'fr', 'de', 'it', 'es', 'pt_BR',
                  'nl', 'mg', 'ro', 'eu']
    _default_langs = _all_langs[:4]
    _cps_login = None

    # ------------------------------------------------------------
    # cps actions
    #
    def cpsLogin(self, login, password, comment=None):
        """Log in a user.

        Raise on invalid credential."""
        self._cps_login = None
        params = [['__ac_name', login],
                  ['__ac_password', password],
                  ['__ac_persistent', 'on'],
                  ['submit', 'Login'],
                  ]
        self.post("%s/logged_in" % self.server_url, params,
                  description="Log in user [%s] %s" % (login, comment or ''))
        # assume we are logged in if we have a logout link...
        self.assert_('%s/logout' % self.server_url in self.listHref(),
                     'invalid credential: [%s:%s].' % (login, password))
        self._cps_login = login

    def cpsLogout(self):
        """Log out the current user."""
        if self._cps_login is not None:
            self.get('%s/logout' % self.server_url,
                     description="Log out [%s]" % self._cps_login)

    def cpsCreateSite(self, admin_id, admin_pwd,
                      manager_id, manager_password,
                      manager_mail, langs=None, title=None,
                      description=None,
                      interface="portlets",
                      zope_url=None,
                      site_id=None):
        """Create a CPS Site.

        if zope_url or site_id is not provided guess them from the server_url.
        """
        if zope_url is None or site_id is None:
            zope_url, site_id = self.cpsGuessZopeUrl()
        self.setBasicAuth(admin_id, admin_pwd)
        params = {"id": site_id,
                  "title": title or "CPS Portal",
                  "description": description or "A funkload cps test site",
                  "manager_id": manager_id,
                  "manager_password": manager_password,
                  "manager_password_confirmation": manager_password,
                  "manager_email": manager_mail,
                  "manager_sn": "CPS",
                  "manager_givenName": "Manager",
                  "langs_list:list": langs or self._default_langs,
                  "interface": interface,
                  "submit": "Create"}
        self.post("%s/manage_addProduct/CPSDefault/manage_addCPSDefaultSite" %
                  zope_url, params, description="Create a CPS Site")
        self.clearBasicAuth()

    def cpsCreateGroup(self, group_name):
        """Create a cps group."""
        server_url = self.server_url
        params = [["dirname", "groups"],
                  ["id", ""],
                  ["widget__group", group_name],
                  ["widget__members:tokens:default", ""],
                  ["cpsdirectory_entry_create_form:method", "Create"]]
        self.post("%s/" % server_url, params)
        self.assert_(self.getLastUrl().find('psm_entry_created')!=-1,
                         'Failed to create group %s' % group_name)

    def cpsVerifyGroup(self, group_name):
        """Check existance or create a cps group."""
        server_url = self.server_url
        params = [["dirname", "groups"],
                  ["id", group_name],]
        if self.exists("%s/cpsdirectory_entry_view" % server_url, params,
                       description="Check that group [%s] exists."
                       % group_name):
            self.logd('Group %s exists.')
        else:
            self.cpsCreateGroup(group_name)

    def cpsCreateUser(self, user_id=None, user_pwd=None,
                      user_givenName=None, user_sn=None,
                      user_email=None, groups=None):
        """Create a cps user with the Member role.

        return login, pwd"""
        lipsum = self._lipsum
        sign = lipsum.getUniqWord()
        user_id = user_id or 'fl_' + sign.lower()
        user_givenName = user_givenName or lipsum.getWord().capitalize()
        user_sn = user_sn or user_id.upper()
        user_email = user_email or "root@127.0.0.01"
        user_pwd = user_pwd or lipsum.getUniqWord(length_min=6)
        params = [["dirname", "members"],
                  ["id", ""],
                  ["widget__id", user_id],
                  ["widget__password", user_pwd],
                  ["widget__confirm", user_pwd],
                  ["widget__givenName", user_givenName],
                  ["widget__sn", user_sn],
                  ["widget__email", user_email],
                  ["widget__roles:tokens:default", ""],
                  ["widget__roles:list", "Member"],
                  ["widget__groups:tokens:default", ""],
                  ["widget__homeless", "0"],
                  ["cpsdirectory_entry_create_form:method", "Create"]]
        for group in groups:
            params.append(["widget__groups:list", group])
        self.post("%s/" % self.server_url, params,
                  description="Create user [%s]" % user_id)
        self.assert_(self.getLastUrl().find('psm_entry_created')!=-1,
                     'Failed to create user %s' % user_id)
        return user_id, user_pwd

    def cpsVerifyUser(self, user_id=None, user_pwd=None,
                      user_givenName=None, user_sn=None,
                      user_email=None, groups=None):
        """Verify if user exists or create him.

        return login, pwd

        if user exists pwd is None.
        """
        if user_id:
            params = [["dirname", "members"],
                      ["id", user_id],]
            if self.exists(
                "%s/cpsdirectory_entry_view" % self.server_url, params):
                self.logd('User %s exists.')
                return user_id, None

        return self.cpsCreateUser(user_id, user_pwd, user_givenName,
                                  user_sn, user_email, groups)

    def cpsSetLocalRole(self, url, name, role):
        """Setup local role role to url."""
        params = [["member_ids:list", name],
                  ["member_role", role]]
        self.post("%s/folder_localrole_add" % url, params,
                  description="Grant local role %s to %s" % (role, name))

    def cpsCreateSection(self, parent_url, title,
                         description="ftest section for funkload testing.",
                         lang=None):
        """Create a section."""
        return self.cpsCreateFolder('Section', parent_url, title, description,
                                    lang or self.cpsGetRandomLanguage())

    def cpsCreateWorkspace(self, parent_url, title,
                           description="ftest workspace for funkload testing.",
                           lang=None):
        """Create a workspace."""
        return self.cpsCreateFolder('Workspace', parent_url, title,
                                    description,
                                    lang or self.cpsGetRandomLanguage())

    def cpsCreateFolder(self, type, parent_url, title,
                        description, lang):
        """Create a section or a workspace.

        Return the section full url."""
        params = [["type_name", type],
                  ["widget__Title", title],
                  ["widget__Description",
                   description],
                  ["widget__LanguageSelectorCreation", lang],
                  ["widget__hidden_folder", "0"],
                  ["cpsdocument_create_button", "Create"]]
        self.post("%s/cpsdocument_create_form" % parent_url,
                  params, "Create a %s" % type)
        return self.cpsCleanUrl(self.getLastBaseUrl())

    def cpsCreateDocument(self, parent_url):
        """Create a simple random document.

        return a tuple: (doc_url, doc_id)
        """
        language = self.cpsGetRandomLanguage()
        title = self._lipsum.getSubject(uniq=True,
                                        prefix='test %s' % language)
        params = [["type_name", "Document"],
                  ["widget__Title", title],
                  ["widget__Description", self._lipsum.getSubject(10)],
                  ["widget__LanguageSelectorCreation", language],
                  ["widget__content", self._lipsum.getMessage()],
                  ["widget__content_rformat", "text"],
                  ["cpsdocument_create_button", "Create"]]
        self.post("%s/cpsdocument_create_form" % parent_url, params,
                  description="Creating a document")
        self.assert_(self.getLastUrl().find('psm_content_created')!=-1,
                     'Failed to create [%s] in %s/.' % (title, parent_url))
        doc_url = self.cpsCleanUrl(self.getLastBaseUrl())
        doc_id = doc_url.split('/')[-1]
        return doc_url, doc_id

    def cpsCreateNewsItem(self, parent_url):
        """Create a random news.

        return a tuple: (doc_url, doc_id)."""
        language = self.cpsGetRandomLanguage()
        title = self._lipsum.getSubject(uniq=True,
                                        prefix='test %s' % language)
        params = [["type_name", "News Item"],
                  ["widget__Title", title],
                  ["widget__Description", self._lipsum.getSubject(10)],
                  ["widget__LanguageSelectorCreation", language],
                  ["widget__photo_title", "none"],
                  ["widget__photo_filename", ""],
                  ["widget__photo_choice", "keep"],
                  ["widget__photo", ""],
                  ["widget__photo_resize", "img_auto_size"],
                  ["widget__photo_rposition", "left"],
                  ["widget__photo_subtitle", ""],
                  ["widget__content", self._lipsum.getMessage()],
                  ["widget__content_rformat", "text"],
                  ["widget__Subject:tokens:default", ""],
                  ["widget__Subject:list", "Business"],
                  # prevent invalid date depending on ui locale
                  ["widget__publication_date_date", time.strftime('01/01/%Y')],
                  ["widget__publication_date_hour", time.strftime('%H')],
                  ["widget__publication_date_minute", time.strftime('%M')],
                  ["cpsdocument_create_button", "Create"]]
        self.post("%s/cpsdocument_create_form" % parent_url, params,
                  description="Creating a news item")
        last_url = self.getLastUrl()
        self.assert_('psm_content_created' in last_url,
                     'Failed to create [%s] in %s/.' % (title, parent_url))
        doc_url = self.cpsCleanUrl(self.getLastBaseUrl())
        doc_id = doc_url.split('/')[-1]
        return doc_url, doc_id

    def cpsChangeUiLanguage(self, lang):
        """Change the ui language and return the referer page."""
        self.get("%s/cpsportlet_change_language" % self.server_url,
                 params=[['lang', lang]],
                 description="Change UI language to %s" % lang)


    # ------------------------------------------------------------
    # helpers
    #
    def cpsGetRandomLanguage(self):
        """Return a random language."""
        return random.choice(self._all_langs)

    def cpsGuessZopeUrl(self, cps_url=None):
        """Guess a zope url and site_id from a CPS Site url.

        return a tuple (zope_url, site_id)
        """
        if cps_url is None:
            cps_url = self.server_url
        site_id = cps_url.split('/')[-1]
        zope_url = cps_url[:-(len(site_id)+1)]
        return zope_url, site_id

    def cpsSearchDocId(self, doc_id):
        """Return the list of url that ends with doc_id.

        Using catalog search."""
        params = [["SearchableText", doc_id]]
        self.post("%s/search_form" % self.server_url, params,
                  description="Searching doc_id %s" % doc_id)
        ret = self.cpsListDocumentHref(pattern='%s$' % doc_id)
        self.logd('found %i link ends with %s' % (len(ret), doc_id))
        return ret

    def cpsCleanUrl(self, url_in):
        """Try to remove server_url and clean ending."""
        url = url_in
        server_url = self.server_url
        for ending in ('/', '/view', '/folder_contents',
                       '/folder_view', '/cpsdocument_metadata',
                       '/cpsdocument_edit_form'):
            if url.endswith(ending):
                url = url[:-len(ending)]
            if url.startswith(server_url):
                url = url[len(server_url):]
        return url

    def cpsListDocumentHref(self, pattern=None):
        """Return a clean list of document href that matches pattern.

        Try to remove server_url and other cps trailings,
        return a list of uniq url."""
        ret = []
        for href in [self.cpsCleanUrl(x) for x in self.listHref(pattern)]:
            if href not in ret:
                ret.append(href)
        return ret


########NEW FILE########
__FILENAME__ = CPS340DocTest
# (C) Copyright 2006 Nuxeo SAS <http://nuxeo.com>
# Author: Olivier Grisel ogrisel@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Doctest support for CPS340TestCase

$Id$
"""

from CPS340TestCase import CPSTestCase
from FunkLoadDocTest import FunkLoadDocTest


class CPSDocTest(FunkLoadDocTest, CPSTestCase):
    """Class to use to doctest a CPS portal

    >>> from CPS340DocTest import CPSDocTest
    >>> cps_url = 'http://localhost:8080/cps'
    >>> fl = CPSDocTest(cps_url)
    >>> fl.cps_test_case_version
    (3, 4, 0)
    >>> fl.server_url == cps_url
    True

    Then you can use the CPS340TestCase API like fl.cpsLogin('manager', 'pwd').
    """
    def __init__(self, server_url, debug=False, debug_level=1):
        """init CPSDocTest

        server_url is the CPS server url."""
        FunkLoadDocTest.__init__(self, debug=debug, debug_level=debug_level)
        # FunkLoadDocTest handles the init of FunkLoadTestCase which is the
        # same as CPSTestCase
        self.server_url = server_url

def _test():
    import doctest, CPS340DocTest
    return doctest.testmod(CPS340DocTest)

if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = CPS340TestCase
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad test case for Nuxeo CPS.

$Id: CPSTestCase.py 24728 2005-08-31 08:13:54Z bdelbosc $
"""
import time
import random
from Lipsum import Lipsum
from ZopeTestCase import ZopeTestCase
from webunit.utility import Upload

class CPSTestCase(ZopeTestCase):
    """Common CPS tasks.

    setUp must set a server_url attribute."""
    cps_test_case_version = (3, 4, 0)
    server_url = None
    _lipsum = Lipsum()
    _all_langs = ['en', 'fr', 'de', 'it', 'es', 'pt_BR',
                  'nl', 'mg', 'ro', 'eu']
    _default_langs = _all_langs[:4]
    _default_extensions = ['CPSForum:default',
                           'CPSSkins:cps3',
                           'CPSSubscriptions:default']
    _cps_login = None

    # ------------------------------------------------------------
    # cps actions
    #
    def cpsLogin(self, login, password, comment=None):
        """Log in a user.

        Raise on invalid credential."""
        self._cps_login = None
        params = [['__ac_name', login],
                  ['__ac_password', password],
                  ['__ac_persistent', 'on'],
                  ['submit', 'Login'],
                  ]
        self.post("%s/logged_in" % self.server_url, params,
                  description="Log in user [%s] %s" % (login, comment or ''))
        # assume we are logged in if we have a logout link...
        self.assert_([link for link in self.listHref()
                      if link.endswith('logout')],
                     'invalid credential: [%s:%s].' % (login, password))
        self._cps_login = login

    def cpsLogout(self):
        """Log out the current user."""
        if self._cps_login is not None:
            self.get('%s/logout' % self.server_url,
                     description="Log out [%s]" % self._cps_login)

    def cpsCreateSite(self, admin_id, admin_pwd,
                      manager_id, manager_password,
                      manager_mail, langs=None, title=None,
                      description=None,
                      interface="portlets",
                      zope_url=None,
                      site_id=None,
                      extensions=None):
        """Create a CPS Site.

        if zope_url or site_id is not provided guess them from the server_url.
        """
        if zope_url is None or site_id is None:
            zope_url, site_id = self.cpsGuessZopeUrl()
        self.setBasicAuth(admin_id, admin_pwd)
        params = {
            'site_id': site_id,
            'title': title or "FunkLoad CPS Portal",
            'manager_id': manager_id,
            'password': manager_password,
            'password_confirm': manager_password,
            'manager_email': manager_mail,
            'manager_firstname': 'Manager',
            'manager_lastname': 'CPS Manager',
            'extension_ids:list': extensions or self._default_extensions,
            'description': description or "A funkload cps test site",
            'languages:list': langs or self._default_langs,
            'submit': 'Add',
            'profile_id': 'CPSDefault:default'}
        self.post("%s/manage_addProduct/CPSDefault/addConfiguredCPSSite" %
                  zope_url, params, description="Create a CPS Site")
        self.clearBasicAuth()

    def cpsCreateGroup(self, group_name):
        """Create a cps group."""
        server_url = self.server_url
        params = [["dirname", "groups"],
                  ["id", ""],
                  ["widget__group", group_name],
                  ["widget__members:tokens:default", ""],
                  ["cpsdirectory_entry_create_form:method", "Create"]]
        self.post("%s/" % server_url, params)
        self.assert_(self.getLastUrl().find('psm_entry_created')!=-1,
                         'Failed to create group %s' % group_name)

    def cpsVerifyGroup(self, group_name):
        """Check existance or create a cps group."""
        server_url = self.server_url
        params = [["dirname", "groups"],
                  ["id", group_name],]
        if self.exists("%s/cpsdirectory_entry_view" % server_url, params,
                       description="Check that group [%s] exists."
                       % group_name):
            self.logd('Group %s exists.')
        else:
            self.cpsCreateGroup(group_name)

    def cpsCreateUser(self, user_id=None, user_pwd=None,
                      user_givenName=None, user_sn=None,
                      user_email=None, groups=None):
        """Create a cps user with the Member role.

        return login, pwd"""
        lipsum = self._lipsum
        sign = lipsum.getUniqWord()
        user_id = user_id or 'fl_' + sign.lower()
        user_givenName = user_givenName or lipsum.getWord().capitalize()
        user_sn = user_sn or user_id.upper()
        user_email = user_email or "root@127.0.0.01"
        user_pwd = user_pwd or lipsum.getUniqWord(length_min=6)
        params = [["dirname", "members"],
                  ["id", ""],
                  ["widget__id", user_id],
                  ["widget__password", user_pwd],
                  ["widget__confirm", user_pwd],
                  ["widget__givenName", user_givenName],
                  ["widget__sn", user_sn],
                  ["widget__email", user_email],
                  ["widget__roles:tokens:default", ""],
                  ["widget__roles:list", "Member"],
                  ["widget__groups:tokens:default", ""],
                  ["widget__homeless:boolean", "False"],
                  ["cpsdirectory_entry_create_form:method", "Create"]]
        for group in groups:
            params.append(["widget__groups:list", group])
        self.post("%s/" % self.server_url, params,
                  description="Create user [%s]" % user_id)
        self.assert_(self.getLastUrl().find('psm_entry_created')!=-1,
                     'Failed to create user %s' % user_id)
        return user_id, user_pwd

    def cpsVerifyUser(self, user_id=None, user_pwd=None,
                      user_givenName=None, user_sn=None,
                      user_email=None, groups=None):
        """Verify if user exists or create him.

        return login, pwd

        if user exists pwd is None.
        """
        if user_id:
            params = [["dirname", "members"],
                      ["id", user_id],]
            if self.exists(
                "%s/cpsdirectory_entry_view" % self.server_url, params):
                self.logd('User %s exists.')
                return user_id, None

        return self.cpsCreateUser(user_id, user_pwd, user_givenName,
                                  user_sn, user_email, groups)

    def cpsSetLocalRole(self, url, name, role):
        """Setup local role role to url."""
        params = [["member_ids:list", name],
                  ["member_role", role]]
        self.post("%s/folder_localrole_add" % url, params,
                  description="Grant local role %s to %s" % (role, name))

    def cpsCreateSection(self, parent_url, title,
                         description="ftest section for funkload testing.",
                         lang=None):
        """Create a section."""
        return self.cpsCreateFolder('Section', parent_url, title, description,
                                    lang or self.cpsGetRandomLanguage())

    def cpsCreateWorkspace(self, parent_url, title,
                           description="ftest workspace for funkload testing.",
                           lang=None):
        """Create a workspace."""
        return self.cpsCreateFolder('Workspace', parent_url, title,
                                    description,
                                    lang or self.cpsGetRandomLanguage())

    def cpsCreateFolder(self, type, parent_url, title,
                        description, lang):
        """Create a section or a workspace.

        Return the section full url."""
        params = [["type_name", type],
                  ["widget__Title", title],
                  ["widget__Description",
                   description],
                  ["widget__LanguageSelectorCreation", lang],
                  ["widget__hidden_folder:boolean", False],
                  ["cpsdocument_create_button", "Create"]]
        self.post("%s/cpsdocument_create" % parent_url,
                  params, "Create a %s" % type)
        return self.cpsCleanUrl(self.getLastBaseUrl())

    def cpsCreateDocument(self, parent_url):
        """Create a simple random document.

        return a tuple: (doc_url, doc_id)
        """
        language = self.cpsGetRandomLanguage()
        title = self._lipsum.getSubject(uniq=True,
                                        prefix='test %s' % language)
        params = [["type_name", "Document"],
                  ["widget__Title", title],
                  ["widget__Description", self._lipsum.getSubject(10)],
                  ["widget__LanguageSelectorCreation", language],
                  ["widget__content", self._lipsum.getMessage()],
                  ["widget__content_rformat", "text"],
                  ["cpsdocument_create_button", "Create"]]
        self.post("%s/cpsdocument_create" % parent_url, params,
                  description="Creating a document")
        self.assert_(self.getLastUrl().find('psm_content_created')!=-1,
                     'Failed to create [%s] in %s/.' % (title, parent_url))
        doc_url = self.cpsCleanUrl(self.getLastBaseUrl())
        doc_id = doc_url.split('/')[-1]
        return doc_url, doc_id

    def cpsCreateNewsItem(self, parent_url, photo_path=None):
        """Create a random news.

        return a tuple: (doc_url, doc_id)."""
        language = self.cpsGetRandomLanguage()
        title = self._lipsum.getSubject(uniq=True,
                                        prefix='test %s' % language)
        params = [["cpsformuid", self._lipsum.getUniqWord()],
                  ["type_name", "News Item"],
                  ["widget__Title", title],
                  ["widget__Description", self._lipsum.getSubject(10)],
                  ['widget__photo_filename', ''],
                  ['widget__photo_choice', photo_path and 'change' or 'keep'],
                  ['widget__photo', Upload(photo_path or '')],
                  ['widget__photo_resize', 'img_auto_size'],
                  ['widget__photo_rposition', 'left'],
                  ['widget__photo_subtitle', ''],
                  ["widget__content", self._lipsum.getMessage()],
                  ["widget__content_rformat", "text"],
                  ['widget__content_fileupload', Upload('')],
                  ["widget__Subject:tokens:default", ""],
                  ["widget__Subject:list", "Business"],
                  # prevent invalid date depending on ui locale
                  ["widget__publication_date_date", time.strftime('01/01/%Y')],
                  ["widget__publication_date_hour", time.strftime('%H')],
                  ["widget__publication_date_minute", time.strftime('%M')],
                  ["cpsdocument_create_button", "Create"]]
        self.post("%s/cpsdocument_create" % parent_url, params,
                  description="Creating a news item")
        last_url = self.getLastUrl()
        self.assert_('psm_content_created' in last_url,
                     'Failed to create [%s] in %s/.' % (title, parent_url))
        doc_url = self.cpsCleanUrl(self.getLastBaseUrl())
        doc_id = doc_url.split('/')[-1]
        return doc_url, doc_id

    def cpsChangeUiLanguage(self, lang):
        """Change the ui language and return the referer page."""
        self.get("%s/cpsportlet_change_language" % self.server_url,
                 params=[['lang', lang]],
                 description="Change UI language to %s" % lang)


    # ------------------------------------------------------------
    # helpers
    #
    def cpsGetRandomLanguage(self):
        """Return a random language."""
        return random.choice(self._all_langs)

    def cpsGuessZopeUrl(self, cps_url=None):
        """Guess a zope url and site_id from a CPS Site url.

        return a tuple (zope_url, site_id)
        """
        if cps_url is None:
            cps_url = self.server_url
        site_id = cps_url.split('/')[-1]
        zope_url = cps_url[:-(len(site_id)+1)]
        return zope_url, site_id

    def cpsSearchDocId(self, doc_id):
        """Return the list of url that ends with doc_id.

        Using catalog search."""
        params = [["SearchableText", doc_id]]
        self.post("%s/search_form" % self.server_url, params,
                  description="Searching doc_id %s" % doc_id)
        ret = self.cpsListDocumentHref(pattern='%s$' % doc_id)
        self.logd('found %i link ends with %s' % (len(ret), doc_id))
        return ret

    def cpsCleanUrl(self, url_in):
        """Try to remove server_url and clean ending."""
        url = url_in
        server_url = self.server_url
        for ending in ('/', '/view', '/folder_contents',
                       '/folder_view', '/cpsdocument_metadata',
                       '/cpsdocument_edit_form'):
            if url.endswith(ending):
                url = url[:-len(ending)]
            if url.startswith(server_url):
                url = url[len(server_url):]
        return url

    def cpsListDocumentHref(self, pattern=None):
        """Return a clean list of document href that matches pattern.

        Try to remove server_url and other cps trailings,
        return a list of uniq url."""
        ret = []
        for href in [self.cpsCleanUrl(x) for x in self.listHref(pattern)]:
            if href not in ret:
                ret.append(href)
        return ret


########NEW FILE########
__FILENAME__ = CPSTestCase
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad test case for Nuxeo CPS.

$Id: CPSTestCase.py 24728 2005-08-31 08:13:54Z bdelbosc $
"""
from CPS340TestCase import CPSTestCase

########NEW FILE########
__FILENAME__ = ZopeTestCase
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad test case for Zope.

$Id$
"""
import time
from socket import error as SocketError
from FunkLoadTestCase import FunkLoadTestCase


class ZopeTestCase(FunkLoadTestCase):
    """Common zope 2.8 tasks."""

    def zopeRestart(self, zope_url, admin_id, admin_pwd, time_out=600):
        """Stop and Start Zope server."""
        self.setBasicAuth(admin_id, admin_pwd)
        params = {"manage_restart:action": "Restart"}
        url = "%s/Control_Panel" % zope_url
        self.post(url, params, description="Restarting Zope server")
        down = True
        time_start = time.time()
        while(down):
            time.sleep(2)
            try:
                self.get(url, description="Checking zope presence")
            except SocketError:
                if time.time() - time_start > time_out:
                    self.fail('Zope restart time out %ss' % time_out)
            else:
                down = False

        self.clearBasicAuth()

    def zopePackZodb(self, zope_url, admin_id, admin_pwd,
                     database="main", days=0):
        """Pack a zodb database."""
        self.setBasicAuth(admin_id, admin_pwd)
        url = '%s/Control_Panel/Database/%s/manage_pack' % (
            zope_url, database)
        params = {'days:float': str(days)}
        resp = self.post(url, params,
                         description="Packing %s Zodb, removing previous "
                         "revisions of objects that are older than %s day(s)."
                         % (database, days), ok_codes=[200, 302, 500])
        if resp.code == 500:
            if self.getBody().find(
                "Error Value: The database has already been packed") == -1:
                self.fail("Pack_zodb return a code 500.")
            else:
                self.logd('Zodb has already been packed.')
        self.clearBasicAuth()

    def zopeFlushCache(self, zope_url, admin_id, admin_pwd, database="main"):
        """Remove all objects from all ZODB in-memory caches."""
        self.setBasicAuth(admin_id, admin_pwd)
        url = "%s/Control_Panel/Database/%s/manage_minimize" % (zope_url,
                                                                database)
        self.get(url, description="Flush %s Zodb cache" % database)

    def zopeAddExternalMethod(self, parent_url, admin_id, admin_pwd,
                              method_id, module, function,
                              run_it=True):
        """Add an External method an run it."""
        self.setBasicAuth(admin_id, admin_pwd)
        params = [["id", method_id],
                  ["title", ""],
                  ["module", module],
                  ["function", function],
                  ["submit", " Add "]]
        url = parent_url
        url += "/manage_addProduct/ExternalMethod/manage_addExternalMethod"
        resp = self.post(url, params, ok_codes=[200, 302, 400],
                         description="Adding %s external method" % method_id)
        if resp.code == 400:
            if self.getBody().find('is invalid - it is already in use.') == -1:
                self.fail('Error got 400 on manage_addExternalMethod')
            else:
                self.logd('External method already exists')
        if run_it:
            self.get('%s/%s' % (parent_url, method_id),
                     description="Execute %s external method" % method_id)
        self.clearBasicAuth()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
import views
from django.views.generic.simple import direct_to_template
from django.http import HttpResponse

urlpatterns = patterns('',
    # Example:
    (r'get', views.getter),
    (r'put', views.putter),
    (r'delete', views.deleter),
    (r'post', views.poster))

########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.http import HttpResponse,HttpResponseRedirect
import django.http

def getter(request):
    return HttpResponseRedirect("/fltest/_getter/")
def poster(request):
    return HttpResponseRedirect("/fltest/_poster")
def putter(request):
    return HttpResponseRedirect("/fltest/_putter")
def deleter(request):
    return HttpResponseRedirect("/fltest/_deleter")



########NEW FILE########
__FILENAME__ = settings
# Django settings for fltest project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = '/home/ali/_dev/eclipse/fltest/sqlite.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'f+q#v(p8q)*14u^i1)0^&a+f0@i7!n_0%lzr4wavocpj2nya71'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'fltest.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponse,HttpResponseNotAllowed
import datetime

def _getter( request ):
    if request.method == "GET":
        now = datetime.datetime.now()
        html = "<html><body>It is now %s.</body></html>" % now
        return HttpResponse(html)
    else:
        return HttpResponseNotAllowed("only gets")

def _poster( request ):
    if request.method == "POST":
        now = datetime.datetime.now()
        html = "<html><body>It is now %s.</body></html>" % now
        return HttpResponse(html)
    else:
        return HttpResponseNotAllowed("only posts")

def _deleter( request ):
    if request.method == "DELETE":
        now = datetime.datetime.now()
        html = "<html><body>It is now %s.</body></html>" % now
        return HttpResponse(html)
    else:
        return HttpResponseNotAllowed("only deletes")

def _putter( request ):
    if request.method == "PUT":
        now = datetime.datetime.now()
        html = "<html><body>It is now %s.</body></html>" % now
        return HttpResponse(html)
    else:
        return HttpResponseNotAllowed("only puts")


urlpatterns = patterns('',
    # Example:
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': '/tmp/snapshots'}),

    (r'^fltest/methods',include('fltest.methods.urls')),
    (r'^fltest/_getter', _getter),
    (r'^fltest/_putter', _putter),
    (r'^fltest/_deleter',_deleter),
    (r'^fltest/_poster', _poster),
)

########NEW FILE########
__FILENAME__ = test_SeamBooking
# -*- coding: iso-8859-15 -*-
"""seam_booking FunkLoad test

$Id$
"""
import unittest
import random
from funkload.FunkLoadTestCase import FunkLoadTestCase
from webunit.utility import Upload
from funkload.utils import Data
from funkload.Lipsum import Lipsum


class SeamBooking(FunkLoadTestCase):
    """Simple test to register a new user and book an hotel.

    This test use a configuration file SeamBooking.conf.
    """

    jsf_tag_tree = '<input type="hidden" name="jsf_tree_64" id="jsf_tree_64" value="'
    jsf_tag_state = '<input type="hidden" name="jsf_state_64" id="jsf_state_64" value="'

    hotel_names = ["Tower", "Ritz", "Sea", "Hotel"]
    nb_letters = 3        # number of letter to type when searching an hotel
    password = "password" # password used for users

    def jsfParams(self, params):
        """Helper to extarct jsf states from the last page and add them to the params."""
        html = self.getBody()
        tag = self.jsf_tag_tree
        start = html.find(tag) + len(tag)
        end = html.find('"', start)
        if start < 0 or end < 0:
            raise ValueError('No Jsf STATE TREE found in the previous page.')
        state = html[start:end]
        params.insert(0, ["jsf_tree_64", state])
        tag = self.jsf_tag_state
        start = html.find(tag) + len(tag)
        end = html.find('"', start)
        if start < 0 or end < 0:
            raise ValueError('No Jsf STATE STATE found in the previous page.')
        state = html[start:end]
        params.insert(1, ["jsf_state_64", state])
        return params


    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')
        self.lipsum = Lipsum()


    def test_seam_booking(self):
        # The description should be set in the configuration file
        server_url = self.server_url

        self.get(server_url + "/seam-booking/home.seam",
            description="Booking home page")
        register_link = self.listHref(content_pattern="Register New User")
        self.assert_(len(register_link), "Register link not found")
        register_link = register_link[0]

        self.get(server_url + register_link,
                 description="Register new User")
        self.assert_("register_SUBMIT" in self.getBody(),
                     "Failing to view Registration page.")

        username = self.lipsum.getUniqWord()
        realname = username + " " + self.lipsum.getUniqWord()
        password = self.password

        self.post(server_url + "/seam-booking/register.seam", self.jsfParams(params=[
            ['register:username', username],
            ['register:name', realname],
            ['register:password', password],
            ['register:verify', password],
            ['register:register', 'Register'],
            ['register_SUBMIT', '1'],
            ['register:_link_hidden_', ''],
            ['jsf_viewid', '/register.xhtml']]),
            description="Submit register form")
        self.assert_("Successfully registered as" in self.getBody(),
                     "Failing register new user.")
        params = self.jsfParams(params=[
            ['login:username', username],
            ['login:password', password],
            ['login:login', 'Account Login'],
            ['login_SUBMIT', '1'],
            ['login:_link_hidden_', ''],
            ['jsf_viewid', '/home.xhtml']])
        self.post(server_url + "/seam-booking/home.seam", params,
            description="Submit account login")
        self.assert_(username in self.getBody(),
                     "Failing login new user %s:%s" % (username, password) + str(params))
        self.assert_("No Bookings Found" in self.getBody(),
                     "Weird there should be no booking for new user %s:%s" %
                     (username, password))

        # Simulate ajax search for an hotel by typing nb_letters
        nb_letters = self.nb_letters
        hotel_query = random.choice(self.hotel_names)
        for i in range(1, nb_letters + 1):
            self.post(server_url + "/seam-booking/main.seam", self.jsfParams(params=[
            ['AJAXREQUEST', '_viewRoot'],
            ['main:searchString', hotel_query[:i]],
            ['main:pageSize', '10'],
            ['main_SUBMIT', '1'],
            ['jsf_viewid', '/main.xhtml'],
            ['main:findHotels', 'main:findHotels']]),
            description="Ajax search %i letter" % i)
            self.assert_("View Hotel" in self.getBody(),
                         "No match for search hotel.")

        # Extract the list of link to hotel and choose a random one
        hotel_links = self.listHref(content_pattern="View Hotel")
        self.get(server_url + random.choice(hotel_links),
                 description="View a random hotel in the result list")
        self.assert_("hotel_SUBMIT" in self.getBody())

        self.post(server_url + "/seam-booking/hotel.seam", self.jsfParams(params=[
            ['hotel:bookHotel', 'Book Hotel'],
            ['hotel_SUBMIT', '1'],
            ['hotel:_link_hidden_', ''],
            ['jsf_viewid', '/hotel.xhtml']]),
            description="Book hotel")
        self.assert_("booking_SUBMIT" in self.getBody())

        self.post(server_url + "/seam-booking/book.seam", self.jsfParams(params=[
            ['booking:checkinDate', '11/07/2008'],
            ['booking:checkoutDate', '11/08/2008'],
            ['booking:beds', '1'],
            ['booking:smoking', 'false'],
            ['booking:creditCard', '1234567890123456'],
            ['booking:creditCardName', realname],
            ['booking:creditCardExpiryMonth', '1'],
            ['booking:creditCardExpiryYear', '2009'],
            ['booking:proceed', 'Proceed'],
            ['booking_SUBMIT', '1'],
            ['booking:_link_hidden_', ''],
            ['jsf_viewid', '/book.xhtml']]),
            description="Proceed booking")
        self.assert_("confirm_SUBMIT" in self.getBody())

        self.post(server_url + "/seam-booking/confirm.seam", self.jsfParams(params=[
            ['confirm:confirm', 'Confirm'],
            ['confirm_SUBMIT', '1'],
            ['confirm:_link_hidden_', ''],
            ['jsf_viewid', '/confirm.xhtml']]),
            description="Confirm booking")
        self.assert_("No Bookings Found" not in self.getBody(),
                     "Booking is not taken in account.")

        # Logout
        logout_link = self.listHref(content_pattern="Logout")
        self.assert_(len(logout_link), "Logout link not found")
        logout_link = logout_link[0]
        self.get(server_url + logout_link,
            description="Logout")
        self.assert_("login_SUBMIT" in self.getBody())

        # end of test -----------------------------------------------

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")


if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = test_Simple
# -*- coding: iso-8859-15 -*-
"""Simple FunkLoad test

$Id$
"""
import unittest
from random import random
from funkload.FunkLoadTestCase import FunkLoadTestCase

class Simple(FunkLoadTestCase):
    """This test use a configuration file Simple.conf."""

    def setUp(self):
        """Setting up test."""
        self.server_url = self.conf_get('main', 'url')

    def test_simple(self):
        # The description should be set in the configuration file
        server_url = self.server_url
        # begin test ---------------------------------------------
        nb_time = self.conf_getInt('test_simple', 'nb_time')
        for i in range(nb_time):
            self.get(server_url, description='Get URL')
        # end test -----------------------------------------------


if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = test_Credential
# -*- coding: iso-8859-15 -*-
"""Simple FunkLoad test

$Id$
"""
import unittest
from random import random
from funkload.FunkLoadTestCase import FunkLoadTestCase

class Credential(FunkLoadTestCase):
    """This test use a configuration file Credential.conf."""

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')

    def test_credential(self):
        server_url = self.server_url
        ret = self.xmlrpc(server_url, 'getStatus',
                          description="Check getStatus")
        self.assert_('running' in ret, 'Server is down %s' % ret)
        self.logd('ret %s' % ret)

        ret = self.xmlrpc(server_url, 'getCredential',
                          description="Get a credential from a file")
        self.logd('ret %s' % ret)
        self.assertEquals(len(ret), 2, 'Invalid return %s' % ret)

        ret = self.xmlrpc(server_url, 'listGroups',
                          description="list groups from the group file")
        self.logd('ret %s' % ret)
        a_group = ret[0]

        ret = self.xmlrpc(server_url, 'listCredentials',
                          description="list all credential of the file")
        self.logd('ret %s' % ret)

        ret = self.xmlrpc(server_url, 'listCredentials', (a_group,),
                          description="list credentials of group " +
                          a_group)
        self.logd('ret %s' % ret)


    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")


if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = test_Zope
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Simple funkload zope tests

$Id$
"""
import unittest
from funkload.ZopeTestCase import ZopeTestCase
from funkload.Lipsum import Lipsum


class Zope(ZopeTestCase):
    """Testing the funkload ZopeTestCase

    This test use a configuration file Zope.conf.
    """

    def setUp(self):
        """Setting up test."""
        self.logd("setUp.")
        self.zope_url = self.conf_get('main', 'url')
        self.admin_id = self.conf_get('main', 'admin_id')
        self.admin_pwd = self.conf_get('main', 'admin_pwd')

    def test_flushCache(self):
        self.zopeFlushCache(self.zope_url, self.admin_id, self.admin_pwd)

    def test_restart(self):
        self.zopeRestart(self.zope_url, self.admin_id, self.admin_pwd,
                         time_out=10)

    def test_packZodb(self):
        self.zopePackZodb(self.zope_url, self.admin_id, self.admin_pwd)

    def test_00_verifyExample(self):
        if not self.exists(self.zope_url + '/Examples'):
            self.setBasicAuth(self.admin_id, self.admin_pwd)
            self.get(self.zope_url +
                     '/manage_importObject?file=Examples.zexp&set_owner:int=1')
            self.assert_('successfully imported' in self.getBody())
            self.clearBasicAuth()
        self.get(self.zope_url + '/Examples')

    def test_exampleNavigation(self):
        server_url = self.zope_url

        self.get("%s/Examples" % server_url)
        self.get("%s/Examples/Navigation" % server_url)
        self.get("%s/Examples/Navigation/Mammals" % server_url)
        self.get("%s/Examples/Navigation/Mammals/Primates" % server_url)
        self.get("%s/Examples/Navigation/Mammals/Primates/Monkeys" % server_url)
        self.get("%s/Examples/Navigation/Mammals/Whales" % server_url)
        self.get("%s/Examples/Navigation/Mammals/Bats" % server_url)
        self.get("%s/Examples" % server_url)


    def test_exampleGuestBook(self):
        server_url = self.zope_url
        self.get("%s/Examples/GuestBook" % server_url)
        server_url = self.zope_url
        self.setBasicAuth(self.admin_id, self.admin_pwd)
        lipsum = Lipsum()
        self.get("%s/Examples/GuestBook/addEntry.html" % server_url)
        params = [["guest_name", lipsum.getWord().capitalize()],
                  ["comments", lipsum.getParagraph()]]
        self.post("%s/Examples/GuestBook/addEntry" % server_url, params)
        self.clearBasicAuth()


    def test_exampleFileLibrary(self):
        server_url = self.zope_url
        self.get("%s/Examples/FileLibrary" % server_url)
        for sort in ('type', 'size', 'date'):
            params = [["sort", sort],
                      ["reverse:int", "0"]]
            self.post("%s/Examples/FileLibrary/index_html" % server_url,
                      params,
                      description="File Library sort by %s" % sort)

    def test_exampleShoppingCart(self):
        server_url = self.zope_url

        self.get("%s/Examples/ShoppingCart" % server_url)
        params = [["orders.id:records", "510-115"],
                  ["orders.quantity:records", "1"],
                  ["orders.id:records", "510-122"],
                  ["orders.quantity:records", "2"],
                  ["orders.id:records", "510-007"],
                  ["orders.quantity:records", "3"]]
        self.post("%s/Examples/ShoppingCart/addItems" % server_url, params)


    def test_anonymous_reader(self):
        server_url = self.zope_url
        self.get("%s/Examples/Navigation/Mammals/Whales" % server_url)
        self.get("%s/Examples/GuestBook" % server_url)
        self.get("%s/Examples/GuestBook/addEntry.html" % server_url)
        params = [["sort", 'date'],
                  ["reverse:int", "0"]]
        self.get("%s/Examples/FileLibrary/index_html" % server_url, params)
        self.get("%s/Examples/ShoppingCart" % server_url)

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.")

if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = DemoInstaller
"""Extract the demo from the funkload egg into the current path."""

import os
from shutil import copytree
from pkg_resources import resource_filename, cleanup_resources

def main():
    """main."""
    demo_path = 'funkload-demo'
    print "Extract FunkLoad examples into ./%s : ... " % demo_path,
    cache_path = resource_filename('funkload', 'demo')
    demo_path = os.path.join(os.path.abspath(os.path.curdir), demo_path)
    copytree(cache_path, demo_path)
    cleanup_resources()
    print "done."


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = Distributed
#!/usr/bin/python
# Author: Ali-Akber Saifee
# Contributors: Andrew McFague
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
import os
import platform
import re
import socket
import threading
import time
from datetime import datetime
from socket import error as SocketError
from stat import S_ISREG, S_ISDIR
from glob import glob
from xml.etree.ElementTree import ElementTree
from xmlrpclib import ServerProxy
import json
import sys

import paramiko

from utils import mmn_encode, trace, package_tests, get_virtualenv_script, \
    get_version

try:
    from funkload.rtfeedback import (FeedbackPublisher,
                                     DEFAULT_ENDPOINT, DEFAULT_PUBSUB)
    LIVE_FEEDBACK = True
except ImportError:
    LIVE_FEEDBACK = False
    DEFAULT_PUBSUB = DEFAULT_ENDPOINT = None


def load_module(test_module):
    module = __import__(test_module)
    parts = test_module.split('.')[1:]
    while parts:
        part = parts.pop()
        module = getattr(module, part)
    return module


def load_unittest(test_module, test_class, test_name, options):
    """instantiate a unittest."""
    module = load_module(test_module)
    klass = getattr(module, test_class)
    return klass(test_name, options)


def _print_rt(msg):
    msg = json.loads(msg[0])
    if msg['result'] == 'failure':
        sys.stdout.write('F')
    else:
        sys.stdout.write('.')
    sys.stdout.flush()


class DistributorBase(object):
    """
    base class for any XXXDistributor objects that can be used
    to distribute benches accross multiple machines.
    """
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.connected = False


def requiresconnection(fn):
    """
    decorator for :class:`~SSHDistributor`
    object that raises a runtime exception upon calling methods
    if the object hasn't been connected properly.
    """
    def _requiresconnect(self, *args, **kwargs):
        if not self.connected:
            raise RuntimeError(
                "%s requires an ssh connection to be created" % fn.func_name)
        return fn(self, *args, **kwargs)
    _requiresconnect.__name__ = fn.__name__
    _requiresconnect.__doc__ = fn.__doc__
    return _requiresconnect


class SSHDistributor(DistributorBase):
    """
    Provides commands to perform distirbuted actions
    using an ssh connection (depends on paramiko). Essentially
    used by :class:`~DistributionMgr`.

    """
    def __init__(self, name, host, username=None, password=None,
                 key_filename=None, channel_timeout=None):
        """
        performs authentication and tries to connect to the
        `host`.
        """
        DistributorBase.__init__(self, host, username, password)

        self.connection = paramiko.client.SSHClient()
        self.connection.load_system_host_keys()
        self.connection.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.error = ""
        self.name = name  # So we can have multiples tests per host
        self.channel_timeout = channel_timeout
        credentials = {}
        if username and password:
            credentials = {"username": username, "password": password}
        elif username and key_filename:
            credentials = {"username": username, "key_filename": key_filename}
        elif username:
            credentials = {"username": username}
        host_port = host.split(':')
        if len(host_port) > 1:
            host = host_port[0]
            port = int(host_port[1])
        else:
            port = 22
        try:
            # print "connect to " + host + " port " + str(port)  + " " + str(credentials)
            self.connection.connect(host, timeout=5, port=port, **credentials)
            self.connected = True
        except socket.gaierror, error:
            self.error = error
        except socket.timeout, error:
            self.error = error
        self.killed = False

    @requiresconnection
    def get(self, remote_path, local_path):
        """
        performs a copy from ``remote_path`` to ``local_path``.
        For performing the inverse operation, use the :meth:`put`
        """
        try:
            sftp = self.connection.open_sftp()
            sftp.get(remote_path, local_path)
        except Exception, error:
            trace("failed to get %s->%s with error %s\n" %
                  (local_path, remote_path, error))

    @requiresconnection
    def put(self, local_path, remote_path):
        """
        performs a copy from `local_path` to `remote_path`
        For performing the inverse operation, use the :meth:`get`
        """
        try:
            sftp = self.connection.open_sftp()
            sftp.put(local_path, remote_path)
        except Exception, error:
            trace("failed to put %s->%s with error %s\n" %
                  (local_path, remote_path, error))

    @requiresconnection
    def execute(self, cmd_string, shell_interpreter="bash -c", cwdir=None):
        """
        evaluated the command specified by ``cmd_string`` in the context
        of ``cwdir`` if it is specified. The optional ``shell_interpreter``
        parameter allows overloading the default bash.
        """
        obj = self.threaded_execute(cmd_string, shell_interpreter, cwdir)
        obj.join()
        out = ""
        err = ""
        while True:
            if self.killed:
                break
            e = obj.err.read(1)
            err += e
            #trace(e)
            o = obj.output.read(1)
            out += o
            #trace(o)
            if not o and not e:
                break

        return out, err

    @requiresconnection
    def threaded_execute(self, cmd_string, shell_interpreter="bash -c",
                         cwdir=None):
        """
        basically the same as :meth:`execute` execept that it returns
        a started :mod:`threading.Thread` object instead of the output.
        """
        class ThreadedExec(threading.Thread):
            "simple Thread wrapper on :meth:`execute`"
            # FIXME Remove the dependency on self.connection
            def __init__(self_, cmd_string, shell_interpreter, cwdir):
                threading.Thread.__init__(self_)
                self_.cmd_string = cmd_string
                self_.shell_interpreter = shell_interpreter
                self_.cwdir = cwdir

            def run(self_):
                exec_str = ""
                if self_.cwdir:
                    exec_str += "pushd .; cd %s;" % cwdir
                exec_str += "%s \"%s\"" % (
                    self_.shell_interpreter, self_.cmd_string)
                if self_.cwdir:
                    exec_str += "; popd;"
                #trace("DEBUG: %s\n" %exec_str)
                try:
                    self_.input, self_.output, self_.err = \
                        self_.exec_command(self.connection, exec_str,
                                           bufsize=1,
                                           timeout=self.channel_timeout)
                except Exception, e:
                    if not self.killed:
                        raise

            def exec_command(self, connection, command, bufsize=-1, timeout=None):
                # Override to set timeout properly see
                # http://mohangk.org/blog/2011/07/paramiko-sshclient-exec_command-timeout-workaround/
                chan = connection._transport.open_session()
                chan.settimeout(timeout)
                print command
                chan.exec_command(command)
                stdin = chan.makefile('wb', bufsize)
                stdout = chan.makefile('rb', bufsize)
                stderr = chan.makefile_stderr('rb', bufsize)
                return stdin, stdout, stderr

        th_obj = ThreadedExec(cmd_string, shell_interpreter, cwdir)
        th_obj.start()
        return th_obj

    @requiresconnection
    def isdir(self, remote_path):
        """
        test to see if the path pointing to ``remote_dir``
        exists as a directory.
        """
        try:
            sftp = self.connection.open_sftp()
            st = sftp.stat(remote_path)
            return S_ISDIR(st.st_mode)
        except Exception:
            return False

    @requiresconnection
    def isfile(self, remote_path):
        """
        test to see if the path pointing to ``remote_path``
        exists as a file.
        """
        try:
            sftp = self.connection.open_sftp()
            st = sftp.stat(remote_path)
            return S_ISREG(st.st_mode)
        except Exception:
            return False

    def die(self):
        """
        kills the ssh connection
        """
        self.connection.close()
        self.killed = True


class DistributionMgr(threading.Thread):
    """
    Interface for use by :mod:`funkload.TestRunner` to distribute
    the bench over multiple machines.
    """
    def __init__(self, module_name, class_name, method_name, options,
                 cmd_args):
        """
        mirrors the initialization of :class:`funkload.BenchRunner.BenchRunner`
        """
        # store the args. these can be passed to BenchRunner later.
        self.module_name = module_name
        self.class_name = class_name
        self.method_name = method_name
        self.options = options
        self.cmd_args = cmd_args

        wanted = lambda x: ('--distribute' not in x) and ('discover' != x)
        self.cmd_args = filter(wanted, self.cmd_args)
        self.cmd_args.append("--is-distributed")
        # ? Won't this double the --feedback option?
        if options.feedback:
            self.cmd_args.append("--feedback")

        module = load_module(module_name)
        module_file = module.__file__
        self.tarred_tests, self.tarred_testsdir = package_tests(module_file)

        self.remote_res_dir = "/tmp/funkload-bench-sandbox/"

        test = load_unittest(self.module_name, class_name,
                             mmn_encode(method_name, 0, 0, 0), options)

        self.config_path = test._config_path
        self.result_path = test.result_path
        self.class_title = test.conf_get('main', 'title')
        self.class_description = test.conf_get('main', 'description')
        self.test_id = self.method_name
        self.test_url = test.conf_get('main', 'url')
        self.cycles = map(int, test.conf_getList('bench', 'cycles'))
        self.duration = test.conf_getInt('bench', 'duration')
        self.startup_delay = test.conf_getFloat('bench', 'startup_delay')
        self.cycle_time = test.conf_getFloat('bench', 'cycle_time')
        self.sleep_time = test.conf_getFloat('bench', 'sleep_time')
        self.sleep_time_min = test.conf_getFloat('bench', 'sleep_time_min')
        self.sleep_time_max = test.conf_getFloat('bench', 'sleep_time_max')
        if test.conf_get('distribute', 'channel_timeout', '', quiet=True):
            self.channel_timeout = test.conf_getFloat(
                'distribute', 'channel_timeout')
        else:
            self.channel_timeout = None
        self.threads = []  # Contains list of ThreadData objects
        self.last_thread_id = -1
        self.thread_creation_lock = threading.Lock()

        if options.python_bin:
            self.python_bin = options.python_bin
        else:
            self.python_bin = test.conf_get(
                'distribute', 'python_bin', 'python')

        if options.distributed_packages:
            self.distributed_packages = options.distributed_packages
        else:
            self.distributed_packages = test.conf_get(
                'distribute', 'packages', '')

        try:
            desc = getattr(test, self.method_name).__doc__.strip()
        except:
            desc = ""
        self.test_description = test.conf_get(self.method_name, 'description',
                                              desc)
        # make a collection output location
        if options.distributed_log_path:
            self.distribution_output = options.distributed_log_path
        elif test.conf_get('distribute', 'log_path', '', quiet=True):
            self.distribution_output = test.conf_get('distribute', 'log_path')
        else:
            raise UserWarning("log_path isn't defined in section [distribute]")

        # check if user has overridden the default funkload distro download
        # location this will be used to download funkload on the worker nodes.
        self.funkload_location = test.conf_get(
            'distribute', 'funkload_location', 'funkload')

        if not os.path.isdir(self.distribution_output):
            os.makedirs(self.distribution_output)

        # check if hosts are in options
        workers = []                  # list of (host, port, descr)
        if options.workerlist:
            for h in options.workerlist.split(","):
                cred_host = h.split("@")
                if len(cred_host) == 1:
                    uname, pwd, host = None, None, cred_host[0]
                else:
                    cred = cred_host[0]
                    host = cred_host[1]
                    uname_pwd = cred.split(":")
                    if len(uname_pwd) == 1:
                        uname, pwd = uname_pwd[0], None
                    else:
                        uname, pwd = uname_pwd

                worker = {"name": host.replace(":", "_"),
                          "host": host,
                          "password": pwd,
                          "username": uname,
                          "channel_timeout": self.channel_timeout}

                if options.distributed_key_filename:
                    worker['key_filename'] = options.distributed_key_filename

                workers.append(worker)
        else:
            hosts = test.conf_get('workers', 'hosts', '', quiet=True).split()
            for host in hosts:
                host = host.strip()
                if options.distributed_key_filename:
                    key_filename = options.distributed_key_filename
                else:
                    key_filename = test.conf_get(host, 'ssh_key', '')

                workers.append({
                    "name": host.replace(":", "_"),
                    "host": test.conf_get(host, "host", host),
                    "password": test.conf_get(host, 'password', ''),
                    "username": test.conf_get(host, 'username', ''),
                    "key_filename": key_filename,
                    "channel_timeout": self.channel_timeout})

        self._workers = []
        [self._workers.append(SSHDistributor(**w)) for w in workers]
        self._worker_results = {}
        trace(str(self))

        # setup monitoring
        monitor_hosts = []                  # list of (host, port, descr)
        if not options.is_distributed:
            hosts = test.conf_get('monitor', 'hosts', '', quiet=True).split()
            for host in sorted(hosts):
                name = host
                host = test.conf_get(host, 'host', host.strip())
                monitor_hosts.append((name, host,
                                      test.conf_getInt(name, 'port'),
                                      test.conf_get(name, 'description', '')))
        self.monitor_hosts = monitor_hosts
        # keep the test to use the result logger for monitoring
        # and call setUp/tearDown Cycle
        self.test = test

        # start the feedback receiver
        if LIVE_FEEDBACK and options.feedback:
            trace("* Starting the Feedback Publisher\n")
            self.feedback = FeedbackPublisher(
                endpoint=options.feedback_endpoint or DEFAULT_ENDPOINT,
                pubsub_endpoint=options.feedback_pubsub_endpoint or
                DEFAULT_PUBSUB,
                handler=_print_rt)
            self.feedback.start()
        else:
            self.feedback = None

    def __repr__(self):
        """Display distributed bench information."""
        text = []
        text.append('=' * 72)
        text.append('Benching %s.%s' % (self.class_name,
                                        self.method_name))
        text.append('=' * 72)
        text.append(self.test_description)
        text.append('-' * 72 + '\n')
        text.append("Configuration")
        text.append("=============\n")
        text.append("* Current time: %s" % datetime.now().isoformat())
        text.append("* Configuration file: %s" % self.config_path)
        text.append("* Distributed output: %s" % self.distribution_output)
        size = os.path.getsize(self.tarred_tests)
        text.append("* Tarred tests: %0.2fMB" % (float(size) / 10.0 ** 6))
        text.append("* Server: %s" % self.test_url)
        text.append("* Cycles: %s" % self.cycles)
        text.append("* Cycle duration: %ss" % self.duration)
        text.append("* Sleeptime between request: from %ss to %ss" % (
            self.sleep_time_min, self.sleep_time_max))
        text.append("* Sleeptime between test case: %ss" % self.sleep_time)
        text.append("* Startup delay between thread: %ss" %
                    self.startup_delay)
        text.append("* Channel timeout: %s%s" % (
            self.channel_timeout, "s" if self.channel_timeout else ""))
        text.append("* Workers :%s\n\n" % ",".join(
                    w.name for w in self._workers))
        return '\n'.join(text)

    def prepare_workers(self, allow_errors=False):
        """
        Initialize the sandboxes in each worker node to prepare for a
        bench run. The additional parameter `allow_errors` will essentially
        make the distinction between ignoring unresponsive/inappropriate
        nodes - or raising an error and failing the entire bench.
        """
        # right, lets figure out if funkload can be setup on each host

        def local_prep_worker(worker):

            remote_res_dir = os.path.join(self.remote_res_dir, worker.name)
            virtual_env = os.path.join(
                remote_res_dir, self.tarred_testsdir)

            if worker.isdir(virtual_env):
                worker.execute("rm -rf %s" % virtual_env)

            worker.execute("mkdir -p %s" % virtual_env)
            worker.put(
                get_virtualenv_script(),
                os.path.join(remote_res_dir, "virtualenv.py"))

            trace(".")
            worker.execute(
                "%s virtualenv.py %s" % (
                    self.python_bin, os.path.join(remote_res_dir, self.tarred_testsdir)),
                cwdir=remote_res_dir)

            tarball = os.path.split(self.tarred_tests)[1]
            remote_tarball = os.path.join(remote_res_dir, tarball)

            # setup funkload
            cmd = "./bin/easy_install setuptools ez_setup {funkload}".format(
                funkload=self.funkload_location)

            if self.distributed_packages:
                cmd += " %s" % self.distributed_packages

            worker.execute(cmd, cwdir=virtual_env)

            # unpackage tests.
            worker.put(
                self.tarred_tests, os.path.join(remote_res_dir, tarball))
            worker.execute(
                "tar -xvf %s" % tarball,
                cwdir=remote_res_dir)
            worker.execute("rm %s" % remote_tarball)

            # workaround for https://github.com/pypa/virtualenv/issues/330
            worker.execute("rm lib64", cwdir=virtual_env)
            worker.execute("ln -s lib lib64", cwdir=virtual_env)

        threads = []
        trace("* Preparing sandboxes for %d workers." % len(self._workers))
        for worker in list(self._workers):
            if not worker.connected:
                if allow_errors:
                    trace("%s is not connected, removing from pool.\n" %
                          worker.name)
                    self._workers.remove(worker)
                    continue
                else:
                    raise RuntimeError(
                        "%s is not contactable with error %s" % (
                            worker.name, worker.error))

            # Verify that the Python binary is available
            which_python = "test -x `which %s 2>&1 > /dev/null` && echo true" \
                % (self.python_bin)
            out, err = worker.execute(which_python)

            if out.strip() == "true":
                threads.append(threading.Thread(
                    target=local_prep_worker,
                    args=(worker,)))
            elif allow_errors:
                trace("Cannot find Python binary at path `%s` on %s, " +
                      "removing from pool" % (self.python_bin, worker.name))
                self._workers.remove(worker)
            else:
                raise RuntimeError("%s is not contactable with error %s" % (
                    worker.name, worker.error))

        [k.start() for k in threads]
        [k.join() for k in threads]
        trace("\n")
        if not self._workers:
            raise RuntimeError("no workers available for distribution")

    def abort(self):
        for worker in self._workers:
            worker.die()

    def run(self):
        """
        """
        threads = []
        trace("* Starting %d workers" % len(self._workers))

        self.startMonitors()
        for worker in self._workers:
            remote_res_dir = os.path.join(self.remote_res_dir, worker.name)
            venv = os.path.join(remote_res_dir, self.tarred_testsdir)
            obj = worker.threaded_execute(
                'bin/fl-run-bench ' + ' '.join(self.cmd_args),
                cwdir=venv)
            trace(".")
            threads.append(obj)

        trace("\n")

        while True:
            if all([not thread.is_alive() for thread in threads]):
                # we're done
                break
            time.sleep(5.)

        trace("\n")

        for thread, worker in zip(threads, self._workers):
            self._worker_results[worker] = thread.output.read()
            trace("* [%s] returned\n" % worker.name)
            err_string = thread.err.read()
            if err_string:
                trace("\n".join("  [%s]: %s" % (worker.name, k) for k
                                in err_string.split("\n") if k.strip()))
            trace("\n")

        self.stopMonitors()
        self.correlate_statistics()

    def final_collect(self):
        expr = re.compile("Log\s+xml:\s+(.*?)\n")
        for worker, results in self._worker_results.items():
            res = expr.findall(results)
            if res:
                remote_file = res[0]
                filename = os.path.split(remote_file)[1]
                local_file = os.path.join(
                    self.distribution_output, "%s-%s" % (
                        worker.name, filename))
                if os.access(local_file, os.F_OK):
                    os.rename(local_file, local_file + '.bak-' +
                              str(int(time.time())))
                worker.get(remote_file, local_file)
                trace("* Received bench log from [%s] into %s\n" % (
                    worker.name, local_file))

    def startMonitors(self):
        """Start monitoring on hosts list."""
        if not self.monitor_hosts:
            return
        monitor_hosts = []
        monitor_key = "%s:0:0" % self.method_name
        for (name, host, port, desc) in self.monitor_hosts:
            trace("* Start monitoring %s: ..." % name)
            server = ServerProxy("http://%s:%s" % (host, port))
            try:
                server.startRecord(monitor_key)
            except SocketError:
                trace(' failed, server is down.\n')
            else:
                trace(' done.\n')
                monitor_hosts.append((name, host, port, desc))
        self.monitor_hosts = monitor_hosts

    def stopMonitors(self):
        """Stop monitoring and save xml result."""
        if not self.monitor_hosts:
            return
        monitor_key = "%s:0:0" % self.method_name
        successful_results = []
        for (name, host, port, desc) in self.monitor_hosts:
            trace('* Stop monitoring %s: ' % host)
            server = ServerProxy("http://%s:%s" % (host, port))
            try:
                server.stopRecord(monitor_key)
                successful_results.append(server.getXmlResult(monitor_key))
            except SocketError:
                trace(' failed, server is down.\n')
            else:
                trace(' done.\n')

        self.write_statistics(successful_results)
        if self.feedback is not None:
            self.feedback.close()

    def write_statistics(self, successful_results):
        """ Write the distributed stats to a file in the output dir """
        path = os.path.join(self.distribution_output, "stats.xml")
        if os.access(path, os.F_OK):
            os.rename(path, path + '.bak-' + str(int(time.time())))
        config = {'id': self.test_id,
                  'description': self.test_description,
                  'class_title': self.class_title,
                  'class_description': self.class_description,
                  'module': self.module_name,
                  'class': self.class_name,
                  'method': self.method_name,
                  'cycles': self.cycles,
                  'duration': self.duration,
                  'sleep_time': self.sleep_time,
                  'startup_delay': self.startup_delay,
                  'sleep_time_min': self.sleep_time_min,
                  'sleep_time_max': self.sleep_time_max,
                  'cycle_time': self.cycle_time,
                  'configuration_file': self.config_path,
                  'server_url': self.test_url,
                  'log_xml': self.result_path,
                  'python_version': platform.python_version()}

        for (name, host, port, desc) in self.monitor_hosts:
            config[name] = desc

        with open(path, "w+") as fd:
            fd.write('<funkload version="{version}" time="{time}">\n'.format(
                     version=get_version(), time=time.time()))
            for key, value in config.items():
                # Write out the config values
                fd.write('<config key="{key}" value="{value}"/>\n'.format(
                         key=key, value=value))
            for xml in successful_results:
                fd.write(xml)
                fd.write("\n")

            fd.write("</funkload>\n")

    def _calculate_time_skew(self, results, stats):
        if not results or not stats:
            return 1

        def min_time(vals):
            keyfunc = lambda elem: float(elem.attrib['time'])
            return keyfunc(min(vals, key=keyfunc))

        results_min = min_time(results)
        monitor_min = min_time(stats)

        return results_min / monitor_min

    def _calculate_results_ranges(self, results):
        seen = []
        times = {}
        for element in results:
            cycle = int(element.attrib['cycle'])
            if cycle not in seen:
                seen.append(cycle)

                cvus = int(element.attrib['cvus'])
                start_time = float(element.attrib['time'])
                times[start_time] = (cycle, cvus)

        return times

    def correlate_statistics(self):
        result_path = None
        if not self.monitor_hosts:
            return
        for worker, results in self._worker_results.items():
            files = glob("%s/%s-*.xml" % (self.distribution_output,
                                          worker.name))
            if files:
                result_path = files[0]
                break

        if not result_path:
            trace("* No output files found; unable to correlate stats.\n")
            return

        # Calculate the ratio between results and monitoring
        results_tree = ElementTree(file=result_path)
        stats_path = os.path.join(self.distribution_output, "stats.xml")
        stats_tree = ElementTree(file=stats_path)

        results = results_tree.findall("testResult")
        stats = stats_tree.findall("monitor")
        ratio = self._calculate_time_skew(results, stats)

        # Now that we have the ratio, we can calculate the sessions!
        times = self._calculate_results_ranges(results)
        times_desc = sorted(times.keys(), reverse=True)

        # Now, parse the stats tree and update values
        def find_range(start_time):
            for time_ in times_desc:
                if start_time > time_:
                    return times[time_]
            else:
                return times[time_]

        for stat in stats:
            adj_time = float(stat.attrib['time']) * ratio
            cycle, cvus = find_range(adj_time)
            key, cycle_, cvus_ = stat.attrib['key'].partition(':')
            stat.attrib['key'] = "%s:%d:%d" % (key, cycle, cvus)

        stats_tree.write(stats_path)

########NEW FILE########
__FILENAME__ = FunkLoadDocTest
# (C) Copyright 2006 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad doc test

$Id$
"""
import os
from tempfile import gettempdir
from FunkLoadTestCase import FunkLoadTestCase
import PatchWebunit

class FunkLoadDocTest(FunkLoadTestCase):
    """Class to use in doctest.

    >>> from FunkLoadDocTest import FunkLoadDocTest
    >>> fl = FunkLoadDocTest()
    >>> ret = fl.get('http://localhost')
    >>> ret.code
    200
    >>> 'HTML' in ret.body
    True

    """
    def __init__(self, debug=False, debug_level=1):
        """Initialise the test case."""
        class Dummy:
            pass
        option = Dummy()
        option.ftest_sleep_time_max = .001
        option.ftest_sleep_time_min = .001
        if debug:
            option.ftest_log_to = 'console file'
            if debug_level:
                option.debug_level = debug_level
        else:
            option.ftest_log_to = 'file'
        tmp_path = gettempdir()
        option.ftest_log_path = os.path.join(tmp_path, 'fl-doc-test.log')
        option.ftest_result_path = os.path.join(tmp_path, 'fl-doc-test.xml')
        FunkLoadTestCase.__init__(self, 'runTest', option)

    def runTest(self):
        """FL doctest"""
        return


def _test():
    import doctest, FunkLoadDocTest
    return doctest.testmod(FunkLoadDocTest)

if __name__ == "__main__":
    _test()


########NEW FILE########
__FILENAME__ = FunkLoadHTTPServer
#!/usr/bin/python
# (C) Copyright 2010 Nuxeo SAS <http://nuxeo.com>
# Author: Goutham Bhat
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

"""Debug HTTPServer module for Funkload."""

import BaseHTTPServer
import threading
import urlparse
from utils import trace

class FunkLoadHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handles HTTP requests from client in debug bench mode.

    These are the requests currently supported:
    /cvu?inc=<INTEGER> :: Increments number of CVU by given value.
    /cvu?dec=<INTEGER> :: Decrements number of CVU by given value.
    """
    benchrunner = None
    def do_GET(self):
        benchrunner = FunkLoadHTTPRequestHandler.benchrunner

        parsed_url = urlparse.urlparse(self.path)
        if parsed_url.path == '/cvu':
            query_args = parsed_url.query.split('&')
            if len(query_args) > 0:
                query_parts = query_args[0].split('=')
                if len(query_parts) == 2:
                    message = 'Number of threads changed from %d to %d.'
                    old_num_threads = benchrunner.getNumberOfThreads()
                    if query_parts[0] == 'inc':
                        benchrunner.addThreads(int(query_parts[1]))
                    elif query_parts[0] == 'dec':
                        benchrunner.removeThreads(int(query_parts[1]))
                    new_num_threads = benchrunner.getNumberOfThreads()
                    self.respond('CVU changed from %d to %d.' %
                                 (old_num_threads, new_num_threads))
        elif parsed_url.path == '/getcvu':
            self.respond('CVU = %d' % benchrunner.getNumberOfThreads())

    def respond(self, message):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(message)

class FunkLoadHTTPServer(threading.Thread):
    """Starts a HTTP server in a separate thread."""

    def __init__(self, benchrunner, port):
        threading.Thread.__init__(self)
        self.benchrunner = benchrunner
        self.port = port
        FunkLoadHTTPRequestHandler.benchrunner = benchrunner

    def run(self):
        port = 8000
        if self.port:
            port = int(self.port)
        server_address = ('', port)
        trace("Starting debug HTTP server at port %d\n" % port)

        httpd = BaseHTTPServer.HTTPServer(server_address, FunkLoadHTTPRequestHandler)
        httpd.serve_forever()

########NEW FILE########
__FILENAME__ = FunkLoadTestCase
# (C) Copyright 2005-2011 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors: Tom Lazar
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad test case using Richard Jones' webunit.

$Id: FunkLoadTestCase.py 24757 2005-08-31 12:22:19Z bdelbosc $
"""
import os
import sys
import time
import string
import re
import logging
import gzip
import threading
from StringIO import StringIO
from warnings import warn
from socket import error as SocketError
from types import DictType, ListType, TupleType
from datetime import datetime
import unittest
import traceback
from random import random
from urllib import urlencode
from tempfile import mkdtemp
from xml.sax.saxutils import quoteattr
from urlparse import urljoin
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

from webunit.webunittest import WebTestCase, HTTPError

import PatchWebunit
from utils import get_default_logger, mmn_is_bench, mmn_decode, Data
from utils import recording, thread_sleep, is_html, get_version, trace
from xmlrpclib import ServerProxy

_marker = []

# ------------------------------------------------------------
# Classes
#
class ConfSectionFinder(object):
    '''Convenience class.  Lets us access conf sections and attrs by
    doing MyTestCase().conf.sectionName.attrName
    '''
    allowedChars = string.ascii_letters + string.digits + '_'
    def __init__(self, testcase):
        self.testcase = testcase
        self.quiet = False

    def __getattr__(self, section):
        class ConfKeyFinder(object):
            def __getattr__(sself, attr):
                assert sself.validInput(section, attr), \
                       'To use the convenient .section.attr access to your'\
                       ' config variables, they can not contain any special'\
                       ' characters (alphanumeric and _ only)'
                return self.testcase.conf_get(section, attr, quiet=self.quiet)
            def validInput(sself, section, attr):
                return set(section+attr).issubset(self.allowedChars)
        return ConfKeyFinder()

class FunkLoadTestCase(unittest.TestCase):
    """Unit test with browser and configuration capabilties."""
    # ------------------------------------------------------------
    # Initialisation
    #
    def __init__(self, methodName='runTest', options=None):
        """Initialise the test case.

        Note that methodName is encoded in bench mode to provide additional
        information like thread_id, concurrent virtual users..."""
        if mmn_is_bench(methodName):
            self.in_bench_mode = True
        else:
            self.in_bench_mode = False
        self.test_name, self.cycle, self.cvus, self.thread_id = mmn_decode(
            methodName)
        self.meta_method_name = methodName
        self.suite_name = self.__class__.__name__
        unittest.TestCase.__init__(self, methodName=self.test_name)
        self._response = None
        self._options = options
        self.debug_level = getattr(options, 'debug_level', 0)
        self._funkload_init()
        self._dump_dir = getattr(options, 'dump_dir', None)
        self._dumping =  self._dump_dir and True or False
        self._viewing = getattr(options, 'firefox_view', False)
        self._accept_invalid_links = getattr(options, 'accept_invalid_links',
                                             False)
        self._bench_label = getattr(options, 'label', None)
        self._stop_on_fail = getattr(options, 'stop_on_fail', False)
        self._pause = getattr(options, 'pause', False)
        self._keyfile_path = None
        self._certfile_path = None
        self._accept_gzip = False
        if self._viewing and not self._dumping:
            # viewing requires dumping contents
            self._dumping = True
            self._dump_dir = mkdtemp('_funkload')
        self._loop_mode = getattr(options, 'loop_steps', False)
        if self._loop_mode:
            if ':' in options.loop_steps:
                steps = options.loop_steps.split(':')
                self._loop_steps = range(int(steps[0]), int(steps[1]))
            else:
                self._loop_steps = [int(options.loop_steps)]
            self._loop_number = options.loop_number
            self._loop_recording = False
            self._loop_records = []
        if sys.version_info >= (2, 5):
            self.__exc_info = sys.exc_info


    def _funkload_init(self):
        """Initialize a funkload test case using a configuration file."""
        # look into configuration file
        config_path = getattr(self._options, 'config', None)
        if not config_path:
          config_directory = os.getenv('FL_CONF_PATH', '.')
          config_path = os.path.join(config_directory,
                                     self.__class__.__name__ + '.conf')
        config_path = os.path.abspath(os.path.expanduser(config_path))
        if not os.path.exists(config_path):
            config_path = "Missing: "+ config_path
        config = ConfigParser()
        config.read(config_path)
        self._config = config
        self._config_path = config_path
        self.conf = ConfSectionFinder(self)
        self.default_user_agent = self.conf_get('main', 'user_agent',
                                                'FunkLoad/%s' % get_version(),
                                                quiet=True)
        if self.in_bench_mode:
            section = 'bench'
        else:
            section = 'ftest'
        self.setOkCodes( self.conf_getList(section, 'ok_codes',
                                           [200, 301, 302, 303, 307],
                                           quiet=True) )
        self.sleep_time_min = self.conf_getFloat(section, 'sleep_time_min', 0)
        self.sleep_time_max = self.conf_getFloat(section, 'sleep_time_max', 0)
        self._simple_fetch = self.conf_getInt(section, 'simple_fetch', 0, 
                                              quiet=True)
        self.log_to = self.conf_get(section, 'log_to', 'console file')
        self.log_path = self.conf_get(section, 'log_path', 'funkload.log')
        self.result_path = os.path.abspath(
            self.conf_get(section, 'result_path', 'funkload.xml'))

        # init loggers
        if self.in_bench_mode:
            level = logging.INFO
        else:
            level = logging.DEBUG
        self.logger = get_default_logger(self.log_to, self.log_path,
                                         level=level)
        self.logger_result = get_default_logger(log_to="xml",
                                                log_path=self.result_path,
                                                name="FunkLoadResult")
        #self.logd('_funkload_init config [%s], log_to [%s],'
        #          ' log_path [%s], result [%s].' % (
        #    self._config_path, self.log_to, self.log_path, self.result_path))

        # init webunit browser (passing a fake methodName)
        self._browser = WebTestCase(methodName='log')
        self.clearContext()

        #self.logd('# FunkLoadTestCase._funkload_init done')
    
    
    def setOkCodes(self, ok_codes):
        """Set ok codes."""
        self.ok_codes = map(int, ok_codes)
    
    
    def clearContext(self):
        """Reset the testcase."""
        self._browser.clearContext()
        self._browser.css = {}
        self._browser.history = []
        self._browser.extra_headers = []
        if self.debug_level >= 3:
            self._browser.debug_headers = True
        else:
            self._browser.debug_headers = False
        self.step_success = True
        self.test_status = 'Successful'
        self.steps = 0
        self.page_responses = 0
        self.total_responses = 0
        self.total_time = 0.0
        self.total_pages = self.total_images = 0
        self.total_links = self.total_redirects = 0
        self.total_xmlrpc = 0
        self.clearBasicAuth()
        self.clearHeaders()
        self.clearKeyAndCertificateFile()
        self.setUserAgent(self.default_user_agent)

        self.logdd('FunkLoadTestCase.clearContext done')



    #------------------------------------------------------------
    # browser simulation
    #
    def _connect(self, url, params, ok_codes, rtype, description, redirect=False, consumer=None):
        """Handle fetching, logging, errors and history."""
        if params is None and rtype in ('post','put'):
            # enable empty put/post
            params = []
        t_start = time.time()
        try:
            response = self._browser.fetch(url, params, ok_codes=ok_codes,
                                           key_file=self._keyfile_path,
                                           cert_file=self._certfile_path, method=rtype, consumer=consumer)
        except:
            etype, value, tback = sys.exc_info()
            t_stop = time.time()
            t_delta = t_stop - t_start
            self.total_time += t_delta
            self.step_success = False
            self.test_status = 'Failure'
            self.logd(' Failed in %.3fs' % t_delta)
            if etype is HTTPError:
                self._log_response(value.response, rtype, description,
                                   t_start, t_stop, log_body=True)
                if self._dumping:
                    self._dump_content(value.response, description)
                raise self.failureException, str(value.response)
            else:
                self._log_response_error(url, rtype, description, t_start,
                                         t_stop)
                if etype is SocketError:
                    raise SocketError("Can't load %s." % url)
                raise
        t_stop = time.time()
        # Log response
        t_delta = t_stop - t_start
        self.total_time += t_delta
        if redirect:
            self.total_redirects += 1
        elif rtype != 'link':
            self.total_pages += 1
        else:
            self.total_links += 1

        if rtype in ('put', 'post', 'get', 'delete'):
            # this is a valid referer for the next request
            self.setHeader('Referer', url)
        self._browser.history.append((rtype, url))
        self.logd(' Done in %.3fs' % t_delta)
        if self._accept_gzip:
            if response.headers is not None and response.headers.get('Content-Encoding') == 'gzip':
                buf = StringIO(response.body)
                response.body = gzip.GzipFile(fileobj=buf).read()
        self._log_response(response, rtype, description, t_start, t_stop)
        if self._dumping:
            self._dump_content(response, description)
        return response

    def _browse(self, url_in, params_in=None,
                description=None, ok_codes=None,
                method='post',
                follow_redirect=True, load_auto_links=True,
                sleep=True):
        """Simulate a browser handle redirects, load/cache css and images."""
        self._response = None
        # Loop mode
        if self._loop_mode:
            if self.steps == self._loop_steps[0]:
                self._loop_recording = True
                self.logi('Loop mode start recording')
            if self._loop_recording:
                self._loop_records.append((url_in, params_in, description,
                                           ok_codes, method, follow_redirect,
                                           load_auto_links, False))
        # ok codes
        if ok_codes is None:
            ok_codes = self.ok_codes
        if type(params_in) is DictType:
            params_in = params_in.items()
        params = []
        if params_in:
            if isinstance(params_in, Data):
                params = params_in
            else:
                for key, value in params_in:
                    if type(value) is DictType:
                        for val, selected in value.items():
                            if selected:
                                params.append((key, val))
                    elif type(value) in (ListType, TupleType):
                        for val in value:
                            params.append((key, val))
                    else:
                        params.append((key, value))

        if method == 'get' and params:
            url = url_in + '?' + urlencode(params)
        else:
            url = url_in
        if method == 'get':
            params = None

        if method == 'get':
            if not self.in_bench_mode:
                self.logd('GET: %s\n\tPage %i: %s ...' % (url, self.steps,
                                                          description or ''))
        else:
            url = url_in
            if not self.in_bench_mode:
                self.logd('%s: %s %s\n\tPage %i: %s ...' % (
                        method.upper(), url, str(params),
                        self.steps, description or ''))
            # Fetching
        response = self._connect(url, params, ok_codes, method, description)

        # Check redirection
        if follow_redirect and response.code in (301, 302, 303, 307):
            max_redirect_count = 10
            thread_sleep()              # give a chance to other threads
            while response.code in (301, 302, 303, 307) and max_redirect_count:
                # Figure the location - which may be relative
                newurl = response.headers['Location']
                url = urljoin(url_in, newurl)
                # Save the current url as the base for future redirects
                url_in = url
                self.logd(' Load redirect link: %s' % url)
                # Use the appropriate method for redirection
                if response.code in (302, 303):
                    method = 'get'
                if response.code == 303:
                    # 303 is HTTP/1.1, make sure the connection 
                    # is not in keep alive mode
                    self.setHeader('Connection', 'close')
                response = self._connect(url, None, ok_codes, rtype=method,
                                         description=None, redirect=True)
                max_redirect_count -= 1
            if not max_redirect_count:
                self.logd(' WARNING Too many redirects give up.')

        # Load auto links (css and images)
        response.is_html = is_html(response.body)
        if load_auto_links and response.is_html and not self._simple_fetch:
            self.logd(' Load css and images...')
            page = response.body
            t_start = time.time()
            c_start = self.total_time
            try:
                # pageImages is patched to call _log_response on all links
                self._browser.pageImages(url, page, self)
            except HTTPError, error:
                if self._accept_invalid_links:
                    if not self.in_bench_mode:
                        self.logd('  ' + str(error))
                else:
                    t_stop = time.time()
                    t_delta = t_stop - t_start
                    self.step_success = False
                    self.test_status = 'Failure'
                    self.logd('  Failed in ~ %.2fs' % t_delta)
                    # XXX The duration logged for this response is wrong
                    self._log_response(error.response, 'link', None,
                                       t_start, t_stop, log_body=True)
                    raise self.failureException, str(error)
            c_stop = self.total_time
            self.logd('  Done in %.3fs' % (c_stop - c_start))
        if sleep:
            self.sleep()
        self._response = response

        # Loop mode
        if self._loop_mode and self.steps == self._loop_steps[-1]:
            self._loop_recording = False
            self.logi('Loop mode end recording.')
            t_start = self.total_time
            count = 0
            for i in range(self._loop_number):
                self.logi('Loop mode replay %i' % i)
                for record in self._loop_records:
                    count += 1
                    self.steps += 1
                    self._browse(*record)
            t_delta = self.total_time - t_start
            text = ('End of loop: %d pages rendered in %.3fs, '
                    'avg of %.3fs per page, '
                    '%.3f SPPS without concurrency.' % (count, t_delta,
                                                        t_delta / count,
                                                        count/t_delta))
            self.logi(text)
            trace(text + '\n')

        return response

    def post(self, url, params=None, description=None, ok_codes=None,
             load_auto_links=True):
        """Make an HTTP POST request to the specified url with params.

        Returns a webunit.webunittest.HTTPResponse object.
        """
        self.steps += 1
        self.page_responses = 0
        response = self._browse(url, params, description, ok_codes,
                                method="post", load_auto_links=load_auto_links)
        return response

    def get(self, url, params=None, description=None, ok_codes=None,
            load_auto_links=True):
        """Make an HTTP GET request to the specified url with params.

        Returns a webunit.webunittest.HTTPResponse object.
        """
        self.steps += 1
        self.page_responses = 0
        response = self._browse(url, params, description, ok_codes,
                                method="get", load_auto_links=load_auto_links)
        return response

    def method(self, method, url, params=None, description=None,
               ok_codes=None, load_auto_links=True):
        """Generic HTTP request method.
        Can be used to make MOVE, MKCOL, etc method name HTTP requests.

        Returns a webunit.webunittest.HTTPResponse object.
        """
        self.steps += 1
        self.page_responses = 0
        response = self._browse(url, params, description, ok_codes,
                                method=method, load_auto_links=load_auto_links)
        return response

    def put(self, url, params=None, description=None, ok_codes=None,
            load_auto_links=True):
        """Make an HTTP PUT request to the specified url with params."""
        return self.method('put', url, params, description, ok_codes,
                load_auto_links=load_auto_links)

    def delete(self, url, description=None, ok_codes=None):
        """Make an HTTP DELETE request to the specified url."""
        return self.method('delete', url, None, description, ok_codes)

    def head(self, url, description=None, ok_codes=None):
        """Make an HTTP HEAD request to the specified url with params."""
        return self.method('head', url, None, description, ok_codes)

    def options(self, url, description=None, ok_codes=None):
        """Make an HTTP OPTIONS request to the specified url."""
        return self.method('options', url, None, description, ok_codes)

    def propfind(self, url, params=None, depth=None, description=None,
                 ok_codes=None):
        """Make a DAV PROPFIND request to the specified url with params."""
        if ok_codes is None:
            codes = [207, ]
        else:
            codes = ok_codes
        if depth is not None:
            self.setHeader('depth', str(depth))
        ret = self.method('PROPFIND', url, params=params,
                          description=description, ok_codes=codes)
        if depth is not None:
            self.delHeader('depth')
        return ret

    def exists(self, url, params=None, description="Checking existence"):
        """Try a GET on URL return True if the page exists or False."""
        resp = self.get(url, params, description=description,
                        ok_codes=[200, 301, 302, 303, 307, 404, 503], load_auto_links=False)
        if resp.code not in [200, 301, 302, 303, 307]:
            self.logd('Page %s not found.' % url)
            return False
        return True

    def xmlrpc(self, url_in, method_name, params=None, description=None):
        """Call an xml rpc method_name on url with params."""
        self.steps += 1
        self.page_responses = 0
        self.logd('XMLRPC: %s::%s\n\tCall %i: %s ...' % (url_in, method_name,
                                                         self.steps,
                                                         description or ''))
        response = None
        t_start = time.time()
        if self._authinfo is not None:
            url = url_in.replace('//', '//'+self._authinfo)
        else:
            url = url_in
        try:
            server = ServerProxy(url)
            method = getattr(server, method_name)
            if params is not None:
                response = method(*params)
            else:
                response = method()
        except:
            etype, value, tback = sys.exc_info()
            t_stop = time.time()
            t_delta = t_stop - t_start
            self.total_time += t_delta
            self.step_success = False
            self.test_status = 'Error'
            self.logd(' Failed in %.3fs' % t_delta)
            self._log_xmlrpc_response(url_in, method_name, description,
                                      response, t_start, t_stop, -1)
            if etype is SocketError:
                raise SocketError("Can't access %s." % url)
            raise
        t_stop = time.time()
        t_delta = t_stop - t_start
        self.total_time += t_delta
        self.total_xmlrpc += 1
        self.logd(' Done in %.3fs' % t_delta)
        self._log_xmlrpc_response(url_in, method_name, description, response,
                                  t_start, t_stop, 200)
        self.sleep()
        return response

    def xmlrpc_call(self, url_in, method_name, params=None, description=None):
        """BBB of xmlrpc, this method will be removed for 1.6.0."""
        warn('Since 1.4.0 the method "xmlrpc_call" is renamed into "xmlrpc".',
             DeprecationWarning, stacklevel=2)
        return self.xmlrpc(url_in, method_name, params, description)

    def waitUntilAvailable(self, url, time_out=20, sleep_time=2):
        """Wait until url is available.

        Try a get on url every sleep_time until server is reached or
        time is out."""
        time_start = time.time()
        while(True):
            try:
                self._browser.fetch(url, None,
                                    ok_codes=[200, 301, 302, 303, 307],
                                    key_file=self._keyfile_path,
                                    cert_file=self._certfile_path, method="get")
            except SocketError:
                if time.time() - time_start > time_out:
                    self.fail('Time out service %s not available after %ss' %
                              (url, time_out))
            else:
                return
            time.sleep(sleep_time)

    def comet(self, url, consumer, description=None):
        """Initiate a comet request and process the input in a separate thread.
        This call is async and return a thread object.

        The consumer method takes as parameter an input string, it can
        close the comet connection by returning 0."""
        self.steps += 1
        self.page_responses = 0
        thread = threading.Thread(target=self._cometFetcher, args=(url, consumer, description))
        thread.start()
        return thread

    def _cometFetcher(self, url, consumer, description):
        self._connect(url, None, self.ok_codes, 'GET', description, consumer=consumer)

    def setBasicAuth(self, login, password):
        """Set HTTP basic authentication for the following requests."""
        self._browser.setBasicAuth(login, password)
        self._authinfo = '%s:%s@' % (login, password)

    def clearBasicAuth(self):
        """Remove basic authentication."""
        self._browser.clearBasicAuth()
        self._authinfo = None

    def addHeader(self, key, value):
        """Add an http header."""
        self._browser.extra_headers.append((key, value))

    def setHeader(self, key, value):
        """Add or override an http header.

        If value is None, the key is removed."""
        headers = self._browser.extra_headers
        for i, (k, v) in enumerate(headers):
            if k == key:
                if value is not None:
                    headers[i] = (key, value)
                else:
                    del headers[i]
                break
        else:
            if value is not None:
                headers.append((key, value))
        if key.lower() == 'accept-encoding':
            if value and value.lower() == 'gzip':
                self._accept_gzip = True
            else:
                self._accept_gzip = False

    def delHeader(self, key):
        """Remove an http header key."""
        self.setHeader(key, None)

    def clearHeaders(self):
        """Remove all http headers set by addHeader or setUserAgent.

        Note that the Referer is also removed."""
        self._browser.extra_headers = []

    def debugHeaders(self, debug_headers=True):
        """Print request headers."""
        self._browser.debug_headers = debug_headers

    def setUserAgent(self, agent):
        """Set User-Agent http header for the next requests.

        If agent is None, the user agent header is removed."""
        self.setHeader('User-Agent', agent)

    def sleep(self):
        """Sleeps a random amount of time.

        Between the predefined sleep_time_min and sleep_time_max values.
        """
        if self._pause:
            raw_input("Press ENTER to continue ")
            return
        s_min = self.sleep_time_min
        s_max = self.sleep_time_max
        if s_max != s_min:
            s_val = s_min + abs(s_max - s_min) * random()
        else:
            s_val = s_min
        # we should always sleep something
        thread_sleep(s_val)

    def setKeyAndCertificateFile(self, keyfile_path, certfile_path):
        """Set the paths to a key file and a certificate file that will be
        used by a https (ssl/tls) connection when calling the post or get
        methods.

        keyfile_path : path to a PEM formatted file that contains your
        private key.
        certfile_path : path to a PEM formatted certificate chain file.
        """
        self._keyfile_path = keyfile_path
        self._certfile_path = certfile_path

    def clearKeyAndCertificateFile(self):
        """Clear any key file or certificate file paths set by calls to
        setKeyAndCertificateFile.
        """
        self._keyfile_path = None
        self._certfile_path = None

    #------------------------------------------------------------
    # Assertion helpers
    #
    def getLastUrl(self):
        """Return the last accessed url taking into account redirection."""
        response = self._response
        if response is not None:
            return response.url
        return ''

    def getBody(self):
        """Return the last response content."""
        response = self._response
        if response is not None:
            return response.body
        return ''

    def listHref(self, url_pattern=None, content_pattern=None):
        """Return a list of href anchor url present in the last html response.

        Filtering href with url pattern or link text pattern."""
        response = self._response
        ret = []
        if response is not None:
            a_links = response.getDOM().getByName('a')
            if a_links:
                for link in a_links:
                    try:
                        ret.append((link.getContentString(), link.href))
                    except AttributeError:
                        pass
            if url_pattern is not None:
                pat = re.compile(url_pattern)
                ret = [link for link in ret
                       if pat.search(link[1]) is not None]
            if content_pattern is not None:
                pat = re.compile(content_pattern)
                ret = [link for link in ret
                       if link[0] and (pat.search(link[0]) is not None)]
        return [link[1] for link in ret]

    def getLastBaseUrl(self):
        """Return the base href url."""
        response = self._response
        if response is not None:
            base = response.getDOM().getByName('base')
            if base:
                return base[0].href
        return ''

    #------------------------------------------------------------
    # configuration file utils
    #
    def conf_get(self, section, key, default=_marker, quiet=False):
        """Return an entry from the options or configuration file."""
        # check for a command line options
        opt_key = '%s_%s' % (section, key)
        opt_val = getattr(self._options, opt_key, None)
        if opt_val:
            #print('[%s] %s = %s from options.' % (section, key, opt_val))
            return opt_val
        # check for the configuration file if opt val is None
        # or nul
        try:
            val = self._config.get(section, key)
        except (NoSectionError, NoOptionError):
            if not quiet:
                self.logi('[%s] %s not found' % (section, key))
            if default is _marker:
                raise
            val = default
        #print('[%s] %s = %s from config.' % (section, key, val))
        return val

    def conf_getInt(self, section, key, default=_marker, quiet=False):
        """Return an integer from the configuration file."""
        return int(self.conf_get(section, key, default, quiet))

    def conf_getFloat(self, section, key, default=_marker, quiet=False):
        """Return a float from the configuration file."""
        return float(self.conf_get(section, key, default, quiet))

    def conf_getList(self, section, key, default=_marker, quiet=False,
                     separator=None):
        """Return a list from the configuration file."""
        value = self.conf_get(section, key, default, quiet)
        if value is default:
            return value
        if separator is None:
            separator = ':'
        if separator in value:
            return value.split(separator)
        return [value]

    #------------------------------------------------------------
    # Extend unittest.TestCase to provide bench cycle hook
    #
    def setUpCycle(self):
        """Called on bench mode before a cycle start."""
        pass

    def midCycle(self, cycle, cvus):
        """Called in the middle of a bench cycle."""
        pass

    def tearDownCycle(self):
        """Called after a cycle in bench mode."""
        pass

    #------------------------------------------------------------
    # Extend unittest.TestCase to provide bench setup/teardown hook
    #
    def setUpBench(self):
        """Called before the start of the bench."""
        pass

    def tearDownBench(self):
        """Called after a the bench."""
        pass

    #------------------------------------------------------------
    # logging
    #
    def logd(self, message):
        """Debug log."""
        self.logger.debug(self.meta_method_name +': ' +message)

    def logdd(self, message):
        """Verbose Debug log."""
        if self.debug_level >= 2:
            self.logger.debug(self.meta_method_name +': ' +message)

    def logi(self, message):
        """Info log."""
        if hasattr(self, 'logger'):
            self.logger.info(self.meta_method_name+': '+message)
        else:
            print self.meta_method_name+': '+message

    def _logr(self, message, force=False):
        """Log a result."""
        if force or not self.in_bench_mode or recording():
            self.logger_result.info(message)

    def _open_result_log(self, **kw):
        """Open the result log."""
        self._logr('<funkload version="%s" time="%s">' % (
                get_version(), datetime.now().isoformat()), force=True)
        self.addMetadata(ns=None, **kw)

    def addMetadata(self, ns="meta", **kw):
        """Add metadata info."""
        xml = []
        for key, value in kw.items():
            if ns is not None:
                xml.append('<config key="%s:%s" value=%s />' % (
                        ns, key, quoteattr(str(value))))
            else:
                xml.append('<config key="%s" value=%s />' % (
                        key, quoteattr(str(value))))
        self._logr('\n'.join(xml), force=True)

    def _close_result_log(self):
        """Close the result log."""
        self._logr('</funkload>', force=True)

    def _log_response_error(self, url, rtype, description, time_start,
                            time_stop):
        """Log a response that raise an unexpected exception."""
        self.total_responses += 1
        self.page_responses += 1
        info = {}
        info['cycle'] = self.cycle
        info['cvus'] = self.cvus
        info['thread_id'] = self.thread_id
        info['suite_name'] = self.suite_name
        info['test_name'] = self.test_name
        info['step'] = self.steps
        info['number'] = self.page_responses
        info['type'] = rtype
        info['url'] = quoteattr(url)
        info['code'] = -1
        info['description'] = description and quoteattr(description) or '""'
        info['time_start'] = time_start
        info['duration'] = time_stop - time_start
        info['result'] = 'Error'
        info['traceback'] = quoteattr(' '.join(
            traceback.format_exception(*sys.exc_info())))
        message = '''<response cycle="%(cycle).3i" cvus="%(cvus).3i" thread="%(thread_id).3i" suite="%(suite_name)s" name="%(test_name)s" step="%(step).3i" number="%(number).3i" type="%(type)s" result="%(result)s" url=%(url)s code="%(code)s" description=%(description)s time="%(time_start)s" duration="%(duration)s" traceback=%(traceback)s />''' % info
        self._logr(message)

    def _log_response(self, response, rtype, description, time_start,
                      time_stop, log_body=False):
        """Log a response."""
        self.total_responses += 1
        self.page_responses += 1
        info = {}
        info['cycle'] = self.cycle
        info['cvus'] = self.cvus
        info['thread_id'] = self.thread_id
        info['suite_name'] = self.suite_name
        info['test_name'] = self.test_name
        info['step'] = self.steps
        info['number'] = self.page_responses
        info['type'] = rtype
        info['url'] = quoteattr(response.url)
        info['code'] = response.code
        info['description'] = description and quoteattr(description) or '""'
        info['time_start'] = time_start
        info['duration'] = time_stop - time_start
        info['result'] = self.step_success and 'Successful' or 'Failure'
        response_start = '''<response cycle="%(cycle).3i" cvus="%(cvus).3i" thread="%(thread_id).3i" suite="%(suite_name)s" name="%(test_name)s" step="%(step).3i" number="%(number).3i" type="%(type)s" result="%(result)s" url=%(url)s code="%(code)s" description=%(description)s time="%(time_start)s" duration="%(duration)s"''' % info

        if not log_body:
            message = response_start + ' />'
        else:
            response_start = response_start + '>\n  <headers>'
            header_xml = []
            if response.headers is not None:
                for key, value in response.headers.items():
                    header_xml.append('    <header name="%s" value=%s />' % (
                            key, quoteattr(value)))
            headers = '\n'.join(header_xml) + '\n  </headers>'
            message = '\n'.join([
                response_start,
                headers,
                '  <body><![CDATA[\n%s\n]]>\n  </body>' % response.body,
                '</response>'])
        self._logr(message)

    def _log_xmlrpc_response(self, url, method, description, response,
                             time_start, time_stop, code):
        """Log a response."""
        self.total_responses += 1
        self.page_responses += 1
        info = {}
        info['cycle'] = self.cycle
        info['cvus'] = self.cvus
        info['thread_id'] = self.thread_id
        info['suite_name'] = self.suite_name
        info['test_name'] = self.test_name
        info['step'] = self.steps
        info['number'] = self.page_responses
        info['type'] = 'xmlrpc'
        info['url'] = quoteattr(url + '#' + method)
        info['code'] = code
        info['description'] = description and quoteattr(description) or '""'
        info['time_start'] = time_start
        info['duration'] = time_stop - time_start
        info['result'] = self.step_success and 'Successful' or 'Failure'
        message = '''<response cycle="%(cycle).3i" cvus="%(cvus).3i" thread="%(thread_id).3i" suite="%(suite_name)s" name="%(test_name)s" step="%(step).3i" number="%(number).3i" type="%(type)s" result="%(result)s" url=%(url)s code="%(code)s" description=%(description)s time="%(time_start)s" duration="%(duration)s" />"''' % info
        self._logr(message)

    def _log_result(self, time_start, time_stop):
        """Log the test result."""
        info = {}
        info['cycle'] = self.cycle
        info['cvus'] = self.cvus
        info['thread_id'] = self.thread_id
        info['suite_name'] = self.suite_name
        info['test_name'] = self.test_name
        info['steps'] = self.steps
        info['time_start'] = time_start
        info['duration'] = time_stop - time_start
        info['connection_duration'] = self.total_time
        info['requests'] = self.total_responses
        info['pages'] = self.total_pages
        info['xmlrpc'] = self.total_xmlrpc
        info['redirects'] = self.total_redirects
        info['images'] = self.total_images
        info['links'] = self.total_links
        info['result'] = self.test_status
        if self.test_status != 'Successful':
            info['traceback'] = 'traceback=' + quoteattr(' '.join(
                traceback.format_exception(*sys.exc_info()))) + ' '
        else:
            info['traceback'] = ''
        text = '''<testResult cycle="%(cycle).3i" cvus="%(cvus).3i" thread="%(thread_id).3i" suite="%(suite_name)s" name="%(test_name)s"  time="%(time_start)s" result="%(result)s" steps="%(steps)s" duration="%(duration)s" connection_duration="%(connection_duration)s" requests="%(requests)s" pages="%(pages)s" xmlrpc="%(xmlrpc)s" redirects="%(redirects)s" images="%(images)s" links="%(links)s" %(traceback)s/>''' % info
        self._logr(text)

    def _dump_content(self, response, description):
        """Dump the html content in a file.

        Use firefox to render the content if we are in rt viewing mode."""
        dump_dir = self._dump_dir
        if dump_dir is None:
            return
        if getattr(response, 'code', 301) in [301, 302, 303, 307]:
            return
        if not response.body:
            return
        if not os.access(dump_dir, os.W_OK):
            os.mkdir(dump_dir, 0775)
        content_type = response.headers.get('content-type')
        if content_type == 'text/xml':
            ext = '.xml'
        else:
            ext = os.path.splitext(response.url)[1]
            if not ext.startswith('.') or len(ext) > 4:
                ext = '.html'
        file_path = os.path.abspath(
            os.path.join(dump_dir, '%3.3i%s' % (self.steps, ext)))
        f = open(file_path, 'w')
        f.write(response.body)
        f.close()
        if self._viewing:
            cmd = 'firefox -remote  "openfile(file://%s#%s,new-tab)"' % (
                file_path, description)
            ret = os.system(cmd)
            if ret != 0 and not sys.platform.lower().startswith('win'):
                self.logi('Failed to remote control firefox: %s' % cmd)
                self._viewing = False

    #------------------------------------------------------------
    # Overriding unittest.TestCase
    #
    def __call__(self, result=None):
        """Run the test method.

        Override to log test result."""
        t_start = time.time()
        if result is None:
            result = self.defaultTestResult()
        result.startTest(self)
        if sys.version_info >= (2, 5):
            testMethod = getattr(self, self._testMethodName)
        else:
            testMethod = getattr(self, self._TestCase__testMethodName)
        try:
            ok = False
            try:
                if not self.in_bench_mode:
                    self.logd('Starting -----------------------------------\n\t%s'
                              % self.conf_get(self.meta_method_name, 'description', ''))
                self.setUp()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, self.__exc_info())
                self.test_status = 'Error'
                self._log_result(t_start, time.time())
                return
            try:
                testMethod()
                ok = True
            except self.failureException:
                result.addFailure(self, self.__exc_info())
                self.test_status = 'Failure'
            except KeyboardInterrupt:
                raise
            except:
                result.addFailure(self, self.__exc_info())
                self.test_status = 'Error'
            try:
                self.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                result.addFailure(self, self.__exc_info())
                self.test_status = 'Error'
                ok = False
            if ok:
                result.addSuccess(self)
        finally:
            self._log_result(t_start, time.time())
            if not ok and self._stop_on_fail:
                result.stop()
            result.stopTest(self)




# ------------------------------------------------------------
# testing
#
class DummyTestCase(FunkLoadTestCase):
    """Testing Funkload TestCase."""

    def test_apache(self):
        """Simple apache test."""
        self.logd('start apache test')
        for i in range(2):
            self.get('http://localhost/')
            self.logd('base_url: ' + self.getLastBaseUrl())
            self.logd('url: ' + self.getLastUrl())
            self.logd('hrefs: ' + str(self.listHref()))
        self.logd("Total connection time = %s" % self.total_time)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = Lipsum
# -*- coding: ISO-8859-15 -*-
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""A simple Lorem ipsum generator.

$Id: Lipsum.py 24649 2005-08-29 14:20:19Z bdelbosc $
"""
import random

# vacabulary simple ascii
V_ASCII = ('ad', 'aquam', 'albus', 'archaeos', 'arctos', 'argentatus',
           'arvensis', 'australis', 'biscort' 'borealis', 'brachy', 'bradus',
           'brevis', 'campus', 'cauda', 'caulos', 'cephalus', 'chilensis',
           'chloreus', 'cola', 'cristatus', 'cyanos', 'dactylus', 'deca',
           'dermis', 'delorum', 'di', 'diplo', 'dodeca', 'dolicho',
           'domesticus', 'dorsum', 'dulcis', 'echinus', 'ennea', 'erythro',
           'familiaris', 'flora', 'folius', 'fuscus', 'fulvus', 'gaster',
           'glycis', 'hexa', 'hortensis', 'it', 'indicus', 'lateralis',
           'leucus', 'lineatus', 'lipsem', 'lutea', 'maculatus', 'major',
           'maximus', 'melanus', 'minimus', 'minor', 'mono', 'montanus',
           'morphos', 'mauro', 'niger', 'nona', 'nothos', 'notos',
           'novaehollandiae', 'novaeseelandiae', 'noveboracensis', 'obscurus',
           'occidentalis', 'octa', 'oeos', 'officinalis', 'oleum',
           'orientalis', 'ortho', 'pachys', 'palustris', 'parvus', 'pedis',
           'pelagius', 'penta', 'petra', 'phyllo', 'phyton', 'platy',
           'pratensis', 'protos', 'pteron', 'punctatus', 'rhiza', 'rhytis',
           'rubra', 'rostra', 'rufus', 'sativus', 'saurus', 'sinensis',
           'stoma', 'striatus', 'silvestris', 'sit', 'so', 'tetra',
           'tinctorius', 'tomentosus', 'tres', 'tris', 'trich', 'thrix',
           'unus', 'variabilis', 'variegatus', 'ventrus', 'verrucosus', 'via',
           'viridis', 'vitis', 'volans', 'vulgaris', 'xanthos', 'zygos',
           )

# vocabulary with some diacritics
V_DIAC = ('acanth', 'acro', 'actino', 'adelphe', 'adéno', 'aéro', 'agogue',
          'agro', 'algie', 'allo', 'amphi', 'andro', 'anti', 'anthropo',
          'aqui', 'archéo', 'archie', 'auto', 'bio', 'calli', 'cephal',
          'chiro', 'chromo', 'chrono', 'dactyle', 'démo', 'eco', 'eudaimonia',
          'êthos', 'géo', 'glyphe', 'gone', 'gramme', 'graphe', 'hiéro',
          'homo', 'iatrie', 'lipi', 'lipo', 'logie', 'lyco', 'lyse', 'machie',
          'mélan', 'méta', 'naute', 'nèse', 'pedo', 'phil', 'phobie', 'podo',
          'polis', 'poly', 'rhino', 'xeno', 'zoo',
          )

# latin 9 vocabulary
V_8859_15 = ('jàcánth', 'zâcrö', 'bãctinõ', 'zädelphe', 'kådénô', 'zæró',
             'agòguê', 'algië', 'allð', 'amphi', 'añdro', 'añti', 'aqúi',
             'aùtø', 'biø', 'caßi', 'çephal', 'lýco', 'rÿtøñ', 'oþiß',
             'es', 'du', 'de', 'le', 'as', 'us', 'i', 'ave', 'ov ¼',
             'zur ½', 'ab ¾',
             )

# common char to build identifier
CHARS = "abcdefghjkmnopqrstuvwxyz123456789"

# separator
SEP = ',' * 10 + ';?!'

class Lipsum:
    """Kind of Lorem ipsum generator."""

    def __init__(self, vocab=V_ASCII,
                 chars=CHARS, sep=SEP):
        self.vocab = vocab
        self.chars = chars
        self.sep = sep

    def getWord(self):
        """Return a random word."""
        return random.choice(self.vocab)

    def getUniqWord(self, length_min=None, length_max=None):
        """Generate a kind of uniq identifier."""
        length_min = length_min or 5
        length_max = length_max or 9
        length = random.randrange(length_min, length_max)
        chars = self.chars
        return ''.join([random.choice(chars) for i in range(length)])

    def getSubject(self, length=5, prefix=None, uniq=False,
                   length_min=None, length_max=None):
        """Return a subject of length words."""
        subject = []
        if prefix:
            subject.append(prefix)
        if uniq:
            subject.append(self.getUniqWord())
        if length_min and length_max:
            length = random.randrange(length_min, length_max+1)
        for i in range(length):
            subject.append(self.getWord())
        return ' '.join(subject).capitalize()

    def getSentence(self):
        """Return a random sentence."""
        sep = self.sep
        length = random.randrange(5, 20)
        sentence = [self.getWord() for i in range(length)]
        for i in range(random.randrange(0, 3)):
            sentence.insert(random.randrange(length-4)+2, random.choice(sep))
        sentence = ' '.join(sentence).capitalize() + '.'
        sentence = sentence.replace(' ,', ',')
        sentence = sentence.replace(',,', ',')
        return sentence

    def getParagraph(self, length=4):
        """Return a paragraph."""
        return ' '.join([self.getSentence() for i in range(length)])

    def getMessage(self, length=7):
        """Return a message paragraph length."""
        return '\n\n'.join([self.getParagraph() for i in range(
            random.randrange(3,length))])

    def getPhoneNumber(self, lang="fr", format="medium"):
        """Return a random Phone number."""
        if lang == "en_US":
            num = []
            num.append("%3.3i" % random.randrange(0, 999))
            num.append("%4.4i" % random.randrange(0, 9999))
            if format == "short":
                return "-".join(num)
            num.insert(0, "%3.3i" % random.randrange(0, 999))
            if format == "medium":
                return "(%s) %s-%s" % tuple(num)
            # default long
            return "+00 1 (%s) %s-%s" % tuple(num)

        # default lang == 'fr':
        num = ['07']
        for i in range(4):
            num.append('%2.2i' % random.randrange(0, 99))
        if format == "medium":
            return " ".join(num)
        elif format == "long":
            num[0] = '(0)7'
            return "+33 "+ " ".join(num)
        # default format == 'short':
        return "".join(num)

    def getAddress(self, lang="fr"):
        """Return a random address."""
        # default lang == fr
        return "%i %s %s\n%5.5i %s" % (
            random.randrange(1, 100),
            random.choice(['rue', 'avenue', 'place', 'boulevard']),
            self.getSubject(length_min=1, length_max=3),
            random.randrange(99000, 99999),
            self.getSubject(length_min=1, length_max=2))


def main():
    """Testing."""
    print 'Word: %s\n' % (Lipsum().getWord())
    print 'UniqWord: %s\n' % (Lipsum().getUniqWord())
    print 'Subject: %s\n' % (Lipsum().getSubject())
    print 'Subject uniq: %s\n' % (Lipsum().getSubject(uniq=True))
    print 'Sentence: %s\n' % (Lipsum().getSentence())
    print 'Paragraph: %s\n' % (Lipsum().getParagraph())
    print 'Message: %s\n' % (Lipsum().getMessage())
    print 'Phone number: %s\n' % Lipsum().getPhoneNumber()
    print 'Phone number fr short: %s\n' % Lipsum().getPhoneNumber(
        lang="fr", format="short")
    print 'Phone number fr medium: %s\n' % Lipsum().getPhoneNumber(
        lang="fr", format="medium")
    print 'Phone number fr long: %s\n' % Lipsum().getPhoneNumber(
        lang="fr", format="long")
    print 'Phone number en_US short: %s\n' % Lipsum().getPhoneNumber(
        lang="en_US", format="short")
    print 'Phone number en_US medium: %s\n' % Lipsum().getPhoneNumber(
        lang="en_US", format="medium")
    print 'Phone number en_US long: %s\n' % Lipsum().getPhoneNumber(
        lang="en_US", format="long")
    print 'Address default: %s' % Lipsum().getAddress()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = MergeResultFiles
# (C) Copyright 2010 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Merge FunkLoad result files to produce a report for distributed bench
reports."""
import xml.parsers.expat
from utils import trace

class EndOfConfig(Exception):
    pass

class FunkLoadConfigXmlParser:
    """Parse the config part of a funkload xml results file."""
    def __init__(self):
        """Init setup expat handlers."""
        self.current_element = [{'name': 'root'}]
        self.cycles = None
        self.cycle_duration = 0
        self.nodes = {}
        self.config = {}
        self.files = []
        self.current_file = None

    def parse(self, xml_file):
        """Do the parsing."""
        self.current_file = xml_file
        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.handleStartElement
        try:
            parser.ParseFile(file(xml_file))
        except xml.parsers.expat.ExpatError, msg:
            if (self.current_element[-1]['name'] == 'funkload'
                and str(msg).startswith('no element found')):
                print "Missing </funkload> tag."
            else:
                print 'Error: invalid xml bench result file'
                if len(self.current_element) <= 1 or (
                    self.current_element[1]['name'] != 'funkload'):
                    print """Note that you can generate a report only for a
                    bench result done with fl-run-bench (and not on a test
                    result done with fl-run-test)."""
                else:
                    print """You may need to remove non ascii char that comes
                    from error pages catched during the bench. iconv
                    or recode may help you."""
                print 'Xml parser element stack: %s' % [
                    x['name'] for x in self.current_element]
                raise
        except EndOfConfig:
            return

    def handleStartElement(self, name, attrs):
        """Called by expat parser on start element."""
        if name == 'funkload':
            self.config['version'] = attrs['version']
            self.config['time'] = attrs['time']
        elif name == 'config':
            self.config[attrs['key']] = attrs['value']
            if attrs['key'] == 'duration':
                if self.cycle_duration and attrs['value'] != self.cycle_duration:
                    trace('Skipping file %s with different cycle duration %s' % (self.current_file, attrs['value']))
                    raise EndOfConfig
                self.cycle_duration = attrs['value']
            elif attrs['key'] == 'cycles':
                if self.cycles and attrs['value'] != self.cycles:
                    trace('Skipping file %s with different cycles %s != %s' % (self.current_file, attrs['value'], self.cycles))
                    raise EndOfConfig
                self.cycles = attrs['value']
            elif attrs['key'] == 'node':
                self.nodes[self.current_file] = attrs['value']
        else:
            self.files.append(self.current_file)
            raise EndOfConfig

def replace_all(text, dic):
    for i, j in dic.iteritems():
        if isinstance(text, str):
            text = text.decode('utf-8', 'ignore')
        text = text.replace(i, j)
    return text.encode('utf-8')


class MergeResultFiles:
    def __init__(self, input_files, output_file):
        xml_parser = FunkLoadConfigXmlParser()
        for input_file in input_files:
            trace (".")
            xml_parser.parse(input_file)

        node_count = len(xml_parser.files)

        # compute cumulated cycles
        node_cycles = [int(item) for item in xml_parser.cycles[1:-1].split(',')]
        cycles = map(lambda x: x * node_count, node_cycles)

        # node names
        node_names = []
        i = 0
        for input_file in xml_parser.files:
            node_names.append(xml_parser.nodes.get(input_file, 'node-' + str(i)))
            i += 1
        trace("\nnodes: %s\n" % ', '.join(node_names))
        trace("cycles for a node:    %s\n" % node_cycles)
        trace("cycles for all nodes: %s\n" % cycles)

        output = open(output_file, 'w+')
        i = 0
        for input_file in xml_parser.files:
            dic = {xml_parser.cycles: str(cycles),
                   'host="localhost"': 'host="%s"' % node_names[i],
                   'thread="': 'thread="' + str(i)}
            if i == 0:
                dic['key="node" value="%s"' % node_names[0]] = 'key="node" value="%s"' % (
                    ', '.join(node_names))
            c = 0
            for cycle in node_cycles:
                dic['cycle="%3.3i" cvus="%3.3i"' % (c, node_cycles[c])] = 'cycle="%3.3i" cvus="%3.3i"' % (c, cycles[c])
                c += 1

            f = open(input_file)
            for line in f.xreadlines():
                if "</funkload>" in line:
                    continue
                elif i > 0 and ('<funkload' in line or '<config' in line):
                    continue
                output.write(replace_all(line, dic))
            f.close()
            i += 1
        output.write("</funkload>\n")
        output.close()




########NEW FILE########
__FILENAME__ = Monitor
# (C) Copyright 2005-2011 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors: 
#   Krzysztof A. Adamski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""A Linux monitor server/controller.
"""
import sys
from time import time, sleep
from threading import Thread
from XmlRpcBase import XmlRpcBaseServer, XmlRpcBaseController
from MonitorPlugins import MonitorPlugins

# ------------------------------------------------------------
# classes
#
class MonitorInfo:
    """A simple class to collect info."""
    def __init__(self, host, plugins):
        self.time = time()
        self.host = host
        for plugin in (plugins.MONITORS.values()):
            for key, value in plugin.getStat().items():
                setattr(self, key, value)

    def __repr__(self, extra_key=None):
        text = "<monitor "
        if extra_key is not None:
            text += 'key="%s" ' % extra_key
        for key, value in self.__dict__.items():
            text += '%s="%s" ' % (key, value)
        text += ' />'
        return text


class MonitorThread(Thread):
    """The monitor thread that collect information."""
    def __init__(self, records, plugins, host=None, interval=None):
        Thread.__init__(self)
        self.records = records
        self._recorder_count = 0        # number of recorder
        self._running = False           # boolean running mode
        self._interval = None           # interval between monitoring
        self._host = None               # name of the monitored host
        self._plugins=plugins           # monitor plugins
        self.setInterval(interval)
        self.setHost(host)
        # this makes threads endings if main stop with a KeyboardInterupt
        self.setDaemon(1)

    def setInterval(self, interval):
        """Set the interval between monitoring."""
        self._interval = interval

    def setHost(self, host):
        """Set the monitored host."""
        self._host = host

    def run(self):
        """Thread jobs."""
        self._running = True
        while self._running:
            t1=time()
            if self._recorder_count > 0:
                self.monitor()
            t2=time()
            to_sleep=self._interval-(t2-t1)
            if to_sleep>0:
                sleep(to_sleep)

    def stop(self):
        """Stop the thread."""
        self._running = False

    def monitor(self):
        """The monitor task."""
        self.records.append(MonitorInfo(self._host, self._plugins))

    def startRecord(self):
        """Enable recording."""
        self._recorder_count += 1

    def stopRecord(self):
        """Stop recording."""
        self._recorder_count -= 1

    def countRecorders(self):
        """Return the number of recorder."""
        return self._recorder_count



# ------------------------------------------------------------
# Server
#
class MonitorServer(XmlRpcBaseServer):
    """The XML RPC monitor server."""
    server_name = "monitor"
    method_names = XmlRpcBaseServer.method_names + [
        'startRecord', 'stopRecord', 'getResult', 'getXmlResult', 'getMonitorsConfig']

    def __init__(self, argv=None):
        self.interval = None
        self.records = []
        self._keys = {}
        XmlRpcBaseServer.__init__(self, argv)
        self.plugins=MonitorPlugins(self._conf)
        self.plugins.registerPlugins()
        self._monitor = MonitorThread(self.records,
                                      self.plugins,
                                      self.host,
                                      self.interval)
        self._monitor.start()

    def _init_cb(self, conf, options):
        """init callback."""
        self.interval = conf.getfloat('server', 'interval')
        self._conf=conf

    def startRecord(self, key):
        """Start to monitor if it is the first key."""
        self.logd('startRecord %s' % key)
        if not self._keys.has_key(key) or self._keys[key][1] is not None:
            self._monitor.startRecord()
        self._keys[key] = [len(self.records), None]
        return 1

    def stopRecord(self, key):
        """Stop to monitor if it is the last key."""
        self.logd('stopRecord %s' % key)
        if not self._keys.has_key(key) or self._keys[key][1] is not None:
            return 0
        self._keys[key] = [self._keys[key][0], len(self.records)]
        self._monitor.stopRecord()
        return 1

    def getResult(self, key):
        """Return stats for key."""
        self.logd('getResult %s' % key)
        if key not in self._keys.keys():
            return []
        ret = self.records[self._keys[key][0]:self._keys[key][1]]
        return ret

    def getMonitorsConfig(self):
        ret = {}
        for plugin in (self.plugins.MONITORS.values()):
            conf = plugin.getConfig()
            if conf:
                ret[plugin.name] = conf
        return ret

    def getXmlResult(self, key):
        """Return result as xml."""
        self.logd('getXmlResult %s' % key)
        ret = self.getResult(key)
        ret = [stat.__repr__(key) for stat in ret]
        return '\n'.join(ret)

    def test(self):
        """auto test."""
        key = 'internal_test_monitor'
        self.startRecord(key)
        sleep(3)
        self.stopRecord(key)
        self.log(self.records)
        self.log(self.getXmlResult(key))
        return 1



# ------------------------------------------------------------
# Controller
#
class MonitorController(XmlRpcBaseController):
    """Monitor controller."""
    server_class = MonitorServer

    def test(self):
        """Testing monitor server."""
        server = self.server
        key = 'internal_test_monitor'
        server.startRecord(key)
        sleep(2)
        server.stopRecord(key)
        self.log(server.getXmlResult(key))
        return 0

# ------------------------------------------------------------
# main
#
def main():
    """Control monitord server."""
    ctl = MonitorController()
    sys.exit(ctl())

def test():
    """Test wihtout rpc server."""
    mon = MonitorServer()
    mon.test()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = MonitorPlugins
# (C) 2011-2012 Nuxeo SAS <http://nuxeo.com>
# Author: Krzysztof A. Adamski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
import sys
import re
import pickle
import pkg_resources

ENTRYPOINT = 'funkload.plugins.monitor'

gd_colors = [['red', 0xff0000],
             ['green', 0x00ff00],
             ['blue', 0x0000ff],
             ['yellow', 0xffff00],
             ['purple', 0x7f007f],
             ]


class MonitorPlugins():
    MONITORS = {}

    def __init__(self, conf=None):
        self.conf = conf
        self.enabled = None
        self.disabled = None
        if conf == None or not conf.has_section('plugins'):
            return
        if conf.has_option('plugins', 'monitors_enabled'):
            self.enabled = re.split(r'\s+', conf.get('plugins', 'monitors_enabled'))
        if conf.has_option('plugins', 'monitors_disabled'):
            self.disabled = re.split(r'\s+', conf.get('plugins', 'monitors_disabled'))

    def registerPlugins(self):
        for entrypoint in pkg_resources.iter_entry_points(ENTRYPOINT):
            p = entrypoint.load()(self.conf)
            if self.enabled != None:
                if p.name in self.enabled:
                    self.MONITORS[p.name] = p
            elif self.disabled != None:
                if p.name not in self.disabled:
                    self.MONITORS[p.name] = p
            else:
                self.MONITORS[p.name] = p

    def configure(self, config):
        for plugin in self.MONITORS.values():
            if config.has_key(plugin.name):
                plugin.setConfig(config[plugin.name])


class Plot:
    def __init__(self, plots, title="", ylabel="", unit="", **kwargs):
        self.plots = plots
        self.title = title
        self.ylabel = ylabel
        self.unit = unit
        for key in kwargs:
            setattr(self, key, kwargs[key])


class MonitorPlugin(object):
    def __init__(self, conf=None):
        if not hasattr(self, 'name') or self.name == None:
            self.name = self.__class__.__name__
        if not hasattr(self, 'plots'):
            self.plots = []
        self._conf = conf

    def _getKernelRev(self):
        """Get the kernel version."""
        version = open("/proc/version").readline()
        kernel_rev = float(re.search(r'version (\d+\.\d+)\.\d+',
                                     version).group(1))
        return kernel_rev

    def _checkKernelRev(self):
        """Check the linux kernel revision."""
        kernel_rev = self._getKernelRev()
        if (kernel_rev > 2.6) or (kernel_rev < 2.4):
            sys.stderr.write(
                "Sorry, kernel v%0.1f is not supported\n" % kernel_rev)
            sys.exit(-1)
        return kernel_rev

    def gnuplot(self, times, host, image_prefix, data_prefix, gplot_path, chart_size, stats):
        parsed = self.parseStats(stats)
        if parsed == None:
            return None

        image_path = "%s.png" % image_prefix
        data_path = "%s.data" % data_prefix

        data = [times]
        labels = ["TIME"]
        plotlines = []
        plotsno = 0
        for plot in self.plots:
            if len(plot.plots) == 0:
                continue
            ylabel = plot.ylabel
            if plot.unit != "":
                ylabel += '[%s]' % plot.unit
            plotlines.append('set title "%s"' % plot.title)
            plotlines.append('set ylabel "%s"' % ylabel)
            plot_line = 'plot "%s"' % data_path

            li = []
            for p in plot.plots.keys():
                data.append(parsed[p])
                labels.append(p)
                li.append(' u 1:%d title "%s" with %s' % (len(data), plot.plots[p][1], plot.plots[p][0]))
            plotlines.append(plot_line + ', ""'.join(li))
            plotsno += 1

        lines = []
        lines.append('set output "%s"' % image_path)
        lines.append('set terminal png size %d,%d' % (chart_size[0], chart_size[1] * plotsno))
        lines.append('set grid back')
        lines.append('set xdata time')
        lines.append('set timefmt "%H:%M:%S"')
        lines.append('set format x "%H:%M"')
        lines.append('set multiplot layout %d, 1' % plotsno)
        lines.extend(plotlines)

        data = zip(*data)
        f = open(data_path, 'w')
        f.write("%s\n" % " ".join(labels))
        for line in data:
            f.write(' '.join([str(item) for item in line]) + '\n')
        f.close()

        f = open(gplot_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()

        return [(self.name, image_path)]

    def gdchart(self, x, times, host, image_prefix, stats):
        parsed = self.parseStats(stats)
        if parsed == None:
            return None

        ret = []
        i = 0
        for plot in self.plots:
            image_path = "%s_%d.png" % (image_prefix, i)
            i += 1
            title = "%s:" % host
            data = []
            title_parts = []
            j = 0
            for p in plot.plots.keys():
                data.append(parsed[p])
                title_parts.append(" %s (%s)" % (plot.plots[p][1], gd_colors[j][0]))
                j += 1
            title += ", ".join(title_parts)

            colors = []
            for c in gd_colors:
                colors.append(c[1])

            x.title = title
            x.ytitle = plot.ylabel
            x.ylabel_fmt = '%%.2f %s' % plot.unit
            x.set_color = tuple(colors)
            x.title = title
            x.xtitle = 'time and CUs'
            x.setLabels(times)
            x.setData(*data)
            x.draw(image_path)
            ret.append((plot.title, image_path))

        return ret

    def getConfig(self):
        return pickle.dumps(self.plots).replace("\n", "\\n")

    def setConfig(self, config):
        config = str(config.replace("\\n", "\n"))
        self.plots = pickle.loads(config)

    def getStat(self):
        """ Read stats from system """
        pass

    def parseStats(self, stats):
        """ Parse MonitorInfo object list """
        pass

########NEW FILE########
__FILENAME__ = MonitorPluginsDefault
# (C) 2012 Nuxeo SAS <http://nuxeo.com>
# Authors: Krzysztof A. Adamski
#          bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
from  MonitorPlugins import MonitorPlugin, Plot


class MonitorCUs(MonitorPlugin):
    plot1 = {'CUs': ['impulse', 'CUs']}
    plots = [Plot(plot1, title="Concurent users", ylabel="CUs")]

    def getStat(self):
        return {}

    def parseStats(self, stats):
        if not (hasattr(stats[0], 'cvus')):
            return None
        cus = [int(x.cvus) for x in stats]

        return {'CUs': cus}


class MonitorMemFree(MonitorPlugin):
    plot1 = {'MEM': ['lines lw 2', 'Memory'],
             'SWAP': ['lines lw 2', 'Swap']}
    plots = [Plot(plot1, title="Memory usage", unit="kB")]

    def getStat(self):
        meminfo_fields = ["MemTotal", "MemFree", "SwapTotal", "SwapFree", "Buffers", "Cached"]
        meminfo = open("/proc/meminfo")
        kernel_rev = self._getKernelRev()
        if kernel_rev <= 2.4:
            # Kernel 2.4 has extra lines of info, duplicate of later info
            meminfo.readline()
            meminfo.readline()
            meminfo.readline()
        lines = meminfo.readlines()
        meminfo.close()
        meminfo_stats = {}
        for line in lines:
            line = line[:-1]
            stats = line.split()
            field = stats[0][:-1]
            if field in meminfo_fields:
                meminfo_stats[field[0].lower() + field[1:]] = stats[1]
        return meminfo_stats

    def parseStats(self, stats):
        if not (hasattr(stats[0], 'memTotal') and
                hasattr(stats[0], 'memFree') and
                hasattr(stats[0], 'swapTotal') and
                hasattr(stats[0], 'swapFree')):
            return None
        mem_total = int(stats[0].memTotal)
        if hasattr(stats[0], 'buffers'):
            mem_used = [mem_total - int(x.memFree) - int(x.buffers) - int(x.cached) for x in stats]
        else:
            # old monitoring does not have cached or buffers info
            mem_used = [mem_total - int(x.memFree) for x in stats]
        mem_used_start = mem_used[0]
        mem_used = [x - mem_used_start for x in mem_used]
        swap_total = int(stats[0].swapTotal)
        swap_used = [swap_total - int(x.swapFree) for x in stats]
        swap_used_start = swap_used[0]
        swap_used = [x - swap_used_start for x in swap_used]
        return {'MEM': mem_used, 'SWAP': swap_used}


class MonitorCPU(MonitorPlugin):
    plot1 = {'CPU': ['impulse lw 2', 'CPU 1=100%%'],
            'LOAD1': ['lines lw 2', 'Load 1min'],
            'LOAD5': ['lines lw 2', 'Load 5min'],
            'LOAD15': ['lines lw 2', 'Load 15min']}
    plots = [Plot(plot1, title="Load average", ylabel="loadavg")]

    def getStat(self):
        return dict(self._getCPU().items() + self._getLoad().items())

    def _getCPU(self):
        """Read the current system cpu usage from /proc/stat."""
        lines = open("/proc/stat").readlines()
        for line in lines:
            #print "l = %s" % line
            l = line.split()
            if len(l) < 5:
                continue
            if l[0].startswith('cpu'):
                # cpu = sum of usr, nice, sys
                cpu = long(l[1]) + long(l[2]) + long(l[3])
                idl = long(l[4])
                return {'CPUTotalJiffies': cpu,
                        'IDLTotalJiffies': idl,
                        }
        return {}

    def _getLoad(self):
        """Read the current system load from /proc/loadavg."""
        loadavg = open("/proc/loadavg").readline()
        loadavg = loadavg[:-1]
        # Contents are space separated:
        # 5, 10, 15 min avg. load, running proc/total threads, last pid
        stats = loadavg.split()
        running = stats[3].split("/")
        load_stats = {}
        load_stats['loadAvg1min'] = stats[0]
        load_stats['loadAvg5min'] = stats[1]
        load_stats['loadAvg15min'] = stats[2]
        load_stats['running'] = running[0]
        load_stats['tasks'] = running[1]
        return load_stats

    def parseStats(self, stats):
        if not (hasattr(stats[0], 'loadAvg1min') and
                hasattr(stats[0], 'loadAvg5min') and
                hasattr(stats[0], 'loadAvg15min')):
            return None
        cpu_usage = [0]
        for i in range(1, len(stats)):
            if not (hasattr(stats[i], 'CPUTotalJiffies') and
                    hasattr(stats[i - 1], 'CPUTotalJiffies')):
                cpu_usage.append(None)
            else:
                dt = ((long(stats[i].IDLTotalJiffies) +
                       long(stats[i].CPUTotalJiffies)) -
                      (long(stats[i - 1].IDLTotalJiffies) +
                       long(stats[i - 1].CPUTotalJiffies)))
                if dt:
                    ttl = (float(long(stats[i].CPUTotalJiffies) -
                                 long(stats[i - 1].CPUTotalJiffies)) /
                           dt)
                else:
                    ttl = None
                cpu_usage.append(ttl)

        load_avg_1 = [float(x.loadAvg1min) for x in stats]
        load_avg_5 = [float(x.loadAvg5min) for x in stats]
        load_avg_15 = [float(x.loadAvg15min) for x in stats]
        return {'LOAD1': load_avg_1,
                'LOAD5': load_avg_5,
                'LOAD15': load_avg_15,
                'CPU': cpu_usage}


class MonitorNetwork(MonitorPlugin):
    interface = 'eth0'
    plot1 = {'NETIN': ['lines lw 2', 'In'],
            'NETOUT': ['lines lw 2', 'Out']}
    plots = [Plot(plot1, title="Network traffic", ylabel="", unit="kB")]

    def __init__(self, conf):
        super(MonitorNetwork, self).__init__(conf)
        if conf != None:
            self.interface = conf.get('server', 'interface')

    def getStat(self):
        """Read the stats from an interface."""
        ifaces = open("/proc/net/dev")
        # Skip the information banner
        ifaces.readline()
        ifaces.readline()
        # Read the rest of the lines
        lines = ifaces.readlines()
        ifaces.close()
        # Process the interface lines
        net_stats = {}
        for line in lines:
            # Parse the interface line
            # Interface is followed by a ':' and then bytes, possibly with
            # no spaces between : and bytes
            line = line[:-1]
            (device, data) = line.split(':')

            # Get rid of leading spaces
            device = device.lstrip()
            # get the stats
            stats = data.split()
            if device == self.interface:
                net_stats['receiveBytes'] = stats[0]
                net_stats['receivePackets'] = stats[1]
                net_stats['transmitBytes'] = stats[8]
                net_stats['transmitPackets'] = stats[9]
        return net_stats

    def parseStats(self, stats):
        if not (hasattr(stats[0], 'transmitBytes') or
                hasattr(stats[0], 'receiveBytes')):
            return None
        net_in = [None]
        net_out = [None]
        for i in range(1, len(stats)):
            if not (hasattr(stats[i], 'receiveBytes') and
                    hasattr(stats[i - 1], 'receiveBytes')):
                net_in.append(None)
            else:
                net_in.append((int(stats[i].receiveBytes) -
                               int(stats[i - 1].receiveBytes)) /
                              (1024 * (float(stats[i].time) -
                                       float(stats[i - 1].time))))

            if not (hasattr(stats[i], 'transmitBytes') and
                    hasattr(stats[i - 1], 'transmitBytes')):
                net_out.append(None)
            else:
                net_out.append((int(stats[i].transmitBytes) -
                                int(stats[i - 1].transmitBytes)) /
                              (1024 * (float(stats[i].time) -
                                       float(stats[i - 1].time))))
        return {'NETIN': net_in, 'NETOUT': net_out}

########NEW FILE########
__FILENAME__ = PatchWebunit
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors: Tom Lazar
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Patching Richard Jones' webunit for FunkLoad.

* Add cache for links (css, js)
* store a browser history
* add headers
* log response
* remove webunit log
* fix HTTPResponse __repr__
* patching webunit mimeEncode to be rfc 1945 3.6.2 compliant using CRLF
* patching to remove cookie with a 'deleted' value
* patching to have application/x-www-form-urlencoded by default and only
  multipart when a file is posted
* patch fetch postdata must be [(key, value) ...] no more dict or list value

$Id: PatchWebunit.py 24649 2005-08-29 14:20:19Z bdelbosc $
"""
import os
import sys
import time
import urlparse
from urllib import urlencode
import httplib
import cStringIO
from mimetypes import guess_type
import datetime
import Cookie

from webunit import cookie
from webunit.IMGSucker import IMGSucker
from webunit.webunittest import WebTestCase, WebFetcher
from webunit.webunittest import HTTPResponse, HTTPError, VERBOSE
from webunit.utility import Upload

from utils import thread_sleep, Data
import re

valid_url = re.compile(r'^(http|https)://[a-z0-9\.\-\:]+(\/[^\ \t\<\>]*)?$',
                       re.I)

BOUNDARY = '--------------GHSKFJDLGDS7543FJKLFHRE75642756743254'
SEP_BOUNDARY = '--' + BOUNDARY
END_BOUNDARY = SEP_BOUNDARY + '--'

def mimeEncode(data, sep_boundary=SEP_BOUNDARY, end_boundary=END_BOUNDARY):
    '''Take the mapping of data and construct the body of a
    multipart/form-data message with it using the indicated boundaries.
    '''
    ret = cStringIO.StringIO()
    first_part = True
    for key, value in data:
        if not key:
            continue
        # Don't add newline before first part
        if first_part:
            first_part = False
        else:
            ret.write('\r\n')
        ret.write(sep_boundary)
        if isinstance(value, Upload):
            ret.write('\r\nContent-Disposition: form-data; name="%s"'%key)
            ret.write('; filename="%s"\r\n' % os.path.basename(value.filename))
            if value.filename:
                mimetype = guess_type(value.filename)[0]
                if mimetype is not None:
                    ret.write('Content-Type: %s\r\n' % mimetype)
                value = open(os.path.join(value.filename), "rb").read()
            else:
                value = ''
            ret.write('\r\n')
        else:
            ret.write('\r\nContent-Disposition: form-data; name="%s"'%key)
            ret.write("\r\n\r\n")
        ret.write(str(value))
        if value and value[-1] == '\r':
            ret.write('\r\n')  # write an extra newline
    ret.write('\r\n')
    ret.write(end_boundary)
    ret.write('\r\n')
    return ret.getvalue()


class FKLIMGSucker(IMGSucker):
    """Image and links loader, patched to log response stats."""
    def __init__(self, url, session, ftestcase=None):
        IMGSucker.__init__(self, url, session)
        self.ftestcase = ftestcase

    def do_img(self, attributes):
        """Process img tag."""
        newattributes = []
        for name, value in attributes:
            if name == 'src':
                # construct full url
                url = urlparse.urljoin(self.base, value)
                # make sure it's syntactically valid
                if not valid_url.match(url):
                    continue
                # TODO: figure the re-write path
                # newattributes.append((name, path))
                if not self.session.images.has_key(url):
                    self.ftestcase.logdd('    img: %s ...' % url)
                    t_start = time.time()
                    self.session.images[url] = self.session.fetch(url)
                    t_stop = time.time()
                    self.ftestcase.logdd('     Done in %.3fs' %
                                         (t_stop - t_start))
                    self.session.history.append(('image', url))
                    self.ftestcase.total_time += (t_stop - t_start)
                    self.ftestcase.total_images += 1
                    self.ftestcase._log_response(self.session.images[url],
                                                 'image', None, t_start,
                                                 t_stop)
                    thread_sleep()      # give a chance to other threads
            else:
                newattributes.append((name, value))
        # Write the img tag to file (with revised paths)
        self.unknown_starttag('img', newattributes)

    def do_link(self, attributes):
        """Process link tag."""
        newattributes = [('rel', 'stylesheet'), ('type', 'text/css')]
        for name, value in attributes:
            if name == 'href':
                # construct full url
                url = urlparse.urljoin(self.base, value)
                # make sure it's syntactically valid
                if not valid_url.match(url):
                    continue
                # TODO: figure the re-write path
                # newattributes.append((name, path))
                if not self.session.css.has_key(url):
                    self.ftestcase.logdd('    link: %s ...' % url)
                    t_start = time.time()
                    self.session.css[url] = self.session.fetch(url)
                    t_stop = time.time()
                    self.ftestcase.logdd('     Done in %.3fs' %
                                         (t_stop - t_start))
                    self.session.history.append(('link', url))
                    self.ftestcase.total_time += (t_stop - t_start)
                    self.ftestcase.total_links += 1
                    self.ftestcase._log_response(self.session.css[url],
                                                 'link', None, t_start, t_stop)
                    thread_sleep()      # give a chance to other threads
            else:
                newattributes.append((name, value))
        # Write the link tag to file (with revised paths)
        self.unknown_starttag('link', newattributes)

# remove webunit logging
def WTC_log(self, message, content):
    """Remove webunit logging."""
    pass
WebTestCase.log = WTC_log

def decodeCookies(url, server, headers, cookies):
    """Decode cookies into the supplied cookies dictionary,
    according to RFC 6265.

    Relevant specs:
    http://www.ietf.org/rfc/rfc2109.txt (obsolete)
    http://www.ietf.org/rfc/rfc2965.txt (obsolete)
    http://www.ietf.org/rfc/rfc6265.txt (proposed standard)
    """
    # see rfc 6265, section 5.1.4
    # empty path => '/'
    # path must begin with '/', so we only weed out the rightmost '/'
    request_path = urlparse.urlparse(url)[2]
    if len(request_path) > 2 and request_path[-1] == '/':
        request_path = request_path[:-1]
    else:
        request_path = '/'

    # XXX - tried slurping all the set-cookie and joining them on
    # '\n', some cookies were not parsed. This below worked flawlessly.
    for ch in headers.getallmatchingheaders('set-cookie'):
        cookie = Cookie.SimpleCookie(ch.strip()).values()[0]

        # see rfc 6265, section 5.3, step 7
        path = cookie['path'] or request_path

        # see rfc 6265, section 5.3, step 4 to 6
        # XXX - we don't bother with cookie persistence
        # XXX - we don't check for public suffixes
        if cookie['domain']:
            domain = cookie['domain']
            # see rfc6265, section 5.2.3
            if domain[0] == '.':
               domain = domain[1:]
            if not server.endswith(domain):
               continue
        else:
            domain = server

        # all date handling is done is UTC
        # XXX - need reviewing by someone familiar with python datetime objects
        now = datetime.datetime.utcnow()
        expire = datetime.datetime.min
        maxage = cookie['max-age']
        # see rfc 6265, section 5.3, step 3
        if maxage != '':
            timedelta = int(maxage)
            if timedelta > 0:
                expire = now + timedelta
        else:
            if cookie['expires'] == '':
                expire = datetime.datetime.max
            else:
                expire = datetime.datetime.strptime(cookie['expires'],"%a, %d-%b-%Y %H:%M:%S %Z")

        cookie['expires'] = expire
        bydom = cookies.setdefault(domain, {})
        bypath = bydom.setdefault(path, {})

        if expire > now:
            bypath[cookie.key] = cookie
        elif cookie.key in bypath:
            del bypath[cookie.key]


# use fl img sucker
def WTC_pageImages(self, url, page, testcase=None):
    '''Given the HTML page that was loaded from url, grab all the images.
    '''
    sucker = FKLIMGSucker(url, self, testcase)
    sucker.feed(page)
    sucker.close()

WebTestCase.pageImages = WTC_pageImages


# WebFetcher fetch
def WF_fetch(self, url, postdata=None, server=None, port=None, protocol=None,
             ok_codes=None, key_file=None, cert_file=None, method="GET", consumer=None):
    '''Run a single test request to the indicated url. Use the POST data
    if supplied. Accepts key and certificate file paths for https (ssl/tls)
    connections.

    Raises failureException if the returned data contains any of the
    strings indicated to be Error Content.
    Returns a HTTPReponse object wrapping the response from the server.
    '''
    # see if the url is fully-qualified (not just a path)
    t_protocol, t_server, t_url, x, t_args, x = urlparse.urlparse(url)
    if t_server:
        protocol = t_protocol
        if ':' in t_server:
            server, port = t_server.split(':')
        else:
            server = t_server
            if protocol == 'http':
                port = '80'
            else:
                port = '443'
        url = t_url
        if t_args:
            url = url + '?' + t_args
        # ignore the machine name if the URL is for localhost
        if t_server == 'localhost':
            server = None
    elif not server:
        # no server was specified with this fetch, or in the URL, so
        # see if there's a base URL to use.
        base = self.get_base_url()
        if base:
            t_protocol, t_server, t_url, x, x, x = urlparse.urlparse(base)
            if t_protocol:
                protocol = t_protocol
            if t_server:
                server = t_server
            if t_url:
                url = urlparse.urljoin(t_url, url)

    # TODO: allow override of the server and port from the URL!
    if server is None:
        server = self.server
    if port is None:
        port = self.port
    if protocol is None:
        protocol = self.protocol
    if ok_codes is None:
        ok_codes = self.expect_codes
    webproxy = {}

    if protocol == 'http':
        try:
            proxystring = os.environ["http_proxy"].replace("http://", "")
            webproxy['host'] = proxystring.split(":")[0]
            webproxy['port'] = int(proxystring.split(":")[1])
        except (KeyError, IndexError, ValueError):
            webproxy = False

        if webproxy:
            h = httplib.HTTPConnection(webproxy['host'], webproxy['port'])
        else:
            h = httplib.HTTP(server, int(port))
        if int(port) == 80:
            host_header = server
        else:
            host_header = '%s:%s' % (server, port)
    elif protocol == 'https':
        #if httpslib is None:
            #raise ValueError, "Can't fetch HTTPS: M2Crypto not installed"

        # FL Patch -------------------------
        try:
            proxystring = os.environ["https_proxy"].replace("http://", "").replace("https://", "")
            webproxy['host'] = proxystring.split(":")[0]
            webproxy['port'] = int(proxystring.split(":")[1])
        except (KeyError, IndexError, ValueError):
            webproxy = False

        # patched to use the given key and cert file
        if webproxy:
            h = httplib.HTTPSConnection(webproxy['host'], webproxy['port'],
                                        key_file, cert_file)
        else:
            h = httplib.HTTPS(server, int(port), key_file, cert_file)

        # FL Patch end  -------------------------

        if int(port) == 443:
            host_header = server
        else:
            host_header = '%s:%s' % (server, port)
    else:
        raise ValueError, protocol

    headers = []
    params = None
    if postdata is not None:
        if webproxy:
            h.putrequest(method.upper(), "%s://%s%s" % (protocol,
                                                        host_header, url))
        else:
            # Normal post
            h.putrequest(method.upper(), url)
        if postdata:
            if isinstance(postdata, Data):
                # User data and content_type
                params = postdata.data
                if postdata.content_type:
                    headers.append(('Content-type', postdata.content_type))
            else:
                # Check for File upload
                is_multipart = False
                for field, value in postdata:
                    if isinstance(value, Upload):
                        # Post with a data file requires multipart mimeencode
                        is_multipart = True
                        break
                if is_multipart:
                    params = mimeEncode(postdata)
                    headers.append(('Content-type', 'multipart/form-data; boundary=%s'%
                                    BOUNDARY))
                else:
                    params = urlencode(postdata)
                    headers.append(('Content-type', 'application/x-www-form-urlencoded'))
            headers.append(('Content-length', str(len(params))))
    else:
        if webproxy:
            h.putrequest(method.upper(), "%s://%s%s" % (protocol,
                                                        host_header, url))
        else:
            h.putrequest(method.upper(), url)

    # Other Full Request headers
    if self.authinfo:
        headers.append(('Authorization', "Basic %s"%self.authinfo))
    if not webproxy:
        # HTTPConnection seems to add a host header itself.
        # So we only need to do this if we are not using a proxy.
        headers.append(('Host', host_header))

    # FL Patch -------------------------
    for key, value in self.extra_headers:
        headers.append((key, value))

    # FL Patch end ---------------------

    # Send cookies
    #  - check the domain, max-age (seconds), path and secure
    #    (http://www.ietf.org/rfc/rfc2109.txt)
    cookies_used = []
    cookie_list = []
    for domain, cookies in self.cookies.items():
        # check cookie domain
        if not server.endswith(domain) and domain[1:] != server:
            continue
        for path, cookies in cookies.items():
            # check that the path matches
            urlpath = urlparse.urlparse(url)[2]
            if not urlpath.startswith(path) and not (path == '/' and
                    urlpath == ''):
                continue
            for sendcookie in cookies.values():
                # and that the cookie is or isn't secure
                if sendcookie['secure'] and protocol != 'https':
                    continue
                # TODO: check for expires (max-age is working)
                # hard coded value that application can use to work
                # around expires
                if sendcookie.coded_value in ('"deleted"', "null", "deleted"):
                    continue
                cookie_list.append("%s=%s;"%(sendcookie.key,
                                            sendcookie.coded_value))
                cookies_used.append(sendcookie.key)

    if cookie_list:
        headers.append(('Cookie', ' '.join(cookie_list)))

    # check that we sent the cookies we expected to
    if self.expect_cookies is not None:
        assert cookies_used == self.expect_cookies, \
            "Didn't use all cookies (%s expected, %s used)"%(
            self.expect_cookies, cookies_used)


    # write and finish the headers
    for header in headers:
        h.putheader(*header)
    h.endheaders()

    if self.debug_headers:
        for header in headers:
            print "Putting header -- %s: %s" % header

    if params is not None:
        h.send(params)

    # handle the reply
    if webproxy:
        r = h.getresponse()
        errcode = r.status
        errmsg = r.reason
        headers = r.msg
        if headers is None or headers.has_key('content-length') and headers['content-length'] == "0":
            data = None
        else:
            data = r.read()
        response = HTTPResponse(self.cookies, protocol, server, port, url,
                                errcode, errmsg, headers, data,
                                self.error_content)

    else:
        # get the body and save it
        errcode, errmsg, headers = h.getreply()
        if headers is None or headers.has_key('content-length') and headers['content-length'] == "0":
            response = HTTPResponse(self.cookies, protocol, server, port, url,
                                    errcode, errmsg, headers, None,
                                    self.error_content)
        else:
            f = h.getfile()
            g = cStringIO.StringIO()
            if consumer is None:
                d = f.read()
            else:
                d = f.readline(1)
            while d:
                g.write(d)
                if consumer is None:
                    d = f.read()
                else:
                    ret = consumer(d)
                    if ret == 0:
                        # consumer close connection
                        d = None
                    else:
                        d = f.readline(1)
            response = HTTPResponse(self.cookies, protocol, server, port, url,
                                    errcode, errmsg, headers, g.getvalue(),
                                    self.error_content)
            f.close()

    if errcode not in ok_codes:
        if VERBOSE:
            sys.stdout.write('e')
            sys.stdout.flush()
        raise HTTPError(response)

    # decode the cookies
    if self.accept_cookies:
        try:
            # decode the cookies and update the cookies store
            decodeCookies(url, server, headers, self.cookies)
        except:
            if VERBOSE:
                sys.stdout.write('c')
                sys.stdout.flush()
            raise

    # Check errors
    if self.error_content:
        data = response.body
        for content in self.error_content:
            if data.find(content) != -1:
                msg = "Matched error: %s" % content
                if hasattr(self, 'results') and self.results:
                    self.writeError(url, msg)
                self.log('Matched error'+`(url, content)`, data)
                if VERBOSE:
                    sys.stdout.write('c')
                    sys.stdout.flush()
                raise self.failureException, msg

    if VERBOSE:
        sys.stdout.write('_')
        sys.stdout.flush()
    return response

WebFetcher.fetch = WF_fetch


def HR___repr__(self):
    """fix HTTPResponse rendering."""
    return """<response url="%s://%s:%s%s" code="%s" message="%s" />""" % (
        self.protocol, self.server, self.port, self.url, self.code,
        self.message)

HTTPResponse.__repr__ = HR___repr__


########NEW FILE########
__FILENAME__ = Recorder
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""TCPWatch FunkLoad Test Recorder.

Requires tcpwatch-httpproxy or tcpwatch.py available at:

* http://hathawaymix.org/Software/TCPWatch/tcpwatch-1.3.tar.gz

Credits goes to Ian Bicking for parsing tcpwatch files.

$Id$
"""
import os
import sys
import re
from cStringIO import StringIO
from optparse import OptionParser, TitledHelpFormatter
from tempfile import mkdtemp
import rfc822
from cgi import FieldStorage
from urlparse import urlsplit
from utils import truncate, trace, get_version, Data


def get_null_file():
    if sys.platform.lower().startswith('win'):
        return "NUL"
    else:
        return "/dev/null"


class Request:
    """Store a tcpwatch request."""
    def __init__(self, file_path):
        """Load a tcpwatch request file."""
        self.file_path = file_path
        f = open(file_path, 'rb')
        line = f.readline().replace('\r\r', '\r').split(None, 2)
        if not line:
            trace('# Warning: empty first line on %s\n' % self.file_path)
            line = f.readline().replace('\r\r', '\r').split(None, 2)
        self.method = line[0]
        url = line[1]
        scheme, host, path, query, fragment = urlsplit(url)
        self.host = scheme + '://' + host
        self.rurl = url[len(self.host):]
        self.url = url
        self.path = path
        self.version = line[2].strip()
        self.headers = dict(rfc822.Message(f).items())
        self.body = f.read().replace('\r\r\n','', 1).replace('\r\r', '\r').replace('\r\n', '\n')
        f.close()

    def extractParam(self):
        """Turn muti part encoded form into params."""
        params = []
        try:
            environ = {
                'CONTENT_TYPE': self.headers['content-type'],
                'CONTENT_LENGTH': self.headers['content-length'],
                'REQUEST_METHOD': 'POST',
                }
        except KeyError:
            trace('# Warning: missing header content-type or content-length'
                  ' in file: %s not an http request ?\n' % self.file_path)
            return params

        form = FieldStorage(fp=StringIO(self.body),
                            environ=environ,
                            keep_blank_values=True)
        try:
            keys = form.keys()
        except TypeError:
            trace('# Using custom data for request: %s ' % self.file_path)
            params = Data(self.headers['content-type'], self.body)
            return params

        for item in form.list:
            key = item.name
            value = item.value
            filename = item.filename

            if filename is None:
                params.append([key, value])
            else:
                # got a file upload
                filename = filename or ''
                params.append([key, 'Upload("%s")' % filename])
                if filename:
                    if os.path.exists(filename):
                        trace('# Warning: uploaded file: %s already'
                              ' exists, keep it.\n' % filename)
                    else:
                        trace('# Saving uploaded file: %s\n' % filename)
                        f = open(filename, 'w')
                        f.write(str(value))
                        f.close()
        return params

    def __repr__(self):
        params = ''
        if self.body:
            params = self.extractParam()
        return '<request method="%s" url="%s" %s/>' % (
            self.method, self.url, str(params))


class Response:
    """Store a tcpwatch response."""
    def __init__(self, file_path):
        """Load a tcpwatch response file."""
        self.file_path = file_path
        f = open(file_path, 'rb')
        line = f.readline().split(None, 2)
        self.version = line[0]
        self.status_code = line[1].strip()
        if len(line) > 2:
            self.status_message = line[2].strip()
        else:
            self.status_message = ''
        self.headers = dict(rfc822.Message(f).items())
        self.body = f.read()
        f.close()

    def __repr__(self):
        return '<response code="%s" type="%s" status="%s" />' % (
            self.status_code, self.headers.get('content-type'),
            self.status_message)


class RecorderProgram:
    """A tcpwatch to funkload recorder."""
    tcpwatch_cmd = ['tcpwatch-httpproxy', 'tcpwatch.py', 'tcpwatch']
    MYFACES_STATE = 'org.apache.myfaces.trinidad.faces.STATE'
    MYFACES_FORM = 'org.apache.myfaces.trinidad.faces.FORM'
    USAGE = """%prog [options] [test_name]

%prog launch a TCPWatch proxy and record activities, then output
a FunkLoad script or generates a FunkLoad unit test if test_name is specified.

The default proxy port is 8090.

Note that tcpwatch-httpproxy or tcpwatch.py executable must be accessible from your env.

See http://funkload.nuxeo.org/ for more information.

Examples
========
  %prog foo_bar
                        Run a proxy and create a FunkLoad test case,
                        generates test_FooBar.py and FooBar.conf file.
                        To test it:  fl-run-test -dV test_FooBar.py
  %prog -p 9090
                        Run a proxy on port 9090, output script to stdout.
  %prog -i /tmp/tcpwatch
                        Convert a tcpwatch capture into a script.
"""
    def __init__(self, argv=None):
        if argv is None:
            argv = sys.argv[1:]
        self.verbose = False
        self.tcpwatch_path = None
        self.prefix = 'watch'
        self.port = "8090"
        self.server_url = None
        self.class_name = None
        self.test_name = None
        self.loop = 1
        self.script_path = None
        self.configuration_path = None
        self.use_myfaces = False
        self.parseArgs(argv)

    def getTcpWatchCmd(self):
        """Return the tcpwatch cmd to use."""
        tcpwatch_cmd = self.tcpwatch_cmd[:]
        if os.getenv("TCPWATCH"):
            tcpwatch_cmd.insert(0, os.getenv("TCPWATCH"))
        for cmd in tcpwatch_cmd:
            ret = os.system(cmd + ' -h  2> %s' % get_null_file())
            if ret == 0:
                return cmd
        raise RuntimeError('Tcpwatch is not installed no %s found. '
                           'Visit http://funkload.nuxeo.org/INSTALL.html' %
                           str(self.tcpwatch_cmd))

    def parseArgs(self, argv):
        """Parse programs args."""
        parser = OptionParser(self.USAGE, formatter=TitledHelpFormatter(),
                              version="FunkLoad %s" % get_version())
        parser.add_option("-v", "--verbose", action="store_true",
                          help="Verbose output")
        parser.add_option("-p", "--port", type="string", dest="port",
                          default=self.port, help="The proxy port.")
        parser.add_option("-L", type="string", dest="forward",
                          default=None,
                          help="Forwarded connection <listen_port>:<dest_host>:<dest_port>.")
        parser.add_option("-i", "--tcp-watch-input", type="string",
                          dest="tcpwatch_path", default=None,
                          help="Path to an existing tcpwatch capture.")
        parser.add_option("-l", "--loop", type="int",
                          dest="loop", default=1,
                          help="Loop mode.")

        options, args = parser.parse_args(argv)
        if len(args) == 1:
            test_name = args[0]
        else:
            test_name = None

        self.verbose = options.verbose
        self.tcpwatch_path = options.tcpwatch_path
        self.port = options.port
        self.forward = options.forward
        if not test_name and not self.tcpwatch_path:
            self.loop = options.loop
        if test_name:
            test_name = test_name.replace('-', '_')
            class_name = ''.join([x.capitalize()
                                  for x in re.split('_|-', test_name)])
            self.test_name = test_name
            self.class_name = class_name
            self.script_path = './test_%s.py' % class_name
            self.configuration_path = './%s.conf' % class_name

    def startProxy(self):
        """Start a tcpwatch session."""
        self.tcpwatch_path = mkdtemp('_funkload')
        if self.forward is not None:
            cmd = self.getTcpWatchCmd() + ' -L %s -s -r %s' % (self.forward,
                                                               self.tcpwatch_path)
        else:
            cmd = self.getTcpWatchCmd() + ' -p %s -s -r %s' % (self.port,
                                                               self.tcpwatch_path)
        if os.name == 'posix':
            if self.verbose:
                cmd += ' | grep "T http"'
            else:
                cmd += ' > %s' % get_null_file()
        trace("Hit Ctrl-C to stop recording.\n")
        try:
            os.system(cmd)
        except KeyboardInterrupt:
            pass

    def searchFiles(self):
        """Search tcpwatch file."""
        items = {}
        prefix = self.prefix
        for filename in os.listdir(self.tcpwatch_path):
            if not filename.startswith(prefix):
                continue
            name, ext = os.path.splitext(filename)
            name = name[len(self.prefix):]
            ext = ext[1:]
            if ext == 'errors':
                trace("Error in response %s\n" % name)
                continue
            assert ext in ('request', 'response'), "Bad extension: %r" % ext
            items.setdefault(name, {})[ext] = os.path.join(
                self.tcpwatch_path, filename)
        items = items.items()
        items.sort()
        return [(v['request'], v['response'])
                for name, v in items
                if v.has_key('response')]

    def extractRequests(self, files):
        """Filter and extract request from tcpwatch files."""
        last_code = None
        filter_ctypes = ('image', 'css', 'javascript', 'x-shockwave-flash')
        filter_url = ('.jpg', '.png', '.gif', '.css', '.js', '.swf')
        requests = []
        for request_path, response_path in files:
            response = Response(response_path)
            request = Request(request_path)
            if self.server_url is None:
                self.server_url = request.host
            ctype = response.headers.get('content-type', '')
            url = request.url
            if request.method != "POST" and (
                last_code in ('301', '302') or
                [x for x in filter_ctypes if x in ctype] or
                [x for x in filter_url if url.endswith(x)]):
                last_code = response.status_code
                continue
            last_code = response.status_code
            requests.append(request)
        return requests

    def reindent(self, code, indent=8):
        """Improve indentation."""
        spaces = ' ' * indent
        code = code.replace('], [', '],\n%s    [' % spaces)
        code = code.replace('[[', '[\n%s    [' % spaces)
        code = code.replace(', description=', ',\n%s    description=' % spaces)
        code = code.replace('self.', '\n%sself.' % spaces)
        return code

    def convertToFunkLoad(self, request):
        """return a funkload python instruction."""
        text = []
        text.append('        # ' + request.file_path)
        if request.host != self.server_url:
            text.append('self.%s("%s"' % (request.method.lower(),
                                          request.url))
        else:
            text.append('self.%s(server_url + "%s"' % (
                request.method.lower(),  request.rurl.strip()))
        description = "%s %s" % (request.method.capitalize(),
                                 request.path | truncate(42))
        if request.body:
            params = request.extractParam()
            if isinstance(params, Data):
                params = "Data('%s', '''%s''')" % (params.content_type,
                                                       params.data)
            else:
                myfaces_form = None
                if self.MYFACES_STATE not in [key for key, value in params]:
                    params = 'params=%s' % params
                else:
                    # apache myfaces state add a wrapper
                    self.use_myfaces = True
                    new_params = []
                    for key, value in params:
                        if key == self.MYFACES_STATE:
                            continue
                        if key == self.MYFACES_FORM:
                            myfaces_form = value
                            continue
                        new_params.append([key, value])
                    params = "    self.myfacesParams(%s, form='%s')" % (
                        new_params, myfaces_form)
                params = re.sub("'Upload\(([^\)]*)\)'", "Upload(\\1)", params)
            text.append(', ' + params)
        text.append(', description="%s")' % description)
        return ''.join(text)

    def extractScript(self):
        """Convert a tcpwatch capture into a FunkLoad script."""
        files = self.searchFiles()
        requests = self.extractRequests(files)
        code = [self.convertToFunkLoad(request)
                for request in requests]
        if not code:
            trace("Sorry no action recorded.\n")
            return ''
        code.insert(0, '')
        return self.reindent('\n'.join(code))

    def writeScript(self, script):
        """Write the FunkLoad test script."""
        trace('Creating script: %s.\n' % self.script_path)
        from pkg_resources import resource_string
        if self.use_myfaces:
            tpl_name = 'data/MyFacesScriptTestCase.tpl'
        else:
            tpl_name = 'data/ScriptTestCase.tpl'
        tpl = resource_string('funkload', tpl_name)
        content = tpl % {'script': script,
                         'test_name': self.test_name,
                         'class_name': self.class_name}
        if os.path.exists(self.script_path):
            trace("Error file %s already exists.\n" % self.script_path)
            return
        f = open(self.script_path, 'w')
        f.write(content)
        f.close()

    def writeConfiguration(self):
        """Write the FunkLoad configuration test script."""
        trace('Creating configuration file: %s.\n' % self.configuration_path)
        from pkg_resources import resource_string
        tpl = resource_string('funkload', 'data/ConfigurationTestCase.tpl')
        content = tpl % {'server_url': self.server_url,
                         'test_name': self.test_name,
                         'class_name': self.class_name}
        if os.path.exists(self.configuration_path):
            trace("Error file %s already exists.\n" %
                  self.configuration_path)
            return
        f = open(self.configuration_path, 'w')
        f.write(content)
        f.close()

    def run(self):
        """run it."""
        count = self.loop
        while count:
            count -= 1
            if count:
                print "Remaining loop: %i" % count
            if self.tcpwatch_path is None:
                self.startProxy()
            script = self.extractScript()
            if not script:
                self.tcpwatch_path = None
                continue
            if self.test_name is not None:
                self.writeScript(script)
                self.writeConfiguration()
            else:
                print script
                print
            self.tcpwatch_path = None


def main():
    RecorderProgram().run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ReportBuilder
# (C) Copyright 2005-2011 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors:
#   Krzysztof A. Adamski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Create an ReST or HTML report with charts from a FunkLoad bench xml result.

Producing html and png chart require python-docutils and gnuplot

$Id: ReportBuilder.py 24737 2005-08-31 09:00:16Z bdelbosc $
"""

USAGE = """%prog [options] xmlfile [xmlfile...]

or

  %prog --diff REPORT_PATH1 REPORT_PATH2

%prog analyze a FunkLoad bench xml result file and output a report.
If there are more than one file the xml results are merged.

See http://funkload.nuxeo.org/ for more information.

Examples
========
  %prog funkload.xml
                        ReST rendering into stdout.
  %prog --html -o /tmp funkload.xml
                        Build an HTML report in /tmp
  %prog --html node1.xml node2.xml node3.xml
                        Build an HTML report merging test results from 3 nodes.
  %prog --diff /path/to/report-reference /path/to/report-challenger
                        Build a differential report to compare 2 bench reports,
                        requires gnuplot.
  %prog --trend /path/to/report-dir1 /path/to/report-1 ... /path/to/report-n
                        Build a trend report using multiple reports.
  %prog -h
                        More options.
"""
try:
    import psyco
    psyco.full()
except ImportError:
    pass
import os
import xml.parsers.expat
from optparse import OptionParser, TitledHelpFormatter
from tempfile import NamedTemporaryFile

from ReportStats import AllResponseStat, PageStat, ResponseStat, TestStat
from ReportStats import MonitorStat, ErrorStat
from ReportRenderRst import RenderRst
from ReportRenderHtml import RenderHtml
from ReportRenderDiff import RenderDiff
from ReportRenderTrend import RenderTrend
from MergeResultFiles import MergeResultFiles
from utils import trace, get_version
from apdex import Apdex


# ------------------------------------------------------------
# Xml parser
#
class FunkLoadXmlParser:
    """Parse a funkload xml results."""
    def __init__(self):
        """Init setup expat handlers."""
        parser = xml.parsers.expat.ParserCreate()
        parser.CharacterDataHandler = self.handleCharacterData
        parser.StartElementHandler = self.handleStartElement
        parser.EndElementHandler = self.handleEndElement
        parser.StartCdataSectionHandler = self.handleStartCdataSection
        parser.EndCdataSectionHandler = self.handleEndCdataSection
        self.parser = parser
        self.current_element = [{'name': 'root'}]
        self.is_recording_cdata = False
        self.current_cdata = ''

        self.cycles = None
        self.cycle_duration = 0
        self.stats = {}                 # cycle stats
        self.monitor = {}               # monitoring stats
        self.monitorconfig = {}         # monitoring config
        self.config = {}
        self.error = {}

    def parse(self, xml_file):
        """Do the parsing."""
        try:
            self.parser.ParseFile(file(xml_file))
        except xml.parsers.expat.ExpatError, msg:
            if (self.current_element[-1]['name'] == 'funkload'
                and str(msg).startswith('no element found')):
                print "Missing </funkload> tag."
            else:
                print 'Error: invalid xml bench result file'
                if len(self.current_element) <= 1 or (
                    self.current_element[1]['name'] != 'funkload'):
                    print """Note that you can generate a report only for a
                    bench result done with fl-run-bench (and not on a test
                    resu1lt done with fl-run-test)."""
                else:
                    print """You may need to remove non ascii characters which
                    come from error pages caught during the bench test. iconv
                    or recode may help you."""
                print 'Xml parser element stack: %s' % [
                    x['name'] for x in self.current_element]
                raise

    def handleStartElement(self, name, attrs):
        """Called by expat parser on start element."""
        if name == 'funkload':
            self.config['version'] = attrs['version']
            self.config['time'] = attrs['time']
        elif name == 'config':
            self.config[attrs['key']] = attrs['value']
            if attrs['key'] == 'duration':
                self.cycle_duration = attrs['value']
        elif name == 'header':
            # save header as extra response attribute
            headers = self.current_element[-2]['attrs'].setdefault(
                'headers', {})
            headers[str(attrs['name'])] = str(attrs['value'])
        self.current_element.append({'name': name, 'attrs': attrs})

    def handleEndElement(self, name):
        """Processing element."""
        element = self.current_element.pop()
        attrs = element['attrs']
        if name == 'testResult':
            cycle = attrs['cycle']
            stats = self.stats.setdefault(cycle, {'response_step': {}})
            stat = stats.setdefault(
                'test', TestStat(cycle, self.cycle_duration,
                                 attrs['cvus']))
            stat.add(attrs['result'], attrs['pages'], attrs.get('xmlrpc', 0),
                     attrs['redirects'], attrs['images'], attrs['links'],
                     attrs['connection_duration'], attrs.get('traceback'))
            stats['test'] = stat
        elif name == 'response':
            cycle = attrs['cycle']
            stats = self.stats.setdefault(cycle, {'response_step':{}})
            stat = stats.setdefault(
                'response', AllResponseStat(cycle, self.cycle_duration,
                                            attrs['cvus']))
            stat.add(attrs['time'], attrs['result'], attrs['duration'])
            stats['response'] = stat

            stat = stats.setdefault(
                'page', PageStat(cycle, self.cycle_duration, attrs['cvus']))
            stat.add(attrs['thread'], attrs['step'], attrs['time'],
                     attrs['result'], attrs['duration'], attrs['type'])
            stats['page'] = stat

            step = '%s.%s' % (attrs['step'], attrs['number'])
            stat = stats['response_step'].setdefault(
                step, ResponseStat(attrs['step'], attrs['number'],
                                   attrs['cvus']))
            stat.add(attrs['type'], attrs['result'], attrs['url'],
                     attrs['duration'], attrs.get('description'))
            stats['response_step'][step] = stat
            if attrs['result'] != 'Successful':
                result = str(attrs['result'])
                stats = self.error.setdefault(result, [])
                stats.append(ErrorStat(
                    attrs['cycle'], attrs['step'], attrs['number'],
                    attrs.get('code'), attrs.get('headers'),
                    attrs.get('body'), attrs.get('traceback')))
        elif name == 'monitor':
            host = attrs.get('host')
            stats = self.monitor.setdefault(host, [])
            stats.append(MonitorStat(attrs))
        elif name =='monitorconfig':
            host = attrs.get('host')
            config = self.monitorconfig.setdefault(host, {})
            config[attrs.get('key')]=attrs.get('value')


    def handleStartCdataSection(self):
        """Start recording cdata."""
        self.is_recording_cdata = True
        self.current_cdata = ''

    def handleEndCdataSection(self):
        """Save CDATA content into the parent element."""
        self.is_recording_cdata = False
        # assume CDATA is encapsulate in a container element
        name = self.current_element[-1]['name']
        self.current_element[-2]['attrs'][name] = self.current_cdata
        self.current_cdata = ''

    def handleCharacterData(self, data):
        """Extract cdata."""
        if self.is_recording_cdata:
            self.current_cdata += data



# ------------------------------------------------------------
# main
#
def main():
    """ReportBuilder main."""
    parser = OptionParser(USAGE, formatter=TitledHelpFormatter(),
                          version="FunkLoad %s" % get_version())
    parser.add_option("-H", "--html", action="store_true", default=False,
                      dest="html", help="Produce an html report.")
    parser.add_option("--org", action="store_true", default=False,
                      dest="org", help="Org-mode report.")
    parser.add_option("-P", "--with-percentiles", action="store_true",
                      default=True, dest="with_percentiles",
                      help=("Include percentiles in tables, use 10%, 50% and"
                            " 90% for charts, default option."))
    parser.add_option("--no-percentiles", action="store_false",
                      dest="with_percentiles",
                      help=("No percentiles in tables display min, "
                            "avg and max in charts."))
    cur_path = os.path.abspath(os.path.curdir)
    parser.add_option("-d", "--diff", action="store_true",
                      default=False, dest="diffreport",
                      help=("Create differential report."))
    parser.add_option("-t", "--trend", action="store_true",
                      default=False, dest="trendreport",
                      help=("Build a trend reprot."))
    parser.add_option("-o", "--output-directory", type="string",
                      dest="output_dir",
                      help="Parent directory to store reports, the directory"
                      "name of the report will be generated automatically.",
                      default=cur_path)
    parser.add_option("-r", "--report-directory", type="string",
                      dest="report_dir",
                      help="Directory name to store the report.",
                      default=None)
    parser.add_option("-T", "--apdex-T", type="float",
                      dest="apdex_t",
                      help="Apdex T constant in second, default is set to 1.5s. "
                      "Visit http://www.apdex.org/ for more information.",
                      default=Apdex.T)
    parser.add_option("-x", "--css", type="string",
                      dest="css_file",
                      help="Custom CSS file to use for the HTML reports",
                      default=None)
    parser.add_option("", "--skip-definitions", action="store_true",
                      default=False, dest="skip_definitions",
                      help="If True, will skip the definitions")
    parser.add_option("-q", "--quiet", action="store_true",
                      default=False, dest="quiet",
                      help=("Report no system messages when generating"
                            " html from rst."))

    options, args = parser.parse_args()
    if options.diffreport:
        if len(args) != 2:
            parser.error("incorrect number of arguments")
        trace("Creating diff report ... ")
        output_dir = options.output_dir
        html_path = RenderDiff(args[0], args[1], options,
                               css_file=options.css_file)
        trace("done: \n")
        trace("%s\n" % html_path)
    elif options.trendreport:
        if len(args) < 2:
            parser.error("incorrect number of arguments")
        trace("Creating trend report ... ")
        output_dir = options.output_dir
        html_path = RenderTrend(args, options, css_file=options.css_file)
        trace("done: \n")
        trace("%s\n" % html_path)
    else:
        if len(args) < 1:
            parser.error("incorrect number of arguments")
        if len(args) > 1:
            trace("Merging results files: ")
            f = NamedTemporaryFile(prefix='fl-mrg-', suffix='.xml')
            tmp_file = f.name
            f.close()
            MergeResultFiles(args, tmp_file)
            trace("Results merged in tmp file: %s\n" % os.path.abspath(tmp_file))
            args = [tmp_file]
        options.xml_file = args[0]
        Apdex.T = options.apdex_t
        xml_parser = FunkLoadXmlParser()
        xml_parser.parse(options.xml_file)
        if options.html:
            trace("Creating html report: ...")
            html_path = RenderHtml(xml_parser.config, xml_parser.stats,
                                   xml_parser.error, xml_parser.monitor,
                                   xml_parser.monitorconfig,
                                   options,
                                   css_file=options.css_file)()
            trace("done: \n")
            trace(html_path + "\n")
        elif options.org:
            from ReportRenderOrg import RenderOrg
            print unicode(RenderOrg(xml_parser.config, xml_parser.stats,
                                xml_parser.error, xml_parser.monitor,
                                xml_parser.monitorconfig, options)).encode("utf-8")
        else:
            print unicode(RenderRst(xml_parser.config, xml_parser.stats,
                                xml_parser.error, xml_parser.monitor,
                                xml_parser.monitorconfig, options)).encode("utf-8")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ReportRenderDiff
# (C) Copyright 2008 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Classes that render a differential report

$Id$
"""
import os
from ReportRenderRst import rst_title
from ReportRenderHtmlBase import RenderHtmlBase
from ReportRenderHtmlGnuPlot import gnuplot

def getReadableDiffReportName(a, b):
    """Return a readeable diff report name using 2 reports"""
    a = os.path.basename(a)
    b = os.path.basename(b)
    if a == b:
        return "diff_" + a + "_vs_idem"
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            break
    for i in range(i, 0, -1):
        # try to keep numbers
        if a[i] not in "_-0123456789":
            i += 1
            break

    r = b[:i] + "_" + b[i:] + "_vs_" + a[i:]
    if r.startswith('test_'):
        r = r[5:]
    r = r.replace('-_', '_')
    r = r.replace('_-', '_')
    r = r.replace('__', '_')
    return "diff_" + r

def getRPath(a, b):
    """Return a relative path of b from a."""
    a_path = a.split('/')
    b_path = b.split('/')
    for i in range(min(len(a_path), len(b_path))):
        if a_path[i] != b_path[i]:
            break
    return '../' * len(a_path[i:]) + '/'.join(b_path[i:])

class RenderDiff(RenderHtmlBase):
    """Differential report."""
    report_dir1 = None
    report_dir2 = None
    header = None
    sep = ', '
    data_file = None
    output_dir = None
    script_file = None

    def __init__(self, report_dir1, report_dir2, options, css_file=None):
        # Swap windows path separator backslashes for forward slashes
        # Windows accepts '/' but some file formats like rest treat the
        # backslash specially.
        self.report_dir1 = os.path.abspath(report_dir1).replace('\\', '/')
        self.report_dir2 = os.path.abspath(report_dir2).replace('\\', '/')
        self.options = options
        self.css_file = css_file
        self.quiet = options.quiet

    def generateReportDirectory(self, output_dir):
        """Generate a directory name for a report."""
        output_dir = os.path.abspath(output_dir)
        report_dir = os.path.join(output_dir, getReadableDiffReportName(
            self.report_dir1, self.report_dir2))
        if not os.access(report_dir, os.W_OK):
            os.mkdir(report_dir, 0775)
        return report_dir

    def createCharts(self):
        """Render stats."""
        self.createGnuplotData()
        self.createGnuplotScript()
        gnuplot(self.script_file)

    def createRstFile(self):
        """Create the ReST file."""
        rst_path = os.path.join(self.report_dir, 'index.rst')
        lines = []
        b1 = os.path.basename(self.report_dir1)
        b2 = os.path.basename(self.report_dir2)

        # Swap windows path separator backslashes for forward slashes
        b1_rpath = getRPath(self.report_dir.replace('\\', '/'),
                            os.path.join(self.report_dir1,
                                         'index.html').replace('\\', '/'))
        b2_rpath = getRPath(self.report_dir.replace('\\', '/'),
                            os.path.join(self.report_dir2,
                                         'index.html').replace('\\', '/'))
        if b1 == b2:
            b2 = b2 +"(2)"
        lines.append(rst_title("FunkLoad_ differential report", level=0))
        lines.append("")
        lines.append(".. sectnum::    :depth: 2")
        lines.append("")
        lines.append(rst_title("%s vs %s" % (b2, b1), level=1))
        lines.append(" * Reference bench report **B1**: `" +
                     b1 + " <" + b1_rpath + ">`_ [#]_")
        lines.append(" * Challenger bench report **B2**: `" +
                     b2 + " <" + b2_rpath + ">`_ [#]_")

        lines.append("")
        lines.append(rst_title("Requests", level=2))
        lines.append(" .. image:: rps_diff.png")
        lines.append(" .. image:: request.png")
        lines.append(rst_title("Pages", level=2))
        lines.append(" .. image:: spps_diff.png")

        escapeReportDir = lambda rd: rd.replace('\\', '/').replace('_', '\\_')
        lines.append(" .. [#] B1 path: " + escapeReportDir(self.report_dir1))
        lines.append(" .. [#] B2 path: " + escapeReportDir(self.report_dir2))

        lines.append(" .. _FunkLoad: http://funkload.nuxeo.org/")
        lines.append("")
        f = open(rst_path, 'w')
        f.write('\n'.join(lines))
        f.close()
        self.rst_path = rst_path

    def copyXmlResult(self):
        pass

    def __repr__(self):
        return self.render()

    def extract_stat(self, tag, report_dir):
        """Extract stat from the ReST index file."""
        lines = open(os.path.join(report_dir, "index.rst")).readlines()
        try:
            idx = lines.index("%s stats\n" % tag)
        except ValueError:
            print "ERROR tag %s not found in rst report %s" % (tag, report_dir)
            return []
        delim = 0
        ret =  []
        for line in lines[idx:]:
            if line.startswith(" ====="):
                delim += 1
                continue
            if delim == 1:
                self.header = line.strip().split()
            if delim < 2:
                continue
            if delim == 3:
                break
            ret.append([x.replace("%","") for x in line.strip().split()])
        return ret

    def createGnuplotData(self):
        """Render rst stat."""

        def output_stat(tag, rep):
            stat = self.extract_stat(tag, rep)
            text = []
            text.append('# ' + tag + " stat for: " + rep)
            text.append('# ' + ' '.join(self.header))
            for line in stat:
                text.append(' '.join(line))
            return '\n'.join(text)


        def output_stat_diff(tag, rep1, rep2):
            stat1 = self.extract_stat(tag, rep1)
            stat2 = self.extract_stat(tag, rep2)
            text = []
            text.append('# ' + tag + " stat for: " + rep1 + " and " + rep2)
            text.append('# ' + ' '.join(self.header) + ' ' +
                        ' '.join([x+ "-2" for x in self.header]))
            for s1 in stat1:
                for s2 in stat2:
                    if s1[0] == s2[0]:
                        text.append(' '.join(s1) + ' ' + ' '.join(s2))
                        break
                if s1[0] != s2[0]:
                    text.append(' '.join(s1))
            return '\n'.join(text)

        rep1 = self.report_dir1
        rep2 = self.report_dir2

        data_file = os.path.join(self.report_dir, 'diffbench.dat')
        self.data_file = data_file
        f = open(data_file, 'w')
        f.write('# ' + rep1 + ' vs ' + rep2 + '\n')
        for tag, rep in (('Page', rep1), ('Page', rep2),
                         ('Request', rep1), ('Request', rep2)):
            f.write(output_stat(tag, rep) + '\n\n\n')
        f.write(output_stat_diff('Page', rep1, rep2) + '\n\n\n')
        f.write(output_stat_diff('Request', rep1, rep2))
        f.close()


    def createGnuplotScript(self):
        """Build gnuplot script"""
        script_file = os.path.join(self.report_dir, 'script.gplot')
        self.script_file = script_file
        f = open(script_file, 'w')
        rep1 = self.report_dir1
        rep2 = self.report_dir2
        f.write('# ' + rep1 + ' vs ' + rep2 + '\n')

        f.write('''# COMMON SETTINGS
set grid  back
set xlabel "Concurrent Users"
set boxwidth 0.9 relative
set style fill solid 1

# SPPS
set output "spps_diff.png"
set terminal png size 640,380
set title "Successful Pages Per Second"
set ylabel "SPPS"
plot "diffbench.dat" i 4 u 1:4:19 w filledcurves above t "B2<B1", "" i 4 u 1:4:19 w filledcurves below t "B2>B1", "" i 4 u 1:4 w lines lw 2 t "B1", "" i 4 u 1:19 w lines lw 2 t "B2"

# RPS
set output "rps_diff.png"
set terminal png size 640,380
set multiplot title "Requests Per Second (Scalability)"
set title "Requests Per Second" offset 0, -2
set size 1, 0.67
set origin 0, 0.3
set ylabel ""
set format x ""
set xlabel ""
plot "diffbench.dat" i 5 u 1:4:19 w filledcurves above t "B2<B1", "" i 5 u 1:4:19 w filledcurves below t "B2>B1", "" i 5 u 1:4 w lines lw 2 t "B1", "" i 5 u 1:19 w lines lw 2 t "B2"

# % RPS
set title "RPS B2/B1 %"  offset 0, -2
set size 1, 0.33
set origin 0, 0
set format y "% g%%"
set format x "% g"
set xlabel "Concurrent Users"

plot "diffbench.dat" i 5 u 1:($19<$4?((($19*100)/$4) - 100): 0) w boxes notitle, "" i 5 u 1:($19>=$4?((($19*100)/$4)-100): 0) w boxes notitle
unset multiplot


# RESPONSE TIMES
set output "request.png"
set terminal png size 640,640
set multiplot title "Request Response time (Velocity)"

# AVG
set title "Average"  offset 0, -2
set size 0.5, 0.67
set origin 0, 0.30
set ylabel ""
set format y "% gs"
set xlabel ""
set format x ""
plot "diffbench.dat" i 5 u 1:25:10 w filledcurves above t "B2<B1", "" i 5 u 1:25:10 w filledcurves below t "B2>B1", "" i 5 u 1:10 w lines lw 2 t "B1", "" i 5 u 1:25 w lines lw 2 t "B2

# % AVG
set title "Average B1/B2 %"  offset 0, -2
set size 0.5, 0.31
set origin 0, 0
set format y "% g%%"
set format x "% g"
set xlabel "Concurrent Users"
plot "diffbench.dat" i 5 u 1:($25>$10?((($10*100)/$25) - 100): 0) w boxes notitle, "" i 5 u 1:($25<=$10?((($10*100)/$25) - 100): 0) w boxes notitle

# MEDIAN
set size 0.5, 0.31
set format y "% gs"
set xlabel ""
set format x ""

set title "Median"
set origin 0.5, 0.66
plot "diffbench.dat" i 5 u 1:28:13 w filledcurves above notitle, "" i 5 u 1:28:13 w filledcurves below notitle, "" i 5 u 1:13 w lines lw 2 notitle, "" i 5 u 1:28 w lines lw 2 notitle

# P90
set title "p90"
set origin 0.5, 0.33
plot "diffbench.dat" i 5 u 1:29:14 w filledcurves above notitle, "" i 5 u 1:29:14 w filledcurves below notitle, "" i 5 u 1:14 w lines lw 2 notitle, "" i 5 u 1:29 w lines lw 2 notitle

# MAX
set title "Max"
set origin 0.5, 0
set format x "% g"
set xlabel "Concurrent Users"
plot "diffbench.dat" i 5 u 1:26:11 w filledcurves above notitle, "" i 5 u 1:26:11 w filledcurves below notitle, "" i 5 u 1:11 w lines lw 2 notitle, "" i 5 u 1:26 w lines lw 2 notitle
unset multiplot
''')

        f.close()


########NEW FILE########
__FILENAME__ = ReportRenderHtml
# (C) Copyright 2008 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Choose the best html rendering

$Id: ReportRenderHtml.py 53544 2009-03-09 16:28:58Z tlazar $
"""

try:
    # 1/ gnuplot
    from ReportRenderHtmlGnuPlot import RenderHtmlGnuPlot as RenderHtml
except ImportError:
    # 2/ no charts
    from ReportRenderHtmlBase import RenderHtmlBase as RenderHtml

from ReportRenderHtmlGnuPlot import RenderHtmlGnuPlot as RenderHtml

########NEW FILE########
__FILENAME__ = ReportRenderHtmlBase
# (C) Copyright 2005-2011 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors:
#   Tom Lazar
#   Krzysztof A. Adamski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Html rendering

$Id$
"""
import os
from shutil import copyfile
from ReportRenderRst import RenderRst, rst_title


class RenderHtmlBase(RenderRst):
    """Render stats in html.

    Simply render stuff in ReST then ask docutils to build an html doc.
    """
    chart_size = (350, 250)
    big_chart_size = (640, 480)

    def __init__(self, config, stats, error, monitor, monitorconfig, options, css_file=None):
        RenderRst.__init__(self, config, stats, error, monitor, monitorconfig, options)
        self.css_file = css_file
        self.quiet = options.quiet
        self.report_dir = self.css_path = self.rst_path = self.html_path = None

    def getChartSize(self, cvus):
        """Compute the right size lenght depending on the number of cvus."""
        size = list(self.chart_size)
        len_cvus = len(cvus)
        chart_size = self.chart_size
        big_chart_size = self.big_chart_size
        if ((len_cvus * 50) > chart_size[0]):
            if (len_cvus * 50 < big_chart_size):
                return ((len_cvus * 50), big_chart_size[1])
            return big_chart_size
        return chart_size

    def generateReportDirectory(self, output_dir):
        """Generate a directory name for a report."""
        config = self.config
        stamp = config['time'][:19].replace(':', '')
        stamp = stamp.replace('-', '')
        if config.get('label', None) is None:
            report_dir = os.path.join(output_dir, '%s-%s' % (
                config['id'], stamp))
        else:
            report_dir = os.path.join(output_dir, '%s-%s-%s' % (
                config['id'], stamp, config.get('label')))
        return report_dir

    def prepareReportDirectory(self):
        """Create a report directory."""
        if self.options.report_dir:
            report_dir = os.path.abspath(self.options.report_dir)
        else:
            # init output dir
            output_dir = os.path.abspath(self.options.output_dir)
            if not os.access(output_dir, os.W_OK):
                os.mkdir(output_dir, 0775)
            # init report dir
            report_dir = self.generateReportDirectory(output_dir)
        if not os.access(report_dir, os.W_OK):
            os.mkdir(report_dir, 0775)
        self.report_dir = report_dir

    def createRstFile(self):
        """Create the ReST file."""
        rst_path = os.path.join(self.report_dir, 'index.rst')
        f = open(rst_path, 'w')
        f.write(unicode(self).encode("utf-8"))
        f.close()
        self.rst_path = rst_path

    def copyCss(self):
        """Copy the css to the report dir."""
        css_file = self.css_file
        if css_file is not None:
            css_filename = os.path.split(css_file)[-1]
            css_dest_path = os.path.join(self.report_dir, css_filename)
            copyfile(css_file, css_dest_path)
        else:
            # use the one in our package_data
            from pkg_resources import resource_string
            css_content = resource_string('funkload', 'data/funkload.css')
            css_dest_path = os.path.join(self.report_dir, 'funkload.css')
            f = open(css_dest_path, 'w')
            f.write(css_content)
            f.close()
        self.css_path = css_dest_path

    def copyXmlResult(self):
        """Make a copy of the xml result."""
        xml_src_path = self.options.xml_file
        xml_dest_path = os.path.join(self.report_dir, 'funkload.xml')
        copyfile(xml_src_path, xml_dest_path)

    def generateHtml(self):
        """Ask docutils to convert our rst file into html."""
        from docutils.core import publish_cmdline
        html_path = os.path.join(self.report_dir, 'index.html')
        cmdline = []
        if self.quiet:
            cmdline.append('-q')
        cmdline.extend(['-t', '--stylesheet-path', self.css_path,
                        self.rst_path, html_path])
        publish_cmdline(writer_name='html', argv=cmdline)
        self.html_path = html_path

    def render(self):
        """Create the html report."""
        self.prepareReportDirectory()
        self.createRstFile()
        self.copyCss()
        try:
            self.generateHtml()
            pass
        except ImportError:
            print "WARNING docutils not found, no html output."
            return ''
        self.createCharts()
        self.copyXmlResult()
        return os.path.abspath(self.html_path)

    __call__ = render


    def createCharts(self):
        """Create all charts."""
        self.createTestChart()
        self.createPageChart()
        self.createAllResponseChart()
        for step_name in self.steps:
            self.createResponseChart(step_name)

    # monitoring charts
    def createMonitorCharts(self):
        """Create all montirored server charts."""
        if not self.monitor or not self.with_chart:
            return
        self.append(rst_title("Monitored hosts", 2))
        charts={}
        for host in self.monitor.keys():
            charts[host]=self.createMonitorChart(host)
        return charts

    def createTestChart(self):
        """Create the test chart."""

    def createPageChart(self):
        """Create the page chart."""

    def createAllResponseChart(self):
        """Create global responses chart."""

    def createResponseChart(self, step):
        """Create responses chart."""

    def createMonitorChart(self, host):
        """Create monitrored server charts."""




########NEW FILE########
__FILENAME__ = ReportRenderHtmlGnuPlot
# (C) Copyright 2009 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors: Kelvin Ward
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Render chart using gnuplot >= 4.2

$Id$
"""

import os
import sys
import re
from commands import getstatusoutput
from apdex import Apdex
from ReportRenderRst import rst_title
from ReportRenderHtmlBase import RenderHtmlBase
from datetime import datetime
from MonitorPlugins import MonitorPlugins
from MonitorPluginsDefault import MonitorCPU, MonitorMemFree, MonitorNetwork, MonitorCUs

def gnuplot(script_path):
    """Execute a gnuplot script."""
    path = os.path.dirname(os.path.abspath(script_path))
    if sys.platform.lower().startswith('win'):
        # commands module doesn't work on win and gnuplot is named
        # wgnuplot
        ret = os.system('cd "' + path + '" && wgnuplot "' +
                        os.path.abspath(script_path) + '"')
        if ret != 0:
            raise RuntimeError("Failed to run wgnuplot cmd on " +
                               os.path.abspath(script_path))

    else:
        cmd = 'cd "' + path + '"; gnuplot "' + os.path.abspath(script_path) + '"'
        ret, output = getstatusoutput(cmd)
        if ret != 0:
            raise RuntimeError("Failed to run gnuplot cmd: " + cmd +
                               "\n" + str(output))

def gnuplot_scriptpath(base, filename):
    """Return a file path string from the join of base and file name for use
    inside a gnuplot script.

    Backslashes (the win os separator) are replaced with forward
    slashes. This is done because gnuplot scripts interpret backslashes
    specially even in path elements.
    """
    return os.path.join(base, filename).replace("\\", "/")

class FakeMonitorConfig:
    def __init__(self, name):
        self.name = name

class RenderHtmlGnuPlot(RenderHtmlBase):
    """Render stats in html using gnuplot

    Simply render stuff in ReST then ask docutils to build an html doc.
    """
    chart_size = (640, 540)
    #big_chart_size = (640, 480)
    ticpattern = re.compile('(\:\d+)\ ')

    def getChartSizeTmp(self, cvus):
        """Override for gnuplot format"""
        return str(self.chart_size[0]) + ',' + str(self.chart_size[1])

    def getXRange(self):
        """Return the max CVUs range."""
        maxCycle = self.config['cycles'].split(',')[-1]
        maxCycle = str(maxCycle[:-1].strip())
        if maxCycle.startswith("["):
            maxCycle = maxCycle[1:]
        return "[0:" + str(int(maxCycle) + 1) + "]"

    def useXTicLabels(self):
        """Guess if we need to use labels for x axis or number."""
        cycles = self.config['cycles'][1:-1].split(',')
        if len(cycles) <= 1:
            # single cycle
            return True
        if len(cycles) != len(set(cycles)):
            # duplicates cycles
            return True
        cycles = [int(i) for i in cycles]
        for i, v in enumerate(cycles[1:]):
            # unordered cycles
            if cycles[i] > v:
                return True
        return False

    def fixXLabels(self, lines):
        """Fix gnuplot script if CUs are not ordered."""
        if not self.useXTicLabels():
            return lines
        # remove xrange line
        out = lines.replace('set xrange', '#set xrange')
        # rewrite plot using xticlabels
        out = out.replace(' 1:', ' :')
        out = self.ticpattern.sub(r'\1:xticlabels(1) ', out)
        return out

    def createTestChart(self):
        """Create the test chart."""
        image_path = gnuplot_scriptpath(self.report_dir, 'tests.png')
        gplot_path = str(os.path.join(self.report_dir, 'tests.gplot'))
        data_path  = gnuplot_scriptpath(self.report_dir, 'tests.data')
        stats = self.stats
        # data
        lines = ["CUs STPS ERROR"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle].has_key('test'):
                continue
            values = []
            test = stats[cycle]['test']
            values.append(str(test.cvus))
            cvus.append(str(test.cvus))
            values.append(str(test.tps))
            error = test.error_percent
            if error:
                has_error = True
            values.append(str(error))
            lines.append(' '.join(values))
        if len(lines) == 1:
            # No tests finished during the cycle
            return
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = ['set output "' + image_path +'"']
        lines.append('set title "Successful Tests Per Second"')
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Test/s"')
        lines.append('set grid back')
        lines.append('set xrange ' + self.getXRange())

        if not has_error:
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "STPS"' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "STPS"' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set ytics 20')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            lines.append('set yrange [0:100]')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)
        return

    def appendDelays(self, delay, delay_low, delay_high, stats):
        """ Show percentiles or min, avg and max in chart. """
        if self.options.with_percentiles:
            delay.append(stats.percentiles.perc50)
            delay_low.append(stats.percentiles.perc10)
            delay_high.append(stats.percentiles.perc90)
        else:
            delay.append(stats.avg)
            delay_low.append(stats.min)
            delay_high.append(stats.max)


    def createPageChart(self):
        """Create the page chart."""
        image_path = gnuplot_scriptpath(self.report_dir, 'pages_spps.png')
        image2_path = gnuplot_scriptpath(self.report_dir, 'pages.png')
        gplot_path = str(os.path.join(self.report_dir, 'pages.gplot'))
        data_path = gnuplot_scriptpath(self.report_dir, 'pages.data')
        stats = self.stats
        # data
        lines = ["CUs SPPS ERROR MIN AVG MAX P10 P50 P90 P95 APDEX E G F P U"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle].has_key('page'):
                continue
            values = []
            page = stats[cycle]['page']
            values.append(str(page.cvus))
            cvus.append(str(page.cvus))
            values.append(str(page.rps))
            error = page.error_percent
            if error:
                has_error = True
            values.append(str(error))
            values.append(str(page.min))
            values.append(str(page.avg))
            values.append(str(page.max))
            values.append(str(page.percentiles.perc10))
            values.append(str(page.percentiles.perc50))
            values.append(str(page.percentiles.perc90))
            values.append(str(page.percentiles.perc95))
            score = page.apdex_score
            values.append(str(score))

            apdex = ['0', '0', '0', '0', '0']
            score_cls = Apdex.get_score_class(score)
            score_classes = Apdex.score_classes[:] #copy
            #flip from worst-to-best to best-to-worst
            score_classes.reverse()
            index = score_classes.index(score_cls)
            apdex[index] = str(score)

            values = values + apdex
            lines.append(' '.join(values))
        if len(lines) == 1:
            # No pages finished during a cycle
            return
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = ['set output "' + image_path +'"']
        lines.append('set title "Successful Pages Per Second"')
        lines.append('set ylabel "Pages Per Second"')
        lines.append('set grid back')
        lines.append('set xrange ' + self.getXRange())
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        lines.append('set format x ""')
        lines.append('set multiplot')
        lines.append('unset title')
        lines.append('unset xlabel')
        lines.append('set bmargin 0')
        lines.append('set lmargin 8')
        lines.append('set rmargin 9.5')
        lines.append('set key inside top')
        if has_error:
            lines.append('set size 1, 0.4')
            lines.append('set origin 0, 0.6')
        else:
            lines.append('set size 1, 0.6')
            lines.append('set origin 0, 0.4')
        lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "SPPS"' % data_path)
        # apdex
        lines.append('set boxwidth 0.8')
        lines.append('set style fill solid .7')
        lines.append('set ylabel "Apdex %.1f" ' % Apdex.T)
        lines.append('set yrange [0:1]')
        lines.append('set key outside top')
        if has_error:
            lines.append('set origin 0.0, 0.3')
            lines.append('set size 1.0, 0.3')
        else:
            lines.append('set size 1.0, 0.4')
            lines.append('set bmargin 3')
            lines.append('set format x "% g"')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set origin 0.0, 0.0')

        lines.append('plot "%s" u 1:12 w boxes lw 2 lt rgb "#99CDFF" t "E", "" u 1:13 w boxes lw 2 lt rgb "#00FF01" t "G", "" u 1:14 w boxes lw 2 lt rgb "#FFFF00" t "F", "" u 1:15 w boxes lw 2 lt rgb "#FF7C81" t "P", "" u 1:16 w boxes lw 2 lt rgb "#C0C0C0" t "U"' % data_path)
        lines.append('unset boxwidth')
        lines.append('set key inside top')
        if has_error:
            lines.append('set bmargin 3')
            lines.append('set format x "% g"')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set origin 0.0, 0.0')
            lines.append('set size 1.0, 0.3')
            lines.append('set ylabel "% errors"')
            lines.append('set yrange [0:100]')
            lines.append('plot "%s" u 1:3 w boxes lt 1 lw 2 t "%% Errors"' % data_path)

        lines.append('unset yrange')
        lines.append('set autoscale y')
        lines.append('unset multiplot')
        lines.append('set size 1.0, 1.0')
        lines.append('unset rmargin')
        lines.append('set output "%s"' % image2_path)
        lines.append('set title "Pages Response time"')
        lines.append('set ylabel "Duration (s)"')
        lines.append('set bars 5.0')
        lines.append('set style fill solid .25')
        lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)

    def createRPSTimeChart(self):
        """Create a RPS chart where X-axis represent the time in seconds."""
        img_path = gnuplot_scriptpath(self.report_dir, 'time_rps.png')
        plot_path = gnuplot_scriptpath(self.report_dir, 'time_rps.gplot')
        
        stats = self.stats

        start_timeline = sys.maxint
        end_timeline = -1
        max_rps = 0
        min_rps = 0
        
        for cycle in self.cycles:
            dpath = gnuplot_scriptpath(self.report_dir,
                                       'time_rps-{0}.data'.format(cycle))
            f = open(dpath, 'w')
            f.write('Timeline RPS\n')

            try:
                st = stats[cycle]['response']
                for k in sorted(st.per_second.iterkeys()):
                    if k < start_timeline:
                        start_timeline = k
                    if k > end_timeline:
                        end_timeline = k

                    if st.per_second[k] > max_rps:
                        max_rps = st.per_second[k]
                        
                    f.write('{0} {1}\n'.format(k, st.per_second[k]))
            except Exception as e:
                print "Exception: {0}".format(e)
            finally:
                f.close
        #print "max rps: {0}".format(max_rps)
        #print "time range: {0}-{1}".format(start_timeline, end_timeline)

        max_rps = int(max_rps * 1.25)

        f = open(plot_path, "w")

        lines = []
        lines.append('set output "{0}"'.format(img_path))
        lines.append('set title "Request Per Second over time"')
        lines.append('set xlabel "Time line"')
        lines.append('set xdata time')
        lines.append('set timefmt "%s"')
        lines.append('set format x "%H:%M"')
        lines.append('set ylabel "RPS"')
        lines.append('set grid')
        #lines.append('set xrange [{0}:{1}]'.format(0, end_timeline - start_timeline))
        lines.append('set yrange [{0}:{1}]'.format(min_rps, max_rps))
        # I don't know why self.getChartSizeTmp() accept cvus which is not used currently.
        cvus = []
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))

        plot_line = 'plot '
        colors = [
            # This RGB value used for the line color for each cycle.
            # TODO: use more pretty color?
            "000000",
            "0000FF",
            "00FA9A",
            "191970",
            "8B008B",
            "FF00FF",
            "FFD700",
            "0000CD",
            "00BFFF",
            "00FF00",
            "7FFF00",
            "FF0000",
            "FF8C00",
                   ];
        for i, cycle in enumerate(self.cycles):
            if i != 0:
                plot_line += ', \\\n'
            dpath = gnuplot_scriptpath(self.report_dir,
                                       'time_rps-{0}.data'.format(cycle))
            #lines.append('set size 1,1\n')
            #lines.append('set origin 0,0\n')
            #plot_line += '"' + dpath + '" u ($1 - {0}):($2)'.format(start_timeline)
            plot_line += '"' + dpath + '" u ($1):($2)'
            plot_line += ' w linespoints smooth sbezier lw 1 lt 2 lc ' + \
                         'rgbcolor "#696969" notitle'
            plot_line += ', \\\n'
            #plot_line += '"' + dpath + '" u ($1 - {0}):($2)'.format(start_timeline)
            plot_line += '"' + dpath + '" u ($1):($2)'
            plot_line += ' w linespoints lw 1 lt 2 lc ' + \
                         'rgbcolor "#{0}" t "{1} CUs"'.format(colors[i % len(colors)],
                                                                     stats[cycle]['response'].cvus)
        lines.append(plot_line)
        #lines.append('unset multiplot\n')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(plot_path)
        return

    def createAllResponseChart(self):
        """Create global responses chart."""
        self.createRPSTimeChart()
        
        image_path = gnuplot_scriptpath(self.report_dir, 'requests_rps.png')
        image2_path = gnuplot_scriptpath(self.report_dir, 'requests.png')
        gplot_path = str(os.path.join(self.report_dir, 'requests.gplot'))
        data_path = gnuplot_scriptpath(self.report_dir, 'requests.data')
        stats = self.stats
        # data
        lines = ["CUs RPS ERROR MIN AVG MAX P10 P50 P90 P95 APDEX"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle].has_key('response'):
                continue
            values = []
            resp = stats[cycle]['response']
            values.append(str(resp.cvus))
            cvus.append(str(resp.cvus))
            values.append(str(resp.rps))
            error = resp.error_percent
            if error:
                has_error = True
            values.append(str(error))
            values.append(str(resp.min))
            values.append(str(resp.avg))
            values.append(str(resp.max))
            values.append(str(resp.percentiles.perc10))
            values.append(str(resp.percentiles.perc50))
            values.append(str(resp.percentiles.perc90))
            values.append(str(resp.percentiles.perc95))
            values.append(str(resp.apdex_score))
            lines.append(' '.join(values))
        if len(lines) == 1:
            # No result during a cycle
            return
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = ['set output "' + image_path +'"']
        lines.append('set title "Requests Per Second"')
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Requests Per Second"')
        lines.append('set grid')
        lines.append('set xrange ' + self.getXRange())
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        if not has_error:
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "RPS"' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:2 w linespoints lw 2 lt 2 t "RPS"' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            #lines.append('set yrange [0:100]')
            #lines.append('set ytics 20')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
            lines.append('set size 1.0, 1.0')
        lines.append('set output "%s"' % image2_path)
        lines.append('set title "Requests Response time"')
        lines.append('set ylabel "Duration (s)"')
        lines.append('set bars 5.0')
        lines.append('set grid back')
        lines.append('set style fill solid .25')
        lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)

        return


    def createResponseChart(self, step):
        """Create responses chart."""
        image_path = gnuplot_scriptpath(self.report_dir,
                                        'request_%s.png' % step)
        gplot_path = str(os.path.join(self.report_dir,
                                      'request_%s.gplot' % step))
        data_path = gnuplot_scriptpath(self.report_dir,
                                       'request_%s.data' % step)
        stats = self.stats
        # data
        lines = ["CUs STEP ERROR MIN AVG MAX P10 P50 P90 P95 APDEX"]
        cvus = []
        has_error = False
        for cycle in self.cycles:
            if not stats[cycle]['response_step'].has_key(step):
                continue
            values = []
            resp = stats[cycle]['response_step'].get(step)
            values.append(str(resp.cvus))
            cvus.append(str(resp.cvus))
            values.append(str(step))
            error = resp.error_percent
            if error:
                has_error = True
            values.append(str(error))
            values.append(str(resp.min))
            values.append(str(resp.avg))
            values.append(str(resp.max))
            values.append(str(resp.percentiles.perc10))
            values.append(str(resp.percentiles.perc50))
            values.append(str(resp.percentiles.perc90))
            values.append(str(resp.percentiles.perc95))
            values.append(str(resp.apdex_score))
            lines.append(' '.join(values))
        if len(lines) == 1:
            # No result during a cycle
            return
        f = open(data_path, 'w')
        f.write('\n'.join(lines) + '\n')
        f.close()
        # script
        lines = []
        lines.append('set output "%s"' % image_path)
        lines.append('set terminal png size ' + self.getChartSizeTmp(cvus))
        lines.append('set grid')
        lines.append('set bars 5.0')
        lines.append('set title "Request %s Response time"' % step)
        lines.append('set xlabel "Concurrent Users"')
        lines.append('set ylabel "Duration (s)"')
        lines.append('set grid back')
        lines.append('set style fill solid .25')
        lines.append('set xrange ' + self.getXRange())
        if not has_error:
            lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
        else:
            lines.append('set format x ""')
            lines.append('set multiplot')
            lines.append('unset title')
            lines.append('unset xlabel')
            lines.append('set size 1, 0.7')
            lines.append('set origin 0, 0.3')
            lines.append('set lmargin 5')
            lines.append('set bmargin 0')
            lines.append('plot "%s" u 1:8:8:10:9 t "med/p90/p95" w candlesticks lt 1 lw 1 whiskerbars 0.5, "" u 1:7:4:8:8 w candlesticks lt 2 lw 1 t "min/p10/med" whiskerbars 0.5, "" u 1:5 t "avg" w lines lt 3 lw 2' % data_path)
            lines.append('set format x "% g"')
            lines.append('set bmargin 3')
            lines.append('set autoscale y')
            lines.append('set style fill solid .25')
            lines.append('set size 1.0, 0.3')
            lines.append('set xlabel "Concurrent Users"')
            lines.append('set ylabel "% errors"')
            lines.append('set origin 0.0, 0.0')
            #lines.append('set yrange [0:100]')
            #lines.append('set ytics 20')
            lines.append('plot "%s" u 1:3 w linespoints lt 1 lw 2 t "%% Errors"' % data_path)
            lines.append('unset multiplot')
            lines.append('set size 1.0, 1.0')
        f = open(gplot_path, 'w')
        lines = self.fixXLabels('\n'.join(lines) + '\n')
        f.write(lines)
        f.close()
        gnuplot(gplot_path)
        return

    def createMonitorChart(self, host):
        """Create monitrored server charts."""
        stats = self.monitor[host]
        times = []
        cvus_list = []
        for stat in stats:
            test, cycle, cvus = stat.key.split(':')
            stat.cvus=cvus
            date = datetime.fromtimestamp(float(stat.time))
            times.append(date.strftime("%H:%M:%S"))
            #times.append(int(float(stat.time))) # - time_start))
            cvus_list.append(cvus)

        Plugins = MonitorPlugins()
        Plugins.registerPlugins()
        Plugins.configure(self.getMonitorConfig(host))

        charts=[]
        for plugin in Plugins.MONITORS.values():
            image_prefix = gnuplot_scriptpath(self.report_dir, '%s_%s' % (host, plugin.name))
            data_prefix = gnuplot_scriptpath(self.report_dir, '%s_%s' % (host, plugin.name))
            gplot_path = str(os.path.join(self.report_dir, '%s_%s.gplot' % (host, plugin.name)))
            r=plugin.gnuplot(times, host, image_prefix, data_prefix, gplot_path, self.chart_size, stats)
            if r!=None:
                gnuplot(gplot_path)
                charts.extend(r)
        return charts

########NEW FILE########
__FILENAME__ = ReportRenderOrg
# (C) Copyright 2011 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Classes that render statistics in emacs org-mode format.
"""
import re
from ReportRenderRst import RenderRst
from ReportRenderRst import BaseRst
import ReportRenderRst
from MonitorPlugins import MonitorPlugins

FL_SITE = "http://funkload.nuxeo.org"


def org_title(title, level=1, newpage=True):
    """Return an org section."""
    org = []
    if newpage:
        org.append("")
        org.append("")
        org.append("#+BEGIN_LaTeX")
        org.append("\\newpage")
        org.append('#+END_LaTeX')
    org.append('*' * (level - 1) + ' ' + title + '\n')
    return '\n'.join(org)


def org_image(self):
    org = ["#+BEGIN_LaTeX"]
    org.append('\\begin{center}')
    for image_name in self.image_names:
        org.append("\includegraphics[scale=0.5]{{./%s}.png}" % image_name)
    org.append('\\end{center}')
    org.append('#+END_LaTeX')
    return '\n'.join(org) + '\n'


def org_header(self, with_chart=False):
    headers = self.headers[:]
    if self.with_percentiles:
        self._attach_percentiles_header(headers)
    org = [self.render_image()]
    org.append("#+BEGIN_LaTeX")
    org.append("\\tiny")
    org.append('#+END_LaTeX')
    org.append(' |' + '|'.join(headers) + '|\n |-')
    return '\n'.join(org)


def org_footer(self):
    org = [' |-']
    org.append("#+BEGIN_LaTeX")
    org.append("\\normalsize")
    org.append('#+END_LaTeX')
    return '\n'.join(org)

ReportRenderRst.rst_title = org_title
ReportRenderRst.LI = '-'
BaseRst.render_header = org_header
BaseRst.render_footer = org_footer
BaseRst.render_image = org_image
BaseRst.sep = '|'


class RenderOrg(RenderRst):
    """Render stats in emacs org-mode format."""
    # number of slowest requests to display
    slowest_items = 5
    with_chart = True

    def __init__(self, config, stats, error, monitor, monitorconfig, options):
        options.html = True
        RenderRst.__init__(self, config, stats, error, monitor, monitorconfig, options)

    def renderHeader(self):
        config = self.config
        self.append('#    -*- mode: org -*-')
        self.append('#+TITLE: FunkLoad bench report')
        self.append('#+DATE: ' + self.date)
        self.append('''#+STYLE: <link rel="stylesheet" type="text/css" href="eon.css" />
#+LaTeX_CLASS: koma-article
#+LaTeX_CLASS_OPTIONS: [a4paper,landscape]
#+LATEX_HEADER: \usepackage[utf8]{inputenc}
#+LATEX_HEADER: \usepackage[en]{babel}
#+LATEX_HEADER: \usepackage{fullpage}
#+LATEX_HEADER: \usepackage[hyperref,x11names]{xcolor}
#+LATEX_HEADER: \usepackage[colorlinks=true,urlcolor=SteelBlue4,linkcolor=Firebrick4]{hyperref}
#+LATEX_HEADER: \usepackage{graphicx}
#+LATEX_HEADER: \usepackage[T1]{fontenc}''')

        description = [config['class_description']]
        description += ["Bench result of ``%s.%s``: " % (config['class'],
                                                       config['method'])]
        description += [config['description']]

        self.append('#+TEXT: Bench result of =%s.%s=: %s' % (
                config['class'], config['method'], ' '.join(description)))
        self.append('#+OPTIONS: toc:1')
        self.append('')

    def renderMonitor(self, host, charts):
        """Render a monitored host."""
        description = self.config.get(host, '')
        self.append(org_title("%s: %s" % (host, description), 3))
        for chart in charts:
            self.append('#+BEGIN_LaTeX')
            self.append('\\begin{center}')
            self.append("\includegraphics[scale=0.5]{{./%s}.png}" % chart[1])
            self.append('\\end{center}')
            self.append('#+END_LaTeX')

    def renderHook(self):
        self.rst = [line.replace('``', '=') for line in self.rst]
        lapdex = "Apdex_{%s}" % str(self.options.apdex_t)
        kv = re.compile("^(\ *\- [^\:]*)\:(.*)")
        bold = re.compile("\*\*([^\*]+)\*\*")
        link = re.compile("\`([^\<]+)\<([^\>]+)\>\`\_")
        ret = []
        for line in self.rst:
            line = re.sub(kv, lambda m: "%s :: %s\n\n" % (
                    m.group(1), m.group(2)), line)
            line = re.sub(bold, lambda m: "*%s*" % (m.group(1)),
                          line)
            line = re.sub(link, lambda m: "[[%s][%s]]" % (m.group(2),
                                                          m.group(1).strip()),
                          line)
            line = line.replace('|APDEXT|', lapdex)
            line = line.replace('Apdex*', lapdex)
            line = line.replace('Apdex T', 'Apdex_{T}')
            line = line.replace('FunkLoad_',
                                '[[%s][FunkLoad]]' % FL_SITE)
            ret.append(line)
        self.rst = ret

    def createMonitorCharts(self):
        """Create all montirored server charts."""
        if not self.monitor or not self.with_chart:
            return
        self.append(org_title("Monitored hosts", 2))
        charts = {}
        for host in self.monitor.keys():
            charts[host] = self.createMonitorChart(host)
        return charts

    def createMonitorChart(self, host):
        """Create monitrored server charts."""
        charts = []
        Plugins = MonitorPlugins()
        Plugins.registerPlugins()
        Plugins.configure(self.getMonitorConfig(host))

        for plugin in Plugins.MONITORS.values():
            image_path = ('%s_%s' % (host, plugin.name)).replace("\\", "/")
            charts.append((plugin.name, image_path))
        return charts

########NEW FILE########
__FILENAME__ = ReportRenderRst
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Classes that render statistics.

$Id$
"""
import os
from utils import get_version
from apdex import Apdex
from MonitorPluginsDefault import MonitorCPU, MonitorMemFree, MonitorNetwork, MonitorCUs

LI = '*'
# ------------------------------------------------------------
# ReST rendering
#
def rst_title(title, level=1, newpage=True):
    """Return a rst title."""
    rst_level = ['=', '=', '-', '~']
    if level == 0:
        rst = [rst_level[level] * len(title)]
    else:
        rst = ['']
    rst.append(title)
    rst.append(rst_level[level] * len(title))
    rst.append('')
    return '\n'.join(rst)

def dumb_pluralize(num, word):
    #Doesn't follow all English rules, but sufficent for our purpose
    return ' %s %s' % (num, word + ['s',''][num==1])



class BaseRst:
    """Base class for ReST renderer."""
    fmt_int = "%18d"
    fmt_float = "%18.3f"
    fmt_str = "%18s"
    fmt_percent = "%16.2f%%"
    fmt_deco = "=================="
    sep = " "
    headers = []
    indent = 0
    image_names = []
    with_percentiles = False
    with_apdex = False

    def __init__(self, stats):
        self.stats = stats

    def __repr__(self):
        """Render stats."""
        ret = ['']
        ret.append(self.render_header())
        ret.append(self.render_stat())
        ret.append(self.render_footer())
        return '\n'.join(ret)

    def render_images(self):
        """Render images link."""
        indent = ' ' * self.indent
        rst = []
        for image_name in self.image_names:
            rst.append(indent + " .. image:: %s.png" % image_name)
        rst.append('')
        return '\n'.join(rst)

    def render_header(self, with_chart=False):
        """Render rst header."""
        headers = self.headers[:]
        if self.with_percentiles:
            self._attach_percentiles_header(headers)
        deco = ' ' + " ".join([self.fmt_deco] * len(headers))
        header = " " + " ".join([ "%18s" % h for h in headers ])
        indent = ' ' * self.indent
        ret = []
        if with_chart:
            ret.append(self.render_images())
        ret.append(indent + deco)
        ret.append(indent + header)
        ret.append(indent + deco)
        return '\n'.join(ret)

    def _attach_percentiles_header(self, headers):
        """ Attach percentile headers. """
        headers.extend(
            ["P10", "MED", "P90", "P95"])

    def _attach_percentiles(self, ret):
        """ Attach percentiles, if this is wanted. """
        percentiles = self.stats.percentiles
        fmt = self.fmt_float
        ret.extend([
            fmt % percentiles.perc10,
            fmt % percentiles.perc50,
            fmt % percentiles.perc90,
            fmt % percentiles.perc95
        ])

    def render_footer(self):
        """Render rst footer."""
        headers = self.headers[:]
        if self.with_percentiles:
            self._attach_percentiles_header(headers)
        deco = " ".join([self.fmt_deco] * len(headers))
        footer =  ' ' * (self.indent + 1) + deco
        footer +=  '\n\n'
        if self.with_apdex:
            footer +=  ' ' * (self.indent + 1) + "\* Apdex |APDEXT|"
        return footer

    def render_stat(self):
        """Render rst stat."""
        raise NotImplemented


class AllResponseRst(BaseRst):
    """AllResponseStat rendering."""
    headers = [ "CUs", "Apdex*", "Rating*", "RPS", "maxRPS", "TOTAL", "SUCCESS","ERROR",
        "MIN", "AVG", "MAX"]
    image_names = ['requests_rps', 'requests', 'time_rps']
    with_apdex = True

    def render_stat(self):
        """Render rst stat."""
        ret = [' ' * self.indent]
        stats = self.stats
        stats.finalize()
        ret.append(self.fmt_int % stats.cvus)
        if self.with_apdex:
            ret.append(self.fmt_float % stats.apdex_score)
            ret.append(self.fmt_str % Apdex.get_label(stats.apdex_score))
        ret.append(self.fmt_float % stats.rps)
        ret.append(self.fmt_float % stats.rps_max)
        ret.append(self.fmt_int % stats.count)
        ret.append(self.fmt_int % stats.success)
        ret.append(self.fmt_percent % stats.error_percent)
        ret.append(self.fmt_float % stats.min)
        ret.append(self.fmt_float % stats.avg)
        ret.append(self.fmt_float % stats.max)
        if self.with_percentiles:
            self._attach_percentiles(ret)
        ret = self.sep.join(ret)
        return ret


class PageRst(AllResponseRst):
    """Page rendering."""
    headers = ["CUs", "Apdex*", "Rating", "SPPS", "maxSPPS", "TOTAL", "SUCCESS",
              "ERROR", "MIN", "AVG", "MAX"]
    image_names = ['pages_spps', 'pages']
    with_apdex = True

class ResponseRst(BaseRst):
    """Response rendering."""
    headers = ["CUs", "Apdex*", "Rating", "TOTAL", "SUCCESS", "ERROR", "MIN", "AVG", "MAX"]
    indent = 4
    image_names = ['request_']
    with_apdex = True

    def __init__(self, stats):
        BaseRst.__init__(self, stats)
        # XXX quick fix for #1017
        self.image_names = [name + str(stats.step) + '.' + str(stats.number)
                            for name in self.image_names]

    def render_stat(self):
        """Render rst stat."""
        stats = self.stats
        stats.finalize()
        ret = [' ' * self.indent]
        ret.append(self.fmt_int % stats.cvus)
        ret.append(self.fmt_float % stats.apdex_score)
        ret.append(self.fmt_str % Apdex.get_label(stats.apdex_score))
        ret.append(self.fmt_int % stats.count)
        ret.append(self.fmt_int % stats.success)
        ret.append(self.fmt_percent % stats.error_percent)
        ret.append(self.fmt_float % stats.min)
        ret.append(self.fmt_float % stats.avg)
        ret.append(self.fmt_float % stats.max)
        if self.with_percentiles:
            self._attach_percentiles(ret)
        ret = self.sep.join(ret)
        return ret


class TestRst(BaseRst):
    """Test Rendering."""
    headers = ["CUs", "STPS", "TOTAL", "SUCCESS", "ERROR"]
    image_names = ['tests']
    with_percentiles = False

    def render_stat(self):
        """Render rst stat."""
        stats = self.stats
        stats.finalize()
        ret = [' ' * self.indent]
        ret.append(self.fmt_int % stats.cvus)
        ret.append(self.fmt_float % stats.tps)
        ret.append(self.fmt_int % stats.count)
        ret.append(self.fmt_int % stats.success)
        ret.append(self.fmt_percent % stats.error_percent)
        ret = self.sep.join(ret)
        return ret


class RenderRst:
    """Render stats in ReST format."""
    # number of slowest requests to display
    slowest_items = 5

    def __init__(self, config, stats, error, monitor, monitorconfig, options):
        self.config = config
        self.stats = stats
        self.error = error
        self.monitor = monitor
        self.monitorconfig = monitorconfig
        self.options = options
        self.rst = []

        cycles = stats.keys()
        cycles.sort()
        self.cycles = cycles
        if options.with_percentiles:
            BaseRst.with_percentiles = True
        if options.html:
            self.with_chart = True
        else:
            self.with_chart = False
        self.date = config['time'][:19].replace('T', ' ')

    def getRepresentativeCycleStat(self):
        """Return the cycle stat with the maximum number of steps."""
        stats = self.stats
        max_steps = 0
        cycle_r = None
        for cycle in self.cycles:
            steps = stats[cycle]['response_step'].keys()
            if cycle_r is None:
                cycle_r = stats[cycle]
            if len(steps) > max_steps:
                max_steps = steps
                cycle_r = stats[cycle]
        return cycle_r

    def getBestStpsCycle(self):
        """Return the cycle with the maximum STPS."""
        stats = self.stats
        max_stps = -1
        cycle_r = None
        for cycle in self.cycles:
            if not stats[cycle].has_key('test'):
                continue
            stps = stats[cycle]['test'].tps
            if stps > max_stps:
                max_stps = stps
                cycle_r = cycle
        if cycle_r is None and len(self.cycles):
            # no test ends during a cycle return the first one
            cycle_r = self.cycles[0]
        return cycle_r

    def getBestCycle(self):
        """Return the cycle with the maximum Apdex and SPPS."""
        stats = self.stats
        max_spps = -1
        cycle_r = None
        for cycle in self.cycles:
            if not stats[cycle].has_key('page'):
                continue
            if stats[cycle]['page'].apdex_score < 0.85:
                continue
            spps = stats[cycle]['page'].rps * stats[cycle]['page'].apdex_score
            if spps > max_spps:
                max_spps = spps
                cycle_r = cycle
        if cycle_r is None and len(self.cycles):
            # no test ends during a cycle return the first one
            cycle_r = self.cycles[0]
        return cycle_r

    def append(self, text):
        """Append text to rst output."""
        self.rst.append(text)

    def renderHeader(self):
        config = self.config
        self.append(rst_title("FunkLoad_ bench report", 0))
        self.append('')
        self.append(':date: ' + self.date)
        description = [config['class_description']]
        description += ["Bench result of ``%s.%s``: " % (config['class'],
                                                       config['method'])]
        description += [config['description']]
        indent = "\n           "
        self.append(':abstract: ' + indent.join(description))
        self.append('')
        self.append(".. _FunkLoad: http://funkload.nuxeo.org/")
        self.append(".. sectnum::    :depth: 2")
        self.append(".. contents:: Table of contents")
        self.append(".. |APDEXT| replace:: \ :sub:`%.1f`" % self.options.apdex_t)

    def renderConfig(self):
        """Render bench configuration and metadata."""
        self.renderHeader()
        config = self.config
        self.append(rst_title("Bench configuration", 2))
        self.append(LI + " Launched: %s" % self.date)
        if config.get('node'):
            self.append(LI + " From: %s" % config['node'])
        self.append(LI + " Test: ``%s.py %s.%s``" % (config['module'],
                                                 config['class'],
                                                 config['method']))
        if config.get('label'):
            self.append(LI + " Label: %s" % config['label'])
        self.append(LI + " Target server: %s" % config['server_url'])
        self.append(LI + " Cycles of concurrent users: %s" % config['cycles'])
        self.append(LI + " Cycle duration: %ss" % config['duration'])
        self.append(LI + " Sleeptime between requests: from %ss to %ss" % (
            config['sleep_time_min'], config['sleep_time_max']))
        self.append(LI + " Sleeptime between test cases: %ss" %
                    config['sleep_time'])
        self.append(LI + " Startup delay between threads: %ss" %
                    config['startup_delay'])
        self.append(LI + " Apdex: |APDEXT|")
        self.append(LI + " FunkLoad_ version: %s" % config['version'])
        self.append("")
        # check for metadata
        has_meta = False
        for key in config.keys():
            if key.startswith("meta:"):
                if not has_meta:
                    self.append("Bench metadata:")
                    self.append('')
                    has_meta = True
                self.append(LI + " %s: %s" % (key[5:], config[key]))
        if has_meta:
            self.append("")

    def renderTestContent(self, test):
        """Render global information about test content."""

        self.append(rst_title("Bench content", 2))
        config = self.config
        self.append('The test ``%s.%s`` contains: ' % (config['class'],
                                                       config['method']))
        self.append('')
        self.append(LI + dumb_pluralize(test.pages, 'page'))
        self.append(LI + dumb_pluralize(test.redirects, 'redirect'))
        self.append(LI + dumb_pluralize(test.links, 'link'))
        self.append(LI + dumb_pluralize(test.images, 'image'))
        self.append(LI + dumb_pluralize(test.xmlrpc, 'XML-RPC call'))
        self.append('')

        self.append('The bench contains:')
        total_tests = 0
        total_tests_error = 0
        total_pages = 0
        total_pages_error = 0
        total_responses = 0
        total_responses_error = 0
        stats = self.stats
        for cycle in self.cycles:
            if stats[cycle].has_key('test'):
                total_tests += stats[cycle]['test'].count
                total_tests_error += stats[cycle]['test'].error
            if stats[cycle].has_key('page'):
                stat = stats[cycle]['page']
                stat.finalize()
                total_pages += stat.count
                total_pages_error += stat.error
            if stats[cycle].has_key('response'):
                total_responses += stats[cycle]['response'].count
                total_responses_error += stats[cycle]['response'].error
        self.append('')
        pluralized_t_errs = dumb_pluralize(total_tests_error, 'error')
        pluralized_p_errs = dumb_pluralize(total_pages_error, 'error')
        pluralized_r_errs = dumb_pluralize(total_responses_error, 'error')
        self.append(LI + " %s tests" % total_tests + (
            total_tests_error and "," + pluralized_t_errs or ''))
        self.append(LI + " %s pages" % total_pages + (
            total_pages_error and "," + pluralized_p_errs or ''))
        self.append(LI + " %s requests" % total_responses + (
            total_responses_error and "," + pluralized_r_errs or ''))
        self.append('')


    def renderCyclesStat(self, key, title, description=''):
        """Render a type of stats for all cycles."""
        stats = self.stats
        first = True
        if key == 'test':
            klass = TestRst
        elif key == 'page':
            klass = PageRst
        elif key == 'response':
            klass = AllResponseRst
        self.append(rst_title(title, 2))
        if description:
            self.append(description)
            self.append('')
        renderer = None
        for cycle in self.cycles:
            if not stats[cycle].has_key(key):
                continue
            renderer = klass(stats[cycle][key])
            if first:
                self.append(renderer.render_header(self.with_chart))
                first = False
            self.append(renderer.render_stat())
        if renderer is not None:
            self.append(renderer.render_footer())
        else:
            self.append('Sorry no %s have finished during a cycle, '
                        'the cycle duration is too short.\n' % key)


    def renderCyclesStepStat(self, step):
        """Render a step stats for all cycle."""
        stats = self.stats
        first = True
        renderer = None
        for cycle in self.cycles:
            stat = stats[cycle]['response_step'].get(step)
            if stat is None:
                continue
            renderer = ResponseRst(stat)
            if first:
                self.append(renderer.render_header(self.with_chart))
                first = False
            self.append(renderer.render_stat())
        if renderer is not None:
            self.append(renderer.render_footer())

    def renderPageDetail(self, cycle_r):
        """Render a page detail."""
        self.append(rst_title("Page detail stats", 2))
        cycle_r_steps = cycle_r['response_step']
        steps = cycle_r['response_step'].keys()
        steps.sort()
        self.steps = steps
        current_step = -1
        newpage = False
        for step_name in steps:
            a_step = cycle_r_steps[step_name]
            if a_step.step != current_step:
                current_step = a_step.step
                self.append(rst_title("PAGE %s: %s" % (
                    a_step.step, a_step.description or a_step.url), 3, newpage))
                newpage = True
            self.append(LI + ' Req: %s, %s, url ``%s``' % (a_step.number,
                                                           a_step.type,
                                                           a_step.url))
            self.append('')
            self.renderCyclesStepStat(step_name)


    def createMonitorCharts(self):
        pass

    def renderMonitors(self):
        """Render all monitored hosts."""
        if not self.monitor or not self.with_chart:
            return
        charts = self.createMonitorCharts()
        if charts == None:
            return
        for host in charts.keys():
            self.renderMonitor(host, charts[host])


    def renderMonitor(self, host, charts):
        """Render a monitored host."""
        description = self.config.get(host, '')
        if len(charts)>0:
            self.append(rst_title("%s: %s" % (host, description), 3))
        for chart in charts:
            self.append("**%s**\n\n.. image:: %s\n" % (
                    chart[0], os.path.basename(chart[1])))

    def renderSlowestRequests(self, number):
        """Render the n slowest requests of the best cycle."""
        stats = self.stats
        self.append(rst_title("Slowest requests", 2))
        cycle = self.getBestCycle()
        cycle_name = None
        if not (cycle and stats[cycle].has_key('response_step')):
            return
        steps = stats[cycle]['response_step'].keys()
        items = []
        for step_name in steps:
            stat = stats[cycle]['response_step'][step_name]
            stat.finalize()
            items.append((stat.avg, stat.step,
                          stat.type, stat.url, stat.description,
                          stat.apdex_score))
            if not cycle_name:
                cycle_name = stat.cvus

        items.sort()
        items.reverse()
        self.append('The %d slowest average response time during the '
                    'best cycle with **%s** CUs:\n' % (number, cycle_name))
        for item in items[:number]:
            self.append(LI + ' In page %s, Apdex rating: %s, avg response time: %3.2fs, %s: ``%s``\n'
                        '  `%s`' % (
                item[1], Apdex.get_label(item[5]), item[0], item[2], item[3], item[4]))

    def renderErrors(self):
        """Render error list."""
        if not len(self.error):
            return
        self.append(rst_title("Failures and Errors", 2))
        for status in ('Failure', 'Error'):
            if not self.error.has_key(status):
                continue
            stats = self.error[status]
            errors = {}
            for stat in stats:
                header = stat.header
                key = (stat.code,
                       header.get('bobo-exception-file'),
                       header.get('bobo-exception-line'),
                       )
                err_list = errors.setdefault(key, [])
                err_list.append(stat)
            err_types = errors.keys()
            err_types.sort()
            self.append(rst_title(status + 's', 3))
            for err_type in err_types:
                stat = errors[err_type][0]
                pluralized_times = dumb_pluralize(len(errors[err_type]), 'time')
                if err_type[1]:
                    self.append(LI + '%s, code: %s, %s\n'
                                '  in %s, line %s: %s' %(
                        pluralized_times,
                        err_type[0],
                        header.get('bobo-exception-type'),
                        err_type[1], err_type[2],
                        header.get('bobo-exception-value')))
                else:
                    traceback = stat.traceback and stat.traceback.replace(
                        'File ', '\n    File ') or 'No traceback.'
                    self.append(LI + '%s, code: %s::\n\n'
                                '    %s\n' %(
                        pluralized_times,
                        err_type[0], traceback))

    def renderDefinitions(self):
        """Render field definition."""
        self.append(rst_title("Definitions", 2))
        self.append(LI + ' CUs: Concurrent users or number of concurrent threads'
                    ' executing tests.')
        self.append(LI + ' Request: a single GET/POST/redirect/XML-RPC request.')
        self.append(LI + ' Page: a request with redirects and resource'
                    ' links (image, css, js) for an HTML page.')
        self.append(LI + ' STPS: Successful tests per second.')
        self.append(LI + ' SPPS: Successful pages per second.')
        self.append(LI + ' RPS: Requests per second, successful or not.')
        self.append(LI + ' maxSPPS: Maximum SPPS during the cycle.')
        self.append(LI + ' maxRPS: Maximum RPS during the cycle.')
        self.append(LI + ' MIN: Minimum response time for a page or request.')
        self.append(LI + ' AVG: Average response time for a page or request.')
        self.append(LI + ' MAX: Maximmum response time for a page or request.')
        self.append(LI + ' P10: 10th percentile, response time where 10 percent'
                    ' of pages or requests are delivered.')
        self.append(LI + ' MED: Median or 50th percentile, response time where half'
                    ' of pages or requests are delivered.')
        self.append(LI + ' P90: 90th percentile, response time where 90 percent'
                    ' of pages or requests are delivered.')
        self.append(LI + ' P95: 95th percentile, response time where 95 percent'
                    ' of pages or requests are delivered.')
        self.append(LI + Apdex.description_para)
        self.append(LI + Apdex.rating_para)
        self.append('')
        self.append('Report generated with FunkLoad_ ' + get_version() +
                    ', more information available on the '
                    '`FunkLoad site <http://funkload.nuxeo.org/#benching>`_.')

    def renderHook(self):
        """Hook for post processing"""
        pass

    def __repr__(self):
        self.renderConfig()
        if not self.cycles:
            self.append('No cycle found')
            return '\n'.join(self.rst)
        cycle_r = self.getRepresentativeCycleStat()

        if cycle_r.has_key('test'):
            self.renderTestContent(cycle_r['test'])

        self.renderCyclesStat('test', 'Test stats',
                              'The number of Successful **Tests** Per Second '
                              '(STPS) over Concurrent Users (CUs).')
        self.renderCyclesStat('page', 'Page stats',
                              'The number of Successful **Pages** Per Second '
                              '(SPPS) over Concurrent Users (CUs).\n'
                              'Note: an XML-RPC call counts as a page.')
        self.renderCyclesStat('response', 'Request stats',
                              'The number of **Requests** Per Second (RPS) '
                              '(successful or not) over Concurrent Users (CUs).')
        self.renderSlowestRequests(self.slowest_items)
        self.renderMonitors()
        self.renderPageDetail(cycle_r)
        self.renderErrors()
        if not self.options.skip_definitions:
            self.renderDefinitions()
        self.renderHook()
        return '\n'.join(self.rst)

    def getMonitorConfig(self, host):
        """Return the host config or a default for backward compat"""
        if host in self.monitorconfig:
            return self.monitorconfig[host]
        return {'MonitorCPU': MonitorCPU().getConfig(),
                'MonitorMemFree': MonitorMemFree().getConfig(),
                'MonitorNetwork': MonitorNetwork(None).getConfig(),
                'MonitorCUs': MonitorCUs().getConfig()}


########NEW FILE########
__FILENAME__ = ReportRenderTrend
# (C) Copyright 2011 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Trend report rendering

The trend report uses metadata from a funkload.metadata file if present.

The format of the metadata file is the following:
label:short label to be displayed in the graph
anykey:anyvalue
a multi line description in ReST will be displayed in the listing parts
"""
import os
from ReportRenderRst import rst_title
from ReportRenderHtmlBase import RenderHtmlBase
from ReportRenderHtmlGnuPlot import gnuplot
from ReportRenderDiff import getRPath

def extract(report_dir, startswith):
    """Extract line form the ReST index file."""
    f = open(os.path.join(report_dir, "index.rst"))
    line = f.readline()
    while line:
        if line.startswith(startswith):
            f.close()
            return line[len(startswith):].strip()
        line = f.readline()
    f.close()
    return None


def extract_date(report_dir):
    """Extract the bench date form the ReST index file."""
    tag = "* Launched: "
    value = extract(report_dir, tag)
    if value is None:
        print "ERROR no date found in rst report %s" % report_dir
        return "NA"
    return value


def extract_max_cus(report_dir):
    """Extract the maximum concurrent users form the ReST index file."""
    tag = "* Cycles of concurrent users: "
    value = extract(report_dir, tag)
    if value is None:
        print "ERROR no max CUs found in rst report %s" % report_dir
        return "NA"
    return value.split(', ')[-1][:-1]


def extract_metadata(report_dir):
    """Extract the metadata from a funkload.metadata file."""
    ret = {}
    try:
        f = open(os.path.join(report_dir, "funkload.metadata"))
    except IOError:
        return ret
    lines = f.readlines()
    f.close()
    for line in lines:
        sep = None
        if line.count(':'):
            sep = ':'
        elif line.count('='):
            sep = '='
        else:
            key = 'misc'
            value = line.strip()
        if sep is not None:
            key, value = line.split(sep, 1)
            ret[key.strip()] = value.strip()
        elif value:
            v = ret.setdefault('misc', '')
            ret['misc'] = v + ' ' + value
    return ret

def extract_stat(tag, report_dir):
    """Extract stat from the ReST index file."""
    lines = open(os.path.join(report_dir, "index.rst")).readlines()
    try:
        idx = lines.index("%s stats\n" % tag)
    except ValueError:
        print "ERROR tag %s not found in rst report %s" % (tag, report_dir)
        return []
    delim = 0
    ret =  []
    header = ""
    for line in lines[idx:]:
        if line.startswith(" ====="):
            delim += 1
            continue
        if delim == 1:
            header = line.strip().split()
        if delim < 2:
            continue
        if delim == 3:
            break
        ret.append([x.replace("%","") for x in line.strip().split()])
    return header, ret

def get_metadata(metadata):
    """Format metadata."""
    ret = []
    keys = metadata.keys()
    keys.sort()
    for key in keys:
        if key not in ('label', 'misc'):
            ret.append('%s: %s' % (key, metadata[key]))
    if metadata.get('misc'):
        ret.append(metadata['misc'])
    return ', '.join(ret)


class RenderTrend(RenderHtmlBase):
    """Trend report."""
    report_dir1 = None
    report_dir2 = None
    header = None
    sep = ', '
    data_file = None
    output_dir = None
    script_file = None

    def __init__(self, args, options, css_file=None):
        # Swap windows path separator backslashes for forward slashes
        # Windows accepts '/' but some file formats like rest treat the
        # backslash specially.
        self.args = [os.path.abspath(arg).replace('\\', '/') for arg in args]
        self.options = options
        self.css_file = css_file
        self.quiet = options.quiet

    def generateReportDirectory(self, output_dir):
        """Generate a directory name for a report."""
        output_dir = os.path.abspath(output_dir)
        report_dir = os.path.join(output_dir, 'trend-report')
        if not os.access(report_dir, os.W_OK):
            os.mkdir(report_dir, 0775)
        report_dir.replace('\\', '/')
        return report_dir

    def createCharts(self):
        """Render stats."""
        self.createGnuplotData()
        self.createGnuplotScript()
        gnuplot(self.script_file)

    def createRstFile(self):
        """Create the ReST file."""
        rst_path = os.path.join(self.report_dir, 'index.rst')
        lines = []
        reports = self.args
        reports_name = [os.path.basename(report) for report in reports]
        reports_date = [extract_date(report) for report in reports]
        self.reports_name = reports_name
        reports_metadata = [extract_metadata(report) for report in reports]
        self.reports_metadata = reports_metadata
        reports_rpath = [getRPath(self.report_dir, 
                                  os.path.join(report, 'index.html').replace(
                    '\\', '/')) for report in reports]
        self.max_cus = extract_max_cus(reports[0])
        # TODO: handles case where reports_name are the same
        lines.append(rst_title("FunkLoad_ trend report", level=0))
        lines.append("")
        lines.append(".. sectnum::    :depth: 2")
        lines.append("")
        lines.append(rst_title("Trends", level=2))
        lines.append(" .. image:: trend_apdex.png")
        lines.append(" .. image:: trend_spps.png")
        lines.append(" .. image:: trend_avg.png")
        lines.append("")
        lines.append(rst_title("List of reports", level=1))
        count = 0
        for report in reports_name:
            count += 1
                         
            lines.append(" * Bench **%d** %s: `%s <%s>`_ %s" % (
                    count, reports_date[count - 1], report, 
                    reports_rpath[count - 1], 
                    get_metadata(reports_metadata[count - 1])))
            lines.append("")
        lines.append(" .. _FunkLoad: http://funkload.nuxeo.org/")
        lines.append("")
        f = open(rst_path, 'w')
        f.write('\n'.join(lines))
        f.close()
        self.rst_path = rst_path

    def copyXmlResult(self):
        pass

    def __repr__(self):
        return self.render()

    def createGnuplotData(self):
        """Render rst stat."""

        def output_stat(tag, count):
            header, stat = extract_stat(tag, rep)
            text = []
            for line in stat:
                line.insert(0, str(count))
                line.append(extract_date(rep))
                text.append(' '.join(line))
            return '\n'.join(text)

        data_file = os.path.join(self.report_dir, 'trend.dat')
        self.data_file = data_file
        f = open(data_file, 'w')
        count = 0
        for rep in self.args:
            count += 1
            f.write(output_stat('Page', count) + '\n\n')
        f.close()

    def createGnuplotScript(self):
        """Build gnuplot script"""
        labels = []
        count = 0
        for metadata in self.reports_metadata:
            count += 1
            if metadata.get('label'):
                labels.append('set label "%s" at %d,%d,1 rotate by 45 front' % (
                        metadata.get('label'), count, int(self.max_cus) + 2))
        labels = '\n'.join(labels)
        script_file = os.path.join(self.report_dir, 'script.gplot')
        self.script_file = script_file
        f = open(script_file, 'w')
        f.write('# ' + ' '.join(self.reports_name))
        f.write('''# COMMON SETTINGS
set grid  back
set boxwidth 0.9 relative

# Apdex
set output "trend_apdex.png"
set terminal png size 640,380
set border 895 front linetype -1 linewidth 1.000
set grid nopolar
set grid xtics nomxtics ytics nomytics noztics nomztics \
 nox2tics nomx2tics noy2tics nomy2tics nocbtics nomcbtics
set grid layerdefault  linetype 0 linewidth 1.000,  linetype 0 linewidth 1.000
set style line 100  linetype 5 linewidth 0.10 pointtype 100 pointsize default
#set view map
unset surface
set style data pm3d
set style function pm3d
set ticslevel 0
set nomcbtics
set xrange [ * : * ] noreverse nowriteback
set yrange [ * : * ] noreverse nowriteback
set zrange [ * : * ] noreverse nowriteback
set cbrange [ * : * ] noreverse nowriteback
set lmargin 0
set pm3d at s scansforward
# set pm3d scansforward interpolate 0,1
set view map
set title "Apdex Trend"
set xlabel "Bench"
set ylabel "CUs"
%s
splot "trend.dat" using 1:2:3 with linespoints
unset label
set view

set output "trend_spps.png"
set title "Pages per second Trend"
splot "trend.dat" using 1:2:5 with linespoints

set output "trend_avg.png"
set palette negative
set title "Average response time (s)"
splot "trend.dat" using 1:2:11 with linespoints

''' % labels)
        f.close()


########NEW FILE########
__FILENAME__ = ReportStats
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Classes that collect statistics submitted by the result parser.

$Id: ReportStats.py 24737 2005-08-31 09:00:16Z bdelbosc $
"""

from apdex import Apdex


class MonitorStat:
    """Collect system monitor info."""
    def __init__(self, attrs):
        for key, value in attrs.items():
            setattr(self, key, value)


class ErrorStat:
    """Collect Error or Failure stats."""
    def __init__(self, cycle, step, number, code, header, body, traceback):
        self.cycle = cycle
        self.step = step
        self.number = number
        self.code = code
        self.header = header and header.copy() or {}
        self.body = body or None
        self.traceback = traceback


class Percentiles:
    """ Calculate Percentiles with the given stepsize. """

    def __init__(self, stepsize=10, name="UNKNOWN", results=None):
        self.stepsize = stepsize
        self.name = name
        if results is None:
            self.results = []
        else:
            self.results = results

    def addResult(self, newresult):
        """Add a new result."""
        self.results.append(newresult)

    def calcPercentiles(self):
        """Compute percentiles."""
        results = self.results
        results.sort()
        len_results = len(results)
        old_value = -1
        for perc in range(0, 100, self.stepsize):
            index = int(perc / 100.0 * len_results)
            try:
                value = results[index]
            except IndexError:
                value = -1.0
            setattr(self, "perc%02d" % perc, float(value))
            old_value = value

    def __str__(self):
        self.calcPercentiles()
        fmt_string = ["Percentiles: %s" % self.name]
        for perc in range(0, 100, self.stepsize):
            name = "perc%02d" % perc
            fmt_string.append("%s=%s" % (name, getattr(self, name)))
        return ", ".join(fmt_string)

    def __repr__(self):
        return "Percentiles(stepsize=%r, name=%r, results=%r)" % (
            self.stepsize, self.name, self.results)


class ApdexStat:
    def __init__(self):
        self.apdex_satisfied = 0
        self.apdex_tolerating = 0
        self.apdex_frustrated = 0
        self.count = 0

    def add(self, duration):
        if Apdex.satisfying(duration):
            self.apdex_satisfied += 1
        elif Apdex.tolerable(duration):
            self.apdex_tolerating += 1
        else:
            self.apdex_frustrated += 1
        self.count += 1

    def getScore(self):
        return Apdex.score(self.apdex_satisfied, self.apdex_tolerating,
                           self.apdex_frustrated)


class AllResponseStat:
    """Collect stat for all response in a cycle."""
    def __init__(self, cycle, cycle_duration, cvus):
        self.cycle = cycle
        self.cycle_duration = cycle_duration
        self.cvus = int(cvus)
        self.per_second = {}
        self.max = 0
        self.min = 999999999
        self.avg = 0
        self.total = 0
        self.count = 0
        self.success = 0
        self.error = 0
        self.error_percent = 0
        self.rps = 0
        self.rps_min = 0
        self.rps_max = 0
        self.finalized = False
        self.percentiles = Percentiles(stepsize=5, name=cycle)
        self.apdex = ApdexStat()
        self.apdex_score = None

    def add(self, date, result, duration):
        """Add a new response to stat."""
        date_s = int(float(date))
        self.per_second[date_s] = self.per_second.setdefault(
            int(date_s), 0) + 1
        self.count += 1
        if result == 'Successful':
            self.success += 1
        else:
            self.error += 1
        duration_f = float(duration)
        self.max = max(self.max, duration_f)
        self.min = min(self.min, duration_f)
        self.total += duration_f
        self.finalized = False
        self.percentiles.addResult(duration_f)
        self.apdex.add(duration_f)

    def finalize(self):
        """Compute avg times."""
        if self.finalized:
            return
        if self.count:
            self.avg = self.total / float(self.count)
        self.min = min(self.max, self.min)
        if self.error:
            self.error_percent = 100.0 * self.error / float(self.count)

        rps_min = rps_max = 0
        for date in self.per_second.keys():
            rps_max = max(rps_max, self.per_second[date])
            rps_min = min(rps_min, self.per_second[date])
        if self.cycle_duration:
            rps = self.count / float(self.cycle_duration)
            if rps < 1:
                # average is lower than 1 this means that sometime there was
                # no request during one second
                rps_min = 0
            self.rps = rps
        self.rps_max = rps_max
        self.rps_min = rps_min
        self.percentiles.calcPercentiles()
        self.apdex_score = self.apdex.getScore()
        self.finalized = True


class SinglePageStat:
    """Collect stat for a single page."""
    def __init__(self, step):
        self.step = step
        self.count = 0
        self.date_s = None
        self.duration = 0.0
        self.result = 'Successful'

    def addResponse(self, date, result, duration):
        """Add a response to a page."""
        self.count += 1
        if self.date_s is None:
            self.date_s = int(float(date))
        self.duration += float(duration)
        if result != 'Successful':
            self.result = result

    def __repr__(self):
        """Representation."""
        return 'page %s %s %ss' % (self.step,
                                   self.result, self.duration)


class PageStat(AllResponseStat):
    """Collect stat for asked pages in a cycle."""
    def __init__(self, cycle, cycle_duration, cvus):
        AllResponseStat.__init__(self, cycle, cycle_duration, cvus)
        self.threads = {}

    def add(self, thread, step,  date, result, duration, rtype):
        """Add a new response to stat."""
        thread = self.threads.setdefault(thread, {'count': 0,
                                                  'pages': {}})
        if str(rtype) in ('post', 'get', 'xmlrpc', 'put', 'delete', 'head'):
            new_page = True
        else:
            new_page = False
        if new_page:
            thread['count'] += 1
            self.count += 1
        if not thread['count']:
            # don't take into account request that belongs to a staging up page
            return
        stat = thread['pages'].setdefault(thread['count'],
                                          SinglePageStat(step))
        stat.addResponse(date, result, duration)
        self.apdex.add(float(duration))
        self.finalized = False

    def finalize(self):
        """Compute avg times."""
        if self.finalized:
            return
        for thread in self.threads.keys():
            for page in self.threads[thread]['pages'].values():
                if str(page.result) == 'Successful':
                    if page.date_s:
                        count = self.per_second.setdefault(page.date_s, 0) + 1
                        self.per_second[page.date_s] = count
                    self.success += 1
                    self.total += page.duration
                    self.percentiles.addResult(page.duration)
                else:
                    self.error += 1
                    continue
                duration = page.duration
                self.max = max(self.max, duration)
                self.min = min(self.min, duration)
        AllResponseStat.finalize(self)
        if self.cycle_duration:
            # override rps to srps
            self.rps = self.success / float(self.cycle_duration)
        self.percentiles.calcPercentiles()
        self.finalized = True


class ResponseStat:
    """Collect stat a specific response in a cycle."""
    def __init__(self, step, number, cvus):
        self.step = step
        self.number = number
        self.cvus = int(cvus)
        self.max = 0
        self.min = 999999999
        self.avg = 0
        self.total = 0
        self.count = 0
        self.success = 0
        self.error = 0
        self.error_percent = 0
        self.url = '?'
        self.description = ''
        self.type = '?'
        self.finalized = False
        self.percentiles = Percentiles(stepsize=5, name=step)
        self.apdex = ApdexStat()
        self.apdex_score = None

    def add(self, rtype, result, url, duration, description=None):
        """Add a new response to stat."""
        self.count += 1
        if result == 'Successful':
            self.success += 1
        else:
            self.error += 1
        self.max = max(self.max, float(duration))
        self.min = min(self.min, float(duration))
        self.total += float(duration)
        self.percentiles.addResult(float(duration))
        self.url = url
        self.type = rtype
        if description is not None:
            self.description = description
        self.finalized = False
        self.apdex.add(float(duration))

    def finalize(self):
        """Compute avg times."""
        if self.finalized:
            return
        if self.total:
            self.avg = self.total / float(self.count)
        self.min = min(self.max, self.min)
        if self.error:
            self.error_percent = 100.0 * self.error / float(self.count)
        self.percentiles.calcPercentiles()
        self.apdex_score = self.apdex.getScore()
        self.finalized = True


class TestStat:
    """Collect test stat for a cycle.

    Stat on successful test case.
    """
    def __init__(self, cycle, cycle_duration, cvus):
        self.cycle = cycle
        self.cycle_duration = float(cycle_duration)
        self.cvus = int(cvus)
        self.max = 0
        self.min = 999999999
        self.avg = 0
        self.total = 0
        self.count = 0
        self.success = 0
        self.error = 0
        self.error_percent = 0
        self.traceback = []
        self.pages = self.images = self.redirects = self.links = 0
        self.xmlrpc = 0
        self.tps = 0
        self.finalized = False
        self.percentiles = Percentiles(stepsize=5, name=cycle)

    def add(self, result, pages, xmlrpc, redirects, images, links,
            duration, traceback=None):
        """Add a new response to stat."""
        self.finalized = False
        self.count += 1
        if traceback is not None:
            self.traceback.append(traceback)
        if result == 'Successful':
            self.success += 1
        else:
            self.error += 1
            return
        self.max = max(self.max, float(duration))
        self.min = min(self.min, float(duration))
        self.total += float(duration)
        self.pages = max(self.pages, int(pages))
        self.xmlrpc = max(self.xmlrpc, int(xmlrpc))
        self.redirects = max(self.redirects, int(redirects))
        self.images = max(self.images, int(images))
        self.links = max(self.links, int(links))
        self.percentiles.addResult(float(duration))

    def finalize(self):
        """Compute avg times."""
        if self.finalized:
            return
        if self.success:
            self.avg = self.total / float(self.success)
        self.min = min(self.max, self.min)
        if self.error:
            self.error_percent = 100.0 * self.error / float(self.count)
        if self.cycle_duration:
            self.tps = self.success / float(self.cycle_duration)
        self.percentiles.calcPercentiles()
        self.finalized = True

########NEW FILE########
__FILENAME__ = rtfeedback
import json
import socket
try:
    import gevent
    import zmq.green as zmq
except ImportError:
    import zmq

from multiprocessing import Process
from zmq.eventloop import ioloop, zmqstream


DEFAULT_ENDPOINT = 'tcp://127.0.0.1:9999'
DEFAULT_PUBSUB = 'tcp://127.0.0.1:9998'


class FeedbackPublisher(Process):
    """Publishes all the feedback received from the various nodes.
    """
    def __init__(self, endpoint=DEFAULT_ENDPOINT,
                 pubsub_endpoint=DEFAULT_PUBSUB,
                 context=None, handler=None):
        Process.__init__(self)
        self.context = context
        self.endpoint = endpoint
        self.pubsub_endpoint = pubsub_endpoint
        self.daemon = True
        self.handler = handler

    def _handler(self, msg):
        if self.handler is not None:
            self.handler(msg)
        self.pub_sock.send_multipart(['feedback', msg[0]])

    def run(self):
        print 'publisher running in a thread'
        self.context = self.context or zmq.Context.instance()
        self.sock = self.context.socket(zmq.PULL)
        self.sock.bind(self.endpoint)
        self.pub_sock = self.context.socket(zmq.PUB)
        self.pub_sock.bind(self.pubsub_endpoint)
        self.loop = ioloop.IOLoop.instance()
        self.stream = zmqstream.ZMQStream(self.sock, self.loop)
        self.stream.on_recv(self._handler)
        self.loop.start()

    def stop(self):
        self.loop.close()


class FeedbackSender(object):
    """Sends feedback
    """
    def __init__(self, endpoint=DEFAULT_ENDPOINT, server=None, context=None):
        self.context = context or zmq.Context.instance()
        self.sock = self.context.socket(zmq.PUSH)
        self.sock.connect(endpoint)
        if server is None:
            server = socket.gethostname()
        self.server = server

    def test_done(self, data):
        data['server'] = self.server
        self.sock.send(json.dumps(data))


class FeedbackSubscriber(Process):
    """Subscribes to a published feedback.
    """
    def __init__(self, pubsub_endpoint=DEFAULT_PUBSUB, handler=None,
                 context=None, **kw):
        Process.__init__(self)
        self.handler = handler
        self.context = context
        self.pubsub_endpoint = pubsub_endpoint
        self.daemon = True
        self.kw = kw

    def _handler(self, msg):
        topic, msg = msg
        msg = json.loads(msg)
        if self.handler is None:
            print msg
        else:
            self.handler(msg, **self.kw)

    def run(self):
        self.context = self.context or zmq.Context.instance()
        self.pub_sock = self.context.socket(zmq.SUB)
        self.pub_sock.connect(self.pubsub_endpoint)
        self.pub_sock.setsockopt(zmq.SUBSCRIBE, b'')
        self.loop = ioloop.IOLoop.instance()
        self.stream = zmqstream.ZMQStream(self.pub_sock, self.loop)
        self.stream.on_recv(self._handler)
        self.loop.start()

    def stop(self):
        self.loop.close()


if __name__ == '__main__':
    print 'Starting subscriber'
    sub = FeedbackSubscriber()
    print 'Listening to events on %r' % sub.pubsub_endpoint
    try:
        sub.run()
    except KeyboardInterrupt:
        sub.stop()
        print 'Bye!'

########NEW FILE########
__FILENAME__ = TestRunner
#!/usr/bin/python
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad Test runner.

Similar to unittest.TestProgram but:
* you can pass the python module to load
* able to override funkload configuration file using command line options
* cool color output
* support doctest with python2.4

$Id: TestRunner.py 24758 2005-08-31 12:33:00Z bdelbosc $
"""
try:
    import psyco
    psyco.full()
except ImportError:
    pass
import os
import sys
import types
import time
import unittest
import re
from StringIO import StringIO
from optparse import OptionParser, TitledHelpFormatter
from utils import red_str, green_str, get_version
from funkload.FunkLoadTestCase import FunkLoadTestCase

# ------------------------------------------------------------
# doctest patch to command verbose mode only available with python2.4
#
g_doctest_verbose = False
try:
    from doctest import DocTestSuite, DocFileSuite, DocTestCase, DocTestRunner
    from doctest import REPORTING_FLAGS, _unittest_reportflags
    g_has_doctest = True
except ImportError:
    g_has_doctest = False
else:
    def DTC_runTest(self):
        test = self._dt_test
        old = sys.stdout
        new = StringIO()
        optionflags = self._dt_optionflags
        if not (optionflags & REPORTING_FLAGS):
            # The option flags don't include any reporting flags,
            # so add the default reporting flags
            optionflags |= _unittest_reportflags
        # Patching doctestcase to enable verbose mode
        global g_doctest_verbose
        runner = DocTestRunner(optionflags=optionflags,
                               checker=self._dt_checker,
                               verbose=g_doctest_verbose)
        # End of patch
        try:
            runner.DIVIDER = "-"*70
            failures, tries = runner.run(
                test, out=new.write, clear_globs=False)
        finally:
            sys.stdout = old
        if failures:
            raise self.failureException(self.format_failure(new.getvalue()))
        elif g_doctest_verbose:
            print new.getvalue()

    DocTestCase.runTest = DTC_runTest



# ------------------------------------------------------------
#
#
class TestLoader(unittest.TestLoader):
    """Override to add options when instanciating test case."""
    def loadTestsFromTestCase(self, testCaseClass):
        """Return a suite of all tests cases contained in testCaseClass"""
        if not issubclass(testCaseClass, FunkLoadTestCase):
            return unittest.TestLoader.loadTestsFromTestCase(self,
                                                             testCaseClass)
        options = getattr(self, 'options', None)
        return self.suiteClass([testCaseClass(name, options) for name in
                                self.getTestCaseNames(testCaseClass)])

    def loadTestsFromModule(self, module):
        """Return a suite of all tests cases contained in the given module"""
        global g_has_doctest
        tests = []
        doctests = None
        if g_has_doctest:
            try:
                doctests = DocTestSuite(module)
            except ValueError:
                pass
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, (type, types.ClassType)) and
                issubclass(obj, unittest.TestCase)):
                tests.append(self.loadTestsFromTestCase(obj))
        suite = self.suiteClass(tests)
        if doctests is not None:
            suite.addTest(doctests)
        return suite


    def loadTestsFromName(self, name, module=None):
        """Return a suite of all tests cases given a string specifier.

        The name may resolve either to a module, a test case class, a
        test method within a test case class, or a callable object which
        returns a TestCase or TestSuite instance.

        The method optionally resolves the names relative to a given module.
        """
        parts = name.split('.')
        if module is None:
            if not parts:
                raise ValueError, "incomplete test name: %s" % name
            else:
                parts_copy = parts[:]
                while parts_copy:
                    try:
                        module = __import__('.'.join(parts_copy))
                        break
                    except ImportError:
                        del parts_copy[-1]
                        if not parts_copy: raise
                parts = parts[1:]
        obj = module
        for part in parts:
            obj = getattr(obj, part)
        import unittest
        if type(obj) == types.ModuleType:
            return self.loadTestsFromModule(obj)
        elif (isinstance(obj, (type, types.ClassType)) and
              issubclass(obj, unittest.TestCase)):
            return self.loadTestsFromTestCase(obj)
        elif type(obj) == types.UnboundMethodType:
            # pass funkload options
            if issubclass(obj.im_class, FunkLoadTestCase):
                return obj.im_class(obj.__name__, self.options)
            else:
                return obj.im_class(obj.__name__)
        elif callable(obj):
            test = obj()
            if not isinstance(test, unittest.TestCase) and \
               not isinstance(test, unittest.TestSuite):
                raise ValueError, \
                      "calling %s returned %s, not a test" % (obj,test)
            return test
        else:
            raise ValueError, "don't know how to make test from: %s" % obj




class ColoredStream(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, arg):
        if arg in ['OK', 'Ok', 'ok', '.']:
            arg = green_str(arg)
        elif arg in ['ERROR', 'E', 'FAILED', 'FAIL', 'F']:
            arg = red_str(arg)
        sys.stderr.write(arg)

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

class _ColoredTextTestResult(unittest._TextTestResult):
    """Colored version."""
    def printErrorList(self, flavour, errors):
        flavour = red_str(flavour)
        super(_ColoredTextTestResult, self).printErrorList(flavour, errors)


def filter_testcases(suite, cpattern, negative_pattern=False):
    """Filter a suite with test names that match the compiled regex pattern."""
    new = unittest.TestSuite()
    for test in suite._tests:
        if isinstance(test, unittest.TestCase):
            name = test.id() # Full test name: package.module.class.method
            name = name[1 + name.rfind('.'):] # extract method name
            if cpattern.search(name):
                if not negative_pattern:
                    new.addTest(test)
            elif negative_pattern:
                new.addTest(test)
        else:
            filtered = filter_testcases(test, cpattern, negative_pattern)
            if filtered:
                new.addTest(filtered)
    return new


def display_testcases(suite):
    """Display test cases of the suite."""
    for test in suite._tests:
        if isinstance(test, unittest.TestCase):
            name = test.id()
            name = name[1 + name.find('.'):]
            print name
        else:
            display_testcases(test)


class TestProgram(unittest.TestProgram):
    """Override to add a python module and more options."""
    USAGE = """%prog [options] file [class.method|class|suite] [...]

%prog launch a FunkLoad unit test.

A FunkLoad unittest use a configuration file named [class].conf, this
configuration is overriden by the command line options.

See http://funkload.nuxeo.org/ for more information.


Examples
========
  %prog myFile.py
                        Run all tests.
  %prog myFile.py test_suite
                        Run suite named test_suite.
  %prog myFile.py MyTestCase.testSomething
                        Run a single test MyTestCase.testSomething.
  %prog myFile.py MyTestCase
                        Run all 'test*' test methods in MyTestCase.
  %prog myFile.py MyTestCase -u http://localhost
                        Same against localhost.
  %prog --doctest myDocTest.txt
                        Run doctest from plain text file (requires python2.4).
  %prog --doctest -d myDocTest.txt
                        Run doctest with debug output (requires python2.4).
  %prog myfile.py -V
                        Run default set of tests and view in real time each
                        page fetch with firefox.
  %prog myfile.py MyTestCase.testSomething -l 3 -n 100
                        Run MyTestCase.testSomething, reload one hundred
                        time the page 3 without concurrency and as fast as
                        possible. Output response time stats. You can loop
                        on many pages using slice -l 2:4.
  %prog myFile.py -e [Ss]ome
                        Run all tests that match the regex [Ss]ome.
  %prog myFile.py -e '!xmlrpc$'
                        Run all tests that does not ends with xmlrpc.
  %prog myFile.py --list
                        List all the test names.
  %prog -h
                        More options.
"""
    def __init__(self, module=None, defaultTest=None,
                 argv=None, testRunner=None,
                 testLoader=unittest.defaultTestLoader):
        if argv is None:
            argv = sys.argv
        self.module = module
        self.testNames = None
        self.verbosity = 1
        self.color = True
        self.profile = False
        self.defaultTest = defaultTest
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        self.parseArgs(argv)
        self.testRunner = testRunner
        self.checkAsDocFile = False

        module = self.module
        if type(module)  == type(''):
            try:
                self.module = __import__(module)
            except ImportError:
                global g_has_doctest
                if g_has_doctest:
                    # may be a doc file case
                    self.checkAsDocFile = True
                else:
                    raise
            else:
                for part in module.split('.')[1:]:
                    self.module = getattr(self.module, part)
        else:
            self.module = module
        self.loadTests()
        if self.list_tests:
            display_testcases(self.test)
        else:
            self.runTests()

    def loadTests(self):
        """Load unit and doc tests from modules or names."""
        if self.checkAsDocFile:
            self.test = DocFileSuite(os.path.abspath(self.module),
                                     module_relative=False)
        else:
            if self.testNames is None:
                self.test = self.testLoader.loadTestsFromModule(self.module)
            else:
                self.test = self.testLoader.loadTestsFromNames(self.testNames,
                                                               self.module)
        if self.test_name_pattern is not None:
            test_name_pattern = self.test_name_pattern
            negative_pattern = False
            if test_name_pattern.startswith('!'):
                test_name_pattern = test_name_pattern[1:]
                negative_pattern = True
            cpattern = re.compile(test_name_pattern)
            self.test = filter_testcases(self.test, cpattern, negative_pattern)

    def parseArgs(self, argv):
        """Parse programs args."""
        global g_doctest_verbose
        parser = OptionParser(self.USAGE, formatter=TitledHelpFormatter(),
                              version="FunkLoad %s" % get_version())
        parser.add_option("", "--config", type="string", dest="config", metavar='CONFIG',
                          help="Path to alternative config file.")
        parser.add_option("-q", "--quiet", action="store_true",
                          help="Minimal output.")
        parser.add_option("-v", "--verbose", action="store_true",
                          help="Verbose output.")
        parser.add_option("-d", "--debug", action="store_true",
                          help="FunkLoad and doctest debug output.")
        parser.add_option("--debug-level", type="int",
                          help="Debug level 3 is more verbose.")
        parser.add_option("-u", "--url", type="string", dest="main_url",
                          help="Base URL to bench without ending '/'.")
        parser.add_option("-m", "--sleep-time-min", type="string",
                          dest="ftest_sleep_time_min",
                          help="Minumum sleep time between request.")
        parser.add_option("-M", "--sleep-time-max", type="string",
                          dest="ftest_sleep_time_max",
                          help="Maximum sleep time between request.")
        parser.add_option("--dump-directory", type="string",
                          dest="dump_dir",
                          help="Directory to dump html pages.")
        parser.add_option("-V", "--firefox-view", action="store_true",
                          help="Real time view using firefox, "
                          "you must have a running instance of firefox "
                          "in the same host.")
        parser.add_option("--no-color", action="store_true",
                          help="Monochrome output.")
        parser.add_option("-l", "--loop-on-pages", type="string",
                          dest="loop_steps",
                          help="Loop as fast as possible without concurrency "
                          "on pages, expect a page number or a slice like 3:5."
                          " Output some statistics.")
        parser.add_option("-n", "--loop-number", type="int",
                          dest="loop_number", default=10,
                          help="Number of loop.")
        parser.add_option("--accept-invalid-links", action="store_true",
                          help="Do not fail if css/image links are "
                          "not reachable.")
        parser.add_option("--simple-fetch", action="store_true",
                          dest="ftest_simple_fetch",
                          help="Don't load additional links like css "
                          "or images when fetching an html page.")
        parser.add_option("--stop-on-fail", action="store_true",
                          help="Stop tests on first failure or error.")
        parser.add_option("-e", "--regex", type="string", default=None,
                          help="The test names must match the regex.")
        parser.add_option("--list", action="store_true",
                          help="Just list the test names.")
        parser.add_option("--doctest", action="store_true", default=False,
                          help="Check for a doc test.")
        parser.add_option("--pause", action="store_true",
                          help="Pause between request, "
                          "press ENTER to continue.")
        parser.add_option("--profile", action="store_true",
                          help="Run test under the Python profiler.")

        options, args = parser.parse_args()
        if self.module is None:
            if len(args) == 0:
                parser.error("incorrect number of arguments")
            # remove the .py
            module = args[0]
            if module.endswith('.py'):
                module =  os.path.basename(os.path.splitext(args[0])[0])
            self.module = module
        else:
            args.insert(0, self.module)
        if not options.doctest:
            global g_has_doctest
            g_has_doctest = False
        if options.verbose:
            self.verbosity = 2
        if options.quiet:
            self.verbosity = 0
            g_doctest_verbose = False
        if options.debug or options.debug_level:
            options.ftest_debug_level = 1
            options.ftest_log_to = 'console file'
            g_doctest_verbose = True
        if options.debug_level:
            options.ftest_debug_level = int(options.debug_level)
        if sys.platform.lower().startswith('win'):
            self.color = False
        else:
            self.color = not options.no_color
        self.test_name_pattern = options.regex
        self.list_tests = options.list
        self.profile = options.profile

        # set testloader options
        self.testLoader.options = options
        if self.defaultTest is not None:
            self.testNames = [self.defaultTest]
        elif len(args) > 1:
            self.testNames = args[1:]
        # else we have to load all module test

    def runTests(self):
        """Launch the tests."""
        if self.testRunner is None:
            if self.color:
                self.testRunner = unittest.TextTestRunner(
                    stream =ColoredStream(sys.stderr),
                    resultclass = _ColoredTextTestResult,
                    verbosity = self.verbosity)
            else:
                self.testRunner = unittest.TextTestRunner(
                    verbosity=self.verbosity)
        if self.profile:
            import profile, pstats
            pr = profile.Profile()
            d = {'self': self}
            pr.runctx('result = self.testRunner.run(self.test)', {}, d)
            result = d['result']
            pr.dump_stats('profiledata')
            ps = pstats.Stats('profiledata')
            ps.strip_dirs()
            ps.sort_stats('cumulative')
            ps.print_stats()
        else:
            result = self.testRunner.run(self.test)
        sys.exit(not result.wasSuccessful())



# ------------------------------------------------------------
# main
#
def main():
    """Default main."""
    # enable to load module in the current path
    cur_path = os.path.abspath(os.path.curdir)
    sys.path.insert(0, cur_path)
    # use our testLoader
    test_loader = TestLoader()
    TestProgram(testLoader=test_loader)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_apdex
#! /usr/bin/env python

import os
import sys
import unittest

if os.path.realpath(os.curdir) == os.path.realpath(os.path.dirname(__file__)):
    sys.path.append('../..')

from funkload.apdex import Apdex

class TestApdex(unittest.TestCase):

    def test_sanity(self):
        self.assertEqual(Apdex.T, 1.5)

        self.assertTrue(Apdex.satisfying(0.1))
        self.assertTrue(Apdex.satisfying(1.49))
        self.assertFalse(Apdex.satisfying(1.5))

        self.assertTrue(Apdex.tolerable(1.5))
        self.assertTrue(Apdex.tolerable(5.99))
        self.assertFalse(Apdex.tolerable(6.0))

        self.assertTrue(Apdex.frustrating(6.0))

    def test_100_percent_satisfied(self):
        s, t, f = 10, 0, 0
        score = Apdex.score(s, t, f)
        self.assertTrue(score == 1.0)
        self.assertTrue(score.label == Apdex.Excellent.label)
        self.assertTrue(Apdex.get_label(score) == Apdex.Excellent.label)

    def test_unacceptable(self):
        s, t, f = 0, 0, 10
        score = Apdex.score(s, t, f)
        self.assertTrue(score == 0)
        self.assertTrue(score.label == Apdex.Unacceptable.label)
        self.assertTrue(Apdex.get_label(score) == Apdex.Unacceptable.label)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_dummy
# (C) Copyright 2006 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
#
"""Dummy test used by test_Install.py

$Id$

simple doctest in a docstring:

  >>> 1 + 1
  2

"""
import unittest

class TestDummy1(unittest.TestCase):
    """Dummy test case."""
    def test_dummy1_1(self):
        self.assertEquals(1+1, 2)

    def test_dummy1_2(self):
        self.assertEquals(1+1, 2)


class TestDummy2(unittest.TestCase):
    """Dummy test case."""
    def test_dummy2_1(self):
        self.assertEquals(1+1, 2)

    def test_dummy2_2(self):
        self.assertEquals(1+1, 2)

class TestDummy3(unittest.TestCase):
    """Failing test case not part of the test_suite."""
    def test_dummy3_1(self):
        self.assertEquals(1+1, 2)

    def test_dummy3_2(self):
        # failing test case
        self.assertEquals(1+1, 3, 'example of a failing test')

    def test_dummy3_3(self):
        # error test case
        impossible = 1/0
        self.assert_(1+1, 2)


class Dummy:
    """Testing docstring."""
    def __init__(self, value):
        self.value = value

    def double(self):
        """Return the double of the initial value.

        >>> d = Dummy(1)
        >>> d.double()
        2

        """
        return self.value * 2

def test_suite():
    """Return a test suite."""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDummy1))
    suite.addTest(unittest.makeSuite(TestDummy2))
    return suite

if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = test_Install
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
#
"""Check an installed FunkLoad.

$Id$
"""
import os
import sys
import unittest
import commands

def winplatform_getstatusoutput(cmd):
    """A replacement for commands.getstatusoutput on the windows platform.
    commands.getstatusoutput only works on unix platforms.
    This only works with python2.6+ as the subprocess module is required.
    os.system provides the return code value but not the output streams of the
    commands.
    os.popen provides the output streams but no reliable easy to get return code.
    """
    try:
        import subprocess
    except ImportError:
        return None

    # create a new handle for the stdout pipe of cmd, and redirect cmd's stderr to stdout
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               shell=True, universal_newlines=True)
    stdoutdata, stderrdata = process.communicate()
    return (process.returncode, stdoutdata)


class TestInstall(unittest.TestCase):
    """Check installation."""

    def setUp(self):
        self.test_file = 'test_dummy.py'
        self.doctest_file = 'doctest_dummy.txt'

    def system(self, cmd, expected_code=0):
        """Execute a cmd and exit on fail return cmd output."""

        if sys.platform.lower().startswith('win'):
            ret = winplatform_getstatusoutput(cmd)
            if not ret:
                self.fail('Cannot run self.system on windows without the subprocess module (python 2.6)')
        else:
            ret = commands.getstatusoutput(cmd)

        if ret[0] != expected_code:
            self.fail("exec [%s] return code %s != %s output:\n%s" %
                      (cmd, ret[0], expected_code, ret[1]))
        return ret[1]

    def test_01_requires(self):
        try:
            import webunit
        except ImportError:
            self.fail('Missing Required module webunit')
        try:
            import funkload
        except ImportError:
            self.fail('Unable to import funkload module.')
        try:
            import docutils
        except ImportError:
            print ("WARNING: missing docutils module, "
                   "no HTML report available.")

        if sys.platform.lower().startswith('win'):
            ret = winplatform_getstatusoutput('wgnuplot --version')
            if not ret:
                self.fail('Cannot run self.system on windows without the subprocess module (python 2.6)')
        else:
            ret = commands.getstatusoutput('gnuplot --version')

        print ret[1]
        if ret[0]:
            print ("WARNING: gnuplot is missing, no charts available in "
                   "HTML reports.")

        from funkload.TestRunner import g_has_doctest
        if not g_has_doctest:
            print "WARNING: Python 2.4 is required to support doctest"


    def test_testloader(self):
        # check testrunner loader
        test_file = self.test_file
        # listing test
        output = self.system("fl-run-test %s --list" % test_file)
        self.assert_('test_dummy1_1' in output)
        self.assert_('test_dummy2_1' in output)
        self.assert_('test_dummy3_1' in output)

        # list a test suite
        output = self.system("fl-run-test %s test_suite --list" % test_file)
        self.assert_('test_dummy1_1' in output)
        self.assert_('test_dummy2_1' in output)
        self.assert_('test_dummy3_1' not in output)

        # list all test in a test case class
        output = self.system("fl-run-test %s TestDummy1 --list" % test_file)
        self.assert_('test_dummy1_1' in output)
        self.assert_('test_dummy1_2' in output)
        self.assert_('test_dummy2_1' not in output)

        # match regex
        output = self.system("fl-run-test %s --list -e dummy1_1" % test_file)
        self.assert_('test_dummy1_1' in output)
        self.assert_('test_dummy2_1' not in output)

        output = self.system("fl-run-test %s TestDummy1 --list -e dummy1_1" %
                             test_file)
        self.assert_('test_dummy1_1' in output)
        self.assert_('test_dummy2_1' not in output)

        output = self.system("fl-run-test %s --list -e 2$" % test_file)
        self.assert_('test_dummy1_2' in output)
        self.assert_('test_dummy2_2' in output)
        self.assert_('test_dummy1_1' not in output)
        self.assert_('test_dummy2_1' not in output)

        output = self.system("fl-run-test %s --list -e '!2$'" % test_file)
        self.assert_('test_dummy1_1' in output, output)
        self.assert_('test_dummy2_1' in output)
        self.assert_('test_dummy1_2' not in output)
        self.assert_('test_dummy2_2' not in output)


    def test_doctestloader(self):
        # check testrunner loader
        from funkload.TestRunner import g_has_doctest
        if not g_has_doctest:
            self.fail('Python 2.4 is required to support doctest')

        test_file = self.test_file
        # listing test
        output = self.system("fl-run-test %s --doctest --list" % test_file)
        self.assert_('Dummy.double' in output, 'missing doctest')

        # list a test suite
        output = self.system("fl-run-test %s  --doctest test_suite --list" % test_file)
        self.assert_('Dummy.double' not in output,
                     'doctest is not part of the suite')

        # list all test in a test case class
        output = self.system("fl-run-test %s --doctest TestDummy1 --list" % test_file)
        self.assert_('Dummy.double' not in output,
                     'doctest is not part of the testcase')

        # pure doctest
        doctest_file = self.doctest_file
        output = self.system("fl-run-test %s --doctest --list" % doctest_file)
        self.assert_(doctest_file.replace('.', '_') in output,
                     'no %s in output %s' % (doctest_file, output))

        # match regex
        output = self.system("fl-run-test %s --doctest --list -e dummy1_1" % test_file)


    def test_testrunner(self):
        # try to launch a test
        test_file = self.test_file
        output = self.system('fl-run-test %s TestDummy1 -v' % test_file)
        self.assert_('Ran 0 tests' not in output,
                     'not expected output:"""%s"""' % output)

        output = self.system('fl-run-test %s TestDummy2 -v' % test_file)
        self.assert_('Ran 0 tests' not in output,
                     'not expected output:"""%s"""' % output)
        # doctest
        from funkload.TestRunner import g_has_doctest
        if g_has_doctest:
            output = self.system('fl-run-test %s --doctest -e double -v' % test_file)
            self.assert_('Ran 0 tests' not in output,
                         'not expected output:"""%s"""' % output)

        # failing test
        output = self.system('fl-run-test %s TestDummy3 -v' % test_file,
                             expected_code=256)
        self.assert_('Ran 0 tests' not in output,
                     'not expected output:"""%s"""' % output)
        self.assert_('FAILED' in output)
        self.assert_('ERROR' in output)


    def test_xmlrpc(self):
        # windows os does not support the monitor server
        if not sys.platform.lower().startswith('win'):
            # extract demo example and run the xmlrpc test
            from tempfile import mkdtemp
            pwd = os.getcwd()
            tmp_path = mkdtemp('funkload')
            os.chdir(tmp_path)
            self.system('fl-install-demo')
            os.chdir(os.path.join(tmp_path, 'funkload-demo', 'xmlrpc'))
            self.system("fl-credential-ctl cred.conf restart")
            self.system("fl-monitor-ctl monitor.conf restart")
            self.system("fl-run-test -v test_Credential.py")
            self.system("fl-run-bench -c 1:10:20 -D 4 "
                        "test_Credential.py Credential.test_credential")
            self.system("fl-monitor-ctl monitor.conf stop")
            self.system("fl-credential-ctl cred.conf stop")
            self.system("fl-build-report credential-bench.xml --html")
            os.chdir(pwd)


def test_suite():
    """Return a test suite."""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInstall))
    return suite

if __name__ in ('main', '__main__'):
    unittest.main()

########NEW FILE########
__FILENAME__ = test_monitor_plugins
import unittest
import time
from ConfigParser import ConfigParser
from funkload.MonitorPlugins import MonitorPlugins

class TestMonitorPlugins(unittest.TestCase):
    default_plugins=['MonitorCPU', 'MonitorNetwork', 'MonitorMemFree', 'MonitorCUs']
    def test_register_default(self):
        """ Make sure all default plugins are loaded """
        p=MonitorPlugins()
        p.registerPlugins()
        plugins_loaded=p.MONITORS.keys()
        for plugin in self.default_plugins:
            self.assertTrue(plugin in plugins_loaded)

    def test_getStat(self):
        """ Make sure getStat does not raise any exception """
        p=MonitorPlugins()
        p.registerPlugins()

        for plugin in self.default_plugins:
            p.MONITORS[plugin].getStat()

    def test_network(self):
        """ Make sure self.interface is properly read from config in MonitorNetwork plugin """
        conf=ConfigParser()
        conf.add_section('server')
        conf.set('server', 'interface', 'eth9')

        p=MonitorPlugins(conf)
        p.registerPlugins()

        self.assertTrue(p.MONITORS['MonitorNetwork'].interface == 'eth9')

    def test_MonitorInfo(self):
        """ Make sure Monitor.MonitorInfo still works with plugins """
        from funkload.Monitor import MonitorInfo
        p=MonitorPlugins()
        p.registerPlugins()
        m=MonitorInfo('somehost', p)
        self.assertTrue(m.host=='somehost')

    def test_MonitorThread(self):
        """ Make sure Monitor.MonitorThread still works with plugins """
        from funkload.Monitor import MonitorThread

        p=MonitorPlugins()
        p.registerPlugins()

        records=[]
        monitor = MonitorThread(records, p, 'localhost', 1)
        monitor.start()
        monitor.startRecord()
        time.sleep(3)
        monitor.stopRecord()
        monitor.stop()

        self.assertTrue(len(records)>0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_rtfeedback
import unittest
import time

from funkload import rtfeedback
import zmq


class TestFeedback(unittest.TestCase):

    def test_feedback(self):

        context = zmq.Context.instance()

        pub = rtfeedback.FeedbackPublisher(context=context)
        pub.start()

        msgs = []

        def _msg(msg):
            msgs.append(msg)

        sub = rtfeedback.FeedbackSubscriber(handler=_msg, context=context)
        sub.start()

        sender = rtfeedback.FeedbackSender(context=context)

        for i in range(10):
            sender.test_done({'result': 'success'})

        time.sleep(.1)
        self.assertEqual(len(msgs), 10)

########NEW FILE########
__FILENAME__ = utils
# (C) Copyright 2005-2010 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
# Contributors: Goutham Bhat
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""FunkLoad common utils.

$Id: utils.py 24649 2005-08-29 14:20:19Z bdelbosc $
"""
import os
import sys
import time
import logging
from time import sleep
from socket import error as SocketError
from xmlrpclib import ServerProxy
import pkg_resources
import tarfile
import tempfile


def thread_sleep(seconds=0):
    """Sleep seconds."""
    # looks like python >= 2.5 does not need a minimal sleep to let thread
    # working properly
    if seconds:
        sleep(seconds)

# ------------------------------------------------------------
# semaphores
#
g_recording = False

def recording():
    """A semaphore to tell the running threads when to begin recording."""
    global g_recording
    return g_recording

def set_recording_flag(value):
    """Enable recording."""
    global g_recording
    g_recording = value

# ------------------------------------------------------------
# daemon
#
# See the Chad J. Schroeder example for a full explanation
# this version does not chdir to '/' to keep relative path
def create_daemon():
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.
    """
    try:
        pid = os.fork()
    except OSError, msg:
        raise Exception, "%s [%d]" % (msg.strerror, msg.errno)
    if (pid == 0):
        os.setsid()
        try:
            pid = os.fork()
        except OSError, msg:
            raise Exception, "%s [%d]" % (msg.strerror, msg.errno)
        if (pid == 0):
            os.umask(0)
        else:
            os._exit(0)
    else:
        sleep(.5)
        os._exit(0)
    import resource
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = 1024
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:
            pass
    os.open('/dev/null', os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)
    return(0)


# ------------------------------------------------------------
# meta method name encodage
#
MMN_SEP = ':'                           # meta method name separator

def mmn_is_bench(meta_method_name):
    """Is it a meta method name ?."""
    return meta_method_name.count(MMN_SEP) and True or False

def mmn_encode(method_name, cycle, cvus, thread_id):
    """Encode a extra information into a method_name."""
    return MMN_SEP.join((method_name, str(cycle), str(cvus), str(thread_id)))

def mmn_decode(meta_method_name):
    """Decode a meta method name."""
    if mmn_is_bench(meta_method_name):
        method_name, cycle, cvus, thread_id = meta_method_name.split(MMN_SEP)
        return (method_name, int(cycle), int(cvus), int(thread_id))
    else:
        return (meta_method_name, 1, 0, 1)

# ------------------------------------------------------------
# logging
#
def get_default_logger(log_to, log_path=None, level=logging.DEBUG,
                       name='FunkLoad'):
    """Get a logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        # already setup
        return logger
    if log_path:
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception, e:
                raise Exception("%s, (%s) (%s)" % (e, log_dir, log_path))
    if log_to.count("console"):
        hdlr = logging.StreamHandler()
        logger.addHandler(hdlr)
    if log_to.count("file") and log_path:
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s')
        hdlr = logging.FileHandler(log_path)
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
    if log_to.count("xml") and log_path:
        if os.access(log_path, os.F_OK):
            os.rename(log_path, log_path + '.bak-' + str(int(time.time())))
        hdlr = logging.FileHandler(log_path)
        logger.addHandler(hdlr)
    logger.setLevel(level)
    return logger


def close_logger(name):
    """Close the logger."""
    logger = logging.getLogger(name)
    for hdlr in logger.handlers:
        logger.removeHandler(hdlr)


def trace(message):
    """Simple print to stdout

    Not thread safe."""
    sys.stdout.write(message)
    sys.stdout.flush()


# ------------------------------------------------------------
# xmlrpc
#
def xmlrpc_get_seq(host, port):
    """Get credential thru xmlrpc credential_server."""
    url = "http://%s:%s" % (host, port)
    server = ServerProxy(url, allow_none=True)
    try:
        return server.getSeq()
    except SocketError:
        raise SocketError(
            'No Credential server reachable at %s, use fl-credential-ctl '
            'to start the credential server.' % url)

def xmlrpc_get_credential(host, port, group=None):
    """Get credential thru xmlrpc credential_server."""
    url = "http://%s:%s" % (host, port)
    server = ServerProxy(url, allow_none=True)
    try:
        return server.getCredential(group)
    except SocketError:
        raise SocketError(
            'No Credential server reachable at %s, use fl-credential-ctl '
            'to start the credential server.' % url)

def xmlrpc_list_groups(host, port):
    """Get list of groups thru xmlrpc credential_server."""
    url = "http://%s:%s" % (host, port)
    server = ServerProxy(url)
    try:
        return server.listGroups()
    except SocketError:
        raise SocketError(
            'No Credential server reachable at %s, use fl-credential-ctl '
            'to start the credential server.' % url)

def xmlrpc_list_credentials(host, port, group=None):
    """Get list of users thru xmlrpc credential_server."""
    url = "http://%s:%s" % (host, port)
    server = ServerProxy(url, allow_none=True)
    try:
        return server.listCredentials(group)
    except SocketError:
        raise SocketError(
            'No Credential server reachable at %s, use fl-credential-ctl '
            'to start the credential server.' % url)



# ------------------------------------------------------------
# misc
#
def get_version():
    """Retrun the FunkLoad package version."""
    from pkg_resources import get_distribution
    return get_distribution('funkload').version


_COLOR = {'green': "\x1b[32;01m",
          'red': "\x1b[31;01m",
          'reset': "\x1b[0m"
          }

def red_str(text):
    """Return red text."""
    global _COLOR
    return _COLOR['red'] + text + _COLOR['reset']

def green_str(text):
    """Return green text."""
    global _COLOR
    return _COLOR['green'] + text + _COLOR['reset']

def is_html(text):
    """Simple check that return True if the text is an html page."""
    if text is not None and '<html' in text[:300].lower():
        return True
    return False


# credits goes to Subways and Django folks
class BaseFilter(object):
    """Base filter."""
    def __ror__(self, other):
        return other  # pass-thru

    def __call__(self, other):
        return other | self


class truncate(BaseFilter):
    """Middle truncate string up to length."""
    def __init__(self, length=40, extra='...'):
        self.length = length
        self.extra = extra

    def __ror__(self, other):
        if len(other) > self.length:
            mid_size = (self.length - 3) / 2
            other = other[:mid_size] + self.extra + other[-mid_size:]
        return other


def is_valid_html(html=None, file_path=None, accept_warning=False):
    """Ask tidy if the html is valid.

    Return a tuple (status, errors)
    """
    if not file_path:
        fd, file_path = mkstemp(prefix='fl-tidy', suffix='.html')
        os.write(fd, html)
        os.close(fd)
    tidy_cmd = 'tidy -errors %s' % file_path
    ret, output = getstatusoutput(tidy_cmd)
    status = False
    if ret == 0:
        status = True
    elif ret == 256:
        # got warnings
        if accept_warning:
            status = True
    elif ret > 512:
        if 'command not found' in output:
            raise RuntimeError('tidy command not found, please install tidy.')
        raise RuntimeError('Executing [%s] return: %s ouput: %s' %
                           (tidy_cmd, ret, output))
    return status, output

class Data:
    '''Simple "sentinel" class that lets us identify user data
    and content type in POST'''
    def __init__(self, content_type, data):
        self.content_type = content_type
        self.data = data

    def __cmp__(self, other):
        diff = cmp(self.content_type, other.content_type)
        if not diff:
            diff = cmp(self.data, other.data)
        return diff

    def __repr__(self):
        return "[User data " + str(self.content_type) + "]"


def get_virtualenv_script():
    """
    returns the path of the virtualenv.py script that is
    installed in the system. if it doesn't exist returns
    None.
    """
    pkg = pkg_resources.get_distribution('virtualenv')
    script_path =  os.path.join( pkg.location, 'virtualenv.py')

    if os.path.isfile( script_path ):
        return script_path
    else:
        return None


def package_tests(module_file):
    """
    this function will basically allow you to create a tarball
    of the current working directory (of tests) for transport over
    to a remote machine. It uses a few heuristics to avoid packaging
    log files.
    """
    exclude_func = lambda filename: filename.find(".log")>=0 or\
                                    filename.find(".bak")>=0 or\
                                    filename.find(".pyc")>=0 or\
                                    filename.find(".gplot")>=0 or\
                                    filename.find(".png")>=0 or\
                                    filename.find(".data")>=0 or\
                                    filename.find(".xml")>=0 or\
                                    os.path.split(filename)[1] == "bin" or\
                                    os.path.split(filename)[1] == "lib"

    _path = tempfile.mktemp(suffix='.tar')
    import hashlib
    _targetdir = hashlib.md5(os.path.splitext(module_file)[0]).hexdigest()
    _directory = os.path.split(os.path.abspath(module_file))[0]
    _tar = tarfile.TarFile( _path  ,'w')
    _tar.add ( _directory, _targetdir , exclude = exclude_func )
    _tar.close()
    return _path, _targetdir

def extract_token(text, tag_start, tag_end):
    """Extract a token from text, using the first occurence of
    tag_start and ending with tag_end. Return None if tags are not
    found."""
    start = text.find(tag_start)
    end = text.find(tag_end, start + len(tag_start))
    if start < 0 or end < 0:
        return None
    return text[start + len(tag_start):end]

########NEW FILE########
__FILENAME__ = XmlRpcBase
# (C) Copyright 2005 Nuxeo SAS <http://nuxeo.com>
# Author: bdelbosc@nuxeo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
"""Base class to build XML RPC daemon server.

$Id$
"""
import sys, os
from socket import error as SocketError
from time import sleep
from ConfigParser import ConfigParser, NoOptionError
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy
import logging
from optparse import OptionParser, TitledHelpFormatter

from utils import create_daemon, get_default_logger, close_logger
from utils import trace, get_version


def is_server_running(host, port):
    """Check if the XML/RPC server is running checking getStatus RPC."""
    server = ServerProxy("http://%s:%s" % (host, port))
    try:
        server.getStatus()
    except SocketError:
        return False
    return True



# ------------------------------------------------------------
# rpc to manage the server
#
class MySimpleXMLRPCServer(SimpleXMLRPCServer):
    """SimpleXMLRPCServer with allow_reuse_address."""
    # this property set SO_REUSEADDR which tells the operating system to allow
    # code to connect to a socket even if it's waiting for other potential
    # packets
    allow_reuse_address = True


# ------------------------------------------------------------
# Server
#
class XmlRpcBaseServer:
    """The base class for xml rpc server."""

    usage = """%prog [options] config_file

Start %prog XML/RPC daemon.
"""
    server_name = None
    # list RPC Methods
    method_names = ['stopServer', 'getStatus']

    def __init__(self, argv=None):
        if self.server_name is None:
            self.server_name = self.__class__.__name__
        if argv is None:
            argv = sys.argv
        conf_path, options = self.parseArgs(argv)
        self.default_log_path = self.server_name + '.log'
        self.default_pid_path = self.server_name + '.pid'
        self.server = None
        self.quit = False

        # read conf
        conf = ConfigParser()
        conf.read(conf_path)
        self.conf_path = conf_path
        self.host = conf.get('server', 'host')
        self.port = conf.getint('server', 'port')
        try:
            self.pid_path = conf.get('server', 'pid_path')
        except NoOptionError:
            self.pid_path = self.default_pid_path
        try:
            log_path = conf.get('server', 'log_path')
        except NoOptionError:
            log_path = self.default_log_path

        if is_server_running(self.host, self.port):
            trace("Server already running on %s:%s." % (self.host, self.port))
            sys.exit(0)

        trace('Starting %s server at http://%s:%s/' % (self.server_name,
                                                       self.host, self.port))
        # init logger
        if options.verbose:
            level = logging.DEBUG
        else:
            level = logging.INFO
        if options.debug:
            log_to = 'file console'
        else:
            log_to = 'file'
        self.logger = get_default_logger(log_to, log_path, level=level,
                                         name=self.server_name)
        # subclass init
        self._init_cb(conf, options)

        # daemon mode
        if not options.debug:
            trace(' as daemon.\n')
            close_logger(self.server_name)
            create_daemon()
            # re init the logger
            self.logger = get_default_logger(log_to, log_path, level=level,
                                             name=self.server_name)
        else:
            trace(' in debug mode.\n')

        # init rpc
        self.initServer()

    def _init_cb(self, conf, options):
        """init procedure intend to be implemented by subclasses.

        This method is called before to switch in daemon mode.
        conf is a ConfigParser object."""
        pass

    def logd(self, message):
        """Debug log."""
        self.logger.debug(message)

    def log(self, message):
        """Log information."""
        self.logger.info(message)

    def parseArgs(self, argv):
        """Parse programs args."""
        parser = OptionParser(self.usage, formatter=TitledHelpFormatter(),
                              version="FunkLoad %s" % get_version())
        parser.add_option("-v", "--verbose", action="store_true",
                          help="Verbose output")
        parser.add_option("-d", "--debug", action="store_true",
                          help="debug mode, server is run in forground")

        options, args = parser.parse_args(argv)
        if len(args) != 2:
            parser.error("Missing configuration file argument")
        return args[1], options

    def initServer(self):
        """init the XMLR/PC Server."""
        self.log("Init XML/RPC server %s:%s." % (self.host, self.port))
        server = MySimpleXMLRPCServer((self.host, self.port))
        for method_name in self.method_names:
            self.logd('register %s' % method_name)
            server.register_function(getattr(self, method_name))
        self.server = server

    def run(self):
        """main server loop."""
        server = self.server
        pid = os.getpid()
        open(self.pid_path, "w").write(str(pid))
        self.log("XML/RPC server pid=%i running." % pid)
        while not self.quit:
            server.handle_request()
        sleep(.5)
        server.server_close()
        self.log("XML/RPC server pid=%i stopped." % pid)
        os.remove(self.pid_path)

    __call__ = run

    # RPC
    #
    def stopServer(self):
        """Stop the server."""
        self.log("stopServer request.")
        self.quit = True
        return 1

    def getStatus(self):
        """Return a status."""
        self.logd("getStatus request.")
        return "%s running pid = %s" % (self.server_name, os.getpid())





# ------------------------------------------------------------
# Controller
#
class XmlRpcBaseController:
    """An XML/RPC controller."""

    usage = """%prog config_file action

action can be: start|startd|stop|restart|status|test

Execute action on the XML/RPC server.
"""
    # the server class
    server_class = XmlRpcBaseServer

    def __init__(self, argv=None):
        if argv is None:
            argv = sys.argv
        conf_path, self.action, options = self.parseArgs(argv)
        # read conf
        conf = ConfigParser()
        conf.read(conf_path)
        self.host = conf.get('server', 'host')
        self.conf_path = conf_path
        self.port = conf.getint('server', 'port')
        self.url = 'http://%s:%s/' % (self.host, self.port)
        self.quiet = options.quiet
        self.verbose = options.verbose
        self.server = ServerProxy(self.url)


    def parseArgs(self, argv):
        """Parse programs args."""
        parser = OptionParser(self.usage, formatter=TitledHelpFormatter(),
                              version="FunkLoad %s" % get_version())
        parser.add_option("-q", "--quiet", action="store_true",
                          help="Suppress console output")
        parser.add_option("-v", "--verbose", action="store_true",
                          help="Verbose mode (log-level debug)")
        options, args = parser.parse_args(argv)
        if len(args) != 3:
            parser.error("Missing argument")
        return args[1], args[2], options

    def log(self, message, force=False):
        """Log a message."""
        if force or not self.quiet:
            trace(str(message))

    def startServer(self, debug=False):
        """Start an XML/RPC server."""
        argv = ['cmd', self.conf_path]
        if debug:
            argv.append('-dv')
        elif self.verbose:
            argv.append('-v')
        daemon = self.server_class(argv)
        daemon.run()

    def __call__(self, action=None):
        """Call the xml rpc action"""
        server = self.server
        if action is None:
            action = self.action
        is_running = is_server_running(self.host, self.port)
        if action == 'status':
            if is_running:
                ret = server.getStatus()
                self.log('%s %s.\n' % (self.url, ret))
            else:
                self.log('No server reachable at %s.\n' % self.url)
            return 0
        elif action in ('stop', 'restart'):
            if is_running:
                ret = server.stopServer()
                self.log('Server %s is stopped.\n' % self.url)
                is_running = False
            elif action == 'stop':
                self.log('No server reachable at %s.\n' % self.url)
            if action == 'restart':
                self('start')
        elif 'start' in action:
            if is_running:
                self.log('Server %s is already running.\n' % self.url)
            else:
                return self.startServer(action=='startd')
        elif not is_running:
            self.log('No server reachable at %s.\n' % self.url)
            return -1
        elif action == 'reload':
            ret = server.reloadConf()
            self.log('done\n')
        elif action == 'test':
            return self.test()
        else:
            raise NotImplementedError('Unknow action %s' % action)
        return 0

    # this method is done to be overriden in sub classes
    def test(self):
        """Testing the XML/RPC.

        Must return an exit code, 0 for success.
        """
        ret = self.server.getStatus()
        self.log('Testing getStatus: %s\n' % ret)
        return 0

def main():
    """Main"""
    ctl = XmlRpcBaseController()
    ret = ctl()
    sys.exit(ret)

if __name__ == '__main__':
    main()

########NEW FILE########
