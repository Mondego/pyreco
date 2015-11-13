__FILENAME__ = typogrify_tags
import re
import calendar
from datetime import date, timedelta
import smartypants as _smartypants

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.utils.translation import ungettext, ugettext
from django.utils.encoding import force_unicode

import typogrify.titlecase as _titlecase

register = template.Library()


def smart_filter(fn):
    '''
    Escapes filter's content based on template autoescape mode and marks output as safe
    '''
    def wrapper(text, autoescape=None):
        if autoescape:
            esc = conditional_escape
        else:
            esc = lambda x: x

        return mark_safe(fn(esc(text)))
    wrapper.needs_autoescape = True

    register.filter(fn.__name__, wrapper)
    return wrapper


@smart_filter
def amp(text, autoescape=None):
    """Wraps apersands in HTML with ``<span class="amp">`` so they can be
    styled with CSS. Apersands are also normalized to ``&amp;``. Requires
    ampersands to have whitespace or an ``&nbsp;`` on both sides.

    >>> amp('One & two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('One &amp; two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('One &#38; two')
    u'One <span class="amp">&amp;</span> two'

    >>> amp('One&nbsp;&amp;&nbsp;two')
    u'One&nbsp;<span class="amp">&amp;</span>&nbsp;two'

    It won't mess up & that are already wrapped, in entities or URLs

    >>> amp('One <span class="amp">&amp;</span> two')
    u'One <span class="amp">&amp;</span> two'
    >>> amp('&ldquo;this&rdquo; & <a href="/?that&amp;test">that</a>')
    u'&ldquo;this&rdquo; <span class="amp">&amp;</span> <a href="/?that&amp;test">that</a>'

    It should ignore standalone amps that are in attributes
    >>> amp('<link href="xyz.html" title="One & Two">xyz</link>')
    u'<link href="xyz.html" title="One & Two">xyz</link>'
    """

    # tag_pattern from http://haacked.com/archive/2004/10/25/usingregularexpressionstomatchhtml.aspx
    # it kinda sucks but it fixes the standalone amps in attributes bug
    tag_pattern = '</?\w+((\s+\w+(\s*=\s*(?:".*?"|\'.*?\'|[^\'">\s]+))?)+\s*|\s*)/?>'
    amp_finder = re.compile(r"(\s|&nbsp;)(&|&amp;|&\#38;)(\s|&nbsp;)")
    intra_tag_finder = re.compile(r'(?P<prefix>(%s)?)(?P<text>([^<]*))(?P<suffix>(%s)?)' % (tag_pattern, tag_pattern))

    def _amp_process(groups):
        prefix = groups.group('prefix') or ''
        text = amp_finder.sub(r"""\1<span class="amp">&amp;</span>\3""", groups.group('text'))
        suffix = groups.group('suffix') or ''
        return prefix + text + suffix
    return intra_tag_finder.sub(_amp_process, text)


@smart_filter
def caps(text):
    """Wraps multiple capital letters in ``<span class="caps">``
    so they can be styled with CSS.

    >>> caps("A message from KU")
    u'A message from <span class="caps">KU</span>'

    Uses the smartypants tokenizer to not screw with HTML or with tags it shouldn't.

    >>> caps("<PRE>CAPS</pre> more CAPS")
    u'<PRE>CAPS</pre> more <span class="caps">CAPS</span>'

    >>> caps("A message from 2KU2 with digits")
    u'A message from <span class="caps">2KU2</span> with digits'

    >>> caps("Dotted caps followed by spaces should never include them in the wrap D.O.T.   like so.")
    u'Dotted caps followed by spaces should never include them in the wrap <span class="caps">D.O.T.</span>  like so.'

    All caps with with apostrophes in them shouldn't break. Only handles dump apostrophes though.
    >>> caps("JIMMY'S")
    u'<span class="caps">JIMMY\\'S</span>'

    >>> caps("<i>D.O.T.</i>HE34T<b>RFID</b>")
    u'<i><span class="caps">D.O.T.</span></i><span class="caps">HE34T</span><b><span class="caps">RFID</span></b>'
    """

    tokens = _smartypants._tokenize(text)
    result = []
    in_skipped_tag = False

    cap_finder = re.compile(r"""(
                            (\b[A-Z\d]*        # Group 2: Any amount of caps and digits
                            [A-Z]\d*[A-Z]      # A cap string must at least include two caps (but they can have digits between them)
                            [A-Z\d']*\b)       # Any amount of caps and digits or dumb apostsrophes
                            | (\b[A-Z]+\.\s?   # OR: Group 3: Some caps, followed by a '.' and an optional space
                            (?:[A-Z]+\.\s?)+)  # Followed by the same thing at least once more
                            (?:\s|\b|$))
                            """, re.VERBOSE)

    def _cap_wrapper(matchobj):
        """This is necessary to keep dotted cap strings to pick up extra spaces"""
        if matchobj.group(2):
            return """<span class="caps">%s</span>""" % matchobj.group(2)
        else:
            if matchobj.group(3)[-1] == " ":
                caps = matchobj.group(3)[:-1]
                tail = ' '
            else:
                caps = matchobj.group(3)
                tail = ''
            return """<span class="caps">%s</span>%s""" % (caps, tail)

    tags_to_skip_regex = re.compile("<(/)?(?:pre|code|kbd|script|math)[^>]*>", re.IGNORECASE)

    for token in tokens:
        if token[0] == "tag":
            # Don't mess with tags.
            result.append(token[1])
            close_match = tags_to_skip_regex.match(token[1])
            if close_match and close_match.group(1) is None:
                in_skipped_tag = True
            else:
                in_skipped_tag = False
        else:
            if in_skipped_tag:
                result.append(token[1])
            else:
                result.append(cap_finder.sub(_cap_wrapper, token[1]))
    return "".join(result)


