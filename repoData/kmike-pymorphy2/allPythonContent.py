__FILENAME__ = bench
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pymorphy2 benchmark utility.

Usage:
    bench.py run [--dict=<DICT_PATH>] [--repeats=<NUM>] [--verbose]
    bench.py -h | --help
    bench.py --version

Options:
    -d --dict <DICT_PATH>   Use dictionary from <DICT_PATH>
    -r --repeats <NUM>      Number of times to run each benchmarks [default: 5]
    -v --verbose            Be more verbose

"""
import logging
import sys
import os
from pymorphy2.vendor.docopt import docopt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pymorphy2

from benchmarks import speed

logger = logging.getLogger('pymorphy2.bench')
logger.addHandler(logging.StreamHandler())


def main():
    """ CLI interface dispatcher """
    args = docopt(__doc__, version=pymorphy2.__version__)

    if args['--verbose']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args['run']:
        speed.bench_all(
            dict_path=args['--dict'],
            repeats=int(args['--repeats'])
        )

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
########NEW FILE########
__FILENAME__ = speed
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division
import logging
import codecs
import os
import functools
import datetime

from pymorphy2 import MorphAnalyzer
from benchmarks import utils

logger = logging.getLogger('pymorphy2.bench')

DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'dev_data',
    'unigrams.txt'
)

def load_words(path=DATA_PATH):
    words = []
    with codecs.open(path, 'r', 'utf8') as f:
        for line in f:
            word, count, ipm = line.split()
            count = int(count)
            words.append((word.lower(), count))
    return words

def get_total_usages(words):
    return sum(w[1] for w in words)

def bench_tag(morph, words, total_usages, repeats):
    word_no_umlauts = [(w[0].replace('ё', 'е'), w[1]) for w in words]

    def _run():
        for word, cnt in words:
            for x in range(cnt):
                morph.tag(word)

    def _run_nofreq():
        for word, cnt in words:
            morph.tag(word)

    def _run_no_umlauts():
        for word, cnt in word_no_umlauts:
            morph.tag(word)

    def _run_str():
        for word, cnt in words:
            str(morph.tag(word))

    measure = functools.partial(utils.measure, repeats=repeats)

    logger.info("    morph.tag(w): %0.0f words/sec (considering word frequencies)", measure(_run, total_usages))
    logger.info("    morph.tag(w): %0.0f words/sec", measure(_run_nofreq, len(words)))
    logger.info("    morph.tag(w): %0.0f words/sec (umlauts removed from input)", measure(_run_no_umlauts, len(words)))
    logger.info("    morph.tag(w): %0.0f words/sec (str(tag) called)", measure(_run_str, len(words)))


def bench_parse(morph, words, total_usages, repeats):
    def _run():
        for word, cnt in words:
            for x in range(cnt):
                morph.parse(word)

    def _run_nofreq():
        for word, cnt in words:
            morph.parse(word)

    def _run_normal_form():
        for word, cnt in words:
            [p.normal_form for p in morph.parse(word)]

    def _run_normalized():
        for word, cnt in words:
            [p.normalized for p in morph.parse(word)]

    def _run_is_noun():
        for word, cnt in words:
            [set(['NOUN']) in p.tag for p in morph.parse(word)]

    def _run_is_noun2():
        for word, cnt in words:
            [p.tag.POS == 'NOUN' for p in morph.parse(word)]

    def _run_word_is_known():
        for x in range(10):
            for word, cnt in words:
                morph.word_is_known(word)

    def _run_cyr_repr():
        for word, cnt in words:
            [p.tag.cyr_repr for p in morph.parse(word)]

    def _run_grammemes_cyr():
        for word, cnt in words:
            [p.tag.grammemes_cyr for p in morph.parse(word)]

    def _run_POS_cyr():
        for word, cnt in words:
            [morph.lat2cyr(p.tag) for p in morph.parse(word)]

    def _run_lexeme():
        for word, cnt in words[::5]:
            [p.lexeme for p in morph.parse(word)]

    measure = functools.partial(utils.measure, repeats=repeats)

    def show_info(bench_name, func, note='', count=len(words)):
        wps = measure(func, count)
        logger.info("    %-50s %0.0f words/sec %s", bench_name, wps, note)


    # === run benchmarks:

    show_info('morph.parse(w)', _run_nofreq)
    show_info('morph.parse(w)', _run, '(considering word frequencies)', total_usages)

    if morph._result_type is not None:
        show_info('morph.word_is_known(w)', _run_word_is_known, count=len(words)*10)
        show_info("[p.normal_form for p in morph.parse(w)]", _run_normal_form)
        show_info("[p.normalized for p in morph.parse(w)]", _run_normalized)
        show_info("[p.lexeme for p in morph.parse(w)]", _run_lexeme, count=len(words)/5)
        show_info("[{'NOUN'} in p.tag for p in morph.parse(w)]", _run_is_noun)
        show_info("[p.tag.POS == 'NOUN' for p in morph.parse(w)]", _run_is_noun2)
        show_info("[p.tag.cyr_repr for p in morph.parse(word)]", _run_cyr_repr)
        show_info("[p.tag.grammemes_cyr for p in morph.parse(word)]", _run_grammemes_cyr)
        show_info("[morph.lat2cyr(p.tag) for p in morph.parse(word)]", _run_POS_cyr)

    logger.info("")


def bench_all(repeats, dict_path=None):
    """ Run all benchmarks """
    logger.debug("loading MorphAnalyzer...")
    morph = MorphAnalyzer(dict_path)
    morph_plain = MorphAnalyzer(dict_path, result_type=None)

    logger.debug("loading benchmark data...")
    words = load_words()
    total_usages = get_total_usages(words)

    logger.debug("Words: %d, usages: %d", len(words), total_usages)

    start_time = datetime.datetime.now()

    logger.info("\nbenchmarking MorphAnalyzer():")
    bench_parse(morph, words, total_usages, repeats)
    bench_tag(morph, words, total_usages, repeats)

    logger.info("\nbenchmarking MorphAnalyzer(result_type=None):")
    bench_parse(morph_plain, words, total_usages, repeats)

    end_time = datetime.datetime.now()
    logger.info("----\nDone in %s.\n" % (end_time-start_time))

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division
import time
import timeit
import gc

def measure(func, inner_iterations=1, repeats=5):
    """
    Runs func ``repeats`` times and returns the fastest speed
    (inner loop iterations per second). Use ``inner_iterations`` to specify
    the number of inner loop iterations.

    Use this function for long-running functions.
    """
    gc.disable()
    times = []
    for x in range(repeats):
        start = time.time()
        func()
        times.append(time.time() - start)

    gc.enable()
    return inner_iterations/min(times)


def bench(stmt, setup, op_count=1, repeats=3, runs=5):
    """
    Runs ``stmt`` benchmark ``repeats``*``runs`` times,
    selects the fastest run and returns the minimum time.
    """
    timer = timeit.Timer(stmt, setup)
    times = []
    for x in range(runs):
        times.append(timer.timeit(repeats))

    def op_time(t):
        return op_count*repeats / t

    return op_time(min(times))


def format_bench(name, result, description='K words/sec'):
    return "%25s:\t%0.3f%s" % (name, result, description)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pymorphy2 documentation build configuration file, created by
# sphinx-quickstart on Sun Jul 29 04:34:30 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.
from __future__ import unicode_literals

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
))

def setup(app):
    # see https://github.com/snide/sphinx_rtd_theme/issues/117
    app.add_stylesheet("rtfd_overrides.css")

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode', 'sphinx.ext.graphviz']

graphviz_output_format = 'svg'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Морфологический анализатор pymorphy2'
copyright = '2014, Mikhail Korobov'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = 'v0.1'
# The full version, including alpha/beta/rc tags.
release = 'v0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'ru'

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Морфологический анализатор pymorphy2"

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = u'pymorphy2'

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

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
htmlhelp_basename = 'pymorphy2doc'


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
  ('index', 'pymorphy2.tex', 'pymorphy2 Documentation',
   'Mikhail Korobov', 'manual'),
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
    ('index', 'pymorphy2', 'pymorphy2 Documentation',
     ['Mikhail Korobov'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'pymorphy2', 'pymorphy2 Documentation',
   'Mikhail Korobov', 'pymorphy2', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = analyzer
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, division
import os
import heapq
import collections
import logging
import threading
import operator

from pymorphy2 import opencorpora_dict
from pymorphy2 import units
from pymorphy2.dawg import ConditionalProbDistDAWG

logger = logging.getLogger(__name__)

_Parse = collections.namedtuple('Parse', 'word, tag, normal_form, score, methods_stack')

_score_getter = operator.itemgetter(3)

class Parse(_Parse):
    """
    Parse result wrapper.
    """

    _morph = None
    """ :type _morph: MorphAnalyzer """

    _dict = None
    """ :type _dict: pymorphy2.opencorpora_dict.Dictionary """

    def inflect(self, required_grammemes):
        res = self._morph._inflect(self, required_grammemes)
        return None if not res else res[0]

    def make_agree_with_number(self, num):
        """
        Inflect the word so that it agrees with ``num``
        """
        return self.inflect(self.tag.numeral_agreement_grammemes(num))

    @property
    def lexeme(self):
        """ A lexeme this form belongs to. """
        return self._morph.get_lexeme(self)

    @property
    def is_known(self):
        """ True if this form is a known dictionary form. """
        return self._dict.word_is_known(self.word, strict_ee=True)

    @property
    def normalized(self):
        """ A :class:`Parse` instance for :attr:`self.normal_form`. """
        last_method = self.methods_stack[-1]
        return self.__class__(*last_method[0].normalized(self))

    # @property
    # def paradigm(self):
    #     return self._dict.build_paradigm_info(self.para_id)


class SingleTagProbabilityEstimator(object):
    def __init__(self, dict_path):
        cpd_path = os.path.join(dict_path, 'p_t_given_w.intdawg')
        self.p_t_given_w = ConditionalProbDistDAWG().load(cpd_path)

    def apply_to_parses(self, word, word_lower, parses):
        if not parses:
            return parses

        probs = [self.p_t_given_w.prob(word_lower, tag)
                for (word, tag, normal_form, score, methods_stack) in parses]

        if sum(probs) == 0:
            # no P(t|w) information is available; return normalized estimate
            k = 1.0 / sum(map(_score_getter, parses))
            return [
                (word, tag, normal_form, score*k, methods_stack)
                for (word, tag, normal_form, score, methods_stack) in parses
            ]

        # replace score with P(t|w) probability
        return sorted([
            (word, tag, normal_form, prob, methods_stack)
            for (word, tag, normal_form, score, methods_stack), prob
            in zip(parses, probs)
        ], key=_score_getter, reverse=True)

    def apply_to_tags(self, word, word_lower, tags):
        if not tags:
            return tags
        return sorted(tags,
            key=lambda tag: self.p_t_given_w.prob(word_lower, tag),
            reverse=True
        )


class DummySingleTagProbabilityEstimator(object):
    def __init__(self, dict_path):
        pass

    def apply_to_parses(self, word, word_lower, parses):
        return parses

    def apply_to_tags(self, word, word_lower, tags):
        return tags


class MorphAnalyzer(object):
    """
    Morphological analyzer for Russian language.

    For a given word it can find all possible inflectional paradigms
    and thus compute all possible tags and normal forms.

    Analyzer uses morphological word features and a lexicon
    (dictionary compiled from XML available at OpenCorpora.org);
    for unknown words heuristic algorithm is used.

    Create a :class:`MorphAnalyzer` object::

        >>> import pymorphy2
        >>> morph = pymorphy2.MorphAnalyzer()

    MorphAnalyzer uses dictionaries from ``pymorphy2-dicts`` package
    (which can be installed via ``pip install pymorphy2-dicts``).

    Alternatively (e.g. if you have your own precompiled dictionaries),
    either create ``PYMORPHY2_DICT_PATH`` environment variable
    with a path to dictionaries, or pass ``path`` argument
    to :class:`pymorphy2.MorphAnalyzer` constructor::

        >>> morph = pymorphy2.MorphAnalyzer('/path/to/dictionaries') # doctest: +SKIP

    By default, methods of this class return parsing results
    as namedtuples :class:`Parse`. This has performance implications
    under CPython, so if you need maximum speed then pass
    ``result_type=None`` to make analyzer return plain unwrapped tuples::

        >>> morph = pymorphy2.MorphAnalyzer(result_type=None)

    """

    ENV_VARIABLE = 'PYMORPHY2_DICT_PATH'
    DEFAULT_UNITS = [
        [
            units.DictionaryAnalyzer,
            units.AbbreviatedFirstNameAnalyzer,
            units.AbbreviatedPatronymicAnalyzer,
        ],

        units.NumberAnalyzer,
        units.PunctuationAnalyzer,
        [
            units.RomanNumberAnalyzer,
            units.LatinAnalyzer
        ],

        units.HyphenSeparatedParticleAnalyzer,
        units.HyphenAdverbAnalyzer,
        units.HyphenatedWordsAnalyzer,
        units.KnownPrefixAnalyzer,
        [
            units.UnknownPrefixAnalyzer,
            units.KnownSuffixAnalyzer
        ],
        units.UnknAnalyzer,
    ]

    def __init__(self, path=None, result_type=Parse, units=None,
                 probability_estimator_cls=SingleTagProbabilityEstimator):
        path = self.choose_dictionary_path(path)
        with threading.RLock():
            self.dictionary = opencorpora_dict.Dictionary(path)
            if probability_estimator_cls is None:
                probability_estimator_cls = DummySingleTagProbabilityEstimator
            self.prob_estimator = probability_estimator_cls(path)

            if result_type is not None:
                # create a subclass with the same name,
                # but with _morph attribute bound to self
                res_type = type(
                    result_type.__name__,
                    (result_type,),
                    {'_morph': self, '_dict': self.dictionary}
                )
                self._result_type = res_type
            else:
                self._result_type = None

            self._result_type_orig = result_type
            self._init_units(units)

    def _init_units(self, unit_classes=None):
        if unit_classes is None:
            unit_classes = self.DEFAULT_UNITS

        self._unit_classes = unit_classes
        self._units = []
        for item in unit_classes:
            if isinstance(item, (list, tuple)):
                for cls in item[:-1]:
                    self._units.append((cls(self), False))
                self._units.append((item[-1](self), True))
            else:
                self._units.append((item(self), True))

    @classmethod
    def choose_dictionary_path(cls, path=None):
        if path is not None:
            return path

        if cls.ENV_VARIABLE in os.environ:
            return os.environ[cls.ENV_VARIABLE]

        try:
            import pymorphy2_dicts
            return pymorphy2_dicts.get_path()
        except ImportError:
            msg = ("Can't find dictionaries. "
                   "Please either pass a path to dictionaries, "
                   "or install 'pymorphy2-dicts' package, "
                   "or set %s environment variable.") % cls.ENV_VARIABLE
            raise ValueError(msg)

    def parse(self, word):
        """
        Analyze the word and return a list of :class:`pymorphy2.analyzer.Parse`
        namedtuples:

            Parse(word, tag, normal_form, para_id, idx, _score)

        (or plain tuples if ``result_type=None`` was used in constructor).
        """
        res = []
        seen = set()
        word_lower = word.lower()

        for analyzer, is_terminal in self._units:
            res.extend(analyzer.parse(word, word_lower, seen))

            if is_terminal and res:
                break

        res = self.prob_estimator.apply_to_parses(word, word_lower, res)

        if self._result_type is None:
            return res

        return [self._result_type(*p) for p in res]

    def tag(self, word):
        res = []
        seen = set()
        word_lower = word.lower()

        for analyzer, is_terminal in self._units:
            res.extend(analyzer.tag(word, word_lower, seen))

            if is_terminal and res:
                break

        return self.prob_estimator.apply_to_tags(word, word_lower, res)

    def normal_forms(self, word):
        """
        Return a list of word normal forms.
        """
        seen = set()
        result = []

        for p in self.parse(word):
            normal_form = p[2]
            if normal_form not in seen:
                result.append(normal_form)
                seen.add(normal_form)
        return result

    # ==== inflection ========

    def get_lexeme(self, form):
        """
        Return the lexeme this parse belongs to.
        """
        methods_stack = form[4]
        last_method = methods_stack[-1]
        result = last_method[0].get_lexeme(form)

        if self._result_type is None:
            return result
        return [self._result_type(*p) for p in result]

    def _inflect(self, form, required_grammemes):
        possible_results = [f for f in self.get_lexeme(form)
                            if required_grammemes <= f[1].grammemes]

        if not possible_results:
            required_grammemes = self.TagClass.fix_rare_cases(required_grammemes)
            possible_results = [f for f in self.get_lexeme(form)
                                if required_grammemes <= f[1].grammemes]

        grammemes = form[1].updated_grammemes(required_grammemes)
        def similarity(frm):
            tag = frm[1]
            return len(grammemes & tag.grammemes)

        return heapq.nlargest(1, possible_results, key=similarity)

    # ====== misc =========

    def iter_known_word_parses(self, prefix=""):
        """
        Return an iterator over parses of dictionary words that starts
        with a given prefix (default empty prefix means "all words").
        """

        # XXX: this method currently assumes that
        # units.DictionaryAnalyzer is the first analyzer unit.
        for word, tag, normal_form, para_id, idx in self.dictionary.iter_known_words(prefix):
            methods = ((self._units[0][0], word, para_id, idx),)
            parse = (word, tag, normal_form, 1.0, methods)
            if self._result_type is None:
                yield parse
            else:
                yield self._result_type(*parse)

    def word_is_known(self, word, strict_ee=False):
        """
        Check if a ``word`` is in the dictionary.
        Pass ``strict_ee=True`` if ``word`` is guaranteed to
        have correct е/ё letters.

        .. note::

            Dictionary words are not always correct words;
            the dictionary also contains incorrect forms which
            are commonly used. So for spellchecking tasks this
            method should be used with extra care.

        """
        return self.dictionary.word_is_known(word.lower(), strict_ee)

    @property
    def TagClass(self):
        """
        :rtype: pymorphy2.tagset.OpencorporaTag
        """
        return self.dictionary.Tag

    def cyr2lat(self, tag_or_grammeme):
        """ Return Latin representation for ``tag_or_grammeme`` string """
        return self.TagClass.cyr2lat(tag_or_grammeme)

    def lat2cyr(self, tag_or_grammeme):
        """ Return Cyrillic representation for ``tag_or_grammeme`` string """
        return self.TagClass.lat2cyr(tag_or_grammeme)

    def __reduce__(self):
        args = (self.dictionary.path, self._result_type_orig, self._unit_classes)
        return self.__class__, args, None



########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function, division

import logging
import time
import sys
import codecs
import os

import pymorphy2
from pymorphy2 import opencorpora_dict, test_suite_generator
from pymorphy2.vendor.docopt import docopt
from pymorphy2.utils import download_bz2, get_mem_usage, json_read, json_write

logger = logging.getLogger('pymorphy2')
logger.addHandler(logging.StreamHandler())

XML_BZ2_URL = "http://opencorpora.org/files/export/dict/dict.opcorpora.xml.bz2"

# ============================ Commands ===========================

def compile_dict(in_filename, out_path=None, overwrite=False, prediction_options=None):
    """
    Make a Pymorphy2 dictionary from OpenCorpora .xml dictionary.
    """
    if out_path is None:
        out_path = 'dict'

    opencorpora_dict.convert_to_pymorphy2(
        opencorpora_dict_path = in_filename,
        out_path = out_path,
        overwrite = overwrite,
        prediction_options = prediction_options
    )

def show_dict_mem_usage(dict_path=None, verbose=False):
    """
    Show dictionary memory usage.
    """
    initial_mem = get_mem_usage()
    initial_time = time.time()

    morph = pymorphy2.MorphAnalyzer(dict_path)

    end_time = time.time()
    mem_usage = get_mem_usage()

    logger.info('Memory usage: %0.1fM dictionary, %0.1fM total (load time %0.2fs)',
        (mem_usage-initial_mem)/(1024*1024), mem_usage/(1024*1024), end_time-initial_time)

    if verbose:
        try:
            from guppy import hpy; hp=hpy()
            logger.debug(hp.heap())
        except ImportError:
            logger.warn('guppy is not installed, detailed info is not available')


def show_dict_meta(dict_path=None):
    morph = pymorphy2.MorphAnalyzer(dict_path)

    for key, value in morph.dictionary.meta.items():
        logger.info("%s: %s", key, value)


def make_test_suite(dict_filename, out_filename, word_limit=100):
    """ Make a test suite from (unparsed) OpenCorpora dictionary. """
    return test_suite_generator.make_test_suite(
        dict_filename, out_filename, word_limit=int(word_limit))


def download_dict_xml(out_filename, verbose):
    """ Download an updated dictionary XML from OpenCorpora """
    def on_chunk():
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()

    logger.info('Creating %s from %s' % (out_filename, XML_BZ2_URL))
    with open(out_filename, "wb") as f:
        download_bz2(XML_BZ2_URL, f, on_chunk=on_chunk)

    logger.info('\nDone.')


def _parse(dict_path, in_filename, out_filename):
    morph = pymorphy2.MorphAnalyzer(dict_path)
    with codecs.open(in_filename, 'r', 'utf8') as in_file:
        with codecs.open(out_filename, 'w', 'utf8') as out_file:
            for line in in_file:
                word = line.strip()
                parses = morph.parse(word)
                parse_str = "|".join([p[1] for p in parses])
                out_file.write(word + ": " +parse_str + "\n")


def download_corpus_xml(out_filename):
    from opencorpora.cli import _download, FULL_CORPORA_URL_BZ2
    return _download(
        out_file=out_filename,
        decompress=True,
        disambig=False,
        url=FULL_CORPORA_URL_BZ2,
        verbose=True
    )


def estimate_tag_cpd(corpus_filename, out_path, min_word_freq, update_meta=True):
    from pymorphy2.opencorpora_dict.probability import (
        estimate_conditional_tag_probability, build_cpd_dawg)

    m = pymorphy2.MorphAnalyzer(out_path, probability_estimator_cls=None)

    logger.info("Estimating P(t|w) from %s" % corpus_filename)
    cpd, cfd = estimate_conditional_tag_probability(m, corpus_filename)

    logger.info("Encoding P(t|w) as DAWG")
    d = build_cpd_dawg(m, cpd, int(min_word_freq))
    dawg_filename = os.path.join(out_path, 'p_t_given_w.intdawg')
    d.save(dawg_filename)

    if update_meta:
        logger.info("Updating meta information")
        meta_filename = os.path.join(out_path, 'meta.json')
        meta = json_read(meta_filename)
        meta.extend([
            ('P(t|w)', True),
            ('P(t|w)_unique_words', len(cpd.conditions())),
            ('P(t|w)_outcomes', cfd.N()),
            ('P(t|w)_min_word_freq', int(min_word_freq)),
        ])
        json_write(meta_filename, meta)

    logger.info('\nDone.')


# =============================================================================

# Hacks are here to make docstring compatible with both
# docopt and sphinx.ext.autodoc.

head = """

Pymorphy2 is a morphological analyzer / inflection engine for Russian language.
"""
__doc__ ="""
Usage::

    pymorphy dict compile <DICT_XML> [--out <PATH>] [--force] [--verbose] [--min_ending_freq <NUM>] [--min_paradigm_popularity <NUM>] [--max_suffix_length <NUM>]
    pymorphy dict download_xml <OUT_FILE> [--verbose]
    pymorphy dict mem_usage [--dict <PATH>] [--verbose]
    pymorphy dict make_test_suite <XML_FILE> <OUT_FILE> [--limit <NUM>] [--verbose]
    pymorphy dict meta [--dict <PATH>]
    pymorphy prob download_xml <OUT_FILE> [--verbose]
    pymorphy prob estimate_cpd <CORPUS_XML> [--out <PATH>] [--min_word_freq <NUM>]
    pymorphy _parse <IN_FILE> <OUT_FILE> [--dict <PATH>] [--verbose]
    pymorphy -h | --help
    pymorphy --version

