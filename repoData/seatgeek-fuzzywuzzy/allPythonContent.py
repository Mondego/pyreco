__FILENAME__ = benchmarks
# -*- coding: utf8 -*-

from timeit import timeit
import math

iterations = 100000

cirque_strings = [
    "cirque du soleil - zarkana - las vegas",
    "cirque du soleil ",
    "cirque du soleil las vegas",
    "zarkana las vegas",
    "las vegas cirque du soleil at the bellagio",
    "zarakana - cirque du soleil - bellagio"
]

choices = [
    "",
    "new york yankees vs boston red sox",
    "",
    "zarakana - cirque du soleil - bellagio",
    None,
    "cirque du soleil las vegas",
    None
]

mixed_strings = [
    "Lorem Ipsum is simply dummy text of the printing and typesetting industry.",
    "C\\'est la vie",
    u"Ça va?",
    u"Cães danados",
    u"\xacCamarões assados",
    u"a\xac\u1234\u20ac\U00008000"
]

common_setup = "from fuzzywuzzy import fuzz, utils; "
basic_setup = "from fuzzywuzzy.string_processing import StringProcessor;"


def print_result_from_timeit(stmt='pass', setup='pass', number=1000000):
    """
    Clean function to know how much time took the execution of one statement
    """
    units = ["s", "ms", "us", "ns"]
    duration = timeit(stmt, setup, number=number)
    avg_duration = duration / float(number)
    thousands = int(math.floor(math.log(avg_duration, 1000)))

    print "Total time: %fs. Average run: %.3f%s." \
        % (duration, avg_duration * (1000 ** -thousands), units[-thousands])

for s in choices:
    print 'Test validate_string for: "%s"' % s
    print_result_from_timeit('utils.validate_string(\'%s\')' % s, common_setup, number=iterations)

print

for s in mixed_strings + cirque_strings + choices:
    print 'Test full_process for: "%s"' % s
    print_result_from_timeit('utils.full_process(u\'%s\')' % s,
                             common_setup + basic_setup, number=iterations)

### benchmarking the core matching methods...

for s in cirque_strings:
    print 'Test fuzz.ratio for string: "%s"' % s
    print '-------------------------------'
    print_result_from_timeit('fuzz.ratio(u\'cirque du soleil\', u\'%s\')' % s,
                             common_setup + basic_setup, number=iterations / 100)

for s in cirque_strings:
    print 'Test fuzz.partial_ratio for string: "%s"' % s
    print '-------------------------------'
    print_result_from_timeit('fuzz.partial_ratio(u\'cirque du soleil\', u\'%s\')'
                             % s, common_setup + basic_setup, number=iterations / 100)

for s in cirque_strings:
    print 'Test fuzz.WRatio for string: "%s"' % s
    print '-------------------------------'
    print_result_from_timeit('fuzz.WRatio(u\'cirque du soleil\', u\'%s\')' % s,
                             common_setup + basic_setup, number=iterations / 100)

