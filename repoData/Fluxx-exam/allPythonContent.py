__FILENAME__ = asserts
from functools import partial
from operator import eq, ne


IRRELEVANT = object()


class ChangeWatcher(object):

    POSTCONDITION_FAILURE_MESSAGE = {
        ne: 'Value did not change',
        eq: 'Value changed from {before} to {after}',
        'invalid': 'Value changed to {after}, not {expected_after}'
    }

    def __init__(self, comparator, check, *args, **kwargs):
        self.check = check
        self.comparator = comparator

        self.args = args
        self.kwargs = kwargs

        self.expected_before = kwargs.pop('before', IRRELEVANT)
        self.expected_after = kwargs.pop('after', IRRELEVANT)

    def __enter__(self):
        self.before = self.__apply()

        if not self.expected_before is IRRELEVANT:
            check = self.comparator(self.before, self.expected_before)
            message = "Value before is {before}, not {expected_before}"

            assert not check, message.format(**vars(self))

    def __exit__(self, exec_type, exec_value, traceback):
        if exec_type is not None:
            return False  # reraises original exception

        self.after = self.__apply()

        met_precondition = self.comparator(self.before, self.after)
        after_value_matches = self.after == self.expected_after

        # Changed when it wasn't supposed to, or, didn't change when it was
        if not met_precondition:
            self.__raise_postcondition_error(self.comparator)
        # Do care about the after value, but it wasn't equal
        elif self.expected_after is not IRRELEVANT and not after_value_matches:
            self.__raise_postcondition_error('invalid')

    def __apply(self):
        return self.check(*self.args, **self.kwargs)

    def __raise_postcondition_error(self, key):
        message = self.POSTCONDITION_FAILURE_MESSAGE[key]
        raise AssertionError(message.format(**vars(self)))


class AssertsMixin(object):
    assertChanges = partial(ChangeWatcher, ne)
    assertDoesNotChange = partial(
        ChangeWatcher,
        eq,
        before=IRRELEVANT,
        after=IRRELEVANT
    )

########NEW FILE########
__FILENAME__ = cases
from __future__ import absolute_import

from exam.decorators import before, after, around, patcher  # NOQA
from exam.objects import noop  # NOQA
from exam.asserts import AssertsMixin

import inspect


class MultipleGeneratorsContextManager(object):

    def __init__(self, *generators):
        self.generators = generators

    def __enter__(self, *args, **kwargs):
        [next(g) for g in self.generators]

    def __exit__(self, *args, **kwargs):
        for generator in reversed(self.generators):
            try:
                next(generator)
            except StopIteration:
                pass


class Exam(AssertsMixin):

    @before
    def __setup_patchers(self):
        for attr, patchr in self.__attrs_of_type(patcher):
            patch_object = patchr.build_patch(self)
            setattr(self, attr, patch_object.start())
            self.addCleanup(patch_object.stop)

    def __attrs_of_type(self, kind):
        for base in reversed(inspect.getmro(type(self))):
            for attr, class_value in vars(base).items():
                resolved_value = getattr(type(self), attr, False)

                if type(resolved_value) is not kind:
                    continue
                # If the attribute inside of this base is not the exact same
                # value as the one in type(self), that means that it's been
                # overwritten somewhere down the line and we shall skip it
                elif class_value is not resolved_value:
                    continue
                else:
                    yield attr, resolved_value

    def __run_hooks(self, hook):
        for _, value in self.__attrs_of_type(hook):
            value(self)

    def run(self, *args, **kwargs):
        generators = (value(self) for _, value in self.__attrs_of_type(around))
        with MultipleGeneratorsContextManager(*generators):
            self.__run_hooks(before)
            getattr(super(Exam, self), 'run', noop)(*args, **kwargs)
            self.__run_hooks(after)

########NEW FILE########
__FILENAME__ = decorators
from __future__ import absolute_import

from mock import patch
from functools import partial, wraps
import types

import exam.cases


