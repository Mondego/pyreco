__FILENAME__ = gentest
# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import re
import urllib
from distutils.cmd import Command


TESTCASE_TEMPLATE = u''\
'''# -*- coding: utf-8 -*-
from tests import HangulizeTestCase


class {name}TestCase(HangulizeTestCase):
    """ {url} """

    def setUp(self):
        from hangulize.langs.{locale} import {name}
        self.lang = {name}()
    {body}'''
TEST_METHOD_TEMPLATE = u''\
'''
    def test_{testname}(self):
        """{title}{body}"""{assertions}
'''
CODE_SEP = u'\n        '
ASSERTION_TEMPLATE = u"assert u'{want}' == self.hangulize(u'{word}')"


class gen_test(Command):

    user_options = [('url=', 'a', 'the rules url'),
                    ('name=', 'n', 'the language name'),
                    ('locale=', 'l', 'the locale code')]

    def initialize_options(self):
        self.url = None
        self.name = None
        self.locale = None

    def finalize_options(self):
        pass

    def run(self):
        if not self.url:
            self.url = raw_input('Rules URL(http://korean.go.kr/...): ')
        if not self.name:
            self.name = raw_input('Language Name(ex. Italian): ')
        if not self.locale:
            self.locale = raw_input('Locale Code(ex. it): ')
        path = os.path.join('tests', '%s.dist.py' % self.locale)
        with open(path, 'w') as out:
            print 'generating test suite...',
            print>>out, generate_testsuite(self.url,
                                           self.name,
                                           self.locale).encode('utf-8')
            print 'done'
            print 'test suite was built at %s' % path


def ordinalth(n):
    last = n - n / 10 * 10
    if last == 1:
        return '%dst' % n
    elif last == 2:
        return '%dnd' % n
    elif last == 3:
        return '%drd' % n
    return '%dth' % n


def generate_testsuite(url, name, locale):
    from BeautifulSoup import BeautifulSoup
    html = ''.join(urllib.urlopen(url).readlines())
    soup = BeautifulSoup(html)
    def need(tag):
        return tag.name == 'h3' and tag.get('class') in ('big', 'clear') or \
               tag.name == 'h4' and len(tag.attrs) == 0 or \
               tag.name == 'p' and tag.get('class') == 'h3Text' or \
               tag.name == 'li' and tag.parent.parent.get('class') in \
               ('jamobox', 'rulebox01')
    def text(tag):
        return ''.join(e for e in tag.recursiveChildGenerator() \
                         if isinstance(e, unicode))
    rules = []
    examples = {}
    body = []
    for tag in soup.findAll(need):
        if tag.get('class') == 'big':
            header = text(tag)
        elif tag.get('class') == 'clear':
            rules.append([text(tag)])
        elif tag.name in ('h4', 'p'):
            rules[-1].append(text(tag))
        elif tag.name == 'li':
            i = len(rules) - 1
            if not examples.get(i):
                examples[i] = []
            examples[i].append(text(tag))
    for i, rule in enumerate(rules):
        assertions = []
        for x in examples[i]:
            match = re.match('(?:\(.+\) )?([^ ]+) (.+)', x)
            if not match:
                assertions.append('# %s' % x)
                continue
            assertion = ASSERTION_TEMPLATE.format(want=match.group(2),
                                                  word=match.group(1))
            assertions.append(assertion)
        testname = ordinalth(int(re.search('\d+', rule[0]).group(0)))
        title = re.sub(u'(제\d+항)(?=.)', r'\1: ', rule[0])
        if len(rule) > 1:
            rulebody = CODE_SEP + CODE_SEP.join(s for s in rule[1:]) + CODE_SEP
        else:
            rulebody = ''
        if assertions:
            assertions = CODE_SEP + CODE_SEP.join(assertions)
        else:
            assertions = ''
        method = TEST_METHOD_TEMPLATE.format(testname=testname,
                                             title=title,
                                             body=rulebody,
                                             assertions=assertions)
        body.append(method)
    body = ''.join(body).strip()

    return TESTCASE_TEMPLATE.format(name=name, locale=locale,
                                    url=url, body=body)

########NEW FILE########
__FILENAME__ = helper
import platform


def color(msg, color):
    if platform.win32_ver()[0]:
        return msg
    colors = dict(BLACK=30, RED=31, GREEN=32, YELLOW=33, BLUE=34,
                  MAGENTA=35, CYAN=36, WHITE=37)
    code = colors[color.upper()]
    return '\033[1;%dm%s\033[0m' % (code, msg)

########NEW FILE########
__FILENAME__ = profile
try:
    from cProfile import run as run_profile
except ImportError:
    from profile import run as run_profile
from distutils.cmd import Command


class profile(Command):

    user_options = [('lang=', 'l', 'the language code(ISO 639-3)')]

    def initialize_options(self):
        self.lang = None

    def finalize_options(self):
        pass

    def run(self):
        code = '' \
'''
import unittest
import tests
suite = tests.suite(%r)
unittest.TextTestRunner(verbosity=1).run(suite)
try:
    from guppy import hpy
    print '============= memory usage ============='
    print hpy().heap()
    print '----------------------------------------'
except ImportError:
    pass
''' \
        '' % self.lang
        run_profile(code)

########NEW FILE########
__FILENAME__ = repl
# -*- coding: utf-8 -*-
import re
import logging
from distutils.cmd import Command
from cmds.helper import color
from hangulize import hangulize, get_lang, DONE, SPECIAL, BLANK, ZWSP


class REPLHandler(logging.StreamHandler):

    color_map = {'hangulize': 'cyan', 'rewrite': 'green', 'remove': 'red'}

    @staticmethod
    def readably(string):
        string = string.replace(DONE, '.')
        string = string.replace(SPECIAL, '#')
        string = re.sub('^' + BLANK + '|' + BLANK + '$', '', string)
        string = re.sub(ZWSP, '\r', string)
        string = re.sub(BLANK, ' ', string)
        string = re.sub('\r', ZWSP, string)
        return string

    def handle(self, record):
        msg = self.readably(record.msg)
        # keywords
        maxlen = max([len(x) for x in self.color_map.keys()])
        def deco(color_name):
            def replace(m):
                pad = ' ' * (maxlen - len(m.group(1)))
                return color(m.group(1), color_name) + pad
            return replace
        for keyword, color_name in self.color_map.items():
            msg = re.sub(r'(?<=\t)(%s)' % keyword, deco(color_name), msg)
        # result
        msg = re.sub(r'(?<=^\=\>)(.*)$', color(r'\1', 'yellow'), msg)
        # step
        msg = re.sub(r'^(>>|\.\.)', color(r'\1', 'blue'), msg)
        msg = re.sub(r'^(=>)', color(r'\1', 'magenta'), msg)
        # arrow
        msg = re.sub(r'(->)(?= [^ ]+$)', color(r'\1', 'black'), msg)
        record.msg = msg
        return logging.StreamHandler.handle(self, record)


class repl(Command):
    """Read-eval-print loop for Hangulize

        $ python setup.py repl
        Select Locale: it
        ==> gloria
        -> 'gloria'
        -> ' loria'
        -> '  oria'
        -> '  o ia'
        -> '  o i '
        -> '  o   '
        -> '      '
        글로리아
    """

    user_options = [('lang=', 'l', 'the language code(ISO 639-3)')]

    def initialize_options(self):
        self.lang = None

    def finalize_options(self):
        pass

    def run(self):
        import sys
        logger = make_logger()
        encoding = sys.stdout.encoding
        def _repl():
            while True:
                lang = self.lang or raw_input(color('Lang: ', 'magenta'))
                try:
                    lang = get_lang(lang)
                    logger.info('** ' + color(type(lang).__name__, 'green') + \
                                ' is selected')
                    break
                except Exception, e:
                    logger.error(color(e, 'red'))
                    self.lang = None
            while True:
                string = raw_input(color('==> ', 'cyan'))
                if not string:
                    logger.info('** ' + color('End', 'green'))
                    break
                yield lang.hangulize(string.decode(encoding), logger=logger)
        for hangul in _repl():
            pass


def make_logger(name='Hangulize REPL'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(REPLHandler())
    return logger

########NEW FILE########
__FILENAME__ = stat
from distutils.cmd import Command
import hangulize.langs
from cmds.helper import color


class stat(Command):

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        langs = hangulize.langs.get_list()
        examples = []
        for lang in (x.replace('.', '_') for x in langs):
            mod = getattr(__import__('tests.%s' % lang), lang)
            case = [x for x in dir(mod) if x.endswith('TestCase') and \
                                           not x.startswith('Hangulize')][0]
            examples += getattr(mod, case).get_examples().keys()
        print 'Supported languages:',
        print color(len(langs), 'cyan')
        print 'Prepared examples:',
        print color(len(examples), 'cyan')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Hangulize documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 24 17:08:22 2011.
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
sys.path.insert(0, os.path.abspath('_themes'))
sys.path.insert(0, os.path.abspath('..'))

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
project = u'Hangulize'
copyright = u'2010-2013, Heungsub Lee'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from hangulize import __version__ as version
# The full version, including alpha/beta/rc tags.
release = version

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
#pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'hangulize'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {'github_fork': 'sublee/hangulize',
                      'google_analytics': 'UA-28655602-1'}

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
html_favicon = 'favicon.ico'

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
htmlhelp_basename = 'Hangulizedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Hangulize.tex', u'Hangulize Documentation',
   u'Heungsub Lee', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'hangulize', u'Hangulize Documentation',
     [u'Heungsub Lee'], 1)
]

########NEW FILE########
__FILENAME__ = hangul
#
# This file is part of KoreanCodecs.
#
# Copyright(C) 2002-2003 Hye-Shik Chang <perky@FreeBSD.org>.
#
# KoreanCodecs is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# KoreanCodecs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with KoreanCodecs; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# $Id: hangul.py,v 1.2 2003/10/15 19:24:53 perky Exp $
#

class UnicodeHangulError(Exception):
    
    def __init__ (self, msg):
        self.msg = msg
        Exception.__init__(self, msg)
    
    def __repr__ (self):
        return self.msg
    
    __str__ = __repr__

Null = u''
try:
    True
except:
    True = 1
    False = 0

class Jaeum:

    Codes = (u'\u3131', u'\u3132', u'\u3133', u'\u3134', u'\u3135', u'\u3136',
            #    G         GG          GS         N          NJ         NH
             u'\u3137', u'\u3138', u'\u3139', u'\u313a', u'\u313b', u'\u313c',
            #    D         DD          L          LG         LM         LB
             u'\u313d', u'\u313e', u'\u313f', u'\u3140', u'\u3141', u'\u3142',
            #    LS        LT          LP         LH         M          B
             u'\u3143', u'\u3144', u'\u3145', u'\u3146', u'\u3147', u'\u3148',
            #    BB        BS          S          SS         NG         J
             u'\u3149', u'\u314a', u'\u314b', u'\u314c', u'\u314d', u'\u314e')
            #    JJ        C           K          T          P          H
    Width = len(Codes)
    G, GG, GS, N, NJ, NH, D, DD, L, LG, LM, LB, LS, LT, LP, LH, M, B, \
    BB, BS, S, SS, NG, J, JJ, C, K, T, P, H = Codes
    Choseong = [G, GG, N, D, DD, L, M, B, BB, S, SS, NG, J, JJ, C, K, T, P, H]
    Jongseong = [Null, G, GG, GS, N, NJ, NH, D, L, LG, LM, LB, LS, LT, \
                LP, LH, M, B, BS, S, SS, NG, J, C, K, T, P, H]
    MultiElement = {
        GG: (G, G),  GS: (G, S),  NJ: (N, J),  NH: (N, H),  DD: (D, D),
        LG: (L, G),  LM: (L, M),  LB: (L, B),  LS: (L, S),  LT: (L, T),
        LP: (L, P),  LH: (L, H),  BB: (B, B),  BS: (B, S),  SS: (S, S),
        JJ: (J, J)
    }


class Moeum:

    Codes = (u'\u314f', u'\u3150', u'\u3151', u'\u3152', u'\u3153', u'\u3154',
            #    A          AE        YA         YAE         EO         E
             u'\u3155', u'\u3156', u'\u3157', u'\u3158', u'\u3159', u'\u315a',
            #    YEO        YE        O          WA          WAE        OE
             u'\u315b', u'\u315c', u'\u315d', u'\u315e', u'\u315f', u'\u3160',
            #    YO         U         WEO        WE          WI         YU
             u'\u3161', u'\u3162', u'\u3163')
            #    EU         YI        I
    Width = len(Codes)
    A, AE, YA, YAE, EO, E, YEO, YE, O, WA, WAE, OE, YO, \
    U, WEO, WE, WI, YU, EU, YI, I = Codes
    Jungseong = list(Codes)
    MultiElement = {
        AE: (A, I),  YAE: (YA, I),  YE: (YEO, I), WA: (O, A),  WAE: (O, A, I),
        OE: (O, I),  WEO: (U, EO),  WE: (U, E),   WI: (U, I),  YI: (EU, I)
    }

# Aliases for your convinience
Choseong = Jaeum.Choseong
Jungseong = Moeum.Jungseong
Jongseong = Jaeum.Jongseong

for name, code in Jaeum.__dict__.items() + Moeum.__dict__.items():
    if name.isupper() and len(name) <= 3:
        exec "%s = %s" % (name, repr(code))
del name, code

# Unicode Hangul Syllables Characteristics
ZONE = (u'\uAC00', u'\uD7A3')
NCHOSEONG  = len(Choseong)
NJUNGSEONG = len(Jungseong)
NJONGSEONG = len(Jongseong)
JBASE_CHOSEONG  = u'\u1100'
JBASE_JUNGSEONG = u'\u1161'
JBASE_JONGSEONG = u'\u11A8'
CHOSEONG_FILLER = u'\u115F'
JUNGSEONG_FILLER = u'\u1160'

_ishangul = (
    lambda code:
        ZONE[0] <= code <= ZONE[1] or
        code in Jaeum.Codes or
        code in Moeum.Codes
)

# Alternative Suffixes : do not use outside
ALT_SUFFIXES = {
    u'\uc744': (u'\ub97c', u'\uc744'), # reul, eul
    u'\ub97c': (u'\ub97c', u'\uc744'), # reul, eul
    u'\uc740': (u'\ub294', u'\uc740'), # neun, eun
    u'\ub294': (u'\ub294', u'\uc740'), # neun, eun
    u'\uc774': (u'\uac00', u'\uc774'), # yi, ga
    u'\uac00': (u'\uac00', u'\uc774'), # yi, ga
    u'\uc640': (u'\uc640', u'\uacfc'), # wa, gwa
    u'\uacfc': (u'\uc640', u'\uacfc'), # wa, gwa
}

# Ida-Varitaion Suffixes : do not use outside
IDA_SUFFIXES = {
    u'(\uc774)': (u'', u'\uc774'),     # (yi)da
    u'(\uc785)': (17, u'\uc785'),      # (ip)nida
    u'(\uc778)': (4, u'\uc778'),       # (in)-
}

def isJaeum(u):
    if u:
        for c in u:
            if c not in Jaeum.Codes:
                break
        else:
            return True
    return False

def isMoeum(u):
    if u:
        for c in u:
            if c not in Moeum.Codes:
                break
        else:
            return True
    return False

def ishangul(u):
    if u:
        for c in u:
            if not _ishangul(c):
                break
        else:
            return True
    return False

def join(codes):
    """ Join function which makes hangul syllable from jamos """
    if len(codes) != 3:
        raise UnicodeHangulError("needs 3-element tuple")
    if not codes[0] or not codes[1]: # single jamo
        return codes[0] or codes[1]

    return unichr(
        0xac00 + (
            Choseong.index(codes[0])*NJUNGSEONG +
            Jungseong.index(codes[1])
        )*NJONGSEONG + Jongseong.index(codes[2])
    )

def split(code):
    """ Split function which splits hangul syllable into jamos """
    if len(code) != 1 or not _ishangul(code):
        raise UnicodeHangulError("needs 1 hangul letter")
    if code in Jaeum.Codes:
        return (code, Null, Null)
    if code in Moeum.Codes:
        return (Null, code, Null)

    code = ord(code) - 0xac00
    return (
        Choseong[int(code / (NJUNGSEONG*NJONGSEONG))], # Python3000 safe
        Jungseong[int(code / NJONGSEONG) % NJUNGSEONG],
        Jongseong[code % NJONGSEONG]
    )

def conjoin(s):
    obuff = []
    ncur = 0

    while ncur < len(s):
        c = s[ncur]
        if JBASE_CHOSEONG <= c <= u'\u1112' or c == CHOSEONG_FILLER: # starts with choseong
            if len(s) > ncur+1 and JUNGSEONG_FILLER <= s[ncur+1] <= u'\u1175':
                cho = Choseong[ord(c) - ord(JBASE_CHOSEONG)]
                jung = Jungseong[ord(s[ncur+1]) - ord(JBASE_JUNGSEONG)]
                if len(s) > ncur+2 and JBASE_JONGSEONG <= s[ncur+2] <= u'\u11C2':
                    jong = Jongseong[ord(s[ncur+2]) - ord(JBASE_JONGSEONG) + 1]
                    ncur += 2
                else:
                    jong = Null
                    ncur += 1
                obuff.append(join([cho, jung, jong]))
            else:
                obuff.append(join([Choseong[ord(c) - ord(JBASE_CHOSEONG)], Null, Null]))
        elif JBASE_JUNGSEONG <= c <= u'\u1175':
            obuff.append(join([Null, Jungseong[ord(c) - ord(JBASE_JUNGSEONG)], Null]))
        else:
            obuff.append(c)
        ncur += 1
    
    return u''.join(obuff)

def disjoint(s):
    obuff = []
    for c in s:
        if _ishangul(c):
            cho, jung, jong = split(c)
            if cho:
                obuff.append( unichr(ord(JBASE_CHOSEONG) + Choseong.index(cho)) )
            else:
                obuff.append( CHOSEONG_FILLER )

            if jung:
                obuff.append( unichr(ord(JBASE_JUNGSEONG) + Jungseong.index(jung)) )
            else:
                obuff.append( JUNGSEONG_FILLER )

            if jong:
                obuff.append( unichr(ord(JBASE_JONGSEONG) + Jongseong.index(jong) - 1) )
        else:
            obuff.append(c)
    return u''.join(obuff)

def _has_final(c):
    # for internal use only
    if u'\uac00' <= c <= u'\ud7a3': # hangul
        return 1, (ord(c) - 0xac00) % 28 > 0
    else:
        return 0, c in u'013678.bklmnptLMNRZ'

# Iterator Emulator for ancient versions before 2.1
try:
    iter
except:
    class iter:
        def __init__(self, obj):
            self.obj = obj
            self.ptr = 0
        def next(self):
            try:
                return self.obj[self.ptr]
            finally:
                self.ptr += 1

# Nested scope lambda emulation for versions before 2.2
import sys
if sys.hexversion < '0x2020000':
    class plambda:
        def __init__(self, obj):
            self.obj = obj
        def __call__(self):
            return self.obj
else:
    plambda = None
del sys

def format(fmtstr, *args, **kwargs):
    if kwargs:
        argget = lambda:kwargs
        if plambda:
            argget = plambda(kwargs)
    else:
        argget = iter(args).next

    obuff = []
    ncur = escape = fmtinpth = 0
    ofmt = fmt = u''

    while ncur < len(fmtstr):
        c = fmtstr[ncur]

        if escape:
            obuff.append(c)
            escape = 0
            ofmt   = u''
        elif c == u'\\':
            escape = 1
        elif fmt:
            fmt += c
            if not fmtinpth and c.isalpha():
                ofmt = fmt % argget()
                obuff.append(ofmt)
                fmt = u''
            elif fmtinpth and c == u')':
                fmtinpth = 0
            elif c == u'(':
                fmtinpth = 1
            elif c == u'%':
                obuff.append(u'%')
        elif c == u'%':
            fmt  += c
            ofmt = u''
        else:
            if ofmt and ALT_SUFFIXES.has_key(c):
                obuff.append(ALT_SUFFIXES[c][
                    _has_final(ofmt[-1])[1] and 1 or 0
                ])
            elif ofmt and IDA_SUFFIXES.has_key(fmtstr[ncur:ncur+3]):
                sel = IDA_SUFFIXES[fmtstr[ncur:ncur+3]]
                ishan, hasfinal = _has_final(ofmt[-1])

                if hasfinal:
                    obuff.append(sel[1])
                elif ishan:
                    if sel[0]:
                        obuff[-1] = obuff[-1][:-1] + unichr(ord(ofmt[-1]) + sel[0])
                else:
                    obuff.append(sel[0] and sel[1])
                ncur += 2
            else:
                obuff.append(c)
    
            ofmt = u''

        ncur += 1
    
    return u''.join(obuff)


########NEW FILE########
__FILENAME__ = narrow
# -*- coding: utf-8 -*-
from hangulize import *


class NarrowGeorgian(Language):
    """For transcribing Georgian (narrow transcription).
    The lenis, fortis, and aspirated series of stops and affricates of Korean
    are all employed. The Georgian grapheme ვ is taken to be /w/ after an
    obstruent and before a vowel, to be /f/ after a vowel and before a
    voiceless stop or affricate, and to be /v/ in all other cases."""

    __iso639__ = {1: 'ka', 2: 'geo', 3: 'kat'}
    __tmp__ = ',;'

    vowels = u'აეიოუ'
    cs = u'ბგდვზთკლმნპჟრსტფქღყშჩცძწჭხჯჰV'
    vl = u'თკპტფქყჩცწჭ'
    ob = u'ბგდვზთკპჟსტფქღყშჩცძწჭხჯჰ'
    notation = Notation([
        (u'ჱ', u'ეჲ'),
        (u'ჲ', u'ი'),
        (u'უჳ', u'უ'),
        (u'ჳ', u'უ'),
        (u'ჴ', u'ხ'),
        (u'ჵ', u'ო'),
        (u'ჶ', u'ფ'),
        (u'{@}ვ{<vl>}', u'ჶ'),
        (u'ვ$', u'ჶ'),
        (u'ბბ', u'ბ'),
        (u'გგ', u'გ'),
        (u'დდ', u'დ'),
        (u'ვვ', u'ვ'),
        (u'ზზ', u'ზ'),
        (u'თთ', u'თ'),
        (u'კკ', u'კ'),
        (u'ლლ', u'ლ'),
        (u'მმ', u'მ,მ'),
        (u'ნნ', u'ნ,ნ'),
        (u'პპ', u'პ'),
        (u'ჟჟ', u'ჟ'),
        (u'რრ', u'რ'),
        (u'სს', u'ს'),
        (u'ტტ', u'ტ'),
        (u'ფფ', u'ფ'),
        (u'ქქ', u'ქ'),
        (u'ღღ', u'ღ'),
        (u'ყყ', u'ყ'),
        (u'შშ', u'შ'),
        (u'ხხ', u'ხ'),
        (u'ჰჰ', u'ჰ'),
        (u'დ{ძ|ჯ}', None),
        (u'თ{ჩ|ც}', None),
        (u'ტ{წ|ჭ}', None),
        (u'დჟ', u'ჯ'),
        (u'თშ', u'ჩ'),
        (u'ტშ', u'ჭ'),
        (u'დზ', u'ძ'),
        (u'თს', u'ც'),
        (u'ტს', u'წ'),
        (u'{<ob>}ვ{ა|ე|ი}', u'V'),
        (u'ჟ{<cs>}', u'ჟუ'),
        (u'ჟ$', u'ჟუ'),
        (u'შ{<cs>}', u'შუ'),
        (u'შ$', u'ში'),
        (u'ჩ{V}', u'ჩუ'),
        (u'ჩ{<cs>}', u'ჩი'),
        (u'ჩ$', u'ჩი'),
        (u'ძ{V}', u'ძუ'),
        (u'ძ{<cs>}', u'ძი'),
        (u'ძ$', u'ძი'),
        (u'ჭ{V}', u'ჭუ'),
        (u'ჭ{<cs>}', u'ჭი'),
        (u'ჭ$', u'ძი'),
        (u'^ლ', u'ლ;'),
        (u'^მ$', u'მ;'),
        (u'^ნ', u'ნ;'),
        (u'ლ$', u'ლ,'),
        (u'მ$', u'მ,'),
        (u'ნ$', u'ნ,'),
        (u'ლ{@|მ,|ნ,}', u'ლ;'),
        (u'{,}ლ', u'ლ;'),
        (u'მ{@}', u'მ;'),
        (u'ნ{@}', u'ნ;'),
        (u'ლ', u'ლ,'),
        (u'მ', u'მ,'),
        (u'ნ', u'ნ,'),
        (u',,', u','),
        (u',;', None),
        (u',ლ,', u'ლ,'),
        (u',მ,', u'მ,'),
        (u',ნ,', u'ნ,'),
        (u'ლ{მნ}', u'ლ,'),
        (u';', None),
        (u'აა', u'ა'),
        (u'ეე', u'ე'),
        (u'იი', u'ი'),
        (u'ოო', u'ო'),
        (u'უუ', u'უ'),
        (u'ბ', Choseong(B)),
        (u'გ', Choseong(G)),
        (u'დ', Choseong(D)),
        (u'ვ', Choseong(B)),
        (u'ზ', Choseong(J)),
        (u'თ', Choseong(T)),
        (u'კ', Choseong(GG)),
        (u'^ლ', Choseong(L)),
        (u'{,}ლ', Choseong(L)),
        (u'ლ,', Jongseong(L)),
        (u'ლ', Jongseong(L), Choseong(L)),
        (u'მ,', Jongseong(M)),
        (u'მ', Choseong(M)),
        (u'ნ,', Jongseong(N)),
        (u'ნ', Choseong(N)),
        (u'პ', Choseong(BB)),
        (u'ჟ', Choseong(J)),
        (u'რ', Choseong(L)),
        (u'ს', Choseong(S)),
        (u'ტ', Choseong(DD)),
        (u'ფ', Choseong(P)),
        (u'ქ', Choseong(K)),
        (u'ღ', Choseong(G)),
        (u'ყ', Choseong(GG)),
        (u'ჩ', Choseong(C)),
        (u'ც', Choseong(C)),
        (u'ძ', Choseong(J)),
        (u'წ', Choseong(JJ)),
        (u'ჭ', Choseong(JJ)),
        (u'ხ', Choseong(H)),
        (u'ჯ', Choseong(J)),
        (u'ჰ', Choseong(H)),
        (u'ჶ', Choseong(P)),
        (u'ჸ', Choseong(NG)),
        (u'შა', Choseong(S), Jungseong(YA)),
        (u'შე', Choseong(S), Jungseong(YE)),
        (u'ში', Choseong(S), Jungseong(I)),
        (u'შო', Choseong(S), Jungseong(YO)),
        (u'შუ', Choseong(S), Jungseong(YU)),
        (u'შჷ', Choseong(S), Jungseong(YEO)),
        (u'Vა', Choseong(NG), Jungseong(WA)),
        (u'Vე', Choseong(NG), Jungseong(WE)),
        (u'Vი', Choseong(NG), Jungseong(WI)),
        (u'ა', Jungseong(A)),
        (u'ე', Jungseong(E)),
        (u'ი', Jungseong(I)),
        (u'ო', Jungseong(O)),
        (u'უ', Jungseong(U)),
        (u'ჷ', Jungseong(EO)),
    ])

    def normalize(self, string):
        return normalize_roman(string, {
            u'Ⴀ': u'ა', u'ⴀ': u'ა', u'Ⴁ': u'ბ', u'ⴁ': u'ბ', u'Ⴂ': u'გ',
            u'ⴂ': u'გ', u'Ⴃ': u'დ', u'ⴃ': u'დ', u'Ⴄ': u'ე', u'ⴄ': u'ე',
            u'Ⴅ': u'ვ', u'ⴅ': u'ვ', u'Ⴆ': u'ზ', u'ⴆ': u'ზ', u'Ⴡ': u'ჱ',
            u'ⴡ': u'ჱ', u'Ⴇ': u'თ', u'ⴇ': u'თ', u'Ⴈ': u'ი', u'ⴈ': u'ი',
            u'Ⴉ': u'კ', u'ⴉ': u'კ', u'Ⴊ': u'ლ', u'ⴊ': u'ლ', u'Ⴋ': u'მ',
            u'ⴋ': u'მ', u'Ⴌ': u'ნ', u'ⴌ': u'ნ', u'Ⴢ': u'ჲ', u'ⴢ': u'ჲ',
            u'Ⴍ': u'ო', u'ⴍ': u'ო', u'Ⴎ': u'პ', u'ⴎ': u'პ', u'Ⴏ': u'ჟ',
            u'ⴏ': u'ჟ', u'Ⴐ': u'რ', u'ⴐ': u'რ', u'Ⴑ': u'ს', u'ⴑ': u'ს',
            u'Ⴒ': u'ტ', u'ⴒ': u'ტ', u'Ⴣ': u'ჳ', u'ⴣ': u'ჳ', u'Ⴍ': u'უ',
            u'ⴍ': u'უ', u'Ⴔ': u'ფ', u'ⴔ': u'ფ', u'Ⴕ': u'ქ', u'ⴕ': u'ქ',
            u'Ⴖ': u'ღ', u'ⴖ': u'ღ', u'Ⴗ': u'ყ', u'ⴗ': u'ყ', u'Ⴘ': u'შ',
            u'ⴘ': u'შ', u'Ⴙ': u'ჩ', u'ⴙ': u'ჩ', u'Ⴚ': u'ც', u'ⴚ': u'ც',
            u'Ⴛ': u'ძ', u'ⴛ': u'ძ', u'Ⴜ': u'წ', u'ⴜ': u'წ', u'Ⴝ': u'ჭ',
            u'ⴝ': u'ჭ', u'Ⴞ': u'ხ', u'ⴞ': u'ხ', u'Ⴤ': u'ჴ', u'ⴤ': u'ჴ',
            u'Ⴟ': u'ჯ', u'ⴟ': u'ჯ', u'Ⴠ': u'ჰ', u'ⴠ': u'ჰ', u'Ⴥ': u'ჵ',
            u'ⴥ': u'ჵ'
        })


__lang__ = NarrowGeorgian

########NEW FILE########
__FILENAME__ = br
# -*- coding: utf-8 -*-
from hangulize import *


class BrazilianPortuguese(Language):
    """For transcribing Brazilian Portuguese."""

    __iso639__ = {1: 'pt', 2: 'por', 3: 'por'}
    __tmp__ = ',;~'

    vowels = u'aAeEiIoOuUQ'
    cs = u'bcCdfghjklmnpqrRsStvwxz'
    son = u'lmnr' # sonorant
    vl = u'cCfkpqRsSt' # voiceless
    notation = Notation([
        (u'ã', 'A~'),
        (u'á', 'A'),
        (u'â', 'A'),
        (u'sç', 'S'),
        (u'ç', 'S'),
        (u'é', 'E'),
        (u'ê', 'E'),
        (u'õ', 'O~'),
        (u'ó', 'O'),
        (u'ô', 'O'),
        ('dumont$', 'dumon'),
        ('^eduar', 'Eduar'),
        ('^eldorado', 'Eldorado'),
        ('^joA~', 'juA~'),
        ('^mirra$', 'mira'),
        ('bb', 'b'),
        ('cc', 'c'),
        ('dd', 'd'),
        ('ff', 'f'),
        ('gg', 'g'),
        ('hh', 'h'),
        ('jj', 'j'),
        ('kk', 'k'),
        ('ll', 'l'),
        ('mm', 'm'),
        ('nn', 'n'),
        ('pp', 'p'),
        ('qq', 'q'),
        ('tt', 't'),
        ('vv', 'v'),
        ('ww', 'w'),
        ('xx', 'x'),
        ('zz', 'z'),
        ('ch', 'C'),
        ('lh', 'L'),
        ('nh', 'N'),
        ('^ex{@}', 'ez'),
        ('^hex{@}', 'ez'),
        ('~e', '~i'),
        ('A~o', 'A~'),
        ('c{k|q}', None),
        ('sc{e|E|i}', 'S'),
        ('ssc{e|E|i}', 'S'),
        ('xc{e|E|i}', 'S'),
        ('xs', 'S'),
        ('xss', 'S'),
        ('ss', 'S'),
        ('c{e|E|i}', 'S'),
        ('c', 'k'),
        ('x{@}', 'C'),
        ('x', 'S'),
        ('g{e|E|i}', 'j'),
        ('{g|q}u{e|E|i}', None),
        ('^e{a$|(<cs>)a$|(<cs>)(<cs>)a$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)a$}', 'E'),
        ('^e{am$|(<cs>)am$|(<cs>)(<cs>)am$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)am$}', 'E'),
        ('^e{ans$|(<cs>)ans$|(<cs>)(<cs>)ans$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)ans$}', 'E'),
        ('^e{as$|(<cs>)as$|(<cs>)(<cs>)as$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)as$}', 'E'),
        ('^e{o$|(<cs>)o$|(<cs>)(<cs>)o$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)o$}', 'E'),
        ('^e{om$|(<cs>)om$|(<cs>)(<cs>)om$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)om$}', 'E'),
        ('^e{ons$|(<cs>)ons$|(<cs>)(<cs>)ons$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)ons$}', 'E'),
        ('^e{os$|(<cs>)os$|(<cs>)(<cs>)os$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)os$}', 'E'),
        ('^e{e$|(<cs>)e$|(<cs>)(<cs>)e$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)e$}', 'E'),
        ('^e{em$|(<cs>)em$|(<cs>)(<cs>)em$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)em$}', 'E'),
        ('^e{ens$|(<cs>)ens$|(<cs>)(<cs>)ens$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)ens$}', 'E'),
        ('^e{es$|(<cs>)es$|(<cs>)(<cs>)es$}', 'E'),
        ('^e{(<cs>)(<cs>)(<cs>)es$}', 'E'),
        ('^e', 'i'),
        ('e$', 'i'),
        ('o$', 'u'),
        ('os$', 'us'),
        ('{p|b|m|f|v|g|q}es$', 'Es'),
        ('es$', 'is'),
        ('q', 'k'),
        ('ou', 'o'),
        ('A', 'a'),
        ('E', 'e'),
        ('I', 'i'),
        ('O', 'o'),
        ('U', 'u'),
        ('aa', 'a'),
        ('ee', 'e'),
        ('oo', 'o'),
        ('uu', 'u'),
        ('yy', 'iy'),
        ('^y{@}', 'Y'),
        ('{@}y{@}', 'Y'),
        ('y', 'i'),
        ('ii', 'i'),
        ('m$', '~'),
        ('n$', '~'),
        ('ns$', '~s'),
        ('n{g|k}', '~'),
        ('^r', 'R'),
        ('{n|l|s}r', 'R'),
        ('rr', 'R'),
        ('^s', 'S'),
        ('{<vl>}s', 'S'),
        ('{@}s{@}', 'z'),
        ('s{@}', 'S'),
        ('s{<vl>}', 'S'),
        ('s$', 'S'),
        ('s', 'Z'),
        ('z{@}', 'Z'),
        ('z{<vl>}', 'S'),
        ('z$', 'S'),
        ('Z', 'z'),
        ('k{<son>}', 'F'),
        ('{@}k{<cs>}', 'k,'),
        ('F', 'k'),
        ('C{@}', 'SY'),
        ('C', 'Si'),
        ('N{@}', 'nY'),
        ('N', 'n'),
        ('L{@}', 'lY'),
        ('L', 'l'),
        ('^l', 'l;'),
        ('^m', 'm;'),
        ('^n', 'n;'),
        ('ul$', 'ul,'),
        ('l$', 'u'),
        ('l{<cs>}', 'u'),
        ('m$', 'm,'),
        ('n$', 'n,'),
        ('l', 'l;'),
        ('m{@}', 'm;'),
        ('n{@|Y}', 'n;'),
        ('m', 'm,'),
        ('n', 'n,'),
        ('~', '~,'),
        (',,', ','),
        (',;', None),
        (',m,', 'm,'),
        (',n,', 'n,'),
        (';', None),
        ('^w', 'W'),
        ('{@|g|k}w', 'W'),
        ('w', 'QW'),
        ('di', 'ji'),
        ('ti', 'Ti'),
        ('b', Choseong(B)),
        ('d', Choseong(D)),
        ('f', Choseong(P)),
        ('g', Choseong(G)),
        ('j', Choseong(J)),
        ('j', None),
        ('k,', Jongseong(G)),
        ('k', Choseong(K)),
        ('^l', Choseong(L)),
        ('l,', Jongseong(L)),
        ('{,}l', Choseong(L)),
        ('l', Jongseong(L), Choseong(L)),
        ('m,', Jongseong(M)),
        ('m', Choseong(M)),
        ('n,', Jongseong(N)),
        ('n', Choseong(N)),
        ('~', Jongseong(NG)),
        ('p,', Jongseong(B)),
        ('p', Choseong(P)),
        ('r', Choseong(L)),
        ('R', Choseong(H)),
        ('S', Choseong(S)),
        ('t,', Jongseong(S)),
        ('t', Choseong(T)),
        ('T', Choseong(C)),
        ('v', Choseong(B)),
        ('z', Choseong(J)),
        ('Ya', Jungseong(YA)),
        ('Ye', Jungseong(YE)),
        ('Yi', Jungseong(I)),
        ('Yo', Jungseong(YO)),
        ('Yu', Jungseong(YU)),
        ('YQ', Jungseong(EU)),
        ('Wa', Jungseong(WA)),
        ('We', Jungseong(WE)),
        ('Wi', Jungseong(WI)),
        ('Wo', Jungseong(WEO)),
        ('Wu', Jungseong(U)),
        ('WQ', Jungseong(E)),
        ('a', Jungseong(A)),
        ('e', Jungseong(E)),
        ('i', Jungseong(I)),
        ('o', Jungseong(O)),
        ('u', Jungseong(U)),
        ('Q', Jungseong(EU)),
        ('h', None),
    ])

    def normalize(self, string):
        return normalize_roman(string, {
            u'Ã': u'ã', u'Á': u'á', u'Â': u'â', u'Ç': u'ç', u'É': u'é',
            u'Ê': u'ê', u'ê': u'é', u'Õ': u'õ', u'Ó': u'ó', u'Ô': u'ô'
        })


__lang__ = BrazilianPortuguese

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
    hangulize.models
    ~~~~~~~~~~~~~~~~

    :copyright: (c) 2010-2013 by Heungsub Lee
    :license: BSD, see LICENSE for more details.
"""
import functools
import re
import sys

from hangulize.hangul import *


SPACE = ' '
ZWSP = '/' # zero-width space
EDGE = chr(3)
SPECIAL = chr(6)
BLANK = '(?:%s)' % '|'.join(map(re.escape, (SPACE, ZWSP, EDGE, SPECIAL)))
DONE = chr(0)
ENCODING = getattr(sys.stdout, 'encoding', 'utf-8')
EMPTY_TUPLE = ()


def cached_property(func, name=None):
    if name is None:
        name = func.__name__
    def get(self):
        try:
            return self.__dict__[name]
        except KeyError:
            val = func(self)
            self.__dict__[name] = val
            return val
    functools.update_wrapper(get, func)
    def del_(self):
        self.__dict__.pop(name, None)
    return property(get, None, del_)


class Phoneme(object):
    """This abstract class wraps a Hangul letter."""

    def __init__(self, letter):
        self.letter = letter

    def __repr__(self):
        name = type(self).__name__
        return "<%s '%s'>" % (name, self.letter.encode(ENCODING))


class Choseong(Phoneme):
    """A initial consonant in Hangul.

        >>> Choseong(G)
        <Choseung 'ㄱ'>
    """

    pass


class Jungseong(Phoneme):
    """A vowel in Hangul.

        >>> Jungseong(A)
        <Jungseong 'ㅏ'>
    """

    pass


class Jongseong(Phoneme):
    """A final consonant in Hangul.

        >>> Jongseong(G)
        <Jongseong 'ㄱ'>
    """

    pass


class Impurity(Phoneme):
    """An impurity letter will be kept."""

    pass


class Notation(object):
    """Describes loanword orthography.

    :param rules: the rewrite rules as an ordered key-value list
    """

    def __init__(self, rules):
        self.rules = rules

    def __add__(self, rules):
        if isinstance(rules, Notation):
            rules = rules.rules
        return Notation(self.rules + rules)

    def __radd__(self, lrules):
        if isinstance(lrules, Notation):
            lrules = lrules.rules
        return Notation(lrules + self.rules)

    def __iter__(self):
        if not getattr(self, '_rewrites', None):
            self._rewrites = [Rewrite(*item) for item in self.items()]
        return iter(self._rewrites)

    def items(self, left_edge=False, right_edge=False, lang=None):
        """Yields each notation rules as regex."""
        for one in self.rules:
            pattern = one[0]
            # accept *args
            if len(one) == 2:
                val = one[1]
                if isinstance(val, Phoneme):
                    val = val,
            # accept args(a tuple instance)
            else:
                val = one[1:]
            yield pattern, val

    @property
    def chars(self):
        """The humane characters from the notation keys."""
        chest = []
        for one in self.rules:
            pattern = Rewrite.VARIABLE_PATTERN.sub('', one[0])
            pattern = re.sub(r'[\{\}\@\[\]\^\$]', '', pattern)
            for c in pattern:
                chest.append(c)
        return set(chest)


class Language(object):
    """Wraps a foreign language. The language should have a :class:`Notation`
    instance.

        >>> class Extraterrestrial(Language):
        ...     notation = Notation([
        ...         (u'ㅹ', (Choseong(BB), Jungseong(U), Jongseong(NG))),
        ...         (u'㉠', (Choseong(G),)),
        ...         (u'ㅣ', (Jungseong(I),)),
        ...         (u'ㅋ', (Choseong(K), Jungseong(I), Jongseong(G)))
        ...     ])
        ...
        >>> ext = Extraterrestrial()
        >>> print ext.hangulize(u'ㅹ㉠ㅣㅋㅋㅋ')
        뿡기킥킥킥

    :param logger: a logger
    """

    __tmp__ = ''
    __special__ = '.,;?~"()[]{}'

    vowels = EMPTY_TUPLE
    notation = None

    def __new__(cls):
        if not getattr(cls, '_instances', None):
            cls._instances = {}
        if cls not in cls._instances:
            cls._instances[cls] = object.__new__(cls)
        return cls._instances[cls]

    def __init__(self):
        if not isinstance(self.notation, Notation):
            raise NotImplementedError("notation has to be defined")

    @cached_property
    def _steal_specials(self):
        def keep(match, rewrite):
            """keep special characters."""
            self._specials.append(match.group(0))
            return SPECIAL
        esc = '(%s)' % '|'.join(re.escape(x) \
                                for x in self.__special__ + self.__tmp__)
        return Rewrite(esc, keep)

    @cached_property
    def _recover_specials(self):
        def escape(match, rewrite):
            """escape special characters."""
            return (Impurity(self._specials.pop(0)),)
        return Rewrite(SPECIAL, escape)

    @cached_property
    def _remove_tmp(self):
        tmp = '(%s)' % '|'.join(re.escape(x) for x in self.__tmp__)
        return Rewrite(tmp, None)

    @property
    def chars_pattern(self):
        """The regex pattern which is matched the valid characters."""
        return ''.join(re.escape(c) for c in self.notation.chars)

    def split(self, string):
        """Splits words from the string. Each words have only valid characters.
        """
        pattern = '[^%s]+' % self.chars_pattern
        return re.split(pattern, string)

    def transcribe(self, string, logger=None):
        """Returns :class:`Phoneme` instance list from the word."""
        string = re.sub(r'\s+', SPACE, string)
        string = re.sub(r'^|$', EDGE, string)
        self._specials = []
        phonemes = []

        # steal special characters
        string = self._steal_specials(string, phonemes)
        # apply the notation
        for rewrite in self.notation:
            string = rewrite(string, phonemes, lang=self, logger=logger)
        # remove temporary characters
        string = self._remove_tmp(string, phonemes)
        # recover special characters
        string = self._recover_specials(string, phonemes)

        # post processing
        string = re.sub('^' + BLANK, '', string)
        string = re.sub(BLANK + '$', '', string)
        phonemes = phonemes[1:-1]
        string = _hold_spaces(string, phonemes)
        string = _remove_zwsp(string, phonemes)
        string = _pass_unmatched(string, phonemes)

        # flatten
        phonemes = reduce(list.__add__, map(list, filter(None, phonemes)), [])
        return phonemes

    def normalize(self, string):
        """Before transcribing, normalizes the string. You could specify the
        different normalization for the language with overriding this method.
        """
        return string

    def hangulize(self, string, logger=None):
        """Hangulizes the string.

            >>> from hangulize.langs.ja import Japanese
            >>> ja = Japanese()
            >>> ja.hangulize(u'あかちゃん')
            아카찬
        """
        from hangulize.processing import complete_syllables
        def stringify(syllable):
            if isinstance(syllable[0], Impurity):
                return syllable[0].letter
            else:
                return join(syllable)
        if not isinstance(string, unicode):
            string = string.decode()
        string = self.normalize(string)
        logger and logger.info(">> '%s'" % string)
        phonemes = self.transcribe(string, logger=logger)
        try:
            syllables = complete_syllables(phonemes)
            result = [stringify(syl) for syl in syllables]
            hangulized = ''.join(result)
        except TypeError:
            hangulized = u''
        logger and logger.info('=> %s' % hangulized)
        return hangulized

    @property
    def iso639_1(self):
        return self.__iso639__.get(1)

    @property
    def iso639_2(self):
        return self.__iso639__.get(2)

    @property
    def iso639_3(self):
        return self.__iso639__.get(3)

    @property
    def code(self):
        return re.sub('^hangulize\.langs\.', '', type(self).__module__)


class Rewrite(object):

    VOWELS_PATTERN = re.compile('@')
    VARIABLE_PATTERN = re.compile('<(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>')
    LEFT_EDGE_PATTERN = re.compile(r'^(\^?)\^')
    RIGHT_EDGE_PATTERN = re.compile(r'\$(\$?)$')
    LOOKBEHIND_PATTERN = re.compile('^(?P<edge>(?:\^(?:\^)?)?){([^}]+?)}')
    LOOKAHEAD_PATTERN = re.compile('{([^}]+?)}(?P<edge>(?:\$(?:\$)?)?)$')
    def NEGATIVE(regex):
        pattern = regex.pattern.replace('{', '{~')
        return re.compile(pattern)
    NEGATIVE_LOOKBEHIND_PATTERN = NEGATIVE(LOOKBEHIND_PATTERN)
    NEGATIVE_LOOKAHEAD_PATTERN = NEGATIVE(LOOKAHEAD_PATTERN)
    del NEGATIVE

    def __init__(self, pattern, val):
        """Makes a replace function with the given pattern and value."""
        self.pattern, self.val = pattern, val
        self.__regexes__ = {}

    def __call__(self, string, phonemes=None, lang=None, logger=None):
        # allocate needed offsets
        if not phonemes and isinstance(phonemes, list):
            phonemes += [None] * len(string)

        regex = self.compile_pattern(lang)

        # replacement function
        if phonemes:
            deletions = []
        def repl(match):
            val = self.val(match, self) if callable(self.val) else self.val
            repls.append(val)
            start, end = match.span()

            if val:
                is_tuple = isinstance(val, tuple)
                if not is_tuple:
                    if lang:
                        # variable replacement
                        cls = type(self)
                        srcvars = cls.find_actual_variables(self.pattern)
                        dstvars = cls.find_actual_variables(self.val)
                        srcvars, dstvars = list(srcvars), list(dstvars)
                        if len(srcvars) == len(dstvars) == 1:
                            src = getattr(lang, srcvars[0].group('name'))
                            dst = getattr(lang, dstvars[0].group('name'))
                            if len(src) != len(dst):
                                msg = 'the destination variable should ' \
                                      'have the same length with the ' \
                                      'source variable'
                                raise ValueError(msg)
                            dictionary = dict(zip(src, dst))
                            let = dictionary[match.group(0)]
                            val = self.VARIABLE_PATTERN.sub(let, val)
                        # group reference
                        val = re.sub(r'\\(\d+)',
                                     lambda m: match.group(int(m.group(1))),
                                     val)
                    if phonemes:
                        for x in xrange(len(val) - len(match.group(0))):
                            phonemes.insert(start, None)
                    return val
                elif phonemes and is_tuple:
                    # toss phonemes, and check the matched string
                    phonemes[start] = val
                    return DONE * (end - start)
            else:
                # when val is None, the matched string should remove
                if phonemes:
                    deletions.append((start, end))
                return ''

        if logger:
            prev = string
        repls = []

        # replace the string
        string = regex.sub(repl, string)

        # remove kept deletions
        if phonemes:
            for start, end in reversed(deletions):
                del phonemes[start:end]

        if logger:
            # report changes
            if prev != string:
                val = repls.pop()
                args = (string, self.pattern)
                if not val:
                    msg = ".. '%s'\tremove %s" % args
                elif isinstance(val, tuple):
                    val = ''.join(x.letter for x in val)
                    msg = ".. '%s'\thangulize %s -> %s" % (args + (val,))
                else:
                    msg = ".. '%s'\trewrite %s -> %s" % (args + (val,))
                logger.info(msg)
                #print phonemes

        return string

    def compile_pattern(self, lang=None):
        if lang not in self.__regexes__:
            regex = re.compile(type(self).regexify(self.pattern, lang))
            self.__regexes__[lang] = regex
        return self.__regexes__[lang]

    @classmethod
    def regexify(cls, pattern, lang=None):
        regex = pattern
        if lang:
            regex = cls.regexify_variable(regex, lang)
        regex = cls.regexify_negative_lookaround(regex)
        regex = cls.regexify_lookaround(regex)
        regex = cls.regexify_edge_of_word(regex)
        return regex

    @classmethod
    def regexify_edge_of_word(cls, regex):
        left_edge = r'(?<=\1%s)' % BLANK
        right_edge = r'(?=%s\1)' % BLANK
        regex = cls.LEFT_EDGE_PATTERN.sub(left_edge, regex)
        regex = cls.RIGHT_EDGE_PATTERN.sub(right_edge, regex)
        return regex

    def _make_lookaround(behind_pattern, ahead_pattern,
                        behind_prefix, ahead_prefix):
        @staticmethod
        def meth(regex):
            def lookbehind(match):
                edge = re.sub('\^$', BLANK, match.group('edge'))
                return '(?' + behind_prefix + edge + \
                       '(?:' + match.group(2) + '))'
            def lookahead(match):
                edge = re.sub('^\$', BLANK, match.group('edge'))
                return '(?' + ahead_prefix + \
                       '(?:' + match.group(1) + ')' + edge + ')'
            regex = behind_pattern.sub(lookbehind, regex)
            regex = ahead_pattern.sub(lookahead, regex)
            return regex
        return meth

    _positive = _make_lookaround(LOOKBEHIND_PATTERN,
                                 LOOKAHEAD_PATTERN,
                                 '<=', '=')
    _negative = _make_lookaround(NEGATIVE_LOOKBEHIND_PATTERN,
                                 NEGATIVE_LOOKAHEAD_PATTERN,
                                 '<!', '!')
    regexify_lookaround = _positive
    regexify_negative_lookaround = _negative
    del _make_lookaround, _positive, _negative

    @classmethod
    def regexify_variable(cls, regex, lang):
        def to_variable(match):
            var = getattr(lang, match.group('name'))
            return '(%s)' % '|'.join(re.escape(x) for x in var)
        regex = cls.VOWELS_PATTERN.sub('<vowels>', regex)
        regex = cls.VARIABLE_PATTERN.sub(to_variable, regex)
        return regex

    @classmethod
    def find_actual_variables(cls, pattern):
        # pass when there's no any variable patterns
        if not cls.VOWELS_PATTERN.search(pattern) and \
           not cls.VARIABLE_PATTERN.search(pattern):
            return EMPTY_TUPLE
        try:
            pattern = cls.LOOKBEHIND_PATTERN.sub(DONE, pattern)
            pattern = cls.LOOKAHEAD_PATTERN.sub(DONE, pattern)
            pattern = cls.VOWELS_PATTERN.sub('<>', pattern)
            return cls.VARIABLE_PATTERN.finditer(pattern)
        except TypeError:
            return EMPTY_TUPLE


_remove_zwsp = Rewrite(ZWSP, (Impurity(''),))
_hold_spaces = Rewrite(SPACE, (Impurity(' '),))
_pass_unmatched = Rewrite('[^' + DONE + ']+',
                          lambda m, r: (Impurity(m.group(0)),))


HangulizeError = Exception
LanguageError = ValueError
InvalidCodeError = ValueError

########NEW FILE########
__FILENAME__ = normalization
# -*- coding: utf-8 -*-
"""
    hangulize.normalization
    ~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2010-2013 by Heungsub Lee
    :license: BSD, see LICENSE for more details.
"""
import unicodedata


def normalize_roman(string, additional=None):
    """Removes diacritics from the string and converts to lowercase.

        >>> normalize_roman(u'Eèé')
        u'eee'
    """
    if additional:
        safe = additional.keys() + additional.values()
        def gen():
            for c in string:
                if c not in safe:
                    yield normalize_roman(c)
                elif c in additional:
                    yield additional[c]
                else:
                    yield c
        return ''.join(gen())
    else:
        chars = []
        for c in string:
            if unicodedata.category(c) == 'Lo':
                chars.append(c)
            else:
                nor = unicodedata.normalize('NFD', c)
                chars.extend(x for x in nor if unicodedata.category(x) != 'Mn')
        return ''.join(chars).lower()

########NEW FILE########
__FILENAME__ = processing
# -*- coding: utf-8 -*-
"""
    hangulize.processing
    ~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2010-2013 by Heungsub Lee
    :license: BSD, see LICENSE for more details.
"""
from hangulize.hangul import *
from hangulize.models import *


def complete_syllable(syllable):
    """Inserts the default jungseong or jongseong if it is not exists.

        >>> complete_syllable((Jungseong(YO),))
        (u'ㅇ', u'ㅛ', u'')
        >>> print hangulize.hangul.join(_)
        요
    """
    syllable = list(syllable)
    components = [type(ph) for ph in syllable]
    if Choseong not in components:
        syllable.insert(0, Choseong(NG))
    if Jungseong not in components:
        syllable.insert(1, Jungseong(EU))
    if Jongseong not in components:
        syllable.insert(2, Jungseong(Null))
    return tuple((ph.letter for ph in syllable))


def complete_syllables(phonemes):
    """Separates each syllables and completes every syllable."""
    components, syllable = [Choseong, Jungseong, Jongseong], []
    if phonemes:
        for ph in phonemes:
            comp = type(ph)
            new_syllable = comp is Impurity or syllable and \
                           components.index(comp) <= \
                           components.index(type(syllable[-1]))
            if new_syllable:
                if syllable:
                    yield complete_syllable(syllable)
                    syllable = []
                if comp is Impurity:
                    yield (ph,)
                    continue
            syllable.append(ph)
        if syllable:
            yield complete_syllable(syllable)


def split_phonemes(word):
    """Returns the splitted phonemes from the word.

        >>> split_phonemes(u'안녕') #doctest: +NORMALIZE_WHITESPACE
        (<Choseong 'ㅇ'>, <Jungseong 'ㅏ'>, <Jongseong 'ㄴ'>,
         <Choseong 'ㄴ'>, <Jungseong 'ㅕ'>, <Jongseong 'ㅇ'>)
    """
    result = []
    for c in word:
        try:
            c = split(c)
            result.append(Choseong(c[0]))
            result.append(Jungseong(c[1]))
            if c[2] is not Null:
                result.append(Jongseong(c[2]))
        except UnicodeHangulError:
            result.append(Impurity(c))
    return tuple(result)


def join_phonemes(phonemes):
    """Returns the word from the splitted phonemes.

        >>> print join_phonemes((Jungseong(A), Jongseong(N),
        ...                      Choseong(N), Jungseong(YEO), Jongseong(NG)))
        안녕
    """
    syllables = complete_syllables(phonemes)
    chars = (join(syl) for syl in syllables)
    return reduce(unicode.__add__, chars)

########NEW FILE########
__FILENAME__ = aze
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.aze import Azerbaijani


class AzerbaijaniTestCase(HangulizeTestCase):

    lang = Azerbaijani()

    def test_people(self):
        self.assert_examples({
            u'Namiq Abdullayev': u'나미크 아브둘라예프',
            u'Qəmər Almaszadə': u'게메르 알마스자데',
            u'Heydər Əliyev': u'헤이데르 엘리예프',
            u'İlham Əliyev': u'일함 엘리예프',
            u'Hüseyn Ərəblinski': u'휘세인 에레블린스키',
            u'Rəşid Behbudov': u'레시트 베흐부도프',
            u'Bülbül': u'뷜뷜',
            u'Cəfər Cabbarlı': u'제페르 자발르',
            u'Vaqif Cavadov': u'바기프 자바도프',
            u'Hüseyn Cavid': u'휘세인 자비트',
            u'Füzuli': u'퓌줄리',
            u'Üzeyir Hacıbəyov': u'위제이르 하즈베요프',
            u'Mehdi Hüseynzadə': u'메흐디 휘세인자데',
            u'Kərim Kərimov': u'케림 케리모프',
            u'Fərid Mansurov': u'페리트 만수로프',
            u'Elnur Məmmədli': u'엘누르 멤메들리',
            u'Məhəmməd Mövlazadə': u'메헴메트 뫼블라자데',
            u'Əzizə Mustafazadə': u'에지제 무스타파자데',
            u'Vaqif Mustafazadə': u'바기프 무스타파자데',
            u'Mikayıl Müşfiq': u'미카이을 뮈슈피크',
            u'Xurşidbanu Natəvan': u'후르시드바누 나테반',
            u'Hüseyn xan Naxçıvanski': u'휘세인 한 나흐츠반스키',
            u'Nəriman Nərimanov': u'네리만 네리마노프',
            u'İmadəddin Nəsimi': u'이마데딘 네시미',
            u'Mir-Möhsün Nəvvab': u'미르뫼흐쉰 네바프',
            u'Ramil Quliyev': u'라밀 굴리예프',
            u'Nigar Rəfibəyli': u'니가르 레피베일리',
            u'Artur Rəsizadə': u'아르투르 레시자데',
            u'Məhəmməd Əmin Rəsulzadə': u'메헴메트 에민 레술자데',
            u'Süleyman Rüstəm': u'쉴레이만 뤼스템',
            u'Rəsul Rza': u'레술 르자',
            u'Rəşad Sadıqov': u'레샤트 사드고프',
            u'Məmməd ağa Şahtaxtinski': u'멤메트 아가 샤흐타흐틴스키',
            u'Məhəmmədhüseyn Şəhriyar': u'메헴메트휘세인 셰흐리야르',
            u'Nigar Şıxlinskaya': u'니가르 시으흘린스카야',
            u'Zeynalabdin Tağıyev': u'제이날라브딘 타그예프',
            u'Aysel Teymurzadə': u'아이셀 테이무르자데',
            u'Səməd Vurğun': u'세메트 부르군',
            u'Fətəli xan Xoyski': u'페텔리 한 호이스키',
        })

    def test_places(self):
        self.assert_examples({
            u'Abşeron': u'압셰론',
            u'Ağdam': u'아그담',
            u'Azərbaycan': u'아제르바이잔',
            u'Bakı': u'바크',
            u'Gəncə': u'겐제',
            u'İçəri Şəhər': u'이체리 셰헤르',
            u'Lənkəran': u'렌케란',
            u'Mingəçevir': u'민게체비르',
            u'Naftalan': u'나프탈란',
            u'Naxçıvan': u'나흐츠반',
            u'Qəbələ': u'게벨레',
            u'Qobustan': u'고부스탄',
            u'Salyan': u'살리안',
            u'Sumqayıt': u'숨가이으트',
            u'Şəki': u'셰키',
            u'Şəmkir': u'솀키르',
            u'Şirvan': u'시르반',
            u'Talış': u'탈르슈',
            u'Tovuz': u'토부스',
            u'Xaçmaz': u'하치마스',
            u'Xınalıq': u'흐날르크',
            u'Xırdalan': u'흐르달란',
            u'Yevlax': u'예블라흐',
            u'Zaqatala': u'자가탈라',
        })

    def test_others(self):
        self.assert_examples({
            u'jurnal': u'주르날',
        })

########NEW FILE########
__FILENAME__ = bel
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.bel import Belarusian


class BelarusianTestCase(HangulizeTestCase):

    lang = Belarusian()

    def test_people(self):
        self.assert_examples({
            u'Аляксей Абалмасаў': u'알략세이 아발마사우',
            u'Вікторыя Азарэнка': u'빅토리야 아자렌카',
            u'Святлана Алексіевіч': u'스뱌틀라나 알렉시예비치',
            u'Францішак Аляхновіч': u'프란치샤크 알랴흐노비치',
            u'Андрэй Арамнаў': u'안드레이 아람나우',
            u'Алег Ахрэм': u'알레크 아흐렘',
            u'Максім Багдановіч': u'막심 바흐다노비치',
            u'Святлана Багінская': u'스뱌틀라나 바힌스카야',
            u'Францішак Багушэвіч': u'프란치샤크 바후셰비치',
            u'Сымон Будны': u'시몬 부드니',
            u'Аляксандр Глеб': u'알략산드르 흘레프',
            u'Яўген Глебаў': u'야우헨 흘레바우',
            u'Аляксей Грышын': u'알략세이 흐리신',
            u'Вінцэнт Дунін-Марцінкевіч': u'빈첸트 두닌마르친케비치',
            u'Ефрасіння Полацкая': u'예프라신냐 폴라츠카야',
            u'Кастусь Каліноўскі': u'카스투스 칼리노우스키',
            u'Кацярына Карстэн': u'카차리나 카르스텐',
            u'Якуб Колас': u'야쿠프 콜라스',
            u'Янка Купала': u'얀카 쿠팔라',
            u'Вацлаў Ластоўскі': u'바츨라우 라스토우스키',
            u'Аляксандр Лукашэнка': u'알략산드르 루카셴카',
            u'Ігар Лучанок': u'이하르 루차노크',
            u'Вадзім Махнеў': u'바짐 마흐네우',
            u'Юлія Несцярэнка': u'율리야 네스차렌카',
            u'Аляксандр Патупа': u'알략산드르 파투파',
            u'Іпаці Пацей': u'이파치 파체이',
            u'Алаіза Пашкевіч': u'알라이자 파슈케비치',
            u'Наталля Пяткевіч': u'나탈랴 퍄트케비치',
            u'Радзівіл': u'라지빌',
            u'Максім Рамашчанка': u'막심 라마샨카',
            u'Міхаіл Савіцкі': u'미하일 사비츠키',
            u'Леў Сапега': u'레우 사페하',
            u'Ян Серада': u'얀 세라다',
            u'Францыск Скарына': u'프란치스크 스카리나',
            u'Раман Скірмунт': u'라만 스키르문트',
            u'Мялецій Сматрыцкі': u'먈레치 스마트리츠키',
            u'Ян Станкевіч': u'얀 스탄케비치',
            u'Фёдар Сумкін': u'표다르 숨킨',
            u'Браніслаў Тарашкевіч': u'브라니슬라우 타라슈케비치',
            u'Віктар Тураў': u'빅타르 투라우',
            u'Мікалай Улашчык': u'미칼라이 울라시크',
            u'Фёдар Фёдараў': u'표다르 표다라우',
            u'Ян Чачот': u'얀 차초트',
        })

    def test_places(self):
        self.assert_examples({
            u'Бабруйск': u'바브루이스크',
            u'Баранавічы': u'바라나비치',
            u'Белавежская пушча': u'벨라베슈스카야 푸샤',
            u'Беларусь': u'벨라루스',
            u'Брэст': u'브레스트',
            u'Віцебск': u'비쳅스크',
            u'Гомель': u'호멜',
            u'Гродна': u'흐로드나',
            u'Камянец': u'카먀네츠',
            u'Магілёў': u'마힐료우',
            u'Мінск': u'민스크',
            u'Мір': u'미르',
            u'Мураванка': u'무라반카',
            u'Нясвіж': u'냐스비시',
            u'Полацк': u'폴라츠크',
            u'Сынкавічы': u'신카비치',
        })

########NEW FILE########
__FILENAME__ = bul
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.bul import Bulgarian


class BulgarianTestCase(HangulizeTestCase):

    lang = Bulgarian()

    def test_people(self):
        self.assert_examples({
            u'Димитър Бербатов': u'디미터르 베르바토프',
            u'Петър Берон': u'페터르 베론',
            u'Илия Бешков': u'일리야 베슈코프',
            u'Петър Богдан': u'페터르 보그단',
            u'Христо Ботев': u'흐리스토 보테프',
            u'Златьо Бояджиев': u'즐라툐 보야지에프',
            u'Никола Вапцаров': u'니콜라 밥차로프',
            u'Гаврил Радомир': u'가브릴 라도미르',
            u'Иван Евстратиев Гешов': u'이반 에프스트라티에프 게쇼프',
            u'Мария Гроздева': u'마리야 그로즈데바',
            u'Николай Гяуров': u'니콜라이 갸우로프',
            u'Екатерина Дафовска': u'에카테리나 다포프스카',
            u'Григор Димитров': u'그리고르 디미트로프',
            u'Гена Димитрова': u'게나 디미트로바',
            u'Галина Дурмушлийска': u'갈리나 두르무슐리스카',
            u'Цанко Дюстабанов': u'찬코 듀스타바노프',
            u'Людмила Дяковска': u'류드밀라 댜코프스카',
            u'Тодор Живков': u'토도르 지프코프',
            u'Иван Рилски': u'이반 릴스키',
            u'Ренета Инджова': u'레네타 인조바',
            u'Елена Йончева': u'엘레나 욘체바',
            u'Асен Йорданов': u'아센 요르다노프',
            u'Райна Кабаиванска': u'라이나 카바이반스카',
            u'Матей Казийски': u'마테이 카지스키',
            u'Константин Тих': u'콘스탄틴 티흐',
            u'Алеко Константинов': u'알레코 콘스탄티노프',
            u'Емил Костадинов': u'에밀 코스타디노프',
            u'Стефка Костадинова': u'스테프카 코스타디노바',
            u'Крум': u'크룸',
            u'Юлия Кръстева': u'율리야 크러스테바',
            u'Весела Лечева': u'베셀라 레체바',
            u'Йордан Лечков': u'요르단 레치코프',
            u'Андрей Луканов': u'안드레이 루카노프',
            u'Димитър Механджийски': u'디미터르 메한지스키',
            u'Иван Милев': u'이반 밀레프',
            u'Михаил Шишман': u'미하일 시슈만',
            u'Иван Мърквичка': u'이반 머르크비치카' ,
            u'Георги Наджаков': u'게오르기 나자코프',
            u'Иван Павлов': u'이반 파블로프',
            u'Паисий Хилендарски': u'파이시 힐렌다르스키',
            u'Стилиян Петров': u'스틸리얀 페트로프',
            u'Григор Пърличев': u'그리고르 퍼를리체프',
            u'Анна-Мария Равнополска-Дийн': u'안나마리야 라브노폴스카딘',
            u'Александър Райчев': u'알렉산더르 라이체프',
            u'Симеон Велики': u'시메온 벨리키',
            u'Пенчо Славейков': u'펜초 슬라베이코프',
            u'Стефан Стамболов': u'스테판 스탐볼로프',
            u'Теодосий Синаитски': u'테오도시 시나이츠키',
            u'Цветан Тодоров': u'츠베탄 토도로프',
            u'Христо Стоичков': u'흐리스토 스토이치코프',
            u'Борис Христов': u'보리스 흐리스토프',
            u'Григорий Цамблак': u'그리고리 참블라크',
            u'Драган Цанков': u'드라간 찬코프',
            u'Христо Явашев': u'흐리스토 야바셰프',
        })

    def test_places(self):
        self.assert_examples({
            u'Асеновград': u'아세노브그라드',
            u'Банско': u'반스코',
            u'Бургас': u'부르가스',
            u'Варна': u'바르나',
            u'Девня': u'데브냐',
            u'Добрич': u'도브리치',
            u'Добърско': u'도버르스코',
            u'Дуранкулак': u'두란쿨라크',
            u'Евксиноград': u'에프크시노그라드',
            u'Златоград': u'즐라토그라드',
            u'Искър': u'이스커르',
            u'Исперих': u'이스페리흐',
            u'Казанлък': u'카잔러크',
            u'Кърджали': u'커르잘리',
            u'Кюстендил': u'큐스텐딜',
            u'Мадара': u'마다라',
            u'Малко Търново': u'말코 터르노보',
            u'Мелник': u'멜니크',
            u'Мусала': u'무살라',
            u'Несебър': u'네세버르',
            u'Панагюрище': u'파나규리슈테',
            u'Петрич': u'페트리치',
            u'Пещера': u'페슈테라',
            u'Пирин': u'피린',
            u'Плевен': u'플레벤',
            u'Пловдив': u'플로브디프',
            u'Ралица': u'랄리차',
            u'Рила': u'릴라',
            u'Родопи': u'로도피',
            u'Свещари': u'스베슈타리',
            u'Созопол': u'소조폴',
            u'София': u'소피야',
            u'Сливен': u'슬리벤',
            u'Смолян': u'스몰랸',
            u'Стара Загора': u'스타라 자고라',
            u'Търговище' : u'터르고비슈테',
        })
########NEW FILE########
__FILENAME__ = cat
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.cat import Catalan


class CatalanTestCase(HangulizeTestCase):

    lang = Catalan()

    def test_people(self):
        self.assert_examples({
            u'Arantxa': u'아란차',
            u'Valentí Almirall': u'발렌티 알미랄',
            u'Jaume Bartumeu': u'자우메 바르투메우',
            u'Sergi Bruguera': u'세르지 브루게라',
            u'Montserrat Caballé': u'몬세라트 카발례',
            u'Santiago Calatrava': u'산티아고 칼라트라바',
            u'Joan Capdevila': u'조안 캅데빌라',
            u'Josep Carner': u'조제프 카르네르',
            u'Pau Casals': u'파우 카잘스',
            u'Lluís Companys': u'류이스 콤파니스',
            u'Àlex Corretja': u'알렉스 코레자',
            u'Albert Costa': u'알베르트 코스타',
            u'Salvador Dalí': u'살바도르 달리',
            u'Salvador Espriu': u'살바도르 에스프리우',
            u'Cesc Fàbregas': u'세스크 파브레가스',
            u'Pau Gasol': u'파우 가졸',
            u'Antoni Gaudí': u'안토니 가우디',
            u'Josep Guardiola': u'조제프 과르디올라',
            u'Xavi Hernández': u'샤비 에르난데스',
            u'Ramon Llull': u'라몬 률',
            u'Francesc Macià i Llussà': u'프란세스크 마시아 이 류사',
            u'Joan Maragall': u'조안 마라갈',
            u'Ausiàs March': u'아우지아스 마르크',
            u'Joanot Martorell': u'조아노트 마르토렐',
            u'Joan Miró': u'조안 미로',
            u'Gerard Piqué': u'제라르트 피케',
            u'Josep Pla': u'조제프 플라',
            u'Eudald Pradell': u'에우달 프라델',
            u'Carles Puyol': u'카를레스 푸욜',
            u'Mercè Rodoreda': u'메르세 로도레다',
            u'Jordi Savall': u'조르디 사발',
            u'Joan Manuel Serrat': u'조안 마누엘 세라트',
            u'Joaquim Sorolla': u'조아킴 소롤랴',
            u'Antoni Tàpies': u'안토니 타피에스',
            u'Josep Tarradellas': u'조제프 타라델랴스',
            u'Jordi Tarrés': u'조르디 타레스',
            u'Jacint Verdaguer': u'자신 베르다게르',
        })

    def test_places(self):
        self.assert_examples({
            u'Alacant': u'알라칸',
            u'Andorra': u'안도라',
            u'Andorra la Vella': u'안도라 라 벨랴',
            u'Barcelona': u'바르셀로나',
            u'Berga': u'베르가',
            u'Besalú': u'베잘루',
            u'Catalunya': u'카탈루냐',
            u'Cerdanya': u'세르다냐',
            u'Conflent': u'콘플렌',
            u'Eivissa': u'에이비사',
            u'Elx': u'엘시',
            u'Empúries': u'엠푸리에스',
            u'Figueres': u'피게레스',
            u'Girona': u'지로나',
            u'Lleida': u'례이다',
            u'Manresa': u'만레자',
            u'Montjuïc': u'몬주이크',
            u'Montserrat': u'몬세라트',
            u'Osona': u'오조나',
            u'Pallars': u'팔랴르스',
            u'Pallars Jussà': u'팔랴르스 주사',
            u'Pallars Sobirà': u'팔랴르스 소비라',
            u'Palma': u'팔마',
            u'Ribagorça': u'리바고르사',
            u'Rosselló': u'로셀료',
            u'Tarragona': u'타라고나',
            u'Urgell': u'우르젤',
            u'València': u'발렌시아',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'Barça': u'바르사',
            u'Camp Nou': u'캄 노우',
            u'Canigó': u'카니고',
            u'Espanyol': u'에스파뇰',
            u'estel·lar': u'에스텔라르',
            u'llengua': u'롕과',
            u'modernisme': u'모데르니즈메',
            u'Renaixença': u'레나셴사',
            u'Sagrada Família': u'사그라다 파밀리아',
        })
########NEW FILE########
__FILENAME__ = ces
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.ces import Czech


class CzechTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0209.jsp """

    lang = Czech()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0107.jsp """
        self.assert_examples({
            u'barva': u'바르바',
            u'obchod': u'옵호트',
            u'dobrý': u'도브리',
            u'jeřab': u'예르자프',
            u'cigareta': u'치가레타',
            u'nemocnice': u'네모츠니체',
            u'nemoc': u'네모츠',
            u'čapek': u'차페크',
            u'kulečnik': u'쿨레치니크',
            u'míč': u'미치',
            u'dech': u'데흐',
            u'divadlo': u'디바들로',
            u'led': u'레트',
            u"ďábel": u'댜벨',
            u"loďka": u'로티카',
            u"hruď": u'흐루티',
            u'fík': u'피크',
            u'knoflík': u'크노플리크',
            u'gramofon': u'그라모폰',
            u'hadr': u'하드르',
            u'hmyz': u'흐미스',
            u'bůh': u'부흐',
            u'choditi': u'호디티',
            u'chlapec': u'흘라페츠',
            u'prach': u'프라흐',
            u'kachna': u'카흐나',
            u'nikdy': u'니크디',
            u'padák': u'파다크',
            u'lev': u'레프',
            u'šplhati': u'슈플하티',
            u'postel': u'포스텔',
            u'most': u'모스트',
            u'mrak': u'므라크',
            u'podzim': u'포드짐',
            u'noha': u'노하',
            u'podmínka': u'포드민카',
            u'němý': u'네미',
            u'sáňky': u'산키',
            u'Plzeň': u'플젠',
            u'Praha': u'프라하',
            u'koroptev': u'코롭테프',
            u'strop': u'스트로프',
            u'quasi': u'크바시',
            u'ruka': u'루카',
            u'harmonika': u'하르모니카',
            u'mír': u'미르',
            u'řeka': u'르제카',
            u'námořník': u'나모르주니크',
            u'hořký': u'호르슈키',
            u'kouř': u'코우르시',
            u'sedlo': u'세들로',
            u'máslo': u'마슬로',
            u'nos': u'노스',
            u'šaty': u'샤티',
            u'šternberk': u'슈테른베르크',
            u'koš': u'코시',
            u'tam': u'탐',
            u'matka': u'마트카',
            u'bolest': u'볼레스트',
            u'tělo': u'텔로',
            u'štěstí': u'슈테스티',
            u"oběť": u'오베티',
            u'vysoký': u'비소키',
            u'knihovna': u'크니호브나',
            u'kov': u'코프',
            u'xerox': u'제록스',
            u'saxofón': u'삭소폰',
            u'zámek': u'자메크',
            u'pozdní': u'포즈드니',
            u'bez': u'베스',
            u'žižka': u'지슈카',
            u'žvěřina': u'주베르지나',
            u'Brož': u'브로시',
            u'jaro': u'야로',
            u'pokoj': u'포코이',
            u'balík': u'발리크',
            u'komár': u'코마르',
            u'dech': u'데흐',
            u'léto': u'레토',
            u'šest': u'셰스트',
            u'věk': u'베크',
            u'kino': u'키노',
            u'míra': u'미라',
            u'obec': u'오베츠',
            u'nervózni': u'네르보즈니',
            u'buben': u'부벤',
            u'úrok': u'우로크',
            u'dům': u'둠',
            u'jazýk': u'야지크',
            u'líný': u'리니',
        })

    def test_1st(self):
        """제1항: k, p
        어말과 유성 자음 앞에서는 '으'를 붙여 적고, 무성 자음 앞에서는
        받침으로 적는다.
        """
        self.assert_examples({
            u'mozek': u'모제크',
            u'koroptev': u'코롭테프',
        })

    def test_2nd(self):
        """제2항: b, d, d', g
        1. 어말에 올 때에는 '프', '트', '티', '크'로 적는다.
        2. 유성 자음 앞에서는 '브', '드', '디', '그'로 적는다.
        3. 무성 자음 앞에서 b, g는 받침으로 적고, d, d'는 '트', '티'로 적는다.
        """
        self.assert_examples({
            u'led': u'레트',
            u'ledvina': u'레드비나',
            u'obchod': u'옵호트',
            u'odpadky': u'오트파트키',
        })

    def test_3nd(self):
        """제3항: v, w, z, ř, ž, š
        1. v, w, z가 무성 자음 앞이나 어말에 올 때에는 '프, 프, 스'로 적는다.
        2. ř, ž가 유성 자음 앞에 올 때에는 '르주', '주', 무성 자음 앞에 올
           때에는 '르슈', '슈', 어말에 올 때에는 '르시', '시'로 적는다.
        3. š는 자음 앞에서는 '슈', 어말에서는 '시'로 적는다.
        """
        self.assert_examples({
            u'hmyz': u'흐미스',
            u'námořník': u'나모르주니크',
            u'hořký': u'호르슈키',
            u'kouř': u'코우르시',
            u'puška': u'푸슈카',
            u'myš': u'미시',
        })

    def test_4th(self):
        """제4항: l, lj
        어중의 l, lj가 모음 앞에 올 때에는 'ㄹㄹ', 'ㄹ리'로 적는다.
        """
        self.assert_examples({
            u'kolo': u'콜로',
        })

    def test_5th(self):
        """제5항: m
        m이 r 앞에 올 때에는 '으'를 붙여 적는다.
        """
        self.assert_examples({
            u'humr': u'후므르',
        })

    def test_6th(self):
        """제6항
        자음에 '예'가 결합되는 경우에는 '예' 대신에 '에'로 적는다. 다만,
        자음이 'ㅅ'인 경우에는 '셰'로 적는다.
        """
        self.assert_examples({
            u'věk': u'베크',
            u'šest': u'셰스트',
        })
########NEW FILE########
__FILENAME__ = cym
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.cym import Welsh


class WelshTestCase(HangulizeTestCase):

    lang = Welsh()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'Cymru': u'컴리',
            u'Cymraeg': u'컴라이그',
            u'Caernarfon': u'카이르나르본',
            u'Ceredigion': u'케레디기온',
            u'Aberystwyth': u'아베러스투이스',
            u'Brynmawr': u'브런마우르',
            u'Llangollen': u'흘란고흘렌',
            u'Llanelli': u'흘라네흘리',
            u'Gwynedd': u'귀네드',
            u'Ystradgynlais': u'어스트라드건라이스',
            u'Tawe': u'타웨',
            u'Powys': u'포위스',
            u'Meredith': u'메레디스',
            u'Glyndŵr': u'글런두르',
            u'Rhys': u'흐리스',
            u'Ifans': u'이반스',
            u'Emrys': u'엠리스',
            u'Hywel': u'허웰',
            u'Gwilym': u'귈림',
            u'Llinor': u'흘리노르',
            u'Ieuan': u'예이안',
            u'Cerys': u'케리스',
            u'Dafydd': u'다비드',
            u'Iwan': u'이완',
            u'Huw': u'히우',
            u'Ciaran': u'키아란',
            u'Myfanwy': u'머바누이',
            u'Llywelyn': u'흘러웰린',
            u'Calennig': u'칼레니그',
            u'cnapan': u'크나판',
            u'cwm': u'쿰',
            u'fy ngwely': u'벙 웰리',
            u'fy nhadau': u'번 하다이',
            u"Banc Ty'nddôl": u'방크 턴돌',
        })
########NEW FILE########
__FILENAME__ = deu
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.deu import German


class GermanTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0202.jsp """

    lang = German()

    def test_1st(self):
        """제1항: 
        1. 자음 앞의 는 '으'를 붙여 적는다.
        2. 어말의 '는 '어'로 적는다.
        3. 복합어 및 파생어의 선행 요소가 로 끝나는 경우는 2의 규정을 준용한다.
        """
        self.assert_examples({
            u'Hormon': u'호르몬',
            u'Hermes': u'헤르메스',
            u'Herr': u'헤어',
            u'Rasur': u'라주어',
            u'Tür': u'튀어',
            u'Ohr': u'오어',
            u'Vater': u'파터',
            u'Schiller': u'실러',
        # 합성어
        #    u'verarbeiten': u'페어아르바이텐',
        #    u'zerknirschen': u'체어크니르셴',
        #    u'Fürsorge': u'퓌어조르게',
        #    u'Vorbild': u'포어빌트',
        #    u'auβerhalb': u'아우서할프',
        #    u'Urkunde': u'우어쿤데',
        #    u'Vaterland': u'파터란트',
        })

    def test_2nd(self):
        """제2항: 어말의 파열음은 '으'를 붙여 적는 것을 원칙으로 한다."""
        self.assert_examples({
        #    u'Rostock': u'로스토크', # 규칙?
            u'Stadt': u'슈타트',
        })

    def test_3rd(self):
        """제3항: 철자 'berg', 'burg'는 '베르크', '부르크'로 통일해서 적는다."""
        self.assert_examples({
            u'Heidelberg': u'하이델베르크',
            u'Hamburg': u'함부르크',
        })

    def test_4th(self):
        """제4항: 
        1. 어말 또는 자음 앞에서는 '슈'로 적는다.
        2.  앞에서는 'ㅅ'으로 적는다.
        3. 그 밖의 모음 앞에서는 뒤따르는 모음에 따라 '샤, 쇼, 슈' 등으로 적는다.
        """
        self.assert_examples({
            u'Mensch': u'멘슈',
            u'Mischling': u'미슐링',
            u'Schüler': u'쉴러',
            u'schön': u'쇤',
            u'Schatz': u'샤츠',
            u'schon': u'숀',
            u'Schule': u'슐레',
            u'Schelle': u'셸레',
        })

    def test_5th(self):
        """제5항: 로 발음되는 äu, eu는 '오이'로 적는다."""
        self.assert_examples({
            u'läuten': u'로이텐',
            u'Fräulein': u'프로일라인',
            u'Europa': u'오이로파',
            u'Freundin': u'프로인딘',
        })

    def test_6th(self):
        """연음, -st, ich/achlaut, 움라우트, 강세음절의 r"""
        self.assert_examples({
            u'ein': u'아인',
            u'einer': u'아이너',
            u'einen': u'아이넨',
            u'ist': u'이스트',
            u'bist': u'비스트',
            u'Buch': u'부흐',
            u'ich': u'이히',
            u'Königen': u'쾨니겐',
            u'für': u'퓌어',
            u'der': u'데어',
        })

    def test_7th(self):
        """준칙: 모음 또는 l 앞의 ng에는 'ㄱ'을 첨가하여 표기한다."""
        self.assert_examples({
            u'Tübingen': u'튀빙겐',
            u'Spengler': u'슈펭글러',
        })

    def test_8th(self):
        """기타 용례"""
        self.assert_examples({
            u'Fischer': u'피셔',
            u'Richard': u'리하르트',
            u'Niclas': u'니클라스',
            u'Kupfer': u'쿠퍼',
            u'Beelitz': u'벨리츠',
        })
########NEW FILE########
__FILENAME__ = ell
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.ell import Greek


class GreekTestCase(HangulizeTestCase):

    lang = Greek()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'Αγαμέμνων': u'아가멤논',
            u'Άγγελος': u'앙겔로스',
            u'Άγια Βαρβάρα': u'아야 바르바라',
            u'Αγία Παρασκευή': u'아이아 파라스케비',
            u'Αγιά Σοφιά': u'아야 소피아',
            u'Άγιος Δημήτριος': u'아요스 디미트리오스',
            u'Άγκυρα': u'앙기라',
            u'Αγρίνιο': u'아그리니오',
            u'άγχος': u'앙호스',
            u'Αθανάσιος': u'아타나시오스',
            u'Αθήνα': u'아티나',
            u'Αιγαίο': u'에예오',
            u'Αιγάλεω': u'에갈레오',
            u'Αιολίδα': u'에올리다',
            u'αισθάνομαι': u'에스타노메',
            u'ακαδημία': u'아카디미아',
            u'Αλεξάνδρεια': u'알렉산드리아',
            u'Αλεξανδρούπολη': u'알렉산드루폴리',
            u'Αλέξης': u'알렉시스',
            u'Άλιμος': u'알리모스',
            u'Αμπελόκηποι Θεσσαλονίκης': u'암벨로키피 테살로니키스',
            u'Αναστάσιος': u'아나스타시오스',
            u'Ανδρέας': u'안드레아스',
            u'Άνθιμος': u'안티모스',
            u'Άννα': u'아나',
            u'Ανταρκτική': u'안다르크티키',
            u'Αντώνης': u'안도니스',
            u'απηύδησα': u'아피브디사',
            u'Αργυρούπολη': u'아르이루폴리',
            u'Αρκτικός': u'아르크티코스',
            u'Αρμονία': u'아르모니아',
            u'άρπυια': u'아르피아',
            u'άτεκνη': u'아테크니',
            u'ατμοσφαίρας': u'아트모스페라스',
            u'Αττική': u'아티키',
            u'αυθεντικός': u'아프텐디코스',
            u'άυλος': u'아일로스',
            u'Αυξεντίου': u'아프크센디우',
            u'αύριο': u'아브리오',
            u'αυτός': u'아프토스',
            u'Αχαρνές': u'아하르네스',
            u'Βάρη': u'바리',
            u'Βάρκιζα': u'바르키자',
            u'Βασίλης': u'바실리스',
            u'βασιλιάς': u'바실리아스',
            u'Βέροια': u'베리아',
            u'βιβλίο': u'비블리오',
            u'βίντσι': u'빈치',
            u'βοήθειες': u'보이티에스',
            u'Βόλος': u'볼로스',
            u'βορράς': u'보라스',
            u'Βουλιαγμένη': u'불리아그메니',
            u'Βύρωνας': u'비로나스',
            u'Γαλάτσι': u'갈라치',
            u'γάντζος': u'간조스',
            u'Γαύδος': u'가브도스',
            u'γεννώ': u'예노',
            u'Γεωργία': u'예오르이아',
            u'Γεώργιος': u'예오르요스',
            u'Γιάννης': u'야니스',
            u'γιατρός': u'야트로스',
            u'Γιωργία': u'요르이아',
            u'Γιώργος': u'요르고스',
            u'γκαλερί': u'갈레리',
            u'Γκέκας': u'게카스',
            u'γκρίζος': u'그리조스',
            u'Γλυφάδα': u'글리파다',
            u'Γρηγόρης': u'그리고리스',
            u'Γρηγόριος': u'그리고리오스',
            u'γυαλί': u'얄리',
            u'γυναίκα': u'이네카',
            u'Δαίδαλος': u'데달로스',
            u'Δανάη': u'다나이',
            u'Δανιηλίδου': u'다니일리두',
            u'Δάφνη': u'다프니',
            u'δέντρο': u'덴드로',
            u'Δέσποινα': u'데스피나',
            u'Δημήτηρ': u'디미티르',
            u'Δημήτρης': u'디미트리스',
            u'δημοκρατία': u'디모크라티아',
            u'Δημολέων': u'디몰레온',
            u'διάλεκτος': u'디알렉토스',
            u'Διογένης': u'디오예니스',
            u'Διομήδης': u'디오미디스',
            u'Διόνυσος': u'디오니소스',
            u'δόγης': u'도이스',
            u'Δράμα': u'드라마',
            u'δυϊκός': u'디이코스',
            u'Δυρράχιο': u'디라히오',
            u'έβδομη': u'에브도미',
            u'Ειρήνη': u'이리니',
            u'είσαι': u'이세',
            u'εκθαμνίσητε': u'엑탐니시테',
            u'έκκλησιν': u'에클리신',
            u'εκπνέω': u'엑프네오',
            u'εκπρόσωπος': u'엑프로소포스',
            u'εκφράσω': u'엑프라소',
            u'ελεγκτής': u'엘렝티스',
            u'έλεγχος': u'엘렝호스',
            u'Ελένη': u'엘레니',
            u'Ελεύθερος': u'엘레프테로스',
            u'Ελευσίνα': u'엘레프시나',
            u'Ελλάδα': u'엘라다',
            u'Ελύτης': u'엘리티스',
            u'έξυπνη': u'엑시프니',
            u'επηυξημένος': u'에피프크시메노스',
            u'Ερμιόνη': u'에르미오니',
            u'Έσδρας': u'에스드라스',
            u'Ετεοκλή': u'에테오클리',
            u'Ευαγγέλιον': u'에방겔리온',
            u'Εύβοια': u'에비아',
            u'Ευγενία': u'에브예니아',
            u'Ευκλείδης': u'에프클리디스',
            u'Ευλαλία': u'에블랄리아',
            u'Εύξεινος': u'에프크시노스',
            u'Εύοσμος': u'에보스모스',
            u'έυπνον': u'에이프논',
            u'Ευριδίκη': u'에브리디키',
            u'Ευρώπη': u'에브로피',
            u'Ευστάθιος': u'에프스타티오스',
            u'ευφορία': u'에포리아',
            u'ευφράδεια': u'에프라디아',
            u'ευχαριστώ': u'에프하리스토',
            u'ευχή': u'에프히',
            u'Ζαγοράκης': u'자고라키스',
            u'Ζαχαρίας': u'자하리아스',
            u'Ζεύγμα': u'제브그마',
            u'Ζολώτας': u'졸로타스',
            u'Ζωγράφου': u'조그라푸',
            u'Ζωή': u'조이',
            u'ηθοποιός': u'이토피오스',
            u'Ηλέκτρα': u'일렉트라',
            u'ηλεκτρονικά': u'일렉트로니카',
            u'Ηλιούπολη': u'일리우폴리',
            u'Ήπειρος': u'이피로스',
            u'Ηράκλειο': u'이라클리오',
            u'Ηρακλής': u'이라클리스',
            u'Ησαΐας': u'이사이아스',
            u'ηυξημένου': u'이프크시메누',
            u'Θάνου': u'타누',
            u'Θεοδωράκης': u'테오도라키스',
            u'Θεόδωρος': u'테오도로스',
            u'Θεοφάνης': u'테오파니스',
            u'Θεόφιλος': u'테오필로스',
            u'Θεσσαλία': u'테살리아',
            u'Θεσσαλονίκη': u'테살로니키',
            u'Θήβα': u'티바',
            u'Θράκη': u'트라키',
            u'Ιάκωβος': u'이아코보스',
            u'Ιαλυσός': u'이알리소스',
            u'Ιάνθη': u'이안티',
            u'Ιάσονας': u'이아소나스',
            u'Ιερεμίας': u'이에레미아스',
            u'Ίλιον': u'일리온',
            u'Ισμήνη': u'이스미니',
            u'ιστορία': u'이스토리아',
            u'Ιφιγένεια': u'이피예니아',
            u'Ιωακείμ': u'이오아킴',
            u'Ιωάννινα': u'이오아니나',
            u'Ιωσήφ': u'이오시프',
            u'Καβάλα': u'카발라',
            u'Καβάφη': u'카바피',
            u'Καζαντζάκης': u'카잔자키스',
            u'Καθαρεύουσα': u'카타레부사',
            u'καλά': u'칼라',
            u'Καλαμαριά': u'칼라마리아',
            u'Καλαμάτα': u'칼라마타',
            u'Καλλιθέα': u'칼리테아',
            u'Καλλιόπη': u'칼리오피',
            u'Καλλιρρόη': u'칼리로이',
            u'Κάλυμνος': u'칼림노스',
            u'Κάλχας': u'칼하스',
            u'κανένα': u'카네나',
            u'Καραμανλής': u'카라만리스',
            u'Κασσάνδρα': u'카산드라',
            u'Κατερίνη': u'카테리니',
            u'Κατσουράνης': u'카추라니스',
            u'Κάυστρος': u'카이스트로스',
            u'καυτός': u'카프토스',
            u'Κερατσίνι': u'케라치니',
            u'Κέρκυρα': u'케르키라',
            u'Κεϋλάνη': u'케일라니',
            u'Κεφαλλονιά': u'케팔로니아',
            u'Κηφισιά': u'키피시아',
            u'κινηματογράφος': u'키니마토그라포스',
            u'Κλεοπάτρα': u'클레오파트라',
            u'Κλυταιμνήστρα': u'클리템니스트라',
            u'Κοζάνη': u'코자니',
            u'κοινή': u'키니',
            u'κόμμα': u'코마',
            u'Κομοτηνή': u'코모티니',
            u'Κορυδαλλός': u'코리달로스',
            u'κόσμος': u'코스모스',
            u'Κόων': u'코온',
            u'Κρήτη': u'크리티',
            u'Κρινώ': u'크리노',
            u'Κύπρος': u'키프로스',
            u'Κυργιάκος': u'키르야코스',
            u'Κωκυτός': u'코키토스',
            u'Λάιος': u'라이오스',
            u'Λαμία': u'라미아',
            u'Λάρισα': u'라리사',
            u'Λειψοί': u'립시',
            u'λεπτό': u'렙토',
            u'Λέσβος': u'레스보스',
            u'Λεύκτρα': u'레프크트라',
            u'Λεωδάμας': u'레오다마스',
            u'Λεωνίδας': u'레오니다스',
            u'λιοντάρι': u'리온다리',
            u'Λουκά': u'루카',
            u'Λυκαβηττός': u'리카비토스',
            u'μαγειρειό': u'마이리오',
            u'Μαΐου': u'마이우',
            u'Μακεδονία': u'마케도니아',
            u'Μάνδρα': u'만드라',
            u'Μαργαρίτα': u'마르가리타',
            u'Μάρθα': u'마르타',
            u'Μαρία': u'마리아',
            u'Μάρκος': u'마르코스',
            u'Μαρούσι': u'마루시',
            u'Ματθαίος': u'마테오스',
            u'Ματθίας': u'마티아스',
            u'μαύρος': u'마브로스',
            u'μεζές': u'메제스',
            u'Μελπομένη': u'멜포메니',
            u'Μενέλαος': u'메넬라오스',
            u'Μεσογείων': u'메소이온',
            u'Μετέωρα': u'메테오라',
            u'Μίκης': u'미키스',
            u'Μιλτιάδης': u'밀티아디스',
            u'Μιχάλης': u'미할리스',
            u'μοιραία': u'미레아',
            u'μονοθεϊστική': u'모노테이스티키',
            u'μουσακάς': u'무사카스',
            u'μουσική': u'무시키',
            u'Μούσχουρη': u'무스후리',
            u'Μπενάκη': u'베나키',
            u'μπρούντζος': u'브룬조스',
            u'μπωλ': u'볼',
            u'Μύκονος': u'미코노스',
            u'μυρμήγκι': u'미르밍기',
            u'μωβ': u'모브',
            u'Νάξος': u'낙소스',
            u'Νάρκισσος': u'나르키소스',
            u'ναυάγησε': u'나바이세',
            u'Νέα Ιωνία': u'네아 이오니아',
            u'Νέα Σμύρνη': u'네아 스미르니',
            u'Νέα Φιλαδέλφεια': u'네아 필라델피아',
            u'Νέστωρ': u'네스토르',
            u'Νίκαια': u'니케아',
            u'Νίκανδρος': u'니칸드로스',
            u'Νικάνωρ': u'니카노르',
            u'Νικόλαος': u'니콜라오스',
            u'Νικολάου': u'니콜라우',
            u'Ξανά': u'크사나',
            u'Ξάνθη': u'크산티',
            u'Ξανθίππη': u'크산티피',
            u'ξεϋφαίνω': u'크세이페노',
            u'Οδυσσέας': u'오디세아스',
            u'Ολυμπιακός': u'올림비아코스',
            u'Όλυμπος': u'올림보스',
            u'Παγγαία': u'팡게아',
            u'Παγδατής': u'파그다티스',
            u'Παλαιό Φάληρο': u'팔레오 팔리로',
            u'Παλαιό Ψυχικό': u'팔레오 프시히코',
            u'Παναγιώτης': u'파나요티스',
            u'Παναθηναϊκός': u'파나티나이코스',
            u'Παπαδόπουλος': u'파파도풀로스',
            u'Παπανδρέου': u'파판드레우',
            u'παπούτσια': u'파푸치아',
            u'Πάρις': u'파리스',
            u'Πάτρα': u'파트라',
            u'πατριάς': u'파트리아스',
            u'παύω': u'파보',
            u'Πειραιάς': u'피레아스',
            u'Πελασγία': u'펠라스이아',
            u'Πελασγός': u'펠라스고스',
            u'Πελοπόννησος': u'펠로포니소스',
            u'Πέμπτη': u'펨티',
            u'πέντε': u'펜데',
            u'Περιστέρι': u'페리스테리',
            u'Πέτρος': u'페트로스',
            u'Πετρούπολη': u'페트루폴리',
            u'Πεύκη': u'페프키',
            u'Πηνελόπη': u'피넬로피',
            u'πηγή': u'피이',
            u'Πιερής': u'피에리스',
            u'Πισσαρίδης': u'피사리디스',
            u'Πλάκα': u'플라카',
            u'Πλάτων': u'플라톤',
            u'Πολίχνη Θεσσαλονίκης': u'폴리흐니 테살로니키스',
            u'Πόλυβος': u'폴리보스',
            u'Πολυνείκης': u'폴리니키스',
            u'Πρίαμος': u'프리아모스',
            u'Προκόπιος': u'프로코피오스',
            u'προστατεύω': u'프로스타테보',
            u'προϋπολογίζω': u'프로이폴로이조',
            u'ρίχνω': u'리흐노',
            u'Ρόδος': u'로도스',
            u'Σάββας': u'사바스',
            u'Σάββατο': u'사바토',
            u'σάλπιγξ': u'살핑크스',
            u'Σάρα': u'사라',
            u'Σελήνη': u'셀리니',
            u'Σεπφώρα': u'세포라',
            u'Σέρρες': u'세레스',
            u'Σεφέρης': u'세페리스',
            u'Σημίτης': u'시미티스',
            u'σκέπτομαι': u'스켑토메',
            u'Σμύρνη': u'스미르니',
            u'Σπάρτη': u'스파르티',
            u'Σπυρίδων': u'스피리돈',
            u'Σταυρούπολη': u'스타브루폴리',
            u'Στέφανος': u'스테파노스',
            u'στρατηγός': u'스트라티고스',
            u'Στρογγυλή': u'스트롱길리',
            u'Στυλιανός': u'스틸리아노스',
            u'Συγγραφείς': u'싱그라피스',
            u'σύγχρονος': u'싱흐로노스',
            u'Συκιές': u'시키에스',
            u'Συμεών': u'시메온',
            u'συμφωνώ': u'심포노',
            u'Σύνταγμα': u'신다그마',
            u'Σωκράτης': u'소크라티스',
            u'Ταλθύβιος': u'탈티비오스',
            u'Τάσσος': u'타소스',
            u'ταυ': u'타프',
            u'Ταΰγετος': u'타이예토스',
            u'τέσσερα': u'테세라',
            u'τζατζίκι': u'자지키',
            u'Τζόρβας': u'조르바스',
            u'Τιμόθεος': u'티모테오스',
            u'Τραϊανός': u'트라이아노스',
            u'Τρίκαλα': u'트리칼라',
            u'Υάκινθος': u'이아킨토스',
            u'υγειά': u'이야',
            u'υιός': u'이오스',
            u'Υπατία': u'이파티아',
            u'υπήρξεν': u'이피르크센',
            u'Φίλιππος': u'필리포스',
            u'Φιλιππούπολη': u'필리푸폴리',
            u'Φοίβη': u'피비',
            u'φτάνω': u'프타노',
            u'Φυλλίς': u'필리스',
            u'Χαϊδάρι': u'하이다리',
            u'χαϊδεύω': u'하이데보',
            u'χαίρετε': u'헤레테',
            u'Χαλάνδρι': u'할란드리',
            u'Χάλκη': u'할키',
            u'Χαλκίδα': u'할키다',
            u'Χανιά': u'하니아',
            u'χαρακτήρα': u'하락티라',
            u'Χαριστέας': u'하리스테아스',
            u'χέρι': u'헤리',
            u'χθες': u'흐테스',
            u'Χίος': u'히오스',
            u'Χοϊδάς': u'호이다스',
            u'Χρύσης': u'흐리시스',
            u'χρώματα': u'흐로마타',
            u'Ψέριμος': u'프세리모스',
            u'ψωμί': u'프소미',
            u'Ωνάσης': u'오나시스',
        })
########NEW FILE########
__FILENAME__ = epo
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.epo import Esperanto


class EsperantoTestCase(HangulizeTestCase):

    lang = Esperanto()

    def test_examples_in_wikipedia(self):
        """ http://ko.wikipedia.org/wiki/에스페란토 """
        self.assert_examples({
            u'Supersigno': u'수페르시그노',
            u'Ĉapelo': u'차펠로',
            u'Saluton': u'살루톤',
            u'Ĝis revido': u'지스 레비도',
            u'Adiaŭ': u'아디아우',
            u'Jes': u'예스',
            u'Ne': u'네',
            u'Dankon': u'단콘',
            u'Mi tre ĝojas renkonti vin': u'미 트레 조야스 렌콘티 빈',
            u'Ĉu vi fartas bone': u'추 비 파르타스 보네',
            u'Mi estas koreo': u'미 에스타스 코레오',
            u'iĉismo': u'이치스모',
            u'riismo': u'리이스모',
            u'lingve universala': u'린그베 우니베르살라',
            u'La Esperantisto': u'라 에스페란티스토',
        })

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'Pasporta Servo': u'파스포르타 세르보',
            u'Fonto': u'폰토',
            u'Esperantujo': u'에스페란투요',
            u'Literatura Foiro': u'리테라투라 포이로',
            u'La Espero': u'라 에스페로',
            u'Finvenkismo': u'핀벤키스모',
            u'Raŭmismo': u'라우미스모',
            u'Civitanismo': u'치비타니스모',
            u'Unua Libro': u'우누아 리브로',
            u'Dua Libro': u'두아 리브로',
            u'Lingvo Internacia': u'린그보 인테르나치아',
            u'Fundamento de Esperanto': u'푼다멘토 데 에스페란토',
            u'La Ondo de Esperanto': u'라 온도 데 에스페란토',
            u'La Teatra Movado dum la Milito': u'라 테아트라 모바도 둠 라 밀리토',
            u'Gogo kaj liaj amikoj': u'고고 카이 리아이 아미코이',
            u'Serio Oriento-Okcidento': u'세리오 오리엔토옥치덴토',
            u'Ĉu vi pretas?': u'추 비 프레타스?',
        })
########NEW FILE########
__FILENAME__ = est
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.est import Estonian


class EstonianTestCase(HangulizeTestCase):

    lang = Estonian()

    def test_people(self):
        self.assert_examples({
            u'Andrus Ansip': u'안드루스 안시프',
            u'Jakob Hurt': u'야코브 후르트',
            u'Maarja-Liis Ilus': u'마리아리스 일루스',
            u'Ernst Jaakson': u'에른스트 약손',
            u'Carl Robert Jakobson': u'카를 로베르트 야콥손',
            u'Siim Kallas': u'심 칼라스',
            u'Kaia Kanepi': u'카이아 카네피',
            u'Gerd Kanter': u'게르드 칸테르',
            u'Jaan Kaplinski': u'얀 카플린스키',
            u'Paul Keres': u'파울 케레스',
            u'Jaan Kirsipuu': u'얀 키르시푸',
            u'Lydia Koidula': u'뤼디아 코이둘라',
            u'Jaan Kross': u'얀 크로스',
            u'Kerli Kõiv': u'케를리 커이브',
            u'Mart Laar': u'마르트 라르',
            u'Lennart Meri': u'렌나르트 메리',
            u'Markko Märtin': u'마르코 매르틴',
            u'Georg Ots': u'게오르그 오츠',
            u'Juhan Parts': u'유한 파르츠',
            u'Indrek Pertelson': u'인드레크 페르텔손',
            u'Arvo Pärt': u'아르보 패르트',
            u'Konstantin Päts': u'콘스탄틴 패츠',
            u'Johannes Pääsuke': u'요한네스 패수케',
            u'Kristjan Raud': u'크리스티안 라우드',
            u'Arnold Rüütel': u'아르놀드 뤼텔',
            u'Gustav Suits': u'구스타브 수이츠',
            u'Kristina Šmigun': u'크리스티나 슈미군',
            u'Anton Hansen Tammsaare': u'안톤 한센 탐사레',
            u'Rudolf Tobias': u'루돌프 토비아스',
            u'Villu Toots': u'빌루 토츠',
            u'Veljo Tormis': u'벨리오 토르미스',
            u'Jüri Uluots': u'위리 울루오츠',
            u'Andrus Veerpalu': u'안드루스 베르팔루',
            u'Veiko Õunpuu': u'베이코 어운푸',
        })

    def test_places(self):
        self.assert_examples({
            u'Haapsalu': u'합살루',
            u'Kohtla-Järve': u'코흐틀라얘르베',
            u'Koiva': u'코이바',
            u'Kuressaare': u'쿠레사레',
            u'Narva': u'나르바',
            u'Paide': u'파이데',
            u'Pärnu': u'패르누',
            u'Rakvere': u'라크베레',
            u'Tallinn': u'탈린',
            u'Tartu': u'타르투',
            u'Toompea': u'톰페아',
            u'Valga': u'발가',
            u'Viljandi': u'빌리안디',
            u'Võru': u'버루',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'Kalevipoeg': u'칼레비포에그',
            u'kannel': u'칸넬',
        })

########NEW FILE########
__FILENAME__ = fin
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.fin import Finnish


class FinnishTestCase(HangulizeTestCase):

    lang = Finnish()

    def test_people(self):
        self.assert_examples({
            u'Alvar Aalto': u'알바르 알토',
            u'Juhani Aho': u'유하니 아호',
            u'Martti Ahtisaari': u'마르티 아흐티사리',
            u'Akseli Gallen-Kallela': u'악셀리 갈렌칼렐라',
            u'Veikko Hakulinen': u'베이코 하쿨리넨',
            u'Pekka Halonen': u'페카 할로넨',
            u'Tarja Halonen': u'타리아 할로넨',
            u'Sami Hyypiä': u'사미 휘피애',
            u'Mika Häkkinen': u'미카 해키넨',
            u'Jussi Jääskeläinen': u'유시 얘스켈래이넨',
            u'Aki Kaurismäki': u'아키 카우리스매키',
            u'Urho Kekkonen': u'우르호 케코넨',
            u'Miikka Kiprusoff': u'미카 키프루소프',
            u'Marja-Liisa Kirvesniemi': u'마리아리사 키르베스니에미',
            u'Mauno Koivisto': u'마우노 코이비스토',
            u'Saku Koivu': u'사쿠 코이부',
            u'Hannes Kolehmainen': u'한네스 콜레흐마이넨',
            u'Jari Kurri': u'야리 쿠리',
            u'Jari Litmanen': u'야리 리트마넨',
            u'Eero Mäntyranta': u'에로 맨튀란타',
            u'Paavo Nurmi': u'파보 누르미',
            u'Ville Ritola': u'빌레 리톨라',
            u'Kimi Räikkönen': u'키미 래이쾨넨',
            u'Eero Saarinen': u'에로 사리넨',
            u'Teemu Selanne': u'테무 셀란네',
            u'Frans Eemil Sillanpää': u'프란스 에밀 실란패',
            u'Tarja Turunen': u'타리아 투루넨',
            u'Artturi Ilmari Virtanen': u'아르투리 일마리 비르타넨',
            u'Yrjö Väisälä': u'위리외 배이샐래',
            u'Tapio Wirkkala': u'타피오 비르칼라',
        })

    def test_places(self):
        self.assert_examples({
            u'Espoo': u'에스포',
            u'Helsinki': u'헬싱키',
            u'Joensuu': u'요엔수',
            u'Jyväskylä': u'위배스퀼래',
            u'Kajaani': u'카야니',
            u'Karjala': u'카리알라',
            u'Kuopio': u'쿠오피오',
            u'Lappeenranta': u'라펜란타',
            u'Mikkeli': u'미켈리',
            u'Nokia': u'노키아',
            u'Oulu': u'오울루',
            u'Rovaniemi': u'로바니에미',
            u'Saimaa': u'사이마',
            u'Savonlinna': u'사본린나',
            u'Suomenlinna': u'수오멘린나',
            u'Suomi': u'수오미',
            u'Tampere': u'탐페레',
            u'Tapiola': u'타피올라',
            u'Turku': u'투르쿠',
            u'Vaasa': u'바사',
            u'Vantaa': u'반타',
        })

    def test_mythology(self):
        self.assert_examples({
            u'Aino': u'아이노',
            u'Ilmarinen': u'일마리넨',
            u'Joukahainen': u'요우카하이넨',
            u'Kalevala': u'칼레발라',
            u'Kullervo': u'쿨레르보',
            u'Lemminkäinen': u'렘밍캐이넨',
            u'Louhi': u'로우히',
            u'Marjatta': u'마리아타',
            u'Pohjola': u'포흐욜라',
            u'Sampo': u'삼포',
            u'Ukko': u'우코',
            u'Väinämöinen': u'배이내뫼이넨',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'kantele': u'칸텔레',
            u'sauna': u'사우나',
            u'sisu': u'시수',
        })
########NEW FILE########
__FILENAME__ = grc
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.grc import AncientGreek


class AncientGreekTestCase(HangulizeTestCase):

    lang = AncientGreek()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'Αἴγυπτος': u'아이깁토스',
            u'Ἀκρόπολις': u'아크로폴리스',
            u'Ἀλεξάνδρεια': u'알렉산드레이아',
            u'Ἁλικαρνασσός': u'할리카르나소스',
            u'Ἀμφίπολις': u'암피폴리스',
            u'Ἀντιόχεια': u'안티오케이아',
            u'Ἄργος': u'아르고스',
            u'Ἀτλάντις': u'아틀란티스',
            u'Ἀττική': u'아티케',
            u'Δαλματία': u'달마티아',
            u'Δαμασκός': u'다마스코스',
            u'Δαρδανέλλια': u'다르다넬리아',
            u'Δεκάπολις': u'데카폴리스',
            u'Δελφοί': u'델포이',
            u'Δῆλος': u'델로스',
            u'Ἐλεφαντίνη': u'엘레판티네',
            u'Ἑλλάς': u'헬라스',
            u'Ἑλλήσποντος': u'헬레스폰토스',
            u'Εὔβοια': u'에우보이아',
            u'Ζάκυνθος': u'자킨토스',
            u'Θῆβαι': u'테바이',
            u'Ἰθάκη': u'이타케',
            u'Ἴλιον': u'일리온',
            u'Ἱσπανία': u'히스파니아',
            u'Ἰωνία': u'이오니아',
            u'Ὄλυμπος': u'올림포스',
            u'Ἑρμιόνη': u'헤르미오네',
            u'Εὐρώπη': u'에우로페',
            u'Ῥοδόπη': u'로도페',
            u'Ῥόδος': u'로도스',
            u'Σαλαμίς': u'살라미스',
            u'Σαμοθρᾴκη': u'사모트라케',
            u'Τῆλος': u'텔로스',
            u'Τιτάν': u'티탄',
            u'Τυῤῥηνία': u'티레니아',
            u'Φρυγία': u'프리기아',
            u'Ὠκεανία': u'오케아니아',
            u'Ὦξος': u'옥소스',
            u'Ὠρίων': u'오리온',
            u'Εὐρυδίκη': u'에우리디케',
            u'Ἀφροδίτη': u'아프로디테',
            u'Ἀπόλλων': u'아폴론',
            u'Ἄρης': u'아레스',
            u'Ἀρτεμίς': u'아르테미스',
            u'Ἀθηνᾶ': u'아테나',
            u'Δημήτηρ': u'데메테르',
            u'Ἥρα': u'헤라',
            u'Ἀχελῷος': u'아켈로오스',
            u'Ἀχέρων': u'아케론',
            u'Ἄδωνις': u'아도니스',
            u'Αἴολος': u'아이올로스',
            u'Ἄτλας': u'아틀라스',
            u'Βορέας': u'보레아스',
            u'Χάος': u'카오스',
            u'Χίμαιρα': u'키마이라',
            u'Χρόνος': u'크로노스',
            u'Δάφνη': u'다프네',
            u'Διόνυσος': u'디오니소스',
            u'Δωρίς': u'도리스',
            u'Ἠώς': u'에오스',
            u'Ἔρις': u'에리스',
            u'Ἔρως': u'에로스',
            u'Γαῖα': u'가이아',
            u'Γανυμήδης': u'가니메데스',
            u'ᾍδης': u'하데스',
            u'Ἥβη': u'헤베',
            u'Ἑκάτη': u'헤카테',
            u'Ἑλένη': u'헬레네',
            u'Ἥλιος': u'헬리오스',
            u'Ἥφαιστος': u'헤파이스토스',
            u'Ἡρακλῆς': u'헤라클레스',
            u'Ἑρμής': u'헤르메스',
            u'Ἑστία': u'헤스티아',
            u'Ὕδρα': u'히드라',
            u'Ὕπνος': u'히프노스',
            u'Ίαπετός': u'이아페토스',
            u'Ἶρις': u'이리스',
            u'Καλλιόπη': u'칼리오페',
            u'Κέρβερος': u'케르베로스',
            u'Κυβέλη': u'키벨레',
            u'Μέδουσα': u'메두사',
            u'Μνήμη': u'므네메',
            u'Μορφεύς': u'모르페우스',
            u'Νέμεσις': u'네메시스',
            u'Νηρεύς': u'네레우스',
            u'Νίκη': u'니케',
            u'Ὠρίων': u'오리온',
            u'Πάν': u'판',
            u'Πανδώρα': u'판도라',
            u'Περσεφόνη': u'페르세포네',
            u'Περσεύς': u'페르세우스',
            u'Φοίβη': u'포이베',
            u'Ποσειδῶν': u'포세이돈',
            u'Προμηθεύς': u'프로메테우스',
            u'Πρωτεύς': u'프로테우스',
            u'Ῥέα': u'레아',
            u'Σεμέλη': u'세멜레',
            u'Σιληνός': u'실레노스',
            u'Σφίγξ': u'스핑크스',
            u'Στύξ': u'스틱스',
            u'Θάνατος': u'타나토스',
            u'Τυφών': u'티폰',
            u'Οὐρανός': u'우라노스',
            u'Ζέφυρος': u'제피로스',
            u'Ζεύς': u'제우스',
            u'Ὀρφεύς': u'오르페우스',
            u'Σαπφώ': u'사포',
            u'Πίνδαρος': u'핀다로스',
            u'Ἱέρων': u'히에론',
            u'Περικλῆς': u'페리클레스',
            u'Ἡρόδοτος': u'헤로도토스',
            u'Πλούταρχος': u'플루타르코스',
            u'Ἀναξαγόρας': u'아낙사고라스',
            u'Ἀρχιμήδης': u'아르키메데스',
            u'Σωκράτης': u'소크라테스',
            u'Πλάτων': u'플라톤',
            u'Ἀριστοτέλης': u'아리스토텔레스',
            u'Ἀλέξανδρος': u'알렉산드로스',
            u'Ἀντιγόνη': u'안티고네',
            u'Οἰδίπους': u'오이디푸스',
            u'Βοιωτία': u'보이오티아',
            u'Θουκυδίδης': u'투키디데스',
            u'Ὅμηρος': u'호메로스',
            u'Ἀριάδνη': u'아리아드네',
            u'Ἰλιάς': u'일리아스',
            u'Ὀδύσσεια': u'오디세이아',
            u'Ἀχιλλεύς': u'아킬레우스',
            u'Ἀγαμέμνων': u'아가멤논',
            u'Μυκήνη': u'미케네',
            u'Θερμοπύλαι': u'테르모필라이',
            u'Λεωνίδας': u'레오니다스',
            u'Ἀναξανδρίδας': u'아낙산드리다스',
            u'Κλεομένης': u'클레오메네스',
            u'Ὀδυσσεύς': u'오디세우스',
            u'Πηνελόπη': u'페넬로페',
            u'Σίσυφος': u'시시포스',
            u'Νεμέα': u'네메아',
            u'Ἰάσων': u'이아손',
            u'Τυνδάρεως': u'틴다레오스',
            u'Αἴας': u'아이아스',
            u'Ἕκτωρ': u'헥토르',
            u'Ἀνδρομάχη': u'안드로마케',
            u'Τροία': u'트로이아',
            u'Ἀντίγονος': u'안티고노스',
            u'Σέλευκος': u'셀레우코스',
            u'Πτολεμαῖος': u'프톨레마이오스',
            u'Πέργαμον': u'페르가몬',
            u'Ἄτταλος': u'아탈로스',
            u'Κροῖσος': u'크로이소스',
            u'Σόλων': u'솔론',
            u'Λυκοῦργος': u'리쿠르고스',
            u'Πολύβιος': u'폴리비오스',
            u'Μίδας': u'미다스',
            u'Κυβέλη': u'키벨레',
            u'Σκύθαι': u'스키타이',
            u'Ἀμαζόνες': u'아마조네스',
            u'Ἀμαζών': u'아마존',
            u'Πενθεσίλεια': u'펜테실레이아',
            u'Ἱππολύτη': u'히폴리테',
            u'Πυθία': u'피티아',
            u'Πύθων': u'피톤',
            u'όμφαλος': u'옴팔로스',
            u'Πυθαγόρας': u'피타고라스',
            u'Ἱπποκράτης': u'히포크라테스',
            u'Πάππος': u'파포스',
            u'Πυθαγόρας': u'피타고라스',
            u'Ζήνων': u'제논',
            u'Ἀναξίμανδρος': u'아낙시만드로스',
            u'Θαλῆς': u'탈레스',
            u'Δημόκριτος': u'데모크리토스',
            u'Ἀπολλώνιος': u'아폴로니오스',
            u'Στράβων': u'스트라본',
            u'Εὐκτήμων': u'에욱테몬',
            u'Ἐρατοσθένης': u'에라토스테네스',
            u'Ἵππαρχος': u'히파르코스',
            u'Ἡσίοδος': u'헤시오도스',
            u'Αἴσωπος': u'아이소포스',
            u'Εὐριπίδης': u'에우리피데스',
            u'Ξενοφῶν': u'크세노폰',
            u'Θεμιστοκλῆς': u'테미스토클레스',
        })
########NEW FILE########
__FILENAME__ = hbs
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.hbs import SerboCroatian


class SerboCroatianTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0210.jsp """

    lang = SerboCroatian()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0108.jsp """
        self.assert_examples({
            u'bog': u'보그',
            u'drobnjak': u'드로브냐크',
            u'pogreb': u'포그레브',
            u'cigara': u'치가라',
            u'novac': u'노바츠',
            u'čelik': u'첼리크',
            u'točka': u'토치카',
            u'kolač': u'콜라치',
            u'naći': u'나치',
            u'sestrić': u'세스트리치',
            u'desno': u'데스노',
            u'drvo': u'드르보',
            u'medved': u'메드베드',
            u'džep': u'제프',
            u'narudžba': u'나루지바',
        #    u'Ðurađ': u'주라지',
            u'fasada': u'파사다',
            u'kifla': u'키플라',
            u'šaraf': u'샤라프',
            u'gost': u'고스트',
            u'dugme': u'두그메',
            u'krug': u'크루그',
            u'hitan': u'히탄',
            u'šah': u'샤흐',
            u'korist': u'코리스트',
            u'krug': u'크루그',
            u'jastuk': u'야스투크',
            u'levo': u'레보',
            u'balkon': u'발콘',
            u'šal': u'샬',
            u'ljeto': u'레토',
            u'pasulj': u'파술',
            u'malo': u'말로',
            u'mnogo': u'므노고',
            u'osam': u'오삼',
            u'nos': u'노스',
            u'banka': u'반카',
            u'loman': u'로만',
            u'Njegoš': u'네고시',
            u'svibanj': u'스비반',
            u'peta': u'페타',
            u'opština': u'옵슈티나',
            u'lep': u'레프',
            u'riba': u'리바',
            u'torba': u'토르바',
            u'mir': u'미르',
            u'sedam': u'세담',
            u'posle': u'포슬레',
            u'glas': u'글라스',
            u'šal': u'샬',
            u'vlasništvo': u'블라스니슈트보',
            u'broš': u'브로시',
            u'telo': u'텔로',
            u'ostrvo': u'오스트르보',
            u'put': u'푸트',
            u'vatra': u'바트라',
            u'olovka': u'올로브카',
            u'proliv': u'프롤리브',
            u'zavoj': u'자보이',
            u'pozno': u'포즈노',
            u'obraz': u'오브라즈',
            u'žena': u'제나',
            u'izložba': u'이즐로주바',
            u'muž': u'무주',
            u'pojas': u'포야스',
            u'zavoj': u'자보이',
            u'odjelo': u'오델로',
            u'bakar': u'바카르',
            u'cev': u'체브',
            u'dim': u'딤',
            u'molim': u'몰림',
            u'zubar': u'주바르',
        })

    def test_1st(self):
        """제1항: k, p
        k, p는 어말과 유성 자음 앞에서는 '으'를 붙여 적고, 무성 자음 앞에서는
        받침으로 적는다.
        """
        self.assert_examples({
            u'jastuk': u'야스투크',
            u'јастук': u'야스투크',
            u'opština': u'옵슈티나',
            u'општина': u'옵슈티나',
        })

    def test_2nd(self):
        """제2항: l
        어중의 l이 모음 앞에 올 때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'kula': u'쿨라',
            u'кула': u'쿨라',
        })

    def test_3rd(self):
        """제3항: m
        어두의 m이 l, r, n 앞에 오거나 어중의 m이 r 앞에 올 때에는 '으'를
        붙여 적는다.
        """
        self.assert_examples({
            u'mlad': u'믈라드',
            u'млад': u'믈라드',
            u'mnogo': u'므노고',
            u'много': u'므노고',
            u'smrt': u'스므르트',
            u'смрт': u'스므르트',
        })

    def test_4th(self):
        """제4항: š
        š는 자음 앞에서는 '슈', 어말에서는 '시'로 적는다.
        """
        self.assert_examples({
            u'šljivovica': u'슐리보비차',
            u'шљивовица': u'슐리보비차',
            u'Niš': u'니시',
            u'Ниш': u'니시',
        })

    def test_5th(self):
        """제5항
        자음에 '예'가 결합되는 경우에는 '예' 대신에 '에'로 적는다. 다만,
        자음이 'ㅅ'인 경우에는 '셰'로 적는다.
        """
        self.assert_examples({
            u'bjedro': u'베드로',
            u'бједро': u'베드로',
            u'sjedlo': u'셰들로',
            u'сједло': u'셰들로',
        })

########NEW FILE########
__FILENAME__ = hun
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.hun import Hungarian


class HungarianTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0212.jsp """

    lang = Hungarian()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0110.jsp """
        self.assert_examples({
            u'bab': u'버브',
            u'ablak': u'어블러크',
            u'citrom': u'치트롬',
            u'nyolcvan': u'뇰츠번',
            u'arc': u'어르츠',
            u'csavar': u'처버르',
            u'kulcs': u'쿨치',
            u'daru': u'더루',
            u'medve': u'메드베',
            u'gond': u'곤드',
            u'dzsem': u'젬',
            u'elfog': u'엘포그',
            u'gumi': u'구미',
            u'nyugta': u'뉴그터',
            u'csomag': u'초머그',
            u'gyár': u'자르',
            u'hagyma': u'허지머',
            u'nagy': u'너지',
            u'hal': u'헐',
            u'juh': u'유흐',
            u'béka': u'베커',
            u'keksz': u'켁스',
            u'szék': u'세크',
            u'len': u'렌',
            u'meleg': u'멜레그',
            u'dél': u'델',
            u'málna': u'말너',
            u'bomba': u'봄버',
            u'álom': u'알롬',
            u'néma': u'네머',
            u'bunda': u'분더',
            u'pihen': u'피헨',
            u'nyak': u'녀크',
            u'hányszor': u'하니소르',
            u'irány': u'이라니',
            u'árpa': u'아르퍼',
            u'csipke': u'칩케',
            u'hónap': u'호너프',
            u'róka': u'로커',
            u'barna': u'버르너',
            u'ár': u'아르',
            u'sál': u'샬',
            u'puska': u'푸슈커',
            u'aratás': u'어러타시',
            u'alszik': u'얼시크',
            u'asztal': u'어스털',
            u'húsz': u'후스',
            u'ajto': u'어이토',
            u'borotva': u'보로트버',
            u'csont': u'촌트',
            u'atya': u'어처',
            u'vesz': u'베스',
            u'évszázad': u'에브사저드',
            u'enyv': u'에니브',
            u'zab': u'저브',
            u'kezd': u'케즈드',
            u'blúz': u'블루즈',
            u'zsák': u'자크',
            u'tőzsde': u'퇴주데',
            u'rozs': u'로주',
            u'ajak': u'어여크',
            u'fej': u'페이',
            u'január': u'여누아르',
            u'lyuk': u'유크',
            u'mélység': u'메이셰그',
            u'király': u'키라이',
            u'lakat': u'러커트',
            u'máj': u'마이',
            u'mert': u'메르트',
            u'mész': u'메스',
            u'isten': u'이슈텐',
            u'sí': u'시',
            u'torna': u'토르너',
            u'róka': u'로커',
            u'sör': u'쇠르',
            u'nő': u'뇌',
            u'bunda': u'분더',
            u'hús': u'후시',
            u'füst': u'퓌슈트',
            u'fű': u'퓌',
        })

    def test_1st(self):
        """제1항: k, p
        어말과 유성 자음 앞에서는 '으'를 붙여 적고, 무성 자음 앞에서는
        받침으로 적는다.
        """
        self.assert_examples({
            u'ablak': u'어블러크',
            u'csipke': u'칩케',
        })

    def test_2nd(self):
        """제2항
        bb, cc, dd, ff, gg, ggy, kk, ll, lly, nn, nny, pp, rr, ss, ssz, tt,
        tty는 b, c, d, f, g, gy, k, l, ly, n, ny, p, r, s, sz, t, ty와 같이
        적는다. 다만, 어중의 nn, nny와 모음 앞의 ll은 'ㄴㄴ', 'ㄴ니',
        'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'között': u'쾨죄트',
            u'dinnye': u'딘네',
            u'nulla': u'눌러',
        })

    def test_3rd(self):
        """제3항: l
        어중의 l이 모음 앞에 올 때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'olaj': u'올러이',
        })

    def test_4th(self):
        """제4항: s
        s는 자음 앞에서는 '슈', 어말에서는 '시'로 적는다.
        """
        self.assert_examples({
            u'Pest': u'페슈트',
            u'lapos': u'러포시',
        })

    def test_5th(self):
        """제5항
        자음에 '예'가 결합되는 경우에는 '예' 대신에 '에'로 적는다. 다만,
        자음이 'ㅅ'인 경우에는 '셰'로 적는다.
        """
        self.assert_examples({
            u'nyer': u'네르',
            u'selyem': u'셰옘',
        })
########NEW FILE########
__FILENAME__ = internal
# -*- coding: utf-8 -*-
import unittest
from hangulize import *
from cmds import repl
from tests import HangulizeTestCase


class APITestCase(unittest.TestCase):

    import hangulize.langs
    langs = hangulize.langs.list_langs()

    def test_toplevel_langs(self):
        assert 'ita' in self.langs
        assert 'jpn' in self.langs
        assert 'kat' in self.langs
        assert 'por' in self.langs

    def test_sub_langs(self):
        assert 'kat.narrow' in self.langs
        assert 'por.br' in self.langs

    def test_only_langs(self):
        assert '__init__' not in self.langs

    def test_deprecated_langs(self):
        assert 'it' not in self.langs
        assert 'ja' not in self.langs

    def test_logger(self):
        import logging
        class TestHandler(logging.StreamHandler):
            msgs = []
            def handle(self, record):
                self.msgs.append(record.msg)
            @property
            def result(self):
                return '\n'.join(self.msgs)
        logger = logging.getLogger('test')
        handler = TestHandler()
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        hangulize(u'gloria', 'ita', logger=logger)
        assert ">> 'gloria'" in handler.result

    def test_singleton(self):
        from hangulize import get_lang
        from hangulize.langs.ita import Italian
        from hangulize.langs.jpn import Japanese
        assert Italian() is Italian()
        assert get_lang('ita') is Italian()
        assert get_lang('ita') is get_lang('ita')
        assert Japanese() is Japanese()
        assert get_lang('jpn') is Japanese()
        assert get_lang('jpn') is get_lang('jpn')
        assert Italian() is not Japanese()
        assert get_lang('ita') is not Japanese()
        assert get_lang('ita') is not get_lang('jpn')

    def test_sub_lang(self):
        from hangulize import get_lang
        assert get_lang('kat.narrow')

    def test_normalize(self):
        from hangulize.normalization import normalize_roman
        assert u'abc' == normalize_roman(u'AbC')
        assert u'a/a' == normalize_roman(u'Ä/ä')
        assert u'o/o' == normalize_roman(u'Ö/ö')
        assert u'u/u' == normalize_roman(u'Ü/ü')
        assert u'한글' == normalize_roman(u'한글')
        assert u'a한글o' == normalize_roman(u'Ä한글Ö')
        assert u'a한u글o' == normalize_roman(u'Ä한ü글Ö')
        assert u'123aehtw' == normalize_roman(u'123ǞËḧT̈Ẅ')

    def test_str(self):
        from hangulize import hangulize
        hangulize('Hello', 'ita')

    def test_supports(self):
        from hangulize import supports
        assert supports('lat')
        assert supports('lit')
        assert supports('ell')
        assert not supports('nex')


class PatternTestCase(HangulizeTestCase):

    class TestLang(Language):
        vowels = 'a', 'i', 'u', 'e', 'o'
        voiced = 'b', 'd', 'g'
        voiceless = 'ptk'
        longvowels = 'AIUEO'
        cons = 'bcdfghjklmnpqrstvwxyz'
        notation = Notation([
            ('van gogh', split_phonemes(u'반 고흐')),
            ('^^l', Choseong(L)),
            ('^l', Choseong(N)),
            ('l', Jongseong(L), Choseong(L)),
            ('q$$', split_phonemes(u'쿸')),
            ('q$', Jongseong(K)),
            ('zu', Choseong(J), Jungseong(EU)),
            ('ju', (Choseong(J), Jungseong(YU))),
            ('y(o)', Jungseong(YO)),
            ('y{a}', Jungseong(YA)),
            ('y{~a}', Jungseong(I)),
            ('t{~a|i}', Choseong(C)),
            ('(sh|xh|z)', 'S'),
            ('(<voiceless>|x){@}', 'X'),
            ('^^{a}b', Choseong(BB)),
            ('^{a}b', Jongseong(P)),
            ('b{o}$', Choseong(P)),
            ('{a}(<voiceless>)', '<voiced>e'),
            ('{<cons>}<vowels>{gh}', '<longvowels>'),
            ("d'i", 'di'),
            ("d i", 'di'),
            ('X', Choseong(GG)),
            ('S', Choseong(SS)),
            ('p', Choseong(P)),
            ('t', Choseong(T)),
            ('k', Choseong(K)),
            ('b', (Choseong(B),)),
            ('d', (Choseong(D),)),
            ('g', (Choseong(G),)),
            ('a', (Jungseong(A),)),
            ('i', (Jungseong(I),)),
            ('u', (Jungseong(U),)),
            ('e', (Jungseong(E),)),
            ('o', (Jungseong(O),)),
            ('c', (Choseong(C),)),
            ('O', (Jungseong(O), Jungseong(U))),
            ('h$', (Jongseong(H))),
        ])
        def normalize(self, string):
            return normalize_roman(string)

    lang = TestLang()

    def test_separator(self):
        self.assert_examples({u'shazixhu': u'싸씨쑤'})

    def test_variable(self):
        self.assert_examples({
            u'xupatiku': u'꾸까끼꾸',
            u'ptiku': u'프끼꾸'
        })

    def test_phonemes(self):
        self.assert_examples({u'zuju': u'즈쥬'})

    def test_caret_before_curly_bracket(self):
        self.assert_examples({u'la abba': u'라 앞바'})

    def test_dollar_after_curly_bracket(self):
        self.assert_examples({u'bbo': u'브포'})

    def test_variable_replacement(self):
        self.assert_examples({
            u'gap': u'가베',
            u'bakk': u'바게크',
            u'tatkak': u'까츠까게',
            u'cogh': u'초우긓',
        })

    def test_start_of_string(self):
        self.assert_examples({u'lalala': u'랄랄라'})

    def test_start_of_word(self):
        self.assert_examples({
            u'lala lalala': u'랄라 날랄라',
            u'abba': u'아쁘바'
        })

    def test_end_of_string(self):
        self.assert_examples({
            u'babeq': u'바베쿸',
            u'babeq ku': u'바벸 꾸'
        })

    def test_special_character(self):
        self.assert_examples({u"d'i": u'디'})

    def test_space(self):
        self.assert_examples({
            u'd i': u'디',
            u'van Gogh': u'반 고흐'
        })

    def test_negative_lookaround(self):
        self.assert_examples({
            u'ya': u'야아',
            u'yo': u'요',
            u'yu': u'이우',
            u'titatutote': u'끼까추초체'
        })

    def test_zero_width_space(self):
        class AmoLang(Language):
            notation = Notation([
                ('-', '/'),
                ('m$', Jongseong(M)),
                ('m', Choseong(M)),
                ('a', Jungseong(A)),
                ('o', Jungseong(O)),
            ])
        self.assert_examples({
            u'am-o': u'암오',
            u'amo': u'아모',
            u'am o': u'암 오'
        }, lang=AmoLang())

    def test_group_reference(self):
        class GrpRefLang(Language):
            notation = Notation([('(ab)c', r'\1')])
        self.assert_examples({'abc': 'ab'}, lang=GrpRefLang())


class AlgorithmTestCase(HangulizeTestCase):

    def test_phunctuation(self):
        """이슈5: 문장부호에 맞붙은 글자가 시작 글자 또는 끝 글자로 인식 안 됨
        http://github.com/sublee/hangulize/issues#issue/5
        """
        assert hangulize(u'nad', 'pol') + ',' == hangulize(u'nad,', 'pol')
        assert '.' + hangulize(u'jak', 'pol') == hangulize(u'.jak', 'pol')
        self.assert_examples({
            u'nad, nad jak .jak': u'나트, 나트 야크 .야크',
        }, 'pol')

    def test_wide_letter(self):
        self.assert_examples({u'guaguam': u'과괌'}, 'spa')

    def test_empty_sequence(self):
        """아무 규칙에도 매치되지 않아 빈 시퀀스가 반환될 때 다음 에러가 발생:

            TypeError: reduce() of empty sequence with no initial value
        """
        self.assert_examples({u'h': u''}, 'ita')

    def test_special_chars(self):
        self.assert_examples({
            u'leert,': u'레이르트,',
            u'(leert}': u'(레이르트}',
            u'"leert"': u'"레이르트"',
        }, 'nld')
        self.assert_examples({
            u'Търговище,': u'터르고비슈테,',
        }, 'bul')

    def test_tmp_chars(self):
        averroes = hangulize(u'Averroës', 'lat')
        self.assert_examples({
            u'%Averroës': '%' + averroes,
            u'%Averroës%': '%' + averroes + '%',
            u'Averroës%': averroes + '%',
        }, 'lat')

    def test_mixed_with_hangul(self):
        self.assert_examples({
            u'とうめい 고속도로': u'도메이 고속도로',
            u'からふと 섬': u'가라후토 섬',
            u'とさ 만': u'도사 만',
            u'This is 삼천えん': u'This is 삼천엔',
        }, 'jpn')
        self.assert_examples({
            u'한gloria리랑': u'한글로리아리랑',
        }, 'ita')

    def test_remove_char(self):
        #logger = repl.make_logger()
        class TestLang(Language):
            notation = Notation([
                ('k', Choseong(K)), ('i', Jungseong(I)),
                ('a', None), 
            ])
        self.assert_examples({
            u'kaaai': u'키',
            u'aakaaaia': u'키',
            u'kiaakaaaiakiaaaaaaa': u'키키키',
            u'aaaiaaakkiaakaaaiakiaaaiaaakaaaa': u'이크키키키이크',
            u'aiakakaiakaiakaiaiaka': u'이크키키키이크',
        }, TestLang())#, logger=logger)

    def test_too_many_rules(self):
        class TooHeavyLang(Language):
            notation = Notation([
                ('a', Jungseong(A)),  ('b', Choseong(B)),
                ('c', Choseong(C)),   ('d', Choseong(D)),
                ('e', Jungseong(E)),  ('f', Choseong(P)),
                ('g', Choseong(G)),   ('h', Choseong(H)),
                ('i', Jungseong(I)),  ('j', Choseong(J)),
                ('k', Choseong(K)),   ('l', Choseong(L)),
                ('m', Choseong(M)),   ('n', Choseong(N)),
                ('o', Jungseong(O)),  ('p', Choseong(P)),
                ('q', Choseong(K)),   ('r', Choseong(L)),
                ('s', Choseong(S)),   ('t', Choseong(T)),
                ('u', Jungseong(U)),  ('v', Choseong(B)),
                ('w', Jungseong(EU)), ('x', Choseong(GG)),
                ('y', Jungseong(I)),  ('z', Choseong(J)),

                ('A', Jungseong(A)),  ('B', Choseong(B)),
                ('C', Choseong(C)),   ('D', Choseong(D)),
                ('E', Jungseong(E)),  ('F', Choseong(P)),
                ('G', Choseong(G)),   ('H', Choseong(H)),
                ('I', Jungseong(I)),  ('J', Choseong(J)),
                ('K', Choseong(K)),   ('L', Choseong(L)),
                ('M', Choseong(M)),   ('N', Choseong(N)),
                ('O', Jungseong(O)),  ('P', Choseong(P)),
                ('Q', Choseong(K)),   ('R', Choseong(L)),
                ('S', Choseong(S)),   ('T', Choseong(T)),
                ('U', Jungseong(U)),  ('V', Choseong(B)),
                ('W', Jungseong(EU)), ('X', Choseong(GG)),
                ('Y', Jungseong(I)),  ('Z', Choseong(J)),

                ('a1', Jungseong(A)),  ('b1', Choseong(B)),
                ('c1', Choseong(C)),   ('d1', Choseong(D)),
                ('e1', Jungseong(E)),  ('f1', Choseong(P)),
                ('g1', Choseong(G)),   ('h1', Choseong(H)),
                ('i1', Jungseong(I)),  ('j1', Choseong(J)),
                ('k1', Choseong(K)),   ('l1', Choseong(L)),
                ('m1', Choseong(M)),   ('n1', Choseong(N)),
                ('o1', Jungseong(O)),  ('p1', Choseong(P)),
                ('q1', Choseong(K)),   ('r1', Choseong(L)),
                ('s1', Choseong(S)),   ('t1', Choseong(T)),
                ('u1', Jungseong(U)),  ('v1', Choseong(B)),
                ('w1', Jungseong(EU)), ('x1', Choseong(GG)),
                ('y1', Jungseong(I)),  ('z1', Choseong(J)),

                ('A1', Jungseong(A)),  ('B1', Choseong(B)),
                ('C1', Choseong(C)),   ('D1', Choseong(D)),
                ('E1', Jungseong(E)),  ('F1', Choseong(P)),
                ('G1', Choseong(G)),   ('H1', Choseong(H)),
                ('I1', Jungseong(I)),  ('J1', Choseong(J)),
                ('K1', Choseong(K)),   ('L1', Choseong(L)),
                ('M1', Choseong(M)),   ('N1', Choseong(N)),
                ('O1', Jungseong(O)),  ('P1', Choseong(P)),
                ('Q1', Choseong(K)),   ('R1', Choseong(L)),
                ('S1', Choseong(S)),   ('T1', Choseong(T)),
                ('U1', Jungseong(U)),  ('V1', Choseong(B)),
                ('W1', Jungseong(EU)), ('X1', Choseong(GG)),
                ('Y1', Jungseong(I)),  ('Z1', Choseong(J)),

                ('a2', Jungseong(A)),  ('b2', Choseong(B)),
                ('c2', Choseong(C)),   ('d2', Choseong(D)),
                ('e2', Jungseong(E)),  ('f2', Choseong(P)),
                ('g2', Choseong(G)),   ('h2', Choseong(H)),
                ('i2', Jungseong(I)),  ('j2', Choseong(J)),
                ('k2', Choseong(K)),   ('l2', Choseong(L)),
                ('m2', Choseong(M)),   ('n2', Choseong(N)),
                ('o2', Jungseong(O)),  ('p2', Choseong(P)),
                ('q2', Choseong(K)),   ('r2', Choseong(L)),
                ('s2', Choseong(S)),   ('t2', Choseong(T)),
                ('u2', Jungseong(U)),  ('v2', Choseong(B)),
                ('w2', Jungseong(EU)), ('x2', Choseong(GG)),
                ('y2', Jungseong(I)),  ('z2', Choseong(J)),

                ('A2', Jungseong(A)),  ('B2', Choseong(B)),
                ('C2', Choseong(C)),   ('D2', Choseong(D)),
                ('E2', Jungseong(E)),  ('F2', Choseong(P)),
                ('G2', Choseong(G)),   ('H2', Choseong(H)),
                ('I2', Jungseong(I)),  ('J2', Choseong(J)),
                ('K2', Choseong(K)),   ('L2', Choseong(L)),
                ('M2', Choseong(M)),   ('N2', Choseong(N)),
                ('O2', Jungseong(O)),  ('P2', Choseong(P)),
                ('Q2', Choseong(K)),   ('R2', Choseong(L)),
                ('S2', Choseong(S)),   ('T2', Choseong(T)),
                ('U2', Jungseong(U)),  ('V2', Choseong(B)),
                ('W2', Jungseong(EU)), ('X2', Choseong(GG)),
                ('Y2', Jungseong(I)),  ('Z2', Choseong(J)),

                ('a3', Jungseong(A)),  ('b3', Choseong(B)),
                ('c3', Choseong(C)),   ('d3', Choseong(D)),
                ('e3', Jungseong(E)),  ('f3', Choseong(P)),
                ('g3', Choseong(G)),   ('h3', Choseong(H)),
                ('i3', Jungseong(I)),  ('j3', Choseong(J)),
                ('k3', Choseong(K)),   ('l3', Choseong(L)),
                ('m3', Choseong(M)),   ('n3', Choseong(N)),
                ('o3', Jungseong(O)),  ('p3', Choseong(P)),
                ('q3', Choseong(K)),   ('r3', Choseong(L)),
                ('s3', Choseong(S)),   ('t3', Choseong(T)),
                ('u3', Jungseong(U)),  ('v3', Choseong(B)),
                ('w3', Jungseong(EU)), ('x3', Choseong(GG)),
                ('y3', Jungseong(I)),  ('z3', Choseong(J)),

                ('A3', Jungseong(A)),  ('B3', Choseong(B)),
                ('C3', Choseong(C)),   ('D3', Choseong(D)),
                ('E3', Jungseong(E)),  ('F3', Choseong(P)),
                ('G3', Choseong(G)),   ('H3', Choseong(H)),
                ('I3', Jungseong(I)),  ('J3', Choseong(J)),
                ('K3', Choseong(K)),   ('L3', Choseong(L)),
                ('M3', Choseong(M)),   ('N3', Choseong(N)),
                ('O3', Jungseong(O)),  ('P3', Choseong(P)),
                ('Q3', Choseong(K)),   ('R3', Choseong(L)),
                ('S3', Choseong(S)),   ('T3', Choseong(T)),
                ('U3', Jungseong(U)),  ('V3', Choseong(B)),
                ('W3', Jungseong(EU)), ('X3', Choseong(GG)),
                ('Y3', Jungseong(I)),  ('Z3', Choseong(J)),

                ('a4', Jungseong(A)),  ('b4', Choseong(B)),
                ('c4', Choseong(C)),   ('d4', Choseong(D)),
                ('e4', Jungseong(E)),  ('f4', Choseong(P)),
                ('g4', Choseong(G)),   ('h4', Choseong(H)),
                ('i4', Jungseong(I)),  ('j4', Choseong(J)),
                ('k4', Choseong(K)),   ('l4', Choseong(L)),
                ('m4', Choseong(M)),   ('n4', Choseong(N)),
                ('o4', Jungseong(O)),  ('p4', Choseong(P)),
                ('q4', Choseong(K)),   ('r4', Choseong(L)),
                ('s4', Choseong(S)),   ('t4', Choseong(T)),
                ('u4', Jungseong(U)),  ('v4', Choseong(B)),
                ('w4', Jungseong(EU)), ('x4', Choseong(GG)),
                ('y4', Jungseong(I)),  ('z4', Choseong(J)),

                ('A4', Jungseong(A)),  ('B4', Choseong(B)),
                ('C4', Choseong(C)),   ('D4', Choseong(D)),
                ('E4', Jungseong(E)),  ('F4', Choseong(P)),
                ('G4', Choseong(G)),   ('H4', Choseong(H)),
                ('I4', Jungseong(I)),  ('J4', Choseong(J)),
                ('K4', Choseong(K)),   ('L4', Choseong(L)),
                ('M4', Choseong(M)),   ('N4', Choseong(N)),
                ('O4', Jungseong(O)),  ('P4', Choseong(P)),
                ('Q4', Choseong(K)),   ('R4', Choseong(L)),
                ('S4', Choseong(S)),   ('T4', Choseong(T)),
                ('U4', Jungseong(U)),  ('V4', Choseong(B)),
                ('W4', Jungseong(EU)), ('X4', Choseong(GG)),
                ('Y4', Jungseong(I)),  ('Z4', Choseong(J)),
            ])
        self.assert_examples({u'ab': u'아브'}, TooHeavyLang())


class TestCaseTestCase(unittest.TestCase):

    def test_capture_examples(self):
        return
        import hangulize.langs
        langs = hangulize.langs.list_langs()
        for i in xrange(len(langs)):
            lang = langs.pop(0)
            test = lang.replace('.', '_')
            test = getattr(__import__('tests.%s' % test), test)
            try:
                test_case = getattr(test, [x for x in dir(test) \
                                             if x.endswith('TestCase')][0])
                test_method = [x for x in dir(test_case) \
                               if x.startswith('test')][0]
            except IndexError:
                continue
            assert isinstance(test_case.get_examples(test_method), dict)


try:
    get_lang('it', iso639=1)
    class LanguageCodeTestCase(unittest.TestCase):

        table = [('bg', 'bul', 'bul'),
                 ('ca', 'cat', 'cat'),
                 ('cs', 'cze', 'ces'),
                 ('cy', 'wel', 'cym'),
                 ('de', 'ger', 'deu'),
                 ('el', 'gre', 'ell'),
                 ('et', 'est', 'est'),
                 ('fi', 'fin', 'fin'),
                 (None, 'grc', 'grc'),
                 (None, None, 'hbs'),
                 ('hu', 'hun', 'hun'),
                 ('ja', 'jpn', 'jpn')]

        def test_regard_iso639_1(self):
            assert type(get_lang('bg', iso639=1)) is type(get_lang('bg'))
            assert type(get_lang('ja', iso639=1)) is type(get_lang('ja'))

        def test_iso639_1(self):
            for iso639_1, iso639_2, iso639_3 in self.table:
                if not iso639_1:
                    continue
                assert type(get_lang(iso639_3)) is type(get_lang(iso639_1,
                                                                 iso639=1))

        def test_iso639_2(self):
            for iso639_1, iso639_2, iso639_3 in self.table:
                if not iso639_2:
                    continue
                assert type(get_lang(iso639_3)) is type(get_lang(iso639_2,
                                                                 iso639=2))

        def test_iso639_3(self):
            for iso639_1, iso639_2, iso639_3 in self.table:
                assert type(get_lang(iso639_3)) is type(get_lang(iso639_3,
                                                                 iso639=3))
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = isl
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.isl import Icelandic


class IcelandicTestCase(HangulizeTestCase):

    lang = Icelandic()

    def test_people(self):
        self.assert_examples({
            u'Agnar Helgason': u'아그나르 헬가손',
            u'Ágústa Eva Erlendsdóttir': u'아우구스타 에바 에를렌스도티르',
            u'Albert Guðmundsson': u'알베르트 그뷔드뮌손',
            u'Ari Þorgilsson': u'아리 소르길손',
            u'Arnaldur Indriðason': u'아르드날뒤르 인드리다손',
            u'Árni Magnússon': u'아우르드니 마그누손',
            u'Árni Sigfússon': u'아우르드니 시그푸손',
            u'Ásgeir Ásgeirsson': u'아우스게이르 아우스게이르손',
            u'Ásgeir Helgason': u'아우스게이르 헬가손',
            u'Ásgeir Sigurvinsson': u'아우스게이르 시귀르빈손',
            u'Ásmundur Sveinsson': u'아우스뮌뒤르 스베인손',
            u'Baltasar Kormákur': u'발타사르 코르마우퀴르',
            u'Björgólfur Guðmundsson': u'비외르골뷔르 그뷔드뮌손',
            u'Björgólfur Thor Björgólfsson': u'비외르골뷔르 소르 비외르골프손',
            u'Björgvin Halldórsson': u'비외르그빈 하들도르손',
            u'Björk Guðmundsdóttir': u'비외르크 그뷔드뮌스도티르',
            u'Björn Bjarnason': u'비외르든 비아르드나손',
            u'Björn Hlynur Haraldsson': u'비외르든 흘리뉘르 하랄손',
            u'Bragi Ólafsson': u'브라이이 올라프손',
            u'Davíð Oddsson': u'다비드 오드손',
            u'Davíð Stefánsson': u'다비드 스테파운손',
            u'Eggert Pálsson': u'에게르트 파울손',
            u'Eiður Smári Guðjohnsen': u'에이뒤르 스마우리 그뷔드요흔센',
            u'Einar Bárðarson': u'에이나르 바우르다르손',
            u'Einar Benediktsson': u'에이나르 베네딕츠손',
            u'Einar Hákonarson': u'에이나르 하우코나르손',
            u'Einar Hjörleifsson Kvaran': u'에이나르 혜르들레이프손 크바란',
            u'Einar Jónsson': u'에이나르 욘손',
            u'Einar Kárason': u'에이나르 카우라손',
            u'Einar Már Guðmundsson': u'에이나르 마우르 그뷔드뮌손',
            u'Einar Örn Benediktsson': u'에이나르 외르든 베네딕츠손',
            u'Eiríkur rauði': u'에이리퀴르 뢰이디',
            u'Eiríkur Hauksson': u'에이리퀴르 회익손',
            u'Emilíana Torrini Davíðsdóttir': u'에밀리아나 토리니 다비스도티르',
            u'Freydís Eiríksdóttir': u'프레이디스 에이릭스도티르',
            u'Friðrik Ólafsson': u'프리드리크 올라프손',
            u'Friðrik Þór Friðriksson': u'프리드리크 소르 프리드릭손',
            u'Garðar': u'가르다르',
            u'Geir Hilmar': u'게이르 힐마르',
            u'Gisli Gudjonsson': u'기슬리 그뷔드욘손',
            u'Gísli Örn Garðarsson': u'기슬리 외르든 가르다르손',
            u'Gísli Pálsson': u'기슬리 파울손',
            u'Guðmundur Arason': u'그뷔드뮌뒤르 아라손',
            u'Guðmundur Hagalín': u'그뷔드뮌뒤르 하갈린',
            u'Guðríður Þorbjarnardóttir': u'그뷔드리뒤르 소르비아르드나르도티르',
            u'Gunnfríður Jónsdóttir': u'귄프리뒤르 욘스도티르',
            u'Hafdís Huld': u'하프디스 휠드',
            u'Halldór Ásgrímsson': u'하들도르 아우스그림손',
            u'Halldór Blöndal': u'하들도르 블뢴달',
            u'Halldór Kiljan Laxness': u'하들도르 킬리안 락스네스',
            u'Hallgrímur Helgason': u'하들그리뮈르 헬가손',
            u'Hannes Hafstein': u'한네스 하프스테인',
            u'Hannes Hólmsteinn Gissurarson': u'한네스 홀름스테이든 기쉬라르손',
            u'Hannibal Valdimarsson': u'한니발 발디마르손',
            u'Haukur Tómasson': u'회이퀴르 토마손',
            u'Heiðar Helguson': u'헤이다르 헬귀손',
            u'Helgi Valdimarsson': u'헬기 발디마르손',
            u'Hermann Hreiðarsson': u'헤르만 흐레이다르손',
            u'Hilmar Örn Hilmarsson': u'힐마르 외르든 힐마르손',
            u'Hilmir Snær Guðnason': u'힐미르 스나이르 그뷔드나손',
            u'Hólmfríður Karlsdóttir': u'홀름프리뒤르 카르들스도티르',
            u'Hrafn Gunnlaugsson': u'흐라픈 귄뢰익손',
            u'Hreiðar Már Sigurðsson': u'흐레이다르 마우르 시귀르손',
            u'Ingólfur Arnarson': u'잉골뷔르 아르드나르손',
            u'Ísleifur Gissurarson': u'이슬레이뷔르 기쉬라르손',
            u'Ívar Ingimarsson': u'이바르 잉기마르손',
            u'Jóhanna Sigurðardóttir': u'요한나 시귀르다르도티르',
            u'Jóhannes Karl Gudjonsson': u'요한네스 카르들 그뷔드욘손',
            u'Jóhannes úr Kötlum': u'요한네스 우르 쾨틀륌',
            u'Jón Ásgeir Jóhannesson': u'욘 아우스게이르 요한네손',
            u'Jón Baldvin Hannibalsson': u'욘 발드빈 한니발손',
            u'Jón Kalman Stefánsson': u'욘 칼만 스테파운손',
            u'Jón Leifs': u'욘 레이프스',
            u'Jón Loftsson': u'욘 로프츠손',
            u'Jón Páll Sigmarsson': u'욘 파우들 시그마르손',
            u'Jón Sigurðsson': u'욘 시귀르손',
            u'Jón Thoroddsen': u'욘 소로드센',
            u'Jónas Hallgrímsson': u'요나스 하들그림손',
            u'Kári Stefánsson': u'카우리 스테파운손',
            u'Kjartan Ólafsson': u'캬르탄 올라프손',
            u'Kolbeinn Tumason': u'콜베이든 튀마손',
            u'Kristín Marja Baldursdóttir': u'크리스틴 마리아 발뒤르스도티르',
            u'Kristján Eldjárn': u'크리스티아운 엘디아우르든',
            u'Leifur Eiríksson': u'레이뷔르 에이릭손',
            u'Linda Pétursdóttir': u'린다 피에튀르스도티르',
            u'Loftur Sæmundsson': u'로프튀르 사이뮌손',
            u'Magnús Magnússon': u'마그누스 마그누손',
            u'Magnús Þorsteinsson': u'마그누스 소르스테인손',
            u'Magnús Ver Magnússon': u'마그누스 베르 마그누손',
            u'Margrét Hermanns Auðardóttir': u'마르그리에트 헤르만스 외이다르도티르',
            u'Margrét Vilhjálmsdóttir': u'마르그리에트 빌햐울름스도티르',
            u'Markús Örn Antonsson': u'마르쿠스 외르든 안톤손',
            u'Mugison': u'뮈이이손',
            u'Nína Dögg Filippusdóttir': u'니나 되그 필리퓌스도티르',
            u'Ólafur Darri Ólafsson': u'올라뷔르 다리 올라프손',
            u'Ólafur Egill Ólafsson': u'올라뷔르 에이이들 올라프손',
            u'Ólafur Jóhann Ólafsson': u'올라뷔르 요한 올라프손',
            u'Ólafur Ragnar Grímsson': u'올라뷔르 라그나르 그림손',
            u'Örvar Þóreyjarson Smárason': u'외르바르 소레이야르손 스마우라손',
            u'Páll Skúlason': u'파우들 스쿨라손',
            u'Ragnar Bjarnason': u'라그나르 비아르드나손',
            u'Ragnar Bragason': u'라그나르 브라가손',
            u'Ragnheiður Gröndal': u'라근헤이뒤르 그뢴달',
            u'Silvía Nótt': u'실비아 노트',
            u'Sigurður Helgason': u'시귀르뒤르 헬가손',
            u'Sigurður Nordal': u'시귀르뒤르 노르달',
            u'Sigurður Þórarinsson': u'시귀르뒤르 소라린손',
            u'Sjón': u'숀',
            u'Snorri Hjartarson': u'스노리 햐르타르손',
            u'Snorri Sturluson': u'스노리 스튀르들뤼손',
            u'Steingrímur Hermannsson': u'스테잉그리뮈르 헤르만손',
            u'Steinunn Sigurðardóttir': u'스테이뉜 시귀르다르도티르',
            u'Stefán Guðmundur Guðmundsson': u'스테파운 그뷔드뮌뒤르 그뷔드뮌손',
            u'Sveinn Björnsson': u'스베이든 비외르든손',
            u'Þóra Magnúsdóttir': u'소라 마그누스도티르',
            u'Þórarinn Eldjárn': u'소라린 엘디아우르든',
            u'Þórbergur Þórðarson': u'소르베르귀르 소르다르손',
            u'Þorfinnur Karlsefni': u'소르핀뉘르 카르들세프니',
            u'Þorgeirr Þorkelsson Ljósvetningagoði': u'소르게이르 소르켈손 리오스베트닝가고디',
            u'Thorkell Atlason': u'소르케들 아틀라손',
            u'Þorsteinn Gylfason': u'소르스테이든 길바손',
            u'Þorsteinn Pálsson': u'소르스테이든 파울손',
            u'Þorvaldur Eiríksson': u'소르발뒤르 에이릭손',
            u'Tinna Gunnlaugsdóttir': u'틴나 귄뢰익스도티르',
            u'Tómas Guðmundsson': u'토마스 그뷔드뮌손',
            u'Unnur Birna Vilhjálmsdóttir': u'윈뉘르 비르드나 빌햐울름스도티르',
            u'Vala Flosadottir': u'발라 플로사도티르',
            u'Vigdís Finnbogadóttir': u'비그디스 핀보가도티르',
            u'Vigdís Grímsdóttir': u'비그디스 그림스도티르',
            u'Viktor Arnar Ingólfsson': u'빅토르 아르드나르 잉골프손',
            u'Vilhjálmur Árnason': u'빌햐울뮈르 아우르드나손',
            u'Vilhjálmur Stefánsson': u'빌햐울뮈르 스테파운손',
        })

    def test_places(self):
        self.assert_examples({
            u'Akranes': u'아크라네스',
            u'Akureyri': u'아퀴레이리',
            u'Blöndós': u'블뢴도스',
            u'Bolungarvík': u'볼룽가르비크',
            u'Borgafjörður': u'보르가피외르뒤르',
            u'Borganes': u'보르가네스',
            u'Dalvík': u'달비크',
            u'Djúpivogur': u'디우피보귀르',
            u'Egilsstaðir': u'에이일스타디르',
            u'Eyjafjallajökull': u'에이야피아들라예퀴들',
            u'Goðafoss': u'고다포스',
            u'Grímsey': u'그림세이',
            u'Grindavík': u'그린다비크',
            u'Hafnarfjörður': u'하프나르피외르뒤르',
            u'Höfn í Hornafirði': u'회픈 이 호르드나피르디',
            u'Hofsjökull': u'호프스예퀴들',
            u'Hólmavík': u'홀마비크',
            u'Húsavík': u'후사비크',
            u'Hvammstangi': u'크밤스타웅기',
            u'Hvíta': u'크비타',
            u'Hvolsvöllur': u'크볼스뵈들뤼르',
            u'Ísafjörður': u'이사피외르뒤르',
            u'Keflavík': u'케플라비크',
            u'Kópavogur': u'코파보귀르',
            u'Lagarfljólt': u'라가르플리올트',
            u'Langjökull': u'라웅그예퀴들',
            u'Mosfellsbær': u'모스펠스바이르',
            u'Mýrdalsjökull': u'미르달스예퀴들',
            u'Mývatn': u'미바튼',
            u'Neskaupstaður': u'네스쾨이프스타뒤르',
            u'Njarðvík': u'니아르드비크',
            u'Ólafsfjörður': u'올라프스피외르뒤르',
            u'Ólafsvík': u'올라프스비크',
            u'Raufarhöfn': u'뢰이바르회픈',
            u'Reykjanes': u'레이캬네스',
            u'Reykjavík': u'레이캬비크',
            u'Sauðárkrókur': u'쇠이다우르크로퀴르',
            u'Selfoss': u'셀포스',
            u'Seyðisfjörður': u'세이디스피외르뒤르',
            u'Siglufjörður': u'시글뤼피외르뒤르',
            u'Skjálfandafljót': u'스캬울반다플리오트',
            u'Stykkishólmur': u'스티키스홀뮈르',
            u'Surtsey': u'쉬르트세이',
            u'Vatnajökull': u'바트나예퀴들',
            u'Vík': u'비크',
            u'Vopnafjörður': u'보프나피외르뒤르',
            u'Þingvellir': u'싱그베들리르',
            u'Þjórsá': u'시오르사우',
            u'Þórisvatn': u'소리스바튼',
            u'Þorlákshöfn': u'소를라욱스회픈',
            u'Þórshöfn': u'소르스회픈',
        })
########NEW FILE########
__FILENAME__ = ita
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.ita import Italian


class ItalianTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0205.jsp """

    lang = Italian()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0103.jsp """
        self.assert_examples({
            u'Bologna': u'볼로냐',
            u'bravo': u'브라보',
            u'Como': u'코모',
            u'Sicilia': u'시칠리아',
            u'credo': u'크레도',
            u'Pinocchio': u'피노키오',
            u'cherubino': u'케루비노',
            u'Dante': u'단테',
            u'drizza': u'드리차',
            u'Firenze': u'피렌체',
            u'freddo': u'프레도',
            u'Galileo': u'갈릴레오',
            u'Genova': u'제노바',
            u'gloria': u'글로리아',
            u'hanno': u'안노',
            u'oh': u'오',
            u'Milano': u'밀라노',
            u'largo': u'라르고',
            u'palco': u'팔코',
            u'Macchiavelli': u'마키아벨리',
            u'mamma': u'맘마',
            u'Campanella': u'캄파넬라',
            u'Nero': u'네로',
            u'Anna': u'안나',
            u'divertimento': u'디베르티멘토',
            u'Pisa': u'피사',
            u'prima': u'프리마',
            u'quando': u'콴도',
            u'queto': u'퀘토',
            u'Roma': u'로마',
            u'Marconi': u'마르코니',
            u'Sorrento': u'소렌토',
            u'asma': u'아스마',
            u'sasso': u'사소',
            u'Torino': u'토리노',
            u'tranne': u'트란네',
            u'Vivace': u'비바체',
            u'manovra': u'마노브라',
            u'nozze': u'노체',
            u'mancanza': u'만칸차',
            u'abituro': u'아비투로',
            u'capra': u'카프라',
            u'erta': u'에르타',
            u'padrone': u'파드로네',
            u'infamia': u'인파미아',
            u'manica': u'마니카',
            u'oblio': u'오블리오',
            u'poetica': u'포에티카',
            u'uva': u'우바',
            u'spuma': u'스푸마',
        })

    def test_1st(self):
        """제1항: gl
        i 앞에서는 'ㄹㄹ'로 적고, 그 밖의 경우에는 '글ㄹ'로 적는다.
        """
        self.assert_examples({
            u'paglia': u'팔리아',
            u'egli': u'엘리',
            u'gloria': u'글로리아',
            u'glossa': u'글로사',
        })

    def test_2nd(self):
        """제2항: gn
        뒤따르는 모음과 합쳐 '냐', '녜', '뇨', '뉴', '니'로 적는다.
        """
        self.assert_examples({
            u'montagna': u'몬타냐',
            u'gneiss': u'녜이스',
            u'gnocco': u'뇨코',
            u'gnu': u'뉴',
            u'ogni': u'오니',
        })

    def test_3rd(self):
        """제3항: sc
        sce는 '셰'로, sci는 '시'로 적고, 그 밖의 경우에는 '스ㅋ'으로 적는다.
        """
        self.assert_examples({
            u'crescendo': u'크레셴도',
            u'scivolo': u'시볼로',
            u'Tosca': u'토스카',
            u'scudo': u'스쿠도',
        })

    def test_4th(self):
        """제4항
        같은 자음이 겹쳤을 때에는 겹치지 않은 경우와 같이 적는다. 다만, -mm-,
        -nn-의 경우는 'ㅁㅁ', 'ㄴㄴ'으로 적는다.
        """
        self.assert_examples({
            u'Puccini': u'푸치니',
            u'buffa': u'부파',
            u'allegretto': u'알레그레토',
            u'carro': u'카로',
            u'rosso': u'로소',
            u'mezzo': u'메초',
            u'gomma': u'곰마',
            u'bisnonno': u'비스논노',
        })

    def test_5th(self):
        """제5항: c, g
        1. c와 g는 e, i 앞에서 각각 'ㅊ', 'ㅈ'으로 적는다.
        2. c와 g 다음에 ia, io, iu가 올 때에는 각각 '차, 초, 추',
           '자, 조, 주'로 적는다.
        """
        self.assert_examples({
            u'cenere': u'체네레',
            u'genere': u'제네레',
            u'cima': u'치마',
            u'gita': u'지타',
            u'caccia': u'카차',
            u'micio': u'미초',
        })

    def test_6th(self):
        """제6항: qu
        qu는 뒤따르는 모음과 합쳐 '콰, 퀘, 퀴' 등으로 적는다. 다만, o 앞에서는
        '쿠'로 적는다.
        """
        self.assert_examples({
            u'soqquadro': u'소콰드로',
            u'quello': u'퀠로',
            u'quieto': u'퀴에토',
            u'quota': u'쿠오타',
        })

    def test_7th(self):
        """제7항: l, ll
        어말 또는 자음 앞의 l, ll은 받침으로 적고, 어중의 l, ll이 모음 앞에
        올 때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'sol': u'솔',
            u'polca': u'폴카',
            u'Carlo': u'카를로',
            u'quello': u'퀠로',
        })

    def test_hangulize(self):
        self.assert_examples({
            u'italia': u'이탈리아',
            u'Innocenti': u'인노첸티',
            u'Cerigotto': u'체리고토',
            u'Juventus': u'유벤투스',
            u'Schiavonia': u'스키아보니아',
            u'Fogli': u'폴리',
            u'Caravaggio': u'카라바조',
            u'nephos': u'네포스',
            u'sbozzacchisce': u'스보차키셰',
            u'Scalenghe': u'스칼렌게',
            u'Fabrizio': u'파브리치오',
            u'Anghiari': u'안기아리',
            u'soqquadro': u'소콰드로',
            u'Bologna': u'볼로냐',
            u'Fognini': u'포니니',
            u'Ignazio': u'이냐치오',
            u"Giro d'Italia": u'지로 디탈리아',
            u"per l'avvenire d'Italia": u'페르 라베니레 디탈리아',
            u'Rex': u'렉스',
        })
########NEW FILE########
__FILENAME__ = jpn
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.jpn import Japanese


class JapaneseTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0206.jsp """

    lang = Japanese()

    def test_1st(self):
        """제1항: 촉음
        촉음(促音) [ッ(っ)]는 'ㅅ'으로 통일해서 적는다.
        """
        self.assert_examples({
            u'サッポロ': u'삿포로',
            u'トットリ': u'돗토리',
            u'ヨッカイチ': u'욧카이치',
        })

    def test_2nd(self):
        """제2항: 장모음
        장모음은 따로 표기하지 않는다.
        """
        self.assert_examples({
            u'キュウシュウ': u'규슈',
            u'ニイガタ': u'니가타',
            u'トウキョウ': u'도쿄',
            u'オオサカ': u'오사카',
        })

    def test_hangulize(self):
        self.assert_examples({
            u'にほん': u'니혼',
            u'にほんばし': u'니혼바시',
            u'あかちゃん': u'아카찬',
        })

    def test_examples_a_column(self):
        self.assert_examples({
            u'あゆみ': u'아유미',
            u'あつぎ': u'아쓰기',
            u'あいづわかまつ': u'아이즈와카마쓰',
            u'あらかわ': u'아라카와',
            u'へいあん': u'헤이안',
            u'あきた': u'아키타',
            u'あきはばら': u'아키하바라',
            u'あおもり': u'아오모리',
            u'あまくさ': u'아마쿠사',
            u'あさま': u'아사마',
            u'あしお': u'아시오',
            u'あしかが': u'아시카가',
            u'あかぎ': u'아카기',
            u'あかいし': u'아카이시',
            u'おあかん': u'오아칸',
            u'あさひかわ': u'아사히카와',
            u'あご': u'아고',
            u'あたみ': u'아타미',
            u'あまみおお': u'아마미오',
            u'あいち': u'아이치',
            u'あんじょう': u'안조',
            u'あつみ': u'아쓰미',
            u'あかん': u'아칸',
            u'あそ': u'아소',
            u'あぶくま': u'아부쿠마',
            u'あげお': u'아게오',
            u'おわりあさひ': u'오와리아사히',
            u'あすか': u'아스카',
            u'あかし': u'아카시',
            u'あばしり': u'아바시리',
            u'あやべ': u'아야베',
            u'あしのこ': u'아시노코',
            u'あわじ': u'아와지',
            u'あまがさき': u'아마가사키',
            u'くろさわ あきら': u'구로사와 아키라',
            u'ごとう あつし': u'고토 아쓰시',
            u'きかい': u'기카이',
            u'あいづわかまつ': u'아이즈와카마쓰',
            u'いずみ': u'이즈미',
            u'かいなん': u'가이난',
            u'へいあん': u'헤이안',
            u'はぼまい': u'하보마이',
            u'すいた': u'스이타',
            u'こうらくえん': u'고라쿠엔',
            u'かすみがうら': u'가스미가우라',
            u'うらわ': u'우라와',
            u'うらかわ': u'우라카와',
            u'はちじょう': u'하치조',
            u'ようかいち': u'요카이치',
            u'はちおうじ': u'하치오지',
            u'はっこうだ': u'핫코다',
            u'てんりゅう': u'덴류',
            u'かわうち': u'가와우치',
            u'こまえ': u'고마에',
            u'こうらくえん': u'고라쿠엔',
            u'えな': u'에나',
            u'えとろふ': u'에토로후',
            u'かわごえ': u'가와고에',
            u'まえばし': u'마에바시',
            u'えちご': u'에치고',
            u'おまえ': u'오마에',
            u'えひめ': u'에히메',
            u'まつまえ': u'마쓰마에',
            u'くろしお': u'구로시오',
            u'つるおか': u'쓰루오카',
            u'とよおか': u'도요오카',
            u'はちおうじ': u'하치오지',
            u'やお': u'야오',
            u'ななお': u'나나오',
            u'おきなわ': u'오키나와',
            u'あおもり': u'아오모리',
        })

    def test_examples_ka_column(self):
        self.assert_examples({
            u'なかしべつ': u'나카시베쓰',
            u'きかい': u'기카이',
            u'よこすか': u'요코스카',
            u'あいづわかまつ': u'아이즈와카마쓰',
            u'あらかわ': u'아라카와',
            u'からふと': u'가라후토',
            u'わかやま': u'와카야마',
            u'げんかいなだ': u'겐카이나다',
            u'きかい': u'기카이',
            u'けごんのたき': u'게곤노타키',
            u'ひろさき': u'히로사키',
            u'しもきた': u'시모키타',
            u'しものせき': u'시모노세키',
            u'おきなわ': u'오키나와',
            u'あきた': u'아키타',
            u'くろしお': u'구로시오',
            u'くろべ': u'구로베',
            u'こうらくえん': u'고라쿠엔',
            u'ゆくはし': u'유쿠하시',
            u'ちくご': u'지쿠고',
            u'くさつ': u'구사쓰',
            u'せんかく': u'센카쿠',
            u'あまくさ': u'아마쿠사',
            u'くしろ': u'구시로',
            u'くらしき': u'구라시키',
            u'けごんのたき': u'게곤노타키',
            u'はっけん': u'핫켄',
            u'やりがたけ': u'야리가타케',
            u'いけだ': u'이케다',
            u'おんたけ': u'온타케',
            u'みやけ': u'미야케',
            u'きただけ': u'기타다케',
            u'ほっくわん': u'홋쿠완',
            u'おおたけ': u'오타케',
            u'なら けん': u'나라 겐',
            u'こまえ': u'고마에',
            u'こうらくえん': u'고라쿠엔',
            u'よこすか': u'요코스카',
            u'よこて': u'요코테',
            u'よこはま': u'요코하마',
            u'はこだて': u'하코다테',
            u'はっこうだ': u'핫코다',
            # u'しれとこ': u'시레토고',
            # => 시레토코
            u'とまこまい': u'도마코마이',
            u'にっこう': u'닛코',
        })

    def test_examples_ga_column(self):
        self.assert_examples({
            u'かながわ': u'가나가와',
            u'かすみがうら': u'가스미가우라',
            u'もがみ': u'모가미',
            u'やりがたけ': u'야리가타케',
            u'つがる': u'쓰가루',
            u'するが': u'스루가',
            u'さが': u'사가',
            u'たねが': u'다네가',
            u'あつぎ': u'아쓰기',
            u'とちぎ': u'도치기',
            u'はぎ': u'하기',
            u'あかぎ': u'아카기',
            u'ぎの': u'기노',
            u'ぎんざ': u'긴자',
            u'むぎ': u'무기',
            u'ぎふ': u'기후',
            u'みやぎ': u'미야기',
            u'けいひん': u'게이힌',
            u'かわぐち': u'가와구치',
            u'よなぐに': u'요나구니',
            u'もりぐち': u'모리구치',
            u'やまぐち': u'야마구치',
            u'ぐんま': u'군마',
            u'さかぐち きんいちろう': u'사카구치 긴이치로',
            u'ひぐち けいこ': u'히구치 게이코',
            u'ひぐち たかやす': u'히구치 다카야스',
            u'さとう めぐむ': u'사토 메구무',
            u'げんかいなだ': u'겐카이나다',
            u'あげお': u'아게오',
            u'くればやし しげお': u'구레바야시 시게오',
            u'むらかみ しげとし': u'무라카미 시게토시',
            u'しげみつ まもる': u'시게미쓰 마모루',
            u'さいとう しげよし': u'사이토 시게요시',
            u'まちだ しげる': u'마치다 시게루',
            u'まえお しげさぶろう': u'마에오 시게사부로',
            u'ながしま しげお': u'나가시마 시게오',
            u'けごんのたき': u'게곤노타키',
            u'ぶんご': u'분고',
            u'ちくご': u'지쿠고',
            u'かわごえ': u'가와고에',
            u'ちゅうごく': u'주고쿠',
            u'えちご': u'에치고',
            u'ごとう': u'고토',
            u'あご': u'아고',
            u'こごた': u'고고타',
            u'ひょうご': u'효고',
        })

########NEW FILE########
__FILENAME__ = kat
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.kat import Georgian


class GeorgianTestCase(HangulizeTestCase):

    lang = Georgian()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'თბილისი': u'트빌리시',
            u'ქუთაისი': u'쿠타이시',
            u'ბათუმი': u'바투미',
            u'რუსთავი': u'루스타비',
            u'ზუგდიდი': u'주그디디',
            u'გორი': u'고리',
            u'ფოთი': u'포티',
            u'დავით': u'다비트',
            u'გიორგი': u'기오르기',
            u'ფარნავაზი': u'파르나바지',
            u'მითრიდატე': u'미트리다테',
            u'თამარი': u'타마리',
            u'ზვიად': u'즈비아드',
            u'გამსახურდია': u'감사후르디아',
            u'ალექსანდრე': u'알레크산드레',
            u'დიმიტრი': u'디미트리',
            u'ამილახვარი': u'아밀라흐바리',
            u'გიორგი': u'기오르기',
            u'სააკაძე': u'사카제',
            u'ვახუშტი': u'바후슈티',
            u'ზურაბ': u'주라브',
            u'ავალიშვილი': u'아발리슈빌리',
            u'ლევან': u'레반',
            u'ჭილაშვილი': u'칠라슈빌리',
            u'კახაბერ': u'카하베르',
            u'კახა': u'카하',
            u'კალაძე': u'칼라제',
            u'ზურაბ': u'주라브',
            u'აზმაიფარაშვილი': u'아즈마이파라슈빌리',
            u'კონსტანტინე': u'콘스탄티네',
            u'გამსახურდია': u'감사후르디아',
            u'მიხეილ': u'미헤일',
            u'ჯავახიშვილი': u'자바히슈빌리',
            u'კიტა': u'키타',
            u'აბაშიძე': u'아바시제',
            u'არნოლდ': u'아르놀드',
            u'ჩიქობავა': u'치코바바',
            u'ანა': u'아나',
            u'კალანდაძე': u'칼란다제',
            u'იოსებ': u'이오세브',
            u'გრიშაშვილი': u'그리샤슈빌리',
            u'კახაბერ': u'카하베르',
            u'კახა': u'카하',
            u'კალაძე': u'칼라제',
            u'მთაწმინდა': u'음타츠민다',
            u'მერაბ': u'메라브',
            u'კოსტავა': u'코스타바',
            u'შოთა': u'쇼타',
            u'არველაძე': u'아르벨라제',
            u'დიმიტრი': u'디미트리',
            u'არაყიშვილი': u'아라키슈빌리',
            u'ელენე': u'엘레네',
            u'ახვლედიანი': u'아흐블레디아니',
            u'მაყვალა': u'마크발라',
            u'ქასრაშვილი': u'카스라슈빌리',
            u'პეტრე': u'페트레',
            u'მიხეილ': u'미헤일',
            u'სააკაშვილი': u'사카슈빌리',
            u'ედუარდ': u'에두아르드',
            u'შევარდნაძე': u'셰바르드나제',
            u'ზურაბ': u'주라브',
            u'ჟვანია': u'주바니아',
            u'ნიკოლოზ': u'니콜로즈',
            u'ნიკა': u'니카',
            u'გილაური': u'길라우리',
            u'გრიგოლ': u'그리골',
            u'მგალობლიშვილ': u'음갈로블리슈빌',
            u'ნინო': u'니노',
            u'ბურჯანაძე': u'부르자나제',
            u'თათია': u'타티아',
            u'მანაგაძე': u'마나가제',
            u'გიორგი': u'기오르기',
            u'ღონღაძე': u'곤가제',
            u'ზაზა': u'자자',
            u'ფაჩულია': u'파출리아',
            u'ნიკოლოზ': u'니콜로즈',
            u'ბარათაშვილი': u'바라타슈빌리',
            u'რაფიელ': u'라피엘',
            u'ერისთავი': u'에리스타비',
            u'ჯვარი': u'즈바리',
            u'მტკვარი': u'음트크바리',
            u'ზარზმა': u'자르즈마',
            u'ავტო': u'아프토',
        })
########NEW FILE########
__FILENAME__ = kat_narrow
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.kat.narrow import NarrowGeorgian


class NarrowGeorgianTestCase(HangulizeTestCase):

    lang = NarrowGeorgian()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'თბილისი': u'트빌리시',
            u'ქუთაისი': u'쿠타이시',
            u'ბათუმი': u'바투미',
            u'რუსთავი': u'루스타비',
            u'ზუგდიდი': u'주그디디',
            u'გორი': u'고리',
            u'ფოთი': u'포티',
            u'დავით': u'다비트',
            u'გიორგი': u'기오르기',
            u'ფარნავაზი': u'파르나바지',
            u'მითრიდატე': u'미트리다떼',
            u'თამარი': u'타마리',
            u'ზვიად': u'즈위아드',
            u'გამსახურდია': u'감사후르디아',
            u'ალექსანდრე': u'알레크산드레',
            u'დიმიტრი': u'디미뜨리',
            u'ამილახვარი': u'아밀라흐와리',
            u'გიორგი': u'기오르기',
            u'სააკაძე': u'사까제',
            u'ვახუშტი': u'바후슈띠',
            u'ზურაბ': u'주라브',
            u'ავალიშვილი': u'아발리슈윌리',
            u'ლევან': u'레반',
            u'ჭილაშვილი': u'찔라슈윌리',
            u'კახაბერ': u'까하베르',
            u'კახა': u'까하',
            u'კალაძე': u'깔라제',
            u'ზურაბ': u'주라브',
            u'აზმაიფარაშვილი': u'아즈마이파라슈윌리',
            u'კონსტანტინე': u'꼰스딴띠네',
            u'გამსახურდია': u'감사후르디아',
            u'მიხეილ': u'미헤일',
            u'ჯავახიშვილი': u'자바히슈윌리',
            u'კიტა': u'끼따',
            u'აბაშიძე': u'아바시제',
            u'არნოლდ': u'아르놀드',
            u'ჩიქობავა': u'치코바바',
            u'ანა': u'아나',
            u'კალანდაძე': u'깔란다제',
            u'იოსებ': u'이오세브',
            u'გრიშაშვილი': u'그리샤슈윌리',
            u'კახაბერ': u'까하베르',
            u'კახა': u'까하',
            u'კალაძე': u'깔라제',
            u'მთაწმინდა': u'음타쯔민다',
            u'მერაბ': u'메라브',
            u'კოსტავა': u'꼬스따바',
            u'შოთა': u'쇼타',
            u'არველაძე': u'아르벨라제',
            u'დიმიტრი': u'디미뜨리',
            u'არაყიშვილი': u'아라끼슈윌리',
            u'ელენე': u'엘레네',
            u'ახვლედიანი': u'아흐블레디아니',
            u'მაყვალა': u'마끄왈라',
            u'ქასრაშვილი': u'카스라슈윌리',
            u'პეტრე': u'뻬뜨레',
            u'მიხეილ': u'미헤일',
            u'სააკაშვილი': u'사까슈윌리',
            u'ედუარდ': u'에두아르드',
            u'შევარდნაძე': u'셰바르드나제',
            u'ზურაბ': u'주라브',
            u'ჟვანია': u'주와니아',
            u'ნიკოლოზ': u'니꼴로즈',
            u'ნიკა': u'니까',
            u'გილაური': u'길라우리',
            u'გრიგოლ': u'그리골',
            u'მგალობლიშვილ': u'음갈로블리슈윌',
            u'ნინო': u'니노',
            u'ბურჯანაძე': u'부르자나제',
            u'თათია': u'타티아',
            u'მანაგაძე': u'마나가제',
            u'გიორგი': u'기오르기',
            u'ღონღაძე': u'곤가제',
            u'ზაზა': u'자자',
            u'ფაჩულია': u'파출리아',
            u'ნიკოლოზ': u'니꼴로즈',
            u'ბარათაშვილი': u'바라타슈윌리',
            u'რაფიელ': u'라피엘',
            u'ერისთავი': u'에리스타비',
            u'ჯვარი': u'즈와리',
            u'მტკვარი': u'음뜨끄와리',
            u'ზარზმა': u'자르즈마',
            u'ავტო': u'아프또',
        })
########NEW FILE########
__FILENAME__ = lat
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.lat import Latin


class LatinTestCase(HangulizeTestCase):

    lang = Latin()

    def test_people_roman(self):
        self.assert_examples({
            u'Flavius Aëtius': u'플라비우스 아에티우스',
            u'FLAVIVS AËTIVS': u'플라비우스 아에티우스',
            u'Gnaeus Julius Agricola': u'그나이우스 율리우스 아그리콜라',
            u'GNAEUS IVLIVS AGRICOLA': u'그나이우스 율리우스 아그리콜라',
            u'Marcus Vipsanius Agrippa': u'마르쿠스 빕사니우스 아그리파',
            u'MARCVS VIPSANIVS AGRIPPA': u'마르쿠스 빕사니우스 아그리파',
            u'Julia Augusta Agrippina': u'율리아 아우구스타 아그리피나',
            u'IVLIA AVGVSTA AGRIPPINA': u'율리아 아우구스타 아그리피나',
            u'Marcus Antonius': u'마르쿠스 안토니우스',
            u'MARCVS ANTONIVS': u'마르쿠스 안토니우스',
            u'Apuleius': u'아풀레이우스',
            u'APVLEIVS': u'아풀레이우스',
            u'Gaius Julius Caesar Augustus': \
                u'가이우스 율리우스 카이사르 아우구스투스',
            u'GAIVS IVLIVS CAESAR AVGVSTVS': \
                u'가이우스 율리우스 카이사르 아우구스투스',
            u'Gaius Julius Caesar': u'가이우스 율리우스 카이사르',
            u'GAIVS IVLIVS CAESAR': u'가이우스 율리우스 카이사르',
            u'Gaius Valerius Catullus': u'가이우스 발레리우스 카툴루스',
            u'GAIVS VALERIVS CATVLLVS': u'가이우스 발레리우스 카툴루스',
            u'Marcus Tullius Cicero': u'마르쿠스 툴리우스 키케로',
            u'MARCVS TVLLIVS CICERO': u'마르쿠스 툴리우스 키케로',
            u'Tiberius Claudius Caesar Augustus Germanicus': \
                u'티베리우스 클라우디우스 카이사르 아우구스투스 게르마니쿠스',
            u'TIBERIVS CLAVDIVS CAESAR AVGVSTVS GERMANICVS': \
                u'티베리우스 클라우디우스 카이사르 아우구스투스 게르마니쿠스',
            u'Lucius Aurelius Commodus Antoninus': \
                u'루키우스 아우렐리우스 콤모두스 안토니누스',
            u'LVCIVS AVRELIVS COMMODVS ANTONINVS': \
                u'루키우스 아우렐리우스 콤모두스 안토니누스',
            u'Flavius Valerius Aurelius Constantinus': \
                u'플라비우스 발레리우스 아우렐리우스 콘스탄티누스',
            u'FLAVIVS VALERIVS AVRELIVS CONSTANTINVS': \
                u'플라비우스 발레리우스 아우렐리우스 콘스탄티누스',
            u'Cornelia Scipionis Africana': \
                u'코르넬리아 스키피오니스 아프리카나',
            u'CORNELIA SCIPIONIS AFRICANA': \
                u'코르넬리아 스키피오니스 아프리카나',
            u'Marcus Licinius Crassus': u'마르쿠스 리키니우스 크라수스',
            u'MARCVS LICINIVS CRASSVS': u'마르쿠스 리키니우스 크라수스',
            u'Gaius Aurelius Valerius Diocletianus': \
                u'가이우스 아우렐리우스 발레리우스 디오클레티아누스',
            u'GAIVS AVRELIVS VALERIVS DIOCLETIANVS': \
                u'가이우스 아우렐리우스 발레리우스 디오클레티아누스',
            u'Publius Aelius Hadrianus': u'푸블리우스 아일리우스 하드리아누스',
            u'PVBLIVS AELIVS HADRIANVS': u'푸블리우스 아일리우스 하드리아누스',
            u'Quintus Horatius Flaccus': u'퀸투스 호라티우스 플라쿠스',
            u'QVINTVS HORATIVS FLACCVS': u'퀸투스 호라티우스 플라쿠스',
            u'Flavius Petrus Sabbatius Justinianus': \
                u'플라비우스 페트루스 사바티우스 유스티니아누스',
            u'FLAVIVS PETRVS SABBATIVS IVSTINIANVS': \
                u'플라비우스 페트루스 사바티우스 유스티니아누스',
            u'Titus Livius': u'티투스 리비우스',
            u'TITVS LIVIVS': u'티투스 리비우스',
            u'Gaius Marius': u'가이우스 마리우스',
            u'GAIVS MARIVS': u'가이우스 마리우스',
            u'Nero Claudius Caesar Augustus Germanicus': \
                u'네로 클라우디우스 카이사르 아우구스투스 게르마니쿠스',
            u'NERO CLAVDIVS CAESAR AVGVSTVS GERMANICVS': \
                u'네로 클라우디우스 카이사르 아우구스투스 게르마니쿠스',
            u'Gaius Octavius': u'가이우스 옥타비우스',
            u'GAIVS OCTAVIVS': u'가이우스 옥타비우스',
            u'Titus Maccius Plautus': u'티투스 마키우스 플라우투스',
            u'TITVS MACCIVS PLAVTVS': u'티투스 마키우스 플라우투스',
            u'Gaius Plinius Secundus': u'가이우스 플리니우스 세쿤두스',
            u'GAIVS PLINIVS SECVNDVS': u'가이우스 플리니우스 세쿤두스',
            u'Gaius Plinius Caecilius Secundus': \
                u'가이우스 플리니우스 카이킬리우스 세쿤두스',
            u'GAIVS PLINIVS CAECILIVS SECVNDVS': \
                u'가이우스 플리니우스 카이킬리우스 세쿤두스',
            u'Gnaeus Pompeius Magnus': u'그나이우스 폼페이우스 마그누스',
            u'GNAEVS POMPEIVS MAGNVS': u'그나이우스 폼페이우스 마그누스',
            u'Sextus Aurelius Propertius': \
                u'섹스투스 아우렐리우스 프로페르티우스',
            u'SEXTVS AVRELIVS PROPERTIVS': \
                u'섹스투스 아우렐리우스 프로페르티우스',
            u'Gaius Sallustius Crispus': u'가이우스 살루스티우스 크리스푸스',
            u'GAIVS SALLVSTIVS CRISPVS': u'가이우스 살루스티우스 크리스푸스',
            u'Lucius Annaeus Seneca': u'루키우스 안나이우스 세네카',
            u'LVCIVS ANNAEUS SENECA': u'루키우스 안나이우스 세네카',
            u'Spartacus': u'스파르타쿠스',
            u'SPARTACVS': u'스파르타쿠스',
            u'Gaius Suetonius Tranquillus': u'가이우스 수에토니우스 트랑퀼루스',
            u'GAIVS SVETONIVS TRANQVILLVS': u'가이우스 수에토니우스 트랑퀼루스',
            u'Lucius Cornelius Sulla Felix': \
                u'루키우스 코르넬리우스 술라 펠릭스',
            u'LVCIVS CORNELIVS SVLLA FELIX': \
                u'루키우스 코르넬리우스 술라 펠릭스',
            u'Publius Cornelius Tacitus': u'푸블리우스 코르넬리우스 타키투스',
            u'PVBLIVS CORNELIVS TACITVS': u'푸블리우스 코르넬리우스 타키투스',
            u'Marcus Ulpius Nerva Trajanus': \
                u'마르쿠스 울피우스 네르바 트라야누스',
            u'MARCUS VLPIVS NERVA TRAIANVS': \
                u'마르쿠스 울피우스 네르바 트라야누스',
            u'Publius Vergilius Maro': u'푸블리우스 베르길리우스 마로',
            u'PVBLIVS VERGILIVS MARO': u'푸블리우스 베르길리우스 마로',
            u'Titus Flavius Vespasianus': u'티투스 플라비우스 베스파시아누스',
            u'TITVS FLAVIVS VESPASIANVS': u'티투스 플라비우스 베스파시아누스',
            u'Marcus Vitruvius Pollio': u'마르쿠스 비트루비우스 폴리오',
            u'MARCVS VITRVVIVS POLLIO': u'마르쿠스 비트루비우스 폴리오',
        })

    def test_people_nonroman(self):
        self.assert_examples({
            u'Georgius Agricola': u'게오르기우스 아그리콜라',
            u'Anselmus': u'안셀무스',
            u'Averroës': u'아베로에스',
            u'Aurelius Augustinus Hipponensis': \
                u'아우렐리우스 아우구스티누스 히포넨시스',
            u'Carolus Magnus': u'카롤루스 마그누스',
            u'Nicolaus Copernicus': u'니콜라우스 코페르니쿠스',
            u'Cyrus': u'키루스',
            u'Darius': u'다리우스',
            u'Gotarzes': u'고타르제스',
            u'Hannibal': u'한니발',
            u'Flavius Josephus': u'플라비우스 요세푸스',
            u'Mithridates': u'미트리다테스',
            u'Flavius Odoacer': u'플라비우스 오도아케르',
        })

    def test_places(self):
        self.assert_examples({
            u'Aegyptus': u'아이깁투스',
            u'Asia': u'아시아',
            u'Assyria': u'아시리아',
            u'Britannia': u'브리탄니아',
            u'Carthago': u'카르타고',
            u'Cannae': u'칸나이',
            u'Galatia': u'갈라티아',
            u'Gallia': u'갈리아',
            u'Germania': u'게르마니아',
            u'Hispania': u'히스파니아',
            u'Illyricum': u'일리리쿰',
            u'Iudaea': u'유다이아',
            u'Latium': u'라티움',
            u'Lusitania': u'루시타니아',
            u'Numidia': u'누미디아',
            u'Padus': u'파두스',
            u'Parthia': u'파르티아',
        #    u'Pompeii': u'폼페이',
            u'Roma': u'로마',
            u'Sicilia': u'시킬리아',
            u'Syracusae': u'시라쿠사이',
            u'Thracia': u'트라키아',
            u'Mons Vesuvius': u'몬스 베수비우스',
        })

    def test_texts(self):
        self.assert_examples({
            u'Aeneis': u'아이네이스',
            u'Naturalis Historia': u'나투랄리스 히스토리아',
            u'Commentarii de Bello Gallico': u'콤멘타리이 데 벨로 갈리코',
            u'Confessiones': u'콘페시오네스',
            u'Metamorphoseon': u'메타모르포세온',
            u'Philosophiæ Naturalis Principia Mathematica': \
                u'필로소피아이 나투랄리스 프링키피아 마테마티카',
        })

    def test_mythology(self):
        self.assert_examples({
            u'Apollo': u'아폴로',
            u'Bacchus': u'바쿠스',
            u'Ceres': u'케레스',
            u'Diana': u'디아나',
            u'Ianus': u'야누스',
            u'Iuno': u'유노',
            u'Iupitter': u'유피테르',
            u'Mars': u'마르스',
            u'Mercurius': u'메르쿠리우스',
            u'Minerva': u'미네르바',
            u'Neptunus': u'넵투누스',
            u'Pluto': u'플루토',
            u'Saturnus': u'사투르누스',
            u'Venus': u'베누스',
            u'Vesta': u'베스타',
            u'Vulcanus': u'불카누스',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'consul': u'콘술',
            u'Pax Romana': u'팍스 로마나',
            u'res publica': u'레스 푸블리카',
            u'senatus': u'세나투스',
        })

########NEW FILE########
__FILENAME__ = lav
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.lav import Latvian


class LatvianTestCase(HangulizeTestCase):

    lang = Latvian()

    def test_people(self):
        self.assert_examples({
            u'Alberts': u'알베르츠',
            u'Gunārs Astra': u'구나르스 아스트라',
            u'Helmuts Balderis': u'헬무츠 발데리스',
            u'Jānis Balodis': u'야니스 발로디스',
            u'Krišjānis Barons': u'크리샤니스 바론스',
            u'Mihails Barišņikovs': u'미하일스 바리슈니코우스',
            u'Vizma Belševica': u'비즈마 벨셰비차',
            u'Eduards Berklavs': u'에두아르츠 베르클라우스',
            u'Ernests Blanks': u'에르네스츠 블랑크스',
            u'Rūdolfs Blaumanis': u'루돌프스 블라우마니스',
            u'Aleksandrs Čaks': u'알렉산드르스 착스',
            u'Jānis Čakste': u'야니스 착스테',
            u'Emīls Dārziņš': u'에밀스 다르진슈',
            u'Eliass Eliezers Desslers': u'엘리아스 엘리에제르스 데슬레르스',
            u'Sergejs Eizenšteins': u'세르게이스 에이젠슈테인스',
            u'Movša Feigins': u'모우샤 페이긴스',
            u'Elīna Garanča': u'엘리나 가란차',
            u'Ernests Gulbis': u'에르네스츠 굴비스',
            u'Uvis Helmanis': u'우비스 헬마니스',
            u'Artūrs Irbe': u'아르투르스 이르베',
            u'Kārlis Irbītis': u'카를리스 이르비티스',
            u'Gatis Jahovičs': u'가티스 야호비치',
            u'Kaspars Kambala': u'카스파르스 캄발라',
            u'Aleksandrs Koblencs': u'알렉산드르스 코블렌츠',
            u'Gustavs Klucis': u'구스타우스 클루치스',
            u'Ābrams Izāks Kūks': u'아브람스 이작스 쿡스',
            u'Aleksandrs Kovaļevskis': u'알렉산드르스 코발레우스키스',
            u'Miķelis Krogzems': u'미첼리스 크로그젬스',
            u'Juris Kronbergs': u'유리스 크론베르크스',
            u'Atis Kronvalds': u'아티스 크론발츠',
            u'Alberts Kviesis': u'알베르츠 크비에시스',
            u'Aleksandrs Laime': u'알렉산드르스 라이메',
            u'Nikolajs Loskis': u'니콜라이스 로스키스',
            u'Jevgēnija Ļisicina': u'예우게니야 리시치나',
            u'Zigfrīds Anna Meierovics': u'직프리츠 안나 메이에로비츠',
            u'Evgenijs Millers': u'에우게니스 밀레르스',
            u'Kārlis Mīlenbahs': u'카를리스 밀렌바흐스',
            u'Stanislavs Olijars': u'스타니슬라우스 올리야르스',
            u'Elvīra Ozoliņa': u'엘비라 오졸리냐',
            u'Vilhelms Ostvalds': u'빌헬름스 오스트발츠',
            u'Sandis Ozoliņš': u'산디스 오졸린슈',
            u'Valdemārs Ozoliņš': u'발데마르스 오졸린슈',
            u'Artis Pabriks': u'아르티스 파브릭스',
            u'Karlis Padegs': u'카를리스 파덱스',
            u'Marian Pahars': u'마리안 파하르스',
            u'Vladimirs Petrovs': u'블라디미르스 페트로우스',
            u'Andrejs Pumpurs': u'안드레이스 품푸르스',
            u'Mārtiņš Rubenis': u'마르틴슈 루베니스',
            u'Juris Rubenis': u'유리스 루베니스',
            u'Elza Rozenberga': u'엘자 로젠베르가',
            u'Uļjana Semjonova': u'울랴나 세묘노바',
            u'Māris Štrombergs': u'마리스 슈트롬베르크스',
            u'Pēteris Stučka': u'페테리스 스투치카',
            u'Viktors Ščerbatihs': u'빅토르스 슈체르바티흐스',
            u'Haralds Silovs': u'하랄츠 실로우스',
            u'Andris Šķēle': u'안드리스 슈첼레',
            u'Ernests Štālbergs': u'에르네스츠 슈탈베르크스',
            u'Guntis Ulmanis': u'군티스 울마니스',
            u'Kārlis Ulmanis': u'카를리스 울마니스',
            u'Romāns Vainšteins': u'로만스 바인슈테인스',
            u'Krišjānis Valdemārs': u'크리샤니스 발데마르스',
            u'Miķelis Valters': u'미첼리스 발테르스',
            u'Valdis Valters': u'발디스 발테르스',
            u'Aleksandrs Vanags': u'알렉산드르스 바낙스',
            u'Ojārs Vācietis': u'오야르스 바치에티스',
            u'Eduards Veidenbaums': u'에두아르츠 베이덴바움스',
            u'Makss Veinreihs': u'막스 베인레이흐스',
            u'Visvaldis': u'비스발디스',
            u'Jāzeps Vītols': u'야젭스 비톨스',
            u'Māris Verpakovskis': u'마리스 베르파코우스키스',
            u'Aleksandrs Voitkevičs': u'알렉산드르스 보이트케비치',
            u'Kārlis Zariņš': u'카를리스 자린슈',
            u'Gustavs Zemgals': u'구스타우스 젬갈스',
            u'Valdis Zatlers': u'발디스 자틀레르스',
            u'Imants Ziedonis': u'이만츠 지에도니스',
            u'Sergejs Žoltoks': u'세르게이스 졸톡스',
        })

    def test_places(self):
        self.assert_examples({
            u'Daugava': u'다우가바',
            u'Daugavpils': u'다우가우필스',
            u'Grobiņa': u'그로비냐',
            u'Jēkabpils': u'예캅필스',
            u'Jelgava': u'옐가바',
            u'Jersika': u'예르시카',
            u'Jūrmala': u'유르말라',
            u'Koknese': u'코크네세',
            u'Kurzeme': u'쿠르제메',
            u'Latgale': u'라트갈레',
            u'Latvija': u'라트비야',
            u'Liepāja': u'리에파야',
            u'Rēzekne': u'레제크네',
            u'Rīga': u'리가',
            u'Valmiera': u'발미에라',
            u'Ventspils': u'벤츠필스',
            u'Vidzeme': u'비제메',
            u'Zemgale': u'젬갈레',
        })
########NEW FILE########
__FILENAME__ = lit
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.lit import Lithuanian


class LithuanianTestCase(HangulizeTestCase):

    lang = Lithuanian()

    def test_people(self):
        self.assert_examples({
            u'Valdas Adamkus': u'발다스 아담쿠스',
            u'Virgilijus Alekna': u'비르길리유스 알레크나',
            u'Algirdas': u'알기르다스',
            u'Jurgis Baltrušaitis': u'유르기스 발트루샤이티스',
            u'Gediminas Baravykas': u'게디미나스 바라비카스',
            u'Jonas Basanavičius': u'요나스 바사나비추스',
            u'Bernardas Brazdžionis': u'베르나르다스 브라즈조니스',
            u'Elena Čiudakova': u'엘레나 추다코바',
            u'Čiurlionis': u'추를료니스',
            u'Tomas Danilevičius': u'토마스 다닐레비추스',
            u'Simonas Daukantas': u'시모나스 다우칸타스',
            u'Jurgis Dobkevičius': u'유르기스 돕케비추스',
            u'Gediminas': u'게디미나스',
            u'Vitas Gerulaitis': u'비타스 게룰라이티스',
            u'Marija Gimbutienė': u'마리야 김부티에네',
            u'Dalia Grybauskaitė': u'달랴 그리바우스카이테',
            u'Laurynas Gucevičius': u'라우리나스 구체비추스',
            u'Žydrūnas Ilgauskas': u'지드루나스 일가우스카스',
            u'Jonas Jablonskis': u'요나스 야블론스키스',
            u'Edgaras Jankauskas': u'에드가라스 양카우스카스',
            u'Šarūnas Jasikevičius': u'샤루나스 야시케비추스',
            u'Jogaila': u'요가일라',
            u'Kęstutis': u'케스투티스',
            u'Linas Kleiza': u'리나스 클레이자',
            u'Konstantinas': u'콘스탄티나스',
            u'Jonas Kubilius': u'요나스 쿠빌류스',
            u'Vincas Kudirka': u'빈차스 쿠디르카',
            u'Maironis': u'마이로니스',
            u'Šarūnas Marčiulionis': u'샤루나스 마르출료니스',
            u'Mikalojus': u'미칼로유스',
            u'Mindaugas': u'민다우가스',
            u'Arminas Narbekovas': u'아르미나스 나르베코바스',
            u'Salomėja Nėris': u'살로메야 네리스',
            u'Martynas Mažvydas': u'마르티나스 마주비다스',
            u'Mykolas Kleopas Oginskis': u'미콜라스 클레오파스 오긴스키스',
            u'Robertas Poškus': u'로베르타스 포슈쿠스',
            u'Kazimiera Prunskienė': u'카지미에라 프룬스키에네',
            u'Jonušas Radvila': u'요누샤스 라드빌라',
            u'Violeta Riaubiškytė': u'뵬레타 랴우비슈키테',
            u'Arvydas Sabonis': u'아르비다스 사보니스',
            u'Antanas Smetona': u'안타나스 스메토나',
            u'Darius Songaila': u'다류스 송가일라',
            u'Marius Stankevičius': u'마류스 스탕케비추스',
            u'Vytautas Straižys': u'비타우타스 스트라이지스',
            u'Deividas Šemberas': u'데이비다스 솀베라스',
            u'Ramūnas Šiškauskas': u'라무나스 시슈카우스카스',
            u'Juozas Urbšys': u'유오자스 우르프시스',
            u'Vytautas': u'비타우타스',
        })

    def test_places(self):
        self.assert_examples({
            u'Alytus': u'알리투스',
            u'Biržai': u'비르자이',
            u'Dubingiai': u'두빙갸이',
            u'Įsrutis': u'이스루티스',
            u'Kaunas': u'카우나스',
            u'Kernavė': u'케르나베',
            u'Klaipėda': u'클라이페다',
            u'Marijampolė': u'마리얌폴레',
            u'Mažeikiai': u'마제이캬이',
            u'Panevėžys': u'파네베지스',
            u'Šiauliai': u'샤울랴이',
            u'Trakai': u'트라카이',
            u'Vilnius': u'빌뉴스',
        })
########NEW FILE########
__FILENAME__ = mkd
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.mkd import Macedonian


class MacedonianTestCase(HangulizeTestCase):

    lang = Macedonian()

    def test_people(self):
        self.assert_examples({
            # u'Методија Андонов-Ченто': u'메토디야 안도노프첸토',
            # => 메토디야 안도노브첸토
            u'Димитрије Бужаровски': u'디미트리예 부자로프스키',
            u'Владо Бучковски': u'블라도 부치코프스키',
            u'Киро Глигоров': u'키로 글리고로프',
            u'Каролина Гочева': u'카롤리나 고체바',
            u'Никола Груевски': u'니콜라 그루에프스키',
            u'Димитар Димитров': u'디미타르 디미트로프',
            u'Партенија Зографски': u'파르테니야 조그라프스키',
            u'Ѓорге Иванов': u'교르게 이바노프',
            u'Милан Ивановиќ': u'밀란 이바노비치',
            u'Катарина Ивановска': u'카타리나 이바노프스카',
            u'Баже Илијоски': u'바제 일리요스키',
            u'Славко Јаневски': u'슬라프코 야네프스키',
            u'Борјан Јовановски': u'보리안 요바노프스키',
            u'Климент Охридски': u'클리멘트 오흐리츠키',
            u'Срѓан Керим': u'스르잔 케림',
            u'Никола Кљусев': u'니콜라 클류세프',
            u'Лазар Колишевски': u'라자르 콜리셰프스키',
            u'Блаже Конески': u'블라제 코네스키',
            u'Хари Костов': u'하리 코스토프',
            u'Жарко Кујунџиски': u'자르코 쿠윤지스키',
            u'Кирил Лазаров': u'키릴 라자로프',
            u'Венко Марковски': u'벤코 마르코프스키',
            u'Димитар Миладинов': u'디미타르 밀라디노프',
            u'Константин Миладинов': u'콘스탄틴 밀라디노프',
            u'Крсте Мисирков': u'크르스테 미시르코프',
            u'Петар Наумоски': u'페타르 나우모스키',
            u'Коле Неделковски': u'콜레 네델코프스키',
            u'Саша Огненовски': u'사샤 오그네노프스키',
            u'Горан Пандев': u'고란 판데프',
            u'Живко Поповски-Цветин': u'지프코 포포프스키츠베틴',
            u'Јулија Портјанко': u'율리야 포르티안코',
            u'Тоше Проески': u'토셰 프로에스키',
            u'Ѓорѓи Пулевски': u'교르기 풀레프스키',
            u'Кочо Рацин': u'코초 라친',
            u'Есма Реџепова': u'에스마 레제포바',
            u'Стевица Ристиќ': u'스테비차 리스티치',
            u'Душан Савиќ': u'두샨 사비치',
            u'Тодор Скаловски': u'토도르 스칼로프스키',
            u'Врбица Стефанов': u'브르비차 스테파노프',
            u'Горан Стефановски': u'고란 스테파노프스키',
            u'Борис Трајковски': u'보리스 트라이코프스키',
            u'Ѓорѓи Христов': u'교르기 흐리스토프',
            u'Бранко Црвенковски': u'브란코 츠르벤코프스키',
            u'Љубомир Цуцуловски': u'류보미르 추출로프스키',
            u'Коле Чашуле': u'콜레 차슐레',
            u'Живко Чинго': u'지프코 친고',
            u'Александар Џамбазов': u'알렉산다르 잠바조프',
        })

    def test_places(self):
        self.assert_examples({
            u'Битола': u'비톨라',
            u'Велес': u'벨레스',
            u'Гевгелија': u'게브겔리야',
            u'Гостивар': u'고스티바르',
            u'Кавадарци': u'카바다르치',
            u'Кичево': u'키체보',
            u'Кокино': u'코키노',
            u'Кораб': u'코라프',
            u'Кочани': u'코차니',
            u'Кратово': u'크라토보',
            u'Куклица': u'쿠클리차',
            u'Куманово': u'쿠마노보',
            u'Македонија': u'마케도니야',
            u'Маркови Кули': u'마르코비 쿨리',
            u'Нов Дојран': u'노프 도이란',
            u'Охрид': u'오흐리트',
            u'Прилеп': u'프릴레프',
            u'Радовиш': u'라도비시',
            u'Скопје': u'스코피에',
            u'Слатино': u'슬라티노',
            u'Струга': u'스트루가',
            u'Струмица': u'스트루미차',
            u'Тетово': u'테토보',
            u'Шар': u'샤르',
            u'Штип': u'슈티프',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'Металург': u'메탈루르크',
        })

########NEW FILE########
__FILENAME__ = nld
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.nld import Dutch


class DutchTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0220.jsp """

    lang = Dutch()

    def test_etc(self):
        self.assert_examples({
            u'tuig': u'타위흐',
        })

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0118.jsp """
        self.assert_examples({
            u'Borst': u'보르스트',
            u'Bram': u'브람',
            u'Jacob': u'야코프',
            u'Campen': u'캄펀',
            u'Nicolaas': u'니콜라스',
            u'topic': u'토픽',
            u'scrupel': u'스크뤼펄',
            u'cyaan': u'시안',
            u'Ceelen': u'세일런',
            u'Volcher': u'폴허르',
            u'Utrecht': u'위트레흐트',
            u'Delft': u'델프트',
            u'Edgar': u'엣하르',
            u'Hendrik': u'헨드릭',
            u'Helmond': u'헬몬트',
            u'Flevoland': u'플레볼란트',
            u'Graaf': u'흐라프',
            u'Goes': u'후스',
            u'Limburg': u'림뷔르흐',
            u'Heineken': u'헤이네컨',
            u'Hendrik': u'헨드릭',
            u'Jongkind': u'용킨트',
            u'Jan': u'얀',
            u'Jeroen': u'예룬',
            u'Kok': u'콕',
            u'Alkmaar': u'알크마르',
            u'Zierikzee': u'지릭제이',
            u'kwaliteit': u'크발리테이트',
            u'kwellen': u'크벨런',
            u'kwitantie': u'크비탄시',
            u'Lasso': u'라소',
            u'Friesland': u'프리슬란트',
            u'sabel': u'사벌',
            u'Meerssen': u'메이르선',
            u'Zalm': u'잘름',
            u'Nijmegen': u'네이메헌',
            u'Jansen': u'얀선',
            u'Inge': u'잉어',
            u'Groningen': u'흐로닝언',
            u'Peper': u'페퍼르',
            u'Kapteyn': u'캅테인',
            u'Koopmans': u'코프만스',
            u'Rotterdam': u'로테르담',
            u'Asser': u'아서르',
            u'Spinoza': u'스피노자',
            u'Hals': u'할스',
            u'Schiphol': u'스히폴',
            u'Escher': u'에스허르',
            u'typisch': u'티피스',
            u'sjaal': u'샬',
            u'huisje': u'하위셔',
            u'ramsj': u'람시',
            u'fetisj': u'페티시',
            u'Tinbergen': u'틴베르헌',
            u'Gerrit': u'헤릿',
            u'Petrus': u'페트뤼스',
            u'Aartsen': u'아르천',
            u'Beets': u'베이츠',
            u'Veltman': u'펠트만',
            u'Einthoven': u'에인트호번',
            u'Weltevree': u'벨테브레이',
            u'Wim': u'빔',
            u'cyaan': u'시안',
        #    u'Lyonnet': u'리오넷',
            u'typisch': u'티피스',
            u'Verwey': u'페르베이',
            u'Zeeman': u'제이만',
            u'Huizinga': u'하위징아',
            u'Asser': u'아서르',
            u'Frans': u'프란스',
            u'Egmont': u'에흐몬트',
            u'Frederik': u'프레데릭',
            u'Heineken': u'헤이네컨',
            u'Lubbers': u'뤼버르스',
            u'Campen': u'캄펀',
            u'Nicolaas': u'니콜라스',
            u'Tobias': u'토비아스',
            u'Pieter': u'피터르',
            u'Vries': u'프리스',
            u'Onnes': u'오너스',
            u'Vondel': u'폰덜',
            u'Boer': u'부르',
            u'Boerhaave': u'부르하버',
            u'Utrecht': u'위트레흐트',
            u'Petrus': u'페트뤼스',
            u'Europort': u'외로포르트',
            u'Deurne': u'되르너',
            u'ruw': u'뤼',
            u'duwen': u'뒤언',
            u'Euwen': u'에위언',
            u'Bouts': u'바우츠',
            u'Bouwman': u'바우만',
            u'Paul': u'파울',
            u'Lauwersmeer': u'라우에르스메이르',
            u'Heike': u'헤이커',
            u'Bolkestein': u'볼케스테인',
            u'IJssel': u'에이설',
            u'Huizinga': u'하위징아',
            u'Zuid-Holland': u'자위트홀란트',
            u'Buys': u'바위스',
            u'draaien': u'드라이언',
            u'fraai': u'프라이',
            u'zaait': u'자이트',
            u'Maaikes': u'마이커스',
            u'Booisman': u'보이스만',
            u'Hooites': u'호이터스',
            u'Boeijinga': u'부잉아',
            u'moeite': u'무이터',
            u'Leeuwenhoek': u'레이우엔훅',
            u'Meeuwes': u'메이우어스',
            u'Lieuwma': u'리우마',
            u'Rieuwers': u'리우어르스',
        })

    def test_1st(self):
        """제1항
        무성 파열음 p, t, k는 자음 앞이나 어말에 올 경우에는 각각 받침
        ‘ㅂ, ㅅ, ㄱ'으로 적는다. 다만, 앞 모음이 이중 모음이거나 장모음(같은
        모음을 겹쳐 적는 경우)인 경우와 앞이나 뒤의 자음이 유음이나 비음인
        경우에는 ‘프, 트, 크'로 적는다.
        """
        self.assert_examples({
            u'Wit': u'빗',
            u'Gennip': u'헤닙',
            u'Kapteyn': u'캅테인',
            u'september': u'셉템버르',
            u'Petrus': u'페트뤼스',
            u'Arcadelt': u'아르카덜트',
            u'Hoop': u'호프',
            u'Eijkman': u'에이크만',
        })

    def test_2nd(self):
        """제2항
        유성 파열음 b, d가 어말에 올 경우에는 각각 ‘프, 트'로 적고, 어중에 올
        경우에는 앞이나 뒤의 자음이 유음이나 비음인 경우와 앞 모음이
        이중모음이거나 장모음(같은 모음을 겹쳐 적는 경우)인 경우에는 ‘브, 드'로
        적는다. 그 외에는 모두 받침 ‘ㅂ, ㅅ'으로 적는다.
        """
        self.assert_examples({
            u'Bram': u'브람',
            u'Hendrik': u'헨드릭',
            u'Jakob': u'야코프',
            u'Edgar': u'엣하르',
            u'Zeeland': u'제일란트',
            u'Koenraad': u'쿤라트',
        })

    def test_3rd(self):
        """제3항
        v가 어두에 올 경우에는 ‘ㅍ, 프'로 적고, 그 외에는 모두 ‘ㅂ, 브'로
        적는다.
        """
        self.assert_examples({
            u'Veltman': u'펠트만',
            u'Vries': u'프리스',
            u'Grave': u'흐라버',
            u'Weltevree': u'벨테브레이',
        })

    def test_4th(self):
        """제4항
        c는 차용어에 쓰이므로 해당 언어의 발음에 따라 ‘ㅋ'이나 ‘ㅅ'으로 적는다.
        """
        self.assert_examples({
            u'Nicolaas': u'니콜라스',
            u'Hendricus': u'헨드리퀴스',
            u'cyaan': u'시안',
            u'Franciscus': u'프란시스퀴스',
        })

    def test_5th(self):
        """제5항
        g, ch는 ‘ㅎ'으로 적되, 차용어의 경우에는 해당 언어의 발음에 따라 적는다.
        """
        self.assert_examples({
            u'gulden': u'휠던',
            u'Haag': u'하흐',
            u'Hooch': u'호흐',
            u'Volcher': u'폴허르',
            u'Eugene': u'외젠',
            u'Michael': u'미카엘',
        })

    def test_6th(self):
        """제6항
        -tie는 ‘시'로 적는다.
        """
        self.assert_examples({
            u'natie': u'나시',
            u'politie': u'폴리시',
        })

    def test_7th(self):
        """제7항
        어중의 l이 모음 앞에 오거나 모음이 따르지 않는 비음 앞에 올 때에는
        ‘?'로 적는다. 다만, 비음 뒤의 l은 모음 앞에 오더라도 ‘ㄹ'로 적는다.
        """
        self.assert_examples({
            u'Tiele': u'틸러',
            u'Zalm': u'잘름',
            u'Berlage': u'베를라허',
            u'Venlo': u'펜로',
        })

    def test_8th(self):
        """제8항: nk
        k 앞에 오는 n은 받침 ‘ㅇ'으로 적는다. 
        """
        self.assert_examples({
            u'Frank': u'프랑크',
            u'Hiddink': u'히딩크',
            u'Benk': u'벵크',
            u'Wolfswinkel': u'볼프스빙컬',
        })

    def test_9th(self):
        """제9항
        같은 자음이 겹치는 경우에는 겹치지 않은 경우와 같이 적는다.
        """
        self.assert_examples({
            u'Hobbema': u'호베마',
            u'Ballot': u'발롯',
            u'Emmen': u'에먼',
            u'Gennip': u'헤닙',
        })

    def test_10th(self):
        """제10항
        e는 ‘에'로 적는다. 다만, 이음절 이상에서 마지막 음절에 오는 e와 어말의
        e는 모두 ‘어'로 적는다.
        """
        self.assert_examples({
            u'Dennis': u'데니스',
            u'Breda': u'브레다',
            u'Stevin': u'스테빈',
            u'Peter': u'페터르',
            u'Heineken': u'헤이네컨',
            u'Campen': u'캄펀',
        })

    def test_11st(self):
        """제11항
        같은 모음이 겹치는 경우에는 겹치지 않은 경우와 같이 적는다. 다만 ee는
        ‘에이'로 적는다.
        """
        self.assert_examples({
            u'Hooch': u'호흐',
            u'Mondriaan': u'몬드리안',
            u'Kees': u'케이스',
            u'Meerssen': u'메이르선',
        })

    def test_12nd(self):
        """제12항
        -ig는 ‘어흐'로 적는다.
        """
        self.assert_examples({
            u'tachtig': u'타흐터흐',
            u'hartig': u'하르터흐',
        })

    def test_13rd(self):
        """제13항
        -berg는 ‘베르흐'로 적는다.
        """
        self.assert_examples({
            u'Duisenberg': u'다위센베르흐',
            u'Mengelberg': u'멩엘베르흐',
        })

    def test_14th(self):
        """제14항
        over-는 ‘오버르'로 적는다.
        """
        self.assert_examples({
            u'Overijssel': u'오버레이설',
            u'overkomst': u'오버르콤스트',
        })

    def test_15th(self):
        """제15항
        모음 è, é, ê, ë는 ‘에'로 적고, ï 는 ‘이' 로 적는다.
        """
        self.assert_examples({
            u'carré': u'카레',
        #    u'casuïst': u'카수이스트',
            u'drieëntwintig': u'드리엔트빈터흐',
        })

    def test_people(self):
        self.assert_examples({
            u'Jozias van Aartsen': u'요지아스 판아르천',
            u'Sharon den Adel': u'샤론 덴아덜',
            u'Dick Advocaat': u'딕 아드보카트',
            u'Karel Appel': u'카럴 아펄',
            u'Jakob Arcadelt': u'야코프 아르카덜트',
            u'Naomi van As': u'나오미 판아스',
            u'Tobias Michael Carel Asser': u'토비아스 미카엘 카럴 아서르',
            u'Ryan Babel': u'라이언 바벌',
            u'Jan Peter Balkenende': u'얀 페터르 발케넨더',
            u'Willem Barentsz': u'빌럼 바렌츠',
            u'Marco van Basten': u'마르코 판바스턴',
            u'Beatrix Wilhelmina Armgard': u'베아트릭스 빌헬미나 아름하르트',
            u'Nicolaas Beets': u'니콜라스 베이츠',
            u'Dennis Bergkamp': u'데니스 베르흐캄프',
            u'Hendrik Petrus Berlage': u'헨드릭 페트뤼스 베를라허',
            u'Bernhard Leopold': u'베른하르트 레오폴트',
            u'Leo Beenhakker': u'레오 베인하커르',
            u'Willem Blaeu': u'빌럼 블라우',
            u'Nicolaas Bloembergen': u'니콜라스 블룸베르헌',
            u'Evert Bloemsma': u'에버르트 블룸스마',
            u'Herman Boerhaave': u'헤르만 부르하버',
            u'Frits Bolkestein': u'프리츠 볼케스테인',
            u'Mark van Bommel': u'마르크 판보멀',
            u'Corrie ten Boom': u'코리 텐봄',
            u'Els Borst': u'엘스 보르스트',
            u'Theo Bos': u'테오 보스',
            u'Dirck Bouts': u'디르크 바우츠',
            u'Giovanni van Bronckhorst': u'조바니 판브롱크호르스트',
            u'Pieter Brueghel': u'피터르 브뤼헐',
            u'Armin van Buuren': u'아르민 판뷔런',
            u'Buys Ballot': u'바위스 발롯',
            u'Frank de Boer': u'프랑크 더부르',
            u'Gerard ter Borch': u'헤라르트 테르보르흐',
            u'Hans van den Broek': u'한스 판덴브룩',
            u'Inge de Bruijn': u'잉어 더브라윈',
            u'Jacob van Campen': u'야코프 판캄펀',
            u'Pieter Camper': u'피터르 캄퍼르',
            u'Phillip Cocu': u'필립 코퀴',
            u'Volcher Coiter': u'폴허르 코이터르',
            u'Anton Corbijn': u'안톤 코르베인',
            u'Johan Cruijff': u'요한 크라위프',
            u'Paul Crutzen': u'파울 크뤼천',
            u'Edgar Davids': u'엣하르 다비츠',
            u'Edith van Dijk': u'에딧 판데이크',
            u'Edsger Dijkstra': u'에츠허르 데이크스트라',
            u'Theo van Doesburg': u'테오 판두스뷔르흐',
            u'Kees van Dongen': u'케이스 판동언',
            u'Wim Duisenberg': u'빔 다위센베르흐',
            u'Christiaan Eijkman': u'크리스티안 에이크만',
            u'Willem Einthoven': u'빌럼 에인트호번',
            u'Pim Fortuyn': u'핌 포르타윈',
            u'Louis van Gaal': u'루이 판할',
            u'Yuri van Gelder': u'유리 판헬더르',
            u'Karien van Gennip': u'카린 판헤닙',
            u'Yvonne van Gennip': u'이보너 판헤닙',
            u'Annette Gerritsen': u'아네터 헤리천',
            u'Arnold Geulincx': u'아르놀트 횔링크스',
            u'Hans van Ginkel': u'한스 판힝컬',
            u'Hugo van der Goes': u'휘호 판데르후스',
            u'Theo van Gogh': u'테오 반고흐',
            u'Vincent van Gogh': u'빈센트 반고흐',
            u'Herman Gorter': u'헤르만 호르터르',
            u'Jan Gossaert': u'얀 호사르트',
            u'Reinier de Graaf': u'레이니어르 더흐라프',
            u'Frank de Grave': u'프랑크 더흐라버',
            u'Hugo de Groot': u'휘호 더흐로트',
            u'Ruud Gullit': u'뤼트 휠릿',
            u'Frans Hals': u'프란스 할스',
            u'Hendrik Hamel': u'헨드릭 하멜',
            u'Herman Heijermans': u'헤르만 헤이예르만스',
            u'Jan Baptista van Helmont': u'얀 밥티스타 판헬몬트',
            u'Guus Hiddink': u'휘스 히딩크',
            u'Meindert Hobbema': u'메인더르트 호베마',
            u'Jacobus Henricus van ’t Hoff': u'야코뷔스 헨리퀴스 판엇호프',
            u'Pieter de Hooch': u'피터르 더호흐',
            u'Gerard ’t Hooft': u'헤라르트 엇호프트',
            u'Pieter van den Hoogenband': u'피터르 판덴호헨반트',
            u'Jaap de Hoop Scheffer': u'야프 더호프 스헤퍼르',
            u'Johan Huizinga': u'요한 하위징아',
            u'Mark Huizinga': u'마르크 하위징아',
            u'Klaas-Jan Huntelaar': u'클라스얀 휜텔라르',
            u'Christiaan Huygens': u'크리스티안 하위헌스',
            u'Jan Ingenhousz': u'얀 잉엔하우스',
            u'Jozef Israëls': u'요제프 이스라엘스',
            u'Cornelis Jansen': u'코르넬리스 얀선',
            u'Famke Janssen': u'팜커 얀선',
            u'Johan Jongkind': u'요한 용킨트',
            u'Annemarie Jorritsma': u'아네마리 요리츠마',
            u'Juliana Louise Emma Marie Wilhelmina': \
            u'율리아나 루이서 에마 마리 빌헬미나',
            u'Heike Kamerlingh Onnes': u'헤이커 카메를링 오너스',
            u'Jacobus Cornelius Kapteyn': u'야코뷔스 코르넬리위스 캅테인',
            u'Petrus Jacobus Kipp': u'페트뤼스 야코뷔스 킵',
            u'Patrick Kluivert': u'파트릭 클라위버르트',
            u'Ronald Koeman': u'로날트 쿠만',
            u'Wim Kok': u'빔 콕',
            u'Willem Johan Kolff': u'빌럼 요한 콜프',
            u'Pieter Kooijmans': u'피터르 코이만스',
            u'Rem Koolhaas': u'렘 콜하스',
            u'Willem de Kooning': u'빌럼 더코닝',
            u'Tjalling Koopmans': u'티알링 코프만스',
            u'Benk Korthals': u'벵크 코르탈스',
            u'Sven Kramer': u'스벤 크라머르',
            u'Dirk Kuyt': u'디르크 카위트',
            u'Lamoraal van Egmont': u'라모랄 판에흐몬트',
            u'Orlando di Lasso': u'오를란도 디라소',
            u'Jan Leeghwater': u'얀 레이흐바터르',
            u'Antoni van Leeuwenhoek': u'안토니 판레이우엔훅',
            u'Lucas van Leyden': u'뤼카스 판레이던',
            u'Jan Huygen van Linschoten': u'얀 하위헌 판린스호턴',
            u'Hendrik Willem van Loon': u'헨드릭 빌럼 판론',
            u'Hendrik Antoon Lorentz': u'헨드릭 안톤 로렌츠',
            u'Ruud Lubbers': u'뤼트 뤼버르스',
            u'Karel van Mander': u'카럴 판만더르',
            u'Bert van Marwijk': u'베르트 판마르베이크',
            u'Joris Mathijsen': u'요리스 마테이선',
            u'Simon van der Meer': u'시몬 판데르메이르',
            u'Willem Mengelberg': u'빌럼 멩엘베르흐',
            u'Paul Menkveld': u'파울 멩크벨트',
            u'Gabriël Metsu': u'가브리엘 메취',
            u'Rinus Michels': u'리뉘스 미헐스',
            u'Piet Mondriaan': u'핏 몬드리안',
            u'Harry Mulisch': u'하리 뮐리스',
            u'Ruud van Nistelrooy': u'뤼트 판니스텔로이',
            u'Teun de Nooijer': u'퇸 더노이여르',
            u'Cees Nooteboom': u'케이스 노테봄',
            u'André Ooijer': u'안드레 오이여르',
            u'Jan Hendrik Oort': u'얀 헨드릭 오르트',
            u'Adriaen van Ostade': u'아드리안 판오스타더',
            u'Marc Overmars': u'마르크 오버르마르스',
            u'Joachim Patinir': u'요아힘 파티니르',
            u'Bram Peper': u'브람 페퍼르',
            u'Robin van Persie': u'로빈 판페르시',
            u'Frank Rijkaard': u'프랑크 레이카르트',
            u'Rembrandt Harmenszoon van Rijn': u'렘브란트 하르먼스존 판레인',
            u'Arjen Robben': u'아르연 로번',
            u'Guido van Rossum': u'히도 판로쉼',
            u'André Rouvoet': u'안드레 라우붓',
            u'Jacob van Ruisdael': u'야코프 판라위스달',
            u'Mark Rutte': u'마르크 뤼터',
            u'Michiel de Ruyter': u'미키엘 더라위터르',
            u'Edwin van der Sar': u'에드빈 판데르사르',
            u'Nicolien Sauerbreij': u'니콜린 사우에르브레이',
            u'Clarence Seedorf': u'클라렌서 세이도르프',
            u'Geertgen tot Sint Jans': u'헤이르트헌 톳신트얀스',
            u'Claus Sluter': u'클라우스 슬뤼터르',
            u'Rik Smits': u'릭 스미츠',
            u'Wesley Sneijder': u'베슬리 스네이더르',
            u'Willebrord Snel van Royen': u'빌레브로르트 스넬 판로이언',
            u'Baruch Spinoza': u'바뤼흐 스피노자',
            u'Jan Steen': u'얀 스테인',
            u'Simon Stevin': u'시몬 스테빈',
            u'Jan Swammerdam': u'얀 스바메르담',
            u'Jan Pieterszoon Sweelinck': u'얀 피터르스존 스베일링크',
            u'Abel Tasman': u'아벌 타스만',
            u'Cornelis Petrus Tiele': u'코르넬리스 페트뤼스 틸러',
            u'Tiësto': u'티에스토',
            u'Jan Tinbergen': u'얀 틴베르헌',
            u'Nikolaas Tinbergen': u'니콜라스 틴베르헌',
            u'Mark Tuitert': u'마르크 타위터르트',
            u'Gerard Unger': u'헤라르트 윙어르',
            u'Joop den Uyl': u'요프 덴아윌',
            u'Rafaël van der Vaart': u'라파엘 판데르파르트',
            u'Adriaen van de Velde': u'아드리안 판더펠더',
            u'Marleen Veldhuis': u'마를레인 펠드하위스',
            u'Martinus Veltman': u'마르티뉘스 펠트만',
            u'Esther Vergeer': u'에스터르 페르헤이르',
            u'Paul Verhoeven': u'파울 페르후번',
            u'Johannes Vermeer': u'요하네스 페르메이르',
            u'Albert Verwey': u'알버르트 페르베이',
            u'Joost van den Vondel': u'요스트 판덴폰덜',
            u'Marianne Vos': u'마리아너 포스',
            u'Hugo de Vries': u'휘호 더프리스',
            u'Johannes Diderik van der Waals': u'요하네스 디데릭 판데르발스',
            u'Maarten van der Weijden': u'마르턴 판데르베이던',
            u'Jan Weltevree': u'얀 벨테브레이',
            u'Rogier van der Weyden': u'로히어르 판데르베이던',
            u'Geert Wilders': u'헤이르트 빌더르스',
            u'Adriaan Willaert': u'아드리안 빌라르트',
            u'Willem-Alexander Claus George Ferdinand': \
            u'빌럼알렉산더르 클라우스 헤오르허 페르디난트',
            u'Michael Dudok de Wit': u'미카엘 뒤독 더빗',
            u'Johan de Witt': u'요한 더빗',
            u'Joost Wolfswinkel': u'요스트 볼프스빙컬',
            u'Ireen Wüst': u'이레인 뷔스트',
            u'Gerrit Zalm': u'헤릿 잘름',
            u'Pieter Zeeman': u'피터르 제이만',
            u'Frits Zernike': u'프리츠 제르니커',
            u'Joop Zoetemelk': u'요프 주테멜크',
        })

    def test_places(self):
        self.assert_examples({
            u'Almelo': u'알멜로',
            u'Alphen aan den Rijn': u'알펀안덴레인',
            u'Ameland': u'아멜란트',
            u'Amersfoort': u'아메르스포르트',
            u'Amstelveen': u'암스텔베인',
            u'Amsterdam': u'암스테르담',
            u'Andelst': u'안델스트',
            u'Apeldoorn': u'아펠도른',
            u'Appingedam': u'아핑에담',
            u'Arnhem': u'아른험',
            u'Assen': u'아선',
            u'Asten': u'아스턴',
            u'Barneveld': u'바르네벨트',
            u'Bedum': u'베뒴',
            u'Beilen': u'베일런',
            u'Bergen op Zoom': u'베르헌옵좀',
            u'Berkel': u'베르컬',
            u'Berkhout': u'베르크하우트',
            u'Best': u'베스트',
            u'Beverwijk': u'베베르베이크',
            u'Birdaard': u'비르다르트',
            u'Bolsward': u'볼스바르트',
            u'Borne': u'보르너',
            u'Boxtel': u'복스털',
            u'Breda': u'브레다',
            u'Breskens': u'브레스컨스',
            u'Burgh-Haamstede': u'뷔르흐함스테더',
            u'Capelle aan de Ijssel': u'카펠러안더에이설',
            u'Castricum': u'카스트리큄',
            u'Coevorden': u'쿠보르던',
            u'Creil': u'크레일',
            u'Culemborg': u'퀼렘보르흐',
            u'Delfzijl': u'델프제일',
            u'Den Bosch': u'덴보스',
            u'Den Burg': u'덴뷔르흐',
            u'Den Haag': u'덴하흐',
            u'Den Helder': u'덴헬더르',
            u'Deventer': u'데벤터르',
            u'Diremond': u'디레몬트',
            u'Doesburg': u'두스뷔르흐',
            u'Doetinchem': u'두틴험',
            u'Dokkum': u'도큄',
            u'Dordrecht': u'도르드레흐트',
            u'Drachten': u'드라흐턴',
            u'Drenthe': u'드렌터',
            u'Dronten': u'드론턴',
            u'Ede': u'에더',
            u'Eemskanaal': u'에임스카날',
            u'Eenrum': u'에인륌',
            u'Eibergen': u'에이베르헌',
            u'Eindhoven': u'에인트호번',
            u'Emmeloord': u'에멜로르트',
            u'Enkhuizen': u'엥크하위전',
            u'Enschede': u'엔스헤데',
            u'Erp': u'에르프',
            u'Etten-Leur': u'에턴뢰르',
            u'Ferwerd': u'페르버르트',
            u'Franeker': u'프라네커르',
            u'Gelderland': u'헬데를란트',
            u'Gorinchem': u'호린험',
            u'Gouda': u'하우다',
            u'Haarlem': u'하를럼',
            u'Halsteren': u'할스테런',
            u'Hapert': u'하퍼르트',
            u'Hardenberg': u'하르덴베르흐',
            u'Harderwijk': u'하르데르베이크',
            u'Harlingen': u'하를링언',
            u'Heerde': u'헤이르더',
            u'Heerenveen': u'헤이렌베인',
            u'Heerhugowaard': u'헤이르휘호바르트',
            u'Heerlen': u'헤이를런',
            u'Hellevoetsluis': u'헬레부츨라위스',
            u'Hengelo': u'헹엘로',
            u'Herkenbosch': u'헤르켄보스',
            u'Hillegom': u'힐레홈',
            u'Hilversum': u'힐베르쉼',
            u'Hoek van Holland': u'훅판홀란트',
            u'Hollum': u'홀륌',
            u'Hoogerheide': u'호헤르헤이더',
            u'Hoogeveen': u'호헤베인',
            u'Hoogezand-Sappemeer': u'호헤잔트사페메이르',
            u'Hoog-Keppel': u'호흐케펄',
            u'Hoorn': u'호른',
            u'IJmuiden': u'에이마위던',
            u'IJsselmeer': u'에이설메이르',
            u'Kampen': u'캄펀',
            u'Katwijk aan Zee': u'카트베이크안제이',
            u'Kerkrade': u'케르크라더',
            u'Kessel': u'케설',
            u'Kloosterhaar': u'클로스테르하르',
            u'Kollum': u'콜륌',
            u'Koudekerke': u'카우데케르커',
            u'Kraggenburg': u'크라헨뷔르흐',
            u'Lauwersmeer': u'라우에르스메이르',
            u'Leeuwarden': u'레이우아르던',
            u'Leiden': u'레이던',
            u'Lelystad': u'렐리스타트',
            u'Luyksgestel': u'라위크스헤스털',
            u'Maarssen': u'마르선',
            u'Maastricht': u'마스트리흐트',
            u'Markermeer': u'마르케르메이르',
            u'Marsdiep': u'마르스딥',
            u'Mechelen': u'메헬런',
            u'Meppel': u'메펄',
            u'Middelburg': u'미델뷔르흐',
            u'Middelharnis': u'미델하르니스',
            u'Naarden': u'나르던',
            u'Nieuwegein': u'니우에헤인',
            u'Nieuwe Niedorp': u'니우어니도르프',
            u'Nijkerk': u'네이커르크',
            u'Nijverdal': u'네이베르달',
            u'Noord-Brabant': u'노르트브라반트',
            u'Noord-Holland': u'노르트홀란트',
            u'Oenkerk': u'웅커르크',
            u'Oldenzaal': u'올덴잘',
            u'Ommen': u'오먼',
            u'Oosterhout': u'오스테르하우트',
            u'Oosterschelde': u'오스테르스헬더',
            u'Oost-Vlieland': u'오스트플릴란트',
            u'Oss': u'오스',
            u'Philippine': u'필리피너',
            u'Purmerend': u'퓌르메런트',
            u'Raalte': u'랄터',
            u'Roermond': u'루르몬트',
            u'Roordahuizum': u'로르다하위쥠',
            u'Roosendaal': u'로센달',
            u'Schagen': u'스하헌',
            u'Scharendijke': u'스하렌데이커',
            u'Schiermonnikoog': u'스히르모니코흐',
            u'Schoonhoven': u'스혼호번',
            u'’s-Gravenhage': u"'스흐라벤하허",
            u'’s-Hertogenbosch': u"'스헤르토헨보스",
            u'Sittarad': u'시타라트',
            u'Sloten': u'슬로턴',
            u'Sluis': u'슬라위스',
            u'Sneek': u'스네이크',
            u'Spijkenisse': u'스페이케니서',
            u'Steeswijk': u'스테이스베이크',
            u'Stein': u'스테인',
            u'Terneuzen': u'테르뇌전',
            u'Terschelling': u'테르스헬링',
            u'Texel': u'텍설',
            u'Tiel': u'틸',
            u'Tilburg': u'틸뷔르흐',
            u'Torenberg': u'토렌베르흐',
            u'Uden': u'위던',
            u'Uithuizen': u'아위트하위전',
            u'Urk': u'위르크',
            u'Valkenswaard': u'팔켄스바르트',
            u'Veendam': u'페인담',
            u'Veenendal': u'페이넨달',
            u'Veldhoven': u'펠트호번',
            u'Vlaardingen': u'플라르딩언',
            u'Vlieland': u'플릴란트',
            u'Vlissingen': u'플리싱언',
            u'Vriezenveen': u'프리젠베인',
            u'Waal': u'발',
            u'Waalwijk': u'발베이크',
            u'Wadden': u'바던',
            u'Waddeneilanden': u'바데네일란던',
            u'Waddenzee': u'바덴제이',
            u'Waddinxveen': u'바딩크스베인',
            u'Wageningen': u'바헤닝언',
            u'Wanroij': u'반로이',
            u'Weert': u'베이르트',
            u'Westerschelde': u'베스테르스헬더',
            u'Westkapelle': u'베스트카펠러',
            u'West-Terschelling': u'베스트테르스헬링',
            u'Wieringerwerf': u'비링에르버르프',
            u'Wijchen': u'베이헌',
            u'Winterswijk': u'빈테르스베이크',
            u'Witmarsum': u'비트마르쉼',
            u'Wolvega': u'볼베하',
            u'Wonschoten': u'본스호턴',
            u'Zaandam': u'잔담',
            u'Zandvoort': u'잔드보르트',
            u'Zevenaar': u'제베나르',
            u'Zevenbergen': u'제벤베르헌',
            u'Zutphan': u'쥣판',
            u'Zwolle': u'즈볼러',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'brik': u'브릭',
            u'Delft Stedelijk': u'델프트 스테델레이크',
            u'De Stijl': u'더스테일',
            u'gulden': u'휠던',
            u'Elfstedentocht': u'엘프스테덴토흐트',
        })

########NEW FILE########
__FILENAME__ = pol
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.pol import Polish


class PolishTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0208.jsp """

    lang = Polish()

    def test_people(self):
        self.assert_examples({
            u'Jerzy Andrzejewski': u'예지 안제예프스키',
            u'Stefan Banach': u'스테판 바나흐',
            u'Stanisław Barańczak': u'스타니스와프 바란차크',
            u'Marek Belka': u'마레크 벨카',
            u'Seweryn Bialer': u'세베린 비알레르',
            u'Bolesław Bierut': u'볼레스와프 비에루트',
            u'Zbigniew Boniek': u'즈비그니에프 보니에크',
            u'Bogdan Borusewicz': u'보그단 보루세비치',
            u'Zbigniew Bujak': u'즈비그니에프 부야크',
            u'Jerzy Buzek': u'예지 부제크',
            u'Włodzimierz Cimoszewicz': u'브워지미에시 치모셰비치',
            u'Józef Cyrankiewicz': u'유제프 치란키에비치',
            u'Ignacy Daszyński': u'이그나치 다신스키',
            u'Kazimierz Deyna': u'카지미에시 데이나',
            u'Roman Dmowski': u'로만 드모프스키',
            u'Jerzy Dudek': u'예지 두데크',
            u'Dariusz Dziekanowski': u'다리우시 지에카노프스키',
            u'Feliks Dzierżyński': u'펠릭스 지에르진스키',
            u'Kazimierz Fajans': u'카지미에시 파얀스',
            u'Magdalena Frackowiak': u'마그달레나 프라츠코비아크',
            u'Kazimierz Funk': u'카지미에시 푼크',
            u'Edward Gierek': u'에드바르트 기에레크',
            u'Józef Glemp': u'유제프 글렘프',
            u'Leopold Godowsky': u'레오폴트 고도프스키',
            u'Witold Gombrowicz': u'비톨트 곰브로비치',
            u'Władysław Gomułka': u'브와디스와프 고무우카',
            u'Jerzy Grotowski': u'예지 그로토프스키',
            u'Zbigniew Herbert': u'즈비그니에프 헤르베르트',
            u'Leonid Hurwicz': u'레오니트 후르비치',
            u'Jarosław Iwaszkiewicz': u'야로스와프 이바슈키에비치',
            u'Aleksander Jabłoński': u'알렉산데르 야브원스키',
            u'Jadwiga Andegaweńska': u'야드비가 안데가벤스카',
            u'Jagiełło': u'야기에워',
            u'Wanda Jakubowska': u'반다 야쿠보프스카',
            u'Henryk Jankowski': u'헨리크 얀코프스키',
            u'Wojciech Jaruzelski': u'보이치에흐 야루젤스키',
            u'Otylia Jędrzejczak': u'오틸리아 옝제이차크',
            u'Jan Andrzej Paweł Kaczmarek': \
                u'얀 안제이 파베우 카치마레크',
            u'Jarosław Kaczyński': u'야로스와프 카친스키',
            u'Lech Kaczyński': u'레흐 카친스키',
            u'Stanisław Kania': u'스타니스와프 카니아',
            u'Krzysztof Kieślowski': u'크시슈토프 키에실로프스키',
            u'Stefan Kisielewski': u'스테판 키시엘레프스키',
            u'Leszek Kołakowski': u'레셰크 코와코프스키',
            u'Bronisław Komorowski': u'브로니스와프 코모로프스키',
            u'Paweł Korzeniowski': u'파베우 코제니오프스키',
            u'Tadeusz Kościuszko': u'타데우시 코시치우슈코',
            u'Justyna Kowalczyk': u'유스티나 코발치크',
            u'Zygmunt Krasiński': u'지그문트 크라신스키',
            u'Jacek Krzynówek': u'야체크 크시누베크',
            u'Jacek Kuroń': u'야체크 쿠론',
            u'Aleksander Kwaśniewski': u'알렉산데르 크바시니에프스키',
            u'Wanda Landowska': u'반다 란도프스카',
            u'Grzegorz Lato': u'그제고시 라토',
            u'Joachim Lelewel': u'요아힘 렐레벨',
            u'Włodzimierz Lubański': u'브워지미에시 루반스키',
            u'Jan Łukasiewicz': u'얀 우카시에비치',
            u'Bronisław Malinowski': u'브로니스와프 말리노프스키',
            u'Adam Małysz': u'아담 마위시',
            u'Kazimierz Marcinkiewicz': u'카지미에시 마르친키에비치',
            u'Tadeusz Mazowiecki': u'타데우시 마조비에츠키',
            u'Zbigniew Messner': u'즈비그니에프 메스네르',
            u'Adam Michnik': u'아담 미흐니크',
            u'Adam Mickiewicz': u'아담 미츠키에비치',
            u'Stanisław Mikołajczyk': u'스타니스와프 미코와이치크',
            u'Leszek Miller': u'레셰크 밀레르',
            u'Czesław Miłosz': u'체스와프 미워시',
            u'Sławomir Mrożek': u'스와보미르 므로제크',
            u'Cyprian Kamil Norwid': u'치프리안 카밀 노르비트',
            u'Edward Ochab': u'에드바르트 오하프',
            u'Eliza Orzeszkowa': u'엘리자 오제슈코바',
            u'Ignacy Jan Paderewski': u'이그나치 얀 파데레프스키',
            u'Krzysztof Penderecki': u'크시슈토프 펜데레츠키',
            u'Józef Piłsudski': u'유제프 피우수트스키',
            u'Jacek Podsiadło': u'야체크 포트시아드워',
            u'Anja Rubik': u'아냐 루비크',
            u'Mateusz Sawrymowicz': u'마테우시 사브리모비치',
            u'Wacław Sierpiński': u'바츠와프 시에르핀스키',
            u'Maria Skłodowska': u'마리아 스크워도프스카',
            u'Włodzimierz Smolarek': u'브워지미에시 스몰라레크',
            u'Katarzyna Sowula': u'카타지나 소불라',
            u'Andrzej Stasiuk': u'안제이 스타시우크',
            u'Andrzej Szarmach': u'안제이 샤르마흐',
            u'Wojciech Szczęsny': u'보이치에흐 슈쳉스니',
            u'Piotr Szewc': u'피오트르 셰프츠',
            u'Sławomir Szmal': u'스와보미르 슈말',
            u'Rafał Szukała': u'라파우 슈카와',
            u'Alfred Tarski': u'알프레트 타르스키',
            u'Stefan Themerson': u'스테판 테메르손',
            u'Olga Tokarczuk': u'올가 토카르추크',
            u'Jan Tomaszewski': u'얀 토마셰프스키',
            u'Donald Tusk': u'도날트 투스크',
            u'Andrzej Wajda': u'안제이 바이다',
            u'Lech Wałęsa': u'레흐 바웬사',
            u'Mia Wasikowska': u'미아 바시코프스카',
            u'Wanda Wasilewska': u'반다 바실레프스카',
            u'Adam Ważyk': u'아담 바지크',
            u'Aleksander Wielopolski': u'알렉산데르 비엘로폴스키',
            u'Henryk Wieniawski': u'헨리크 비에니아프스키',
            u'Ernest Wilimowski': u'에르네스트 빌리모프스키',
            u'Stanisław Ignacy Witkiewicz': \
                u'스타니스와프 이그나치 비트키에비치',
            u'Michał Witkowski': u'미하우 비트코프스키',
            u'Karol Wojtyła': u'카롤 보이티와',
            u'Katarzyna Woźniak': u'카타지나 보지니아크',
            u'Stanisław Wyspiański': u'스타니스와프 비스피안스키',
            u'Stefan Wyszyński': u'스테판 비신스키',
            u'Ludwik Łazarz Zamenhof': u'루드비크 와자시 자멘호프',
            u'Krystian Zimerman': u'크리스티안 지메르만',
            u'Luiza Złotkowska': u'루이자 즈워트코프스카',
            u'Florian Znaniecki': u'플로리안 즈나니에츠키',
            u'Stefan Żeromski': u'스테판 제롬스키',
            u'Maciej Żurawski': u'마치에이 주라프스키',
        })

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0106.jsp """
        self.assert_examples({
            u'burak': u'부라크',
            u'szybko': u'십코',
            u'dobrze': u'도브제',
            u'chleb': u'흘레프',
            u'cel': u'첼',
            u'Balicki': u'발리츠키',
            u'noc': u'노츠',
            u'dać': u'다치',
            u'dach': u'다흐',
            u'zdrowy': u'즈드로비',
            u'słodki': u'스워트키',
            u'pod': u'포트',
            u'fasola': u'파솔라',
            u'befsztyk': u'베프슈티크',
            u'góra': u'구라',
            u'grad': u'그라트',
            u'targ': u'타르크',
            u'herbata': u'헤르바타',
            u'Hrubieszów': u'흐루비에슈프',
            u'kino': u'키노',
            u'daktyl': u'닥틸',
            u'król': u'크룰',
            u'bank': u'반크',
            u'lis': u'리스',
            u'kolano': u'콜라노',
            u'motyl': u'모틸',
            u'most': u'모스트',
            u'zimno': u'짐노',
            u'sam': u'삼',
            u'nerka': u'네르카',
            u'dokument': u'도쿠멘트',
            u'dywan': u'디반',
            u'Gdańsk': u'그단스크',
            u'Poznań': u'포즈난',
            u'para': u'파라',
            u'Słupsk': u'스웁스크',
            u'chłop': u'흐워프',
            u'rower': u'로베르',
            u'garnek': u'가르네크',
            u'sznur': u'슈누르',
            u'serce': u'세르체',
            u'srebro': u'스레브로',
            u'pas': u'파스',
            u'ślepy': u'실레피',
            u'dziś': u'지시',
            u'tam': u'탐',
            u'matka': u'마트카',
            u'but': u'부트',
            u'Warszawa': u'바르샤바',
            u'piwnica': u'피브니차',
            u'krew': u'크레프',
            u'zamek': u'자메크',
            u'zbrodnia': u'즈브로드니아',
            u'wywóz': u'비부스',
            u'gwoździk': u'그보지지크',
            u'więź': u'비엥시',
            u'żyto': u'지토',
            u'różny': u'루주니',
            u'łyżka': u'위슈카',
            u'straż': u'스트라시',
            u'chory': u'호리',
            u'kuchnia': u'쿠흐니아',
            u'dach': u'다흐',
            u'dziura': u'지우라',
            u'dzwon': u'즈본',
            u'mosiądz': u'모시옹츠',
            u'niedźwiedź': u'니에치비에치',
            u'drzewo': u'제보',
            u'łodż': u'워치',
            u'czysty': u'치스티',
            u'beczka': u'베치카',
            u'klucz': u'클루치',
            u'szary': u'샤리',
            u'musztarda': u'무슈타르다',
            u'kapelusz': u'카펠루시',
            u'rzeka': u'제카',
            u'Przemyśl': u'프셰미실',
            u'kołnierz': u'코우니에시',
            u'jasny': u'야스니',
            u'kraj': u'크라이',
            u'łono': u'워노',
            u'głowa': u'그워바',
            u'bułka': u'부우카',
            u'kanał': u'카나우',
            u'trawa': u'트라바',
            u'trąba': u'트롱바',
            u'mąka': u'몽카',
            u'kąt': u'콩트',
            u'tą': u'통',
            u'zero': u'제로',
            u'kępa': u'켕파',
            u'węgorz': u'벵고시',
            u'Częstochowa': u'쳉스토호바',
            u'proszę': u'프로셰',
            u'zima': u'지마',
            u'udo': u'우도',
            u'próba': u'프루바',
            u'kula': u'쿨라',
            u'daktyl': u'닥틸',
        })

    def test_1st(self):
        """제1항: k, p
        어말과 유성 자음 앞에서는 '으'를 붙여 적고, 무성 자음 앞에서는
        받침으로 적는다.
        """
        self.assert_examples({
            u'zamek': u'자메크',
            u'mokry': u'모크리',
            u'Słupsk': u'스웁스크',
        })

    def test_2nd(self):
        """제2항: b, d, g
        1. 어말에 올 때에는 '프', '트', '크'로 적는다.
        2. 유성 자음 앞에서는 '브', '드', '그'로 적는다.
        3. 무성 자음 앞에서 b, g는 받침으로 적고, d는 '트'로 적는다.
        """
        self.assert_examples({
            u'od': u'오트',
            u'zbrodnia': u'즈브로드니아',
            u'Grabski': u'그랍스키',
            u'odpis': u'오트피스',
        })

    def test_3rd(self):
        """제3항: w, z, ź, dz, ż, rz, sz
        1. w, z, ź, dz가 무성 자음 앞이나 어말에 올 때에는 '프, 스, 시, 츠'로
           적는다.
        2. ż와 rz는 모음 앞에 올 때에는 'ㅈ'으로 적되, 앞의 자음이 무성
           자음일 때에는 '시'로 적는다. 유성 자음 앞에 올 때에는 '주', 무성
           자음 앞에 올 때에는 '슈', 어말에 올 때에는 '시'로 적는다.
        3. sz는 자음 앞에서는 '슈', 어말에서는 '시'로 적는다.
        """
        self.assert_examples({
            u'zabawka': u'자바프카',
            u'obraz': u'오브라스',
            u'Rzeszów': u'제슈프',
            u'Przemyśl': u'프셰미실',
            u'grzmot': u'그주모트',
            u'łóżko': u'우슈코',
            u'pęcherz': u'펭헤시',
            u'koszt': u'코슈트',
            u'kosz': u'코시',
        })

    def test_4th(self):
        """제4항: ł
        1. ł는 뒤따르는 모음과 결합할 때 합쳐서 적는다. (ło는 '워'로 적는다.)
           다만, 자음 뒤에 올 때에는 두 음절로 갈라 적는다.
        2. oł는 '우'로 적는다.
        """
        self.assert_examples({
            u'łono': u'워노',
            u'głowa': u'그워바',
            u'przyjaciół': u'프시야치우',
        })

    def test_5th(self):
        """제5항: l
        어중의 l이 모음 앞에 올 때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'olej': u'올레이',
        })

    def test_6th(self):
        """제6항: m
        어두의 m이 l, r 앞에 올 때에는 '으'를 붙여 적는다.
        """
        self.assert_examples({
            u'mleko': u'믈레코',
            u'mrówka': u'므루프카',
        })

    def test_7th(self):
        """제7항: ę
        ę은 '엥'으로 적는다. 다만, 어말의 ę는 '에'로 적는다.
        """
        self.assert_examples({
            u'ręka': u'렝카',
            u'proszę': u'프로셰',
        })

    def test_8th(self):
        """제8항
        'ㅈ', 'ㅊ'으로 표기되는 자음(c, z) 뒤의 이중 모음은 단모음으로 적는다.
        """
        self.assert_examples({
            u'stacja': u'스타차',
            u'fryzjer': u'프리제르',
        })

    def test_etc(self):
        self.assert_examples({
            u'przjyaciół': u'프시아치우',
        })
########NEW FILE########
__FILENAME__ = por
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.por import Portuguese


class PortugueseTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0219.jsp """

    lang = Portuguese()

    def test_1st(self):
        """제1항
        c, g는 a, o, u 앞에서는 각각 ‘ㅋ, ㄱ'으로 적고, e, i 앞에서는
        ‘ㅅ, ㅈ'으로 적는다.
        """
        self.assert_examples({
            u'Cabral': u'카브랄',
            u'Camocim': u'카모싱',
            u'Egas': u'에가스',
            u'Gil': u'질',
        })

    def test_2nd(self):
        """제2항
        gu, qu는 a, o, u 앞에서는 각각 ‘구, 쿠'로 적고, e, i 앞에서는
        ‘ㄱ, ㅋ'으로 적는다.
        """
        self.assert_examples({
            u'Iguaçú': u'이구아수',
            u'Araquari': u'아라쿠아리',
            u'Guerra': u'게하',
            u'Aquilino': u'아킬리누',
        })

    def test_3rd(self):
        """제3항
        d, t는 ㄷ, ㅌ으로 적는다.
        """
        self.assert_examples({
            u'Amado': u'아마두',
            u'Costa': u'코스타',
            u'Diamantina': u'디아만티나',
            u'Alegrete': u'알레그레트',
            u'Montes': u'몬트스',
        })

    def test_4th(self):
        """제4항
        어말의 -che는 ‘시'로 적는다.
        """
        self.assert_examples({
            u'Angoche': u'앙고시',
            u'Peniche': u'페니시',
        })

    def test_5th(self):
        """제5항: l
        1. 어중의 l이 모음 앞에 오거나 모음이 따르지 않는 비음 앞에 오는
           경우에는 ‘?'로 적는다. 다만, 비음 뒤의 l은 모음 앞에 오더라도 ‘ㄹ'로
           적는다.
        2. 어말 또는 자음 앞의 l은 받침 ‘ㄹ'로 적는다.
        """
        self.assert_examples({
            u'Carlos': u'카를루스',
            u'Amalia': u'아말리아',
            u'Sul': u'술',
            u'Azul': u'아줄',
            u'Gilberto': u'질베르투',
            u'Caracol': u'카라콜',
        })

    def test_6th(self):
        """제6항
        m, n은 각각 ㅁ, ㄴ으로 적고, 어말에서는 모두 받침 ‘ㅇ'으로 적는다.
        어말 -ns의 n도 받침 ‘ㅇ'으로 적는다.
        """
        self.assert_examples({
            u'Manuel': u'마누엘',
            u'Moniz': u'모니스',
            u'Campos': u'캄푸스',
            u'Vincente': u'빈센트',
            u'Santarem': u'산타렝',
            u'Rondon': u'혼동',
            u'Lins': u'링스',
            u'Rubens': u'후벵스',
        })

    def test_7th(self):
        """제7항
        ng, nc, nq 연쇄에서 ‘g, c, q'가 ‘ㄱ'이나 ‘ㅋ'으로 표기되면 ‘n'은
        받침 ‘ㅇ'으로 적는다.
        """
        self.assert_examples({
            u'Angola': u'앙골라',
            u'Angelo': u'안젤루',
            u'Branco': u'브랑쿠',
            u'Francisco': u'프란시스쿠',
            u'Conquista': u'콩키스타',
            u'Junqueiro': u'중케이루',
        })

    def test_8th(self):
        """제8항
        r는 어두나 n, l, s 뒤에 오는 경우에는 ‘ㅎ'으로 적고, 그 밖의 경우에는
        ‘ㄹ, 르'로 적는다.
        """
        self.assert_examples({
            u'Ribeiro': u'히베이루',
            u'Henrique': u'엔히크',
            u'Bandeira': u'반데이라',
            u'Salazar': u'살라자르',
        })

    def test_9th(self):
        """제9항: s
        1. 어두나 모음 앞에서는 ‘ㅅ'으로 적고, 모음 사이에서는 ‘ㅈ'으로 적는다.
        2. 무성 자음 앞이나 어말에서는 ‘스'로 적고, 유성 자음 앞에서는 ‘즈'로
           적는다.
        """
        self.assert_examples({
            u'Salazar': u'살라자르',
            u'Afonso': u'아폰수',
            u'Barroso': u'바호주',
            u'Gervasio': u'제르바지우',
        })

    def test_10th(self):
        """제10항: sc, sç, xc
        sc와 xc는 e, i 앞에서 ‘ㅅ'으로 적는다. sç는 항상 ‘ㅅ'으로 적는다.
        """
        self.assert_examples({
            u'Nascimento': u'나시멘투',
            u'piscina': u'피시나',
            u'excelente': u'이셀렌트',
            u'cresça': u'크레사',
        })

    def test_11st(self):
        """제11항
        x는 ‘시'로 적되, 어두 e와 모음 사이에 오는 경우에는 ‘ㅈ'으로 적는다.
        """
        self.assert_examples({
            u'Teixeira': u'테이셰이라',
            u'lixo': u'리슈',
            u'exame': u'이자므',
            u'exemplo': u'이젬플루',
        })

    def test_12nd(self):
        """제12항
        같은 자음이 겹치는 경우에는 겹치지 않은 경우와 같이 적는다. 다만, rr는
        ‘ㅎ, 흐'로, ss는 ‘ㅅ, 스'로 적는다.
        """
        self.assert_examples({
            u'Garrett': u'가헤트',
            u'Barroso': u'바호주',
            u'Mattoso': u'마토주',
            u'Toress': u'토레스',
        })

    def test_13rd(self):
        """제13항
        o는 ‘오'로 적되, 어말이나 -os의 o는 ‘우'로 적는다.
        """
        self.assert_examples({
            u'Nobre': u'노브르',
            u'Antonio': u'안토니우',
            u'Melo': u'멜루',
            u'Saramago': u'사라마구',
            u'Passos': u'파수스',
            u'Lagos': u'라구스',
        })

    def test_14th(self):
        """제14항
        e는 ‘에'로 적되, 어두 무강세 음절에서는 ‘이'로 적는다. 어말에서는
        ‘으'로 적는다.
        """
        self.assert_examples({
            u'Montemayor': u'몬테마요르',
            u'Estremoz': u'이스트레모스',
            u'Chifre': u'시프르',
            u'de': u'드',
        })

    def test_15th(self):
        """제15항: -es
        1. p, b, m, f, v 다음에 오는 어말 -es는 ‘-에스'로 적는다.
        2. 그 밖의 어말 -es는 ‘-으스'로 적는다.
        """
        self.assert_examples({
            u'Lopes': u'로페스',
            u'Gomes': u'고메스',
            u'Neves': u'네베스',
            u'Chaves': u'샤베스',
            u'Soares': u'소아르스',
            u'Pires': u'피르스',
        })
########NEW FILE########
__FILENAME__ = por_br
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.por.br import BrazilianPortuguese


class BrazilianPortugueseTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0219.jsp """

    lang = BrazilianPortuguese()

    def test_3rd(self):
        """제3항
        d, t는 ㄷ, ㅌ으로 적는다. i 앞이나 어말 e 및 어말 -es 앞에서는
        ‘ㅈ, ㅊ'으로 적는다.
        """
        self.assert_examples({
            u'Diamantina': u'지아만치나',
            u'Alegrete': u'알레그레치',
            u'Montes': u'몬치스',
        })

    def test_5th(self):
        """제5항: l
        1. 어중의 l이 모음 앞에 오거나 모음이 따르지 않는 비음 앞에 오는
           경우에는 ‘?'로 적는다. 다만, 비음 뒤의 l은 모음 앞에 오더라도 ‘ㄹ'로
           적는다.
        2. 어말 또는 자음 앞의 l은 받침 ‘ㄹ'로 적는다. 다만, 브라질
           포르투갈어에서 자음 앞이나 어말에 오는 경우에는 ‘우'로 적되, 어말에
           -ul 이 오는 경우에는 ‘울'로 적는다.
        """
        self.assert_examples({
            u'Gilberto': u'지우베르투',
            u'Caracol': u'카라코우',
        })

    def test_14th(self):
        """제14항
        e는 ‘에'로 적되, 어두 무강세 음절과 어말에서는 ‘이'로 적는다.
        """
        self.assert_examples({
            u'Chifre': u'시프리',
            u'de': u'지',
        })

    def test_15th(self):
        """제15항: -es
        어말 -es는 ‘-이스'로 적는다.
        """
        self.assert_examples({
            u'Dorneles': u'도르넬리스',
            u'Correntes': u'코헨치스',
        })
########NEW FILE########
__FILENAME__ = ron
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.ron import Romanian


class RomanianTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0211.jsp """

    lang = Romanian()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0109.jsp """
        self.assert_examples({
            u'bibliotecă': u'비블리오테커',
            u'alb': u'알브',
            u'Cîntec': u'큰테크',
            u'Cine': u'치네',
            u'factură': u'팍투러',
            u'Moldova': u'몰도바',
            u'Brad': u'브라드',
            u'Focşani': u'폭샤니',
            u'Cartof': u'카르토프',
            u'Galaţi': u'갈라치',
            u'Gigel': u'지젤',
            u'hering': u'헤린그',
            u'haţeg': u'하체그',
            u'duh': u'두흐',
            u'Jiu': u'지우',
            u'Cluj': u'클루지',
            u'kilogram': u'킬로그람',
            u'bibliotecă': u'비블리오테커',
            u'hotel': u'호텔',
            u'Maramureş': u'마라무레슈',
            u'Avram': u'아브람',
            u'Nucet': u'누체트',
            u'Bran': u'브란',
            u'pumn': u'품느',
            u'pianist': u'피아니스트',
            u'septembrie': u'셉템브리에',
            u'cap': u'카프',
            u'radio': u'라디오',
            u'dor': u'도르',
            u'Sibiu': u'시비우',
            u'pas': u'파스',
            u'şag': u'샤그',
            u'Mureş': u'무레슈',
            u'telefonist': u'텔레포니스트',
            u'bilet': u'빌레트',
            u'ţigară': u'치가러',
            u'braţ': u'브라츠',
            u'Victoria': u'빅토리아',
            u'Braşov': u'브라쇼브',
            u'taxi': u'탁시',
            u'examen': u'에그자멘',
            u'ziar': u'지아르',
            u'autobuz': u'아우토부즈',
            u'Cheia': u'케이아',
            u'Gheorghe': u'게오르게',
            u'Arad': u'아라드',
            u'Bacău': u'바커우',
            u'Elena': u'엘레나',
            u'pianist': u'피아니스트',
            u'Cîmpina': u'큼피나',
            u'România': u'로므니아',
            u'Oradea': u'오라데아',
            u'Nucet': u'누체트',
        })

    def test_1st(self):
        """제1항: c, p
        어말과 유성 자음 앞에서는 '으'를 붙여 적고, 무성 자음 앞에서는
        받침으로 적는다.
        """
        self.assert_examples({
            u'cap': u'카프',
            u'Cîntec': u'큰테크',
            u'factură': u'팍투러',
            u'septembrie': u'셉템브리에',
        })

    def test_2nd(self):
        """제2항: c, g
        c, g는 e, i 앞에서는 각각 'ㅊ', 'ㅈ'으로, 그 밖의 모음 앞에서는 'ㅋ',
        'ㄱ'으로 적는다.
        """
        self.assert_examples({
            u'cap': u'카프',
            u'centru': u'첸트루',
            u'Galaţi': u'갈라치',
            u'Gigel': u'지젤',
        })

    def test_3rd(self):
        """제3항: l
        어중의 l이 모음 앞에 올 때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'clei': u'클레이',
        })

    def test_4th(self):
        """제4항: n
        n이 어말에서 m 뒤에 올 때는 '으'를 붙여 적는다.
        """
        self.assert_examples({
            u'lemn': u'렘느',
            u'pumn': u'품느',
        })

    def test_5th(self):
        """제5항: e
        e는 '에'로 적되, 인칭 대명사 및 동사 este, era 등의 어두 모음 e는
        '예'로 적는다.
        """
        self.assert_examples({
            u'Emil': u'에밀',
            u'eu': u'예우',
            u'el': u'옐',
            u'este': u'예스테',
            u'era': u'예라',
        })

    def test_etc(self):
        self.assert_examples({
            u'Sturdza': u'스투르자',
            u'Theodor': u'테오도르',
        })
########NEW FILE########
__FILENAME__ = rus
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.rus import Russian


class RussianTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0221.jsp """

    lang = Russian()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'Премьер': u'프레미예르',
            u'Авксесия': u'압크세시야',
        })

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0119.jsp """
        self.assert_examples({
            u'Болотов': u'볼로토프',
            u'Бобров': u'보브로프',
            u'Курбский': u'쿠릅스키',
            u'Глеб': u'글레프',
            u'Гончаров': u'곤차로프',
            u'Манечка': u'마네치카',
            u'Якубович': u'야쿠보비치',
            u'Дмитрий': u'드미트리',
            u'Бенедиктов': u'베네딕토프',
            u'Находка': u'나홋카',
            u'Восход': u'보스호트',
            u'Фёдор': u'표도르',
            u'Ефремов': u'예프레모프',
            u'Иосиф': u'이오시프',
            u'Гоголь': u'고골',
            u'Мусоргский': u'무소륵스키',
            u'Богдан': u'보그단',
            u'Андарбаг': u'안다르바크',
            u'Хабаровск': u'하바롭스크',
            u'Ахматова': u'아흐마토바',
            u'Ойстрах': u'오이스트라흐',
            u'Калмык': u'칼미크',
            u'Аксаков': u'악사코프',
            u'Квас': u'크바스',
            u'Владивосток': u'블라디보스토크',
            u'Ленин': u'레닌',
            u'Николай': u'니콜라이',
            u'Крылов': u'크릴로프',
            u'Павел': u'파벨',
            u'Михаийл': u'미하일',
            u'Максим': u'막심',
            u'Мценск': u'므첸스크',
            u'Надя': u'나댜',
            u'Стефан': u'스테판',
            u'Пётр': u'표트르',
            u'Ростопчиня': u'로스톱치냐',
            u'Псков': u'프스코프',
            u'Майкоп': u'마이코프',
            u'Рыбинск': u'리빈스크',
            u'Лермонтов': u'레르몬토프',
            u'Артём': u'아르툠',
            u'Василий': u'바실리',
            u'Стефан': u'스테판',
            u'Борис': u'보리스',
            u'Шелгунов': u'셸구노프',
            u'Шишков': u'시시코프',
            u'Щербаков': u'셰르바코프',
            u'Щирец': u'시레츠',
            u'борщ': u'보르시',
            u'Татьяна': u'타티야나',
            u'Хватков': u'흐밧코프',
            u'Тверь': u'트베리',
            u'Бурят': u'부랴트',
            u'Гатчина': u'가치나',
            u'Тютчев': u'튜체프',
            u'Капица': u'카피차',
            u'Цветаева': u'츠베타예바',
            u'Брятск': u'브랴츠크',
            u'Якутск': u'야쿠츠크',
            u'Веревкин': u'베렙킨',
            u'Достоевский': u'도스토옙스키',
            u'Владивосток': u'블라디보스토크',
            u'Марков': u'마르코프',
            u'Зайчев': u'자이체프',
            u'Кузнецов': u'쿠즈네초프',
            u'Агрыз': u'아그리스',
            u'Жадовская': u'자돕스카야',
            u'Жданов': u'즈다노프',
            u'Лужков': u'루시코프',
            u'Кебеж': u'케베시',
            u'Юрий': u'유리',
            u'Андрей': u'안드레이',
            u'Белый': u'벨리',
            u'Аксаков': u'악사코프',
            u'Абакан': u'아바칸',
            u'Петров': u'페트로프',
            u'Евгений': u'예브게니',
            u'Алексеев': u'알렉세예프',
            u'Эртель': u'예르텔',
            u'Иванов': u'이바노프',
            u'Иосиф': u'이오시프',
            u'Хомяков': u'호먀코프',
            u'Ока': u'오카',
            u'Ушаков': u'우샤코프',
            u'Сарапул': u'사라풀',
            u'Салтыков': u'살티코프',
            u'Кыра': u'키라',
            u'Белый': u'벨리',
            u'Ясинский': u'야신스키',
            u'Адыгея': u'아디게야',
            u'Соловьёв': u'솔로비요프',
            u'Артём': u'아르툠',
            u'Юрий': u'유리',
            u'Юрга': u'유르가',
        })

    def test_1st(self):
        """제1항: p(п), t(т), k(к), b(б), d(д), g(г), f(ф), v(в)
        파열음과 마찰음 f(ф)·v(в)는 무성 자음 앞에서는 앞 음절의 받침으로
        적고, 유성 자음 앞에서는 ‘으'를 붙여 적는다.
        """
        self.assert_examples({
            u'Садко': u'삿코',
            u'Агрыз': u'아그리스',
            u'Акбаур': u'아크바우르',
            u'Ростопчиня': u'로스톱치냐',
            u'Акмеизм': u'아크메이즘',
            u'Рубцовск': u'룹촙스크',
            u'Брятск': u'브랴츠크',
            u'Лопатка': u'로팟카',
            u'Ефремов': u'예프레모프',
            u'Достоевский': u'도스토옙스키',
        })

    def test_2nd(self):
        """제2항: z(з), zh(ж)
        z(з)와 zh(ж)는 유성 자음 앞에서는 ‘즈'로 적고 무성 자음 앞에서는
        각각 ‘스, 시'로 적는다.
        """
        self.assert_examples({
            u'Назрань': u'나즈란',
        #    u'Нижний Тагил': u'니즈니타길',
            u'Нижний Тагил': u'니즈니 타길',
            u'Острогожск': u'오스트로고시스크',
            u'Лужков': u'루시코프',
        })

    def test_3rd(self):
        """제3항
        지명의 -grad(град)와 -gorod(город)는 관용을 살려 각각 ‘-그라드',
        ‘-고로드'로 표기한다.
        """
        self.assert_examples({
            u'Волгоград': u'볼고그라드',
            u'Калининград': u'칼리닌그라드',
            u'Славгород': u'슬라브고로드',
        })

    def test_4th(self):
        """제4항
        자음 앞의 -ds(дс)-는 ‘츠'로 적는다.
        """
        self.assert_examples({
            u'Петрозаводск': u'페트로자보츠크',
            u'Вернадский': u'베르나츠키',
        })

    def test_5th(self):
        """제5항
        어말 또는 자음 앞의 l(л)은 받침 ‘ㄹ'로 적고, 어중의 l이 모음 앞에
        올 때에는 ‘ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'Павел': u'파벨',
            u'Николаевич': u'니콜라예비치',
            u'Земля': u'제믈랴',
            u'Цимлянск': u'치믈랸스크',
        })

    def test_6th(self):
        """제6항
        l'(ль), m(м)이 어두 자음 앞에 오는 경우에는 각각 ‘리', ‘므'로 적는다.
        """
        self.assert_examples({
            u'Льбовна': u'리보브나',
            u'Мценск': u'므첸스크',
        })

    def test_7th(self):
        """제7항
        같은 자음이 겹치는 경우에는 겹치지 않은 경우와 같이 적는다. 다만,
        mm(мм), nn(нн)은 모음 앞에서 ‘ㅁㅁ', ‘ㄴㄴ'으로 적는다.
        """
        self.assert_examples({
            u'Гиппиус': u'기피우스',
            u'Аввакум': u'아바쿰',
            u'Одесса': u'오데사',
            u'Акколь': u'아콜',
            u'Соллогуб': u'솔로구프',
            u'Анна': u'안나',
            u'Гамма': u'감마',
        })

    def test_8th(self):
        """제8항
        e(е, э)는 자음 뒤에서는 ‘에'로 적고, 그 외의 경우에는 ‘예'로 적는다.
        """
        self.assert_examples({
            u'Алексей': u'알렉세이',
            u'Егвекинот': u'예그베키노트',
        })

    def test_9th(self):
        """제9항: 연음 부호 '(ь)
        연음 부호 '(ь)은 ‘이'로 적는다. 다만 l', m', n'(ль, мь, нь)이 자음
        앞이나 어말에 오는 경우에는 적지 않는다.
        """
        self.assert_examples({
            u'Льбовна': u'리보브나',
            u'Игорь': u'이고리',
            u'Илья': u'일리야',
            u'Дьяково': u'디야코보',
            u'Ольга': u'올가',
        #    u'Пермь': u'페름',
            u'Рязань': u'랴잔',
            u'Гоголь': u'고골',
        })

    def test_10th(self):
        """제10항
        dz(дз), dzh(дж)는 각각 z, zh와 같이 적는다.
        """
        self.assert_examples({
            u'Дзержинский': u'제르진스키',
            u'Таджикистан': u'타지키스탄',
        })
########NEW FILE########
__FILENAME__ = slk
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.slk import Slovak


class SlovakTestCase(HangulizeTestCase):

    lang = Slovak()

    def test_people(self):
        self.assert_examples({
            u'Ján Bahýľ': u'얀 바힐',
            u'Štefan Banič': u'슈테판 바니치',
            u'Anton Bernolák': u'안톤 베르놀라크',
            u'Peter Bondra': u'페테르 본드라',
            u'Zdeno Chára': u'즈데노 하라',
            u'Dominika Cibulková': u'도미니카 치불코바',
            u'Ján Čarnogurský': u'얀 차르노구르스키',
            u'Štefan Marko Daxner': u'슈테판 마르코 닥스네르',
            u'Pavol Demitra': u'파볼 데미트라',
            u'Alexander Dubček': u'알렉산데르 둡체크',
            u'Mikuláš Dzurinda': u'미쿨라시 주린다',
            u'Marián Gáborík': u'마리안 가보리크',
            u'Marek Hamšík': u'마레크 함시크',
            u'Daniela Hantuchová': u'다니엘라 한투호바',
            u'Andrej Hlinka': u'안드레이 흘린카',
            u'Milan Hodža': u'밀란 호자',
            u'Marian Hossa': u'마리안 호사',
            u'Dominik Hrbatý': u'도미니크 흐르바티',
            u'Pavol Hurajt': u'파볼 후라이트',
            u'Jozef Miloslav Hurban': u'요제프 밀로슬라우 후르반',
            u'Gustáv Husák': u'구스타우 후사크',
            u'Hviezdoslav': u'흐비에즈도슬라우',
            u'Dionýz Ilkovič': u'디오니스 일코비치',
            u'Elena Kaliská': u'엘레나 칼리스카',
            u'Michaela Kocianová': u'미하엘라 코치아노바',
            u'Karol Kučera': u'카롤 쿠체라',
            u'Anastasiya Kuzmina': u'아나스타시야 쿠즈미나',
            u'Michal Martikán': u'미할 마르티칸',
            u'Janko Matúška': u'얀코 마투슈카',
            u'Vladimír Mečiar': u'블라디미르 메치아르',
            u'Martina Moravcová': u'마르티나 모라우초바',
            u'Jozef Murgaš': u'요제프 무르가시',
            u'Natália Prekopová': u'나탈리아 프레코포바',
            u'Jozef Roháček': u'요제프 로하체크',
            u'Magdaléna Rybáriková': u'마그달레나 리바리코바',
            u'Zuzana Sekerová': u'주자나 세케로바',
            u'Aurel Stodola': u'아우렐 스토돌라',
            u'Eugen Suchoň': u'에우겐 수혼',
            u'Martin Škrtel': u'마르틴 슈크르텔',
            u'Milan Rastislav Štefánik': u'밀란 라스티슬라우 슈테파니크',
            u'Zuzana Štefečeková': u'주자나 슈테페체코바',
            u'Peter Šťastný': u'페테르 슈탸스트니',
            u'Ľudovít Štúr': u'류도비트 슈투르',
            u'Jozef Tiso': u'요제프 티소',
            u'Vavrinec': u'바우리네츠',
            u'Rudolf Vrba': u'루돌프 브르바',
            u'Vladimír Weiss': u'블라디미르 베이스',
        })

    def test_places(self):
        self.assert_examples({
            u'Banská Bystrica': u'반스카 비스트리차',
            u'Bardejov': u'바르데요우',
            u'Bratislava': u'브라티슬라바',
            u'Komárno': u'코마르노',
            u'Košice': u'코시체',
            u'Manínska tiesňava': u'마닌스카 티에스냐바',
            u'Martin': u'마르틴',
            u'Michalovce': u'미할로우체',
            u'Nitra': u'니트라',
            u'Poprad': u'포프라트',
            u'Považská': u'포바슈스카',
            u'Prešov': u'프레쇼우',
            u'Rožňava': u'로주냐바',
            u'Slavín': u'슬라빈',
            u'Spiš': u'스피시',
            u'Trenčín': u'트렌친',
            u'Trnava': u'트르나바',
            u'Váh': u'바흐',
            u'Vlkolínec': u'블콜리네츠',
            u'Vydrica': u'비드리차',
            u'Zvolen': u'즈볼렌',
            u'Žilina': u'질리나',
            u'Žehra': u'제흐라',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'deväť': u'데베티',
            u'jahôd': u'야후오트',
            u'mäkčeň': u'멕첸',
            u'pätnásť': u'페트나스티',
        })
########NEW FILE########
__FILENAME__ = slv
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.slv import Slovene


class SloveneTestCase(HangulizeTestCase):

    lang = Slovene()

    def test_people(self):
        self.assert_examples({
            u'Milenko Ačimovič': u'밀렌코 아치모비치',
            u'Anton Aškerc': u'안톤 아슈케르츠',
            u'Armin Bačinovič': u'아르민 바치노비치',
            u'Janez Bleiweis': u'야네스 블레이베이스',
            u'Jože Brumen': u'요제 브루멘',
            u'Ivan Cankar': u'이반 찬카르',
            u'Sebastjan Cimirotič': u'세바스티안 치미로티치',
            u'Zlatko Dedič': u'즐라트코 데디치',
            u'Janez Drnovšek': u'야네스 드르노우셰크',
            u'Gregor Fučka': u'그레고르 푸치카',
            u'Jakob Petelin Gallus': u'야코프 페텔린 갈루스',
            u'Samir Handanovič': u'사미르 한다노비치',
            u'Matevž Irt': u'마테우시 이르트',
            u'Željko Ivanek': u'젤코 이바네크',
            u'Rihard Jakopič': u'리하르트 야코피치',
            u'Janez Janša': u'야네스 얀샤',
            u'Bojan Jokić': u'보얀 요키치',
            u'Srečko Katanec': u'스레치코 카타네츠',
            u'Matjaž Kek': u'마티아시 케크',
            u'Ivana Kobilca': u'이바나 코빌차',
            u'Oskar Kogoj': u'오스카르 코고이',
            u'Anže Kopitar': u'안제 코피타르',
            u'Robert Koren': u'로베르트 코렌',
            u'Milan Kučan': u'밀란 쿠찬',
            u'Fran Levstik': u'프란 레우스티크',
            u'Rudolf Maister': u'루돌프 마이스테르',
            u'Željko Milinovič': u'젤코 밀리노비치',
            u'Radoslav Nesterovič': u'라도슬라우 네스테로비치',
            u'Milivoje Novakovič': u'밀리보예 노바코비치',
            u'Borut Pahor': u'보루트 파호르',
            u'Lojze Peterle': u'로이제 페테를레',
            u'Jože Plečnik': u'요제 플레치니크',
            u'Bojan Prašnikar': u'보얀 프라슈니카르',
            u'Friderik Pregl': u'프리데리크 프레글',
            u'France Prešeren': u'프란체 프레셰렌',
            u'Uroš Slokar': u'우로시 슬로카르',
            u'Anton Martin Slomšek': u'안톤 마르틴 슬롬셰크',
            u'Katarina Srebotnik': u'카타리나 스레보트니크',
            u'Leon Štukelj': u'레온 슈투켈',
            u'Dubravka Tomšič': u'두브라우카 톰시치',
            u'Primož Trubar': u'프리모시 트루바르',
            u'Danilo Türk': u'다닐로 튀르크',
            u'Sašo Udovič': u'사쇼 우도비치',
            u'Beno Udrih': u'베노 우드리흐',
            u'Janez Vajkard Valvasor': u'야네스 바이카르트 발바소르',
            u'Jurij Vega': u'유리 베가',
            u'Zdenko Verdenik': u'즈덴코 베르데니크',
            u'Saša Vujačič': u'사샤 부야치치',
            u'Zlatko Zahovič': u'즐라트코 자호비치',
            u'Slavoj Žižek': u'슬라보이 지제크',
        })

    def test_places(self):
        self.assert_examples({
            u'Bled': u'블레트',
            u'Bohinj': u'보힌',
            u'Celje': u'첼리에',
            u'Domžale': u'돔잘레',
            u'Izola': u'이졸라',
            u'Jesenice': u'예세니체',
            u'Kamnik': u'캄니크',
            u'Koper': u'코페르',
            u'Kranj': u'크란',
            u'Kras': u'크라스',
            u'Ljubljana': u'류블랴나',
            u'Maribor': u'마리보르',
            u'Murska Sobota': u'무르스카 소보타',
            u'Nova Gorica': u'노바 고리차',
            u'Novo mesto': u'노보 메스토',
            u'Piran': u'피란',
            u'Pivka': u'피우카',
            u'Ptuj': u'프투이',
            u'Slovenija': u'슬로베니야',
            u'Škofja Loka': u'슈코피아 로카',
            u'Trbovlje': u'트르보울리에',
            u'Triglav': u'트리글라우',
            u'Velenje': u'벨레니에',
        })

########NEW FILE########
__FILENAME__ = spa
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.spa import Spanish


class SpanishTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0204.jsp """

    lang = Spanish()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0102.jsp """
        self.assert_examples({
            u'biz': u'비스',
            u'blandon': u'블란돈',
            u'braceo': u'브라세오',
            u'colcren': u'콜크렌',
            u'Cecilia': u'세실리아',
            u'coccion': u'콕시온',
            u'bistec': u'비스텍',
            u'dictado': u'딕타도',
            u'chicharra': u'치차라',
            u'felicidad': u'펠리시다드',
            u'fuga': u'푸가',
            u'fran': u'프란',
            u'ganga': u'강가',
            u'geologia': u'헤올로히아',
            u'yungla': u'융글라',
            u'hipo': u'이포',
            u'quehacer': u'케아세르',
            u'jueves': u'후에베스',
            u'reloj': u'렐로',
            u'kapok': u'카포크',
            u'lacrar': u'라크라르',
            u'Lulio': u'룰리오',
            u'ocal': u'오칼',
            u'llama': u'야마',
            u'lluvia': u'유비아',
            u'membrete': u'멤브레테',
            u'noche': u'노체',
            u'flan': u'플란',
            u'ñoñez': u'뇨녜스',
            u'mañana': u'마냐나',
            u'pepsina': u'펩시나',
            u'plantón': u'플란톤',
            u'quisquilla': u'키스키야',
            u'rascador': u'라스카도르',
            u'sastreria': u'사스트레리아',
            u'tetraetro': u'테트라에트로',
            u'viudedad': u'비우데다드',
            u'xenón': u'세논',
            u'laxante': u'락산테',
            u'yuxta': u'육스타',
            u'zagal': u'사갈',
            u'liquidez': u'리키데스',
            u'walkirias': u'왈키리아스',
            u'yungla': u'융글라',
            u'braceo': u'브라세오',
            u'reloj': u'렐로',
            u'Lulio': u'룰리오',
            u'ocal': u'오칼',
            u'viudedad': u'비우데다드',
        })

    def test_1st(self):
        """제1항: gu, qu
        gu, qu는 i, e 앞에서는 각각 'ㄱ, ㅋ'으로 적고, o 앞에서는 '구, 쿠'로
        적는다. 다만, a 앞에서는 그 a와 합쳐 '과, 콰'로 적는다.
        """
        self.assert_examples({
            u'guerra': u'게라',
            u'queso': u'케소',
            u'Guipuzcoa': u'기푸스코아',
            u'quisquilla': u'키스키야',
            u'antiguo': u'안티구오',
            u'Quorem': u'쿠오렘',
            u'Nicaragua': u'니카라과',
            u'Quarai': u'콰라이',
        })

    def test_2nd(self):
        """제2항
        같은 자음이 겹치는 경우에는 겹치지 않은 경우와 같이 적는다. 다만,
        -cc-는 'ㄱㅅ'으로 적는다.
        """
        self.assert_examples({
            u'carrera': u'카레라',
            u'carreterra': u'카레테라',
            u'accion': u'악시온',
        })

    def test_3rd(self):
        """제3항: c, g
        c와 g 다음에 모음 e와 i가 올 때에는 c는 'ㅅ'으로, g는 'ㅎ'으로 적고,
        그 외는 'ㅋ'과 'ㄱ'으로 적는다.
        """
        self.assert_examples({
            u'Cecilia': u'세실리아',
            u'cifra': u'시프라',
            u'georgico': u'헤오르히코',
            u'giganta': u'히간타',
            u'coquito': u'코키토',
            u'gato': u'가토',
        })

    def test_4th(self):
        """제4항: x
        x가 모음 앞에 오되 어두일 때에는 'ㅅ'으로 적고, 어중일 때에는
        'ㄱㅅ'으로 적는다.
        """
        self.assert_examples({
            u'xilofono': u'실로포노',
            u'laxante': u'락산테',
        })

    def test_5th(self):
        """제5항: l
        어말 또는 자음 앞의 l은 받침 'ㄹ'로 적고, 어중의 1이 모음 앞에 올
        때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'ocal': u'오칼',
            u'colcren': u'콜크렌',
            u'blandon': u'블란돈',
            u'Cecilia': u'세실리아',
        })

    def test_6th(self):
        """제6항: nc, ng
        c와 g 앞에 오는 n은 받침 'ㅇ'으로 적는다.
        """
        self.assert_examples({
            u'blanco': u'블랑코',
            u'yungla': u'융글라',
        })

    def test_hangulize(self):
        self.assert_examples({
            u'ñoñez': u'뇨녜스',
            u'güerrero': u'궤레로',
            u'Güicho': u'귀초',
            u'Gamiño': u'가미뇨',
            u'Ángeles': u'앙헬레스',
            u'José Ortega y Gasset': u'호세 오르테가 이 가세트',
        })
########NEW FILE########
__FILENAME__ = sqi
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.sqi import Albanian


class AlbanianTestCase(HangulizeTestCase):

    lang = Albanian()

    def test_people(self):
        self.assert_examples({
            u'Ramiz Alia': u'라미즈 알리아',
            u'Valon Behrami': u'발론 베흐라미',
            u'Sali Berisha': u'살리 베리샤',
            u'Agnes Gonxha Bojaxhiu': u'아그네스 곤자 보야지우',
            u'Bujar Bukoshi': u'부야르 부코시',
            u'Gjon Buzuku': u'존 부주쿠',
            u'Gjergj Fishta': u'제르지 피슈타',
            u'Lorik Cana': u'로리크 차나',
            u'Eqrem Çabej': u'에치렘 차베이',
            u'Adil Çarçani': u'아딜 차르차니',
            u'Agim Çeku': u'아김 체쿠',
            u'Emina Çunmulaj': u'에미나 춘물라이',
            u'Leka Dukagjini': u'레카 두카지니',
            u'Eliza Dushku': u'엘리자 두슈쿠',
            u'Mit\'hat Frashëri': u'미트하트 프라셔리',
            u'Simon Gjoni': u'시몬 조니',
            u'Luigj Gurakuqi': u'루이지 구라쿠치',
            u'Enver Hoxha': u'엔베르 호자',
            u'Ismail Kadare': u'이스마일 카다레',
            u'Dhimitër Kamarda': u'디미터르 카마르다',
            u'Ibrahim Kodra': u'이브라힘 코드라',
            u'Jakup Krasniqi': u'야쿠프 크라스니치',
            u'Luan Krasniqi': u'루안 크라스니치',
            u'Shefki Kuqi': u'셰프키 쿠치',
            u'Vasil Laçi': u'바실 라치',
            u'Riza Lushta': u'리자 루슈타',
            u'Mirela Manjani': u'미렐라 마냐니',
            u'Gjeke Marinaj': u'제케 마리나이',
            u'Rexhep Meidani': u'레제프 메이다니',
            u'Alfred Moisiu': u'알프레드 모이시우',
            u'Fatos Nano': u'파토스 나노',
            u'Behxhet Pacolli': u'베흐제트 파촐리',
            u'Adrian Paçi': u'아드리안 파치',
            u'Rexhep Qosja': u'레제프 초시아',
            u'Ibrahim Rugova': u'이브라힘 루고바',
            u'Fatmir Sejdiu': u'파트미르 세이디우',
            u'Klodiana Shala': u'클로디아나 샬라',
            u'Artim Shaqiri': u'아르팀 샤치리',
            u'Xherdan Shaqiri': u'제르단 샤치리',
            u'Gjergj Kastriot Skanderbeg': u'제르지 카스트리오트 스칸데르베그',
            u'Hashim Thaçi': u'하심 사치',
            u'Bamir Topi': u'바미르 토피',
            u'Pashko Vasa': u'파슈코 바사',
        })

    def test_places(self):
        self.assert_examples({
            u'Berati': u'베라티',
            u'Butrinti': u'부트린티',
            u'Durrësi': u'두러시',
            u'Elbasani': u'엘바사니',
            u'Fieri': u'피에리',
            u'Gjakova': u'자코바',
            u'Gjilani': u'질라니',
            u'Gjirokastra': u'지로카스트라',
            u'Kaçaniku': u'카차니쿠',
            u'Kavaja': u'카바야',
            u'Korça': u'코르차',
            u'Kruja': u'크루야',
            u'Lezha': u'레자',
            u'Lushnja': u'루슈냐',
            u'Mitrovica': u'미트로비차',
            u'Peja': u'페야',
            u'Pogradeci': u'포그라데치',
            u'Prishtina': u'프리슈티나',
            u'Prizreni': u'프리즈레니',
            u'Saranda': u'사란다',
            u'Shkodra': u'슈코드라',
            u'Shkumbini': u'슈쿰비니',
            u'Shqipëria': u'슈치퍼리아',
            u'Tirana': u'티라나',
            u'Ulpiana': u'울피아나',
            u'Vlora': u'블로라',
        })
########NEW FILE########
__FILENAME__ = swe
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.swe import Swedish


class SwedishTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0213.jsp """

    lang = Swedish()

    def test_basic(self):
        """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0111.jsp """
        self.assert_examples({
            u'bal': u'발',
            u'snabbt': u'스납트',
            u'Jacob': u'야코브',
            u'Carlsson': u'칼손',
            u'Celsius': u'셀시우스',
            u'Ericson': u'에릭손',
            u'charm': u'샤름',
            u'och': u'오크',
            u'dag': u'다그',
            u'dricka': u'드리카',
            u'Halmstad': u'할름스타드',
            u'Djurgården': u'유르고르덴',
            u'adjö': u'아예',
            u'Sundsvall': u'순스발',
            u'Falun': u'팔룬',
            u'luft': u'루프트',
            u'Gustav': u'구스타브',
            u'helgon': u'헬곤',
            u'Göteborg': u'예테보리',
            u'Geijer': u'예이예르',
            u'Gislaved': u'이슬라베드',
            u'älg': u'엘리',
            u'Strindberg': u'스트린드베리',
            u'Borg': u'보리',
            u'Magnus': u'망누스',
            u'Ragnar': u'랑나르',
            u'Agnes': u'앙네스',
            u'högst': u'획스트',
            u'Grönberg': u'그뢴베리',
            u'Gjerstad': u'예르스타드',
            u'Gjörwell': u'예르벨',
            u'Hälsingborg': u'헬싱보리',
            u'hyra': u'휘라',
            u'Dahl': u'달',
            u'Hjälmaren': u'옐마렌',
            u'Hjalmar': u'얄마르',
            u'Hjort': u'요르트',
            u'Jansson': u'얀손',
            u'Jönköping': u'옌셰핑',
            u'Johansson': u'요한손',
            u'börja': u'뵈리아',
            u'fjäril': u'피에릴',
            u'mjuk': u'미우크',
            u'mjöl': u'미엘',
            u'Karl': u'칼',
            u'Kock': u'코크',
            u'Kungsholm': u'쿵스홀름',
            u'Kerstin': u'셰르스틴',
            u'Norrköping': u'노르셰핑',
            u'Lysekil': u'뤼세실',
            u'oktober': u'옥토베르',
            u'Fredrik': u'프레드리크',
            u'kniv': u'크니브',
            u'vacker': u'바케르',
            u'Stockholm': u'스톡홀름',
            u'bock': u'보크',
            u'Kjell': u'셸',
            u'Kjula': u'슐라',
            u'Linköping': u'린셰핑',
            u'tala': u'탈라',
            u'tal': u'탈',
            u'Ljusnan': u'유스난',
            u'Södertälje': u'쇠데르텔리에',
            u'detalj': u'데탈리',
            u'Malmö': u'말뫼',
            u'samtal': u'삼탈',
            u'hummer': u'훔메르',
            u'Norrköping': u'노르셰핑',
            u'Vänern': u'베네른',
            u'land': u'란드',
            u'Karlshamn': u'칼스함',
            u'Borlänge': u'볼렝에',
            u'kung': u'쿵',
            u'lång': u'롱',
            u'anka': u'앙카',
            u'Sankt': u'상트',
            u'bank': u'방크',
            u'Piteå': u'피테오',
            u'knappt': u'크납트',
            u'Uppsala': u'웁살라',
            u'kamp': u'캄프',
            u'Malmqvist': u'말름크비스트',
            u'Lindqvist': u'린드크비스트',
            u'röd': u'뢰드',
            u'Wilander': u'빌란데르',
            u'Björk': u'비에르크',
            u'Erlander': u'엘란데르',
            u'Karlgren': u'칼그렌',
            u'Jarl': u'얄',
            u'sommar': u'솜마르',
            u'Storvik': u'스토르비크',
            u'dans': u'단스',
            u'Schack': u'샤크',
            u'Schein': u'셰인',
            u'revansch': u'레반슈',
            u'Nässjö': u'네셰',
            u'sjukhem': u'슈크헴',
            u'Sjöberg': u'셰베리',
            u'Skoglund': u'스코글룬드',
            u'Skellefteå': u'셸레프테오',
            u'Skövde': u'셰브데',
            u'Skeppsholmen': u'솁스홀멘',
            u'Hammarskjöld': u'함마르셸드',
            u'Skjöldebrand': u'셸데브란드',
            u'Stjärneborg': u'셰르네보리',
            u'Oxenstjerna': u'옥센셰르나',
            u'Göta': u'예타',
            u'Botkyrka': u'봇쉬르카',
            u'Trelleborg': u'트렐레보리',
            u'båt': u'보트',
            u'Luther': u'루테르',
            u'Thunberg': u'툰베리',
            u'lektion': u'렉숀',
            u'station': u'스타숀',
            u'tjeck': u'셰크',
            u'Tjåkkå': u'쇼코',
            u'tjäna': u'셰나',
            u'tjugo': u'슈고',
            u'Sverige': u'스베리예',
            u'Wasa': u'바사',
            u'Swedenborg': u'스베덴보리',
            u'Eslöv': u'에슬뢰브',
            u'Axel': u'악셀',
            u'Alexander': u'알렉산데르',
            u'sex': u'섹스',
            u'Zachris': u'사크리스',
            u'zon': u'손',
            u'Lorenzo': u'로렌소',
            u'Kalix': u'칼릭스',
            u'Falun': u'팔룬',
            u'Alvesta': u'알베스타',
            u'Enköping': u'엔셰핑',
            u'Svealand': u'스베알란드',
            u'Mälaren': u'멜라렌',
            u'Vänern': u'베네른',
            u'Trollhättan': u'트롤헤탄',
            u'Idre': u'이드레',
            u'Kiruna': u'키루나',
            u'Åmål': u'오몰',
            u'Västerås': u'베스테로스',
            u'Småland': u'스몰란드',
            u'Boden': u'보덴',
            u'Stockholm': u'스톡홀름',
            u'Örebro': u'외레브로',
            u'Östersund': u'외스테르순드',
            u'Björn': u'비에른',
            u'Linköping': u'린셰핑',
            u'Umeå': u'우메오',
            u'Luleå': u'룰레오',
            u'Lund': u'룬드',
            u'Ystad': u'위스타드',
            u'Nynäshamn': u'뉘네스함',
            u'Visby': u'비스뷔',
        })

    def test_1st(self):
        """제1항
        1. b, g가 무성 자음 앞에 올 때에는 받침 'ㅂ, ㄱ'으로 적는다.
        2. k, ck, p, t는 무성 자음 앞에서 받침 'ㄱ, ㄱ, ㅂ, ㅅ'으로 적는다.
        """
        self.assert_examples({
            u'snabbt': u'스납트',
            u'högst': u'획스트',
            u'oktober': u'옥토베르',
            u'Stockholm': u'스톡홀름',
            u'Uppsala': u'웁살라',
            u'Botkyrka': u'봇쉬르카',
        })

    def test_2nd(self):
        """제2항: c는 'ㅋ'으로 적되, e, i, a, y, o 앞에서는 'ㅅ'으로 적는다."""
        self.assert_examples({
            u'campa': u'캄파',
            u'Celsius': u'셀시우스',
        })

    def test_3rd(self):
        """제3항: g
        1. 모음 앞의 g는 'ㄱ'으로 적되, e, i, a, y, o 앞에서는 '이'로 적고
           뒤따르는 모음과 합쳐 적는다.
        2. lg, rg의 g는 '이'로 적는다
        3. n 앞의 g는 'ㅇ'으로 적는다.
        4. 무성 자음 앞의 g는 받침 'ㄱ'으로 적는다.
        5. 그 밖의 자음 앞과 어말에서는 '그'로 적는다.
        """
        self.assert_examples({
            u'Gustav': u'구스타브',
            u'Göteborg': u'예테보리',
            u'älg': u'엘리',
            u'Borg': u'보리',
            u'Magnus': u'망누스',
            u'högst': u'획스트',
            u'Ludvig': u'루드비그',
            u'Greta': u'그레타',
        })

    def test_4th(self):
        """제4항: j는 자음과 모음 사이에 올 때에 앞의 자음과 합쳐서 적는다."""
        self.assert_examples({
            u'fjäril': u'피에릴',
            u'mjuk': u'미우크',
            u'kedja': u'셰디아',
            u'Björn': u'비에른',
        })

    def test_5th(self):
        """제5항
        k는 'ㅋ'으로 적되, e, i, a, y, o 앞에서는 '시'로 적고 뒤따르는 모음과
        합쳐 적는다.
        """
        self.assert_examples({
            u'Kungsholm': u'쿵스홀름',
            u'Norrköping': u'노르셰핑',
        })

    def test_6th(self):
        """제6항
        어말 또는 자음 앞의 l은 받침 'ㄹ'로 적고, 어중의 l이 모음 앞에 올
        때에는 'ㄹㄹ'로 적는다.
        """
        self.assert_examples({
            u'folk': u'폴크',
            u'tal': u'탈',
            u'tala': u'탈라',
        })

    def test_7th(self):
        """제7항
        어두의 lj는 '이'로 적되 뒤따르는 모음과 합쳐 적고, 어중의 lj는
        'ㄹ리'로 적는다.
        """
        self.assert_examples({
            u'Ljusnan': u'유스난',
            u'Södertälje': u'쇠데르텔리에',
        })

    def test_8th(self):
        """제8항
        n은 어말에서 m 다음에 올 때 적지 않는다.
        """
        self.assert_examples({
            u'Karlshamn': u'칼스함',
            u'namn': u'남',
        })

    def test_9th(self):
        """제9항
        nk는 자음 t 앞에서는 'ㅇ'으로, 그 밖의 경우에는 'ㅇ크'로 적는다.
        """
        self.assert_examples({
            u'anka': u'앙카',
            u'Sankt': u'상트',
            u'punkt': u'풍트',
            u'bank': u'방크',
        })

    def test_10th(self):
        """제10항
        sk는 '스ㅋ'으로 적되 e, i, a, y, o 앞에서는 '시'로 적고, 뒤따르는
        모음과 합쳐 적는다.
        """
        self.assert_examples({
            u'Skoglund': u'스코글룬드',
            u'skuldra': u'스쿨드라',
            u'skål': u'스콜',
            u'skörd': u'셰르드',
            u'skydda': u'쉬다',
        })

    def test_11st(self):
        """제11항
        o는 '외'로 적되 g, j, k, kj, lj, skj 다음에서는 '에'로 적고, 앞의
        '이' 또는 '시'와 합쳐서 적는다. 다만, jo 앞에 그 밖의 자음이 올 때에는
        j는 앞의 자음과 합쳐 적고, o는 '에'로 적는다.
        """
        self.assert_examples({
            u'Örebro': u'외레브로',
            u'Göta': u'예타',
            u'Jönköping': u'옌셰핑',
            u'Björn': u'비에른',
            u'Björling': u'비엘링',
            u'mjöl': u'미엘',
        })

    def test_12nd(self):
        """제12항
        같은 자음이 겹치는 경우에는 겹치지 않은 경우와 같이 적는다. 단, mm,
        nn은 모음 앞에서 'ㅁㅁ', 'ㄴㄴ'으로 적는다.
        """
        self.assert_examples({
            u'Kattegatt': u'카테가트',
            u'Norrköping': u'노르셰핑',
            u'Uppsala': u'웁살라',
            u'Bromma': u'브롬마',
            u'Dannemora': u'단네모라',
        })

    def test_people(self):
        self.assert_examples({
            u'Sankta Ragnhild': u'상타 랑힐드',
        })
########NEW FILE########
__FILENAME__ = tur
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.tur import Turkish


class TurkishTestCase(HangulizeTestCase):

    lang = Turkish()

    def test_people(self):
        self.assert_examples({
            u'Sait Faik Abasıyanık': u'사이트 파이크 아바스야느크',
            u'Ali Kuşçu': u'알리 쿠슈추',
            u'Hamit Altıntop': u'하미트 알튼토프',
            u'Mustafa Kemal Atatürk': u'무스타파 케말 아타튀르크',
            u'Garabet Amira Balyan': u'가라베트 아미라 발리안',
            u'Krikor Balyan': u'크리코르 발리안',
            u'Nigoğos Balyan': u'니고오스 발리안',
            u'Battani': u'바타니',
            u'Hüseyin Çağlayan': u'휘세인 찰라얀',
            u'Süleyman Çelebi': u'쉴레이만 첼레비',
            u'Rauf Denktaş': u'라우프 뎅크타슈',
            u'Bülent Ecevit': u'뷜렌트 에제비트',
            u'Ahmet Mithat Efendi': u'아흐메트 미타트 에펜디',
            u'Yunus Emre': u'유누스 엠레',
            u'Recep Tayyip Erdoğan': u'레제프 타이이프 에르도안',
            u'Sertab Erener': u'세르타브 에레네르',
            u'Tevfik Fikret': u'테브피크 피크레트',
            u'Ertuğrul Gazi': u'에르투룰 가지',
            u'Ziya Gökalp': u'지야 괴칼프',
            u'Abdullah Gül': u'아브둘라흐 귈',
            u'Şenol Güneş': u'셰놀 귀네슈',
            u'Reşat Nuri Güntekin': u'레샤트 누리 귄테킨',
            u'Ahmed Hâşim': u'아흐메드 하심',
            u'Nâzım Hikmet': u'나즘 히크메트',
            u'Nihat Kahveci': u'니하트 카흐베지',
            u'Yakup Kadri Karaosmanoğlu': u'야쿠프 카드리 카라오스마놀루',
            u'Nâmık Kemal': u'나므크 케말',
            u'Yaşar Kemal': u'야샤르 케말',
            u'Fazıl Küçük': u'파즐 퀴취크',
            u'İlhan Mansız': u'일한 만스즈',
            u'Nakkaş Osman': u'나카슈 오스만',
            u'Orhan Pamuk': u'오르한 파무크',
            u'Ajda Pekkan': u'아주다 페칸',
            u'Osman Hamdi Bey': u'오스만 함디 베이',
            u'Pir Sultan Abdal': u'피르 술탄 아브달',
            u'Rüştü Reçber': u'뤼슈튀 레치베르',
            u'Ziynet Sali': u'지네트 살리',
            u'Ömer Seyfettin': u'외메르 세이페틴',
            u'Kanuni Sultan Süleyman': u'카누니 술탄 쉴레이만',
            u'Tuncay Şanlı': u'툰자이 샨르',
            u'Âşık Veysel Şatıroğlu': u'아시으크 베이셀 샤트롤루',
            u'Mahzuni Şerif': u'마흐주니 셰리프',
            u'Hakan Şükür': u'하칸 쉬퀴르',
            u'Takiyüddin ibn Manıf': u'타키위딘 이븐 마느프',
            u'Tarkan Tevetoğlu': u'타르칸 테베톨루',
            u'Arda Turan': u'아르다 투란',
            u'Halit Ziya Uşaklıgil': u'할리트 지야 우샤클르길',
        })

    def test_places(self):
        self.assert_examples({
            u'Adana': u'아다나',
            u'Ağrı': u'아르',
            u'Ankara': u'앙카라',
            u'Antakya': u'안타키아',
            u'Antalya': u'안탈리아',
            u'Arykanda': u'아리칸다',
            u'Beşiktaş': u'베식타슈',
            u'Bursa': u'부르사',
            u'Çanakkale': u'차나칼레',
            u'Çatalhöyük': u'차탈회위크',
            u'Denizli': u'데니즐리',
            u'Divriği': u'디브리이',
            u'Dolmabahçe': u'돌마바흐체',
            u'Gaziantep': u'가지안테프',
            u'Hattuşaş': u'하투샤슈',
            u'İstanbul': u'이스탄불',
            u'İzmir': u'이즈미르',
            u'Kapadokya': u'카파도키아',
            u'Kayseri': u'카이세리',
            u'Konya': u'코니아',
            u'Mersin': u'메르신',
            u'Pamukkale': u'파무칼레',
            u'Patara': u'파타라',
            u'Safranbolu': u'사프란볼루',
            u'Selçuk': u'셀추크',
            u'Topkapı': u'톱카프',
            u'Trabzon': u'트라브존',
            u'Türkiye': u'튀르키예',
        })

########NEW FILE########
__FILENAME__ = ukr
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.ukr import Ukrainian


class UkrainianTestCase(HangulizeTestCase):

    lang = Ukrainian()

    def test_people(self):
        self.assert_examples({
            u'Олександр Алієв': u'올렉산드르 알리예우',
            u'Степан Бандера': u'스테판 반데라',
            u'Оксана Баюл': u'옥사나 바율',
            u'Катерина Білокур': u'카테리나 빌로쿠르',
            u'Олег Блохін': u'올레흐 블로힌',
            u'Альона Бондаренко': u'알료나 본다렌코',
            u'Катерина Бондаренко': u'카테리나 본다렌코',
            u'Сергій Бубка': u'세르히 부브카',
            u'Володимир Вернадський': u'볼로디미르 베르나즈키',
            u'Володимир Мономах': u'볼로디미르 모노마흐',
            u'Андрій Воронін': u'안드리 보로닌',
            u'Данило Галицький': u'다닐로 할리츠키',
            u'Олександр Довженко': u'올렉산드르 도우젠코',
            u'Михайло Грушевський': u'미하일로 흐루셰우스키',
            u'Віталій Кличко': u'비탈리 클리치코',
            u'Володимир Кличко': u'볼로디미르 클리치코',
            u'Яна Клочкова': u'야나 클로치코바',
            u'Іван Кожедуб': u'이반 코제두브',
            u'Сергій Корольов': u'세르히 코롤료우',
            u'Леонід Кравчук': u'레오니드 크라우추크',
            u'Міла Куніс': u'밀라 쿠니스',
            u'Ольга Куриленко': u'올하 쿠릴렌코',
            u'Леонід Кучма': u'레오니드 쿠치마',
            u'Максиміліан Левчин': u'막시밀리안 레우친',
            u'Микола Лисенко': u'미콜라 리센코',
            u'Валерій Лобановський': u'발레리 로바노우스키',
            u'Левко Лук\'яненко': u'레우코 루키야넨코',
            u'Іван Мазепа': u'이반 마제파',
            u'Андрій Медведєв': u'안드리 메드베데우',
            u'Артем Мілевський': u'아르템 밀레우스키',
            u'Мстислав Володимирович': u'므스티슬라우 볼로디미로비치',
            u'Ярослав Мудрий': u'야로슬라우 무드리',
            u'Пилип Орлик': u'필리프 오를리크',
            u'Вадим Перельман': u'바딤 페렐만',
            u'Симон Петлюра': u'시몬 페틀류라',
            u'Віктор Пінчук': u'빅토르 핀추크',
            u'Сергій Ребров': u'세르히 레브로우',
            u'Климент Редько': u'클리멘트 레디코',
            u'Роман Мстиславич': u'로만 므스티슬라비치',
            u'Григорій Сковорода': u'흐리호리 스코보로다',
            u'Йосип Сліпий': u'요시프 슬리피',
            u'Василь Стус': u'바실 스투스',
            u'Борис Тарасюк': u'보리스 타라슈크',
            u'Олена Теліга': u'올레나 텔리하',
            u'Юлія Тимошенко': u'율리야 티모셴코',
            u'Анатолій Тимощук': u'아나톨리 티모슈크',
            u'Сергій Тігіпко': u'세르히 티힙코',
            u'Леся Українка': u'레샤 우크라인카',
            u'Іван Франко': u'이반 프란코',
            u'Богдан Хмельницький': u'보흐단 흐멜니츠키',
            u'Вячеслав Чорновіл': u'뱌체슬라우 초르노빌',
            u'Андрій Шевченко': u'안드리 셰우첸코',
            u'Тарас Шевченко': u'타라스 셰우첸코',
            u'Андрей Шептицький': u'안드레이 솁티츠키',
            u'Роман Шухевич': u'로만 슈헤비치',
            u'Віктор Ющенко': u'빅토르 유셴코',
            u'Віктор Янукович': u'빅토르 야누코비치',
        })

    def test_places(self):
        self.assert_examples({
            u'Ананьїв': u'아나니우',
            u'Асканія-Нова': u'아스카니야노바',
            u'Біла Церква': u'빌라 체르크바',
            u'Вінниця': u'빈니차',
            u'Горлівка': u'호를리우카',
            u'Дніпродзержинськ': u'드니프로제르진스크',
            u'Дніпропетровськ': u'드니프로페트로우스크',
            u'Донецьк': u'도네츠크',
            u'Євпаторія': u'예우파토리야',
            u'Єнакієве': u'예나키예베',
            u'Житомир': u'지토미르',
            u'Запоріжжя': u'자포리자',
            u'Івано-Франківськ': u'이바노프란키우스크',
            u'Кам\'янець-Подільський': u'카미야네츠포딜스키',
            u'Києво-Печерська лавра': u'키예보페체르스카 라우라',
            u'Київ': u'키이우',
            u'Кіровоград': u'키로보흐라드',
            u'Кременчук': u'크레멘추크',
            u'Кривий ріг': u'크리비 리흐',
            u'Луганськ': u'루한스크',
            u'Луцьк': u'루츠크',
            u'Львів': u'리비우',
            u'Макіївка': u'마키이우카',
            u'Маріуполь': u'마리우폴',
            u'Миколаїв': u'미콜라이우',
            u'Одеса': u'오데사',
            u'Полтава': u'폴타바',
            u'Рівне': u'리우네',
            u'Сєверодонецьк': u'세베로도네츠크',
            u'Слов\'янськ': u'슬로비얀스크',
            u'Суми': u'수미',
            u'Тернопіль': u'테르노필',
            u'Ужгород': u'우주호로드',
            u'Харків': u'하르키우',
            u'Херсон': u'헤르손',
            u'Черкаси': u'체르카시',
            u'Чернівці': u'체르니우치',
            u'Чернігів': u'체르니히우',
        })

    def test_miscellaneous(self):
        self.assert_examples({
            u'бандура': u'반두라',
            u'гетьман': u'헤티만',
            u'Голодомор': u'홀로도모르',
            u'гопак': u'호파크',
            u'кобзар': u'코브자르',
            u'козак': u'코자크',
            u'писанка': u'피산카',
        })

########NEW FILE########
__FILENAME__ = vie
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.vie import Vietnamese


class VietnameseTestCase(HangulizeTestCase):
    """ http://korean.go.kr/09_new/dic/rule/rule_foreign_0218.jsp """

    lang = Vietnamese()

    def test_1st(self):
        """제1항
        nh는 이어지는 모음과 합쳐서 한 음절로 적는다. 어말이나 자음 앞에서는
        받침 ‘ㄴ' 으로 적되, 그 앞의 모음이 a인 경우에는 a와 합쳐 ‘아인'으로
        적는다.
        """
        self.assert_examples({
        #    u'Nha Trang': u'냐짱',
        #    u'Hô Chi Minh': u'호찌민',
        #    u'Thanh Hoa': u'타인호아',
        #    u'Đông Khanh': u'동카인',
        })

    def test_2nd(self):
        """제2항
        qu는 이어지는 모음이 a일 경우에는 합쳐서 ‘꽈'로 적는다.
        """
        self.assert_examples({
            u'Quang': u'꽝',
        #    u'hat quan ho': u'핫꽌호',
            u'Quôc': u'꾸옥',
            u'Quyên': u'꾸옌',
        })

    def test_3rd(self):
        """제3항
        y는 뒤따르는 모음과 합쳐서 한 음절로 적는다.
        """
        self.assert_examples({
            u'yên': u'옌',
            u'Nguyên': u'응우옌',
        })

    def test_4th(self):
        """제4항
        어중의 l이 모음 앞에 올 때에는 ‘ㄹㄹ'로 적는다.
        다만, 인명의 성과 이름은 별개의 단어로 보아 이 규칙을 적용하지 않는다.
        """
        self.assert_examples({
        #    u'klông put': u'끌롱쁫',
            u'Pleiku': u'쁠래이꾸',
        #    u'Ha Long': u'할롱',
        #    u'My Lay': u'밀라이',
        })
########NEW FILE########
__FILENAME__ = wlm
# -*- coding: utf-8 -*-
from tests import HangulizeTestCase
from hangulize.langs.wlm import MiddleWelsh


class MiddleWelshTestCase(HangulizeTestCase):

    lang = MiddleWelsh()

    def test_examples_of_iceager(self):
        self.assert_examples({
            u'Mabinogion': u'마비노기온',
            u'Culhwch': u'퀼후흐',
            u'Olwen': u'올웬',
            u'Taliesin': u'탈리에신',
            u'Peredur': u'페레뒤르',
            u'Geraint': u'게라인트',
            u'Rhonabwy': u'흐로나부이',
            u'Rhiannon': u'흐리아논',
            u'Annwn': u'아눈',
            u'Pryderi': u'프러데리',
            u'Brânwen': u'브란웬',
            u'Llŷr': u'흘리르',
            u'Gwawl': u'과울',
            u'Beli Mawr': u'벨리 마우르',
            u'Gofannon': u'고바논',
            u'Gwynedd': u'귀네드',
            u'Arianrhod': u'아리안흐로드',
            u'Manawydan': u'마나위단',
            u'Gwenhwyfar': u'궨후이바르',
            u'Aneirin': u'아네이린',
            u'Myrddin': u'머르딘',
            u'Llywarch': u'흘러와르흐',
            u'Cad Godeu': u'카드 고데이',
            u'Lleu Llaw Gyffes': u'흘레이 흘라우 거페스',
            u'tynged': u'텅에드',
            u'Chwedlau Odo': u'훼들라이 오도',
            u'Culhwch ac Olwen': u'퀼후흐 악 올웬',
            u'Math fab Mathonwy': u'마스 바브 마소누이',
            u'Pwyll Pendefig Dyfed': u'푸이흘 펜데비그 더베드',
        })
########NEW FILE########