########NEW FILE########
__FILENAME__ = fuzz
#!/usr/bin/env python
# encoding: utf-8
"""
fuzz.py

Copyright (c) 2011 Adam Cohen

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from __future__ import unicode_literals

try:
    from StringMatcher import StringMatcher as SequenceMatcher
except:
    from difflib import SequenceMatcher

from . import utils


###########################
# Basic Scoring Functions #
###########################


def ratio(s1, s2):

    if s1 is None:
        raise TypeError("s1 is None")
    if s2 is None:
        raise TypeError("s2 is None")
    s1, s2 = utils.make_type_consistent(s1, s2)
    if len(s1) == 0 or len(s2) == 0:
        return 0

    m = SequenceMatcher(None, s1, s2)
    return utils.intr(100 * m.ratio())


# todo: skip duplicate indexes for a little more speed
def partial_ratio(s1, s2):

    if s1 is None:
        raise TypeError("s1 is None")
    if s2 is None:
        raise TypeError("s2 is None")
    s1, s2 = utils.make_type_consistent(s1, s2)
    if len(s1) == 0 or len(s2) == 0:
        return 0

    if len(s1) <= len(s2):
        shorter = s1
        longer = s2
    else:
        shorter = s2
        longer = s1

    m = SequenceMatcher(None, shorter, longer)
    blocks = m.get_matching_blocks()

    # each block represents a sequence of matching characters in a string
    # of the form (idx_1, idx_2, len)
    # the best partial match will block align with at least one of those blocks
    #   e.g. shorter = "abcd", longer = XXXbcdeEEE
    #   block = (1,3,3)
    #   best score === ratio("abcd", "Xbcd")
    scores = []
    for block in blocks:
        long_start = block[1] - block[0] if (block[1] - block[0]) > 0 else 0
        long_end = long_start + len(shorter)
        long_substr = longer[long_start:long_end]

        m2 = SequenceMatcher(None, shorter, long_substr)
        r = m2.ratio()
        if r > .995:
            return 100
        else:
            scores.append(r)

    return int(100 * max(scores))


##############################
# Advanced Scoring Functions #
##############################

# Sorted Token
#   find all alphanumeric tokens in the string
#   sort those tokens and take ratio of resulting joined strings
#   controls for unordered string elements
def _token_sort(s1, s2, partial=True, force_ascii=True):

    if s1 is None:
        raise TypeError("s1 is None")
    if s2 is None:
        raise TypeError("s2 is None")

    # pull tokens
    tokens1 = utils.full_process(s1, force_ascii=force_ascii).split()
    tokens2 = utils.full_process(s2, force_ascii=force_ascii).split()

    # sort tokens and join
    sorted1 = " ".join(sorted(tokens1))
    sorted2 = " ".join(sorted(tokens2))

    sorted1 = sorted1.strip()
    sorted2 = sorted2.strip()

    if partial:
        return partial_ratio(sorted1, sorted2)
    else:
        return ratio(sorted1, sorted2)


def token_sort_ratio(s1, s2, force_ascii=True):
    return _token_sort(s1, s2, partial=False, force_ascii=force_ascii)


def partial_token_sort_ratio(s1, s2, force_ascii=True):
    return _token_sort(s1, s2, partial=True, force_ascii=force_ascii)


# Token Set
#   find all alphanumeric tokens in each string...treat them as a set
#   construct two strings of the form
#       <sorted_intersection><sorted_remainder>
#   take ratios of those two strings
#   controls for unordered partial matches
def _token_set(s1, s2, partial=True, force_ascii=True):

    if s1 is None:
        raise TypeError("s1 is None")
    if s2 is None:
        raise TypeError("s2 is None")

    p1 = utils.full_process(s1, force_ascii=force_ascii)
    p2 = utils.full_process(s2, force_ascii=force_ascii)

    if not utils.validate_string(p1):
        return 0
    if not utils.validate_string(p2):
        return 0

    # pull tokens
    tokens1 = set(utils.full_process(p1).split())
    tokens2 = set(utils.full_process(p2).split())

    intersection = tokens1.intersection(tokens2)
    diff1to2 = tokens1.difference(tokens2)
    diff2to1 = tokens2.difference(tokens1)

    sorted_sect = " ".join(sorted(intersection))
    sorted_1to2 = " ".join(sorted(diff1to2))
    sorted_2to1 = " ".join(sorted(diff2to1))

    combined_1to2 = sorted_sect + " " + sorted_1to2
    combined_2to1 = sorted_sect + " " + sorted_2to1

    # strip
    sorted_sect = sorted_sect.strip()
    combined_1to2 = combined_1to2.strip()
    combined_2to1 = combined_2to1.strip()

    pairwise = [
        ratio(sorted_sect, combined_1to2),
        ratio(sorted_sect, combined_2to1),
        ratio(combined_1to2, combined_2to1)
    ]
    return max(pairwise)


def token_set_ratio(s1, s2, force_ascii=True):
    return _token_set(s1, s2, partial=False, force_ascii=force_ascii)


def partial_token_set_ratio(s1, s2, force_ascii=True):
    return _token_set(s1, s2, partial=True, force_ascii=force_ascii)


# TODO: numerics

###################
# Combination API #
###################

# q is for quick
def QRatio(s1, s2, force_ascii=True):

    p1 = utils.full_process(s1, force_ascii=force_ascii)
    p2 = utils.full_process(s2, force_ascii=force_ascii)

    if not utils.validate_string(p1):
        return 0
    if not utils.validate_string(p2):
        return 0

    return ratio(p1, p2)


def UQRatio(s1, s2):
    return QRatio(s1, s2, force_ascii=False)


# w is for weighted
def WRatio(s1, s2, force_ascii=True):

    p1 = utils.full_process(s1, force_ascii=force_ascii)
    p2 = utils.full_process(s2, force_ascii=force_ascii)

    if not utils.validate_string(p1):
        return 0
    if not utils.validate_string(p2):
        return 0

    # should we look at partials?
    try_partial = True
    unbase_scale = .95
    partial_scale = .90

    base = ratio(p1, p2)
    len_ratio = float(max(len(p1), len(p2))) / min(len(p1), len(p2))

    # if strings are similar length, don't use partials
    if len_ratio < 1.5:
        try_partial = False

    # if one string is much much shorter than the other
    if len_ratio > 8:
        partial_scale = .6

    if try_partial:
        partial = partial_ratio(p1, p2) * partial_scale
        ptsor = partial_token_sort_ratio(p1, p2, force_ascii=force_ascii) \
            * unbase_scale * partial_scale
        ptser = partial_token_set_ratio(p1, p2, force_ascii=force_ascii) \
            * unbase_scale * partial_scale

        return int(max(base, partial, ptsor, ptser))
    else:
        tsor = token_sort_ratio(p1, p2, force_ascii=force_ascii) * unbase_scale
        tser = token_set_ratio(p1, p2, force_ascii=force_ascii) * unbase_scale

        return int(max(base, tsor, tser))


def UWRatio(s1, s2):
    return WRatio(s1, s2, force_ascii=False)

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
# encoding: utf-8
"""
process.py