class fixture(object):

    def __init__(self, thing, *args, **kwargs):
        self.thing = thing
        self.args = args
        self.kwargs = kwargs

    def __get__(self, testcase, type=None):
        if not self in testcase.__dict__:
            # If this fixture is not present in the test case's __dict__,
            # freshly apply this fixture and store that in the dict, keyed by
            # self
            application = self.__apply(testcase)(*self.args, **self.kwargs)
            testcase.__dict__[self] = application

        return testcase.__dict__[self]

    def __apply(self, testcase):
        # If self.thing is a method type, it means that the function is already
        # bound to a class and therefore we should treat it just like a normal
        # functuion and return it.
        if type(self.thing) in (type, types.MethodType):
            return self.thing
        # If not, it means that's it's a vanilla function, so either a decorated
        # instance method in the test case body or a lambda.  In either of those
        # cases, it's called with the test case instance (self) to the author.
        else:
            return partial(self.thing, testcase)


class base(object):

    def __init__(self, *things):
        self.init_callables = things

    def __call__(self, instance):
        return self.init_callables[0](instance)


class before(base):

    def __call__(self, thing):
        # There a couple possible situations at this point:
        #
        # If ``thing`` is an instance of a test case, this means that we
        # ``init_callable`` is the function we want to decorate.  As such,
        # simply call that callable with the instance.
        if isinstance(thing, exam.cases.Exam):
            return self.init_callables[0](thing)
        # If ``thing is not an instance of the test case, it means thi before
        # hook was constructed with a callable that we need to run before
        # actually running the decorated function.  It also means that ``thing``
        # is the function we're decorating, so we need to return a callable that
        # accepts a test case instance and, when called, calls the
        # ``init_callable`` first, followed by the actual function we are
        # decorating.
        else:
            @wraps(thing)
            def inner(testcase):
                [f(testcase) for f in self.init_callables]
                thing(testcase)

            return inner


class after(base):
    pass


class around(base):
    pass


