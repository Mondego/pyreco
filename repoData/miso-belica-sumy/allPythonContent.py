__FILENAME__ = content_based
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from ..models import TfDocumentModel as TfModel


def cosine_similarity(evaluated_model, reference_model):
    """
    Computes cosine similarity of two text documents. Each document
    has to be represented as TF model of non-empty document.

    :returns float:
        0 <= cos <= 1, where 0 means independence and 1 means
        exactly the same.
    """
    if not (isinstance(evaluated_model, TfModel) and isinstance(reference_model, TfModel)):
        raise ValueError(
            "Arguments has to be instances of 'sumy.models.TfDocumentModel'")

    terms = frozenset(evaluated_model.terms) | frozenset(reference_model.terms)

    numerator = 0.0
    for term in terms:
        numerator += evaluated_model.term_frequency(term) * reference_model.term_frequency(term)

    denominator = evaluated_model.magnitude * reference_model.magnitude
    if denominator == 0.0:
        raise ValueError("Document model can't be empty. Given %r & %r" % (
            evaluated_model, reference_model))

    return numerator / denominator


def unit_overlap(evaluated_model, reference_model):
    """
    Computes unit overlap of two text documents. Documents
    has to be represented as TF models of non-empty document.

    :returns float:
        0 <= overlap <= 1, where 0 means no match and 1 means
        exactly the same.
    """
    if not (isinstance(evaluated_model, TfModel) and isinstance(reference_model, TfModel)):
        raise ValueError(
            "Arguments has to be instances of 'sumy.models.TfDocumentModel'")

    terms1 = frozenset(evaluated_model.terms)
    terms2 = frozenset(reference_model.terms)

    if not terms1 and not terms2:
        raise ValueError(
            "Documents can't be empty. Please pass the valid documents.")

    common_terms_count = len(terms1 & terms2)
    return common_terms_count / (len(terms1) + len(terms2) - common_terms_count)

########NEW FILE########
__FILENAME__ = coselection
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals


def f_score(evaluated_sentences, reference_sentences, weight=1.0):
    """
    Computation of F-Score measure. It is computed as
    F(E) = ( (W^2 + 1) * P(E) * R(E) ) / ( W^2 * P(E) + R(E) ), where:

    - P(E) is precision metrics of extract E.
    - R(E) is recall metrics of extract E.
    - W is a weighting factor that favours P(E) metrics
      when W > 1 and favours R(E) metrics when W < 1.

    If W = 1.0 (default value) basic F-Score is computed.
    It is equivalent to F(E) = (2 * P(E) * R(E)) / (P(E) + R(E)).

    :parameter iterable evaluated_sentences:
        Sentences of evaluated extract.
    :parameter iterable reference_sentences:
        Sentences of reference extract.
    :returns float:
        Returns 0.0 <= P(E) <= 1.0
    """
    p = precision(evaluated_sentences, reference_sentences)
    r = recall(evaluated_sentences, reference_sentences)

    weight **= 2 # weight = weight^2
    denominator = weight * p + r
    if denominator == 0.0:
        return 0.0
    else:
        return ((weight + 1) * p * r) / denominator


def precision(evaluated_sentences, reference_sentences):
    """
    Intrinsic method of evaluation for extracts. It is computed as
    P(E) = A / B, where:

    - A is count of common sentences occurring in both extracts.
    - B is count of sentences in evaluated extract.

    :parameter iterable evaluated_sentences:
        Sentences of evaluated extract.
    :parameter iterable reference_sentences:
        Sentences of reference extract.
    :returns float:
        Returns 0.0 <= P(E) <= 1.0
    """
    return _divide_evaluation(reference_sentences, evaluated_sentences)


def recall(evaluated_sentences, reference_sentences):
    """
    Intrinsic method of evaluation for extracts. It is computed as
    R(E) = A / C, where:

    - A is count of common sentences in both extracts.
    - C is count of sentences in reference extract.

    :parameter iterable evaluated_sentences:
        Sentences of evaluated extract.
    :parameter iterable reference_sentences:
        Sentences of reference extract.
    :returns float:
        Returns 0.0 <= R(E) <= 1.0
    """
    return _divide_evaluation(evaluated_sentences, reference_sentences)


def _divide_evaluation(numerator_sentences, denominator_sentences):
    denominator_sentences = frozenset(denominator_sentences)
    numerator_sentences = frozenset(numerator_sentences)

    if len(numerator_sentences) == 0 or len(denominator_sentences) == 0:
        raise ValueError("Both collections have to contain at least 1 sentence.")

    common_count = len(denominator_sentences & numerator_sentences)
    choosen_count = len(denominator_sentences)

    assert choosen_count != 0
    return common_count / choosen_count

########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf8 -*-

"""
Sumy - evaluation of automatic text summary.

Usage:
    sumy_eval (random | luhn | edmundson | lsa | text-rank | lex-rank) <reference_summary> [--length=<length>] [--language=<lang>]
    sumy_eval (random | luhn | edmundson | lsa | text-rank | lex-rank) <reference_summary> [--length=<length>] [--language=<lang>] --url=<url>
    sumy_eval (random | luhn | edmundson | lsa | text-rank | lex-rank) <reference_summary> [--length=<length>] [--language=<lang>] --file=<file_path> --format=<file_format>
    sumy_eval --version
    sumy_eval --help

Options:
    <reference_summary>  Path to the file with reference summary.
    --url=<url>          URL address of summarizied message.
    --file=<file>        Path to file with summarizied text.
    --format=<format>    Format of input file. [default: plaintext]
    --length=<length>    Length of summarizied text. It may be count of sentences
                         or percentage of input text. [default: 20%]
    --language=<lang>    Natural language of summarizied text. [default: english]
    --version            Displays version of application.
    --help               Displays this text.

"""

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import sys

from itertools import chain
from docopt import docopt
from .. import __version__
from ..utils import ItemsCount, get_stop_words
from ..models import TfDocumentModel
from .._compat import urllib, to_string
from ..nlp.tokenizers import Tokenizer
from ..parsers.html import HtmlParser
from ..parsers.plaintext import PlaintextParser
from ..summarizers.random import RandomSummarizer
from ..summarizers.luhn import LuhnSummarizer
from ..summarizers.edmundson import EdmundsonSummarizer
from ..summarizers.lsa import LsaSummarizer
from ..summarizers.text_rank import TextRankSummarizer
from ..summarizers.lex_rank import LexRankSummarizer
from ..nlp.stemmers import Stemmer
from . import precision, recall, f_score, cosine_similarity, unit_overlap


HEADERS = {
    "User-Agent": "Sumy (Automatic text summarizer) Version/%s" % __version__,
}
PARSERS = {
    "html": HtmlParser,
    "plaintext": PlaintextParser,
}


def build_random(parser, language):
    return RandomSummarizer()


def build_luhn(parser, language):
    summarizer = LuhnSummarizer(Stemmer(language))
    summarizer.stop_words = get_stop_words(language)

    return summarizer


def build_edmundson(parser, language):
    summarizer = EdmundsonSummarizer(Stemmer(language))
    summarizer.null_words = get_stop_words(language)
    summarizer.bonus_words = parser.significant_words
    summarizer.stigma_words = parser.stigma_words

    return summarizer


def build_lsa(parser, language):
    summarizer = LsaSummarizer(Stemmer(language))
    summarizer.stop_words = get_stop_words(language)

    return summarizer


def build_text_rank(parser, language):
    summarizer = TextRankSummarizer(Stemmer(language))
    summarizer.stop_words = get_stop_words(language)

    return summarizer


def build_lex_rank(parser, language):
    summarizer = LexRankSummarizer(Stemmer(language))
    summarizer.stop_words = get_stop_words(language)

    return summarizer


def evaluate_cosine_similarity(evaluated_sentences, reference_sentences):
    evaluated_words = tuple(chain(*(s.words for s in evaluated_sentences)))
    reference_words = tuple(chain(*(s.words for s in reference_sentences)))
    evaluated_model = TfDocumentModel(evaluated_words)
    reference_model = TfDocumentModel(reference_words)

    return cosine_similarity(evaluated_model, reference_model)


def evaluate_unit_overlap(evaluated_sentences, reference_sentences):
    evaluated_words = tuple(chain(*(s.words for s in evaluated_sentences)))
    reference_words = tuple(chain(*(s.words for s in reference_sentences)))
    evaluated_model = TfDocumentModel(evaluated_words)
    reference_model = TfDocumentModel(reference_words)

    return unit_overlap(evaluated_model, reference_model)


AVAILABLE_METHODS = {
    "random": build_random,
    "luhn": build_luhn,
    "edmundson": build_edmundson,
    "lsa": build_lsa,
    "text-rank": build_text_rank,
    "lex-rank": build_lex_rank,
}
AVAILABLE_EVALUATIONS = (
    ("Precision", False, precision),
    ("Recall", False, recall),
    ("F-score", False, f_score),
    ("Cosine similarity", False, evaluate_cosine_similarity),
    ("Cosine similarity (document)", True, evaluate_cosine_similarity),
    ("Unit overlap", False, evaluate_unit_overlap),
    ("Unit overlap (document)", True, evaluate_unit_overlap),
)


def main(args=None):
    args = docopt(to_string(__doc__), args, version=__version__)
    summarizer, document, items_count, reference_summary = handle_arguments(args)

    evaluated_sentences = summarizer(document, items_count)
    reference_document = PlaintextParser.from_string(reference_summary,
        Tokenizer(args["--language"]))
    reference_sentences = reference_document.document.sentences

    for name, evaluate_document, evaluate in AVAILABLE_EVALUATIONS:
        if evaluate_document:
            result = evaluate(evaluated_sentences, document.sentences)
        else:
            result = evaluate(evaluated_sentences, reference_sentences)
        print("%s: %f" % (name, result))


def handle_arguments(args):
    parser = PARSERS["plaintext"]
    input_stream = sys.stdin

    if args["--url"] is not None:
        parser = PARSERS["html"]
        request = urllib.Request(args["--url"], headers=HEADERS)
        input_stream = urllib.urlopen(request)
    elif args["--file"] is not None:
        parser = PARSERS.get(args["--format"], PlaintextParser)
        input_stream = open(args["--file"], "rb")

    summarizer_builder = AVAILABLE_METHODS["luhn"]
    for method, builder in AVAILABLE_METHODS.items():
        if args[method]:
            summarizer_builder = builder
            break

    items_count = ItemsCount(args["--length"])

    parser = parser(input_stream.read(), Tokenizer(args["--language"]))
    if input_stream is not sys.stdin:
        input_stream.close()

    with open(args["<reference_summary>"], "rb") as file:
        reference_summmary = file.read().decode("utf8")

    return summarizer_builder(parser, args["--language"]), parser.document, items_count, reference_summmary


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        exit(1)
    except Exception as e:
        print(e)
        exit(1)

########NEW FILE########
__FILENAME__ = _document
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from itertools import chain
from ...utils import cached_property
from ..._compat import unicode_compatible


@unicode_compatible
class ObjectDocumentModel(object):
    def __init__(self, paragraphs):
        self._paragraphs = tuple(paragraphs)

    @property
    def paragraphs(self):
        return self._paragraphs

    @cached_property
    def sentences(self):
        sentences = (p.sentences for p in self._paragraphs)
        return tuple(chain(*sentences))

    @cached_property
    def headings(self):
        headings = (p.headings for p in self._paragraphs)
        return tuple(chain(*headings))

    @cached_property
    def words(self):
        words = (p.words for p in self._paragraphs)
        return tuple(chain(*words))

    def __unicode__(self):
        return "<DOM with %d paragraphs>" % len(self.paragraphs)

    def __repr__(self):
        return self.__str__()

########NEW FILE########
__FILENAME__ = _paragraph
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from itertools import chain
from ..._compat import unicode_compatible
from ...utils import cached_property
from ._sentence import Sentence


@unicode_compatible
class Paragraph(object):
    __slots__ = (
        "_sentences",
        "_cached_property_sentences",
        "_cached_property_headings",
        "_cached_property_words",
    )

    def __init__(self, sentences):
        sentences = tuple(sentences)
        for sentence in sentences:
            if not isinstance(sentence, Sentence):
                raise TypeError("Only instances of class 'Sentence' are allowed.")

        self._sentences = sentences

    @cached_property
    def sentences(self):
        return tuple(s for s in self._sentences if not s.is_heading)

    @cached_property
    def headings(self):
        return tuple(s for s in self._sentences if s.is_heading)

    @cached_property
    def words(self):
        return tuple(chain(*(s.words for s in self._sentences)))

    def __unicode__(self):
        return "<Paragraph with %d headings & %d sentences>" % (
            len(self.headings),
            len(self.sentences),
        )

    def __repr__(self):
        return self.__str__()

########NEW FILE########
__FILENAME__ = _sentence
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from ...utils import cached_property
from ..._compat import to_unicode, to_string, unicode_compatible


@unicode_compatible
class Sentence(object):
    __slots__ = ("_text", "_cached_property_words", "_tokenizer", "_is_heading",)

    def __init__(self, text, tokenizer, is_heading=False):
        self._text = to_unicode(text).strip()
        self._tokenizer = tokenizer
        self._is_heading = bool(is_heading)

    @cached_property
    def words(self):
        return self._tokenizer.to_words(self._text)

    @property
    def is_heading(self):
        return self._is_heading

    def __eq__(self, sentence):
        assert isinstance(sentence, Sentence)
        return self._is_heading is sentence._is_heading and self._text == sentence._text

    def __ne__(self, sentence):
        return not self.__eq__(sentence)

    def __hash__(self):
        return hash((self._is_heading, self._text))

    def __unicode__(self):
        return self._text

    def __repr__(self):
        return to_string("<%s: %s>") % (
            "Heading" if self._is_heading else "Sentence",
            self.__str__()
        )

########NEW FILE########
__FILENAME__ = tf
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import math

from pprint import pformat
from collections import Sequence
from .._compat import to_unicode, unicode, string_types, Counter


class TfDocumentModel(object):
    """Term-Frequency document model (term = word)."""
    def __init__(self, words, tokenizer=None):
        if isinstance(words, string_types) and tokenizer is None:
            raise ValueError(
                "Tokenizer has to be given if ``words`` is not a sequence.")
        elif isinstance(words, string_types):
            words = tokenizer.to_words(to_unicode(words))
        elif not isinstance(words, Sequence):
            raise ValueError(
                "Parameter ``words`` has to be sequence or string with tokenizer given.")

        self._terms = Counter(map(unicode.lower, words))
        self._max_frequency = max(self._terms.values()) if self._terms else 1

    @property
    def magnitude(self):
        """
        Lenght/norm/magnitude of vector representation of document.
        This is usually denoted by ||d||.
        """
        return math.sqrt(sum(t**2 for t in self._terms.values()))

    @property
    def terms(self):
        return self._terms.keys()

    def most_frequent_terms(self, count=0):
        """
        Returns ``count`` of terms sorted by their frequency
        in descending order.

        :parameter int count:
            Max. number of returned terms. Value 0 means no limit (default).
        """
        # sort terms by number of occurrences in descending order
        terms = sorted(self._terms.items(), key=lambda i: -i[1])

        terms = tuple(i[0] for i in terms)
        if count == 0:
            return terms
        elif count > 0:
            return terms[:count]
        else:
            raise ValueError(
                "Only non-negative values are allowed for count of terms.")

    def term_frequency(self, term):
        """
        Returns frequency of term in document.

        :returns int:
            Returns count of words in document.
        """
        return self._terms.get(term, 0)

    def normalized_term_frequency(self, term, smooth=0.0):
        """
        Returns normalized frequency of term in document.
        http://nlp.stanford.edu/IR-book/html/htmledition/maximum-tf-normalization-1.html

        :parameter float smooth:
            0.0 <= smooth <= 1.0, generally set to 0.4, although some
            early work used the value 0.5. The term is a smoothing term
            whose role is to damp the contribution of the second term.
            It may be viewed as a scaling down of TF by the largest TF
            value in document.
        :returns float:
            0.0 <= frequency <= 1.0, where 0 means no occurence in document
            and 1 the most frequent term in document.
        """
        frequency = self.term_frequency(term) / self._max_frequency
        return smooth + (1.0 - smooth)*frequency

    def __repr__(self):
        return "<TfDocumentModel %s>" % pformat(self._terms)