Options::

    -v --verbose                        Be more verbose
    -f --force                          Overwrite target folder
    -o --out <PATH>                     Output folder name [default: dict]
    --limit <NUM>                       Min. number of words per gram. tag [default: 100]
    --min_ending_freq <NUM>             Prediction: min. number of suffix occurances [default: 2]
    --min_paradigm_popularity <NUM>     Prediction: min. number of lexemes for the paradigm [default: 3]
    --max_suffix_length <NUM>           Prediction: max. length of prediction suffixes [default: 5]
    --min_word_freq <NUM>               P(t|w) estimation: min. word count in source corpus [default: 1]
    --dict <PATH>                       Dictionary folder path

"""
DOC = head + __doc__.replace('::\n', ':')


def main():
    """
    Pymorphy CLI interface dispatcher
    """
    args = docopt(DOC, version=pymorphy2.__version__)

    if args['--verbose']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.debug(args)

    if args['_parse']:
        return _parse(args['--dict'], args['<IN_FILE>'], args['<OUT_FILE>'])

    elif args['dict']:
        if args['compile']:
            prediction_options = dict(
                (key, int(args['--'+key]))
                for key in ('min_ending_freq', 'min_paradigm_popularity', 'max_suffix_length')
            )
            return compile_dict(args['<DICT_XML>'], args['--out'], args['--force'], prediction_options)
        elif args['mem_usage']:
            return show_dict_mem_usage(args['--dict'], args['--verbose'])
        elif args['meta']:
            return show_dict_meta(args['--dict'])
        elif args['make_test_suite']:
            return make_test_suite(args['<XML_FILE>'], args['<OUT_FILE>'], int(args['--limit']))
        elif args['download_xml']:
            return download_dict_xml(args['<OUT_FILE>'], args['--verbose'])

    elif args['prob']:
        if args['download_xml']:
            return download_corpus_xml(args['<OUT_FILE>'])
        elif args['estimate_cpd']:
            return estimate_tag_cpd(args['<CORPUS_XML>'], args['--out'], args['--min_word_freq'])


########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

PARADIGM_PREFIXES = ["", "по", "наи"]

PREDICTION_PREFIXES = [
    "авиа",
    "авто",
    "аква",
    "анти",
    "анти-",
    "антропо",
    "архи",
    "арт",
    "арт-",
    "астро",
    "аудио",
    "аэро",
    "без",
    "бес",
    "био",
    "вело",
    "взаимо",
    "вне",
    "внутри",
    "видео",
    "вице-",
    "вперед",
    "впереди",
    "гекто",
    "гелио",
    "гео",
    "гетеро",
    "гига",
    "гигро",
    "гипер",
    "гипо",
    "гомо",
    "дву",
    "двух",
    "де",
    "дез",
    "дека",
    "деци",
    "дис",
    "до",
    "евро",
    "за",
    "зоо",
    "интер",
    "инфра",
    "квази",
    "квази-",
    "кило",
    "кино",
    "контр",
    "контр-",
    "космо",
    "космо-",
    "крипто",
    "лейб-",
    "лже",
    "лже-",
    "макро",
    "макси",
    "макси-",
    "мало",
    "меж",
    "медиа",
    "медиа-",
    "мега",
    "мета",
    "мета-",
    "метео",
    "метро",
    "микро",
    "милли",
    "мини",
    "мини-",
    "моно",
    "мото",
    "много",
    "мульти",
    "нано",
    "нарко",
    "не",
    "небез",
    "недо",
    "нейро",
    "нео",
    "низко",
    "обер-",
    "обще",
    "одно",
    "около",
    "орто",
    "палео",
    "пан",
    "пара",
    "пента",
    "пере",
    "пиро",
    "поли",
    "полу",
    "после",
    "пост",
    "пост-",
    "порно",
    "пра",
    "пра-",
    "пред",
    "пресс-",
    "противо",
    "противо-",
    "прото",
    "псевдо",
    "псевдо-",
    "радио",
    "разно",
    "ре",
    "ретро",
    "ретро-",
    "само",
    "санти",
    "сверх",
    "сверх-",
    "спец",
    "суб",
    "супер",
    "супер-",
    "супра",
    "теле",
    "тетра",
    "топ-",
    "транс",
    "транс-",
    "ультра",
    "унтер-",
    "штаб-",
    "экзо",
    "эко",
    "эндо",
    "эконом-",
    "экс",
    "экс-",
    "экстра",
    "экстра-",
    "электро",
    "энерго",
    "этно",
]

########NEW FILE########
__FILENAME__ = dawg
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

try:
    from dawg import DAWG, RecordDAWG, IntCompletionDAWG
    CAN_CREATE = True

except ImportError:
    from dawg_python import DAWG, RecordDAWG, IntCompletionDAWG
    CAN_CREATE = False

def assert_can_create():
    if not CAN_CREATE:
        msg = ("Creating of DAWGs with DAWG-Python is "
               "not supported; install 'dawg' package.")
        raise NotImplementedError(msg)


class WordsDawg(RecordDAWG):
    """
    DAWG for storing words.
    """

    # We are storing 2 unsigned short ints as values:
    # the paradigm ID and the form index (inside paradigm).
    # Byte order is big-endian (this makes word forms properly sorted).
    DATA_FORMAT = str(">HH")

    def __init__(self, data=None):
        if data is None:
            super(WordsDawg, self).__init__(self.DATA_FORMAT)
        else:
            assert_can_create()
            super(WordsDawg, self).__init__(self.DATA_FORMAT, data)


class PredictionSuffixesDAWG(WordsDawg):
    """
    DAWG for storing prediction data.
    """

    # We are storing 3 unsigned short ints as values:
    # count, the paradigm ID and the form index (inside paradigm).
    # Byte order is big-endian (this makes word forms properly sorted).
    DATA_FORMAT = str(">HHH")


class ConditionalProbDistDAWG(IntCompletionDAWG):

    MULTIPLIER = 1000000

    def __init__(self, data=None):
        if data is None:
            super(ConditionalProbDistDAWG, self).__init__()
        else:
            assert_can_create()
            dawg_data = (
                ("%s:%s" % (word, tag), int(prob*self.MULTIPLIER))
                for (word, tag), prob in data
            )
            super(ConditionalProbDistDAWG, self).__init__(dawg_data)

    def prob(self, word, tag):
        dawg_key = "%s:%s" % (word, tag)
        return self.get(dawg_key, 0) / self.MULTIPLIER

########NEW FILE########
__FILENAME__ = compile
# -*- coding: utf-8 -*-
"""
:mod:`pymorphy2.opencorpora_dict.compile` is a
module for converting OpenCorpora dictionaries
to pymorphy2 representation.
"""
from __future__ import absolute_import, unicode_literals
import os
import logging
import collections
import itertools
import array
import operator

try:
    izip = itertools.izip
except AttributeError:
    izip = zip

from pymorphy2 import dawg
from pymorphy2.constants import PARADIGM_PREFIXES, PREDICTION_PREFIXES
from pymorphy2.utils import longest_common_substring, largest_group

logger = logging.getLogger(__name__)


CompiledDictionary = collections.namedtuple(
    'CompiledDictionary',
    'gramtab suffixes paradigms words_dawg prediction_suffixes_dawgs parsed_dict prediction_options'
)


def convert_to_pymorphy2(opencorpora_dict_path, out_path, overwrite=False,
                         prediction_options=None):
    """
    Convert a dictionary from OpenCorpora XML format to
    Pymorphy2 compacted format.

    ``out_path`` should be a name of folder where to put dictionaries.
    """
    from .parse import parse_opencorpora_xml
    from .preprocess import simplify_tags
    from .storage import save_compiled_dict

    dawg.assert_can_create()
    if not _create_out_path(out_path, overwrite):
        return

    parsed_dict = parse_opencorpora_xml(opencorpora_dict_path)
    simplify_tags(parsed_dict)
    compiled_dict = compile_parsed_dict(parsed_dict, prediction_options)
    save_compiled_dict(compiled_dict, out_path)


def compile_parsed_dict(parsed_dict, prediction_options=None):
    """
    Return compacted dictionary data.
    """
    _prediction_options = dict(
        # defaults
        min_ending_freq=2,
        min_paradigm_popularity=3,
        max_suffix_length=5
    )
    _prediction_options.update(prediction_options or {})

    gramtab = []
    paradigms = []
    words = []

    seen_tags = dict()
    seen_paradigms = dict()

    logger.info("inlining lexeme derivational rules...")
    lexemes = _join_lexemes(parsed_dict.lexemes, parsed_dict.links)

    logger.info('building paradigms...')
    logger.debug("%20s %15s %15s %15s", "word", "len(gramtab)", "len(words)", "len(paradigms)")

    paradigm_popularity = collections.defaultdict(int)

    for index, lexeme in enumerate(lexemes):
        stem, paradigm = _to_paradigm(lexeme)

        # build gramtab
        for suff, tag, pref in paradigm:
            if tag not in seen_tags:
                seen_tags[tag] = len(gramtab)
                gramtab.append(tag)

        # build paradigm index
        if paradigm not in seen_paradigms:
            seen_paradigms[paradigm] = len(paradigms)
            paradigms.append(
                tuple([(suff, seen_tags[tag], pref) for suff, tag, pref in paradigm])
            )

        para_id = seen_paradigms[paradigm]
        paradigm_popularity[para_id] += 1

        for idx, (suff, tag, pref) in enumerate(paradigm):
            form = pref+stem+suff
            words.append(
                (form, (para_id, idx))
            )

        if not (index % 10000):
            word = paradigm[0][2] + stem + paradigm[0][0]
            logger.debug("%20s %15s %15s %15s", word, len(gramtab), len(words), len(paradigms))


    logger.debug("%20s %15s %15s %15s", "total:", len(gramtab), len(words), len(paradigms))
    logger.debug("linearizing paradigms..")

    def get_form(para):
        return list(next(izip(*para)))

    forms = [get_form(para) for para in paradigms]
    suffixes = sorted(set(list(itertools.chain(*forms))))
    suffixes_dict = dict(
        (suff, index)
        for index, suff in enumerate(suffixes)
    )

    def fix_strings(paradigm):
        """ Replace suffix and prefix with the respective id numbers. """
        para = []
        for suff, tag, pref in paradigm:
            para.append(
                (suffixes_dict[suff], tag, PARADIGM_PREFIXES.index(pref))
            )
        return para

    paradigms = (fix_strings(para) for para in paradigms)
    paradigms = [_linearized_paradigm(paradigm) for paradigm in paradigms]

    logger.debug('calculating prediction data..')
    suffixes_dawgs_data = _suffixes_prediction_data(
        words, paradigm_popularity, gramtab, paradigms, suffixes, **_prediction_options
    )

    logger.debug('building word DAWG..')
    words_dawg = dawg.WordsDawg(words)

    del words

    prediction_suffixes_dawgs = []
    for prefix_id, dawg_data in enumerate(suffixes_dawgs_data):
        logger.debug('building prediction_suffixes DAWGs #%d..' % prefix_id)
        prediction_suffixes_dawgs.append(dawg.PredictionSuffixesDAWG(dawg_data))

    return CompiledDictionary(tuple(gramtab), suffixes, paradigms,
                              words_dawg, prediction_suffixes_dawgs,
                              parsed_dict, _prediction_options)


def _join_lexemes(lexemes, links):
    """
    Combine linked lexemes to a single lexeme.
    """

#    <link_types>
#    <type id="1">ADJF-ADJS</type>
#    <type id="2">ADJF-COMP</type>
#    <type id="3">INFN-VERB</type>
#    <type id="4">INFN-PRTF</type>
#    <type id="5">INFN-GRND</type>
#    <type id="6">PRTF-PRTS</type>
#    <type id="7">NAME-PATR</type>
#    <type id="8">PATR_MASC-PATR_FEMN</type>
#    <type id="9">SURN_MASC-SURN_FEMN</type>
#    <type id="10">SURN_MASC-SURN_PLUR</type>
#    <type id="11">PERF-IMPF</type>
#    <type id="12">ADJF-SUPR_ejsh</type>
#    <type id="13">PATR_MASC_FORM-PATR_MASC_INFR</type>
#    <type id="14">PATR_FEMN_FORM-PATR_FEMN_INFR</type>
#    <type id="15">ADJF_eish-SUPR_nai_eish</type>
#    <type id="16">ADJF-SUPR_ajsh</type>
#    <type id="17">ADJF_aish-SUPR_nai_aish</type>
#    <type id="18">ADJF-SUPR_suppl</type>
#    <type id="19">ADJF-SUPR_nai</type>
#    <type id="20">ADJF-SUPR_slng</type>
#    </link_types>

    EXCLUDED_LINK_TYPES = set([7, ])
#    ALLOWED_LINK_TYPES = set([3, 4, 5])

    moves = dict()

    def move_lexeme(from_id, to_id):
        lm = lexemes[str(from_id)]

        while to_id in moves:
            to_id = moves[to_id]

        lexemes[str(to_id)].extend(lm)
        del lm[:]
        moves[from_id] = to_id

    for link_start, link_end, type_id in links:
        if type_id in EXCLUDED_LINK_TYPES:
            continue

#        if type_id not in ALLOWED_LINK_TYPES:
#            continue

        move_lexeme(link_end, link_start)

    lex_ids = sorted(lexemes.keys(), key=int)
    return [lexemes[lex_id] for lex_id in lex_ids if lexemes[lex_id]]


def _to_paradigm(lexeme):
    """
    Extract (stem, paradigm) pair from lexeme (which is a list of
    (word_form, tag) tuples). Paradigm is a list of suffixes with
    associated tags and prefixes.
    """
    forms, tags = list(zip(*lexeme))
    prefixes = [''] * len(tags)

    if len(forms) == 1:
        stem = forms[0]
    else:
        stem = longest_common_substring(forms)
        prefixes = [form[:form.index(stem)] for form in forms]

        # only allow prefixes from PARADIGM_PREFIXES
        if any(pref not in PARADIGM_PREFIXES for pref in prefixes):
            stem = ""
            prefixes = [''] * len(tags)

    suffixes = (
        form[len(pref)+len(stem):]
        for form, pref in zip(forms, prefixes)
    )

    return stem, tuple(zip(suffixes, tags, prefixes))


def _suffixes_prediction_data(words, paradigm_popularity, gramtab, paradigms, suffixes,
                              min_ending_freq, min_paradigm_popularity, max_suffix_length):

    logger.debug('calculating prediction data: removing non-productive paradigms..')
    productive_paradigms = set(
        para_id
        for (para_id, count) in paradigm_popularity.items()
        if count >= min_paradigm_popularity
    )

    # ["suffix"] => number of occurrences
    # this is for removing non-productive suffixes
    ending_counts = collections.defaultdict(int)

    # [form_prefix_id]["suffix"]["POS"][(para_id, idx)] => number or occurrences
    # this is for selecting most popular parses
    endings = {}
    for form_prefix_id in range(len(PARADIGM_PREFIXES)):
        endings[form_prefix_id] = collections.defaultdict(
                                    lambda: collections.defaultdict(
                                        lambda: collections.defaultdict(int)))

    logger.debug('calculating prediction data: checking word endings..')
    for word, (para_id, idx) in words:

        if para_id not in productive_paradigms:
            continue

        paradigm = paradigms[para_id]

        form_count = len(paradigm) // 3

        tag = gramtab[paradigm[form_count + idx]]
        form_prefix_id = paradigm[2*form_count + idx]
        form_prefix = PARADIGM_PREFIXES[form_prefix_id]
        form_suffix = suffixes[paradigm[idx]]

        assert len(word) >= len(form_prefix+form_suffix), word
        assert word.startswith(form_prefix), word
        assert word.endswith(form_suffix), word

        if len(word) == len(form_prefix) + len(form_suffix):
            # pseudo-paradigms are useless for prediction
            continue

        POS = tuple(tag.replace(' ', ',', 1).split(','))[0]

        for i in range(max(len(form_suffix), 1), max_suffix_length+1): #was: 1,2,3,4,5
            word_end = word[-i:]

            ending_counts[word_end] += 1
            endings[form_prefix_id][word_end][POS][(para_id, idx)] += 1

    dawgs_data = []

    for form_prefix_id in sorted(endings.keys()):
        logger.debug('calculating prediction data: preparing DAWGs data #%d..' % form_prefix_id)
        counted_suffixes_dawg_data = []
        endings_with_prefix = endings[form_prefix_id]

        for suff in endings_with_prefix:
            if ending_counts[suff] < min_ending_freq:
                continue

            for POS in endings_with_prefix[suff]:

                common_endings = largest_group(
                    endings_with_prefix[suff][POS].items(),
                    operator.itemgetter(1)
                )

                for form, cnt in common_endings:
                    counted_suffixes_dawg_data.append(
                        (suff, (cnt,) + form)
                    )

        dawgs_data.append(counted_suffixes_dawg_data)

    return dawgs_data


def _linearized_paradigm(paradigm):
    """
    Convert ``paradigm`` (a list of tuples with numbers)
    to 1-dimensional array.array (for reduced memory usage).
    """
    return array.array(str("H"), list(itertools.chain(*zip(*paradigm))))


def _create_out_path(out_path, overwrite=False):
    try:
        logger.debug("Creating output folder %s", out_path)
        os.mkdir(out_path)
    except OSError:
        if overwrite:
            logger.info("Output folder already exists, overwriting..")
        else:
            logger.warning("Output folder already exists!")
            return False
    return True


########NEW FILE########
__FILENAME__ = parse
# -*- coding: utf-8 -*-
"""
:mod:`pymorphy2.opencorpora_dict.parse` is a
module for OpenCorpora XML dictionaries parsing.
"""
from __future__ import absolute_import, unicode_literals, division

import logging
import collections

try:
    from lxml.etree import iterparse

    def xml_clear_elem(elem):
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

except ImportError:
    try:
        from xml.etree.cElementTree import iterparse
    except ImportError:
        from xml.etree.ElementTree import iterparse

    def xml_clear_elem(elem):
        elem.clear()


logger = logging.getLogger(__name__)

ParsedDictionary = collections.namedtuple('ParsedDictionary', 'lexemes links grammemes version revision')


def parse_opencorpora_xml(filename):
    """
    Parse OpenCorpora dict XML and return a ``ParsedDictionary`` namedtuple.
    """

    links = []
    lexemes = {}
    grammemes = []
    version, revision = None, None
    _lexemes_len = 0

    for ev, elem in iterparse(filename, events=(str('start'), str('end'))):

        if ev == 'start':
            if elem.tag == 'dictionary':
                version = elem.get('version')
                revision = elem.get('revision')
                logger.info("dictionary v%s, rev%s", version, revision)
                xml_clear_elem(elem)
            continue

        if elem.tag == 'grammeme':
            name = elem.find('name').text
            parent = elem.get('parent')
            alias = elem.find('alias').text
            description = elem.find('description').text

            grammeme = (name, parent, alias, description)
            grammemes.append(grammeme)
            xml_clear_elem(elem)

        if elem.tag == 'lemma':
            if not lexemes:
                logger.info('parsing xml:lemmas...')

            lex_id, word_forms = _word_forms_from_xml_elem(elem)
            lexemes[lex_id] = word_forms
            xml_clear_elem(elem)

        elif elem.tag == 'link':
            if not links:
                logger.info('parsing xml:links...')

            link_tuple = (
                elem.get('from'),
                elem.get('to'),
                elem.get('type'),
            )
            links.append(link_tuple)
            xml_clear_elem(elem)

        if len(lexemes) != _lexemes_len and not (len(lexemes) % 50000):
            logger.debug("%d lexemes parsed" % len(lexemes))
            _lexemes_len = len(lexemes)

    return ParsedDictionary(lexemes, links, grammemes, version, revision)


def _grammemes_from_elem(elem):
    return ",".join(g.get('v') for g in elem.findall('g'))


def _word_forms_from_xml_elem(elem):
    """
    Return a list of (word, tag) pairs given "lemma" XML element.
    """
    lexeme = []
    lex_id = elem.get('id')

    if len(elem) == 0:  # deleted lexeme?
        return lex_id, lexeme

    base_info = elem.findall('l')

    assert len(base_info) == 1
    base_grammemes = _grammemes_from_elem(base_info[0])

    for form_elem in elem.findall('f'):
        grammemes = _grammemes_from_elem(form_elem)
        form = form_elem.get('t').lower()
        lexeme.append(
            (form, " ".join([base_grammemes, grammemes]).strip())
        )

    return lex_id, lexeme

########NEW FILE########
__FILENAME__ = preprocess
# -*- coding: utf-8 -*-
"""
:mod:`pymorphy2.opencorpora_dict.preprocess` is a
module for preprocessing parsed OpenCorpora dictionaries.

The presence of this module means that pymorphy2 dictionaries are
not fully compatible with OpenCorpora.
"""
from __future__ import absolute_import, unicode_literals
import logging
import collections
logger = logging.getLogger(__name__)


def simplify_tags(parsed_dict, skip_space_ambiguity=True):
    """
    This function simplifies tags in :param:`parsed_dict`.
    :param:`parsed_dict` is modified inplace.
    """
    logger.info("simplifying tags: looking for tag spellings")
    spellings = _get_tag_spellings(parsed_dict)

    logger.info("simplifying tags: looking for spelling duplicates "
                "(skip_space_ambiguity: %s)", skip_space_ambiguity)
    tag_replaces = _get_duplicate_tag_replaces(spellings, skip_space_ambiguity)
    logger.debug("%d duplicate tags will be removed", len(tag_replaces))

    logger.info("simplifying tags: fixing")
    for lex_id in parsed_dict.lexemes:
        new_lexeme = [
            (word, _simplify_tag(tag, tag_replaces))
            for word, tag in parsed_dict.lexemes[lex_id]
        ]
        parsed_dict.lexemes[lex_id] = new_lexeme


def tag2grammemes(tag_str):
    """ Given tag string, return tag grammemes """
    return _split_grammemes(replace_redundant_grammemes(tag_str))


def replace_redundant_grammemes(tag_str):
    """ Replace 'loc1', 'gen1' and 'acc1' grammemes in ``tag_str`` """
    return tag_str.replace('loc1', 'loct').replace('gen1', 'gent').replace('acc1', 'accs')


def _split_grammemes(tag_str):
    return frozenset(tag_str.replace(' ', ',', 1).split(','))


def _get_tag_spellings(parsed_dict):
    """
    Return a dict where keys are sets of grammemes found in dictionary
    and values are counters of all tag spellings for these grammemes.
    """
    spellings = collections.defaultdict(lambda: collections.defaultdict(int))
    for tag in _itertags(parsed_dict):
        spellings[tag2grammemes(tag)][tag] += 1
    return spellings


def _get_duplicate_tag_replaces(spellings, skip_space_ambiguity):
    replaces = {}
    for grammemes in spellings:
        tags = spellings[grammemes]
        if _is_ambiguous(tags.keys(), skip_space_ambiguity):
            items = sorted(tags.items(), key=lambda it: it[1], reverse=True)
            top_tag = items[0][0]
            for tag, count in items[1:]:
                replaces[tag] = top_tag
    return replaces


def _is_ambiguous(tags, skip_space_ambiguity=True):
    """
    >>> _is_ambiguous(['NOUN sing,masc'])
    False
    >>> _is_ambiguous(['NOUN sing,masc', 'NOUN masc,sing'])
    True
    >>> _is_ambiguous(['NOUN masc,sing', 'NOUN,masc sing'])
    False
    >>> _is_ambiguous(['NOUN masc,sing', 'NOUN,masc sing'], skip_space_ambiguity=False)
    True
    """
    if len(tags) < 2:
        return False

    if skip_space_ambiguity:
        # if space position differs then skip this ambiguity
        # XXX: this doesn't handle cases when space position difference
        # is not the only ambiguity
        space_pos = [tag.index(' ') if ' ' in tag else None
                     for tag in map(str, tags)]
        if len(space_pos) == len(set(space_pos)):
            return False

    return True


def _simplify_tag(tag, tag_replaces):
    tag = replace_redundant_grammemes(tag)
    return tag_replaces.get(tag, tag)


def _itertags(parsed_dict):
    for lex_id in parsed_dict.lexemes:
        for word, tag in parsed_dict.lexemes[lex_id]:
            yield tag

########NEW FILE########
__FILENAME__ = probability
# -*- coding: utf-8 -*-
"""
Module for estimating P(t|w) from partially annotated OpenCorpora XML dump
and saving this information to a file.

