__FILENAME__ = assertions_test
# -*- coding: utf-8 -*-
from __future__ import with_statement
import warnings

from testify import TestCase
from testify import assertions
from testify import run
from testify import assert_between
from testify import assert_dict_subset
from testify import assert_equal
from testify import assert_not_reached
from testify import assert_true
from testify import assert_false
from testify.contrib.doctestcase import DocTestCase


class DiffMessageTestCase(TestCase):

    def test_shows_string_diffs(self):
        expected = 'Diff:\nl: abc<>\nr: abc<def>'
        diff_message = assertions._diff_message('abc', 'abcdef')
        assert_equal(expected, diff_message)

    def test_shows_repr_diffs(self):
        class AbcRepr(object):
            __repr__ = lambda self: 'abc'

        class AbcDefRepr(object):
            __repr__ = lambda self: 'abcdef'

        expected = 'Diff:\nl: abc<>\nr: abc<def>'
        diff_message = assertions._diff_message(AbcRepr(), AbcDefRepr())
        assert_equal(expected, diff_message)


class AssertBetweenTestCase(TestCase):

    def test_argument_order(self):
        try:
            assert_between(1, 2, 3)
        except AssertionError:
            assert False, "Expected assert_between(1, 2, 3) to pass."

        try:
            assert_between(2, 1, 3)
            assert False, "Expected assert_between(2, 1, 3) to fail."
        except AssertionError:
            pass


class AssertEqualTestCase(TestCase):

    def test_shows_pretty_diff_output(self):
        expected = \
            'assertion failed: l == r\n' \
            "l: 'that reviewboard differ is awesome'\n" \
            "r: 'dat reviewboard differ is ozsom'\n\n" \
            'Diff:' \
            '\nl: <th>at reviewboard differ is <awe>som<e>\n' \
            'r: <d>at reviewboard differ is <oz>som<>'

        try:
            assert_equal('that reviewboard differ is awesome',
                         'dat reviewboard differ is ozsom')
        except AssertionError, e:
            assert_equal(expected, e.args[0])
        else:
            assert False, 'Expected `AssertionError`.'

    def test_unicode_diff(self):
        ascii_string = 'abc'
        unicode_string = u'ü and some more'
        def assert_with_unicode_msg():
            assert_equal(unicode_string, ascii_string)
        assertions.assert_raises_and_contains(AssertionError, 'abc', assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, 'and some more', assert_with_unicode_msg)

    def test_unicode_diff2(self):
        unicode_string = u'Thę quıćk brōwń fōx jumpęd ōvęr thę łąźy dōğ.'
        utf8_string = u'Thę quıćk brōwń fōx jumpęd ōvęr thę łąży dōğ.'
        def assert_with_unicode_msg():
            assertions.assert_equal(unicode_string, utf8_string)
        assertions.assert_raises_and_contains(AssertionError, 'łą<ź>y', assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, 'łą<ż>y', assert_with_unicode_msg)

    def test_unicode_diff3(self):
        unicode_string = u'münchen'
        utf8_string = unicode_string.encode('utf8')
        def assert_with_unicode_msg():
            assert_equal(unicode_string, utf8_string)
        assertions.assert_raises_and_contains(AssertionError, r"l: u'm\xfcnchen'", assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, r"r: 'm\xc3\xbcnchen'", assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, 'l: münchen', assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, 'r: münchen', assert_with_unicode_msg)

    def test_bytes_diff(self):
        byte_string1 = 'm\xeenchen'
        byte_string2 = 'm\xaanchen'
        def assert_with_unicode_msg():
            assert_equal(byte_string1, byte_string2)
        assertions.assert_raises_and_contains(AssertionError, r"l: 'm\xeenchen'", assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, r"r: 'm\xaanchen'", assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, 'l: m<î>nchen', assert_with_unicode_msg)
        assertions.assert_raises_and_contains(AssertionError, 'r: m<ª>nchen', assert_with_unicode_msg)

    def test_utf8_diff(self):
        utf8_string1 = u'münchen'.encode('utf8')
        utf8_string2 = u'mënchen'.encode('utf8')
        def assert_with_unicode_msg():
            assert_equal(utf8_string1, utf8_string2)
        for content in (
                r"l: 'm\xc3\xbcnchen'",
                r"r: 'm\xc3\xabnchen'",
                "l: m<ü>nchen",
                "r: m<ë>nchen",
        ):
            assertions.assert_raises_and_contains(AssertionError, content, assert_with_unicode_msg)

    def test_str_versus_unicode_diff(self):
        """Real-world example from https://github.com/Yelp/Testify/issues/144#issuecomment-14188539
        A good assert_equal implementation will clearly show that these have completely different character contents.
        """
        unicode_string = u'm\xc3\xbcnchen'
        byte_string = 'm\xc3\xbcnchen'

        def assert_with_unicode_msg():
            assert_equal(unicode_string, byte_string)
        for content in (
                r"l: u'm\xc3\xbcnchen'",
                r"r: 'm\xc3\xbcnchen'",
                "l: m<Ã¼>nchen",
                "r: m<ü>nchen",
        ):
            assertions.assert_raises_and_contains(AssertionError, content, assert_with_unicode_msg)

    def test_assert_true(self):
        assert_true(1)
        assert_true('False')
        assert_true([0])
        assert_true([''])
        assert_true({'a': 0})

    def test_assert_false(self):
        assert_false(None)
        assert_false(0)
        assert_false(0L)
        assert_false(0.0)
        assert_false('')
        assert_false(())
        assert_false([])
        assert_false({})
        assert_false((''))


class AssertInTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_in(1, [1, 2], msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_in(1, [1, 2], message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertNotInTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_not_in(3, [1, 2], msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_not_in(3, [1, 2], message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertIsTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_is(None, None, msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_is(None, None, message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertIsNotTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_is_not(False, None, msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_is_not(False, None, message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertAllMatchRegexTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_all_match_regex("foo",
                                              ["foobar", "foobaz"],
                                              msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_all_match_regex("foo",
                                              ["foobar", "foobaz"],
                                              message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertAnyMatchRegexTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_any_match_regex("foo",
                                              ["foobar", "barbaz"],
                                              msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_any_match_regex("foo",
                                              ["foobar", "barbaz"],
                                              message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertAllNotMatchRegexTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_all_not_match_regex("qux",
                                                  ["foobar", "barbaz"],
                                                  msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_all_not_match_regex("qux",
                                                  ["foobar", "barbaz"],
                                                  message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertSetsEqualTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_sets_equal(set([1, 2]),
                                         set([1, 2]),
                                         msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_sets_equal(set([1, 2]),
                                         set([1, 2]),
                                         message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertDictsEqualTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_dicts_equal({"a": 1, "b": 2},
                                          {"a": 1, "b": 2},
                                          msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_dicts_equal({"a": 1, "b": 2},
                                          {"a": 1, "b": 2},
                                          message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertDictSubsetTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_dict_subset({"a": 1, "b": 2},
                                          {"a": 1, "b": 2, "c": 3},
                                          msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_dict_subset({"a": 1, "b": 2},
                                          {"a": 1, "b": 2, "c": 3},
                                          message="This is a message")

            assertions.assert_equal(len(w), 0)


class AssertSubsetTestCase(TestCase):

    def test_deprecated_msg_param(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_subset(set([1, 2]),
                                     set([1, 2, 3]),
                                     msg="This is a message")

            assertions.assert_equal(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            assertions.assert_in("msg is deprecated", str(w[-1].message))

    def test_message_param_not_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            assertions.assert_subset(set([1, 2]),
                                     set([1, 2, 3]),
                                     message="This is a message")

            assertions.assert_equal(len(w), 0)


class MyException(Exception):
    pass


class AssertRaisesAsContextManagerTestCase(TestCase):

    def test_fails_when_exception_is_not_raised(self):
        def exception_should_be_raised():
            with assertions.assert_raises(MyException):
                pass

        try:
            exception_should_be_raised()
        except AssertionError:
            pass
        else:
            assert_not_reached('AssertionError should have been raised')

    def test_passes_when_exception_is_raised(self):
        def exception_should_be_raised():
            with assertions.assert_raises(MyException):
                raise MyException

        exception_should_be_raised()

    def test_crashes_when_another_exception_class_is_raised(self):
        def assert_raises_an_exception_and_raise_another():
            with assertions.assert_raises(MyException):
                raise ValueError

        try:
            assert_raises_an_exception_and_raise_another()
        except ValueError:
            pass
        else:
            raise AssertionError('ValueError should have been raised')


class AssertRaisesAsCallableTestCase(TestCase):

    def test_fails_when_exception_is_not_raised(self):
        raises_nothing = lambda: None
        try:
            assertions.assert_raises(ValueError, raises_nothing)
        except AssertionError:
            pass
        else:
            assert_not_reached('AssertionError should have been raised')

    def test_passes_when_exception_is_raised(self):
        def raises_value_error():
            raise ValueError
        assertions.assert_raises(ValueError, raises_value_error)

    def test_fails_when_wrong_exception_is_raised(self):
        def raises_value_error():
            raise ValueError
        try:
            assertions.assert_raises(MyException, raises_value_error)
        except ValueError:
            pass
        else:
            assert_not_reached('ValueError should have been raised')

    def test_callable_is_called_with_all_arguments(self):
        class GoodArguments(Exception): pass
        arg1, arg2, kwarg = object(), object(), object()
        def check_arguments(*args, **kwargs):
            assert_equal((arg1, arg2), args)
            assert_equal({'kwarg': kwarg}, kwargs)
            raise GoodArguments
        assertions.assert_raises(GoodArguments, check_arguments, arg1, arg2, kwarg=kwarg)


class AssertRaisesSuchThatTestCase(TestCase):

    def test_fails_when_no_exception_is_raised(self):
        """Tests that the assertion fails when no exception is raised."""
        exists = lambda e: True
        with assertions.assert_raises(AssertionError):
            with assertions.assert_raises_such_that(Exception, exists):
                pass

    def test_fails_when_wrong_exception_is_raised(self):
        """Tests that when an unexpected exception is raised, that it is
        passed through and the assertion fails."""
        exists = lambda e: True
        # note: in assert_raises*, if the exception raised is not of the
        # expected type, that exception just falls through
        with assertions.assert_raises(Exception):
            with assertions.assert_raises_such_that(AssertionError, exists):
                raise Exception("the wrong exception")

    def test_fails_when_exception_test_fails(self):
        """Tests that when an exception of the right type that fails the
        passed in exception test is raised, the assertion fails."""
        has_two_args = lambda e: assertions.assert_length(e.args, 2)
        with assertions.assert_raises(AssertionError):
            with assertions.assert_raises_such_that(Exception, has_two_args):
                raise Exception("only one argument")

    def test_passes_when_correct_exception_is_raised(self):
        """Tests that when an exception of the right type that passes the
        exception test is raised, the assertion passes."""
        has_two_args = lambda e: assertions.assert_length(e.args, 2)
        with assertions.assert_raises_such_that(Exception, has_two_args):
            raise Exception("first", "second")

    def test_callable_is_called_with_all_arguments(self):
        """Tests that the callable form works properly, with all arguments
        passed through."""
        message_is_foo = lambda e: assert_equal(str(e), 'foo')
        class GoodArguments(Exception): pass
        arg1, arg2, kwarg = object(), object(), object()
        def check_arguments(*args, **kwargs):
            assert_equal((arg1, arg2), args)
            assert_equal({'kwarg': kwarg}, kwargs)
            raise GoodArguments('foo')
        assertions.assert_raises_such_that(GoodArguments, message_is_foo, check_arguments, arg1, arg2, kwarg=kwarg)


class AssertRaisesExactlyTestCase(TestCase):
    class MyException(ValueError): pass

    def test_passes_when_correct_exception_is_raised(self):
        with assertions.assert_raises_exactly(self.MyException, "first", "second"):
            raise self.MyException("first", "second")

    def test_fails_with_wrong_value(self):
        with assertions.assert_raises(AssertionError):
            with assertions.assert_raises_exactly(self.MyException, "first", "second"):
                raise self.MyException("red", "blue")

    def test_fails_with_different_class(self):
        class SpecialException(self.MyException): pass

        with assertions.assert_raises(AssertionError):
            with assertions.assert_raises_exactly(self.MyException, "first", "second"):
                raise SpecialException("first", "second")

    def test_fails_with_vague_class(self):
        with assertions.assert_raises(AssertionError):
            with assertions.assert_raises_exactly(Exception, "first", "second"):
                raise self.MyException("first", "second")

    def test_unexpected_exception_passes_through(self):
        class DifferentException(Exception): pass

        with assertions.assert_raises(DifferentException):
            with assertions.assert_raises_exactly(self.MyException, "first", "second"):
                raise DifferentException("first", "second")


class AssertRaisesAndContainsTestCase(TestCase):

    def test_fails_when_exception_is_not_raised(self):
        raises_nothing = lambda: None
        try:
            assertions.assert_raises_and_contains(ValueError, 'abc', raises_nothing)
        except AssertionError:
            pass
        else:
            assert_not_reached('AssertionError should have been raised')

    def test_fails_when_wrong_exception_is_raised(self):
        def raises_value_error():
            raise ValueError
        try:
            assertions.assert_raises_and_contains(MyException, 'abc', raises_value_error)
        except ValueError:
            pass
        else:
            assert_not_reached('ValueError should have been raised')

    def test_callable_is_called_with_all_arguments(self):
        class GoodArguments(Exception): pass
        arg1, arg2, kwarg = object(), object(), object()
        def check_arguments(*args, **kwargs):
            assert_equal((arg1, arg2), args)
            assert_equal({'kwarg': kwarg}, kwargs)
            raise GoodArguments('abc')
        assertions.assert_raises_and_contains(GoodArguments, 'abc', check_arguments, arg1, arg2, kwarg=kwarg)

    def test_fails_when_exception_does_not_contain_string(self):
        def raises_value_error():
            raise ValueError('abc')
        try:
            assertions.assert_raises_and_contains(ValueError, 'xyz', raises_value_error)
        except AssertionError:
            pass
        else:
            assert_not_reached('AssertionError should have been raised')

    def test_passes_when_exception_contains_string_with_matching_case(self):
        def raises_value_error():
            raise ValueError('abc')
        assertions.assert_raises_and_contains(ValueError, 'abc', raises_value_error)

    def test_passes_when_exception_contains_string_with_non_matching_case(self):
        def raises_value_error():
            raise ValueError('abc')
        assertions.assert_raises_and_contains(ValueError, 'ABC', raises_value_error)

    def test_passes_when_exception_contains_multiple_strings(self):
        def raises_value_error():
            raise ValueError('abc xyz')
        assertions.assert_raises_and_contains(ValueError, ['ABC', 'XYZ'], raises_value_error)

    def test_fails_when_exception_does_not_contains_all_strings(self):
        def raises_value_error():
            raise ValueError('abc xyz')
        try:
            assertions.assert_raises_and_contains(ValueError, ['ABC', '123'], raises_value_error)
        except AssertionError:
            pass
        else:
            assert_not_reached('AssertionError should have been raised')


class AssertDictSubsetTestCase(TestCase):

    def test_passes_with_subset(self):
        superset = {'one': 1, 'two': 2, 'three': 3}
        subset = {'one': 1}

        assert_dict_subset(subset, superset)

    def test_fails_with_wrong_key(self):
        superset = {'one': 1, 'two': 2, 'three': 3}
        subset = {'four': 4}

        assertions.assert_raises(AssertionError, assert_dict_subset, subset, superset)

    def test_fails_with_wrong_value(self):
        superset = {'one': 1, 'two': 2, 'three': 3}
        subset = {'one': 2}

        assertions.assert_raises(AssertionError, assert_dict_subset, superset, subset)

    def test_message_on_fail(self):
        superset = {'one': 1, 'two': 2, 'three': 3}
        subset = {'one': 2, 'two':2}
        expected = "expected [subset has:{'one': 2}, superset has:{'one': 1}]"

        try:
            assert_dict_subset(subset, superset)
        except AssertionError, e:
            assert_equal(expected, e.args[0])
        else:
            assert_not_reached('AssertionError should have been raised')


class AssertEmptyTestCase(TestCase):

    def test_passes_on_empty_tuple(self):
        """Test that assert_empty passes on an empty tuple."""
        assertions.assert_empty(())

    def test_passes_on_empty_list(self):
        """Test that assert_empty passes on an empty list."""
        assertions.assert_empty([])

    def test_passes_on_unyielding_generator(self):
        """Test that assert_empty passes on an 'empty' generator."""
        def yield_nothing():
            if False:
                yield 0

        assertions.assert_empty(yield_nothing())

    def test_fails_on_nonempty_tuple(self):
        """Test that assert_empty fails on a nonempty tuple."""
        with assertions.assert_raises(AssertionError):
            assertions.assert_empty((0,))

    def test_fails_on_nonempty_list(self):
        """Test that assert_empty fails on a nonempty list."""
        with assertions.assert_raises(AssertionError):
            assertions.assert_empty([0])

    def test_fails_on_infinite_generator(self):
        """Tests that assert_empty fails on an infinite generator."""
        def yes():
            while True:
                yield 'y'

        with assertions.assert_raises(AssertionError):
            assertions.assert_empty(yes())

    def test_max_elements_to_print_eq_0_means_no_sample_message(self):
        """Tests that when max_elements_to_print is 0, there is no sample in the error message."""
        iterable = [1, 2, 3]
        expected_message = "iterable %s was unexpectedly non-empty." % iterable

        def message_has_no_sample(exception):
            assertions.assert_equal(str(exception), expected_message)

        with assertions.assert_raises_such_that(
                AssertionError, message_has_no_sample):
            assertions.assert_empty(iterable, max_elements_to_print=0)

    def test_max_elements_to_print_gt_len_means_whole_iterable_sample_message(self):
        """
        Tests that when max_elements_to_print is greater than the length of
        the whole iterable, the whole iterable is printed.
        """
        elements = [1, 2, 3, 4, 5]
        iterable = (i for i in elements)
        expected_message = "iterable %s was unexpectedly non-empty. elements: %s" \
                         % (iterable, elements)

        def message_has_whole_iterable_sample(exception):
            assertions.assert_equal(str(exception), expected_message)

        with assertions.assert_raises_such_that(
                AssertionError, message_has_whole_iterable_sample):
            assertions.assert_empty(iterable, max_elements_to_print=len(elements)+1)

    def test_max_elements_to_print_eq_len_means_whole_iterable_sample_message(self):
        """
        Tests that when max_elements_to_print is equal to the length of
        the whole iterable, the whole iterable is printed.
        """
        elements = [1, 2, 3, 4, 5]
        iterable = (i for i in elements)
        expected_message = "iterable %s was unexpectedly non-empty. elements: %s" \
                         % (iterable, elements)

        def message_has_whole_iterable_sample(exception):
            assertions.assert_equal(str(exception), expected_message)

        with assertions.assert_raises_such_that(
                AssertionError, message_has_whole_iterable_sample):
            assertions.assert_empty(iterable, max_elements_to_print=len(elements))

    def test_max_elements_to_print_lt_len_means_partial_iterable_sample_message(self):
        """
        Tests that when max_elements_to_print is less than the length of the
        whole iterable, the first max_elements_to_print elements are printed.
        """
        elements = [1, 2, 3, 4, 5]
        iterable = (i for i in elements)
        max_elements_to_print = len(elements) - 1
        expected_message = "iterable %s was unexpectedly non-empty. first %i elements: %s" \
                         % (iterable, max_elements_to_print, elements[:max_elements_to_print])

        def message_has_whole_iterable_sample(exception):
            assertions.assert_equal(str(exception), expected_message)

        with assertions.assert_raises_such_that(
                AssertionError, message_has_whole_iterable_sample):
            assertions.assert_empty(iterable, max_elements_to_print=max_elements_to_print)


class AssertNotEmptyTestCase(TestCase):

    def test_fails_on_empty_tuple(self):
        with assertions.assert_raises(AssertionError):
            assertions.assert_not_empty(())

    def test_fails_on_empty_list(self):
        """Test that assert_not_empty fails on an empty list."""
        with assertions.assert_raises(AssertionError):
            assertions.assert_not_empty([])

    def test_fails_on_unyielding_generator(self):
        """Test that assert_not_empty fails on an 'empty' generator."""
        def yield_nothing():
            if False:
                yield 0

        with assertions.assert_raises(AssertionError):
            assertions.assert_not_empty(yield_nothing())

    def test_passes_on_nonempty_tuple(self):
        """Test that assert_not_empty passes on a nonempty tuple."""
        assertions.assert_not_empty((0,))

    def test_passes_on_nonempty_list(self):
        """Test that assert_not_empty passes on a nonempty list."""
        assertions.assert_not_empty([0])

    def test_passes_on_infinite_generator(self):
        """Tests that assert_not_empty fails on an infinite generator."""
        def yes():
            while True:
                yield 'y'

        assertions.assert_not_empty(yes())


class AssertWarnsTestCase(TestCase):

    def _create_user_warning(self):
        warnings.warn('Hey!', stacklevel=2)

    def _create_deprecation_warning(self):
        warnings.warn('Deprecated!', DeprecationWarning, stacklevel=2)

    def _raise_exception(self, *args):
        raise RuntimeError('A test got too far! args=%r' % args)

    def test_fails_when_no_warning(self):
        """Test that assert_warns fails when there is no warning thrown."""
        with assertions.assert_raises(AssertionError):
            with assertions.assert_warns():
                pass

    def test_fails_when_no_warning_with_callable(self):
        """Test that assert_warns fails when there is no warning thrown."""
        with assertions.assert_raises(AssertionError):
            do_nothing = lambda: None
            assertions.assert_warns(UserWarning, do_nothing)

    def test_fails_when_incorrect_warning(self):
        """
        Test that assert_warns fails when we pass a specific warning and
        a different warning class is thrown.
        """
        with assertions.assert_raises(AssertionError):
            with assertions.assert_warns(DeprecationWarning):
                self._create_user_warning()

    def test_fails_when_incorrect_warning_with_callable(self):
        """
        Test that assert_warns fails when we pass a specific warning and
        a different warning class is thrown.
        """
        with assertions.assert_raises(AssertionError):
            assertions.assert_warns(DeprecationWarning, self._create_user_warning)

    def test_passes_with_any_warning(self):
        """Test that assert_warns passes if no specific warning class is given."""
        with assertions.assert_warns():
            self._create_user_warning()

    def test_passes_with_specific_warning(self):
        """Test that assert_warns passes if a specific warning class is given and thrown."""
        with assertions.assert_warns(DeprecationWarning):
            self._create_deprecation_warning()

    def test_passes_with_specific_warning_with_callable(self):
        """Test that assert_warns passes if a specific warning class is given and thrown."""
        assertions.assert_warns(DeprecationWarning, self._create_deprecation_warning)

    def test_passes_with_specific_warning_with_callable_arguments(self):
        """Test that assert_warns passes args and kwargs to the callable correctly."""
        def _requires_args_and_kwargs(*args, **kwargs):
            if args != ['foo'] and kwargs != {'bar': 'bar'}:
                raise ValueError('invalid values for args and kwargs')
            self._create_user_warning()
        # If we hit the ArgumentError, our test fails.
        assertions.assert_warns(UserWarning, _requires_args_and_kwargs, 'foo', bar='bar')

    def test_fails_when_warnings_test_raises_exception(self):
        """
        Test that assert_warns_such_that (used as a context manager)
        fails when the warnings_test method raises an exception.
        """
        with assertions.assert_raises(RuntimeError):
            with assertions.assert_warns_such_that(self._raise_exception):
                self._create_user_warning()

    def test_passes_when_warnings_test_returns_true(self):
        """
        Test that assert_warns_such_that (used as a context manager)
        passes when the warnings_test method returns True.
        This should happen if warnings is populated correctly.
        """
        def one_user_warning_caught(warnings):
            assert_equal([UserWarning], [w.category for w in warnings])

        with assertions.assert_warns_such_that(one_user_warning_caught):
            self._create_user_warning()

    def test_fails_when_warnings_test_raises_exception_with_callable(self):
        """
        Test that assert_warns_such_that (when given a callable object)
        fails when the warnings_test method raises an exception.
        """
        with assertions.assert_raises(RuntimeError):
            assertions.assert_warns_such_that(self._raise_exception,
                                              self._create_user_warning)

    def test_passes_when_warnings_test_returns_true_with_callable(self):
        """
        Test that assert_warns_such_that (when given a callable object)
        passes when the warnings_test method returns True.
        This should happen if warnings is populated correctly.
        """
        def create_multiple_warnings(warnings_count):
            for _ in range(warnings_count):
                self._create_user_warning()

        three_warnings_caught = lambda warnings: assert_equal(len(warnings), 3)
        assertions.assert_warns_such_that(three_warnings_caught,
                                          create_multiple_warnings, 3)


class DocTest(DocTestCase):
    module = assertions

if __name__ == '__main__':
    run()
# vim:et:sts=4:sw=4:

########NEW FILE########
__FILENAME__ = discovery_failure_test
from __future__ import with_statement

import logging
import os
import tempfile

from testify import TestCase, assert_in, class_setup, class_teardown, run, test_discovery
from testify.test_discovery import DiscoveryError

_log = logging.getLogger('testify')

class BrokenImportTestCase(TestCase):
    __test__ = False

    def create_broken_import_file(self, contents='import non_existent_module'):
        """Write out a test file containing a bad import. This way, a broken
        test isn't lying around to be discovered while running other tests.
        Write the file in the directory containing this test file; otherwise,
        Testify will refuse to import it."""
        here = os.path.dirname(os.path.abspath(__file__))
        (unused_filehandle, self.broken_import_file_path) = tempfile.mkstemp(
            prefix='fake_broken_import',
            suffix='.py',
            dir=here,
        )
        with open(self.broken_import_file_path, 'w') as broken_import_file:
            broken_import_file.write(contents)
        self.broken_import_module = 'test.%s' % os.path.splitext(os.path.basename(self.broken_import_file_path))[0]

    def delete_broken_import_file(self):
        files = [
            self.broken_import_file_path,
            # Also remove the .pyc that was created if the file was imported.
            self.broken_import_file_path + 'c',
        ]
        for f in files:
            try:
                os.remove(f)
            except OSError, exc:
                _log.error("Could not remove broken import file %s: %r" % (f, exc))

    @class_setup
    def setup_import_file(self):
        self.create_broken_import_file()

    @class_teardown
    def teardown_import_file(self):
        self.delete_broken_import_file()


class DiscoveryFailureTestCase(BrokenImportTestCase):
    def test_discover_test_with_broken_import(self):
        """Insure that DiscoveryError is raised when a test which imports a
        non-existent module is discovered."""
        try:
            discovered_tests = test_discovery.discover(self.broken_import_module)
            discovered_tests.next()
        except DiscoveryError, exc:
            assert_in('No module named non_existent_module', str(exc))
        else:
            assert False, 'Expected DiscoveryError.'


class DiscoveryFailureUnknownErrorTestCase(BrokenImportTestCase):
    @class_setup
    def setup_import_file(self):
        self.create_broken_import_file(contents='raise AttributeError("aaaaa!")')

    def test_discover_test_with_unknown_import_error(self):
        """Insure that DiscoveryError is raised when a test which raises an unusual exception upon import is discovered."""

        try:
            discovered_tests = test_discovery.discover(self.broken_import_module)
            discovered_tests.next()
        except DiscoveryError, exc:
            assert_in('Got unknown error when trying to import', str(exc))
        else:
            assert False, 'Expected DiscoveryError.'

if __name__ == '__main__':
    run()

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = failing_test

import testify as T


@T.suite('fake')
class FailingTest(T.TestCase):
    """This is used for an integration test showing failures trigger nonzero
    return values.
    """
    def test_failing(self):
        assert False

########NEW FILE########
__FILENAME__ = json_log_test
import __builtin__
import StringIO
try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

from testify import assert_equal
from testify import run
from testify import setup
from testify import teardown
from testify import test_case
from testify import test_result
from testify.plugins import json_log
from testify.utils import turtle


class JSONReporterTestCase(test_case.TestCase):

    class BaseTestCase(test_case.TestCase):
        def test_method(self):
            return

    BaseTestCase.__module__ = 'base'

    class ExtendedTestCase(BaseTestCase):
        pass

    ExtendedTestCase.__module__ = 'extended'

    extended_test_case = ExtendedTestCase()

    json_reporter_options = turtle.Turtle(json_results_logging=True,
                                          json_results=None,
                                          label=None,
                                          extra_json_info=None,
                                          bucket=None,
                                          bucket_count=None,
                                          verbosity=0)

    @setup
    def setup(self):
        """Monkey patch `open` to point to a `StringIO()` at `self.log_file`
        and create a new `JSONReporter`.
        """
        self._open = __builtin__.open
        self.log_file = StringIO.StringIO()
        # Prevent the mock log file from being closed.
        self._log_file_close = self.log_file.close
        self.log_file.close = lambda: None
        __builtin__.open = lambda *args: self.log_file

        self.json_reporter = json_log.JSONReporter(self.json_reporter_options)

    @teardown
    def teardown(self):
        """Restore `open` and close `self.log_file`."""
        __builtin__.open = self._open

        self.log_file.close = self._log_file_close
        self.log_file.close()

    def test_report_extended_test_module_name(self):
        """When `JSONReporter` logs the results for a test, make sure it
        records the module that the test method's `TestCase` is in, and not the
        module of the `TestCase`'s base class that defined the method.

        Regression test for GitHub #13.
        """

        result = test_result.TestResult(self.extended_test_case.test_method)

        self.json_reporter.test_start(result.to_dict())

        result.start()
        result.end_in_success()

        self.json_reporter.test_complete(result.to_dict())
        assert_equal(True, self.json_reporter.report())

        log_lines = ''.join(line for line in
                            self.log_file.getvalue().splitlines()
                            if line != 'RUN COMPLETE')

        result = json.loads(log_lines)

        assert_equal('extended', result['method']['module'])
        assert_equal('extended ExtendedTestCase.test_method', result['method']['full_name'])


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = mock_logging_test
from __future__ import with_statement

import logging

from testify import assert_equal
from testify import assert_raises
from testify import class_setup
from testify import run
from testify import setup
from testify import TestCase
from testify.utils.mock_logging import MockHandler, mock_logging


class MockHandlerTest(TestCase):
    """Test and verify behaviour of MockHandler.
    """

    @class_setup
    def setup_logger(self):
        self.log = logging.getLogger('mocklogger_test')
        self.handler = MockHandler()
        self.log.handlers = [self.handler]

    @setup
    def clear_logger(self):
        self.handler.clear()

    def test_asserter(self):
        def helper_test_asserts():
            with self.handler.assert_logs():
                pass

        def helper_test_non_asserts():
            with self.log.assert_does_not_log():
                self.log.error("test error message 1")

        def helper_test_asserts_level():
            with self.log.assert_logs(levels=[logging.DEBUG]):
                self.log.log(logging.DEBUG, "test debug message 1")

        with assert_raises(AssertionError):
            with self.handler.assert_logs():
                pass
        with assert_raises(AssertionError):
            with self.handler.assert_does_not_log():
                self.log.error("test error message 2")
        with self.handler.assert_logs(levels=[logging.DEBUG]):
            self.log.debug("test debug message 2")
        with self.handler.assert_does_not_log(levels=[logging.DEBUG]):
            self.log.info("test debug message 3")


class MockLoggingTest(TestCase):
    """Test and verify behaviour of mock_logging context manager.
    """
    def test_mock_logging(self):
        with mock_logging() as mock_handler:
            logging.info("bananas")
            assert_equal(["bananas"], mock_handler.get(logging.INFO))

    def test_specific_mock_logging(self):
        with mock_logging(['mocklogger_test_2']) as mock_handler:
            logging.getLogger('mocklogger_test_2').info('banana1')
            logging.getLogger('mocklogger_test_3').info('banana2')
            assert_equal(["banana1"], mock_handler.get(logging.INFO))


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = http_reporter_test
import threading
import tornado.ioloop
import tornado.httpserver
import tornado.web
import Queue

from test.test_logger_test import ExceptionInClassFixtureSampleTests
from testify import assert_equal, assert_is, setup_teardown, TestCase
from testify.test_runner import TestRunner
from testify.plugins.http_reporter import HTTPReporter

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json


class DummyTestCase(TestCase):
    __test__ = False
    def test(self):
        pass


class HTTPReporterTestCase(TestCase):
    @setup_teardown
    def make_fake_server(self):
        self.results_reported = []
        self.status_codes = Queue.Queue()

        class ResultsHandler(tornado.web.RequestHandler):
            def post(handler):
                result = json.loads(handler.request.body)
                self.results_reported.append(result)

                try:
                    status_code = self.status_codes.get_nowait()
                    handler.send_error(status_code)
                except Queue.Empty:
                    handler.finish("kthx")

            def get_error_html(handler, status, **kwargs    ):
                return "error"

        app = tornado.web.Application([(r"/results", ResultsHandler)])
        srv = tornado.httpserver.HTTPServer(app)
        srv.listen(0)
        portnum = self.get_port_number(srv)

        iol = tornado.ioloop.IOLoop.instance()
        thread = threading.Thread(target=iol.start)
        thread.daemon = True # If for some reason this thread gets blocked, don't prevent quitting.
        thread.start()

        self.connect_addr = "localhost:%d" % portnum

        yield

        iol.stop()
        thread.join()

    def get_port_number(self, server):
        if hasattr(server, "_sockets"): # tornado > 2.0
            _socket = server._sockets.values()[0]
        else: # tornado 1.2 or earlier
            _socket = server._socket
        return _socket.getsockname()[1]

    def test_http_reporter_reports(self):
        """A simple test to make sure the HTTPReporter actually reports things."""

        runner = TestRunner(DummyTestCase, test_reporters=[HTTPReporter(None, self.connect_addr, 'runner1')])
        ret = runner.run()
        assert_is(ret, True)

        (method_result, test_case_result) = self.results_reported
        assert_equal(method_result['runner_id'], 'runner1')
        assert_equal(method_result['method']['class'], 'DummyTestCase')
        assert_equal(method_result['method']['name'], 'test')

    def test_http_reporter_tries_twice(self):
        self.status_codes.put(409)
        self.status_codes.put(409)

        runner = TestRunner(DummyTestCase, test_reporters=[HTTPReporter(None, self.connect_addr, 'tries_twice')])
        runner.run()

        (first, second, test_case_result) = self.results_reported

        assert_equal(first['runner_id'], 'tries_twice')
        assert_equal(first, second)

    def test_http_reporter_completed_test_case(self):
        runner = TestRunner(DummyTestCase, test_reporters=[HTTPReporter(None, self.connect_addr, 'runner1')])
        runner.run()

        (test_method_result, test_case_result) = self.results_reported
        assert_equal(test_case_result['method']['name'], 'run')

    def test_http_reporter_class_teardown_exception(self):
        runner = TestRunner(ExceptionInClassFixtureSampleTests.FakeClassTeardownTestCase, test_reporters=[HTTPReporter(None, self.connect_addr, 'runner1')])
        runner.run()

        (test1_method_result, test2_method_result, class_teardown_result, test_case_result) = self.results_reported
        assert_equal(test_case_result['method']['name'], 'run')


# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = sql_reporter_test
from mock import patch
import time
from optparse import OptionParser

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

SA = None
try:
    import sqlalchemy as SA
except ImportError:
    pass

from test.discovery_failure_test import BrokenImportTestCase
from test.test_logger_test import ExceptionInClassFixtureSampleTests
from test.test_case_test import RegexMatcher
from testify import TestCase, assert_equal, assert_gt, assert_in,  assert_in_range, setup_teardown
from testify.plugins.sql_reporter import add_command_line_options, SQLReporter
from testify.test_result import TestResult
from testify.test_runner import TestRunner

class DummyTestCase(TestCase):
    __test__ = False
    def test_pass(self):
        pass

    def test_fail(self):
        assert False

    def test_multiline(self):
        raise Exception("""I love lines:
    1
        2
            3""")

class SQLReporterBaseTestCase(TestCase):
    __test__ = False

    @setup_teardown
    def make_reporter(self):
        """Make self.reporter, a SQLReporter that runs on an empty in-memory SQLite database."""
        if not SA:
            msg = 'SQL Reporter plugin requires sqlalchemy and you do not have it installed in your PYTHONPATH.\n'
            raise ImportError, msg

        parser = OptionParser()
        add_command_line_options(parser)
        self.fake_buildbot_run_id = 'A' * 36
        (options, args) = parser.parse_args([
            '--reporting-db-url', 'sqlite://',
            '--sql-reporting-frequency', '0.05',
            '--build-info', json.dumps({
                'buildbot' : 1,
                'buildnumber' : 1,
                'buildbot_run_id': self.fake_buildbot_run_id,
                'branch' : 'a_branch_name',
                'revision' : 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
                'buildname' : 'a_build_name'
            })
        ])
        create_engine_opts = {
            'poolclass' : SA.pool.StaticPool,
            'connect_args' : {'check_same_thread' : False}
        }

        self.reporter = SQLReporter(options, create_engine_opts=create_engine_opts)

        yield
        # no teardown.

    def _get_test_results(self, conn):
        """Return a list of tests and their results from SA connection `conn`."""
        return list(conn.execute(SA.select(
            columns=(
                self.reporter.TestResults,
                self.reporter.Tests,
                self.reporter.Failures,
            ),
            from_obj=self.reporter.TestResults.join(
                self.reporter.Tests,
                self.reporter.TestResults.c.test == self.reporter.Tests.c.id
            ).outerjoin(
                self.reporter.Failures,
                self.reporter.TestResults.c.failure == self.reporter.Failures.c.id
            )
        )))


class SQLReporterTestCase(SQLReporterBaseTestCase):
    def test_integration(self):
        """Run a runner with self.reporter as a test reporter, and verify a bunch of stuff."""
        runner = TestRunner(DummyTestCase, test_reporters=[self.reporter])
        conn = self.reporter.conn

        # We're creating a new in-memory database in make_reporter, so we don't need to worry about rows from previous tests.
        (build,) = list(conn.execute(self.reporter.Builds.select()))

        assert_equal(build['buildname'], 'a_build_name')
        assert_equal(build['branch'], 'a_branch_name')
        assert_equal(build['revision'], 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
        assert_equal(build['buildbot_run_id'], self.fake_buildbot_run_id)

        # Method count should be None until we discover (which is part of running)
        assert_equal(build['method_count'], None)
        # End time should be None until we run.
        assert_equal(build['end_time'], None)

        assert runner.run()

        # Now that we've run the tests, get the build row again and check to see that things are updated.
        (updated_build,) = list(conn.execute(self.reporter.Builds.select()))

        for key in updated_build.keys():
            if key not in ('end_time', 'run_time', 'method_count'):
                assert_equal(build[key], updated_build[key])

        assert_gt(updated_build['run_time'], 0)
        assert_in_range(updated_build['end_time'], 0, time.time())
        assert_equal(updated_build['method_count'], 3)

        # The discovery_failure column should exist and be False.
        assert 'discovery_failure' in build
        assert_equal(build['discovery_failure'], False)

        # Check test results.
        test_results = self._get_test_results(conn)
        assert_equal(len(test_results), 3)

        # Check that we have one failure and one pass, and that they're the right tests.
        (passed_test,) = [r for r in test_results if not r['failure']]
        (failed_test, failed_test_2) = [r for r in test_results if r['failure']]

        assert_equal(passed_test['method_name'], 'test_pass')
        assert_equal(passed_test.traceback, None)
        assert_equal(passed_test.error, None)

        assert_equal(failed_test['method_name'], 'test_fail')
        assert_equal(failed_test.traceback.split('\n'), [
            'Traceback (most recent call last):',
            RegexMatcher('  File "(\./)?test/plugins/sql_reporter_test\.py", line \d+, in test_fail'),
            '    assert False',
            'AssertionError',
            '' # ends with newline
        ])
        assert_equal(failed_test.error, 'AssertionError')

        assert_equal(failed_test_2['method_name'], 'test_multiline')
        assert_equal(failed_test_2.traceback.split('\n'), [
            'Traceback (most recent call last):',
            RegexMatcher('  File "(\./)?test/plugins/sql_reporter_test\.py", line \d+, in test_multiline'),
            '    3""")',
            'Exception: I love lines:',
            '    1',
            '        2',
            '            3',
            '' # ends with newline
        ])
        assert_equal(failed_test_2.error, 'Exception: I love lines:\n    1\n        2\n            3')



    def test_update_counts(self):
        """Tell our SQLReporter to update its counts, and check that it does."""
        conn = self.reporter.conn

        (build,) = list(conn.execute(self.reporter.Builds.select()))

        assert_equal(build['method_count'], None)

        self.reporter.test_counts(3, 50)
        (updated_build,) = list(conn.execute(self.reporter.Builds.select()))

        assert_equal(updated_build['method_count'], 50)

    def test_previous_run(self):
        """Insert a test result with two previous runs, and make sure it works properly."""
        conn = self.reporter.conn

        test_case = DummyTestCase()
        results = [TestResult(test_case.test_pass) for _ in xrange(3)]

        previous_run = None
        for result in results:
            if previous_run:
                result.start(previous_run=previous_run.to_dict())
            else:
                result.start()

            result.end_in_success()
            previous_run = result

        self.reporter.test_complete(results[-1].to_dict())

        assert self.reporter.report() # Make sure all results are inserted.

        test_results = self._get_test_results(conn)
        assert_equal(len(test_results), 3)

        for result in test_results:
            assert_equal(result['method_name'], 'test_pass')

    def test_traceback_size_limit(self):
        """Insert a failure with a long exception and make sure it gets truncated."""
        conn = self.reporter.conn

        test_case = DummyTestCase()
        result = TestResult(test_case.test_fail)
        result.start()
        result.end_in_failure((type(AssertionError), AssertionError('A' * 200), None))

        with patch.object(self.reporter.options, 'sql_traceback_size', 50):
            with patch.object(result, 'format_exception_info') as mock_format_exception_info:
                mock_format_exception_info.return_value = "AssertionError: %s\n%s\n" % ('A' * 200, 'A' * 200)

                self.reporter.test_complete(result.to_dict())

            assert self.reporter.report()

        failure = conn.execute(self.reporter.Failures.select()).fetchone()
        assert_equal(len(failure.traceback), 50)
        assert_equal(len(failure.error), 50)
        assert_in('Exception truncated.', failure.traceback)
        assert_in('Exception truncated.', failure.error)


class SQLReporterDiscoveryFailureTestCase(SQLReporterBaseTestCase, BrokenImportTestCase):
    def test_sql_reporter_sets_discovery_failure_flag(self):
        runner = TestRunner(self.broken_import_module, test_reporters=[self.reporter])
        runner.run()

        conn = self.reporter.conn
        (build,) = list(conn.execute(self.reporter.Builds.select()))

        assert_equal(build['discovery_failure'], True)
        assert_equal(build['method_count'], 0)


class SQLReporterExceptionInClassFixtureTestCase(SQLReporterBaseTestCase):
    def test_setup(self):
        runner = TestRunner(ExceptionInClassFixtureSampleTests.FakeClassSetupTestCase, test_reporters=[self.reporter])
        runner.run()

        conn = self.reporter.conn

        test_results = self._get_test_results(conn)
        assert_equal(len(test_results), 2)

        # Errors in class_setup methods manifest as errors in the test case's
        # test methods.
        for result in test_results:
            assert_equal(
                result['failure'],
                True,
                'Unexpected success for %s.%s' % (result['class_name'], result['method_name'])
            )

        failures = conn.execute(self.reporter.Failures.select()).fetchall()
        for failure in failures:
            assert_in('in class_setup_raises_exception', failure.traceback)


    def test_teardown(self):
        runner = TestRunner(ExceptionInClassFixtureSampleTests.FakeClassTeardownTestCase, test_reporters=[self.reporter])
        runner.run()

        conn = self.reporter.conn

        test_results = self._get_test_results(conn)
        assert_equal(len(test_results), 3)

        # Errors in class_teardown methods manifest as an additional test
        # result.
        class_teardown_result = test_results[-1]
        assert_equal(
            class_teardown_result['failure'],
            True,
            'Unexpected success for %s.%s' % (class_teardown_result['class_name'], class_teardown_result['method_name'])
        )

        failure = conn.execute(self.reporter.Failures.select()).fetchone()
        assert_in('in class_teardown_raises_exception', failure.traceback)


class SQLReporterTestCompleteIgnoresResultsForRun(SQLReporterBaseTestCase):
    def test_test_complete(self):
        assert_equal(self.reporter.result_queue.qsize(), 0)

        test_case = DummyTestCase()
        fake_test_result = TestResult(test_case.run)
        self.reporter.test_complete(fake_test_result.to_dict())

        assert_equal(self.reporter.result_queue.qsize(), 0)


class SQLReporterReportResultsByChunk(SQLReporterBaseTestCase):
    def test_happy_path(self):
        conn = self.reporter.conn
        test_case = DummyTestCase()
        results = [
            TestResult(test_case.test_pass),
            TestResult(test_case.test_fail),
        ]
        chunk = []
        for result in results:
            result.start()
            result.end_in_success()
            chunk.append(result.to_dict())

        # In production, Someone Else takes care of manipulating the reporter's
        # result_queue. We'll just mock the method we care about to avoid
        # violating the Law of Demeter.
        with patch.object(self.reporter.result_queue, 'task_done') as mock_task_done:
            self.reporter._report_results_by_chunk(conn, chunk)
            assert_equal(len(results), mock_task_done.call_count)

        test_results = self._get_test_results(conn)
        assert_equal(len(results), len(test_results))


# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = violation_collector_test
import contextlib
import os
import socket
import tempfile
import time

catbox = None
try:
    import catbox
except ImportError:
    pass

SA = None
try:
    import sqlalchemy as SA
except ImportError:
    pass

import mock

import testify as T

from testify.plugins.violation_collector import ctx

from testify.plugins.violation_collector import cleandict
from testify.plugins.violation_collector import collect
from testify.plugins.violation_collector import get_db_url
from testify.plugins.violation_collector import is_sqlite_filepath
from testify.plugins.violation_collector import run_in_catbox
from testify.plugins.violation_collector import sqlite_dbpath
from testify.plugins.violation_collector import writeln

from testify.plugins.violation_collector import ViolationReporter
from testify.plugins.violation_collector import ViolationStore

from testify.plugins.violation_collector import TEST_METHOD_TYPE


@contextlib.contextmanager
def mocked_ctx():
    with mock.patch('testify.plugins.violation_collector.ctx') as mock_ctx:
        yield mock_ctx


@contextlib.contextmanager
def mocked_store():
    def mock_init_database(obj):
        obj.metadata = mock.MagicMock()
        obj.Violations = mock.MagicMock()
        obj.Methods = mock.MagicMock()

    with mock.patch('testify.plugins.violation_collector.SA'):
        mock_options = mock.Mock()
        mock_options.violation_dburl = "fake db url"
        mock_options.violation_dbconfig = None
        mock_options.build_info = None

        # we're doing our own method paching here because
        # mock.patch.object's side_effect functions are not passed in
        # the object.
        original_init_database = ViolationStore.init_database
        ViolationStore.init_database = mock_init_database
        yield ViolationStore(mock_options)
        ViolationStore.init_database = original_init_database


@contextlib.contextmanager
def sqlite_store():
    test_violations_file = "test_violations.sqlite"
    mock_options = mock.Mock()
    mock_options.violation_dburl = "sqlite:///%s" % test_violations_file
    mock_options.violation_dbconfig = None
    mock_options.build_info = None

    yield ViolationStore(mock_options)

    os.unlink(test_violations_file)


@contextlib.contextmanager
def mocked_reporter(store):
    mock_options = mock.Mock()
    reporter = ViolationReporter(mock_options, store)
    yield reporter


class HelperFunctionsTestCase(T.TestCase):
    def test_get_db_url_with_dburl(self):
        options = mock.Mock()
        options.violation_dburl = 'sqlite:///fake/database'
        options.violation_dbconfig = None
        T.assert_equal(get_db_url(options), options.violation_dburl)

    def test_get_db_url_with_dbconfig(self):
        options = mock.Mock()
        options.violation_dburl = 'sqlite:///fake/database'
        options.violation_dbconfig = '/fake/path/to/db/'

        mocked_open = mock.Mock(spec=file)
        mocked_open.__enter__ = mock.Mock()
        mocked_open.__exit__ = mock.Mock()
        with mock.patch(
            'testify.plugins.violation_collector.open',
            create=True,
            return_value=mocked_open
        ):
            with mock.patch.object(SA.engine.url, 'URL') as mocked_sa_url:
                T.assert_not_equal(get_db_url(options), options.violation_dburl)
                mocked_open.read.assert_called
                mocked_sa_url.URL.assert_called

    def test_is_sqliteurl(self):
        assert is_sqlite_filepath("sqlite:///")
        assert is_sqlite_filepath("sqlite:///test.db")
        assert is_sqlite_filepath("sqlite:////tmp/test-database.sqlite")

        sa_engine_url = SA.engine.url.URL(drivername='mysql', host='fakehost', database='fakedb')
        T.assert_equal(is_sqlite_filepath(sa_engine_url), False)

    def test_sqlite_dbpath(self):
        T.assert_equal(sqlite_dbpath("sqlite:///test.sqlite"), os.path.abspath("test.sqlite"))
        T.assert_equal(sqlite_dbpath("sqlite:////var/tmp/test.sqlite"), "/var/tmp/test.sqlite")

    def test_cleandict(self):
        dirty_dict = {'a': 1, 'b': 2, 'c': 3}
        clean_dict = {'a': 1}
        T.assert_equal(cleandict(dirty_dict, allowed_keys=['a']), clean_dict)

    def test_collect(self):
        with mocked_ctx() as mock_ctx:
            fake_time = 10
            with mock.patch.object(time, 'time', return_value=fake_time):
                fake_violation = "fake_violation1"
                fake_resolved_path = "fake_resolved_path"
                collect(fake_violation, "", fake_resolved_path)

                fake_violation_data = {
                    'syscall': fake_violation,
                    'syscall_args': fake_resolved_path,
                    'start_time': fake_time
                }
                mock_ctx.store.add_violation.assert_called_with(fake_violation_data)


    def test_run_in_catbox(self):
        with mock.patch('testify.plugins.violation_collector.catbox') as mock_catbox:
            mock_method = mock.Mock()
            mock_logger = mock.Mock()
            mock_paths = mock.Mock()

            run_in_catbox(mock_method, mock_logger, mock_paths)

            mock_catbox.run.assert_called_with(
                mock_method,
                collect_only=True,
                network=False,
                logger=mock_logger,
                writable_paths=mock_paths,
            )

    def test_writeln_with_default_verbosity(self):
        with mocked_ctx() as mctx:
            msg = "test message"

            writeln(msg)

            mctx.output_stream.write.assert_called_with(msg + "\n")
            assert mctx.output_stream.flush.called

    def test_writeln_with_verbosity_silent(self):
        with mocked_ctx() as mctx:
            # when ctx.output_verbosity is defined as silent and we
            # want to write a message in in VERBOSITY_SILENT, we
            # should still see the message.
            verbosity = T.test_logger.VERBOSITY_SILENT
            mctx.output_verbosity = T.test_logger.VERBOSITY_SILENT
            msg = "test message"

            writeln(msg, verbosity)

            mctx.output_stream.write.assert_called_with(msg + "\n")
            assert mctx.output_stream.flush.called

    def test_writeln_with_verbosity_verbose(self):
        with mocked_ctx() as mctx:
            # should see verbose messages in a verbose context.
            verbosity = T.test_logger.VERBOSITY_VERBOSE
            msg = "test message"
            mctx.output_verbosity = verbosity

            writeln(msg, verbosity)

            mctx.output_stream.write.assert_called_with(msg + "\n")
            assert mctx.output_stream.flush.called

    def test_writeln_with_verbosity_verbose_in_silent_context(self):
        with mocked_ctx() as mctx:
            # when the context is defined as silent, verbose level
            # messages should be ignored.
            mctx.output_verbosity = T.test_logger.VERBOSITY_SILENT
            msg = "test message"

            writeln(msg, T.test_logger.VERBOSITY_VERBOSE)

            T.assert_equal(mctx.output_stream.flush.called, False)


class ViolationReporterTestCase(T.TestCase):

    @T.setup_teardown
    def setup_reporter(self):
        self.mock_result = mock.MagicMock()
        result_attrs = {
            'method' : 'mock_method',
            'class'  : 'mock_class',
            'name'   : 'mock_name',
            'module' : 'mock_module',
        }
        self.mock_result.configure_mocks(**result_attrs)
        store = mock.Mock()
        with mocked_reporter(store) as reporter:
            self.mock_store = store
            reporter.options.disable_violations_summary = False
            self.reporter = reporter
            yield

    @T.setup
    def setup_fake_violations(self):
        self.fake_violations = [
            ('fake_class1', 'fake_method1', 'fake_violation1', 5),
            ('fake_class1', 'fake_method2', 'fake_violation2', 5),
            ('fake_class2', 'fake_method3', 'fake_violation3', 5),
            ('fake_class3', 'fake_method4', 'fake_violation1', 5),
        ]

    def test_test_case_start(self):
        self.reporter.test_case_start(self.mock_result)
        assert self.mock_store.add_method.called

    def test_test_start(self):
        self.reporter.test_start(self.mock_result)
        assert self.mock_store.add_method.called

    def test_class_setup_start(self):
        self.reporter.class_setup_start(self.mock_result)
        assert self.mock_store.add_method.called

    def test_class_teardown_start(self):
        self.reporter.class_teardown_start(self.mock_result)
        assert self.mock_store.add_method.called

    def test_get_syscall_count(self):
        T.assert_equal(
            self.reporter.get_syscall_count(self.fake_violations),
            [('fake_violation2', 5), ('fake_violation3', 5), ('fake_violation1', 10)]
        )

    def test_get_violations_count(self):
        syscall_violation_counts = self.reporter.get_syscall_count(self.fake_violations)
        T.assert_equal(
            self.reporter.get_violations_count(syscall_violation_counts),
            sum(count for violating_class, violating_method, violation, count in self.fake_violations)
        )

    def test_report_with_no_violations(self):
        with mock.patch('testify.plugins.violation_collector.writeln') as mock_writeln:
            self.mock_store.violation_counts.return_value = []

            self.reporter.report()

            mock_writeln.assert_called_with(
                "No syscall violations! \o/\n",
                T.test_logger.VERBOSITY_NORMAL
            )

    def test_report_with_violations(self):
        with mocked_ctx() as mctx:
            mctx.output_verbosity = T.test_logger.VERBOSITY_VERBOSE
            fake_violation = [
                ('fake_class1', 'fake_method1', 'fake_violation1', 5),
            ]
            self.mock_store.violation_counts.return_value = fake_violation

            self.reporter.report()
            mctx.output_stream.write.assert_called_with("%s.%s\t%s\t%s\n" % fake_violation[0])

    def test_report_with_violations_summary_disabled(self):
        with mocked_ctx() as mctx:
            # reporter is created in a setup method and safe to alter
            self.reporter.options.disable_violations_summary = True

            mctx.output_verbosity = T.test_logger.VERBOSITY_VERBOSE
            fake_violation = [
                ('fake_class1', 'fake_method1', 'fake_violation1', 5),
            ]
            self.mock_store.violation_counts.return_value = fake_violation

            self.reporter.report()
            T.assert_equal(mctx.output_stream.write.called, False)


@T.suite("catbox")
class ViolationStoreTestCase(T.TestCase):

    def test_violation_store_does_not_connect_db_when_initialized(self):
        with mocked_store() as mock_store:
            T.assert_equal(mock_store.engine, None)
            T.assert_equal(mock_store.conn, None)

    def test_add_method(self):
        with mocked_store() as mock_store:
            mock_store._set_last_test_id = mock.Mock()
            mock_store.add_method("fake_module", "fake_class", "fake_method", TEST_METHOD_TYPE)

            assert mock_store.engine.connect.called
            assert mock_store.conn.execute.called
            assert mock_store.Methods.insert.called

    def test_add_violation(self):
        with mocked_store() as mock_store:
            fake_test_id = 1
            fake_violation = mock.Mock()
            mock_store.get_last_test_id = mock.Mock()
            mock_store.get_last_test_id.return_value = fake_test_id

            mock_store.add_violation(fake_violation)

            call_to_violation_update = fake_violation.update.call_args[0]
            first_arg_to_violation_update = call_to_violation_update[0]
            T.assert_equal(first_arg_to_violation_update, {'test_id': fake_test_id})

            assert mock_store.engine.connect.called
            assert mock_store.conn.execute.called
            assert mock_store.Violations.insert.called


@T.suite("catbox")
class ViolationCollectorPipelineTestCase(T.TestCase):

    class ViolatingTestCase(T.TestCase):
        def make_filesystem_violation(self, suffix):
            fd, fpath = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            os.unlink(fpath)

        def make_network_violation(self):
            s = socket.socket()
            s.connect(("127.0.0.1", 80))
            s.close()

        def test_filesystem_violation(self):
            self.make_filesystem_violation("fake_testfile")

        def test_network_violation(self):
            self.make_network_violation()

    class ViolatingTestCaseWithSetupAndTeardown(ViolatingTestCase):

        @T.setup
        def __setup(self):
            self.make_filesystem_violation("fake_testcase_setup")

        @T.teardown
        def __teardown(self):
            self.make_filesystem_violation("fake_testcase_teardown")

    class ViolatingTestCaseWithClassSetupAndTeardown(ViolatingTestCase):

        @T.class_setup
        def __class_setup(self):
            self.make_filesystem_violation("fake_testcase_class_setup")

        @T.class_teardown
        def __class_teardown(self):
            self.make_filesystem_violation("fake_testcase_class_teardown")

    @contextlib.contextmanager
    def run_testcase_in_catbox(self, test_case):
        if not catbox:
            msg = 'Violation collection pipeline tests require catbox.\n'
            msg_pcre = 'https://github.com/Yelp/catbox/wiki/Install-Catbox-with-PCRE-enabled\n'
            raise ImportError, msg + msg_pcre

        with sqlite_store() as store:
            with mocked_reporter(store) as reporter:
                ctx.store = store

                # Runing the test case inside catbox, we'll catch
                # violating syscalls and catbox will call our logger
                # function (collect)
                runner = T.test_runner.TestRunner(test_case, test_reporters=[reporter])
                run_in_catbox(runner.run, collect, [])

                yield store.violation_counts()

                ctx.store = None

    def test_catbox_methods_inserts(self):
        with self.run_testcase_in_catbox(self.ViolatingTestCase):
            query = SA.sql.select([
                ctx.store.Methods.c.class_name,
                ctx.store.Methods.c.method_name,
                ctx.store.Methods.c.method_type,
            ]).where(
                SA.and_(
                    ctx.store.Methods.c.class_name == 'ViolatingTestCase',
                    ctx.store.Methods.c.method_name == 'test_filesystem_violation',
                    ctx.store.Methods.c.method_type == TEST_METHOD_TYPE,
                )
            )
            result = ctx.store.conn.execute(query).fetchone()
            T.assert_equal(result, ('ViolatingTestCase', 'test_filesystem_violation', TEST_METHOD_TYPE))

    def test_catbox_violations_inserts(self):
        with self.run_testcase_in_catbox(self.ViolatingTestCase):
            query = SA.sql.select([
                ctx.store.Violations.c.syscall,
            ]).where(
                ctx.store.Violations.c.syscall == 'socketcall',
            )
            result = ctx.store.conn.execute(query).fetchall()
            T.assert_equal(len(result), 1)

    def test_violation_collector_pipeline(self):
        with self.run_testcase_in_catbox(self.ViolatingTestCase) as violations:
            T.assert_in(
                (u'ViolatingTestCase', u'test_network_violation', u'socketcall', 1),
                violations
            )
            T.assert_in(
                (u'ViolatingTestCase', u'test_filesystem_violation', u'unlink', 2),
                violations
            )
            T.assert_in(
                (u'ViolatingTestCase', u'test_filesystem_violation', u'open', 2),
                violations
            )

    def test_violation_collector_pipeline_with_fixtures(self):
        with self.run_testcase_in_catbox(self.ViolatingTestCaseWithSetupAndTeardown) as violations:
            # setup/teardown fixtures will bump the unlink count for test_filesystem_violation by 2
            T.assert_in(
                (u'ViolatingTestCaseWithSetupAndTeardown', u'test_filesystem_violation', u'unlink', 4),
                violations
            )
            # setup/teardown fixtures will bump the open count for test_filesystem_violation by 2
            T.assert_in(
                (u'ViolatingTestCaseWithSetupAndTeardown', u'test_filesystem_violation', u'open', 4),
                violations
            )

    def test_violation_collector_pipeline_with_class_level_fixtures(self):
        with self.run_testcase_in_catbox(self.ViolatingTestCaseWithClassSetupAndTeardown) as violations:
            T.assert_in(
                (u'ViolatingTestCaseWithClassSetupAndTeardown', u'__class_setup', u'open', 2),
                violations
            )
            T.assert_in(
                (u'ViolatingTestCaseWithClassSetupAndTeardown', u'__class_setup', u'unlink', 2),
                violations
            )
            T.assert_in(
                (u'ViolatingTestCaseWithClassSetupAndTeardown', u'__class_teardown', u'open', 1),
                violations
            )
            T.assert_in(
                (u'ViolatingTestCaseWithClassSetupAndTeardown', u'__class_teardown', u'unlink', 1),
                violations
            )

if __name__ == '__main__':
    T.run()

########NEW FILE########
__FILENAME__ = test_case_test
import unittest

from testify import assert_equal
from testify import assert_in
from testify import class_setup
from testify import class_setup_teardown
from testify import class_teardown
from testify import let
from testify import run
from testify import setup
from testify import teardown
from testify import TestCase
from testify import test_runner


class TestMethodsGetRun(TestCase):
    def test_method_1(self):
        self.test_1_run = True

    def test_method_2(self):
        self.test_2_run = True

    @class_teardown
    def assert_test_methods_were_run(self):
        assert self.test_1_run
        assert self.test_2_run


class DeprecatedClassSetupFixturesGetRun(TestCase):
    def classSetUp(self):
        self.test_var = True

    def test_test_var(self):
        assert self.test_var


class DeprecatedSetupFixturesGetRun(TestCase):
    def setUp(self):
        self.test_var = True

    def test_test_var(self):
        assert self.test_var


class DeprecatedTeardownFixturesGetRun(TestCase):
    COUNTER = 0

    def tearDown(self):
        self.test_var = True

    def test_test_var_pass_1(self):
        self.COUNTER += 1
        if self.COUNTER > 1:
            assert self.test_var

    def test_test_var_pass_2(self):
        self.COUNTER += 1
        if self.COUNTER > 1:
            assert self.test_var


class DeprecatedClassTeardownFixturesGetRun(TestCase):
    def test_placeholder(self):
        pass

    def class_teardown(self):
        self.test_var = True

    @class_teardown
    def test_test_var(self):
        assert self.test_var


class ClassSetupFixturesGetRun(TestCase):
    @class_setup
    def set_test_var(self):
        self.test_var = True

    def test_test_var(self):
        assert self.test_var


class SetupFixturesGetRun(TestCase):
    @setup
    def set_test_var(self):
        self.test_var = True

    def test_test_var(self):
        assert self.test_var


class TeardownFixturesGetRun(TestCase):
    COUNTER = 0

    @teardown
    def set_test_var(self):
        self.test_var = True

    def test_test_var_first_pass(self):
        self.COUNTER += 1
        if self.COUNTER > 1:
            assert self.test_var

    def test_test_var_second_pass(self):
        self.COUNTER += 1
        if self.COUNTER > 1:
            assert self.test_var


class OverrideTest(TestCase):
    def test_method_1(self):
        pass

    def test_method_2(self):
        pass


class UnitTest(unittest.TestCase):
    # a compact way to record each step's completion
    status = [False] * 6

    def classSetUp(self):
        self.status[0] = True

    def setUp(self):
        self.status[1] = True

    def test_i_ran(self):
        self.status[2] = True

    def tearDown(self):
        self.status[3] = True

    def classTearDown(self):
        self.status[4] = True

    @teardown
    def no_really_i_tore_down(self):
        """Fixture mixins should still work as expected."""
        self.status[5] = True


class UnitTestUntested(UnitTest):
    __test__ = False
    status = [False] * 6


class UnitTestTestYoDawg(TestCase):
    """Make sure we actually detect and run all steps in unittest.TestCases."""
    def test_unit_test_status(self):
        runner = test_runner.TestRunner(UnitTest)
        assert runner.run()
        assert UnitTest.status == [True] * 6, UnitTest.status

        runner = test_runner.TestRunner(UnitTestUntested)
        assert runner.run()
        assert UnitTestUntested.status == [False] * 6, UnitTestUntested.status

# The following cases test unittest.TestCase inheritance, fixtures and mixins

class BaseUnitTest(unittest.TestCase):
    done = False

    def __init__(self):
        super(BaseUnitTest, self).__init__()
        self.init = True

    def setUp(self):
        assert self.init
        assert not self.done
        self.foo = True

    def tearDown(self):
        assert self.init
        assert not self.done
        self.done = True


class DoNothingMixin(object):
    pass


class DerivedUnitTestMixinWithFixture(BaseUnitTest):
    @setup
    def set_bar(self):
        assert self.foo # setUp runs first
        self.bar = True

    @teardown
    def not_done(self): # tearDown runs last
        assert not self.done

    @class_teardown
    def i_ran(cls):
        cls.i_ran = True


class DerivedUnitTestWithFixturesAndTests(DerivedUnitTestMixinWithFixture, DoNothingMixin):
    def test_foo_bar(self):
        assert self.foo
        assert self.bar
        assert not self.done


class DerivedUnitTestWithAdditionalFixturesAndTests(DerivedUnitTestMixinWithFixture):
    @setup
    def set_baz(self):
        assert self.foo
        assert self.bar
        self.baz = True

    @teardown
    def clear_foo(self):
        self.foo = False

    def test_foo_bar_baz(self):
        assert self.foo
        assert self.bar
        assert self.baz


class TestDerivedUnitTestsRan(TestCase):
    def test_unit_tests_ran(self):
        assert DerivedUnitTestMixinWithFixture.i_ran
        assert DerivedUnitTestWithFixturesAndTests.i_ran
        assert DerivedUnitTestWithAdditionalFixturesAndTests.i_ran


class ClobberLetTest(TestCase):
    """Test overwritting a let does not break subsequent tests.

    Because we are unsure which test will run first, two tests will clobber a
    let that is asserted about in the other test.
    """

    @let
    def something(self):
        return 1

    @let
    def something_else(self):
        return 2

    def test_something(self):
        self.something_else = 3
        assert_equal(self.something, 1)

    def test_something_else(self):
        self.something = 4
        assert_equal(self.something_else, 2)


class CallbacksGetCalledTest(TestCase):
    def test_class_fixtures_get_reported(self):
        """Make a test case, register a bunch of callbacks for class fixtures on it, and make sure the callbacks are all run in the right order."""
        class InnerTestCase(TestCase):
            def classSetUp(self):
                pass

            def classTearDown(self):
                pass

            @class_setup_teardown
            def __class_setup_teardown(self):
                yield

            def test_things(self):
                pass

        inner_test_case = InnerTestCase()
        events = (
            TestCase.EVENT_ON_RUN_TEST_METHOD,
            TestCase.EVENT_ON_COMPLETE_TEST_METHOD,
            TestCase.EVENT_ON_RUN_CLASS_SETUP_METHOD,
            TestCase.EVENT_ON_COMPLETE_CLASS_SETUP_METHOD,
            TestCase.EVENT_ON_RUN_CLASS_TEARDOWN_METHOD,
            TestCase.EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD,
            TestCase.EVENT_ON_RUN_TEST_CASE,
            TestCase.EVENT_ON_COMPLETE_TEST_CASE,
        )

        calls_to_callback = []
        def make_callback(event):
            def callback(result):
                calls_to_callback.append((event, result['method']['name'] if result else None))
            return callback

        for event in events:
            inner_test_case.register_callback(event, make_callback(event))

        inner_test_case.run()

        assert_equal(calls_to_callback, [
            (TestCase.EVENT_ON_RUN_TEST_CASE, 'run'),

            (TestCase.EVENT_ON_RUN_CLASS_SETUP_METHOD, 'classSetUp'),
            (TestCase.EVENT_ON_COMPLETE_CLASS_SETUP_METHOD, 'classSetUp'),

            (TestCase.EVENT_ON_RUN_CLASS_SETUP_METHOD, '__class_setup_teardown'),
            (TestCase.EVENT_ON_COMPLETE_CLASS_SETUP_METHOD, '__class_setup_teardown'),

            (TestCase.EVENT_ON_RUN_TEST_METHOD, 'test_things'),
            (TestCase.EVENT_ON_COMPLETE_TEST_METHOD, 'test_things'),

            (TestCase.EVENT_ON_RUN_CLASS_TEARDOWN_METHOD, '__class_setup_teardown'),
            (TestCase.EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD, '__class_setup_teardown'),

            (TestCase.EVENT_ON_RUN_CLASS_TEARDOWN_METHOD, 'classTearDown'),
            (TestCase.EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD, 'classTearDown'),

            (TestCase.EVENT_ON_COMPLETE_TEST_CASE, 'run'),
        ])


class FailingTeardownMethodsTest(TestCase):

    class ClassWithTwoFailingTeardownMethods(TestCase):

        methods_ran = []

        def test_method(self):
            self.methods_ran.append("test_method")
            assert False

        @teardown
        def first_teardown(self):
            self.methods_ran.append("first_teardown")
            assert False

        @teardown
        def second_teardown(self):
            self.methods_ran.append("second_teardown")
            assert False

    @setup
    def run_test_case(self):
        self.testcase = self.ClassWithTwoFailingTeardownMethods()
        self.testcase.run()

    def test_class_with_two_failing_teardown_methods(self):
        assert_in("test_method", self.testcase.methods_ran)
        assert_in("first_teardown", self.testcase.methods_ran)
        assert_in("second_teardown", self.testcase.methods_ran)

    def test_multiple_error_formatting(self):
        test_result = self.testcase.results()[0]
        assert_equal(
            test_result.format_exception_info().split('\n'),
            [
                'Traceback (most recent call last):',
                RegexMatcher('  File "(\./)?test/test_case_test\.py", line \d+, in test_method'),
                '    assert False',
                'AssertionError',
                '',
                'During handling of the above exception, another exception occurred:',
                '',
                'Traceback (most recent call last):',
                RegexMatcher('  File "(\./)?test/test_case_test\.py", line \d+, in first_teardown'),
                '    assert False',
                'AssertionError',
                '',
                'During handling of the above exception, another exception occurred:',
                '',
                'Traceback (most recent call last):',
                RegexMatcher('  File "(\./)?test/test_case_test\.py", line \d+, in second_teardown'),
                '    assert False',
                'AssertionError',
                '', # Ends with newline.
            ]
        )

class RegexMatcher(object):
    def __init__(self, regex):
        import re
        self.__re = re.compile(regex)
    def __eq__(self, other):
        return bool(self.__re.match(other))
    def __repr__(self):
        return '%s(%r)' % (
                type(self).__name__,
                self.__re.pattern,
        )


class ExceptionDuringClassSetupTest(TestCase):

    class FakeParentTestCase(TestCase):

        def __init__(self, *args, **kwargs):
            self.run_methods = []
            super(ExceptionDuringClassSetupTest.FakeParentTestCase, self).__init__(*args, **kwargs)

        @class_setup
        def parent_class_setup(self):
            self.run_methods.append("parent class_setup")
            raise Exception

        @class_teardown
        def parent_class_teardown(self):
            self.run_methods.append("parent class_teardown")

        @setup
        def parent_setup(self):
            self.run_methods.append("parent setup")
            raise Exception

        @teardown
        def parent_teardown(self):
            self.run_methods.append("parent teardown")

        def test_parent(self):
            self.run_methods.append("parent test method")

    class FakeChildTestCase(FakeParentTestCase):

        @class_setup
        def child_class_setup(self):
            self.run_methods.append("child class_setup")

        @class_teardown
        def child_class_teardown(self):
            self.run_methods.append("child class_teardown")

        @setup
        def child_setup(self):
            self.run_methods.append("child setup")

        @teardown
        def child_teardown(self):
            self.run_methods.append("child teardown")

        def test_child(self):
            self.run_methods.append("child test method")

    def test_parent(self):
        test_case = self.FakeParentTestCase()
        test_case.run()
        expected = ["parent class_setup", "parent class_teardown",]
        assert_equal(expected, test_case.run_methods)

    def test_child(self):
        test_case = self.FakeChildTestCase()
        test_case.run()
        expected = ["parent class_setup", "child class_teardown", "parent class_teardown",]
        assert_equal(expected, test_case.run_methods)


class ExceptionDuringSetupTest(TestCase):

    class FakeParentTestCase(TestCase):

        def __init__(self, *args, **kwargs):
            self.run_methods = []
            super(ExceptionDuringSetupTest.FakeParentTestCase, self).__init__(*args, **kwargs)

        @setup
        def parent_setup(self):
            self.run_methods.append("parent setup")
            raise Exception

        @teardown
        def parent_teardown(self):
            self.run_methods.append("parent teardown")

        def test_parent(self):
            self.run_methods.append("parent test method")

    class FakeChildTestCase(FakeParentTestCase):

        @setup
        def child_setup(self):
            self.run_methods.append("child setup")

        @teardown
        def child_teardown(self):
            self.run_methods.append("child teardown")

        def test_child(self):
            self.run_methods.append("child test method")

    def test_parent(self):
        test_case = self.FakeParentTestCase()
        test_case.run()
        expected = ["parent setup", "parent teardown",]
        assert_equal(expected, test_case.run_methods)

    def test_child(self):
        test_case = self.FakeChildTestCase()
        test_case.run()
        # FakeChildTestCase has two test methods (test_parent and test_child), so the fixtures are run twice.
        expected = ["parent setup", "child teardown", "parent teardown",] * 2
        assert_equal(expected, test_case.run_methods)


class ExceptionDuringClassTeardownTest(TestCase):

    class FakeParentTestCase(TestCase):

        def __init__(self, *args, **kwargs):
            self.run_methods = []
            super(ExceptionDuringClassTeardownTest.FakeParentTestCase, self).__init__(*args, **kwargs)

        @class_setup
        def parent_setup(self):
            self.run_methods.append("parent class_setup")

        @class_teardown
        def parent_teardown(self):
            self.run_methods.append("parent class_teardown")
            raise Exception

        def test_parent(self):
            self.run_methods.append("parent test method")

    class FakeChildTestCase(FakeParentTestCase):

        @class_setup
        def child_setup(self):
            self.run_methods.append("child class_setup")

        @class_teardown
        def child_teardown(self):
            self.run_methods.append("child class_teardown")

        def test_child(self):
            self.run_methods.append("child test method")

    def test_parent(self):
        test_case = self.FakeParentTestCase()
        test_case.run()
        expected = ["parent class_setup", "parent test method", "parent class_teardown",]
        assert_equal(expected, test_case.run_methods)

    def test_child(self):
        test_case = self.FakeChildTestCase()
        test_case.run()
        expected = [
            "parent class_setup",
            "child class_setup",
            "child test method",
            "parent test method",
            "child class_teardown",
            "parent class_teardown",
        ]
        assert_equal(expected, test_case.run_methods)


class ExceptionDuringTeardownTest(TestCase):

    class FakeParentTestCase(TestCase):

        def __init__(self, *args, **kwargs):
            self.run_methods = []
            super(ExceptionDuringTeardownTest.FakeParentTestCase, self).__init__(*args, **kwargs)

        @setup
        def parent_setup(self):
            self.run_methods.append("parent setup")

        @teardown
        def parent_teardown(self):
            self.run_methods.append("parent teardown")
            raise Exception

        def test_parent(self):
            self.run_methods.append("parent test method")

    class FakeChildTestCase(FakeParentTestCase):

        @setup
        def child_setup(self):
            self.run_methods.append("child setup")

        @teardown
        def child_teardown(self):
            self.run_methods.append("child teardown")

        def test_child(self):
            self.run_methods.append("child test method")

    def test_parent(self):
        test_case = self.FakeParentTestCase()
        test_case.run()
        expected = ["parent setup", "parent test method", "parent teardown",]
        assert_equal(expected, test_case.run_methods)

    def test_child(self):
        test_case = self.FakeChildTestCase()
        test_case.run()
        expected = [
            # Fixtures run before and after each test method.
            # Here's test_child.
            "parent setup",
            "child setup",
            "child test method",
            "child teardown",
            "parent teardown",
            # Here's test_parent.
            "parent setup",
            "child setup",
            "parent test method",
            "child teardown",
            "parent teardown",
        ]
        assert_equal(expected, test_case.run_methods)


class TestCaseKeepsReferenceToResultsForTestMethod(TestCase):
    def test_reference_to_results(self):
        assert self.test_result


class NoAttributesNamedTest(TestCase):
    class FakeTestCase(TestCase):
        def test_your_might(self):
            assert True

    def test_attributes(self):
        test_case = self.FakeTestCase()
        expected_attributes = sorted([
            "test_result",     # Part of the public API (its name is unfortunate but e.g. Selenium relies on it)
            "test_your_might", # "Actual" test method in the test case
        ])
        actual_attributes = sorted([attribute for attribute in dir(test_case) if attribute.startswith("test")])
        assert_equal(expected_attributes, actual_attributes)


if __name__ == '__main__':
    run()

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_discovery_test

from functools import wraps
from os import chdir
from os import getcwd
from os.path import abspath
from os.path import dirname
from os.path import join

from testify import assert_length
from testify import assert_raises
from testify import run
from testify import TestCase
from testify import test_discovery


HERE = dirname(abspath(__file__))

class DiscoveryTestCase(TestCase):
    def discover(self, path):
        # Exhaust the generator to catch exceptions
        return [mod for mod in test_discovery.discover(path)]

def relative(func):
    'decorator for tests that rely on relative paths'
    @wraps(func)
    def wrapped(*args, **kwargs):
        cwd = getcwd()
        chdir(HERE)
        try:
            return func(*args, **kwargs)
        finally:
            # clean up even after test failures
            chdir(cwd)
    return wrapped

class TestDiscoverDottedPath(DiscoveryTestCase):
    @relative
    def test_dotted_path(self):
        assert self.discover('test_suite_subdir.define_testcase')

class TestDiscoverFilePath(DiscoveryTestCase):
    @relative
    def test_file_path(self):
        assert self.discover('test_suite_subdir/define_testcase')

    @relative
    def test_file_path_with_py_suffix(self):
        assert self.discover('test_suite_subdir/define_testcase.py')

    @relative
    def test_file_path_with_non_normal_path(self):
        assert self.discover('./test_suite_subdir///define_testcase.py')

    def test_file_absolute_path(self):
        assert self.discover(join(HERE, 'test_suite_subdir/define_testcase.py'))


class TestDiscoverIgnoreImportedThings(DiscoveryTestCase):
    @relative
    def test_imported_things_are_ignored(self):
        #TODO CHANGE MY NAME
        discovered_imported = list(test_discovery.discover('test_suite_subdir.import_testcase'))
        discovered_actually_defined_in_module = list(test_discovery.discover('test_suite_subdir.define_testcase'))

        assert_length(discovered_imported, 0)
        assert_length(discovered_actually_defined_in_module, 1)


class ImportTestClassCase(DiscoveryTestCase):

    def discover(self, module_path, class_name):
        return test_discovery.import_test_class(module_path, class_name)

    @relative
    def test_discover_testify_case(self):
        assert self.discover('test_suite_subdir.define_testcase', 'DummyTestCase')

    @relative
    def test_discover_unittest_case(self):
        assert self.discover('test_suite_subdir.define_unittestcase', 'TestifiedDummyUnitTestCase')

    @relative
    def test_discover_bad_case(self):
        assert_raises(test_discovery.DiscoveryError, self.discover, 'bad.subdir', 'DummyTestCase')
        assert_raises(test_discovery.DiscoveryError, self.discover, 'test_suite_subdir.define_testcase', 'IGNORE ME')


if __name__ == '__main__':
    run()

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_fixtures_test
import itertools

from testify import assert_equal
from testify import assert_not_equal
from testify import class_setup
from testify import class_setup_teardown
from testify import class_teardown
from testify import let
from testify import setup
from testify import setup_teardown
from testify import suite
from testify import teardown
from testify import TestCase


class FixtureMethodRegistrationOrderTest(TestCase):
    """Test that registered fixtures execute in the expected order, which is:
     - class_setup
     - enter class_setup_teardown
     - setup
     - enter setup_teardown

     - test

     - exit setup_teardown, in Reverse of definition
     - teardown
     - exit class_setup_teardown in Reverse order of definition
     - class_teardown
    """
    def __init__(self, *args, **kwargs):
        super(FixtureMethodRegistrationOrderTest, self).__init__(*args, **kwargs)
        self.counter = 0

    @class_setup
    def __class_setup_prerun_1(self):
        assert_equal(self.counter, 0)
        self.counter += 1

    @class_setup
    def __class_setup_prerun_2(self):
        assert_equal(self.counter, 1)
        self.counter += 1

    @class_setup
    def third_setup(self):
        assert_equal(self.counter, 2)
        self.counter += 1

    @class_setup_teardown
    def __class_context_manager_1(self):
        assert_equal(self.counter, 3)
        self.counter += 1
        yield
        assert_equal(self.counter, 17)
        self.counter += 1

    @class_setup_teardown
    def __class_context_manager_2(self):
        assert_equal(self.counter, 4)
        self.counter += 1
        yield
        assert_equal(self.counter, 16)
        self.counter += 1

    @setup
    def __setup_prerun_1(self):
        assert_equal(self.counter, 5)
        self.counter += 1

    @setup
    def __setup_prerun_2(self):
        assert_equal(self.counter, 6)
        self.counter += 1

    @setup
    def real_setup(self):
        assert_equal(self.counter, 7)
        self.counter += 1

    @setup_teardown
    def __context_manager_1(self):
        assert_equal(self.counter, 8)
        self.counter += 1
        yield
        assert_equal(self.counter, 12)
        self.counter += 1

    @setup_teardown
    def __context_manager_2(self):
        assert_equal(self.counter, 9)
        self.counter += 1
        yield
        assert_equal(self.counter, 11)
        self.counter += 1

    def test_fixture_registration_order(self):
        assert_equal(self.counter, 10)
        self.counter += 1

    @teardown
    def do_some_teardown(self):
        assert_equal(self.counter, 13)
        self.counter += 1

    @teardown
    def __zteardown_postrun_1(self):
        assert_equal(self.counter, 14)
        self.counter += 1

    @teardown
    def __teardown_postrun_2(self):
        assert_equal(self.counter, 15)
        self.counter += 1

    @class_teardown
    def just_class_teardown(self):
        assert_equal(self.counter, 18)
        self.counter += 1

    @class_teardown
    def __class_teardown_postrun_1(self):
        assert_equal(self.counter, 19)
        self.counter += 1

    @class_teardown
    def __class_teardown_postrun_2(self):
        assert_equal(self.counter, 20)


class FixtureMethodRegistrationOrderWithBaseClassTest(TestCase):
    """Test that registered fixtures execute in the expected order, which is:
     - class_setup & enter class_setup_teardown of the Base class
     - class_setup & enter class_setup_teardown of the Derived class
     - exit class_setup_teardown & class_teardown of the Derived class
     - exit class_setup_teardown & class_teardown of the Base class
    """

    class FakeBaseClass(TestCase):

        def __init__(self, *args, **kwargs):
            super(FixtureMethodRegistrationOrderWithBaseClassTest.FakeBaseClass, self).__init__(*args, **kwargs)
            self.method_order = []

        def classSetUp(self):
            self.method_order.append("base_classSetUp")

        def classTearDown(self):
            self.method_order.append("base_classTearDown")

        @class_setup
        def base_class_setup(self):
            self.method_order.append("base_class_setup")

        @class_setup_teardown
        def base_class_setup_teardown(self):
            self.method_order.append("base_class_setup_teardown_setup_phase")
            yield
            self.method_order.append("base_class_setup_teardown_teardown_phase")

        @class_teardown
        def base_class_teardown(self):
            self.method_order.append("base_class_teardown")

        @setup_teardown
        def base_instance_setup_teardown(self):
            self.method_order.append("base_instance_setup_teardown_setup_phase")
            yield
            self.method_order.append("base_instance_setup_teardown_teardown_phase")

        @setup
        def base_instance_setup(self):
            self.method_order.append("base_instance_setup")

        @teardown
        def base_instance_teardown(self):
            self.method_order.append("base_instance_teardown")

        def test_something(self):
            """Need a test method to get instance-level fixtures to run."""
            return True

    class FakeDerivedClass(FakeBaseClass):
        @class_setup
        def derived_class_setup(self):
            self.method_order.append("derived_class_setup")

        @class_setup_teardown
        def derived_class_setup_teardown(self):
            self.method_order.append("derived_class_setup_teardown_setup_phase")
            yield
            self.method_order.append("derived_class_setup_teardown_teardown_phase")

        @class_teardown
        def derived_class_teardown(self):
            self.method_order.append("derived_class_teardown")

        @setup_teardown
        def base_derived_setup_teardown(self):
            self.method_order.append("derived_instance_setup_teardown_setup_phase")
            yield
            self.method_order.append("derived_instance_setup_teardown_teardown_phase")

        @setup
        def derived_instance_setup(self):
            self.method_order.append("derived_instance_setup")

        @teardown
        def derived_instance_teardown(self):
            self.method_order.append("derived_instance_teardown")

    class FakeDerivedClassWithDeprecatedClassLevelFixtures(FakeBaseClass):
        def classSetUp(self):
            self.method_order.append("derived_classSetUp")

        def classTearDown(self):
            self.method_order.append("derived_classTearDown")

        @class_setup
        def derived_class_setup(self):
            self.method_order.append("derived_class_setup")

        @class_setup_teardown
        def derived_class_setup_teardown(self):
            self.method_order.append("derived_class_setup_teardown_setup_phase")
            yield
            self.method_order.append("derived_class_setup_teardown_teardown_phase")

        @class_teardown
        def derived_class_teardown(self):
            self.method_order.append("derived_class_teardown")

    def test_order(self):
        fake_test_case = self.FakeDerivedClass()
        fake_test_case.run()
        expected_order = [
            "base_classSetUp",
            "base_class_setup",
            "base_class_setup_teardown_setup_phase",

            "derived_class_setup",
            "derived_class_setup_teardown_setup_phase",

            "base_instance_setup",
            "base_instance_setup_teardown_setup_phase",

            "derived_instance_setup",
            "derived_instance_setup_teardown_setup_phase",

            "derived_instance_setup_teardown_teardown_phase",
            "derived_instance_teardown",

            "base_instance_setup_teardown_teardown_phase",
            "base_instance_teardown",

            "derived_class_setup_teardown_teardown_phase",
            "derived_class_teardown",

            "base_class_setup_teardown_teardown_phase",
            "base_class_teardown",
            "base_classTearDown",
        ]

        assert_equal(fake_test_case.method_order, expected_order)

    def test_order_with_deprecated_class_level_fixtures_in_derived_class(self):
        fake_test_case = self.FakeDerivedClassWithDeprecatedClassLevelFixtures()
        fake_test_case.run()
        expected_order = [
            "base_class_setup",
            "base_class_setup_teardown_setup_phase",

            "derived_classSetUp",
            "derived_class_setup",
            "derived_class_setup_teardown_setup_phase",

            "base_instance_setup",
            "base_instance_setup_teardown_setup_phase",

            "base_instance_setup_teardown_teardown_phase",
            "base_instance_teardown",

            "derived_class_setup_teardown_teardown_phase",
            "derived_class_teardown",
            "derived_classTearDown",

            "base_class_setup_teardown_teardown_phase",
            "base_class_teardown",
        ]

        assert_equal(fake_test_case.method_order, expected_order)


class TestRegisterFixtureMethodsParentClass(TestCase):
    """A parent class to test the ability to register fixture methods"""

    @setup
    def parent_setup_1(self):
        """Set an instance variable to test that this method gets called"""
        self.parent_setup_exists = 1

    @setup
    def __parent_setup_2(self):
        """Set an instance variable to test that this method gets called"""
        self.parent_setup_exists += 1


class TestRegisterFixtureMethodsChildClass(TestRegisterFixtureMethodsParentClass):
    """A child class to test the ability to register fixture methods"""

    @setup
    def __zchild_setup_1(self):
        self.child_setup_exists = self.parent_setup_exists + 1

    @setup
    def __child_setup_2(self):
        self.child_setup_2_exists = self.child_setup_exists + 1

    def test_things_exist(self):
        """Check for instance variable set by fixture method from parent class"""
        self.failUnless(self.parent_setup_exists == 2)
        assert self.child_setup_exists == 3
        assert self.child_setup_2_exists == 4


@class_setup
def test_incorrectly_defined_fixture():
    """Not a true test, but declarations like this shouldn't crash."""
    pass


class FixtureMixin(object):
    @class_setup
    def set_attr(cls):
        cls.foo = True

    @property
    def get_foo(self):
        # properties dependent on setup shouldn't crash our dir() loop when
        # determining fixures on a class
        return self.foo

    def test_foo(self):
        self.foo_ran = self.get_foo


class TestFixtureMixinsGetRun(TestCase, FixtureMixin):
    # define the teardown here in case the mixin doesn't properly apply it
    @class_teardown
    def make_sure_i_ran(self):
        assert self.foo_ran


class RedefinedFixtureWithNoDecoratorTest(TestCase, FixtureMixin):
    def set_attr(self):
        pass

    def test_foo(self):
        # set_attr shouldn't have run because it's no longer decorated
        assert not hasattr(self, 'foo')


class TestSubclassedCasesWithFeatureMixinsGetRun(TestFixtureMixinsGetRun):
    pass


class TestOtherCasesWithSameFixtureMixinsGetRun(TestCase, FixtureMixin):
    @teardown
    def make_sure_i_ran(self):
        assert self.foo_ran


class NewerFixtureMixin(object):
    @class_setup
    def set_another_attr(cls):
        assert cls.foo # this setup should run after FixtureMixin's
        cls.bar = True

    def test_bar(self):
        self.bar_ran = self.bar


class TestFixtureMixinOrder(TestCase, NewerFixtureMixin, FixtureMixin):
    @class_teardown
    def make_sure_i_ran(self):
        assert self.foo_ran
        assert self.bar_ran


class DeprecatedFixtureOrderTestBase(TestCase):
    @class_setup
    def set_something(self):
        assert not hasattr(self, 'something')
        self.something = True

    @class_teardown
    def clear_something(self):
        assert self.something == None


class DeprecatedFixtureOrderTestChild(DeprecatedFixtureOrderTestBase):
    """Tests that deprecated fixtures on children are called in the correct order."""

    def classSetUp(self):
        """Should be called after do_something."""
        assert self.something == True
        self.something = False

    def test_something(self):
        assert self.something == False

    def classTearDown(self):
        """Should be called before clear_something"""
        assert self.something == False
        self.something = None


class FixtureOverloadTestBase(TestCase):
    foo = True
    @setup
    def unset_foo(self):
        self.foo = False


class FixtureOverloadTestChild(FixtureOverloadTestBase):
    """Tests that overloading a fixture works as expected."""
    @setup
    def unset_foo(self):
        pass

    def test_overloaded_setup(self):
        # we shouldn't have unset this
        assert self.foo


class LetTest(TestCase):

    @let
    def counter(self):
        return itertools.count(0)

    def test_first_call_is_not_cached(self):
        assert_equal(self.counter.next(), 0)

    def test_subsequent_calls_are_cached(self):
        assert_equal(self.counter.next(), 0)
        assert_equal(self.counter.next(), 1)


class LetWithLambdaTest(TestCase):

    counter = let(lambda self: itertools.count(0))

    def test_first_call_is_not_cached(self):
        assert_equal(self.counter.next(), 0)

    def test_subsequent_calls_are_cached(self):
        assert_equal(self.counter.next(), 0)
        assert_equal(self.counter.next(), 1)


class LetWithSubclassTest(LetWithLambdaTest):
    """Test that @let is inherited correctly."""
    pass


class SuiteDecoratorTest(TestCase):

    def test_suite_pollution_with_suites_attribute(self):
        """Test if suite decorator modifies the object's attribute
        objects instead of assigning a new object. Modifying _suite
        attribute objects causes suite pollution in TestCases.

        Here we test if the _suites attribute's id() remains the same
        to verify suite decorator does not modify the object's
        attribute object.
        """

        def function_to_decorate():
            pass

        function_to_decorate._suites = set(['fake_suite_1'])

        suites_before_decoration = function_to_decorate._suites

        function_to_decorate = suite('fake_suite_2')(function_to_decorate)

        suites_after_decoration =  function_to_decorate._suites

        assert_not_equal(
            id(suites_before_decoration),
            id(suites_after_decoration),
            "suites decorator modifies the object's _suite attribute"
        )

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_logger_test
import cStringIO

from mock import patch

from test.discovery_failure_test import BrokenImportTestCase
from testify import TestCase, assert_equal, assert_in, class_setup, class_setup_teardown, class_teardown, run, setup, teardown
from testify.test_logger import TextTestLogger, VERBOSITY_NORMAL
from testify.test_runner import TestRunner
from testify.utils import turtle


class TextLoggerBaseTestCase(TestCase):
    @setup
    def create_stream_for_logger(self):
        self.stream = cStringIO.StringIO()

    @setup
    def create_options_for_test_runner(self):
        """Fake an OptionParser-style options object."""
        self.options = turtle.Turtle(
            verbosity=VERBOSITY_NORMAL,
            summary_mode=False,
        )

    @teardown
    def close_stream_for_logger(self):
        self.stream.close()


class TextLoggerDiscoveryFailureTestCase(BrokenImportTestCase, TextLoggerBaseTestCase):
    def test_text_test_logger_prints_discovery_failure_message(self):
        runner = TestRunner(
            self.broken_import_module,
            test_reporters=[TextTestLogger(self.options, stream=self.stream)],
        )
        runner.run()
        logger_output = self.stream.getvalue()
        assert_in('DISCOVERY FAILURE!', logger_output)


class FakeClassFixtureException(Exception):
    pass


class ExceptionInClassFixtureSampleTests(TestCase):
    class FakeClassSetupTestCase(TestCase):
        @class_setup
        def class_setup_raises_exception(self):
            raise FakeClassFixtureException('class_setup kaboom')

        def test1(self):
            assert False, 'test1 should not be reached; class_setup should have aborted.'

        def test2(self):
            assert False, 'test2 should not be reached; class_setup should have aborted.'

    class FakeClassTeardownTestCase(TestCase):
        @class_teardown
        def class_teardown_raises_exception(self):
            raise FakeClassFixtureException('class_teardown kaboom')

        def test1(self):
            pass

        def test2(self):
            pass

    class FakeSetupPhaseOfClassSetupTeardownTestCase(TestCase):
        @class_setup_teardown
        def class_setup_teardown_raises_exception_in_setup_phase(self):
            raise FakeClassFixtureException('class_setup_teardown setup phase kaboom')
            yield # Never reached
            # Empty teardown, also never reached

        def test1(self):
            pass

        def test2(self):
            pass


    class FakeTeardownPhaseOfClassSetupTeardownTestCase(TestCase):
        @class_setup_teardown
        def class_setup_teardown_raises_exception_in_teardown_phase(self):
            # Empty setup
            yield
            raise FakeClassFixtureException('class_setup_teardown teardown phase kaboom')

        def test1(self):
            pass

        def test2(self):
            pass


class TextLoggerExceptionInClassFixtureTestCase(TextLoggerBaseTestCase):
    """Tests how TextLogger handles exceptions in @class_[setup | teardown |
    setup_teardown]. Also an integration test with how results are collected
    because this seemed like the most natural place to test everything.
    """

    def _run_test_case(self, test_case):
        self.logger = TextTestLogger(self.options, stream=self.stream)
        runner = TestRunner(
            test_case,
            test_reporters=[self.logger],
        )
        runner_result = runner.run()
        assert_equal(runner_result, False)

    def test_class_setup(self):
        self._run_test_case(ExceptionInClassFixtureSampleTests.FakeClassSetupTestCase)

        # The fake test methods assert if they are called. If we make it here,
        # then execution never reached those methods and we are happy.

        for result in self.logger.results:
            assert_equal(
                result['success'],
                False,
                'Unexpected success for %s' % result['method']['full_name'],
            )
            assert_equal(
                result['error'],
                True,
                'Unexpected non-error for %s' % result['method']['full_name'],
            )

        logger_output = self.stream.getvalue()
        assert_in('error', logger_output)
        assert_in('FakeClassSetupTestCase.test1', logger_output)
        assert_in('FakeClassSetupTestCase.test2', logger_output)
        assert_in('in class_setup_raises_exception', logger_output)


    def test_setup_phase_of_class_setup_teardown(self):
        self._run_test_case(ExceptionInClassFixtureSampleTests.FakeSetupPhaseOfClassSetupTeardownTestCase)

        # The fake test methods assert if they are called. If we make it here,
        # then execution never reached those methods and we are happy.

        for result in self.logger.results:
            assert_equal(
                result['success'],
                False,
                'Unexpected success for %s' % result['method']['full_name'],
            )
            assert_equal(
                result['error'],
                True,
                'Unexpected non-error for %s' % result['method']['full_name'],
            )

        logger_output = self.stream.getvalue()
        assert_in('error', logger_output)
        assert_in('FakeSetupPhaseOfClassSetupTeardownTestCase.test1', logger_output)
        assert_in('FakeSetupPhaseOfClassSetupTeardownTestCase.test2', logger_output)
        assert_in('in class_setup_teardown_raises_exception_in_setup_phase', logger_output)


    def test_class_teardown(self):
        self._run_test_case(ExceptionInClassFixtureSampleTests.FakeClassTeardownTestCase)
        assert_equal(len(self.logger.results), 3)

        class_teardown_result = self.logger.results[-1]
        assert_equal(
            class_teardown_result['success'],
            False,
            'Unexpected success for %s' % class_teardown_result['method']['full_name'],
        )
        assert_equal(
            class_teardown_result['error'],
            True,
            'Unexpected non-error for %s' % class_teardown_result['method']['full_name'],
        )

        logger_output = self.stream.getvalue()
        assert_in('error', logger_output)
        assert_in('FakeClassTeardownTestCase.class_teardown_raises_exception', logger_output)


    def test_teardown_phase_of_class_setup_teardown(self):
        self._run_test_case(ExceptionInClassFixtureSampleTests.FakeTeardownPhaseOfClassSetupTeardownTestCase)
        assert_equal(len(self.logger.results), 3)

        class_teardown_result = self.logger.results[-1]
        assert_equal(
            class_teardown_result['success'],
            False,
            'Unexpected success for %s' % class_teardown_result['method']['full_name'],
        )
        assert_equal(
            class_teardown_result['error'],
            True,
            'Unexpected non-error for %s' % class_teardown_result['method']['full_name'],
        )

        logger_output = self.stream.getvalue()
        assert_in('error', logger_output)
        assert_in('FakeTeardownPhaseOfClassSetupTeardownTestCase.class_setup_teardown_raises_exception_in_teardown_phase', logger_output)


    def test_class_teardown_raises_after_test_raises(self):
        """Patch our fake test case, replacing test1() with a function that
        raises its own exception. Make sure that both the method's exception
        and the class_teardown exception are represented in the results.
        """

        class FakeTestException(Exception):
            pass

        def test1_raises(self):
            raise FakeTestException('I raise before class_teardown raises')

        with patch.object(ExceptionInClassFixtureSampleTests.FakeClassTeardownTestCase, 'test1', test1_raises):
            self._run_test_case(ExceptionInClassFixtureSampleTests.FakeClassTeardownTestCase)

            assert_equal(len(self.logger.results), 3)
            test1_raises_result = self.logger.results[0]
            class_teardown_result = self.logger.results[-1]
            assert_in('FakeTestException', str(test1_raises_result['exception_info_pretty']))
            assert_in('FakeClassFixtureException', str(class_teardown_result['exception_info_pretty']))


if __name__ == '__main__':
    run()

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_program_test
import os
import subprocess

import mock
from testify import setup_teardown, TestCase, test_program
from testify.assertions import assert_equal, assert_raises, assert_in
from optparse import OptionParser


class OptionParserErrorException(Exception):
    pass


class ParseTestRunnerCommandLineArgsTest(TestCase):
    @setup_teardown
    def patch_OptionParser_error(self):
        def new_error(*args, **kwargs):
            raise OptionParserErrorException(*args, **kwargs)
        with mock.patch.object(OptionParser, 'error', side_effect=new_error):
            yield

    def test__parse_test_runner_command_line_module_method_overrides_empty_input(self):
        """Make sure _parse_test_runner_command_line_module_method_overrides returns something sensible if you pass it an empty list of arguments."""
        assert_equal(test_program._parse_test_runner_command_line_module_method_overrides([]), (None, {}))

    def test_parse_test_runner_command_line_args_rerun_test_file(self):
        """Make sure that when --rerun-test-file is passed, parse_test_runner_command_line_args doesn't complain about a missing test path."""
        test_program.parse_test_runner_command_line_args([], ['--rerun-test-file', '-'])

    def test_parse_test_runner_command_line_args_connect(self):
        """Make sure that when --connect is passed, parse_test_runner_command_line_args doesn't complain about a missing test path."""
        test_program.parse_test_runner_command_line_args([], ['--connect', 'localhost:65537'])

    def test_parse_test_runner_command_line_args_replay_json_inline(self):
        """Make sure that when --replay-json-inline is passed, parse_test_runner_command_line_args doesn't complain about a missing test path."""
        test_program.parse_test_runner_command_line_args([], ['--replay-json-inline', '{something that obviously isnt json}'])

    def test_parse_test_runner_command_line_args_replay_json(self):
        """Make sure that when --replay-json-inline is passed, parse_test_runner_command_line_args doesn't complain about a missing test path."""
        test_program.parse_test_runner_command_line_args([], ['--replay-json', 'somejsonfile.txt'])

    def test_parse_test_runner_command_line_args_no_test_path(self):
        """Make sure that if no options and no arguments are passed, parse_test_runner_command_line_args DOES complain about a missing test path."""
        with assert_raises(OptionParserErrorException):
            test_program.parse_test_runner_command_line_args([], [])


def test_call(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, command)
    return stdout.strip()


class TestifyRunAcceptanceTestCase(TestCase):

    expected_list = (
        'testing_suite.example_test ExampleTestCase.test_one\n'
        'testing_suite.example_test ExampleTestCase.test_two\n'
        'testing_suite.example_test SecondTestCase.test_one'
    )

    expected_tests = 'PASSED.  3 tests'

    def test_run_testify_from_bin_list_tests(self):
        output = test_call(['bin/testify', '--list-tests', 'testing_suite'])
        assert_equal(output, self.expected_list)

    def test_run_testify_as_module_list_tests(self):
        output = test_call([
                'python', '-m', 'testify.test_program',
                '--list-tests', 'testing_suite'])
        assert_equal(output, self.expected_list)

    def test_run_testify_from_bin(self):
        output = test_call(['bin/testify', 'testing_suite', '-v'])
        assert_in(self.expected_tests, output)

    def test_run_testify_test_module(self):
        output = test_call(['python', '-m', 'testing_suite.example_test', '-v'])
        assert_in(self.expected_tests, output)

    def test_run_testify_test_file(self):
        output = test_call(['python', 'testing_suite/example_test.py', '-v'])
        assert_in(self.expected_tests, output)

    def test_run_testify_test_file_class(self):
        output = test_call([
                'python', 'testing_suite/example_test.py', '-v',
                'ExampleTestCase'])
        assert_in('PASSED.  2 tests', output)

    def test_run_testify_test_file_class_and_method(self):
        output = test_call([
                'python', 'testing_suite/example_test.py', '-v',
                'ExampleTestCase.test_one'])
        assert_in('PASSED.  1 test', output)

    def test_run_testify_with_failure(self):
        assert_raises(
                subprocess.CalledProcessError,
                test_call,
                ['python', 'testing_suite/example_test.py', 'DoesNotExist'])


class TestClientServerReturnCode(TestCase):
    def test_client_returns_zero_on_success(self):
        server_process = subprocess.Popen(
            [
                'python', '-m', 'testify.test_program',
                'testing_suite.example_test',
                '--serve', '9001',
            ],
            stdout=open(os.devnull, 'w'),
            stderr=open(os.devnull, 'w'),
        )
        # test_call has the side-effect of asserting the return code is 0
        ret = test_call([
            'python', '-m', 'testify.test_program',
            '--connect', 'localhost:9001',
        ])
        assert_in('PASSED', ret)
        assert_equal(server_process.wait(), 0)

    def test_client_returns_nonzero_on_failure(self):
        server_process = subprocess.Popen(
            [
                'python', '-m', 'testify.test_program',
                'test.failing_test',
                '--serve', '9001',
            ],
            stdout=open(os.devnull, 'w'),
            stderr=open(os.devnull, 'w'),
        )
        # Need two clients in order to finish running tests
        client_1 = subprocess.Popen(
            [
                'python', '-m', 'testify.test_program',
                '--connect', 'localhost:9001',
            ],
            stdout=open(os.devnull, 'w'),
            stderr=open(os.devnull, 'w'),
        )
        client_2 = subprocess.Popen(
            [
                'python', '-m', 'testify.test_program',
                '--connect', 'localhost:9001',
            ],
            stdout=open(os.devnull, 'w'),
            stderr=open(os.devnull, 'w'),
        )
        assert_equal(client_1.wait(), 1)
        assert_equal(client_2.wait(), 1)
        assert_equal(server_process.wait(), 1)
            

########NEW FILE########
__FILENAME__ = test_result_serializable_test
from testify import test_case
from testify import run
from testify import test_result
from testify import assert_equal

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

class TestResultIsSerializableTestCase(test_case.TestCase):
    class NullTestCase(test_case.TestCase):
        def test_method(self):
            return

    null_test_case = NullTestCase()

    def test_test_result_is_serializable(self):
        result = test_result.TestResult(self.null_test_case.test_method)
        json.dumps(result.to_dict())
        result.start()
        json.dumps(result.to_dict())
        result.end_in_success()
        json.dumps(result.to_dict())

    def test_not_garbled_by_serialization(self):
        """Make sure that converting to JSON and back results in the same dictionary."""
        result = test_result.TestResult(self.null_test_case.test_method)
        assert_equal(
            result.to_dict(),
            json.loads(json.dumps(result.to_dict()))
        )

        result.start()
        assert_equal(
            result.to_dict(),
            json.loads(json.dumps(result.to_dict()))
        )

        result.end_in_success()
        assert_equal(
            result.to_dict(),
            json.loads(json.dumps(result.to_dict()))
        )




if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = test_result_test
import mock

from testify import assert_equal
from testify import assert_raises
from testify import setup_teardown
from testify import run
from testify import TestCase
from testify.test_result import TestResult


def fake_format_exception(exctype, value, tb, limit=None):
    return 'Traceback: %s\n' % (exctype.__name__)


class TestResultTestCase(TestCase):

    @setup_teardown
    def mock_test_result(self):
        test_method = mock.Mock(__name__='test_name')
        with mock.patch('testify.TestCase.test_result', new_callable=mock.PropertyMock) as test_result:
            test_result.return_value = TestResult(test_method)
            yield

    def _append_exc_info(self, exc_type):
        value, tb = mock.Mock(), mock.Mock(tb_next=None)
        tb.tb_frame.f_globals.has_key.return_value = False
        self.test_result.exception_infos.append((exc_type, value, tb))
        return value, tb

    @mock.patch('traceback.format_exception', wraps=fake_format_exception)
    def test_frame_stripping(self, mock_format_exception):
        """On assertion error, testify strips head and tail frame which originate from testify."""
        test_result = TestResult(lambda:'wat', runner_id='foo!')
        test_result.start()

        root_tb = tb = mock.Mock()
        testify_frames = [True, True, False, True, False, True, True]
        for testify_frame in testify_frames:
            tb.tb_next = mock.Mock()
            tb = tb.tb_next
            tb.configure_mock(**{'tb_frame.f_globals.has_key.return_value': testify_frame})
        tb.tb_next = None
        tb = root_tb.tb_next

        test_result.end_in_failure((AssertionError, 'wat', tb))

        formatted = test_result.format_exception_info()
        assert_equal(formatted, 'Traceback: AssertionError\n')

        # It should format three frames of the stack, starting with the third frame.
        mock_format_exception.assert_called_with(AssertionError, 'wat', tb.tb_next.tb_next, 3)

    @mock.patch('traceback.format_exception', wraps=fake_format_exception)
    def test_format_exception_info_assertion(self, mock_format_exception):
        value, tb = self._append_exc_info(AssertionError)
        formatted = self.test_result.format_exception_info()
        mock_format_exception.assert_called_with(AssertionError, value, tb, 1)
        assert_equal(formatted, 'Traceback: AssertionError\n')

    @mock.patch('traceback.format_exception', wraps=fake_format_exception)
    def test_format_exception_info_error(self, mock_format_exception):
        value, tb = self._append_exc_info(ValueError)
        formatted = self.test_result.format_exception_info()
        mock_format_exception.assert_called_with(ValueError, value, tb, None)
        assert_equal(formatted, 'Traceback: ValueError\n')

    @mock.patch('testify.test_result.fancy_tb_formatter')
    def test_format_exception_info_assertion_pretty(self, mock_format):
        value, tb = self._append_exc_info(AssertionError)
        formatted = self.test_result.format_exception_info(pretty=True)
        mock_format.assert_called_with(AssertionError, value, tb, 1)
        assert_equal(formatted, mock_format.return_value)

    @mock.patch('testify.test_result.fancy_tb_formatter')
    def test_format_exception_info_error_pretty(self, mock_format):
        value, tb = self._append_exc_info(ValueError)
        formatted = self.test_result.format_exception_info(pretty=True)
        mock_format.assert_called_with(ValueError, value, tb)
        assert_equal(formatted, mock_format.return_value)

    @mock.patch('traceback.format_exception', wraps=fake_format_exception)
    def test_format_exception_info_multiple(self, mock_format_exception):
        class Error1(Exception): pass
        class Error2(Exception): pass

        value1, tb1 = self._append_exc_info(Error1)
        value2, tb2 = self._append_exc_info(Error2)
        formatted = self.test_result.format_exception_info()
        mock_format_exception.assert_has_calls([
                mock.call(Error1, value1, tb1, None),
                mock.call(Error2, value2, tb2, None),
        ])
        assert_equal(
                formatted,
                (
                    'Traceback: Error1\n'
                    '\n'
                    'During handling of the above exception, another exception occurred:\n'
                    '\n'
                    'Traceback: Error2\n'
                )
        )


class TestResultStateTest(TestCase):
    """Make sure we don't have a test_result outside of a running test."""

    class WompTest(TestCase):

        @setup_teardown
        def assert_result_state(self):
            assert self.test_result
            yield
            assert self.test_result

        def test_success(self):
            pass

        def test_fail(self):
            assert False

    def test_results(self):
        test_suite = self.WompTest()

        # we only get a test_result once we enter setup
        assert test_suite.test_result is None

        with assert_raises(RuntimeError):
            # results? what results?!
            test_suite.results()

        test_suite.run()

        test_results = test_suite.results()

        assert_equal([result.success for result in test_results], [False, True])


if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = bucketing_test
"""This file is for testing the bucketing system."""

import testify as T


class TestCaseWithManyTests(T.TestCase):
    def test0(self): pass
    def test1(self): pass
    def test2(self): pass
    def test3(self): pass
    def test4(self): pass
    def test5(self): pass
    def test6(self): pass
    def test7(self): pass
    def test8(self): pass
    def test9(self): pass


class TestCaseWithFewTests(T.TestCase):
    def test0(self): pass


class AAA_FirstTestCaseWithSameNumberOfTests(T.TestCase):
    def test0(self): pass
    def test1(self): pass
    def test2(self): pass
    def test3(self): pass
    def test4(self): pass


class ZZZ_SecondTestCaseWithSameNumberOfTests(T.TestCase):
    def test0(self): pass
    def test1(self): pass
    def test2(self): pass
    def test3(self): pass
    def test4(self): pass

########NEW FILE########
__FILENAME__ = test_runner_client_test
import testify

from testify.test_runner_client import TestRunnerClient


class ClientDiscoveryTestCase(testify.TestCase):
    """Integration tests for TestRunnerClient's test discovery."""

    @testify.class_setup
    def init_test_runner_client(self):
        self.client = TestRunnerClient(
                None,
                connect_addr=None,
                runner_id=None,
                options=testify.turtle.Turtle(),
        )

    def discover(self, class_path):
        def foo(*args, **kwargs):
            return class_path, 'test_foo', True

        self.client.get_next_tests = foo
        return [x for x in self.client.discover()]

    def test_discover_testify_case(self):
        assert self.discover('test.test_suite_subdir.define_testcase DummyTestCase')

    def test_discover_unittest_case(self):
        assert self.discover('test.test_suite_subdir.define_unittestcase TestifiedDummyUnitTestCase')

########NEW FILE########
__FILENAME__ = test_runner_server_test
import contextlib
import logging
import threading

import mock
import tornado.ioloop

from discovery_failure_test import BrokenImportTestCase
from test_logger_test import ExceptionInClassFixtureSampleTests
from testify import (
    assert_equal,
    assert_in,
    assert_any_match_regex,
    assert_raises_and_contains,
    class_setup,
    class_teardown,
    setup,
    teardown,
    test_case,
    test_runner_server,
    test_result,
)
from testify.utils import turtle

_log = logging.getLogger('testify')


def get_test(server, runner_id):
    """A blocking function to request a test from a TestRunnerServer."""
    sem = threading.Semaphore(0)
    tests_received = [] # Python closures aren't as cool as JS closures, so we have to use something already on the heap in order to pass data from an inner func to an outer func.

    def inner(test_dict):
        tests_received.append(test_dict)
        sem.release()

    def inner_empty():
        tests_received.append(None)
        sem.release()

    server.get_next_test(runner_id, inner, inner_empty)
    sem.acquire()

    # Verify only one test was received.
    (test_received,) = tests_received
    return test_received


@contextlib.contextmanager
def disable_requeueing(server):
    orig_disable_requeueing = server.disable_requeueing
    server.disable_requeueing = True
    yield
    server.disable_requeueing = orig_disable_requeueing


class TestRunnerServerBaseTestCase(test_case.TestCase):
    __test__ = False

    def build_test_case(self):
        class DummyTestCase(test_case.TestCase):
            def __init__(self_, *args, **kwargs):
                super(DummyTestCase, self_).__init__(*args, **kwargs)
                self_.should_pass = kwargs.pop('should_pass', True)
            def test(self_):
                assert self_.should_pass

        self.dummy_test_case = DummyTestCase

    def run_test(self, runner_id, should_pass=True):
        self.test_instance = self.dummy_test_case(should_pass=should_pass)
        for event in [
            test_case.TestCase.EVENT_ON_COMPLETE_TEST_METHOD,
            test_case.TestCase.EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD,
            test_case.TestCase.EVENT_ON_COMPLETE_TEST_CASE,
        ]:
            self.test_instance.register_callback(
                event,
                lambda result: self.server.report_result(runner_id, result),
            )

        self.test_instance.run()

    def get_seen_methods(self, test_complete_calls):
        seen_methods = set()
        for call in test_complete_calls:
            args = call[0]
            first_arg = args[0]
            first_method_name = first_arg['method']['name']
            seen_methods.add(first_method_name)
        return seen_methods

    def start_server(self, test_reporters=None, failure_limit=None):
        if test_reporters is None:
            self.test_reporter = turtle.Turtle()
            test_reporters = [self.test_reporter]

        self.server = test_runner_server.TestRunnerServer(
            self.dummy_test_case,
            options=turtle.Turtle(
                runner_timeout=1,
                server_timeout=10,
                revision=None,
                shutdown_delay_for_connection_close=0.001,
                shutdown_delay_for_outstanding_runners=1,
            ),
            serve_port=0,
            test_reporters=test_reporters,
            plugin_modules=[],
            failure_limit=failure_limit,
        );

        def catch_exceptions_in_thread():
            try:
                self.server.run()
            except (Exception, SystemExit), exc:
                _log.error("Thread threw exception: %r" % exc)
                raise

        self.thread = threading.Thread(None, catch_exceptions_in_thread)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.thread.join()

    @class_setup
    def setup_test_case(self):
        self.build_test_case()

    @setup
    def setup_server(self):
        self.start_server()

    @teardown
    def teardown_server(self):
        self.stop_server()


class TestRunnerServerBrokenImportTestCase(TestRunnerServerBaseTestCase, BrokenImportTestCase,):
    def create_broken_import_file(self):
        """We must control when this setup method is run since
        build_test_case() depends on it. So we'll stub it out for now and call
        it when we're ready from build_test_case()."""
        pass

    def build_test_case(self):
        super(TestRunnerServerBrokenImportTestCase, self).create_broken_import_file()
        self.dummy_test_case = self.broken_import_module

    def start_server(self):
        """To insure the server has started before we start testing, set up a
        lock which will be released when reporting happens as the final phase
        of server startup.

        Without this, weird race conditions abound where things break because
        server startup is incomplete."""
        lock = threading.Event()
        self.report_call_count = 0

        def report_releases_lock():
            lock.set()
            self.report_call_count += 1
        self.mock_reporter = turtle.Turtle(report=report_releases_lock)
        super(TestRunnerServerBrokenImportTestCase, self).start_server(test_reporters=[self.mock_reporter])

        lock.wait(1)
        assert lock.isSet(), "Timed out waiting for server to finish starting."

    def test_reports_are_generated_after_discovery_failure(self):
        assert_equal(self.report_call_count, 1)


class TestRunnerServerTestCase(TestRunnerServerBaseTestCase):
    def timeout_class(self, runner, test):
        assert test
        tornado.ioloop.IOLoop.instance().add_callback(lambda: self.server.check_in_class(runner, test['class_path'], timed_out=True))

    def test_passing_tests_run_only_once(self):
        """Start a server with one test case to run. Make sure it hands out that test, report it as success, then make sure it gives us nothing else."""
        first_test = get_test(self.server, 'runner1')

        assert_equal(first_test['class_path'], 'test.test_runner_server_test DummyTestCase')
        assert_equal(first_test['methods'], ['test', 'run'])

        self.run_test('runner1')

        second_test = get_test(self.server, 'runner1')
        assert_equal(second_test, None)

    def test_requeue_on_failure(self):
        """Start a server with one test case to run. Make sure it hands out that test, report it as failure, then make sure it gives us the same one, then nothing else."""
        first_test = get_test(self.server, 'runner1')
        assert_equal(first_test['class_path'], 'test.test_runner_server_test DummyTestCase')
        assert_equal(first_test['methods'], ['test', 'run'])

        self.run_test('runner1', should_pass=False)

        second_test = get_test(self.server, 'runner2')
        assert_equal(second_test['class_path'], 'test.test_runner_server_test DummyTestCase')
        assert_equal(second_test['methods'], ['test', 'run'])

        self.run_test('runner2', should_pass=False)

        assert_equal(get_test(self.server, 'runner3'), None)

    def test_requeue_on_timeout(self):
        """Start a server with one test case to run. Make sure it hands out the same test twice, then nothing else."""

        first_test = get_test(self.server, 'runner1')
        self.timeout_class('runner1', first_test)

        # Now just ask for a second test. This should give us the same test again.
        second_test = get_test(self.server, 'runner2')
        self.timeout_class('runner2', second_test)

        # Ask for a third test. This should give us None.
        third_test = get_test(self.server, 'runner3')

        assert first_test
        assert second_test

        assert_equal(first_test['class_path'], second_test['class_path'])
        assert_equal(first_test['methods'], second_test['methods'])
        assert_equal(third_test, None)

    def test_disable_requeueing_on_failure(self):
        with disable_requeueing(self.server):
            first_test = get_test(self.server, 'runner1')
            assert_equal(first_test['class_path'], 'test.test_runner_server_test DummyTestCase')
            assert_equal(first_test['methods'], ['test', 'run'])

            self.run_test('runner1', should_pass=False)

            assert_equal(get_test(self.server, 'runner2'), None)

    def test_disable_requeueing_on_timeout(self):
        with disable_requeueing(self.server):
            first_test = get_test(self.server, 'runner1')
            self.timeout_class('runner1', first_test)

            assert_equal(get_test(self.server, 'runner2'), None)

    def test_report_when_requeueing_is_disabled(self):
        with disable_requeueing(self.server):
            first_test = get_test(self.server, 'runner1')
            assert_equal(first_test['class_path'], 'test.test_runner_server_test DummyTestCase')
            assert_equal(first_test['methods'], ['test', 'run'])

            self.run_test('runner1', should_pass=False)

            test_complete_calls = self.test_reporter.test_complete.calls
            test_complete_call_args = [call[0] for call in test_complete_calls]
            test_results = [args[0] for args in test_complete_call_args]
            full_names = [tr['method']['full_name'] for tr in test_results]
            assert_any_match_regex('test.test_runner_server_test DummyTestCase.test', full_names)

    def test_fail_then_timeout_twice(self):
        """Fail, then time out, then time out again, then time out again.
        The first three fetches should give the same test; the last one should be None."""
        first_test = get_test(self.server, 'runner1')
        self.run_test('runner1', should_pass=False)

        second_test = get_test(self.server, 'runner2')
        self.timeout_class('runner2', second_test)

        third_test = get_test(self.server, 'runner3')
        self.timeout_class('runner3', third_test)


        assert_equal(first_test['class_path'], second_test['class_path'])
        assert_equal(first_test['methods'], second_test['methods'])

        assert_equal(first_test['class_path'], third_test['class_path'])
        assert_equal(first_test['methods'], third_test['methods'])

        # Check that it didn't requeue again.
        assert_equal(get_test(self.server, 'runner4'), None)

    def test_timeout_then_fail_twice(self):
        """Time out once, then fail, then fail again.
        The first three fetches should give the same test; the last one should be None."""
        first_test = get_test(self.server, 'runner1')
        self.timeout_class('runner1', first_test)

        # Don't run it.
        second_test = get_test(self.server, 'runner2')
        self.run_test('runner2', should_pass=False)
        third_test = get_test(self.server, 'runner3')
        self.run_test('runner3', should_pass=False)
        assert_equal(first_test['class_path'], second_test['class_path'])
        assert_equal(first_test['methods'], second_test['methods'])
        assert_equal(first_test['class_path'], third_test['class_path'])
        assert_equal(first_test['methods'], third_test['methods'])

        # Check that it didn't requeue again.
        assert_equal(get_test(self.server, 'runner4'), None)

    def test_get_next_test_doesnt_loop_forever(self):
        """In certain situations, get_next_test will recurse until it runs out of stack space. Make sure that doesn't happen.

        Here are the conditions needed to reproduce this bug
         - The server sees multiple runners
         - The server has more than one test in its queue
         - All the tests in the server's queue were last run by the runner asking for tests.
        """
        self.server.test_queue = test_runner_server.AsyncDelayedQueue()

        self.server.test_queue.put(0, {'last_runner': 'foo', 'class_path': '1', 'methods': ['blah'], 'fixture_methods': []})
        self.server.test_queue.put(0, {'last_runner': 'foo', 'class_path': '2', 'methods': ['blah'], 'fixture_methods': []})
        self.server.test_queue.put(0, {'last_runner': 'foo', 'class_path': '3', 'methods': ['blah'], 'fixture_methods': []})

        failures = []

        def on_test_callback(test):
            failures.append("get_next_test called back with a test.")

        def on_empty_callback():
            failures.append("get_next_test called back with no test.")

        # We need the server to see multiple runners, otherwise the offending code path doesn't get triggered.
        get_test(self.server, 'bar')
        # If this test fails the way we expect it to, this call to get_test will block indefinitely.

        thread = threading.Thread(None, lambda: self.server.get_next_test('foo', on_test_callback, on_empty_callback))
        thread.start()
        thread.join(0.5)

        assert not thread.is_alive(), "get_next_test is still running after 0.5s"

        if failures:
            raise Exception(' '.join(failures))

    def test_activity_on_method_results(self):
        """Previously, the server was not resetting last_activity_time when a client posted results.
        This could lead to an issue when the last client still running tests takes longer than the
        server_timeout. See https://github.com/Yelp/Testify/issues/110
        """

        test = get_test(self.server, 'runner1')
        def make_fake_result(method):
            result = test_result.TestResult(getattr(self.dummy_test_case, method))
            result.start()
            result.end_in_success()
            return result.to_dict()

        for method in test['methods']:
            method_is_last = method == test['methods'][-1]
            if method_is_last:
                # 'activate' will be called twice at the end: once after the
                # method runs, then once more when the TestCase is checked back
                # in to the master.
                expected_call_count = 2
            else:
                expected_call_count = 1
            result = make_fake_result(method)

            with mock.patch.object(self.server, 'activity') as m_activity:
                self.server.report_result('runner1', result)
                assert_equal(m_activity.call_count, expected_call_count)

    def test_fake_result_format(self):
        get_test(self.server, 'runner1')

        fake_result = self.server._fake_result('foo', 'bar', 'baz')
        fake_result = _replace_values_with_types(fake_result)

        real_result = test_result.TestResult(self.dummy_test_case.test, runner_id='foo!')
        real_result.start()
        try:
            print 1/0
        except:
            import sys
            real_result.end_in_failure(sys.exc_info())
        real_result = real_result.to_dict()
        real_result = _replace_values_with_types(real_result)

        assert_equal(fake_result, real_result)


class TestRunnerServerExceptionInSetupPhaseBaseTestCase(TestRunnerServerBaseTestCase):
    """Child classes should set:

    - self.dummy_test_case - a test case that raises an exception during a
      class_setup or the setup phase of a class_setup_teardown

    - self.class_setup_teardown_method_name - the name of the method which will raise an
      exception

    This class's test method will do the rest.
    """

    __test__ = False

    def test_exception_in_setup_phase(self):
        """If a class_setup method raises an exception, this exception is
        reported as an error in all of the test methods in the test case. The
        methods are then treated as flakes and re-run.
        """
        # Pull and run the test case, thereby causing class_setup to run.
        test_case = get_test(self.server, 'runner')
        assert_equal(len(test_case['methods']), 3)
        # The last method will be the special 'run' method which signals the
        # entire test case is complete (including class_teardown).
        assert_equal(test_case['methods'][-1], 'run')

        self.run_test('runner')

        # 'classTearDown' is a deprecated synonym for 'class_teardown'. We
        # don't especially care about it, but it's in there.
        #
        # Exceptions during execution of class_setup cause test methods to fail
        # and get requeued as flakes. They aren't reported now because they
        # aren't complete.
        expected_methods = set(['classTearDown', 'run'])
        # self.run_test configures us up to collect results submitted at
        # class_teardown completion time. class_setup_teardown methods report
        # the result of their teardown phase at "class_teardown completion"
        # time. So, when testing the setup phase of class_setup_teardown, we
        # will see an "extra" method.
        #
        # Child classes which exercise class_setup_teardown will set
        # self.class_setup_teardown_method_name so we can add it to
        # expected_methods here.
        if hasattr(self, 'class_setup_teardown_method_name'):
            expected_methods.add(self.class_setup_teardown_method_name)
        seen_methods = self.get_seen_methods(self.test_reporter.test_complete.calls)
        # This produces a clearer diff than simply asserting the sets are
        # equal.
        assert_equal(expected_methods.symmetric_difference(seen_methods), set())

        # Verify the failed test case is re-queued for running.
        assert_equal(self.server.test_queue.empty(), False)
        requeued_test_case = get_test(self.server, 'runner2')
        assert_in(self.dummy_test_case.__name__, requeued_test_case['class_path'])

        # Reset reporter.
        self.test_reporter.test_complete = turtle.Turtle()

        # Run tests again.
        self.run_test('runner2')

        # This time, test methods have been re-run as flakes. Now that these
        # methods are are complete, they should be reported.
        expected_methods = set(['test1', 'test2', 'classTearDown', 'run'])
        if hasattr(self, 'class_setup_teardown_method_name'):
            expected_methods.add(self.class_setup_teardown_method_name)
        seen_methods = self.get_seen_methods(self.test_reporter.test_complete.calls)
        # This produces a clearer diff than simply asserting the sets are
        # equal.
        assert_equal(expected_methods.symmetric_difference(seen_methods), set())

        # Verify no more test cases have been re-queued for running.
        assert_equal(self.server.test_queue.empty(), True)

class TestRunnerServerExceptionInClassSetupTestCase(TestRunnerServerExceptionInSetupPhaseBaseTestCase):
    def build_test_case(self):
        self.dummy_test_case = ExceptionInClassFixtureSampleTests.FakeClassSetupTestCase


class TestRunnerServerExceptionInSetupPhaseOfClassSetupTeardownTestCase(TestRunnerServerExceptionInSetupPhaseBaseTestCase):
    def build_test_case(self):
        self.dummy_test_case = ExceptionInClassFixtureSampleTests.FakeSetupPhaseOfClassSetupTeardownTestCase
        self.class_setup_teardown_method_name = 'class_setup_teardown_raises_exception_in_setup_phase'


class TestRunnerServerExceptionInTeardownPhaseBaseTestCase(TestRunnerServerBaseTestCase):
    """Child classes should set:

    - self.dummy_test_case - a test case that raises an exception during a
      class_teardown or the teardown phase of a class_setup_teardown

    - self.teardown_method_name - the name of the method which will raise an
      exception

    This class's test method will do the rest.
    """

    __test__ = False

    def test_exception_in_teardown_phase(self):
        # Pull and run the test case, thereby causing class_teardown to run.
        test_case = get_test(self.server, 'runner')
        assert_equal(len(test_case['methods']), 3)
        # The last method will be the special 'run' method which signals the
        # entire test case is complete (including class_teardown).
        assert_equal(test_case['methods'][-1], 'run')

        self.run_test('runner')

        # 'classTearDown' is a deprecated synonym for 'class_teardown'. We
        # don't especially care about it, but it's in there.
        expected_methods = set(['test1', 'test2', self.teardown_method_name, 'classTearDown', 'run'])
        seen_methods = self.get_seen_methods(self.test_reporter.test_complete.calls)
        # This produces a clearer diff than simply asserting the sets are
        # equal.
        assert_equal(expected_methods.symmetric_difference(seen_methods), set())

        # Verify the failed class_teardown method is not re-queued for running
        # -- it doesn't make sense to re-run a "flaky" class_teardown.
        assert_equal(self.server.test_queue.empty(), True)


class TestRunnerServerExceptionInClassTeardownTestCase(TestRunnerServerExceptionInTeardownPhaseBaseTestCase):
    def build_test_case(self):
        self.dummy_test_case = ExceptionInClassFixtureSampleTests.FakeClassTeardownTestCase
        self.teardown_method_name = 'class_teardown_raises_exception'


class TestRunnerServerExceptionInTeardownPhaseOfClassSetupTeardownTestCase(TestRunnerServerExceptionInTeardownPhaseBaseTestCase):
    def build_test_case(self):
        self.dummy_test_case = ExceptionInClassFixtureSampleTests.FakeTeardownPhaseOfClassSetupTeardownTestCase
        self.teardown_method_name = 'class_setup_teardown_raises_exception_in_teardown_phase'


class FailureLimitTestCaseMixin(object):
    """A mixin containing dummy test cases for verifying failure limit behavior."""

    class FailureLimitTestCase(test_case.TestCase):
        """Basic test case containing test methods which fail."""
        TEST_CASE_FAILURE_LIMIT = 0

        def __init__(self, *args, **kwargs):
            test_case.TestCase.__init__(self, *args, **kwargs)
            self.failure_limit = self.TEST_CASE_FAILURE_LIMIT

        def test1(self):
            assert False, "I am the first failure. failure_limit is %s" % self.failure_limit

        def test2(self):
            assert False, "I am the second (and last) failure. failure_limit is %s" % self.failure_limit

        def test3(self):
            assert False, "This test should not run because failure_count (%s) >= failure_limit (%s)." % (self.failure_count, self.failure_limit)

    class TestCaseFailureLimitTestCase(FailureLimitTestCase):
        TEST_CASE_FAILURE_LIMIT = 2

    class FailureLimitClassTeardownFailureTestCase(FailureLimitTestCase):
        """Add failing class_teardown methods to FailureLimitTestCase."""

        CLASS_TEARDOWN_FAILURES = 2

        @class_teardown
        def teardown1(self):
            assert False, "I am the failure beyond the last failure. failure_limit is %s" % self.failure_limit

        @class_teardown
        def teardown2(self):
            assert False, "I am the second failure beyond the last failure. failure_limit is %s" % self.failure_limit

    class TestCaseFailureLimitClassTeardownFailureTestCase(FailureLimitClassTeardownFailureTestCase):
        TEST_CASE_FAILURE_LIMIT = 2

    class FailureLimitClassTeardownErrorTestCase(FailureLimitTestCase):
        """Add to FailureLimitTestCase class_teardown methods which raises exceptions."""

        CLASS_TEARDOWN_FAILURES = 2

        @class_teardown
        def teardown_1(self):
            raise Exception("I am the failure beyond the last failure. failure_limit is %s" % self.failure_limit)

        @class_teardown
        def teardown_2(self):
            raise Exception("I am the second failure beyond the last failure. failure_limit is %s" % self.failure_limit)

    class TestCaseFailureLimitClassTeardownErrorTestCase(FailureLimitClassTeardownErrorTestCase):
        TEST_CASE_FAILURE_LIMIT = 2


class TestCaseFailureLimitTestCase(TestRunnerServerBaseTestCase, FailureLimitTestCaseMixin):
    """Verify that test methods are not run after TestCase.failure_limit is
    reached.
    """

    def build_test_case(self):
        self.dummy_test_case = FailureLimitTestCaseMixin.TestCaseFailureLimitTestCase

    def test_methods_are_not_run_after_failure_limit_reached(self):
        get_test(self.server, 'runner')
        self.run_test('runner')
        # Verify that only N failing tests are run, where N is the test case's
        # failure_limit.
        assert_equal(self.test_instance.failure_count, self.dummy_test_case.TEST_CASE_FAILURE_LIMIT)


class TestCaseFailureLimitClassTeardownFailureTestCase(TestRunnerServerBaseTestCase, FailureLimitTestCaseMixin):
    """Verify that failures in class_teardown methods are counted even after
    failure_limit is reached.
    """

    def build_test_case(self):
        self.dummy_test_case = FailureLimitTestCaseMixin.TestCaseFailureLimitClassTeardownFailureTestCase

    def test_methods_are_not_run_after_failure_limit_reached(self):
        get_test(self.server, 'runner')
        self.run_test('runner')
        # Let N = the test case's failure limit
        # Let C = the number of class_teardown methods with failures
        # N failing tests will run, followed by C class_teardown methods.
        # So the test case's failure_count should be N + C.
        assert_equal(self.test_instance.failure_count, self.dummy_test_case.TEST_CASE_FAILURE_LIMIT + self.dummy_test_case.CLASS_TEARDOWN_FAILURES)


class TestCaseFailureLimitClassTeardownErrorTestCase(TestCaseFailureLimitClassTeardownFailureTestCase):
    """Verify that errors in class_teardown methods are counted even after
    failure_limit is reached.

    We modify the dummy test case to have class_teardown methods which raise
    exceptions and let the test methods from the parent class do the
    verification.
    """

    def build_test_case(self):
        self.dummy_test_case = FailureLimitTestCaseMixin.TestCaseFailureLimitClassTeardownErrorTestCase


class TestRunnerServerFailureLimitTestCase(TestRunnerServerBaseTestCase, FailureLimitTestCaseMixin):
    """Verify that test methods are not run after TestRunnerServer.failure_limit is
    reached.
    """

    TEST_RUNNER_SERVER_FAILURE_LIMIT = 2

    def build_test_case(self):
        self.dummy_test_case = FailureLimitTestCaseMixin.FailureLimitTestCase

    def start_server(self):
        """Call parent's start_server but with a failure_limit."""
        super(TestRunnerServerFailureLimitTestCase, self).start_server(failure_limit=self.TEST_RUNNER_SERVER_FAILURE_LIMIT)

    def test_methods_are_not_run_after_failure_limit_reached(self):
        assert_equal(self.server.failure_count, 0)
        get_test(self.server, 'runner')
        assert_raises_and_contains(
            ValueError,
            'FailureLimitTestCase not checked out.',
            self.run_test,
            'runner',
        )
        # Verify that only N failing tests are run, where N is the server's
        # failure_limit.
        assert_equal(self.server.failure_count, self.TEST_RUNNER_SERVER_FAILURE_LIMIT)


class TestRunnerServerFailureLimitClassTeardownFailureTestCase(TestRunnerServerBaseTestCase, FailureLimitTestCaseMixin):
    """Verify that test methods are not run after TestRunnerServer.failure_limit is
    reached, but class_teardown methods (which might continue to bump
    failure_count) are still run.
    """

    TEST_RUNNER_SERVER_FAILURE_LIMIT = 2

    def build_test_case(self):
        self.dummy_test_case = FailureLimitTestCaseMixin.FailureLimitClassTeardownFailureTestCase

    def start_server(self):
        """Call parent's start_server but with a failure_limit."""
        super(TestRunnerServerFailureLimitClassTeardownFailureTestCase, self).start_server(failure_limit=self.TEST_RUNNER_SERVER_FAILURE_LIMIT)

    def test_class_teardown_counted_as_failure_after_limit_reached(self):
        assert_equal(self.server.failure_count, 0)
        get_test(self.server, 'runner')

        # The following behavior is bad because it doesn't allow clients to
        # report class_teardown failures (which they are contractually
        # obligated to run regardless of any failure limit). See
        # https://github.com/Yelp/Testify/issues/120 for ideas about how to fix
        # this.
        #
        # For now, we write this test to pin down the existing behavior and
        # notice if it changes.
        test_case_name = self.dummy_test_case.__name__
        assert_raises_and_contains(
            ValueError,
            '%s not checked out.' % test_case_name,
            self.run_test,
            'runner',
        )
        # Verify that only N failing tests are run, where N is the server's
        # failure_limit.
        #
        # Once issue #120 is fixed, the failure count should (probably) be
        # TEST_RUNNER_SERVER_FAILURE_LIMIT + CLASS_TEARDOWN_FAILURES.
        assert_equal(self.server.failure_count, self.TEST_RUNNER_SERVER_FAILURE_LIMIT)


class TestRunnerServerFailureLimitClassTeardownErrorTestCase(TestRunnerServerFailureLimitClassTeardownFailureTestCase):
    """Verify that test methods are not run after TestRunnerServer.failure_limit is
    reached, but class_teardown methods (which might continue to bump
    failure_count) are still run.

    We modify the dummy test case to have class_teardown methods which raise
    exceptions and let the test methods from the parent class do the
    verification.
    """

    def build_test_case(self):
        self.dummy_test_case = FailureLimitTestCaseMixin.FailureLimitClassTeardownErrorTestCase

def _replace_values_with_types(obj):
    # This makes it simple to compare the format of two dictionaries.
    if isinstance(obj, dict):
        return dict((key, _replace_values_with_types(val)) for key, val in obj.items())
    else:
        return type(obj).__name__


# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = base_class

import testify as T

class BaseClass(T.TestCase):
    __test__ = False
    def test_foo(self): pass

########NEW FILE########
__FILENAME__ = inheriting_class

from .base_class import BaseClass

class InheritingClass(BaseClass):
    __test__ = False

########NEW FILE########
__FILENAME__ = test_runner_test
import __builtin__
import contextlib
import imp
import mock
from testify import assert_equal
from testify import setup
from testify import setup_teardown
from testify import test_case
from testify import test_discovery
from testify import test_runner

from .test_runner_subdir.inheriting_class import InheritingClass
from .test_runner_bucketing import bucketing_test

prepared = False
running = False

def prepare_test_case(options, test_case):
    global prepared
    prepared = True

def run_test_case(options, test_case, runnable):
    global running
    running = True
    try:
        return runnable()
    finally:
        running = False


class TestTestRunnerGetTestMethodName(test_case.TestCase):

    def test_method_from_other_module_reports_class_module(self):
        ret = test_runner.TestRunner.get_test_method_name(
            InheritingClass.test_foo,
        )

        assert_equal(
            ret,
            '{0} {1}.{2}'.format(
                InheritingClass.__module__,
                InheritingClass.__name__,
                InheritingClass.test_foo.__name__,
            ),
        )

class PluginTestCase(test_case.TestCase):
    """Verify plugin support

    This is pretty complex and deserves some amount of explanation.
    What we're doing here is creating a module object on the fly (our plugin) and a
    test case class so we can call runner directly and verify the right parts get called.

    If you have a failure in here the stack is going to look crazy because we are a test case, being called by
    a test running, which is building and running ANOTHER test runner to execute ANOTHER test case. Cheers.
    """
    @setup
    def build_module(self):
        self.our_module = imp.new_module("our_module")
        setattr(self.our_module, "prepare_test_case", prepare_test_case)
        setattr(self.our_module, "run_test_case", run_test_case)

    @setup
    def build_test_case(self):
        self.ran_test = False
        class DummyTestCase(test_case.TestCase):
            def test(self_):
                self.ran_test = True
                assert self.our_module.prepared
                assert self.our_module.running

        self.dummy_test_class = DummyTestCase

    def test_plugin_run(self):
        runner = test_runner.TestRunner(self.dummy_test_class, plugin_modules=[self.our_module])

        assert runner.run()
        assert self.ran_test
        assert not running
        assert prepared


class TestTestRunnerGetTestsForSuite(test_case.TestCase):

    @setup_teardown
    def mock_out_things(self):
        mock_returned_test = mock.Mock()
        self.mock_test_method = mock.Mock()
        mock_returned_test.runnable_test_methods.return_value = [
            self.mock_test_method,
        ]
        with contextlib.nested(
            mock.patch.object(
                test_runner.TestRunner,
                'discover',
                autospec=True,
                return_value=[mock_returned_test],
            ),
            mock.patch.object(
                test_case.TestCase,
                'in_suite',
            ),
        ) as (
            self.discover_mock,
            self.in_suite_mock,
        ):
            yield

    def test_get_tests_for_suite_in_suite(self):
        self.in_suite_mock.return_value = True

        instance = test_runner.TestRunner(mock.sentinel.test_class)
        ret = instance.get_tests_for_suite(mock.sentinel.selected_suite_name)
        assert_equal(ret, [self.mock_test_method])

    def test_get_tests_for_suite_not_in_suite(self):
        self.in_suite_mock.return_value = False

        instance = test_runner.TestRunner(mock.sentinel.test_class)
        ret = instance.get_tests_for_suite(mock.sentinel.selected_suite_name)
        assert_equal(ret, [])


class TestTestRunnerPrintsTestNames(test_case.TestCase):

    @setup_teardown
    def mock_out_things(self):
        with contextlib.nested(
            mock.patch.object(
                test_runner.TestRunner,
                'get_tests_for_suite',
                autospec=True,
                return_value=[mock.sentinel.test1, mock.sentinel.test2],
            ),
            mock.patch.object(
                test_runner.TestRunner,
                'get_test_method_name',
            ),
            mock.patch.object(
                __builtin__,
                'print',
                autospec=True,
            ),
        ) as (
            self.get_tests_for_suite_mock,
            self.get_test_method_name_mock,
            self.print_mock,
        ):
            yield

    def test_prints_one_per_line(self):
        instance = test_runner.TestRunner(mock.sentinel.test_class)
        instance.list_tests(mock.sentinel.selected_suite_name)
        self.print_mock.assert_has_calls([
            mock.call(self.get_test_method_name_mock.return_value)
            for _ in self.get_tests_for_suite_mock.return_value
        ])


class TestMoreFairBucketing(test_case.TestCase):
    """This tests the "more fair bucketing" approach to bucketing tests.

    The algorithm for bucketing tests is as follows:

    - If there is no bucketing, don't sort or bucket
    - Otherwise bucket as follows:

        1. Sort the tests, first by number of tests and then by name
           (Sorting by name is merely for determinism)
        2. In order, round robin associate the tests with a bucket
           following this pattern:

           (for example 3 buckets)
           1 2 3 3 2 1 1 2 3 (etc.)
    """

    all_tests = (
        bucketing_test.TestCaseWithManyTests,
        bucketing_test.TestCaseWithFewTests,
        bucketing_test.AAA_FirstTestCaseWithSameNumberOfTests,
        bucketing_test.ZZZ_SecondTestCaseWithSameNumberOfTests,
    )

    all_tests_sorted_by_number_of_tests = (
        all_tests[0],
        all_tests[2],
        all_tests[3],
        all_tests[1],
    )

    @setup_teardown
    def mock_out_test_discovery(self):
        with mock.patch.object(
            test_discovery,
            'discover',
            autospec=True,
        ) as self.discover_mock:
            yield

    def assert_types_of_discovered(self, discovered, expected):
        assert_equal(tuple(map(type, discovered)), tuple(expected))

    def test_bucketing_no_buckets(self):
        self.discover_mock.return_value = self.all_tests

        instance = test_runner.TestRunner(mock.sentinel.test_path)
        discovered = instance.discover()
        # The tests we discover should be in the order that test_discovery
        # returns them as
        self.assert_types_of_discovered(discovered, self.all_tests)

    def test_bucketing_one_bucket(self):
        """Trivial base case, should return similar to no_buckets, but with sorting"""
        self.discover_mock.return_value = self.all_tests

        instance = test_runner.TestRunner(mock.sentinel.test_path, bucket=0, bucket_count=1)
        discovered = instance.discover()
        self.assert_types_of_discovered(discovered, self.all_tests_sorted_by_number_of_tests)

    def test_multiple_buckets(self):
        self.discover_mock.return_value = self.all_tests

        # Buckets should be assigned:
        # 0 -> TestCaseWithManyTesets, TestCaseWithFewTests
        # 1 -> AAA_FirstTestCaseWithSameNumberOfTests, ZZZ_SecondTestCaseWithSameNumberOfTests
        instance = test_runner.TestRunner(mock.sentinel.test_path, bucket=0, bucket_count=2)
        discovered = instance.discover()
        self.assert_types_of_discovered(
            discovered,
            (
                bucketing_test.TestCaseWithManyTests,
                bucketing_test.TestCaseWithFewTests,
            ),
        )

        instance = test_runner.TestRunner(mock.sentinel.test_path, bucket=1, bucket_count=2)
        discovered = instance.discover()
        self.assert_types_of_discovered(
            discovered,
            (
                bucketing_test.AAA_FirstTestCaseWithSameNumberOfTests,
                bucketing_test.ZZZ_SecondTestCaseWithSameNumberOfTests,
            ),
        )

    def test_bucketing_with_filtering(self):
        self.discover_mock.return_value = self.all_tests
        instance = test_runner.TestRunner(
            mock.sentinel.test_path,
            bucket=0,
            bucket_count=1,
            module_method_overrides={
                self.all_tests[0].__name__: set(),
            },
        )
        
        discovered = instance.discover()
        self.assert_types_of_discovered(discovered, (self.all_tests[0],))

########NEW FILE########
__FILENAME__ = test_suites_test
import unittest
from types import MethodType

from testify import TestCase, assert_equal, suite
from testify.test_runner import TestRunner

_suites = ['module-level']


class TestSuitesTestCase(TestCase):

    def test_subclass_suites_doesnt_affect_superclass_suites(self):
        """Check that setting _suites in a subclass only affects that subclass, not the superclass.
        Checking https://github.com/Yelp/Testify/issues/53"""
        class SuperTestCase(TestCase):
            _suites = ['super']
            def test_thing(self):
                pass

        class SubTestCase(SuperTestCase):
            _suites = ['sub']

        # If we set suites_require=['super'], then only the superclass should have a method to run.
        super_instance = SuperTestCase(suites_require=set(['super']))
        sub_instance = SubTestCase(suites_require=set(['super']))

        assert_equal(list(super_instance.runnable_test_methods()), [super_instance.test_thing])
        assert_equal(list(sub_instance.runnable_test_methods()), [sub_instance.test_thing])

        # Conversely, if we set suites_require=['sub'], then only the subclass should have a method to run.
        super_instance = SuperTestCase(suites_require=set(['sub']))
        sub_instance = SubTestCase(suites_require=set(['sub']))

        assert_equal(list(super_instance.runnable_test_methods()), [])
        assert_equal(list(sub_instance.runnable_test_methods()), [sub_instance.test_thing])

    def test_suite_decorator_overrides_parent(self):
        """Check that the @suite decorator overrides any @suite on the overridden (parent class) method."""
        class SuperTestCase(TestCase):
            @suite('super')
            def test_thing(self):
                pass

        class SubTestCase(SuperTestCase):
            __test__ = False

            @suite('sub')
            def test_thing(self):
                pass

        super_instance = SuperTestCase()
        sub_instance = SubTestCase()

        assert_equal(super_instance.test_thing._suites, set(['super']))
        assert_equal(sub_instance.test_thing._suites, set(['sub']))


class ListSuitesMixin(object):
    """Test that we pick up the correct suites when using --list-suites."""

    # applied to test_foo, test_disabled, test_also.., test_not.., and test_list..
    _suites = ['class-level-suite']

    def __init__(self, **kwargs):
        super(ListSuitesMixin, self).__init__(**kwargs)

        # add a dynamic test to guard against
        # https://github.com/Yelp/Testify/issues/85
        test = MethodType(lambda self: True, self, type(self))
        setattr(self, 'test_foo', test)

    @suite('disabled', 'crazy', conditions=True)
    def test_disabled(self): True

    @suite('disabled', reason='blah')
    def test_also_disabled(self): True

    @suite('not-applied', conditions=False)
    def test_not_disabled(self): True

    def test_list_suites(self):
        # for suites affecting all of this class's tests
        num_tests = len(list(self.runnable_test_methods()))

        test_runner = TestRunner(type(self))
        assert_equal(test_runner.list_suites(), {
            'disabled': '2 tests',
            'module-level': '%d tests' % num_tests,
            'class-level-suite': '%d tests' % num_tests,
            'crazy': '1 tests',
        })


class ListSuitesTestCase(TestCase, ListSuitesMixin):
    """Test that suites are correctly applied to Testify TestCases."""
    pass


class ListSuitesUnittestCase(unittest.TestCase, ListSuitesMixin):
    """Test that suites are correctly applied to UnitTests."""
    pass

########NEW FILE########
__FILENAME__ = define_testcase
from testify import TestCase

class DummyTestCase(TestCase):
    def test_blah(self):
        pass

########NEW FILE########
__FILENAME__ = define_unittestcase
import unittest

class DummyUnitTestCase(unittest.TestCase):
    def test_foo(self):
        assert True


########NEW FILE########
__FILENAME__ = import_testcase
from .define_testcase import DummyTestCase

__suites__ = 'blah'

########NEW FILE########
__FILENAME__ = inspection_test
from testify import TestCase
from testify import setup
from testify import turtle
from testify.utils import inspection

class DummyTestCase(TestCase):

    @setup
    def fixture(self):
        pass

    turtle_method = turtle.Turtle()

    def instance(self):
        pass

    @staticmethod
    def static():
        pass


class IsFixtureMethodTest(TestCase):

    def test_fixture(self):
        assert inspection.is_fixture_method(DummyTestCase.fixture)

    def test_turtle(self):
        """Turtles are callable but not fixtures!"""
        assert not inspection.is_fixture_method(DummyTestCase.turtle_method)

    def test_lambda(self):
        assert not inspection.is_fixture_method(lambda: None)

    def test_static_method(self):
        assert not inspection.is_fixture_method(DummyTestCase.static)

    def test_instance(self):
        assert not inspection.is_fixture_method(DummyTestCase.instance)


class CallableSetattrTest(TestCase):

    def test_set_function_attr(self):
        function = lambda: None
        inspection.callable_setattr(function, 'foo', True)
        assert function.foo

    def test_set_method_attr(self):
        inspection.callable_setattr(DummyTestCase.fixture, 'foo', True)
        assert DummyTestCase.fixture.foo




########NEW FILE########
__FILENAME__ = stringdiffer_test
from testify import TestCase
from testify import assert_equal
from testify import run
from testify.contrib.doctestcase import DocTestCase

from testify.utils import stringdiffer


class HighlightStringRegionsTestCase(TestCase):

    def test_it_highlights_string_regions(self):
        expected = '<Thi>s is <a> string.'
        actual = stringdiffer.highlight_regions('This is a string.',
                                                 [(0, 3), (8, 9)])
        assert_equal(expected, actual)


class HighlightStringTestCase(TestCase):

    def test_it_returns_strings_with_highlighted_regions(self):
        lhs = 'i am the best'
        rhs = 'i am the worst'

        expected_old = 'i am the <be>st'
        expected_new = 'i am the <wor>st'

        diff = stringdiffer.highlight(lhs, rhs)
        assert_equal(expected_old, diff.old)
        assert_equal(expected_new, diff.new)

    def test_it_returns_another_pair_with_highlighted_regions(self):
        lhs = 'i am the best'
        rhs = 'i am the greatest'

        expected_old = 'i am the <b>est'
        expected_new = 'i am the <great>est'

        diff = stringdiffer.highlight(lhs, rhs)
        assert_equal(expected_old, diff.old)
        assert_equal(expected_new, diff.new)

    def test_it_returns_two_highlighted_regions(self):
        lhs = 'thes strings are really close to each other'
        rhs = 'these strings are really close to eachother'

        expected_old = 'thes<> strings are really close to each other'
        expected_new = 'thes<e> strings are really close to each<>other'

        diff = stringdiffer.highlight(lhs, rhs)
        assert_equal(expected_old, diff.old)
        assert_equal(expected_new, diff.new)

    def test_it_does_a_good_job_with_reprs(self):
        lhs = '<Object(something=123, nothing=349)>'
        rhs = '<Object(something=93428, nothing=624)>'

        expected_old = '<Object(something=<123>, nothing=<349>)>'
        expected_new = '<Object(something=<93428>, nothing=<624>)>'

        diff = stringdiffer.highlight(lhs, rhs)
        assert_equal(expected_old, diff.old)
        assert_equal(expected_new, diff.new)


class DocTest(DocTestCase):
    module = stringdiffer


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = test_turtle
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from testify import *
from testify.contrib.doctestcase import DocTestCase

class TurtleTestCase(TestCase):
    @setup
    def build_turtle(self):
        self.leonardo = turtle.Turtle()

    def test_call(self):
        """Just call a turtle"""
        ret = self.leonardo()
        assert ret
        assert_length(self.leonardo.returns, 1)
        assert_call(self.leonardo, 0)
        assert_equal(ret, self.leonardo.returns[0])

    def test_attribute(self):
        """Check our attribute access"""
        assert self.leonardo.is_awesome().and_can_chain().whatever_he_wants()

    def test_call_record(self):
        """Check that calls are recorded"""
        self.leonardo(1, 2, 3, quatro=4)
        assert_length(self.leonardo.calls, 1)
        assert_call(self.leonardo, 0, 1, 2, 3, quatro=4)
        self.leonardo(5, six=6)
        assert_call(self.leonardo, 1, 5, six=6)
    
    def test_attribute_setting(self):
        """Check that we can set attributes and pull them back out"""
        self.leonardo.color = "blue"
        assert_equal(self.leonardo.color, "blue")
    
    def test_attribute_persistence(self):
        """When an attribute is built, it should be persisted"""
        weapon = self.leonardo.weapon
        assert_equal(weapon, self.leonardo.weapon)
        assert weapon is self.leonardo.weapon


class DocTest(DocTestCase):
    module = turtle

########NEW FILE########
__FILENAME__ = assertions
# -*- coding: utf-8 -*-
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import with_statement

import contextlib
from itertools import islice
import re
import warnings

from .utils import stringdiffer


__testify = 1


def _val_subtract(val1, val2, dict_subtractor, list_subtractor):
    """
    Find the difference between two container types

    Returns:

    The difference between the values as defined by list_subtractor() and
    dict_subtractor() if both values are the same container type.

    None if val1 == val2
    val1 if type(val1) != type(val1)
    Otherwise - the difference between the values
    """

    if val1 == val2:
        # if the values are the same, return a degenerate type
        # this case is not used by list_subtract or dict_subtract
        return type(val1)()

    if isinstance(val1, dict) and isinstance(val2, dict):
        val_diff = dict_subtractor(val1, val2)
    elif isinstance(val1, (list, tuple)) and isinstance(val2, (list, tuple)):
        val_diff = list_subtractor(val1, val2)
    else:
        val_diff = val1

    return val_diff


def _dict_subtract(dict1, dict2):
    """
    Return key,value pairs from dict1 that are not in dict2

    Returns:
    A new dict 'res_dict' with the following properties:

    For all (key, val) pairs where key appears in dict2:

    if dict1[val] == dict2[val] then res_dict[val] is not defined
    else res_dict[val] == dict1[val]

    If vals are themselves dictionaries the algorim is applied recursively.

    Example:
        _dict_subtract({
                       1: 'one',
                       2: 'two',
                       3: {'a': 'A', 'b': 'B'},
                       4: {'c': 'C', 'd': 'D'}
                      },
                      {
                       2: 'two',
                       3: {'a': 'A', 'b': 'B'},
                       4: {'d': 'D'},
                       5: {'e': 'E'}
                      }) => {1: 'one', 4: {'c': 'C'}}
    """

    # make a result we can edit
    result = dict(dict1)

    # find the common keys -- i.e., the ones we might need to subtract
    common_keys = set(dict1.keys()) & set(dict2.keys())
    for key in common_keys:
        val1, val2 = dict1[key], dict2[key]

        if val1 == val2:
            # values are the same: subtract
            del result[key]
        else:
            # values are different: set the output key to the different between the values
            result[key] = _val_subtract(val1, val2, _dict_subtract, _list_subtract)

    return result


def _list_subtract(list1, list2):
    """
    Returns the difference between list1 and list2.

    _list_subtract([1,2,3], [3,2,1]) == [1,3]

    If any items in the list are container types, the method recursively calls
    itself or _dict_subtract() to subtract the child
    containers.
    """

    # call val_subtract on all items that are not the same
    res_list = [_val_subtract(val1, val2, _dict_subtract, _list_subtract)
                for val1, val2 in zip(list1, list2) if val1 != val2]

    # now append items that come after any item in list1
    res_list += list1[len(list2):]

    # return a tuple of list1 is a tuple
    if isinstance(list1, tuple):
        return tuple(res_list)
    else:
        return res_list


def assert_raises(*args, **kwargs):
    """Assert an exception is raised as a context manager or by passing in a
    callable and its arguments.

    As a context manager:
    >>> with assert_raises(Exception):
    ...     raise Exception

    Pass in a callable:
    >>> def raise_exception(arg, kwarg=None):
    ...     raise Exception
    >>> assert_raises(Exception, raise_exception, 1, kwarg=234)
    """
    if (len(args) == 1) and not kwargs:
        return _assert_raises_context_manager(args[0])
    else:
        return _assert_raises(*args, **kwargs)


def assert_raises_such_that(exception_class, exception_test=lambda e: e, callable_obj=None, *args, **kwargs):
    """
    Assert that an exception is raised such that expection_test(exception)
    passes, either in a with statement via a context manager or while calling
    a given callable on given arguments.

    Arguments:
        exception_class - class corresponding to the expected exception
        exception_test - a callable which takes an exception instance and
            asserts things about it
        callable_obj, *args, **kwargs - optional, a callable object and
            arguments to pass into it which when used are expected to raise the
            exception; if not provided, this function returns a context manager
            which will check that the assertion is raised within the context
            (the body of the with statement).

    As a context manager:
    >>> says_whatever = lambda e: assert_equal(str(e), "whatever")
    >>> with assert_raises_such_that(Exception, says_whatever):
    ...     raise Exception("whatever")

    Pass in a callable:
    >>> says_whatever = lambda e: assert_equal(str(e), "whatever")
    >>> def raise_exception(arg, kwarg=None):
    ...     raise Exception("whatever")
    >>> assert_raises_such_that(Exception, says_whatever, raise_exception, 1, kwarg=234)
    """
    if callable_obj is None:
        return _assert_raises_context_manager(exception_class, exception_test)
    else:
        with _assert_raises_context_manager(exception_class, exception_test):
            callable_obj(*args, **kwargs)


def assert_raises_exactly(exception_class, *args):
    """
    Assert that a particular exception_class is raised with particular arguments.
    Use this assertion when the exception message is important.
    """
    def test_exception(exception):
        # We want to know the exact exception type, not that it has some superclass.
        assert_is(type(exception), exception_class)
        assert_equal(exception.args, args)

    return assert_raises_such_that(exception_class, test_exception)


def assert_raises_and_contains(expected_exception_class, strings, callable_obj, *args, **kwargs):
    """Assert an exception is raised by passing in a callable and its
    arguments and that the string representation of the exception
    contains the case-insensitive list of passed in strings.

    Args
        strings -- can be a string or an iterable of strings
    """
    try:
        callable_obj(*args, **kwargs)
    except expected_exception_class, e:
        message = str(e).lower()
        if isinstance(strings, basestring):
            strings = [strings]
        for string in strings:
            assert_in(string.lower(), message)
    else:
        assert_not_reached("No exception was raised (expected %s)" % expected_exception_class)


@contextlib.contextmanager
def _assert_raises_context_manager(exception_class, exception_test=lambda e: e):
    """Builds a context manager for testing that code raises an assertion.

    Args:
        exception_class - a subclass of Exception
        exception_test - optional, a function to apply to the exception (to
            test something about it)
    """
    try:
        yield
    except exception_class as e:
        exception_test(e)
    else:
        assert_not_reached("No exception was raised (expected %r)" %
                           exception_class)


def _assert_raises(exception_class, callable, *args, **kwargs):
    with _assert_raises_context_manager(exception_class):
        callable(*args, **kwargs)


def _diff_message(lhs, rhs):
    """If `lhs` and `rhs` are strings, return the a formatted message
    describing their differences. If they're not strings, describe the
    differences in their `repr()`s.

    NOTE: Only works well for strings not containing newlines.
    """
    lhs = _to_characters(lhs)
    rhs = _to_characters(rhs)

    message = u'Diff:\nl: %s\nr: %s' % stringdiffer.highlight(lhs, rhs)
    # Python2 exceptions require bytes.
    return message.encode('UTF-8')


def assert_equal(lval, rval, message=None):
    """Assert that lval and rval are equal."""
    if message:
        assert lval == rval, message
    else:
        assert lval == rval, \
            "assertion failed: l == r\nl: %r\nr: %r\n\n%s" % \
                (lval, rval, _diff_message(lval, rval))


assert_equals = assert_equal


def assert_true(lval, message=None):
    """Assert that lval evaluates to True, not identity."""
    if message:
        assert bool(lval) == True, message
    else:
        assert bool(lval) == True, \
            "assertion failed: l == r\nl: %r\nr: %r\n\n%s" % \
                (lval, True, _diff_message(lval, True))


def assert_false(lval, message=None):
    """Assert that lval evaluates to False, not identity."""
    if message:
        assert bool(lval) == False, message
    else:
        assert bool(lval) == False, \
            "assertion failed: l == r\nl: %r\nr: %r\n\n%s" % \
                (lval, False, _diff_message(lval, False))


def assert_almost_equal(lval, rval, digits, message=None):
    """Assert that lval and rval, when rounded to the specified number of digits, are the same."""
    real_message = message or "%r !~= %r" % (lval, rval)
    assert round(lval, digits) == round(rval, digits), real_message


def assert_within_tolerance(lval, rval, tolerance, message=None):
    """Assert that the difference between the two values, as a fraction of the left value, is smaller than the tolerance specified.
    That is, abs(float(lval) - float(rval)) / float(lval) < tolerance"""
    real_message = message or "%r !~= %r" % (lval, rval)
    assert abs(float(lval) - float(rval)) / float(lval) < tolerance, real_message


def assert_not_equal(lval, rval, message=None):
    """Assert that lval and rval are unequal to each other."""
    if message:
        assert lval != rval, message
    else:
        assert lval != rval, 'assertion failed: %r != %r' % (lval, rval)


def assert_lt(lval, rval, message=None):
    """Assert that lval is less than rval."""
    if message:
        assert lval < rval, message
    else:
        assert lval < rval, 'assertion failed: %r < %r' % (lval, rval)


def assert_lte(lval, rval, message=None):
    """Assert that lval is less than or equal to rval"""
    if message:
        assert lval <= rval, message
    else:
        assert lval <= rval, 'assertion failed: %r <= %r' % (lval, rval)


def assert_gt(lval, rval, message=None):
    """Assert that lval is greater than rval."""
    if message:
        assert lval > rval, message
    else:
        assert lval > rval, 'assertion failed: %r > %r' % (lval, rval)


def assert_gte(lval, rval, message=None):
    """Assert that lval is greater than or equal to rval"""
    if message:
        assert lval >= rval, message
    else:
        assert lval >= rval, 'assertion failed: %r >= %r' % (lval, rval)


def assert_in_range(val, start, end, message=None, inclusive=False):
    """Assert that val is greater than start and less than end. If inclusive is true, val may be equal to start or end."""
    if inclusive:
        real_message = message or "! %s <= %r <= %r" % (start, val, end)
        assert start <= val <= end, real_message
    else:
        real_message = message or "! %s < %r < %r" % (start, val, end)
        assert start < val < end, real_message


def assert_between(a, b, c):
    """Assert that b is between a and c, inclusive."""
    assert_in_range(b, a, c, inclusive=True)


def assert_in(item, sequence, message="assertion failed: expected %(item)r in %(sequence)r", msg=None):
    """Assert that the item is in the sequence."""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    assert item in sequence, message % {'item':item, 'sequence':sequence}

def assert_not_in(item, sequence, message="assertion failed: expected %(item)r not in %(sequence)r", msg=None):
    """Assert that the item is not in the sequence."""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    assert item not in sequence, message % {'item':item, 'sequence':sequence}


def assert_all_in(left, right):
    """Assert that everything in `left` is also in `right`
    Note: This is different than `assert_subset()` because python sets use
    `__hash__()` for comparision whereas `in` uses `__eq__()`.
    """
    unmatching = []
    for item in left:
        if item not in right:
            unmatching.append(item)
    if unmatching:
        raise AssertionError(
            'The following items were not found in %s: %s' % (right, unmatching)
        )


def assert_starts_with(val, prefix):
    """Assert that val.startswith(prefix)."""
    message = "%(val)r does not start with %(prefix)r" % locals()
    assert val.startswith(prefix), message


def assert_not_reached(message=None):
    """Raise an AssertionError with a message."""
    if message:
        assert False, message
    else:
        assert False, 'egads! this line ought not to have been reached'


def assert_rows_equal(rows1, rows2):
    """Check that two sequences contain the same lists of dictionaries"""

    def norm_row(row):
        if isinstance(row, dict):
            return tuple((k, row[k]) for k in sorted(row))
        else:
            return tuple(sorted(row))

    def norm_rows(rows):
        return tuple(sorted(norm_row(row) for row in rows))

    assert_equal(norm_rows(rows1), norm_rows(rows2))


def assert_empty(iterable, max_elements_to_print=None, message=None):
    """
    Assert that an iterable contains no values.

    Args:
        iterable - any iterable object
        max_elements_to_print - int or None, maximum number of elements from
            iterable to include in the error message. by default, includes all
            elements from iterables with a len(), and 10 elements otherwise.
            if max_elements_to_print is 0, no sample is printed.
        message - str or None, custom message to print if the iterable yields.
            a sample is appended to the end unless max_elements_to_print is 0.
    """
    # Determine whether or not we can print all of iterable, which could be
    # an infinite (or very slow) generator.
    if max_elements_to_print is None:
        try:
            max_elements_to_print = len(iterable)
        except TypeError:
            max_elements_to_print = 10

    # Build the message *before* touching iterable since that might modify it.
    message = message or "iterable {0} was unexpectedly non-empty.".format(iterable)

    # Get the first max_elements_to_print + 1 items from iterable, or just
    # the first item if max_elements_to_print is 0.  Trying to get an
    # extra item by adding 1 to max_elements_to_print lets us tell whether
    # we got everything in iterator, regardless of if it has len() defined.
    if max_elements_to_print == 0:
        sample = list(islice(iterable, 0, 1))
    else:
        sample_plus_extra = list(islice(iterable, 0, max_elements_to_print + 1))
        sample_is_whole_iterable = len(sample_plus_extra) <= max_elements_to_print
        sample = sample_plus_extra[:max_elements_to_print]

        if sample_is_whole_iterable:
            message += ' elements: %s' % sample
        else:
            message += ' first %s elements: %s' % (len(sample), sample)

    assert len(sample) == 0, message


def assert_not_empty(iterable, message=None):
    """
    Assert that an iterable is not empty (by trying to loop over it).

    Args:
        iterable - any iterable object
        message - str or None, message to print if the iterable doesn't yield
    """
    for value in iterable:
        break
    else:
        # The else clause of a for loop is reached iff you break out of the loop.
        raise AssertionError(message if message else
            "iterable {0} is unexpectedly empty".format(iterable)
        )


def assert_length(sequence, expected, message=None):
    """Assert a sequence or iterable has an expected length."""
    message = message or "%(sequence)s has length %(length)s expected %(expected)s"
    length = len(list(sequence))
    assert length == expected, message % locals()


def assert_call(turtle, call_idx, *args, **kwargs):
    """Assert that a function was called on turtle with the correct args."""
    actual = turtle.calls[call_idx] if turtle.calls else None
    message = "Call %s expected %s, was %s" % (call_idx, (args, kwargs), actual)
    assert actual == (args, kwargs), message


def assert_is(left, right, message="expected %(left)r is %(right)r", msg=None):
    """Assert that left and right are the same object"""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    assert left is right, message % {'left':left, 'right': right}


def assert_is_not(left, right, message="expected %(left)r is not %(right)r", msg=None):
    """Assert that left and right are NOT the same object"""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    assert left is not right, message % {'left':left, 'right':right}


def assert_all_match_regex(pattern, values, message="expected %(value)r to match %(pattern)r", msg=None):
    """Assert that all values in an iterable match a regex pattern.

    Args:
    pattern -- a regex.
    values -- an iterable of values to test.

    Raises AssertionError if any value does not match.

    """
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    for value in values:
        assert re.match(pattern, value), message % {'value':value, 'pattern':pattern}


def assert_match_regex(pattern, value, *args, **kwargs):
    """Assert that a single value matches a regex pattern."""
    assert_all_match_regex(pattern, [value], *args, **kwargs)


def assert_any_match_regex(pattern, values, message="expected at least one %(values)r to match %(pattern)r", msg=None):
    """Assert that at least one value in an iterable matches a regex pattern.

    Args:
    pattern -- a regex.
    values -- an iterable of values to test.

    Raises AssertionError if all values don't match.

    """
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    for value in values:
        if re.match(pattern, value) is not None:
            return

    raise AssertionError(message % {'values':values, 'pattern':pattern})


def assert_all_not_match_regex(pattern, values, message="expected %(value)r to not match %(pattern)r", msg=None):
    """Assert that all values don't match a regex pattern.

    Args:
    pattern -- a regex.
    values -- an iterable of values to test.

    Raises AssertionError if any values matches.

    """
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    for value in values:
        assert not re.match(pattern, value), message % {'value':value, 'pattern':pattern}


def assert_sets_equal(left, right, message="expected %(left)r == %(right)r [left has:%(extra_left)r, right has:%(extra_right)r]", msg=None):
    """Assert that two sets are equal."""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    if left != right:
        extra_left = left - right
        extra_right = right - left
        raise AssertionError(message % {
            'left': left,
            'right': right,
            'extra_left': extra_left,
            'extra_right': extra_right,
        })


def assert_dicts_equal(left, right, ignore_keys=None, message="expected %(left)r == %(right)r [left has:%(extra_left)r, right has:%(extra_right)r]", msg=None):
    """Assert that two dictionarys are equal (optionally ignoring certain keys)."""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    if ignore_keys is not None:
        left = dict((k, left[k]) for k in left if k not in ignore_keys)
        right = dict((k, right[k]) for k in right if k not in ignore_keys)

    if left == right:
        return

    extra_left = _dict_subtract(left, right)
    extra_right = _dict_subtract(right, left)
    raise AssertionError(message % {
        'left': left,
        'right': right,
        'extra_left': extra_left,
        'extra_right': extra_right,
    })


def assert_dict_subset(left, right, message="expected [subset has:%(extra_left)r, superset has:%(extra_right)s]", msg=None):
    """Assert that a dictionary is a strict subset of another dictionary (both keys and values)."""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    difference_dict = _dict_subtract(left, right)

    if not difference_dict:
        return

    extra_left = difference_dict
    small_right = dict((k, right[k]) for k in right if k in left.keys())
    extra_right = _dict_subtract(small_right, left)
    raise AssertionError(message % {
        'left': left,
        'right': right,
        'extra_left': extra_left,
        'extra_right': extra_right,
    })


def assert_subset(left, right, message="expected %(set_left)r <= %(set_right)r [left has:%(extra)r]", msg=None):
    """Assert that the left set is a subset of the right set."""
    if msg:
        warnings.warn("msg is deprecated", DeprecationWarning)
        message = msg

    set_left = set(left)
    set_right = set(right)
    if not (set_left <= set_right):
        extra = set_left - set_right
        raise AssertionError(message % {
            'left': left,
            'right': right,
            'set_left': set_left,
            'set_right': set_right,
            'extra': extra,
        })


def assert_list_prefix(left, right):
    """Assert that the left list is a prefix of the right list."""
    assert_equal(left, right[:len(left)])


def assert_sorted_equal(left, right, **kwargs):
    """Assert equality, but without respect to ordering of elements. Basically for multisets."""
    assert_equal(sorted(left), sorted(right), **kwargs)


def assert_isinstance(object_, type_):
    """Assert that an object is an instance of a given type."""
    assert isinstance(object_, type_), "Expected type %r but got type %r" % (type_, type(object_))


def assert_datetimes_equal(a, b):
    """Tests for equality of times by only testing up to the millisecond."""
    assert_equal(a.utctimetuple()[:-3], b.utctimetuple()[:-3], "%r != %r" % (a, b))


def assert_exactly_one(*args, **kwargs):
    """Assert that only one of the given arguments passes the provided truthy function (non-None by default).

    Args:
        truthy_fxn: a filter to redefine truthy behavior. Should take an object and return
        True if desired conditions are satisfied. For example:

        >>> assert_exactly_one(True, False, truthy_fxn=bool) # Success
        True

        >>> assert_exactly_one(0, None) # Success
        0

        >>> assert_exactly_one(True, False)
        Traceback (most recent call last):
            ...
        AssertionError: Expected exactly one True (got 2) args: (True, False)

    Returns:
        The argument that passes the truthy function
    """
    truthy_fxn = kwargs.pop('truthy_fxn', lambda x: x is not None)
    assert not kwargs, "Unexpected kwargs: %r" % kwargs

    true_args = [arg for arg in args if truthy_fxn(arg)]
    if len(true_args) != 1:
        raise AssertionError("Expected exactly one True (got %d) args: %r" % (len(true_args), args))

    return true_args[0]


@contextlib.contextmanager
def _assert_warns_context_manager(warning_class=None, warnings_test=None):
    """
    Builds a context manager for testing code that should throw a warning.
    This will look for a given class, call a custom test, or both.

    Args:
        warning_class - a class or subclass of Warning. If not None, then
            the context manager will raise an AssertionError if the block
            does not throw at least one warning of that type.
        warnings_test - a function which takes a list of warnings caught,
            and makes a number of assertions about the result. If the function
            returns without an exception, the context manager will consider
            this a successful assertion.
    """
    with warnings.catch_warnings(record=True) as caught:
        # All warnings should be triggered.
        warnings.resetwarnings()
        if warning_class:
            warnings.simplefilter('ignore')
            warnings.simplefilter('always', category=warning_class)
        else:
            warnings.simplefilter('always')
        # Do something that ought to trigger a warning.
        yield
        # We should have received at least one warning.
        assert_gt(len(caught), 0, 'expected at least one warning to be thrown')
        # Run the custom test against the warnings we caught.
        if warnings_test:
            warnings_test(caught)


def assert_warns(warning_class=None, callable=None, *args, **kwargs):
    """Assert that the given warning class is thrown as a context manager
    or by passing in a callable and its arguments.

    As a context manager:
    >>> with assert_warns():
    ...     warnings.warn('Hey!')

    Passing in a callable:
    >>> def throw_warning():
    ...     warnings.warn('Hey!')
    >>> assert_warns(UserWarning, throw_warning)
    """
    if callable is None:
        return _assert_warns_context_manager(warning_class=warning_class)
    else:
        with _assert_warns_context_manager(warning_class=warning_class):
            callable(*args, **kwargs)


def assert_warns_such_that(warnings_test, callable=None, *args, **kwargs):
    """
    Assert that the given warnings_test function returns True when
    called with a full list of warnings that were generated by either
    a code block (when this is used as a context manager in a `with` statement)
    or the given callable (when called with the appropriate args and kwargs).

    As a context manager:
    >>> def two_warnings_thrown(warnings):
    ...     assert len(warnings) == 2
    >>> with assert_warns_such_that(two_warnings_thrown):
    ...     warnings.warn('Hey!')
    ...     warnings.warn('Seriously!')

    Passing in a callable:
    >>> def throw_warnings(count):
    ...     for n in range(count):
    ...         warnings.warn('Warning #%i' % n)
    >>> assert_warns_such_that(two_warnings_thrown, throw_warnings, 2)
    """
    if callable is None:
        return _assert_warns_context_manager(warnings_test=warnings_test)
    else:
        with _assert_warns_context_manager(warnings_test=warnings_test):
            callable(*args, **kwargs)


def _to_characters(x):
    """Return characters that represent the object `x`, come hell or high water."""
    if isinstance(x, unicode):
        return x
    try:
        return unicode(x, 'UTF-8')
    except UnicodeDecodeError:
        return unicode(x, 'latin1')
    except TypeError:
        # We're only allowed to specify an encoding for str values, for whatever reason.
        try:
            return unicode(x)
        except UnicodeDecodeError:
            # You get this (for example) when an error object contains utf8 bytes.
            try:
                return unicode(str(x), 'UTF-8')
            except UnicodeDecodeError:
                return unicode(str(x), 'latin1')
# vim:et:sts=4:sw=4:

########NEW FILE########
__FILENAME__ = doctestcase
import sys

from doctest import DocTestFinder, DocTestRunner, REPORT_NDIFF
from StringIO import StringIO
from testify import MetaTestCase, TestCase
from types import MethodType

class DocMetaTestCase(MetaTestCase):
    """See DocTestCase for documentation."""
    def __init__(cls, name, bases, dct):
        super(DocMetaTestCase, cls).__init__(name, bases, dct)

        try:
            module = dct['module']
        except KeyError:
            if dct.get('__test__', True) == False:
                # This is some kind of abstract class. Do nothing.
                return
            else:
                raise ValueError('No module was given for doctest search!')

        globs = dct.get('globs', None)
        extraglobs = dct.get('extraglobs', None)

        if isinstance(module, basestring):
            # transform a module name into a module
            module = sys.modules[module]

        for doctest in DocTestFinder(recurse=True).find(module, name='test_doc', globs=globs, extraglobs=extraglobs):
            cls.add_test(doctest)

    def add_test(cls, doctest):
        "add a test to this TestCase"
        if not doctest.examples:
            # There's no tests in this doctest. Don't bother.
            return

        test = lambda self: run_test(doctest)

        # Need to change dots to colons so that testify doesn't try to interpret them.
        testname = doctest.name.replace('.', ':')
        test.__name__ = doctest.name = testname

        test = MethodType(test, None, cls)
        vars(test)['_suites'] = set()

        setattr(cls, test.__name__, test)

def run_test(doctest):
    summary = StringIO()
    runner = DocTestRunner(optionflags=REPORT_NDIFF)
    runner.run(doctest, out=summary.write)

    assert runner.failures == 0, '\n' + summary.getvalue()

class DocTestCase(TestCase):
    """
    A testify TestCase that turns doctests into unit tests.

    Subclass attributes:
        module -- the module object to be introspected for doctests
        globs -- (optional) a dictionary containing the initial global variables for the tests.
            A new copy of this dictionary is created for each test.
        extraglobs -- (optional) an extra set of global variables, which is merged into globs.
    """
    __metaclass__ = DocMetaTestCase
    __test__ = False

########NEW FILE########
__FILENAME__ = deprecated_assertions
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


__testify = 1

def fail(self, msg=None):
    """Fail immediately, with the given message."""
    raise AssertionError, msg

def failIf(self, expr, msg=None):
    "Fail the test if the expression is true."
    if expr: raise AssertionError, msg

def failUnless(self, expr, msg=None):
    """Fail the test unless the expression is true."""
    if not expr: raise AssertionError, msg

def failUnlessRaises(self, excClass, callableObj, *args, **kwargs):
    """Fail unless an exception of class excClass is thrown
       by callableObj when invoked with arguments args and keyword
       arguments kwargs. If a different type of exception is
       thrown, it will not be caught, and the test case will be
       deemed to have suffered an error, exactly as for an
       unexpected exception.
    """
    try:
        callableObj(*args, **kwargs)
    except excClass:
        return
    else:
        if hasattr(excClass,'__name__'): excName = excClass.__name__
        else: excName = str(excClass)
        raise AssertionError, "%s not raised" % excName

def failUnlessEqual(self, first, second, msg=None):
    """Fail if the two objects are unequal as determined by the '=='
       operator.
    """
    if not first == second:
        raise AssertionError, \
              (msg or '%r != %r' % (first, second))

def failIfEqual(self, first, second, msg=None):
    """Fail if the two objects are equal as determined by the '=='
       operator.
    """
    if first == second:
        raise AssertionError, \
              (msg or '%r == %r' % (first, second))

def failUnlessAlmostEqual(self, first, second, places=7, msg=None):
    """Fail if the two objects are unequal as determined by their
       difference rounded to the given number of decimal places
       (default 7) and comparing to zero.

       Note that decimal places (from zero) are usually not the same
       as significant digits (measured from the most signficant digit).
    """
    if round(second-first, places) != 0:
        raise AssertionError, \
              (msg or '%r != %r within %r places' % (first, second, places))

def failIfAlmostEqual(self, first, second, places=7, msg=None):
    """Fail if the two objects are equal as determined by their
       difference rounded to the given number of decimal places
       (default 7) and comparing to zero.

       Note that decimal places (from zero) are usually not the same
       as significant digits (measured from the most signficant digit).
    """
    if round(second-first, places) == 0:
        raise AssertionError, \
              (msg or '%r == %r within %r places' % (first, second, places))

# Synonyms for assertion methods

# stop using these
assertEqual = assertEquals = failUnlessEqual
# stop using these
assertNotEqual = assertNotEquals = failIfEqual

assertAlmostEqual = assertAlmostEquals = failUnlessAlmostEqual

assertNotAlmostEqual = assertNotAlmostEquals = failIfAlmostEqual

assertRaises = failUnlessRaises

assert_ = assertTrue = failUnless

assertFalse = failIf

########NEW FILE########
__FILENAME__ = errors
class TestifyError(Exception): pass

########NEW FILE########
__FILENAME__ = code_coverage
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from testify.utils import code_coverage

def add_command_line_options(parser):
    parser.add_option("-c", "--coverage", action="store_true", dest="coverage")

def run_test_case(options, test_case, runnable):
    if options.coverage:
        code_coverage.start(test_case.__class__.__module__ + "." + test_case.__class__.__name__)
        return runnable()
        code_coverage.stop()
    else:
        return runnable()

########NEW FILE########
__FILENAME__ = http_reporter
import httplib
import logging
import Queue
import threading
import urllib2

from testify import test_reporter

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

class HTTPReporter(test_reporter.TestReporter):
    def report_results(self):
        while True:
            result = self.result_queue.get()
            result['runner_id'] = self.runner_id

            try:
                try:
                    urllib2.urlopen('http://%s/results?runner=%s' % (self.connect_addr, self.runner_id), json.dumps(result))
                except (urllib2.URLError, httplib.BadStatusLine), e:
                    # Retry once.
                    urllib2.urlopen('http://%s/results?runner=%s' % (self.connect_addr, self.runner_id), json.dumps(result))
            except urllib2.HTTPError, e:
                logging.error('Skipping returning results for test %s because of error: %s' % (result['method']['full_name'], e.read()))
            except Exception, e:
                logging.error('Skipping returning results for test %s because of unknown error: %s' % (result['method']['full_name'], e))

            self.result_queue.task_done()


    def __init__(self, options, connect_addr, runner_id, *args, **kwargs):
        self.connect_addr = connect_addr
        self.runner_id = runner_id

        self.result_queue = Queue.Queue()
        self.reporting_thread = threading.Thread(target=self.report_results)
        # A daemon thread should be fine, since the test_runner_client won't quit until the server goes away or says to quit.
        # In either of these cases, any outstanding results won't be processed anyway, so there's no reason for us to wait
        # for the reporting thread to finish before quitting.
        self.reporting_thread.daemon = True
        self.reporting_thread.start()

        super(HTTPReporter, self).__init__(options, *args, **kwargs)

    def test_case_complete(self, result):
        """Add a result to result_queue. The result is specially constructed to
        signal to the test_runner server that a test_runner client has finished
        running an entire TestCase.
        """
        self.result_queue.put(result)

    def class_teardown_complete(self, result):
        """If there was an error during class_teardown, insert the result
        containing the error into the queue that report_results pulls from.
        """
        if not result['success']:
            self.result_queue.put(result)

    def test_complete(self, result):
        self.result_queue.put(result)

    def report(self):
        """Wait until all results have been sent back."""
        self.result_queue.join()
        return True


def build_test_reporters(options):
    if options.connect_addr:
        return [HTTPReporter(options, options.connect_addr, options.runner_id)]
    return []

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = json_log
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

from testify import test_reporter

class ResultLogHandler(logging.Handler):
    """Log Handler to collect log output during a test run"""
    def __init__(self, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)

        self.records = []

    def emit(self, record):
        self.records.append(record)

    def results(self):
        return [self.formatter.format(rec) for rec in self.records]


class JSONReporter(test_reporter.TestReporter):
    def __init__(self, *args, **kwargs):
        super(JSONReporter, self).__init__(*args, **kwargs)

        # Time to open a log file
        self.log_file = open(self.options.json_results, "a")

        # We also want to track log output
        self.log_hndl = None
        self._reset_logging()

    def _reset_logging(self):
        root = logging.getLogger('')
        if self.log_hndl:
            # Remove it if we already have one
            root.removeHandler(self.log_hndl)

        # Create a new one
        if self.options.json_results_logging:
            self.log_hndl = ResultLogHandler()
            self.log_hndl.setLevel(self.options.verbosity)
            self.log_hndl.setFormatter(logging.Formatter('%(asctime)s\t%(name)-12s: %(levelname)-8s %(message)s'))
            root.addHandler(self.log_hndl)

    def test_complete(self, result):
        """Called when a test case is complete"""

        if self.options.label:
            result['label'] = self.options.label
        if self.options.extra_json_info:
            if not hasattr(self.options, 'parsed_extra_json_info'):
                self.options.parsed_extra_json_info = json.loads(self.options.extra_json_info)
            result.update(self.options.parsed_extra_json_info)
        if self.options.bucket is not None:
            result['bucket'] = self.options.bucket
        if self.options.bucket_count is not None:
            result['bucket_count'] = self.options.bucket_count

        if not result['success']:
            if self.log_hndl:
                result['log'] = self.log_hndl.results()

        self.log_file.write(json.dumps(result))
        self.log_file.write("\n")

        self._reset_logging()

    def report(self):
        self.log_file.write("RUN COMPLETE\n")
        self.log_file.close()
        return True


# Hooks for plugin system

def add_command_line_options(parser):
    parser.add_option("--json-results", action="store", dest="json_results", type="string", default=None, help="Store test results in json format")
    parser.add_option("--json-results-logging", action="store_true", dest="json_results_logging", default=False, help="Store log output for failed test results in json")
    parser.add_option("--extra-json-info", action="store", dest="extra_json_info", type="string", help="json containing some extra info to be stored")

def build_test_reporters(options):
    if options.json_results:
        return [JSONReporter(options)]
    else:
        return []

########NEW FILE########
__FILENAME__ = profile
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import cProfile

def add_command_line_options(parser):
    parser.add_option("-p", "--profile", action="store_true", dest="profile")

def run_test_case(options, test_case, runnable):
    if options.profile:
        cprofile_filename = test_case.__class__.__module__ + "." + test_case.__class__.__name__ + '.cprofile'
        return cProfile.runctx('runnable()', globals(), locals(), cprofile_filename)
    else:
        return runnable()
    
########NEW FILE########
__FILENAME__ = seed
# Copyright 2011 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import random

def add_command_line_options(parser):
    parser.add_option("--seed", action="store", dest="seed", type='int', default=None, help="Seed random for each test using this value + hash of the testclass' name. This allows tests to have random yet reproducible numbers.")

def run_test_case(options, test_case, runnable):
    # If random seed is set, seed with seed value plus hash(testclass name). This makes random tests at least be reproducible,
    # and rerunning with another seed (eg. timestamp) will let repeated runs use random values.
    if options.seed:
        random.seed(options.seed + hash(test_case.__class__.__name__))
    return runnable()


########NEW FILE########
__FILENAME__ = sql_reporter
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import logging

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

import yaml
import time
import threading
import Queue

SA = None
try:
    import sqlalchemy as SA
except ImportError:
    pass

from testify import test_reporter

def md5(s):
    return hashlib.md5(s.encode('utf8') if isinstance(s, unicode) else s).hexdigest()


class SQLReporter(test_reporter.TestReporter):

    def __init__(self, options, *args, **kwargs):
        dburl = options.reporting_db_url or SA.engine.url.URL(**yaml.safe_load(open(options.reporting_db_config)))

        create_engine_opts = kwargs.pop('create_engine_opts', {
            'poolclass' : kwargs.pop('poolclass', SA.pool.NullPool),
            'pool_recycle' : 3600,
        })

        self.init_database()
        self.engine = SA.create_engine(dburl, **create_engine_opts)
        self.conn = self.engine.connect()
        self.metadata.create_all(self.engine)

        if not options.build_info:
            raise ValueError("Build info must be specified when reporting to a database.")
        
        build_info_dict = json.loads(options.build_info)
        self.build_id = self.create_build_row(build_info_dict)
        self.start_time = time.time()

        # Cache of (module,class_name,method_name) => test id
        self.test_id_cache = dict(
                ((row[self.Tests.c.module], row[self.Tests.c.class_name], row[self.Tests.c.method_name]), row[self.Tests.c.id])
                for row in self.conn.execute(self.Tests.select())
            )

        self.result_queue = Queue.Queue()
        self.ok = True

        self.reporting_frequency = options.sql_reporting_frequency
        self.batch_size = options.sql_batch_size

        self.reporting_thread = threading.Thread(target=self.report_results)
        self.reporting_thread.daemon = True
        self.reporting_thread.start()

        super(SQLReporter, self).__init__(options, *args, **kwargs)

    def init_database(self):
        self.metadata = SA.MetaData()

        self.Tests = SA.Table('tests', self.metadata,
            SA.Column('id', SA.Integer, primary_key=True, autoincrement=True),
            SA.Column('module', SA.String(255)),
            SA.Column('class_name', SA.String(255)),
            SA.Column('method_name', SA.String(255)),
        )
        SA.Index('ix_individual_test', self.Tests.c.module, self.Tests.c.class_name, self.Tests.c.method_name, unique=True)

        self.Failures = SA.Table('failures', self.metadata,
            SA.Column('id', SA.Integer, primary_key=True, autoincrement=True),
            SA.Column('error', SA.Text, nullable=False),
            SA.Column('traceback', SA.Text, nullable=False),
            SA.Column('hash', SA.String(40), unique=True, nullable=False),
        )

        self.Builds = SA.Table('builds', self.metadata,
            SA.Column('id', SA.Integer, primary_key=True, autoincrement=True),
            SA.Column('buildbot_run_id', SA.String(36), index=True, nullable=True),
            SA.Column('buildbot', SA.Integer, nullable=False),
            SA.Column('buildnumber', SA.Integer, nullable=False),
            SA.Column('buildname', SA.String(40), nullable=False),
            SA.Column('branch', SA.String(255), index=True, nullable=False),
            SA.Column('revision', SA.String(40), index=True, nullable=False),
            SA.Column('end_time', SA.Integer, index=True, nullable=True),
            SA.Column('run_time', SA.Float, nullable=True),
            SA.Column('method_count', SA.Integer, nullable=True),
            SA.Column('submit_time', SA.Integer, index=True, nullable=True),
            SA.Column('discovery_failure', SA.Boolean, default=False, nullable=True),
        )
        SA.Index('ix_individual_run', self.Builds.c.buildbot, self.Builds.c.buildname, self.Builds.c.buildnumber, self.Builds.c.revision, unique=True)

        self.TestResults = SA.Table('test_results', self.metadata,
            SA.Column('id', SA.Integer, primary_key=True, autoincrement=True),
            SA.Column('test', SA.Integer, index=True, nullable=False),
            SA.Column('failure', SA.Integer, index=True),
            SA.Column('build', SA.Integer, index=True, nullable=False),
            SA.Column('end_time', SA.Integer, index=True, nullable=False),
            SA.Column('run_time', SA.Float, index=True, nullable=False),
            SA.Column('runner_id', SA.String(255), index=True, nullable=True),
            SA.Column('previous_run', SA.Integer, index=False, nullable=True),
        )
        SA.Index('ix_build_test_failure', self.TestResults.c.build, self.TestResults.c.test, self.TestResults.c.failure)


    def create_build_row(self, info_dict):
        results = self.conn.execute(self.Builds.insert({
            'buildbot_run_id' : info_dict['buildbot_run_id'],
            'buildbot' : info_dict['buildbot'],
            'buildnumber' : info_dict['buildnumber'],
            'branch' : info_dict['branch'],
            'revision' : info_dict['revision'],
            'submit_time' : info_dict.get('submitstamp'),
            'buildname' : info_dict['buildname'],
        }))
        return results.lastrowid

    def test_counts(self, test_case_count, test_method_count):
        """Store the number of tests so we can determine progress."""
        self.conn.execute(SA.update(self.Builds,
            whereclause=(self.Builds.c.id == self.build_id),
            values={
                'method_count' : test_method_count,
            }
        ))

    def class_teardown_complete(self, result):
        """If there was an error during class_teardown, insert the result
        containing the error into the queue that report_results pulls from.
        """
        if not result['success']:
            self.result_queue.put(result)

    def test_complete(self, result):
        """Insert a result into the queue that report_results pulls from."""
        # Test methods named 'run' are special. See TestCase.run().
        if not result['method']['name'] == 'run':
            self.result_queue.put(result)

    def test_discovery_failure(self, exc):
        """Set the discovery_failure flag to True and method_count to 0."""
        self.conn.execute(SA.update(self.Builds,
            whereclause=(self.Builds.c.id == self.build_id),
            values={
                'discovery_failure' : True,
                'method_count' : 0,
            }
        ))

    def _canonicalize_exception(self, traceback, error):
        error = error.strip()
        if self.options.sql_traceback_size is not None:
            truncation_message = " (Exception truncated.)"
            size_limit = self.options.sql_traceback_size - len(truncation_message)
            if len(traceback) > self.options.sql_traceback_size:
                traceback = traceback[:size_limit] + truncation_message
            if len(error) > self.options.sql_traceback_size:
                error = error[:size_limit] + truncation_message

        return (traceback, error)

    def _create_row_to_insert(self, conn, result, previous_run_id=None):
        return {
            'test' : self._get_test_id(conn, result['method']['module'], result['method']['class'], result['method']['name']),
            'failure' : self._get_failure_id(conn, result['exception_info'], result['exception_only']),
            'build' : self.build_id,
            'end_time' : result['end_time'],
            'run_time' : result['run_time'],
            'runner_id' : result['runner_id'],
            'previous_run' : previous_run_id,
        }

    def _get_test_id(self, conn, module, class_name, method_name):
        """Get the ID of the self.Tests row that corresponds to this test. If the row doesn't exist, insert one"""

        cached_result = self.test_id_cache.get((module, class_name, method_name), None)
        if cached_result is not None:
            return cached_result

        query = SA.select(
            [self.Tests.c.id],
            SA.and_(
                self.Tests.c.module == module,
                self.Tests.c.class_name == class_name,
                self.Tests.c.method_name == method_name,
            )
        )

        # Most of the time, the self.Tests row will already exist for this test (it's been run before.)
        row = conn.execute(query).fetchone()
        if row:
            return row[self.Tests.c.id]
        else:
            # Not there (this test hasn't been run before); create it
            results = conn.execute(self.Tests.insert({
                'module' : module,
                'class_name' : class_name,
                'method_name' : method_name,
            }))
            # and then return it.
            return results.lastrowid

    def _get_failure_id(self, conn, exception_info, error):
        """Get the ID of the failure row for the specified exception."""
        if not exception_info:
            return None

        # Canonicalize the traceback and error for storage.
        traceback, error = self._canonicalize_exception(exception_info, error)

        exc_hash = md5(traceback)

        query = SA.select(
            [self.Failures.c.id],
            self.Failures.c.hash == exc_hash,
        )
        row = conn.execute(query).fetchone()
        if row:
            return row[self.Failures.c.id]
        else:
            # We haven't inserted this row yet; insert it and re-query.
            results = conn.execute(self.Failures.insert({
                'hash' : exc_hash,
                'error' : error,
                'traceback': traceback,
            }))
            return results.lastrowid

    def _insert_single_run(self, conn, result):
        """Recursively insert a run and its previous runs."""
        previous_run_id = self._insert_single_run(conn, result['previous_run']) if result['previous_run'] else None
        results = conn.execute(self.TestResults.insert(self._create_row_to_insert(conn, result, previous_run_id=previous_run_id)))
        return results.lastrowid

    def _report_results_by_chunk(self, conn, chunk):
        try:
            conn.execute(self.TestResults.insert(),
                [self._create_row_to_insert(conn, result, result.get('previous_run_id', None)) for result in chunk]
            )
        except Exception, e:
            logging.exception("Exception while reporting results: " + repr(e))
            self.ok = False
        finally:
            # Do this in finally so we don't hang at report() time if we get errors.
            for _ in xrange(len(chunk)):
                self.result_queue.task_done()

    def report_results(self):
        """A worker func that runs in another thread and reports results to the database.
        Create a self.TestResults row from a test result dict. Also inserts the previous_run row."""
        conn = self.engine.connect()

        while True:
            results = []
            # Block until there's a result available.
            results.append(self.result_queue.get())
            # Grab any more tests that come in during the next self.reporting_frequency seconds.
            time.sleep(self.reporting_frequency)
            try:
                while True:
                    results.append(self.result_queue.get_nowait())
            except Queue.Empty:
                pass

            # Insert any previous runs, if necessary.
            for result in filter(lambda x: x['previous_run'], results):
                try:
                    result['previous_run_id'] = self._insert_single_run(conn, result['previous_run'])
                except Exception, e:
                    logging.exception("Exception while reporting results: " + repr(e))
                    self.ok = False

            chunks = (results[i:i+self.batch_size] for i in xrange(0, len(results), self.batch_size))

            for chunk in chunks:
                self._report_results_by_chunk(conn, chunk)

    def report(self):
        self.end_time = time.time()
        self.result_queue.join()
        query = SA.update(self.Builds,
            whereclause=(self.Builds.c.id == self.build_id),
            values={
                'end_time' : self.end_time,
                'run_time' : self.end_time - self.start_time,
            }
        )
        self.conn.execute(query)
        return self.ok


# Hooks for plugin system
def add_command_line_options(parser):
    parser.add_option("--reporting-db-config", action="store", dest="reporting_db_config", type="string", default=None, help="Path to a yaml file describing the SQL database to report into.")
    parser.add_option('--reporting-db-url', action="store", dest="reporting_db_url", type="string", default=None, help="The URL of a SQL database to report into.")
    parser.add_option("--build-info", action="store", dest="build_info", type="string", default=None, help="A JSON dictionary of information about this build, to store in the reporting database.")
    parser.add_option("--sql-reporting-frequency", action="store", dest="sql_reporting_frequency", type="float", default=1.0, help="How long to wait between SQL inserts, at a minimum")
    parser.add_option("--sql-batch-size", action="store", dest="sql_batch_size", type="int", default="500", help="Maximum number of rows to insert at any one time")
    parser.add_option("--sql-traceback-size", action="store", dest="sql_traceback_size", type="int", default="65536", help="Maximum length of traceback to store. Tracebacks longer than this will be truncated.")

def build_test_reporters(options):
    if options.reporting_db_config or options.reporting_db_url:
        if not SA:
            msg = 'SQL Reporter plugin requires sqlalchemy and you do not have it installed in your PYTHONPATH.\n'
            raise ImportError, msg
        return [SQLReporter(options)]
    return []

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = violation_collector
import fcntl
import itertools
import json
import logging
import operator
import os
import select
import sys
import time

catbox = None
try:
    import catbox
except ImportError:
    pass

SA = None
try:
    import sqlalchemy as SA
except ImportError:
    pass
import yaml

from testify import test_reporter
from testify import test_logger


method_types = ('undefined', 'test', 'setup', 'teardown', 'class_setup', 'class_teardown')

(
    UNDEFINED_METHOD_TYPE,
    TEST_METHOD_TYPE,
    SETUP_METHOD_TYPE,
    TEARDOWN_METHOD_TYPE,
    CLASS_SETUP_METHOD_TYPE,
    CLASS_TEARDOWN_METHOD_TYPE
) = method_types


class _Context(object):
    store = None
    output_stream = None
    output_verbosity = test_logger.VERBOSITY_NORMAL

'''Catbox will fork this process and run TestProgram in the child. The
child process runs the tests while the parent process traces the
tests' execution.

The instances created by this module in this global context will have
two copies: one in parent (collecting syscall violations) and one in
the traced child process (running tests).'''
ctx = _Context()

def get_db_url(options):
    '''If a configuration file is given, returns the database URL from
    the configuration file. Otherwise returns violation-db-url option.
    '''
    if options.violation_dbconfig:
        with open(options.violation_dbconfig) as db_config_file:
            return SA.engine.url.URL(**yaml.safe_load(db_config_file))
    else:
        return options.violation_dburl

def is_sqlite_filepath(dburl):
    '''Check if dburl is an sqlite file path.'''
    return type(dburl) in (str, unicode) and dburl.startswith('sqlite:///')


def sqlite_dbpath(dburl):
    '''Return the file path of the sqlite url'''
    if is_sqlite_filepath(dburl):
        return os.path.abspath(dburl[len('sqlite:///'):])
    return None


def cleandict(dictionary, allowed_keys):
    '''Cleanup the dictionary removing all keys but the allowed ones.'''
    return dict((k, v) for k, v in dictionary.iteritems() if k in allowed_keys)


def writable_paths(options):
    '''Generate a list of writable paths'''
    paths = ['~.*pyc$', '/dev/null']
    if is_sqlite_filepath(options.violation_dburl):
        paths.append('~%s.*$' % sqlite_dbpath(options.violation_dburl))
    return paths


def run_in_catbox(method, logger, paths):
    '''Run the given method in catbox. method is going to be run in
    catbox to be traced and logger will be notified of any violations
    in the method.

    paths is a list of writable strings (regexp). Catbox will ignore
    violations by syscalls if the syscall is call writing to a path in
    the writable paths list.
    '''
    return catbox.run(
        method,
        collect_only=True,
        network=False,
        logger=logger,
        writable_paths=paths,
    ).code


def writeln(msg, verbosity=None):
    '''Write msg to the output stream appending a new line'''
    global ctx
    verbosity =  verbosity or ctx.output_verbosity
    if ctx.output_stream and (verbosity <= ctx.output_verbosity):
        msg = msg.encode('utf8') if isinstance(msg, unicode) else msg
        ctx.output_stream.write(msg + '\n')
        ctx.output_stream.flush()


def collect(syscall, path, resolved_path):
    '''This is the 'logger' method passed to catbox. This method
    will be triggered at each catbox violation.
    '''
    global ctx
    try:
        writeln(
            'CATBOX_VIOLATION: %s, %s' % (syscall, resolved_path),
            test_logger.VERBOSITY_VERBOSE
        )

        ctx.store.add_violation({
            'syscall': syscall,
            'syscall_args': resolved_path,
            'start_time': time.time()
        })
    except Exception, e:
        # No way to recover in here, just report error and violation
        sys.stderr.write('Error collecting violation data. Error %r. Violation: %r\n' % (e, (syscall, resolved_path)))


class ViolationStore(object):
    TEST_ID_DESC_END = ','
    MAX_TEST_ID_LINE = 1024 * 10

    def __init__(self, options):
        self.options = options

        self.dburl = get_db_url(self.options)
        if options.build_info:
            info = json.loads(options.build_info)
            self.info = cleandict(info, ['branch', 'revision', 'buildbot_run_id'])
        else:
            self.info = {'branch': '', 'revision': '', 'buildbot_run_id': None}

        self.init_database()

        if is_sqlite_filepath(self.dburl):
            if self.dburl.find(':memory:') > -1:
                raise ValueError('Can not use sqlite memory database for ViolationStore')
            dbpath = sqlite_dbpath(self.dburl)
            if os.path.exists(dbpath):
                os.unlink(dbpath)

        self.last_test_id = 0
        self._setup_pipe()

        self.engine = self.conn = None

    def init_database(self):
        self.metadata = SA.MetaData()

        self.Violations = SA.Table(
            'catbox_violations', self.metadata,
            SA.Column('id', SA.Integer, primary_key=True, autoincrement=True),
            SA.Column('test_id', SA.Integer, index=True, nullable=False),
            SA.Column('syscall', SA.String(20), nullable=False),
            SA.Column('syscall_args', SA.Text, nullable=True),
            SA.Column('start_time', SA.Integer),
        )

        self.Methods = SA.Table(
            'catbox_methods', self.metadata,
            SA.Column('id', SA.Integer, primary_key=True, autoincrement=True),
            SA.Column('buildbot_run_id', SA.String(36), index=True, nullable=True),
            SA.Column('branch', SA.Text),
            SA.Column('revision', SA.Text),
            SA.Column('start_time', SA.Integer),
            SA.Column('module', SA.Text, nullable=False),
            SA.Column('class_name', SA.Text, nullable=False),
            SA.Column('method_name', SA.Text, nullable=False),
            SA.Column('method_type', SA.Enum(*method_types), nullable=False),
        )

    def _setup_pipe(self):
        """Setup a pipe to enable communication between parent and
        traced child processes.

        Adding tests and adding violations to the database is done
        through different processes. We use this pipe to update the
        last test id to be used while inserting Violations. Although
        it is possible to get it from the database we'll use the pipe
        not to make a db query each time we add a violation (and would
        really work when there is multiple builders writing to the
        database).
        """
        self.test_id_read_fd, self.test_id_write_fd = os.pipe()

        fcntl.fcntl(self.test_id_read_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        self.epoll = select.epoll()
        self.epoll.register(self.test_id_read_fd, select.EPOLLIN | select.EPOLLET)

    def _connect_db(self):
        engine = SA.create_engine(self.dburl)
        conn = engine.connect()
        if is_sqlite_filepath(self.dburl):
            conn.execute('PRAGMA journal_mode = MEMORY;')
        self.metadata.create_all(engine)
        return engine, conn

    def _set_last_test_id(self, test_id):
        """Set the latest test id inserted to the database. See the
        _setup_pipe's docstring for details.
        """
        if self.test_id_read_fd:
            # If this method is called it means that we're in the
            # traced child process. Reporter (running in the traced
            # child process) will ultimately call this method to write
            # the test id to the pipe when we start running a test
            # method. Closing the read end of the pipe as we don't
            # need to read/write from there.
            os.close(self.test_id_read_fd)
            self.test_id_read_fd = None

        os.write(self.test_id_write_fd, '%d%s' % (test_id, self.TEST_ID_DESC_END))

    def _parse_last_test_id(self, data):
        """Get last non empty string as violator line."""
        test_id_str = data.split(self.TEST_ID_DESC_END)[-2]
        return int(test_id_str)

    def get_last_test_id(self):
        """Get the latest test id inserted to the database. See the
        setup_pipe's docstring for details.
        """
        if self.test_id_write_fd:
            # If this method is called it means that we're in the
            # parent process. Parent process will use this method to
            # read from pipe and learn about the running test method
            # to report violations. Closing the write end of the pipe
            # as we don't need to read/write from there.
            os.close(self.test_id_write_fd)
            self.test_id_write_fd = None

        events = self.epoll.poll(.01)
        for fileno, event in events:
            if event == select.EPOLLIN:
                read = os.read(fileno, self.MAX_TEST_ID_LINE)
                if read:
                    self.last_test_id = self._parse_last_test_id(read)
        return self.last_test_id

    def add_method(self, module, class_name, method_name, method_type):
        if self.engine is None and self.conn is None:
            # We are in the traced child process and this is the first
            # request to add a test to the database. We should create
            # a connection for this process. Note that making the
            # connection earlier would not work as the connection
            # object would be shared by two processes and cause
            # deadlock in mysql client library.
            self.engine, self.conn = self._connect_db()
        try:
            testinfo = {
                'module': module,
                'class_name': class_name,
                'method_name': method_name,
                'start_time': time.time(),
                'method_type': method_type,
            }
            testinfo.update(self.info)
            result = self.conn.execute(self.Methods.insert(), testinfo)
            self._set_last_test_id(result.lastrowid)
        except Exception, e:
            logging.error('Exception inserting testinfo: %r' % e)

    def add_violation(self, violation):
        if self.engine is None and self.conn is None:
            # We are in the parent process and this is the first
            # request to add a violation to the database. We should
            # create a connection for this process.
            #
            # As in add_method (see above), making the connection
            # earlier would not work due due to deadlock issues.
            self.engine, self.conn = self._connect_db()
        try:
            test_id = self.get_last_test_id()
            violation.update({'test_id': test_id})
            self.conn.execute(self.Violations.insert(), violation)
        except Exception, e:
            logging.error('Exception inserting violations: %r' % e)

    def violation_counts(self):
        query = SA.sql.select([
            self.Methods.c.class_name,
            self.Methods.c.method_name,
            self.Violations.c.syscall,
            SA.sql.func.count(self.Violations.c.syscall).label('count')

        ]).where(
            self.Violations.c.test_id == self.Methods.c.id
        ).group_by(
            self.Methods.c.class_name, self.Methods.c.method_name, self.Violations.c.syscall
        ).order_by(
            'count DESC'
        )
        result = self.conn.execute(query)
        violations = []
        for row in result:
            violations.append((row['class_name'], row['method_name'], row['syscall'], row['count']))
        return violations


class ViolationReporter(test_reporter.TestReporter):
    def __init__(self, options, store):
        self.options = options
        self.store = store
        super(ViolationReporter, self).__init__(options)

    def __update_violator(self, result, method_type):
        method = result['method']
        test_case_name = method['class']
        test_method_name = method['name']
        module_path = method['module']
        self.store.add_method(module_path, test_case_name, test_method_name, method_type)

    def test_case_start(self, result):
        self.__update_violator(result, UNDEFINED_METHOD_TYPE)

    def test_start(self, result):
        self.__update_violator(result, TEST_METHOD_TYPE)

    def class_setup_start(self, result):
        self.__update_violator(result, CLASS_SETUP_METHOD_TYPE)

    def class_teardown_start(self, result):
        self.__update_violator(result, CLASS_TEARDOWN_METHOD_TYPE)

    def get_syscall_count(self, violations):
        syscall_violations = []
        for syscall, violators in itertools.groupby(sorted(violations, key=operator.itemgetter(2)), operator.itemgetter(2)):
            count = sum(violator[3] for violator in violators)
            syscall_violations.append((syscall, count))
        return sorted(syscall_violations, key=operator.itemgetter(1))

    def get_violations_count(self, syscall_violation_counts):
        return sum(count for (syscall, count) in syscall_violation_counts)

    def report(self):
        if self.options.disable_violations_summary is not True:
            violations = self.store.violation_counts()
            if ctx.output_verbosity == test_logger.VERBOSITY_VERBOSE:
                self._report_verbose(violations)
            elif ctx.output_verbosity >= test_logger.VERBOSITY_NORMAL:
                self._report_normal(violations)
            else:
                self._report_silent(violations)

    def _report_verbose(self, violations):
        verbosity = test_logger.VERBOSITY_VERBOSE
        self._report_normal(violations)
        writeln('')
        for class_name, test_method, syscall, count in violations:
            writeln('%s.%s\t%s\t%s' % (class_name, test_method, syscall, count), verbosity)

    def _report_normal(self, violations):
        if not len(violations):
            writeln('No syscall violations! \o/\n', test_logger.VERBOSITY_NORMAL)
            return
        self._report_silent(violations)

    def _report_silent(self, violations):
        syscall_violation_counts = self.get_syscall_count(violations)
        violations_count = self.get_violations_count(syscall_violation_counts)
        violations_line = '%s %s' % (
            '%s syscall violations:' % violations_count,
            ','.join(['%s (%s)' % (syscall, count) for syscall, count in syscall_violation_counts])
        )
        writeln(violations_line, test_logger.VERBOSITY_SILENT)



def add_command_line_options(parser):
    parser.add_option(
        '-V',
        '--collect-violations',
        action='store_true',
        dest='catbox_violations',
        help='Network or filesystem access from tests will be reported as violations.'
    )
    parser.add_option(
        '--violation-db-url',
        dest='violation_dburl',
        default='sqlite:///violations.sqlite',
        help='URL of the SQL database to store violations.'
    )
    parser.add_option(
        '--violation-db-config',
        dest='violation_dbconfig',
        help='Yaml configuration file describing SQL database to store violations.'
    )
    parser.add_option(
        '--disable-violations-summary',
        action='store_true',
        dest='disable_violations_summary',
        help='Disable preparing a summary .'
    )


def prepare_test_program(options, program):
    global ctx
    if options.catbox_violations:
        if not sys.platform.startswith('linux'):
            msg = 'Violation collection plugin is Linux-specific. Please either run your tests on Linux or disable the plugin.'
            raise Exception, msg
        msg_pcre = '\nhttps://github.com/Yelp/catbox/wiki/Install-Catbox-with-PCRE-enabled\n'
        if not catbox:
            msg = 'Violation collection requires catbox and you do not have it installed in your PYTHONPATH.\n'
            msg += msg_pcre
            raise ImportError, msg
        if catbox and not catbox.has_pcre():
            msg = 'Violation collection requires catbox compiled with PCRE. Your catbox installation does not have PCRE support.'
            msg += msg_pcre
            raise ImportError, msg
        if not SA:
            msg = 'Violation collection requires sqlalchemy and you do not have it installed in your PYTHONPATH.\n'
            raise ImportError, msg

        ctx.output_stream = sys.stderr # TODO: Use logger?
        ctx.output_verbosity = options.verbosity
        ctx.store = ViolationStore(options)
        def _run():
            return run_in_catbox(
                program.__original_run__,
                collect,
                writable_paths(options)
            )
        program.__original_run__ = program.run
        program.run = _run


def build_test_reporters(options):
    global ctx
    if options.catbox_violations:
        return [ViolationReporter(options, ctx.store)]
    return []

########NEW FILE########
__FILENAME__ = test_case
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This module contains the TestCase class and other helper code, like decorators for test methods."""

# TODO: finish doing the retry stuff for the inner clauses

from __future__ import with_statement

__author__ = "Oliver Nicholas <bigo@yelp.com>"
__testify = 1

from collections import defaultdict
from new import instancemethod
import functools
import inspect
import sys
import types
import unittest

from testify.utils import class_logger
from testify.test_fixtures import DEPRECATED_FIXTURE_TYPE_MAP
from testify.test_fixtures import TestFixtures
from testify.test_fixtures import suite
from test_result import TestResult
import deprecated_assertions


class MetaTestCase(type):
    """This base metaclass is used to collect each TestCase's decorated fixture methods at
    runtime. It is implemented as a metaclass so we can determine the order in which
    fixture methods are defined.
    """
    __test__ = False

    def __new__(mcls, name, bases, dct):
        # This is the constructor for all TestCase *classes*.
        for member_name, member in dct.iteritems():
            if member_name.startswith('test') and isinstance(member, types.FunctionType):
                if not hasattr(member, '_suites'):
                    member._suites = set()

        # Unfortunately, this implementation detail has become a public interface.
        # The set of suites must include the suites from all bases classes.
        cls_suites = dct.pop('_suites', ())
        bases_suites = [
            getattr(base, '_suites', ())
            for base in bases
        ]
        dct['_suites'] = set().union(cls_suites, *bases_suites)

        return super(MetaTestCase, mcls).__new__(mcls, name, bases, dct)

    @staticmethod
    def _cmp_str(instance):
        """Return a canonical representation of a TestCase for sorting and hashing."""
        return "%s.%s" % (instance.__module__, instance.__name__)

    def __cmp__(cls, other):
        """Sort TestCases by a particular string representation."""
        return cmp(MetaTestCase._cmp_str(cls), MetaTestCase._cmp_str(other))


class TestCase(object):
    """The TestCase class defines test methods and fixture methods; it is the meat and potatoes of testing.

    QuickStart:
        define a test method, instantiate an instance and call test_case.run()

    Extended information:
        TestCases can contain any number of test methods, as well as class-level
        setup/teardown methods and setup/teardowns to be wrapped around each test
        method. These are defined by decorators.

        The phases of execution are thus:
        class_setup
            setup
                test_method_1
            teardown
            setup
                test_method_2
            teardown
        class_teardown

        The results of test methods are stored in TestResult objects.

        Additional behavior beyond running tests, such as logging results, is achieved
        by registered callbacks.  For more information see the docstrings for:
            register_on_complete_test_method_callback
            register_on_run_test_method_callback
    """
    __metaclass__ = MetaTestCase
    __test__ = False

    STAGE_UNSTARTED = 0
    STAGE_CLASS_SETUP = 1
    STAGE_SETUP = 2
    STAGE_TEST_METHOD = 3
    STAGE_TEARDOWN = 4
    STAGE_CLASS_TEARDOWN = 5

    EVENT_ON_RUN_TEST_METHOD = 1
    EVENT_ON_COMPLETE_TEST_METHOD = 2
    EVENT_ON_RUN_CLASS_SETUP_METHOD = 3
    EVENT_ON_COMPLETE_CLASS_SETUP_METHOD = 4
    EVENT_ON_RUN_CLASS_TEARDOWN_METHOD = 5
    EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD = 6
    EVENT_ON_RUN_TEST_CASE = 7
    EVENT_ON_COMPLETE_TEST_CASE = 8

    log = class_logger.ClassLogger()

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__()

        self.__test_fixtures = TestFixtures.discover_from(self)

        self.__suites_include = kwargs.get('suites_include', set())
        self.__suites_exclude = kwargs.get('suites_exclude', set())
        self.__suites_require = kwargs.get('suites_require', set())
        self.__name_overrides = kwargs.get('name_overrides', None)

        TestResult.debug = kwargs.get('debugger') # sorry :(

        # callbacks for various stages of execution, used for stuff like logging
        self.__callbacks = defaultdict(list)

        self.__all_test_results = []

        self._stage = self.STAGE_UNSTARTED

        # for now, we still support the use of unittest-style assertions defined on the TestCase instance
        for name in dir(deprecated_assertions):
            if name.startswith(('assert', 'fail')):
                setattr(self, name, instancemethod(getattr(deprecated_assertions, name), self, self.__class__))

        self.failure_limit = kwargs.pop('failure_limit', None)
        self.failure_count = 0

    @property
    def test_result(self):
        return self.__all_test_results[-1] if self.__all_test_results else None

    def _generate_test_method(self, method_name, function):
        """Allow tests to define new test methods in their __init__'s and have appropriate suites applied."""
        suite(*getattr(self, '_suites', set()))(function)
        setattr(self, method_name, instancemethod(function, self, self.__class__))

    def runnable_test_methods(self):
        """Generator method to yield runnable test methods.

        This will pick out the test methods from this TestCase, and then exclude any in
        any of our exclude_suites.  If there are any include_suites, it will then further
        limit itself to test methods in those suites.
        """
        for member_name in dir(self):
            if not member_name.startswith("test"):
                continue
            member = getattr(self, member_name)
            if not inspect.ismethod(member):
                continue

            member_suites = self.suites(member)

            # if there are any exclude suites, exclude methods under them
            if self.__suites_exclude and self.__suites_exclude & member_suites:
                continue
            # if there are any include suites, only run methods in them
            if self.__suites_include and not (self.__suites_include & member_suites):
                continue
            # if there are any require suites, only run methods in *all* of those suites
            if self.__suites_require and not ((self.__suites_require & member_suites) == self.__suites_require):
                continue

            # if there are any name overrides, only run the named methods
            if self.__name_overrides is None or member.__name__ in self.__name_overrides:
                yield member

    def run(self):
        """Delegator method encapsulating the flow for executing a TestCase instance.

        This method tracks its progress in a TestResult with test_method 'run'.
        This TestResult is used as a signal when running in client/server mode:
        when the client is done running a TestCase and its fixtures, it sends
        this TestResult to the server during the EVENT_ON_COMPLETE_TEST_CASE
        phase.

        This could be handled better. See
        https://github.com/Yelp/Testify/issues/121.
        """

        # The TestResult constructor wants an actual method, which it inspects
        # to determine the method name (and class name, so it must be a method
        # and not a function!). self.run is as good a method as any.
        test_case_result = TestResult(self.run)
        test_case_result.start()
        self.fire_event(self.EVENT_ON_RUN_TEST_CASE, test_case_result)

        self._stage = self.STAGE_CLASS_SETUP
        with self.__test_fixtures.class_context(
                setup_callbacks=[
                    functools.partial(self.fire_event, self.EVENT_ON_RUN_CLASS_SETUP_METHOD),
                    functools.partial(self.fire_event, self.EVENT_ON_COMPLETE_CLASS_SETUP_METHOD),
                ],
                teardown_callbacks=[
                    functools.partial(self.fire_event, self.EVENT_ON_RUN_CLASS_TEARDOWN_METHOD),
                    functools.partial(self.fire_event, self.EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD),
                ],
        ) as class_fixture_failures:
            # if we have class fixture failures, we're not going to bother
            # running tests, but we need to generate bogus results for them all
            # and mark them as failed.
            self.__run_test_methods(class_fixture_failures)
            self._stage = self.STAGE_CLASS_TEARDOWN

        # class fixture failures count towards our total
        self.failure_count += len(class_fixture_failures)

        # you might think that we would want to do this... but this is a
        # bogus test result used for reporting to the server. we always
        # have it report success, i guess.
        # for exc_info in fixture_failures:
        #     test_case_result.end_in_failure(exc_info)

        if not test_case_result.complete:
            test_case_result.end_in_success()

        self.fire_event(self.EVENT_ON_COMPLETE_TEST_CASE, test_case_result)

    @classmethod
    def in_suite(cls, method, suite_name):
        """Return a bool denoting whether the given method is in the given suite."""
        return suite_name in getattr(method, '_suites', set())

    def suites(self, method=None):
        """Returns the suites associated with this test case and, optionally, the given method."""
        suites = set(getattr(self, '_suites', []))
        if method is not None:
            suites |= getattr(method, '_suites', set())
        return suites

    def results(self):
        """Available after calling `self.run()`."""
        if self._stage != self.STAGE_CLASS_TEARDOWN:
            raise RuntimeError('results() called before tests have executed')
        return list(self.__all_test_results)

    def method_excluded(self, method):
        """Given this TestCase's included/excluded suites, is this test method excluded?

        Returns a set of the excluded suites that the argument method is in, or an empty
        suite if none.
        """
        method_suites = set(getattr(method, '_suites', set()))
        return (self.__suites_exclude & method_suites)

    def __run_test_methods(self, class_fixture_failures):
        """Run this class's setup fixtures / test methods / teardown fixtures.

        These are run in the obvious order - setup and teardown go before and after,
        respectively, every test method.  If there was a failure in the class_setup
        phase, no method-level fixtures or test methods will be run, and we'll eventually
        skip all the way to the class_teardown phase.   If a given test method is marked
        as disabled, neither it nor its fixtures will be run.  If there is an exception
        during the setup phase, the test method will not be run and execution
        will continue with the teardown phase.
        """
        for test_method in self.runnable_test_methods():
            result = TestResult(test_method)

            # Sometimes, test cases want to take further action based on
            # results, e.g. further clean-up or reporting if a test method
            # fails. (Yelp's Selenium test cases do this.) If you need to
            # programatically inspect test results, you should use
            # self.results().

            # NOTE: THIS IS INCORRECT -- im_self is shared among all test
            # methods on the TestCase instance. This is preserved for backwards
            # compatibility and should be removed eventually.

            try:
                # run "on-run" callbacks. e.g. print out the test method name
                self.fire_event(self.EVENT_ON_RUN_TEST_METHOD, result)

                result.start()
                self.__all_test_results.append(result)

                # if class setup failed, this test has already failed.
                self._stage = self.STAGE_CLASS_SETUP
                for exc_info in class_fixture_failures:
                    result.end_in_failure(exc_info)

                if result.complete:
                    continue

                # first, run setup fixtures
                self._stage = self.STAGE_SETUP
                with self.__test_fixtures.instance_context() as fixture_failures:
                    # we haven't had any problems in class/instance setup, onward!
                    if not fixture_failures:
                        self._stage = self.STAGE_TEST_METHOD
                        result.record(test_method)
                    self._stage = self.STAGE_TEARDOWN

                # maybe something broke during teardown -- record it
                for exc_info in fixture_failures:
                    result.end_in_failure(exc_info)

                # if nothing's gone wrong, it's not about to start
                if not result.complete:
                    result.end_in_success()

            except (KeyboardInterrupt, SystemExit):
                result.end_in_interruption(sys.exc_info())
                raise

            finally:
                self.fire_event(self.EVENT_ON_COMPLETE_TEST_METHOD, result)

                if not result.success:
                    self.failure_count += 1
                    if self.failure_limit and self.failure_count >= self.failure_limit:
                        break

    def register_callback(self, event, callback):
        """Register a callback for an internal event, usually used for logging.

        The argument to the callback will be the test method object itself.

        Fixture objects can be distinguished by the running them through
        inspection.is_fixture_method().
        """
        self.__callbacks[event].append(callback)

    def fire_event(self, event, result):
        for callback in self.__callbacks[event]:
            callback(result.to_dict())

    def classSetUp(self): pass
    def setUp(self): pass
    def tearDown(self): pass
    def classTearDown(self): pass
    def runTest(self): pass


class TestifiedUnitTest(TestCase, unittest.TestCase):

    @classmethod
    def from_unittest_case(cls, unittest_class, module_suites=None):
        """"Constructs a new testify.TestCase from a unittest.TestCase class.

        This operates recursively on the TestCase's class hierarchy by
        converting each parent unittest.TestCase into a TestifiedTestCase.

        If 'suites' are provided, they are treated as module-level suites to be
        applied in addition to class- and test-level suites.
        """

        # our base case: once we get to the parent TestCase, replace it with our
        # own parent class that will just handle inheritance for super()
        if unittest_class == unittest.TestCase:
            return TestifiedUnitTest

        # we're going to update our class dict with some testify defaults to
        # make things Just Work
        unittest_dict = dict(unittest_class.__dict__)
        default_test_case_dict = dict(TestCase.__dict__)

        # testify.TestCase defines its own deprecated fixtures; don't let them
        # overwrite unittest's fixtures
        for deprecated_fixture_name in DEPRECATED_FIXTURE_TYPE_MAP:
            del default_test_case_dict[deprecated_fixture_name]

        # set testify defaults on the unittest class
        for member_name, member in default_test_case_dict.iteritems():
            unittest_dict.setdefault(member_name, member)

        # use an __init__ smart enough to figure out our inheritance
        unittest_dict['__init__'] = cls.__init__

        # add module-level suites in addition to any suites already on the class
        class_suites = set(getattr(unittest_class, '_suites', []))
        unittest_dict['_suites'] = class_suites | set(module_suites or [])

        # traverse our class hierarchy and 'testify' parent unittest.TestCases
        bases = []

        for base_class in unittest_class.__bases__:
            if issubclass(base_class, unittest.TestCase):
                base_class = cls.from_unittest_case(base_class, module_suites=module_suites)
            bases.append(base_class)

        # include our original unittest class so existing super() calls still
        # work; this is our last base class to prevent infinite recursion in
        # those super calls
        bases.insert(1, unittest_class)

        new_name = 'Testified' + unittest_class.__name__

        return MetaTestCase(new_name, tuple(bases), unittest_dict)


# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_discovery
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import inspect
import logging
import os
import sys
import time
import traceback
import types
import unittest
from test_case import MetaTestCase, TestifiedUnitTest
from errors import TestifyError

_log = logging.getLogger('testify')

class DiscoveryError(TestifyError): pass

def gather_test_paths(testing_dir):
    """Given a directory path, yield up paths for all py files inside of it"""
    for adir, subdirs, subfiles in os.walk(testing_dir):
        # ignore .svn directories and other such hiddens
        if adir.startswith('.'):
            continue
        for subfile in subfiles:
            # ignore __init__ files, dotfiles, etc
            if subfile.endswith('.py') and not (subfile.startswith('__init__.') or subfile.startswith('.')):
                relative_path = os.path.realpath(adir)[len(os.getcwd()) + 1:]
                fs_path = os.path.join(relative_path, subfile)
                yield fs_path[:-3].replace('/','.')

def discover(what):
    """Given a string module path, drill into it for its TestCases.

    This will descend recursively into packages and lists, so the following are valid:
        - add_test_module('tests.biz_cmds.biz_ad_test')
        - add_test_module('tests.biz_cmds.biz_ad_test.tests')
        - add_test_module('tests.biz_cmds')
        - add_test_module('tests')
    """

    def discover_inner(locator, suites=None):
        suites = suites or []
        if isinstance(locator, basestring):
            import_error = None
            try:
                test_module = __import__(locator)
            except (ValueError, ImportError), e:
                import_error = e
                _log.info('discover_inner: Failed to import %s: %s' % (locator, e))
                if os.path.isfile(locator) or os.path.isfile(locator+'.py'):
                    here = os.path.abspath(os.path.curdir) + os.path.sep
                    new_loc = os.path.abspath(locator)
                    if not new_loc.startswith(here):
                        raise DiscoveryError('Can only load modules by path within the current directory')

                    new_loc = new_loc[len(here):]
                    new_loc = new_loc.rsplit('.py',1)[0] #allows for .pyc and .pyo as well
                    new_loc = new_loc.replace(os.sep,'.')
                    try:
                        test_module = __import__(new_loc)
                        locator = new_loc
                        del new_loc
                    except (ValueError, ImportError):
                        raise DiscoveryError("Failed to find module %s" % locator)
                else:
                    try:
                        test_module = __import__('.'.join(locator.split('.')[:-1]))
                    except (ValueError, ImportError):
                        raise DiscoveryError("Failed to find module %s" % locator)
            except Exception:
                raise DiscoveryError("Got unknown error when trying to import %s:\n\n%s" % (
                    locator,
                    ''.join(traceback.format_exception(*sys.exc_info()))
                ))

            for part in locator.split('.')[1:]:
                try:
                    test_module = getattr(test_module, part)
                except AttributeError:
                    message = "discovery(%s) failed: module %s has no attribute %r" % (locator, test_module, part)
                    if import_error is not None:
                        message += "; this is most likely due to earlier error %r" % (import_error,)
                    raise DiscoveryError(message)
        else:
            test_module = locator

        # if it's a list, iterate it and add its members
        if isinstance(test_module, (list, tuple)):
            for item in test_module:
                for test_case_class in discover_inner(item):
                    yield test_case_class

        # If it's actually a package, recursively descend.  If it's a true module, import its TestCase members
        elif isinstance(test_module, types.ModuleType):
            module_suites = suites + getattr(test_module, '_suites', [])

            # If it has a __path__, it should be a package (directory)
            if hasattr(test_module, '__path__'):
                module_filesystem_path = test_module.__path__[0]
                # but let's be sure
                if os.path.isdir(module_filesystem_path):
                    contents = os.listdir(module_filesystem_path)
                    for item in contents:
                        # ignore .svn and other miscellanea
                        if item.startswith('.'):
                            continue

                        # If it's actually a package (directory + __init__.py)
                        item_path = os.path.join(module_filesystem_path, item)
                        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, '__init__.py')):
                            for test_case_class in discover_inner("%s.%s" % (locator, item), suites=module_suites):
                                yield test_case_class

                        # other than directories, only look in .py files
                        elif item.endswith('.py'):
                            for test_case_class in discover_inner("%s.%s" % (locator, item[:-3]), suites=module_suites):
                                yield test_case_class

            # Otherwise it's some other type of module
            else:
                for member_name in dir(test_module):
                    obj = getattr(test_module, member_name)
                    if isinstance(obj, types.TypeType) and inspect.getmodule(obj) == test_module:
                        for test_case_class in discover_inner(obj, suites=module_suites):
                            yield test_case_class

        # it's not a list, it's not a bare module - let's see if it's an honest-to-god TestCaseBase
        elif isinstance(test_module, MetaTestCase) and (not '__test__' in test_module.__dict__ or bool(test_module.__test__)):
                if test_module not in discover_set:
                    _log.debug("discover: discovered %s" % test_module)
                    if suites:
                        if not hasattr(test_module, '_suites'):
                            setattr(test_module, '_suites', set())
                        elif not isinstance(test_module._suites, set):
                            test_module._suites = set(test_module._suites)
                        test_module._suites = test_module._suites | set(suites)
                    discover_set.add(test_module)
                    yield test_module

        # detect unittest test cases
        elif issubclass(test_module, unittest.TestCase) and (not '__test__' in test_module.__dict__ or bool(test_module.__test__)):
            test_case = TestifiedUnitTest.from_unittest_case(test_module, module_suites=suites)
            discover_set.add(test_case)
            yield test_case

    discover_set = set()
    time_start = time.time()

    for discovery in discover_inner(what):
        yield discovery

    time_end = time.time()
    _log.debug("discover: discovered %d test cases in %s" % (len(discover_set), time_end - time_start))

def import_test_class(module_path, class_name):
    for klass in discover(module_path):
        if klass.__name__ == class_name:
            return klass

    raise DiscoveryError(class_name)

########NEW FILE########
__FILENAME__ = test_fixtures
__testify =1
import contextlib
import inspect
import sys
from new import instancemethod

from testify.utils import inspection
from testify.test_result import TestResult


FIXTURE_TYPES = (
    'class_setup',
    'setup',
    'teardown',
    'class_teardown',
    'setup_teardown',
    'class_setup_teardown',
)
FIXTURES_WHICH_CAN_RETURN_UNEXPECTED_RESULTS = (
    'class_teardown',
    'class_setup_teardown',
)

# In general, inherited fixtures are applied first unless they are of these
# types. These fixtures are applied (in order of their definitions) starting
# with those defined on the current class, and then those defined on inherited
# classes (following MRO).
REVERSED_FIXTURE_TYPES = (
    'teardown',
    'class_teardown',
)

DEPRECATED_FIXTURE_TYPE_MAP = {
    'classSetUp': 'class_setup',
    'setUp': 'setup',
    'tearDown': 'teardown',
    'classTearDown': 'class_teardown',
}

TEARDOWN_FIXTURES = ['teardown', 'class_teardown']

SETUP_FIXTURES = ['setup', 'class_setup']

HYBRID_FIXTURES = ['setup_teardown', 'class_setup_teardown']


class TestFixtures(object):
    """
    Handles all the juggling of actual fixture methods and the context they are
    supposed to provide our tests.
    """

    def __init__(self, class_fixtures, instance_fixtures):
        # We convert all class-level fixtures to
        # class_setup_teardown fixtures a) to handle all
        # class-level fixtures the same and b) to make the
        # behavior more predictable when a TestCase has different
        # fixtures interacting.
        self.class_fixtures = self.sort(
            self.ensure_generator(f) for f in class_fixtures
        )
        self.instance_fixtures = self.sort(
            self.ensure_generator(f) for f in instance_fixtures
        )

    def ensure_generator(self, fixture):
        if fixture._fixture_type in HYBRID_FIXTURES:
            # already a context manager, nothing to do
            return fixture

        def wrapper(self):
            if fixture._fixture_type in SETUP_FIXTURES:
                fixture()
                yield
            elif fixture._fixture_type in TEARDOWN_FIXTURES:
                yield
                fixture()

        wrapper.__name__ = fixture.__name__
        wrapper.__doc__ = fixture.__doc__
        wrapper._fixture_type = fixture._fixture_type
        wrapper._fixture_id = fixture._fixture_id
        wrapper._defining_class_depth = fixture._defining_class_depth

        return instancemethod(wrapper, fixture.im_self, fixture.im_class)

    @contextlib.contextmanager
    def class_context(self, setup_callbacks=None, teardown_callbacks=None):
        with self.enter(self.class_fixtures, setup_callbacks, teardown_callbacks) as fixture_failures:
            yield fixture_failures

    @contextlib.contextmanager
    def instance_context(self):
        with self.enter(self.instance_fixtures) as fixture_failures:
            yield fixture_failures

    @contextlib.contextmanager
    def enter(self, fixtures, setup_callbacks=None, teardown_callbacks=None, stop_setups=False):
        """Transform each fixture_method into a context manager, enter them
        recursively, and yield any failures.

        `stop_setups` is set after a setup fixture fails. This flag prevents
        more setup fixtures from being added to the onion after a failure as we
        recurse through the list of fixtures.
        """

        # base case
        if not fixtures:
            yield []
            return

        setup_callbacks = setup_callbacks or [None, None]
        teardown_callbacks = teardown_callbacks or [None, None]

        fixture = fixtures[0]

        ctm = contextlib.contextmanager(fixture)()

        # class_teardown fixture is wrapped as
        # class_setup_teardown. We should not fire events for the
        # setup phase of this fake context manager.
        suppress_callbacks = bool(fixture._fixture_type in TEARDOWN_FIXTURES)

        # if a previous setup fixture failed, stop running new setup
        # fixtures.  this doesn't apply to teardown fixtures, however,
        # because behind the scenes they're setup_teardowns, and we need
        # to run the (empty) setup portion in order to get the teardown
        # portion later.
        if not stop_setups or fixture._fixture_type in TEARDOWN_FIXTURES:
            enter_failures = self.run_fixture(
                fixture,
                ctm.__enter__,
                enter_callback=None if suppress_callbacks else setup_callbacks[0],
                exit_callback=None if suppress_callbacks else setup_callbacks[1],
            )
            # keep skipping setups once we've had a failure
            stop_setups = stop_setups or bool(enter_failures)
        else:
            # we skipped the setup, pretend like nothing happened.
            enter_failures = []

        with self.enter(fixtures[1:], setup_callbacks, teardown_callbacks, stop_setups) as all_failures:
            all_failures += enter_failures or []
            # need to only yield one failure
            yield all_failures

        # this setup fixture got skipped due to an earlier setup fixture
        # failure, or failed itself. all of these fixtures are basically
        # represented by setup_teardowns, but because we never ran this setup,
        # we have nothing to do for teardown (if we did visit it here, that
        # would have the effect of running the setup we just skipped), so
        # instead bail out and move on to the next fixture on the stack.
        if stop_setups and fixture._fixture_type in SETUP_FIXTURES:
            return

        # class_setup fixture is wrapped as
        # class_setup_teardown. We should not fire events for the
        # teardown phase of this fake context manager.
        suppress_callbacks = bool(fixture._fixture_type in SETUP_FIXTURES)

        # this is hack to finish the remainder of the context manager without
        # calling contextlib's __exit__; doing that messes up the stack trace
        # we end up with.
        def exit():
            try:
                ctm.gen.next()
            except StopIteration:
                pass

        exit_failures = self.run_fixture(
            fixture,
            exit,
            enter_callback=None if suppress_callbacks else teardown_callbacks[0],
            exit_callback=None if suppress_callbacks else teardown_callbacks[1],
        )

        all_failures += exit_failures or []

    def run_fixture(self, fixture, function_to_call, enter_callback=None, exit_callback=None):

        result = TestResult(fixture)
        try:
            result.start()
            if enter_callback:
                enter_callback(result)
            if result.record(function_to_call):
                result.end_in_success()
            else:
                return result.exception_infos
            #else:
             #   self.failure_count += 1
        except (KeyboardInterrupt, SystemExit):
            result.end_in_interruption(sys.exc_info())
            raise
        finally:
            if exit_callback:
                exit_callback(result)

    def sort(self, fixtures):

        def key(fixture):
            """Use class depth, fixture type and fixture id to define
            a sortable key for fixtures.

            Class depth is the most significant value and defines the
            MRO (reverse mro for teardown methods) order. Fixture type
            and fixture id help us to define the expected order.

            See
            test.test_case_test.FixtureMethodRegistrationOrderWithBaseClassTest
            for the expected order.
            """
            fixture_order = {
                'class_setup' : 0,
                'class_teardown': 1,
                'class_setup_teardown': 2,

                'setup': 3,
                'teardown': 4,
                'setup_teardown': 5,
            }

            if fixture._fixture_type in REVERSED_FIXTURE_TYPES:
                ## class_teardown fixtures should be run in reverse
                ## definition order (last definition runs
                ## first). Converting fixture_id to its negative
                ## value will sort class_teardown fixtures in the
                ## same class in reversed order.
                return (fixture._defining_class_depth, fixture_order[fixture._fixture_type], -fixture._fixture_id)

            return (fixture._defining_class_depth, fixture_order[fixture._fixture_type], fixture._fixture_id)

        return sorted(fixtures, key=key)

    @classmethod
    def discover_from(cls, test_case):
        """Initialize and populate the lists of fixture methods for this TestCase.

        Fixture methods are identified by the fixture_decorator_factory when the
        methods are created. This means in order to figure out all the fixtures
        this particular TestCase will need, we have to test all of its attributes
        for 'fixture-ness'.

        See __fixture_decorator_factory for more info.
        """

        all_fixtures = {}
        for fixture_type in FIXTURE_TYPES:
            all_fixtures[fixture_type] = []

        # the list of classes in our heirarchy, starting with the highest class
        # (object), and ending with our class
        reverse_mro_list = [x for x in reversed(type(test_case).mro())]

        # discover which fixures are on this class, including mixed-in ones

        # we want to know everything on this class (including stuff inherited
        # from bases), but we don't want to trigger any lazily loaded
        # attributes, so dir() isn't an option; this traverses __bases__/__dict__
        # correctly for us.
        for classified_attr in inspect.classify_class_attrs(type(test_case)):
            # have to index here for Python 2.5 compatibility
            attr_name = classified_attr[0]
            unbound_method = classified_attr[3]
            defining_class = classified_attr[2]

            # skip everything that's not a function/method
            if not inspect.isroutine(unbound_method):
                continue

            # if this is an old setUp/tearDown/etc, tag it as a fixture
            if attr_name in DEPRECATED_FIXTURE_TYPE_MAP:
                fixture_type = DEPRECATED_FIXTURE_TYPE_MAP[attr_name]
                fixture_decorator = globals()[fixture_type]
                unbound_method = fixture_decorator(unbound_method)

            # collect all of our fixtures in appropriate buckets
            if inspection.is_fixture_method(unbound_method):
                # where in our MRO this fixture was defined
                defining_class_depth = reverse_mro_list.index(defining_class)
                inspection.callable_setattr(
                        unbound_method,
                        '_defining_class_depth',
                        defining_class_depth,
                )

                # we grabbed this from the class and need to bind it to the
                # test case
                instance_method = instancemethod(unbound_method, test_case, test_case.__class__)
                all_fixtures[instance_method._fixture_type].append(instance_method)

        class_level = ['class_setup', 'class_teardown', 'class_setup_teardown']
        inst_level = ['setup', 'teardown', 'setup_teardown']

        return cls(
            class_fixtures=sum([all_fixtures[typ] for typ in class_level], []),
            instance_fixtures=sum([all_fixtures[typ] for typ in inst_level], []),
        )


def suite(*args, **kwargs):
    """Decorator to conditionally assign suites to individual test methods.

    This decorator takes a variable number of positional suite arguments and two optional kwargs:
        - conditional: if provided and does not evaluate to True, the suite will not be applied.
        - reason: if provided, will be attached to the method for logging later.

    Can be called multiple times on one method to assign individual conditions or reasons.
    """
    def mark_test_with_suites(function):
        conditions = kwargs.get('conditions')
        reason = kwargs.get('reason')
        if not hasattr(function, '_suites'):
            function._suites = set()
        if args and (conditions is None or bool(conditions) is True):
            function._suites = set(function._suites) | set(args)
            if reason:
                if not hasattr(function, '_suite_reasons'):
                    function._suite_reasons = []
                function._suite_reasons.append(reason)
        return function

    return mark_test_with_suites


# unique id for fixtures
_fixture_id = [0]

def __fixture_decorator_factory(fixture_type):
    """Decorator generator for the fixture decorators.

    Tagging a class/instancemethod as 'setup', etc, will mark the method with a
    _fixture_id. Smaller fixture ids correspond to functions higher on the
    class hierarchy, since base classes (and their methods!) are created before
    their children.

    When our test cases are instantiated, they use this _fixture_id to sort
    methods into the appropriate _fixture_methods bucket. Note that this
    sorting cannot be done here, because this decorator does not recieve
    instancemethods -- which would be aware of their class -- because the class
    they belong to has not yet been created.

    **NOTE**: This means fixtures of the same type on a class will be executed
    in the order that they are defined, before/after fixtures execute on the
    parent class execute setups/teardowns, respectively.
    """

    def fixture_decorator(callable_):
        # Decorators act on *functions*, so we need to take care when dynamically
        # decorating class attributes (which are (un)bound methods).
        function = inspection.get_function(callable_)

        # record the fixture type and id for this function
        function._fixture_type = fixture_type

        if function.__name__ in DEPRECATED_FIXTURE_TYPE_MAP:
            # we push deprecated setUps/tearDowns to the beginning or end of
            # our fixture lists, respectively. this is the best we can do,
            # because these methods are generated in the order their classes
            # are created, so we can't assign a fair fixture_id to them.
            function._fixture_id = 0 if fixture_type.endswith('setup') else float('inf')
        else:
            # however, if we've tagged a fixture with our decorators then we
            # effectively register their place on the class hierarchy by this
            # fixture_id.
            function._fixture_id = _fixture_id[0]

        _fixture_id[0] += 1

        return function

    fixture_decorator.__name__ = fixture_type

    return fixture_decorator


class_setup = __fixture_decorator_factory('class_setup')
setup = __fixture_decorator_factory('setup')
teardown = __fixture_decorator_factory('teardown')
class_teardown = __fixture_decorator_factory('class_teardown')
setup_teardown = __fixture_decorator_factory('setup_teardown')
class_setup_teardown = __fixture_decorator_factory('class_setup_teardown')


class let(object):
    """Decorator that creates a lazy-evaluated helper property. The value is
    cached across multiple calls in the same test, but not across multiple
    tests.
    """

    _unsaved = []

    def __init__(self, func):
        self._func = func
        self._result = self._unsaved

    def __get__(self, test_case, cls):
        if test_case is None:
            return self
        if self._result is self._unsaved:
            self.__set__(test_case, self._func(test_case))
        return self._result

    def __set__(self, test_case, value):
        self._save_result(value)
        self._register_reset_after_test_completion(test_case)

    def _save_result(self, result):
        self._result = result

    def _register_reset_after_test_completion(self, test_case):
        test_case.register_callback(
                test_case.EVENT_ON_COMPLETE_TEST_METHOD,
                lambda _: self._reset_value(),
        )

    def _reset_value(self):
        self._result = self._unsaved

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_logger
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This module contains classes and constants related to outputting test results."""
__testify = 1

import collections
import logging
import operator
import subprocess
import sys

from testify import test_reporter

VERBOSITY_SILENT    = 0  # Don't say anything, just exit with a status code
VERBOSITY_NORMAL    = 1  # Output dots for each test method run
VERBOSITY_VERBOSE   = 2  # Output method names and timing information

class TestLoggerBase(test_reporter.TestReporter):

    def __init__(self, options, stream=sys.stdout):
        super(TestLoggerBase, self).__init__(options)
        self.stream = stream
        self.results = []
        self.test_case_classes = set()

    def test_start(self, result):
        self.test_case_classes.add((result['method']['module'], result['method']['class']))
        self.report_test_name(result['method'])

    def test_complete(self, result):
        self.report_test_result(result)
        self.results.append(result)
        if not result['success']:
            self.report_failure(result)

    def fixture_start(self, result):
        self.test_case_classes.add((result['method']['module'], result['method']['class']))

    def class_teardown_complete(self, result):
        if not result['success']:
            self.report_test_name(result['method'])
            self.report_test_result(result)
            self.results.append(result)

    def report(self):
        # All the TestCases have been run - now collate results by status and log them
        results_by_status = collections.defaultdict(list)
        for result in self.results:
            if result['success']:
                results_by_status['successful'].append(result)
            elif result['failure'] or result['error']:
                results_by_status['failed'].append(result)
            elif result['interrupted']:
                results_by_status['interrupted'].append(result)
            else:
                results_by_status['unknown'].append(result)

        if self.options.summary_mode:
            self.report_failures(results_by_status['failed'])
        self.report_stats(len(self.test_case_classes), **results_by_status)

        if len(self.results) == 0:
            return False
        else:
            return bool((len(results_by_status['failed']) + len(results_by_status['unknown'])) == 0)

    def report_test_name(self, test_method):
        pass

    def report_test_result(self, result):
        pass

    def report_failures(self, failed_results):
        if failed_results:
            self.heading('FAILURES', 'The following tests are expected to pass.')
            for result in failed_results:
                self.failure(result)
        else:
            # throwing this in so that someone looking at the bottom of the
            # output won't have to scroll up to figure out whether failures
            # were expected or not.
            self.heading('FAILURES', 'None!')

    def report_failure(self, result):
        pass

    def report_stats(self, test_case_count, all_results, failed_results, unknown_results):
        pass

    def _format_test_method_name(self, test_method):
        """Take a test method as input and return a string for output"""
        if test_method['module'] != '__main__':
            return "%s %s.%s" % (test_method['module'], test_method['class'], test_method['name'])
        else:
            return "%s.%s" % (test_method['class'], test_method['name'])

class TextTestLogger(TestLoggerBase):
    def __init__(self, options, stream=sys.stdout):
        super(TextTestLogger, self).__init__(options, stream)

        # Checking for color support isn't as fun as we might hope.  We're
        # going to use the command 'tput colors' to get a list of colors
        # supported by the shell. But of course we if this fails terribly,
        # we'll want to just fall back to no colors
        self.use_color = False
        if sys.stdin.isatty():
            try:
                output = subprocess.Popen(["tput", "colors"], stdout=subprocess.PIPE).communicate()[0]
                if int(output.strip()) >= 8:
                    self.use_color = True
            except Exception, e:
                if self.options.verbosity >= VERBOSITY_VERBOSE:
                    self.writeln("Failed to find color support: %r" % e)

    def write(self, message):
        """Write a message to the output stream, no trailing newline"""
        self.stream.write(message.encode('utf8') if isinstance(message, unicode) else message)
        self.stream.flush()

    def writeln(self, message):
        """Write a message and append a newline"""
        self.stream.write("%s\n" % (message.encode('utf8') if isinstance(message, unicode) else message))
        self.stream.flush()

    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

    def _colorize(self, message, color = CYAN):
        if not color or not self.use_color:
            return message
        else:
            start_color = chr(0033) + '[1;%sm' % color
            end_color = chr(0033) + '[m'
            return start_color + message + end_color

    def test_discovery_failure(self, exc):
        self.writeln(self._colorize("DISCOVERY FAILURE!", self.MAGENTA))
        self.writeln("There was a problem importing one or more tests:")
        self.writeln(str(exc))

    def report_test_name(self, test_method):
        if self.options.verbosity >= VERBOSITY_VERBOSE:
            self.write("%s ... " % self._format_test_method_name(test_method))

    def report_test_result(self, result):
        if self.options.verbosity > VERBOSITY_SILENT:
            if result['success']:
                if result['previous_run']:
                    status = "flaky"
                else:
                    status = "success"
            elif result['failure']:
                status = "fail"
            elif result['error']:
                status = "error"
            elif result['interrupted']:
                status = "interrupted"
            else:
                status = "unknown"

            status_description, status_letter, color = {
                "success" : ('ok', '.', self.GREEN),
                "flaky" : ('flaky', '!', self.YELLOW),
                "fail" : ('FAIL', 'F', self.RED),
                "error" : ('ERROR', 'E', self.RED),
                "interrupted" : ('INTERRUPTED', '-', self.YELLOW),
                "unknown" : ('UNKNOWN', '?', None),
            }[status]

            if status in ('fail', 'error'):
                self.writeln("%s: %s\n%s" % (status, self._format_test_method_name(result['method']), result['exception_info']))

            if self.options.verbosity == VERBOSITY_NORMAL:
                self.write(self._colorize(status_letter, color))
            else:
                if result['normalized_run_time']:
                    self.writeln("%s in %s" % (self._colorize(status_description, color), result['normalized_run_time']))
                else:
                    self.writeln(self._colorize(status_description, color))

    def heading(self, *messages):
        self.writeln("")
        self.writeln("=" * 72)
        for line in messages:
            self.writeln(line)

    def failure(self, result):
        self.writeln("")
        self.writeln("=" * 72)
        self.writeln(self._format_test_method_name(result['method']))

        if self.use_color:
            self.writeln(result['exception_info_pretty'])
        else:
            self.writeln(result['exception_info'])

        self.writeln('=' * 72)
        self.writeln("")

    def report_stats(self, test_case_count, **results):
        successful = results.get('successful', [])
        failed = results.get('failed', [])
        interrupted = results.get('interrupted', [])
        unknown = results.get('unknown', [])

        test_method_count = sum(len(bucket) for bucket in results.values())
        test_word = "test" if test_method_count == 1 else "tests"
        case_word = "case" if test_case_count == 1 else "cases"
        overall_success = not failed and not unknown and not interrupted

        self.writeln('')

        if overall_success:
            if successful:
                status_string = self._colorize("PASSED", self.GREEN)
            else:
                if test_method_count == 0:
                    self.writeln("No tests were discovered (tests must subclass TestCase and test methods must begin with 'test').")
                status_string = self._colorize("ERROR", self.MAGENTA)
        else:
            status_string = self._colorize("FAILED", self.RED)

        self.write("%s.  " % status_string)
        self.write("%d %s / %d %s: " % (test_method_count, test_word, test_case_count, case_word))

        passed_string = self._colorize("%d passed" % len(successful), (self.GREEN if len(successful) else None))

        failed_string = self._colorize("%d failed" % len(failed), (self.RED if len(failed) else None))

        self.write("%s, %s.  " % (passed_string, failed_string))

        total_test_time = reduce(
            operator.add,
            (result['run_time'] for result in (successful+failed+interrupted)),
            0,
            )
        self.writeln("(Total test time %.2fs)" % total_test_time)


class ColorlessTextTestLogger(TextTestLogger):
    def _colorize(self, message, color=None):
        return message


class TestResultGrabberHandler(logging.Handler):
    """Logging handler to store log message during a test run"""
    def emit(self, record):
        raise Exception(repr(record))

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_program
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import with_statement

from collections import defaultdict
from optparse import OptionParser
import os
import pwd
import socket
import sys
import logging
import imp

import testify
from testify import test_logger
from testify.test_runner import TestRunner

ACTION_RUN_TESTS = 0
ACTION_LIST_SUITES = 1
ACTION_LIST_TESTS = 2

DEFAULT_PLUGIN_PATH = os.path.join(os.path.split(__file__)[0], 'plugins')

log = logging.getLogger('testify')

def get_bucket_overrides(filename):
    """Returns a map from test class name to test bucket.

    test class name: {test module}.{classname}
    test bucket: int
    """
    ofile = open(filename)
    overrides = {}
    for line in ofile.readlines():
        if line.startswith('#'):
            continue
        if line.strip() == '':
            continue
        test_module_and_class, bucket = line.strip().split(',')
        overrides[test_module_and_class] = int(bucket)
    ofile.close()
    return overrides

def load_plugins():
    """Load any plugin modules

    We load plugin modules based on directories provided to us by the environment, as well as a default in our own folder.

    Returns a list of module objects
    """
    # This function is a little wacky, doesn't seem like we SHOULD have to do all this just to get the behavior we want.
    # The idea will be to check out the directory contents and pick up any files that seem to match what python knows how to
    # import.

    # To properly load the module, we'll need to identify what type it is by the file extension
    suffix_map = {}
    for suffix in imp.get_suffixes():
        suffix_map[suffix[0]] = suffix

    plugin_directories = [DEFAULT_PLUGIN_PATH]
    if 'TESTIFY_PLUGIN_PATH' in os.environ:
        plugin_directories += os.environ['TESTIFY_PLUGIN_PATH'].split(':')

    plugin_modules = []
    for plugin_path in plugin_directories:
        for file_name in os.listdir(plugin_path):

            # For any file that we know how to load, try to import it
            if any(file_name.endswith('.py') and not file_name.startswith('.') for suffix in suffix_map.iterkeys()):
                full_file_path = os.path.join(plugin_path, file_name)
                mod_name, suffix = os.path.splitext(file_name)

                with open(full_file_path, "r") as file:
                    try:
                        plugin_modules.append(imp.load_module(mod_name, file, full_file_path, suffix_map.get(suffix)))
                    except TypeError:
                        continue
                    except ImportError, e:
                        print >>sys.stderr, "Failed to import plugin %s: %r" % (full_file_path, e)
                    except Exception, e:
                        raise Exception('whaa?: %r' % e)
    return plugin_modules


def parse_test_runner_command_line_args(plugin_modules, args):
    """Parse command line args for the TestRunner to determine verbosity and other stuff"""
    parser = OptionParser(
            usage="%prog <test path> [options]",
            version="%%prog %s" % testify.__version__,
            prog='testify')

    parser.set_defaults(verbosity=test_logger.VERBOSITY_NORMAL)
    parser.add_option("-s", "--silent", action="store_const", const=test_logger.VERBOSITY_SILENT, dest="verbosity")
    parser.add_option("-v", "--verbose", action="store_const", const=test_logger.VERBOSITY_VERBOSE, dest="verbosity")
    parser.add_option("-d", "--ipdb", action="store_true", dest="debugger", help="Enter post mortem debugging mode with ipdb in the case of an exception thrown in a test method or fixture method.")

    parser.add_option("-i", "--include-suite", action="append", dest="suites_include", type="string", default=[])
    parser.add_option("-x", "--exclude-suite", action="append", dest="suites_exclude", type="string", default=[])
    parser.add_option("-q", "--require-suite", action="append", dest="suites_require", type="string", default=[])

    parser.add_option("--list-suites", action="store_true", dest="list_suites")
    parser.add_option("--list-tests", action="store_true", dest="list_tests")

    parser.add_option("--label", action="store", dest="label", type="string", help="label for this test run")

    parser.add_option("--bucket", action="store", dest="bucket", type="int")
    parser.add_option("--bucket-count", action="store", dest="bucket_count", type="int")
    parser.add_option("--bucket-overrides-file", action="store", dest="bucket_overrides_file", default=None)
    parser.add_option("--bucket-salt", action="store", dest="bucket_salt", default=None)

    parser.add_option("--summary", action="store_true", dest="summary_mode")
    parser.add_option("--no-color", action="store_true", dest="disable_color", default=bool(not os.isatty(sys.stdout.fileno())))

    parser.add_option("--log-file", action="store", dest="log_file", type="string", default=None)
    parser.add_option("--log-level", action="store", dest="log_level", type="string", default="INFO")
    parser.add_option('--print-log', action="append", dest="print_loggers", type="string", default=[], help="Direct logging output for these loggers to the console")

    parser.add_option('--serve', action="store", dest="serve_port", type="int", default=None, help="Run in server mode, listening on this port for testify clients.")
    parser.add_option('--connect', action="store", dest="connect_addr", type="string", default=None, metavar="HOST:PORT", help="Connect to a testify server (testify --serve) at this HOST:PORT")
    parser.add_option('--revision', action="store", dest="revision", type="string", default=None, help="With --serve, refuses clients that identify with a different or no revision. In client mode, sends the revision number to the server for verification.")
    parser.add_option('--retry-limit', action="store", dest="retry_limit", type="int", default=60, help="Number of times to try connecting to the server before exiting.")
    parser.add_option('--retry-interval', action="store", dest="retry_interval", type="int", default=2, help="Interval, in seconds, between trying to connect to the server.")
    parser.add_option('--reconnect-retry-limit', action="store", dest="reconnect_retry_limit", type="int", default=5, help="Number of times to try reconnecting to the server before exiting if we have previously connected.")
    parser.add_option('--disable-requeueing', action="store_true", dest="disable_requeueing", help="Disable re-queueing/re-running failed tests on a different builder.")

    parser.add_option('--failure-limit', action="store", dest="failure_limit", type="int", default=None, help="Quit after this many test failures.")
    parser.add_option('--runner-timeout', action="store", dest="runner_timeout", type="int", default=300, help="How long to wait to wait for activity from a test runner before requeuing the tests it has checked out.")
    parser.add_option('--server-timeout', action="store", dest="server_timeout", type="int", default=300, help="How long to wait after the last activity from any test runner before shutting down.")

    parser.add_option('--server-shutdown-delay', action='store', dest='shutdown_delay_for_connection_close', type="float", default=0.01, help="How long to wait (in seconds) for data to finish writing to sockets before shutting down the server.")
    parser.add_option('--server-shutdown-delay-outstanding-runners', action='store', dest='shutdown_delay_for_outstanding_runners', type='int', default=5, help="How long to wait (in seconds) for all clients to check for new tests before shutting down the server.")

    parser.add_option('--runner-id', action="store", dest="runner_id", type="string", default="%s-%d" % (socket.gethostname(), os.getpid()), help="With --connect, an identity passed to the server on each request. Passed to the server's test reporters. Defaults to <HOST>-<PID>.")

    parser.add_option('--replay-json', action="store", dest="replay_json", type="string", default=None, help="Instead of discovering and running tests, read a file with one JSON-encoded test result dictionary per line, and report each line to test reporters as if we had just run that test.")
    parser.add_option('--replay-json-inline', action="append", dest="replay_json_inline", type="string", metavar="JSON_OBJECT", help="Similar to --replay-json, but allows result objects to be passed on the command line. May be passed multiple times. If combined with --replay-json, inline results get reported first.")

    parser.add_option('--rerun-test-file', action="store", dest="rerun_test_file", type="string", default=None, help="Rerun tests listed in FILE in order. One test per line, in the format 'path.to.class ClassName.test_method_name'. Consecutive tests in the same class will be run on the same test class instance.")

    # Add in any additional options
    for plugin in plugin_modules:
        if hasattr(plugin, 'add_command_line_options'):
            plugin.add_command_line_options(parser)

    (options, args) = parser.parse_args(args)
    if len(args) < 1 and not (options.connect_addr or options.rerun_test_file or options.replay_json or options.replay_json_inline):
        parser.error("Test path required unless --connect or --rerun-test-file specified.")

    if options.connect_addr and options.serve_port:
        parser.error("--serve and --connect are mutually exclusive.")

    test_path, module_method_overrides = _parse_test_runner_command_line_module_method_overrides(args)

    if pwd.getpwuid(os.getuid()).pw_name == 'buildbot':
        options.disable_color = True

    if options.list_suites:
        runner_action = ACTION_LIST_SUITES
    elif options.list_tests:
        runner_action = ACTION_LIST_TESTS
    else:
        runner_action = ACTION_RUN_TESTS


    test_runner_args = {
        'debugger': options.debugger,
        'suites_include': options.suites_include,
        'suites_exclude': options.suites_exclude,
        'suites_require': options.suites_require,
        'failure_limit' : options.failure_limit,
        'module_method_overrides': module_method_overrides,
        'options': options,
        'plugin_modules': plugin_modules
    }

    return runner_action, test_path, test_runner_args, options

def _parse_test_runner_command_line_module_method_overrides(args):
    """Parse a set of positional args (returned from an OptionParser probably)
    for specific modules or test methods.
    eg/ > python some_module_test.py SomeTestClass.some_test_method
    """
    test_path = args[0] if args else None

    module_method_overrides = defaultdict(set)
    for arg in args[1:]:
        module_path_components = arg.split('.')
        module_name = module_path_components[0]
        method_name = module_path_components[1] if len(module_path_components) > 1 else None
        if method_name:
            module_method_overrides[module_name].add(method_name)
        else:
            module_method_overrides[module_name] = None

    return test_path, module_method_overrides


class TestProgram(object):

    def __init__(self, command_line_args=None):
        """Initialize and run the test with the given command_line_args
            command_line_args will be passed to parser.parse_args
        """
        self.plugin_modules = load_plugins()
        command_line_args = command_line_args or sys.argv[1:]
        self.runner_action, self.test_path, self.test_runner_args, self.other_opts = parse_test_runner_command_line_args(
            self.plugin_modules,
            command_line_args
        )

        # allow plugins to modify test program
        for plugin_mod in self.plugin_modules:
            if hasattr(plugin_mod, "prepare_test_program"):
                plugin_mod.prepare_test_program(self.other_opts, self)

    def get_reporters(self, options, plugin_modules):
        reporters = []
        if options.disable_color:
            reporters.append(test_logger.ColorlessTextTestLogger(options))
        else:
            reporters.append(test_logger.TextTestLogger(options))

        for plugin in plugin_modules:
            if hasattr(plugin, "build_test_reporters"):
                reporters += plugin.build_test_reporters(options)
        return reporters

    def run(self):
        """Run testify, return True on success, False on failure."""
        self.setup_logging(self.other_opts)

        bucket_overrides = {}
        if self.other_opts.bucket_overrides_file:
            bucket_overrides = get_bucket_overrides(self.other_opts.bucket_overrides_file)

        if self.other_opts.serve_port:
            from test_runner_server import TestRunnerServer
            test_runner_class = TestRunnerServer
            self.test_runner_args['serve_port'] = self.other_opts.serve_port
        elif self.other_opts.connect_addr:
            from test_runner_client import TestRunnerClient
            test_runner_class = TestRunnerClient
            self.test_runner_args['connect_addr'] = self.other_opts.connect_addr
            self.test_runner_args['runner_id'] = self.other_opts.runner_id
        elif self.other_opts.replay_json or self.other_opts.replay_json_inline:
            from test_runner_json_replay import TestRunnerJSONReplay
            test_runner_class = TestRunnerJSONReplay
            self.test_runner_args['replay_json'] = self.other_opts.replay_json
            self.test_runner_args['replay_json_inline'] = self.other_opts.replay_json_inline
        elif self.other_opts.rerun_test_file:
            from test_rerunner import TestRerunner
            test_runner_class = TestRerunner
            self.test_runner_args['rerun_test_file'] = self.other_opts.rerun_test_file
        else:
            test_runner_class = TestRunner

        # initialize reporters 
        self.test_runner_args['test_reporters'] = self.get_reporters(
            self.other_opts, self.test_runner_args['plugin_modules']
        )

        runner = test_runner_class(
            self.test_path,
            bucket_overrides=bucket_overrides,
            bucket_count=self.other_opts.bucket_count,
            bucket_salt=self.other_opts.bucket_salt,
            bucket=self.other_opts.bucket,
            **self.test_runner_args
        )

        if self.runner_action == ACTION_LIST_SUITES:
            runner.list_suites()
            return True
        elif self.runner_action == ACTION_LIST_TESTS:
            runner.list_tests()
            return True
        elif self.runner_action == ACTION_RUN_TESTS:
            label_text = ""
            bucket_text = ""
            if self.other_opts.label:
                label_text = " " + self.other_opts.label
            if self.other_opts.bucket_count:
                salt_info =  (' [salt: %s]' % self.other_opts.bucket_salt) if self.other_opts.bucket_salt else ''
                bucket_text = " (bucket %d of %d%s)" % (self.other_opts.bucket, self.other_opts.bucket_count, salt_info)
            log.info("starting test run%s%s", label_text, bucket_text)

            # Allow plugins to modify the test runner.
            for plugin_mod in self.test_runner_args['plugin_modules']:
                if hasattr(plugin_mod, "prepare_test_runner"):
                    plugin_mod.prepare_test_runner(self.test_runner_args['options'], runner)

            return runner.run()

    def setup_logging(self, options):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
        console.setLevel(logging.WARNING)
        root_logger.addHandler(console)

        if options.log_file:
            handler = logging.FileHandler(options.log_file, "a")
            handler.setFormatter(logging.Formatter('%(asctime)s\t%(name)-12s: %(levelname)-8s %(message)s'))

            log_level = getattr(logging, options.log_level)
            handler.setLevel(log_level)

            root_logger.addHandler(handler)

        if options.print_loggers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(name)-12s: %(message)s')
            console.setFormatter(formatter)

            for logger_name in options.print_loggers:
                logging.getLogger(logger_name).addHandler(handler)


def run():
    """Entry point for running a test file directly."""
    args = ["__main__"] + sys.argv[1:]
    sys.exit(not TestProgram(command_line_args=args).run())


def main():
    sys.exit(not TestProgram().run())


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_reporter
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class TestReporter(object):
    """Base interface for tracking results of test runs

    A TestReporter is configured as a callback for each test case by test_runner.
    """
    def __init__(self, options):
        """Constructor

        Args -
            options - The result of  OptionParser which contains, as attributes, all the options for the running program.
        """
        self.options = options

    def test_counts(self, test_case_count, test_method_count):
        """Called after discovery finishes. May not be called by all test runners, e.g. TestRunnerClient."""
        pass

    def test_start(self, result):
        """Called when a test method is being run. Gets passed a TestResult dict which should not be complete."""
        pass

    def test_complete(self, result):
        """Called when a test method is complete. result is a TestResult dict which should be complete."""
        pass

    def test_discovery_failure(self, exc):
        """Called when there was a failure during test discovery. exc is the exception object generated during the error."""

    def class_setup_start(self, result):
        """Called when a class_setup or the first half of a class_setup_teardown starts"""
        pass

    def class_setup_complete(self, result):
        """Called when a class_setup or the first half of a class_setup_teardown finishes"""
        pass

    def class_teardown_start(self, result):
        """Called when a class_teardown or the second half of a class_setup_teardown starts"""
        pass

    def class_teardown_complete(self, result):
        """Called when a class_teardown or the second half of a class_setup_teardown finishes"""
        pass

    def test_case_start(self, result):
        """Called when a test case is being run. Gets passed the special "run" method as a TestResult."""
        pass

    def test_case_complete(self, result):
        """Called when a test case and all of its fixtures have been run."""
        pass

    def report(self):
        """Called at the end of the test run to report results

        Should return a bool to indicate if the reporter thinks the test run was successful
        """
        return True

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_rerunner
from itertools import groupby
import sys

import test_discovery
from test_runner import TestRunner

class TestRerunner(TestRunner):
    def __init__(self, *args, **kwargs):
        filename = kwargs.pop('rerun_test_file')
        if filename == '-':
            self.rerun_test_file = sys.stdin
        else:
            self.rerun_test_file = open(filename)
        super(TestRerunner, self).__init__(*args, **kwargs)

    def discover(self):
        for class_path, lines in groupby(self.rerun_test_file, lambda line: line.rpartition('.')[0]):
            if not class_path:
                # Skip blank lines
                continue
            methods = [line.rpartition('.')[2].strip() for line in lines]

            module_path, _, class_name = class_path.partition(' ')

            klass = test_discovery.import_test_class(module_path, class_name)
            yield klass(name_overrides=methods)

########NEW FILE########
__FILENAME__ = test_result
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This module contains the TestResult class, each instance of which holds status information for a single test method."""
__testify = 1
import datetime
import sys
import time
import traceback

from testify.utils import inspection

#If IPython is available, use it for fancy color traceback formatting
try:
    try:
        # IPython >= 0.11
        from IPython.core.ultratb import ListTB
        _hush_pyflakes = [ListTB]
        del _hush_pyflakes
    except ImportError:
        # IPython < 0.11
        from IPython.ultraTB import ListTB

    list_tb = ListTB(color_scheme='Linux')
    def fancy_tb_formatter(etype, value, tb, length=None):
        tb = traceback.extract_tb(tb, limit=length)
        return list_tb.text(etype, value, tb, context=0)
except ImportError:
    fancy_tb_formatter = None

def plain_tb_formatter(etype, value, tb, length=None):
    # We want our formatters to return a string.
    return ''.join(traceback.format_exception(etype, value, tb, length))

class TestResult(object):
    debug = False

    def __init__(self, test_method, runner_id=None):
        super(TestResult, self).__init__()
        self.test_method = test_method
        self.test_method_name = test_method.__name__
        self.success = self.failure = self.error = self.interrupted = None
        self.run_time = self.start_time = self.end_time = None
        self.exception_infos = []
        self.complete = False
        self.previous_run = None
        self.runner_id = runner_id

    @property
    def exception_info(self):
        raise AttributeError('The exception_info attribute has been replaced with the .exception_infos list. Please update your code.')

    def start(self, previous_run=None):
        self.previous_run = previous_run
        self.start_time = datetime.datetime.now()

    def record(self, function):
        """Excerpted code for executing a block of code that might raise an
        exception, requiring us to update a result object.

        Return value is a boolean describing whether the block was successfully
        executed without exceptions.
        """
        try:
            function()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, exception:
            # some code may want to use an alternative exc_info for an exception
            # (for instance, in an event loop). You can signal an alternative
            # stack to use by adding a _testify_exc_tb attribute to the
            # exception object
            if hasattr(exception, '_testify_exc_tb'):
                exc_info = (type(exception), exception, exception._testify_exc_tb)
            else:
                exc_info = sys.exc_info()

            self.end_in_failure(exc_info)

            if self.debug:
                self._postmortem(exc_info)
            return False
        else:
            return True

    def _postmortem(self, exc_info):
        _, _, traceback = exc_info
        print "\nDEBUGGER"
        print self.format_exception_info()
        try:
            import ipdb
            detected_postmortem_tool = ipdb.post_mortem
        except ImportError:
            import pdb
            detected_postmortem_tool = pdb.post_mortem
        detected_postmortem_tool(traceback)

    def _complete(self):
        self.complete = True
        self.end_time = datetime.datetime.now()
        self.run_time = self.end_time - self.start_time

    def end_in_failure(self, exception_info):
        if not self.complete:
            self._complete()

        self.success = False

        if isinstance(exception_info[1], AssertionError):
            # test failure, kinda expect these vs. unknown errors
            self.failure = True
        else:
            self.error = True

        self.exception_infos.append(exception_info)

    def end_in_success(self):
        if not self.complete:
            self._complete()
            self.success = True

    def end_in_interruption(self, exception_info):
        if not self.complete:
            self._complete()
            self.interrupted = True
            self.exception_infos.append(exception_info)

    def __make_multi_error_message(self, formatter):
        result = []
        for exception_info in self.exception_infos:
            exctype, value, tb = exception_info
            part = formatter(exctype, value, tb)
            result.append(part)

        if len(result) == 1:
            return result[0]
        else:
            # Meant to match the python3 multiple-exception support:
            #   http://docs.python.org/3.1/reference/simple_stmts.html#the-raise-statement
            return '\nDuring handling of the above exception, another exception occurred:\n\n'.join(result)

    def format_exception_info(self, pretty=False):
        if not self.exception_infos:
            return None

        tb_formatter = fancy_tb_formatter if (pretty and fancy_tb_formatter) else plain_tb_formatter

        def is_relevant_tb_level(tb):
            if tb.tb_frame.f_globals.has_key('__testify'):
                # nobody *wants* to read testify
                return False
            else:
                return True

        def count_relevant_tb_levels(tb):
            # count up to the *innermost* relevant frame
            length = 0
            relevant = 0
            while tb:
                length += 1
                if is_relevant_tb_level(tb):
                    relevant = length
                tb = tb.tb_next
            return relevant

        def formatter(exctype, value, tb):
            # Skip test runner traceback levels at the top.
            while tb and not is_relevant_tb_level(tb):
                tb = tb.tb_next

            if exctype is AssertionError:
                # Skip testify.assertions traceback levels at the bottom.
                length = count_relevant_tb_levels(tb)
                return tb_formatter(exctype, value, tb, length)
            elif not tb:
                return "Exception: %r (%r)" % (exctype, value)
            else:
                return tb_formatter(exctype, value, tb)

        return self.__make_multi_error_message(formatter)

    def format_exception_only(self):
        def formatter(exctype, value, tb):
            return ''.join(traceback.format_exception_only(exctype, value))

        return self.__make_multi_error_message(formatter)

    def to_dict(self):
        return {
            'previous_run' : self.previous_run,
            'start_time' : time.mktime(self.start_time.timetuple()) if self.start_time else None,
            'end_time' : time.mktime(self.end_time.timetuple()) if self.end_time else None,
            'run_time' : (self.run_time.seconds + float(self.run_time.microseconds) / 1000000) if self.run_time else None,
            'normalized_run_time' : None if not self.run_time else "%.2fs" % (self.run_time.seconds + (self.run_time.microseconds / 1000000.0)),
            'complete': self.complete,
            'success' : self.success,
            'failure' : self.failure,
            'error' : self.error,
            'interrupted' : self.interrupted,
            'exception_info' : self.format_exception_info(),
            'exception_info_pretty' : self.format_exception_info(pretty=True),
            'exception_only' : self.format_exception_only(),
            'runner_id' : self.runner_id,
            'method' : {
                'module' : self.test_method.im_class.__module__,
                'class' : self.test_method.im_class.__name__,
                'name' : self.test_method.__name__,
                'full_name' : '%s %s.%s' % (self.test_method.im_class.__module__, self.test_method.im_class.__name__, self.test_method.__name__),
                'fixture_type' : None if not inspection.is_fixture_method(self.test_method) else self.test_method._fixture_type,
            }
        }

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_runner
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

"""This module contains the TestRunner class and other helper code"""
__author__ = "Oliver Nicholas <bigo@yelp.com>"
__testify = 1

from collections import defaultdict
import itertools
import functools
import pprint
import sys

from test_case import MetaTestCase, TestCase
import test_discovery


class TestRunner(object):
    """TestRunner is the controller class of the testify suite.

    It is responsible for collecting a list of TestCase subclasses, instantiating and
    running them, delegating the collection of results and printing of statistics.
    """

    def __init__(self,
                 test_path_or_test_case,
                 bucket=None,
                 bucket_count=None,
                 bucket_overrides=None,
                 bucket_salt=None,
                 debugger=None,
                 suites_include=(),
                 suites_exclude=(),
                 suites_require=(),
                 options=None,
                 test_reporters=None,
                 plugin_modules=None,
                 module_method_overrides=None,
                 failure_limit=None
                 ):
        """After instantiating a TestRunner, call run() to run them."""

        self.test_path_or_test_case = test_path_or_test_case
        self.bucket = bucket
        self.bucket_count = bucket_count
        self.bucket_overrides = bucket_overrides if bucket_overrides is not None else {}
        self.bucket_salt = bucket_salt

        self.debugger = debugger

        self.suites_include = set(suites_include)
        self.suites_exclude = set(suites_exclude)
        self.suites_require = set(suites_require)

        self.options = options

        self.plugin_modules = plugin_modules or []
        self.test_reporters = test_reporters or []
        self.module_method_overrides = module_method_overrides if module_method_overrides is not None else {}

        self.failure_limit = failure_limit
        self.failure_count = 0

    @classmethod
    def get_test_method_name(cls, test_method):
        return '%s %s.%s' % (
            test_method.im_class.__module__,
            test_method.im_class.__name__,
            test_method.__name__,
        )

    def discover(self):
        def construct_test(test_case_class):
            test_case = test_case_class(
                suites_include=self.suites_include,
                suites_exclude=self.suites_exclude,
                suites_require=self.suites_require,
                name_overrides=self.module_method_overrides.get(test_case_class.__name__, None),
                failure_limit=(self.failure_limit - self.failure_count) if self.failure_limit else None,
                debugger=self.debugger,
            )
            return test_case

        def discover_tests():
            return [
                construct_test(test_case_class)
                for test_case_class in test_discovery.discover(self.test_path_or_test_case)
                if not self.module_method_overrides or test_case_class.__name__ in self.module_method_overrides
            ]

        def discover_tests_by_buckets():
            # Sort by the test count, use the cmp_str as a fallback for determinism
            test_cases = sorted(
                discover_tests(),
                key=lambda test_case: (
                    -1 * len(list(test_case.runnable_test_methods())),
                    MetaTestCase._cmp_str(type(test_case)),
                )
            )

            # Assign buckets round robin
            buckets = defaultdict(list)
            for bucket, test_case in itertools.izip(
                itertools.cycle(
                    range(self.bucket_count) + list(reversed(range(self.bucket_count)))
                ),
                test_cases,
            ):
                # If the class is supposed to be specially bucketed, do so
                bucket = self.bucket_overrides.get(MetaTestCase._cmp_str(type(test_case)), bucket)
                buckets[bucket].append(test_case)

            return buckets[self.bucket]

        def discover_tests_testing():
            # For testing purposes only
            return [self.test_path_or_test_case()]

        discovered_tests = []
        try:
            if isinstance(self.test_path_or_test_case, (TestCase, MetaTestCase)):
                discovered_tests = discover_tests_testing()
            elif self.bucket is not None:
                discovered_tests = discover_tests_by_buckets()
            else:
                discovered_tests = discover_tests()
        except test_discovery.DiscoveryError, exc:
            for reporter in self.test_reporters:
                reporter.test_discovery_failure(exc)
            sys.exit(1)
        test_case_count = len(discovered_tests)
        test_method_count = sum(len(list(test_case.runnable_test_methods())) for test_case in discovered_tests)
        for reporter in self.test_reporters:
            reporter.test_counts(test_case_count, test_method_count)
        return discovered_tests

    def run(self):
        """Instantiate our found test case classes and run their test methods.

        We use this opportunity to apply any test method name overrides that were parsed
        from the command line (or rather, passed in on initialization).

        Logging of individual results is accomplished by registering callbacks for
        the TestCase instances to call when they begin and finish running each test.

        At its conclusion, we pass our collected results to our TestLogger to
        print out exceptions and testing summaries.
        """

        try:
            for test_case in self.discover():
                if self.failure_limit and self.failure_count >= self.failure_limit:
                    break

                # We allow our plugins to mutate the test case prior to execution
                for plugin_mod in self.plugin_modules:
                    if hasattr(plugin_mod, "prepare_test_case"):
                        plugin_mod.prepare_test_case(self.options, test_case)

                if not any(test_case.runnable_test_methods()):
                    continue

                def failure_counter(result_dict):
                    if not result_dict['success']:
                        self.failure_count += 1

                for reporter in self.test_reporters:
                    test_case.register_callback(test_case.EVENT_ON_RUN_TEST_METHOD, reporter.test_start)
                    test_case.register_callback(test_case.EVENT_ON_COMPLETE_TEST_METHOD, reporter.test_complete)

                    test_case.register_callback(test_case.EVENT_ON_RUN_CLASS_SETUP_METHOD, reporter.class_setup_start)
                    test_case.register_callback(test_case.EVENT_ON_COMPLETE_CLASS_SETUP_METHOD, reporter.class_setup_complete)

                    test_case.register_callback(test_case.EVENT_ON_RUN_CLASS_TEARDOWN_METHOD, reporter.class_teardown_start)
                    test_case.register_callback(test_case.EVENT_ON_COMPLETE_CLASS_TEARDOWN_METHOD, reporter.class_teardown_complete)

                    test_case.register_callback(test_case.EVENT_ON_RUN_TEST_CASE, reporter.test_case_start)
                    test_case.register_callback(test_case.EVENT_ON_COMPLETE_TEST_CASE, reporter.test_case_complete)

                test_case.register_callback(test_case.EVENT_ON_COMPLETE_TEST_METHOD, failure_counter)

                # Now we wrap our test case like an onion. Each plugin given the opportunity to wrap it.
                runnable = test_case.run
                for plugin_mod in self.plugin_modules:
                    if hasattr(plugin_mod, "run_test_case"):
                        runnable = functools.partial(plugin_mod.run_test_case, self.options, test_case, runnable)

                # And we finally execute our finely wrapped test case
                runnable()

        except (KeyboardInterrupt, SystemExit):
            # we'll catch and pass a keyboard interrupt so we can cancel in the middle of a run
            # but still get a testing summary.
            pass

        report = [reporter.report() for reporter in self.test_reporters]
        return all(report)

    def list_suites(self):
        """List the suites represented by this TestRunner's tests."""
        suites = defaultdict(list)
        for test_instance in self.discover():
            for test_method in test_instance.runnable_test_methods():
                for suite_name in test_instance.suites(test_method):
                    suites[suite_name].append(test_method)
        suite_counts = dict((suite_name, "%d tests" % len(suite_members)) for suite_name, suite_members in suites.iteritems())

        pp = pprint.PrettyPrinter(indent=2)
        print(pp.pformat(dict(suite_counts)))

        return suite_counts

    def get_tests_for_suite(self, selected_suite_name):
        """Gets the test list for the suite"""
        test_list = []
        for test_instance in self.discover():
            for test_method in test_instance.runnable_test_methods():
                if not selected_suite_name or TestCase.in_suite(test_method, selected_suite_name):
                    test_list.append(test_method)
        return test_list

    def list_tests(self, selected_suite_name=None):
        """Lists all tests, optionally scoped to a single suite."""
        test_list = self.get_tests_for_suite(selected_suite_name)
        for test_method_name in (
            self.get_test_method_name(test)
            for test in test_list
        ):
            print(test_method_name)

        return test_list

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = test_runner_client
"""
Client-server setup for evenly distributing tests across multiple processes.
See the test_runner_server module.
"""
import urllib2
try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json
import time
import logging

import test_discovery
from test_runner import TestRunner


class TestRunnerClient(TestRunner):
    def __init__(self, *args, **kwargs):
        self.connect_addr = kwargs.pop('connect_addr')
        self.runner_id = kwargs.pop('runner_id')
        self.revision = kwargs['options'].revision

        self.retry_limit = kwargs['options'].retry_limit
        self.retry_interval = kwargs['options'].retry_interval
        self.reconnect_retry_limit = kwargs['options'].reconnect_retry_limit

        super(TestRunnerClient, self).__init__(*args, **kwargs)

    def discover(self):
        finished = False
        first_connect = True
        while not finished:
            class_path, methods, finished = self.get_next_tests(
                retry_limit=(self.retry_limit if first_connect else self.reconnect_retry_limit),
                retry_interval=self.retry_interval,
            )
            first_connect = False
            if class_path and methods:
                module_path, _, class_name = class_path.partition(' ')

                klass = test_discovery.import_test_class(module_path, class_name)
                yield klass(name_overrides=methods)

    def get_next_tests(self, retry_interval=2, retry_limit=0):
        try:
            if self.revision:
                url = 'http://%s/tests?runner=%s&revision=%s' % (self.connect_addr, self.runner_id, self.revision)
            else:
                url = 'http://%s/tests?runner=%s' % (self.connect_addr, self.runner_id)
            response = urllib2.urlopen(url)
            d = json.load(response)
            return (d.get('class'), d.get('methods'), d['finished'])
        except urllib2.HTTPError, e:
            logging.warning("Got HTTP status %d when requesting tests -- bailing" % (e.code))
            return None, None, True
        except urllib2.URLError, e:
            if retry_limit > 0:
                logging.warning("Got error %r when requesting tests, retrying %d more times." % (e, retry_limit))
                time.sleep(retry_interval)
                return self.get_next_tests(retry_limit=retry_limit-1, retry_interval=retry_interval)
            else:
                return None, None, True # Stop trying if we can't connect to the server.

########NEW FILE########
__FILENAME__ = test_runner_json_replay
try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json

import sys


from test_runner import TestRunner

class TestRunnerJSONReplay(TestRunner):
    """A fake test runner that loads a one-dict-per-line JSON file and sends each dict to the test reporters."""
    def __init__(self, *args, **kwargs):
        self.replay_json = kwargs.pop('replay_json')
        self.replay_json_inline = kwargs.pop('replay_json_inline')

        self.results = self.loadlines()

        super(TestRunnerJSONReplay, self).__init__(*args, **kwargs)

    def discover(self):
        """No-op because this class runs no tests"""
        pass

    def run(self):
        """Replays the results given.
        Reports the test counts, each test result, and calls .report() for all test reporters."""
        test_cases = set()
        test_methods = set()

        for result in self.results:
            test_cases.add((result['method']['module'], result['method']['class'],))
            test_methods.add((result['method']['module'], result['method']['class'], result['method']['name'],))

        for reporter in self.test_reporters:
            reporter.test_counts(len(test_cases), len(test_methods))

        for result in self.results:
            for reporter in self.test_reporters:
                reporter.test_start(result)
                reporter.test_complete(result)

        report = [reporter.report() for reporter in self.test_reporters]
        return all(report)

    def loadlines(self):
        lines = []
        if self.replay_json_inline:
            lines.extend(self.replay_json_inline)

        if self.replay_json:
            f = open(self.replay_json)
            lines.extend(f.readlines())
        else:
            lines.append("RUN COMPLETE")

        assert lines, "No JSON data found."

        results = []
        for line in lines:
            if line.strip() == "RUN COMPLETE":
                continue
            try:
                results.append(json.loads(line.strip()))
            except:
                sys.exit("Invalid JSON line: %r" % line.strip())

        if lines[-1].strip() != "RUN COMPLETE":
            sys.exit("Incomplete run detected")

        return results
########NEW FILE########
__FILENAME__ = test_runner_server
"""
Client-server setup to evenly distribute tests across multiple processes. The server
discovers all test classes and enqueues them, then clients connect to the server,
receive tests to run, and send back their results.

The server keeps track of the overall status of the run and manages timeouts and retries.
"""

from __future__ import with_statement

import logging

from test_fixtures import FIXTURES_WHICH_CAN_RETURN_UNEXPECTED_RESULTS
from test_runner import TestRunner
import tornado.httpserver
import tornado.ioloop
import tornado.web

_log = logging.getLogger('testify')

try:
    import simplejson as json
    _hush_pyflakes = [json]
    del _hush_pyflakes
except ImportError:
    import json
import logging

import Queue
import time

class AsyncDelayedQueue(object):
    def __init__(self):
        self.data_queue = Queue.PriorityQueue()
        self.callback_queue = Queue.PriorityQueue()
        self.finalized = False

    def get(self, c_priority, callback, runner=None):
        """Queue up a callback to receive a test."""
        if self.finalized:
            callback(None, None)
            return

        self.callback_queue.put((c_priority, callback, runner))
        tornado.ioloop.IOLoop.instance().add_callback(self.match)

    def put(self, d_priority, data):
        """Queue up a test to get given to a callback."""
        self.data_queue.put((d_priority, data))
        tornado.ioloop.IOLoop.instance().add_callback(self.match)

    def match(self):
        """Try to pair a test to a callback.

        This loops over each queued callback (and each queued test)
        trying to find a match. It breaks out of the loop as soon as
        it finds a valid callback-test match, re-queueing anything it
        skipped. (In the worst case, this is O(n^2), but most of the
        time no loop iterations beyond the first will be necessary -
        the vast majority of the time, the first callback will match
        the first test).
        """

        callback = None
        runner = None
        data = None

        skipped_callbacks = []
        while callback is None:

            try:
                c_priority, callback, runner = self.callback_queue.get_nowait()
            except Queue.Empty:
                break

            skipped_tests = []
            while data is None:
                try:
                    d_priority, data = self.data_queue.get_nowait()
                except Queue.Empty:
                    break

                if runner is not None and data.get('last_runner') == runner:
                    skipped_tests.append((d_priority, data))
                    data = None
                    continue

            for skipped in skipped_tests:
                self.data_queue.put(skipped)

            if data is None:
                skipped_callbacks.append((c_priority, callback, runner))
                callback = None
                continue

        for skipped in skipped_callbacks:
            self.callback_queue.put(skipped)

        if callback is not None:
            callback(d_priority, data)
            tornado.ioloop.IOLoop.instance().add_callback(self.match)

    def empty(self):
        """Returns whether or not we have any pending tests."""
        return self.data_queue.empty()

    def waiting(self):
        """Returns whether or not we have any pending callbacks."""
        return self.callback_queue.empty()

    def finalize(self):
        """Immediately call any pending callbacks with None,None
        and ensure that any future get() calls do the same."""
        self.finalized = True
        try:
            while True:
                _, callback, _ = self.callback_queue.get_nowait()
                callback(None, None)
        except Queue.Empty:
            pass

class TestRunnerServer(TestRunner):
    def __init__(self, *args, **kwargs):
        self.serve_port = kwargs.pop('serve_port')
        self.runner_timeout = kwargs['options'].runner_timeout
        self.revision = kwargs['options'].revision
        self.server_timeout = kwargs['options'].server_timeout
        self.shutdown_delay_for_connection_close = kwargs['options'].shutdown_delay_for_connection_close
        self.shutdown_delay_for_outstanding_runners = kwargs['options'].shutdown_delay_for_outstanding_runners
        self.disable_requeueing = kwargs['options'].disable_requeueing

        self.test_queue = AsyncDelayedQueue()
        self.checked_out = {} # Keyed on class path (module class).
        self.failed_rerun_methods = set() # Set of (class_path, method) who have failed.
        self.timeout_rerun_methods = set() # Set of (class_path, method) who were sent to a client but results never came.
        self.previous_run_results = {} # Keyed on (class_path, method), values are result dictionaries.
        self.runners = set() # The set of runner_ids who have asked for tests.
        self.runners_outstanding = set() # The set of runners who have posted results but haven't asked for the next test yet.
        self.shutting_down = False # Whether shutdown() has been called.

        super(TestRunnerServer, self).__init__(*args, **kwargs)

    def get_next_test(self, runner_id, on_test_callback, on_empty_callback):
        """Enqueue a callback (which should take one argument, a test_dict) to be called when the next test is available."""

        self.runners.add(runner_id)

        def callback(priority, test_dict):
            if not test_dict:
                return on_empty_callback()

            if test_dict.get('last_runner', None) != runner_id or (self.test_queue.empty() and len(self.runners) <= 1):
                self.check_out_class(runner_id, test_dict)
                on_test_callback(test_dict)
            else:
                if self.test_queue.empty():
                    # Put the test back in the queue, and queue ourselves to pick up the next test queued.
                    self.test_queue.put(priority, test_dict)
                    self.test_queue.callback_queue.put((-1, callback))
                else:
                    # Get the next test, process it, then place the old test back in the queue.
                    self.test_queue.get(0, callback, runner=runner_id)
                    self.test_queue.put(priority, test_dict)

        self.test_queue.get(0, callback, runner=runner_id)

    def report_result(self, runner_id, result):
        class_path = '%s %s' % (result['method']['module'], result['method']['class'])
        d = self.checked_out.get(class_path)

        if not d:
            raise ValueError("Class %s not checked out." % class_path)
        if d['runner'] != runner_id:
            raise ValueError("Class %s checked out by runner %s, not %s" % (class_path, d['runner'], runner_id))
        if result['method']['name'] not in d['methods']:
            # If class_teardown failed, the client will send us a result to let us
            # know. If that happens, don't worry about the apparently un-checked
            # out test method.
            if result['method']['fixture_type'] in FIXTURES_WHICH_CAN_RETURN_UNEXPECTED_RESULTS:
                pass
            else:
                raise ValueError("Method %s not checked out by runner %s." % (result['method']['name'], runner_id))

        self.activity()

        if result['success']:
            d['passed_methods'][result['method']['name']] = result
        else:
            d['failed_methods'][result['method']['name']] = result
            self.failure_count += 1
            if self.failure_limit and self.failure_count >= self.failure_limit:
                logging.error('Too many failures, shutting down.')
                return self.early_shutdown()

        d['timeout_time'] = time.time() + self.runner_timeout

        # class_teardowns are special.
        if result['method']['fixture_type'] not in FIXTURES_WHICH_CAN_RETURN_UNEXPECTED_RESULTS:
            d['methods'].remove(result['method']['name'])

        if not d['methods']:
            self.check_in_class(runner_id, class_path, finished=True)

    def run(self):
        class TestsHandler(tornado.web.RequestHandler):
            @tornado.web.asynchronous
            def get(handler):
                runner_id = handler.get_argument('runner')

                if self.shutting_down:
                    self.runners_outstanding.discard(runner_id)
                    return handler.finish(json.dumps({
                        'finished': True,
                    }))

                if self.revision and self.revision != handler.get_argument('revision'):
                    return handler.send_error(409, reason="Incorrect revision %s -- server is running revision %s" % (handler.get_argument('revision'), self.revision))

                def callback(test_dict):
                    self.runners_outstanding.discard(runner_id)
                    handler.finish(json.dumps({
                        'class': test_dict['class_path'],
                        'methods': test_dict['methods'],
                        'finished': False,
                    }))

                def empty_callback():
                    self.runners_outstanding.discard(runner_id)
                    handler.finish(json.dumps({
                        'finished': True,
                    }))

                self.get_next_test(runner_id, callback, empty_callback)

            def finish(handler, *args, **kwargs):
                super(TestsHandler, handler).finish(*args, **kwargs)
                tornado.ioloop.IOLoop.instance().add_callback(handler.after_finish)

            def after_finish(handler):
                if self.shutting_down and not self.runners_outstanding:
                    iol = tornado.ioloop.IOLoop.instance()
                    iol.add_callback(iol.stop)

        class ResultsHandler(tornado.web.RequestHandler):
            def post(handler):
                runner_id = handler.get_argument('runner')
                self.runners_outstanding.add(runner_id)
                result = json.loads(handler.request.body)

                try:
                    self.report_result(runner_id, result)
                except ValueError, e:
                    return handler.send_error(409, reason=str(e))

                return handler.finish("kthx")

            def get_error_html(handler, status_code, **kwargs):
                reason = kwargs.pop('reason', None)
                if reason:
                    return reason
                else:
                    return super(ResultsHandler, handler).get_error_html(status_code, **kwargs)

        try:
            # Enqueue all of our tests.
            discovered_tests = []
            try:
                discovered_tests = self.discover()
            except Exception, exc:
                _log.debug("Test discovery blew up!: %r" % exc)
                raise
            for test_instance in discovered_tests:
                test_dict = {
                    'class_path' : '%s %s' % (test_instance.__module__, test_instance.__class__.__name__),
                    'methods' : [test.__name__ for test in test_instance.runnable_test_methods()],
                }

                if test_dict['methods']:
                    # When the client has finished running the entire TestCase,
                    # it will signal us by sending back a result with method
                    # name 'run'. Add this result to the list we expect to get
                    # back from the client.
                    test_dict['methods'].append('run')
                    self.test_queue.put(0, test_dict)

            # Start an HTTP server.
            application = tornado.web.Application([
                (r"/tests", TestsHandler),
                (r"/results", ResultsHandler),
            ])

            server = tornado.httpserver.HTTPServer(application)
            server.listen(self.serve_port)

            def timeout_server():
                if time.time() > self.last_activity_time + self.server_timeout:
                    logging.error('No client activity for %ss, shutting down.' % self.server_timeout)
                    self.shutdown()
                else:
                    tornado.ioloop.IOLoop.instance().add_timeout(self.last_activity_time + self.server_timeout, timeout_server)
            self.activity()
            timeout_server() # Set the first callback.

            tornado.ioloop.IOLoop.instance().start()

        finally:
            # Report what happened, even if something went wrong.
            report = [reporter.report() for reporter in self.test_reporters]
            return all(report)


    def activity(self):
        self.last_activity_time = time.time()

    def check_out_class(self, runner, test_dict):
        self.activity()

        self.checked_out[test_dict['class_path']] = {
            'runner' : runner,
            'class_path' : test_dict['class_path'],
            'methods' : set(test_dict['methods']),
            'failed_methods' : {},
            'passed_methods' : {},
            'start_time' : time.time(),
            'timeout_time' : time.time() + self.runner_timeout,
        }

        self.timeout_class(runner, test_dict['class_path'])

    def check_in_class(self, runner, class_path, timed_out=False, finished=False, early_shutdown=False):
        if not timed_out:
            self.activity()

        if 1 != len([opt for opt in (timed_out, finished, early_shutdown) if opt]):
            raise ValueError("Must set exactly one of timed_out, finished, or early_shutdown.")

        if class_path not in self.checked_out:
            raise ValueError("Class path %r not checked out." % class_path)
        if not early_shutdown and self.checked_out[class_path]['runner'] != runner:
            raise ValueError("Class path %r not checked out by runner %r." % (class_path, runner))

        d = self.checked_out.pop(class_path)

        passed_methods = list(d['passed_methods'].items())
        failed_methods = list(d['failed_methods'].items())
        tests_to_report = passed_methods[:]
        requeue_methods = []

        for method, result in failed_methods:
            if self.disable_requeueing == True:
                # If requeueing is disabled we'll report failed methods immediately.
                tests_to_report.append((method, result))

            else:
                if (class_path, method) in self.failed_rerun_methods:
                    # failed methods already rerun, no need to requeue.
                    tests_to_report.append((method, result))

                elif result['method']['fixture_type'] in FIXTURES_WHICH_CAN_RETURN_UNEXPECTED_RESULTS:
                    # Unexpexpected fixture failures, we'll report but no need to requeue.
                    tests_to_report.append((method, result))

                elif early_shutdown:
                    # Server is shutting down. Just report the failure, no need to requeue.
                    tests_to_report.append((method, result))

                else:
                    # Otherwise requeue the method to be run on a different builder.
                    requeue_methods.append((method, result))

        for method, result_dict in tests_to_report:
            for reporter in self.test_reporters:
                result_dict['previous_run'] = self.previous_run_results.get((class_path, method), None)
                reporter.test_start(result_dict)
                reporter.test_complete(result_dict)

        # Requeue failed tests
        requeue_dict = {
            'last_runner' : runner,
            'class_path' : d['class_path'],
            'methods' : [],
        }

        for method, result_dict in requeue_methods:
            requeue_dict['methods'].append(method)
            self.failed_rerun_methods.add((class_path, method))
            result_dict['previous_run'] = self.previous_run_results.get((class_path, method), None)
            self.previous_run_results[(class_path, method)] = result_dict

        if requeue_dict['methods']:
            # When the client has finished running the entire TestCase,
            # it will signal us by sending back a result with method
            # name 'run'. Add this result to the list we expect to get
            # back from the client.
            requeue_dict['methods'].append('run')

        if finished:
            if len(d['methods']) != 0:
                raise ValueError("check_in_class called with finished=True but this class (%s) still has %d methods without results." % (class_path, len(d['methods'])))
        elif timed_out:
            # Requeue or report timed-out tests.

            for method in d['methods']:
                # Fake the results dict.
                module, _, classname = class_path.partition(' ')
                result_dict = self._fake_result(class_path, method, runner)

                if (class_path, method) not in self.timeout_rerun_methods and self.disable_requeueing != True:
                    requeue_dict['methods'].append(method)
                    self.timeout_rerun_methods.add((class_path, method))
                    self.previous_run_results[(class_path, method)] = result_dict
                else:
                    for reporter in self.test_reporters:
                        reporter.test_start(result_dict)
                        reporter.test_complete(result_dict)

        if requeue_dict['methods']:
            self.test_queue.put(-1, requeue_dict)

        if self.test_queue.empty() and len(self.checked_out) == 0:
            self.shutdown()

    def _fake_result(self, class_path, method, runner):
        error_message = "The runner running this method (%s) didn't respond within %ss.\n" % (runner, self.runner_timeout)
        module, _, classname = class_path.partition(' ')

        return {
            'previous_run' : self.previous_run_results.get((class_path, method), None),
            'start_time' : time.time()-self.runner_timeout,
            'end_time' : time.time(),
            'run_time' : float(self.runner_timeout),
            'normalized_run_time' : "%.2fs" % (self.runner_timeout),
            'complete': True, # We've tried running the test.
            'success' : False,
            'failure' : None,
            'error' : True,
            'interrupted' : None,
            'exception_info' : error_message,
            'exception_info_pretty' : error_message,
            'exception_only' : error_message,
            'runner_id' : runner,
            'method' : {
                'module' : module,
                'class' : classname,
                'name' : method,
                'full_name' : "%s.%s" % (class_path, method),
                'fixture_type' : None,
            }
        }

    def timeout_class(self, runner, class_path):
        """Check that it's actually time to rerun this class; if not, reset the timeout. Check the class in and rerun it."""
        d = self.checked_out.get(class_path, None)

        if not d:
            return

        if time.time() < d['timeout_time']:
            # We're being called for the first time, or someone has updated timeout_time since the timeout was set (e.g. results came in)
            tornado.ioloop.IOLoop.instance().add_timeout(d['timeout_time'], lambda: self.timeout_class(runner, class_path))
            return

        try:
            self.check_in_class(runner, class_path, timed_out=True)
        except ValueError:
            # If another builder has checked out the same class in the mean time, don't throw an error.
            pass

    def early_shutdown(self):
        for class_path in self.checked_out.keys():
            self.check_in_class(None, class_path, early_shutdown=True)
        self.shutdown()

    def shutdown(self):
        if self.shutting_down:
            # Try not to shut down twice.
            return

        self.shutting_down = True
        self.test_queue.finalize()
        iol = tornado.ioloop.IOLoop.instance()
        # Can't immediately call stop, otherwise the runner currently POSTing its results will get a Connection Refused when it tries to ask for the next test.

        # Without this check, we could end up queueing a stop() call on a
        # tornado server we spin up later, causing it to hang mysteriously.
        if iol.running():
            if self.runners_outstanding:
                # Stop in 5 seconds if all the runners_outstanding don't come back by then.
                iol.add_timeout(time.time()+self.shutdown_delay_for_outstanding_runners, iol.stop)
            else:
                # Give tornado enough time to finish writing to all the clients, then shut down.
                iol.add_timeout(time.time()+self.shutdown_delay_for_connection_close, iol.stop)
        else:
            _log.error("TestRunnerServer on port %s has been asked to shutdown but its IOLoop is not running."
                " Perhaps it died an early death due to discovery failure." % self.serve_port
            )

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = class_logger
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging

class ClassLogger(object):
    """Descriptor that returns a logger for a class named module.class
        
    Expected Usage:
        class MyClass(object):
            ...
            log = ClassLogger() 

            def my_method(self):
                self.log.debug('some debug message') 
                # should log something like: mymodule.MyClass 'some debug message'
    """

    def __get__(self, obj, obj_type=None):
        object_class = obj_type or obj.__class__
        name = 'testify.%s.%s' % (object_class.__module__, object_class.__name__)
        return logging.getLogger(name)

########NEW FILE########
__FILENAME__ = code_coverage
#!/usr/local/bin/python

__author__="lenza"
__date__ ="$May 25, 2009"

"""This is a module for gathing code coverage information.
Use coverage.start() to begin collecting information, and coverage.stop() to end collection.
See https://trac.yelpcorp.com/wiki/TestingCoverage for more information
"""

import sys

class FakeCoverage:
    warning_printed = False

    @classmethod
    def start(cls):
        if not cls.warning_printed:
            print >>sys.stderr, "*** WARNING: To gather coverage information you must install the Python coverage package."
            print >>sys.stderr, "See: http://pypi.python.org/pypi/coverage/"
            cls.warning_printed = True

    @staticmethod
    def stop(): pass

    @staticmethod
    def save(): pass

try:
    import coverage
    _hush_pyflakes = [coverage]
    del _hush_pyflakes
except (ImportError, NameError), ex:
    coverage = None

started = False
coverage_instance = None

def start(testcase_name = None):
    global started
    global coverage_instance
    assert not started
    if coverage is not None:
        coverage_instance = coverage.coverage(data_file="coverage_file.", data_suffix=testcase_name, auto_data=True)
    else:
        coverage_instance = FakeCoverage()

    coverage_instance.start()
    started = True

def stop():
    global started
    global coverage_instance
    assert started
    coverage_instance.stop()
    coverage_instance.save()
    started = False

if __name__ == "__main__":
    if coverage is None:
        print """You must install the Python coverage 3.0.b3 package to use coverage.\nhttp://pypi.python.org/pypi/coverage/"""
        quit()

    if len(sys.argv) < 2:
        print "Usage: python code_coverage.py output_directory <diff>"
        quit()

    if len(sys.argv) > 2:
        diff_file = sys.argv[2]
    else:
        diff_file = None

    directory = sys.argv[1]
    coverage_instance = coverage.coverage(data_file="coverage_file.", auto_data=True)
    coverage_instance.exclude("^import")
    coverage_instance.exclude("from.*import")
    coverage_instance.combine()
    if diff_file is None:
        coverage_instance.html_report(morfs=None, directory=directory, ignore_errors=False, omit_prefixes=None)
    else:
        coverage_instance.svnhtml_report(morfs=None, directory=directory, ignore_errors=False, omit_prefixes=None, filename=diff_file)

    #coverage_result = coverage_entry_point()
    #sys.exit(coverage_result)


########NEW FILE########
__FILENAME__ = exception
"""Helper methods for formatting and manipulating tracebacks"""
import traceback

def format_exception_info(exception_info_tuple, formatter=None):
    if formatter is None:
        formatter = traceback.format_exception
        
    exctype, value, tb = exception_info_tuple
    # Skip test runner traceback levels
    while tb and is_relevant_tb_level(tb):
        tb = tb.tb_next
    if exctype is AssertionError:
        # Skip testify.assertions traceback levels
        length = count_relevant_tb_levels(tb)
        return formatter(exctype, value, tb, length)

    if not tb:
        return "Exception: %r (%r)" % (exctype, value)

    return formatter(exctype, value, tb)

def is_relevant_tb_level(tb):
    return tb.tb_frame.f_globals.has_key('__testify')

def count_relevant_tb_levels(tb):
    length = 0
    while tb and not is_relevant_tb_level(tb):
        length += 1
        tb = tb.tb_next
    return length

########NEW FILE########
__FILENAME__ = inspection
# Copyright 2012 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helpers for dealing with class and method introspection.

In particular, these functions help to remedy differences in behavior between
Python 2.6.x and 2.7.3+ when getting/setting attributes on instancemethods.

Attributes can be freely set on functions, but not instancemethods. Because we
juggle methods and functions often interchangably, these produce the desired
effect of setting (or getting) the attribute on the function regardless of our
callable's type.
"""

import inspect
import types


def callable_hasattr(callable_, attr_name):
    function = get_function(callable_)
    return hasattr(function, attr_name)

def callable_setattr(callable_, attr_name, attr_value):
    function = get_function(callable_)
    setattr(function, attr_name, attr_value)

def get_function(callable_):
    """If given a method, returns its function object; otherwise a no-op."""
    if isinstance(callable_, types.MethodType):
        return callable_.im_func
    return callable_

def is_fixture_method(callable_):
    """Whether Testify has decorated this callable as a test fixture."""
    # ensure we don't pick up turtles/mocks as fixtures
    if not inspect.isroutine(callable_):
        return False

    # _fixture_id indicates this method was tagged by us as a fixture
    return callable_hasattr(callable_, '_fixture_type')


########NEW FILE########
__FILENAME__ = mock_logging
"""
Provides the mock_logging context manager.
"""

import itertools
import logging
from contextlib import contextmanager
from testify import assert_any_match_regex
from testify import assert_all_not_match_regex


class MockHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        # logging.Handler is old-style in 2.6
        logging.Handler.__init__(self, *args, **kwargs)
        self.buf = {}

    @contextmanager
    def assert_logs(self, levels=None, log_regex=".*"):
        """Asserts that the given block will log some messages.

        Args:
          levels -- log level to look for. By default, look at all levels
          log_regex -- regex matching a particular log message to look for. By default,
            any message will match.
        """
        self.clear()
        yield
        self.assert_logged(levels, log_regex)

    def assert_logged(self, levels=None, log_regex=".*"):
        """Asserts that the mock hander did log some messages.

        Args:
          levels -- log level to look for. By default, look at all levels
          log_regex -- regex matching a particular log message to look for. By default,
            any message will match.
        """
        if levels:
            for level in levels:
                assert level in self.buf, 'expected something to be logged in level %r' % level
                assert_any_match_regex(log_regex, self.buf[level])
        else:
            assert self.buf, 'expected something to be logged'
            assert_any_match_regex(log_regex, itertools.chain.from_iterable(self.buf.values()))

    @contextmanager
    def assert_does_not_log(self, levels=None, log_regex=".*"):
        """Asserts that the given block will not log some messages.

        Args:
          levels -- log level to look for. By default, look at all levels
          log_regex -- regex matching a particular log message to look for. By default,
            any message will match.
        """
        self.clear()
        yield
        self.assert_did_not_log(levels, log_regex)

    def assert_did_not_log(self, levels=None, log_regex=".*"):
        """Asserts that the mock handler did not log some messages.

        Args:
          levels -- log level to look for. By default, look at all levels
          log_regex -- regex matching a particular log message to look for. By default,
            any message will match.
        """
        if self.buf is None:
            return
        if levels:
            for level in levels:
                if level in self.buf:
                    assert_all_not_match_regex(log_regex, self.buf[level])
        else:
            assert_all_not_match_regex(log_regex, itertools.chain.from_iterable(self.buf.values()))

    def clear(self):
        """Clear all logged messages.
        """
        self.buf.clear()

    def get(self, level):
        """Get all messages logged for a certain level.
        Returns a list of messages for the given level.
        """
        return self.buf.get(level)

    def emit(self, record):
        """Handles emit calls from logging, stores the logged record in an internal list that is
        accessible via MockHandler.get.
        """
        msg = self.format(record)
        self.buf.setdefault(record.levelno, [])
        self.buf[record.levelno].append(msg)


@contextmanager
def mock_logging(logger_names=[]):
    """Mocks out logging inside the context manager. If a logger name is
    provided, will only mock out that logger. Otherwise, mocks out the root
    logger.

    Not threadsafe.

    Yields a MockHandler object.

    Example;

        with mock_logging() as mock_handler:
            logging.info("event")
            assert_equal(["event"], mock_handler.get(logging.INFO))


        with mock_logging(['subsystem']) as mock_handler:
            logging.getLogger('subsystem').info("event")
            assert_equal(["event"], mock_handler.get(logging.INFO))

    """
    if logger_names:
        queue = [logging.getLogger(logger_name) for logger_name in logger_names]
    else:
        queue = [logging.getLogger('')]
    new_handler = MockHandler()
    previous_handlers = {}
    previous_propagates = {}
    for logger in queue:
        previous_handlers[logger] = logger.handlers[:]
        previous_propagates[logger] = logger.propagate
        logger.handlers = [new_handler]
        logger.propagate = 0
    yield new_handler
    for logger in queue:
        logger.handlers = previous_handlers[logger]
        logger.propagate = previous_propagates[logger]

########NEW FILE########
__FILENAME__ = stringdiffer
"""
Inter-line differ, for readable diffs in test assertion failure messages.

Based around a differ borrowed from Review Board.
"""
from difflib import SequenceMatcher


LEFT_HIGHLIGHT_CHARACTER = '<'
RIGHT_HIGHLIGHT_CHARACTER = '>'


# Borrowed from
# https://github.com/reviewboard/reviewboard/blob/master/reviewboard/diffviewer/diffutils.py
def get_line_changed_regions(oldline, newline):
    if oldline is None or newline is None:
        return (None, None)

    # Use the SequenceMatcher directly. It seems to give us better results
    # for this. We should investigate steps to move to the new differ.
    differ = SequenceMatcher(None, oldline, newline)

    # This thresholds our results -- we don't want to show inter-line diffs if
    # most of the line has changed, unless those lines are very short.

    # FIXME: just a plain, linear threshold is pretty crummy here.  Short
    # changes in a short line get lost.  I haven't yet thought of a fancy
    # nonlinear test.
    if differ.ratio() < 0.6:
        return (None, None)

    oldchanges = []
    newchanges = []
    back = (0, 0)

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == "equal":
            if ((i2 - i1 < 3) or (j2 - j1 < 3)) and (i1, j1) != (0, 0):
                back = (j2 - j1, i2 - i1)
            continue

        oldstart, oldend = i1 - back[0], i2
        newstart, newend = j1 - back[1], j2

        if oldchanges != [] and oldstart <= oldchanges[-1][1] < oldend:
            oldchanges[-1] = (oldchanges[-1][0], oldend)
        elif not oldline[oldstart:oldend].isspace():
            oldchanges.append((oldstart, oldend))

        if newchanges != [] and newstart <= newchanges[-1][1] < newend:
            newchanges[-1] = (newchanges[-1][0], newend)
        elif not newline[newstart:newend].isspace():
            newchanges.append((newstart, newend))

        back = (0, 0)

    return (oldchanges, newchanges)


def highlight_regions(string, regions):
    """Given `string` and `regions` (a list of (beginning index, end index)
    tuples), return `string` marked up to highlight those regions.

    >>> highlight_regions('This is a string.', [(0, 3), (8, 9)])
    '<Thi>s is <a> string.'
    """
    string = list(string)
    # Inserting into the middle of a list shifts all the elements over by one.
    # Each time a markup element is added, increase a result string's insertion
    # offset.
    offset = 0

    for beginning, end in sorted(regions or []):
        string.insert(offset + beginning, LEFT_HIGHLIGHT_CHARACTER)
        offset +=1
        string.insert(offset + end, RIGHT_HIGHLIGHT_CHARACTER)
        offset +=1

    return ''.join(string)


# no namedtuple in Python 2.5; here is a simple imitation
# HighlightedDiff = collections.namedtuple('HighlightedDiff', 'old new')
class HighlightedDiff(tuple):

    def __new__(cls, old, new):
        return tuple.__new__(cls, (old, new))

    __slots__ = ()  # no attributes allowed

    @property
    def old(self):
        return self[0]

    @property
    def new(self):
        return self[1]

    def __repr__(self):
        return '%s(old=%r, new=%r)' % (self.__class__.__name__, self.old, self.new)


def highlight(old, new):
    """Given two strings, return a `HighlightedDiff` containing the strings
    with markup identifying the parts that changed.

    >>> highlight('Testify is great.', 'testify is gr8')
    HighlightedDiff(old='<T>estify is gr<eat.>', new='<t>estify is gr<8>')
    """
    oldchanges, newchanges = get_line_changed_regions(old, new)
    return HighlightedDiff(highlight_regions(old, oldchanges),
                           highlight_regions(new, newchanges))
# vim:et:sts=4:sw=4:

########NEW FILE########
__FILENAME__ = turtle
# Copyright 2009 Yelp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Mocking and Stubbing framework

This framework is built around the 'Turtle' object. A Turtle object returns another turtle for every 
unknown (not predefined) attributed asked for. It is also callable, returning (of course) a turtle.

After a turtle is used, it can be inspected to find out what happened:

  >>> leonardo = Turtle()
  >>> leonardo.color = "blue"
  >>> leonardo.attack(weapon="katanas") #doctest:+ELLIPSIS
  <testify.utils.turtle.Turtle object at 0x...>

  >>> len(leonardo.defend)
  0

  >>> len(leonardo.attack)
  1

  >>> leonardo.attack.calls
  [((), {'weapon': 'katanas'})]

  >>> for args, kwargs in leonardo.attack:
  ...     print kwargs.get('weapon')
  katanas

To control the behavior of a turtle (for example, if you want some function call to return False instead)
just set the attribute yourself

  >>> raphael = Turtle(color="red")
  >>> raphael.is_shell_shocked = lambda : False

Then you can call:
  >>> if not raphael.is_shell_shocked():
  ...     print raphael.color
  red

"Turtles all the way down": http://en.wikipedia.org/wiki/Turtles_all_the_way_down
"""

class Turtle(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

        self.calls = []
        self.returns = []

    def __iter__(self):
        return iter(self.calls)

    def __len__(self):
        return len(self.calls)

    def __nonzero__(self):
        return True

    def __getattr__(self, name):
        self.__dict__[name] = Turtle()
        return self.__dict__[name]

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        new_turtle = type(self)()
        self.returns.append(new_turtle)
        return new_turtle


########NEW FILE########
__FILENAME__ = example_test

from testify import TestCase, run


class ExampleTestCase(TestCase):

    def test_one(self):
        pass

    def test_two(self):
        pass


class SecondTestCase(TestCase):

    def test_one(self):
      pass


if __name__ == "__main__":
    run()

########NEW FILE########