########NEW FILE########
__FILENAME__ = czech
# -*- coding: utf8 -*-

"""
Czech stemmer
Copyright © 2010 Luís Gomes <luismsgomes@gmail.com>.

Ported from the Java implementation available at:
    http://members.unine.ch/jacques.savoy/clef/index.html

Usage:
    czech_stemmer.py light|aggressive
"""

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re
import sys

from warnings import warn
from ..._compat import unicode


WORD_PATTERN = re.compile(r"^\w+$", re.UNICODE)


def stem_word(word, aggressive=False):
    if not isinstance(word, unicode):
        word = word.decode("utf8")

    if not WORD_PATTERN.match(word):
        return word

    if not word.islower() and not word.istitle() and not word.isupper():
        warn("skipping word with mixed case: " + word)
        return word

    stem = word.lower()
    stem = _remove_case(stem)
    stem = _remove_possessives(stem)

    if aggressive:
        stem = _remove_comparative(stem)
        stem = _remove_diminutive(stem)
        stem = _remove_augmentative(stem)
        stem = _remove_derivational(stem)

    if word.isupper():
        return stem.upper()
    if word.istitle():
        return stem.title()

    return stem


def _remove_case(word):
    if len(word) > 7 and word.endswith("atech"):
        return word[:-5]

    if len(word) > 6:
        if word.endswith("ětem"):
            return _palatalize(word[:-3])
        if word.endswith("atům"):
            return word[:-4]

    if len(word) > 5:
        if word[-3:] in ("ech", "ich", "ích", "ého", "ěmi", "emi", "ému",
                         "ete", "eti", "iho", "ího", "ími", "imu"):
            return _palatalize(word[:-2])
        if word[-3:] in ("ách", "ata", "aty", "ých", "ama", "ami",
                         "ové", "ovi", "ými"):
            return word[:-3]

    if len(word) > 4:
        if word.endswith("em"):
            return _palatalize(word[:-1])
        if word[-2:] in ("es", "ém", "ím"):
            return _palatalize(word[:-2])
        if word[-2:] in ("ům", "at", "ám", "os", "us", "ým", "mi", "ou"):
            return word[:-2]

    if len(word) > 3:
        if word[-1] in "eiíě":
            return _palatalize(word)
        if word[-1] in "uyůaoáéý":
            return word[:-1]

    return word


def _remove_possessives(word):
    if len(word) > 5:
        if word[-2:] in ("ov", "ův"):
            return word[:-2]
        if word.endswith("in"):
            return _palatalize(word[:-1])
    return word


def _remove_comparative(word):
    if len(word) > 5:
        if word[-3:] in ("ejš", "ějš"):
            return _palatalize(word[:-2])
    return word


def _remove_diminutive(word):
    if len(word) > 7 and word.endswith("oušek"):
        return word[:-5]
    if len(word) > 6:
        if word[-4:] in ("eček", "éček", "iček", "íček", "enek", "ének",
                         "inek", "ínek"):
            return _palatalize(word[:-3])
        if word[-4:] in ("áček", "aček", "oček", "uček", "anek", "onek",
                         "unek", "ánek"):
            return _palatalize(word[:-4])
    if len(word) > 5:
        if word[-3:] in ("ečk", "éčk", "ičk", "íčk", "enk", "énk",
                         "ink", "ínk"):
            return _palatalize(word[:-3])
        if word[-3:] in ("áčk", "ačk", "očk", "učk", "ank", "onk",
                         "unk", "átk", "ánk", "ušk"):
            return word[:-3]
    if len(word) > 4:
        if word[-2:] in ("ek", "ék", "ík", "ik"):
            return _palatalize(word[:-1])
        if word[-2:] in ("ák", "ak", "ok", "uk"):
            return word[:-1]
    if len(word) > 3 and word[-1] == "k":
        return word[:-1]
    return word


def _remove_augmentative(word):
    if len(word) > 6 and word.endswith("ajzn"):
        return word[:-4]
    if len(word) > 5 and word[-3:] in ("izn", "isk"):
        return _palatalize(word[:-2])
    if len(word) > 4 and word.endswith("ák"):
        return word[:-2]
    return word


def _remove_derivational(word):
    if len(word) > 8 and word.endswith("obinec"):
        return word[:-6]
    if len(word) > 7:
        if word.endswith("ionář"):
            return _palatalize(word[:-4])
        if word[-5:] in ("ovisk", "ovstv", "ovišt", "ovník"):
            return word[:-5]
    if len(word) > 6:
        if word[-4:] in ("ásek", "loun", "nost", "teln", "ovec", "ovík",
                         "ovtv", "ovin", "štin"):
            return word[:-4]
        if word[-4:] in ("enic", "inec", "itel"):
            return _palatalize(word[:-3])
    if len(word) > 5:
        if word.endswith("árn"):
            return word[:-3]
        if word[-3:] in ("ěnk", "ián", "ist", "isk", "išt", "itb", "írn"):
            return _palatalize(word[:-2])
        if word[-3:] in ("och", "ost", "ovn", "oun", "out", "ouš",
                         "ušk", "kyn", "čan", "kář", "néř", "ník",
                         "ctv", "stv"):
            return word[:-3]
    if len(word) > 4:
        if word[-2:] in ("áč", "ač", "án", "an", "ář", "as"):
            return word[:-2]
        if word[-2:] in ("ec", "en", "ěn", "éř", "íř", "ic", "in", "ín",
                         "it", "iv"):
            return _palatalize(word[:-1])
        if word[-2:] in ("ob", "ot", "ov", "oň", "ul", "yn", "čk", "čn",
                         "dl", "nk", "tv", "tk", "vk"):
            return word[:-2]
    if len(word) > 3 and word[-1] in "cčklnt":
        return word[:-1]
    return word


def _palatalize(word):
    if word[-2:] in ("ci", "ce", "či", "če"):
        return word[:-2] + "k"

    if word[-2:] in ("zi", "ze", "ži", "že"):
        return word[:-2] + "h"

    if word[-3:] in ("čtě", "čti", "čtí"):
        return word[:-3] + "ck"

    if word[-3:] in ("ště", "šti", "ští"):
        return word[:-3] + "sk"

    return word[:-1]


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ("light", "aggressive"):
        sys.exit(__doc__.encode("utf8"))

    aggressive_stemming = bool(sys.argv[1] == "aggressive")
    for line in sys.stdin:
        words = tuple(w.decode("utf8") + " " + stem_word(w, aggressive_stemming) for w in line.split())
        print(*map(lambda s: s.encode("utf8"), words))

########NEW FILE########
__FILENAME__ = tokenizers
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re
import nltk

from .._compat import to_string, to_unicode, unicode


class Tokenizer(object):
    """Language dependent tokenizer of text document."""

    _WORD_PATTERN = re.compile(r"^[^\W\d_]+$", re.UNICODE)
    # feel free to contribute if you have better tokenizer for any of these languages :)
    LANGUAGE_ALIASES = {
        "slovak": "czech",
    }

    def __init__(self, language):
        self._language = language

        tokenizer_language = self.LANGUAGE_ALIASES.get(language, language)
        self._sentence_tokenizer = self._sentence_tokenizer(tokenizer_language)

    @property
    def language(self):
        return self._language

    def _sentence_tokenizer(self, language):
        path = to_string("tokenizers/punkt/%s.pickle") % to_string(language)
        return nltk.data.load(path)

    def to_sentences(self, paragraph):
        sentences = self._sentence_tokenizer.tokenize(to_unicode(paragraph))
        return tuple(map(unicode.strip, sentences))

    def to_words(self, sentence):
        words = nltk.word_tokenize(to_unicode(sentence))
        return tuple(filter(self._is_word, words))

    def _is_word(self, word):
        return bool(Tokenizer._WORD_PATTERN.search(word))

########NEW FILE########
__FILENAME__ = html
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from breadability.readable import Article
from .._compat import urllib
from ..utils import cached_property
from ..models.dom import Sentence, Paragraph, ObjectDocumentModel
from .parser import DocumentParser


class HtmlParser(DocumentParser):
    """Parser of text from HTML format into DOM."""

    SIGNIFICANT_TAGS = (
        "h1", "h2", "h3",
        "b", "strong",
        "big",
        "dfn",
        "em",
    )

    @classmethod
    def from_string(cls, string, url, tokenizer):
        return cls(string, tokenizer, url)

    @classmethod
    def from_file(cls, file_path, url, tokenizer):
        with open(file_path, "rb") as file:
            return cls(file.read(), tokenizer, url)

    @classmethod
    def from_url(cls, url, tokenizer):
        response = urllib.urlopen(url)
        data = response.read()
        response.close()

        return cls(data, tokenizer, url)

    def __init__(self, html_content, tokenizer, url=None):
        super(HtmlParser, self).__init__(tokenizer)
        self._article = Article(html_content, url)

    @cached_property
    def significant_words(self):
        words = []
        for paragraph in self._article.main_text:
            for text, annotations in paragraph:
                if self._contains_any(annotations, *self.SIGNIFICANT_TAGS):
                    words.extend(self.tokenize_words(text))

        if words:
            return tuple(words)
        else:
            return self.SIGNIFICANT_WORDS

    @cached_property
    def stigma_words(self):
        words = []
        for paragraph in self._article.main_text:
            for text, annotations in paragraph:
                if self._contains_any(annotations, "a", "strike", "s"):
                    words.extend(self.tokenize_words(text))

        if words:
            return tuple(words)
        else:
            return self.STIGMA_WORDS

    def _contains_any(self, sequence, *args):
        if sequence is None:
            return False

        for item in args:
            if item in sequence:
                return True

        return False

    @cached_property
    def document(self):
        # "a", "abbr", "acronym", "b", "big", "blink", "blockquote", "cite", "code",
        # "dd", "del", "dfn", "dir", "dl", "dt", "em", "h", "h1", "h2", "h3", "h4",
        # "h5", "h6", "i", "ins", "kbd", "li", "marquee", "menu", "ol", "pre", "q",
        # "s", "samp", "strike", "strong", "sub", "sup", "tt", "u", "ul", "var",

        annotated_text = self._article.main_text

        paragraphs = []
        for paragraph in annotated_text:
            sentences = []

            current_text = ""
            for text, annotations in paragraph:
                if annotations and ("h1" in annotations or "h2" in annotations or "h3" in annotations):
                    sentences.append(Sentence(text, self._tokenizer, is_heading=True))
                # skip <pre> nodes
                elif not (annotations and "pre" in annotations):
                    current_text += " " + text

            new_sentences = self.tokenize_sentences(current_text)
            sentences.extend(Sentence(s, self._tokenizer) for s in new_sentences)
            paragraphs.append(Paragraph(sentences))

        return ObjectDocumentModel(paragraphs)

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals


class DocumentParser(object):
    """Abstract parser of input format into DOM."""

    SIGNIFICANT_WORDS = (
        "významný",
        "vynikající",
        "podstatný",
        "význačný",
        "důležitý",
        "slavný",
        "zajímavý",
        "eminentní",
        "vlivný",
        "supr",
        "super",
        "nejlepší",
        "dobrý",
        "kvalitní",
        "optimální",
        "relevantní",
    )
    STIGMA_WORDS = (
        "nejhorší",
        "zlý",
        "šeredný",
    )

    def __init__(self, tokenizer):
        self._tokenizer = tokenizer

    def tokenize_sentences(self, paragraph):
        return self._tokenizer.to_sentences(paragraph)

    def tokenize_words(self, sentence):
        return self._tokenizer.to_words(sentence)

########NEW FILE########
__FILENAME__ = plaintext
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from .._compat import to_unicode
from ..utils import cached_property
from ..models.dom import Sentence, Paragraph, ObjectDocumentModel
from .parser import DocumentParser


class PlaintextParser(DocumentParser):
    @classmethod
    def from_string(cls, string, tokenizer):
        return cls(string, tokenizer)

    @classmethod
    def from_file(cls, file_path, tokenizer):
        with open(file_path) as file:
            return cls(file.read(), tokenizer)

    def __init__(self, text, tokenizer):
        super(PlaintextParser, self).__init__(tokenizer)
        self._text = to_unicode(text).strip()

    @cached_property
    def significant_words(self):
        words = []
        for paragraph in self.document.paragraphs:
            for heading in paragraph.headings:
                words.extend(heading.words)

        if words:
            return tuple(words)
        else:
            return self.SIGNIFICANT_WORDS

    @cached_property
    def stigma_words(self):
        return self.STIGMA_WORDS

    @cached_property
    def document(self):
        current_paragraph = []
        paragraphs = []
        for line in self._text.splitlines():
            line = line.strip()
            if line.isupper():
                heading = Sentence(line, self._tokenizer, is_heading=True)
                current_paragraph.append(heading)
            elif not line and current_paragraph:
                sentences = self._to_sentences(current_paragraph)
                paragraphs.append(Paragraph(sentences))
                current_paragraph = []
            elif line:
                current_paragraph.append(line)

        sentences = self._to_sentences(current_paragraph)
        paragraphs.append(Paragraph(sentences))

        return ObjectDocumentModel(paragraphs)

    def _to_sentences(self, lines):
        text = ""
        sentence_objects = []

        for line in lines:
            if isinstance(line, Sentence):
                if text:
                    sentences = self.tokenize_sentences(text)
                    sentence_objects += map(self._to_sentence, sentences)

                sentence_objects.append(line)
                text = ""
            else:
                text += " " + line

        text = text.strip()
        if text:
            sentences = self.tokenize_sentences(text)
            sentence_objects += map(self._to_sentence, sentences)

        return sentence_objects

    def _to_sentence(self, text):
        assert text.strip()
        return Sentence(text, self._tokenizer)

########NEW FILE########
__FILENAME__ = edmundson
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from collections import defaultdict
from ..nlp.stemmers import null_stemmer
from ._summarizer import AbstractSummarizer
from .edmundson_cue import EdmundsonCueMethod
from .edmundson_key import EdmundsonKeyMethod
from .edmundson_title import EdmundsonTitleMethod
from .edmundson_location import EdmundsonLocationMethod


_EMPTY_SET = frozenset()