Copyright (c) 2011 Adam Cohen

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import itertools

from . import fuzz
from . import utils


def extract(query, choices, processor=None, scorer=None, limit=5):
    """Find best matches in a list of choices, return a list of tuples
       containing the match and it's score.

    Arguments:
        query       -- an object representing the thing we want to find
        choices     -- a list of objects we are attempting to extract
                       values from
        scorer      -- f(OBJ, QUERY) --> INT. We will return the objects
                       with the highest score by default, we use
                       score.WRatio() and both OBJ and QUERY should be
                       strings
        processor   -- f(OBJ_A) --> OBJ_B, where the output is an input
                       to scorer for example, "processor = lambda x:
                       x[0]" would return the first element in a
                       collection x (of, say, strings) this would then
                       be used in the scoring collection by default, we
                       use utils.full_process()

    """
    if choices is None or len(choices) == 0:
        return []

    # default, turn whatever the choice is into a workable string
    if processor is None:
        processor = lambda x: utils.full_process(x)

    # default: wratio
    if scorer is None:
        scorer = fuzz.WRatio

    sl = list()

    for choice in choices:
        processed = processor(choice)
        score = scorer(query, processed)
        tuple = (choice, score)
        sl.append(tuple)

    sl.sort(key=lambda i: i[1], reverse=True)
    return sl[:limit]


def extractBests(query, choices, processor=None, scorer=None, score_cutoff=0, limit=5):
    """Find best matches above a score in a list of choices, return a
    list of tuples containing the match and it's score.

    Convenience method which returns the choices with best scores, see
    extract() for full arguments list

    Optional parameter: score_cutoff.
        If the choice has a score of less than or equal to score_cutoff
        it will not be included on result list

    """

    best_list = extract(query, choices, processor, scorer, limit)
    if len(best_list) > 0:
        return list(itertools.takewhile(lambda x: x[1] > score_cutoff, best_list))
    else:
        return []