This module requires NLTK3 master, opencorpora-tools>=0.4.4 and dawg >= 0.7
packages for probability estimation and resulting file creation.
"""
from __future__ import absolute_import
from pymorphy2.opencorpora_dict.preprocess import tag2grammemes
from pymorphy2.dawg import ConditionalProbDistDAWG


def estimate_conditional_tag_probability(morph, corpus_filename):
    """
    Estimate P(t|w) based on OpenCorpora xml dump.

    Probability is estimated based on counts of disambiguated
    ambiguous words, using simple Laplace smoothing.
    """
    import nltk
    import opencorpora

    class _ConditionalProbDist(nltk.ConditionalProbDist):
        """
        This ConditionalProbDist subclass passes 'condition' variable to
        probdist_factory. See https://github.com/nltk/nltk/issues/500
        """
        def __init__(self, cfdist, probdist_factory):
            self._probdist_factory = probdist_factory
            for condition in cfdist:
                self[condition] = probdist_factory(cfdist[condition], condition)

    reader = opencorpora.CorpusReader(corpus_filename)

    ambiguous_words = (
        (w.lower(), tag2grammemes(t))
        for (w, t) in _disambiguated_words(reader)
        if len(morph.tag(w)) > 1
    )
    ambiguous_words = ((w, gr) for (w, gr) in ambiguous_words
                       if gr != set(['UNKN']))

    def probdist_factory(fd, condition):
        bins = max(len(morph.tag(condition)), fd.B())
        return nltk.LaplaceProbDist(fd, bins=bins)

    cfd = nltk.ConditionalFreqDist(ambiguous_words)
    cpd = _ConditionalProbDist(cfd, probdist_factory)
    return cpd, cfd


def build_cpd_dawg(morph, cpd, min_frequency):
    """
    Return conditional tag probability information encoded as DAWG.

    For each "interesting" word and tag the resulting DAWG
    stores ``"word:tag"`` key with ``probability*1000000`` integer value.
    """
    words = [word for (word, fd) in cpd.items()
             if fd.freqdist().N() >= min_frequency]

    prob_data = filter(
        lambda rec: not _all_the_same(rec[1]),
        ((word, _tag_probabilities(morph, word, cpd)) for word in words)
    )
    dawg_data = (
        ((word, tag), prob)
        for word, probs in prob_data
        for tag, prob in probs.items()
    )
    return ConditionalProbDistDAWG(dawg_data)


def _disambiguated_words(reader):
    return (
        (word, parses[0][1])
        for (word, parses) in reader.iter_parsed_words()
        if len(parses) == 1
    )


def _all_the_same(probs):
    return len(set(probs.values())) <= 1


def _parse_probabilities(morph, word, cpd):
    """
    Return probabilities of word parses
    according to CustomConditionalProbDist ``cpd``.
    """
    parses = morph.parse(word)
    probabilities = [cpd[word].prob(p.tag.grammemes) for p in parses]
    return list(zip(parses, probabilities))


def _tag_probabilities(morph, word, cpd):
    return dict(
        (p.tag, prob)
        for (p, prob) in _parse_probabilities(morph, word, cpd)
    )



########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-
"""
:mod:`pymorphy2.opencorpora_dict.storage` is a
module for saving and loading pymorphy2 dictionaries.
"""
from __future__ import absolute_import, unicode_literals
import datetime
import os
import logging
import collections
import itertools
import array
import struct

try:
    izip = itertools.izip
except AttributeError:
    izip = zip

import pymorphy2
from pymorphy2 import tagset
from pymorphy2 import dawg
from pymorphy2.constants import PARADIGM_PREFIXES, PREDICTION_PREFIXES
from pymorphy2.utils import json_write, json_read

logger = logging.getLogger(__name__)

CURRENT_FORMAT_VERSION = '2.4'

LoadedDictionary = collections.namedtuple('LoadedDictionary', [
    'meta', 'gramtab', 'suffixes', 'paradigms', 'words',
    'prediction_prefixes', 'prediction_suffixes_dawgs',
    'Tag', 'paradigm_prefixes']
)


def load_dict(path, gramtab_format='opencorpora-int'):
    """
    Load pymorphy2 dictionary.
    ``path`` is a folder name with dictionary data.
    """

    _f = lambda p: os.path.join(path, p)

    meta = _load_meta(_f('meta.json'))
    _assert_format_is_compatible(meta, path)

    Tag = _load_tag_class(gramtab_format, _f('grammemes.json'))

    str_gramtab = _load_gramtab(meta, gramtab_format, path)
    gramtab = [Tag(tag_str) for tag_str in str_gramtab]

    suffixes = json_read(_f('suffixes.json'))
    paradigm_prefixes = json_read(_f('paradigm-prefixes.json'))
    paradigms = _load_paradigms(_f('paradigms.array'))
    words = dawg.WordsDawg().load(_f('words.dawg'))

    prediction_prefixes = dawg.DAWG().load(_f('prediction-prefixes.dawg'))

    prediction_suffixes_dawgs = []
    for prefix_id in range(len(paradigm_prefixes)):
        fn = _f('prediction-suffixes-%s.dawg' % prefix_id)
        assert os.path.exists(fn)
        prediction_suffixes_dawgs.append(dawg.PredictionSuffixesDAWG().load(fn))

    return LoadedDictionary(meta, gramtab, suffixes, paradigms, words,
                            prediction_prefixes, prediction_suffixes_dawgs,
                            Tag, paradigm_prefixes)


def save_compiled_dict(compiled_dict, out_path):
    """
    Save a compiled_dict to ``out_path``
    ``out_path`` should be a name of folder where to put dictionaries.
    """
    logger.info("Saving...")
    _f = lambda path: os.path.join(out_path, path)

    json_write(_f('grammemes.json'), compiled_dict.parsed_dict.grammemes)

    gramtab_formats = {}
    for format, Tag in tagset.registry.items():
        Tag._init_grammemes(compiled_dict.parsed_dict.grammemes)
        new_gramtab = [Tag._from_internal_tag(tag) for tag in compiled_dict.gramtab]

        gramtab_name = "gramtab-%s.json" % format
        gramtab_formats[format] = gramtab_name

        json_write(_f(gramtab_name), new_gramtab)

    with open(_f('paradigms.array'), 'wb') as f:
        f.write(struct.pack(str("<H"), len(compiled_dict.paradigms)))
        for para in compiled_dict.paradigms:
            f.write(struct.pack(str("<H"), len(para)))
            para.tofile(f)

    json_write(_f('suffixes.json'), compiled_dict.suffixes)
    compiled_dict.words_dawg.save(_f('words.dawg'))

    for prefix_id, prediction_suffixes_dawg in enumerate(compiled_dict.prediction_suffixes_dawgs):
        prediction_suffixes_dawg.save(_f('prediction-suffixes-%s.dawg' % prefix_id))


    dawg.DAWG(PREDICTION_PREFIXES).save(_f('prediction-prefixes.dawg'))
    json_write(_f('paradigm-prefixes.json'), PARADIGM_PREFIXES)

    logger.debug("computing metadata..")

    def _dawg_len(dawg):
        return sum(1 for k in dawg.iterkeys())

    logger.debug('  words_dawg_len')
    words_dawg_len = _dawg_len(compiled_dict.words_dawg)
    logger.debug('  prediction_suffixes_dawgs_len')

    prediction_suffixes_dawg_lenghts = []
    for prediction_suffixes_dawg in compiled_dict.prediction_suffixes_dawgs:
        prediction_suffixes_dawg_lenghts.append(_dawg_len(prediction_suffixes_dawg))

    meta = [
        ['format_version', CURRENT_FORMAT_VERSION],
        ['pymorphy2_version', pymorphy2.__version__],
        ['compiled_at', datetime.datetime.utcnow().isoformat()],

        ['source', 'opencorpora.org'],
        ['source_version', compiled_dict.parsed_dict.version],
        ['source_revision', compiled_dict.parsed_dict.revision],
        ['source_lexemes_count', len(compiled_dict.parsed_dict.lexemes)],
        ['source_links_count', len(compiled_dict.parsed_dict.links)],

        ['gramtab_length', len(compiled_dict.gramtab)],
        ['gramtab_formats', gramtab_formats],
        ['paradigms_length', len(compiled_dict.paradigms)],
        ['suffixes_length', len(compiled_dict.suffixes)],

        ['words_dawg_length', words_dawg_len],
        ['prediction_options', compiled_dict.prediction_options],
        ['prediction_suffixes_dawg_lengths', prediction_suffixes_dawg_lenghts],
        ['prediction_prefixes_dawg_length', len(PREDICTION_PREFIXES)],
        ['paradigm_prefixes_length', len(PARADIGM_PREFIXES)],
    ]

    json_write(_f('meta.json'), meta, indent=4)


def _load_meta(filename):
    """ Load metadata. """
    meta = json_read(filename, parse_float=str)
    if hasattr(collections, 'OrderedDict'):
        return collections.OrderedDict(meta)
    return dict(meta)


def _load_tag_class(gramtab_format, grammemes_filename):
    """ Load and initialize Tag class (according to ``gramtab_format``). """
    if gramtab_format not in tagset.registry:
        raise ValueError("This gramtab format ('%s') is unsupported." % gramtab_format)

    # FIXME: clone the class
    Tag = tagset.registry[gramtab_format] #._clone_class()

    grammemes = json_read(grammemes_filename)
    Tag._init_grammemes(grammemes)

    return Tag


def _load_gramtab(meta, gramtab_format, path):
    """ Load gramtab (a list of tags) """
    gramtab_formats = meta.get('gramtab_formats', {})
    if gramtab_format not in gramtab_formats:
        raise ValueError("This gramtab format (%s) is unavailable; available formats: %s" % (gramtab_format, gramtab_formats.keys()))

    gramtab_filename = os.path.join(path, gramtab_formats[gramtab_format])
    return json_read(gramtab_filename)


def _load_paradigms(filename):
    """ Load paradigms data """
    paradigms = []
    with open(filename, 'rb') as f:
        paradigms_count = struct.unpack(str("<H"), f.read(2))[0]

        for x in range(paradigms_count):
            paradigm_len = struct.unpack(str("<H"), f.read(2))[0]

            para = array.array(str("H"))
            para.fromfile(f, paradigm_len)

            paradigms.append(para)
    return paradigms


def _assert_format_is_compatible(meta, path):
    """ Raise an exception if dictionary format is not compatible """
    format_version = str(meta.get('format_version', '0.0'))

    if '.' not in format_version:
        raise ValueError('Invalid format_version: %s' % format_version)

    major, minor = format_version.split('.')
    curr_major, curr_minor = CURRENT_FORMAT_VERSION.split('.')

    if major != curr_major:
        msg = ("Error loading dictionaries from %s: "
               "the format ('%s') is not supported; "
               "required format is '%s.x'.") % (path, format_version, curr_major)
        raise ValueError(msg)


########NEW FILE########
__FILENAME__ = wrapper
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division
import logging
from .storage import load_dict

logger = logging.getLogger(__name__)


class Dictionary(object):
    """
    OpenCorpora dictionary wrapper class.
    """

    def __init__(self, path):

        logger.info("Loading dictionaries from %s", path)

        self._data = load_dict(path)

        logger.info("format: %(format_version)s, revision: %(source_revision)s, updated: %(compiled_at)s", self._data.meta)

        # attributes from opencorpora_dict.storage.LoadedDictionary
        self.paradigms = self._data.paradigms
        self.gramtab = self._data.gramtab
        self.paradigm_prefixes = self._data.paradigm_prefixes
        self.suffixes = self._data.suffixes
        self.words = self._data.words
        self.prediction_prefixes = self._data.prediction_prefixes
        self.prediction_suffixes_dawgs = self._data.prediction_suffixes_dawgs
        self.meta = self._data.meta
        self.Tag = self._data.Tag

        # extra attributes
        self.path = path
        self.ee = self.words.compile_replaces({'е': 'ё'})

    def build_tag_info(self, para_id, idx):
        """
        Return tag as a string.
        """
        paradigm = self.paradigms[para_id]
        tag_info_offset = len(paradigm) // 3
        tag_id = paradigm[tag_info_offset + idx]
        return self.gramtab[tag_id]

    def build_paradigm_info(self, para_id):
        """
        Return a list of

            (prefix, tag, suffix)

        tuples representing the paradigm.
        """
        paradigm = self.paradigms[para_id]
        paradigm_len = len(paradigm) // 3
        res = []
        for idx in range(paradigm_len):
            prefix_id = paradigm[paradigm_len*2 + idx]
            prefix = self.paradigm_prefixes[prefix_id]

            suffix_id = paradigm[idx]
            suffix = self.suffixes[suffix_id]

            res.append(
                (prefix, self.build_tag_info(para_id, idx), suffix)
            )
        return res

    def build_normal_form(self, para_id, idx, fixed_word):
        """
        Build a normal form.
        """

        if idx == 0: # a shortcut: normal form is a word itself
            return fixed_word

        paradigm = self.paradigms[para_id]
        paradigm_len = len(paradigm) // 3

        stem = self.build_stem(paradigm, idx, fixed_word)

        normal_prefix_id = paradigm[paradigm_len*2 + 0]
        normal_suffix_id = paradigm[0]

        normal_prefix = self.paradigm_prefixes[normal_prefix_id]
        normal_suffix = self.suffixes[normal_suffix_id]

        return normal_prefix + stem + normal_suffix

    def build_stem(self, paradigm, idx, fixed_word):
        """
        Return word stem (given a word, paradigm and the word index).
        """
        paradigm_len = len(paradigm) // 3

        prefix_id = paradigm[paradigm_len*2 + idx]
        prefix = self.paradigm_prefixes[prefix_id]

        suffix_id = paradigm[idx]
        suffix = self.suffixes[suffix_id]

        if suffix:
            return fixed_word[len(prefix):-len(suffix)]
        else:
            return fixed_word[len(prefix):]

    def word_is_known(self, word, strict_ee=False):
        """
        Check if a ``word`` is in the dictionary.
        Pass ``strict_ee=True`` if ``word`` is guaranteed to
        have correct е/ё letters.

        .. note::

            Dictionary words are not always correct words;
            the dictionary also contains incorrect forms which
            are commonly used. So for spellchecking tasks this
            method should be used with extra care.

        """
        if strict_ee:
            return word in self.words
        else:
            return bool(self.words.similar_keys(word, self.ee))

    def iter_known_words(self, prefix=""):
        """
        Return an iterator over ``(word, tag, normal_form, para_id, idx)``
        tuples with dictionary words that starts with a given prefix
        (default empty prefix means "all words").
        """

        for word, (para_id, idx) in self.words.iteritems(prefix):
            tag = self.build_tag_info(para_id, idx)
            normal_form = self.build_normal_form(para_id, idx, word)
            yield word, tag, normal_form, para_id, idx


    def __repr__(self):
        return str("<%s>") % self.__class__.__name__



########NEW FILE########
__FILENAME__ = shapes
# -*- coding: utf-8 -*-
from __future__ import absolute_import
# unicode_literals future import is not needed and breaks 2.x tests

import re
import warnings
import unicodedata


_latin_letters_cache = {}
def is_latin_char(uchr):
    try:
        return _latin_letters_cache[uchr]
    except KeyError:
        if isinstance(uchr, bytes):
            uchr = uchr.decode('ascii')
        is_latin = 'LATIN' in unicodedata.name(uchr)
        return _latin_letters_cache.setdefault(uchr, is_latin)


def is_latin(token):
    """
    Return True if all token letters are latin and there is at
    least one latin letter in the token:

        >>> is_latin('foo')
        True
        >>> is_latin('123-FOO')
        True
        >>> is_latin('123')
        False
        >>> is_latin(':)')
        False
        >>> is_latin('')
        False

    """
    return (
        any(ch.isalpha() for ch in token) and
        all(is_latin_char(ch) for ch in token if ch.isalpha())
    )


def is_punctuation(token):
    """
    Return True if a word contains only spaces and punctuation marks
    and there is at least one punctuation mark:

        >>> is_punctuation(', ')
        True
        >>> is_punctuation('..!')
        True
        >>> is_punctuation('x')
        False
        >>> is_punctuation(' ')
        False
        >>> is_punctuation('')
        False

    """
    if isinstance(token, bytes):  # python 2.x ascii str
        token = token.decode('ascii')

    return (
        bool(token) and
        not token.isspace() and
        all(unicodedata.category(ch)[0] == 'P' for ch in token if not ch.isspace())
    )


# The regex is from "Dive into Python" book.
ROMAN_NUMBERS_RE = re.compile("""
    M{0,4}              # thousands - 0 to 4 M's
    (CM|CD|D?C{0,3})    # hundreds - 900 (CM), 400 (CD), 0-300 (0 to 3 C's),
                        #            or 500-800 (D, followed by 0 to 3 C's)
    (XC|XL|L?X{0,3})    # tens - 90 (XC), 40 (XL), 0-30 (0 to 3 X's),
                        #        or 50-80 (L, followed by 0 to 3 X's)
    (IX|IV|V?I{0,3})    # ones - 9 (IX), 4 (IV), 0-3 (0 to 3 I's),
                        #        or 5-8 (V, followed by 0 to 3 I's)
    $                   # end of string