class patcher(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.func = None
        self.patch_func = patch

    def __call__(self, func):
        self.func = func
        return self

    def build_patch(self, instance):
        if self.func:
            self.kwargs['new'] = self.func(instance)

        return self.patch_func(*self.args, **self.kwargs)

    @classmethod
    def object(cls, *args, **kwargs):
        instance = cls(*args, **kwargs)
        instance.patch_func = patch.object
        return instance

########NEW FILE########
__FILENAME__ = fixtures
#: A string representation of a 2px square GIF, suitable for use in PIL.
two_px_square_image = (
        'GIF87a\x02\x00\x02\x00\xb3\x00\x00\x00\x00\x00\xff\xff\xff\x00\x00' +
        '\x00\x00\x00\x00\x00\x00\x00\xff\x00\xff\x00\x00\x00\x00\x00\x00' +
        '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
        '\x00\x00\x00\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x02\x00\x02\x00' +
        '\x00\x04\x04\x10\x94\x02"\x00;'
    )

#: A string representation of a 1px square GIF, suitable for use in PIL.
one_px_spacer = (
        'GIF89a\x01\x00\x01\x00\x80\x00\x00\xdb\xdf\xef\x00\x00\x00!\xf9\x04' +
        '\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D' +
        '\x01\x00;'
    )

########NEW FILE########
__FILENAME__ = helpers
from __future__ import absolute_import

import shutil
import os
import functools

from mock import MagicMock, patch, call


def rm_f(path):
    try:
        # Assume it's a directory
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        # Directory delete failed, so it's likely a file
        os.remove(path)


def track(**mocks):
    tracker = MagicMock()

    for name, mocker in mocks.items():
        tracker.attach_mock(mocker, name)

    return tracker


def intercept(obj, methodname, wrapper):
    """
    Wraps an existing method on an object with the provided generator, which
    will be "sent" the value when it yields control.

    ::

        >>> def ensure_primary_key_is_set():
        ...     assert model.pk is None
        ...     saved = yield
        ...     aasert model is saved
        ...     assert model.pk is not None
        ...
        >>> intercept(model, 'save', ensure_primary_key_is_set)
        >>> model.save()

    :param obj: the object that has the method to be wrapped
    :type obj: :class:`object`
    :param methodname: the name of the method that will be wrapped
    :type methodname: :class:`str`
    :param wrapper: the wrapper
    :type wrapper: generator callable
    """
    original = getattr(obj, methodname)

    def replacement(*args, **kwargs):
        wrapfn = wrapper(*args, **kwargs)
        wrapfn.send(None)
        result = original(*args, **kwargs)
        try:
            wrapfn.send(result)
        except StopIteration:
            return result
        else:
            raise AssertionError('Generator did not stop')

    def unwrap():
        """
        Restores the method to it's original (unwrapped) state.
        """
        setattr(obj, methodname, original)

    replacement.unwrap = unwrap

    setattr(obj, methodname, replacement)


class mock_import(patch.dict):

    FROM_X_GET_Y = lambda s, x, y: getattr(x, y)

    def __init__(self, path):
        self.mock = MagicMock()
        self.path = path
        self.modules = {self.base: self.mock}

        for i in range(len(self.remainder)):
            tail_parts = self.remainder[0:i + 1]
            key = '.'.join([self.base] + tail_parts)
            reduction = functools.reduce(self.FROM_X_GET_Y, tail_parts, self.mock)
            self.modules[key] = reduction

        super(mock_import, self).__init__('sys.modules', self.modules)

    @property
    def base(self):
        return self.path.split('.')[0]

    @property
    def remainder(self):
        return self.path.split('.')[1:]

    def __enter__(self):
        super(mock_import, self).__enter__()
        return self.modules[self.path]

    def __call__(self, func):
        super(mock_import, self).__call__(func)

        @functools.wraps(func)
        def inner(*args, **kwargs):
            args = list(args)
            args.insert(1, self.modules[self.path])

            with self:
                func(*args, **kwargs)

        return inner


class effect(list):
    """
    Helper class that is itself callable, whose return values when called are
    configured via the tuples passed in to the constructor. Useful to build
    ``side_effect`` callables for Mock objects.  Raises TypeError if called with
    arguments that it was not configured with:

    >>> from exam.objects import call, effect
    >>> side_effect = effect((call(1), 'with 1'), (call(2), 'with 2'))
    >>> side_effect(1)
    'with 1'
    >>> side_effect(2)
    'with 2'

    Call argument equality is checked via equality (==) of the ``call``` object,
    which is the 0th item of the configuration tuple passed in to the ``effect``
    constructor.  By default, ``call`` objects are just ``mock.call`` objects.

    If you would like to customize this behavior, subclass `effect` and redefine
    your own `call_class` class variable.  I.e.

        class myeffect(effect):
            call_class = my_call_class
    """

    call_class = call

    def __init__(self, *calls):
        """
        :param calls: Two-item tuple containing call and the return value.
        :type calls: :class:`effect.call_class`
        """
        super(effect, self).__init__(calls)

    def __call__(self, *args, **kwargs):
        this_call = self.call_class(*args, **kwargs)

        for call_obj, return_value in self:
            if call_obj == this_call:
                return return_value

        raise TypeError('Unknown effect for: %r, %r' % (args, kwargs))


########NEW FILE########
__FILENAME__ = mock
from __future__ import absolute_import

from mock import Mock as BaseMock
from mock import call


class Mock(BaseMock):

    def assert_called(self):
        assert self.called

    def assert_not_called(self):
        assert not self.called

    def assert_not_called_with(self, *args, **kwargs):
        assert not call(*args, **kwargs) == self.call_args

    def assert_not_called_once_with(self, *args, **kwargs):
        assert len(self.__calls_matching(*args, **kwargs)) is not 1

    def assert_not_any_call(self, *args, **kwargs):
        assert len(self.__calls_matching(*args, **kwargs)) is 0

    def __calls_matching(self, *args, **kwargs):
        calls_match = lambda other_call: call(*args, **kwargs) == other_call
        return list(filter(calls_match, self.call_args_list))

########NEW FILE########
__FILENAME__ = objects
from __future__ import absolute_import


def always(value):
    return lambda *a, **k: value

noop = no_op = always(None)

########NEW FILE########
__FILENAME__ = dummy
#: Module purely exists to test patching things.
thing = True
it = lambda: False


def get_thing():
    global thing
    return thing


def get_it():
    global it
    return it


def get_prop():
    return ThingClass.prop


class ThingClass(object):
    prop = True

########NEW FILE########
__FILENAME__ = test_asserts
from tests import TestCase

from exam import Exam, fixture
from exam.asserts import AssertsMixin


class AssertChangesMixin(Exam, TestCase):

    case = fixture(AssertsMixin)
    thing = fixture(list)

    def no_op_context(self, *args, **kwargs):
        with self.case.assertChanges(len, self.thing, *args, **kwargs):
            pass

    def test_checks_change_on_callable_passed(self):
        with self.case.assertChanges(len, self.thing, before=0, after=1):
            self.thing.append(1)

    def test_after_check_asserts_ends_on_after_value(self):
        self.thing.append(1)
        with self.case.assertChanges(len, self.thing, after=2):
            self.thing.append(1)

    def test_before_check_asserts_starts_on_before_value(self):
        self.thing.append(1)
        with self.case.assertChanges(len, self.thing, before=1):
            self.thing.append(1)
            self.thing.append(2)

    def test_verifies_value_must_change_no_matter_what(self):
        self.thing.append(1)

        with self.assertRaises(AssertionError):
            self.no_op_context(after=1)

        with self.assertRaises(AssertionError):
            self.no_op_context(before=1)

        with self.assertRaises(AssertionError):
            self.no_op_context()

    def test_reraises_exception_if_raised_in_context(self):
        with self.assertRaises(NameError):
            with self.case.assertChanges(len, self.thing, after=5):
                self.thing.append(1)
                undefined_name

    def test_does_not_change_passes_if_no_change_was_made(self):
        with self.assertDoesNotChange(len, self.thing):
            pass

    def test_raises_assertion_error_if_value_changes(self):
        msg = 'Value changed from 0 to 1'
        with self.assertRaisesRegexp(AssertionError, msg):
            with self.assertDoesNotChange(len, self.thing):
                self.thing.append(1)

    def test_assertion_error_mentions_unexpected_result_at_after(self):
        msg = 'Value changed to 1, not 3'
        with self.assertRaisesRegexp(AssertionError, msg):
            with self.assertChanges(len, self.thing, after=3):
                self.thing.append(1)
########NEW FILE########
__FILENAME__ = test_cases
from mock import sentinel
from tests import TestCase

from exam.decorators import before, after, around, patcher
from exam.cases import Exam

from tests.dummy import get_thing, get_it, get_prop, ThingClass


class SimpleTestCase(object):
    """
    Meant to act like a typical unittest.TestCase
    """

    def __init__(self):
        self.cleanups = []
        self.setups = 0
        self.teardowns = 0

    def setUp(self):
        self.setups += 1

    def tearDown(self):
        self.teardowns += 1

    def run(self, *args, **kwargs):
        # At this point in time, exam has run its before hooks and has super'd
        # to the TestCase (us), so, capture the state of calls
        self.calls_before_run = list(self.calls)
        self.vars_when_run = vars(self)

    def addCleanup(self, func):
        self.cleanups.append(func)


class BaseTestCase(Exam, SimpleTestCase):
    """
    Meant to act like a test case a typical user would have.
    """
    def __init__(self, *args, **kwargs):
        self.calls = []
        super(BaseTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        """
        Exists only to prove that adding a setUp method to a test case does not
        break Exam.
        """
        pass

    def tearDown(self):
        """
        Exists only to prove that adding a tearDown method to a test case does
        not break Exam.
        """
        pass


class CaseWithBeforeHook(BaseTestCase):

    @before
    def run_before(self):
        self.calls.append('run before')


class CaseWithDecoratedBeforeHook(BaseTestCase):

    def setup_some_state(self):
        self.state = True

    def setup_some_other_state(self):
        self.other_state = True

    @before(setup_some_state)
    def should_have_run_before(self):
        pass

    @before(setup_some_state, setup_some_other_state)
    def should_have_run_both_states(self):
        pass


class SubclassWithBeforeHook(CaseWithBeforeHook):

    @before
    def subclass_run_before(self):
        self.calls.append('subclass run before')


class CaseWithAfterHook(CaseWithBeforeHook):

    @after
    def run_after(self):
        self.calls.append('run after')


class SubclassCaseWithAfterHook(CaseWithAfterHook):

    @after
    def subclass_run_after(self):
        self.calls.append('subclass run after')


class CaseWithAroundHook(BaseTestCase):

    @around
    def run_around(self):
        self.calls.append('run around before')
        yield
        self.calls.append('run around after')


class SubclassCaseWithAroundHook(BaseTestCase):

    @around
    def subclass_run_around(self):
        self.calls.append('subclass run around before')
        yield
        self.calls.append('subclass run around after')


class CaseWithPatcher(BaseTestCase):

    @patcher('tests.dummy.thing')
    def dummy_thing(self):
        return sentinel.mock

    dummy_it = patcher('tests.dummy.it', return_value=12)


class SubclassedCaseWithPatcher(CaseWithPatcher):
    pass


class CaseWithPatcherObject(BaseTestCase):

    @patcher.object(ThingClass, 'prop')
    def dummy_thing(self):
        return 15


class SubclassedCaseWithPatcherObject(CaseWithPatcherObject):
    pass


# TODO: Make the subclass checking just be a subclass of the test case
class TestExam(Exam, TestCase):

    def test_assert_changes_is_asserts_mixin_assert_changes(self):
        from exam.asserts import AssertsMixin
        self.assertEqual(AssertsMixin.assertChanges, Exam.assertChanges)

    def test_before_runs_method_before_test_case(self):
        case = CaseWithBeforeHook()
        self.assertEqual(case.calls, [])
        case.run()
        self.assertEqual(case.calls_before_run, ['run before'])

    def test_before_decorator_runs_func_before_function(self):
        case = CaseWithDecoratedBeforeHook()
        self.assertFalse(hasattr(case, 'state'))
        case.should_have_run_before()
        self.assertTrue(case.state)

    def test_before_decorator_runs_multiple_funcs(self):
        case = CaseWithDecoratedBeforeHook()
        self.assertFalse(hasattr(case, 'state'))
        self.assertFalse(hasattr(case, 'other_state'))
        case.should_have_run_both_states()
        self.assertTrue(case.state)
        self.assertTrue(case.other_state)

    def test_before_decorator_does_not_squash_func_name(self):
        self.assertEqual(
            CaseWithDecoratedBeforeHook.should_have_run_before.__name__,
            'should_have_run_before'
        )

    def test_after_adds_each_method_after_test_case(self):
        case = CaseWithAfterHook()
        self.assertEqual(case.calls, [])
        case.run()
        self.assertEqual(case.calls, ['run before', 'run after'])

    def test_around_calls_methods_before_and_after_run(self):
        case = CaseWithAroundHook()
        self.assertEqual(case.calls, [])
        case.run()
        self.assertEqual(case.calls_before_run, ['run around before'])
        self.assertEqual(case.calls, ['run around before', 'run around after'])

    def test_before_works_on_subclasses(self):
        case = SubclassWithBeforeHook()
        self.assertEqual(case.calls, [])

        case.run()

        # The only concern with ordering here is that the parent class's @before
        # hook fired before it's parents.  The actual order of the @before hooks
        # within a level of class is irrelevant.
        self.assertEqual(case.calls, ['run before', 'subclass run before'])

    def test_after_works_on_subclasses(self):
        case = SubclassCaseWithAfterHook()
        self.assertEqual(case.calls, [])

        case.run()

        self.assertEqual(case.calls_before_run, ['run before'])
        self.assertEqual(case.calls, ['run before', 'run after', 'subclass run after'])

    def test_around_works_with_subclasses(self):
        case = SubclassCaseWithAroundHook()
        self.assertEqual(case.calls, [])

        case.run()

        self.assertEqual(case.calls_before_run, ['subclass run around before'])
        self.assertEqual(case.calls, ['subclass run around before', 'subclass run around after'])

    def test_patcher_start_value_is_added_to_case_dict_on_run(self):
        case = CaseWithPatcher()
        case.run()
        self.assertEqual(case.vars_when_run['dummy_thing'], sentinel.mock)

    def test_patcher_patches_object_on_setup_and_adds_patcher_to_cleanup(self):
        case = CaseWithPatcher()

        self.assertNotEqual(get_thing(), sentinel.mock)

        case.run()

        self.assertEqual(get_thing(), sentinel.mock)
        [cleanup() for cleanup in case.cleanups]
        self.assertNotEqual(get_thing(), sentinel.mock)

    def test_patcher_lifecycle_works_on_subclasses(self):
        case = SubclassedCaseWithPatcher()

        self.assertNotEqual(get_thing(), sentinel.mock)

        case.run()

        self.assertEqual(get_thing(), sentinel.mock)
        [cleanup() for cleanup in case.cleanups]
        self.assertNotEqual(get_thing(), sentinel.mock)

    def test_patcher_patches_with_a_magic_mock_if_no_function_decorated(self):
        case = CaseWithPatcher()

        self.assertNotEqual(get_it()(), 12)
        case.run()
        self.assertEqual(get_it()(), 12)

        case.cleanups[0]()
        self.assertNotEqual(get_thing(), 12)

    def test_patcher_object_patches_object(self):
        case = CaseWithPatcherObject()
        self.assertNotEqual(get_prop(), 15)

        case.run()
        self.assertEqual(get_prop(), 15)

        [cleanup() for cleanup in case.cleanups]
        self.assertNotEqual(get_prop(), 15)

    def test_patcher_object_works_with_subclasses(self):
        case = SubclassedCaseWithPatcherObject()

        self.assertNotEqual(get_prop(), 15)
        case.run()
        self.assertEqual(get_prop(), 15)

        [cleanup() for cleanup in case.cleanups]
        self.assertNotEqual(get_prop(), 15)

########NEW FILE########
__FILENAME__ = test_decorators
from tests import TestCase

from exam.decorators import fixture


class Outer(object):

    @classmethod
    def meth(cls):
        return cls, 'from method'

    @classmethod
    def reflective_meth(cls, arg):
        return cls, arg


class Dummy(object):

    outside = 'value from outside'

    @fixture
    def number(self):
        return 42

    @fixture
    def obj(self):
        return object()

    inline = fixture(int, 5)
    inline_func = fixture(lambda self: self.outside)
    inline_func_with_args = fixture(lambda *a, **k: (a, k), 1, 2, a=3)
    inline_from_method = fixture(Outer.meth)

    inline_from_method_with_arg_1 = fixture(Outer.reflective_meth, 1)
    inline_from_method_with_arg_2 = fixture(Outer.reflective_meth, 2)


class ExtendedDummy(Dummy):

    @fixture
    def number(self):
        return 42 + 42


class TestFixture(TestCase):

    def test_converts_method_to_property(self):
        self.assertEqual(Dummy().number, 42)

    def test_caches_property_on_same_instance(self):
        instance = Dummy()
        self.assertEqual(instance.obj, instance.obj)

    def test_gives_different_object_on_separate_instances(self):
        self.assertNotEqual(Dummy().obj, Dummy().obj)

    def test_can_be_used_inline_with_a_function(self):
        self.assertEqual(Dummy().inline_func, 'value from outside')

    def test_can_be_used_with_a_callable_that_takes_args(self):
        inst = Dummy()
        self.assertEqual(inst.inline_func_with_args, ((inst, 1, 2), dict(a=3)))

    def test_can_be_used_with_class_method(self):
        self.assertEqual(Dummy().inline_from_method, (Outer, 'from method'))

    def test_if_passed_type_builds_new_object(self):
        self.assertEqual(Dummy().inline, 5)

    def test_override_in_subclass_overrides_value(self):
        self.assertEqual(ExtendedDummy().number, 42 + 42)

    def test_captures_identical_funcs_with_args_separatly(self):
        instance = Dummy()

        first = instance.inline_from_method_with_arg_1
        second = instance.inline_from_method_with_arg_2

        self.assertNotEqual(first, second)

########NEW FILE########
__FILENAME__ = test_exam
from tests import TestCase


import exam


class TestExam(TestCase):

    DECORATORS = ('fixture', 'before', 'after', 'around', 'patcher')

    def test_exam_is_cases_exam(self):
        from exam.cases import Exam
        self.assertEqual(exam.Exam, Exam)

    def test_imports_all_the_decorators(self):
        import exam.decorators

        for decorator in self.DECORATORS:
            from_decorators = getattr(exam.decorators, decorator)
            from_root = getattr(exam, decorator)

            self.assertEqual(from_root, from_decorators)

########NEW FILE########
__FILENAME__ = test_helpers
from tests import TestCase
from mock import patch, Mock, sentinel

from exam.helpers import intercept, rm_f, track, mock_import, call, effect
from exam.decorators import fixture


@patch('exam.helpers.shutil')
class TestRmrf(TestCase):

    path = '/path/to/folder'

    def test_calls_shutil_rmtreee(self, shutil):
        rm_f(self.path)
        shutil.rmtree.assert_called_once_with(self.path, ignore_errors=True)

    @patch('exam.helpers.os')
    def test_on_os_errors_calls_os_remove(self, os, shutil):
        shutil.rmtree.side_effect = OSError
        rm_f(self.path)
        os.remove.assert_called_once_with(self.path)


class TestTrack(TestCase):

    @fixture
    def foo_mock(self):
        return Mock()

    @fixture
    def bar_mock(self):
        return Mock()

    def test_makes_new_mock_and_attaches_each_kwarg_to_it(self):
        tracker = track(foo=self.foo_mock, bar=self.bar_mock)
        self.assertEqual(tracker.foo, self.foo_mock)
        self.assertEqual(tracker.bar, self.bar_mock)


class TestMockImport(TestCase):

    def test_is_a_context_manager_that_yields_patched_import(self):
        with mock_import('foo') as mock_foo:
            import foo
            self.assertEqual(foo, mock_foo)

    def test_mocks_import_for_packages(self):
        with mock_import('foo.bar.baz') as mock_baz:
            import foo.bar.baz
            self.assertEqual(foo.bar.baz, mock_baz)

    @mock_import('foo')
    def test_can_be_used_as_a_decorator_too(self, mock_foo):
        import foo
        self.assertEqual(foo, mock_foo)

    @mock_import('foo')
    @mock_import('bar')
    def test_stacked_adds_args_bottom_up(self, mock_bar, mock_foo):
        import foo
        import bar
        self.assertEqual(mock_bar, bar)
        self.assertEqual(mock_foo, foo)


class TestIntercept(TestCase):

    class Example(object):
        def method(self, positional, keyword):
            return sentinel.METHOD_RESULT

    def test_intercept(self):
        ex = self.Example()

        def counter(positional, keyword):
            assert positional is sentinel.POSITIONAL_ARGUMENT
            assert keyword is sentinel.KEYWORD_ARGUMENT
            result = yield
            assert result is sentinel.METHOD_RESULT
            counter.calls += 1

        counter.calls = 0

        intercept(ex, 'method', counter)
        self.assertEqual(counter.calls, 0)
        assert ex.method(sentinel.POSITIONAL_ARGUMENT,
            keyword=sentinel.KEYWORD_ARGUMENT) is sentinel.METHOD_RESULT
        self.assertEqual(counter.calls, 1)

        ex.method.unwrap()
        assert ex.method(sentinel.POSITIONAL_ARGUMENT,
            keyword=sentinel.KEYWORD_ARGUMENT) is sentinel.METHOD_RESULT
        self.assertEqual(counter.calls, 1)


class TestEffect(TestCase):

    def test_creates_callable_mapped_to_config_dict(self):
        config = [
            (call(1), 2),
            (call('a'), 3),
            (call(1, b=2), 4),
            (call(c=3), 5)
        ]
        side_effecet = effect(*config)

        self.assertEqual(side_effecet(1), 2)
        self.assertEqual(side_effecet('a'), 3)
        self.assertEqual(side_effecet(1, b=2), 4)
        self.assertEqual(side_effecet(c=3), 5)

    def test_raises_type_error_when_called_with_unknown_args(self):
        side_effect = effect((call(1), 5))
        self.assertRaises(TypeError, side_effect, 'junk')

    def test_can_be_used_with_mutable_data_structs(self):
        side_effect = effect((call([1, 2, 3]), 'list'))
        self.assertEqual(side_effect([1, 2, 3]), 'list')

########NEW FILE########
__FILENAME__ = test_mock
from tests import TestCase

from exam.mock import Mock
from exam.decorators import fixture, before


class MockTest(TestCase):

    mock = fixture(Mock)

    @before
    def assert_mock_clean(self):
        self.mock.assert_not_called()

    def test_assert_called_asserts_mock_was_called(self):
        self.assertRaises(AssertionError, self.mock.assert_called)

        self.mock()
        self.mock.assert_called()

        self.mock.reset_mock()
        self.assertRaises(AssertionError, self.mock.assert_called)

    def test_assert_not_called_asserts_mock_was_not_called(self):
        self.mock()
        self.assertRaises(AssertionError, self.mock.assert_not_called)

        self.mock.reset_mock()
        self.mock.assert_not_called()

    def test_assert_not_called_with_asserts_not_called_with_args(self):
        self.mock(1, 2, three=4)
        self.mock.assert_called_with(1, 2, three=4)

        self.mock.assert_not_called_with(1, 2, four=5)
        self.mock.assert_not_called_with(1, three=5)
        self.mock.assert_not_called_with()

        with self.assertRaises(AssertionError):
            self.mock.assert_not_called_with(1, 2, three=4)

        self.mock('foo')
        self.mock.assert_not_called_with(1, 2, three=4)  # not the latest call

    def test_assert_not_called_once_with_asserts_one_call_with_args(self):
        self.mock.assert_not_called_once_with(1, 2, three=4)  # 0 times

        self.mock(1, 2, three=4)

        with self.assertRaises(AssertionError):
            self.mock.assert_not_called_once_with(1, 2, three=4)  # 1 time

        self.mock(1, 2, three=4)
        self.mock.assert_not_called_once_with(1, 2, three=4)  # 2 times

    def test_assert_not_any_call_asserts_never_called_with_args(self):
        self.mock.assert_not_any_call(1, 2, three=4)

        self.mock(1, 2, three=4)

        with self.assertRaises(AssertionError):
            self.mock.assert_not_any_call(1, 2, three=4)

        self.mock('foo')

        with self.assertRaises(AssertionError):
            # Even though it's not the latest, it was previously called with
            # these args
            self.mock.assert_not_any_call(1, 2, three=4)

########NEW FILE########
__FILENAME__ = test_objects
from mock import sentinel
from tests import TestCase

from exam.objects import always, noop


class TestAlways(TestCase):

    def test_always_returns_identity(self):
        fn = always(sentinel.RESULT_VALUE)
        assert fn() is sentinel.RESULT_VALUE
        assert fn(1, key='value') is sentinel.RESULT_VALUE

    def test_can_be_called_with_anything(self):
        noop()
        noop(1)
        noop(key='val')
        noop(1, key='val')
        noop(1, 2, 3, key='val')
        noop(1, 2, 3, key='val', another='thing')

    def test_returns_none(self):
        self.assertIsNone(noop())

########NEW FILE########