def extractOne(query, choices, processor=None, scorer=None, score_cutoff=0):
    """Find the best match above a score in a list of choices, return a
    tuple containing the match and it's score if it's above the treshold
    or None.

    Convenience method which returns the single best choice, see
    extract() for full arguments list

    Optional parameter: score_cutoff.
        If the best choice has a score of less than or equal to
        score_cutoff we will return none (intuition: not a good enough
        match)

    """

    best_list = extract(query, choices, processor, scorer, limit=1)
    if len(best_list) > 0:
        best = best_list[0]
        if best[1] > score_cutoff:
            return best
        else:
            return None
    else:
        return None

########NEW FILE########
__FILENAME__ = StringMatcher
#!/usr/bin/env python
# encoding: utf-8
"""
StringMatcher.py

ported from python-Levenshtein
[https://github.com/miohtama/python-Levenshtein]
"""

from Levenshtein import *
from warnings import warn

class StringMatcher:
    """A SequenceMatcher-like class built on the top of Levenshtein"""

    def _reset_cache(self):
        self._ratio = self._distance = None
        self._opcodes = self._editops = self._matching_blocks = None

    def __init__(self, isjunk=None, seq1='', seq2=''):
        if isjunk:
            warn("isjunk not NOT implemented, it will be ignored")
        self._str1, self._str2 = seq1, seq2
        self._reset_cache()

    def set_seqs(self, seq1, seq2):
        self._str1, self._str2 = seq1, seq2
        self._reset_cache()

    def set_seq1(self, seq1):
        self._str1 = seq1
        self._reset_cache()

    def set_seq2(self, seq2):
        self._str2 = seq2
        self._reset_cache()

    def get_opcodes(self):
        if not self._opcodes:
            if self._editops:
                self._opcodes = opcodes(self._editops, self._str1, self._str2)
            else:
                self._opcodes = opcodes(self._str1, self._str2)
        return self._opcodes

    def get_editops(self):
        if not self._editops:
            if self._opcodes:
                self._editops = editops(self._opcodes, self._str1, self._str2)
            else:
                self._editops = editops(self._str1, self._str2)
        return self._editops

    def get_matching_blocks(self):
        if not self._matching_blocks:
            self._matching_blocks = matching_blocks(self.get_opcodes(),
                                                    self._str1, self._str2)
        return self._matching_blocks

    def ratio(self):
        if not self._ratio:
            self._ratio = ratio(self._str1, self._str2)
        return self._ratio

    def quick_ratio(self):
        # This is usually quick enough :o)
        if not self._ratio:
            self._ratio = ratio(self._str1, self._str2)
        return self._ratio

    def real_quick_ratio(self):
        len1, len2 = len(self._str1), len(self._str2)
        return 2.0 * min(len1, len2) / (len1 + len2)

    def distance(self):
        if not self._distance:
            self._distance = distance(self._str1, self._str2)
        return self._distance
########NEW FILE########
__FILENAME__ = string_processing
from __future__ import unicode_literals
import re


class StringProcessor(object):
    """
    This class defines method to process strings in the most
    efficient way. Ideally all the methods below use unicode strings
    for both input and output.
    """

    @classmethod
    def replace_non_letters_non_numbers_with_whitespace(cls, a_string):
        """
        This function replaces any sequence of non letters and non
        numbers with a single white space.
        """
        regex = re.compile(r"(?ui)\W")
        return regex.sub(" ", a_string)

    @classmethod
    def strip(cls, a_string):
        """
        This function strips leading and trailing white space.
        """

        return a_string.strip()

    @classmethod
    def to_lower_case(cls, a_string):
        """
        This function returns the lower-cased version of the string given.
        """
        return a_string.lower()

    @classmethod
    def to_upper_case(cls, a_string):
        """
        This function returns the upper-cased version of the string given.
        """
        return a_string.upper()

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
import sys

from fuzzywuzzy.string_processing import StringProcessor


PY3 = sys.version_info[0] == 3


