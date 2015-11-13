__FILENAME__ = docopt
"""Pythonic command-line interface parser that will make you smile.

 * http://docopt.org
 * Repository and issue-tracker: https://github.com/docopt/docopt
 * Licensed under terms of MIT license (see LICENSE-MIT)
 * Copyright (c) 2013 Vladimir Keleshev, vladimir@keleshev.com

"""
import sys
import re


__all__ = ['docopt']
__version__ = '0.6.1'


class DocoptLanguageError(Exception):

    """Error in construction of usage-message by developer."""


class DocoptExit(SystemExit):

    """Exit in case user invoked program with incorrect arguments."""

    usage = ''

    def __init__(self, message=''):
        SystemExit.__init__(self, (message + '\n' + self.usage).strip())


class Pattern(object):

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))

    def fix(self):
        self.fix_identities()
        self.fix_repeating_arguments()
        return self

    def fix_identities(self, uniq=None):
        """Make pattern-tree tips point to same object if they are equal."""
        if not hasattr(self, 'children'):
            return self
        uniq = list(set(self.flat())) if uniq is None else uniq
        for i, child in enumerate(self.children):
            if not hasattr(child, 'children'):
                assert child in uniq
                self.children[i] = uniq[uniq.index(child)]
            else:
                child.fix_identities(uniq)

    def fix_repeating_arguments(self):
        """Fix elements that should accumulate/increment values."""
        either = [list(child.children) for child in transform(self).children]
        for case in either:
            for e in [child for child in case if case.count(child) > 1]:
                if type(e) is Argument or type(e) is Option and e.argcount:
                    if e.value is None:
                        e.value = []
                    elif type(e.value) is not list:
                        e.value = e.value.split()
                if type(e) is Command or type(e) is Option and e.argcount == 0:
                    e.value = 0
        return self


def transform(pattern):
    """Expand pattern into an (almost) equivalent one, but with single Either.

    Example: ((-a | -b) (-c | -d)) => (-a -c | -a -d | -b -c | -b -d)
    Quirks: [-a] => (-a), (-a...) => (-a -a)

    """
    result = []
    groups = [[pattern]]
    while groups:
        children = groups.pop(0)
        parents = [Required, Optional, OptionsShortcut, Either, OneOrMore]
        if any(t in map(type, children) for t in parents):
            child = [c for c in children if type(c) in parents][0]
            children.remove(child)
            if type(child) is Either:
                for c in child.children:
                    groups.append([c] + children)
            elif type(child) is OneOrMore:
                groups.append(child.children * 2 + children)
            else:
                groups.append(child.children + children)
        else:
            result.append(children)
    return Either(*[Required(*e) for e in result])


class LeafPattern(Pattern):

    """Leaf/terminal node of a pattern tree."""

    def __init__(self, name, value=None):
        self.name, self.value = name, value

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.name, self.value)

    def flat(self, *types):
        return [self] if not types or type(self) in types else []

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        pos, match = self.single_match(left)
        if match is None:
            return False, left, collected
        left_ = left[:pos] + left[pos + 1:]
        same_name = [a for a in collected if a.name == self.name]
        if type(self.value) in (int, list):
            if type(self.value) is int:
                increment = 1
            else:
                increment = ([match.value] if type(match.value) is str
                             else match.value)
            if not same_name:
                match.value = increment
                return True, left_, collected + [match]
            same_name[0].value += increment
            return True, left_, collected
        return True, left_, collected + [match]


class BranchPattern(Pattern):

    """Branch/inner node of a pattern tree."""

    def __init__(self, *children):
        self.children = list(children)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(repr(a) for a in self.children))

    def flat(self, *types):
        if type(self) in types:
            return [self]
        return sum([child.flat(*types) for child in self.children], [])


class Argument(LeafPattern):

    def single_match(self, left):
        for n, pattern in enumerate(left):
            if type(pattern) is Argument:
                return n, Argument(self.name, pattern.value)
        return None, None

    @classmethod
    def parse(class_, source):
        name = re.findall('(<\S*?>)', source)[0]
        value = re.findall('\[default: (.*)\]', source, flags=re.I)
        return class_(name, value[0] if value else None)


class Command(Argument):

    def __init__(self, name, value=False):
        self.name, self.value = name, value

    def single_match(self, left):
        for n, pattern in enumerate(left):
            if type(pattern) is Argument:
                if pattern.value == self.name:
                    return n, Command(self.name, True)
                else:
                    break
        return None, None