""", re.VERBOSE | re.IGNORECASE)

def is_roman_number(token):
    """
    Return True if token looks like a Roman number:

        >>> is_roman_number('II')
        True
        >>> is_roman_number('IX')
        True
        >>> is_roman_number('XIIIII')
        False
        >>> is_roman_number('')
        False

    """
    if not token:
        return False
    return re.match(ROMAN_NUMBERS_RE, token) is not None


def restore_capitalization(word, example):
    """
    Make the capitalization of the ``word`` be the same as in ``example``:

        >>> restore_capitalization('bye', 'Hello')
        'Bye'
        >>> restore_capitalization('half-an-hour', 'Minute')
        'Half-An-Hour'
        >>> restore_capitalization('usa', 'IEEE')
        'USA'
        >>> restore_capitalization('pre-world', 'anti-World')
        'pre-World'
        >>> restore_capitalization('123-do', 'anti-IEEE')
        '123-DO'
        >>> restore_capitalization('123--do', 'anti--IEEE')
        '123--DO'

    In the alignment fails, the reminder is lower-cased:

        >>> restore_capitalization('foo-BAR-BAZ', 'Baz-Baz')
        'Foo-Bar-baz'
        >>> restore_capitalization('foo', 'foo-bar')
        'foo'

    .. note:

        Currently this function doesn't handle uppercase letters in
        the middle of the token (e.g. McDonald).

    """
    if '-' in example:
        results = []
        word_parts = word.split('-')
        example_parts = example.split('-')

        for i, part in enumerate(word_parts):
            if len(example_parts) > i:
                results.append(_make_the_same_case(part, example_parts[i]))
            else:
                results.append(part.lower())

        return '-'.join(results)

    return _make_the_same_case(word, example)


def restore_word_case(word, example):
    """ This function is renamed to ``restore_capitalization`` """
    warnings.warn(
        "`restore_word_case` function is renamed to `restore_capitalization`; "
        "old alias will be removed in future releases.",
    )
    return restore_capitalization(word, example)


def _make_the_same_case(word, example):
    if example.islower():
        return word.lower()
    elif example.isupper():
        return word.upper()
    elif example.istitle():
        return word.title()
    else:
        return word.lower()

########NEW FILE########
__FILENAME__ = tagset
# -*- coding: utf-8 -*-
"""
Utils for working with grammatical tags.
"""
from __future__ import absolute_import, unicode_literals
import collections
import threading

try:
    from sys import intern
except ImportError:
    # python 2.x has builtin ``intern`` function
    pass

# a bit of *heavy* magic...
class _select_grammeme_from(object):
    """
    Descriptor object for accessing grammemes of certain classes
    (e.g. number or voice).
    """
    def __init__(self, grammeme_set):
        self.grammeme_set = grammeme_set
        # ... are descriptors not magical enough?

        # In order to fight typos, raise an exception
        # if a result is compared to a grammeme which
        # is not in a set of allowed grammemes.
        _str = type("unicode string")

        class TypedGrammeme(_str):
            def __eq__(self, other):
                if other is None:
                    return False
                if other not in grammeme_set:
                    known_grammemes = ", ".join(grammeme_set)
                    raise ValueError("'%s' is not a valid grammeme for this attribute. Valid grammemes: %s" % (other, known_grammemes))
                return _str.__eq__(self, other)

            def __ne__(self, other):
                return not self.__eq__(other)

            def __hash__(self):
                return _str.__hash__(self)

        self.TypedGrammeme = TypedGrammeme

    def __get__(self, instance, owner):
        grammemes = self.grammeme_set & instance.grammemes

        if not grammemes:
            # XXX: type checks are not enforced in this case
            return None

        res = next(iter(grammemes))
        return self.TypedGrammeme(res) if owner.typed_grammemes else res


# Design notes: Tag objects are immutable, but the tag class is mutable.
class OpencorporaTag(object):
    """
    Wrapper class for OpenCorpora.org tags.

    .. warning::

        In order to work properly, the class has to be globally
        initialized with actual grammemes (using _init_grammemes method).

        Pymorphy2 initializes it when loading a dictionary;
        it may be not a good idea to use this class directly.
        If possible, use ``morph_analyzer.TagClass`` instead.

    Example::

        >>> from pymorphy2 import MorphAnalyzer
        >>> morph = MorphAnalyzer()
        >>> Tag = morph.TagClass  # get an initialzed Tag class
        >>> tag = Tag('VERB,perf,tran plur,impr,excl')
        >>> tag
        OpencorporaTag('VERB,perf,tran plur,impr,excl')

    Tag instances have attributes for accessing grammemes::

        >>> print(tag.POS)
        VERB
        >>> print(tag.number)
        plur
        >>> print(tag.case)
        None

    Available attributes are: POS, animacy, aspect, case, gender, involvement,
    mood, number, person, tense, transitivity and voice.

    You may check if a grammeme is in tag or if all grammemes
    from a given set are in tag::

        >>> 'perf' in tag
        True
        >>> 'nomn' in tag
        False
        >>> 'Geox' in tag
        False
        >>> set(['VERB', 'perf']) in tag
        True
        >>> set(['VERB', 'perf', 'sing']) in tag
        False

    In order to fight typos, for unknown grammemes an exception is raised::

        >>> 'foobar' in tag
        Traceback (most recent call last):
        ...
        ValueError: Grammeme is unknown: foobar
        >>> set(['NOUN', 'foo', 'bar']) in tag
        Traceback (most recent call last):
        ...
        ValueError: Grammemes are unknown: {'bar', 'foo'}

    This also works for attributes::

        >>> tag.POS == 'plur'
        Traceback (most recent call last):
        ...
        ValueError: 'plur' is not a valid grammeme for this attribute. Valid grammemes: ...

    """

    # Grammeme categories
    # (see http://opencorpora.org/dict.php?act=gram for a full set)
    # -------------------------------------------------------------

    PARTS_OF_SPEECH = frozenset([
        'NOUN',  # имя существительное
        'ADJF',  # имя прилагательное (полное)
        'ADJS',  # имя прилагательное (краткое)
        'COMP',  # компаратив
        'VERB',  # глагол (личная форма)
        'INFN',  # глагол (инфинитив)
        'PRTF',  # причастие (полное)
        'PRTS',  # причастие (краткое)
        'GRND',  # деепричастие
        'NUMR',  # числительное
        'ADVB',  # наречие
        'NPRO',  # местоимение-существительное
        'PRED',  # предикатив
        'PREP',  # предлог
        'CONJ',  # союз
        'PRCL',  # частица
        'INTJ',  # междометие
    ])

    ANIMACY = frozenset([
        'anim',  # одушевлённое
        'inan',  # неодушевлённое
    ])

    GENDERS = frozenset([
        'masc',  # мужской род
        'femn',  # женский род
        'neut',  # средний род
    ])

    NUMBERS = frozenset([
        'sing',  # единственное число
        'plur',  # множественное число
    ])

    CASES = frozenset([
        'nomn',  # именительный падеж
        'gent',  # родительный падеж
        'datv',  # дательный падеж
        'accs',  # винительный падеж
        'ablt',  # творительный падеж
        'loct',  # предложный падеж
        'voct',  # звательный падеж
        'gen1',  # первый родительный падеж
        'gen2',  # второй родительный (частичный) падеж
        'acc2',  # второй винительный падеж
        'loc1',  # первый предложный падеж
        'loc2',  # второй предложный (местный) падеж
    ])

    ASPECTS = frozenset([
        'perf',  # совершенный вид
        'impf',  # несовершенный вид
    ])

    TRANSITIVITY = frozenset([
        'tran',  # переходный
        'intr',  # непереходный
    ])

    PERSONS = frozenset([
        '1per',  # 1 лицо
        '2per',  # 2 лицо
        '3per',  # 3 лицо
    ])

    TENSES = frozenset([
        'pres',  # настоящее время
        'past',  # прошедшее время
        'futr',  # будущее время
    ])

    MOODS = frozenset([
        'indc',  # изъявительное наклонение
        'impr',  # повелительное наклонение
    ])

    VOICES = frozenset([
        'actv',  # действительный залог
        'pssv',  # страдательный залог
    ])

    INVOLVEMENT = frozenset([
        'incl',  # говорящий включён в действие
        'excl',  # говорящий не включён в действие
    ])

    # Set this to False (as a class attribute) to disable strict
    # grammeme type checking for tag.POS, tag.voice, etc. attributes.
    # Without type checks comparisons are about 2x faster.
    typed_grammemes = True

    # Tag format identifier
    # (compatible with https://github.com/kmike/russian-tagsets)
    # ----------------------------------------------------------
    FORMAT = 'opencorpora-int'


    # Helper attributes for inflection/declension routines
    # ----------------------------------------------------
    _NON_PRODUCTIVE_GRAMMEMES = set(['NUMR', 'NPRO', 'PRED', 'PREP',
                                     'CONJ', 'PRCL', 'INTJ', 'Apro'])
    _EXTRA_INCOMPATIBLE = {  # XXX: is it a good idea to have these rules?
        'plur': set(['GNdr']),
        # XXX: how to use rules from OpenCorpora?
        # (they have "lexeme/form" separation)
    }
    _GRAMMEME_INDICES = collections.defaultdict(int)
    _GRAMMEME_INCOMPATIBLE = collections.defaultdict(set)
    _LAT2CYR = None
    _CYR2LAT = None
    KNOWN_GRAMMEMES = set()

    _NUMERAL_AGREEMENT_GRAMMEMES = (
        set(['sing', 'nomn']),
        set(['sing', 'accs']),
        set(['sing', 'gent']),
        set(['plur', 'nomn']),
        set(['plur', 'gent']),
    )

    RARE_CASES = {
        'gen1': 'gent',
        'gen2': 'gent',
        'acc1': 'accs',
        'acc2': 'accs',
        'loc1': 'loct',
        'loc2': 'loct',
        'voct': 'nomn'
    }

    __slots__ = ['_grammemes_tuple', '_grammemes_cache', '_str', '_POS',
                 '_cyr', '_cyr_grammemes_cache']

    def __init__(self, tag):
        self._str = tag
        # XXX: we loose information about which grammemes
        # belongs to lexeme and which belongs to form
        # (but this information seems useless for pymorphy2).

        # Hacks for better memory usage:
        # - store grammemes in a tuple and build a set only when needed;
        # - use byte strings for grammemes under Python 2.x;
        # - grammemes are interned.
        grammemes = tag.replace(' ', ',', 1).split(',')
        grammemes_tuple = tuple([intern(str(g)) for g in grammemes])

        self._assert_grammemes_are_known(set(grammemes_tuple))

        self._grammemes_tuple = grammemes_tuple
        self._POS = self._grammemes_tuple[0]
        self._grammemes_cache = None
        self._cyr_grammemes_cache = None
        self._cyr = None

    # attributes for grammeme categories
    POS = _select_grammeme_from(PARTS_OF_SPEECH)
    animacy = _select_grammeme_from(ANIMACY)
    aspect = _select_grammeme_from(ASPECTS)
    case = _select_grammeme_from(CASES)
    gender = _select_grammeme_from(GENDERS)
    involvement = _select_grammeme_from(INVOLVEMENT)
    mood = _select_grammeme_from(MOODS)
    number = _select_grammeme_from(NUMBERS)
    person = _select_grammeme_from(PERSONS)
    tense = _select_grammeme_from(TENSES)
    transitivity = _select_grammeme_from(TRANSITIVITY)
    voice = _select_grammeme_from(VOICES)

    @property
    def grammemes(self):
        """ A frozenset with grammemes for this tag. """
        if self._grammemes_cache is None:
            self._grammemes_cache = frozenset(self._grammemes_tuple)
        return self._grammemes_cache

    @property
    def grammemes_cyr(self):
        """ A frozenset with Cyrillic grammemes for this tag. """
        if self._cyr_grammemes_cache is None:
            cyr_grammemes = [self._LAT2CYR[g] for g in self._grammemes_tuple]
            self._cyr_grammemes_cache = frozenset(cyr_grammemes)
        return self._cyr_grammemes_cache

    @property
    def cyr_repr(self):
        """ Cyrillic representation of this tag """
        if self._cyr is None:
            self._cyr = self.lat2cyr(self)
        return self._cyr

    @classmethod
    def cyr2lat(cls, tag_or_grammeme):
        """ Return Latin representation for ``tag_or_grammeme`` string """
        return _translate_tag(tag_or_grammeme, cls._CYR2LAT)

    @classmethod
    def lat2cyr(cls, tag_or_grammeme):
        """ Return Cyrillic representation for ``tag_or_grammeme`` string """
        return _translate_tag(tag_or_grammeme, cls._LAT2CYR)

    def __contains__(self, grammeme):

        # {'NOUN', 'sing'} in tag
        if isinstance(grammeme, (set, frozenset)):
            if grammeme <= self.grammemes:
                return True
            self._assert_grammemes_are_known(grammeme)
            return False

        # 'NOUN' in tag
        if grammeme in self.grammemes:
            return True
        else:
            if not self.grammeme_is_known(grammeme):
                raise ValueError("Grammeme is unknown: %s" % grammeme)
            return False

    # FIXME: __repr__ and __str__ always return unicode,
    # but they should return a byte string under Python 2.x.
    def __str__(self):
        return self._str

    def __repr__(self):
        return "OpencorporaTag('%s')" % self


    def __eq__(self, other):
        return self._grammemes_tuple == other._grammemes_tuple

    def __ne__(self, other):
        return self._grammemes_tuple != other._grammemes_tuple

    def __lt__(self, other):
        return self._grammemes_tuple < other._grammemes_tuple

    def __gt__(self, other):
        return self._grammemes_tuple > other._grammemes_tuple

    def __hash__(self):
        return hash(self._grammemes_tuple)

    def __len__(self):
        return len(self._grammemes_tuple)

    def __reduce__(self):
        return self.__class__, (self._str,), None


    def is_productive(self):
        return not self.grammemes & self._NON_PRODUCTIVE_GRAMMEMES

    def _is_unknown(self):
        return self._POS not in self.PARTS_OF_SPEECH

    @classmethod
    def grammeme_is_known(cls, grammeme):
        cls._assert_grammemes_initialized()
        return grammeme in cls.KNOWN_GRAMMEMES

    @classmethod
    def _assert_grammemes_are_known(cls, grammemes):
        if not grammemes <= cls.KNOWN_GRAMMEMES:
            cls._assert_grammemes_initialized()
            unknown = grammemes - cls.KNOWN_GRAMMEMES
            unknown_repr = ", ".join(["'%s'" % g for g in sorted(unknown)])
            raise ValueError("Grammemes are unknown: {%s}" % unknown_repr)

    @classmethod
    def _assert_grammemes_initialized(cls):
        if not cls.KNOWN_GRAMMEMES:
            msg = "The class was not properly initialized."
            raise RuntimeError(msg)

    def updated_grammemes(self, required):
        """
        Return a new set of grammemes with ``required`` grammemes added
        and incompatible grammemes removed.
        """
        new_grammemes = self.grammemes | required
        for grammeme in required:
            if not self.grammeme_is_known(grammeme):
                raise ValueError("Unknown grammeme: %s" % grammeme)
            new_grammemes -= self._GRAMMEME_INCOMPATIBLE[grammeme]
        return new_grammemes

    @classmethod
    def fix_rare_cases(cls, grammemes):
        """
        Replace rare cases (loc2/voct/...) with common ones (loct/nomn/...).
        """
        return frozenset(cls.RARE_CASES.get(g, g) for g in grammemes)

    @classmethod
    def add_grammemes_to_known(cls, lat, cyr):
        cls.KNOWN_GRAMMEMES.add(lat)
        cls._LAT2CYR[lat] = cyr
        cls._CYR2LAT[cyr] = lat

    @classmethod
    def _init_grammemes(cls, dict_grammemes):
        """
        Initialize various class attributes with grammeme
        information obtained from XML dictionary.

        ``dict_grammemes`` is a list of tuples::

            [
                (name, parent, alias, description),
                ...
            ]

        """
        with threading.RLock():
            cls.KNOWN_GRAMMEMES = set()
            cls._CYR2LAT = {}
            cls._LAT2CYR = {}
            for name, parent, alias, description in dict_grammemes:
                cls.add_grammemes_to_known(name, alias)

            gr = dict((name, parent) for (name, parent, alias, description) in dict_grammemes)

            # figure out parents & children
            children = collections.defaultdict(set)
            for index, (name, parent, alias, description) in enumerate(dict_grammemes):
                if parent:
                    children[parent].add(name)
                if gr.get(parent, None):  # parent's parent
                    children[gr[parent]].add(name)

            # expand EXTRA_INCOMPATIBLE
            for grammeme, g_set in cls._EXTRA_INCOMPATIBLE.items():
                for g in g_set.copy():
                    g_set.update(children[g])

            # fill GRAMMEME_INDICES and GRAMMEME_INCOMPATIBLE
            for index, (name, parent, alias, description) in enumerate(dict_grammemes):
                cls._GRAMMEME_INDICES[name] = index
                incompatible = cls._EXTRA_INCOMPATIBLE.get(name, set())
                incompatible = (incompatible | children[parent]) - set([name])

                cls._GRAMMEME_INCOMPATIBLE[name] = frozenset(incompatible)

    # XXX: do we still need these methods?
    @classmethod
    def _from_internal_tag(cls, tag):
        """ Return tag string given internal tag string """
        return tag

    @classmethod
    def _from_internal_grammeme(cls, grammeme):
        return grammeme

    def numeral_agreement_grammemes(self, num):
        if (num % 10 == 1) and (num % 100 != 11):
            index = 0
        elif (num % 10 >= 2) and (num % 10 <= 4) and (num % 100 < 10 or num % 100 >= 20):
            index = 1
        else:
            index = 2

        if self.POS not in ('NOUN', 'ADJF', 'PRTF'):
            return set([])

        if self.POS == 'NOUN' and self.case not in ('nomn', 'accs'):
            if index == 0:
                grammemes = set(['sing', self.case])
            else:
                grammemes = set(['plur', self.case])
        elif index == 0:
            if self.case == 'nomn':
                grammemes = self._NUMERAL_AGREEMENT_GRAMMEMES[0]
            else:
                grammemes = self._NUMERAL_AGREEMENT_GRAMMEMES[1]
        elif self.POS == 'NOUN' and index == 1:
            grammemes = self._NUMERAL_AGREEMENT_GRAMMEMES[2]
        elif self.POS in ('ADJF', 'PRTF') and self.gender == 'femn' and index == 1:
            grammemes = self._NUMERAL_AGREEMENT_GRAMMEMES[3]
        else:
            grammemes = self._NUMERAL_AGREEMENT_GRAMMEMES[4]
        return grammemes

    #@classmethod
    #def _clone_class(cls):
    #    Tag = type(cls.__name__, (cls,), {
    #         'KNOWN_GRAMMEMES': cls.KNOWN_GRAMMEMES.copy(),
    #    })
    #    # copyreg.pickle(Tag, pickle_tag)
    #    return Tag



class CyrillicOpencorporaTag(OpencorporaTag):
    """
    Tag class that uses Cyrillic tag names.

    .. warning::

        This class is experimental and incomplete, do not use
        it because it may be removed in future!
    """

    FORMAT = 'opencorpora-ext'

    _GRAMMEME_ALIAS_MAP = dict()

    @classmethod
    def _from_internal_tag(cls, tag):
        for name, alias in cls._GRAMMEME_ALIAS_MAP.items():
            if alias:
                tag = tag.replace(name, alias)
        return tag

    @classmethod
    def _from_internal_grammeme(cls, grammeme):
        return cls._GRAMMEME_ALIAS_MAP.get(grammeme, grammeme)

    @classmethod
    def _init_grammemes(cls, dict_grammemes):
        """
        Initialize various class attributes with grammeme
        information obtained from XML dictionary.
        """
        cls._init_alias_map(dict_grammemes)
        super(CyrillicOpencorporaTag, cls)._init_grammemes(dict_grammemes)

        GRAMMEME_INDICES = collections.defaultdict(int)
        for name, idx in cls._GRAMMEME_INDICES.items():
            GRAMMEME_INDICES[cls._from_internal_grammeme(name)] = idx
        cls._GRAMMEME_INDICES = GRAMMEME_INDICES

        GRAMMEME_INCOMPATIBLE = collections.defaultdict(set)
        for name, value in cls._GRAMMEME_INCOMPATIBLE.items():
            GRAMMEME_INCOMPATIBLE[cls._from_internal_grammeme(name)] = set([
                cls._from_internal_grammeme(gr) for gr in value
            ])
        cls._GRAMMEME_INCOMPATIBLE = GRAMMEME_INCOMPATIBLE

        cls._NON_PRODUCTIVE_GRAMMEMES = set([
            cls._from_internal_grammeme(gr) for gr in cls._NON_PRODUCTIVE_GRAMMEMES
        ])

    @classmethod
    def _init_alias_map(cls, dict_grammemes):
        for name, parent, alias, description in dict_grammemes:
            cls._GRAMMEME_ALIAS_MAP[name] = alias


def _translate_tag(tag, mapping):
    """
    Translate ``tag`` string according to ``mapping``, assuming grammemes
    are separated by commas or whitespaces. Commas/whitespaces positions
    are preserved.
    """
    if isinstance(tag, OpencorporaTag):
        tag = str(tag)
    return " ".join([
        _translate_comma_separated(whitespace_separated_part, mapping)
        for whitespace_separated_part in tag.split()
    ])


def _translate_comma_separated(tag_part, mapping):
    grammemes = [mapping.get(tok, tok) for tok in tag_part.split(',')]
    return ",".join(grammemes)


registry = dict()

for tag_type in [CyrillicOpencorporaTag, OpencorporaTag]:
    registry[tag_type.FORMAT] = tag_type

########NEW FILE########
__FILENAME__ = test_suite_generator
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
import collections
import copy
import re
import codecs

from pymorphy2.opencorpora_dict.parse import parse_opencorpora_xml
from pymorphy2.utils import combinations_of_all_lengths

logger = logging.getLogger(__name__)


def _get_word_parses(lexemes):
    word_parses = collections.defaultdict(list) # word -> possible tags

    for index, lex_id in enumerate(lexemes):
        lexeme = lexemes[lex_id]
        for word, tag in lexeme:
            word_parses[word].append(tag)

    return word_parses


def _add_ee_parses(word_parses):

    def replace_chars(word, positions, replacement):
        chars = list(word)
        for pos in positions:
            chars[pos] = replacement
        return "".join(chars)

    def variants_with_missing_umlauts(word):
        umlaut_positions = [m.start() for m in re.finditer('ё', word, re.U)]
        for positions in combinations_of_all_lengths(umlaut_positions):
            yield replace_chars(word, positions, 'е')


    _word_parses = copy.deepcopy(word_parses)

    for word in word_parses:
        parses = word_parses[word]

        for word_variant in variants_with_missing_umlauts(word):
            _word_parses[word_variant].extend(parses)

    return _word_parses


def _get_test_suite(word_parses, word_limit=100):
    """
    Limit word_parses to ``word_limit`` words per tag.
    """
    gramtab = collections.defaultdict(int)  # tagset -> number of stored items
    result = list()
    for word in word_parses:
        tags = word_parses[word]
        for tag in tags:
            gramtab[tag] += 1
        if any(gramtab[tag] < word_limit for tag in tags):
            result.append((word, tags))

    return result


def _save_test_suite(path, suite, revision):
    with codecs.open(path, 'w', 'utf8') as f:
        f.write("%s\n" % revision)
        for word, parses in suite:
            txt = "|".join([word]+parses) +'\n'
            f.write(txt)


def make_test_suite(opencorpora_dict_path, out_path, word_limit=100):
    """
    Extract test data from OpenCorpora .xml dictionary (at least
    ``word_limit`` words for each distinct gram. tag) and save it to a file.
    """
    logger.debug('loading dictionary to memory...')
    parsed_dict = parse_opencorpora_xml(opencorpora_dict_path)

    logger.debug('preparing...')
    parses = _get_word_parses(parsed_dict.lexemes)

    logger.debug('dictionary size: %d', len(parses))

    logger.debug('handling umlauts...')
    parses = _add_ee_parses(parses)
    logger.debug('dictionary size: %d', len(parses))

    logger.debug('building test suite...')
    suite = _get_test_suite(parses, word_limit)

    logger.debug('test suite size: %d', len(suite))

    logger.debug('saving...')
    _save_test_suite(out_path, suite, parsed_dict.revision)

########NEW FILE########
__FILENAME__ = tokenizers
# -*- coding: utf-8 -*-
import re
GROUPING_SPACE_REGEX = re.compile('([^\w_-]|[+])', re.U)

def simple_word_tokenize(text):
    """
    Split text into tokens. Don't split by hyphen.
    """
    return [t for t in GROUPING_SPACE_REGEX.split(text)
            if t and not t.isspace()]

########NEW FILE########
__FILENAME__ = abbreviations
# -*- coding: utf-8 -*-
"""
Analyzer units for abbreviated words
------------------------------------
"""
from __future__ import absolute_import, unicode_literals, division
from pymorphy2.units.base import BaseAnalyzerUnit


class _InitialsAnalyzer(BaseAnalyzerUnit):
    SCORE = 0.1
    LETTERS = set('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ')
    TAG_PATTERN = None

    def __init__(self, morph):
        if self.TAG_PATTERN is None:
            raise ValueError("Define TAG_PATTERN in a subclass")

        super(_InitialsAnalyzer, self).__init__(morph)

        if 'Init' not in self.morph.TagClass.KNOWN_GRAMMEMES:
            self.morph.TagClass.add_grammemes_to_known('Init', 'иниц')

        self._tags = self._get_gender_case_tags(self.TAG_PATTERN)

    def _get_gender_case_tags(self, pattern):
        return [
            self.morph.TagClass(pattern % {'gender': gender, 'case': case})
            for gender in ['masc', 'femn']
            for case in ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct']
        ]

    def parse(self, word, word_lower, seen_parses):
        if word not in self.LETTERS:
            return []
        return [
            (word_lower, tag, word_lower, self.SCORE, ((self, word),))
            for tag in self._tags
        ]

    def tag(self, word, word_lower, seen_tags):
        if word not in self.LETTERS:
            return []
        return self._tags[:]


class AbbreviatedFirstNameAnalyzer(_InitialsAnalyzer):
    TAG_PATTERN = 'NOUN,anim,%(gender)s,Sgtm,Name,Fixd,Abbr,Init sing,%(case)s'

    def __init__(self, morph):
        super(AbbreviatedFirstNameAnalyzer, self).__init__(morph)
        self._tags_masc = [tag for tag in self._tags if 'masc' in tag]
        self._tags_femn = [tag for tag in self._tags if 'femn' in tag]
        assert self._tags_masc + self._tags_femn == self._tags

    def get_lexeme(self, form):
        # 2 lexemes: masc and femn
        fixed_word, form_tag, normal_form, score, methods_stack = form
        tags = self._tags_masc if 'masc' in form_tag else self._tags_femn
        return [
            (fixed_word, tag, normal_form, score, methods_stack)
            for tag in tags
        ]

    def normalized(self, form):
        # don't normalize female names to male names
        fixed_word, form_tag, normal_form, score, methods_stack = form
        tags = self._tags_masc if 'masc' in form_tag else self._tags_femn
        return fixed_word, tags[0], normal_form, score, methods_stack


class AbbreviatedPatronymicAnalyzer(_InitialsAnalyzer):
    TAG_PATTERN = 'NOUN,anim,%(gender)s,Sgtm,Patr,Fixd,Abbr,Init sing,%(case)s'

    def get_lexeme(self, form):
        fixed_word, _, normal_form, score, methods_stack = form
        return [
            (fixed_word, tag, normal_form, score, methods_stack)
            for tag in self._tags
        ]

    def normalized(self, form):
        fixed_word, _, normal_form, score, methods_stack = form
        return fixed_word, self._tags[0], normal_form, score, methods_stack

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division
from pymorphy2.units.utils import without_last_method, append_method


class BaseAnalyzerUnit(object):

    def __init__(self, morph):
        """
        :type morph: pymorphy2.analyzer.MorphAnalyzer
        :type self.dict: pymorphy2.analyzer.Dictionary
        """
        self.morph = morph
        self.dict = morph.dictionary

    def parse(self, word, word_lower, seen_parses):
        raise NotImplementedError()

    def tag(self, word, word_lower, seen_tags):
        raise NotImplementedError()

    def __repr__(self):
        return str("<%s>") % self.__class__.__name__


class AnalogyAnalizerUnit(BaseAnalyzerUnit):

    def normalized(self, form):
        base_analyzer, this_method = self._method_info(form)
        return self._normalized(form, base_analyzer, this_method)

    def _normalized(self, form, base_analyzer, this_method):
        normalizer = self.normalizer(form, this_method)

        form = without_last_method(next(normalizer))
        normal_form = normalizer.send(base_analyzer.normalized(form))
        return append_method(normal_form, this_method)

    def get_lexeme(self, form):
        base_analyzer, this_method = self._method_info(form)
        return self._get_lexeme(form, base_analyzer, this_method)

    def _get_lexeme(self, form, base_analyzer, this_method):
        lexemizer = self.lexemizer(form, this_method)
        form = without_last_method(next(lexemizer))
        lexeme = lexemizer.send(base_analyzer.get_lexeme(form))
        return [append_method(f, this_method) for f in lexeme]

    def normalizer(self, form, this_method):
        """ A coroutine for normalization """

        # 1. undecorate form:
        # form = undecorate(form)

        # 2. get normalized version of undecorated form:
        normal_form = yield form

        # 3. decorate the normalized version:
        # normal_form = decorate(normal_form)

        # 4. return the result
        yield normal_form

    def lexemizer(self, form, this_method):
        """ A coroutine for preparing lexemes """
        lexeme = yield form
        yield lexeme

    def _method_info(self, form):
        methods_stack = form[4]
        base_method, this_method = methods_stack[-2:]
        base_analyzer = base_method[0]
        return base_analyzer, this_method

########NEW FILE########
__FILENAME__ = by_analogy
# -*- coding: utf-8 -*-
"""
Analogy analyzer units
----------------------