@smart_filter
def number_suffix(text):
    """Wraps date suffix in <span class="ord">
    so they can be styled with CSS.

    >>> number_suffix("10th")
    u'10<span class="rod">th</span>'

    Uses the smartypants tokenizer to not screw with HTML or with tags it shouldn't.

    """

    suffix_finder = re.compile(r'(?P<number>[\d]+)(?P<ord>st|nd|rd|th)')

    def _suffix_process(groups):
        number = groups.group('number')
        suffix = groups.group('ord')

        return "%s<span class='ord'>%s</span>" % (number, suffix)
    return suffix_finder.sub(_suffix_process, text)


@smart_filter
def initial_quotes(text):
    """Wraps initial quotes in ``class="dquo"`` for double quotes or
    ``class="quo"`` for single quotes. Works in these block tags ``(h1-h6, p, li, dt, dd)``
    and also accounts for potential opening inline elements ``a, em, strong, span, b, i``

    >>> initial_quotes('"With primes"')
    u'<span class="dquo">"</span>With primes"'
    >>> initial_quotes("'With single primes'")
    u'<span class="quo">\\'</span>With single primes\\''

    >>> initial_quotes('<a href="#">"With primes and a link"</a>')
    u'<a href="#"><span class="dquo">"</span>With primes and a link"</a>'

    >>> initial_quotes('&#8220;With smartypanted quotes&#8221;')
    u'<span class="dquo">&#8220;</span>With smartypanted quotes&#8221;'
    """

    quote_finder = re.compile(r"""((<(p|h[1-6]|li|dt|dd)[^>]*>|^)              # start with an opening p, h1-6, li, dd, dt or the start of the string
                                  \s*                                          # optional white space!
                                  (<(a|em|span|strong|i|b)[^>]*>\s*)*)         # optional opening inline tags, with more optional white space for each.
                                  (("|&ldquo;|&\#8220;)|('|&lsquo;|&\#8216;))  # Find me a quote! (only need to find the left quotes and the primes)
                                                                               # double quotes are in group 7, singles in group 8
                                  """, re.VERBOSE)

    def _quote_wrapper(matchobj):
        if matchobj.group(7):
            classname = "dquo"
            quote = matchobj.group(7)
        else:
            classname = "quo"
            quote = matchobj.group(8)
        return """%s<span class="%s">%s</span>""" % (matchobj.group(1), classname, quote)
    output = quote_finder.sub(_quote_wrapper, text)
    return output


@smart_filter
def smartypants(text):
    """Applies smarty pants to curl quotes.

    >>> smartypants('The "Green" man')
    u'The &#8220;Green&#8221; man'
    """

    return _smartypants.smartypants(text)


@smart_filter
def titlecase(text):
    """Support for titlecase.py's titlecasing

    >>> titlecase("this V that")
    u'This v That'

    >>> titlecase("this is just an example.com")
    u'This Is Just an example.com'
    """

    return _titlecase.titlecase(text)