def validate_string(s):
    try:
        if len(s) > 0:
            return True
        else:
            return False
    except:
        return False

bad_chars = str('')  # ascii dammit!
for i in range(128, 256):
    bad_chars += chr(i)
if PY3:
    translation_table = dict((ord(c), None) for c in bad_chars)


def asciionly(s):
    if PY3:
        return s.translate(translation_table)
    else:
        return s.translate(None, bad_chars)


def asciidammit(s):
    if type(s) is str:
        return asciionly(s)
    elif type(s) is unicode:
        return asciionly(s.encode('ascii', 'ignore'))
    else:
        return asciidammit(unicode(s))


def make_type_consistent(s1, s2):
    if isinstance(s1, str) and isinstance(s2, str):
        return s1, s2

    elif isinstance(s1, unicode) and isinstance(s2, unicode):
        return s1, s2

    else:
        return unicode(s1), unicode(s2)


def full_process(s, force_ascii=False):
    """Process string by
        -- removing all but letters and numbers
        -- trim whitespace
        -- force to lower case
        if force_ascii == True, force convert to ascii"""

    if s is None:
        return ""

    if force_ascii:
        s = asciidammit(s)
    # Keep only Letters and Numbres (see Unicode docs).
    string_out = StringProcessor.replace_non_letters_non_numbers_with_whitespace(s)
    # Force into lowercase.
    string_out = StringProcessor.to_lower_case(string_out)
    # Remove leading and trailing whitespaces.
    string_out = StringProcessor.strip(string_out)
    return string_out


def intr(n):
    '''Returns a correctly rounded integer'''
    return int(round(n))

########NEW FILE########
__FILENAME__ = test_fuzzywuzzy
# -*- coding: utf8 -*-
from __future__ import unicode_literals
import unittest
import re
import sys

from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from fuzzywuzzy import utils
from fuzzywuzzy.string_processing import StringProcessor

if sys.version_info[0] == 3:
    unicode = str

if sys.version_info[:2] == (2, 6):
    # Monkeypatch to make tests work on 2.6
    def assertLess(first, second, msg=None):
        assert first > second
    unittest.TestCase.assertLess = assertLess


class StringProcessingTest(unittest.TestCase):
    def test_replace_non_letters_non_numbers_with_whitespace(self):
        strings = ["new york mets - atlanta braves", "Cães danados",
                   "New York //// Mets $$$", "Ça va?"]
        for string in strings:
            proc_string = StringProcessor.replace_non_letters_non_numbers_with_whitespace(string)
            regex = re.compile(r"(?ui)[\W]")
            for expr in regex.finditer(proc_string):
                self.assertEquals(expr.group(), " ")

    def test_dont_condense_whitespace(self):
        s1 = "new york mets - atlanta braves"
        s2 = "new york mets atlanta braves"
        p1 = StringProcessor.replace_non_letters_non_numbers_with_whitespace(s1)
        p2 = StringProcessor.replace_non_letters_non_numbers_with_whitespace(s2)
        self.assertNotEqual(p1, p2)


class UtilsTest(unittest.TestCase):
    def setUp(self):
        self.s1 = "new york mets"
        self.s1a = "new york mets"
        self.s2 = "new YORK mets"
        self.s3 = "the wonderful new york mets"
        self.s4 = "new york mets vs atlanta braves"
        self.s5 = "atlanta braves vs new york mets"
        self.s6 = "new york mets - atlanta braves"
        self.mixed_strings = [
            "Lorem Ipsum is simply dummy text of the printing and typesetting industry.",
            "C'est la vie",
            "Ça va?",
            "Cães danados",
            "\xacCamarões assados",
            "a\xac\u1234\u20ac\U00008000",
            "\u00C1"
        ]

    def tearDown(self):
        pass

    def test_asciidammit(self):
        for s in self.mixed_strings:
            utils.asciidammit(s)

    def test_asciionly(self):
        for s in self.mixed_strings:
            # ascii only only runs on strings
            s = utils.asciidammit(s)
            utils.asciionly(s)

    def test_fullProcess(self):
        for s in self.mixed_strings:
            utils.full_process(s)

    def test_fullProcessForceAscii(self):
        for s in self.mixed_strings:
            utils.full_process(s, force_ascii=True)