This module provides analyzer units that analyzes unknown words by looking
at how similar known words are analyzed.

"""

from __future__ import absolute_import, unicode_literals, division

import operator

from pymorphy2.units.base import AnalogyAnalizerUnit
from pymorphy2.units.by_lookup import DictionaryAnalyzer
from pymorphy2.units.utils import (add_parse_if_not_seen, add_tag_if_not_seen,
                                   without_fixed_prefix, with_prefix)
from pymorphy2.utils import word_splits

_cnt_getter = operator.itemgetter(3)


class _PrefixAnalyzer(AnalogyAnalizerUnit):

    def normalizer(self, form, this_method):
        prefix = this_method[1]
        normal_form = yield without_fixed_prefix(form, len(prefix))
        yield with_prefix(normal_form, prefix)

    def lexemizer(self, form, this_method):
        prefix = this_method[1]
        lexeme = yield without_fixed_prefix(form, len(prefix))
        yield [with_prefix(f, prefix) for f in lexeme]


class KnownPrefixAnalyzer(_PrefixAnalyzer):
    """
    Parse the word by checking if it starts with a known prefix
    and parsing the reminder.

    Example: псевдокошка -> (псевдо) + кошка.
    """
    ESTIMATE_DECAY = 0.75
    MIN_REMINDER_LENGTH = 3

    def parse(self, word, word_lower, seen_parses):
        result = []
        for prefix, unprefixed_word in self.possible_splits(word_lower):
            method = (self, prefix)

            parses = self.morph.parse(unprefixed_word)
            for fixed_word, tag, normal_form, score, methods_stack in parses:

                if not tag.is_productive():
                    continue

                parse = (
                    prefix + fixed_word,
                    tag,
                    prefix + normal_form,
                    score * self.ESTIMATE_DECAY,
                    methods_stack + (method,)
                )

                add_parse_if_not_seen(parse, result, seen_parses)

        return result

    def tag(self, word, word_lower, seen_tags):
        result = []
        for prefix, unprefixed_word in self.possible_splits(word_lower):
            for tag in self.morph.tag(unprefixed_word):
                if not tag.is_productive():
                    continue
                add_tag_if_not_seen(tag, result, seen_tags)
        return result

    def possible_splits(self, word):
        word_prefixes = self.dict.prediction_prefixes.prefixes(word)
        word_prefixes.sort(key=len, reverse=True)
        for prefix in word_prefixes:
            unprefixed_word = word[len(prefix):]

            if len(unprefixed_word) < self.MIN_REMINDER_LENGTH:
                continue

            yield prefix, unprefixed_word


class UnknownPrefixAnalyzer(_PrefixAnalyzer):
    """
    Parse the word by parsing only the word suffix
    (with restrictions on prefix & suffix lengths).

    Example: байткод -> (байт) + код

    """
    ESTIMATE_DECAY = 0.5

    def __init__(self, morph):
        super(AnalogyAnalizerUnit, self).__init__(morph)
        self.dict_analyzer = DictionaryAnalyzer(morph)

    def parse(self, word, word_lower, seen_parses):
        result = []
        for prefix, unprefixed_word in word_splits(word_lower):

            method = (self, prefix)

            parses = self.dict_analyzer.parse(unprefixed_word, unprefixed_word, seen_parses)
            for fixed_word, tag, normal_form, score, methods_stack in parses:

                if not tag.is_productive():
                    continue

                parse = (
                    prefix + fixed_word,
                    tag,
                    prefix + normal_form,
                    score * self.ESTIMATE_DECAY,
                    methods_stack + (method,)
                )
                add_parse_if_not_seen(parse, result, seen_parses)

        return result

    def tag(self, word, word_lower, seen_tags):
        result = []
        for _, unprefixed_word in word_splits(word_lower):

            tags = self.dict_analyzer.tag(unprefixed_word, unprefixed_word, seen_tags)
            for tag in tags:

                if not tag.is_productive():
                    continue

                add_tag_if_not_seen(tag, result, seen_tags)

        return result


class KnownSuffixAnalyzer(AnalogyAnalizerUnit):
    """
    Parse the word by checking how the words with similar suffixes
    are parsed.

    Example: бутявкать -> ...вкать

    """
    min_word_length = 4
    ESTIMATE_DECAY = 0.5

    class FakeDictionary(DictionaryAnalyzer):
        """ This is just a DictionaryAnalyzer with different __repr__ """
        pass

    def __init__(self, morph):
        super(KnownSuffixAnalyzer, self).__init__(morph)

        self._paradigm_prefixes = list(reversed(list(enumerate(self.dict.paradigm_prefixes))))
        max_suffix_length = self.dict.meta['prediction_options']['max_suffix_length']
        self._prediction_splits = list(reversed(range(1, max_suffix_length+1)))

        self.fake_dict = self.FakeDictionary(morph)

    def parse(self, word, word_lower, seen_parses):
        result = []
        if len(word) < self.min_word_length:
            return result

        # smoothing; XXX: isn't max_cnt better?
        # or maybe use a proper discounting?
        total_counts = [1] * len(self._paradigm_prefixes)

        for prefix_id, prefix, suffixes_dawg in self._possible_prefixes(word_lower):

            for i in self._prediction_splits:

                # XXX: this should be counted once, not for each prefix
                word_start, word_end = word_lower[:-i], word_lower[-i:]

                para_data = suffixes_dawg.similar_items(word_end, self.dict.ee)
                for fixed_suffix, parses in para_data:

                    fixed_word = word_start + fixed_suffix

                    for cnt, para_id, idx in parses:
                        tag = self.dict.build_tag_info(para_id, idx)

                        # skip non-productive tags
                        if not tag.is_productive():
                            continue

                        total_counts[prefix_id] += cnt

                        # avoid duplicate parses
                        reduced_parse = fixed_word, tag, para_id
                        if reduced_parse in seen_parses:
                            continue
                        seen_parses.add(reduced_parse)

                        # ok, build the result
                        normal_form = self.dict.build_normal_form(para_id, idx, fixed_word)
                        methods = (
                            (self.fake_dict, fixed_word, para_id, idx),
                            (self, fixed_suffix),
                        )
                        parse = (cnt, fixed_word, tag, normal_form, prefix_id, methods)
                        result.append(parse)

                if total_counts[prefix_id] > 1:
                    break

        result = [
            (fixed_word, tag, normal_form, cnt/total_counts[prefix_id] * self.ESTIMATE_DECAY, methods_stack)
            for (cnt, fixed_word, tag, normal_form, prefix_id, methods_stack) in result
        ]
        result.sort(key=_cnt_getter, reverse=True)
        return result

    def tag(self, word, word_lower, seen_tags):
        # XXX: the result order may be different from
        # ``self.parse(...)``.

        result = []
        if len(word) < self.min_word_length:
            return result

        for prefix_id, prefix, suffixes_dawg in self._possible_prefixes(word_lower):

            for i in self._prediction_splits:

                # XXX: end should be counted once, not for each prefix
                end = word_lower[-i:]

                para_data = suffixes_dawg.similar_items(end, self.dict.ee)
                found = False

                for fixed_suffix, parses in para_data:
                    for cnt, para_id, idx in parses:

                        tag = self.dict.build_tag_info(para_id, idx)

                        if not tag.is_productive():
                            continue

                        found = True
                        if tag in seen_tags:
                            continue
                        seen_tags.add(tag)
                        result.append((cnt, tag))

                if found:
                    break

        result.sort(reverse=True)
        return [tag for cnt, tag in result]

    def _possible_prefixes(self, word):
        for prefix_id, prefix in self._paradigm_prefixes:
            if not word.startswith(prefix):
                continue

            suffixes_dawg = self.dict.prediction_suffixes_dawgs[prefix_id]
            yield prefix_id, prefix, suffixes_dawg

########NEW FILE########
__FILENAME__ = by_hyphen
# -*- coding: utf-8 -*-
"""
Analyzer units for unknown words with hyphens
---------------------------------------------
"""

from __future__ import absolute_import, unicode_literals, division

from pymorphy2.units.base import BaseAnalyzerUnit, AnalogyAnalizerUnit
from pymorphy2.units.utils import (add_parse_if_not_seen, add_tag_if_not_seen,
                                   with_suffix, without_fixed_suffix,
                                   with_prefix, without_fixed_prefix,
                                   replace_methods_stack)


class HyphenSeparatedParticleAnalyzer(AnalogyAnalizerUnit):
    """
    Parse the word by analyzing it without
    a particle after a hyphen.

    Example: смотри-ка -> смотри + "-ка".

    .. note::

        This analyzer doesn't remove particles from the result
        so for normalization you may need to handle
        particles at tokenization level.

    """
    ESTIMATE_DECAY = 0.9

    # XXX: maybe the code can be made faster by compiling this list to a DAWG?
    PARTICLES_AFTER_HYPHEN = [
        "-то", "-ка", "-таки", "-де", "-тко", "-тка", "-с", "-ста",
    ]

    def parse(self, word, word_lower, seen_parses):

        result = []
        for unsuffixed_word, particle in self.possible_splits(word_lower):
            method = (self, particle)

            for fixed_word, tag, normal_form, score, methods_stack in self.morph.parse(unsuffixed_word):
                parse = (
                    fixed_word+particle,
                    tag,
                    normal_form+particle,
                    score*self.ESTIMATE_DECAY,
                    methods_stack+(method,)
                )
                add_parse_if_not_seen(parse, result, seen_parses)

            # If a word ends with with one of the particles,
            # it can't ends with an another.
            break

        return result

    def tag(self, word, word_lower, seen_tags):
        result = []
        for unsuffixed_word, particle in self.possible_splits(word_lower):
            result.extend(self.morph.tag(unsuffixed_word))
            # If a word ends with with one of the particles,
            # it can't ends with an another.
            break

        return result

    def possible_splits(self, word):
        if '-' not in word:
            return

        for particle in self.PARTICLES_AFTER_HYPHEN:
            if not word.endswith(particle):
                continue

            unsuffixed_word = word[:-len(particle)]
            if not unsuffixed_word:
                continue

            yield unsuffixed_word, particle

    def normalizer(self, form, this_method):
        particle = this_method[1]
        normal_form = yield without_fixed_suffix(form, len(particle))
        yield with_suffix(normal_form, particle)

    def lexemizer(self, form, this_method):
        particle = this_method[1]
        lexeme = yield without_fixed_suffix(form, len(particle))
        yield [with_suffix(f, particle) for f in lexeme]


class HyphenAdverbAnalyzer(BaseAnalyzerUnit):
    """
    Detect adverbs that starts with "по-".

    Example: по-западному
    """
    ESTIMATE_DECAY = 0.7

    def __init__(self, morph):
        super(HyphenAdverbAnalyzer, self).__init__(morph)
        self._tag = self.morph.TagClass('ADVB')

    def parse(self, word, word_lower, seen_parses):
        if not self.should_parse(word_lower):
            return []

        parse = (
            word_lower, self._tag, word_lower,
            self.ESTIMATE_DECAY,
            ((self, word),)
        )
        seen_parses.add(parse)
        return [parse]

    def tag(self, word, word_lower, seen_tags):
        if not self.should_parse(word_lower) or self._tag in seen_tags:
            return []

        seen_tags.add(self._tag)
        return [self._tag]

    def should_parse(self, word):
        if len(word) < 5 or not word.startswith('по-'):
            return False

        tags = self.morph.tag(word[3:])
        return any(set(['ADJF', 'sing', 'datv']) in tag for tag in tags)

    def normalized(self, form):
        return form

    def get_lexeme(self, form):
        return [form]


class HyphenatedWordsAnalyzer(BaseAnalyzerUnit):
    """
    Parse the word by parsing its hyphen-separated parts.

    Examples:

        * интернет-магазин -> "интернет-" + магазин
        * человек-гора -> человек + гора

    """
    ESTIMATE_DECAY = 0.75

    _CONSIDER_THE_SAME = {
        'V-oy': 'V-ey',
        'gen1': 'gent',
        'loc1': 'loct',
        # 'acc1': 'accs',

    }  # TODO: add more grammemes

    def __init__(self, morph):
        super(HyphenatedWordsAnalyzer, self).__init__(morph)
        Tag = morph.TagClass
        self._FEATURE_GRAMMEMES = (Tag.PARTS_OF_SPEECH | Tag.NUMBERS |
                                   Tag.CASES | Tag.PERSONS | Tag.TENSES)

    def parse(self, word, word_lower, seen_parses):
        if not self._should_parse(word_lower):
            return []

        left, right = word_lower.split('-', 1)
        left_parses = self.morph.parse(left)
        right_parses = self.morph.parse(right)

        result = self._parse_as_variable_both(left_parses, right_parses, seen_parses)

        # We copy `seen_parses` to preserve parses even if similar parses
        # were observed at previous step (they may have different lexemes).
        _seen = seen_parses.copy()
        result.extend(self._parse_as_fixed_left(right_parses, _seen, left))
        seen_parses.update(_seen)

        return result

    def _parse_as_fixed_left(self, right_parses, seen, left):
        """
        Step 1: Assume that the left part is an uninflected prefix.
        Examples: интернет-магазин, воздушно-капельный
        """
        result = []

        for fixed_word, tag, normal_form, score, right_methods in right_parses:

            if tag._is_unknown():
                continue

            new_methods_stack = ((self, left, right_methods),)

            parse = (
                '-'.join((left, fixed_word)),
                tag,
                '-'.join((left, normal_form)),
                score * self.ESTIMATE_DECAY,
                new_methods_stack
            )
            result.append(parse)
            # add_parse_if_not_seen(parse, result, seen_left)

        return result

    def _parse_as_variable_both(self, left_parses, right_parses, seen):
        """
        Step 2: if left and right can be parsed the same way,
        then it may be the case that both parts should be inflected.
        Examples: человек-гора, команд-участниц, компания-производитель
        """
        result = []
        right_features = [self._similarity_features(p[1]) for p in right_parses]

        # FIXME: quadratic algorithm
        for left_parse in left_parses:

            left_tag = left_parse[1]

            if left_tag._is_unknown():
                continue

            left_feat = self._similarity_features(left_tag)

            for parse_index, right_parse in enumerate(right_parses):

                right_feat = right_features[parse_index]

                if left_feat != right_feat:
                    continue

                left_methods = left_parse[4]
                right_methods = right_parse[4]

                new_methods_stack = ((self, left_methods, right_methods),)

                # tag
                parse = (
                    '-'.join((left_parse[0], right_parse[0])),  # word
                    left_tag,
                    '-'.join((left_parse[2], right_parse[2])),  # normal form
                    left_parse[3] * self.ESTIMATE_DECAY,
                    new_methods_stack
                )
                result.append(parse)
                # add_parse_if_not_seen(parse, result, seen_right)

        return result

    def _similarity_features(self, tag):
        """ :type tag: pymorphy2.tagset.OpencorporaTag """
        return replace_grammemes(
            tag.grammemes & self._FEATURE_GRAMMEMES,
            {'gen1': 'gent', 'loc1': 'loct'}
        )

    def tag(self, word, word_lower, seen_tags):
        result = []
        # TODO: do not use self.parse
        for p in self.parse(word, word_lower, set()):
            add_tag_if_not_seen(p[1], result, seen_tags)
        return result

    def _should_parse(self, word):
        if '-' not in word:
            return False

        word_stripped = word.strip('-')
        if word_stripped != word:
            # don't handle words that start of end with a hyphen
            return False

        if word_stripped.count('-') != 1:
            # require exactly 1 hyphen, in the middle of the word
            return False

        if self.dict.prediction_prefixes.prefixes(word):
            # such words should really be parsed by KnownPrefixAnalyzer
            return False

        return True

    def normalized(self, form):
        return next(self._iter_lexeme(form))

    def get_lexeme(self, form):
        return list(self._iter_lexeme(form))

    def _iter_lexeme(self, form):
        methods_stack = form[4]
        assert len(methods_stack) == 1

        this_method, left_methods, right_methods = methods_stack[0]
        assert this_method is self

        if self._fixed_left_method_was_used(left_methods):
            # Form is obtained by parsing right part,
            # assuming that left part is an uninflected prefix.
            # Lexeme can be calculated from the right part in this case:
            prefix = left_methods + '-'

            right_form = without_fixed_prefix(
                replace_methods_stack(form, right_methods),
                len(prefix)
            )
            base_analyzer = right_methods[-1][0]

            lexeme = base_analyzer.get_lexeme(right_form)
            return (
                replace_methods_stack(
                    with_prefix(f, prefix),
                    ((this_method, left_methods, f[4]),)
                )
                for f in lexeme
            )

        else:
            # Form is obtained by parsing both parts.
            # Compute lexemes for left and right parts,
            # then merge them.
            left_form = self._without_right_part(
                replace_methods_stack(form, left_methods)
            )

            right_form = self._without_left_part(
                replace_methods_stack(form, right_methods)
            )

            left_lexeme = left_methods[-1][0].get_lexeme(left_form)
            right_lexeme = right_methods[-1][0].get_lexeme(right_form)

            return self._merge_lexemes(left_lexeme, right_lexeme)

    def _merge_lexemes(self, left_lexeme, right_lexeme):

        for left, right in self._align_lexeme_forms(left_lexeme, right_lexeme):
            word = '-'.join((left[0], right[0]))
            tag = left[1]
            normal_form = '-'.join((left[2], right[2]))
            score = (left[3] + right[3]) / 2
            method_stack = ((self, left[4], right[4]), )

            yield (word, tag, normal_form, score, method_stack)

    def _align_lexeme_forms(self, left_lexeme, right_lexeme):
        # FIXME: quadratic algorithm
        for right in right_lexeme:
            min_dist, closest = 1e6, None
            gr_right = replace_grammemes(right[1].grammemes, self._CONSIDER_THE_SAME)

            for left in left_lexeme:
                gr_left = replace_grammemes(left[1].grammemes, self._CONSIDER_THE_SAME)
                dist = len(gr_left ^ gr_right)
                if dist < min_dist:
                    min_dist = dist
                    closest = left

            yield closest, right

    @classmethod
    def _without_right_part(cls, form):
        word, tag, normal_form, score, methods_stack = form
        return (word[:word.index('-')], tag, normal_form[:normal_form.index('-')],
                score, methods_stack)

    @classmethod
    def _without_left_part(cls, form):
        word, tag, normal_form, score, methods_stack = form
        return (word[word.index('-')+1:], tag, normal_form[normal_form.index('-')+1:],
                score, methods_stack)

    @classmethod
    def _fixed_left_method_was_used(cls, left_methods):
        return not isinstance(left_methods, tuple)


def replace_grammemes(grammemes, replaces):
    grammemes = set(grammemes)
    for gr, replace in replaces.items():
        if gr in grammemes:
            grammemes.remove(gr)
            grammemes.add(replace)
    return grammemes

########NEW FILE########
__FILENAME__ = by_lookup
# -*- coding: utf-8 -*-
"""
Dictionary analyzer unit
------------------------
"""
from __future__ import absolute_import, division, unicode_literals
import logging
from pymorphy2.units.base import BaseAnalyzerUnit


logger = logging.getLogger(__name__)


class DictionaryAnalyzer(BaseAnalyzerUnit):
    """
    Analyzer unit that analyzes word using dictionary.
    """

    def parse(self, word, word_lower, seen_parses):
        """
        Parse a word using this dictionary.
        """
        res = []
        normal_forms_cache = {}
        para_data = self.dict.words.similar_items(word_lower, self.dict.ee)

        for fixed_word, parses in para_data:
            # `fixed_word` is a word with proper ё letters

            for para_id, idx in parses:
                if para_id not in normal_forms_cache:
                    normal_form = self.dict.build_normal_form(para_id, idx, fixed_word)
                    normal_forms_cache[para_id] = normal_form
                else:
                    normal_form = normal_forms_cache[para_id]

                tag = self.dict.build_tag_info(para_id, idx)
                method = ((self, fixed_word, para_id, idx),)
                res.append((fixed_word, tag, normal_form, 1.0, method))

        # res.sort(key=lambda p: len(p[1]))  #  prefer simple parses
        return res

    def tag(self, word, word_lower, seen_tags):
        """
        Tag a word using this dictionary.
        """
        para_data = self.dict.words.similar_item_values(word_lower, self.dict.ee)

        # avoid extra attribute lookups
        paradigms = self.dict.paradigms
        gramtab = self.dict.gramtab

        # tag known word
        result = []
        for parse in para_data:
            for para_id, idx in parse:
                # result.append(self.build_tag_info(para_id, idx))
                # .build_tag_info is unrolled for speed
                paradigm = paradigms[para_id]
                paradigm_len = len(paradigm) // 3
                tag_id = paradigm[paradigm_len + idx]
                result.append(gramtab[tag_id])

        return result

    def get_lexeme(self, form):
        """
        Return a lexeme (given a parsed word).
        """
        fixed_word, tag, normal_form, score, methods_stack = form
        _, para_id, idx = self._extract_para_info(methods_stack)

        _para = self.dict.paradigms[para_id]
        stem = self.dict.build_stem(_para, idx, fixed_word)

        result = []
        paradigm = self.dict.build_paradigm_info(para_id)  # XXX: reuse _para?

        for index, (_prefix, _tag, _suffix) in enumerate(paradigm):
            word = _prefix + stem + _suffix
            new_methods_stack = self._fix_stack(methods_stack, word, para_id, index)
            parse = (word, _tag, normal_form, 1.0, new_methods_stack)
            result.append(parse)

        return result

    def normalized(self, form):
        fixed_word, tag, normal_form, score, methods_stack = form
        original_word, para_id, idx = self._extract_para_info(methods_stack)

        if idx == 0:
            return form

        tag = self.dict.build_tag_info(para_id, 0)
        new_methods_stack = self._fix_stack(methods_stack, normal_form, para_id, 0)

        return (normal_form, tag, normal_form, 1.0, new_methods_stack)

    def _extract_para_info(self, methods_stack):
        # This method assumes that DictionaryAnalyzer is the first
        # and the only method in methods_stack.
        analyzer, original_word, para_id, idx = methods_stack[0]
        assert analyzer is self
        return original_word, para_id, idx

    def _fix_stack(self, methods_stack, word, para_id, idx):
        method0 = self, word, para_id, idx
        return (method0,) + methods_stack[1:]

########NEW FILE########
__FILENAME__ = by_shape
# -*- coding: utf-8 -*-
"""
Analyzer units that analyzes non-word tokes
-------------------------------------------
"""

from __future__ import absolute_import, unicode_literals, division

from pymorphy2.units.base import BaseAnalyzerUnit
from pymorphy2.shapes import is_latin, is_punctuation, is_roman_number


class _ShapeAnalyzer(BaseAnalyzerUnit):
    SCORE = 0.9
    EXTRA_GRAMMEMES = []
    EXTRA_GRAMMEMES_CYR = []

    def __init__(self, morph):
        super(_ShapeAnalyzer, self).__init__(morph)

        for lat, cyr in zip(self.EXTRA_GRAMMEMES, self.EXTRA_GRAMMEMES_CYR):
            self.morph.TagClass.add_grammemes_to_known(lat, cyr)

    def parse(self, word, word_lower, seen_parses):
        shape = self.check_shape(word, word_lower)
        if not shape:
            return []

        methods = ((self, word),)
        return [(word_lower, self.get_tag(word, shape), word_lower, self.SCORE, methods)]

    def tag(self, word, word_lower, seen_tags):
        shape = self.check_shape(word, word_lower)
        if not shape:
            return []
        return [self.get_tag(word, shape)]

    def get_lexeme(self, form):
        return [form]

    def normalized(self, form):
        return form

    # implement these 2 methods in a subclass:
    def check_shape(self, word, word_lower):
        raise NotImplementedError()

    def get_tag(self, word, shape):
        raise NotImplementedError()


class _SingleShapeAnalyzer(_ShapeAnalyzer):
    TAG_STR = None
    TAG_STR_CYR = None

    def __init__(self, morph):
        assert self.TAG_STR is not None
        assert self.TAG_STR_CYR is not None
        self.EXTRA_GRAMMEMES = self.TAG_STR.split(',')
        self.EXTRA_GRAMMEMES_CYR = self.TAG_STR_CYR.split(',')
        super(_SingleShapeAnalyzer, self).__init__(morph)
        self._tag = self.morph.TagClass(self.TAG_STR)

    def get_tag(self, word, shape):
        return self._tag


class PunctuationAnalyzer(_SingleShapeAnalyzer):
    """
    This analyzer tags punctuation marks as "PNCT".
    Example: "," -> PNCT
    """
    TAG_STR = 'PNCT'
    TAG_STR_CYR = 'ЗПР'  # aot.ru uses this name

    def check_shape(self, word, word_lower):
        return is_punctuation(word)


class LatinAnalyzer(_SingleShapeAnalyzer):
    """
    This analyzer marks latin words with "LATN" tag.
    Example: "pdf" -> LATN
    """
    TAG_STR = 'LATN'
    TAG_STR_CYR = 'ЛАТ'

    def check_shape(self, word, word_lower):
        return is_latin(word)


class NumberAnalyzer(_ShapeAnalyzer):
    """
    This analyzer marks integer numbers with "NUMB,int" or "NUMB,real" tags.
    Example: "12" -> NUMB,int; "12.4" -> NUMB,real

    .. note::

        Don't confuse it with "NUMR": "тридцать" -> NUMR

    """
    EXTRA_GRAMMEMES = ['NUMB', 'intg', 'real']
    EXTRA_GRAMMEMES_CYR = ['ЧИСЛО', 'цел', 'вещ']

    def __init__(self, morph):
        super(NumberAnalyzer, self).__init__(morph)
        self._tags = {
            'intg': morph.TagClass('NUMB,intg'),
            'real': morph.TagClass('NUMB,real'),
        }

    def check_shape(self, word, word_lower):
        try:
            int(word)
            return 'intg'
        except ValueError:
            try:
                float(word.replace(',', '.'))
                return 'real'
            except ValueError:
                pass
        return False

    def get_tag(self, word, shape):
        return self._tags[shape]


class RomanNumberAnalyzer(_SingleShapeAnalyzer):
    TAG_STR = 'ROMN'
    TAG_STR_CYR = 'РИМ'

    def check_shape(self, word, word_lower):
        return is_roman_number(word)

########NEW FILE########
__FILENAME__ = unkn
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from pymorphy2.units.base import BaseAnalyzerUnit


class UnknAnalyzer(BaseAnalyzerUnit):
    """
    Add an UNKN parse if other analyzers returned nothing.
    This allows to always have at least one parse result.
    """
    def __init__(self, morph):
        super(UnknAnalyzer, self).__init__(morph)
        self.morph.TagClass.add_grammemes_to_known('UNKN', 'НЕИЗВ')
        self._tag = self.morph.TagClass('UNKN')

    def parse(self, word, word_lower, seen_parses):
        if seen_parses:
            return []

        methods = ((self, word),)
        return [(word_lower, self._tag, word_lower, 1.0, methods)]

    def tag(self, word, word_lower, seen_tags):
        if seen_tags:
            return []
        return [self._tag]

    def get_lexeme(self, form):
        return [form]

    def normalized(self, form):
        return form

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division


def add_parse_if_not_seen(parse, result_list, seen_parses):
    try:
        para_id = parse[4][0][2]
    except IndexError:
        para_id = None

    word = parse[0]
    tag = parse[1]

    reduced_parse = word, tag, para_id

    if reduced_parse in seen_parses:
        return
    seen_parses.add(reduced_parse)
    result_list.append(parse)


def add_tag_if_not_seen(tag, result_list, seen_tags):
    if tag in seen_tags:
        return
    seen_tags.add(tag)
    result_list.append(tag)


def with_suffix(form, suffix):
    """ Return a new form with ``suffix`` attached """
    word, tag, normal_form, score, methods_stack = form
    return (word+suffix, tag, normal_form+suffix, score, methods_stack)


def without_fixed_suffix(form, suffix_length):
    """ Return a new form with ``suffix_length`` chars removed from right """
    word, tag, normal_form, score, methods_stack = form
    return (word[:-suffix_length], tag, normal_form[:-suffix_length],
            score, methods_stack)


def without_fixed_prefix(form, prefix_length):
    """ Return a new form with ``prefix_length`` chars removed from left """
    word, tag, normal_form, score, methods_stack = form
    return (word[prefix_length:], tag, normal_form[prefix_length:],
            score, methods_stack)


def with_prefix(form, prefix):
    """ Return a new form with ``prefix`` added """
    word, tag, normal_form, score, methods_stack = form
    return (prefix+word, tag, prefix+normal_form, score, methods_stack)


def replace_methods_stack(form, new_methods_stack):
    """
    Return a new form with ``methods_stack``
    replaced with ``new_methods_stack``
    """
    return form[:4] + (new_methods_stack,)


def without_last_method(form):
    """ Return a new form without last method from methods_stack """
    stack = form[4][:-1]
    return form[:4] + (stack,)


def append_method(form, method):
    """ Return a new form with ``method`` added to methods_stack """
    stack = form[4]
    return form[:4] + (stack+(method,),)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import
# unicode_literals here would break tests

import bz2
import os
import itertools
import codecs
import json

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

CHUNK_SIZE = 256*1024


def download_bz2(url, out_fp, chunk_size=CHUNK_SIZE, on_chunk=lambda: None):
    """
    Download a bz2-encoded file from ``url`` and write it to ``out_fp`` file.
    """
    decompressor = bz2.BZ2Decompressor()
    fp = urlopen(url, timeout=30)

    while True:
        data = fp.read(chunk_size)
        if not data:
            break
        out_fp.write(decompressor.decompress(data))
        on_chunk()


def get_mem_usage():
    import psutil
    proc = psutil.Process(os.getpid())
    try:
        return proc.memory_info().rss
    except AttributeError:
        # psutil < 2.x
        return proc.get_memory_info()[0]


def combinations_of_all_lengths(it):
    """
    Return an iterable with all possible combinations of items from ``it``:

        >>> for comb in combinations_of_all_lengths('ABC'):
        ...     print("".join(comb))
        A
        B
        C
        AB
        AC
        BC
        ABC

    """
    return itertools.chain(
        *(itertools.combinations(it, num+1) for num in range(len(it)))
    )


def longest_common_substring(data):
    """
    Return a longest common substring of a list of strings:

        >>> longest_common_substring(["apricot", "rice", "cricket"])
        'ric'
        >>> longest_common_substring(["apricot", "banana"])
        'a'
        >>> longest_common_substring(["foo", "bar", "baz"])
        ''

    See http://stackoverflow.com/questions/2892931/.
    """
    substr = ''
    if len(data) > 1 and len(data[0]) > 0:
        for i in range(len(data[0])):
            for j in range(len(data[0])-i+1):
                if j > len(substr) and all(data[0][i:i+j] in x for x in data):
                    substr = data[0][i:i+j]
    return substr


def json_write(filename, obj, **json_options):
    """ Create file ``filename`` with ``obj`` serialized to JSON """

    json_options.setdefault('ensure_ascii', False)
    with codecs.open(filename, 'w', 'utf8') as f:
        json.dump(obj, f, **json_options)


def json_read(filename, **json_options):
    """ Read an object from a json file ``filename`` """
    with codecs.open(filename, 'r', 'utf8') as f:
        return json.load(f, **json_options)


def largest_group(iterable, key):
    """
    Find a group of largest elements (according to ``key``).

    >>> s = [-4, 3, 5, 7, 4, -7]
    >>> largest_group(s, abs)
    [7, -7]

    """
    it1, it2 = itertools.tee(iterable)
    max_key = max(map(key, it1))
    return [el for el in it2 if key(el) == max_key]


def word_splits(word, min_reminder=3, max_prefix_length=5):
    """
    Return all splits of a word (taking in account min_reminder and
    max_prefix_length).
    """
    max_split = min(max_prefix_length, len(word)-min_reminder)
    split_indexes = range(1, 1+max_split)
    return [(word[:i], word[i:]) for i in split_indexes]

########NEW FILE########
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
        for i, c in enumerate(self.children):
            if not hasattr(c, 'children'):
                assert c in uniq
                self.children[i] = uniq[uniq.index(c)]
            else:
                c.fix_identities(uniq)

    def fix_repeating_arguments(self):
        """Fix elements that should accumulate/increment values."""
        either = [list(c.children) for c in self.either.children]
        for case in either:
            for e in [c for c in case if case.count(c) > 1]:
                if type(e) is Argument or type(e) is Option and e.argcount:
                    if e.value is None:
                        e.value = []
                    elif type(e.value) is not list:
                        e.value = e.value.split()
                if type(e) is Command or type(e) is Option and e.argcount == 0:
                    e.value = 0
        return self

    @property
    def either(self):
        """Transform pattern into an equivalent, with only top-level Either."""
        # Currently the pattern will not be equivalent, but more "narrow",
        # although good enough to reason about list arguments.
        ret = []
        groups = [[self]]
        while groups:
            children = groups.pop(0)
            types = [type(c) for c in children]
            if Either in types:
                either = [c for c in children if type(c) is Either][0]
                children.pop(children.index(either))
                for c in either.children:
                    groups.append([c] + children)
            elif Required in types:
                required = [c for c in children if type(c) is Required][0]
                children.pop(children.index(required))
                groups.append(list(required.children) + children)
            elif Optional in types:
                optional = [c for c in children if type(c) is Optional][0]
                children.pop(children.index(optional))
                groups.append(list(optional.children) + children)
            elif AnyOptions in types:
                optional = [c for c in children if type(c) is AnyOptions][0]
                children.pop(children.index(optional))
                groups.append(list(optional.children) + children)
            elif OneOrMore in types:
                oneormore = [c for c in children if type(c) is OneOrMore][0]
                children.pop(children.index(oneormore))
                groups.append(list(oneormore.children) * 2 + children)
            else:
                ret.append(children)
        return Either(*[Required(*e) for e in ret])


class ChildPattern(Pattern):

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

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


class ParentPattern(Pattern):

    def __init__(self, *children):
        self.children = list(children)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(repr(a) for a in self.children))

    def flat(self, *types):
        if type(self) in types:
            return [self]
        return sum([c.flat(*types) for c in self.children], [])


class Argument(ChildPattern):

    def single_match(self, left):
        for n, p in enumerate(left):
            if type(p) is Argument:
                return n, Argument(self.name, p.value)
        return None, None

    @classmethod
    def parse(class_, source):
        name = re.findall('(<\S*?>)', source)[0]
        value = re.findall('\[default: (.*)\]', source, flags=re.I)
        return class_(name, value[0] if value else None)


class Command(Argument):

    def __init__(self, name, value=False):
        self.name = name
        self.value = value

    def single_match(self, left):
        for n, p in enumerate(left):
            if type(p) is Argument:
                if p.value == self.name:
                    return n, Command(self.name, True)
                else:
                    break
        return None, None


class Option(ChildPattern):

    def __init__(self, short=None, long=None, argcount=0, value=False):
        assert argcount in (0, 1)
        self.short, self.long = short, long
        self.argcount, self.value = argcount, value
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
        for n, p in enumerate(left):
            if self.name == p.name:
                return n, p
        return None, None

    @property
    def name(self):
        return self.long or self.short

    def __repr__(self):
        return 'Option(%r, %r, %r, %r)' % (self.short, self.long,
                                           self.argcount, self.value)


class Required(ParentPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        l = left
        c = collected
        for p in self.children:
            matched, l, c = p.match(l, c)
            if not matched:
                return False, left, collected
        return True, l, c


class Optional(ParentPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        for p in self.children:
            m, left, collected = p.match(left, collected)
        return True, left, collected


class AnyOptions(Optional):

    """Marker/placeholder for [options] shortcut."""


class OneOrMore(ParentPattern):

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


class Either(ParentPattern):

    def match(self, left, collected=None):
        collected = [] if collected is None else collected
        outcomes = []
        for p in self.children:
            matched, _, _ = outcome = p.match(left, collected)
            if matched:
                outcomes.append(outcome)
        if outcomes:
            return min(outcomes, key=lambda outcome: len(outcome[1]))
        return False, left, collected


class TokenStream(list):

    def __init__(self, source, error):
        self += source.split() if hasattr(source, 'split') else source
        self.error = error

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
                if tokens.current() is None:
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
                    if tokens.current() is None:
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
    tokens = TokenStream(re.sub(r'([\[\]\(\)\|]|\.\.\.)', r' \1 ', source),
                         DocoptLanguageError)
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
        return [AnyOptions()]
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
    # in python < 2.7 you can't pass flags=re.MULTILINE
    split = re.split('\n *(<\S+?>|-\S+?)', doc)[1:]
    split = [s1 + s2 for s1, s2 in zip(split[::2], split[1::2])]
    options = [Option.parse(s) for s in split if s.startswith('-')]
    #arguments = [Argument.parse(s) for s in split if s.startswith('<')]
    #return options, arguments
    return options


def printable_usage(doc):
    # in python < 2.7 you can't pass flags=re.IGNORECASE
    usage_split = re.split(r'([Uu][Ss][Aa][Gg][Ee]:)', doc)
    if len(usage_split) < 3:
        raise DocoptLanguageError('"usage:" (case-insensitive) not found.')
    if len(usage_split) > 3:
        raise DocoptLanguageError('More than one "usage:" (case-insensitive).')
    return re.split(r'\n\s*\n', ''.join(usage_split[1:]))[0].strip()


def formal_usage(printable_usage):
    pu = printable_usage.split()[1:]  # split and drop "usage:"
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
    >>> from docopt import docopt # doctest: +SKIP
    >>> doc = '''
    ...    Usage:
    ...        my_program tcp <host> <port> [--timeout=<seconds>]
    ...        my_program serial <port> [--baud=<n>] [--timeout=<seconds>]
    ...        my_program (-h | --help | --version)
    ...
    ...    Options:
    ...        -h, --help  Show this screen and exit.
    ...        --baud=<n>  Baudrate [default: 9600]
    ...    '''
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
    if argv is None:
        argv = sys.argv[1:]
    DocoptExit.usage = printable_usage(doc)
    options = parse_defaults(doc)
    pattern = parse_pattern(formal_usage(DocoptExit.usage), options)
    # [default] syntax for argument is disabled
    #for a in pattern.flat(Argument):
    #    same_name = [d for d in arguments if d.name == a.name]
    #    if same_name:
    #        a.value = same_name[0].value
    argv = parse_argv(TokenStream(argv, DocoptExit), list(options),
                      options_first)
    pattern_options = set(pattern.flat(Option))
    for ao in pattern.flat(AnyOptions):
        doc_options = parse_defaults(doc)
        ao.children = list(set(doc_options) - pattern_options)
        #if any_options:
        #    ao.children += [Option(o.short, o.long, o.argcount)
        #                    for o in argv if type(o) is Option]
    extras(help, version, argv, doc)
    matched, left, collected = pattern.fix().match(argv)
    if matched and left == []:  # better error message if left?
        return Dict((a.name, a.value) for a in (pattern.flat() + collected))
    raise DocoptExit()

########NEW FILE########
__FILENAME__ = version
__version__ = "0.7"

########NEW FILE########
__FILENAME__ = test_analyzer
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import pickle
import pytest
import pymorphy2
from pymorphy2.units.by_lookup import DictionaryAnalyzer
from pymorphy2.units.by_analogy import UnknownPrefixAnalyzer, KnownPrefixAnalyzer
from pymorphy2.units.by_hyphen import HyphenatedWordsAnalyzer

from .utils import morph

# TODO: move most of tests to test_parsing

TEST_DATA = [
    ('кошка', ['кошка']),
    ('кошке', ['кошка']),

    # в pymorphy 0.5.6 результат парсинга - наоборот, сначала СТАЛЬ, потом СТАТЬ
    ('стали', ['стать', 'сталь']),

    ('наистарейший', ['старый']),

    ('котёнок', ['котёнок']),
    ('котенок', ['котёнок']),
    ('тяжелый', ['тяжёлый']),
    ('легок', ['лёгкий']),

    ('она', ['она']),
    ('ей', ['она']),
    ('я', ['я']),
    ('мне', ['я']),

    ('наиневероятнейший', ['вероятный']),
    ('лучший', ['хороший']),
    ('наилучший', ['хороший']),
    ('человек', ['человек']),
    ('люди', ['человек']),

    ('клюеву', ['клюев']),
    ('клюева', ['клюев']),

    ('гулял', ['гулять']),
    ('гуляла', ['гулять']),
    ('гуляет', ['гулять']),
    ('гуляют', ['гулять']),
    ('гуляли', ['гулять']),
    ('гулять', ['гулять']),

    ('гуляющий', ['гулять']),
    ('гулявши', ['гулять']),
    ('гуляя', ['гулять']),
    ('гуляющая', ['гулять']),
    ('загулявший', ['загулять']),

    ('красивый', ['красивый']),
    ('красивая', ['красивый']),
    ('красивому', ['красивый']),
    ('красивые', ['красивый']),

    ('действие', ['действие']),
]

PREFIX_PREDICTION_DATA = [
    ('псевдокошка', ['псевдокошка']),
    ('псевдокошкой', ['псевдокошка']),

    ('сверхнаистарейший', ['сверхстарый']),
    ('сверхнаистарейший', ['сверхстарый']),
    ('квазипсевдонаистарейшего', ['квазипсевдостарый']),
    ('небесконечен', ['небесконечный']),

    ('мегакоту', ['мегакот']),
    ('мегасверхнаистарейшему', ['мегасверхстарый']),
]

PREDICTION_TEST_DATA = [
    ('триждычерезпилюлюокнами', ['триждычерезпилюлюокно']),
    ('разквакались', ['разквакаться']),
    ('кашиварнее', ['кашиварный']),
    ('покашиварней', ['кашиварный', 'покашиварный', 'покашиварня']),
    ('подкашиварней', ['дкашиварный', 'подкашиварный', 'подкашиварня']),
    ('депыртаментов', ['депыртамент', 'депыртаментовый']),
    ('измохратился', ['измохратиться']),

    ('бутявкой', ['бутявка']), # и никаких местоимений!
    ('сапают', ['сапать']), # и никаких местоимений!

    ('кюди', ['кюдить', 'кюдь', 'кюди']), # и никаких "человек"
]

NON_PRODUCTIVE_BUGS_DATA = [
    ('бякобы', 'PRCL'),
    ('бякобы', 'CONJ'),
    ('псевдоякобы', 'PRCL'),
    ('псевдоякобы', 'CONJ'),
]


def test_pickling():
    data = pickle.dumps(morph, pickle.HIGHEST_PROTOCOL)
    morph2 = pickle.loads(data)
    assert morph2.tag('слово') == morph.tag('слово')


def with_test_data(data, second_param_name='parse_result'):
    return pytest.mark.parametrize(
        ("word", second_param_name),
        data
    )


class TestNormalForms:
    @with_test_data(TEST_DATA)
    def test_normal_forms(self, word, parse_result):
        assert morph.normal_forms(word) == parse_result

    @with_test_data(PREDICTION_TEST_DATA)
    def test_normal_forms_prediction(self, word, parse_result):
        assert morph.normal_forms(word) == parse_result

    @with_test_data(PREFIX_PREDICTION_DATA)
    def test_normal_forms_prefix_prediction(self, word, parse_result):
        assert morph.normal_forms(word) == parse_result


class TestTagAndParse:
    """
    This test checks if morph.tag produces the same results as morph.parse.
    """
    def assertTagAndParseAgree(self, word):
        assert set(morph.tag(word)) == set(p.tag for p in morph.parse(word))

    @with_test_data(TEST_DATA)
    def test_basic(self, word, parse_result):
        self.assertTagAndParseAgree(word)

    @with_test_data(PREDICTION_TEST_DATA)
    def test_prediction(self, word, parse_result):
        self.assertTagAndParseAgree(word)

    @with_test_data(PREFIX_PREDICTION_DATA)
    def test_prefix_prediction(self, word, parse_result):
        self.assertTagAndParseAgree(word)


class TestTagMethod:
    def _tagged_as(self, tags, cls):
        return any(tag.POS == cls for tag in tags)

    def assertNotTaggedAs(self, word, cls):
        tags = morph.tag(word)
        assert not self._tagged_as(tags, cls), (tags, cls)

    @with_test_data(NON_PRODUCTIVE_BUGS_DATA, 'cls')
    def test_no_nonproductive_forms(self, word, cls):
        self.assertNotTaggedAs(word, cls)


class TestParse:
    def _parsed_as(self, parse, cls):
        return any(p[1].POS==cls for p in parse)

    def _parse_cls_first_index(self, parse, cls):
        for idx, p in enumerate(parse):
            if p.tag.POS == cls:
                return idx

    def assertNotParsedAs(self, word, cls):
        parse = morph.parse(word)
        assert not self._parsed_as(parse, cls), (parse, cls)

    @with_test_data(NON_PRODUCTIVE_BUGS_DATA, 'cls')
    def test_no_nonproductive_forms(self, word, cls):
        self.assertNotParsedAs(word, cls)

    def test_no_duplicate_parses(self):
        parse = morph.parse('бутявкой')
        data = [variant[:3] for variant in parse]
        assert len(set(data)) == len(data), parse

    def test_parse_order(self):
        parse = morph.parse('продюсерство')
        assert self._parsed_as(parse, 'NOUN')
        assert self._parsed_as(parse, 'ADVB')
        assert self._parse_cls_first_index(parse, 'NOUN') < self._parse_cls_first_index(parse, 'ADVB')


class TestHyphen:

    def assert_not_parsed_by_hyphen(self, word):
        for p in morph.parse(word):
            for meth in p.methods_stack:
                analyzer = meth[0]
                assert not isinstance(analyzer, HyphenatedWordsAnalyzer), p.methods_stack

    def test_no_hyphen_analyzer_for_known_prefixes(self):
        # this word should be parsed by KnownPrefixAnalyzer
        self.assert_not_parsed_by_hyphen('мини-будильник')

    def test_no_hyphen_analyzer_bad_input(self):
        self.assert_not_parsed_by_hyphen('привет-пока-')


class TestTagWithPrefix:
    def test_tag_with_unknown_prefix(self):
        word = 'мегакот'
        pred1 = UnknownPrefixAnalyzer(morph)
        pred2 = KnownPrefixAnalyzer(morph)

        parse1 = pred1.tag(word, word.lower(), set())
        parse2 = pred2.tag(word, word.lower(), set())
        assert parse1 == parse2

    def test_longest_prefixes_are_used(self):
        parses = morph.parse('недобарабаном')
        assert len(parses) == 1
        assert len(parses[0].methods_stack) == 2 # недо+барабаном, not не+до+барабаном


class TestUtils:
    def test_word_is_known(self):
        assert morph.word_is_known('еж')
        assert morph.word_is_known('ёж')
        assert not morph.word_is_known('еш')

    def test_word_is_known_strict(self):
        assert not morph.word_is_known('еж', strict_ee=True)
        assert morph.word_is_known('ёж', strict_ee=True)
        assert not morph.word_is_known('еш', strict_ee=True)


class TestParseResultClass:
    def assertNotTuples(self, parses):
        assert all(type(p) != tuple for p in parses)

    def assertAllTuples(self, parses):
        assert all(type(p) == tuple for p in parses)

    def test_namedtuples(self):
        self.assertNotTuples(morph.parse('кот'))
        # self.assertNotTuples(morph.inflect('кот', set(['plur'])))
        # self.assertNotTuples(morph.decline('кот'))

    def test_plain_tuples(self):
        morph_plain = pymorphy2.MorphAnalyzer(result_type=None)
        self.assertAllTuples(morph_plain.parse('кот'))
        # self.assertAllTuples(morph_plain.inflect('кот', set(['plur'])))
        # self.assertAllTuples(morph_plain.decline('кот'))


class TestLatinPredictor:
    def test_tag(self):
        assert morph.tag('Maßstab') == [morph.TagClass('LATN')]

    def test_parse(self):
        parses = morph.parse('Maßstab')
        assert len(parses) == 1
        assert 'LATN' in parses[0].tag

    def test_lexeme(self):
        p = morph.parse('Maßstab')[0]
        assert p.lexeme == [p]

    def test_normalized(self):
        p = morph.parse('Maßstab')[0]
        assert p.normalized == p

    def test_normal_forms(self):
        assert morph.normal_forms('Maßstab') == ['maßstab']


class TetsPunctuationPredictor:
    def test_tag(self):
        assert morph.tag('…') == [morph.TagClass('PNCT')]


class TestInitials:

    def assertHasFirstName(self, tags):
        assert any(set(['Name', 'Abbr']) in tag for tag in tags), tags

    def assertHasPatronymic(self, tags):
        assert any(set(['Patr', 'Abbr']) in tag for tag in tags), tags

    def _filter_parse(self, word, grammemes):
        return [p for p in morph.parse(word) if set(grammemes) in p.tag]

    def test_tag(self):
        tags = morph.tag('Д')
        self.assertHasFirstName(tags)
        self.assertHasPatronymic(tags)

    def test_tag_conj(self):
        tags = morph.tag('И')
        self.assertHasFirstName(tags)
        self.assertHasPatronymic(tags)
        assert any('CONJ' in tag for tag in tags), tags

    def test_parse(self):
        tags = [p.tag for p in morph.parse('И')]
        self.assertHasFirstName(tags)
        self.assertHasPatronymic(tags)

    def test_normalize_name_masc(self):
        parse = self._filter_parse('И', ['Name', 'accs', 'masc'])[0]
        assert parse.normalized.word == 'и'
        assert parse.normalized.tag.case == 'nomn'
        assert parse.normalized.tag.gender == 'masc'

    def test_normalize_patr_masc(self):
        parse = self._filter_parse('И', ['Patr', 'accs', 'masc'])[0]
        assert parse.normalized.word == 'и'
        assert parse.normalized.tag.case == 'nomn'
        assert parse.normalized.tag.gender == 'masc'

    def test_normalize_name_femn(self):
        parse = self._filter_parse('И', ['Name', 'accs', 'femn'])[0]
        assert parse.normalized.word == 'и'
        assert parse.normalized.tag.case == 'nomn'
        assert parse.normalized.tag.gender == 'femn'

    def test_normalize_patr_femn(self):
        parse = self._filter_parse('И', ['Patr', 'accs', 'femn'])[0]
        assert parse.normalized.word == 'и'
        assert parse.normalized.tag.case == 'nomn'
        assert parse.normalized.tag.gender == 'masc'


def test_iter_known_word_parses():
    parses = list(morph.iter_known_word_parses('приве'))
    assert any(
        (p.word=='привет' and isinstance(p.methods_stack[0][0], DictionaryAnalyzer))
        for p in parses
    ), parses

########NEW FILE########
__FILENAME__ = test_fuzzy
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import codecs
import os
import pytest

from .utils import morph

SUITE_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'dev_data',
    'suite.txt'
)

Tag = morph.TagClass

def iter_suite(path):
    """
    loads test suite
    """
    with codecs.open(path, 'r', 'utf8') as f:
        for index, line in enumerate(f):
            line = line.strip("\n")

            if index == 0: # revision
                yield line
                continue

            # test data
            parts = line.split('|')
            word, tags = parts[0], [Tag(tag) for tag in parts[1:]]
            yield word, tags

def load_suite(path):
    suite = list(iter_suite(path))
    return suite[0], suite[1:]


def test_tagger_fuzzy():
    if not os.path.exists(SUITE_PATH):
        msg = """
        Fuzzy test suite was not created. In order to run
        "fuzzy" tests create a test suite with the following command:

            pymorphy dict make_test_suite dict.xml dev_data/suite.txt -v

        """
        pytest.skip(msg)

    suite_revision, suite70k = load_suite(SUITE_PATH)
    dict_revision = morph.meta()['source_revision']
    if suite_revision != dict_revision:
        msg = """
        Test suite revision (%s) doesn't match dictionary revision (%s).
        Regenerate test suite with the following command:

            pymorphy dict make_test_suite dict.xml dev_data/suite.txt -v

        """  % (suite_revision, dict_revision)
        pytest.skip(msg)

    for word, tags in suite70k:
        parse_result = set(morph.tag(word))
        assert parse_result == set(tags)

########NEW FILE########
__FILENAME__ = test_inflection
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import pytest

from .utils import morph
from pymorphy2.shapes import restore_capitalization

def with_test_data(data):
    return pytest.mark.parametrize(
        ("word", "grammemes", "result"),
        data
    )

def assert_first_inflected_variant(word, grammemes, result):
    inflected_variants = [p.inflect(set(grammemes)) for p in morph.parse(word)]
    inflected_variants = [v for v in inflected_variants if v]
    # inflected_variants = morph.inflect(word, grammemes)
    assert len(inflected_variants)

    inflected = inflected_variants[0]
    assert restore_capitalization(inflected.word, word) == result


@with_test_data([
    # суслики и бутявки
    ("суслик", ["datv"], "суслику"),
    ("суслики", ["datv"], "сусликам"),
    ("сусликов", ["datv"], "сусликам"),
    ("суслика", ["datv"], "суслику"),
    ("суслик", ["datv", "plur"], "сусликам"),

    ("бутявка", ["datv"], "бутявке"),
    ("бутявок", ["datv"], "бутявкам"),

    # глаголы, причастия, деепричастия
    ("гуляю", ["past"], "гулял"),
    ("гулял", ["pres"], "гуляю"),
    ("гулял", ["INFN"], "гулять"),
    ("гулял", ["GRND"], "гуляв"),
    ("гулял", ["PRTF"], "гулявший"),
    ("гуляла", ["PRTF"], "гулявшая"),
    ("гуляю", ["PRTF", "datv"], "гуляющему"),
    ("гулявший", ["VERB"], "гулял"),
    ("гулявший", ["VERB", "femn"], "гуляла"),
    ("иду", ["2per"], "идёшь"),
    ("иду", ["2per", "plur"], "идёте"),
    ("иду", ["3per"], "идёт"),
    ("иду", ["3per", "plur"], "идут"),
    ("иду", ["impr", "excl"], "иди"),

    # баг из pymorphy
    ('киев', ['loct'], 'киеве'),

    # одушевленность
    ('слабый', ['accs', 'inan'], 'слабый'),
    ('слабый', ['accs', 'anim'], 'слабого'),

    # сравнительные степени прилагательных
    ('быстрый', ['COMP'], 'быстрее'),
    ('хорошая', ['COMP'], 'лучше'),

    # частицы - не отрезаются
    ('скажи-ка', ['futr'], 'скажу-ка'),
])
def test_first_inflected_value(word, grammemes, result):
    assert_first_inflected_variant(word, grammemes, result)


def test_orel():
    assert_first_inflected_variant('орел', ['gent'], 'орла')


@with_test_data([
    ('снег', ['gent'], 'снега'),
    ('снег', ['gen2'], 'снегу'),
    ('Боря', ['voct'], 'Борь'),
])
def test_second_cases(word, grammemes, result):
    assert_first_inflected_variant(word, grammemes, result)


@with_test_data([
    ('валенок', ['gent', 'sing'], 'валенка'),
    ('валенок', ['gen2', 'sing'], 'валенка'),  # there is no gen2
    ('велосипед', ['loct'], 'велосипеде'), # о велосипеде
    ('велосипед', ['loc2'], 'велосипеде'), # а тут второго предложного нет, в велосипеде
    ('хомяк', ['voct'], 'хомяк'),        # there is not voct, nomn should be used
    ('Геннадий', ['voct'], 'Геннадий'),  # there is not voct, nomn should be used
])
def test_case_substitution(word, grammemes, result):
    assert_first_inflected_variant(word, grammemes, result)


@pytest.mark.xfail
@with_test_data([
    # доп. падежи, fixme
    ('лес', ['loct'], 'лесе'),   # о лесе
    ('лес', ['loc2'], 'лесу'),   # в лесу
    ('острова', ['datv'], 'островам'),
])
def test_best_guess(word, grammemes, result):
    assert_first_inflected_variant(word, grammemes, result)

########NEW FILE########
__FILENAME__ = test_lexemes
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import pytest
from .utils import morph


# lexemes are divided by blank lines;
# lines that starts with "#" are comments;
# lines that starts with "XFAIL" excludes lexeme from testing.

def parse_lexemes(lexemes_txt):
    lexemes_txt = "".join(
        line for line in lexemes_txt.strip().splitlines(True)
             if not line.startswith("#")
    )
    return lexemes_txt.split("\n\n")

def get_lexeme_words(lexeme):
    lexeme_words = tuple(lexeme.split())
    if lexeme_words[0].startswith('XFAIL'):
        pytest.xfail()
    return lexeme_words


def parse_full_lexeme(lexeme):
    forms = lexeme.strip().splitlines()
    return [form.split(None, 1) for form in forms]


LEXEMES = parse_lexemes("""
# =========== noun
кот кота коту кота котом коте
коты котов котам котов котами котах

