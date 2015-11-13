__FILENAME__ = debugging
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging


def debug_func(f):
    """Function decorator to start a pdb shell before calling the decorated
        function."""
    def debuggedf(*args, **kwargs):
        import pdb
        pdb.set_trace()
        return f(*args, **kwargs)
    return debuggedf

def log_args(fn, classname=None):
    """Function decorator that logs the call of the decorated function with
        arguments and return value."""
    if classname is None:
        classname = ''
    else:
        classname = classname + '.'

    def logger_fn(*args, **kwargs):
        args_s = ', '.join([repr(a) for a in args])
        kwargs_s = ', '.join(("%s=%s" % (key, repr(value))) for key, value in kwargs.items())
        if not args_s or not kwargs_s:
            all_args = args_s + kwargs_s
        else:
            all_args = ', '.join([args_s, kwargs_s])
        retval = fn(*args, **kwargs)
        print '%s%s(%s) => %s' % (classname, fn.__name__, all_args, retval)
        return retval

    return logger_fn

def log_all_methods(cls):
    """Class decorator that applies the C{log_args} decorator to all of the
        methods in the class."""
    if not hasattr(cls, '__base__'):
        raise TypeError('Not a class: %s' % (cls))
    for attr in dir(cls):
        method = getattr(cls, attr)
        if attr.startswith('__') and attr.endswith('__') or getattr(method, 'im_class', None) is not cls:
            continue
        if callable(method):
            setattr(cls, attr, log_args(method, classname=cls.__name__))
    return cls

########NEW FILE########
__FILENAME__ = runvirtaal
#!/usr/bin/env python
import sys, os, subprocess

_home = os.environ["HOME"]
_res_path = os.path.normpath(os.path.join(sys.path[0], "..", "Resources"))
_lib_path = os.path.join(_res_path, "lib")
_share_path = os.path.join(_res_path, "share")
_pylib_path = os.path.join(_lib_path, "python2.7")
_site_lib_path = os.path.join(_pylib_path, "site-packages")
_virtaal_path = os.path.join(_share_path, "virtaal")
_virtaal_locale = os.path.join(_share_path, "locale")
_conf_path = os.path.join(_res_path, "etc");
_gtk2_conf = os.path.join(_conf_path, "gtk-2.0")
sys.path = [_virtaal_path,
            os.path.join(_pylib_path, "lib-dynload"),
            os.path.join(_site_lib_path, "pyenchant-1.6.5-py2.7.egg"),
            os.path.join(_site_lib_path, "pyobjc-2.3-py2.7.egg"),
            os.path.join(_site_lib_path, "pyobjc_core-2.3-py2.7-macosx-10.5-i386.egg"),
            os.path.join(_site_lib_path, "pyobjc_framework_Cocoa-2.3-py2.7-macosx-10.5-i386.egg"),
            os.path.join(_site_lib_path, "distribute-0.6.10-py2.7.egg"),
            os.path.join(_site_lib_path, "lxml-2.3-py2.7-macosx-10.5-i386.egg"),
            os.path.join(_site_lib_path, "gtk-2.0"),
            _site_lib_path,
            _pylib_path]

sys.prefix = _res_path
os.environ["PYTHONHOME"]=_res_path
os.environ["XDG_DATA_DIRS"]=_share_path
os.environ["DYLD_LIBRARY_PATH"]=_lib_path
os.environ["LD_LIBRARY_PATH"]=_lib_path
os.environ["GTK_PATH"] = _res_path
os.environ["GTK2_RC_FILES"] = os.path.join(_gtk2_conf, "gtkrc")
os.environ["GTK_IM_MODULE_FILE"]= os.path.join(_gtk2_conf, "immodules")
os.environ["GDK_PIXBUF_MODULE_FILE"] = os.path.join(_gtk2_conf, "gdk-pixbuf.loaders")
os.environ["PANGO_RC_FILES"] = os.path.join(_conf_path, "pango", "pangorc")

os.environ["VIRTAALDIR"] = _virtaal_path
os.environ["VIRTAALI18N"] = _virtaal_locale
os.environ["VIRTAALHOME"] = os.path.join(_home, "Library", "Application Support")

LANG = "C" #Default
defaults = "/usr/bin/defaults"
_languages = ""
_collation = ""
_locale = ""
_language = ""
LC_COLLATE = ""
try:
    _languages = subprocess.Popen(
        [defaults,  "read", "-app", "Virtaal", "AppleLanguages"],
        stderr=open("/dev/null"),
        stdout=subprocess.PIPE).communicate()[0].strip("()\n").split(",\n")
    if _languages == ['']:
        _languages = ""
except:
    pass
if not _languages:
    try:
        _languages = subprocess.Popen(
            [defaults, "read", "-g", "AppleLanguages"],
            stderr=open("/dev/null"),
            stdout=subprocess.PIPE).communicate()[0].strip("()\n").split(",\n")
    except:
        pass

for _lang in _languages:
    _lang=_lang.strip().strip('"').replace("-", "_", 1)
    if _lang == "cn_Hant": #Traditional; Gettext uses cn_TW
        _lang = "zh_TW"
    if _lang == "cn_Hans": #Simplified; Gettext uses cn_CN
        _lang = "zh_CN"
    _language = _lang
    if _lang.startswith("en"): #Virtaal doesn't have explicit English translation, use C
        break
    if os.path.exists(os.path.join(_virtaal_locale, _lang, "LC_MESSAGES",
                                   "virtaal.mo")):
        LANG = _lang
        break
    elif os.path.exists(os.path.join(_virtaal_locale, _lang[:2], "LC_MESSAGES",
                                     "virtaal.mo")):
        LANG = _lang[:2]
        break
try:
    _collation=subprocess.Popen(
        [defaults, "read", "-app", "Virtaal", "AppleCollationOrder"],
        stderr=open("/dev/null"),
        stdout=subprocess.PIPE).communicate()[0]
except:
    pass
if not _collation:
    try:
        _collation=subprocess.Popen(
            [defaults, "read", "-g", "AppleCollationOrder"],
            stderr=open("/dev/null"),
            stdout=subprocess.PIPE).communicate()[0]
    except:
        pass
if _collation:
    if LANG == "C" and not _language and os.path.exists(os.path.join(_virtaal_locale, _collation,
                                                   "LC_MESSAGES", "virtaal.mo")):
        LANG = _collation
    LC_COLLATE = _collation
if LANG == "C" and not _language:
    try:
        _locale=subprocess.Popen(
            [defaults, "read", "-app", "Virtaal", "AppleLocale"],
            stderr=open("/dev/null"),
            stdout=subprocess.PIPE).communicate()[0]
    except:
        pass
    if not _locale:
        try:
            _locale=subprocess.Popen(
                [defaults, "read", "-g", "AppleLocale"],
                stderr=open("/dev/null"),
                stdout=subprocess.PIPE).communicate()[0]
        except:
            pass
    if _locale:
        if os.path.exists(os.path.join(_virtaal_locale, _locale[:5],
                                       "LC_MESSAGES", "virtaal.mo")):
            LANG = _locale[:5]
        elif os.path.exists(os.path.join(_virtaal_locale, _locale[:2],
                                         "LC_MESSAGES", "virtaal.mo")):
            LANG = _locale[:2]

os.environ["LANG"] = LANG
if not _language:
    _language = LANG
if LC_COLLATE:
    os.environ["LC_COLLATE"] = LC_COLLATE
if _language == "C" or _language == "en":
    LC_ALL = "en_US"
elif len(_language) == 2:
    LC_ALL = _language + "_" + _language.upper() #Because setlocale gets cranky
                                       #if it only has two letters
else:
    LC_ALL = _language

os.environ["LANGUAGE"] = LC_ALL
os.environ["LC_ALL"] = LC_ALL + ".UTF-8" #Spell-checker dictionary support

#LaunchServices sticks this argument on the front of argument
#lists. It must make sense to somebody, but Virtaal isn't that
#somebody.
for _arg in sys.argv:
    if _arg.startswith("-psn"):
        sys.argv.remove(_arg)

from virtaal.main import Virtaal
prog = Virtaal(None)
prog.run()


########NEW FILE########
__FILENAME__ = optparse
"""optparse - a powerful, extensible, and easy-to-use option parser.

By Greg Ward <gward@python.net>

Originally distributed as Optik; see http://optik.sourceforge.net/ .

If you have problems with this module, please do not file bugs,
patches, or feature requests with Python; instead, use Optik's
SourceForge project page:
  http://sourceforge.net/projects/optik

For support, use the optik-users@lists.sourceforge.net mailing list
(http://lists.sourceforge.net/lists/listinfo/optik-users).
"""

# Python developers: please do not make changes to this file, since
# it is automatically generated from the Optik source code.

__version__ = "1.5.3"

__all__ = ['Option',
           'SUPPRESS_HELP',
           'SUPPRESS_USAGE',
           'Values',
           'OptionContainer',
           'OptionGroup',
           'OptionParser',
           'HelpFormatter',
           'IndentedHelpFormatter',
           'TitledHelpFormatter',
           'OptParseError',
           'OptionError',
           'OptionConflictError',
           'OptionValueError',
           'BadOptionError']

__copyright__ = """
Copyright (c) 2001-2006 Gregory P. Ward.  All rights reserved.
Copyright (c) 2002-2006 Python Software Foundation.  All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

  * Neither the name of the author nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys, os
import types
import textwrap

def _repr(self):
    return "<%s at 0x%x: %s>" % (self.__class__.__name__, id(self), self)


# This file was generated from:
#   Id: option_parser.py 527 2006-07-23 15:21:30Z greg
#   Id: option.py 522 2006-06-11 16:22:03Z gward
#   Id: help.py 527 2006-07-23 15:21:30Z greg
#   Id: errors.py 509 2006-04-20 00:58:24Z gward

try:
    from gettext import gettext
except ImportError:
    def gettext(message):
        return message
_ = gettext


class OptParseError (Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class OptionError (OptParseError):
    """
    Raised if an Option instance is created with invalid or
    inconsistent arguments.
    """

    def __init__(self, msg, option):
        self.msg = msg
        self.option_id = str(option)

    def __str__(self):
        if self.option_id:
            return "option %s: %s" % (self.option_id, self.msg)
        else:
            return self.msg

class OptionConflictError (OptionError):
    """
    Raised if conflicting options are added to an OptionParser.
    """

class OptionValueError (OptParseError):
    """
    Raised if an invalid option value is encountered on the command
    line.
    """

class BadOptionError (OptParseError):
    """
    Raised if an invalid option is seen on the command line.
    """
    def __init__(self, opt_str):
        self.opt_str = opt_str

    def __str__(self):
        return _("no such option: %s") % self.opt_str

class AmbiguousOptionError (BadOptionError):
    """
    Raised if an ambiguous option is seen on the command line.
    """
    def __init__(self, opt_str, possibilities):
        BadOptionError.__init__(self, opt_str)
        self.possibilities = possibilities

    def __str__(self):
        return (_("ambiguous option: %s (%s?)")
                % (self.opt_str, ", ".join(self.possibilities)))


class HelpFormatter:

    """
    Abstract base class for formatting option help.  OptionParser
    instances should use one of the HelpFormatter subclasses for
    formatting help; by default IndentedHelpFormatter is used.

    Instance attributes:
      parser : OptionParser
        the controlling OptionParser instance
      indent_increment : int
        the number of columns to indent per nesting level
      max_help_position : int
        the maximum starting column for option help text
      help_position : int
        the calculated starting column for option help text;
        initially the same as the maximum
      width : int
        total number of columns for output (pass None to constructor for
        this value to be taken from the $COLUMNS environment variable)
      level : int
        current indentation level
      current_indent : int
        current indentation level (in columns)
      help_width : int
        number of columns available for option help text (calculated)
      default_tag : str
        text to replace with each option's default value, "%default"
        by default.  Set to false value to disable default value expansion.
      option_strings : { Option : str }
        maps Option instances to the snippet of help text explaining
        the syntax of that option, e.g. "-h, --help" or
        "-fFILE, --file=FILE"
      _short_opt_fmt : str
        format string controlling how short options with values are
        printed in help text.  Must be either "%s%s" ("-fFILE") or
        "%s %s" ("-f FILE"), because those are the two syntaxes that
        Optik supports.
      _long_opt_fmt : str
        similar but for long options; must be either "%s %s" ("--file FILE")
        or "%s=%s" ("--file=FILE").
    """

    NO_DEFAULT_VALUE = "none"

    def __init__(self,
                 indent_increment,
                 max_help_position,
                 width,
                 short_first):
        self.parser = None
        self.indent_increment = indent_increment
        self.help_position = self.max_help_position = max_help_position
        if width is None:
            try:
                width = int(os.environ['COLUMNS'])
            except (KeyError, ValueError):
                width = 80
            width -= 2
        self.width = width
        self.current_indent = 0
        self.level = 0
        self.help_width = None          # computed later
        self.short_first = short_first
        self.default_tag = "%default"
        self.option_strings = {}
        self._short_opt_fmt = "%s %s"
        self._long_opt_fmt = "%s=%s"

    def set_parser(self, parser):
        self.parser = parser

    def set_short_opt_delimiter(self, delim):
        if delim not in ("", " "):
            raise ValueError(
                "invalid metavar delimiter for short options: %r" % delim)
        self._short_opt_fmt = "%s" + delim + "%s"

    def set_long_opt_delimiter(self, delim):
        if delim not in ("=", " "):
            raise ValueError(
                "invalid metavar delimiter for long options: %r" % delim)
        self._long_opt_fmt = "%s" + delim + "%s"

    def indent(self):
        self.current_indent += self.indent_increment
        self.level += 1

    def dedent(self):
        self.current_indent -= self.indent_increment
        assert self.current_indent >= 0, "Indent decreased below 0."
        self.level -= 1

    def format_usage(self, usage):
        raise NotImplementedError, "subclasses must implement"

    def format_heading(self, heading):
        raise NotImplementedError, "subclasses must implement"

    def _format_text(self, text):
        """
        Format a paragraph of free-form text for inclusion in the
        help output at the current indentation level.
        """
        text_width = self.width - self.current_indent
        indent = " "*self.current_indent
        return textwrap.fill(text,
                             text_width,
                             initial_indent=indent,
                             subsequent_indent=indent)

    def format_description(self, description):
        if description:
            return self._format_text(description) + "\n"
        else:
            return ""

    def format_epilog(self, epilog):
        if epilog:
            return "\n" + self._format_text(epilog) + "\n"
        else:
            return ""


    def expand_default(self, option):
        if self.parser is None or not self.default_tag:
            return option.help

        default_value = self.parser.defaults.get(option.dest)
        if default_value is NO_DEFAULT or default_value is None:
            default_value = self.NO_DEFAULT_VALUE

        return option.help.replace(self.default_tag, str(default_value))

    def format_option(self, option):
        # The help for each option consists of two parts:
        #   * the opt strings and metavars
        #     eg. ("-x", or "-fFILENAME, --file=FILENAME")
        #   * the user-supplied help string
        #     eg. ("turn on expert mode", "read data from FILENAME")
        #
        # If possible, we write both of these on the same line:
        #   -x      turn on expert mode
        #
        # But if the opt string list is too long, we put the help
        # string on a second line, indented to the same column it would
        # start in if it fit on the first line.
        #   -fFILENAME, --file=FILENAME
        #           read data from FILENAME
        result = []
        opts = self.option_strings[option]
        opt_width = self.help_position - self.current_indent - 2
        if len(opts) > opt_width:
            opts = "%*s%s\n" % (self.current_indent, "", opts)
            indent_first = self.help_position
        else:                       # start help on same line as opts
            opts = "%*s%-*s  " % (self.current_indent, "", opt_width, opts)
            indent_first = 0
        result.append(opts)
        if option.help:
            help_text = self.expand_default(option)
            help_lines = textwrap.wrap(help_text, self.help_width)
            result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
            result.extend(["%*s%s\n" % (self.help_position, "", line)
                           for line in help_lines[1:]])
        elif opts[-1] != "\n":
            result.append("\n")
        return "".join(result)

    def store_option_strings(self, parser):
        self.indent()
        max_len = 0
        for opt in parser.option_list:
            strings = self.format_option_strings(opt)
            self.option_strings[opt] = strings
            max_len = max(max_len, len(strings) + self.current_indent)
        self.indent()
        for group in parser.option_groups:
            for opt in group.option_list:
                strings = self.format_option_strings(opt)
                self.option_strings[opt] = strings
                max_len = max(max_len, len(strings) + self.current_indent)
        self.dedent()
        self.dedent()
        self.help_position = min(max_len + 2, self.max_help_position)
        self.help_width = self.width - self.help_position

    def format_option_strings(self, option):
        """Return a comma-separated list of option strings & metavariables."""
        if option.takes_value():
            metavar = option.metavar or option.dest.upper()
            short_opts = [self._short_opt_fmt % (sopt, metavar)
                          for sopt in option._short_opts]
            long_opts = [self._long_opt_fmt % (lopt, metavar)
                         for lopt in option._long_opts]
        else:
            short_opts = option._short_opts
            long_opts = option._long_opts

        if self.short_first:
            opts = short_opts + long_opts
        else:
            opts = long_opts + short_opts

        return ", ".join(opts)

class IndentedHelpFormatter (HelpFormatter):
    """Format help with indented section bodies.
    """

    def __init__(self,
                 indent_increment=2,
                 max_help_position=24,
                 width=None,
                 short_first=1):
        HelpFormatter.__init__(
            self, indent_increment, max_help_position, width, short_first)

    def format_usage(self, usage):
        return _("Usage: %s\n") % usage

    def format_heading(self, heading):
        return "%*s%s:\n" % (self.current_indent, "", heading)


class TitledHelpFormatter (HelpFormatter):
    """Format help with underlined section headers.
    """

    def __init__(self,
                 indent_increment=0,
                 max_help_position=24,
                 width=None,
                 short_first=0):
        HelpFormatter.__init__ (
            self, indent_increment, max_help_position, width, short_first)

    def format_usage(self, usage):
        return "%s  %s\n" % (self.format_heading(_("Usage")), usage)

    def format_heading(self, heading):
        return "%s\n%s\n" % (heading, "=-"[self.level] * len(heading))


def _parse_num(val, type):
    if val[:2].lower() == "0x":         # hexadecimal
        radix = 16
    elif val[:2].lower() == "0b":       # binary
        radix = 2
        val = val[2:] or "0"            # have to remove "0b" prefix
    elif val[:1] == "0":                # octal
        radix = 8
    else:                               # decimal
        radix = 10

    return type(val, radix)

def _parse_int(val):
    return _parse_num(val, int)

def _parse_long(val):
    return _parse_num(val, long)

_builtin_cvt = { "int" : (_parse_int, _("integer")),
                 "long" : (_parse_long, _("long integer")),
                 "float" : (float, _("floating-point")),
                 "complex" : (complex, _("complex")) }

def check_builtin(option, opt, value):
    (cvt, what) = _builtin_cvt[option.type]
    try:
        return cvt(value)
    except ValueError:
        raise OptionValueError(
            _("option %s: invalid %s value: %r") % (opt, what, value))

def check_choice(option, opt, value):
    if value in option.choices:
        return value
    else:
        choices = ", ".join(map(repr, option.choices))
        raise OptionValueError(
            _("option %s: invalid choice: %r (choose from %s)")
            % (opt, value, choices))

# Not supplying a default is different from a default of None,
# so we need an explicit "not supplied" value.
NO_DEFAULT = ("NO", "DEFAULT")


class Option:
    """
    Instance attributes:
      _short_opts : [string]
      _long_opts : [string]

      action : string
      type : string
      dest : string
      default : any
      nargs : int
      const : any
      choices : [string]
      callback : function
      callback_args : (any*)
      callback_kwargs : { string : any }
      help : string
      metavar : string
    """

    # The list of instance attributes that may be set through
    # keyword args to the constructor.
    ATTRS = ['action',
             'type',
             'dest',
             'default',
             'nargs',
             'const',
             'choices',
             'callback',
             'callback_args',
             'callback_kwargs',
             'help',
             'metavar']

    # The set of actions allowed by option parsers.  Explicitly listed
    # here so the constructor can validate its arguments.
    ACTIONS = ("store",
               "store_const",
               "store_true",
               "store_false",
               "append",
               "append_const",
               "count",
               "callback",
               "help",
               "version")

    # The set of actions that involve storing a value somewhere;
    # also listed just for constructor argument validation.  (If
    # the action is one of these, there must be a destination.)
    STORE_ACTIONS = ("store",
                     "store_const",
                     "store_true",
                     "store_false",
                     "append",
                     "append_const",
                     "count")

    # The set of actions for which it makes sense to supply a value
    # type, ie. which may consume an argument from the command line.
    TYPED_ACTIONS = ("store",
                     "append",
                     "callback")

    # The set of actions which *require* a value type, ie. that
    # always consume an argument from the command line.
    ALWAYS_TYPED_ACTIONS = ("store",
                            "append")

    # The set of actions which take a 'const' attribute.
    CONST_ACTIONS = ("store_const",
                     "append_const")

    # The set of known types for option parsers.  Again, listed here for
    # constructor argument validation.
    TYPES = ("string", "int", "long", "float", "complex", "choice")

    # Dictionary of argument checking functions, which convert and
    # validate option arguments according to the option type.
    #
    # Signature of checking functions is:
    #   check(option : Option, opt : string, value : string) -> any
    # where
    #   option is the Option instance calling the checker
    #   opt is the actual option seen on the command-line
    #     (eg. "-a", "--file")
    #   value is the option argument seen on the command-line
    #
    # The return value should be in the appropriate Python type
    # for option.type -- eg. an integer if option.type == "int".
    #
    # If no checker is defined for a type, arguments will be
    # unchecked and remain strings.
    TYPE_CHECKER = { "int"    : check_builtin,
                     "long"   : check_builtin,
                     "float"  : check_builtin,
                     "complex": check_builtin,
                     "choice" : check_choice,
                   }


    # CHECK_METHODS is a list of unbound method objects; they are called
    # by the constructor, in order, after all attributes are
    # initialized.  The list is created and filled in later, after all
    # the methods are actually defined.  (I just put it here because I
    # like to define and document all class attributes in the same
    # place.)  Subclasses that add another _check_*() method should
    # define their own CHECK_METHODS list that adds their check method
    # to those from this class.
    CHECK_METHODS = None


    # -- Constructor/initialization methods ----------------------------

    def __init__(self, *opts, **attrs):
        # Set _short_opts, _long_opts attrs from 'opts' tuple.
        # Have to be set now, in case no option strings are supplied.
        self._short_opts = []
        self._long_opts = []
        opts = self._check_opt_strings(opts)
        self._set_opt_strings(opts)

        # Set all other attrs (action, type, etc.) from 'attrs' dict
        self._set_attrs(attrs)

        # Check all the attributes we just set.  There are lots of
        # complicated interdependencies, but luckily they can be farmed
        # out to the _check_*() methods listed in CHECK_METHODS -- which
        # could be handy for subclasses!  The one thing these all share
        # is that they raise OptionError if they discover a problem.
        for checker in self.CHECK_METHODS:
            checker(self)

    def _check_opt_strings(self, opts):
        # Filter out None because early versions of Optik had exactly
        # one short option and one long option, either of which
        # could be None.
        opts = filter(None, opts)
        if not opts:
            raise TypeError("at least one option string must be supplied")
        return opts

    def _set_opt_strings(self, opts):
        for opt in opts:
            if len(opt) < 2:
                raise OptionError(
                    "invalid option string %r: "
                    "must be at least two characters long" % opt, self)
            elif len(opt) == 2:
                if not (opt[0] == "-" and opt[1] != "-"):
                    raise OptionError(
                        "invalid short option string %r: "
                        "must be of the form -x, (x any non-dash char)" % opt,
                        self)
                self._short_opts.append(opt)
            else:
                if not (opt[0:2] == "--" and opt[2] != "-"):
                    raise OptionError(
                        "invalid long option string %r: "
                        "must start with --, followed by non-dash" % opt,
                        self)
                self._long_opts.append(opt)

    def _set_attrs(self, attrs):
        for attr in self.ATTRS:
            if attrs.has_key(attr):
                setattr(self, attr, attrs[attr])
                del attrs[attr]
            else:
                if attr == 'default':
                    setattr(self, attr, NO_DEFAULT)
                else:
                    setattr(self, attr, None)
        if attrs:
            attrs = attrs.keys()
            attrs.sort()
            raise OptionError(
                "invalid keyword arguments: %s" % ", ".join(attrs),
                self)


    # -- Constructor validation methods --------------------------------

    def _check_action(self):
        if self.action is None:
            self.action = "store"
        elif self.action not in self.ACTIONS:
            raise OptionError("invalid action: %r" % self.action, self)

    def _check_type(self):
        if self.type is None:
            if self.action in self.ALWAYS_TYPED_ACTIONS:
                if self.choices is not None:
                    # The "choices" attribute implies "choice" type.
                    self.type = "choice"
                else:
                    # No type given?  "string" is the most sensible default.
                    self.type = "string"
        else:
            # Allow type objects or builtin type conversion functions
            # (int, str, etc.) as an alternative to their names.  (The
            # complicated check of __builtin__ is only necessary for
            # Python 2.1 and earlier, and is short-circuited by the
            # first check on modern Pythons.)
            import __builtin__
            if ( type(self.type) is types.TypeType or
                 (hasattr(self.type, "__name__") and
                  getattr(__builtin__, self.type.__name__, None) is self.type) ):
                self.type = self.type.__name__

            if self.type == "str":
                self.type = "string"

            if self.type not in self.TYPES:
                raise OptionError("invalid option type: %r" % self.type, self)
            if self.action not in self.TYPED_ACTIONS:
                raise OptionError(
                    "must not supply a type for action %r" % self.action, self)

    def _check_choice(self):
        if self.type == "choice":
            if self.choices is None:
                raise OptionError(
                    "must supply a list of choices for type 'choice'", self)
            elif type(self.choices) not in (types.TupleType, types.ListType):
                raise OptionError(
                    "choices must be a list of strings ('%s' supplied)"
                    % str(type(self.choices)).split("'")[1], self)
        elif self.choices is not None:
            raise OptionError(
                "must not supply choices for type %r" % self.type, self)

    def _check_dest(self):
        # No destination given, and we need one for this action.  The
        # self.type check is for callbacks that take a value.
        takes_value = (self.action in self.STORE_ACTIONS or
                       self.type is not None)
        if self.dest is None and takes_value:

            # Glean a destination from the first long option string,
            # or from the first short option string if no long options.
            if self._long_opts:
                # eg. "--foo-bar" -> "foo_bar"
                self.dest = self._long_opts[0][2:].replace('-', '_')
            else:
                self.dest = self._short_opts[0][1]

    def _check_const(self):
        if self.action not in self.CONST_ACTIONS and self.const is not None:
            raise OptionError(
                "'const' must not be supplied for action %r" % self.action,
                self)

    def _check_nargs(self):
        if self.action in self.TYPED_ACTIONS:
            if self.nargs is None:
                self.nargs = 1
        elif self.nargs is not None:
            raise OptionError(
                "'nargs' must not be supplied for action %r" % self.action,
                self)

    def _check_callback(self):
        if self.action == "callback":
            if not callable(self.callback):
                raise OptionError(
                    "callback not callable: %r" % self.callback, self)
            if (self.callback_args is not None and
                type(self.callback_args) is not types.TupleType):
                raise OptionError(
                    "callback_args, if supplied, must be a tuple: not %r"
                    % self.callback_args, self)
            if (self.callback_kwargs is not None and
                type(self.callback_kwargs) is not types.DictType):
                raise OptionError(
                    "callback_kwargs, if supplied, must be a dict: not %r"
                    % self.callback_kwargs, self)
        else:
            if self.callback is not None:
                raise OptionError(
                    "callback supplied (%r) for non-callback option"
                    % self.callback, self)
            if self.callback_args is not None:
                raise OptionError(
                    "callback_args supplied for non-callback option", self)
            if self.callback_kwargs is not None:
                raise OptionError(
                    "callback_kwargs supplied for non-callback option", self)


    CHECK_METHODS = [_check_action,
                     _check_type,
                     _check_choice,
                     _check_dest,
                     _check_const,
                     _check_nargs,
                     _check_callback]


    # -- Miscellaneous methods -----------------------------------------

    def __str__(self):
        return "/".join(self._short_opts + self._long_opts)

    __repr__ = _repr

    def takes_value(self):
        return self.type is not None

    def get_opt_string(self):
        if self._long_opts:
            return self._long_opts[0]
        else:
            return self._short_opts[0]


    # -- Processing methods --------------------------------------------

    def check_value(self, opt, value):
        checker = self.TYPE_CHECKER.get(self.type)
        if checker is None:
            return value
        else:
            return checker(self, opt, value)

    def convert_value(self, opt, value):
        if value is not None:
            if self.nargs == 1:
                return self.check_value(opt, value)
            else:
                return tuple([self.check_value(opt, v) for v in value])

    def process(self, opt, value, values, parser):

        # First, convert the value(s) to the right type.  Howl if any
        # value(s) are bogus.
        value = self.convert_value(opt, value)

        # And then take whatever action is expected of us.
        # This is a separate method to make life easier for
        # subclasses to add new actions.
        return self.take_action(
            self.action, self.dest, opt, value, values, parser)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "store":
            setattr(values, dest, value)
        elif action == "store_const":
            setattr(values, dest, self.const)
        elif action == "store_true":
            setattr(values, dest, True)
        elif action == "store_false":
            setattr(values, dest, False)
        elif action == "append":
            values.ensure_value(dest, []).append(value)
        elif action == "append_const":
            values.ensure_value(dest, []).append(self.const)
        elif action == "count":
            setattr(values, dest, values.ensure_value(dest, 0) + 1)
        elif action == "callback":
            args = self.callback_args or ()
            kwargs = self.callback_kwargs or {}
            self.callback(self, opt, value, parser, *args, **kwargs)
        elif action == "help":
            parser.print_help()
            parser.exit()
        elif action == "version":
            parser.print_version()
            parser.exit()
        else:
            raise RuntimeError, "unknown action %r" % self.action

        return 1

# class Option


SUPPRESS_HELP = "SUPPRESS"+"HELP"
SUPPRESS_USAGE = "SUPPRESS"+"USAGE"

# For compatibility with Python 2.2
try:
    True, False
except NameError:
    (True, False) = (1, 0)

try:
    basestring
except NameError:
    def isbasestring(x):
        return isinstance(x, (types.StringType, types.UnicodeType))
else:
    def isbasestring(x):
        return isinstance(x, basestring)


class Values:

    def __init__(self, defaults=None):
        if defaults:
            for (attr, val) in defaults.items():
                setattr(self, attr, val)

    def __str__(self):
        return str(self.__dict__)

    __repr__ = _repr

    def __cmp__(self, other):
        if isinstance(other, Values):
            return cmp(self.__dict__, other.__dict__)
        elif isinstance(other, types.DictType):
            return cmp(self.__dict__, other)
        else:
            return -1

    def _update_careful(self, dict):
        """
        Update the option values from an arbitrary dictionary, but only
        use keys from dict that already have a corresponding attribute
        in self.  Any keys in dict without a corresponding attribute
        are silently ignored.
        """
        for attr in dir(self):
            if dict.has_key(attr):
                dval = dict[attr]
                if dval is not None:
                    setattr(self, attr, dval)

    def _update_loose(self, dict):
        """
        Update the option values from an arbitrary dictionary,
        using all keys from the dictionary regardless of whether
        they have a corresponding attribute in self or not.
        """
        self.__dict__.update(dict)

    def _update(self, dict, mode):
        if mode == "careful":
            self._update_careful(dict)
        elif mode == "loose":
            self._update_loose(dict)
        else:
            raise ValueError, "invalid update mode: %r" % mode

    def read_module(self, modname, mode="careful"):
        __import__(modname)
        mod = sys.modules[modname]
        self._update(vars(mod), mode)

    def read_file(self, filename, mode="careful"):
        vars = {}
        execfile(filename, vars)
        self._update(vars, mode)

    def ensure_value(self, attr, value):
        if not hasattr(self, attr) or getattr(self, attr) is None:
            setattr(self, attr, value)
        return getattr(self, attr)


class OptionContainer:

    """
    Abstract base class.

    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      option_list : [Option]
        the list of Option objects contained by this OptionContainer
      _short_opt : { string : Option }
        dictionary mapping short option strings, eg. "-f" or "-X",
        to the Option instances that implement them.  If an Option
        has multiple short option strings, it will appears in this
        dictionary multiple times. [1]
      _long_opt : { string : Option }
        dictionary mapping long option strings, eg. "--file" or
        "--exclude", to the Option instances that implement them.
        Again, a given Option can occur multiple times in this
        dictionary. [1]
      defaults : { string : any }
        dictionary mapping option destination names to default
        values for each destination [1]

    [1] These mappings are common to (shared by) all components of the
        controlling OptionParser, where they are initially created.

    """

    def __init__(self, option_class, conflict_handler, description):
        # Initialize the option list and related data structures.
        # This method must be provided by subclasses, and it must
        # initialize at least the following instance attributes:
        # option_list, _short_opt, _long_opt, defaults.
        self._create_option_list()

        self.option_class = option_class
        self.set_conflict_handler(conflict_handler)
        self.set_description(description)

    def _create_option_mappings(self):
        # For use by OptionParser constructor -- create the master
        # option mappings used by this OptionParser and all
        # OptionGroups that it owns.
        self._short_opt = {}            # single letter -> Option instance
        self._long_opt = {}             # long option -> Option instance
        self.defaults = {}              # maps option dest -> default value


    def _share_option_mappings(self, parser):
        # For use by OptionGroup constructor -- use shared option
        # mappings from the OptionParser that owns this OptionGroup.
        self._short_opt = parser._short_opt
        self._long_opt = parser._long_opt
        self.defaults = parser.defaults

    def set_conflict_handler(self, handler):
        if handler not in ("error", "resolve"):
            raise ValueError, "invalid conflict_resolution value %r" % handler
        self.conflict_handler = handler

    def set_description(self, description):
        self.description = description

    def get_description(self):
        return self.description


    def destroy(self):
        """see OptionParser.destroy()."""
        del self._short_opt
        del self._long_opt
        del self.defaults


    # -- Option-adding methods -----------------------------------------

    def _check_conflict(self, option):
        conflict_opts = []
        for opt in option._short_opts:
            if self._short_opt.has_key(opt):
                conflict_opts.append((opt, self._short_opt[opt]))
        for opt in option._long_opts:
            if self._long_opt.has_key(opt):
                conflict_opts.append((opt, self._long_opt[opt]))

        if conflict_opts:
            handler = self.conflict_handler
            if handler == "error":
                raise OptionConflictError(
                    "conflicting option string(s): %s"
                    % ", ".join([co[0] for co in conflict_opts]),
                    option)
            elif handler == "resolve":
                for (opt, c_option) in conflict_opts:
                    if opt.startswith("--"):
                        c_option._long_opts.remove(opt)
                        del self._long_opt[opt]
                    else:
                        c_option._short_opts.remove(opt)
                        del self._short_opt[opt]
                    if not (c_option._short_opts or c_option._long_opts):
                        c_option.container.option_list.remove(c_option)

    def add_option(self, *args, **kwargs):
        """add_option(Option)
           add_option(opt_str, ..., kwarg=val, ...)
        """
        if type(args[0]) is types.StringType:
            option = self.option_class(*args, **kwargs)
        elif len(args) == 1 and not kwargs:
            option = args[0]
            if not isinstance(option, Option):
                raise TypeError, "not an Option instance: %r" % option
        else:
            raise TypeError, "invalid arguments"

        self._check_conflict(option)

        self.option_list.append(option)
        option.container = self
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option

        if option.dest is not None:     # option has a dest, we need a default
            if option.default is not NO_DEFAULT:
                self.defaults[option.dest] = option.default
            elif not self.defaults.has_key(option.dest):
                self.defaults[option.dest] = None

        return option

    def add_options(self, option_list):
        for option in option_list:
            self.add_option(option)

    # -- Option query/removal methods ----------------------------------

    def get_option(self, opt_str):
        return (self._short_opt.get(opt_str) or
                self._long_opt.get(opt_str))

    def has_option(self, opt_str):
        return (self._short_opt.has_key(opt_str) or
                self._long_opt.has_key(opt_str))

    def remove_option(self, opt_str):
        option = self._short_opt.get(opt_str)
        if option is None:
            option = self._long_opt.get(opt_str)
        if option is None:
            raise ValueError("no such option %r" % opt_str)

        for opt in option._short_opts:
            del self._short_opt[opt]
        for opt in option._long_opts:
            del self._long_opt[opt]
        option.container.option_list.remove(option)


    # -- Help-formatting methods ---------------------------------------

    def format_option_help(self, formatter):
        if not self.option_list:
            return ""
        result = []
        for option in self.option_list:
            if not option.help is SUPPRESS_HELP:
                result.append(formatter.format_option(option))
        return "".join(result)

    def format_description(self, formatter):
        return formatter.format_description(self.get_description())

    def format_help(self, formatter):
        result = []
        if self.description:
            result.append(self.format_description(formatter))
        if self.option_list:
            result.append(self.format_option_help(formatter))
        return "\n".join(result)


class OptionGroup (OptionContainer):

    def __init__(self, parser, title, description=None):
        self.parser = parser
        OptionContainer.__init__(
            self, parser.option_class, parser.conflict_handler, description)
        self.title = title

    def _create_option_list(self):
        self.option_list = []
        self._share_option_mappings(self.parser)

    def set_title(self, title):
        self.title = title

    def destroy(self):
        """see OptionParser.destroy()."""
        OptionContainer.destroy(self)
        del self.option_list

    # -- Help-formatting methods ---------------------------------------

    def format_help(self, formatter):
        result = formatter.format_heading(self.title)
        formatter.indent()
        result += OptionContainer.format_help(self, formatter)
        formatter.dedent()
        return result


class OptionParser (OptionContainer):

    """
    Class attributes:
      standard_option_list : [Option]
        list of standard options that will be accepted by all instances
        of this parser class (intended to be overridden by subclasses).

    Instance attributes:
      usage : string
        a usage string for your program.  Before it is displayed
        to the user, "%prog" will be expanded to the name of
        your program (self.prog or os.path.basename(sys.argv[0])).
      prog : string
        the name of the current program (to override
        os.path.basename(sys.argv[0])).
      epilog : string
        paragraph of help text to print after option help

      option_groups : [OptionGroup]
        list of option groups in this parser (option groups are
        irrelevant for parsing the command-line, but very useful
        for generating help)

      allow_interspersed_args : bool = true
        if true, positional arguments may be interspersed with options.
        Assuming -a and -b each take a single argument, the command-line
          -ablah foo bar -bboo baz
        will be interpreted the same as
          -ablah -bboo -- foo bar baz
        If this flag were false, that command line would be interpreted as
          -ablah -- foo bar -bboo baz
        -- ie. we stop processing options as soon as we see the first
        non-option argument.  (This is the tradition followed by
        Python's getopt module, Perl's Getopt::Std, and other argument-
        parsing libraries, but it is generally annoying to users.)

      process_default_values : bool = true
        if true, option default values are processed similarly to option
        values from the command line: that is, they are passed to the
        type-checking function for the option's type (as long as the
        default value is a string).  (This really only matters if you
        have defined custom types; see SF bug #955889.)  Set it to false
        to restore the behaviour of Optik 1.4.1 and earlier.

      rargs : [string]
        the argument list currently being parsed.  Only set when
        parse_args() is active, and continually trimmed down as
        we consume arguments.  Mainly there for the benefit of
        callback options.
      largs : [string]
        the list of leftover arguments that we have skipped while
        parsing options.  If allow_interspersed_args is false, this
        list is always empty.
      values : Values
        the set of option values currently being accumulated.  Only
        set when parse_args() is active.  Also mainly for callbacks.

    Because of the 'rargs', 'largs', and 'values' attributes,
    OptionParser is not thread-safe.  If, for some perverse reason, you
    need to parse command-line arguments simultaneously in different
    threads, use different OptionParser instances.

    """

    standard_option_list = []

    def __init__(self,
                 usage=None,
                 option_list=None,
                 option_class=Option,
                 version=None,
                 conflict_handler="error",
                 description=None,
                 formatter=None,
                 add_help_option=True,
                 prog=None,
                 epilog=None):
        OptionContainer.__init__(
            self, option_class, conflict_handler, description)
        self.set_usage(usage)
        self.prog = prog
        self.version = version
        self.allow_interspersed_args = True
        self.process_default_values = True
        if formatter is None:
            formatter = IndentedHelpFormatter()
        self.formatter = formatter
        self.formatter.set_parser(self)
        self.epilog = epilog

        # Populate the option list; initial sources are the
        # standard_option_list class attribute, the 'option_list'
        # argument, and (if applicable) the _add_version_option() and
        # _add_help_option() methods.
        self._populate_option_list(option_list,
                                   add_help=add_help_option)

        self._init_parsing_state()


    def destroy(self):
        """
        Declare that you are done with this OptionParser.  This cleans up
        reference cycles so the OptionParser (and all objects referenced by
        it) can be garbage-collected promptly.  After calling destroy(), the
        OptionParser is unusable.
        """
        OptionContainer.destroy(self)
        for group in self.option_groups:
            group.destroy()
        del self.option_list
        del self.option_groups
        del self.formatter


    # -- Private methods -----------------------------------------------
    # (used by our or OptionContainer's constructor)

    def _create_option_list(self):
        self.option_list = []
        self.option_groups = []
        self._create_option_mappings()

    def _add_help_option(self):
        self.add_option("-h", "--help",
                        action="help",
                        help=_("show this help message and exit"))

    def _add_version_option(self):
        self.add_option("--version",
                        action="version",
                        help=_("show program's version number and exit"))

    def _populate_option_list(self, option_list, add_help=True):
        if self.standard_option_list:
            self.add_options(self.standard_option_list)
        if option_list:
            self.add_options(option_list)
        if self.version:
            self._add_version_option()
        if add_help:
            self._add_help_option()

    def _init_parsing_state(self):
        # These are set in parse_args() for the convenience of callbacks.
        self.rargs = None
        self.largs = None
        self.values = None


    # -- Simple modifier methods ---------------------------------------

    def set_usage(self, usage):
        if usage is None:
            self.usage = _("%prog [options]")
        elif usage is SUPPRESS_USAGE:
            self.usage = None
        # For backwards compatibility with Optik 1.3 and earlier.
        elif usage.lower().startswith("usage: "):
            self.usage = usage[7:]
        else:
            self.usage = usage

    def enable_interspersed_args(self):
        self.allow_interspersed_args = True

    def disable_interspersed_args(self):
        self.allow_interspersed_args = False

    def set_process_default_values(self, process):
        self.process_default_values = process

    def set_default(self, dest, value):
        self.defaults[dest] = value

    def set_defaults(self, **kwargs):
        self.defaults.update(kwargs)

    def _get_all_options(self):
        options = self.option_list[:]
        for group in self.option_groups:
            options.extend(group.option_list)
        return options

    def get_default_values(self):
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return Values(self.defaults)

        defaults = self.defaults.copy()
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isbasestring(default):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)

        return Values(defaults)


    # -- OptionGroup methods -------------------------------------------

    def add_option_group(self, *args, **kwargs):
        # XXX lots of overlap with OptionContainer.add_option()
        if type(args[0]) is types.StringType:
            group = OptionGroup(self, *args, **kwargs)
        elif len(args) == 1 and not kwargs:
            group = args[0]
            if not isinstance(group, OptionGroup):
                raise TypeError, "not an OptionGroup instance: %r" % group
            if group.parser is not self:
                raise ValueError, "invalid OptionGroup (wrong parser)"
        else:
            raise TypeError, "invalid arguments"

        self.option_groups.append(group)
        return group

    def get_option_group(self, opt_str):
        option = (self._short_opt.get(opt_str) or
                  self._long_opt.get(opt_str))
        if option and option.container is not self:
            return option.container
        return None


    # -- Option-parsing methods ----------------------------------------

    def _get_args(self, args):
        if args is None:
            return sys.argv[1:]
        else:
            return args[:]              # don't modify caller's list

    def parse_args(self, args=None, values=None):
        """
        parse_args(args : [string] = sys.argv[1:],
                   values : Values = None)
        -> (values : Values, args : [string])

        Parse the command-line options found in 'args' (default:
        sys.argv[1:]).  Any errors result in a call to 'error()', which
        by default prints the usage message to stderr and calls
        sys.exit() with an error message.  On success returns a pair
        (values, args) where 'values' is an Values instance (with all
        your option values) and 'args' is the list of arguments left
        over after parsing options.
        """
        rargs = self._get_args(args)
        if values is None:
            values = self.get_default_values()

        # Store the halves of the argument list as attributes for the
        # convenience of callbacks:
        #   rargs
        #     the rest of the command-line (the "r" stands for
        #     "remaining" or "right-hand")
        #   largs
        #     the leftover arguments -- ie. what's left after removing
        #     options and their arguments (the "l" stands for "leftover"
        #     or "left-hand")
        self.rargs = rargs
        self.largs = largs = []
        self.values = values

        try:
            stop = self._process_args(largs, rargs, values)
        except (BadOptionError, OptionValueError), err:
            self.error(str(err))

        args = largs + rargs
        return self.check_values(values, args)

    def check_values(self, values, args):
        """
        check_values(values : Values, args : [string])
        -> (values : Values, args : [string])

        Check that the supplied option values and leftover arguments are
        valid.  Returns the option values and leftover arguments
        (possibly adjusted, possibly completely new -- whatever you
        like).  Default implementation just returns the passed-in
        values; subclasses may override as desired.
        """
        return (values, args)

    def _process_args(self, largs, rargs, values):
        """_process_args(largs : [string],
                         rargs : [string],
                         values : Values)

        Process command-line arguments and populate 'values', consuming
        options and arguments from 'rargs'.  If 'allow_interspersed_args' is
        false, stop at the first non-option argument.  If true, accumulate any
        interspersed non-option arguments in 'largs'.
        """
        while rargs:
            arg = rargs[0]
            # We handle bare "--" explicitly, and bare "-" is handled by the
            # standard arg handler since the short arg case ensures that the
            # len of the opt string is greater than 1.
            if arg == "--":
                del rargs[0]
                return
            elif arg[0:2] == "--":
                # process a single long option (possibly with value(s))
                self._process_long_opt(rargs, values)
            elif arg[:1] == "-" and len(arg) > 1:
                # process a cluster of short options (possibly with
                # value(s) for the last one only)
                self._process_short_opts(rargs, values)
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]
            else:
                return                  # stop now, leave this arg in rargs

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                            ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)] and largs is a *subset* of
        # [arg0, ..., arg(i-1)] (any options and their arguments will have
        # been removed from largs).
        #
        # The while loop will usually consume 1 or more arguments per pass.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

    def _match_long_opt(self, opt):
        """_match_long_opt(opt : string) -> string

        Determine which long option string 'opt' matches, ie. which one
        it is an unambiguous abbrevation for.  Raises BadOptionError if
        'opt' doesn't unambiguously match any long option string.
        """
        return _match_abbrev(opt, self._long_opt)

    def _process_long_opt(self, rargs, values):
        arg = rargs.pop(0)

        # Value explicitly attached to arg?  Pretend it's the next
        # argument.
        if "=" in arg:
            (opt, next_arg) = arg.split("=", 1)
            rargs.insert(0, next_arg)
            had_explicit_value = True
        else:
            opt = arg
            had_explicit_value = False

        opt = self._match_long_opt(opt)
        option = self._long_opt[opt]
        if option.takes_value():
            nargs = option.nargs
            if len(rargs) < nargs:
                if nargs == 1:
                    self.error(_("%s option requires an argument") % opt)
                else:
                    self.error(_("%s option requires %d arguments")
                               % (opt, nargs))
            elif nargs == 1:
                value = rargs.pop(0)
            else:
                value = tuple(rargs[0:nargs])
                del rargs[0:nargs]

        elif had_explicit_value:
            self.error(_("%s option does not take a value") % opt)

        else:
            value = None

        option.process(opt, value, values, self)

    def _process_short_opts(self, rargs, values):
        arg = rargs.pop(0)
        stop = False
        i = 1
        for ch in arg[1:]:
            opt = "-" + ch
            option = self._short_opt.get(opt)
            i += 1                      # we have consumed a character

            if not option:
                raise BadOptionError(opt)
            if option.takes_value():
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    rargs.insert(0, arg[i:])
                    stop = True

                nargs = option.nargs
                if len(rargs) < nargs:
                    if nargs == 1:
                        self.error(_("%s option requires an argument") % opt)
                    else:
                        self.error(_("%s option requires %d arguments")
                                   % (opt, nargs))
                elif nargs == 1:
                    value = rargs.pop(0)
                else:
                    value = tuple(rargs[0:nargs])
                    del rargs[0:nargs]

            else:                       # option doesn't take a value
                value = None

            option.process(opt, value, values, self)

            if stop:
                break


    # -- Feedback methods ----------------------------------------------

    def get_prog_name(self):
        if self.prog is None:
            return os.path.basename(sys.argv[0])
        else:
            return self.prog

    def expand_prog_name(self, s):
        return s.replace("%prog", self.get_prog_name())

    def get_description(self):
        return self.expand_prog_name(self.description)

    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(msg)
        sys.exit(status)

    def error(self, msg):
        """error(msg : string)

        Print a usage message incorporating 'msg' to stderr and exit.
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        self.print_usage(sys.stderr)
        self.exit(2, "%s: error: %s\n" % (self.get_prog_name(), msg))

    def get_usage(self):
        if self.usage:
            return self.formatter.format_usage(
                self.expand_prog_name(self.usage))
        else:
            return ""

    def print_usage(self, file=None):
        """print_usage(file : file = stdout)

        Print the usage message for the current program (self.usage) to
        'file' (default stdout).  Any occurence of the string "%prog" in
        self.usage is replaced with the name of the current program
        (basename of sys.argv[0]).  Does nothing if self.usage is empty
        or not defined.
        """
        if self.usage:
            print >>file, self.get_usage()

    def get_version(self):
        if self.version:
            return self.expand_prog_name(self.version)
        else:
            return ""

    def print_version(self, file=None):
        """print_version(file : file = stdout)

        Print the version message for this program (self.version) to
        'file' (default stdout).  As with print_usage(), any occurence
        of "%prog" in self.version is replaced by the current program's
        name.  Does nothing if self.version is empty or undefined.
        """
        if self.version:
            print >>file, self.get_version()

    def format_option_help(self, formatter=None):
        if formatter is None:
            formatter = self.formatter
        formatter.store_option_strings(self)
        result = []
        result.append(formatter.format_heading(_("Options")))
        formatter.indent()
        if self.option_list:
            result.append(OptionContainer.format_option_help(self, formatter))
            result.append("\n")
        for group in self.option_groups:
            result.append(group.format_help(formatter))
            result.append("\n")
        formatter.dedent()
        # Drop the last "\n", or the header if no options or option groups:
        return "".join(result[:-1])

    def format_epilog(self, formatter):
        return formatter.format_epilog(self.epilog)

    def format_help(self, formatter=None):
        if formatter is None:
            formatter = self.formatter
        result = []
        if self.usage:
            result.append(self.get_usage() + "\n")
        if self.description:
            result.append(self.format_description(formatter) + "\n")
        result.append(self.format_option_help(formatter))
        result.append(self.format_epilog(formatter))
        return "".join(result)

    # used by test suite
    def _get_encoding(self, file):
        encoding = getattr(file, "encoding", None)
        if not encoding:
            encoding = sys.getdefaultencoding()
        return encoding

    def print_help(self, file=None):
        """print_help(file : file = stdout)

        Print an extended help message, listing all options and any
        help text provided with them, to 'file' (default stdout).
        """
        if file is None:
            file = sys.stdout
        encoding = self._get_encoding(file)
        file.write(self.format_help().encode(encoding, "replace"))

# class OptionParser


def _match_abbrev(s, wordmap):
    """_match_abbrev(s : string, wordmap : {string : Option}) -> string

    Return the string key in 'wordmap' for which 's' is an unambiguous
    abbreviation.  If 's' is found to be ambiguous or doesn't match any of
    'words', raise BadOptionError.
    """
    # Is there an exact match?
    if wordmap.has_key(s):
        return s
    else:
        # Isolate all words with s as a prefix.
        possibilities = [word for word in wordmap.keys()
                         if word.startswith(s)]
        # No exact match, so there had better be just one possibility.
        if len(possibilities) == 1:
            return possibilities[0]
        elif not possibilities:
            raise BadOptionError(s)
        else:
            # More than one possible completion: ambiguous prefix.
            possibilities.sort()
            raise AmbiguousOptionError(s, possibilities)


# Some day, there might be many Option classes.  As of Optik 1.3, the
# preferred way to instantiate Options is indirectly, via make_option(),
# which will become a factory function when there are many Option
# classes.
make_option = Option

########NEW FILE########
__FILENAME__ = profiling
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

def label(code):
    if isinstance(code, str):
        return ('~', 0, code)    # built-in functions ('~' sorts at the end)
    else:
        return '%s %s:%d' % (code.co_name, code.co_filename, code.co_firstlineno)


class KCacheGrind(object):
    def __init__(self, profiler):
        self.data = profiler.getstats()
        self.out_file = None

    def output(self, out_file):
        self.out_file = out_file
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for entry in self.data:
            self._entry(entry)

    def _print_summary(self):
        max_cost = 0
        for entry in self.data:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, entry):
        out_file = self.out_file
        code = entry.code
        inlinetime = int(entry.inlinetime * 1000)
        #print >> out_file, 'ob=%s' % (code.co_filename,)
        if isinstance(code, str):
            print >> out_file, 'fi=~'
        else:
            print >> out_file, 'fi=%s' % (code.co_filename,)
        print >> out_file, 'fn=%s' % (label(code),)
        if isinstance(code, str):
            print >> out_file, '0 ', inlinetime
        else:
            print >> out_file, '%d %d' % (code.co_firstlineno, inlinetime)
        # recursive calls are counted in entry.calls
        if entry.calls:
            calls = entry.calls
        else:
            calls = []
        if isinstance(code, str):
            lineno = 0
        else:
            lineno = code.co_firstlineno
        for subentry in calls:
            self._subentry(lineno, subentry)
        print >> out_file

    def _subentry(self, lineno, subentry):
        out_file = self.out_file
        code = subentry.code
        totaltime = int(subentry.totaltime * 1000)
        #print >> out_file, 'cob=%s' % (code.co_filename,)
        print >> out_file, 'cfn=%s' % (label(code),)
        if isinstance(code, str):
            print >> out_file, 'cfi=~'
            print >> out_file, 'calls=%d 0' % (subentry.callcount,)
        else:
            print >> out_file, 'cfi=%s' % (code.co_filename,)
            print >> out_file, 'calls=%d %d' % (
                subentry.callcount, code.co_firstlineno)
        print >> out_file, '%d %d' % (lineno, totaltime)

def profile_func(filename=None, mode='w+'):
    """Function/method decorator that will cause only the decorated callable
        to be profiled (with a C{KCacheGrind} profiler) and saved to the
        specified file.

        @type  filename: str
        @param filename: The filename to write the profile to. If not specified
            the decorated function's name is used, followed by "_func.profile".
        @type  mode: str
        @param mode: The mode in which to open C{filename}. Default is 'w+'."""
    def proffunc(f):
        def profiled_func(*args, **kwargs):
            import cProfile
            import logging

            logging.info('Profiling function %s' % (f.__name__))

            try:
                profile_file = open(filename or '%s_func.profile' % (f.__name__), mode)
                profiler = cProfile.Profile()
                retval = profiler.runcall(f, *args, **kwargs)
                k_cache_grind = KCacheGrind(profiler)
                k_cache_grind.output(profile_file)
                profile_file.close()
            except IOError:
                logging.exception(_("Could not open profile file '%(filename)s'") % {"filename": filename})

            return retval

        return profiled_func
    return proffunc

########NEW FILE########
__FILENAME__ = tmp_strings
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

# This just contains some strings that are bugfixes that need to be translatable

_("Gettext PO file")
_("Gettext MO file")
_("Qt .qm file")
_("OmegaT Glossary")

########NEW FILE########
__FILENAME__ = update_autocorr
#!/usr/bin/python
"""
Quick and dirty autocorr file downloader

Downloads all available autocor files from OpenOffice.org Mercurial repository.
Works in the current directory.
"""

import urllib
import re

HG_AUTOCORR_DIR = 'http://hg.services.openoffice.org/DEV300/file/tip/extras/source/autotext/lang'
FILE_PATTERN = re.compile('acor_(.*).dat')
SKIP_LANGS = ("eu",) # garbage == en-US

langs = []

print "Getting language list..."

for line in urllib.urlopen('%s/?style=raw' % HG_AUTOCORR_DIR).readlines():
    if line.startswith("drwx"): # readable, executable directory
        lang = line.split()[1]
        if lang not in SKIP_LANGS:
            langs.append(lang)
        else:
            print "Skipping %s" % lang

print "done"
print "Available languages: %s" % " ".join(langs)

for lang in langs:
    for line in urllib.urlopen('%s/%s/?style=raw' % (HG_AUTOCORR_DIR, lang)).readlines():
        try:
            chmod, size, fname = line.split()
            if FILE_PATTERN.match(fname):
                print "Downloading %s (%s bytes)..." % (fname, size)
                file_contents = urllib.urlopen('%s/%s/%s?style=raw' %
                                               (HG_AUTOCORR_DIR, lang, fname)).read()
                file(fname, "wb").write(file_contents)
                print "done"
        except ValueError:
            # don't process empty lines
            pass

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Virtaal documentation build configuration file.
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

sys.path.insert(0, os.path.abspath('_ext'))
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions # coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
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
project = u'Virtaal'
copyright = u'2013, Translate'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.7.1'
# The full version, including alpha/beta/rc tags.
release = '0.7.1'

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
exclude_patterns = ['_build', '_themes/README.rst']

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx-bootstrap'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'nosidebar': True,
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
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = '../share/icons/virtaal.png'

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
html_show_sourcelink = False

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
htmlhelp_basename = 'Virtaaldoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual])
latex_documents = [
  ('index', 'Virtaal.tex', u'Virtaal Documentation',
   u'Translate', 'manual'),
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


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'virtaal', u'Virtaal Documentation',
     [u'Translate'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Virtaal', u'Virtaal Documentation',
   u'Translate', 'Virtaal', 'Powerful, uncluttered XLIFF and PO editor.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Coverage checker options -------------------------------------------------

coverage_ignore_modules = []

coverage_ignore_functions = ['main']

coverage_ignore_classes = []

coverage_write_headline = False

# -- Options for Intersphinx -------------------------------------------------

intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7', None),
    'django': ('http://django.readthedocs.org/en/latest/', None),
    'pootle': ('http://docs.translatehouse.org/projects/pootle/en/latest/', None),
    'toolkit': ('http://docs.translatehouse.org/projects/translate-toolkit/en/latest/', None),
}


# -- Options for Exernal links -------------------------------------------------

extlinks = {
    # :role: (URL, prefix)
    'bug': ('http://bugs.locamotion.org/show_bug.cgi?id=%s',
            'bug '),
    'man': ('http://linux.die.net/man/1/%s', ''),
    'wp': ('http://en.wikipedia.org/wiki/%s', ''),
    'wiki': ('http://translate.sourceforge.net/wiki/%s', ''),
}

# -- Options for Linkcheck -------------------------------------------------

# Add regex's here for links that should be ignored.
linkcheck_ignore = [
    'http://open-tran.eu',  # Doesn't seem to respond at all but is live
]

########NEW FILE########
__FILENAME__ = gobjectwrapper
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from gobject import GObject, signal_list_names
#import logging


class GObjectWrapper(GObject):
    """
    A wrapper for GObject sub-classes that provides some more powerful signal-
    handling.
    """

    # INITIALIZERS #
    def __init__(self):
        GObject.__init__(self)
        self._all_signals = signal_list_names(self.__gtype_name__)
        self._enabled_signals = list(self._all_signals)


    # METHODS #
    def disable_signals(self, signals=[]):
        """Disable all or specified signals."""
        if signals:
            for sig in signals:
                if sig in self._enabled_signals:
                    self._enabled_signals.remove(sig)
        else:
            self._enabled_signals = []

    def enable_signals(self, signals=[]):
        """Enable all or specified signals."""
        if signals:
            for sig in signals:
                if sig not in self._enabled_signals:
                    self._enabled_signals.append(sig)
        else:
            self._enabled_signals = list(self._all_signals) # Enable all signals

    def emit(self, signame, *args):
        if signame in self._enabled_signals:
            #logging.debug('emit("%s", %s)' % (signame, ','.join([repr(arg) for arg in args])))
            GObject.emit(self, signame, *args)

########NEW FILE########
__FILENAME__ = pan_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007-2010 Zuza Software Foundation
# Copyright 2013-2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


#XXX: main imports lower down


# Before we even try to get anything done, set up stdout and stderr on our
# packaged windows build. This has to happen as early as possible, otherwise
# error messages will not be available for inspection.
import os
import sys

def get_config_dir():
    if os.name == 'nt':
        confdir = os.path.join(os.environ['APPDATA'], 'Virtaal')
    elif sys.platform == 'darwin':
        confdir = os.path.expanduser('~/Library/Application Support/Virtaal')
    else:
        #TODO: skuif na ~/.config/virtaal en migreer
        confdir = os.path.expanduser('~/.virtaal')

    confdir = confdir.decode(sys.getfilesystemencoding())
    if not os.path.exists(confdir):
        os.makedirs(confdir)

    return confdir

if os.name == 'nt':
    filename_template = os.path.join(get_config_dir(), '%s_virtaal.log')
    sys.stdout = open(filename_template % ('stdout'), 'w')
    sys.stderr = open(filename_template % ('stderr'), 'w')


# Ok, now we can continue with what we actually wanted to do

import ConfigParser
import locale, gettext
from virtaal.support.libi18n.locale import fix_locale, fix_libintl
from translate.misc import file_discovery
from translate.lang import data

from virtaal.__version__ import ver

DEBUG = True # Enable debugging by default, while bin/virtaal still disables it by default.
             # This means that if Virtaal (or parts thereof) is run in some other strange way,
             # debugging is enabled.


x_generator = 'Virtaal ' + ver
default_config_name = u"virtaal.ini"


def osx_lang():
    """Do some non-posix things to get the language on OSX."""
    import CoreFoundation
    return CoreFoundation.CFLocaleCopyPreferredLanguages()[0]

def get_locale_lang():
    #if we wanted to determine the UI language ourselves, this should work:
    #lang = locale.getdefaultlocale(('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'))[0]
    #if not lang and sys.platform == "darwin":
    #   lang = osx_lang()

    # guess default target lang based on locale, simplify to commonly used form
    try:
        lang = locale.getdefaultlocale(('LANGUAGE', 'LC_ALL', 'LANG'))[0]
        if not lang and sys.platform == "darwin":
           lang = osx_lang()
        if lang:
            return data.simplify_to_common(lang)
    except Exception, e:
        import logging
        logging.warning("%s", e)
    return 'en'

def name():
    import getpass
    name = getpass.getuser().decode(sys.getfilesystemencoding()) #username only
    # pwd is only available on UNIX
    try:
        import pwd
        name = pwd.getpwnam(name)[4].split(",")[0]
    except ImportError, _e:
        pass
    return name or u""

def get_default_font():
    default_font = 'monospace'
    font_size = ''

    # First try and get the default font size from GConf
    try:
        import gconf
        client = gconf.client_get_default()
        client.add_dir('/desktop/gnome/interface', gconf.CLIENT_PRELOAD_NONE)
        font_name = client.get_string('/desktop/gnome/interface/monospace_font_name')
        font_size = font_name.split(' ')[-1]
    except ImportError, ie:
        import logging
        logging.debug('Unable to import gconf module: %s', ie)
    except Exception:
        # Ignore any other errors and try the next method
        pass

    # Get the default font size from Gtk
    if not font_size:
        import gtk
        font_name = str(gtk.Label().rc_get_style().font_desc)
        font_size = font_name.split(' ')[-1]

    if font_size:
        default_font += ' ' + font_size

    return default_font

defaultfont = get_default_font()


class Settings:
    """Handles loading/saving settings from/to a configuration file."""

    sections = ["translator", "general", "language", "placeable_state", "plugin_state", "undo"]

    translator =    {
        "name": name(),
        "email": "",
        "team": "",
    }
    general =       {
        "lastdir": "",
        "maximized": '',
        "windowwidth": 796,
        "windowheight": 544,
    }
    language =      {
        "nplurals": 0,
        "plural": None,
        "recentlangs": "",
        "sourcefont": defaultfont,
        "sourcelang": "en",
        "targetfont": defaultfont,
        "targetlang": None,
        "uilang": "",
    }
    placeable_state = {
        "altattrplaceable": "disabled",
        "fileplaceable": "disabled",
    }
    plugin_state =  {
        "_helloworld": "disabled",
    }
    undo = {
        "depth": 10000,
    }

    def __init__(self, filename = None):
        """Load settings, using the given or default filename"""
        if not filename:
            self.filename = os.path.join(get_config_dir(), default_config_name)
        else:
            self.filename = filename
            if not os.path.isfile(self.filename):
                raise Exception

        self.language["targetlang"] = data.simplify_to_common(get_locale_lang())
        self.config = ConfigParser.RawConfigParser()
        self.read()

    def read(self):
        """Read the configuration file and set the dictionaries up."""
        self.config.read(self.filename)
        for section in self.sections:
            if not self.config.has_section(section):
                self.config.add_section(section)

        for key, value in self.config.items("translator"):
            self.translator[key] = value
        for key, value in self.config.items("general"):
            self.general[key] = value
        for key, value in self.config.items("language"):
            self.language[key] = value
        for key, value in self.config.items("placeable_state"):
            self.placeable_state[key] = value
        for key, value in self.config.items("plugin_state"):
            self.plugin_state[key] = value
        for key, value in self.config.items("undo"):
            self.undo[key] = value

        # Make sure we have some kind of font names to work with
        for font in ('sourcefont', 'targetfont'):
            if not self.language[font]:
                self.language[font] = defaultfont

    def write(self):
        """Write the configuration file."""

        # Don't save the default font to file
        fonts = (self.language['sourcefont'], self.language['targetfont'])
        for font in ('sourcefont', 'targetfont'):
            if self.language[font] == defaultfont:
                self.language[font] = ''

        for key in self.translator:
            self.config.set("translator", key, self.translator[key])
        for key in self.general:
            self.config.set("general", key, self.general[key])
        for key in self.language:
            self.config.set("language", key, self.language[key])
        for key in self.placeable_state:
            self.config.set("placeable_state", key, self.placeable_state[key])
        for key in self.plugin_state:
            self.config.set("plugin_state", key, self.plugin_state[key])
        for key in self.undo:
            self.config.set("undo", key, self.undo[key])

        # make sure that the configuration directory exists
        project_dir = os.path.split(self.filename)[0]
        if not os.path.isdir(project_dir):
            os.makedirs(project_dir)
        file = open(self.filename, 'w')
        self.config.write(file)
        file.close()

        self.language['sourcefont'] = fonts[0]
        self.language['targetfont'] = fonts[1]

settings = Settings()

ui_language = settings.language["uilang"]
if ui_language:
    locale_lang = get_locale_lang()
    fix_locale(ui_language)
    try:
        locale.setlocale(locale.LC_ALL, ui_language)
    except locale.Error:
        pass
    languages = [ui_language, locale_lang]
    gettext.translation('virtaal', languages=languages, fallback=True).install(unicode=1)
else:
    fix_locale()
    try:
        #if the locale is not installed it can cause a traceback
        locale.setlocale(locale.LC_ALL, '')
        gettext.install("virtaal", unicode=1)
    except locale.Error, e:
        import logging
        logging.warning("Couldn't set the locale: %s", e)
        # See bug 3109
        __builtin__.__dict__['_'] = lambda s: s


# Determine the directory the main executable is running from
main_dir = u''
if getattr(sys, 'frozen', False):
    main_dir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
else:
    main_dir = os.path.dirname(unicode(sys.argv[0], sys.getfilesystemencoding()))


if os.name =='nt' and getattr(sys, 'frozen', False):
    fix_libintl(main_dir)

if _(''):
    # If this is true, we have a translated interface
    ui_language = ui_language or get_locale_lang()
else:
    ui_language = 'en'


def get_abs_data_filename(path_parts, basedirs=None):
    """Get the absolute path to the given file- or directory name in Virtaal's
        data directory.

        @type  path_parts: list
        @param path_parts: The path parts that can be joined by os.path.join().
        """
    if basedirs is None:
        basedirs = []
    basedirs += [
        os.path.join(os.path.dirname(unicode(__file__, sys.getfilesystemencoding())), os.path.pardir),
    ]
    return file_discovery.get_abs_data_filename(path_parts, basedirs=basedirs)

def load_config(filename, section=None):
    """Load the configuration from the given filename (and optional section
        into a dictionary structure.

        @returns: A 2D-dictionary representing the configuration file if no
            section was specified. Otherwise a simple dictionary representing
            the given configuration section."""
    parser = ConfigParser.RawConfigParser()
    parser.read(filename)

    if section:
        if section not in parser.sections():
            return {}
        return dict(parser.items(section))

    conf = {}
    for section in parser.sections():
        conf[section] = dict(parser.items(section))
    return conf

def save_config(filename, config, section=None):
    """Save the given configuration data to the given filename and under the
        given section (if specified).

        @param config: A dictionary containing the configuration section data
            if C{section} was specified. Otherwise, if C{section} is not
            specified, it should be a 2D-dictionary representing the entire
            configuration file."""
    parser = ConfigParser.ConfigParser()
    parser.read(filename)

    if section:
        config = {section: config}

    for sect in config.keys():
        parser.remove_section(sect)

    for section, section_conf in config.items():
        if section not in parser.sections():
            parser.add_section(section)
        for key, value in section_conf.items():
            if isinstance(value, list):
                value = ','.join(value)
            parser.set(section, key, value)

    conffile = open(filename, 'w')
    parser.write(conffile)
    conffile.close()

########NEW FILE########
__FILENAME__ = basecontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from virtaal.common import GObjectWrapper


class BaseController(GObjectWrapper):
    """Interface for controllers."""

    def __init__(self):
        raise NotImplementedError('This interface cannot be instantiated.')

########NEW FILE########
__FILENAME__ = baseplugin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os

from virtaal.common import pan_app

class PluginUnsupported(Exception):
    pass

class BasePlugin(object):
    """The base interface to be implemented by all plug-ins."""

    configure_func = None
    """A function that starts the plug-in's configuration, if available."""
    description = ''
    """A description about the plug-in's purpose."""
    display_name = ''
    """The plug-in's name, suitable for display."""
    version = 0
    """The plug-in's version number."""
    default_config = {}

    # INITIALIZERS #
    def __new__(cls, *args, **kwargs):
        """Create a new plug-in instance and check that it is valid."""
        if not cls.display_name:
            raise Exception('No name specified')
        if cls.version <= 0:
            raise Exception('Invalid version number specified')
        return super(BasePlugin, cls).__new__(cls)

    def __init__(self):
        raise NotImplementedError('This interface cannot be instantiated.')

    # METHODS #
    def destroy(self):
        """This method is called by C{PluginController.shutdown()} and should be
            implemented by all plug-ins that need to do clean-up."""
        pass

    def load_config(self):
        """Load plugin config from default location."""
        self.config = {}
        self.config.update(self.default_config)
        config_file = os.path.join(pan_app.get_config_dir(), "plugins.ini")
        self.config.update(pan_app.load_config(config_file, self.internal_name))

    def save_config(self):
        """Save plugin config to default location."""
        config_file = os.path.join(pan_app.get_config_dir(), "plugins.ini")
        pan_app.save_config(config_file, self.config, self.internal_name)

########NEW FILE########
__FILENAME__ = checkscontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
from gobject import SIGNAL_RUN_FIRST, timeout_add

from virtaal.common import GObjectWrapper

from basecontroller import BaseController

check_names = {
    'fuzzy': _(u"Fuzzy"),
    'untranslated': _(u"Untranslated"),
    'accelerators': _(u"Accelerators"),
    'acronyms': _(u"Acronyms"),
    'blank': _(u"Blank"),
    'brackets': _(u"Brackets"),
    'compendiumconflicts': _(u"Compendium conflict"),
    'credits': _(u"Translator credits"),
    'doublequoting': _(u"Double quotes"),
    'doublespacing': _(u"Double spaces"),
    'doublewords': _(u"Repeated word"),
    'emails': _(u"E-mail"),
    'endpunc': _(u"Ending punctuation"),
    'endwhitespace': _(u"Ending whitespace"),
    'escapes': _(u"Escapes"),
    'filepaths': _(u"File paths"),
    'functions': _(u"Functions"),
    'gconf': _(u"GConf values"),
    'kdecomments': _(u"Old KDE comment"),
    'long': _(u"Long"),
    'musttranslatewords': _(u"Must translate words"),
    'newlines': _(u"Newlines"),
    'nplurals': _(u"Number of plurals"),
    'notranslatewords': _(u"Don't translate words"),
    'numbers': _(u"Numbers"),
    'options': _(u"Options"),
    'printf': _(u"printf()"),
    'puncspacing': _(u"Punctuation spacing"),
    'purepunc': _(u"Pure punctuation"),
    'sentencecount': _(u"Number of sentences"),
    'short': _(u"Short"),
    'simplecaps': _(u"Simple capitalization"),
    'simpleplurals': _(u"Simple plural(s)"),
    'singlequoting': _(u"Single quotes"),
    'spellcheck': _(u"Spelling"),
    'startcaps': _(u"Starting capitalization"),
    'startpunc': _(u"Starting punctuation"),
    'startwhitespace': _(u"Starting whitespace"),
    'tabs': _(u"Tabs"),
    'unchanged': _(u"Unchanged"),
    'urls': _(u"URLs"),
    'validchars': _(u"Valid characters"),
    'variables': _(u"Placeholders"),
    'xmltags': _(u"XML tags"),

# Consider:
#  -  hassuggestion
#  -  isreview
}


class ChecksController(BaseController):
    """Controller for quality checks."""

    __gtype_name__ = 'ChecksController'
    __gsignals__ = {
        'checker-set':  (SIGNAL_RUN_FIRST, None, (object,)),
        'unit-checked': (SIGNAL_RUN_FIRST, None, (object, object, object))
    }

    CHECK_TIMEOUT = 500
    """Time to wait before performing checks on the current unit."""

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.checks_controller = self
        self.store_controller = main_controller.store_controller

        main_controller.store_controller.connect('store-loaded', self._on_store_loaded)
        main_controller.unit_controller.connect('unit-modified', self._on_unit_modified)
        if main_controller.lang_controller:
            main_controller.lang_controller.connect('target-lang-changed', self._on_target_lang_changed)
        else:
            main_controller.connect('controller-registered', self._on_controller_registered)

        self.code = None
        self._checker = None
        self._check_timer_active = False
        self._checker_code_to_name = {
              None: _('Default'),
              "openoffice":  _('OpenOffice.org'),
              "mozilla": _('Mozilla'),
              "kde": _('KDE'),
              "gnome": _('GNOME'),
              "drupal": _('Drupal'),
        }
        self._checker_name_to_code = dict([(value, key) for (key, value) in self._checker_code_to_name.items()])
        self._checker_info = None
        self._checker_menu_items = {}
        self._cursor_connection = ()
        self.last_unit = None

        self._projview = None
        self._unitview = None

        if self.store_controller.get_store():
            # We are too late for the initial 'store-loaded'
            self._on_store_loaded(self.store_controller)

    # ACCESSORS #
    def _get_checker_info(self):
        if not self._checker_info:
            from translate.filters import checks
            self._checker_info = {
                # XXX: Add other checkers below with a localisable string as key
                #      (used on the GUI) and a checker class as the value.
                None:    checks.StandardChecker,
                'openoffice': checks.OpenOfficeChecker,
                'mozilla':    checks.MozillaChecker,
                'drupal':     checks.DrupalChecker,
                'gnome':      checks.GnomeChecker,
                'kde':        checks.KdeChecker,
            }
        return self._checker_info
    checker_info = property(_get_checker_info)

    def _get_projview(self):
        from virtaal.views.checksprojview import ChecksProjectView
        if self._projview is None:
            self._projview = ChecksProjectView(self)
            self._projview.show()
        return self._projview
    projview = property(_get_projview)

    def _get_unitview(self):
        from virtaal.views.checksunitview import ChecksUnitView
        if self._unitview is None:
            self._unitview = ChecksUnitView(self)
            self._unitview.show()
        return self._unitview
    unitview = property(_get_unitview)

    def get_checker(self):
        return self._checker

    def set_checker_by_name(self, name):
        self.set_checker_by_code(self._checker_name_to_code.get(name, None))

    def set_checker_by_code(self, code):
        target_lang = self.main_controller.lang_controller.target_lang.code
        if not target_lang:
            target_lang = None
        self._checker = self.checker_info.get(code, self.checker_info[None])()
        self._checker.config.updatetargetlanguage(target_lang)

        self.emit('checker-set', code)
        self.projview.set_checker_name(self._checker_code_to_name.get(code, self._checker_code_to_name[None]))
        self.code = code
        if self.main_controller.unit_controller.current_unit:
            self.check_unit(self.main_controller.unit_controller.current_unit)


    # METHODS #
    def check_unit(self, unit):
        checker = self.get_checker()
        if not checker:
            logging.debug('No checker instantiated :(')
            return
        self.last_failures = checker.run_filters(unit)
        if self.last_failures:
            logging.debug('Failures: %s' % (self.last_failures))
        self.unitview.update(self.last_failures)
        self.emit('unit-checked', unit, checker, self.last_failures)
        return self.last_failures

    def _check_timer_expired(self, unit):
        self._check_timer_active = False
        if unit is not self.last_unit:
            return
        self.check_unit(unit)

    def _start_check_timer(self):
        if self._check_timer_active:
            return
        if not self.last_unit:
            # haven't changed units yet, probably strange timing issue
            return
        self._check_timer_active = True
        timeout_add(self.CHECK_TIMEOUT, self._check_timer_expired, self.last_unit)

    def get_check_name(self, check):
        """Return the human readable form of the given check name."""
        name = check_names.get(check, None)
        if not name and check.startswith('check-'):
            check = check[len('check-'):]
            name = check_names.get(check, None)
        if not name:
            name = check
        return name


    # EVENT HANDLERS #
    def _on_controller_registered(self, main_controller, controller):
        if controller is main_controller.lang_controller:
            controller.connect('target-lang-changed', self._on_target_lang_changed)

    def _on_cursor_changed(self, cursor):
        self.last_unit = cursor.deref()
        self.check_unit(self.last_unit)

    def _on_target_lang_changed(self, lang_controller, langcode):
        current_checker = self.get_checker()
        if current_checker:
           current_checker.config.updatetargetlanguage(langcode)
           self.emit('checker-set', self.code)
           if self.last_unit:
               self.check_unit(self.last_unit)

    def _on_store_loaded(self, store_controller):
        self.set_checker_by_code(store_controller.store._trans_store.getprojectstyle())
        if self._cursor_connection:
            widget, connect_id = self._cursor_connection
            widget.disconnect(connect_id)
        self._cursor_connection = (
            store_controller.cursor,
            store_controller.cursor.connect('cursor-changed', self._on_cursor_changed)
        )
        self._on_cursor_changed(store_controller.cursor)

    def _on_unit_modified(self, unit_controller, unit):
        self._start_check_timer()

########NEW FILE########
__FILENAME__ = cursor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
from gobject import SIGNAL_RUN_FIRST
from bisect import bisect_left

from virtaal.common import GObjectWrapper


class Cursor(GObjectWrapper):
    """
    Manages the current position in an arbitrary model.

    NOTE: Assigning to C{self.pos} causes the "cursor-changed" signal
    to be emitted.
    """

    __gtype_name__ = "Cursor"

    __gsignals__ = {
        "cursor-changed": (SIGNAL_RUN_FIRST, None, ()),
        "cursor-empty":   (SIGNAL_RUN_FIRST, None, ()),
    }


    # INITIALIZERS #
    def __init__(self, model, indices, circular=True):
        """Constructor.
            @type  model: anything
            @param model: The model (usually a collection) to which the cursor is applicable.
            @type  indices: ordered collection
            @param indices: The valid values for C{self.index}."""
        GObjectWrapper.__init__(self)

        self.model = model
        self._indices = indices
        self.circular = circular

        self._pos = 0


    # ACCESSORS #
    def _get_pos(self):
        return self._pos
    def _set_pos(self, value):
        if value == self._pos:
            return # Don't unnecessarily move the cursor (or emit 'cursor-changed', more specifically)
        if value >= len(self.indices):
            self._pos = len(self.indices) - 1
        elif value < 0:
            self._pos = 0
        else:
            self._pos = value
        self.emit('cursor-changed')
    pos = property(_get_pos, _set_pos)

    def _get_index(self):
        l_indices = len(self._indices)
        if l_indices < 1:
            return -1
        if self.pos >= l_indices:
            return l_indices - 1
        return self._indices[self.pos]
    def _set_index(self, index):
        """Move the cursor to the cursor to the position specified by C{index}.
            @type  index: int
            @param index: The index that the cursor should point to."""
        self.pos = bisect_left(self._indices, index)
    index = property(_get_index, _set_index)

    def _get_indices(self):
        return self._indices
    def _set_indices(self, value):
        oldindex = self.index
        oldpos = self.pos

        self._indices = list(value)

        self.index = oldindex
        if len(self._indices) == 0:
            self.emit('cursor-empty')
        if oldpos == self.pos and oldindex != self.index:
            self.emit('cursor-changed')
    indices = property(_get_indices, _set_indices)

    # METHODS #
    def deref(self):
        """Dereference the cursor to the item in the model that the cursor is
            currently pointing to.

            @returns: C{self.model[self.index]}, or C{None} if any error occurred."""
        try:
            return self.model[self.index]
        except Exception, exc:
            logging.debug('Unable to dereference cursor:\n%s' % (exc))
            return None

    def force_index(self, index):
        """Force the cursor to move to the given index, even if it is not in the
            C{self.indices} list.
            This should only be used when absolutely necessary. Be prepared to
            deal with the consequences of using this method."""
        oldindex = self.index
        if index not in self.indices:
            newindices = list(self.indices)
            insert_pos = bisect_left(self.indices, index)
            if insert_pos == len(self.indices):
                newindices.append(index)
            else:
                newindices.insert(insert_pos, index)
            self.indices = newindices
        self.index = index

    def move(self, offset):
        """Move the cursor C{offset} positions down.
            The cursor will wrap around to the beginning if C{circular=True}
            was given when the cursor was created."""
        # FIXME: Possibly contains off-by-one bug(s)
        if 0 <= self.pos + offset < len(self._indices):
            self.pos += offset
        elif self.circular:
            if self.pos + offset >= 0:
                self.pos = self.pos + offset - len(self._indices)
            elif self.pos + offset < 0:
                self.pos = self.pos + offset + len(self._indices)
        else:
            raise IndexError()

########NEW FILE########
__FILENAME__ = langcontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os
from gobject import SIGNAL_RUN_FIRST

from virtaal.common import GObjectWrapper, pan_app
from virtaal.models.langmodel import LanguageModel

from basecontroller import BaseController


class LanguageController(BaseController):
    """
    The logic behind language management in Virtaal.
    """

    __gtype_name__ = 'LanguageController'
    __gsignals__ = {
        'source-lang-changed': (SIGNAL_RUN_FIRST, None, (str,)),
        'target-lang-changed': (SIGNAL_RUN_FIRST, None, (str,)),
    }

    NUM_RECENT = 5
    """The number of recent language pairs to save/display."""

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.lang_controller = self
        self.lang_identifier = None
        self.new_langs = []
        self._init_langs()
        self.recent_pairs = self._load_recent()

        self.main_controller.store_controller.connect('store-loaded', self._on_store_loaded)
        self.main_controller.connect('quit', self._on_quit)
        self.connect('source-lang-changed', self._on_lang_changed)
        self.connect('target-lang-changed', self._on_lang_changed)

        self.view = None

    def _init_langs(self):
        try:
            self._source_lang = LanguageModel(pan_app.settings.language['sourcelang'])
        except Exception:
            self._source_lang = None

        try:
            self._target_lang = LanguageModel(pan_app.settings.language['targetlang'])
        except Exception:
            self._target_lang = None

        # Load previously-saved (new) languages
        filename = os.path.join(pan_app.get_config_dir(), 'langs.ini')
        if os.path.isfile(filename):
            languages = pan_app.load_config(filename)
            for code in languages:
                languages[code] = (
                    languages[code]['name'],
                    int(languages[code]['nplurals']),
                    languages[code]['plural']
                )
            LanguageModel.languages.update(languages)


    # ACCESSORS #
    def _get_source_lang(self):
        return self._source_lang
    def _set_source_lang(self, lang):
        if isinstance(lang, basestring):
            lang = LanguageModel(lang)
        if not lang or lang == self._source_lang:
            return
        self._source_lang = lang
        self.emit('source-lang-changed', self._source_lang.code)
    source_lang = property(_get_source_lang, _set_source_lang)

    def _get_target_lang(self):
        return self._target_lang
    def _set_target_lang(self, lang):
        if isinstance(lang, basestring):
            lang = LanguageModel(lang)
        if not lang or lang == self._target_lang:
            return
        self._target_lang = lang
        self.emit('target-lang-changed', self._target_lang.code)
    target_lang = property(_get_target_lang, _set_target_lang)

    def set_language_pair(self, srclang, tgtlang):
        if isinstance(srclang, basestring):
            srclang = LanguageModel(srclang)
        if isinstance(tgtlang, basestring):
            tgtlang = LanguageModel(tgtlang)

        pair = (srclang, tgtlang)
        if pair in self.recent_pairs:
            self.recent_pairs.remove(pair)

        self.recent_pairs.insert(0, pair)
        self.recent_pairs = self.recent_pairs[:self.NUM_RECENT]

        self.source_lang = srclang
        self.target_lang = tgtlang
        self.view.update_recent_pairs()
        if self.source_lang == self.target_lang:
            self.view.notify_same_langs()


    # METHODS #
    def get_detected_langs(self):
        store = self.main_controller.store_controller.store
        if not store:
            return None

        if not self.lang_identifier:
            from translate.lang.identify import LanguageIdentifier
            self.lang_identifier = LanguageIdentifier()
        srccode = self.lang_identifier.identify_source_lang(store.get_units())
        tgtcode = self.lang_identifier.identify_target_lang(store.get_units())
        srclang = tgtlang = None
        if srccode:
            srclang = LanguageModel(srccode)
        if tgtcode:
            tgtlang = LanguageModel(tgtcode)

        return srclang, tgtlang

    def _load_recent(self):
        code_pairs = pan_app.settings.language['recentlangs'].split('|')
        codes = [pair.split(',') for pair in code_pairs]
        if codes == [['']]:
            return []

        recent_pairs = []
        for srccode, tgtcode in codes:
            srclang = LanguageModel(srccode)
            tgtlang = LanguageModel(tgtcode)
            recent_pairs.append((srclang, tgtlang))

        return recent_pairs

    def save_recent(self):
        pairs = [','.join([src.code, tgt.code]) for (src, tgt) in self.recent_pairs]
        recent = '|'.join(pairs)
        pan_app.settings.language['recentlangs'] = recent


    # EVENT HANDLERS #
    def _on_lang_changed(self, sender, code):
        self.save_recent()
        if self.source_lang == self.target_lang:
            self.view.notify_same_langs()
        else:
            self.view.notify_diff_langs()

    def _on_quit(self, main_controller):
        pan_app.settings.language['sourcelang'] = self.source_lang.code
        pan_app.settings.language['targetlang'] = self.target_lang.code

        if not self.new_langs:
            return

        langs = {}
        filename = os.path.join(pan_app.get_config_dir(), 'langs.ini')
        if os.path.isfile(filename):
            langs = pan_app.load_config(filename)

        newlangdict = {}
        for code in self.new_langs:
            newlangdict[code] = {}
            newlangdict[code]['name'] = LanguageModel.languages[code][0]
            newlangdict[code]['nplurals'] = LanguageModel.languages[code][1]
            newlangdict[code]['plural'] = LanguageModel.languages[code][2]
        langs.update(newlangdict)

        pan_app.save_config(filename, langs)

    def _on_store_loaded(self, store_controller):
        if not self.view:
            from virtaal.views.langview import LanguageView
            self.view = LanguageView(self)
            self.view.show()
        srclang = store_controller.store.get_source_language() or self.source_lang.code
        tgtlang = store_controller.store.get_target_language() or self.target_lang.code
        self.set_language_pair(srclang, tgtlang)
        self.target_lang.nplurals = self.target_lang.nplurals or store_controller.get_nplurals()

########NEW FILE########
__FILENAME__ = maincontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
from gobject import SIGNAL_RUN_FIRST
import os

from virtaal.common import GObjectWrapper, pan_app
from virtaal.views.mainview import MainView

from basecontroller import BaseController


class MainController(BaseController):
    """The main controller that initializes the others and contains the main
        program loop."""

    __gtype_name__ = 'MainController'
    __gsignals__ = {
        'controller-registered': (SIGNAL_RUN_FIRST, None, (object,)),
        'quit':                  (SIGNAL_RUN_FIRST, None, tuple()),
    }

    # INITIALIZERS #
    def __init__(self):
        GObjectWrapper.__init__(self)
        self._force_saveas = False

        self._checks_controller = None
        self._lang_controller = None
        self._mode_controller = None
        self._placeables_controller = None
        self._plugin_controller = None
        self._store_controller = None
        self._undo_controller = None
        self._unit_controller = None
        self._welcomescreen_controller = None
        self.view = MainView(self)

    def load_plugins(self):
        # Helper method to be called from virtaal.main
        if self.plugin_controller:
            self.plugin_controller.load_plugins()

    def destroy(self):
        self.store_controller.destroy()


    # ACCESSORS #
    def get_store(self):
        """Returns the store model of the current open translation store or C{None}."""
        return self.store_controller.get_store()

    def get_store_filename(self):
        """C{self.store_controller.get_store_filename()}"""
        return self.store_controller.get_store_filename()

    def get_translator_name(self):
        name = pan_app.settings.translator["name"]
        if not name:
            return self.show_input(
                title=_('Header information'),
                msg=_('Please enter your name')
            )
        return name

    def get_translator_email(self):
        email = pan_app.settings.translator["email"]
        if not email:
            return self.show_input(
                title=_('Header information'),
                msg=_('Please enter your e-mail address')
            )
        return email

    def get_translator_team(self):
        team = pan_app.settings.translator["team"]
        if not team:
            return self.show_input(
                title=_('Header information'),
                msg=_("Please enter your team's information")
            )
        return team

    def set_saveable(self, value):
        self.view.set_saveable(value)

    def set_force_saveas(self, value):
        self._force_saveas = value

    def get_force_saveas(self):
        return self._force_saveas

    def _get_checks_controller(self):
        return self._checks_controller
    def _set_checks_controller(self, value):
        self._checks_controller = value
        self.emit('controller-registered', self._checks_controller)
    checks_controller = property(_get_checks_controller, _set_checks_controller)

    def _get_lang_controller(self):
        return self._lang_controller
    def _set_lang_controller(self, value):
        self._lang_controller = value
        self.emit('controller-registered', self._lang_controller)
    lang_controller = property(_get_lang_controller, _set_lang_controller)

    def _get_mode_controller(self):
        return self._mode_controller
    def _set_mode_controller(self, value):
        self._mode_controller = value
        self.emit('controller-registered', self._mode_controller)
    mode_controller = property(_get_mode_controller, _set_mode_controller)

    def _get_placeables_controller(self):
        return self._placeables_controller
    def _set_placeables_controller(self, value):
        self._placeables_controller = value
        self.emit('controller-registered', self._placeables_controller)
    placeables_controller = property(_get_placeables_controller, _set_placeables_controller)

    def _get_plugin_controller(self):
        return self._plugin_controller
    def _set_plugin_controller(self, value):
        self._plugin_controller = value
        self.emit('controller-registered', self._plugin_controller)
    plugin_controller = property(_get_plugin_controller, _set_plugin_controller)

    def _get_store_controller(self):
        return self._store_controller
    def _set_store_controller(self, value):
        self._store_controller = value
        self.emit('controller-registered', self._store_controller)
    store_controller = property(_get_store_controller, _set_store_controller)

    def _get_undo_controller(self):
        return self._undo_controller
    def _set_undo_controller(self, value):
        self._undo_controller = value
        self.emit('controller-registered', self._undo_controller)
    undo_controller = property(_get_undo_controller, _set_undo_controller)

    def _get_unit_controller(self):
        return self._unit_controller
    def _set_unit_controller(self, value):
        self._unit_controller = value
        self.emit('controller-registered', self._unit_controller)
    unit_controller = property(_get_unit_controller, _set_unit_controller)

    def _get_welcomescreen_controller(self):
        return self._welcomescreen_controller
    def _set_welcomescreen_controller(self, value):
        self._welcomescreen_controller = value
        self.emit('controller-registered', self._welcomescreen_controller)
    welcomescreen_controller = property(_get_welcomescreen_controller, _set_welcomescreen_controller)


    # METHODS #
    def open_file(self, filename=None, uri='', forget_dir=False):
        """Open the file given by C{filename}.
            @returns: The filename opened, or C{None} if an error has occurred."""
        # We might be a bit early for some of the other controllers, so let's
        # make it our problem and ensure the last ones are in the main
        # controller.
        while not self.placeables_controller:
            gtk.main_iteration(False)
        if filename is None:
            return self.view.open_file()
        if self.store_controller.is_modified():
            response = self.view.show_save_confirm_dialog()
            if response == 'save':
                if not self.save_file():
                    return False
            elif response == 'cancel':
                return False
            # Unnecessary to test for 'discard'

        if filename.startswith('file://'):
            if os.name == "nt":
                filename = filename[len('file:///'):]
            else:
                filename = filename[len('file://'):]

        if self.store_controller.store and self.store_controller.store.get_filename() == filename:
            promptmsg = _('You selected the currently open file for opening. Do you want to reload the file?')
            if not self.show_prompt(msg=promptmsg):
                return False

        try:
            self.store_controller.open_file(filename, uri, forget_dir=forget_dir)
            self.mode_controller.refresh_mode()
            return True
        except Exception, exc:
            import logging
            logging.exception('MainController.open_file(filename="%s", uri="%s")' % (filename, uri))
            self.show_error(
                filename + ":\n" + _("Could not open file.\n\n%(error_message)s\n\nTry opening a different file.") % {'error_message': str(exc)}
            )
            return False

    def open_tutorial(self):
        # Save on the disk a localized version of the tutorial using the
        # current locale.
        from virtaal.support.tutorial import create_localized_tutorial
        filename = create_localized_tutorial()

        # Open the file just created on the fly.
        self.open_file(filename, forget_dir=True)
        import shutil
        import os.path
        shutil.rmtree(os.path.dirname(filename))


    def save_file(self, filename=None, force_saveas=False):
        # we return True on success
        if not filename and (self.get_force_saveas() or force_saveas):
            filename = self.store_controller.get_bundle_filename()
            if filename is None:
                filename = self.get_store_filename() or ''
            filename = self.view.show_save_dialog(current_filename=filename, title=_("Save"))
            if not filename:
                return False

        if self._do_save_file(filename):
            if self.get_force_saveas():
                self.set_force_saveas(False)
            return True
        else:
            return False

    def _do_save_file(self, filename=None):
        """Delegate saving to the store_controller, but do error handling.

        Return True on success, False otherwise."""
        try:
            self.store_controller.save_file(filename)
            return True
        except IOError, exc:
            self.show_error(
                _("Could not save file.\n\n%(error_message)s\n\nTry saving to a different location.") % {'error_message': str(exc)}
            )
        except Exception, exc:
            import logging
            logging.exception('MainController.save_file(filename="%s")' % (filename))
            self.show_error(
                _("Could not save file.\n\n%(error_message)s" % {'error_message': str(exc)})
            )
        return False

    def binary_export(self):
        #let's try to suggest a filename:
        filename = self.store_controller.get_bundle_filename()
        if filename is None:
            filename = self.get_store_filename() or ''
        if not (filename.endswith('.po') or filename.endswith('.po.bz2') or filename.endswith('.po.gz')):
            self.show_error(
                _("Can only export Gettext PO files")
            )
            return False

        if filename.endswith('.po'):
            #TODO: do something better, especially for files like fr.po and gnome-shell.po.master.fr.po
            filename = filename[:-3] + '.mo'
        else:
            filename = 'messages.mo'
        filename = self.view.show_save_dialog(current_filename=filename, title=_("Export"))
        if not filename:
            return False
        try:
            self.store_controller.binary_export(filename)
            return True
        except IOError, exc:
            self.show_error(
                _("Could not export file.\n\n%(error_message)s\n\nTry saving to a different location.") % {'error_message': str(exc)}
            )
        except Exception, exc:
            import logging
            logging.exception('MainController.binary_export(filename="%s")' % (filename))
            self.show_error(
                _("Could not export file.\n\n%(error_message)s" % {'error_message': str(exc)})
            )
        return False

    def close_file(self):
        if self.store_controller.is_modified():
            response = self.view.show_save_confirm_dialog()
            if response == 'save':
                if not self.save_file():
                    return False
            elif response == 'cancel':
                return False
            # Unnecessary to test for 'discard'
        self.store_controller.close_file()

    def revert_file(self, filename=None):
        confirm = self.show_prompt(_("Reload File"), _("Reload file from last saved copy and lose all changes?"))
        if not confirm:
            return

        try:
            self.store_controller.revert_file()
            self.mode_controller.refresh_mode()
        except Exception, exc:
            import logging
            logging.exception('MainController.revert_file(filename="%s")' % (filename))
            self.show_error(
                _("Could not open file.\n\n%(error_message)s\n\nTry opening a different file.") % {'error_message': str(exc)}
            )

    def update_file(self, filename, uri=''):
        """Update the current file using the file given by C{filename} as template.
            @returns: The filename opened, or C{None} if an error has occurred."""
        if self.store_controller.is_modified():
            response = self.view.show_save_confirm_dialog()
            if response == 'save':
                if not self.save_file():
                    return False
            elif response == 'cancel':
                return False
            # Unnecessary to test for 'discard'

        if self.store_controller.store and self.store_controller.store.get_filename() == filename:
            promptmsg = _('You selected the currently open file for opening. Do you want to reload the file?')
            if not self.show_prompt(msg=promptmsg):
                return False

        try:
            self.store_controller.update_file(filename, uri)
            self.mode_controller.refresh_mode()
            return True
        except Exception, exc:
            import logging
            logging.exception('MainController.update_file(filename="%s", uri="%s")' % (filename, uri))
            self.show_error(
                _("Could not open file.\n\n%(error_message)s\n\nTry opening a different file.") % {'error_message': str(exc)}
            )
            return False

    def select_unit(self, unit, force=False):
        """Select the specified unit in the store view."""
        self.store_controller.select_unit(unit, force)

    def show_error(self, msg):
        """Shortcut for C{self.view.show_error_dialog()}"""
        return self.view.show_error_dialog(message=msg)

    def show_input(self, title='', msg=''):
        """Shortcut for C{self.view.show_input_dialog()}"""
        return self.view.show_input_dialog(title=title, message=msg)

    def show_prompt(self, title='', msg=''):
        """Shortcut for C{self.view.show_prompt_dialog()}"""
        return self.view.show_prompt_dialog(title=title, message=msg)

    def show_info(self, title='', msg=''):
        """Shortcut for C{self.view.show_info_dialog()}"""
        return self.view.show_info_dialog(title=title, message=msg)

    def quit(self, force=False):
        if self.store_controller.is_modified() and not force:
            response = self.view.show_save_confirm_dialog()
            if response == 'save':
                if not self.save_file():
                    return False
            elif response != 'discard':
                return True

        self.view.hide()
        if self.plugin_controller:
            self.plugin_controller.shutdown()
        self.emit('quit')
        self.view.quit()
        return False

    def run(self):
        self.view.show()

########NEW FILE########
__FILENAME__ = modecontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject

from virtaal.common import GObjectWrapper

from basecontroller import BaseController


class ModeController(BaseController):
    """
    Contains logic for switching and managing unit selection modes.

    In the context of modes, models always represent a specific mode. So it's
    not strictly a data model (as it contains its own logic), but it is the
    standard type of object that is manipulated and handled by this controller
    and C{ModeView} objects.
    """

    __gtype_name__ = 'ModeController'
    __gsignals__ = {
        'mode-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }
    default_mode_name = 'Default'

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.mode_controller = self

        self._init_modes()
        from virtaal.views.modeview  import ModeView
        self.view = ModeView(self)
        self.view.connect('mode-selected', self._on_mode_selected)

        self.current_mode = None
        self.view.select_mode(self.modenames[self.default_mode_name])

        self.main_controller.store_controller.connect('store-closed', self._on_store_closed)

    def _init_modes(self):
        self.modes = {}
        self.modenames = {}

        from virtaal.modes  import modeclasses
        for modeclass in modeclasses:
            newmode = modeclass(self)
            self.modes[newmode.name] = newmode
            self.modenames[newmode.name] = newmode.display_name


    # ACCESSORS #
    def get_mode_by_display_name(self, displayname):
        candidates = [mode for name, mode in self.modes.items() if mode.display_name == displayname]
        if candidates:
            return candidates[0]


    # METHODS #
    def refresh_mode(self):
        if not self.current_mode:
            self.select_default_mode()
        else:
            self.select_mode(self.current_mode)

    def select_default_mode(self):
        self.select_mode_by_name(self.default_mode_name)

    def select_mode_by_display_name(self, displayname):
        self.select_mode(self.get_mode_by_display_name(displayname))

    def select_mode_by_name(self, name):
        self.select_mode(self.modes[name])

    def select_mode(self, mode):
        if self.current_mode:
            self.view.remove_mode_widgets(self.current_mode.widgets)
            self.current_mode.unselected()

        self.current_mode = mode
        self._ignore_mode_change = True
        self.view.select_mode(self.modenames[mode.name])
        self._ignore_mode_change = False
        self.view.show()
        self.current_mode.selected()
        import logging
        logging.info('Mode selected: %s' % (self.current_mode.name))
        self.emit('mode-selected', self.current_mode)

    # EVENT HANDLERS #
    def _on_mode_selected(self, _modeview, modename):
        if not getattr(self, '_ignore_mode_change', True):
            self.select_mode(self.get_mode_by_display_name(modename))

    def _on_store_closed(self, store_controller):
        self.select_default_mode()
        self.view.hide()

########NEW FILE########
__FILENAME__ = placeablescontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
from translate.storage.placeables import general, StringElem, parse as parse_placeables

from virtaal.common import pan_app, GObjectWrapper
from virtaal.views import placeablesguiinfo

from basecontroller import BaseController


class PlaceablesController(BaseController):
    """Basic controller for placeable-related logic."""

    __gtype_name__ = 'PlaceablesController'
    __gsignals__ = {
        'parsers-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, tuple()),
    }

    parsers = []
    """The list of parsers that should be used by the main placeables C{parse()}
    function.
    @see translate.storage.placeables.parse"""

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.placeables_controller = self
        self._init_parsers()
        self._init_parser_descriptions()
        self._init_notarget_list()

        self.main_controller.view.main_window.connect('style-set', self._on_style_set)
        self._on_style_set(self.main_controller.view.main_window, None)
        self.main_controller.connect('quit', self._on_quit)

    def _init_notarget_list(self):
        self.non_target_placeables = [
            general.AltAttrPlaceable,
            general.CamelCasePlaceable,
            general.CapsPlaceable,
            general.EmailPlaceable,
            general.FilePlaceable,
            general.PunctuationPlaceable,
            general.UrlPlaceable,
        ]

    def _init_parsers(self):
        disabled = [name for name, state in pan_app.settings.placeable_state.items() if state.lower() == 'disabled']

        self.parsers = []
        for parser in general.parsers:
            classname = parser.im_self.__name__.lower()
            if classname in disabled:
                continue
            self.add_parsers(parser)

    def _init_parser_descriptions(self):
        self.parser_info = {}

        # Test for presence of parser classes by hand
        self.parser_info[general.CamelCasePlaceable.parse] = (
            #l10n: See http://en.wikipedia.org/wiki/CamelCase
            _('CamelCase'),
            _('Words with internal capitalization, such as some brand names and WikiWords')
        )
        self.parser_info[general.CapsPlaceable.parse] = (
            _('Capitals'),
            #l10n: this refers to "UPPERCASE" / "CAPITAL" letters
            _('Words containing uppercase letters only')
        )
        self.parser_info[general.OptionPlaceable.parse] = (
            _('Command Line Options'),
            _('Application command line options, such as --help, -h and -I')
        )
        self.parser_info[general.EmailPlaceable.parse] = (
            _('E-mail'),
            _('E-mail addresses')
        )
        self.parser_info[general.FilePlaceable.parse] = (
            _('File Names'),
            _('Paths referring to file locations')
        )
        self.parser_info[general.FormattingPlaceable.parse] = (
            _('Placeholders (printf)'),
            _('Placeholders used in "printf" strings')
        )
        self.parser_info[general.PythonFormattingPlaceable.parse] = (
            _('Placeholders (Python)'),
            _('Placeholders in Python strings')
        )
        self.parser_info[general.JavaMessageFormatPlaceable.parse] = (
            _('Placeholders (Java)'),
            _('Placeholders in Java strings')
        )
        self.parser_info[general.QtFormattingPlaceable.parse] = (
            _('Placeholders (Qt)'),
            _('Placeholders in Qt strings')
        )
        self.parser_info[general.NumberPlaceable.parse] = (
            _('Numbers'),
            #l10n: 'decimal fractions' refer to numbers like 0.2 or 499,99
            _('Integer numbers and decimal fractions')
        )
        self.parser_info[general.PunctuationPlaceable.parse] = (
            _('Punctuation'),
            _('Symbols and less frequently used punctuation marks')
        )
        self.parser_info[general.UrlPlaceable.parse] = (
            _('URLs'),
            _('URLs, hostnames and IP addresses')
        )
        self.parser_info[general.XMLEntityPlaceable.parse] = (
            #l10n: see http://en.wikipedia.org/wiki/Character_entity_reference
            _('XML Entities'),
            _('Entity references, such as &amp; and &#169;')
        )
        self.parser_info[general.XMLTagPlaceable.parse] = (
            _('XML Tags'),
            _('XML tags, such as <b> and </i>')
        )
        # This code should eventually be used to add the SpacesPlaceable, but
        # it is not working well yet. We add the strings for translation so
        # that we won't need to break the string freeze later when it works.
#        self.parser_info[general.AltAttrPlaceable.parse] = (
#            _('"alt" Attributes'),
#            _('Placeable for "alt" attributes (as found in HTML)')
#        )
#        self.parser_info[general.SpacesPlaceable.parse] = (
#            _('Spaces'),
#            _('Double spaces and spaces in unexpected positions')
#        )

        _('Spaces'),
        _('Double spaces and spaces in unexpected positions')
        _('"alt" Attributes'),
        _('Placeable for "alt" attributes (as found in HTML)')
        _('Placeholders (Drupal)'),
        _('Placeholders in Drupal strings')


    # METHODS #
    def add_parsers(self, *newparsers):
        """Add the specified parsers to the list of placeables parser functions."""
        if [f for f in newparsers if not callable(f)]:
            raise TypeError('newparsers may only contain callable objects.')

        sortedparsers = []

        # First add parsers from general.parsers in order
        for parser in general.parsers:
            if parser in (self.parsers + list(newparsers)):
                sortedparsers.append(parser)
        # Add parsers not in general.parsers
        for parser in newparsers:
            if parser not in general.parsers:
                sortedparsers.append(parser)

        self.parsers = sortedparsers
        self.emit('parsers-changed')

    def apply_parsers(self, elems, parsers=None):
        """Apply all selected placeable parsers to the list of string elements
            given.

            @param elems: The list of C{StringElem}s to apply the parsers to."""
        if not isinstance(elems, list) and isinstance(elems, StringElem):
            elems = [elems]

        if parsers is None:
            parsers = self.parsers

        for elem in elems:
            elem = elem
            parsed = parse_placeables(elem, parsers)
            if isinstance(elem, (str, unicode)) and parsed != StringElem(elem):
                parent = elem.get_parent_elem(elem)
                if parent is not None:
                    parent.sub[parent.sub.index(elem)] = StringElem(parsed)
        return elems

    def get_parsers_for_textbox(self, textbox):
        """Get the parsers that should be applied to the given text box.
            This is intended for use by C{TextBox} to supply it with appropriate
            parsers, based on whether the text box is used for source- or target
            text."""
        if textbox in self.main_controller.unit_controller.view.targets:
            tgt_parsers = []
            return [p for p in self.parsers if p.im_self not in self.non_target_placeables]
        return self.parsers

    def get_gui_info(self, placeable):
        """Get an appropriate C{StringElemGUI} or sub-class instance based on
        the type of C{placeable}. The mapping between placeables classes and
        GUI info classes is defined in
        L{virtaal.views.placeablesguiinfo.element_gui_map}."""
        if not isinstance(placeable, StringElem):
            raise ValueError('placeable must be a StringElem.')
        for plac_type, info_type in placeablesguiinfo.element_gui_map:
            if isinstance(placeable, plac_type):
                return info_type
        return placeablesguiinfo.StringElemGUI

    def remove_parsers(self, *parsers):
        changed = False
        for p in parsers:
            if p in self.parsers:
                self.parsers.remove(p)
                changed = True
        if changed:
            self.emit('parsers-changed')


    # EVENT HANDLERS #
    def _on_style_set(self, widget, prev_style):
        placeablesguiinfo.update_style(widget)

        # Refresh text boxes' colours
        unitview = self.main_controller.unit_controller.view
        for textbox in unitview.sources + unitview.targets:
            if textbox.props.visible:
                textbox.refresh()

    def _on_quit(self, main_ctrlr):
        for parser in general.parsers:
            classname = parser.im_self.__name__
            enabled = parser in self.parsers
            if classname in pan_app.settings.placeable_state or not enabled:
                pan_app.settings.placeable_state[classname.lower()] = enabled and 'enabled' or 'disabled'

########NEW FILE########
__FILENAME__ = plugincontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import os
import sys
from gobject import SIGNAL_RUN_FIRST, TYPE_PYOBJECT, idle_add

from virtaal.common import pan_app, GObjectWrapper

from basecontroller import BaseController
from baseplugin import PluginUnsupported, BasePlugin


if os.name == 'nt':
    sys.path.insert(0, pan_app.main_dir.encode(sys.getfilesystemencoding()))
if 'RESOURCEPATH' in os.environ:
    sys.path.insert(0, os.path.join(os.environ['RESOURCEPATH']))

# The following line allows us to import user plug-ins from ~/.virtaal/virtaal_plugins
# (see PluginController.PLUGIN_MODULES)
sys.path.insert(0, pan_app.get_config_dir().encode(sys.getfilesystemencoding()))

class PluginController(BaseController):
    """This controller is responsible for all plug-in management."""

    __gtype_name__ = 'PluginController'
    __gsignals__ = {
        'plugin-enabled':  (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'plugin-disabled': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
    }

    # The following class variables are set for the main plug-in controller.
    # To use this class to manage any other plug-ins, these will (most likely) have to be changed.
    PLUGIN_CLASSNAME = 'Plugin'
    """The name of the class that will be instantiated from the plug-in module."""
    PLUGIN_CLASS_INFO_ATTRIBS = ['description', 'display_name', 'version']
    """Attributes of the plug-in class that contain info about it. Should contain PLUGIN_NAME_ATTRIB."""
    PLUGIN_DIRS = [
        os.path.join(pan_app.get_config_dir(), u'virtaal_plugins'),
        os.path.join(os.path.dirname(__file__).decode(sys.getfilesystemencoding()), u'..', u'plugins')
    ]
    """The directories to search for plug-in names."""
    PLUGIN_INTERFACE = BasePlugin
    """The interface class that the plug-in class must inherit from."""
    PLUGIN_MODULES = ['virtaal_plugins', 'virtaal.plugins']
    """The module name to import the plugin from. This is prepended to the
        plug-in's name as found by C{_find_plugin_names()} and passed to
        C{__import__()}."""
    PLUGIN_NAME_ATTRIB = 'display_name'
    """The attribute of a plug-in that contains its name."""

    # INITIALIZERS #
    def __init__(self, controller, classname=None):
        GObjectWrapper.__init__(self)

        self.controller = controller
        if classname:
            self.PLUGIN_CLASSNAME = classname
        else:
            # controller is maincontroller
            controller.plugin_controller = self
        self.plugins       = {}
        self.pluginmodules = {}

        if os.name == 'nt':
            self.PLUGIN_DIRS.insert(0, os.path.join(pan_app.main_dir, u'virtaal_plugins'))
        if 'RESOURCEPATH' in os.environ:
            self.PLUGIN_DIRS.insert(0, os.path.join(os.environ['RESOURCEPATH'].decode(sys.getfilesystemencoding()), u'virtaal_plugins'))


    # METHODS #
    def disable_plugin(self, name):
        """Destroy the plug-in with the given name."""
        logging.debug('Disabling plugin: %s' % (name))

        if name in self.plugins:
            self.emit('plugin-disabled', self.plugins[name])
            self.plugins[name].destroy()
            del self.plugins[name]
        if name in self.pluginmodules:
            del self.pluginmodules[name]

    def enable_plugin(self, name):
        """Load the plug-in with the given name and instantiate it."""
        if name in self.plugins:
            return None

        try:
            plugin_class = self._get_plugin_class(name)
            try:
                self.plugins[name] = plugin_class(name, self.controller)
            except PluginUnsupported, pu:
                logging.info(pu.message)
                return None
            self.emit('plugin-enabled', self.plugins[name])
            logging.info('    - ' + getattr(self.plugins[name], self.PLUGIN_NAME_ATTRIB, name))
            return self.plugins[name]
        except Exception, e:
            # the name is unicode which can trigger encoding issues in the
            # logging module, so let's encode it now already
            logging.exception('Failed to load plugin "%s"\n%s' % (name.encode('utf-8'), e))

        return None

    def get_plugin_info(self, name):
        plugin_class = self._get_plugin_class(name)
        item = {}
        for attrib in self.PLUGIN_CLASS_INFO_ATTRIBS:
            item[attrib] = getattr(plugin_class, attrib, None)
        return item

    def load_plugins(self):
        """Load plugins from the "plugins" directory."""
        self.plugins       = {}
        self.pluginmodules = {}
        disabled_plugins = self.get_disabled_plugins()

        logging.info('Loading plug-ins:')
        for name in self._find_plugin_names():
            if name in disabled_plugins:
                continue
            # We use idle_add(), so that the UI will respond sooner
            idle_add(self.enable_plugin, name)
        logging.info('Queued all plugins for loading')

    def shutdown(self):
        """Disable all plug-ins."""
        for name in list(self.plugins.keys()):
            self.disable_plugin(name)

    def get_disabled_plugins(self):
        """Returns a list of names of plug-ins that are disabled in the
            configuration.

            This method should be replaced if an instance is not used for
            normal plug-ins."""
        return [plugin_name for (plugin_name, state) in pan_app.settings.plugin_state.items() if state.lower() == 'disabled']

    def _get_plugin_class(self, name):
        if name in self.plugins:
            return self.plugins[name].__class__

        module = None
        for plugin_module in self.PLUGIN_MODULES:
            # The following line makes sure that we have a valid module name to import from
            modulename = '.'.join([part for part in [plugin_module, name] if part])
            try:
                module = __import__(
                    modulename,
                    globals(),              # globals
                    [],                     # locals
                    [self.PLUGIN_CLASSNAME] # fromlist
                )
                break
            except ImportError, ie:
                if not ie.args[0].startswith('No module named') and pan_app.DEBUG:
                    logging.exception('from %s import %s' % (modulename, self.PLUGIN_CLASSNAME))

        if module is None:
            if pan_app.DEBUG:
                logging.exception('Could not find plug-in "%s"' % (name))
            raise Exception('Could not find plug-in "%s"' % (name))

        plugin_class = getattr(module, self.PLUGIN_CLASSNAME, None)
        if plugin_class is None:
            raise Exception('Plugin "%s" has no class called "%s"' % (name, self.PLUGIN_CLASSNAME))

        if self.PLUGIN_INTERFACE is not None:
            if not issubclass(plugin_class, self.PLUGIN_INTERFACE):
                raise Exception(
                    'Plugin "%s" contains a member called "%s" which is not a valid plug-in class.' % (name, self.PLUGIN_CLASSNAME)
                )

        self.pluginmodules[name] = module
        return plugin_class

    def _find_plugin_names(self):
        """Look in C{self.PLUGIN_DIRS} for importable Python modules.
            @note: Hidden files/directories are ignored.
            @note: If a plug-in is in a directory, it's C{self.PLUGIN_CLASSNAME}
                class should be exposed in the plug-in's __init__.py file.
            @returns: A list of module names, assumed to be plug-ins."""
        plugin_names = []

        for dir in self.PLUGIN_DIRS:
            if not os.path.isdir(dir):
                continue
            for name in os.listdir(dir):
                if name.startswith(u'.') or name.startswith(u'test_'):
                    continue
                fullpath = os.path.join(dir, name)
                if os.path.isdir(fullpath):
                    # XXX: The plug-in system assumes that a plug-in in a directory makes the Plugin class accessible via it's __init__.py
                    if pan_app.DEBUG or name[0] != u'_':
                        plugin_names.append(name)
                elif os.path.isfile(fullpath) and not name.startswith(u'__init__.py'):
                    if u'.py' not in name:
                        continue
                    plugname = u'.'.join(name.split(os.extsep)[:-1]) # Effectively removes extension, preserving other .'s in the name
                    if pan_app.DEBUG or plugname[0] != u'_':
                        plugin_names.append(plugname)

        plugin_names = list(set(plugin_names))
        #logging.debug('Found plugins: %s' % (', '.join(plugin_names)))
        return plugin_names

########NEW FILE########
__FILENAME__ = prefscontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from virtaal.common import GObjectWrapper, pan_app

from basecontroller import BaseController


class PreferencesController(BaseController):
    """Controller for driving the preferences GUI."""

    __gtype_name__ = 'PreferencesController'

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.placeables_controller = main_controller.placeables_controller
        self.plugin_controller = main_controller.plugin_controller
        from virtaal.views.prefsview import PreferencesView
        self.view = PreferencesView(self)
        self.view.connect('prefs-done', self._on_prefs_done)


    # METHODS #
    def set_placeable_enabled(self, parser, enabled):
        """Enable or disable a placeable with the given parser function."""
        if enabled:
            self.placeables_controller.add_parsers(parser)
        else:
            self.placeables_controller.remove_parsers(parser)
        self.update_config_placeables_state(parser=parser, disabled=not enabled)

    def set_plugin_enabled(self, plugin_name, enabled):
        """Enabled or disable a plug-in with the given name."""
        if enabled:
            self.plugin_controller.enable_plugin(plugin_name)
        else:
            self.plugin_controller.disable_plugin(plugin_name)
        self.update_config_plugin_state(plugin_name=plugin_name, disabled=not enabled)

    def update_config_placeables_state(self, parser, disabled):
        """Make sure that the placeable with the given name is enabled/disabled
            in the main configuration file."""
        classname = parser.im_self.__name__
        pan_app.settings.placeable_state[classname.lower()] = disabled and 'disabled' or 'enabled'

    def update_config_plugin_state(self, plugin_name, disabled):
        """Make sure that the plug-in with the given name is enabled/disabled
            in the main configuration file."""
        # A plug-in is considered "enabled" as long as
        # pan_app.settings.plugin_state[plugin_name].lower() != 'disabled',
        # even if not pan_app.settings.plugin_state.has_key(plugin_name).
        # This method is put here in stead of in PluginController, because it
        # is not safe to assume that the plug-ins being managed my any given
        # PluginController instance is enabled/disabled via the main virtaal.ini's
        # "[plugin_state]" section.
        pan_app.settings.plugin_state[plugin_name] = disabled and 'disabled' or 'enabled'
        self.update_prefs_gui_data()

    def update_prefs_gui_data(self):
        self._update_font_gui_data()
        self._update_placeables_gui_data()
        self._update_plugin_gui_data()
        self._update_user_gui_data()

    def _update_font_gui_data(self):
        self.view.font_data = {
            'source': pan_app.settings.language['sourcefont'],
            'target': pan_app.settings.language['targetfont'],
        }

    def _update_placeables_gui_data(self):
        items = []
        allparsers = self.placeables_controller.parser_info.items()
        allparsers.sort(key=lambda x: x[1][0])
        for parser, (name, desc) in allparsers:
            items.append({
                'name': name,
                'desc': desc,
                'enabled': parser in self.placeables_controller.parsers,
                'data': parser
            })
        self.view.placeables_data = items

    def _update_plugin_gui_data(self):
        plugin_items = []
        for found_plugin in self.plugin_controller._find_plugin_names():
            if found_plugin in self.plugin_controller.plugins:
                plugin = self.plugin_controller.plugins[found_plugin]
                plugin_items.append({
                    'name': plugin.display_name,
                    'desc': plugin.description,
                    'enabled': True,
                    'data': {'internal_name': found_plugin},
                    'config': plugin.configure_func
                })
            else:
                try:
                    info = self.plugin_controller.get_plugin_info(found_plugin)
                except Exception, e:
                    import logging
                    logging.debug('Problem getting information for plugin %s' % found_plugin)
                    continue

                plugin_items.append({
                    'name': info['display_name'],
                    'desc': info['description'],
                    'enabled': False,
                    'data': {'internal_name': found_plugin},
                    'config': None
                })
        # XXX: Note that we ignore plugin_controller.get_disabled_plugins(),
        # because we need to know which plug-ins are currently enabled/disabled
        # (not dependant on config).

        self.view.plugin_data = plugin_items

    def _update_user_gui_data(self):
        self.view.user_data = {
            'name':  pan_app.settings.translator['name'],
            'email': pan_app.settings.translator['email'],
            'team':  pan_app.settings.translator['team'],
        }


    # EVENT HANDLERS #
    def _on_prefs_done(self, view):
        # Update pan_app.settings with data from view
        font_data = view.font_data
        pan_app.settings.language['sourcefont'] = font_data['source']
        pan_app.settings.language['targetfont'] = font_data['target']
        # Reload unit to reload fonts
        self.main_controller.unit_controller.view.update_languages()

        user_data = view.user_data
        for key in ('name', 'email', 'team'):
            pan_app.settings.translator[key] = user_data[key]

########NEW FILE########
__FILENAME__ = propertiescontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


from virtaal.common import GObjectWrapper

from basecontroller import BaseController


class PropertiesController(BaseController):
    """Controller for driving the properties GUI."""

    __gtype_name__ = 'PropertiesController'

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        from virtaal.views.propertiesview import PropertiesView
        self.view = PropertiesView(self)


    # METHODS #

    def update_gui_data(self):
        import os.path
        filename = os.path.abspath(self.main_controller.store_controller.get_store().get_filename())
        if os.path.exists(filename):
            self.view.data['file_location'] = filename
            self.view.data['file_size'] = os.path.getsize(filename)
        self.view.data['file_type'] = self.main_controller.store_controller.get_store().get_store_type()
        self.view.stats = self.main_controller.store_controller.get_store().get_stats_totals()

    # EVENT HANDLERS #

########NEW FILE########
__FILENAME__ = storecontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
# Copyright 2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import os

from virtaal.common import GObjectWrapper
from basecontroller import BaseController


# TODO: Create an event that is emitted when a cursor is created
class StoreController(BaseController):
    """The controller for all store-level activities."""

    __gtype_name__ = 'StoreController'
    __gsignals__ = {
        'store-loaded': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'store-saved':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'store-closed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    }

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.store_controller = self
        self._unit_controller = None # This is set by UnitController itself when it is created

        self._archivetemp = None
        self.cursor = None
        self.handler_ids = {}
        self._modified = False
        self.project = None
        self.store = None
        self._tempfiles = []
        self._view = None

        self._controller_register_id = self.main_controller.connect('controller-registered', self._on_controller_registered)

    def destroy(self):
        if self.project:
            del self.project
        if self._archivetemp and os.path.isfile(self._archivetemp):
            os.unlink(self._archivetemp)
        for tempfile in self._tempfiles:
            try:
                os.unlink(tempfile)
            except Exception:
                pass


    # ACCESSORS #

    def _getview(self):
        if not self._view:
            from virtaal.views.storeview import StoreView
            self._view = StoreView(self)
        return self._view
    view = property(_getview)

    def get_nplurals(self, store=None):
        if not store:
            store = self.store
        return store and store.nplurals or 0

    def get_bundle_filename(self):
        """Returns the file name of the bundle archive, if we are working with one."""
        if self._archivetemp:
            return self._targetfname

        from translate.storage.bundleprojstore import BundleProjectStore
        if self.project and isinstance(self.project.store, BundleProjectStore):
            return self.project.store.zip.filename
        return None

    def get_store(self):
        return self.store

    def get_store_filename(self):
        """Returns a display-friendly string representing the current open
            store's file name. If a bundle is currently open, this method will
            return a file name in the format "bundle.zip:some_file.xlf"."""
        store = self.get_store()
        if not store:
            return ''
        filename = ''
        if self.project:
            from translate.storage.bundleprojstore import BundleProjectStore
            if isinstance(self.project.store, BundleProjectStore):
                # This should always be the case
                filename = self.project.store.zip.filename + ':'
                projfname = self.project.get_proj_filename(store.get_filename())
                _dir, projfname = os.path.split(projfname)
                filename += projfname
        else:
            filename += store.get_filename()
        return filename

    def get_store_checker(self):
        store = self.get_store()
        if not store:
            raise ValueError('No store to get checker from')
        return store.get_checker()

    def get_store_stats(self):
        store = self.get_store()
        if not store:
            raise ValueError('No store to get checker from')
        return store.stats

    def get_store_checks(self):
        store = self.get_store()
        if not store:
            raise ValueError('No store to get checker from')
        return store.checks

    def get_unit_celleditor(self, unit):
        """Load the given unit in via the C{UnitController} and return
            the C{gtk.CellEditable} it creates."""
        return self.unit_controller.load_unit(unit)

    def is_modified(self):
        return self._modified

    def _get_unitcontroller(self):
        return self._unit_controller

    def _set_unitcontroller(self, unitcont):
        """@type unitcont: UnitController"""
        if self.unit_controller and 'unitview.unit-modified' in self.handler_ids:
            self.unit_controller.disconnect(self.handler_ids['unitview.unit-modified'])
        self._unit_controller = unitcont
        self.handler_ids['unitview.unit-modified'] = self.unit_controller.connect('unit-modified', self._unit_modified)
    unit_controller = property(_get_unitcontroller, _set_unitcontroller)


    # METHODS #
    def select_unit(self, unit, force=False):
        """Select the specified unit and scroll to it.
            Note that, because we change units via the cursor, the unit to
            select must be valid according to the cursor."""
        if self.cursor.deref() is unit:
            # Unit is already selected; no need to do more work
            return

        i = 0
        try:
            # XXX: list.index() is O(n) - pretty bad in a long file if we're
            # looking for something towards the end. Keep in mind that it
            # calls unit.__eq__ which does a *lot* of things.
            i = self.store.get_units().index(unit)
            #TODO: consider replacing with API that uses index instead of unit
        except Exception, exc:
            import logging
            logging.debug('Unit not found:\n%s' % (exc))

        if force:
            self.cursor.force_index(i)
        else:
            self.cursor.index = i

    def open_file(self, filename, uri='', forget_dir=False):
        from virtaal.models.storemodel import StoreModel
        from translate.convert import factory as convert_factory
        force_saveas = False
        extension = filename.split(os.extsep)[-1]
        if extension == 'zip':
            import logging
            from translate.storage import bundleprojstore
            try:
                from translate.storage.project import Project
                self.project = Project(bundleprojstore.BundleProjectStore(filename))
            except bundleprojstore.InvalidBundleError, err:
                logging.exception('Unable to load project bundle')

            if not len(self.project.store.transfiles):
                # FIXME: Ask the user to select a source file to convert?
                if not len(self.project.store.sourcefiles):
                    raise bundleprojstore.InvalidBundleError(_('No source or translatable files in bundle'))
                self.project.convert_forward(self.project.store.sourcefiles[0])

            # FIXME: Ask the user which translatable file to open?
            transfile = self.project.get_file(self.project.store.transfiles[0])
            self.real_filename = transfile.name
            logging.info(
                'Editing translation file %s:%s' %
                (filename, self.project.store.transfiles[0])
            )
            self.store = StoreModel(transfile, self)
        elif extension in convert_factory.converters:
            # Use temporary file name for bundle archive
            self._targetfname = self._get_new_bundle_filename(filename)
            tempfname = self._get_new_bundle_filename(filename, force_temp=True)
            self._archivetemp = tempfname
            from translate.storage import bundleprojstore
            from translate.storage.project import Project
            self.project = Project(projstore=bundleprojstore.BundleProjectStore(tempfname))
            srcfile, srcfilename, transfile, transfilename = self.project.add_source_convert(filename)
            self.real_filename = transfile.name

            import logging
            logging.info('Converted document %s to translatable file %s' % (srcfilename, self.real_filename))
            self.store = StoreModel(transfile, self)
            force_saveas = True
        else:
            self.store = StoreModel(filename, self)

        if len(self.store.get_units()) < 1:
            # clean up, otherwise self.store still contains the store
            self.close_file()
            raise ValueError(_('The file contains nothing to translate.'))

        self._modified = False

        # if file is a template, force saveas
        import re
        _pot_re = re.compile("\.pot(\.gz|\.bz2)?$")
        if _pot_re.search(filename):
            force_saveas = True
            self.store._trans_store.filename = _pot_re.sub('.po', filename)
            filename = _pot_re.sub('.po', filename)

        # forgetting the directory only makes sense if we force save as
        if force_saveas and forget_dir:
            filename = os.path.split(filename)[1]
            self.store._trans_store.filename = filename

        self.main_controller.set_force_saveas(force_saveas)
        self.main_controller.set_saveable(self._modified)

        from cursor import Cursor
        self.cursor = Cursor(self.store, self.store.stats['total'])

        self.view.load_store(self.store)
        self.view.show()

        self.emit('store-loaded')

    def save_file(self, filename=None):
        self.unit_controller.prepare_for_save()
        if self.project is None:
            self.store.save_file(filename) # store.save_file() will raise an appropriate exception if necessary
        else:
            # XXX: filename is the name that the bundle archive should be saved
            #      as, seeing as self.store is opened from a temporary file
            #      (see translate.storage.bundleprojstore.BundleProjectStore.get_file())
            self.store.save_file()

            proj_fname = self.project.get_proj_filename(self.real_filename)
            if not proj_fname:
                # This really shouldn't happen
                raise ValueError("Unable to determine file's project name: %s" % (self.real_filename))

            self.project.update_file(proj_fname, open(self.real_filename))
            self.project.convert_forward(proj_fname, overwrite_output=True)
            self.project.save()

            if self._archivetemp:
                if self._archivetemp == filename:
                    self._archivetemp = None
                else:
                    assert self.project.store.zip.filename == self._archivetemp
                    self.project.close()
                    self.project = None
                    import shutil
                    shutil.move(self._archivetemp, filename)
                    self._archivetemp = None

                    cursor_pos = self.cursor.pos
                    def post_save(sender):
                        if not hasattr(self, '_proj_file_saved_id'):
                            return
                        self.disconnect(self._proj_file_saved_id)
                        self.main_controller.open_file(filename)
                        self.cursor.pos = cursor_pos
                    self._proj_file_saved_id = self.connect('store-saved', post_save)
        self._modified = False
        self.main_controller.set_saveable(False)
        self.emit('store-saved')

    def binary_export(self, filename):
        #TODO: confirm file extension is correct
        #TODO: confirm that there is something translated in the store
        from translate.tools.pocompile import POCompile
        compiler = POCompile()
        binary_output = open(filename, 'wb')
        binary_output.write(compiler.convertstore(self.store._trans_store))
        binary_output.close()

    def close_file(self):
        del self.project
        self.project = None
        self.store = None
        self._modified = False
        self.main_controller.set_saveable(False)
        self.view.hide() # This MUST be called BEFORE `self.cursor = None`
        self.emit('store-closed') # This should be emitted BEFORE `self.cursor = None` to allow any other modules to disconnect from the cursor
        self.cursor = None
        import gc
        gc.collect()

    def export_project_file(self, filename=None, openafter=False, readonly=False):
        if not self.project:
            return
        import logging
        if self.is_modified():
            self.main_controller.save_file()
        self.project.save()

        # Make sure we have an output file to export
        export_projfname = None
        if self.project.store.targetfiles:
            export_projfname = self.project.store.targetfiles[0]
        elif self.project.store.transfiles:
            transfile = self.project.store.transfiles[0]
            _export_file, export_projfname = self.project.convert_forward(transfile)

        if not export_projfname:
            raise RuntimeError("Unable to find an exportable file in project")

        if not filename:
            if readonly:
                # Read-only files to in the temp directory with a different
                # layout of its filename.
                from translate.storage.project import split_extensions
                fname, ext = split_extensions(export_projfname.split('/')[-1])
                fname = 'virtaal_preview_' + fname + '_'
                ext = os.extsep + ext
                from tempfile import mkstemp
                fd, filename = mkstemp(suffix=ext, prefix=fname)
                os.close(fd)
                self._tempfiles.append(filename)
            else:
                filename = self._guess_export_filename(export_projfname)

        logging.debug('Exporting project file %s to %s' % (export_projfname, filename))
        self.project.export_file(export_projfname, filename)

        if readonly:
            logging.debug('Setting %s read-only' % (filename))
            from stat import S_IREAD
            os.chmod(filename, S_IREAD)

        if openafter:
            logging.debug('Opening: %s' % (filename))
            from virtaal.support import openmailto
            openmailto.open(filename)

    def revert_file(self):
        self.open_file(self.store.filename)

    def update_file(self, filename, uri=''):
        if not self.store:
            #FIXME: we should never allow updates if no file is already open
            self.open_file(filename, uri=uri)
            return

        post_update_action = None
        extension = filename.split(os.extsep)[-1]
        from translate.convert import factory as convert_factory
        if extension in convert_factory.converters:
            import logging
            from translate.storage import factory
            try:
                outfile = convert_factory.convert(open(filename))[0]
                factory.getobject(outfile.name)
                filename = outfile.name
                def unlink_outfile():
                    try:
                        os.unlink(filename)
                    except Exception:
                        logging.exception("Unable to delete file %s:" % (filename))
            except Exception:
                # Anticipated exceptions/errors:
                # * Conversion error: anything that went wrong in
                #   convert_factory.convert(). This is likely if filename is a
                #   translation store that needs a template to be converted by
                #   the (automatically) selected converter.
                # * AttributeError on "outfile.name": if outfile is not a file-
                #   like object (with a "name" attribute)
                # * ValueError on factory.getobject(): outfile is not a
                #   translation store. This will happen when filename already
                #   refers to a translation store and we just converted it to
                #   a non-translation store format. FIXME: This might indicate
                #   a problem with the convert_factory not distinguising between
                #   its input and output document types.
                logging.exception("Error converting file to translatable file:")

        # Let's entirely clear things in the view to ensure that no signals
        # are still attached to old models before we start chaning things. See 
        # bug 1854.
        self.view.load_store(None)
        self.store.update_file(filename)

        self._modified = True
        self.main_controller.set_saveable(self._modified)
        self.main_controller.set_force_saveas(self._modified)

        from cursor import Cursor
        self.cursor = Cursor(self.store, self.store.stats['total'])

        self.view.load_store(self.store)
        self.view.show()

        self.emit('store-loaded')

    def update_store_checks(self, **kwargs):
        """Shortcut to C{StoreModel.update_stats()}"""
        store = self.get_store()
        if not store:
            raise ValueError('No store to get checker from')
        return store.update_checks(**kwargs)

    def compare_stats(self, oldstats, newstats):
        #l10n: The heading of statistics before updating to the new template
        before = _("Before:")
        #l10n: The heading of statistics after updating to the new template
        after = _("After:")
        translated = _("Translated: %d")
        fuzzy = _("Fuzzy: %d")
        untranslated = _("Untranslated: %d")
        total = _("Total: %d")
        output = "%s\n\t%s\n\t%s\n\t%s\n\t%s\n" % (before, translated, fuzzy, untranslated, total)
        output += "%s\n\t%s\n\t%s\n\t%s\n\t%s" % (after, translated, fuzzy, untranslated, total)

        old_trans = len(oldstats['translated'])
        old_fuzzy = len(oldstats['fuzzy'])
        old_untrans = len(oldstats['untranslated'])
        old_total = old_trans + old_fuzzy + old_untrans

        new_trans = len(newstats['translated'])
        new_fuzzy = len(newstats['fuzzy'])
        new_untrans = len(newstats['untranslated'])
        new_total = new_trans + new_fuzzy + new_untrans

        output %= (old_trans, old_fuzzy, old_untrans, old_total,
                   new_trans, new_fuzzy, new_untrans, new_total)

        #l10n: this refers to updating a file to a new template (POT file)
        self.main_controller.show_info(_("File Updated"), output)

    def _get_new_bundle_filename(self, infilename, force_temp=False):
        """Creates a file name that can be used for a bundle, based on the given
            file name.

            First tries to create a bundle in the same directory as the given
            file by the transformation in the following example:
            C{foo.odt -> foo_en__af.zip}
            where "en" and "af" are the currently selected source and target
            languages.

            If a file with that name already exists, an attempt will be made to
            create a file name in the format C{foo_en__af_XXXXX.zip} in the
            document's directory. If that fails (the directory might not be
            writable), a temporary file name of the same format is created.

            @returns: The suggested file name for the bundle."""
        from tempfile import mkstemp
        from translate.storage.project import split_extensions
        fname, extensions = split_extensions(infilename)

        prefix = fname + u'_%s__%s' % (
            self.main_controller.lang_controller.source_lang.code,
            self.main_controller.lang_controller.target_lang.code
        )
        if extensions:
            extensions_parts = extensions.split(os.extsep)
            extensions_parts[-1] = u'zip'
            suffix = os.extsep.join([''] + extensions_parts)
        else:
            suffix = os.extsep + u'zip'

        if not force_temp:
            # Try foo_en__af.zip
            outfname = prefix + suffix
            if not os.path.isfile(outfname):
                try:
                    os.unlink(outfname)
                    return outfname
                except Exception:
                    pass

            prefix += u'_'

            # Try foo_en__af_XXXXX.zip
            try:
                directory = os.path.split(os.path.abspath(infilename))[0]
                if not directory:
                    directory = None
                fd, outfname = mkstemp(suffix=suffix, prefix=prefix, dir=directory)
                os.close(fd)
                if os.path.isfile(outfname):
                    os.unlink(outfname)
                return outfname
            except Exception:
                pass

        # Try /tmp/foo_en__af_XXXXX.zip as a last resort
        prefix = os.path.basename(prefix)
        fd, outfname = mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        if os.path.isfile(outfname):
            os.unlink(outfname)
        return outfname

    def _guess_export_filename(self, projfname):
        guess = projfname.split('/')[-1]
        bundle_fname = self.get_bundle_filename()
        if bundle_fname:
            directory = os.path.split(os.path.abspath(bundle_fname))[0]
            guess = os.path.join(directory, guess)
        if os.path.isfile(guess):
            directory, fname = os.path.split(guess)
            from translate.storage.project import split_extensions
            basefname, extensions = split_extensions(fname)
            guess = basefname + u'_%s__%s' % (
                self.main_controller.lang_controller.source_lang.code,
                self.main_controller.lang_controller.target_lang.code
            )
            guess += os.extsep + extensions
            guess = os.path.join(directory, guess)
        return guess


    # EVENT HANDLERS #
    def _on_controller_registered(self, main_controller, controller):
        if controller is main_controller.lang_controller:
            main_controller.disconnect(self._controller_register_id)
            main_controller.lang_controller.connect('source-lang-changed', self._on_source_lang_changed)
            main_controller.lang_controller.connect('target-lang-changed', self._on_target_lang_changed)

    def _on_source_lang_changed(self, _sender, langcode):
        self.store.set_source_language(langcode)

    def _on_target_lang_changed(self, _sender, langcode):
        self.store.set_target_language(langcode)

    def _unit_modified(self, emitter, unit):
        self._modified = True
        self.main_controller.set_saveable(self._modified)

########NEW FILE########
__FILENAME__ = undocontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk
from gtk import gdk
from translate.storage.placeables import StringElem

from virtaal.common import GObjectWrapper, pan_app

from basecontroller import BaseController


class UndoController(BaseController):
    """Contains "undo" logic."""

    __gtype_name__ = 'UndoController'


    # INITIALIZERS #
    def __init__(self, main_controller):
        """Constructor.
            @type main_controller: virtaal.controllers.MainController"""
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.undo_controller = self
        self.unit_controller = self.main_controller.store_controller.unit_controller

        self.enabled = True
        from virtaal.models.undomodel import UndoModel
        self.model = UndoModel(self)

        self._setup_key_bindings()
        self._connect_undo_signals()

    def _connect_undo_signals(self):
        # First connect to the unit controller
        self.unit_controller.connect('unit-delete-text', self._on_unit_delete_text)
        self.unit_controller.connect('unit-insert-text', self._on_unit_insert_text)
        self.main_controller.store_controller.connect('store-closed', self._on_store_loaded_closed)
        self.main_controller.store_controller.connect('store-loaded', self._on_store_loaded_closed)

        mainview = self.main_controller.view
        mainview.gui.get_object('menu_edit').set_accel_group(self.accel_group)
        self.mnu_undo = mainview.gui.get_object('mnu_undo')
        self.mnu_undo.set_accel_path('<Virtaal>/Edit/Undo')
        self.mnu_undo.connect('activate', self._on_undo_activated)

    def _setup_key_bindings(self):
        """Setup Gtk+ key bindings (accelerators).
            This method *may* need to be moved into a view object, but if it is,
            it will be the only functionality in such a class. Therefore, it
            is done here. At least for now."""
        gtk.accel_map_add_entry("<Virtaal>/Edit/Undo", gtk.keysyms.z, gdk.CONTROL_MASK)

        self.accel_group = gtk.AccelGroup()
        # The following line was commented out, because it caused a double undo when pressing
        # Ctrl+Z, but only one if done through the menu item. This way it all works as expected.
        #self.accel_group.connect_by_path("<Virtaal>/Edit/Undo", self._on_undo_activated)

        mainview = self.main_controller.view # FIXME: Is this acceptable?
        mainview.add_accel_group(self.accel_group)


    # DECORATORS #
    def if_enabled(method):
        def enabled_method(self, *args, **kwargs):
            if self.enabled:
                return method(self, *args, **kwargs)
        return enabled_method


    # METHODS #
    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def push_current_text(self, textbox):
        """Save the current text in the given (target) text box on the undo stack."""
        current_text = textbox.elem.copy()
        unitview = self.unit_controller.view

        curpos = textbox.get_cursor_position()
        targetn = unitview.targets.index(textbox)
        def undo_set_text(unit):
            textbox.elem.sub = current_text.sub

        data = {
            'action': undo_set_text,
            'cursorpos': curpos,
            'targetn': targetn,
            'unit': unitview.unit
        }
        if pan_app.DEBUG:
            data['desc'] = 'Set target %d text to %s' % (targetn, repr(current_text)),
        self.model.push(data)

    def record_stop(self):
        self.model.record_stop()

    def record_start(self):
        self.model.record_start()

    def _disable_unit_signals(self):
        """Disable all signals emitted by the unit view.
            This should always be followed, as soon as possible, by
            C{self._enable_unit_signals()}."""
        self.unit_controller.view.disable_signals()

    def _enable_unit_signals(self):
        """Enable all signals emitted by the unit view.
            This should always follow, as soon as possible, after a call to
            C{self._disable_unit_signals()}."""
        self.unit_controller.view.enable_signals()

    def _perform_undo(self, undo_info):
        self._select_unit(undo_info['unit'])

        #if 'desc' in undo_info:
        #    logging.debug('Description: %s' % (undo_info['desc']))

        self._disable_unit_signals()
        undo_info['action'](undo_info['unit'])
        self._enable_unit_signals()

        textbox = self.unit_controller.view.targets[undo_info['targetn']]
        def refresh():
            textbox.refresh_cursor_pos = undo_info['cursorpos']
            textbox.refresh()
        gobject.idle_add(refresh)

    def _select_unit(self, unit):
        """Select the given unit in the store view.
            This is to select the unit where the undo-action took place.
            @type  unit: translate.storage.base.TranslationUnit
            @param unit: The unit to select in the store view."""
        self.main_controller.select_unit(unit, force=True)


    # EVENT HANDLERS #
    def _on_store_loaded_closed(self, storecontroller):
        if storecontroller.store is not None:
            self.mnu_undo.set_sensitive(True)
        else:
            self.mnu_undo.set_sensitive(False)
        self.model.clear()

    @if_enabled
    def _on_undo_activated(self, *args):
        undo_info = self.model.pop()
        if not undo_info:
            return

        if isinstance(undo_info, list):
            for ui in reversed(undo_info):
                self._perform_undo(ui)
        else:
            self._perform_undo(undo_info)

    @if_enabled
    def _on_unit_delete_text(self, unit_controller, unit, deleted, parent, offset, cursor_pos, elem, target_num):
        def undo_action(unit):
            #logging.debug('(undo) %s.insert(%d, "%s")' % (repr(elem), offset, deleted))
            if parent is None:
                elem.sub = deleted.sub
                return
            if isinstance(deleted, StringElem):
                try:
                    elem.insert(offset, deleted, preferred_parent=parent)
                except TypeError:
                    # the preferred_parent parameter is not in Toolkit 1.9 or
                    # 1.10 with which we otherwise work perfectly. So work with
                    # this just to make it easier for people from checkout.
                    # TODO: remove this when we depend on newer toolkit version
                    elem.insert(offset, deleted)
                elem.prune()

        data = {
            'action': undo_action,
            'cursorpos': cursor_pos,
            'targetn': target_num,
            'unit': unit,
        }
        if pan_app.DEBUG:
            data['desc'] = 'offset=%d, deleted="%s", parent=%s, cursor_pos=%d, elem=%s' % (offset, repr(deleted), repr(parent), cursor_pos, repr(elem))
        self.model.push(data)

    @if_enabled
    def _on_unit_insert_text(self, unit_controller, unit, ins_text, offset, elem, target_num):
        #logging.debug('_on_unit_insert_text(ins_text="%r", offset=%d, elem=%s, target_n=%d)' % (ins_text, offset, repr(elem), target_num))
        len_ins_text = len(ins_text) # remember, since ins_text might change

        def undo_action(unit):
            if isinstance(ins_text, StringElem) and hasattr(ins_text, 'gui_info') and ins_text.gui_info.widgets:
                # Only for elements with representation widgets
                elem.delete_elem(ins_text)
            else:
                tree_offset = elem.gui_info.gui_to_tree_index(offset)
                #logging.debug('(undo) %s.delete_range(%d, %d)' % (repr(elem), tree_offset, tree_offset+len_ins_text))
                elem.delete_range(tree_offset, tree_offset+len_ins_text)
            elem.prune()

        data = {
            'action': undo_action,
            'unit': unit,
            'targetn': target_num,
            'cursorpos': offset
        }
        if pan_app.DEBUG:
            data['desc'] = 'ins_text="%s", offset=%d, elem=%s' % (ins_text, offset, repr(elem))
        self.model.push(data)

########NEW FILE########
__FILENAME__ = unitcontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from gobject import SIGNAL_RUN_FIRST, timeout_add
from translate.storage import workflow

from virtaal.common import GObjectWrapper

from basecontroller import BaseController


class UnitController(BaseController):
    """Controller for unit-based operations."""

    __gtype_name__ = "UnitController"
    __gsignals__ = {
        'unit-done':           (SIGNAL_RUN_FIRST, None, (object, int)),
        'unit-modified':       (SIGNAL_RUN_FIRST, None, (object,)),
        'unit-delete-text':    (SIGNAL_RUN_FIRST, None, (object, object, object, int, int, object, int)),
        'unit-insert-text':    (SIGNAL_RUN_FIRST, None, (object, object, int, object, int)),
        'unit-paste-start':    (SIGNAL_RUN_FIRST, None, (object, object, object, int)),
    }

    STATE_TIMEOUT = 200

    # INITIALIZERS #
    def __init__(self, store_controller):
        GObjectWrapper.__init__(self)

        self.current_unit = None
        self.main_controller = store_controller.main_controller
        self.main_controller.unit_controller = self
        self.store_controller = store_controller
        self.store_controller.unit_controller = self
        self.checks_controller = None

        from virtaal.views.unitview import UnitView
        self.view = UnitView(self)
        self.view.connect('delete-text', self._unit_delete_text)
        self.view.connect('insert-text', self._unit_insert_text)
        self.view.connect('paste-start', self._unit_paste_start)
        self.view.connect('modified', self._unit_modified)
        self.view.connect('unit-done', self._unit_done)
        self.view.enable_signals()

        self.store_controller.connect('store-loaded', self._on_store_loaded)
        self.main_controller.connect('controller-registered', self._on_controller_registered)

        self._recreate_workflow = False
        self._unit_state_names = {}
        self._state_timer_active = False


    # ACCESSORS #
    def get_unit_target(self, target_index):
        return self.view.get_target_n(target_index)

    def set_unit_target(self, target_index, value, cursor_pos=-1):
        self.view.set_target_n(target_index, value, cursor_pos)


    # METHODS #
    def get_unit_state_names(self, unit=None):
        self._unit_state_names = {
            #FIXME: choose friendly names
            workflow.StateEnum.EMPTY: _('Untranslated'),
            workflow.StateEnum.NEEDS_WORK: _('Needs work'),
            workflow.StateEnum.REJECTED: _('Rejected'),
            workflow.StateEnum.NEEDS_REVIEW: _('Needs review'),
            workflow.StateEnum.UNREVIEWED: _('Translated'),
            workflow.StateEnum.FINAL: _('Reviewed'),
            }
        return self._unit_state_names

    def set_current_state(self, newstate, from_user=False):
        if isinstance(newstate, workflow.UnitState):
            newstate = newstate.state_value
        self.current_unit._current_state = newstate
        if from_user:
            # No need to update the GUI, and we should make the choice sticky
            self.current_unit._state_sticky = True
        else:
            self.view.update_state(self._unit_state_names[newstate])

    def load_unit(self, unit):
        if self.current_unit and self.current_unit is unit:
            return self.view
        self.current_unit = unit
        self.nplurals = self.main_controller.lang_controller.target_lang.nplurals

        unit._modified = False
        if not unit.STATE:
            # If the unit doesn't support states, just skip the state code
            self.view.load_unit(unit)
            return self.view

        # This unit does support states
        state_n, state_id = unit.get_state_n(), unit.get_state_id()
        state_names = self.get_unit_state_names()
        unit._state_sticky = False
        unit._current_state = state_n
        if self._recreate_workflow or True:
            # This will only happen when a document is loaded.
            self._unit_state_names = {}
            # FIXME: The call below is run for the second time, but is necessary
            #        because the names could have changed in the new document :/
            state_names = self.get_unit_state_names()
            if state_names:
                unit._workflow = workflow.create_unit_workflow(unit, state_names)
            self._recreate_workflow = False

        if state_names:
            unit._workflow.reset(unit, init_state=state_names[state_id])
            #XXX: we should make 100% sure that .reset() doesn't actually call
            # a set method in the unit, since it might cause a diff or loss of
            # meta-data.
        self.view.load_unit(unit)
        return self.view

    def _unit_delete_text(self, unitview, deleted, parent, offset, cursor_pos, elem, target_num):
        self.emit('unit-delete-text', self.current_unit, deleted, parent, offset, cursor_pos, elem, target_num)

    def _unit_insert_text(self, unitview, ins_text, offset, elem, target_num):
        self.emit('unit-insert-text', self.current_unit, ins_text, offset, elem, target_num)

    def _unit_paste_start(self, unitview, old_text, offsets, target_num):
        self.emit('unit-paste-start', self.current_unit, old_text, offsets, target_num)

    def _unit_modified(self, *args):
        self.emit('unit-modified', self.current_unit)
        self.current_unit._modified = True
        if self.current_unit.STATE and not self.current_unit._state_sticky:
            self._start_state_timer()

    def _unit_done(self, widget, unit):
        if unit._modified and unit.STATE:
            if len(unit.target) != 0 and unit._current_state == workflow.StateEnum.EMPTY and not unit._state_sticky:
                # Oops! The user entered a translation, but the timer didn't
                # expire yet, so let's mark it fuzzy to be safe. We don't know
                # exactly what kind of fuzzy the format supports, so let's use
                # .set_state_n() directly. Also, if the workflow does more, we
                # probably don't want it, since we really only want to set the
                # state.
                unit.set_state_n(workflow.StateEnum.NEEDS_REVIEW)
            else:
                # Now really advance the workflow that we ended at
                unit._workflow.set_current_state(self._unit_state_names[unit._current_state])

        self.emit('unit-done', unit, unit._modified)
        # let's just clean up a bit:
        del unit._modified
        if unit.STATE:
            del unit._state_sticky
            del unit._current_state

    def _state_timer_expired(self, unit):
        self._state_timer_active = False
        if unit is not self.current_unit:
            return
        if unit.hasplural():
            target_len = min([len(s) for s in unit.target.strings])
        else:
            target_len = len(unit.target)
        empty_state = unit._current_state == workflow.StateEnum.EMPTY
        if target_len and empty_state:
            self.set_current_state(workflow.StateEnum.UNREVIEWED)
        elif not target_len and not empty_state:
            self.set_current_state(workflow.StateEnum.EMPTY)

    def _start_state_timer(self):
        if self._state_timer_active:
            return
        self._state_timer_active = True
        timeout_add(self.STATE_TIMEOUT, self._state_timer_expired, self.current_unit)

    def prepare_for_save(self):
        """Finalise outstanding changes to the toolkit store for saving."""
        unit = self.current_unit
        if unit._modified and unit.STATE:
            unit._workflow.set_current_state(self._unit_state_names[unit._current_state])

    # EVENT HANDLERS #
    def _on_controller_registered(self, main_controller, controller):
        if controller is main_controller.lang_controller:
            self.main_controller.lang_controller.connect('source-lang-changed', self._on_language_changed)
            self.main_controller.lang_controller.connect('target-lang-changed', self._on_language_changed)
        elif controller is main_controller.checks_controller:
            self.checks_controller = controller
        elif controller is main_controller.placeables_controller:
            controller.connect('parsers-changed', self._on_parsers_changed)
            self._on_parsers_changed(controller)

    def _on_language_changed(self, lang_controller, langcode):
        self.nplurals = lang_controller.target_lang.nplurals
        if hasattr(self, 'view'):
            self.view.update_languages()

    def _on_parsers_changed(self, placeables_controller):
        if self.current_unit:
            self.current_unit.rich_source = placeables_controller.apply_parsers(self.current_unit.rich_source)

    def _on_store_loaded(self, store_controller):
        """Call C{_on_language_changed()} and set flag to recreate workflow.

            If the target language loaded at start-up (from config) is the same
            as that of the first opened file, C{self.view.update_languages()} is
            not called, because the L{LangController}'s C{"target-lang-changed"}
            signal is never emitted, because the language has not really
            changed.

            This event handler ensures that it is loaded. As a side-effect,
            C{self.view.update_languages()} is called twice if language before
            and after a store load is different. But we'll just have to live
            with that."""
        self._on_language_changed(
            self.main_controller.lang_controller,
            self.main_controller.lang_controller.target_lang.code
        )
        self._recreate_workflow = True

########NEW FILE########
__FILENAME__ = welcomescreencontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


from basecontroller import BaseController


class WelcomeScreenController(BaseController):
    """
    Contains logic for the welcome screen.
    """

    MAX_RECENT = 5
    """The maximum number of recent items to display."""

    LINKS = {
        'manual':   _('http://translate.sourceforge.net/wiki/virtaal/using_virtaal'),
        'locguide': _('http://translate.sourceforge.net/wiki/guide/start'),
        # FIXME: The URL below should be replaced with a proper feedback URL
        'feedback': _("http://translate.sourceforge.net/wiki/virtaal/index#contact"),
        'features_more': _('http://translate.sourceforge.net/wiki/virtaal/features')
    }

    # INITIALIZERS #
    def __init__(self, main_controller):
        self.main_controller = main_controller
        main_controller.welcomescreen_controller = self

        self._recent_files = []
        from virtaal.views.welcomescreenview import WelcomeScreenView
        self.view = WelcomeScreenView(self)

        main_controller.store_controller.connect('store-closed', self._on_store_closed)
        main_controller.store_controller.connect('store-loaded', self._on_store_loaded)


    # METHODS #
    def activate(self):
        """Show the welcome screen and trigger activation logic (ie. find
            recent files)."""
        from gobject import idle_add
        idle_add(self.update_recent)
        self.view.show()

    def open_cheatsheat(self):
        from virtaal.support import openmailto
        # FIXME: The URL below is just a temporary solution
        openmailto.open(_('http://translate.sourceforge.net/wiki/virtaal/cheatsheet'))

    def open_file(self, filename=None):
        self.main_controller.open_file(filename)

    def open_recent(self, n):
        n -= 1 # Shift from nominal value [1; 5] to index value [0; 4]
        if 0 <= n <= len(self._recent_files)-1:
            self.open_file(self._recent_files[n]['uri'].decode('utf-8'))
        else:
            import logging
            logging.debug('Invalid recent file index (%d) given. Recent files: %s)' % (n, self._recent_files))

    def open_tutorial(self):
        self.main_controller.open_tutorial()

    def try_open_link(self, name):
        if name not in self.LINKS:
            return False
        from virtaal.support import openmailto
        openmailto.open(self.LINKS[name])
        return True

    def update_recent(self):
        from virtaal.views import recent
        self._recent_files = [{
                'name': i.get_display_name(),
                'uri':  i.get_uri_display()
            } for i in recent.rc.get_items()[:self.MAX_RECENT]
        ]
        self.view.update_recent_buttons(self._recent_files)


    # EVENT HANDLERS #
    def _on_store_closed(self, store_controller):
        self.activate()

    def _on_store_loaded(self, store_controller):
        self.view.hide()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


# This is the main loader for Virtaal. We want the GUI to show really quickly,
# so do a few unusual things. The _Deferer helps us to serialise events in idle
# spots in the gobject event loop, so that we can load some expensive stuff
# after the GUI is already showing.


import gobject


class _Deferer:
    _todo = []

    def __call__(self, func, *args):
        def next_job():
            # We return True if we want gobject to schedule this again while
            # there is still something to do
            try:
                (func, args) = self._todo.pop(0)
            except IndexError:
                # This is possible if a previous func() was last, but added
                # something during execution. Therefore a different next_job()
                # is in the event loop to handle that job, and will be gone
                # when we get round to doing this one again.
                return False
            func(*args)
            return bool(self._todo)

        if not self._todo:
            # No existing jobs, so start one
            gobject.idle_add(next_job)
        self._todo.append((func, args))


class Virtaal(object):
    """The main Virtaal program entry point."""

    def __init__(self, startupfile):
        # We try to get the welcomescreen loaded as early as possible
        from virtaal.controllers.maincontroller import MainController
        from virtaal.controllers.welcomescreencontroller import WelcomeScreenController
        from virtaal.controllers.storecontroller import StoreController

        main_controller = MainController()
        store_controller = StoreController(main_controller)

        self.defer = _Deferer()
        self.main_controller = main_controller

        if startupfile:
            # Just call the open plainly - we want it done before we start the
            # event loop.
            if self._open_with_file(startupfile):
                self.defer(WelcomeScreenController, main_controller)
            else:
                # Something went wrong, and we have to show the welcome screen
                wc = WelcomeScreenController(main_controller)
                wc.activate()
            self.defer(self._load_extras)

        else:
            wc = WelcomeScreenController(main_controller)
            wc.activate()
            # Now we try to get the event loop started as quickly as possible,
            # so we defer as much as possible.
            self.defer(self._open_with_welcome)


    def _open_with_file(self, startupfile):
        # Things needed for opening a file, including inter-dependencies
        from virtaal.controllers.unitcontroller import UnitController
        from virtaal.controllers.modecontroller import ModeController
        from virtaal.controllers.langcontroller import LanguageController
        from virtaal.controllers.placeablescontroller import PlaceablesController

        main_controller = self.main_controller

        if isinstance(startupfile, str):
            import sys
            startupfile = unicode(startupfile, sys.getfilesystemencoding())

        UnitController(main_controller.store_controller)
        ModeController(main_controller)
        LanguageController(main_controller)
        PlaceablesController(main_controller)

        return main_controller.open_file(startupfile)

    def _open_with_welcome(self):
        from virtaal.controllers.unitcontroller import UnitController
        from virtaal.controllers.modecontroller import ModeController
        from virtaal.controllers.langcontroller import LanguageController
        from virtaal.controllers.placeablescontroller import PlaceablesController

        defer = self.defer
        main_controller = self.main_controller

        defer(UnitController, main_controller.store_controller)
        defer(ModeController, main_controller)
        defer(LanguageController, main_controller)
        defer(PlaceablesController, main_controller)
        self.defer(self._load_extras)

    def _load_extras(self):
        from virtaal.controllers.plugincontroller import PluginController
        from virtaal.controllers.prefscontroller import PreferencesController
        from virtaal.controllers.checkscontroller import ChecksController
        from virtaal.controllers.undocontroller import UndoController
        from virtaal.controllers.propertiescontroller import PropertiesController

        defer = self.defer
        main_controller = self.main_controller

        defer(ChecksController, main_controller)
        defer(UndoController, main_controller)
        defer(PluginController, main_controller)
        defer(PreferencesController, main_controller)
        defer(PropertiesController, main_controller)
        defer(main_controller.load_plugins)


    # METHODS #
    def run(self):
        self.main_controller.run()
        self.main_controller.destroy()
        del self.main_controller


if __name__ == '__main__':
    virtaal = Virtaal('')
    virtaal.run()

########NEW FILE########
__FILENAME__ = basemodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject


class BaseModel(gobject.GObject):
    """Base class for all models."""

    __gtype_name__ = "BaseModel"

    __gsignals__ = {
        "loaded": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        "saved":  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    }

    # INITIALIZERS #
    def __init__(self):
        gobject.GObject.__init__(self)


    # ACCESSORS #
    def is_modified(self):
        return False

    # METHODS #
    def loaded(self):
        """Emits the "loaded" signal."""
        self.emit('loaded')

    def saved(self):
        """Emits the "saved" signal."""
        self.emit('saved')

########NEW FILE########
__FILENAME__ = langmodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging

from translate.lang.data import languages as toolkit_langs, tr_lang
from translate.lang import data

from virtaal.common.pan_app import ui_language

from basemodel import BaseModel

gettext_lang = tr_lang(ui_language)

class LanguageModel(BaseModel):
    """
    A simple container for language information for use by the C{LanguageController}
    and C{LanguageView}.
    """

    __gtype_name__ = 'LanguageModel'

    languages = {}

    # INITIALIZERS #
    def __init__(self, langcode='und', more_langs={}):
        """Constructor.
            Looks up the language information based on the given language code
            (C{langcode})."""
        super(LanguageModel, self).__init__()
        if not self.languages:
            self.languages.update(toolkit_langs)
        self.languages.update(more_langs)
        self.load(langcode)


    # SPECIAL METHODS #
    def __eq__(self, otherlang):
        """Check that the C{code}, C{nplurals} and C{plural} attributes are the
            same. The C{name} attribute may differ, seeing as it is localised.

            @type  otherlang: LanguageModel
            @param otherlang: The language to compare the current instance to."""
        return  isinstance(otherlang, LanguageModel) and \
                self.code     == otherlang.code and \
                self.nplurals == otherlang.nplurals and \
                self.plural   == otherlang.plural


    # METHODS #
    def load(self, langcode):
        #FIXME: what if we get language code with different capitalization?
        if langcode not in self.languages:
            try:
                langcode = self._match_normalized_langcode(langcode)
            except ValueError:
                langcode = data.simplify_to_common(langcode, self.languages)
                if langcode not in self.languages:
                    try:
                        langcode = self._match_normalized_langcode(langcode)
                    except ValueError:
                        logging.info("unkown language %s" % langcode)
                        self.name = langcode
                        self.code = langcode
                        self.nplurals = 0
                        self.plural = ""
                        return

        self.name = gettext_lang(self.languages[langcode][0])
        self.code = langcode
        self.nplurals = self.languages[langcode][1]
        self.plural = self.languages[langcode][2]

    def _match_normalized_langcode(self, langcode):
        languages_keys = self.languages.keys()
        normalized_keys = [data.normalize_code(lang) for lang in languages_keys]
        i =  normalized_keys.index(data.normalize_code(langcode))
        return languages_keys[i]


########NEW FILE########
__FILENAME__ = storemodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os

from virtaal.common import pan_app

from basemodel import BaseModel


def fix_indexes(stats, valid_units=None):
    """convert statsdb array to use model index instead of storage class index"""
    if valid_units is None:
        valid_units = stats['total']

    new_stats = {}
    if valid_units:
        valid_unit_indexes = dict([(uindex, index) for (index, uindex) in enumerate(valid_units)])
        # Adjust stats
        for key in stats:
            if key == 'extended':
                new_stats['extended'] = {}
                for estate in stats['extended']:
                    new_stats['extended'][estate] = [valid_unit_indexes[i] for i in stats['extended'][estate]]
                continue
            new_stats[key] = [valid_unit_indexes[i] for i in stats[key]]
    return new_stats


class StoreModel(BaseModel):
    """
    This model represents a translation store/file. It is basically a wrapper
    for the C{translate.storage.store} class. It is mostly based on the old
    C{Document} class from Virtaal's pre-MVC days.
    """

    __gtype_name__ = "StoreModel"

    # INITIALIZERS #
    def __init__(self, fileobj, controller):
        super(StoreModel, self).__init__()
        self.controller = controller
        self.load_file(fileobj)


    # SPECIAL METHODS #
    def __getitem__(self, index):
        """Alias for C{get_unit}."""
        return self.get_unit(index)

    def __len__(self):
        if not self._trans_store:
            return -1
        return len(self._valid_units)


    # ACCESSORS #
    def get_filename(self):
        return self._trans_store and self._trans_store.filename or None

    def get_checker(self):
        return self._checker

    def get_source_language(self):
        """Return the current store's source language."""
        candidate = self._trans_store.units[0].getsourcelanguage()
        # If we couldn't get the language from the first unit, try the store
        if candidate is None:
            candidate = self._trans_store.getsourcelanguage()
        if candidate and not candidate in ['und', 'en', 'en_US']:
            return candidate

    def set_source_language(self, langcode):
        self._trans_store.setsourcelanguage(langcode)

    def get_target_language(self):
        """Return the current store's target language."""
        candidate = self._trans_store.units[0].gettargetlanguage()
        # If we couldn't get the language from the first unit, try the store
        if candidate is None:
            candidate = self._trans_store.gettargetlanguage()
        if candidate and candidate != 'und':
            return candidate

    def set_target_language(self, langcode):
        self._trans_store.settargetlanguage(langcode)

    def get_store_type(self):
        return self._trans_store.Name

    def get_unit(self, index):
        """Get a specific unit by index."""
        return self._trans_store.units[self._valid_units[index]]

    def get_units(self):
        # TODO: Add caching
        """Return the current store's (filtered) units."""
        return [self._trans_store.units[i] for i in self._valid_units]

    def get_stats_totals(self):
        """Return totals for word and string counts."""
        if not self.filename:
            return {}
        from translate.storage import statsdb
        totals = statsdb.StatsCache().file_extended_totals(self.filename,  self._trans_store)
        return totals


    # METHODS #
    def load_file(self, fileobj):
        # Adapted from Document.__init__()
        filename = fileobj
        if isinstance(filename, basestring):
            if not os.path.exists(filename):
                raise IOError(_('The file does not exist.'))
            if not os.path.isfile(filename):
                raise IOError(_('Not a valid file.'))
        else:
            # Try and determine the file name of the file object
            filename = getattr(fileobj, 'name', None)
            if filename is None:
                filename = getattr(fileobj, 'filename', None)
            if filename is None:
                filename = '<projectfile>'
        import logging
        logging.info('Loading file %s' % (filename))
        from translate.storage import factory
        self._trans_store = factory.getobject(fileobj)
        self.filename = filename
        self.update_stats(filename=filename)
        #self._correct_header(self._trans_store)
        self.nplurals = self._compute_nplurals(self._trans_store)

    def save_file(self, filename=None):
        self._update_header()
        if filename is None:
            filename = self.filename
        if filename == self.filename:
            self._trans_store.save()
        else:
            self._trans_store.savefile(filename)
        self.filename = filename
        self.update_stats(filename=filename)

    def update_stats(self, filename=None):
        self.stats = None
        if self._trans_store is None:
            return

        if filename is None:
            filename = self.filename

        from translate.storage import statsdb
        stats = statsdb.StatsCache().filestatestats(filename,  self._trans_store, extended=True)
        self._valid_units = stats['total']
        self.stats = fix_indexes(stats)
        return self.stats

    def update_checks(self, checker=None, filename=None):
        self.checks = None
        if self._trans_store is None:
            return

        if filename is None:
            filename = self.filename

        if checker is None:
            checker = self._checker
        else:
            self._checker = checker

        from translate.storage import statsdb
        errors = statsdb.StatsCache().filechecks(filename, checker, self._trans_store)
        self.checks = fix_indexes(errors, self._valid_units)
        return self.checks

    def update_file(self, filename):
        # Adapted from Document.__init__()
        from translate.storage import factory, statsdb
        newstore = factory.getobject(filename)
        oldfilename = self._trans_store.filename
        oldfileobj = self._trans_store.fileobj

        #get a copy of old stats before we convert
        from translate.filters import checks
        oldstats = statsdb.StatsCache().filestats(oldfilename, checks.UnitChecker(), self._trans_store)

        from translate.convert import pot2po
        self._trans_store = pot2po.convert_stores(newstore, self._trans_store, fuzzymatching=False)
        self._trans_store.fileobj = oldfileobj #Let's attempt to keep the old file and name if possible

        #FIXME: ugly tempfile hack, can we please have a pure store implementation of statsdb
        import tempfile
        import os
        tempfd, tempfilename = tempfile.mkstemp()
        os.write(tempfd, str(self._trans_store))
        self.update_stats(filename=tempfilename)
        os.close(tempfd)
        os.remove(tempfilename)

        self.controller.compare_stats(oldstats, self.stats)

        # store filename or else save is confused
        self._trans_store.filename = oldfilename
        self._correct_header(self._trans_store)
        self.nplurals = self._compute_nplurals(self._trans_store)

    def _compute_nplurals(self, store):
        # Copied as-is from Document._compute_nplurals()
        # FIXME this needs to be pushed back into the stores, we don't want to import each format
        from translate.storage.poheader import poheader
        if isinstance(store, poheader):
            nplurals, _pluralequation = store.getheaderplural()
            if nplurals is None:
                return
            return int(nplurals)
        else:
            from translate.storage import ts2 as ts
            if isinstance(store, ts.tsfile):
                return store.nplural()

    def _correct_header(self, store):
        """This ensures that the file has a header if it is a poheader type of
        file, and fixes the statistics if we had to add a header."""
        # Copied as-is from Document._correct_header()
        from translate.storage.poheader import poheader
        if isinstance(store, poheader) and not store.header():
            store.updateheader(add=True)
            new_stats = {}
            for key, values in self.stats.iteritems():
                new_stats[key] = [value+1 for value in values]
            self.stats = new_stats

    def _update_header(self):
        """Make sure that headers are complete and update with current time (if applicable)."""
        # This method comes from Virtaal 0.2's main_window.py:Virtaal._on_file_save().
        # It makes sure that, if we are working with a PO file, that all header info is present.
        from translate.storage.poheader import poheader, tzstring
        if isinstance(self._trans_store, poheader):
            name = self.controller.main_controller.get_translator_name()
            email = self.controller.main_controller.get_translator_email()
            team = self.controller.main_controller.get_translator_team()
            if name is None or email is None or team is None:
                # User cancelled
                raise Exception('Save cancelled.')
            pan_app.settings.translator["name"] = name
            pan_app.settings.translator["email"] = email
            pan_app.settings.translator["team"] = team
            pan_app.settings.write()

            header_updates = {}
            import time
            header_updates["PO_Revision_Date"] = time.strftime("%Y-%m-%d %H:%M") + tzstring()
            header_updates["X_Generator"] = pan_app.x_generator
            if name or email:
                header_updates["Last_Translator"] = u"%s <%s>" % (name, email)
                self._trans_store.updatecontributor(name, email)
            if team:
                header_updates["Language-Team"] = team
            target_lang = self.controller.main_controller.lang_controller.target_lang
            header_updates["Language"] = target_lang.code
            project_code = self.controller.main_controller.checks_controller.code
            if project_code:
                header_updates["X-Project-Style"] = project_code
            self._trans_store.updateheader(add=True, **header_updates)

            plural = target_lang.plural
            nplurals = target_lang.nplurals
            if plural:
                self._trans_store.updateheaderplural(nplurals, plural)

########NEW FILE########
__FILENAME__ = undomodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from basemodel import BaseModel


class UndoModel(BaseModel):
    """Simple model representing an undo history."""

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller

        super(UndoModel, self).__init__()
        self.index = -1
        self.recording = False
        self.undo_stack = []


    # METHODS #
    def clear(self):
        """Clear the undo stack and reset the index pointer."""
        self.undo_stack = []
        self.index = -1

    def pop(self, permanent=False):
        if not self.undo_stack or not (0 <= self.index < len(self.undo_stack)):
            return None

        if not permanent:
            self.index -= 1
            return self.undo_stack[self.index+1]

        # self.index does not necessarily point to the last element in the list, so we have
        # to throw away the rest of the list first.
        self.undo_stack = self.undo_stack[:self.index]
        item = self.undo_stack.pop()
        self.index = len(self.undo_stack) - 1
        return item

    def push(self, undo_dict):
        """Push an undo-action onto the undo stack.
            @type  undo_dict: dict
            @param undo_dict: A dictionary containing undo information with the
                following keys:
                 - "action": Value is a callable that is called (with the "unit"
                   value, to effect the undo).
                 - "unit": Value is the unit on which the undo-action is applicable.
                 - "targetn": The index of the target on which the undo is applicable.
                 - "cursorpos": The position of the cursor after the undo."""
        for key in ('action', 'unit', 'targetn', 'cursorpos'):
            if not key in undo_dict:
                raise ValueError('Invalid undo dictionary!')

        if self.recording:
            self.undo_stack[-1].append(undo_dict)
        else:
            if self.index < 0:
                self.undo_stack = []
            if self.index != len(self.undo_stack) - 1:
                self.undo_stack = self.undo_stack[:self.index+1]
            self.undo_stack.append(undo_dict)
        self.index = len(self.undo_stack) - 1

    def record_start(self):
        if self.recording:
            raise Exception('Undo already recording.')

        if self.index < 0:
            self.undo_stack = []
        if self.index != len(self.undo_stack) - 1:
            self.undo_stack = self.undo_stack[:self.index+1]

        self.undo_stack.append([])
        self.index = len(self.undo_stack) - 1
        self.recording = True

    def record_stop(self):
        if not self.recording:
            raise Exception("Undo can't stop recording if it was not recording in the first place.")

        # In some cases we can get rid of an unnecessary list containing
        # nothing or a single dictionary. That saves 32 bytes on 32 bit python
        # per entry.
        last_entry_len = len(self.undo_stack[-1])
        if last_entry_len == 0:
            # this can happen with something like Ctrl+C
            del self.undo_stack[-1]
        elif last_entry_len == 1:
            self.undo_stack[-1] = self.undo_stack[-1][0]
        self.recording = False

########NEW FILE########
__FILENAME__ = basemode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


class BaseMode(object):
    """Interface for other modes."""
    name = 'BaseMode'
    """The internal name of the mode."""
    display_name = ''
    """Sublcasses should mark this for translation with _()"""
    widgets = []

    # INITIALIZERS #
    def __init__(self, mode_controller):
        raise NotImplementedError()


    # METHODS #
    def selected(self):
        """Signals that this mode has just been selected by the given document."""
        raise NotImplementedError()

    def unselected(self):
        """This is run right before the mode is unselected."""
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = defaultmode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from basemode import BaseMode


class DefaultMode(BaseMode):
    """Default mode - Include all units."""

    name = 'Default'
    display_name = _("All")
    widgets = []

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.ModeController
            @param controller: The ModeController that managing program modes."""
        self.controller = controller


    # METHODS #
    def selected(self):
        cursor = self.controller.main_controller.store_controller.cursor
        if not cursor or not cursor.model:
            return
        cursor.indices = cursor.model.stats['total']

    def unselected(self):
        pass

########NEW FILE########
__FILENAME__ = qualitycheckmode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import locale
import gtk

from virtaal.views.widgets.popupmenubutton import PopupMenuButton, POS_NW_SW

from basemode import BaseMode


class QualityCheckMode(BaseMode):
    """Include units based on quality checks that units fail."""

    name = 'QualityCheck'
    display_name = _("Quality Checks")
    widgets = []

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.ModeController
            @param controller: The ModeController that managing program modes."""
        self.controller = controller
        self.store_controller = controller.main_controller.store_controller
        self.main_controller = controller.main_controller
        self._checker_set_id = None
        self.filter_checks = []
        # a way to map menuitems to their check names, and signal ids:
        self._menuitem_checks = {}
        self.store_filename = None


    # METHODS #
    def _prepare_stats(self):
        self.store_controller.update_store_checks(checker=self.main_controller.checks_controller.get_checker())
        self.stats = self.store_controller.get_store_checks()
        # A currently selected check might disappear if the style changes:
        self.filter_checks = [check for check in self.filter_checks if check in self.stats]
        self.storecursor = self.store_controller.cursor
        self.checks_names = {}
        for check, indices in self.stats.iteritems():
            if indices and check not in ('total', 'translated', 'untranslated', 'extended'):
                self.checks_names[check] = self.main_controller.checks_controller.get_check_name(check)

    def selected(self):
        self._prepare_stats()
        self._checker_set_id = self.main_controller.checks_controller.connect('checker-set', self._on_checker_set)
        # redo stats on save to refresh navigation controls
        self._store_saved_id = self.store_controller.connect('store-saved', self._on_checker_set)

        self._add_widgets()
        self._update_button_label()
        self.update_indices()

    def unselected(self):
        if self._checker_set_id:
            self.main_controller.checks_controller.disconnect(self._checker_set_id)
            self._checker_set_id = None
            self.store_controller.disconnect(self._store_saved_id)
            self.store_saved_id = None

    def update_indices(self):
        if not self.storecursor or not self.storecursor.model:
            return

        indices = []
        for check in self.filter_checks:
            indices.extend(self.stats[check])

        if not indices:
            indices = range(len(self.storecursor.model))
        indices.sort()

        self.storecursor.indices = indices

    def _add_widgets(self):
        table = self.controller.view.mode_box
        self.btn_popup = PopupMenuButton(menu_pos=POS_NW_SW)
        self.btn_popup.set_relief(gtk.RELIEF_NORMAL)
        self.btn_popup.set_menu(self._create_checks_menu())

        self.widgets = [self.btn_popup]

        xoptions = gtk.FILL
        table.attach(self.btn_popup, 2, 3, 0, 1, xoptions=xoptions)

        table.show_all()

    def _create_checks_menu(self):
        menu = gtk.Menu()
        self._create_menu_entries(menu)
        return menu

    def _create_menu_entries(self, menu):
        for mi, (name, signal_id) in self._menuitem_checks.iteritems():
            mi.disconnect(signal_id)
            menu.remove(mi)
        assert not menu.get_children()
        self._menuitem_checks = {}
        for check_name, display_name in sorted(self.checks_names.iteritems(), key=lambda x: x[1], cmp=locale.strcoll):
            #l10n: %s is the name of the check and must be first. %d is the number of failures
            menuitem = gtk.CheckMenuItem(label="%s (%d)" % (display_name, len(self.stats[check_name])))
            menuitem.set_active(check_name in self.filter_checks)
            menuitem.show()
            self._menuitem_checks[menuitem] = (check_name, menuitem.connect('toggled', self._on_check_menuitem_toggled))
            menu.append(menuitem)

    def _update_button_label(self):
        check_labels = [mi.child.get_label() for mi in self.btn_popup.menu if mi.get_active()]
        btn_label = u''
        if not check_labels:
            #l10n: This is the button where the user can select units by failing quality checks
            btn_label = _(u'Select Checks')
        elif len(check_labels) == len(self.checks_names):
            #l10n: This refers to quality checks
            btn_label = _(u'All Checks')
        else:
            btn_label = u', '.join(check_labels[:3])
            if len(check_labels) > 3:
                btn_label += u'...'
        self.btn_popup.set_label(btn_label)


    # EVENT HANDLERS #
    def _on_checker_set(self, checkscontroller, checker=None):
        self._prepare_stats()
        self._create_menu_entries(self.btn_popup.menu)
        self._update_button_label()
        self.update_indices()

    def _on_check_menuitem_toggled(self, checkmenuitem):
        self.filter_checks = []
        for menuitem in self.btn_popup.menu:
            if not isinstance(menuitem, gtk.CheckMenuItem) or not menuitem.get_active():
                continue
            if menuitem in self._menuitem_checks:
                self.filter_checks.append(self._menuitem_checks[menuitem][0])
        self.update_indices()
        self._update_button_label()

########NEW FILE########
__FILENAME__ = quicktransmode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from virtaal.support.set_enumerator import UnionSetEnumerator
from virtaal.support.sorted_set import SortedSet

from basemode import BaseMode


class QuickTranslateMode(BaseMode):
    """Quick translate mode - Include only untranslated and fuzzy units."""

    name = 'QuickTranslate'
    display_name = _("Incomplete")
    widgets = []

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.ModeController
            @param controller: The ModeController that managing program modes."""
        self.controller = controller


    # METHODS #
    def selected(self):
        cursor = self.controller.main_controller.store_controller.cursor
        if not cursor or not cursor.model:
            return

        indices = list(UnionSetEnumerator(
            SortedSet(cursor.model.stats['untranslated']),
            SortedSet(cursor.model.stats['fuzzy'])
        ).set)

        if not indices:
            self.controller.select_default_mode()
            return

        cursor.indices = indices

    def unselected(self):
        pass

########NEW FILE########
__FILENAME__ = searchmode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk
import gtk.gdk
import logging

from virtaal.controllers.cursor import Cursor

from basemode import BaseMode
from virtaal.views.theme import current_theme


class SearchMode(BaseMode):
    """Search mode - Includes only units matching the given search string."""

    display_name = _("Search")
    name = 'Search'
    widgets = []

    MAX_RESULTS = 200000
    SEARCH_DELAY = 500

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.ModeController
            @param controller: The ModeController managing navigation modes."""
        self.controller = controller
        self.unitview = controller.main_controller.unit_controller.view

        self._create_widgets()
        self._setup_key_bindings()
        # We alter the colours of ent_search, so let's listen for changes on
        # ent_replace to ensure we are always compliant to the style.
        self.ent_replace.connect('style-set', self._on_style_set)

        self.filter = None
        self.matches = []
        self.select_first_match = True
        self._search_timeout = 0
        self._unit_modified_id = 0

    def _create_widgets(self):
        # Widgets for search functionality (in first row)
        self.ent_search = gtk.Entry()
        self.ent_search.connect('changed', self._on_search_text_changed)
        self.ent_search.connect('activate', self._on_entry_activate)
        self.btn_search = gtk.Button(_('Search'))
        self.btn_search.connect('clicked', self._on_search_clicked)
        self.chk_casesensitive = gtk.CheckButton(_('_Case sensitive'))
        self.chk_casesensitive.connect('toggled', self._refresh_proxy)
        # l10n: To read about what regular expressions are, see
        # http://en.wikipedia.org/wiki/Regular_expression
        self.chk_regex = gtk.CheckButton(_("_Regular expression"))
        self.chk_regex.connect('toggled', self._refresh_proxy)

        # Widgets for replace (second row)
        # l10n: This text label shows in front of the text box where the replacement
        # text is typed. Keep in mind that the text box will appear after this text.
        # If this sentence construction is hard to use, consdider translating this as
        # "Replacement"
        self.lbl_replace = gtk.Label(_('Replace with'))
        self.ent_replace = gtk.Entry()
        # l10n: Button text
        self.btn_replace = gtk.Button(_('Replace'))
        self.btn_replace.connect('clicked', self._on_replace_clicked)
        # l10n: Check box
        self.chk_replace_all = gtk.CheckButton(_('Replace _All'))

        self.widgets = [
            self.ent_search, self.btn_search, self.chk_casesensitive, self.chk_regex,
            self.lbl_replace, self.ent_replace, self.btn_replace, self.chk_replace_all
        ]

    def _setup_key_bindings(self):
        gtk.accel_map_add_entry("<Virtaal>/Edit/Search", gtk.keysyms.F3, 0)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Search Ctrl+F", gtk.keysyms.F, gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Search: Next", gtk.keysyms.G, gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Search: Previous", gtk.keysyms.G, gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK)

        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<Virtaal>/Edit/Search", self._on_start_search)
        self.accel_group.connect_by_path("<Virtaal>/Edit/Search Ctrl+F", self._on_start_search)
        self.accel_group.connect_by_path("<Virtaal>/Edit/Search: Next", self._on_search_next)
        self.accel_group.connect_by_path("<Virtaal>/Edit/Search: Previous", self._on_search_prev)

        self.controller.main_controller.view.add_accel_group(self.accel_group)


    # METHODS #
    def selected(self):
        # XXX: Assumption: This method is called when a new file is loaded and that is
        #      why we keep a reference to the store's cursor.
        self.storecursor = self.controller.main_controller.store_controller.cursor
        if not self.storecursor or not self.storecursor.model:
            return

        self._add_widgets()
        self._connect_highlighting()
        self._connect_textboxes()
        unitcont = self.controller.main_controller.unit_controller
        if self._unit_modified_id:
            unitcont.disconnect(self._unit_modified_id)
        self._unit_modified_id = unitcont.connect('unit-modified', self._on_unit_modified)
        if not self.ent_search.get_text():
            self.storecursor.indices = self.storecursor.model.stats['total']
        else:
            self.update_search()

        def grab_focus():
            curpos = self.ent_search.props.cursor_position
            self.ent_search.grab_focus()
            # that will select all text, so reset the cursor position
            self.ent_search.set_position(curpos)
            return False

        # FIXME: The following line is a VERY UGLY HACK, but at least it works.
        gobject.timeout_add(100, grab_focus)

    def select_match(self, match):
        """Select the specified match in the GUI."""
        main_controller = self.controller.main_controller
        main_controller.select_unit(match.unit)
        view = main_controller.unit_controller.view

        if match.part == 'target':
            textbox = view.targets[match.part_n]
        elif match.part == 'source':
            textbox = view.sources[match.part_n]

        if not textbox:
            return False

        # Wait for SearchMode to finish with its highlighting and stuff, and then we do...
        def select_match_text():
            textbox.grab_focus()
            buff = textbox.buffer
            buffstr = textbox.get_text()

            start, end = match.start, match.end
            if hasattr(textbox.elem, 'gui_info'):
                start_iter = textbox.elem.gui_info.treeindex_to_iter(start)
                end_iter = textbox.elem.gui_info.treeindex_to_iter(end, start_at=(start, start_iter))
            else:
                start_iter = buff.get_iter_at_offset(start)
                end_iter = buff.get_iter_at_offset(end)

            buff.select_range(end_iter, start_iter)
            return False

        # TODO: Implement for 'notes' and 'locations' parts
        gobject.idle_add(select_match_text)

    def replace_match(self, match, replace_str):
        main_controller = self.controller.main_controller
        unit_controller = main_controller.unit_controller
        # Using unit_controller directly is a hack to make sure that the replacement changes are immediately displayed.
        if match.part != 'target':
            return

        if unit_controller is None:
            if match.unit.hasplural():
                string_n = match.unit.target.strings[match.part_n]
                strings[match.part_n] = string_n[:match.start] + replace_str + string_n[match.end:]
                match.unit.target = strings
            else:
                rstring = match.unit.target
                rstring = rstring[:match.start] + replace_str + rstring[match.end:]
                match.unit.target = rstring
        else:
            main_controller.select_unit(match.unit)
            rstring = unit_controller.get_unit_target(match.part_n)
            unit_controller.set_unit_target(match.part_n, rstring[:match.start] + replace_str + rstring[match.end:])

    def update_search(self):
        from translate.tools.pogrep import GrepFilter
        self.filter = GrepFilter(
            searchstring=unicode(self.ent_search.get_text()),
            searchparts=('source', 'target'),
            ignorecase=not self.chk_casesensitive.get_active(),
            useregexp=self.chk_regex.get_active(),
            max_matches=self.MAX_RESULTS
        )
        store_units = self.storecursor.model.get_units()
        self.matches, indexes = self.filter.getmatches(store_units)
        self.matchcursor = Cursor(self.matches, range(len(self.matches)))

        logging.debug('Search text: %s (%d matches)' % (self.ent_search.get_text(), len(indexes)))

        if indexes:
            self.ent_search.modify_base(gtk.STATE_NORMAL, self.default_base)
            self.ent_search.modify_text(gtk.STATE_NORMAL, self.default_text)

            self.storecursor.indices = indexes
            # Select initial match for in the current unit.
            match_index = 0
            selected_unit = self.storecursor.model[self.storecursor.index]
            for match in self.matches:
                if match.unit is selected_unit:
                    break
                match_index += 1
            self.matchcursor.index = match_index
        else:
            if self.ent_search.get_text():
                self.ent_search.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(current_theme['warning_bg']))
                self.ent_search.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('#fff'))
            else:
                self.ent_search.modify_base(gtk.STATE_NORMAL, self.default_base)
                self.ent_search.modify_text(gtk.STATE_NORMAL, self.default_text)

            self.filter.re_search = None
            # Act like the "Default" mode...
            self.storecursor.indices = self.storecursor.model.stats['total']
        self._highlight_matches()

        def grabfocus():
            curpos = self.ent_search.props.cursor_position
            self.ent_search.grab_focus()
            # that will select all text, so reset the cursor position
            self.ent_search.set_position(curpos)
            return False
        gobject.idle_add(grabfocus)

    def unselected(self):
        # TODO: Unhightlight the previously selected unit
        if hasattr(self, '_signalid_cursor_changed'):
            self.storecursor.disconnect(self._signalid_cursor_changed)

        if hasattr(self, '_textbox_signals'):
            for textbox, signal_id in self._textbox_signals.items():
                textbox.disconnect(signal_id)

        if self._unit_modified_id:
            self.controller.main_controller.unit_controller.disconnect(self._unit_modified_id)
            self._unit_modified_id = 0

        self.matches = []

    def _add_widgets(self):
        table = self.controller.view.mode_box

        xoptions = gtk.FILL
        table.attach(self.ent_search, 2, 3, 0, 1, xoptions=xoptions)
        table.attach(self.btn_search, 3, 4, 0, 1, xoptions=xoptions)
        table.attach(self.chk_casesensitive, 4, 5, 0, 1, xoptions=xoptions)
        table.attach(self.chk_regex, 5, 6, 0, 1, xoptions=xoptions)

        table.attach(self.lbl_replace, 1, 2, 1, 2, xoptions=xoptions)
        table.attach(self.ent_replace, 2, 3, 1, 2, xoptions=xoptions)
        table.attach(self.btn_replace, 3, 4, 1, 2, xoptions=xoptions)
        table.attach(self.chk_replace_all, 4, 5, 1, 2, xoptions=xoptions)

        table.show_all()

    def _connect_highlighting(self):
        self._signalid_cursor_changed = self.storecursor.connect('cursor-changed', self._on_cursor_changed)

    def _connect_textboxes(self):
        self._textbox_signals = {}
        for textbox in self.unitview.sources + self.unitview.targets:
            self._textbox_signals[textbox] = textbox.connect(
                'refreshed', self._on_textbox_refreshed
            )

    def _get_matches_for_unit(self, unit):
        return [match for match in self.matches if match.unit is unit]

    def _get_unit_matches_dict(self):
        d = {}
        for match in self.matches:
            if match.unit not in d:
                d[match.unit] = []
            d[match.unit].append(match)
        return d

    def _highlight_matches(self):
        if getattr(self.filter, 're_search', None) is None:
            return

        for textbox in self.unitview.sources + self.unitview.targets:
            if textbox.props.visible:
                self._highlight_textbox_matches(textbox)

    def _get_matches_for_textbox(self, textbox):
        role = textbox.role
        unit = self.unitview.unit
        if role == 'source':
            textbox_n = self.unitview.sources.index(textbox)
        elif role == 'target':
            textbox_n = self.unitview.targets.index(textbox)
        else:
            raise ValueError('Could not find text box in sources or targets: %s' % (textbox))
        return [
            m for m in self.matches
            if m.unit is unit and \
                m.part == role and \
                m.part_n == textbox_n
        ]

    def _highlight_textbox_matches(self, textbox, select_match=True):
        buff = textbox.buffer
        buffstr = textbox.get_text()

        # Make sure the 'search_highlight' tag in the textbox's tag table
        # is "fresh".
        try:
            tagtable = buff.get_tag_table()
            tag = tagtable.lookup('search_highlight')
            if tag:
                tagtable.remove(tag)
            tagtable.add(self._make_highlight_tag())
        except ValueError, ve:
            logging.exception("(Re-)adding search highlighting tag exception:")

        select_iters = []

        # We keep the iterator and index pointing to the end of the previous
        # match so that we continue searching from there for the next match.
        end_iter = None
        old_end = -1

        for match in self._get_matches_for_textbox(textbox):
            start, end = match.start, match.end
            if hasattr(textbox.elem, 'gui_info'):
                if end_iter:
                    start_iter = textbox.elem.gui_info.treeindex_to_iter(start, start_at=(old_end, end_iter))
                else:
                    start_iter = textbox.elem.gui_info.treeindex_to_iter(start)
                end_iter   = textbox.elem.gui_info.treeindex_to_iter(end, start_at=(start, start_iter))
                old_end = end
            else:
                start_iter, end_iter = buff.get_iter_at_offset(start), buff.get_iter_at_offset(end)
                old_end = end
            buff.apply_tag_by_name('search_highlight', start_iter, end_iter)

            if select_match and textbox.role == 'target' and not select_iters and self.select_first_match:
                select_iters = [start_iter, end_iter]

        if select_iters:
            buff.select_range(select_iters[1], select_iters[0])

    def _make_highlight_tag(self):
        tag = gtk.TextTag(name='search_highlight')
        tag.set_property('background', 'yellow')
        tag.set_property('foreground', 'black')
        return tag

    def _move_match(self, offset):
        if self.controller.current_mode is not self:
            return

        if getattr(self, 'matchcursor', None) is None:
            self.update_search()
            self._move_match(offset)
            return

        old_match_index = self.matchcursor.index
        if not self.matches or old_match_index != self.matchcursor.index:
            self.update_search()
            return

        self.matchcursor.move(offset)
        self.select_match(self.matches[self.matchcursor.index])

    def _replace_all(self):
        self.controller.main_controller.undo_controller.record_start()

        repl_str = self.ent_replace.get_text()
        unit_matches = self._get_unit_matches_dict()

        for unit, matches in unit_matches.items():
            for match in reversed(matches):
                self.replace_match(match, repl_str)

        self.controller.main_controller.undo_controller.record_stop()
        self.update_search()


    # EVENT HANDLERS #
    def _on_entry_activate(self, entry):
        self.update_search()
        self._move_match(0) # Select the current match.

    def _on_cursor_changed(self, cursor):
        assert cursor is self.storecursor

        self._highlight_matches()

    def _on_replace_clicked(self, btn):
        if not self.storecursor or not self.ent_search.get_text() or not self.ent_replace.get_text():
            return
        self.update_search()

        if self.chk_replace_all.get_active():
            self._replace_all()
        else:
            current_unit = self.storecursor.deref()
            # Find matches in the current unit.
            unit_matches = [match for match in self.matches if match.unit is current_unit and match.part == 'target']
            if len(unit_matches) > 0:
                i = self.matches.index(unit_matches[0])
                self.controller.main_controller.undo_controller.record_start()
                self.replace_match(unit_matches[0], self.ent_replace.get_text())
                self.controller.main_controller.undo_controller.record_stop()
                # FIXME: The following is necessary to avoid an IndexError in
                # del in certain circumstances. I'm not sure why it happens,
                # but I suspect it has something to do with self.matches not
                # being updated as expected after an undo.
                if 0 <= i < len(self.matches):
                    del self.matches[i]
            elif self.filter.re_search:
                # If there is no current search, we don't want to advance and
                # give the impression that we replaced something (bug 1636)
                self.storecursor.move(1)

        self.update_search()

    def _on_search_clicked(self, btn):
        self._move_match(1)

    def _on_search_next(self, *args):
        # FIXME: Remove the following check when these actions are connected to menu items.
        if self.controller.main_controller.store_controller.store is None:
            return
        self._move_match(1)

    def _on_search_prev(self, *args):
        # FIXME: Remove the following check when these actions are connected to menu items.
        if self.controller.main_controller.store_controller.store is None:
            return
        self._move_match(-1)

    def _on_search_text_changed(self, entry):
        if self._search_timeout:
            gobject.source_remove(self._search_timeout)
            self._search_timeout = 0

        self._search_timeout = gobject.timeout_add(self.SEARCH_DELAY, self.update_search)

    def _on_start_search(self, _accel_group, _acceleratable, _keyval, _modifier):
        """This is called via the accelerator."""
        # FIXME: Remove the following check when these actions are connected to menu items.
        if self.controller.main_controller.store_controller.store is None:
            return
        self.controller.select_mode(self)

    def _on_style_set(self, widget, prev_style):
        self.default_base = widget.style.base[gtk.STATE_NORMAL]
        self.default_text = widget.style.text[gtk.STATE_NORMAL]
        self.ent_search.modify_base(gtk.STATE_NORMAL, self.default_base)
        self.ent_search.modify_text(gtk.STATE_NORMAL, self.default_text)

    def _on_textbox_refreshed(self, textbox, elem):
        """Redoes highlighting after a C{StringElem} render destoyed it."""
        if not textbox.props.visible or not unicode(elem):
            return

        self._highlight_textbox_matches(textbox, select_match=False)

    def _on_unit_modified(self, unit_controller, current_unit):
        unit_matches = self._get_matches_for_unit(current_unit)
        for match in unit_matches:
            if not self.filter.re_search.match(match.get_getter()()[match.start:match.end]):
                logging.debug('Match to remove: %s' % (match))
                self.matches.remove(match)
                self.matchcursor.indices = range(len(self.matches))

    def _refresh_proxy(self, *args):
        self.update_search()

########NEW FILE########
__FILENAME__ = workflowmode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import gtk

from virtaal.views.widgets.popupmenubutton import PopupMenuButton, POS_NW_SW

from basemode import BaseMode


class WorkflowMode(BaseMode):
    """Workflow mode - Include units based on its workflow state, as specified
        by the user."""

    name = 'Workflow'
    display_name = _("Workflow")
    widgets = []

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.ModeController
            @param controller: The ModeController that managing program modes."""
        self.controller = controller
        self.filter_states = []
        self._menuitem_states = {}


    # METHODS #
    def selected(self):
        self.storecursor = self.controller.main_controller.store_controller.cursor

        self.state_names = self.controller.main_controller.unit_controller.get_unit_state_names()
        if self.storecursor and self.storecursor.model and 'extended' in self.storecursor.model.stats:
            self.state_names = [i for i in self.state_names.items() if i[0] in self.storecursor.model.stats['extended']]
        else:
            self.state_names = self.state_names.items()

        self.state_names.sort(key=lambda x: x[0])

        self._add_widgets()
        self._update_button_label()
        if not self.state_names:
            self._disable()
        self.update_indices()

    def unselected(self):
        pass

    def update_indices(self):
        if not self.storecursor or not self.storecursor.model:
            return

        indices = []
        for state in self.filter_states:
            indices.extend(self.storecursor.model.stats['extended'][state])

        if not indices:
            indices.extend(self.storecursor.model.stats['total'])
        else:
            indices.sort()

        self.storecursor.indices = indices

    def _add_widgets(self):
        table = self.controller.view.mode_box
        self.btn_popup = PopupMenuButton(menu_pos=POS_NW_SW)
        self.btn_popup.set_relief(gtk.RELIEF_NORMAL)
        self.btn_popup.set_menu(self._create_state_menu())

        self.widgets = [self.btn_popup]

        xoptions = gtk.FILL
        table.attach(self.btn_popup, 2, 3, 0, 1, xoptions=xoptions)

        table.show_all()

    def _create_state_menu(self):
        menu = gtk.Menu()

        for iid, name in self.state_names:
            menuitem = gtk.CheckMenuItem(label=name)
            menuitem.show()
            self._menuitem_states[menuitem] = iid
            menuitem.connect('toggled', self._on_state_menuitem_toggled)
            menu.append(menuitem)
        return menu

    def _update_button_label(self):
        state_labels = [mi.child.get_label() for mi in self.btn_popup.menu if mi.get_active()]
        btn_label = u''
        if not state_labels:
            #l10n: This is the button where the user can select units by workflow state
            btn_label = _(u'Select States')
        elif len(state_labels) == len(self.state_names):
            #l10n: This refers to workflow states
            btn_label = _(u'All States')
        else:
            btn_label = u', '.join(state_labels[:3])
            if len(state_labels) > 3:
                btn_label += u'...'
        self.btn_popup.set_label(btn_label)

    def _disable(self):
        """Disable the widgets (workflow not possible now)."""
        self.btn_popup.set_sensitive(False)

    # EVENT HANDLERS #
    def _on_state_menuitem_toggled(self, checkmenuitem):
        self.filter_states = []
        for menuitem in self.btn_popup.menu:
            if not isinstance(menuitem, gtk.CheckMenuItem) or not menuitem.get_active():
                continue
            if menuitem in self._menuitem_states:
                self.filter_states.append(self._menuitem_states[menuitem])
        self.update_indices()
        self._update_button_label()

########NEW FILE########
__FILENAME__ = autocompletor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""Contains the AutoCompletor class."""

import gobject
import re
try:
    from collections import defaultdict
except ImportError:
    class defaultdict(dict):
        def __init__(self, default_factory=lambda: None):
            self.__factory = default_factory

        def __getitem__(self, key):
            if key in self:
                return super(defaultdict, self).__getitem__(key)
            else:
                return self.__factory()

from virtaal.controllers.baseplugin import BasePlugin
from virtaal.views.widgets.textbox import TextBox


class AutoCompletor(object):
    """
    Does auto-completion of registered words in registered widgets.
    """

    wordsep_re = re.compile(r'\W+', re.UNICODE)

    MAX_WORDS = 10000
    DEFAULT_COMPLETION_LENGTH = 4 # The default minimum length of a word that may
                                  # be auto-completed.

    def __init__(self, main_controller, word_list=[], comp_len=DEFAULT_COMPLETION_LENGTH):
        """Constructor.

            @type  word_list: iterable
            @param word_list: A list of words that should be auto-completed."""
        self.main_controller = main_controller
        assert isinstance(word_list, list)
        self.comp_len = comp_len
        self.clear_words()
        self.add_words(word_list)
        self.widgets = set()

    def add_widget(self, widget):
        """Add a widget to the list of widgets to do auto-completion for."""
        if widget in self.widgets:
            return # Widget already added

        if isinstance(widget, TextBox):
            self._add_text_box(widget)
            return

        raise ValueError("Widget type %s not supported." % (type(widget)))

    def add_words(self, words, update=True):
        """Add a word or words to the list of words to auto-complete."""
        for word in words:
            if self.isusable(word):
                self._word_freq[word] += 1
        if update:
            self._update_word_list()

    def add_words_from_units(self, units):
        """Collect all words from the given translation units to use for
            auto-completion.

            @type  units: list
            @param units: The translation units to collect words from.
            """
        for unit in units:
            target = unit.target
            if not target:
                continue
            self.add_words(self.wordsep_re.split(target), update=False)
            if len(self._word_freq) > self.MAX_WORDS:
                break

        self._update_word_list()

    def autocomplete(self, word):
        for w in self._word_list:
            if w.startswith(word):
                return w, w[len(word):]
        return None, u''

    def clear_widgets(self):
        """Release all registered widgets from the spell of auto-completion."""
        for w in set(self.widgets):
            self.remove_widget(w)

    def clear_words(self):
        """Remove all registered words; effectively turns off auto-completion."""
        self._word_list = []
        self._word_freq = defaultdict(lambda: 0)

    def isusable(self, word):
        """Returns a value indicating if the given word should be kept as a
        suggestion for autocomplete."""
        return len(word) > self.comp_len + 2

    def remove_widget(self, widget):
        """Remove a widget (currently only L{TextBox}s are accepted) from
            the list of widgets to do auto-correction for.
            """
        if isinstance(widget, TextBox) and widget in self.widgets:
            self._remove_textbox(widget)

    def remove_words(self, words):
        """Remove a word or words from the list of words to auto-complete."""
        if isinstance(words, basestring):
            del self._word_freq[words]
            self._word_list.remove(words)
        else:
            for w in words:
                try:
                    del self._word_freq[w]
                    self._word_list.remove(w)
                except KeyError:
                    pass

    def _add_text_box(self, textbox):
        """Add the given L{TextBox} to the list of widgets to do auto-
            correction on."""
        if not hasattr(self, '_textbox_insert_ids'):
            self._textbox_insert_ids = {}
        handler_id = textbox.connect('text-inserted', self._on_insert_text)
        self._textbox_insert_ids[textbox] = handler_id
        self.widgets.add(textbox)

    def _on_insert_text(self, textbox, text, offset, elem):
        if not isinstance(text, basestring) or self.wordsep_re.match(text):
            return
        # We are only interested in single character insertions, otherwise we
        # react similarly for paste and similar events
        if len(text) > 1:
            return

        prefix = unicode(textbox.get_text(0, offset) + text)
        postfix = unicode(textbox.get_text(offset))
        buffer = textbox.buffer

        # Quick fix to check that we don't autocomplete in the middle of a word.
        right_lim = len(postfix) > 0 and postfix[0] or ' '
        if not self.wordsep_re.match(right_lim):
            return

        lastword = self.wordsep_re.split(prefix)[-1]

        if len(lastword) >= self.comp_len:
            completed_word, word_postfix = self.autocomplete(lastword)
            if completed_word == lastword:
                return

            if completed_word:
                # Updating of the buffer is deferred until after this signal
                # and its side effects are taken care of. We abuse
                # gobject.idle_add for that.
                insert_offset = offset + 1 # len(text) == 1
                def suggest_completion():
                    textbox.handler_block(self._textbox_insert_ids[textbox])
                    #logging.debug("textbox.suggestion = {'text': u'%s', 'offset': %d}" % (word_postfix, insert_offset))
                    textbox.suggestion = {'text': word_postfix, 'offset': insert_offset}
                    textbox.handler_unblock(self._textbox_insert_ids[textbox])

                    sel_iter_start = buffer.get_iter_at_offset(insert_offset)
                    sel_iter_end   = buffer.get_iter_at_offset(insert_offset + len(word_postfix))
                    buffer.select_range(sel_iter_start, sel_iter_end)

                    return False

                gobject.idle_add(suggest_completion, priority=gobject.PRIORITY_HIGH)

    def _remove_textbox(self, textbox):
        """Remove the given L{TextBox} from the list of widgets to do
            auto-correction on.
            """
        if not hasattr(self, '_textbox_insert_ids'):
            return
        # Disconnect the "insert-text" event handler
        textbox.disconnect(self._textbox_insert_ids[textbox])

        self.widgets.remove(textbox)

    def _update_word_list(self):
        """Update and sort found words according to frequency."""
        wordlist = self._word_freq.items()
        wordlist.sort(key=lambda x:x[1], reverse=True)
        self._word_list = [items[0] for items in wordlist]


class Plugin(BasePlugin):
    description = _('Automatically complete long words while you type')
    display_name = _('AutoCompletor')
    version = 0.1

    # INITIALIZERS #
    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name
        self.main_controller = main_controller

        self._init_plugin()

    def _init_plugin(self):
        from virtaal.common import pan_app
        self.autocomp = AutoCompletor(self.main_controller)

        self._store_loaded_id = self.main_controller.store_controller.connect('store-loaded', self._on_store_loaded)

        if self.main_controller.store_controller.get_store():
            # Connect to already loaded store. This happens when the plug-in is enabled after loading a store.
            self._on_store_loaded(self.main_controller.store_controller)

        self._unitview_id = None
        unitview = self.main_controller.unit_controller.view
        if unitview.targets:
            self._connect_to_textboxes(unitview, unitview.targets)
        else:
            self._unitview_id = unitview.connect('targets-created', self._connect_to_textboxes)

    def _connect_to_textboxes(self, unitview, textboxes):
        for target in textboxes:
                self.autocomp.add_widget(target)

    # METHDOS #
    def destroy(self):
        """Remove all signal-connections."""
        self.autocomp.clear_words()
        self.autocomp.clear_widgets()
        self.main_controller.store_controller.disconnect(self._store_loaded_id)
        if getattr(self, '_cursor_changed_id', None):
            self.store_cursor.disconnect(self._cursor_changed_id)
        if self._unitview_id:
            self.main_controller.unit_controller.view.disconnect(self._unitview_id)


    # EVENT HANDLERS #
    def _on_cursor_change(self, cursor):
        def add_widgets():
            if hasattr(self, 'lastunit'):
                if self.lastunit.hasplural():
                    for target in self.lastunit.target:
                        if target:
                            #logging.debug('Adding words: %s' % (self.autocomp.wordsep_re.split(unicode(target))))
                            self.autocomp.add_words(self.autocomp.wordsep_re.split(unicode(target)))
                else:
                    if self.lastunit.target:
                        #logging.debug('Adding words: %s' % (self.autocomp.wordsep_re.split(unicode(self.lastunit.target))))
                        self.autocomp.add_words(self.autocomp.wordsep_re.split(unicode(self.lastunit.target)))
            self.lastunit = cursor.deref()
        gobject.idle_add(add_widgets)

    def _on_store_loaded(self, storecontroller):
        self.autocomp.add_words_from_units(storecontroller.get_store().get_units())

        if hasattr(self, '_cursor_changed_id'):
            self.store_cursor.disconnect(self._cursor_changed_id)
        self.store_cursor = storecontroller.cursor
        self._cursor_changed_id = self.store_cursor.connect('cursor-changed', self._on_cursor_change)
        self._on_cursor_change(self.store_cursor)

########NEW FILE########
__FILENAME__ = autocorrector
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""Contains the AutoCorrector class."""

import gobject
import logging
import os
import re
import zipfile

from virtaal.common import pan_app
from virtaal.controllers.baseplugin import BasePlugin
from virtaal.views.widgets.textbox import TextBox


class AutoCorrector(object):
    """
    Does auto-correction on editable text widgets using OpenOffice.org auto-
    correction files.
    """

    wordsep_re = re.compile('\W+', re.UNICODE)

    REPLACEMENT, REGEX = range(2)

    def __init__(self, main_controller, lang='', acorpath=None):
        """Create a new AutoCorrector instance and load the OpenOffice.org
            auto-correction diction for language code 'lang'.

            @type  lang: str
            @param lang: The code of the language to load auto-correction data
                for. See M{load_dictionary} for more information about how this
                parameter is used.
            @type  acorpath: str
            @param acorpath: The path to the directory containing the
                OpenOffice.org auto-correction data files (acor_*.dat).
            """
        self.main_controller = main_controller
        self.lang = None
        if acorpath is None or not os.path.isdir(acorpath):
            acorpath = os.path.curdir
        self.acorpath = acorpath
        self.load_dictionary(lang)
        self.widgets = set()

    def add_widget(self, widget):
        """Add a widget (currently only C{TextBox}s are accepted) to the
            list of widgets to do auto-correction for.
            """
        if not self.correctiondict:
            return # No dictionary to work with, so we can't handle any widgets

        if widget in self.widgets:
            return # Widget already added

        if isinstance(widget, TextBox):
            self._add_textbox(widget)
            return

        raise ValueError("Widget type %s not supported." % (type(widget)))

    def autocorrect(self, src, endindex, inserted=u''):
        """Apply auto-correction to source string.

            @type  src: basestring
            @param src: The candidate-string for auto-correction.
            @type  endindex: int
            @param endindex: The logical end of the string. ie. The part of the
                string _before_ this index tested for the presence of a
                correctable string.
            @type  inserted: basestring
            @param inserted: The string that was inserted at I{endindex}

            @rtype: 2-tuple
            @return: The range in C{src} to be changed (or C{None} if no
                correction was found) as well as the string to replace that
                range with.
            """
        if not self.correctiondict:
            return None, u''

        candidate = src[:endindex]

        for key in self.correctiondict:
            mobj = self.correctiondict[key][self.REGEX].search(candidate)
            if mobj:
                replace_range = mobj.start(), mobj.end()
                replacement = self.correctiondict[key][self.REPLACEMENT]
                return replace_range, replacement

        return None, u'' # No corrections done

    def clear_widgets(self):
        """Removes references to all widgets that is being auto-corrected."""
        for w in set(self.widgets):
            self.remove_widget(w)

    def load_dictionary(self, lang):
        """Load the OpenOffice.org auto-correction dictionary for language
            'lang'.

            OpenOffice.org's auto-correction data files are in named in the
            format "acor_I{lang}-I{country}.dat", where I{lang} is the ISO
            language code and I{country} the country code. This function can
            handle (for example) "af", "af_ZA" or "af-ZA" to load the Afrikaans
            data file. Here are the steps taken in trying to find the correct
            data file:
              - Underscores are replaced with hyphens in C{lang} ("af_ZA" ->
                "af-ZA").
              - The file for C{lang} is opened ("acor_af-ZA.dat").
              - If the open fails, the language code ("af") is extracted and the
                first file found starting with "acor_af" and ending in ".dat" is
                used.

            These steps imply that if "af" is given as lang, the data file
            "acor_af-ZA.dat" will end up being loaded.
            """
        # Change "af_ZA" to "af-ZA", which OOo uses to store acor files.
        if lang == self.lang:
            return

        if not lang:
            self.correctiondict = {}
            self.lang = ''
            return

        lang = lang.replace('_', '-')
        try:
            acor = zipfile.ZipFile(os.path.join(self.acorpath, 'acor_%s.dat' % lang))
        except IOError, _exc:
            # Try to find a file that starts with 'acor_%s' % (lang[0]) (where
            # lang[0] is the part of lang before the '-') and ends with '.dat'
            langparts = lang.split('-')
            filenames = [fn for fn in os.listdir(self.acorpath) if fn.startswith('acor_%s' % langparts[0])
                                                                   and fn.endswith('.dat')]
            for fn in filenames:
                try:
                    acor = zipfile.ZipFile(os.path.join(self.acorpath, fn))
                    break
                except IOError:
                    logging.exception('Unable to load auto-correction data file for language %s' % (lang))

            else:
                # If no acceptable auto-correction file was found, we create an
                # empty dictionary.
                self.correctiondict = {}
                self.lang = ''
                return

        xmlstr = acor.read('DocumentList.xml')
        from lxml import etree
        xml = etree.fromstring(xmlstr)
        # Sample element from DocumentList.xml (it has no root element!):
        #   <block-list:block block-list:abbreviated-name="teh" block-list:name="the"/>
        # This means that xml.iterchildren() will return an iterator over all
        # of <block-list> elements and entry.values() will return a 2-tuple
        # with the values of the "abbreviated-name" and "name" attributes.
        # That is how I got to the simple line below.
        self.correctiondict = dict([entry.values() for entry in xml.iterchildren()])

        # Add auto-correction regex for each loaded word.
        for key, value in self.correctiondict.items():
            self.correctiondict[key] = (unicode(value), re.compile(r'\b%s$' % (re.escape(key)), re.UNICODE))

        self.lang = lang
        return

    def remove_widget(self, widget):
        """Remove a widget (currently only C{TextBox}es are accepted) from
            the list of widgets to do auto-correction for.
            """
        if not self.correctiondict:
            return

        if isinstance(widget, TextBox) and widget in self.widgets:
            self._remove_textbox(widget)

    def set_widgets(self, widget_collection):
        """Replace the widgets being auto-corrected with the collection given."""
        self.clear_widgets()
        for w in widget_collection:
            self.add_widget(w)

    def _add_textbox(self, textbox):
        """Add the given C{TextBox} to the list of widgets to do auto-
            correction on.
            """
        if not hasattr(self, '_textbox_handler_ids'):
            self._textbox_handler_ids = {}

        handler_id = textbox.connect(
            'text-inserted',
            self._on_insert_text
        )
        self._textbox_handler_ids[textbox] = handler_id
        self.widgets.add(textbox)

    def _on_insert_text(self, textbox, text, cursorpos, elem):
        if not isinstance(text, basestring):
            return
        if not self.wordsep_re.split(text)[-1]:
            bufftext = unicode(elem)
            offset = elem.gui_info.gui_to_tree_index(cursorpos)
            reprange, replacement = self.autocorrect(bufftext, offset, text)
            if reprange is not None:
                # Updating of the buffer is deferred until after this signal
                # and its side effects are taken care of. We abuse
                # gobject.idle_add for that.
                def correct_text():
                    buffer = textbox.buffer
                    start_iter = elem.gui_info.treeindex_to_iter(reprange[0])
                    end_iter = elem.gui_info.treeindex_to_iter(reprange[1], (reprange[0], start_iter))

                    self.main_controller.undo_controller.record_start()
                    buffer.delete(start_iter, end_iter)
                    buffer.insert(end_iter, replacement)
                    self.main_controller.undo_controller.record_stop()

                    newcursorpos = elem.gui_info.tree_to_gui_index(reprange[0]) + len(replacement) + len(text)
                    def refresh():
                        textbox.refresh_cursor_pos = newcursorpos
                        textbox.refresh()
                    gobject.idle_add(refresh)
                    return False

                gobject.idle_add(correct_text)

    def _remove_textbox(self, textbox):
        """Remove the given C{TextBox} from the list of widgets to do
            auto-correction on.
            """
        if not hasattr(self, '_textbox_handler_ids'):
            return
        # Disconnect the "insert-text" event handler
        textbox.disconnect(self._textbox_handler_ids[textbox])
        self.widgets.remove(textbox)


class Plugin(BasePlugin):
    description = _('Automatically correct text while you type')
    display_name = _('AutoCorrector')
    version = 0.1

    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name
        self.main_controller = main_controller

        self._init_plugin()

    def _init_plugin(self):
        self.autocorr = AutoCorrector(self.main_controller, acorpath=pan_app.get_abs_data_filename(['virtaal', 'autocorr']))

        def on_cursor_change(cursor):
            def add_widgets():
                self.autocorr.clear_widgets()
                for target in self.main_controller.unit_controller.view.targets:
                    self.autocorr.add_widget(target)
                return False
            gobject.idle_add(add_widgets)

        def on_store_loaded(storecontroller):
            self.autocorr.load_dictionary(lang=self.main_controller.lang_controller.target_lang.code)

            if getattr(self, '_cursor_changed_id', None):
                self.store_cursor.disconnect(self._cursor_changed_id)
            self.store_cursor = storecontroller.cursor
            self._cursor_changed_id = self.store_cursor.connect('cursor-changed', on_cursor_change)
            on_cursor_change(self.store_cursor)

        def on_target_lang_changed(lang_controller, lang):
            self.autocorr.load_dictionary(lang)
            # If the previous language didn't have a correction list, we might
            # have never attached, so let's make sure we attach.
            on_cursor_change(None)


        self._store_loaded_id = self.main_controller.store_controller.connect('store-loaded', on_store_loaded)

        if self.main_controller.store_controller.get_store():
            # Connect to already loaded store. This happens when the plug-in is enabled after loading a store.
            on_store_loaded(self.main_controller.store_controller)

        self._target_lang_changed_id = self.main_controller.lang_controller.connect('target-lang-changed', on_target_lang_changed)

    def destroy(self):
        """Remove all signal-connections."""
        self.autocorr.clear_widgets()
        self.main_controller.store_controller.disconnect(self._store_loaded_id)
        if getattr(self, '_cursor_changed_id', None):
            self.store_cursor.disconnect(self._cursor_changed_id)

########NEW FILE########
__FILENAME__ = lookupcontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import os

from virtaal.common import GObjectWrapper
from virtaal.controllers.basecontroller import BaseController
from virtaal.controllers.plugincontroller import PluginController

from lookupview import LookupView
from models.baselookupmodel import BaseLookupModel


class LookupController(BaseController):
    """The central connection between look-up back-ends and the rest of Virtaal."""

    __gtype_name__ = 'LookupController'
    __gsignals__ = {
        'lookup-query': (gobject.SIGNAL_RUN_FIRST, None, (object,))
    }

    # INITIALIZERS #
    def __init__(self, plugin, config):
        GObjectWrapper.__init__(self)

        self.config = config
        self.main_controller = plugin.main_controller
        self.plugin = plugin

        self.disabled_model_names = ['baselookupmodel'] + self.config.get('disabled_models', [])
        self._signal_ids = {}
        self.view = LookupView(self)
        self._load_models()

    def _load_models(self):
        self.plugin_controller = PluginController(self, 'LookupModel')
        self.plugin_controller.PLUGIN_CLASS_INFO_ATTRIBS = ['display_name', 'description']
        new_dirs = []
        for dir in self.plugin_controller.PLUGIN_DIRS:
           new_dirs.append(os.path.join(dir, 'lookup', 'models'))
        self.plugin_controller.PLUGIN_DIRS = new_dirs

        self.plugin_controller.PLUGIN_INTERFACE = BaseLookupModel
        self.plugin_controller.PLUGIN_MODULES = ['virtaal_plugins.lookup.models', 'virtaal.plugins.lookup.models']
        self.plugin_controller.get_disabled_plugins = lambda *args: self.disabled_model_names

        self.plugin_controller.load_plugins()


    # METHODS #
    def destroy(self):
        self.view.destroy()
        self.plugin_controller.shutdown()

########NEW FILE########
__FILENAME__ = lookupview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import gtk

from virtaal.views.baseview import BaseView
from virtaal.views.widgets.selectdialog import SelectDialog


class LookupView(BaseView):
    """
    Makes look-up models accessible via the source- and target text views'
    context menu.
    """

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        self.lang_controller = controller.main_controller.lang_controller

        self._textbox_ids = []
        self._unitview_ids = []
        unitview = controller.main_controller.unit_controller.view
        if unitview.sources:
            self._connect_to_textboxes(unitview, unitview.sources)
        else:
            self._unitview_ids.append(unitview.connect('sources-created', self._connect_to_textboxes))
        if unitview.targets:
            self._connect_to_textboxes(unitview, unitview.targets)
        else:
            self._unitview_ids.append(unitview.connect('targets-created', self._connect_to_textboxes))

    def _connect_to_textboxes(self, unitview, textboxes):
        for textbox in textboxes:
            self._textbox_ids.append((
                textbox,
                textbox.connect('populate-popup', self._on_populate_popup)
            ))


    # METHODS #
    def destroy(self):
        for id in self._unitview_ids:
            self.controller.main_controller.unit_controller.view.disconnect(id)
        for textbox, id in self._textbox_ids:
            textbox.disconnect(id)

    def select_backends(self, parent):
        selectdlg = SelectDialog(
            #l10n: The 'services' here refer to different look-up plugins,
            #such as web look-up, etc.
            title=_('Select Look-up Services'),
            message=_('Select the services that should be used to perform look-ups'),
            size=(self.controller.config['backends_dialog_width'], 200)
        )
        if isinstance(parent, gtk.Window):
            selectdlg.set_transient_for(parent)
            selectdlg.set_icon(parent.get_icon())

        items = []
        plugin_controller = self.controller.plugin_controller
        for plugin_name in plugin_controller._find_plugin_names():
            if plugin_name == 'baselookupmodel':
                continue
            try:
                info = plugin_controller.get_plugin_info(plugin_name)
            except Exception, e:
                logging.debug('Problem getting information for plugin %s' % plugin_name)
                continue
            enabled = plugin_name in plugin_controller.plugins
            config = enabled and plugin_controller.plugins[plugin_name].configure_func or None

            items.append({
                'name': info['display_name'],
                'desc': info['description'],
                'data': {'internal_name': plugin_name},
                'enabled': enabled,
                'config': config,
            })

        def item_enabled(dlg, item):
            internal_name = item['data']['internal_name']
            plugin_controller.enable_plugin(internal_name)
            if internal_name in self.controller.config['disabled_models']:
                self.controller.config['disabled_models'].remove(internal_name)

        def item_disabled(dlg, item):
            internal_name = item['data']['internal_name']
            plugin_controller.disable_plugin(internal_name)
            if internal_name not in self.controller.config['disabled_models']:
                self.controller.config['disabled_models'].append(internal_name)

        selectdlg.connect('item-enabled',  item_enabled)
        selectdlg.connect('item-disabled', item_disabled)
        selectdlg.run(items=items)


    # SIGNAL HANDLERS #
    def _on_lookup_selected(self, menuitem, plugin, query, query_is_source):
        plugin.lookup(query, query_is_source, srclang, tgtlang)

    def _on_populate_popup(self, textbox, menu):
        buf = textbox.buffer
        if not buf.get_has_selection():
            return

        selection = buf.get_text(*buf.get_selection_bounds()).strip()
        role      = textbox.role
        srclang   = self.lang_controller.source_lang.code
        tgtlang   = self.lang_controller.target_lang.code

        lookup_menu = gtk.Menu()
        menu_item = gtk.MenuItem(_('Look-up "%(selection)s"') % {'selection': selection})

        plugins = self.controller.plugin_controller.plugins
        menu_items = []
        names = plugins.keys()
        names.sort()
        for name in names:
            menu_items.extend(
                plugins[name].create_menu_items(selection, role, srclang, tgtlang)
            )
        if not menu_items:
            return

        for i in menu_items:
            lookup_menu.append(i)

        sep = gtk.SeparatorMenuItem()
        sep.show()
        menu.append(sep)
        menu_item.set_submenu(lookup_menu)
        menu_item.show_all()
        menu.append(menu_item)

########NEW FILE########
__FILENAME__ = baselookupmodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from virtaal.models.basemodel import BaseModel


class BaseLookupModel(object):
    """The base interface to be implemented by all look-up backend models."""

    description = ""
    """A description of the backend. This will be displayed to users."""
    display_name = None
    """The backend's name, suitable for display."""

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        """Initialise the model."""
        raise NotImplementedError()


    # METHODS #
    def create_menu_items(self, query, role, srclang, tgtlang):
        """Create the a list C{gtk.MenuItem}s for the given parameters.

        @type  query: basestring
        @param query: The string to use in the look-up.
        @type  query_is_src: bool
        @param query_is_src: C{True} if C{query} is from a source text box. C{False} otherwise.
        @type  srclang: str
        @param srclang: The language code of the source language.
        @type  tgtlang: str
        @param tgtlang: The language code of the target language."""
        raise NotImplementedError()

    def destroy(self):
        pass

########NEW FILE########
__FILENAME__ = weblookup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
# Copyright 2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import pango
import urllib
from os import path

from virtaal.common import pan_app
from virtaal.views.baseview import BaseView

try:
    from virtaal.plugins.lookup.models.baselookupmodel import BaseLookupModel
except ImportError:
    from virtaal_plugins.lookup.models.baselookupmodel import BaseLookupModel


class LookupModel(BaseLookupModel):
    """Look-up the selected string on the web."""

    __gtype_name__ = 'WebLookupModel'
    #l10n: plugin name
    display_name = _('Web Look-up')
    description = _('Look-up the selected text on a web site')

    URLDATA = [
        {
            'display_name': _('Google'),
            'url': 'http://www.google.com/search?q=%(query)s',
            'quoted': True,
        },
        {
            'display_name': _('Wikipedia'),
            'url': 'http://%(querylang)s.wikipedia.org/wiki/%(query)s',
            'quoted': False,
        },
    ]
    """A list of dictionaries containing data about each URL:
    * C{display_name}: The name that will be shown in the context menu
    * C{url}: The actual URL that will be queried. See below for template
        variables.
    * C{quoted}: Whether or not the query string should be put in quotes (").

    Valid template variables in 'url' fields are:
    * C{%(query)s}: The selected text that makes up the look-up query.
    * C{%(querylang)s}: The language of the query string (one of C{%(srclang)s}
        or C{%(tgtlang)s}).
    * C{%(nonquerylang)s}: The source- or target language which is B{not} the
        language that the query (selected text) is in.
    * C{%(srclang)s}: The currently selected source language.
    * C{%(tgtlang)s}: The currently selected target language.
    """

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.controller = controller
        self.internal_name = internal_name

        self.configure_func = self.configure
        self.urldata_file = path.join(pan_app.get_config_dir(), "weblookup.ini")

        self._load_urldata()

    def _load_urldata(self):
        urls = pan_app.load_config(self.urldata_file).values()
        if urls:
            for u in urls:
                if 'quoted' in u:
                    u['quoted'] = u['quoted'] == 'True'
            self.URLDATA = urls


    # METHODS #
    def configure(self, parent):
        configure_dialog = WebLookupConfigDialog(parent.get_toplevel())
        configure_dialog.urldata = self.URLDATA
        configure_dialog.run()
        self.URLDATA = configure_dialog.urldata
        #logging.debug('New URL data: %s' % (self.URLDATA))

    def create_menu_items(self, query, role, srclang, tgtlang):
        querylang = role == 'source' and srclang or tgtlang
        nonquerylang = role != 'source' and srclang or tgtlang
        query = urllib.quote(query)
        items = []
        for urlinfo in self.URLDATA:
            uquery = query
            if 'quoted' in urlinfo and urlinfo['quoted']:
                uquery = '"' + uquery + '"'

            i = gtk.MenuItem(urlinfo['display_name'])
            lookup_str = urlinfo['url'] % {
                'query':        uquery,
                'querylang':    querylang,
                'nonquerylang': nonquerylang,
                'srclang':      srclang,
                'tgtlang':      tgtlang
            }
            i.connect('activate', self._on_lookup, lookup_str)
            items.append(i)
        return items

    def destroy(self):
        config = dict([ (u['display_name'], u) for u in self.URLDATA ])
        pan_app.save_config(self.urldata_file, config)


    # SIGNAL HANDLERS #
    def _on_lookup(self, menuitem, url):
        from virtaal.support.openmailto import open
        open(url)


class WebLookupConfigDialog(object):
    """Dialog manages the URLs used by the web look-up plug-in."""

    COL_NAME, COL_URL, COL_QUOTE, COL_DATA = range(4)

    # INITIALIZERS #
    def __init__(self, parent):
        self.gui = BaseView.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='WebLookupManager',
            domain='virtaal'
        )

        self._get_widgets()
        if isinstance(parent, gtk.Widget):
            self.dialog.set_transient_for(parent)
            self.dialog.set_icon(parent.get_toplevel().get_icon())

        self._init_widgets()
        self._init_treeview()

    def _get_widgets(self):
        widget_names = ('btn_url_add', 'btn_url_remove', 'tvw_urls')

        for name in widget_names:
            setattr(self, name, self.gui.get_object(name))

        self.dialog = self.gui.get_object('WebLookupManager')
        self.add_dialog = WebLookupAddDialog(self.dialog)

    def _init_treeview(self):
        self.lst_urls = gtk.ListStore(str, str, bool, object)
        self.tvw_urls.set_model(self.lst_urls)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('Name'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', self.COL_NAME)
        col.props.resizable = True
        col.set_sort_column_id(0)
        self.tvw_urls.append_column(col)

        cell = gtk.CellRendererText()
        cell.props.ellipsize = pango.ELLIPSIZE_MIDDLE
        col = gtk.TreeViewColumn(_('URL'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', self.COL_URL)
        col.props.resizable = True
        col.set_expand(True)
        col.set_sort_column_id(1)
        self.tvw_urls.append_column(col)

        cell = gtk.CellRendererToggle()
        cell.set_radio(False)
        #l10n: Whether the selected text should be surrounded by "quotes"
        col = gtk.TreeViewColumn(_('Quote Query'))
        col.pack_start(cell)
        col.add_attribute(cell, 'active', self.COL_QUOTE)
        self.tvw_urls.append_column(col)

    def _init_widgets(self):
        self.btn_url_add.connect('clicked', self._on_add_clicked)
        self.btn_url_remove.connect('clicked', self._on_remove_clicked)


    # ACCESSORS #
    def _get_urldata(self):
        return [row[self.COL_DATA] for row in self.lst_urls]
    def _set_urldata(self, value):
        self.lst_urls.clear()
        for url in value:
            self.lst_urls.append((url['display_name'], url['url'], url['quoted'], url))
    urldata = property(_get_urldata, _set_urldata)


    # METHODS #
    def run(self, parent=None):
        if isinstance(parent, gtk.Widget):
            self.dialog.set_transient_for(parent)

        self.dialog.show()
        self.dialog.run()
        self.dialog.hide()


    # SIGNAL HANDLERS #
    def _on_add_clicked(self, button):
        url = self.add_dialog.run()
        if url is None:
            return
        self.lst_urls.append((url['display_name'], url['url'], url['quoted'], url))

    def _on_remove_clicked(self, button):
        selected = self.tvw_urls.get_selection().get_selected()
        if not selected or not selected[1]:
            return
        selected[0].remove(selected[1])


class WebLookupAddDialog(object):
    """The dialog used to add URLs for the web look-up plug-in."""

    # INITIALIZERS #
    def __init__(self, parent):
        self.gui = BaseView.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='WebLookupAdd',
            domain='virtaal'
        )
        self._get_widgets()

        if isinstance(parent, gtk.Window):
            self.dialog.set_transient_for(parent)
            self.dialog.set_icon(parent.get_toplevel().get_icon())

    def _get_widgets(self):
        widget_names = ('btn_url_cancel', 'btn_url_ok', 'cbtn_url_quote', 'ent_url_name', 'ent_url')

        for name in widget_names:
            setattr(self, name, self.gui.get_object(name))

        self.dialog = self.gui.get_object('WebLookupAdd')


    # METHODS #
    def run(self):
        self.ent_url.set_text('')
        self.ent_url_name.set_text('')
        self.cbtn_url_quote.set_active(False)

        self.dialog.show()
        response = self.dialog.run()
        self.dialog.hide()

        if response != gtk.RESPONSE_OK:
            return None

        self.url = {
            'display_name':   self.ent_url_name.get_text(),
            'url':            self.ent_url.get_text(),
            'quoted':         self.cbtn_url_quote.get_active(),
        }
        return self.url

########NEW FILE########
__FILENAME__ = migration
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""Plugin to import data from other applications.

Currently there is some support for importing settings from Poedit and
Lokalize. Translation Memory can be imported from Poedit and Lokalize.
"""

try:
    import bsddb
except ImportError:
    bsddb = None
import ConfigParser
import logging
import os
import StringIO
import struct
import sys
from os import path
try:
    from sqlite3 import dbapi2
except ImportError:
    from pysqlite2 import dbapi2

from virtaal.common import pan_app
from virtaal.controllers.baseplugin import BasePlugin

from translate.storage.pypo import extractpoline
from translate.storage import tmdb


def _prepare_db_string(string):
    """Helper method needed by the Berkeley DB TM converters."""
    string = '"%s"' % string
    string = unicode(extractpoline(string), 'utf-8')
    return string

class Plugin(BasePlugin):
    description = _('Migrate settings from KBabel, Lokalize and/or Poedit to Virtaal.')
    display_name = _('Migration Assistant')
    version = 0.1

    default_config = {
        "tmdb": path.join(pan_app.get_config_dir(), "tm.db")
    }

    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name
        self.main_controller = main_controller
        self.load_config()
        self._init_plugin()

    def _init_plugin(self):
        message = _('Should Virtaal try to import settings and data from other applications?')
        must_migrate = self.main_controller.show_prompt(_('Import data from other applications?'), message)
        if not must_migrate:
            logging.debug('Migration not done due to user choice')
        else:
            # We'll store the tm here:
            self.tmdb = tmdb.TMDB(self.config["tmdb"])
            # We actually need source, target, context, targetlanguage
            self.migrated = []

            if sys.platform == "darwin":
                self.poedit_dir = path.expanduser('~/Library/Preferences')
            else:
                self.poedit_dir = path.expanduser('~/.poedit')

            #TODO: check if we can do better than hardcoding the kbabel location
            #this path is specified in ~/.kde/config/kbabel.defaultproject and kbabeldictrc
            self.kbabel_dir = path.expanduser('~/.kde/share/apps/kbabeldict/dbsearchengine')

            self.lokalize_rc = path.expanduser('~/.kde/share/config/lokalizerc')
            self.lokalize_tm_dir = path.expanduser('~/.kde/share/apps/lokalize/')

            self.poedit_settings_import()
            self.poedit_tm_import()
            self.kbabel_tm_import()
            self.lokalize_settings_import()
            self.lokalize_tm_import()

            if self.migrated:
                message = _('Migration was successfully completed') + '\n\n'
                message += _('The following items were migrated:') + '\n\n'
                message += u"\n".join([u" • %s" % item for item in self.migrated])
                #   (we can mark this ^^^ for translation if somebody asks)
                self.main_controller.show_info(_('Migration completed'), message)
            else:
                message = _("Virtaal was not able to migrate any settings or data")
                self.main_controller.show_info(_('Nothing migrated'), message)
            logging.debug('Migration plugin executed')

        pan_app.settings.plugin_state[self.internal_name] = "disabled"

    def poedit_settings_import(self):
        """Attempt to import the settings from Poedit."""
        if sys.platform == 'darwin':
            config_filename = path.join(self.poedit_dir, 'net.poedit.Poedit.cfg')
        else:
            config_filename = path.join(self.poedit_dir, 'config')
        get_thing = None
        if not path.exists(config_filename):
            try:
                import _winreg
            except Exception, e:
                return

            def get_thing(section, item):
                key = None
                try:
                    key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"Software\Vaclav Slavik\Poedit\%s" % section)
                except WindowsError:
                    return

                data = None
                try:
                    # This is very inefficient, but who cares?
                    for i in range(100):
                        name, data, type = _winreg.EnumValue(key, i)
                        if name == item:
                            break
                except EnvironmentError, e:
                    pass
                except Exception, e:
                    logging.exception("Error obtaining from registry: %s, %s", section, item)
                return data

        else:
            self.poedit_config = ConfigParser.ConfigParser()
            poedit_config_file = open(config_filename, 'r')
            contents = StringIO.StringIO('[poedit_headerless_file]\n' + poedit_config_file.read())
            poedit_config_file.close()
            self.poedit_config.readfp(contents)
            def get_thing(section, item):
                dictionary = dict(self.poedit_config.items(section or 'poedit_headerless_file'))
                return dictionary.get(item, None)

        if get_thing is None:
            return

        lastdir = get_thing('', 'last_file_path')
        name = get_thing('', 'translator_name')
        translator_email = get_thing('', 'translator_email')

        if lastdir:
            pan_app.settings.general['lastdir'] = lastdir
        if name:
            pan_app.settings.translator['name'] = name
        if translator_email:
            pan_app.settings.translator['email'] = translator_email

        self.poedit_database_path = get_thing('TM', 'database_path')
        self.poedit_languages = []
        languages = get_thing('TM', 'languages')
        if languages:
            self.poedit_languages = languages.split(':')

        if lastdir or name or translator_email:
            pan_app.settings.write()
            self.migrated.append(_("Poedit settings"))

    def poedit_tm_import(self):
        """Attempt to import the Translation Memory used in KBabel."""
        if bsddb is None or not hasattr(self, "poedit_database_path"):
            return

        # import each language separately
        for lang in self.poedit_languages:
            strings_db_file = path.join(self.poedit_database_path, lang, 'strings.db')
            translations_db_file = path.join(self.poedit_database_path, lang, 'translations.db')
            if not path.exists(strings_db_file) or not path.exists(translations_db_file):
                continue
            sources = bsddb.hashopen(strings_db_file, 'r')
            targets = bsddb.rnopen(translations_db_file, 'r')
            for source, str_index in sources.iteritems():
                unit = {"context" : ""}
                # the index is a four byte integer encoded as a string
                # was little endian on my machine, not sure if it is universal
                index = struct.unpack('i', str_index)
                target = targets[index[0]][:-1] # null-terminated
                unit["source"] = _prepare_db_string(source)
                unit["target"] = _prepare_db_string(target)
                self.tmdb.add_dict(unit, "en", lang, commit=False)
            self.tmdb.connection.commit()

            logging.debug('%d units migrated from Poedit TM: %s.' % (len(sources), lang))
            sources.close()
            targets.close()
            self.migrated.append(_("Poedit's Translation Memory: %(database_language_code)s") % \
                    {"database_language_code": lang})

    def kbabel_tm_import(self):
        """Attempt to import the Translation Memory used in KBabel."""
        if bsddb is None or not path.exists(self.kbabel_dir):
            return
        for tm_filename in os.listdir(self.kbabel_dir):
            if not tm_filename.startswith("translations.") or not tm_filename.endswith(".db"):
                continue
            tm_file = path.join(self.kbabel_dir, tm_filename)
            lang = tm_filename.replace("translations.", "").replace(".db", "")
            translations = bsddb.btopen(tm_file, 'r')

            for source, target in translations.iteritems():
                unit = {"context" : ""}
                source = source[:-1] # null-terminated
                target = target[16:-1] # 16 bytes of padding, null-terminated
                unit["source"] = _prepare_db_string(source)
                unit["target"] = _prepare_db_string(target)
                self.tmdb.add_dict(unit, "en", lang, commit=False)
            self.tmdb.connection.commit()

            logging.debug('%d units migrated from KBabel %s TM.' % (len(translations), lang))
            translations.close()
            self.migrated.append(_("KBabel's Translation Memory: %(database_language_code)s") % \
                      {"database_language_code": lang})

    def lokalize_settings_import(self):
        """Attempt to import the settings from Lokalize."""
        if not path.exists(self.lokalize_rc):
            return

        lokalize_config = ConfigParser.ConfigParser()
        lokalize_config.read(self.lokalize_rc)
        lokalize_identity = dict(lokalize_config.items('Identity'))

        pan_app.settings.translator['name'] = lokalize_identity['authorname']
        pan_app.settings.translator['email'] = lokalize_identity['authoremail']
        pan_app.settings.translator['team'] = lokalize_identity['defaultmailinglist']
        pan_app.settings.general['lastdir'] = path.dirname(dict(lokalize_config.items('State'))['project'])

        pan_app.settings.write()
        self.migrated.append(_("Lokalize settings"))

    def lokalize_tm_import(self):
        """Attempt to import the Translation Memory used in Lokalize."""
        if not path.isdir(self.lokalize_tm_dir):
            return
        databases = [name for name in os.listdir(self.lokalize_tm_dir) if path.exists(name)]
        for database in databases:
            self.do_lokalize_tm_import(database)

    def do_lokalize_tm_import(self, filename):
        """Import the given Translation Memory file used by Lokalize."""
        lang = self.main_controller.lang_controller.target_lang.code
        connection = dbapi2.connect(filename)
        cursor = connection.cursor()
        cursor.execute("""SELECT english, target from tm_main;""")
        for (source, target) in cursor:
            unit = { "source" : source,
                     "target" : target,
                     "context" : ""
                     }
            self.tmdb.add_dict(unit, "en", lang, commit=False)
        self.tmdb.connection.commit()
        connection.close()
        self.migrated.append(_("Lokalize's Translation Memory: %(database_name)s") % \
                {"database_name": path.basename(filename)})

########NEW FILE########
__FILENAME__ = spellchecker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import os
import os.path
import re
import sys
from gettext import dgettext
import gobject

from virtaal.common import pan_app
from virtaal.controllers.baseplugin import PluginUnsupported, BasePlugin

if not pan_app.DEBUG:
    try:
        import psyco
    except:
        psyco = None
else:
    psyco = None

_dict_add_re = re.compile('Add "(.*)" to Dictionary')


class Plugin(BasePlugin):
    """A plugin to control spell checking.

    It can also download spell checkers on Windows and Mac."""

    display_name = _('Spell Checker')
    description = _('Check spelling and provide suggestions')
    version = 0.1

    _base_URL = 'http://dictionary.locamotion.org/hunspell/'
    _dict_URL = _base_URL + '%s.tar.bz2'
    _lang_list = 'languages.txt'

    # INITIALIZERS #
    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name

        if os.name == 'nt':
            DICTDIR = os.path.join(os.environ['APPDATA'], 'enchant', 'myspell')
            # if we can't decode it as ascii, enchant won't work on Windows
            try:
                DICTDIR = DICTDIR.decode('ascii')
            except UnicodeDecodeError:
                raise PluginUnsupported("Spell checking is not supported with non-ascii username")

        # If these imports fail, the plugin is automatically disabled
        import gtkspell
        import enchant
        self.gtkspell = gtkspell
        self.enchant = enchant
        # languages that we've handled before:
        self._seen_languages = {}
        # languages supported by enchant:
        self._enchant_languages = self.enchant.list_languages()

        # HTTP clients (Windows and Mac only)
        self.clients = {}
        # downloadable languages (Windows and Mac only)
        self.languages = set()

        unit_view = main_controller.unit_controller.view
        self.unit_view = unit_view
        self._connect_id = self.unit_view.connect('textview-language-changed', self._on_unit_lang_changed)

        self._textbox_ids = []
        self._unitview_ids = []
        # For some reason the i18n of gtkspell doesn't work on Windows, so we
        # intervene. We also don't want the Languages submenu, so we remove it.
        if unit_view.sources:
            self._connect_to_textboxes(unit_view, unit_view.sources)
            srclang = main_controller.lang_controller.source_lang.code
            for textview in unit_view.sources:
                self._on_unit_lang_changed(unit_view, textview, srclang)
        else:
            self._unitview_ids.append(unit_view.connect('sources-created', self._connect_to_textboxes))
        if unit_view.targets:
            self._connect_to_textboxes(unit_view, unit_view.targets)
            tgtlang = main_controller.lang_controller.target_lang.code
            for textview in unit_view.targets:
                self._on_unit_lang_changed(unit_view, textview, tgtlang)
        else:
            self._unitview_ids.append(unit_view.connect('targets-created', self._connect_to_textboxes))

    def destroy(self):
        """Remove signal connections and disable spell checking."""
        for id in self._unitview_ids:
            self.unit_view.disconnect(id)
        for textbox, id in self._textbox_ids:
            textbox.disconnect(id)
        if getattr(self, '_connect_id', None):
            self.unit_view.disconnect(self._connect_id)
        for text_view in self.unit_view.sources + self.unit_view.targets:
            self._disable_checking(text_view)

    def _connect_to_textboxes(self, unitview, textboxes):
        for textbox in textboxes:
            self._textbox_ids.append((
                textbox,
                textbox.connect('populate-popup', self._on_populate_popup)
            ))


    # METHODS #

    def _build_client(self, url, clients_id, callback, error_callback=None):
        from virtaal.support.httpclient import HTTPClient
        client = HTTPClient()
        client.set_virtaal_useragent()
        self.clients[clients_id] = client
        if logging.root.level != logging.DEBUG:
            client.get(url, callback)
        else:
            def error_log(request, result):
                logging.debug('Could not get %s: status %d' % (url, request.status))
            client.get(url, callback, error_callback=error_log)

    def _download_checker(self, language):
        """A Windows-and Mac only way to obtain new dictionaries."""
        if os.name == 'nt' and 'APPDATA' not in os.environ:
            # We won't have an idea of where to save it, so let's give up now
            return
        if language in self.clients:
            # We already tried earlier, or started the process
            return
        if not self.languages:
            if self._lang_list not in self.clients:
                # We don't yet have a list of available languages
                url = self._base_URL + self._lang_list #index page listing all the dictionaries
                callback = lambda *args: self._process_index(language=language, *args)
                self._build_client(url, self._lang_list, callback)
                # self._process_index will call this again, so we can exit
            return

        language_to_download = None
        # People almost definitely want 'en_US' for 'en', so let's ensure
        # that we get that right:
        if language == 'en':
            language_to_download = 'en_US'
            self.clients[language] = None
        else:
            # Let's see if a dictionary is available for this language:
            for l in self.languages:
                if l == language or l.startswith(language+'_'):
                    self.clients[language] = None
                    logging.debug("Will use %s to spell check %s", l, language)
                    language_to_download = l
                    break
            else:
                # No dictionary available
                # Indicate that we never need to try this language:
                logging.debug("Found no suitable language for spell checking")
                self.clients[language] = None
                return

       # Now download the actual files after we have determined that it is
       # available
        callback = lambda *args: self._process_tarball(language=language, *args)
        url = self._dict_URL % language_to_download
        self._build_client(url, language, callback)


    def _tar_ok(self, tar):
        # TODO: Verify that the tarball is ok:
        # - only two files
        # - must be .aff and .dic
        # - language codes should be sane
        # - file sizes should be ok
        # - no directory structure
        return True

    def _ensure_dir(self, dir):
        if not os.path.isdir(dir):
            os.makedirs(dir)

    def _process_index(self, request, result, language=None):
        """Process the list of languages."""
        if request.status == 200 and not self.languages:
            self.languages = set(result.split())
            self._download_checker(language)
        else:
            logging.debug("Couldn't get list of spell checkers")
            #TODO: disable plugin

    def _process_tarball(self, request, result, language=None):
        # Indicate that we already tried and shouldn't try again later:
        self.clients[language] = None

        if request.status == 200:
            logging.debug('Got a dictionary')
            from cStringIO import StringIO
            import tarfile
            file_obj = StringIO(result)
            tar = tarfile.open(fileobj=file_obj)
            if not self._tar_ok(tar):
                return
            if os.name == 'nt':
                DICTDIR = os.path.join(os.environ['APPDATA'], 'enchant', 'myspell')
            elif sys.platform == 'darwin':
                DICTDIR = os.path.expanduser("~/.enchant/myspell")
            self._ensure_dir(DICTDIR)
            tar.extractall(DICTDIR)
            self._seen_languages.pop(language, None)
            self._enchant_languages = self.enchant.list_languages()
            self.unit_view.update_languages()
        else:
            logging.debug("Couldn't get a dictionary. Status code: %d" % (request.status))

    def _disable_checking(self, text_view):
        """Disable checking on the given text_view."""
        if getattr(text_view, 'spell_lang', 'xxxx') is None:
            # No change necessary - already disabled
            return
        spell = None
        try:
            spell = self.gtkspell.get_from_text_view(text_view)
        except SystemError, e:
            # At least on Mandriva .get_from_text_view() sometimes returns
            # a SystemError without a description. Things seem to work fine
            # anyway, so let's ignore it and hope for the best.
            pass
        if not spell is None:
            spell.detach()
        text_view.spell_lang = None
    if psyco:
        psyco.cannotcompile(_disable_checking)


    # SIGNAL HANDLERS #
    def _on_unit_lang_changed(self, unit_view, text_view, language):
        if not self.gtkspell:
            return

        # enchant doesn't like anything except plain strings (bug 1852)
        language = str(language)

        if language == 'en':
            language = 'en_US'
        elif language == 'pt':
            language == 'pt_PT'
        elif language == 'de':
            language == 'de_DE'

        if not language in self._seen_languages and not self.enchant.dict_exists(language):
            # Sometimes enchants *wants* a country code, other times it does not.
            # For the cases where it requires one, we look for the first language
            # code that enchant supports and use that one.
            for code in self._enchant_languages:
                if code.startswith(language+'_'):
                    self._seen_languages[language] = code
                    language = code
                    break
            else:
                #logging.debug('No code in enchant.list_languages() that starts with "%s"' % (language))

                # If we are on Windows or Mac, let's try to download a spell checker:
                if os.name == 'nt' or sys.platform == 'darwin':
                    self._download_checker(language)
                    # If we get it, it will only be activated asynchronously
                    # later
                #TODO: packagekit on Linux?

                # We couldn't find a dictionary for "language", so we should make sure that we don't
                # have a spell checker for a different language on the text view. See bug 717.
                self._disable_checking(text_view)
                self._seen_languages[language] = None
                return

        language = self._seen_languages.get(language, language)
        if language is None:
            self._disable_checking(text_view)
            return

        if getattr(text_view, 'spell_lang', None) == language:
            # No change necessary - already enabled
            return
        gobject.idle_add(self._activate_checker, text_view, language, priority=gobject.PRIORITY_LOW)

    def _activate_checker(self, text_view, language):
        # All the expensive stuff in here called on idle. We mush also isolate
        # this away from psyco
        try:
            spell = None
            try:
                spell = self.gtkspell.get_from_text_view(text_view)
            except SystemError, e:
                # At least on Mandriva .get_from_text_view() sometimes returns
                # a SystemError without a description. Things seem to work fine
                # anyway, so let's ignore it and hope for the best.
                pass
            if spell is None:
                spell = self.gtkspell.Spell(text_view, language)
            else:
                spell.set_language(language)
                spell.recheck_all()
            text_view.spell_lang = language
        except Exception, e:
            logging.exception("Could not initialize spell checking: %s", e)
            self.gtkspell = None
            #TODO: unload plugin
    if psyco:
        # Some of the gtkspell stuff can't work with psyco and will dump core
        # if we don't avoid psyco compilation
        psyco.cannotcompile(_activate_checker)

    def _on_populate_popup(self, textbox, menu):
        # We can't work with the menu immediately, since gtkspell only adds its
        # entries in the event handler.
        gobject.idle_add(self._fix_menu, menu)

    def _fix_menu(self, menu):
        _entries_above_separator = False
        _now_remove_separator = False
        for item in menu:
            if item.get_name() == 'GtkSeparatorMenuItem':
                if not _entries_above_separator:
                    menu.remove(item)
                break

            label = item.get_property('label')

            # For some reason the i18n of gtkspell doesn't work on Windows, so
            # we intervene.
            if label == "<i>(no suggestions)</i>":
                #l10n: This refers to spell checking
                item.set_property('label', _("<i>(no suggestions)</i>"))

            if label == "Ignore All":
                #l10n: This refers to spell checking
                item.set_property('label', _("Ignore All"))

            if label == "More...":
                #l10n: This refers to spelling suggestions
                item.set_property('label', _("More..."))

            m = _dict_add_re.match(label)
            if m:
                word = m.group(1)
                #l10n: This refers to the spell checking dictionary
                item.set_property('label', _('Add "%s" to Dictionary') % word)

            # We don't want a language selector - we have our own
            if label in dgettext('gtkspell', 'Languages'):
                menu.remove(item)
                if not _entries_above_separator:
                    _now_remove_separator = True
                    continue

            _entries_above_separator = True

########NEW FILE########
__FILENAME__ = autoterm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import os
import time
from translate.search.match import terminologymatcher
from translate.storage import factory
from translate.storage.base import TranslationStore
from translate.storage.placeables.terminology import TerminologyPlaceable

from virtaal.common import pan_app
from virtaal.support.httpclient import HTTPClient

from basetermmodel import BaseTerminologyModel

THREE_DAYS = 60 * 60 * 24 * 3


class TerminologyModel(BaseTerminologyModel):
    """A terminology back-end to access the Translate.org.za-managed terminology."""

    __gtype_name__ = 'AutoTermTerminology'
    display_name = _('Localization Terminology')
    description = _('Selected localization terminology')

    _l10n_URL = 'http://terminology.locamotion.org/l10n/%(srclang)s/%(tgtlang)s'

    TERMDIR = os.path.join(pan_app.get_config_dir(), 'autoterm')

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        super(TerminologyModel, self).__init__(controller)
        self.internal_name = internal_name
        self.client = HTTPClient()
        self.client.set_virtaal_useragent()

        self.load_config()

        if not os.path.isdir(self.TERMDIR):
            os.mkdir(self.TERMDIR)

        self.main_controller = controller.main_controller
        self.term_controller = controller
        self.matcher = None
        self.init_matcher()

        lang_controller = self.main_controller.lang_controller
        self.source_lang = lang_controller.source_lang.code
        self.target_lang = lang_controller.target_lang.code
        self._connect_ids.append((
            lang_controller.connect('source-lang-changed', self._on_lang_changed, 'source'),
            lang_controller
        ))
        self._connect_ids.append((
            lang_controller.connect('target-lang-changed', self._on_lang_changed, 'target'),
            lang_controller
        ))

        self.update_terms()

    def init_matcher(self, filename=''):
        """
        Initialize the matcher to be used by the C{TerminologyPlaceable} parser.
        """
        if self.matcher in TerminologyPlaceable.matchers:
            TerminologyPlaceable.matchers.remove(self.matcher)

        if os.path.isfile(filename):
            logging.debug('Loading terminology from %s' % (filename))
            self.store = factory.getobject(filename)
        else:
            logging.debug('Creating empty terminology store')
            self.store = TranslationStore()
        self.store.makeindex()
        self.matcher = terminologymatcher(self.store)
        TerminologyPlaceable.matchers.append(self.matcher)


    # ACCESSORS #
    def _get_curr_term_filename(self, srclang=None, tgtlang=None, ext=None):
        if srclang is None:
            srclang = self.source_lang
        if tgtlang is None:
            tgtlang = self.target_lang
        if not ext:
            ext = 'po'

        base = '%s__%s' % (srclang, tgtlang)
        for filename in os.listdir(self.TERMDIR):
            if filename.startswith(base):
                return filename
        return base + os.extsep + ext
    curr_term_filename = property(_get_curr_term_filename)


    # METHODS #
    def update_terms(self, srclang=None, tgtlang=None):
        """Update the terminology file for the given language or all if none specified."""
        if srclang is None:
            srclang = self.source_lang
        if tgtlang is None:
            tgtlang = self.target_lang

        if srclang is None and tgtlang is None:
            # Update all files
            return

        if srclang is None or tgtlang is None:
            raise ValueError('Both srclang and tgtlang must be specified')

        if not self.is_update_needed(srclang, tgtlang):
            logging.debug('Skipping update for (%s, %s) language pair' % (srclang, tgtlang))
            localfile = self._get_curr_term_filename(srclang, tgtlang)
            localfile = os.path.join(self.TERMDIR, localfile)
            self.init_matcher(localfile)
            return

        self._update_term_file(srclang, tgtlang)

    def is_update_needed(self, srclang, tgtlang):
        localfile = self._get_curr_term_filename(srclang, tgtlang)
        localfile = os.path.join(self.TERMDIR, localfile)
        if not os.path.isfile(localfile):
            return True
        stats = os.stat(localfile)
        from datetime import datetime
        return (time.mktime(datetime.now().timetuple()) - stats.st_mtime) > THREE_DAYS

    def _check_for_update(self, srclang, tgtlang):
        localfile = self._get_curr_term_filename(srclang, tgtlang)
        localfile = os.path.join(self.TERMDIR, localfile)
        etag = None
        if os.path.isfile(localfile) and localfile in self.config:
            etag = self.config[os.path.abspath(localfile)]

        url = self._l10n_URL % {'srclang': srclang, 'tgtlang': tgtlang}

        if not os.path.isfile(localfile):
            localfile = None
        callback = lambda *args: self._process_header(localfile=localfile, *args)

        if logging.root.level != logging.DEBUG:
            self.client.get(url, callback, etag)
        else:
            def error_log(request, result):
                logging.debug('Could not get %s: status %d' % (url, request.status))
            self.client.get(url, callback, etag, error_callback=error_log)

    def _get_ext_from_url(self, url):
        from urlparse import urlparse
        parsed = urlparse(url)
        #dir, filename = os.path.split(parsed.path)
        #rewritten for compatibility with Python 2.4:
        dir, filename = os.path.split(parsed[2])
        if not filename or '.' not in filename:
            return None
        ext = filename.split('.')[-1]
        if not ext:
            ext = None
        return ext

    def _get_ext_from_store_guess(self, content):
        from StringIO import StringIO
        from translate.storage.factory import _guessextention
        s = StringIO(content)
        try:
            return _guessextention(s)
        except ValueError:
            pass
        return None

    def _process_header(self, request, result, localfile=None):
        if request.status == 304:
            logging.debug('ETag matches for file %s :)' % (localfile))
        elif request.status == 200:
            if not localfile:
                ext = self._get_ext_from_url(request.get_effective_url())
                if ext is None:
                    ext = self._get_ext_from_store_guess(result)
                if ext is None:
                    logging.debug('Unable to determine extension for store. Defaulting to "po".')
                    ext = 'po'
                localfile = self._get_curr_term_filename(ext=ext)
                localfile = os.path.join(self.TERMDIR, localfile)
            logging.debug('Saving to %s' % (localfile))
            open(localfile, 'w').write(result)

            # Find ETag header and save the value
            headers = request.result_headers.getvalue().splitlines()
            etag = ''
            etagline = [l for l in headers if l.lower().startswith('etag:')]
            if etagline:
                etag = etagline[0][7:-1]
            self.config[os.path.abspath(localfile)] = etag
        else:
            logging.debug('Unhandled status code: %d' % (request.status))
            localfile = ''

        if os.path.isfile(localfile):
            # Update mtime
            os.utime(localfile, None)
        self.init_matcher(localfile)

    def _update_term_file(self, srclang, tgtlang):
        """Update the terminology file for the given languages."""
        self.init_matcher() # Make sure that the matcher is empty until we have an update
        filename = self._get_curr_term_filename(srclang, tgtlang)
        localfile = os.path.join(self.TERMDIR, filename)

        self._check_for_update(srclang, tgtlang)


    # SIGNAL HANDLERS #
    def _on_lang_changed(self, lang_controller, lang, which):
        setattr(self, '%s_lang' % (which), lang)
        self.update_terms(self.source_lang, self.target_lang)

########NEW FILE########
__FILENAME__ = basetermmodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os
import gobject

from virtaal.models.basemodel import BaseModel
from virtaal.common import pan_app

class BaseTerminologyModel(BaseModel):
    """The base interface to be implemented by all terminology backend models."""

    __gtype_name__ = None
    __gsignals__ = {
        'match-found': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT,))
    }

    configure_func = None
    """A function that starts the configuration, if available."""
    display_name = None
    """The backend's name, suitable for display."""
    default_config = {}
    """Default configuration shared by all terminology model plug-ins."""

    # INITIALIZERS #
    def __init__(self, controller):
        """Initialise the model and connects it to the appropriate events.

            Only call this from child classes once the object was successfully
            created and want to be connected to signals."""
        super(BaseTerminologyModel, self).__init__()
        self.config = {}
        self.controller = controller
        self._connect_ids = []

        #static suggestion cache for slow terminology queries
        #TODO: cache invalidation, maybe decorate query to automate cache handling?
        self.cache = {}


    # METHODS #
    def destroy(self):
        self.save_config()
        #disconnect all signals
        [widget.disconnect(cid) for (cid, widget) in self._connect_ids]

    def load_config(self):
        """Load terminology backend config from default location"""
        self.config = {}
        self.config.update(self.default_config)
        config_file = os.path.join(pan_app.get_config_dir(), "terminology.ini")
        self.config.update(pan_app.load_config(config_file, self.internal_name))

    def save_config(self):
        """Save terminology backend config to default location"""
        config_file = os.path.join(pan_app.get_config_dir(), "terminology.ini")
        pan_app.save_config(config_file, self.config, self.internal_name)

########NEW FILE########
__FILENAME__ = localfileview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import pango
from gtk import gdk
from translate.storage import factory as store_factory

from virtaal.views.baseview import BaseView
from virtaal.views.theme import current_theme


class LocalFileView:
    """
    Class that manages the localfile terminology plug-in's GUI presense and interaction.
    """

    # INITIALIZERS #
    def __init__(self, model):
        self.term_model = model
        self.controller = model.controller
        self.mainview = model.controller.main_controller.view
        self._signal_ids = []
        self._setup_menus()
        self._addterm = None
        self._fileselect = None


    # METHODS #
    def _setup_menus(self):
        mnu_transfer = self.mainview.gui.get_object('mnu_placnext')
        self.mnui_edit = self.mainview.gui.get_object('menuitem_edit')
        self.menu = self.mnui_edit.get_submenu()

        self.mnu_select_files, _menu = self.mainview.find_menu_item(_('Terminology _Files...'), self.mnui_edit)
        if not self.mnu_select_files:
            self.mnu_select_files = self.mainview.append_menu_item(_('Terminology _Files...'), self.mnui_edit, after=mnu_transfer)
        self._signal_ids.append((
            self.mnu_select_files,
            self.mnu_select_files.connect('activate', self._on_select_term_files)
        ))

        self.mnu_add_term, _menu = self.mainview.find_menu_item(_('Add _Term...'), self.mnui_edit)
        if not self.mnu_add_term:
            self.mnu_add_term = self.mainview.append_menu_item(_('Add _Term...'), self.mnui_edit, after=mnu_transfer)
        self._signal_ids.append((
            self.mnu_add_term,
            self.mnu_add_term.connect('activate', self._on_add_term)
        ))

        gtk.accel_map_add_entry("<Virtaal>/Terminology/Add Term", gtk.keysyms.t, gdk.CONTROL_MASK)
        accel_group = self.menu.get_accel_group()
        if accel_group is None:
            accel_group = gtk.AccelGroup()
            self.menu.set_accel_group(accel_group)
        self.mnu_add_term.set_accel_path("<Virtaal>/Terminology/Add Term")
        self.menu.set_accel_group(accel_group)

    def destroy(self):
        for gobj, signal_id in self._signal_ids:
            gobj.disconnect(signal_id)

        self.menu.remove(self.mnu_select_files)
        self.menu.remove(self.mnu_add_term)


    # PROPERTIES #
    def _get_addterm(self):
        if not self._addterm:
            self._addterm = TermAddDialog(model=self.term_model)
        return self._addterm
    addterm = property(_get_addterm)

    def _get_fileselect(self):
        if not self._fileselect:
            self._fileselect = FileSelectDialog(model=self.term_model)
        return self._fileselect
    fileselect = property(_get_fileselect)


    # EVENT HANDLERS #
    def _on_add_term(self, menuitem):
        self.addterm.run(parent=self.mainview.main_window)

    def _on_select_term_files(self, menuitem):
        self.fileselect.run(parent=self.mainview.main_window)


class FileSelectDialog:
    """
    Wrapper for the selection dialog, created in GtkBuilder, to manage the list of
    files used by this plug-in.
    """

    COL_FILE, COL_EXTEND = range(2)

    # INITIALIZERS #
    def __init__(self, model):
        self.controller = model.controller
        self.term_model = model
        self.gui = BaseView.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='TermFilesDlg',
            domain='virtaal'
        )
        self._get_widgets()
        self._init_treeview()
        self._init_add_chooser()

    def _get_widgets(self):
        widget_names = ('btn_add_file', 'btn_remove_file', 'btn_open_termfile', 'tvw_termfiles')

        for name in widget_names:
            setattr(self, name, self.gui.get_object(name))

        self.dialog = self.gui.get_object('TermFilesDlg')
        self.btn_add_file.connect('clicked', self._on_add_file_clicked)
        self.btn_remove_file.connect('clicked', self._on_remove_file_clicked)
        self.btn_open_termfile.connect('clicked', self._on_open_termfile_clicked)
        self.tvw_termfiles.get_selection().connect('changed', self._on_selection_changed)

    def _init_treeview(self):
        self.lst_files = gtk.ListStore(str, bool)
        self.tvw_termfiles.set_model(self.lst_files)

        cell = gtk.CellRendererText()
        cell.props.ellipsize = pango.ELLIPSIZE_MIDDLE
        col = gtk.TreeViewColumn(_('File'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', self.COL_FILE)
        col.set_expand(True)
        col.set_sort_column_id(0)
        self.tvw_termfiles.append_column(col)

        cell = gtk.CellRendererToggle()
        cell.set_radio(True)
        cell.connect('toggled', self._on_toggle)
        col = gtk.TreeViewColumn(_('Extendable'))
        col.pack_start(cell)
        col.add_attribute(cell, 'active', self.COL_EXTEND)
        col.set_expand(False)
        self.tvw_termfiles.append_column(col)

        extend_file = self.term_model.config.get('extendfile', '')
        files = self.term_model.config['files']
        for f in files:
            self.lst_files.append([f, f == extend_file])

        # If there was no extend file, select the first one
        for row in self.lst_files:
            if row[self.COL_EXTEND]:
                break
        else:
            itr = self.lst_files.get_iter_first()
            if itr and self.lst_files.iter_is_valid(itr):
                self.lst_files.set_value(itr, self.COL_EXTEND, True)
                self.term_model.config['extendfile'] = self.lst_files.get_value(itr, self.COL_FILE)
                self.term_model.save_config()

    def _init_add_chooser(self):
        # The following code was mostly copied from virtaal.views.MainView._create_dialogs()
        #TODO: use native dialogues
        dlg = gtk.FileChooserDialog(
            _('Add Files'),
            self.controller.main_controller.view.main_window,
            gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        )
        dlg.set_default_response(gtk.RESPONSE_OK)
        all_supported_filter = gtk.FileFilter()
        all_supported_filter.set_name(_("All Supported Files"))
        dlg.add_filter(all_supported_filter)
        supported_files_dict = dict([ (_(name), (extension, mimetype)) for name, extension, mimetype in store_factory.supported_files() ])
        supported_file_names = supported_files_dict.keys()
        from locale import strcoll
        supported_file_names.sort(cmp=strcoll)
        for name in supported_file_names:
            extensions, mimetypes = supported_files_dict[name]
            #XXX: we can't open generic .csv formats, so listing it is probably
            # more harmful than good.
            if "csv" in extensions:
                continue
            new_filter = gtk.FileFilter()
            new_filter.set_name(name)
            if extensions:
                for extension in extensions:
                    new_filter.add_pattern("*." + extension)
                    all_supported_filter.add_pattern("*." + extension)
                    for compress_extension in store_factory.decompressclass.keys():
                        new_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
                        all_supported_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
            if mimetypes:
                for mimetype in mimetypes:
                    new_filter.add_mime_type(mimetype)
                    all_supported_filter.add_mime_type(mimetype)
            dlg.add_filter(new_filter)
        all_filter = gtk.FileFilter()
        all_filter.set_name(_("All Files"))
        all_filter.add_pattern("*")
        dlg.add_filter(all_filter)
        dlg.set_select_multiple(True)

        self.add_chooser = dlg


    # METHODS #
    def clear_selection(self):
        self.tvw_termfiles.get_selection().unselect_all()

    def run(self, parent=None):
        if isinstance(parent, gtk.Widget):
            self.dialog.set_transient_for(parent)

        self.clear_selection()

        self.dialog.show_all()
        self.dialog.run()
        self.dialog.hide()


    # EVENT HANDLERS #
    def _on_add_file_clicked(self, button):
        self.add_chooser.show_all()
        response = self.add_chooser.run()
        self.add_chooser.hide()

        if response != gtk.RESPONSE_OK:
            return

        mainview = self.term_model.controller.main_controller.view
        currfiles = [row[self.COL_FILE] for row in self.lst_files]
        for filename in self.add_chooser.get_filenames():
            if filename in currfiles:
                continue
            # Try and open filename as a translation store
            try:
                import os.path
                if not os.path.isfile(filename):
                    raise IOError(_('"%s" is not a usable file.') % filename)
                store = store_factory.getobject(filename)
                currfiles.append(filename)
                self.lst_files.append([filename, False])
            except Exception, exc:
                message = _('Unable to load %(filename)s:\n\n%(errormsg)s') % {'filename': filename, 'errormsg': str(exc)}
                mainview.show_error_dialog(title=_('Error opening file'), message=message)

        self.term_model.config['files'] = currfiles
        self.term_model.save_config()
        self.term_model.load_files() # FIXME: This could be optimized to only load and add the new selected files.

    def _on_remove_file_clicked(self, button):
        model, selected = self.tvw_termfiles.get_selection().get_selected()
        if not selected:
            return

        remfile = model.get_value(selected, self.COL_FILE)
        extend = model.get_value(selected, self.COL_EXTEND)
        self.term_model.config['files'].remove(remfile)

        if extend:
            self.term_model.config['extendfile'] = ''
            itr = model.get_iter_first()
            if itr and model.iter_is_valid(itr):
                model.set_value(itr, self.COL_EXTEND, True)
                self.term_model.config['extendfile'] = model.get_value(itr, self.COL_FILE)

        self.term_model.save_config()
        self.term_model.load_files() # FIXME: This could be optimized to only remove the selected file from the terminology matcher.
        model.remove(selected)

    def _on_open_termfile_clicked(self, button):
        selection = self.tvw_termfiles.get_selection()
        model, itr = selection.get_selected()
        if itr is None:
            return
        selected_file = model.get_value(itr, self.COL_FILE)
        self.term_model.controller.main_controller.open_file(selected_file)

    def _on_selection_changed(self, treesel):
        model, itr = treesel.get_selected()
        enabled = itr is not None
        self.btn_open_termfile.set_sensitive(enabled)
        self.btn_remove_file.set_sensitive(enabled)

    def _on_toggle(self, renderer, path):
        toggled_file = self.lst_files.get_value(self.lst_files.get_iter(path), self.COL_FILE)

        itr = self.lst_files.get_iter_first()
        while itr is not None and self.lst_files.iter_is_valid(itr):
            self.lst_files.set_value(itr, self.COL_EXTEND, self.lst_files.get_value(itr, self.COL_FILE) == toggled_file)
            itr = self.lst_files.iter_next(itr)

        self.term_model.config['extendfile'] = toggled_file
        self.term_model.save_config()


class TermAddDialog:
    """
    Wrapper for the dialog used to add a new term to the terminology file.
    """

    # INITIALIZERS #
    def __init__(self, model):
        self.term_model = model
        self.lang_controller = model.controller.main_controller.lang_controller
        self.unit_controller = model.controller.main_controller.unit_controller

        self.gui = BaseView.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='TermAddDlg',
            domain='virtaal'
        )
        self._get_widgets()

    def _get_widgets(self):
        widget_names = (
            'btn_add_term', 'cmb_termfile', 'eb_add_term_errors', 'ent_source',
            'ent_target', 'lbl_add_term_errors', 'lbl_srclang', 'lbl_tgtlang',
            'txt_comment'
        )

        for name in widget_names:
            setattr(self, name, self.gui.get_object(name))

        self.dialog = self.gui.get_object('TermAddDlg')

        cellr = gtk.CellRendererText()
        cellr.props.ellipsize = pango.ELLIPSIZE_MIDDLE
        self.lst_termfiles = gtk.ListStore(str)
        self.cmb_termfile.set_model(self.lst_termfiles)
        self.cmb_termfile.pack_start(cellr)
        self.cmb_termfile.add_attribute(cellr, 'text', 0)

        self.ent_source.connect('changed', self._on_entry_changed)
        self.ent_target.connect('changed', self._on_entry_changed)


    # METHODS #
    def add_term_unit(self, source, target):
        filename = self.cmb_termfile.get_active_text()
        store = self.term_model.get_store_for_filename(filename)
        if store is None:
            import logging
            logging.debug('No terminology store to extend :(')
            return
        unit = store.addsourceunit(source)
        unit.target = target

        buff = self.txt_comment.get_buffer()
        comments = buff.get_text(buff.get_start_iter(), buff.get_end_iter())
        if comments:
            unit.addnote(comments)

        store.save()
        self.term_model.matcher.extendtm(unit)
        #logging.debug('Added new term: [%s] => [%s], file=%s' % (source, target, store.filename))

    def reset(self):
        unitview = self.unit_controller.view

        source_text = u''
        for src in unitview.sources:
            selection = src.buffer.get_selection_bounds()
            if selection:
                source_text = src.get_text(*selection)
                break

        from virtaal.views import rendering
        self.ent_source.modify_font(rendering.get_source_font_description())
        self.ent_source.set_text(source_text.strip())

        target_text = u''
        for tgt in unitview.targets:
            selection = tgt.buffer.get_selection_bounds()
            if selection:
                target_text = tgt.get_text(*selection)
                break
        self.ent_target.modify_font(rendering.get_target_font_description())
        self.ent_target.set_text(target_text.strip())

        self.txt_comment.get_buffer().set_text('')

        self.eb_add_term_errors.hide()
        self.btn_add_term.props.sensitive = True
        self.lbl_srclang.set_text_with_mnemonic(_(u'_Source term — %(langname)s') % {'langname': self.lang_controller.source_lang.name})
        self.lbl_tgtlang.set_text_with_mnemonic(_(u'_Target term — %(langname)s') % {'langname': self.lang_controller.target_lang.name})

        self.lst_termfiles.clear()

        extendfile = self.term_model.config.get('extendfile', None)
        select_index = -1
        i = 0
        for f in self.term_model.config['files']:
            if f == extendfile:
                select_index = i
            self.lst_termfiles.append([f])
            i += 1

        if select_index >= 0:
            self.cmb_termfile.set_active(select_index)

    def run(self, parent=None):
        self.reset()

        if isinstance(parent, gtk.Widget):
            self.dialog.set_transient_for(parent)

        self.dialog.show()
        self._on_entry_changed(None)
        self.ent_source.grab_focus()
        response = self.dialog.run()
        self.dialog.hide()

        if response != gtk.RESPONSE_OK:
            return

        self.add_term_unit(self.ent_source.get_text(), self.ent_target.get_text())


    # EVENT HANDLERS #
    def _on_entry_changed(self, entry):
        self.btn_add_term.props.sensitive = True
        self.eb_add_term_errors.hide()

        src_text = self.ent_source.get_text()
        tgt_text = self.ent_target.get_text()

        dup = self.term_model.get_duplicates(src_text, tgt_text)
        if dup:
            self.lbl_add_term_errors.set_text(_('Identical entry already exists.'))
            self.eb_add_term_errors.modify_bg(gtk.STATE_NORMAL, gdk.color_parse(current_theme['warning_bg']))
            self.eb_add_term_errors.show_all()
            self.btn_add_term.props.sensitive = False
            return

        same_src_units = self.term_model.get_units_with_source(src_text)
        if src_text and same_src_units:
            # We want to separate multiple terms with the correct list
            # separator for the UI language:
            from translate.lang import factory as lang_factory
            from virtaal.common.pan_app import ui_language
            separator = lang_factory.getlanguage(ui_language).listseperator

            #l10n: The variable is an existing term formatted for emphasis. The default is bold formatting, but you can remove/change the markup if needed. Leave it unchanged if you are unsure.
            translations = separator.join([_('<b>%s</b>') % (u.target) for u in same_src_units])
            errormsg = _('Existing translations: %(translations)s') % {
                'translations': translations
            }
            self.lbl_add_term_errors.set_markup(errormsg)
            self.eb_add_term_errors.modify_bg(gtk.STATE_NORMAL, gdk.color_parse(current_theme['warning_bg']))
            self.eb_add_term_errors.show_all()
            return

########NEW FILE########
__FILENAME__ = opentran
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import re
from translate.storage.placeables.terminology import TerminologyPlaceable
from translate.storage.base import TranslationUnit
from translate.lang import data

from basetermmodel import BaseTerminologyModel

MIN_TERM_LENGTH = 4

caps_re = re.compile('([a-z][A-Z])|([A-Z]{2,})')
def is_case_sensitive(text):
    """Tries to detect camel or other cases where casing might be significant."""
    return caps_re.search(text) is not None

class TerminologyModel(BaseTerminologyModel):
    """
    Terminology model that queries Open-tran.eu for terminology results.
    """

    __gtype_name__ = 'OpenTranTerminology'
    display_name = _('Open-Tran.eu')
    description = _('Terms from Open-Tran.eu')

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        super(TerminologyModel, self).__init__(controller)

        self.internal_name = internal_name
        self.load_config()

        self.main_controller = controller.main_controller
        self.term_controller = controller
        self.matcher = None
        self._init_matcher()

        self.opentrantm = self._find_opentran_tm()
        if self.opentrantm is None:
            self._init_opentran_client()
        else:
            self.opentrantm.connect('match-found', self._on_match_found)
            self.__setup_opentrantm_lang_watchers()

    def _find_opentran_tm(self):
        """
        Try and find an existing OpenTranClient instance, used by the OpenTran
        TM model.
        """
        plugin_ctrl = self.main_controller.plugin_controller
        if 'tm' not in plugin_ctrl.plugins:
            return None

        tm_ctrl = plugin_ctrl.plugins['tm'].tmcontroller
        if 'opentran' not in tm_ctrl.plugin_controller.plugins:
            return None

        return tm_ctrl.plugin_controller.plugins['opentran']

    def _init_matcher(self):
        """
        Initialize the matcher to be used by the C{TerminologyPlaceable} parser.
        """
        if self.matcher in TerminologyPlaceable.matchers:
            TerminologyPlaceable.matchers.remove(self.matcher)

        from translate.storage.base import TranslationStore
        self.store = TranslationStore()
        self.store.makeindex()
        from translate.search.match import terminologymatcher
        self.matcher = terminologymatcher(self.store)
        TerminologyPlaceable.matchers.append(self.matcher)

    def _init_opentran_client(self):
        """
        Create and initialize a new Open-Tran client. This should only happen
        when the Open-Tran TM model plug-in is not loaded.
        """
        plugin_ctrlr = self.main_controller.plugin_controller
        lang_ctrlr = self.main_controller.lang_controller
        # The following two values were copied from plugins/tm/__init__.py
        max_candidates = 5
        min_similarity = 70

        # Try to get max_candidates and min_quality from the TM plug-in
        if 'tm' in plugin_ctrlr.plugins:
            max_candidates = plugin_ctrlr.plugins['tm'].config['max_matches']
            min_similarity = plugin_ctrlr.plugins['tm'].config['min_quality']

        from virtaal.support import opentranclient
        self.opentranclient = opentranclient.OpenTranClient(
            max_candidates=max_candidates,
            min_similarity=min_similarity
        )
        self.opentranclient.source_lang = lang_ctrlr.source_lang.code
        self.opentranclient.target_lang = lang_ctrlr.target_lang.code

        self.__setup_lang_watchers()
        self.__setup_cursor_watcher()

    def __setup_cursor_watcher(self):
        unitview = self.main_controller.unit_controller.view
        def cursor_changed(cursor):
            self.__start_query()

        store_ctrlr = self.main_controller.store_controller
        def store_loaded(store_ctrlr):
            if hasattr(self, '_cursor_connect_id'):
                self.cursor.disconnect(self._cursor_connect_id)
            self.cursor = store_ctrlr.cursor
            self._cursor_connect_id = self.cursor.connect('cursor-changed', cursor_changed)
            cursor_changed(self.cursor)

        store_ctrlr.connect('store-loaded', store_loaded)
        if store_ctrlr.store:
            store_loaded(store_ctrlr)

    def __setup_lang_watchers(self):
        def client_lang_changed(client, lang):
            self.cache = {}
            self._init_matcher()
            self.__start_query()

        self._connect_ids.append((
            self.opentranclient.connect('source-lang-changed', client_lang_changed),
            self.opentranclient
        ))
        self._connect_ids.append((
            self.opentranclient.connect('target-lang-changed', client_lang_changed),
            self.opentranclient
        ))

        lang_controller = self.main_controller.lang_controller
        self._connect_ids.append((
            lang_controller.connect(
                'source-lang-changed',
                lambda _c, lang: self.opentranclient.set_source_lang(lang)
            ),
            lang_controller
        ))
        self._connect_ids.append((
            lang_controller.connect(
                'target-lang-changed',
                lambda _c, lang: self.opentranclient.set_target_lang(lang)
            ),
            lang_controller
        ))

    def __setup_opentrantm_lang_watchers(self):
        def set_lang(ctrlr, lang):
            self.cache = {}
            self._init_matcher()

        self._connect_ids.append((
            self.opentrantm.tmclient.connect('source-lang-changed', set_lang),
            self.opentrantm.tmclient
        ))
        self._connect_ids.append((
            self.opentrantm.tmclient.connect('target-lang-changed', set_lang),
            self.opentrantm.tmclient
        ))

    def __start_query(self):
        unit = self.main_controller.unit_controller.current_unit
        if not unit:
            return
        query_str = unit.source
        if not self.cache.has_key(query_str):
            self.cache[query_str] = None
            logging.debug('Query string: %s (target lang: %s)' % (query_str, self.opentranclient.target_lang))
            self.opentranclient.translate_unit(query_str, lambda *args: self.add_last_suggestions(self.opentranclient))


    # METHODS #
    def add_last_suggestions(self, opentranclient):
        """Grab the last suggestions from the TM client."""
        added = False
        if opentranclient.last_suggestions:
            for sugg in opentranclient.last_suggestions:
                units = self.create_suggestions(sugg)
                if units:
                    for u in units:
                        self.store.addunit(u)
                        self.store.add_unit_to_index(u)
                    added = True
            opentranclient.last_suggestions = []
        if added:
            self.matcher.inittm(self.store)
            unitview = self.main_controller.unit_controller.view
            self.main_controller.placeables_controller.apply_parsers(
                elems=[src.elem for src in unitview.sources],
                parsers=[TerminologyPlaceable.parse]
            )
            for src in unitview.sources:
                src.refresh()

    def create_suggestions(self, suggestion):
        # Skip any suggestions where the suggested translation contains parenthesis
        if re.match(r'\(.*\)', suggestion['text']):
            return []

        units = []

        for proj in suggestion['projects']:
            # Skip fuzzy matches:
            if proj['flags'] != 0:
                continue

            source = proj['orig_phrase'].strip()
            # Skip strings that are too short
            if len(source) < MIN_TERM_LENGTH:
                continue
            # Skip any units containing parenthesis
            if re.match(r'\(.*\)', source):
                continue
            unit = TranslationUnit(source)

            target = suggestion['text'].strip()

            # Skip phrases already found:
            old_unit = self.store.findunit(proj['orig_phrase'])
            if old_unit and old_unit.target == target:
                continue
            # We mostly want to work with lowercase strings, but in German (and
            # some languages with a related writing style), this will probably
            # irritate more often than help, since nouns are always written to
            # start with capital letters.
            target_lang_code = self.main_controller.lang_controller.target_lang.code
            if not data.normalize_code(target_lang_code) in ('de', 'de-de', 'lb', 'als', 'ksh', 'stq', 'vmf'):
                # unless the string contains multiple consecutive uppercase
                # characters or using some type of camel case, we take it to
                # lower case
                if not is_case_sensitive(target):
                    target = target.lower()
            unit.target = target
            units.append(unit)
        return units

    def destroy(self):
        super(TerminologyModel, self).destroy()
        if self.matcher in TerminologyPlaceable.matchers:
            TerminologyPlaceable.matchers.remove(self.matcher)


    # EVENT HANDLERS #
    def _on_match_found(self, *args):
        self.add_last_suggestions(self.opentrantm.tmclient)

########NEW FILE########
__FILENAME__ = termcontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import os.path
from translate.storage.placeables import terminology

from virtaal.common import GObjectWrapper
from virtaal.controllers.basecontroller import BaseController
from virtaal.controllers.plugincontroller import PluginController
from virtaal.views import placeablesguiinfo

from models.basetermmodel import BaseTerminologyModel
from termview import TerminologyGUIInfo, TerminologyView


class TerminologyController(BaseController):
    """The logic-filled glue between the terminology view and -model."""

    __gtype_name__ = 'TerminologyController'
    __gsignals__ = {
        'start-query': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
    }

    # INITIALIZERS #
    def __init__(self, main_controller, config={}):
        GObjectWrapper.__init__(self)

        self.config = config
        self.main_controller = main_controller
        self.placeables_controller = main_controller.placeables_controller

        self.disabled_model_names = ['basetermmodel'] + self.config.get('disabled_models', [])
        self.placeables_controller.add_parsers(*terminology.parsers)
        self.placeables_controller.non_target_placeables.append(terminology.TerminologyPlaceable)
        self.placeables_controller.connect('parsers-changed', self._on_placeables_changed)
        main_controller.view.main_window.connect('style-set', self._on_style_set)
        self._on_style_set(main_controller.view.main_window, None)

        if not (terminology.TerminologyPlaceable, TerminologyGUIInfo) in placeablesguiinfo.element_gui_map:
            placeablesguiinfo.element_gui_map.insert(0, (terminology.TerminologyPlaceable, TerminologyGUIInfo))

        self.view = TerminologyView(self)
        self._connect_signals()
        self._load_models()

    def _connect_signals(self):
        def lang_changed(ctrlr, lang):
            for src in self.main_controller.unit_controller.view.sources:
                src.elem.remove_type(terminology.TerminologyPlaceable)
                src.refresh()

        lang_controller = self.main_controller.lang_controller
        lang_controller.connect('source-lang-changed', lang_changed)
        lang_controller.connect('target-lang-changed', lang_changed)

    def _load_models(self):
        self.plugin_controller = PluginController(self, 'TerminologyModel')
        self.plugin_controller.PLUGIN_CLASS_INFO_ATTRIBS = ['description', 'display_name']
        new_dirs = []
        for dir in self.plugin_controller.PLUGIN_DIRS:
           new_dirs.append(os.path.join(dir, 'terminology', 'models'))
        self.plugin_controller.PLUGIN_DIRS = new_dirs

        self.plugin_controller.PLUGIN_INTERFACE = BaseTerminologyModel
        self.plugin_controller.PLUGIN_MODULES = ['virtaal_plugins.terminology.models', 'virtaal.plugins.terminology.models']
        self.plugin_controller.get_disabled_plugins = lambda *args: self.disabled_model_names
        self.plugin_controller.load_plugins()


    # METHODS #
    def destroy(self):
        self.view.destroy()
        self.plugin_controller.shutdown()
        self.placeables_controller.remove_parsers(terminology.parsers)


    # EVENT HANDLERS #
    def _on_placeables_changed(self, placeables_controller):
        for term_parser in terminology.parsers:
            if term_parser not in placeables_controller.parsers:
                placeables_controller.add_parsers(term_parser)

    def _on_style_set(self, widget, prev_style):
        TerminologyGUIInfo.update_style(widget)

########NEW FILE########
__FILENAME__ = termview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import logging

from virtaal.views.baseview import BaseView
from virtaal.views import rendering
from virtaal.views.theme import is_inverse
from virtaal.views.placeablesguiinfo import StringElemGUI
from virtaal.views.widgets.selectdialog import SelectDialog


_default_fg = '#006600'
_default_bg = '#eeffee'
_inverse_fg = '#c7ffff'
_inverse_bg = '#003700'

class TerminologyGUIInfo(StringElemGUI):
    """
    GUI info object for terminology placeables. It creates a combo box to
    choose the selected match from.
    """
    # MEMBERS #
    fg = _default_fg
    bg = _default_bg

    def __init__(self, elem, textbox, **kwargs):
        assert elem.__class__.__name__ == 'TerminologyPlaceable'
        super(TerminologyGUIInfo, self).__init__(elem, textbox, **kwargs)


    # METHODS #
    def get_insert_widget(self):
        if len(self.elem.translations) > 1:
            return TerminologyCombo(self.elem)
        return None

    @classmethod
    def update_style(self, widget):
        import gtk
        fg = widget.style.fg[gtk.STATE_NORMAL]
        bg = widget.style.base[gtk.STATE_NORMAL]
        if is_inverse(fg, bg):
            self.fg = _inverse_fg
            self.bg = _inverse_bg
        else:
            self.fg = _default_fg
            self.bg = _default_bg


class TerminologyCombo(gtk.ComboBox):
    """
    A combo box containing translation matches.
    """

    # INITIALIZERS #
    def __init__(self, elem):
        super(TerminologyCombo, self).__init__()
        self.elem = elem
        self.insert_iter = None
        self.selected_string = None
        self.set_name('termcombo')
        # Let's make it as small as possible, since we don't want to see the
        # combo at all.
        self.set_size_request(0, 0)
        self.__init_combo()
        cell_renderers = self.get_cells()
        # Set the font correctly for the target
        if cell_renderers:
            cell_renderers[0].props.font_desc = rendering.get_target_font_description()
        self.menu = self.menu_get_for_attach_widget()[0]
        self.menu.connect('selection-done', self._on_selection_done)

    def __init_combo(self):
        self._model = gtk.ListStore(str)
        for trans in self.elem.translations:
            self._model.append([trans])

        self.set_model(self._model)
        self._renderer = gtk.CellRendererText()
        self.pack_start(self._renderer)
        self.add_attribute(self._renderer, 'text', 0)

        # Force the "appears-as-list" style property to 0
        rc_string = """
            style "not-a-list"
            {
                GtkComboBox::appears-as-list = 0
            }
            class "GtkComboBox" style "not-a-list"
            """
        gtk.rc_parse_string(rc_string)


    # METHODS #
    def inserted(self, insert_iter, anchor):
        self.insert_offset = insert_iter.get_offset()
        self.grab_focus()
        self.popup()

    def insert_selected(self):
        iter = self.get_active_iter()
        if iter:
            self.selected_string = self._model.get_value(iter, 0)

        if self.parent:
            self.parent.grab_focus()

        parent = self.parent
        buffer = parent.get_buffer()
        parent.remove(self)
        if self.insert_offset >= 0:
            iterins  = buffer.get_iter_at_offset(self.insert_offset)
            iternext = buffer.get_iter_at_offset(self.insert_offset + 1)
            if iternext:
                buffer.delete(iterins, iternext)

            iterins  = buffer.get_iter_at_offset(self.insert_offset)
            parent.refresh_cursor_pos = buffer.props.cursor_position
            if self.selected_string:
                buffer.insert(iterins, self.selected_string)
                parent.emit("changed")


    # EVENT HANDLERS #
    def _on_selection_done(self, menushell):
        self.insert_selected()


class TerminologyView(BaseView):
    """
    Does general GUI setup for the terminology plug-in.
    """

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        self._signal_ids = []


    # METHODS #
    def destroy(self):
        for gobj, signal_id in self._signal_ids:
            gobj.disconnect(signal_id)

    def select_backends(self, parent):
        selectdlg = SelectDialog(
            title=_('Select Terminology Sources'),
            message=_('Select the sources of terminology suggestions'),
            parent=parent,
            size=(self.controller.config['backends_dialog_width'], 300),
        )
        selectdlg.set_icon(self.controller.main_controller.view.main_window.get_icon())

        items = []
        plugin_controller = self.controller.plugin_controller
        for plugin_name in plugin_controller._find_plugin_names():
            if plugin_name == 'basetermmodel':
                continue
            try:
                info = plugin_controller.get_plugin_info(plugin_name)
            except Exception, e:
                logging.debug('Problem getting information for plugin %s' % plugin_name)
                continue
            enabled = plugin_name in plugin_controller.plugins
            config = enabled and plugin_controller.plugins[plugin_name] or None
            items.append({
                'name': info['display_name'],
                'desc': info['description'],
                'data': {'internal_name': plugin_name},
                'enabled': enabled,
                'config': config,
            })

        def item_enabled(dlg, item):
            internal_name = item['data']['internal_name']
            plugin_controller.enable_plugin(internal_name)
            if internal_name in self.controller.config['disabled_models']:
                self.controller.config['disabled_models'].remove(internal_name)

        def item_disabled(dlg, item):
            internal_name = item['data']['internal_name']
            plugin_controller.disable_plugin(internal_name)
            if internal_name not in self.controller.config['disabled_models']:
                self.controller.config['disabled_models'].append(internal_name)

        selectdlg.connect('item-enabled',  item_enabled)
        selectdlg.connect('item-disabled', item_disabled)
        selectdlg.run(items=items)

########NEW FILE########
__FILENAME__ = amagama
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import remotetm


class TMModel(remotetm.TMModel):
    """This is the translation memory model."""

    __gtype_name__ = 'AmagamaTMModel'
    display_name = _('Amagama')
    description = _('Previous translations for Free and Open Source Software')
    #l10n: Try to keep this as short as possible.
    shortname = _('Amagama')

    default_config = {
        "host" : "amagama.locamotion.org",
        "port" : "80",
    }

    def push_store(self, store_controller):
        pass

    def upload_store(self, store_controller):
        pass

########NEW FILE########
__FILENAME__ = apertium
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""A TM provider that can query the web service for the Apertium software for
Machine Translation.

http://wiki.apertium.org/wiki/Apertium_web_service
"""

import urllib
# These two json modules are API compatible
try:
    import simplejson as json #should be a bit faster; needed for Python < 2.6
except ImportError:
    import json #available since Python 2.6

from basetmmodel import BaseTMModel, unescape_html_entities

from virtaal.support.httpclient import HTTPClient, RESTRequest


class TMModel(BaseTMModel):
    """This is the translation memory model."""

    __gtype_name__ = 'ApertiumTMModel'
    display_name = _('Apertium')
    description = _('Unreviewed machine translations from Apertium')

    url = "http://api.apertium.org/json"
    default_config = {
        "appid" : "",
    }

    # INITIALISERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        self.language_pairs = []
        self.load_config()

        self.client = HTTPClient()
        self.url_getpairs = "%(url)s/listPairs?appId=%(appid)s" % {"url": self.url, "appid": self.config["appid"]}
        self.url_translate = "%(url)s/translate" % {"url": self.url}
        self.appid = self.config['appid']
        langreq = RESTRequest(self.url_getpairs, '')
        self.client.add(langreq)
        langreq.connect(
            'http-success',
            lambda langreq, response: self.got_language_pairs(response)
        )

        super(TMModel, self).__init__(controller)


    # METHODS #
    def query(self, tmcontroller, unit):
        """Send the query to the web service. The response is handled by means
        of a call-back because it happens asynchronously."""
        pair = (self.source_lang, self.target_lang)
        if pair not in self.language_pairs:
            return

        query_str = unit.source
        if self.cache.has_key(query_str):
            self.emit('match-found', query_str, self.cache[query_str])
        else:
            values = {
                'appId': self.appid,
                'q': query_str,
                'langpair': "%s|%s" % (self.source_lang, self.target_lang),
                'markUnknown': "no",
                'format': 'html',
            }
            req = RESTRequest(self.url_translate + "?" + urllib.urlencode(values), '')
            self.client.add(req)
            req.connect(
                'http-success',
                lambda req, response: self.got_translation(response, query_str)
            )

    def got_language_pairs(self, val):
        """Handle the response from the web service to set up language pairs."""
        data = json.loads(val)
        if data['responseStatus'] != 200:
            import logging
            logging.debug("Failed to get languages:\n%s", (data['responseDetails']))
            return

        self.language_pairs = [(pair['sourceLanguage'], pair['targetLanguage']) for pair in data['responseData']]

    def got_translation(self, val, query_str):
        """Handle the response from the web service now that it came in."""
        data = json.loads(val)

        if data['responseStatus'] != 200:
            import logging
            logging.debug("Failed to translate '%s':\n%s", (query_str, data['responseDetails']))
            return

        target = data['responseData']['translatedText']
        target = unescape_html_entities(target)
        if target.endswith("\n") and not query_str.endswith("\n"):
            target = target[:-1]# chop of \n
        if not isinstance(target, unicode):
            target = unicode(target, 'utf-8')
        match = {
            'source': query_str,
            'target': target,
            #l10n: Try to keep this as short as possible. Feel free to transliterate in CJK languages for optimal vertical display.
            'tmsource': _('Apertium'),
        }
        self.cache[query_str] = [match]

        self.emit('match-found', query_str, [match])

########NEW FILE########
__FILENAME__ = basetmmodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os
import gobject
import htmlentitydefs
import re

from virtaal.models.basemodel import BaseModel
from virtaal.common import pan_app


#http://effbot.org/zone/re-sub.htm#unescape-html
def unescape_html_entities(text):
    def fixup(m):
        text = m.group(0)
        entity = htmlentitydefs.entitydefs.get(text[1:-1])
        if not entity:
            if text[:2] == "&#":
                try:
                    return unichr(int(text[2:-1]))
                except ValueError:
                    pass
        else:
            return unicode(entity, "iso-8859-1")
    return re.sub("&(#[0-9]+|\w+);", fixup, text)


class BaseTMModel(BaseModel):
    """The base interface to be implemented by all TM backend models."""

    __gtype_name__ = None
    __gsignals__ = {
        'match-found': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT,))
    }

    description = ""
    """A description of the backend. Will be displayed to users."""
    display_name = None
    """The backend's name, suitable for display."""

    configure_func = None
    """A function that starts the configuration, if available."""
    default_config = {}
    """Default configuration shared by all TM model plug-ins."""

    # INITIALIZERS #
    def __init__(self, controller):
        """Initialise the model and connects it to the appropriate events.

            Only call this from child classes once the object was successfully
            created and want to be connected to signals."""
        super(BaseTMModel, self).__init__()
        self.config = {}
        self.controller = controller
        self._connect_ids = []
        self._connect_ids.append((self.controller.connect('start-query', self.query), self.controller))

        #static suggestion cache for slow TM queries
        #TODO: cache invalidation, maybe decorate query to automate cache handling?
        self.cache = {}

        self.source_lang = None
        self.target_lang = None
        self.checker = None
        lang_controller = self.controller.main_controller.lang_controller
        checks_controller = self.controller.main_controller.checks_controller
        self._set_source_lang(None, lang_controller.source_lang.code)
        self._set_target_lang(None, lang_controller.target_lang.code)
        self._set_checker(None, checks_controller.code)
        self._connect_ids.append((lang_controller.connect('source-lang-changed', self._set_source_lang), lang_controller))
        self._connect_ids.append((lang_controller.connect('target-lang-changed', self._set_target_lang), lang_controller))
        self._connect_ids.append((checks_controller.connect('checker-set', self._set_checker), checks_controller))


    # METHODS #
    def destroy(self):
        self.save_config()
        #disconnect all signals
        [widget.disconnect(cid) for (cid, widget) in self._connect_ids]

    def query(self, tmcontroller, unit):
        """Attempt to give suggestions applicable to query_str.

        All TM backends must implement this method, check for
        suggested translations for unit, emit "match-found" on success."""
        pass

    def load_config(self):
        """load TM backend config from default location"""
        self.config = {}
        self.config.update(self.default_config)
        config_file = os.path.join(pan_app.get_config_dir(), "tm.ini")
        self.config.update(pan_app.load_config(config_file, self.internal_name))

    def save_config(self):
        """save TM backend config to default location"""
        config_file = os.path.join(pan_app.get_config_dir(), "tm.ini")
        pan_app.save_config(config_file, self.config, self.internal_name)

    def set_source_lang(self, language):
        """models override this to implement their own
        source-lang-changed event handlers"""
        pass

    def set_target_lang(self, language):
        """models override this to implement their own
        target-lang-changed event handlers"""
        pass

    def set_checker(self, checker):
        """models override this to implement their own
        checker-set event handlers"""
        pass

    def _set_source_lang(self, controller, language):
        """private method for baseline handling of source language
        change events"""
        if (language != self.source_lang):
            self.source_lang = language
            self.cache = {}
            self.set_source_lang(language)

    def _set_target_lang(self, controller, language):
        """private method for baseline handling of target language change events"""
        if (language != self.target_lang):
            self.target_lang = language
            self.cache = {}
            self.set_target_lang(language)

    def _set_checker(self, controller, checker):
        """private method for handling of project style change events"""
        if (checker != self.checker):
            self.checker = checker
            #TODO: consider:
            #self.cache = {}
            self.set_checker(checker)

########NEW FILE########
__FILENAME__ = currentfile
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from translate.search import match

from basetmmodel import BaseTMModel


class TMModel(BaseTMModel):
    """Translation memory model that matches against translated strings from current file"""

    __gtype_name__ = 'CurrentFileTMModel'
    display_name = _('Current File')
    description = _('Translated units from the currently open file')

    default_config = { 'max_length': 1000 }

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        super(TMModel, self).__init__(controller)

        self.matcher = None
        self.internal_name = internal_name
        self.load_config()

        self._connect_ids.append((
            self.controller.main_controller.store_controller.connect('store-loaded', self.recreate_matcher),
            self.controller.main_controller.store_controller
        ))
        if self.controller.main_controller.store_controller.get_store() is not None:
            self.recreate_matcher(self.controller.main_controller.store_controller)

        self._connect_ids.append((
            self.controller.main_controller.store_controller.unit_controller.connect('unit-done', self._on_unit_modified),
            self.controller.main_controller.store_controller.unit_controller
        ))


    # METHODS #
    def recreate_matcher(self, storecontroller):
        store = storecontroller.get_store()._trans_store
        if self.matcher is None:
            options = {
                'max_length': int(self.config['max_length']),
                'max_candidates': self.controller.max_matches,
                'min_similarity': self.controller.min_quality
            }
            self.matcher = match.matcher(store, **options)
        else:
            self.matcher.extendtm(store.units)
        self.cache = {}

    def query(self, tmcontroller, unit):
        query_str = unit.source
        matches = []
        # The cache is cleared when translated units change, so this is safe
        if query_str in self.cache:
            matches = self.cache[query_str]
        else:
            matches = self._check_other_units(unit)
            # Cache even empty results, so we don't need to query again
            self.cache[query_str] = matches
            # We don't want to cache alt trans, since this is different for
            # units with the same source text.

        matches += self._check_alttrans(unit)
        if matches:
            self.emit('match-found', query_str, matches)

    def _check_other_units(self, unit):
        matches = []

        query_str = unit.source
        if not isinstance(query_str, unicode):
            query_str = unicode(query_str, 'utf-8')

        for candidate in self.matcher.matches(query_str):
            m = match.unit2dict(candidate)
            #l10n: Try to keep this as short as possible.
            m['tmsource'] = _('This file')
            matches.append(m)
        return [m for m in matches if m['quality'] != u'100']

    def _check_alttrans(self, unit):
        if not hasattr(unit, 'getalttrans'):
            return []
        alttrans = unit.getalttrans()
        if not alttrans:
            return []

        from translate.search.lshtein import LevenshteinComparer
        lcomparer = LevenshteinComparer(max_len=1000)

        results = []
        for alt in alttrans:
            quality = lcomparer.similarity(unit.source, alt.source, self.controller.min_quality - 15)
            # let's check if it is useful, but be more lenient
            if quality < self.controller.min_quality - 10:
                continue
            tmsource = _('This file')

            xmlelement = getattr(alt, 'xmlelement', None)
            if xmlelement is not None:
                origin = alt.xmlelement.get('origin', '')
                if origin:
                    if origin == "lmc":
                        # Experimental code to test lmc research. Everything
                        # in a try block, just in case.
                        try:
                            from lxml import etree
                            import os.path
                            extras = xmlelement.xpath('processing-instruction()')
                            meta = dict((pi.target, pi.text) for pi in extras)
                            tmsource = [meta.get("contact-name", ""), meta.get("category", ""), os.path.splitext(meta.get("original", ""))[0]]
                            tmsource = u"\n".join(filter(None, tmsource))
                        except Exception, e:
                            import logging
                            logging.info(e)

                    tmsource += "\n" + origin

            results.append({
                'source': alt.source,
                'target': alt.target,
                'quality': quality,
                'tmsource': tmsource,
            })
        return results


    # EVENT HANDLERS #
    def _on_unit_modified(self, widget, new_unit, modified):
        """Add the new translation unit to the TM."""
        if modified and new_unit.istranslated():
            self.matcher.extendtm(new_unit)
            # This new target text might be relevant for other units that are
            # already cached, so let's remove ones with source text of similar
            # length
            min_quality = self.controller.min_quality
            start = self.matcher.getstartlength(min_quality, new_unit.source)
            stop = self.matcher.getstoplength(min_quality, new_unit.source)
            def unaffected(key):
                l = len(key)
                return l < start or l > stop

            self.cache = dict((k,v) for (k,v) in self.cache.iteritems() if unaffected(k))

########NEW FILE########
__FILENAME__ = google_translate
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
# Copyright 2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import urllib
import pycurl
# These two json modules are API compatible
try:
    import simplejson as json #should be a bit faster; needed for Python < 2.6
except ImportError:
    import json #available since Python 2.6

from basetmmodel import BaseTMModel, unescape_html_entities
from virtaal.support.httpclient import HTTPClient, RESTRequest


# Some codes are weird or can be reused for others
code_translation = {
    'fl': 'tl', # Filipino -> Tagalog
    'he': 'iw', # Weird code Google uses for Hebrew
    'nb': 'no', # Google maps no (Norwegian) to its Norwegian (Bokmål) (nb) translator
}

virtaal_referrer = "http://virtaal.org/"

class TMModel(BaseTMModel):
    """This is a Google Translate translation memory model.

    The plugin uses the U{Google AJAX Languages API<http://code.google.com/apis/ajaxlanguage/>}
    to query Google's machine translation services.  The implementation makes use of the 
    U{RESTful<http://code.google.com/apis/ajaxlanguage/documentation/#fonje>} interface for 
    Non-JavaScript environments.
    """

    __gtype_name__ = 'GoogleTranslateTMModel'
    #l10n: The name of Google Translate in your language (translated in most languages). See http://translate.google.com/
    display_name = _('Google Translate')
    description = _("Unreviewed machine translations from Google's translation service")
    default_config = {'api_key': ''}

    translate_url = "https://www.googleapis.com/language/translate/v2?key=%(key)s&q=%(message)s&source=%(from)s&target=%(to)s"
    languages_url = "https://www.googleapis.com/language/translate/v2/languages?key=%(key)s"

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        super(TMModel, self).__init__(controller)
        self.load_config()
        if not self.config['api_key']:
            self._disable_all("An API key is needed to use the Google Translate plugin")
            return
        self.client = HTTPClient()
        self._languages = set()
        langreq = RESTRequest(self.url_getlanguages % self.config, '')
        self.client.add(langreq)
        langreq.connect(
            'http-success',
            lambda langreq, response: self.got_languages(response)
        )

    # METHODS #
    def query(self, tmcontroller, unit):
        query_str = unit.source
        # Google's Terms of Service says the whole URL must be less than "2K"
        # characters.
        query_str = query_str[:2000 - len(self.translate_url)]
        source_lang = code_translation.get(self.source_lang, self.source_lang).replace('_', '-')
        target_lang = code_translation.get(self.target_lang, self.target_lang).replace('_', '-')
        if source_lang not in self._languages or target_lang not in self._languages:
            logging.debug('language pair not supported: %s => %s' % (source_lang, target_lang))
            return

        if self.cache.has_key(query_str):
            self.emit('match-found', query_str, self.cache[query_str])
        else:
            real_url = self.translate_url % {
                'key':     self.config['api_key'],
                'message': urllib.quote_plus(query_str.encode('utf-8')),
                'from':    source_lang,
                'to':      target_lang,
            }

            req = RESTRequest(real_url, '')
            self.client.add(req)
            # Google's Terms of Service says we need a proper HTTP referrer
            req.curl.setopt(pycurl.REFERER, virtaal_referrer)
            req.connect(
                'http-success',
                lambda req, response: self.got_translation(response, query_str)
            )
            req.connect(
                'http-client-error',
                lambda req, response: self.got_error(response, query_str)
            )
            req.connect(
                'http-server-error',
                lambda req, response: self.got_error(response, query_str)
            )

    def got_translation(self, val, query_str):
        """Handle the response from the web service now that it came in."""
        # In December 2011 version 1 of the API was deprecated, and we had to
        # release code to handle the eminent disappearance of the API. Although
        # version 2 is now supported, the code is a bit more careful (as most
        # code probably should be) and in case of error we make the list of
        # supported languages empty so that no unnecesary network activity is
        # performed if we can't communicate with the available API any more.
        try:
            data = json.loads(val)
            # We try to access the members to validate that the dictionary is
            # formed in the way we expect.
            data['data']
            data['data']['translations']
            text = data['data']['translations'][0]['translatedText']
        except Exception, e:
            self._disable_all("Error with json response: %s" % e)
            return

        target_unescaped = unescape_html_entities(text)
        if not isinstance(target_unescaped, unicode):
            target_unescaped = unicode(target_unescaped, 'utf-8')
        match = {
            'source': query_str,
            'target': target_unescaped,
            #l10n: Try to keep this as short as possible. Feel free to transliterate.
            'tmsource': _('Google')
        }
        self.cache[query_str] = [match]
        self.emit('match-found', query_str, [match])

    def got_languages(self, val):
        """Handle the response from the web service to set up language pairs."""
        try:
            data = json.loads(val)
            data['data']
            languages = data['data']['languages']
        except Exception, e:
            self._disable_all("Error with json response: %s" % e)
            return
        self._languages = set([l['language'] for l in languages])

    def got_error(self, val, query_str):
        self._disable_all("Got an error response: %s" % val)

    def _disable_all(self, reason):
        self._languages = set()
        logging.debug("Stopping all queries for Google Translate. %s" % reason)

########NEW FILE########
__FILENAME__ = libtranslate
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import ctypes.util
from ctypes import *
if not ctypes.util.find_library("translate"):
    raise ImportError("libtranslate not found")

import logging
from translate.misc import quote

from virtaal.common import pan_app

from basetmmodel import BaseTMModel


class TMModel(BaseTMModel):
    """This is a libtranslate translation memory model.

    The plugin does the following: initialise libtranslate, get the services, get a session.
    During operation it simply queries libtranslate for a translation.  This follows the
    pattern outlined in file:///usr/share/gtk-doc/html/libtranslate/tutorials.html (sorry
    no online version found, use the one packaged with libtranslate).
    """

    __gtype_name__ = 'LibtranslateTMModel'
    #l10n: This is the name of a software library. You almost definitely don't want to translate this. The lower case 'l' is intentional.
    display_name = _('libtranslate')
    description = _('Unreviewed machine translations from various services')

    # TODO - allow the user to configure which systems to query for translations, default will be all`


    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name

        self.lt = cdll.LoadLibrary(ctypes.util.find_library("translate"))

        # Define all used functions
        self.lt.translate_init.argtypes = [c_int]
        self.lt.translate_init.restype = c_int
        self.lt.translate_get_services.restype = c_int
        self.lt.translate_session_new.argtype = [c_int]
        self.lt.translate_session_new.restype = c_int
        self.lt.translate_session_translate_text.argtype = [c_int, c_char_p, c_char_p, c_char_p, c_int, c_int, c_int]
        self.lt.translate_session_translate_text.restype = c_char_p

        # Initialise libtranslate
        err = c_int()
        if not self.lt.translate_init(err):
            # TODO: cleanup memory used by err
            raise Exception("Unable to initialise libtranslate: %s" % err)

        services = self.lt.translate_get_services()
        self.session = self.lt.translate_session_new(services)
        # TODO see file:///usr/share/gtk-doc/html/libtranslate/tutorials.html
        # g_slist_foreach(services, (GFunc) g_object_unref, NULL);
        # g_slist_free(services);

        super(TMModel, self).__init__(controller)


    # METHODS #
    def query(self, tmcontroller, unit):
        query_str = unit.source
        translation = []
        err = c_int()
        result = self.lt.translate_session_translate_text(
            self.session, query_str,
            self.source_lang, self.target_lang,
            None, None, err
        )
        if result is None:
            # TODO handle errors and cleanup errors
            logging.warning("An error occured while getting a translation: %s" % err)
            return
        if not isinstance(result, unicode):
            result = unicode(result, 'utf-8') # XXX: The encoding is just a guess
        translation.append({
            'source': query_str,
            'target': quote.rstripeol(result),
            #l10n: Try to keep this as short as possible. Feel free to transliterate in CJK languages for vertical display optimization.
            'tmsource': _('libtranslate')
        })

        # TODO: drop any memory used by 'result'
        self.emit('match-found', query_str, translation)

########NEW FILE########
__FILENAME__ = localtm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009,2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import os
import sys
import socket

from virtaal.common import pan_app
from basetmmodel import BaseTMModel
import remotetm


class TMModel(remotetm.TMModel):
    """This is the translation memory model."""

    __gtype_name__ = 'LocalTMModel'
    display_name = _('Local Translation Memory')
    description = _('Previous translations you have made')
    #l10n: Try to keep this as short as possible.
    shortname = _('Local TM')

    default_config = {
        "tmserver_bind" : "localhost",
        "tmserver_port" : "55555",
        "tmdb" : os.path.join(pan_app.get_config_dir(), u"tm.db")
    }

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        self.load_config()

        # test if port specified in config is free
        self.config["tmserver_port"] = int(self.config["tmserver_port"])
        if test_port(self.config["tmserver_bind"], self.config["tmserver_port"]):
            port = self.config["tmserver_port"]
        else:
            port = find_free_port(self.config["tmserver_bind"], 49152, 65535)
        if os.name == "nt":
            executable = os.path.abspath(os.path.join(pan_app.main_dir, u"tmserver.exe"))
        else:
            executable = u"tmserver"

        command = [
            executable.encode(sys.getfilesystemencoding()),
            "-b", self.config["tmserver_bind"],
            "-p", str(port),
            "-d", self.config["tmdb"].encode(sys.getfilesystemencoding()),
            "--min-similarity=%d" % controller.min_quality,
            "--max-candidates=%d" % controller.max_matches,
        ]

        if pan_app.DEBUG:
            command.append("--debug")

        logging.debug("launching tmserver with command %s" % " ".join(command))
        try:
            import subprocess
            from virtaal.support import tmclient
            self.tmserver = subprocess.Popen(command)
            url = "http://%s:%d/tmserver" % (self.config["tmserver_bind"], port)

            self.tmclient = tmclient.TMClient(url)
        except OSError, e:
            message = "Failed to start TM server: %s" % str(e)
            logging.exception('Failed to start TM server')
            raise

        # Do not use super() here, as remotetm.TMModel does a bit more than we
        # want in this case.
        BaseTMModel.__init__(self, controller)
        self._connect_ids.append((
            self.controller.main_controller.store_controller.connect("store-saved", self.push_store),
            self.controller.main_controller.store_controller
        ))

    def destroy(self):
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.TerminateProcess(int(self.tmserver._handle), -1)
            logging.debug("killing tmserver with handle %d" % int(self.tmserver._handle))
        else:
            import signal
            os.kill(self.tmserver.pid, signal.SIGTERM)
            logging.debug("killing tmserver with pid %d" % self.tmserver.pid)


def test_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except socket.error:
        return False


def find_free_port(host, min_port, max_port):
    import random
    port_range = range(min_port, max_port)
    random.shuffle(port_range)
    for port in port_range:
        if test_port(host, port):
            return port
    #FIXME: shall we throw an exception if no free port is found?
    return None

########NEW FILE########
__FILENAME__ = microsoft_translator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""A TM provider that can query the web service for Micrsoft Translator
Machine Translations."""

import urllib

from basetmmodel import BaseTMModel

from virtaal.support.httpclient import HTTPClient, RESTRequest

# Code corrections
code_translation = {
    'zh_CN': 'zh-CHS', # Simplified
    'zh_TW': 'zh-CHT', # Traditional
    'nb': 'no', # Norwegian (Nyorks) uses no not nb
}

def strip_bom(string):
    if string[0] == u'\ufeff':
        return string[1:]
    return string

class TMModel(BaseTMModel):
    """This is the translation memory model."""

    __gtype_name__ = 'MicrosoftTranslatorTMModel'
    display_name = _('Microsoft Translator')
    description = _('Unreviewed machine translations from Microsoft Translator')

    default_config = {
        "url" : "http://api.microsofttranslator.com/V1/Http.svc",
        "appid" : "7286B45B8C4816BDF75DC007C1952DDC11C646C1",
    }

    # INITIALISERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        self.languages = []
        self.load_config()

        self.client = HTTPClient()
        self.url_getlanguages = "%(url)s/GetLanguages?appId=%(appid)s" % {"url": self.config['url'], "appid": self.config["appid"]}
        self.url_translate = "%(url)s/Translate" % {"url": self.config['url']}
        self.appid = self.config['appid']
        langreq = RESTRequest(self.url_getlanguages, '')
        self.client.add(langreq)
        langreq.connect(
            'http-success',
            lambda langreq, response: self.got_languages(response)
        )

        super(TMModel, self).__init__(controller)


    # METHODS #
    def query(self, tmcontroller, unit):
        """Send the query to the web service. The response is handled by means
        of a call-back because it happens asynchronously."""
        source_lang = code_translation.get(self.source_lang, self.source_lang)
        target_lang = code_translation.get(self.target_lang, self.target_lang)
        if source_lang not in self.languages or target_lang not in self.languages:
            return

        query_str = unit.source
        if self.cache.has_key(query_str):
            self.emit('match-found', query_str, self.cache[query_str])
        else:
            values = {
                'appId': self.appid,
                'text': query_str,
                'from': source_lang,
                'to': target_lang
            }
            req = RESTRequest(self.url_translate + "?" + urllib.urlencode(values), '')
            self.client.add(req)
            req.connect(
                'http-success',
                lambda req, response: self.got_translation(response, query_str)
            )

    def got_languages(self, val):
        """Handle the response from the web service to set up language pairs."""
        val = strip_bom(val.decode('utf-8')).strip()
        self.languages = [lang for lang in val.split('\r\n')]

    def got_translation(self, val, query_str):
        """Handle the response from the web service now that it came in."""
        if not isinstance(val, unicode):
            val = unicode(val, 'utf-8')
        val = strip_bom(val)
        match = {
            'source': query_str,
            'target': val,
            #l10n: Try to keep this as short as possible. Feel free to transliterate in CJK languages for optimal vertical display.
            'tmsource': _('Microsoft'),
        }
        self.cache[query_str] = [match]

        self.emit('match-found', query_str, [match])

########NEW FILE########
__FILENAME__ = moses
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


from basetmmodel import BaseTMModel


class TMModel(BaseTMModel):
    """This is the Moses translation memory model.

    The plugin uses the Moses Statistical Machine Translation software's server to
    query over RPC for MT suggestions."""

    __gtype_name__ = 'MosesTMModel'
    display_name = _('Moses')
    description = _('Unreviewed machine translations from a Moses server')

    default_config = { "fr->en": "http://localhost:8080", }

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        super(TMModel, self).__init__(controller)

        self.load_config()
        self.clients = {}
        self._init_plugin()

    def _init_plugin(self):
        from virtaal.support.mosesclient import MosesClient
        # let's map servers to clients to detect duplicates
        client_map = {}
        for lang_pair, server in self.config.iteritems():
            pair = lang_pair.split("->")
            if self.clients.get(pair[0]) is None:
                self.clients[pair[0]] = {}
            if server in client_map:
                client = client_map[server]
                client.set_multilang()
            else:
                client = MosesClient(server)
                client_map[server] = client
            self.clients[pair[0]].update({pair[1]: client})


    # METHODS #
    def query(self, tmcontroller, unit):
        if self.source_lang in self.clients and self.target_lang in self.clients[self.source_lang]:
            query_str = unicode(unit.source) # cast in case of multistrings
            if query_str in self.cache:
                self.emit('match-found', query_str, [self.cache[query_str]])
                return

            client = self.clients[self.source_lang][self.target_lang]
            client.translate_unit(query_str, self._handle_response, self.target_lang)
            return

    def _handle_response(self, id, response):
        if not response:
            return
        result = {
            'source': id,
            'target': response,
            #l10n: Try to keep this as short as possible. Feel free to transliterate in CJK languages for vertical display optimization.
            'tmsource': _('Moses'),
        }

        self.cache[id] = result
        self.emit('match-found', id, [result])

########NEW FILE########
__FILENAME__ = opentran
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from virtaal.support import opentranclient

from virtaal.common import pan_app

from basetmmodel import BaseTMModel

# Some names are a bit too long, so let's "translate" them to something shorter
new_names = {
        'OpenOffice.org': 'OpenOffice',
        'Debian Installer': 'Debian Inst.',
}

class TMModel(BaseTMModel):
    """This is the translation memory model."""

    __gtype_name__ = 'OpenTranTMModel'
    display_name = _('Open-Tran.eu')
    description = _('Previous translations for Free and Open Source Software')

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        self.load_config()

        self.tmclient = opentranclient.OpenTranClient(
            max_candidates=controller.max_matches,
            min_similarity=controller.min_quality
        )

        super(TMModel, self).__init__(controller)


    # METHODS #
    def set_source_lang(self, language):
        self.tmclient.set_source_lang(language)

    def set_target_lang(self, language):
        self.tmclient.set_target_lang(language)

    def query(self, tmcontroller, unit):
        query_str = unit.source
        if self.cache.has_key(query_str):
            self.emit('match-found', query_str, self.cache[query_str])
        else:
            self.tmclient.translate_unit(query_str, self._handle_matches)

    def _handle_matches(self, widget, query_str, matches):
        """Handle the matches when returned from self.tmclient."""
        for match in matches:
            if not isinstance(match['target'], unicode):
                match['target'] = unicode(match['target'], 'utf-8')
            if 'tmsource' in match:
                # Try to replace some long names like "OpenOffice.org" which
                # doesn't display nicely:
                match['tmsource'] = new_names.get(match['tmsource']) or match['tmsource']
                #l10n: Try to keep this as short as possible. Feel free to transliterate in CJK languages for vertical display optimization.
                match['tmsource'] = _('OpenTran') + '\n' + match['tmsource']
            else:
                match['tmsource'] = _('OpenTran')
        self.cache[query_str] = matches
        self.emit('match-found', query_str, matches)

########NEW FILE########
__FILENAME__ = remotetm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from basetmmodel import BaseTMModel


class TMModel(BaseTMModel):
    """TM back-end that allows Virtaal to connect to a remote TM server."""

    __gtype_name__ = 'RemoteTMModel'
    display_name = _('Remote Server')
    description = _('A translation memory server')
    #l10n: Try to keep this as short as possible.
    shortname = _('Remote TM')

    default_config = {
        "host" : "localhost",
        "port" : "55555",
    }

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        super(TMModel, self).__init__(controller)
        self.internal_name = internal_name
        self.load_config()
        url = "http://%s:%s/tmserver" % (self.config["host"], self.config["port"])

        from virtaal.support import tmclient
        self.tmclient = tmclient.TMClient(url)
        self.tmclient.set_virtaal_useragent()


    # METHODS #
    def query(self, tmcontroller, unit):
        # We don't want to do lookups in case of misconfigurations like en->en
        if self.source_lang == self.target_lang:
            return

        # TODO: Figure out languages
        query_str = unit.source
        if query_str in self.cache:
            _cached = self.cache[query_str]
            if _cached:
                # Only emit if we actually have something to offer
                self.emit('match-found', query_str, _cached)
        else:
            params = {}
            if self.checker:
                params['style'] = self.checker
            self.tmclient.translate_unit(query_str, self.source_lang, self.target_lang, self._handle_matches, params)

    def _handle_matches(self, widget, query_str, matches):
        """Handle the matches when returned from self.tmclient."""
        self.cache[query_str] = matches or None # None instead of empty list
        if matches:
            for match in matches:
                match['tmsource'] = self.shortname
                if not isinstance(match['target'], unicode):
                    match['target'] = unicode(match['target'], 'utf-8')
            self.emit('match-found', query_str, matches)

    def push_store(self, store_controller):
        """Add units in store to TM database on save."""
        units = []
        for unit in store_controller.store.get_units():
            if  unit.istranslated():
                units.append(unit2dict(unit))
        #FIXME: do we get source and target langs from
        #store_controller or from tm state?
        self.tmclient.add_store(store_controller.store.get_filename(), units, self.source_lang, self.target_lang)
        self.cache = {}

    def upload_store(self, store_controller):
        """Upload store to TM server."""
        self.tmclient.upload_store(store_controller.store._trans_store, self.source_lang, self.target_lang)
        self.cache = {}


def unit2dict(unit):
    return {"source": unit.source, "target": unit.target, "context": unit.getcontext()}

########NEW FILE########
__FILENAME__ = test_basetmmodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from basetmmodel import unescape_html_entities

def test_unescape_html_entities():
    """Test the unescaping of &amp; and &#39; type HTML escapes"""
    assert unescape_html_entities("This &amp; That") == "This & That"
    assert unescape_html_entities("&#39;n Vertaler") == "'n Vertaler"
    assert unescape_html_entities("Copyright &copy; 2009 Virtaa&#7741;") == u"Copyright © 2009 Virtaaḽ"

########NEW FILE########
__FILENAME__ = tinytm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
# Copyright 2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import logging

from virtaal.common import pan_app

from basetmmodel import BaseTMModel
from virtaal.controllers.baseplugin import PluginUnsupported


MAX_ERRORS = 5


class TMModel(BaseTMModel):
    """This is a TinyTM translation memory model.

    Built according the l{protocol<http://tinytm.org/en/technology/protocol.html>} defined
    by the TinyTM project.
    """

    __gtype_name__ = 'TinyTmTMModel'
    display_name = _('TinyTM')
    description = _('A TinyTM translation memory server')

    default_config = {
        "server":   "localhost",
        "username": "postgres",
        "password": "",
        "database": "tinytm",
        "port": "5432",
    }

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        self.load_config()

        try:
            import psycopg2
            self.psycopg2 = psycopg2
        except ImportError:
            raise PluginUnsupported("The psycopg2 package is required for TinyTM")

        # We count errors so that we can disable the plugin if it experiences
        # multiple problems. If still negative, it means we were never able to
        # connect, so we can disable the plugin completely.
        self._errors = -1

        self._db_con = self.psycopg2.connect(
            database=self.config["database"],
            user=self.config["username"],
            password=self.config["password"],
            host=self.config["server"],
            async=1,
            port=self.config["port"],
        )
        self.wait()
        self._errors = 0

        super(TMModel, self).__init__(controller)


    # METHODS #
    def query(self, tmcontroller, unit):
        if self._db_con.closed or self._db_con.isexecuting():
            # Two cursors can't execute concurrently on an asynchronous
            # connection. We could try to cancel the old one, but if it hasn't
            # finished yet, it might be busy. So let's rather not pile on
            # another query to avoid overloading the server.
            return

        query_str = unit.source
        matches = []
        cursor = self._db_con.cursor()
        try:
            cursor.execute(
                """SELECT * FROM tinytm_get_fuzzy_matches(%s, %s, %s, '', '')""",
                (self.source_lang, self.target_lang, query_str.encode('utf-8'))
            )
            # You can connect to any postgres database and use this for basic
            # testing:
            #cursor.execute("""select pg_sleep(2); SELECT 99, 'source', 'target';""")
            # Uncomment this if you don't trust the results
            #cursor.execute("""SELECT * FROM tinytm_get_fuzzy_matches('en', 'de', 'THE EUROPEAN ECONOMIC COMMUNITY', '', '')""")
        except self.psycopg2.Error, e:
            self.error(e)
        self.wait()
        for result in cursor.fetchall():
            quality, source, target = result[:3]
            if not isinstance(target, unicode):
                target = unicode(target, 'utf-8')
            matches.append({
                'source': source,
                'target': target,
                'quality': quality,
                'tmsource': self.display_name,
            })

        self.emit('match-found', query_str, matches)

    def wait(self):
        import select
        while 1:
            while gtk.events_pending():
                gtk.main_iteration()
            try:
                state = self._db_con.poll()
            except self.psycopg2.Error, e:
                self.error(e)

            if state == self.psycopg2.extensions.POLL_OK:
                break
            elif state == self.psycopg2.extensions.POLL_WRITE:
                select.select([], [self._db_con.fileno()], [], 0.05)
            elif state == self.psycopg2.extensions.POLL_READ:
                select.select([self._db_con.fileno()], [], [], 0.05)
            else:
                self.error()
                raise self.psycopg2.OperationalError("poll() returned %s" % state)

    def error(self, e=None):
        if self._errors < 0:
            # We're still busy initialising
            raise PluginUnsupported("Unable to connect to the TinyTM server.")

        if e:
            logging.error("[%s] %s" % (e.pgcode, e.pgerror))
        self._errors += 1
        if self._errors > MAX_ERRORS:
            self._db_con.close()

    def destroy(self):
        super(TMModel, self).destroy()
        self._db_con.close()

########NEW FILE########
__FILENAME__ = _dummytm
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from basetmmodel import BaseTMModel


class TMModel(BaseTMModel):
    """This is a dummy (testing) translation memory model."""

    __gtype_name__ = 'DummyTMModel'
    display_name = _('Dummy TM provider for testing')
    description = _('A translation memory suggestion providers that is only useful for testing')

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.internal_name = internal_name
        super(TMModel, self).__init__(controller)


    # METHODS #
    def query(self, tmcontroller, unit):
        query_str = unit.source
        tm_matches = []
        tm_matches.append({
            'source': 'This match has no "quality" field',
            'target': u'Hierdie woordeboek het geen "quality"-veld nie.',
            'tmsource': 'DummyTM'
        })
        tm_matches.append({
            'source': query_str.lower(),
            'target': query_str.upper(),
            'quality': 100,
            'tmsource': 'DummyTM'
        })
        reverse_str = list(query_str)
        reverse_str.reverse()
        reverse_str = u''.join(reverse_str)
        tm_matches.append({
            'source': reverse_str.lower(),
            'target': reverse_str.upper(),
            'quality': 32,
            'tmsource': 'DummyTM'
        })

        self.emit('match-found', query_str, tm_matches)

########NEW FILE########
__FILENAME__ = tmcontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import os.path
from translate.lang.data import forceunicode, normalize

from virtaal.controllers.basecontroller import BaseController


class TMController(BaseController):
    """The logic-filled glue between the TM view and -model."""

    __gtype_name__ = 'TMController'
    __gsignals__ = {
        'start-query': (gobject.SIGNAL_RUN_FIRST, None, (object,))
    }

    QUERY_DELAY = 300
    """The delay after a unit is selected (C{Cursor}'s "cursor-changed" event)
        before the TM is queried."""

    # INITIALIZERS #
    def __init__(self, main_controller, config={}):
        from virtaal.common import GObjectWrapper
        GObjectWrapper.__init__(self)

        self.config = config
        self.main_controller = main_controller
        self.disabled_model_names = ['basetmmodel'] + self.config.get('disabled_models', [])
        self.max_matches = self.config.get('max_matches', 5)
        self.min_quality = self.config.get('min_quality', 75)

        self._signal_ids = {}
        from tmview import TMView
        self.storecursor = None
        self.view = TMView(self, self.max_matches)
        self._load_models()

        self._connect_plugin()

    def _connect_plugin(self):
        self._store_loaded_id = self.main_controller.store_controller.connect('store-loaded', self._on_store_loaded)
        self._store_closed_id = self.main_controller.store_controller.connect('store-closed', self._on_store_closed)
        if self.main_controller.store_controller.get_store() is not None:
            self._on_store_loaded(self.main_controller.store_controller)
            self.view._should_show_tmwindow = True

        if self.main_controller.mode_controller is not None:
            self._mode_selected_id = self.main_controller.mode_controller.connect('mode-selected', self._on_mode_selected)

    def _load_models(self):
        from virtaal.controllers.plugincontroller import PluginController
        self.plugin_controller = PluginController(self, 'TMModel')
        self.plugin_controller.PLUGIN_CLASS_INFO_ATTRIBS = ['display_name', 'description']
        new_dirs = []
        for dir in self.plugin_controller.PLUGIN_DIRS:
           new_dirs.append(os.path.join(dir, 'tm', 'models'))
        self.plugin_controller.PLUGIN_DIRS = new_dirs

        from models.basetmmodel import BaseTMModel
        self.plugin_controller.PLUGIN_INTERFACE = BaseTMModel
        self.plugin_controller.PLUGIN_MODULES = ['virtaal_plugins.tm.models', 'virtaal.plugins.tm.models']
        self.plugin_controller.get_disabled_plugins = lambda *args: self.disabled_model_names

        self._model_signal_ids = {}
        def on_plugin_enabled(plugin_ctrlr, plugin):
            self._model_signal_ids[plugin] = plugin.connect('match-found', self.accept_response)
        def on_plugin_disabled(plugin_ctrlr, plugin):
            plugin.disconnect(self._model_signal_ids[plugin])
        self._signal_ids['plugin-enabled']  = self.plugin_controller.connect('plugin-enabled',  on_plugin_enabled)
        self._signal_ids['plugin-disabled'] = self.plugin_controller.connect('plugin-disabled', on_plugin_disabled)

        self.plugin_controller.load_plugins()


    # METHODS #
    def accept_response(self, tmmodel, query_str, matches):
        """Accept a query-response from the model.
            (This method is used as Model-Controller communications)"""
        if not self.storecursor:
            # File closed since the query was started
            return
        query_str = forceunicode(query_str)
        if query_str != self.current_query or not matches:
            return
        # Perform some sanity checks on matches first
        for match in matches:
            if not isinstance(match.get('quality', 0), int):
                match['quality'] = int(match['quality'] or 0)
            if 'tmsource' not in match or match['tmsource'] is None:
                match['tmsource'] = tmmodel.display_name
            match['query_str'] = query_str

        anything_new = False
        for match in matches:
            curr_targets = [normalize(m['target']) for m in self.matches]
            if normalize(match['target']) not in curr_targets:
                # Let's insert at the end to prioritise existing matches over
                # new ones. We rely on the guarantee of sort stability. This
                # way an existing 100% will be above a new 100%.
                self.matches.append(match)
                anything_new = True
            else:
                norm_match_target = normalize(match['target'])
                prevmatch = [m for m in self.matches if normalize(m['target']) == norm_match_target][0]
                if 'quality' not in prevmatch or not prevmatch['quality']:
                    # Matches without quality are assumed to be less appropriate
                    # (ie. MT matches) than matches with an associated quality.
                    self.matches.remove(prevmatch)
                    self.matches.append(match)
                    anything_new = True
        if not anything_new:
            return
        self.matches.sort(key=lambda x: 'quality' in x and x['quality'] or 0, reverse=True)
        self.matches = self.matches[:self.max_matches]

        # Only call display_matches if necessary:
        if self.matches:
            self.view.display_matches(self.matches)

    def destroy(self):
        # Destroy the view
        self.view.hide()
        self.view.destroy()

        # Disconnect signals
        self.main_controller.store_controller.disconnect(self._store_loaded_id)
        if getattr(self, '_cursor_changed_id', None):
            self.main_controller.store_controller.cursor.disconnect(self._cursor_changed_id)
        if getattr(self, '_mode_selected_id', None):
            self.main_controller.mode_controller.disconnect(self._mode_selected_id)
        if getattr(self, '_target_focused_id', None):
            self.main_controller.unit_controller.view.disconnect(self._target_focused_id)

        self.plugin_controller.shutdown()

    def select_match(self, match_data):
        """Handle a match-selection event.
            (This method is used as View-Controller communications)"""
        unit_controller = self.main_controller.unit_controller
        target_n = unit_controller.view.focused_target_n
        old_text = unit_controller.view.get_target_n(target_n)
        textbox =  unit_controller.view.targets[target_n]
        self.main_controller.undo_controller.push_current_text(textbox)
        unit_controller.set_unit_target(target_n, forceunicode(match_data['target']))

    def send_tm_query(self, unit=None):
        """Send a new query to the TM engine.
            (This method is used as Controller-Model communications)"""
        if unit is not None:
            self.unit = unit

        self.current_query = self.unit.source
        self.matches = []
        self.view.clear()
        self.emit('start-query', self.unit)

    def start_query(self):
        """Start a TM query after C{self.QUERY_DELAY} milliseconds."""
        if not self.storecursor:
            return

        if not hasattr(self, 'unit'):
            self.unit = self.storecursor.deref()

        self.unit_view = self.main_controller.unit_controller.view
        if getattr(self, '_target_focused_id', None) and getattr(self, 'unit_view', None):
            self.unit_view.disconnect(self._target_focused_id)
        self._target_focused_id = self.unit_view.connect('target-focused', self._on_target_focused)
        self.view.hide()

        def start_query():
            self.send_tm_query()
            return False
        if getattr(self, '_delay_id', 0):
            gobject.source_remove(self._delay_id)
        self._delay_id = gobject.timeout_add(self.QUERY_DELAY, start_query)


    # EVENT HANDLERS #
    def _on_cursor_changed(self, cursor):
        self.storecursor = cursor
        self.unit = cursor.deref()

        if self.unit is None:
            return

        if self.view.active and self.unit.istranslated():
            self.view.mnu_suggestions.set_active(False)
        elif not self.view.active and not self.unit.istranslated():
            self.view.mnu_suggestions.set_active(True)

        return self.start_query()

    def _on_mode_selected(self, modecontroller, mode):
        self.view.update_geometry()

    def _on_store_closed(self, storecontroller):
        if hasattr(self, '_cursor_changed_id') and self.storecursor:
            self.storecursor.disconnect(self._cursor_changed_id)
        self.storecursor = None
        self._cursor_changed_id = 0
        self.view.hide()

    def _on_store_loaded(self, storecontroller):
        """Disconnect from the previous store's cursor and connect to the new one."""
        if getattr(self, '_cursor_changed_id', None) and self.storecursor:
            self.storecursor.disconnect(self._cursor_changed_id)
        self.storecursor = storecontroller.cursor
        self._cursor_changed_id = self.storecursor.connect('cursor-changed', self._on_cursor_changed)

        def handle_first_unit():
            self._on_cursor_changed(self.storecursor)
            return False
        gobject.idle_add(handle_first_unit)

    def _on_target_focused(self, unitcontroller, target_n):
        #import logging
        #logging.debug('target_n: %d' % (target_n))
        self.view.update_geometry()

########NEW FILE########
__FILENAME__ = tmview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gobject
import logging
from gtk import gdk

from virtaal.common import GObjectWrapper
from virtaal.views.baseview import BaseView

from tmwidgets import *


class TMView(BaseView, GObjectWrapper):
    """The fake drop-down menu in which the TM matches are displayed."""

    __gtype_name__ = 'TMView'
    __gsignals__ = {
        'tm-match-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    # INITIALIZERS #
    def __init__(self, controller, max_matches):
        GObjectWrapper.__init__(self)

        self.controller = controller
        self.isvisible = False
        self.max_matches = max_matches
        self._may_show_tmwindow = True # is it allowed to display now (application is in focus)
        self._should_show_tmwindow = False # should it be displayed now (even if it doesn't, due to application focus?
        self._signal_ids = []

        self.tmwindow = TMWindow(self)
        main_window = self.controller.main_controller.view.main_window

        self._signal_ids.append((
            self.tmwindow.treeview,
            self.tmwindow.treeview.connect('row-activated', self._on_row_activated)
        ))
        self._signal_ids.append((
            controller.main_controller.store_controller.view.parent_widget.get_vscrollbar(),
            controller.main_controller.store_controller.view.parent_widget.get_vscrollbar().connect('value-changed', self._on_store_view_scroll)
        ))
        self._signal_ids.append((
            main_window,
            main_window.connect('focus-in-event', self._on_focus_in_mainwindow)
        ))
        self._signal_ids.append((
            main_window,
            main_window.connect('focus-out-event', self._on_focus_out_mainwindow)
        ))
        self._signal_ids.append((
            main_window,
            main_window.connect('configure_event', self._on_configure_mainwindow)
        ))
        self._signal_ids.append((
            controller.main_controller.store_controller,
            controller.main_controller.store_controller.connect('store-closed', self._on_store_closed)
        ))
        self._signal_ids.append((
            controller.main_controller.store_controller,
            controller.main_controller.store_controller.connect('store-loaded', self._on_store_loaded)
        ))

        self._setup_key_bindings()
        self._setup_menu_items()

    def _setup_key_bindings(self):
        """Setup Gtk+ key bindings (accelerators)."""

        gtk.accel_map_add_entry("<Virtaal>/TM/Hide TM", gtk.keysyms.Escape, 0)

        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<Virtaal>/TM/Hide TM", self._on_hide_tm)

        # Connect Ctrl+n (1 <= n <= 9) to select match n.
        for i in range(1, 10):
            numstr = str(i)
            numkey = gtk.keysyms._0 + i
            gtk.accel_map_add_entry("<Virtaal>/TM/Select match " + numstr, numkey, gdk.CONTROL_MASK)
            self.accel_group.connect_by_path("<Virtaal>/TM/Select match " + numstr, self._on_select_match)

        mainview = self.controller.main_controller.view
        mainview.add_accel_group(self.accel_group)

    def _setup_menu_items(self):
        mainview = self.controller.main_controller.view
        menubar = mainview.menubar
        self.mnui_view = mainview.gui.get_object('menuitem_view')
        self.menu = self.mnui_view.get_submenu()

        self.mnu_suggestions = gtk.CheckMenuItem(label=_('Translation _Suggestions'))
        self.mnu_suggestions.show()
        self.menu.append(self.mnu_suggestions)

        gtk.accel_map_add_entry("<Virtaal>/TM/Toggle Show TM", gtk.keysyms.F9, 0)
        accel_group = self.menu.get_accel_group()
        if accel_group is None:
            accel_group = self.accel_group
            self.menu.set_accel_group(self.accel_group)
        self.mnu_suggestions.set_accel_path("<Virtaal>/TM/Toggle Show TM")
        self.menu.set_accel_group(accel_group)

        self.mnu_suggestions.connect('toggled', self._on_toggle_show_tm)
        self.mnu_suggestions.set_active(True)


    # ACCESSORS #
    def _get_active(self):
        return self.mnu_suggestions.get_active()
    active = property(_get_active)


    # METHODS #
    def clear(self):
        """Clear the TM matches."""
        self.tmwindow.liststore.clear()
        self.hide()

    def destroy(self):
        for gobj, signal_id in self._signal_ids:
            gobj.disconnect(signal_id)

        self.menu.remove(self.mnu_suggestions)

    def display_matches(self, matches):
        """Add the list of TM matches to those available and show the TM window."""
        liststore = self.tmwindow.liststore
        liststore.clear()
        for match in matches:
            tooltip = ''
            if len(liststore) <= 9:
                tooltip = _('Ctrl+%(number_key)d') % {"number_key": len(liststore)+1}
            liststore.append([match, tooltip])

        if len(liststore) > 0:
            self.show()
            self.update_geometry()

    def get_target_width(self):
        if not hasattr(self.controller, 'unit_view'):
            return -1
        n = self.controller.unit_view.focused_target_n
        textview = self.controller.unit_view.targets[n]
        return textview.get_allocation().width

    def hide(self):
        """Hide the TM window."""
        self.tmwindow.hide()
        self.isvisible = False

    def select_backends(self, parent):
        from virtaal.views.widgets.selectdialog import SelectDialog
        selectdlg = SelectDialog(
            #l10n: The 'sources' here refer to different translation memory plugins,
            #such as local tm, open-tran.eu, the current file, etc.
            title=_('Select sources of Translation Memory'),
            message=_('Select the sources that should be queried for translation memory'),
            parent=parent,
            size=(400, 580),
        )
        selectdlg.set_icon(self.controller.main_controller.view.main_window.get_icon())

        items = []
        plugin_controller = self.controller.plugin_controller
        for plugin_name in plugin_controller._find_plugin_names():
            if plugin_name == 'basetmmodel':
                continue
            try:
                info = plugin_controller.get_plugin_info(plugin_name)
            except Exception, e:
                logging.debug('Problem getting information for plugin %s' % plugin_name)
                continue
            enabled = plugin_name in plugin_controller.plugins
            config = enabled and plugin_controller.plugins[plugin_name].configure_func or None
            items.append({
                'name': info['display_name'],
                'desc': info['description'],
                'data': {'internal_name': plugin_name},
                'enabled': enabled,
                'config': config,
            })

        def item_enabled(dlg, item):
            internal_name = item['data']['internal_name']
            plugin_controller.enable_plugin(internal_name)
            if internal_name in self.controller.config['disabled_models']:
                self.controller.config['disabled_models'].remove(internal_name)

        def item_disabled(dlg, item):
            internal_name = item['data']['internal_name']
            plugin_controller.disable_plugin(internal_name)
            if internal_name not in self.controller.config['disabled_models']:
                self.controller.config['disabled_models'].append(internal_name)

        selectdlg.connect('item-enabled',  item_enabled)
        selectdlg.connect('item-disabled', item_disabled)
        selectdlg.run(items=items)

    def select_match(self, match_data):
        """Select the match data as accepted by the user."""
        self.controller.select_match(match_data)

    def select_match_index(self, index):
        """Select the TM match with the given index (first match is 1).
            This method causes a row in the TM window's C{gtk.TreeView} to be
            selected and activated. This runs this class's C{_on_select_match()}
            method which runs C{select_match()}."""
        if index < 0 or not self.isvisible:
            return

        logging.debug('Selecting index %d' % (index))
        liststore = self.tmwindow.liststore
        itr = liststore.get_iter_first()

        i=1
        while itr and i < index and liststore.iter_is_valid(itr):
            itr = liststore.iter_next(itr)
            i += 1

        if not itr or not liststore.iter_is_valid(itr):
            return

        path = liststore.get_path(itr)
        self.tmwindow.treeview.get_selection().select_iter(itr)
        self.tmwindow.treeview.row_activated(path, self.tmwindow.tvc_match)

    def show(self, force=False):
        """Show the TM window."""
        if not self.active or (self.isvisible and not force) or not self._may_show_tmwindow:
            return # This window is already visible
        self.tmwindow.show_all()
        self.isvisible = True
        self._should_show_tmwindow = False

    def update_geometry(self):
        """Update the TM window's position and size."""
        def update():
            selected = self._get_selected_unit_view()
            if selected:
                self.tmwindow.update_geometry(selected)
        gobject.idle_add(update)

    def _get_selected_unit_view(self):
        n = self.controller.main_controller.unit_controller.view.focused_target_n
        if n is None:
            # There is no unit. Nothing to do.
            return None
        return self.controller.main_controller.unit_controller.view.targets[n]


    # EVENT HANDLERS #
    def _on_focus_in_mainwindow(self, widget, event):
        self._may_show_tmwindow = True
        if not self._should_show_tmwindow or self.isvisible:
            return
        if not self.controller.storecursor:
            return # No store loaded
        self.show()

        selected = self._get_selected_unit_view()
        self.tmwindow.update_geometry(selected)

    def _on_focus_out_mainwindow(self, widget, event):
        self._may_show_tmwindow = False
        if not self.isvisible:
            return
        self.hide()
        self._should_show_tmwindow = True

    def _on_configure_mainwindow(self, widget, event):
        if self._should_show_tmwindow:
            # For some reason tvc_tm_source needs this help to recalculate its
            # size, otherwise it goes through the roof (rhs of the screen), and
            # the size calculation of the renderer isn't even called. See bug
            # 1809.
            self.tmwindow.tvc_tm_source.queue_resize()
            self.update_geometry()

    def _on_hide_tm(self, accel_group, acceleratable, keyval, modifier):
        self.hide()

    def _on_row_activated(self, treeview, path, column):
        """Called when a TM match is selected in the TM window."""
        liststore = treeview.get_model()
        assert liststore is self.tmwindow.liststore
        itr = liststore.get_iter(path)
        match_data = liststore.get_value(itr, 0)

        self.select_match(match_data)

    def _on_select_match(self, accel_group, acceleratable, keyval, modifier):
        self.select_match_index(int(keyval - gtk.keysyms._0))

    def _on_store_closed(self, storecontroller):
        self.hide()
        self.mnu_suggestions.set_sensitive(False)

    def _on_store_loaded(self, storecontroller):
        self.mnu_suggestions.set_sensitive(True)

    def _on_store_view_scroll(self, *args):
        if self.isvisible:
            self.hide()

    def _on_toggle_show_tm(self, *args):
        if not self.active and self.isvisible:
            self.hide()
        elif self.active and not self.isvisible:
            self.controller.start_query()

########NEW FILE########
__FILENAME__ = tmwidgets
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk
import logging
import pango

from virtaal.views import markup, rendering


class TMWindow(gtk.Window):
    """Constructs the main TM window and all its children."""

    MAX_HEIGHT = 300

    # INITIALIZERS #
    def __init__(self, view):
        super(TMWindow, self).__init__(gtk.WINDOW_POPUP)
        self.view = view

        self.set_has_frame(True)

        self._build_gui()

    def _build_gui(self):
        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.scrolled_window.set_shadow_type(gtk.SHADOW_IN)

        self.treeview = self._create_treeview()

        self.scrolled_window.add(self.treeview)
        self.add(self.scrolled_window)

    def _create_treeview(self):
        self.liststore = gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING)
        treeview = gtk.TreeView(model=self.liststore)
        treeview.set_rules_hint(False)
        treeview.set_headers_visible(False)

        self.perc_renderer = gtk.CellRendererProgress()
        self.match_renderer = TMMatchRenderer(self.view)
        self.tm_source_renderer = TMSourceColRenderer(self.view)

        # l10n: match quality column label
        self.tvc_perc = gtk.TreeViewColumn(_('%'), self.perc_renderer)
        self.tvc_perc.set_cell_data_func(self.perc_renderer, self._percent_data_func)
        self.tvc_match = gtk.TreeViewColumn(_('Matches'), self.match_renderer, matchdata=0)
        self.tvc_match.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.tvc_tm_source = gtk.TreeViewColumn(_('TM Source'), self.tm_source_renderer, matchdata=0)
        self.tvc_tm_source.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)

        treeview.append_column(self.tvc_perc)
        treeview.append_column(self.tvc_match)
        treeview.append_column(self.tvc_tm_source)
        treeview.set_tooltip_column(1)

        return treeview

    # METHODS #
    def rows_height(self):
        height = 0
        itr = self.liststore.get_iter_first()
        vert_sep = self.treeview.style_get_property('vertical-separator')
        while itr and self.liststore.iter_is_valid(itr):
            path = self.liststore.get_path(itr)
            height += self.treeview.get_cell_area(path, self.tvc_match).height + vert_sep
            itr = self.liststore.iter_next(itr)
        # This seems necessary on some themes, but on others (like wimp and the
        # large inverse theme of GNOME, it causes the scrollbar to appear.
        #if height:
        #    height -= vert_sep

        return height

    def update_geometry(self, widget):
        """Move this window to right below the given widget so that C{widget}'s
            bottom left corner and this window's top left corner line up."""
        if not self.props.visible:
            return

        widget_alloc = widget.parent.get_allocation()
        gdkwin = widget.get_window(gtk.TEXT_WINDOW_WIDGET)
        if gdkwin is None:
            return
        vscrollbar = self.scrolled_window.get_vscrollbar()
        scrollbar_width = vscrollbar.props.visible and vscrollbar.get_allocation().width + 1 or 0

        x, y = gdkwin.get_origin()

        if widget.get_direction() == gtk.TEXT_DIR_LTR:
            x -= self.tvc_perc.get_width()
        else:
            x -= self.tvc_tm_source.get_width() + scrollbar_width
        y += widget_alloc.height + 2

        tm_source_width = self.tvc_tm_source.get_width()
        if tm_source_width > 100:
            # Sometimes this column is still way too wide after a reconfigure.
            # See bug 1809 for more detail.
            tm_source_width = self.tvc_perc.get_width()
        width = widget_alloc.width + self.tvc_perc.get_width() + tm_source_width + scrollbar_width
        height = min(self.rows_height(), self.MAX_HEIGHT) + 4
        # TODO: Replace the hard-coded value above with a query to the theme. It represents the width of the shadow of self.scrolled_window

        #logging.debug('TMWindow.update_geometry(%dx%d +%d+%d)' % (width, height, x, y))
        self.resize(width, height)
        self.scrolled_window.set_size_request(width, height)
        self.window.move_resize(0,0, width,height)
        self.window.get_toplevel().move_resize(x,y, width,height)


    # EVENT HANLDERS #
    def _percent_data_func(self, column, cell_renderer, tree_model, iter):
        match_data = tree_model.get_value(iter, 0)
        if match_data.get('quality', None) is not None:
            quality = int(match_data['quality'])
            cell_renderer.set_property('value', quality)
            #l10n: This message allows you to customize the appearance of the match percentage. Most languages can probably leave it unchanged.
            cell_renderer.set_property('text', _("%(match_quality)s%%") % \
                    {"match_quality": quality})
            return
        elif gtk.gtk_version < (2,16,0):
            # Rendering bug with some older versions of GTK if a progress is at
            # 0%. GNOME bug 567253.
            cell_renderer.set_property('value', 3)
        else:
            cell_renderer.set_property('value', 0)
        #l10n: This indicates a suggestion from machine translation. It is displayed instead of the match percentage.
        cell_renderer.set_property('text', _(u"?"))


class TMSourceColRenderer(gtk.GenericCellRenderer):
    """
    Renders the TM source for the row.
    """

    __gtype_name__ = "TMSourceColRenderer"
    __gproperties__ = {
        "matchdata": (
            gobject.TYPE_PYOBJECT,
            "The match data.",
            "The match data that this renderer is currently handling",
            gobject.PARAM_READWRITE
        ),
    }

    YPAD = 2

    # INITIALIZERS #
    def __init__(self, view):
        gtk.GenericCellRenderer.__init__(self)

        self.view = view
        self.matchdata = None


    # INTERFACE METHODS #
    def on_get_size(self, widget, cell_area):
        if 'tmsource' not in self.matchdata:
            return 0, 0, 0, 0

        label = gtk.Label()
        label.set_markup(u'<small>%s</small>' % self.matchdata['tmsource'])
        label.get_pango_context().set_base_gravity(pango.GRAVITY_AUTO)
        label.set_angle(270)
        size = label.size_request()
        return 0, 0, size[0], size[1] + self.YPAD*2

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def on_render(self, window, widget, _background_area, cell_area, _expose_area, _flags):
        if 'tmsource' not in self.matchdata:
            return
        x_offset = 0
        y_offset = 0

        x = cell_area.x + x_offset
        y = cell_area.y + y_offset + self.YPAD

        label = gtk.Label()
        label.set_markup(u'<small>%s</small>' % self.matchdata['tmsource'])
        label.get_pango_context().set_base_dir(pango.DIRECTION_TTB_LTR)
        if widget.get_direction() == gtk.TEXT_DIR_RTL:
            label.set_angle(90)
        else:
            label.set_angle(270)
        label.set_alignment(0.5, 0.5)
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, False,
                cell_area, widget, '', x, y, label.get_layout())


class TMMatchRenderer(gtk.GenericCellRenderer):
    """
    Renders translation memory matches.

    This class was adapted from C{virtaal.views.widgets.storecellrenderer.StoreCellRenderer}.
    """

    __gtype_name__ = 'TMMatchRenderer'
    __gproperties__ = {
        "matchdata": (
            gobject.TYPE_PYOBJECT,
            "The match data.",
            "The match data that this renderer is currently handling",
            gobject.PARAM_READWRITE
        ),
    }

    BOX_MARGIN = 3
    """The number of pixels between where the source box is drawn and where the
        text layout begins."""
    LINE_SEPARATION = 10
    """The number of pixels between source and target in a single row."""
    ROW_PADDING = 6
    """The number of pixels between rows."""

    # INITIALIZERS #
    def __init__(self, view):
        gtk.GenericCellRenderer.__init__(self)

        self.view = view
        self.layout = None
        self.matchdata = None


    # INTERFACE METHODS #
    def on_get_size(self, widget, cell_area):
        width = self.view.get_target_width() - self.BOX_MARGIN
        height = self._compute_cell_height(widget, width)
        height = min(height, 600)
        #print 'do_get_size() (w, h):', width, height

        x_offset = 0
        y_offset = self.ROW_PADDING / 2
        return x_offset, y_offset, width, height

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def on_render(self, window, widget, _background_area, cell_area, _expose_area, _flags):
        x_offset = 0
        y_offset = self.BOX_MARGIN
        width = cell_area.width
        height = self._compute_cell_height(widget, width)

        x = cell_area.x + x_offset
        if not self.source_layout:
            # We do less for MT results
            target_y = cell_area.y
            widget.get_style().paint_layout(window, gtk.STATE_NORMAL, False,
                    cell_area, widget, '', x, target_y, self.target_layout)
            return

        source_height = self.source_layout.get_pixel_size()[1]
        source_y = cell_area.y + y_offset
        target_y = cell_area.y + y_offset + source_height + self.LINE_SEPARATION

        source_dx = target_dx = self.BOX_MARGIN

        widget.get_style().paint_box(window, gtk.STATE_NORMAL, gtk.SHADOW_ETCHED_IN,
                cell_area, widget, '', x, source_y-self.BOX_MARGIN, width-self.BOX_MARGIN, source_height+(self.LINE_SEPARATION/2))
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, False,
                cell_area, widget, '', x + source_dx, source_y, self.source_layout)
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, False,
                cell_area, widget, '', x + target_dx, target_y, self.target_layout)

    # METHODS #
    def _compute_cell_height(self, widget, width):
        srclang = self.view.controller.main_controller.lang_controller.source_lang.code
        tgtlang = self.view.controller.main_controller.lang_controller.target_lang.code

        self.target_layout = self._get_pango_layout(
            widget, self.matchdata['target'], width - (2*self.BOX_MARGIN),
            rendering.get_target_font_description()
        )
        self.target_layout.get_context().set_language(rendering.get_language(tgtlang))

        if self.matchdata.get('quality', 0) == 0 and \
                self.matchdata['source'] == self.matchdata['query_str']:
            # We do less for MT results
            self.source_layout = None
            height = self.target_layout.get_pixel_size()[1]
            return height + self.ROW_PADDING

        else:
            self.source_layout = self._get_pango_layout(
                widget, self.matchdata['source'], width - (2*self.BOX_MARGIN),
                rendering.get_source_font_description(),
                self.matchdata['query_str']
            )
            self.source_layout.get_context().set_language(rendering.get_language(srclang))

            height = self.source_layout.get_pixel_size()[1] + self.target_layout.get_pixel_size()[1]
            return height + self.LINE_SEPARATION + self.ROW_PADDING

    def _get_pango_layout(self, widget, text, width, font_description, diff_text=u""):
        '''Gets the Pango layout used in the cell in a TreeView widget.'''
        # We can't use widget.get_pango_context() because we'll end up
        # overwriting the language and font settings if we don't have a
        # new one
        layout = pango.Layout(widget.create_pango_context())
        layout.set_font_description(font_description)
        layout.set_wrap(pango.WRAP_WORD_CHAR)
        layout.set_width(width * pango.SCALE)
        #XXX - plurals?
        layout.set_markup(markup.markuptext(text, diff_text=diff_text))
        # This makes no sense, but has the desired effect to align things correctly for
        # both LTR and RTL languages:
        if widget.get_direction() == gtk.TEXT_DIR_RTL:
            layout.set_alignment(pango.ALIGN_RIGHT)
        return layout

########NEW FILE########
__FILENAME__ = _helloworld
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""example plugin."""

import logging

from virtaal.controllers.baseplugin import BasePlugin


class Plugin(BasePlugin):
    description = _('Simple plug-in that serves as an example to developers.')
    display_name = _('Hello World')
    version = '0.1'
    default_config = {
        "name": "Hello World",
        "question": "Stop annoying you?",
        "info": "Store loaded!"
    }

    # INITIALIZERS #
    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name
        self.main_controller = main_controller

        self.load_config()
        self._init_plugin()
        logging.debug('HelloWorld loaded')

        self.annoy = True

    def _init_plugin(self):
        self._store_loaded_id = self.main_controller.store_controller.connect('store-loaded', self.on_store_loaded)

        if self.main_controller.store_controller.get_store():
            self.on_store_loaded(self.main_controller.store_controller)


    # METHODS #
    def destroy(self):
        self.main_controller.store_controller.disconnect(self._store_loaded_id)
        if getattr(self, '_cursor_changed_id', None):
            self.main_controller.store_controller.cursor.disconnect(self._cursor_changed_id)
        self.save_config()


    # EVENT HANDLERS #
    def on_store_loaded(self, storecontroller):
        self.main_controller.show_info(self.config["name"], self.config["info"])
        self._cursor_changed_id = storecontroller.cursor.connect('cursor-changed', self.on_cursor_change)

    def on_cursor_change(self, cursor):
        if self.annoy:
            self.annoy = not self.main_controller.show_prompt(self.config["name"], self.config["question"])

########NEW FILE########
__FILENAME__ = ipython_view
#!/usr/bin/python
'''
Provides IPython console widget.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
'''

import gtk, gobject
import re
import sys
import os
import pango
from StringIO import StringIO

import IPython

class IterableIPShell:
  '''
  Create an IPython instance. Does not start a blocking event loop,
  instead allow single iterations. This allows embedding in GTK+ 
  without blockage.

  @ivar IP: IPython instance.
  @type IP: IPython.iplib.InteractiveShell
  @ivar iter_more: Indicates if the line executed was a complete command,
  or we should wait for more.
  @type iter_more: integer
  @ivar history_level: The place in history where we currently are 
  when pressing up/down.
  @type history_level: integer
  @ivar complete_sep: Seperation delimeters for completion function.
  @type complete_sep: _sre.SRE_Pattern
  '''
  def __init__(self,argv=[],user_ns=None,user_global_ns=None, 
               cin=None, cout=None,cerr=None, input_func=None):
    '''
    
    
    @param argv: Command line options for IPython
    @type argv: list
    @param user_ns: User namespace.
    @type user_ns: dictionary
    @param user_global_ns: User global namespace.
    @type user_global_ns: dictionary.
    @param cin: Console standard input.
    @type cin: IO stream
    @param cout: Console standard output.
    @type cout: IO stream 
    @param cerr: Console standard error.
    @type cerr: IO stream
    @param input_func: Replacement for builtin raw_input()
    @type input_func: function
    '''
    if input_func:
      IPython.iplib.raw_input_original = input_func
    if cin:
      IPython.Shell.Term.cin = cin
    if cout:
      IPython.Shell.Term.cout = cout
    if cerr:
      IPython.Shell.Term.cerr = cerr

    # This is to get rid of the blockage that accurs during 
    # IPython.Shell.InteractiveShell.user_setup()
    IPython.iplib.raw_input = lambda x: None

    self.term = IPython.genutils.IOTerm(cin=cin, cout=cout, cerr=cerr)
    os.environ['TERM'] = 'dumb'
    excepthook = sys.excepthook 
    self.IP = IPython.Shell.make_IPython(
      argv,user_ns=user_ns,
      user_global_ns=user_global_ns,
      embedded=True,
      shell_class=IPython.Shell.InteractiveShell)
    self.IP.system = lambda cmd: self.shell(self.IP.var_expand(cmd),
                                            header='IPython system call: ',
                                            verbose=self.IP.rc.system_verbose)
    sys.excepthook = excepthook
    self.iter_more = 0
    self.history_level = 0
    self.complete_sep =  re.compile('[\s\{\}\[\]\(\)]')

  def execute(self):
    '''
    Executes the current line provided by the shell object.
    '''
    self.history_level = 0
    orig_stdout = sys.stdout
    sys.stdout = IPython.Shell.Term.cout
    try:
      line = self.IP.raw_input(None, self.iter_more)
      if self.IP.autoindent:
        self.IP.readline_startup_hook(None)
    except KeyboardInterrupt:
      self.IP.write('\nKeyboardInterrupt\n')
      self.IP.resetbuffer()
      # keep cache in sync with the prompt counter:
      self.IP.outputcache.prompt_count -= 1
        
      if self.IP.autoindent:
        self.IP.indent_current_nsp = 0
      self.iter_more = 0
    except:
      self.IP.showtraceback()
    else:
      self.iter_more = self.IP.push(line)
      if (self.IP.SyntaxTB.last_syntax_error and
          self.IP.rc.autoedit_syntax):
        self.IP.edit_syntax_error()
    if self.iter_more:
      self.prompt = str(self.IP.outputcache.prompt2).strip()
      if self.IP.autoindent:
        self.IP.readline_startup_hook(self.IP.pre_readline)
    else:
      self.prompt = str(self.IP.outputcache.prompt1).strip()
    sys.stdout = orig_stdout

  def historyBack(self):
    '''
    Provides one history command back.
    
    @return: The command string.
    @rtype: string
    '''
    self.history_level -= 1
    return self._getHistory()
  
  def historyForward(self):
    '''
    Provides one history command forward.
    
    @return: The command string.
    @rtype: string
    '''
    self.history_level += 1
    return self._getHistory()
  
  def _getHistory(self):
    '''
    Get's the command string of the current history level.
    
    @return: Historic command string.
    @rtype: string
    '''
    try:
      rv = self.IP.user_ns['In'][self.history_level].strip('\n')
    except IndexError:
      self.history_level = 0
      rv = ''
    return rv

  def updateNamespace(self, ns_dict):
    '''
    Add the current dictionary to the shell namespace.
    
    @param ns_dict: A dictionary of symbol-values.
    @type ns_dict: dictionary
    '''
    self.IP.user_ns.update(ns_dict)

  def complete(self, line):
    '''
    Returns an auto completed line and/or posibilities for completion.
    
    @param line: Given line so far.
    @type line: string
    
    @return: Line completed as for as possible, 
    and possible further completions.
    @rtype: tuple
    '''
    split_line = self.complete_sep.split(line)
    possibilities = self.IP.complete(split_line[-1])
    if possibilities:
      def _commonPrefix(str1, str2):
        '''
        Reduction function. returns common prefix of two given strings.
        
        @param str1: First string.
        @type str1: string
        @param str2: Second string
        @type str2: string
        
        @return: Common prefix to both strings.
        @rtype: string
        '''
        for i in range(len(str1)):
          if not str2.startswith(str1[:i+1]):
            return str1[:i]
        return str1
      common_prefix = reduce(_commonPrefix, possibilities)
      completed = line[:-len(split_line[-1])]+common_prefix
    else:
      completed = line
    return completed, possibilities
  

  def shell(self, cmd,verbose=0,debug=0,header=''):
    '''
    Replacement method to allow shell commands without them blocking.
    
    @param cmd: Shell command to execute.
    @type cmd: string
    @param verbose: Verbosity
    @type verbose: integer
    @param debug: Debug level
    @type debug: integer
    @param header: Header to be printed before output
    @type header: string
    '''
    stat = 0
    if verbose or debug: print header+cmd
    # flush stdout so we don't mangle python's buffering
    if not debug:
      input, output = os.popen4(cmd)
      print output.read()
      output.close()
      input.close()

class ConsoleView(gtk.TextView):
  '''
  Specialized text view for console-like workflow.

  @cvar ANSI_COLORS: Mapping of terminal colors to X11 names.
  @type ANSI_COLORS: dictionary

  @ivar text_buffer: Widget's text buffer.
  @type text_buffer: gtk.TextBuffer
  @ivar color_pat: Regex of terminal color pattern
  @type color_pat: _sre.SRE_Pattern
  @ivar mark: Scroll mark for automatic scrolling on input.
  @type mark: gtk.TextMark
  @ivar line_start: Start of command line mark.
  @type line_start: gtk.TextMark
  '''
  ANSI_COLORS =  {'0;30': 'Black',     '0;31': 'Red',
                  '0;32': 'Green',     '0;33': 'Brown',
                  '0;34': 'Blue',      '0;35': 'Purple',
                  '0;36': 'Cyan',      '0;37': 'LightGray',
                  '1;30': 'DarkGray',  '1;31': 'DarkRed',
                  '1;32': 'SeaGreen',  '1;33': 'Yellow',
                  '1;34': 'LightBlue', '1;35': 'MediumPurple',
                  '1;36': 'LightCyan', '1;37': 'White'}

  def __init__(self):
    '''
    Initialize console view.
    '''
    gtk.TextView.__init__(self)
    self.modify_font(pango.FontDescription('Mono'))
    self.set_cursor_visible(True)
    self.text_buffer = self.get_buffer()
    self.mark = self.text_buffer.create_mark('scroll_mark', 
                                             self.text_buffer.get_end_iter(),
                                             False)
    for code in self.ANSI_COLORS:
      self.text_buffer.create_tag(code, 
                                  foreground=self.ANSI_COLORS[code], 
                                  weight=700)
    self.text_buffer.create_tag('0')
    self.text_buffer.create_tag('notouch', editable=False)
    self.color_pat = re.compile('\x01?\x1b\[(.*?)m\x02?')
    self.line_start = \
        self.text_buffer.create_mark('line_start', 
                                     self.text_buffer.get_end_iter(), True)
    self.connect('key-press-event', self.onKeyPress)
    
  def write(self, text, editable=False):
    gobject.idle_add(self._write, text, editable)

  def _write(self, text, editable=False):
    '''
    Write given text to buffer.
    
    @param text: Text to append.
    @type text: string
    @param editable: If true, added text is editable.
    @type editable: boolean
    '''
    segments = self.color_pat.split(text)
    segment = segments.pop(0)
    start_mark = self.text_buffer.create_mark(None, 
                                              self.text_buffer.get_end_iter(), 
                                              True)
    self.text_buffer.insert(self.text_buffer.get_end_iter(), segment)

    if segments:
      ansi_tags = self.color_pat.findall(text)
      for tag in ansi_tags:
        i = segments.index(tag)
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(),
                                             segments[i+1], tag)
        segments.pop(i)
    if not editable:
      self.text_buffer.apply_tag_by_name('notouch',
                                         self.text_buffer.get_iter_at_mark(start_mark),
                                         self.text_buffer.get_end_iter())
    self.text_buffer.delete_mark(start_mark)
    self.scroll_mark_onscreen(self.mark)


  def showPrompt(self, prompt):
    gobject.idle_add(self._showPrompt, prompt)

  def _showPrompt(self, prompt):
    '''
    Prints prompt at start of line.
    
    @param prompt: Prompt to print.
    @type prompt: string
    '''
    self._write(prompt)
    self.text_buffer.move_mark(self.line_start,
                               self.text_buffer.get_end_iter())

  def changeLine(self, text):
    gobject.idle_add(self._changeLine, text)

  def _changeLine(self, text):
    '''
    Replace currently entered command line with given text.
    
    @param text: Text to use as replacement.
    @type text: string
    '''
    iter = self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.delete(self.text_buffer.get_iter_at_mark(self.line_start), iter)
    self._write(text, True)

  def getCurrentLine(self):
    '''
    Get text in current command line.
    
    @return: Text of current command line.
    @rtype: string
    '''
    rv = self.text_buffer.get_slice(
      self.text_buffer.get_iter_at_mark(self.line_start),
      self.text_buffer.get_end_iter(), False)
    return rv

  def showReturned(self, text):
    gobject.idle_add(self._showReturned, text)

  def _showReturned(self, text):
    '''
    Show returned text from last command and print new prompt.
    
    @param text: Text to show.
    @type text: string
    '''
    iter = self.text_buffer.get_iter_at_mark(self.line_start)
    iter.forward_to_line_end()
    self.text_buffer.apply_tag_by_name(
      'notouch', 
      self.text_buffer.get_iter_at_mark(self.line_start),
      iter)
    self._write('\n'+text)
    if text:
      self._write('\n')
    self._showPrompt(self.prompt)
    self.text_buffer.move_mark(self.line_start,self.text_buffer.get_end_iter())
    self.text_buffer.place_cursor(self.text_buffer.get_end_iter())

  def onKeyPress(self, widget, event):
    '''
    Key press callback used for correcting behavior for console-like 
    interfaces. For example 'home' should go to prompt, not to begining of
    line.
    
    @param widget: Widget that key press accored in.
    @type widget: gtk.Widget
    @param event: Event object
    @type event: gtk.gdk.Event
    
    @return: Return True if event should not trickle.
    @rtype: boolean
    '''
    insert_mark = self.text_buffer.get_insert()
    insert_iter = self.text_buffer.get_iter_at_mark(insert_mark)
    selection_mark = self.text_buffer.get_selection_bound()
    selection_iter = self.text_buffer.get_iter_at_mark(selection_mark)
    start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
    if event.keyval == gtk.keysyms.Home:
      if event.state & gtk.gdk.CONTROL_MASK or event.state & gtk.gdk.MOD1_MASK:
        pass
      elif event.state & gtk.gdk.SHIFT_MASK:
        self.text_buffer.move_mark(insert_mark, start_iter)
        return True
      else:
        self.text_buffer.place_cursor(start_iter)
        return True
    elif event.keyval == gtk.keysyms.Left:
      insert_iter.backward_cursor_position()
      if not insert_iter.editable(True):
        return True
    elif not event.string:
      pass
    elif start_iter.compare(insert_iter) <= 0 and \
          start_iter.compare(selection_iter) <= 0:
      pass
    elif start_iter.compare(insert_iter) > 0 and \
          start_iter.compare(selection_iter) > 0:
      self.text_buffer.place_cursor(start_iter)
    elif insert_iter.compare(selection_iter) < 0:
      self.text_buffer.move_mark(insert_mark, start_iter)
    elif insert_iter.compare(selection_iter) > 0:
      self.text_buffer.move_mark(selection_mark, start_iter)             

    return self.onKeyPressExtend(event)

  def onKeyPressExtend(self, event):
    '''
    For some reason we can't extend onKeyPress directly (bug #500900).
    '''
    pass

class IPythonView(ConsoleView, IterableIPShell):
  '''
  Sub-class of both modified IPython shell and L{ConsoleView} this makes
  a GTK+ IPython console.
  '''
  def __init__(self):
    '''
    Initialize. Redirect I/O to console.
    '''
    ConsoleView.__init__(self)
    self.cout = StringIO()
    IterableIPShell.__init__(self, cout=self.cout,cerr=self.cout, 
                             input_func=self.raw_input)
#    self.connect('key_press_event', self.keyPress)
    self.execute()
    self.cout.truncate(0)
    self.showPrompt(self.prompt)
    self.interrupt = False

  def raw_input(self, prompt=''):
    '''
    Custom raw_input() replacement. Get's current line from console buffer.
    
    @param prompt: Prompt to print. Here for compatability as replacement.
    @type prompt: string
    
    @return: The current command line text.
    @rtype: string
    '''
    if self.interrupt:
      self.interrupt = False
      raise KeyboardInterrupt
    return self.getCurrentLine()

  def onKeyPressExtend(self, event):
    '''
    Key press callback with plenty of shell goodness, like history, 
    autocompletions, etc.
    
    @param widget: Widget that key press occured in.
    @type widget: gtk.Widget
    @param event: Event object.
    @type event: gtk.gdk.Event
    
    @return: True if event should not trickle.
    @rtype: boolean
    '''
    if event.state & gtk.gdk.CONTROL_MASK and event.keyval == 99:
      self.interrupt = True
      self._processLine()
      return True
    elif event.keyval == gtk.keysyms.Return:
      self._processLine()
      return True
    elif event.keyval == gtk.keysyms.Up:
      self.changeLine(self.historyBack())
      return True
    elif event.keyval == gtk.keysyms.Down:
      self.changeLine(self.historyForward())
      return True
    elif event.keyval == gtk.keysyms.Tab:
      if not self.getCurrentLine().strip():
        return False
      completed, possibilities = self.complete(self.getCurrentLine())
      if len(possibilities) > 1:
        slice = self.getCurrentLine()
        self.write('\n')
        for symbol in possibilities:
          self.write(symbol+'\n')
        self.showPrompt(self.prompt)
      self.changeLine(completed or slice)
      return True

  def _processLine(self):
    '''
    Process current command line.
    '''
    self.history_pos = 0
    self.execute()
    rv = self.cout.getvalue()
    if rv: rv = rv.strip('\n')
    self.showReturned(rv)
    self.cout.truncate(0)

########NEW FILE########
__FILENAME__ = _python_console
#!/usr/bin/env python

import gobject
import gtk
import pango
import re
import sys
import traceback
from gtk import gdk

from virtaal.controllers.baseplugin import BasePlugin


class PythonConsole(gtk.ScrolledWindow):
    def __init__(self, namespace = {}, destroy_cb = None):
        gtk.ScrolledWindow.__init__(self)

        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC);
        self.set_shadow_type(gtk.SHADOW_IN)
        self.view = gtk.TextView()
        self.view.modify_font(pango.FontDescription('Monospace'))
        self.view.set_editable(True)
        self.view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.add(self.view)
        self.view.show()

        buffer = self.view.get_buffer()
        self.normal = buffer.create_tag("normal")
        self.error  = buffer.create_tag("error")
        self.error.set_property("foreground", "red")
        self.command = buffer.create_tag("command")
        self.command.set_property("foreground", "blue")

        self.__spaces_pattern = re.compile(r'^\s+')
        self.namespace = namespace

        self.destroy_cb = destroy_cb

        self.block_command = False

        # Init first line
        buffer.create_mark("input-line", buffer.get_end_iter(), True)
        buffer.insert(buffer.get_end_iter(), ">>> ")
        buffer.create_mark("input", buffer.get_end_iter(), True)

        # Init history
        self.history = ['']
        self.history_pos = 0
        self.current_command = ''
        self.namespace['__history__'] = self.history

        # Set up hooks for standard output.
        self.stdout = gtkoutfile(self, sys.stdout.fileno(), self.normal)
        self.stderr = gtkoutfile(self, sys.stderr.fileno(), self.error)

        # Signals
        self.view.connect("key-press-event", self.__key_press_event_cb)
        buffer.connect("mark-set", self.__mark_set_cb)


    def __key_press_event_cb(self, view, event):
        if event.keyval == gtk.keysyms.d and \
           event.state == gtk.gdk.CONTROL_MASK:
            self.destroy()

        elif event.keyval == gtk.keysyms.Return and \
             event.state == gtk.gdk.CONTROL_MASK:
            # Get the command
            buffer = view.get_buffer()
            inp_mark = buffer.get_mark("input")
            inp = buffer.get_iter_at_mark(inp_mark)
            cur = buffer.get_end_iter()
            line = buffer.get_text(inp, cur)
            self.current_command = self.current_command + line + "\n"
            self.history_add(line)

            # Prepare the new line
            cur = buffer.get_end_iter()
            buffer.insert(cur, "\n... ")
            cur = buffer.get_end_iter()
            buffer.move_mark(inp_mark, cur)

            # Keep indentation of precendent line
            spaces = re.match(self.__spaces_pattern, line)
            if spaces is not None:
                buffer.insert(cur, line[spaces.start() : spaces.end()])
                cur = buffer.get_end_iter()

            buffer.place_cursor(cur)
            gobject.idle_add(self.scroll_to_end)
            return True

        elif event.keyval == gtk.keysyms.Return:
            # Get the marks
            buffer = view.get_buffer()
            lin_mark = buffer.get_mark("input-line")
            inp_mark = buffer.get_mark("input")

            # Get the command line
            inp = buffer.get_iter_at_mark(inp_mark)
            cur = buffer.get_end_iter()
            line = buffer.get_text(inp, cur)
            self.current_command = self.current_command + line + "\n"
            self.history_add(line)

            # Make the line blue
            lin = buffer.get_iter_at_mark(lin_mark)
            buffer.apply_tag(self.command, lin, cur)
            buffer.insert(cur, "\n")

            cur_strip = self.current_command.rstrip()

            if cur_strip.endswith(":") \
            or (self.current_command[-2:] != "\n\n" and self.block_command):
                # Unfinished block command
                self.block_command = True
                com_mark = "... "
            elif cur_strip.endswith("\\"):
                com_mark = "... "
            else:
                # Eval the command
                self.__run(self.current_command)
                self.current_command = ''
                self.block_command = False
                com_mark = ">>> "

            # Prepare the new line
            cur = buffer.get_end_iter()
            buffer.move_mark(lin_mark, cur)
            buffer.insert(cur, com_mark)
            cur = buffer.get_end_iter()
            buffer.move_mark(inp_mark, cur)
            buffer.place_cursor(cur)
            gobject.idle_add(self.scroll_to_end)
            return True

        elif event.keyval == gtk.keysyms.KP_Down or \
             event.keyval == gtk.keysyms.Down:
            # Next entry from history
            view.emit_stop_by_name("key_press_event")
            self.history_down()
            gobject.idle_add(self.scroll_to_end)
            return True

        elif event.keyval == gtk.keysyms.KP_Up or \
             event.keyval == gtk.keysyms.Up:
            # Previous entry from history
            view.emit_stop_by_name("key_press_event")
            self.history_up()
            gobject.idle_add(self.scroll_to_end)
            return True

        elif event.keyval == gtk.keysyms.KP_Left or \
             event.keyval == gtk.keysyms.Left or \
             event.keyval == gtk.keysyms.BackSpace:
            buffer = view.get_buffer()
            inp = buffer.get_iter_at_mark(buffer.get_mark("input"))
            cur = buffer.get_iter_at_mark(buffer.get_insert())
            return inp.compare(cur) == 0

        elif event.keyval == gtk.keysyms.Home:
            # Go to the begin of the command instead of the begin of
            # the line
            buffer = view.get_buffer()
            inp = buffer.get_iter_at_mark(buffer.get_mark("input"))
            if event.state == gtk.gdk.SHIFT_MASK:
                buffer.move_mark_by_name("insert", inp)
            else:
                buffer.place_cursor(inp)
            return True

    def __mark_set_cb(self, buffer, iter, name):
        input = buffer.get_iter_at_mark(buffer.get_mark("input"))
        pos   = buffer.get_iter_at_mark(buffer.get_insert())
        self.view.set_editable(pos.compare(input) != -1)

    def get_command_line(self):
        buffer = self.view.get_buffer()
        inp = buffer.get_iter_at_mark(buffer.get_mark("input"))
        cur = buffer.get_end_iter()
        return buffer.get_text(inp, cur)

    def set_command_line(self, command):
        buffer = self.view.get_buffer()
        mark = buffer.get_mark("input")
        inp = buffer.get_iter_at_mark(mark)
        cur = buffer.get_end_iter()
        buffer.delete(inp, cur)
        buffer.insert(inp, command)
        buffer.select_range(buffer.get_iter_at_mark(mark),
                            buffer.get_end_iter())
        self.view.grab_focus()

    def history_add(self, line):
        if line.strip() != '':
            self.history_pos = len(self.history)
            self.history[self.history_pos - 1] = line
            self.history.append('')

    def history_up(self):
        if self.history_pos > 0:
            self.history[self.history_pos] = self.get_command_line()
            self.history_pos = self.history_pos - 1
            self.set_command_line(self.history[self.history_pos])

    def history_down(self):
        if self.history_pos < len(self.history) - 1:
            self.history[self.history_pos] = self.get_command_line()
            self.history_pos = self.history_pos + 1
            self.set_command_line(self.history[self.history_pos])

    def scroll_to_end(self):
        iter = self.view.get_buffer().get_end_iter()
        self.view.scroll_to_iter(iter, 0.0)
        return False

    def write(self, text, tag = None):
        buffer = self.view.get_buffer()
        if tag is None:
            buffer.insert(buffer.get_end_iter(), text)
        else:
            buffer.insert_with_tags(buffer.get_end_iter(), text, tag)
        gobject.idle_add(self.scroll_to_end)

    def eval(self, command, display_command = False):
        buffer = self.view.get_buffer()
        lin = buffer.get_mark("input-line")
        buffer.delete(buffer.get_iter_at_mark(lin),
                      buffer.get_end_iter())

        if isinstance(command, list) or isinstance(command, tuple):
            for c in command:
                if display_command:
                    self.write(">>> " + c + "\n", self.command)
                self.__run(c)
        else:
            if display_command:
                self.write(">>> " + c + "\n", self.command)
            self.__run(command)

        cur = buffer.get_end_iter()
        buffer.move_mark_by_name("input-line", cur)
        buffer.insert(cur, ">>> ")
        cur = buffer.get_end_iter()
        buffer.move_mark_by_name("input", cur)
        self.view.scroll_to_iter(buffer.get_end_iter(), 0.0)

    def __run(self, command):
        sys.stdout, self.stdout = self.stdout, sys.stdout
        sys.stderr, self.stderr = self.stderr, sys.stderr

        try:
            try:
                r = eval(command, self.namespace, self.namespace)
                if r is not None:
                    print `r`
            except SyntaxError:
                exec command in self.namespace
        except:
            if hasattr(sys, 'last_type') and sys.last_type == SystemExit:
                self.destroy()
            else:
                traceback.print_exc()

        sys.stdout, self.stdout = self.stdout, sys.stdout
        sys.stderr, self.stderr = self.stderr, sys.stderr

    def destroy(self):
        if self.destroy_cb is not None:
            self.destroy_cb()


class gtkoutfile:
    """A fake output file object.  It sends output to a TK test widget,
    and if asked for a file number, returns one set on instance creation"""
    def __init__(self, console, fn, tag):
        self.fn = fn
        self.console = console
        self.tag = tag
    def close(self):         pass
    def flush(self):         pass
    def fileno(self):        return self.fn
    def isatty(self):        return 0
    def read(self, a):       return ''
    def readline(self):      return ''
    def readlines(self):     return []
    def write(self, s):      self.console.write(s, self.tag)
    def writelines(self, l): self.console.write(l, self.tag)
    def seek(self, a):       raise IOError, (29, 'Illegal seek')
    def tell(self):          raise IOError, (29, 'Illegal seek')
    truncate = tell


class Plugin(BasePlugin):
    description = _("Run-time access to Virtaal's internals (for developers).")
    display_name = _('Python Console')
    version = 0.1

    # INITIALIZERS #
    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name
        self.main_controller = main_controller

        self._init_plugin()

    def _init_plugin(self):
        self.window = None

        self._setup_key_bindings()
        self._setup_menu_item()

    def _setup_key_bindings(self):
        """Setup Gtk+ key bindings (accelerators)."""

        gtk.accel_map_add_entry("<Virtaal>/View/Python Console", gtk.keysyms.y, gdk.CONTROL_MASK)

        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<Virtaal>/View/Python Console", self._on_menuitem_activated)

        self.main_controller.view.add_accel_group(self.accel_group)

    def _setup_menu_item(self):
        self.menu = self.main_controller.view.gui.get_object('menu_view')
        self.menuitem = gtk.MenuItem(label=_('P_ython Console'))
        self.menuitem.show()
        self.menu.append(self.menuitem)

        gtk.accel_map_add_entry("<Virtaal>/View/Python Console", gtk.keysyms.F9, 0)
        accel_group = self.menu.get_accel_group()
        if accel_group is None:
            accel_group = self.accel_group
            self.menu.set_accel_group(self.accel_group)
        self.menuitem.set_accel_path("<Virtaal>/View/Python Console")
        self.menu.set_accel_group(accel_group)

        self.menuitem.connect('activate', self._on_menuitem_activated)


    # METHODS #
    def show_console(self, *args):
        if not self.window:
            ns = {
                '__builtins__' : __builtins__,
                'mc': self.main_controller,
                'sc': self.main_controller.store_controller,
                'uc': self.main_controller.unit_controller,
                'mv': self.main_controller.view,
                'sv': self.main_controller.store_controller.view,
                'uv': self.main_controller.unit_controller.view,
            }
            console = PythonConsole(namespace = ns, destroy_cb = self._on_console_destroyed)
            console.set_size_request(600, 400)

            self.window = gtk.Window()
            self.window.set_title('Virtaal Python Console')
            self.window.set_transient_for(self.main_controller.view.main_window)
            self.window.add(console)
            self.window.connect('destroy', self._on_console_destroyed)
        self.window.show_all()
        self.window.grab_focus()


    # EVENT HANDLERS #
    def _on_console_destroyed(self, *args):
        self.window = None

    def _on_menuitem_activated(self, *args):
        self.show_console()

########NEW FILE########
__FILENAME__ = depcheck
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

__all__ = ['check_dependencies', 'extra_tests', 'import_checks']


# Modules to try and import:
import_checks = ['translate', 'gtk', 'lxml.etree', 'json', 'pycurl', 'sqlite3', 'wsgiref']


#########################
# Specific Module Tests #
#########################
MIN_GTK_VERSION = (2, 18, 0)
def test_gtk_version():
    try:
        import gtk
        return gtk.ver >= MIN_GTK_VERSION
        # GtkBuilder was in GTK+ earlier already, but at least this bug is
        # quite nasty:
        # https://bugzilla.gnome.org/show_bug.cgi?id=582025
        # That seems to be fixed in time for 2.18 which was released in
        # September 2009
    except Exception:
        pass
    return False

def test_sqlite3_version():
    try:
        #TODO: work out if we need certain versions
        try:
            from sqlite3 import dbapi2
        except ImportError:
            from pysqlite2 import dbapi2
        return True
    except Exception:
        pass
    return False

def test_json():
    # We can work with simplejson or json (available since Python 2.6)
    try:
        try:
            import simplejson as json
        except ImportError:
            import json
        return True
    except Exception:
        pass
    return False

MIN_TRANSLATE_VERSION = (1, 9, 0)
def test_translate_toolkit_version():
    try:
        from translate.__version__ import ver
        return ver >= MIN_TRANSLATE_VERSION
    except Exception:
        pass
    return False


extra_tests = {
    'gtk': test_gtk_version,
    'sqlite3': test_sqlite3_version,
    'translate': test_translate_toolkit_version,
    'json': test_json,
}


#############################
# General Testing Functions #
#############################
def test_import(modname):
    try:
        __import__(modname, {}, {}, [])
    except ImportError:
        return False
    return True

def check_dependencies(module_names=import_checks):
    """Returns a list of modules that could not be imported."""
    names = []
    for name in module_names:
        if name in extra_tests:
            if not extra_tests[name]():
                names.append(name)
        elif not test_import(name):
            names.append(name)
    return names



########
# MAIN #
########
if __name__ == '__main__':
    failed = check_dependencies()
    if not failed:
        print 'All dependencies met.'
    else:
        print 'Dependencies not met: %s' % (', '.join(failed))

########NEW FILE########
__FILENAME__ = httpclient
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
# 2013 Friedel Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import StringIO
import urllib
import logging

import gobject
import pycurl
try:
    import libproxy
    proxy_factory = libproxy.ProxyFactory()
except ImportError:
    libproxy = None

from virtaal.common.gobjectwrapper import GObjectWrapper

__all__ = ['HTTPClient', 'HTTPRequest', 'RESTRequest']


class HTTPRequest(GObjectWrapper):
    """Single HTTP request, blocking if used standalone."""

    __gtype_name__ = 'HttpClientRequest'
    __gsignals__ = {
        "http-success":      (gobject.SIGNAL_RUN_LAST, None, (object,)),
        "http-redirect":     (gobject.SIGNAL_RUN_LAST, None, (object,)),
        "http-client-error": (gobject.SIGNAL_RUN_LAST, None, (object,)),
        "http-server-error": (gobject.SIGNAL_RUN_LAST, None, (object,)),
    }

    def __init__(self, url, method='GET', data=None, headers=None,
            headers_only=False, user_agent=None, follow_location=False,
            force_quiet=True):
        GObjectWrapper.__init__(self)
        self.result = StringIO.StringIO()
        self.result_headers = StringIO.StringIO()

        if isinstance(url, unicode):
            self.url = url.encode("utf-8")
        else:
            self.url = url
        self.method = method
        self.data = data
        self.headers = headers
        self.status = None

        # the actual curl request object
        self.curl = pycurl.Curl()
        if (logging.root.level == logging.DEBUG and not force_quiet):
            self.curl.setopt(pycurl.VERBOSE, 1)

        self.curl.setopt(pycurl.WRITEFUNCTION, self.result.write)
        self.curl.setopt(pycurl.HEADERFUNCTION, self.result_headers.write)
        # We want to use gzip and deflate if possible:
        self.curl.setopt(pycurl.ENCODING, "") # use all available encodings
        self.curl.setopt(pycurl.URL, self.url)

        # let's set the HTTP request method
        if method == 'GET':
            self.curl.setopt(pycurl.HTTPGET, 1)
        elif method == 'POST':
            self.curl.setopt(pycurl.POST, 1)
        elif method == 'PUT':
            self.curl.setopt(pycurl.UPLOAD, 1)
        else:
            self.curl.setopt(pycurl.CUSTOMREQUEST, method)
        if data:
            if method == "PUT":
                self.data = StringIO.StringIO(data)
                self.curl.setopt(pycurl.READFUNCTION, self.data.read)
                self.curl.setopt(pycurl.INFILESIZE, len(self.data.getvalue()))
            else:
                self.curl.setopt(pycurl.POSTFIELDS, self.data)
                self.curl.setopt(pycurl.POSTFIELDSIZE, len(self.data))
        if headers:
            self.curl.setopt(pycurl.HTTPHEADER, headers)
        if headers_only:
            self.curl.setopt(pycurl.HEADER, 1)
            self.curl.setopt(pycurl.NOBODY, 1)
        if user_agent:
            self.curl.setopt(pycurl.USERAGENT, user_agent)
        if follow_location:
            self.curl.setopt(pycurl.FOLLOWLOCATION, 1)

        if libproxy:
            for proxy in proxy_factory.getProxies(self.url):
                # if we connect to localhost (localtm) with proxy specifically
                # set to direct://, libcurl connects fine, but then asks
                #   GET http://localhost:55555/unit/en/af/whatever
                # instead of
                #   GET /unit/en/af/whatever
                # and it doesn't work. We have to set it specifically to ""
                # though, otherwise it seems to fall back to environment
                # variables.
                if proxy == "direct://":
                    proxy = ""
                self.curl.setopt(pycurl.PROXY, proxy)
                #only use the first one
                break
        else:
            # Proxy: let's be careful to isolate the protocol to ensure that we
            # support the case where http and https might use different proxies
            split_url = self.url.split('://', 1)
            if len(split_url) > 1:
                #We were able to get a protocol
                protocol, address = split_url
                host, _path = urllib.splithost('//' + address)
                proxies = urllib.getproxies()
                if protocol in proxies and not urllib.proxy_bypass(host):
                    self.curl.setopt(pycurl.PROXY, proxies[protocol])

        # self reference required, because CurlMulti will only return
        # Curl handles
        self.curl.request = self

    def __repr__(self):
        return '<%s:%s>' % (self.method, self.get_effective_url())

    def get_effective_url(self):
        return self.curl.getinfo(pycurl.EFFECTIVE_URL)

    def perform(self):
        """run the request (blocks)"""
        self.curl.perform()

    def handle_result(self):
        """called after http request is done"""
        self.status = self.curl.getinfo(pycurl.HTTP_CODE)

        #TODO: handle 3xx, throw exception on other codes
        if self.status >= 200 and self.status < 300:
            # 2xx indicated success
            self.emit("http-success", self.result.getvalue())
        elif self.status >= 300 and self.status < 400:
            # 3xx redirection
            self.emit("http-redirect", self.result.getvalue())
        elif self.status >= 400 and self.status < 500:
            # 4xx client error
            self.emit("http-client-error", self.status)
        elif self.status >= 500 and self.status < 600:
            # 5xx server error
            self.emit("http-server-error", self.status)


class RESTRequest(HTTPRequest):
    """Single HTTP REST request, blocking if used standalone."""

    def __init__(self, url, id, method='GET', data=None, headers=None, user_agent=None, params=None):
        super(RESTRequest, self).__init__(url, method, data, headers, user_agent=user_agent)

        url = self.url
        self.id = id
        if id:
            url += '/' + urllib.quote(id.encode('utf-8'), safe='')

        if params:
            url += '?' + urllib.urlencode(params)

        self.curl.setopt(pycurl.URL, url)


class HTTPClient(object):
    """Non-blocking client that can handle multiple (asynchronous) HTTP requests."""

    def __init__(self):
        # state variable used to add and remove dispatcher to gtk event loop
        self.running = False

        # Since pycurl doesn't keep references to requests, requests
        # get garbage collected before they are done. We need to keep requests in
        # a set and detroy them manually.
        self.requests = set()
        self.curl = pycurl.CurlMulti()
        self.user_agent = None

    def add(self,request):
        """add a request to the queue"""
        # First ensure that we're not piling up on unanswered requests:
        if len(self.requests) > 15:
            return
        self.curl.add_handle(request.curl)
        self.requests.add(request)
        self.run()

    def run(self):
        """client should not be running when request queue is empty"""
        if self.running: return
        gobject.timeout_add(100, self.perform)
        self.running = True

    def close_request(self, handle):
        """finalize a successful request"""
        self.curl.remove_handle(handle)
        handle.request.handle_result()
        self.requests.remove(handle.request)

    def close_failed_request(self, fail_tuple):
        # fail_tuple is (handle, error_code, error_message)
        # see E_* constants in pycurl for error_code
        self.curl.remove_handle(fail_tuple[0])
        self.requests.remove(fail_tuple[0].request)
        logging.debug(fail_tuple[2])

    def perform(self):
        """main event loop function, non blocking execution of all queued requests"""
        ret, num_handles = self.curl.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM and num_handles == 0:
            self.running = False
        num, completed, failed = self.curl.info_read()
        [self.close_request(com) for com in completed]
        [self.close_failed_request(fail) for fail in failed]
        if not self.running:
            #we are done with this batch what do we do?
            return False
        return True

    def get(self, url, callback, etag=None, error_callback=None):
        headers = None
        if etag:
            # See http://en.wikipedia.org/wiki/HTTP_ETag for more details about ETags
            headers = ['If-None-Match: "%s"' % (etag)]
        request = HTTPRequest(url, headers=headers, user_agent=self.user_agent, follow_location=True)
        self.add(request)

        if callback:
            request.connect('http-success', callback)
            request.connect('http-redirect', callback)
        if error_callback:
            request.connect('http-client-error', error_callback)
            request.connect('http-server-error', error_callback)

    def set_virtaal_useragent(self):
        """Set a nice user agent indicating Virtaal and its version."""
        if self.user_agent and self.user_agent.startswith('Virtaal'):
            return
        import sys
        from virtaal.__version__ import ver as version
        platform = sys.platform
        if platform.startswith('linux'):
            import os
            # All systems supporting systemd:
            if os.path.isfile('/etc/os-release'):
                try:
                    lines = open('/etc/os-release').read().splitlines()
                    distro = None
                    distro_version = None
                    for line in lines:
                        if line.startswith('NAME'):
                            distro = line.split('=')[-1]
                            distro = distro.replace('"', '')
                        if line.startswith('VERSION'):
                            distro_version = line.split('=')[-1]
                            distro_version = distro_version.replace('"', '')
                    platform = '%s; %s %s' % (platform, distro, distro_version)
                except Exception, e:
                    pass

            # Debian, Ubuntu, Mandriva:
            elif os.path.isfile('/etc/lsb-release'):
                try:
                    lines = open('/etc/lsb-release').read().splitlines()
                    for line in lines:
                        if line.startswith('DISTRIB_DESCRIPTION'):
                            distro = line.split('=')[-1]
                            distro = distro.replace('"', '')
                            platform = '%s; %s' % (platform, distro)
                except Exception, e:
                    pass
            # Fedora, RHEL:
            elif os.path.isfile('/etc/system-release'):
                try:
                    lines = open('/etc/system-release').read().splitlines()
                    for line in lines:
                        distro, dummy, distro_version, codename = line.split()
                        platform = '%s; %s %s' % (platform, distro, distro_version)
                except Exception, e:
                    pass
        elif platform.startswith('win'):
            major, minor = sys.getwindowsversion()[:2]
            # from http://msdn.microsoft.com/en-us/library/ms724833%28v=vs.85%29.aspx
            name_dict = {
                    (5, 0): "Windows 2000",
                    (5, 1): "Windows XP",
                    (6, 0): "Windows Vista", # Also Windows Server 2008
                    (6, 1): "Windows 7",     # Also Windows Server 2008 R2
                    (6, 2): "Windows 8",     # Also Windows Server 2012
                    (6, 3): "Windows 8.1",   # Also Windows Server 2012 R2
            }
            # (5, 2) includes XP Professional x64 Edition, Server 2003, Home Server, Server 2003 R2
            name = name_dict.get((major, minor), None)
            if name:
                platform = '%s; %s' % (platform, name)
        elif platform.startswith('darwin'):
            import platform as plat
            release, versioninfo, machine = plat.mac_ver()
            platform = "%s; %s %s" % (platform, release, machine)
        self.user_agent = 'Virtaal/%s (%s)' % (version, platform)

########NEW FILE########
__FILENAME__ = locale
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008 Dieter Verfaillie <dieterv@optionexplicit.be>
# Copyright 2009-2010 Zuza Software Foundation
# Copyright 2013-2014 F Wolff
#
# (NOTE: LGPL)
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; If not, see <http://www.gnu.org/licenses/>.


import os
import sys


def _isofromlangid(langid):
    # ISO 639-1
    #    http://www.loc.gov/standards/iso639-2/
    # List of existing mui packs:
    #    http://www.microsoft.com/globaldev/reference/win2k/setup/Langid.mspx
    # List of known id's
    #    http://www.microsoft.com/globaldev/reference/lcid-all.mspx

    lcid = {1078:    'af',    # Afrikaans - South Africa
            1052:    'sq',    # Albanian - Albania
           #1156:    'gsw',   # Alsatian
            1118:    'am',    # Amharic - Ethiopia
            1025:    'ar',    # Arabic - Saudi Arabia
            5121:    'ar',    # Arabic - Algeria
            15361:   'ar',    # Arabic - Bahrain
            3073:    'ar',    # Arabic - Egypt
            2049:    'ar',    # Arabic - Iraq
            11265:   'ar',    # Arabic - Jordan
            13313:   'ar',    # Arabic - Kuwait
            12289:   'ar',    # Arabic - Lebanon
            4097:    'ar',    # Arabic - Libya
            6145:    'ar',    # Arabic - Morocco
            8193:    'ar',    # Arabic - Oman
            16385:   'ar',    # Arabic - Qatar
            10241:   'ar',    # Arabic - Syria
            7169:    'ar',    # Arabic - Tunisia
            14337:   'ar',    # Arabic - U.A.E.
            9217:    'ar',    # Arabic - Yemen
            1067:    'hy',    # Armenian - Armenia
            1101:    'as',    # Assamese
            2092:    'az',    # Azeri (Cyrillic)
            1068:    'az',    # Azeri (Latin)
            1133:    'ba',    # Bashkir
            1069:    'eu',    # Basque
            1059:    'be',    # Belarusian
            1093:    'bn_IN', # Bengali (India)
            2117:    'bn',    # Bengali (Bangladesh)
            5146:    'bs',    # Bosnian (Bosnia/Herzegovina)
            1150:    'br',    # Breton
            1026:    'bg',    # Bulgarian
            1109:    'my',    # Burmese
            1027:    'ca',    # Catalan
            1116:    'chr',   # Cherokee - United States
            2052:    'zh_CN', # Chinese - People's Republic of China
            4100:    'zh',    # Chinese - Singapore
            1028:    'zh_TW', # Chinese - Taiwan
            3076:    'zh_HK', # Chinese - Hong Kong SAR
            5124:    'zh',    # Chinese - Macao SAR
            1155:    'co',    # Corsican
            1050:    'hr',    # Croatian
            4122:    'hr',    # Croatian (Bosnia/Herzegovina)
            1029:    'cs',    # Czech
            1030:    'da',    # Danish
           #1164:    'fa_AF'  # Dari
            1125:    'dv',    # Divehi
            1043:    'nl',    # Dutch - Netherlands
            2067:    'nl',    # Dutch - Belgium
            1126:    'bin',   # Edo
            1033:    'en',    # English - United States
            2057:    'en_UK', # English - United Kingdom
            3081:    'en',    # English - Australia
            10249:   'en',    # English - Belize
            4105:    'en_CA', # English - Canada
            9225:    'en',    # English - Caribbean
            15369:   'en',    # English - Hong Kong SAR
            16393:   'en',    # English - India
            14345:   'en',    # English - Indonesia
            6153:    'en',    # English - Ireland
            8201:    'en',    # English - Jamaica
            17417:   'en',    # English - Malaysia
            5129:    'en',    # English - New Zealand
            13321:   'en',    # English - Philippines
            18441:   'en',    # English - Singapore
            7177:    'en_ZA', # English - South Africa
            11273:   'en',    # English - Trinidad
            12297:   'en',    # English - Zimbabwe
            1061:    'et',    # Estonian
            1080:    'fo',    # Faroese
            1065:    'fa',    # Persian
            1124:    'fil',   # Filipino #XXX: GTK uses Tagalog (tl)
            1035:    'fi',    # Finnish
            1036:    'fr',    # French - France
            2060:    'fr',    # French - Belgium
            11276:   'fr',    # French - Cameroon
            3084:    'fr',    # French - Canada
            9228:    'fr',    # French - Democratic Rep. of Congo
            12300:   'fr',    # French - Cote d'Ivoire
            15372:   'fr',    # French - Haiti
            5132:    'fr',    # French - Luxembourg
            13324:   'fr',    # French - Mali
            6156:    'fr',    # French - Monaco
            14348:   'fr',    # French - Morocco
            58380:   'fr',    # French - North Africa
            8204:    'fr',    # French - Reunion
            10252:   'fr',    # French - Senegal
            4108:    'fr',    # French - Switzerland
            7180:    'fr',    # French - West Indies
            1122:    'fy',    # Frisian - Netherlands
            1127:    'ff',    # Fulfulde - Nigeria
            1071:    'mk',    # FYRO Macedonian
            2108:    'ga',    # Gaelic (Ireland)
            1084:    'gd',    # Gaelic (Scotland)
            1110:    'gl',    # Galician
            1079:    'ka',    # Georgian
            1031:    'de',    # German - Germany
            3079:    'de',    # German - Austria
            5127:    'de',    # German - Liechtenstein
            4103:    'de',    # German - Luxembourg
            2055:    'de',    # German - Switzerland
            1032:    'el',    # Greek
            1135:    'kl',    # Greenlandic
            1140:    'gn',    # Guarani - Paraguay
            1095:    'gu',    # Gujarati
            1128:    'ha',    # Hausa - Nigeria
            1141:    'haw',   # Hawaiian - United States
            1037:    'he',    # Hebrew
            1081:    'hi',    # Hindi
            1038:    'hu',    # Hungarian
            1129:    'ibb',   # Ibibio - Nigeria
            1039:    'is',    # Icelandic
            1136:    'ig',    # Igbo - Nigeria
            1057:    'id',    # Indonesian
            1117:    'iu',    # Inuktitut
            1040:    'it',    # Italian - Italy
            2064:    'it',    # Italian - Switzerland
            1041:    'ja',    # Japanese
            1158:    'quc',   # K'iche
            1099:    'kn',    # Kannada
            1137:    'kr',    # Kanuri - Nigeria
            2144:    'ks',    # Kashmiri
            1120:    'ks',    # Kashmiri (Arabic)
            1087:    'kk',    # Kazakh
            1107:    'km',    # Khmer
            1159:    'rw',    # Kinyarwanda
            1111:    'knn',   # Konkani
            1042:    'ko',    # Korean
            1088:    'ky',    # Kyrgyz (Cyrillic)
            1108:    'lo',    # Lao
            1142:    'la',    # Latin
            1062:    'lv',    # Latvian
            1063:    'lt',    # Lithuanian
            1134:    'lb',    # Luxembourgish
            1086:    'ms',    # Malay - Malaysia
            2110:    'ms',    # Malay - Brunei Darussalam
            1100:    'ml',    # Malayalam
            1082:    'mt',    # Maltese
            1112:    'mni',   # Manipuri
            1153:    'mi',    # Maori - New Zealand
            1146:    'arn',   # Mapudungun
            1102:    'mr',    # Marathi
            1148:    'moh',   # Mohawk
            1104:    'mn',    # Mongolian (Cyrillic)
            2128:    'mn',    # Mongolian (Mongolian)
            1121:    'ne',    # Nepali
            2145:    'ne',    # Nepali - India
            1044:    'no',    # Norwegian (Bokmￃﾥl)
            2068:    'no',    # Norwegian (Nynorsk)
            1154:    'oc',    # Occitan
            1096:    'or',    # Oriya
            1138:    'om',    # Oromo
            1145:    'pap',   # Papiamentu
            1123:    'ps',    # Pashto
            1045:    'pl',    # Polish
            1046:    'pt_BR', # Portuguese - Brazil
            2070:    'pt',    # Portuguese - Portugal
            1094:    'pa',    # Punjabi
            2118:    'pa',    # Punjabi (Pakistan)
            1131:    'qu',    # Quecha - Bolivia
            2155:    'qu',    # Quecha - Ecuador
            3179:    'qu',    # Quecha - Peru
            1047:    'rm',    # Rhaeto-Romanic
            1048:    'ro',    # Romanian
            2072:    'ro',    # Romanian - Moldava
            1049:    'ru',    # Russian
            2073:    'ru',    # Russian - Moldava
            1083:    None,    # Sami (Lappish)
            1103:    'sa',    # Sanskrit
            1132:    'nso',   # Northern Sotho
            3098:    'sr',    # Serbian (Cyrillic)
            2074:    'sr@latin',# Serbian (Latin)
            1113:    'sd',    # Sindhi - India
            2137:    'sd',    # Sindhi - Pakistan
            1115:    'si',    # Sinhalese - Sri Lanka
            1051:    'sk',    # Slovak
            1060:    'sl',    # Slovenian
            1143:    'so',    # Somali
            1070:    None,    # Sorbian
            3082:    'es',    # Spanish - Spain (Modern Sort)
            1034:    'es',    # Spanish - Spain (Traditional Sort)
            11274:   'es',    # Spanish - Argentina
            16394:   'es',    # Spanish - Bolivia
            13322:   'es',    # Spanish - Chile
            9226:    'es',    # Spanish - Colombia
            5130:    'es',    # Spanish - Costa Rica
            7178:    'es',    # Spanish - Dominican Republic
            12298:   'es',    # Spanish - Ecuador
            17418:   'es',    # Spanish - El Salvador
            4106:    'es',    # Spanish - Guatemala
            18442:   'es',    # Spanish - Honduras
            58378:   'es',    # Spanish - Latin America
            2058:    'es',    # Spanish - Mexico
            19466:   'es',    # Spanish - Nicaragua
            6154:    'es',    # Spanish - Panama
            15370:   'es',    # Spanish - Paraguay
            10250:   'es',    # Spanish - Peru
            20490:   'es',    # Spanish - Puerto Rico
            21514:   'es',    # Spanish - United States
            14346:   'es',    # Spanish - Uruguay
            8202:    'es',    # Spanish - Venezuela
            1072:    'st',    # Sutu
            1089:    'sw',    # Swahili
            1053:    'sv',    # Swedish
            2077:    'sv',    # Swedish - Finland
            1114:    'syc',   # Syriac
            1064:    'tg',    # Tajik
            1119:    None,    # Tamazight (Arabic)
            2143:    None,    # Tamazight (Latin)
            1097:    'ta',    # Tamil
            1092:    'tt',    # Tatar
            1098:    'te',    # Telugu
            1054:    'th',    # Thai
            2129:    'bo',    # Tibetan - Bhutan
            1105:    'bo',    # Tibetan - People's Republic of China
            2163:    'ti',    # Tigrigna - Eritrea
            1139:    'ti',    # Tigrigna - Ethiopia
            1073:    'ts',    # Tsonga
            1074:    'tn',    # Tswana
            1055:    'tr',    # Turkish
            1090:    'tk',    # Turkmen
            1152:    'ug',    # Uighur - China
            1058:    'uk',    # Ukrainian
            1056:    'ur',    # Urdu
            2080:    'ur',    # Urdu - India
            2115:    'uz@cyrillic',    # Uzbek (Cyrillic)
            1091:    'uz',    # Uzbek (Latin)
            1075:    've',    # Venda
            1066:    'vi',    # Vietnamese
            1106:    'cy',    # Welsh
            1160:    'wo',    # Wolof
            1076:    'xh',    # Xhosa
            1157:    'sah',   # Yakut
            1144:    'ii',    # Yi
            1085:    'yi',    # Yiddish
            1130:    'yo',    # Yoruba
            1077:    'zu',    # Zulu
    }

    return lcid.get(langid, None)


def get_win32_lang(system_ui=False):
    """Return the locale for the user (default) or the system UI."""
    # This supports windows MUI language packs and will return
    # the windows installation language if not available or
    # if the language has not been changed by the user.
    # Works on win2k and up.
    from ctypes import windll
    if system_ui:
        #Windows UI language
        langid = windll.kernel32.GetUserDefaultUILanguage()
    else:
        #User's locale
        langid = windll.kernel32.GetUserDefaultLangID()
    if not langid == 0:
        lang = _isofromlangid(langid) or 'C'
    else:
        lang = 'C'

    return lang


def _getlang():
    # Environment always overrides this for debugging purposes.
    lang = os.getenv('LANG') or get_win32_lang()
    return lang


def _putenv(name, value):
    # From python 2.4 on, os.environ changes only
    # work within python and no longer apply to low level
    # C stuff on win32. Let's force LANG so it works with
    # gtk+ etc
    from ctypes import windll
    kernel32 = windll.kernel32
    result = kernel32.SetEnvironmentVariableW(name, value)
    del kernel32
    if result == 0:
        raise

    from ctypes import cdll
    msvcrt = cdll.msvcrt
    result = msvcrt._putenv('%s=%s' % (name, value))
    del msvcrt


def fix_locale(lang=None):
    """This fixes some strange issues to ensure locale and gettext works
    correctly, also within glade, even with a non-default locale passed as
    parameter."""
    if sys.platform == 'win32':
        lang = lang or _getlang()

        _putenv('LANGUAGE', lang)

        os.environ['LANG'] = lang
        _putenv('LANG', lang)

        os.environ['LC_ALL'] = lang
        _putenv('LC_ALL', lang)
    if lang:
        # This is to support a non-locale UI language:
        os.environ['LANGUAGE'] = lang


def fix_libintl(main_dir):
    """Bind gettext in the libintl since the gettext package doesn't."""
    # See https://bugzilla.gnome.org/show_bug.cgi?id=574520
    from ctypes import cdll
    libintl = cdll.intl
    # we need main_dir in the filesystem encoding:
    main_dir = main_dir.encode(sys.getfilesystemencoding())
    locale_dir = os.path.join(main_dir, "share", "locale")
    libintl.bindtextdomain("virtaal", locale_dir)
    libintl.bind_textdomain_codeset("virtaal", 'UTF-8')
    del libintl

########NEW FILE########
__FILENAME__ = mosesclient
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import logging
import xmlrpclib

from translate.lang import data

from virtaal.support.httpclient import HTTPClient, HTTPRequest

# Moses handles these characters as spaced out
punc_symbols = ur'''.,?!:;'"“”‘’—)'''
punc_tuples = [(c, u" %s" % c) for c in punc_symbols]


def prepare(query_str):
    query_str = query_str.lower()
    for c, repl in punc_tuples:
        query_str = query_str.replace(c, repl)
    query_str = query_str.replace(u"(", u"( ")
    # Newlines need special handling since Moses doesn't support it:
    query_str = query_str.replace(u"\n", u" __::__ ")
    return query_str

def fixup(source, response):
    source = data.forceunicode(source)
    response = data.forceunicode(response)
    from translate.filters.autocorrect import correct
    tmp = correct(source, response)
    if tmp:
        response = tmp
    response = response.replace(u" __::__ ", "\n")
    # and again for the sake of \n\n:
    response = response.replace(u"__::__ ", "\n")
    response = response.replace(u"( ", u"(")
    for c, repl in punc_tuples:
        response = response.replace(repl, c)
    return response


class MosesClient(gobject.GObject, HTTPClient):
    """A client to communicate with a moses XML RPC servers"""

    __gtype_name__ = 'MosesClient'
    __gsignals__ = {
        'source-lang-changed': (gobject.SIGNAL_RUN_LAST, None, (str,)),
        'target-lang-changed': (gobject.SIGNAL_RUN_LAST, None, (str,)),
    }

    def __init__(self, url):
        gobject.GObject.__init__(self)
        HTTPClient.__init__(self)

        self.url = url + '/RPC2'
        self.multilang = False

    def set_multilang(self, state=True):
        """Enable multilingual support.

        If this is set, the plugin will specify the 'system' parameter when
        communicating with the Moses XML RPC server."""
        self.multilang = state

    def translate_unit(self, unit_source, callback=None, target_language=None):
        parameters = {
                'text': prepare(unit_source),
        }
        if self.multilang:
            parameters['system'] = target_language

        request_body = xmlrpclib.dumps(
                (parameters,), "translate"
        )
        request = HTTPRequest(
            self.url, "POST", request_body,
            headers=["Content-Type: text/xml", "Content-Length: %s" % len(request_body)],
        )
        request.source_text = unit_source
        self.add(request)

        if callback:
            def call_callback(request, response):
                return callback(
                    request.source_text, self._handle_response(request.source_text, response)
                )
            request.connect("http-success", call_callback)

    def _loads_safe(self, response):
        """Does the loading of the XML-RPC response, but handles exceptions."""
        try:
            (data,), _fish = xmlrpclib.loads(response)
        except xmlrpclib.Fault, exc:
            if "Unknown translation system id" in exc.faultString:
                self.set_multilang(False)
                #TODO: consider redoing the request now that multilang is False
                return None
        except Exception, exc:
            logging.debug('XML-RPC exception: %s' % (exc))
            return None
        return data

    def _handle_response(self, id, response):
        """Use the same format as tmserver."""
        suggestion = self._loads_safe(response)
        if not suggestion:
            return None
        return fixup(id, data.forceunicode(suggestion['text']))

########NEW FILE########
__FILENAME__ = native_widgets
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Zuza Software Foundation
# Copyright 2013-2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""This provides access to the native file dialogs for certain platforms, and
some related helper code."""

import os
import sys
import gettext

from virtaal.common import pan_app

#TODO:
# - refactor repeated parts
# - Confirm error handling works correctly


def _dialog_to_use():
    # We want to know if we should use a native dialog, but don't want to show
    # it in a different language than the Virtaal UI. So we can try to detect
    # if the system (Windows/KDE) is in the same language as the Virtaal GUI.
    ui_language = pan_app.ui_language

    if sys.platform == 'win32':
        from virtaal.support.libi18n.locale import get_win32_lang
        win32_lang = get_win32_lang(system_ui=True)
        if win32_lang == ui_language or ui_language == 'en' and win32_lang == 'C':
            return 'win32'

    elif os.environ.get('KDE_FULL_SESSION') == 'true' and ( \
                pan_app.ui_language == 'en' or \
                gettext.dgettext('kdelibs4', '') or \
                not gettext.dgettext('gtk20', '')):
            return 'kdialog'

    if sys.platform == 'darwin':
        return 'darwin'

    return None # default

# Hardcode for testing:
dialog_to_use = _dialog_to_use()
#dialog_to_use = 'kdialog'
#dialog_to_use = 'win32'
#dialog_to_use = None

_file_types = []

def _get_file_types():
    global _file_types
    if _file_types:
        return _file_types
    from translate.storage import factory
    from locale import strcoll
    all_supported_ext = []
    supported_files = []
    _sorted = sorted(factory.supported_files(), cmp=strcoll, key=lambda x: x[0])
    for name, extensions, mimetypes in _sorted:
        name = _(name)
        extension_filter = ["*.%s" % ext for ext in extensions]
        all_supported_ext.extend(extension_filter)
        supported_files.append((name, extension_filter))

    supported_files.insert(0, (_("All Supported Files"), all_supported_ext))
    _file_types = supported_files
    return supported_files

def _get_used_filetypes(current_filename):
    directory, filename = os.path.split(current_filename)
    name, extension = os.path.splitext(filename)
    supported_files = []
    for type_name, extensions in _get_file_types():
        if "*%s" % extension in extensions:
            supported_files = [(type_name, extensions)]
    return supported_files

### KDE/kdialog ###

def _show_kdialog(window, title, args):
    xid = window.window.xid
    import subprocess
    command = [
            'kdialog',
#            '--name', _('Virtaal'),
#            '--title', 'Virtaal',
            '--caption', _('Virtaal'),
            '--icon', 'virtaal',
            '--title', title,
            '--attach', str(xid),
    ]
    command.extend(args)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    output = output [:-1] # we don't want the last newline
    error = output [:-1] # we don't want the last newline
    ret = process.returncode
    # bash truth values: 0/1 = True/False
    if ret == 0: # success
        filename = output.decode('utf-8') # get system locale
        pan_app.settings.general["lastdir"] = os.path.dirname(filename)
        return (True, filename)
    if ret == 1: # cancel
        return (False, u'')
    raise Exception("Something went wrong with kdialog", error)


def kdialog_open_dialog(window, title, directory):
    supported_files = _get_file_types()
    args = [
        '--getopenfilename', directory or '.',
        #'''*.po *.xlf|All Translatable Files\n*.ts|Qt .ts file''',   # example with wildcards
        #'text/x-gettext-translation application/x-xliff application/x-linguist,   #example with mime-types
        '\n'.join('|'.join([' '.join(extensions), name]) for name, extensions in supported_files)
    ]
    title = title or _("Choose a Translation File")
    (returncode, filename) = _show_kdialog(window, title, args)
    if returncode:
        return (filename, u"file://%s" % filename)
    else:
        return ()

def kdialog_save_dialog(window, title, current_filename):
    supported_files = _get_used_filetypes(current_filename)
    args = [
        '--getsavefilename', current_filename or '.',
        '\n'.join('|'.join([' '.join(extensions), name]) for name, extensions in supported_files)
    ]
    title = title or _("Save")
    (returncode, filename) = _show_kdialog(window, title, args)
    if returncode and os.path.exists(filename):
        # confirm overwrite, since kdialog can't:
        args = [
            '--yesno',
            #gettext.dgettext('gtk20.mo', 'A file named \"%s\" already exists.  Do you want to replace it?') % filename,
            gettext.dgettext('kdelibs4', 'A file named "%1" already exists. Are you sure you want to overwrite it?').replace('%1', '%s') % filename,
        ]
        (should_overwrite, _nothing) = _show_kdialog(window, "Overwrite", args)
        if not should_overwrite:
            return None
        return filename
    return None


#### Windows/win32 ####

def win32_open_dialog(window, title, directory):
    # http://msdn.microsoft.com/en-us/library/aa155724%28v=office.10%29.aspx
    import winxpgui
    import win32con
    import pywintypes
    supported_files = [ (_(name), ';'.join(extensions)) for name, extensions in _get_file_types() ]

    type_filter = '\0'.join(('%s\0%s') % (name, extensions) for name, extensions in supported_files) + '\0'
    custom_filter = _("All Files") + '\0*.*\0'
    title = title or _('Choose a Translation File')
    try:
        filename, customfilter, flags = winxpgui.GetOpenFileNameW(
            hwndOwner=window.window.handle,
            InitialDir=directory,
            Flags=win32con.OFN_EXPLORER|win32con.OFN_FILEMUSTEXIST|win32con.OFN_HIDEREADONLY,
            File='', DefExt='',
            Title=title,
            Filter=type_filter,
            CustomFilter=custom_filter,
            FilterIndex=1,              # Select the "All Supported Files"
        )
    except pywintypes.error, e:
        if isinstance(e.args, tuple) and len(e.args) == 3:
            if e.args[0] == 0:
                # cancel
                return ()
        raise Exception("Something went wrong with winxpgui", e)
    # success
    pan_app.settings.general["lastdir"] = os.path.dirname(filename)
    return (filename, u"file:///%s" % filename)

def win32_save_dialog(window, title, current_filename):
    import winxpgui
    import win32con
    import pywintypes
    supported_files = _get_used_filetypes(current_filename)

    type_filter = '\0'.join(('%s\0%s') % (name, ';'.join(extensions)) for name, extensions in supported_files) + '\0'
    custom_filter = _("All Files") + '\0*.*\0'
    directory, filename = os.path.split(current_filename)
    name, extension = os.path.splitext(filename)
    title = title or _('Save')
    try:
        filename, customfilter, flags = winxpgui.GetSaveFileNameW(
            hwndOwner=window.window.handle,
            InitialDir=directory,
            Flags=win32con.OFN_EXPLORER|win32con.OFN_OVERWRITEPROMPT,
            File=name, DefExt=extension,
            Title=title,
            Filter=type_filter,
            CustomFilter=custom_filter,
            FilterIndex=1,              # Select the relevant filter
        )
    except pywintypes.error, e:
        if isinstance(e.args, tuple) and len(e.args) == 3:
            if e.args[0] == 0:
                # cancel
                return u''
        raise Exception("Something went wrong with winxpgui", e)
    # success
    return filename


#### Mac/darwin ####

def darwin_open_dialog(window, title, directory):
    # http://developer.apple.com/library/mac/#documentation/Cocoa/Conceptual/AppFileMgmt/Concepts/SaveOpenPanels.html#//apple_ref/doc/uid/20000771-BBCFDGFC
    # http://scottr.org/blog/2008/jul/04/building-cocoa-guis-python-pyobjc-part-four/
    from objc import NO
    from AppKit import NSOpenPanel
    from translate.storage import factory
    from locale import strcoll
    file_types = []
    _sorted = sorted(factory.supported_files(), cmp=strcoll, key=lambda x: x[0])
    for name, extension, mimetype in _sorted:
        file_types.extend(extension)
    panel = NSOpenPanel.openPanel()
    panel.setCanChooseDirectories_(NO)
    panel.setTitle_(title or _("Choose a Translation File"))
    panel.setAllowsMultipleSelection_(NO)
    panel.setAllowedFileTypes_(file_types)
    panel.setDirectoryURL_(u"file:///%s" % directory)
    ret_value = panel.runModalForTypes_(file_types)
    if ret_value:
        return (panel.filenames()[0], panel.URLs()[0].absoluteString())
    else:
        return ()

def darwin_save_dialog(window, title, current_filename):
    from AppKit import NSSavePanel
    directory, filename = os.path.split(current_filename)
    panel = NSSavePanel.savePanel()
    panel.setTitle_(title or _("Save"))
    panel.setDirectoryURL_(u"file:///%s" % directory)
    panel.setNameFieldStringValue_(filename)
    ret_value = panel.runModal()
    if ret_value:
        return panel.filename()
    else:
        return u''

########NEW FILE########
__FILENAME__ = openmailto
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# This file incorporates work covered by the following copyright:
#
#   Copyright (c) 2007, Antonio Valentino
#   Obtained from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/511443
#   which is licensed under the Python license.

"""Utilities for opening files or URLs in the registered default application
and for sending e-mail using the user's preferred composer."""

__version__ = '1.0'
__all__ = ['open', 'mailto']

import os
import sys
import logging
# Some imports are only necessary on some platforms, and are postponed to try
# to speed up startup


_controllers = {}
_open = None


class BaseController(object):
    '''Base class for open program controllers.'''

    def __init__(self, name):
        self.name = name

    def open(self, filename):
        raise NotImplementedError


class Controller(BaseController):
    '''Controller for a generic open program.'''

    def __init__(self, *args):
        super(Controller, self).__init__(os.path.basename(args[0]))
        self.args = list(args)

    def _invoke(self, cmdline):
        import subprocess
        if sys.platform[:3] == 'win':
            closefds = False
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            closefds = True
            startupinfo = None

        if (os.environ.get('DISPLAY') or sys.platform[:3] == 'win' or
                                                    sys.platform == 'darwin'):
            inout = file(os.devnull, 'r+')
        else:
            # for TTY programs, we need stdin/out
            inout = None

        # if possible, put the child precess in separate process group,
        # so keyboard interrupts don't affect child precess as well as
        # Python
        setsid = getattr(os, 'setsid', None)
        if not setsid:
            setsid = getattr(os, 'setpgrp', None)

        pipe = subprocess.Popen(cmdline, stdin=inout, stdout=inout,
                                stderr=inout, close_fds=closefds,
                                preexec_fn=setsid, startupinfo=startupinfo)

        # It is assumed that this kind of tools (gnome-open, kfmclient,
        # exo-open, xdg-open and open for OSX) immediately exit after lauching
        # the specific application
        returncode = pipe.wait()
        if hasattr(self, 'fixreturncode'):
            returncode = self.fixreturncode(returncode)
        return not returncode

    def open(self, filename):
        if isinstance(filename, basestring):
            cmdline = self.args + [filename]
        else:
            # assume it is a sequence
            cmdline = self.args + filename
        try:
            return self._invoke(cmdline)
        except OSError:
            return False


# Platform support for Windows
if sys.platform[:3] == 'win':

    class Start(BaseController):
        '''Controller for the win32 start progam through os.startfile.'''

        def open(self, filename):
            try:
                os.startfile(filename)
            except WindowsError:
                # [Error 22] No application is associated with the specified
                # file for this operation: '<URL>'
                return False
            else:
                return True

    _controllers['windows-default'] = Start("start")
    _open = _controllers['windows-default'].open


# Platform support for MacOS
elif sys.platform == 'darwin':
    _controllers['open']= Controller('open')
    _open = _controllers['open'].open


# Platform support for Unix
else:

    import commands
    # @WARNING: use the private API of the webbrowser module (._iscommand)
    import webbrowser

    class KfmClient(Controller):
        '''Controller for the KDE kfmclient program.'''

        def __init__(self, kfmclient='kfmclient'):
            super(KfmClient, self).__init__(kfmclient, 'exec')
            self.kde_version = self.detect_kde_version()

        def detect_kde_version(self):
            kde_version = None
            try:
                info = commands.getoutput('kde-config --version')

                for line in info.splitlines():
                    if line.startswith('KDE'):
                        kde_version = line.split(':')[-1].strip()
                        break
            except (OSError, RuntimeError):
                pass

            return kde_version

        def fixreturncode(self, returncode):
            if returncode is not None and self.kde_version > '3.5.4':
                return returncode
            else:
                return os.EX_OK

    def detect_desktop_environment():
        '''Checks for known desktop environments

        Return the desktop environments name, lowercase (kde, gnome, xfce)
        or "generic"

        '''

        desktop_environment = 'generic'

        if os.environ.get('KDE_FULL_SESSION') == 'true':
            desktop_environment = 'kde'
        elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
            desktop_environment = 'gnome'
        else:
            try:
                info = commands.getoutput('xprop -root _DT_SAVE_MODE')
                if ' = "xfce4"' in info:
                    desktop_environment = 'xfce'
            except (OSError, RuntimeError):
                pass

        return desktop_environment


    def register_X_controllers():
        if webbrowser._iscommand('kfmclient'):
            _controllers['kde-open'] = KfmClient()

        for command in ('gnome-open', 'exo-open', 'xdg-open'):
            if webbrowser._iscommand(command):
                _controllers[command] = Controller(command)

    def get():
        controllers_map = { \
            'gnome': 'gnome-open',
            'kde': 'kde-open',
            'xfce': 'exo-open',
        }

        desktop_environment = detect_desktop_environment()

        try:
            controller_name = controllers_map[desktop_environment]
            return _controllers[controller_name].open

        except KeyError:
            if _controllers.has_key('xdg-open'):
                return _controllers['xdg-open'].open
            else:
                return webbrowser.open


    if os.environ.get("DISPLAY"):
        register_X_controllers()
    _open = get()


def open(filename):
    '''Open a file or an URL in the registered default application.'''

    return _open(filename)


def _fix_addersses(**kwargs):
    for headername in ('address', 'to', 'cc', 'bcc'):
        try:
            headervalue = kwargs[headername]
            if not headervalue:
                del kwargs[headername]
                continue
            elif not isinstance(headervalue, basestring):
                # assume it is a sequence
                headervalue = ','.join(headervalue)

        except KeyError:
            pass
        except TypeError:
            raise TypeError('string or sequence expected for "%s", ' \
                            '%s found' % (headername,
                                          type(headervalue).__name__))
        else:
            translation_map = {'%': '%25', '&': '%26', '?': '%3F'}
            for char, replacement in translation_map.items():
                headervalue = headervalue.replace(char, replacement)
            kwargs[headername] = headervalue

    return kwargs


def mailto_format(**kwargs):
    # @TODO: implement utf8 option

    from email.Utils import encode_rfc2231
    kwargs = _fix_addersses(**kwargs)
    parts = []
    for headername in ('to', 'cc', 'bcc', 'subject', 'body', 'attach'):
        if kwargs.has_key(headername):
            headervalue = kwargs[headername]
            if not headervalue:
                continue
            if headername in ('address', 'to', 'cc', 'bcc'):
                parts.append('%s=%s' % (headername, headervalue))
            else:
                headervalue = encode_rfc2231(headervalue) # @TODO: check
                parts.append('%s=%s' % (headername, headervalue))

    mailto_string = 'mailto:%s' % kwargs.get('address', '')
    if parts:
        mailto_string = '%s?%s' % (mailto_string, '&'.join(parts))

    return mailto_string


def mailto(address, to=None, cc=None, bcc=None, subject=None, body=None,
           attach=None):
    '''Send an e-mail using the user's preferred composer.

    Open the user's preferred e-mail composer in order to send a mail to
    address(es) that must follow the syntax of RFC822. Multiple addresses
    may be provided (for address, cc and bcc parameters) as separate
    arguments.

    All parameters provided are used to prefill corresponding fields in
    the user's e-mail composer. The user will have the opportunity to
    change any of this information before actually sending the e-mail.

    @param address: destination recipient
    @param cc: recipient to be copied on the e-mail
    @param bcc: recipient to be blindly copied on the e-mail
    @param subject: subject for the e-mail
    @param body: body of the e-mail. Since the user will be able
              to make changes before actually sending the e-mail, this
              can be used to provide the user with a template for the
              e-mail text may contain linebreaks
    @param attach: an attachment for the e-mail. file must point to
              an existing file
    '''

    mailto_string = mailto_format(**locals())
    return open(mailto_string)


if __name__ == '__main__':
    from optparse import OptionParser

    version = '%%prog %s' % __version__
    usage = (
        '\n\n%prog FILENAME [FILENAME(s)] -- for opening files'
        '\n\n%prog -m [OPTIONS] ADDRESS [ADDRESS(es)] -- for sending e-mails'
    )

    parser = OptionParser(usage=usage, version=version, description=__doc__)
    parser.add_option('-m', '--mailto', dest='mailto_mode', default=False, \
                      action='store_true', help='set mailto mode. '
                      'If not set any other option is ignored')
    parser.add_option('--cc', dest='cc', help='specify a recipient to be '
                      'copied on the e-mail')
    parser.add_option('--bcc', dest='bcc', help='specify a recipient to be '
                      'blindly copied on the e-mail')
    parser.add_option('--subject', dest='subject',
                      help='specify a subject for the e-mail')
    parser.add_option('--body', dest='body', help='specify a body for the '
                      'e-mail. Since the user will be able to make changes '
                      'before actually sending the e-mail, this can be used '
                      'to provide the user with a template for the e-mail '
                      'text may contain linebreaks')
    parser.add_option('--attach', dest='attach', help='specify an attachment '
                      'for the e-mail. file must point to an existing file')

    (options, args) = parser.parse_args()

    if not args:
        parser.print_usage()
        parser.exit(1)

    if options.mailto_mode:
        if not mailto(args, None, options.cc, options.bcc, options.subject,
                      options.body, options.attach):
            sys.exit('Unable to open the e-mail client')
    else:
        for name in ('cc', 'bcc', 'subject', 'body', 'attach'):
            if getattr(options, name):
                parser.error('The "cc", "bcc", "subject", "body" and "attach" '
                             'options are only accepten in mailto mode')
        success = False
        for arg in args:
            if not open(arg):
                logging.debug('Unable to open "%s"', arg)
            else:
                success = True
        sys.exit(success)

########NEW FILE########
__FILENAME__ = opentranclient
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import logging
# These two json modules are API compatible
try:
    import simplejson as json #should be a bit faster; needed for Python < 2.6
except ImportError:
    import json #available since Python 2.6

from translate.lang import data
from translate.search.lshtein import LevenshteinComparer

from virtaal.support.httpclient import HTTPClient, RESTRequest

class OpenTranClient(gobject.GObject, HTTPClient):
    """CRUD operations for TM units and stores"""

    __gtype_name__ = 'OpenTranClient'
    __gsignals__ = {
        'source-lang-changed': (gobject.SIGNAL_RUN_LAST, None, (str,)),
        'target-lang-changed': (gobject.SIGNAL_RUN_LAST, None, (str,)),
    }

    def __init__(self, max_candidates=3, min_similarity=75, max_length=1000):
        gobject.GObject.__init__(self)
        HTTPClient.__init__(self)

        self.max_candidates = max_candidates
        self.min_similarity = min_similarity
        self.comparer = LevenshteinComparer(max_length)
        self.last_suggestions = []  # used by the open-tran terminology backend

        self._languages = set()

        self.source_lang = None
        self.target_lang = None
        #detect supported language

        self.url_getlanguages = 'http://open-tran.eu/json/supported'
        self.url_translate = 'http://%s.%s.open-tran.eu/json/suggest'
        langreq = RESTRequest(self.url_getlanguages, id='')
        self.add(langreq)
        langreq.connect(
            'http-success',
            lambda langreq, response: self.got_languages(response)
        )

    def got_languages(self, val):
        """Handle the response from the web service to set up language pairs."""
        data = self._loads_safe(val)
        self._languages = set(data)
        self.set_source_lang(self.source_lang)
        self.set_target_lang(self.target_lang)

    def translate_unit(self, unit_source, callback=None):
        if self.source_lang is None or self.target_lang is None:
            return

        if not self._languages:
            # for some reason we don't (yet) have supported languages
            return

        query_str = unit_source
        request = RESTRequest(self.url_translate % (self.source_lang, self.target_lang), id=query_str)
        self.add(request)
        def call_callback(request, response):
            return callback(
                request, request.id, self.format_suggestions(request.id, response)
            )

        if callback:
            request.connect("http-success", call_callback)

    def set_source_lang(self, language):
        language = language.lower().replace('-', '_').replace('@', '_')
        if not self._languages:
            # for some reason we don't (yet) have supported languages
            self.source_lang = language
            # we'll redo this once we have languages
            return

        if language in self._languages:
            self.source_lang = language
            logging.debug("source language %s supported" % language)
            self.emit('source-lang-changed', self.source_lang)
        else:
            lang = data.simplercode(language)
            if lang:
                self.set_source_lang(lang)
            else:
                self.source_lang = None
                logging.debug("source language %s not supported" % language)

    def set_target_lang(self, language):
        language = language.lower().replace('-', '_').replace('@', '_')
        if not self._languages:
            # for some reason we don't (yet) have supported languages
            self.target_lang = language
            # we'll redo this once we have languages
            return

        if language in self._languages:
            self.target_lang = language
            logging.debug("target language %s supported" % language)
            self.emit('target-lang-changed', self.target_lang)
        else:
            lang = data.simplercode(language)
            if lang:
                self.set_target_lang(lang)
            else:
                self.target_lang = None
                logging.debug("target language %s not supported" % language)

    def _loads_safe(self, response):
        """Does the loading of the JSON response, but handles exceptions."""
        try:
            data = json.loads(response)
        except Exception, exc:
            logging.debug('JSON exception: %s' % (exc))
            return None
        return data

    def format_suggestions(self, id, response):
        """clean up open tran suggestion and use the same format as tmserver"""
        suggestions = self._loads_safe(response)
        if not suggestions:
            return []
        id = data.forceunicode(id)
        self.last_suggestions.extend(suggestions)  # we keep it for the terminology back-end
        results = []
        for suggestion in suggestions:
            #check for fuzzyness at the 'flag' member:
            for project in suggestion['projects']:
                if project['flags'] == 0:
                    break
            else:
                continue
            result = {}
            result['target'] = data.forceunicode(suggestion['text'])
            result['tmsource'] = suggestion['projects'][0]['name']
            result['source'] = data.forceunicode(suggestion['projects'][0]['orig_phrase'])
            #open-tran often gives too many results with many which can't really be
            #considered to be suitable for translation memory
            result['quality'] = self.comparer.similarity(id, result['source'], self.min_similarity)
            if result['quality'] >= self.min_similarity:
                results.append(result)
        results.sort(key=lambda match: match['quality'], reverse=True)
        results = results[:self.max_candidates]
        return results

########NEW FILE########
__FILENAME__ = set_enumerator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007-2009,2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
from bisect import bisect_left

from virtaal.support.sorted_set import SortedSet


# FIXME: Add docstrings!

class UnionSetEnumerator(gobject.GObject):
    __gtype_name__ = "UnionSetEnumerator"

    __gsignals__ = {
        "remove": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT)),
        "add":    (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT))
    }

    def __init__(self, *sets):
        gobject.GObject.__init__(self)

        if len(sets) > 0:
            self.sets = sets
            self.set = reduce(lambda big_set, set: big_set.union(set), sets[1:], sets[0])
        else:
            self.sets = [SortedSet([])]
            self.set = SortedSet([])

    #cursor = property(lambda self: self._current_element, _set_cursor)

    def __len__(self):
        return len(self.set.data)

    def __contains__(self, element):
        try:
            return element in self.set
        except IndexError:
            return False

    def _before_add(self, _src, _pos, element):
        if element not in self.set:
            self.set.add(element)
            cursor_pos = bisect_left(self.set.data, element)
            self.emit('add', self, cursor_pos, element)

    def _before_remove(self, _src, _pos, element):
        if element in self.set:
            self.set.remove(element)
            self.emit('remove', self, bisect_left(self.set.data, element), element)

    def remove(self, element):
        for set_ in self.sets:
            set_.remove(element)

########NEW FILE########
__FILENAME__ = simplegeneric
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
# This file was originally part of the PEAK project:
#   http://peak.telecommunity.com/DevCenter/FrontPage
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

__all__ = ["generic"]

from types import ClassType, InstanceType
classtypes = type, ClassType


def generic(func):
    """Create a simple generic function"""

    _sentinel = object()

    def _by_class(*args, **kw):
        cls = args[0].__class__
        for t in type(cls.__name__, (cls,object), {}).__mro__:
            f = _gbt(t, _sentinel)
            if f is not _sentinel:
                return f(*args, **kw)
        else:
            return func(*args, **kw)

    _by_type = {object: func, InstanceType: _by_class}
    _gbt = _by_type.get

    def when_type(t):
        """Decorator to add a method that will be called for type `t`"""
        if not isinstance(t, classtypes):
            raise TypeError(
                "%r is not a type or class" % (t,)
            )
        def decorate(f):
            if _by_type.setdefault(t,f) is not f:
                raise TypeError(
                    "%r already has method for type %r" % (func, t)
                )
            return f
        return decorate

    _by_object = {}
    _gbo = _by_object.get

    def when_object(o):
        """Decorator to add a method that will be called for object `o`"""
        def decorate(f):
            if _by_object.setdefault(id(o), (o,f))[1] is not f:
                raise TypeError(
                    "%r already has method for object %r" % (func, o)
                )
            return f
        return decorate

    def dispatch(*args, **kw):
        f = _gbo(id(args[0]), _sentinel)
        if f is _sentinel:
            for t in type(args[0]).__mro__:
                f = _gbt(t, _sentinel)
                if f is not _sentinel:
                    return f(*args, **kw)
            else:
                return func(*args, **kw)
        else:
            return f[1](*args, **kw)

    dispatch.__name__       = func.__name__
    dispatch.__dict__       = func.__dict__.copy()
    dispatch.__doc__        = func.__doc__
    dispatch.__module__     = func.__module__

    dispatch.when_type = when_type
    dispatch.when_object = when_object
    dispatch.default = func
    dispatch.has_object = lambda o: id(o) in _by_object
    dispatch.has_type   = lambda t: t in _by_type
    return dispatch

def test_suite():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags=doctest.ELLIPSIS|doctest.REPORT_ONLY_FIRST_FAILURE,
    )

########NEW FILE########
__FILENAME__ = sorted_set
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
# The file was taken from
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/230113
# and was written by Raymond Hettinger.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

""" altsets.py -- An alternate implementation of Sets.py

Implements set operations using sorted lists as the underlying data structure.

Advantages:

  - Space savings -- lists are much more compact than a dictionary
    based implementation.

  - Flexibility -- elements do not need to be hashable, only __cmp__
    is required.

  - Fast operations depending on the underlying data patterns.
    Non-overlapping sets get united, intersected, or differenced
    with only log(N) element comparisons.  Results are built using
    fast-slicing.

  - Algorithms are designed to minimize the number of compares
    which can be expensive.

  - Natural support for sets of sets.  No special accomodation needs to
    be made to use a set or dict as a set member, but users need to be
    careful to not mutate a member of a set since that may breaks its
    sort invariant.

Disadvantages:

  - Set construction uses list.sort() with potentially N log(N)
    comparisons.

  - Membership testing and element addition use log(N) comparisons.
    Element addition uses list.insert() with takes O(N) time.

ToDo:

   - Make the search routine adapt to the data; falling backing to
     a linear search when encountering random data.

"""

from bisect import bisect_left

import gobject


class SortedSet(gobject.GObject):
    __gtype_name__ = "SortedSet"

    __gsignals__ = {
        "removed":       (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT)),
        "added":         (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT)),
        "before-remove": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT)),
        "before-add":    (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT))
    }

    def __init__(self, iterable):
        gobject.GObject.__init__(self)

        data = list(iterable)
        data.sort()
        result = data[:1]
        for elem in data[1:]:
            if elem == result[-1]:
                continue
            result.append(elem)
        self.data = result

    def __repr__(self):
        return 'SortedSet(' + repr(self.data) + ')'

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, elem):
        data = self.data
        i = bisect_left(self.data, elem, 0)
        return i<len(data) and data[i] == elem

    def add(self, elem):
        if elem not in self:
            i = bisect_left(self.data, elem)
            self.emit('before-add', i, elem)
            self.data.insert(i, elem)
            self.emit('added', i, elem)

    def remove(self, elem):
        data = self.data
        i = bisect_left(self.data, elem, 0)
        if i<len(data) and data[i] == elem:
            elem = data[i]
            self.emit('before-remove', i, elem)
            del data[i]
            self.emit('removed', i, elem)

    def _getotherdata(other):
        if not isinstance(other, SortedSet):
            other = SortedSet(other)
        return other.data
    _getotherdata = staticmethod(_getotherdata)

    def __cmp__(self, other, cmp=cmp):
        return cmp(self.data, SortedSet._getotherdata(other))

    def union(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = SortedSet._getotherdata(other)
        result = SortedSet([])
        append = result.data.append
        extend = result.data.extend
        try:
            while 1:
                if x[i] == y[j]:
                    append(x[i])
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    cut = find(y, x[i], j)
                    extend(y[j:cut])
                    j = cut
                else:
                    cut = find(x, y[j], i)
                    extend(x[i:cut])
                    i = cut
        except IndexError:
            extend(x[i:])
            extend(y[j:])
        return result

    def intersection(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = SortedSet._getotherdata(other)
        result = SortedSet([])
        append = result.data.append
        try:
            while 1:
                if x[i] == y[j]:
                    append(x[i])
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    j = find(y, x[i], j)
                else:
                    i = find(x, y[j], i)
        except IndexError:
            pass
        return result

    def difference(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = SortedSet._getotherdata(other)
        result = SortedSet([])
        extend = result.data.extend
        try:
            while 1:
                if x[i] == y[j]:
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    j = find(y, x[i], j)
                else:
                    cut = find(x, y[j], i)
                    extend(x[i:cut])
                    i = cut
        except IndexError:
            extend(x[i:])
        return result

    def symmetric_difference(self, other, find=bisect_left):
        i = j = 0
        x = self.data
        y = SortedSet._getotherdata(other)
        result = SortedSet([])
        extend = result.data.extend
        try:
            while 1:
                if x[i] == y[j]:
                    i += 1
                    j += 1
                elif x[i] > y[j]:
                    cut = find(y, x[i], j)
                    extend(y[j:cut])
                    j = cut
                else:
                    cut = find(x, y[j], i)
                    extend(x[i:cut])
                    i = cut
        except IndexError:
            extend(x[i:])
            extend(y[j:])
        return result

########NEW FILE########
__FILENAME__ = thread
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.


import gtk
import threading
import Queue


def run_in_thread(widget, target, args):
    # Idea from tortoisehg's gtklib.py
    q = Queue.Queue()
    def func(*kwargs):
        q.put(target(*kwargs))

    thread = threading.Thread(target=func, args=args)
    thread.start()

    # we make the given widget insensitive to avoid interaction that we can't
    # handle concurrently
    widget.set_sensitive(False)
    import time
    while thread.isAlive():
        # let gtk process events while target is still running
        gtk.main_iteration(block=False)
        # Since we are not blocking, we're spinning, which isn't nice. We could
        # set block=True, but then the window might stay insensitive when the
        # thread finished, and only exit this loop when it gets another event
        # (like a mouse move). So we sleep a bit to avoid excessive CPU use.
        time.sleep(0.03)

    widget.set_sensitive(True)
    if q.qsize():
        return q.get(0)

########NEW FILE########
__FILENAME__ = tmclient
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

# These two json modules are API compatible
try:
    import simplejson as json #should be a bit faster; needed for Python < 2.6
except ImportError:
    import json #available since Python 2.6

import pycurl

from virtaal.support.httpclient import HTTPClient, RESTRequest


class TMClient(HTTPClient):
    """CRUD operations for TM units and stores"""

    def __init__(self, base_url):
        HTTPClient.__init__(self)
        self.base_url = base_url

    def translate_unit(self, unit_source, source_lang, target_lang, callback=None, params=None):
        """suggest translations from TM"""
        request = RESTRequest(
                self.base_url + "/%s/%s/unit" % (source_lang, target_lang),
                unit_source, "GET",
                user_agent=self.user_agent,
                params=params,
        )
        # TM requests have to finish quickly to be useful. This also helps to
        # avoid buildup in case of network failure
        request.curl.setopt(pycurl.TIMEOUT, 30)
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def add_unit(self, unit, source_lang, target_lang, callback=None):
        request = RESTRequest(
                self.base_url + "/%s/%s/unit" % (source_lang, target_lang),
                unit['source'], "PUT", json.dumps(unit),
                user_agent=self.user_agent)
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def update_unit(self, unit, source_lang, target_lang, callback=None):
        request = RESTRequest(
                self.base_url + "/%s/%s/unit" % (source_lang, target_lang),
                unit['source'], "POST", json.dumps(unit),
                user_agent=self.user_agent)
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def forget_unit(self, unit_source, source_lang, target_lang, callback=None):
        request = RESTRequest(
                self.base_url + "/%s/%s/unit" % (source_lang, target_lang, self.user_agent),
                unit_source, "DELETE",
                user_agent=self.user_agent)
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def get_store_stats(self, store, callback=None):
        request = RESTRequest(
                self.base_url + "/store",
                store.filename, "GET",
                user_agent=self.user_agent)
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def upload_store(self, store, source_lang, target_lang, callback=None):
        data = str(store)
        request = RESTRequest(
                self.base_url + "/%s/%s/store" % (source_lang, target_lang),
                store.filename, "PUT", data,
                user_agent=self.user_agent)
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def add_store(self, filename, store, source_lang, target_lang, callback=None):
        request = RESTRequest(
                self.base_url + "/%s/%s/store" % (source_lang, target_lang),
                filename, "POST", json.dumps(store))
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

    def forget_store(self, store, callback=None):
        request = RESTRequest(
                self.base_url + "/store",
                store.filename, "DELETE")
        self.add(request)
        if callback:
            request.connect(
                "http-success",
                lambda widget, response: callback(widget, widget.id, json.loads(response))
            )

########NEW FILE########
__FILENAME__ = tutorial
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2013 Zuza Software Foundation
# Copyright 2012 Leandro Regueiro Iglesias
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os.path
from tempfile import mkdtemp

from translate.storage import factory


def create_localized_tutorial():
    """Save on disk a tutorial POT file with comments using current locale."""

    # All the entries in the tutorial.
    #
    # It is a tuple of entries, in which entry is in the form of a tuple with a
    # comment for the translator, a string (or list of source strings) and an
    # optional string context (blank string if not provided).
    tutorial_entries = (
    # Translators: Don't translate the "Welcome" word.
    (_(u"Welcome to the Virtaal tutorial. You can do the first translation by "
       u"typing just the translation for \"Welcome\". Then press Enter."),
     u"Welcome",
     u""),

    (_(u"Translate this slightly longer message. If a spell checker is "
       u"available, spelling mistakes are indicated similarly to word "
       u"processors. Make sure the correct language is selected in the bottom "
       u"right of the window."),
     u"With this file you can learn about translation using Virtaal",
     u""),

    (_(u"This tutorial will show you some of the things you might want to pay "
       u"attention to while translating software programs. It will help you "
       u"to avoid some problems and produce translations of a higher "
       u"quality."),
     u"Quality is important",
     u""),

    (_(u"Some of the advice will only be relevant to some languages. For "
       u"example, if your language does not use the Latin alphabet, some of "
       u"the advice might not be relevant to translation in your language. "
       u"For many languages there are established translation rules."),
     u"Languages are different",
     u""),

    (_(u"The correct use of capital letters are important in many languages. "
       u"Translate this message with careful attention to write \"Virtaal\" "
       u"with a capital letter."),
     u"The product we use is called Virtaal",
     u""),

    (_(u"In this message the English uses a capital letter for almost every "
       u"word. Almost no other language uses this style. Unless your language "
       u"definitely needs to follow the English style (also called Title "
       u"Case), translate this by following the normal capitalisation rules "
       u"for your language. If your language does not use capital letters, "
       u"simply translate it normally."),
     u"Download the File Now",
     u""),

    (_(u"If you translated the previous message you should see a window with "
       u"that translation and a percentage indicating how similar the source "
       u"strings (English) are. It is Virtaal's translation memory at work. "
       u"Press Control+1 to copy the suggested translation to the current "
       u"translation. Remember to always review suggestions before you use "
       u"them."),
     u"Download the files now",
     u""),

    (_(u"This is a simple message that starts with a capital letter in "
       u"English. If your language uses capital letters, you almost "
       u"definitely want to start your translation with a capital letter as "
       u"well."),
     u"Time",
     u""),

    (_(u"This is a simple message that starts with a lower case letter in "
       u"English. If your language uses capital letters, you almost "
       u"definitely want to start your translation with a lower case letter "
       u"as well."),
     u"later",
     u""),

    (_(u"This message is a question. Make sure that you use the correct "
       u"question mark in your translation as well."),
     u"What is your name?",
     u""),

    (_(u"This message is a label as part of a form. Note how it ends with a "
       u"colon (:)."),
     u"Name:",
     u""),

    (_(u"If the source will remain mostly or completely unchanged it is "
       u"convenient to copy the entire source string with Alt+Down. Here is "
       u"almost nothing to translate, so just press Alt+Down and make "
       u"corrections if necessary."),
     u"<b><a href=\"http://virtaal.org/\">Virtaal</a></b>",
     u""),

    (_(u"Placeables are special parts of the text, like the © symbol, that "
       u"can be automatically highlighted and easily inserted into the "
       u"translation. Select the © with Alt+Right and transfer it to the "
       u"target with Alt+Down."),
     u"© Virtaal Team",
     u""),

    (_(u"Recognised placeables include special symbols, numbers, variable "
       u"place holders, acronyms and many more. Move to each one with "
       u"Alt+Right and transfer it down with Alt+Down."),
     u"© 2009 contributors",
     u""),

    (_(u"This message ends with ... to indicate that clicking on this text "
       u"will cause a dialogue to appear instead of just performing an "
       u"action. Be sure to end your message with ... as well."),
     u"Save As...",
     u""),

    (_(u"This message ends with a special character that looks like three "
       u"dots. Select the special character with Alt+Right and copy it to "
       u"your translation with Alt+Down. Don't just type three dot "
       u"characters."),
     u"Save As…",
     u""),

    (_(u"This message has two sentences. Translate them and make sure you "
       u"start each with a capital letter if your language uses them, and end "
       u"each sentence properly."),
     u"Always try your best. Many people are available to learn from.",
     u""),

    (_(u"This message marks the word \"now\" as important with bold tags. "
       u"These tags can be transferred from the source with Alt+Right and "
       u"Alt+Down. Leave the <b> and </b> in the translation around the part "
       u"that corresponds to \"now\". Read more about XML markup here: "
       u"http://en.wikipedia.org/wiki/XML"),
     u"Restart the program <b>now</b>",
     u""),

    (_(u"This message is very similar to the previous message. Use the "
       u"suggestion of the previous translation with Ctrl+1. Note how the "
       u"only difference is that this one ends with a full stop after the "
       u"last tag."),
     u"Restart the program <b>now</b>.",
     u""),

    (_(u"In this message \"%d\" is a placeholder (variable) that represents a "
       u"number. Make sure your translation contains \"%d\" somewhere. In "
       u"this case it refers a number of files. When this message is used the "
       u"\"%d\" will be replaced with a number e.g. 'Number of files copied: "
       u"5'.  Note that \"%d\" does not refer to a percentage."),
     u"Number of files copied: %d",
     u""),

    (_(u"In this message, \"%d\" refers again to the number of files, but "
       u"note how the \"(s)\" is used to show that we don't know how many it "
       u"will be. This is often hard to translate well. If you encounter this "
       u"in software translation, you might want to hear from developers if "
       u"this can be avoided. Read more about this and decide how to do it in "
       u"your language: http://docs.translatehouse.org/projects/"
       u"localization-guide/en/latest/guide/translation/plurals.html"),
     u"%d file(s) will be downloaded",
     u""),

    # Entry with plurals.
    (_(u"In this message the proper way of translating plurals are seen. You "
       u"need to enter between 1 and 6 different versions of the translation "
       u"to ensure the correct grammar in your language. Read more about this "
       u"here: http://docs.translatehouse.org/projects/localization-guide/en/"
       u"latest/guide/translation/plurals.html"),
     [
        u"%d file will be downloaded",
        u"%d files will be downloaded",
     ],
     u""),

    (_(u"In this message, \"%s\" is a placeholder (variable) that represents "
       u"a file name. Make sure your translation contains %s somewhere. When "
       u"this message is used, the %s will be replaced with a file name e.g. "
       u"'The file will be saved as example.odt'.  Note that \"%s\" does not "
       u"refer to a percentage."),
     u"The file will be saved as %s",
     u""),

    (_(u"In this message the variable is surrounded by double quotes. Make "
       u"sure your translation contains the variable %s and surround it "
       u"similarly with quotes in the way required by your language. If your "
       u"language uses the same quotes as English, type it exactly as shown "
       u"for the English. If your language uses different characters you can "
       u"just type them around the variable."),
     u"The file \"%s\" was not saved",
     u""),

    (_(u"In this message, \"%(name)s\" is a placeholder (variable). Note that "
       u"the 's' is part of the variable, and the whole variable from '%' to "
       u"the 's' should appear unchanged somewhere in your translation. These "
       u"type of variables give you an idea of what they will contain. In "
       u"this case, it will contain a name."),
     u"Welcome back, %(name)s",
     u""),

    (_(u"In this message the user of the software is asked to do something. "
       u"Make sure you translate it by being as polite or respectful as is "
       u"necessary for your culture."),
     u"Please enter your password here",
     u""),

    (_(u"In this message there is reference to \"Linux\" (a product name). "
       u"Many languages will not translate it, but your language might use a "
       u"transliteration if you don't use the Latin script for your "
       u"language."),
     u"This software runs on Linux",
     u""),

    (_(u"This message contains the URL (web address) of the project website. "
       u"It must be transferred as a placeable or typed over exactly."),
     u"Visit the project website at http://virtaal.org/",
     u""),

    (_(u"This message refers to a website with more information. Sometimes "
       u"you might be allowed or encouraged to change the URL (web address) "
       u"to a website in your language. In this case, replace the \"en\" at "
       u"the start of the address to your language code so that the address "
       u"points to the corresponding article in your language about XML."),
     u"For more information about XML, visit http://en.wikipedia.org/wiki/XML",
     u""),

    # Entry with context message.
    (_(u"This translation contains an ambiguous word - it has two possible "
       u"meanings. Make sure you can see the context information showing that "
       u"this is a verb (an action as in \"click here to view it\")."),
     u"View",
     u"verb"),

    # Entry with context message.
    (_(u"This translation contains an ambiguous word - it has two possible "
       u"meanings. Make sure you can see the context information showing that "
       u"this is a noun (a thing as in \"click to change the view to full "
       u"screen\"). If Virtaal gives your previous translation as a "
       u"suggestion, take care to only use it if it is definitely appropriate "
       u"in this case as well."),
     u"View",
     u"noun"),

    (_(u"An accelerator key is a key on your keyboard that you can press to "
       u"to quickly access a menu or function. It is also called a hot key, "
       u"access key or mnemonic. In program interfaces they are shown as an "
       u"underlined letter in the text label. In the translatable text they "
       u"are marked using some character like the underscore here, but other "
       u"characters are used for this as well. In this case the the "
       u"accelerator key is \"f\" since the underscore is before this letter "
       u"and it means that this accelerator could be triggered by pressing "
       u"Alt+F."),
     u"_File",
     u""),

    (_(u"In this entry you can see other kind of accelerator."),
     u"&File",
     u""),

    (_(u"And another kind of accelerator."),
     u"~File",
     u""),

    # Entry with context message.
    (_(u"Virtaal is able to provide suggestions from several terminology "
       u"glossaries and provides easy shortcuts to allow paste them in the "
       u"translation field. Right now Virtaal has only one empty terminology "
       u"glossary, but you can start filling it. In order to do that select "
       u"the original text, press Ctrl+T, provide a translation for your "
       u"language, and save."),
     u"Filter",
     u"verb"),

    # Entry with context message.
    (_(u"In the previous entry you have created one terminology entry for the "
       u"the \"filter\" verb. Now do the same for \"filter\" noun."),
     u"Filter",
     u"noun"),

    (_(u"If you have created any terminology in the previous entries you may "
       u"may now see some of the words with a green background (or other "
       u"color depending on your theme). This means that Virtaal has "
       u"terminology suggestions for that word. Use Alt+Right to select the "
       u"highlighted word, and then press Alt+Down. If only one suggestions "
       u"is provided Alt+Down just copies the suggestion to the translation "
       u"field. But if several suggestions are available Alt+Down shows a "
       u"suggestion list which you can navigate using Down and Up keys. Once "
       u"you have selected the desired suggestion press Enter to copy it to "
       u"the translation field."),
     u"Filter the list by date using the \"filter by date\" filter.",
     u""),

    (_(u"This message has two lines. Make sure that your translation also "
       u"contains two lines. You can separate lines with Shift+Enter or "
       u"copying new-line placeables (displayed as ¶)."),
     (u"A camera has been connected to your computer.\nNo photos were found "
      u"on the camera."),
     u""),

    (_(u"This message contains tab characters to separate some headings. Make "
       u"sure you separate your translations in the same way."),
     u"Heading 1\tHeading 2\tHeading 3",
     u""),

    (_(u"This message contains a large number that is formatted according to "
       u"to American convention. Translate this but be sure to format the "
       u"number according to the convention for your language. You might need "
       u"to change the comma (,) and full stop (.) to other characters, and "
       u"you might need to use a different number system. Make sure that you "
       u"understand the American formatting: the number is bigger than one "
       u"thousand."),
     u"It will take 1,234.56 hours to do",
     u""),

    (_(u"This message refers to miles. If the programmers encourage it, you "
       u"might want to change this to kilometres in your translation, if "
       u"kilometres are more commonly used in your language. Note that 1 mile "
       u"is about 1.6 kilometres. Note that automated tests for \"numbers\" "
       u"will complain if the number is changed, but in this case it is safe "
       u"to do."),
     u"The road is 10 miles long",
     u""),

    (_(u"This message contains a link that the user will be able to click on "
       u"on to visit the help page. Make sure you maintain the information "
       u"between the angle brackets (<...>) correctly. The double quotes (\") "
       u"should never be changed in tags, even if your language uses a "
       u"different type of quotation marks."),
     (u"Feel free to visit our <a "
      u"href=\"http://docs.translatehouse.org/projects/virtaal/en/latest/\">"
      u"help page</a>"),
     u""),

    (_(u"This message contains a similar link, but the programmers decided to "
       u"to rather insert the tags with variables so that translators can't "
       u"change them. Make sure you position the two variables (%s) so that "
       u"they correspond to the opening and closing tag of the previous "
       u"translation."),
     u"Feel free to visit our %shelp page%s",
     u""),

    (_(u"This message contains the <b> and </b> tags to emphasize a word, "
       u"while everything is inside <p> and </p> tags. Make sure your whole "
       u"translation is inside <p> and </p> tags."),
     u"<p>Restart the program <b>now</b></p>",
     u""),

    (_(u"This message contains a similar link that is contained within <span> "
       u"and </span>. Make sure you maintain all the tags (<...>) correctly, "
       u"and that the link is contained completely inside the <span> and "
       u"</span> tags in your translation. Make sure that the text inside the "
       u"\"a\" tags correspond to \"help page\" and that your translation "
       u"corresponding to the second sentence is contained in the <span> "
       u"tags. Note how the full stop is still inside the </span> tag."),
     (u"The software has many features. <span class=\"info\">Feel free to "
      u"to visit our <a "
      u"href=\"http://docs.translatehouse.org/projects/virtaal/en/latest/\">"
      u"help page</a>.</span>"),
     u""),
    )

    # Tutorial filename at a temporary file in a random temporary directory.
    filename = os.path.join(mkdtemp("", "tmp_virtaal_"), "virtaal_tutorial.pot")

    tutorial_file = factory.getobject(filename)

    for comment, source, context in tutorial_entries:
        # The next creates an unit with the provided source (even if plural)
        # and returns it. In case of plural, source should be a list of strings
        # instead of a string.
        unit = tutorial_file.addsourceunit(source)

        if isinstance(source, list):
            # Maybe unnecessary since when Virtaal opens the file and doesn't
            # crash, even if it has only a msgstr for plural entries, and it
            # shows the appropiate number of translation fields (for the target
            # language).
            unit.settarget([u"", u""])

        unit.addnote(comment, "developer")
        unit.setcontext(context)

    tutorial_file.save()

    # Return the filename to enable opening the file.
    return filename

########NEW FILE########
__FILENAME__ = test_maincontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from test_scaffolding import TestScaffolding


class TestMainController(TestScaffolding):
    def test_get_store(self):
        self.store_controller.open_file(self.testfile[1])
        assert self.main_controller.get_store() == self.store_controller.store
        assert self.main_controller.get_store_filename() == self.store_controller.store.get_filename()

########NEW FILE########
__FILENAME__ = test_modecontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from test_scaffolding import TestScaffolding


class TestModeController(TestScaffolding):
    def test_get_mode_by_display_name(self):
        default_mode_display_name = self.mode_controller.modenames['Default']
        default_mode = self.mode_controller.get_mode_by_display_name(default_mode_display_name)
        assert default_mode == self.mode_controller.modes[self.mode_controller.default_mode_name]

    def test_select_mode(self):
        self.store_controller.open_file(self.testfile[1])
        for name, mode in self.mode_controller.modes.items():
            self.mode_controller.select_mode(mode)
            assert self.mode_controller.current_mode is mode

    def test_select_mode_by_name(self):
        self.store_controller.open_file(self.testfile[1])
        for name, mode in self.mode_controller.modes.items():
            self.mode_controller.select_mode_by_name(name)
            assert self.mode_controller.current_mode is mode

########NEW FILE########
__FILENAME__ = test_scaffolding
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os
import tempfile
from translate.storage import factory

from virtaal.controllers.maincontroller import MainController
from virtaal.controllers.storecontroller import StoreController
from virtaal.controllers.unitcontroller import UnitController
from virtaal.controllers.undocontroller import UndoController
from virtaal.controllers.modecontroller import ModeController
from virtaal.controllers.checkscontroller import ChecksController
from virtaal.controllers.langcontroller import LanguageController


class TestScaffolding(object):
    def setup_class(self):
        self.main_controller = MainController()
        self.store_controller = StoreController(self.main_controller)
        self.unit_controller = UnitController(self.store_controller)
        self.checks_controller = ChecksController(self.main_controller)

        # Load additional built-in modules
        self.undo_controller = UndoController(self.main_controller)
        self.mode_controller = ModeController(self.main_controller)
        self.lang_controller = LanguageController(self.main_controller)

        po_contents = """# Afrikaans (af) localisation of Virtaal.
# Copyright (C) 2008 Zuza Software Foundation (Translate.org.za)
# This file is distributed under the same license as the Virtaal package.
# Dwayne Bailey <dwayne@translate.org.za>, 2008
# F Wolff <friedel@translate.org.za>, 2008
msgid ""
msgstr ""
"Project-Id-Version: Virtaal 0.1\\n"
"Report-Msgid-Bugs-To: translate-devel@lists.sourceforge.net\\n"
"POT-Creation-Date: 2008-10-14 15:33+0200\\n"
"PO-Revision-Date: 2008-10-14 15:46+0200\\n"
"Last-Translator: F Wolff <friedel@translate.org.za>\\n"
"Language-Team: translate-discuss-af@lists.sourceforge.net\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
"X-Generator: Virtaal 0.2\\n"

#: ../bin/virtaal:41
msgid "You must specify a directory or a translation file for --terminology"
msgstr "U moet 'n gids of vertaallêer spesifiseer vir --terminology"

#: ../bin/virtaal:46
#, c-format
msgid "%prog [options] [translation_file]"
msgstr "%prog [opsies] [vertaallêer]"

#, fuzzy
#: ../bin/virtaal:49
msgid "PROFILE"
msgstr "PROFIEL"
"""
        self.testfile = tempfile.mkstemp(suffix='.po', prefix='test_storemodel')
        os.write(self.testfile[0], po_contents)
        os.close(self.testfile[0])
        self.trans_store = factory.getobject(self.testfile[1])

    def teardown_class(self):
        os.unlink(self.testfile[1])

########NEW FILE########
__FILENAME__ = test_storecontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from test_scaffolding import TestScaffolding


class TestStoreController(TestScaffolding):
    def test_open_file(self):
        self.store_controller.open_file(self.testfile[1])
        assert self.store_controller.store.get_filename() == self.testfile[1]

########NEW FILE########
__FILENAME__ = test_storecursor
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from test_scaffolding import TestScaffolding


class TestCursor(TestScaffolding):
    def test_move(self):
        self.store_controller.open_file(self.testfile[1])
        cursor = self.store_controller.cursor
        oldpos = cursor.pos
        cursor.move(1)
        assert cursor.pos == oldpos + 1
        cursor.move(-2)
        assert cursor.pos == len(cursor.indices) - 1

    def test_indices(self):
        cursor = self.store_controller.cursor
        cursor.pos = 0
        cursor.indices = [1, 2]
        assert cursor.pos == 0
        cursor.move(2)
        assert cursor.pos == 0

########NEW FILE########
__FILENAME__ = test_storemodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from virtaal.models.storemodel import StoreModel

from test_scaffolding import TestScaffolding


class TestStoreModel(TestScaffolding):
    def test_load(self):
        self.model = StoreModel(self.testfile[1], None) # We can pass "None" as the controller, because it does not have an effect on this test
        self.model.load_file(self.testfile[1])
        assert len(self.model) <= len(self.trans_store.units)
        assert self.model.get_filename() == self.testfile[1]

########NEW FILE########
__FILENAME__ = test_unitcontroller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from test_scaffolding import TestScaffolding


class TestUnitController(TestScaffolding):



    def test_get_target(self):
        # The unit indexes below differ by 1, because the StoreModel class (and thus the rest of Virtaal)
        # ignores PO headers (and other untranslatable units), whereas the Toolkit's stores do not.

        test_unit = self.trans_store.getunits()[1]
        view = self.unit_controller.load_unit(test_unit)

        assert unicode(self.unit_controller.view.targets[0].elem) == self.trans_store.getunits()[1].target

    def test_set_target(self):
        test_unit = self.trans_store.getunits()[1]
        view = self.unit_controller.load_unit(test_unit)

        self.unit_controller.set_unit_target(0, [u'Test',])
        assert unicode(self.unit_controller.view.targets[0].elem) == u'Test'

########NEW FILE########
__FILENAME__ = tips
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""These are some tips that are displayed to the user."""

from gettext import gettext as _


tips = [
    _("At the end of a translation, simply press <Enter> to continue with the next one."),
    _("To copy the original string into the target field, simply press <Alt+Down>."),
    #_("When editing a fuzzy translation, the fuzzy marker will automatically be removed."),
    # l10n: Refer to the translation of "Fuzzy" to find the appropriate shortcut key to recommend
    _("To mark the current translation as fuzzy, simply press <Alt+U>."),
    _("To mark the current translation as incomplete, simply press <Ctrl+Shift+Enter>."),
    _("To mark the current translation as complete, simply press <Ctrl+Enter>."),
    _("Use Ctrl+Up or Ctrl+Down to move between translations."),
    _("Use Ctrl+PgUp or Ctrl+PgDown to move in large steps between translations."),
]

########NEW FILE########
__FILENAME__ = baseview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from gtk import Builder

from virtaal.common import pan_app


#cache builders so that we don't parse files repeatedly
_builders = {}


class BaseView(object):
    """Interface for views."""

    def __init__(self):
        raise NotImplementedError('This interface cannot be instantiated.')

    @classmethod
    def load_builder_file(cls, path_parts, root=None, domain=''):
        _id = "/".join(path_parts)
        if _id in _builders:
            return _builders[_id]
        buildername = pan_app.get_abs_data_filename(path_parts)
        builder = Builder()
        builder.add_from_file(buildername)
        builder.set_translation_domain(domain)
        _builders[_id] = builder
        return builder

    def show(self):
        raise NotImplementedError('This method needs to be implemented by all sub-classes.')

########NEW FILE########
__FILENAME__ = checksprojview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from virtaal.views.widgets.popupmenubutton import PopupMenuButton

from baseview import BaseView


class ChecksProjectView(BaseView):
    """Manages project type selection and other quality checks UI elements."""

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        self.current_project = None
        self._checker_menu_items = {}

        self._create_project_button()

    def _create_project_button(self):
        self.btn_proj = PopupMenuButton(label=_('Project Type'))
        menu = gtk.Menu()
        for checkercode in self.controller.checker_info:
            checkername = self.controller._checker_code_to_name[checkercode]
            mitem = gtk.MenuItem(checkername)
            mitem.show()
            mitem.connect('activate', self._on_menu_item_activate)
            menu.append(mitem)
            self._checker_menu_items[checkername] = mitem
        self.btn_proj.set_menu(menu)


    # METHODS #
    def show(self):
        statusbar = self.controller.main_controller.view.status_bar
        for child in statusbar.get_children():
            if child is self.btn_proj:
                return
        statusbar.pack_start(self.btn_proj, expand=False)
        statusbar.show_all()

    def set_checker_name(self, cname):
        # l10n: The label indicating the checker style (GNOME/KDE/whatever)
        self.btn_proj.set_label(_('Checks: %(checker_name)s') % {'checker_name': cname})


    # EVENT HANDLER #
    def _on_menu_item_activate(self, menuitem):
        self.controller.set_checker_by_name(menuitem.child.get_label())

########NEW FILE########
__FILENAME__ = checksunitview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import locale

import gtk
import pango
from translate.lang import factory as lang_factory

from virtaal.common.pan_app import ui_language
from virtaal.views.widgets.popupwidgetbutton import PopupWidgetButton, POS_SE_NE

from baseview import BaseView


class ChecksUnitView(BaseView):
    """The unit specific view for quality checks."""

    COL_CHECKNAME, COL_DESC = range(2)

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        main_controller = controller.main_controller
        main_window = main_controller.view.main_window

        self.popup_content = self._create_popup_content()
        self._create_checks_button(self.popup_content, main_window)
        self._create_menu_item()
        main_controller.store_controller.connect('store-closed', self._on_store_closed)
        main_controller.store_controller.connect('store-loaded', self._on_store_loaded)

        self._prev_failures = None
        self._listsep = lang_factory.getlanguage(ui_language).listseperator

    def _create_checks_button(self, widget, main_window):
        self.lbl_btnchecks = gtk.Label()
        self.lbl_btnchecks.show()
        self.lbl_btnchecks.set_ellipsize(pango.ELLIPSIZE_END)
        self.btn_checks = PopupWidgetButton(widget, label=None, popup_pos=POS_SE_NE, main_window=main_window, sticky=True)
        self.btn_checks.set_property('relief', gtk.RELIEF_NONE)
        self.btn_checks.set_update_popup_geometry_func(self.update_geometry)
        self.btn_checks.add(self.lbl_btnchecks)

    def _create_menu_item(self):
        mainview = self.controller.main_controller.view
        self.mnu_checks = mainview.gui.get_object('mnu_checks')
        self.mnu_checks.connect('activate', self._on_activated)

    def _create_popup_content(self):
        vb = gtk.VBox()
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame.add(vb)

        self.lbl_empty = gtk.Label('<i>' + _('No issues') + '</i>')
        self.lbl_empty.set_use_markup(True)
        self.lbl_empty.hide()
        vb.pack_start(self.lbl_empty)

        self.lst_checks = gtk.ListStore(str, str)
        self.tvw_checks = gtk.TreeView()
        name_column = gtk.TreeViewColumn(_('Quality Check'), gtk.CellRendererText(), text=self.COL_CHECKNAME)
        name_column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.tvw_checks.append_column(name_column)

        description_renderer = gtk.CellRendererText()
        #description_renderer.set_property('wrap-mode', pango.WRAP_WORD_CHAR)
        description_column = gtk.TreeViewColumn(_('Description'), description_renderer, text=self.COL_DESC)
        description_column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.tvw_checks.append_column(description_column)
        self.tvw_checks.set_model(self.lst_checks)
        self.tvw_checks.get_selection().set_mode(gtk.SELECTION_NONE)

        vb.pack_start(self.tvw_checks)

        return frame


    # METHODS #
    def show(self):
        parent = self.controller.main_controller.unit_controller.view._widgets['vbox_right']
        parent.pack_start(self.btn_checks, expand=False, fill=True)
        self.btn_checks.show()

    def hide(self):
        if self.btn_checks.get_active():
            self.btn_checks.clicked()

    def update(self, failures):
        # We don't want to show "untranslated"
        failures.pop('untranslated', None)
        if failures == self._prev_failures:
            return
        self._prev_failures = failures
        if not failures:
            # We want an empty button, but this causes a bug where subsequent
            # updates don't show, so we set it to a non-breaking space
            self.lbl_btnchecks.set_text(u"\u202a")
            self._show_empty_label()
            self.btn_checks.set_tooltip_text(u"")
            return

        self.lst_checks.clear()
        nice_name = self.controller.get_check_name
        sorted_failures = sorted(failures.iteritems(), key=lambda x: nice_name(x[0]), cmp=locale.strcoll)
        names = []
        for testname, desc in sorted_failures:
            testname = nice_name(testname)
            self.lst_checks.append([testname, desc])
            names.append(testname)

        name_str = self._listsep.join(names)
        self.btn_checks.set_tooltip_text(name_str)
        self.lbl_btnchecks.set_text(name_str)
        self._show_treeview()

    def _show_empty_label(self):
        self.tvw_checks.hide()
        self.lbl_empty.show()

    def _show_treeview(self):
        self.lbl_empty.hide()
        self.tvw_checks.show_all()

    def update_geometry(self, popup, popup_alloc, btn_alloc, btn_window_xy, geom):
        x, y, width, height = geom

        textbox = self.controller.main_controller.unit_controller.view.sources[0]
        alloc = textbox.get_allocation()

        if width > alloc.width * 1.3:
            return x, y, int(alloc.width * 1.3), height
        return geom


    # EVENT HANDLERS #
    def _on_activated(self, menu_iitem):
        self.btn_checks.clicked()

    def _on_store_closed(self, store_controller):
        self.mnu_checks.set_sensitive(False)
        self.hide()

    def _on_store_loaded(self, store_controller):
        self.mnu_checks.set_sensitive(True)

########NEW FILE########
__FILENAME__ = langview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import os
import gobject
import gtk
import gtk.gdk
import logging

from virtaal.common import GObjectWrapper
from virtaal.models.langmodel import LanguageModel

from baseview import BaseView
from widgets.popupmenubutton import PopupMenuButton


class LanguageView(BaseView):
    """
    Manages the language selection on the GUI and communicates with its associated
    C{LanguageController}.
    """

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        self._init_gui()

    def _create_dialogs(self):
        from widgets.langselectdialog import LanguageSelectDialog
        from widgets.langadddialog import LanguageAddDialog
        langs = [LanguageModel(lc) for lc in LanguageModel.languages]
        langs.sort(key=lambda x: x.name)
        self.select_dialog = LanguageSelectDialog(langs, parent=self.controller.main_controller.view.main_window)
        self.select_dialog.btn_add.connect('clicked', self._on_addlang_clicked)

        self.add_dialog = LanguageAddDialog(parent=self.select_dialog.dialog)

    def _init_gui(self):
        self.menu = None
        self.popupbutton = PopupMenuButton()
        self.popupbutton.connect('toggled', self._on_button_toggled)

        self.controller.main_controller.view.main_window.connect(
            'style-set', self._on_style_set
        )
        if self.controller.recent_pairs:
            self.popupbutton.text = self._get_display_string(*self.controller.recent_pairs[0])

    def _init_menu(self):
        self.menu = gtk.Menu()
        self.popupbutton.set_menu(self.menu)

        self.recent_items = []
        for i in range(self.controller.NUM_RECENT):
            item = gtk.MenuItem('')
            item.connect('activate', self._on_pairitem_activated, i)
            self.recent_items.append(item)
        seperator = gtk.SeparatorMenuItem()
        self.other_item = gtk.MenuItem(_('_New Language Pair...'))
        self.other_item.connect('activate', self._on_other_activated)
        [self.menu.append(item) for item in (seperator, self.other_item)]
        self.update_recent_pairs()

        self.controller.main_controller.view.main_window.connect(
            'style-set', self._on_style_set
        )


    # METHODS #
    def _get_display_string(self, srclang, tgtlang):
        if self.popupbutton.get_direction() == gtk.TEXT_DIR_RTL:
            # We need to make sure we get the direction correct if the
            # language names are untranslated. The right-to-left embedding
            # (RLE) characters ensure that untranslated language names will
            # still diplay with the correct direction as they are present
            # in the interface.
            pairlabel = u'\u202b%s ← \u202b%s' % (srclang.name, tgtlang.name)
        else:
            pairlabel = u'%s → %s' % (srclang.name, tgtlang.name)
        # While it seems that the arrows are not well supported on Windows
        # systems, we fall back to using the French quotes. It automatically
        # does the right thing for RTL.
        if os.name == 'nt':
            pairlabel = u'%s » %s' % (srclang.name, tgtlang.name)
        return pairlabel

    def notify_same_langs(self):
        def notify():
            for s in [gtk.STATE_ACTIVE, gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_SELECTED]:
                self.popupbutton.child.modify_fg(s, gtk.gdk.color_parse('#f66'))
        gobject.idle_add(notify)

    def notify_diff_langs(self):
        def notify():
            if hasattr(self, 'popup_default_fg'):
                fgcol = self.popup_default_fg
            else:
                fgcol = gtk.widget_get_default_style().fg
            for s in [gtk.STATE_ACTIVE, gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_SELECTED]:
                self.popupbutton.child.modify_fg(s, fgcol[s])
        gobject.idle_add(notify)

    def show(self):
        """Add the managed C{PopupMenuButton} to the C{MainView}'s status bar."""
        statusbar = self.controller.main_controller.view.status_bar

        for child in statusbar.get_children():
            if child is self.popupbutton:
                return
        statusbar.pack_end(self.popupbutton, expand=False)
        statusbar.show_all()

    def focus(self):
        self.popupbutton.grab_focus()

    def update_recent_pairs(self):
        if not self.menu:
            self._init_menu()
        # Clear all menu items
        for i in range(self.controller.NUM_RECENT):
            item = self.recent_items[i]
            if item.parent is self.menu:
                item.get_child().set_text('')
                self.menu.remove(item)

        # Update menu items' strings
        i = 0
        for pair in self.controller.recent_pairs:
            if i not in range(self.controller.NUM_RECENT):
                break
            self.recent_items[i].get_child().set_text_with_mnemonic(
                "_%(accesskey)d. %(language_pair)s" % {
                    "accesskey": i + 1,
                    "language_pair": self._get_display_string(*pair)
                }
            )
            i += 1

        # Re-add menu items that have something to show
        for i in range(self.controller.NUM_RECENT):
            item = self.recent_items[i]
            if item.get_child().get_text():
                self.menu.insert(item, i)

        self.menu.show_all()
        self.popupbutton.text = self.recent_items[0].get_child().get_text()[3:]


    # EVENT HANDLERS #
    def _on_addlang_clicked(self, button):
        if not self.add_dialog.run():
            return

        err = self.add_dialog.check_input_sanity()
        if err:
            self.controller.main_controller.show_error(err)
            return

        name = self.add_dialog.langname
        code = self.add_dialog.langcode
        nplurals = self.add_dialog.nplurals
        plural = self.add_dialog.plural

        if self.add_dialog.langcode in LanguageModel.languages:
            raise Exception('Language code %s already used.' % (code))

        LanguageModel.languages[code] = (name, nplurals, plural)
        self.controller.new_langs.append(code)

        # Reload the language data in the selection dialog.
        self.select_dialog.clear_langs()
        langs = [LanguageModel(lc) for lc in LanguageModel.languages]
        langs.sort(key=lambda x: x.name)
        self.select_dialog.update_languages(langs)

    def _on_button_toggled(self, popupbutton):
        if not popupbutton.get_active():
            return
        detected = self.controller.get_detected_langs()
        if detected and len(detected) == 2 and detected[0] and detected[1]:
            logging.debug("Detected language pair: %s -> %s" % (detected[0].code, detected[1].code))
            if detected not in self.controller.recent_pairs:
                if len(self.controller.recent_pairs) >= self.controller.NUM_RECENT:
                    self.controller.recent_pairs[-1] = detected
                else:
                    self.controller.recent_pairs.append(detected)
        self.update_recent_pairs()

    def _on_other_activated(self, menuitem):
        if not getattr(self, 'select_dialog', None):
            self._create_dialogs()
        if self.select_dialog.run(self.controller.source_lang.code, self.controller.target_lang.code):
            self.controller.set_language_pair(
                self.select_dialog.get_selected_source_lang(),
                self.select_dialog.get_selected_target_lang()
            )
        self.controller.main_controller.unit_controller.view.targets[0].grab_focus()

    def _on_pairitem_activated(self, menuitem, item_n):
        logging.debug('Selected language pair: %s' % (self.recent_items[item_n].get_child().get_text()))
        pair = self.controller.recent_pairs[item_n]
        self.controller.set_language_pair(*pair)
        self.controller.main_controller.unit_controller.view.targets[0].grab_focus()

    def _on_style_set(self, widget, prev_style):
        if not hasattr(self, 'popup_default_fg'):
            self.popup_default_fg = widget.style.fg

########NEW FILE########
__FILENAME__ = mainview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
# Copyright 2013-2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import locale
import os
import sys
from gtk import gdk

from virtaal.views import theme
from virtaal.common import pan_app

from baseview import BaseView

def fill_dialog(dialog, title='', message='', markup=''):
    if title:
        dialog.set_title(title)
    if markup:
        dialog.set_markup(markup)
    else:
        dialog.set_markup(message.replace('<', '&lt;'))


class EntryDialog(gtk.Dialog):
    """A simple dialog containing a dialog for user input."""

    def __init__(self, parent):
        super(EntryDialog, self).__init__(title='Input Dialog', parent=parent)
        self.set_size_request(450, 100)

        self.lbl_message = gtk.Label()
        self.vbox.pack_start(self.lbl_message)

        self.ent_input = gtk.Entry()
        self.ent_input.set_activates_default(True)
        self.vbox.pack_start(self.ent_input)

        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.set_default_response(gtk.RESPONSE_OK)

    def run(self, title=None, message=None, keepInput=False):
        if message:
            self.set_message(message)
        if title:
            self.set_title(title)

        if not keepInput:
            self.ent_input.set_text('')

        self.show_all()
        self.ent_input.grab_focus()
        response = super(EntryDialog, self).run()

        return response, self.ent_input.get_text().decode('utf-8')

    def set_message(self, message):
        self.lbl_message.set_markup(message)

    def set_title(self, title):
        super(EntryDialog, self).set_title(title)

# XXX: This class is based on main_window.py:Virtaal from the pre-MVC days (Virtaal 0.2).
class MainView(BaseView):
    """The view containing the main window and menus."""

    # INITIALIZERS #
    def __init__(self, controller):
        """Constructor.
            @type  controller: virtaal.controllers.MainController
            @param controller: The controller that this view is "connected" to."""
        self.controller = controller
        self.modified = False

        if os.name == 'nt':
            # Make sure that rule-hints are shown in Windows
            rc_string = """
                style "show-rules"
                {
                    GtkTreeView::allow-rules = 1
                }
                class "GtkTreeView" style "show-rules"
                """
            gtk.rc_parse_string(rc_string)

        # Set the GtkBuilder file
        self.gui = self.load_builder_file(["virtaal", "virtaal.ui"], root='MainWindow', domain="virtaal")
        self.main_window = self.gui.get_object("MainWindow")

        # The classic menu bar:
        self.menubar = self.gui.get_object('menubar')
        # The menu structure, regardless of where it is shown (initially the menubar):
        self.menu_structure = self.menubar
        self.status_bar = self.gui.get_object("status_bar")
        self.status_bar.set_sensitive(False)
        self.statusbar_context_id = self.status_bar.get_context_id("statusbar")
        #Only used in full screen, initialised as needed
        self.btn_app = None
        self.app_menu = None

        if sys.platform == 'darwin':
            try:
                gtk.rc_parse(pan_app.get_abs_data_filename(["themes", "OSX_Leopard_theme", "gtkrc"]))
            except:
                import logging
                logging.exception("Couldn't find OSX_Leopard_theme")

            # Sometimes we have two resize grips: one from GTK, one from Aqua. We
            # might want to disable the GTK one:
            #self.gui.get_object('status_bar').set_property("has-resize-grip", False)
            try:
                import gtk_osxapplication
                osxapp = gtk_osxapplication.OSXApplication()
                # Move the menu bar to the mac menu
                self.menubar.hide()
                osxapp.set_menu_bar(self.menubar)
                # Ensure Ctrl-O change to Cmd-O, etc
                osxapp.set_use_quartz_accelerators(True)
                # Move the quit menu item
                mnu_quit = self.gui.get_object("mnu_quit")
                mnu_quit.hide()
                self.gui.get_object("separator_mnu_file_2").hide()
                # Move the about menu item
                mnu_about = self.gui.get_object("mnu_about")
                osxapp.insert_app_menu_item(mnu_about, 0)
                self.gui.get_object("separator_mnu_help_1").hide()
                # Move the preferences menu item
                osxapp.insert_app_menu_item(gtk.SeparatorMenuItem(), 1)
                mnu_prefs = self.gui.get_object("mnu_prefs")
                osxapp.insert_app_menu_item(mnu_prefs, 2)
                self.gui.get_object("separator_mnu_edit_3").hide()
                gtk.accel_map_load(pan_app.get_abs_data_filename(["virtaal", "virtaal.accel"]))
                osxapp.ready()
                osxapp.connect("NSApplicationOpenFile", self._on_osx_openfile_event)
                osxapp.connect("NSApplicationBlockTermination", self._on_quit)
            except ImportError, e:
                import logging
                logging.debug("gtk_osxapplication module not found. Expect zero integration with the Mac desktop.")

        self.main_window.connect('destroy', self._on_quit)
        self.main_window.connect('delete-event', self._on_quit)
        # File menu signals
        self.gui.get_object('mnu_open').connect('activate', self._on_file_open)
        self.gui.get_object('mnu_save').connect('activate', self._on_file_save)
        self.gui.get_object('mnu_saveas').connect('activate', self._on_file_saveas)
        self.gui.get_object('mnu_close').connect('activate', self._on_file_close)
        self.gui.get_object('mnu_update').connect('activate', self._on_file_update)
        self.gui.get_object('mnu_binary_export').connect('activate', self._on_file_binary_export)
        self.gui.get_object('mnu_revert').connect('activate', self._on_file_revert)
        self.gui.get_object('mnu_quit').connect('activate', self._on_quit)
        # View menu signals
        self.gui.get_object('mnu_fullscreen').connect('activate', self._on_fullscreen)
        # Help menu signals
        self.gui.get_object('mnu_documentation').connect('activate', self._on_documentation)
        self.gui.get_object('mnu_tutorial').connect('activate', self._on_tutorial)
        self.gui.get_object('mnu_localization_guide').connect('activate', self._on_localization_guide)
        self.gui.get_object('mnu_report_bug').connect('activate', self._on_report_bug)
        self.gui.get_object('mnu_about').connect('activate', self._on_help_about)

        self.main_window.set_icon_from_file(pan_app.get_abs_data_filename(["icons", "virtaal.ico"]))
        self.main_window.resize(
            int(pan_app.settings.general['windowwidth']),
            int(pan_app.settings.general['windowheight'])
        )
        self._top_window = self.main_window

        self.main_window.connect('window-state-event', self._on_window_state_event)

        self.controller.connect('controller-registered', self._on_controller_registered)
        self._create_dialogs()
        self._setup_key_bindings()
        self._track_window_state()
        self._setup_dnd()
        from gobject import idle_add
        idle_add(self._setup_recent_files)
        self.main_window.connect('style-set', self._on_style_set)

    def _create_dialogs(self):
        self._input_dialog = None
        self._error_dialog = None
        self._prompt_dialog = None
        self._info_dialog = None
        self._save_chooser = None
        self._open_chooser = None
        self._confirm_dialog = None

    def _setup_recent_files(self):
        from virtaal.views import recent
        recent_files = self.gui.get_object("mnu_recent_files")
        recent.rc.connect("item-activated", self._on_recent_file_activated)
        recent_files.set_submenu(recent.rc)

    @property
    def input_dialog(self):
        # Generic input dialog
        if not self._input_dialog:
            self._input_dialog = EntryDialog(self.main_window)
        return self._input_dialog

    @property
    def error_dialog(self):
        if not self._error_dialog:
        # Error dialog
            self._error_dialog = gtk.MessageDialog(self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_ERROR,
                gtk.BUTTONS_OK)
            self._error_dialog.set_title(_("Error"))
        return self._error_dialog

    @property
    def prompt_dialog(self):
        # Yes/No prompt dialog
        if not self._prompt_dialog:
            self._prompt_dialog = gtk.MessageDialog(self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_YES_NO,
            )
            self._prompt_dialog.set_default_response(gtk.RESPONSE_NO)
        return self._prompt_dialog

    @property
    def info_dialog(self):
        # Informational dialog
        if not self._info_dialog:
            self._info_dialog = gtk.MessageDialog(self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_INFO,
                gtk.BUTTONS_OK,
            )
        return self._info_dialog

    @property
    def open_chooser(self):
        # Open (file chooser) dialog
        if not self._open_chooser:
            self._open_chooser = gtk.FileChooserDialog(
                _('Choose a Translation File'),
                self.main_window,
                gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            )
            self._open_chooser.set_default_response(gtk.RESPONSE_OK)
            all_supported_filter = gtk.FileFilter()
            all_supported_filter.set_name(_("All Supported Files"))
            self._open_chooser.add_filter(all_supported_filter)
            from translate.storage import factory as storage_factory
            supported_files_dict = dict([ (_(name), (extensions, mimetypes)) for name, extensions, mimetypes in storage_factory.supported_files() ])
            supported_file_names = supported_files_dict.keys()
            supported_file_names.sort(cmp=locale.strcoll)
            for name in supported_file_names:
                extensions, mimetypes = supported_files_dict[name]
                #XXX: we can't open generic .csv formats, so listing it is probably
                # more harmful than good.
                if "csv" in extensions:
                    continue
                new_filter = gtk.FileFilter()
                new_filter.set_name(name)
                if extensions:
                    for extension in extensions:
                        new_filter.add_pattern("*." + extension)
                        all_supported_filter.add_pattern("*." + extension)
                        for compress_extension in storage_factory.decompressclass.keys():
                            new_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
                            all_supported_filter.add_pattern("*.%s.%s" % (extension, compress_extension))
                if mimetypes:
                    for mimetype in mimetypes:
                        new_filter.add_mime_type(mimetype)
                        all_supported_filter.add_mime_type(mimetype)
                self._open_chooser.add_filter(new_filter)

            #doc_filter = gtk.FileFilter()
            #doc_filter.set_name(_('Translatable documents'))
            #from translate.convert import factory as convert_factory
            #for extension in convert_factory.converters.keys():
            #    if isinstance(extension, tuple):
            #        continue # Skip extensions that need templates
            #    doc_filter.add_pattern('*.' + extension)
            #    all_supported_filter.add_pattern('*.' + extension)
            #self._open_chooser.add_filter(doc_filter)

            #proj_filter = gtk.FileFilter()
            #proj_filter.set_name(_('Translate project bundles'))
            #proj_filter.add_pattern('*.zip')
            #all_supported_filter.add_pattern('*.zip')
            #self._open_chooser.add_filter(proj_filter)

            all_filter = gtk.FileFilter()
            all_filter.set_name(_("All Files"))
            all_filter.add_pattern("*")
            self._open_chooser.add_filter(all_filter)

        return self._open_chooser

    @property
    def save_chooser(self):
        # Save (file chooser) dialog
        if not self._save_chooser:
            self._save_chooser = gtk.FileChooserDialog(
                _("Save"),
                self.main_window,
                gtk.FILE_CHOOSER_ACTION_SAVE,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK)
            )
            self._save_chooser.set_do_overwrite_confirmation(True)
            self._save_chooser.set_default_response(gtk.RESPONSE_OK)
        return self._save_chooser

    @property
    def confirm_dialog(self):
        # Save confirmation dialog (Save/Discard/Cancel buttons)
        if not self._confirm_dialog:
            (RESPONSE_SAVE, RESPONSE_DISCARD) = (gtk.RESPONSE_YES, gtk.RESPONSE_NO)
            self._confirm_dialog = gtk.MessageDialog(
                self.main_window,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_NONE,
                _("The current file has been modified.\nDo you want to save your changes?")
            )
            self._confirm_dialog.__save_button = self._confirm_dialog.add_button(gtk.STOCK_SAVE, RESPONSE_SAVE)
            self._confirm_dialog.add_button(_("_Discard"), RESPONSE_DISCARD)
            self._confirm_dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            self._confirm_dialog.set_default_response(RESPONSE_SAVE)
        return self._confirm_dialog

    def _setup_key_bindings(self):
        self.accel_group = gtk.AccelGroup()
        self.main_window.add_accel_group(self.accel_group)

    def _track_window_state(self):
        self._window_is_maximized = False

        def on_state_event(widget, event):
            self._window_is_maximized = bool(event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED)
        self.main_window.connect('window-state-event', on_state_event)

    def _setup_dnd(self):
        """configures drag and drop"""
        targets = gtk.target_list_add_uri_targets()
        # Konqueror needs gtk.gdk.ACTION_MOVE
        self.main_window.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self.main_window.connect("drag_data_received", self._on_drag_data_received)

    def _on_drag_data_received(self, w, context, x, y, data, info, time):
        if sys.platform == 'darwin' or gtk.targets_include_uri(context.targets):
            # We don't check for valid targets on Mac (darwin) since there is
            # a bug in target_incude_uri on that platform, no adverse situations
            # seem to arise but we leave other platforms to do the right thing.

            # the data comes as a string with each URI on a line; lines
            # terminated with '\r\n. For now we just take the first one:
            filename = data.data.split("\r\n")[0]
            if filename.startswith("file://"):
                # This is a URI, so we handle encoded characters like spaces:
                import urllib
                filename = urllib.unquote(filename)
                #TODO: only bother if the extension is supported?
                self.controller.open_file(filename)

        return True

    def _on_style_set(self, widget, prev_style):
        theme.update_style(widget)
        # on windows the tooltip colour is wrong in inverse themes (bug 1923)
        if os.name == 'nt':
            if theme.INVERSE:
                tooltip_text = "white"
            else:
                tooltip_text = "black"
            rc_string = """
                style "better-tooltips"
                {
                    fg[NORMAL] = "%s"
                }
                widget "gtk-tooltip*" style "better-tooltips"
                """ % tooltip_text
            gtk.rc_parse_string(rc_string)


    # ACCESSORS #
    def add_accel_group(self, accel_group):
        """Add the given accelerator group to the main window.
            @type accel_group: gtk.AccelGroup"""
        self.main_window.add_accel_group(accel_group)

    def set_saveable(self, value):
        # Repeatedly doing all of this is unnecessary, and can make the window
        # title flash slightly. So if the file is already modified, don't
        # bother redoing all of this.
        if value and self.modified:
            return
        menuitem = self.gui.get_object("mnu_save")
        menuitem.set_sensitive(value)
        menuitem = self.gui.get_object("mnu_revert")
        menuitem.set_sensitive(value)
        filename = self.controller.get_store_filename()
        if filename:
            modified = ""
            if value:
                modified = "*"
            self.main_window.set_title(
                    #l10n: This is the title of the main window of Virtaal
                    #%(modified_marker)s is a star that is displayed if the file is modified, and should be at the start of the window title
                    #%(current_file)s is the file name of the current file
                    #most languages will not need to change this
                    (_('%(modified_marker)s%(current_file)s - Virtaal') %
                        {
                            "current_file": os.path.basename(filename),
                            "modified_marker": modified
                        }
                    ).rstrip()
                )
        self.modified = value

    def set_statusbar_message(self, msg):
        self.status_bar.pop(self.statusbar_context_id)
        self.status_bar.push(self.statusbar_context_id, msg)
        if msg:
            time.sleep(self.WRAP_DELAY)


    # METHODS #
    def ask_plural_info(self):
        """Ask the user to provide plural information.
            @returns: A 2-tuple containing the number of plurals as the first
                element and the plural equation as the second element."""
        # Adapted from Virtaal 0.2's document.py:compute_nplurals
        def ask_for_number_of_plurals():
            while True:
                try:
                    nplurals = self.show_input_dialog(message=_("Please enter the number of noun forms (plurals) to use"))
                    return int(nplurals)
                except ValueError, _e:
                    pass

        def ask_for_plurals_equation():
            return self.show_input_dialog(message=_("Please enter the plural equation to use"))

        from translate.lang import factory as langfactory
        lang     = langfactory.getlanguage(self.controller.lang_controller.target_lang.code)
        nplurals = lang.nplurals or ask_for_number_of_plurals()
        if nplurals > 1 and lang.pluralequation == "0":
            return nplurals, ask_for_plurals_equation()
        else:
            # Note that if nplurals == 1, the default equation "0" is correct
            return nplurals, lang.pluralequation

    def append_menu(self, name):
        """Add a menu with the given name to the menu bar."""
        menu = gtk.Menu()
        menuitem = gtk.MenuItem(name)
        menuitem.set_submenu(menu)
        self.menu_structure.append(menuitem)
        if self.menu_structure.get_property('visible'):
            self.menu_structure.show_all()
        return menuitem

    def append_menu_item(self, name, menu, after=None):
        """Add a new menu item with the given name to the menu with the given
            name (C{menu})."""
        if isinstance(after, (str, unicode)):
            after = self.find_menu(after)

        parent_item = None
        if isinstance(menu, gtk.MenuItem):
            parent_item = menu
        else:
            parent_item = self.find_menu(menu)
        if parent_item is None:
            return None

        parent_menu = parent_item.get_submenu()
        menuitem = gtk.MenuItem(name)
        if after is None:
            parent_menu.add(menuitem)
        else:
            after_index = parent_menu.get_children().index(after) + 1
            parent_menu.insert(menuitem, after_index)
        if self.menu_structure.get_property('visible'):
            self.menu_structure.show_all()
        return menuitem

    def find_menu(self, label):
        """Find the menu with the given label on the menu bar."""
        for menuitem in self.menu_structure.get_children():
            if menuitem.get_child() and menuitem.get_child().get_text() == label:
                return menuitem

        if '_' in label:
            return self.find_menu(label.replace('_', ''))

        return None

    def find_menu_item(self, label, menu=None):
        """Find the menu item with the given label and in the menu with the
            given name (if it exists).

            @param label: The label of the menu item to find.
            @param menu: The (optional) (name of the) menu to search in."""
        if not isinstance(menu, gtk.MenuItem):
            menu = self.find_menu(label)
        if menu is not None:
            menus = [menu]
        else:
            menus = [mi for mi in self.menu_structure.get_children()]

        for menuitem in menus:
            for item in menuitem.get_submenu().get_children():
                if item.get_child() and item.get_child().get_text() == label:
                    return item, menuitem

        if '_' in label:
            return self.find_menu_item(label.replace('_', ''), menu)

        return None, None

    def open_file(self):
        filename_and_uri = self.show_open_dialog()
        if filename_and_uri:
            filename, uri = filename_and_uri
            self._uri = uri
            return self.controller.open_file(filename, uri=uri)
        return False

    def hide(self):
        """Hide and don't return until it is really hidden."""
        self.main_window.hide()
        while gtk.events_pending():
            gtk.main_iteration()

    def quit(self):
        if self._window_is_maximized:
            pan_app.settings.general['maximized'] = 1
        else:
            width, height = self.main_window.get_size()
            pan_app.settings.general['windowwidth'] = width
            pan_app.settings.general['windowheight'] = height
            pan_app.settings.general['maximized'] = ''
        pan_app.settings.write()
        gtk.main_quit()

    def show(self):
        if pan_app.settings.general['maximized']:
            self.main_window.maximize()
        self.main_window.show()
        from gobject import threads_init
        threads_init()

        # Uncomment this line to measure startup time until the window shows.
        # It causes the program to quit immediately when the window is shown:
        #self.main_window.connect('expose-event', lambda widget, event: gtk.main_quit())

        # Uncomment these lines to measure true startup time. It causes the
        # program to quit immediately when the last thing added to the gobject
        # idle queue during startup, is done.
        #from gobject import idle_add
        #idle_add(gtk.main_quit)

        # Uncomment these lines to see which modules have already been imported
        # at this stage. Keep in mind that something like pprint could affect
        # the list.
        #print "\n".join(sorted(sys.modules.keys()))
        gtk.main()

    def show_input_dialog(self, title='', message=''):
        """Shows a simple dialog containing a text entry.
            @returns: The text entered into the dialog, or C{None}."""
        self.input_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.input_dialog
        response, text = self.input_dialog.run(title=title, message=message)
        self.input_dialog.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_OK:
            return text
        return None

    def show_open_dialog(self, title=''):
        """@returns: The selected file name and URI if the OK button was clicked.
            C{None} otherwise."""
        last_path = (pan_app.settings.general["lastdir"] or "").decode(sys.getdefaultencoding())

        # Do native dialogs in a thread so that GTK can continue drawing.
        from virtaal.support import native_widgets
        dialog_to_use = native_widgets.dialog_to_use
        if dialog_to_use:
            from virtaal.support.thread import run_in_thread
            open_dialog_func = None
            if dialog_to_use == 'kdialog':
                open_dialog_func = native_widgets.kdialog_open_dialog
            elif native_widgets.dialog_to_use == 'win32':
                open_dialog_func = native_widgets.win32_open_dialog
            elif native_widgets.dialog_to_use == 'darwin':
                open_dialog_func = native_widgets.darwin_open_dialog
            if open_dialog_func:
                return run_in_thread(self.main_window, open_dialog_func, (self.main_window, title, last_path))

        # otherwise we always fall back to the default code
        if title:
            self.open_chooser.set_title(title)

        if os.path.exists(last_path):
            self.open_chooser.set_current_folder(last_path)

        self.open_chooser.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.open_chooser
        response = self.open_chooser.run() == gtk.RESPONSE_OK
        self.open_chooser.hide()
        self._top_window = old_top

        if response:
            filename = self.open_chooser.get_filename().decode('utf-8')
            pan_app.settings.general["lastdir"] = os.path.dirname(filename)
            return (filename, self.open_chooser.get_uri().decode('utf-8'))
        else:
            return ()

    def show_error_dialog(self, title='', message='', markup=''):
        fill_dialog(self.error_dialog, title, message, markup)

        self.error_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.error_dialog
        response = self.error_dialog.run()
        self.error_dialog.hide()
        self._top_window = old_top

    def show_prompt_dialog(self, title='', message='', markup=''):
        fill_dialog(self.prompt_dialog, title, message, markup)

        self.prompt_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.prompt_dialog
        response = self.prompt_dialog.run()
        self.prompt_dialog.hide()
        self._top_window = old_top

        return response == gtk.RESPONSE_YES

    def show_info_dialog(self, title='', message='', markup=''):
        """shows a simple info dialog containing a message and an OK button"""
        fill_dialog(self.info_dialog, title, message, markup)

        self.info_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.info_dialog
        response = self.info_dialog.run()
        self.info_dialog.hide()
        self._top_window = old_top

    def show_save_dialog(self, title, current_filename=None):
        """@returns: C{True} if the OK button was pressed, C{False} for any
            other response."""
        if not current_filename:
            current_filename = self.controller.get_store().get_filename()

        # Do native dialogs in a thread so that GTK can continue drawing.
        from virtaal.support import native_widgets
        dialog_to_use = native_widgets.dialog_to_use
        save_dialog_func = None
        if dialog_to_use:
            from virtaal.support.thread import run_in_thread
            if dialog_to_use == 'kdialog':
                save_dialog_func = native_widgets.kdialog_save_dialog
            elif native_widgets.dialog_to_use == 'win32':
                save_dialog_func = native_widgets.win32_save_dialog
            elif native_widgets.dialog_to_use == 'darwin':
                dialog_to_use = native_widgets.darwin_save_dialog
            if save_dialog_func:
                return run_in_thread(self.main_window, save_dialog_func, (self.main_window, title, current_filename))

        # otherwise we always fall back to the default code
        if title:
            self.save_chooser.set_title(title)

        directory, filename = os.path.split(current_filename)

        if os.access(directory, os.F_OK | os.R_OK | os.X_OK | os.W_OK):
            self.save_chooser.set_current_folder(directory)
        self.save_chooser.set_current_name(filename)

        self.save_chooser.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.save_chooser
        response = self.save_chooser.run()
        self.save_chooser.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_OK:
            filename = self.save_chooser.get_filename().decode('utf-8')
            #FIXME: do we need uri here?
            return filename

    def show_save_confirm_dialog(self):
        """@returns: One of C{'save'}, C{'discard'}, or C{'cancel'},
            depending on the button pressed."""
        self.confirm_dialog.set_transient_for(self._top_window)
        old_top = self._top_window
        self._top_window = self.confirm_dialog
        self.confirm_dialog.__save_button.grab_focus()
        response = self.confirm_dialog.run()
        self.confirm_dialog.hide()
        self._top_window = old_top

        if response == gtk.RESPONSE_YES:
            return 'save'
        elif response == gtk.RESPONSE_NO:
            return 'discard'
        return 'cancel'

    def show_app_icon(self):
        if not self.btn_app:
            self.btn_app = self.gui.get_object('btn_app')
            image = self.gui.get_object('img_app')
            image.set_from_file(pan_app.get_abs_data_filename(['icons', 'hicolor', '24x24', 'mimetypes', 'x-translation.png']))
            self.app_menu = gtk.Menu()
            self.btn_app.connect('pressed', self._on_app_pressed)
            self.btn_app.show()
        for child in self.menu_structure:
            child.reparent(self.app_menu)
        self.menu_structure = self.app_menu
        self.btn_app.show()

    def hide_app_icon(self):
        self.btn_app.hide()
        for child in self.app_menu:
            child.reparent(self.menubar)
        self.menu_structure = self.menubar

    # SIGNAL HANDLERS #
    def _on_controller_registered(self, main_controller, new_controller):
        if not main_controller.store_controller == new_controller:
            return
        if getattr(self, '_store_loaded_handler_id ', None):
            main_controller.store_controller.disconnect(self._store_loaded_handler_id)

        self._store_closed_handler_id = new_controller.connect('store-closed', self._on_store_closed)
        self._store_loaded_handler_id = new_controller.connect('store-loaded', self._on_store_loaded)

    def _on_documentation(self, _widget=None):
        from virtaal.support import openmailto
        openmailto.open("http://translate.sourceforge.net/wiki/virtaal/index")

    def _on_file_open(self, _widget):
        self.open_file()

    def _on_file_save(self, widget=None):
        self.controller.save_file()

    def _on_file_saveas(self, widget=None):
        self.controller.save_file(force_saveas=True)

    def _on_file_binary_export(self, widget=None):
        self.controller.binary_export()

    def _on_file_close(self, widget=None):
        self.controller.close_file()

    def _on_file_update(self, _widget):
        filename_and_uri = self.show_open_dialog()
        if filename_and_uri:
            filename, uri = filename_and_uri
            self._uri = uri
            self.controller.update_file(filename, uri=uri)

    def _on_file_revert(self, widget=None):
        self.controller.revert_file()

    def _on_fullscreen(self, widget=None):
        if widget.get_active():
            self.main_window.fullscreen()
            self.status_bar.hide()
            self.show_app_icon()
            self.menubar.hide()
        else:
            self.main_window.unfullscreen()
            self.status_bar.show()
            self.hide_app_icon()
            self.menubar.show()

    def _on_tutorial(self, widget=None):
        self.controller.open_tutorial()

    def _on_localization_guide(self, _widget=None):
        # Should be more redundent
        # If the guide is installed and no internet then open local
        # If Internet then go live, if no Internet or guide then disable
        from virtaal.support import openmailto
        openmailto.open("http://translate.sourceforge.net/wiki/guide/start")

    def _on_help_about(self, _widget=None):
        from widgets.aboutdialog import AboutDialog
        AboutDialog(self.main_window)

    def _on_quit(self, *args):
        self.controller.quit()
        return True

    def _on_recent_file_activated(self, chooser):
        item = chooser.get_current_item()
        if item.exists():
            # For now we only handle local files, and limited the recent
            # manager to only give us those anyway, so we can get the filename
            self._uri = item.get_uri()
            self.controller.open_file(item.get_uri_display().decode('utf-8'), uri=item.get_uri().decode('utf-8'))

    def _on_report_bug(self, _widget=None):
        from virtaal.support import openmailto
        from virtaal import __version__
        openmailto.open("http://bugs.locamotion.org/enter_bug.cgi?product=Virtaal&version=%s" % __version__.ver)

    def _on_store_closed(self, store_controller):
        for widget_name in ('mnu_saveas', 'mnu_close', 'mnu_update', 'mnu_properties', 'mnu_binary_export'):
            self.gui.get_object(widget_name).set_sensitive(False)
        self.status_bar.set_sensitive(False)
        self.main_window.set_title(_('Virtaal'))

    def _on_store_loaded(self, store_controller):
        self.gui.get_object('mnu_saveas').set_sensitive(True)
        self.gui.get_object('mnu_close').set_sensitive(True)
        self.gui.get_object('mnu_update').set_sensitive(True)
        self.gui.get_object('mnu_properties').set_sensitive(True)
        filename = store_controller.get_store_filename()
        #TODO: move logic to storecontroller
        if filename.endswith('.po') or filename.endswith('.po.bz2') or filename.endswith('.po.gz'):
            self.gui.get_object('mnu_binary_export').set_sensitive(True)

        self.status_bar.set_sensitive(True)
        from virtaal.views import recent
        if store_controller.project:
            if not store_controller._archivetemp:
                recent.rm.add_item('file://' + store_controller.get_bundle_filename())
        else:
            if getattr(self, '_uri', None):
                recent.rm.add_item(self._uri)
            else:
                if os.name == 'nt':
                    url = 'file:///' + os.path.abspath(store_controller.store.filename)
                else:
                    url = 'file://' + os.path.abspath(store_controller.store.filename)
                recent.rm.add_item(url)

    def _on_window_state_event(self, widget, event):
        mnu_fullscreen = self.gui.get_object('mnu_fullscreen')
        mnu_fullscreen.set_active(event.new_window_state & gdk.WINDOW_STATE_FULLSCREEN)

    def _on_app_pressed(self, btn):
        self.app_menu.popup(None, None, None, 0, 0)

    def _on_osx_openfile_event(self, macapp, filename):
        # Note! A limitation of the current GTK-OSX code
        # (2.18) is that we cannot perform any operations
        # involving the GTK run-loop within this handler,
        # therefore we schedule the load to occur afterwards.
        # See gdk/quartz/gdkeventloop-quartz.c in the GTK+ source. 
        from gobject import idle_add
        def callback():
            self.controller.open_file(filename)
        idle_add(callback) 
        # We must indicate we handled this or crash
        return True 

########NEW FILE########
__FILENAME__ = markup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007-2011 Zuza Software Foundation
# Copyright 2014 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import re

from diff_match_patch import diff_match_patch

from virtaal.views.theme import current_theme


# We want to draw unexpected spaces specially so that users can spot them
# easily without having to resort to showing all spaces weirdly
_fancy_spaces_re = re.compile(r"""(?m)  #Multiline expression
        [ ]{2,}|     #More than two consecutive
        ^[ ]+|       #At start of a line
        [ ]+$        #At end of line""", re.VERBOSE)
"""A regular expression object to find all unusual spaces we want to show"""

def _fancyspaces(string):
    """Indicate the fancy spaces with a grey squigly."""
    spaces = string.group()
#    while spaces[0] in "\t\n\r":
#        spaces = spaces[1:]
    return u'<span underline="error" foreground="grey">%s</span>' % spaces


# Highligting for XML

# incorrect XML might be marked up incorrectly:  "<a> text </a more text bla"
_xml_re = re.compile("&lt;[^>]+>")
def _fancy_xml(escape):
    """Marks up the XML to appear in the warning red colour."""
    return u'<span foreground="%s">%s</span>' % (current_theme['markup_warning_fg'], escape.group())

def _subtle_escape(escape):
    """Marks up the given escape to appear in a subtle grey colour."""
    return u'<span foreground="%s">%s</span>' % (current_theme['subtle_fg'], escape)

def _escape_entities(s):
    """Escapes '&' and '<' in literal text so that they are not seen as markup."""
    s = s.replace(u"&", u"&amp;") # Must be done first!
    s = s.replace(u"<", u"&lt;")
    s = _xml_re.sub(_fancy_xml, s)
    return s


# Public methods

def markuptext(text, fancyspaces=True, markupescapes=True, diff_text=u""):
    """Markup the given text to be pretty Pango markup.

    Special characters (&, <) are converted, XML markup highligthed with
    escapes and unusual spaces optionally being indicated."""
    # locations are coming through here for some reason - tooltips, maybe
    if not text:
        return u""

    if diff_text and diff_text != text:
        text = pango_diff(diff_text, text)
    else:
        text = _escape_entities(text)

    if fancyspaces:
        text = _fancy_spaces_re.sub(_fancyspaces, text)

    if markupescapes:
#        text = text.replace(u"\r\n", _subtle_escape(u'¶\r\n')
        text = text.replace(u"\n", _subtle_escape(u'¶\n'))
        if text.endswith(u'\n</span>'):
            text = text[:-len(u'\n</span>')] + u'</span>'

    return text

def escape(text):
    """This is to escape text for use with gtk.TextView"""
    if not text:
        return ""
    text = text.replace("\n", u'¶\n')
    if text.endswith("\n"):
        text = text[:-len("\n")]
    return text

def unescape(text):
    """This is to unescape text for use with gtk.TextView"""
    if not text:
        return ""
    text = text.replace("\t", "")
    text = text.replace("\n", "")
    text = text.replace("\r", "")
    text = text.replace("\\t", "\t")
    text = text.replace("\\n", "\n")
    text = text.replace("\\r", "\r")
    text = text.replace("\\\\", "\\")
    return text


def _pango_spans(attr, text):
    return "<span %s>%s</span>" % (attr, _escape_entities(text))


# Templates for pango markup
# Variable substitution is done later, so that it can react to theme changes.
_diff_pango_templates = {
        'insert_attr':
                "underline='single'"\
                "underline_color='#777777'"\
                "weight='bold'"\
                "background='%(diff_insert_bg)s'",
        'delete_attr':
                "strikethrough='true'"\
                "strikethrough_color='#777'"\
                "background='%(diff_delete_bg)s'",
        #replace_attr_remove = delete_attr
        'replace_attr_add':
                "underline='single'"\
                "underline_color='#777777'"\
                "weight='bold'"
                "background='%(diff_replace_bg)s'",
        'replace_attr_add_case':
                "underline='single'"\
                "underline_color='#777777'"\
                "background='%(diff_replace_bg)s'",
}

differencer = diff_match_patch()
def pango_diff(a, b):
    """Highlights the differences between a and b for Pango rendering.

    We try to simplify things by only showing the new part of a replacement,
    unless it might be misleading (e.g. when a big chunk is replaced with a
    much shorter string). Certain cases with mostly case differences are
    highlighted more subtly."""

    insert_attr = _diff_pango_templates['insert_attr'] % current_theme
    delete_attr = _diff_pango_templates['delete_attr'] % current_theme
    replace_attr_remove = delete_attr
    replace_attr_add = _diff_pango_templates['replace_attr_add'] % current_theme
    replace_attr_add_case = _diff_pango_templates['replace_attr_add_case'] % current_theme

    textdiff = u"" # to store the final result
    removed = u"" # the removed text that we might still want to add
    diff = differencer.diff_main(a, b)
    differencer.diff_cleanupSemantic(diff)
    for op, text in diff:
        if op == 0: # equality
            if removed:
                textdiff += _pango_spans(delete_attr, removed)
                removed = u""
            textdiff += _escape_entities(text)
        elif op == 1: # insertion
            if removed:
                # this is part of a substitution, not a plain insertion. We
                # will format this differently.
                len_text = len(text)
                len_removed = len(removed)
                # if the new insertion is big enough (will draw attention) or
                # the removed part is not much bigger than the insertion we
                # can give a subtle highlighting for mostly case differences:
                if (len_text > 5 or len_removed < len_text + 2) and \
                        removed.lower().endswith(text.lower()):
                    # a more subtle replace highligting, since only case differs
                    textdiff += _pango_spans(replace_attr_add_case, text)
                else:
                    # Replacement. We only show the deleted part of the
                    # replacement if it is much longer than the new insertion
                    # and not alphanumeric (to draw attention):
                    if len_text < 3 and len_removed > 2 * len_text and \
                            not removed.isalpha():
                        textdiff += _pango_spans(delete_attr, removed)
                    textdiff += _pango_spans(replace_attr_add, text)
                removed = u""
            else:
                # plain insertion
                textdiff += _pango_spans(insert_attr, text)
        elif op == -1: # deletion
            removed = text
    if removed:
        textdiff += _pango_spans(delete_attr, removed)
    return textdiff

########NEW FILE########
__FILENAME__ = modeview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk

from virtaal.common import GObjectWrapper

from baseview import BaseView


class ModeView(GObjectWrapper, BaseView):
    """
    Manages the mode selection on the GUI and communicates with its associated
    C{ModeController}.
    """

    __gtype_name__ = 'ModeView'
    __gsignals__ = {
        "mode-selected":  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,)),
    }

    # INITIALIZERS #
    def __init__(self, controller):
        GObjectWrapper.__init__(self)

        self.controller = controller
        self._build_gui()
        self._load_modes()

    def _build_gui(self):
        # Get the mode container from the main controller
        # We need the *same* GtkBuilder instance as used by the MainView, because we need
        # the gtk.Table as already added to the main window. Loading the GtkBuilder file again
        # would create a new main window with a different gtk.Table.
        gui = self.controller.main_controller.view.gui # FIXME: Is this acceptable?
        self.mode_box = gui.get_object('mode_box')

        self.cmb_modes = gtk.combo_box_new_text()
        self.cmb_modes.connect('changed', self._on_cmbmode_change)

        self.lbl_mode = gtk.Label()
        #l10n: This refers to the 'mode' that determines how Virtaal moves
        #between units.
        self.lbl_mode.set_markup_with_mnemonic(_('N_avigation:'))
        self.lbl_mode.props.xpad = 3
        self.lbl_mode.set_mnemonic_widget(self.cmb_modes)

        self.mode_box.attach(self.lbl_mode, 0, 1, 0, 1, xoptions=0, yoptions=0)
        self.mode_box.attach(self.cmb_modes, 1, 2, 0, 1, xoptions=0, yoptions=0)

    def _load_modes(self):
        self.displayname_index = {}
        i = 0
        for name in self.controller.modes:
            displayname = self.controller.modenames[name]
            self.cmb_modes.append_text(displayname)
            self.displayname_index[displayname] = i
            i += 1


    # METHODS #
    def hide(self):
        self.mode_box.hide()

    def remove_mode_widgets(self, widgets):
        if not widgets:
            return

        # Remove previous mode's widgets
        if self.cmb_modes.get_active() > -1:
            for w in self.mode_box.get_children():
                if w in widgets:
                    self.mode_box.remove(w)

    def select_mode(self, displayname):
        if displayname in self.displayname_index:
            self.cmb_modes.set_active(self.displayname_index[displayname])
        else:
            raise ValueError('Unknown mode specified: %s' % (mode_name))

    def show(self):
        self.mode_box.show_all()

    def focus(self):
        self.cmb_modes.grab_focus()

    # EVENT HANDLERS #
    def _on_cmbmode_change(self, combo):
        self.emit('mode-selected', combo.get_active_text())

########NEW FILE########
__FILENAME__ = placeablesguiinfo
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gtk.gdk
import pango
from translate.storage.placeables import base, StringElem, general, xliff

from virtaal.views.rendering import get_role_font_description, make_pango_layout
from virtaal.views import theme


def _count_anchors(buffer, itr):
    anchor_text = buffer.get_slice(buffer.get_start_iter(), itr)
    #XXX: This is a utf-8 bytestring, not unicode! Converting to Unicode
    # just to look for 0xFFFC is a waste.
    return anchor_text.count('\xef\xbf\xbc')


class StringElemGUI(object):
    """
    A convenient container for all GUI properties of a L{StringElem}.
    """

    # MEMBERS #
    fg = '#000' # See update_style
    """The current foreground colour.
        @see update_style"""
    bg = '#fff'
    """The current background colour.
        @see update_style"""

    cursor_allowed = True
    """Whether the cursor is allowed to enter this element."""


    # INITIALIZERS #
    def __init__(self, elem, textbox, **kwargs):
        if not isinstance(elem, StringElem):
            raise ValueError('"elem" parameter must be a StringElem.')
        self.elem = elem
        self.textbox = textbox
        self.widgets = []
        self.create_repr_widgets()

        attribs = ('fg', 'bg', 'cursor_allowed')
        for kw in kwargs:
            if kw in attribs:
                setattr(self, kw, kwargs[kw])

    # METHODS #
    def create_tags(self):
        tag = gtk.TextTag()
        if self.fg:
            tag.props.foreground = self.fg

        if self.bg:
            tag.props.background = self.bg

        return [(tag, None, None)]

    def create_repr_widgets(self):
        """Creates the two widgets that are rendered before and after the
            contained string. The widgets should be placed in C{self.widgets}."""
        return None

    def copy(self):
        return self.__class__(
            elem=self.elem, textbox=self.textbox,
            fg=self.fg, bg=self.bg,
            cursor_allowed=self.cursor_allowed
        )

    def elem_at_offset(self, offset, child_offset=0):
        """Find the C{StringElem} at the given offset.
            This method is used in Virtaal as a replacement for
            C{StringElem.elem_at_offset}, because this method takes the rendered
            widgets into account.

            @type  offset: int
            @param offset: The offset into C{self.textbox} to find the the element
            @type  child_offset: int
            @param child_offset: The offset of C{self.elem} into the buffer of
                C{self.textbox}. This is so recursive calls to child elements
                can be aware of where in the textbox it appears."""
        if offset < 0 or offset >= self.length():
            return None

        pre_len = self.has_start_widget() and 1 or 0

        # First check if offset doesn't point to a widget that does not belong to self.elem
        if offset in (0, self.length()-1):
            anchor = self.textbox.buffer.get_iter_at_offset(child_offset+offset).get_child_anchor()
            if anchor is not None:
                widget = anchor.get_widgets()

                if len(widget) > 0:
                    widget = widget[0]

                    # The list comprehension below is used, in stead of a simple "w in self.widgets",
                    # because we want to use "is" comparison in stead of __eq__.
                    if widget is not None and [w for w in self.widgets if w is widget]:
                        return self.elem
                    if self.elem.isleaf():
                        # If there's a widget at {offset}, but it does not belong to this widget or
                        # any of its children (it's a leaf, so no StringElem children), the widget
                        # can't be part of the sub-tree with {self.elem} at the root.
                        return None

        if self.elem.isleaf():
            return self.elem

        child_offset += pre_len
        offset -= pre_len

        childlen = 0 # Length of the children already consumed
        for child in self.elem.sub:
            if isinstance(child, StringElem):
                if not hasattr(child, 'gui_info'):
                    gui_info_class = self.textbox.placeables_controller.get_gui_info(child)
                    child.gui_info = gui_info_class(elem=child, textbox=self.textbox)

                try:
                    elem = child.gui_info.elem_at_offset(offset-childlen, child_offset=child_offset+childlen)
                    if elem is not None:
                        return elem
                except AttributeError:
                    pass
                childlen += child.gui_info.length()
            else:
                if offset <= len(child):
                    return self.elem
                childlen += len(child)

        return None

    def get_insert_widget(self):
        return None

    def gui_to_tree_index(self, index):
        # The difference between a GUI offset and a tree offset is the iter-
        # consuming widgets in the text box. So we just iterate from the start
        # of the text buffer and count the positions without widgets.

        if index == 0:
            return 0

        if self.elem.isleaf() and len(self.widgets) == 0:
            return index

        # buffer might contain anchors
        buffer = self.textbox.buffer
        anchors = _count_anchors(buffer, buffer.get_iter_at_offset(index))
        return index - anchors

    def has_start_widget(self):
        return len(self.widgets) > 0 and self.widgets[0]

    def has_end_widget(self):
        return len(self.widgets) > 1 and self.widgets[1]

    def index(self, elem):
        """Replacement for C{StringElem.elem_offset()} to be aware of included
            widgets."""
        if elem is self.elem:
            return 0

        i = 0
        if self.has_start_widget():
            i = 1
        for child in self.elem.sub:
            if isinstance(child, StringElem):
                index = child.gui_info.index(elem)
                if index >= 0:
                    return index + i
                i -= index # XXX: Add length. See comment below.
            else:
                i += len(child)
        # We basically calculated the length thus far, so pass it back as a
        # negative number to avoid having to call .length() as well. Big
        # performance win in very complex trees.
        if self.has_end_widget():
            i += 1
        return -i

    def iter_sub_with_index(self):
        i = 0
        if self.has_start_widget():
            i = 1
        for child in self.elem.sub:
            yield (child, i)
            if hasattr(child, 'gui_info'):
                i += child.gui_info.length()
            else:
                i += len(child)

    def length(self):
        """Calculate the length of the current element, taking into account
            possibly included widgets."""
        length = len([w for w in self.widgets if w is not None])
        for child in self.elem.sub:
            if isinstance(child, StringElem) and hasattr(child, 'gui_info'):
                length += child.gui_info.length()
            else:
                length += len(child)
        return length

    def render(self, offset=-1):
        """Render the string element string and its associated widgets."""
        buffer = self.textbox.buffer
        if offset < 0:
            offset = 0
            buffer.set_text('')

        if self.has_start_widget():
            anchor = buffer.create_child_anchor(buffer.get_iter_at_offset(offset))
            self.textbox.add_child_at_anchor(self.widgets[0], anchor)
            self.widgets[0].show()
            offset += 1

        for child in self.elem.sub:
            if isinstance(child, StringElem):
                child.gui_info.render(offset)
                offset += child.gui_info.length()
            else:
                buffer.insert(buffer.get_iter_at_offset(offset), child)
                offset += len(child)

        if self.has_end_widget():
            anchor = buffer.create_child_anchor(buffer.get_iter_at_offset(offset))
            self.textbox.add_child_at_anchor(self.widgets[1], anchor)
            self.widgets[1].show()
            offset += 1

        return offset

    def tree_to_gui_index(self, index):
        return self.treeindex_to_iter(index).get_offset()

    def treeindex_to_iter(self, index, start_at=None):
        """Convert the tree index to a gtk iterator. The optional start_at
        indicates a reference point (index, iter) from where to start looking,
        for example a previous index that is known to have occurred earlier."""
        buffer = self.textbox.buffer
        if index == 0:
            return buffer.get_start_iter()

        if self.elem.isleaf() and len(self.widgets) == 0:
            return buffer.get_iter_at_offset(index)

        if start_at:
            (char_counter, itr) = start_at
            itr = itr.copy()
            assert char_counter <= index
        else:
            itr = buffer.get_iter_at_offset(index)
            anchors = _count_anchors(buffer, itr)
            char_counter = index - anchors
        while char_counter <= index and not itr.is_end():
            anchor = itr.get_child_anchor()
            if anchor is None or not anchor.get_widgets():
                char_counter += 1
            itr.forward_char()
        itr.backward_char()
        return itr


class PhGUI(StringElemGUI):
    fg = theme.current_theme['markup_warning_fg']
    bg = theme.current_theme['ph_placeable_bg']


class BxGUI(StringElemGUI):
    bg = '#E6E6FA'

    def create_repr_widgets(self):
        self.widgets.append(gtk.Label('(('))

        for lbl in self.widgets:
            font_desc = self.textbox.style.font_desc
            lbl.modify_font(font_desc)
            self.textbox.get_pango_context().set_font_description(font_desc)
            w, h = make_pango_layout(self.textbox, u'((', 100).get_pixel_size()
            lbl.set_size_request(-1, int(h/1.2))


class ExGUI(StringElemGUI):
    bg = '#E6E6FA'

    def create_repr_widgets(self):
        self.widgets.append(gtk.Label('))'))

        for lbl in self.widgets:
            font_desc = self.textbox.style.font_desc
            lbl.modify_font(font_desc)
            self.textbox.get_pango_context().set_font_description(font_desc)
            w, h = make_pango_layout(self.textbox, u'))', 100).get_pixel_size()
            lbl.set_size_request(-1, int(h/1.2))


class NewlineGUI(StringElemGUI):
    SCALE_FACTOR = 1.2 # Experimentally determined
    fg = theme.current_theme['subtle_fg']

    def create_repr_widgets(self):
        lbl = gtk.Label(u'¶')
        lbl.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.fg)) # foreground is light grey
        font_desc = self.textbox.style.font_desc
        lbl.modify_font(font_desc)
        self.textbox.get_pango_context().set_font_description(font_desc)
        w, h = make_pango_layout(self.textbox, u'¶', 100).get_pixel_size()
        lbl.set_size_request(-1, int(h/1.2))
        self.widgets.append(lbl)

class UrlGUI(StringElemGUI):
    fg = theme.current_theme['url_fg']

    def create_tags(self):
        tag = gtk.TextTag()
        tag.props.foreground = self.fg
        tag.props.background = self.bg
        tag.props.underline = pango.UNDERLINE_SINGLE
        return [(tag, None, None)]


class GPlaceableGUI(StringElemGUI):
    bg = '#ffd27f'

    def create_repr_widgets(self):
        self.widgets.append(gtk.Label('<'))
        self.widgets.append(gtk.Label('>'))
        if self.elem.id:
            self.widgets[0].set_text('<%s|' % (self.elem.id))

        for lbl in self.widgets:
            font_desc = self.textbox.style.font_desc
            lbl.modify_font(font_desc)
            self.textbox.get_pango_context().set_font_description(font_desc)
            w, h = make_pango_layout(self.textbox, u'<foo>', 100).get_pixel_size()
            lbl.set_size_request(-1, int(h/1.2))


class XPlaceableGUI(StringElemGUI):
    bg = '#ff7fef'

    def create_repr_widgets(self):
        lbl = gtk.Label('[]')
        self.widgets.append(lbl)
        if self.elem.id:
            lbl.set_text('[%s]' % (self.elem.id))

        font_desc = self.textbox.style.font_desc
        lbl.modify_font(font_desc)
        self.textbox.get_pango_context().set_font_description(font_desc)
        w, h = make_pango_layout(self.textbox, u'[foo]', 100).get_pixel_size()
        lbl.set_size_request(-1, int(h/1.2))


class UnknownXMLGUI(StringElemGUI):
    bg = '#add8e6'

    def create_repr_widgets(self):
        self.widgets.append(gtk.Label('{'))
        self.widgets.append(gtk.Label('}'))

        info = ''
        if self.elem.xml_node.tag:
            tag = self.elem.xml_node.tag
            if tag.startswith('{'):
                # tag is namespaced
                tag = tag[tag.index('}')+1:]
            info += tag + '|'
        # Uncomment the if's below for more verbose placeables
        #if self.elem.id:
        #    info += 'id=%s|'  % (self.elem.id)
        #if self.elem.rid:
        #    info += 'rid=%s|' % (self.elem.rid)
        #if self.elem.xid:
        #    info += 'xid=%s|' % (self.elem.xid)
        if info:
            self.widgets[0].set_text('{%s' % (info))

        for lbl in self.widgets:
            lbl.modify_font(get_role_font_description(self.textbox.role))
            w, h = make_pango_layout(self.textbox, u'{foo}', 100).get_pixel_size()
            lbl.set_size_request(-1, int(h/1.2))

def update_style(widget):
    fg = widget.style.fg[gtk.STATE_NORMAL]
    bg = widget.style.base[gtk.STATE_NORMAL]
    StringElemGUI.fg = fg.to_string()
    StringElemGUI.bg = bg.to_string()
    PhGUI.fg = theme.current_theme['markup_warning_fg']
    PhGUI.bg = theme.current_theme['ph_placeable_bg']
    UrlGUI.fg = theme.current_theme['url_fg']
    NewlineGUI.fg = theme.current_theme['subtle_fg']


element_gui_map = [
    (general.NewlinePlaceable, NewlineGUI),
    (general.UrlPlaceable, UrlGUI),
    (general.EmailPlaceable, UrlGUI),
    (base.Ph, PhGUI),
    (base.Bx, BxGUI),
    (base.Ex, ExGUI),
    (base.G, GPlaceableGUI),
    (base.X, XPlaceableGUI),
    (xliff.UnknownXML, UnknownXMLGUI),
]

########NEW FILE########
__FILENAME__ = prefsview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gtk.gdk
import pango
from gobject import SIGNAL_RUN_FIRST

from virtaal.common import GObjectWrapper, pan_app
from virtaal.views.widgets.selectview import SelectView

from baseview import BaseView


class PreferencesView(BaseView, GObjectWrapper):
    """Load, display and control the "Preferences" dialog."""

    __gtype_name__ = 'PreferencesView'
    __gsignals__ = {
        'prefs-done': (SIGNAL_RUN_FIRST, None, ()),
    }

    # INITIALIZERS #
    def __init__(self, controller):
        GObjectWrapper.__init__(self)
        self.controller = controller
        self._widgets = {}
        self._setup_key_bindings()
        self._setup_menu_item()

    def _get_widgets(self):
        self.gui = self.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='PreferencesDlg',
            domain="virtaal"
        )

        widget_names = (
            'btn_default_fonts', 'ent_email', 'ent_team', 'ent_translator',
            'fbtn_source', 'fbtn_target', 'scrwnd_placeables', 'scrwnd_plugins',
        )
        for name in widget_names:
            self._widgets[name] = self.gui.get_object(name)

        self._widgets['dialog'] = self.gui.get_object('PreferencesDlg')
        self._widgets['dialog'].set_transient_for(self.controller.main_controller.view.main_window)
        self._widgets['dialog'].set_icon(self.controller.main_controller.view.main_window.get_icon())

    def _init_gui(self):
        self._get_widgets()
        self._init_font_gui()
        self._init_placeables_page()
        self._init_plugins_page()

    def _init_font_gui(self):
        def reset_fonts(button):
            self._widgets['fbtn_source'].set_font_name(pan_app.get_default_font())
            self._widgets['fbtn_target'].set_font_name(pan_app.get_default_font())
        self._widgets['btn_default_fonts'].connect('clicked', reset_fonts)

    def _init_placeables_page(self):
        self.placeables_select = SelectView()
        self.placeables_select.connect('item-enabled', self._on_placeable_toggled)
        self.placeables_select.connect('item-disabled', self._on_placeable_toggled)
        self._widgets['scrwnd_placeables'].add(self.placeables_select)
        self._widgets['scrwnd_placeables'].show_all()

    def _init_plugins_page(self):
        self.plugins_select = SelectView()
        self.plugins_select.connect('item-enabled', self._on_plugin_toggled)
        self.plugins_select.connect('item-disabled', self._on_plugin_toggled)
        self._widgets['scrwnd_plugins'].add(self.plugins_select)
        self._widgets['scrwnd_plugins'].show_all()

    def _setup_key_bindings(self):
        gtk.accel_map_add_entry("<Virtaal>/Edit/Preferences", gtk.keysyms.p, gtk.gdk.CONTROL_MASK)

    def _setup_menu_item(self):
        mainview = self.controller.main_controller.view
        menu_edit = mainview.gui.get_object('menu_edit')
        mnu_prefs = mainview.gui.get_object('mnu_prefs')

        accel_group = menu_edit.get_accel_group()
        if accel_group is None:
            accel_group = gtk.AccelGroup()
            menu_edit.set_accel_group(accel_group)
            mainview.add_accel_group(accel_group)

        mnu_prefs.set_accel_path("<Virtaal>/Edit/Preferences")
        mnu_prefs.connect('activate', self._show_preferences)

    # ACCESSORS #
    def _get_font_data(self):
        return {
            'source': self._widgets['fbtn_source'].get_font_name(),
            'target': self._widgets['fbtn_target'].get_font_name(),
        }
    def _set_font_data(self, value):
        if not isinstance(value, dict) or not 'source' in value or not 'target' in value:
            raise ValueError('Value must be a dictionary')
        sourcefont = pango.FontDescription(value['source'])
        targetfont = pango.FontDescription(value['target'])
        self._widgets['fbtn_source'].set_font_name(value['source'])
        self._widgets['fbtn_target'].set_font_name(value['target'])
    font_data = property(_get_font_data, _set_font_data)

    def _get_placeables_data(self):
        return self.placeables_select.get_all_items()
    def _set_placeables_data(self, value):
        selected = self.placeables_select.get_selected_item()
        self.placeables_select.set_model(value)
        self.placeables_select.select_item(selected)
    placeables_data = property(_get_placeables_data, _set_placeables_data)

    def _get_plugin_data(self):
        return self.plugins_select.get_all_items()
    def _set_plugin_data(self, value):
        selected = self.plugins_select.get_selected_item()
        self.plugins_select.set_model(value)
        self.plugins_select.select_item(selected)
    plugin_data = property(_get_plugin_data, _set_plugin_data)

    def _get_user_data(self):
        return {
            'name':  self._widgets['ent_translator'].get_text(),
            'email': self._widgets['ent_email'].get_text(),
            'team':  self._widgets['ent_team'].get_text()
        }
    def _set_user_data(self, value):
        if not isinstance(value, dict):
            raise ValueError('Value must be a dictionary')
        if 'name' in value:
            self._widgets['ent_translator'].set_text(value['name'] or u'')
        if 'email' in value:
            self._widgets['ent_email'].set_text(value['email'] or u'')
        if 'team' in value:
            self._widgets['ent_team'].set_text(value['team'] or u'')
    user_data = property(_get_user_data, _set_user_data)


    # METHODS #
    def show(self):
        if not self._widgets:
            self._init_gui()
        self.placeables_select.select_item(None)
        self.plugins_select.select_item(None)
        self.controller.update_prefs_gui_data()
        #logging.debug('Plug-in data: %s' % (str(self.plugin_data)))
        self._widgets['dialog'].run()
        self._widgets['dialog'].hide()
        self.emit('prefs-done')


    # EVENT HANDLERS #
    def _on_placeable_toggled(self, sview, item):
        self.controller.set_placeable_enabled(
            parser=item['data'],
            enabled=item['enabled']
        )

    def _on_plugin_toggled(self, sview, item):
        self.controller.set_plugin_enabled(
            plugin_name=item['data']['internal_name'],
            enabled=item['enabled']
        )

    def _show_preferences(self, *args):
        self.show()

########NEW FILE########
__FILENAME__ = propertiesview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from virtaal.common import GObjectWrapper

from baseview import BaseView


def _statistics(stats):
    """return string tuples (Description, value) when given the output of
    statsdb.StatsCache::file_extended_totals"""
    descriptions = {
            "empty": _("Untranslated:"),
            "needs-work": _("Needs work:"),
            "rejected": _("Rejected:"),
            "needs-review": _("Needs review:"),
            "unreviewed": _("Translated:"),
            "final": _("Reviewed:"),
    }
    from translate.storage import statsdb
    state_dict = statsdb.extended_state_strings

    # just to check that the code didn't get out of sync somewhere:
    if not set(descriptions.iterkeys()) == set(state_dict.itervalues()):
        logging.warning("statsdb.state_dict doesn't correspond to descriptions here")

    statistics = []
    # We want to build them up from untranslated -> reviewed
    for state in sorted(state_dict.iterkeys()):
        key = state_dict[state]
        if not key in stats:
            continue
        statistics.append((descriptions[key], stats[key]['units'], stats[key]['sourcewords']))
    return statistics


def _nice_percentage(numerator, denominator):
    """Returns a string that is a nicely readable percentage."""
    if numerator == 0:
        return _("(0%)")
    if numerator == denominator:
        return _("(100%)")
    percentage = numerator * 100.0 / denominator
    #l10n: This is the formatting for percentages in the file properties. If unsure, just copy the original.
    return _("(%04.1f%%)") % percentage


class PropertiesView(BaseView, GObjectWrapper):
    """Load, display and control the "Properties" dialog."""

    __gtype_name__ = 'PropertiesView'

    # INITIALIZERS #
    def __init__(self, controller):
        GObjectWrapper.__init__(self)
        self.controller = controller
        self._widgets = {}
        self.data = {}
        self._setup_key_bindings()
        self._setup_menu_item()

    def _get_widgets(self):
        self.gui = self.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='PropertiesDlg',
            domain="virtaal"
        )

        widget_names = (
            'tbl_properties',
            'lbl_type', 'lbl_location', 'lbl_filesize',
            'lbl_word_total', 'lbl_string_total',
            'vbox_word_labels', 'vbox_word_stats', 'vbox_word_perc',
            'vbox_string_labels', 'vbox_string_stats', 'vbox_string_perc',
        )
        for name in widget_names:
            self._widgets[name] = self.gui.get_object(name)

        self._widgets['dialog'] = self.gui.get_object('PropertiesDlg')
        self._widgets['dialog'].set_transient_for(self.controller.main_controller.view.main_window)
        self._widgets['dialog'].set_icon(self.controller.main_controller.view.main_window.get_icon())

    def _init_gui(self):
        self._get_widgets()

    def _setup_key_bindings(self):
        import gtk.gdk
        gtk.accel_map_add_entry("<Virtaal>/File/Properties", gtk.keysyms.Return, gtk.gdk.MOD1_MASK)

    def _setup_menu_item(self):
        mainview = self.controller.main_controller.view
        menu_file = mainview.gui.get_object('menu_file')
        mnu_properties = mainview.gui.get_object('mnu_properties')

        accel_group = menu_file.get_accel_group()
        if not accel_group:
            accel_group = gtk.AccelGroup()
            menu_file.set_accel_group(accel_group)
            mainview.add_accel_group(accel_group)

        mnu_properties.set_accel_path("<Virtaal>/File/Properties")
        mnu_properties.connect('activate', self._show_properties)

    # ACCESSORS #


    # METHODS #
    def show(self):
        if not self._widgets:
            self._init_gui()
        self.controller.update_gui_data()
        statistics = _statistics(self.stats)
        tbl_properties = self._widgets['tbl_properties']
        if self.controller.main_controller.store_controller.is_modified():
            tbl_properties.set_tooltip_text(_("Save the file for up-to-date information"))
        else:
            tbl_properties.set_tooltip_text("")
        vbox_word_labels = self._widgets['vbox_word_labels']
        vbox_word_stats = self._widgets['vbox_word_stats']
        vbox_word_perc = self._widgets['vbox_word_perc']
        vbox_string_labels = self._widgets['vbox_string_labels']
        vbox_string_stats = self._widgets['vbox_string_stats']
        vbox_string_perc = self._widgets['vbox_string_perc']
        # Remove all previous work so that we can start afresh:
        for vbox in (vbox_word_labels, vbox_word_stats, vbox_word_perc,
                vbox_string_labels, vbox_string_stats, vbox_string_perc):
            for child in vbox.get_children():
                vbox.remove(child)
        total_words = 0
        total_strings = 0
        for (description, strings, words) in statistics:
            # Add two identical labels for the word/string descriptions
            lbl_desc = gtk.Label(description)
            lbl_desc.set_alignment(1.0, 0.5) # Right aligned
            lbl_desc.show()
            vbox_word_labels.pack_start(lbl_desc)

            lbl_desc = gtk.Label(description)
            lbl_desc.set_alignment(1.0, 0.5) # Right aligned
            lbl_desc.show()
            vbox_string_labels.pack_start(lbl_desc)

            # Now for the numbers
            total_words += words
            lbl_stats = gtk.Label(str(words))
            lbl_stats.set_alignment(1.0, 0.5)
            lbl_stats.show()
            vbox_word_stats.pack_start(lbl_stats)

            total_strings += strings
            lbl_stats = gtk.Label(str(strings))
            lbl_stats.set_alignment(1.0, 0.5)
            lbl_stats.show()
            vbox_string_stats.pack_start(lbl_stats)

        # Now we do the percentages:
        for (description, strings, words) in statistics:
            percentage = _nice_percentage(words, total_words)
            lbl_perc = gtk.Label(percentage)
            lbl_perc.set_alignment(0.0, 0.5)
            lbl_perc.show()
            vbox_word_perc.pack_start(lbl_perc)

            percentage = _nice_percentage(strings, total_strings)
            lbl_perc = gtk.Label(percentage)
            lbl_perc.set_alignment(0.0, 0.5)
            lbl_perc.show()
            vbox_string_perc.pack_start(lbl_perc)


        #l10n: The total number of words. You can not use %Id at this stage. If unsure, just copy the original.
        self._widgets['lbl_word_total'].set_markup(_("<b>%d</b>") % total_words)
        self._widgets['lbl_string_total'].set_markup(_("<b>%d</b>") % total_strings)

        self._widgets['lbl_type'].set_text(self.data['file_type'])
        filename = self.data.get('file_location', '')
        self._widgets['lbl_location'].set_text(filename)
        if filename:
            self._widgets['lbl_location'].set_tooltip_text(filename)
        file_size = self.data.get('file_size', 0)
        if file_size:
            #Let's get this from glib20.mo so that we're consistent with the file dialogue
            import gettext
            self._widgets['lbl_filesize'].set_text(gettext.dgettext('glib20', "%.1f KB") % (file_size / 1024.0))

        self._widgets['dialog'].run()
        self._widgets['dialog'].hide()


    # EVENT HANDLERS #
    def _show_properties(self, *args):
        self.show()

########NEW FILE########
__FILENAME__ = recent
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from translate.storage import factory

import gtk


rf = gtk.RecentFilter()
for name, extensions, mimetypes in factory.supported_files():
    if extensions:
        for extension in extensions:
            if extension in ("txt"):
                continue
            rf.add_pattern("*.%s" % extension)
            for compress_extension in factory.decompressclass.keys():
                rf.add_pattern("*.%s.%s" % (extension, compress_extension))
    if mimetypes:
        for mimetype in mimetypes:
            rf.add_mime_type(mimetype)
for app in ("virtaal", "poedit", "kbabel", "lokalize", "gtranslator"):
    rf.add_application(app)

rm = gtk.recent_manager_get_default()

rc = gtk.RecentChooserMenu()
# For now we don't handle non-local files yet
rc.set_local_only(True)
rc.set_show_not_found(False)
rc.set_show_numbers(True)
rc.set_show_tips(True)
rc.set_sort_type(gtk.RECENT_SORT_MRU)
rc.add_filter(rf)
rc.set_limit(15)

########NEW FILE########
__FILENAME__ = rendering
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import pango

from virtaal.common import pan_app

_font_descriptions = {}

def get_font_description(code):
    """Provide a pango.FontDescription and keep it for reuse."""
    global _font_descriptions
    if not code in _font_descriptions:
        _font_descriptions[code] = pango.FontDescription(code)
    return _font_descriptions[code]

def get_source_font_description():
    return get_font_description(pan_app.settings.language["sourcefont"])

def get_target_font_description():
    return get_font_description(pan_app.settings.language["targetfont"])

def get_role_font_description(role):
    if role == 'source':
        return get_source_font_description()
    elif role == 'target':
        return get_target_font_description()

def make_pango_layout(widget, text, width):
    pango_layout = pango.Layout(widget.get_pango_context())
    pango_layout.set_width(width * pango.SCALE)
    pango_layout.set_wrap(pango.WRAP_WORD_CHAR)
    pango_layout.set_text(text or u"")
    return pango_layout


_languages = {}

def get_language(code):
    """Provide a pango.Language and keep it for reuse."""
    global _languages
    if not code in _languages:
        _languages[code] = pango.Language(code)
    return _languages[code]

########NEW FILE########
__FILENAME__ = storeview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from baseview import BaseView
from widgets.storetreeview import StoreTreeView


# XXX: ASSUMPTION: The model to display is self.controller.store
# TODO: Add event handler for store controller's cursor-creation event, so that
#       the store view can connect to the new cursor's "cursor-changed" event
#       (which is currently done in load_store())
class StoreView(BaseView):
    """The view of the store and interface to store-level actions."""

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        # XXX: While I can't think of a better way to do this, the following line would have to do :/
        self.parent_widget = self.controller.main_controller.view.gui.get_object('scrwnd_storeview')

        self.cursor = None
        self._cursor_changed_id = 0

        self._init_treeview()
        self._add_accelerator_bindings()

        main_window = self.controller.main_controller.view.main_window
        main_window.connect('configure-event', self._treeview.on_configure_event)
        if main_window.get_property('visible'):
            # Because StoreView might be loaded lazily, the window might already
            # have its style set
            self._on_style_set(main_window, None)
        main_window.connect('style-set', self._on_style_set)

    def _init_treeview(self):
        self._treeview = StoreTreeView(self)

    def _add_accelerator_bindings(self):
        gtk.accel_map_add_entry("<Virtaal>/Navigation/Up", gtk.accelerator_parse("Up")[0], gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Navigation/Down", gtk.accelerator_parse("Down")[0], gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Navigation/PgUp", gtk.accelerator_parse("Page_Up")[0], gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Navigation/PgDown", gtk.accelerator_parse("Page_Down")[0], gtk.gdk.CONTROL_MASK)

        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<Virtaal>/Navigation/Up", self._treeview._move_up)
        self.accel_group.connect_by_path("<Virtaal>/Navigation/Down", self._treeview._move_down)
        self.accel_group.connect_by_path("<Virtaal>/Navigation/PgUp", self._treeview._move_pgup)
        self.accel_group.connect_by_path("<Virtaal>/Navigation/PgDown", self._treeview._move_pgdown)

        mainview = self.controller.main_controller.view
        mainview.add_accel_group(self.accel_group)
        mainview.gui.get_object('menu_navigation').set_accel_group(self.accel_group)
        self.mnu_up = mainview.gui.get_object('mnu_up')
        self.mnu_down = mainview.gui.get_object('mnu_down')
        self.mnu_pageup = mainview.gui.get_object('mnu_pageup')
        self.mnu_pagedown = mainview.gui.get_object('mnu_pagedown')
        self.mnu_up.set_accel_path('<Virtaal>/Navigation/Up')
        self.mnu_down.set_accel_path('<Virtaal>/Navigation/Down')
        self.mnu_pageup.set_accel_path('<Virtaal>/Navigation/PgUp')
        self.mnu_pagedown.set_accel_path('<Virtaal>/Navigation/PgDown')

        self._set_menu_items_sensitive(False)


    # ACCESSORS #
    def get_store(self):
        return self.store

    def get_unit_celleditor(self, unit):
        return self.controller.get_unit_celleditor(unit)


    # METHODS #
    def hide(self):
        self.parent_widget.props.visible = False
        self.load_store(None)

    def load_store(self, store):
        self.store = store
        if store:
            self._treeview.set_model(store)
            self._set_menu_items_sensitive(True)
            self.cursor = self.controller.cursor
            self._cursor_changed_id = self.cursor.connect('cursor-changed', self._on_cursor_change)
        else:
            if self._cursor_changed_id and self.cursor:
                self.cursor.disconnect(self._cursor_changed_id)
                self.cursor = None
            self._set_menu_items_sensitive(False)
            self._treeview.set_model(None)

    def show(self):
        child = self.parent_widget.get_child()
        if child and child is not self._treeview:
            self.parent_widget.remove(child)
            child.destroy()
        if not self._treeview.parent:
            self.parent_widget.add(self._treeview)
        self.parent_widget.show_all()
        if not self.controller.get_store():
            return
        self._treeview.select_index(0)

    def _set_menu_items_sensitive(self, sensitive=True):
        for widget in (self.mnu_up, self.mnu_down, self.mnu_pageup, self.mnu_pagedown):
            widget.set_sensitive(sensitive)


    # EVENT HANDLERS #
    def _on_cursor_change(self, cursor):
        self._treeview.select_index(cursor.index)

    def _on_export(self, menu_item):
        # TODO: Get file name from user.
        try:
            self.controller.export_project_file(filename=None)
        except Exception, exc:
            self.controller.main_controller.view.show_error_dialog(
                title=_("Export failed"), message=str(exc)
            )

    def _on_export_open(self, menu_item):
        # TODO: Get file name from user.
        try:
            self.controller.export_project_file(filename=None, openafter=True)
        except Exception, exc:
            self.controller.main_controller.view.show_error_dialog(
                title=_("Export failed"), message=str(exc)
            )

    def _on_preview(self, menu_item):
        # TODO: Get file name from user.
        try:
            self.controller.export_project_file(filename=None, openafter=True, readonly=True)
        except Exception, exc:
            self.controller.main_controller.view.show_error_dialog(
                title=_("Preview failed"), message=str(exc)
            )

    def _on_style_set(self, widget, prev_style):
        # The following color change is to reduce the flickering seen when
        # changing units. It's not the perfect cure, but helps a lot.
        # http://bugs.locamotion.org/show_bug.cgi?id=1412
        self._treeview.modify_base(gtk.STATE_ACTIVE, widget.style.bg[gtk.STATE_NORMAL])

########NEW FILE########
__FILENAME__ = theme
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

INVERSE = False
"""Whether we are currently in an inverse type of theme (lite text on dark
background).

Other code wanting to alter their behaviour on whether we run in an inverse
theme or not, can inspect this to know.
"""

_default_theme = {
    # Generic styling for a URL
    'url_fg': '#0000ff',
    'subtle_fg': 'darkgrey',
    # Colours for the selected placeable (not affected by its type)
    'selected_placeable_fg': '#000000',
    'selected_placeable_bg': '#90ee90',
    # Red warning foreground colour for things like XML markup
    'markup_warning_fg': '#8b0000', #darkred/#8b0000
    'ph_placeable_bg': '#f7f7f7',
    # warning background for things like no search result
    'warning_bg': '#f66',
    # row colour for fuzzy strings
    'fuzzy_row_bg': 'grey',
    # selector text box border
    'selector_textbox': '#5096f3',
    # diffing markup:
    # background for insertion
    'diff_insert_bg': '#a0ffa0',
    # background for deletion
    'diff_delete_bg': '#ccc',
    # background for replacement (deletion+insertion)
    'diff_replace_bg': '#ffff70',
}

_inverse_theme = {
    'url_fg': '#aaaaff',
    'subtle_fg': 'grey',
    'selected_placeable_fg': '#ffffff',
    'selected_placeable_bg': '#007010',
    'markup_warning_fg': '#ffa0a0',
    'ph_placeable_bg': '#101010',
    'warning_bg': '#900',
    'fuzzy_row_bg': '#474747',
    'selector_textbox': '#cbdffb',
    'diff_insert_bg': '#005500',
    'diff_delete_bg': '#333',
    'diff_replace_bg': '#4a4a00',
}

current_theme = _default_theme.copy()

def set_default():
    global INVERSE
    global current_theme
    INVERSE = False
    current_theme.update(_default_theme)

def set_inverse():
    global INVERSE
    global current_theme
    INVERSE = True
    current_theme.update(_inverse_theme)

def is_inverse(fg, bg):
    """Takes a guess at whether the given foreground and background colours
    represents and inverse theme (light text on a dark background)."""
    # Let's sum the three colour components to work out a rough idea of how
    # "light" the colour is:
    # TODO: consider using luminance calculation instead (probably overkill)
    bg_sum = sum((bg.red, bg.green, bg.blue))
    fg_sum = sum((fg.red, fg.green, fg.blue))
    if bg_sum < fg_sum:
        return True
    else:
        return False

def update_style(widget):
    _style = widget.style
    fg = _style.fg[gtk.STATE_NORMAL]
    bg = _style.base[gtk.STATE_NORMAL]
    if is_inverse(fg, bg):
        set_inverse()
    else:
        set_default()

    # On some themes (notably Windows XP with classic style), diff_delete_bg is
    # almost identical to the background colour used. So we use something from
    # the gtk theme that is supposed to be different, but not much.
    if not has_reasonable_contrast(_style.bg[gtk.STATE_NORMAL], gtk.gdk.color_parse(current_theme['diff_delete_bg'])):
        if INVERSE:
            new_diff_delete_bg =  _style.dark[gtk.STATE_NORMAL]
        else:
            new_diff_delete_bg =  _style.light[gtk.STATE_NORMAL]
        # we only want to change if it will actually result in something readable:
        if has_good_contrast(_style.text[gtk.STATE_NORMAL], new_diff_delete_bg):
            current_theme['diff_delete_bg'] = new_diff_delete_bg.to_string()


# these are based on an (old?) Web Content Accessibility Guidelines of the w3c
# See  http://juicystudio.com/article/luminositycontrastratioalgorithm.php
# TODO: Might be a bit newer/better, so we shuld consider updating the code:
#      http://www.w3.org/TR/WCAG20/Overview.html

def _luminance(c):
    r = pow(c.red/65535.0, 2.2)
    g = pow(c.green/65535.0, 2.2)
    b = pow(c.blue/65535.0, 2.2)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def _luminance_contrast_ratio(c1, c2):
    l1 = _luminance(c1)
    l2 = _luminance(c2)
    l1, l2 = max(l1, l2), min(l1, l2)
    return (l1 + 0.05) / (l2 + 0.05)

def has_good_contrast(c1, c2):
    """Takes a guess at whether the two given colours are in good contrast to
    each other (for example, to be able to be used together as foreground and
    background colour)."""
    return _luminance_contrast_ratio(c1, c2) >= 4.5

def has_reasonable_contrast(c1, c2):
    """Similarly to has_good_contrast() this says whether the two given
    colours have at least a reasonable amount of contrast, so that they would
    be distinguishable."""
    return _luminance_contrast_ratio(c1, c2) >= 1.2
    # constant determined by testing in many themes, Windows XP with "classic"
    # being the edge case

########NEW FILE########
__FILENAME__ = unitview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import logging
import re
from gobject import idle_add, PARAM_READWRITE, SIGNAL_RUN_FIRST, TYPE_PYOBJECT
from translate.lang import factory

from virtaal.common import GObjectWrapper

import rendering
from baseview import BaseView
from widgets.textbox import TextBox
from widgets.listnav import ListNavigator


class UnitView(gtk.EventBox, GObjectWrapper, gtk.CellEditable, BaseView):
    """View for translation units and its actions. It should not be used at
    all when no current unit is being edited. """

    __gtype_name__ = "UnitView"
    __gsignals__ = {
        'delete-text':    (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, TYPE_PYOBJECT, int, int, TYPE_PYOBJECT, int)),
        'insert-text':    (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, int, TYPE_PYOBJECT, int)),
        'paste-start':    (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, TYPE_PYOBJECT, int)),
        'modified':       (SIGNAL_RUN_FIRST, None, ()),
        'unit-done':      (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'targets-created':(SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'sources-created':(SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'target-focused': (SIGNAL_RUN_FIRST, None, (int,)),
        'textview-language-changed': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, TYPE_PYOBJECT)),
    }
    __gproperties__ = {
        'editing-canceled': (bool, 'Editing cancelled', 'Editing was cancelled', False, PARAM_READWRITE),
    }

    first_word_re = re.compile("(?m)(?u)^(<[^>]+>|\\\\[nt]|[\W$^\n])*(\\b|\\Z)")
    """A regular expression to help us find a meaningful place to position the
        cursor initially."""

    MAX_SOURCES = 6
    """The number of text boxes to manage as sources."""
    MAX_TARGETS = 6
    """The number of text boxes to manage as targets."""

    # INITIALIZERS #
    def __init__(self, controller):
        gtk.EventBox.__init__(self)
        GObjectWrapper.__init__(self)

        self.controller = controller
        self._focused_target_n = None
        self.gui = self.load_builder_file(["virtaal", "virtaal.ui"], root='UnitEditor', domain="virtaal")

        self.must_advance = False
        self._modified = False

        self.connect('key-press-event', self._on_key_press_event)
        # We automatically inherrit the tooltip from the Treeview, so we have
        # to show our own custom one to not have a tooltip obscuring things
        invisible_tooltip = gtk.Window(gtk.WINDOW_POPUP)
        invisible_tooltip.resize(1,1)
        invisible_tooltip.set_opacity(0)
        self.set_tooltip_window(invisible_tooltip)
        self.connect('query-tooltip', self._on_query_tooltip)

        self._widgets = {
            'context_info': None,
            'state': None,
            'notes': {},
            'sources': [],
            'targets': []
        }
        self._get_widgets()
        self._widgets['vbox_editor'].reparent(self)
        self._setup_menus()
        self.unit = None

    def _setup_menus(self):
        def get_focused(widgets):
            for textview in widgets:
                if textview.is_focus():
                    return textview
            return None

        clipboard = gtk.Clipboard(selection=gtk.gdk.SELECTION_CLIPBOARD)
        def on_cut(menuitem):
            focused = get_focused(self.targets)
            if focused is not None:
                focused.get_buffer().cut_clipboard(clipboard, True)
        def on_copy(menuitem):
            focused = get_focused(self.targets + self.sources)
            if focused is not None:
                focused.get_buffer().copy_clipboard(clipboard)
        def on_paste(menuitem):
            focused = get_focused(self.targets)
            if focused is not None:
                focused.get_buffer().paste_clipboard(clipboard, None, True)

        maingui = self.controller.main_controller.view.gui
        self.mnu_cut = maingui.get_object('mnu_cut')
        self.mnu_copy = maingui.get_object('mnu_copy')
        self.mnu_paste = maingui.get_object('mnu_paste')

        self.mnu_cut.connect('activate', on_cut)
        self.mnu_copy.connect('activate', on_copy)
        self.mnu_paste.connect('activate', on_paste)

        # And now for the "Transfer from source" and placeable selection menu items
        mnu_next = maingui.get_object('mnu_placnext')
        mnu_prev = maingui.get_object('mnu_placprev')
        mnu_transfer = maingui.get_object('mnu_transfer')
        self.mnu_next = mnu_next
        self.mnu_prev = mnu_prev
        self.mnu_transfer = mnu_transfer
        menu_edit = maingui.get_object('menu_edit')

        def on_next(*args):
            self.targets[self.focused_target_n].move_elem_selection(1)
        def on_prev(*args):
            self.targets[self.focused_target_n].move_elem_selection(-1)
        def on_transfer(*args):
            ev = gtk.gdk.Event(gtk.gdk.KEY_PRESS)
            ev.state = gtk.gdk.MOD1_MASK
            ev.keyval = gtk.keysyms.Down
            ev.window = self.targets[self.focused_target_n].get_window(gtk.TEXT_WINDOW_WIDGET)
            ev.put()
        mnu_next.connect('activate', on_next)
        mnu_prev.connect('activate', on_prev)
        mnu_transfer.connect('activate', on_transfer)

        gtk.accel_map_add_entry("<Virtaal>/Edit/Next Placeable", gtk.keysyms.Right, gtk.gdk.MOD1_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Prev Placeable", gtk.keysyms.Left, gtk.gdk.MOD1_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Transfer", gtk.keysyms.Down, gtk.gdk.MOD1_MASK)

        accel_group = menu_edit.get_accel_group()
        if not accel_group:
            accel_group = gtk.AccelGroup()

        self.controller.main_controller.view.add_accel_group(accel_group)
        menu_edit.set_accel_group(accel_group)
        mnu_next.set_accel_path("<Virtaal>/Edit/Next Placeable")
        mnu_prev.set_accel_path("<Virtaal>/Edit/Prev Placeable")
        mnu_transfer.set_accel_path("<Virtaal>/Edit/Transfer")

        # Disable the menu items to start with, because we can't assume that a
        # store is loaded. See _set_menu_items_sensitive() for more activation.
        self._set_menu_items_sensitive(False)

        def on_store_closed(*args):
            mnu_next.set_sensitive(False)
            mnu_prev.set_sensitive(False)
            mnu_transfer.set_sensitive(False)
            self.mnu_cut.set_sensitive(False)
            self.mnu_copy.set_sensitive(False)
            self.mnu_paste.set_sensitive(False)
        def on_store_loaded(*args):
            mnu_next.set_sensitive(True)
            mnu_prev.set_sensitive(True)
            mnu_transfer.set_sensitive(True)
            self.mnu_cut.set_sensitive(True)
            self.mnu_copy.set_sensitive(True)
            self.mnu_paste.set_sensitive(True)
        self.controller.main_controller.store_controller.connect('store-closed', on_store_closed)
        self.controller.main_controller.store_controller.connect('store-loaded', on_store_loaded)


    # ACCESSORS #
    def is_modified(self):
        return self._modified

    def _get_focused_target_n(self):
        return self._focused_target_n
    def _set_focused_target_n(self, target_n):
        self.focus_text_view(self.targets[target_n])
    focused_target_n = property(_get_focused_target_n, _set_focused_target_n)

    def get_target_n(self, n):
        return self.targets[n].get_text()

    def set_target_n(self, n, newtext, cursor_pos=-1):
        # TODO: Save cursor position and set after assignment
        self.targets[n].set_text(newtext)
        if cursor_pos > -1:
            self.targets[n].buffer.place_cursor(self.targets[n].buffer.get_iter_at_offset(cursor_pos))

    sources = property(lambda self: self._widgets['sources'])
    targets = property(lambda self: self._widgets['targets'])


    # METHODS #
    def copy_original(self, textbox):
        if textbox.selector_textbox is not textbox and \
            textbox.selector_textbox.selected_elem is not None:
            textbox.insert_translation(textbox.selector_textbox.selected_elem)
            textbox.move_elem_selection(1)
            return

        undocontroller = self.controller.main_controller.undo_controller
        lang = factory.getlanguage(self.controller.main_controller.lang_controller.target_lang.code)

        selector_textbox_index = textbox.selector_textboxes.index(textbox.selector_textbox)
        tgt = self.unit.rich_source[selector_textbox_index].copy()
        placeables_controller = self.controller.main_controller.placeables_controller
        parsers = placeables_controller.get_parsers_for_textbox(textbox)
        placeables_controller.apply_parsers(tgt, parsers)
        if textbox.role == 'target':
            for plac in placeables_controller.non_target_placeables:
                tgt.remove_type(plac)
        tgt.prune()

        punctgt = tgt.copy()
        punctgt.map(
            lambda e: e.apply_to_strings(lang.punctranslate),
            lambda e: e.isleaf() and e.istranslatable
        )

        if punctgt != tgt:
            undocontroller.push_current_text(textbox)
            textbox.set_text(tgt)
            tgt = punctgt

        undocontroller.push_current_text(textbox)
        textbox.set_text(tgt)

        textbox.refresh_cursor_pos = self._get_editing_start_pos(textbox.elem)
        textbox.refresh()

        return False

    def do_start_editing(self, *_args):
        """C{gtk.CellEditable.start_editing()}"""
        self.focus_text_view(self.targets[0])

    def do_editing_done(self, *_args):
        pass

    def focus_text_view(self, textbox):
        textbox.grab_focus()

        text = textbox.get_text()
        translation_start = self._get_editing_start_pos(textbox.elem)
        textbox.buffer.place_cursor(textbox.buffer.get_iter_at_offset(translation_start))

        self._focused_target_n = self.targets.index(textbox)
        #logging.debug('emit("target-focused", focused_target_n=%d)' % (self._focused_target_n))
        self.emit('target-focused', self._focused_target_n)

    def load_unit(self, unit):
        """Load a GUI (C{gtk.CellEditable}) for the given unit."""
        assert unit
        if unit is None:
            logging.error("UnitView can't load a None unit")

        if unit is self.unit:
            return

        #logging.debug('emit("unit-done", self.unit=%s)' % (self.unit))
        if self.unit:
            self.emit('unit-done', self.unit)
        for src in self.sources:
            src.select_elem(elem=None)

        self.unit = unit
        self.disable_signals(['modified', 'insert-text', 'delete-text'])
        self._update_editor_gui()
        self.enable_signals(['modified', 'insert-text', 'delete-text'])

        for i in range(len(self.targets)):
            self.targets[i]._source_text = unit.source # FIXME: Find a better way to do this!

        self._modified = False

    def modified(self):
        self._modified = True
        #logging.debug('emit("modified")')
        self.emit('modified')

    def show(self):
        super(UnitView, self).show()

    def update_languages(self):
        srclang = self.controller.main_controller.lang_controller.source_lang.code
        tgtlang = self.controller.main_controller.lang_controller.target_lang.code

        for textview in self.sources:
            self._update_textview_language(textview, srclang)
            textview.modify_font(rendering.get_source_font_description())
            # This causes some problems, so commented out for now
            #textview.get_pango_context().set_font_description(rendering.get_source_font_description())
        for textview in self.targets:
            self._update_textview_language(textview, tgtlang)
            textview.modify_font(rendering.get_target_font_description())
            textview.get_pango_context().set_font_description(rendering.get_target_font_description())

    def _get_editing_start_pos(self, elem):
        if not elem:
            return 0
        translation_start = self.first_word_re.match(unicode(elem)).span()[1]
        start_elem = elem.elem_at_offset(translation_start)
        if not start_elem.iseditable:
            flattened = elem.flatten()
            start_index = flattened.index(start_elem)
            if start_index == len(flattened)-1:
                return len(elem)
            next_elem = flattened[start_index+1]
            return elem.elem_offset(next_elem)
        return translation_start

    def _get_widgets(self):
        """Get the widgets we would like to use from the loaded GtkBuilder XML object."""
        if not getattr(self, '_widgets', None):
            self._widgets = {}

        widget_names = ('vbox_editor', 'vbox_middle', 'vbox_sources', 'vbox_targets', 'vbox_options', 'vbox_right')

        for name in widget_names:
            self._widgets[name] = self.gui.get_object(name)

        self._widgets['vbox_targets'].connect('key-press-event', self._on_key_press_event)

    def _set_menu_items_sensitive(self, sensitive=True):
        for widget in (self.mnu_next, self.mnu_prev, self.mnu_transfer):
            widget.set_sensitive(sensitive)

    def _update_editor_gui(self):
        """Build the default editor with the following components:
            - A C{gtk.TextView} for each source
            - A C{gtk.TextView} for each target
            - A C{ListNavigator} for the unit states
            - A C{gtk.Label} for programmer notes
            - A C{gtk.Label} for translator notes
            - A C{gtk.Label} for context info"""
        # We assume a unit exists, otherwise none of this makes sense:
        self._layout_update_notes('programmer')
        self._layout_update_sources()
        self._layout_update_context_info()
        self._layout_update_targets()
        self._layout_update_notes('translator')
        self._layout_update_states()
        self._set_menu_items_sensitive(True)

    def _update_textview_language(self, text_view, language):
        language = str(language)
        #logging.debug('Updating text view for language %s' % (language))
        text_view.get_pango_context().set_language(rendering.get_language(language))
        self.emit('textview-language-changed', text_view, language)


    # GUI BUILDING CODE #
    def _create_sources(self):
        for i in range(len(self.sources), self.MAX_SOURCES):
            source = self._create_textbox(u'', editable=False, role='source')
            textbox = source.get_child()
            textbox.modify_font(rendering.get_source_font_description())
            self._widgets['vbox_sources'].pack_start(source)
            self.sources.append(textbox)

            # The following fixes a very weird crash (bug #810)
            def ignore_tab(txtbx, event, eventname):
                if event.keyval in (gtk.keysyms.Tab, gtk.keysyms.ISO_Left_Tab):
                    self.focused_target_n = 0
                    return True
            textbox.connect('key-pressed', ignore_tab)

        self.emit('sources-created', self.sources)

    def _create_targets(self):
        def on_textbox_n_press_event(textbox, event, eventname):
            """Handle special keypresses in the textarea."""

        def target_key_press_event(textbox, event, eventname, next_textbox):
            if not eventname:
                return False
            if eventname in  ('enter', 'ctrl-enter', 'ctrl-shift-enter'):
                if next_textbox is not None and next_textbox.props.visible:
                    self.focus_text_view(next_textbox)
                else:
                    if eventname == 'ctrl-enter' and self.unit.STATE:
                        #Ctrl+Enter means additionally advance the unit in the workflow
                        listnav = self._widgets['state']
                        listnav.move_state(1)
                    elif eventname == 'ctrl-shift-enter' and self.unit.STATE:
                        listnav = self._widgets['state']
                        listnav.move_state(-1)
                    # textbox is the last text view in this unit, so we need to move on
                    # to the next one.
                    textbox.parent.parent.emit('key-press-event', event)
                return True

            # Alt-Down
            elif eventname == 'alt-down':
                idle_add(self.copy_original, textbox)
                return True

            # Shift-Tab
            elif eventname == 'shift-tab':
                if self.focused_target_n > 0:
                    self.focused_target_n -= 1
                return True
            # Ctrl-Tab
            elif eventname == 'ctrl-tab':
                self.controller.main_controller.lang_controller.view.focus()
                return True
            # Ctrl-Shift-Tab
            elif eventname == 'ctrl-shift-tab':
                self.controller.main_controller.mode_controller.view.focus()
                return True

            return False

        for i in range(len(self.targets), self.MAX_TARGETS):
            target = self._create_textbox(u'', editable=True, role='target', scroll_policy=gtk.POLICY_AUTOMATIC)
            textbox = target.get_child()
            textbox.modify_font(rendering.get_target_font_description())
            textbox.selector_textboxes = self.sources
            textbox.selector_textbox = self.sources[0]
            textbox.connect('paste-clipboard', self._on_textbox_paste_clipboard, i)
            textbox.connect('text-inserted', self._on_target_insert_text, i)
            textbox.connect('text-deleted', self._on_target_delete_range, i)
            textbox.connect('changed', self._on_target_changed, i)

            self._widgets['vbox_targets'].pack_start(target)
            self.targets.append(textbox)

        for target, next_target in zip(self.targets, self.targets[1:] + [None]):
            target.connect('key-pressed', target_key_press_event, next_target)

        self.emit('targets-created', self.targets)

    def _create_textbox(self, text=u'', editable=True, role=None, scroll_policy=gtk.POLICY_AUTOMATIC):
        textbox = TextBox(self.controller.main_controller, role=role)
        textbox.set_editable(editable)
        textbox.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        textbox.set_border_window_size(gtk.TEXT_WINDOW_TOP, 1)
        textbox.set_left_margin(2)
        textbox.set_right_margin(2)
        textbox.set_text(text or u'')
        textbox.connect('focus-in-event', self._on_textbox_focused)
        textbox.connect('focus-out-event', self._on_textbox_unfocused)

        scrollwnd = gtk.ScrolledWindow()
        scrollwnd.set_policy(gtk.POLICY_NEVER, scroll_policy)
        scrollwnd.set_shadow_type(gtk.SHADOW_IN)
        scrollwnd.add(textbox)

        return scrollwnd

    def _create_workflow_liststore(self):
        workflow = self.controller.current_unit._workflow
        lst = gtk.ListStore(str, object)
        if not workflow:
            return lst
        for state in workflow.states:
            lst.append([state.name, state])
        return lst

    def _layout_update_notes(self, origin):
        if origin not in self._widgets['notes']:
            label = gtk.Label()
            label.set_line_wrap(True)
            label.set_justify(gtk.JUSTIFY_FILL)
            label.set_property('selectable', True)

            self._widgets['vbox_middle'].pack_start(label)
            if origin == 'programmer':
                self._widgets['vbox_middle'].reorder_child(label, 0)
            elif origin == 'translator':
                self._widgets['vbox_middle'].reorder_child(label, 4)

            self._widgets['notes'][origin] = label

        note_text = self.unit.getnotes(origin) or u""

        if origin == "programmer" and len(note_text) < 15 and self.unit is not None and self.unit.getlocations():
            note_text += u"  " + u" ".join(self.unit.getlocations()[:3])

        # FIXME: This is a temporary quick fix (to bug 1145) to ensure that
        # excessive translator comments don't cover the whole display.
        # The labels used for displaying these comments (programmer- as well as
        # translator comments) should be displayed in a scrollable widget with
        # proper size limitations.
        TEXT_LIMIT = 200
        if origin == "translator" and len(note_text) > TEXT_LIMIT:
            note_text = note_text[:TEXT_LIMIT] + '...'

        self._widgets['notes'][origin].set_text(note_text)

        if note_text:
            self._widgets['notes'][origin].show_all()
        else:
            self._widgets['notes'][origin].hide()

    def _layout_update_sources(self):
        num_source_widgets = len(self.sources)

        if num_source_widgets < self.MAX_SOURCES:
            # Technically the condition above will only be True when num_target_widgets == 0, ie.
            # no target text boxes has been created yet.
            self._create_sources()
            num_source_widgets = len(self.sources)

        if self.unit is None:
            if num_source_widgets >= 1:
                # The above condition should *never* be False
                textbox = self.sources[0]
                textbox.set_text(u'')
                textbox.parent.show()
            for i in range(1, num_source_widgets):
                self.sources[i].parent.hide_all()
            return

        num_unit_sources = 1
        if self.unit.hasplural():
            num_unit_sources = len(self.unit.source.strings)

        for i in range(self.MAX_SOURCES):
            if i < num_unit_sources:
                sourcestr = self.unit.rich_source[i]
                self.sources[i].modify_font(rendering.get_source_font_description())
                # FIXME: This modfies the unit's copy - we should not do this
                self.sources[i].set_text(sourcestr)
                self.sources[i].parent.show_all()
                #logging.debug('Showing source #%d: %s' % (i, self.sources[i]))
            else:
                #logging.debug('Hiding source #%d: %s' % (i, self.sources[i]))
                self.sources[i].parent.hide_all()

    def _layout_update_context_info(self):
        if not self._widgets['context_info']:
            label = gtk.Label()
            label.set_line_wrap(True)
            label.set_justify(gtk.JUSTIFY_FILL)
            label.set_property('selectable', True)
            self._widgets['vbox_middle'].pack_start(label)
            self._widgets['vbox_middle'].reorder_child(label, 2)
            self._widgets['context_info'] = label

        if self.unit.getcontext():
            self._widgets['context_info'].show()
            self._widgets['context_info'].set_text(self.unit.getcontext() or u"")
        else:
            self._widgets['context_info'].hide()

    def _layout_update_targets(self):
        num_target_widgets = len(self.targets)

        if num_target_widgets < self.MAX_TARGETS:
            # Technically the condition above will only be True when num_target_widgets == 0, ie.
            # no target text boxes has been created yet.
            self._create_targets()
            num_target_widgets = len(self.targets)

        if self.unit is None:
            if num_target_widgets >= 1:
                # The above condition should *never* be False
                textbox = self.targets[0]
                textbox.set_text(u'')
                textbox.parent.show_all()
            for i in range(1, num_target_widgets):
                self.targets[i].parent.hide_all()
            return

        num_unit_targets = 1
        nplurals = 1
        if self.unit.hasplural():
            num_unit_targets = len(self.unit.target.strings)
            nplurals = self.controller.main_controller.lang_controller.target_lang.nplurals

        visible_sources = [src for src in self.sources if src.props.visible]

        rich_target = self.unit.rich_target
        rich_target_len = len(rich_target)
        for i in range(self.MAX_TARGETS):
            if i < nplurals:
                # plural forms already in file
                targetstr = u''
                if i < rich_target_len and rich_target[i] is not None:
                    targetstr = rich_target[i]
                self.targets[i].modify_font(rendering.get_target_font_description())
                self.targets[i].set_text(targetstr)
                self.targets[i].parent.show_all()
                self.targets[i].selector_textboxes = visible_sources
                self.targets[i].selector_textbox = visible_sources[0]
                #logging.debug('Showing target #%d: %s' % (i, self.targets[i]))
            else:
                # outside plural range
                #logging.debug('Hiding target #%d: %s' % (i, self.targets[i]))
                self.targets[i].parent.hide_all()

    def _layout_update_states(self):
        if not self._widgets['state'] and self.unit.STATE:
            statenav = ListNavigator()
            statenav.set_tooltips_text(
                _("Move one step back in the workflow (Ctrl+Shift+Enter)"), \
                _("Click to move to a specific state in the workflow"), \
                _("Move one step forward in the workflow (Ctrl+Enter)")
            )
            statenav.connect('selection-changed', self._on_state_changed)
            self._widgets['vbox_right'].pack_end(statenav, expand=False, fill=False)
            self._widgets['state'] = statenav

        state_names = self.controller.get_unit_state_names()
        if not state_names or not self.unit.STATE:
            widget = self._widgets['state']
            if widget:
                widget.hide()
            return
        state_name = state_names[self.unit.get_state_id()]

        unselectable = state_names.get(0, None)
        if unselectable:
            unselectable = [unselectable]

        self._widgets['state'].set_model(
            self._create_workflow_liststore(),
            unselectable=unselectable,
            select_name=state_name,
        )
        self._widgets['state'].show_all()

    def update_state(self, newstate):
        """Update it without emitting any signals or recreating anything."""
        self._widgets['state'].select_by_name(newstate)

    # EVENT HANLDERS #
    def _on_state_changed(self, listnav, newstate):
        if self.controller.current_unit._workflow:
            self.controller.set_current_state(newstate, from_user=True)
        self.modified()

    def _on_key_press_event(self, _widget, event, *_args):
        if event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.KP_Enter:
            self.must_advance = True
            # Clear selected elements
            self.editing_done()
            return True
        self.must_advance = False
        return False

    def _on_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return True

    def _on_target_changed(self, buffer, index):
        tgt = self.targets[index]
        nplurals = self.controller.main_controller.lang_controller.target_lang.nplurals
        if tgt.elem is not None:
            rich_target = self.unit.rich_target
            if self.unit.hasplural() and len(rich_target) < nplurals:
                # pad the target with empty strings
                rich_target += (nplurals - len(rich_target)) * [u""]
            rich_target[index] = tgt.elem
            self.unit.rich_target = rich_target
        else:
            newtext = self.get_target_n(index)
            if self.unit.hasplural():
                # FIXME: The following two lines are necessary because self.unit.target always
                # returns a new multistring, so you can't assign to an index directly.
                target = self.unit.target.strings
                if len(target) < nplurals:
                    # pad the target with empty strings
                    target += (nplurals - len(target)) * [u""]
                target[index] = newtext
                self.unit.target = target
            elif index == 0:
                self.unit.target = newtext
            else:
                raise IndexError()

        self.modified()

    def _on_target_insert_text(self, textbox, ins_text, offset, elem, target_num):
        #logging.debug('emit("insert-text", ins_text="%s", offset=%d, elem=%s, target_num=%d)' % (ins_text, offset, repr(elem), target_num))
        self.emit('insert-text', ins_text, offset, elem, target_num)

    def _on_target_delete_range(self, textbox, deleted, parent, offset, cursor_pos, elem, target_num):
        #logging.debug('emit("delete-text", deleted=%s, offset=%d, cursor_pos=%d, elem=%s, target_num=%d)' % (deleted, offset, cursor_pos, repr(elem), target_num))
        self.emit('delete-text', deleted, parent, offset, cursor_pos, elem, target_num)

    def _on_textbox_paste_clipboard(self, textbox, target_num):
        buff = textbox.buffer
        old_text = textbox.get_text()
        ins_iter  = buff.get_iter_at_mark(buff.get_insert())
        selb_iter = buff.get_iter_at_mark(buff.get_selection_bound())

        offsets = {
            'insert_offset': ins_iter.get_offset(),
            'selection_offset': selb_iter.get_offset()
        }

        #logging.debug('emit("paste-start", old_text="%s", offsets=%s, target_num=%d)' % (old_text, offsets, target_num))
        self.emit('paste-start', old_text, offsets, target_num)

    def _on_textbox_focused(self, textbox, event):
        for mnu in (self.mnu_cut, self.mnu_copy, self.mnu_paste):
            mnu.set_sensitive(True)

    def _on_textbox_unfocused(self, textbox, event):
        for mnu in (self.mnu_cut, self.mnu_copy, self.mnu_paste):
            mnu.set_sensitive(False)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk

__all__ = ['pulse']

COL_RED, COL_GREEN, COL_BLUE = range(3)


def pulse_step(widget, steptime, colordiff, stopcolor, component):
    """Performs one step in the fade.
        @param widget: The widget being faded.
        @param steptime: The duration (ms) of this step.
        @param colordiff: Tuple of RGB-deltas to be added to the current
            colour.
        @param stopcolor: Don't queue another iteration if we've reached this,
            our target colour."""
    if len(colordiff) < 3:
        raise ValueError('colordiff does not have all colour deltas')

    col = getattr(widget.style, component)[gtk.STATE_NORMAL]
    modify_func = getattr(widget, 'modify_%s' % (component))

    # Check if col's values have not overshot stopcolor, taking into
    # account the sign of the colordiff element (colordiff[x]/abs(colordiff[x])).
    # FIXME: I'm sure the conditions below have a more mathematically elegant
    # solution, but my brain is too melted at the moment to see it.
    if (colordiff[COL_RED] == 0 or (colordiff[COL_RED] > 0 and col.red+colordiff[COL_RED] >= stopcolor[COL_RED]) or (colordiff[COL_RED] < 0 and col.red+colordiff[COL_RED] <= stopcolor[COL_RED])) and \
            (colordiff[COL_GREEN] == 0 or (colordiff[COL_GREEN] > 0 and col.green+colordiff[COL_GREEN] >= stopcolor[COL_GREEN]) or (colordiff[COL_GREEN] < 0 and col.green+colordiff[COL_GREEN] <= stopcolor[COL_GREEN])) and \
            (colordiff[COL_BLUE] == 0 or (colordiff[COL_BLUE]  > 0 and col.blue+colordiff[COL_BLUE] >= stopcolor[COL_BLUE]) or (colordiff[COL_BLUE] < 0 and col.blue+colordiff[COL_BLUE] <= stopcolor[COL_BLUE])):
        # Pulse overshot, restore stopcolor and end the fade
        col = gtk.gdk.Color(
            red=stopcolor[COL_RED],
            green=stopcolor[COL_GREEN],
            blue=stopcolor[COL_BLUE]
        )
        modify_func(gtk.STATE_NORMAL, col)
        #logging.debug(
        #    'Pulse complete (%d, %d, %d) > (%d, %d, %d)' %
        #    (col.red, col.green, col.blue, stopcolor[COL_RED], stopcolor[COL_GREEN], stopcolor[COL_BLUE])
        #)
        return

    col.red   += colordiff[COL_RED]
    col.green += colordiff[COL_GREEN]
    col.blue  += colordiff[COL_BLUE]

    if col.red == stopcolor[COL_RED] and \
            col.green == stopcolor[COL_GREEN] and \
            col.blue  == stopcolor[COL_BLUE]:
        # Pulse complete
        modify_func(gtk.STATE_NORMAL, col)
        return

    modify_func(gtk.STATE_NORMAL, col)
    gobject.timeout_add(steptime, pulse_step, widget, steptime, colordiff, stopcolor, component)

def pulse(widget, color, fadetime=5000, steptime=10, component='bg'):
    """Fade the background colour of the current widget from the given colour
        back to its original background colour.
        @type  widget: gtk.Widget
        @param widget: The widget to pulse.
        @param color: Tuple of RGB-values.
        @param fadetime: The total duration (in ms) of the fade.
        @param steptime: The number of steps that the fade should be divided
            into."""
    if not isinstance(widget, gtk.Widget):
        raise ValueError('widget is not a GTK widget')

    if not component in ('base', 'bg', 'fg'):
        raise ValueError('"component" must be either "base", "bg" or "fg"')

    modify_func = getattr(widget, 'modify_%s' % (component))

    col = getattr(widget.style, component)[gtk.STATE_NORMAL]
    nsteps = fadetime/steptime
    colordiff = (
        (col.red   - color[COL_RED])   / nsteps,
        (col.green - color[COL_GREEN]) / nsteps,
        (col.blue  - color[COL_BLUE])  / nsteps,
    )
    stopcolor = (col.red, col.green, col.blue)
    #logging.debug(
    #    'Before fade: [widget %s][steptime %d][colordiff %s][stopcolor %s]' %
    #    (widget, steptime, colordiff, stopcolor)
    #)
    pulsecol = gtk.gdk.Color(
        red=color[COL_RED],
        green=color[COL_GREEN],
        blue=color[COL_BLUE]
    )
    modify_func(gtk.STATE_NORMAL, pulsecol)
    gobject.timeout_add(steptime, pulse_step, widget, steptime, colordiff, stopcolor, component)

########NEW FILE########
__FILENAME__ = welcomescreenview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
from gobject import idle_add

from virtaal.common.pan_app import get_abs_data_filename, ui_language
from virtaal.views.widgets.welcomescreen import WelcomeScreen

from baseview import BaseView


class WelcomeScreenView(BaseView):
    """Manages the welcome screen widget."""

    PARENT_VBOX_POSITION = 2
    """Index of the welcome screen in the main VBox."""

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        gui = self.load_builder_file(["virtaal", "virtaal.ui"], root='WelcomeScreen', domain="virtaal")
        self.widget = WelcomeScreen(gui)
        self.parent_widget = self.controller.main_controller.view.gui.get_object('vbox_main')

        self.set_banner()
        self.widget.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.widget.connect('button-clicked', self._on_button_clicked)

    def set_banner(self):
        if ui_language == "ar":
            self.widget.set_banner_image(get_abs_data_filename(['virtaal', 'welcome_screen_banner_ar.png']))
            return
        if self.widget.get_direction() == gtk.TEXT_DIR_RTL:
            self.widget.set_banner_image(get_abs_data_filename(['virtaal', 'welcome_screen_banner_rtl.png']))
        else:
            self.widget.set_banner_image(get_abs_data_filename(['virtaal', 'welcome_screen_banner.png']))


    # METHODS #
    def hide(self):
        self.widget.hide()
        if self.widget.parent is self.parent_widget:
            self.parent_widget.remove(self.widget)

    def show(self):
        if not self.widget.parent:
            self.parent_widget.add(self.widget)
        else:
            self.widget.reparent(self.parent_widget)
        self.parent_widget.child_set_property(self.widget, 'position', self.PARENT_VBOX_POSITION)
        self.parent_widget.child_set_property(self.widget, 'expand', True)

        self.widget.show()

        def calculate_width():
            txt = self.widget.widgets['txt_features']
            expander = txt.parent.parent

            screenwidth = self.widget.get_allocation().width
            col1 = self.widget.widgets['buttons']['open'].parent
            width_col1 = col1.get_allocation().width
            if width_col1 > 0.7 * screenwidth:
                width_col1 = int(0.7 * screenwidth)
                col1.set_size_request(width_col1, -1)
                
            maxwidth = 1.8 * width_col1
            # Preliminary width is the whole_screen - width_col1 - 30
            # The "50" above is just to make sure we don't go under the
            # vertical scroll bar (if it is showing).
            width = screenwidth - width_col1 - 50

            if width > maxwidth:
                width = int(maxwidth)

            txt.set_size_request(width, -1)
        idle_add(calculate_width)

    def update_recent_buttons(self, items):
        # if there are no items (maybe failure in xbel), hide the whole widget
        if not items:
            self.widget.gui.get_object("frame_recent").hide()
        else:
            self.widget.gui.get_object("frame_recent").show_all()

        buttons = [
            self.widget.widgets['buttons']['recent' + str(i)] for i in range(1, self.controller.MAX_RECENT+1)
        ]
        markup = '<span underline="single">%(name)s</span>'

        iconfile = get_abs_data_filename(['icons', 'hicolor', '24x24', 'mimetypes', 'x-translation.png'])
        for i in range(len(items)):
            buttons[i].child.get_children()[0].set_from_file(iconfile)
            name = items[i]['name']
            name = name.replace('&', '&amp;')
            name = name.replace('<', '&lt;')
            buttons[i].child.get_children()[1].set_markup(markup % {'name': name})
            buttons[i].set_tooltip_text(items[i]['uri'])
            buttons[i].props.visible = True
        for i in range(len(items), 5):
            buttons[i].props.visible = False


    # EVENT HANDLERS #
    def _on_button_clicked(self, button, name):
        """This method basically delegates button clicks to controller actions."""
        if name == 'open':
            self.controller.open_file()
        elif name.startswith('recent'):
            n = int(name[len('recent'):])
            self.controller.open_recent(n)
        elif name == 'tutorial':
            self.controller.open_tutorial()
        elif name == 'cheatsheet':
            self.controller.open_cheatsheat()
        else:
            self.controller.try_open_link(name)

########NEW FILE########
__FILENAME__ = aboutdialog
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from virtaal import __version__
from virtaal.common import pan_app
from virtaal.support import openmailto


class AboutDialog(gtk.AboutDialog):
    def __init__(self, parent):
        gtk.AboutDialog.__init__(self)
        self._register_uri_handlers()
        self.set_name("Virtaal")
        self.set_version(__version__.ver)
        self.set_copyright(_(u"Copyright © 2007-2010 Zuza Software Foundation"))
        # l10n: Please retain the literal name "Virtaal", but feel free to
        # additionally transliterate the name and to add a translation of "For Language", which is what the name means.
        self.set_comments(_("Virtaal is a program for doing translation.") + "\n\n" +
            _("The initial focus is on software translation (localization or l10n), but we definitely intend it to be useful as a general purpose tool for Computer Aided Translation (CAT)."))
        self.set_license("""This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Library General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.""")
        self.set_website("http://translate.sourceforge.net/wiki/virtaal/index")
        self.set_website_label(_("Virtaal website"))
        authors = [
                "Friedel Wolff",
                "Wynand Winterbach",
                "Dwayne Bailey",
                "Walter Leibbrandt",
        ]
        if pan_app.ui_language == "ar":
            authors.append(u"علاء عبد الفتاح")
        else:
            authors.append(u"Alaa Abd El Fattah")
        authors.extend([
                "",  # just for spacing
                _("We thank our donors:"),
                _("The International Development Research Centre"),
                "\thttp://idrc.ca/",
                _("Mozilla Corporation"),
                "\thttp://mozilla.com/",
                ])
        self.set_authors(authors)
        # l10n: Rather than translating, fill in the names of the translators
        self.set_translator_credits(_("translator-credits"))
        self.set_icon(parent.get_icon())
        self.set_logo(gtk.gdk.pixbuf_new_from_file(pan_app.get_abs_data_filename(["virtaal", "virtaal_logo.png"])))
        self.set_artists([
                "Heather Bailey",
                ])
        # FIXME entries that we may want to add
        #self.set_documenters()
        self.connect ("response", lambda d, r: d.destroy())
        self.show()

    def on_url(self, dialog, uri, data):
        if data == "mail":
            openmailto.mailto(uri)
        elif data == "url":
            openmailto.open(uri)

    def _register_uri_handlers(self):
        """Register the URL and email handlers

        Use open and mailto from virtaal.support.openmailto
        """
        gtk.about_dialog_set_url_hook(self.on_url, "url")
        gtk.about_dialog_set_email_hook(self.on_url, "mail")

########NEW FILE########
__FILENAME__ = cellrendererwidget
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import pango
from gobject import idle_add, PARAM_READWRITE, SIGNAL_RUN_FIRST, TYPE_PYOBJECT


def flagstr(flags):
    """Create a string-representation for the given flags structure."""
    fset = []
    for f in dir(gtk):
        if not f.startswith('CELL_RENDERER_'):
            continue
        if flags & getattr(gtk, f):
            fset.append(f)
    return '|'.join(fset)


class CellRendererWidget(gtk.GenericCellRenderer):
    __gtype_name__ = 'CellRendererWidget'
    __gproperties__ = {
        'widget': (TYPE_PYOBJECT, 'Widget', 'The column containing the widget to render', PARAM_READWRITE),
    }

    XPAD = 2
    YPAD = 2


    # INITIALIZERS #
    def __init__(self, strfunc, default_width=-1):
        gtk.GenericCellRenderer.__init__(self)

        self.default_width = default_width
        self._editing = False
        self.strfunc = strfunc
        self.widget = None


    # INTERFACE METHODS #
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_get_size(self, widget, cell_area=None):
        #print '%s>> on_get_size()' % (self.strfunc(self.widget))
        # FIXME: This method works fine for unselected cells (rows) and gives the same (wrong) results for selected cells.
        height = width = 0

        if cell_area is not None:
            return self.XPAD, self.YPAD, cell_area.width - 2*self.XPAD, cell_area.height - 2*self.YPAD

        width = widget.get_allocation().width
        if width <= 1:
            width = self.default_width
        layout = self.create_pango_layout(self.strfunc(self.widget), widget, width)
        width, height = layout.get_pixel_size()

        if self.widget:
            w, h = self.widget.size_request()
            width =  max(width,  w)
            height = max(height, h)

        #print 'width %d | height %d | lw %d | lh %d' % (width, height, lw, lh)
        height += self.YPAD * 2
        width  += self.XPAD * 2

        return self.XPAD, self.YPAD, width, height

    def on_render(self, window, widget, bg_area, cell_area, expose_area, flags):
        #print '%s>> on_render(flags=%s)' % (self.strfunc(self.widget), flagstr(flags))
        if flags & gtk.CELL_RENDERER_SELECTED:
            self.props.mode = gtk.CELL_RENDERER_MODE_EDITABLE
            self._start_editing(widget) # FIXME: This is obviously a hack, but what more do you want?
            return True
        self.props.mode = gtk.CELL_RENDERER_MODE_INERT
        xo, yo, w, h = self.get_size(widget, cell_area)
        x = cell_area.x + xo
        layout = self.create_pango_layout(self.strfunc(self.widget), widget, w)
        layout_w, layout_h = layout.get_pixel_size()
        y = cell_area.y + yo + (h-layout_h)/2
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, True, cell_area, widget, '', x, y, layout)

    def on_start_editing(self, event, tree_view, path, bg_area, cell_area, flags):
        #print '%s>> on_start_editing(flags=%s, event=%s)' % (self.strfunc(self.widget), flagstr(flags), event)
        editable = self.widget
        if not isinstance(editable, gtk.CellEditable):
            editable = CellWidget(editable)
        editable.show_all()
        editable.grab_focus()
        return editable

    # METHODS #
    def create_pango_layout(self, string, widget, width):
        font = widget.get_pango_context().get_font_description()
        layout = pango.Layout(widget.get_pango_context())
        layout.set_font_description(font)
        layout.set_wrap(pango.WRAP_WORD_CHAR)
        layout.set_width(width * pango.SCALE)
        layout.set_markup(string)
        # This makes no sense, but mostly has the desired effect to align things correctly for
        # RTL languages which is otherwise incorrect. Untranslated entries is still wrong.
        if widget.get_direction() == gtk.TEXT_DIR_RTL:
            layout.set_alignment(pango.ALIGN_RIGHT)
            layout.set_auto_dir(False)
        return layout

    def _start_editing(self, treeview):
        """Force the cell to enter editing mode by going through the parent
            gtk.TextView."""
        if self._editing:
            return
        self._editing = True

        model, iter = treeview.get_selection().get_selected()
        path = model.get_path(iter)
        col = [c for c in treeview.get_columns() if self in c.get_cell_renderers()]
        if len(col) < 1:
            self._editing = False
            return
        treeview.set_cursor_on_cell(path, col[0], self, True)
        # XXX: Hack to make sure that the lock (_start_editing) is not released before the next on_render() is called.
        def update_lock():
            self._editing = False
        idle_add(update_lock)


class CellWidget(gtk.HBox, gtk.CellEditable):
    __gtype_name__ = 'CellWidget'
    __gsignals__ = {
        'modified': (SIGNAL_RUN_FIRST, None, ())
    }
    __gproperties__ = {
        'editing-canceled': (bool, 'Editing cancelled', 'Editing was cancelled', False, PARAM_READWRITE),
    }

    # INITIALIZERS #
    def __init__(self, *widgets):
        super(CellWidget, self).__init__()
        for w in widgets:
            if w.parent is not None:
                w.parent.remove(w)
            self.pack_start(w)


    # INTERFACE METHODS #
    def do_editing_done(self, *args):
        pass

    def do_remove_widget(self, *args):
        pass

    def do_start_editing(self, *args):
        pass


if __name__ == "__main__":
    class Tree(gtk.TreeView):
        def __init__(self):
            self.store = gtk.ListStore(str, TYPE_PYOBJECT, bool)
            gtk.TreeView.__init__(self)
            self.set_model(self.store)
            self.set_headers_visible(True)

            self.append_column(gtk.TreeViewColumn('First', gtk.CellRendererText(), text=0))
            self.append_column(gtk.TreeViewColumn('Second', CellRendererWidget(lambda widget: '<b>' + widget.get_children()[0].get_label() + '</b>'), widget=1))

        def insert(self, name):
            iter = self.store.append()
            hb = gtk.HBox()
            hb.pack_start(gtk.Button(name))
            lbl = gtk.Label((name + ' ') * 20)
            lbl.set_line_wrap(True)
            hb.pack_start(lbl, expand=False)
            self.store.set(iter, 0, name, 1, hb, 2, True)

    w = gtk.Window()
    w.set_position(gtk.WIN_POS_CENTER)
    w.connect('delete-event', gtk.main_quit)
    t = Tree()
    t.insert('foo')
    t.insert('bar')
    t.insert('baz')
    w.add(t)

    w.show_all()
    gtk.main()

########NEW FILE########
__FILENAME__ = label_expander
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gtk.gdk
import gobject
import pango

from virtaal.views import markup

class LabelExpander(gtk.EventBox):
    __gproperties__ = {
        "expanded": (gobject.TYPE_BOOLEAN,
                     "expanded",
                     "A boolean indicating whether this widget has been expanded to show its contained widget",
                     False,
                     gobject.PARAM_READWRITE),
    }

    def __init__(self, widget, get_text, expanded=False):
        super(LabelExpander, self).__init__()

        label_text = gtk.Label()
        label_text.set_single_line_mode(False)
        label_text.set_line_wrap(True)
        label_text.set_justify(gtk.JUSTIFY_FILL)
        label_text.set_use_markup(True)

        self.label = gtk.EventBox()
        self.label.add(label_text)

        self.widget = widget
        self.get_text = get_text

        self.expanded = expanded

        #self.label.connect('button-release-event', lambda widget, *args: setattr(self, 'expanded', True))

    def do_get_property(self, prop):
        return getattr(self, prop.name)

    def do_set_property(self, prop, value):
        setattr(self, prop.name, value)

    def _get_expanded(self):
        return self.child == self.widget

    def _set_expanded(self, value):
        if self.child != None:
            self.remove(self.child)

        if value:
            self.add(self.widget)
        else:
            self.add(self.label)
            self.label.child.set_markup(markup.markuptext(self.get_text(), fancyspaces=False, markupescapes=False))

        self.child.show()

    expanded = property(_get_expanded, _set_expanded)

########NEW FILE########
__FILENAME__ = langadddialog
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk

from virtaal.common import pan_app
from virtaal.views.baseview import BaseView


class LanguageAddDialog(object):
    """
    Represents and manages an instance of the dialog used for adding a language.
    """

    # INITIALIZERS #
    def __init__(self, parent=None):
        super(LanguageAddDialog, self).__init__()

        self.gui = BaseView.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='LanguageAdder',
            domain='virtaal'
        )

        self._get_widgets()
        if isinstance(parent, gtk.Widget):
            self.dialog.set_transient_for(parent)
            self.dialog.set_icon(parent.get_toplevel().get_icon())

    def _get_widgets(self):
        """Load the GtkBuilder file and get the widgets we would like to use."""
        widget_names = ('btn_add_ok', 'ent_langname', 'ent_langcode', 'sbtn_nplurals', 'ent_plural')

        for name in widget_names:
            setattr(self, name, self.gui.get_object(name))

        self.dialog = self.gui.get_object('LanguageAdder')


    # ACCESSORS #
    def _get_langname(self):
        return self.ent_langname.get_text()
    def _set_langname(self, value):
        self.ent_langname.set_text(value)
    langname = property(_get_langname, _set_langname)

    def _get_langcode(self):
        return self.ent_langcode.get_text()
    def _set_langcode(self, value):
        self.ent_langcode.set_text(value)
    langcode = property(_get_langcode, _set_langcode)

    def _get_nplurals(self):
        return int(self.sbtn_nplurals.get_value())
    def _set_nplurals(self):
        self.sbtn_nplurals.set_value(int(value))
    nplurals = property(_get_nplurals, _set_nplurals)

    def _get_plural(self):
        return self.ent_plural.get_text()
    def _set_plural(self, value):
        self.ent_plural.set_text(value)
    plural = property(_get_plural, _set_plural)


    # METHODS #
    def clear(self):
        for entry in (self.ent_langname, self.ent_langcode, self.ent_plural):
            entry.set_text('')
        self.sbtn_nplurals.set_value(0)

    def run(self, clear=True):
        if clear:
            self.clear()
        response = self.dialog.run() == gtk.RESPONSE_OK
        self.dialog.hide()
        return response

    def check_input_sanity(self):
        # TODO: Add more sanity checks
        code = self.langcode
        try:
            ascii_code = unicode(code, 'ascii')
        except UnicodeDecodeError:
            return _('Language code must be an ASCII string.')

        if len(code) < 2:
            return _('Language code must be at least 2 characters long.')

        return ''

########NEW FILE########
__FILENAME__ = langselectdialog
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk
import locale

from virtaal.common import pan_app
from virtaal.views.baseview import BaseView


class LanguageSelectDialog(object):
    """
    Represents and manages an instance of the dialog used for language-selection.
    """

    # INITIALIZERS #
    def __init__(self, languages, parent=None):
        super(LanguageSelectDialog, self).__init__()

        self.gui = BaseView.load_builder_file(
            ["virtaal", "virtaal.ui"],
            root='LanguageSelector',
            domain='virtaal'
        )

        self._get_widgets()
        self._init_treeviews()
        self.update_languages(languages)

        if isinstance(parent, gtk.Widget):
            self.dialog.set_transient_for(parent)
            self.dialog.set_icon(parent.get_toplevel().get_icon())

    def _get_widgets(self):
        """Load the GtkBuilder file and get the widgets we would like to use."""
        widget_names = ('btn_add', 'btn_cancel', 'btn_ok', 'tvw_sourcelang', 'tvw_targetlang')

        for name in widget_names:
            setattr(self, name, self.gui.get_object(name))

        self.dialog = self.gui.get_object('LanguageSelector')

        self.btn_ok.connect('clicked', lambda *args: self.dialog.response(gtk.RESPONSE_OK))
        self.btn_cancel.connect('clicked', lambda *args: self.dialog.response(gtk.RESPONSE_CANCEL))

    def _init_treeviews(self):
        self.lst_langs_src = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.lst_langs_tgt = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.tvw_sourcelang.set_model(self.lst_langs_src)
        self.tvw_targetlang.set_model(self.lst_langs_tgt)

        def searchfunc(model, column, key, iter):
            if  model.get_value(iter, 0).lower().startswith(key.lower()) or \
                model.get_value(iter, 1).lower().startswith(key.lower()):
                return False
            return True
        self.tvw_sourcelang.set_search_equal_func(searchfunc)
        self.tvw_targetlang.set_search_equal_func(searchfunc)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('Language'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', 0)
        col.set_sort_column_id(0)
        self.tvw_sourcelang.append_column(col)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('Language'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', 0)
        col.set_sort_column_id(0)
        self.tvw_targetlang.append_column(col)

        cell = gtk.CellRendererText()
        #l10n: This is the column heading for the language code
        col = gtk.TreeViewColumn(_('Code'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', 1)
        col.set_sort_column_id(1)
        self.tvw_sourcelang.append_column(col)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('Code'))
        col.pack_start(cell)
        col.add_attribute(cell, 'text', 1)
        col.set_sort_column_id(1)
        self.tvw_targetlang.append_column(col)

        def sortfunc(model, iter1, iter2, col):
            return locale.strcoll(model.get_value(iter1, col), model.get_value(iter2, col))
        self.lst_langs_src.set_sort_func(0, sortfunc, 0)
        self.lst_langs_src.set_sort_func(1, sortfunc, 1)
        self.lst_langs_tgt.set_sort_func(0, sortfunc, 0)
        self.lst_langs_tgt.set_sort_func(1, sortfunc, 1)


    # ACCESSORS #
    def get_selected_source_lang(self):
        model, i = self.tvw_sourcelang.get_selection().get_selected()
        if i is not None and model.iter_is_valid(i):
            return model.get_value(i, 1)
        return ''

    def get_selected_target_lang(self):
        model, i = self.tvw_targetlang.get_selection().get_selected()
        if i is not None and model.iter_is_valid(i):
            return model.get_value(i, 1)
        return ''


    # METHODS #
    def clear_langs(self):
        self.lst_langs_src.clear()
        self.lst_langs_tgt.clear()

    def run(self, srclang, tgtlang):
        self.curr_srclang = srclang
        self.curr_tgtlang = tgtlang

        self._select_lang(self.tvw_sourcelang, srclang)
        self._select_lang(self.tvw_targetlang, tgtlang)

        self.tvw_targetlang.grab_focus()
        response = self.dialog.run() == gtk.RESPONSE_OK
        self.dialog.hide()
        return response

    def update_languages(self, langs):
        selected_srccode = self.get_selected_source_lang()
        selected_tgtcode = self.get_selected_target_lang()

        for lang in langs:
            self.lst_langs_src.append([lang.name, lang.code])
            self.lst_langs_tgt.append([lang.name, lang.code])

        if selected_srccode:
            self._select_lang(self.tvw_sourcelang, selected_srccode)
        else:
            self._select_lang(self.tvw_sourcelang, getattr(self, 'curr_srclang', 'en'))
        if selected_tgtcode:
            self._select_lang(self.tvw_targetlang, selected_tgtcode)
        else:
            self._select_lang(self.tvw_targetlang, getattr(self, 'curr_tgtlang', 'en'))

    def _select_lang(self, treeview, langcode):
        model = treeview.get_model()
        i = model.get_iter_first()
        while i is not None and model.iter_is_valid(i):
            if model.get_value(i, 1) == langcode:
                break
            i = model.iter_next(i)

        if i is None or not model.iter_is_valid(i):
            return

        path = model.get_path(i)
        treeview.get_selection().select_iter(i)
        treeview.scroll_to_cell(path)


########NEW FILE########
__FILENAME__ = listnav
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""
ListNavigator: A composite widget for navigating in a list of "states" by using
"previous" and "next" buttons as well as a pop-up list containing all available
options.
"""

import logging
import gobject, gtk

from popupwidgetbutton import PopupWidgetButton


class ListNavigator(gtk.HBox):
    __gtype_name__ = 'ListNavigator'
    __gsignals__ = {
        'back-clicked':      (gobject.SIGNAL_RUN_FIRST, None, ()),
        'forward-clicked':   (gobject.SIGNAL_RUN_FIRST, None, ()),
        'selection-changed': (gobject.SIGNAL_RUN_FIRST, None, (object,))
    }

    COL_DISPLAY, COL_VALUE = range(2)

    # INITIALIZERS #
    def __init__(self):
        super(ListNavigator, self).__init__()
        self._init_widgets()

    def _init_treeview(self):
        tvw = gtk.TreeView()
        tvw.append_column(gtk.TreeViewColumn(
            "State", gtk.CellRendererText(), text=self.COL_DISPLAY
        ))
        lst = gtk.ListStore(str, object)
        tvw.set_model(lst)
        tvw.set_headers_visible(False)
        tvw.get_selection().connect('changed', self._on_selection_changed)

        return tvw, lst

    def _init_widgets(self):
        # Create widgets
        self.btn_back = gtk.Button()
        self.btn_forward = gtk.Button()
        self.btn_back.add(gtk.Arrow(gtk.ARROW_LEFT, gtk.SHADOW_NONE))
        self.btn_forward.add(gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_NONE))

        self.tvw_items, self.lst_items = self._init_treeview()
        frame = gtk.Frame()
        #frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame.add(self.tvw_items)

        self.btn_popup = PopupWidgetButton(frame, label='(uninitialised)')

        # Connect to signals
        self.btn_back.connect('clicked', self._on_back_clicked)
        self.btn_forward.connect('clicked', self._on_forward_clicked)

        self.btn_popup.connect('key-press-event', self._on_popup_key_press_event)

        # Add widgets to containers
        self.pack_start(self.btn_back,    expand=False, fill=False)
        self.pack_start(self.btn_popup,   expand=True,  fill=True)
        self.pack_start(self.btn_forward, expand=False, fill=False)

    def set_tooltips_text(self, backward, default, forward):
        """Set tooltips for the widgets."""
        self.btn_back.set_tooltip_text(backward)
        self.set_tooltip_text(default)
        self.btn_forward.set_tooltip_text(forward)

    # METHODS #
    def move_state(self, offset):
        # XXX: Adapted from ActivityEntry._on_key_press_event
        #      (from the hamster-applet project)
        model, itr = self.tvw_items.get_selection().get_selected()
        path = model.get_path(itr)
        i = path[0] + offset
        # keep it in the sane borders
        i = min(max(i, 0), len(self.tvw_items.get_model()) - 1)

        _itr = model.get_iter(i)
        selected_name  = model.get_value(itr, self.COL_DISPLAY)
        if selected_name in self.unselectable:
            return

        self.tvw_items.scroll_to_cell(i, use_align=True, row_align=0.4)
        self.tvw_items.set_cursor(i)

    def set_model(self, model, unselectable=None, select_first=True, select_name=None):
        """Set the model for the C{gtk.TreeView} in the pop-up window.
            @type  select_first: bool
            @param select_first: Whether or not the first row should be selected
            @type  select_name: str
            @param select_name: The row with this display value is selected.
                This overrides C{select_first}."""
        if model.get_column_type(self.COL_DISPLAY) != gobject.TYPE_STRING:
            raise ValueError('Column %d does not contain "string" values' % (self.COL_DISPLAY))
        if model.get_column_type(self.COL_VALUE) != gobject.TYPE_PYOBJECT:
            raise ValueError('Column %d does not contain "object" values' % (self.COL_VALUE))

        # we're just initialising, so we don't want listeners to think something really changed
        self._should_emit_changed = False
        self.tvw_items.set_model(model)
        if unselectable:
            self.unselectable = unselectable
        else:
            self.unselectable = []

        select_path = None
        if select_first:
            select_path = 0
        if select_name is not None:
            for row in model:
                if row[self.COL_DISPLAY] == select_name:
                    select_path = row.path[0]
                    self.btn_popup.set_label(select_name)
                    break

        if select_path is not None:
            self.tvw_items.set_cursor(select_path)
            self.tvw_items.scroll_to_cell(select_path, use_align=True, row_align=0.4)
        self._should_emit_changed = True

    def set_parent_window(self, wnd_parent):
        self.btn_popup.popup.set_transient_for(wnd_parent)

    def select_by_name(self, name):
        self._should_emit_changed = False
        for row in self.tvw_items.get_model():
            if row[self.COL_DISPLAY] == name:
                logging.debug('name: %s' % (name))
                self.tvw_items.get_selection().select_iter(row.iter)
                self._should_emit_changed = True
                return

    def select_by_object(self, obj):
        for row in self.tvw_items.get_model():
            if row[self.COL_VALUE] == obj:
                self.tvw_items.get_selection().select_iter(row.iter)
                return


    # EVENT HANDLERS #
    def _on_back_clicked(self, button):
        self.emit('back-clicked')
        self.move_state(-1)

    def _on_forward_clicked(self, button):
        self.emit('forward-clicked')
        self.move_state(1)

    def _on_popup_key_press_event(self, widget, event):
        assert widget is self.btn_popup

        # See virtaal.views.widgets.textbox.TextBox._on_key_pressed for an
        # explanation fo the filter below.
        filtered_state = event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK | gtk.gdk.MOD4_MASK | gtk.gdk.SHIFT_MASK)
        keyval = event.keyval

        if filtered_state == 0:
            # No modifying keys (like Ctrl and Alt) are pressed
            if keyval == gtk.keysyms.Up and self.btn_popup.is_popup_visible:
                self.move_state(-1)
                return True
            elif keyval == gtk.keysyms.Down and self.btn_popup.is_popup_visible:
                self.move_state(1)
                return True

        return False

    def _on_selection_changed(self, selection):
        model, itr = selection.get_selected()
        if not model or not itr:
            return
        selected_name  = model.get_value(itr, self.COL_DISPLAY)
        selected_value = model.get_value(itr, self.COL_VALUE)

        self.btn_popup.set_label(selected_name)

        # If setting to "untranslated" internally (when we don't wan't to emit
        # the changed event), we can allow the unselectable ones, since we are
        # in control:
        if self._should_emit_changed and selected_name in self.unselectable:
            selection.select_iter(model.iter_next(itr))
            return
        # Disable back/forward buttons if the first/last item was selected
        # TODO: disable btn_back if the previous can't be selected (like untranslated)
        isfirst = selected_value == model.get_value(model[0].iter, self.COL_VALUE)
        islast  = selected_value == model.get_value(model[len(model)-1].iter, self.COL_VALUE)
        self.btn_back.set_sensitive(not isfirst)
        self.btn_forward.set_sensitive(not islast)

        if self._should_emit_changed:
            self.emit('selection-changed', selected_value)


if __name__ == '__main__':
    # XXX: Uncomment below to test RTL
    #gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)
    listnav = ListNavigator()

    hb = gtk.HBox()
    hb.pack_start(listnav, expand=False, fill=False)
    vb = gtk.VBox()
    vb.pack_start(hb, expand=False, fill=False)

    wnd = gtk.Window()
    wnd.set_title('List Navigator Test')
    wnd.set_size_request(400, 300)
    wnd.add(vb)
    wnd.connect('destroy', lambda *args: gtk.main_quit())
    listnav.set_parent_window(wnd)

    def on_selection_changed(sender, selected):
        sender.btn_popup.set_label('Item %d' % (selected.i))
    listnav.connect('selection-changed', on_selection_changed)

    def create_test_model():
        class Item(object):
            def __init__(self, i):
                self.i = i
            def __str__(self):
                return '<Item i=%s>' % (self.i)

        lst = gtk.ListStore(str, object)
        for i in range(10):
            lst.append([i, Item(i)])
        return lst
    listnav.set_model(create_test_model())

    wnd.show_all()
    gtk.main()

########NEW FILE########
__FILENAME__ = popupmenubutton
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

# Positioning constants below:
# POS_CENTER_BELOW: Centers the pop-up window below the button (default).
# POS_CENTER_ABOVE: Centers the pop-up window above the button.
# POS_NW_SW: Positions the pop-up window so that its North West (top left)
#            corner is on the South West corner of the button.
# POS_NE_SE: Positions the pop-up window so that its North East (top right)
#            corner is on the South East corner of the button. RTL of POS_NW_SW
# POS_NW_NE: Positions the pop-up window so that its North West (top left)
#            corner is on the North East corner of the button.
# POS_SW_NW: Positions the pop-up window so that its South West (bottom left)
#            corner is on the North West corner of the button.
# POS_SE_NE: Positions the pop-up window so that its South East (bottom right)
#            corner is on the North East corner of the button. RTL of POS_SW_NW
POS_CENTER_BELOW, POS_CENTER_ABOVE, POS_NW_SW, POS_NE_SE, POS_NW_NE, POS_SW_NW, POS_SE_NE = range(7)
# XXX: Add position symbols above as needed and implementation in
#      _update_popup_geometry()

_rtl_pos_map = {
        POS_CENTER_BELOW: POS_CENTER_BELOW,
        POS_CENTER_ABOVE: POS_CENTER_ABOVE,
        POS_SW_NW: POS_SE_NE,
        POS_NW_SW: POS_NE_SE,
}

class PopupMenuButton(gtk.ToggleButton):
    """A toggle button that displays a pop-up menu when clicked."""

    # INITIALIZERS #
    def __init__(self, label=None, menu_pos=POS_SW_NW):
        gtk.ToggleButton.__init__(self, label=label)
        self.set_relief(gtk.RELIEF_NONE)
        self.set_menu(gtk.Menu())

        if self.get_direction() == gtk.TEXT_DIR_LTR:
            self.menu_pos = menu_pos
        else:
            self.menu_pos = _rtl_pos_map.get(menu_pos, POS_SE_NE)

        self.connect('toggled', self._on_toggled)


    # ACCESSORS #
    def set_menu(self, menu):
        if getattr(self, '_menu_selection_done_id', None):
            self.menu.disconnect(self._menu_selection_done_id)
        self.menu = menu
        self._menu_selection_done_id = self.menu.connect('selection-done', self._on_menu_selection_done)

    def _get_text(self):
        return unicode(self.get_label())
    def _set_text(self, value):
        self.set_label(value)
    text = property(_get_text, _set_text)


    # METHODS #
    def _calculate_popup_pos(self, menu):
        menu_width, menu_height = 0, 0
        menu_alloc = menu.get_allocation()
        if menu_alloc.height > 1:
            menu_height = menu_alloc.height
            menu_width = menu_alloc.width
        else:
            menu_width, menu_height = menu.size_request()

        btn_window_xy = self.window.get_origin()
        btn_alloc = self.get_allocation()

        # Default values are POS_SW_NW
        x = btn_window_xy[0] + btn_alloc.x
        y = btn_window_xy[1] + btn_alloc.y - menu_height
        if self.menu_pos == POS_NW_SW:
            y = btn_window_xy[1] + btn_alloc.y + btn_alloc.height
        elif self.menu_pos == POS_NE_SE:
            x -= (menu_width - btn_alloc.width)
            y = btn_window_xy[1] + btn_alloc.y + btn_alloc.height
        elif self.menu_pos == POS_SE_NE:
            x -= (menu_width - btn_alloc.width)
        elif self.menu_pos == POS_NW_NE:
            x += btn_alloc.width
            y = btn_window_xy[1] + btn_alloc.y
        elif self.menu_pos == POS_CENTER_BELOW:
            x -= (menu_width - btn_alloc.width) / 2
        elif self.menu_pos == POS_CENTER_ABOVE:
            x -= (menu_width - btn_alloc.width) / 2
            y = btn_window_xy[1] - menu_height
        return (x, y, True)

    def popdown(self):
        self.menu.popdown()
        return True

    def popup(self):
        self.menu.popup(None, None, self._calculate_popup_pos, 0, 0)


    # EVENT HANDLERS #
    def _on_menu_selection_done(self, menu):
        self.set_active(False)

    def _on_toggled(self, togglebutton):
        assert self is togglebutton

        if self.get_active():
            self.popup()
        else:
            self.popdown()

########NEW FILE########
__FILENAME__ = popupwidgetbutton
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""
PopupWidgetButton: Extends a C{gtk.ToggleButton} to show a given widget in a
pop-up window.
"""

import gtk
from gobject import SIGNAL_RUN_FIRST

# XXX: Kudo's to Toms Bauģis <toms.baugis at gmail.com> who wrote the
#      ActivityEntry widget for the hamster-applet project. A lot of this
#      class's signal handling is based on his example.

# Positioning constants below:
# POS_CENTER_BELOW: Centers the pop-up window below the button (default).
# POS_CENTER_ABOVE: Centers the pop-up window above the button.
# POS_NW_SW: Positions the pop-up window so that its North West (top left)
#            corner is on the South West corner of the button.
# POS_NE_SE: Positions the pop-up window so that its North East (top right)
#            corner is on the South East corner of the button. RTL of POS_NW_SW
# POS_NW_NE: Positions the pop-up window so that its North West (top left)
#            corner is on the North East corner of the button.
# POS_SE_NE: Positions the pop-up window so that its South East (bottom right)
#            corner is on the North East corner of the button.
# POS_SW_NW: Positions the pop-up window so that its South West (bottom left)
#            corner is on the North West corner of the button. RTL of POS_SE_NE

POS_CENTER_BELOW, POS_CENTER_ABOVE, POS_NW_SW, POS_NE_SE, POS_NW_NE, POS_SW_NW, POS_SE_NE = range(7)
# XXX: Add position symbols above as needed and implementation in
#      _update_popup_geometry()

_rtl_pos_map = {
        POS_CENTER_BELOW: POS_CENTER_BELOW,
        POS_CENTER_ABOVE: POS_CENTER_ABOVE,
        POS_SE_NE: POS_SW_NW,
        POS_NW_SW: POS_NE_SE,
}

class PopupWidgetButton(gtk.ToggleButton):
    """Extends a C{gtk.ToggleButton} to show a given widget in a pop-up window."""
    __gtype_name__ = 'PopupWidgetButton'
    __gsignals__ = {
        'shown':  (SIGNAL_RUN_FIRST, None, ()),
        'hidden': (SIGNAL_RUN_FIRST, None, ()),
    }

    # INITIALIZERS #
    def __init__(self, widget, label='Pop-up', popup_pos=POS_NW_SW, main_window=None, sticky=False):
        super(PopupWidgetButton, self).__init__(label=label)
        if not sticky:
            self.connect('focus-out-event', self._on_focus_out_event)
        if main_window:
            main_window.connect('focus-out-event', self._on_focus_out_event)
        self.connect('key-press-event', self._on_key_press_event)
        self.connect('toggled', self._on_toggled)

        if self.get_direction() == gtk.TEXT_DIR_LTR:
            self.popup_pos = popup_pos
        else:
            self.popup_pos = _rtl_pos_map.get(popup_pos, POS_NE_SE)
        self._parent_button_press_id = None
        self._update_popup_geometry_func = None

        # Create pop-up window
        self.popup = gtk.Window(type=gtk.WINDOW_POPUP)
        self.popup.set_size_request(0,0)
        self.popup.add(widget)
        self.popup.show_all()
        self.popup.hide()

        self.connect('expose-event', self._on_expose)


    # ACCESSORS #
    def _get_is_popup_visible(self):
        return self.popup.props.visible
    is_popup_visible = property(_get_is_popup_visible)

    def set_update_popup_geometry_func(self, func):
        self._update_popup_geometry_func = func

    # METHODS #
    def calculate_popup_xy(self, popup_alloc, btn_alloc, btn_window_xy):
        # Default values are POS_NW_SW
        x = btn_window_xy[0] + btn_alloc.x
        y = btn_window_xy[1] + btn_alloc.y + btn_alloc.height
        width, height = self.popup.get_child_requisition()

        if self.popup_pos == POS_NE_SE:
            x -= (popup_alloc.width - btn_alloc.width)
        elif self.popup_pos == POS_NW_NE:
            x += btn_alloc.width
            y = btn_window_xy[1] + btn_alloc.y
        elif self.popup_pos == POS_SE_NE:
            x -= (popup_alloc.width - btn_alloc.width)
            y = btn_window_xy[1] - popup_alloc.height
        elif self.popup_pos == POS_SW_NW:
            y = btn_window_xy[1] - popup_alloc.height
        elif self.popup_pos == POS_CENTER_BELOW:
            x -= (popup_alloc.width - btn_alloc.width) / 2
        elif self.popup_pos == POS_CENTER_ABOVE:
            x -= (popup_alloc.width - btn_alloc.width) / 2
            y = btn_window_xy[1] - popup_alloc.height

        return x, y

    def hide_popup(self):
        self.set_active(False)

    def show_popup(self):
        self.set_active(True)

    def _do_hide_popup(self):
        if self._parent_button_press_id and self.get_toplevel().handler_is_connected(self._parent_button_press_id):
            self.get_toplevel().disconnect(self._parent_button_press_id)
            self._parent_button_press_id = None
        self.popup.hide()
        self.emit('hidden')

    def _do_show_popup(self):
        if not self._parent_button_press_id and self.get_toplevel():
            self._parent_button_press_id = self.get_toplevel().connect('button-press-event', self._on_focus_out_event)
        self.popup.present()
        self._update_popup_geometry()
        self.emit('shown')

    def _update_popup_geometry(self):
        self.popup.set_size_request(-1, -1)
        width, height = self.popup.get_child_requisition()

        x, y = -1, -1
        popup_alloc = self.popup.get_allocation()
        btn_window_xy = self.window.get_origin()
        btn_alloc = self.get_allocation()

        if callable(self._update_popup_geometry_func):
            x, y, new_width, new_height = self._update_popup_geometry_func(
                self.popup, popup_alloc, btn_alloc, btn_window_xy,
                (x, y, width, height)
            )
            if new_width != width or new_height != height:
                width, height = new_width, new_height
                self.popup.set_size_request(width, height)

        popup_alloc.width, popup_alloc.height = width, height
        x, y = self.calculate_popup_xy(popup_alloc, btn_alloc, btn_window_xy)

        self.popup.window.get_toplevel().move_resize(x, y, width, height)


    # EVENT HANDLERS #
    def _on_focus_out_event(self, window, event):
        self.hide_popup()

    def _on_key_press_event(self, window, event):
        if event.keyval == gtk.keysyms.Escape and self.popup.props.visible:
            self.hide_popup()
            return True
        return False

    def _on_toggled(self, button):
        if button.get_active():
            self._do_show_popup()
        else:
            self._do_hide_popup()

    def _on_expose(self, widget, event):
        self._update_popup_geometry()


if __name__ == '__main__':
    btn = PopupWidgetButton(label='TestMe', widget=gtk.Button('Click me'))

    hb = gtk.HBox()
    hb.pack_start(gtk.Button('Left'),  expand=False, fill=False)
    hb.pack_start(btn,                 expand=False, fill=False)
    hb.pack_start(gtk.Button('Right'), expand=False, fill=False)
    vb = gtk.VBox()
    vb.pack_start(hb, expand=False, fill=False)

    from gtk import Window
    wnd = Window()
    wnd.set_size_request(400, 300)
    wnd.set_title('Pop-up Window Button Test')
    wnd.add(vb)
    wnd.connect('destroy', lambda *args: gtk.main_quit())
    wnd.show_all()
    gtk.main()

########NEW FILE########
__FILENAME__ = selectdialog
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
from gobject import SIGNAL_RUN_FIRST, TYPE_PYOBJECT

from virtaal.common import GObjectWrapper

from selectview import SelectView


class SelectDialog(GObjectWrapper):
    """
    A dialog wrapper to easily select items from a list.
    """

    __gtype_name__ = 'SelectDialog'
    __gsignals__ = {
        'item-enabled':   (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'item-disabled':  (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'item-selected':  (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'selection-done': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
    }

    # INITIALIZERS #
    def __init__(self, items=None, title=None, message=None, parent=None, size=None):
        super(SelectDialog, self).__init__()
        self.sview = SelectView(items)
        self._create_gui(title, message, parent)
        self._connect_signals()

        if size and len(size) == 2:
            w, h = -1, -1
            if size[0] > 0:
                w = size[0]
            if size[1] > 0:
                h = size[1]
            self.dialog.set_size_request(w, h)

    def _connect_signals(self):
        self.sview.connect('item-enabled',  self._on_item_enabled)
        self.sview.connect('item-disabled', self._on_item_disabled)
        self.sview.connect('item-selected', self._on_item_selected)

    def _create_gui(self, title, message, parent):
        self.dialog = gtk.Dialog()
        self.dialog.set_modal(True)
        if isinstance(parent, gtk.Widget):
            self.set_transient_for(parent)
        self.dialog.set_title(title is not None and title or 'Select items')
        self.message = gtk.Label(message is not None and message or '')
        self.dialog.child.pack_start(self.message, expand=False, fill=False, padding=10)

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolled_window.add(self.sview)
        self.dialog.child.pack_end(scrolled_window, expand=True, fill=True)
        self.dialog.add_buttons(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)


    # METHODS #
    def get_message(self):
        return self.message.get_text()

    def set_icon(self, icon):
        """Simple proxy method to C{self.dialog.set_icon(icon)}."""
        self.dialog.set_icon(icon)

    def set_message(self, msg):
        self.message.set_text(msg)

    def set_transient_for(self, parent):
        """Simple proxy method to C{self.dialog.set_transient_for(parent)}."""
        self.dialog.set_transient_for(parent)

    def run(self, items=None, parent=None):
        if items is not None:
            self.sview.set_model(items)
        if isinstance(parent, gtk.Widget):
            self.dialog.reparent(parent)
        self.dialog.show_all()
        self.response = self.dialog.run()
        self.dialog.hide()
        self.emit('selection-done', self.sview.get_all_items())
        return self.response


    # EVENT HANDLERS #
    def _on_item_enabled(self, selectview, item):
        self.emit('item-enabled', item)

    def _on_item_disabled(self, selectview, item):
        self.emit('item-disabled', item)

    def _on_item_selected(self, selectview, item):
        self.emit('item-selected', item)

########NEW FILE########
__FILENAME__ = selectview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import locale
from gobject import SIGNAL_RUN_FIRST, TYPE_PYOBJECT

from virtaal.common import GObjectWrapper
from virtaal.views.widgets.cellrendererwidget import CellRendererWidget

__all__ = ['COL_ENABLED', 'COL_NAME', 'COL_DESC', 'COL_DATA', 'COL_WIDGET', 'SelectView']

COL_ENABLED, COL_NAME, COL_DESC, COL_DATA, COL_WIDGET = range(5)


class SelectView(gtk.TreeView, GObjectWrapper):
    """
    A tree view that enables the user to select items from a list.
    """

    __gtype_name__ = 'SelectView'
    __gsignals__ = {
        'item-enabled':  (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'item-disabled': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'item-selected': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
    }

    CONTENT_VBOX = 'vb_content'
    """The name of the C{gtk.VBox} containing the selection items."""

    # INITIALIZERS #
    def __init__(self, items=None, bold_name=True):
        gtk.TreeView.__init__(self)
        GObjectWrapper.__init__(self)

        self.bold_name = bold_name
        self.selected_item = None
        if not items:
            items = gtk.ListStore(bool, str, str, TYPE_PYOBJECT, TYPE_PYOBJECT)
        self.set_model(items)

        self._add_columns()
        self._set_defaults()
        self._connect_events()

    def _add_columns(self):
        cell = gtk.CellRendererToggle()
        cell.connect('toggled', self._on_item_toggled)
        self.select_col = gtk.TreeViewColumn(_('Enabled'), cell, active=COL_ENABLED)
        self.append_column(self.select_col)

        width = self.get_allocation().width
        if width <= 1:
            width = 200 # FIXME: Arbitrary default value

        cell = CellRendererWidget(strfunc=self._get_widget_string, default_width=width)
        self.namedesc_col = gtk.TreeViewColumn(_('Name'), cell, widget=4)
        self.append_column(self.namedesc_col)

    def _connect_events(self):
        self.get_selection().connect('changed', self._on_selection_change)

    def _set_defaults(self):
        self.set_rules_hint(True)


    # METHODS #
    def _create_widget_for_item(self, item):
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        vbox.min_height = 60

        vbox.lbl_name = None
        if 'name' in item and item['name']:
            name = (self.bold_name and '<b>%s</b>' or '%s') % (item['name'])
            lbl = gtk.Label()
            lbl.set_alignment(0, 0)
            lbl.set_text(name)
            lbl.set_use_markup(self.bold_name)
            vbox.pack_start(lbl)
            vbox.lbl_name = lbl

        vbox.lbl_desc = None
        if 'desc' in item and item['desc']:
            lbl = gtk.Label()
            lbl.set_alignment(0, 0)
            lbl.set_line_wrap(True)
            lbl.set_text(item['desc'])
            lbl.set_use_markup(False)
            vbox.pack_start(lbl)
            vbox.lbl_desc = lbl
        hbox.pack_start(vbox)

        #TODO: ideally we need an accesskey, but it is not currently working
        if 'config' in item and callable(item['config']):
            btnconf = gtk.Button(_('Configure...'))
            def clicked(button, event):
                item['config'](self.get_toplevel())
            btnconf.connect('button-release-event', clicked)
            btnconf.config_func = item['config']
            vbox.btn_conf = btnconf
            hbox.pack_start(btnconf, expand=False)

        return hbox

    def _get_widget_string(self, widget):
        s = ''
        widget = widget.get_children()[0]
        if widget.lbl_name:
            s = widget.lbl_name.get_label()
        if widget.lbl_desc:
            # avoid the import of xml.sax.saxutils.escape
            escaped = widget.lbl_desc.get_text().replace(u"&", u"&amp;").replace(u"<", u"&lt;") # & must be first
            s += '\n' + escaped
        return s

    def get_all_items(self):
        if not self._model:
            return None
        return [
            {
                'enabled': row[COL_ENABLED],
                'name':    row[COL_NAME],
                'desc':    row[COL_DESC],
                'data':    row[COL_DATA]
            } for row in self._model
        ]

    def get_item(self, iter):
        if not self._model:
            return None
        if not self._model.iter_is_valid(iter):
            return None

        config = None
        widget = self._model.get_value(iter, COL_WIDGET)
        try:
            if widget:
                widget = widget.get_children()[1]
            if widget:
                config = widget.config_func
        except IndexError:
            pass

        item = {
            'enabled': self._model.get_value(iter, COL_ENABLED),
            'name':    self._model.get_value(iter, COL_NAME),
            'desc':    self._model.get_value(iter, COL_DESC),
            'data':    self._model.get_value(iter, COL_DATA),
        }
        if config:
            item['config'] = config

        return item

    def get_selected_item(self):
        return self.selected_item

    def select_item(self, item):
        if item is None:
            self.get_selection().unselect_all()
            return
        found = False
        itr = self._model.get_iter_first()
        while itr is not None and self._model.iter_is_valid(itr):
            if self.get_item(itr) == item:
                found = True
                break
        if found and itr and self._model.iter_is_valid(itr):
            self.get_selection().select_iter(itr)
            self.selected_item = item
        else:
            self.selected_item = None

    def set_model(self, items):
        if isinstance(items, gtk.ListStore):
            self._model = items
        else:
            self._model = gtk.ListStore(bool, str, str, TYPE_PYOBJECT, TYPE_PYOBJECT)
            items.sort(cmp=locale.strcoll, key=lambda x: x.get('name', ''))
            for row in items:
                self._model.append([
                    row.get('enabled', False),
                    row.get('name', ''),
                    row.get('desc', ''),
                    row.get('data', None),
                    self._create_widget_for_item(row)
                ])

        gtk.TreeView.set_model(self, self._model)


    # EVENT HANDLERS #
    def _on_item_toggled(self, cellr, path):
        iter = self._model.get_iter(path)
        if not iter:
            return
        item_info = self.get_item(iter)
        item_info['enabled'] = not item_info['enabled']
        self._model.set_value(iter, COL_ENABLED, item_info['enabled'])

        if item_info['enabled']:
            self.emit('item-enabled', item_info)
        else:
            self.emit('item-disabled', item_info)

    def _on_selection_change(self, selection):
        model, iter = selection.get_selected()
        if isinstance(model, gtk.TreeIter) and model is self._model and self._model.iter_is_valid(iter):
            self.selected_item = self.get_item(iter)
            self.emit('item-selected', self.selected_item)

########NEW FILE########
__FILENAME__ = storecellrenderer
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gobject
import pango

from translate.lang import factory

from virtaal.common import pan_app
from virtaal.support.simplegeneric import generic
from virtaal.views import markup, rendering
from virtaal.views.theme import current_theme


@generic
def compute_optimal_height(widget, width):
    raise NotImplementedError()

@compute_optimal_height.when_type(gtk.Widget)
def gtk_widget_compute_optimal_height(widget, width):
    pass

@compute_optimal_height.when_type(gtk.Container)
def gtk_container_compute_optimal_height(widget, width):
    if not widget.props.visible:
        return
    for child in widget.get_children():
        compute_optimal_height(child, width)

@compute_optimal_height.when_type(gtk.Table)
def gtk_table_compute_optimal_height(widget, width):
    for child in widget.get_children():
        # width / 2 because we use half of the available width
        compute_optimal_height(child, width / 2)

@compute_optimal_height.when_type(gtk.TextView)
def gtk_textview_compute_optimal_height(widget, width):
    if not widget.props.visible:
        return
    buf = widget.get_buffer()
    # For border calculations, see gtktextview.c:gtk_text_view_size_request in the GTK source
    border = 2 * widget.border_width - 2 * widget.parent.border_width
    if widget.style_get_property("interior-focus"):
        border += 2 * widget.style_get_property("focus-line-width")

    buftext = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
    # A good way to test height estimation is to use it for all units and
    # compare the reserved space to the actual space needed to display a unit.
    # To use height estimation for all units (not just empty units), use:
    #if True:
    if not buftext:
        text = getattr(widget, '_source_text', u"")
        if text:
            lang = factory.getlanguage(pan_app.settings.language["targetlang"])
            buftext = lang.alter_length(text)
            buftext = markup.escape(buftext)

    _w, h = rendering.make_pango_layout(widget, buftext, width - border).get_pixel_size()
    if h == 0:
        # No idea why this bug happens, but it often happens for the first unit
        # directly after the file is opened. For now we try to guess a more
        # useful default than 0. This should look much better than 0, at least.
        h = 28
    parent = widget.parent
    if isinstance(parent, gtk.ScrolledWindow) and parent.get_shadow_type() != gtk.SHADOW_NONE:
        border += 2 * parent.rc_get_style().ythickness
    widget.parent.set_size_request(-1, h + border)

@compute_optimal_height.when_type(gtk.Label)
def gtk_label_compute_optimal_height(widget, width):
    if widget.get_text().strip() == "":
        widget.set_size_request(width, 0)
    else:
        _w, h = rendering.make_pango_layout(widget, widget.get_label(), width).get_pixel_size()
        widget.set_size_request(width, h)


class StoreCellRenderer(gtk.GenericCellRenderer):
    """
    Cell renderer for a unit based on the C{UnitRenderer} class from Virtaal's
    pre-MVC days.
    """

    __gtype_name__ = "StoreCellRenderer"

    __gproperties__ = {
        "unit": (
            object,
            "The unit",
            "The unit that this renderer is currently handling",
            gobject.PARAM_READWRITE
        ),
        "editable": (
            bool,
            "editable",
            "A boolean indicating whether this unit is currently editable",
            False,
            gobject.PARAM_READWRITE
        ),
    }

    __gsignals__ = {
        "editing-done": (
            gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
            (gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN)
        ),
        "modified": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    ROW_PADDING = 10
    """The number of pixels between rows."""

    # INITIALIZERS #
    def __init__(self, view):
        gtk.GenericCellRenderer.__init__(self)
        self.set_property('mode', gtk.CELL_RENDERER_MODE_EDITABLE)
        self.view = view
        self.__unit = None
        self.editable = False
        self.source_layout = None
        self.target_layout = None


    # ACCESSORS #
    def _get_unit(self):
        return self.__unit

    def _set_unit(self, value):
        if value.isfuzzy():
            self.props.cell_background = current_theme['fuzzy_row_bg']
            self.props.cell_background_set = True
        else:
            self.props.cell_background_set = False
        self.__unit = value

    unit = property(_get_unit, _set_unit, None, None)


    # INTERFACE METHODS #
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_get_size(self, widget, _cell_area):
        #TODO: store last unitid and computed dimensions
        width = widget.get_toplevel().get_allocation().width - 32
        if width < -1:
            width = -1
        if self.editable:
            editor = self.view.get_unit_celleditor(self.unit)
            editor.set_size_request(width, -1)
            editor.show()
            compute_optimal_height(editor, width)
            parent_height = widget.get_allocation().height
            if parent_height < -1:
                parent_height = widget.size_request()[1]
            if parent_height > 0:
                self.check_editor_height(editor, width, parent_height)
            _width, height = editor.size_request()
            height += self.ROW_PADDING
        else:
            height = self.compute_cell_height(widget, width)
        #height = min(height, 600)
        y_offset = self.ROW_PADDING / 2
        return 0, y_offset, width, height

    def do_start_editing(self, _event, tree_view, path, _bg_area, cell_area, _flags):
        """Initialize and return the editor widget."""
        editor = self.view.get_unit_celleditor(self.unit)
        editor.set_size_request(cell_area.width, cell_area.height)
        if not getattr(self, '_editor_editing_done_id', None):
            self._editor_editing_done_id = editor.connect("editing-done", self._on_editor_done)
        if not getattr(self, '_editor_modified_id', None):
            self._editor_modified_id = editor.connect("modified", self._on_modified)
        return editor

    def on_render(self, window, widget, _background_area, cell_area, _expose_area, _flags):
        if self.editable:
            return True
        x_offset, y_offset, width, _height = self.do_get_size(widget, cell_area)
        x = cell_area.x + x_offset
        y = cell_area.y + y_offset
        source_x = x
        target_x = x
        if widget.get_direction() == gtk.TEXT_DIR_LTR:
            target_x += width/2
        else:
            source_x += (width/2) + 10
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, False,
                cell_area, widget, '', source_x, y, self.source_layout)
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, False,
                cell_area, widget, '', target_x, y, self.target_layout)


    # METHODS #
    def _get_pango_layout(self, widget, text, width, font_description):
        '''Gets the Pango layout used in the cell in a TreeView widget.'''
        # We can't use widget.get_pango_context() because we'll end up
        # overwriting the language and font settings if we don't have a
        # new one
        layout = pango.Layout(widget.create_pango_context())
        layout.set_font_description(font_description)
        layout.set_wrap(pango.WRAP_WORD_CHAR)
        layout.set_width(width * pango.SCALE)
        #XXX - plurals?
        text = text or u""
        layout.set_markup(markup.markuptext(text))
        return layout

    def compute_cell_height(self, widget, width):
        lang_controller = self.view.controller.main_controller.lang_controller
        srclang = lang_controller.source_lang.code
        tgtlang = lang_controller.target_lang.code
        self.source_layout = self._get_pango_layout(widget, self.unit.source, width / 2,
                rendering.get_source_font_description())
        self.source_layout.get_context().set_language(rendering.get_language(srclang))
        self.target_layout = self._get_pango_layout(widget, self.unit.target, width / 2,
                rendering.get_target_font_description())
        self.target_layout.get_context().set_language(rendering.get_language(tgtlang))
        # This makes no sense, but has the desired effect to align things correctly for
        # both LTR and RTL languages:
        if widget.get_direction() == gtk.TEXT_DIR_RTL:
            self.source_layout.set_alignment(pango.ALIGN_RIGHT)
            self.target_layout.set_alignment(pango.ALIGN_RIGHT)
            self.target_layout.set_auto_dir(False)
        _layout_width, source_height = self.source_layout.get_pixel_size()
        _layout_width, target_height = self.target_layout.get_pixel_size()
        return max(source_height, target_height) + self.ROW_PADDING

    def check_editor_height(self, editor, width, parentheight):
        notesheight = 0

        for note in editor._widgets['notes'].values():
            notesheight += note.size_request()[1]

        maxheight = parentheight - notesheight

        if maxheight < 0:
            return

        visible_textboxes = []
        for textbox in (editor._widgets['sources'] + editor._widgets['targets']):
            if textbox.props.visible:
                visible_textboxes.append(textbox)

        max_tb_height = maxheight / len(visible_textboxes)

        for textbox in visible_textboxes:
            if textbox.props.visible and textbox.parent.size_request()[1] > max_tb_height:
                textbox.parent.set_size_request(-1, max_tb_height)
                #logging.debug('%s.set_size_request(-1, %d)' % (textbox.parent, max_tb_height))


    # EVENT HANDLERS #
    def _on_editor_done(self, editor):
        self.emit("editing-done", editor.get_data("path"), editor.must_advance, editor.is_modified())
        return True

    def _on_modified(self, widget):
        self.emit("modified")

########NEW FILE########
__FILENAME__ = storetreemodel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gobject

from virtaal.views import markup


COLUMN_NOTE, COLUMN_UNIT, COLUMN_EDITABLE = 0, 1, 2

class StoreTreeModel(gtk.GenericTreeModel):
    """Custom C{gtk.TreeModel} adapted from the old C{UnitModel} class."""

    def __init__(self, storemodel):
        gtk.GenericTreeModel.__init__(self)
        self._store = storemodel
        self._store_len = len(storemodel)
        self._current_editable = 0

    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST | gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return 3

    def on_get_column_type(self, index):
        if index == 0:
            return gobject.TYPE_STRING
        elif index == 1:
            return gobject.TYPE_PYOBJECT
        elif index == 2:
            return gobject.TYPE_BOOLEAN

    def on_get_iter(self, path):
        return path[0]

    def on_get_path(self, rowref):
        return (rowref,)

    def on_get_value(self, rowref, column):
        if column <= 1:
            unit = self._store[rowref]
            if column == 0:
                note_text = unit.getnotes()
                if not note_text:
                    locations = unit.getlocations()
                    if locations:
                        note_text = locations[0]
                return markup.markuptext(note_text, fancyspaces=False, markupescapes=False) or None
            else:
                return unit
        else:
            return self._current_editable == rowref

    def on_iter_next(self, rowref):
        if rowref < self._store_len - 1:
            return rowref + 1
        else:
            return None

    def on_iter_children(self, parent):
        if parent == None and self._store_len > 0:
            return 0
        else:
            return None

    def on_iter_has_child(self, rowref):
        return False

    def on_iter_n_children(self, rowref):
        if rowref == None:
            return self._store_len
        else:
            return 0

    def on_iter_nth_child(self, parent, n):
        if parent == None:
            return n
        else:
            return None

    def on_iter_parent(self, child):
        return None

    # Non-model-interface methods

    def set_editable(self, new_path):
        old_path = (self._current_editable,)
        self._current_editable = new_path[0]
        self.row_changed(old_path, self.get_iter(old_path))
        self.row_changed(new_path, self.get_iter(new_path))

    def store_index_to_path(self, store_index):
        return self.on_get_path(store_index)

    def path_to_store_index(self, path):
        return path[0]

########NEW FILE########
__FILENAME__ = storetreeview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import gobject
import logging

from storecellrenderer import StoreCellRenderer
from storetreemodel import COLUMN_NOTE, COLUMN_UNIT, COLUMN_EDITABLE, StoreTreeModel


class StoreTreeView(gtk.TreeView):
    """
    The extended C{gtk.TreeView} we use display our units.
    This class was adapted from the old C{UnitGrid} class.
    """

    __gsignals__ = {
        'modified':(gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    # INITIALIZERS #
    def __init__(self, view):
        self.view = view
        super(StoreTreeView, self).__init__()

        self.set_headers_visible(False)
        #self.set_direction(gtk.TEXT_DIR_LTR)

        self.renderer = self._make_renderer()
        self.append_column(self._make_column(self.renderer))
        self._enable_tooltips()

        self._install_callbacks()

        # This must be changed to a mutex if you ever consider
        # writing multi-threaded code. However, the motivation
        # for this horrid little variable is so dubious that you'd
        # be better off writing better code. I'm sorry to leave it
        # to you.
        self._waiting_for_row_change = 0

    def _enable_tooltips(self):
        if hasattr(self, "set_tooltip_column"):
            self.set_tooltip_column(COLUMN_NOTE)
        self.set_rules_hint(True)

    def _install_callbacks(self):
        self.connect('key-press-event', self._on_key_press)
        self.connect("cursor-changed", self._on_cursor_changed)
        self.connect("button-press-event", self._on_button_press)
        self.connect('focus-in-event', self.on_configure_event)

        # The following connections are necessary, because Gtk+ apparently *only* uses accelerators
        # to add pretty key-bindings next to menu items and does not really care if an accelerator
        # path has a connected handler.
        mainview = self.view.controller.main_controller.view
        mainview.gui.get_object('mnu_up').connect('activate', lambda *args: self._move_up(None, None, None, None))
        mainview.gui.get_object('mnu_down').connect('activate', lambda *args: self._move_down(None, None, None, None))
        mainview.gui.get_object('mnu_pageup').connect('activate', lambda *args: self._move_pgup(None, None, None, None))
        mainview.gui.get_object('mnu_pagedown').connect('activate', lambda *args: self._move_pgdown(None, None, None, None))

    def _make_renderer(self):
        renderer = StoreCellRenderer(self.view)
        renderer.connect("editing-done", self._on_cell_edited, self.get_model())
        renderer.connect("modified", self._on_modified)
        return renderer

    def _make_column(self, renderer):
        column = gtk.TreeViewColumn(None, renderer, unit=COLUMN_UNIT, editable=COLUMN_EDITABLE)
        column.set_expand(True)
        return column


    # METHODS #
    def select_index(self, index):
        """Select the row with the given index."""
        model = self.get_model()
        if not model or not isinstance(model, StoreTreeModel):
            return
        newpath = model.store_index_to_path(index)
        selected = self.get_selection().get_selected()
        selected_path = isinstance(selected[1], gtk.TreeIter) and model.get_path(selected[1]) or None

        if selected[1] is None or (selected_path and selected_path != newpath):
            #logging.debug('select_index()->self.set_cursor(path="%s")' % (newpath))
            # XXX: Both of the "self.set_cursor()" calls below are necessary in
            #      order to have both bug 869 fixed and keep search highlighting
            #      in working order. After exhaustive inspection of the
            #      interaction between emitted signals involved, Friedel and I
            #      still have no idea why exactly it is needed. This just seems
            #      to be the correct GTK black magic incantation to make it
            #      "work".
            self.set_cursor(newpath, self.get_columns()[0], start_editing=True)
            self.get_model().set_editable(newpath)
            def change_cursor():
                self.set_cursor(newpath, self.get_columns()[0], start_editing=True)
                self._waiting_for_row_change -= 1
            self._waiting_for_row_change += 1
            gobject.idle_add(change_cursor, priority=gobject.PRIORITY_DEFAULT_IDLE)

    def set_model(self, storemodel):
        if storemodel:
            model = StoreTreeModel(storemodel)
        else:
            model = gtk.ListStore(object)
        super(StoreTreeView, self).set_model(model)

    def _keyboard_move(self, offset):
        if not self.view.controller.get_store():
            return

        # We don't want to process keyboard move events until we have finished updating
        # the display after a move event. So we use this awful, awful, terrible scheme to
        # keep track of pending draw events. In reality, it should be impossible for
        # self._waiting_for_row_change to be larger than 1, but my superstition led me
        # to be safe about it.
        if self._waiting_for_row_change > 0:
            return True

        try:
            #self._owner.set_statusbar_message(self.document.mode_cursor.move(offset))
            self.view.cursor.move(offset)
        except IndexError:
            pass

        return True

    def _move_up(self, _accel_group, _acceleratable, _keyval, _modifier):
        return self._keyboard_move(-1)

    def _move_down(self, _accel_group, _acceleratable, _keyval, _modifier):
        return self._keyboard_move(1)

    def _move_pgup(self, _accel_group, _acceleratable, _keyval, _modifier):
        return self._keyboard_move(-10)

    def _move_pgdown(self, _accel_group, _acceleratable, _keyval, _modifier):
        return self._keyboard_move(10)


    # EVENT HANDLERS #
    def _on_button_press(self, widget, event):
        # If the event did not happen in the treeview, but in the
        # editing widget, then the event window will not correspond to
        # the treeview's drawing window. This happens when the
        # user clicks on the edit widget. But if this happens, then
        # we don't want anything to happen, so we return True.
        if event.window != widget.get_bin_window():
            return True

        answer = self.get_path_at_pos(int(event.x), int(event.y))
        if answer is None:
            logging.debug("Not path found at (%d,%d)" % (int(event.x), int(event.y)))
            return True

        old_path, _old_column = self.get_cursor()
        path, _column, _x, _y = answer
        if old_path != path:
            index = self.get_model().path_to_store_index(path)
            if index not in self.view.cursor.indices:
                self.view.controller.main_controller.mode_controller.select_default_mode()
            self.view.cursor.index = index

        return True

    def _on_cell_edited(self, _cell, _path_string, must_advance, _modified, _model):
        if must_advance:
            return self._keyboard_move(1)
        return True

    def on_configure_event(self, widget, _event, *_user_args):
        path, column = self.get_cursor()

        self.columns_autosize()
        if path != None:
            cell_area = self.get_cell_area(path, column)
            def do_setcursor():
                self.set_cursor(path, column, start_editing=True)
            gobject.idle_add(do_setcursor)

        return False

    def _on_cursor_changed(self, _treeview):
        path, _column = self.get_cursor()

        index = _treeview.get_model().path_to_store_index(path)
        if index != self.view.cursor.index:
            self.view.cursor.index = index

        # We defer the scrolling until GTK has finished all its current drawing
        # tasks, hence the gobject.idle_add. If we don't wait, then the TreeView
        # draws the editor widget in the wrong position. Presumably GTK issues
        # a redraw event for the editor widget at a given x-y position and then also
        # issues a TreeView scroll; thus, the editor widget gets drawn at the wrong
        # position.
        def do_scroll():
            self.scroll_to_cell(path, self.get_column(0), True, 0.5, 0.0)
            return False

        gobject.idle_add(do_scroll)
        return True

    def _on_key_press(self, _widget, _event, _data=None):
        # The TreeView does interesting things with combos like SHIFT+TAB.
        # So we're going to stop it from doing this.
        return True

    def _on_modified(self, _widget):
        self.emit("modified")
        return True

########NEW FILE########
__FILENAME__ = test_selectdialog
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from selectdialog import SelectDialog


class TestSelectDialog(object):
    """
    Test runner for SelectDialog.
    """

    def __init__(self):
        self.items = (
            {'enabled': True,  'name': 'item1', 'desc': 'desc1'},
            {'enabled': False, 'name': 'item2'                 },
            {'enabled': True,                   'desc': 'desc3'},
            {                  'name': 'item4', 'desc': 'desc4'},
            {'enabled': True,  'name': 'item5', 'desc': ''     },
            {'enabled': False, 'name': '',      'desc': 'desc6'},
        )
        self.dialog = SelectDialog(self.items, title='Test runner', message='Select the items you want:')
        self.dialog.connect('item-enabled',   self._on_dialog_action, 'Enabled')
        self.dialog.connect('item-disabled',  self._on_dialog_action, 'Disabled')
        self.dialog.connect('item-selected',  self._on_dialog_action, 'Selected')
        self.dialog.connect('selection-done', self._on_dialog_action, 'Selection done')

    def run(self):
        self.dialog.run()

    def _on_dialog_action(self, dialog, item, action):
        print '%s: %s' % (action, item)


if __name__ == '__main__':
    runner = TestSelectDialog()
    runner.run()

########NEW FILE########
__FILENAME__ = test_selectview
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from selectview import SelectView


class SelectViewTestWindow(gtk.Window):
    def __init__(self):
        super(SelectViewTestWindow, self).__init__()
        self.connect('destroy', lambda *args: gtk.main_quit())
        self.add(self.create_selectview())

    def create_selectview(self):
        self.items = (
            {'enabled': True,  'name': 'item1', 'desc': 'desc1'},
            {'enabled': False, 'name': 'item2'                 },
            {'enabled': True,                   'desc': 'desc3'},
            {                  'name': 'item4', 'desc': 'desc4'},
            {'enabled': True,  'name': 'item5', 'desc': ''     },
            {'enabled': False, 'name': '',      'desc': 'desc6'},
        )
        self.selectview = SelectView(self.items)
        self.selectview.connect('item-enabled', self._on_item_action, 'enabled')
        self.selectview.connect('item-disabled', self._on_item_action, 'disabled')
        self.selectview.connect('item-selected', self._on_item_action, 'selected')
        return self.selectview


    def _on_item_action(self, sender, item_info, action):
        print 'Item %s: %s' % (action, item_info)


if __name__ == '__main__':
    win = SelectViewTestWindow()
    win.show_all()
    gtk.main()

########NEW FILE########
__FILENAME__ = test_textbox
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk

from textbox import TextBox


class TextWindow(gtk.Window):
    def __init__(self, textbox=None):
        super(TextWindow, self).__init__()
        if textbox is None:
            textbox = TextBox()

        self.vbox = gtk.VBox()
        self.add(self.vbox)

        self.textbox = textbox
        self.vbox.add(textbox)

        self.connect('destroy', lambda *args: gtk.main_quit())
        self.set_size_request(600, 100)


class TestTextBox(object):
    def __init__(self):
        self.window = TextWindow()


if __name__ == '__main__':
    window = TextWindow()
    window.show_all()
    window.textbox.set_text(u'Ģët <a href="http://www.example.com" alt="Ģët &brand;!">&brandLong;</a>')
    gtk.main()

########NEW FILE########
__FILENAME__ = textbox
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
# Copyright 2013 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
from gobject import SIGNAL_RUN_FIRST, SIGNAL_RUN_LAST

from translate.storage.placeables import StringElem, parse as elem_parse
from translate.storage.placeables.terminology import TerminologyPlaceable
from translate.lang import data

from virtaal.views import placeablesguiinfo
from virtaal.views.theme import current_theme


class TextBox(gtk.TextView):
    """
    A C{gtk.TextView} extended to work with our nifty L{StringElem} parsed
    strings.
    """

    __gtype_name__ = 'TextBox'
    __gsignals__ = {
        'element-selected':      (SIGNAL_RUN_FIRST, None, (object,)),
        'key-pressed':           (SIGNAL_RUN_LAST,  bool, (object, str)),
        'refreshed':             (SIGNAL_RUN_FIRST, None, (object,)),
        'text-deleted':          (SIGNAL_RUN_LAST,  bool, (object, object, int, int, object)),
        'text-inserted':         (SIGNAL_RUN_LAST,  bool, (object, int, object)),
        'changed':               (SIGNAL_RUN_LAST, None, ()),
    }

    SPECIAL_KEYS = {
        'alt-down':  [(gtk.keysyms.Down,  gtk.gdk.MOD1_MASK)],
        'alt-left':  [(gtk.keysyms.Left,  gtk.gdk.MOD1_MASK)],
        'alt-right': [(gtk.keysyms.Right, gtk.gdk.MOD1_MASK)],
        'enter':     [(gtk.keysyms.Return, 0), (gtk.keysyms.KP_Enter, 0)],
        'ctrl-enter':[(gtk.keysyms.Return, gtk.gdk.CONTROL_MASK), (gtk.keysyms.KP_Enter, gtk.gdk.CONTROL_MASK)],
        'ctrl-shift-enter':[(gtk.keysyms.Return, gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK), (gtk.keysyms.KP_Enter, gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK)],
        'shift-tab': [(gtk.keysyms.ISO_Left_Tab, gtk.gdk.SHIFT_MASK), (gtk.keysyms.Tab, gtk.gdk.SHIFT_MASK)],
        'ctrl-tab': [(gtk.keysyms.ISO_Left_Tab, gtk.gdk.CONTROL_MASK), (gtk.keysyms.Tab, gtk.gdk.CONTROL_MASK)],
        'ctrl-shift-tab': [(gtk.keysyms.ISO_Left_Tab, gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK), (gtk.keysyms.Tab, gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK)],
    }
    """A table of name-keybinding mappings. The name (key) is passed as the
    second parameter to the 'key-pressed' event."""
    unselectables = [StringElem]
    """A list of classes that should not be selectable with Alt+Left or Alt+Right."""

    # INITIALIZERS #
    def __init__(self, main_controller, text=None, selector_textbox=None, role=None):
        """Constructor.
        @type  main_controller: L{virtaal.controllers.main_controller}
        @param main_controller: The main controller instance.
        @type  text: String
        @param text: The initial text to set in the new text box. Optional.
        @type  selector_textbox: C{TextBox}
        @param selector_textbox: The text box in which placeable selection
            (@see{select_elem}) should happen. Optional."""
        super(TextBox, self).__init__()
        self.buffer = self.get_buffer()
        self.elem = None
        self.main_controller = main_controller
        self.placeables_controller = main_controller.placeables_controller
        self.refresh_actions = []
        self.refresh_cursor_pos = -1
        self.role = role
        self.selector_textbox = selector_textbox or self
        self.selector_textboxes = [selector_textbox or self]
        self.selected_elem = None
        self.selected_elem_index = None
        self._suggestion = None
        self.undo_controller = main_controller.undo_controller

        self.__connect_default_handlers()

        if self.placeables_controller is None or self.undo_controller is None:
            # This should always happen, because the text boxes are created
            # when the unit controller is created, which happens before the
            # creation of the placeables- and undo controllers.
            self.__controller_connect_id = main_controller.connect('controller-registered', self.__on_controller_register)
        if text:
            self.set_text(text)

    def __connect_default_handlers(self):
        self.connect('button-press-event', self._on_event_remove_suggestion)
        self.connect('focus-out-event', self._on_event_remove_suggestion)
        self.connect('key-press-event', self._on_key_pressed)
        self.connect('move-cursor', self._on_event_remove_suggestion)
        self.buffer.connect('insert-text', self._on_insert_text)
        self.buffer.connect('delete-range', self._on_delete_range)
        self.buffer.connect('begin-user-action', self._on_begin_user_action)
        self.buffer.connect('end-user-action', self._on_end_user_action)


    def _get_suggestion(self):
        return self._suggestion
    def _set_suggestion(self, value):
        if value is None:
            self.hide_suggestion()
            self._suggestion = None
            return

        if not (isinstance(value, dict) and \
                'text'   in value and value['text'] and \
                'offset' in value and value['offset'] >= 0):
            raise ValueError('invalid suggestion dictionary: %s' % (value))

        if self.suggestion_is_visible():
            self.suggestion = None
        self._suggestion = value
        self.show_suggestion()
    suggestion = property(_get_suggestion, _set_suggestion)

    # OVERRIDDEN METHODS #
    def get_stringelem(self):
        if self.elem is None:
            return None
        return elem_parse(self.elem, self.placeables_controller.get_parsers_for_textbox(self))

    def get_text(self, start_iter=None, end_iter=None):
        """Return the text rendered in this text box.
            Uses C{gtk.TextBuffer.get_text()}."""
        if isinstance(start_iter, int):
            start_iter = self.buffer.get_iter_at_offset(start_iter)
        if isinstance(end_iter, int):
            end_iter = self.buffer.get_iter_at_offset(end_iter)
        if start_iter is None:
            start_iter = self.buffer.get_start_iter()
        if end_iter is None:
            end_iter = self.buffer.get_end_iter()
        return data.forceunicode(self.buffer.get_text(start_iter, end_iter))

    def set_text(self, text):
        """Set the text rendered in this text box.
            Uses C{gtk.TextBuffer.set_text()}.
            @type  text: str|unicode|L{StringElem}
            @param text: The text to render in this text box."""
        if not isinstance(text, StringElem):
            text = StringElem(text)

        if self.elem is None:
            self.elem = StringElem(u'')

        if text is not self.elem:
            # If text is self.elem, we are busy with a refresh and we should remember the selected element.
            self.selected_elem = None
            self.selected_elem_index = None

            # We have to edit the existing .elem for the sake of the undo controller
            if self.placeables_controller:
                self.elem.sub = [elem_parse(text, self.placeables_controller.get_parsers_for_textbox(self))]
            else:
                self.elem.sub = [text]

        self.update_tree()
        self.emit("changed")


    # METHODS #
    def add_default_gui_info(self, elem):
        """Add default GUI info to string elements in the tree that does not
            have any GUI info.

            Only leaf nodes are (currently) extended with a C{StringElemGUI}
            (or sub-class) instance. Other nodes has C{gui_info} set to C{None}.

            @type  elem: StringElem
            @param elem: The root of the string element tree to add default
                GUI info to.
            """
        if not isinstance(elem, StringElem):
            return

        if not hasattr(elem, 'gui_info') or not elem.gui_info:
            if not self.placeables_controller:
                return
            elem.gui_info = self.placeables_controller.get_gui_info(elem)(elem=elem, textbox=self)

        for sub in elem.sub:
            self.add_default_gui_info(sub)

    def apply_gui_info(self, elem, include_subtree=True, offset=None):
        if getattr(elem, 'gui_info', None):
            if offset is None:
                offset = self.elem.gui_info.index(elem)
            #logging.debug('offset for %s: %d' % (repr(elem), offset))
            if offset >= 0:
                #logging.debug('[%s] at offset %d' % (unicode(elem).encode('utf-8'), offset))
                start_index = offset
                end_index = offset + elem.gui_info.length()
                interval = end_index - start_index
                for tag, tag_start, tag_end in elem.gui_info.create_tags():
                    if tag is None:
                        continue
                    # Calculate tag start and end offsets
                    if tag_start is None:
                        tag_start = 0
                    if tag_end is None:
                        tag_end = end_index
                    if tag_start < 0:
                        tag_start += interval + 1
                    else:
                        tag_start += start_index
                    if tag_end < 0:
                        tag_end += end_index + 1
                    else:
                        tag_end += start_index
                    if tag_start < start_index:
                        tag_start = start_index
                    if tag_end > end_index:
                        tag_end = end_index

                    iters = (
                        self.buffer.get_iter_at_offset(tag_start),
                        self.buffer.get_iter_at_offset(tag_end)
                    )
                    #logging.debug('  Apply tag at interval (%d, %d) [%s]' % (tag_start, tag_end, self.get_text(*iters)))

                    if not include_subtree or \
                            elem.gui_info.fg != placeablesguiinfo.StringElemGUI.fg or \
                            elem.gui_info.bg != placeablesguiinfo.StringElemGUI.bg:
                        self.buffer.get_tag_table().add(tag)
                        self.buffer.apply_tag(tag, iters[0], iters[1])

        if include_subtree:
            for sub, index in elem.gui_info.iter_sub_with_index():
                if isinstance(sub, StringElem):
                    self.apply_gui_info(sub, offset=index+offset)

    def get_cursor_position(self):
        return self.buffer.props.cursor_position

    def hide_suggestion(self):
        if not self.suggestion_is_visible():
            return
        selection = self.buffer.get_selection_bounds()
        if not selection:
            return

        self.buffer.handler_block_by_func(self._on_delete_range)
        self.buffer.delete(*selection)
        self.buffer.handler_unblock_by_func(self._on_delete_range)

    def insert_translation(self, elem):
        selection = self.buffer.get_selection_bounds()
        if selection:
            self.buffer.delete(*selection)

        while gtk.events_pending():
            gtk.main_iteration()

        cursor_pos = self.buffer.props.cursor_position
        widget = elem.gui_info.get_insert_widget()
        if widget:
            def show_widget():
                cursor_iter = self.buffer.get_iter_at_offset(cursor_pos)
                anchor = self.buffer.create_child_anchor(cursor_iter)
                # It is necessary to recreate cursor_iter becuase, for some inexplicable reason,
                # the Gtk guys thought it acceptable to have create_child_anchor() above CHANGE
                # THE PARAMETER ITER'S VALUE! But only in some cases, while the moon is 73.8% full
                # and it's after 16:33. Documenting this is obviously also too much to ask.
                # Nevermind the fact that there isn't simply a gtk.TextBuffer.remove_anchor() method
                # or something similar. Why would you want to remove anything from a TextView that
                # you have added anyway!?
                # It's crap like this that'll make me ditch Gtk.
                cursor_iter = self.buffer.get_iter_at_offset(cursor_pos)
                self.add_child_at_anchor(widget, anchor)
                widget.show_all()
                if callable(getattr(widget, 'inserted', None)):
                    widget.inserted(cursor_iter, anchor)
            # show_widget() must be deferred until the refresh() following this
            # signal's completion. Otherwise the changes made by show_widget()
            # and those made by the refresh() will wage war on each other and
            # leave Virtaal as one of the casualties thereof.
            self.refresh_actions.append(show_widget)
        else:
            translation = elem.translate()
            if isinstance(translation, StringElem):
                self.add_default_gui_info(translation)
                insert_offset = self.elem.gui_info.gui_to_tree_index(cursor_pos)
                self.elem.insert(insert_offset, translation)
                self.elem.prune()

                self.emit('text-inserted', translation, cursor_pos, self.elem)

                if hasattr(translation, 'gui_info'):
                    cursor_pos += translation.gui_info.length()
                else:
                    cursor_pos += len(translation)
            else:
                self.buffer.insert_at_cursor(translation)
                cursor_pos += len(translation)
        self.refresh_cursor_pos = cursor_pos
        self.refresh()

    def move_elem_selection(self, offset):
        direction = offset/abs(offset) # Reduce offset to one of -1, 0 or 1
        st_index = self.selector_textboxes.index(self.selector_textbox)
        st_len = len(self.selector_textboxes)

        if self.selector_textbox.selected_elem_index is None:
            if offset <= 0:
                if offset < 0 and st_len > 1:
                    self.selector_textbox = self.selector_textboxes[(st_index + direction) % st_len]
                self.selector_textbox.select_elem(offset=offset)
            else:
                self.selector_textbox.select_elem(offset=offset-1)
        else:
            self.selector_textbox.select_elem(offset=self.selector_textbox.selected_elem_index + offset)

        if self.selector_textbox.selected_elem_index is None and direction >= 0:
            self.selector_textbox = self.selector_textboxes[(st_index + direction) % st_len]
        self.__color_selector_textboxes()

    def __color_selector_textboxes(self, *args):
        """Put a highlighting border around the current selector text box."""
        if not hasattr(self, 'selector_color'):
            self.selector_color = gtk.gdk.color_parse(current_theme['selector_textbox'])
        if not hasattr(self, 'nonselector_color'):
            self.nonselector_color = self.parent.style.bg[gtk.STATE_NORMAL]

        for selector in self.selector_textboxes:
            if selector is self.selector_textbox:
                selector.parent.modify_bg(gtk.STATE_NORMAL, self.selector_color)
            else:
                selector.parent.modify_bg(gtk.STATE_NORMAL, self.nonselector_color)

    def place_cursor(self, cursor_pos):
        cursor_iter = self.buffer.get_iter_at_offset(cursor_pos)

        if not cursor_iter:
            raise ValueError('Could not get TextIter for position %d (%d)' % (cursor_pos, len(self.get_text())))
        #logging.debug('setting cursor to position %d' % (cursor_pos))
        self.buffer.place_cursor(cursor_iter)
        # Make sure the cursor is visible to reduce jitters (with backspace at
        # the end of a long unit with scrollbar, for example).
        self.scroll_to_iter(cursor_iter, 0.0)

    def refresh(self, preserve_selection=True):
        """Refresh the text box by setting its text to the current text."""
        if not self.props.visible:
            return # Don't refresh if this text box is not going to be seen anyway
        #logging.debug('self.refresh_cursor_pos = %d' % (self.refresh_cursor_pos))
        if self.refresh_cursor_pos < 0:
            self.refresh_cursor_pos = self.buffer.props.cursor_position
        selection = [itr.get_offset() for itr in self.buffer.get_selection_bounds()]

        if self.elem is not None:
            self.elem.prune()
            self.set_text(self.elem)
        else:
            self.set_text(self.get_text())

        if preserve_selection and selection:
            self.buffer.select_range(
                self.buffer.get_iter_at_offset(selection[0]),
                self.buffer.get_iter_at_offset(selection[1]),
            )
        elif self.refresh_cursor_pos >= 0:
            self.place_cursor(self.refresh_cursor_pos)
        self.refresh_cursor_pos = -1

        for action in self.refresh_actions:
            if callable(action):
                action()
        self.refresh_actions = []

        self.emit('refreshed', self.elem)

    def select_elem(self, elem=None, offset=None):
        if elem is not None and offset is not None:
            raise ValueError('Only one of "elem" or "offset" may be specified.')

        if elem is None and offset is None:
            # Clear current selection
            #logging.debug('Clearing selected placeable from %s' % (repr(self)))
            if self.selected_elem is not None:
                #logging.debug('Selected item *was* %s' % (repr(self.selected_elem)))
                self.selected_elem.gui_info = None
                self.add_default_gui_info(self.selected_elem)
                self.selected_elem = None
            self.selected_elem_index = None
            self.emit('element-selected', self.selected_elem)
            return

        filtered_elems = [e for e in self.elem.depth_first() if e.__class__ not in self.unselectables]
        if not filtered_elems:
            return

        if elem is None and offset is not None:
            if self.selected_elem_index is not None and not (0 <= offset < len(filtered_elems)):
                # Clear selection when we go past the first or last placeable
                self.select_elem(None)
                self.apply_gui_info(self.elem)
                return
            return self.select_elem(elem=filtered_elems[offset % len(filtered_elems)])

        if elem not in filtered_elems:
            return

        # Reset the default tag for the previously selected element
        if self.selected_elem is not None:
            self.selected_elem.gui_info = None
            self.add_default_gui_info(self.selected_elem)

        i = 0
        for fe in filtered_elems:
            if fe is elem:
                break
            i += 1
        self.selected_elem_index = i
        self.selected_elem = elem
        #logging.debug('Selected element: %s (%s)' % (repr(self.selected_elem), unicode(self.selected_elem)))
        if not hasattr(elem, 'gui_info') or not elem.gui_info:
            elem.gui_info = placeablesguiinfo.StringElemGUI(elem, self, fg=current_theme['selected_placeable_fg'], bg=current_theme['selected_placeable_bg'])
        else:
            elem.gui_info.fg = current_theme['selected_placeable_fg']
            elem.gui_info.bg = current_theme['selected_placeable_bg']
        self.apply_gui_info(self.elem, include_subtree=False)
        self.apply_gui_info(self.elem)
        self.apply_gui_info(elem, include_subtree=False)
        cursor_offset = self.elem.find(self.selected_elem) + len(self.selected_elem)
        self.place_cursor(cursor_offset)
        self.emit('element-selected', self.selected_elem)

    def show_suggestion(self, suggestion=None):
        if isinstance(suggestion, dict):
            self.suggestion = suggestion
        if self.suggestion is None:
            return
        iters = (self.buffer.get_iter_at_offset(self.suggestion['offset']),)
        self.buffer.handler_block_by_func(self._on_insert_text)
        self.buffer.insert(iters[0], self.suggestion['text'])
        self.buffer.handler_unblock_by_func(self._on_insert_text)
        iters = (
            self.buffer.get_iter_at_offset(self.suggestion['offset']),
            self.buffer.get_iter_at_offset(
                self.suggestion['offset'] + len(self.suggestion['text'])
            )
        )
        self.buffer.select_range(*iters)

    def suggestion_is_visible(self):
        """Checks whether the current text suggestion is visible."""
        selection = self.buffer.get_selection_bounds()
        if not selection or self.suggestion is None:
            return False
        start_offset = selection[0].get_offset()
        text = self.buffer.get_text(*selection)
        return self.suggestion['text'] and \
                self.suggestion['text'] == text and \
                self.suggestion['offset'] >= 0 and \
                self.suggestion['offset'] == start_offset

    def update_tree(self):
        if not self.placeables_controller:
            return
        if self.elem is None:
            self.elem = StringElem(u'')

        self.add_default_gui_info(self.elem)

        self.buffer.handler_block_by_func(self._on_delete_range)
        self.buffer.handler_block_by_func(self._on_insert_text)
        self.elem.gui_info.render()
        self.show_suggestion()
        self.buffer.handler_unblock_by_func(self._on_delete_range)
        self.buffer.handler_unblock_by_func(self._on_insert_text)

        tagtable = self.buffer.get_tag_table()
        def remtag(tag, data):
            tagtable.remove(tag)
        # FIXME: The following line caused the program to segfault, so it's removed (for now).
        #tagtable.foreach(remtag)
        # At this point we have a tree of string elements with GUI info.
        self.apply_gui_info(self.elem)


    # EVENT HANDLERS #
    def __on_controller_register(self, main_controller, controller):
        if controller is main_controller.placeables_controller:
            self.placeables_controller = controller
        elif controller is main_controller.undo_controller:
            self.undo_controller = controller

        if self.placeables_controller is not None and \
                self.undo_controller is not None:
            main_controller.disconnect(self.__controller_connect_id)

    def _on_begin_user_action(self, buffer):
        if not self.undo_controller:
            # Maybe not ready yet, so we'll loose a bit of undo data
            return
        if not self.undo_controller.model.recording:
            self.undo_controller.record_start()

    def _on_end_user_action(self, buffer):
        if not self.undo_controller:
            return
        if self.undo_controller.model.recording:
            self.undo_controller.record_stop()
        self.refresh()

    def _on_delete_range(self, buffer, start_iter, end_iter):
        if self.elem is None:
            return

        cursor_pos = self.refresh_cursor_pos
        if cursor_pos < 0:
            cursor_pos = self.buffer.props.cursor_position

        start_offset = start_iter.get_offset()
        end_offset = end_iter.get_offset()

        start_elem = self.elem.gui_info.elem_at_offset(start_offset)
        if start_elem is None:
            return
        start_elem_len = start_elem.gui_info.length()
        start_elem_offset = self.elem.gui_info.index(start_elem)

        end_elem = self.elem.gui_info.elem_at_offset(end_offset)
        if end_elem is not None:
            # end_elem can be None if end_offset == self.elem.gui_info.length()
            end_elem_len = end_elem.gui_info.length()
            end_elem_offset = self.elem.gui_info.index(end_elem)
        else:
            end_elem_len = 0
            end_elem_offset = self.elem.gui_info.length()

        #logging.debug('pre-checks: %s[%d:%d]' % (repr(self.elem), start_offset, end_offset))
        #logging.debug('start_elem_offset= %d\tend_elem_offset= %d' % (start_elem_offset, end_elem_offset))
        #logging.debug('start_elem_len   = %d\tend_elem_len   = %d' % (start_elem_len, end_elem_len))
        #logging.debug('start_offset     = %d\tend_offset     = %d' % (start_offset, end_offset))

        # Per definition of a selection, cursor_pos must be at either
        # start_offset or end_offset
        key_is_delete = cursor_pos == start_offset
        done = False

        deleted, parent, index = None, None, None

        if abs(start_offset - end_offset) == 1:
            position = None
            #################################
            #  Placeable:  |<<|content|>>|  #
            #  Cursor:     a  b       c  d  #
            #===============================#
            #           Editable            #
            #===============================#
            #   |  Backspace  |  Delete     #
            #---|-------------|-------------#
            # a |  N/A        |  Placeable  #
            # b |  Nothing    | @Delete "c" #
            # c | @Delete "t" |  Nothing    #
            # d |  Placeable  |  N/A        #
            #===============================#
            #         Non-Editable          #
            #===============================#
            # a |  N/A        |  Placeable  #
            # b | *Nothing    | *Nothing    #
            # c | *Nothing    | *Nothing    #
            # d |  Placeable  |  N/A        #
            #################################
            # The table above specifies what should be deleted for editable and
            # non-editable placeables when the cursor is at a specific boundry
            # position (a, b, c, d) and a specified key is pressed (backspace or
            # delete). Without widgets, positions b and c fall away.
            #
            # @ It is unnecessary to handle these cases, as long as control drops
            #   through to a place where it is handled below.
            # * Or "Placeable" depending on the value of the XXX flag in the
            #   placeable's GUI info object

            # First we check if we fall in any of the situations represented by
            # the table above.
            has_start_widget = has_end_widget = False
            if hasattr(start_elem, 'gui_info'):
                has_start_widget = start_elem.gui_info.has_start_widget()
                has_end_widget   = start_elem.gui_info.has_end_widget()

            if cursor_pos == start_elem_offset:
                position = 'a'
            elif has_start_widget and cursor_pos == start_elem_offset+1:
                position = 'b'
            elif has_end_widget and cursor_pos == start_elem_offset + start_elem_len - 1:
                position = 'c'
            elif cursor_pos == start_elem_offset + start_elem_len:
                position = 'd'

            # If the current state is in the table, handle it
            if position:
                #logging.debug('(a)<<(b)content(c)>>(d)   pos=%s' % (position))
                if (position == 'a' and not key_is_delete) or (position == 'd' and key_is_delete):
                    # "N/A" fields in table
                    pass
                elif (position == 'a' and key_is_delete) or (position == 'd' and not key_is_delete):
                    # "Placeable" fields
                    if (position == 'a' and (has_start_widget or not start_elem.iseditable)) or \
                            (position == 'd' and (has_end_widget or not start_elem.iseditable)):
                        deleted = start_elem.copy()
                        parent = self.elem.get_parent_elem(start_elem)
                        index = parent.elem_offset(start_elem)
                        self.elem.delete_elem(start_elem)

                        self.refresh_cursor_pos = start_elem_offset
                        start_offset = start_elem_offset
                        end_offset = start_elem_offset + start_elem_len
                        done = True
                elif not start_elem.iseditable and position in ('b', 'c'):
                    # "*Nothing" fields
                    if start_elem.isfragile:
                        deleted = start_elem.copy()
                        parent = self.elem.get_parent_elem(start_elem)
                        index = parent.elem_offset(start_elem)
                        self.elem.delete_elem(start_elem)

                        self.refresh_cursor_pos = start_elem_offset
                        start_offset = start_elem_offset
                        end_offset = start_elem_offset + start_elem_len
                    done = True
                # At this point we have checked for all cases except where
                # position in ('b', 'c') for editable elements.
                elif (position == 'c' and not key_is_delete) or (position == 'b' and key_is_delete):
                    # '@Delete "t"' and '@Delete "c"' fields; handled normally below
                    pass
                elif (position == 'b' and not key_is_delete) or (position == 'c' and key_is_delete):
                    done = True
                else:
                    raise Exception('Unreachable code reached. Please close the black hole nearby.')

        #logging.debug('%s[%d] >===> %s[%d]' % (repr(start_elem), start_offset, repr(end_elem), end_offset))

        if not done:
            start_tree_offset = self.elem.gui_info.gui_to_tree_index(start_offset)
            end_tree_offset = self.elem.gui_info.gui_to_tree_index(end_offset)
            deleted, parent, index = self.elem.delete_range(start_tree_offset, end_tree_offset)

            if index is not None:
                parent_offset = self.elem.elem_offset(parent)
                if parent_offset < 0:
                    parent_offset = 0
                self.refresh_cursor_pos = start_offset
                index = parent_offset + index
            else:
                self.refresh_cursor_pos = self.elem.gui_info.tree_to_gui_index(start_offset)

        if index is None:
            index = start_offset

        if deleted:
            self.elem.prune()
            self.emit(
                'text-deleted', deleted, parent, index,
                self.buffer.props.cursor_position, self.elem
            )

    def _on_insert_text(self, buffer, iter, ins_text, length):
        if self.elem is None:
            return

        ins_text = data.forceunicode(ins_text[:length])
        buff_offset = iter.get_offset()
        gui_info = self.elem.gui_info
        left = gui_info.elem_at_offset(buff_offset-1)
        right = gui_info.elem_at_offset(buff_offset)

        #logging.debug('"%s[[%s]]%s" | elem=%s[%d] | left=%s right=%s' % (
        #    buffer.get_text(buffer.get_start_iter(), iter),
        #    ins_text,
        #    buffer.get_text(iter, buffer.get_end_iter()),
        #    repr(self.elem), buff_offset,
        #    repr(left), repr(right)
        #))

        succeeded = False
        if not (left is None and right is None) and (left is not right or not unicode(left)):
            succeeded = self.elem.insert_between(left, right, ins_text)
            #logging.debug('self.elem.insert_between(%s, %s, "%s"): %s' % (repr(left), repr(right), ins_text, succeeded))
        if not succeeded and left is not None and left is right and left.isleaf():
            # This block handles the special case where a the cursor is just
            # inside a leaf element with a closing widget. In this case both
            # left and right will point to the element in question, but it
            # need not be empty to be a leaf. Because the cursor is still
            # "inside" the element, we want to append to this leaf in stead
            # of after it, which is what StringElem.insert() will do, seeing
            # as the position before and after the widget is the same to in
            # the context of StringElem.
            anchor = iter.get_child_anchor()
            if anchor:
                widgets = anchor.get_widgets()
                left_widgets = left.gui_info.widgets
                if len(widgets) > 0 and len(left_widgets) > 1 and \
                        widgets[0] is left_widgets[1] and \
                        iter.get_offset() == self.elem.gui_info.length() - 1:
                    succeeded = left.insert(len(left), ins_text)
                    #logging.debug('%s.insert(len(%s), "%s")' % (repr(left), repr(left), ins_text))
        if not succeeded:
            offset = gui_info.gui_to_tree_index(buff_offset)
            succeeded = self.elem.insert(offset, ins_text)
            #logging.debug('self.elem.insert(%d, "%s"): %s' % (offset, ins_text, succeeded))

        if succeeded:
            self.elem.prune()
            cursor_pos = self.refresh_cursor_pos
            if cursor_pos < 0:
                cursor_pos = self.buffer.props.cursor_position
            cursor_pos += len(ins_text)
            self.refresh_cursor_pos = cursor_pos
            #logging.debug('text-inserted: %s@%d of %s' % (ins_text, iter.get_offset(), repr(self.elem)))
            self.emit('text-inserted', ins_text, buff_offset, self.elem)

    def _on_key_pressed(self, widget, event, *args):
        evname = None

        if self.suggestion_is_visible():
            if event.keyval == gtk.keysyms.Tab:
                self.hide_suggestion()
                self.buffer.insert(
                    self.buffer.get_iter_at_offset(self.suggestion['offset']),
                    self.suggestion['text']
                )
                self.suggestion = None
                self.emit("changed")
                return True
            self.suggestion = None

        # Uncomment the following block to get nice textual logging of key presses in the textbox
        #keyname = '<unknown>'
        #for attr in dir(gtk.keysyms):
        #    if getattr(gtk.keysyms, attr) == event.keyval:
        #        keyname = attr
        #statenames = []
        #for attr in [a for a in ('MOD1_MASK', 'MOD2_MASK', 'MOD3_MASK', 'MOD4_MASK', 'MOD5_MASK', 'CONTROL_MASK', 'SHIFT_MASK', 'RELEASE_MASK', 'LOCK_MASK', 'SUPER_MASK', 'HYPER_MASK', 'META_MASK')]:
        #    if event.state & getattr(gtk.gdk, attr):
        #        statenames.append(attr)
        #statenames = '|'.join(statenames)
        #logging.debug('Key pressed: %s (%s)' % (keyname, statenames))
        #logging.debug('state (raw): %x' % (event.state,))

        # Filter out unimportant flags that is present with other keyboard
        # layouts and input methods. The following has been encountered:
        # * MOD2_MASK - Num Lock (bug 926)
        # * LEAVE_NOTIFY_MASK - Arabic keyboard layout (?) (bug 926)
        # * 0x2000000 - IBus input method (bug 1281)
        filtered_state = event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK | gtk.gdk.MOD4_MASK | gtk.gdk.SHIFT_MASK)

        for name, keyslist in self.SPECIAL_KEYS.items():
            for keyval, state in keyslist:
                if event.keyval == keyval and filtered_state == state:
                    evname = name

        return self.emit('key-pressed', event, evname)

    def _on_event_remove_suggestion(self, *args):
        self.suggestion = None


    # SPECIAL METHODS #
    def __repr__(self):
        return '<TextBox %x %s "%s">' % (id(self), self.role, unicode(self.elem))

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

__all__ = ['forall_widgets']

import gtk

from virtaal.support.simplegeneric import generic


@generic
def get_children(widget):
    return []

@get_children.when_type(gtk.Container)
def get_children_container(widget):
    return widget.get_children()

def forall_widgets(f, widget):
    f(widget)
    for child in get_children(widget):
        forall_widgets(f, child)


########NEW FILE########
__FILENAME__ = welcomescreen
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
from gobject import SIGNAL_RUN_FIRST

from virtaal.views.theme import current_theme

class WelcomeScreen(gtk.ScrolledWindow):
    """
    The scrolled window that contains the welcome screen container widget.
    """

    __gtype_name__ = 'WelcomeScreen'
    __gsignals__ = { 'button-clicked': (SIGNAL_RUN_FIRST, None, (str,)) }


    # INITIALISERS #
    def __init__(self, gui):
        """Constructor.
            @type  gui: C{gtk.Builder}
            @param gui: The GtkBuilder XML object to retrieve the welcome screen from."""
        super(WelcomeScreen, self).__init__()

        self.gui = gui

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        win = gui.get_object('WelcomeScreen')
        if not win:
            raise ValueError('Welcome screen not found in GtkBuikder object.')
        child = win.child
        win.remove(child)
        self.add_with_viewport(child)

        self._get_widgets()
        self._init_feature_view()

    def _get_widgets(self):
        self.widgets = {}
        widget_names = ('img_banner', 'exp_features', 'txt_features')
        for wname in widget_names:
            self.widgets[wname] = self.gui.get_object(wname)

        self.widgets['buttons'] = {}
        button_names = (
            'open', 'recent1', 'recent2', 'recent3', 'recent4', 'recent5',
            'tutorial', 'cheatsheet', 'features_more', 'manual', 'locguide',
            'feedback'
        )
        for bname in button_names:
            btn = self.gui.get_object('btn_' + bname)
            self.widgets['buttons'][bname] = btn
            btn.connect('clicked', self._on_button_clicked, bname)


    def _style_widgets(self):
        url_fg_color = gtk.gdk.color_parse(current_theme['url_fg'])

        for s in [gtk.STATE_ACTIVE, gtk.STATE_NORMAL, gtk.STATE_SELECTED]:
            self.widgets['exp_features'].get_children()[1].modify_fg(s, url_fg_color)

        # Find a gtk.Label as a child of the button...
        for btn in self.widgets['buttons'].values():
            label = None
            if isinstance(btn.child, gtk.Label):
                label = btn.child
            else:
                for widget in btn.child.get_children():
                    if isinstance(widget, gtk.Label):
                        label = widget
                        break
            if label:
                for s in [gtk.STATE_ACTIVE, gtk.STATE_NORMAL, gtk.STATE_SELECTED]:
                    label.modify_fg(s, url_fg_color)

    def _init_feature_view(self):
        features = u"\n".join([
            u" • " + _("Translation memory"),
            u" • " + _("Terminology assistance"),
            u" • " + _("Quality checks"),
            u" • " + _("Machine translation"),
            u" • " + _("Highlighting and insertion of placeables"),
            u" • " + _("Many plugins and options for customization"),
        ])
        self.widgets['txt_features'].get_buffer().set_text(features)


    # METHODS #
    def set_banner_image(self, filename):
        self.widgets['img_banner'].set_from_file(filename)


    # SIGNAL HANDLERS #
    def _on_button_clicked(self, button, name):
        self.emit('button-clicked', name)

    def do_style_set(self, previous_style):
        self.child.modify_bg(gtk.STATE_NORMAL, self.style.base[gtk.STATE_NORMAL])
        self._style_widgets()

########NEW FILE########
__FILENAME__ = __version__
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""This file contains the version."""
ver = "1.0.0-beta1"

########NEW FILE########