class RatioTest(unittest.TestCase):

    def setUp(self):
        self.s1 = "new york mets"
        self.s1a = "new york mets"
        self.s2 = "new YORK mets"
        self.s3 = "the wonderful new york mets"
        self.s4 = "new york mets vs atlanta braves"
        self.s5 = "atlanta braves vs new york mets"
        self.s6 = "new york mets - atlanta braves"

        self.cirque_strings = [
            "cirque du soleil - zarkana - las vegas",
            "cirque du soleil ",
            "cirque du soleil las vegas",
            "zarkana las vegas",
            "las vegas cirque du soleil at the bellagio",
            "zarakana - cirque du soleil - bellagio"
        ]

        self.baseball_strings = [
            "new york mets vs chicago cubs",
            "chicago cubs vs chicago white sox",
            "philladelphia phillies vs atlanta braves",
            "braves vs mets",
        ]

    def tearDown(self):
        pass

    def testEqual(self):
        self.assertEqual(fuzz.ratio(self.s1, self.s1a), 100)

    def testCaseInsensitive(self):
        self.assertNotEqual(fuzz.ratio(self.s1, self.s2), 100)
        self.assertEqual(fuzz.ratio(utils.full_process(self.s1), utils.full_process(self.s2)), 100)

    def testPartialRatio(self):
        self.assertEqual(fuzz.partial_ratio(self.s1, self.s3), 100)

    def testTokenSortRatio(self):
        self.assertEqual(fuzz.token_sort_ratio(self.s1, self.s1a), 100)

    def testPartialTokenSortRatio(self):
        self.assertEqual(fuzz.partial_token_sort_ratio(self.s1, self.s1a), 100)
        self.assertEqual(fuzz.partial_token_sort_ratio(self.s4, self.s5), 100)

    def testTokenSetRatio(self):
        self.assertEqual(fuzz.token_set_ratio(self.s4, self.s5), 100)

    def testPartialTokenSetRatio(self):
        self.assertEqual(fuzz.token_set_ratio(self.s4, self.s5), 100)

    def testQuickRatioEqual(self):
        self.assertEqual(fuzz.QRatio(self.s1, self.s1a), 100)

    def testQuickRatioCaseInsensitive(self):
        self.assertEqual(fuzz.QRatio(self.s1, self.s2), 100)

    def testQuickRatioNotEqual(self):
        self.assertNotEqual(fuzz.QRatio(self.s1, self.s3), 100)

    def testWRatioEqual(self):
        self.assertEqual(fuzz.WRatio(self.s1, self.s1a), 100)

    def testWRatioCaseInsensitive(self):
        self.assertEqual(fuzz.WRatio(self.s1, self.s2), 100)

    def testWRatioPartialMatch(self):
        # a partial match is scaled by .9
        self.assertEqual(fuzz.WRatio(self.s1, self.s3), 90)

    def testWRatioMisorderedMatch(self):
        # misordered full matches are scaled by .95
        self.assertEqual(fuzz.WRatio(self.s4, self.s5), 95)

    def testWRatioUnicode(self):
        self.assertEqual(fuzz.WRatio(unicode(self.s1), unicode(self.s1a)), 100)

    def testQRatioUnicode(self):
        self.assertEqual(fuzz.WRatio(unicode(self.s1), unicode(self.s1a)), 100)

    def testEmptyStringsScore0(self):
        self.assertEqual(fuzz.ratio("", ""), 0)
        self.assertEqual(fuzz.partial_ratio("", ""), 0)

    def testIssueSeven(self):
        s1 = "HSINCHUANG"
        s2 = "SINJHUAN"
        s3 = "LSINJHUANG DISTRIC"
        s4 = "SINJHUANG DISTRICT"

        self.assertTrue(fuzz.partial_ratio(s1, s2) > 75)
        self.assertTrue(fuzz.partial_ratio(s1, s3) > 75)
        self.assertTrue(fuzz.partial_ratio(s1, s4) > 75)

    def testRatioUnicodeString(self):
        s1 = "\u00C1"
        s2 = "ABCD"
        score = fuzz.ratio(s1, s2)
        self.assertEqual(0, score)

    def testPartialRatioUnicodeString(self):
        s1 = "\u00C1"
        s2 = "ABCD"
        score = fuzz.partial_ratio(s1, s2)
        self.assertEqual(0, score)

    def testWRatioUnicodeString(self):
        s1 = "\u00C1"
        s2 = "ABCD"
        score = fuzz.WRatio(s1, s2)
        self.assertEqual(0, score)

        # Cyrillic.
        s1 = "\u043f\u0441\u0438\u0445\u043e\u043b\u043e\u0433"
        s2 = "\u043f\u0441\u0438\u0445\u043e\u0442\u0435\u0440\u0430\u043f\u0435\u0432\u0442"
        score = fuzz.WRatio(s1, s2, force_ascii=False)
        self.assertNotEqual(0, score)

        # Chinese.
        s1 = "\u6211\u4e86\u89e3\u6570\u5b66"
        s2 = "\u6211\u5b66\u6570\u5b66"
        score = fuzz.WRatio(s1, s2, force_ascii=False)
        self.assertNotEqual(0, score)

    def testQRatioUnicodeString(self):
        s1 = "\u00C1"
        s2 = "ABCD"
        score = fuzz.QRatio(s1, s2)
        self.assertEqual(0, score)

        # Cyrillic.
        s1 = "\u043f\u0441\u0438\u0445\u043e\u043b\u043e\u0433"
        s2 = "\u043f\u0441\u0438\u0445\u043e\u0442\u0435\u0440\u0430\u043f\u0435\u0432\u0442"
        score = fuzz.QRatio(s1, s2, force_ascii=False)
        self.assertNotEqual(0, score)

        # Chinese.
        s1 = "\u6211\u4e86\u89e3\u6570\u5b66"
        s2 = "\u6211\u5b66\u6570\u5b66"
        score = fuzz.QRatio(s1, s2, force_ascii=False)
        self.assertNotEqual(0, score)

    def testQratioForceAscii(self):
        s1 = "ABCD\u00C1"
        s2 = "ABCD"

        score = fuzz.QRatio(s1, s2, force_ascii=True)
        self.assertEqual(score, 100)

        score = fuzz.QRatio(s1, s2, force_ascii=False)
        self.assertLess(score, 100)

    def testQRatioForceAscii(self):
        s1 = "ABCD\u00C1"
        s2 = "ABCD"

        score = fuzz.WRatio(s1, s2, force_ascii=True)
        self.assertEqual(score, 100)

        score = fuzz.WRatio(s1, s2, force_ascii=False)
        self.assertLess(score, 100)

    def testTokenSetForceAscii(self):
        s1 = "ABCD\u00C1 HELP\u00C1"
        s2 = "ABCD HELP"

        score = fuzz._token_set(s1, s2, force_ascii=True)
        self.assertEqual(score, 100)

        score = fuzz._token_set(s1, s2, force_ascii=False)
        self.assertLess(score, 100)

    def testTokenSortForceAscii(self):
        s1 = "ABCD\u00C1 HELP\u00C1"
        s2 = "ABCD HELP"

        score = fuzz._token_sort(s1, s2, force_ascii=True)
        self.assertEqual(score, 100)

        score = fuzz._token_sort(s1, s2, force_ascii=False)
        self.assertLess(score, 100)

    # test processing methods
    def testGetBestChoice1(self):
        query = "new york mets at atlanta braves"
        best = process.extractOne(query, self.baseball_strings)
        self.assertEqual(best[0], "braves vs mets")

    def testGetBestChoice2(self):
        query = "philadelphia phillies at atlanta braves"
        best = process.extractOne(query, self.baseball_strings)
        self.assertEqual(best[0], self.baseball_strings[2])

    def testGetBestChoice3(self):
        query = "atlanta braves at philadelphia phillies"
        best = process.extractOne(query, self.baseball_strings)
        self.assertEqual(best[0], self.baseball_strings[2])

    def testGetBestChoice4(self):
        query = "chicago cubs vs new york mets"
        best = process.extractOne(query, self.baseball_strings)
        self.assertEqual(best[0], self.baseball_strings[0])