# =========== pronoun
он его него ему нему его него
им ним нём

# =========== pronoun with a particle
он-то его-то него-то ему-то нему-то его-то него-то
им-то ним-то нём-то

# =========== noun with a known prefix
лжекот лжекота лжекоту лжекота лжекотом лжекоте
лжекоты лжекотов лжекотам лжекотов лжекотами лжекотах

# =========== noun with two known prefixes (hyphenated)
экс-лжекот экс-лжекота экс-лжекоту экс-лжекота экс-лжекотом экс-лжекоте
экс-лжекоты экс-лжекотов экс-лжекотам экс-лжекотов экс-лжекотами экс-лжекотах

# =========== noun with two known prefixes
экслжекот экслжекота экслжекоту экслжекота экслжекотом экслжекоте экслжекоты
экслжекотов экслжекотам экслжекотов экслжекотами экслжекотах

# =========== noun witn a guessed prefix
буропёс буропса буропсу буропса буропсом буропсе
буропсы буропсов буропсам буропсов буропсами буропсах

# =========== both parts can be inflected the same way
кот-маг кота-мага коту-магу кота-мага котом-магом коте-маге
коты-маги котов-магов котам-магам котов-магов котами-магами котах-магах

команда-участница команды-участницы команде-участнице команду-участницу командой-участницей командою-участницею команде-участнице
команды-участницы команд-участниц командам-участницам команды-участниц командами-участницами командах-участницах