class EdmundsonSummarizer(AbstractSummarizer):
    _bonus_words = _EMPTY_SET
    _stigma_words = _EMPTY_SET
    _null_words = _EMPTY_SET

    def __init__(self, stemmer=null_stemmer, cue_weight=1.0, key_weight=0.0,
            title_weight=1.0, location_weight=1.0):
        super(EdmundsonSummarizer, self).__init__(stemmer)

        self._ensure_correct_weights(cue_weight, key_weight, title_weight,
            location_weight)

        self._cue_weight = float(cue_weight)
        self._key_weight = float(key_weight)
        self._title_weight = float(title_weight)
        self._location_weight = float(location_weight)

    def _ensure_correct_weights(self, *weights):
        for w in weights:
            if w < 0.0:
                raise ValueError("Negative wights are not allowed.")

    @property
    def bonus_words(self):
        return self._bonus_words

    @bonus_words.setter
    def bonus_words(self, collection):
        self._bonus_words = frozenset(map(self.stem_word, collection))

    @property
    def stigma_words(self):
        return self._stigma_words

    @stigma_words.setter
    def stigma_words(self, collection):
        self._stigma_words = frozenset(map(self.stem_word, collection))

    @property
    def null_words(self):
        return self._null_words

    @null_words.setter
    def null_words(self, collection):
        self._null_words = frozenset(map(self.stem_word, collection))

    def __call__(self, document, sentences_count):
        ratings = defaultdict(int)

        if self._cue_weight > 0.0:
            method = self._build_cue_method_instance()
            ratings = self._update_ratings(ratings, method.rate_sentences(document))
        if self._key_weight > 0.0:
            method = self._build_key_method_instance()
            ratings = self._update_ratings(ratings, method.rate_sentences(document))
        if self._title_weight > 0.0:
            method = self._build_title_method_instance()
            ratings = self._update_ratings(ratings, method.rate_sentences(document))
        if self._location_weight > 0.0:
            method = self._build_location_method_instance()
            ratings = self._update_ratings(ratings, method.rate_sentences(document))

        return self._get_best_sentences(document.sentences, sentences_count, ratings)

    def _update_ratings(self, ratings, new_ratings):
        assert len(ratings) == 0 or len(ratings) == len(new_ratings)

        for sentence, rating in new_ratings.items():
            ratings[sentence] += rating

        return ratings

    def cue_method(self, document, sentences_count, bunus_word_value=1, stigma_word_value=1):
        summarization_method = self._build_cue_method_instance()
        return summarization_method(document, sentences_count, bunus_word_value,
            stigma_word_value)

    def _build_cue_method_instance(self):
        self.__check_bonus_words()
        self.__check_stigma_words()

        return EdmundsonCueMethod(self._stemmer, self._bonus_words, self._stigma_words)

    def key_method(self, document, sentences_count, weight=0.5):
        summarization_method = self._build_key_method_instance()
        return summarization_method(document, sentences_count, weight)

    def _build_key_method_instance(self):
        self.__check_bonus_words()

        return  EdmundsonKeyMethod(self._stemmer, self._bonus_words)

    def title_method(self, document, sentences_count):
        summarization_method = self._build_title_method_instance()
        return summarization_method(document, sentences_count)

    def _build_title_method_instance(self):
        self.__check_null_words()

        return EdmundsonTitleMethod(self._stemmer, self._null_words)

    def location_method(self, document, sentences_count, w_h=1, w_p1=1, w_p2=1, w_s1=1, w_s2=1):
        summarization_method = self._build_location_method_instance()
        return summarization_method(document, sentences_count, w_h, w_p1, w_p2, w_s1, w_s2)

    def _build_location_method_instance(self):
        self.__check_null_words()

        return EdmundsonLocationMethod(self._stemmer, self._null_words)

    def __check_bonus_words(self):
        if not self._bonus_words:
            raise ValueError("Set of bonus words is empty. Please set attribute 'bonus_words' with collection of words.")

    def __check_stigma_words(self):
        if not self._stigma_words:
            raise ValueError("Set of stigma words is empty. Please set attribute 'stigma_words' with collection of words.")

    def __check_null_words(self):
        if not self._null_words:
            raise ValueError("Set of null words is empty. Please set attribute 'null_words' with collection of words.")

########NEW FILE########
__FILENAME__ = edmundson_cue
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from ._summarizer import AbstractSummarizer


class EdmundsonCueMethod(AbstractSummarizer):
    def __init__(self, stemmer, bonus_words, stigma_words):
        super(EdmundsonCueMethod, self).__init__(stemmer)
        self._bonus_words = bonus_words
        self._stigma_words = stigma_words

    def __call__(self, document, sentences_count, bunus_word_weight, stigma_word_weight):
        return self._get_best_sentences(document.sentences,
            sentences_count, self._rate_sentence, bunus_word_weight,
            stigma_word_weight)

    def _rate_sentence(self, sentence, bunus_word_weight, stigma_word_weight):
        # count number of bonus/stigma words in sentece
        words = map(self.stem_word, sentence.words)
        bonus_words_count, stigma_words_count = self._count_words(words)

        # compute positive & negative rating
        bonus_rating = bonus_words_count*bunus_word_weight
        stigma_rating = stigma_words_count*stigma_word_weight

        # rating of sentence is (positive - negative) rating
        return bonus_rating - stigma_rating

    def _count_words(self, words):
        """
        Counts number of bonus/stigma words.

        :param iterable words:
            Collection of words.
        :returns pair:
            Tuple with number of words (bonus words, stigma words).
        """
        bonus_words_count = 0
        stigma_words_count = 0

        for word in words:
            if word in self._bonus_words:
                bonus_words_count +=1
            if word in self._stigma_words:
                stigma_words_count += 1

        return bonus_words_count, stigma_words_count

    def rate_sentences(self, document, bunus_word_weight=1, stigma_word_weight=1):
        rated_sentences = {}
        for sentence in document.sentences:
            rated_sentences[sentence] = self._rate_sentence(sentence,
                bunus_word_weight, stigma_word_weight)

        return rated_sentences

########NEW FILE########
__FILENAME__ = edmundson_key
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from .._compat import Counter
from ._summarizer import AbstractSummarizer


class EdmundsonKeyMethod(AbstractSummarizer):
    def __init__(self, stemmer, bonus_words):
        super(EdmundsonKeyMethod, self).__init__(stemmer)
        self._bonus_words = bonus_words

    def __call__(self, document, sentences_count, weight):
        significant_words = self._compute_significant_words(document, weight)

        return self._get_best_sentences(document.sentences,
            sentences_count, self._rate_sentence, significant_words)

    def _compute_significant_words(self, document, weight):
        # keep only stems contained in bonus words
        words = map(self.stem_word, document.words)
        words = filter(self._is_bonus_word, words)

        # compute frequencies of bonus words in document
        word_counts = Counter(words)
        word_frequencies = word_counts.values()

        # no frequencies means no significant words
        if not word_frequencies:
            return ()

        # return only words greater than weight
        max_word_frequency = max(word_frequencies)
        return tuple(word for word, frequency in word_counts.items()
            if frequency/max_word_frequency > weight)

    def _is_bonus_word(self, word):
        return word in self._bonus_words

    def _rate_sentence(self, sentence, significant_words):
        words = map(self.stem_word, sentence.words)
        return sum(w in significant_words for w in words)

    def rate_sentences(self, document, weight=0.5):
        significant_words = self._compute_significant_words(document, weight)

        rated_sentences = {}
        for sentence in document.sentences:
            rated_sentences[sentence] = self._rate_sentence(sentence,
                significant_words)

        return rated_sentences

########NEW FILE########
__FILENAME__ = edmundson_location
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from itertools import chain
from operator import attrgetter
from .._compat import ffilter
from ._summarizer import AbstractSummarizer


class EdmundsonLocationMethod(AbstractSummarizer):
    def __init__(self, stemmer, null_words):
        super(EdmundsonLocationMethod, self).__init__(stemmer)
        self._null_words = null_words

    def __call__(self, document, sentences_count, w_h, w_p1, w_p2, w_s1, w_s2):
        significant_words = self._compute_significant_words(document)
        ratings = self._rate_sentences(document, significant_words, w_h, w_p1,
            w_p2, w_s1, w_s2)

        return self._get_best_sentences(document.sentences, sentences_count, ratings)

    def _compute_significant_words(self, document):
        headings = document.headings

        significant_words = chain(*map(attrgetter("words"), headings))
        significant_words = map(self.stem_word, significant_words)
        significant_words = ffilter(self._is_null_word, significant_words)

        return frozenset(significant_words)

    def _is_null_word(self, word):
        return word in self._null_words

    def _rate_sentences(self, document, significant_words, w_h, w_p1, w_p2, w_s1, w_s2):
        rated_sentences = {}
        paragraphs = document.paragraphs

        for paragraph_order, paragraph in enumerate(paragraphs):
            sentences = paragraph.sentences
            for sentence_order, sentence in enumerate(sentences):
                rating = self._rate_sentence(sentence, significant_words)
                rating *= w_h

                if paragraph_order == 0:
                    rating += w_p1
                elif paragraph_order == len(paragraphs) - 1:
                    rating += w_p2

                if sentence_order == 0:
                    rating += w_s1
                elif sentence_order == len(sentences) - 1:
                    rating += w_s2

                rated_sentences[sentence] = rating

        return rated_sentences

    def _rate_sentence(self, sentence, significant_words):
        words = map(self.stem_word, sentence.words)
        return sum(w in significant_words for w in words)

    def rate_sentences(self, document, w_h=1, w_p1=1, w_p2=1, w_s1=1, w_s2=1):
        significant_words = self._compute_significant_words(document)
        return self._rate_sentences(document, significant_words, w_h, w_p1, w_p2, w_s1, w_s2)

########NEW FILE########
__FILENAME__ = edmundson_title
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from operator import attrgetter
from itertools import chain
from .._compat import ffilter
from ._summarizer import AbstractSummarizer


class EdmundsonTitleMethod(AbstractSummarizer):
    def __init__(self, stemmer, null_words):
        super(EdmundsonTitleMethod, self).__init__(stemmer)
        self._null_words = null_words

    def __call__(self, document, sentences_count):
        sentences = document.sentences
        significant_words = self._compute_significant_words(document)

        return self._get_best_sentences(sentences, sentences_count,
            self._rate_sentence, significant_words)

    def _compute_significant_words(self, document):
        heading_words = map(attrgetter("words"), document.headings)

        significant_words = chain(*heading_words)
        significant_words = map(self.stem_word, significant_words)
        significant_words = ffilter(self._is_null_word, significant_words)

        return frozenset(significant_words)

    def _is_null_word(self, word):
        return word in self._null_words

    def _rate_sentence(self, sentence, significant_words):
        words = map(self.stem_word, sentence.words)
        return sum(w in significant_words for w in words)

    def rate_sentences(self, document):
        significant_words = self._compute_significant_words(document)

        rated_sentences = {}
        for sentence in document.sentences:
            rated_sentences[sentence] = self._rate_sentence(sentence,
                significant_words)

        return rated_sentences

########NEW FILE########
__FILENAME__ = lex_rank
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import math

try:
    import numpy
except ImportError:
    numpy = None

from ._summarizer import AbstractSummarizer
from .._compat import Counter


class LexRankSummarizer(AbstractSummarizer):
    """
    LexRank: Graph-based Centrality as Salience in Text Summarization
    Source: http://tangra.si.umich.edu/~radev/lexrank/lexrank.pdf
    """
    threshold = 0.1
    epsilon = 0.1
    _stop_words = frozenset()

    @property
    def stop_words(self):
        return self._stop_words

    @stop_words.setter
    def stop_words(self, words):
        self._stop_words = frozenset(map(self.normalize_word, words))

    def __call__(self, document, sentences_count):
        self._ensure_dependecies_installed()

        sentences_words = [self._to_words_set(s) for s in document.sentences]
        tf_metrics = self._compute_tf(sentences_words)
        idf_metrics = self._compute_idf(sentences_words)

        matrix = self._create_matrix(sentences_words, self.threshold, tf_metrics, idf_metrics)
        scores = self.power_method(matrix, self.epsilon)
        ratings = dict(zip(document.sentences, scores))

        return self._get_best_sentences(document.sentences, sentences_count, ratings)

    def _ensure_dependecies_installed(self):
        if numpy is None:
            raise ValueError("LexRank summarizer requires NumPy. Please, install it by command 'pip install numpy'.")

    def _to_words_set(self, sentence):
        words = map(self.normalize_word, sentence.words)
        return [self.stem_word(w) for w in words if w not in self._stop_words]

    def _compute_tf(self, sentences):
        tf_values = map(Counter, sentences)

        tf_metrics = []
        for sentence in tf_values:
            metrics = {}
            max_tf = self._find_tf_max(sentence)

            for term, tf in sentence.items():
                metrics[term] = tf / max_tf

            tf_metrics.append(metrics)

        return tf_metrics

    def _find_tf_max(self, terms):
        return max(terms.values()) if terms else 1

    def _compute_idf(self, sentences):
        idf_metrics = {}
        sentences_count = len(sentences)

        for sentence in sentences:
            for term in sentence:
                if term not in idf_metrics:
                    n_j = sum(1 for s in sentences if term in s)
                    idf_metrics[term] = sentences_count / n_j

        return idf_metrics

    def _create_matrix(self, sentences, threshold, tf_metrics, idf_metrics):
        """
        Creates matrix of shape |sentences|×|sentences|.
        """
        # create matrix |sentences|×|sentences| filled with zeroes
        sentences_count = len(sentences)
        matrix = numpy.zeros((sentences_count, sentences_count))
        degrees = numpy.zeros((sentences_count, ))

        for row, (sentence1, tf1) in enumerate(zip(sentences, tf_metrics)):
            for col, (sentence2, tf2) in enumerate(zip(sentences, tf_metrics)):
                matrix[row, col] = self._compute_cosine(sentence1, sentence2, tf1, tf2, idf_metrics)

                if matrix[row, col] > threshold:
                    matrix[row, col] = 1.0
                    degrees[row] += 1
                else:
                    matrix[row, col] = 0

        for row in range(sentences_count):
            for col in range(sentences_count):
                if degrees[row] == 0:
                    degrees[row] = 1

                matrix[row][col] = matrix[row][col] / degrees[row]

        return matrix

    def _compute_cosine(self, sentence1, sentence2, tf1, tf2, idf_metrics):
        common_words = frozenset(sentence1) & frozenset(sentence2)

        numerator = 0.0
        for term in common_words:
            numerator += tf1[term]*tf2[term] * idf_metrics[term]**2

        denominator1 = sum((tf1[t]*idf_metrics[t])**2 for t in sentence1)
        denominator2 = sum((tf2[t]*idf_metrics[t])**2 for t in sentence2)

        if denominator1 > 0 and denominator2 > 0:
            return numerator / (math.sqrt(denominator1) * math.sqrt(denominator2))
        else:
            return 0.0

    def power_method(self, matrix, epsilon):
        transposed_matrix = matrix.T
        sentences_count = len(matrix)
        p_vector = [1.0 / sentences_count] * sentences_count
        lambda_val = 1.0

        while lambda_val > epsilon:
            next_p = [0] * sentences_count
            for i in range(sentences_count):
                for j in range(sentences_count):
                    next_p[i] += transposed_matrix[j, i] * p_vector[j]

            p_vector = next_p

            lambda_val = sum((next_p[i] - p_vector[i])**2 for i in range(sentences_count))

        return p_vector

########NEW FILE########
__FILENAME__ = lsa
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import math
try:
    import numpy
except ImportError:
    numpy = None

try:
    from numpy.linalg import svd as singular_value_decomposition
except ImportError:
    singular_value_decomposition = None
from ._summarizer import AbstractSummarizer


class LsaSummarizer(AbstractSummarizer):
    MIN_DIMENSIONS = 3
    REDUCTION_RATIO = 1/1
    _stop_words = frozenset()

    @property
    def stop_words(self):
        return self._stop_words

    @stop_words.setter
    def stop_words(self, words):
        self._stop_words = frozenset(map(self.normalize_word, words))

    def __call__(self, document, sentences_count):
        self._ensure_dependecies_installed()

        dictionary = self._create_dictionary(document)
        # empty document
        if not dictionary:
            return ()

        matrix = self._create_matrix(document, dictionary)
        matrix = self._compute_term_frequency(matrix)
        u, sigma, v = singular_value_decomposition(matrix, full_matrices=False)

        ranks = iter(self._compute_ranks(sigma, v))
        return self._get_best_sentences(document.sentences, sentences_count,
            lambda s: next(ranks))

    def _ensure_dependecies_installed(self):
        if numpy is None:
            raise ValueError("LSA summarizer requires NumPy. Please, install it by command 'pip install numpy'.")

    def _create_dictionary(self, document):
        """Creates mapping key = word, value = row index"""
        words = map(self.normalize_word, document.words)
        unique_words = frozenset(self.stem_word(w) for w in words if w not in self._stop_words)

        return dict((w, i) for i, w in enumerate(unique_words))

    def _create_matrix(self, document, dictionary):
        """
        Creates matrix of shape |unique words|×|sentences| where cells
        contains number of occurences of words (rows) in senteces (cols).
        """
        sentences = document.sentences

        # create matrix |unique words|×|sentences| filled with zeroes
        words_count = len(dictionary)
        sentences_count = len(sentences)
        assert words_count >= sentences_count, "Number of words (%d) should be larger than number of sentences (%d)" % (words_count, sentences_count)
        matrix = numpy.zeros((words_count, sentences_count))

        for col, sentence in enumerate(sentences):
            for word in map(self.stem_word, sentence.words):
                # only valid words is counted (not stop-words, ...)
                if word in dictionary:
                    row = dictionary[word]
                    matrix[row, col] += 1

        return matrix

    def _compute_term_frequency(self, matrix, smooth=0.4):
        """
        Computes TF metrics for each sentence (column) in the given matrix.
        You can read more about smoothing parameter at URL below:
        http://nlp.stanford.edu/IR-book/html/htmledition/maximum-tf-normalization-1.html
        """
        assert 0.0 <= smooth < 1.0

        max_word_frequencies = numpy.max(matrix, axis=0)
        rows, cols = matrix.shape
        for row in range(rows):
            for col in range(cols):
                max_word_frequency = max_word_frequencies[col]
                if max_word_frequency != 0:
                    frequency = matrix[row, col]/max_word_frequency
                    matrix[row, col] = smooth + (1.0 - smooth)*frequency

        return matrix

    def _compute_ranks(self, sigma, v_matrix):
        assert len(sigma) == v_matrix.shape[0], "Matrices should be multiplicable"

        dimensions = max(LsaSummarizer.MIN_DIMENSIONS,
            int(len(sigma)*LsaSummarizer.REDUCTION_RATIO))
        powered_sigma = tuple(s**2 if i < dimensions else 0.0
            for i, s in enumerate(sigma))

        ranks = []
        # iterate over columns of matrix (rows of transposed matrix)
        for column_vector in v_matrix.T:
            rank = sum(s*v**2 for s, v in zip(powered_sigma, column_vector))
            ranks.append(math.sqrt(rank))

        return ranks