class ProcessTest(unittest.TestCase):

    def setUp(self):
        self.s1 = "new york mets"
        self.s1a = "new york mets"
        self.s2 = "new YORK mets"
        self.s3 = "the wonderful new york mets"
        self.s4 = "new york mets vs atlanta braves"
        self.s5 = "atlanta braves vs new york mets"
        self.s6 = "new york mets - atlanta braves"

        self.cirque_strings = [
            "cirque du soleil - zarkana - las vegas",
            "cirque du soleil ",
            "cirque du soleil las vegas",
            "zarkana las vegas",
            "las vegas cirque du soleil at the bellagio",
            "zarakana - cirque du soleil - bellagio"
        ]

        self.baseball_strings = [
            "new york mets vs chicago cubs",
            "chicago cubs vs chicago white sox",
            "philladelphia phillies vs atlanta braves",
            "braves vs mets",
        ]

    def testWithProcessor(self):
        events = [
            ["chicago cubs vs new york mets", "CitiField", "2011-05-11", "8pm"],
            ["new york yankees vs boston red sox", "Fenway Park", "2011-05-11", "8pm"],
            ["atlanta braves vs pittsburgh pirates", "PNC Park", "2011-05-11", "8pm"],
        ]
        query = "new york mets vs chicago cubs"
        processor = lambda event: event[0]

        best = process.extractOne(query, events, processor=processor)
        self.assertEqual(best[0], events[0])

    def testWithScorer(self):
        choices = [
            "new york mets vs chicago cubs",
            "chicago cubs at new york mets",
            "atlanta braves vs pittsbugh pirates",
            "new york yankees vs boston red sox"
        ]

        # in this hypothetical example we care about ordering, so we use quick ratio
        query = "new york mets at chicago cubs"
        scorer = fuzz.QRatio

        # first, as an example, the normal way would select the "more
        # 'complete' match of choices[1]"

        best = process.extractOne(query, choices)
        self.assertEqual(best[0], choices[1])

        # now, use the custom scorer

        best = process.extractOne(query, choices, scorer=scorer)
        self.assertEqual(best[0], choices[0])

    def testWithCutoff(self):
        choices = [
            "new york mets vs chicago cubs",
            "chicago cubs at new york mets",
            "atlanta braves vs pittsbugh pirates",
            "new york yankees vs boston red sox"
        ]

        query = "los angeles dodgers vs san francisco giants"

        # in this situation, this is an event that does not exist in the list
        # we don't want to randomly match to something, so we use a reasonable cutoff

        best = process.extractOne(query, choices, score_cutoff=50)
        self.assertTrue(best is None)
        #self.assertIsNone(best) # unittest.TestCase did not have assertIsNone until Python 2.7

        # however if we had no cutoff, something would get returned

        #best = process.extractOne(query, choices)
        #self.assertIsNotNone(best)

    def testEmptyStrings(self):
        choices = [
            "",
            "new york mets vs chicago cubs",
            "new york yankees vs boston red sox",
            "",
            ""
        ]

        query = "new york mets at chicago cubs"

        best = process.extractOne(query, choices)
        self.assertEqual(best[0], choices[1])

    def testNullStrings(self):
        choices = [
            None,
            "new york mets vs chicago cubs",
            "new york yankees vs boston red sox",
            None,
            None
        ]

        query = "new york mets at chicago cubs"

        best = process.extractOne(query, choices)
        self.assertEqual(best[0], choices[1])


if __name__ == '__main__':
    unittest.main()         # run all tests

########NEW FILE########