# =========== prediction using suffix
йотка йотки йотке йотку йоткой йоткою йотке
йотки йоток йоткам йотки йотками йотках

# =========== left part is fixed
кото-пёс кото-пса кото-псу кото-пса кото-псом кото-псе
кото-псы кото-псов кото-псам кото-псов кото-псами кото-псах

# =========== left part is fixed, right is with known prefix
кото-псевдопёс кото-псевдопса кото-псевдопсу кото-псевдопса кото-псевдопсом кото-псевдопсе
кото-псевдопсы кото-псевдопсов кото-псевдопсам кото-псевдопсов кото-псевдопсами кото-псевдопсах

# =========== numeral with gender
два двух двум два двух двумя двух
две двух двум две двух двумя двух
два двух двум два двумя двух

# =========== two adverbs
красиво-туманно

# =========== adverb ПО-..
по-театральному

по-западному

# =========== two numerals: one depends on gender, the other doesn't
XFAIL: see https://github.com/kmike/pymorphy2/issues/18
два-три двух-трёх двум-трем два-три двух-трёх двумя-тремя двух-трёх
две-три двух-трёх двум-трем две-три двух-трёх двумя-тремя двух-трёх
два-три двух-трёх двум-трём два-три двумя-тремя двух-трёх

# =========== two nouns that parses differently
человек-гора человека-горы человеку-горе человека-гору человеком-горой человеком-горою человеке-горе
люди-горы людей-гор людям-горам людей-горы людьми-горами людях-горах

гора-человек горы-человека горе-человеку гору-человека горой-человеком горе-человеке
горы-люди гор-людей гор-человек горам-людям горам-человекам горы-людей горами-людьми горами-человеками горах-людях горах-человеках

XFAIL: this is currently too complex
человек-гора человека-горы человеку-горе человека-гору человеком-горой человеком-горою человеке-горе
люди-горы людей-гор человек-гор людям-горам человекам-горам людей-гор людьми-горами человеками-горами людях-горах человеках-горах

# =========== two nouns, one of which has gen1/gen2 forms
лес-колдун леса-колдуна лесу-колдуну лес-колдуна лесом-колдуном лесе-колдуне
леса-колдуны лесов-колдунов лесам-колдунам леса-колдунов лесами-колдунами лесах-колдунах

""")


LEXEMES_FULL = parse_lexemes("""
# ============ noun, a sanity check
кот        NOUN,anim,masc sing,nomn
кота       NOUN,anim,masc sing,gent
коту       NOUN,anim,masc sing,datv
кота       NOUN,anim,masc sing,accs
котом      NOUN,anim,masc sing,ablt
коте       NOUN,anim,masc sing,loct
коты       NOUN,anim,masc plur,nomn
котов      NOUN,anim,masc plur,gent
котам      NOUN,anim,masc plur,datv
котов      NOUN,anim,masc plur,accs
котами     NOUN,anim,masc plur,ablt
котах      NOUN,anim,masc plur,loct

# =========== adverb
театрально ADVB

по-театральному ADVB

# =========== pronoun with a particle
он-то      NPRO,masc,3per,Anph sing,nomn
его-то     NPRO,masc,3per,Anph sing,gent
него-то    NPRO,masc,3per,Anph sing,gent,Af-p
ему-то     NPRO,masc,3per,Anph sing,datv
нему-то    NPRO,masc,3per,Anph sing,datv,Af-p
его-то     NPRO,masc,3per,Anph sing,accs
него-то    NPRO,masc,3per,Anph sing,accs,Af-p
им-то      NPRO,masc,3per,Anph sing,ablt
ним-то     NPRO,masc,3per,Anph sing,ablt,Af-p
нём-то     NPRO,masc,3per,Anph sing,loct,Af-p

# ========== initials
И  NOUN,anim,masc,Sgtm,Name,Fixd,Abbr,Init sing,nomn
И  NOUN,anim,masc,Sgtm,Name,Fixd,Abbr,Init sing,gent
И  NOUN,anim,masc,Sgtm,Name,Fixd,Abbr,Init sing,datv
И  NOUN,anim,masc,Sgtm,Name,Fixd,Abbr,Init sing,accs
И  NOUN,anim,masc,Sgtm,Name,Fixd,Abbr,Init sing,ablt
И  NOUN,anim,masc,Sgtm,Name,Fixd,Abbr,Init sing,loct

И  NOUN,anim,femn,Sgtm,Name,Fixd,Abbr,Init sing,nomn
И  NOUN,anim,femn,Sgtm,Name,Fixd,Abbr,Init sing,gent
И  NOUN,anim,femn,Sgtm,Name,Fixd,Abbr,Init sing,datv
И  NOUN,anim,femn,Sgtm,Name,Fixd,Abbr,Init sing,accs
И  NOUN,anim,femn,Sgtm,Name,Fixd,Abbr,Init sing,ablt
И  NOUN,anim,femn,Sgtm,Name,Fixd,Abbr,Init sing,loct

И  NOUN,anim,masc,Sgtm,Patr,Fixd,Abbr,Init sing,nomn
И  NOUN,anim,masc,Sgtm,Patr,Fixd,Abbr,Init sing,gent
И  NOUN,anim,masc,Sgtm,Patr,Fixd,Abbr,Init sing,datv
И  NOUN,anim,masc,Sgtm,Patr,Fixd,Abbr,Init sing,accs
И  NOUN,anim,masc,Sgtm,Patr,Fixd,Abbr,Init sing,ablt
И  NOUN,anim,masc,Sgtm,Patr,Fixd,Abbr,Init sing,loct
И  NOUN,anim,femn,Sgtm,Patr,Fixd,Abbr,Init sing,nomn
И  NOUN,anim,femn,Sgtm,Patr,Fixd,Abbr,Init sing,gent
И  NOUN,anim,femn,Sgtm,Patr,Fixd,Abbr,Init sing,datv
И  NOUN,anim,femn,Sgtm,Patr,Fixd,Abbr,Init sing,accs
И  NOUN,anim,femn,Sgtm,Patr,Fixd,Abbr,Init sing,ablt
И  NOUN,anim,femn,Sgtm,Patr,Fixd,Abbr,Init sing,loct