########NEW FILE########
__FILENAME__ = luhn
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from ..models import TfDocumentModel
from ._summarizer import AbstractSummarizer


class LuhnSummarizer(AbstractSummarizer):
    max_gap_size = 4
    # TODO: better recognition of significant words (automatic)
    significant_percentage = 1
    _stop_words = frozenset()

    @property
    def stop_words(self):
        return self._stop_words

    @stop_words.setter
    def stop_words(self, words):
        self._stop_words = frozenset(map(self.normalize_word, words))

    def __call__(self, document, sentences_count):
        words = self._get_significant_words(document.words)
        return self._get_best_sentences(document.sentences,
            sentences_count, self.rate_sentence, words)

    def _get_significant_words(self, words):
        words = map(self.normalize_word, words)
        words = tuple(self.stem_word(w) for w in words if w not in self._stop_words)

        model = TfDocumentModel(words)

        # take only best `significant_percentage` % words
        best_words_count = int(len(words) * self.significant_percentage)
        words = model.most_frequent_terms(best_words_count)

        # take only words contained multiple times in document
        return tuple(t for t in words if model.term_frequency(t) > 1)

    def rate_sentence(self, sentence, significant_stems):
        ratings = self._get_chunk_ratings(sentence, significant_stems)
        return max(ratings) if ratings else 0

    def _get_chunk_ratings(self, sentence, significant_stems):
        chunks = []
        NONSIGNIFICANT_CHUNK = [0]*self.max_gap_size

        in_chunk = False
        for order, word in enumerate(sentence.words):
            stem = self.stem_word(word)
            # new chunk
            if stem in significant_stems and not in_chunk:
                in_chunk = True
                chunks.append([1])
            # append word to chunk
            elif in_chunk:
                is_significant_word = int(stem in significant_stems)
                chunks[-1].append(is_significant_word)

            # end of chunk
            if chunks and chunks[-1][-self.max_gap_size:] == NONSIGNIFICANT_CHUNK:
                in_chunk = False

        return tuple(map(self._get_chunk_rating, chunks))

    def _get_chunk_rating(self, chunk):
        chunk = self.__remove_trailing_zeros(chunk)
        words_count = len(chunk)
        assert words_count > 0

        significant_words = sum(chunk)
        if significant_words == 1:
            return 0
        else:
            return significant_words**2 / words_count

    def __remove_trailing_zeros(self, collection):
        """Removes trailing zeroes from indexable collection of numbers"""
        index = len(collection) - 1
        while index >= 0 and collection[index] == 0:
            index -= 1

        return collection[:index + 1]

########NEW FILE########
__FILENAME__ = random
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import random

from ._summarizer import AbstractSummarizer


class RandomSummarizer(AbstractSummarizer):
    """Summarizer that picks sentences randomly."""

    def __call__(self, document, sentences_count):
        sentences = document.sentences
        ratings = self._get_random_ratings(sentences)

        return self._get_best_sentences(sentences, sentences_count, ratings)

    def _get_random_ratings(self, sentences):
        ratings = list(range(len(sentences)))
        random.shuffle(ratings)

        return dict((s, r) for s, r in zip(sentences, ratings))

########NEW FILE########
__FILENAME__ = text_rank
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import math

from itertools import combinations
from collections import defaultdict
from ._summarizer import AbstractSummarizer


class TextRankSummarizer(AbstractSummarizer):
    """Source: https://github.com/adamfabish/Reduction"""

    _stop_words = frozenset()

    @property
    def stop_words(self):
        return self._stop_words

    @stop_words.setter
    def stop_words(self, words):
        self._stop_words = frozenset(map(self.normalize_word, words))

    def __call__(self, document, sentences_count):
        ratings = self.rate_sentences(document)
        return self._get_best_sentences(document.sentences, sentences_count, ratings)

    def rate_sentences(self, document):
        sentences_words = [(s, self._to_words_set(s)) for s in document.sentences]
        ratings = defaultdict(float)

        for (sentence1, words1), (sentence2, words2) in combinations(sentences_words, 2):
            rank = self._rate_sentences_edge(words1, words2)
            ratings[sentence1] += rank
            ratings[sentence2] += rank

        return ratings

    def _to_words_set(self, sentence):
        words = map(self.normalize_word, sentence.words)
        return [self.stem_word(w) for w in words if w not in self._stop_words]

    def _rate_sentences_edge(self, words1, words2):
        rank = 0
        for w1 in words1:
            for w2 in words2:
                rank += int(w1 == w2)

        if rank == 0:
            return 0.0

        assert len(words1) > 0 and len(words2) > 0
        norm = math.log(len(words1)) + math.log(len(words2))
        return 0.0 if norm == 0.0 else rank / norm

########NEW FILE########
__FILENAME__ = _summarizer
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals


from collections import namedtuple
from operator import attrgetter
from ..utils import ItemsCount
from .._compat import to_unicode
from ..nlp.stemmers import null_stemmer


SentenceInfo = namedtuple("SentenceInfo", ("sentence", "order", "rating",))


class AbstractSummarizer(object):
    def __init__(self, stemmer=null_stemmer):
        if not callable(stemmer):
            raise ValueError("Stemmer has to be a callable object")

        self._stemmer = stemmer

    def __call__(self, document, sentences_count):
        raise NotImplementedError("This method should be overriden in subclass")

    def stem_word(self, word):
        return self._stemmer(self.normalize_word(word))

    def normalize_word(self, word):
        return to_unicode(word).lower()

    def _get_best_sentences(self, sentences, count, rating, *args, **kwargs):
        rate = rating
        if isinstance(rating, dict):
            assert not args and not kwargs
            rate = lambda s: rating[s]

        infos = (SentenceInfo(s, o, rate(s, *args, **kwargs))
            for o, s in enumerate(sentences))

        # sort sentences by rating in descending order
        infos = sorted(infos, key=attrgetter("rating"), reverse=True)
        # get `count` first best rated sentences
        if not isinstance(count, ItemsCount):
            count = ItemsCount(count)
        infos = count(infos)
        # sort sentences by their order in document
        infos = sorted(infos, key=attrgetter("order"))

        return tuple(i.sentence for i in infos)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import sys

from functools import wraps
from os.path import dirname, abspath, join, exists
from ._compat import to_string, to_unicode, string_types


def cached_property(getter):
    """
    Decorator that converts a method into memoized property.
    The decorator works as expected only for classes with
    attribute '__dict__' and immutable properties.
    """
    @wraps(getter)
    def decorator(self):
        key = "_cached_property_" + getter.__name__

        if not hasattr(self, key):
            setattr(self, key, getter(self))

        return getattr(self, key)

    return property(decorator)


def expand_resource_path(path):
    directory = dirname(sys.modules["sumy"].__file__)
    directory = abspath(directory)
    return join(directory, to_string("data"), to_string(path))


def get_stop_words(language):
    path = expand_resource_path("stopwords/%s.txt" % language)
    if not exists(path):
        raise LookupError("Stop-words are not available for language %s." % language)
    return read_stop_words(path)


def read_stop_words(filename):
    with open(filename, "rb") as open_file:
        return frozenset(to_unicode(w.rstrip()) for w in open_file.readlines())