class Option(LeafPattern):

    def __init__(self, short=None, long=None, argcount=0, value=False):
        assert argcount in (0, 1)
        self.short, self.long, self.argcount = short, long, argcount
        self.value = None if value is False and argcount else value

    @classmethod
    def parse(class_, option_description):
        short, long, argcount, value = None, None, 0, False
        options, _, description = option_description.strip().partition('  ')
        options = options.replace(',', ' ').replace('=', ' ')
        for s in options.split():
            if s.startswith('--'):
                long = s
            elif s.startswith('-'):
                short = s
            else:
                argcount = 1
        if argcount:
            matched = re.findall('\[default: (.*)\]', description, flags=re.I)
            value = matched[0] if matched else None
        return class_(short, long, argcount, value)

    def single_match(self, left):
        for n, pattern in enumerate(left):
            if self.name == pattern.name:
                return n, pattern
        return None, None

    @property
    def name(self):
        return self.long or self.short

    def __repr__(self):
        return 'Option(%r, %r, %r, %r)' % (self.short, self.long,
                                           self.argcount, self.value)


class Required(BranchPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        l = left
        c = collected
        for pattern in self.children:
            matched, l, c = pattern.match(l, c)
            if not matched:
                return False, left, collected
        return True, l, c


class Optional(BranchPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        for pattern in self.children:
            m, left, collected = pattern.match(left, collected)
        return True, left, collected


class OptionsShortcut(Optional):

    """Marker/placeholder for [options] shortcut."""


class OneOrMore(BranchPattern):

    def match(self, left, collected=None):
        assert len(self.children) == 1
        collected = [] if collected is None else collected
        l = left
        c = collected
        l_ = None
        matched = True
        times = 0
        while matched:
            # could it be that something didn't match but changed l or c?
            matched, l, c = self.children[0].match(l, c)
            times += 1 if matched else 0
            if l_ == l:
                break
            l_ = l
        if times >= 1:
            return True, l, c
        return False, left, collected


class Either(BranchPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        outcomes = []
        for pattern in self.children:
            matched, _, _ = outcome = pattern.match(left, collected)
            if matched:
                outcomes.append(outcome)
        if outcomes:
            return min(outcomes, key=lambda outcome: len(outcome[1]))
        return False, left, collected


class Tokens(list):

    def __init__(self, source, error=DocoptExit):
        self += source.split() if hasattr(source, 'split') else source
        self.error = error

    @staticmethod
    def from_pattern(source):
        source = re.sub(r'([\[\]\(\)\|]|\.\.\.)', r' \1 ', source)
        source = [s for s in re.split('\s+|(\S*<.*?>)', source) if s]
        return Tokens(source, error=DocoptLanguageError)

    def move(self):
        return self.pop(0) if len(self) else None

    def current(self):
        return self[0] if len(self) else None


def parse_long(tokens, options):
    """long ::= '--' chars [ ( ' ' | '=' ) chars ] ;"""
    long, eq, value = tokens.move().partition('=')
    assert long.startswith('--')
    value = None if eq == value == '' else value
    similar = [o for o in options if o.long == long]
    if tokens.error is DocoptExit and similar == []:  # if no exact match
        similar = [o for o in options if o.long and o.long.startswith(long)]
    if len(similar) > 1:  # might be simply specified ambiguously 2+ times?
        raise tokens.error('%s is not a unique prefix: %s?' %
                           (long, ', '.join(o.long for o in similar)))
    elif len(similar) < 1:
        argcount = 1 if eq == '=' else 0
        o = Option(None, long, argcount)
        options.append(o)
        if tokens.error is DocoptExit:
            o = Option(None, long, argcount, value if argcount else True)
    else:
        o = Option(similar[0].short, similar[0].long,
                   similar[0].argcount, similar[0].value)
        if o.argcount == 0:
            if value is not None:
                raise tokens.error('%s must not have an argument' % o.long)
        else:
            if value is None:
                if tokens.current() in [None, '--']:
                    raise tokens.error('%s requires argument' % o.long)
                value = tokens.move()
        if tokens.error is DocoptExit:
            o.value = value if value is not None else True
    return [o]


def parse_shorts(tokens, options):
    """shorts ::= '-' ( chars )* [ [ ' ' ] chars ] ;"""
    token = tokens.move()
    assert token.startswith('-') and not token.startswith('--')
    left = token.lstrip('-')
    parsed = []
    while left != '':
        short, left = '-' + left[0], left[1:]
        similar = [o for o in options if o.short == short]
        if len(similar) > 1:
            raise tokens.error('%s is specified ambiguously %d times' %
                               (short, len(similar)))
        elif len(similar) < 1:
            o = Option(short, None, 0)
            options.append(o)
            if tokens.error is DocoptExit:
                o = Option(short, None, 0, True)
        else:  # why copying is necessary here?
            o = Option(short, similar[0].long,
                       similar[0].argcount, similar[0].value)
            value = None
            if o.argcount != 0:
                if left == '':
                    if tokens.current() in [None, '--']:
                        raise tokens.error('%s requires argument' % short)
                    value = tokens.move()
                else:
                    value = left
                    left = ''
            if tokens.error is DocoptExit:
                o.value = value if value is not None else True
        parsed.append(o)
    return parsed


def parse_pattern(source, options):
    tokens = Tokens.from_pattern(source)
    result = parse_expr(tokens, options)
    if tokens.current() is not None:
        raise tokens.error('unexpected ending: %r' % ' '.join(tokens))
    return Required(*result)


def parse_expr(tokens, options):
    """expr ::= seq ( '|' seq )* ;"""
    seq = parse_seq(tokens, options)
    if tokens.current() != '|':
        return seq
    result = [Required(*seq)] if len(seq) > 1 else seq
    while tokens.current() == '|':
        tokens.move()
        seq = parse_seq(tokens, options)
        result += [Required(*seq)] if len(seq) > 1 else seq
    return [Either(*result)] if len(result) > 1 else result


def parse_seq(tokens, options):
    """seq ::= ( atom [ '...' ] )* ;"""
    result = []
    while tokens.current() not in [None, ']', ')', '|']:
        atom = parse_atom(tokens, options)
        if tokens.current() == '...':
            atom = [OneOrMore(*atom)]
            tokens.move()
        result += atom
    return result


def parse_atom(tokens, options):
    """atom ::= '(' expr ')' | '[' expr ']' | 'options'
             | long | shorts | argument | command ;
    """
    token = tokens.current()
    result = []
    if token in '([':
        tokens.move()
        matching, pattern = {'(': [')', Required], '[': [']', Optional]}[token]
        result = pattern(*parse_expr(tokens, options))
        if tokens.move() != matching:
            raise tokens.error("unmatched '%s'" % token)
        return [result]
    elif token == 'options':
        tokens.move()
        return [OptionsShortcut()]
    elif token.startswith('--') and token != '--':
        return parse_long(tokens, options)
    elif token.startswith('-') and token not in ('-', '--'):
        return parse_shorts(tokens, options)
    elif token.startswith('<') and token.endswith('>') or token.isupper():
        return [Argument(tokens.move())]
    else:
        return [Command(tokens.move())]


def parse_argv(tokens, options, options_first=False):
    """Parse command-line argument vector.

    If options_first:
        argv ::= [ long | shorts ]* [ argument ]* [ '--' [ argument ]* ] ;
    else:
        argv ::= [ long | shorts | argument ]* [ '--' [ argument ]* ] ;

    """
    parsed = []
    while tokens.current() is not None:
        if tokens.current() == '--':
            return parsed + [Argument(None, v) for v in tokens]
        elif tokens.current().startswith('--'):
            parsed += parse_long(tokens, options)
        elif tokens.current().startswith('-') and tokens.current() != '-':
            parsed += parse_shorts(tokens, options)
        elif options_first:
            return parsed + [Argument(None, v) for v in tokens]
        else:
            parsed.append(Argument(None, tokens.move()))
    return parsed


def parse_defaults(doc):
    defaults = []
    for s in parse_section('options:', doc):
        # FIXME corner case "bla: options: --foo"
        _, _, s = s.partition(':')  # get rid of "options:"
        split = re.split('\n[ \t]*(-\S+?)', '\n' + s)[1:]
        split = [s1 + s2 for s1, s2 in zip(split[::2], split[1::2])]
        options = [Option.parse(s) for s in split if s.startswith('-')]
        defaults += options
    return defaults


def parse_section(name, source):
    pattern = re.compile('^([^\n]*' + name + '[^\n]*\n?(?:[ \t].*?(?:\n|$))*)',
                         re.IGNORECASE | re.MULTILINE)
    return [s.strip() for s in pattern.findall(source)]


def formal_usage(section):
    _, _, section = section.partition(':')  # drop "usage:"
    pu = section.split()
    return '( ' + ' '.join(') | (' if s == pu[0] else s for s in pu[1:]) + ' )'


def extras(help, version, options, doc):
    if help and any((o.name in ('-h', '--help')) and o.value for o in options):
        print(doc.strip("\n"))
        sys.exit()
    if version and any(o.name == '--version' and o.value for o in options):
        print(version)
        sys.exit()


class Dict(dict):
    def __repr__(self):
        return '{%s}' % ',\n '.join('%r: %r' % i for i in sorted(self.items()))


def docopt(doc, argv=None, help=True, version=None, options_first=False):
    """Parse `argv` based on command-line interface described in `doc`.

    `docopt` creates your command-line interface based on its
    description that you pass as `doc`. Such description can contain
    --options, <positional-argument>, commands, which could be
    [optional], (required), (mutually | exclusive) or repeated...

    Parameters
    ----------
    doc : str
        Description of your command-line interface.
    argv : list of str, optional
        Argument vector to be parsed. sys.argv[1:] is used if not
        provided.
    help : bool (default: True)
        Set to False to disable automatic help on -h or --help
        options.
    version : any object
        If passed, the object will be printed if --version is in
        `argv`.
    options_first : bool (default: False)
        Set to True to require options precede positional arguments,
        i.e. to forbid options and positional arguments intermix.

    Returns
    -------
    args : dict
        A dictionary, where keys are names of command-line elements
        such as e.g. "--verbose" and "<path>", and values are the
        parsed values of those elements.

    Example
    -------
    >>> from docopt import docopt
    >>> doc = '''
    ... Usage:
    ...     my_program tcp <host> <port> [--timeout=<seconds>]
    ...     my_program serial <port> [--baud=<n>] [--timeout=<seconds>]
    ...     my_program (-h | --help | --version)
    ...
    ... Options:
    ...     -h, --help  Show this screen and exit.
    ...     --baud=<n>  Baudrate [default: 9600]
    ... '''
    >>> argv = ['tcp', '127.0.0.1', '80', '--timeout', '30']
    >>> docopt(doc, argv)
    {'--baud': '9600',
     '--help': False,
     '--timeout': '30',
     '--version': False,
     '<host>': '127.0.0.1',
     '<port>': '80',
     'serial': False,
     'tcp': True}

    See also
    --------
    * For video introduction see http://docopt.org
    * Full documentation is available in README.rst as well as online
      at https://github.com/docopt/docopt#readme

    """
    argv = sys.argv[1:] if argv is None else argv

    usage_sections = parse_section('usage:', doc)
    if len(usage_sections) == 0:
        raise DocoptLanguageError('"usage:" (case-insensitive) not found.')
    if len(usage_sections) > 1:
        raise DocoptLanguageError('More than one "usage:" (case-insensitive).')
    DocoptExit.usage = usage_sections[0]

    options = parse_defaults(doc)
    pattern = parse_pattern(formal_usage(DocoptExit.usage), options)
    # [default] syntax for argument is disabled
    #for a in pattern.flat(Argument):
    #    same_name = [d for d in arguments if d.name == a.name]
    #    if same_name:
    #        a.value = same_name[0].value
    argv = parse_argv(Tokens(argv), list(options), options_first)
    pattern_options = set(pattern.flat(Option))
    for options_shortcut in pattern.flat(OptionsShortcut):
        doc_options = parse_defaults(doc)
        options_shortcut.children = list(set(doc_options) - pattern_options)
        #if any_options:
        #    options_shortcut.children += [Option(o.short, o.long, o.argcount)
        #                    for o in argv if type(o) is Option]
    extras(help, version, argv, doc)
    matched, left, collected = pattern.fix().match(argv)
    if matched and left == []:  # better error message if left?
        return Dict((a.name, a.value) for a in (pattern.flat() + collected))
    raise DocoptExit()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# konch documentation build configuration file.
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
import konch
sys.path.append(os.path.abspath("_themes"))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'konch'
copyright = u'2014'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = release =  konch.__version__

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
pygments_style = 'flask_theme_support.FlaskyStyle'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'kr_small'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
  'index_logo': 'konch.png',
  'index_logo_height': '200px',
  'github_fork': 'sloria/konch'
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
# html_logo = ''

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
htmlhelp_basename = 'konchdoc'


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
  ('index', 'konch.tex', u'konch Documentation',
   u'Steven Loria', 'manual'),
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
    ('index', 'konch', u'konch Documentation',
     [u'Steven Loria'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'konch', u'konch Documentation',
   u'Steven Loria', 'konch', 'HTTP Request Parsing for Pirates',
   ''),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

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
__FILENAME__ = konch_flask
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask

import konch

konch.config({
    'context': {
        'request': flask.request,
        'url_for': flask.url_for,
        'Flask': flask.Flask,
        'render_template': flask.render_template
    }
})

########NEW FILE########
__FILENAME__ = konch_named
"""Example .konchrc with named configs.

To use a named config, run:

    $ konch --name=trig

or

    $ konch -n trig
"""
import os
import sys
import math


import konch

# the default config
konch.config({
    'context': [os, sys],
    'banner': 'The default shell'
})

# A named config
konch.named_config('trig', {
    'context': [math.sin, math.tan, math.cos],
    'banner': 'The trig shell'
})

konch.named_config('func', {
    'context': [math.gamma, math.exp, math.log],
    'banner': 'The func shell'
})

########NEW FILE########
__FILENAME__ = konch_random
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random

import konch

banner = '''
"Probability is not a mere computation of odds on the dice or more complicated
variants; it is the acceptance of the lack of certainty in our knowledge and
the development of methods for dealing with our ignorance."
- Nassim Nickolas Taleb
'''

konch.config({
    'context': [random.randint, random.random, random.choice],
    'banner': banner,
    'shell': konch.IPythonShell,
})

########NEW FILE########
__FILENAME__ = konch_requests
# -*- coding: utf-8 -*-
import konch
import requests

konch.config({
    'context': {
        'httpget': requests.get,
        'httppost': requests.post,
        'httpput': requests.put,
        'httpdelete': requests.delete
    },
    'banner': 'A humanistic HTTP shell'
})

########NEW FILE########
__FILENAME__ = konch
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''konch: Customizes your Python shell.

Usage:
  konch
  konch init
  konch init [<config_file>] [-d]
  konch [--name=<name>] [-d]
  konch [--name=<name>] [--file=<file>] [--shell=<shell_name>] [-d]

Options:
  -h --help                  Show this screen.
  -v --version               Show version.
  init                       Creates a starter .konchrc file.
  -n --name=<name>           Named config to use.
  -s --shell=<shell_name>    Shell to use. Can be either "ipy" (IPython),
                              "bpy" (BPython), "py" (built-in Python shell),
                               or "auto". Overrides the 'shell' option in .konchrc.
  -f --file=<file>           File path of konch config file to execute. If not provided,
                               konch will use the .konchrc file in the current
                               directory.
  -d --debug                 Enable debugging/verbose mode.
'''

from __future__ import unicode_literals, print_function
import logging
import os
import sys
import code
import warnings
import random

from docopt import docopt

__version__ = '0.3.4'
__author__ = 'Steven Loria'
__license__ = 'MIT'

logger = logging.getLogger(__name__)

BANNER_TEMPLATE = """{version}

{text}
"""

CONTEXT_TEMPLATE = """
Context:
{context}
"""


DEFAULT_CONFIG_FILE = '.konchrc'

INIT_TEMPLATE = '''# -*- coding: utf-8 -*-
import konch

# TODO: Edit me
# Available options: 'context', 'banner', 'shell', 'prompt', 'hide_context'
konch.config({
    'context': {
        'speak': konch.speak
    }
})
'''


def execute_file(fname, globals_=None, locals_=None):
    """Executes code in a file. Python 2/3-compatible."""
    exec(compile(open(fname).read(), fname, 'exec'), globals_, locals_)


def format_context(context):
    """Output the a context dictionary as a string."""
    if context is None:
        return ''
    line_format = '{name}: {obj!r}'
    return '\n'.join([
        line_format.format(name=name, obj=obj)
        for name, obj in context.items()
    ])


def make_banner(text=None, context=None, hide_context=False):
    """Generates a full banner with version info, the given text, and a
    formatted list of context variables.
    """
    banner_text = text or speak()
    out = BANNER_TEMPLATE.format(version=sys.version, text=banner_text)
    if context and not hide_context:
        out += CONTEXT_TEMPLATE.format(context=format_context(context))
    return out


def context_list2dict(context_list):
    """Converts a list of objects (functions, classes, or modules) to a
    dictionary mapping the object names to the objects.
    """
    return dict(
        (obj.__name__, obj) for obj in context_list
    )


class Shell(object):
    """Base shell class.

    :param dict context: Dictionary that defines what variables will be
        available when the shell is run.
    :param str banner: Banner text that appears on startup.
    :param str prompt: Custom input prompt.
    :param str output: Custom output prompt.
    """

    def __init__(self, context, banner=None, prompt=None,
            output=None, hide_context=False):
        self.context = context
        self.hide_context = hide_context
        self.banner = make_banner(banner, context, hide_context=hide_context)
        self.prompt = prompt
        self.output = output

    def start(self):
        raise NotImplementedError


class PythonShell(Shell):
    """The built-in Python shell."""

    def start(self):
        if self.prompt:
            sys.ps1 = self.prompt
        if self.output:
            warnings.warn('Custom output templates not supported by PythonShell.')
        code.interact(self.banner, local=self.context)
        return None


class IPythonShell(Shell):
    """The IPython shell."""

    def start(self):
        try:
            from IPython import embed
            from IPython.config.loader import Config as IPyConfig
        except ImportError:
            raise ShellNotAvailableError('IPython shell not available.')
        ipy_config = IPyConfig()
        prompt_config = ipy_config.PromptManager
        if self.prompt:
            prompt_config.in_template = self.prompt
        if self.output:
            prompt_config.out_template = self.output
        embed(banner1=self.banner,
            user_ns=self.context,
            config=ipy_config)
        return None


class BPythonShell(Shell):
    """The BPython shell."""

    def start(self):
        try:
            from bpython import embed
        except ImportError:
            raise ShellNotAvailableError('BPython shell not available.')
        if self.prompt:
            warnings.warn('Custom prompts not supported by BPythonShell.')
        if self.output:
            warnings.warn('Custom output templates not supported by BPythonShell.')
        embed(banner=self.banner, locals_=self.context)
        return None


class AutoShell(Shell):
    """Shell that runs IPython or BPython if available. Falls back to built-in
    Python shell.
    """

    def __init__(self, context, banner, *args, **kwargs):
        Shell.__init__(self, context, *args, **kwargs)
        self.banner = banner

    def start(self):
        shell_args = {
            'context': self.context,
            'banner': self.banner,
            'prompt': self.prompt,
            'output': self.output,
            'hide_context': self.hide_context,
        }
        try:
            return IPythonShell(**shell_args).start()
        except ShellNotAvailableError:
            try:
                return BPythonShell(**shell_args).start()
            except ShellNotAvailableError:
                return PythonShell(**shell_args).start()
        return None


class KonchError(Exception):
    pass


class ShellNotAvailableError(KonchError):
    pass

SHELL_MAP = {
    'ipy': IPythonShell, 'ipython': IPythonShell,
    'bpy': BPythonShell, 'bpython': BPythonShell,
    'py': PythonShell, 'python': PythonShell,
    'auto': AutoShell,
}

CONCHES = [
    ('"My conch told me to come save you guys."\n'
    '"Hooray for the magic conches!"'),
    '"All hail the Magic Conch!"',
    '"Hooray for the magic conches!"',
    '"Uh, hello there. Magic Conch, I was wondering... '
    'should I have the spaghetti or the turkey?"',
    '"This copyrighted conch is the cornerstone of our organization."',
    '"Praise the Magic Conch!"',
    '"the conch exploded into a thousand white fragments and ceased to exist."',
    '"S\'right. It\'s a shell!"',
    '"Ralph felt a kind of affectionate reverence for the conch"',
    '"Conch! Conch!"',
    '"That\'s why you got the conch out of the water"',
    '"the summons of the conch"',
    '"Whoever holds the conch gets to speak."',
    '"They\'ll come when they hear us--"',
    '"We gotta drop the load!"',
    '"Dude, we\'re falling right out the sky!!"',
    ('"Oh, Magic Conch Shell, what do we need to do to get out of the Kelp Forest?"\n'
        '"Nothing."'),
    '"The shell knows all!"',
    '"we must never question the wisdom of the Magic Conch."',
    '"The Magic Conch! A club member!"'
]


def speak():
    return random.choice(CONCHES)


class Config(dict):
    """A dict-like config object. Behaves like a normal dict except that
    the ``context`` will always be converted from a list to a dict.
    Defines the default configuration.
    """

    def __init__(self, context=None, banner=None, shell=AutoShell,
            prompt=None, output=None, hide_context=False):
        ctx = Config.transform_val(context) or {}
        super(Config, self).__init__(context=ctx, banner=banner, shell=shell,
            prompt=prompt, output=output, hide_context=hide_context)

    def __setitem__(self, key, value):
        val = Config.transform_val(value)
        super(Config, self).__setitem__(key, val)

    @staticmethod
    def transform_val(val):
        if isinstance(val, (list, tuple)):
            return context_list2dict(val)
        return val

    def update(self, d):
        for key in d.keys():
            self[key] = d[key]

# _cfg and _config_registry are global variables that may be mutated by a
# .konchrc file
_cfg = Config()
_config_registry = {
    'default': _cfg
}


def start(context=None, banner=None, shell=AutoShell,
        prompt=None, output=None, hide_context=False):
    """Start up the konch shell. Takes the same parameters as Shell.__init__.
    """
    logger.debug('Using shell...')
    logger.debug(shell)
    if banner is None:
        banner = speak()
    # Default to global config
    context_ = context or _cfg['context']
    banner_ = banner or _cfg['banner']
    shell_ = shell or _cfg['shell']
    prompt_ = prompt or _cfg['prompt']
    output_ = output or _cfg['output']
    hide_context_ = hide_context or _cfg['hide_context']
    shell_(context=context_, banner=banner_,
        prompt=prompt_, output=output_, hide_context=hide_context_).start()


def config(config_dict):
    """Configures the konch shell. This function should be called in a
    .konchrc file.

    :param dict config_dict: Dict that may contain 'context', 'banner', and/or
        'shell' (default shell class to use).
    """
    logger.debug('Updating with {0}'.format(config_dict))
    _cfg.update(config_dict)
    return _cfg


def named_config(name, config_dict):
    """Adds a named config to the config registry.
    This function should be called in a .konchrc file.
    """
    _config_registry[name] = Config(**config_dict)


def reset_config():
    global _cfg
    _cfg = Config()
    return _cfg


def get_file_directory(filename):
    return os.path.dirname(os.path.abspath(filename))


def __ensure_directory_in_path(filename):
    """Ensures that a file's directory is in the Python path.
    """
    directory = get_file_directory(filename)
    if directory not in sys.path:
        logger.debug('Adding {0} to sys.path'.format(directory))
        sys.path.insert(0, directory)


def use_file(filename):
    # First update _cfg by executing the config file
    config_file = filename or resolve_path(DEFAULT_CONFIG_FILE)
    if config_file and os.path.exists(config_file):
        logger.info('Using {0}'.format(config_file))
        # Ensure that relative imports are possible
        __ensure_directory_in_path(config_file)
        execute_file(config_file)
    else:
        if not config_file:
            warnings.warn('No config file found.')
        else:
            warnings.warn('"{fname}" not found.'.format(fname=config_file))
    return _cfg


def __get_home_directory():
    return os.path.expanduser('~')


def resolve_path(filename):
    """Find a file by walking up parent directories until the file is found.
    Return the absolute path of the file.
    """
    current = os.getcwd()
    sentinal_dir = os.path.join(__get_home_directory(), '..')
    while current != sentinal_dir:
        target = os.path.join(current, filename)
        if os.path.exists(target):
            return os.path.abspath(target)
        else:
            current = os.path.abspath(os.path.join(current, '..'))

    return False


def init_config(config_file=None):
    if not os.path.exists(config_file):
        with open(config_file, 'w') as fp:
            fp.write(INIT_TEMPLATE)
        print('Initialized konch. Edit {0} to your needs and run `konch` '
                'to start an interactive session.'
                .format(config_file))
        sys.exit(0)
    else:
        print('{0} already exists in this directory.'
                .format(config_file))
        sys.exit(1)


def parse_args():
    """Exposes the docopt command-line arguments parser.
    Return a dictionary of arguments.
    """
    return docopt(__doc__, version=__version__)


def main():
    """Main entry point for the konch CLI."""
    args = parse_args()
    if args['--debug']:
        logging.basicConfig(
            format='%(levelname)s %(filename)s: %(message)s',
            level=logging.DEBUG)
    logger.debug(args)

    if args['init']:
        config_file = args['<config_file>'] or DEFAULT_CONFIG_FILE
        init_config(config_file)
    use_file(args['--file'])

    if args['--name']:
        config_dict = _config_registry.get(args['--name'], _cfg)
        logger.debug('Using named config...')
        logger.debug(config)
    else:
        config_dict = _cfg
    # Allow default shell to be overriden by command-line argument
    shell_name = args['--shell']
    if shell_name:
        config_dict['shell'] = SHELL_MAP.get(shell_name.lower(), AutoShell)
    logger.debug('Starting with config {0}'.format(config_dict))
    start(**config_dict)
    sys.exit(0)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tasks
# -*- coding: utf-8 -*-
import os

from invoke import task, run

docs_dir = 'docs'
build_dir = os.path.join(docs_dir, '_build')

@task
def test():
    run('python setup.py test', pty=True)

@task
def clean():
    run("rm -rf build")
    run("rm -rf dist")
    run("rm -rf konch.egg-info")
    clean_docs()
    print("Cleaned up.")

@task
def clean_docs():
    run("rm -rf %s" % build_dir)

@task
def browse_docs():
    run("open %s" % os.path.join(build_dir, 'index.html'))

@task
def docs(clean=False, browse=False):
    if clean:
        clean_docs()
    run("sphinx-build %s %s" % (docs_dir, build_dir), pty=True)
    if browse:
        browse_docs()

@task
def readme(browse=False):
    run('rst2html.py README.rst > README.html')

@task
def publish(test=False):
    """Publish to the cheeseshop."""
    if test:
        run('python setup.py register -r test sdist upload -r test')
    else:
        run("python setup.py register sdist upload")

########NEW FILE########
__FILENAME__ = test_konch
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import os

import pytest
from scripttest import TestFileEnvironment

import konch


def assert_in_output(s, res, message=None):
    """Assert that a string is in either stdout or std err.
    Included because banners are sometimes outputted to stderr.
    """
    assert any([s in res.stdout, res.stdout, s in res.stderr]), message


@pytest.fixture
def env():
    return TestFileEnvironment(ignore_hidden=False)


def teardown_function(func):
    konch.reset_config()


def test_format_context():
    context = {
        'my_number': 42,
        'my_func': lambda x: x,
    }
    result = konch.format_context(context)
    assert result == '\n'.join([
        '{0}: {1!r}'.format(key, value)
        for key, value in context.items()
    ])


def test_make_banner_custom():
    text = 'I want to be the very best'
    result = konch.make_banner(text)
    assert text in result
    assert sys.version in result


def test_make_banner_with_context():
    context = {'foo': 42}
    result = konch.make_banner(context=context)
    assert konch.format_context(context) in result


def test_make_banner_hide_context():
    context = {'foo': 42}
    result = konch.make_banner(context=context, hide_context=True)
    assert konch.format_context(context) not in result


def test_cfg_defaults():
    assert konch._cfg['shell'] == konch.AutoShell
    assert konch._cfg['banner'] is None
    assert konch._cfg['context'] == {}
    assert konch._cfg['hide_context'] is False


def test_config():
    assert konch._cfg == konch.Config()
    konch.config({
        'banner': 'Foo bar'
    })
    assert konch._cfg['banner'] == 'Foo bar'


def test_reset_config():
    assert konch._cfg == konch.Config()
    konch.config({
        'banner': 'Foo bar'
    })
    konch.reset_config()
    assert konch._cfg == konch.Config()

def test_parse_args():
    args = konch.parse_args()
    assert '--shell' in args
    assert 'init' in args
    assert '<config_file>' in args
    assert '--name' in args


def test_context_list2dict():
    import math
    class MyClass:
        pass
    def my_func():
        pass

    my_objects = [math, MyClass, my_func]
    expected = {'my_func': my_func, 'MyClass': MyClass, 'math': math}
    assert konch.context_list2dict(my_objects) == expected


def test_config_list():
    assert konch._cfg == konch.Config()
    def my_func():
        return
    konch.config({
        'context': [my_func]
    })
    assert konch._cfg['context']['my_func'] == my_func


def test_config_converts_list_context():
    import math
    config = konch.Config(context=[math])
    assert config['context'] == {'math': math}


def test_config_set_context_converts_list():
    import math
    config = konch.Config()
    config['context'] = [math]
    assert config['context'] == {'math': math}


def test_config_update_context_converts_list():
    import math
    config = konch.Config()
    config.update({
        'context': [math]
    })
    assert config['context'] == {'math': math}


def test_named_config_adds_to_registry():
    assert konch._config_registry['default'] == konch._cfg
    assert len(konch._config_registry.keys()) == 1
    konch.named_config('mynamespace', {'context': {'foo': 42}})
    assert len(konch._config_registry.keys()) == 2
    # reset config_registry
    konch._config_registry = {'default': konch._cfg}


##### Command tests #####


def test_init_creates_config_file(env):
    res = env.run('konch', 'init')
    assert res.returncode == 0
    assert konch.DEFAULT_CONFIG_FILE in res.files_created


def test_init_with_filename(env):
    res = env.run('konch', 'init', 'myconfig')
    assert 'myconfig' in res.files_created


def test_konch_with_no_config_file(env):
    try:
        os.remove(os.path.join(env.base_path, '.konchrc'))
    except OSError:
        pass
    res = env.run('konch', expect_stderr=True)
    assert res.returncode == 0


def test_konch_init_when_config_file_exists(env):
    env.run('konch', 'init')
    res = env.run('konch', 'init', expect_error=True)
    assert 'already exists' in res.stdout
    assert res.returncode == 1


def test_default_banner(env):
    env.run('konch', 'init')
    res = env.run('konch', expect_stderr=True)
    assert_in_output(str(sys.version), res)


def test_config_file_not_found(env):
    res = env.run('konch', '-f', 'notfound', expect_stderr=True)
    assert 'not found' in res.stderr
    assert res.returncode == 0

TEST_CONFIG = """
import konch

konch.config({
    'banner': 'Test banner'
    'prompt': 'myprompt >>>'
})
"""


@pytest.fixture
def fileenv(request, env):
    fpath = os.path.join(env.base_path, 'testrc')
    with open(fpath, 'w') as fp:
        fp.write(TEST_CONFIG_WITH_NAMES)
    def finalize():
        os.remove(fpath)
    request.addfinalizer(finalize)
    return env


def test_custom_banner(fileenv):
    res = fileenv.run('konch', '-f', 'testrc', expect_stderr=True)
    assert_in_output('Test banner', res)


def test_custom_prompt(fileenv):
    res = fileenv.run('konch', '-f', 'testrc', expect_stderr=True)
    assert_in_output('myprompt >>>', res)


def test_version(env):
    res = env.run('konch', '--version')
    assert konch.__version__ in res.stdout
    res = env.run('konch', '-v')
    assert konch.__version__ in res.stdout


TEST_CONFIG_WITH_NAMES = """
import konch

konch.config({
    'context': {
        'foo': 42,
    },
    'banner': 'Default'
})

konch.named_config('conf2', {
    'context': {
        'bar': 24
    },
    'banner': 'Conf2'
})
"""


@pytest.fixture
def fileenv2(request, env):
    fpath = os.path.join(env.base_path, '.konchrc')
    with open(fpath, 'w') as fp:
        fp.write(TEST_CONFIG_WITH_NAMES)
    def finalize():
        os.remove(fpath)
    request.addfinalizer(finalize)
    return env


@pytest.fixture
def folderenv(request, env):
    folder = os.path.abspath(os.path.join(env.base_path, 'testdir'))
    os.makedirs(folder)
    def finalize():
        os.removedirs(folder)
    request.addfinalizer(finalize)
    return env


def test_default_config(fileenv2):
    res = fileenv2.run('konch', expect_stderr=True)
    assert_in_output('Default', res)
    assert_in_output('foo', res)


def test_selecting_named_config(fileenv2):
    res = fileenv2.run('konch', '-n', 'conf2', expect_stderr=True)
    assert_in_output('Conf2', res)
    assert_in_output('bar', res)


def test_selecting_name_that_doesnt_exist(fileenv2):
    res = fileenv2.run('konch', '-n', 'doesntexist', expect_stderr=True)
    assert_in_output('Default', res)


def test_resolve_path(folderenv):
    folderenv.run('konch', 'init')
    fpath = os.path.abspath(os.path.join(folderenv.base_path, '.konchrc'))
    assert os.path.exists(fpath)
    folder = os.path.abspath(os.path.join(folderenv.base_path, 'testdir'))
    os.chdir(folder)
    assert konch.resolve_path('.konchrc') == fpath

########NEW FILE########
