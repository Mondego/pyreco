__FILENAME__ = verbal_expressions_test
# -*- encoding: utf-8 -*-
import unittest
from verbalexpressions import VerEx
import re

class VerExTest(unittest.TestCase):
    '''
        Tests for verbal_expressions.py
    '''

    def setUp(self):
        self.v = VerEx()

    def tearDown(self):
        self.v = None
        self.exp = None

    def test_should_render_verex_as_string(self):
        self.assertEquals(str(self.v.add('^$')), '^$')

    def test_should_match_characters_in_range(self):
        self.exp = self.v.start_of_line().range('a', 'c').regex()
        for character in ['a', 'b', 'c']:
            self.assertRegexpMatches(character, self.exp)

    def test_should_not_match_characters_outside_of_range(self):
        self.exp = self.v.start_of_line().range('a', 'c').regex()
        self.assertNotRegexpMatches('d', self.exp)

    def test_should_match_characters_in_extended_range(self):
        self.exp = self.v.start_of_line().range('a', 'b', 'X', 'Z').regex()
        for character in ['a', 'b']:
            self.assertRegexpMatches(character, self.exp)
        for character in ['X', 'Y', 'Z']:
            self.assertRegexpMatches(character, self.exp)

    def test_should_not_match_characters_outside_of_extended_range(self):
        self.exp = self.v.start_of_line().range('a', 'b', 'X', 'Z').regex()
        self.assertNotRegexpMatches('c', self.exp)
        self.assertNotRegexpMatches('W', self.exp)


    def test_should_match_start_of_line(self):
        self.exp = self.v.start_of_line().regex()
        self.assertRegexpMatches('text  ', self.exp, 'Not started :(')

    def test_should_match_end_of_line(self):
        self.exp = self.v.start_of_line().end_of_line().regex()
        self.assertRegexpMatches('', self.exp, 'It\'s not the end!')

    def test_should_match_anything(self):
        self.exp = self.v.start_of_line().anything().end_of_line().regex()
        self.assertRegexpMatches('!@#$%¨&*()__+{}', self.exp, 'Not so anything...')

    def test_should_match_anything_but_specified_element_when_element_is_not_found(self):
        self.exp = self.v.start_of_line().anything_but('X').end_of_line().regex()
        self.assertRegexpMatches('Y Files', self.exp, 'Found the X!')

    def test_should_not_match_anything_but_specified_element_when_specified_element_is_found(self):
        self.exp = self.v.start_of_line().anything_but('X').end_of_line().regex()
        self.assertNotRegexpMatches('VerEX', self.exp, 'Didn\'t found the X :(')

    def test_should_find_element(self):
        self.exp = self.v.start_of_line().find('Wally').end_of_line().regex()
        self.assertRegexpMatches('Wally', self.exp, '404! Wally not Found!')

    def test_should_not_find_missing_element(self):
        self.exp = self.v.start_of_line().find('Wally').end_of_line().regex()
        self.assertNotRegexpMatches('Wall-e', self.exp, 'DAFUQ is Wall-e?')

    def test_should_match_when_maybe_element_is_present(self):
        self.exp = self.v.start_of_line().find('Python2.').maybe('7').end_of_line().regex()
        self.assertRegexpMatches('Python2.7', self.exp, 'Version doesn\'t match!')

    def test_should_match_when_maybe_element_is_missing(self):
        self.exp = self.v.start_of_line().find('Python2.').maybe('7').end_of_line().regex()
        self.assertRegexpMatches('Python2.', self.exp, 'Version doesn\'t match!')

    def test_should_match_on_any_when_element_is_found(self):
        self.exp = self.v.start_of_line().any('Q').anything().end_of_line().regex()
        self.assertRegexpMatches('Query', self.exp, 'No match found!')

    def test_should_not_match_on_any_when_element_is_not_found(self):
        self.exp = self.v.start_of_line().any('Q').anything().end_of_line().regex()
        self.assertNotRegexpMatches('W', self.exp, 'I\'ve found it!')

    def test_should_match_when_line_break_present(self):
        self.exp = self.v.start_of_line().anything().line_break().anything().end_of_line().regex()
        self.assertRegexpMatches('Marco \n Polo', self.exp, 'Give me a break!!')

    def test_should_match_when_line_break_and_carriage_return_present(self):
        self.exp = self.v.start_of_line().anything().line_break().anything().end_of_line().regex()
        self.assertRegexpMatches('Marco \r\n Polo', self.exp, 'Give me a break!!')

    def test_should_not_match_when_line_break_is_missing(self):
        self.exp = self.v.start_of_line().anything().line_break().anything().end_of_line().regex()
        self.assertNotRegexpMatches('Marco Polo', self.exp, 'There\'s a break here!')

    def test_should_match_when_tab_present(self):
        self.exp = self.v.start_of_line().anything().tab().end_of_line().regex()
        self.assertRegexpMatches('One tab only	', self.exp, 'No tab here!')

    def test_should_not_match_when_tab_is_missing(self):
        self.exp = self.v.start_of_line().anything().tab().end_of_line().regex()
        self.assertFalse(re.match(self.exp, 'No tab here'), 'There\'s a tab here!')

    def test_should_match_when_word_present(self):
        self.exp = self.v.start_of_line().anything().word().end_of_line().regex()
        self.assertRegexpMatches('Oneword', self.exp, 'Not just a word!')

    def test_not_match_when_two_words_are_present_instead_of_one(self):
        self.exp = self.v.start_of_line().anything().tab().end_of_line().regex()
        self.assertFalse(re.match(self.exp, 'Two words'), 'I\'ve found two of them')

    def test_should_match_when_or_condition_fulfilled(self):
        self.exp = self.v.start_of_line().anything().find('G').OR().find('h').end_of_line().regex()
        self.assertRegexpMatches('Github', self.exp, 'Octocat not found')

    def test_should_not_match_when_or_condition_not_fulfilled(self):
        self.exp = self.v.start_of_line().anything().find('G').OR().find('h').end_of_line().regex()
        self.assertFalse(re.match(self.exp, 'Bitbucket'), 'Bucket not found')

    def test_should_match_on_upper_case_when_lower_case_is_given_and_any_case_is_true(self):
        self.exp = self.v.start_of_line().find('THOR').end_of_line().with_any_case(True).regex()
        self.assertRegexpMatches('thor', self.exp, 'Upper case Thor, please!')

    def test_should_match_multiple_lines(self):
        self.exp = self.v.start_of_line().anything().find('Pong').anything().end_of_line().search_one_line(True).regex()
        self.assertRegexpMatches('Ping \n Pong \n Ping', self.exp, 'Pong didn\'t answer')

    def test_should_match_email_address(self):
        self.exp = self.v.start_of_line().word().then('@').word().then('.').word().end_of_line().regex()
        self.assertRegexpMatches('mail@mail.com', self.exp, 'Not a valid email')

    def test_should_match_url(self):
        self.exp = self.v.start_of_line().then('http').maybe('s').then('://').maybe('www.').word().then('.').word().maybe('/').end_of_line().regex()
        self.assertRegexpMatches('https://www.google.com/', self.exp, 'Not a valid email')