@smart_filter
def widont(text):
    """Replaces the space between the last two words in a string with ``&nbsp;``
    Works in these block tags ``(h1-h6, p, li, dd, dt)`` and also accounts for
    potential closing inline elements ``a, em, strong, span, b, i``

    >>> widont('A very simple test')
    u'A very simple&nbsp;test'

    Single word items shouldn't be changed
    >>> widont('Test')
    u'Test'
    >>> widont(' Test')
    u' Test'
    >>> widont('<ul><li>Test</p></li><ul>')
    u'<ul><li>Test</p></li><ul>'
    >>> widont('<ul><li> Test</p></li><ul>')
    u'<ul><li> Test</p></li><ul>'

    >>> widont('<p>In a couple of paragraphs</p><p>paragraph two</p>')
    u'<p>In a couple of&nbsp;paragraphs</p><p>paragraph&nbsp;two</p>'

    >>> widont('<h1><a href="#">In a link inside a heading</i> </a></h1>')
    u'<h1><a href="#">In a link inside a&nbsp;heading</i> </a></h1>'

    >>> widont('<h1><a href="#">In a link</a> followed by other text</h1>')
    u'<h1><a href="#">In a link</a> followed by other&nbsp;text</h1>'

    Empty HTMLs shouldn't error
    >>> widont('<h1><a href="#"></a></h1>')
    u'<h1><a href="#"></a></h1>'

    >>> widont('<div>Divs get no love!</div>')
    u'<div>Divs get no love!</div>'

    >>> widont('<pre>Neither do PREs</pre>')
    u'<pre>Neither do PREs</pre>'

    >>> widont('<div><p>But divs with paragraphs do!</p></div>')
    u'<div><p>But divs with paragraphs&nbsp;do!</p></div>'
    """

    widont_finder = re.compile(r"""((?:</?(?:a|em|span|strong|i|b)[^>]*>)|[^<>\s]) # must be proceeded by an approved inline opening or closing tag or a nontag/nonspace
                                   \s+                                             # the space to replace
                                   ([^<>\s]+                                       # must be flollowed by non-tag non-space characters
                                   \s*                                             # optional white space!
                                   (</(a|em|span|strong|i|b)>\s*)*                 # optional closing inline tags with optional white space after each
                                   ((</(p|h[1-6]|li|dt|dd)>)|$))                   # end with a closing p, h1-6, li or the end of the string
                                   """, re.VERBOSE)

    output = widont_finder.sub(r'\1&nbsp;\2', text)
    return output


@register.filter
def fuzzydate(value, cutoff=180):
    """
    * takes a value (date) and cutoff (in days)

    If the date is within 1 day of Today:
        Returns
            'today'
            'yesterday'
            'tomorrow'

    If the date is within Today +/- the cutoff:
        Returns
            '2 months ago'
            'in 3 weeks'
            '2 years ago'
            etc.


    if this date is from the current year, but outside the cutoff:
        returns the value for 'CURRENT_YEAR_DATE_FORMAT' in settings if it exists.
        Otherwise returns:
            January 10th
            December 1st

    if the date is not from the current year and outside the cutoff:
        returns the value for 'DATE_FORMAT' in settings if it exists.
    """

    try:
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't a date object
        return value
    except ValueError:
        # Date arguments out of range
        return value

    today = date.today()
    delta = value - today

    if delta.days == 0:
        return u"today"
    elif delta.days == -1:
        return u"yesterday"
    elif delta.days == 1:
        return u"tomorrow"

    chunks = (
        (365.0, lambda n: ungettext('year', 'years', n)),
        (30.0, lambda n: ungettext('month', 'months', n)),
        (7.0, lambda n: ungettext('week', 'weeks', n)),
        (1.0, lambda n: ungettext('day', 'days', n)),
    )

    if abs(delta.days) <= cutoff:
        for i, (chunk, name) in enumerate(chunks):
                if abs(delta.days) >= chunk:
                    count = abs(round(delta.days / chunk, 0))
                    break

        date_str = ugettext('%(number)d %(type)s') % {'number': count, 'type': name(count)}

        if delta.days > 0:
            return "in " + date_str
        else:
            return date_str + " ago"
    else:
        if value.year == today.year:
            format = getattr(settings, "CURRENT_YEAR_DATE_FORMAT", "F jS")
        else:
            format = getattr(settings, "DATE_FORMAT")

        return template.defaultfilters.date(value, format)
