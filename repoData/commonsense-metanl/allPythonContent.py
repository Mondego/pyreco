__FILENAME__ = extprocess
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
Tools for using an external program as an NLP pipe. See, for example,
freeling.py.
"""

import subprocess
import unicodedata
import sys
from ftfy.fixes import remove_control_chars, remove_unsafe_private_use
if sys.version_info.major == 2:
    range = xrange
    str_func = unicode
else:
    str_func = str


def render_safe(text):
    '''
    Make sure the given text is safe to pass to an external process.
    '''
    return remove_control_chars(remove_unsafe_private_use(text))


class ProcessError(IOError):
    """
    A subclass of IOError raised when we can't start the external process.
    """
    pass


class ProcessWrapper(object):
    """
    A ProcessWrapper uses the `subprocess` module to keep a process open that
    we can pipe stuff through to get NLP results.

    Instead of every instance immediately opening a process, however, it waits
    until the first time it is needed, then starts the process.

    Many methods are intended to be implemented by subclasses of ProcessWrapper
    that actually know what program they're talking to.
    """
    def __del__(self):
        """
        Clean up by closing the pipe.
        """
        if hasattr(self, '_process'):
            self._process.stdin.close()

    @property
    def process(self):
        """
        Store the actual process in _process. If it doesn't exist yet, create
        it.
        """
        if hasattr(self, '_process'):
            return self._process
        else:
            self._process = self._get_process()
            return self._process

    def _get_command(self):
        """
        This method should return the command to run, as a list
        of arguments that can be used by subprocess.Popen.
        """
        raise NotImplementedError

    def _get_process(self):
        """
        Create the process by running the specified command.
        """
        command = self._get_command()
        return subprocess.Popen(command, bufsize=-1, close_fds=True,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)

    def get_record_root(self, record):
        """
        Given a *record* (the data that the external process returns for a
        given single token), this specifies how to extract its root word
        (aka its lemma).
        """
        raise NotImplementedError

    def get_record_token(self, record):
        """
        Given a record, this specifies how to extract the exact word or token
        that was processed.
        """
        raise NotImplementedError

    def analyze(self, text):
        """
        Take text as input, run it through the external process, and return a
        list of *records* containing the results.
        """
        raise NotImplementedError

    def send_input(self, data):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def receive_output_line(self):
        line = self.process.stdout.readline()
        if not line:
            raise ProcessError("reached end of output")
        return line

    def restart_process(self):
        if hasattr(self, '_process'):
            self._process.stdin.close()
        self._process = self._get_process()
        return self._process

    def tokenize_list(self, text):
        """
        Split a text into separate words.
        """
        return [self.get_record_token(record) for record in self.analyze(text)]

    def tokenize(self, text):
        """
        Yell at people who are still using simplenlp's bad idea of
        tokenization.
        """
        raise NotImplementedError("tokenize is deprecated. Use tokenize_list.")

    def is_stopword_record(self, record, common_words=False):
        """
        Given a record, return whether it represents a stopword (a word that
        should be discarded in NLP results).

        Note that we want very few words to be stopwords. Words that are
        meaningful but simply common can be recognized by their very high word
        frequency, and handled appropriately. Often, we only want determiners
        (such as 'a', 'an', and 'the' in English) to be stopwords.

        Takes in a vestigial parameter, `common_words`, and ignores it.
        """
        raise NotImplementedError

    def is_stopword(self, text):
        """
        Determine whether a single word is a stopword, or whether a short
        phrase is made entirely of stopwords, disregarding context.

        Use of this function should be avoided; it's better to give the text
        in context and let the process determine which words are the stopwords.
        """
        found_content_word = False
        for record in self.analyze(text):
            if not self.is_stopword_record(record):
                found_content_word = True
                break
        return not found_content_word

    def get_record_pos(self, record):
        """
        Given a record, get the word's part of speech.

        This default implementation simply distinguishes stopwords from
        non-stopwords.
        """
        if self.is_stopword_record(record):
            return 'STOP'
        else:
            return 'TERM'

    def normalize_list(self, text, cache=None):
        """
        Get a canonical list representation of text, with words
        separated and reduced to their base forms.

        TODO: use the cache.
        """
        words = []
        analysis = self.analyze(text)
        for record in analysis:
            if not self.is_stopword_record(record):
                words.append(self.get_record_root(record))
        if not words:
            # Don't discard stopwords if that's all you've got
            words = [self.get_record_token(record) for record in analysis]
        return words

    def normalize(self, text, cache=None):
        """
        Get a canonical string representation of this text, like
        :meth:`normalize_list` but joined with spaces.

        TODO: use the cache.
        """
        return ' '.join(self.normalize_list(text, cache))

    def tag_and_stem(self, text, cache=None):
        """
        Given some text, return a sequence of (stem, pos, text) triples as
        appropriate for the reader. `pos` can be as general or specific as
        necessary (for example, it might label all parts of speech, or it might
        only distinguish function words from others).

        Twitter-style hashtags and at-mentions have the stem and pos they would
        have without the leading # or @. For instance, if the reader's triple
        for "thing" is ('thing', 'NN', 'things'), then "#things" would come out
        as ('thing', 'NN', '#things').
        """
        analysis = self.analyze(text)
        triples = []

        for record in analysis:
            root = self.get_record_root(record)
            token = self.get_record_token(record)

            if token:
                if unicode_is_punctuation(token):
                    triples.append((token, '.', token))
                else:
                    pos = self.get_record_pos(record)
                    triples.append((root, pos, token))
        return triples

    def extract_phrases(self, text):
        """
        Given some text, extract phrases of up to 2 content words,
        and map their normalized form to the complete phrase.
        """
        analysis = self.analyze(text)
        for pos1 in range(len(analysis)):
            rec1 = analysis[pos1]
            if not self.is_stopword_record(rec1):
                yield self.get_record_root(rec1), rec1[0]
                for pos2 in range(pos1 + 1, len(analysis)):
                    rec2 = analysis[pos2]
                    if not self.is_stopword_record(rec2):
                        roots = [self.get_record_root(rec1),
                                 self.get_record_root(rec2)]
                        pieces = [analysis[i][0] for i in range(pos1, pos2+1)]
                        term = ' '.join(roots)
                        phrase = ''.join(pieces)
                        yield term, phrase
                        break


def unicode_is_punctuation(text):
    """
    Test if a token is made entirely of Unicode characters of the following
    classes:

    - P: punctuation
    - S: symbols
    - Z: separators
    - M: combining marks
    - C: control characters

    >>> unicode_is_punctuation('word')
    False
    >>> unicode_is_punctuation('。')
    True
    >>> unicode_is_punctuation('-')
    True
    >>> unicode_is_punctuation('-3')
    False
    >>> unicode_is_punctuation('あ')
    False
    """
    for char in str_func(text):
        category = unicodedata.category(char)[0]
        if category not in 'PSZMC':
            return False
    return True

########NEW FILE########
__FILENAME__ = freeling
from __future__ import unicode_literals

import pkg_resources
from metanl.extprocess import ProcessWrapper, ProcessError, render_safe


class FreelingWrapper(ProcessWrapper):
    r"""
    Handle English, Spanish, Italian, Portuguese, or Welsh text by calling an
    installed copy of FreeLing.

    The constructor takes one argument, which is the installed filename of the
    language-specific config file, such as 'en.cfg'.

        >>> english.tag_and_stem("This is a test.\n\nIt has two paragraphs, and that's okay.")
        [('this', 'DT', 'This'), ('be', 'VBZ', 'is'), ('a', 'DT', 'a'), ('test', 'NN', 'test'), ('.', '.', '.'), ('it', 'PRP', 'It'), ('have', 'VBZ', 'has'), ('two', 'DT', 'two'), ('paragraph', 'NNS', 'paragraphs'), (',', '.', ','), ('and', 'CC', 'and'), ('that', 'PRP', 'that'), ('be', 'VBZ', "'s"), ('okay', 'JJ', 'okay'), ('.', '.', '.')]

        >>> english.tag_and_stem("this has\ntwo lines")
        [('this', 'DT', 'this'), ('have', 'VBZ', 'has'), ('two', 'DT', 'two'), ('line', 'NNS', 'lines')]

    """
    def __init__(self, lang):
        self.lang = lang
        self.configfile = pkg_resources.resource_filename(
            __name__, 'data/freeling/%s.cfg' % lang)
        self.splitterfile = pkg_resources.resource_filename(
            __name__, 'data/freeling/generic_splitter.dat')

    def _get_command(self):
        """
        Get the command for running the basic FreeLing pipeline in the
        specified language.

        The options we choose are:

            -f data/freeling/<language>.cfg
                load our custom configuration for the language
            --fsplit data/freeling/generic_splitter.dat
                don't do any special handling of ends of sentences
        """
        return ['analyze', '-f', self.configfile, '--fsplit',
                self.splitterfile]

    def get_record_root(self, record):
        """
        Given a FreeLing record, return the root word.
        """
        return record[1].lower()

    def get_record_token(self, record):
        """
        The token of a FreeLing record is the first item on the line.
        """
        return record[0]

    def get_record_pos(self, record):
        """
        In English, return the third segment of the record.

        In other languages, this segment contains one letter for the part of
        speech, plus densely-encoded features that we really have no way to
        use. Return just the part-of-speech letter.
        """
        if self.lang == 'en':
            return record[2]
        else:
            return record[2][0]

    def is_stopword_record(self, record, common_words=False):
        """
        Determiners are stopwords. Detect this by checking whether their POS
        starts with 'D'.
        """
        return (record[2][0] == 'D')

    def analyze(self, text):
        """
        Run text through the external process, and get a list of lists
        ("records") that contain the analysis of each word.
        """
        try:
            text = render_safe(text).strip()
            if not text:
                return []
            chunks = text.split('\n')
            results = []
            for chunk_text in chunks:
                if chunk_text.strip():
                    textbytes = (chunk_text + '\n').encode('utf-8')
                    self.send_input(textbytes)
                    out_line = ''
                    while True:
                        out_line = self.receive_output_line()
                        out_line = out_line.decode('utf-8')

                        if out_line == '\n':
                            break

                        record = out_line.strip('\n').split(' ')
                        results.append(record)
            return results
        except ProcessError:
            self.restart_process()
            return self.analyze(text)


LANGUAGES = {}
english = LANGUAGES['en'] = FreelingWrapper('en')
spanish = LANGUAGES['es'] = FreelingWrapper('es')
italian = LANGUAGES['it'] = FreelingWrapper('it')
portuguese = LANGUAGES['pt'] = FreelingWrapper('pt')
russian = LANGUAGES['ru'] = FreelingWrapper('ru')
welsh = LANGUAGES['cy'] = FreelingWrapper('cy')

########NEW FILE########
__FILENAME__ = mecab
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
"""
This module provides some basic Japanese NLP by wrapping the output of MeCab.
It can tokenize and normalize Japanese words, detect and remove stopwords,
and it can even respell words in kana or romaji.