class ItemsCount(object):
    def __init__(self, value):
        self._value = value

    def __call__(self, sequence):
        if isinstance(self._value, string_types):
            if self._value.endswith("%"):
                total_count = len(sequence)
                percentage = int(self._value[:-1])
                # at least one sentence should be choosen
                count = max(1, total_count*percentage // 100)
                return sequence[:count]
            else:
                return sequence[:int(self._value)]
        elif isinstance(self._value, (int, float)):
            return sequence[:int(self._value)]
        else:
            ValueError("Unsuported value of items count '%s'." % self._value)

    def __repr__(self):
        return to_string("<ItemsCount: %r>" % self._value)

########NEW FILE########
__FILENAME__ = _compat
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from sys import version_info


PY3 = version_info[0] == 3


if PY3:
    bytes = bytes
    unicode = str
else:
    bytes = str
    unicode = unicode
string_types = (bytes, unicode,)


try:
    import urllib2 as urllib
except ImportError:
    from urllib import request as urllib


try:
    from itertools import ifilterfalse as ffilter
except ImportError:
    from itertools import filterfalse as ffilter


try:
    from collections import Counter
except ImportError:
    # Python < 2.7
    from itertools import groupby

    def Counter(iterable):
        iterable = sorted(iterable)
        return dict((key, len(tuple(group))) for key, group in groupby(iterable))


def unicode_compatible(cls):
    """
    Decorator for unicode compatible classes. Method ``__unicode__``
    has to be implemented to work decorator as expected.
    """
    if PY3:
        cls.__str__ = cls.__unicode__
        cls.__bytes__ = lambda self: self.__str__().encode("utf8")
    else:
        cls.__str__ = lambda self: self.__unicode__().encode("utf8")

    return cls


def to_string(object):
    return to_unicode(object) if PY3 else to_bytes(object)


def to_bytes(object):
    if isinstance(object, bytes):
        return object
    elif isinstance(object, unicode):
        return object.encode("utf8")
    else:
        # try encode instance to bytes
        return instance_to_bytes(object)


def to_unicode(object):
    if isinstance(object, unicode):
        return object
    elif isinstance(object, bytes):
        return object.decode("utf8")
    else:
        # try decode instance to unicode
        return instance_to_unicode(object)


def instance_to_bytes(instance):
    if PY3:
        if hasattr(instance, "__bytes__"):
            return bytes(instance)
        elif hasattr(instance, "__str__"):
            return unicode(instance).encode("utf8")
    else:
        if hasattr(instance, "__str__"):
            return bytes(instance)
        elif hasattr(instance, "__unicode__"):
            return unicode(instance).encode("utf8")

    return to_bytes(repr(instance))


def instance_to_unicode(instance):
    if PY3:
        if hasattr(instance, "__str__"):
            return unicode(instance)
        elif hasattr(instance, "__bytes__"):
            return bytes(instance).decode("utf8")
    else:
        if hasattr(instance, "__unicode__"):
            return unicode(instance)
        elif hasattr(instance, "__str__"):
            return bytes(instance).decode("utf8")

    return to_unicode(repr(instance))

########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf8 -*-

"""
Sumy - automatic text summarizer.

Usage:
    sumy (luhn | edmundson | lsa | text-rank | lex-rank) [--length=<length>] [--language=<lang>] [--stopwords=<file_path>] [--format=<format>]
    sumy (luhn | edmundson | lsa | text-rank | lex-rank) [--length=<length>] [--language=<lang>] [--stopwords=<file_path>] [--format=<format>] --url=<url>
    sumy (luhn | edmundson | lsa | text-rank | lex-rank) [--length=<length>] [--language=<lang>] [--stopwords=<file_path>] [--format=<format>] --file=<file_path>
    sumy --version
    sumy --help

Options:
    --length=<length>        Length of summarized text. It may be count of sentences
                             or percentage of input text. [default: 20%]
    --language=<lang>        Natural language of summarized text. [default: english]
    --stopwords=<file_path>  Path to a file containing a list of stopwords. One word per line in UTF-8 encoding.
                             If it's not provided default list of stop-words is used according to chosen language.
    --format=<format>        Format of input document. Possible values: html, plaintext
    --url=<url>              URL address of the web page to summarize.
    --file=<file_path>       Path to the text file to summarize.
    --version                Displays current application version.
    --help                   Displays this text.

"""

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import sys

from docopt import docopt
from . import __version__
from .utils import ItemsCount, get_stop_words, read_stop_words
from ._compat import urllib, to_string, to_unicode, to_bytes, PY3
from .nlp.tokenizers import Tokenizer
from .parsers.html import HtmlParser
from .parsers.plaintext import PlaintextParser
from .summarizers.luhn import LuhnSummarizer
from .summarizers.edmundson import EdmundsonSummarizer
from .summarizers.lsa import LsaSummarizer
from .summarizers.text_rank import TextRankSummarizer
from .summarizers.lex_rank import LexRankSummarizer
from .nlp.stemmers import Stemmer

HEADERS = {
    "User-Agent": "Sumy (Automatic text summarizer) Version/%s" % __version__,
}
PARSERS = {
    "html": HtmlParser,
    "plaintext": PlaintextParser,
}

AVAILABLE_METHODS = {
    "luhn": LuhnSummarizer,
    "edmundson": EdmundsonSummarizer,
    "lsa": LsaSummarizer,
    "text-rank": TextRankSummarizer,
    "lex-rank": LexRankSummarizer,
}


def main(args=None):
    args = docopt(to_string(__doc__), args, version=__version__)
    summarizer, parser, items_count = handle_arguments(args)

    for sentence in summarizer(parser.document, items_count):
        if PY3:
            print(to_unicode(sentence))
        else:
            print(to_bytes(sentence))

    return 0


def handle_arguments(args, default_input_stream=sys.stdin):
    language = args["--language"]
    document_format = args['--format']

    if args["--url"] is not None:
        parser = PARSERS[document_format or "html"]
        request = urllib.Request(args["--url"], headers=HEADERS)
        input_stream = urllib.urlopen(request)
    elif args["--file"] is not None:
        parser = PARSERS[document_format or "plaintext"]
        input_stream = open(args["--file"], "rb")
    else:
        parser = PARSERS[document_format or "plaintext"]
        input_stream = default_input_stream

    items_count = ItemsCount(args["--length"])

    if args['--stopwords']:
        stop_words = read_stop_words(args['--stopwords'])
    else:
        stop_words = get_stop_words(language)

    parser = parser(input_stream.read(), Tokenizer(language))
    if input_stream is not sys.stdin:
        input_stream.close()

    stemmer = Stemmer(language)

    summarizer_class = next(cls for name, cls in AVAILABLE_METHODS.items() if args[name])
    summarizer = build_summarizer(summarizer_class, stop_words, stemmer, parser)

    return summarizer, parser, items_count


def build_summarizer(summarizer_class, stop_words, stemmer, parser):
    summarizer = summarizer_class(stemmer)
    if summarizer_class is EdmundsonSummarizer:
        summarizer.null_words = stop_words
        summarizer.bonus_words = parser.significant_words
        summarizer.stigma_words = parser.stigma_words
    else:
        summarizer.stop_words = stop_words
    return summarizer


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        exit(1)
    except Exception as e:
        print(e)
        exit(1)

########NEW FILE########
__FILENAME__ = test_evaluation
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.nlp.tokenizers import Tokenizer
from sumy.models import TfDocumentModel
from sumy.evaluation import precision, recall, f_score
from sumy.evaluation import cosine_similarity, unit_overlap


class TestCoselectionEvaluation(unittest.TestCase):
    def test_precision_empty_evaluated(self):
        self.assertRaises(ValueError, precision, (), ("s1", "s2", "s3", "s4", "s5"))

    def test_precision_empty_reference(self):
        self.assertRaises(ValueError, precision, ("s1", "s2", "s3", "s4", "s5"), ())

    def test_precision_no_match(self):
        result = precision(("s1", "s2", "s3", "s4", "s5"), ("s6", "s7", "s8"))

        self.assertEqual(result, 0.0)

    def test_precision_reference_smaller(self):
        result = precision(("s1", "s2", "s3", "s4", "s5"), ("s1",))

        self.assertAlmostEqual(result, 0.2)

    def test_precision_evaluated_smaller(self):
        result = precision(("s1",), ("s1", "s2", "s3", "s4", "s5"))

        self.assertAlmostEqual(result, 1.0)

    def test_precision_equals(self):
        sentences = ("s1", "s2", "s3", "s4", "s5")
        result = precision(sentences, sentences)

        self.assertAlmostEqual(result, 1.0)

    def test_recall_empty_evaluated(self):
        self.assertRaises(ValueError,  recall, (), ("s1", "s2", "s3", "s4", "s5"))

    def test_recall_empty_reference(self):
        self.assertRaises(ValueError,  recall, ("s1", "s2", "s3", "s4", "s5"), ())

    def test_recall_no_match(self):
        result = recall(("s1", "s2", "s3", "s4", "s5"), ("s6", "s7", "s8"))

        self.assertEqual(result, 0.0)

    def test_recall_reference_smaller(self):
        result = recall(("s1", "s2", "s3", "s4", "s5"), ("s1",))

        self.assertAlmostEqual(result, 1.0)

    def test_recall_evaluated_smaller(self):
        result = recall(("s1",), ("s1", "s2", "s3", "s4", "s5"))

        self.assertAlmostEqual(result, 0.20)

    def test_recall_equals(self):
        sentences = ("s1", "s2", "s3", "s4", "s5")
        result = recall(sentences, sentences)

        self.assertAlmostEqual(result, 1.0)

    def test_basic_f_score_empty_evaluated(self):
        self.assertRaises(ValueError, f_score, (), ("s1", "s2", "s3", "s4", "s5"))

    def test_basic_f_score_empty_reference(self):
        self.assertRaises(ValueError, f_score, ("s1", "s2", "s3", "s4", "s5"), ())

    def test_basic_f_score_no_match(self):
        result = f_score(("s1", "s2", "s3", "s4", "s5"), ("s6", "s7", "s8"))

        self.assertEqual(result, 0.0)

    def test_basic_f_score_reference_smaller(self):
        result = f_score(("s1", "s2", "s3", "s4", "s5"), ("s1",))

        self.assertAlmostEqual(result, 1/3)

    def test_basic_f_score_evaluated_smaller(self):
        result = f_score(("s1",), ("s1", "s2", "s3", "s4", "s5"))

        self.assertAlmostEqual(result, 1/3)

    def test_basic_f_score_equals(self):
        sentences = ("s1", "s2", "s3", "s4", "s5")
        result = f_score(sentences, sentences)

        self.assertAlmostEqual(result, 1.0)

    def test_f_score_1(self):
        sentences = (("s1",), ("s1", "s2", "s3", "s4", "s5"))
        result = f_score(*sentences, weight=2.0)

        p = 1/1
        r = 1/5
        # ( (W^2 + 1) * P * R ) / ( W^2 * P + R )
        expected = (5 * p * r) / (4 * p + r)

        self.assertAlmostEqual(result, expected)

    def test_f_score_2(self):
        sentences = (("s1", "s3", "s6"), ("s1", "s2", "s3", "s4", "s5"))
        result = f_score(*sentences, weight=0.5)

        p = 2/3
        r = 2/5
        # ( (W^2 + 1) * P * R ) / ( W^2 * P + R )
        expected = (1.25 * p * r) / (0.25 * p + r)

        self.assertAlmostEqual(result, expected)


class TestContentBasedEvaluation(unittest.TestCase):
    def test_wrong_arguments(self):
        text = "Toto je moja veta, to sa nedá poprieť."
        model = TfDocumentModel(text, Tokenizer("czech"))

        self.assertRaises(ValueError, cosine_similarity, text, text)
        self.assertRaises(ValueError, cosine_similarity, text, model)
        self.assertRaises(ValueError, cosine_similarity, model, text)

    def test_empty_model(self):
        text = "Toto je moja veta, to sa nedá poprieť."
        model = TfDocumentModel(text, Tokenizer("czech"))
        empty_model = TfDocumentModel([])

        self.assertRaises(ValueError, cosine_similarity, empty_model, empty_model)
        self.assertRaises(ValueError, cosine_similarity, empty_model, model)
        self.assertRaises(ValueError, cosine_similarity, model, empty_model)

    def test_cosine_exact_match(self):
        text = "Toto je moja veta, to sa nedá poprieť."
        model = TfDocumentModel(text, Tokenizer("czech"))

        self.assertAlmostEqual(cosine_similarity(model, model), 1.0)

    def test_cosine_no_match(self):
        tokenizer = Tokenizer("czech")
        model1 = TfDocumentModel("Toto je moja veta. To sa nedá poprieť!",
            tokenizer)
        model2 = TfDocumentModel("Hento bolo jeho slovo, ale možno klame.",
            tokenizer)

        self.assertAlmostEqual(cosine_similarity(model1, model2), 0.0)

    def test_cosine_half_match(self):
        tokenizer = Tokenizer("czech")
        model1 = TfDocumentModel("Veta aká sa tu len veľmi ťažko hľadá",
            tokenizer)
        model2 = TfDocumentModel("Teta ktorá sa tu iba veľmi zle hľadá",
            tokenizer)

        self.assertAlmostEqual(cosine_similarity(model1, model2), 0.5)

    def test_unit_overlap_empty(self):
        tokenizer = Tokenizer("english")
        model = TfDocumentModel("", tokenizer)

        self.assertRaises(ValueError, unit_overlap, model, model)

    def test_unit_overlap_wrong_arguments(self):
        tokenizer = Tokenizer("english")
        model = TfDocumentModel("", tokenizer)

        self.assertRaises(ValueError, unit_overlap, "model", "model")
        self.assertRaises(ValueError, unit_overlap, "model", model)
        self.assertRaises(ValueError, unit_overlap, model, "model")

    def test_unit_overlap_exact_match(self):
        tokenizer = Tokenizer("czech")
        model = TfDocumentModel("Veta aká sa len veľmi ťažko hľadá.", tokenizer)

        self.assertAlmostEqual(unit_overlap(model, model), 1.0)

    def test_unit_overlap_no_match(self):
        tokenizer = Tokenizer("czech")
        model1 = TfDocumentModel("Toto je moja veta. To sa nedá poprieť!",
            tokenizer)
        model2 = TfDocumentModel("Hento bolo jeho slovo, ale možno klame.",
            tokenizer)

        self.assertAlmostEqual(unit_overlap(model1, model2), 0.0)

    def test_unit_overlap_half_match(self):
        tokenizer = Tokenizer("czech")
        model1 = TfDocumentModel("Veta aká sa tu len veľmi ťažko hľadá",
            tokenizer)
        model2 = TfDocumentModel("Teta ktorá sa tu iba veľmi zle hľadá",
            tokenizer)

        self.assertAlmostEqual(unit_overlap(model1, model2), 1/3)

########NEW FILE########
__FILENAME__ = test_main
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from docopt import docopt, DocoptExit
from sumy.__main__ import __doc__ as main_doc
from sumy.__main__ import handle_arguments, to_string, __version__
from .utils import StringIO


class TestMain(unittest.TestCase):
    DEFAULT_ARGS = {
        '--file': None,
        '--format': None,
        '--help': False,
        '--language': 'english',
        '--length': '20%',
        '--stopwords': None,
        '--url': None,
        '--version': False,
        'edmundson': False,
        'lex-rank': False,
        'lsa': True,
        'luhn': False,
        'text-rank': False,
    }

    def test_ok_args(self):
        docopt(to_string(main_doc), 'luhn --url=URL --format=FORMAT'.split(), version=__version__)

    def test_args_none(self):
        self.assertRaises(DocoptExit, docopt, to_string(main_doc), None, version=__version__)

    def test_args_just_command(self):
        args = docopt(to_string(main_doc), ['lsa'], version=__version__)
        self.assertEqual(self.DEFAULT_ARGS, args)

    def test_args_two_commands(self):
        self.assertRaises(DocoptExit, docopt, to_string(main_doc), 'lsa luhn'.split(), version=__version__)

    def test_args_url_and_file(self):
        self.assertRaises(DocoptExit, docopt, to_string(main_doc), 'lsa --url=URL --file=FILE'.split(), version=__version__)

    def test_handle_default_arguments(self):
        handle_arguments(self.DEFAULT_ARGS, default_input_stream=StringIO("Whatever."))

    def test_handle_wrong_format(self):
        wrong_args = self.DEFAULT_ARGS.copy()
        wrong_args.update({'--url': 'URL', '--format': 'text'})
        self.assertRaises(KeyError, handle_arguments, wrong_args, default_input_stream=StringIO("Whatever."))

########NEW FILE########
__FILENAME__ = test_dom
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy._compat import to_unicode
from sumy.nlp.tokenizers import Tokenizer
from sumy.models.dom import Paragraph, Sentence
from ..utils import build_document, build_document_from_string


class TestDocument(unittest.TestCase):
    def test_unique_words(self):
        document = build_document(
            ("Nějaký muž šel kolem naší zahrady", "Nějaký muž šel kolem vaší zahrady",),
            ("Už už abych taky šel",),
        )

        returned = tuple(sorted(frozenset(document.words)))
        expected = (
            "Nějaký",
            "Už",
            "abych",
            "kolem",
            "muž",
            "naší",
            "taky",
            "už",
            "vaší",
            "zahrady",
            "šel"
        )
        self.assertEqual(expected, returned)

    def test_headings(self):
        document = build_document_from_string("""
            Nějaký muž šel kolem naší zahrady
            Nějaký jiný muž šel kolem vaší zahrady

            # Nová myšlenka
            Už už abych taky šel
        """)

        self.assertEqual(len(document.headings), 1)
        self.assertEqual(to_unicode(document.headings[0]), "Nová myšlenka")

    def test_sentences(self):
        document = build_document_from_string("""
            Nějaký muž šel kolem naší zahrady
            Nějaký jiný muž šel kolem vaší zahrady

            # Nová myšlenka
            Už už abych taky šel
        """)

        self.assertEqual(len(document.sentences), 3)
        self.assertEqual(to_unicode(document.sentences[0]),
            "Nějaký muž šel kolem naší zahrady")
        self.assertEqual(to_unicode(document.sentences[1]),
            "Nějaký jiný muž šel kolem vaší zahrady")
        self.assertEqual(to_unicode(document.sentences[2]),
            "Už už abych taky šel")

    def test_only_instances_of_sentence_allowed(self):
        document = build_document_from_string("""
            Nějaký muž šel kolem naší zahrady
            Nějaký jiný muž šel kolem vaší zahrady

            # Nová myšlenka
            Už už abych taky šel
        """)

        self.assertRaises(TypeError, Paragraph,
            list(document.sentences) + ["Last sentence"])

    def test_sentences_equal(self):
        sentence1 = Sentence("", Tokenizer("czech"))
        sentence2 = Sentence("", Tokenizer("czech"))
        self.assertEqual(sentence1, sentence2)

        sentence1 = Sentence("word another.", Tokenizer("czech"))
        sentence2 = Sentence("word another.", Tokenizer("czech"))
        self.assertEqual(sentence1, sentence2)

        sentence1 = Sentence("word another", Tokenizer("czech"))
        sentence2 = Sentence("another word", Tokenizer("czech"))
        self.assertNotEqual(sentence1, sentence2)

########NEW FILE########
__FILENAME__ = test_tf
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.nlp.tokenizers import Tokenizer
from sumy.models import TfDocumentModel


class TestTfModel(unittest.TestCase):
    def test_no_tokenizer_with_string(self):
        self.assertRaises(ValueError, TfDocumentModel, "text without tokenizer")

    def test_pretokenized_words(self):
        model = TfDocumentModel(("wA", "WB", "wB", "WA"))

        terms = tuple(sorted(model.terms))
        self.assertEqual(terms, ("wa", "wb"))

    def test_pretokenized_words_frequencies(self):
        model = TfDocumentModel(("wC", "wC", "WC", "wA", "WB", "wB"))

        self.assertEqual(model.term_frequency("wa"), 1)
        self.assertEqual(model.term_frequency("wb"), 2)
        self.assertEqual(model.term_frequency("wc"), 3)
        self.assertEqual(model.term_frequency("wd"), 0)

        self.assertEqual(model.most_frequent_terms(), ("wc", "wb", "wa"))

    def test_magnitude(self):
        tokenizer = Tokenizer("english")
        text = "wA wB wC wD"
        model = TfDocumentModel(text, tokenizer)

        self.assertAlmostEqual(model.magnitude, 2.0)

    def test_terms(self):
        tokenizer = Tokenizer("english")
        text = "wA wB wC wD wB wD wE"
        model = TfDocumentModel(text, tokenizer)

        terms = tuple(sorted(model.terms))
        self.assertEqual(terms, ("wa", "wb", "wc", "wd", "we"))

    def test_term_frequency(self):
        tokenizer = Tokenizer("english")
        text = "wA wB wC wA wA wC wD wCwB"
        model = TfDocumentModel(text, tokenizer)

        self.assertEqual(model.term_frequency("wa"), 3)
        self.assertEqual(model.term_frequency("wb"), 1)
        self.assertEqual(model.term_frequency("wc"), 2)
        self.assertEqual(model.term_frequency("wd"), 1)
        self.assertEqual(model.term_frequency("wcwb"), 1)
        self.assertEqual(model.term_frequency("we"), 0)
        self.assertEqual(model.term_frequency("missing"), 0)

    def test_most_frequent_terms(self):
        tokenizer = Tokenizer("english")
        text = "wE wD wC wB wA wE WD wC wB wE wD WE wC wD wE"
        model = TfDocumentModel(text, tokenizer)

        self.assertEqual(model.most_frequent_terms(1), ("we",))
        self.assertEqual(model.most_frequent_terms(2), ("we", "wd"))
        self.assertEqual(model.most_frequent_terms(3), ("we", "wd", "wc"))
        self.assertEqual(model.most_frequent_terms(4), ("we", "wd", "wc", "wb"))
        self.assertEqual(model.most_frequent_terms(5), ("we", "wd", "wc", "wb", "wa"))
        self.assertEqual(model.most_frequent_terms(), ("we", "wd", "wc", "wb", "wa"))

    def test_most_frequent_terms_empty(self):
        tokenizer = Tokenizer("english")
        model = TfDocumentModel("", tokenizer)

        self.assertEqual(model.most_frequent_terms(), ())
        self.assertEqual(model.most_frequent_terms(10), ())

    def test_most_frequent_terms_negative_count(self):
        tokenizer = Tokenizer("english")
        model = TfDocumentModel("text", tokenizer)

        self.assertRaises(ValueError, model.most_frequent_terms, -1)

    def test_normalized_words_frequencies(self):
        words = "a b c d e c b d c e e d e d e".split()
        model = TfDocumentModel(tuple(words))

        self.assertAlmostEqual(model.normalized_term_frequency("a"), 1/5)
        self.assertAlmostEqual(model.normalized_term_frequency("b"), 2/5)
        self.assertAlmostEqual(model.normalized_term_frequency("c"), 3/5)
        self.assertAlmostEqual(model.normalized_term_frequency("d"), 4/5)
        self.assertAlmostEqual(model.normalized_term_frequency("e"), 5/5)
        self.assertAlmostEqual(model.normalized_term_frequency("z"), 0.0)

        self.assertEqual(model.most_frequent_terms(), ("e", "d", "c", "b", "a"))

    def test_normalized_words_frequencies_with_smoothing_term(self):
        words = "a b c d e c b d c e e d e d e".split()
        model = TfDocumentModel(tuple(words))

        self.assertAlmostEqual(model.normalized_term_frequency("a", 0.5), 0.5 + 1/10)
        self.assertAlmostEqual(model.normalized_term_frequency("b", 0.5), 0.5 + 2/10)
        self.assertAlmostEqual(model.normalized_term_frequency("c", 0.5), 0.5 + 3/10)
        self.assertAlmostEqual(model.normalized_term_frequency("d", 0.5), 0.5 + 4/10)
        self.assertAlmostEqual(model.normalized_term_frequency("e", 0.5), 0.5 + 5/10)
        self.assertAlmostEqual(model.normalized_term_frequency("z", 0.5), 0.5)

        self.assertEqual(model.most_frequent_terms(), ("e", "d", "c", "b", "a"))

########NEW FILE########
__FILENAME__ = test_parsers
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy._compat import to_unicode
from sumy.parsers.plaintext import PlaintextParser
from sumy.parsers.html import HtmlParser
from sumy.nlp.tokenizers import Tokenizer
from .utils import expand_resource_path


class TestParser(unittest.TestCase):
    def test_parse_plaintext(self):
        parser = PlaintextParser.from_string("""
            Ako sa máš? Ja dobre! A ty? No
            mohlo to byť aj lepšie!!! Ale pohodička.


            TOTO JE AKOŽE NADPIS
            A toto je text pod ním, ktorý je textový.
            A tak ďalej...
        """, Tokenizer("czech"))

        document = parser.document

        self.assertEqual(len(document.paragraphs), 2)

        self.assertEqual(len(document.paragraphs[0].headings), 0)
        self.assertEqual(len(document.paragraphs[0].sentences), 5)

        self.assertEqual(len(document.paragraphs[1].headings), 1)
        self.assertEqual(len(document.paragraphs[1].sentences), 2)

    def test_parse_plaintext_long(self):
        parser = PlaintextParser.from_string("""
            Ako sa máš? Ja dobre! A ty? No
            mohlo to byť aj lepšie!!! Ale pohodička.

            TOTO JE AKOŽE NADPIS
            A toto je text pod ním, ktorý je textový.
            A tak ďalej...

            VEĽKOLEPÉ PREKVAPENIE
            Tretí odstavec v tomto texte je úplne o ničom. Ale má
            vety a to je hlavné. Takže sa majte na pozore ;-)

            A tak ďalej...


            A tak este dalej!
        """, Tokenizer("czech"))

        document = parser.document

        self.assertEqual(len(document.paragraphs), 5)

        self.assertEqual(len(document.paragraphs[0].headings), 0)
        self.assertEqual(len(document.paragraphs[0].sentences), 5)

        self.assertEqual(len(document.paragraphs[1].headings), 1)
        self.assertEqual(len(document.paragraphs[1].sentences), 2)

        self.assertEqual(len(document.paragraphs[2].headings), 1)
        self.assertEqual(len(document.paragraphs[2].sentences), 3)

        self.assertEqual(len(document.paragraphs[3].headings), 0)
        self.assertEqual(len(document.paragraphs[3].sentences), 1)

        self.assertEqual(len(document.paragraphs[4].headings), 0)
        self.assertEqual(len(document.paragraphs[4].sentences), 1)


class TestHtmlParser(unittest.TestCase):
    def test_annotated_text(self):
        path = expand_resource_path("snippets/paragraphs.html")
        url = "http://www.snippet.org/paragraphs.html"
        parser = HtmlParser.from_file(path, url, Tokenizer("czech"))

        document = parser.document

        self.assertEqual(len(document.paragraphs), 2)

        self.assertEqual(len(document.paragraphs[0].headings), 1)
        self.assertEqual(len(document.paragraphs[0].sentences), 1)

        self.assertEqual(to_unicode(document.paragraphs[0].headings[0]),
            "Toto je nadpis prvej úrovne")
        self.assertEqual(to_unicode(document.paragraphs[0].sentences[0]),
            "Toto je prvý odstavec a to je fajn.")

        self.assertEqual(len(document.paragraphs[1].headings), 0)
        self.assertEqual(len(document.paragraphs[1].sentences), 2)

        self.assertEqual(to_unicode(document.paragraphs[1].sentences[0]),
            "Tento text je tu aby vyplnil prázdne miesto v srdci súboru.")
        self.assertEqual(to_unicode(document.paragraphs[1].sentences[1]),
            "Aj súbory majú predsa city.")

########NEW FILE########
__FILENAME__ = test_stemmers
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.nlp.stemmers import null_stemmer, Stemmer


class TestStemmers(unittest.TestCase):
    """Simple tests to make sure all stemmers share the same API."""
    def test_missing_stemmer_language(self):
        self.assertRaises(LookupError, Stemmer, "klingon")

    def test_null_stemmer(self):
        self.assertEqual("ľščťžýáíé", null_stemmer("ľŠčŤžÝáÍé"))

    def test_english_stemmer(self):
        english_stemmer = Stemmer('english')
        self.assertEqual("beauti", english_stemmer("beautiful"))

    def test_german_stemmer(self):
        german_stemmer = Stemmer('german')
        self.assertEqual("sterb", german_stemmer("sterben"))

    def test_czech_stemmer(self):
        czech_stemmer = Stemmer('czech')
        self.assertEqual("pěkn", czech_stemmer("pěkný"))

    def test_french_stemmer(self):
        french_stemmer = Stemmer('czech')
        self.assertEqual("jol", french_stemmer("jolies"))

    def test_slovak_stemmer(self):
        expected = Stemmer("czech")
        actual = Stemmer("slovak")
        self.assertEqual(type(actual), type(expected))
        self.assertEqual(expected.__dict__, actual.__dict__)

########NEW FILE########
__FILENAME__ = test_edmundson
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.summarizers.edmundson import EdmundsonSummarizer
from sumy._compat import to_unicode
from ..utils import build_document, build_document_from_string


class TestEdmundson(unittest.TestCase):
    def test_bonus_words_property(self):
        summarizer = EdmundsonSummarizer()

        self.assertEqual(summarizer.bonus_words, frozenset())

        words = ("word", "another", "and", "some", "next",)
        summarizer.bonus_words = words
        self.assertTrue(isinstance(summarizer.bonus_words, frozenset))
        self.assertEqual(summarizer.bonus_words, frozenset(words))

    def test_stigma_words_property(self):
        summarizer = EdmundsonSummarizer()

        self.assertEqual(summarizer.stigma_words, frozenset())

        words = ("word", "another", "and", "some", "next",)
        summarizer.stigma_words = words
        self.assertTrue(isinstance(summarizer.stigma_words, frozenset))
        self.assertEqual(summarizer.stigma_words, frozenset(words))

    def test_null_words_property(self):
        summarizer = EdmundsonSummarizer()

        self.assertEqual(summarizer.null_words, frozenset())

        words = ("word", "another", "and", "some", "next",)
        summarizer.null_words = words
        self.assertTrue(isinstance(summarizer.null_words, frozenset))
        self.assertEqual(summarizer.null_words, frozenset(words))

    def test_empty_document(self):
        summarizer = EdmundsonSummarizer(cue_weight=0, key_weight=0,
            title_weight=0, location_weight=0)

        sentences = summarizer(build_document(), 10)
        self.assertEqual(len(sentences), 0)

    def test_mixed_cue_key(self):
        document = build_document_from_string("""
            # This is cool heading
            Because I am sentence I like words
            And because I am string I like characters

            # blank and heading
            This is next paragraph because of blank line above
            Here is the winner because contains words like cool and heading
        """)

        summarizer = EdmundsonSummarizer(cue_weight=1, key_weight=1,
            title_weight=0, location_weight=0)
        summarizer.bonus_words = ("cool", "heading", "sentence", "words", "like", "because")
        summarizer.stigma_words = ("this", "is", "I", "am", "and",)

        sentences = summarizer(document, 2)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]),
            "Because I am sentence I like words")
        self.assertEqual(to_unicode(sentences[1]),
            "Here is the winner because contains words like cool and heading")

    def test_cue_with_no_words(self):
        summarizer = EdmundsonSummarizer()

        self.assertRaises(ValueError, summarizer.cue_method, build_document(), 10)

    def test_cue_with_no_stigma_words(self):
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("great", "very", "beautiful",)

        self.assertRaises(ValueError, summarizer.cue_method, build_document(), 10)

    def test_cue_with_no_bonus_words(self):
        summarizer = EdmundsonSummarizer()
        summarizer.stigma_words = ("useless", "bad", "spinach",)

        self.assertRaises(ValueError, summarizer.cue_method, build_document(), 10)

    def test_cue_empty(self):
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc",)
        summarizer.stigma_words = ("sa", "sb", "sc",)

        sentences = summarizer.cue_method(build_document(), 10)
        self.assertEqual(len(sentences), 0)

    def test_cue_letters_case(self):
        document = build_document(
            ("X X X", "x x x x",),
            ("w w w", "W W W W",)
        )

        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("X", "w",)
        summarizer.stigma_words = ("stigma",)

        sentences = summarizer.cue_method(document, 2)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]), "x x x x")
        self.assertEqual(to_unicode(sentences[1]), "W W W W")

    def test_cue_1(self):
        document = build_document(
            ("ba bb bc bb unknown ľščťžýáíé sb sc sb",)
        )

        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc",)
        summarizer.stigma_words = ("sa", "sb", "sc",)

        sentences = summarizer.cue_method(document, 10)
        self.assertEqual(len(sentences), 1)

    def test_cue_2(self):
        document = build_document(
            ("ba bb bc bb unknown ľščťžýáíé sb sc sb",),
            ("Pepek likes spinach",)
        )

        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc",)
        summarizer.stigma_words = ("sa", "sb", "sc",)

        sentences = summarizer.cue_method(document, 10)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]),
            "ba bb bc bb unknown ľščťžýáíé sb sc sb")
        self.assertEqual(to_unicode(sentences[1]), "Pepek likes spinach")

        sentences = summarizer.cue_method(document, 1)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(to_unicode(sentences[0]),
            "ba bb bc bb unknown ľščťžýáíé sb sc sb")

    def test_cue_3(self):
        document = build_document(
            (
                "ba "*10,
                "bb "*10,
                " sa"*8 + " bb"*10,
                "bb bc ba",
            ),
            (),
            (
                "babbbc "*10,
                "na nb nc nd sa" + " bc"*10,
                " ba n"*10,
            )
        )

        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc",)
        summarizer.stigma_words = ("sa", "sb", "sc",)

        sentences = summarizer.cue_method(document, 5)
        self.assertEqual(len(sentences), 5)
        self.assertEqual(to_unicode(sentences[0]), ("ba "*10).strip())
        self.assertEqual(to_unicode(sentences[1]), ("bb "*10).strip())
        self.assertEqual(to_unicode(sentences[2]), "bb bc ba")
        self.assertEqual(to_unicode(sentences[3]),
            "na nb nc nd sa bc bc bc bc bc bc bc bc bc bc")
        self.assertEqual(to_unicode(sentences[4]), ("ba n "*10).strip())

    def test_key_empty(self):
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc",)

        sentences = summarizer.key_method(build_document(), 10)
        self.assertEqual(len(sentences), 0)

    def test_key_without_bonus_words(self):
        summarizer = EdmundsonSummarizer()

        self.assertRaises(ValueError, summarizer.key_method, build_document(), 10)

    def test_key_no_bonus_words_in_document(self):
        document = build_document(
            ("wa wb wc wd", "I like music",),
            ("This is test sentence with some extra words",)
        )
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc", "bonus",)

        sentences = summarizer.key_method(document, 10)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(to_unicode(sentences[0]), "wa wb wc wd")
        self.assertEqual(to_unicode(sentences[1]), "I like music")
        self.assertEqual(to_unicode(sentences[2]),
            "This is test sentence with some extra words")

    def test_key_1(self):
        document = build_document(
            ("wa wb wc wd", "I like music",),
            ("This is test sentence with some extra words and bonus",)
        )
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("ba", "bb", "bc", "bonus",)

        sentences = summarizer.key_method(document, 1)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(to_unicode(sentences[0]),
            "This is test sentence with some extra words and bonus")

    def test_key_2(self):
        document = build_document(
            ("Om nom nom nom nom", "Sure I summarize it, with bonus",),
            ("This is bonus test sentence with some extra words and bonus",)
        )
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("nom", "bonus",)

        sentences = summarizer.key_method(document, 2)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]), "Om nom nom nom nom")
        self.assertEqual(to_unicode(sentences[1]),
            "This is bonus test sentence with some extra words and bonus")

    def test_key_3(self):
        document = build_document(
            ("wa", "wa wa", "wa wa wa", "wa wa wa wa", "wa Wa Wa Wa wa",),
            ("x X x X",)
        )
        summarizer = EdmundsonSummarizer()
        summarizer.bonus_words = ("wa", "X",)

        sentences = summarizer.key_method(document, 3)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(to_unicode(sentences[0]), "wa wa wa")
        self.assertEqual(to_unicode(sentences[1]), "wa wa wa wa")
        self.assertEqual(to_unicode(sentences[2]), "wa Wa Wa Wa wa")

        sentences = summarizer.key_method(document, 3, weight=0)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(to_unicode(sentences[0]), "wa wa wa wa")
        self.assertEqual(to_unicode(sentences[1]), "wa Wa Wa Wa wa")
        self.assertEqual(to_unicode(sentences[2]), "x X x X")

    def test_title_method_with_empty_document(self):
        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("ba", "bb", "bc",)

        sentences = summarizer.title_method(build_document(), 10)
        self.assertEqual(len(sentences), 0)

    def test_title_method_without_null_words(self):
        summarizer = EdmundsonSummarizer()

        self.assertRaises(ValueError, summarizer.title_method, build_document(), 10)

    def test_title_method_without_title(self):
        document = build_document(
            ("This is sentence", "This is another one",),
            ("And some next sentence but no heading",)
        )

        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("this", "is", "some", "and",)

        sentences = summarizer.title_method(document, 10)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(to_unicode(sentences[0]), "This is sentence")
        self.assertEqual(to_unicode(sentences[1]), "This is another one")
        self.assertEqual(to_unicode(sentences[2]), "And some next sentence but no heading")

    def test_title_method_1(self):
        document = build_document_from_string("""
            # This is cool heading
            Because I am sentence I like words
            And because I am string I like characters

            # blank and heading
            This is next paragraph because of blank line above
            Here is the winner because contains words like cool and heading
        """)

        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("this", "is", "I", "am", "and",)

        sentences = summarizer.title_method(document, 1)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(to_unicode(sentences[0]),
            "Here is the winner because contains words like cool and heading")

    def test_title_method_2(self):
        document = build_document_from_string("""
            # This is cool heading
            Because I am sentence I like words
            And because I am string I like characters

            # blank and heading
            This is next paragraph because of blank line above
            Here is the winner because contains words like cool and heading
        """)

        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("this", "is", "I", "am", "and",)

        sentences = summarizer.title_method(document, 2)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]),
            "This is next paragraph because of blank line above")
        self.assertEqual(to_unicode(sentences[1]),
            "Here is the winner because contains words like cool and heading")

    def test_title_method_3(self):
        document = build_document_from_string("""
            # This is cool heading
            Because I am sentence I like words
            And because I am string I like characters

            # blank and heading
            This is next paragraph because of blank line above
            Here is the winner because contains words like cool and heading
        """)

        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("this", "is", "I", "am", "and",)

        sentences = summarizer.title_method(document, 3)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(to_unicode(sentences[0]),
            "Because I am sentence I like words")
        self.assertEqual(to_unicode(sentences[1]),
            "This is next paragraph because of blank line above")
        self.assertEqual(to_unicode(sentences[2]),
            "Here is the winner because contains words like cool and heading")

    def test_location_method_with_empty_document(self):
        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("na", "nb", "nc",)

        sentences = summarizer.location_method(build_document(), 10)
        self.assertEqual(len(sentences), 0)

    def test_location_method_without_null_words(self):
        summarizer = EdmundsonSummarizer()

        self.assertRaises(ValueError, summarizer.location_method, build_document(), 10)

    def test_location_method_1(self):
        document = build_document_from_string("""
            # na nb nc ha hb
            ha = 1 + 1 + 1 = 3
            ha hb = 2 + 1 + 1 = 4

            first = 1
            ha hb ha = 3
            last = 1

            # hc hd
            hb hc hd = 3 + 1 + 1 = 5
            ha hb = 2 + 1 + 1 = 4
        """)

        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("na", "nb", "nc", "nd", "ne",)

        sentences = summarizer.location_method(document, 4)
        self.assertEqual(len(sentences), 4)
        self.assertEqual(to_unicode(sentences[0]), "ha = 1 + 1 + 1 = 3")
        self.assertEqual(to_unicode(sentences[1]), "ha hb = 2 + 1 + 1 = 4")
        self.assertEqual(to_unicode(sentences[2]), "hb hc hd = 3 + 1 + 1 = 5")
        self.assertEqual(to_unicode(sentences[3]), "ha hb = 2 + 1 + 1 = 4")

    def test_location_method_2(self):
        document = build_document_from_string("""
            # na nb nc ha hb
            ha = 1 + 1 + 0 = 2
            middle = 0
            ha hb = 2 + 1 + 0 = 3

            first = 1
            ha hb ha = 3
            last = 1

            # hc hd
            hb hc hd = 3 + 1 + 0 = 4
            ha hb = 2 + 1 + 0 = 3
        """)

        summarizer = EdmundsonSummarizer()
        summarizer.null_words = ("na", "nb", "nc", "nd", "ne",)

        sentences = summarizer.location_method(document, 4, w_p1=0, w_p2=0)
        self.assertEqual(len(sentences), 4)
        self.assertEqual(to_unicode(sentences[0]), "ha hb = 2 + 1 + 0 = 3")
        self.assertEqual(to_unicode(sentences[1]), "ha hb ha = 3")
        self.assertEqual(to_unicode(sentences[2]), "hb hc hd = 3 + 1 + 0 = 4")
        self.assertEqual(to_unicode(sentences[3]), "ha hb = 2 + 1 + 0 = 3")