fuzzydate.is_safe = True


@register.filter
def super_fuzzydate(value):
    try:
        value = date(value.year, value.month, value.day)
    except AttributeError:
        # Passed value wasn't a date object
        return value
    except ValueError:
        # Date arguments out of range
        return value

    # today
    today = date.today()
    delta = value - today

    # get the easy values out of the way
    if delta.days == 0:
        return u"Today"
    elif delta.days == -1:
        return u"Yesterday"
    elif delta.days == 1:
        return u"Tomorrow"

    # if we're in the future...
    if value > today:
        end_of_week = today + timedelta(days=7 - today.isoweekday())
        if value <= end_of_week:
            # return the name of the day (Wednesday)
            return u'this %s' % template.defaultfilters.date(value, "l")

        end_of_next_week = end_of_week + timedelta(weeks=1)
        if value <= end_of_next_week:
            # return the name of the day(Next Wednesday)
            return u"next %s" % template.defaultfilters.date(value, "l")

        end_of_month = today + timedelta(calendar.monthrange(today.year, today.month)[1] - today.day)
        if value <= end_of_month:
            # return the number of weeks (in two weeks)
            if value <= end_of_next_week + timedelta(weeks=1):
                return u"in two weeks"
            elif value <= end_of_next_week + timedelta(weeks=2):
                return u"in three weeks"
            elif value <= end_of_next_week + timedelta(weeks=3):
                return u"in four weeks"
            elif value <= end_of_next_week + timedelta(weeks=4):
                return u"in five weeks"

        if today.month == 12:
            next_month = 1
        else:
            next_month = today.month + 1

        end_of_next_month = date(today.year, next_month, calendar.monthrange(today.year, today.month)[1])
        if value <= end_of_next_month:
            # if we're in next month
            return u'next month'

        # the last day of the year
        end_of_year = date(today.year, 12, 31)
        if value <= end_of_year:
            # return the month name (March)
            return template.defaultfilters.date(value, "F")

        # the last day of next year
        end_of_next_year = date(today.year + 1, 12, 31)
        if value <= end_of_next_year:
            return u'next %s' % template.defaultfilters.date(value, "F")

        return template.defaultfilters.date(value, "Y")
    else:
        # TODO add the past
        return fuzzydate(value)
super_fuzzydate.is_safe = True

@register.filter
def text_whole_number(value):
    """
    Takes a whole number, and if its less than 10, writes it out in text.

    english only for now.
    """

    try:
        value = int(value)
    except ValueError:
        # Not an int
        return value

    if value <= 10:
        if value == 1:
            value = "one"
        elif value == 2:
            value = "two"
        elif value == 3:
            value = "three"
        elif value == 4:
            value = "four"
        elif value == 5:
            value = "five"
        elif value == 6:
            value = "six"
        elif value == 7:
            value = "seven"
        elif value == 8:
            value = "eight"
        elif value == 9:
            value = "nine"
        elif value == 10:
            value = "ten"
    return value
text_whole_number.is_safe = True

@smart_filter
def typogrify(text):
    """The super typography filter

    Applies the following filters: widont, smartypants, caps, amp, initial_quotes

    >>> typogrify('<h2>"Jayhawks" & KU fans act extremely obnoxiously</h2>')
    u'<h2><span class="dquo">&#8220;</span>Jayhawks&#8221; <span class="amp">&amp;</span> <span class="caps">KU</span> fans act extremely&nbsp;obnoxiously</h2>'

    Each filters properly handles autoescaping.
    >>> conditional_escape(typogrify('<h2>"Jayhawks" & KU fans act extremely obnoxiously</h2>'))
    u'<h2><span class="dquo">&#8220;</span>Jayhawks&#8221; <span class="amp">&amp;</span> <span class="caps">KU</span> fans act extremely&nbsp;obnoxiously</h2>'
    """
    text = force_unicode(text)
    text = amp(text)
    text = widont(text)
    text = smartypants(text)
    text = caps(text)
    text = initial_quotes(text)
    text = number_suffix(text)

    return text


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

########NEW FILE########
__FILENAME__ = fuzzydate
from datetime import datetime, timedelta

from django.test import TestCase
from django.conf import settings

from typogrify.templatetags.typogrify_tags import fuzzydate


