__FILENAME__ = collections
# -*- coding: utf-8 -*-
"""
Compatibility of :module:`collections` between different Python versions.
"""

from __future__ import absolute_import
import warnings

try:
    # -- SINCE: Python2.7
    from collections import OrderedDict
except ImportError:     # pragma: no cover
    try:
        # -- BACK-PORTED FOR: Python 2.4 .. 2.6
        from ordereddict import OrderedDict
    except ImportError:
        message = "collections.OrderedDict is missing: Install 'ordereddict'."
        warnings.warn(message)
        # -- BACKWARD-COMPATIBLE: Better than nothing (for behave use case).
        OrderedDict = dict

########NEW FILE########
__FILENAME__ = importlib
# -*- coding: utf-8 -*-
"""
importlib was introduced in python2.7, python3.2...
"""

try:
    from importlib import import_module
except ImportError:
    """Backport of importlib.import_module from 3.x."""
    # While not critical (and in no way guaranteed!), it would be nice to keep this
    # code compatible with Python 2.3.
    import sys

    def _resolve_name(name, package, level):
        """Return the absolute name of the module to be imported."""
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in xrange(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                  "package")
        return "%s.%s" % (package[:dot], name)


    def import_module(name, package=None):
        """Import a module.

        The 'package' argument is required when performing a relative import. It
        specifies the package to use as the anchor point from which to resolve the
        relative import to an absolute import.

        """
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]

########NEW FILE########
__FILENAME__ = os_path
# -*- coding: utf-8 -*-
"""
Compatibility of :module:`os.path` between different Python versions.
"""

import os.path

relpath = getattr(os.path, "relpath", None)
if relpath is None: # pragma: no cover
    # -- Python2.5 doesn't know about relpath
    def relpath(path, start=os.path.curdir):
        """
        Return a relative version of a path
        BASED-ON: Python2.7
        """
        if not path:
            raise ValueError("no path specified")

        start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
        path_list  = [x for x in os.path.abspath(path).split(os.path.sep) if x]
        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.path.curdir
        return os.path.join(*rel_list)

########NEW FILE########
__FILENAME__ = configuration
# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse
import logging
import shlex
from six.moves import configparser

from behave.model import FileLocation, ScenarioOutline
from behave.reporter.junit import JUnitReporter
from behave.reporter.summary import SummaryReporter
from behave.tag_expression import TagExpression
from behave.formatter.base import StreamOpener
from behave.formatter.formatters import formatters as registered_formatters


class Unknown(object): pass

class LogLevel(object):
    names = [
         "NOTSET", "CRITICAL", "FATAL", "ERROR",
         "WARNING", "WARN", "INFO", "DEBUG",
    ]

    @staticmethod
    def parse(levelname, unknown_level=None):
        """
        Convert levelname into a numeric log level.

        :param levelname: Logging levelname (as string)
        :param unknown_level: Used if levelname is unknown (optional).
        :return: Numeric log-level or unknown_level, if levelname is unknown.
        """
        return getattr(logging, levelname.upper(), unknown_level)

    @classmethod
    def parse_type(cls, levelname):
        level = cls.parse(levelname, Unknown)
        if level is Unknown:
            message = "%s is unknown, use: %s" % \
                      (levelname, ", ".join(cls.names[1:]))
            raise argparse.ArgumentTypeError(message)
        return level

    @staticmethod
    def to_string(level):
        return logging.getLevelName(level)


class ConfigError(Exception):
    pass


options = [
    (('-c', '--no-color'),
     dict(action='store_false', dest='color',
          help="Disable the use of ANSI color escapes.")),

    (('--color',),
     dict(action='store_true', dest='color',
          help="""Use ANSI color escapes. This is the default
                  behaviour. This switch is used to override a
                  configuration file setting.""")),

    (('-d', '--dry-run'),
     dict(action='store_true',
          help="Invokes formatters without executing the steps.")),

    (('-e', '--exclude'),
     dict(metavar="PATTERN", dest='exclude_re',
          help="""Don't run feature files matching regular expression
                  PATTERN.""")),

    (('-i', '--include'),
     dict(metavar="PATTERN", dest='include_re',
          help="Only run feature files matching regular expression PATTERN.")),

    (('--no-junit',),
     dict(action='store_false', dest='junit',
          help="Don't output JUnit-compatible reports.")),

    (('--junit',),
     dict(action='store_true',
          help="""Output JUnit-compatible reports.
                  When junit is enabled, all stdout and stderr
                  will be redirected and dumped to the junit report,
                  regardless of the '--capture' and '--no-capture' options.
                  """)),

    (('--junit-directory',),
     dict(metavar='PATH', dest='junit_directory',
          default='reports',
          help="""Directory in which to store JUnit reports.""")),

    ((),  # -- CONFIGFILE only
     dict(dest='default_format',
          help="Specify default formatter (default: pretty).")),


    (('-f', '--format'),
     dict(action='append',
          help="""Specify a formatter. If none is specified the default
                  formatter is used. Pass '--format help' to get a
                  list of available formatters.""")),

    ((),  # -- CONFIGFILE only
     dict(dest='scenario_outline_annotation_schema',
          help="""Specify name annotation schema for scenario outline
                  (default="{name} -- @{row.id} {examples.name}").""")),

#    (('-g', '--guess'),
#     dict(action='store_true',
#          help="Guess best match for ambiguous steps.")),

    (('-k', '--no-skipped'),
     dict(action='store_false', dest='show_skipped',
          help="Don't print skipped steps (due to tags).")),

    (('--show-skipped',),
     dict(action='store_true',
          help="""Print skipped steps.
                  This is the default behaviour. This switch is used to
                  override a configuration file setting.""")),

    (('--no-snippets',),
     dict(action='store_false', dest='show_snippets',
          help="Don't print snippets for unimplemented steps.")),
    (('--snippets',),
     dict(action='store_true', dest='show_snippets',
          help="""Print snippets for unimplemented steps.
                  This is the default behaviour. This switch is used to
                  override a configuration file setting.""")),

    (('-m', '--no-multiline'),
     dict(action='store_false', dest='show_multiline',
          help="""Don't print multiline strings and tables under
                  steps.""")),

    (('--multiline', ),
     dict(action='store_true', dest='show_multiline',
          help="""Print multiline strings and tables under steps.
                  This is the default behaviour. This switch is used to
                  override a configuration file setting.""")),

    (('-n', '--name'),
     dict(action="append",
          help="""Only execute the feature elements which match part
                  of the given name. If this option is given more
                  than once, it will match against all the given
                  names.""")),

    (('--no-capture',),
     dict(action='store_false', dest='stdout_capture',
          help="""Don't capture stdout (any stdout output will be
                  printed immediately.)""")),

    (('--capture',),
     dict(action='store_true', dest='stdout_capture',
          help="""Capture stdout (any stdout output will be
                  printed if there is a failure.)
                  This is the default behaviour. This switch is used to
                  override a configuration file setting.""")),

    (('--no-capture-stderr',),
     dict(action='store_false', dest='stderr_capture',
          help="""Don't capture stderr (any stderr output will be
                  printed immediately.)""")),

    (('--capture-stderr',),
     dict(action='store_true', dest='stderr_capture',
          help="""Capture stderr (any stderr output will be
                  printed if there is a failure.)
                  This is the default behaviour. This switch is used to
                  override a configuration file setting.""")),

    (('--no-logcapture',),
     dict(action='store_false', dest='log_capture',
          help="""Don't capture logging. Logging configuration will
                  be left intact.""")),

    (('--logcapture',),
     dict(action='store_true', dest='log_capture',
          help="""Capture logging. All logging during a step will be captured
                  and displayed in the event of a failure.
                  This is the default behaviour. This switch is used to
                  override a configuration file setting.""")),

    (('--logging-level',),
     dict(type=LogLevel.parse_type,
          help="""Specify a level to capture logging at. The default
                  is INFO - capturing everything.""")),

    (('--logging-format',),
     dict(help="""Specify custom format to print statements. Uses the
                  same format as used by standard logging handlers. The
                  default is '%%(levelname)s:%%(name)s:%%(message)s'.""")),

    (('--logging-datefmt',),
     dict(help="""Specify custom date/time format to print
                  statements.
                  Uses the same format as used by standard logging
                  handlers.""")),

    (('--logging-filter',),
     dict(help="""Specify which statements to filter in/out. By default,
                  everything is captured. If the output is too verbose, use
                  this option to filter out needless output.
                  Example: --logging-filter=foo will capture statements issued
                  ONLY to foo or foo.what.ever.sub but not foobar or other
                  logger. Specify multiple loggers with comma:
                  filter=foo,bar,baz.
                  If any logger name is prefixed with a minus, eg filter=-foo,
                  it will be excluded rather than included.""",
          config_help="""Specify which statements to filter in/out. By default,
                         everything is captured. If the output is too verbose,
                         use this option to filter out needless output.
                         Example: ``logging_filter = foo`` will capture
                         statements issued ONLY to "foo" or "foo.what.ever.sub"
                         but not "foobar" or other logger. Specify multiple
                         loggers with comma: ``logging_filter = foo,bar,baz``.
                         If any logger name is prefixed with a minus, eg
                         ``logging_filter = -foo``, it will be excluded rather
                         than included.""")),

    (('--logging-clear-handlers',),
     dict(action='store_true',
          help="Clear all other logging handlers.")),

    (('--no-summary',),
     dict(action='store_false', dest='summary',
          help="""Don't display the summary at the end of the run.""")),

    (('--summary',),
     dict(action='store_true', dest='summary',
          help="""Display the summary at the end of the run.""")),

    (('-o', '--outfile'),
     dict(action='append', dest='outfiles', metavar='FILE',
          help="Write to specified file instead of stdout.")),

    ((),  # -- CONFIGFILE only
     dict(action='append', dest='paths',
          help="Specify default feature paths, used when none are provided.")),

    (('-q', '--quiet'),
     dict(action='store_true',
          help="Alias for --no-snippets --no-source.")),

    (('-s', '--no-source'),
     dict(action='store_false', dest='show_source',
          help="""Don't print the file and line of the step definition with the
                  steps.""")),

    (('--show-source',),
     dict(action='store_true', dest='show_source',
          help="""Print the file and line of the step
                  definition with the steps. This is the default
                  behaviour. This switch is used to override a
                  configuration file setting.""")),

    (('--stop',),
     dict(action='store_true',
          help='Stop running tests at the first failure.')),

    # -- DISABLE-UNUSED-OPTION: Not used anywhere.
    # (('-S', '--strict'),
    # dict(action='store_true',
    #    help='Fail if there are any undefined or pending steps.')),

    (('-t', '--tags'),
     dict(action='append', metavar='TAG_EXPRESSION',
          help="""Only execute features or scenarios with tags
                  matching TAG_EXPRESSION. Pass '--tags-help' for
                  more information.""",
          config_help="""Only execute certain features or scenarios based
                         on the tag expression given. See below for how to code
                         tag expressions in configuration files.""")),

    (('-T', '--no-timings'),
     dict(action='store_false', dest='show_timings',
          help="""Don't print the time taken for each step.""")),

    (('--show-timings',),
     dict(action='store_true', dest='show_timings',
          help="""Print the time taken, in seconds, of each step after the
                  step has completed. This is the default behaviour. This
                  switch is used to override a configuration file
                  setting.""")),

    (('-v', '--verbose'),
     dict(action='store_true',
          help='Show the files and features loaded.')),

    (('-w', '--wip'),
     dict(action='store_true',
          help="""Only run scenarios tagged with "wip". Additionally: use the
                  "plain" formatter, do not capture stdout or logging output
                  and stop at the first failure.""")),

    (('-x', '--expand'),
     dict(action='store_true',
          help="Expand scenario outline tables in output.")),

    (('--lang',),
     dict(metavar='LANG',
          help="Use keywords for a language other than English.")),

    (('--lang-list',),
     dict(action='store_true',
          help="List the languages available for --lang.")),

    (('--lang-help',),
     dict(metavar='LANG',
          help="List the translations accepted for one language.")),

    (('--tags-help',),
     dict(action='store_true',
          help="Show help for tag expressions.")),

    (('--version',),
     dict(action='store_true', help="Show version.")),
]

# -- OPTIONS: With raw value access semantics in configuration file.
raw_value_options = frozenset([
    "logging_format",
    "logging_datefmt",
    # -- MAYBE: "scenario_outline_annotation_schema",
])

def read_configuration(path):
    cfg = configparser.SafeConfigParser()
    cfg.read(path)
    cfgdir = os.path.dirname(path)
    result = {}
    for fixed, keywords in options:
        if 'dest' in keywords:
            dest = keywords['dest']
        else:
            for opt in fixed:
                if opt.startswith('--'):
                    dest = opt[2:].replace('-', '_')
                else:
                    assert len(opt) == 2
                    dest = opt[1:]
        if dest in 'tags_help lang_list lang_help version'.split():
            continue
        if not cfg.has_option('behave', dest):
            continue
        action = keywords.get('action', 'store')
        if action == 'store':
            use_raw_value = dest in raw_value_options
            result[dest] = cfg.get('behave', dest, use_raw_value)
        elif action in ('store_true', 'store_false'):
            result[dest] = cfg.getboolean('behave', dest)
        elif action == 'append':
            result[dest] = \
                [s.strip() for s in cfg.get('behave', dest).splitlines()]
        else:
            raise ValueError('action "%s" not implemented' % action)

    if 'format' in result:
        # -- OPTIONS: format/outfiles are coupled in configuration file.
        formatters = result['format']
        formatter_size = len(formatters)
        outfiles = result.get('outfiles', [])
        outfiles_size = len(outfiles)
        if outfiles_size < formatter_size:
            for formatter_name in formatters[outfiles_size:]:
                outfile = "%s.output" % formatter_name
                outfiles.append(outfile)
            result['outfiles'] = outfiles
        elif len(outfiles) > formatter_size:
            print "CONFIG-ERROR: Too many outfiles (%d) provided." % outfiles_size
            result['outfiles'] = outfiles[:formatter_size]

    for paths_name in ('paths', 'outfiles'):
        if paths_name in result:
            # -- Evaluate relative paths relative to configfile location.
            # NOTE: Absolute paths are preserved by os.path.join().
            paths = result[paths_name]
            result[paths_name] = \
                [os.path.normpath(os.path.join(cfgdir, p)) for p in paths]

    return result


def load_configuration(defaults, verbose=False):
    paths = ['./', os.path.expanduser('~')]
    if sys.platform in ('cygwin', 'win32') and 'APPDATA' in os.environ:
        paths.append(os.path.join(os.environ['APPDATA']))

    for path in paths:
        for filename in 'behave.ini .behaverc'.split():
            filename = os.path.join(path, filename)
            if os.path.isfile(filename):
                if verbose:
                    print 'Loading config defaults from "%s"' % filename
                defaults.update(read_configuration(filename))

    if verbose:
        print 'Using defaults:'
        for k, v in defaults.items():
            print '%15s %s' % (k, v)


# construct the parser
#usage = "%(prog)s [options] [ [FILE|DIR|URL][:LINE[:LINE]*] ]+"
usage = "%(prog)s [options] [ [DIR|FILE|FILE:LINE] ]+"
description = """\
Run a number of feature tests with behave."""
more = """
EXAMPLES:
behave features/
behave features/one.feature features/two.feature
behave features/one.feature:10
behave @features.txt
"""
parser = argparse.ArgumentParser(usage=usage, description=description)
for fixed, keywords in options:
    if not fixed:
        continue    # -- CONFIGFILE only.
    if 'config_help' in keywords:
        keywords = dict(keywords)
        del keywords['config_help']
    parser.add_argument(*fixed, **keywords)
parser.add_argument('paths', nargs='*',
                help='Feature directory, file or file location (FILE:LINE).')


class Configuration(object):
    defaults = dict(
        color=sys.platform != 'win32',
        show_snippets=True,
        show_skipped=True,
        dry_run=False,
        show_source=True,
        show_timings=True,
        stdout_capture=True,
        stderr_capture=True,
        log_capture=True,
        logging_format='%(levelname)s:%(name)s:%(message)s',
        logging_level=logging.INFO,
        summary=True,
        junit=False,
        # -- SPECIAL:
        default_format="pretty",   # -- Used when no formatters are configured.
        scenario_outline_annotation_schema=u"{name} -- @{row.id} {examples.name}"
    )

    def __init__(self, command_args=None, load_config=True, verbose=None,
                 **kwargs):
        """
        Constructs a behave configuration object.
          * loads the configuration defaults (if needed).
          * process the command-line args
          * store the configuration results

        :param command_args: Provide command args (as sys.argv).
            If command_args is None, sys.argv[1:] is used.
        :type command_args: list<str>, str
        :param load_config: Indicate if configfile should be loaded (=true)
        :param verbose: Indicate if diagnostic output is enabled
        :param kwargs:  Used to hand-over/overwrite default values.
        """
        if command_args is None:
            command_args = sys.argv[1:]
        elif isinstance(command_args, basestring):
            if isinstance(command_args, unicode):
                command_args = command_args.encode("utf-8")
            command_args = shlex.split(command_args)
        if verbose is None:
            # -- AUTO-DISCOVER: Verbose mode from command-line args.
            verbose = ('-v' in command_args) or ('--verbose' in command_args)

        defaults = self.defaults.copy()
        for name, value in kwargs.items():
            defaults[name] = value
        self.defaults = defaults
        self.formatters = []
        self.reporters = []
        self.name_re = None
        self.outputs = []
        self.include_re = None
        self.exclude_re = None
        self.scenario_outline_annotation_schema = None
        if load_config:
            load_configuration(self.defaults, verbose=verbose)
        parser.set_defaults(**self.defaults)
        args = parser.parse_args(command_args)
        for key, value in args.__dict__.items():
            if key.startswith('_'):
                continue
            setattr(self, key, value)

        self.paths = [os.path.normpath(path) for path in self.paths]
        if not args.outfiles:
            self.outputs.append(StreamOpener(stream=sys.stdout))
        else:
            for outfile in args.outfiles:
                if outfile and outfile != '-':
                    self.outputs.append(StreamOpener(outfile))
                else:
                    self.outputs.append(StreamOpener(stream=sys.stdout))

        if self.wip:
            # Only run scenarios tagged with "wip".
            # Additionally:
            #  * use the "plain" formatter (per default)
            #  * do not capture stdout or logging output and
            #  * stop at the first failure.
            self.default_format = "plain"
            self.tags = ["wip"]
            self.color = False
            self.stop = True
            self.log_capture = False
            self.stdout_capture = False

        self.tags = TagExpression(self.tags or [])

        if self.quiet:
            self.show_source = False
            self.show_snippets = False

        if self.exclude_re:
            self.exclude_re = re.compile(self.exclude_re)

        if self.include_re:
            self.include_re = re.compile(self.include_re)
        if self.name:
            # -- SELECT: Scenario-by-name, build regular expression.
            self.name_re = self.build_name_re(self.name)

        if self.junit:
            # Buffer the output (it will be put into Junit report)
            self.stdout_capture = True
            self.stderr_capture = True
            self.log_capture = True
            self.reporters.append(JUnitReporter(self))
        if self.summary:
            self.reporters.append(SummaryReporter(self))

        unknown_formats = self.collect_unknown_formats()
        if unknown_formats:
            parser.error("format=%s is unknown" % ", ".join(unknown_formats))

        self.setup_model()

    def collect_unknown_formats(self):
        unknown_formats = []
        if self.format:
            for formatter in self.format:
                if formatter == "help":
                    continue
                elif formatter not in registered_formatters:
                    unknown_formats.append(formatter)
        return unknown_formats

    @staticmethod
    def build_name_re(names):
        """
        Build regular expression for scenario selection by name
        by using a list of name parts or name regular expressions.

        :param names: List of name parts or regular expressions (as text).
        :return: Compiled regular expression to use.
        """
        pattern = u"|".join(names)
        return re.compile(pattern, flags=(re.UNICODE | re.LOCALE))

    def exclude(self, filename):
        if isinstance(filename, FileLocation):
            filename = str(filename)

        if self.include_re and self.include_re.search(filename) is None:
            return True
        if self.exclude_re and self.exclude_re.search(filename) is not None:
            return True
        return False

    def setup_logging(self, level=None, configfile=None, **kwargs):
        """
        Support simple setup of logging subsystem.
        Ensures that the logging level is set.
        But note that the logging setup can only occur once.

        SETUP MODES:
          * :func:`logging.config.fileConfig()`, if ``configfile` is provided.
          * :func:`logging.basicConfig(), otherwise.

        .. code-block: python
            # -- FILE: features/environment.py
            def before_all(context):
                context.config.setup_logging()

        :param level:       Logging level of root logger.
                            If None, use :attr:`logging_level` value.
        :param configfile:  Configuration filename for fileConfig() setup.
        :param kwargs:      Passed to :func:`logging.basicConfig()`
        """
        if level is None:
            level = self.logging_level

        if configfile:
            from logging.config import fileConfig
            fileConfig(configfile)
        else:
            format = kwargs.pop("format", self.logging_format)
            datefmt = kwargs.pop("datefmt", self.logging_datefmt)
            logging.basicConfig(format=format, datefmt=datefmt, **kwargs)
        # -- ENSURE: Default log level is set
        #    (even if logging subsystem is already configured).
        logging.getLogger().setLevel(level)

    def setup_model(self):
        if self.scenario_outline_annotation_schema:
            name_schema = unicode(self.scenario_outline_annotation_schema)
            ScenarioOutline.annotation_schema = name_schema.strip()

########NEW FILE########
__FILENAME__ = ansi_escapes
# -*- coding: utf-8 -*-
"""
Provides ANSI escape sequences for coloring/formatting output in ANSI terminals.
"""

import os
import re

colors = {
    'black':        u"\x1b[30m",
    'red':          u"\x1b[31m",
    'green':        u"\x1b[32m",
    'yellow':       u"\x1b[33m",
    'blue':         u"\x1b[34m",
    'magenta':      u"\x1b[35m",
    'cyan':         u"\x1b[36m",
    'white':        u"\x1b[37m",
    'grey':         u"\x1b[90m",
    'bold':         u"\x1b[1m",
}

aliases = {
    'undefined':    'yellow',
    'pending':      'yellow',
    'executing':    'grey',
    'failed':       'red',
    'passed':       'green',
    'outline':      'cyan',
    'skipped':      'cyan',
    'comments':     'grey',
    'tag':          'cyan',
}

escapes = {
    'reset':        u'\x1b[0m',
    'up':           u'\x1b[1A',
}

if 'GHERKIN_COLORS' in os.environ:
    new_aliases = [p.split('=') for p in os.environ['GHERKIN_COLORS'].split(':')]
    aliases.update(dict(new_aliases))

for alias in aliases:
    escapes[alias] = ''.join([colors[c] for c in aliases[alias].split(',')])
    arg_alias = alias + '_arg'
    arg_seq = aliases.get(arg_alias, aliases[alias] + ',bold')
    escapes[arg_alias] = ''.join([colors[c] for c in arg_seq.split(',')])


def up(n):
    return u"\x1b[%dA" % n

_ANSI_ESCAPE_PATTERN = re.compile(u"\x1b\[\d+[mA]", re.UNICODE)
def strip_escapes(text):
    """
    Removes ANSI escape sequences from text (if any are contained).

    :param text: Text that may or may not contain ANSI escape sequences.
    :return: Text without ANSI escape sequences.
    """
    return _ANSI_ESCAPE_PATTERN.sub("", text)


def use_ansi_escape_colorbold_composites():     # pragma: no cover
    """
    Patch for "sphinxcontrib-ansi" to process the following ANSI escapes
    correctly (set-color set-bold sequences):

        ESC[{color}mESC[1m  => ESC[{color};1m

    Reapply aliases to ANSI escapes mapping.
    """
    global escapes
    color_codes = {}
    for color_name, color_escape in colors.items():
        color_code = color_escape.replace(u"\x1b[", u"").replace(u"m", u"")
        color_codes[color_name] = color_code

    for alias in aliases:
        parts = [ color_codes[c] for c in aliases[alias].split(',') ]
        composite_escape = u"\x1b[{0}m".format(u";".join(parts))
        escapes[alias] = composite_escape

        arg_alias = alias + '_arg'
        arg_seq = aliases.get(arg_alias, aliases[alias] + ',bold')
        parts = [ color_codes[c] for c in arg_seq.split(',') ]
        composite_escape = u"\x1b[{0}m".format(u";".join(parts))
        escapes[arg_alias] = composite_escape

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

import codecs
import os.path
import sys


class StreamOpener(object):
    """
    Provides a transport vehicle to open the formatter output stream
    when the formatter needs it.
    In addition, it provides the formatter with more control:

      * when a stream is opened
      * if a stream is opened at all
      * the name (filename/dirname) of the output stream
      * let it decide if directory mode is used instead of file mode
    """
    default_encoding = "UTF-8"

    def __init__(self, filename=None, stream=None, encoding=None):
        if not encoding:
            encoding = self.default_encoding
        if stream:
            stream = self.ensure_stream_with_encoder(stream, encoding)
        self.name = filename
        self.stream = stream
        self.encoding = encoding
        self.should_close_stream = not stream   # Only for not pre-opened ones.

    @staticmethod
    def ensure_dir_exists(directory):
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

    @classmethod
    def ensure_stream_with_encoder(cls, stream, encoding=None):
        if not encoding:
            encoding = cls.default_encoding
        if hasattr(stream, "stream"):
            return stream    # Already wrapped with a codecs.StreamWriter
        elif sys.version_info[0] < 3:
            # py2 does, however, sometimes declare an encoding on sys.stdout,
            # even if it doesn't use it (or it might be explicitly None)
            stream = codecs.getwriter(encoding)(stream)
        elif not getattr(stream, 'encoding', None):
            # ok, so the stream doesn't have an encoding at all so add one
            stream = codecs.getwriter(encoding)(stream)
        return stream

    def open(self):
        if not self.stream or self.stream.closed:
            self.ensure_dir_exists(os.path.dirname(self.name))
            stream = open(self.name, "w")
            # stream = codecs.open(self.name, "w", encoding=self.encoding)
            stream = self.ensure_stream_with_encoder(stream, self.encoding)
            self.stream = stream  # -- Keep stream for house-keeping.
            self.should_close_stream = True
            assert self.should_close_stream
        return self.stream

    def close(self):
        """
        Close the stream, if it was opened by this stream_opener.
        Skip closing for sys.stdout and pre-opened streams.
        :return: True, if stream was closed.
        """
        closed = False
        if self.stream and self.should_close_stream:
            closed = getattr(self.stream, "closed", False)
            if not closed:
                self.stream.close()
                closed = True
            self.stream = None
        return closed


class Formatter(object):
    """
    Base class for all formatter classes.
    A formatter is an extension point (variation point) for the runner logic.
    A formatter is called while processing model elements.

    Processing Logic (simplified, without ScenarioOutline and skip logic)::

        for feature in runner.features:
            formatter = get_formatter(...)
            formatter.uri(feature.filename)
            formatter.feature(feature)
            for scenario in feature.scenarios:
                formatter.scenario(scenario)
                for step in scenario.all_steps:
                    formatter.step(step)
                    step_match = step_registry.find_match(step)
                    formatter.match(step_match)
                    if step_match:
                        step_match.run()
                    else:
                        step.status = "undefined"
                    formatter.result(step.status)
            formatter.eof() # -- FEATURE-END
        formatter.close()
    """
    name = None
    description = None

    def __init__(self, stream_opener, config):
        self.stream_opener = stream_opener
        self.stream = stream_opener.stream
        self.config = config

    @property
    def stdout_mode(self):
        return not self.stream_opener.name

    def open(self):
        """
        Ensure that the output stream is open.
        Triggers the stream opener protocol (if necessary).

        :return: Output stream to use (just opened or already open).
        """
        if not self.stream:
            self.stream = self.stream_opener.open()
        return self.stream

    def uri(self, uri):
        """
        Called before processing a file (normally a feature file).

        :param uri:  URI or filename (as string).
        """
        pass

    def feature(self, feature):
        """
        Called before a feature is executed.

        :param feature:  Feature object (as :class:`behave.model.Feature`)
        """
        pass

    def background(self, background):
        """
        Called when a (Feature) Background is provided.
        Called after :method:`feature()` is called.
        Called before processing any scenarios or scenario outlines.

        :param background:  Background object (as :class:`behave.model.Background`)
        """
        pass

    def scenario(self, scenario):
        """
        Called before a scenario is executed (or an example of ScenarioOutline).

        :param scenario:  Scenario object (as :class:`behave.model.Scenario`)
        """
        pass

    def scenario_outline(self, outline):
        pass

    def examples(self, examples):
        pass

    def step(self, step):
        """
        Called before a step is executed (and matched).

        :param step: Step object (as :class:`behave.model.Step`)
        """

    def match(self, match):
        """
        Called when a step was matched against its step implementation.

        :param match:  Registered step (as Match), undefined step (as NoMatch).
        """
        pass

    def result(self, step_result):
        """
        Called after processing a step (when the step result is known).

        :param step_result:  Step result (as string-enum).
        """
        pass

    def eof(self):
        """
        Called after processing a feature (or a feature file).
        """
        pass

    def close(self):
        """
        Called before the formatter is no longer used (stream/io compatibility).
        """
        self.close_stream()

    def close_stream(self):
        """
        Close the stream, but only if this is needed.
        This step is skipped if the stream is sys.stdout.
        """
        if self.stream:
            # -- DELEGATE STREAM-CLOSING: To stream_opener
            assert self.stream is self.stream_opener.stream
            self.stream_opener.close()
        self.stream = None      # -- MARK CLOSED.

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-
# FIXME:
__status__ = "DEAD, BROKEN"

from gherkin.tag_expression import TagExpression


class LineFilter(object):
    def __init__(self, lines):
        self.lines = lines

    def eval(self, tags, names, ranges):
        for r in ranges:
            for line in self.lines:
                if r[0] <= line <= r[1]:
                    return True
        return False

    def filter_table_body_rows(self, rows):
        body = [r for r in rows[1:] if r.line in self.lines]
        return [rows[0]] + body


class RegexpFilter(object):
    def __init__(self, regexen):
        self.regexen = regexen

    def eval(self, tags, names, ranges):
        for regex in self.regexen:
            for name in names:
                if regex.search(name):
                    return True
        return False

    def filter_table_body_rows(self, rows):
        return rows


class TagFilter(object):
    def __init__(self, tags):
        self.tag_expression = TagExpression(tags)

    def eval(self, tags, names, ranges):
        return self.tag_expression.eval([tag.name for tag in set(tags)])

    def filter_table_body_rows(self, rows):
        return rows

########NEW FILE########
__FILENAME__ = filter_formatter
# -*- coding: utf-8 -*-
# FIXME:
__status__ = "DEAD, BROKEN"

import re
from gherkin.formatter import filters

re_type = type(re.compile(''))


class FilterError(Exception):
    pass


class FilterFormatter(object):
    def __init__(self, formatter, filters):
        self.formatter = formatter
        self.filter = self.detect_filters(filters)

        self._feature_tags = []
        self._feature_element_tags = []
        self._examples_tags = []

        self._feature_events = []
        self._background_events = []
        self._feature_element_events = []
        self._examples_events = []

        self._feature_name = None
        self._feature_element_name = None
        self._examples_name = None

        self._feature_element_range = None
        self._examples_range = None

    def uri(self, uri):
        self.formatter.uri(uri)

    def feature(self, feature):
        self._feature_tags = feature.tags
        self._feature_name = feature.name
        self._feature_events = [feature]

    def background(self, background):
        self._feature_element_name = background.name
        self._feature_element_range = background.line_range()
        self._background_events = [background]

    def scenario(self, scenario):
        self.replay()
        self._feature_element_tags = scenario.tags
        self._feature_element_name = scenario.name
        self._feature_element_range = scenario.line_range()
        self._feature_element_events = [scenario]

    def scenario_outline(self, scenario_outline):
        self.replay()
        self._feature_element_tags = scenario_outline.tags
        self._feature_element_name = scenario_outline.name
        self._feature_element_range = scenario_outline.line_range()
        self._feature_element_events = [scenario_outline]

    def examples(self, examples):
        self.replay()
        self._examples_tags = examples.tags
        self._examples_name = examples.name

        if len(examples.rows) == 0:
            table_body_range = (examples.line_range()[1],
                                examples.line_range()[1])
        elif len(examples.rows) == 1:
            table_body_range = (examples.rows[0].line, examples.rows[0].line)
        else:
            table_body_range = (examples.rows[1].line, examples.rows[-1].line)

        self._examples_range = [examples.line_range()[0], table_body_range[1]]

        if self.filter.eval([], [], [table_body_range]):
            examples.rows = self.filter.filter_table_body_rows(examples.rows)

        self._examples_events = [examples]

    def step(self, step):
        if len(self._feature_element_events) > 0:
            self._feature_element_events.append(step)
        else:
            self._background_events.append(step)

        self._feature_element_range = (self._feature_element_range[0],
                                       step.line_range()[1])

    def eof(self):
        self.replay()
        self.formatter.eof()

    def detect_filters(self, filter_list):
        filter_classes = set([type(f) for f in filter_list])
        if len(filter_classes) > 1 and filter_classes != set([str, unicode]):
            message = "Inconsistent filters: %r" % (filter_list, )
            raise FilterError(message)

        if type(filter_list[0]) == int:
            return filters.LineFilter(filter_list)
        if type(filter_list[0]) == re_type:
            return filters.RegexpFilter(filter_list)
        return filters.TagFilter(filter_list)

    def replay(self):
        tags = self._feature_tags + self._feature_element_tags
        names = [self._feature_name, self._feature_element_name]
        ranges = [self._feature_element_range]

        feature_element_ok = self.filter.eval(
            tags,
            [n for n in names if n is not None],
            [r for r in ranges if r is not None],
        )

        examples_ok = self.filter.eval(
            tags + self._examples_tags,
            [n for n in names + [self._examples_name] if n is not None],
            [r for r in ranges + [self._examples_range] if r is not None],
        )

        if feature_element_ok or examples_ok:
            self.replay_events(self._feature_events)
            self.replay_events(self._background_events)
            self.replay_events(self._feature_element_events)

            if examples_ok:
                self.replay_events(self._examples_events)

        self._examples_events[:] = []
        self._examples_tags[:] = []
        self._examples_name = None

    def replay_events(self, events):
        for event in events:
            event.replay(self.formatter)
        events[:] = []

########NEW FILE########
__FILENAME__ = formatters
# -*- coding: utf-8 -*-

import sys
from behave.formatter.base import StreamOpener
from behave.textutil import compute_words_maxsize
from behave.importer import LazyDict, LazyObject


# -----------------------------------------------------------------------------
# FORMATTER REGISTRY:
# -----------------------------------------------------------------------------
formatters = LazyDict()


def register_as(formatter_class, name):
    """
    Register formatter class with given name.

    :param formatter_class:  Formatter class to register.
    :param name:  Name for this formatter (as identifier).
    """
    formatters[name] = formatter_class

def register(formatter_class):
    register_as(formatter_class, formatter_class.name)


def list_formatters(stream):
    """
    Writes a list of the available formatters and their description to stream.

    :param stream:  Output stream to use.
    """
    formatter_names = sorted(formatters)
    column_size = compute_words_maxsize(formatter_names)
    schema = u"  %-"+ str(column_size) +"s  %s\n"
    for name in formatter_names:
        stream.write(schema % (name, formatters[name].description))


def get_formatter(config, stream_openers):
    # -- BUILD: Formatter list
    default_stream_opener = StreamOpener(stream=sys.stdout)
    formatter_list = []
    for i, name in enumerate(config.format):
        stream_opener = default_stream_opener
        if i < len(stream_openers):
            stream_opener = stream_openers[i]
        formatter_list.append(formatters[name](stream_opener, config))
    return formatter_list


# -----------------------------------------------------------------------------
# SETUP:
# -----------------------------------------------------------------------------
def setup_formatters():
    # -- NOTE: Use lazy imports for formatters (to speed up start-up time).
    _L = LazyObject
    register_as(_L("behave.formatter.plain:PlainFormatter"), "plain")
    register_as(_L("behave.formatter.pretty:PrettyFormatter"), "pretty")
    register_as(_L("behave.formatter.json:JSONFormatter"), "json")
    register_as(_L("behave.formatter.json:PrettyJSONFormatter"), "json.pretty")
    register_as(_L("behave.formatter.null:NullFormatter"), "null")
    register_as(_L("behave.formatter.progress:ScenarioProgressFormatter"),
                "progress")
    register_as(_L("behave.formatter.progress:StepProgressFormatter"),
                "progress2")
    register_as(_L("behave.formatter.progress:ScenarioStepProgressFormatter"),
                "progress3")
    register_as(_L("behave.formatter.rerun:RerunFormatter"), "rerun")
    register_as(_L("behave.formatter.tags:TagsFormatter"), "tags")
    register_as(_L("behave.formatter.tags:TagsLocationFormatter"),
                "tags.location")
    register_as(_L("behave.formatter.steps:StepsFormatter"), "steps")
    register_as(_L("behave.formatter.steps:StepsDocFormatter"), "steps.doc")
    register_as(_L("behave.formatter.steps:StepsUsageFormatter"), "steps.usage")
    register_as(_L("behave.formatter.sphinx_steps:SphinxStepsFormatter"),
                "sphinx.steps")


# -----------------------------------------------------------------------------
# MODULE-INIT:
# -----------------------------------------------------------------------------
setup_formatters()

########NEW FILE########
__FILENAME__ = json
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from behave.formatter.base import Formatter
import base64
import six
try:
    import json
except ImportError:
    import simplejson as json


# -----------------------------------------------------------------------------
# CLASS: JSONFormatter
# -----------------------------------------------------------------------------
class JSONFormatter(Formatter):
    name = 'json'
    description = 'JSON dump of test run'
    dumps_kwargs = {}
    split_text_into_lines = True   # EXPERIMENT for better readability.

    json_number_types = (int, long, float)
    json_scalar_types = json_number_types + (six.text_type, bool, type(None))

    def __init__(self, stream_opener, config):
        super(JSONFormatter, self).__init__(stream_opener, config)
        # -- ENSURE: Output stream is open.
        self.stream = self.open()
        self.feature_count = 0
        self.current_feature = None
        self.current_feature_data = None
        self._step_index = 0

    def reset(self):
        self.current_feature = None
        self.current_feature_data = None
        self._step_index = 0

    # -- FORMATTER API:
    def uri(self, uri):
        pass

    def feature(self, feature):
        self.reset()
        self.current_feature = feature
        self.current_feature_data = {
            'keyword': feature.keyword,
            'name': feature.name,
            'tags': list(feature.tags),
            'location': unicode(feature.location),
            'status': feature.status,
        }
        element = self.current_feature_data
        if feature.description:
            element['description'] = feature.description

    def background(self, background):
        element = self.add_feature_element({
            'type': 'background',
            'keyword': background.keyword,
            'name': background.name,
            'location': unicode(background.location),
            'steps': [],
        })
        if background.name:
            element['name'] = background.name
        self._step_index = 0

        # -- ADD BACKGROUND STEPS: Support *.feature file regeneration.
        for step_ in background.steps:
            self.step(step_)

    def scenario(self, scenario):
        element = self.add_feature_element({
            'type': 'scenario',
            'keyword': scenario.keyword,
            'name': scenario.name,
            'tags': scenario.tags,
            'location': unicode(scenario.location),
            'steps': [],
        })
        if scenario.description:
            element['description'] = scenario.description
        self._step_index = 0

    def scenario_outline(self, scenario_outline):
        element = self.add_feature_element({
            'type': 'scenario_outline',
            'keyword': scenario_outline.keyword,
            'name': scenario_outline.name,
            'tags': scenario_outline.tags,
            'location': unicode(scenario_outline.location),
            'steps': [],
            'examples': [],
        })
        if scenario_outline.description:
            element['description'] = scenario_outline.description
        self._step_index = 0

    @classmethod
    def make_table(cls, table):
        table_data = {
            'headings': table.headings,
            'rows': [ list(row) for row in table.rows ]
        }
        return table_data

    def examples(self, examples):
        e = {
            'type': 'examples',
            'keyword': examples.keyword,
            'name': examples.name,
            'location': unicode(examples.location),
        }

        if examples.table:
            e['table'] = self.make_table(examples.table)

        element = self.current_feature_element
        element['examples'].append(e)

    def step(self, step):
        s = {
            'keyword': step.keyword,
            'step_type': step.step_type,
            'name': step.name,
            'location': unicode(step.location),
        }

        if step.text:
            text = step.text
            if self.split_text_into_lines and "\n" in text:
                text = text.splitlines()
            s['text'] = text
        if step.table:
            s['table'] = self.make_table(step.table)
        element = self.current_feature_element
        element['steps'].append(s)

    def match(self, match):
        args = []
        for argument in match.arguments:
            argument_value = argument.value
            if not isinstance(argument_value, self.json_scalar_types):
                # -- OOPS: Avoid invalid JSON format w/ custom types.
                # Use raw string (original) instead.
                argument_value = argument.original
            assert isinstance(argument_value, self.json_scalar_types)
            arg = {
                'value': argument_value,
            }
            if argument.name:
                arg['name'] = argument.name
            if argument.original != argument_value:
                # -- REDUNDANT DATA COMPRESSION: Suppress for strings.
                arg['original'] = argument.original
            args.append(arg)

        match_data = {
            'location': unicode(match.location) or "",
            'arguments': args,
        }
        if match.location:
            # -- NOTE: match.location=None occurs for undefined steps.
            steps = self.current_feature_element['steps']
            steps[self._step_index]['match'] = match_data

    def result(self, result):
        steps = self.current_feature_element['steps']
        steps[self._step_index]['result'] = {
            'status': result.status,
            'duration': result.duration,
        }
        if result.error_message and result.status == 'failed':
            # -- OPTIONAL: Provided for failed steps.
            error_message = result.error_message
            if self.split_text_into_lines and "\n" in error_message:
                error_message = error_message.splitlines()
            result_element = steps[self._step_index]['result']
            result_element['error_message'] = error_message
        self._step_index += 1

    def embedding(self, mime_type, data):
        step = self.current_feature_element['steps'][-1]
        step['embeddings'].append({
            'mime_type': mime_type,
            'data': base64.b64encode(data).replace('\n', ''),
        })

    def eof(self):
        """
        End of feature
        """
        if not self.current_feature_data:
            return

        # -- NORMAL CASE: Write collected data of current feature.
        self.update_status_data()

        if self.feature_count == 0:
            # -- FIRST FEATURE:
            self.write_json_header()
        else:
            # -- NEXT FEATURE:
            self.write_json_feature_separator()

        self.write_json_feature(self.current_feature_data)
        self.current_feature_data = None
        self.feature_count += 1

    def close(self):
        self.write_json_footer()
        self.close_stream()

    # -- JSON-DATA COLLECTION:
    def add_feature_element(self, element):
        assert self.current_feature_data is not None
        if 'elements' not in self.current_feature_data:
            self.current_feature_data['elements'] = []
        self.current_feature_data['elements'].append(element)
        return element

    @property
    def current_feature_element(self):
        assert self.current_feature_data is not None
        return self.current_feature_data['elements'][-1]

    def update_status_data(self):
        assert self.current_feature
        assert self.current_feature_data
        self.current_feature_data['status'] = self.current_feature.status

    # -- JSON-WRITER:
    def write_json_header(self):
        self.stream.write('[\n')

    def write_json_footer(self):
        self.stream.write('\n]\n')

    def write_json_feature(self, feature_data):
        self.stream.write(json.dumps(feature_data, **self.dumps_kwargs))
        self.stream.flush()

    def write_json_feature_separator(self):
        self.stream.write(",\n\n")


# -----------------------------------------------------------------------------
# CLASS: PrettyJSONFormatter
# -----------------------------------------------------------------------------
class PrettyJSONFormatter(JSONFormatter):
    """
    Provides readable/comparable textual JSON output.
    """
    name = 'json.pretty'
    description = 'JSON dump of test run (human readable)'
    dumps_kwargs = { 'indent': 2, 'sort_keys': True }

########NEW FILE########
__FILENAME__ = null
# -*- coding: utf-8 -*-

from behave.formatter.base import Formatter

class NullFormatter(Formatter):
    """
    Provides formatter that does not output anything.
    Implements the NULL pattern for a formatter (similar like: /dev/null).
    """
    name = "null"
    description = "Provides formatter that does not output anything."

########NEW FILE########
__FILENAME__ = plain
# -*- coding: utf-8 -*-

from behave.formatter.base import Formatter
from behave.model_describe import ModelPrinter
from behave.textutil import make_indentation


# -----------------------------------------------------------------------------
# CLASS: PlainFormatter
# -----------------------------------------------------------------------------
class PlainFormatter(Formatter):
    """
    Provides a simple plain formatter without coloring/formatting.
    The formatter displays now also:

       * multi-line text (doc-strings)
       * table
       * tags (maybe)
    """
    name = "plain"
    description = "Very basic formatter with maximum compatibility"

    SHOW_MULTI_LINE = True
    SHOW_TAGS = False
    SHOW_ALIGNED_KEYWORDS = False
    DEFAULT_INDENT_SIZE = 2

    def __init__(self, stream_opener, config, **kwargs):
        super(PlainFormatter, self).__init__(stream_opener, config)
        self.steps = []
        self.show_timings = config.show_timings
        self.show_multiline = config.show_multiline and self.SHOW_MULTI_LINE
        self.show_aligned_keywords = self.SHOW_ALIGNED_KEYWORDS
        self.show_tags = self.SHOW_TAGS
        self.indent_size = self.DEFAULT_INDENT_SIZE
        # -- ENSURE: Output stream is open.
        self.stream = self.open()
        self.printer = ModelPrinter(self.stream)
        # -- LAZY-EVALUATE:
        self._multiline_indentation = None

    @property
    def multiline_indentation(self):
        if self._multiline_indentation is None:
            offset = 0
            if self.show_aligned_keywords:
                offset = 2
            indentation = make_indentation(3 * self.indent_size + offset)
            self._multiline_indentation = indentation
        return self._multiline_indentation

    def reset_steps(self):
        self.steps = []

    def write_tags(self, tags, indent=None):
        if tags and self.show_tags:
            indent = indent or ""
            text = " @".join(tags)
            self.stream.write(u"%s@%s\n" % (indent, text))

    # -- IMPLEMENT-INTERFACE FOR: Formatter
    def feature(self, feature):
        self.reset_steps()
        self.write_tags(feature.tags)
        self.stream.write(u"%s: %s\n" % (feature.keyword, feature.name))

    def background(self, background):
        self.reset_steps()
        indent = make_indentation(self.indent_size)
        text = u"%s%s: %s\n" % (indent, background.keyword, background.name)
        self.stream.write(text)

    def scenario(self, scenario):
        self.reset_steps()
        self.stream.write(u"\n")
        indent = make_indentation(self.indent_size)
        text = u"%s%s: %s\n" % (indent, scenario.keyword, scenario.name)
        self.write_tags(scenario.tags, indent)
        self.stream.write(text)

    def scenario_outline(self, outline):
        self.reset_steps()
        indent = make_indentation(self.indent_size)
        text = u"%s%s: %s\n" % (indent, outline.keyword, outline.name)
        self.write_tags(outline.tags, indent)
        self.stream.write(text)

    def step(self, step):
        self.steps.append(step)

    def result(self, result):
        """
        Process the result of a step (after step execution).

        :param result:
        """
        step = self.steps.pop(0)
        indent = make_indentation(2 * self.indent_size)
        if self.show_aligned_keywords:
            # -- RIGHT-ALIGN KEYWORDS (max. keyword width: 6):
            text = u"%s%6s %s ... " % (indent, step.keyword, step.name)
        else:
            text = u"%s%s %s ... " % (indent, step.keyword, step.name)
        self.stream.write(text)

        status = result.status
        if self.show_timings:
            status += " in %0.3fs" % step.duration

        if result.error_message:
            self.stream.write(u"%s\n%s\n" % (status, result.error_message))
        else:
            self.stream.write(u"%s\n" % status)

        if self.show_multiline:
            if step.text:
                self.doc_string(step.text)
            if step.table:
                self.table(step.table)

    def eof(self):
        self.stream.write("\n")

    # -- MORE: Formatter helpers
    def doc_string(self, doc_string):
        self.printer.print_docstring(doc_string, self.multiline_indentation)

    def table(self, table):
        self.printer.print_table(table, self.multiline_indentation)


# -----------------------------------------------------------------------------
# CLASS: Plain0Formatter
# -----------------------------------------------------------------------------
class Plain0Formatter(PlainFormatter):
    """
    Similar to old plain formatter without support for:

      * multi-line text
      * tables
      * tags
    """
    name = "plain0"
    description = "Very basic formatter with maximum compatibility"
    SHOW_MULTI_LINE = False
    SHOW_TAGS = False
    SHOW_ALIGNED_KEYWORDS = False

########NEW FILE########
__FILENAME__ = pretty
# -*- coding: utf8 -*-

from behave.formatter.ansi_escapes import escapes, up
from behave.formatter.base import Formatter
from behave.model_describe import escape_cell, escape_triple_quotes
from behave.textutil import indent
import sys


# -----------------------------------------------------------------------------
# TERMINAL SUPPORT:
# -----------------------------------------------------------------------------
DEFAULT_WIDTH = 80
DEFAULT_HEIGHT = 24

def get_terminal_size():
    if sys.platform == 'windows':
        # Autodetecting the size of a Windows command window is left as an
        # exercise for the reader. Prizes may be awarded for the best answer.
        return (DEFAULT_WIDTH, DEFAULT_HEIGHT)

    try:
        import fcntl
        import termios
        import struct

        zero_struct = struct.pack('HHHH', 0, 0, 0, 0)
        result = fcntl.ioctl(0, termios.TIOCGWINSZ, zero_struct)
        h, w, hp, wp = struct.unpack('HHHH', result)

        return w or DEFAULT_WIDTH, h or DEFAULT_HEIGHT
    except:
        return (DEFAULT_WIDTH, DEFAULT_HEIGHT)


# -----------------------------------------------------------------------------
# COLORING SUPPORT:
# -----------------------------------------------------------------------------
class MonochromeFormat(object):
    def text(self, text):
        assert isinstance(text, unicode)
        return text


class ColorFormat(object):
    def __init__(self, status):
        self.status = status

    def text(self, text):
        assert isinstance(text, unicode)
        return escapes[self.status] + text + escapes['reset']


# -----------------------------------------------------------------------------
# CLASS: PrettyFormatter
# -----------------------------------------------------------------------------
class PrettyFormatter(Formatter):
    name = 'pretty'
    description = 'Standard colourised pretty formatter'

    def __init__(self, stream_opener, config):
        super(PrettyFormatter, self).__init__(stream_opener, config)
        # -- ENSURE: Output stream is open.
        self.stream = self.open()
        isatty = getattr(self.stream, "isatty", lambda: True)
        stream_supports_colors = isatty()
        self.monochrome = not config.color or not stream_supports_colors
        self.show_source = config.show_source
        self.show_timings = config.show_timings
        self.show_multiline = config.show_multiline
        self.formats = None
        self.display_width = get_terminal_size()[0]

        # -- UNUSED: self.tag_statement = None
        self.steps = []
        self._uri = None
        self._match = None
        self.statement = None
        self.indentations = []
        self.step_lines = 0


    def reset(self):
        # -- UNUSED: self.tag_statement = None
        self.steps = []
        self._uri = None
        self._match = None
        self.statement = None
        self.indentations = []
        self.step_lines = 0

    def uri(self, uri):
        self.reset()
        self._uri = uri

    def feature(self, feature):
        #self.print_comments(feature.comments, '')
        self.print_tags(feature.tags, '')
        self.stream.write(u"%s: %s" % (feature.keyword, feature.name))
        if self.show_source:
            format = self.format('comments')
            self.stream.write(format.text(u" # %s" % feature.location))
        self.stream.write("\n")
        self.print_description(feature.description, '  ', False)
        self.stream.flush()

    def background(self, background):
        self.replay()
        self.statement = background

    def scenario(self, scenario):
        self.replay()
        self.statement = scenario

    def scenario_outline(self, scenario_outline):
        self.replay()
        self.statement = scenario_outline

    def replay(self):
        self.print_statement()
        self.print_steps()
        self.stream.flush()

    def examples(self, examples):
        self.replay()
        self.stream.write("\n")
        self.print_comments(examples.comments, '    ')
        self.print_tags(examples.tags, '    ')
        self.stream.write('    %s: %s\n' % (examples.keyword, examples.name))
        self.print_description(examples.description, '      ')
        self.table(examples.rows)
        self.stream.flush()

    def step(self, step):
        self.steps.append(step)

    def match(self, match):
        self._match = match
        self.print_statement()
        self.print_step('executing', self._match.arguments,
                        self._match.location, self.monochrome)
        self.stream.flush()

    def result(self, result):
        if not self.monochrome:
            lines = self.step_lines + 1
            if self.show_multiline:
                if result.table:
                    lines += len(result.table.rows) + 1
                if result.text:
                    lines += len(result.text.splitlines()) + 2
            self.stream.write(up(lines))
            arguments = []
            location = None
            if self._match:
                arguments = self._match.arguments
                location = self._match.location
            self.print_step(result.status, arguments, location, True)
        if result.error_message:
            self.stream.write(indent(result.error_message.strip(), u'      '))
            self.stream.write('\n\n')
        self.stream.flush()

    def arg_format(self, key):
        return self.format(key + '_arg')

    def format(self, key):
        if self.monochrome:
            if self.formats is None:
                self.formats = MonochromeFormat()
            return self.formats
        if self.formats is None:
            self.formats = {}
        format = self.formats.get(key, None)
        if format is not None:
            return format
        format = self.formats[key] = ColorFormat(key)
        return format

    def eof(self):
        self.replay()
        self.stream.write('\n')
        self.stream.flush()

    def table(self, table):
        cell_lengths = []
        all_rows = [table.headings] + table.rows
        for row in all_rows:
            lengths = [len(escape_cell(c)) for c in row]
            cell_lengths.append(lengths)

        max_lengths = []
        for col in range(0, len(cell_lengths[0])):
            max_lengths.append(max([c[col] for c in cell_lengths]))

        for i, row in enumerate(all_rows):
            #for comment in row.comments:
            #    self.stream.write('      %s\n' % comment.value)
            self.stream.write('      |')
            for j, (cell, max_length) in enumerate(zip(row, max_lengths)):
                self.stream.write(' ')
                self.stream.write(self.color(cell, None, j))
                self.stream.write(' ' * (max_length - cell_lengths[i][j]))
                self.stream.write(' |')
            self.stream.write('\n')
        self.stream.flush()

    def doc_string(self, doc_string):
        #self.stream.write('      """' + doc_string.content_type + '\n')
        prefix = '      '
        self.stream.write('%s"""\n' % prefix)
        doc_string = escape_triple_quotes(indent(doc_string, prefix))
        self.stream.write(doc_string)
        self.stream.write('\n%s"""\n' % prefix)
        self.stream.flush()

    # def doc_string(self, doc_string):
    #     from behave.model_describe import ModelDescriptor
    #     prefix = '      '
    #     text = ModelDescriptor.describe_docstring(doc_string, prefix)
    #     self.stream.write(text)
    #     self.stream.flush()

    def exception(self, exception):
        exception_text = HERP
        self.stream.write(self.failed(exception_text) + '\n')
        self.stream.flush()

    def color(self, cell, statuses, color):
        if statuses:
            return escapes['color'] + escapes['reset']
        else:
            return escape_cell(cell)

    def indented_text(self, text, proceed):
        if not text:
            return u''

        if proceed:
            indentation = self.indentations.pop(0)
        else:
            indentation = self.indentations[0]

        indentation = u' ' * indentation
        return u'%s # %s' % (indentation, text)

    def calculate_location_indentations(self):
        line_widths = []
        for s in [self.statement] + self.steps:
            string = s.keyword + ' ' + s.name
            line_widths.append(len(string))
        max_line_width = max(line_widths)
        self.indentations = [max_line_width - width for width in line_widths]

    def print_statement(self):
        if self.statement is None:
            return

        self.calculate_location_indentations()
        self.stream.write(u"\n")
        #self.print_comments(self.statement.comments, '  ')
        if hasattr(self.statement, 'tags'):
            self.print_tags(self.statement.tags, u'  ')
        self.stream.write(u"  %s: %s " % (self.statement.keyword,
                                          self.statement.name))

        location = self.indented_text(unicode(self.statement.location), True)
        if self.show_source:
            self.stream.write(self.format('comments').text(location))
        self.stream.write("\n")
        #self.print_description(self.statement.description, u'    ')
        self.statement = None

    def print_steps(self):
        while self.steps:
            self.print_step('skipped', [], None, True)

    def print_step(self, status, arguments, location, proceed):
        if proceed:
            step = self.steps.pop(0)
        else:
            step = self.steps[0]

        text_format = self.format(status)
        arg_format = self.arg_format(status)

        #self.print_comments(step.comments, '    ')
        self.stream.write('    ')
        self.stream.write(text_format.text(step.keyword + ' '))
        line_length = 5 + len(step.keyword)

        step_name = unicode(step.name)

        text_start = 0
        for arg in arguments:
            if arg.end <= text_start:
                # -- SKIP-OVER: Optional and nested regexp args
                #    - Optional regexp args (unmatched: None).
                #    - Nested regexp args that are already processed.
                continue
                # -- VALID, MATCHED ARGUMENT:
            assert arg.original is not None
            text = step_name[text_start:arg.start]
            self.stream.write(text_format.text(text))
            line_length += len(text)
            self.stream.write(arg_format.text(arg.original))
            line_length += len(arg.original)
            text_start = arg.end

        if text_start != len(step_name):
            text = step_name[text_start:]
            self.stream.write(text_format.text(text))
            line_length += (len(text))

        if self.show_source:
            location = unicode(location)
            if self.show_timings and status in ('passed', 'failed'):
                location += ' %0.3fs' % step.duration
            location = self.indented_text(location, proceed)
            self.stream.write(self.format('comments').text(location))
            line_length += len(location)
        elif self.show_timings and status in ('passed', 'failed'):
            timing = '%0.3fs' % step.duration
            timing = self.indented_text(timing, proceed)
            self.stream.write(self.format('comments').text(timing))
            line_length += len(timing)
        self.stream.write("\n")

        self.step_lines = int((line_length - 1) / self.display_width)

        if self.show_multiline:
            if step.text:
                self.doc_string(step.text)
            if step.table:
                self.table(step.table)

    def print_tags(self, tags, indentation):
        if not tags:
            return
        line = ' '.join('@' + tag for tag in tags)
        self.stream.write(indentation + line + '\n')

    def print_comments(self, comments, indentation):
        if not comments:
            return

        self.stream.write(indent([c.value for c in comments], indentation))
        self.stream.write('\n')

    def print_description(self, description, indentation, newline=True):
        if not description:
            return

        self.stream.write(indent(description, indentation))
        if newline:
            self.stream.write('\n')

########NEW FILE########
__FILENAME__ = progress
# -*- coding: utf-8 -*-
"""
Provides 2 dotted progress formatters:

  * ScenarioProgressFormatter (scope: scenario)
  * StepProgressFormatter (scope: step)

A "dot" character that represents the result status is printed after
executing a scope item.
"""

from behave.formatter.base import Formatter
from behave.compat.os_path import relpath
import os

# -----------------------------------------------------------------------------
# CLASS: ProgressFormatterBase
# -----------------------------------------------------------------------------
class ProgressFormatterBase(Formatter):
    """
    Provides formatter base class for different variants of progress formatters.
    A progress formatter show an abbreviated, compact dotted progress bar,
    similar to unittest output (in terse mode).
    """
    # -- MAP: step.status to short dot_status representation.
    dot_status = {
        "passed":    ".",
        "failed":    "F",
        "error":     "E",   # Caught exception, but not an AssertionError
        "skipped":   "S",
        "untested":  "_",
        "undefined": "U",
    }
    show_timings = False

    def __init__(self, stream_opener, config):
        super(ProgressFormatterBase, self).__init__(stream_opener, config)
        # -- ENSURE: Output stream is open.
        self.stream = self.open()
        self.steps = []
        self.failures = []
        self.current_feature  = None
        self.current_scenario = None
        self.show_timings = config.show_timings and self.show_timings

    def reset(self):
        self.steps = []
        self.failures = []
        self.current_feature  = None
        self.current_scenario = None

    # -- FORMATTER API:
    def feature(self, feature):
        self.current_feature = feature
        short_filename = relpath(feature.filename, os.getcwd())
        self.stream.write("%s  " % short_filename)
        self.stream.flush()

    def background(self, background):
        pass

    def scenario(self, scenario):
        """
        Process the next scenario.
        But first allow to report the status on the last scenario.
        """
        self.report_scenario_completed()
        self.current_scenario = scenario

    def scenario_outline(self, outline):
        self.current_scenario = outline

    def step(self, step):
        self.steps.append(step)

    def result(self, result):
        self.steps.pop(0)
        self.report_step_progress(result)

    def eof(self):
        """
        Called at end of a feature.
        It would be better to have a hook that is called after all features.
        """
        self.report_scenario_completed()
        self.report_feature_completed()
        # XXX-OLD: self.stream.write('\n')
        self.report_failures()
        self.stream.flush()
        self.reset()

    # -- SPECIFIC PART:
    def report_step_progress(self, result):
        """
        Report the progress on the current step.
        The default implementation is empty.
        It should be override by a concrete class.
        """
        pass

    def report_scenario_progress(self):
        """
        Report the progress for the current/last scenario.
        The default implementation is empty.
        It should be override by a concrete class.
        """
        pass

    def report_feature_completed(self):
        """Hook called when a feature is completed to perform the last tasks.
        """
        pass

    def report_scenario_completed(self):
        """Hook called when a scenario is completed to perform the last tasks.
        """
        self.report_scenario_progress()

    def report_feature_duration(self):
        if self.show_timings and self.current_feature:
            self.stream.write(u"  # %.3fs" % self.current_feature.duration)
        self.stream.write("\n")

    def report_scenario_duration(self):
        if self.show_timings and self.current_scenario:
            self.stream.write(u"  # %.3fs" % self.current_scenario.duration)
        self.stream.write("\n")

    def report_failures(self):
        if self.failures:
            separator = "-" * 80
            # XXX-OLD: self.stream.write(u"\n%s\n" % separator)
            self.stream.write(u"%s\n" % separator)
            for result in self.failures:
                self.stream.write(u"FAILURE in step '%s':\n" % result.name)
                self.stream.write(u"  Feature:  %s\n" % result.feature.name)
                self.stream.write(u"  Scenario: %s\n" % result.scenario.name)
                self.stream.write(u"%s\n" % result.error_message)
                if result.exception:
                    self.stream.write(u"exception: %s\n" % result.exception)
            self.stream.write(u"%s\n" % separator)


# -----------------------------------------------------------------------------
# CLASS: ScenarioProgressFormatter
# -----------------------------------------------------------------------------
class ScenarioProgressFormatter(ProgressFormatterBase):
    """
    Report dotted progress for each scenario similar to unittest.
    """
    name = "progress"
    description = "Shows dotted progress for each executed scenario."

    def report_scenario_progress(self):
        """
        Report the progress for the current/last scenario.
        """
        if not self.current_scenario:
            return  # SKIP: No results to report for first scenario.
        # -- NORMAL-CASE:
        # XXX-JE-TODO
        status = self.current_scenario.status
        dot_status = self.dot_status[status]
        if status == "failed":
            # XXX-JE-TODO: self.failures.append(result)
            pass
        self.stream.write(dot_status)
        self.stream.flush()

    def report_feature_completed(self):
        self.report_feature_duration()

# -----------------------------------------------------------------------------
# CLASS: StepProgressFormatter
# -----------------------------------------------------------------------------
class StepProgressFormatter(ProgressFormatterBase):
    """
    Report dotted progress for each step similar to unittest.
    """
    name = "progress2"
    description = "Shows dotted progress for each executed step."

    def report_step_progress(self, result):
        """
        Report the progress for each step.
        """
        dot_status = self.dot_status[result.status]
        if result.status == "failed":
            if (result.exception and
                not isinstance(result.exception, AssertionError)):
                # -- ISA-ERROR: Some Exception
                dot_status = self.dot_status["error"]
            result.feature  = self.current_feature
            result.scenario = self.current_scenario
            self.failures.append(result)
        self.stream.write(dot_status)
        self.stream.flush()

    def report_feature_completed(self):
        self.report_feature_duration()


# -----------------------------------------------------------------------------
# CLASS: ScenarioStepProgressFormatter
# -----------------------------------------------------------------------------
class ScenarioStepProgressFormatter(StepProgressFormatter):
    """
    Shows detailed dotted progress for both each step of a scenario.
    Differs from StepProgressFormatter by:

      * showing scenario names (as prefix scenario step progress)
      * showing failures after each scenario (if necessary)

    EXAMPLE:
        $ behave -f progress3 features
        Feature with failing scenario    # features/failing_scenario.feature
            Simple scenario with last failing step  ....F
        -----------------------------------------------------------------------
        FAILURE in step 'last step fails' (features/failing_scenario.feature:7):
        Assertion Failed: xxx
        -----------------------------------------------------------------------
    """
    name = "progress3"
    description = "Shows detailed progress for each step of a scenario."
    indent_size = 2
    scenario_prefix = " " * indent_size

    # -- FORMATTER API:
    def feature(self, feature):
        self.current_feature = feature
        short_filename = relpath(feature.filename, os.getcwd())
        self.stream.write(u"%s    # %s" % (feature.name, short_filename))

    def scenario(self, scenario):
        """Process the next scenario."""
        # -- LAST SCENARIO: Report failures (if any).
        self.report_scenario_completed()

        # -- NEW SCENARIO:
        assert not self.failures
        self.current_scenario = scenario
        scenario_name = scenario.name
        if scenario_name:
            scenario_name += " "
        # XXX-JE-OLD: self.stream.write(u'\n%s%s ' % (self.scenario_prefix, scenario_name))
        self.stream.write(u"%s%s " % (self.scenario_prefix, scenario_name))
        self.stream.flush()

    def eof_XXX_DISABLED(self):
        has_scenarios = self.current_feature and self.current_scenario
        super(ScenarioStepProgressFormatter, self).eof()
        if has_scenarios:
            # -- EMPTY-LINE between 2 features.
            self.stream.write("\n")

    # -- PROGRESS FORMATTER DETAILS:
    # @overriden
    def report_feature_completed(self):
        # -- SKIP: self.report_feature_duration()
        has_scenarios = self.current_feature and self.current_scenario
        if has_scenarios:
            # -- EMPTY-LINE between 2 features.
            self.stream.write("\n")

    def report_scenario_completed(self):
        self.report_scenario_progress()
        self.report_scenario_duration()
        self.report_failures()
        self.failures = []

    def report_failures(self):
        if self.failures:
            separator = "-" * 80
            # XXX-JE-OLD: self.stream.write(u"\n%s\n" % separator)
            self.stream.write(u"%s\n" % separator)
            for failure in self.failures:
                self.stream.write(u"FAILURE in step '%s' (%s):\n" % \
                                  (failure.name, failure.location))
                self.stream.write(u"%s\n" % failure.error_message)
                self.stream.write(u"%s\n" % separator)
            self.stream.flush()

########NEW FILE########
__FILENAME__ = rerun
# -*- coding: utf-8 -*-
"""
Provides a formatter that simplifies to rerun the failing scenarios
of the last test run. It writes a text file with the file locations of
the failing scenarios, like:

    # -- file:rerun.features
    # RERUN: Failing scenarios during last test run.
    features/alice.feature:10
    features/alice.feature:42
    features/bob.feature:67

To rerun the failing scenarios, use:

    behave @rerun_failing.features

Normally, you put the RerunFormatter into the behave configuration file:

    # -- file:behave.ini
    [behave]
    format   = rerun
    outfiles = rerun_failing.features
"""

from behave.formatter.base import Formatter
from behave.compat.os_path import relpath
from datetime import datetime
import os


# -----------------------------------------------------------------------------
# CLASS: RerunFormatter
# -----------------------------------------------------------------------------
class RerunFormatter(Formatter):
    """
    Provides formatter class that emits a summary which scenarios failed
    during the last test run. This output can be used to rerun the tests
    with the failed scenarios.
    """
    name = "rerun"
    description = "Emits scenario file locations of failing scenarios"

    show_timestamp = False
    show_failed_scenarios_descriptions = False

    def __init__(self, stream_opener, config):
        super(RerunFormatter, self).__init__(stream_opener, config)
        self.failed_scenarios = []
        self.current_feature = None

    def reset(self):
        self.failed_scenarios = []
        self.current_feature = None

    # -- FORMATTER API:
    def feature(self, feature):
        self.current_feature = feature

    def eof(self):
        """Called at end of a feature."""
        if self.current_feature and self.current_feature.status == "failed":
            # -- COLLECT SCENARIO FAILURES:
            for scenario in self.current_feature.walk_scenarios():
                if scenario.status == "failed":
                    self.failed_scenarios.append(scenario)

        # -- RESET:
        self.current_feature = None
        assert self.current_feature is None

    def close(self):
        """Called at end of test run."""
        stream_name = self.stream_opener.name
        if self.failed_scenarios:
            # -- ENSURE: Output stream is open.
            self.stream = self.open()
            self.report_scenario_failures()
        elif stream_name and os.path.exists(stream_name):
            # -- ON SUCCESS: Remove last rerun file with its failures.
            os.remove(self.stream_opener.name)

        # -- FINALLY:
        self.close_stream()

    # -- SPECIFIC-API:
    def report_scenario_failures(self):
        assert self.failed_scenarios
        # -- SECTION: Banner
        message = u"# -- RERUN: %d failing scenarios during last test run.\n"
        self.stream.write(message % len(self.failed_scenarios))
        if self.show_timestamp:
            now = datetime.now().replace(microsecond=0)
            self.stream.write("# NOW: %s\n"% now.isoformat(" "))

        # -- SECTION: Textual summary in comments.
        if self.show_failed_scenarios_descriptions:
            current_feature = None
            for index, scenario in enumerate(self.failed_scenarios):
                if current_feature != scenario.filename:
                    if current_feature is not None:
                        self.stream.write(u"#\n")
                    current_feature = scenario.filename
                    short_filename = relpath(scenario.filename, os.getcwd())
                    self.stream.write(u"# %s\n" % short_filename)
                self.stream.write(u"#  %4d:  %s\n" % \
                                  (scenario.line, scenario.name))
            self.stream.write("\n")

        # -- SECTION: Scenario file locations, ala: "alice.feature:10"
        for scenario in self.failed_scenarios:
            self.stream.write(u"%s\n" % scenario.location)
        self.stream.write("\n")

########NEW FILE########
__FILENAME__ = sphinx_steps
# -*- coding: utf-8 -*-
"""
Provides a formatter that generates Sphinx-based documentation
of available step definitions (step implementations).

TODO:
  * Post-processor for step docstrings.
  * Solution for requires: table, text
  * i18n keywords

.. seealso::
    http://sphinx-doc.org/
"""

from behave.formatter.steps import AbstractStepsFormatter
from behave.formatter import sphinx_util
from behave.compat.os_path import relpath
from behave.model import Table
from operator import attrgetter
import inspect
import os.path
import sys


# -----------------------------------------------------------------------------
# HELPER CLASS:
# -----------------------------------------------------------------------------
class StepsModule(object):
    """
    Value object to keep track of step definitions that belong to same module.
    """

    def __init__(self, module_name, step_definitions=None):
        self.module_name = module_name
        self.step_definitions = step_definitions or []
        self._name = None
        self._filename = None


    @property
    def name(self):
        if self._name is None:
            # -- DISCOVER ON DEMAND: From step definitions (module).
            # REQUIRED: To discover complete canonical module name.
            module = self.module
            if module:
                # -- USED-BY: Imported step libraries.
                module_name = self.module.__name__
            else:
                # -- USED-BY: features/steps/*.py (without __init__.py)
                module_name = self.module_name
            self._name = module_name
        return self._name

    @property
    def filename(self):
        if not self._filename:
            if self.step_definitions:
                filename = inspect.getfile(self.step_definitions[0].func)
                self._filename = relpath(filename)
        return self._filename

    @property
    def module(self):
        if self.step_definitions:
            return inspect.getmodule(self.step_definitions[0].func)
        return sys.modules.get(self.module_name)

    @property
    def module_doc(self):
        module = self.module
        if module:
            return inspect.getdoc(module)
        return None

    def append(self, step_definition):
        self.step_definitions.append(step_definition)


# -----------------------------------------------------------------------------
# CLASS: SphinxStepsDocumentGenerator
# -----------------------------------------------------------------------------
class SphinxStepsDocumentGenerator(object):
    """
    Provides document generator class that generates Sphinx-based
    documentation for step definitions. The primary purpose is to:

      * help the step-library provider/writer
      * simplify self-documentation of step-libraries

    EXAMPLE:
        step_definitions = ...  # Collect from step_registry
        doc_generator = SphinxStepsDocumentGenerator(step_definitions, "output")
        doc_generator.write_docs()

    .. seealso:: http://sphinx-doc.org/
    """
    default_step_definition_doc = """\
.. todo::
    Step definition description is missing.
"""
    shows_step_module_info = True
    shows_step_module_overview = True
    make_step_index_entries = True

    document_separator = "# -- DOCUMENT-END " + "-" * 60
    step_document_prefix = "step_module."
    step_heading_prefix = "**Step:** "

    def __init__(self, step_definitions, destdir=None, stream=None):
        self.step_definitions = step_definitions
        self.destdir = destdir
        self.stream = stream
        self.document = None

    @property
    def stdout_mode(self):
        """
        Indicates that output towards stdout should be used.
        """
        return self.stream is not None

    @staticmethod
    def describe_step_definition(step_definition, step_type=None):
        if not step_type:
            step_type = step_definition.step_type or "step"

        if step_type == "step":
            step_type_text = "Given/When/Then"
        else:
            step_type_text = step_type.capitalize()
        # -- ESCAPE: Some chars required for ReST documents (like backticks)
        step_text = step_definition.string
        if "`" in step_text:
            step_text = step_text.replace("`", "\`")
        return u"%s %s" % (step_type_text, step_text)

    def ensure_destdir_exists(self):
        assert self.destdir
        if os.path.isfile(self.destdir):
            print "OOPS: remove %s" % self.destdir
            os.remove(self.destdir)
        if not os.path.exists(self.destdir):
            os.makedirs(self.destdir)

    def ensure_document_is_closed(self):
        if self.document and not self.stdout_mode:
            self.document.close()
            self.document = None

    def discover_step_modules(self):
        step_modules_map = {}
        for step_definition in self.step_definitions:
            assert step_definition.step_type is not None
            step_filename = step_definition.location.filename
            step_module = step_modules_map.get(step_filename, None)
            if not step_module:
                filename = inspect.getfile(step_definition.func)
                module_name = inspect.getmodulename(filename)
                assert module_name, \
                    "step_definition: %s" % step_definition.location
                step_module = StepsModule(module_name)
                step_modules_map[step_filename] = step_module
            step_module.append(step_definition)

        step_modules = sorted(step_modules_map.values(), key=attrgetter("name"))
        for module in step_modules:
            step_definitions = sorted(module.step_definitions,
                                      key=attrgetter("location"))
            module.step_definitions = step_definitions
        return step_modules

    def create_document(self, filename):
        if not (filename.endswith(".rst") or filename.endswith(".txt")):
            filename += ".rst"
        if self.stdout_mode:
            stream = self.stream
            document = sphinx_util.DocumentWriter(stream, should_close=False)
        else:
            self.ensure_destdir_exists()
            filename = os.path.join(self.destdir, filename)
            document = sphinx_util.DocumentWriter.open(filename)
        return document

    def write_docs(self):
        step_modules = self.discover_step_modules()
        self.write_step_module_index(step_modules)
        for step_module in step_modules:
            self.write_step_module(step_module)
        return len(step_modules)

    def write_step_module_index(self, step_modules, filename="index.rst"):
        document = self.create_document(filename)
        document.write(".. _docid.steps:\n\n")
        document.write_heading("Step Definitions")
        document.write("""\
The following step definitions are provided here.

----

""")
        entries = sorted([self.step_document_prefix + module.name
                          for module in step_modules])
        document.write_toctree(entries, maxdepth=1)
        document.close()
        if self.stdout_mode:
            sys.stdout.write("\n%s\n" % self.document_separator)

    def write_step_module(self, step_module):
        self.ensure_document_is_closed()
        document_name = self.step_document_prefix + step_module.name
        self.document = self.create_document(document_name)
        self.document.write(".. _docid.steps.%s:\n" % step_module.name)
        self.document.write_heading(step_module.name, index_id=step_module.name)
        if self.shows_step_module_info:
            self.document.write(":Module:   %s\n" % step_module.name)
            self.document.write(":Filename: %s\n" % step_module.filename)
            self.document.write("\n")
        if step_module.module_doc:
            module_doc = step_module.module_doc.strip()
            self.document.write("%s\n\n" % module_doc)
        if self.shows_step_module_overview:
            self.document.write_heading("Step Overview", level=1)
            self.write_step_module_overview(step_module.step_definitions)

        self.document.write_heading("Step Definitions", level=1)
        for step_definition in step_module.step_definitions:
            self.write_step_definition(step_definition)

        # -- FINALLY: Clean up resources.
        self.document.close()
        self.document = None
        if self.stdout_mode:
            sys.stdout.write("\n%s\n" % self.document_separator)

    def write_step_module_overview(self, step_definitions):
        assert self.document
        headings = [u"Step Definition", u"Given", u"When", u"Then", u"Step"]
        table = Table(headings)
        step_type_cols = {
            "given": [u"  x", u"  ",  u"  ",  u"  "],
            "when":  [u"  ",  u"  x", u"  ",  u"  "],
            "then":  [u"  ",  u"  ",  u"  x", u"  "],
            "step":  [u"  x", u"  x", u"  x", u"  x"],
        }
        for step_definition in step_definitions:
            row = [self.describe_step_definition(step_definition)]
            row.extend(step_type_cols[step_definition.step_type])
            table.add_row(row)
        self.document.write_table(table)

    @staticmethod
    def make_step_definition_index_id(step_definition):
        if step_definition.step_type == "step":
            index_kinds = ("Given", "When", "Then", "Step")
        else:
            keyword = step_definition.step_type.capitalize()
            index_kinds = (keyword,)

        schema = "single: %s%s; %s %s"
        index_parts = []
        for index_kind in index_kinds:
            keyword = index_kind
            word = " step"
            if index_kind == "Step":
                keyword = "Given/When/Then"
                word = ""
            part = schema % (index_kind, word, keyword, step_definition.string)
            index_parts.append(part)
        joiner = "\n    "
        return joiner + joiner.join(index_parts)

    def make_step_definition_doc(self, step_definition):
        doc = inspect.getdoc(step_definition.func)
        if not doc:
            doc = self.default_step_definition_doc
        doc = doc.strip()
        return doc

    def write_step_definition(self, step_definition):
        assert self.document
        step_text = self.describe_step_definition(step_definition)
        if step_text.startswith("* "):
            step_text = step_text[2:]
        index_id = None
        if self.make_step_index_entries:
            index_id = self.make_step_definition_index_id(step_definition)

        heading = step_text
        if self.step_heading_prefix:
            heading = self.step_heading_prefix + step_text
        self.document.write_heading(heading, level=2, index_id=index_id)
        step_definition_doc = self.make_step_definition_doc(step_definition)
        self.document.write("%s\n" % step_definition_doc)
        self.document.write("\n")


# -----------------------------------------------------------------------------
# CLASS: SphinxStepsFormatter
# -----------------------------------------------------------------------------
class SphinxStepsFormatter(AbstractStepsFormatter):
    """
    Provides formatter class that generates Sphinx-based documentation
    for all registered step definitions. The primary purpose is to:

      * help the step-library provider/writer
      * simplify self-documentation of step-libraries

    .. note::
        Supports dry-run mode.
        Supports destination directory mode to write multiple documents.
    """
    name = "sphinx.steps"
    description = "Generate sphinx-based documentation for step definitions."
    doc_generator_class = SphinxStepsDocumentGenerator

    def __init__(self, stream_opener, config):
        super(SphinxStepsFormatter, self).__init__(stream_opener, config)
        self.destdir = stream_opener.name

    @property
    def step_definitions(self):
        """
        Derive step definitions from step-registry.
        """
        steps = []
        for step_type, step_definitions in self.step_registry.steps.items():
            for step_definition in step_definitions:
                step_definition.step_type = step_type
                steps.append(step_definition)
        return steps

    # -- FORMATTER-API:
    def close(self):
        """Called at end of test run."""
        if not self.step_registry:
            self.discover_step_definitions()
        self.report()

    # -- SPECIFIC-API:
    def create_document_generator(self):
        generator_class = self.doc_generator_class
        if self.stdout_mode:
            return generator_class(self.step_definitions, stream=self.stream)
        else:
            return generator_class(self.step_definitions, destdir=self.destdir)

    def report(self):
        document_generator = self.create_document_generator()
        document_counts = document_generator.write_docs()
        if not self.stdout_mode:
            msg = "%s: Written %s document(s) into directory '%s'.\n"
            sys.stdout.write(msg % (self.name, document_counts, self.destdir))

########NEW FILE########
__FILENAME__ = sphinx_util
# -*- coding: utf-8 -*-
"""
Provides utility function for generating Sphinx-based documentation.
"""

from behave.textutil import compute_words_maxsize
import codecs


# -----------------------------------------------------------------------------
# SPHINX OUTPUT GENERATION FUNCTIONS:
# -----------------------------------------------------------------------------
class DocumentWriter(object):
    """
    Provides a simple "ReStructured Text Writer" to generate
    Sphinx-based documentation.
    """
    heading_styles = ["=", "=", "-", "~"]
    default_encoding = "utf-8"
    default_toctree_title = "**Contents:**"

    def __init__(self, stream, filename=None, should_close=True):
        self.stream = stream
        self.filename = filename
        self.should_close = should_close

    @classmethod
    def open(cls, filename, encoding=None):
        encoding = encoding or cls.default_encoding
        stream = codecs.open(filename, "wb", encoding)
        return cls(stream, filename)

    def write(self, *args):
        return self.stream.write(*args)

    def close(self):
        if self.stream and self.should_close:
            self.stream.close()
        self.stream = None

    def write_heading(self, heading, level=0, index_id=None):
        assert self.stream
        assert heading, "Heading should not be empty"
        assert 0 <= level < len(self.heading_styles)
        if level >= len(self.heading_styles):
            level = len(self.heading_styles) - 1
        heading_size = len(heading)
        heading_style = self.heading_styles[level]
        if level == 0 and heading_size < 70:
            heading_size = 70
        separator = heading_style * heading_size
        if index_id:
            if isinstance(index_id, (list, tuple)):
                index_id = ", ".join(index_id)
            self.stream.write(".. index:: %s\n\n" % index_id)
        if level == 0:
            self.stream.write("%s\n" % separator)
        self.stream.write("%s\n" % heading)
        self.stream.write("%s\n" % separator)
        self.stream.write("\n")

    def write_toctree(self, entries, title=None, maxdepth=2):
        if title is None:
            title  = self.default_toctree_title
        line_prefix = " " * 4
        if title:
            self.stream.write("%s\n\n" % title)
        self.stream.write(".. toctree::\n")
        self.stream.write("%s:maxdepth: %d\n\n" % (line_prefix, maxdepth))
        for entry in entries:
            self.stream.write("%s%s\n" % (line_prefix, entry))
        self.stream.write("\n")

    def write_table(self, table):
        """
        Write a ReST simple table.

        EXAMPLE:
        ========================================= ===== ===== ===== =====
        Step Definition                           Given When  Then  Step
        ========================================= ===== ===== ===== =====
        Given a file named "{filename}" contains
        Then the file "{filename}" should ...
        ========================================= ===== ===== ===== =====

        :param table:   Table to render (as `behave.model.Table`)

        .. todo::
            Column alignments
        """
        assert self.stream

        # -- STEP: Determine table layout dimensions
        cols_size = []
        separator_parts = []
        row_schema_parts = []
        for col_index, heading in enumerate(table.headings):
            column = [unicode(row[col_index]) for row in table.rows]
            column.append(heading)
            column_size = compute_words_maxsize(column)
            cols_size.append(column_size)
            separator_parts.append("=" * column_size)
            row_schema_parts.append("%-" + str(column_size) + "s")

        separator = " ".join(separator_parts) + "\n"
        row_schema = " ".join(row_schema_parts) + "\n"
        self.stream.write("\n")     # -- ENSURE: Empty line before table start.
        self.stream.write(separator)
        self.stream.write(row_schema % tuple(table.headings))
        self.stream.write(separator)
        for row in table.rows:
            self.stream.write(row_schema % tuple(row))
        self.stream.write(separator)
        self.stream.write("\n")     # -- ENSURE: Empty line after table end.

########NEW FILE########
__FILENAME__ = steps
# -*- coding: utf-8 -*-
"""
Provides a formatter that provides an overview of available step definitions
(step implementations).
"""

from behave.formatter.base import Formatter
from behave.step_registry import StepRegistry, registry
from behave.textutil import compute_words_maxsize, indent, make_indentation
from behave import i18n
from operator import attrgetter
import inspect


# -----------------------------------------------------------------------------
# CLASS: AbstractStepsFormatter
# -----------------------------------------------------------------------------
class AbstractStepsFormatter(Formatter):
    """
    Provides a formatter base class that provides the common functionality
    for formatter classes that operate on step definitions (implementations).

    .. note::
        Supports behave dry-run mode.
    """
    step_types = ("given", "when", "then", "step")

    def __init__(self, stream_opener, config):
        super(AbstractStepsFormatter, self).__init__(stream_opener, config)
        self.step_registry = None
        self.current_feature = None

    def reset(self):
        self.step_registry = None
        self.current_feature = None

    def discover_step_definitions(self):
        if self.step_registry is None:
            self.step_registry = StepRegistry()

        for step_type in registry.steps.keys():
            step_definitions = tuple(registry.steps[step_type])
            for step_definition in step_definitions:
                step_definition.step_type = step_type
            self.step_registry.steps[step_type] = step_definitions

    # -- FORMATTER API:
    def feature(self, feature):
        self.current_feature = feature
        if not self.step_registry:
            # -- ONLY-ONCE:
            self.discover_step_definitions()

    def eof(self):
        """Called at end of a feature."""
        self.current_feature = None

    def close(self):
        """Called at end of test run."""
        if not self.step_registry:
            self.discover_step_definitions()

        if self.step_registry:
            # -- ENSURE: Output stream is open.
            self.stream = self.open()
            self.report()

        # -- FINALLY:
        self.close_stream()

    # -- REPORT SPECIFIC-API:
    def report(self):
        raise NotImplementedError()

    @staticmethod
    def describe_step_definition(step_definition, step_type=None):
        if not step_type:
            step_type = step_definition.step_type
        assert step_type
        return u"@%s('%s')" % (step_type, step_definition.string)


# -----------------------------------------------------------------------------
# CLASS: StepsFormatter
# -----------------------------------------------------------------------------
class StepsFormatter(AbstractStepsFormatter):
    """
    Provides formatter class that provides an overview
    which step definitions are available.

    EXAMPLE:
        $ behave --dry-run -f steps features/
        GIVEN STEP DEFINITIONS[21]:
          Given a new working directory
          Given I use the current directory as working directory
          Given a file named "{filename}" with
          ...
          Given a step passes
          Given a step fails

        WHEN STEP DEFINITIONS[14]:
          When I run "{command}"
          ...
          When a step passes
          When a step fails

        THEN STEP DEFINITIONS[45]:
          Then the command should fail with returncode="{result:int}"
          Then it should pass with
          Then it should fail with
          Then the command output should contain "{text}"
          ...
          Then a step passes
          Then a step fails

        GENERIC STEP DEFINITIONS[13]:
          * I remove the directory "{directory}"
          * a file named "{filename}" exists
          * a file named "{filename}" does not exist
          ...
          * a step passes
          * a step fails

    .. note::
        Supports behave dry-run mode.
    """
    name = "steps"
    description = "Shows step definitions (step implementations)."
    shows_location = True
    min_location_column = 40

    # -- REPORT SPECIFIC-API:
    def report(self):
        self.report_steps_by_type()

    def report_steps_by_type(self):
        """
        Show an overview of the existing step implementations per step type.
        """
        assert set(self.step_types) == set(self.step_registry.steps.keys())
        language = self.config.lang or "en"
        language_keywords = i18n.languages[language]

        for step_type in self.step_types:
            steps = list(self.step_registry.steps[step_type])
            if step_type != "step":
                steps.extend(self.step_registry.steps["step"])
            if not steps:
                continue

            # -- PREPARE REPORT: For a step-type.
            step_type_name = step_type.upper()
            if step_type == "step":
                step_keyword = "*"
                step_type_name = "GENERIC"
            else:
                # step_keyword = step_type.capitalize()
                keywords = language_keywords[step_type]
                if keywords[0] == u"*":
                    assert len(keywords) > 1
                    step_keyword = keywords[1]
                else:
                    step_keyword = keywords[0]

            steps_text = [u"%s %s" % (step_keyword, step.string)
                          for step in steps]
            if self.shows_location:
                max_size = compute_words_maxsize(steps_text)
                if max_size < self.min_location_column:
                    max_size = self.min_location_column
                schema = u"  %-" + str(max_size) + "s  # %s\n"
            else:
                schema = u"  %s\n"

            # -- REPORT:
            message = "%s STEP DEFINITIONS[%s]:\n"
            self.stream.write(message % (step_type_name, len(steps)))
            for step, step_text in zip(steps, steps_text):
                if self.shows_location:
                    self.stream.write(schema % (step_text, step.location))
                else:
                    self.stream.write(schema % step_text)
            self.stream.write("\n")


# -----------------------------------------------------------------------------
# CLASS: StepsDocFormatter
# -----------------------------------------------------------------------------
class StepsDocFormatter(AbstractStepsFormatter):
    """
    Provides formatter class that shows the documentation of all registered
    step definitions. The primary purpose is to provide help for a test writer.

    EXAMPLE:
        $ behave --dry-run -f steps.doc features/
        @given('a file named "{filename}" with')
          Function: step_a_file_named_filename_with()
          Location: behave4cmd0/command_steps.py:50
            Creates a textual file with the content provided as docstring.

        @when('I run "{command}"')
          Function: step_i_run_command()
          Location: behave4cmd0/command_steps.py:80
            Run a command as subprocess, collect its output and returncode.

        @step('a file named "{filename}" exists')
          Function: step_file_named_filename_exists()
          Location: behave4cmd0/command_steps.py:305
            Verifies that a file with this filename exists.

            .. code-block:: gherkin

                Given a file named "abc.txt" exists
                 When a file named "abc.txt" exists
        ...

    .. note::
        Supports behave dry-run mode.
    """
    name = "steps.doc"
    description = "Shows documentation for step definitions."
    shows_location = True
    shows_function_name = True
    ordered_by_location = True
    doc_prefix = make_indentation(4)

    # -- REPORT SPECIFIC-API:
    def report(self):
        self.report_step_definition_docs()
        self.stream.write("\n")

    def report_step_definition_docs(self):
        step_definitions = []
        for step_type in self.step_types:
            for step_definition in self.step_registry.steps[step_type]:
                # step_definition.step_type = step_type
                assert step_definition.step_type is not None
                step_definitions.append(step_definition)

        if self.ordered_by_location:
            step_definitions = sorted(step_definitions,
                                      key=attrgetter("location"))

        for step_definition in step_definitions:
            self.write_step_definition(step_definition)

    def write_step_definition(self, step_definition):
        step_definition_text = self.describe_step_definition(step_definition)
        self.stream.write(u"%s\n" % step_definition_text)
        doc = inspect.getdoc(step_definition.func)
        func_name = step_definition.func.__name__
        if self.shows_function_name and func_name not in ("step", "impl"):
            self.stream.write(u"  Function: %s()\n" % func_name)
        if self.shows_location:
            self.stream.write(u"  Location: %s\n" % step_definition.location)
        if doc:
            doc = doc.strip()
            self.stream.write(indent(doc, self.doc_prefix))
            self.stream.write("\n")
        self.stream.write("\n")


# -----------------------------------------------------------------------------
# CLASS: StepsUsageFormatter
# -----------------------------------------------------------------------------
class StepsUsageFormatter(AbstractStepsFormatter):
    """
    Provides formatter class that shows how step definitions are used by steps.

    EXAMPLE:
        $ behave --dry-run -f steps.usage features/
        ...

    .. note::
        Supports behave dry-run mode.
    """
    name = "steps.usage"
    description = "Shows how step definitions are used by steps."
    doc_prefix = make_indentation(4)
    min_location_column = 40

    def __init__(self, stream_opener, config):
        super(StepsUsageFormatter, self).__init__(stream_opener, config)
        self.step_usage_database = {}
        self.undefined_steps = []

    def reset(self):
        super(StepsUsageFormatter, self).reset()
        self.step_usage_database = {}
        self.undefined_steps = []

    def get_step_type_for_step_definition(self, step_definition):
        step_type = step_definition.step_type
        if not step_type:
            # -- DETERMINE STEP-TYPE FROM STEP-REGISTRY:
            assert self.step_registry
            for step_type, values in self.step_registry.steps.items():
                if step_definition in values:
                    return step_type
            # -- OTHERWISE:
            step_type = "step"
        return step_type

    def select_unused_step_definitions(self):
        step_definitions = set()
        for step_type, values in self.step_registry.steps.items():
            step_definitions.update(values)
        used_step_definitions = set(self.step_usage_database.keys())
        unused_step_definitions = step_definitions - used_step_definitions
        return unused_step_definitions

    def update_usage_database(self, step_definition, step):
        matching_steps = self.step_usage_database.get(step_definition, None)
        if matching_steps is None:
            assert step_definition.step_type is not None
            matching_steps = self.step_usage_database[step_definition] = []
        # -- AVOID DUPLICATES: From Scenario Outlines
        if not steps_contain(matching_steps, step):
            matching_steps.append(step)

    def update_usage_database_for_step(self, step):
        step_definition = self.step_registry.find_step_definition(step)
        if step_definition:
            self.update_usage_database(step_definition, step)
        # elif step not in self.undefined_steps:
        elif not steps_contain(self.undefined_steps, step):
            # -- AVOID DUPLICATES: From Scenario Outlines
            self.undefined_steps.append(step)

    def update_usage_database_for_feature(self, feature):
        # -- PROCESS BACKGROUND (if exists): Use Background steps only once.
        if feature.background:
            for step in feature.background.steps:
                self.update_usage_database_for_step(step)

        # -- PROCESS SCENARIOS: Without background steps.
        for scenario in feature.walk_scenarios():
            for step in scenario.steps:
                self.update_usage_database_for_step(step)

    # -- FORMATTER API:
    def feature(self, feature):
        super(StepsUsageFormatter, self).feature(feature)
        self.update_usage_database_for_feature(feature)

    # -- REPORT API:
    def report(self):
        self.report_used_step_definitions()
        self.report_unused_step_definitions()
        self.report_undefined_steps()
        self.stream.write("\n")

    # -- REPORT SPECIFIC-API:
    def report_used_step_definitions(self):
        # -- STEP: Used step definitions.
        # ORDERING: Sort step definitions by file location.
        get_location = lambda x: x[0].location
        step_definition_items = self.step_usage_database.items()
        step_definition_items = sorted(step_definition_items, key=get_location)

        for step_definition, steps in step_definition_items:
            stepdef_text = self.describe_step_definition(step_definition)
            steps_text = [u"  %s %s" % (step.keyword, step.name)
                          for step in steps]
            steps_text.append(stepdef_text)
            max_size = compute_words_maxsize(steps_text)
            if max_size < self.min_location_column:
                max_size = self.min_location_column

            schema = u"%-" + str(max_size) + "s  # %s\n"
            self.stream.write(schema % (stepdef_text, step_definition.location))
            schema = u"%-" + str(max_size) + "s  # %s\n"
            for step, step_text in zip(steps, steps_text):
                self.stream.write(schema % (step_text, step.location))
            self.stream.write("\n")

    def report_unused_step_definitions(self):
        unused_step_definitions = self.select_unused_step_definitions()
        if not unused_step_definitions:
            return

        # -- STEP: Prepare report for unused step definitions.
        # ORDERING: Sort step definitions by file location.
        get_location = lambda x: x.location
        step_definitions = sorted(unused_step_definitions, key=get_location)
        step_texts = [self.describe_step_definition(step_definition)
                      for step_definition in step_definitions]

        max_size = compute_words_maxsize(step_texts)
        if max_size < self.min_location_column-2:
            max_size = self.min_location_column-2

        # -- STEP: Write report.
        schema = u"  %-" + str(max_size) + "s  # %s\n"
        self.stream.write("UNUSED STEP DEFINITIONS[%d]:\n" % len(step_texts))
        for step_definition, text in zip(step_definitions, step_texts):
            self.stream.write(schema % (text, step_definition.location))

    def report_undefined_steps(self):
        if not self.undefined_steps:
            return

        # -- STEP: Undefined steps.
        undefined_steps = sorted(self.undefined_steps,
                                 key=attrgetter("location"))

        steps_text = [u"  %s %s" % (step.keyword, step.name)
                      for step in undefined_steps]
        max_size = compute_words_maxsize(steps_text)
        if max_size < self.min_location_column:
            max_size = self.min_location_column

        self.stream.write("\nUNDEFINED STEPS[%d]:\n" % len(steps_text))
        schema = u"%-" + str(max_size) + "s  # %s\n"
        for step, step_text in zip(undefined_steps, steps_text):
            self.stream.write(schema % (step_text, step.location))

# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS:
# -----------------------------------------------------------------------------
def steps_contain(steps, step):
    for other_step in steps:
        if step == other_step and step.location == other_step.location:
            # -- NOTE: Step comparison does not take location into account.
            return True
    # -- OTHERWISE: Not contained yet (or step in other location).
    return False

########NEW FILE########
__FILENAME__ = tags
# -*- coding: utf-8 -*-
"""
Collects data how often a tag count is used and where.

EXAMPLE:

    $ behave --dry-run -f tag_counts features/
"""

from behave.formatter.base import Formatter
from behave.textutil import compute_words_maxsize


# -----------------------------------------------------------------------------
# CLASS: AbstractTagsFormatter
# -----------------------------------------------------------------------------
class AbstractTagsFormatter(Formatter):
    """
    Abstract base class for formatter that collect information on tags.

    .. note::
        Supports dry-run mode for faster feedback.
    """
    with_tag_inheritance = False

    def __init__(self, stream_opener, config):
        super(AbstractTagsFormatter, self).__init__(stream_opener, config)
        self.tag_counts = {}
        self._uri = None
        self._feature_tags = None
        self._scenario_outline_tags = None

    # -- Formatter API:
    def uri(self, uri):
        self._uri = uri

    def feature(self, feature):
        self._feature_tags = feature.tags
        self.record_tags(feature.tags, feature)

    def scenario(self, scenario):
        tags = set(scenario.tags)
        if self.with_tag_inheritance:
            tags.update(self._feature_tags)
        self.record_tags(tags, scenario)

    def scenario_outline(self, scenario_outline):
        self._scenario_outline_tags = scenario_outline.tags
        self.record_tags(scenario_outline.tags, scenario_outline)

    def examples(self, examples):
        tags = set(examples.tags)
        if self.with_tag_inheritance:
            tags.update(self._scenario_outline_tags)
            tags.update(self._feature_tags)
        self.record_tags(tags, examples)

    def close(self):
        """Emit tag count reports."""
        # -- ENSURE: Output stream is open.
        self.stream = self.open()
        self.report_tags()
        self.close_stream()

    # -- SPECIFIC API:
    def record_tags(self, tags, model_element):
        for tag in tags:
            if tag not in self.tag_counts:
                self.tag_counts[tag] = []
            self.tag_counts[tag].append(model_element)

    def report_tags(self):
        raise NotImplementedError


# -----------------------------------------------------------------------------
# CLASS: TagsFormatter
# -----------------------------------------------------------------------------
class TagsFormatter(AbstractTagsFormatter):
    """
    Formatter that collects information:

      * which tags exist
      * how often a tag is used (counts)
      * usage context/category: feature, scenario, ...

    .. note::
        Supports dry-run mode for faster feedback.
    """
    name = "tags"
    description = "Shows tags (and how often they are used)."
    with_tag_inheritance = False
    show_ordered_by_usage = False

    def report_tags(self):
        self.report_tag_counts()
        if self.show_ordered_by_usage:
            self.report_tag_counts_by_usage()

    @staticmethod
    def get_tag_count_details(tag_count):
        details = {}
        for element in tag_count:
            category = element.keyword.lower()
            if category not in details:
                details[category] = 0
            details[category] += 1

        parts = []
        if len(details) == 1:
            parts.append(details.keys()[0])
        else:
            for category in sorted(details.keys()):
                text = u"%s: %d" % (category, details[category])
                parts.append(text)
        return ", ".join(parts)

    def report_tag_counts(self):
        # -- PREPARE REPORT:
        ordered_tags = sorted(list(self.tag_counts.keys()))
        tag_maxsize = compute_words_maxsize(ordered_tags)
        schema = "  @%-" + str(tag_maxsize) + "s %4d    (used for %s)\n"

        # -- EMIT REPORT:
        self.stream.write("TAG COUNTS (alphabetically sorted):\n")
        for tag in ordered_tags:
            tag_data = self.tag_counts[tag]
            counts = len(tag_data)
            details = self.get_tag_count_details(tag_data)
            self.stream.write(schema % (tag, counts, details))
        self.stream.write("\n")

    def report_tag_counts_by_usage(self):
        # -- PREPARE REPORT:
        compare_tag_counts_size = lambda x: len(self.tag_counts[x])
        ordered_tags = sorted(list(self.tag_counts.keys()),
                              key=compare_tag_counts_size)
        tag_maxsize = compute_words_maxsize(ordered_tags)
        schema = "  @%-" + str(tag_maxsize) + "s %4d    (used for %s)\n"

        # -- EMIT REPORT:
        self.stream.write("TAG COUNTS (most often used first):\n")
        for tag in ordered_tags:
            tag_data = self.tag_counts[tag]
            counts = len(tag_data)
            details = self.get_tag_count_details(tag_data)
            self.stream.write(schema % (tag, counts, details))
        self.stream.write("\n")


# -----------------------------------------------------------------------------
# CLASS: TagsLocationFormatter
# -----------------------------------------------------------------------------
class TagsLocationFormatter(AbstractTagsFormatter):
    """
    Formatter that collects information:

      * which tags exist
      * where the tags are used (location)

    .. note::
        Supports dry-run mode for faster feedback.
    """
    name = "tags.location"
    description = "Shows tags and the location where they are used."
    with_tag_inheritance = False

    def report_tags(self):
        self.report_tags_by_locations()

    def report_tags_by_locations(self):
        # -- PREPARE REPORT:
        locations = set()
        for tag_elements in self.tag_counts.values():
            locations.update([unicode(x.location) for x in tag_elements])
        location_column_size = compute_words_maxsize(locations)
        schema = u"    %-" + str(location_column_size) + "s   %s\n"

        # -- EMIT REPORT:
        self.stream.write("TAG LOCATIONS (alphabetically ordered):\n")
        for tag in sorted(self.tag_counts.keys()):
            self.stream.write("  @%s:\n" % tag)
            for element in self.tag_counts[tag]:
                info = u"%s: %s" % (element.keyword, element.name)
                self.stream.write(schema % (element.location, info))
            self.stream.write("\n")
        self.stream.write("\n")

########NEW FILE########
__FILENAME__ = i18n
#-*- encoding: UTF-8 -*-

# file generated by convert_i18n_yaml.py from i18n.yaml

languages = \
{'ar': {'and': [u'*', u'\u0648'],
        'background': [u'\u0627\u0644\u062e\u0644\u0641\u064a\u0629'],
        'but': [u'*', u'\u0644\u0643\u0646'],
        'examples': [u'\u0627\u0645\u062b\u0644\u0629'],
        'feature': [u'\u062e\u0627\u0635\u064a\u0629'],
        'given': [u'*', u'\u0628\u0641\u0631\u0636'],
        'name': [u'Arabic'],
        'native': [u'\u0627\u0644\u0639\u0631\u0628\u064a\u0629'],
        'scenario': [u'\u0633\u064a\u0646\u0627\u0631\u064a\u0648'],
        'scenario_outline': [u'\u0633\u064a\u0646\u0627\u0631\u064a\u0648 \u0645\u062e\u0637\u0637'],
        'then': [u'*', u'\u0627\u0630\u0627\u064b', u'\u062b\u0645'],
        'when': [u'*',
                 u'\u0645\u062a\u0649',
                 u'\u0639\u0646\u062f\u0645\u0627']},
 'bg': {'and': [u'*', u'\u0418'],
        'background': [u'\u041f\u0440\u0435\u0434\u0438\u0441\u0442\u043e\u0440\u0438\u044f'],
        'but': [u'*', u'\u041d\u043e'],
        'examples': [u'\u041f\u0440\u0438\u043c\u0435\u0440\u0438'],
        'feature': [u'\u0424\u0443\u043d\u043a\u0446\u0438\u043e\u043d\u0430\u043b\u043d\u043e\u0441\u0442'],
        'given': [u'*', u'\u0414\u0430\u0434\u0435\u043d\u043e'],
        'name': [u'Bulgarian'],
        'native': [u'\u0431\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438'],
        'scenario': [u'\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439'],
        'scenario_outline': [u'\u0420\u0430\u043c\u043a\u0430 \u043d\u0430 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439'],
        'then': [u'*', u'\u0422\u043e'],
        'when': [u'*', u'\u041a\u043e\u0433\u0430\u0442\u043e']},
 'ca': {'and': [u'*', u'I'],
        'background': [u'Rerefons', u'Antecedents'],
        'but': [u'*', u'Per\xf2'],
        'examples': [u'Exemples'],
        'feature': [u'Caracter\xedstica', u'Funcionalitat'],
        'given': [u'*', u'Donat', u'Donada', u'At\xe8s', u'Atesa'],
        'name': [u'Catalan'],
        'native': [u'catal\xe0'],
        'scenario': [u'Escenari'],
        'scenario_outline': [u"Esquema de l'escenari"],
        'then': [u'*', u'Aleshores', u'Cal'],
        'when': [u'*', u'Quan']},
 'cs': {'and': [u'*', u'A', u'A tak\xe9'],
        'background': [u'Pozad\xed', u'Kontext'],
        'but': [u'*', u'Ale'],
        'examples': [u'P\u0159\xedklady'],
        'feature': [u'Po\u017eadavek'],
        'given': [u'*', u'Pokud'],
        'name': [u'Czech'],
        'native': [u'\u010cesky'],
        'scenario': [u'Sc\xe9n\xe1\u0159'],
        'scenario_outline': [u'N\xe1\u010drt Sc\xe9n\xe1\u0159e',
                             u'Osnova sc\xe9n\xe1\u0159e'],
        'then': [u'*', u'Pak'],
        'when': [u'*', u'Kdy\u017e']},
 'cy-GB': {'and': [u'*', u'A'],
           'background': [u'Cefndir'],
           'but': [u'*', u'Ond'],
           'examples': [u'Enghreifftiau'],
           'feature': [u'Arwedd'],
           'given': [u'*', u'Anrhegedig a'],
           'name': [u'Welsh'],
           'native': [u'Cymraeg'],
           'scenario': [u'Scenario'],
           'scenario_outline': [u'Scenario Amlinellol'],
           'then': [u'*', u'Yna'],
           'when': [u'*', u'Pryd']},
 'da': {'and': [u'*', u'Og'],
        'background': [u'Baggrund'],
        'but': [u'*', u'Men'],
        'examples': [u'Eksempler'],
        'feature': [u'Egenskab'],
        'given': [u'*', u'Givet'],
        'name': [u'Danish'],
        'native': [u'dansk'],
        'scenario': [u'Scenarie'],
        'scenario_outline': [u'Abstrakt Scenario'],
        'then': [u'*', u'S\xe5'],
        'when': [u'*', u'N\xe5r']},
 'de': {'and': [u'*', u'Und'],
        'background': [u'Grundlage'],
        'but': [u'*', u'Aber'],
        'examples': [u'Beispiele'],
        'feature': [u'Funktionalit\xe4t'],
        'given': [u'*', u'Angenommen', u'Gegeben sei'],
        'name': [u'German'],
        'native': [u'Deutsch'],
        'scenario': [u'Szenario'],
        'scenario_outline': [u'Szenariogrundriss'],
        'then': [u'*', u'Dann'],
        'when': [u'*', u'Wenn']},
 'en': {'and': [u'*', u'And'],
        'background': [u'Background'],
        'but': [u'*', u'But'],
        'examples': [u'Examples', u'Scenarios'],
        'feature': [u'Feature'],
        'given': [u'*', u'Given'],
        'name': [u'English'],
        'native': [u'English'],
        'scenario': [u'Scenario'],
        'scenario_outline': [u'Scenario Outline', u'Scenario Template'],
        'then': [u'*', u'Then'],
        'when': [u'*', u'When']},
 'en-Scouse': {'and': [u'*', u'An'],
               'background': [u'Dis is what went down'],
               'but': [u'*', u'Buh'],
               'examples': [u'Examples'],
               'feature': [u'Feature'],
               'given': [u'*', u'Givun', u'Youse know when youse got'],
               'name': [u'Scouse'],
               'native': [u'Scouse'],
               'scenario': [u'The thing of it is'],
               'scenario_outline': [u'Wharrimean is'],
               'then': [u'*', u'Dun', u'Den youse gotta'],
               'when': [u'*', u'Wun', u'Youse know like when']},
 'en-au': {'and': [u'*', u'N'],
           'background': [u'Background'],
           'but': [u'*', u'Cept'],
           'examples': [u'Cobber'],
           'feature': [u'Crikey'],
           'given': [u'*', u'Ya know how'],
           'name': [u'Australian'],
           'native': [u'Australian'],
           'scenario': [u'Mate'],
           'scenario_outline': [u'Blokes'],
           'then': [u'*', u'Ya gotta'],
           'when': [u'*', u'When']},
 'en-lol': {'and': [u'*', u'AN'],
            'background': [u'B4'],
            'but': [u'*', u'BUT'],
            'examples': [u'EXAMPLZ'],
            'feature': [u'OH HAI'],
            'given': [u'*', u'I CAN HAZ'],
            'name': [u'LOLCAT'],
            'native': [u'LOLCAT'],
            'scenario': [u'MISHUN'],
            'scenario_outline': [u'MISHUN SRSLY'],
            'then': [u'*', u'DEN'],
            'when': [u'*', u'WEN']},
 'en-pirate': {'and': [u'*', u'Aye'],
               'background': [u'Yo-ho-ho'],
               'but': [u'*', u'Avast!'],
               'examples': [u'Dead men tell no tales'],
               'feature': [u'Ahoy matey!'],
               'given': [u'*', u'Gangway!'],
               'name': [u'Pirate'],
               'native': [u'Pirate'],
               'scenario': [u'Heave to'],
               'scenario_outline': [u'Shiver me timbers'],
               'then': [u'*', u'Let go and haul'],
               'when': [u'*', u'Blimey!']},
 'en-tx': {'and': [u'*', u"And y'all"],
           'background': [u'Background'],
           'but': [u'*', u"But y'all"],
           'examples': [u'Examples'],
           'feature': [u'Feature'],
           'given': [u'*', u"Given y'all"],
           'name': [u'Texan'],
           'native': [u'Texan'],
           'scenario': [u'Scenario'],
           'scenario_outline': [u"All y'all"],
           'then': [u'*', u"Then y'all"],
           'when': [u'*', u"When y'all"]},
 'eo': {'and': [u'*', u'Kaj'],
        'background': [u'Fono'],
        'but': [u'*', u'Sed'],
        'examples': [u'Ekzemploj'],
        'feature': [u'Trajto'],
        'given': [u'*', u'Donita\u0135o'],
        'name': [u'Esperanto'],
        'native': [u'Esperanto'],
        'scenario': [u'Scenaro'],
        'scenario_outline': [u'Konturo de la scenaro'],
        'then': [u'*', u'Do'],
        'when': [u'*', u'Se']},
 'es': {'and': [u'*', u'Y'],
        'background': [u'Antecedentes'],
        'but': [u'*', u'Pero'],
        'examples': [u'Ejemplos'],
        'feature': [u'Caracter\xedstica'],
        'given': [u'*', u'Dado', u'Dada', u'Dados', u'Dadas'],
        'name': [u'Spanish'],
        'native': [u'espa\xf1ol'],
        'scenario': [u'Escenario'],
        'scenario_outline': [u'Esquema del escenario'],
        'then': [u'*', u'Entonces'],
        'when': [u'*', u'Cuando']},
 'et': {'and': [u'*', u'Ja'],
        'background': [u'Taust'],
        'but': [u'*', u'Kuid'],
        'examples': [u'Juhtumid'],
        'feature': [u'Omadus'],
        'given': [u'*', u'Eeldades'],
        'name': [u'Estonian'],
        'native': [u'eesti keel'],
        'scenario': [u'Stsenaarium'],
        'scenario_outline': [u'Raamstsenaarium'],
        'then': [u'*', u'Siis'],
        'when': [u'*', u'Kui']},
 'fi': {'and': [u'*', u'Ja'],
        'background': [u'Tausta'],
        'but': [u'*', u'Mutta'],
        'examples': [u'Tapaukset'],
        'feature': [u'Ominaisuus'],
        'given': [u'*', u'Oletetaan'],
        'name': [u'Finnish'],
        'native': [u'suomi'],
        'scenario': [u'Tapaus'],
        'scenario_outline': [u'Tapausaihio'],
        'then': [u'*', u'Niin'],
        'when': [u'*', u'Kun']},
 'fr': {'and': [u'*', u'Et'],
        'background': [u'Contexte'],
        'but': [u'*', u'Mais'],
        'examples': [u'Exemples'],
        'feature': [u'Fonctionnalit\xe9'],
        'given': [u'*',
                  u'Soit',
                  u'Etant donn\xe9',
                  u'Etant donn\xe9e',
                  u'Etant donn\xe9s',
                  u'Etant donn\xe9es',
                  u'\xc9tant donn\xe9',
                  u'\xc9tant donn\xe9e',
                  u'\xc9tant donn\xe9s',
                  u'\xc9tant donn\xe9es'],
        'name': [u'French'],
        'native': [u'fran\xe7ais'],
        'scenario': [u'Sc\xe9nario'],
        'scenario_outline': [u'Plan du sc\xe9nario', u'Plan du Sc\xe9nario'],
        'then': [u'*', u'Alors'],
        'when': [u'*', u'Quand', u'Lorsque', u"Lorsqu'<"]},
 'he': {'and': [u'*', u'\u05d5\u05d2\u05dd'],
        'background': [u'\u05e8\u05e7\u05e2'],
        'but': [u'*', u'\u05d0\u05d1\u05dc'],
        'examples': [u'\u05d3\u05d5\u05d2\u05de\u05d0\u05d5\u05ea'],
        'feature': [u'\u05ea\u05db\u05d5\u05e0\u05d4'],
        'given': [u'*', u'\u05d1\u05d4\u05d9\u05e0\u05ea\u05df'],
        'name': [u'Hebrew'],
        'native': [u'\u05e2\u05d1\u05e8\u05d9\u05ea'],
        'scenario': [u'\u05ea\u05e8\u05d7\u05d9\u05e9'],
        'scenario_outline': [u'\u05ea\u05d1\u05e0\u05d9\u05ea \u05ea\u05e8\u05d7\u05d9\u05e9'],
        'then': [u'*', u'\u05d0\u05d6', u'\u05d0\u05d6\u05d9'],
        'when': [u'*', u'\u05db\u05d0\u05e9\u05e8']},
 'hr': {'and': [u'*', u'I'],
        'background': [u'Pozadina'],
        'but': [u'*', u'Ali'],
        'examples': [u'Primjeri', u'Scenariji'],
        'feature': [u'Osobina', u'Mogu\u0107nost', u'Mogucnost'],
        'given': [u'*', u'Zadan', u'Zadani', u'Zadano'],
        'name': [u'Croatian'],
        'native': [u'hrvatski'],
        'scenario': [u'Scenarij'],
        'scenario_outline': [u'Skica', u'Koncept'],
        'then': [u'*', u'Onda'],
        'when': [u'*', u'Kada', u'Kad']},
 'hu': {'and': [u'*', u'\xc9s'],
        'background': [u'H\xe1tt\xe9r'],
        'but': [u'*', u'De'],
        'examples': [u'P\xe9ld\xe1k'],
        'feature': [u'Jellemz\u0151'],
        'given': [u'*', u'Amennyiben', u'Adott'],
        'name': [u'Hungarian'],
        'native': [u'magyar'],
        'scenario': [u'Forgat\xf3k\xf6nyv'],
        'scenario_outline': [u'Forgat\xf3k\xf6nyv v\xe1zlat'],
        'then': [u'*', u'Akkor'],
        'when': [u'*', u'Majd', u'Ha', u'Amikor']},
 'id': {'and': [u'*', u'Dan'],
        'background': [u'Dasar'],
        'but': [u'*', u'Tapi'],
        'examples': [u'Contoh'],
        'feature': [u'Fitur'],
        'given': [u'*', u'Dengan'],
        'name': [u'Indonesian'],
        'native': [u'Bahasa Indonesia'],
        'scenario': [u'Skenario'],
        'scenario_outline': [u'Skenario konsep'],
        'then': [u'*', u'Maka'],
        'when': [u'*', u'Ketika']},
 'is': {'and': [u'*', u'Og'],
        'background': [u'Bakgrunnur'],
        'but': [u'*', u'En'],
        'examples': [u'D\xe6mi', u'Atbur\xf0ar\xe1sir'],
        'feature': [u'Eiginleiki'],
        'given': [u'*', u'Ef'],
        'name': [u'Icelandic'],
        'native': [u'\xcdslenska'],
        'scenario': [u'Atbur\xf0ar\xe1s'],
        'scenario_outline': [u'L\xfdsing Atbur\xf0ar\xe1sar',
                             u'L\xfdsing D\xe6ma'],
        'then': [u'*', u'\xde\xe1'],
        'when': [u'*', u'\xdeegar']},
 'it': {'and': [u'*', u'E'],
        'background': [u'Contesto'],
        'but': [u'*', u'Ma'],
        'examples': [u'Esempi'],
        'feature': [u'Funzionalit\xe0'],
        'given': [u'*', u'Dato', u'Data', u'Dati', u'Date'],
        'name': [u'Italian'],
        'native': [u'italiano'],
        'scenario': [u'Scenario'],
        'scenario_outline': [u'Schema dello scenario'],
        'then': [u'*', u'Allora'],
        'when': [u'*', u'Quando']},
 'ja': {'and': [u'*', u'\u304b\u3064<'],
        'background': [u'\u80cc\u666f'],
        'but': [u'*',
                u'\u3057\u304b\u3057<',
                u'\u4f46\u3057<',
                u'\u305f\u3060\u3057<'],
        'examples': [u'\u4f8b', u'\u30b5\u30f3\u30d7\u30eb'],
        'feature': [u'\u30d5\u30a3\u30fc\u30c1\u30e3', u'\u6a5f\u80fd'],
        'given': [u'*', u'\u524d\u63d0<'],
        'name': [u'Japanese'],
        'native': [u'\u65e5\u672c\u8a9e'],
        'scenario': [u'\u30b7\u30ca\u30ea\u30aa'],
        'scenario_outline': [u'\u30b7\u30ca\u30ea\u30aa\u30a2\u30a6\u30c8\u30e9\u30a4\u30f3',
                             u'\u30b7\u30ca\u30ea\u30aa\u30c6\u30f3\u30d7\u30ec\u30fc\u30c8',
                             u'\u30c6\u30f3\u30d7\u30ec',
                             u'\u30b7\u30ca\u30ea\u30aa\u30c6\u30f3\u30d7\u30ec'],
        'then': [u'*', u'\u306a\u3089\u3070<'],
        'when': [u'*', u'\u3082\u3057<']},
 'ko': {'and': [u'*', u'\uadf8\ub9ac\uace0<'],
        'background': [u'\ubc30\uacbd'],
        'but': [u'*', u'\ud558\uc9c0\ub9cc<', u'\ub2e8<'],
        'examples': [u'\uc608'],
        'feature': [u'\uae30\ub2a5'],
        'given': [u'*', u'\uc870\uac74<', u'\uba3c\uc800<'],
        'name': [u'Korean'],
        'native': [u'\ud55c\uad6d\uc5b4'],
        'scenario': [u'\uc2dc\ub098\ub9ac\uc624'],
        'scenario_outline': [u'\uc2dc\ub098\ub9ac\uc624 \uac1c\uc694'],
        'then': [u'*', u'\uadf8\ub7ec\uba74<'],
        'when': [u'*', u'\ub9cc\uc77c<', u'\ub9cc\uc57d<']},
 'lt': {'and': [u'*', u'Ir'],
        'background': [u'Kontekstas'],
        'but': [u'*', u'Bet'],
        'examples': [u'Pavyzd\u017eiai', u'Scenarijai', u'Variantai'],
        'feature': [u'Savyb\u0117'],
        'given': [u'*', u'Duota'],
        'name': [u'Lithuanian'],
        'native': [u'lietuvi\u0173 kalba'],
        'scenario': [u'Scenarijus'],
        'scenario_outline': [u'Scenarijaus \u0161ablonas'],
        'then': [u'*', u'Tada'],
        'when': [u'*', u'Kai']},
 'lu': {'and': [u'*', u'an', u'a'],
        'background': [u'Hannergrond'],
        'but': [u'*', u'awer', u'm\xe4'],
        'examples': [u'Beispiller'],
        'feature': [u'Funktionalit\xe9it'],
        'given': [u'*', u'ugeholl'],
        'name': [u'Luxemburgish'],
        'native': [u'L\xebtzebuergesch'],
        'scenario': [u'Szenario'],
        'scenario_outline': [u'Plang vum Szenario'],
        'then': [u'*', u'dann'],
        'when': [u'*', u'wann']},
 'lv': {'and': [u'*', u'Un'],
        'background': [u'Konteksts', u'Situ\u0101cija'],
        'but': [u'*', u'Bet'],
        'examples': [u'Piem\u0113ri', u'Paraugs'],
        'feature': [u'Funkcionalit\u0101te', u'F\u012b\u010da'],
        'given': [u'*', u'Kad'],
        'name': [u'Latvian'],
        'native': [u'latvie\u0161u'],
        'scenario': [u'Scen\u0101rijs'],
        'scenario_outline': [u'Scen\u0101rijs p\u0113c parauga'],
        'then': [u'*', u'Tad'],
        'when': [u'*', u'Ja']},
 'nl': {'and': [u'*', u'En'],
        'background': [u'Achtergrond'],
        'but': [u'*', u'Maar'],
        'examples': [u'Voorbeelden'],
        'feature': [u'Functionaliteit'],
        'given': [u'*', u'Gegeven', u'Stel'],
        'name': [u'Dutch'],
        'native': [u'Nederlands'],
        'scenario': [u'Scenario'],
        'scenario_outline': [u'Abstract Scenario'],
        'then': [u'*', u'Dan'],
        'when': [u'*', u'Als']},
 'no': {'and': [u'*', u'Og'],
        'background': [u'Bakgrunn'],
        'but': [u'*', u'Men'],
        'examples': [u'Eksempler'],
        'feature': [u'Egenskap'],
        'given': [u'*', u'Gitt'],
        'name': [u'Norwegian'],
        'native': [u'norsk'],
        'scenario': [u'Scenario'],
        'scenario_outline': [u'Scenariomal', u'Abstrakt Scenario'],
        'then': [u'*', u'S\xe5'],
        'when': [u'*', u'N\xe5r']},
 'pl': {'and': [u'*', u'Oraz', u'I'],
        'background': [u'Za\u0142o\u017cenia'],
        'but': [u'*', u'Ale'],
        'examples': [u'Przyk\u0142ady'],
        'feature': [u'W\u0142a\u015bciwo\u015b\u0107'],
        'given': [u'*', u'Zak\u0142adaj\u0105c', u'Maj\u0105c'],
        'name': [u'Polish'],
        'native': [u'polski'],
        'scenario': [u'Scenariusz'],
        'scenario_outline': [u'Szablon scenariusza'],
        'then': [u'*', u'Wtedy'],
        'when': [u'*', u'Je\u017celi', u'Je\u015bli']},
 'pt': {'and': [u'*', u'E'],
        'background': [u'Contexto'],
        'but': [u'*', u'Mas'],
        'examples': [u'Exemplos'],
        'feature': [u'Funcionalidade'],
        'given': [u'*', u'Dado', u'Dada', u'Dados', u'Dadas'],
        'name': [u'Portuguese'],
        'native': [u'portugu\xeas'],
        'scenario': [u'Cen\xe1rio', u'Cenario'],
        'scenario_outline': [u'Esquema do Cen\xe1rio', u'Esquema do Cenario'],
        'then': [u'*', u'Ent\xe3o', u'Entao'],
        'when': [u'*', u'Quando']},
 'ro': {'and': [u'*', u'Si', u'\u0218i', u'\u015ei'],
        'background': [u'Context'],
        'but': [u'*', u'Dar'],
        'examples': [u'Exemple'],
        'feature': [u'Functionalitate',
                    u'Func\u021bionalitate',
                    u'Func\u0163ionalitate'],
        'given': [u'*',
                  u'Date fiind',
                  u'Dat fiind',
                  u'Dati fiind',
                  u'Da\u021bi fiind',
                  u'Da\u0163i fiind'],
        'name': [u'Romanian'],
        'native': [u'rom\xe2n\u0103'],
        'scenario': [u'Scenariu'],
        'scenario_outline': [u'Structura scenariu',
                             u'Structur\u0103 scenariu'],
        'then': [u'*', u'Atunci'],
        'when': [u'*', u'Cand', u'C\xe2nd']},
 'ru': {'and': [u'*',
                u'\u0418',
                u'\u041a \u0442\u043e\u043c\u0443 \u0436\u0435'],
        'background': [u'\u041f\u0440\u0435\u0434\u044b\u0441\u0442\u043e\u0440\u0438\u044f',
                       u'\u041a\u043e\u043d\u0442\u0435\u043a\u0441\u0442'],
        'but': [u'*', u'\u041d\u043e', u'\u0410'],
        'examples': [u'\u041f\u0440\u0438\u043c\u0435\u0440\u044b'],
        'feature': [u'\u0424\u0443\u043d\u043a\u0446\u0438\u044f',
                    u'\u0424\u0443\u043d\u043a\u0446\u0438\u043e\u043d\u0430\u043b',
                    u'\u0421\u0432\u043e\u0439\u0441\u0442\u0432\u043e'],
        'given': [u'*',
                  u'\u0414\u043e\u043f\u0443\u0441\u0442\u0438\u043c',
                  u'\u0414\u0430\u043d\u043e',
                  u'\u041f\u0443\u0441\u0442\u044c'],
        'name': [u'Russian'],
        'native': [u'\u0440\u0443\u0441\u0441\u043a\u0438\u0439'],
        'scenario': [u'\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439'],
        'scenario_outline': [u'\u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f'],
        'then': [u'*', u'\u0422\u043e', u'\u0422\u043e\u0433\u0434\u0430'],
        'when': [u'*',
                 u'\u0415\u0441\u043b\u0438',
                 u'\u041a\u043e\u0433\u0434\u0430']},
 'sk': {'and': [u'*', u'A'],
        'background': [u'Pozadie'],
        'but': [u'*', u'Ale'],
        'examples': [u'Pr\xedklady'],
        'feature': [u'Po\u017eiadavka'],
        'given': [u'*', u'Pokia\u013e'],
        'name': [u'Slovak'],
        'native': [u'Slovensky'],
        'scenario': [u'Scen\xe1r'],
        'scenario_outline': [u'N\xe1\u010drt Scen\xe1ru'],
        'then': [u'*', u'Tak'],
        'when': [u'*', u'Ke\u010f']},
 'sr-Cyrl': {'and': [u'*', u'\u0418'],
             'background': [u'\u041a\u043e\u043d\u0442\u0435\u043a\u0441\u0442',
                            u'\u041e\u0441\u043d\u043e\u0432\u0430',
                            u'\u041f\u043e\u0437\u0430\u0434\u0438\u043d\u0430'],
             'but': [u'*', u'\u0410\u043b\u0438'],
             'examples': [u'\u041f\u0440\u0438\u043c\u0435\u0440\u0438',
                          u'\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0458\u0438'],
             'feature': [u'\u0424\u0443\u043d\u043a\u0446\u0438\u043e\u043d\u0430\u043b\u043d\u043e\u0441\u0442',
                         u'\u041c\u043e\u0433\u0443\u045b\u043d\u043e\u0441\u0442',
                         u'\u041e\u0441\u043e\u0431\u0438\u043d\u0430'],
             'given': [u'*',
                       u'\u0417\u0430\u0434\u0430\u0442\u043e',
                       u'\u0417\u0430\u0434\u0430\u0442\u0435',
                       u'\u0417\u0430\u0434\u0430\u0442\u0438'],
             'name': [u'Serbian'],
             'native': [u'\u0421\u0440\u043f\u0441\u043a\u0438'],
             'scenario': [u'\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u043e',
                          u'\u041f\u0440\u0438\u043c\u0435\u0440'],
             'scenario_outline': [u'\u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0458\u0430',
                                  u'\u0421\u043a\u0438\u0446\u0430',
                                  u'\u041a\u043e\u043d\u0446\u0435\u043f\u0442'],
             'then': [u'*', u'\u041e\u043d\u0434\u0430'],
             'when': [u'*',
                      u'\u041a\u0430\u0434\u0430',
                      u'\u041a\u0430\u0434']},
 'sr-Latn': {'and': [u'*', u'I'],
             'background': [u'Kontekst', u'Osnova', u'Pozadina'],
             'but': [u'*', u'Ali'],
             'examples': [u'Primeri', u'Scenariji'],
             'feature': [u'Funkcionalnost',
                         u'Mogu\u0107nost',
                         u'Mogucnost',
                         u'Osobina'],
             'given': [u'*', u'Zadato', u'Zadate', u'Zatati'],
             'name': [u'Serbian (Latin)'],
             'native': [u'Srpski (Latinica)'],
             'scenario': [u'Scenario', u'Primer'],
             'scenario_outline': [u'Struktura scenarija',
                                  u'Skica',
                                  u'Koncept'],
             'then': [u'*', u'Onda'],
             'when': [u'*', u'Kada', u'Kad']},
 'sv': {'and': [u'*', u'Och'],
        'background': [u'Bakgrund'],
        'but': [u'*', u'Men'],
        'examples': [u'Exempel'],
        'feature': [u'Egenskap'],
        'given': [u'*', u'Givet'],
        'name': [u'Swedish'],
        'native': [u'Svenska'],
        'scenario': [u'Scenario'],
        'scenario_outline': [u'Abstrakt Scenario', u'Scenariomall'],
        'then': [u'*', u'S\xe5'],
        'when': [u'*', u'N\xe4r']},
 'tr': {'and': [u'*', u'Ve'],
        'background': [u'Ge\xe7mi\u015f'],
        'but': [u'*', u'Fakat', u'Ama'],
        'examples': [u'\xd6rnekler'],
        'feature': [u'\xd6zellik'],
        'given': [u'*', u'Diyelim ki'],
        'name': [u'Turkish'],
        'native': [u'T\xfcrk\xe7e'],
        'scenario': [u'Senaryo'],
        'scenario_outline': [u'Senaryo tasla\u011f\u0131'],
        'then': [u'*', u'O zaman'],
        'when': [u'*', u'E\u011fer ki']},
 'uk': {'and': [u'*',
                u'\u0406',
                u'\u0410 \u0442\u0430\u043a\u043e\u0436',
                u'\u0422\u0430'],
        'background': [u'\u041f\u0435\u0440\u0435\u0434\u0443\u043c\u043e\u0432\u0430'],
        'but': [u'*', u'\u0410\u043b\u0435'],
        'examples': [u'\u041f\u0440\u0438\u043a\u043b\u0430\u0434\u0438'],
        'feature': [u'\u0424\u0443\u043d\u043a\u0446\u0456\u043e\u043d\u0430\u043b'],
        'given': [u'*',
                  u'\u041f\u0440\u0438\u043f\u0443\u0441\u0442\u0438\u043c\u043e',
                  u'\u041f\u0440\u0438\u043f\u0443\u0441\u0442\u0438\u043c\u043e, \u0449\u043e',
                  u'\u041d\u0435\u0445\u0430\u0439',
                  u'\u0414\u0430\u043d\u043e'],
        'name': [u'Ukrainian'],
        'native': [u'\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430'],
        'scenario': [u'\u0421\u0446\u0435\u043d\u0430\u0440\u0456\u0439'],
        'scenario_outline': [u'\u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430 \u0441\u0446\u0435\u043d\u0430\u0440\u0456\u044e'],
        'then': [u'*', u'\u0422\u043e', u'\u0422\u043e\u0434\u0456'],
        'when': [u'*',
                 u'\u042f\u043a\u0449\u043e',
                 u'\u041a\u043e\u043b\u0438']},
 'uz': {'and': [u'*', u'\u0412\u0430'],
        'background': [u'\u0422\u0430\u0440\u0438\u0445'],
        'but': [u'*',
                u'\u041b\u0435\u043a\u0438\u043d',
                u'\u0411\u0438\u0440\u043e\u043a',
                u'\u0410\u043c\u043c\u043e'],
        'examples': [u'\u041c\u0438\u0441\u043e\u043b\u043b\u0430\u0440'],
        'feature': [u'\u0424\u0443\u043d\u043a\u0446\u0438\u043e\u043d\u0430\u043b'],
        'given': [u'*', u'\u0410\u0433\u0430\u0440'],
        'name': [u'Uzbek'],
        'native': [u'\u0423\u0437\u0431\u0435\u043a\u0447\u0430'],
        'scenario': [u'\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439'],
        'scenario_outline': [u'\u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430\u0441\u0438'],
        'then': [u'*', u'\u0423\u043d\u0434\u0430'],
        'when': [u'*', u'\u0410\u0433\u0430\u0440']},
 'vi': {'and': [u'*', u'V\xe0'],
        'background': [u'B\u1ed1i c\u1ea3nh'],
        'but': [u'*', u'Nh\u01b0ng'],
        'examples': [u'D\u1eef li\u1ec7u'],
        'feature': [u'T\xednh n\u0103ng'],
        'given': [u'*', u'Bi\u1ebft', u'Cho'],
        'name': [u'Vietnamese'],
        'native': [u'Ti\u1ebfng Vi\u1ec7t'],
        'scenario': [u'T\xecnh hu\u1ed1ng', u'K\u1ecbch b\u1ea3n'],
        'scenario_outline': [u'Khung t\xecnh hu\u1ed1ng',
                             u'Khung k\u1ecbch b\u1ea3n'],
        'then': [u'*', u'Th\xec'],
        'when': [u'*', u'Khi']},
 'zh-CN': {'and': [u'*', u'\u800c\u4e14<'],
           'background': [u'\u80cc\u666f'],
           'but': [u'*', u'\u4f46\u662f<'],
           'examples': [u'\u4f8b\u5b50'],
           'feature': [u'\u529f\u80fd'],
           'given': [u'*', u'\u5047\u5982<'],
           'name': [u'Chinese simplified'],
           'native': [u'\u7b80\u4f53\u4e2d\u6587'],
           'scenario': [u'\u573a\u666f'],
           'scenario_outline': [u'\u573a\u666f\u5927\u7eb2'],
           'then': [u'*', u'\u90a3\u4e48<'],
           'when': [u'*', u'\u5f53<']},
 'zh-TW': {'and': [u'*', u'\u800c\u4e14<', u'\u4e26\u4e14<'],
           'background': [u'\u80cc\u666f'],
           'but': [u'*', u'\u4f46\u662f<'],
           'examples': [u'\u4f8b\u5b50'],
           'feature': [u'\u529f\u80fd'],
           'given': [u'*', u'\u5047\u8a2d<'],
           'name': [u'Chinese traditional'],
           'native': [u'\u7e41\u9ad4\u4e2d\u6587'],
           'scenario': [u'\u5834\u666f', u'\u5287\u672c'],
           'scenario_outline': [u'\u5834\u666f\u5927\u7db1',
                                u'\u5287\u672c\u5927\u7db1'],
           'then': [u'*', u'\u90a3\u9ebc<'],
           'when': [u'*', u'\u7576<']}}

########NEW FILE########
__FILENAME__ = importer
# -*- coding: utf-8 -*-
"""
Importer module for lazy-loading/importing modules and objects.

REQUIRES: importlib (provided in Python2.7, Python3.2...)
"""

from behave.compat import importlib


class Unknown(object):
    pass


class LazyObject(object):
    """
    Provides a placeholder for an object that should be loaded lazily.
    """

    def __init__(self, module_name, object_name=None):
        if ":" in module_name and not object_name:
            module_name, object_name = module_name.split(":")
        assert ":" not in module_name
        self.module_name = module_name
        self.object_name = object_name
        self.obj = None

    @staticmethod
    def load_module(module_name):
        return importlib.import_module(module_name)

    def __get__(self, obj=None, type=None):
        """
        Implement descriptor protocol,
        useful if this class is used as attribute.
        :return: Real object (lazy-loaded if necessary).
        :raise ImportError: If module or object cannot be imported.
        """
        __pychecker__ = "unusednames=obj,type"
        if not self.obj:
            # -- SETUP-ONCE: Lazy load the real object.
            module = self.load_module(self.module_name)
            obj = getattr(module, self.object_name, Unknown)
            if obj is Unknown:
                msg = "%s: %s is Unknown" % (self.module_name, self.object_name)
                raise ImportError(msg)
            self.obj = obj
        return obj

    def __set__(self, obj, value):
        """
        Implement descriptor protocol.
        """
        __pychecker__ = "unusednames=obj"
        self.obj = value

    def get(self):
        return self.__get__()


class LazyDict(dict):
    """
    Provides a dict that supports lazy loading of objects.
    A LazyObject is provided as placeholder for a value that should be
    loaded lazily.
    """

    def __getitem__(self, key):
        """
        Provides access to stored dict values.
        Implements lazy loading of item value (if necessary).
        When lazy object is loaded, its value with the dict is replaced
        with the real value.

        :param key:  Key to access the value of an item in the dict.
        :return: value
        :raises: KeyError if item is not found
        :raises: ImportError for a LazyObject that cannot be imported.
        """
        value = dict.__getitem__(self, key)
        if isinstance(value, LazyObject):
            # -- LAZY-LOADING MECHANISM: Load object and replace with lazy one.
            value = value.__get__()
            self[key] = value
        return value

########NEW FILE########
__FILENAME__ = json_parser
# -*- coding: utf-8 -*-
"""
Read behave's JSON output files and store retrieved information in
:mod:`behave.model` elements.

Utility to retrieve runtime information from behave's JSON output.

REQUIRES: Python >= 2.6 (json module is part of Python standard library)
"""

__author__    = "Jens Engel"


# -- IMPORTS:
from behave import model
import codecs
try:
    import json
except ImportError:
    # -- PYTHON 2.5 backward compatible: Use simplejson module.
    import simplejson as json


# ----------------------------------------------------------------------------
# FUNCTIONS:
# ----------------------------------------------------------------------------
def parse(json_filename, encoding="UTF-8"):
    """
    Reads behave JSON output file back in and stores information in
    behave model elements.

    :param json_filename:  JSON filename to process.
    :return: List of feature objects.
    """
    with codecs.open(json_filename, "rU", encoding=encoding) as fp:
        json_data = json.load(fp, encoding=encoding)
        json_processor = JsonParser()
        features = json_processor.parse_features(json_data)
        return features


# ----------------------------------------------------------------------------
# CLASSES:
# ----------------------------------------------------------------------------
class JsonParser(object):

    def parse_features(self, json_data):
        assert isinstance(json_data, list)
        features = []
        json_features = json_data
        for json_feature in json_features:
            feature = self.parse_feature(json_feature)
            features.append(feature)
        return features

    def parse_feature(self, json_feature):
        name = json_feature.get("name", u"")
        keyword = json_feature.get("keyword", None)
        tags = json_feature.get("tags", [])
        description = json_feature.get("description", [])
        location = json_feature.get("location", u"")
        filename, line = location.split(":")
        feature = model.Feature(filename, line, keyword, name, tags, description)

        json_elements = json_feature.get("elements", [])
        for json_element in json_elements:
            self.add_feature_element(feature, json_element)
        return feature


    def add_feature_element(self, feature, json_element):
        datatype = json_element.get("type", u"")
        category = datatype.lower()
        if category == "background":
            background = self.parse_background(json_element)
            feature.background = background
        elif category == "scenario":
            scenario = self.parse_scenario(json_element)
            feature.add_scenario(scenario)
        elif category == "scenario_outline":
            scenario_outline = self.parse_scenario_outline(json_element)
            feature.add_scenario(scenario_outline)
            self.current_scenario_outline = scenario_outline
        # elif category == "examples":
        #     examples = self.parse_examples(json_element)
        #     self.current_scenario_outline.examples = examples
        else:
            raise KeyError("Invalid feature-element keyword: %s" % category)


    def parse_background(self, json_element):
        """
        self.add_feature_element({
            'keyword': background.keyword,
            'location': background.location,
            'steps': [],
        })
        """
        keyword = json_element.get("keyword", u"")
        name    = json_element.get("name", u"")
        location = json_element.get("location", u"")
        json_steps = json_element.get("steps", [])
        steps = self.parse_steps(json_steps)
        filename, line = location.split(":")
        background = model.Background(filename, line, keyword, name, steps)
        return background

    def parse_scenario(self, json_element):
        """
        self.add_feature_element({
            'keyword': scenario.keyword,
            'name': scenario.name,
            'tags': scenario.tags,
            'location': scenario.location,
            'steps': [],
        })
        """
        keyword = json_element.get("keyword", u"")
        name    = json_element.get("name", u"")
        description = json_element.get("description", [])
        tags    = json_element.get("tags", [])
        location = json_element.get("location", u"")
        json_steps = json_element.get("steps", [])
        steps = self.parse_steps(json_steps)
        filename, line = location.split(":")
        scenario = model.Scenario(filename, line, keyword, name, tags, steps)
        scenario.description = description
        return scenario

    def parse_scenario_outline(self, json_element):
        """
        self.add_feature_element({
            'keyword': scenario_outline.keyword,
            'name': scenario_outline.name,
            'tags': scenario_outline.tags,
            'location': scenario_outline.location,
            'steps': [],
            'examples': [],
        })
        """
        keyword = json_element.get("keyword", u"")
        name    = json_element.get("name", u"")
        description = json_element.get("description", [])
        tags    = json_element.get("tags", [])
        location = json_element.get("location", u"")
        json_steps = json_element.get("steps", [])
        json_examples = json_element.get("examples", [])
        steps = self.parse_steps(json_steps)
        examples = []
        if json_examples:
            examples = self.parse_examples(json_examples)
        filename, line = location.split(":")
        scenario_outline = model.ScenarioOutline(filename, line, keyword, name,
                                tags=tags, steps=steps, examples=examples)
        scenario_outline.description = description
        return scenario_outline

    def parse_steps(self, json_steps):
        steps = []
        for json_step in json_steps:
            step = self.parse_step(json_step)
            steps.append(step)
        return steps

    def parse_step(self, json_element):
        """
        s = {
            'keyword': step.keyword,
            'step_type': step.step_type,
            'name': step.name,
            'location': step.location,
        }

        if step.text:
            s['text'] = step.text
        if step.table:
            s['table'] = self.make_table(step.table)
        element = self.current_feature_element
        element['steps'].append(s)
        """
        keyword = json_element.get("keyword", u"")
        name    = json_element.get("name", u"")
        step_type = json_element.get("step_type", u"")
        location = json_element.get("location", u"")
        text = json_element.get("text", None)
        if isinstance(text, list):
            text = "\n".join(text)
        table = None
        json_table = json_element.get("table", None)
        if json_table:
            table = self.parse_table(json_table)
        filename, line = location.split(":")
        step = model.Step(filename, line, keyword, step_type, name)
        step.text = text
        step.table = table
        json_result = json_element.get("result", None)
        if json_result:
            self.add_step_result(step, json_result)
        return step

    def add_step_result(self, step, json_result):
        """
        steps = self.current_feature_element['steps']
        steps[self._step_index]['result'] = {
            'status': result.status,
            'duration': result.duration,
        }
        """
        status   = json_result.get("status", u"")
        duration = json_result.get("duration", 0)
        error_message = json_result.get("error_message", None)
        if isinstance(error_message, list):
            error_message = "\n".join(error_message)
        step.status = status
        step.duration = duration
        step.error_message = error_message

    def parse_table(self, json_table):
        """
        table_data = {
            'headings': table.headings,
            'rows': [ list(row) for row in table.rows ]
        }
        return table_data
        """
        headings = json_table.get("headings", [])
        rows    = json_table.get("rows", [])
        table = model.Table(headings, rows=rows)
        return table


    def parse_examples(self, json_element):
        """
        e = {
            'keyword': examples.keyword,
            'name': examples.name,
            'location': examples.location,
        }

        if examples.table:
            e['table'] = self.make_table(examples.table)

        element = self.current_feature_element
        element['examples'].append(e)
        """
        keyword = json_element.get("keyword", u"")
        name    = json_element.get("name", u"")
        location = json_element.get("location", u"")

        table = None
        json_table = json_element.get("table", None)
        if json_table:
            table = self.parse_table(json_table)
        filename, line = location.split(":")
        examples = model.Examples(filename, line, keyword, name, table)
        return examples



########NEW FILE########
__FILENAME__ = log_capture
import logging
import functools
from logging.handlers import BufferingHandler
import re

from behave.configuration import ConfigError


class RecordFilter(object):
    '''Implement logging record filtering as per the configuration
    --logging-filter option.
    '''
    def __init__(self, names):
        self.include = set()
        self.exclude = set()
        for name in names.split(','):
            if name[0] == '-':
                self.exclude.add(name[1:])
            else:
                self.include.add(name)

    def filter(self, record):
        if self.exclude:
            return record.name not in self.exclude
        return record.name in self.include


# originally from nostetsts logcapture plugin
class LoggingCapture(BufferingHandler):
    '''Capture logging events in a memory buffer for later display or query.

    Captured logging events are stored on the attribute
    :attr:`~LoggingCapture.buffer`:

    .. attribute:: buffer

       This is a list of captured logging events as `logging.LogRecords`_.

    .. _`logging.LogRecords`:
       http://docs.python.org/library/logging.html#logrecord-objects

    By default the format of the messages will be::

        '%(levelname)s:%(name)s:%(message)s'

    This may be overridden using standard logging formatter names in the
    configuration variable ``logging_format``.

    The level of logging captured is set to ``logging.NOTSET`` by default. You
    may override this using the configuration setting ``logging_level`` (which
    is set to a level name.)

    Finally there may be `filtering of logging events`__ specified by the
    configuration variable ``logging_filter``.

    .. __: behave.html#command-line-arguments

    '''
    def __init__(self, config, level=None):
        BufferingHandler.__init__(self, 1000)
        self.config = config
        self.old_handlers = []
        self.old_level = None

        # set my formatter
        fmt = datefmt = None
        if config.logging_format:
            fmt = config.logging_format
        else:
            fmt = '%(levelname)s:%(name)s:%(message)s'
        if config.logging_datefmt:
            datefmt = config.logging_datefmt
        fmt = logging.Formatter(fmt, datefmt)
        self.setFormatter(fmt)

        # figure the level we're logging at
        if level is not None:
            self.level = level
        elif config.logging_level:
            self.level = config.logging_level
        else:
            self.level = logging.NOTSET

        # construct my filter
        if config.logging_filter:
            self.addFilter(RecordFilter(config.logging_filter))

    def __nonzero__(self):
        return bool(self.buffer)

    def flush(self):
        pass  # do nothing

    def truncate(self):
        self.buffer = []

    def getvalue(self):
        return '\n'.join(self.formatter.format(r) for r in self.buffer)

    def findEvent(self, pattern):
        '''Search through the buffer for a message that matches the given
        regular expression.

        Returns boolean indicating whether a match was found.
        '''
        pattern = re.compile(pattern)
        for record in self.buffer:
            if pattern.search(record.getMessage()) is not None:
                return True
        return False

    def any_errors(self):
        '''Search through the buffer for any ERROR or CRITICAL events.

        Returns boolean indicating whether a match was found.
        '''
        return any(record for record in self.buffer
                   if record.levelname in ('ERROR', 'CRITICAL'))

    def inveigle(self):
        '''Turn on logging capture by replacing all existing handlers
        configured in the logging module.

        If the config var logging_clear_handlers is set then we also remove
        all existing handlers.

        We also set the level of the root logger.

        The opposite of this is :meth:`~LoggingCapture.abandon`.
        '''
        root_logger = logging.getLogger()
        if self.config.logging_clear_handlers:
            # kill off all the other log handlers
            for logger in logging.Logger.manager.loggerDict.values():
                if hasattr(logger, "handlers"):
                    for handler in logger.handlers:
                        self.old_handlers.append((logger, handler))
                        logger.removeHandler(handler)

        # sanity check: remove any existing LoggingCapture
        for handler in root_logger.handlers[:]:
            if isinstance(handler, LoggingCapture):
                root_logger.handlers.remove(handler)
            elif self.config.logging_clear_handlers:
                self.old_handlers.append((root_logger, handler))
                root_logger.removeHandler(handler)

        # right, we're it now
        root_logger.addHandler(self)

        # capture the level we're interested in
        self.old_level = root_logger.level
        root_logger.setLevel(self.level)

    def abandon(self):
        '''Turn off logging capture.

        If other handlers were removed by :meth:`~LoggingCapture.inveigle` then
        they are reinstated.
        '''
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if handler is self:
                root_logger.handlers.remove(handler)

        if self.config.logging_clear_handlers:
            for logger, handler in self.old_handlers:
                logger.addHandler(handler)

        if self.old_level is not None:
            # -- RESTORE: Old log.level before inveigle() was used.
            root_logger.setLevel(self.old_level)
            self.old_level = None

# pre-1.2 backwards compatibility
MemoryHandler = LoggingCapture


def capture(*args, **kw):
    '''Decorator to wrap an *environment file function* in log file capture.

    It configures the logging capture using the *behave* context - the first
    argument to the function being decorated (so don't use this to decorate
    something that doesn't have *context* as the first argument.)

    The basic usage is:

    .. code-block: python

        @capture
        def after_scenario(context, scenario):
            ...

    The function prints any captured logging (at the level determined by the
    ``log_level`` configuration setting) directly to stdout, regardless of
    error conditions.

    It is mostly useful for debugging in situations where you are seeing a
    message like::

        No handlers could be found for logger "name"

    The decorator takes an optional "level" keyword argument which limits the
    level of logging captured, overriding the level in the run's configuration:

    .. code-block: python

        @capture(level=logging.ERROR)
        def after_scenario(context, scenario):
            ...

    This would limit the logging captured to just ERROR and above, and thus
    only display logged events if they are interesting.
    '''
    def create_decorator(func, level=None):
        def f(context, *args):
            h = LoggingCapture(context.config, level=level)
            h.inveigle()
            try:
                func(context, *args)
            finally:
                h.abandon()
            v = h.getvalue()
            if v:
                print 'Captured Logging:'
                print v
        return f

    if not args:
        return functools.partial(create_decorator, level=kw.get('level'))
    else:
        return create_decorator(args[0])

########NEW FILE########
__FILENAME__ = matchers
from __future__ import with_statement

import re
import parse
from parse_type import cfparse
from behave import model


class Matcher(object):
    """Pull parameters out of step names.

    .. attribute:: string

       The match pattern attached to the step function.

    .. attribute:: func

       The step function the pattern is being attached to.
    """
    schema = u"@%s('%s')"   # Schema used to describe step definition (matcher)

    def __init__(self, func, string, step_type=None):
        self.func = func
        self.string = string
        self.step_type = step_type
        self._location = None

    @property
    def location(self):
        if self._location is None:
            self._location = model.Match.make_location(self.func)
        return self._location

    def describe(self, schema=None):
        """Provide a textual description of the step function/matcher object.

        :param schema:  Text schema to use.
        :return: Textual description of this step definition (matcher).
        """
        step_type = self.step_type or 'step'
        if not schema:
            schema = self.schema
        return schema % (step_type, self.string)


    def check_match(self, step):
        """Match me against the "step" name supplied.

        Return None if I don't match otherwise return a list of matches as
        :class:`behave.model.Argument` instances.

        The return value from this function will be converted into a
        :class:`behave.model.Match` instance by *behave*.
        """
        raise NotImplementedError

    def match(self, step):
        result = self.check_match(step)
        if result is None:
            return None
        return model.Match(self.func, result)

    def __repr__(self):
        return u"<%s: %r>" % (self.__class__.__name__, self.string)


class ParseMatcher(Matcher):
    custom_types = {}

    def __init__(self, func, string, step_type=None):
        super(ParseMatcher, self).__init__(func, string, step_type)
        self.parser = parse.compile(self.string, self.custom_types)

    def check_match(self, step):
        result = self.parser.parse(step)
        if not result:
            return None

        args = []
        for index, value in enumerate(result.fixed):
            start, end = result.spans[index]
            args.append(model.Argument(start, end, step[start:end], value))
        for name, value in result.named.items():
            start, end = result.spans[name]
            args.append(model.Argument(start, end, step[start:end], value, name))
        args.sort(key=lambda x: x.start)
        return args

class CFParseMatcher(ParseMatcher):
    """
    Uses :class:`parse_type.cfparse.Parser` instead of "parse.Parser".
    Provides support for automatic generation of type variants
    for fields with CardinalityField part.
    """
    def __init__(self, func, string, step_type=None):
        super(ParseMatcher, self).__init__(func, string, step_type)
        self.parser = cfparse.Parser(self.string, self.custom_types)


def register_type(**kw):
    """Registers a custom type that will be available to "parse"
    for type conversion during step matching.

    Converters should be supplied as ``name=callable`` arguments (or as dict).

    A type converter should follow :pypi:`parse` module rules.
    In general, a type converter is a function that converts text (as string)
    into a value-type (type converted value).

    EXAMPLE:

    .. code-block:: python

        from behave import register_type, given
        import parse

        # -- TYPE CONVERTER: For a simple, positive integer number.
        @parse.with_pattern(r"\d+")
        def parse_number(text):
            return int(text)

        # -- REGISTER TYPE-CONVERTER: With behave
        register_type(Number=parse_number)

        # -- STEP DEFINITIONS: Use type converter.
        @given('{amount:Number} vehicles')
        def step_impl(context, amount):
            assert isinstance(amount, int)
    """
    ParseMatcher.custom_types.update(kw)


class RegexMatcher(Matcher):
    def __init__(self, func, string, step_type=None):
        super(RegexMatcher, self).__init__(func, string, step_type)
        self.regex = re.compile(self.string)

    def check_match(self, step):
        m = self.regex.match(step)
        if not m:
            return None

        groupindex = dict((y, x) for x, y in self.regex.groupindex.items())
        args = []
        for index, group in enumerate(m.groups()):
            index += 1
            name = groupindex.get(index, None)
            args.append(model.Argument(m.start(index), m.end(index), group,
                                       group, name))

        return args


matcher_mapping = {
    "parse": ParseMatcher,
    "cfparse": CFParseMatcher,
    "re": RegexMatcher,
}
current_matcher = ParseMatcher


def use_step_matcher(name):
    """Change the parameter matcher used in parsing step text.

    The change is immediate and may be performed between step definitions in
    your step implementation modules - allowing adjacent steps to use different
    matchers if necessary.

    There are several parsers available in *behave* (by default):

    **parse** (the default, based on: :pypi:`parse`)
        Provides a simple parser that replaces regular expressions for
        step parameters with a readable syntax like ``{param:Type}``.
        The syntax is inspired by the Python builtin ``string.format()``
        function.
        Step parameters must use the named fields syntax of :pypi:`parse`
        in step definitions. The named fields are extracted,
        optionally type converted and then used as step function arguments.

        Supports type conversions by using type converters
        (see :func:`~behave.register_type()`).

    **cfparse** (extends: :pypi:`parse`, requires: :pypi:`parse_type`)
        Provides an extended parser with "Cardinality Field" (CF) support.
        Automatically creates missing type converters for related cardinality
        as long as a type converter for cardinality=1 is provided.
        Supports parse expressions like:

            * ``{values:Type+}`` (cardinality=1..N, many)
            * ``{values:Type*}`` (cardinality=0..N, many0)
            * ``{value:Type?}``  (cardinality=0..1, optional)

        Supports type conversions (as above).

    **re**
        This uses full regular expressions to parse the clause text. You will
        need to use named groups "(?P<name>...)" to define the variables pulled
        from the text and passed to your ``step()`` function.

        Type conversion is **not supported**.
        A step function writer may implement type conversion
        inside the step function (implementation).

    You may `define your own matcher`_.

    .. _`define your own matcher`: api.html#step-parameters
    """
    global current_matcher
    current_matcher = matcher_mapping[name]

def step_matcher(name):
    """
    DEPRECATED, use :func:`use_step_matcher()` instead.
    """
    # -- BACKWARD-COMPATIBLE NAME: Mark as deprecated.
    import warnings
    warnings.warn("Use 'use_step_matcher()' instead",
                  PendingDeprecationWarning, stacklevel=2)
    use_step_matcher(name)

def get_matcher(func, string):
    return current_matcher(func, string)



########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-

from __future__ import with_statement
import copy
import difflib
import itertools
import os.path
import sys
import time
import traceback
from behave import step_registry
from behave.compat.os_path import relpath


class Argument(object):
    '''An argument found in a *feature file* step name and extracted using
    step decorator `parameters`_.

    The attributes are:

    .. attribute:: original

       The actual text matched in the step name.

    .. attribute:: value

       The potentially type-converted value of the argument.

    .. attribute:: name

       The name of the argument. This will be None if the parameter is
       anonymous.

    .. attribute:: start

       The start index in the step name of the argument. Used for display.

    .. attribute:: end

       The end index in the step name of the argument. Used for display.
    '''
    def __init__(self, start, end, original, value, name=None):
        self.start = start
        self.end = end
        self.original = original
        self.value = value
        self.name = name


# @total_ordering
# class FileLocation(unicode):
class FileLocation(object):
    """
    Provides a value object for file location objects.
    A file location consists of:

      * filename
      * line (number), optional

    LOCATION SCHEMA:
      * "{filename}:{line}" or
      * "{filename}" (if line number is not present)
    """
    # -- pylint: disable=R0904,R0924
    #   R0904: 30,0:FileLocation: Too many public methods (43/30) => unicode
    #   R0924: 30,0:FileLocation: Badly implemented Container, ...=> unicode
    __pychecker__ = "missingattrs=line"     # -- Ignore warnings for 'line'.

    def __init__(self, filename, line=None):
        self.filename = filename
        self.line = line

    # def __new__(cls, filename, line=None):
    #     assert isinstance(filename, basestring)
    #     obj = unicode.__new__(cls, filename)
    #     obj.line = line
    #     obj.__filename = filename
    #     return obj
    #
    # @property
    # def filename(self):
    #     # -- PREVENT: Assignments via property (and avoid self-recursion).
    #     return self.__filename

    def get(self):
        return self.filename

    def abspath(self):
        return os.path.abspath(self.filename)

    def basename(self):
        return os.path.basename(self.filename)

    def dirname(self):
        return os.path.dirname(self.filename)

    def relpath(self, start=os.curdir):
        """
        Compute relative path for start to filename.

        :param start: Base path or start directory (default=current dir).
        :return: Relative path from start to filename
        """
        return relpath(self.filename, start)

    def exists(self):
        return os.path.exists(self.filename)

    def __eq__(self, other):
        if isinstance(other, FileLocation):
            return self.filename == other.filename and self.line == other.line
        elif isinstance(other, basestring):
            return self.filename == other
        else:
            raise AttributeError("Cannot compare FileLocation with %s:%s" % \
                                 (type(other), other))

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if isinstance(other, FileLocation):
            if self.filename < other.filename:
                return True
            elif self.filename > other.filename:
                return False
            else:
                assert self.filename == other.filename
                return self.line < other.line
        elif isinstance(other, basestring):
            return self.filename < other
        else:
            raise AttributeError("Cannot compare FileLocation with %s:%s" % \
                                 (type(other), other))

    def __le__(self, other):
        # -- SEE ALSO: python2.7, functools.total_ordering
        return not other < self

    def __gt__(self, other):
        # -- SEE ALSO: python2.7, functools.total_ordering
        if isinstance(other, FileLocation):
            return other < self
        else:
            return self.filename > other

    def __ge__(self, other):
        # -- SEE ALSO: python2.7, functools.total_ordering
        return not self < other

    def __repr__(self):
        return u'<FileLocation: filename="%s", line=%s>' % \
               (self.filename, self.line)

    def __str__(self):
        if self.line is None:
            return self.filename
        return u"%s:%d" % (self.filename, self.line)


class BasicStatement(object):
    def __init__(self, filename, line, keyword, name):
        filename = filename or '<string>'
        filename = relpath(filename, os.getcwd())   # -- NEEDS: abspath?
        self.location = FileLocation(filename, line)
        assert isinstance(keyword, unicode)
        assert isinstance(name, unicode)
        self.keyword = keyword
        self.name = name

    @property
    def filename(self):
        # return os.path.abspath(self.location.filename)
        return self.location.filename

    @property
    def line(self):
        return self.location.line

    # @property
    # def location(self):
    #     p = relpath(self.filename, os.getcwd())
    #     return '%s:%d' % (p, self.line)

    def __lt__(self, other):
        # -- PYTHON3 SUPPORT, ORDERABLE:
        # NOTE: Ignore potential FileLocation differences.
        return (self.keyword, self.name) < (other.keyword, other.name)

    def __cmp__(self, other):
        # -- NOTE: Ignore potential FileLocation differences.
        return cmp((self.keyword, self.name), (other.keyword, other.name))


class TagStatement(BasicStatement):

    def __init__(self, filename, line, keyword, name, tags):
        super(TagStatement, self).__init__(filename, line, keyword, name)
        self.tags = tags


class TagAndStatusStatement(BasicStatement):
    final_status = ('passed', 'failed', 'skipped')

    def __init__(self, filename, line, keyword, name, tags):
        super(TagAndStatusStatement, self).__init__(filename, line, keyword, name)
        self.tags = tags
        self.should_skip = False
        self._cached_status = None

    @property
    def status(self):
        if self._cached_status not in self.final_status:
            # -- RECOMPUTE: As long as final status is not reached.
            self._cached_status = self.compute_status()
        return self._cached_status

    def reset(self):
        self.should_skip = False
        self._cached_status = None

    def compute_status(self):
        raise NotImplementedError


class Replayable(object):
    type = None

    def replay(self, formatter):
        getattr(formatter, self.type)(self)


class Feature(TagAndStatusStatement, Replayable):
    '''A `feature`_ parsed from a *feature file*.

    The attributes are:

    .. attribute:: keyword

       This is the keyword as seen in the *feature file*. In English this will
       be "Feature".

    .. attribute:: name

       The name of the feature (the text after "Feature".)

    .. attribute:: description

       The description of the feature as seen in the *feature file*. This is
       stored as a list of text lines.

    .. attribute:: background

       The :class:`~behave.model.Background` for this feature, if any.

    .. attribute:: scenarios

       A list of :class:`~behave.model.Scenario` making up this feature.

    .. attribute:: tags

       A list of @tags (as :class:`~behave.model.Tag` which are basically
       glorified strings) attached to the feature.
       See :ref:`controlling things with tags`.

    .. attribute:: status

       Read-Only. A summary status of the feature's run. If read before the
       feature is fully tested it will return "untested" otherwise it will
       return one of:

       "untested"
         The feature was has not been completely tested yet.
       "skipped"
         One or more steps of this feature was passed over during testing.
       "passed"
         The feature was tested successfully.
       "failed"
         One or more steps of this feature failed.

    .. attribute:: duration

       The time, in seconds, that it took to test this feature. If read before
       the feature is tested it will return 0.0.

    .. attribute:: filename

       The file name (or "<string>") of the *feature file* where the feature
       was found.

    .. attribute:: line

       The line number of the *feature file* where the feature was found.

    .. _`feature`: gherkin.html#features
    '''

    type = "feature"

    def __init__(self, filename, line, keyword, name, tags=None,
                 description=None, scenarios=None, background=None):
        tags = tags or []
        super(Feature, self).__init__(filename, line, keyword, name, tags)
        self.description = description or []
        self.scenarios = []
        self.background = background
        self.parser = None
        if scenarios:
            for scenario in scenarios:
                self.add_scenario(scenario)

    def reset(self):
        '''
        Reset to clean state before a test run.
        '''
        super(Feature, self).reset()
        for scenario in self.scenarios:
            scenario.reset()

    def __repr__(self):
        return '<Feature "%s": %d scenario(s)>' % \
            (self.name, len(self.scenarios))

    def __iter__(self):
        return iter(self.scenarios)

    def add_scenario(self, scenario):
        scenario.feature = self
        scenario.background = self.background
        self.scenarios.append(scenario)

    def compute_status(self):
        """
        Compute the status of this feature based on its:
           * scenarios
           * scenario outlines

        :return: Computed status (as string-enum).
        """
        skipped = True
        passed_count = 0
        for scenario in self.scenarios:
            scenario_status = scenario.status
            if scenario_status == 'failed':
                return 'failed'
            elif scenario_status == 'untested':
                if passed_count > 0:
                    return 'failed'  # ABORTED: Some passed, now untested.
                return 'untested'
            if scenario_status != 'skipped':
                skipped = False
            if scenario_status == 'passed':
                passed_count += 1
        return skipped and 'skipped' or 'passed'

    @property
    def duration(self):
        # -- NEW: Background is executed N times, now part of scenarios.
        feature_duration = 0.0
        for scenario in self.scenarios:
            feature_duration += scenario.duration
        return feature_duration

    def walk_scenarios(self, with_outlines=False):
        """
        Provides a flat list of all scenarios of this feature.
        A ScenarioOutline element adds its scenarios to this list.
        But the ScenarioOutline element itself is only added when specified.

        A flat scenario list is useful when all scenarios of a features
        should be processed.

        :param with_outlines: If ScenarioOutline items should be added, too.
        :return: List of all scenarios of this feature.
        """
        all_scenarios = []
        for scenario in self.scenarios:
            if isinstance(scenario, ScenarioOutline):
                scenario_outline = scenario
                if with_outlines:
                    all_scenarios.append(scenario_outline)
                all_scenarios.extend(scenario_outline.scenarios)
            else:
                all_scenarios.append(scenario)
        return all_scenarios

    def should_run(self, config=None):
        """
        Determines if this Feature (and its scenarios) should run.
        Implements the run decision logic for a feature.
        The decision depends on:

          * if the Feature is marked as skipped
          * if the config.tags (tag expression) enable/disable this feature

        :param config:  Runner configuration to use (optional).
        :return: True, if scenario should run. False, otherwise.
        """
        answer = not self.should_skip
        if answer and config:
            answer = self.should_run_with_tags(config.tags)
        return answer

    def should_run_with_tags(self, tag_expression):
        '''
        Determines if this feature should run when the tag expression is used.
        A feature should run if:
          * it should run according to its tags
          * any of its scenarios should run according to its tags

        :param tag_expression:  Runner/config environment tags to use.
        :return: True, if feature should run. False, otherwise (skip it).
        '''
        run_feature = tag_expression.check(self.tags)
        if not run_feature:
            for scenario in self:
                if scenario.should_run_with_tags(tag_expression):
                    run_feature = True
                    break
        return run_feature

    def mark_skipped(self):
        """
        Marks this feature (and all its scenarios and steps) as skipped.
        """
        self._cached_status = None
        self.should_skip = True
        for scenario in self.scenarios:
            scenario.mark_skipped()
        else:
            # -- SPECIAL CASE: Feature without scenarios
            self._cached_status = "skipped"
        assert self.status == "skipped"

    def run(self, runner):
        self._cached_status = None
        runner.context._push()
        runner.context.feature = self

        # run this feature if the tags say so or any one of its scenarios
        run_feature = self.should_run(runner.config)
        if run_feature or runner.config.show_skipped:
            for formatter in runner.formatters:
                formatter.feature(self)

        # current tags as a set
        runner.context.tags = set(self.tags)

        if not runner.config.dry_run and run_feature:
            for tag in self.tags:
                runner.run_hook('before_tag', runner.context, tag)
            runner.run_hook('before_feature', runner.context, self)

        if self.background and (run_feature or runner.config.show_skipped):
            for formatter in runner.formatters:
                formatter.background(self.background)

        failed_count = 0
        for scenario in self.scenarios:
            # -- OPTIONAL: Select scenario by name (regular expressions).
            # XXX if (runner.config.name and
            # XXX         not runner.config.name_re.search(scenario.name)):
            if (runner.config.name and
                     not scenario.should_run_with_name_select(runner.config)):
                scenario.mark_skipped()
                continue

            failed = scenario.run(runner)
            if failed:
                failed_count += 1
                if runner.config.stop or runner.aborted:
                    # -- FAIL-EARLY: Stop after first failure.
                    break
        else:
            if not run_feature:
                # -- SPECIAL CASE: Feature without scenarios:
                self._cached_status = 'skipped'

        if run_feature:
            runner.run_hook('after_feature', runner.context, self)
            for tag in self.tags:
                runner.run_hook('after_tag', runner.context, tag)

        runner.context._pop()

        if run_feature or runner.config.show_skipped:
            for formatter in runner.formatters:
                formatter.eof()

        failed = (failed_count > 0)
        return failed


class Background(BasicStatement, Replayable):
    '''A `background`_ parsed from a *feature file*.

    The attributes are:

    .. attribute:: keyword

       This is the keyword as seen in the *feature file*. In English this will
       typically be "Background".

    .. attribute:: name

       The name of the background (the text after "Background:".)

    .. attribute:: steps

       A list of :class:`~behave.model.Step` making up this background.

    .. attribute:: duration

       The time, in seconds, that it took to run this background. If read
       before the background is run it will return 0.0.

    .. attribute:: filename

       The file name (or "<string>") of the *feature file* where the scenario
       was found.

    .. attribute:: line

       The line number of the *feature file* where the scenario was found.

    .. _`background`: gherkin.html#backgrounds
    '''
    type = "background"

    def __init__(self, filename, line, keyword, name, steps=None):
        super(Background, self).__init__(filename, line, keyword, name)
        self.steps = steps or []

    def __repr__(self):
        return '<Background "%s">' % self.name

    def __iter__(self):
        return iter(self.steps)

    @property
    def duration(self):
        duration = 0
        for step in self.steps:
            duration += step.duration
        return duration


class Scenario(TagAndStatusStatement, Replayable):
    '''A `scenario`_ parsed from a *feature file*.

    The attributes are:

    .. attribute:: keyword

       This is the keyword as seen in the *feature file*. In English this will
       typically be "Scenario".

    .. attribute:: name

       The name of the scenario (the text after "Scenario:".)

    .. attribute:: description

       The description of the scenario as seen in the *feature file*.
       This is stored as a list of text lines.

    .. attribute:: feature

       The :class:`~behave.model.Feature` this scenario belongs to.

    .. attribute:: steps

       A list of :class:`~behave.model.Step` making up this scenario.

    .. attribute:: tags

       A list of @tags (as :class:`~behave.model.Tag` which are basically
       glorified strings) attached to the scenario.
       See :ref:`controlling things with tags`.

    .. attribute:: status

       Read-Only. A summary status of the scenario's run. If read before the
       scenario is fully tested it will return "untested" otherwise it will
       return one of:

       "untested"
         The scenario was has not been completely tested yet.
       "skipped"
         One or more steps of this scenario was passed over during testing.
       "passed"
         The scenario was tested successfully.
       "failed"
         One or more steps of this scenario failed.

    .. attribute:: duration

       The time, in seconds, that it took to test this scenario. If read before
       the scenario is tested it will return 0.0.

    .. attribute:: filename

       The file name (or "<string>") of the *feature file* where the scenario
       was found.

    .. attribute:: line

       The line number of the *feature file* where the scenario was found.

    .. _`scenario`: gherkin.html#scenarios
    '''
    type = "scenario"

    def __init__(self, filename, line, keyword, name, tags=None, steps=None,
                 description=None):
        tags = tags or []
        super(Scenario, self).__init__(filename, line, keyword, name, tags)
        self.description = description or []
        self.steps = steps or []
        self.background = None
        self.feature = None  # REFER-TO: owner=Feature
        self._background_steps = None
        self._row = None
        self.was_dry_run = False
        self.stderr = None
        self.stdout = None

    def reset(self):
        '''
        Reset the internal data to reintroduce new-born state just after the
        ctor was called.
        '''
        super(Scenario, self).reset()
        self._row = None
        self.was_dry_run = False
        self.stderr = None
        self.stdout = None
        for step in self.all_steps:
            step.reset()

    @property
    def background_steps(self):
        '''
        Provide background steps if feature has a background.
        Lazy init that copies the background steps.

        Note that a copy of the background steps is needed to ensure
        that the background step status is specific to the scenario.

        :return:  List of background steps or empty list
        '''
        if self._background_steps is None:
            # -- LAZY-INIT (need copy of background.steps):
            # Each scenario needs own background.steps status.
            # Otherwise, background step status of the last scenario is used.
            steps = []
            if self.background:
                steps = [copy.copy(step) for step in self.background.steps]
            self._background_steps = steps
        return self._background_steps

    @property
    def all_steps(self):
        """Returns iterator to all steps, including background steps if any."""
        if self.background is not None:
            return itertools.chain(self.background_steps, self.steps)
        else:
            return iter(self.steps)

    def __repr__(self):
        return '<Scenario "%s">' % self.name

    def __iter__(self):
        # XXX return iter(self.all_steps)
        return self.all_steps

    def compute_status(self):
        """Compute the status of the scenario from its steps.
        :return: Computed status (as string).
        """
        for step in self.all_steps:
            if step.status == 'undefined':
                if self.was_dry_run:
                    # -- SPECIAL CASE: In dry-run with undefined-step discovery
                    #    Undefined steps should not cause failed scenario.
                    return 'untested'
                else:
                    # -- NORMALLY: Undefined steps cause failed scenario.
                    return 'failed'
            elif step.status != 'passed':
                assert step.status in ('failed', 'skipped', 'untested')
                return step.status
            #elif step.status == 'failed':
            #    return 'failed'
            #elif step.status == 'skipped':
            #    return 'skipped'
            #elif step.status == 'untested':
            #    return 'untested'
        return 'passed'

    @property
    def duration(self):
        # -- ORIG: for step in self.steps:  Background steps were excluded.
        scenario_duration = 0
        for step in self.all_steps:
            scenario_duration += step.duration
        return scenario_duration

    @property
    def effective_tags(self):
        """
        Effective tags for this scenario:
          * own tags
          * tags inherited from its feature
        """
        tags = self.tags
        if self.feature:
            tags = self.feature.tags + self.tags
        return tags

    def should_run(self, config=None):
        """
        Determines if this Scenario (or ScenarioOutline) should run.
        Implements the run decision logic for a scenario.
        The decision depends on:

          * if the Scenario is marked as skipped
          * if the config.tags (tag expression) enable/disable this scenario
          * if the scenario is selected by name

        :param config:  Runner configuration to use (optional).
        :return: True, if scenario should run. False, otherwise.
        """
        answer = not self.should_skip
        if answer and config:
            answer = (self.should_run_with_tags(config.tags) and
                      self.should_run_with_name_select(config))
        return answer

    def should_run_with_tags(self, tag_expression):
        """
        Determines if this scenario should run when the tag expression is used.

        :param tag_expression:  Runner/config environment tags to use.
        :return: True, if scenario should run. False, otherwise (skip it).
        """
        return tag_expression.check(self.effective_tags)

    def should_run_with_name_select(self, config):
        """Determines if this scenario should run when it is selected by name.

        :param config:  Runner/config environment name regexp (if any).
        :return: True, if scenario should run. False, otherwise (skip it).
        """
        # -- SELECT-ANY: If select by name is not specified (not config.name).
        return not config.name or config.name_re.search(self.name)

    def mark_skipped(self):
        """
        Marks this scenario (and all its steps) as skipped.
        """
        self._cached_status = None
        self.should_skip = True
        for step in self.all_steps:
            assert step.status == "untested" or step.status == "skipped"
            step.status = "skipped"
        else:
            # -- SPECIAL CASE: Scenario without steps
            self._cached_status = "skipped"
        assert self.status == "skipped", "OOPS: scenario.status=%s" % self.status

    def run(self, runner):
        self._cached_status = None
        failed = False
        run_scenario = self.should_run(runner.config)
        run_steps = run_scenario and not runner.config.dry_run
        dry_run_scenario = run_scenario and runner.config.dry_run
        self.was_dry_run = dry_run_scenario

        if run_scenario or runner.config.show_skipped:
            for formatter in runner.formatters:
                formatter.scenario(self)

        runner.context._push()
        runner.context.scenario = self
        runner.context.tags = set(self.effective_tags)

        if not runner.config.dry_run and run_scenario:
            for tag in self.tags:
                runner.run_hook('before_tag', runner.context, tag)
            runner.run_hook('before_scenario', runner.context, self)

        runner.setup_capture()

        if run_scenario or runner.config.show_skipped:
            for step in self:
                for formatter in runner.formatters:
                    formatter.step(step)

        for step in self.all_steps:
            if run_steps:
                if not step.run(runner):
                    run_steps = False
                    failed = True
                    runner.context._set_root_attribute('failed', True)
                    self._cached_status = 'failed'
            elif failed or dry_run_scenario:
                # -- SKIP STEPS: After failure/undefined-step occurred.
                # BUT: Detect all remaining undefined steps.
                step.status = 'skipped'
                if dry_run_scenario:
                    step.status = 'untested'
                found_step = step_registry.registry.find_match(step)
                if not found_step:
                    step.status = 'undefined'
                    runner.undefined_steps.append(step)
            else:
                # -- SKIP STEPS: For disabled scenario.
                # NOTE: Undefined steps are not detected (by intention).
                step.status = 'skipped'
        else:
            if not run_scenario:
                # -- SPECIAL CASE: Scenario without steps.
                self._cached_status = 'skipped'

        # Attach the stdout and stderr if generate Junit report
        if runner.config.junit:
            self.stdout = runner.context.stdout_capture.getvalue()
            self.stderr = runner.context.stderr_capture.getvalue()
        runner.teardown_capture()

        if not runner.config.dry_run and run_scenario:
            runner.run_hook('after_scenario', runner.context, self)
            for tag in self.tags:
                runner.run_hook('after_tag', runner.context, tag)

        runner.context._pop()
        return failed


class ScenarioOutline(Scenario):
    """A `scenario outline`_ parsed from a *feature file*.

    A scenario outline extends the existing :class:`~behave.model.Scenario`
    class with the addition of the :class:`~behave.model.Examples` tables of
    data from the *feature file*.

    The attributes are:

    .. attribute:: keyword

       This is the keyword as seen in the *feature file*. In English this will
       typically be "Scenario Outline".

    .. attribute:: name

       The name of the scenario (the text after "Scenario Outline:".)

    .. attribute:: description

       The description of the `scenario outline`_ as seen in the *feature file*.
       This is stored as a list of text lines.

    .. attribute:: feature

       The :class:`~behave.model.Feature` this scenario outline belongs to.

    .. attribute:: steps

       A list of :class:`~behave.model.Step` making up this scenario outline.

    .. attribute:: examples

       A list of :class:`~behave.model.Examples` used by this scenario outline.

    .. attribute:: tags

       A list of @tags (as :class:`~behave.model.Tag` which are basically
       glorified strings) attached to the scenario.
       See :ref:`controlling things with tags`.

    .. attribute:: status

       Read-Only. A summary status of the scenario outlines's run. If read
       before the scenario is fully tested it will return "untested" otherwise
       it will return one of:

       "untested"
         The scenario was has not been completely tested yet.
       "skipped"
         One or more scenarios of this outline was passed over during testing.
       "passed"
         The scenario was tested successfully.
       "failed"
         One or more scenarios of this outline failed.

    .. attribute:: duration

       The time, in seconds, that it took to test the scenarios of this
       outline. If read before the scenarios are tested it will return 0.0.

    .. attribute:: filename

       The file name (or "<string>") of the *feature file* where the scenario
       was found.

    .. attribute:: line

       The line number of the *feature file* where the scenario was found.

    .. _`scenario outline`: gherkin.html#scenario-outlines
    """
    type = "scenario_outline"
    annotation_schema = u"{name} -- @{row.id} {examples.name}"

    def __init__(self, filename, line, keyword, name, tags=None,
                 steps=None, examples=None, description=None):
        super(ScenarioOutline, self).__init__(filename, line, keyword, name,
                                              tags, steps, description)
        self.examples = examples or []
        self._scenarios = []

    def reset(self):
        """Reset runtime temporary data like before a test run."""
        super(ScenarioOutline, self).reset()
        for scenario in self.scenarios:
            scenario.reset()

    @staticmethod
    def render_template(text, row=None, params=None):
        """Render a text template with placeholders, ala "Hello <name>".

        :param row:     As placeholder provider (dict-like).
        :param params:  As additional placeholder provider (as dict).
        :return: Rendered text, known placeholders are substituted w/ values.
        """
        if not ('<' in text and '>' in text):
            return text

        safe_values = False
        for placeholders in (row, params):
            if not placeholders:
                continue
            for name, value in placeholders.items():
                if safe_values and ('<' in value and '>' in value):
                    continue    # -- OOPS, value looks like placeholder.
                text = text.replace("<%s>" % name, value)
        return text

    def make_scenario_name(self, example, row, params=None):
        """Build a scenario name for an example row of this scenario outline.
        Placeholders for row data are replaced by values.

        SCHEMA: "{scenario_outline.name} -*- {examples.name}@{row.id}"

        :param example:  Examples object.
        :param row:      Row of this example.
        :param params:   Additional placeholders for example/row.
        :return: Computed name for the scenario representing example/row.
        """
        if params is None:
            params = {}
        params["examples.name"] = example.name or ""
        params.setdefault("examples.index", example.index)
        params.setdefault("row.index", row.index)
        params.setdefault("row.id", row.id)

        # -- STEP: Replace placeholders in scenario/example name (if any).
        examples_name = self.render_template(example.name, row, params)
        params["examples.name"] = examples_name
        scenario_name = self.render_template(self.name, row, params)

        class Data(object):
            def __init__(self, name, index):
                self.name = name
                self.index = index
                self.id = name

        example_data = Data(examples_name, example.index)
        row_data = Data(row.id, row.index)
        return self.annotation_schema.format(name=scenario_name,
                                        examples=example_data, row=row_data)

    def make_row_tags(self, row, params=None):
        if not self.tags:
            return None

        tags = []
        for tag in self.tags:
            if '<' in tag and '>' in tag:
                tag = self.render_template(tag, row, params)
            if '<' in tag or '>' in tag:
                # -- OOPS: Unknown placeholder, drop tag.
                continue
            new_tag = Tag.make_name(tag, unescape=True)
            tags.append(new_tag)
        return tags

    @classmethod
    def make_step_for_row(cls, outline_step, row, params=None):
        # -- BASED-ON: new_step = outline_step.set_values(row)
        new_step = copy.deepcopy(outline_step)
        new_step.name = cls.render_template(new_step.name, row, params)
        if new_step.text:
            new_step.text = cls.render_template(new_step.text, row)
        if new_step.table:
            for name, value in row.items():
                for row in new_step.table:
                    for i, cell in enumerate(row.cells):
                        row.cells[i] = cell.replace("<%s>" % name, value)
        return new_step

    @property
    def scenarios(self):
        """Return the scenarios with the steps altered to take the values from
        the examples.
        """
        if self._scenarios:
            return self._scenarios

        # -- BUILD SCENARIOS (once): For this ScenarioOutline from examples.
        params = {
            "examples.name": None,
            "examples.index": None,
            "row.index": None,
            "row.id": None,
        }
        for example_index, example in enumerate(self.examples):
            example.index = example_index+1
            params["examples.name"]  = example.name
            params["examples.index"] = str(example.index)
            for row_index, row in enumerate(example.table):
                row.index = row_index+1
                row.id = "%d.%d" % (example.index, row.index)
                params["row.id"] = row.id
                params["row.index"] = str(row.index)
                scenario_name = self.make_scenario_name(example, row, params)
                row_tags = self.make_row_tags(row, params)
                new_steps = []
                for outline_step in self.steps:
                    new_step = self.make_step_for_row(outline_step, row, params)
                    new_steps.append(new_step)

                # -- STEP: Make Scenario name for this row.
                # scenario_line = example.line + 2 + row_index
                scenario_line = row.line
                scenario = Scenario(self.filename, scenario_line, self.keyword,
                                    scenario_name, row_tags, new_steps)
                scenario.feature = self.feature
                scenario.background = self.background
                scenario._row = row
                self._scenarios.append(scenario)
        return self._scenarios

    def __repr__(self):
        return '<ScenarioOutline "%s">' % self.name

    def __iter__(self):
        return iter(self.scenarios)

    def compute_status(self):
        for scenario in self.scenarios:
            scenario_status = scenario.status
            if scenario_status != 'passed':
                assert scenario_status in ('failed', 'skipped', 'untested')
                return scenario_status
            #if scenario.status == 'failed':
            #    return 'failed'
            #elif scenario.status == 'skipped':
            #    return 'skipped'
            #elif scenario.status == 'untested':
            #    return 'untested'
        return 'passed'

    @property
    def duration(self):
        outline_duration = 0
        for scenario in self.scenarios:
            outline_duration += scenario.duration
        return outline_duration

    def should_run_with_tags(self, tag_expression):
        """
        Determines if this scenario outline (or one of its scenarios)
        should run when the tag expression is used.

        :param tag_expression:  Runner/config environment tags to use.
        :return: True, if scenario should run. False, otherwise (skip it).
        """
        if tag_expression.check(self.effective_tags):
            return True

        for scenario in self.scenarios:
            if scenario.should_run_with_tags(tag_expression):
                return True
        # -- NOTHING SELECTED:
        return False

    def should_run_with_name_select(self, config):
        """Determines if this scenario should run when it is selected by name.

        :param config:  Runner/config environment name regexp (if any).
        :return: True, if scenario should run. False, otherwise (skip it).
        """
        if not config.name:
            return True # -- SELECT-ALL: Select by name is not specified.

        for scenario in self.scenarios:
            if scenario.should_run_with_name_select(config):
                return True
        # -- NOTHING SELECTED:
        return False

    def mark_skipped(self):
        """
        Marks this scenario outline (and all its scenarios/steps) as skipped.
        """
        self._cached_status = None
        self.should_skip = True
        for scenario in self.scenarios:
            scenario.mark_skipped()
        else:
            # -- SPECIAL CASE: ScenarioOutline without scenarios/examples
            self._cached_status = "skipped"
        assert self.status == "skipped"

    def run(self, runner):
        self._cached_status = None
        failed_count = 0
        for scenario in self.scenarios:
            runner.context._set_root_attribute('active_outline', scenario._row)
            failed = scenario.run(runner)
            if failed:
                failed_count += 1
                if runner.config.stop or runner.aborted:
                    # -- FAIL-EARLY: Stop after first failure.
                    break
        runner.context._set_root_attribute('active_outline', None)
        return failed_count > 0


class Examples(BasicStatement, Replayable):
    '''A table parsed from a `scenario outline`_ in a *feature file*.

    The attributes are:

    .. attribute:: keyword

       This is the keyword as seen in the *feature file*. In English this will
       typically be "Example".

    .. attribute:: name

       The name of the example (the text after "Example:".)

    .. attribute:: table

       An instance  of :class:`~behave.model.Table` that came with the example
       in the *feature file*.

    .. attribute:: filename

       The file name (or "<string>") of the *feature file* where the scenario
       was found.

    .. attribute:: line

       The line number of the *feature file* where the scenario was found.

    .. _`examples`: gherkin.html#examples
    '''
    type = "examples"

    def __init__(self, filename, line, keyword, name, table=None):
        super(Examples, self).__init__(filename, line, keyword, name)
        self.table = table
        self.index = None


class Step(BasicStatement, Replayable):
    '''A single `step`_ parsed from a *feature file*.

    The attributes are:

    .. attribute:: keyword

       This is the keyword as seen in the *feature file*. In English this will
       typically be "Given", "When", "Then" or a number of other words.

    .. attribute:: name

       The name of the step (the text after "Given" etc.)

    .. attribute:: step_type

       The type of step as determined by the keyword. If the keyword is "and"
       then the previous keyword in the *feature file* will determine this
       step's step_type.

    .. attribute:: text

       An instance of :class:`~behave.model.Text` that came with the step
       in the *feature file*.

    .. attribute:: table

       An instance of :class:`~behave.model.Table` that came with the step
       in the *feature file*.

    .. attribute:: status

       Read-Only. A summary status of the step's run. If read before the
       step is tested it will return "untested" otherwise it will
       return one of:

       "skipped"
         This step was passed over during testing.
       "passed"
         The step was tested successfully.
       "failed"
         The step failed.

    .. attribute:: duration

       The time, in seconds, that it took to test this step. If read before the
       step is tested it will return 0.0.

    .. attribute:: error_message

       If the step failed then this will hold any error information, as a
       single string. It will otherwise be None.

    .. attribute:: filename

       The file name (or "<string>") of the *feature file* where the step was
       found.

    .. attribute:: line

       The line number of the *feature file* where the step was found.

    .. _`step`: gherkin.html#steps
    '''
    type = "step"

    def __init__(self, filename, line, keyword, step_type, name, text=None,
                 table=None):
        super(Step, self).__init__(filename, line, keyword, name)
        self.step_type = step_type
        self.text = text
        self.table = table

        self.status = 'untested'
        self.duration = 0
        self.exception = None
        self.exc_traceback = None
        self.error_message = None

    def reset(self):
        '''Reset temporary runtime data to reach clean state again.'''
        self.status = 'untested'
        self.duration = 0
        self.exception = None
        self.exc_traceback = None
        self.error_message = None

    def store_exception_context(self, exception):
        self.exception = exception
        self.exc_traceback = sys.exc_info()[2]

    def __repr__(self):
        return '<%s "%s">' % (self.step_type, self.name)

    def __eq__(self, other):
        return (self.step_type, self.name) == (other.step_type, other.name)

    def __hash__(self):
        return hash(self.step_type) + hash(self.name)

    def set_values(self, table_row):
        """Clone a new step from this one, used for ScenarioOutline.
        Replace ScenarioOutline placeholders w/ values.

        :param table_row:  Placeholder data for example row.
        :return: Cloned, adapted step object.

        .. note:: Deprecating
            Use 'ScenarioOutline.make_step_for_row()' instead.
        """
        # new_step = copy.deepcopy(self)
        # for name, value in table_row.items():
        #     new_step.name = new_step.name.replace("<%s>" % name, value)
        #     if new_step.text:
        #         new_step.text = new_step.text.replace("<%s>" % name, value)
        #     if new_step.table:
        #         for row in new_step.table:
        #             for i, cell in enumerate(row.cells):
        #                 row.cells[i] = cell.replace("<%s>" % name, value)
        # return new_step
        import warnings
        warnings.warn("Use 'ScenarioOutline.make_step_for_row()' instead",
                      PendingDeprecationWarning, stacklevel=2)
        outline_step = self
        return ScenarioOutline.make_step_for_row(outline_step, table_row)

    def run(self, runner, quiet=False, capture=True):
        # -- RESET: Run information.
        self.exception = self.exc_traceback = self.error_message = None

        # access module var here to allow test mocking to work
        match = step_registry.registry.find_match(self)
        if match is None:
            runner.undefined_steps.append(self)
            if not quiet:
                for formatter in runner.formatters:
                    formatter.match(NoMatch())

            self.status = 'undefined'
            if not quiet:
                for formatter in runner.formatters:
                    formatter.result(self)

            return False

        keep_going = True

        if not quiet:
            for formatter in runner.formatters:
                formatter.match(match)

        runner.run_hook('before_step', runner.context, self)
        if capture:
            runner.start_capture()

        try:
            start = time.time()
            # -- ENSURE:
            #  * runner.context.text/.table attributes are reset (#66).
            #  * Even EMPTY multiline text is available in context.
            runner.context.text = self.text
            runner.context.table = self.table
            match.run(runner.context)
            self.status = 'passed'
        except KeyboardInterrupt, e:
            runner.aborted = True
            error = u"ABORTED: By user (KeyboardInterrupt)."
            self.status = 'failed'
            self.store_exception_context(e)
        except AssertionError, e:
            self.status = 'failed'
            self.store_exception_context(e)
            if e.args:
                error = u'Assertion Failed: %s' % e
            else:
                # no assertion text; format the exception
                error = traceback.format_exc()
        except Exception, e:
            self.status = 'failed'
            error = traceback.format_exc()
            self.store_exception_context(e)

        self.duration = time.time() - start
        if capture:
            runner.stop_capture()

        # flesh out the failure with details
        if self.status == 'failed':
            if capture:
                # -- CAPTURE-ONLY: Non-nested step failures.
                if runner.config.stdout_capture:
                    output = runner.stdout_capture.getvalue()
                    if output:
                        error += '\nCaptured stdout:\n' + output
                if runner.config.stderr_capture:
                    output = runner.stderr_capture.getvalue()
                    if output:
                        error += '\nCaptured stderr:\n' + output
                if runner.config.log_capture:
                    output = runner.log_capture.getvalue()
                    if output:
                        error += '\nCaptured logging:\n' + output
            self.error_message = error
            keep_going = False

        if not quiet:
            for formatter in runner.formatters:
                formatter.result(self)

        runner.run_hook('after_step', runner.context, self)
        return keep_going


class Table(Replayable):
    '''A `table`_ extracted from a *feature file*.

    Table instance data is accessible using a number of methods:

    **iteration**
      Iterating over the Table will yield the :class:`~behave.model.Row`
      instances from the .rows attribute.

    **indexed access**
      Individual rows may be accessed directly by index on the Table instance;
      table[0] gives the first non-heading row and table[-1] gives the last
      row.

    The attributes are:

    .. attribute:: headings

       The headings of the table as a list of strings.

    .. attribute:: rows

       An list of instances of :class:`~behave.model.Row` that make up the body
       of the table in the *feature file*.

    Tables are also comparable, for what that's worth. Headings and row data
    are compared.

    .. _`table`: gherkin.html#table
    '''
    type = "table"

    def __init__(self, headings, line=None, rows=None):
        Replayable.__init__(self)
        self.headings = headings
        self.line = line
        self.rows = []
        if rows:
            for row in rows:
                self.add_row(row, line)

    def add_row(self, row, line=None):
        self.rows.append(Row(self.headings, row, line))

    def add_column(self, column_name, values=None, default_value=u""):
        """
        Adds a new column to this table.
        Uses :param:`default_value` for new cells (if :param:`values` are
        not provided). param:`values` are extended with :param:`default_value`
        if values list is smaller than the number of table rows.

        :param column_name: Name of new column (as string).
        :param values: Optional list of cell values in new column.
        :param default_value: Default value for cell (if values not provided).
        :returns: Index of new column (as number).
        """
        # assert isinstance(column_name, unicode)
        assert not self.has_column(column_name)
        if values is None:
            values = [default_value] * len(self.rows)
        elif not isinstance(values, list):
            values = list(values)
        if len(values) < len(self.rows):
            more_size = len(self.rows) - len(values)
            more_values = [default_value] * more_size
            values.extend(more_values)

        new_column_index = len(self.headings)
        self.headings.append(column_name)
        for row, value in zip(self.rows, values):
            assert len(row.cells) == new_column_index
            row.cells.append(value)
        return new_column_index

    def remove_column(self, column_name):
        if not isinstance(column_name, int):
            try:
                column_index = self.get_column_index(column_name)
            except ValueError:
                raise KeyError("column=%s is unknown" % column_name)

        assert isinstance(column_index, int)
        assert column_index < len(self.headings)
        del self.headings[column_index]
        for row in self.rows:
            assert column_index < len(row.cells)
            del row.cells[column_index]

    def remove_columns(self, column_names):
        for column_name in column_names:
            self.remove_column(column_name)

    def has_column(self, column_name):
        return column_name in self.headings

    def get_column_index(self, column_name):
        return self.headings.index(column_name)

    def require_column(self, column_name):
        """
        Require that a column exists in the table.
        Raise an AssertionError if the column does not exist.

        :param column_name: Name of new column (as string).
        :return: Index of column (as number) if it exists.
        """
        if not self.has_column(column_name):
            columns = ", ".join(self.headings)
            msg = "REQUIRE COLUMN: %s (columns: %s)" % (column_name, columns)
            raise AssertionError(msg)
        return self.get_column_index(column_name)

    def require_columns(self, column_names):
        for column_name in column_names:
            self.require_column(column_name)

    def ensure_column_exists(self, column_name):
        """
        Ensures that a column with the given name exists.
        If the column does not exist, the column is added.

        :param column_name: Name of column (as string).
        :return: Index of column (as number).
        """
        if self.has_column(column_name):
            return self.get_column_index(column_name)
        else:
            return self.add_column(column_name)

    def __repr__(self):
        return "<Table: %dx%d>" % (len(self.headings), len(self.rows))

    def __eq__(self, other):
        if isinstance(other, Table):
            if self.headings != other.headings:
                return False
            for my_row, their_row in zip(self.rows, other.rows):
                if my_row != their_row:
                    return False
        else:
            # -- ASSUME: table <=> raw data comparison
            other_rows = other
            for my_row, their_row in zip(self.rows, other_rows):
                if my_row != their_row:
                    return False
        return True

    def __ne__(self, other):
        return not self == other

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, index):
        return self.rows[index]

    def assert_equals(self, data):
        '''Assert that this table's cells are the same as the supplied "data".

        The data passed in must be a list of lists giving:

            [
                [row 1],
                [row 2],
                [row 3],
            ]

        If the cells do not match then a useful AssertionError will be raised.
        '''
        assert self == data
        raise NotImplementedError


class Row(object):
    '''One row of a `table`_ parsed from a *feature file*.

    Row data is accessible using a number of methods:

    **iteration**
      Iterating over the Row will yield the individual cells as strings.

    **named access**
      Individual cells may be accessed by heading name; row['name'] would give
      the cell value for the column with heading "name".

    **indexed access**
      Individual cells may be accessed directly by index on the Row instance;
      row[0] gives the first cell and row[-1] gives the last cell.

    The attributes are:

    .. attribute:: cells

       The list of strings that form the cells of this row.

    .. attribute:: headings

       The headings of the table as a list of strings.

    Rows are also comparable, for what that's worth. Only the cells are
    compared.

    .. _`table`: gherkin.html#table
    '''
    def __init__(self, headings, cells, line=None, comments=None):
        self.headings = headings
        self.comments = comments
        for c in cells:
            assert isinstance(c, unicode)
        self.cells = cells
        self.line = line

    def __getitem__(self, name):
        try:
            index = self.headings.index(name)
        except ValueError:
            if isinstance(name, int):
                index = name
            else:
                raise KeyError('"%s" is not a row heading' % name)
        return self.cells[index]

    def __repr__(self):
        return '<Row %r>' % (self.cells,)

    def __eq__(self, other):
        return self.cells == other.cells

    def __ne__(self, other):
        return not self == other

    def __len__(self):
        return len(self.cells)

    def __iter__(self):
        return iter(self.cells)

    def items(self):
        return zip(self.headings, self.cells)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def as_dict(self):
        """
        Converts the row and its cell data into a dictionary.
        :return: Row data as dictionary (without comments, line info).
        """
        from behave.compat.collections import OrderedDict
        return OrderedDict(self.items())


class Tag(unicode):
    """Tags appear may be associated with Features or Scenarios.

    They're a subclass of regular strings (unicode pre-Python 3) with an
    additional ``line`` number attribute (where the tag was seen in the source
    feature file.

    See :ref:`controlling things with tags`.
    """
    def __new__(cls, name, line):
        o = unicode.__new__(cls, name)
        o.line = line
        return o

    @staticmethod
    def make_name(text, unescape=False):
        """Translate text into a "valid tag" without whitespace, etc.
        Translation rules are:
          * alnum chars => same, kept
          * space chars => '_'
          * other chars => deleted

        :param text: Unicode text as input for name.
        :return: Unicode name that can be used as tag.
        """
        assert isinstance(text, unicode)
        if unescape:
            # -- UNESCAPE: Some escaped sequences
            text = text.replace("\\t", "\t").replace("\\n", "\n")
        allowed_chars = u'._-'
        chars = []
        for char in text:
            if char.isalnum() or char in allowed_chars:
                chars.append(char)
            elif char.isspace():
                chars.append(u'_')
        return u"".join(chars)


class Text(unicode):
    '''Store multiline text from a Step definition.

    The attributes are:

    .. attribute:: value

       The actual text parsed from the *feature file*.

    .. attribute:: content_type

       Currently only 'text/plain'.
    '''
    def __new__(cls, value, content_type=u'text/plain', line=0):
        assert isinstance(value, unicode)
        assert isinstance(content_type, unicode)
        o = unicode.__new__(cls, value)
        o.content_type = content_type
        o.line = line
        return o

    def line_range(self):
        line_count = len(self.splitlines())
        return (self.line, self.line + line_count + 1)

    def replace(self, old, new):
        return Text(super(Text, self).replace(old, new), self.content_type,
                    self.line)

    def assert_equals(self, expected):
        '''Assert that my text is identical to the "expected" text.

        A nice context diff will be displayed if they do not match.'
        '''
        if self == expected:
            return True
        diff = []
        for line in difflib.unified_diff(self.splitlines(),
                                         expected.splitlines()):
            diff.append(line)
        # strip unnecessary diff prefix
        diff = ['Text does not match:'] + diff[3:]
        raise AssertionError('\n'.join(diff))


class Match(Replayable):
    '''An parameter-matched *feature file* step name extracted using
    step decorator `parameters`_.

    .. attribute:: func

       The step function that this match will be applied to.

    .. attribute:: arguments

       A list of :class:`behave.model.Argument` instances containing the
       matched parameters from the step name.
    '''
    type = "match"

    def __init__(self, func, arguments=None):
        super(Match, self).__init__()
        self.func = func
        self.arguments = arguments
        self.location = None
        if func:
            self.location = self.make_location(func)

    def __repr__(self):
        if self.func:
            func_name = self.func.__name__
        else:
            func_name = '<no function>'
        return '<Match %s, %s>' % (func_name, self.location)

    def __eq__(self, other):
        if not isinstance(other, Match):
            return False
        return (self.func, self.location) == (other.func, other.location)

    def with_arguments(self, arguments):
        match = copy.copy(self)
        match.arguments = arguments
        return match

    def run(self, context):
        args = []
        kwargs = {}
        for arg in self.arguments:
            if arg.name is not None:
                kwargs[arg.name] = arg.value
            else:
                args.append(arg.value)

        with context.user_mode():
            self.func(context, *args, **kwargs)

    @staticmethod
    def make_location(step_function):
        '''
        Extracts the location information from the step function and builds
        the location string (schema: "{source_filename}:{line_number}").

        :param step_function: Function whose location should be determined.
        :return: Step function location as string.
        '''
        filename = relpath(step_function.func_code.co_filename, os.getcwd())
        line_number = step_function.func_code.co_firstlineno
        return FileLocation(filename, line_number)


class NoMatch(Match):
    '''
    Used for an "undefined step" when it can not be matched with a
    step definition.
    '''

    def __init__(self):
        Match.__init__(self, func=None)
        self.func = None
        self.arguments = []
        self.location = None


def reset_model(model_elements):
    """
    Reset the test run information stored in model elements.

    :param model_elements:  List of model elements (Feature, Scenario, ...)
    """
    for model_element in model_elements:
        model_element.reset()

########NEW FILE########
__FILENAME__ = model_describe
# -*- coding: utf-8 -*-
"""
Provides textual descriptions for :mod:`behave.model` elements.
"""

from behave.textutil import indent


# -----------------------------------------------------------------------------
# FUNCTIONS:
# -----------------------------------------------------------------------------
def escape_cell(cell):
    """
    Escape table cell contents.
    :param cell:  Table cell (as unicode string).
    :return: Escaped cell (as unicode string).
    """
    cell = cell.replace(u'\\', u'\\\\')
    cell = cell.replace(u'\n', u'\\n')
    cell = cell.replace(u'|', u'\\|')
    return cell


def escape_triple_quotes(text):
    """
    Escape triple-quotes, used for multi-line text/doc-strings.
    """
    return text.replace(u'"""', u'\\"\\"\\"')


# -----------------------------------------------------------------------------
# CLASS:
# -----------------------------------------------------------------------------
class ModelDescriptor(object):

    @staticmethod
    def describe_table(table, indentation=None):
        """
        Provide a textual description of the table (as used w/ Gherkin).

        :param table:  Table to use (as :class:`behave.model.Table`)
        :param indentation:  Line prefix to use (as string, if any).
        :return: Textual table description (as unicode string).
        """
        # -- STEP: Determine output size of all cells.
        cell_lengths = []
        all_rows = [table.headings] + table.rows
        for row in all_rows:
            lengths = [len(escape_cell(c)) for c in row]
            cell_lengths.append(lengths)

        # -- STEP: Determine max. output size for each column.
        max_lengths = []
        for col in range(0, len(cell_lengths[0])):
            max_lengths.append(max([c[col] for c in cell_lengths]))

        # -- STEP: Build textual table description.
        lines = []
        for r, row in enumerate(all_rows):
            line = u"|"
            for c, (cell, max_length) in enumerate(zip(row, max_lengths)):
                pad_size = max_length - cell_lengths[r][c]
                line += u" %s%s |" % (escape_cell(cell), " " * pad_size)
            line += u"\n"
            lines.append(line)

        if indentation:
            return indent(lines, indentation)
        # -- OTHERWISE:
        return u"".join(lines)

    @staticmethod
    def describe_docstring(doc_string, indentation=None):
        """
        Provide a textual description of the multi-line text/triple-quoted
        doc-string (as used w/ Gherkin).

        :param doc_string:  Multi-line text to use.
        :param indentation:  Line prefix to use (as string, if any).
        :return: Textual table description (as unicode string).
        """
        text = escape_triple_quotes(doc_string)
        text = u'"""\n' + text + '\n"""\n'

        if indentation:
            text = indent(text, indentation)
        return text


class ModelPrinter(ModelDescriptor):

    def __init__(self, stream):
        super(ModelPrinter, self).__init__()
        self.stream = stream

    def print_table(self, table, indentation=None):
        self.stream.write(self.describe_table(table, indentation))
        self.stream.flush()

    def print_docstring(self, text, indentation=None):
        self.stream.write(self.describe_docstring(text, indentation))
        self.stream.flush()

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

from __future__ import with_statement

from behave import model, i18n

DEFAULT_LANGUAGE = 'en'


def parse_file(filename, language=None):
    with open(filename, 'rb') as f:
        # file encoding is assumed to be utf8. Oh, yes.
        data = f.read().decode('utf8')
    return parse_feature(data, language, filename)


def parse_feature(data, language=None, filename=None):
    # ALL data operated on by the parser MUST be unicode
    assert isinstance(data, unicode)

    try:
        result = Parser(language).parse(data, filename)
    except ParserError, e:
        e.filename = filename
        raise

    return result

def parse_steps(text, language=None, filename=None):
    """
    Parse a number of steps a multi-line text from a scenario.
    Scenario line with title and keyword is not provided.

    :param text: Multi-line text with steps to parse (as unicode).
    :param language:  i18n language identifier (optional).
    :param filename:  Filename (optional).
    :return: Parsed steps (if successful).
    """
    assert isinstance(text, unicode)
    try:
        result = Parser(language, variant='steps').parse_steps(text, filename)
    except ParserError, e:
        e.filename = filename
        raise
    return result

def parse_tags(text):
    """
    Parse tags from text (one or more lines, as string).

    :param text: Multi-line text with tags to parse (as unicode).
    :return: List of tags (if successful).
    """
    # assert isinstance(text, unicode)
    if not text:
        return []
    return Parser().parse_tags(text)


class ParserError(Exception):
    def __init__(self, message, line, filename=None, line_text=None):
        if line:
            message += ' at line %d' % line
            if line_text:
                message += ": '%s'" % line_text.strip()
        super(ParserError, self).__init__(message)
        self.line = line
        self.line_text = line_text
        self.filename = filename

    def __str__(self):
        if self.filename:
            return 'Failed to parse "%s": %s' % (self.filename, self.args[0])
        return 'Failed to parse <string>: %s' % self.args[0]


class Parser(object):
    # pylint: disable=W0201,R0902
    #   W0201   Attribute ... defined outside __init__() method => reset()
    #   R0902   Too many instance attributes (15/10)

    def __init__(self, language=None, variant=None):
        if not variant:
            variant = 'feature'
        self.language = language
        self.variant = variant
        self.reset()

    def reset(self):
        # This can probably go away.
        if self.language:
            self.keywords = i18n.languages[self.language]
        else:
            self.keywords = None

        self.state = 'init'
        self.line = 0
        self.last_step = None
        self.multiline_start = None
        self.multiline_leading = None
        self.multiline_terminator = None

        self.filename = None
        self.feature = None
        self.statement = None
        self.tags = []
        self.lines = []
        self.table = None
        self.examples = None

    def parse(self, data, filename=None):
        self.reset()

        self.filename = filename

        for line in data.split('\n'):
            self.line += 1
            if not line.strip() and not self.state == 'multiline':
                # -- SKIP EMPTY LINES, except in multiline string args.
                continue
            self.action(line)

        if self.table:
            self.action_table('')

        feature = self.feature
        if feature:
            feature.parser = self
        self.reset()
        return feature

    def _build_feature(self, keyword, line):
        name = line[len(keyword) + 1:].strip()
        self.feature = model.Feature(self.filename, self.line, keyword,
                                     name, tags=self.tags)
        # -- RESET STATE:
        self.tags = []

    def _build_background_statement(self, keyword, line):
        if self.tags:
            msg = 'Background supports no tags: @%s' % (' @'.join(self.tags))
            raise ParserError(msg, self.line, self.filename, line)
        name = line[len(keyword) + 1:].strip()
        statement = model.Background(self.filename, self.line, keyword, name)
        self.statement = statement
        self.feature.background = self.statement

    def _build_scenario_statement(self, keyword, line):
        name = line[len(keyword) + 1:].strip()
        self.statement = model.Scenario(self.filename, self.line,
                                        keyword, name, tags=self.tags)
        self.feature.add_scenario(self.statement)
        # -- RESET STATE:
        self.tags = []

    def _build_scenario_outline_statement(self, keyword, line):
        # pylint: disable=C0103
        #   C0103   Invalid name "build_scenario_outline_statement", too long.
        name = line[len(keyword) + 1:].strip()
        self.statement = model.ScenarioOutline(self.filename, self.line,
                                               keyword, name, tags=self.tags)
        self.feature.add_scenario(self.statement)
        # -- RESET STATE:
        self.tags = []

    def _build_examples(self, keyword, line):
        if not isinstance(self.statement, model.ScenarioOutline):
            message = 'Examples must only appear inside scenario outline'
            raise ParserError(message, self.line, self.filename, line)
        name = line[len(keyword) + 1:].strip()
        self.examples = model.Examples(self.filename, self.line,
                                       keyword, name)
        # pylint: disable=E1103
        #   E1103   Instance of 'Background' has no 'examples' member
        #           (but some types could not be inferred).
        self.statement.examples.append(self.examples)


    def diagnose_feature_usage_error(self):
        if self.feature:
            return "Multiple features in one file are not supported."
        else:
            return "Feature should not be used here."

    def diagnose_background_usage_error(self):
        if self.feature and self.feature.scenarios:
            return "Background may not occur after Scenario/ScenarioOutline."
        elif self.tags:
            return "Background does not support tags."
        else:
            return "Background should not be used here."

    def diagnose_scenario_usage_error(self):
        if not self.feature:
            return "Scenario may not occur before Feature."
        else:
            return "Scenario should not be used here."

    def diagnose_scenario_outline_usage_error(self):
        if not self.feature:
            return "ScenarioOutline may not occur before Feature."
        else:
            return "ScenarioOutline should not be used here."

    def ask_parse_failure_oracle(self, line):
        """
        Try to find the failure reason when a parse failure occurs:

            Oracle, oracle, ... what went wrong?
            Zzzz

        :param line:  Text line where parse failure occured (as string).
        :return: Reason (as string) if an explanation is found.
                 Otherwise, empty string or None.
        """
        feature_kwd = self.match_keyword('feature', line)
        if feature_kwd:
            return self.diagnose_feature_usage_error()
        background_kwd = self.match_keyword('background', line)
        if background_kwd:
            return self.diagnose_background_usage_error()
        scenario_kwd = self.match_keyword('scenario', line)
        if scenario_kwd:
            return self.diagnose_scenario_usage_error()
        scenario_outline_kwd = self.match_keyword('scenario_outline', line)
        if scenario_outline_kwd:
            return self.diagnose_scenario_outline_usage_error()
        # -- OTHERWISE:
        if self.variant == 'feature' and not self.feature:
            return "No feature found."
        # -- FINALLY: No glue what went wrong.
        return None

    def action(self, line):
        if line.strip().startswith('#') and not self.state == 'multiline':
            if self.keywords or self.state != 'init' or self.tags:
                return

            line = line.strip()[1:].strip()
            if line.lstrip().lower().startswith('language:'):
                language = line[9:].strip()
                self.language = language
                self.keywords = i18n.languages[language]
            return

        func = getattr(self, 'action_' + self.state, None)
        if func is None:
            line = line.strip()
            msg = "Parser in unknown state %s;" % self.state
            raise ParserError(msg, self.line, self.filename, line)
        if not func(line):
            line = line.strip()
            msg = u"\nParser failure in state %s, at line %d: '%s'\n" % \
                  (self.state, self.line, line)
            reason = self.ask_parse_failure_oracle(line)
            if reason:
                msg += u"REASON: %s" % reason
            raise ParserError(msg, None, self.filename)

    def action_init(self, line):
        line = line.strip()
        if line.startswith('@'):
            self.tags.extend(self.parse_tags(line))
            return True

        feature_kwd = self.match_keyword('feature', line)
        if feature_kwd:
            self._build_feature(feature_kwd, line)
            self.state = 'feature'
            return True
        return False

    def subaction_detect_next_scenario(self, line):
        if line.startswith('@'):
            self.tags.extend(self.parse_tags(line))
            self.state = 'next_scenario'
            return True

        scenario_kwd = self.match_keyword('scenario', line)
        if scenario_kwd:
            self._build_scenario_statement(scenario_kwd, line)
            self.state = 'scenario'
            return True

        scenario_outline_kwd = self.match_keyword('scenario_outline', line)
        if scenario_outline_kwd:
            self._build_scenario_outline_statement(scenario_outline_kwd, line)
            self.state = 'scenario'
            return True

        # -- OTHERWISE:
        return False

    def action_feature(self, line):
        line = line.strip()
        if self.subaction_detect_next_scenario(line):
            return True

        background_kwd = self.match_keyword('background', line)
        if background_kwd:
            self._build_background_statement(background_kwd, line)
            self.state = 'steps'
            return True

        self.feature.description.append(line)
        return True

    def action_next_scenario(self, line):
        """
        Entered after first tag for Scenario/ScenarioOutline is detected.
        """
        line = line.strip()
        if self.subaction_detect_next_scenario(line):
            return True

        return False

    def action_scenario(self, line):
        """
        Entered when Scenario/ScenarioOutline keyword/line is detected.
        Hunts/collects scenario description lines.

        DETECT:
            * first step of Scenario/ScenarioOutline
            * next Scenario/ScenarioOutline.
        """
        line = line.strip()
        step = self.parse_step(line)
        if step:
            # -- FIRST STEP DETECTED: End collection of scenario descriptions.
            self.state = 'steps'
            self.statement.steps.append(step)
            return True

        # -- CASE: Detect next Scenario/ScenarioOutline
        #   * Scenario with scenario description, but without steps.
        #   * Title-only scenario without scenario description and steps.
        if self.subaction_detect_next_scenario(line):
            return True

        # -- OTHERWISE: Add scenario description line.
        # pylint: disable=E1103
        #   E1103   Instance of 'Background' has no 'description' member...
        self.statement.description.append(line)
        return True

    def action_steps(self, line):
        """
        Entered when first step is detected (or nested step parsing).

        Subcases:
          * step
          * multi-line text (doc-string), following a step
          * table, following a step
          * examples for a ScenarioOutline, after ScenarioOutline steps

        DETECT:
          * next Scenario/ScenarioOutline
        """
        # pylint: disable=R0911
        #   R0911   Too many return statements (8/6)
        stripped = line.lstrip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            self.state = 'multiline'
            self.multiline_start = self.line
            self.multiline_terminator = stripped[:3]
            self.multiline_leading = line.index(stripped[0])
            return True

        line = line.strip()
        step = self.parse_step(line)
        if step:
            self.statement.steps.append(step)
            return True

        if self.subaction_detect_next_scenario(line):
            return True

        examples_kwd = self.match_keyword('examples', line)
        if examples_kwd:
            self._build_examples(examples_kwd, line)
            self.state = 'table'
            return True

        if line.startswith('|'):
            assert self.statement.steps, "TABLE-START without step detected."
            self.state = 'table'
            return self.action_table(line)

        return False

    def action_multiline(self, line):
        if line.strip().startswith(self.multiline_terminator):
            step = self.statement.steps[-1]
            step.text = model.Text(u'\n'.join(self.lines), u'text/plain',
                                   self.multiline_start)
            if step.name.endswith(':'):
                step.name = step.name[:-1]
            self.lines = []
            self.multiline_terminator = None
            self.state = 'steps'
            return True

        self.lines.append(line[self.multiline_leading:])
        # -- BETTER DIAGNOSTICS: May remove non-whitespace in execute_steps()
        removed_line_prefix = line[:self.multiline_leading]
        if removed_line_prefix.strip():
            message  = "BAD-INDENT in multiline text: "
            message += "Line '%s' would strip leading '%s'" % \
                        (line, removed_line_prefix)
            raise ParserError(message, self.line, self.filename)
        return True

    def action_table(self, line):
        line = line.strip()

        if not line.startswith('|'):
            if self.examples:
                self.examples.table = self.table
                self.examples = None
            else:
                step = self.statement.steps[-1]
                step.table = self.table
                if step.name.endswith(':'):
                    step.name = step.name[:-1]
            self.table = None
            self.state = 'steps'
            return self.action_steps(line)

        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if self.table is None:
            self.table = model.Table(cells, self.line)
        else:
            if len(cells) != len(self.table.headings):
                raise ParserError("Malformed table", self.line)
            self.table.add_row(cells, self.line)
        return True

    def match_keyword(self, keyword, line):
        if not self.keywords:
            self.language = DEFAULT_LANGUAGE
            self.keywords = i18n.languages[DEFAULT_LANGUAGE]
        for alias in self.keywords[keyword]:
            if line.startswith(alias + ':'):
                return alias
        return False

    def parse_tags(self, line):
        '''
        Parse a line with one or more tags:

          * A tag starts with the AT sign.
          * A tag consists of one word without whitespace chars.
          * Multiple tags are separated with whitespace chars
          * End-of-line comment is stripped.

        :param line:   Line with one/more tags to process.
        :raise ParseError: If syntax error is detected.
        '''
        assert line.startswith('@')
        tags = []
        for word in line.split():
            if word.startswith('@'):
                tags.append(model.Tag(word[1:], self.line))
            elif word.startswith('#'):
                break   # -- COMMENT: Skip rest of line.
            else:
                # -- BAD-TAG: Abort here.
                raise ParserError("tag: %s (line: %s)" % (word, line),
                                  self.line, self.filename)
        return tags

    def parse_step(self, line):
        for step_type in ('given', 'when', 'then', 'and', 'but'):
            for kw in self.keywords[step_type]:
                if kw.endswith('<'):
                    whitespace = ''
                    kw = kw[:-1]
                else:
                    whitespace = ' '

                # try to match the keyword; also attempt a purely lowercase
                # match if that'll work
                if not (line.startswith(kw + whitespace)
                        or line.lower().startswith(kw.lower() + whitespace)):
                    continue

                name = line[len(kw):].strip()
                if step_type in ('and', 'but'):
                    if not self.last_step:
                        raise ParserError("No previous step", self.line)
                    step_type = self.last_step
                else:
                    self.last_step = step_type
                step = model.Step(self.filename, self.line, kw, step_type,
                                  name)
                return step
        return None

    def parse_steps(self, text, filename=None):
        """
        Parse support for execute_steps() functionality that supports step with:
          * multiline text
          * table

        :param text:  Text that contains 0..* steps
        :return: List of parsed steps (as model.Step objects).
        """
        assert isinstance(text, unicode)
        if not self.language:
            self.language = u"en"
        self.reset()
        self.filename = filename
        self.statement = model.Scenario(filename, 0, u"scenario", u"")
        self.state = 'steps'

        for line in text.split("\n"):
            self.line += 1
            if not line.strip() and not self.state == 'multiline':
                # -- SKIP EMPTY LINES, except in multiline string args.
                continue
            self.action(line)

        # -- FINALLY:
        if self.table:
            self.action_table("")
        steps = self.statement.steps
        return steps


########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

class Reporter(object):
    """
    Base class for all reporters.
    A reporter provides an extension point (variant point) for the runner logic.
    A reporter is called after a model element is processed
    (and its result status is known).
    Otherwise, a reporter is similar to a formatter, but it has a simpler API.

    Processing Logic (simplified)::

        config.reporters = ...  #< Configuration (and provision).
        runner.run():
            for feature in runner.features:
                feature.run()     # And feature scenarios, too.
                for reporter in config.reporters:
                    reporter.feature(feature)
            # -- FINALLY:
            for reporter in config.reporters:
                reporter.end()

    An existing formatter can be reused as reporter by using
    :class:`behave.report.formatter_reporter.FormatterAsReporter`.
    """
    def __init__(self, config):
        self.config = config

    def feature(self, feature):
        """
        Called after a feature was processed.

        :param feature:  Feature object (as :class:`behave.model.Feature`)
        """
        assert feature.status in ("skipped", "passed", "failed")
        raise NotImplementedError

    def end(self):
        """
        Called after all model elements are processed (optional-hook).
        """
        pass

########NEW FILE########
__FILENAME__ = junit
# -*- coding: utf-8 -*-

import os.path
import codecs
from xml.etree import ElementTree
from behave.reporter.base import Reporter
from behave.model import Scenario, ScenarioOutline, Step
from behave.formatter import ansi_escapes
from behave.model_describe import ModelDescriptor
from behave.textutil import indent, make_indentation


def CDATA(text=None):
    # -- issue #70: remove_ansi_escapes(text)
    element = ElementTree.Element('![CDATA[')
    element.text = ansi_escapes.strip_escapes(text)
    return element


class ElementTreeWithCDATA(ElementTree.ElementTree):
    def _write(self, file, node, encoding, namespaces):
        """This method is for ElementTree <= 1.2.6"""

        if node.tag == '![CDATA[':
            text = node.text.encode(encoding)
            file.write("\n<![CDATA[%s]]>\n" % text)
        else:
            ElementTree.ElementTree._write(self, file, node, encoding,
                                           namespaces)


if hasattr(ElementTree, '_serialize'):
    def _serialize_xml(write, elem, encoding, qnames, namespaces,
                       orig=ElementTree._serialize_xml):
        if elem.tag == '![CDATA[':
            write("\n<%s%s]]>\n" % (elem.tag, elem.text.encode(encoding)))
            return
        return orig(write, elem, encoding, qnames, namespaces)

    ElementTree._serialize_xml = ElementTree._serialize['xml'] = _serialize_xml


class FeatureReportData(object):
    """
    Provides value object to collect JUnit report data from a Feature.
    """
    def __init__(self, feature, filename, classname=None):
        if not classname and filename:
            classname = filename.replace('/', '.')
        self.feature = feature
        self.filename = filename
        self.classname = classname
        self.testcases = []
        self.counts_tests = 0
        self.counts_errors = 0
        self.counts_failed = 0
        self.counts_skipped = 0

    def reset(self):
        self.testcases = []
        self.counts_tests = 0
        self.counts_errors = 0
        self.counts_failed = 0
        self.counts_skipped = 0


class JUnitReporter(Reporter):
    """
    Generates JUnit-like XML test report for behave.
    """
    show_multiline = True
    show_timings   = True     # -- Show step timings.

    def make_feature_filename(self, feature):
        filename = None
        for path in self.config.paths:
            if feature.filename.startswith(path):
                filename = feature.filename[len(path) + 1:]
                break
        if not filename:
            # -- NOTE: Directory path (subdirs) are taken into account.
            filename = feature.location.relpath(self.config.base_dir)
        filename = filename.rsplit('.', 1)[0]
        filename = filename.replace('\\', '/').replace('/', '.')
        return filename

    # -- REPORTER-API:
    def feature(self, feature):
        filename  = self.make_feature_filename(feature)
        classname = filename
        report    = FeatureReportData(feature, filename)
        filename  = 'TESTS-%s.xml' % filename

        suite = ElementTree.Element('testsuite')
        suite.set('name', '%s.%s' % (classname, feature.name or feature.filename))

        # -- BUILD-TESTCASES: From scenarios
        for scenario in feature:
            if isinstance(scenario, ScenarioOutline):
                scenario_outline = scenario
                self._process_scenario_outline(scenario_outline, report)
            else:
                self._process_scenario(scenario, report)

        # -- ADD TESTCASES to testsuite:
        for testcase in report.testcases:
            suite.append(testcase)

        suite.set('tests', str(report.counts_tests))
        suite.set('errors', str(report.counts_errors))
        suite.set('failures', str(report.counts_failed))
        suite.set('skipped', str(report.counts_skipped))  # WAS: skips
        # -- ORIG: suite.set('time', str(round(feature.duration, 3)))
        suite.set('time', str(round(feature.duration, 6)))

        if not os.path.exists(self.config.junit_directory):
            # -- ENSURE: Create multiple directory levels at once.
            os.makedirs(self.config.junit_directory)

        tree = ElementTreeWithCDATA(suite)
        report_filename = os.path.join(self.config.junit_directory, filename)
        tree.write(codecs.open(report_filename, 'w'), 'UTF-8')

    # -- MORE:
    @staticmethod
    def select_step_with_status(status, steps):
        """
        Helper function to find the first step that has the given step.status.

        EXAMPLE: Search for a failing step in a scenario (all steps).
            >>> scenario = ...
            >>> failed_step = select_step_with_status("failed", scenario)
            >>> failed_step = select_step_with_status("failed", scenario.all_steps)
            >>> assert failed_step.status == "failed"

        EXAMPLE: Search only scenario steps, skip background steps.
            >>> failed_step = select_step_with_status("failed", scenario.steps)

        :param status:  Step status to search for (as string).
        :param steps:   List of steps to search in (or scenario).
        :returns: Step object, if found.
        :returns: None, otherwise.
        """
        for step in steps:
            assert isinstance(step, Step), \
                "TYPE-MISMATCH: step.class=%s"  % step.__class__.__name__
            if step.status == status:
                return step
        # -- OTHERWISE: No step with the given status found.
        # KeyError("Step with status={0} not found".format(status))
        return None

    @classmethod
    def describe_step(cls, step):
        status = str(step.status)
        if cls.show_timings:
            status += u" in %0.3fs" % step.duration
        text  = u'%s %s ... ' % (step.keyword, step.name)
        text += u'%s\n' % status
        if cls.show_multiline:
            prefix = make_indentation(2)
            if step.text:
                text += ModelDescriptor.describe_docstring(step.text, prefix)
            elif step.table:
                text += ModelDescriptor.describe_table(step.table, prefix)
        return text

    @classmethod
    def describe_scenario(cls, scenario):
        """
        Describe the scenario and the test status.
        NOTE: table, multiline text is missing in description.

        :param scenario:  Scenario that was tested.
        :return: Textual description of the scenario.
        """
        header_line  = u'\n@scenario.begin\n'
        header_line += '  %s: %s\n' % (scenario.keyword, scenario.name)
        footer_line  = u'\n@scenario.end\n' + u'-' * 80 + '\n'
        text = u''
        for step in scenario:
            text += cls.describe_step(step)
        step_indentation = make_indentation(4)
        return header_line + indent(text, step_indentation) + footer_line

    def _process_scenario(self, scenario, report):
        """
        Process a scenario and append information to JUnit report object.
        This corresponds to a JUnit testcase:

          * testcase.@classname = f(filename) +'.'+ feature.name
          * testcase.@name   = scenario.name
          * testcase.@status = scenario.status
          * testcase.@time   = scenario.duration

        Distinguishes now between failures and errors.
        Failures are AssertationErrors: expectation is violated/not met.
        Errors are unexpected RuntimeErrors (all other exceptions).

        If a failure/error occurs, the step, that caused the failure,
        and its location are provided now.

        :param scenario:  Scenario to process.
        :param report:    Context object to store/add info to (outgoing param).
        """
        assert isinstance(scenario, Scenario)
        assert not isinstance(scenario, ScenarioOutline)
        feature   = report.feature
        classname = report.classname
        report.counts_tests += 1

        case = ElementTree.Element('testcase')
        case.set('classname', '%s.%s' % (classname, feature.name or feature.filename))
        case.set('name', scenario.name or '')
        case.set('status', scenario.status)
        # -- ORIG: case.set('time', str(round(scenario.duration, 3)))
        case.set('time', str(round(scenario.duration, 6)))

        step = None
        if scenario.status == 'failed':
            for status in ('failed', 'undefined'):
                step = self.select_step_with_status(status, scenario)
                if step:
                    break
            assert step, "OOPS: No failed step found in scenario: %s" % scenario.name
            assert step.status in ('failed', 'undefined')
            element_name = 'failure'
            if isinstance(step.exception, (AssertionError, type(None))):
                # -- FAILURE: AssertionError
                report.counts_failed += 1
            else:
                # -- UNEXPECTED RUNTIME-ERROR:
                report.counts_errors += 1
                element_name = 'error'
            # -- COMMON-PART:
            failure = ElementTree.Element(element_name)
            step_text = self.describe_step(step).rstrip()
            text = u"\nFailing step: %s\nLocation: %s\n" % (step_text, step.location)
            message = unicode(step.exception)
            if len(message) > 80:
                message = message[:80] + "..."
            failure.set('type', step.exception.__class__.__name__)
            failure.set('message', message)
            text += unicode(step.error_message)
            failure.append(CDATA(text))
            case.append(failure)
        elif scenario.status in ('skipped', 'untested'):
            report.counts_skipped += 1
            step = self.select_step_with_status('undefined', scenario)
            if step:
                # -- UNDEFINED-STEP:
                report.counts_failed += 1
                failure = ElementTree.Element('failure')
                failure.set('type', 'undefined')
                failure.set('message', ('Undefined Step: %s' % step.name))
                case.append(failure)
            else:
                skip = ElementTree.Element('skipped')
                case.append(skip)

        # Create stdout section for each test case
        stdout = ElementTree.Element('system-out')
        text  = self.describe_scenario(scenario)

        # Append the captured standard output
        if scenario.stdout:
            text += '\nCaptured stdout:\n%s\n' % scenario.stdout
        stdout.append(CDATA(text))
        case.append(stdout)

        # Create stderr section for each test case
        if scenario.stderr:
            stderr = ElementTree.Element('system-err')
            text = u'\nCaptured stderr:\n%s\n' % scenario.stderr
            stderr.append(CDATA(text))
            case.append(stderr)

        report.testcases.append(case)

    def _process_scenario_outline(self, scenario_outline, report):
        assert isinstance(scenario_outline, ScenarioOutline)
        for scenario in scenario_outline:
            assert isinstance(scenario, Scenario)
            self._process_scenario(scenario, report)

########NEW FILE########
__FILENAME__ = summary
# -*- coding: UTF-8 -*-
"""
Provides a summary after each test run.
"""

import sys
from behave.model import ScenarioOutline
from behave.reporter.base import Reporter


# -- DISABLED: optional_steps = ('untested', 'undefined')
optional_steps = ('untested',)


def format_summary(statement_type, summary):
    parts = []
    for status in ('passed', 'failed', 'skipped', 'undefined', 'untested'):
        if status not in summary:
            continue
        counts = summary[status]
        if status in optional_steps and counts == 0:
            # -- SHOW-ONLY: For relevant counts, suppress: untested items, etc.
            continue

        if not parts:
            # -- FIRST ITEM: Add statement_type to counter.
            label = statement_type
            if counts != 1:
                label += 's'
            part = '%d %s %s' % (counts, label, status)
        else:
            part = '%d %s' % (counts, status)
        parts.append(part)
    return ', '.join(parts) + '\n'


class SummaryReporter(Reporter):
    show_failed_scenarios = True
    output_stream_name = "stdout"

    def __init__(self, config):
        super(SummaryReporter, self).__init__(config)
        self.stream = getattr(sys, self.output_stream_name, sys.stderr)
        self.feature_summary = {'passed': 0, 'failed': 0, 'skipped': 0,
                                'untested': 0}
        self.scenario_summary = {'passed': 0, 'failed': 0, 'skipped': 0,
                                 'untested': 0}
        self.step_summary = {'passed': 0, 'failed': 0, 'skipped': 0,
                             'undefined': 0, 'untested': 0}
        self.duration = 0.0
        self.failed_scenarios = []

    def feature(self, feature):
        self.feature_summary[feature.status or 'skipped'] += 1
        self.duration += feature.duration
        for scenario in feature:
            if isinstance(scenario, ScenarioOutline):
                self.process_scenario_outline(scenario)
            else:
                self.process_scenario(scenario)

    def end(self):
        # -- SHOW FAILED SCENARIOS (optional):
        if self.show_failed_scenarios and self.failed_scenarios:
            self.stream.write("\nFailing scenarios:\n")
            for scenario in self.failed_scenarios:
                self.stream.write("  %s  %s\n" % (
                    scenario.location, scenario.name))
            self.stream.write("\n")

        # -- SHOW SUMMARY COUNTS:
        self.stream.write(format_summary('feature', self.feature_summary))
        self.stream.write(format_summary('scenario', self.scenario_summary))
        self.stream.write(format_summary('step', self.step_summary))
        timings = int(self.duration / 60), self.duration % 60
        self.stream.write('Took %dm%02.3fs\n' % timings)

    def process_scenario(self, scenario):
        if scenario.status == 'failed':
            self.failed_scenarios.append(scenario)
        self.scenario_summary[scenario.status or 'skipped'] += 1
        for step in scenario:
            self.step_summary[step.status or 'skipped'] += 1

    def process_scenario_outline(self, scenario_outline):
        for scenario in scenario_outline.scenarios:
            self.process_scenario(scenario)

########NEW FILE########
__FILENAME__ = runner
# -*- coding: utf-8 -*-

from __future__ import with_statement
import contextlib
import os.path
import StringIO
import sys
import traceback
import warnings
import weakref

from behave import matchers
from behave.step_registry import setup_step_decorators
from behave.formatter import formatters
from behave.configuration import ConfigError
from behave.log_capture import LoggingCapture
from behave.runner_util import \
    collect_feature_locations, parse_features


class ContextMaskWarning(UserWarning):
    '''Raised if a context variable is being overwritten in some situations.

    If the variable was originally set by user code then this will be raised if
    *behave* overwites the value.

    If the variable was originally set by *behave* then this will be raised if
    user code overwites the value.
    '''
    pass


class Context(object):
    '''Hold contextual information during the running of tests.

    This object is a place to store information related to the tests you're
    running. You may add arbitrary attributes to it of whatever value you need.

    During the running of your tests the object will have additional layers of
    namespace added and removed automatically. There is a "root" namespace and
    additional namespaces for features and scenarios.

    Certain names are used by *behave*; be wary of using them yourself as
    *behave* may overwrite the value you set. These names are:

    .. attribute:: feature

      This is set when we start testing a new feature and holds a
      :class:`~behave.model.Feature`. It will not be present outside of a
      feature (i.e. within the scope of the environment before_all and
      after_all).

    .. attribute:: scenario

      This is set when we start testing a new scenario (including the
      individual scenarios of a scenario outline) and holds a
      :class:`~behave.model.Scenario`. It will not be present outside of the
      scope of a scenario.

    .. attribute:: tags

      The current set of active tags (as a Python set containing instances of
      :class:`~behave.model.Tag` which are basically just glorified strings)
      combined from the feature and scenario. This attribute will not be
      present outside of a feature scope.

    .. attribute:: aborted

      This is set to true in the root namespace when the user aborts a test run
      (:exc:`KeyboardInterrupt` exception). Initially: False.

    .. attribute:: failed

      This is set to true in the root namespace as soon as a step fails.
      Initially: False.

    .. attribute:: table

      This is set at the step level and holds any :class:`~behave.model.Table`
      associated with the step.

    .. attribute:: text

      This is set at the step level and holds any multiline text associated
      with the step.

    .. attribute:: config

      The configuration of *behave* as determined by configuration files and
      command-line options. The attributes of this object are the same as the
      `configuration file settion names`_.

    .. attribute:: active_outline

      This is set for each scenario in a scenario outline and references the
      :class:`~behave.model.Row` that is active for the current scenario. It is
      present mostly for debugging, but may be useful otherwise.

    .. attribute:: log_capture

      If logging capture is enabled then this attribute contains the captured
      logging as an instance of :class:`~behave.log_capture.LoggingCapture`.
      It is not present if logging is not being captured.

    .. attribute:: stdout_capture

      If stdout capture is enabled then this attribute contains the captured
      output as a StringIO instance. It is not present if stdout is not being
      captured.

    .. attribute:: stderr_capture

      If stderr capture is enabled then this attribute contains the captured
      output as a StringIO instance. It is not present if stderr is not being
      captured.

    If an attempt made by user code to overwrite one of these variables, or
    indeed by *behave* to overwite a user-set variable, then a
    :class:`behave.runner.ContextMaskWarning` warning will be raised.

    You may use the "in" operator to test whether a certain value has been set
    on the context, for example:

        'feature' in context

    checks whether there is a "feature" value in the context.

    Values may be deleted from the context using "del" but only at the level
    they are set. You can't delete a value set by a feature at a scenario level
    but you can delete a value set for a scenario in that scenario.

    .. _`configuration file settion names`: behave.html#configuration-files
    '''
    BEHAVE = 'behave'
    USER = 'user'

    def __init__(self, runner):
        self._runner = weakref.proxy(runner)
        self._config = runner.config
        d = self._root = {
            'aborted': False,
            'failed': False,
            'config': self._config,
            'active_outline': None,
        }
        self._stack = [d]
        self._record = {}
        self._origin = {}
        self._mode = self.BEHAVE
        self.feature = None

    def _push(self):
        self._stack.insert(0, {})

    def _pop(self):
        self._stack.pop(0)

    @contextlib.contextmanager
    def user_mode(self):
        try:
            self._mode = self.USER
            yield
        finally:
            # -- NOTE: Otherwise skipped if AssertionError/Exception is raised.
            self._mode = self.BEHAVE

    def _set_root_attribute(self, attr, value):
        for frame in self.__dict__['_stack']:
            if frame is self.__dict__['_root']:
                continue
            if attr in frame:
                record = self.__dict__['_record'][attr]
                params = {
                    'attr': attr,
                    'filename': record[0],
                    'line': record[1],
                    'function': record[3],
                }
                self._emit_warning(attr, params)

        self.__dict__['_root'][attr] = value
        if attr not in self._origin:
            self._origin[attr] = self._mode

    def _emit_warning(self, attr, params):
        msg = ''
        if self._mode is self.BEHAVE and self._origin[attr] is not self.BEHAVE:
            msg = "behave runner is masking context attribute '%(attr)s' " \
                  "orignally set in %(function)s (%(filename)s:%(line)s)"
        elif self._mode is self.USER:
            if self._origin[attr] is not self.USER:
                msg = "user code is masking context attribute '%(attr)s' " \
                      "orignally set by behave"
            elif self._config.verbose:
                msg = "user code is masking context attribute " \
                    "'%(attr)s'; see the tutorial for what this means"
        if msg:
            msg = msg % params
            warnings.warn(msg, ContextMaskWarning, stacklevel=3)

    def _dump(self):
        for level, frame in enumerate(self._stack):
            print 'Level %d' % level
            print repr(frame)

    def __getattr__(self, attr):
        if attr[0] == '_':
            return self.__dict__[attr]
        for frame in self._stack:
            if attr in frame:
                return frame[attr]
        msg = "'{0}' object has no attribute '{1}'"
        msg = msg.format(self.__class__.__name__, attr)
        raise AttributeError(msg)

    def __setattr__(self, attr, value):
        if attr[0] == '_':
            self.__dict__[attr] = value
            return

        for frame in self._stack[1:]:
            if attr in frame:
                record = self._record[attr]
                params = {
                    'attr': attr,
                    'filename': record[0],
                    'line': record[1],
                    'function': record[3],
                }
                self._emit_warning(attr, params)

        stack_frame = traceback.extract_stack(limit=2)[0]
        self._record[attr] = stack_frame
        frame = self._stack[0]
        frame[attr] = value
        if attr not in self._origin:
            self._origin[attr] = self._mode

    def __delattr__(self, attr):
        frame = self._stack[0]
        if attr in frame:
            del frame[attr]
            del self._record[attr]
        else:
            msg = "'{0}' object has no attribute '{1}' at the current level"
            msg = msg.format(self.__class__.__name__, attr)
            raise AttributeError(msg)

    def __contains__(self, attr):
        if attr[0] == '_':
            return attr in self.__dict__
        for frame in self._stack:
            if attr in frame:
                return True
        return False

    def execute_steps(self, steps_text):
        '''The steps identified in the "steps" text string will be parsed and
        executed in turn just as though they were defined in a feature file.

        If the execute_steps call fails (either through error or failure
        assertion) then the step invoking it will fail.

        ValueError will be raised if this is invoked outside a feature context.

        Returns boolean False if the steps are not parseable, True otherwise.
        '''
        assert isinstance(steps_text, unicode), "Steps must be unicode."
        if not self.feature:
            raise ValueError('execute_steps() called outside of feature')

        # -- PREPARE: Save original context data for current step.
        # Needed if step definition that called this method uses .table/.text
        original_table = getattr(self, "table", None)
        original_text  = getattr(self, "text", None)

        self.feature.parser.variant = 'steps'
        steps = self.feature.parser.parse_steps(steps_text)
        for step in steps:
            passed = step.run(self._runner, quiet=True, capture=False)
            if not passed:
                # -- ISSUE #96: Provide more substep info to diagnose problem.
                step_line = u"%s %s" % (step.keyword, step.name)
                message = "%s SUB-STEP: %s" % (step.status.upper(), step_line)
                if step.error_message:
                    message += "\nSubstep info: %s" % step.error_message
                assert False, message

        # -- FINALLY: Restore original context data for current step.
        self.table = original_table
        self.text  = original_text
        return True


def exec_file(filename, globals={}, locals=None):
    if locals is None:
        locals = globals
    locals['__file__'] = filename
    if sys.version_info[0] == 3:
        with open(filename) as f:
            # -- FIX issue #80: exec(f.read(), globals, locals)
            filename2 = os.path.relpath(filename, os.getcwd())
            code = compile(f.read(), filename2, 'exec')
            exec(code, globals, locals)
    else:
        execfile(filename, globals, locals)


def path_getrootdir(path):
    """
    Extract rootdir from path in a platform independent way.

    POSIX-PATH EXAMPLE:
        rootdir = path_getrootdir("/foo/bar/one.feature")
        assert rootdir == "/"

    WINDOWS-PATH EXAMPLE:
        rootdir = path_getrootdir("D:\\foo\\bar\\one.feature")
        assert rootdir == r"D:\"
    """
    drive, _ = os.path.splitdrive(path)
    if drive:
        # -- WINDOWS:
        return drive + os.path.sep
    # -- POSIX:
    return os.path.sep


class PathManager(object):
    """
    Context manager to add paths to sys.path (python search path) within a scope
    """
    def __init__(self, paths=None):
        self.initial_paths = paths or []
        self.paths = None

    def __enter__(self):
        self.paths = list(self.initial_paths)
        sys.path = self.paths + sys.path

    def __exit__(self, *crap):
        for path in self.paths:
            sys.path.remove(path)
        self.paths = None

    def add(self, path):
        if self.paths is None:
            # -- CALLED OUTSIDE OF CONTEXT:
            self.initial_paths.append(path)
        else:
            sys.path.insert(0, path)
            self.paths.append(path)


class ModelRunner(object):
    """
    Test runner for a behave model (features).
    Provides the core functionality of a test runner and
    the functional API needed by model elements.

    .. attribute:: aborted

          This is set to true when the user aborts a test run
          (:exc:`KeyboardInterrupt` exception). Initially: False.
          Stored as derived attribute in :attr:`Context.aborted`.
    """

    def __init__(self, config, features=None):
        self.config = config
        self.features = features or []
        self.hooks = {}
        self.formatters = []
        self.undefined_steps = []

        self.context = None
        self.feature = None

        self.stdout_capture = None
        self.stderr_capture = None
        self.log_capture = None
        self.old_stdout = None
        self.old_stderr = None

    # @property
    def _get_aborted(self):
        value = False
        if self.context:
            value = self.context.aborted
        return value

    # @aborted.setter
    def _set_aborted(self, value):
        assert self.context
        self.context._set_root_attribute('aborted', bool(value))

    aborted = property(_get_aborted, _set_aborted,
                       doc="Indicates that test run is aborted by the user.")

    def run_hook(self, name, context, *args):
        if not self.config.dry_run and (name in self.hooks):
            # try:
            with context.user_mode():
                self.hooks[name](context, *args)
            # except KeyboardInterrupt:
            #     self.aborted = True
            #     if name not in ("before_all", "after_all"):
            #         raise

    def setup_capture(self):
        if not self.context:
            self.context = Context(self)

        if self.config.stdout_capture:
            self.stdout_capture = StringIO.StringIO()
            self.context.stdout_capture = self.stdout_capture

        if self.config.stderr_capture:
            self.stderr_capture = StringIO.StringIO()
            self.context.stderr_capture = self.stderr_capture

        if self.config.log_capture:
            self.log_capture = LoggingCapture(self.config)
            self.log_capture.inveigle()
            self.context.log_capture = self.log_capture

    def start_capture(self):
        if self.config.stdout_capture:
            # -- REPLACE ONLY: In non-capturing mode.
            if not self.old_stdout:
                self.old_stdout = sys.stdout
                sys.stdout = self.stdout_capture
            assert sys.stdout is self.stdout_capture

        if self.config.stderr_capture:
            # -- REPLACE ONLY: In non-capturing mode.
            if not self.old_stderr:
                self.old_stderr = sys.stderr
                sys.stderr = self.stderr_capture
            assert sys.stderr is self.stderr_capture

    def stop_capture(self):
        if self.config.stdout_capture:
            # -- RESTORE ONLY: In capturing mode.
            if self.old_stdout:
                sys.stdout = self.old_stdout
                self.old_stdout = None
            assert sys.stdout is not self.stdout_capture

        if self.config.stderr_capture:
            # -- RESTORE ONLY: In capturing mode.
            if self.old_stderr:
                sys.stderr = self.old_stderr
                self.old_stderr = None
            assert sys.stderr is not self.stderr_capture

    def teardown_capture(self):
        if self.config.log_capture:
            self.log_capture.abandon()

    def run_model(self, features=None):
        if not self.context:
            self.context = Context(self)
        if features is None:
            features = self.features

        # -- ENSURE: context.execute_steps() works in weird cases (hooks, ...)
        context = self.context
        self.setup_capture()
        self.run_hook('before_all', context)

        run_feature = not self.aborted
        failed_count = 0
        undefined_steps_initial_size = len(self.undefined_steps)
        for feature in features:
            if run_feature:
                try:
                    self.feature = feature
                    for formatter in self.formatters:
                        formatter.uri(feature.filename)

                    failed = feature.run(self)
                    if failed:
                        failed_count += 1
                        if self.config.stop or self.aborted:
                            # -- FAIL-EARLY: After first failure.
                            run_feature = False
                except KeyboardInterrupt:
                    self.aborted = True
                    failed_count += 1
                    run_feature = False

            # -- ALWAYS: Report run/not-run feature to reporters.
            # REQUIRED-FOR: Summary to keep track of untested features.
            for reporter in self.config.reporters:
                reporter.feature(feature)

        # -- AFTER-ALL:
        if self.aborted:
            print "\nABORTED: By user."
        for formatter in self.formatters:
            formatter.close()
        self.run_hook('after_all', self.context)
        for reporter in self.config.reporters:
            reporter.end()
        # if self.aborted:
        #     print "\nABORTED: By user."
        failed = ((failed_count > 0) or self.aborted or
                  (len(self.undefined_steps) > undefined_steps_initial_size))
        return failed

    def run(self):
        """
        Implements the run method by running the model.
        """
        self.context = Context(self)
        return self.run_model()


class Runner(ModelRunner):
    """
    Standard test runner for behave:

      * setup paths
      * loads environment hooks
      * loads step definitions
      * select feature files, parses them and creates model (elements)
    """
    def __init__(self, config):
        super(Runner, self).__init__(config)
        self.path_manager = PathManager()
        self.base_dir = None


    def setup_paths(self):
        if self.config.paths:
            if self.config.verbose:
                print 'Supplied path:', \
                      ', '.join('"%s"' % path for path in self.config.paths)
            first_path = self.config.paths[0]
            if hasattr(first_path, "filename"):
                # -- BETTER: isinstance(first_path, FileLocation):
                first_path = first_path.filename
            base_dir = first_path
            if base_dir.startswith('@'):
                # -- USE: behave @features.txt
                base_dir = base_dir[1:]
                file_locations = self.feature_locations()
                if file_locations:
                    base_dir = os.path.dirname(file_locations[0].filename)
            base_dir = os.path.abspath(base_dir)

            # supplied path might be to a feature file
            if os.path.isfile(base_dir):
                if self.config.verbose:
                    print 'Primary path is to a file so using its directory'
                base_dir = os.path.dirname(base_dir)
        else:
            if self.config.verbose:
                print 'Using default path "./features"'
            base_dir = os.path.abspath('features')

        # Get the root. This is not guaranteed to be '/' because Windows.
        root_dir = path_getrootdir(base_dir)
        new_base_dir = base_dir

        while True:
            if self.config.verbose:
                print 'Trying base directory:', new_base_dir

            if os.path.isdir(os.path.join(new_base_dir, 'steps')):
                break
            if os.path.isfile(os.path.join(new_base_dir, 'environment.py')):
                break
            if new_base_dir == root_dir:
                break

            new_base_dir = os.path.dirname(new_base_dir)

        if new_base_dir == root_dir:
            if self.config.verbose:
                if not self.config.paths:
                    print 'ERROR: Could not find "steps" directory. Please '\
                        'specify where to find your features.'
                else:
                    print 'ERROR: Could not find "steps" directory in your '\
                        'specified path "%s"' % base_dir
            raise ConfigError('No steps directory in "%s"' % base_dir)

        base_dir = new_base_dir
        self.config.base_dir = base_dir

        for dirpath, dirnames, filenames in os.walk(base_dir):
            if [fn for fn in filenames if fn.endswith('.feature')]:
                break
        else:
            if self.config.verbose:
                if not self.config.paths:
                    print 'ERROR: Could not find any "<name>.feature" files. '\
                        'Please specify where to find your features.'
                else:
                    print 'ERROR: Could not find any "<name>.feature" files '\
                        'in your specified path "%s"' % base_dir
            raise ConfigError('No feature files in "%s"' % base_dir)

        self.base_dir = base_dir
        self.path_manager.add(base_dir)
        if not self.config.paths:
            self.config.paths = [base_dir]

        if base_dir != os.getcwd():
            self.path_manager.add(os.getcwd())

    def before_all_default_hook(self, context):
        """
        Default implementation for :func:`before_all()` hook.
        Setup the logging subsystem based on the configuration data.
        """
        context.config.setup_logging()

    def load_hooks(self, filename='environment.py'):
        hooks_path = os.path.join(self.base_dir, filename)
        if os.path.exists(hooks_path):
            exec_file(hooks_path, self.hooks)

        if 'before_all' not in self.hooks:
            self.hooks['before_all'] = self.before_all_default_hook

    def load_step_definitions(self, extra_step_paths=[]):
        step_globals = {
            'use_step_matcher': matchers.use_step_matcher,
            'step_matcher':     matchers.step_matcher, # -- DEPRECATING
        }
        setup_step_decorators(step_globals)

        # -- Allow steps to import other stuff from the steps dir
        # NOTE: Default matcher can be overridden in "environment.py" hook.
        steps_dir = os.path.join(self.base_dir, 'steps')
        paths = [steps_dir] + list(extra_step_paths)
        with PathManager(paths):
            default_matcher = matchers.current_matcher
            for path in paths:
                for name in sorted(os.listdir(path)):
                    if name.endswith('.py'):
                        # -- LOAD STEP DEFINITION:
                        # Reset to default matcher after each step-definition.
                        # A step-definition may change the matcher 0..N times.
                        # ENSURE: Each step definition has clean globals.
                        step_module_globals = step_globals.copy()
                        exec_file(os.path.join(path, name), step_module_globals)
                        matchers.current_matcher = default_matcher

    def feature_locations(self):
        return collect_feature_locations(self.config.paths)


    def run(self):
        with self.path_manager:
            self.setup_paths()
            return self.run_with_paths()


    def run_with_paths(self):
        self.context = Context(self)
        self.load_hooks()
        self.load_step_definitions()

        # -- ENSURE: context.execute_steps() works in weird cases (hooks, ...)
        # self.setup_capture()
        # self.run_hook('before_all', self.context)

        # -- STEP: Parse all feature files (by using their file location).
        feature_locations = [ filename for filename in self.feature_locations()
                                    if not self.config.exclude(filename) ]
        features = parse_features(feature_locations, language=self.config.lang)
        self.features.extend(features)

        # -- STEP: Run all features.
        stream_openers = self.config.outputs
        self.formatters = formatters.get_formatter(self.config, stream_openers)
        return self.run_model()





########NEW FILE########
__FILENAME__ = runner_util
# -*- coding: utf-8 -*-
"""
Contains utility functions and classes for Runners.
"""

from behave import parser
from behave.model import FileLocation
from bisect import bisect
import glob
import os.path
import re
import sys
import types


# -----------------------------------------------------------------------------
# EXCEPTIONS:
# -----------------------------------------------------------------------------
class FileNotFoundError(LookupError):
    pass


class InvalidFileLocationError(LookupError):
    pass


class InvalidFilenameError(ValueError):
    pass


# -----------------------------------------------------------------------------
# CLASS: FileLocationParser
# -----------------------------------------------------------------------------
class FileLocationParser:
    # -- pylint: disable=W0232
    # W0232: 84,0:FileLocationParser: Class has no __init__ method
    pattern = re.compile(r"^\s*(?P<filename>.*):(?P<line>\d+)\s*$", re.UNICODE)

    @classmethod
    def parse(cls, text):
        match = cls.pattern.match(text)
        if match:
            filename = match.group("filename").strip()
            line = int(match.group("line"))
            return FileLocation(filename, line)
        else:
            # -- NORMAL PATH/FILENAME:
            filename = text.strip()
            return FileLocation(filename)

    # @classmethod
    # def compare(cls, location1, location2):
    #     loc1 = cls.parse(location1)
    #     loc2 = cls.parse(location2)
    #     return cmp(loc1, loc2)


# -----------------------------------------------------------------------------
# CLASSES:
# -----------------------------------------------------------------------------
class FeatureScenarioLocationCollector(object):
    """
    Collects FileLocation objects for a feature.
    This is used to select a subset of scenarios in a feature that should run.

    USE CASE:
        behave feature/foo.feature:10
        behave @selected_features.txt
        behave @rerun_failed_scenarios.txt

    With features configuration files, like:

        # -- file:rerun_failed_scenarios.txt
        feature/foo.feature:10
        feature/foo.feature:25
        feature/bar.feature
        # -- EOF

    """
    def __init__(self, feature=None, location=None, filename=None):
        if not filename and location:
            filename = location.filename
        self.feature = feature
        self.filename = filename
        self.use_all_scenarios = False
        self.scenario_lines = set()
        self.all_scenarios = set()
        self.selected_scenarios = set()
        if location:
            self.add_location(location)

    def clear(self):
        self.feature = None
        self.filename = None
        self.use_all_scenarios = False
        self.scenario_lines = set()
        self.all_scenarios = set()
        self.selected_scenarios = set()

    def add_location(self, location):
        if not self.filename:
            self.filename = location.filename
            # if self.feature and False:
            #     self.filename = self.feature.filename
        # -- NORMAL CASE:
        assert self.filename == location.filename, \
            "%s <=> %s" % (self.filename, location.filename)
        if location.line:
            self.scenario_lines.add(location.line)
        else:
            # -- LOCATION WITHOUT LINE NUMBER:
            # Selects all scenarios in a feature.
            self.use_all_scenarios = True

    @staticmethod
    def select_scenario_line_for(line, scenario_lines):
        """
        Select scenario line for any given line.

        ALGORITHM: scenario.line <= line < next_scenario.line

        :param line:  A line number in the file (as number).
        :param scenario_lines: Sorted list of scenario lines.
        :return: Scenario.line (first line) for the given line.
        """
        if not scenario_lines:
            return 0    # -- Select all scenarios.
        pos = bisect(scenario_lines, line) - 1
        if pos < 0:
            pos = 0
        return scenario_lines[pos]

    def discover_selected_scenarios(self, strict=False):
        """
        Discovers selected scenarios based on the provided file locations.
        In addition:
          * discover all scenarios
          * auto-correct BAD LINE-NUMBERS

        :param strict:  If true, raises exception if file location is invalid.
        :return: List of selected scenarios of this feature (as set).
        :raises InvalidFileLocationError:
            If file location is no exactly correct and strict is true.
        """
        assert self.feature
        if not self.all_scenarios:
            self.all_scenarios = self.feature.walk_scenarios()

        # -- STEP: Check if lines are correct.
        existing_lines = [scenario.line for scenario in self.all_scenarios]
        selected_lines = list(self.scenario_lines)
        for line in selected_lines:
            new_line = self.select_scenario_line_for(line, existing_lines)
            if new_line != line:
                # -- AUTO-CORRECT BAD-LINE:
                self.scenario_lines.remove(line)
                self.scenario_lines.add(new_line)
                if strict:
                    msg = "Scenario location '...:%d' should be: '%s:%d'" % \
                          (line, self.filename, new_line)
                    raise InvalidFileLocationError(msg)

        # -- STEP: Determine selected scenarios and store them.
        scenario_lines = set(self.scenario_lines)
        selected_scenarios = set()
        for scenario in self.all_scenarios:
            if scenario.line in scenario_lines:
                selected_scenarios.add(scenario)
                scenario_lines.remove(scenario.line)
        # -- CHECK ALL ARE RESOLVED:
        assert not scenario_lines
        return selected_scenarios

    def build_feature(self):
        """
        Determines which scenarios in the feature are selected and marks the
        remaining scenarios as skipped. Scenarios with the following tags
        are excluded from skipped-marking:

          * @setup
          * @teardown

        If no file locations are stored, the unmodified feature is returned.

        :return: Feature object to use.
        """
        use_all_scenarios = not self.scenario_lines or self.use_all_scenarios
        if not self.feature or use_all_scenarios:
            return self.feature

        # -- CASE: Select subset of all scenarios of this feature.
        #    Mark other scenarios as skipped (except in a few cases).
        self.all_scenarios = self.feature.walk_scenarios()
        self.selected_scenarios = self.discover_selected_scenarios()
        unselected_scenarios = set(self.all_scenarios) - self.selected_scenarios
        for scenario in unselected_scenarios:
            if "setup" in scenario.tags or "teardown" in scenario.tags:
                continue
            scenario.mark_skipped()
        return self.feature


class FeatureListParser(object):
    """
    Read textual file, ala '@features.txt'. This file contains:

      * a feature filename or FileLocation on each line
      * empty lines (skipped)
      * comment lines (skipped)
      * wildcards are expanded to select 0..N filenames or directories

    Relative path names are evaluated relative to the listfile directory.
    A leading '@' (AT) character is removed from the listfile name.
    """

    @staticmethod
    def parse(text, here=None):
        """
        Parse contents of a features list file as text.

        :param text: Contents of a features list(file).
        :param here: Current working directory to use (optional).
        :return: List of FileLocation objects
        """
        locations = []
        for line in text.splitlines():
            filename = line.strip()
            if not filename:
                continue    # SKIP: Over empty line(s).
            elif filename.startswith('#'):
                continue    # SKIP: Over comment line(s).

            if here and not os.path.isabs(filename):
                filename = os.path.join(here, line)
            filename = os.path.normpath(filename)
            if glob.has_magic(filename):
                # -- WITH WILDCARDS:
                for filename2 in glob.iglob(filename):
                    location = FileLocationParser.parse(filename2)
                    locations.append(location)
            else:
                location = FileLocationParser.parse(filename)
                locations.append(location)
        return locations

    @classmethod
    def parse_file(cls, filename):
        """
        Read textual file, ala '@features.txt'.

        :param filename:  Name of feature list file.
        :return: List of feature file locations.
        """
        if filename.startswith('@'):
            filename = filename[1:]
        if not os.path.isfile(filename):
            raise FileNotFoundError(filename)
        here = os.path.dirname(filename) or "."
        contents = open(filename).read()
        return cls.parse(contents, here)

# -----------------------------------------------------------------------------
# FUNCTIONS:
# -----------------------------------------------------------------------------
def parse_features(feature_files, language=None):
    """
    Parse feature files and return list of Feature model objects.
    Handles:

      * feature file names, ala "alice.feature"
      * feature file locations, ala: "alice.feature:10"

    :param feature_files: List of feature file names to parse.
    :param language:      Default language to use.
    :return: List of feature objects.
    """
    scenario_collector = FeatureScenarioLocationCollector()
    features = []
    for location in feature_files:
        if not isinstance(location, FileLocation):
            assert isinstance(location, basestring)
            location = FileLocation(os.path.normpath(location))

        if location.filename == scenario_collector.filename:
            scenario_collector.add_location(location)
            continue
        elif scenario_collector.feature:
            # -- ADD CURRENT FEATURE: As collection of scenarios.
            current_feature = scenario_collector.build_feature()
            features.append(current_feature)
            scenario_collector.clear()

        # -- NEW FEATURE:
        assert isinstance(location, FileLocation)
        filename = os.path.abspath(location.filename)
        feature = parser.parse_file(filename, language=language)
        if feature:
            # -- VALID FEATURE:
            # SKIP CORNER-CASE: Feature file without any feature(s).
            scenario_collector.feature = feature
            scenario_collector.add_location(location)
    # -- FINALLY:
    if scenario_collector.feature:
        current_feature = scenario_collector.build_feature()
        features.append(current_feature)
    return features


def collect_feature_locations(paths, strict=True):
    """
    Collect feature file names by processing list of paths (from command line).
    A path can be a:

      * filename (ending with ".feature")
      * location, ala "{filename}:{line_number}"
      * features configuration filename, ala "@features.txt"
      * directory, to discover and collect all "*.feature" files below.

    :param paths:  Paths to process.
    :return: Feature file locations to use (as list of FileLocations).
    """
    locations = []
    for path in paths:
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames.sort()
                for filename in sorted(filenames):
                    if filename.endswith(".feature"):
                        location = FileLocation(os.path.join(dirpath, filename))
                        locations.append(location)
        elif path.startswith('@'):
            # -- USE: behave @list_of_features.txt
            locations.extend(FeatureListParser.parse_file(path[1:]))
        else:
            # -- OTHERWISE: Normal filename or location (schema: filename:line)
            location = FileLocationParser.parse(path)
            if not location.filename.endswith(".feature"):
                raise InvalidFilenameError(location.filename)
            elif location.exists():
                locations.append(location)
            elif strict:
                raise FileNotFoundError(path)
    return locations


def make_undefined_step_snippet(step, language=None):
    """
    Helper function to create an undefined-step snippet for a step.

    :param step: Step to use (as Step object or step text).
    :param language: i18n language, optionally needed for step text parsing.
    :return: Undefined-step snippet (as string).
    """
    if isinstance(step, types.StringTypes):
        step_text = step
        steps = parser.parse_steps(step_text, language=language)
        step = steps[0]
        assert step, "ParseError: %s" % step_text
    prefix = u""
    if sys.version_info[0] == 2:
        prefix = u"u"
    single_quote = "'"
    if single_quote in step.name:
        step.name = step.name.replace(single_quote, r"\'")

    schema = u"@%s(%s'%s')\ndef step_impl(context):\n    assert False\n\n"
    snippet = schema % (step.step_type, prefix, step.name)
    return snippet


def print_undefined_step_snippets(undefined_steps, stream=None, colored=True):
    """
    Print snippets for the undefined steps that were discovered.

    :param undefined_steps:  List of undefined steps (as list<string>).
    :param stream:      Output stream to use (default: sys.stderr).
    :param colored:     Indicates if coloring should be used (default: True)
    """
    if not undefined_steps:
        return
    if not stream:
        stream = sys.stderr

    msg = u"\nYou can implement step definitions for undefined steps with "
    msg += u"these snippets:\n\n"
    printed = set()
    for step in undefined_steps:
        if step in printed:
            continue
        printed.add(step)
        msg += make_undefined_step_snippet(step)

    if colored:
        # -- OOPS: Unclear if stream supports ANSI coloring.
        from behave.formatter.ansi_escapes import escapes
        msg = escapes['undefined'] + msg + escapes['reset']
    stream.write(msg)
    stream.flush()

########NEW FILE########
__FILENAME__ = step_registry
# -*- coding: utf-8 -*-
"""
Provides a step registry and step decorators.
The step registry allows to match steps (model elements) with
step implementations (step definitions). This is necessary to execute steps.
"""


class AmbiguousStep(ValueError):
    pass


class StepRegistry(object):
    def __init__(self):
        self.steps = {
            'given': [],
            'when': [],
            'then': [],
            'step': [],
        }

    @staticmethod
    def same_step_definition(step, other_string, other_location):
        return (step.string == other_string and
                step.location == other_location and
                other_location.filename != "<string>")

    def add_step_definition(self, keyword, string, func):
        # TODO try to fix module dependencies to avoid this
        from behave import matchers, model
        step_location = model.Match.make_location(func)
        step_type = keyword.lower()
        step_definitions = self.steps[step_type]
        for existing in step_definitions:
            if self.same_step_definition(existing, string, step_location):
                # -- EXACT-STEP: Same step function is already registered.
                # This may occur when a step module imports another one.
                return
            elif existing.match(string):
                message = '%s has already been defined in\n  existing step %s'
                new_step = u"@%s('%s')" % (step_type, string)
                existing.step_type = step_type
                existing_step = existing.describe()
                existing_step += " at %s" % existing.location
                raise AmbiguousStep(message % (new_step, existing_step))
        step_definitions.append(matchers.get_matcher(func, string))

    def find_step_definition(self, step):
        candidates = self.steps[step.step_type]
        more_steps = self.steps['step']
        if step.step_type != 'step' and more_steps:
            # -- ENSURE: self.step_type lists are not modified/extended.
            candidates = list(candidates)
            candidates += more_steps

        for step_definition in candidates:
            if step_definition.match(step.name):
                return step_definition
        return None

    def find_match(self, step):
        candidates = self.steps[step.step_type]
        more_steps = self.steps['step']
        if step.step_type != 'step' and more_steps:
            # -- ENSURE: self.step_type lists are not modified/extended.
            candidates = list(candidates)
            candidates += more_steps

        for step_definition in candidates:
            result = step_definition.match(step.name)
            if result:
                return result

        return None

    def make_decorator(self, step_type):
        # pylint: disable=W0621
        #   W0621: 44,29:StepRegistry.make_decorator: Redefining 'step_type' ..
        def decorator(string):
            def wrapper(func):
                self.add_step_definition(step_type, string, func)
                return func
            return wrapper
        return decorator


registry = StepRegistry()

# -- Create the decorators
def setup_step_decorators(context=None, registry=registry):
    if context is None:
        context = globals()
    for step_type in ('given', 'when', 'then', 'step'):
        step_decorator = registry.make_decorator(step_type)
        context[step_type.title()] = context[step_type] = step_decorator

# -----------------------------------------------------------------------------
# MODULE INIT:
# -----------------------------------------------------------------------------
# limit import * to just the decorators
names = 'given when then step'
names = names + ' ' + names.title()
__all__ = names.split()

setup_step_decorators()

########NEW FILE########
__FILENAME__ = tag_expression
# -*- coding: utf-8 -*-

class TagExpression(object):
    """
    Tag expression, as logical boolean expression, to select
    (include or exclude) model elements.

    BOOLEAN LOGIC := (or_expr1) and (or_expr2) and ...
    with or_exprN := [not] tag1 or [not] tag2 or ...
    """

    def __init__(self, tag_expressions):
        self.ands = []
        self.limits = {}

        for expr in tag_expressions:
            self.store_and_extract_limits(self.normalized_tags_from_or(expr))

    @staticmethod
    def normalize_tag(tag):
        """
        Normalize a tag for a tag expression:

          * strip whitespace
          * strip '@' char
          * convert '~' (tilde) into '-' (minus sign)

        :param tag:  Tag (as string).
        :return: Normalized tag (as string).
        """
        tag = tag.strip()
        if tag.startswith('@'):
            tag = tag[1:]
        elif tag.startswith('-@') or tag.startswith('~@'):
            tag = '-' + tag[2:]
        elif tag.startswith('~'):
            tag = '-' + tag[1:]
        return tag

    @classmethod
    def normalized_tags_from_or(cls, expr):
        """
        Normalizes all tags in an OR expression (and return it as list).

        :param expr:  OR expression to normalize and split (as string).
        :return: Generator of normalized tags (as string)
        """
        for tag in expr.strip().split(','):
            yield cls.normalize_tag(tag)

    def store_and_extract_limits(self, tags):
        tags_with_negation = []

        for tag in tags:
            negated = tag.startswith('-')
            tag = tag.split(':')
            tag_with_negation = tag.pop(0)
            tags_with_negation.append(tag_with_negation)

            if tag:
                limit = int(tag[0])
                if negated:
                    tag_without_negation = tag_with_negation[1:]
                else:
                    tag_without_negation = tag_with_negation
                limited = tag_without_negation in self.limits
                if limited and self.limits[tag_without_negation] != limit:
                    msg = "Inconsistent tag limits for {0}: {1:d} and {2:d}"
                    msg = msg.format(tag_without_negation,
                                     self.limits[tag_without_negation], limit)
                    raise Exception(msg)
                self.limits[tag_without_negation] = limit

        if tags_with_negation:
            self.ands.append(tags_with_negation)

    def check(self, tags):
        """
        Checks if this tag expression matches the tags of a model element.

        :param tags:  List of tags of a model element.
        :return: True, if tag expression matches. False, otherwise.
        """
        if not self.ands:
            return True

        element_tags = set(tags)

        def test_tag(xtag):
            if xtag.startswith('-'): # -- or xtag.startswith('~'):
                return xtag[1:] not in element_tags
            return xtag in element_tags

        # -- EVALUATE: (or_expr1) and (or_expr2) and ...
        return all(any(test_tag(xtag) for xtag in ors)  for ors in self.ands)

    def __len__(self):
        return len(self.ands)

    def __str__(self):
        """Conversion back into string that represents this tag expression."""
        and_parts = []
        for or_terms in self.ands:
            and_parts.append(",".join(or_terms))
        return " ".join(and_parts)

########NEW FILE########
__FILENAME__ = textutil
# -*- coding: utf-8 -*-
"""
Provides some utility functions related to text processing.
"""


def make_indentation(indent_size, part=u" "):
    """
    Creates an indentation prefix string of the given size.
    """
    return indent_size * part


def indent(text, prefix):
    """
    Indent text or a number of text lines (with newline).

    :param lines:  Text lines to indent (as string or list of strings).
    :param prefix: Line prefix to use (as string).
    :return: Indented text (as unicode string).
    """
    lines = text
    newline = u""
    if isinstance(text, basestring):
        lines = text.splitlines(True)
    elif lines and not lines[0].endswith("\n"):
        # -- TEXT LINES: Without trailing new-line.
        newline = u"\n"
    return newline.join([prefix + unicode(line) for line in lines])


def compute_words_maxsize(words):
    """
    Compute the maximum word size from a list of words (or strings).

    :param words: List of words (or strings) to use.
    :return: Maximum size of all words.
    """
    max_size = 0
    for word in words:
        if len(word) > max_size:
            max_size = len(word)
    return max_size

########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf-8 -*-

import sys

from behave import __version__
from behave.configuration import Configuration, ConfigError
from behave.runner import Runner
from behave.runner_util import print_undefined_step_snippets, \
    InvalidFileLocationError, InvalidFilenameError, FileNotFoundError
from behave.parser import ParserError

TAG_HELP = """
Scenarios inherit tags declared on the Feature level. The simplest
TAG_EXPRESSION is simply a tag::

    --tags @dev

You may even leave off the "@" - behave doesn't mind.

When a tag in a tag expression starts with a ~, this represents boolean NOT::

    --tags ~@dev

A tag expression can have several tags separated by a comma, which represents
logical OR::

    --tags @dev,@wip

The --tags option can be specified several times, and this represents logical
AND, for instance this represents the boolean expression
"(@foo or not @bar) and @zap"::

    --tags @foo,~@bar --tags @zap.

Beware that if you want to use several negative tags to exclude several tags
you have to use logical AND::

    --tags ~@fixme --tags ~@buggy.
""".strip()

# TODO
# Positive tags can be given a threshold to limit the number of occurrences.
# Which can be practical if you are practicing Kanban or CONWIP. This will fail
# if there are more than 3 occurrences of the @qa tag:
#
# --tags @qa:3
# """.strip()


def main(args=None):
    config = Configuration(args)
    if config.version:
        print "behave " + __version__
        return 0

    if config.tags_help:
        print TAG_HELP
        return 0

    if config.lang_list:
        from behave.i18n import languages
        iso_codes = languages.keys()
        iso_codes.sort()
        print "Languages available:"
        for iso_code in iso_codes:
            native = languages[iso_code]['native'][0]
            name = languages[iso_code]['name'][0]
            print u'%s: %s / %s' % (iso_code, native, name)
        return 0

    if config.lang_help:
        from behave.i18n import languages
        if config.lang_help not in languages:
            print '%s is not a recognised language: try --lang-list' % \
                    config.lang_help
            return 1
        trans = languages[config.lang_help]
        print u"Translations for %s / %s" % (trans['name'][0],
              trans['native'][0])
        for kw in trans:
            if kw in 'name native'.split():
                continue
            print u'%16s: %s' % (kw.title().replace('_', ' '),
                  u', '.join(w for w in trans[kw] if w != '*'))
        return 0

    if not config.format:
        config.format = [ config.default_format ]
    elif config.format and "format" in config.defaults:
        # -- CASE: Formatter are specified in behave configuration file.
        #    Check if formatter are provided on command-line, too.
        if len(config.format) == len(config.defaults["format"]):
            # -- NO FORMATTER on command-line: Add default formatter.
            config.format.append(config.default_format)
    if 'help' in config.format:
        from behave.formatter import formatters
        print "Available formatters:"
        formatters.list_formatters(sys.stdout)
        return 0

    if len(config.outputs) > len(config.format):
        print 'CONFIG-ERROR: More outfiles (%d) than formatters (%d).' % \
              (len(config.outputs), len(config.format))
        return 1

    failed = True
    runner = Runner(config)
    try:
        failed = runner.run()
    except ParserError, e:
        print "ParseError: %s" % e
    except ConfigError, e:
        print "ConfigError: %s" % e
    except FileNotFoundError, e:
        print "FileNotFoundError: %s" % e
    except InvalidFileLocationError, e:
        print "InvalidFileLocationError: %s" % e
    except InvalidFilenameError, e:
        print "InvalidFilenameError: %s" % e

    if config.show_snippets and runner.undefined_steps:
        print_undefined_step_snippets(runner.undefined_steps,
                                      colored=config.color)

    return_code = 0
    if failed:
        return_code = 1
    return return_code

if __name__ == '__main__':
    # -- EXAMPLE: main("--version")
    sys.exit(main())

########NEW FILE########
__FILENAME__ = command_shell
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provide a behave shell to simplify creation of feature files
and running features, etc.

    context.command_result = behave_shell.behave(cmdline, cwd=context.workdir)
    behave_shell.create_scenario(scenario_text, cwd=context.workdir)
    behave_shell.create_step_definition(context.text, cwd=context.workdir)
    context.command_result = behave_shell.run_feature_with_formatter(
            context.features[0], formatter=formatter, cwd=context.workdir)

"""

from __future__ import print_function, with_statement
from behave4cmd0.__setup import TOP
import os.path
import six
import subprocess
import sys
import shlex
import codecs

# HERE = os.path.dirname(__file__)
# TOP  = os.path.join(HERE, "..")

# -----------------------------------------------------------------------------
# CLASSES:
# -----------------------------------------------------------------------------
class CommandResult(object):
    """
    ValueObject to store the results of a subprocess command call.
    """
    def __init__(self, **kwargs):
        self.command = kwargs.pop("command", None)
        self.returncode = kwargs.pop("returncode", 0)
        self.stdout = kwargs.pop("stdout", "")
        self.stderr = kwargs.pop("stderr", "")
        self._output = None
        if kwargs:
            names = ", ".join(kwargs.keys())
            raise ValueError("Unexpected: %s" % names)

    @property
    def output(self):
        if self._output is None:
            output = self.stdout
            if self.stderr:
                output += "\n"
                output += self.stderr
            self._output = output
        return self._output

    @property
    def failed(self):
        return not self.returncode

    def clear(self):
        self.command = None
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""
        self._output = None


class Command(object):
    """
    Helper class to run commands as subprocess,
    collect their output and subprocess returncode.
    """
    DEBUG = False
    COMMAND_MAP = {
        "behave": os.path.normpath("{0}/bin/behave".format(TOP))
    }

    @classmethod
    def run(cls, command, cwd=".", **kwargs):
        """
        Make a subprocess call, collect its output and returncode.
        Returns CommandResult instance as ValueObject.
        """
        assert isinstance(command, basestring)
        command_result = CommandResult()
        command_result.command = command

        # -- BUILD COMMAND ARGS:
        if isinstance(command, unicode):
            command = codecs.encode(command)
        cmdargs = shlex.split(command)

        # -- TRANSFORM COMMAND (optional)
        real_command = cls.COMMAND_MAP.get(cmdargs[0], None)
        if real_command:
            cmdargs[0] = real_command

        # -- RUN COMMAND:
        try:
            process = subprocess.Popen(cmdargs,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            cwd=cwd, **kwargs)
            out, err = process.communicate()
            # XXX-JE-OLD: if sys.version_info[0] < 3: # py3: we get unicode strings, py2 not
            if six.PY2: # py3: we get unicode strings, py2 not
                # XXX-DISABLED:
                # try:
                #    # jython may not have it
                #     default_encoding = sys.getdefaultencoding()
                # except AttributeError:
                #     default_encoding = sys.stdout.encoding or 'UTF-8'
                default_encoding = 'UTF-8'
                # XXX-JE-OLD: out = unicode(out, process.stdout.encoding or default_encoding)
                # XXX-JE-OLD: err = unicode(err, process.stderr.encoding or default_encoding)
                out = six.text_type(out, process.stdout.encoding or default_encoding)
                err = six.text_type(err, process.stderr.encoding or default_encoding)
            process.poll()
            assert process.returncode is not None
            command_result.stdout = out
            command_result.stderr = err
            command_result.returncode = process.returncode
            if cls.DEBUG:
                print("shell.cwd={0}".format(kwargs.get("cwd", None)))
                print("shell.command: {0}".format(" ".join(cmdargs)))
                print("shell.command.output:\n{0};".format(command_result.output))
        except OSError, e:
            command_result.stderr = u"OSError: %s" % e
            command_result.returncode = e.errno
            assert e.errno != 0
        return command_result



# -----------------------------------------------------------------------------
# FUNCTIONS:
# -----------------------------------------------------------------------------
def run(command, cwd=".", **kwargs):
    return Command.run(command, cwd=cwd, **kwargs)

def behave(cmdline, cwd=".", **kwargs):
    """
    Run behave as subprocess command and return process/shell instance
    with results (collected output, returncode).
    """
    assert isinstance(cmdline, basestring)
    return run("behave " + cmdline, cwd=cwd, **kwargs)

# -----------------------------------------------------------------------------
# TEST MAIN:
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    command = " ".join(sys.argv[1:])
    output = Command.run(sys.argv[1:])
    print("command: {0}\n{1}\n".format(command, output))

########NEW FILE########
__FILENAME__ = command_steps
# -*- coding -*-
"""
Provides step definitions to:

    * run commands, like behave
    * create textual files within a working directory

TODO:
  matcher that ignores empty lines and whitespace and has contains comparison
"""

from __future__ import print_function
from behave import given, when, then, step, matchers
from behave4cmd0 import command_shell, command_util, pathutil, textutil
from behave4cmd0.pathutil import posixpath_normpath
import os
import shutil
from hamcrest import assert_that, equal_to, is_not, contains_string

# -----------------------------------------------------------------------------
# INIT:
# -----------------------------------------------------------------------------
matchers.register_type(int=int)
DEBUG = True


# -----------------------------------------------------------------------------
# STEPS: WORKING DIR
# -----------------------------------------------------------------------------
@given(u'a new working directory')
def step_a_new_working_directory(context):
    """
    Creates a new, empty working directory
    """
    command_util.ensure_context_attribute_exists(context, "workdir", None)
    command_util.ensure_workdir_exists(context)
    shutil.rmtree(context.workdir, ignore_errors=True)

@given(u'I use the current directory as working directory')
def step_use_curdir_as_working_directory(context):
    """
    Uses the current directory as working directory
    """
    context.workdir = os.path.abspath(".")
    command_util.ensure_workdir_exists(context)

# -----------------------------------------------------------------------------
# STEPS: Create files with contents
# -----------------------------------------------------------------------------
@given(u'a file named "{filename}" with')
def step_a_file_named_filename_with(context, filename):
    """
    Creates a textual file with the content provided as docstring.
    """
    assert context.text is not None, "ENSURE: multiline text is provided."
    assert not os.path.isabs(filename)
    command_util.ensure_workdir_exists(context)
    filename2 = os.path.join(context.workdir, filename)
    pathutil.create_textfile_with_contents(filename2, context.text)

    # -- SPECIAL CASE: For usage with behave steps.
    if filename.endswith(".feature"):
        command_util.ensure_context_attribute_exists(context, "features", [])
        context.features.append(filename)

@given(u'an empty file named "{filename}"')
def step_an_empty_file_named_filename(context, filename):
    """
    Creates an empty file.
    """
    assert not os.path.isabs(filename)
    command_util.ensure_workdir_exists(context)
    filename2 = os.path.join(context.workdir, filename)
    pathutil.create_textfile_with_contents(filename2, "")


# -----------------------------------------------------------------------------
# STEPS: Run commands
# -----------------------------------------------------------------------------
@when(u'I run "{command}"')
def step_i_run_command(context, command):
    """
    Run a command as subprocess, collect its output and returncode.
    """
    command_util.ensure_workdir_exists(context)
    context.command_result = command_shell.run(command, cwd=context.workdir)
    command_util.workdir_save_coverage_files(context.workdir)
    if False and DEBUG:
        print(u"XXX run_command: {0}".format(command))
        print(u"XXX run_command.outout {0}".format(context.command_result.output))


@then(u'it should fail with result "{result:int}"')
def step_it_should_fail_with_result(context, result):
    assert_that(context.command_result.returncode, equal_to(result))
    assert_that(result, is_not(equal_to(0)))

@then(u'the command should fail with returncode="{result:int}"')
def step_it_should_fail_with_returncode(context, result):
    assert_that(context.command_result.returncode, equal_to(result))
    assert_that(result, is_not(equal_to(0)))

@then(u'the command returncode is "{result:int}"')
def step_the_command_returncode_is(context, result):
    assert_that(context.command_result.returncode, equal_to(result))

@then(u'the command returncode is non-zero')
def step_the_command_returncode_is_nonzero(context):
    assert_that(context.command_result.returncode, is_not(equal_to(0)))

@then(u'it should pass')
def step_it_should_pass(context):
    assert_that(context.command_result.returncode, equal_to(0))

@then(u'it should fail')
def step_it_should_fail(context):
    assert_that(context.command_result.returncode, is_not(equal_to(0)))

@then(u'it should pass with')
def step_it_should_pass_with(context):
    '''
    EXAMPLE:
        ...
        when I run "behave ..."
        then it should pass with:
            """
            TEXT
            """
    '''
    assert context.text is not None, "ENSURE: multiline text is provided."
    step_command_output_should_contain(context)
    assert_that(context.command_result.returncode, equal_to(0))


@then(u'it should fail with')
def step_it_should_fail_with(context):
    '''
    EXAMPLE:
        ...
        when I run "behave ..."
        then it should fail with:
            """
            TEXT
            """
    '''
    assert context.text is not None, "ENSURE: multiline text is provided."
    step_command_output_should_contain(context)
    assert_that(context.command_result.returncode, is_not(equal_to(0)))


# -----------------------------------------------------------------------------
# STEPS FOR: Output Comparison
# -----------------------------------------------------------------------------
@then(u'the command output should contain "{text}"')
def step_command_output_should_contain_text(context, text):
    '''
    EXAMPLE:
        ...
        Then the command output should contain "TEXT"
    '''
    expected_text = text
    if "{__WORKDIR__}" in expected_text or "{__CWD__}" in expected_text:
        expected_text = textutil.template_substitute(text,
             __WORKDIR__ = posixpath_normpath(context.workdir),
             __CWD__     = posixpath_normpath(os.getcwd())
        )
    actual_output = context.command_result.output
    if DEBUG:
        print(u"expected:\n{0}".format(expected_text))
        print(u"actual:\n{0}".format(actual_output))
    textutil.assert_normtext_should_contain(actual_output, expected_text)


@then(u'the command output should not contain "{text}"')
def step_command_output_should_not_contain_text(context, text):
    '''
    EXAMPLE:
        ...
        then the command output should not contain "TEXT"
    '''
    expected_text = text
    if "{__WORKDIR__}" in text or "{__CWD__}" in text:
        expected_text = textutil.template_substitute(text,
             __WORKDIR__ = posixpath_normpath(context.workdir),
             __CWD__     = posixpath_normpath(os.getcwd())
        )
    actual_output  = context.command_result.output
    if DEBUG:
        print(u"expected:\n{0}".format(expected_text))
        print(u"actual:\n{0}".format(actual_output))
    textutil.assert_normtext_should_not_contain(actual_output, expected_text)


@then(u'the command output should contain exactly "{text}"')
def step_command_output_should_contain_exactly_text(context, text):
    """
    Verifies that the command output of the last command contains the
    expected text.

    .. code-block:: gherkin

        When I run "echo Hello"
        Then the command output should contain "Hello"
    """
    expected_text = text
    if "{__WORKDIR__}" in text or "{__CWD__}" in text:
        expected_text = textutil.template_substitute(text,
             __WORKDIR__ = posixpath_normpath(context.workdir),
             __CWD__     = posixpath_normpath(os.getcwd())
        )
    actual_output  = context.command_result.output
    textutil.assert_text_should_contain_exactly(actual_output, expected_text)


@then(u'the command output should not contain exactly "{text}"')
def step_command_output_should_not_contain_exactly_text(context, text):
    expected_text = text
    if "{__WORKDIR__}" in text or "{__CWD__}" in text:
        expected_text = textutil.template_substitute(text,
             __WORKDIR__ = posixpath_normpath(context.workdir),
             __CWD__     = posixpath_normpath(os.getcwd())
        )
    actual_output  = context.command_result.output
    textutil.assert_text_should_not_contain_exactly(actual_output, expected_text)


@then(u'the command output should contain')
def step_command_output_should_contain(context):
    '''
    EXAMPLE:
        ...
        when I run "behave ..."
        then it should pass
        and  the command output should contain:
            """
            TEXT
            """
    '''
    assert context.text is not None, "REQUIRE: multi-line text"
    step_command_output_should_contain_text(context, context.text)


@then(u'the command output should not contain')
def step_command_output_should_not_contain(context):
    '''
    EXAMPLE:
        ...
        when I run "behave ..."
        then it should pass
        and  the command output should not contain:
            """
            TEXT
            """
    '''
    assert context.text is not None, "REQUIRE: multi-line text"
    step_command_output_should_not_contain_text(context, context.text.strip())


@then(u'the command output should contain exactly')
def step_command_output_should_contain_exactly_with_multiline_text(context):
    assert context.text is not None, "REQUIRE: multi-line text"
    step_command_output_should_contain_exactly_text(context, context.text)


@then(u'the command output should not contain exactly')
def step_command_output_should_contain_not_exactly_with_multiline_text(context):
    assert context.text is not None, "REQUIRE: multi-line text"
    step_command_output_should_not_contain_exactly_text(context, context.text)


# -----------------------------------------------------------------------------
# STEPS FOR: Directories
# -----------------------------------------------------------------------------
@step(u'I remove the directory "{directory}"')
def step_remove_directory(context, directory):
    path_ = directory
    if not os.path.isabs(directory):
        path_ = os.path.join(context.workdir, os.path.normpath(directory))
    if os.path.isdir(path_):
        shutil.rmtree(path_, ignore_errors=True)
    assert_that(not os.path.isdir(path_))

@given(u'I ensure that the directory "{directory}" does not exist')
def step_given_the_directory_should_not_exist(context, directory):
    step_remove_directory(context, directory)

@given(u'a directory named "{path}"')
def step_directory_named_dirname(context, path):
    assert context.workdir, "REQUIRE: context.workdir"
    path_ = os.path.join(context.workdir, os.path.normpath(path))
    if not os.path.exists(path_):
        os.makedirs(path_)
    assert os.path.isdir(path_)

@then(u'the directory "{directory}" should exist')
def step_the_directory_should_exist(context, directory):
    path_ = directory
    if not os.path.isabs(directory):
        path_ = os.path.join(context.workdir, os.path.normpath(directory))
    assert_that(os.path.isdir(path_))

@then(u'the directory "{directory}" should not exist')
def step_the_directory_should_not_exist(context, directory):
    path_ = directory
    if not os.path.isabs(directory):
        path_ = os.path.join(context.workdir, os.path.normpath(directory))
    assert_that(not os.path.isdir(path_))

@step(u'the directory "{directory}" exists')
def step_directory_exists(context, directory):
    """
    Verifies that a directory exists.

    .. code-block:: gherkin

        Given the directory "abc.txt" exists
         When the directory "abc.txt" exists
    """
    step_the_directory_should_exist(context, directory)

@step(u'the directory "{directory}" does not exist')
def step_directory_named_does_not_exist(context, directory):
    """
    Verifies that a directory does not exist.

    .. code-block:: gherkin

        Given the directory "abc/" does not exist
         When the directory "abc/" does not exist
    """
    step_the_directory_should_not_exist(context, directory)

# -----------------------------------------------------------------------------
# FILE STEPS:
# -----------------------------------------------------------------------------
@step(u'a file named "{filename}" exists')
def step_file_named_filename_exists(context, filename):
    """
    Verifies that a file with this filename exists.

    .. code-block:: gherkin

        Given a file named "abc.txt" exists
         When a file named "abc.txt" exists
    """
    step_file_named_filename_should_exist(context, filename)

@step(u'a file named "{filename}" does not exist')
def step_file_named_filename_does_not_exist(context, filename):
    """
    Verifies that a file with this filename does not exist.

    .. code-block:: gherkin

        Given a file named "abc.txt" does not exist
         When a file named "abc.txt" does not exist
    """
    step_file_named_filename_should_not_exist(context, filename)

@then(u'a file named "{filename}" should exist')
def step_file_named_filename_should_exist(context, filename):
    command_util.ensure_workdir_exists(context)
    filename_ = pathutil.realpath_with_context(filename, context)
    assert_that(os.path.exists(filename_) and os.path.isfile(filename_))

@then(u'a file named "{filename}" should not exist')
def step_file_named_filename_should_not_exist(context, filename):
    command_util.ensure_workdir_exists(context)
    filename_ = pathutil.realpath_with_context(filename, context)
    assert_that(not os.path.exists(filename_))

# -----------------------------------------------------------------------------
# STEPS FOR FILE CONTENTS:
# -----------------------------------------------------------------------------
@then(u'the file "{filename}" should contain "{text}"')
def step_file_should_contain_text(context, filename, text):
    expected_text = text
    if "{__WORKDIR__}" in text or "{__CWD__}" in text:
        expected_text = textutil.template_substitute(text,
            __WORKDIR__ = posixpath_normpath(context.workdir),
            __CWD__     = posixpath_normpath(os.getcwd())
        )
    file_contents = pathutil.read_file_contents(filename, context=context)
    file_contents = file_contents.rstrip()
    if DEBUG:
        print(u"expected:\n{0}".format(expected_text))
        print(u"actual:\n{0}".format(file_contents))
    textutil.assert_normtext_should_contain(file_contents, expected_text)


@then(u'the file "{filename}" should not contain "{text}"')
def step_file_should_not_contain_text(context, filename, text):
    file_contents = pathutil.read_file_contents(filename, context=context)
    file_contents = file_contents.rstrip()
    textutil.assert_normtext_should_not_contain(file_contents, text)
    # XXX assert_that(file_contents, is_not(contains_string(text)))


@then(u'the file "{filename}" should contain')
def step_file_should_contain_multiline_text(context, filename):
    assert context.text is not None, "REQUIRE: multiline text"
    step_file_should_contain_text(context, filename, context.text)


@then(u'the file "{filename}" should not contain')
def step_file_should_not_contain_multiline_text(context, filename):
    assert context.text is not None, "REQUIRE: multiline text"
    step_file_should_not_contain_text(context, filename, context.text)


# -----------------------------------------------------------------------------
# ENVIRONMENT VARIABLES
# -----------------------------------------------------------------------------
@step(u'I set the environment variable "{env_name}" to "{env_value}"')
def step_I_set_the_environment_variable_to(context, env_name, env_value):
    if not hasattr(context, "environ"):
        context.environ = {}
    context.environ[env_name] = env_value
    os.environ[env_name] = env_value

@step(u'I remove the environment variable {env_name}')
def step_I_remove_the_environment_variable(context, env_name):
    if not hasattr(context, "environ"):
        context.environ = {}
    context.environ[env_name] = ""
    os.environ[env_name] = ""
    del context.environ[env_name]
    del os.environ[env_name]


########NEW FILE########
__FILENAME__ = command_util
# -*- coding -*-
"""
Provides some command utility functions.

TODO:
  matcher that ignores empty lines and whitespace and has contains comparison
"""

from behave4cmd0 import pathutil
from behave4cmd0.__setup import TOP, TOPA
import os.path
import shutil
from fnmatch import fnmatch

# -----------------------------------------------------------------------------
# CONSTANTS:
# -----------------------------------------------------------------------------
# HERE    = os.path.dirname(__file__)
# TOP     = os.path.join(HERE, "..")
# TOPA    = os.path.abspath(TOP)
WORKDIR = os.path.join(TOP, "__WORKDIR__")


# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS:
# -----------------------------------------------------------------------------
def workdir_save_coverage_files(workdir, destdir=None):
    assert os.path.isdir(workdir)
    if not destdir:
        destdir = TOPA
    if os.path.abspath(workdir) == os.path.abspath(destdir):
        return  # -- SKIP: Source directory is destination directory (SAME).

    for fname in os.listdir(workdir):
        if fnmatch(fname, ".coverage.*"):
            # -- MOVE COVERAGE FILES:
            sourcename = os.path.join(workdir, fname)
            shutil.move(sourcename, destdir)

# def ensure_directory_exists(dirname):
#     """
#     Ensures that a directory exits.
#     If it does not exist, it is automatically created.
#     """
#     if not os.path.exists(dirname):
#         os.makedirs(dirname)
#     assert os.path.exists(dirname)
#     assert os.path.isdir(dirname)

def ensure_context_attribute_exists(context, name, default_value=None):
    """
    Ensure a behave resource exists as attribute in the behave context.
    If this is not the case, the attribute is created by using the default_value.
    """
    if not hasattr(context, name):
        setattr(context, name, default_value)

def ensure_workdir_exists(context):
    """
    Ensures that the work directory exists.
    In addition, the location of the workdir is stored as attribute in
    the context object.
    """
    ensure_context_attribute_exists(context, "workdir", None)
    if not context.workdir:
        context.workdir = os.path.abspath(WORKDIR)
    pathutil.ensure_directory_exists(context.workdir)


# def create_textfile_with_contents(filename, contents):
#     """
#     Creates a textual file with the provided contents in the workdir.
#     Overwrites an existing file.
#     """
#     ensure_directory_exists(os.path.dirname(filename))
#     if os.path.exists(filename):
#         os.remove(filename)
#     outstream = open(filename, "w")
#     outstream.write(contents)
#     if not contents.endswith("\n"):
#         outstream.write("\n")
#     outstream.flush()
#     outstream.close()
#     assert os.path.exists(filename)

# def text_remove_empty_lines(text):
#     """
#     Whitespace normalization:
#       - Strip empty lines
#       - Strip trailing whitespace
#     """
#     lines = [ line.rstrip()  for line in text.splitlines()  if line.strip() ]
#     return "\n".join(lines)
#
# def text_normalize(text):
#     """
#     Whitespace normalization:
#       - Strip empty lines
#       - Strip leading whitespace  in a line
#       - Strip trailing whitespace in a line
#       - Normalize line endings
#     """
#     lines = [ line.strip()  for line in text.splitlines()  if line.strip() ]
#     return "\n".join(lines)

# def posixpath_normpath(pathname):
#     """
#     Convert path into POSIX path:
#       - Normalize path
#       - Replace backslash with slash
#     """
#     backslash = '\\'
#     pathname = os.path.normpath(pathname)
#     if backslash in pathname:
#         pathname = pathname.replace(backslash, '/')
#     return pathname

########NEW FILE########
__FILENAME__ = failing_steps
# -*- coding: utf-8 -*-
"""
Generic failing steps.
Often needed in examples.

EXAMPLES:

    Given a step fails
    When  another step fails
    Then  a step fails

    Given ...
    When  ...
    Then  it should fail because "the person is unknown".
"""

from behave import step, then

# -----------------------------------------------------------------------------
# STEPS FOR: failing
# -----------------------------------------------------------------------------
@step('{word:w} step fails')
def step_fails(context, word):
    """
    Step that always fails, mostly needed in examples.
    """
    assert False, "EXPECT: Failing step"

@then(u'it should fail because "{reason}"')
def then_it_should_fail_because(context, reason):
    """
    Self documenting step that indicates why this step should fail.
    """
    assert False, "FAILED: %s" % reason

# @step(u'an error should fail because "{reason}"')
# def then_it_should_fail_because(context, reason):
#     """
#    Self documenting step that indicates why this step should fail.
#    """
#    assert False, reason
########NEW FILE########
__FILENAME__ = steps
# -*- coding: utf-8 -*-
"""
Provides step definitions to perform tests with the Python logging subsystem.

.. code-block: gherkin

    Given I create log records with:
        | category | level   | message |
        | foo.bar  | WARN    | Hello LogRecord |
        | bar      | CURRENT | Hello LogRecord |
    And I create a log record with:
        | category | level   | message |
        | foo      | ERROR   | Hello Foo |
    Then the command output should contain the following log records:
        | category | level   | message |
        | bar      | CURRENT | xxx     |
    Then the command output should not contain the following log records:
        | category | level   | message |
        | bar      | CURRENT | xxx     |
    Then the file "behave.log" should contain the log records:
        | category | level   | message |
        | bar      | CURRENT | xxx     |
    Then the file "behave.log" should not contain the log records:
        | category | level   | message |
        | bar      | CURRENT | xxx     |

    Given I define the log record schema:
        | category | level   | message |
        | root     | INFO    | Hello LogRecord |
    And I create log records with:
        | category | level   | message |
        | foo.bar  | INFO    | Hello LogRecord |
        | bar      | INFO    | Hello LogRecord |
    Then the command output should contain log records from categories
        | category |
        | foo.bar  |
        | bar      |

    Given I use the log record configuration:
        | property | value |
        | format   | LOG.%(levelname)-8s %(name)s %(message)s |
        | datefmt  |       |

IDEA:

.. code-block:: gherkin

    Given I capture log records
    When I create log records with:
        | category | level   | message |
        | foo.bar  | WARN    | Hello LogRecord |
    Then the captured log should contain the following log records:
        | category | level   | message |
        | bar      | CURRENT | xxx     |
    And the captured log should not contain the following log records:
        | category | level   | message |
        | bar      | CURRENT | xxx     |
"""

from behave import given, when, then, step
from behave4cmd0.command_steps import \
    step_file_should_contain_multiline_text, \
    step_file_should_not_contain_multiline_text
from behave.configuration import LogLevel
from behave.log_capture import LoggingCapture
import logging

# -----------------------------------------------------------------------------
# STEP UTILS:
# -----------------------------------------------------------------------------
def make_log_record(category, level, message):
    if category in ("root", "__ROOT__"):
        category = None
    logger = logging.getLogger(category)
    logger.log(level, message)

def make_log_record_output(category, level, message,
                           format=None, datefmt=None, **kwargs):
    """
    Create the output for a log record, like performed by :mod:`logging` module.

    :param category:    Name of the logger (as string or None).
    :param level:       Log level (as number).
    :param message:     Log message to use.
    :returns: Log record output (as string)
    """
    if not category or (category == "__ROOT__"):
        category = "root"
    levelname = logging.getLevelName(level)
    record_data = dict(name=category, levelname=levelname, msg=message)
    record_data.update(kwargs)
    record = logging.makeLogRecord(record_data)
    formatter = logging.Formatter(format, datefmt=datefmt)
    return formatter.format(record)

class LogRecordTable(object):

    @classmethod
    def make_output_for_row(cls, row, format=None, datefmt=None, **kwargs):
        category = row.get("category", None)
        level = LogLevel.parse_type(row.get("level", "INFO"))
        message = row.get("message", "__UNDEFINED__")
        return make_log_record_output(category, level, message,
                                      format, datefmt, **kwargs)

    @staticmethod
    def annotate_with_row_schema(table, row_schema):
        """
        Annotate/extend a table of log-records with additional columns from
        the log-record schema if columns are missing.

        :param table:   Table w/ log-records (as :class:`behave.model.Table`)
        :param row_schema:  Log-record row schema (as dict).
        """
        for column, value in row_schema.items():
            if column not in table.headings:
                table.add_column(column, default_value=value)


# -----------------------------------------------------------------------------
# STEP DEFINITIONS:
# -----------------------------------------------------------------------------
# @step('I create log records for the following categories')
# def step_I_create_logrecords_for_categories_with_text(context):
#     assert context.text is not None, "REQUIRE: context.text"
#     current_level = context.config.logging_level
#     categories = context.text.split()
#     for category_name in categories:
#         logger = logging.getLogger(category_name)
#         logger.log(current_level, "__LOG_RECORD__")

@step('I create log records with')
def step_I_create_logrecords_with_table(context):
    """
    Step definition that creates one more log records by using a table.

    .. code-block: gherkin

        When I create log records with:
            | category | level | message   |
            |  foo     | ERROR | Hello Foo |
            |  foo.bar | WARN  | Hello Foo.Bar |

    Table description
    ------------------

    | Column   | Type     | Required | Description |
    | category | string   | yes      | Category (or logger) to use. |
    | level    | LogLevel | yes      | Log level to use.   |
    | message  | string   | yes      | Log message to use. |

    .. code-block: python

        import logging
        from behave.configuration import LogLevel
        for row in table.rows:
            logger = logging.getLogger(row.category)
            level  = LogLevel.parse_type(row.level)
            logger.log(level, row.message)
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["category", "level", "message"])
    for row in context.table.rows:
        category = row["category"]
        if category == "__ROOT__":
            category = None
        level = LogLevel.parse_type(row["level"])
        message = row["message"]
        make_log_record(category, level, message)


@step('I create a log record with')
def step_I_create_logrecord_with_table(context):
    """
    Create an log record by using a table to provide the parts.

    .. seealso: :func:`step_I_create_logrecords_with_table()`
    """
    assert context.table, "REQUIRE: context.table"
    assert len(context.table.rows) == 1, "REQUIRE: table.row.size == 1"
    step_I_create_logrecords_with_table(context)

@step('I define the log record schema')
def step_I_define_logrecord_schema_with_table(context):
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["category", "level", "message"])
    assert len(context.table.rows) == 1, \
        "REQUIRE: context.table.rows.size(%s) == 1" % (len(context.table.rows))

    row = context.table.rows[0]
    row_schema = dict(category=row["category"], level=row["level"],
                  message=row["message"])
    context.log_record_row_schema = row_schema


@then('the command output should contain the following log records')
def step_command_output_should_contain_log_records(context):
    """
    Verifies that the command output contains the specified log records
    (in any order).

    .. code-block: gherkin

        Then the command output should contain the following log records:
            | category | level   | message |
            | bar      | CURRENT | xxx     |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["category", "level", "message"])
    format = getattr(context, "log_record_format", context.config.logging_format)
    for row in context.table.rows:
        output = LogRecordTable.make_output_for_row(row, format)
        context.execute_steps(u'''
            Then the command output should contain:
                """
                {expected_output}
                """
            '''.format(expected_output=output))


@then('the command output should not contain the following log records')
def step_command_output_should_not_contain_log_records(context):
    """
    Verifies that the command output contains the specified log records
    (in any order).

    .. code-block: gherkin

        Then the command output should contain the following log records:
            | category | level   | message |
            | bar      | CURRENT | xxx     |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["category", "level", "message"])
    format = getattr(context, "log_record_format", context.config.logging_format)
    for row in context.table.rows:
        output = LogRecordTable.make_output_for_row(row, format)
        context.execute_steps(u'''
            Then the command output should not contain:
                """
                {expected_output}
                """
            '''.format(expected_output=output))

@then('the command output should contain the following log record')
def step_command_output_should_contain_log_record(context):
    assert context.table, "REQUIRE: context.table"
    assert len(context.table.rows) == 1, "REQUIRE: table.row.size == 1"
    step_command_output_should_contain_log_records(context)


@then('the command output should not contain the following log record')
def step_command_output_should_not_contain_log_record(context):
    assert context.table, "REQUIRE: context.table"
    assert len(context.table.rows) == 1, "REQUIRE: table.row.size == 1"
    step_command_output_should_not_contain_log_records(context)

@then('the command output should contain log records from categories')
def step_command_output_should_contain_log_records_from_categories(context):
    """
    Verifies that the command output contains the specified log records
    (in any order).

    .. code-block: gherkin

        Given I define a log record schema:
            | category | level | message |
            | root     | ERROR | __LOG_MESSAGE__ |
        Then the command output should contain log records from categories:
            | category |
            | bar      |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_column("category")
    record_schema = context.log_record_row_schema
    LogRecordTable.annotate_with_row_schema(context.table, record_schema)
    step_command_output_should_contain_log_records(context)
    context.table.remove_columns(["level", "message"])


@then('the command output should not contain log records from categories')
def step_command_output_should_not_contain_log_records_from_categories(context):
    """
    Verifies that the command output contains not log records from
    the provided log categories (in any order).

    .. code-block: gherkin

        Given I define the log record schema:
            | category | level | message |
            | root     | ERROR | __LOG_MESSAGE__ |
        Then the command output should not contain log records from categories:
            | category |
            | bar      |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_column("category")
    record_schema = context.log_record_row_schema
    LogRecordTable.annotate_with_row_schema(context.table, record_schema)
    step_command_output_should_not_contain_log_records(context)
    context.table.remove_columns(["level", "message"])

@then('the file "{filename}" should contain the log records')
def step_file_should_contain_log_records(context, filename):
    """
    Verifies that the command output contains the specified log records
    (in any order).

    .. code-block: gherkin

        Then the file "xxx.log" should contain the log records:
            | category | level   | message |
            | bar      | CURRENT | xxx     |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["category", "level", "message"])
    format = getattr(context, "log_record_format", context.config.logging_format)
    for row in context.table.rows:
        output = LogRecordTable.make_output_for_row(row, format)
        context.text = output
        step_file_should_contain_multiline_text(context, filename)

@then('the file "{filename}" should not contain the log records')
def step_file_should_not_contain_log_records(context, filename):
    """
    Verifies that the command output contains the specified log records
    (in any order).

    .. code-block: gherkin

        Then the file "xxx.log" should not contain the log records:
            | category | level   | message |
            | bar      | CURRENT | xxx     |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["category", "level", "message"])
    format = getattr(context, "log_record_format", context.config.logging_format)
    for row in context.table.rows:
        output = LogRecordTable.make_output_for_row(row, format)
        context.text = output
        step_file_should_not_contain_multiline_text(context, filename)


@step('I use "{log_record_format}" as log record format')
def step_use_log_record_format_text(context, log_record_format):
    context.log_record_format = log_record_format

@step('I use the log record configuration')
def step_use_log_record_configuration(context):
    """
    Define log record configuration parameters.

    .. code-block: gherkin

        Given I use the log record configuration:
            | property | value |
            | format   |       |
            | datefmt  |       |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["property", "value"])
    for row in context.table.rows:
        property_name = row["property"]
        value = row["value"]
        if property_name == "format":
            context.log_record_format = value
        elif property_name == "datefmt":
            context.log_record_datefmt = value
        else:
            raise KeyError("Unknown property=%s" % property_name)


# -----------------------------------------------------------------------------
# TODO: STEP DEFINITIONS:
# -----------------------------------------------------------------------------
@step('I capture log records with level "{level}" or above')
def step_I_capture_logrecords(context, level):
    raise NotImplementedError()


@step('I capture log records')
def step_I_capture_logrecords(context):
    """

    .. code-block: gherkin
        Given I capture log records
        When I capture log records

    :param context:
    """
    raise NotImplementedError()
    logcapture = getattr(context, "logcapture", None)
    if not logcapture:
        context.logcapture = LoggingCapture()

########NEW FILE########
__FILENAME__ = note_steps
# -*- coding: utf-8 -*-
"""
Step definitions for providing notes/hints.
The note steps explain what was important in the last few steps of
this scenario (for a test reader).
"""

from behave import step


# -----------------------------------------------------------------------------
# STEPS FOR: remarks/comments
# -----------------------------------------------------------------------------
@step(u'note that "{remark}"')
def step_note_that(context, remark):
    """
    Used as generic step that provides an additional remark/hint
    and enhance the readability/understanding without performing any check.

    .. code-block:: gherkin

        Given that today is "April 1st"
          But note that "April 1st is Fools day (and beware)"
    """
    log = getattr(context, "log", None)
    if log:
        log.info(u"NOTE: %s;" % remark)


########NEW FILE########
__FILENAME__ = passing_steps
# -*- coding: utf-8 -*-
"""
Passing steps.
Often needed in examples.

EXAMPLES:

    Given a step passes
    When  another step passes
    Then  a step passes

    Given ...
    When  ...
    Then  it should pass because "the answer is correct".
"""

from behave import step, then

# -----------------------------------------------------------------------------
# STEPS FOR: passing
# -----------------------------------------------------------------------------
@step('{word:w} step passes')
def step_passes(context, word):
    """
    Step that always fails, mostly needed in examples.
    """
    pass

@then('it should pass because "{reason}"')
def then_it_should_pass_because(context, reason):
    """
    Self documenting step that indicates some reason.
    """
    pass


########NEW FILE########
__FILENAME__ = pathutil
# -*- coding -*-
"""
Provides some command utility functions.

TODO:
  matcher that ignores empty lines and whitespace and has contains comparison
"""

from __future__ import print_function, unicode_literals
# from behave4cmd.steputil import ensure_attribute_exists
# import shutil
import os.path
import codecs
# try:
#     import io
# except ImportError:
#     # -- FOR: python2.5
#     import codecs as io

# -----------------------------------------------------------------------------
# CONSTANTS:
# -----------------------------------------------------------------------------
# HERE     = os.path.dirname(__file__)
# WORKDIR  = os.path.join(HERE, "..", "__WORKDIR__")
# # -- XXX-SHOULD-BE:
# WORKDIR  = os.path.join(os.getcwd(), "__WORKDIR__")
# WORKDIR  = os.path.abspath(WORKDIR)


# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS:
# -----------------------------------------------------------------------------
def realpath_with_context(path, context):
    """
    Convert a path into its realpath:

      * For relative path: use :attr:`context.workdir` as root directory
      * For absolute path: Pass-through without any changes.

    :param path: Filepath to convert (as string).
    :param context: Behave context object (with :attr:`context.workdir`)
    :return: Converted path.
    """
    if not os.path.isabs(path):
        # XXX ensure_workdir_exists(context)
        assert context.workdir
        path = os.path.join(context.workdir, os.path.normpath(path))
    return path

def posixpath_normpath(pathname):
    """
    Convert path into POSIX path:

      * Normalize path
      * Replace backslash with slash

    :param pathname: Pathname (as string)
    :return: Normalized POSIX path.
    """
    backslash = '\\'
    pathname2 = os.path.normpath(pathname) or "."
    if backslash in pathname2:
        pathname2 = pathname2.replace(backslash, '/')
    return pathname2

def read_file_contents(filename, context=None, encoding=None):
    filename_ = realpath_with_context(filename, context)
    assert os.path.exists(filename_)
    with open(filename_, "r") as file_:
        file_contents = file_.read()
    return file_contents

# def create_new_workdir(context):
#     ensure_attribute_exists(context, "workdir", default=WORKDIR)
#     if os.path.exists(context.workdir):
#         shutil.rmtree(context.workdir, ignore_errors=True)
#     ensure_workdir_exists(context)

def create_textfile_with_contents(filename, contents, encoding='utf-8'):
    """
    Creates a textual file with the provided contents in the workdir.
    Overwrites an existing file.
    """
    ensure_directory_exists(os.path.dirname(filename))
    if os.path.exists(filename):
        os.remove(filename)
    outstream = codecs.open(filename, "w", encoding)
    outstream.write(contents)
    if contents and not contents.endswith("\n"):
        outstream.write("\n")
    outstream.flush()
    outstream.close()
    assert os.path.exists(filename), "ENSURE file exists: %s" % filename


def ensure_file_exists(filename, context=None):
    real_filename = filename
    if context:
        real_filename = realpath_with_context(filename, context)
    if not os.path.exists(real_filename):
        create_textfile_with_contents(real_filename, "")
    assert os.path.exists(real_filename), "ENSURE file exists: %s" % filename

def ensure_directory_exists(dirname, context=None):
    """
    Ensures that a directory exits.
    If it does not exist, it is automatically created.
    """
    real_dirname = dirname
    if context:
        real_dirname = realpath_with_context(dirname, context)
    if not os.path.exists(real_dirname):
        os.makedirs(real_dirname)
    assert os.path.exists(real_dirname), "ENSURE dir exists: %s" % dirname
    assert os.path.isdir(real_dirname),  "ENSURE isa dir: %s" % dirname

# def ensure_workdir_exists(context):
#     """
#     Ensures that the work directory exists.
#     In addition, the location of the workdir is stored as attribute in
#     the context object.
#     """
#     ensure_attribute_exists(context, "workdir", default=WORKDIR)
#     # if not context.workdir:
#     #     context.workdir = os.path.abspath(WORKDIR)
#     ensure_directory_exists(context.workdir)

########NEW FILE########
__FILENAME__ = textutil
# -*- coding -*-
"""
Provides some command utility functions.

TODO:
  matcher that ignores empty lines and whitespace and has contains comparison
"""

from __future__ import unicode_literals
from hamcrest import assert_that, is_not, equal_to, contains_string
# DISABLED: from behave4cmd.hamcrest_text import matches_regexp
import codecs

DEBUG = False

# -----------------------------------------------------------------------------
# CLASS: TextProxy
# -----------------------------------------------------------------------------
# class TextProxy(object):
#     """
#     Simplifies conversion between (Unicode) string and its byte representation.
#     Provides a ValueObject to store a string or its byte representation.
#     Afterwards you can explicitly access both representations by using:
#
#     EXAMPLE:
#
#     .. testcode::
#
#         from behave4cmd.textutil import TextProxy
#         message = TextProxy("Hello world", encoding="UTF-8")
#         assert message.data == "Hello world"  # -- RAW DATA access.
#         assert isinstance(message.text, basestring)
#         assert isinstance(message.bytes, bytes)
#         assert message == "Hello world"
#         assert len(message) == len(message.data) == 11
#     """
#     encoding_errors = "strict"
#     default_encoding = "UTF-8"
#
#     def __init__(self, data=None, encoding=None, errors=None):
#         self.encoding = encoding or self.default_encoding
#         self.errors = errors or self.encoding_errors
#         self.set(data)
#
#     def get(self):
#         return self.data
#
#     def set(self, data):
#         self.data = data or ""
#         self._text = None
#         self._bytes = None
#
#     def clear(self):
#         self.set(None)
#
#     @property
#     def text(self):
#         """Provide access to string-representation of the data."""
#         if self._text is None:
#             if isinstance(self.data, basestring):
#                 _text = self.data
#             elif isinstance(self.data, bytes):
#                 _text = codecs.decode(self.data, self.encoding, self.errors)
#             else:
#                 _text = str(self.data)
#             self._text = _text
#         assert isinstance(self._text, basestring)
#         return self._text
#
#     @property
#     def bytes(self):
#         """Provide access to byte-representation of the data."""
#         if self._bytes is None:
#             if isinstance(self.data, bytes) and not isinstance(self.data, str):
#                 self._bytes = self.data
#             else:
#                 text = self.data
#                 if not isinstance(text, basestring):
#                     text = unicode(text)
#                 assert isinstance(text, basestring)
#                 self._bytes = codecs.encode(text, self.encoding, self.errors)
#         assert isinstance(self._bytes, bytes)
#         return self._bytes
#
#     def __repr__(self):
#         """Textual representation of this object."""
#         data = self.data or ""
#         prefix = ""
#         if isinstance(data, bytes) and not isinstance(data, basestring):
#             prefix= u"b"
# #        str(self.text)
# #        str(self.encoding)
# #        str(prefix)
# #        _ =  u"<TextProxy data[size=%d]=x'x', encoding=x>" % len(self)
# #        _ = u"<TextProxy data[size=x]=%s'x', encoding=x>" % prefix
# #        _ = u"<TextProxy data[size=x]=x'%s', encoding=x>" % self.text
# #        _ = u"<TextProxy data[size=x]=x'x', encoding=%s>" % self.encoding
#         return u"<TextProxy data[size=%d]=%s'%s', encoding=%s>" %\
#                (len(self), prefix, self.text, self.encoding)
#
#     def __str__(self):
#         """Conversion into str() object."""
#         return self.text
#
#     def __bytes__(self):
#         """Conversion into bytes() object."""
#         return self.bytes
#
#     def __bool__(self):
#         """Conversion into a bool value, used for truth testing."""
#         return bool(self.data)
#
#     def __iter__(self):
#         """Conversion into an iterator."""
#         return iter(self.data)
#
#     def __contains__(self, item):
#         """Check if item is contained in raw data."""
#         if isinstance(item, basestring):
#             return item in self.text
#         elif isinstance(item, bytes):
#             return item in self.bytes
#         else:
#             return item in self.data
#
#     def __len__(self):
#         if self.data is None:
#             return 0
#         return len(self.data)
#
#     def __nonzero__(self):
#         return len(self) > 0
#
#     def __eq__(self, other):
#         if isinstance(other, basestring):
#             return self.text == other
#         elif isinstance(other, bytes):
#             return self.bytes == other
#         else:
#             return self.data == other
#
#     def __ne__(self, other):
#         return not (self == other)
#
# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS:
# -----------------------------------------------------------------------------
def template_substitute(text, **kwargs):
    """
    Replace placeholders in text by using the data mapping.
    Other placeholders that is not represented by data is left untouched.

    :param text:   Text to search and replace placeholders.
    :param data:   Data mapping/dict for placeholder key and values.
    :return: Potentially modified text with replaced placeholders.
    """
    for name, value in kwargs.items():
        placeholder_pattern = "{%s}" % name
        if placeholder_pattern in text:
            text = text.replace(placeholder_pattern, value)
    return text


def text_remove_empty_lines(text):
    """
    Whitespace normalization:

      - Strip empty lines
      - Strip trailing whitespace
    """
    lines = [ line.rstrip()  for line in text.splitlines()  if line.strip() ]
    return "\n".join(lines)

def text_normalize(text):
    """
    Whitespace normalization:

      - Strip empty lines
      - Strip leading whitespace  in a line
      - Strip trailing whitespace in a line
      - Normalize line endings
    """
    # if not isinstance(text, str):
    if isinstance(text, bytes):
        # -- MAYBE: command.ouput => bytes, encoded stream output.
        text = codecs.decode(text)
    lines = [ line.strip()  for line in text.splitlines()  if line.strip() ]
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# ASSERTIONS:
# -----------------------------------------------------------------------------
def assert_text_should_equal(actual_text, expected_text):
    assert_that(actual_text, equal_to(expected_text))

def assert_text_should_not_equal(actual_text, expected_text):
    assert_that(actual_text, is_not(equal_to(expected_text)))

def assert_text_should_contain_exactly(text, expected_part):
    assert_that(text, contains_string(expected_part))

def assert_text_should_not_contain_exactly(text, expected_part):
    assert_that(text, is_not(contains_string(expected_part)))

def assert_text_should_contain(text, expected_part):
    assert_that(text, contains_string(expected_part))

def assert_text_should_not_contain(text, unexpected_part):
    assert_that(text, is_not(contains_string(unexpected_part)))

def assert_normtext_should_equal(actual_text, expected_text):
    expected_text2 = text_normalize(expected_text.strip())
    actual_text2   = text_normalize(actual_text.strip())
    assert_that(actual_text2, equal_to(expected_text2))

def assert_normtext_should_not_equal(actual_text, expected_text):
    expected_text2 = text_normalize(expected_text.strip())
    actual_text2   = text_normalize(actual_text.strip())
    assert_that(actual_text2, is_not(equal_to(expected_text2)))

def assert_normtext_should_contain(text, expected_part):
    expected_part2 = text_normalize(expected_part)
    actual_text    = text_normalize(text.strip())
    if DEBUG:
        print("expected:\n{0}".format(expected_part2))
        print("actual:\n{0}".format(actual_text))
    assert_text_should_contain(actual_text, expected_part2)

def assert_normtext_should_not_contain(text, unexpected_part):
    unexpected_part2 = text_normalize(unexpected_part)
    actual_text      = text_normalize(text.strip())
    if DEBUG:
        print("expected:\n{0}".format(unexpected_part2))
        print("actual:\n{0}".format(actual_text))
    assert_text_should_not_contain(actual_text, unexpected_part2)


# def assert_text_should_match_pattern(text, pattern):
#     """
#     Assert that the :attr:`text` matches the regular expression :attr:`pattern`.
#
#     :param text: Multi-line text (as string).
#     :param pattern: Regular expression pattern (as string, compiled regexp).
#     :raise: AssertionError, if text matches not the pattern.
#     """
#     assert_that(text, matches_regexp(pattern))
#
# def assert_text_should_not_match_pattern(text, pattern):
#     """
#     Assert that the :attr:`text` matches not the regular expression
#     :attr:`pattern`.
#
#     :param text: Multi-line text (as string).
#     :param pattern: Regular expression pattern (as string, compiled regexp).
#     :raise: AssertionError, if text matches the pattern.
#     """
#     assert_that(text, is_not(matches_regexp(pattern)))
#
# -----------------------------------------------------------------------------
# MAIN:
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = __all_steps__
# -*- coding: utf-8 -*-
"""
Import all step definitions of this step-library.
Step definitions are automatically registered in "behave.step_registry".
"""

# -- IMPORT STEP-LIBRARY: behave4cmd0
import behave4cmd0.command_steps
import behave4cmd0.note_steps
import behave4cmd0.log.steps

########NEW FILE########
__FILENAME__ = behave.step_durations
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility script to retrieve duration information from behave JSON output.

REQUIRES: Python >= 2.6 (json module is part of Python standard library)
LICENSE:  BSD
"""

__author__    = "Jens Engel"
__copyright__ = "(c) 2013 by Jens Engel"
__license__   = "BSD"
VERSION = "0.1.0"


# -- IMPORTS:
from behave import json_parser
from behave.model import ScenarioOutline
from optparse import OptionParser
from operator import attrgetter
import os.path
import sys


# ----------------------------------------------------------------------------
# FUNCTIONS:
# ----------------------------------------------------------------------------
class StepDurationData(object):
    def __init__(self, step=None):
        self.step_name = None
        self.min_duration = sys.maxint
        self.max_duration = 0
        self.durations = []
        self.step = step
        if step:
            self.process_step(step)

    @staticmethod
    def make_step_name(step):
        step_name = "%s %s" % (step.step_type.capitalize(), step.name)
        return step_name

    def process_step(self, step):
        step_name = self.make_step_name(step)
        if not self.step_name:
            self.step_name = step_name
        if self.min_duration > step.duration:
            self.min_duration = step.duration
        if self.max_duration < step.duration:
            self.max_duration = step.duration
        self.durations.append(step.duration)


class BehaveDurationData(object):
    def __init__(self):
        self.step_registry = {}
        self.all_steps = []
        self.all_scenarios = []


    def process_features(self, features):
        for feature in features:
            self.process_feature(feature)

    def process_feature(self, feature):
        if feature.background:
            self.process_background(feature.background)
        for scenario in feature.scenarios:
            if isinstance(scenario, ScenarioOutline):
                self.process_scenario_outline(scenario)
            else:
                self.process_scenario(scenario)

    def process_step(self, step):
        step_name = StepDurationData.make_step_name(step)
        known_step = self.step_registry.get(step_name, None)
        if known_step:
            known_step.process_step(step)
        else:
            step_data = StepDurationData(step)
            self.step_registry[step_name] = step_data
        self.all_steps.append(step)

    def process_background(self, scenario):
        for step in scenario:
            self.process_step(step)

    def process_scenario(self, scenario):
        for step in scenario:
            self.process_step(step)

    def process_scenario_outline(self, scenario_outline):
        for scenario in scenario_outline:
            self.process_scenario(scenario)

    def report_step_durations(self, limit=None, min_duration=None, ostream=sys.stdout):
        step_datas = self.step_registry.values()
        steps_size = len(step_datas)
        steps_by_longest_duration_first = sorted(step_datas,
                                                 key=attrgetter("max_duration"),
                                                 reverse=True)
        ostream.write("STEP DURATIONS (longest first, size=%d):\n" % steps_size)
        ostream.write("-" * 80)
        ostream.write("\n")
        for index, step in enumerate(steps_by_longest_duration_first):
            ostream.write("% 4d.  %9.6fs  %s" % \
                          (index+1, step.max_duration, step.step_name))
            calls = len(step.durations)
            if calls > 1:
                ostream.write(" (%d calls, min: %.6fs)\n" % (calls, step.min_duration))
            else:
                ostream.write("\n")
            if ((limit and index+1 >= limit) or
                (step.max_duration < min_duration)):
                remaining = steps_size - (index+1)
                ostream.write("...\nSkip remaining %d steps.\n" % remaining)
                break


# ----------------------------------------------------------------------------
# MAIN FUNCTION:
# ----------------------------------------------------------------------------
def main(args=None):
    if args is None:
        args = sys.argv[1:]

    usage_ = """%prog [OPTIONS] JsonFile
Read behave JSON data file and extract steps with longest duration."""
    parser = OptionParser(usage=usage_, version=VERSION)
    parser.add_option("-e", "--encoding", dest="encoding",
                     default="UTF-8",
                     help="Encoding to use (default: %default).")
    parser.add_option("-l", "--limit", dest="limit", type="int",
                     help="Max. number of steps (default: %default).")
    parser.add_option("-m", "--min", dest="min_duration", default="0",
                     help="Min. duration threshold (default: %default).")
    options, filenames = parser.parse_args(args)
    if not filenames:
        parser.error("OOPS, no filenames provided.")
    elif len(filenames) > 1:
        parser.error("OOPS: Can only process one JSON file.")
    min_duration = float(options.min_duration)
    if min_duration < 0:
        min_duration = None
    json_filename = filenames[0]
    if not os.path.exists(json_filename):
        parser.error("JSON file '%s' not found" % json_filename)

    # -- NORMAL PROCESSING: Read JSON, extract step durations and report them.
    features = json_parser.parse(json_filename)
    processor = BehaveDurationData()
    processor.process_features(features)
    processor.report_step_durations(options.limit, min_duration)
    sys.stdout.write("Detected %d features.\n" % len(features))
    return 0


# ----------------------------------------------------------------------------
# AUTO-MAIN:
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = json.format
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility script to format/beautify one or more JSON files.

REQUIRES: Python >= 2.6 (json module is part of Python standard library)
LICENSE:  BSD
"""

__author__    = "Jens Engel"
__copyright__ = "(c) 2011-2013 by Jens Engel"
VERSION = "0.2.2"

# -- IMPORTS:
import os.path
import glob
import logging
from   optparse import OptionParser
import sys
try:
    import json
except ImportError:
    import simplejson as json   #< BACKWARD-COMPATIBLE: Python <= 2.5


# ----------------------------------------------------------------------------
# CONSTANTS:
# ----------------------------------------------------------------------------
DEFAULT_INDENT_SIZE = 2

# ----------------------------------------------------------------------------
# FUNCTIONS:
# ----------------------------------------------------------------------------
def json_format(filename, indent=DEFAULT_INDENT_SIZE, **kwargs):
    """
    Format/Beautify a JSON file.

    :param filename:    Filename of a JSON file to process.
    :param indent:      Number of chars to indent per level (default: 4).
    :returns: >= 0, if successful (written=1, skipped=2). Zero(0), otherwise.
    :raises:  ValueError,           if parsing JSON file contents fails.
    :raises:  json.JSONDecodeError, if parsing JSON file contents fails.
    :raises:  IOError (Error 2), if file not found.
    """
    console  = kwargs.get("console", logging.getLogger("console"))
    encoding = kwargs.get("encoding", None)
    dry_run  = kwargs.get("dry_run", False)
    if indent is None:
        sort_keys = False
    else:
        sort_keys = True

    message = "%s ..." % filename
#    if not (os.path.exists(filename) and os.path.isfile(filename)):
#        console.error("%s ERROR: file not found.", message)
#        return 0

    contents = open(filename, "r").read()
    data      = json.loads(contents, encoding=encoding)
    contents2 = json.dumps(data, indent=indent, sort_keys=sort_keys)
    contents2 = contents2.strip()
    contents2 = "%s\n" % contents2
    if contents == contents2:
        console.info("%s SKIP (already pretty)", message)
        return 2 #< SKIPPED.
    elif not dry_run:
        outfile = open(filename, "w")
        outfile.write(contents2)
        outfile.close()
        console.warn("%s OK", message)
        return 1 #< OK

def json_formatall(filenames, indent=DEFAULT_INDENT_SIZE, dry_run=False):
    """
    Format/Beautify a JSON file.

    :param filenames:  Format one or more JSON files.
    :param indent:     Number of chars to indent per level (default: 4).
    :returns:  0, if successful. Otherwise, number of errors.
    """
    errors = 0
    console = logging.getLogger("console")
    for filename in filenames:
        try:
            result = json_format(filename, indent=indent, console=console,
                                 dry_run=dry_run)
            if not result:
                errors += 1
#        except json.decoder.JSONDecodeError, e:
#            console.error("ERROR: %s (filename: %s)", e, filename)
#            errors += 1
        except StandardError, e:
            console.error("ERROR %s: %s (filename: %s)",
                          e.__class__.__name__, e, filename)
            errors += 1
    return errors

# ----------------------------------------------------------------------------
# MAIN FUNCTION:
# ----------------------------------------------------------------------------
def main(args=None):
    """Boilerplate for this script."""
    if args is None:
        args = sys.argv[1:]

    usage_ = """%prog [OPTIONS] JsonFile [MoreJsonFiles...]
Format/Beautify one or more JSON file(s)."""
    parser = OptionParser(usage=usage_, version=VERSION)
    parser.add_option("-i", "--indent", dest="indent_size",
                default=DEFAULT_INDENT_SIZE, type="int",
                help="Indent size to use (default: %default).")
    parser.add_option("-c", "--compact", dest="compact",
                action="store_true", default=False,
                help="Use compact format (default: %default).")
    parser.add_option("-n", "--dry-run", dest="dry_run",
                action="store_true", default=False,
                help="Check only if JSON is well-formed (default: %default).")
    options, filenames = parser.parse_args(args)    #< pylint: disable=W0612
    if not filenames:
        parser.error("OOPS, no filenames provided.")
    if options.compact:
        options.indent_size = None

    # -- STEP: Init logging subsystem.
    format_ = "json.format: %(message)s"
    logging.basicConfig(level=logging.WARN, format=format_)
    console = logging.getLogger("console")

    # -- DOS-SHELL SUPPORT: Perform filename globbing w/ wildcards.
    skipped = 0
    filenames2 = []
    for filename in filenames:
        if "*" in filenames:
            files = glob.glob(filename)
            filenames2.extend(files)
        elif os.path.isdir(filename):
            # -- CONVENIENCE-SHORTCUT: Use DIR as shortcut for JSON files.
            files = glob.glob(os.path.join(filename, "*.json"))
            filenames2.extend(files)
            if not files:
                console.info("SKIP %s, no JSON files found in dir.", filename)
                skipped += 1
        elif not os.path.exists(filename):
            console.warn("SKIP %s, file not found.", filename)
            skipped += 1
            continue
        else:
            assert os.path.exists(filename)
            filenames2.append(filename)
    filenames = filenames2

    # -- NORMAL PROCESSING:
    errors  = json_formatall(filenames, options.indent_size,
                             dry_run=options.dry_run)
    console.error("Processed %d files (%d with errors, skipped=%d).",
                  len(filenames), errors, skipped)
    if not filenames:
        errors += 1
    return errors

# ----------------------------------------------------------------------------
# AUTO-MAIN:
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = jsonschema_validate
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Validate a JSON file against its JSON schema.

SEE ALSO:
  * https://python-jsonschema.readthedocs.org/
  * https://python-jsonschema.readthedocs.org/en/latest/errors.html

REQUIRES:
  Python >= 2.6
  jsonschema >= 1.3.0
  argparse
"""

__author__  = "Jens Engel"
__version__ = "0.1.0"

from jsonschema import validate
import argparse
import os.path
import sys
import textwrap
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        sys.exit("REQUIRE: simplejson (which is not installed)")


# -----------------------------------------------------------------------------
# CONSTANTS:
# -----------------------------------------------------------------------------
HERE = os.path.dirname(__file__)
TOP  = os.path.normpath(os.path.join(HERE, ".."))
SCHEMA = os.path.join(TOP, "etc", "json", "behave.json-schema")


# -----------------------------------------------------------------------------
# FUNCTIONS:
# -----------------------------------------------------------------------------
def jsonschema_validate(filename, schema, encoding=None):
    f = open(filename, "r")
    contents = f.read()
    f.close()
    data = json.loads(contents, encoding=encoding)
    return validate(data, schema)


def main(args=None):
    """
    Validate JSON files against their JSON schema.
    NOTE: Behave's JSON-schema is used per default.

    SEE ALSO:
      * http://json-schema.org/
      * http://tools.ietf.org/html/draft-zyp-json-schema-04
    """
    if args is None:
        args = sys.argv[1:]
    default_schema = None
    if os.path.exists(SCHEMA):
        default_schema = SCHEMA

    parser = argparse.ArgumentParser(
                description=textwrap.dedent(main.__doc__),
                formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-v", "--version",
                        action="version", version=__version__)
    parser.add_argument("-s", "--schema",
                        help="JSON schema to use.")
    parser.add_argument("-e", "--encoding",
                        help="Encoding for JSON/JSON schema.")
    parser.add_argument("files", nargs="+", metavar="JSON_FILE",
                        help="JSON file to check.")
    parser.set_defaults(
            schema=default_schema,
            encoding="UTF-8"
    )
    options = parser.parse_args(args)
    if not options.schema:
        parser.error("REQUIRE: JSON schema")
    elif not os.path.isfile(options.schema):
        parser.error("SCHEMA not found: %s" % options.schema)

    try:
        f = open(options.schema, "r")
        contents = f.read()
        f.close()
        schema = json.loads(contents, encoding=options.encoding)
    except Exception, e:
        msg = "ERROR: %s: %s (while loading schema)" % (e.__class__.__name__, e)
        sys.exit(msg)

    error_count = 0
    for filename in options.files:
        validated = True
        more_info = None
        try:
            print "validate:", filename, "...",
            jsonschema_validate(filename, schema, encoding=options.encoding)
        except Exception, e:
            more_info = "%s: %s" % (e.__class__.__name__, e)
            validated = False
            error_count += 1
        if validated:
            print "OK"
        else:
            print "FAILED\n\n%s" % more_info
    return error_count


# -----------------------------------------------------------------------------
# AUTO-MAIN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = make_localpi
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility script to create a pypi-like directory structure (localpi)
from a number of Python packages in a directory of the local filesystem.

  DIRECTORY STRUCTURE (before):
      +-- downloads/
           +-- alice-1.0.zip
           +-- alice-1.0.tar.gz
           +-- bob-1.3.0.tar.gz
           +-- bob-1.4.2.tar.gz
           +-- charly-1.0.tar.bz2

  DIRECTORY STRUCTURE (afterwards):
      +-- downloads/
           +-- simple/
           |      +-- alice/index.html   --> ../../alice-*.*
           |      +-- bob/index.html     --> ../../bob-*.*
           |      +-- charly/index.html  --> ../../charly-*.*
           |      +-- index.html  --> alice/, bob/, ...
           +-- alice-1.0.zip
           +-- alice-1.0.tar.gz
           +-- bob-1.3.0.tar.gz
           +-- bob-1.4.2.tar.gz
           +-- charly-1.0.tar.bz2

USAGE EXAMPLE:

    mkdir -p /tmp/downloads
    pip install --download=/tmp/downloads argparse Jinja2
    make_localpi.py /tmp/downloads
    pip install --index-url=file:///tmp/downloads/simple argparse Jinja2

ALTERNATIVE:

    pip install --download=/tmp/downloads argparse Jinja2
    pip install --find-links=/tmp/downloads --no-index argparse Jinja2
"""

from __future__ import with_statement, print_function
from fnmatch import fnmatch
import os.path
import shutil
import sys


__author__  = "Jens Engel"
__version__ = "0.2"
__license__ = "BSD"
__copyright__ = "(c) 2013 by Jens Engel"


class Package(object):
    """
    Package entity that keeps track of:
      * one or more versions of this package
      * one or more archive types
    """
    PATTERNS = [
        "*.egg", "*.exe", "*.whl", "*.zip", "*.tar.gz", "*.tar.bz2", "*.7z"
    ]

    def __init__(self, filename, name=None):
        if not name and filename:
            name = self.get_pkgname(filename)
        self.name  = name
        self.files = []
        if filename:
            self.files.append(filename)

    @property
    def versions(self):
        versions_info = [ self.get_pkgversion(p) for p in self.files ]
        return versions_info

    @classmethod
    def split_pkgname_parts(cls, filename):
        basename = cls.splitext(os.path.basename(filename))
        if basename.startswith("http") and r"%2F" in basename:
            # -- PIP DOWNLOAD-CACHE PACKAGE FILE NAME SCHEMA:
            pos = basename.rfind("%2F")
            basename = basename[pos+3:]

        version_part_index = 0
        parts = basename.split("-")
        for index, part in enumerate(parts):
            if index == 0:
                continue
            elif part and part[0].isdigit() and len(part) >= 3:
                version_part_index = index
                break
        name = "-".join(parts[:version_part_index])
        version = "0.0"
        remainder = None
        if version_part_index > 0:
            version = parts[version_part_index]
            if version_part_index+1 < len(parts):
                remainder = "-".join(parts[version_part_index+1:])
        assert name, "OOPS: basename=%s, name='%s'" % (basename, name)
        return (name, version, remainder)


    @classmethod
    def get_pkgname(cls, filename):
        return cls.split_pkgname_parts(filename)[0]

    @classmethod
    def get_pkgversion(cls, filename):
        return cls.split_pkgname_parts(filename)[1]

    @classmethod
    def make_pkgname_with_version(cls, filename):
        pkg_name = cls.get_pkgname(filename)
        pkg_version = cls.get_pkgversion(filename)
        return "%s-%s" % (pkg_name, pkg_version)

    @staticmethod
    def splitext(filename):
        fname = os.path.splitext(filename)[0]
        if fname.endswith(".tar"):
            fname = os.path.splitext(fname)[0]
        return fname

    @classmethod
    def isa(cls, filename):
        basename = os.path.basename(filename)
        if basename.startswith("."):
            return False
        for pattern in cls.PATTERNS:
            if fnmatch(filename, pattern):
                return True
        return False

def collect_packages(package_dir, package_map=None):
    if package_map is None:
        package_map = {}
    packages = []
    for filename in sorted(os.listdir(package_dir)):
        if not Package.isa(filename):
            continue
        pkg_filepath = os.path.join(package_dir, filename)
        package_name = Package.get_pkgname(pkg_filepath)
        package = package_map.get(package_name, None)
        if not package:
            # -- NEW PACKAGE DETECTED: Store/register package.
            package = Package(pkg_filepath)
            package_map[package.name] = package
            packages.append(package)
        else:
            # -- SAME PACKAGE: Collect other variant/version.
            package.files.append(pkg_filepath)
    return packages

def make_index_for(package, index_dir, verbose=True):
    """
    Create an 'index.html' for one package.

    :param package:   Package object to use.
    :param index_dir: Where 'index.html' should be created.
    """
    index_template = """\
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<ul>
{packages}
</ul>
</body>
</html>
"""
    item_template = '<li><a href="{1}">{0}</a></li>'
    index_filename = os.path.join(index_dir, "index.html")
    if not os.path.isdir(index_dir):
        os.makedirs(index_dir)

    parts = []
    for pkg_filename in package.files:
        pkg_name = os.path.basename(pkg_filename)
        if pkg_name == "index.html":
            # -- ROOT-INDEX:
            pkg_name = os.path.basename(os.path.dirname(pkg_filename))
        else:
            # pkg_name = package.splitext(pkg_name)
            pkg_name = package.make_pkgname_with_version(pkg_filename)
        pkg_relpath_to = os.path.relpath(pkg_filename, index_dir)
        parts.append(item_template.format(pkg_name, pkg_relpath_to))

    if not parts:
        print("OOPS: Package %s has no files" % package.name)
        return

    if verbose:
        root_index = not Package.isa(package.files[0])
        if root_index:
            info = "with %d package(s)" % len(package.files)
        else:
            package_versions = sorted(set(package.versions))
            info = ", ".join(reversed(package_versions))
        message = "%-30s  %s" % (package.name, info)
        print(message)

    with open(index_filename, "w") as f:
        packages = "\n".join(parts)
        text = index_template.format(title=package.name, packages=packages)
        f.write(text.strip())
        f.close()


def make_package_index(download_dir):
    """
    Create a pypi server like file structure below download directory.

    :param download_dir:    Download directory with packages.

    EXAMPLE BEFORE:
      +-- downloads/
           +-- wheelhouse/bob-1.4.2-*.whl
           +-- alice-1.0.zip
           +-- alice-1.0.tar.gz
           +-- bob-1.3.0.tar.gz
           +-- bob-1.4.2.tar.gz
           +-- charly-1.0.tar.bz2

    EXAMPLE AFTERWARDS:
      +-- downloads/
           +-- simple/
           |      +-- alice/index.html   --> ../../alice-*.*
           |      +-- bob/index.html     --> ../../bob-*.*
           |      +-- charly/index.html  --> ../../charly-*.*
           |      +-- index.html  --> alice/index.html, bob/index.html, ...
           +-- wheelhouse/bob-1.4.2-*.whl
           +-- alice-1.0.zip
           +-- alice-1.0.tar.gz
           +-- bob-1.3.0.tar.gz
           +-- bob-1.4.2.tar.gz
           +-- charly-1.0.tar.bz2
    """
    if not os.path.isdir(download_dir):
        raise ValueError("No such directory: %r" % download_dir)

    pkg_rootdir = os.path.join(download_dir, "simple")
    if os.path.isdir(pkg_rootdir):
        shutil.rmtree(pkg_rootdir, ignore_errors=True)
    os.mkdir(pkg_rootdir)

    package_dirs = [download_dir]
    wheelhouse_dir = os.path.join(download_dir, "wheelhouse")
    if os.path.isdir(wheelhouse_dir):
        print("Using wheelhouse: %s" % wheelhouse_dir)
        package_dirs.append(wheelhouse_dir)

    # -- STEP: Collect all packages.
    package_map = {}
    packages = []
    for package_dir in package_dirs:
        new_packages = collect_packages(package_dir, package_map)
        packages.extend(new_packages)

    # -- STEP: Make local PYTHON PACKAGE INDEX.
    root_package = Package(None, "Python Package Index")
    root_package.files = [ os.path.join(pkg_rootdir, pkg.name, "index.html")
                           for pkg in packages ]
    make_index_for(root_package, pkg_rootdir)
    for package in packages:
        index_dir = os.path.join(pkg_rootdir, package.name)
        make_index_for(package, index_dir)


# -----------------------------------------------------------------------------
# MAIN:
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if (len(sys.argv) != 2) or "-h" in sys.argv[1:] or "--help" in sys.argv[1:]:
        print("USAGE: %s DOWNLOAD_DIR" % os.path.basename(sys.argv[0]))
        print(__doc__)
        sys.exit(1)
    make_package_index(sys.argv[1])

########NEW FILE########
__FILENAME__ = toxcmd
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Provides a command container for additional tox commands, used in "tox.ini".

COMMANDS:

  * copytree
  * copy
  * py2to3

REQUIRES:
  * argparse
"""

from glob import glob
import argparse
import inspect
import os.path
import shutil
import sys

__author__ = "Jens Engel"
__copyright__ = "(c) 2013 by Jens Engel"
__license__ = "BSD"

# -----------------------------------------------------------------------------
# CONSTANTS:
# -----------------------------------------------------------------------------
VERSION = "0.1.0"
FORMATTER_CLASS = argparse.RawDescriptionHelpFormatter


# -----------------------------------------------------------------------------
# SUBCOMMAND: copytree
# -----------------------------------------------------------------------------
def command_copytree(args):
    """
    Copy one or more source directory(s) below a destination directory.
    Parts of the destination directory path are created if needed.
    Similar to the UNIX command: 'cp -R srcdir destdir'
    """
    for srcdir in args.srcdirs:
        basename = os.path.basename(srcdir)
        destdir2 = os.path.normpath(os.path.join(args.destdir, basename))
        if os.path.exists(destdir2):
            shutil.rmtree(destdir2)
        sys.stdout.write("copytree: %s => %s\n" % (srcdir, destdir2))
        shutil.copytree(srcdir, destdir2)
    return 0


def setup_parser_copytree(parser):
    parser.add_argument("srcdirs", nargs="+", help="Source directory(s)")
    parser.add_argument("destdir", help="Destination directory")


command_copytree.usage = "%(prog)s srcdir... destdir"
command_copytree.short = "Copy source dir(s) below a destination directory."
command_copytree.setup_parser = setup_parser_copytree


# -----------------------------------------------------------------------------
# SUBCOMMAND: copy
# -----------------------------------------------------------------------------
def command_copy(args):
    """
    Copy one or more source-files(s) to a destpath (destfile or destdir).
    Destdir mode is used if:
      * More than one srcfile is provided
      * Last parameter ends with a slash ("/").
      * Last parameter is an existing directory

    Destination directory path is created if needed.
    Similar to the UNIX command: 'cp srcfile... destpath'
    """
    sources = args.sources
    destpath = args.destpath
    source_files = []
    for file_ in sources:
        if "*" in file_:
            selected = glob(file_)
            source_files.extend(selected)
        elif os.path.isfile(file_):
            source_files.append(file_)

    if destpath.endswith("/") or os.path.isdir(destpath) or len(sources) > 1:
        # -- DESTDIR-MODE: Last argument is a directory.
        destdir = destpath
    else:
        # -- DESTFILE-MODE: Copy (and rename) one file.
        assert len(source_files) == 1
        destdir = os.path.dirname(destpath)

    # -- WORK-HORSE: Copy one or more files to destpath.
    if not os.path.isdir(destdir):
        sys.stdout.write("copy: Create dir %s\n" % destdir)
        os.makedirs(destdir)
    for source in source_files:
        destname = os.path.join(destdir, os.path.basename(source))
        sys.stdout.write("copy: %s => %s\n" % (source, destname))
        shutil.copy(source, destname)
    return 0


def setup_parser_copy(parser):
    parser.add_argument("sources", nargs="+", help="Source files.")
    parser.add_argument("destpath", help="Destination path")


command_copy.usage = "%(prog)s sources... destpath"
command_copy.short = "Copy one or more source files to a destinition."
command_copy.setup_parser = setup_parser_copy


# -----------------------------------------------------------------------------
# SUBCOMMAND: mkdir
# -----------------------------------------------------------------------------
def command_mkdir(args):
    """
    Create a non-existing directory (or more ...).
    If the directory exists, the step is skipped.
    Similar to the UNIX command: 'mkdir -p dir'
    """
    errors = 0
    for directory in args.dirs:
        if os.path.exists(directory):
            if not os.path.isdir(directory):
                # -- SANITY CHECK: directory exists, but as file...
                sys.stdout.write("mkdir: %s\n" % directory)
                sys.stdout.write("ERROR: Exists already, but as file...\n")
                errors += 1
        else:
            # -- NORMAL CASE: Directory does not exits yet.
            assert not os.path.isdir(directory)
            sys.stdout.write("mkdir: %s\n" % directory)
            os.makedirs(directory)
    return errors


def setup_parser_mkdir(parser):
    parser.add_argument("dirs", nargs="+", help="Directory(s)")

command_mkdir.usage = "%(prog)s dir..."
command_mkdir.short = "Create non-existing directory (or more...)."
command_mkdir.setup_parser = setup_parser_mkdir

# -----------------------------------------------------------------------------
# SUBCOMMAND: py2to3
# -----------------------------------------------------------------------------
def command_py2to3(args):
    """
    Apply '2to3' tool (Python2 to Python3 conversion tool) to Python sources.
    """
    from lib2to3.main import main
    sys.exit(main("lib2to3.fixes", args=args.sources))


def setup_parser4py2to3(parser):
    parser.add_argument("sources", nargs="+", help="Source files.")


command_py2to3.name = "2to3"
command_py2to3.usage = "%(prog)s sources..."
command_py2to3.short = "Apply python's 2to3 tool to Python sources."
command_py2to3.setup_parser = setup_parser4py2to3


# -----------------------------------------------------------------------------
# COMMAND HELPERS/UTILS:
# -----------------------------------------------------------------------------
def discover_commands():
    commands = []
    for name, func in inspect.getmembers(inspect.getmodule(toxcmd_main)):
        if name.startswith("__"):
            continue
        if name.startswith("command_") and callable(func):
            command_name0 = name.replace("command_", "")
            command_name = getattr(func, "name", command_name0)
            commands.append(Command(command_name, func))
    return commands


class Command(object):
    def __init__(self, name, func):
        assert isinstance(name, basestring)
        assert callable(func)
        self.name = name
        self.func = func
        self.parser = None

    def setup_parser(self, command_parser):
        setup_parser = getattr(self.func, "setup_parser", None)
        if setup_parser and callable(setup_parser):
            setup_parser(command_parser)
        else:
            command_parser.add_argument("args", nargs="*")

    @property
    def usage(self):
        usage = getattr(self.func, "usage", None)
        return usage

    @property
    def short_description(self):
        short_description = getattr(self.func, "short", "")
        return short_description

    @property
    def description(self):
        return inspect.getdoc(self.func)

    def __call__(self, args):
        return self.func(args)


# -----------------------------------------------------------------------------
# MAIN-COMMAND:
# -----------------------------------------------------------------------------
def toxcmd_main(args=None):
    """Command util with subcommands for tox environments."""
    usage = "USAGE: %(prog)s [OPTIONS] COMMAND args..."
    if args is None:
        args = sys.argv[1:]

    # -- STEP: Build command-line parser.
    parser = argparse.ArgumentParser(description=inspect.getdoc(toxcmd_main),
                                     formatter_class=FORMATTER_CLASS)
    common_parser = parser.add_argument_group("Common options")
    common_parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(help="commands")
    for command in discover_commands():
        command_parser = subparsers.add_parser(command.name,
                                               usage=command.usage,
                                               description=command.description,
                                               help=command.short_description,
                                               formatter_class=FORMATTER_CLASS)
        command_parser.set_defaults(func=command)
        command.setup_parser(command_parser)
        command.parser = command_parser

    # -- STEP: Process command-line and run command.
    options = parser.parse_args(args)
    command_function = options.func
    return command_function(options)


# -----------------------------------------------------------------------------
# MAIN:
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(toxcmd_main())

########NEW FILE########
__FILENAME__ = toxcmd3
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Provides a command container for additional tox commands, used in "tox.ini".

COMMANDS:

  * copytree
  * copy
  * py2to3

REQUIRES:
  * argparse
"""

from glob import glob
import argparse
import inspect
import os.path
import shutil
import sys
import collections

__author__ = "Jens Engel"
__copyright__ = "(c) 2013 by Jens Engel"
__license__ = "BSD"

# -----------------------------------------------------------------------------
# CONSTANTS:
# -----------------------------------------------------------------------------
VERSION = "0.1.0"
FORMATTER_CLASS = argparse.RawDescriptionHelpFormatter


# -----------------------------------------------------------------------------
# SUBCOMMAND: copytree
# -----------------------------------------------------------------------------
def command_copytree(args):
    """
    Copy one or more source directory(s) below a destination directory.
    Parts of the destination directory path are created if needed.
    Similar to the UNIX command: 'cp -R srcdir destdir'
    """
    for srcdir in args.srcdirs:
        basename = os.path.basename(srcdir)
        destdir2 = os.path.normpath(os.path.join(args.destdir, basename))
        if os.path.exists(destdir2):
            shutil.rmtree(destdir2)
        sys.stdout.write("copytree: %s => %s\n" % (srcdir, destdir2))
        shutil.copytree(srcdir, destdir2)
    return 0


def setup_parser_copytree(parser):
    parser.add_argument("srcdirs", nargs="+", help="Source directory(s)")
    parser.add_argument("destdir", help="Destination directory")


command_copytree.usage = "%(prog)s srcdir... destdir"
command_copytree.short = "Copy source dir(s) below a destination directory."
command_copytree.setup_parser = setup_parser_copytree


# -----------------------------------------------------------------------------
# SUBCOMMAND: copy
# -----------------------------------------------------------------------------
def command_copy(args):
    """
    Copy one or more source-files(s) to a destpath (destfile or destdir).
    Destdir mode is used if:
      * More than one srcfile is provided
      * Last parameter ends with a slash ("/").
      * Last parameter is an existing directory

    Destination directory path is created if needed.
    Similar to the UNIX command: 'cp srcfile... destpath'
    """
    sources = args.sources
    destpath = args.destpath
    source_files = []
    for file_ in sources:
        if "*" in file_:
            selected = glob(file_)
            source_files.extend(selected)
        elif os.path.isfile(file_):
            source_files.append(file_)

    if destpath.endswith("/") or os.path.isdir(destpath) or len(sources) > 1:
        # -- DESTDIR-MODE: Last argument is a directory.
        destdir = destpath
    else:
        # -- DESTFILE-MODE: Copy (and rename) one file.
        assert len(source_files) == 1
        destdir = os.path.dirname(destpath)

    # -- WORK-HORSE: Copy one or more files to destpath.
    if not os.path.isdir(destdir):
        sys.stdout.write("copy: Create dir %s\n" % destdir)
        os.makedirs(destdir)
    for source in source_files:
        destname = os.path.join(destdir, os.path.basename(source))
        sys.stdout.write("copy: %s => %s\n" % (source, destname))
        shutil.copy(source, destname)
    return 0


def setup_parser_copy(parser):
    parser.add_argument("sources", nargs="+", help="Source files.")
    parser.add_argument("destpath", help="Destination path")


command_copy.usage = "%(prog)s sources... destpath"
command_copy.short = "Copy one or more source files to a destinition."
command_copy.setup_parser = setup_parser_copy


# -----------------------------------------------------------------------------
# SUBCOMMAND: mkdir
# -----------------------------------------------------------------------------
def command_mkdir(args):
    """
    Create a non-existing directory (or more ...).
    If the directory exists, the step is skipped.
    Similar to the UNIX command: 'mkdir -p dir'
    """
    errors = 0
    for directory in args.dirs:
        if os.path.exists(directory):
            if not os.path.isdir(directory):
                # -- SANITY CHECK: directory exists, but as file...
                sys.stdout.write("mkdir: %s\n" % directory)
                sys.stdout.write("ERROR: Exists already, but as file...\n")
                errors += 1
        else:
            # -- NORMAL CASE: Directory does not exits yet.
            assert not os.path.isdir(directory)
            sys.stdout.write("mkdir: %s\n" % directory)
            os.makedirs(directory)
    return errors


def setup_parser_mkdir(parser):
    parser.add_argument("dirs", nargs="+", help="Directory(s)")

command_mkdir.usage = "%(prog)s dir..."
command_mkdir.short = "Create non-existing directory (or more...)."
command_mkdir.setup_parser = setup_parser_mkdir

# -----------------------------------------------------------------------------
# SUBCOMMAND: py2to3
# -----------------------------------------------------------------------------
command_py2to4_work_around3k = True
def command_py2to3(args):
    """
    Apply '2to3' tool (Python2 to Python3 conversion tool) to Python sources.
    """
    from lib2to3.main import main
    args2 = []
    if command_py2to4_work_around3k:
        if args.no_diffs:
            args2.append("--no-diffs")
        if args.write:
            args2.append("-w")
        if args.nobackups:
            args2.append("-n")
    args2.extend(args.sources)
    sys.exit(main("lib2to3.fixes", args=args2))


def setup_parser4py2to3(parser):
    if command_py2to4_work_around3k:
        parser.add_argument("--no-diffs", action="store_true",
                          help="Don't show diffs of the refactoring")
        parser.add_argument("-w", "--write", action="store_true",
                          help="Write back modified files")
        parser.add_argument("-n", "--nobackups", action="store_true", default=False,
                          help="Don't write backups for modified files.")
    parser.add_argument("sources", nargs="+", help="Source files.")


command_py2to3.name = "2to3"
command_py2to3.usage = "%(prog)s sources..."
command_py2to3.short = "Apply python's 2to3 tool to Python sources."
command_py2to3.setup_parser = setup_parser4py2to3


# -----------------------------------------------------------------------------
# COMMAND HELPERS/UTILS:
# -----------------------------------------------------------------------------
def discover_commands():
    commands = []
    for name, func in inspect.getmembers(inspect.getmodule(toxcmd_main)):
        if name.startswith("__"):
            continue
        if name.startswith("command_") and isinstance(func, collections.Callable):
            command_name0 = name.replace("command_", "")
            command_name = getattr(func, "name", command_name0)
            commands.append(Command(command_name, func))
    return commands


class Command(object):
    def __init__(self, name, func):
        assert isinstance(name, str)
        assert isinstance(func, collections.Callable)
        self.name = name
        self.func = func
        self.parser = None

    def setup_parser(self, command_parser):
        setup_parser = getattr(self.func, "setup_parser", None)
        if setup_parser and isinstance(setup_parser, collections.Callable):
            setup_parser(command_parser)
        else:
            command_parser.add_argument("args", nargs="*")

    @property
    def usage(self):
        usage = getattr(self.func, "usage", None)
        return usage

    @property
    def short_description(self):
        short_description = getattr(self.func, "short", "")
        return short_description

    @property
    def description(self):
        return inspect.getdoc(self.func)

    def __call__(self, args):
        return self.func(args)


# -----------------------------------------------------------------------------
# MAIN-COMMAND:
# -----------------------------------------------------------------------------
def toxcmd_main(args=None):
    """Command util with subcommands for tox environments."""
    usage = "USAGE: %(prog)s [OPTIONS] COMMAND args..."
    if args is None:
        args = sys.argv[1:]

    # -- STEP: Build command-line parser.
    parser = argparse.ArgumentParser(description=inspect.getdoc(toxcmd_main),
                                     formatter_class=FORMATTER_CLASS)
    common_parser = parser.add_argument_group("Common options")
    common_parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(help="commands")
    for command in discover_commands():
        command_parser = subparsers.add_parser(command.name,
                                               usage=command.usage,
                                               description=command.description,
                                               help=command.short_description,
                                               formatter_class=FORMATTER_CLASS)
        command_parser.set_defaults(func=command)
        command.setup_parser(command_parser)
        command.parser = command_parser

    # -- STEP: Process command-line and run command.
    options = parser.parse_args(args)
    command_function = options.func
    return command_function(options)


# -----------------------------------------------------------------------------
# MAIN:
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(toxcmd_main())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# behave documentation build configuration file, created by
# sphinx-quickstart on Tue Nov 29 16:33:26 2011.
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
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinxcontrib.cheeseshop",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'behave'
authors = u'Benno Rice, Richard Jones and Jens Engel'
copyright = u'2012-2013, %s' % authors

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from behave import __version__
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

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

extlinks = {
    "pypi": ("https://pypi.python.org/pypi/%s", ""),
    "github": ("https://github.com/%s", "github:/"),
    "issue":  ("https://github.com/behave/behave/issue/%s", "issue #"),
}

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'kr'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

# agogo options:
# headerfont (CSS font family): Font for headings.
# pagewidth (CSS length): Width of the page content, default 70em.
# documentwidth (CSS length): Width of the document (without sidebar), default 50em.
# sidebarwidth (CSS length): Width of the sidebar, default 20em.
# bgcolor (CSS color): Background color.
# headerbg (CSS value for “background”): background for the header area, default a grayish gradient.
# footerbg (CSS value for “background”): background for the footer area, default a light gray gradient.
# linkcolor (CSS color): Body link color.
# headercolor1, headercolor2 (CSS color): colors for <h1> and <h2> headings.
# headerlinkcolor (CSS color): Color for the backreference link in headings.
# textalign (CSS text-align value): Text alignment for the body, default is justify.

html_theme_options = {
 #'bodyfont': '"Ubuntu", sans-serif', # (CSS font family): Font for normal text.
  #'github_fork': 'behave/behave'
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/behave_logo.png"

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
htmlhelp_basename = 'behavedoc'


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
  ('index', 'behave.tex', u'behave Documentation', authors, 'manual'),
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
    ('index', 'behave', u'behave Documentation', [authors], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'behave', u'behave Documentation', authors,
   'behave', 'A test runner for behave (feature tests).', 'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = update_behave_rst
#!/usr/bin/env python

import re
import sys
import conf
import textwrap

sys.argv[0] = 'behave'

from behave import configuration
from behave import __main__

with open('behave.rst-template') as f:
    template = f.read()

#cmdline = configuration.parser.format_help()

config = []
cmdline = []
for fixed, keywords in configuration.options:
    skip = False
    if 'dest' in keywords:
        dest = keywords['dest']
    else:
        for opt in fixed:
            if opt.startswith('--no'):
                skip = True
            if opt.startswith('--'):
                dest = opt[2:].replace('-', '_')
            else:
                assert len(opt) == 2
                dest = opt[1:]

    text = re.sub(r'\s+', ' ', keywords['help']).strip()
    text = text.replace('%%', '%')
    text = textwrap.fill(text, 70, initial_indent='   ', subsequent_indent='   ')
    if fixed:
        # -- COMMAND-LINE OPTIONS (CONFIGFILE only have empty fixed):
        cmdline.append('**%s**\n%s' % (', '.join(fixed), text))

    if skip or dest in 'tags_help lang_list lang_help version'.split():
        continue

    action = keywords.get('action', 'store')
    if action == 'store':
        type = 'text'
    elif action in ('store_true','store_false'):
        type = 'boolean'
    elif action == 'append':
        type = 'text (multiple allowed)'
    else:
        raise ValueError('unknown action %s' % action)

    text = re.sub(r'\s+', ' ', keywords.get('config_help', keywords['help'])).strip()
    text = text.replace('%%', '%')
    text = textwrap.fill(text, 70, initial_indent='   ', subsequent_indent='   ')
    config.append('**%s** -- %s\n%s' % (dest, type, text))


values = dict(
    cmdline='\n'.join(cmdline),
    tag_expression=__main__.TAG_HELP,
    config='\n'.join(config),
)

with open('behave.rst', 'w') as f:
    f.write(template.format(**values))

########NEW FILE########
__FILENAME__ = environment
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
# HOOKS:
# -----------------------------------------------------------------------------
def before_all(context):
    setup_context_with_global_params_test(context)

# -----------------------------------------------------------------------------
# SPECIFIC FUNCTIONALITY:
# -----------------------------------------------------------------------------
def setup_context_with_global_params_test(context):
    context.global_name = "env:Alice"
    context.global_age  = 12

########NEW FILE########
__FILENAME__ = behave_context_steps
# -*- coding: utf-8 -*-
"""
Step definition for Context object tests.

EXAMPLE
    Scenario: Show that Context parameter
      Given I set the parameter "person" to "Alice" in the behave context
      Then the behave context should have a parameter named "person"
      And  the behave context object should contain:
        | Parameter | Value   |
        | person    | "Alice" |

    Scenario: Show that Context parameter are not present in next scenario
      Then the behave context should not have a parameter named "person"
"""

from behave import given, when, then, step
from hamcrest import assert_that, equal_to

# -----------------------------------------------------------------------------
# STEPS:
# -----------------------------------------------------------------------------
@step(u'I set the context parameter "{param_name}" to "{value}"')
def step_set_behave_context_parameter_to(context, param_name, value):
    setattr(context, param_name, value)

@step(u'the parameter "{param_name}" exists in the behave context')
def step_behave_context_parameter_exists(context, param_name):
    assert hasattr(context, param_name)

@step(u'the parameter "{param_name}" does not exist in the behave context')
def step_behave_context_parameter_not_exists(context, param_name):
    assert not hasattr(context, param_name)

@given(u'the behave context has a parameter "{param_name}"')
def given_behave_context_has_parameter_named(context, param_name):
    step_behave_context_parameter_exists(context, param_name)

@given(u'the behave context does not have a parameter "{param_name}"')
def given_behave_context_does_not_have_parameter_named(context, param_name):
    step_behave_context_parameter_not_exists(context, param_name)

@step(u'the behave context should have a parameter "{param_name}"')
def step_behave_context_should_have_parameter_named(context, param_name):
    step_behave_context_parameter_exists(context, param_name)

@step(u'the behave context should not have a parameter "{param_name}"')
def step_behave_context_should_not_have_parameter_named(context, param_name):
    step_behave_context_parameter_not_exists(context, param_name)

@then(u'the behave context should contain')
def then_behave_context_should_contain_with_table(context):
    assert context.table, "ENSURE: table is provided."
    for row in context.table.rows:
        param_name  = row["Parameter"]
        param_value = row["Value"]
        if param_value.startswith('"') and param_value.endswith('"'):
            param_value = param_value[1:-1]
        actual = str(getattr(context, param_name, None))
        assert hasattr(context, param_name)
        assert_that(actual, equal_to(param_value))

@given(u'the behave context contains')
def given_behave_context_contains_with_table(context):
    then_behave_context_should_contain_with_table(context)
########NEW FILE########
__FILENAME__ = behave_model_tag_logic_steps
# -*- coding: utf-8 -*-
"""
Provides step definitions that test tag logic for selected features, scenarios.

.. code-block:: Gherkin

    # -- Scenario: Select scenarios with tags
    Given I use the behave model builder with:
        | statement  | name   | tags      | Comment |
        | Scenario   | A1     | @foo      |          |
        | Scenario   | A3     | @foo @bar |          |
        | Scenario   | B3     |           | Untagged |
    When I run the behave with tags
    Then the following scenarios are selected with cmdline:
        | cmdline                    | selected           | Logic comment |
        | --tags=@foo                | A1, A3, B2         | @foo          |
        | --tags=-@foo               | A1, A3, B2         | @foo          |

.. code-block:: Gherkin

    # IDEA:
    # -- Scenario: Select scenarios with tags
    Given I use the behave model builder with:
        | statement  | name   | tags      | Comment |
        | Feature    | Alice  | @alice    |          |
        | Scenario   | A1     | @foo      |          |
        | Scenario   | A2     | @bar      |          |
        | Scenario   | A3     | @foo @bar |          |
        | Feature    | Bob    | @bob      |          |
        | Scenario   | B1     | @bar      |          |
        | Scenario   | B2     | @foo      |          |
        | Scenario   | B3     |           | Untagged |
    When I run the behave with options "--tags=@foo"
    Then the following scenarios are selected:
        | statement  | name   | selected  |
        | Scenario   | A1     | yes       |
        | Scenario   | A2     | no        |
        | Scenario   | A3     | yes       |
        | Scenario   | B1     | no        |
        | Scenario   | B2     | yes       |
        | Scenario   | B3     | no        |
"""

from behave import given, when, then
from behave_model_util import BehaveModelBuilder, convert_comma_list
from behave_model_util import \
    run_model_with_cmdline, collect_selected_and_skipped_scenarios
from hamcrest import assert_that, equal_to


# -----------------------------------------------------------------------------
# STEP DEFINITIONS:
# -----------------------------------------------------------------------------
@given('a behave model with')
def step_given_a_behave_model_with_table(context):
    """
    Build a behave feature model from a tabular description.

    .. code-block:: gherkin

        # -- Scenario: Select scenarios with tags
        Given I use the behave model builder with:
            | statement  | name   | tags      | Comment |
            | Scenario   | S0     |           | Untagged |
            | Scenario   | S1     | @foo      |          |
            | Scenario   | S3     | @foo @bar |          |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(BehaveModelBuilder.REQUIRED_COLUMNS)
    model_builder = BehaveModelBuilder()
    context.behave_model = model_builder.build_model_from_table(context.table)


@when('I run the behave model with "{hint}"')
def step_when_run_behave_model_with_hint(context, hint):
    pass    # -- ONLY: SYNTACTIC SUGAR


@then('the following scenarios are selected with cmdline')
def step_then_scenarios_are_selected_with_cmdline(context):
    """
    .. code-block:: Gherkin

        Then the following scenarios are selected with cmdline:
            | cmdline      | selected?    | Logic comment |
            | --tags=@foo  | A1, A3, B2   | @foo          |
    """
    assert context.behave_model, "REQUIRE: context attribute"
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["cmdline", "selected?"])

    model = context.behave_model
    for row_index, row in enumerate(context.table.rows):
        cmdline = row["cmdline"]
        expected_selected_names = convert_comma_list(row["selected?"])

        # -- STEP: Run model with cmdline tags
        run_model_with_cmdline(model, cmdline)
        selected, skipped = collect_selected_and_skipped_scenarios(model)
        actual_selected = [scenario.name  for scenario in selected]

        # -- CHECK:
        assert_that(actual_selected, equal_to(expected_selected_names),
                    "cmdline=%s (row=%s)" % (cmdline, row_index))

########NEW FILE########
__FILENAME__ = behave_model_util
# -*- coding: utf-8 -*-

from behave.model import reset_model, Feature, Scenario
from behave.runner import ModelRunner
from behave.parser import parse_tags
from behave.configuration import Configuration


# -----------------------------------------------------------------------------
# TYPE CONVERTERS:
# -----------------------------------------------------------------------------
def convert_comma_list(text):
    text = text.strip()
    return [part.strip()  for part in text.split(",")]

def convert_model_element_tags(text):
    return parse_tags(text.strip())


# -----------------------------------------------------------------------------
# TEST DOMAIN, FIXTURES, STEP UTILS:
# -----------------------------------------------------------------------------
class Model(object):
    def __init__(self, features=None):
        self.features = features or []

class BehaveModelBuilder(object):
    REQUIRED_COLUMNS = ["statement", "name"]
    OPTIONAL_COLUMNS = ["tags"]

    def __init__(self):
        self.features = []
        self.current_feature = None
        self.current_scenario = None

    def build_feature(self, name=u"", tags=None):
        if not name:
            name = u"alice"
        filename = u"%s.feature" % name
        line = 1
        feature = Feature(filename, line, u"Feature", name, tags=tags)
        self.features.append(feature)
        self.current_feature = feature
        return feature

    def build_scenario(self, name="", tags=None):
        if not self.current_feature:
            self.build_feature()
        filename = self.current_feature.filename
        line = self.current_feature.line + 1
        scenario = Scenario(filename, line, u"Scenario", name, tags=tags)
        self.current_feature.add_scenario(scenario)
        self.current_scenario = scenario
        return scenario

    def build_unknown(self, statement, name=u"", row_index=None):
        assert False, u"UNSUPPORTED: statement=%s, name=%s (row=%s)" % \
                      (statement, name, row_index)

    def build_model_from_table(self, table):
        table.require_columns(self.REQUIRED_COLUMNS)
        for row_index, row in enumerate(table.rows):
            statement = row["statement"]
            name = row["name"]
            tags = row.get("tags", [])
            if tags:
                tags = convert_model_element_tags(tags)

            if statement == "Feature":
                self.build_feature(name, tags)
            elif statement == "Scenario":
                self.build_scenario(name, tags)
            else:
                self.build_unknown(statement, name, row_index=row_index)
        return Model(self.features)

def run_model_with_cmdline(model, cmdline):
    reset_model(model.features)
    command_args = cmdline
    config = Configuration(command_args,
                           load_config=False,
                            default_format="null",
                            stdout_capture=False,
                            stderr_capture=False,
                            log_capture=False)
    model_runner = ModelRunner(config, model.features)
    return model_runner.run()

def collect_selected_and_skipped_scenarios(model):
    selected = []
    skipped = []
    for feature in model.features:
        scenarios = feature.scenarios
        for scenario in scenarios:
            if scenario.status == "skipped":
                skipped.append(scenario)
            else:
                assert scenario.status != "untested"
                selected.append(scenario)
    return (selected, skipped)



########NEW FILE########
__FILENAME__ = behave_select_files_steps
# -*- coding: utf-8 -*-
"""
Provides step definitions that test how the behave runner selects feature files.

EXAMPLE:
    Given behave has the following feature fileset:
      '''
      features/alice.feature
      features/bob.feature
      features/barbi.feature
      '''
    When behave includes feature files with "features/a.*\.feature"
    And  behave excludes feature files with "features/b.*\.feature"
    Then the following feature files are selected:
      '''
      features/alice.feature
      '''
"""

from behave import given, when, then
from behave.runner_util import FeatureListParser
from hamcrest import assert_that, equal_to
from copy import copy
import re

# -----------------------------------------------------------------------------
# STEP UTILS:
# -----------------------------------------------------------------------------
class BasicBehaveRunner(object):
    def __init__(self, config=None):
        self.config = config
        self.feature_files = []

    def select_files(self):
        """
        Emulate behave runners file selection by using include/exclude patterns.
        :return: List of selected feature filenames.
        """
        selected = []
        for filename in self.feature_files:
            if not self.config.exclude(filename):
                selected.append(str(filename))
        return selected

# -----------------------------------------------------------------------------
# STEP DEFINITIONS:
# -----------------------------------------------------------------------------
@given('behave has the following feature fileset')
def step_given_behave_has_feature_fileset(context):
    assert context.text is not None, "REQUIRE: text"
    behave_runner = BasicBehaveRunner(config=copy(context.config))
    behave_runner.feature_files = FeatureListParser.parse(context.text)
    context.behave_runner = behave_runner

@when('behave includes all feature files')
def step_when_behave_includes_all_feature_files(context):
    assert context.behave_runner, "REQUIRE: context.behave_runner"
    context.behave_runner.config.include_re = None

@when('behave includes feature files with "{pattern}"')
def step_when_behave_includes_feature_files_with_pattern(context, pattern):
    assert context.behave_runner, "REQUIRE: context.behave_runner"
    context.behave_runner.config.include_re = re.compile(pattern)

@when('behave excludes no feature files')
def step_when_behave_excludes_no_feature_files(context):
    assert context.behave_runner, "REQUIRE: context.behave_runner"
    context.behave_runner.config.exclude_re = None

@when('behave excludes feature files with "{pattern}"')
def step_when_behave_excludes_feature_files_with_pattern(context, pattern):
    assert context.behave_runner, "REQUIRE: context.behave_runner"
    context.behave_runner.config.exclude_re = re.compile(pattern)

@then('the following feature files are selected')
def step_then_feature_files_are_selected_with_text(context):
    assert context.text is not None, "REQUIRE: text"
    assert context.behave_runner, "REQUIRE: context.behave_runner"
    selected_files = context.text.strip().splitlines()
    actual_files = context.behave_runner.select_files()
    assert_that(actual_files, equal_to(selected_files))

########NEW FILE########
__FILENAME__ = behave_tag_expression_steps
# -*- coding: utf-8 -*-
"""
Provides step definitions that test tag expressions (and tag logic).

.. code-block:: gherkin

    Given the tag expression "@foo"
    Then the tag expression selects elements with tags:
        | tags         | selected? |
        | @foo         |   yes     |
        | @other       |   no      |

.. code-block:: gherkin

    Given the named model elements with tags:
        | name | tags   |
        | S1   | @foo   |
    Then the tag expression select model elements with:
        | tag expression | selected?    |
        |  @foo          | S1, S3       |
        | -@foo          | S0, S2, S3   |
"""

from behave import given, then, register_type
from behave.tag_expression import TagExpression
from behave_model_util import convert_comma_list, convert_model_element_tags
from hamcrest import assert_that, equal_to


# -----------------------------------------------------------------------------
# TEST DOMAIN, FIXTURES, STEP UTILS:
# -----------------------------------------------------------------------------
class ModelElement(object):
    def __init__(self, name, tags=None):
        self.name = name
        self.tags = tags or []

# -----------------------------------------------------------------------------
# TYPE CONVERTERS:
# -----------------------------------------------------------------------------
def convert_tag_expression(text):
    parts = text.strip().split()
    return TagExpression(parts)
register_type(TagExpression=convert_tag_expression)

def convert_yesno(text):
    text = text.strip().lower()
    assert text in convert_yesno.choices
    return text in convert_yesno.true_choices
convert_yesno.choices = ("yes", "no", "true", "false")
convert_yesno.true_choices = ("yes", "true")


# -----------------------------------------------------------------------------
# STEP DEFINITIONS:
# -----------------------------------------------------------------------------
@given('the tag expression "{tag_expression:TagExpression}"')
def step_given_the_tag_expression(context, tag_expression):
    """
    Define a tag expression that is used later-on.

    .. code-block:: gherkin

        Given the tag expression "@foo"
    """
    context.tag_expression = tag_expression

@then('the tag expression selects elements with tags')
def step_then_tag_expression_selects_elements_with_tags(context):
    """
    Checks if a tag expression selects an element with the given tags.

    .. code-block:: gherkin
        Then the tag expression selects elements with tags:
            | tags         | selected? |
            | @foo         |   yes     |
            | @other       |   no      |
    """
    assert context.tag_expression, "REQUIRE: context.tag_expression"
    context.table.require_columns(["tags", "selected?"])
    tag_expression = context.tag_expression
    expected = []
    actual   = []
    for row in context.table.rows:
        element_tags = convert_model_element_tags(row["tags"])
        expected_element_selected = convert_yesno(row["selected?"])
        actual_element_selected = tag_expression.check(element_tags)
        expected.append((element_tags, expected_element_selected))
        actual.append((element_tags, actual_element_selected))

    # -- PERFORM CHECK:
    assert_that(actual, equal_to(expected))


@given('the model elements with name and tags')
def step_given_named_model_elements_with_tags(context):
    """
    .. code-block:: gherkin

        Given the model elements with name and tags:
            | name | tags   |
            | S1   | @foo   |
        Then the tag expression select model elements with:
            | tag expression | selected?    |
            |  @foo          | S1, S3       |
            | -@foo          | S0, S2, S3   |
    """
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["name", "tags"])

    # -- PREPARE:
    model_element_names = set()
    model_elements = []
    for row in context.table.rows:
        name = row["name"].strip()
        tags = convert_model_element_tags(row["tags"])
        assert name not in model_element_names, "DUPLICATED: name=%s" % name
        model_elements.append(ModelElement(name, tags=tags))
        model_element_names.add(name)

    # -- SETUP:
    context.model_elements = model_elements


@then('the tag expression selects model elements with')
def step_given_named_model_elements_with_tags(context):
    """
    .. code-block:: gherkin

        Then the tag expression select model elements with:
            | tag expression | selected?    |
            |  @foo          | S1, S3       |
            | -@foo          | S0, S2, S3   |
    """
    assert context.model_elements, "REQUIRE: context attribute"
    assert context.table, "REQUIRE: context.table"
    context.table.require_columns(["tag expression", "selected?"])

    for row_index, row in enumerate(context.table.rows):
        tag_expression_text = row["tag expression"]
        tag_expression = convert_tag_expression(tag_expression_text)
        expected_selected_names = convert_comma_list(row["selected?"])

        actual_selected = []
        for model_element in context.model_elements:
            if tag_expression.check(model_element.tags):
                actual_selected.append(model_element.name)

        assert_that(actual_selected, equal_to(expected_selected_names),
            "tag_expression=%s (row=%s)" % (tag_expression_text, row_index))

########NEW FILE########
__FILENAME__ = behave_undefined_steps
# -*- coding -*-
"""
Provides step definitions for behave based on behave4cmd.

REQUIRES:
  * behave4cmd.steplib.output steps (command output from behave).
"""

from behave import given, when, then, step
from behave.runner_util import make_undefined_step_snippet


# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS:
# -----------------------------------------------------------------------------
def text_indent(text, indent_size=0):
    prefix = " " * indent_size
    return prefix.join(text.splitlines(True))


# -----------------------------------------------------------------------------
# STEPS FOR: Undefined step definitions
# -----------------------------------------------------------------------------
@then(u'an undefined-step snippets section exists')
def step_undefined_step_snippets_section_exists(context):
    """
    Checks if an undefined-step snippet section is in behave command output.
    """
    context.execute_steps(u'''
        Then the command output should contain:
            """
            You can implement step definitions for undefined steps with these snippets:
            """
    ''')

@then(u'an undefined-step snippet should exist for "{step}"')
def step_undefined_step_snippet_should_exist_for(context, step):
    """
    Checks if an undefined-step snippet is provided for a step
    in behave command output (last command).

    EXAMPLE:
        Then an undefined-step snippet should exist for "Given an undefined step"
    """
    undefined_step_snippet  = make_undefined_step_snippet(step)
    context.execute_steps(u'''\
Then the command output should contain:
    """
    {undefined_step_snippet}
    """
    '''.format(undefined_step_snippet=text_indent(undefined_step_snippet, 4)))


@then(u'an undefined-step snippet should not exist for "{step}"')
def step_undefined_step_snippet_should_not_exist_for(context, step):
    """
    Checks if an undefined-step snippet is provided for a step
    in behave command output (last command).
    """
    undefined_step_snippet  = make_undefined_step_snippet(step)
    context.execute_steps(u'''\
Then the command output should not contain:
    """
    {undefined_step_snippet}
    """
    '''.format(undefined_step_snippet=text_indent(undefined_step_snippet, 4)))


@then(u'undefined-step snippets should exist for')
def step_undefined_step_snippets_should_exist_for_table(context):
    """
    Checks if undefined-step snippets are provided.

    EXAMPLE:
        Then undefined-step snippets should exist for:
            | Step |
            | When an undefined step is used |
            | Then another undefined step is used |
    """
    assert context.table, "REQUIRES: table"
    for row in context.table.rows:
        step = row["Step"]
        step_undefined_step_snippet_should_exist_for(context, step)


@then(u'undefined-step snippets should not exist for')
def step_undefined_step_snippets_should_not_exist_for_table(context):
    """
    Checks if undefined-step snippets are not provided.

    EXAMPLE:
        Then undefined-step snippets should not exist for:
            | Step |
            | When an known step is used |
            | Then another known step is used |
    """
    assert context.table, "REQUIRES: table"
    for row in context.table.rows:
        step = row["Step"]
        step_undefined_step_snippet_should_not_exist_for(context, step)

########NEW FILE########
__FILENAME__ = use_steplib_behave4cmd
# -*- coding: utf-8 -*-
"""
Use behave4cmd0 step library (predecessor of behave4cmd).
"""

# -- REGISTER-STEPS:
import behave4cmd0.__all_steps__
import behave4cmd0.passing_steps
import behave4cmd0.failing_steps

########NEW FILE########
__FILENAME__ = ansi_steps
# -*- coding: utf-8 -*-
from behave import then
from behave4cmd0.command_steps import \
    step_command_output_should_contain_text, \
    step_command_output_should_not_contain_text

# -- CONSTANTS:
# ANSI CONTROL SEQUENCE INTRODUCER (CSI).
CSI = u"\x1b["

@then(u'the command output should contain ANSI escape sequences')
def step_command_ouput_should_not_contain_ansi_sequences(context):
    step_command_output_should_contain_text(context, CSI)

@then(u'the command output should not contain any ANSI escape sequences')
def step_command_ouput_should_not_contain_ansi_sequences(context):
    step_command_output_should_not_contain_text(context, CSI)


########NEW FILE########
__FILENAME__ = behave_hooks_steps
# -*- coding: utf-8 -*-
from behave import then

@then('the behave hook "{hook}" was called')
def step_behave_hook_was_called(context, hook):
    substeps = u'Then the command output should contain "hooks.{0}: "'.format(hook)
    context.execute_steps(substeps)


########NEW FILE########
__FILENAME__ = use_steplib_behave4cmd
# -*- coding: utf-8 -*-
"""
Use behave4cmd0 step library (predecessor of behave4cmd).
"""

# -- REGISTER-STEPS:
# import behave4cmd0.__all_steps__
import behave4cmd0.command_steps
import behave4cmd0.passing_steps
import behave4cmd0.failing_steps
import behave4cmd0.note_steps

########NEW FILE########
__FILENAME__ = use_steplib_behave4cmd
# -*- coding: utf-8 -*-
"""
Use behave4cmd0 step library (predecessor of behave4cmd).
"""

# -- REGISTER-STEPS:
import behave4cmd0.__all_steps__

########NEW FILE########
__FILENAME__ = test_summary
from mock import Mock, patch
from nose.tools import *

from behave.model import ScenarioOutline, Scenario
from behave.reporter.summary import SummaryReporter, format_summary

class TestFormatStatus(object):
    def test_passed_entry_contains_label(self):
        summary = {
            'passed': 1,
            'skipped': 0,
            'failed': 0,
            'undefined': 0,
        }

        assert format_summary('fnord', summary).startswith('1 fnord passed')

    def test_passed_entry_is_pluralised(self):
        summary = {
            'passed': 10,
            'skipped': 0,
            'failed': 0,
            'undefined': 0,
        }

        assert format_summary('fnord', summary).startswith('10 fnords passed')

    def test_remaining_fields_are_present(self):
        summary = {
            'passed': 10,
            'skipped': 1,
            'failed': 2,
            'undefined': 3,
        }

        output = format_summary('fnord', summary)

        assert '1 skipped' in output
        assert '2 failed' in output
        assert '3 undefined' in output

    def test_missing_fields_are_not_present(self):
        summary = {
            'passed': 10,
            'skipped': 1,
            'failed': 2,
        }

        output = format_summary('fnord', summary)

        assert '1 skipped' in output
        assert '2 failed' in output
        assert 'undefined' not in output

class TestSummaryReporter(object):
    @patch('sys.stdout')
    def test_duration_is_totalled_up_and_outputted(self, stdout):
        features = [Mock(), Mock(), Mock(), Mock()]
        features[0].duration = 1.9
        features[0].status = 'passed'
        features[0].__iter__ = Mock(return_value=iter([]))
        features[1].duration = 2.7
        features[1].status = 'passed'
        features[1].__iter__ = Mock(return_value=iter([]))
        features[2].duration = 3.5
        features[2].status = 'passed'
        features[2].__iter__ = Mock(return_value=iter([]))
        features[3].duration = 4.3
        features[3].status = 'passed'
        features[3].__iter__ = Mock(return_value=iter([]))

        config = Mock()
        reporter = SummaryReporter(config)

        [reporter.feature(f) for f in features]
        eq_(round(reporter.duration, 3), 12.400)

        reporter.end()
        output = stdout.write.call_args_list[-1][0][0]
        minutes = int(reporter.duration / 60)
        seconds = reporter.duration % 60

        assert '%dm' % (minutes,) in output
        assert '%02.1f' % (seconds,) in output

    @patch('sys.stdout')
    @patch('behave.reporter.summary.format_summary')
    def test_feature_status_is_collected_and_reported(self, format_summary,
                                                      stdout):
        features = [Mock(), Mock(), Mock(), Mock(), Mock()]
        features[0].duration = 1.9
        features[0].status = 'passed'
        features[0].__iter__ = Mock(return_value=iter([]))
        features[1].duration = 2.7
        features[1].status = 'failed'
        features[1].__iter__ = Mock(return_value=iter([]))
        features[2].duration = 3.5
        features[2].status = 'skipped'
        features[2].__iter__ = Mock(return_value=iter([]))
        features[3].duration = 4.3
        features[3].status = 'passed'
        features[3].__iter__ = Mock(return_value=iter([]))
        features[4].duration = 5.1
        features[4].status = None
        features[4].__iter__ = Mock(return_value=iter([]))

        config = Mock()
        reporter = SummaryReporter(config)

        [reporter.feature(f) for f in features]
        reporter.end()

        expected = {
            'passed': 2,
            'failed': 1,
            'skipped': 2,
            'untested': 0,
        }

        eq_(format_summary.call_args_list[0][0], ('feature', expected))

    @patch('sys.stdout')
    @patch('behave.reporter.summary.format_summary')
    def test_scenario_status_is_collected_and_reported(self, format_summary,
                                                       stdout):
        feature = Mock()
        scenarios = [Mock(), Mock(), Mock(), Mock(), Mock()]
        scenarios[0].status = 'failed'
        scenarios[0].__iter__ = Mock(return_value=iter([]))
        scenarios[1].status = 'failed'
        scenarios[1].__iter__ = Mock(return_value=iter([]))
        scenarios[2].status = 'skipped'
        scenarios[2].__iter__ = Mock(return_value=iter([]))
        scenarios[3].status = 'passed'
        scenarios[3].__iter__ = Mock(return_value=iter([]))
        scenarios[4].status = None
        scenarios[4].__iter__ = Mock(return_value=iter([]))
        feature.status = 'failed'
        feature.duration = 12.3
        feature.__iter__ = Mock(return_value=iter(scenarios))

        config = Mock()
        reporter = SummaryReporter(config)

        reporter.feature(feature)
        reporter.end()

        expected = {
            'passed': 1,
            'failed': 2,
            'skipped': 2,
            'untested': 0,
        }

        eq_(format_summary.call_args_list[1][0], ('scenario', expected))

    @patch('behave.reporter.summary.format_summary')
    @patch('sys.stdout')
    def test_scenario_outline_status_is_collected_and_reported(self, stdout,
                                                               format_summary):
        feature = Mock()
        scenarios = [ ScenarioOutline(u"<string>", 0, u"scenario_outline", u"name"),
                      Mock(), Mock(), Mock() ]
        subscenarios = [ Mock(), Mock(), Mock(), Mock() ]
        subscenarios[0].status = 'passed'
        subscenarios[0].__iter__ = Mock(return_value=iter([]))
        subscenarios[1].status = 'failed'
        subscenarios[1].__iter__ = Mock(return_value=iter([]))
        subscenarios[2].status = 'failed'
        subscenarios[2].__iter__ = Mock(return_value=iter([]))
        subscenarios[3].status = 'skipped'
        subscenarios[3].__iter__ = Mock(return_value=iter([]))
        scenarios[0]._scenarios = subscenarios
        scenarios[1].status = 'failed'
        scenarios[1].__iter__ = Mock(return_value=iter([]))
        scenarios[2].status = 'skipped'
        scenarios[2].__iter__ = Mock(return_value=iter([]))
        scenarios[3].status = 'passed'
        scenarios[3].__iter__ = Mock(return_value=iter([]))
        feature.status = 'failed'
        feature.duration = 12.4
        feature.__iter__ = Mock(return_value=iter(scenarios))

        config = Mock()
        reporter = SummaryReporter(config)

        reporter.feature(feature)
        reporter.end()

        expected = {
            'passed': 2,
            'failed': 3,
            'skipped': 2,
            'untested': 0,
            }

        eq_(format_summary.call_args_list[1][0], ('scenario', expected))

    @patch('sys.stdout')
    @patch('behave.reporter.summary.format_summary')
    def test_step_status_is_collected_and_reported(self, format_summary,
                                                   stdout):
        feature = Mock()
        scenario = Mock()
        steps = [Mock(), Mock(), Mock(), Mock(), Mock()]
        steps[0].status = 'failed'
        steps[0].__iter__ = Mock(return_value=iter([]))
        steps[1].status = 'undefined'
        steps[1].__iter__ = Mock(return_value=iter([]))
        steps[2].status = 'passed'
        steps[2].__iter__ = Mock(return_value=iter([]))
        steps[3].status = 'passed'
        steps[3].__iter__ = Mock(return_value=iter([]))
        steps[4].status = None
        steps[4].__iter__ = Mock(return_value=iter([]))
        feature.status = 'failed'
        feature.duration = 12.3
        feature.__iter__ = Mock(return_value=iter([scenario]))
        scenario.status = 'failed'
        scenario.__iter__ = Mock(return_value=iter(steps))

        config = Mock()
        reporter = SummaryReporter(config)

        reporter.feature(feature)
        reporter.end()

        expected = {
            'passed': 2,
            'failed': 1,
            'skipped': 1,
            'untested': 0,
            'undefined': 1,
        }

        eq_(format_summary.call_args_list[2][0], ('step', expected))

########NEW FILE########
__FILENAME__ = test_ansi_escapes
# -*- coding: utf-8 -*-
# pylint: disable=C0103,R0201,W0401,W0614,W0621
#   C0103   Invalid name (setUp(), ...)
#   R0201   Method could be a function
#   W0401   Wildcard import
#   W0614   Unused import ... from wildcard import
#   W0621   Redefining name ... from outer scope

from nose import tools
from behave.formatter import ansi_escapes
import unittest

class StripEscapesTest(unittest.TestCase):
    ALL_COLORS = ansi_escapes.colors.keys()
    CURSOR_UPS = [ ansi_escapes.up(count)  for count in range(10) ]
    TEXTS = [
        u"lorem ipsum",
        u"Alice\nBob\nCharly\nDennis",
    ]

    @classmethod
    def colorize(cls, text, color):
        color_escape = ""
        if color:
            color_escape = ansi_escapes.colors[color]
        return color_escape + text + ansi_escapes.escapes["reset"]

    @classmethod
    def colorize_text(cls, text, colors=None):
        if not colors:
            colors = []
        colors_size = len(colors)
        color_index = 0
        colored_chars = []
        for char in text:
            color = colors[color_index]
            colored_chars.append(cls.colorize(char, color))
            color_index += 1
            if color_index >= colors_size:
                color_index = 0
        return "".join(colored_chars)

    def test_should_return_same_text_without_escapes(self):
        for text in self.TEXTS:
            tools.eq_(text, ansi_escapes.strip_escapes(text))

    def test_should_return_empty_string_for_any_ansi_escape(self):
        for text in ansi_escapes.colors.values():
            tools.eq_("", ansi_escapes.strip_escapes(text))
        for text in ansi_escapes.escapes.values():
            tools.eq_("", ansi_escapes.strip_escapes(text))


    def test_should_strip_color_escapes_from_text(self):
        for text in self.TEXTS:
            colored_text = self.colorize_text(text, self.ALL_COLORS)
            tools.eq_(text, ansi_escapes.strip_escapes(colored_text))
            self.assertNotEqual(text, colored_text)

            for color in self.ALL_COLORS:
                colored_text = self.colorize(text, color)
                tools.eq_(text, ansi_escapes.strip_escapes(colored_text))
                self.assertNotEqual(text, colored_text)

    def test_should_strip_cursor_up_escapes_from_text(self):
        for text in self.TEXTS:
            for cursor_up in self.CURSOR_UPS:
                colored_text = cursor_up + text + ansi_escapes.escapes["reset"]
                tools.eq_(text, ansi_escapes.strip_escapes(colored_text))
                self.assertNotEqual(text, colored_text)

########NEW FILE########
__FILENAME__ = test_configuration
from __future__ import with_statement
import os.path
import tempfile

from nose.tools import *
from behave import configuration

# one entry of each kind handled
TEST_CONFIG='''[behave]
outfiles= /absolute/path1
          relative/path2
paths = /absolute/path3
        relative/path4
tags = @foo,~@bar
       @zap
format=pretty
       tag-counter
stdout_capture=no
bogus=spam
'''

class TestConfiguration(object):

    def test_read_file(self):
        tn = tempfile.mktemp()
        tndir = os.path.dirname(tn)
        with open(tn, 'w') as f:
            f.write(TEST_CONFIG)

        d = configuration.read_configuration(tn)
        eq_(d['outfiles'], [
            os.path.normpath('/absolute/path1'),
            os.path.normpath(os.path.join(tndir, 'relative/path2')),
        ])
        eq_(d['paths'], [
            os.path.normpath('/absolute/path3'),  # -- WINDOWS-REQUIRES: normpath
            os.path.normpath(os.path.join(tndir, 'relative/path4')),
            ])
        eq_(d['format'], ['pretty', 'tag-counter'])
        eq_(d['tags'], ['@foo,~@bar', '@zap'])
        eq_(d['stdout_capture'], False)
        ok_('bogus' not in d)


########NEW FILE########
__FILENAME__ = test_formatter
import struct
import sys
import tempfile
import unittest
from mock import Mock, patch
from nose.tools import *

from behave.formatter import formatters
from behave.formatter import pretty
# from behave.formatter import tags
from behave.formatter.base import StreamOpener
from behave.model import Tag, Feature, Match, Scenario, Step


class TestGetTerminalSize(unittest.TestCase):
    def setUp(self):
        try:
            self.ioctl_patch = patch('fcntl.ioctl')
            self.ioctl = self.ioctl_patch.start()
        except ImportError:
            self.ioctl_patch = None
            self.ioctl = None
        self.zero_struct = struct.pack('HHHH', 0, 0, 0, 0)

    def tearDown(self):
        if self.ioctl_patch:
            self.ioctl_patch.stop()

    def test_windows_fallback(self):
        platform = sys.platform
        sys.platform = 'windows'

        eq_(pretty.get_terminal_size(), (80, 24))

        sys.platform = platform

    def test_termios_fallback(self):
        try:
            import termios
            return
        except ImportError:
            pass

        eq_(pretty.get_terminal_size(), (80, 24))

    def test_exception_in_ioctl(self):
        try:
            import termios
        except ImportError:
            return

        def raiser(*args, **kwargs):
            raise Exception('yeehar!')

        self.ioctl.side_effect = raiser

        eq_(pretty.get_terminal_size(), (80, 24))
        self.ioctl.assert_called_with(0, termios.TIOCGWINSZ, self.zero_struct)

    def test_happy_path(self):
        try:
            import termios
        except ImportError:
            return

        self.ioctl.return_value = struct.pack('HHHH', 17, 23, 5, 5)

        eq_(pretty.get_terminal_size(), (23, 17))
        self.ioctl.assert_called_with(0, termios.TIOCGWINSZ, self.zero_struct)

    def test_zero_size_fallback(self):
        try:
            import termios
        except ImportError:
            return

        self.ioctl.return_value = self.zero_struct

        eq_(pretty.get_terminal_size(), (80, 24))
        self.ioctl.assert_called_with(0, termios.TIOCGWINSZ, self.zero_struct)


def _tf():
    '''Open a temp file that looks a bunch like stdout.
    '''
    if sys.version_info[0] == 3:
        # in python3 it's got an encoding and accepts new-style strings
        return tempfile.TemporaryFile(mode='w', encoding='UTF-8')

    # pre-python3 it's not got an encoding and accepts encoded data
    # (old-style strings)
    return tempfile.TemporaryFile(mode='w')


class FormatterTests(unittest.TestCase):
    formatter_name = "plain"    # SANE DEFAULT, overwritten by concrete classes

    def setUp(self):
        self.config = Mock()
        self.config.color = True
        self.config.outputs = [ StreamOpener(stream=sys.stdout) ]
        self.config.format = [self.formatter_name]

    _line = 0
    @property
    def line(self):
        self._line += 1
        return self._line

    def _formatter(self, file, config):
        stream_opener = StreamOpener(stream=file)
        f = formatters.get_formatter(config, [stream_opener])[0]
        f.uri('<string>')
        return f

    def _feature(self, keyword=u'k\xe9yword', name=u'name', tags=[u'spam', u'ham'],
            location=u'location', description=[u'description'], scenarios=[],
            background=None):
        line = self.line
        tags = [Tag(name, line) for name in tags]
        return Feature('<string>', line, keyword, name, tags=tags,
            description=description, scenarios=scenarios,
            background=background)

    def _scenario(self, keyword=u'k\xe9yword', name=u'name', tags=[], steps=[]):
        line = self.line
        tags = [Tag(name, line) for name in tags]
        return Scenario('<string>', line, keyword, name, tags=tags, steps=steps)

    def _step(self, keyword=u'k\xe9yword', step_type='given', name=u'name',
              text=None, table=None):
        line = self.line
        return Step('<string>', line, keyword, step_type, name, text=text,
                    table=table)

    def _match(self, arguments=None):
        def dummy():
            pass

        return Match(dummy, arguments)

    def test_feature(self):
        # this test does not actually check the result of the formatting; it
        # just exists to make sure that formatting doesn't explode in the face of
        # unicode and stuff
        p = self._formatter(_tf(), self.config)
        f = self._feature()
        p.feature(f)

    def test_scenario(self):
        p = self._formatter(_tf(), self.config)
        f = self._feature()
        p.feature(f)
        s = self._scenario()
        p.scenario(s)

    def test_step(self):
        p = self._formatter(_tf(), self.config)
        f = self._feature()
        p.feature(f)
        s = self._scenario()
        p.scenario(s)
        s = self._step()
        p.step(s)
        p.match(self._match([]))
        s.status = u'passed'
        p.result(s)


class TestPretty(FormatterTests):
    formatter_name = 'pretty'


class TestPlain(FormatterTests):
    formatter_name = 'plain'


class TestJson(FormatterTests):
    formatter_name = 'json'


class TestTagsCount(FormatterTests):
    formatter_name = 'tags'

    def test_tag_counts(self):
        p = self._formatter(_tf(), self.config)

        s = self._scenario(tags=[u'ham', u'foo'])
        f = self._feature(scenarios=[s])  # feature.tags= ham, spam
        p.feature(f)
        p.scenario(s)

        eq_(p.tag_counts, {'ham': [ f, s ], 'spam': [ f ], 'foo': [ s ]})


class MultipleFormattersTests(FormatterTests):
    formatters = []

    def setUp(self):
        self.config = Mock()
        self.config.color = True
        self.config.outputs = [ StreamOpener(stream=sys.stdout)
                                for i in self.formatters ]
        self.config.format = self.formatters

    def _formatters(self, file, config):
        stream_opener = StreamOpener(stream=file)
        fs = formatters.get_formatter(config, [stream_opener])
        for f in fs:
            f.uri('<string>')
        return fs

    def test_feature(self):
        # this test does not actually check the result of the formatting; it
        # just exists to make sure that formatting doesn't explode in the face of
        # unicode and stuff
        ps = self._formatters(_tf(), self.config)
        f = self._feature()
        for p in ps:
            p.feature(f)

    def test_scenario(self):
        ps = self._formatters(_tf(), self.config)
        f = self._feature()
        for p in ps:
            p.feature(f)
            s = self._scenario()
            p.scenario(s)

    def test_step(self):
        ps = self._formatters(_tf(), self.config)
        f = self._feature()
        for p in ps:
            p.feature(f)
            s = self._scenario()
            p.scenario(s)
            s = self._step()
            p.step(s)
            p.match(self._match([]))
            s.status = u'passed'
            p.result(s)


class TestPrettyAndPlain(MultipleFormattersTests):
    formatters = ['pretty', 'plain']

class TestPrettyAndJSON(MultipleFormattersTests):
    formatters = ['pretty', 'json']

class TestJSONAndPlain(MultipleFormattersTests):
    formatters = ['json', 'plain']

########NEW FILE########
__FILENAME__ = test_formatter_progress
# -*- coding: utf-8 -*-
"""
Test progress formatters:
  * behave.formatter.progress.ScenarioProgressFormatter
  * behave.formatter.progress.StepProgressFormatter
"""

from __future__ import absolute_import
from .test_formatter import FormatterTests as FormatterTest
from .test_formatter import MultipleFormattersTests as MultipleFormattersTest

class TestScenarioProgressFormatter(FormatterTest):
    formatter_name = "progress"


class TestStepProgressFormatter(FormatterTest):
    formatter_name = "progress2"


class TestPrettyAndScenarioProgress(MultipleFormattersTest):
    formatters = ['pretty', 'progress']

class TestPlainAndScenarioProgress(MultipleFormattersTest):
    formatters = ['plain', 'progress']

class TestJSONAndScenarioProgress(MultipleFormattersTest):
    formatters = ['json', 'progress']

class TestPrettyAndStepProgress(MultipleFormattersTest):
    formatters = ['pretty', 'progress2']

class TestPlainAndStepProgress(MultipleFormattersTest):
    formatters = ['plain', 'progress2']

class TestJSONAndStepProgress(MultipleFormattersTest):
    formatters = ['json', 'progress2']

class TestScenarioProgressAndStepProgress(MultipleFormattersTest):
    formatters = ['progress', 'progress2']

########NEW FILE########
__FILENAME__ = test_formatter_rerun
# -*- coding: utf-8 -*-
"""
Test behave formatters:
  * behave.formatter.rerun.RerunFormatter
"""

from __future__ import absolute_import
from .test_formatter import FormatterTests as FormatterTest, _tf
from .test_formatter import MultipleFormattersTests as MultipleFormattersTest
from nose.tools import *

class TestRerunFormatter(FormatterTest):
    formatter_name = "rerun"

    def test_feature_with_two_passing_scenarios(self):
        p = self._formatter(_tf(), self.config)
        f = self._feature()
        scenarios = [ self._scenario(), self._scenario() ]
        for scenario in scenarios:
            f.add_scenario(scenario)

        # -- FORMATTER CALLBACKS:
        p.feature(f)
        for scenario in f.scenarios:
            p.scenario(scenario)
            assert scenario.status == "passed"
        p.eof()
        eq_([], p.failed_scenarios)
        # -- EMIT REPORT:
        p.close()

    def test_feature_with_one_passing_one_failing_scenario(self):
        p = self._formatter(_tf(), self.config)
        f = self._feature()
        passing_scenario = self._scenario()
        failing_scenario = self._scenario()
        failing_scenario.steps.append(self._step())
        scenarios = [ passing_scenario, failing_scenario ]
        for scenario in scenarios:
            f.add_scenario(scenario)

        # -- FORMATTER CALLBACKS:
        p.feature(f)
        for scenario in f.scenarios:
            p.scenario(scenario)

        failing_scenario.steps[0].status = "failed"
        assert scenarios[0].status == "passed"
        assert scenarios[1].status == "failed"
        p.eof()
        eq_([ failing_scenario ], p.failed_scenarios)
        # -- EMIT REPORT:
        p.close()

    def test_feature_with_one_passing_two_failing_scenario(self):
        p = self._formatter(_tf(), self.config)
        f = self._feature()
        passing_scenario = self._scenario()
        failing_scenario1 = self._scenario()
        failing_scenario1.steps.append(self._step())
        failing_scenario2 = self._scenario()
        failing_scenario2.steps.append(self._step())
        scenarios = [ failing_scenario1, passing_scenario, failing_scenario2 ]
        for scenario in scenarios:
            f.add_scenario(scenario)

        # -- FORMATTER CALLBACKS:
        p.feature(f)
        for scenario in f.scenarios:
            p.scenario(scenario)

        failing_scenario1.steps[0].status = "failed"
        failing_scenario2.steps[0].status = "failed"
        assert scenarios[0].status == "failed"
        assert scenarios[1].status == "passed"
        assert scenarios[2].status == "failed"
        p.eof()
        eq_([ failing_scenario1, failing_scenario2 ], p.failed_scenarios)
        # -- EMIT REPORT:
        p.close()


class TestRerunAndPrettyFormatters(MultipleFormattersTest):
    formatters = ["rerun", "pretty"]

class TestRerunAndPlainFormatters(MultipleFormattersTest):
    formatters = ["rerun", "plain"]

class TestRerunAndScenarioProgressFormatters(MultipleFormattersTest):
    formatters = ["rerun", "progress"]

class TestRerunAndStepProgressFormatters(MultipleFormattersTest):
    formatters = ["rerun", "progress2"]

class TestRerunAndJsonFormatter(MultipleFormattersTest):
    formatters = ["rerun", "json"]

########NEW FILE########
__FILENAME__ = test_formatter_tags
# -*- coding: utf-8 -*-
"""
Test formatters:
  * behave.formatter.tags.TagsCountFormatter
  * behave.formatter.tags.TagsLocationFormatter
"""

from __future__ import absolute_import
from .test_formatter import FormatterTests as FormatterTest
from .test_formatter import MultipleFormattersTests as MultipleFormattersTest

# -----------------------------------------------------------------------------
# FORMATTER TESTS: With TagCountFormatter
# -----------------------------------------------------------------------------
class TestTagsCountFormatter(FormatterTest):
    formatter_name = "tags"

# -----------------------------------------------------------------------------
# FORMATTER TESTS: With TagLocationFormatter
# -----------------------------------------------------------------------------
class TestTagsLocationFormatter(FormatterTest):
    formatter_name = "tags.location"


# -----------------------------------------------------------------------------
# MULTI-FORMATTER TESTS: With TagCountFormatter
# -----------------------------------------------------------------------------
class TestPrettyAndTagsCount(MultipleFormattersTest):
    formatters = ["pretty", "tags"]

class TestPlainAndTagsCount(MultipleFormattersTest):
    formatters = ["plain", "tags"]

class TestJSONAndTagsCount(MultipleFormattersTest):
    formatters = ["json", "tags"]

class TestRerunAndTagsCount(MultipleFormattersTest):
    formatters = ["rerun", "tags"]


# -----------------------------------------------------------------------------
# MULTI-FORMATTER TESTS: With TagLocationFormatter
# -----------------------------------------------------------------------------
class TestPrettyAndTagsLocation(MultipleFormattersTest):
    formatters = ["pretty", "tags.location"]

class TestPlainAndTagsLocation(MultipleFormattersTest):
    formatters = ["plain", "tags.location"]

class TestJSONAndTagsLocation(MultipleFormattersTest):
    formatters = ["json", "tags.location"]

class TestRerunAndTagsLocation(MultipleFormattersTest):
    formatters = ["rerun", "tags.location"]

class TestTagsCountAndTagsLocation(MultipleFormattersTest):
    formatters = ["tags", "tags.location"]

########NEW FILE########
__FILENAME__ = test_importer
# -*- coding: utf-8 -*-
"""
Tests for behave.importing.
The module provides a lazy-loading/importing mechanism.
"""

from behave.importer import LazyObject, LazyDict
from behave.formatter.base import Formatter
from nose.tools import eq_, assert_raises
import sys
import types
# import unittest


class TestTheory(object): pass
class ImportModuleTheory(TestTheory):
    """
    Provides a test theory for importing modules.
    """

    @classmethod
    def ensure_module_is_not_imported(cls, module_name):
        if module_name in sys.modules:
            del sys.modules[module_name]
        cls.assert_module_is_not_imported(module_name)

    @staticmethod
    def assert_module_is_imported(module_name):
        module = sys.modules.get(module_name, None)
        assert module_name in sys.modules
        assert module is not None

    @staticmethod
    def assert_module_is_not_imported(module_name):
        assert module_name not in sys.modules

    @staticmethod
    def assert_module_with_name(module, name):
        assert isinstance(module, types.ModuleType)
        eq_(module.__name__, name)


class TestLazyObject(object):
    theory = ImportModuleTheory

    def test_load_module__should_fail_for_unknown_module(self):
        assert_raises(ImportError, LazyObject.load_module, "__unknown_module__")

    def test_load_module__should_succeed_for_already_imported_module(self):
        module_name = "behave.importer"
        self.theory.assert_module_is_imported(module_name)

        module = LazyObject.load_module(module_name)
        self.theory.assert_module_with_name(module, module_name)
        self.theory.assert_module_is_imported(module_name)

    def test_load_module__should_succeed_for_existing_module(self):
        module_name = "behave.textutil"
        self.theory.ensure_module_is_not_imported(module_name)

        module = LazyObject.load_module(module_name)
        self.theory.assert_module_with_name(module, module_name)
        self.theory.assert_module_is_imported(module_name)

    def test_get__should_succeed_for_known_object(self):
        lazy = LazyObject("behave.importer", "LazyObject")
        value = lazy.get()
        assert value is LazyObject

        lazy2 = LazyObject("behave.importer:LazyObject")
        value2 = lazy2.get()
        assert value2 is LazyObject

        lazy3 = LazyObject("behave.formatter.steps", "StepsFormatter")
        value3 = lazy3.get()
        assert issubclass(value3, Formatter)

    def test_get__should_fail_for_unknown_module(self):
        lazy = LazyObject("__unknown_module__", "xxx")
        assert_raises(ImportError, lazy.get)

    def test_get__should_fail_for_unknown_object_in_module(self):
        lazy = LazyObject("behave.textutil", "xxx")
        assert_raises(ImportError, lazy.get)


class LazyDictTheory(TestTheory):

    @staticmethod
    def safe_getitem(data, key):
        return dict.__getitem__(data, key)

    @classmethod
    def assert_item_is_lazy(cls, data, key):
        value = cls.safe_getitem(data, key)
        cls.assert_is_lazy_object(value)

    @classmethod
    def assert_item_is_not_lazy(cls, data, key):
        value = cls.safe_getitem(data, key)
        cls.assert_is_not_lazy_object(value)

    @staticmethod
    def assert_is_lazy_object(obj):
        assert isinstance(obj, LazyObject)

    @staticmethod
    def assert_is_not_lazy_object(obj):
        assert not isinstance(obj, LazyObject)


class TestLazyDict(object):
    theory = LazyDictTheory

    def test_unknown_item_access__should_raise_keyerror(self):
        lazy_dict = LazyDict({"alice": 42})
        item_access = lambda key: lazy_dict[key]
        assert_raises(KeyError, item_access, "unknown")

    def test_plain_item_access__should_succeed(self):
        theory = LazyDictTheory
        lazy_dict = LazyDict({"alice": 42})
        theory.assert_item_is_not_lazy(lazy_dict, "alice")

        value = lazy_dict["alice"]
        eq_(value, 42)

    def test_lazy_item_access__should_load_object(self):
        ImportModuleTheory.ensure_module_is_not_imported("inspect")
        lazy_dict = LazyDict({"alice": LazyObject("inspect:ismodule")})
        self.theory.assert_item_is_lazy(lazy_dict, "alice")
        self.theory.assert_item_is_lazy(lazy_dict, "alice")

        value = lazy_dict["alice"]
        self.theory.assert_is_not_lazy_object(value)
        self.theory.assert_item_is_not_lazy(lazy_dict, "alice")

    def test_lazy_item_access__should_fail_with_unknown_module(self):
        lazy_dict = LazyDict({"bob": LazyObject("__unknown_module__", "xxx")})
        item_access = lambda key: lazy_dict[key]
        assert_raises(ImportError, item_access, "bob")

    def test_lazy_item_access__should_fail_with_unknown_object(self):
        lazy_dict = LazyDict({
            "bob": LazyObject("behave.importer", "XUnknown")
        })
        item_access = lambda key: lazy_dict[key]
        assert_raises(ImportError, item_access, "bob")

########NEW FILE########
__FILENAME__ = test_log_capture
from __future__ import with_statement

from nose.tools import *
from mock import patch

from behave.log_capture import LoggingCapture

class TestLogCapture(object):
    def test_get_value_returns_all_log_records(self):
        class FakeConfig(object):
            logging_filter = None
            logging_format = None
            logging_datefmt = None
            logging_level = None

        fake_records = [object() for x in range(0, 10)]

        handler = LoggingCapture(FakeConfig())
        handler.buffer = fake_records

        with patch.object(handler.formatter, 'format') as format:
            format.return_value = 'foo'
            expected = '\n'.join(['foo'] * len(fake_records))

            eq_(handler.getvalue(), expected)

            calls = [args[0][0] for args in format.call_args_list]
            eq_(calls, fake_records)

########NEW FILE########
__FILENAME__ = test_matchers
from __future__ import with_statement

from mock import Mock, patch
from nose.tools import *
import parse

from behave import matchers, model, runner

class DummyMatcher(matchers.Matcher):
    desired_result = None

    def check_match(self, step):
        return DummyMatcher.desired_result

class TestMatcher(object):
    def setUp(self):
        DummyMatcher.desired_result = None

    def test_returns_none_if_check_match_returns_none(self):
        matcher = DummyMatcher(None, None)
        assert matcher.match('just a random step') is None

    def test_returns_match_object_if_check_match_returns_arguments(self):
        arguments = ['some', 'random', 'objects']
        func = lambda x: -x

        DummyMatcher.desired_result = arguments
        matcher = DummyMatcher(func, None)

        match = matcher.match('just a random step')
        assert isinstance(match, model.Match)
        assert match.func is func
        assert match.arguments == arguments

class TestParseMatcher(object):
    def setUp(self):
        self.recorded_args = None

    def record_args(self, *args, **kwargs):
        self.recorded_args = (args, kwargs)

    def test_returns_none_if_parser_does_not_match(self):
        matcher = matchers.ParseMatcher(None, 'a string')
        with patch.object(matcher.parser, 'parse') as parse:
            parse.return_value = None
            assert matcher.match('just a random step') is None

    def test_returns_arguments_based_on_matches(self):
        func = lambda x: -x
        matcher = matchers.ParseMatcher(func, 'foo')

        results = parse.Result([1, 2, 3], {'foo': 'bar', 'baz': -45.3},
                               {
                                   0: (13, 14),
                                   1: (16, 17),
                                   2: (22, 23),
                                   'foo': (32, 35),
                                   'baz': (39, 44),
                               })

        expected = [
            (13, 14, '1', 1, None),
            (16, 17, '2', 2, None),
            (22, 23, '3', 3, None),
            (32, 35, 'bar', 'bar', 'foo'),
            (39, 44, '-45.3', -45.3, 'baz'),
        ]

        with patch.object(matcher.parser, 'parse') as p:
            p.return_value = results
            m = matcher.match('some numbers 1, 2 and 3 and the bar is -45.3')
            assert m.func is func
            args = m.arguments
            have = [(a.start, a.end, a.original, a.value, a.name) for a in args]
            eq_(have, expected)

    def test_named_arguments(self):
        text = "has a {string}, an {integer:d} and a {decimal:f}"
        matcher = matchers.ParseMatcher(self.record_args, text)
        context = runner.Context(Mock())

        m = matcher.match("has a foo, an 11 and a 3.14159")
        m.run(context)
        eq_(self.recorded_args, ((context,), {
            'string': 'foo',
            'integer': 11,
            'decimal': 3.14159
        }))

    def test_positional_arguments(self):
        text = "has a {}, an {:d} and a {:f}"
        matcher = matchers.ParseMatcher(self.record_args, text)
        context = runner.Context(Mock())

        m = matcher.match("has a foo, an 11 and a 3.14159")
        m.run(context)
        eq_(self.recorded_args, ((context, 'foo', 11, 3.14159), {}))

class TestRegexMatcher(object):
    def test_returns_none_if_regex_does_not_match(self):
        matcher = matchers.RegexMatcher(None, 'a string')
        regex = Mock()
        regex.match.return_value = None
        matcher.regex = regex
        assert matcher.match('just a random step') is None

    def test_returns_arguments_based_on_groups(self):
        func = lambda x: -x
        matcher = matchers.RegexMatcher(func, 'foo')

        regex = Mock()
        regex.groupindex = {'foo': 4, 'baz': 5}

        match = Mock()
        match.groups.return_value = ('1', '2', '3', 'bar', '-45.3')
        positions = {
            1: (13, 14),
            2: (16, 17),
            3: (22, 23),
            4: (32, 35),
            5: (39, 44),
        }
        match.start.side_effect = lambda idx: positions[idx][0]
        match.end.side_effect = lambda idx: positions[idx][1]

        regex.match.return_value = match
        matcher.regex = regex

        expected = [
            (13, 14, '1', '1', None),
            (16, 17, '2', '2', None),
            (22, 23, '3', '3', None),
            (32, 35, 'bar', 'bar', 'foo'),
            (39, 44, '-45.3', '-45.3', 'baz'),
        ]

        m = matcher.match('some numbers 1, 2 and 3 and the bar is -45.3')
        assert m.func is func
        args = m.arguments
        have = [(a.start, a.end, a.original, a.value, a.name) for a in args]
        eq_(have, expected)

def test_step_matcher_current_matcher():
    current_matcher = matchers.current_matcher

    for name, klass in matchers.matcher_mapping.items():
        matchers.use_step_matcher(name)
        matcher = matchers.get_matcher(lambda x: -x, 'foo')
        assert isinstance(matcher, klass)

    matchers.current_matcher = current_matcher

########NEW FILE########
__FILENAME__ = test_model
# -*- coding: utf-8 -*-

from __future__ import with_statement
from behave import model
from behave.configuration import Configuration
from behave.compat.collections import OrderedDict
from behave import step_registry
from mock import Mock, patch
from nose.tools import *
import re
import sys
import unittest


class TestFeatureRun(unittest.TestCase):
    def setUp(self):
        self.runner = Mock()
        self.runner.feature.tags = []
        self.config = self.runner.config = Mock()
        self.context = self.runner.context = Mock()
        self.formatters = self.runner.formatters = [Mock()]
        self.run_hook = self.runner.run_hook = Mock()

    def test_formatter_feature_called(self):
        feature = model.Feature('foo.feature', 1, u'Feature', u'foo',
                                background=Mock())

        feature.run(self.runner)

        self.formatters[0].feature.assert_called_with(feature)

    def test_formatter_background_called_when_feature_has_background(self):
        feature = model.Feature('foo.feature', 1, u'Feature', u'foo',
                                background=Mock())

        feature.run(self.runner)

        self.formatters[0].background.assert_called_with(feature.background)

    def test_formatter_background_not_called_when_feature_has_no_background(self):
        feature = model.Feature('foo.feature', 1, u'Feature', u'foo')

        feature.run(self.runner)

        assert not self.formatters[0].background.called

    def test_run_runs_scenarios(self):
        scenarios = [Mock(), Mock()]
        for scenario in scenarios:
            scenario.tags = []
            scenario.run.return_value = False

        self.config.tags.check.return_value = True
        self.config.name = []

        feature = model.Feature('foo.feature', 1, u'Feature', u'foo',
                                scenarios=scenarios)

        feature.run(self.runner)

        for scenario in scenarios:
            scenario.run.assert_called_with(self.runner)

    def test_run_runs_named_scenarios(self):
        scenarios = [Mock(model.Scenario), Mock(model.Scenario)]
        scenarios[0].name = 'first scenario'
        scenarios[1].name = 'second scenario'
        scenarios[0].tags = []
        scenarios[1].tags = []
        # -- FAKE-CHECK:
        scenarios[0].should_run_with_name_select.return_value = True
        scenarios[1].should_run_with_name_select.return_value = False

        for scenario in scenarios:
            scenario.run.return_value = False

        self.config.tags.check.return_value = True
        self.config.name = ['first', 'third']
        self.config.name_re = Configuration.build_name_re(self.config.name)

        feature = model.Feature('foo.feature', 1, u'Feature', u'foo',
                                scenarios=scenarios)

        feature.run(self.runner)

        scenarios[0].run.assert_called_with(self.runner)
        assert not scenarios[1].run.called
        scenarios[0].should_run_with_name_select.assert_called_with(self.config)
        scenarios[1].should_run_with_name_select.assert_called_with(self.config)

    def test_run_runs_named_scenarios_with_regexp(self):
        scenarios = [Mock(), Mock()]
        scenarios[0].name = 'first scenario'
        scenarios[1].name = 'second scenario'
        scenarios[0].tags = []
        scenarios[1].tags = []
        # -- FAKE-CHECK:
        scenarios[0].should_run_with_name_select.return_value = False
        scenarios[1].should_run_with_name_select.return_value = True

        for scenario in scenarios:
            scenario.run.return_value = False

        self.config.tags.check.return_value = True
        self.config.name = ['third .*', 'second .*']
        self.config.name_re = Configuration.build_name_re(self.config.name)

        feature = model.Feature('foo.feature', 1, u'Feature', u'foo',
                                scenarios=scenarios)

        feature.run(self.runner)

        assert not scenarios[0].run.called
        scenarios[1].run.assert_called_with(self.runner)
        scenarios[0].should_run_with_name_select.assert_called_with(self.config)
        scenarios[1].should_run_with_name_select.assert_called_with(self.config)

    def test_feature_hooks_not_run_if_feature_not_being_run(self):
        self.config.tags.check.return_value = False

        feature = model.Feature('foo.feature', 1, u'Feature', u'foo')

        feature.run(self.runner)

        assert not self.run_hook.called


class TestScenarioRun(unittest.TestCase):
    def setUp(self):
        self.runner = Mock()
        self.runner.feature.tags = []
        self.config = self.runner.config = Mock()
        self.config.dry_run = False
        self.context = self.runner.context = Mock()
        self.formatters = self.runner.formatters = [Mock()]
        self.run_hook = self.runner.run_hook = Mock()

    def test_run_invokes_formatter_scenario_and_steps_correctly(self):
        self.config.stdout_capture = False
        self.config.log_capture = False
        self.config.tags.check.return_value = True
        steps = [Mock(), Mock()]
        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo',
                                  steps=steps)

        scenario.run(self.runner)

        self.formatters[0].scenario.assert_called_with(scenario)
        [step.run.assert_called_with(self.runner) for step in steps]

    if sys.version_info[0] == 3:
        stringio_target = 'io.StringIO'
    else:
        stringio_target = 'StringIO.StringIO'

    def test_handles_stdout_and_log_capture(self):
        self.config.stdout_capture = True
        self.config.log_capture = True
        self.config.tags.check.return_value = True

        steps = [Mock(), Mock()]
        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo',
                                  steps=steps)

        scenario.run(self.runner)

        self.runner.setup_capture.assert_called_with()
        self.runner.teardown_capture.assert_called_with()

    def test_failed_step_causes_remaining_steps_to_be_skipped(self):
        self.config.stdout_capture = False
        self.config.log_capture = False
        self.config.tags.check.return_value = True

        steps = [Mock(), Mock()]
        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo',
                                  steps=steps)
        steps[0].run.return_value = False
        steps[1].step_type = "when"
        steps[1].name = "step1"

        def step1_function(context):
            pass
        my_step_registry = step_registry.StepRegistry()
        my_step_registry.add_step_definition("when", "step1", step1_function)

        with patch("behave.step_registry.registry", my_step_registry):
            assert scenario.run(self.runner)
            eq_(steps[1].status, 'skipped')

    def test_failed_step_causes_context_failure_to_be_set(self):
        self.config.stdout_capture = False
        self.config.log_capture = False
        self.config.tags.check.return_value = True

        steps = [
            Mock(step_type="given", name="step0"),
            Mock(step_type="then",  name="step1"),
        ]
        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo',
                                  steps=steps)
        steps[0].run.return_value = False

        assert scenario.run(self.runner)
        self.context._set_root_attribute.assert_called_with('failed', True)

    def test_undefined_step_causes_failed_scenario_status(self):
        self.config.stdout_capture = False
        self.config.log_capture = False
        self.config.tags.check.return_value = True

        passed_step = Mock()
        undefined_step = Mock()

        steps = [passed_step, undefined_step]
        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo',
                                  steps=steps)
        passed_step.run.return_value = True
        passed_step.status = 'passed'
        undefined_step.run.return_value = False
        undefined_step.status = 'undefined'

        assert scenario.run(self.runner)
        eq_(undefined_step.status, 'undefined')
        eq_(scenario.status, 'failed')
        self.context._set_root_attribute.assert_called_with('failed', True)

    def test_skipped_steps_set_step_status_and_scenario_status_if_not_set(self):
        self.config.stdout_capture = False
        self.config.log_capture = False
        self.config.tags.check.return_value = False

        steps = [Mock(), Mock()]
        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo',
                                  steps=steps)

        scenario.run(self.runner)

        assert False not in [s.status == 'skipped' for s in steps]
        eq_(scenario.status, 'skipped')

    def test_scenario_hooks_not_run_if_scenario_not_being_run(self):
        self.config.tags.check.return_value = False

        scenario = model.Scenario('foo.feature', 17, u'Scenario', u'foo')

        scenario.run(self.runner)

        assert not self.run_hook.called

    def test_should_run_with_name_select(self):
        scenario_name = u"first scenario"
        scenario = model.Scenario("foo.feature", 17, u"Scenario", scenario_name)
        self.config.name = ['first .*', 'second .*']
        self.config.name_re = Configuration.build_name_re(self.config.name)

        assert scenario.should_run_with_name_select(self.config)

class TestScenarioOutline(unittest.TestCase):
    def test_run_calls_run_on_each_generated_scenario(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        outline._scenarios = [Mock(), Mock()]
        for scenario in outline._scenarios:
            scenario.run.return_value = False

        runner = Mock()
        runner.context = Mock()

        outline.run(runner)

        [s.run.assert_called_with(runner) for s in outline._scenarios]

    def test_run_stops_on_first_failure_if_requested(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        outline._scenarios = [Mock(), Mock()]
        outline._scenarios[0].run.return_value = True

        runner = Mock()
        runner.context = Mock()
        config = runner.config = Mock()
        config.stop = True

        outline.run(runner)

        outline._scenarios[0].run.assert_called_with(runner)
        assert not outline._scenarios[1].run.called

    def test_run_sets_context_variable_for_outline(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        outline._scenarios = [Mock(), Mock(), Mock()]
        for scenario in outline._scenarios:
            scenario.run.return_value = False

        runner = Mock()
        context = runner.context = Mock()
        config = runner.config = Mock()
        config.stop = True

        outline.run(runner)

        eq_(context._set_root_attribute.call_args_list, [
            (('active_outline', outline._scenarios[0]._row), {}),
            (('active_outline', outline._scenarios[1]._row), {}),
            (('active_outline', outline._scenarios[2]._row), {}),
            (('active_outline', None), {}),
        ])

    def test_run_should_pass_when_all_examples_pass(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        outline._scenarios = [Mock(), Mock(), Mock()]
        for scenario in outline._scenarios:
            scenario.run.return_value = False

        runner = Mock()
        context = runner.context = Mock()
        config = runner.config = Mock()
        config.stop = True

        resultFailed = outline.run(runner)
        eq_(resultFailed, False)

    def test_run_should_fail_when_first_examples_fails(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        failed = True
        outline._scenarios = [Mock(), Mock()]
        outline._scenarios[0].run.return_value = failed
        outline._scenarios[1].run.return_value = not failed

        runner = Mock()
        context = runner.context = Mock()
        config = runner.config = Mock()
        config.stop = True

        resultFailed = outline.run(runner)
        eq_(resultFailed, True)

    def test_run_should_fail_when_last_examples_fails(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        failed = True
        outline._scenarios = [Mock(), Mock()]
        outline._scenarios[0].run.return_value = not failed
        outline._scenarios[1].run.return_value = failed

        runner = Mock()
        context = runner.context = Mock()
        config = runner.config = Mock()
        config.stop = True

        resultFailed = outline.run(runner)
        eq_(resultFailed, True)

    def test_run_should_fail_when_middle_examples_fails(self):
        outline = model.ScenarioOutline('foo.feature', 17, u'Scenario Outline',
                                        u'foo')
        failed = True
        outline._scenarios = [Mock(), Mock(), Mock()]
        outline._scenarios[0].run.return_value = not failed
        outline._scenarios[1].run.return_value = failed
        outline._scenarios[2].run.return_value = not failed

        runner = Mock()
        context = runner.context = Mock()
        config = runner.config = Mock()
        config.stop = True

        resultFailed = outline.run(runner)
        eq_(resultFailed, True)


def raiser(exception):
    def func(*args, **kwargs):
        raise exception
    return func


class TestStepRun(unittest.TestCase):
    def setUp(self):
        self.runner = Mock()
        self.config = self.runner.config = Mock()
        self.config.outputs = [None]
        self.context = self.runner.context = Mock()
        print ('context is', self.context)
        self.formatters = self.runner.formatters = [Mock()]
        self.step_registry = Mock()
        self.stdout_capture = self.runner.stdout_capture = Mock()
        self.stdout_capture.getvalue.return_value = ''
        self.stderr_capture = self.runner.stderr_capture = Mock()
        self.stderr_capture.getvalue.return_value = ''
        self.log_capture = self.runner.log_capture = Mock()
        self.log_capture.getvalue.return_value = ''
        self.run_hook = self.runner.run_hook = Mock()

    def test_run_appends_step_to_undefined_when_no_match_found(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        self.step_registry.find_match.return_value = None
        self.runner.undefined_steps = []
        with patch('behave.step_registry.registry', self.step_registry):
            assert not step.run(self.runner)

        assert step in self.runner.undefined_steps
        eq_(step.status, 'undefined')

    def test_run_reports_undefined_step_via_formatter_when_not_quiet(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        self.step_registry.find_match.return_value = None
        with patch('behave.step_registry.registry', self.step_registry):
            assert not step.run(self.runner)

        self.formatters[0].match.assert_called_with(model.NoMatch())
        self.formatters[0].result.assert_called_with(step)

    def test_run_with_no_match_does_not_touch_formatter_when_quiet(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        self.step_registry.find_match.return_value = None
        with patch('behave.step_registry.registry', self.step_registry):
            assert not step.run(self.runner, quiet=True)

        assert not self.formatters[0].match.called
        assert not self.formatters[0].result.called

    def test_run_when_not_quiet_reports_match_and_result(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match

        side_effects = (None, raiser(AssertionError('whee')),
                        raiser(Exception('whee')))
        for side_effect in side_effects:
            match.run.side_effect = side_effect
            with patch('behave.step_registry.registry', self.step_registry):
                step.run(self.runner)
            self.formatters[0].match.assert_called_with(match)
            self.formatters[0].result.assert_called_with(step)

    def test_run_when_quiet_reports_nothing(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match

        side_effects = (None, raiser(AssertionError('whee')),
                raiser(Exception('whee')))
        for side_effect in side_effects:
            match.run.side_effect = side_effect
            step.run(self.runner, quiet=True)
            assert not self.formatters[0].match.called
            assert not self.formatters[0].result.called

    def test_run_runs_before_hook_then_match_then_after_hook(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match

        side_effects = (None, AssertionError('whee'), Exception('whee'))
        for side_effect in side_effects:
            # Make match.run() and runner.run_hook() the same mock so
            # we can make sure things happen in the right order.
            self.runner.run_hook = match.run = Mock()

            def effect(thing):
                def raiser(*args, **kwargs):
                    match.run.side_effect = None
                    if thing:
                        raise thing

                def nonraiser(*args, **kwargs):
                    match.run.side_effect = raiser

                return nonraiser

            match.run.side_effect = effect(side_effect)
            with patch('behave.step_registry.registry', self.step_registry):
                step.run(self.runner)

            eq_(match.run.call_args_list, [
                (('before_step', self.context, step), {}),
                ((self.context,), {}),
                (('after_step', self.context, step), {}),
            ])

    def test_run_sets_table_if_present(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo',
                          table=Mock())
        self.step_registry.find_match.return_value = Mock()

        with patch('behave.step_registry.registry', self.step_registry):
            step.run(self.runner)

        eq_(self.context.table, step.table)

    def test_run_sets_text_if_present(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo',
                          text=Mock(name='text'))
        self.step_registry.find_match.return_value = Mock()

        with patch('behave.step_registry.registry', self.step_registry):
            step.run(self.runner)

        eq_(self.context.text, step.text)

    def test_run_sets_status_to_passed_if_nothing_goes_wrong(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        step.error_message = None
        self.step_registry.find_match.return_value = Mock()

        with patch('behave.step_registry.registry', self.step_registry):
            step.run(self.runner)

        eq_(step.status, 'passed')
        eq_(step.error_message, None)

    def test_run_sets_status_to_failed_on_assertion_error(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        step.error_message = None
        match = Mock()
        match.run.side_effect = raiser(AssertionError('whee'))
        self.step_registry.find_match.return_value = match

        with patch('behave.step_registry.registry', self.step_registry):
            step.run(self.runner)

        eq_(step.status, 'failed')
        assert step.error_message.startswith('Assertion Failed')

    @patch('traceback.format_exc')
    def test_run_sets_status_to_failed_on_exception(self, format_exc):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        step.error_message = None
        match = Mock()
        match.run.side_effect = raiser(Exception('whee'))
        self.step_registry.find_match.return_value = match
        format_exc.return_value = 'something to do with an exception'

        with patch('behave.step_registry.registry', self.step_registry):
            step.run(self.runner)

        eq_(step.status, 'failed')
        eq_(step.error_message, format_exc.return_value)

    @patch('time.time')
    def test_run_calculates_duration(self, time_time):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match

        def time_time_1():
            def time_time_2():
                return 23
            time_time.side_effect = time_time_2
            return 17

        side_effects = (None, raiser(AssertionError('whee')),
                raiser(Exception('whee')))
        for side_effect in side_effects:
            match.run.side_effect = side_effect
            time_time.side_effect = time_time_1

            with patch('behave.step_registry.registry', self.step_registry):
                step.run(self.runner)
            eq_(step.duration, 23 - 17)

    def test_run_captures_stdout_and_logging(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match

        with patch('behave.step_registry.registry', self.step_registry):
            assert step.run(self.runner)

        self.runner.start_capture.assert_called_with()
        self.runner.stop_capture.assert_called_with()

    def test_run_appends_any_captured_stdout_on_failure(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match
        self.stdout_capture.getvalue.return_value = 'frogs'
        match.run.side_effect = raiser(Exception('halibut'))

        with patch('behave.step_registry.registry', self.step_registry):
            assert not step.run(self.runner)

        assert 'Captured stdout:' in step.error_message
        assert 'frogs' in step.error_message

    def test_run_appends_any_captured_logging_on_failure(self):
        step = model.Step('foo.feature', 17, u'Given', 'given', u'foo')
        match = Mock()
        self.step_registry.find_match.return_value = match
        self.log_capture.getvalue.return_value = 'toads'
        match.run.side_effect = raiser(AssertionError('kipper'))

        with patch('behave.step_registry.registry', self.step_registry):
            assert not step.run(self.runner)

        assert 'Captured logging:' in step.error_message
        assert 'toads' in step.error_message


class TestTableModel(unittest.TestCase):
    HEAD = [u'type of stuff', u'awesomeness', u'ridiculousness']
    DATA = [
        [u'fluffy', u'large', u'frequent'],
        [u'lint', u'low', u'high'],
        [u'green', u'variable', u'awkward'],
    ]

    def setUp(self):
        self.table = model.Table(self.HEAD, 0, self.DATA)

    def test_equivalence(self):
        t1 = self.table
        self.setUp()
        eq_(t1, self.table)

    def test_table_iteration(self):
        for i, row in enumerate(self.table):
            for j, cell in enumerate(row):
                eq_(cell, self.DATA[i][j])

    def test_table_row_by_index(self):
        for i in range(3):
            eq_(self.table[i], model.Row(self.HEAD, self.DATA[i], 0))

    def test_table_row_name(self):
        eq_(self.table[0]['type of stuff'], 'fluffy')
        eq_(self.table[1]['awesomeness'], 'low')
        eq_(self.table[2]['ridiculousness'], 'awkward')

    def test_table_row_index(self):
        eq_(self.table[0][0], 'fluffy')
        eq_(self.table[1][1], 'low')
        eq_(self.table[2][2], 'awkward')

    @raises(KeyError)
    def test_table_row_keyerror(self):
        self.table[0]['spam']

    def test_table_row_items(self):
        eq_(self.table[0].items(), zip(self.HEAD, self.DATA[0]))


class TestModelRow(unittest.TestCase):
    HEAD = [u'name',  u'sex',    u'age']
    DATA = [u'Alice', u'female', u'12']

    def setUp(self):
        self.row = model.Row(self.HEAD, self.DATA, 0)

    def test_len(self):
        eq_(len(self.row), 3)

    def test_getitem_with_valid_colname(self):
        eq_(self.row['name'], u'Alice')
        eq_(self.row['sex'],  u'female')
        eq_(self.row['age'],  u'12')

    @raises(KeyError)
    def test_getitem_with_unknown_colname(self):
        self.row['__UNKNOWN_COLUMN__']

    def test_getitem_with_valid_index(self):
        eq_(self.row[0], u'Alice')
        eq_(self.row[1], u'female')
        eq_(self.row[2], u'12')

    @raises(IndexError)
    def test_getitem_with_invalid_index(self):
        colsize = len(self.row)
        eq_(colsize, 3)
        self.row[colsize]

    def test_get_with_valid_colname(self):
        eq_(self.row.get('name'), u'Alice')
        eq_(self.row.get('sex'),  u'female')
        eq_(self.row.get('age'),  u'12')

    def test_getitem_with_unknown_colname_should_return_default(self):
        eq_(self.row.get('__UNKNOWN_COLUMN__', 'XXX'), u'XXX')

    def test_as_dict(self):
        data1 = self.row.as_dict()
        data2 = dict(self.row.as_dict())
        assert isinstance(data1, dict)
        assert isinstance(data2, dict)
        assert isinstance(data1, OrderedDict)
        # -- REQUIRES: Python2.7 or ordereddict installed.
        # assert not isinstance(data2, OrderedDict)
        eq_(data1, data2)
        eq_(data1['name'], u'Alice')
        eq_(data1['sex'],  u'female')
        eq_(data1['age'],  u'12')


class TestFileLocation(unittest.TestCase):
    ordered_locations1 = [
        model.FileLocation("features/alice.feature",   1),
        model.FileLocation("features/alice.feature",   5),
        model.FileLocation("features/alice.feature",  10),
        model.FileLocation("features/alice.feature",  11),
        model.FileLocation("features/alice.feature", 100),
    ]
    ordered_locations2 = [
        model.FileLocation("features/alice.feature",     1),
        model.FileLocation("features/alice.feature",    10),
        model.FileLocation("features/bob.feature",       5),
        model.FileLocation("features/charly.feature", None),
        model.FileLocation("features/charly.feature",    0),
        model.FileLocation("features/charly.feature",  100),
    ]
    same_locations = [
        ( model.FileLocation("alice.feature"),
          model.FileLocation("alice.feature", None),
        ),
        ( model.FileLocation("alice.feature", 10),
          model.FileLocation("alice.feature", 10),
        ),
        ( model.FileLocation("features/bob.feature", 11),
          model.FileLocation("features/bob.feature", 11),
        ),
    ]

    def test_compare_equal(self):
        for value1, value2 in self.same_locations:
            eq_(value1, value2)

    def test_compare_equal_with_string(self):
        for location in self.ordered_locations2:
            eq_(location, location.filename)
            eq_(location.filename, location)

    def test_compare_not_equal(self):
        for value1, value2 in self.same_locations:
            assert not(value1 != value2)

        for locations in [self.ordered_locations1, self.ordered_locations2]:
            for value1, value2 in zip(locations, locations[1:]):
                assert value1 != value2

    def test_compare_less_than(self):
        for locations in [self.ordered_locations1, self.ordered_locations2]:
            for value1, value2 in zip(locations, locations[1:]):
                assert value1  < value2, "FAILED: %s < %s" % (str(value1), str(value2))
                assert value1 != value2

    def test_compare_less_than_with_string(self):
        locations = self.ordered_locations2
        for value1, value2 in zip(locations, locations[1:]):
            if value1.filename == value2.filename:
                continue
            assert value1  < value2.filename, "FAILED: %s < %s" % (str(value1), str(value2.filename))
            assert value1.filename < value2,  "FAILED: %s < %s" % (str(value1.filename), str(value2))

    def test_compare_greater_than(self):
        for locations in [self.ordered_locations1, self.ordered_locations2]:
            for value1, value2 in zip(locations, locations[1:]):
                assert value2  > value1, "FAILED: %s > %s" % (str(value2), str(value1))
                assert value2 != value1

    def test_compare_less_or_equal(self):
        for value1, value2 in self.same_locations:
            assert value1 <= value2, "FAILED: %s <= %s" % (str(value1), str(value2))
            assert value1 == value2

        for locations in [self.ordered_locations1, self.ordered_locations2]:
            for value1, value2 in zip(locations, locations[1:]):
                assert value1 <= value2, "FAILED: %s <= %s" % (str(value1), str(value2))
                assert value1 != value2

    def test_compare_greater_or_equal(self):
        for value1, value2 in self.same_locations:
            assert value2 >= value1, "FAILED: %s >= %s" % (str(value2), str(value1))
            assert value2 == value1

        for locations in [self.ordered_locations1, self.ordered_locations2]:
            for value1, value2 in zip(locations, locations[1:]):
                assert value2 >= value1, "FAILED: %s >= %s" % (str(value2), str(value1))
                assert value2 != value1

    def test_filename_should_be_same_as_self(self):
        for location in self.ordered_locations2:
            assert location == location.filename
            assert location.filename == location

    def test_string_conversion(self):
        for location in self.ordered_locations2:
            expected = u"%s:%s" % (location.filename, location.line)
            if location.line is None:
                expected = location.filename
            assert str(location) == expected

    def test_repr_conversion(self):
        for location in self.ordered_locations2:
            expected = u'<FileLocation: filename="%s", line=%s>' % \
                       (location.filename, location.line)
            actual = repr(location)
            assert actual == expected, "FAILED: %s == %s" % (actual, expected)

########NEW FILE########
__FILENAME__ = test_parser
#-*- encoding: UTF-8 -*-

from nose.tools import *

from behave import i18n, model, parser

class Common(object):
    def compare_steps(self, steps, expected):
        have = [(s.step_type, s.keyword, s.name, s.text, s.table) for s in steps]
        eq_(have, expected)

class TestParser(Common):
    def test_parses_feature_name(self):
        feature = parser.parse_feature(u"Feature: Stuff\n")
        eq_(feature.name, "Stuff")

    def test_parses_feature_name_without_newline(self):
        feature = parser.parse_feature(u"Feature: Stuff")
        eq_(feature.name, "Stuff")

    def test_parses_feature_description(self):
        doc = u"""
Feature: Stuff
  In order to thing
  As an entity
  I want to do stuff
""".strip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description,
            ["In order to thing", "As an entity", "I want to do stuff"])

    def test_parses_feature_with_a_tag(self):
        doc = u"""
@foo
Feature: Stuff
  In order to thing
  As an entity
  I want to do stuff
""".strip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description,
            ["In order to thing", "As an entity", "I want to do stuff"])
        eq_(feature.tags, [model.Tag(u'foo', 1)])

    def test_parses_feature_with_more_tags(self):
        doc = u"""
@foo @bar @baz @qux @winkle_pickers @number8
Feature: Stuff
  In order to thing
  As an entity
  I want to do stuff
""".strip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description,
            ["In order to thing", "As an entity", "I want to do stuff"])
        eq_(feature.tags, [model.Tag(name, 1)
            for name in (u'foo', u'bar', u'baz', u'qux', u'winkle_pickers', u'number8')])

    def test_parses_feature_with_a_tag_and_comment(self):
        doc = u"""
@foo    # Comment: ...
Feature: Stuff
  In order to thing
  As an entity
  I want to do stuff
""".strip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description,
            ["In order to thing", "As an entity", "I want to do stuff"])
        eq_(feature.tags, [model.Tag(u'foo', 1)])

    def test_parses_feature_with_more_tags_and_comment(self):
        doc = u"""
@foo @bar @baz @qux @winkle_pickers # Comment: @number8
Feature: Stuff
  In order to thing
  As an entity
  I want to do stuff
""".strip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description,
            ["In order to thing", "As an entity", "I want to do stuff"])
        eq_(feature.tags, [model.Tag(name, 1)
                           for name in (u'foo', u'bar', u'baz', u'qux', u'winkle_pickers')])
        # -- NOT A TAG: u'number8'

    def test_parses_feature_with_background(self):
        doc = u"""
Feature: Stuff
  Background:
    Given there is stuff
    When I do stuff
    Then stuff happens
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(feature.background)
        self.compare_steps(feature.background.steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_feature_with_description_and_background(self):
        doc = u"""
Feature: Stuff
  This... is... STUFF!

  Background:
    Given there is stuff
    When I do stuff
    Then stuff happens
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description, ["This... is... STUFF!"])
        assert(feature.background)
        self.compare_steps(feature.background.steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_feature_with_a_scenario(self):
        doc = u"""
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff
    When I do stuff
    Then stuff happens
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_lowercase_step_keywords(self):
        doc = u"""
Feature: Stuff

  Scenario: Doing stuff
    giVeN there is stuff
    when I do stuff
    tHEn stuff happens
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_ja_keywords(self):
        doc = u"""
機能: Stuff

  シナリオ: Doing stuff
    前提there is stuff
    もしI do stuff
    ならばstuff happens
""".lstrip()
        feature = parser.parse_feature(doc, language='ja')
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', u'前提', 'there is stuff', None, None),
            ('when', u'もし', 'I do stuff', None, None),
            ('then', u'ならば', 'stuff happens', None, None),
        ])

    def test_parses_feature_with_description_and_background_and_scenario(self):
        doc = u"""
Feature: Stuff
  Oh my god, it's full of stuff...

  Background:
    Given I found some stuff

  Scenario: Doing stuff
    Given there is stuff
    When I do stuff
    Then stuff happens
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])
        assert(feature.background)
        self.compare_steps(feature.background.steps, [
            ('given', 'Given', 'I found some stuff', None, None),
        ])

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_feature_with_multiple_scenarios(self):
        doc = u"""
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff
    When I do stuff
    Then stuff happens

  Scenario: Doing other stuff
    When stuff happens
    Then I am stuffed

  Scenario: Doing different stuff
    Given stuff
    Then who gives a stuff
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")

        assert(len(feature.scenarios) == 3)

        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

        eq_(feature.scenarios[1].name, 'Doing other stuff')
        self.compare_steps(feature.scenarios[1].steps, [
            ('when', 'When', 'stuff happens', None, None),
            ('then', 'Then', 'I am stuffed', None, None),
        ])

        eq_(feature.scenarios[2].name, 'Doing different stuff')
        self.compare_steps(feature.scenarios[2].steps, [
            ('given', 'Given', 'stuff', None, None),
            ('then', 'Then', 'who gives a stuff', None, None),
        ])

    def test_parses_feature_with_multiple_scenarios_with_tags(self):
        doc = u"""
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff
    When I do stuff
    Then stuff happens

  @one_tag
  Scenario: Doing other stuff
    When stuff happens
    Then I am stuffed

  @lots @of @tags
  Scenario: Doing different stuff
    Given stuff
    Then who gives a stuff
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")

        assert(len(feature.scenarios) == 3)

        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

        eq_(feature.scenarios[1].name, 'Doing other stuff')
        eq_(feature.scenarios[1].tags, [model.Tag(u'one_tag', 1)])
        self.compare_steps(feature.scenarios[1].steps, [
            ('when', 'When', 'stuff happens', None, None),
            ('then', 'Then', 'I am stuffed', None, None),
        ])

        eq_(feature.scenarios[2].name, 'Doing different stuff')
        eq_(feature.scenarios[2].tags, [model.Tag(n, 1) for n in (u'lots', u'of', u'tags')])
        self.compare_steps(feature.scenarios[2].steps, [
            ('given', 'Given', 'stuff', None, None),
            ('then', 'Then', 'who gives a stuff', None, None),
        ])

    def test_parses_feature_with_multiple_scenarios_and_other_bits(self):
        doc = u"""
Feature: Stuff
  Stuffing

  Background:
    Given you're all stuffed

  Scenario: Doing stuff
    Given there is stuff
    When I do stuff
    Then stuff happens

  Scenario: Doing other stuff
    When stuff happens
    Then I am stuffed

  Scenario: Doing different stuff
    Given stuff
    Then who gives a stuff
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.description, ["Stuffing"])

        assert(feature.background)
        self.compare_steps(feature.background.steps, [
            ('given', 'Given', "you're all stuffed", None, None)
        ])

        assert(len(feature.scenarios) == 3)

        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

        eq_(feature.scenarios[1].name, 'Doing other stuff')
        self.compare_steps(feature.scenarios[1].steps, [
            ('when', 'When', 'stuff happens', None, None),
            ('then', 'Then', 'I am stuffed', None, None),
        ])

        eq_(feature.scenarios[2].name, 'Doing different stuff')
        self.compare_steps(feature.scenarios[2].steps, [
            ('given', 'Given', 'stuff', None, None),
            ('then', 'Then', 'who gives a stuff', None, None),
        ])

    def test_parses_feature_with_a_scenario_with_and_and_but(self):
        doc = u"""
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff
    And some other stuff
    When I do stuff
    Then stuff happens
    But not the bad stuff
""".lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', None, None),
            ('given', 'And', 'some other stuff', None, None),
            ('when', 'When', 'I do stuff', None, None),
            ('then', 'Then', 'stuff happens', None, None),
            ('then', 'But', 'not the bad stuff', None, None),
        ])

    def test_parses_feature_with_a_step_with_a_string_argument(self):
        doc = u'''
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff:
      """
      So
      Much
      Stuff
      """
    Then stuff happens
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', "So\nMuch\nStuff", None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_string_argument_correctly_handle_whitespace(self):
        doc = u'''
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff:
      """
      So
        Much
          Stuff
        Has
      Indents
      """
    Then stuff happens
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        string = "So\n  Much\n    Stuff\n  Has\nIndents"
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', string, None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_feature_with_a_step_with_a_string_with_blank_lines(self):
        doc = u'''
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff:
      """
      So

      Much


      Stuff
      """
    Then stuff happens
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', "So\n\nMuch\n\n\nStuff", None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    # MORE-JE-ADDED:
    def test_parses_string_argument_without_stripping_empty_lines(self):
        # -- ISSUE 44: Parser removes comments in multiline text string.
        doc = u'''
Feature: Multiline

  Scenario: Multiline Text with Comments
    Given a multiline argument with:
      """

      """
    And a multiline argument with:
      """
      Alpha.

      Omega.
      """
    Then empty middle lines are not stripped
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Multiline")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, "Multiline Text with Comments")
        text1 = ""
        text2 = "Alpha.\n\nOmega."
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'a multiline argument with', text1, None),
            ('given', 'And',   'a multiline argument with', text2, None),
            ('then', 'Then', 'empty middle lines are not stripped', None, None),
        ])

    def test_parses_feature_with_a_step_with_a_string_with_comments(self):
        doc = u'''
Feature: Stuff

  Scenario: Doing stuff
    Given there is stuff:
      """
      So
      Much
      # Derp
      """
    Then stuff happens
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'there is stuff', "So\nMuch\n# Derp",
                None),
            ('then', 'Then', 'stuff happens', None, None),
        ])

    def test_parses_feature_with_a_step_with_a_table_argument(self):
        doc = u'''
Feature: Stuff

  Scenario: Doing stuff
    Given we classify stuff:
      | type of stuff | awesomeness | ridiculousness |
      | fluffy        | large       | frequent       |
      | lint          | low         | high           |
      | green         | variable    | awkward        |
    Then stuff is in buckets
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing stuff')
        table = model.Table(
            [u'type of stuff', u'awesomeness', u'ridiculousness'],
            0,
            [
                [u'fluffy', u'large', u'frequent'],
                [u'lint', u'low', u'high'],
                [u'green', u'variable', u'awkward'],
            ]
        )
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we classify stuff', None, table),
            ('then', 'Then', 'stuff is in buckets', None, None),
        ])

    def test_parses_feature_with_a_scenario_outline(self):
        doc = u'''
Feature: Stuff

  Scenario Outline: Doing all sorts of stuff
    Given we have <Stuff>
    When we do stuff
    Then we have <Things>

    Examples: Some stuff
      | Stuff      | Things   |
      | wool       | felt     |
      | cotton     | thread   |
      | wood       | paper    |
      | explosives | hilarity |
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing all sorts of stuff')

        table = model.Table(
            [u'Stuff', u'Things'],
            0,
            [
                [u'wool', u'felt'],
                [u'cotton', u'thread'],
                [u'wood', u'paper'],
                [u'explosives', u'hilarity'],
            ]
        )
        eq_(feature.scenarios[0].examples[0].name, 'Some stuff')
        eq_(feature.scenarios[0].examples[0].table, table)
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we have <Stuff>', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have <Things>', None, None),
        ])

    def test_parses_feature_with_a_scenario_outline_with_multiple_examples(self):
        doc = u'''
Feature: Stuff

  Scenario Outline: Doing all sorts of stuff
    Given we have <Stuff>
    When we do stuff
    Then we have <Things>

    Examples: Some stuff
      | Stuff      | Things   |
      | wool       | felt     |
      | cotton     | thread   |

    Examples: Some other stuff
      | Stuff      | Things   |
      | wood       | paper    |
      | explosives | hilarity |
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing all sorts of stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we have <Stuff>', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have <Things>', None, None),
        ])

        table = model.Table(
            [u'Stuff', u'Things'],
            0,
            [
                [u'wool', u'felt'],
                [u'cotton', u'thread'],
            ]
        )
        eq_(feature.scenarios[0].examples[0].name, 'Some stuff')
        eq_(feature.scenarios[0].examples[0].table, table)

        table = model.Table(
            [u'Stuff', u'Things'],
            0,
            [
                [u'wood', u'paper'],
                [u'explosives', u'hilarity'],
            ]
        )
        eq_(feature.scenarios[0].examples[1].name, 'Some other stuff')
        eq_(feature.scenarios[0].examples[1].table, table)

    def test_parses_feature_with_a_scenario_outline_with_tags(self):
        doc = u'''
Feature: Stuff

  @stuff @derp
  Scenario Outline: Doing all sorts of stuff
    Given we have <Stuff>
    When we do stuff
    Then we have <Things>

    Examples: Some stuff
      | Stuff      | Things   |
      | wool       | felt     |
      | cotton     | thread   |
      | wood       | paper    |
      | explosives | hilarity |
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'Doing all sorts of stuff')
        eq_(feature.scenarios[0].tags, [model.Tag(u'stuff', 1), model.Tag(u'derp', 1)])
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we have <Stuff>', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have <Things>', None, None),
        ])

        table = model.Table(
            [u'Stuff', u'Things'],
            0,
            [
                [u'wool', u'felt'],
                [u'cotton', u'thread'],
                [u'wood', u'paper'],
                [u'explosives', u'hilarity'],
            ]
        )
        eq_(feature.scenarios[0].examples[0].name, 'Some stuff')
        eq_(feature.scenarios[0].examples[0].table, table)

    def test_parses_feature_with_the_lot(self):
        doc = u'''
# This one's got comments too.

@derp
Feature: Stuff
  In order to test my parser
  As a test runner
  I want to run tests

  # A møøse once bit my sister
  Background:
    Given this is a test

  @fred
  Scenario: Testing stuff
    Given we are testing
    And this is only a test
    But this is an important test
    When we test with a multiline string:
      """
      Yarr, my hovercraft be full of stuff.
      Also, I be feelin' this pirate schtick be a mite overdone, me hearties.
          Also: rum.
      """
    Then we want it to work

  #These comments are everywhere man
  Scenario Outline: Gosh this is long
    Given this is <length>
    Then we want it to be <width>
    But not <height>

    Examples: Initial
      | length | width | height |
# I don't know why this one is here
      | 1      | 2     | 3      |
      | 4      | 5     | 6      |

    Examples: Subsequent
      | length | width | height |
      | 7      | 8     | 9      |

  Scenario: This one doesn't have a tag
    Given we don't have a tag
    Then we don't really mind

  @stuff @derp
  Scenario Outline: Doing all sorts of stuff
    Given we have <Stuff>
    When we do stuff with a table:
      | a | b | c | d | e |
      | 1 | 2 | 3 | 4 | 5 |
                             # I can see a comment line from here
      | 6 | 7 | 8 | 9 | 10 |
    Then we have <Things>

    Examples: Some stuff
      | Stuff      | Things   |
      | wool       | felt     |
      | cotton     | thread   |
      | wood       | paper    |
      | explosives | hilarity |
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Stuff")
        eq_(feature.tags, [model.Tag(u'derp', 1)])
        eq_(feature.description, ['In order to test my parser',
                                  'As a test runner',
                                  'I want to run tests'])

        assert(feature.background)
        self.compare_steps(feature.background.steps, [
            ('given', 'Given', 'this is a test', None, None)
        ])

        assert(len(feature.scenarios) == 4)

        eq_(feature.scenarios[0].name, 'Testing stuff')
        eq_(feature.scenarios[0].tags, [model.Tag(u'fred', 1)])
        string = '\n'.join([
            'Yarr, my hovercraft be full of stuff.',
            "Also, I be feelin' this pirate schtick be a mite overdone, " + \
                "me hearties.",
            '    Also: rum.'
        ])
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we are testing', None, None),
            ('given', 'And', 'this is only a test', None, None),
            ('given', 'But', 'this is an important test', None, None),
            ('when', 'When', 'we test with a multiline string', string, None),
            ('then', 'Then', 'we want it to work', None, None),
        ])

        eq_(feature.scenarios[1].name, 'Gosh this is long')
        eq_(feature.scenarios[1].tags, [])
        table = model.Table(
            [u'length', u'width', u'height'],
            0,
            [
                [u'1', u'2', u'3'],
                [u'4', u'5', u'6'],
            ]
        )
        eq_(feature.scenarios[1].examples[0].name, 'Initial')
        eq_(feature.scenarios[1].examples[0].table, table)
        table = model.Table(
            [u'length', u'width', u'height'],
            0,
            [
                [u'7', u'8', u'9'],
            ]
        )
        eq_(feature.scenarios[1].examples[1].name, 'Subsequent')
        eq_(feature.scenarios[1].examples[1].table, table)
        self.compare_steps(feature.scenarios[1].steps, [
            ('given', 'Given', 'this is <length>', None, None),
            ('then', 'Then', 'we want it to be <width>', None, None),
            ('then', 'But', 'not <height>', None, None),
        ])

        eq_(feature.scenarios[2].name, "This one doesn't have a tag")
        eq_(feature.scenarios[2].tags, [])
        self.compare_steps(feature.scenarios[2].steps, [
            ('given', 'Given', "we don't have a tag", None, None),
            ('then', 'Then', "we don't really mind", None, None),
        ])

        table = model.Table(
            [u'Stuff', u'Things'],
            0,
            [
                [u'wool', u'felt'],
                [u'cotton', u'thread'],
                [u'wood', u'paper'],
                [u'explosives', u'hilarity'],
            ]
        )
        eq_(feature.scenarios[3].name, 'Doing all sorts of stuff')
        eq_(feature.scenarios[3].tags, [model.Tag(u'stuff', 1), model.Tag(u'derp', 1)])
        eq_(feature.scenarios[3].examples[0].name, 'Some stuff')
        eq_(feature.scenarios[3].examples[0].table, table)
        table = model.Table(
            [u'a', u'b', u'c', u'd', u'e'],
            0,
            [
                [u'1', u'2', u'3', u'4', u'5'],
                [u'6', u'7', u'8', u'9', u'10'],
            ]
        )
        self.compare_steps(feature.scenarios[3].steps, [
            ('given', 'Given', 'we have <Stuff>', None, None),
            ('when', 'When', 'we do stuff with a table', None, table),
            ('then', 'Then', 'we have <Things>', None, None),
        ])


    def test_fails_to_parse_when_and_is_out_of_order(self):
        doc = u"""
Feature: Stuff

  Scenario: Failing at stuff
    And we should fail
""".lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)

    def test_fails_to_parse_when_but_is_out_of_order(self):
        doc = u"""
Feature: Stuff

  Scenario: Failing at stuff
    But we shall fail
""".lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)

    def test_fails_to_parse_when_examples_is_in_the_wrong_place(self):
        doc = u"""
Feature: Stuff

  Scenario: Failing at stuff
    But we shall fail

    Examples: Failure
      | Fail | Wheel|
""".lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)

class TestForeign(Common):
    def test_first_line_comment_sets_language(self):
        doc = u"""
# language: fr
Fonctionnalit\xe9: testing stuff
  Oh my god, it's full of stuff...
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_whitespace_before_first_line_comment_still_sets_language(self):
        doc = u"""


# language: cs
Po\u017eadavek: testing stuff
  Oh my god, it's full of stuff...
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_anything_before_language_comment_makes_it_not_count(self):
        doc = u"""

@wombles
# language: cy-GB
Arwedd: testing stuff
  Oh my god, it's full of stuff...
"""

        assert_raises(parser.ParserError, parser.parse_feature, doc)

    def test_defaults_to_DEFAULT_LANGUAGE(self):
        feature_kwd = i18n.languages[parser.DEFAULT_LANGUAGE]['feature'][0]
        doc = u"""

@wombles
# language: cs
%s: testing stuff
  Oh my god, it's full of stuff...
""" % feature_kwd

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_whitespace_in_the_language_comment_is_flexible_1(self):
        doc = u"""
#language:da
Egenskab: testing stuff
  Oh my god, it's full of stuff...
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_whitespace_in_the_language_comment_is_flexible_2(self):
        doc = u"""
# language:de
Funktionalit\xe4t: testing stuff
  Oh my god, it's full of stuff...
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_whitespace_in_the_language_comment_is_flexible_3(self):
        doc = u"""
#language: en-lol
OH HAI: testing stuff
  Oh my god, it's full of stuff...
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_whitespace_in_the_language_comment_is_flexible_4(self):
        doc = u"""
#       language:     lv
F\u012b\u010da: testing stuff
  Oh my god, it's full of stuff...
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

    def test_parses_french(self):
        doc = u"""
Fonctionnalit\xe9: testing stuff
  Oh my god, it's full of stuff...

  Contexte:
    Soit I found some stuff

  Sc\xe9nario: test stuff
    Soit I am testing stuff
    Alors it should work

  Sc\xe9nario: test more stuff
    Soit I am testing stuff
    Alors it will work
""".lstrip()
        feature = parser.parse_feature(doc, 'fr')
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])
        assert(feature.background)
        self.compare_steps(feature.background.steps, [
            ('given', 'Soit', 'I found some stuff', None, None),
        ])

        assert(len(feature.scenarios) == 2)
        eq_(feature.scenarios[0].name, 'test stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Soit', 'I am testing stuff', None, None),
            ('then', 'Alors', 'it should work', None, None),
        ])

    def test_parses_french_multi_word(self):
        doc = u"""
Fonctionnalit\xe9: testing stuff
  Oh my god, it's full of stuff...

  Sc\xe9nario: test stuff
    Etant donn\xe9 I am testing stuff
    Alors it should work
""".lstrip()
        feature = parser.parse_feature(doc, 'fr')
        eq_(feature.name, "testing stuff")
        eq_(feature.description, ["Oh my god, it's full of stuff..."])

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, 'test stuff')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', u'Etant donn\xe9', 'I am testing stuff', None, None),
            ('then', 'Alors', 'it should work', None, None),
        ])
    test_parses_french_multi_word.go = 1

    def test_properly_handles_whitespace_on_keywords_that_do_not_want_it(self):
        doc = u"""
# language: zh-TW

\u529f\u80fd: I have no idea what I'm saying

  \u5834\u666f: No clue whatsoever
    \u5047\u8a2dI've got no idea
    \u7576I say things
    \u800c\u4e14People don't understand
    \u90a3\u9ebcPeople should laugh
    \u4f46\u662fI should take it well
"""

        feature = parser.parse_feature(doc)
        eq_(feature.name, "I have no idea what I'm saying")

        eq_(len(feature.scenarios), 1)
        eq_(feature.scenarios[0].name, 'No clue whatsoever')
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', u'\u5047\u8a2d', "I've got no idea", None, None),
            ('when', u'\u7576', 'I say things', None, None),
            ('when', u'\u800c\u4e14', "People don't understand", None, None),
            ('then', u'\u90a3\u9ebc', "People should laugh", None, None),
            ('then', u'\u4f46\u662f', "I should take it well", None, None),
        ])


class TestParser4ScenarioDescription(Common):

    def test_parse_scenario_description(self):
        doc = u'''
Feature: Scenario Description

  Scenario: With scenario description

    First line of scenario description.
    Second line of scenario description.

    Third line of scenario description (after an empty line).

      Given we have stuff
      When we do stuff
      Then we have things
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Scenario Description")

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, "With scenario description")
        eq_(feature.scenarios[0].tags, [])
        eq_(feature.scenarios[0].description, [
            "First line of scenario description.",
            "Second line of scenario description.",
            "Third line of scenario description (after an empty line).",
        ])
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we have stuff', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have things', None, None),
        ])


    def test_parse_scenario_with_description_but_without_steps(self):
        doc = u'''
Feature: Scenario Description

  Scenario: With description but without steps

    First line of scenario description.
    Second line of scenario description.

  Scenario: Another one
      Given we have stuff
      When we do stuff
      Then we have things
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Scenario Description")

        assert(len(feature.scenarios) == 2)
        eq_(feature.scenarios[0].name, "With description but without steps")
        eq_(feature.scenarios[0].tags, [])
        eq_(feature.scenarios[0].description, [
            "First line of scenario description.",
            "Second line of scenario description.",
        ])
        eq_(feature.scenarios[0].steps, [])

        eq_(feature.scenarios[1].name, "Another one")
        eq_(feature.scenarios[1].tags, [])
        eq_(feature.scenarios[1].description, [])
        self.compare_steps(feature.scenarios[1].steps, [
            ('given', 'Given', 'we have stuff', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have things', None, None),
        ])


    def test_parse_scenario_with_description_but_without_steps_followed_by_scenario_with_tags(self):
        doc = u'''
Feature: Scenario Description

  Scenario: With description but without steps

    First line of scenario description.
    Second line of scenario description.

  @foo @bar
  Scenario: Another one
      Given we have stuff
      When we do stuff
      Then we have things
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Scenario Description")

        assert(len(feature.scenarios) == 2)
        eq_(feature.scenarios[0].name, "With description but without steps")
        eq_(feature.scenarios[0].tags, [])
        eq_(feature.scenarios[0].description, [
            "First line of scenario description.",
            "Second line of scenario description.",
        ])
        eq_(feature.scenarios[0].steps, [])

        eq_(feature.scenarios[1].name, "Another one")
        eq_(feature.scenarios[1].tags, ["foo", "bar"])
        eq_(feature.scenarios[1].description, [])
        self.compare_steps(feature.scenarios[1].steps, [
            ('given', 'Given', 'we have stuff', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have things', None, None),
        ])

    def test_parse_two_scenarios_with_description(self):
        doc = u'''
Feature: Scenario Description

  Scenario: One with description but without steps

    First line of scenario description.
    Second line of scenario description.

  Scenario: Two with description and with steps

    Another line of scenario description.

      Given we have stuff
      When we do stuff
      Then we have things
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Scenario Description")

        assert(len(feature.scenarios) == 2)
        eq_(feature.scenarios[0].name, "One with description but without steps")
        eq_(feature.scenarios[0].tags, [])
        eq_(feature.scenarios[0].description, [
            "First line of scenario description.",
            "Second line of scenario description.",
        ])
        eq_(feature.scenarios[0].steps, [])

        eq_(feature.scenarios[1].name, "Two with description and with steps")
        eq_(feature.scenarios[1].tags, [])
        eq_(feature.scenarios[1].description, [
            "Another line of scenario description.",
        ])
        self.compare_steps(feature.scenarios[1].steps, [
            ('given', 'Given', 'we have stuff', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have things', None, None),
        ])


def parse_tags(line):
    the_parser = parser.Parser()
    return the_parser.parse_tags(line.strip())

class TestParser4Tags(Common):

    def test_parse_tags_with_one_tag(self):
        tags = parse_tags('@one  ')
        eq_(len(tags), 1)
        eq_(tags[0], "one")

    def test_parse_tags_with_more_tags(self):
        tags = parse_tags('@one  @two.three-four  @xxx')
        eq_(len(tags), 3)
        eq_(tags, [model.Tag(name, 1)
            for name in (u'one', u'two.three-four', u'xxx' )])

    def test_parse_tags_with_tag_and_comment(self):
        tags = parse_tags('@one  # @fake-tag-in-comment xxx')
        eq_(len(tags), 1)
        eq_(tags[0], "one")

    def test_parse_tags_with_tags_and_comment(self):
        tags = parse_tags('@one  @two.three-four  @xxx # @fake-tag-in-comment xxx')
        eq_(len(tags), 3)
        eq_(tags, [model.Tag(name, 1)
                   for name in (u'one', u'two.three-four', u'xxx' )])

    @raises(parser.ParserError)
    def test_parse_tags_with_invalid_tags(self):
        parse_tags('@one  invalid.tag boom')


class TestParser4Background(Common):

    def test_parse_background(self):
        doc = u'''
Feature: Background

  A feature description line 1.
  A feature description line 2.

  Background: One
    Given we init stuff
    When we init more stuff

  Scenario: One
    Given we have stuff
    When we do stuff
    Then we have things
'''.lstrip()
        feature = parser.parse_feature(doc)
        eq_(feature.name, "Background")
        eq_(feature.description, [
            "A feature description line 1.",
            "A feature description line 2.",
        ])
        assert feature.background is not None
        eq_(feature.background.name, "One")
        self.compare_steps(feature.background.steps, [
            ('given', 'Given', 'we init stuff', None, None),
            ('when', 'When', 'we init more stuff', None, None),
        ])

        assert(len(feature.scenarios) == 1)
        eq_(feature.scenarios[0].name, "One")
        eq_(feature.scenarios[0].tags, [])
        self.compare_steps(feature.scenarios[0].steps, [
            ('given', 'Given', 'we have stuff', None, None),
            ('when', 'When', 'we do stuff', None, None),
            ('then', 'Then', 'we have things', None, None),
        ])


    def test_parse_background_with_tags_should_fail(self):
        doc = u'''
Feature: Background with tags
  Expect that a ParserError occurs
  because Background does not support tags/tagging.

  @tags_are @not_supported
  @here
  Background: One
    Given we init stuff
'''.lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)


    def test_parse_two_background_should_fail(self):
        doc = u'''
Feature: Two Backgrounds
  Expect that a ParserError occurs
  because at most one Background is supported.

  Background: One
    Given we init stuff

  Background: Two
    When we init more stuff
'''.lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)


    def test_parse_background_after_scenario_should_fail(self):
        doc = u'''
Feature: Background after Scenario
  Expect that a ParserError occurs
  because Background is only allowed before any Scenario.

  Scenario: One
    Given we have stuff

  Background: Two
    When we init more stuff
'''.lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)


    def test_parse_background_after_scenario_outline_should_fail(self):
        doc = u'''
Feature: Background after ScenarioOutline
  Expect that a ParserError occurs
  because Background is only allowed before any ScenarioOuline.
  Scenario Outline: ...
    Given there is <name>

    Examples:
      | name  |
      | Alice |

  Background: Two
    When we init more stuff
'''.lstrip()
        assert_raises(parser.ParserError, parser.parse_feature, doc)


class TestParser4Steps(Common):
    """
    Tests parser.parse_steps() and parser.Parser.parse_steps() functionality.
    """

    def test_parse_steps_with_simple_steps(self):
        doc = u'''
Given a simple step
When I have another simple step
 And I have another simple step
Then every step will be parsed without errors
'''.lstrip()
        steps = parser.parse_steps(doc)
        eq_(len(steps), 4)
        # -- EXPECTED STEP DATA:
        #     SCHEMA: step_type, keyword, name, text, table
        self.compare_steps(steps, [
            ("given", "Given", "a simple step", None, None),
            ("when",  "When",  "I have another simple step", None, None),
            ("when",  "And",   "I have another simple step", None, None),
            ("then",  "Then",  "every step will be parsed without errors",
                                None, None),
        ])

    def test_parse_steps_with_multiline_text(self):
        doc = u'''
Given a step with multi-line text:
    """
    Lorem ipsum
    Ipsum lorem
    """
When I have a step with multi-line text:
    """
    Ipsum lorem
    Lorem ipsum
    """
Then every step will be parsed without errors
'''.lstrip()
        steps = parser.parse_steps(doc)
        eq_(len(steps), 3)
        # -- EXPECTED STEP DATA:
        #     SCHEMA: step_type, keyword, name, text, table
        text1 = "Lorem ipsum\nIpsum lorem"
        text2 = "Ipsum lorem\nLorem ipsum"
        self.compare_steps(steps, [
            ("given", "Given", "a step with multi-line text", text1, None),
            ("when",  "When",  "I have a step with multi-line text", text2, None),
            ("then",  "Then",  "every step will be parsed without errors",
             None, None),
        ])

    def test_parse_steps_when_last_step_has_multiline_text(self):
        doc = u'''
Given a simple step
Then the last step has multi-line text:
    """
    Lorem ipsum
    Ipsum lorem
    """
'''.lstrip()
        steps = parser.parse_steps(doc)
        eq_(len(steps), 2)
        # -- EXPECTED STEP DATA:
        #     SCHEMA: step_type, keyword, name, text, table
        text2 = "Lorem ipsum\nIpsum lorem"
        self.compare_steps(steps, [
            ("given", "Given", "a simple step", None, None),
            ("then",  "Then",  "the last step has multi-line text", text2, None),
        ])

    def test_parse_steps_with_table(self):
        doc = u'''
Given a step with a table:
    | Name  | Age |
    | Alice |  12 |
    | Bob   |  23 |
When I have a step with a table:
    | Country | Capital |
    | France  | Paris   |
    | Germany | Berlin  |
    | Spain   | Madrid  |
    | USA     | Washington |
Then every step will be parsed without errors
'''.lstrip()
        steps = parser.parse_steps(doc)
        eq_(len(steps), 3)
        # -- EXPECTED STEP DATA:
        #     SCHEMA: step_type, keyword, name, text, table
        table1 = model.Table([u"Name", u"Age"], 0, [
            [ u"Alice", u"12" ],
            [ u"Bob",   u"23" ],
            ])
        table2 = model.Table([u"Country", u"Capital"], 0, [
            [ u"France",   u"Paris" ],
            [ u"Germany",  u"Berlin" ],
            [ u"Spain",    u"Madrid" ],
            [ u"USA",      u"Washington" ],
            ])
        self.compare_steps(steps, [
            ("given", "Given", "a step with a table", None, table1),
            ("when",  "When",  "I have a step with a table", None, table2),
            ("then",  "Then",  "every step will be parsed without errors",
             None, None),
        ])

    def test_parse_steps_when_last_step_has_a_table(self):
        doc = u'''
Given a simple step
Then the last step has a final table:
    | Name   | City |
    | Alonso | Barcelona |
    | Bred   | London  |
'''.lstrip()
        steps = parser.parse_steps(doc)
        eq_(len(steps), 2)
        # -- EXPECTED STEP DATA:
        #     SCHEMA: step_type, keyword, name, text, table
        table2 = model.Table([u"Name", u"City"], 0, [
            [ u"Alonso", u"Barcelona" ],
            [ u"Bred",   u"London" ],
            ])
        self.compare_steps(steps, [
            ("given", "Given", "a simple step", None, None),
            ("then",  "Then",  "the last step has a final table", None, table2),
        ])

    @raises(parser.ParserError)
    def test_parse_steps_with_malformed_table(self):
        doc = u'''
Given a step with a malformed table:
    | Name   | City |
    | Alonso | Barcelona | 2004 |
    | Bred   | London    | 2010 |
'''.lstrip()
        steps = parser.parse_steps(doc)

########NEW FILE########
__FILENAME__ = test_runner
# -*- coding: utf-8 -*-

from __future__ import with_statement
from collections import defaultdict
import os.path
import StringIO
import sys
import warnings
import tempfile

from mock import Mock, patch
from nose.tools import *
import unittest

from behave import model, parser, runner, step_registry
from behave.configuration import ConfigError
from behave.log_capture import LoggingCapture
from behave.formatter.base import StreamOpener


class TestContext(unittest.TestCase):
    def setUp(self):
        r = Mock()
        self.config = r.config = Mock()
        r.config.verbose = False
        self.context = runner.Context(r)

    def test_user_mode_shall_restore_behave_mode(self):
        # -- CASE: No exception is raised.
        with self.context.user_mode():
            eq_(self.context._mode, runner.Context.USER)
            self.context.thing = 'stuff'
        eq_(self.context._mode, runner.Context.BEHAVE)

    def test_user_mode_shall_restore_behave_mode_if_assert_fails(self):
        try:
            with self.context.user_mode():
                eq_(self.context._mode, runner.Context.USER)
                assert False, "XFAIL"
        except AssertionError:
            eq_(self.context._mode, runner.Context.BEHAVE)

    def test_user_mode_shall_restore_behave_mode_if_exception_is_raised(self):
        try:
            with self.context.user_mode():
                eq_(self.context._mode, runner.Context.USER)
                raise RuntimeError("XFAIL")
        except Exception:
            eq_(self.context._mode, runner.Context.BEHAVE)

    def test_context_contains(self):
        eq_('thing' in self.context, False)
        self.context.thing = 'stuff'
        eq_('thing' in self.context, True)
        self.context._push()
        eq_('thing' in self.context, True)

    def test_attribute_set_at_upper_level_visible_at_lower_level(self):
        self.context.thing = 'stuff'
        self.context._push()
        eq_(self.context.thing, 'stuff')

    def test_attribute_set_at_lower_level_not_visible_at_upper_level(self):
        self.context._push()
        self.context.thing = 'stuff'
        self.context._pop()
        assert getattr(self.context, 'thing', None) is None

    def test_attributes_set_at_upper_level_visible_at_lower_level(self):
        self.context.thing = 'stuff'
        self.context._push()
        eq_(self.context.thing, 'stuff')
        self.context.other_thing = 'more stuff'
        self.context._push()
        eq_(self.context.thing, 'stuff')
        eq_(self.context.other_thing, 'more stuff')
        self.context.third_thing = 'wombats'
        self.context._push()
        eq_(self.context.thing, 'stuff')
        eq_(self.context.other_thing, 'more stuff')
        eq_(self.context.third_thing, 'wombats')

    def test_attributes_set_at_lower_level_not_visible_at_upper_level(self):
        self.context.thing = 'stuff'

        self.context._push()
        self.context.other_thing = 'more stuff'

        self.context._push()
        self.context.third_thing = 'wombats'
        eq_(self.context.thing, 'stuff')
        eq_(self.context.other_thing, 'more stuff')
        eq_(self.context.third_thing, 'wombats')

        self.context._pop()
        eq_(self.context.thing, 'stuff')
        eq_(self.context.other_thing, 'more stuff')
        assert getattr(self.context, 'third_thing', None) is None, '%s is not None' % self.context.third_thing

        self.context._pop()
        eq_(self.context.thing, 'stuff')
        assert getattr(self.context, 'other_thing', None) is None, '%s is not None' % self.context.other_thing
        assert getattr(self.context, 'third_thing', None) is None, '%s is not None' % self.context.third_thing

    def test_masking_existing_user_attribute_when_verbose_causes_warning(self):
        warns = []

        def catch_warning(*args, **kwargs):
            warns.append(args[0])

        old_showwarning = warnings.showwarning
        warnings.showwarning = catch_warning

        self.config.verbose = True
        with self.context.user_mode():
            self.context.thing = 'stuff'
            self.context._push()
            self.context.thing = 'other stuff'

        warnings.showwarning = old_showwarning

        print repr(warns)
        assert warns, 'warns is empty!'
        warning = warns[0]
        assert isinstance(warning, runner.ContextMaskWarning), 'warning is not a ContextMaskWarning'
        info = warning.args[0]
        assert info.startswith('user code'), "%r doesn't start with 'user code'" % info
        assert "'thing'" in info, '%r not in %r' % ("'thing'", info)
        assert 'tutorial' in info, '"tutorial" not in %r' % (info, )

    def test_masking_existing_user_attribute_when_not_verbose_causes_no_warning(self):
        warns = []

        def catch_warning(*args, **kwargs):
            warns.append(args[0])

        old_showwarning = warnings.showwarning
        warnings.showwarning = catch_warning

        # explicit
        self.config.verbose = False
        with self.context.user_mode():
            self.context.thing = 'stuff'
            self.context._push()
            self.context.thing = 'other stuff'

        warnings.showwarning = old_showwarning

        assert not warns

    def test_behave_masking_user_attribute_causes_warning(self):
        warns = []

        def catch_warning(*args, **kwargs):
            warns.append(args[0])

        old_showwarning = warnings.showwarning
        warnings.showwarning = catch_warning

        with self.context.user_mode():
            self.context.thing = 'stuff'
        self.context._push()
        self.context.thing = 'other stuff'

        warnings.showwarning = old_showwarning

        print repr(warns)
        assert warns, 'warns is empty!'
        warning = warns[0]
        assert isinstance(warning, runner.ContextMaskWarning), 'warning is not a ContextMaskWarning'
        info = warning.args[0]
        assert info.startswith('behave runner'), "%r doesn't start with 'behave runner'" % info
        assert "'thing'" in info, '%r not in %r' % ("'thing'", info)
        file = __file__.rsplit('.', 1)[0]
        assert file in info, '%r not in %r' % (file, info)

    def test_setting_root_attribute_that_masks_existing_causes_warning(self):
        warns = []

        def catch_warning(*args, **kwargs):
            warns.append(args[0])

        old_showwarning = warnings.showwarning
        warnings.showwarning = catch_warning

        with self.context.user_mode():
            self.context._push()
            self.context.thing = 'teak'
        self.context._set_root_attribute('thing', 'oak')

        warnings.showwarning = old_showwarning

        print repr(warns)
        assert warns
        warning = warns[0]
        assert isinstance(warning, runner.ContextMaskWarning)
        info = warning.args[0]
        assert info.startswith('behave runner'), "%r doesn't start with 'behave runner'" % info
        assert "'thing'" in info, '%r not in %r' % ("'thing'", info)
        file = __file__.rsplit('.', 1)[0]
        assert file in info, '%r not in %r' % (file, info)

    def test_context_deletable(self):
        eq_('thing' in self.context, False)
        self.context.thing = 'stuff'
        eq_('thing' in self.context, True)
        del self.context.thing
        eq_('thing' in self.context, False)

    @raises(AttributeError)
    def test_context_deletable_raises(self):
        eq_('thing' in self.context, False)
        self.context.thing = 'stuff'
        eq_('thing' in self.context, True)
        self.context._push()
        eq_('thing' in self.context, True)
        del self.context.thing

class ExampleSteps(object):
    text  = None
    table = None

    @staticmethod
    def step_passes(context):
        pass

    @staticmethod
    def step_fails(context):
        assert False, "XFAIL"

    @classmethod
    def step_with_text(cls, context):
        assert context.text is not None, "REQUIRE: multi-line text"
        cls.text = context.text

    @classmethod
    def step_with_table(cls, context):
        assert context.table, "REQUIRE: table"
        cls.table = context.table

    @classmethod
    def register_steps_with(cls, step_registry):
        STEP_DEFINITIONS = [
            ("step", "a step passes", cls.step_passes),
            ("step", "a step fails",  cls.step_fails),
            ("step", "a step with text",    cls.step_with_text),
            ("step", "a step with a table",  cls.step_with_table),
        ]
        for keyword, string, func in STEP_DEFINITIONS:
            step_registry.add_step_definition(keyword, string, func)

class TestContext_ExecuteSteps(unittest.TestCase):
    """
    Test the behave.runner.Context.execute_steps() functionality.
    """
    step_registry = None

    def setUp(self):
        runner_ = Mock()
        self.config = runner_.config = Mock()
        runner_.config.verbose = False
        runner_.config.stdout_capture  = False
        runner_.config.stderr_capture  = False
        runner_.config.log_capture  = False
        self.context = runner.Context(runner_)
        # self.context.text = None
        # self.context.table = None
        runner_.context = self.context
        self.context.feature = Mock()
        self.context.feature.parser = parser.Parser()
        if not self.step_registry:
            # -- SETUP ONCE:
            self.step_registry = step_registry.StepRegistry()
            ExampleSteps.register_steps_with(self.step_registry)
        ExampleSteps.text  = None
        ExampleSteps.table = None

    def test_execute_steps_with_simple_steps(self):
        doc = u'''
Given a step passes
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            result = self.context.execute_steps(doc)
            eq_(result, True)

    def test_execute_steps_with_failing_step(self):
        doc = u'''
Given a step passes
When a step fails
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            try:
                result = self.context.execute_steps(doc)
            except AssertionError, e:  # -- PY26-CLEANUP-MARK
                ok_("FAILED SUB-STEP: When a step fails" in str(e))

    def test_execute_steps_with_undefined_step(self):
        doc = u'''
Given a step passes
When a step is undefined
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            try:
                result = self.context.execute_steps(doc)
            except AssertionError, e:  # -- PY26-CLEANUP-MARK
                ok_("UNDEFINED SUB-STEP: When a step is undefined" in str(e))

    def test_execute_steps_with_text(self):
        doc = u'''
Given a step passes
When a step with text:
    """
    Lorem ipsum
    Ipsum lorem
    """
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            result = self.context.execute_steps(doc)
            expected_text = "Lorem ipsum\nIpsum lorem"
            eq_(result, True)
            eq_(expected_text, ExampleSteps.text)

    def test_execute_steps_with_table(self):
        doc = u'''
Given a step with a table:
    | Name  | Age |
    | Alice |  12 |
    | Bob   |  23 |
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            result = self.context.execute_steps(doc)
            expected_table = model.Table([u"Name", u"Age"], 0, [
                    [u"Alice", u"12"],
                    [u"Bob",   u"23"],
            ])
            eq_(result, True)
            eq_(expected_table, ExampleSteps.table)

    def test_context_table_is_restored_after_execute_steps_without_table(self):
        doc = u'''
Given a step passes
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            original_table = "<ORIGINAL_TABLE>"
            self.context.table = original_table
            self.context.execute_steps(doc)
            eq_(self.context.table, original_table)

    def test_context_table_is_restored_after_execute_steps_with_table(self):
        doc = u'''
Given a step with a table:
    | Name  | Age |
    | Alice |  12 |
    | Bob   |  23 |
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            original_table = "<ORIGINAL_TABLE>"
            self.context.table = original_table
            self.context.execute_steps(doc)
            eq_(self.context.table, original_table)

    def test_context_text_is_restored_after_execute_steps_without_text(self):
        doc = u'''
Given a step passes
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            original_text = "<ORIGINAL_TEXT>"
            self.context.text = original_text
            self.context.execute_steps(doc)
            eq_(self.context.text, original_text)

    def test_context_text_is_restored_after_execute_steps_with_text(self):
        doc = u'''
Given a step passes
When a step with text:
    """
    Lorem ipsum
    Ipsum lorem
    """
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            original_text = "<ORIGINAL_TEXT>"
            self.context.text = original_text
            self.context.execute_steps(doc)
            eq_(self.context.text, original_text)


    @raises(ValueError)
    def test_execute_steps_should_fail_when_called_without_feature(self):
        doc = u'''
Given a passes
Then a step passes
'''.lstrip()
        with patch('behave.step_registry.registry', self.step_registry):
            self.context.feature = None
            self.context.execute_steps(doc)


class TestRunner(object):
    def test_load_hooks_execfiles_hook_file(self):
        with patch('behave.runner.exec_file') as ef:
            with patch('os.path.exists') as exists:
                exists.return_value = True
                base_dir = 'fake/path'
                hooks_path = os.path.join(base_dir, 'environment.py')

                r = runner.Runner(None)
                r.base_dir = base_dir
                r.load_hooks()

                exists.assert_called_with(hooks_path)
                ef.assert_called_with(hooks_path, r.hooks)

    def test_run_hook_runs_a_hook_that_exists(self):
        r = runner.Runner(None)
        r.config = Mock()
        r.config.dry_run = False
        r.hooks['before_lunch'] = hook = Mock()
        args = (runner.Context(Mock()), Mock(), Mock())
        r.run_hook('before_lunch', *args)

        hook.assert_called_with(*args)

    def test_run_hook_does_not_runs_a_hook_that_exists_if_dry_run(self):
        r = runner.Runner(None)
        r.config = Mock()
        r.config.dry_run = True
        r.hooks['before_lunch'] = hook = Mock()
        args = (runner.Context(Mock()), Mock(), Mock())
        r.run_hook('before_lunch', *args)

        assert len(hook.call_args_list) == 0

    def test_setup_capture_creates_stringio_for_stdout(self):
        r = runner.Runner(Mock())
        r.config.stdout_capture = True
        r.config.log_capture = False
        r.context = Mock()

        r.setup_capture()

        assert r.stdout_capture is not None
        assert isinstance(r.stdout_capture, StringIO.StringIO)

    def test_setup_capture_does_not_create_stringio_if_not_wanted(self):
        r = runner.Runner(Mock())
        r.config.stdout_capture = False
        r.config.stderr_capture = False
        r.config.log_capture = False

        r.setup_capture()

        assert r.stdout_capture is None

    @patch('behave.runner.LoggingCapture')
    def test_setup_capture_creates_memory_handler_for_logging(self, handler):
        r = runner.Runner(Mock())
        r.config.stdout_capture = False
        r.config.log_capture = True
        r.context = Mock()

        r.setup_capture()

        assert r.log_capture is not None
        handler.assert_called_with(r.config)
        r.log_capture.inveigle.assert_called_with()

    def test_setup_capture_does_not_create_memory_handler_if_not_wanted(self):
        r = runner.Runner(Mock())
        r.config.stdout_capture = False
        r.config.stderr_capture = False
        r.config.log_capture = False

        r.setup_capture()

        assert r.log_capture is None

    def test_start_stop_capture_switcheroos_sys_stdout(self):
        old_stdout = sys.stdout
        sys.stdout = new_stdout = Mock()

        r = runner.Runner(Mock())
        r.config.stdout_capture = True
        r.config.log_capture = False
        r.context = Mock()

        r.setup_capture()
        r.start_capture()

        eq_(sys.stdout, r.stdout_capture)

        r.stop_capture()

        eq_(sys.stdout, new_stdout)

        sys.stdout = old_stdout

    def test_start_stop_capture_leaves_sys_stdout_alone_if_off(self):
        r = runner.Runner(Mock())
        r.config.stdout_capture = False
        r.config.log_capture = False

        old_stdout = sys.stdout

        r.start_capture()

        eq_(sys.stdout, old_stdout)

        r.stop_capture()

        eq_(sys.stdout, old_stdout)

    def test_teardown_capture_removes_log_tap(self):
        r = runner.Runner(Mock())
        r.config.stdout_capture = False
        r.config.log_capture = True

        r.log_capture = Mock()

        r.teardown_capture()

        r.log_capture.abandon.assert_called_with()

    def test_exec_file(self):
        fn = tempfile.mktemp()
        with open(fn, 'w') as f:
            f.write('spam = __file__\n')
        g = {}
        l = {}
        runner.exec_file(fn, g, l)
        assert '__file__' in l
        assert 'spam' in l, '"spam" variable not set in locals (%r)' % (g, l)
        eq_(l['spam'], fn)

    def test_run_returns_true_if_everything_passed(self):
        r = runner.Runner(Mock())
        r.setup_capture = Mock()
        r.setup_paths = Mock()
        r.run_with_paths = Mock()
        r.run_with_paths.return_value = True
        assert r.run()

    def test_run_returns_false_if_anything_failed(self):
        r = runner.Runner(Mock())
        r.setup_capture = Mock()
        r.setup_paths = Mock()
        r.run_with_paths = Mock()
        r.run_with_paths.return_value = False
        assert not r.run()


class TestRunWithPaths(unittest.TestCase):
    def setUp(self):
        self.config = Mock()
        self.config.reporters = []
        self.config.logging_level = None
        self.config.logging_filter = None
        self.config.outputs = [ Mock(), StreamOpener(stream=sys.stdout) ]
        self.config.format = [ "plain", "progress" ]
        self.runner = runner.Runner(self.config)
        self.load_hooks = self.runner.load_hooks = Mock()
        self.load_step_definitions = self.runner.load_step_definitions = Mock()
        self.run_hook = self.runner.run_hook = Mock()
        self.run_step = self.runner.run_step = Mock()
        self.feature_locations = self.runner.feature_locations = Mock()
        self.calculate_summaries = self.runner.calculate_summaries = Mock()

        self.formatter_class = patch('behave.formatter.pretty.PrettyFormatter')
        formatter_class = self.formatter_class.start()
        formatter_class.return_value = self.formatter = Mock()

    def tearDown(self):
        self.formatter_class.stop()

    def test_loads_hooks_and_step_definitions(self):
        self.feature_locations.return_value = []
        self.runner.run_with_paths()

        assert self.load_hooks.called
        assert self.load_step_definitions.called

    def test_runs_before_all_and_after_all_hooks(self):
        # Make runner.feature_locations() and runner.run_hook() the same mock so
        # we can make sure things happen in the right order.
        self.runner.feature_locations = self.run_hook
        self.runner.feature_locations.return_value = []
        self.runner.context = Mock()
        self.runner.run_with_paths()

        eq_(self.run_hook.call_args_list, [
            ((), {}),
            (('before_all', self.runner.context), {}),
            (('after_all', self.runner.context), {}),
        ])

    @patch('behave.parser.parse_file')
    @patch('os.path.abspath')
    def test_parses_feature_files_and_appends_to_feature_list(self, abspath,
                                                              parse_file):
        feature_locations = ['one', 'two', 'three']
        feature = Mock()
        feature.tags = []
        feature.__iter__ = Mock(return_value=iter([]))
        feature.run.return_value = False
        self.runner.feature_locations.return_value = feature_locations
        abspath.side_effect = lambda x: x.upper()
        self.config.lang = 'fritz'
        self.config.format = ['plain']
        self.config.outputs = [ StreamOpener(stream=sys.stdout) ]
        self.config.output.encoding = None
        self.config.exclude = lambda s: False
        self.config.junit = False
        self.config.summary = False
        parse_file.return_value = feature

        self.runner.run_with_paths()

        expected_parse_file_args = \
            [((x.upper(),), {'language': 'fritz'}) for x in feature_locations]
        eq_(parse_file.call_args_list, expected_parse_file_args)
        eq_(self.runner.features, [feature] * 3)


class FsMock(object):
    def __init__(self, *paths):
        self.base = os.path.abspath('.')
        self.sep  = os.path.sep

        # This bit of gymnastics is to support Windows. We feed in a bunch of
        # paths in places using FsMock that assume that POSIX-style paths
        # work. This is faster than fixing all of those but at some point we
        # should totally do it properly with os.path.join() and all that.
        def full_split(path):
            bits = []

            while path:
                path, bit = os.path.split(path)
                bits.insert(0, bit)

            return bits

        paths = [os.path.join(self.base, *full_split(path)) for path in paths]
        print repr(paths)
        self.paths = paths
        self.files = set()
        self.dirs = defaultdict(list)
        separators = [sep for sep in (os.path.sep, os.path.altsep) if sep]
        for path in paths:
            if path[-1] in separators:
                self.dirs[path[:-1]] = []
                d, p = os.path.split(path[:-1])
                while d and p:
                    self.dirs[d].append(p)
                    d, p = os.path.split(d)
            else:
                self.files.add(path)
                d, f = os.path.split(path)
                self.dirs[d].append(f)
        self.calls = []

    def listdir(self, dir):
        # pylint: disable=W0622
        #   W0622   Redefining built-in dir
        self.calls.append(('listdir', dir))
        return self.dirs.get(dir, [])

    def isfile(self, path):
        self.calls.append(('isfile', path))
        return path in self.files

    def isdir(self, path):
        self.calls.append(('isdir', path))
        return path in self.dirs

    def exists(self, path):
        self.calls.append(('exists', path))
        return path in self.dirs or path in self.files

    def walk(self, path, l=None):
        if l is None:
            assert path in self.dirs, '%s not in %s' % (path, self.dirs)
            l = []
        dirnames = []
        filenames = []
        for e in self.dirs[path]:
            if os.path.join(path, e) in self.dirs:
                dirnames.append(e)
                self.walk(os.path.join(path, e), l)
            else:
                filenames.append(e)
        l.append((path, dirnames, filenames))
        return l

    # utilities that we need
    def dirname(self, path, orig=os.path.dirname):
        return orig(path)

    def abspath(self, path, orig=os.path.abspath):
        return orig(path)

    def join(self, a, b, orig=os.path.join):
        return orig(a, b)

    def split(self, path, orig=os.path.split):
        return orig(path)

    def splitdrive(self, path, orig=os.path.splitdrive):
        return orig(path)


class TestFeatureDirectory(object):
    def test_default_path_no_steps(self):
        config = Mock()
        config.paths = []
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock()

        # will look for a "features" directory and not find one
        with patch('os.path', fs):
            assert_raises(ConfigError, r.setup_paths)

        ok_(('isdir', os.path.join(fs.base, 'features', 'steps')) in fs.calls)

    def test_default_path_no_features(self):
        config = Mock()
        config.paths = []
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock('features/steps/')
        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                assert_raises(ConfigError, r.setup_paths)

    def test_default_path(self):
        config = Mock()
        config.paths = []
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock('features/steps/', 'features/foo.feature')

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()

        eq_(r.base_dir, os.path.abspath('features'))

    def test_supplied_feature_file(self):
        config = Mock()
        config.paths = ['foo.feature']
        config.verbose = True
        r = runner.Runner(config)
        r.context = Mock()

        fs = FsMock('steps/', 'foo.feature')

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()
        ok_(('isdir', os.path.join(fs.base, 'steps')) in fs.calls)
        ok_(('isfile', os.path.join(fs.base, 'foo.feature')) in fs.calls)

        eq_(r.base_dir, fs.base)

    def test_supplied_feature_file_no_steps(self):
        config = Mock()
        config.paths = ['foo.feature']
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock('foo.feature')

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    assert_raises(ConfigError, r.setup_paths)

    def test_supplied_feature_directory(self):
        config = Mock()
        config.paths = ['spam']
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock('spam/', 'spam/steps/', 'spam/foo.feature')

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()

        ok_(('isdir', os.path.join(fs.base, 'spam', 'steps')) in fs.calls)

        eq_(r.base_dir, os.path.join(fs.base, 'spam'))

    def test_supplied_feature_directory_no_steps(self):
        config = Mock()
        config.paths = ['spam']
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock('spam/', 'spam/foo.feature')

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                assert_raises(ConfigError, r.setup_paths)

        ok_(('isdir', os.path.join(fs.base, 'spam', 'steps')) in fs.calls)

    def test_supplied_feature_directory_missing(self):
        config = Mock()
        config.paths = ['spam']
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock()

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                assert_raises(ConfigError, r.setup_paths)


class TestFeatureDirectoryLayout2(object):
    def test_default_path(self):
        config = Mock()
        config.paths = []
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock(
            'features/',
            'features/steps/',
            'features/group1/',
            'features/group1/foo.feature',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()

        eq_(r.base_dir, os.path.abspath('features'))

    def test_supplied_root_directory(self):
        config = Mock()
        config.paths = [ 'features' ]
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock(
            'features/',
            'features/group1/',
            'features/group1/foo.feature',
            'features/steps/',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()

        ok_(('isdir',  os.path.join(fs.base, 'features', 'steps')) in fs.calls)
        eq_(r.base_dir, os.path.join(fs.base, 'features'))

    def test_supplied_root_directory_no_steps(self):
        config = Mock()
        config.paths = [ 'features' ]
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock(
            'features/',
            'features/group1/',
            'features/group1/foo.feature',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    assert_raises(ConfigError, r.setup_paths)

        ok_(('isdir',  os.path.join(fs.base, 'features', 'steps')) in fs.calls)
        eq_(r.base_dir, None)


    def test_supplied_feature_file(self):
        config = Mock()
        config.paths = [ 'features/group1/foo.feature' ]
        config.verbose = True
        r = runner.Runner(config)
        r.context = Mock()

        fs = FsMock(
            'features/',
            'features/group1/',
            'features/group1/foo.feature',
            'features/steps/',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()

        ok_(('isdir',  os.path.join(fs.base, 'features', 'steps'))  in fs.calls)
        ok_(('isfile', os.path.join(fs.base, 'features', 'group1', 'foo.feature')) in fs.calls)
        eq_(r.base_dir, fs.join(fs.base, "features"))

    def test_supplied_feature_file_no_steps(self):
        config = Mock()
        config.paths = [ 'features/group1/foo.feature' ]
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock(
            'features/',
            'features/group1/',
            'features/group1/foo.feature',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    assert_raises(ConfigError, r.setup_paths)

    def test_supplied_feature_directory(self):
        config = Mock()
        config.paths = [ 'features/group1' ]
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock(
            'features/',
            'features/group1/',
            'features/group1/foo.feature',
            'features/steps/',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                with r.path_manager:
                    r.setup_paths()

        ok_(('isdir',  os.path.join(fs.base, 'features', 'steps')) in fs.calls)
        eq_(r.base_dir, os.path.join(fs.base, 'features'))


    def test_supplied_feature_directory_no_steps(self):
        config = Mock()
        config.paths = [ 'features/group1' ]
        config.verbose = True
        r = runner.Runner(config)

        fs = FsMock(
            'features/',
            'features/group1/',
            'features/group1/foo.feature',
        )

        with patch('os.path', fs):
            with patch('os.walk', fs.walk):
                assert_raises(ConfigError, r.setup_paths)

        ok_(('isdir',  os.path.join(fs.base, 'features', 'steps')) in fs.calls)


########NEW FILE########
__FILENAME__ = test_step_registry
from __future__ import with_statement

from mock import Mock, patch
from nose.tools import *
from behave import step_registry

class TestStepRegistry(object):
    def test_add_step_definition_adds_to_lowercased_keyword(self):
        registry = step_registry.StepRegistry()
        with patch('behave.matchers.get_matcher') as get_matcher:
            func = lambda x: -x
            string = 'just a test string'
            magic_object = object()
            get_matcher.return_value = magic_object

            for step_type in registry.steps.keys():
                l = []
                registry.steps[step_type] = l

                registry.add_step_definition(step_type.upper(), string, func)

                get_matcher.assert_called_with(func, string)
                eq_(l, [magic_object])

    def test_find_match_with_specific_step_type_also_searches_generic(self):
        registry = step_registry.StepRegistry()

        given_mock = Mock()
        given_mock.match.return_value = None
        step_mock = Mock()
        step_mock.match.return_value = None

        registry.steps['given'].append(given_mock)
        registry.steps['step'].append(step_mock)

        step = Mock()
        step.step_type = 'given'
        step.name = 'just a test step'

        assert registry.find_match(step) is None

        given_mock.match.assert_called_with(step.name)
        step_mock.match.assert_called_with(step.name)

    def test_find_match_with_no_match_returns_none(self):
        registry = step_registry.StepRegistry()

        step_defs = [Mock() for x in range(0, 10)]
        for mock in step_defs:
            mock.match.return_value = None

        registry.steps['when'] = step_defs

        step = Mock()
        step.step_type = 'when'
        step.name = 'just a test step'

        assert registry.find_match(step) is None

    def test_find_match_with_a_match_returns_match(self):
        registry = step_registry.StepRegistry()

        step_defs = [Mock() for x in range(0, 10)]
        for mock in step_defs:
            mock.match.return_value = None
        magic_object = object()
        step_defs[5].match.return_value = magic_object

        registry.steps['then'] = step_defs

        step = Mock()
        step.step_type = 'then'
        step.name = 'just a test step'

        assert registry.find_match(step) is magic_object
        for mock in step_defs[6:]:
            eq_(mock.match.call_count, 0)

    @patch.object(step_registry.registry, 'add_step_definition')
    def test_make_step_decorator_ends_up_adding_a_step_definition(self, add_step_definition):
        step_type = object()
        string = object()
        func = object()

        decorator = step_registry.registry.make_decorator(step_type)
        wrapper = decorator(string)
        assert wrapper(func) is func
        add_step_definition.assert_called_with(step_type, string, func)


########NEW FILE########
__FILENAME__ = test_tag_expression
# -*- coding: utf-8 -*-

from behave.tag_expression import TagExpression
from nose import tools
import unittest


# ----------------------------------------------------------------------------
# BASIC TESTS: 0..1 tags, not @tag
# ----------------------------------------------------------------------------
class TestTagExpressionNoTags(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression([])

    def test_should_match_empty_tags(self):
        assert self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])


class TestTagExpressionFoo(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['foo'])

    def test_should_not_match_no_tags(self):
        assert not self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_not_match_bar(self):
        assert not self.e.check(['bar'])


class TestTagExpressionNotFoo(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['-foo'])

    def test_should_match_no_tags(self):
        assert self.e.check([])

    def test_should_not_match_foo(self):
        assert not self.e.check(['foo'])

    def test_should_match_bar(self):
        assert self.e.check(['bar'])


# ----------------------------------------------------------------------------
# LOGICAL-AND TESTS: With @foo, @bar (2 tags)
# ----------------------------------------------------------------------------
class TestTagExpressionFooAndBar(unittest.TestCase):
    # -- LOGIC: @foo and @bar

    def setUp(self):
        self.e = TagExpression(['foo', 'bar'])

    def test_should_not_match_no_tags(self):
        assert not self.e.check([])

    def test_should_not_match_foo(self):
        assert not self.e.check(['foo'])

    def test_should_not_match_bar(self):
        assert not self.e.check(['bar'])

    def test_should_not_match_other(self):
        assert not self.e.check(['other'])

    def test_should_match_foo_bar(self):
        assert self.e.check(['foo', 'bar'])
        assert self.e.check(['bar', 'foo'])

    def test_should_not_match_foo_other(self):
        assert not self.e.check(['foo', 'other'])
        assert not self.e.check(['other', 'foo'])

    def test_should_not_match_bar_other(self):
        assert not self.e.check(['bar', 'other'])
        assert not self.e.check(['other', 'bar'])

    def test_should_not_match_zap_other(self):
        assert not self.e.check(['zap', 'other'])
        assert not self.e.check(['other', 'zap'])

    def test_should_match_foo_bar_other(self):
        assert self.e.check(['foo', 'bar', 'other'])
        assert self.e.check(['bar', 'other', 'foo'])
        assert self.e.check(['other', 'bar', 'foo'])

    def test_should_not_match_foo_zap_other(self):
        assert not self.e.check(['foo', 'zap', 'other'])
        assert not self.e.check(['other', 'zap', 'foo'])

    def test_should_not_match_bar_zap_other(self):
        assert not self.e.check(['bar', 'zap', 'other'])
        assert not self.e.check(['other', 'bar', 'zap'])

    def test_should_not_match_zap_baz_other(self):
        assert not self.e.check(['zap', 'baz', 'other'])
        assert not self.e.check(['baz', 'other', 'baz'])
        assert not self.e.check(['other', 'baz', 'zap'])


class TestTagExpressionFooAndNotBar(unittest.TestCase):
    # -- LOGIC: @foo and not @bar

    def setUp(self):
        self.e = TagExpression(['foo', '-bar'])

    def test_should_not_match_no_tags(self):
        assert not self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_not_match_bar(self):
        assert not self.e.check(['bar'])

    def test_should_not_match_other(self):
        assert not self.e.check(['other'])

    def test_should_not_match_foo_bar(self):
        assert not self.e.check(['foo', 'bar'])
        assert not self.e.check(['bar', 'foo'])

    def test_should_match_foo_other(self):
        assert self.e.check(['foo', 'other'])
        assert self.e.check(['other', 'foo'])

    def test_should_not_match_bar_other(self):
        assert not self.e.check(['bar', 'other'])
        assert not self.e.check(['other', 'bar'])

    def test_should_not_match_zap_other(self):
        assert not self.e.check(['bar', 'other'])
        assert not self.e.check(['other', 'bar'])

    def test_should_not_match_foo_bar_other(self):
        assert not self.e.check(['foo', 'bar', 'other'])
        assert not self.e.check(['bar', 'other', 'foo'])
        assert not self.e.check(['other', 'bar', 'foo'])

    def test_should_match_foo_zap_other(self):
        assert self.e.check(['foo', 'zap', 'other'])
        assert self.e.check(['other', 'zap', 'foo'])

    def test_should_not_match_bar_zap_other(self):
        assert not self.e.check(['bar', 'zap', 'other'])
        assert not self.e.check(['other', 'bar', 'zap'])

    def test_should_not_match_zap_baz_other(self):
        assert not self.e.check(['zap', 'baz', 'other'])
        assert not self.e.check(['baz', 'other', 'baz'])
        assert not self.e.check(['other', 'baz', 'zap'])


class TestTagExpressionNotBarAndFoo(TestTagExpressionFooAndNotBar):
    # -- REUSE: Test suite due to symmetry in reversed expression
    # LOGIC: not @bar and @foo == @foo and not @bar

    def setUp(self):
        self.e = TagExpression(['-bar', 'foo'])


class TestTagExpressionNotFooAndNotBar(unittest.TestCase):
    # -- LOGIC: not @bar and not @foo

    def setUp(self):
        self.e = TagExpression(['-foo', '-bar'])

    def test_should_match_no_tags(self):
        assert self.e.check([])

    def test_should_not_match_foo(self):
        assert not self.e.check(['foo'])

    def test_should_not_match_bar(self):
        assert not self.e.check(['bar'])

    def test_should_match_other(self):
        assert self.e.check(['other'])

    def test_should_not_match_foo_bar(self):
        assert not self.e.check(['foo', 'bar'])
        assert not self.e.check(['bar', 'foo'])

    def test_should_not_match_foo_other(self):
        assert not self.e.check(['foo', 'other'])
        assert not self.e.check(['other', 'foo'])

    def test_should_not_match_bar_other(self):
        assert not self.e.check(['bar', 'other'])
        assert not self.e.check(['other', 'bar'])

    def test_should_match_zap_other(self):
        assert self.e.check(['zap', 'other'])
        assert self.e.check(['other', 'zap'])

    def test_should_not_match_foo_bar_other(self):
        assert not self.e.check(['foo', 'bar', 'other'])
        assert not self.e.check(['bar', 'other', 'foo'])
        assert not self.e.check(['other', 'bar', 'foo'])

    def test_should_not_match_foo_zap_other(self):
        assert not self.e.check(['foo', 'zap', 'other'])
        assert not self.e.check(['other', 'zap', 'foo'])

    def test_should_not_match_bar_zap_other(self):
        assert not self.e.check(['bar', 'zap', 'other'])
        assert not self.e.check(['other', 'bar', 'zap'])

    def test_should_match_zap_baz_other(self):
        assert self.e.check(['zap', 'baz', 'other'])
        assert self.e.check(['baz', 'other', 'baz'])
        assert self.e.check(['other', 'baz', 'zap'])


class TestTagExpressionNotBarAndNotFoo(TestTagExpressionNotFooAndNotBar):
    # -- REUSE: Test suite due to symmetry in reversed expression
    # LOGIC: not @bar and not @foo == not @foo and not @bar

    def setUp(self):
        self.e = TagExpression(['-bar', '-foo'])


# ----------------------------------------------------------------------------
# LOGICAL-OR TESTS: With @foo, @bar (2 tags)
# ----------------------------------------------------------------------------
class TestTagExpressionFooOrBar(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['foo,bar'])

    def test_should_not_match_no_tags(self):
        assert not self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_match_bar(self):
        assert self.e.check(['bar'])

    def test_should_not_match_other(self):
        assert not self.e.check(['other'])

    def test_should_match_foo_bar(self):
        assert self.e.check(['foo', 'bar'])
        assert self.e.check(['bar', 'foo'])

    def test_should_match_foo_other(self):
        assert self.e.check(['foo', 'other'])
        assert self.e.check(['other', 'foo'])

    def test_should_match_bar_other(self):
        assert self.e.check(['bar', 'other'])
        assert self.e.check(['other', 'bar'])

    def test_should_not_match_zap_other(self):
        assert not self.e.check(['zap', 'other'])
        assert not self.e.check(['other', 'zap'])

    def test_should_match_foo_bar_other(self):
        assert self.e.check(['foo', 'bar', 'other'])
        assert self.e.check(['bar', 'other', 'foo'])
        assert self.e.check(['other', 'bar', 'foo'])

    def test_should_match_foo_zap_other(self):
        assert self.e.check(['foo', 'zap', 'other'])
        assert self.e.check(['other', 'zap', 'foo'])

    def test_should_match_bar_zap_other(self):
        assert self.e.check(['bar', 'zap', 'other'])
        assert self.e.check(['other', 'bar', 'zap'])

    def test_should_not_match_zap_baz_other(self):
        assert not self.e.check(['zap', 'baz', 'other'])
        assert not self.e.check(['baz', 'other', 'baz'])
        assert not self.e.check(['other', 'baz', 'zap'])


class TestTagExpressionBarOrFoo(TestTagExpressionFooOrBar):
    # -- REUSE: Test suite due to symmetry in reversed expression
    # LOGIC: @bar or @foo == @foo or @bar
    def setUp(self):
        self.e = TagExpression(['bar,foo'])


class TestTagExpressionFooOrNotBar(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['foo,-bar'])

    def test_should_match_no_tags(self):
        assert self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_not_match_bar(self):
        assert not self.e.check(['bar'])

    def test_should_match_other(self):
        assert self.e.check(['other'])

    def test_should_match_foo_bar(self):
        assert self.e.check(['foo', 'bar'])
        assert self.e.check(['bar', 'foo'])

    def test_should_match_foo_other(self):
        assert self.e.check(['foo', 'other'])
        assert self.e.check(['other', 'foo'])

    def test_should_not_match_bar_other(self):
        assert not self.e.check(['bar', 'other'])
        assert not self.e.check(['other', 'bar'])

    def test_should_match_zap_other(self):
        assert self.e.check(['zap', 'other'])
        assert self.e.check(['other', 'zap'])

    def test_should_match_foo_bar_other(self):
        assert self.e.check(['foo', 'bar', 'other'])
        assert self.e.check(['bar', 'other', 'foo'])
        assert self.e.check(['other', 'bar', 'foo'])

    def test_should_match_foo_zap_other(self):
        assert self.e.check(['foo', 'zap', 'other'])
        assert self.e.check(['other', 'zap', 'foo'])

    def test_should_not_match_bar_zap_other(self):
        assert not self.e.check(['bar', 'zap', 'other'])
        assert not self.e.check(['other', 'bar', 'zap'])

    def test_should_match_zap_baz_other(self):
        assert self.e.check(['zap', 'baz', 'other'])
        assert self.e.check(['baz', 'other', 'baz'])
        assert self.e.check(['other', 'baz', 'zap'])


class TestTagExpressionNotBarOrFoo(TestTagExpressionFooOrNotBar):
    # -- REUSE: Test suite due to symmetry in reversed expression
    # LOGIC: not @bar or @foo == @foo or not @bar
    def setUp(self):
        self.e = TagExpression(['-bar,foo'])


class TestTagExpressionNotFooOrNotBar(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['-foo,-bar'])

    def test_should_match_no_tags(self):
        assert self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_match_bar(self):
        assert self.e.check(['bar'])

    def test_should_match_other(self):
        assert self.e.check(['other'])

    def test_should_not_match_foo_bar(self):
        assert not self.e.check(['foo', 'bar'])
        assert not self.e.check(['bar', 'foo'])

    def test_should_match_foo_other(self):
        assert self.e.check(['foo', 'other'])
        assert self.e.check(['other', 'foo'])

    def test_should_match_bar_other(self):
        assert self.e.check(['bar', 'other'])
        assert self.e.check(['other', 'bar'])

    def test_should_match_zap_other(self):
        assert self.e.check(['zap', 'other'])
        assert self.e.check(['other', 'zap'])

    def test_should_not_match_foo_bar_other(self):
        assert not self.e.check(['foo', 'bar', 'other'])
        assert not self.e.check(['bar', 'other', 'foo'])
        assert not self.e.check(['other', 'bar', 'foo'])

    def test_should_match_foo_zap_other(self):
        assert self.e.check(['foo', 'zap', 'other'])
        assert self.e.check(['other', 'zap', 'foo'])

    def test_should_match_bar_zap_other(self):
        assert self.e.check(['bar', 'zap', 'other'])
        assert self.e.check(['other', 'bar', 'zap'])

    def test_should_match_zap_baz_other(self):
        assert self.e.check(['zap', 'baz', 'other'])
        assert self.e.check(['baz', 'other', 'baz'])
        assert self.e.check(['other', 'baz', 'zap'])


class TestTagExpressionNotBarOrNotFoo(TestTagExpressionNotFooOrNotBar):
    # -- REUSE: Test suite due to symmetry in reversed expression
    # LOGIC: not @bar or @foo == @foo or not @bar
    def setUp(self):
        self.e = TagExpression(['-bar,-foo'])


# ----------------------------------------------------------------------------
# MORE TESTS: With 3 tags
# ----------------------------------------------------------------------------
class TestTagExpressionFooOrBarAndNotZap(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['foo,bar', '-zap'])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_not_match_foo_zap(self):
        assert not self.e.check(['foo', 'zap'])

    def test_should_not_match_tags(self):
        assert not self.e.check([])

    def test_should_match_foo(self):
        assert self.e.check(['foo'])

    def test_should_match_bar(self):
        assert self.e.check(['bar'])

    def test_should_not_match_other(self):
        assert not self.e.check(['other'])

    def test_should_match_foo_bar(self):
        assert self.e.check(['foo', 'bar'])
        assert self.e.check(['bar', 'foo'])

    def test_should_match_foo_other(self):
        assert self.e.check(['foo', 'other'])
        assert self.e.check(['other', 'foo'])

    def test_should_match_bar_other(self):
        assert self.e.check(['bar', 'other'])
        assert self.e.check(['other', 'bar'])

    def test_should_not_match_zap_other(self):
        assert not self.e.check(['zap', 'other'])
        assert not self.e.check(['other', 'zap'])

    def test_should_match_foo_bar_other(self):
        assert self.e.check(['foo', 'bar', 'other'])
        assert self.e.check(['bar', 'other', 'foo'])
        assert self.e.check(['other', 'bar', 'foo'])

    def test_should_not_match_foo_bar_zap(self):
        assert not self.e.check(['foo', 'bar', 'zap'])
        assert not self.e.check(['bar', 'zap', 'foo'])
        assert not self.e.check(['zap', 'bar', 'foo'])

    def test_should_not_match_foo_zap_other(self):
        assert not self.e.check(['foo', 'zap', 'other'])
        assert not self.e.check(['other', 'zap', 'foo'])

    def test_should_not_match_bar_zap_other(self):
        assert not self.e.check(['bar', 'zap', 'other'])
        assert not self.e.check(['other', 'bar', 'zap'])

    def test_should_not_match_zap_baz_other(self):
        assert not self.e.check(['zap', 'baz', 'other'])
        assert not self.e.check(['baz', 'other', 'baz'])
        assert not self.e.check(['other', 'baz', 'zap'])


# ----------------------------------------------------------------------------
# TESTS WITH LIMIT
# ----------------------------------------------------------------------------
class TestTagExpressionFoo3OrNotBar4AndZap5(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression(['foo:3,-bar', 'zap:5'])

    def test_should_count_tags_for_positive_tags(self):
        tools.eq_(self.e.limits, {'foo': 3, 'zap': 5})

    def test_should_match_foo_zap(self):
        assert self.e.check(['foo', 'zap'])

class TestTagExpressionParsing(unittest.TestCase):
    def setUp(self):
        self.e = TagExpression([' foo:3 , -bar ', ' zap:5 '])

    def test_should_have_limits(self):
        tools.eq_(self.e.limits, {'zap': 5, 'foo': 3})

class TestTagExpressionTagLimits(unittest.TestCase):
    def test_should_be_counted_for_negative_tags(self):
        e = TagExpression(['-todo:3'])
        tools.eq_(e.limits, {'todo': 3})

    def test_should_be_counted_for_positive_tags(self):
        e = TagExpression(['todo:3'])
        tools.eq_(e.limits, {'todo': 3})

    def test_should_raise_an_error_for_inconsistent_limits(self):
        tools.assert_raises(Exception, TagExpression, ['todo:3', '-todo:4'])

    def test_should_allow_duplicate_consistent_limits(self):
        e = TagExpression(['todo:3', '-todo:3'])
        tools.eq_(e.limits, {'todo': 3})


########NEW FILE########
__FILENAME__ = test_tag_expression2
# -*- coding: utf-8 -*-
"""
Alternative approach to test TagExpression by testing all possible combinations.

REQUIRES: Python >= 2.6, because itertools.combinations() is used.
"""

from behave.tag_expression import TagExpression
from nose import tools
import itertools

has_combinations = hasattr(itertools, "combinations")
if has_combinations:
    # -- REQUIRE: itertools.combinations
    # SINCE: Python 2.6

    def all_combinations(items):
        variants = []
        for n in range(len(items)+1):
            variants.extend(itertools.combinations(items, n))
        return variants

    NO_TAGS = "__NO_TAGS__"
    def make_tags_line(tags):
        """
        Convert into tags-line as in feature file.
        """
        if tags:
            return "@" + " @".join(tags)
        return NO_TAGS

    TestCase = object
    # ----------------------------------------------------------------------------
    # TEST: all_combinations() test helper
    # ----------------------------------------------------------------------------
    class TestAllCombinations(TestCase):
        def test_all_combinations_with_2values(self):
            items = "@one @two".split()
            expected = [
                (),
                ('@one',),
                ('@two',),
                ('@one', '@two'),
            ]
            actual = all_combinations(items)
            tools.eq_(actual, expected)
            tools.eq_(len(actual), 4)

        def test_all_combinations_with_3values(self):
            items = "@one @two @three".split()
            expected = [
                (),
                ('@one',),
                ('@two',),
                ('@three',),
                ('@one', '@two'),
                ('@one', '@three'),
                ('@two', '@three'),
                ('@one', '@two', '@three'),
            ]
            actual = all_combinations(items)
            tools.eq_(actual, expected)
            tools.eq_(len(actual), 8)


    # ----------------------------------------------------------------------------
    # COMPLICATED TESTS FOR: TagExpression logic
    # ----------------------------------------------------------------------------
    class TagExpressionTestCase(TestCase):

        def assert_tag_expression_matches(self, tag_expression,
                                          tag_combinations, expected):
            matched = [ make_tags_line(c) for c in tag_combinations
                                if tag_expression.check(c) ]
            tools.eq_(matched, expected)

        def assert_tag_expression_mismatches(self, tag_expression,
                                            tag_combinations, expected):
            mismatched = [ make_tags_line(c) for c in tag_combinations
                                if not tag_expression.check(c) ]
            tools.eq_(mismatched, expected)


    class TestTagExpressionWith1Term(TagExpressionTestCase):
        """
        ALL_COMBINATIONS[4] with: @foo @other
            self.NO_TAGS,
            "@foo", "@other",
            "@foo @other",
        """
        tags = ("foo", "other")
        tag_combinations = all_combinations(tags)

        def test_matches__foo(self):
            tag_expression = TagExpression(["@foo"])
            expected = [
                # -- WITH 0 tags: None
                "@foo",
                "@foo @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

        def test_matches__not_foo(self):
            tag_expression = TagExpression(["-@foo"])
            expected = [
                NO_TAGS,
                "@other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

    class TestTagExpressionWith2Terms(TagExpressionTestCase):
        """
        ALL_COMBINATIONS[8] with: @foo @bar @other
            self.NO_TAGS,
            "@foo", "@bar", "@other",
            "@foo @bar", "@foo @other", "@bar @other",
            "@foo @bar @other",
        """
        tags = ("foo", "bar", "other")
        tag_combinations = all_combinations(tags)

        # -- LOGICAL-OR CASES:
        def test_matches__foo_or_bar(self):
            tag_expression = TagExpression(["@foo,@bar"])
            expected = [
                # -- WITH 0 tags: None
                "@foo", "@bar",
                "@foo @bar", "@foo @other", "@bar @other",
                "@foo @bar @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

        def test_matches__foo_or_not_bar(self):
            tag_expression = TagExpression(["@foo,-@bar"])
            expected = [
                NO_TAGS,
                "@foo", "@other",
                "@foo @bar", "@foo @other",
                "@foo @bar @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

        def test_matches__not_foo_or_not_bar(self):
            tag_expression = TagExpression(["-@foo,-@bar"])
            expected = [
                NO_TAGS,
                "@foo", "@bar", "@other",
                "@foo @other", "@bar @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

        # -- LOGICAL-AND CASES:
        def test_matches__foo_and_bar(self):
            tag_expression = TagExpression(["@foo", "@bar"])
            expected = [
                # -- WITH 0 tags: None
                # -- WITH 1 tag:  None
                "@foo @bar",
                "@foo @bar @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

        def test_matches__foo_and_not_bar(self):
            tag_expression = TagExpression(["@foo", "-@bar"])
            expected = [
                # -- WITH 0 tags: None
                # -- WITH 1 tag:  None
                "@foo",
                "@foo @other",
                # -- WITH 3 tag:  None
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)

        def test_matches__not_foo_and_not_bar(self):
            tag_expression = TagExpression(["-@foo", "-@bar"])
            expected = [
                NO_TAGS,
                "@other",
                # -- WITH 2 tag:  None
                # -- WITH 3 tag:  None
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, expected)


    class TestTagExpressionWith3Terms(TagExpressionTestCase):
        """
        ALL_COMBINATIONS[16] with: @foo @bar @zap @other
            self.NO_TAGS,
            "@foo", "@bar", "@zap", "@other",
            "@foo @bar", "@foo @zap", "@foo @other",
            "@bar @zap", "@bar @other",
            "@zap @other",
            "@foo @bar @zap", "@foo @bar @other", "@foo @zap @other",
            "@bar @zap @other",
            "@foo @bar @zap @other",
        """
        tags = ("foo", "bar", "zap", "other")
        tag_combinations = all_combinations(tags)

        # -- LOGICAL-OR CASES:
        def test_matches__foo_or_bar_or_zap(self):
            tag_expression = TagExpression(["@foo,@bar,@zap"])
            matched = [
                # -- WITH 0 tags: None
                # -- WITH 1 tag:
                "@foo", "@bar", "@zap",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap", "@foo @other",
                "@bar @zap", "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @bar @zap", "@foo @bar @other", "@foo @zap @other",
                "@bar @zap @other",
                # -- WITH 4 tags:
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@other",
                # -- WITH 2 tags: None
                # -- WITH 3 tags: None
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

        def test_matches__foo_or_not_bar_or_zap(self):
            tag_expression = TagExpression(["@foo,-@bar,@zap"])
            matched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@foo", "@zap", "@other",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap", "@foo @other",
                "@bar @zap",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @bar @zap", "@foo @bar @other", "@foo @zap @other",
                "@bar @zap @other",
                # -- WITH 4 tags:
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags: None
                # -- WITH 1 tag:
                "@bar",
                # -- WITH 2 tags:
                "@bar @other",
                # -- WITH 3 tags: None
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)


        def test_matches__foo_or_not_bar_or_not_zap(self):
            tag_expression = TagExpression(["foo,-@bar,-@zap"])
            matched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@foo", "@bar", "@zap", "@other",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap", "@foo @other",
                "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @bar @zap", "@foo @bar @other", "@foo @zap @other",
                # -- WITH 4 tags:
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags: None
                # -- WITH 1 tag: None
                # -- WITH 2 tags:
                "@bar @zap",
                # -- WITH 3 tags: None
                "@bar @zap @other",
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

        def test_matches__not_foo_or_not_bar_or_not_zap(self):
            tag_expression = TagExpression(["-@foo,-@bar,-@zap"])
            matched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@foo", "@bar", "@zap", "@other",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap", "@foo @other",
                "@bar @zap", "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @bar @other", "@foo @zap @other",
                "@bar @zap @other",
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags: None
                # -- WITH 1 tag: None
                # -- WITH 2 tags:
                # -- WITH 3 tags:
                "@foo @bar @zap",
                # -- WITH 4 tags:
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

        def test_matches__foo_and_bar_or_zap(self):
            tag_expression = TagExpression(["@foo", "@bar,@zap"])
            matched = [
                # -- WITH 0 tags:
                # -- WITH 1 tag:
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap",
                # -- WITH 3 tags:
                "@foo @bar @zap", "@foo @bar @other", "@foo @zap @other",
                # -- WITH 4 tags: None
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@foo", "@bar", "@zap", "@other",
                # -- WITH 2 tags:
                "@foo @other",
                "@bar @zap", "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@bar @zap @other",
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

        def test_matches__foo_and_bar_or_not_zap(self):
            tag_expression = TagExpression(["@foo", "@bar,-@zap"])
            matched = [
                # -- WITH 0 tags:
                # -- WITH 1 tag:
                "@foo",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @other",
                # -- WITH 3 tags:
                "@foo @bar @zap", "@foo @bar @other",
                # -- WITH 4 tags: None
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@bar", "@zap", "@other",
                # -- WITH 2 tags:
                "@foo @zap",
                "@bar @zap", "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @zap @other",
                "@bar @zap @other",
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

        def test_matches__foo_and_bar_and_zap(self):
            tag_expression = TagExpression(["@foo", "@bar", "@zap"])
            matched = [
                # -- WITH 0 tags:
                # -- WITH 1 tag:
                # -- WITH 2 tags:
                # -- WITH 3 tags:
                "@foo @bar @zap",
                # -- WITH 4 tags: None
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@foo", "@bar", "@zap", "@other",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap", "@foo @other",
                "@bar @zap", "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @bar @other", "@foo @zap @other",
                "@bar @zap @other",
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

        def test_matches__not_foo_and_not_bar_and_not_zap(self):
            tag_expression = TagExpression(["-@foo", "-@bar", "-@zap"])
            matched = [
                # -- WITH 0 tags:
                NO_TAGS,
                # -- WITH 1 tag:
                "@other",
                # -- WITH 2 tags:
                # -- WITH 3 tags:
                # -- WITH 4 tags: None
            ]
            self.assert_tag_expression_matches(tag_expression,
                                               self.tag_combinations, matched)

            mismatched = [
                # -- WITH 0 tags:
                # -- WITH 1 tag:
                "@foo", "@bar", "@zap",
                # -- WITH 2 tags:
                "@foo @bar", "@foo @zap", "@foo @other",
                "@bar @zap", "@bar @other",
                "@zap @other",
                # -- WITH 3 tags:
                "@foo @bar @zap",
                "@foo @bar @other", "@foo @zap @other",
                "@bar @zap @other",
                # -- WITH 4 tags: None
                "@foo @bar @zap @other",
            ]
            self.assert_tag_expression_mismatches(tag_expression,
                                               self.tag_combinations, mismatched)

########NEW FILE########
__FILENAME__ = convert_i18n_yaml
#!/usr/bin/env python

import pprint
import sys

import yaml

#
# usage: convert_i18n_yaml.py i18n.yml ../behave/i18n.py
#
languages = yaml.load(open(sys.argv[1]))

for language in languages:
    keywords = languages[language]
    for k in keywords:
        v = keywords[k]
        # bloody YAML parser returns a mixture of unicode and str
        if not isinstance(v, unicode):
            v = v.decode('utf8')
        keywords[k] = v.split('|')

content = '''#-*- encoding: UTF-8 -*-

# file generated by convert_i18n_yaml.py from i18n.yaml

languages = \\
'''

i18n_py = open(sys.argv[2], 'w')
i18n_py.write(content.encode('UTF-8'))
i18n_py.write(pprint.pformat(languages).encode('UTF-8'))
i18n_py.write(u'\n')
i18n_py.close()

########NEW FILE########
__FILENAME__ = environment

def before_all(context):
    context.testing_stuff = False
    context.stuff_set_up = False

def before_feature(context, feature):
    context.is_spammy = 'spam' in feature.tags


########NEW FILE########
__FILENAME__ = steps
import logging
from behave import *

spam_log = logging.getLogger('spam')
ham_log = logging.getLogger('ham')

@given("I am testing stuff")
def step(context):
    context.testing_stuff = True

@given("some stuff is set up")
def step(context):
    context.stuff_set_up = True

@given("stuff has been set up")
def step(context):
    assert context.testing_stuff is True
    assert context.stuff_set_up is True

@when("I exercise it work")
def step(context):
    spam_log.error('logging!')
    ham_log.error('logging!')

@then("it will work")
def step(context):
    pass

@given("some text {prefix}")
def step(context, prefix):
    context.prefix = prefix

@when('we add some text {suffix}')
def step(context, suffix):
    context.combination = context.prefix + suffix

@then('we should get the {combination}')
def step(context, combination):
    assert context.combination == combination

@given('some body of text')
def step(context):
    assert context.text
    context.saved_text = context.text

TEXT = '''   Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed
do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut
enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat.'''
@then('the text is as expected')
def step(context):
    assert context.saved_text, 'context.saved_text is %r!!' % (context.saved_text, )
    context.saved_text.assert_equals(TEXT)

@given('some initial data')
def step(context):
    assert context.table
    context.saved_table = context.table

TABLE_DATA = [
    dict(name='Barry', department='Beer Cans'),
    dict(name='Pudey', department='Silly Walks'),
    dict(name='Two-Lumps', department='Silly Walks'),
]
@then('we will have the expected data')
def step(context):
    assert context.saved_table, 'context.saved_table is %r!!' % (context.saved_table, )
    for expected, got in zip(TABLE_DATA, iter(context.saved_table)):
        assert expected['name'] == got['name']
        assert expected['department'] == got['department']

@then('the text is substituted as expected')
def step(context):
    assert context.saved_text, 'context.saved_text is %r!!' % (context.saved_text, )
    expected = TEXT.replace('ipsum', context.active_outline['ipsum'])
    context.saved_text.assert_equals(expected)


TABLE_DATA = [
    dict(name='Barry', department='Beer Cans'),
    dict(name='Pudey', department='Silly Walks'),
    dict(name='Two-Lumps', department='Silly Walks'),
]
@then('we will have the substituted data')
def step(context):
    assert context.saved_table, 'context.saved_table is %r!!' % (context.saved_table, )
    value = context.active_outline['spam']
    expected = value + ' Cans'
    assert context.saved_table[0]['department'] == expected, '%r != %r' % (
        context.saved_table[0]['department'], expected)

@given('the tag "{tag}" is set')
def step(context, tag):
    assert tag in context.tags, '%r NOT present in %r!' % (tag, context.tags)
    if tag == 'spam':
        assert context.is_spammy

@given('the tag "{tag}" is not set')
def step(context, tag):
    assert tag not in context.tags, '%r IS present in %r!' % (tag, context.tags)

@given('a string {argument} an argument')
def step(context, argument):
    context.argument = argument

from behave.matchers import register_type
register_type(custom=lambda s: s.upper())

@given('a string {argument:custom} a custom type')
def step(context, argument):
    context.argument = argument

@then('we get "{argument}" parsed')
def step(context, argument):
    assert context.argument == argument


########NEW FILE########