This requires mecab to be installed separately. On Ubuntu:
    sudo apt-get install mecab mecab-ipadic-utf8

>>> print(normalize('これはテストです'))
テスト
>>> tag_and_stem('これはテストです。')
[('\u3053\u308c', '~\u540d\u8a5e', '\u3053\u308c'), ('\u306f', '~\u52a9\u8a5e', '\u306f'), ('\u30c6\u30b9\u30c8', '\u540d\u8a5e', '\u30c6\u30b9\u30c8'), ('\u3067\u3059', '~\u52a9\u52d5\u8a5e', '\u3067\u3059'), ('\u3002', '.', '\u3002')]
"""

from metanl.token_utils import string_pieces
from metanl.extprocess import ProcessWrapper, ProcessError, render_safe
from collections import namedtuple
import unicodedata
import re
import sys
if sys.version_info.major == 2:
    range = xrange
    str_func = unicode
else:
    str_func = str


class MeCabError(ProcessError):
    pass

MeCabRecord = namedtuple('MeCabRecord',
    [
        'surface',
        'pos',
        'subclass1',
        'subclass2',
        'subclass3',
        'conjugation',
        'form',
        'root',
        'reading',
        'pronunciation'
    ]
)


# MeCab outputs the part of speech of its terms. We can simply identify
# particular (coarse or fine) parts of speech as containing stopwords.

STOPWORD_CATEGORIES = set([
    '助詞',          # coarse: particle
    '助動詞',        # coarse: auxiliary verb
    '接続詞',        # coarse: conjunction
    'フィラー',      # coarse: filler
    '記号',          # coarse: symbol
    '非自立',        # fine: 'not independent'
])


# Forms of particular words should also be considered stopwords sometimes.
#
# A thought: Should the rare kanji version of suru not be a stopword?
# I'll need to ask someone who knows more Japanese, but it may be
# that if they're using the kanji it's for particular emphasis.
STOPWORD_ROOTS = set([
    'する',          # suru: "to do"
    '為る',          # suru in kanji (very rare)
    'くる',          # kuru: "to come"
    '来る',          # kuru in kanji
    'いく',          # iku: "to go"
    '行く',          # iku in kanji
    'いる',          # iru: "to be" (animate)
    '居る',          # iru in kanji
    'ある',          # aru: "to exist" or "to have"
    '有る',          # aru in kanji
    'もの',          # mono: "thing"
    '物',            # mono in kanji
    'よう',          # yō: "way"
    '様',            # yō in kanji
    'れる',          # passive suffix
    'これ',          # kore: "this"
    'それ',          # sore: "that"
    'あれ',          # are: "that over there"
    'この',          # kono: "this"
    'その',          # sono: "that"
    'あの',          # ano: "that over there", "yon"
])


class MeCabWrapper(ProcessWrapper):
    """
    Handle Japanese text using the command-line version of MeCab.
    (mecab-python is convenient, but its installer is too flaky to rely on.)

    ja_cabocha gives more sophisticated results, but requires a large number of
    additional dependencies. Using this tool for Japanese requires only
    MeCab to be installed and accepting UTF-8 text.
    """
    def _get_command(self):
        return ['mecab']

    def _get_process(self):
        try:
            proc = ProcessWrapper._get_process(self)
        except (OSError, ProcessError):
            raise MeCabError("MeCab didn't start. See README.txt for details "
                             "about installing MeCab and other Japanese NLP "
                             "tools.")
        return proc

    def get_record_root(self, record):
        """
        Given a MeCab record, return the root word.
        """
        if record.root == '*':
            return record.surface
        else:
            return record.root

    def get_record_token(self, record):
        return record.surface

    def analyze(self, text):
        """
        Runs a line of text through MeCab, and returns the results as a
        list of lists ("records") that contain the MeCab analysis of each
        word.
        """
        try:
            self.process  # make sure things are loaded
            text = render_safe(text).replace('\n', ' ').lower()
            results = []
            for chunk in string_pieces(text):
                self.send_input((chunk + '\n').encode('utf-8'))
                while True:
                    out_line = self.receive_output_line().decode('utf-8')
                    if out_line == 'EOS\n':
                        break

                    word, info = out_line.strip('\n').split('\t')
                    record_parts = [word] + info.split(',')

                    # Pad the record out to have 10 parts if it doesn't
                    record_parts += [None] * (10 - len(record_parts))
                    record = MeCabRecord(*record_parts)

                    # special case for detecting nai -> n
                    if (record.surface == 'ん' and
                        record.conjugation == '不変化型'):
                        # rebuild the record so that record.root is 'nai'
                        record_parts[MeCabRecord._fields.index('root')] = 'ない'
                        record = MeCabRecord(*record_parts)

                    results.append(record)
            return results
        except ProcessError:
            self.restart_process()
            return self.analyze(text)

    def is_stopword_record(self, record):
        """
        Determine whether a single MeCab record represents a stopword.

        This mostly determines words to strip based on their parts of speech.
        If common_words is set to True (default), it will also strip common
        verbs and nouns such as くる and よう. If more_stopwords is True, it
        will look at the sub-part of speech to remove more categories.
        """
        # preserve negations
        if record.root == 'ない':
            return False
        return (
            record.pos in STOPWORD_CATEGORIES or
            record.subclass1 in STOPWORD_CATEGORIES or
            record.root in STOPWORD_ROOTS
        )

    def get_record_pos(self, record):
        """
        Given a record, get the word's part of speech.

        Here we're going to return MeCab's part of speech (written in
        Japanese), though if it's a stopword we prefix the part of speech
        with '~'.
        """
        if self.is_stopword_record(record):
            return '~' + record.pos
        else:
            return record.pos


class NoStopwordMeCabWrapper(MeCabWrapper):
    """
    This version of the MeCabWrapper doesn't label anything as a stopword. It's
    used in building ConceptNet because discarding stopwords based on MeCab
    categories loses too much information.
    """
    def is_stopword_record(self, record, common_words=False):
        return False


# Define the classes of characters we'll be trying to transliterate
NOT_KANA, KANA, NN, SMALL, SMALL_Y, SMALL_TSU, PROLONG = range(7)


def to_kana(text):
    """
    Use MeCab to turn any text into its phonetic spelling, as katakana
    separated by spaces.
    """
    records = MECAB.analyze(text)
    kana = []
    for record in records:
        if record.pronunciation:
            kana.append(record.pronunciation)
        elif record.reading:
            kana.append(record.reading)
        else:
            kana.append(record.surface)
    return ' '.join(k for k in kana if k)


def get_kana_info(char):
    """
    Return two things about each character:

    - Its transliterated value (in Roman characters, if it's a kana)
    - A class of characters indicating how it affects the romanization
    """
    try:
        name = unicodedata.name(char)
    except ValueError:
        return char, NOT_KANA

    # The names we're dealing with will probably look like
    # "KATAKANA CHARACTER ZI".
    if (name.startswith('HIRAGANA LETTER') or
        name.startswith('KATAKANA LETTER') or
        name.startswith('KATAKANA-HIRAGANA')):
        names = name.split()
        syllable = str_func(names[-1].lower())

        if name.endswith('SMALL TU'):
            # The small tsu (っ) doubles the following consonant.
            # It'll show up as 't' on its own.
            return 't', SMALL_TSU
        elif names[-1] == 'N':
            return 'n', NN
        elif names[1] == 'PROLONGED':
            # The prolongation marker doubles the previous vowel.
            # It'll show up as '_' on its own.
            return '_', PROLONG
        elif names[-2] == 'SMALL':
            # Small characters tend to modify the sound of the previous
            # kana. If they can't modify anything, they're appended to
            # the letter 'x' instead.
            if syllable.startswith('y'):
                return 'x' + syllable, SMALL_Y
            else:
                return 'x' + syllable, SMALL

        return syllable, KANA
    else:
        if char in ROMAN_PUNCTUATION_TABLE:
            char = ROMAN_PUNCTUATION_TABLE[char]
        return char, NOT_KANA


def respell_hepburn(syllable):
    while syllable[:2] in HEPBURN_TABLE:
        syllable = HEPBURN_TABLE[syllable[:2]] + syllable[2:]
    return syllable


def romanize(text, respell=respell_hepburn):
    if respell is None:
        respell = lambda x: x

    kana = to_kana(str_func(text))
    pieces = []
    prevgroup = NOT_KANA

    for char in kana:
        roman, group = get_kana_info(char)
        if prevgroup == NN:
            # When the previous syllable is 'n' and the next syllable would
            # make it ambiguous, add an apostrophe.
            if group != KANA or roman[0] in 'aeinouy':
                if unicodedata.category(roman[0])[0] == 'L':
                    pieces[-1] += "'"

        # Determine how to spell the current character
        if group == NOT_KANA:
            pieces.append(roman)
        elif group == SMALL_TSU or group == NN:
            pieces.append(roman)
        elif group == SMALL_Y:
            if prevgroup == KANA:
                # Modify the previous syllable, if that makes sense. For
                # example, 'ni' + 'ya' becomes 'nya'.
                if not pieces[-1].endswith('i'):
                    pieces.append(roman)
                else:
                    modifier = roman[1:]
                    modified = pieces[-1]
                    pieces[-1] = modified[:-1] + modifier
            else:
                pieces.append(roman)
        elif group == SMALL:
            # Don't respell small vowels _yet_. We'll handle that at the end.
            # This may be a bit ambiguous, but nobody expects to see "tea"
            # spelled "texi".
            pieces.append(roman)
        elif group == PROLONG:
            if prevgroup in (KANA, SMALL_Y, SMALL):
                pieces[-1] = pieces[-1][:-1] + respell(pieces[-1][-1] + '_')
            else:
                pieces.append(roman)
        else:  # this is a normal kana
            if prevgroup == SMALL_TSU:
                if roman[0] in 'aeiouy':
                    # wait, there's no consonant there; cope by respelling the
                    # previous kana as 't-'
                    pieces[-1] = 't-'
                else:
                    # Turn the previous 't' into a copy of the first consonant
                    pieces[-1] = roman[0]
            elif prevgroup == NN:
                # Let Hepburn respell 'n' as 'm' in words such as 'shimbun'.
                try_respell = respell(pieces[-1] + roman[0])
                if try_respell[:-1] != pieces[-1]:
                    pieces[-1] = try_respell[:-1]
            pieces.append(roman)
        prevgroup = group

    romantext = ''.join(respell(piece) for piece in pieces)
    romantext = re.sub(r'[aeiou]x([aeiou])', r'\1', romantext)
    return romantext


# Hepburn romanization is the most familiar to English speakers. It involves
# respelling certain parts of romanized words to better match their
# pronunciation. For example, the name for Mount Fuji is respelled from
# "huzi-san" to "fuji-san".
HEPBURN_TABLE = {
    'si': 'shi',
    'sy': 'sh',
    'ti': 'chi',
    'ty': 'ch',
    'tu': 'tsu',
    'hu': 'fu',
    'zi': 'ji',
    'di': 'ji',
    'zy': 'j',
    'dy': 'j',
    'nm': 'mm',
    'nb': 'mb',
    'np': 'mp',
    'a_': 'aa',
    'e_': 'ee',
    'i_': 'ii',
    'o_': 'ou',
    'u_': 'uu'
}
ROMAN_PUNCTUATION_TABLE = {
    '・': '.',
    '。': '.',
    '、': ',',
    '！': '!',
    '「': '``',
    '」': "''",
    '？': '?',
    '〜': '~'
}

# Provide externally available functions.
MECAB = MeCabWrapper()

normalize = MECAB.normalize
normalize_list = MECAB.normalize_list
tokenize = MECAB.tokenize
tokenize_list = MECAB.tokenize_list
analyze = MECAB.analyze
tag_and_stem = MECAB.tag_and_stem
is_stopword = MECAB.is_stopword

########NEW FILE########
__FILENAME__ = nltk_morphy
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import nltk
from nltk.corpus import wordnet
from metanl.token_utils import untokenize, tokenize
import re

try:
    morphy = wordnet._morphy
except LookupError:
    nltk.download('wordnet')
    morphy = wordnet._morphy

STOPWORDS = ['the', 'a', 'an']

EXCEPTIONS = {
    # Avoid obsolete and obscure roots, the way lexicographers don't.
    'wrought': 'wrought',   # not 'work'
    'media': 'media',       # not 'medium'
    'installed': 'install', # not 'instal'
    'installing': 'install',# not 'instal'
    'synapses': 'synapse',  # not 'synapsis'
    'soles': 'sole',        # not 'sol'
    'pubes': 'pube',        # not 'pubis'
    'dui': 'dui',           # not 'duo'
    'taxis': 'taxi',        # not 'taxis'

    # Work around errors that Morphy makes.
    'alas': 'alas',
    'corps': 'corps',
    'cos': 'cos',
    'enured': 'enure',
    'fiver': 'fiver',
    'hinder': 'hinder',
    'lobed': 'lobe',
    'offerer': 'offerer',
    'outer': 'outer',
    'sang': 'sing',
    'singing': 'sing',
    'solderer': 'solderer',
    'tined': 'tine',
    'twiner': 'twiner',
    'us': 'us',

    # Stem common nouns whose plurals are apparently ambiguous
    'teeth': 'tooth',
    'things': 'thing',
    'people': 'person',

    # Tokenization artifacts
    'wo': 'will',
    'ca': 'can',
    "n't": 'not',
}

AMBIGUOUS_EXCEPTIONS = {
    # Avoid nouns that shadow more common verbs.
    'am': 'be',
    'as': 'as',
    'are': 'be',
    'ate': 'eat',
    'bent': 'bend',
    'drove': 'drive',
    'fell': 'fall',
    'felt': 'feel',
    'found': 'find',
    'has': 'have',
    'lit': 'light',
    'lost': 'lose',
    'sat': 'sit',
    'saw': 'see',
    'sent': 'send',
    'shook': 'shake',
    'shot': 'shoot',
    'slain': 'slay',
    'spoke': 'speak',
    'stole': 'steal',
    'sung': 'sing',
    'thought': 'think',
    'tore': 'tear',
    'was': 'be',
    'won': 'win',
    'feed': 'feed',
}


def _word_badness(word):
    """
    Assign a heuristic to possible outputs from Morphy. Minimizing this
    heuristic avoids incorrect stems.
    """
    if word.endswith('e'):
        return len(word) - 2
    elif word.endswith('ess'):
        return len(word) - 10
    elif word.endswith('ss'):
        return len(word) - 4
    else:
        return len(word)


def _morphy_best(word, pos=None):
    """
    Get the most likely stem for a word using Morphy, once the input has been
    pre-processed by morphy_stem().
    """
    results = []
    if pos is None:
        pos = 'nvar'
    for pos_item in pos:
        results.extend(morphy(word, pos_item))
    if not results:
        return None
    results.sort(key=lambda x: _word_badness(x))
    return results[0]


def morphy_stem(word, pos=None):
    """
    Get the most likely stem for a word. If a part of speech is supplied,
    the stem will be more accurate.

    Valid parts of speech are:

    - 'n' or 'NN' for nouns
    - 'v' or 'VB' for verbs
    - 'a' or 'JJ' for adjectives
    - 'r' or 'RB' for adverbs

    Any other part of speech will be treated as unknown.
    """
    word = word.lower()
    if pos is not None:
        if pos.startswith('NN'):
            pos = 'n'
        elif pos.startswith('VB'):
            pos = 'v'
        elif pos.startswith('JJ'):
            pos = 'a'
        elif pos.startswith('RB'):
            pos = 'r'
    if pos is None and word.endswith('ing') or word.endswith('ed'):
        pos = 'v'
    if pos is not None and pos not in 'nvar':
        pos = None
    if word in EXCEPTIONS:
        return EXCEPTIONS[word]
    if pos is None:
        if word in AMBIGUOUS_EXCEPTIONS:
            return AMBIGUOUS_EXCEPTIONS[word]
    return _morphy_best(word, pos) or word


def tag_and_stem(text):
    """
    Returns a list of (stem, tag, token) triples:

    - stem: the word's uninflected form
    - tag: the word's part of speech
    - token: the original word, so we can reconstruct it later
    """
    tokens = tokenize(text)
    tagged = nltk.pos_tag(tokens)
    out = []
    for token, tag in tagged:
        stem = morphy_stem(token, tag)
        out.append((stem, tag, token))
    return out


def good_lemma(lemma):
    return lemma and lemma not in STOPWORDS and lemma[0].isalnum()


def normalize_list(text):
    """
    Get a list of word stems that appear in the text. Stopwords and an initial
    'to' will be stripped, unless this leaves nothing in the stem.

    >>> normalize_list('the dog')
    ['dog']
    >>> normalize_list('big dogs')
    ['big', 'dog']
    >>> normalize_list('the')
    ['the']
    """
    pieces = [morphy_stem(word) for word in tokenize(text)]
    pieces = [piece for piece in pieces if good_lemma(piece)]
    if not pieces:
        return [text]
    if pieces[0] == 'to':
        pieces = pieces[1:]
    return pieces


def normalize(text):
    """
    Get a string made from the non-stopword word stems in the text. See
    normalize_list().
    """
    return untokenize(normalize_list(text))


def normalize_topic(topic):
    """
    Get a canonical representation of a Wikipedia topic, which may include
    a disambiguation string in parentheses.

    Returns (name, disambig), where "name" is the normalized topic name,
    and "disambig" is a string corresponding to the disambiguation text or
    None.
    """
    # find titles of the form Foo (bar)
    topic = topic.replace('_', ' ')
    match = re.match(r'([^(]+) \(([^)]+)\)', topic)
    if not match:
        return normalize(topic), None
    else:
        return normalize(match.group(1)), 'n/' + match.group(2).strip(' _')


def word_frequency(word, default_freq=0):
    raise NotImplementedError("Word frequency is now in the wordfreq package.")


def get_wordlist():
    raise NotImplementedError("Wordlists are now in the wordfreq package.")

########NEW FILE########
__FILENAME__ = token_utils
# coding: utf-8
from __future__ import unicode_literals
"""
This file contains some generally useful operations you would perform to
separate and join tokens. The tools apply most to English, but should also
be able to do their job in any Western language that uses spaces.
"""

import re
import unicodedata


def tokenize(text):
    """
    Split a text into tokens (words, morphemes we can separate such as
    "n't", and punctuation).
    """
    return list(_tokenize_gen(text))


def _tokenize_gen(text):
    import nltk
    for sent in nltk.sent_tokenize(text):
        for word in nltk.word_tokenize(sent):
            yield word


def untokenize(words):
    """
    Untokenizing a text undoes the tokenizing operation, restoring
    punctuation and spaces to the places that people expect them to be.

    Ideally, `untokenize(tokenize(text))` should be identical to `text`,
    except for line breaks.
    """
    text = ' '.join(words)
    step1 = text.replace("`` ", '"').replace(" ''", '"').replace('. . .', '...')
    step2 = step1.replace(" ( ", " (").replace(" ) ", ") ")
    step3 = re.sub(r' ([.,:;?!%]+)([ \'"`])', r"\1\2", step2)
    step4 = re.sub(r' ([.,:;?!%]+)$', r"\1", step3)
    step5 = step4.replace(" '", "'").replace(" n't", "n't").replace(
        "can not", "cannot")
    step6 = step5.replace(" ` ", " '")
    return step6.strip()


# This expression scans through a reversed string to find segments of
# camel-cased text. Comments show what these mean, forwards, in preference
# order:
CAMEL_RE = re.compile(r"""
    ^( [A-Z]+                 # A string of all caps, such as an acronym
     | [^A-Z0-9 _]+[A-Z _]    # A single capital letter followed by lowercase
                              #   letters, or lowercase letters on their own
                              #   after a word break
     | [^A-Z0-9 _]*[0-9.]+    # A number, possibly followed by lowercase
                              #   letters
     | [ _]+                  # Extra word breaks (spaces or underscores)
     | [^A-Z0-9]*[^A-Z0-9_ ]+ # Miscellaneous symbols, possibly with lowercase
                              #   letters after them
     )
""", re.VERBOSE)


def un_camel_case(text):
    r"""
    Splits apart words that are written in CamelCase.

    Bugs:

    - Non-ASCII characters are treated as lowercase letters, even if they are
      actually capital letters.

    Examples:

    >>> un_camel_case('1984ZXSpectrumGames')
    '1984 ZX Spectrum Games'

    >>> un_camel_case('aaAa aaAaA 0aA  AAAa!AAA')
    'aa Aa aa Aa A 0a A AA Aa! AAA'

    >>> un_camel_case('MotörHead')
    'Mot\xf6r Head'

    >>> un_camel_case('MSWindows3.11ForWorkgroups')
    'MS Windows 3.11 For Workgroups'

    This should not significantly affect text that is not camel-cased:

    >>> un_camel_case('ACM_Computing_Classification_System')
    'ACM Computing Classification System'

    >>> un_camel_case('Anne_Blunt,_15th_Baroness_Wentworth')
    'Anne Blunt, 15th Baroness Wentworth'

    >>> un_camel_case('Hindi-Urdu')
    'Hindi-Urdu'
    """
    revtext = text[::-1]
    pieces = []
    while revtext:
        match = CAMEL_RE.match(revtext)
        if match:
            pieces.append(match.group(1))
            revtext = revtext[match.end():]
        else:
            pieces.append(revtext)
            revtext = ''
    revstr = ' '.join(piece.strip(' _') for piece in pieces
                      if piece.strip(' _'))
    return revstr[::-1].replace('- ', '-')


# see http://www.fileformat.info/info/unicode/category/index.htm
BOUNDARY_CATEGORIES = {'Cc',  # control characters
                       'Cf',  # format characters
                       'Cn',  # "other, not assigned"
                       'Pc',  # connector punctuation
                       'Pd',  # dash
                       'Pe',  # close-punctuation
                       'Pf',  # final-quote
                       'Pi',  # initial-quote
                       'Po',  # other punctuation
                       'Zl',  # line separator
                       'Zp',  # paragraph separator
                       'Zs',  # space separator
                       }

def string_pieces(s, maxlen=1024):
    """
    Takes a (unicode) string and yields pieces of it that are at most `maxlen`
    characters, trying to break it at punctuation/whitespace. This is an
    important step before using a tokenizer with a maximum buffer size.
    """
    if not s:
        return
    i = 0
    while True:
        j = i + maxlen
        if j >= len(s):
            yield s[i:]
            return
        # Using "j - 1" keeps boundary characters with the left chunk
        while unicodedata.category(s[j - 1]) not in BOUNDARY_CATEGORIES:
            j -= 1
            if j == i:
                # No boundary available; oh well.
                j = i + maxlen
                break
        yield s[i:j]
        i = j


########NEW FILE########
__FILENAME__ = merge_english
from metanl.wordlist import get_wordlist, merge_lists

def merge_english():
    books = get_wordlist('en-books')
    twitter = get_wordlist('en-twitter')
    combined = merge_lists([(books, '', 1e9), (twitter, '', 1e9)])
    combined.save('multi-en.txt')
    combined.save_logarithmic('multi-en-logarithmic.txt')
    total = sum(combined.worddict.values())
    print "Average frequency:", total / len(combined.worddict)

if __name__ == '__main__':
    merge_english()

########NEW FILE########
__FILENAME__ = reformat-leeds-ja
from metanl import japanese
from metanl.leeds_corpus_reader import translate_leeds_corpus

translate_leeds_corpus('../metanl/data/source-data/internet-ja-forms.num',
    '../metanl/data/leeds-internet-ja.txt', japanese.normalize)

########NEW FILE########
__FILENAME__ = reformat_using_rosette
from metanl.leeds_corpus_reader import translate_leeds_corpus
import socket, time

def make_rosette_normalizer(lcode):
    from lumi_pipeline.text_readers import get_reader
    reader = get_reader('rosette.%s' % lcode)
    def normalizer(text):
        try:
            triples = reader.text_to_token_triples(text)
        except socket.error:
            time.sleep(1)
            print 'backing off'
            return normalizer(text)
        normalized = u' '.join(lemma.rsplit('|', 1)[0] for lemma, pos, token in triples)
        return normalized
    return normalizer

def main():
    for language in ('pt', 'ru', 'es', 'fr', 'it', 'zh', 'de', 'ar'):
        print language
        translate_leeds_corpus(
            '../metanl/data/source-data/internet-%s-forms.num' % language,
            '../metanl/data/wordlists/leeds-internet-%s.txt' % language,
            make_rosette_normalizer(language)
        )

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_extprocesses
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from metanl.freeling import english, spanish
from metanl.mecab import normalize, tag_and_stem
from metanl.extprocess import unicode_is_punctuation
from nose.tools import eq_


def test_english():
    test_text = "This is a test.\n\nIt has two paragraphs, and that's okay."
    expected_result = [('this', 'DT', 'This'), ('be', 'VBZ', 'is'),
                       ('a', 'DT', 'a'), ('test', 'NN', 'test'),
                       ('.', '.', '.'), ('it', 'PRP', 'It'),
                       ('have', 'VBZ', 'has'), ('two', 'DT', 'two'),
                       ('paragraph', 'NNS', 'paragraphs'), (',', '.', ','),
                       ('and', 'CC', 'and'), ('that', 'PRP', 'that'),
                       ('be', 'VBZ', "'s"), ('okay', 'JJ', 'okay'),
                       ('.', '.', '.')]
    eq_(english.tag_and_stem(test_text), expected_result)

    test_text = "this has\ntwo lines"
    expected_result = [('this', 'DT', 'this'), ('have', 'VBZ', 'has'),
                       ('two', 'DT', 'two'), ('line', 'NNS', 'lines')]
    eq_(english.tag_and_stem(test_text), expected_result)
        

def test_spanish():
    # Spanish works, even with a lot of unicode characters
    test_text = '¿Dónde está mi búfalo?'
    expected_result = [('¿', '.', '¿'),
                       ('dónde', 'P', 'Dónde'),
                       ('estar', 'V', 'está'),
                       ('mi', 'D', 'mi'),
                       ('búfalo', 'N', 'búfalo'),
                       ('?', '.', '?')]
    eq_(spanish.tag_and_stem(test_text), expected_result)


def test_japanese():
    eq_(normalize('これはテストです'), 'テスト')
    this_is_a_test = [('これ', '~名詞', 'これ'),
                      ('は', '~助詞', 'は'),
                      ('テスト', '名詞', 'テスト'),
                      ('です', '~助動詞', 'です'),
                      ('。', '.', '。')]
    eq_(tag_and_stem('これはテストです。'), this_is_a_test)


def test_unicode_is_punctuation():
    assert unicode_is_punctuation('word') is False
    assert unicode_is_punctuation('。') is True
    assert unicode_is_punctuation('-') is True
    assert unicode_is_punctuation('-3') is False
    assert unicode_is_punctuation('あ') is False

########NEW FILE########
__FILENAME__ = test_nltk_morphy
from __future__ import unicode_literals

from metanl.nltk_morphy import normalize_list, tag_and_stem
from nose.tools import eq_

def test_normalize_list():
    # Strip away articles, unless there's only an article
    eq_(normalize_list('the dog'), ['dog'])
    eq_(normalize_list('the'), ['the'])

    # strip out pluralization
    eq_(normalize_list('big dogs'), ['big', 'dog'])


def test_tag_and_stem():
    the_big_dogs = [(u'the', 'DT', u'the'),
                    (u'big', 'JJ', u'big'),
                    (u'dog', 'NNS', u'dogs')]
    eq_(tag_and_stem('the big dogs'), the_big_dogs)

    the_big_hashtag = [(u'the', 'DT', u'the'),
                       (u'#', 'NN', u'#'),
                       (u'big', 'JJ', u'big'),
                       (u'dog', 'NN', u'dog')]
    eq_(tag_and_stem('the #big dog'), the_big_hashtag)

    two_sentences = [(u'i', 'PRP', u'I'),
                     (u'can', 'MD', u'ca'),
                     (u'not', 'RB', u"n't"),
                     (u'.', '.', u'.'),
                     (u'avoid', 'NNP', u'Avoid'),
                     (u'fragment', 'NNS', u'fragments'),
                     (u'.', '.', u'.')]
    eq_(tag_and_stem("I can't. Avoid fragments."), two_sentences)

########NEW FILE########
__FILENAME__ = test_tokens
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from metanl.token_utils import (tokenize, untokenize, un_camel_case,
                                string_pieces)
from nose.tools import eq_
import nltk

def test_tokenize():
    # a snippet from Hitchhiker's Guide that just happens to have
    # most of the examples of punctuation we're looking for.
    #
    # TODO: test wacky behavior with "n't" and "cannot" and stuff.
    text1 = "Time is an illusion. Lunchtime, doubly so."
    text2 = ('"Very deep," said Arthur, "you should send that in to the '
             'Reader\'s Digest. They\'ve got a page for people like you."')
    eq_(tokenize(text1),
        ['Time', 'is', 'an', 'illusion', '.', 'Lunchtime', ',',
         'doubly', 'so', '.']
    )
    eq_(untokenize(tokenize(text1)), text1)
    if nltk.__version__ >= '3':
        eq_(untokenize(tokenize(text2)), text2)

def test_camel_case():
    eq_(un_camel_case('1984ZXSpectrumGames'), '1984 ZX Spectrum Games')
    eq_(un_camel_case('aaAa aaAaA 0aA AAAa!AAA'),
        'aa Aa aa Aa A 0a A AA Aa! AAA')
    eq_(un_camel_case('MotörHead'),
        'Mot\xf6r Head')
    eq_(un_camel_case('MSWindows3.11ForWorkgroups'),
        'MS Windows 3.11 For Workgroups')

    # This should not significantly affect text that is not camel-cased
    eq_(un_camel_case('ACM_Computing_Classification_System'),
        'ACM Computing Classification System')
    eq_(un_camel_case('Anne_Blunt,_15th_Baroness_Wentworth'),
        'Anne Blunt, 15th Baroness Wentworth')
    eq_(un_camel_case('Hindi-Urdu'),
        'Hindi-Urdu')


def test_string_pieces():
    # Break as close to whitespace as possible
    text = "12 12 12345 123456 1234567-12345678"
    eq_(list(string_pieces(text, 6)),
        ['12 12 ', '12345 ', '123456', ' ', '123456', '7-', '123456', '78'])

########NEW FILE########