class TestFuzzyDate(TestCase):
    def setUp(self):
        settings.DATE_FORMAT = "F jS, Y"

    def test_returns_yesterday(self):
        yesterday = datetime.now() - timedelta(hours=24)
        self.assertEquals(fuzzydate(yesterday), "yesterday")

        two_days_ago = datetime.now() - timedelta(hours=48)
        self.assertNotEquals(fuzzydate(two_days_ago), "yesterday")

    def test_returns_today(self):
        today = datetime.now()
        self.assertEquals(fuzzydate(today), "today")

    def test_returns_tomorrow(self):
        tomorrow = datetime.now() + timedelta(hours=24)
        self.assertEquals(fuzzydate(tomorrow), "tomorrow")

    def test_formats_current_year(self):
        now = datetime.now()
        testdate = datetime.strptime("%s/10/10" % now.year, "%Y/%m/%d")

        expected = "October 10th"
        self.assertEquals(fuzzydate(testdate, 1), expected)

    def test_formats_other_years(self):
        testdate = datetime.strptime("1984/10/10", "%Y/%m/%d")

        expected = "October 10th, 1984"
        self.assertEquals(fuzzydate(testdate), expected)

########NEW FILE########
__FILENAME__ = titlecase
# -*- coding: utf-8 -*-

import unittest
import sys
import re

SMALL = 'a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via|vs\.?'
PUNCT = "[!\"#$%&'‘()*+,-./:;?@[\\\\\\]_`{|}~]"

SMALL_WORDS = re.compile(r'^(%s)$' % SMALL, re.I)
INLINE_PERIOD = re.compile(r'[a-zA-Z][.][a-zA-Z]')
UC_ELSEWHERE = re.compile(r'%s*?[a-zA-Z]+[A-Z]+?' % PUNCT)
CAPFIRST = re.compile(r"^%s*?([A-Za-z])" % PUNCT)
SMALL_FIRST = re.compile(r'^(%s*)(%s)\b' % (PUNCT, SMALL), re.I)
SMALL_LAST = re.compile(r'\b(%s)%s?$' % (SMALL, PUNCT), re.I)
SUBPHRASE = re.compile(r'([:.;?!][ ])(%s)' % SMALL)


def titlecase(text):
    """
    Titlecases input text

    This filter changes all words to Title Caps, and attempts to be clever
    about *un*capitalizing SMALL words like a/an/the in the input.

    The list of "SMALL words" which are not capped comes from
    the New York Times Manual of Style, plus 'vs' and 'v'.

    """

    words = re.split('\s', text)
    line = []
    for word in words:
        if INLINE_PERIOD.search(word) or UC_ELSEWHERE.match(word):
            line.append(word)
            continue
        if SMALL_WORDS.match(word):
            line.append(word.lower())
            continue
        line.append(CAPFIRST.sub(lambda m: m.group(0).upper(), word))

    line = " ".join(line)

    line = SMALL_FIRST.sub(lambda m: '%s%s' % (
        m.group(1),
        m.group(2).capitalize()
    ), line)

    line = SMALL_LAST.sub(lambda m: m.group(0).capitalize(), line)

    line = SUBPHRASE.sub(lambda m: '%s%s' % (
        m.group(1),
        m.group(2).capitalize()
    ), line)

    return line