########NEW FILE########
__FILENAME__ = test_lex_rank
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import math
import unittest
import sumy.summarizers.lex_rank as lex_rank_module

from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.stemmers.czech import stem_word
from sumy.nlp.tokenizers import Tokenizer
from sumy.utils import get_stop_words
from ..utils import build_document, load_resource


class TestLexRank(unittest.TestCase):
    def test_numpy_not_installed(self):
        summarizer = LexRankSummarizer()

        numpy = lex_rank_module.numpy
        lex_rank_module.numpy = None

        self.assertRaises(ValueError, summarizer, build_document(), 10)

        lex_rank_module.numpy = numpy

    def test_tf_metrics(self):
        summarizer = LexRankSummarizer()

        sentences = [
            ("this", "sentence", "is", "simple", "sentence"),
            ("this", "is", "simple", "sentence", "yes", "is", "too", "too", "too"),
        ]
        metrics = summarizer._compute_tf(sentences)

        expected = [
            {"this": 1/2, "is": 1/2, "simple": 1/2, "sentence": 1.0},
            {"this": 1/3, "is": 2/3, "yes": 1/3, "simple": 1/3, "sentence": 1/3, "too": 1.0},
        ]
        self.assertEqual(expected, metrics)

    def test_idf_metrics(self):
        summarizer = LexRankSummarizer()

        sentences = [
            ("this", "sentence", "is", "simple", "sentence",),
            ("this", "is", "simple", "sentence", "yes", "is", "too", "too", "too",),
            ("not", "every", "sentence", "makes", "me", "happy",),
            ("yes",),
            (),
            ("every", "day", "is", "happy", "day",),
        ]
        metrics = summarizer._compute_idf(sentences)

        expected = {
            "this": 6/2,
            "is": 6/3,
            "yes": 6/2,
            "simple": 6/2,
            "sentence": 6/3,
            "too": 6/1,
            "not": 6/1,
            "every": 6/2,
            "makes": 6/1,
            "me": 6/1,
            "happy": 6/2,
            "day": 6/1,
        }
        self.assertEqual(expected, metrics)

    def test_modified_cosine_computation(self):
        summarizer = LexRankSummarizer()

        sentence1 = ["this", "sentence", "is", "simple", "sentence"]
        tf1 = {"this": 1/2, "sentence": 1.0, "is": 1/2, "simple": 1/2}
        sentence2 = ["this", "is", "simple", "sentence", "yes", "is", "too", "too"]
        tf2 = {"this": 1/2, "is": 1.0, "simple": 1/2, "sentence": 1/2, "yes": 1/2, "too": 1.0}
        idf = {
            "this": 2/2,
            "sentence": 2/2,
            "is": 2/2,
            "simple": 2/2,
            "yes": 2/1,
            "too": 2/1,
        }

        numerator = sum(tf1[t]*tf2[t]*idf[t]**2 for t in ["this", "sentence", "is", "simple"])
        denominator1 = math.sqrt(sum((tf1[t]*idf[t])**2 for t in sentence1))
        denominator2 = math.sqrt(sum((tf2[t]*idf[t])**2 for t in sentence2))

        expected = numerator / (denominator1 * denominator2)
        cosine = summarizer._compute_cosine(sentence1, sentence2, tf1, tf2, idf)
        self.assertEqual(expected, cosine)

    def test_article_example(self):
        """Source: http://www.prevko.cz/dite/skutecne-pribehy-deti"""
        parser = PlaintextParser.from_string(
            load_resource("articles/prevko_cz_1.txt"),
            Tokenizer("czech")
        )
        summarizer = LexRankSummarizer(stem_word)
        summarizer.stop_words = get_stop_words("czech")

        sentences = summarizer(parser.document, 20)
        self.assertEqual(len(sentences), 20)