# ============ UNKN
ьё UNKN
""")


# ============ Tests:

@pytest.mark.parametrize("lexeme", LEXEMES)
def test_has_proper_lexemes(lexeme):
    """
    Check if the lexeme of the first word in the lexeme is the same lexeme.
    """
    lexeme_words = get_lexeme_words(lexeme)

    variants = _lexemes_for_word(lexeme_words[0])
    if lexeme_words not in variants:
        variants_repr = "\n".join([" ".join(v) for v in variants])
        assert False, "%s not in \n%s" % (lexeme, variants_repr)


@pytest.mark.parametrize("lexeme", LEXEMES)
def test_lexemes_sanity(lexeme):
    """
    Check if parse.lexeme works properly by applying it several times.
    """
    lexeme_words = get_lexeme_words(lexeme)

    for word in lexeme_words:
        for p in morph.parse(word):
            assert p.lexeme[0].lexeme == p.lexeme


@pytest.mark.parametrize("lexeme", LEXEMES)
def test_normalized_is_first(lexeme):
    """
    Test that parse.normalized is a first form in lexeme.
    """
    lexeme_words = get_lexeme_words(lexeme)

    first_parse = morph.parse(lexeme_words[0])[0]
    normal_form = (first_parse.word, first_parse.tag.POS)

    for word in lexeme_words:
        parses = morph.parse(word)
        normalized = [(p.normalized.word, p.normalized.tag.POS) for p in parses]
        assert normal_form in normalized


@pytest.mark.parametrize("lexeme", LEXEMES_FULL)
def test_full_lexemes(lexeme):
    """
    Test that full lexemes are correct.
    """
    forms = parse_full_lexeme(lexeme)
    forms_lower = [(w.lower(), tag) for w, tag in forms]
    for word, tag in forms:
        assert_has_full_lexeme(word, forms_lower)


def assert_has_full_lexeme(word, forms):
    for p in morph.parse(word):
        lexeme_forms = [(f.word, str(f.tag)) for f in p.lexeme]
        if lexeme_forms == forms:
            return
    raise AssertionError("Word %s doesn't have lexeme %s" % (word, forms))


def _lexemes_for_word(word):
    res = []
    for p in morph.parse(word):
        res.append(tuple(f.word for f in p.lexeme))
    return res


########NEW FILE########
__FILENAME__ = test_numeral_agreement
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import pytest

from .utils import morph


@pytest.mark.parametrize(('word', 'result'), [
    # прилагательные
    ("бесплатная", ["бесплатная", "бесплатные", "бесплатных"]),
    ("бесплатный", ["бесплатный", "бесплатных", "бесплатных"]),

    # числительные
    ("первый", ["первый", "первых", "первых"]),
    ("первая", ["первая", "первые", "первых"]),

    # существительные
    ("книга", ["книга", "книги", "книг"]),
    ("болт", ["болт", "болта", "болтов"]),

    # причастия
    ("летящий", ["летящий", "летящих", "летящих"]),
    ("летящая", ["летящая", "летящие", "летящих"]),

    # остальное части речи мы никак не согласовываем с числами
    ("играет", ["играет", "играет", "играет"])
])
def test_plural_forms(word, result):
    parsed = morph.parse(word)
    assert len(parsed)
    for plural, num in zip(result, [1, 2, 5]):
        assert parsed[0].make_agree_with_number(num).word == plural


@pytest.mark.parametrize(('word', 'case', 'result'), [
    ("книги", 'gent', ["книги", "книг", "книг"]),
    ("книге", 'datv', ["книге", "книгам", "книгам"]),
    ("книгу", 'accs', ["книгу", "книги", "книг"]),
    ("книгой", 'ablt', ["книгой", "книгами", "книгами"]),
    ("книге", 'loct', ["книге", "книгах", "книгах"]),

    ("час", "accs", ["час", "часа", "часов"]), # see https://github.com/kmike/pymorphy2/issues/32
    ("день", "accs", ["день", "дня", "дней"]),
    ("минуту", "accs", ["минуту", "минуты", "минут"]),
])
def test_plural_inflected(word, case, result):
    parsed = [p for p in morph.parse(word) if p.tag.case == case]
    assert len(parsed)
    for plural, num in zip(result, [1, 2, 5]):
        assert parsed[0].make_agree_with_number(num).word == plural


@pytest.mark.parametrize(('word', 'num', 'result'), [
    ("лопата", 0, "лопат"),
    ("лопата", 1, "лопата"),
    ("лопата", 2, "лопаты"),
    ("лопата", 4, "лопаты"),
    ("лопата", 5, "лопат"),
    ("лопата", 6, "лопат"),
    ("лопата", 11, "лопат"),
    ("лопата", 12, "лопат"),
    ("лопата", 15, "лопат"),
    ("лопата", 21, "лопата"),
    ("лопата", 24, "лопаты"),
    ("лопата", 25, "лопат"),
    ("лопата", 101, "лопата"),
    ("лопата", 103, "лопаты"),
    ("лопата", 105, "лопат"),
    ("лопата", 111, "лопат"),
    ("лопата", 112, "лопат"),
    ("лопата", 151, "лопата"),
    ("лопата", 122, "лопаты"),
    ("лопата", 5624, "лопаты"),
    ("лопата", 5431, "лопата"),
    ("лопата", 7613, "лопат"),
    ("лопата", 2111, "лопат"),
])
def test_plural_num(word, num, result):
    parsed = morph.parse(word)
    assert len(parsed)
    assert parsed[0].make_agree_with_number(num).word == result

########NEW FILE########
__FILENAME__ = test_opencorpora_dict
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
import pymorphy2
from pymorphy2.opencorpora_dict.compile import (_to_paradigm,
                                                convert_to_pymorphy2)
from pymorphy2.opencorpora_dict.parse import parse_opencorpora_xml
from pymorphy2.dawg import assert_can_create
from pymorphy2.test_suite_generator import make_test_suite

import pytest


class TestToyDictionary:

    XML_PATH = os.path.join(
        os.path.dirname(__file__),
        '..',
        'dev_data',
        'toy_dict.xml'
    )

    def test_parse_xml(self):
        dct = parse_opencorpora_xml(self.XML_PATH)
        assert dct.version == '0.92'
        assert dct.revision == '389440'

        assert dct.links[0] == ('5', '6', '1')
        assert len(dct.links) == 12

        assert dct.grammemes[1] == ('NOUN', 'POST', 'СУЩ', 'имя существительное')
        assert len(dct.grammemes) == 111

        assert dct.lexemes['14'] == [('ёжиться', 'INFN,impf,intr')]

    def test_convert_to_pymorphy2(self, tmpdir):

        # import logging
        # from pymorphy2.opencorpora_dict.compile import logger
        # logger.setLevel(logging.DEBUG)
        # logger.addHandler(logging.StreamHandler())

        try:
            assert_can_create()
        except NotImplementedError as e:
            raise pytest.skip(e)

        # create a dictionary
        out_path = str(tmpdir.join('dicts'))
        options = {
            'min_paradigm_popularity': 0,
            'min_ending_freq': 0,
        }
        convert_to_pymorphy2(self.XML_PATH, out_path, overwrite=True,
                             prediction_options=options)

        # use it
        morph = pymorphy2.MorphAnalyzer(out_path, probability_estimator_cls=None)
        assert morph.tag('ёжиться') == [morph.TagClass('INFN,impf,intr')]

    def test_test_suite_generator(self, tmpdir):
        # just make sure it doesn't raise an exception
        out_path = tmpdir.join('test_suite.txt')
        make_test_suite(self.XML_PATH, str(out_path))
        out_path.check()


class TestToParadigm(object):

    def test_simple(self):
        lexeme = [
            ["ярче", "COMP,Qual"],
            ["ярчей", "COMP,Qual V-ej"],
        ]
        stem, forms = _to_paradigm(lexeme)
        assert stem == "ярче"
        assert forms == (
            ("", "COMP,Qual", ""),
            ("й", "COMP,Qual V-ej", ""),
        )

    def test_single_prefix(self):
        lexeme = [
            ["ярче", "COMP,Qual"],
            ["поярче", "COMP,Qual Cmp2"],
        ]
        stem, forms = _to_paradigm(lexeme)
        assert stem == "ярче"
        assert forms == (
            ("", "COMP,Qual", ""),
            ("", "COMP,Qual Cmp2", "по"),
        )

    def test_multiple_prefixes(self):
        lexeme = [
            ["ярче", "COMP,Qual"],
            ["ярчей", "COMP,Qual V-ej"],
            ["поярче", "COMP,Qual Cmp2"],
            ["поярчей", "COMP,Qual Cmp2,V-ej"],
            ["наиярчайший", "ADJF,Supr,Qual masc,sing,nomn"],
        ]
        stem, forms = _to_paradigm(lexeme)
        assert stem == 'ярч'

    def test_multiple_prefixes_2(self):
        lexeme = [
            ["подробнейший", 1],
            ["наиподробнейший", 2],
            ["поподробнее", 3]
        ]
        stem, forms = _to_paradigm(lexeme)
        assert stem == 'подробне'
        assert forms == (
            ("йший", 1, ""),
            ("йший", 2, "наи"),
            ("е", 3, "по"),
        )

    def test_platina(self):
        lexeme = [
            ["платиновее", 1],
            ["платиновей", 2],
            ["поплатиновее", 3],
            ["поплатиновей", 4],
        ]
        stem, forms = _to_paradigm(lexeme)
        assert forms == (
            ("е", 1, ""),
            ("й", 2, ""),
            ("е", 3, "по"),
            ("й", 4, "по"),
        )
        assert stem == 'платинове'

    def test_no_prefix(self):
        lexeme = [["английский", 1], ["английского", 2]]
        stem, forms = _to_paradigm(lexeme)
        assert stem == 'английск'
        assert forms == (
            ("ий", 1, ""),
            ("ого", 2, ""),
        )

    def test_single(self):
        lexeme = [["английски", 1]]
        stem, forms = _to_paradigm(lexeme)
        assert stem == 'английски'
        assert forms == (("", 1, ""),)



########NEW FILE########
__FILENAME__ = test_parsing
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import random
import concurrent.futures
import pytest
import pymorphy2
from .utils import morph, assert_parse_is_correct


def _to_test_data(text):
    """
    Lines should be of this format: <word> <normal_form> <tag>.
    Lines that starts with "#" and blank lines are skipped.
    """
    return [l.split(None, 2) for l in text.splitlines()
            if l.strip() and not l.startswith("#")]

# TODO: lines that starts with "XFAIL" excludes the next line from testing.
PARSES = _to_test_data("""
# ========= nouns
кошка       кошка       NOUN,inan,femn sing,nomn

# ========= adjectives
хорошему            хороший     ADJF,Qual masc,sing,datv
лучший              хороший     ADJF,Supr,Qual masc,sing,nomn
наиневероятнейший   вероятный   ADJF,Supr,Qual masc,sing,nomn
наистарейший        старый      ADJF,Supr,Qual masc,sing,nomn

# ========= е/ё
котенок     котёнок     NOUN,anim,masc sing,nomn
котёнок     котёнок     NOUN,anim,masc sing,nomn
озера       озеро       NOUN,inan,neut sing,gent
озера       озеро       NOUN,inan,neut plur,nomn

# ========= particle after a hyphen
ей-то               она-то              NPRO,femn,3per,Anph sing,datv
скажи-ка            сказать-ка          VERB,perf,tran sing,impr,excl
измохратился-таки   измохратиться-таки  VERB,perf,intr masc,sing,past,indc

# ========= compound words with hyphen and immutable left
интернет-магазина       интернет-магазин    NOUN,inan,masc sing,gent
pdf-документов          pdf-документ        NOUN,inan,masc plur,gent
аммиачно-селитрового    аммиачно-селитровый ADJF,Qual masc,sing,gent
быстро-быстро           быстро-быстро       ADVB

# ========= compound words with hyphen and mutable left
команд-участниц     команда-участница   NOUN,inan,femn plur,gent
бегает-прыгает      бегать-прыгать      VERB,impf,intr sing,3per,pres,indc
дул-надувался       дуть-надуваться     VERB,impf,tran masc,sing,past,indc

# ПО- (there were bugs for such words in pymorphy 0.5.6)
почтово-банковский  почтово-банковский  ADJF masc,sing,nomn
по-прежнему         по-прежнему         ADVB

# other old bugs
поездов-экспрессов          поезд-экспресс          NOUN,inan,masc plur,gent
подростками-практикантами   подросток-практикант    NOUN,anim,masc plur,ablt
подводников-североморцев    подводник-североморец   NOUN,anim,masc plur,gent

# cities
санкт-петербурга    санкт-петербург     NOUN,inan,masc,Geox sing,gent
ростове-на-дону     ростов-на-дону      NOUN,inan,masc,Sgtm,Geox sing,loct

# ========= non-dictionary adverbs
по-западному        по-западному        ADVB
по-театральному     по-театральному     ADVB
по-воробьиному      по-воробьиному      ADVB

# ========= hyphenated words with non-cyrillic parts
# this used to raise an exception

Ретро-FM    ретро-fm    LATN

# ====================== non-words
.       .       PNCT
,       ,       PNCT
...     ...     PNCT
?!      ?!      PNCT
-       -       PNCT
…       …       PNCT

123         123         NUMB,intg
0           0           NUMB,intg
123.1       123.1       NUMB,real
123,1       123,1       NUMB,real
I           i           ROMN
MCMLXXXIX   mcmlxxxix   ROMN
XVIII       xviii       ROMN

# ========= LATN
Foo     foo     LATN
I       i       LATN

# ========= UNKN
ьё      ьё      UNKN

# ============== common lowercased abbreviations
# should normal forms be expanded?

руб     рубль       NOUN,inan,masc,Fixd,Abbr plur,gent
млн     миллион     NOUN,inan,masc,Fixd,Abbr plur,gent
тыс     тысяча      NOUN,inan,femn,Fixd,Abbr plur,gent
ст      ст          NOUN,inan,femn,Fixd,Abbr sing,accs
""")

PARSES_UPPER = [(w.upper(), norm, tag) for (w, norm, tag) in PARSES]
PARSES_TITLE = [(w.title(), norm, tag) for (w, norm, tag) in PARSES]

SYSTEMATIC_ERRORS = _to_test_data("""
# ============== foreign first names
Уилл    уилл        NOUN,anim,masc,Name sing,nomn
Джеф    джеф        NOUN,anim,masc,Name sing,nomn

# ============== last names
Сердюков    сердюков    NOUN,anim,masc,Surn sing,nomn
Третьяк     третьяк     NOUN,anim,masc,Surn sing,nomn

# ============== common lowercased abbreviations
# should normal forms be expanded?

г       г       NOUN,inan,masc,Fixd,Abbr sing,loc2
п       п       NOUN,inan,masc,Fixd,Abbr sing,accs

# ============== uppercased abbreviations
# it seems is not possible to properly guess gender and number

ГКРФ        гкрф    NOUN,inan,masc,Sgtm,Fixd,Abbr sing,nomn
ПДД         пдд     NOUN,inan,neut,Pltm,Fixd,Abbr plur,nomn
ФП          фп      NOUN,inan,neut,Sgtm,Fixd,Abbr sing,nomn
ООП         ооп     NOUN,inan,neut,Sgtm,Fixd,Abbr sing,nomn
ПИН         пин     NOUN,inan,masc,Sgtm,Fixd,Abbr sing,nomn
УБРиР       убрир   NOUN,inan,masc,Abbr sing,nomn
УБРиРе      убрир   NOUN,inan,masc,Abbr sing,ablt
УБРиР-е     убрир   NOUN,inan,masc,Abbr sing,ablt

# =============== numerals
3-го        3-й     ADJF,Anum masc,sing,gent
41-й        41-й    ADJF,Anum masc,sing,nomn
41-м        41-м    ADJF,Anum masc,sing,loct
2001-й      2001-й  ADJF,Anum masc,sing,nomn
8-му        8-й     ADJF,Anum masc,sing,datv
3-х         3       NUMR,gent

уловка-22   уловка-22   NOUN,inan,femn sing,nomn

""")


def run_for_all(parses):
    return pytest.mark.parametrize(("word", "normal_form", "tag"), parses)


# ====== Tests:
def _test_has_parse(parses):
    @run_for_all(parses)
    def test_case(word, normal_form, tag):
        parse = morph.parse(word)
        assert_parse_is_correct(parse, word, normal_form, tag)

    return test_case

test_has_parse = _test_has_parse(PARSES)
test_has_parse_title = _test_has_parse(PARSES_TITLE)
test_has_parse_upper = _test_has_parse(PARSES_UPPER)

test_has_parse_systematic_errors = pytest.mark.xfail(_test_has_parse(SYSTEMATIC_ERRORS))


def _test_tag(parses):
    @run_for_all(parses)
    def test_tag_produces_the_same_as_parse(word, normal_form, tag):
        """
        Check if morph.tag produces the same results as morph.parse.
        """
        assert set(morph.tag(word)) == set(p.tag for p in morph.parse(word))

    return test_tag_produces_the_same_as_parse

test_tag = _test_tag(PARSES)
test_tag_title = _test_tag(PARSES_TITLE)
test_tag_upper = _test_tag(PARSES_UPPER)

########NEW FILE########
__FILENAME__ = test_result_wrapper
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from .utils import morph

def test_indexing():
    assert len(morph.parse('стреляли')) == 1
    p = morph.parse('стреляли')[0]

    assert p[0] == 'стреляли' # word
    assert p[1].POS == 'VERB' # tag
    assert p[2] == 'стрелять'

    assert p[0] == p.word
    assert p[1] == p.tag
    assert p[2] == p.normal_form

def test_inflect_valid():
    p = morph.parse('стреляли')[0]
    assert p.inflect(set(['femn'])).word == 'стреляла'

def test_inflect_invalid():
    p = morph.parse('стреляли')[0]
    assert p.inflect(set(['NOUN'])) == None


def test_is_known():
    assert morph.parse('стреляли')[0].is_known
    assert not morph.parse('сптриояли')[0].is_known

def test_normalized():
    assert morph.parse('стреляли')[0].normalized.word == 'стрелять'

########NEW FILE########
__FILENAME__ = test_tagset
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import pickle
import pytest

import pymorphy2
from pymorphy2.tagset import OpencorporaTag
from .utils import morph
Tag = morph.TagClass


def test_hashing():
    tag1 = Tag('NOUN')
    tag2 = Tag('NOUN')
    tag3 = Tag('VERB')

    assert tag1 == tag2
    assert tag1 != tag3
    assert set([tag1]) == set([tag2])
    assert set([tag3]) != set([tag1])


@pytest.mark.parametrize(("tag", "cls"), [
        ['NOUN', 'NOUN'],
        ['NOUN,sing', 'NOUN'],
        ['NOUN sing', 'NOUN'],
    ])
def test_cls(tag, cls):
    assert Tag(tag).POS == cls


def test_repr():
    assert repr(Tag('NOUN anim,plur')) == "OpencorporaTag('NOUN anim,plur')"


# Cloning of the Tag class is disabled to allow pickling
@pytest.mark.xfail
def test_extra_grammemes():
    m = pymorphy2.MorphAnalyzer()

    assert m.TagClass.KNOWN_GRAMMEMES is not Tag.KNOWN_GRAMMEMES
    assert m.TagClass.KNOWN_GRAMMEMES is not OpencorporaTag.KNOWN_GRAMMEMES

    assert 'new_grammeme' not in Tag.KNOWN_GRAMMEMES
    assert 'new_grammeme' not in m.TagClass.KNOWN_GRAMMEMES

    m.TagClass.KNOWN_GRAMMEMES.add('new_grammeme')

    new_tag = m.TagClass('NOUN,sing,new_grammeme')

    assert 'new_grammeme' in new_tag
    assert 'new_grammeme' in m.TagClass.KNOWN_GRAMMEMES
    assert 'new_grammeme' not in OpencorporaTag.KNOWN_GRAMMEMES
    assert 'new_grammeme' not in Tag.KNOWN_GRAMMEMES


def test_len():
    assert len(Tag('NOUN')) == 1
    assert len(Tag('NOUN plur')) == 2
    assert len(Tag('NOUN plur,masc')) == 3
    assert len(Tag('NOUN,plur,masc')) == 3


def test_pickle():
    tag = Tag('NOUN')
    data = pickle.dumps(tag, pickle.HIGHEST_PROTOCOL)
    tag_unpickled = pickle.loads(data)
    assert tag == tag_unpickled


def test_pickle_custom():
    m = pymorphy2.MorphAnalyzer()
    m.TagClass.KNOWN_GRAMMEMES.add('new_grammeme')
    tag = m.TagClass('new_grammeme')
    data = pickle.dumps(tag, pickle.HIGHEST_PROTOCOL)
    tag_unpickled = pickle.loads(data)
    assert tag == tag_unpickled


class TestUpdated:

    def test_number(self):
        tag = Tag('NOUN,sing,masc')
        grammemes = tag.updated_grammemes(required=set(['plur']))
        assert grammemes == set(['NOUN', 'plur'])

    def test_order(self):
        tag = Tag('VERB,impf,tran sing,3per,pres,indc')
        grammemes = tag.updated_grammemes(required=set(['1per']))
        assert grammemes == set('VERB,sing,impf,tran,1per,pres,indc'.split(','))


class TestAttributes:

    def test_attributes(self):
        tag = Tag('VERB,impf,tran sing,3per,pres,indc')
        assert tag.POS == 'VERB'
        assert tag.gender is None
        assert tag.animacy is None
        assert tag.number == 'sing'
        assert tag.case is None
        assert tag.tense == 'pres'
        assert tag.aspect == 'impf'
        assert tag.mood == 'indc'
        assert tag.person == '3per'
        assert tag.transitivity == 'tran'
        assert tag.voice is None # ?
        assert tag.involvement is None

    def test_attributes2(self):
        tag = Tag('NOUN,inan,masc plur,accs')
        assert tag.POS == 'NOUN'
        assert tag.gender == 'masc'
        assert tag.animacy == 'inan'
        assert tag.number == 'plur'
        assert tag.case == 'accs'
        assert tag.tense is None
        assert tag.aspect is None
        assert tag.mood is None
        assert tag.person is None
        assert tag.transitivity is None
        assert tag.voice is None
        assert tag.involvement is None

    def test_attributes3(self):
        tag = Tag('PRTF,impf,tran,pres,pssv inan,masc,sing,accs')
        assert tag.voice == 'pssv'

    def test_attributes4(self):
        tag = Tag('VERB,perf,tran plur,impr,excl')
        assert tag.involvement == 'excl'

    def test_attribute_exceptions(self):
        tag = Tag('NOUN,inan,masc plur,accs')

        with pytest.raises(ValueError):
            tag.POS == 'hello'

        with pytest.raises(ValueError):
            tag.POS == 'noun'

    def test_attributes_as_set_items(self):
        tag = Tag('NOUN,inan,masc plur,accs')

        # this doesn't raise an exception
        assert tag.gender in set(['masc', 'sing'])


class TestContains:

    def test_contains_correct(self):
        tag_text = 'VERB,perf,tran plur,impr,excl'
        tag = Tag(tag_text)
        for grammeme in tag_text.replace(' ', ',').split(','):
            assert grammeme in tag

    def test_not_contains(self):
        # we need to use a prepared Tag class for this to work
        tag = Tag('VERB,perf,tran plur,impr,excl')

        assert 'VERB' in tag
        assert 'NOUN' not in tag
        assert 'sing' not in tag
        assert 'Dist' not in tag

    def test_contains_error(self):
        # we need to use a prepared Tag class for this to work
        tag = Tag('VERB,perf,tran plur,impr,excl')

        with pytest.raises(ValueError):
            assert 'foo' in tag

        with pytest.raises(ValueError):
            assert 'VERP' in tag

    def test_contains_set(self):
        tag = Tag('VERB,perf,tran plur,impr,excl')
        assert set(['VERB', 'perf']) in tag
        assert set(['VERB', 'sing']) not in tag

        assert set() in tag # ??

        with pytest.raises(ValueError):
            assert set(['VERB', 'pref']) in tag


class TestCyrillic:
    def test_cyr_repr(self):
        tag = Tag('VERB,perf,tran plur,impr,excl')
        assert tag.cyr_repr == 'ГЛ,сов,перех мн,повел,выкл'

    def test_grammemes_cyr(self):
        tag = Tag('VERB,perf,tran plur,impr,excl')
        assert tag.grammemes_cyr == frozenset(['ГЛ','сов','перех', 'мн','повел','выкл'])

    def test_cyr_extra_grammemes(self):
        tag = Tag('ROMN')
        assert tag.cyr_repr == 'РИМ'

    @pytest.mark.parametrize(('lat', 'cyr'), [
        ('VERB,perf,tran plur,impr,excl', 'ГЛ,сов,перех мн,повел,выкл'),
        ('ROMN', 'РИМ'),
        ('ROMN,unknown_grammeme', 'РИМ,unknown_grammeme'),
        ('plur', 'мн'),
    ])
    def test_lat2cyr(self, lat, cyr):
        assert Tag.lat2cyr(lat) == cyr
        assert Tag.cyr2lat(cyr) == lat

########NEW FILE########
__FILENAME__ = test_threading
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import concurrent.futures
import random
import pytest
import pymorphy2
from .utils import morph, assert_parse_is_correct
from .test_parsing import PARSES


def _check_analyzer(morph, parses):
    for word, normal_form, tag in parses:
        parse = morph.parse(word)
        assert_parse_is_correct(parse, word, normal_form, tag)


def _check_new_analyzer(parses):
    morph = pymorphy2.MorphAnalyzer()
    for word, normal_form, tag in parses:
        parse = morph.parse(word)
        assert_parse_is_correct(parse, word, normal_form, tag)


def _create_morph_analyzer(i):
    morph = pymorphy2.MorphAnalyzer()
    word, normal_form, tag = random.choice(PARSES)
    parse = morph.parse(word)
    assert_parse_is_correct(parse, word, normal_form, tag)


def test_threading_single_morph_analyzer():
    with concurrent.futures.ThreadPoolExecutor(3) as executor:
        res = list(executor.map(_check_analyzer, [morph]*10, [PARSES]*10))


@pytest.mark.xfail  # See https://github.com/kmike/pymorphy2/issues/37
def test_threading_multiple_morph_analyzers():
    with concurrent.futures.ThreadPoolExecutor(3) as executor:
        res = list(executor.map(_check_new_analyzer, [PARSES]*10))


@pytest.mark.xfail  # See https://github.com/kmike/pymorphy2/issues/37
def test_threading_create_analyzer():
    with concurrent.futures.ThreadPoolExecutor(3) as executor:
        res = list(executor.map(_create_morph_analyzer, range(10)))

########NEW FILE########
__FILENAME__ = test_tokenizers
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from pymorphy2.tokenizers import simple_word_tokenize

class TestSimpleWordTokenize:

    def test_split_simple(self):
        assert simple_word_tokenize('Мама мыла раму') == ['Мама', 'мыла', 'раму']
        assert simple_word_tokenize('Постой, паровоз!') == ['Постой', ',', 'паровоз', '!']

    def test_split_hyphen(self):
        assert simple_word_tokenize('Ростов-на-Дону') == ['Ростов-на-Дону']
        assert simple_word_tokenize('Ура - победа') == ['Ура', '-', 'победа']

    def test_split_signs(self):
        assert simple_word_tokenize('a+b=c_1') == ['a','+','b','=','c_1']

    def test_exctract_words(self):
        text = '''Это  отразилось: на количественном,и на качествен_ном
                - росте карельско-финляндского сотрудничества - офигеть! кони+лошади=масло.
                -сказал кто-то --нет--'''

        assert simple_word_tokenize(text) == [
            'Это', 'отразилось', ':', 'на', 'количественном', ',', 'и', 'на',
            'качествен_ном', '-', 'росте', 'карельско-финляндского',
            'сотрудничества', '-', 'офигеть', '!', 'кони', '+', 'лошади',
            '=', 'масло', '.', '-сказал', 'кто-то', '--нет--',
        ]

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import pymorphy2

morph = pymorphy2.MorphAnalyzer()

def assert_parse_is_correct(parses, word, normal_form, tag):
    """
    Check if one of the word parses has normal form ``normal_form``
    and tag ``tag``.
    """
    for p in parses:
        if p.normal_form == normal_form and str(p.tag) == tag:
            return
    assert False, parses


########NEW FILE########