class TitlecaseTests(unittest.TestCase):
    """Tests to ensure titlecase follows all of the rules"""

    def test_q_and_a(self):
        """Testing: Q&A With Steve Jobs: 'That's What Happens In Technology' """
        text = titlecase(
            "Q&A with steve jobs: 'that's what happens in technology'"
        )
        result = "Q&A With Steve Jobs: 'That's What Happens in Technology'"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_at_and_t(self):
        """Testing: What Is AT&T's Problem?"""

        text = titlecase("What is AT&T's problem?")
        result = "What Is AT&T's Problem?"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_apple_deal(self):
        """Testing: Apple Deal With AT&T Falls Through"""

        text = titlecase("Apple deal with AT&T falls through")
        result = "Apple Deal With AT&T Falls Through"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_this_v_that(self):
        """Testing: this v that"""
        text = titlecase("this v that")
        result = "This v That"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_this_v_that2(self):
        """Testing: this v. that"""

        text = titlecase("this v. that")
        result = "This v. That"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_this_vs_that(self):
        """Testing: this vs that"""

        text = titlecase("this vs that")
        result = "This vs That"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_this_vs_that2(self):
        """Testing: this vs. that"""

        text = titlecase("this vs. that")
        result = "This vs. That"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_apple_sec(self):
        """Testing: The SEC's Apple Probe: What You Need to Know"""

        text = titlecase("The SEC's Apple Probe: What You Need to Know")
        result = "The SEC's Apple Probe: What You Need to Know"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_small_word_quoted(self):
        """Testing: 'by the Way, Small word at the start but within quotes.'"""

        text = titlecase(
            "'by the Way, small word at the start but within quotes.'"
        )
        result = "'By the Way, Small Word at the Start but Within Quotes.'"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_small_word_end(self):
        """Testing: Small word at end is nothing to be afraid of"""

        text = titlecase("Small word at end is nothing to be afraid of")
        result = "Small Word at End Is Nothing to Be Afraid Of"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_sub_phrase_small_word(self):
        """Testing: Starting Sub-Phrase With a Small Word: a Trick, Perhaps?"""

        text = titlecase(
            "Starting Sub-Phrase With a Small Word: a Trick, Perhaps?"
        )
        result = "Starting Sub-Phrase With a Small Word: A Trick, Perhaps?"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_small_word_quotes(self):
        """Testing: Sub-Phrase With a Small Word in Quotes: 'a Trick..."""

        text = titlecase(
            "Sub-Phrase With a Small Word in Quotes: 'a Trick, Perhaps?'"
        )
        result = "Sub-Phrase With a Small Word in Quotes: 'A Trick, Perhaps?'"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_small_word_double_quotes(self):
        """Testing: Sub-Phrase With a Small Word in Quotes: \"a Trick..."""
        text = titlecase(
            'Sub-Phrase With a Small Word in Quotes: "a Trick, Perhaps?"'
        )
        result = 'Sub-Phrase With a Small Word in Quotes: "A Trick, Perhaps?"'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_nothing_to_be_afraid_of(self):
        """Testing: \"Nothing to Be Afraid of?\""""
        text = titlecase('"Nothing to Be Afraid of?"')
        result = '"Nothing to Be Afraid Of?"'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_nothing_to_be_afraid_of2(self):
        """Testing: \"Nothing to Be Afraid Of?\""""

        text = titlecase('"Nothing to be Afraid Of?"')
        result = '"Nothing to Be Afraid Of?"'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_a_thing(self):
        """Testing: a thing"""

        text = titlecase('a thing')
        result = 'A Thing'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_vapourware(self):
        """Testing: 2lmc Spool: 'Gruber on OmniFocus and Vapo(u)rware'"""
        text = titlecase(
            "2lmc Spool: 'gruber on OmniFocus and vapo(u)rware'"
        )
        result = "2lmc Spool: 'Gruber on OmniFocus and Vapo(u)rware'"
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_domains(self):
        """Testing: this is just an example.com"""
        text = titlecase('this is just an example.com')
        result = 'This Is Just an example.com'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_domains2(self):
        """Testing: this is something listed on an del.icio.us"""

        text = titlecase('this is something listed on del.icio.us')
        result = 'This Is Something Listed on del.icio.us'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_itunes(self):
        """Testing: iTunes should be unmolested"""

        text = titlecase('iTunes should be unmolested')
        result = 'iTunes Should Be Unmolested'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_thoughts_on_music(self):
        """Testing: Reading Between the Lines of Steve Jobs’s..."""

        text = titlecase(
            'Reading between the lines of steve jobs’s ‘thoughts on music’'
        )
        result = 'Reading Between the Lines of Steve Jobs’s ‘Thoughts on '\
            'Music’'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_repair_perms(self):
        """Testing: Seriously, ‘Repair Permissions’ Is Voodoo"""

        text = titlecase('seriously, ‘repair permissions’ is voodoo')
        result = 'Seriously, ‘Repair Permissions’ Is Voodoo'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))

    def test_generalissimo(self):
        """Testing: Generalissimo Francisco Franco..."""

        text = titlecase(
            'generalissimo francisco franco: still dead; kieren McCarthy: '
            'still a jackass'
        )
        result = 'Generalissimo Francisco Franco: Still Dead; Kieren '\
            'McCarthy: Still a Jackass'
        self.assertEqual(text, result, "%s should be: %s" % (text, result, ))


if __name__ == '__main__':
    if not sys.stdin.isatty():
        for line in sys.stdin:
            print titlecase(line)

    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TitlecaseTests)
        unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