########NEW FILE########
__FILENAME__ = test_lsa
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest
import sumy.summarizers.lsa as lsa_module

from nose import SkipTest
from sumy.summarizers.lsa import LsaSummarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from sumy._compat import to_unicode
from ..utils import build_document, load_resource


class TestLsa(unittest.TestCase):
    def test_numpy_not_installed(self):
        summarizer = LsaSummarizer()

        numpy = lsa_module.numpy
        lsa_module.numpy = None

        self.assertRaises(ValueError, summarizer, build_document(), 10)

        lsa_module.numpy = numpy

    def test_dictionary_without_stop_words(self):
        summarizer = LsaSummarizer()
        summarizer.stop_words = ["stop", "Halt", "SHUT", "HmMm"]

        document = build_document(
            ("stop halt shut hmmm", "Stop Halt Shut Hmmm",),
            ("StOp HaLt ShUt HmMm", "STOP HALT SHUT HMMM",),
            ("Some relevant sentence", "Some moRe releVant sentEnce",),
        )

        expected = frozenset(["some", "more", "relevant", "sentence"])
        dictionary = summarizer._create_dictionary(document)
        self.assertEqual(expected, frozenset(dictionary.keys()))

    def test_empty_document(self):
        document = build_document()
        summarizer = LsaSummarizer()

        sentences = summarizer(document, 10)
        self.assertEqual(len(sentences), 0)

    def test_single_sentence(self):
        document = build_document(("I am the sentence you like",))
        summarizer = LsaSummarizer()
        summarizer.stopwords = ("I", "am", "the",)

        sentences = summarizer(document, 10)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(to_unicode(sentences[0]), "I am the sentence you like")

    def test_document(self):
        document = build_document(
            ("I am the sentence you like", "Do you like me too",),
            ("This sentence is better than that above", "Are you kidding me",)
        )
        summarizer = LsaSummarizer()
        summarizer.stopwords = ("I", "am", "the", "you", "are", "me", "is", "than", "that", "this",)

        sentences = summarizer(document, 2)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]), "I am the sentence you like")
        self.assertEqual(to_unicode(sentences[1]), "This sentence is better than that above")

    def test_real_example(self):
        """Source: http://www.prevko.cz/dite/skutecne-pribehy-deti"""
        parser = PlaintextParser.from_string(
            "Jednalo se o případ chlapce v 6. třídě, který měl problémy s učením. "
            "Přerostly až v reparát z jazyka na konci školního roku. "
            "Nedopadl bohužel dobře a tak musel opakovat 6. třídu, což se chlapci ani trochu nelíbilo. "
            "Připadal si, že je mezi malými dětmi a realizoval se tím, že si ve třídě "
            "o rok mladších dětí budoval vedoucí pozici. "
            "Dost razantně. Fyzickou převahu měl, takže to nedalo až tak moc práce.",
            Tokenizer("czech")
        )
        summarizer = LsaSummarizer(Stemmer("czech"))
        summarizer.stop_words = get_stop_words("czech")

        sentences = summarizer(parser.document, 2)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(to_unicode(sentences[0]),
            "Jednalo se o případ chlapce v 6. třídě, který měl problémy s učením.")
        self.assertEqual(to_unicode(sentences[1]),
            "Nedopadl bohužel dobře a tak musel opakovat 6. třídu, což se chlapci ani trochu nelíbilo.")

    def test_article_example(self):
        """Source: http://www.prevko.cz/dite/skutecne-pribehy-deti"""
        parser = PlaintextParser.from_string(
            load_resource("articles/prevko_cz_1.txt"),
            Tokenizer("czech")
        )
        summarizer = LsaSummarizer(Stemmer("czech"))
        summarizer.stop_words = get_stop_words("czech")

        sentences = summarizer(parser.document, 20)
        self.assertEqual(len(sentences), 20)

    def test_issue_5_svd_converges(self):
        """Source: https://github.com/miso-belica/sumy/issues/5"""
        raise SkipTest("Can't reproduce the issue.")

        parser = PlaintextParser.from_string(
            load_resource("articles/svd_converges.txt"),
            Tokenizer("english")
        )
        summarizer = LsaSummarizer(Stemmer("english"))
        summarizer.stop_words = get_stop_words("english")

        sentences = summarizer(parser.document, 20)
        self.assertEqual(len(sentences), 20)

########NEW FILE########
__FILENAME__ = test_luhn
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.summarizers.luhn import LuhnSummarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers.czech import stem_word
from sumy.utils import get_stop_words
from sumy._compat import to_unicode
from ..utils import build_document, build_sentence


class TestLuhn(unittest.TestCase):
    def test_empty_document(self):
        document = build_document()
        summarizer = LuhnSummarizer()

        returned = summarizer(document, 10)
        self.assertEqual(len(returned), 0)

    def test_single_sentence(self):
        document = build_document(("Já jsem jedna věta",))
        summarizer = LuhnSummarizer()
        summarizer.stop_words = ("já", "jsem",)

        returned = summarizer(document, 10)
        self.assertEqual(len(returned), 1)

    def test_two_sentences(self):
        document = build_document(("Já jsem 1. věta", "A já ta 2. vítězná výhra"))
        summarizer = LuhnSummarizer()
        summarizer.stop_words = ("já", "jsem", "a", "ta",)

        returned = summarizer(document, 10)
        self.assertEqual(len(returned), 2)
        self.assertEqual(to_unicode(returned[0]), "Já jsem 1. věta")
        self.assertEqual(to_unicode(returned[1]), "A já ta 2. vítězná výhra")

    def test_two_sentences_but_one_winner(self):
        document = build_document((
            "Já jsem 1. vítězná ta věta",
            "A já ta 2. vítězná věta"
        ))
        summarizer = LuhnSummarizer()
        summarizer.stop_words = ("já", "jsem", "a", "ta",)

        returned = summarizer(document, 1)
        self.assertEqual(len(returned), 1)
        self.assertEqual(to_unicode(returned[0]), "A já ta 2. vítězná věta")

    def test_three_sentences(self):
        document = build_document((
            "wa s s s wa s s s wa",
            "wb s wb s wb s s s s s s s s s wb",
            "wc s s wc s s wc",
        ))
        summarizer = LuhnSummarizer()
        summarizer.stop_words = ("s",)

        returned = summarizer(document, 1)
        self.assertEqual(len(returned), 1)
        self.assertEqual(to_unicode(returned[0]), "wb s wb s wb s s s s s s s s s wb")

        returned = summarizer(document, 2)
        self.assertEqual(len(returned), 2)
        self.assertEqual(to_unicode(returned[0]), "wb s wb s wb s s s s s s s s s wb")
        self.assertEqual(to_unicode(returned[1]), "wc s s wc s s wc")

        returned = summarizer(document, 3)
        self.assertEqual(len(returned), 3)
        self.assertEqual(to_unicode(returned[0]), "wa s s s wa s s s wa")
        self.assertEqual(to_unicode(returned[1]), "wb s wb s wb s s s s s s s s s wb")
        self.assertEqual(to_unicode(returned[2]), "wc s s wc s s wc")

    def test_various_words_with_significant_percentage(self):
        document = build_document((
            "1 a",
            "2 b b",
            "3 c c c",
            "4 d d d",
            "5 z z z z",
            "6 e e e e e",
        ))
        summarizer = LuhnSummarizer()
        summarizer.stop_words = ("1", "2", "3", "4", "5", "6")

        returned = summarizer(document, 1)
        self.assertEqual(len(returned), 1)
        self.assertEqual(to_unicode(returned[0]), "6 e e e e e")

        returned = summarizer(document, 2)
        self.assertEqual(len(returned), 2)
        self.assertEqual(to_unicode(returned[0]), "5 z z z z")
        self.assertEqual(to_unicode(returned[1]), "6 e e e e e")

        returned = summarizer(document, 3)
        self.assertEqual(len(returned), 3)
        self.assertEqual(to_unicode(returned[0]), "3 c c c")
        self.assertEqual(to_unicode(returned[1]), "5 z z z z")
        self.assertEqual(to_unicode(returned[2]), "6 e e e e e")

    def test_real_example(self):
        parser = PlaintextParser.from_string(
            "Jednalo se o případ chlapce v 6. třídě, který měl problémy s učením. "
            "Přerostly až v reparát z jazyka na konci školního roku. "
            "Nedopadl bohužel dobře a tak musel opakovat 6. třídu, což se chlapci ani trochu nelíbilo. "
            "Připadal si, že je mezi malými dětmi a realizoval se tím, že si ve třídě "
            "o rok mladších dětí budoval vedoucí pozici. "
            "Dost razantně. Fyzickou převahu měl, takže to nedalo až tak moc práce.",
            Tokenizer("czech")
        )
        summarizer = LuhnSummarizer(stem_word)
        summarizer.stop_words = get_stop_words("czech")

        returned = summarizer(parser.document, 2)
        self.assertEqual(len(returned), 2)
        self.assertEqual(to_unicode(returned[0]),
            "Jednalo se o případ chlapce v 6. třídě, který měl problémy s učením.")
        self.assertEqual(to_unicode(returned[1]),
            "Připadal si, že je mezi malými dětmi a realizoval se tím, "
            "že si ve třídě o rok mladších dětí budoval vedoucí pozici.")