########NEW FILE########
__FILENAME__ = verbal_expressions
import re


def re_escape(fn):
    def arg_escaped(this, *args):
        t = [isinstance(a, VerEx) and a.s or re.escape(str(a)) for a in args]
        return fn(this, *t)
    return arg_escaped


class VerEx(object):
    '''
    --- VerbalExpressions class ---
    the following methods behave different from the original js lib!

    - end_of_line
    - start_of_line
    - or
    when you say you want `$`, `^` and `|`, we just insert it right there.
    No other tricks.

    And any string you inserted will be automatically grouped
    except `tab` and `add`.
    '''
    def __init__(self):
        self.s = ''
        self.modifiers = {'I': 0, 'M': 0}

    def __getattr__(self, attr):
        ''' any other function will be sent to the regex object '''
        regex = self.regex()
        return getattr(regex, attr)

    def __str__(self):
        return self.s

    def add(self, value):
        self.s += value
        return self

    def regex(self):
        ''' get a regular expression object. '''
        return re.compile(self.s, self.modifiers['I'] | self.modifiers['M'])
    compile = regex

    def source(self):
        ''' return the raw string'''
        return self.s
    raw = value = source

    # ---------------------------------------------

    def anything(self):
        return self.add('(.*)')

    @re_escape
    def anything_but(self, value):
        return self.add('([^' + value + ']*)')

    def end_of_line(self):
        return self.add('$')

    @re_escape
    def maybe(self, value):
        return self.add("(" + value + ")?")

    def start_of_line(self):
        return self.add('^')

    @re_escape
    def find(self, value):
        return self.add('(' + value + ')')
    then = find

    # special characters and groups

    @re_escape
    def any(self, value):
        return self.add("([" + value + "])")
    any_of = any

    def line_break(self):
        return self.add(r"(\n|(\r\n))")
    br = line_break

    @re_escape
    def range(self, *args):
        from_tos = [args[i:i+2] for i in range(0, len(args), 2)]
        return self.add("([" + ''.join(['-'.join(i) for i in from_tos]) + "])")

    def tab(self):
        return self.add(r'\t')

    def word(self):
        return self.add(r"(\w+)")

    def OR(self, value=None):
        ''' `or` is a python keyword so we use `OR` instead. '''
        self.add("|")
        return self.find(value) if value else self

    def replace(self, string, repl):
        return self.sub(repl, string)

    # --------------- modifiers ------------------------

    # no global option. It depends on which method
    # you called on the regex object.

    def with_any_case(self, value=False):
        self.modifiers['I'] = re.I if value else 0
        return self

    def search_one_line(self, value=False):
        self.modifiers['M'] = re.M if value else 0
        return self

########NEW FILE########