class TestSentenceRating(unittest.TestCase):
    def setUp(self):
        self.summarizer = LuhnSummarizer()
        self.sentence = build_sentence(
            "Nějaký muž šel kolem naší zahrady a žil pěkný život samotáře")

    def test_significant_words(self):
        self.summarizer.significant_percentage = 1/5
        words = self.summarizer._get_significant_words((
            "wa", "wb", "wc", "wd", "we", "wf", "wg", "wh", "wi", "wj",
            "wa", "wb",
        ))

        self.assertEqual(tuple(sorted(words)), ("wa", "wb"))

    def test_stop_words_not_in_significant_words(self):
        self.summarizer.stop_words = ["stop", "Halt", "SHUT", "HmMm"]
        words = self.summarizer._get_significant_words([
            "stop", "Stop", "StOp", "STOP",
            "halt", "Halt", "HaLt", "HALT",
            "shut", "Shut", "ShUt", "SHUT",
            "hmmm", "Hmmm", "HmMm", "HMMM",
            "some", "relevant", "word",
            "some", "more", "relevant", "word",
        ])

        self.assertEqual(tuple(sorted(words)), ("relevant", "some", "word"))

    def test_zero_rating(self):
        significant_stems = ()
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 0)

    def test_single_word(self):
        significant_stems = ("muž",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 0)

    def test_single_word_before_end(self):
        significant_stems = ("život",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 0)

    def test_single_word_at_end(self):
        significant_stems = ("samotáře",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 0)

    def test_two_chunks_too_far(self):
        significant_stems = ("šel", "žil",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 0)

    def test_two_chunks_at_begin(self):
        significant_stems = ("muž", "šel",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 2)

    def test_two_chunks_before_end(self):
        significant_stems = ("pěkný", "život",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 2)

    def test_two_chunks_at_end(self):
        significant_stems = ("pěkný", "samotáře",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 4/3)

    def test_three_chunks_at_begin(self):
        significant_stems = ("nějaký", "muž", "šel",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 3)

    def test_three_chunks_at_end(self):
        significant_stems = ("pěkný", "život", "samotáře",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 3)

    def test_three_chunks_with_gaps(self):
        significant_stems = ("muž", "šel", "zahrady",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 9/5)

    def test_chunks_with_user_gap(self):
        self.summarizer.max_gap_size = 6
        significant_stems = ("muž", "šel", "pěkný",)
        self.assertEqual(self.summarizer.rate_sentence(self.sentence, significant_stems), 9/8)

    def test_three_chunks_with_1_gap(self):
        sentence = build_sentence("w s w s w")
        significant_stems = ("w",)

        self.assertEqual(self.summarizer.rate_sentence(sentence, significant_stems), 9/5)

    def test_three_chunks_with_2_gap(self):
        sentence = build_sentence("w s s w s s w")
        significant_stems = ("w",)

        self.assertEqual(self.summarizer.rate_sentence(sentence, significant_stems), 9/7)

    def test_three_chunks_with_3_gap(self):
        sentence = build_sentence("w s s s w s s s w")
        significant_stems = ("w",)

        self.assertEqual(self.summarizer.rate_sentence(sentence, significant_stems), 1)

########NEW FILE########
__FILENAME__ = test_random
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.summarizers.random import RandomSummarizer
from sumy._compat import to_unicode
from ..utils import build_document, build_document_from_string


class TestRandom(unittest.TestCase):
    def test_empty_document(self):
        document = build_document()
        summarizer = RandomSummarizer()

        sentences = summarizer(document, 10)
        self.assertEqual(len(sentences), 0)

    def test_less_sentences_than_requested(self):
        document = build_document_from_string("""
            This is only one sentence.
        """)
        summarizer = RandomSummarizer()

        sentences = summarizer(document, 10)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(to_unicode(sentences[0]), "This is only one sentence.")

    def test_sentences_in_right_order(self):
        document = build_document_from_string("""
            # Heading one
            First sentence.
            Second sentence.
            Third sentence.
        """)
        summarizer = RandomSummarizer()

        sentences = summarizer(document, 4)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(to_unicode(sentences[0]), "First sentence.")
        self.assertEqual(to_unicode(sentences[1]), "Second sentence.")
        self.assertEqual(to_unicode(sentences[2]), "Third sentence.")

    def test_more_sentences_than_requested(self):
        document = build_document_from_string("""
            # Heading one
            First sentence.
            Second sentence.
            Third sentence.

            # Heading two
            I like sentences
            They are so wordy
            And have many many letters
            And are green in my editor
            But someone doesn't like them :(
        """)
        summarizer = RandomSummarizer()

        sentences = summarizer(document, 4)
        self.assertEqual(len(sentences), 4)

########NEW FILE########
__FILENAME__ = test_text_rank
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy._compat import to_unicode
from ..utils import build_document


class TestTextRank(unittest.TestCase):
    def test_empty_document(self):
        document = build_document()
        summarizer = TextRankSummarizer(Stemmer("english"))

        returned = summarizer(document, 10)
        self.assertEqual(len(returned), 0)

    def test_single_sentence(self):
        document = build_document(("I am one sentence",))
        summarizer = TextRankSummarizer()
        summarizer.stop_words = ("I", "am",)

        returned = summarizer(document, 10)
        self.assertEqual(len(returned), 1)

    def test_two_sentences(self):
        document = build_document(("I am that 1. sentence", "And I am 2. winning prize"))
        summarizer = TextRankSummarizer()
        summarizer.stop_words = ("I", "am", "and", "that",)

        returned = summarizer(document, 10)
        self.assertEqual(len(returned), 2)
        self.assertEqual(to_unicode(returned[0]), "I am that 1. sentence")
        self.assertEqual(to_unicode(returned[1]), "And I am 2. winning prize")

    def test_stop_words_correctly_removed(self):
        summarizer = TextRankSummarizer()
        summarizer.stop_words = ["stop", "Halt", "SHUT", "HmMm"]

        document = build_document(
            ("stop halt shut hmmm", "Stop Halt Shut Hmmm",),
            ("StOp HaLt ShUt HmMm", "STOP HALT SHUT HMMM",),
            ("Some relevant sentence", "Some moRe releVant sentEnce",),
        )
        sentences = document.sentences

        expected = []
        returned = summarizer._to_words_set(sentences[0])
        self.assertEqual(expected, returned)
        returned = summarizer._to_words_set(sentences[1])
        self.assertEqual(expected, returned)
        returned = summarizer._to_words_set(sentences[2])
        self.assertEqual(expected, returned)
        returned = summarizer._to_words_set(sentences[3])
        self.assertEqual(expected, returned)

        expected = ["some", "relevant", "sentence"]
        returned = summarizer._to_words_set(sentences[4])
        self.assertEqual(expected, returned)
        expected = ["some", "more", "relevant", "sentence"]
        returned = summarizer._to_words_set(sentences[5])
        self.assertEqual(expected, returned)

    def test_three_sentences_but_second_winner(self):
        document = build_document([
            "I am that 1. sentence",
            "And I am 2. sentence - winning sentence",
            "And I am 3. sentence - winner is my 2nd name",
        ])
        summarizer = TextRankSummarizer()
        summarizer.stop_words = ["I", "am", "and", "that"]

        returned = summarizer(document, 1)
        self.assertEqual(len(returned), 1)
        self.assertEqual(to_unicode(returned[0]), "And I am 2. sentence - winning sentence")

    def test_sentences_rating(self):
        document = build_document([
            "a c e g",
            "a b c d e f g",
            "b d f",
        ])
        summarizer = TextRankSummarizer()
        summarizer.stop_words = ["I", "am", "and", "that"]

        ratings = summarizer.rate_sentences(document)
        self.assertEqual(len(ratings), 3)
        self.assertTrue(ratings[document.sentences[1]] > ratings[document.sentences[0]])
        self.assertTrue(ratings[document.sentences[0]] > ratings[document.sentences[2]])

########NEW FILE########
__FILENAME__ = test_tokenizers
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.nlp.tokenizers import Tokenizer


class TestTokenizer(unittest.TestCase):
    def test_missing_language(self):
        self.assertRaises(LookupError, Tokenizer, "klingon")

    def test_ensure_czech_tokenizer_available(self):
        tokenizer = Tokenizer("czech")
        self.assertEqual("czech", tokenizer.language)

        sentences = tokenizer.to_sentences("""
            Měl jsem sen, že toto je sen. Bylo to také zvláštní.
            Jakoby jsem plaval v moři rekurze.
        """)

        expected = (
            "Měl jsem sen, že toto je sen.",
            "Bylo to také zvláštní.",
            "Jakoby jsem plaval v moři rekurze.",
        )
        self.assertEqual(expected, sentences)

    def test_language_getter(self):
        tokenizer = Tokenizer("english")
        self.assertEqual("english", tokenizer.language)

    def test_tokenize_sentence(self):
        tokenizer = Tokenizer("english")
        words = tokenizer.to_words("I am a very nice sentence with comma, but..")

        expected = (
            "I", "am", "a", "very", "nice", "sentence",
            "with", "comma",
        )
        self.assertEqual(expected, words)

    def test_tokenize_paragraph(self):
        tokenizer = Tokenizer("english")
        sentences = tokenizer.to_sentences("""
            I am a very nice sentence with comma, but..
            This is next sentence. "I'm bored", said Pepek.
            Ou jee, duffman is here.
        """)

        expected = (
            "I am a very nice sentence with comma, but..",
            "This is next sentence.",
            '"I\'m bored", said Pepek.',
            "Ou jee, duffman is here.",
        )
        self.assertEqual(expected, sentences)

    def test_slovak_alias_into_czech_tokenizer(self):
        tokenizer = Tokenizer("slovak")
        self.assertEqual(tokenizer.language, "slovak")

        sentences = tokenizer.to_sentences("""
            Je to veľmi fajn. Bodaj by nie.
            Ale na druhej strane čo je to oproti inému?
            To nechám na čitateľa.
        """)

        expected = (
            "Je to veľmi fajn.",
            "Bodaj by nie.",
            "Ale na druhej strane čo je to oproti inému?",
            "To nechám na čitateľa.",
        )
        self.assertEqual(expected, sentences)

########NEW FILE########
__FILENAME__ = test_compat
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import SkipTest
from sumy import _compat as py3k


BYTES_STRING = "ľščťžáýíééäúňô €đ€Ł¤".encode("utf8")
UNICODE_STRING = "ľščťžáýíééäúňô €đ€Ł¤"


class TestPy3k(unittest.TestCase):
    def assertStringsEqual(self, str1, str2, *args):
        self.assertEqual(type(str1), type(str2), *args)
        self.assertEqual(str1, str2, *args)

    def test_bytes_to_bytes(self):
        returned = py3k.to_bytes(BYTES_STRING)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_unicode_to_bytes(self):
        returned = py3k.to_bytes(UNICODE_STRING)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_str_object_to_bytes(self):
        value = UNICODE_STRING if py3k.PY3 else BYTES_STRING
        instance = self.__build_test_instance("__str__", value)

        returned = py3k.to_bytes(instance)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_unicode_object_to_bytes(self):
        if not py3k.PY3:
            raise SkipTest("Py2 object has `__str__` method called 1st")

        instance = self.__build_test_instance("__str__", UNICODE_STRING)

        returned = py3k.to_bytes(instance)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_repr_object_to_bytes(self):
        value = UNICODE_STRING if py3k.PY3 else BYTES_STRING
        instance = self.__build_test_instance("__repr__", value)

        returned = py3k.to_bytes(instance)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_data_to_unicode(self):
        returned = py3k.to_unicode(BYTES_STRING)
        self.assertStringsEqual(UNICODE_STRING, returned)

    def test_unicode_to_unicode(self):
        returned = py3k.to_unicode(UNICODE_STRING)
        self.assertStringsEqual(UNICODE_STRING, returned)

    def test_str_object_to_unicode(self):
        value = UNICODE_STRING if py3k.PY3 else BYTES_STRING
        instance = self.__build_test_instance("__str__", value)

        returned = py3k.to_unicode(instance)
        self.assertStringsEqual(UNICODE_STRING, returned)

    def test_unicode_object_to_unicode(self):
        method = "__str__" if py3k.PY3 else "__unicode__"
        instance = self.__build_test_instance(method, UNICODE_STRING)

        returned = py3k.to_unicode(instance)
        self.assertStringsEqual(UNICODE_STRING, returned)

    def test_repr_object_to_unicode(self):
        value = UNICODE_STRING if py3k.PY3 else BYTES_STRING
        instance = self.__build_test_instance("__repr__", value)

        returned = py3k.to_unicode(instance)
        self.assertStringsEqual(UNICODE_STRING, returned)

    def __build_test_instance(self, tested_method, value):
        class Object(object):
            def __init__(self, value):
                self.value = value

        setattr(Object, tested_method, lambda self: self.value)
        return Object(value)

########NEW FILE########
__FILENAME__ = test_unicode_compatible_class
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import SkipTest
from sumy import _compat as compat


BYTES_STRING = "ľščťžáýíééäúňô €đ€Ł¤".encode("utf8")
UNICODE_STRING = "ľščťžáýíééäúňô €đ€Ł¤"
NATIVE_STRING = compat.to_string(UNICODE_STRING)


@compat.unicode_compatible
class O(object):
    def __unicode__(self):
        return UNICODE_STRING


class TestObject(unittest.TestCase):
    def setUp(self):
        self.o = O()

    def assertStringsEqual(self, str1, str2, *args):
        self.assertEqual(type(str1), type(str2), *args)
        self.assertEqual(str1, str2, *args)

    def test_native_bytes(self):
        if not compat.PY3:
            raise SkipTest("Python 2 doesn't support method `__bytes__`")

        returned = bytes(self.o)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_native_unicode(self):
        if compat.PY3:
            raise SkipTest("Python 3 doesn't support method `__unicode__`")

        returned = unicode(self.o)
        self.assertStringsEqual(UNICODE_STRING, returned)

    def test_to_bytes(self):
        returned = compat.to_bytes(self.o)
        self.assertStringsEqual(BYTES_STRING, returned)

    def test_to_string(self):
        returned = compat.to_string(self.o)
        self.assertStringsEqual(NATIVE_STRING, returned)

    def test_to_unicode(self):
        returned = compat.to_unicode(self.o)
        self.assertStringsEqual(UNICODE_STRING, returned)

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from sumy.utils import get_stop_words, read_stop_words, ItemsCount
from ..utils import expand_resource_path


class TestUtils(unittest.TestCase):
    def test_ok_stop_words_language(self):
        stop_words = get_stop_words("french")
        self.assertTrue(len(stop_words) > 1, str(len(stop_words)))

    def test_missing_stop_words_language(self):
        self.assertRaises(LookupError, get_stop_words, "klingon")

    def test_ok_custom_stopwords_file(self):
        stop_words = read_stop_words(expand_resource_path("stopwords/language.txt"))
        self.assertEqual(len(stop_words), 4)

    def test_custom_stop_words_file_not_found(self):
        self.assertRaises(IOError, read_stop_words, expand_resource_path("stopwords/klingon.txt"))

    def test_percentage_items_count(self):
        count = ItemsCount("20%")
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0, 1])

        count = ItemsCount("100%")
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        count = ItemsCount("50%")
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0, 1, 2, 3, 4])

        count = ItemsCount("30%")
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0, 1, 2])

        count = ItemsCount("35%")
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0, 1, 2])

    def test_float_items_count(self):
        count = ItemsCount(3.5)
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0, 1, 2])

        count = ItemsCount(True)
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [0])

        count = ItemsCount(False)
        returned = count([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(returned, [])

    def test_unsuported_items_count(self):
        count = ItemsCount("Hacker")
        self.assertRaises(ValueError, count, [])

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from os.path import dirname, join, abspath
from sumy.nlp.tokenizers import Tokenizer
from sumy._compat import to_string, to_unicode
from sumy.models.dom import ObjectDocumentModel, Paragraph, Sentence


_TOKENIZER = Tokenizer("czech")


def expand_resource_path(path):
    return join(abspath(dirname(__file__)), to_string("data"), to_string(path))


def load_resource(path):
    path = expand_resource_path(path)
    with open(path, "rb") as file:
        return to_unicode(file.read())


def build_document(*sets_of_sentences):
    paragraphs = []
    for sentences in sets_of_sentences:
        sentence_instances = []
        for sentence_as_string in sentences:
            sentence = build_sentence(sentence_as_string)
            sentence_instances.append(sentence)

        paragraphs.append(Paragraph(sentence_instances))

    return ObjectDocumentModel(paragraphs)


def build_document_from_string(string):
    sentences = []
    paragraphs = []

    for line in string.strip().splitlines():
        line = line.lstrip()
        if line.startswith("# "):
            sentences.append(build_sentence(line[2:], is_heading=True))
        elif not line:
            paragraphs.append(Paragraph(sentences))
            sentences = []
        else:
            sentences.append(build_sentence(line))

    paragraphs.append(Paragraph(sentences))
    return ObjectDocumentModel(paragraphs)


def build_sentence(sentence_as_string, is_heading=False):
    return Sentence(sentence_as_string, _TOKENIZER, is_heading)

########NEW FILE########
