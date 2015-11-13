__FILENAME__ = contemplate_koans
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Acknowledgment:
#
# Python Koans is a port of Ruby Koans originally written by Jim Weirich
# and Joe O'brien of Edgecase. There are some differences and tweaks specific
# to the Python language, but a great deal of it has been copied wholesale.
# So thank guys!
#

import sys


if __name__ == '__main__':
    if sys.version_info >= (3, 0):
        print("\nThis is the Python 2 version of Python Koans, but you are " +
              "running it with Python 3 or newer!\n\n"
              "Did you accidentally use the wrong python script? \nTry:\n\n" +
              "    python contemplate_koans.py\n")
    else:
        if sys.version_info < (2, 7):
            print("\n" +
                  "********************************************************\n" +
                  "WARNING:\n" +
                  "This version of Python Koans was designed for " +
                  "Python 2.7 or greater.\n" +
                  "Your version of Python is older, so you may run into " +
                  "problems!\n\n" +
                  "But lets see how far we get...\n" +
                  "********************************************************\n")

        from runner.mountain import Mountain

        Mountain().walk_the_path(sys.argv)

########NEW FILE########
__FILENAME__ = about_asserts
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutAsserts(Koan):

    def test_assert_truth(self):
        """
        We shall contemplate truth by testing reality, via asserts.
        """

        # Confused? This video should help:
        #
        #   http://bit.ly/about_asserts

        self.assertTrue(False)  # This should be true

    def test_assert_with_message(self):
        """
        Enlightenment may be more easily achieved with appropriate messages.
        """
        self.assertTrue(False, "This should be true -- Please fix this")

    def test_fill_in_values(self):
        """
        Sometimes we will ask you to fill in the values
        """
        self.assertEqual(__, 1 + 1)

    def test_assert_equality(self):
        """
        To understand reality, we must compare our expectations against
        reality.
        """
        expected_value = __
        actual_value = 1 + 1
        self.assertTrue(expected_value == actual_value)

    def test_a_better_way_of_asserting_equality(self):
        """
        Some ways of asserting equality are better than others.
        """
        expected_value = __
        actual_value = 1 + 1

        self.assertEqual(expected_value, actual_value)

    def test_that_unittest_asserts_work_the_same_way_as_python_asserts(self):
        """
        Understand what lies within.
        """

        # This throws an AssertionError exception
        assert False

    def test_that_sometimes_we_need_to_know_the_class_type(self):
        """
        What is in a class name?
        """

        # Sometimes we will ask you what the class type of an object is.
        #
        # For example, contemplate the text string "naval". What is it's class type?
        # The koans runner will include this feedback for this koan:
        #
        #   AssertionError: '-=> FILL ME IN! <=-' != <type 'str'>
        #
        # So "naval".__class__ is equal to <type 'str'>? No not quite. This
        # is just what it displays. The answer is simply str.
        #
        # See for yourself:

        self.assertEqual(__, "naval".__class__) # It's str, not <type 'str'>

        # Need an illustration? More reading can be found here:
        #
        #   http://bit.ly/__class__

########NEW FILE########
__FILENAME__ = about_attribute_access
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Partially based on AboutMessagePassing in the Ruby Koans
#

from runner.koan import *


class AboutAttributeAccess(Koan):

    class TypicalObject(object):
        pass

    def test_calling_undefined_functions_normally_results_in_errors(self):
        typical = self.TypicalObject()

        try:
            typical.foobar()
        except Exception as exception:
            self.assertEqual(__, exception.__class__.__name__)
            self.assertMatch(__, exception[0])

    def test_calling_getattribute_causes_an_attribute_error(self):
        typical = self.TypicalObject()

        try:
            typical.__getattribute__('foobar')
        except AttributeError as exception:
            self.assertMatch(__, exception[0])

        # THINK ABOUT IT:
        #
        # If the method __getattribute__() causes the AttributeError, then
        # what would happen if we redefine __getattribute__()?

    # ------------------------------------------------------------------

    class CatchAllAttributeReads(object):
        def __getattribute__(self, attr_name):
            return "Someone called '" + attr_name + \
                "' and it could not be found"

    def test_all_attribute_reads_are_caught(self):
        catcher = self.CatchAllAttributeReads()

        self.assertMatch(__, catcher.foobar)

    def test_intercepting_return_values_can_disrupt_the_call_chain(self):
        catcher = self.CatchAllAttributeReads()

        self.assertMatch(__, catcher.foobaz)  # This is fine

        try:
            catcher.foobaz(1)
        except TypeError as ex:
            self.assertMatch(__, ex[0])

        # foobaz returns a string. What happens to the '(1)' part?
        # Try entering this into a python console to reproduce the issue:
        #
        #     "foobaz"(1)
        #

    def test_changing_getattribute_will_affect__the_getattr_function(self):
        catcher = self.CatchAllAttributeReads()

        self.assertMatch(__, getattr(catcher, 'any_attribute'))

    # ------------------------------------------------------------------

    class WellBehavedFooCatcher(object):
        def __getattribute__(self, attr_name):
            if attr_name[:3] == "foo":
                return "Foo to you too"
            else:
                return \
                    super(AboutAttributeAccess.WellBehavedFooCatcher, self). \
                    __getattribute__(attr_name)

    def test_foo_attributes_are_caught(self):
        catcher = self.WellBehavedFooCatcher()

        self.assertEqual(__, catcher.foo_bar)
        self.assertEqual(__, catcher.foo_baz)

    def test_non_foo_messages_are_treated_normally(self):
        catcher = self.WellBehavedFooCatcher()

        try:
            catcher.normal_undefined_attribute
        except AttributeError as ex:
            self.assertMatch(__, ex[0])

    # ------------------------------------------------------------------

    global stack_depth
    stack_depth = 0

    class RecursiveCatcher(object):
        def __init__(self):
            global stack_depth
            stack_depth = 0
            self.no_of_getattribute_calls = 0

        def __getattribute__(self, attr_name):
            #Uncomment for debugging info:
            #print 'Debug __getattribute__(' + type(self).__name__ + \
            #    "." + attr_name + ") dict=" + str(self.__dict__)

            # We need something that is outside the scope of this class:
            global stack_depth
            stack_depth += 1

            if stack_depth <= 10:  # to prevent a stack overflow
                self.no_of_getattribute_calls += 1
                # Oops! We just accessed an attribute: no_of_getattribute_calls
                # Guess what happens when self.no_of_getattribute_calls is
                # accessed?

            # Using 'object' directly because using super() here will also
            # trigger a __getattribute__() call.
            return object.__getattribute__(self, attr_name)

        def my_method(self):
            pass

    def test_getattribute_is_a_bit_overzealous_sometimes(self):
        catcher = self.RecursiveCatcher()
        catcher.my_method()
        global stack_depth
        self.assertEqual(__, stack_depth)

    # ------------------------------------------------------------------

    class MinimalCatcher(object):
        class DuffObject(object):
            pass

        def __init__(self):
            self.no_of_getattr_calls = 0

        def __getattr__(self, attr_name):
            self.no_of_getattr_calls += 1
            return self.DuffObject

        def my_method(self):
            pass

    def test_getattr_ignores_known_attributes(self):
        catcher = self.MinimalCatcher()
        catcher.my_method()

        self.assertEqual(__, catcher.no_of_getattr_calls)

    def test_getattr_only_catches_unknown_attributes(self):
        catcher = self.MinimalCatcher()
        catcher.purple_flamingos()
        catcher.free_pie()

        self.assertEqual(__,
            catcher.give_me_duff_or_give_me_death().__class__.__name__)

        self.assertEqual(__, catcher.no_of_getattr_calls)

    # ------------------------------------------------------------------

    class PossessiveSetter(object):
        def __setattr__(self, attr_name, value):
            new_attr_name = attr_name

            if attr_name[-5:] == 'comic':
                new_attr_name = "my_" + new_attr_name
            elif attr_name[-3:] == 'pie':
                new_attr_name = "a_" + new_attr_name

            object.__setattr__(self, new_attr_name, value)

    def test_setattr_intercepts_attribute_assignments(self):
        fanboy = self.PossessiveSetter()

        fanboy.comic = 'The Laminator, issue #1'
        fanboy.pie = 'blueberry'

        self.assertEqual(__, fanboy.a_pie)

        #
        # NOTE: Change the prefix to make this next assert pass
        #

        prefix = '__'
        self.assertEqual(
            "The Laminator, issue #1",
            getattr(fanboy, prefix + '_comic'))

    # ------------------------------------------------------------------

    class ScarySetter(object):
        def __init__(self):
            self.num_of_coconuts = 9
            self._num_of_private_coconuts = 2

        def __setattr__(self, attr_name, value):
            new_attr_name = attr_name

            if attr_name[0] != '_':
                new_attr_name = "altered_" + new_attr_name

            object.__setattr__(self, new_attr_name, value)

    def test_it_modifies_external_attribute_as_expected(self):
        setter = self.ScarySetter()
        setter.e = "mc hammer"

        self.assertEqual(__, setter.altered_e)

    def test_it_mangles_some_internal_attributes(self):
        setter = self.ScarySetter()

        try:
            coconuts = setter.num_of_coconuts
        except AttributeError:
            self.assertEqual(__, setter.altered_num_of_coconuts)

    def test_in_this_case_private_attributes_remain_unmangled(self):
        setter = self.ScarySetter()

        self.assertEqual(__, setter._num_of_private_coconuts)

########NEW FILE########
__FILENAME__ = about_classes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutClasses(Koan):
    class Dog(object):
        "Dogs need regular walkies. Never, ever let them drive."

    def test_instances_of_classes_can_be_created_adding_parentheses(self):
        fido = self.Dog()
        self.assertEqual(__, fido.__class__.__name__)

    def test_classes_have_docstrings(self):
        self.assertMatch(__, self.Dog.__doc__)

    # ------------------------------------------------------------------

    class Dog2(object):
        def __init__(self):
            self._name = 'Paul'

        def set_name(self, a_name):
            self._name = a_name

    def test_init_method_is_the_constructor(self):
        dog = self.Dog2()
        self.assertEqual(__, dog._name)

    def test_private_attributes_are_not_really_private(self):
        dog = self.Dog2()
        dog.set_name("Fido")
        self.assertEqual(__, dog._name)
        # The _ prefix in _name implies private ownership, but nothing is truly
        # private in Python.

    def test_you_can_also_access_the_value_out_using_getattr_and_dict(self):
        fido = self.Dog2()
        fido.set_name("Fido")

        self.assertEqual(__, getattr(fido, "_name"))
        # getattr(), setattr() and delattr() are a way of accessing attributes
        # by method rather than through assignment operators

        self.assertEqual(__, fido.__dict__["_name"])
        # Yes, this works here, but don't rely on the __dict__ object! Some
        # class implementations use optimization which result in __dict__ not
        # showing everything.

    # ------------------------------------------------------------------

    class Dog3(object):
        def __init__(self):
            self._name = None

        def set_name(self, a_name):
            self._name = a_name

        def get_name(self):
            return self._name

        name = property(get_name, set_name)

    def test_that_name_can_be_read_as_a_property(self):
        fido = self.Dog3()
        fido.set_name("Fido")

        self.assertEqual(__, fido.get_name())  # access as method
        self.assertEqual(__, fido.name)        # access as property

    # ------------------------------------------------------------------

    class Dog4(object):
        def __init__(self):
            self._name = None

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, a_name):
            self._name = a_name

    def test_creating_properties_with_decorators_is_slightly_easier(self):
        fido = self.Dog4()

        fido.name = "Fido"
        self.assertEqual(__, fido.name)

    # ------------------------------------------------------------------

    class Dog5(object):
        def __init__(self, initial_name):
            self._name = initial_name

        @property
        def name(self):
            return self._name

    def test_init_provides_initial_values_for_instance_variables(self):
        fido = self.Dog5("Fido")
        self.assertEqual(__, fido.name)

    def test_args_must_match_init(self):
        self.assertRaises(___, self.Dog5)  # Evaluates self.Dog5()

        # THINK ABOUT IT:
        # Why is this so?

    def test_different_objects_have_different_instance_variables(self):
        fido = self.Dog5("Fido")
        rover = self.Dog5("Rover")

        self.assertEqual(____, rover.name == fido.name)

    # ------------------------------------------------------------------

    class Dog6(object):
        def __init__(self, initial_name):
            self._name = initial_name

        def get_self(self):
            return self

        def __str__(self):
            #
            # Implement this!
            #
            return __

        def __repr__(self):
            return "<Dog named '" + self._name + "'>"

    def test_inside_a_method_self_refers_to_the_containing_object(self):
        fido = self.Dog6("Fido")

        self.assertEqual(__, fido.get_self())  # Not a string!

    def test_str_provides_a_string_version_of_the_object(self):
        fido = self.Dog6("Fido")
        self.assertEqual("Fido", str(fido))

    def test_str_is_used_explicitly_in_string_interpolation(self):
        fido = self.Dog6("Fido")
        self.assertEqual(__, "My dog is " + str(fido))

    def test_repr_provides_a_more_complete_string_version(self):
        fido = self.Dog6("Fido")
        self.assertEqual(__, repr(fido))

    def test_all_objects_support_str_and_repr(self):
        seq = [1, 2, 3]

        self.assertEqual(__, str(seq))
        self.assertEqual(__, repr(seq))

        self.assertEqual(__, str("STRING"))
        self.assertEqual(__, repr("STRING"))

########NEW FILE########
__FILENAME__ = about_class_attributes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutClassMethods in the Ruby Koans
#

from runner.koan import *


class AboutClassAttributes(Koan):
    class Dog(object):
        pass

    def test_new_style_class_objects_are_objects(self):
        # Note: Old style class instances are not objects but they are being
        # phased out it Python 3.

        fido = self.Dog()
        self.assertEqual(__, isinstance(fido, object))

    def test_classes_are_types(self):
        self.assertEqual(__, self.Dog.__class__ == type)

    def test_classes_are_objects_too(self):
        self.assertEqual(__, issubclass(self.Dog, object))

    def test_objects_have_methods(self):
        fido = self.Dog()
        self.assertEqual(__, len(dir(fido)))

    def test_classes_have_methods(self):
        self.assertEqual(__, len(dir(self.Dog)))

    def test_creating_objects_without_defining_a_class(self):
        singularity = object()
        self.assertEqual(__, len(dir(singularity)))

    def test_defining_attributes_on_individual_objects(self):
        fido = self.Dog()
        fido.legs = 4

        self.assertEqual(__, fido.legs)

    def test_defining_functions_on_individual_objects(self):
        fido = self.Dog()
        fido.wag = lambda: 'fidos wag'

        self.assertEqual(__, fido.wag())

    def test_other_objects_are_not_affected_by_these_singleton_functions(self):
        fido = self.Dog()
        rover = self.Dog()

        def wag():
            return 'fidos wag'
        fido.wag = wag

        try:
            rover.wag()
        except Exception as ex:
            self.assertMatch(__, ex[0])

    # ------------------------------------------------------------------

    class Dog2(object):
        def wag(self):
            return 'instance wag'

        def bark(self):
            return "instance bark"

        def growl(self):
            return "instance growl"

        @staticmethod
        def bark():
            return "staticmethod bark, arg: None"

        @classmethod
        def growl(cls):
            return "classmethod growl, arg: cls=" + cls.__name__

    def test_like_all_objects_classes_can_have_singleton_methods(self):
        self.assertMatch(__, self.Dog2.growl())

    def test_classmethods_are_not_independent_of_instance_methods(self):
        fido = self.Dog2()
        self.assertMatch(__, fido.growl())
        self.assertMatch(__, self.Dog2.growl())

    def test_staticmethods_are_unbound_functions_housed_in_a_class(self):
        self.assertMatch(__, self.Dog2.bark())

    def test_staticmethods_also_overshadow_instance_methods(self):
        fido = self.Dog2()
        self.assertMatch(__, fido.bark())

    # ------------------------------------------------------------------

    class Dog3(object):
        def __init__(self):
            self._name = None

        def get_name_from_instance(self):
            return self._name

        def set_name_from_instance(self, name):
            self._name = name

        @classmethod
        def get_name(cls):
            return cls._name

        @classmethod
        def set_name(cls, name):
            cls._name = name

        name = property(get_name, set_name)
        name_from_instance = property(
            get_name_from_instance, set_name_from_instance)

    def test_classmethods_can_not_be_used_as_properties(self):
        fido = self.Dog3()
        try:
            fido.name = "Fido"
        except Exception as ex:
            self.assertMatch(__, ex[0])

    def test_classes_and_instances_do_not_share_instance_attributes(self):
        fido = self.Dog3()
        fido.set_name_from_instance("Fido")
        fido.set_name("Rover")
        self.assertEqual(__, fido.get_name_from_instance())
        self.assertEqual(__, self.Dog3.get_name())

    def test_classes_and_instances_do_share_class_attributes(self):
        fido = self.Dog3()
        fido.set_name("Fido")
        self.assertEqual(__, fido.get_name())
        self.assertEqual(__, self.Dog3.get_name())

    # ------------------------------------------------------------------

    class Dog4(object):
        def a_class_method(cls):
            return 'dogs class method'

        def a_static_method():
            return 'dogs static method'

        a_class_method = classmethod(a_class_method)
        a_static_method = staticmethod(a_static_method)

    def test_you_can_define_class_methods_without_using_a_decorator(self):
        self.assertEqual(__, self.Dog4.a_class_method())

    def test_you_can_define_static_methods_without_using_a_decorator(self):
        self.assertEqual(__, self.Dog4.a_static_method())

    # ------------------------------------------------------------------

    def test_you_can_explicitly_call_class_methods_from_instance_methods(self):
        fido = self.Dog4()
        self.assertEqual(__, fido.__class__.a_class_method())

########NEW FILE########
__FILENAME__ = about_comprehension
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutComprehension(Koan):


    def test_creating_lists_with_list_comprehensions(self):
        feast = ['lambs', 'sloths', 'orangutans', 'breakfast cereals',
            'fruit bats']

        comprehension = [delicacy.capitalize() for delicacy in feast]

        self.assertEqual(__, comprehension[0])
        self.assertEqual(__, comprehension[2])

    def test_filtering_lists_with_list_comprehensions(self):
        feast = ['spam', 'sloths', 'orangutans', 'breakfast cereals',
            'fruit bats']

        comprehension = [delicacy for delicacy in feast if len(delicacy) > 6]

        self.assertEqual(__, len(feast))
        self.assertEqual(__, len(comprehension))

    def test_unpacking_tuples_in_list_comprehensions(self):
        list_of_tuples = [(1, 'lumberjack'), (2, 'inquisition'), (4, 'spam')]
        comprehension = [ skit * number for number, skit in list_of_tuples ]

        self.assertEqual(__, comprehension[0])
        self.assertEqual(__, len(comprehension[2]))

    def test_double_list_comprehension(self):
        list_of_eggs = ['poached egg', 'fried egg']
        list_of_meats = ['lite spam', 'ham spam', 'fried spam']


        comprehension = [ '{0} and {1}'.format(egg, meat) for egg in list_of_eggs for meat in list_of_meats]


        self.assertEqual(__, len(comprehension))
        self.assertEqual(__, comprehension[0])

    def test_creating_a_set_with_set_comprehension(self):
        comprehension = { x for x in 'aabbbcccc'}

        self.assertEqual(__, comprehension)  # rememeber that set members are unique

    def test_creating_a_dictionary_with_dictionary_comprehension(self):
        dict_of_weapons = {'first': 'fear', 'second': 'surprise',
                           'third':'ruthless efficiency', 'forth':'fanatical devotion',
                           'fifth': None}

        dict_comprehension = { k.upper(): weapon for k, weapon in dict_of_weapons.iteritems() if weapon}

        self.assertEqual(__, 'first' in dict_comprehension)
        self.assertEqual(__, 'FIRST' in dict_comprehension)
        self.assertEqual(__, len(dict_of_weapons))
        self.assertEqual(__, len(dict_comprehension))

########NEW FILE########
__FILENAME__ = about_control_statements
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutControlStatements(Koan):

    def test_if_then_else_statements(self):
        if True:
            result = 'true value'
        else:
            result = 'false value'
        self.assertEqual(__, result)

    def test_if_then_statements(self):
        result = 'default value'
        if True:
            result = 'true value'
        self.assertEqual(__, result)
        
    def test_if_then_elif_else_statements(self):
        if False:
            result = 'first value'
        elif True: 
            result = 'true value'
        else:
            result = 'default value'
        self.assertEqual(__, result)

    def test_while_statement(self):
        i = 1
        result = 1
        while i <= 10:
            result = result * i
            i += 1
        self.assertEqual(__, result)

    def test_break_statement(self):
        i = 1
        result = 1
        while True:
            if i > 10: break
            result = result * i
            i += 1
        self.assertEqual(__, result)

    def test_continue_statement(self):
        i = 0
        result = []
        while i < 10:
            i += 1
            if (i % 2) == 0: continue
            result.append(i)
        self.assertEqual(__, result)

    def test_for_statement(self):
        phrase = ["fish", "and", "chips"]
        result = []
        for item in phrase:
            result.append(item.upper())
        self.assertEqual([__, __, __], result)

    def test_for_statement_with_tuples(self):
        round_table = [
            ("Lancelot", "Blue"),
            ("Galahad", "I don't know!"),
            ("Robin", "Blue! I mean Green!"),
            ("Arthur", "Is that an African Swallow or Amazonian Swallow?")
        ]
        result = []
        for knight, answer in round_table:
            result.append("Contestant: '" + knight + \
            "'   Answer: '" + answer + "'")

        text = __

        self.assertMatch(text, result[2])

        self.assertNoMatch(text, result[0])
        self.assertNoMatch(text, result[1])
        self.assertNoMatch(text, result[3])

########NEW FILE########
__FILENAME__ = about_decorating_with_classes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

import functools


class AboutDecoratingWithClasses(Koan):
    def maximum(self, a, b):
        if a > b:
            return a
        else:
            return b

    def test_partial_that_wrappers_no_args(self):
        """
        Before we can understand this type of decorator we need to consider
        the partial.
        """
        max = functools.partial(self.maximum)

        self.assertEqual(__, max(7, 23))
        self.assertEqual(__, max(10, -10))

    def test_partial_that_wrappers_first_arg(self):
        max0 = functools.partial(self.maximum, 0)

        self.assertEqual(__, max0(-4))
        self.assertEqual(__, max0(5))

    def test_partial_that_wrappers_all_args(self):
        always99 = functools.partial(self.maximum, 99, 20)
        always20 = functools.partial(self.maximum, 9, 20)

        self.assertEqual(__, always99())
        self.assertEqual(__, always20())

    # ------------------------------------------------------------------

    class doubleit(object):
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args):
            return self.fn(*args) + ', ' + self.fn(*args)

        def __get__(self, obj, cls=None):
            if not obj:
                # Decorating an unbound function
                return self
            else:
                # Decorating a bound method
                return functools.partial(self, obj)

    @doubleit
    def foo(self):
        return "foo"

    @doubleit
    def parrot(self, text):
        return text.upper()

    def test_decorator_with_no_arguments(self):
        # To clarify: the decorator above the function has no arguments, even
        # if the decorated function does

        self.assertEqual(__, self.foo())
        self.assertEqual(__, self.parrot('pieces of eight'))

    # ------------------------------------------------------------------

    def sound_check(self):
        #Note: no decorator
        return "Testing..."

    def test_what_a_decorator_is_doing_to_a_function(self):
        #wrap the function with the decorator
        self.sound_check = self.doubleit(self.sound_check)

        self.assertEqual(__, self.sound_check())

    # ------------------------------------------------------------------

    class documenter(object):
        def __init__(self, *args):
            self.fn_doc = args[0]

        def __call__(self, fn):
            def decorated_function(*args):
                return fn(*args)

            if fn.__doc__:
                decorated_function.__doc__ = fn.__doc__ + ": " + self.fn_doc
            else:
                decorated_function.__doc__ = self.fn_doc
            return decorated_function

    @documenter("Increments a value by one. Kind of.")
    def count_badly(self, num):
        num += 1
        if num == 3:
            return 5
        else:
            return num

    @documenter("Does nothing")
    def idler(self, num):
        "Idler"
        pass

    def test_decorator_with_an_argument(self):
        self.assertEqual(__, self.count_badly(2))
        self.assertEqual(__, self.count_badly.__doc__)

    def test_documentor_which_already_has_a_docstring(self):
        self.assertEqual(__, self.idler.__doc__)

    # ------------------------------------------------------------------

    @documenter("DOH!")
    @doubleit
    @doubleit
    def homer(self):
        return "D'oh"

    def test_we_can_chain_decorators(self):
        self.assertEqual(__, self.homer())
        self.assertEqual(__, self.homer.__doc__)

########NEW FILE########
__FILENAME__ = about_decorating_with_functions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutDecoratingWithFunctions(Koan):
    def addcowbell(fn):
        fn.wow_factor = 'COWBELL BABY!'
        return fn

    @addcowbell
    def mediocre_song(self):
        return "o/~ We all live in a broken submarine o/~"

    def test_decorators_can_modify_a_function(self):
        self.assertMatch(__, self.mediocre_song())
        self.assertEqual(__, self.mediocre_song.wow_factor)

    # ------------------------------------------------------------------

    def xmltag(fn):
        def func(*args):
            return '<' + fn(*args) + '/>'
        return func

    @xmltag
    def render_tag(self, name):
        return name

    def test_decorators_can_change_a_function_output(self):
        self.assertEqual(__, self.render_tag('llama'))

########NEW FILE########
__FILENAME__ = about_deleting_objects
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutDeletingObjects(Koan):
    def test_del_can_remove_slices(self):
        lottery_nums = [4, 8, 15, 16, 23, 42]
        del lottery_nums[1]
        del lottery_nums[2:4]

        self.assertEqual(__, lottery_nums)

    def test_del_can_remove_entire_lists(self):
        lottery_nums = [4, 8, 15, 16, 23, 42]
        del lottery_nums
        try:
            win = lottery_nums
        except Exception as e:
            pass
        self.assertMatch(__, e[0])

    # --------------------------------------------------------------------

    class ClosingSale(object):
        def __init__(self):
            self.hamsters = 7
            self.zebras = 84

        def cameras(self):
            return 34

        def toilet_brushes(self):
            return 48

        def jellies(self):
            return 5

    def test_del_can_remove_attributes(self):
        crazy_discounts = self.ClosingSale()
        del self.ClosingSale.toilet_brushes
        del crazy_discounts.hamsters

        try:
            still_available = crazy_discounts.toilet_brushes()
        except AttributeError as e:
            err_msg1 = e.args[0]

        try:
            still_available = crazy_discounts.hamsters
        except AttributeError as e:
            err_msg2 = e.args[0]

        self.assertMatch(__, err_msg1)
        self.assertMatch(__, err_msg2)

    # --------------------------------------------------------------------

    class ClintEastwood(object):
        def __init__(self):
            self._name = None

        def get_name(self):
            try:
                return self._name
            except:
                return "The man with no name"

        def set_name(self, name):
            self._name = name

        def del_name(self):
            del self._name

        name = property(get_name, set_name, del_name, \
            "Mr Eastwood's current alias")

    def test_del_works_with_properties(self):
        cowboy = self.ClintEastwood()
        cowboy.name = 'Senor Ninguno'
        self.assertEqual('Senor Ninguno', cowboy.name)

        del cowboy.name
        self.assertEqual(__, cowboy.name)

    # --------------------------------------------------------------------

    class Prisoner(object):
        def __init__(self):
            self._name = None

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, name):
            self._name = name

        @name.deleter
        def name(self):
            self._name = 'Number Six'

    def test_another_way_to_make_a_deletable_property(self):
        citizen = self.Prisoner()
        citizen.name = "Patrick"
        self.assertEqual('Patrick', citizen.name)

        del citizen.name
        self.assertEqual(__, citizen.name)

    # --------------------------------------------------------------------

    class MoreOrganisedClosingSale(ClosingSale):
        def __init__(self):
            self.last_deletion = None
            super(AboutDeletingObjects.ClosingSale, self).__init__()

        def __delattr__(self, attr_name):
            self.last_deletion = attr_name

    def tests_del_can_be_overriden(self):
        sale = self.MoreOrganisedClosingSale()
        self.assertEqual(5, sale.jellies())
        del sale.jellies
        self.assertEqual(__, sale.last_deletion)

########NEW FILE########
__FILENAME__ = about_dice_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

import random


class DiceSet(object):
    def __init__(self):
        self._values = None

    @property
    def values(self):
        return self._values

    def roll(self, n):
        # Needs implementing!
        # Tip: random.randint(min, max) can be used to generate random numbers
        pass


class AboutDiceProject(Koan):
    def test_can_create_a_dice_set(self):
        dice = DiceSet()
        self.assertTrue(dice)

    def test_rolling_the_dice_returns_a_set_of_integers_between_1_and_6(self):
        dice = DiceSet()

        dice.roll(5)
        self.assertTrue(isinstance(dice.values, list), "should be a list")
        self.assertEqual(5, len(dice.values))
        for value in dice.values:
            self.assertTrue(
                value >= 1 and value <= 6,
                "value " + str(value) + " must be between 1 and 6")

    def test_dice_values_do_not_change_unless_explicitly_rolled(self):
        dice = DiceSet()
        dice.roll(5)
        first_time = dice.values
        second_time = dice.values
        self.assertEqual(first_time, second_time)

    def test_dice_values_should_change_between_rolls(self):
        dice = DiceSet()

        dice.roll(5)
        first_time = dice.values

        dice.roll(5)
        second_time = dice.values

        self.assertNotEqual(first_time, second_time, \
            "Two rolls should not be equal")

        # THINK ABOUT IT:
        #
        # If the rolls are random, then it is possible (although not
        # likely) that two consecutive rolls are equal.  What would be a
        # better way to test this?

    def test_you_can_roll_different_numbers_of_dice(self):
        dice = DiceSet()

        dice.roll(3)
        self.assertEqual(3, len(dice.values))

        dice.roll(1)
        self.assertEqual(1, len(dice.values))

########NEW FILE########
__FILENAME__ = about_dictionaries
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutHashes in the Ruby Koans
#

from runner.koan import *


class AboutDictionaries(Koan):
    def test_creating_dictionaries(self):
        empty_dict = dict()
        self.assertEqual(dict, type(empty_dict))
        self.assertEqual(dict(), empty_dict)
        self.assertEqual(__, len(empty_dict))

    def test_dictionary_literals(self):
        empty_dict = {}
        self.assertEqual(dict, type(empty_dict))
        babel_fish = {'one': 'uno', 'two': 'dos'}
        self.assertEqual(__, len(babel_fish))

    def test_accessing_dictionaries(self):
        babel_fish = {'one': 'uno', 'two': 'dos'}
        self.assertEqual(__, babel_fish['one'])
        self.assertEqual(__, babel_fish['two'])

    def test_changing_dictionaries(self):
        babel_fish = {'one': 'uno', 'two': 'dos'}
        babel_fish['one'] = 'eins'

        expected = {'two': 'dos', 'one': __}
        self.assertEqual(expected, babel_fish)

    def test_dictionary_is_unordered(self):
        dict1 = {'one': 'uno', 'two': 'dos'}
        dict2 = {'two': 'dos', 'one': 'uno'}

        self.assertEqual(____, dict1 == dict2)

    def test_dictionary_keys_and_values(self):
        babel_fish = {'one': 'uno', 'two': 'dos'}
        self.assertEqual(__, len(babel_fish.keys()))
        self.assertEqual(__, len(babel_fish.values()))
        self.assertEqual(__, 'one' in babel_fish.keys())
        self.assertEqual(__, 'two' in babel_fish.values())
        self.assertEqual(__, 'uno' in babel_fish.keys())
        self.assertEqual(__, 'dos' in babel_fish.values())

    def test_making_a_dictionary_from_a_sequence_of_keys(self):
        cards = {}.fromkeys(
            ('red warrior', 'green elf', 'blue valkyrie', 'yellow dwarf',
             'confused looking zebra'),
            42)

        self.assertEqual(__, len(cards))
        self.assertEqual(__, cards['green elf'])
        self.assertEqual(__, cards['yellow dwarf'])

########NEW FILE########
__FILENAME__ = about_exceptions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutExceptions(Koan):

    class MySpecialError(RuntimeError):
        pass

    def test_exceptions_inherit_from_exception(self):
        mro = self.MySpecialError.__mro__
        self.assertEqual(__, mro[1].__name__)
        self.assertEqual(__, mro[2].__name__)
        self.assertEqual(__, mro[3].__name__)
        self.assertEqual(__, mro[4].__name__)

    def test_try_clause(self):
        result = None
        try:
            self.fail("Oops")
        except StandardError as ex:
            result = 'exception handled'

        self.assertEqual(__, result)

        self.assertEqual(____, isinstance(ex, StandardError))
        self.assertEqual(____, isinstance(ex, RuntimeError))

        self.assertTrue(issubclass(RuntimeError, StandardError), \
            "RuntimeError is a subclass of StandardError")

        self.assertEqual(__, ex[0])

    def test_raising_a_specific_error(self):
        result = None
        try:
            raise self.MySpecialError, "My Message"
        except self.MySpecialError as ex:
            result = 'exception handled'

        self.assertEqual(__, result)
        self.assertEqual(__, ex[0])

    def test_else_clause(self):
        result = None
        try:
            pass
        except RuntimeError:
            result = 'it broke'
            pass
        else:
            result = 'no damage done'

        self.assertEqual(__, result)

    def test_finally_clause(self):
        result = None
        try:
            self.fail("Oops")
        except:
            # no code here
            pass
        finally:
            result = 'always run'

        self.assertEqual(__, result)

########NEW FILE########
__FILENAME__ = about_extra_credit
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# EXTRA CREDIT:
#
# Create a program that will play the Greed Game.
# Rules for the game are in GREED_RULES.TXT.
#
# You already have a DiceSet class and score function you can use.
# Write a player class and a Game class to complete the project.  This
# is a free form assignment, so approach it however you desire.

from runner.koan import *


class AboutExtraCredit(Koan):
    # Write tests here. If you need extra test classes add them to the
    # test suite in runner/path_to_enlightenment.py
    def test_extra_credit_task(self):
        pass

########NEW FILE########
__FILENAME__ = about_generators
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Written in place of AboutBlocks in the Ruby Koans
#
# Note: Both blocks and generators use a yield keyword, but they behave
# a lot differently
#

from runner.koan import *


class AboutGenerators(Koan):

    def test_generating_values_on_the_fly(self):
        result = list()
        bacon_generator = (n + ' bacon' for \
                n in ['crunchy', 'veggie', 'danish'])
        for bacon in bacon_generator:
            result.append(bacon)
        self.assertEqual(__, result)

    def test_generators_are_different_to_list_comprehensions(self):
        num_list = [x * 2 for x in range(1, 3)]
        num_generator = (x * 2 for x in range(1, 3))

        self.assertEqual(2, num_list[0])

        # A generator has to be iterated through.
        self.assertEqual(__, list(num_generator)[0])

        # Both list comprehensions and generators can be iterated
        # though. However, a generator function is only called on the
        # first iteration. The values are generated on the fly instead
        # of stored.
        #
        # Generators are more memory friendly, but less versatile

    def test_generator_expressions_are_a_one_shot_deal(self):
        dynamite = ('Boom!' for n in range(3))

        attempt1 = list(dynamite)
        attempt2 = list(dynamite)

        self.assertEqual(__, list(attempt1))
        self.assertEqual(__, list(attempt2))

    # ------------------------------------------------------------------

    def simple_generator_method(self):
        yield 'peanut'
        yield 'butter'
        yield 'and'
        yield 'jelly'

    def test_generator_method_will_yield_values_during_iteration(self):
        result = list()
        for item in self.simple_generator_method():
            result.append(item)
        self.assertEqual(__, result)

    def test_coroutines_can_take_arguments(self):
        result = self.simple_generator_method()
        self.assertEqual(__, next(result))
        self.assertEqual(__, next(result))
        result.close()

    # ------------------------------------------------------------------

    def square_me(self, seq):
        for x in seq:
            yield x * x

    def test_generator_method_with_parameter(self):
        result = self.square_me(range(2, 5))
        self.assertEqual(__, list(result))

    # ------------------------------------------------------------------

    def sum_it(self, seq):
        value = 0
        for num in seq:
            # The local state of 'value' will be retained between iterations
            value += num
            yield value

    def test_generator_keeps_track_of_local_variables(self):
        result = self.sum_it(range(2, 5))
        self.assertEqual(__, list(result))

    # ------------------------------------------------------------------

    def generator_with_coroutine(self):
        result = yield
        yield result

    def test_generators_can_take_coroutines(self):
        generator = self.generator_with_coroutine()

        # THINK ABOUT IT:
        # Why is this line necessary?
        #
        # Hint: Read the "Specification: Sending Values into Generators"
        #       section of http://www.python.org/dev/peps/pep-0342/
        next(generator)

        self.assertEqual(__, generator.send(1 + 2))

    def test_before_sending_a_value_to_a_generator_next_must_be_called(self):
        generator = self.generator_with_coroutine()

        try:
            generator.send(1 + 2)
        except TypeError as ex:
            self.assertMatch(__, ex[0])

    # ------------------------------------------------------------------

    def yield_tester(self):
        value = yield
        if value:
            yield value
        else:
            yield 'no value'

    def test_generators_can_see_if_they_have_been_called_with_a_value(self):
        generator = self.yield_tester()
        next(generator)
        self.assertEqual('with value', generator.send('with value'))

        generator2 = self.yield_tester()
        next(generator2)
        self.assertEqual(__, next(generator2))

    def test_send_none_is_equivalent_to_next(self):
        generator = self.yield_tester()

        next(generator)
        # 'next(generator)' is exactly equivalent to 'generator.send(None)'
        self.assertEqual(__, generator.send(None))

########NEW FILE########
__FILENAME__ = about_inheritance
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutInheritance(Koan):
    class Dog(object):
        def __init__(self, name):
            self._name = name

        @property
        def name(self):
            return self._name

        def bark(self):
            return "WOOF"

    class Chihuahua(Dog):
        def wag(self):
            return "happy"

        def bark(self):
            return "yip"

    def test_subclasses_have_the_parent_as_an_ancestor(self):
        self.assertEqual(____, issubclass(self.Chihuahua, self.Dog))

    def test_this_subclass_ultimately_inherits_from_object_class(self):
        self.assertEqual(____, issubclass(self.Chihuahua, object))

    def test_instances_inherit_behavior_from_parent_class(self):
        chico = self.Chihuahua("Chico")
        self.assertEqual(__, chico.name)

    def test_subclasses_add_new_behavior(self):
        chico = self.Chihuahua("Chico")
        self.assertEqual(__, chico.wag())

        try:
            fido = self.Dog("Fido")
            fido.wag()
        except StandardError as ex:
            self.assertMatch(__, ex[0])

    def test_subclasses_can_modify_existing_behavior(self):
        chico = self.Chihuahua("Chico")
        self.assertEqual(__, chico.bark())

        fido = self.Dog("Fido")
        self.assertEqual(__, fido.bark())

    # ------------------------------------------------------------------

    class BullDog(Dog):
        def bark(self):
            return super(AboutInheritance.BullDog, self).bark() + ", GRR"

    def test_subclasses_can_invoke_parent_behavior_via_super(self):
        ralph = self.BullDog("Ralph")
        self.assertEqual(__, ralph.bark())

    # ------------------------------------------------------------------

    class GreatDane(Dog):
        def growl(self):
            return super(AboutInheritance.GreatDane, self).bark() + ", GROWL"

    def test_super_works_across_methods(self):
        george = self.GreatDane("George")
        self.assertEqual(__, george.growl())

    # ---------------------------------------------------------

    class Pug(Dog):
        def __init__(self, name):
            pass

    class Greyhound(Dog):
        def __init__(self, name):
            super(AboutInheritance.Greyhound, self).__init__(name)

    def test_base_init_does_not_get_called_automatically(self):
        snoopy = self.Pug("Snoopy")
        try:
            name = snoopy.name
        except Exception as ex:
            self.assertMatch(__, ex[0])

    def test_base_init_has_to_be_called_explicitly(self):
        boxer = self.Greyhound("Boxer")
        self.assertEqual(__, boxer.name)

########NEW FILE########
__FILENAME__ = about_iteration
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutIteration(Koan):

    def test_iterators_are_a_type(self):
        it = iter(range(1, 6))

        fib = 0

        for num in it:
            fib += num

        self.assertEqual(__, fib)

    def test_iterating_with_next(self):
        stages = iter(['alpha', 'beta', 'gamma'])

        try:
            self.assertEqual(__, next(stages))
            next(stages)
            self.assertEqual(__, next(stages))
            next(stages)
        except StopIteration as ex:
            err_msg = 'Ran out of iterations'

        self.assertMatch(__, err_msg)

    # ------------------------------------------------------------------

    def add_ten(self, item):
        return item + 10

    def test_map_transforms_elements_of_a_list(self):
        seq = [1, 2, 3]

        mapped_seq = map(self.add_ten, seq)
        self.assertEqual(__, mapped_seq)

    def test_filter_selects_certain_items_from_a_list(self):
        def is_even(item):
            return (item % 2) == 0

        seq = [1, 2, 3, 4, 5, 6]

        even_numbers = filter(is_even, seq)
        self.assertEqual(__, even_numbers)

    def test_just_return_first_item_found(self):
        def is_big_name(item):
            return len(item) > 4

        names = ["Jim", "Bill", "Clarence", "Doug", "Eli"]

        # NOTE This still iterates through the whole names, so not particularly
        # efficient
        self.assertEqual([__], filter(is_big_name, names)[:1])

        # Boring but effective
        for item in names:
            if is_big_name(item):
                self.assertEqual(__, item)
                break

    # ------------------------------------------------------------------

    def add(self, accum, item):
        return accum + item

    def multiply(self, accum, item):
        return accum * item

    def test_reduce_will_blow_your_mind(self):
        result = reduce(self.add, [2, 3, 4])
        self.assertEqual(__, result)

        result2 = reduce(self.multiply, [2, 3, 4], 1)
        self.assertEqual(__, result2)

        # Extra Credit:
        # Describe in your own words what reduce does.

    # ------------------------------------------------------------------

    def test_use_pass_for_iterations_with_no_body(self):
        for num in range(1, 5):
            pass

        self.assertEqual(__, num)

    # ------------------------------------------------------------------

    def test_all_iteration_methods_work_on_any_sequence_not_just_lists(self):
        # Ranges are an iterable sequence
        result = map(self.add_ten, range(1, 4))
        self.assertEqual(__, list(result))

        try:
            f = open("example_file.txt")

            try:
                def make_upcase(line):
                    return line.strip().upper()
                upcase_lines = map(make_upcase, f.readlines())
                self.assertEqual(__, list(upcase_lines))
            finally:
                # Arg, this is ugly.
                # We will figure out how to fix this later.
                f.close()
        except IOError:
            # should never happen
            self.fail()

########NEW FILE########
__FILENAME__ = about_lambdas
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based slightly on the lambdas section of AboutBlocks in the Ruby Koans
#

from runner.koan import *


class AboutLambdas(Koan):
    def test_lambdas_can_be_assigned_to_variables_and_called_explicitly(self):
        add_one = lambda n: n + 1
        self.assertEqual(__, add_one(10))

    # ------------------------------------------------------------------

    def make_order(self, order):
        return lambda qty: str(qty) + " " + order + "s"

    def test_accessing_lambda_via_assignment(self):
        sausages = self.make_order('sausage')
        eggs = self.make_order('egg')

        self.assertEqual(__, sausages(3))
        self.assertEqual(__, eggs(2))

    def test_accessing_lambda_without_assignment(self):
        self.assertEqual(__, self.make_order('spam')(39823))

########NEW FILE########
__FILENAME__ = about_lists
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutArrays in the Ruby Koans
#

from runner.koan import *


class AboutLists(Koan):
    def test_creating_lists(self):
        empty_list = list()
        self.assertEqual(list, type(empty_list))
        self.assertEqual(__, len(empty_list))

    def test_list_literals(self):
        nums = list()
        self.assertEqual([], nums)

        nums[0:] = [1]
        self.assertEqual([1], nums)

        nums[1:] = [2]
        self.assertEqual([1, __], nums)

        nums.append(333)
        self.assertEqual([1, 2, __], nums)

    def test_accessing_list_elements(self):
        noms = ['peanut', 'butter', 'and', 'jelly']

        self.assertEqual(__, noms[0])
        self.assertEqual(__, noms[3])
        self.assertEqual(__, noms[-1])
        self.assertEqual(__, noms[-3])

    def test_slicing_lists(self):
        noms = ['peanut', 'butter', 'and', 'jelly']

        self.assertEqual(__, noms[0:1])
        self.assertEqual(__, noms[0:2])
        self.assertEqual(__, noms[2:2])
        self.assertEqual(__, noms[2:20])
        self.assertEqual(__, noms[4:0])
        self.assertEqual(__, noms[4:100])
        self.assertEqual(__, noms[5:0])

    def test_slicing_to_the_edge(self):
        noms = ['peanut', 'butter', 'and', 'jelly']

        self.assertEqual(__, noms[2:])
        self.assertEqual(__, noms[:2])

    def test_lists_and_ranges(self):
        self.assertEqual(list, type(range(5)))
        self.assertEqual(__, range(5))
        self.assertEqual(__, range(5, 9))

    def test_ranges_with_steps(self):
        self.assertEqual(__, range(0, 8, 2))
        self.assertEqual(__, range(1, 8, 3))
        self.assertEqual(__, range(5, -7, -4))
        self.assertEqual(__, range(5, -8, -4))

    def test_insertions(self):
        knight = ['you', 'shall', 'pass']
        knight.insert(2, 'not')
        self.assertEqual(__, knight)

        knight.insert(0, 'Arthur')
        self.assertEqual(__, knight)

    def test_popping_lists(self):
        stack = [10, 20, 30, 40]
        stack.append('last')

        self.assertEqual(__, stack)

        popped_value = stack.pop()
        self.assertEqual(__, popped_value)
        self.assertEqual(__, stack)

        popped_value = stack.pop(1)
        self.assertEqual(__, popped_value)
        self.assertEqual(__, stack)

        # Notice that there is a "pop" but no "push" in python?

        # Part of the Python philosophy is that there ideally should be one and
        # only one way of doing anything. A 'push' is the same as an 'append'.

        # To learn more about this try typing "import this" from the python
        # console... ;)

    def test_use_deques_for_making_queues(self):
        from collections import deque

        queue = deque([1, 2])
        queue.append('last')

        self.assertEqual(__, list(queue))

        popped_value = queue.popleft()
        self.assertEqual(__, popped_value)
        self.assertEqual(__, list(queue))

########NEW FILE########
__FILENAME__ = about_list_assignments
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutArrayAssignments in the Ruby Koans
#

from runner.koan import *


class AboutListAssignments(Koan):
    def test_non_parallel_assignment(self):
        names = ["John", "Smith"]
        self.assertEqual(__, names)

    def test_parallel_assignments(self):
        first_name, last_name = ["John", "Smith"]
        self.assertEqual(__, first_name)
        self.assertEqual(__, last_name)

    def test_parallel_assignments_with_sublists(self):
        first_name, last_name = [["Willie", "Rae"], "Johnson"]
        self.assertEqual(__, first_name)
        self.assertEqual(__, last_name)

    def test_swapping_with_parallel_assignment(self):
        first_name = "Roy"
        last_name = "Rob"
        first_name, last_name = last_name, first_name
        self.assertEqual(__, first_name)
        self.assertEqual(__, last_name)

########NEW FILE########
__FILENAME__ = about_methods
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Partially based on AboutMethods in the Ruby Koans
#

from runner.koan import *


def my_global_function(a, b):
    return a + b


class AboutMethods(Koan):
    def test_calling_a_global_function(self):
        self.assertEqual(__, my_global_function(2, 3))

    # NOTE: Wrong number of arguments is not a SYNTAX error, but a
    # runtime error.
    def test_calling_functions_with_wrong_number_of_arguments(self):
        try:
            my_global_function()
        except Exception as exception:
            # NOTE: The .__name__ attribute will convert the class
            # into a string value.
            self.assertEqual(__, exception.__class__.__name__)
            self.assertMatch(
                r'my_global_function\(\) takes exactly 2 arguments \(0 given\)',
                exception[0])

        try:
            my_global_function(1, 2, 3)
        except Exception as e:

            # Note, watch out for parenthesis. They need slashes in front!
            self.assertMatch(__, e[0])

    # ------------------------------------------------------------------

    def pointless_method(self, a, b):
        sum = a + b

    def test_which_does_not_return_anything(self):
        self.assertEqual(__, self.pointless_method(1, 2))
        # Notice that methods accessed from class scope do not require
        # you to pass the first "self" argument?

    # ------------------------------------------------------------------

    def method_with_defaults(self, a, b='default_value'):
        return [a, b]

    def test_calling_with_default_values(self):
        self.assertEqual(__, self.method_with_defaults(1))
        self.assertEqual(__, self.method_with_defaults(1, 2))

    # ------------------------------------------------------------------

    def method_with_var_args(self, *args):
        return args

    def test_calling_with_variable_arguments(self):
        self.assertEqual(__, self.method_with_var_args())
        self.assertEqual(('one', ), self.method_with_var_args('one'))
        self.assertEqual(__, self.method_with_var_args('one', 'two'))

    # ------------------------------------------------------------------

    def function_with_the_same_name(self, a, b):
        return a + b

    def test_functions_without_self_arg_are_global_functions(self):
        def function_with_the_same_name(a, b):
            return a * b

        self.assertEqual(__, function_with_the_same_name(3, 4))

    def test_calling_methods_in_same_class_with_explicit_receiver(self):
        def function_with_the_same_name(a, b):
            return a * b

        self.assertEqual(__, self.function_with_the_same_name(3, 4))

    # ------------------------------------------------------------------

    def another_method_with_the_same_name(self):
        return 10

    link_to_overlapped_method = another_method_with_the_same_name

    def another_method_with_the_same_name(self):
        return 42

    def test_that_old_methods_are_hidden_by_redefinitions(self):
        self.assertEqual(__, self.another_method_with_the_same_name())

    def test_that_overlapped_method_is_still_there(self):
        self.assertEqual(__, self.link_to_overlapped_method())

    # ------------------------------------------------------------------

    def empty_method(self):
        pass

    def test_methods_that_do_nothing_need_to_use_pass_as_a_filler(self):
        self.assertEqual(__, self.empty_method())

    def test_pass_does_nothing_at_all(self):
        "You"
        "shall"
        "not"
        pass
        self.assertEqual(____, "Still got to this line" != None)

    # ------------------------------------------------------------------

    def one_line_method(self): return 'Madagascar'

    def test_no_indentation_required_for_one_line_statement_bodies(self):
        self.assertEqual(__, self.one_line_method())

    # ------------------------------------------------------------------

    def method_with_documentation(self):
        "A string placed at the beginning of a function is used for documentation"
        return "ok"

    def test_the_documentation_can_be_viewed_with_the_doc_method(self):
        self.assertMatch(__, self.method_with_documentation.__doc__)

    # ------------------------------------------------------------------

    class Dog(object):
        def name(self):
            return "Fido"

        def _tail(self):
            # Prefixing a method with an underscore implies private scope
            return "wagging"

        def __password(self):
            return 'password'  # Genius!

    def test_calling_methods_in_other_objects(self):
        rover = self.Dog()
        self.assertEqual(__, rover.name())

    def test_private_access_is_implied_but_not_enforced(self):
        rover = self.Dog()

        # This is a little rude, but legal
        self.assertEqual(__, rover._tail())

    def test_double_underscore_attribute_prefixes_cause_name_mangling(self):
        """Attributes names that start with a double underscore get
        mangled when an instance is created."""
        rover = self.Dog()
        try:
            #This may not be possible...
            password = rover.__password()
        except Exception as ex:
            self.assertEqual(__, ex.__class__.__name__)

        # But this still is!
        self.assertEqual(__, rover._Dog__password())

        # Name mangling exists to avoid name clash issues when subclassing.
        # It is not for providing effective access protection

########NEW FILE########
__FILENAME__ = about_method_bindings
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


def function():
    return "pineapple"


def function2():
    return "tractor"


class Class(object):
    def method(self):
        return "parrot"


class AboutMethodBindings(Koan):
    def test_methods_are_bound_to_an_object(self):
        obj = Class()
        self.assertEqual(__, obj.method.im_self == obj)

    def test_methods_are_also_bound_to_a_function(self):
        obj = Class()
        self.assertEqual(__, obj.method())
        self.assertEqual(__, obj.method.im_func(obj))

    def test_functions_have_attributes(self):
        self.assertEqual(__, len(dir(function)))
        self.assertEqual(__, dir(function) == dir(Class.method.im_func))

    def test_bound_methods_have_different_attributes(self):
        obj = Class()
        self.assertEqual(__, len(dir(obj.method)))

    def test_setting_attributes_on_an_unbound_function(self):
        function.cherries = 3
        self.assertEqual(__, function.cherries)

    def test_setting_attributes_on_a_bound_method_directly(self):
        obj = Class()
        try:
            obj.method.cherries = 3
        except AttributeError as ex:
            self.assertMatch(__, ex[0])

    def test_setting_attributes_on_methods_by_accessing_the_inner_function(self):
        obj = Class()
        obj.method.im_func.cherries = 3
        self.assertEqual(__, obj.method.cherries)

    def test_functions_can_have_inner_functions(self):
        function2.get_fruit = function
        self.assertEqual(__, function2.get_fruit())

    def test_inner_functions_are_unbound(self):
        function2.get_fruit = function
        try:
            cls = function2.get_fruit.im_self
        except AttributeError as ex:
            self.assertMatch(__, ex[0])

    # ------------------------------------------------------------------

    class BoundClass(object):
        def __get__(self, obj, cls):
            return (self, obj, cls)

    binding = BoundClass()

    def test_get_descriptor_resolves_attribute_binding(self):
        bound_obj, binding_owner, owner_type = self.binding
        # Look at BoundClass.__get__():
        #   bound_obj = self
        #   binding_owner = obj
        #   owner_type = cls

        self.assertEqual(__, bound_obj.__class__.__name__)
        self.assertEqual(__, binding_owner.__class__.__name__)
        self.assertEqual(AboutMethodBindings, owner_type)

    # ------------------------------------------------------------------

    class SuperColor(object):
        def __init__(self):
            self.choice = None

        def __set__(self, obj, val):
            self.choice = val

    color = SuperColor()

    def test_set_descriptor_changes_behavior_of_attribute_assignment(self):
        self.assertEqual(None, self.color.choice)
        self.color = 'purple'
        self.assertEqual(__, self.color.choice)

########NEW FILE########
__FILENAME__ = about_modules
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# This is very different to AboutModules in Ruby Koans
# Our AboutMultipleInheritance class is a little more comparable
#

from runner.koan import *

from another_local_module import *
from local_module_with_all_defined import *


class AboutModules(Koan):
    def test_importing_other_python_scripts_as_modules(self):
        import local_module  # local_module.py

        duck = local_module.Duck()
        self.assertEqual(__, duck.name)

    def test_importing_attributes_from_classes_using_from_keyword(self):
        from local_module import Duck

        duck = Duck()  # no module qualifier needed this time
        self.assertEqual(__, duck.name)

    def test_we_can_import_multiple_items_at_once(self):
        import jims, joes

        jims_dog = jims.Dog()
        joes_dog = joes.Dog()
        self.assertEqual(__, jims_dog.identify())
        self.assertEqual(__, joes_dog.identify())

    def test_importing_all_module_attributes_at_once(self):
        """
        importing all attributes at once is done like so:
            from another_local_module import *
        The import wildcard cannot be used from within classes or functions.
        """

        goose = Goose()
        hamster = Hamster()

        self.assertEqual(__, goose.name)
        self.assertEqual(__, hamster.name)

    def test_modules_hide_attributes_prefixed_by_underscores(self):
        try:
            private_squirrel = _SecretSquirrel()
        except NameError as ex:
            self.assertMatch(__, ex[0])

    def test_private_attributes_are_still_accessible_in_modules(self):
        from local_module import Duck  # local_module.py

        duck = Duck()
        self.assertEqual(__, duck._password)
        # module level attribute hiding doesn't affect class attributes
        # (unless the class itself is hidden).

    def test_a_modules_XallX_statement_limits_what_wildcards_will_match(self):
        """Examine results of from local_module_with_all_defined import *"""

        # 'Goat' is on the __all__ list
        goat = Goat()
        self.assertEqual(__, goat.name)

        # How about velociraptors?
        lizard = _Velociraptor()
        self.assertEqual(__, lizard.name)

        # SecretDuck? Never heard of her!
        try:
            duck = SecretDuck()
        except NameError as ex:
            self.assertMatch(__, ex[0])

########NEW FILE########
__FILENAME__ = about_monkey_patching
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Related to AboutOpenClasses in the Ruby Koans
#

from runner.koan import *


class AboutMonkeyPatching(Koan):
    class Dog(object):
        def bark(self):
            return "WOOF"

    def test_as_defined_dogs_do_bark(self):
        fido = self.Dog()
        self.assertEqual(__, fido.bark())

    # ------------------------------------------------------------------

    # Add a new method to an existing class.
    def test_after_patching_dogs_can_both_wag_and_bark(self):
        def wag(self):
            return "HAPPY"

        self.Dog.wag = wag

        fido = self.Dog()
        self.assertEqual(__, fido.wag())
        self.assertEqual(__, fido.bark())

    # ------------------------------------------------------------------

    def test_most_built_in_classes_cannot_be_monkey_patched(self):
        try:
            int.is_even = lambda self: (self % 2) == 0
        except StandardError as ex:
            self.assertMatch(__, ex[0])

    # ------------------------------------------------------------------

    class MyInt(int):
        pass

    def test_subclasses_of_built_in_classes_can_be_be_monkey_patched(self):
        self.MyInt.is_even = lambda self: (self % 2) == 0

        self.assertEqual(____, self.MyInt(1).is_even())
        self.assertEqual(____, self.MyInt(2).is_even())

########NEW FILE########
__FILENAME__ = about_multiple_inheritance
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Slightly based on AboutModules in the Ruby Koans
#

from runner.koan import *


class AboutMultipleInheritance(Koan):
    class Nameable(object):
        def __init__(self):
            self._name = None

        def set_name(self, new_name):
            self._name = new_name

        def here(self):
            return "In Nameable class"

    class Animal(object):
        def legs(self):
            return 4

        def can_climb_walls(self):
            return False

        def here(self):
            return "In Animal class"

    class Pig(Animal):
        def __init__(self):
            super(AboutMultipleInheritance.Animal, self).__init__()
            self._name = "Jasper"

        @property
        def name(self):
            return self._name

        def speak(self):
            return "OINK"

        def color(self):
            return 'pink'

        def here(self):
            return "In Pig class"

    class Spider(Animal):
        def __init__(self):
            super(AboutMultipleInheritance.Animal, self).__init__()
            self._name = "Boris"

        def can_climb_walls(self):
            return True

        def legs(self):
            return 8

        def color(self):
            return 'black'

        def here(self):
            return "In Spider class"

    class Spiderpig(Pig, Spider, Nameable):
        def __init__(self):
            super(AboutMultipleInheritance.Pig, self).__init__()
            super(AboutMultipleInheritance.Nameable, self).__init__()
            self._name = "Jeff"

        def speak(self):
            return "This looks like a job for Spiderpig!"

        def here(self):
            return "In Spiderpig class"

    #
    # Hierarchy:
    #               Animal
    #              /     \
    #            Pig   Spider  Nameable
    #              \      |      /
    #                 Spiderpig
    #
    # ------------------------------------------------------------------

    def test_normal_methods_are_available_in_the_object(self):
        jeff = self.Spiderpig()
        self.assertMatch(__, jeff.speak())

    def test_base_class_methods_are_also_available_in_the_object(self):
        jeff = self.Spiderpig()
        try:
            jeff.set_name("Rover")
        except:
            self.fail("This should not happen")
        self.assertEqual(____, jeff.can_climb_walls())

    def test_base_class_methods_can_affect_instance_variables_in_the_object(self):
        jeff = self.Spiderpig()
        self.assertEqual(__, jeff.name)

        jeff.set_name("Rover")
        self.assertEqual(__, jeff.name)

    def test_left_hand_side_inheritance_tends_to_be_higher_priority(self):
        jeff = self.Spiderpig()
        self.assertEqual(__, jeff.color())

    def test_super_class_methods_are_higher_priority_than_super_super_classes(self):
        jeff = self.Spiderpig()
        self.assertEqual(__, jeff.legs())

    def test_we_can_inspect_the_method_resolution_order(self):
        #
        # MRO = Method Resolution Order
        #
        mro = type(self.Spiderpig()).__mro__
        self.assertEqual('Spiderpig', mro[0].__name__)
        self.assertEqual('Pig', mro[1].__name__)
        self.assertEqual(__, mro[2].__name__)
        self.assertEqual(__, mro[3].__name__)
        self.assertEqual(__, mro[4].__name__)
        self.assertEqual(__, mro[5].__name__)

    def test_confirm_the_mro_controls_the_calling_order(self):
        jeff = self.Spiderpig()
        self.assertMatch('Spiderpig', jeff.here())

        next = super(AboutMultipleInheritance.Spiderpig, jeff)
        self.assertMatch('Pig', next.here())

        next = super(AboutMultipleInheritance.Pig, jeff)
        self.assertMatch(__, next.here())

        # Hang on a minute?!? That last class name might be a super class of
        # the 'jeff' object, but its hardly a superclass of Pig, is it?
        #
        # To avoid confusion it may help to think of super() as next_mro().

########NEW FILE########
__FILENAME__ = about_new_style_classes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutNewStyleClasses(Koan):
    class OldStyleClass:
        "An old style class"
        # Original class style have been phased out in Python 3.

    class NewStyleClass(object):
        "A new style class"
        # Introduced in Python 2.2
        #
        # Aside from this set of tests, Python Koans sticks exclusively to this
        # kind of class
        pass

    def test_new_style_classes_inherit_from_object_base_class(self):
        self.assertEqual(____, issubclass(self.NewStyleClass, object))
        self.assertEqual(____, issubclass(self.OldStyleClass, object))

    def test_new_style_classes_have_more_attributes(self):
        self.assertEqual(__, len(dir(self.OldStyleClass)))
        self.assertEqual(__, self.OldStyleClass.__doc__)
        self.assertEqual(__, self.OldStyleClass.__module__)

        self.assertEqual(__, len(dir(self.NewStyleClass)))
        # To examine the available attributes, run
        # 'dir(<Class name goes here>)'
        # from a python console

    # ------------------------------------------------------------------

    def test_old_style_classes_have_type_but_no_class_attribute(self):
        self.assertEqual(__, type(self.OldStyleClass).__name__)

        try:
            cls = self.OldStyleClass.__class__.__name__
        except Exception as ex:
            pass

        # What was that error message from the exception?
        self.assertMatch(__, ex[0])

    def test_new_style_classes_have_same_class_as_type(self):
        new_style = self.NewStyleClass()
        self.assertEqual(__, self.NewStyleClass.__class__)
        self.assertEqual(
            __,
            type(self.NewStyleClass) == self.NewStyleClass.__class__)

    # ------------------------------------------------------------------

    def test_in_old_style_instances_class_is_different_to_type(self):
        old_style = self.OldStyleClass()
        self.assertEqual(__, old_style.__class__.__name__)
        self.assertEqual(__, type(old_style).__name__)

    def test_new_style_instances_have_same_class_as_type(self):
        new_style = self.NewStyleClass()
        self.assertEqual(__, new_style.__class__.__name__)
        self.assertEqual(__, type(new_style) == new_style.__class__)

########NEW FILE########
__FILENAME__ = about_none
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutNil in the Ruby Koans
#

from runner.koan import *


class AboutNone(Koan):

    def test_none_is_an_object(self):
        "Unlike NULL in a lot of languages"
        self.assertEqual(__, isinstance(None, object))

    def test_none_is_universal(self):
        "There is only one None"
        self.assertEqual(__, None is None)

    def test_what_exception_do_you_get_when_calling_nonexistent_methods(self):
        """
        What is the Exception that is thrown when you call a method that does
        not exist?

        Hint: launch python command console and try the code in the
        block below.

        Don't worry about what 'try' and 'except' do, we'll talk about
        this later
        """
        try:
            None.some_method_none_does_not_know_about()
        except Exception as ex:
            # What exception has been caught?
            #
            # Need a recap on how to evaluate __class__ attributes?
            #   https://github.com/gregmalcolm/python_koans/wiki/Class-Attribute

            self.assertEqual(__, ex.__class__)

            # What message was attached to the exception?
            # (HINT: replace __ with part of the error message.)
            self.assertMatch(__, ex.args[0])

    def test_none_is_distinct(self):
        """
        None is distinct from other things which are False.
        """
        self.assertEqual(____, None is not 0)
        self.assertEqual(____, None is not False)

########NEW FILE########
__FILENAME__ = about_packages
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# This is very different to AboutModules in Ruby Koans
# Our AboutMultipleInheritance class is a little more comparable
#

from runner.koan import *

#
# Package hierarchy of Python Koans project:
#
# contemplate_koans.py
# koans/
#     __init__.py
#     about_asserts.py
#     about_attribute_access.py
#     about_class_attributes.py
#     about_classes.py
#     ...
#     a_package_folder/
#         __init__.py
#         a_module.py


class AboutPackages(Koan):
    def test_subfolders_can_form_part_of_a_module_package(self):
        # Import ./a_package_folder/a_module.py
        from a_package_folder.a_module import Duck

        duck = Duck()
        self.assertEqual(__, duck.name)

    def test_subfolders_become_modules_if_they_have_an_init_module(self):
        # Import ./a_package_folder/__init__.py
        from a_package_folder import an_attribute

        self.assertEqual(__, an_attribute)

    def test_subfolders_without_an_init_module_are_not_part_of_the_package(self):
        # Import ./a_normal_folder/
        try:
            import a_normal_folder
        except ImportError as ex:
            self.assertMatch(__, ex[0])

    # ------------------------------------------------------------------

    def test_use_absolute_imports_to_import_upper_level_modules(self):
        # Import /contemplate_koans.py
        import contemplate_koans

        self.assertEqual(__, contemplate_koans.__name__)

        # contemplate_koans.py is the root module in this package because its
        # the first python module called in koans.
        #
        # If contemplate_koan.py was based in a_package_folder that would be
        # the root folder, which would make reaching the koans folder
        # almost impossible. So always leave the starting python script in
        # a folder which can reach everything else.

    def test_import_a_module_in_a_subfolder_using_an_absolute_path(self):
        # Import contemplate_koans.py/koans/a_package_folder/a_module.py
        from koans.a_package_folder.a_module import Duck

        self.assertEqual(__, Duck.__module__)

########NEW FILE########
__FILENAME__ = about_proxy_object_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Project: Create a Proxy Class
#
# In this assignment, create a proxy class (one is started for you
# below).  You should be able to initialize the proxy object with any
# object.  Any attributes called on the proxy object should be forwarded
# to the target object.  As each attribute call is sent, the proxy should
# record the name of the attribute sent.
#
# The proxy class is started for you.  You will need to add a method
# missing handler and any other supporting methods.  The specification
# of the Proxy class is given in the AboutProxyObjectProject koan.

# Note: This is a bit trickier than its Ruby Koans counterpart, but you
# can do it!

from runner.koan import *


class Proxy(object):
    def __init__(self, target_object):
        # WRITE CODE HERE

        #initialize '_obj' attribute last. Trust me on this!
        self._obj = target_object

    # WRITE CODE HERE


# The proxy object should pass the following Koan:
#
class AboutProxyObjectProject(Koan):
    def test_proxy_method_returns_wrapped_object(self):
        # NOTE: The Television class is defined below
        tv = Proxy(Television())

        self.assertTrue(isinstance(tv, Proxy))

    def test_tv_methods_still_perform_their_function(self):
        tv = Proxy(Television())

        tv.channel = 10
        tv.power()

        self.assertEqual(10, tv.channel)
        self.assertTrue(tv.is_on())

    def test_proxy_records_messages_sent_to_tv(self):
        tv = Proxy(Television())

        tv.power()
        tv.channel = 10

        self.assertEqual(['power', 'channel'], tv.messages())

    def test_proxy_handles_invalid_messages(self):
        tv = Proxy(Television())

        ex = None
        try:
            tv.no_such_method()
        except AttributeError as ex:
            pass

        self.assertEqual(AttributeError, type(ex))

    def test_proxy_reports_methods_have_been_called(self):
        tv = Proxy(Television())

        tv.power()
        tv.power()

        self.assertTrue(tv.was_called('power'))
        self.assertFalse(tv.was_called('channel'))

    def test_proxy_counts_method_calls(self):
        tv = Proxy(Television())

        tv.power()
        tv.channel = 48
        tv.power()

        self.assertEqual(2, tv.number_of_times_called('power'))
        self.assertEqual(1, tv.number_of_times_called('channel'))
        self.assertEqual(0, tv.number_of_times_called('is_on'))

    def test_proxy_can_record_more_than_just_tv_objects(self):
        proxy = Proxy("Py Ohio 2010")

        result = proxy.upper()

        self.assertEqual("PY OHIO 2010", result)

        result = proxy.split()

        self.assertEqual(["Py", "Ohio", "2010"], result)
        self.assertEqual(['upper', 'split'], proxy.messages())


# ====================================================================
# The following code is to support the testing of the Proxy class.  No
# changes should be necessary to anything below this comment.

# Example class using in the proxy testing above.
class Television(object):
    def __init__(self):
        self._channel = None
        self._power = None

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value

    def power(self):
        if self._power == 'on':
            self._power = 'off'
        else:
            self._power = 'on'

    def is_on(self):
        return self._power == 'on'


# Tests for the Television class.  All of theses tests should pass.
class TelevisionTest(Koan):
    def test_it_turns_on(self):
        tv = Television()

        tv.power()
        self.assertTrue(tv.is_on())

    def test_it_also_turns_off(self):
        tv = Television()

        tv.power()
        tv.power()

        self.assertFalse(tv.is_on())

    def test_edge_case_on_off(self):
        tv = Television()

        tv.power()
        tv.power()
        tv.power()

        self.assertTrue(tv.is_on())

        tv.power()

        self.assertFalse(tv.is_on())

    def test_can_set_the_channel(self):
        tv = Television()

        tv.channel = 11
        self.assertEqual(11, tv.channel)

########NEW FILE########
__FILENAME__ = about_regex
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

import re


class AboutRegex(Koan):
    """
        These koans are based on Ben's book: Regular Expressions in 10
        minutes. I found this book very useful, so I decided to write
        a koan file in order to practice everything it taught me.
        http://www.forta.com/books/0672325667/
    """

    def test_matching_literal_text(self):
        """
            Lesson 1 Matching Literal String
        """
        string = "Hello, my name is Felix and these koans are based " + \
        "on Ben's book: Regular Expressions in 10 minutes."
        m = re.search(__, string)
        self.assertTrue(
            m and m.group(0) and
                m.group(0) == 'Felix',
            "I want my name")

    def test_matching_literal_text_how_many(self):
        """
            Lesson 1 -- How many matches?

            The default behaviour of most regular expression engines is
            to return just the first match. In python you have the
            following options:

                match()    -->  Determine if the RE matches at the
                                beginning of the string.
                search()   -->  Scan through a string, looking for any
                                location where this RE matches.
                findall()  -->  Find all substrings where the RE
                                matches, and return them as a list.
                finditer() -->  Find all substrings where the RE
                                matches, and return them as an iterator.
        """
        string = ("Hello, my name is Felix and these koans are based " +
            "on Ben's book: Regular Expressions in 10 minutes. " +
            "Repeat My name is Felix")
        m = re.match('Felix', string)  # TIP: match may not be the best option

        # I want to know how many times my name appears
        self.assertEqual(m, __)

    def test_matching_literal_text_not_case_sensitivity(self):
        """
            Lesson 1 -- Matching Literal String non case sensitivity.
            Most regex implementations also support matches that are not
            case sensitive. In python you can use re.IGNORECASE, in
            Javascript you can specify the optional i flag. In Ben's
            book you can see more languages.

        """
        string = "Hello, my name is Felix or felix and this koan " + \
            "is based on Ben's book: Regular Expressions in 10 minutes."

        self.assertEqual(re.findall("felix", string), __)
        self.assertEqual(re.findall("felix", string, re.IGNORECASE), __)

    def test_matching_any_character(self):
        """
            Lesson 1: Matching any character

            `.` matches any character: alphabetic characters, digits,
            and punctuation.
        """
        string = "pecks.xlx\n"    \
                + "orders1.xls\n" \
                + "apec1.xls\n"   \
                + "na1.xls\n"     \
                + "na2.xls\n"     \
                + "sa1.xls"

        # I want to find all uses of myArray
        change_this_search_string = 'a..xlx'
        self.assertEquals(
            len(re.findall(change_this_search_string, string)),
            3)

    def test_matching_set_character(self):
        """
            Lesson 2 -- Matching sets of characters

            A set of characters is defined using the metacharacters
            `[` and `]`. Everything between them is part of the set, and
            any single one of the set members will match.
        """
        string = "sales.xlx\n"    \
                + "sales1.xls\n"  \
                + "orders3.xls\n" \
                + "apac1.xls\n" \
                + "sales2.xls\n"  \
                + "na1.xls\n"  \
                + "na2.xls\n"  \
                + "sa1.xls\n"  \
                + "ca1.xls"
        # I want to find all files for North America(na) or South
        # America(sa), but not (ca) TIP you can use the pattern .a.
        # which matches in above test but in this case matches more than
        # you want
        change_this_search_string = '[nsc]a[2-9].xls'
        self.assertEquals(
            len(re.findall(change_this_search_string, string)),
            3)

    def test_anything_but_matching(self):
        """
            Lesson 2 -- Using character set ranges
            Occasionally, you'll have a list of characters that you don't
            want to match. Character sets can be negated using the ^
            metacharacter.

        """
        string = "sales.xlx\n"    \
                + "sales1.xls\n"  \
                + "orders3.xls\n" \
                + "apac1.xls\n" \
                + "sales2.xls\n"  \
                + "sales3.xls\n"  \
                + "europe2.xls\n"  \
                + "sam.xls\n"  \
                + "na1.xls\n"  \
                + "na2.xls\n"  \
                + "sa1.xls\n"  \
                + "ca1.xls"

        # I want to find the name 'sam'
        change_this_search_string = '[^nc]am'
        self.assertEquals(
            re.findall(change_this_search_string, string),
            ['sam.xls'])

########NEW FILE########
__FILENAME__ = about_scope
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

import jims
import joes

counter = 0  # Global


class AboutScope(Koan):
    #
    # NOTE:
    #   Look in jims.py and joes.py to see definitions of Dog used
    #   for this set of tests
    #

    def test_dog_is_not_available_in_the_current_scope(self):
        try:
            fido = Dog()
        except Exception as ex:
            self.assertMatch(__, ex[0])

    def test_you_can_reference_nested_classes_using_the_scope_operator(self):
        fido = jims.Dog()
        # name 'jims' module name is taken from jims.py filename

        rover = joes.Dog()
        self.assertEqual(__, fido.identify())
        self.assertEqual(__, rover.identify())

        self.assertEqual(____, type(fido) == type(rover))
        self.assertEqual(____, jims.Dog == joes.Dog)

    # ------------------------------------------------------------------

    class str(object):
        pass

    def test_bare_bones_class_names_do_not_assume_the_current_scope(self):
        self.assertEqual(____, AboutScope.str == str)

    def test_nested_string_is_not_the_same_as_the_system_string(self):
        self.assertEqual(____, self.str == type("HI"))

    def test_str_without_self_prefix_stays_in_the_global_scope(self):
        self.assertEqual(____, str == type("HI"))

    # ------------------------------------------------------------------

    PI = 3.1416

    def test_constants_are_defined_with_an_initial_uppercase_letter(self):
        self.assertAlmostEqual(_____, self.PI)
        # Note, floating point numbers in python are not precise.
        # assertAlmostEqual will check that it is 'close enough'

    def test_constants_are_assumed_by_convention_only(self):
        self.PI = "rhubarb"
        self.assertEqual(_____, self.PI)
        # There aren't any real constants in python. Its up to the developer
        # to keep to the convention and not modify them.

    # ------------------------------------------------------------------

    def increment_using_local_counter(self, counter):
        counter = counter + 1

    def increment_using_global_counter(self):
        global counter
        counter = counter + 1

    def test_incrementing_with_local_counter(self):
        global counter
        start = counter
        self.increment_using_local_counter(start)
        self.assertEqual(____, counter == start + 1)

    def test_incrementing_with_global_counter(self):
        global counter
        start = counter
        self.increment_using_global_counter()
        self.assertEqual(____, counter == start + 1)

    # ------------------------------------------------------------------

    global deadly_bingo
    deadly_bingo = [4, 8, 15, 16, 23, 42]

    def test_global_attributes_can_be_created_in_the_middle_of_a_class(self):
        self.assertEqual(__, deadly_bingo[5])

########NEW FILE########
__FILENAME__ = about_scoring_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


# Greed is a dice game where you roll up to five dice to accumulate
# points.  The following "score" function will be used calculate the
# score of a single roll of the dice.
#
# A greed roll is scored as follows:
#
# * A set of three ones is 1000 points
#
# * A set of three numbers (other than ones) is worth 100 times the
#   number. (e.g. three fives is 500 points).
#
# * A one (that is not part of a set of three) is worth 100 points.
#
# * A five (that is not part of a set of three) is worth 50 points.
#
# * Everything else is worth 0 points.
#
#
# Examples:
#
# score([1, 1, 1, 5, 1]) => 1150 points
# score([2, 3, 4, 6, 2]) => 0 points
# score([3, 4, 5, 3, 3]) => 350 points
# score([1, 5, 1, 2, 4]) => 250 points
#
# More scoring examples are given in the tests below:
#
# Your goal is to write the score method.

def score(dice):
    # You need to write this method
    pass


class AboutScoringProject(Koan):
    def test_score_of_an_empty_list_is_zero(self):
        self.assertEqual(0, score([]))

    def test_score_of_a_single_roll_of_5_is_50(self):
        self.assertEqual(50, score([5]))

    def test_score_of_a_single_roll_of_1_is_100(self):
        self.assertEqual(100, score([1]))

    def test_score_of_multiple_1s_and_5s_is_the_sum_of_individual_scores(self):
        self.assertEqual(300, score([1, 5, 5, 1]))

    def test_score_of_single_2s_3s_4s_and_6s_are_zero(self):
        self.assertEqual(0, score([2, 3, 4, 6]))

    def test_score_of_a_triple_1_is_1000(self):
        self.assertEqual(1000, score([1, 1, 1]))

    def test_score_of_other_triples_is_100x(self):
        self.assertEqual(200, score([2, 2, 2]))
        self.assertEqual(300, score([3, 3, 3]))
        self.assertEqual(400, score([4, 4, 4]))
        self.assertEqual(500, score([5, 5, 5]))
        self.assertEqual(600, score([6, 6, 6]))

    def test_score_of_mixed_is_sum(self):
        self.assertEqual(250, score([2, 5, 2, 2, 3]))
        self.assertEqual(550, score([5, 5, 5, 5]))
        self.assertEqual(1150, score([1, 1, 1, 5, 1]))

    def test_ones_not_left_out(self):
        self.assertEqual(300, score([1, 2, 2, 2]))
        self.assertEqual(350, score([1, 5, 2, 2, 2]))

########NEW FILE########
__FILENAME__ = about_sets
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutSets(Koan):
    def test_sets_make_keep_lists_unique(self):
        highlanders = ['MacLeod', 'Ramirez', 'MacLeod', 'Matunas',
            'MacLeod', 'Malcolm', 'MacLeod']

        there_can_only_be_only_one = set(highlanders)

        self.assertEqual(__, there_can_only_be_only_one)

    def test_sets_are_unordered(self):
        self.assertEqual(set([__, __, __, __, __]), set('12345'))

    def test_convert_the_set_into_a_list_to_sort_it(self):
        self.assertEqual(__, sorted(set('13245')))

    # ------------------------------------------------------------------

    def test_set_have_arithmetic_operators(self):
        scotsmen = set(['MacLeod', 'Wallace', 'Willie'])
        warriors = set(['MacLeod', 'Wallace', 'Leonidas'])

        self.assertEqual(__, scotsmen - warriors)
        self.assertEqual(__, scotsmen | warriors)
        self.assertEqual(__, scotsmen & warriors)
        self.assertEqual(__, scotsmen ^ warriors)

    # ------------------------------------------------------------------

    def test_we_can_query_set_membership(self):
        self.assertEqual(__, 127 in set([127, 0, 0, 1]))
        self.assertEqual(__, 'cow' not in set('apocalypse now'))

    def test_we_can_compare_subsets(self):
        self.assertEqual(__, set('cake') <= set('cherry cake'))
        self.assertEqual(__, set('cake').issubset(set('cherry cake')))

        self.assertEqual(__, set('cake') > set('pie'))

########NEW FILE########
__FILENAME__ = about_strings
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutStrings(Koan):

    def test_double_quoted_strings_are_strings(self):
        string = "Hello, world."
        self.assertEqual(__, isinstance(string, basestring))

    def test_single_quoted_strings_are_also_strings(self):
        string = 'Goodbye, world.'
        self.assertEqual(__, isinstance(string, basestring))

    def test_triple_quote_strings_are_also_strings(self):
        string = """Howdy, world!"""
        self.assertEqual(__, isinstance(string, basestring))

    def test_triple_single_quotes_work_too(self):
        string = '''Bonjour tout le monde!'''
        self.assertEqual(__, isinstance(string, basestring))

    def test_raw_strings_are_also_strings(self):
        string = r"Konnichi wa, world!"
        self.assertEqual(__, isinstance(string, basestring))

    def test_use_single_quotes_to_create_string_with_double_quotes(self):
        string = 'He said, "Go Away."'
        self.assertEqual(__, string)

    def test_use_double_quotes_to_create_strings_with_single_quotes(self):
        string = "Don't"
        self.assertEqual(__, string)

    def test_use_backslash_for_escaping_quotes_in_strings(self):
        a = "He said, \"Don't\""
        b = 'He said, "Don\'t"'
        self.assertEqual(__, (a == b))

    def test_use_backslash_at_the_end_of_a_line_to_continue_onto_the_next_line(self):
        string = "It was the best of times,\n\
It was the worst of times."
        self.assertEqual(__, len(string))

    def test_triple_quoted_strings_can_span_lines(self):
        string = """
Howdy,
world!
"""
        self.assertEqual(__, len(string))

    def test_triple_quoted_strings_need_less_escaping(self):
        a = "Hello \"world\"."
        b = """Hello "world"."""
        self.assertEqual(__, (a == b))

    def test_escaping_quotes_at_the_end_of_triple_quoted_string(self):
        string = """Hello "world\""""
        self.assertEqual(__, string)

    def test_plus_concatenates_strings(self):
        string = "Hello, " + "world"
        self.assertEqual(__, string)

    def test_adjacent_strings_are_concatenated_automatically(self):
        string = "Hello" ", " "world"
        self.assertEqual(__, string)

    def test_plus_will_not_modify_original_strings(self):
        hi = "Hello, "
        there = "world"
        string = hi + there
        self.assertEqual(__, hi)
        self.assertEqual(__, there)

    def test_plus_equals_will_append_to_end_of_string(self):
        hi = "Hello, "
        there = "world"
        hi += there
        self.assertEqual(__, hi)

    def test_plus_equals_also_leaves_original_string_unmodified(self):
        original = "Hello, "
        hi = original
        there = "world"
        hi += there
        self.assertEqual(__, original)

    def test_most_strings_interpret_escape_characters(self):
        string = "\n"
        self.assertEqual('\n', string)
        self.assertEqual("""\n""", string)
        self.assertEqual(__, len(string))

########NEW FILE########
__FILENAME__ = about_string_manipulation
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutStringManipulation(Koan):

    def test_use_format_to_interpolate_variables(self):
        value1 = 'one'
        value2 = 2
        string = "The values are {0} and {1}".format(value1, value2)
        self.assertEqual(__, string)

    def test_formatted_values_can_be_shown_in_any_order_or_be_repeated(self):
        value1 = 'doh'
        value2 = 'DOH'
        string = "The values are {1}, {0}, {0} and {1}!".format(value1, value2)
        self.assertEqual(__, string)

    def test_any_python_expression_may_be_interpolated(self):
        import math  # import a standard python module with math functions

        decimal_places = 4
        string = "The square root of 5 is {0:.{1}f}".format(math.sqrt(5), \
            decimal_places)
        self.assertEqual(__, string)

    def test_you_can_get_a_substring_from_a_string(self):
        string = "Bacon, lettuce and tomato"
        self.assertEqual(__, string[7:10])

    def test_you_can_get_a_single_character_from_a_string(self):
        string = "Bacon, lettuce and tomato"
        self.assertEqual(__, string[1])

    def test_single_characters_can_be_represented_by_integers(self):
        self.assertEqual(__, ord('a'))
        self.assertEqual(__, ord('b') == (ord('a') + 1))

    def test_strings_can_be_split(self):
        string = "Sausage Egg Cheese"
        words = string.split()
        self.assertEqual([__, __, __], words)

    def test_strings_can_be_split_with_different_patterns(self):
        import re  # import python regular expression library

        string = "the,rain;in,spain"
        pattern = re.compile(',|;')

        words = pattern.split(string)

        self.assertEqual([__, __, __, __], words)

        # `pattern` is a Python regular expression pattern which matches
        # ',' or ';'

    def test_raw_strings_do_not_interpret_escape_characters(self):
        string = r'\n'
        self.assertNotEqual('\n', string)
        self.assertEqual(__, string)
        self.assertEqual(__, len(string))

        # Useful in regular expressions, file paths, URLs, etc.

    def test_strings_can_be_joined(self):
        words = ["Now", "is", "the", "time"]
        self.assertEqual(__, ' '.join(words))

    def test_strings_can_change_case(self):
        self.assertEqual(__, 'guido'.capitalize())
        self.assertEqual(__, 'guido'.upper())
        self.assertEqual(__, 'TimBot'.lower())
        self.assertEqual(__, 'guido van rossum'.title())
        self.assertEqual(__, 'ToTaLlY aWeSoMe'.swapcase())

########NEW FILE########
__FILENAME__ = about_triangle_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

# You need to write the triangle method in the file 'triangle.py'
from triangle import *


class AboutTriangleProject(Koan):
    def test_equilateral_triangles_have_equal_sides(self):
        self.assertEqual('equilateral', triangle(2, 2, 2))
        self.assertEqual('equilateral', triangle(10, 10, 10))

    def test_isosceles_triangles_have_exactly_two_sides_equal(self):
        self.assertEqual('isosceles', triangle(3, 4, 4))
        self.assertEqual('isosceles', triangle(4, 3, 4))
        self.assertEqual('isosceles', triangle(4, 4, 3))
        self.assertEqual('isosceles', triangle(10, 10, 2))

    def test_scalene_triangles_have_no_equal_sides(self):
        self.assertEqual('scalene', triangle(3, 4, 5))
        self.assertEqual('scalene', triangle(10, 11, 12))
        self.assertEqual('scalene', triangle(5, 4, 2))

########NEW FILE########
__FILENAME__ = about_triangle_project2
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

# You need to finish implementing triangle() in the file 'triangle.py'
from triangle import *


class AboutTriangleProject2(Koan):
    # The first assignment did not talk about how to handle errors.
    # Let's handle that part now.
    def test_illegal_triangles_throw_exceptions(self):
        # Calls triangle(0, 0, 0)
        self.assertRaises(TriangleError, triangle, 0, 0, 0)

        self.assertRaises(TriangleError, triangle, 3, 4, -5)
        self.assertRaises(TriangleError, triangle, 1, 1, 3)
        self.assertRaises(TriangleError, triangle, 2, 5, 2)

########NEW FILE########
__FILENAME__ = about_true_and_false
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutTrueAndFalse(Koan):
    def truth_value(self, condition):
        if condition:
            return 'true stuff'
        else:
            return 'false stuff'

    def test_true_is_treated_as_true(self):
        self.assertEqual(__, self.truth_value(True))

    def test_false_is_treated_as_false(self):
        self.assertEqual(__, self.truth_value(False))

    def test_none_is_treated_as_false(self):
        self.assertEqual(__, self.truth_value(None))

    def test_zero_is_treated_as_false(self):
        self.assertEqual(__, self.truth_value(0))

    def test_empty_collections_are_treated_as_false(self):
        self.assertEqual(__, self.truth_value([]))
        self.assertEqual(__, self.truth_value(()))
        self.assertEqual(__, self.truth_value({}))
        self.assertEqual(__, self.truth_value(set()))

    def test_blank_strings_are_treated_as_false(self):
        self.assertEqual(__, self.truth_value(""))

    def test_everything_else_is_treated_as_true(self):
        self.assertEqual(__, self.truth_value(1))
        self.assertEqual(__, self.truth_value(1,))
        self.assertEqual(
            __,
            self.truth_value("Python is named after Monty Python"))
        self.assertEqual(__, self.truth_value(' '))
        self.assertEqual(__, self.truth_value('0'))

########NEW FILE########
__FILENAME__ = about_tuples
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutTuples(Koan):
    def test_creating_a_tuple(self):
        count_of_three = (1, 2, 5)
        self.assertEqual(__, count_of_three[2])

    def test_tuples_are_immutable_so_item_assignment_is_not_possible(self):
        count_of_three = (1, 2, 5)
        try:
            count_of_three[2] = "three"
        except TypeError as ex:
            self.assertMatch(__, ex[0])

    def test_tuples_are_immutable_so_appending_is_not_possible(self):
        count_of_three = (1, 2, 5)
        try:
            count_of_three.append("boom")
        except Exception as ex:
            self.assertEqual(AttributeError, type(ex))

            # Note, assertMatch() uses regular expression pattern matching,
            # so you don't have to copy the whole message.
            self.assertMatch(__, ex[0])

        # Tuples are less flexible than lists, but faster.

    def test_tuples_can_only_be_changed_through_replacement(self):
        count_of_three = (1, 2, 5)

        list_count = list(count_of_three)
        list_count.append("boom")
        count_of_three = tuple(list_count)

        self.assertEqual(__, count_of_three)

    def test_tuples_of_one_look_peculiar(self):
        self.assertEqual(__, (1).__class__)
        self.assertEqual(__, (1,).__class__)
        self.assertEqual(__, ("Hello comma!", ))

    def test_tuple_constructor_can_be_surprising(self):
        self.assertEqual(__, tuple("Surprise!"))

    def test_creating_empty_tuples(self):
        self.assertEqual(__, ())
        self.assertEqual(__, tuple())  # Sometimes less confusing

    def test_tuples_can_be_embedded(self):
        lat = (37, 14, 6, 'N')
        lon = (115, 48, 40, 'W')
        place = ('Area 51', lat, lon)
        self.assertEqual(__, place)

    def test_tuples_are_good_for_representing_records(self):
        locations = [
            ("Illuminati HQ", (38, 52, 15.56, 'N'), (77, 3, 21.46, 'W')),
            ("Stargate B", (41, 10, 43.92, 'N'), (1, 49, 34.29, 'W')),
        ]

        locations.append(
            ("Cthulhu", (26, 40, 1, 'N'), (70, 45, 7, 'W'))
        )

        self.assertEqual(__, locations[2][0])
        self.assertEqual(__, locations[0][1][2])

########NEW FILE########
__FILENAME__ = about_with_statements
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutSandwichCode in the Ruby Koans
#

from runner.koan import *

import re  # For regular expression string comparisons


class AboutWithStatements(Koan):
    def count_lines(self, file_name):
        try:
            f = open(file_name)
            try:
                return len(f.readlines())
            finally:
                f.close()
        except IOError:
            # should never happen
            self.fail()

    def test_counting_lines(self):
        self.assertEqual(__, self.count_lines("example_file.txt"))

    # ------------------------------------------------------------------

    def find_line(self, file_name):
        try:
            f = open(file_name)
            try:
                for line in f.readlines():
                    match = re.search('e', line)
                    if match:
                        return line
            finally:
                f.close()
        except IOError:
            # should never happen
            self.fail()

    def test_finding_lines(self):
        self.assertEqual(__, self.find_line("example_file.txt"))

    ## ------------------------------------------------------------------
    ## THINK ABOUT IT:
    ##
    ## The count_lines and find_line are similar, and yet different.
    ## They both follow the pattern of "sandwich code".
    ##
    ## Sandwich code is code that comes in three parts: (1) the top slice
    ## of bread, (2) the meat, and (3) the bottom slice of bread.
    ## The bread part of the sandwich almost always goes together, but
    ## the meat part changes all the time.
    ##
    ## Because the changing part of the sandwich code is in the middle,
    ## abstracting the top and bottom bread slices to a library can be
    ## difficult in many languages.
    ##
    ## (Aside for C++ programmers: The idiom of capturing allocated
    ## pointers in a smart pointer constructor is an attempt to deal with
    ## the problem of sandwich code for resource allocation.)
    ##
    ## Python solves the problem using Context Managers. Consider the
    ## following code:
    ##

    class FileContextManager():
        def __init__(self, file_name):
            self._file_name = file_name
            self._file = None

        def __enter__(self):
            self._file = open(self._file_name)
            return self._file

        def __exit__(self, cls, value, tb):
            self._file.close()

    # Now we write:

    def count_lines2(self, file_name):
        with self.FileContextManager(file_name) as f:
            return len(f.readlines())

    def test_counting_lines2(self):
        self.assertEqual(__, self.count_lines2("example_file.txt"))

    # ------------------------------------------------------------------

    def find_line2(self, file_name):
        # Rewrite find_line using the Context Manager.
        pass

    def test_finding_lines2(self):
        self.assertEqual(__, self.find_line2("example_file.txt"))
        self.assertNotEqual(None, self.find_line2("example_file.txt"))

    # ------------------------------------------------------------------

    def count_lines3(self, file_name):
        with open(file_name) as f:
            return len(f.readlines())

    def test_open_already_has_its_own_built_in_context_manager(self):
        self.assertEqual(__, self.count_lines3("example_file.txt"))

########NEW FILE########
__FILENAME__ = another_local_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Goose(object):
    @property
    def name(self):
        return "Mr Stabby"


class Hamster(object):
    @property
    def name(self):
        return "Phil"


class _SecretSquirrel(object):
    @property
    def name(self):
        return "Mr Anonymous"

########NEW FILE########
__FILENAME__ = a_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Duck(object):
    @property
    def name(self):
        return "Howard"
########NEW FILE########
__FILENAME__ = a_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Duck(object):
    @property
    def name(self):
        return "Donald"
########NEW FILE########
__FILENAME__ = jims
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Dog(object):
    def identify(self):
        return "jims dog"

########NEW FILE########
__FILENAME__ = joes
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Dog(object):
    def identify(self):
        return "joes dog"

########NEW FILE########
__FILENAME__ = local_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Duck(object):
    def __init__(self):
        self._password = 'password'  # Genius!

    @property
    def name(self):
        return "Daffy"

########NEW FILE########
__FILENAME__ = local_module_with_all_defined
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = (
    'Goat',
    '_Velociraptor'
)


class Goat(object):
    @property
    def name(self):
        return "George"


class _Velociraptor(object):
    @property
    def name(self):
        return "Cuddles"


class SecretDuck(object):
    @property
    def name(self):
        return "None of your business"

########NEW FILE########
__FILENAME__ = triangle
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Triangle Project Code.


# triangle(a, b, c) analyzes the lengths of the sides of a triangle
# (represented by a, b and c) and returns the type of triangle.
#
# It returns:
#   'equilateral'  if all sides are equal
#   'isosceles'    if exactly 2 sides are equal
#   'scalene'      if no sides are equal
#
# The tests for this method can be found in
#   about_triangle_project.py
# and
#   about_triangle_project_2.py
#
def triangle(a, b, c):
    # DELETE 'PASS' AND WRITE THIS CODE
    pass


# Error class used in part 2.  No need to change this code.
class TriangleError(StandardError):
    pass

########NEW FILE########
__FILENAME__ = ansi
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
'''
This module generates ANSI character codes to printing colors to terminals.
See: http://en.wikipedia.org/wiki/ANSI_escape_code
'''

CSI = '\033['

def code_to_chars(code):
    return CSI + str(code) + 'm'

class AnsiCodes(object):
    def __init__(self, codes):
        for name in dir(codes):
            if not name.startswith('_'):
                value = getattr(codes, name)
                setattr(self, name, code_to_chars(value))

class AnsiFore:
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37
    RESET   = 39

class AnsiBack:
    BLACK   = 40
    RED     = 41
    GREEN   = 42
    YELLOW  = 43
    BLUE    = 44
    MAGENTA = 45
    CYAN    = 46
    WHITE   = 47
    RESET   = 49

class AnsiStyle:
    BRIGHT    = 1
    DIM       = 2
    NORMAL    = 22
    RESET_ALL = 0

Fore = AnsiCodes( AnsiFore )
Back = AnsiCodes( AnsiBack )
Style = AnsiCodes( AnsiStyle )


########NEW FILE########
__FILENAME__ = ansitowin32
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
import re
import sys

from .ansi import AnsiFore, AnsiBack, AnsiStyle, Style
from .winterm import WinTerm, WinColor, WinStyle
from .win32 import windll


if windll is not None:
    winterm = WinTerm()


def is_a_tty(stream):
    return hasattr(stream, 'isatty') and stream.isatty()


class StreamWrapper(object):
    '''
    Wraps a stream (such as stdout), acting as a transparent proxy for all
    attribute access apart from method 'write()', which is delegated to our
    Converter instance.
    '''
    def __init__(self, wrapped, converter):
        # double-underscore everything to prevent clashes with names of
        # attributes on the wrapped stream object.
        self.__wrapped = wrapped
        self.__convertor = converter

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def write(self, text):
        self.__convertor.write(text)


class AnsiToWin32(object):
    '''
    Implements a 'write()' method which, on Windows, will strip ANSI character
    sequences from the text, and if outputting to a tty, will convert them into
    win32 function calls.
    '''
    ANSI_RE = re.compile('\033\[((?:\d|;)*)([a-zA-Z])')

    def __init__(self, wrapped, convert=None, strip=None, autoreset=False):
        # The wrapped stream (normally sys.stdout or sys.stderr)
        self.wrapped = wrapped

        # should we reset colors to defaults after every .write()
        self.autoreset = autoreset

        # create the proxy wrapping our output stream
        self.stream = StreamWrapper(wrapped, self)

        on_windows = sys.platform.startswith('win')

        # should we strip ANSI sequences from our output?
        if strip is None:
            strip = on_windows
        self.strip = strip

        # should we should convert ANSI sequences into win32 calls?
        if convert is None:
            convert = on_windows and is_a_tty(wrapped)
        self.convert = convert

        # dict of ansi codes to win32 functions and parameters
        self.win32_calls = self.get_win32_calls()

        # are we wrapping stderr?
        self.on_stderr = self.wrapped is sys.stderr


    def should_wrap(self):
        '''
        True if this class is actually needed. If false, then the output
        stream will not be affected, nor will win32 calls be issued, so
        wrapping stdout is not actually required. This will generally be
        False on non-Windows platforms, unless optional functionality like
        autoreset has been requested using kwargs to init()
        '''
        return self.convert or self.strip or self.autoreset


    def get_win32_calls(self):
        if self.convert and winterm:
            return {
                AnsiStyle.RESET_ALL: (winterm.reset_all, ),
                AnsiStyle.BRIGHT: (winterm.style, WinStyle.BRIGHT),
                AnsiStyle.DIM: (winterm.style, WinStyle.NORMAL),
                AnsiStyle.NORMAL: (winterm.style, WinStyle.NORMAL),
                AnsiFore.BLACK: (winterm.fore, WinColor.BLACK),
                AnsiFore.RED: (winterm.fore, WinColor.RED),
                AnsiFore.GREEN: (winterm.fore, WinColor.GREEN),
                AnsiFore.YELLOW: (winterm.fore, WinColor.YELLOW),
                AnsiFore.BLUE: (winterm.fore, WinColor.BLUE),
                AnsiFore.MAGENTA: (winterm.fore, WinColor.MAGENTA),
                AnsiFore.CYAN: (winterm.fore, WinColor.CYAN),
                AnsiFore.WHITE: (winterm.fore, WinColor.GREY),
                AnsiFore.RESET: (winterm.fore, ),
                AnsiBack.BLACK: (winterm.back, WinColor.BLACK),
                AnsiBack.RED: (winterm.back, WinColor.RED),
                AnsiBack.GREEN: (winterm.back, WinColor.GREEN),
                AnsiBack.YELLOW: (winterm.back, WinColor.YELLOW),
                AnsiBack.BLUE: (winterm.back, WinColor.BLUE),
                AnsiBack.MAGENTA: (winterm.back, WinColor.MAGENTA),
                AnsiBack.CYAN: (winterm.back, WinColor.CYAN),
                AnsiBack.WHITE: (winterm.back, WinColor.GREY),
                AnsiBack.RESET: (winterm.back, ),
            }


    def write(self, text):
        if self.strip or self.convert:
            self.write_and_convert(text)
        else:
            self.wrapped.write(text)
            self.wrapped.flush()
        if self.autoreset:
            self.reset_all()


    def reset_all(self):
        if self.convert:
            self.call_win32('m', (0,))
        elif is_a_tty(self.wrapped):
            self.wrapped.write(Style.RESET_ALL)


    def write_and_convert(self, text):
        '''
        Write the given text to our wrapped stream, stripping any ANSI
        sequences from the text, and optionally converting them into win32
        calls.
        '''
        cursor = 0
        for match in self.ANSI_RE.finditer(text):
            start, end = match.span()
            self.write_plain_text(text, cursor, start)
            self.convert_ansi(*match.groups())
            cursor = end
        self.write_plain_text(text, cursor, len(text))


    def write_plain_text(self, text, start, end):
        if start < end:
            self.wrapped.write(text[start:end])
            self.wrapped.flush()


    def convert_ansi(self, paramstring, command):
        if self.convert:
            params = self.extract_params(paramstring)
            self.call_win32(command, params)


    def extract_params(self, paramstring):
        def split(paramstring):
            for p in paramstring.split(';'):
                if p != '':
                    yield int(p)
        return tuple(split(paramstring))


    def call_win32(self, command, params):
        if params == []:
            params = [0]
        if command == 'm':
            for param in params:
                if param in self.win32_calls:
                    func_args = self.win32_calls[param]
                    func = func_args[0]
                    args = func_args[1:]
                    kwargs = dict(on_stderr=self.on_stderr)
                    func(*args, **kwargs)
        elif command in ('H', 'f'): # set cursor position
            func = winterm.set_cursor_position
            func(params, on_stderr=self.on_stderr)
        elif command in ('J'):
            func = winterm.erase_data
            func(params, on_stderr=self.on_stderr)
        elif command == 'A':
            if params == () or params == None:
                num_rows = 1
            else:
                num_rows = params[0]
            func = winterm.cursor_up
            func(num_rows, on_stderr=self.on_stderr)


########NEW FILE########
__FILENAME__ = initialise
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
import atexit
import sys

from .ansitowin32 import AnsiToWin32


orig_stdout = sys.stdout
orig_stderr = sys.stderr

wrapped_stdout = sys.stdout
wrapped_stderr = sys.stderr

atexit_done = False


def reset_all():
    AnsiToWin32(orig_stdout).reset_all()


def init(autoreset=False, convert=None, strip=None, wrap=True):

    if not wrap and any([autoreset, convert, strip]):
        raise ValueError('wrap=False conflicts with any other arg=True')

    global wrapped_stdout, wrapped_stderr
    sys.stdout = wrapped_stdout = \
        wrap_stream(orig_stdout, convert, strip, autoreset, wrap)
    sys.stderr = wrapped_stderr = \
        wrap_stream(orig_stderr, convert, strip, autoreset, wrap)

    global atexit_done
    if not atexit_done:
        atexit.register(reset_all)
        atexit_done = True


def deinit():
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr


def reinit():
    sys.stdout = wrapped_stdout
    sys.stderr = wrapped_stdout


def wrap_stream(stream, convert, strip, autoreset, wrap):
    if wrap:
        wrapper = AnsiToWin32(stream,
            convert=convert, strip=strip, autoreset=autoreset)
        if wrapper.should_wrap():
            stream = wrapper.stream
    return stream



########NEW FILE########
__FILENAME__ = win32
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.

# from winbase.h
STDOUT = -11
STDERR = -12

try:
    from ctypes import windll
    from ctypes import wintypes
except ImportError:
    windll = None
    SetConsoleTextAttribute = lambda *_: None
else:
    from ctypes import (
        byref, Structure, c_char, c_short, c_uint32, c_ushort, POINTER
    )

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", wintypes._COORD),
            ("dwCursorPosition", wintypes._COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", wintypes.SMALL_RECT),
            ("dwMaximumWindowSize", wintypes._COORD),
        ]
        def __str__(self):
            return '(%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)' % (
                self.dwSize.Y, self.dwSize.X
                , self.dwCursorPosition.Y, self.dwCursorPosition.X
                , self.wAttributes
                , self.srWindow.Top, self.srWindow.Left, self.srWindow.Bottom, self.srWindow.Right
                , self.dwMaximumWindowSize.Y, self.dwMaximumWindowSize.X
            )

    _GetStdHandle = windll.kernel32.GetStdHandle
    _GetStdHandle.argtypes = [
        wintypes.DWORD,
    ]
    _GetStdHandle.restype = wintypes.HANDLE

    _GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    _GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    _GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    _SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    _SetConsoleTextAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
    ]
    _SetConsoleTextAttribute.restype = wintypes.BOOL

    _SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
    _SetConsoleCursorPosition.argtypes = [
        wintypes.HANDLE,
        wintypes._COORD,
    ]
    _SetConsoleCursorPosition.restype = wintypes.BOOL

    _FillConsoleOutputCharacterA = windll.kernel32.FillConsoleOutputCharacterA
    _FillConsoleOutputCharacterA.argtypes = [
        wintypes.HANDLE,
        c_char,
        wintypes.DWORD,
        wintypes._COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputCharacterA.restype = wintypes.BOOL

    _FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
    _FillConsoleOutputAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
        wintypes.DWORD,
        wintypes._COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputAttribute.restype = wintypes.BOOL

    handles = {
        STDOUT: _GetStdHandle(STDOUT),
        STDERR: _GetStdHandle(STDERR),
    }

    def GetConsoleScreenBufferInfo(stream_id=STDOUT):
        handle = handles[stream_id]
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        success = _GetConsoleScreenBufferInfo(
            handle, byref(csbi))
        return csbi

    def SetConsoleTextAttribute(stream_id, attrs):
        handle = handles[stream_id]
        return _SetConsoleTextAttribute(handle, attrs)

    def SetConsoleCursorPosition(stream_id, position):
        position = wintypes._COORD(*position)
        # If the position is out of range, do nothing.
        if position.Y <= 0 or position.X <= 0:
            return
        # Adjust for Windows' SetConsoleCursorPosition:
        #    1. being 0-based, while ANSI is 1-based.
        #    2. expecting (x,y), while ANSI uses (y,x).
        adjusted_position = wintypes._COORD(position.Y - 1, position.X - 1)
        # Adjust for viewport's scroll position
        sr = GetConsoleScreenBufferInfo(STDOUT).srWindow
        adjusted_position.Y += sr.Top
        adjusted_position.X += sr.Left
        # Resume normal processing
        handle = handles[stream_id]
        return _SetConsoleCursorPosition(handle, adjusted_position)

    def FillConsoleOutputCharacter(stream_id, char, length, start):
        handle = handles[stream_id]
        char = c_char(char)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        success = _FillConsoleOutputCharacterA(
            handle, char, length, start, byref(num_written))
        return num_written.value

    def FillConsoleOutputAttribute(stream_id, attr, length, start):
        ''' FillConsoleOutputAttribute( hConsole, csbi.wAttributes, dwConSize, coordScreen, &cCharsWritten )'''
        handle = handles[stream_id]
        attribute = wintypes.WORD(attr)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        return _FillConsoleOutputAttribute(
            handle, attribute, length, start, byref(num_written))

########NEW FILE########
__FILENAME__ = winterm
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
from . import win32


# from wincon.h
class WinColor(object):
    BLACK   = 0
    BLUE    = 1
    GREEN   = 2
    CYAN    = 3
    RED     = 4
    MAGENTA = 5
    YELLOW  = 6
    GREY    = 7

# from wincon.h
class WinStyle(object):
    NORMAL = 0x00 # dim text, dim background
    BRIGHT = 0x08 # bright text, dim background


class WinTerm(object):

    def __init__(self):
        self._default = win32.GetConsoleScreenBufferInfo(win32.STDOUT).wAttributes
        self.set_attrs(self._default)
        self._default_fore = self._fore
        self._default_back = self._back
        self._default_style = self._style

    def get_attrs(self):
        return self._fore + self._back * 16 + self._style

    def set_attrs(self, value):
        self._fore = value & 7
        self._back = (value >> 4) & 7
        self._style = value & WinStyle.BRIGHT

    def reset_all(self, on_stderr=None):
        self.set_attrs(self._default)
        self.set_console(attrs=self._default)

    def fore(self, fore=None, on_stderr=False):
        if fore is None:
            fore = self._default_fore
        self._fore = fore
        self.set_console(on_stderr=on_stderr)

    def back(self, back=None, on_stderr=False):
        if back is None:
            back = self._default_back
        self._back = back
        self.set_console(on_stderr=on_stderr)

    def style(self, style=None, on_stderr=False):
        if style is None:
            style = self._default_style
        self._style = style
        self.set_console(on_stderr=on_stderr)

    def set_console(self, attrs=None, on_stderr=False):
        if attrs is None:
            attrs = self.get_attrs()
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleTextAttribute(handle, attrs)

    def get_position(self, handle):
        position = win32.GetConsoleScreenBufferInfo(handle).dwCursorPosition
        # Because Windows coordinates are 0-based,
        # and win32.SetConsoleCursorPosition expects 1-based.
        position.X += 1
        position.Y += 1
        return position
    
    def set_cursor_position(self, position=None, on_stderr=False):
        if position is None:
            #I'm not currently tracking the position, so there is no default.
            #position = self.get_position()
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleCursorPosition(handle, position)

    def cursor_up(self, num_rows=0, on_stderr=False):
        if num_rows == 0:
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        position = self.get_position(handle)
        adjusted_position = (position.Y - num_rows, position.X)
        self.set_cursor_position(adjusted_position, on_stderr)

    def erase_data(self, mode=0, on_stderr=False):
        # 0 (or None) should clear from the cursor to the end of the screen.
        # 1 should clear from the cursor to the beginning of the screen.
        # 2 should clear the entire screen. (And maybe move cursor to (1,1)?)
        #
        # At the moment, I only support mode 2. From looking at the API, it
        #    should be possible to calculate a different number of bytes to clear,
        #    and to do so relative to the cursor position.
        if mode[0] not in (2,):
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        # here's where we'll home the cursor
        coord_screen = win32.COORD(0,0)
        csbi = win32.GetConsoleScreenBufferInfo(handle)
        # get the number of character cells in the current buffer
        dw_con_size = csbi.dwSize.X * csbi.dwSize.Y
        # fill the entire screen with blanks
        win32.FillConsoleOutputCharacter(handle, ' ', dw_con_size, coord_screen)
        # now set the buffer's attributes accordingly
        win32.FillConsoleOutputAttribute(handle, self.get_attrs(), dw_con_size, coord_screen );
        # put the cursor at (0, 0)
        win32.SetConsoleCursorPosition(handle, (coord_screen.X, coord_screen.Y))

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2009 Michael Foord
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.6.0
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'patch',
    'patch_object',
    'sentinel',
    'DEFAULT'
)

__version__ = '0.6.0 modified by Greg Malcolm'

class SentinelObject(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SentinelObject "{0!s}">'.format(self.name)


class Sentinel(object):
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        return self._sentinels.setdefault(name, SentinelObject(name))


sentinel = Sentinel()

DEFAULT = sentinel.DEFAULT

class OldStyleClass:
    pass
ClassType = type(OldStyleClass)

def _is_magic(name):
    return '__{0!s}__'.format(name[2:-2]) == name

def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


class Mock(object):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                 name=None, parent=None, wraps=None):
        self._parent = parent
        self._name = name
        if spec is not None and not isinstance(spec, list):
            spec = [member for member in dir(spec) if not _is_magic(member)]

        self._methods = spec
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        self._wraps = wraps

        self.reset_mock()


    def reset_mock(self):
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.values():
            child.reset_mock()
        if isinstance(self._return_value, Mock):
            self._return_value.reset_mock()


    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = Mock()
        return self._return_value

    def __set_return_value(self, value):
        self._return_value = value

    return_value = property(__get_return_value, __set_return_value)


    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = (args, kwargs)
        self.call_args_list.append((args, kwargs))

        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append((name, args, kwargs))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        ret_val = DEFAULT
        if self.side_effect is not None:
            if (isinstance(self.side_effect, Exception) or
                isinstance(self.side_effect, (type, ClassType)) and
                issubclass(self.side_effect, Exception)):
                raise self.side_effect

            ret_val = self.side_effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if self._wraps is not None and self._return_value is DEFAULT:
            return self._wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val


    def __getattr__(self, name):
        if self._methods is not None:
            if name not in self._methods:
                raise AttributeError("Mock object has no attribute '{0!s}'".format(name))
        elif _is_magic(name):
            raise AttributeError(name)

        if name not in self._children:
            wraps = None
            if self._wraps is not None:
                wraps = getattr(self._wraps, name)
            self._children[name] = Mock(parent=self, name=name, wraps=wraps)

        return self._children[name]


    def assert_called_with(self, *args, **kwargs):
        assert self.call_args == (args, kwargs), 'Expected: {0!s}\nCalled with: {1!s}'.format((args, kwargs), self.call_args)


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".{0!s}".format(comp)
        thing = _dot_lookup(thing, comp, import_path)
    return thing


class _patch(object):
    def __init__(self, target, attribute, new, spec, create):
        self.target = target
        self.attribute = attribute
        self.new = new
        self.spec = spec
        self.create = create
        self.has_local = False


    def __call__(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with 2.5)
            extra_args = []
            for patching in patched.patchings:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.append(arg)
            args += tuple(extra_args)
            try:
                return func(*args, **keywargs)
            finally:
                for patching in getattr(patched, 'patchings', []):
                    patching.__exit__()

        patched.patchings = [self]
        patched.__name__ = func.__name__
        patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno",
                                                func.func_code.co_firstlineno)
        return patched


    def get_original(self):
        target = self.target
        name = self.attribute
        create = self.create

        original = DEFAULT
        if _has_local_attr(target, name):
            try:
                original = target.__dict__[name]
            except AttributeError:
                # for instances of classes with slots, they have no __dict__
                original = getattr(target, name)
        elif not create and not hasattr(target, name):
            raise AttributeError("{0!s} does not have the attribute {1!r}".format(target, name))
        return original


    def __enter__(self):
        new, spec, = self.new, self.spec
        original = self.get_original()
        if new is DEFAULT:
            # XXXX what if original is DEFAULT - shouldn't use it as a spec
            inherit = False
            if spec == True:
                # set spec to the object we are replacing
                spec = original
                if isinstance(spec, (type, ClassType)):
                    inherit = True
            new = Mock(spec=spec)
            if inherit:
                new.return_value = Mock(spec=spec)
        self.temp_original = original
        setattr(self.target, self.attribute, new)
        return new


    def __exit__(self, *_):
        if self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
        del self.temp_original


def patch_object(target, attribute, new=DEFAULT, spec=None, create=False):
    return _patch(target, attribute, new, spec, create)


def patch(target, new=DEFAULT, spec=None, create=False):
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: {0!r}".format(target,))
    target = _importer(target)
    return _patch(target, attribute, new, spec, create)



def _has_local_attr(obj, name):
    try:
        return name in vars(obj)
    except TypeError:
        # objects without a __dict__
        return hasattr(obj, name)

########NEW FILE########
__FILENAME__ = helper
#!/usr/bin/env python
# -*- coding: utf-8 -*-

def cls_name(obj):
    return obj.__class__.__name__
########NEW FILE########
__FILENAME__ = koan
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import re

# Starting a classname or attribute with an underscore normally implies Private scope.
# However, we are making an exception for __ and ___.

__all__ = [ "__", "___", "____", "_____", "Koan" ]

__ = "-=> FILL ME IN! <=-"

class ___(Exception):
    pass

____ = "-=> TRUE OR FALSE? <=-"

_____ = 0


class Koan(unittest.TestCase):
    def assertMatch(self, pattern, string, msg=None):
        """
        Throw an exception if the regular expresson pattern is matched
        """
        # Not part of unittest, but convenient for some koans tests
        m = re.search(pattern, string)
        if not m or not m.group(0):
            raise self.failureException, \
                (msg or '{0!r} does not match {1!r}'.format(pattern, string))

    def assertNoMatch(self, pattern, string, msg=None):
        """
        Throw an exception if the regular expresson pattern is not matched
        """
        m = re.search(pattern, string)
        if m and m.group(0):
            raise self.failureException, \
                (msg or '{0!r} matches {1!r}'.format(pattern, string))

########NEW FILE########
__FILENAME__ = mockable_test_result
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

# Needed to stop unittest.TestResult itself getting Mocked out of existence,
# which is a problem when testing the helper classes! (It confuses the runner)

class MockableTestResult(unittest.TestResult):
    pass
########NEW FILE########
__FILENAME__ = mountain
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys

import path_to_enlightenment
from sensei import Sensei
from writeln_decorator import WritelnDecorator

class Mountain:
    def __init__(self):
        self.stream = WritelnDecorator(sys.stdout)
        self.tests = path_to_enlightenment.koans()
        self.lesson = Sensei(self.stream)

    def walk_the_path(self, args=None):
        "Run the koans tests with a custom runner output."

        if args and len(args) >=2:
            args.pop(0)
            test_names = ["koans." + test_name for test_name in args]
            self.tests = unittest.TestLoader().loadTestsFromNames(test_names)
        self.tests(self.lesson)
        self.lesson.learn()
        return self.lesson

########NEW FILE########
__FILENAME__ = path_to_enlightenment
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The path to enlightenment starts with the following:

import unittest

from koans.about_asserts import AboutAsserts
from koans.about_strings import AboutStrings
from koans.about_none import AboutNone
from koans.about_lists import AboutLists
from koans.about_list_assignments import AboutListAssignments
from koans.about_dictionaries import AboutDictionaries
from koans.about_string_manipulation import AboutStringManipulation
from koans.about_tuples import AboutTuples
from koans.about_methods import AboutMethods
from koans.about_control_statements import AboutControlStatements
from koans.about_true_and_false import AboutTrueAndFalse
from koans.about_sets import AboutSets
from koans.about_triangle_project import AboutTriangleProject
from koans.about_exceptions import AboutExceptions
from koans.about_triangle_project2 import AboutTriangleProject2
from koans.about_iteration import AboutIteration
from koans.about_comprehension import AboutComprehension
from koans.about_generators import AboutGenerators
from koans.about_lambdas import AboutLambdas
from koans.about_scoring_project import AboutScoringProject
from koans.about_classes import AboutClasses
from koans.about_new_style_classes import AboutNewStyleClasses
from koans.about_with_statements import AboutWithStatements
from koans.about_monkey_patching import AboutMonkeyPatching
from koans.about_dice_project import AboutDiceProject
from koans.about_method_bindings import AboutMethodBindings
from koans.about_decorating_with_functions import AboutDecoratingWithFunctions
from koans.about_decorating_with_classes import AboutDecoratingWithClasses
from koans.about_inheritance import AboutInheritance
from koans.about_multiple_inheritance import AboutMultipleInheritance
from koans.about_regex import AboutRegex
from koans.about_scope import AboutScope
from koans.about_modules import AboutModules
from koans.about_packages import AboutPackages
from koans.about_class_attributes import AboutClassAttributes
from koans.about_attribute_access import AboutAttributeAccess
from koans.about_deleting_objects import AboutDeletingObjects
from koans.about_proxy_object_project import *
from koans.about_extra_credit import AboutExtraCredit

def koans():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    loader.sortTestMethodsUsing = None
    suite.addTests(loader.loadTestsFromTestCase(AboutAsserts))
    suite.addTests(loader.loadTestsFromTestCase(AboutStrings))
    suite.addTests(loader.loadTestsFromTestCase(AboutNone))
    suite.addTests(loader.loadTestsFromTestCase(AboutLists))
    suite.addTests(loader.loadTestsFromTestCase(AboutListAssignments))
    suite.addTests(loader.loadTestsFromTestCase(AboutDictionaries))
    suite.addTests(loader.loadTestsFromTestCase(AboutStringManipulation))
    suite.addTests(loader.loadTestsFromTestCase(AboutTuples))
    suite.addTests(loader.loadTestsFromTestCase(AboutMethods))
    suite.addTests(loader.loadTestsFromTestCase(AboutControlStatements))
    suite.addTests(loader.loadTestsFromTestCase(AboutTrueAndFalse))
    suite.addTests(loader.loadTestsFromTestCase(AboutSets))
    suite.addTests(loader.loadTestsFromTestCase(AboutTriangleProject))
    suite.addTests(loader.loadTestsFromTestCase(AboutExceptions))
    suite.addTests(loader.loadTestsFromTestCase(AboutTriangleProject2))
    suite.addTests(loader.loadTestsFromTestCase(AboutIteration))
    suite.addTests(loader.loadTestsFromTestCase(AboutComprehension))
    suite.addTests(loader.loadTestsFromTestCase(AboutGenerators))
    suite.addTests(loader.loadTestsFromTestCase(AboutLambdas))
    suite.addTests(loader.loadTestsFromTestCase(AboutScoringProject))
    suite.addTests(loader.loadTestsFromTestCase(AboutClasses))
    suite.addTests(loader.loadTestsFromTestCase(AboutNewStyleClasses))
    suite.addTests(loader.loadTestsFromTestCase(AboutWithStatements))
    suite.addTests(loader.loadTestsFromTestCase(AboutMonkeyPatching))
    suite.addTests(loader.loadTestsFromTestCase(AboutDiceProject))
    suite.addTests(loader.loadTestsFromTestCase(AboutMethodBindings))
    suite.addTests(loader.loadTestsFromTestCase(AboutDecoratingWithFunctions))
    suite.addTests(loader.loadTestsFromTestCase(AboutDecoratingWithClasses))
    suite.addTests(loader.loadTestsFromTestCase(AboutInheritance))
    suite.addTests(loader.loadTestsFromTestCase(AboutMultipleInheritance))
    suite.addTests(loader.loadTestsFromTestCase(AboutScope))
    suite.addTests(loader.loadTestsFromTestCase(AboutModules))
    suite.addTests(loader.loadTestsFromTestCase(AboutPackages))
    suite.addTests(loader.loadTestsFromTestCase(AboutClassAttributes))
    suite.addTests(loader.loadTestsFromTestCase(AboutAttributeAccess))
    suite.addTests(loader.loadTestsFromTestCase(AboutDeletingObjects))
    suite.addTests(loader.loadTestsFromTestCase(AboutProxyObjectProject))
    suite.addTests(loader.loadTestsFromTestCase(TelevisionTest))
    suite.addTests(loader.loadTestsFromTestCase(AboutExtraCredit))
    suite.addTests(loader.loadTestsFromTestCase(AboutRegex))

    return suite

########NEW FILE########
__FILENAME__ = test_helper
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from runner import helper

class TestHelper(unittest.TestCase):

    def test_that_get_class_name_works_with_a_string_instance(self):
        self.assertEqual("str", helper.cls_name(str()))

    def test_that_get_class_name_works_with_a_4(self):
        self.assertEquals("int", helper.cls_name(4))

    def test_that_get_class_name_works_with_a_tuple(self):
        self.assertEquals("tuple", helper.cls_name((3,"pie", [])))

########NEW FILE########
__FILENAME__ = test_mountain
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from libs.mock import *

from runner.mountain import Mountain
from runner import path_to_enlightenment

class TestMountain(unittest.TestCase):

    def setUp(self):
        path_to_enlightenment.koans = Mock()
        self.mountain = Mountain()
        self.mountain.stream.writeln = Mock()

    def test_it_gets_test_results(self):
        self.mountain.lesson.learn = Mock()
        self.mountain.walk_the_path()
        self.assertTrue(self.mountain.lesson.learn.called)


########NEW FILE########
__FILENAME__ = test_sensei
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import re

from libs.mock import *

from runner.sensei import Sensei
from runner.writeln_decorator import WritelnDecorator
from runner.mockable_test_result import MockableTestResult
from runner import path_to_enlightenment

class AboutParrots:
    pass
class AboutLumberjacks:
    pass
class AboutTennis:
    pass
class AboutTheKnightsWhoSayNi:
    pass
class AboutMrGumby:
    pass
class AboutMessiahs:
    pass
class AboutGiantFeet:
    pass
class AboutTrebuchets:
    pass
class AboutFreemasons:
    pass

error_assertion_with_message = """Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_exploding_trousers.py", line 43, in test_durability
    self.assertEqual("Steel","Lard", "Another fine mess you've got me into Stanley...")
AssertionError: Another fine mess you've got me into Stanley..."""

error_assertion_equals = """

Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_exploding_trousers.py", line 49, in test_math
    self.assertEqual(4,99)
AssertionError: 4 != 99
"""

error_assertion_true = """Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_armories.py", line 25, in test_weoponary
    self.assertTrue("Pen" > "Sword")
AssertionError

"""

error_mess = """
Traceback (most recent call last):
  File "contemplate_koans.py", line 5, in <module>
    from runner.mountain import Mountain
  File "/Users/Greg/hg/python_koans/runner/mountain.py", line 7, in <module>
    import path_to_enlightenment
  File "/Users/Greg/hg/python_koans/runner/path_to_enlightenment.py", line 8, in <module>
    from koans import *
  File "/Users/Greg/hg/python_koans/koans/about_asserts.py", line 20
    self.assertTrue(eoe"Pen" > "Sword", "nhnth")
                           ^
SyntaxError: invalid syntax"""

error_with_list = """Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_armories.py", line 84, in test_weoponary
    self.assertEqual([1, 9], [1, 2])
AssertionError: Lists differ: [1, 9] != [1, 2]

First differing element 1:
9
2

- [1, 9]
?     ^

+ [1, 2]
?     ^

"""

class TestSensei(unittest.TestCase):

    def setUp(self):
        self.sensei = Sensei(WritelnDecorator(sys.stdout))
        self.sensei.stream.writeln = Mock()
        path_to_enlightenment.koans = Mock()
        self.tests = Mock()
        self.tests.countTestCases = Mock()

    def test_that_failures_are_handled_in_the_base_class(self):
        MockableTestResult.addFailure = Mock()
        self.sensei.addFailure(Mock(), Mock())
        self.assertTrue(MockableTestResult.addFailure.called)

    def test_that_it_successes_only_count_if_passes_are_currently_allowed(self):
        self.sensei.passesCount = Mock()
        MockableTestResult.addSuccess = Mock()
        self.sensei.addSuccess(Mock())
        self.assertTrue(self.sensei.passesCount.called)

    def test_that_it_passes_on_add_successes_message(self):
        MockableTestResult.addSuccess = Mock()
        self.sensei.addSuccess(Mock())
        self.assertTrue(MockableTestResult.addSuccess.called)

    def test_that_it_increases_the_passes_on_every_success(self):
        pass_count = self.sensei.pass_count
        MockableTestResult.addSuccess = Mock()
        self.sensei.addSuccess(Mock())
        self.assertEqual(pass_count + 1, self.sensei.pass_count)

    def test_that_nothing_is_returned_as_a_first_result_if_there_are_no_failures(self):
        self.sensei.failures = []
        self.assertEqual(None, self.sensei.firstFailure())

    def test_that_nothing_is_returned_as_sorted_result_if_there_are_no_failures(self):
        self.sensei.failures = []
        self.assertEqual(None, self.sensei.sortFailures("AboutLife"))

    def test_that_nothing_is_returned_as_sorted_result_if_there_are_no_relevent_failures(self):
        self.sensei.failures = [
            (AboutTheKnightsWhoSayNi(),"File 'about_the_knights_whn_say_ni.py', line 24"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 43"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 844")
        ]
        self.assertEqual(None, self.sensei.sortFailures("AboutLife"))

    def test_that_nothing_is_returned_as_sorted_result_if_there_are_3_shuffled_results(self):
        self.sensei.failures = [
            (AboutTennis(),"File 'about_tennis.py', line 299"),
            (AboutTheKnightsWhoSayNi(),"File 'about_the_knights_whn_say_ni.py', line 24"),
            (AboutTennis(),"File 'about_tennis.py', line 30"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 43"),
            (AboutTennis(),"File 'about_tennis.py', line 2"),
            (AboutMrGumby(),"File 'about_mr_gumby.py', line odd"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 844")
        ]

        expected = [
            (AboutTennis(),"File 'about_tennis.py', line 2"),
            (AboutTennis(),"File 'about_tennis.py', line 30"),
            (AboutTennis(),"File 'about_tennis.py', line 299")
        ]

        results = self.sensei.sortFailures("AboutTennis")
        self.assertEqual(3, len(results))
        self.assertEqual(2, results[0][0])
        self.assertEqual(30, results[1][0])
        self.assertEqual(299, results[2][0])

    def test_that_it_will_choose_not_find_anything_with_non_standard_error_trace_string(self):
        self.sensei.failures = [
            (AboutMrGumby(),"File 'about_mr_gumby.py', line MISSING"),
        ]
        self.assertEqual(None, self.sensei.sortFailures("AboutMrGumby"))


    def test_that_it_will_choose_correct_first_result_with_lines_9_and_27(self):
        self.sensei.failures = [
            (AboutTrebuchets(),"File 'about_trebuchets.py', line 27"),
            (AboutTrebuchets(),"File 'about_trebuchets.py', line 9"),
            (AboutTrebuchets(),"File 'about_trebuchets.py', line 73v")
        ]
        self.assertEqual("File 'about_trebuchets.py', line 9", self.sensei.firstFailure()[1])

    def test_that_it_will_choose_correct_first_result_with_multiline_test_classes(self):
        self.sensei.failures = [
            (AboutGiantFeet(),"File 'about_giant_feet.py', line 999"),
            (AboutGiantFeet(),"File 'about_giant_feet.py', line 44"),
            (AboutFreemasons(),"File 'about_freemasons.py', line 1"),
            (AboutFreemasons(),"File 'about_freemasons.py', line 11")
        ]
        self.assertEqual("File 'about_giant_feet.py', line 44", self.sensei.firstFailure()[1])

    def test_that_error_report_features_the_assertion_error(self):
        self.sensei.scrapeAssertionError = Mock()
        self.sensei.firstFailure = Mock()
        self.sensei.firstFailure.return_value = (Mock(), "FAILED")
        self.sensei.errorReport()
        self.assertTrue(self.sensei.scrapeAssertionError.called)

    def test_that_error_report_features_a_stack_dump(self):
        self.sensei.scrapeInterestingStackDump = Mock()
        self.sensei.firstFailure = Mock()
        self.sensei.firstFailure.return_value = (Mock(), "FAILED")
        self.sensei.errorReport()
        self.assertTrue(self.sensei.scrapeInterestingStackDump.called)

    def test_that_scraping_the_assertion_error_with_nothing_gives_you_a_blank_back(self):
        self.assertEqual("", self.sensei.scrapeAssertionError(None))

    def test_that_scraping_the_assertion_error_with_messaged_assert(self):
        self.assertEqual("  AssertionError: Another fine mess you've got me into Stanley...",
            self.sensei.scrapeAssertionError(error_assertion_with_message))

    def test_that_scraping_the_assertion_error_with_assert_equals(self):
        self.assertEqual("  AssertionError: 4 != 99",
            self.sensei.scrapeAssertionError(error_assertion_equals))

    def test_that_scraping_the_assertion_error_with_assert_true(self):
        self.assertEqual("  AssertionError",
            self.sensei.scrapeAssertionError(error_assertion_true))

    def test_that_scraping_the_assertion_error_with_syntax_error(self):
        self.assertEqual("  SyntaxError: invalid syntax",
            self.sensei.scrapeAssertionError(error_mess))

    def test_that_scraping_the_assertion_error_with_list_error(self):
        self.assertEqual("""  AssertionError: Lists differ: [1, 9] != [1, 2]

  First differing element 1:
  9
  2

  - [1, 9]
  ?     ^

  + [1, 2]
  ?     ^""",
            self.sensei.scrapeAssertionError(error_with_list))

    def test_that_scraping_a_non_existent_stack_dump_gives_you_nothing(self):
        self.assertEqual("", self.sensei.scrapeInterestingStackDump(None))

    def test_that_if_there_are_no_failures_say_the_final_zenlike_remark(self):
        self.sensei.failures = None
        words = self.sensei.say_something_zenlike()

        m = re.search("Spanish Inquisition", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_are_0_successes_it_will_say_the_first_zen_of_python_koans(self):
        self.sensei.pass_count = 0
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Beautiful is better than ugly", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_1_successes_it_will_say_the_second_zen_of_python_koans(self):
        self.sensei.pass_count = 1
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Explicit is better than implicit", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_10_successes_it_will_say_the_sixth_zen_of_python_koans(self):
        self.sensei.pass_count = 10
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Sparse is better than dense", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_36_successes_it_will_say_the_final_zen_of_python_koans(self):
        self.sensei.pass_count = 36
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Namespaces are one honking great idea", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_37_successes_it_will_say_the_first_zen_of_python_koans_again(self):
        self.sensei.pass_count = 37
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Beautiful is better than ugly", words)
        self.assertTrue(m and m.group(0))

    def test_that_total_lessons_return_7_if_there_are_7_lessons(self):
        self.sensei.filter_all_lessons = Mock()
        self.sensei.filter_all_lessons.return_value = [1,2,3,4,5,6,7]

        self.assertEqual(7, self.sensei.total_lessons())

    def test_that_total_lessons_return_0_if_all_lessons_is_none(self):
        self.sensei.filter_all_lessons = Mock()
        self.sensei.filter_all_lessons.return_value = None

        self.assertEqual(0, self.sensei.total_lessons())

    def test_total_koans_return_43_if_there_are_43_test_cases(self):
        self.sensei.tests.countTestCases = Mock()
        self.sensei.tests.countTestCases.return_value = 43

        self.assertEqual(43, self.sensei.total_koans())

    def test_filter_all_lessons_will_discover_test_classes_if_none_have_been_discovered_yet(self):
        self.sensei.all_lessons = 0
        self.assertTrue(len(self.sensei.filter_all_lessons()) > 10)
        self.assertTrue(len(self.sensei.all_lessons) > 10)

########NEW FILE########
__FILENAME__ = sensei
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import re
import sys
import os
import glob

import helper
from mockable_test_result import MockableTestResult
from runner import path_to_enlightenment

from libs.colorama import init, Fore, Style
init() # init colorama

class Sensei(MockableTestResult):
    def __init__(self, stream):
        unittest.TestResult.__init__(self)
        self.stream = stream
        self.prevTestClassName = None
        self.tests = path_to_enlightenment.koans()
        self.pass_count = 0
        self.lesson_pass_count  = 0
        self.all_lessons = None

    def startTest(self, test):
        MockableTestResult.startTest(self, test)

        if helper.cls_name(test) != self.prevTestClassName:
            self.prevTestClassName = helper.cls_name(test)
            if not self.failures:
                self.stream.writeln()
                self.stream.writeln("{0}{1}Thinking {2}".format(
                    Fore.RESET, Style.NORMAL, helper.cls_name(test)))
                if helper.cls_name(test) != 'AboutAsserts':
                    self.lesson_pass_count += 1

    def addSuccess(self, test):
        if self.passesCount():
            MockableTestResult.addSuccess(self, test)
            self.stream.writeln( \
                "  {0}{1}{2} has expanded your awareness.{3}{4}" \
                .format(Fore.GREEN, Style.BRIGHT, test._testMethodName, \
                Fore.RESET, Style.NORMAL))
            self.pass_count += 1

    def addError(self, test, err):
        # Having 1 list for errors and 1 list for failures would mess with
        # the error sequence
        self.addFailure(test, err)

    def passesCount(self):
        return not (self.failures and helper.cls_name(self.failures[0][0]) !=
                    self.prevTestClassName)

    def addFailure(self, test, err):
        MockableTestResult.addFailure(self, test, err)

    def sortFailures(self, testClassName):
        table = list()
        for test, err in self.failures:
            if helper.cls_name(test) ==  testClassName:
                m = re.search("(?<= line )\d+" ,err)
                if m:
                    tup = (int(m.group(0)), test, err)
                    table.append(tup)

        if table:
            return sorted(table)
        else:
            return None

    def firstFailure(self):
        if not self.failures: return None

        table = self.sortFailures(helper.cls_name(self.failures[0][0]))

        if table:
            return (table[0][1], table[0][2])
        else:
            return None

    def learn(self):
        self.errorReport()

        self.stream.writeln("")
        self.stream.writeln("")
        self.stream.writeln(self.report_progress())
        if self.failures:
          self.stream.writeln(self.report_remaining())
        self.stream.writeln("")
        self.stream.writeln(self.say_something_zenlike())

        if self.failures: sys.exit(-1)
        self.stream.writeln(
            "\n{0}**************************************************" \
            .format(Fore.RESET))
        self.stream.writeln("\n{0}That was the last one, well done!" \
            .format(Fore.MAGENTA))
        self.stream.writeln(
            "\nIf you want more, take a look at about_extra_credit_task.py")

    def errorReport(self):
        problem = self.firstFailure()
        if not problem: return
        test, err = problem
        self.stream.writeln("  {0}{1}{2} has damaged your "
          "karma.".format(Fore.RED, Style.BRIGHT, test._testMethodName))

        self.stream.writeln("\n{0}{1}You have not yet reached enlightenment ..." \
            .format(Fore.RESET, Style.NORMAL))
        self.stream.writeln("{0}{1}{2}".format(Fore.RED, \
            Style.BRIGHT, self.scrapeAssertionError(err)))
        self.stream.writeln("")
        self.stream.writeln("{0}{1}Please meditate on the following code:" \
            .format(Fore.RESET, Style.NORMAL))
        self.stream.writeln("{0}{1}{2}{3}{4}".format(Fore.YELLOW, Style.BRIGHT, \
            self.scrapeInterestingStackDump(err), Fore.RESET, Style.NORMAL))

    def scrapeAssertionError(self, err):
        if not err: return ""

        error_text = ""
        count = 0
        for line in err.splitlines():
            m = re.search("^[^^ ].*$",line)
            if m and m.group(0):
                count+=1

            if count>1:
                error_text += ("  " + line.strip()).rstrip() + '\n'
        return error_text.strip('\n')

    def scrapeInterestingStackDump(self, err):
        if not err:
            return ""

        lines = err.splitlines()

        sep = '@@@@@SEP@@@@@'

        stack_text = ""
        for line in lines:
            m = re.search("^  File .*$",line)
            if m and m.group(0):
                stack_text += '\n' + line

            m = re.search("^    \w(\w)+.*$",line)
            if m and m.group(0):
                stack_text += sep + line

        lines = stack_text.splitlines()

        stack_text = ""
        for line in lines:
            m = re.search("^.*[/\\\\]koans[/\\\\].*$",line)
            if m and m.group(0):
                stack_text += line + '\n'


        stack_text = stack_text.replace(sep, '\n').strip('\n')
        stack_text = re.sub(r'(about_\w+.py)',
                r"{0}\1{1}".format(Fore.BLUE, Fore.YELLOW), stack_text)
        stack_text = re.sub(r'(line \d+)',
                r"{0}\1{1}".format(Fore.BLUE, Fore.YELLOW), stack_text)
        return stack_text

    def report_progress(self):
        return "You have completed {0} koans and " \
            "{1} lessons.".format(
                self.pass_count,
                self.lesson_pass_count)

    def report_remaining(self):
        koans_remaining = self.total_koans() - self.pass_count
        lessons_remaining = self.total_lessons() - self.lesson_pass_count

        return "You are now {0} koans and {1} lessons away from " \
            "reaching enlightenment.".format(
                koans_remaining,
                lessons_remaining)

    # Hat's tip to Tim Peters for the zen statements from The 'Zen
    # of Python' (http://www.python.org/dev/peps/pep-0020/)
    #
    # Also a hat's tip to Ara T. Howard for the zen statements from his
    # metakoans Ruby Quiz (http://rubyquiz.com/quiz67.html) and
    # Edgecase's later permutation in the Ruby Koans
    def say_something_zenlike(self):
        if self.failures:
            turn = self.pass_count % 37

            zenness = "";
            if turn == 0:
                zenness = "Beautiful is better than ugly."
            elif turn == 1 or turn == 2:
                zenness = "Explicit is better than implicit."
            elif turn == 3 or turn == 4:
                zenness = "Simple is better than complex."
            elif turn == 5 or turn == 6:
                zenness = "Complex is better than complicated."
            elif turn == 7 or turn == 8:
                zenness = "Flat is better than nested."
            elif turn == 9 or turn == 10:
                zenness = "Sparse is better than dense."
            elif turn == 11 or turn == 12:
                zenness = "Readability counts."
            elif turn == 13 or turn == 14:
                zenness = "Special cases aren't special enough to " \
                          "break the rules."
            elif turn == 15 or turn == 16:
                zenness = "Although practicality beats purity."
            elif turn == 17 or turn == 18:
                zenness = "Errors should never pass silently."
            elif turn == 19 or turn == 20:
                zenness = "Unless explicitly silenced."
            elif turn == 21 or turn == 22:
                zenness = "In the face of ambiguity, refuse the " \
                          "temptation to guess."
            elif turn == 23 or turn == 24:
                zenness = "There should be one-- and preferably only " \
                          "one --obvious way to do it."
            elif turn == 25 or turn == 26:
                zenness = "Although that way may not be obvious at " \
                          "first unless you're Dutch."
            elif turn == 27 or turn == 28:
                zenness = "Now is better than never."
            elif turn == 29 or turn == 30:
                zenness = "Although never is often better than right " \
                          "now."
            elif turn == 31 or turn == 32:
                zenness = "If the implementation is hard to explain, " \
                          "it's a bad idea."
            elif turn == 33 or turn == 34:
                zenness = "If the implementation is easy to explain, " \
                          "it may be a good idea."
            else:
                zenness = "Namespaces are one honking great idea -- " \
                          "let's do more of those!"
            return "{0}{1}{2}{3}".format(Fore.CYAN, zenness, Fore.RESET, Style.NORMAL);
        else:
            return "{0}Nobody ever expects the Spanish Inquisition." \
                .format(Fore.CYAN)

        # Hopefully this will never ever happen!
        return "The temple is collapsing! Run!!!"

    def total_lessons(self):
        all_lessons = self.filter_all_lessons()

        if all_lessons:
          return len(all_lessons)
        else:
          return 0

    def total_koans(self):
        return self.tests.countTestCases()

    def filter_all_lessons(self):
        cur_dir = os.path.split(os.path.realpath(__file__))[0]
        if not self.all_lessons:
            self.all_lessons = glob.glob('{0}/../koans/about*.py'.format(cur_dir))
            self.all_lessons = filter(lambda filename:
                                      "about_extra_credit" not in filename,
                                      self.all_lessons)
        return self.all_lessons

########NEW FILE########
__FILENAME__ = writeln_decorator
#!/usr/bin/env python
# encoding: utf-8

import sys
import os

# Taken from legacy python unittest
class WritelnDecorator:
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        return getattr(self.stream,attr)

    def writeln(self, arg=None):
        if arg: self.write(arg)
        self.write('\n') # text-mode streams translate to \r\n if needed


########NEW FILE########
__FILENAME__ = _runner_tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest

from runner.runner_tests.test_mountain import TestMountain
from runner.runner_tests.test_sensei import TestSensei
from runner.runner_tests.test_helper import TestHelper

def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMountain))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSensei))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHelper))
    return suite

if __name__ == '__main__':
    res = unittest.TextTestRunner(verbosity=2).run(suite())
    sys.exit(not res.wasSuccessful())

########NEW FILE########
__FILENAME__ = contemplate_koans
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Acknowledgment:
#
# Python Koans is a port of Ruby Koans originally written by Jim Weirich
# and Joe O'brien of Edgecase. There are some differences and tweaks specific
# to the Python language, but a great deal of it has been copied wholesale.
# So thanks guys!
#

import sys

if __name__ == '__main__':
    if sys.version_info < (3, 0):
        print("\nThis is the Python 3 version of Python Koans, but you are " +
              "running it with Python 2!\n\n"
              "Did you accidentally use the wrong python script? \nTry:\n\n" +
              "    python3 contemplate_koans.py\n")
    else:
        if sys.version_info < (3, 3):
            print("\n" +
                  "********************************************************\n" +
                  "WARNING:\n" +
                  "This version of Python Koans was designed for " +
                  "Python 3.3 or greater.\n" +
                  "Your version of Python is older, so you may run into " +
                  "problems!\n\n" +
                  "But lets see how far we get...\n" +
                  "********************************************************\n")

        from runner.mountain import Mountain

        Mountain().walk_the_path(sys.argv)

########NEW FILE########
__FILENAME__ = about_asserts
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutAsserts(Koan):

    def test_assert_truth(self):
        """
        We shall contemplate truth by testing reality, via asserts.
        """

        # Confused? This video should help:
        #
        #   http://bit.ly/about_asserts

        self.assertTrue(False) # This should be true

    def test_assert_with_message(self):
        """
        Enlightenment may be more easily achieved with appropriate messages.
        """
        self.assertTrue(False, "This should be true -- Please fix this")

    def test_fill_in_values(self):
        """
        Sometimes we will ask you to fill in the values
        """
        self.assertEqual(__, 1 + 1)

    def test_assert_equality(self):
        """
        To understand reality, we must compare our expectations against reality.
        """
        expected_value = __
        actual_value = 1 + 1
        self.assertTrue(expected_value == actual_value)

    def test_a_better_way_of_asserting_equality(self):
        """
        Some ways of asserting equality are better than others.
        """
        expected_value = __
        actual_value = 1 + 1

        self.assertEqual(expected_value, actual_value)

    def test_that_unittest_asserts_work_the_same_way_as_python_asserts(self):
        """
        Understand what lies within.
        """

        # This throws an AssertionError exception
        assert False

    def test_that_sometimes_we_need_to_know_the_class_type(self):
        """
        What is in a class name?
        """

        # Sometimes we will ask you what the class type of an object is.
        #
        # For example, contemplate the text string "naval". What is it's class type?
        # The koans runner will include this feedback for this koan:
        #
        #   AssertionError: '-=> FILL ME IN! <=-' != <type 'str'>
        #
        # So "naval".__class__ is equal to <type 'str'>? No not quite. This
        # is just what it displays. The answer is simply str.
        #
        # See for yourself:

        self.assertEqual(__, "naval".__class__) # It's str, not <type 'str'>

        # Need an illustration? More reading can be found here:
        #
        #   http://bit.ly/__class__


########NEW FILE########
__FILENAME__ = about_attribute_access
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Partially based on AboutMessagePassing in the Ruby Koans
#

from runner.koan import *

class AboutAttributeAccess(Koan):

    class TypicalObject:
        pass

    def test_calling_undefined_functions_normally_results_in_errors(self):
        typical = self.TypicalObject()

        with self.assertRaises(___): typical.foobar()

    def test_calling_getattribute_causes_an_attribute_error(self):
        typical = self.TypicalObject()

        with self.assertRaises(___): typical.__getattribute__('foobar')

        # THINK ABOUT IT:
        #
        # If the method __getattribute__() causes the AttributeError, then
        # what would happen if we redefine __getattribute__()?

    # ------------------------------------------------------------------

    class CatchAllAttributeReads:
        def __getattribute__(self, attr_name):
            return "Someone called '" + attr_name + "' and it could not be found"

    def test_all_attribute_reads_are_caught(self):
        catcher = self.CatchAllAttributeReads()

        self.assertRegexpMatches(catcher.foobar, __)

    def test_intercepting_return_values_can_disrupt_the_call_chain(self):
        catcher = self.CatchAllAttributeReads()

        self.assertRegexpMatches(catcher.foobaz, __) # This is fine

        try:
            catcher.foobaz(1)
        except TypeError as ex:
            err_msg = ex.args[0]

        self.assertRegexpMatches(err_msg, __)

        # foobaz returns a string. What happens to the '(1)' part?
        # Try entering this into a python console to reproduce the issue:
        #
        #     "foobaz"(1)
        #

    def test_changes_to_the_getattribute_implementation_affects_getattr_function(self):
        catcher = self.CatchAllAttributeReads()

        self.assertRegexpMatches(getattr(catcher, 'any_attribute'), __)

    # ------------------------------------------------------------------

    class WellBehavedFooCatcher:
        def __getattribute__(self, attr_name):
            if attr_name[:3] == "foo":
                return "Foo to you too"
            else:
                return super().__getattribute__(attr_name)

    def test_foo_attributes_are_caught(self):
        catcher = self.WellBehavedFooCatcher()

        self.assertEqual(__, catcher.foo_bar)
        self.assertEqual(__, catcher.foo_baz)

    def test_non_foo_messages_are_treated_normally(self):
        catcher = self.WellBehavedFooCatcher()

        with self.assertRaises(___): catcher.normal_undefined_attribute

    # ------------------------------------------------------------------

    global stack_depth
    stack_depth = 0

    class RecursiveCatcher:
        def __init__(self):
            global stack_depth
            stack_depth = 0
            self.no_of_getattribute_calls = 0

        def __getattribute__(self, attr_name):
            global stack_depth # We need something that is outside the scope of this class
            stack_depth += 1

            if stack_depth<=10: # to prevent a stack overflow
                self.no_of_getattribute_calls += 1
                # Oops! We just accessed an attribute (no_of_getattribute_calls)
                # Guess what happens when self.no_of_getattribute_calls is
                # accessed?

            # Using 'object' directly because using super() here will also
            # trigger a __getattribute__() call.
            return object.__getattribute__(self, attr_name)

        def my_method(self):
            pass

    def test_getattribute_is_a_bit_overzealous_sometimes(self):
        catcher = self.RecursiveCatcher()
        catcher.my_method()
        global stack_depth
        self.assertEqual(__, stack_depth)

    # ------------------------------------------------------------------

    class MinimalCatcher:
        class DuffObject: pass

        def __init__(self):
            self.no_of_getattr_calls = 0

        def __getattr__(self, attr_name):
            self.no_of_getattr_calls += 1
            return self.DuffObject

        def my_method(self):
            pass

    def test_getattr_ignores_known_attributes(self):
        catcher = self.MinimalCatcher()
        catcher.my_method()

        self.assertEqual(__, catcher.no_of_getattr_calls)

    def test_getattr_only_catches_unknown_attributes(self):
        catcher = self.MinimalCatcher()
        catcher.purple_flamingos()
        catcher.free_pie()

        self.assertEqual(__,
            type(catcher.give_me_duff_or_give_me_death()).__name__)

        self.assertEqual(__, catcher.no_of_getattr_calls)

    # ------------------------------------------------------------------

    class PossessiveSetter(object):
        def __setattr__(self, attr_name, value):
            new_attr_name =  attr_name

            if attr_name[-5:] == 'comic':
                new_attr_name = "my_" + new_attr_name
            elif attr_name[-3:] == 'pie':
                new_attr_name = "a_" + new_attr_name

            object.__setattr__(self, new_attr_name, value)

    def test_setattr_intercepts_attribute_assignments(self):
        fanboy = self.PossessiveSetter()

        fanboy.comic = 'The Laminator, issue #1'
        fanboy.pie = 'blueberry'

        self.assertEqual(__, fanboy.a_pie)

        #
        # NOTE: Change the prefix to make this next assert pass
        #

        prefix = '__'
        self.assertEqual("The Laminator, issue #1", getattr(fanboy, prefix + '_comic'))

    # ------------------------------------------------------------------

    class ScarySetter:
        def __init__(self):
            self.num_of_coconuts = 9
            self._num_of_private_coconuts = 2

        def __setattr__(self, attr_name, value):
            new_attr_name =  attr_name

            if attr_name[0] != '_':
                new_attr_name = "altered_" + new_attr_name

            object.__setattr__(self, new_attr_name, value)

    def test_it_modifies_external_attribute_as_expected(self):
        setter = self.ScarySetter()
        setter.e = "mc hammer"

        self.assertEqual(__, setter.altered_e)

    def test_it_mangles_some_internal_attributes(self):
        setter = self.ScarySetter()

        try:
            coconuts = setter.num_of_coconuts
        except AttributeError:
            self.assertEqual(__, setter.altered_num_of_coconuts)

    def test_in_this_case_private_attributes_remain_unmangled(self):
        setter = self.ScarySetter()

        self.assertEqual(__, setter._num_of_private_coconuts)

########NEW FILE########
__FILENAME__ = about_classes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutClasses(Koan):
    class Dog:
        "Dogs need regular walkies. Never, ever let them drive."

    def test_instances_of_classes_can_be_created_adding_parentheses(self):
        # NOTE: The .__name__ attribute will convert the class
        # into a string value.
        fido = self.Dog()
        self.assertEqual(__, fido.__class__.__name__)

    def test_classes_have_docstrings(self):
        self.assertRegexpMatches(self.Dog.__doc__, __)

    # ------------------------------------------------------------------

    class Dog2:
        def __init__(self):
            self._name = 'Paul'

        def set_name(self, a_name):
            self._name = a_name

    def test_init_method_is_the_constructor(self):
        dog = self.Dog2()
        self.assertEqual(__, dog._name)

    def test_private_attributes_are_not_really_private(self):
        dog = self.Dog2()
        dog.set_name("Fido")
        self.assertEqual(__, dog._name)
        # The _ prefix in _name implies private ownership, but nothing is truly
        # private in Python.

    def test_you_can_also_access_the_value_out_using_getattr_and_dict(self):
        fido = self.Dog2()
        fido.set_name("Fido")

        self.assertEqual(__, getattr(fido, "_name"))
        # getattr(), setattr() and delattr() are a way of accessing attributes
        # by method rather than through assignment operators

        self.assertEqual(__, fido.__dict__["_name"])
        # Yes, this works here, but don't rely on the __dict__ object! Some
        # class implementations use optimization which result in __dict__ not
        # showing everything.

    # ------------------------------------------------------------------

    class Dog3:
        def __init__(self):
            self._name = None

        def set_name(self, a_name):
            self._name = a_name

        def get_name(self):
            return self._name

        name = property(get_name, set_name)

    def test_that_name_can_be_read_as_a_property(self):
        fido = self.Dog3()
        fido.set_name("Fido")

        # access as method
        self.assertEqual(__, fido.get_name())

        # access as property
        self.assertEqual(__, fido.name)

    # ------------------------------------------------------------------

    class Dog4:
        def __init__(self):
            self._name = None

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, a_name):
            self._name = a_name

    def test_creating_properties_with_decorators_is_slightly_easier(self):
        fido = self.Dog4()

        fido.name = "Fido"
        self.assertEqual(__, fido.name)

    # ------------------------------------------------------------------

    class Dog5:
        def __init__(self, initial_name):
            self._name = initial_name

        @property
        def name(self):
            return self._name

    def test_init_provides_initial_values_for_instance_variables(self):
        fido = self.Dog5("Fido")
        self.assertEqual(__, fido.name)

    def test_args_must_match_init(self):
        with self.assertRaises(___):
            self.Dog5()

        # THINK ABOUT IT:
        # Why is this so?

    def test_different_objects_have_different_instance_variables(self):
        fido = self.Dog5("Fido")
        rover = self.Dog5("Rover")

        self.assertEqual(__, rover.name == fido.name)

    # ------------------------------------------------------------------

    class Dog6:
        def __init__(self, initial_name):
            self._name = initial_name

        def get_self(self):
            return self

        def __str__(self):
            #
            # Implement this!
            #
            return __

        def __repr__(self):
            return "<Dog named '" + self._name + "'>"

    def test_inside_a_method_self_refers_to_the_containing_object(self):
        fido = self.Dog6("Fido")

        self.assertEqual(__, fido.get_self())  # Not a string!

    def test_str_provides_a_string_version_of_the_object(self):
        fido = self.Dog6("Fido")

        self.assertEqual("Fido", str(fido))

    def test_str_is_used_explicitly_in_string_interpolation(self):
        fido = self.Dog6("Fido")

        self.assertEqual(__, "My dog is " + str(fido))

    def test_repr_provides_a_more_complete_string_version(self):
        fido = self.Dog6("Fido")
        self.assertEqual(__, repr(fido))

    def test_all_objects_support_str_and_repr(self):
        seq = [1, 2, 3]

        self.assertEqual(__, str(seq))
        self.assertEqual(__, repr(seq))

        self.assertEqual(__, str("STRING"))
        self.assertEqual(__, repr("STRING"))

########NEW FILE########
__FILENAME__ = about_class_attributes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutClassMethods in the Ruby Koans
#

from runner.koan import *

class AboutClassAttributes(Koan):
    class Dog:
        pass

    def test_objects_are_objects(self):
        fido = self.Dog()
        self.assertEqual(__, isinstance(fido, object))

    def test_classes_are_types(self):
        self.assertEqual(__, self.Dog.__class__ == type)

    def test_classes_are_objects_too(self):
        self.assertEqual(__, issubclass(self.Dog, object))

    def test_objects_have_methods(self):
        fido = self.Dog()
        self.assertEqual(__, len(dir(fido)))

    def test_classes_have_methods(self):
        self.assertEqual(__, len(dir(self.Dog)))

    def test_creating_objects_without_defining_a_class(self):
        singularity = object()
        self.assertEqual(__, len(dir(singularity)))

    def test_defining_attributes_on_individual_objects(self):
        fido = self.Dog()
        fido.legs = 4

        self.assertEqual(__, fido.legs)

    def test_defining_functions_on_individual_objects(self):
        fido = self.Dog()
        fido.wag = lambda : 'fidos wag'

        self.assertEqual(__, fido.wag())

    def test_other_objects_are_not_affected_by_these_singleton_functions(self):
        fido = self.Dog()
        rover = self.Dog()

        def wag():
            return 'fidos wag'
        fido.wag = wag

        with self.assertRaises(___): rover.wag()

    # ------------------------------------------------------------------

    class Dog2:
        def wag(self):
            return 'instance wag'

        def bark(self):
            return "instance bark"

        def growl(self):
            return "instance growl"

        @staticmethod
        def bark():
            return "staticmethod bark, arg: None"

        @classmethod
        def growl(cls):
            return "classmethod growl, arg: cls=" + cls.__name__

    def test_since_classes_are_objects_you_can_define_singleton_methods_on_them_too(self):
        self.assertRegexpMatches(self.Dog2.growl(), __)

    def test_classmethods_are_not_independent_of_instance_methods(self):
        fido = self.Dog2()
        self.assertRegexpMatches(fido.growl(), __)
        self.assertRegexpMatches(self.Dog2.growl(), __)

    def test_staticmethods_are_unbound_functions_housed_in_a_class(self):
        self.assertRegexpMatches(self.Dog2.bark(), __)

    def test_staticmethods_also_overshadow_instance_methods(self):
        fido = self.Dog2()
        self.assertRegexpMatches(fido.bark(), __)

    # ------------------------------------------------------------------

    class Dog3:
        def __init__(self):
            self._name = None

        def get_name_from_instance(self):
            return self._name

        def set_name_from_instance(self, name):
            self._name = name

        @classmethod
        def get_name(cls):
            return cls._name

        @classmethod
        def set_name(cls, name):
            cls._name = name

        name = property(get_name, set_name)
        name_from_instance = property(get_name_from_instance, set_name_from_instance)

    def test_classmethods_can_not_be_used_as_properties(self):
        fido = self.Dog3()
        with self.assertRaises(___): fido.name = "Fido"

    def test_classes_and_instances_do_not_share_instance_attributes(self):
        fido = self.Dog3()
        fido.set_name_from_instance("Fido")
        fido.set_name("Rover")
        self.assertEqual(__, fido.get_name_from_instance())
        self.assertEqual(__, self.Dog3.get_name())

    def test_classes_and_instances_do_share_class_attributes(self):
        fido = self.Dog3()
        fido.set_name("Fido")
        self.assertEqual(__, fido.get_name())
        self.assertEqual(__, self.Dog3.get_name())

    # ------------------------------------------------------------------

    class Dog4:
        def a_class_method(cls):
            return 'dogs class method'

        def a_static_method():
            return 'dogs static method'

        a_class_method = classmethod(a_class_method)
        a_static_method = staticmethod(a_static_method)

    def test_you_can_define_class_methods_without_using_a_decorator(self):
        self.assertEqual(__, self.Dog4.a_class_method())

    def test_you_can_define_static_methods_without_using_a_decorator(self):
        self.assertEqual(__, self.Dog4.a_static_method())

    # ------------------------------------------------------------------

    def test_heres_an_easy_way_to_explicitly_call_class_methods_from_instance_methods(self):
        fido = self.Dog4()
        self.assertEqual(__, fido.__class__.a_class_method())

########NEW FILE########
__FILENAME__ = about_comprehension
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutComprehension(Koan):


    def test_creating_lists_with_list_comprehensions(self):
        feast = ['lambs', 'sloths', 'orangutans', 'breakfast cereals',
            'fruit bats']

        comprehension = [delicacy.capitalize() for delicacy in feast]

        self.assertEqual(__, comprehension[0])
        self.assertEqual(__, comprehension[2])

    def test_filtering_lists_with_list_comprehensions(self):
        feast = ['spam', 'sloths', 'orangutans', 'breakfast cereals',
            'fruit bats']

        comprehension = [delicacy for delicacy in feast if len(delicacy) > 6]

        self.assertEqual(__, len(feast))
        self.assertEqual(__, len(comprehension))

    def test_unpacking_tuples_in_list_comprehensions(self):
        list_of_tuples = [(1, 'lumberjack'), (2, 'inquisition'), (4, 'spam')]
        comprehension = [ skit * number for number, skit in list_of_tuples ]

        self.assertEqual(__, comprehension[0])
        self.assertEqual(__, comprehension[2])

    def test_double_list_comprehension(self):
        list_of_eggs = ['poached egg', 'fried egg']
        list_of_meats = ['lite spam', 'ham spam', 'fried spam']


        comprehension = [ '{0} and {1}'.format(egg, meat) for egg in list_of_eggs for meat in list_of_meats]


        self.assertEqual(__, comprehension[0])
        self.assertEqual(__, len(comprehension))

    def test_creating_a_set_with_set_comprehension(self):
        comprehension = { x for x in 'aabbbcccc'}

        self.assertEqual(__, comprehension)  # remember that set members are unique

    def test_creating_a_dictionary_with_dictionary_comprehension(self):
        dict_of_weapons = {'first': 'fear', 'second': 'surprise',
                           'third':'ruthless efficiency', 'forth':'fanatical devotion',
                           'fifth': None}

        dict_comprehension = { k.upper(): weapon for k, weapon in dict_of_weapons.items() if weapon}

        self.assertEqual(__, 'first' in dict_comprehension)
        self.assertEqual(__, 'FIRST' in dict_comprehension)
        self.assertEqual(__, len(dict_of_weapons))
        self.assertEqual(__, len(dict_comprehension))

########NEW FILE########
__FILENAME__ = about_control_statements
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutControlStatements(Koan):

    def test_if_then_else_statements(self):
        if True:
            result = 'true value'
        else:
            result = 'false value'
        self.assertEqual(__, result)

    def test_if_then_statements(self):
        result = 'default value'
        if True:
            result = 'true value'
        self.assertEqual(__, result)
        
    def test_if_then_elif_else_statements(self):
        if False:
            result = 'first value'
        elif True: 
            result = 'true value'
        else:
            result = 'default value'
        self.assertEqual(__, result)

    def test_while_statement(self):
        i = 1
        result = 1
        while i <= 10:
            result = result * i
            i += 1
        self.assertEqual(__, result)

    def test_break_statement(self):
        i = 1
        result = 1
        while True:
            if i > 10: break
            result = result * i
            i += 1
        self.assertEqual(__, result)

    def test_continue_statement(self):
        i = 0
        result = []
        while i < 10:
            i += 1
            if (i % 2) == 0: continue
            result.append(i)
        self.assertEqual(__, result)

    def test_for_statement(self):
        phrase = ["fish", "and", "chips"]
        result = []
        for item in phrase:
            result.append(item.upper())
        self.assertEqual([__, __, __], result)

    def test_for_statement_with_tuples(self):
        round_table = [
            ("Lancelot", "Blue"),
            ("Galahad", "I don't know!"),
            ("Robin", "Blue! I mean Green!"),
            ("Arthur", "Is that an African Swallow or Amazonian Swallow?")
        ]
        result = []
        for knight, answer in round_table:
            result.append("Contestant: '" + knight + "'   Answer: '" + answer + "'")

        text = __

        self.assertRegexpMatches(result[2], text)

        self.assertNoRegexpMatches(result[0], text)
        self.assertNoRegexpMatches(result[1], text)
        self.assertNoRegexpMatches(result[3], text)

########NEW FILE########
__FILENAME__ = about_decorating_with_classes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

import functools

class AboutDecoratingWithClasses(Koan):
    def maximum(self, a, b):
        if a>b:
            return a
        else:
            return b

    def test_partial_that_wrappers_no_args(self):
        """
        Before we can understand this type of decorator we need to consider
        the partial.
        """
        max = functools.partial(self.maximum)

        self.assertEqual(__, max(7,23))
        self.assertEqual(__, max(10,-10))

    def test_partial_that_wrappers_first_arg(self):
        max0 = functools.partial(self.maximum, 0)

        self.assertEqual(__, max0(-4))
        self.assertEqual(__, max0(5))

    def test_partial_that_wrappers_all_args(self):
        always99 = functools.partial(self.maximum, 99, 20)
        always20 = functools.partial(self.maximum, 9, 20)

        self.assertEqual(__, always99())
        self.assertEqual(__, always20())

    # ------------------------------------------------------------------

    class doubleit:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args):
            return self.fn(*args) + ', ' + self.fn(*args)

        def __get__(self, obj, cls=None):
            if not obj:
                # Decorating an unbound function
                return self
            else:
                # Decorating a bound method
                return functools.partial(self, obj)

    @doubleit
    def foo(self):
        return "foo"

    @doubleit
    def parrot(self, text):
        return text.upper()

    def test_decorator_with_no_arguments(self):
        # To clarify: the decorator above the function has no arguments, even
        # if the decorated function does

        self.assertEqual(__, self.foo())
        self.assertEqual(__, self.parrot('pieces of eight'))

    # ------------------------------------------------------------------

    def sound_check(self):
        #Note: no decorator
        return "Testing..."

    def test_what_a_decorator_is_doing_to_a_function(self):
        #wrap the function with the decorator
        self.sound_check = self.doubleit(self.sound_check)

        self.assertEqual(__, self.sound_check())

    # ------------------------------------------------------------------

    class documenter:
        def __init__(self, *args):
            self.fn_doc = args[0]

        def __call__(self, fn):
            def decorated_function(*args):
                return fn(*args)

            if fn.__doc__:
                decorated_function.__doc__ = fn.__doc__ + ": " + self.fn_doc
            else:
                decorated_function.__doc__ = self.fn_doc
            return decorated_function

    @documenter("Increments a value by one. Kind of.")
    def count_badly(self, num):
        num += 1
        if num==3:
            return 5
        else:
            return num
    @documenter("Does nothing")
    def idler(self, num):
        "Idler"
        pass

    def test_decorator_with_an_argument(self):
        self.assertEqual(__, self.count_badly(2))
        self.assertEqual(__, self.count_badly.__doc__)

    def test_documentor_which_already_has_a_docstring(self):
        self.assertEqual(__, self.idler.__doc__)

    # ------------------------------------------------------------------

    @documenter("DOH!")
    @doubleit
    @doubleit
    def homer(self):
        return "D'oh"

    def test_we_can_chain_decorators(self):
        self.assertEqual(__, self.homer())
        self.assertEqual(__, self.homer.__doc__)


########NEW FILE########
__FILENAME__ = about_decorating_with_functions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *


class AboutDecoratingWithFunctions(Koan):
    def addcowbell(fn):
        fn.wow_factor = 'COWBELL BABY!'
        return fn

    @addcowbell
    def mediocre_song(self):
        return "o/~ We all live in a broken submarine o/~"

    def test_decorators_can_modify_a_function(self):
        self.assertRegexpMatches(self.mediocre_song(), __)
        self.assertEqual(__, self.mediocre_song.wow_factor)

    # ------------------------------------------------------------------

    def xmltag(fn):
        def func(*args):
            return '<' + fn(*args) + '/>'
        return func

    @xmltag
    def render_tag(self, name):
        return name

    def test_decorators_can_change_a_function_output(self):
        self.assertEqual(__, self.render_tag('llama'))


########NEW FILE########
__FILENAME__ = about_deleting_objects
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutDeletingObjects(Koan):
    def test_del_can_remove_slices(self):
        lottery_nums = [4, 8, 15, 16, 23, 42]
        del lottery_nums[1]
        del lottery_nums[2:4]

        self.assertEqual(___, lottery_nums)

    def test_del_can_remove_entire_lists(self):
        lottery_nums = [4, 8, 15, 16, 23, 42]
        del lottery_nums

        with self.assertRaises(___): win = lottery_nums

    # ====================================================================

    class ClosingSale:
        def __init__(self):
            self.hamsters = 7
            self.zebras = 84

        def cameras(self):
            return 34

        def toilet_brushes(self):
            return 48

        def jellies(self):
            return 5

    def test_del_can_remove_attributes(self):
        crazy_discounts = self.ClosingSale()
        del self.ClosingSale.toilet_brushes
        del crazy_discounts.hamsters

        try:
            still_available = crazy_discounts.toilet_brushes()
        except AttributeError as e:
            err_msg1 = e.args[0]

        try:
            still_available = crazy_discounts.hamsters
        except AttributeError as e:
            err_msg2 = e.args[0]

        self.assertRegexpMatches(err_msg1, __)
        self.assertRegexpMatches(err_msg2, __)

    # ====================================================================

    class ClintEastwood:
        def __init__(self):
            self._name = None

        def get_name(self):
            try:
                return self._name
            except:
                return "The man with no name"

        def set_name(self, name):
            self._name = name

        def del_name(self):
            del self._name

        name = property(get_name, set_name, del_name, \
            "Mr Eastwood's current alias")

    def test_del_works_with_properties(self):
        cowboy = self.ClintEastwood()
        cowboy.name = 'Senor Ninguno'
        self.assertEqual('Senor Ninguno', cowboy.name)

        del cowboy.name
        self.assertEqual(__, cowboy.name)


    # ====================================================================

    class Prisoner:
        def __init__(self):
            self._name = None

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, name):
            self._name = name

        @name.deleter
        def name(self):
            self._name = 'Number Six'

    def test_another_way_to_make_a_deletable_property(self):
        citizen = self.Prisoner()
        citizen.name = "Patrick"
        self.assertEqual('Patrick', citizen.name)

        del citizen.name
        self.assertEqual(__, citizen.name)

    # ====================================================================

    class MoreOrganisedClosingSale(ClosingSale):
        def __init__(self):
            self.last_deletion = None
            super().__init__()

        def __delattr__(self, attr_name):
            self.last_deletion = attr_name

    def tests_del_can_be_overriden(self):
        sale = self.MoreOrganisedClosingSale()
        self.assertEqual(__, sale.jellies())
        del sale.jellies
        self.assertEqual(__, sale.last_deletion)

########NEW FILE########
__FILENAME__ = about_dice_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

import random

class DiceSet:
    def __init__(self):
        self._values = None

    @property
    def values(self):
        return self._values

    def roll(self, n):
        # Needs implementing!
        # Tip: random.randint(min, max) can be used to generate random numbers
        pass

class AboutDiceProject(Koan):
    def test_can_create_a_dice_set(self):
        dice = DiceSet()
        self.assertTrue(dice)

    def test_rolling_the_dice_returns_a_set_of_integers_between_1_and_6(self):
        dice = DiceSet()

        dice.roll(5)
        self.assertTrue(isinstance(dice.values, list), "should be a list")
        self.assertEqual(5, len(dice.values))
        for value in dice.values:
            self.assertTrue(value >= 1 and value <= 6, "value " + str(value) + " must be between 1 and 6")

    def test_dice_values_do_not_change_unless_explicitly_rolled(self):
        dice = DiceSet()
        dice.roll(5)
        first_time = dice.values
        second_time = dice.values
        self.assertEqual(first_time, second_time)

    def test_dice_values_should_change_between_rolls(self):
        dice = DiceSet()

        dice.roll(5)
        first_time = dice.values

        dice.roll(5)
        second_time = dice.values

        self.assertNotEqual(first_time, second_time, \
            "Two rolls should not be equal")

        # THINK ABOUT IT:
        #
        # If the rolls are random, then it is possible (although not
        # likely) that two consecutive rolls are equal.  What would be a
        # better way to test this?

    def test_you_can_roll_different_numbers_of_dice(self):
        dice = DiceSet()

        dice.roll(3)
        self.assertEqual(3, len(dice.values))

        dice.roll(1)
        self.assertEqual(1, len(dice.values))

########NEW FILE########
__FILENAME__ = about_dictionaries
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutHashes in the Ruby Koans
#

from runner.koan import *

class AboutDictionaries(Koan):
    def test_creating_dictionaries(self):
        empty_dict = dict()
        self.assertEqual(dict, type(empty_dict))
        self.assertDictEqual({}, empty_dict)
        self.assertEqual(__, len(empty_dict))

    def test_dictionary_literals(self):
        empty_dict = {}
        self.assertEqual(dict, type(empty_dict))
        babel_fish = { 'one': 'uno', 'two': 'dos' }
        self.assertEqual(__, len(babel_fish))

    def test_accessing_dictionaries(self):
        babel_fish = { 'one': 'uno', 'two': 'dos' }
        self.assertEqual(__, babel_fish['one'])
        self.assertEqual(__, babel_fish['two'])

    def test_changing_dictionaries(self):
        babel_fish = { 'one': 'uno', 'two': 'dos' }
        babel_fish['one'] = 'eins'

        expected = { 'two': 'dos', 'one': __ }
        self.assertDictEqual(expected, babel_fish)

    def test_dictionary_is_unordered(self):
        dict1 = { 'one': 'uno', 'two': 'dos' }
        dict2 = { 'two': 'dos', 'one': 'uno' }

        self.assertEqual(__, dict1 == dict2)


    def test_dictionary_keys_and_values(self):
        babel_fish = {'one': 'uno', 'two': 'dos'}
        self.assertEqual(__, len(babel_fish.keys()))
        self.assertEqual(__, len(babel_fish.values()))
        self.assertEqual(__, 'one' in babel_fish.keys())
        self.assertEqual(__, 'two' in babel_fish.values())
        self.assertEqual(__, 'uno' in babel_fish.keys())
        self.assertEqual(__, 'dos' in babel_fish.values())

    def test_making_a_dictionary_from_a_sequence_of_keys(self):
        cards = {}.fromkeys(('red warrior', 'green elf', 'blue valkyrie', 'yellow dwarf', 'confused looking zebra'), 42)

        self.assertEqual(__, len(cards))
        self.assertEqual(__, cards['green elf'])
        self.assertEqual(__, cards['yellow dwarf'])


########NEW FILE########
__FILENAME__ = about_exceptions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutExceptions(Koan):

    class MySpecialError(RuntimeError):
        pass

    def test_exceptions_inherit_from_exception(self):
        mro = self.MySpecialError.mro()
        self.assertEqual(__, mro[1].__name__)
        self.assertEqual(__, mro[2].__name__)
        self.assertEqual(__, mro[3].__name__)
        self.assertEqual(__, mro[4].__name__)

    def test_try_clause(self):
        result = None
        try:
            self.fail("Oops")
        except Exception as ex:
            result = 'exception handled'

            ex2 = ex

        self.assertEqual(__, result)

        self.assertEqual(__, isinstance(ex2, Exception))
        self.assertEqual(__, isinstance(ex2, RuntimeError))

        self.assertTrue(issubclass(RuntimeError, Exception), \
            "RuntimeError is a subclass of Exception")

        self.assertEqual(__, ex2.args[0])

    def test_raising_a_specific_error(self):
        result = None
        try:
            raise self.MySpecialError("My Message")
        except self.MySpecialError as ex:
            result = 'exception handled'
            msg = ex.args[0]

        self.assertEqual(__, result)
        self.assertEqual(__, msg)

    def test_else_clause(self):
        result = None
        try:
            pass
        except RuntimeError:
            result = 'it broke'
            pass
        else:
            result = 'no damage done'

        self.assertEqual(__, result)


    def test_finally_clause(self):
        result = None
        try:
            self.fail("Oops")
        except:
            # no code here
            pass
        finally:
            result = 'always run'

        self.assertEqual(__, result)

########NEW FILE########
__FILENAME__ = about_extra_credit
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# EXTRA CREDIT:
#
# Create a program that will play the Greed Game.
# Rules for the game are in GREED_RULES.TXT.
#
# You already have a DiceSet class and score function you can use.
# Write a player class and a Game class to complete the project.  This
# is a free form assignment, so approach it however you desire.

from runner.koan import *

class AboutExtraCredit(Koan):
    # Write tests here. If you need extra test classes add them to the
    # test suite in runner/path_to_enlightenment.py
    def test_extra_credit_task(self):
        pass

########NEW FILE########
__FILENAME__ = about_generators
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Written in place of AboutBlocks in the Ruby Koans
#
# Note: Both blocks and generators use a yield keyword, but they behave
# a lot differently
#

from runner.koan import *

class AboutGenerators(Koan):

    def test_generating_values_on_the_fly(self):
        result = list()
        bacon_generator = (n + ' bacon' for n in ['crunchy','veggie','danish'])

        for bacon in bacon_generator:
            result.append(bacon)

        self.assertEqual(__, result)

    def test_generators_are_different_to_list_comprehensions(self):
        num_list = [x*2 for x in range(1,3)]
        num_generator = (x*2 for x in range(1,3))

        self.assertEqual(2, num_list[0])

        # A generator has to be iterated through.
        with self.assertRaises(___): num = num_generator[0]

        self.assertEqual(__, list(num_generator)[0])

        # Both list comprehensions and generators can be iterated though. However, a generator
        # function is only called on the first iteration. The values are generated on the fly
        # instead of stored.
        #
        # Generators are more memory friendly, but less versatile

    def test_generator_expressions_are_a_one_shot_deal(self):
        dynamite = ('Boom!' for n in range(3))

        attempt1 = list(dynamite)
        attempt2 = list(dynamite)

        self.assertEqual(__, list(attempt1))
        self.assertEqual(__, list(attempt2))

    # ------------------------------------------------------------------

    def simple_generator_method(self):
        yield 'peanut'
        yield 'butter'
        yield 'and'
        yield 'jelly'

    def test_generator_method_will_yield_values_during_iteration(self):
        result = list()
        for item in self.simple_generator_method():
            result.append(item)
        self.assertEqual(__, result)

    def test_coroutines_can_take_arguments(self):
        result = self.simple_generator_method()
        self.assertEqual(__, next(result))
        self.assertEqual(__, next(result))
        result.close()

    # ------------------------------------------------------------------

    def square_me(self, seq):
        for x in seq:
            yield x * x

    def test_generator_method_with_parameter(self):
        result = self.square_me(range(2,5))
        self.assertEqual(__, list(result))

    # ------------------------------------------------------------------

    def sum_it(self, seq):
        value = 0
        for num in seq:
            # The local state of 'value' will be retained between iterations
            value += num
            yield value

    def test_generator_keeps_track_of_local_variables(self):
        result = self.sum_it(range(2,5))
        self.assertEqual(__, list(result))

    # ------------------------------------------------------------------

    def generator_with_coroutine(self):
        result = yield
        yield result

    def test_generators_can_take_coroutines(self):
        generator = self.generator_with_coroutine()

        # THINK ABOUT IT:
        # Why is this line necessary?
        #
        # Hint: Read the "Specification: Sending Values into Generators"
        #       section of http://www.python.org/dev/peps/pep-0342/
        next(generator)

        self.assertEqual(__, generator.send(1 + 2))

    def test_before_sending_a_value_to_a_generator_next_must_be_called(self):
        generator = self.generator_with_coroutine()

        try:
            generator.send(1+2)
        except TypeError as ex:
          ex2 = ex

        self.assertRegexpMatches(ex2.args[0], __)

    # ------------------------------------------------------------------

    def yield_tester(self):
        value = yield
        if value:
            yield value
        else:
            yield 'no value'

    def test_generators_can_see_if_they_have_been_called_with_a_value(self):
        generator = self.yield_tester()
        next(generator)
        self.assertEqual('with value', generator.send('with value'))

        generator2 = self.yield_tester()
        next(generator2)
        self.assertEqual(__, next(generator2))

    def test_send_none_is_equivalent_to_next(self):
        generator = self.yield_tester()

        next(generator)
        # 'next(generator)' is exactly equivalent to 'generator.send(None)'
        self.assertEqual(__, generator.send(None))



########NEW FILE########
__FILENAME__ = about_inheritance
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutInheritance(Koan):
    class Dog:
        def __init__(self, name):
            self._name = name

        @property
        def name(self):
            return self._name

        def bark(self):
            return "WOOF"

    class Chihuahua(Dog):
        def wag(self):
            return "happy"

        def bark(self):
            return "yip"

    def test_subclasses_have_the_parent_as_an_ancestor(self):
        self.assertEqual(__, issubclass(self.Chihuahua, self.Dog))

    def test_this_all_classes_in_python_3_ultimately_inherit_from_object_class(self):
        self.assertEqual(__, issubclass(self.Chihuahua, object))

        # Note: This isn't the case in Python 2. In that version you have
        # to inherit from a built in class or object explicitly

    def test_instances_inherit_behavior_from_parent_class(self):
        chico = self.Chihuahua("Chico")
        self.assertEqual(__, chico.name)

    def test_subclasses_add_new_behavior(self):
        chico = self.Chihuahua("Chico")
        self.assertEqual(__, chico.wag())

        fido = self.Dog("Fido")
        with self.assertRaises(___): fido.wag()

    def test_subclasses_can_modify_existing_behavior(self):
        chico = self.Chihuahua("Chico")
        self.assertEqual(__, chico.bark())

        fido = self.Dog("Fido")
        self.assertEqual(__, fido.bark())

    # ------------------------------------------------------------------

    class BullDog(Dog):
        def bark(self):
            return super().bark() + ", GRR"
            # Note, super() is much simpler to use in Python 3!

    def test_subclasses_can_invoke_parent_behavior_via_super(self):
        ralph = self.BullDog("Ralph")
        self.assertEqual(__, ralph.bark())

    # ------------------------------------------------------------------

    class GreatDane(Dog):
        def growl(self):
            return super().bark() + ", GROWL"

    def test_super_works_across_methods(self):
        george = self.GreatDane("George")
        self.assertEqual(__, george.growl())

    # ---------------------------------------------------------

    class Pug(Dog):
        def __init__(self, name):
            pass

    class Greyhound(Dog):
        def __init__(self, name):
            super().__init__(name)

    def test_base_init_does_not_get_called_automatically(self):
        snoopy = self.Pug("Snoopy")
        with self.assertRaises(___): name = snoopy.name

    def test_base_init_has_to_be_called_explicitly(self):
        boxer = self.Greyhound("Boxer")
        self.assertEqual(__, boxer.name)
########NEW FILE########
__FILENAME__ = about_iteration
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutIteration(Koan):

    def test_iterators_are_a_type(self):
        it = iter(range(1,6))

        fib = 0

        for num in it:
            fib += num

        self.assertEqual(__ , fib)

    def test_iterating_with_next(self):
        stages = iter(['alpha','beta','gamma'])

        try:
            self.assertEqual(__, next(stages))
            next(stages)
            self.assertEqual(__, next(stages))
            next(stages)
        except StopIteration as ex:
            err_msg = 'Ran out of iterations'

        self.assertRegexpMatches(err_msg, __)

    # ------------------------------------------------------------------

    def add_ten(self, item):
        return item + 10

    def test_map_transforms_elements_of_a_list(self):
        seq = [1, 2, 3]
        mapped_seq = list()

        mapping = map(self.add_ten, seq)

        self.assertNotEqual(list, mapping.__class__)
        self.assertEqual(__, mapping.__class__)
        # In Python 3 built in iterator funcs return iterable view objects
        # instead of lists

        for item in mapping:
            mapped_seq.append(item)

        self.assertEqual(__, mapped_seq)

        # None, iterator methods actually return objects of iter type in
        # python 3. In python 2 map() would give you a list.

    def test_filter_selects_certain_items_from_a_list(self):
        def is_even(item):
            return (item % 2) == 0

        seq = [1, 2, 3, 4, 5, 6]
        even_numbers = list()

        for item in filter(is_even, seq):
            even_numbers.append(item)

        self.assertEqual(__, even_numbers)

    def test_just_return_first_item_found(self):
        def is_big_name(item):
            return len(item) > 4

        names = ["Jim", "Bill", "Clarence", "Doug", "Eli"]
        name = None

        iterator = filter(is_big_name, names)
        try:
            name = next(iterator)
        except StopIteration:
            msg = 'Ran out of big names'

        self.assertEqual(__, name)


    # ------------------------------------------------------------------

    def add(self,accum,item):
        return accum + item

    def multiply(self,accum,item):
        return accum * item

    def test_reduce_will_blow_your_mind(self):
        import functools
        # As of Python 3 reduce() has been demoted from a builtin function
        # to the functools module.

        result = functools.reduce(self.add, [2, 3, 4])
        self.assertEqual(__, result.__class__)
        # Reduce() syntax is same as Python 2

        self.assertEqual(__, result)

        result2 = functools.reduce(self.multiply, [2, 3, 4], 1)
        self.assertEqual(__, result2)

        # Extra Credit:
        # Describe in your own words what reduce does.

    # ------------------------------------------------------------------

    def test_use_pass_for_iterations_with_no_body(self):
        for num in range(1,5):
            pass

        self.assertEqual(__, num)

    # ------------------------------------------------------------------

    def test_all_iteration_methods_work_on_any_sequence_not_just_lists(self):
        # Ranges are an iterable sequence
        result = map(self.add_ten, range(1,4))
        self.assertEqual(__, list(result))

        try:
            file = open("example_file.txt")

            try:
                def make_upcase(line):
                    return line.strip().upper()
                upcase_lines = map(make_upcase, file.readlines())
                self.assertEqual(__, list(upcase_lines))
            finally:
                # Arg, this is ugly.
                # We will figure out how to fix this later.
                file.close()
        except IOError:
            # should never happen
            self.fail()

########NEW FILE########
__FILENAME__ = about_lambdas
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based slightly on the lambdas section of AboutBlocks in the Ruby Koans
#

from runner.koan import *

class AboutLambdas(Koan):
    def test_lambdas_can_be_assigned_to_variables_and_called_explicitly(self):
        add_one = lambda n: n + 1
        self.assertEqual(__, add_one(10))

    # ------------------------------------------------------------------

    def make_order(self, order):
        return lambda qty: str(qty) + " " + order + "s"

    def test_accessing_lambda_via_assignment(self):
        sausages = self.make_order('sausage')
        eggs = self.make_order('egg')

        self.assertEqual(__, sausages(3))
        self.assertEqual(__, eggs(2))

    def test_accessing_lambda_without_assignment(self):
        self.assertEqual(__, self.make_order('spam')(39823))

########NEW FILE########
__FILENAME__ = about_lists
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutArrays in the Ruby Koans
#

from runner.koan import *

class AboutLists(Koan):
    def test_creating_lists(self):
        empty_list = list()
        self.assertEqual(list, type(empty_list))
        self.assertEqual(__, len(empty_list))

    def test_list_literals(self):
        nums = list()
        self.assertEqual([], nums)

        nums[0:] = [1]
        self.assertEqual([1], nums)

        nums[1:] = [2]
        self.assertListEqual([1, __], nums)

        nums.append(333)
        self.assertListEqual([1, 2, __], nums)

    def test_accessing_list_elements(self):
        noms = ['peanut', 'butter', 'and', 'jelly']

        self.assertEqual(__, noms[0])
        self.assertEqual(__, noms[3])
        self.assertEqual(__, noms[-1])
        self.assertEqual(__, noms[-3])

    def test_slicing_lists(self):
        noms = ['peanut', 'butter', 'and', 'jelly']

        self.assertEqual(__, noms[0:1])
        self.assertEqual(__, noms[0:2])
        self.assertEqual(__, noms[2:2])
        self.assertEqual(__, noms[2:20])
        self.assertEqual(__, noms[4:0])
        self.assertEqual(__, noms[4:100])
        self.assertEqual(__, noms[5:0])

    def test_slicing_to_the_edge(self):
        noms = ['peanut', 'butter', 'and', 'jelly']

        self.assertEqual(__, noms[2:])
        self.assertEqual(__, noms[:2])

    def test_lists_and_ranges(self):
        self.assertEqual(range, type(range(5)))
        self.assertNotEqual([1, 2, 3, 4, 5], range(1,6))
        self.assertEqual(__, list(range(5)))
        self.assertEqual(__, list(range(5, 9)))

    def test_ranges_with_steps(self):
        self.assertEqual(__, list(range(0, 8, 2)))
        self.assertEqual(__, list(range(1, 8, 3)))
        self.assertEqual(__, list(range(5, -7, -4)))
        self.assertEqual(__, list(range(5, -8, -4)))

    def test_insertions(self):
        knight = ['you', 'shall', 'pass']
        knight.insert(2, 'not')
        self.assertEqual(__, knight)

        knight.insert(0, 'Arthur')
        self.assertEqual(__, knight)

    def test_popping_lists(self):
        stack = [10, 20, 30, 40]
        stack.append('last')

        self.assertEqual(__, stack)

        popped_value = stack.pop()
        self.assertEqual(__, popped_value)
        self.assertEqual(__, stack)

        popped_value = stack.pop(1)
        self.assertEqual(__, popped_value)
        self.assertEqual(__, stack)

        # Notice that there is a "pop" but no "push" in python?

        # Part of the Python philosophy is that there ideally should be one and
        # only one way of doing anything. A 'push' is the same as an 'append'.

        # To learn more about this try typing "import this" from the python
        # console... ;)

    def test_making_queues(self):
        queue = [1, 2]
        queue.append('last')

        self.assertEqual(__, queue)

        popped_value = queue.pop(0)
        self.assertEqual(__, popped_value)
        self.assertEqual(__, queue)

        # Note, for Python 2 popping from the left hand side of a list is
        # inefficient. Use collections.deque instead.

        # This is not an issue for Python 3 though


########NEW FILE########
__FILENAME__ = about_list_assignments
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutArrayAssignments in the Ruby Koans
#

from runner.koan import *

class AboutListAssignments(Koan):
    def test_non_parallel_assignment(self):
        names = ["John", "Smith"]
        self.assertEqual(__, names)

    def test_parallel_assignments(self):
        first_name, last_name = ["John", "Smith"]
        self.assertEqual(__, first_name)
        self.assertEqual(__, last_name)

    def test_parallel_assignments_with_extra_values(self):
        title, *first_names, last_name = ["Sir", "Ricky", "Bobby", "Worthington"]
        self.assertEqual(__, title)
        self.assertEqual(__, first_names)
        self.assertEqual(__, last_name)

    def test_parallel_assignments_with_sublists(self):
        first_name, last_name = [["Willie", "Rae"], "Johnson"]
        self.assertEqual(__, first_name)
        self.assertEqual(__, last_name)

    def test_swapping_with_parallel_assignment(self):
        first_name = "Roy"
        last_name = "Rob"
        first_name, last_name = last_name, first_name
        self.assertEqual(__, first_name)
        self.assertEqual(__, last_name)


########NEW FILE########
__FILENAME__ = about_methods
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Partially based on AboutMethods in the Ruby Koans
#

from runner.koan import *

def my_global_function(a,b):
    return a + b

class AboutMethods(Koan):
    def test_calling_a_global_function(self):
        self.assertEqual(__, my_global_function(2,3))

    # NOTE: Wrong number of arguments is not a SYNTAX error, but a
    # runtime error.
    def test_calling_functions_with_wrong_number_of_arguments(self):
        try:
            my_global_function()
        except TypeError as exception:
            msg = exception.args[0]

        # Note, the text comparison works for Python 3.2
        # It has changed in the past and may change in the future
        self.assertRegexpMatches(msg,
            r'my_global_function\(\) missing 2 required positional arguments')

        try:
            my_global_function(1, 2, 3)
        except Exception as e:
            msg = e.args[0]

        # Note, watch out for parenthesis. They need slashes in front!
        self.assertRegexpMatches(msg, __)

    # ------------------------------------------------------------------

    def pointless_method(self, a, b):
        sum = a + b

    def test_which_does_not_return_anything(self):
        self.assertEqual(__, self.pointless_method(1, 2))
        # Notice that methods accessed from class scope do not require
        # you to pass the first "self" argument?

    # ------------------------------------------------------------------

    def method_with_defaults(self, a, b='default_value'):
        return [a, b]

    def test_calling_with_default_values(self):
        self.assertEqual(__, self.method_with_defaults(1))
        self.assertEqual(__, self.method_with_defaults(1, 2))

    # ------------------------------------------------------------------

    def method_with_var_args(self, *args):
        return args

    def test_calling_with_variable_arguments(self):
        self.assertEqual(__, self.method_with_var_args())
        self.assertEqual(('one',), self.method_with_var_args('one'))
        self.assertEqual(__, self.method_with_var_args('one', 'two'))

    # ------------------------------------------------------------------

    def function_with_the_same_name(self, a, b):
        return a + b

    def test_functions_without_self_arg_are_global_functions(self):
        def function_with_the_same_name(a, b):
            return a * b

        self.assertEqual(__, function_with_the_same_name(3,4))

    def test_calling_methods_in_same_class_with_explicit_receiver(self):
        def function_with_the_same_name(a, b):
            return a * b

        self.assertEqual(__, self.function_with_the_same_name(3,4))

    # ------------------------------------------------------------------

    def another_method_with_the_same_name(self):
        return 10

    link_to_overlapped_method = another_method_with_the_same_name

    def another_method_with_the_same_name(self):
        return 42

    def test_that_old_methods_are_hidden_by_redefinitions(self):
        self.assertEqual(__, self.another_method_with_the_same_name())

    def test_that_overlapped_method_is_still_there(self):
        self.assertEqual(__, self.link_to_overlapped_method())

    # ------------------------------------------------------------------

    def empty_method(self):
        pass

    def test_methods_that_do_nothing_need_to_use_pass_as_a_filler(self):
        self.assertEqual(__, self.empty_method())

    def test_pass_does_nothing_at_all(self):
        "You"
        "shall"
        "not"
        pass
        self.assertEqual(____, "Still got to this line" != None)

    # ------------------------------------------------------------------

    def one_line_method(self): return 'Madagascar'

    def test_no_indentation_required_for_one_line_statement_bodies(self):
        self.assertEqual(__, self.one_line_method())

    # ------------------------------------------------------------------

    def method_with_documentation(self):
        "A string placed at the beginning of a function is used for documentation"
        return "ok"

    def test_the_documentation_can_be_viewed_with_the_doc_method(self):
        self.assertRegexpMatches(self.method_with_documentation.__doc__, __)

    # ------------------------------------------------------------------

    class Dog:
        def name(self):
            return "Fido"

        def _tail(self):
            # Prefixing a method with an underscore implies private scope
            return "wagging"

        def __password(self):
            return 'password' # Genius!

    def test_calling_methods_in_other_objects(self):
        rover = self.Dog()
        self.assertEqual(__, rover.name())

    def test_private_access_is_implied_but_not_enforced(self):
        rover = self.Dog()

        # This is a little rude, but legal
        self.assertEqual(__, rover._tail())

    def test_attributes_with_double_underscore_prefixes_are_subject_to_name_mangling(self):
        rover = self.Dog()
        with self.assertRaises(___): password = rover.__password()

        # But this still is!
        self.assertEqual(__, rover._Dog__password())

        # Name mangling exists to avoid name clash issues when subclassing.
        # It is not for providing effective access protection


########NEW FILE########
__FILENAME__ = about_method_bindings
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

def function():
    return "pineapple"

def function2():
    return "tractor"

class Class:
    def method(self):
        return "parrot"

class AboutMethodBindings(Koan):
    def test_methods_are_bound_to_an_object(self):
        obj = Class()
        self.assertEqual(__, obj.method.__self__ == obj)

    def test_methods_are_also_bound_to_a_function(self):
        obj = Class()
        self.assertEqual(__, obj.method())
        self.assertEqual(__, obj.method.__func__(obj))

    def test_functions_have_attributes(self):
        obj = Class()
        self.assertEqual(__, len(dir(function)))
        self.assertEqual(__, dir(function) == dir(obj.method.__func__))

    def test_methods_have_different_attributes(self):
        obj = Class()
        self.assertEqual(__, len(dir(obj.method)))

    def test_setting_attributes_on_an_unbound_function(self):
        function.cherries = 3
        self.assertEqual(__, function.cherries)

    def test_setting_attributes_on_a_bound_method_directly(self):
        obj = Class()
        with self.assertRaises(___): obj.method.cherries = 3

    def test_setting_attributes_on_methods_by_accessing_the_inner_function(self):
        obj = Class()
        obj.method.__func__.cherries = 3
        self.assertEqual(__, obj.method.cherries)

    def test_functions_can_have_inner_functions(self):
        function2.get_fruit = function
        self.assertEqual(__, function2.get_fruit())

    def test_inner_functions_are_unbound(self):
        function2.get_fruit = function
        with self.assertRaises(___): cls = function2.get_fruit.__self__

    # ------------------------------------------------------------------

    class BoundClass:
        def __get__(self, obj, cls):
            return (self, obj, cls)

    binding = BoundClass()

    def test_get_descriptor_resolves_attribute_binding(self):
        bound_obj, binding_owner, owner_type = self.binding
        # Look at BoundClass.__get__():
        #   bound_obj = self
        #   binding_owner = obj
        #   owner_type = cls

        self.assertEqual(__, bound_obj.__class__.__name__)
        self.assertEqual(__, binding_owner.__class__.__name__)
        self.assertEqual(AboutMethodBindings, owner_type)

    # ------------------------------------------------------------------

    class SuperColor:
        def __init__(self):
            self.choice = None

        def __set__(self, obj, val):
            self.choice = val

    color = SuperColor()

    def test_set_descriptor_changes_behavior_of_attribute_assignment_changes(self):
        self.assertEqual(None, self.color.choice)
        self.color = 'purple'
        self.assertEqual(__, self.color.choice)


########NEW FILE########
__FILENAME__ = about_modules
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# This is very different to AboutModules in Ruby Koans
# Our AboutMultipleInheritance class is a little more comparable
#

from runner.koan import *

from .another_local_module import *
from .local_module_with_all_defined import *

class AboutModules(Koan):
    def test_importing_other_python_scripts_as_modules(self):
        from . import local_module # local_module.py

        duck = local_module.Duck()
        self.assertEqual(__, duck.name)

    def test_importing_attributes_from_classes_using_from_keyword(self):
        from .local_module import Duck

        duck = Duck() # no module qualifier needed this time
        self.assertEqual(__, duck.name)

    def test_we_can_import_multiple_items_at_once(self):
        from . import jims, joes

        jims_dog = jims.Dog()
        joes_dog = joes.Dog()
        self.assertEqual(__, jims_dog.identify())
        self.assertEqual(__, joes_dog.identify())

    def test_importing_all_module_attributes_at_once(self):
        # NOTE Using this module level import declared at the top of this script:
        #   from .another_local_module import *
        #
        # Import wildcard cannot be used from within classes or functions

        goose = Goose()
        hamster = Hamster()

        self.assertEqual(__, goose.name)
        self.assertEqual(__, hamster.name)

    def test_modules_hide_attributes_prefixed_by_underscores(self):
        with self.assertRaises(___): private_squirrel = _SecretSquirrel()

    def test_private_attributes_are_still_accessible_in_modules(self):
        from .local_module import Duck # local_module.py

        duck = Duck()
        self.assertEqual(__, duck._password)
        # module level attribute hiding doesn't affect class attributes
        # (unless the class itself is hidden).

    def test_a_module_can_choose_which_attributes_are_available_to_wildcards(self):
        # NOTE Using this module level import declared at the top of this script:
        #   from .local_module_with_all_defined import *

        # 'Goat' is on the __ALL__ list
        goat = Goat()
        self.assertEqual(__, goat.name)

        # How about velociraptors?
        lizard = _Velociraptor()
        self.assertEqual(__, lizard.name)

        # SecretDuck? Never heard of her!
        with self.assertRaises(___): duck = SecretDuck()

########NEW FILE########
__FILENAME__ = about_monkey_patching
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Related to AboutOpenClasses in the Ruby Koans
#

from runner.koan import *

class AboutMonkeyPatching(Koan):
    class Dog:
        def bark(self):
            return "WOOF"

    def test_as_defined_dogs_do_bark(self):
        fido = self.Dog()
        self.assertEqual(__, fido.bark())

    # ------------------------------------------------------------------

    # Add a new method to an existing class.
    def test_after_patching_dogs_can_both_wag_and_bark(self):
        def wag(self): return "HAPPY"
        self.Dog.wag = wag

        fido = self.Dog()
        self.assertEqual(__, fido.wag())
        self.assertEqual(__, fido.bark())

    # ------------------------------------------------------------------

    def test_most_built_in_classes_cannot_be_monkey_patched(self):
        try:
            int.is_even = lambda self: (self % 2) == 0
        except Exception as ex:
            err_msg = ex.args[0]

        self.assertRegexpMatches(err_msg, __)

    # ------------------------------------------------------------------

    class MyInt(int): pass

    def test_subclasses_of_built_in_classes_can_be_be_monkey_patched(self):
        self.MyInt.is_even = lambda self: (self % 2) == 0

        self.assertEqual(__, self.MyInt(1).is_even())
        self.assertEqual(__, self.MyInt(2).is_even())


########NEW FILE########
__FILENAME__ = about_multiple_inheritance
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Slightly based on AboutModules in the Ruby Koans
#

from runner.koan import *

class AboutMultipleInheritance(Koan):
    class Nameable:
        def __init__(self):
            self._name = None

        def set_name(self, new_name):
            self._name = new_name

        def here(self):
            return "In Nameable class"

    class Animal:
        def legs(self):
            return 4

        def can_climb_walls(self):
            return False

        def here(self):
            return "In Animal class"

    class Pig(Animal):
        def __init__(self):
            super().__init__()
            self._name = "Jasper"

        @property
        def name(self):
            return self._name

        def speak(self):
            return "OINK"

        def color(self):
            return 'pink'

        def here(self):
            return "In Pig class"

    class Spider(Animal):
        def __init__(self):
            super().__init__()
            self._name = "Boris"

        def can_climb_walls(self):
            return True

        def legs(self):
            return 8

        def color(self):
            return 'black'

        def here(self):
            return "In Spider class"

    class Spiderpig(Pig, Spider, Nameable):
        def __init__(self):
            super(AboutMultipleInheritance.Pig, self).__init__()
            super(AboutMultipleInheritance.Nameable, self).__init__()
            self._name = "Jeff"

        def speak(self):
            return "This looks like a job for Spiderpig!"

        def here(self):
            return "In Spiderpig class"

    #
    # Hierarchy:
    #               Animal
    #              /     \
    #            Pig   Spider  Nameable
    #              \      |      /
    #                 Spiderpig
    #
    # ------------------------------------------------------------------

    def test_normal_methods_are_available_in_the_object(self):
        jeff = self.Spiderpig()
        self.assertRegexpMatches(jeff.speak(), __)

    def test_base_class_methods_are_also_available_in_the_object(self):
        jeff = self.Spiderpig()
        try:
            jeff.set_name("Rover")
        except:
            self.fail("This should not happen")
        self.assertEqual(__, jeff.can_climb_walls())

    def test_base_class_methods_can_affect_instance_variables_in_the_object(self):
        jeff = self.Spiderpig()
        self.assertEqual(__, jeff.name)

        jeff.set_name("Rover")
        self.assertEqual(__, jeff.name)

    def test_left_hand_side_inheritance_tends_to_be_higher_priority(self):
        jeff = self.Spiderpig()
        self.assertEqual(__, jeff.color())

    def test_super_class_methods_are_higher_priority_than_super_super_classes(self):
        jeff = self.Spiderpig()
        self.assertEqual(__, jeff.legs())

    def test_we_can_inspect_the_method_resolution_order(self):
        #
        # MRO = Method Resolution Order
        #
        mro = type(self.Spiderpig()).mro()
        self.assertEqual('Spiderpig', mro[0].__name__)
        self.assertEqual('Pig', mro[1].__name__)
        self.assertEqual(__, mro[2].__name__)
        self.assertEqual(__, mro[3].__name__)
        self.assertEqual(__, mro[4].__name__)
        self.assertEqual(__, mro[5].__name__)

    def test_confirm_the_mro_controls_the_calling_order(self):
        jeff = self.Spiderpig()
        self.assertRegexpMatches(jeff.here(), 'Spiderpig')

        next = super(AboutMultipleInheritance.Spiderpig, jeff)
        self.assertRegexpMatches(next.here(), 'Pig')

        next = super(AboutMultipleInheritance.Pig, jeff)
        self.assertRegexpMatches(next.here(), __)

        # Hang on a minute?!? That last class name might be a super class of
        # the 'jeff' object, but its hardly a superclass of Pig, is it?
        #
        # To avoid confusion it may help to think of super() as next_mro().


########NEW FILE########
__FILENAME__ = about_none
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutNil in the Ruby Koans
#

from runner.koan import *

class AboutNone(Koan):

    def test_none_is_an_object(self):
        "Unlike NULL in a lot of languages"
        self.assertEqual(__, isinstance(None, object))

    def test_none_is_universal(self):
        "There is only one None"
        self.assertEqual(____, None is None)

    def test_what_exception_do_you_get_when_calling_nonexistent_methods(self):
        """
        What is the Exception that is thrown when you call a method that does
        not exist?

        Hint: launch python command console and try the code in the block below.

        Don't worry about what 'try' and 'except' do, we'll talk about this later
        """
        try:
            None.some_method_none_does_not_know_about()
        except Exception as ex:
            ex2 = ex

        # What exception has been caught?
        #
        # Need a recap on how to evaluate __class__ attributes?
        #
        #     http://bit.ly/__class__

        self.assertEqual(__, ex2.__class__)

        # What message was attached to the exception?
        # (HINT: replace __ with part of the error message.)
        self.assertRegexpMatches(ex2.args[0], __)

    def test_none_is_distinct(self):
        """
        None is distinct from other things which are False.
        """
        self.assertEqual(__, None is not 0)
        self.assertEqual(__, None is not False)

########NEW FILE########
__FILENAME__ = about_packages
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# This is very different to AboutModules in Ruby Koans
# Our AboutMultipleInheritance class is a little more comparable
#

from runner.koan import *

#
# Package hierarchy of Python Koans project:
#
# contemplate_koans.py
# koans/
#     __init__.py
#     about_asserts.py
#     about_attribute_access.py
#     about_class_attributes.py
#     about_classes.py
#     ...
#     a_package_folder/
#         __init__.py
#         a_module.py

class AboutPackages(Koan):
    def test_subfolders_can_form_part_of_a_module_package(self):
        # Import ./a_package_folder/a_module.py
        from .a_package_folder.a_module import Duck

        duck = Duck()
        self.assertEqual(__, duck.name)

    def test_subfolders_become_modules_if_they_have_an_init_module(self):
        # Import ./a_package_folder/__init__.py
        from .a_package_folder import an_attribute

        self.assertEqual(__, an_attribute)

    # ------------------------------------------------------------------

    def test_use_absolute_imports_to_import_upper_level_modules(self):
        # Import /contemplate_koans.py
        import contemplate_koans

        self.assertEqual(__, contemplate_koans.__name__)

        # contemplate_koans.py is the root module in this package because its
        # the first python module called in koans.
        #
        # If contemplate_koan.py was based in a_package_folder that would be
        # the root folder, which would make reaching the koans folder
        # almost impossible. So always leave the starting python script in
        # a folder which can reach everything else.

    def test_import_a_module_in_a_subfolder_folder_using_an_absolute_path(self):
        # Import contemplate_koans.py/koans/a_package_folder/a_module.py
        from koans.a_package_folder.a_module import Duck

        self.assertEqual(__, Duck.__module__)

########NEW FILE########
__FILENAME__ = about_proxy_object_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Project: Create a Proxy Class
#
# In this assignment, create a proxy class (one is started for you
# below).  You should be able to initialize the proxy object with any
# object.  Any attributes called on the proxy object should be forwarded
# to the target object.  As each attribute call is sent, the proxy should
# record the name of the attribute sent.
#
# The proxy class is started for you.  You will need to add a method
# missing handler and any other supporting methods.  The specification
# of the Proxy class is given in the AboutProxyObjectProject koan.

# Note: This is a bit trickier than its Ruby Koans counterpart, but you
# can do it!

from runner.koan import *

class Proxy:
    def __init__(self, target_object):
        # WRITE CODE HERE

        #initialize '_obj' attribute last. Trust me on this!
        self._obj = target_object

    # WRITE CODE HERE

# The proxy object should pass the following Koan:
#
class AboutProxyObjectProject(Koan):
    def test_proxy_method_returns_wrapped_object(self):
        # NOTE: The Television class is defined below
        tv = Proxy(Television())

        self.assertTrue(isinstance(tv, Proxy))

    def test_tv_methods_still_perform_their_function(self):
        tv = Proxy(Television())

        tv.channel = 10
        tv.power()

        self.assertEqual(10, tv.channel)
        self.assertTrue(tv.is_on())

    def test_proxy_records_messages_sent_to_tv(self):
        tv = Proxy(Television())

        tv.power()
        tv.channel = 10

        self.assertEqual(['power', 'channel'], tv.messages())

    def test_proxy_handles_invalid_messages(self):
        tv = Proxy(Television())

        ex = None
        with self.assertRaises(AttributeError):
            tv.no_such_method()


    def test_proxy_reports_methods_have_been_called(self):
        tv = Proxy(Television())

        tv.power()
        tv.power()

        self.assertTrue(tv.was_called('power'))
        self.assertFalse(tv.was_called('channel'))

    def test_proxy_counts_method_calls(self):
        tv = Proxy(Television())

        tv.power()
        tv.channel = 48
        tv.power()

        self.assertEqual(2, tv.number_of_times_called('power'))
        self.assertEqual(1, tv.number_of_times_called('channel'))
        self.assertEqual(0, tv.number_of_times_called('is_on'))

    def test_proxy_can_record_more_than_just_tv_objects(self):
        proxy = Proxy("Py Ohio 2010")

        result = proxy.upper()

        self.assertEqual("PY OHIO 2010", result)

        result = proxy.split()

        self.assertEqual(["Py", "Ohio", "2010"], result)
        self.assertEqual(['upper', 'split'], proxy.messages())

# ====================================================================
# The following code is to support the testing of the Proxy class.  No
# changes should be necessary to anything below this comment.

# Example class using in the proxy testing above.
class Television:
    def __init__(self):
        self._channel = None
        self._power = None

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value

    def power(self):
        if self._power == 'on':
            self._power = 'off'
        else:
            self._power = 'on'

    def is_on(self):
        return self._power == 'on'

# Tests for the Television class.  All of theses tests should pass.
class TelevisionTest(Koan):
    def test_it_turns_on(self):
        tv = Television()

        tv.power()
        self.assertTrue(tv.is_on())

    def test_it_also_turns_off(self):
        tv = Television()

        tv.power()
        tv.power()

        self.assertFalse(tv.is_on())

    def test_edge_case_on_off(self):
        tv = Television()

        tv.power()
        tv.power()
        tv.power()

        self.assertTrue(tv.is_on())

        tv.power()

        self.assertFalse(tv.is_on())

    def test_can_set_the_channel(self):
        tv = Television()

        tv.channel = 11
        self.assertEqual(11, tv.channel)

########NEW FILE########
__FILENAME__ = about_regex
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *
import re
class AboutRegex(Koan):
    """
        These koans are based on the Ben's book: Regular Expressions in 10 minutes.
        I found this books very useful so I decided to write a koans in order to practice everything I had learned from it.
        http://www.forta.com/books/0672325667/
    """

    def test_matching_literal_text(self):
        """
            Lesson 1 Matching Literal String
        """
        string = "Hello, my name is Felix and this koans are based on the Ben's book: Regular Expressions in 10 minutes."
        m = re.search(__, string)
        self.assertTrue(m and m.group(0) and m.group(0)== 'Felix', "I want my name")

    def test_matching_literal_text_how_many(self):
        """
            Lesson 1 How many matches?

            The default behaviour of most regular expression engines is to return just the first match.
            In python you have the next options:

                match()    -->  Determine if the RE matches at the beginning of the string.
                search()   -->  Scan through a string, looking for any location where this RE matches.
                findall()  -->  Find all substrings where the RE matches, and returns them as a list.
                finditer() -->  Find all substrings where the RE matches, and returns them as an iterator.

        """
        string = "Hello, my name is Felix and this koans are based on the Ben's book: Regular Expressions in 10 minutes. Repeat My name is Felix"
        m = re.match('Felix', string) #TIP: Maybe match it's not the best option

        # I want to know how many times appears my name
        self.assertEqual(m, __)

    def test_matching_literal_text_not_case_sensitivity(self):
        """
            Lesson 1 Matching Literal String non case sensitivity.
            Most regex implementations also support matches that are not case sensitive. In python you can use re.IGNORECASE, in
            Javascript you can specify the optional i flag.
            In Ben's book you can see more languages.

        """
        string = "Hello, my name is Felix or felix and this koans is based on the Ben's book: Regular Expressions in 10 minutes."

        self.assertEqual(re.findall("felix", string), __)
        self.assertEqual(re.findall("felix", string, re.IGNORECASE), __)

    def test_matching_any_character(self):
        """
            Lesson 1 Matching any character

            . matches any character, alphabetic characters, digits and .
        """
        string = "pecks.xlx\n"    \
                + "orders1.xls\n" \
                + "apec1.xls\n"   \
                + "na1.xls\n"     \
                + "na2.xls\n"     \
                + "sa1.xls"

        # TIP: remember the name of this lesson

        change_this_search_string = 'a..xlx' # <-- I want to find all uses of myArray
        self.assertEquals(len(re.findall(change_this_search_string, string)),3)

    def test_matching_set_character(self):
        """
            Lesson 2 Matching sets of characters

            A set of characters is defined using the metacharacters [ and ]. Everything between them is part of the set and
            any one of the set members must match (but not all).
        """
        string = "sales.xlx\n"    \
                + "sales1.xls\n"  \
                + "orders3.xls\n" \
                + "apac1.xls\n" \
                + "sales2.xls\n"  \
                + "na1.xls\n"  \
                + "na2.xls\n"  \
                + "sa1.xls\n"  \
                + "ca1.xls"
        # I want to find all files for North America(na) or South America(sa), but not (ca)
        # TIP you can use the pattern .a. which matches in above test but in this case matches more than you want
        change_this_search_string = '[nsc]a[2-9].xls'
        self.assertEquals(len(re.findall(change_this_search_string, string)),3)

    def test_anything_but_matching(self):
        """
            Lesson 2 Using character set ranges
            Occasionally, you'll want a list of characters that you don't want to match.
            Character sets can be negated using the ^ metacharacter.

        """
        string = "sales.xlx\n"    \
                + "sales1.xls\n"  \
                + "orders3.xls\n" \
                + "apac1.xls\n" \
                + "sales2.xls\n"  \
                + "sales3.xls\n"  \
                + "europe2.xls\n"  \
                + "sam.xls\n"  \
                + "na1.xls\n"  \
                + "na2.xls\n"  \
                + "sa1.xls\n"  \
                + "ca1.xls"

        # I want to find the name sam
        change_this_search_string = '[^nc]am'
        self.assertEquals(re.findall(change_this_search_string, string), ['sam.xls'])



########NEW FILE########
__FILENAME__ = about_scope
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

from . import jims
from . import joes

counter = 0 # Global

class AboutScope(Koan):
    #
    # NOTE:
    #   Look in jims.py and joes.py to see definitions of Dog used
    #   for this set of tests
    #

    def test_dog_is_not_available_in_the_current_scope(self):
        with self.assertRaises(___): fido = Dog()

    def test_you_can_reference_nested_classes_using_the_scope_operator(self):
        fido = jims.Dog()
        # name 'jims' module name is taken from jims.py filename

        rover = joes.Dog()
        self.assertEqual(__, fido.identify())
        self.assertEqual(__, rover.identify())

        self.assertEqual(__, type(fido) == type(rover))
        self.assertEqual(__, jims.Dog == joes.Dog)

    # ------------------------------------------------------------------

    class str:
        pass

    def test_bare_bones_class_names_do_not_assume_the_current_scope(self):
        self.assertEqual(__, AboutScope.str == str)

    def test_nested_string_is_not_the_same_as_the_system_string(self):
        self.assertEqual(__, self.str == type("HI"))

    def test_str_without_self_prefix_stays_in_the_global_scope(self):
        self.assertEqual(__, str == type("HI"))

    # ------------------------------------------------------------------

    PI = 3.1416

    def test_constants_are_defined_with_an_initial_uppercase_letter(self):
        self.assertAlmostEqual(_____, self.PI)
        # Note, floating point numbers in python are not precise.
        # assertAlmostEqual will check that it is 'close enough'

    def test_constants_are_assumed_by_convention_only(self):
        self.PI = "rhubarb"
        self.assertEqual(_____, self.PI)
        # There aren't any real constants in python. Its up to the developer
        # to keep to the convention and not modify them.

    # ------------------------------------------------------------------

    def increment_using_local_counter(self, counter):
        counter = counter + 1

    def increment_using_global_counter(self):
        global counter
        counter = counter + 1

    def test_incrementing_with_local_counter(self):
        global counter
        start = counter
        self.increment_using_local_counter(start)
        self.assertEqual(__, counter == start + 1)

    def test_incrementing_with_global_counter(self):
        global counter
        start = counter
        self.increment_using_global_counter()
        self.assertEqual(__, counter == start + 1)

    # ------------------------------------------------------------------

    def local_access(self):
        stuff = 'eels'
        def from_the_league():
            stuff = 'this is a local shop for local people'
            return stuff
        return from_the_league()

    def nonlocal_access(self):
        stuff = 'eels'
        def from_the_boosh():
            nonlocal stuff
            return stuff
        return from_the_boosh()

    def test_getting_something_locally(self):
        self.assertEqual(__, self.local_access())

    def test_getting_something_nonlocally(self):
        self.assertEqual(__, self.nonlocal_access())

    # ------------------------------------------------------------------

    global deadly_bingo
    deadly_bingo = [4, 8, 15, 16, 23, 42]

    def test_global_attributes_can_be_created_in_the_middle_of_a_class(self):
        self.assertEqual(__, deadly_bingo[5])

########NEW FILE########
__FILENAME__ = about_scoring_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

# Greed is a dice game where you roll up to five dice to accumulate
# points.  The following "score" function will be used calculate the
# score of a single roll of the dice.
#
# A greed roll is scored as follows:
#
# * A set of three ones is 1000 points
#
# * A set of three numbers (other than ones) is worth 100 times the
#   number. (e.g. three fives is 500 points).
#
# * A one (that is not part of a set of three) is worth 100 points.
#
# * A five (that is not part of a set of three) is worth 50 points.
#
# * Everything else is worth 0 points.
#
#
# Examples:
#
# score([1,1,1,5,1]) => 1150 points
# score([2,3,4,6,2]) => 0 points
# score([3,4,5,3,3]) => 350 points
# score([1,5,1,2,4]) => 250 points
#
# More scoring examples are given in the tests below:
#
# Your goal is to write the score method.

def score(dice):
    # You need to write this method
    pass

class AboutScoringProject(Koan):
    def test_score_of_an_empty_list_is_zero(self):
        self.assertEqual(0, score([]))

    def test_score_of_a_single_roll_of_5_is_50(self):
        self.assertEqual(50, score([5]))

    def test_score_of_a_single_roll_of_1_is_100(self):
        self.assertEqual(100, score([1]))

    def test_score_of_multiple_1s_and_5s_is_the_sum_of_individual_scores(self):
        self.assertEqual(300, score([1,5,5,1]))

    def test_score_of_single_2s_3s_4s_and_6s_are_zero(self):
        self.assertEqual(0, score([2,3,4,6]))

    def test_score_of_a_triple_1_is_1000(self):
        self.assertEqual(1000, score([1,1,1]))

    def test_score_of_other_triples_is_100x(self):
        self.assertEqual(200, score([2,2,2]))
        self.assertEqual(300, score([3,3,3]))
        self.assertEqual(400, score([4,4,4]))
        self.assertEqual(500, score([5,5,5]))
        self.assertEqual(600, score([6,6,6]))

    def test_score_of_mixed_is_sum(self):
        self.assertEqual(250, score([2,5,2,2,3]))
        self.assertEqual(550, score([5,5,5,5]))
        self.assertEqual(1150, score([1,1,1,5,1]))

    def test_ones_not_left_out(self):
        self.assertEqual(300, score([1,2,2,2]))
        self.assertEqual(350, score([1,5,2,2,2]))
########NEW FILE########
__FILENAME__ = about_sets
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutSets(Koan):
    def test_sets_make_keep_lists_unique(self):
        highlanders = ['MacLeod', 'Ramirez', 'MacLeod', 'Matunas', 'MacLeod', 'Malcolm', 'MacLeod']

        there_can_only_be_only_one = set(highlanders)

        self.assertEqual(__, there_can_only_be_only_one)

    def test_empty_sets_have_different_syntax_to_populated_sets(self):
        self.assertEqual(__, {1, 2, 3})
        self.assertEqual(__, set())

    def test_dictionaries_and_sets_use_same_curly_braces(self):
        # Note: Sets have only started using braces since Python 3

        self.assertEqual(__, {1, 2, 3}.__class__)
        self.assertEqual(__, {'one': 1, 'two': 2}.__class__)

        self.assertEqual(__, {}.__class__)

    def test_creating_sets_using_strings(self):
        self.assertEqual(__, {'12345'})
        self.assertEqual(__, set('12345'))

    def test_convert_the_set_into_a_list_to_sort_it(self):
        self.assertEqual(__, sorted(set('12345')))

    # ------------------------------------------------------------------

    def test_set_have_arithmetic_operators(self):
        scotsmen = {'MacLeod', 'Wallace', 'Willie'}
        warriors = {'MacLeod', 'Wallace', 'Leonidas'}

        self.assertEqual(__, scotsmen - warriors)
        self.assertEqual(__, scotsmen | warriors)
        self.assertEqual(__, scotsmen & warriors)
        self.assertEqual(__, scotsmen ^ warriors)

    # ------------------------------------------------------------------

    def test_we_can_query_set_membership(self):
        self.assertEqual(__, 127 in {127, 0, 0, 1} )
        self.assertEqual(__, 'cow' not in set('apocalypse now') )

    def test_we_can_compare_subsets(self):
        self.assertEqual(__, set('cake') <= set('cherry cake'))
        self.assertEqual(__, set('cake').issubset(set('cherry cake')) )

        self.assertEqual(__, set('cake') > set('pie'))

########NEW FILE########
__FILENAME__ = about_strings
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutStrings(Koan):

    def test_double_quoted_strings_are_strings(self):
        string = "Hello, world."
        self.assertEqual(__, isinstance(string, str))

    def test_single_quoted_strings_are_also_strings(self):
        string = 'Goodbye, world.'
        self.assertEqual(__, isinstance(string, str))

    def test_triple_quote_strings_are_also_strings(self):
        string = """Howdy, world!"""
        self.assertEqual(__, isinstance(string, str))

    def test_triple_single_quotes_work_too(self):
        string = '''Bonjour tout le monde!'''
        self.assertEqual(__, isinstance(string, str))

    def test_raw_strings_are_also_strings(self):
        string = r"Konnichi wa, world!"
        self.assertEqual(__, isinstance(string, str))

    def test_use_single_quotes_to_create_string_with_double_quotes(self):
        string = 'He said, "Go Away."'
        self.assertEqual(__, string)

    def test_use_double_quotes_to_create_strings_with_single_quotes(self):
        string = "Don't"
        self.assertEqual(__, string)

    def test_use_backslash_for_escaping_quotes_in_strings(self):
        a = "He said, \"Don't\""
        b = 'He said, "Don\'t"'
        self.assertEqual(__, (a == b))

    def test_use_backslash_at_the_end_of_a_line_to_continue_onto_the_next_line(self):
        string = "It was the best of times,\n\
It was the worst of times."
        self.assertEqual(__, len(string))

    def test_triple_quoted_strings_can_span_lines(self):
        string = """
Howdy,
world!
"""
        self.assertEqual(__, len(string))

    def test_triple_quoted_strings_need_less_escaping(self):
        a = "Hello \"world\"."
        b = """Hello "world"."""
        self.assertEqual(__, (a == b))

    def test_escaping_quotes_at_the_end_of_triple_quoted_string(self):
        string = """Hello "world\""""
        self.assertEqual(__, string)

    def test_plus_concatenates_strings(self):
        string = "Hello, " + "world"
        self.assertEqual(__, string)

    def test_adjacent_strings_are_concatenated_automatically(self):
        string = "Hello" ", " "world"
        self.assertEqual(__, string)

    def test_plus_will_not_modify_original_strings(self):
        hi = "Hello, "
        there = "world"
        string = hi + there
        self.assertEqual(__, hi)
        self.assertEqual(__, there)

    def test_plus_equals_will_append_to_end_of_string(self):
        hi = "Hello, "
        there = "world"
        hi += there
        self.assertEqual(__, hi)

    def test_plus_equals_also_leaves_original_string_unmodified(self):
        original = "Hello, "
        hi = original
        there = "world"
        hi += there
        self.assertEqual(__, original)

    def test_most_strings_interpret_escape_characters(self):
        string = "\n"
        self.assertEqual('\n', string)
        self.assertEqual("""\n""", string)
        self.assertEqual(__, len(string))

########NEW FILE########
__FILENAME__ = about_string_manipulation
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutStringManipulation(Koan):

    def test_use_format_to_interpolate_variables(self):
        value1 = 'one'
        value2 = 2
        string = "The values are {0} and {1}".format(value1, value2)
        self.assertEqual(__, string)

    def test_formatted_values_can_be_shown_in_any_order_or_be_repeated(self):
        value1 = 'doh'
        value2 = 'DOH'
        string = "The values are {1}, {0}, {0} and {1}!".format(value1, value2)
        self.assertEqual(__, string)

    def test_any_python_expression_may_be_interpolated(self):
        import math # import a standard python module with math functions

        decimal_places = 4
        string = "The square root of 5 is {0:.{1}f}".format(math.sqrt(5),
            decimal_places)
        self.assertEqual(__, string)

    def test_you_can_get_a_substring_from_a_string(self):
        string = "Bacon, lettuce and tomato"
        self.assertEqual(__, string[7:10])

    def test_you_can_get_a_single_character_from_a_string(self):
        string = "Bacon, lettuce and tomato"
        self.assertEqual(__, string[1])

    def test_single_characters_can_be_represented_by_integers(self):
        self.assertEqual(__, ord('a'))
        self.assertEqual(__, ord('b') == (ord('a') + 1))

    def test_strings_can_be_split(self):
        string = "Sausage Egg Cheese"
        words = string.split()
        self.assertListEqual([__, __, __], words)

    def test_strings_can_be_split_with_different_patterns(self):
        import re #import python regular expression library

        string = "the,rain;in,spain"
        pattern = re.compile(',|;')

        words = pattern.split(string)

        self.assertListEqual([__, __, __, __], words)

        # Pattern is a Python regular expression pattern which matches ',' or ';'

    def test_raw_strings_do_not_interpret_escape_characters(self):
        string = r'\n'
        self.assertNotEqual('\n', string)
        self.assertEqual(__, string)
        self.assertEqual(__, len(string))

        # Useful in regular expressions, file paths, URLs, etc.

    def test_strings_can_be_joined(self):
        words = ["Now", "is", "the", "time"]
        self.assertEqual(__, ' '.join(words))

    def test_strings_can_change_case(self):
        self.assertEqual(__, 'guido'.capitalize())
        self.assertEqual(__, 'guido'.upper())
        self.assertEqual(__, 'TimBot'.lower())
        self.assertEqual(__, 'guido van rossum'.title())
        self.assertEqual(__, 'ToTaLlY aWeSoMe'.swapcase())

########NEW FILE########
__FILENAME__ = about_triangle_project
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

# You need to write the triangle method in the file 'triangle.py'
from .triangle import *

class AboutTriangleProject(Koan):
    def test_equilateral_triangles_have_equal_sides(self):
        self.assertEqual('equilateral', triangle(2, 2, 2))
        self.assertEqual('equilateral', triangle(10, 10, 10))

    def test_isosceles_triangles_have_exactly_two_sides_equal(self):
        self.assertEqual('isosceles', triangle(3, 4, 4))
        self.assertEqual('isosceles', triangle(4, 3, 4))
        self.assertEqual('isosceles', triangle(4, 4, 3))
        self.assertEqual('isosceles', triangle(10, 10, 2))

    def test_scalene_triangles_have_no_equal_sides(self):
        self.assertEqual('scalene', triangle(3, 4, 5))
        self.assertEqual('scalene', triangle(10, 11, 12))
        self.assertEqual('scalene', triangle(5, 4, 2))

########NEW FILE########
__FILENAME__ = about_triangle_project2
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

# You need to finish implementing triangle() in the file 'triangle.py'
from .triangle import *

class AboutTriangleProject2(Koan):
    # The first assignment did not talk about how to handle errors.
    # Let's handle that part now.
    def test_illegal_triangles_throw_exceptions(self):
        with self.assertRaises(TriangleError):
            triangle(0, 0, 0)

        with self.assertRaises(TriangleError):
            triangle(3, 4, -5)

        with self.assertRaises(TriangleError):
            triangle(1, 1, 3)

        with self.assertRaises(TriangleError):
            triangle(2, 5, 2)



########NEW FILE########
__FILENAME__ = about_true_and_false
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutTrueAndFalse(Koan):
    def truth_value(self, condition):
        if condition:
            return 'true stuff'
        else:
            return 'false stuff'

    def test_true_is_treated_as_true(self):
        self.assertEqual(__, self.truth_value(True))

    def test_false_is_treated_as_false(self):
        self.assertEqual(__, self.truth_value(False))

    def test_none_is_treated_as_false(self):
        self.assertEqual(__, self.truth_value(None))

    def test_zero_is_treated_as_false(self):
        self.assertEqual(__, self.truth_value(0))

    def test_empty_collections_are_treated_as_false(self):
        self.assertEqual(__, self.truth_value([]))
        self.assertEqual(__, self.truth_value(()))
        self.assertEqual(__, self.truth_value({}))
        self.assertEqual(__, self.truth_value(set()))

    def test_blank_strings_are_treated_as_false(self):
        self.assertEqual(__, self.truth_value(""))

    def test_everything_else_is_treated_as_true(self):
        self.assertEqual(__, self.truth_value(1))
        self.assertEqual(__, self.truth_value(1,))
        self.assertEqual(__, self.truth_value("Python is named after Monty Python"))
        self.assertEqual(__, self.truth_value(' '))
        self.assertEqual(__, self.truth_value('0'))

########NEW FILE########
__FILENAME__ = about_tuples
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from runner.koan import *

class AboutTuples(Koan):
    def test_creating_a_tuple(self):
        count_of_three =  (1, 2, 5)
        self.assertEqual(__, count_of_three[2])

    def test_tuples_are_immutable_so_item_assignment_is_not_possible(self):
        count_of_three =  (1, 2, 5)
        try:
            count_of_three[2] = "three"
        except TypeError as ex:
            msg = ex.args[0]

        # Note, assertRegexpMatches() uses regular expression pattern matching,
        # so you don't have to copy the whole message.

        self.assertRegexpMatches(msg, __)

    def test_tuples_are_immutable_so_appending_is_not_possible(self):
        count_of_three =  (1, 2, 5)
        with self.assertRaises(___): count_of_three.append("boom")

        # Tuples are less flexible than lists, but faster.

    def test_tuples_can_only_be_changed_through_replacement(self):
        count_of_three = (1, 2, 5)

        list_count = list(count_of_three)
        list_count.append("boom")
        count_of_three = tuple(list_count)

        self.assertEqual(__, count_of_three)

    def test_tuples_of_one_look_peculiar(self):
        self.assertEqual(__, (1).__class__)
        self.assertEqual(__, (1,).__class__)
        self.assertEqual(__, ("Hello comma!", ))

    def test_tuple_constructor_can_be_surprising(self):
        self.assertEqual(__, tuple("Surprise!"))

    def test_creating_empty_tuples(self):
        self.assertEqual(__ , ())
        self.assertEqual(__ , tuple()) #Sometimes less confusing

    def test_tuples_can_be_embedded(self):
        lat = (37, 14, 6, 'N')
        lon = (115, 48, 40, 'W')
        place = ('Area 51', lat, lon)
        self.assertEqual(__, place)

    def test_tuples_are_good_for_representing_records(self):
        locations = [
            ("Illuminati HQ", (38, 52, 15.56, 'N'), (77, 3, 21.46, 'W')),
            ("Stargate B", (41, 10, 43.92, 'N'), (1, 49, 34.29, 'W')),
        ]

        locations.append( ("Cthulu", (26, 40, 1, 'N'), (70, 45, 7, 'W')) )

        self.assertEqual(__, locations[2][0])
        self.assertEqual(__, locations[0][1][2])




########NEW FILE########
__FILENAME__ = about_with_statements
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Based on AboutSandwichCode in the Ruby Koans
#

from runner.koan import *

import re # For regular expression string comparisons

class AboutWithStatements(Koan):
    def count_lines(self, file_name):
        try:
            file = open(file_name)
            try:
                return len(file.readlines())
            finally:
                file.close()
        except IOError:
            # should never happen
            self.fail()

    def test_counting_lines(self):
        self.assertEqual(__, self.count_lines("example_file.txt"))

    # ------------------------------------------------------------------

    def find_line(self, file_name):
        try:
            file = open(file_name)
            try:
                for line in file.readlines():
                    match = re.search('e', line)
                    if match:
                        return line
            finally:
                file.close()
        except IOError:
            # should never happen
            self.fail()

    def test_finding_lines(self):
        self.assertEqual(__, self.find_line("example_file.txt"))

    ## ------------------------------------------------------------------
    ## THINK ABOUT IT:
    ##
    ## The count_lines and find_line are similar, and yet different.
    ## They both follow the pattern of "sandwich code".
    ##
    ## Sandwich code is code that comes in three parts: (1) the top slice
    ## of bread, (2) the meat, and (3) the bottom slice of bread.
    ## The bread part of the sandwich almost always goes together, but
    ## the meat part changes all the time.
    ##
    ## Because the changing part of the sandwich code is in the middle,
    ## abstracting the top and bottom bread slices to a library can be
    ## difficult in many languages.
    ##
    ## (Aside for C++ programmers: The idiom of capturing allocated
    ## pointers in a smart pointer constructor is an attempt to deal with
    ## the problem of sandwich code for resource allocation.)
    ##
    ## Python solves the problem using Context Managers. Consider the
    ## following code:
    ##

    class FileContextManager():
        def __init__(self, file_name):
            self._file_name = file_name
            self._file = None

        def __enter__(self):
            self._file = open(self._file_name)
            return self._file

        def __exit__(self, cls, value, tb):
            self._file.close()

    # Now we write:

    def count_lines2(self, file_name):
        with self.FileContextManager(file_name) as file:
            return len(file.readlines())

    def test_counting_lines2(self):
        self.assertEqual(__, self.count_lines2("example_file.txt"))

    # ------------------------------------------------------------------

    def find_line2(self, file_name):
        # Rewrite find_line using the Context Manager.
        pass

    def test_finding_lines2(self):
        self.assertEqual(__, self.find_line2("example_file.txt"))
        self.assertNotEqual(__, self.find_line2("example_file.txt"))

    # ------------------------------------------------------------------

    def count_lines3(self, file_name):
        with open(file_name) as file:
            return len(file.readlines())

    def test_open_already_has_its_own_built_in_context_manager(self):
        self.assertEqual(__, self.count_lines3("example_file.txt"))

########NEW FILE########
__FILENAME__ = another_local_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Goose:
    @property
    def name(self):
        return "Mr Stabby"

class Hamster:
    @property
    def name(self):
        return "Phil"

class _SecretSquirrel:
    @property
    def name(self):
        return "Mr Anonymous"
########NEW FILE########
__FILENAME__ = a_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Duck:
    @property
    def name(self):
        return "Donald"
########NEW FILE########
__FILENAME__ = jims
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Dog:
    def identify(self):
        return "jims dog"

########NEW FILE########
__FILENAME__ = joes
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Dog:
    def identify(self):
        return "joes dog"

########NEW FILE########
__FILENAME__ = local_module
#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Duck:
    def __init__(self):
        self._password = 'password' # Genius!

    @property
    def name(self):
        return "Daffy"

########NEW FILE########
__FILENAME__ = local_module_with_all_defined
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = (
    'Goat',
    '_Velociraptor'
)

class Goat:
    @property
    def name(self):
        return "George"

class _Velociraptor:
    @property
    def name(self):
        return "Cuddles"

class SecretDuck:
    @property
    def name(self):
        return "None of your business"

########NEW FILE########
__FILENAME__ = triangle
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Triangle Project Code.

# Triangle analyzes the lengths of the sides of a triangle
# (represented by a, b and c) and returns the type of triangle.
#
# It returns:
#   'equilateral'  if all sides are equal
#   'isosceles'    if exactly 2 sides are equal
#   'scalene'      if no sides are equal
#
# The tests for this method can be found in
#   about_triangle_project.py
# and
#   about_triangle_project_2.py
#
def triangle(a, b, c):
    # DELETE 'PASS' AND WRITE THIS CODE
    pass

# Error class used in part 2.  No need to change this code.
class TriangleError(Exception):
    pass

########NEW FILE########
__FILENAME__ = ansi
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
'''
This module generates ANSI character codes to printing colors to terminals.
See: http://en.wikipedia.org/wiki/ANSI_escape_code
'''

CSI = '\033['

def code_to_chars(code):
    return CSI + str(code) + 'm'

class AnsiCodes(object):
    def __init__(self, codes):
        for name in dir(codes):
            if not name.startswith('_'):
                value = getattr(codes, name)
                setattr(self, name, code_to_chars(value))

class AnsiFore:
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37
    RESET   = 39

class AnsiBack:
    BLACK   = 40
    RED     = 41
    GREEN   = 42
    YELLOW  = 43
    BLUE    = 44
    MAGENTA = 45
    CYAN    = 46
    WHITE   = 47
    RESET   = 49

class AnsiStyle:
    BRIGHT    = 1
    DIM       = 2
    NORMAL    = 22
    RESET_ALL = 0

Fore = AnsiCodes( AnsiFore )
Back = AnsiCodes( AnsiBack )
Style = AnsiCodes( AnsiStyle )


########NEW FILE########
__FILENAME__ = ansitowin32
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
import re
import sys

from .ansi import AnsiFore, AnsiBack, AnsiStyle, Style
from .winterm import WinTerm, WinColor, WinStyle
from .win32 import windll


if windll is not None:
    winterm = WinTerm()


def is_a_tty(stream):
    return hasattr(stream, 'isatty') and stream.isatty()


class StreamWrapper(object):
    '''
    Wraps a stream (such as stdout), acting as a transparent proxy for all
    attribute access apart from method 'write()', which is delegated to our
    Converter instance.
    '''
    def __init__(self, wrapped, converter):
        # double-underscore everything to prevent clashes with names of
        # attributes on the wrapped stream object.
        self.__wrapped = wrapped
        self.__convertor = converter

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def write(self, text):
        self.__convertor.write(text)


class AnsiToWin32(object):
    '''
    Implements a 'write()' method which, on Windows, will strip ANSI character
    sequences from the text, and if outputting to a tty, will convert them into
    win32 function calls.
    '''
    ANSI_RE = re.compile('\033\[((?:\d|;)*)([a-zA-Z])')

    def __init__(self, wrapped, convert=None, strip=None, autoreset=False):
        # The wrapped stream (normally sys.stdout or sys.stderr)
        self.wrapped = wrapped

        # should we reset colors to defaults after every .write()
        self.autoreset = autoreset

        # create the proxy wrapping our output stream
        self.stream = StreamWrapper(wrapped, self)

        on_windows = sys.platform.startswith('win')

        # should we strip ANSI sequences from our output?
        if strip is None:
            strip = on_windows
        self.strip = strip

        # should we should convert ANSI sequences into win32 calls?
        if convert is None:
            convert = on_windows and is_a_tty(wrapped)
        self.convert = convert

        # dict of ansi codes to win32 functions and parameters
        self.win32_calls = self.get_win32_calls()

        # are we wrapping stderr?
        self.on_stderr = self.wrapped is sys.stderr


    def should_wrap(self):
        '''
        True if this class is actually needed. If false, then the output
        stream will not be affected, nor will win32 calls be issued, so
        wrapping stdout is not actually required. This will generally be
        False on non-Windows platforms, unless optional functionality like
        autoreset has been requested using kwargs to init()
        '''
        return self.convert or self.strip or self.autoreset


    def get_win32_calls(self):
        if self.convert and winterm:
            return {
                AnsiStyle.RESET_ALL: (winterm.reset_all, ),
                AnsiStyle.BRIGHT: (winterm.style, WinStyle.BRIGHT),
                AnsiStyle.DIM: (winterm.style, WinStyle.NORMAL),
                AnsiStyle.NORMAL: (winterm.style, WinStyle.NORMAL),
                AnsiFore.BLACK: (winterm.fore, WinColor.BLACK),
                AnsiFore.RED: (winterm.fore, WinColor.RED),
                AnsiFore.GREEN: (winterm.fore, WinColor.GREEN),
                AnsiFore.YELLOW: (winterm.fore, WinColor.YELLOW),
                AnsiFore.BLUE: (winterm.fore, WinColor.BLUE),
                AnsiFore.MAGENTA: (winterm.fore, WinColor.MAGENTA),
                AnsiFore.CYAN: (winterm.fore, WinColor.CYAN),
                AnsiFore.WHITE: (winterm.fore, WinColor.GREY),
                AnsiFore.RESET: (winterm.fore, ),
                AnsiBack.BLACK: (winterm.back, WinColor.BLACK),
                AnsiBack.RED: (winterm.back, WinColor.RED),
                AnsiBack.GREEN: (winterm.back, WinColor.GREEN),
                AnsiBack.YELLOW: (winterm.back, WinColor.YELLOW),
                AnsiBack.BLUE: (winterm.back, WinColor.BLUE),
                AnsiBack.MAGENTA: (winterm.back, WinColor.MAGENTA),
                AnsiBack.CYAN: (winterm.back, WinColor.CYAN),
                AnsiBack.WHITE: (winterm.back, WinColor.GREY),
                AnsiBack.RESET: (winterm.back, ),
            }


    def write(self, text):
        if self.strip or self.convert:
            self.write_and_convert(text)
        else:
            self.wrapped.write(text)
            self.wrapped.flush()
        if self.autoreset:
            self.reset_all()


    def reset_all(self):
        if self.convert:
            self.call_win32('m', (0,))
        elif is_a_tty(self.wrapped):
            self.wrapped.write(Style.RESET_ALL)


    def write_and_convert(self, text):
        '''
        Write the given text to our wrapped stream, stripping any ANSI
        sequences from the text, and optionally converting them into win32
        calls.
        '''
        cursor = 0
        for match in self.ANSI_RE.finditer(text):
            start, end = match.span()
            self.write_plain_text(text, cursor, start)
            self.convert_ansi(*match.groups())
            cursor = end
        self.write_plain_text(text, cursor, len(text))


    def write_plain_text(self, text, start, end):
        if start < end:
            self.wrapped.write(text[start:end])
            self.wrapped.flush()


    def convert_ansi(self, paramstring, command):
        if self.convert:
            params = self.extract_params(paramstring)
            self.call_win32(command, params)


    def extract_params(self, paramstring):
        def split(paramstring):
            for p in paramstring.split(';'):
                if p != '':
                    yield int(p)
        return tuple(split(paramstring))


    def call_win32(self, command, params):
        if params == []:
            params = [0]
        if command == 'm':
            for param in params:
                if param in self.win32_calls:
                    func_args = self.win32_calls[param]
                    func = func_args[0]
                    args = func_args[1:]
                    kwargs = dict(on_stderr=self.on_stderr)
                    func(*args, **kwargs)
        elif command in ('H', 'f'): # set cursor position
            func = winterm.set_cursor_position
            func(params, on_stderr=self.on_stderr)
        elif command in ('J'):
            func = winterm.erase_data
            func(params, on_stderr=self.on_stderr)
        elif command == 'A':
            if params == () or params == None:
                num_rows = 1
            else:
                num_rows = params[0]
            func = winterm.cursor_up
            func(num_rows, on_stderr=self.on_stderr)


########NEW FILE########
__FILENAME__ = initialise
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
import atexit
import sys

from .ansitowin32 import AnsiToWin32


orig_stdout = sys.stdout
orig_stderr = sys.stderr

wrapped_stdout = sys.stdout
wrapped_stderr = sys.stderr

atexit_done = False


def reset_all():
    AnsiToWin32(orig_stdout).reset_all()


def init(autoreset=False, convert=None, strip=None, wrap=True):

    if not wrap and any([autoreset, convert, strip]):
        raise ValueError('wrap=False conflicts with any other arg=True')

    global wrapped_stdout, wrapped_stderr
    sys.stdout = wrapped_stdout = \
        wrap_stream(orig_stdout, convert, strip, autoreset, wrap)
    sys.stderr = wrapped_stderr = \
        wrap_stream(orig_stderr, convert, strip, autoreset, wrap)

    global atexit_done
    if not atexit_done:
        atexit.register(reset_all)
        atexit_done = True


def deinit():
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr


def reinit():
    sys.stdout = wrapped_stdout
    sys.stderr = wrapped_stdout


def wrap_stream(stream, convert, strip, autoreset, wrap):
    if wrap:
        wrapper = AnsiToWin32(stream,
            convert=convert, strip=strip, autoreset=autoreset)
        if wrapper.should_wrap():
            stream = wrapper.stream
    return stream



########NEW FILE########
__FILENAME__ = win32
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.

# from winbase.h
STDOUT = -11
STDERR = -12

try:
    from ctypes import windll
    from ctypes import wintypes
except ImportError:
    windll = None
    SetConsoleTextAttribute = lambda *_: None
else:
    from ctypes import (
        byref, Structure, c_char, c_short, c_uint32, c_ushort, POINTER
    )

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", wintypes._COORD),
            ("dwCursorPosition", wintypes._COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", wintypes.SMALL_RECT),
            ("dwMaximumWindowSize", wintypes._COORD),
        ]
        def __str__(self):
            return '(%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d)' % (
                self.dwSize.Y, self.dwSize.X
                , self.dwCursorPosition.Y, self.dwCursorPosition.X
                , self.wAttributes
                , self.srWindow.Top, self.srWindow.Left, self.srWindow.Bottom, self.srWindow.Right
                , self.dwMaximumWindowSize.Y, self.dwMaximumWindowSize.X
            )

    _GetStdHandle = windll.kernel32.GetStdHandle
    _GetStdHandle.argtypes = [
        wintypes.DWORD,
    ]
    _GetStdHandle.restype = wintypes.HANDLE

    _GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    _GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    _GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    _SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    _SetConsoleTextAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
    ]
    _SetConsoleTextAttribute.restype = wintypes.BOOL

    _SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
    _SetConsoleCursorPosition.argtypes = [
        wintypes.HANDLE,
        wintypes._COORD,
    ]
    _SetConsoleCursorPosition.restype = wintypes.BOOL

    _FillConsoleOutputCharacterA = windll.kernel32.FillConsoleOutputCharacterA
    _FillConsoleOutputCharacterA.argtypes = [
        wintypes.HANDLE,
        c_char,
        wintypes.DWORD,
        wintypes._COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputCharacterA.restype = wintypes.BOOL

    _FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
    _FillConsoleOutputAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
        wintypes.DWORD,
        wintypes._COORD,
        POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputAttribute.restype = wintypes.BOOL

    handles = {
        STDOUT: _GetStdHandle(STDOUT),
        STDERR: _GetStdHandle(STDERR),
    }

    def GetConsoleScreenBufferInfo(stream_id=STDOUT):
        handle = handles[stream_id]
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        success = _GetConsoleScreenBufferInfo(
            handle, byref(csbi))
        return csbi

    def SetConsoleTextAttribute(stream_id, attrs):
        handle = handles[stream_id]
        return _SetConsoleTextAttribute(handle, attrs)

    def SetConsoleCursorPosition(stream_id, position):
        position = wintypes._COORD(*position)
        # If the position is out of range, do nothing.
        if position.Y <= 0 or position.X <= 0:
            return
        # Adjust for Windows' SetConsoleCursorPosition:
        #    1. being 0-based, while ANSI is 1-based.
        #    2. expecting (x,y), while ANSI uses (y,x).
        adjusted_position = wintypes._COORD(position.Y - 1, position.X - 1)
        # Adjust for viewport's scroll position
        sr = GetConsoleScreenBufferInfo(STDOUT).srWindow
        adjusted_position.Y += sr.Top
        adjusted_position.X += sr.Left
        # Resume normal processing
        handle = handles[stream_id]
        return _SetConsoleCursorPosition(handle, adjusted_position)

    def FillConsoleOutputCharacter(stream_id, char, length, start):
        handle = handles[stream_id]
        char = c_char(char)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        success = _FillConsoleOutputCharacterA(
            handle, char, length, start, byref(num_written))
        return num_written.value

    def FillConsoleOutputAttribute(stream_id, attr, length, start):
        ''' FillConsoleOutputAttribute( hConsole, csbi.wAttributes, dwConSize, coordScreen, &cCharsWritten )'''
        handle = handles[stream_id]
        attribute = wintypes.WORD(attr)
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        # Note that this is hard-coded for ANSI (vs wide) bytes.
        return _FillConsoleOutputAttribute(
            handle, attribute, length, start, byref(num_written))

########NEW FILE########
__FILENAME__ = winterm
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
from . import win32


# from wincon.h
class WinColor(object):
    BLACK   = 0
    BLUE    = 1
    GREEN   = 2
    CYAN    = 3
    RED     = 4
    MAGENTA = 5
    YELLOW  = 6
    GREY    = 7

# from wincon.h
class WinStyle(object):
    NORMAL = 0x00 # dim text, dim background
    BRIGHT = 0x08 # bright text, dim background


class WinTerm(object):

    def __init__(self):
        self._default = win32.GetConsoleScreenBufferInfo(win32.STDOUT).wAttributes
        self.set_attrs(self._default)
        self._default_fore = self._fore
        self._default_back = self._back
        self._default_style = self._style

    def get_attrs(self):
        return self._fore + self._back * 16 + self._style

    def set_attrs(self, value):
        self._fore = value & 7
        self._back = (value >> 4) & 7
        self._style = value & WinStyle.BRIGHT

    def reset_all(self, on_stderr=None):
        self.set_attrs(self._default)
        self.set_console(attrs=self._default)

    def fore(self, fore=None, on_stderr=False):
        if fore is None:
            fore = self._default_fore
        self._fore = fore
        self.set_console(on_stderr=on_stderr)

    def back(self, back=None, on_stderr=False):
        if back is None:
            back = self._default_back
        self._back = back
        self.set_console(on_stderr=on_stderr)

    def style(self, style=None, on_stderr=False):
        if style is None:
            style = self._default_style
        self._style = style
        self.set_console(on_stderr=on_stderr)

    def set_console(self, attrs=None, on_stderr=False):
        if attrs is None:
            attrs = self.get_attrs()
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleTextAttribute(handle, attrs)

    def get_position(self, handle):
        position = win32.GetConsoleScreenBufferInfo(handle).dwCursorPosition
        # Because Windows coordinates are 0-based,
        # and win32.SetConsoleCursorPosition expects 1-based.
        position.X += 1
        position.Y += 1
        return position
    
    def set_cursor_position(self, position=None, on_stderr=False):
        if position is None:
            #I'm not currently tracking the position, so there is no default.
            #position = self.get_position()
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        win32.SetConsoleCursorPosition(handle, position)

    def cursor_up(self, num_rows=0, on_stderr=False):
        if num_rows == 0:
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        position = self.get_position(handle)
        adjusted_position = (position.Y - num_rows, position.X)
        self.set_cursor_position(adjusted_position, on_stderr)

    def erase_data(self, mode=0, on_stderr=False):
        # 0 (or None) should clear from the cursor to the end of the screen.
        # 1 should clear from the cursor to the beginning of the screen.
        # 2 should clear the entire screen. (And maybe move cursor to (1,1)?)
        #
        # At the moment, I only support mode 2. From looking at the API, it
        #    should be possible to calculate a different number of bytes to clear,
        #    and to do so relative to the cursor position.
        if mode[0] not in (2,):
            return
        handle = win32.STDOUT
        if on_stderr:
            handle = win32.STDERR
        # here's where we'll home the cursor
        coord_screen = win32.COORD(0,0)
        csbi = win32.GetConsoleScreenBufferInfo(handle)
        # get the number of character cells in the current buffer
        dw_con_size = csbi.dwSize.X * csbi.dwSize.Y
        # fill the entire screen with blanks
        win32.FillConsoleOutputCharacter(handle, ' ', dw_con_size, coord_screen)
        # now set the buffer's attributes accordingly
        win32.FillConsoleOutputAttribute(handle, self.get_attrs(), dw_con_size, coord_screen );
        # put the cursor at (0, 0)
        win32.SetConsoleCursorPosition(handle, (coord_screen.X, coord_screen.Y))

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2009 Michael Foord
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.6.0
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'patch',
    'patch_object',
    'sentinel',
    'DEFAULT'
)

__version__ = '0.6.0 modified by Greg Malcolm'

class SentinelObject(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SentinelObject "{0!s}">'.format(self.name)


class Sentinel(object):
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        return self._sentinels.setdefault(name, SentinelObject(name))


sentinel = Sentinel()

DEFAULT = sentinel.DEFAULT

class OldStyleClass:
    pass
ClassType = type(OldStyleClass)

def _is_magic(name):
    return '__{0!s}__'.format(name[2:-2]) == name

def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


class Mock(object):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                 name=None, parent=None, wraps=None):
        self._parent = parent
        self._name = name
        if spec is not None and not isinstance(spec, list):
            spec = [member for member in dir(spec) if not _is_magic(member)]

        self._methods = spec
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        self._wraps = wraps

        self.reset_mock()


    def reset_mock(self):
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.values():
            child.reset_mock()
        if isinstance(self._return_value, Mock):
            self._return_value.reset_mock()


    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = Mock()
        return self._return_value

    def __set_return_value(self, value):
        self._return_value = value

    return_value = property(__get_return_value, __set_return_value)


    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = (args, kwargs)
        self.call_args_list.append((args, kwargs))

        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append((name, args, kwargs))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        ret_val = DEFAULT
        if self.side_effect is not None:
            if (isinstance(self.side_effect, Exception) or
                isinstance(self.side_effect, (type, ClassType)) and
                issubclass(self.side_effect, Exception)):
                raise self.side_effect

            ret_val = self.side_effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if self._wraps is not None and self._return_value is DEFAULT:
            return self._wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val


    def __getattr__(self, name):
        if self._methods is not None:
            if name not in self._methods:
                raise AttributeError("Mock object has no attribute '{0!s}'".format(name))
        elif _is_magic(name):
            raise AttributeError(name)

        if name not in self._children:
            wraps = None
            if self._wraps is not None:
                wraps = getattr(self._wraps, name)
            self._children[name] = Mock(parent=self, name=name, wraps=wraps)

        return self._children[name]


    def assert_called_with(self, *args, **kwargs):
        assert self.call_args == (args, kwargs), 'Expected: {0!s}\nCalled with: {1!s}'.format((args, kwargs), self.call_args)


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".{0!s}".format(comp)
        thing = _dot_lookup(thing, comp, import_path)
    return thing


class _patch(object):
    def __init__(self, target, attribute, new, spec, create):
        self.target = target
        self.attribute = attribute
        self.new = new
        self.spec = spec
        self.create = create
        self.has_local = False


    def __call__(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with 2.5)
            extra_args = []
            for patching in patched.patchings:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.append(arg)
            args += tuple(extra_args)
            try:
                return func(*args, **keywargs)
            finally:
                for patching in getattr(patched, 'patchings', []):
                    patching.__exit__()

        patched.patchings = [self]
        patched.__name__ = func.__name__
        patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno",
                                                func.func_code.co_firstlineno)
        return patched


    def get_original(self):
        target = self.target
        name = self.attribute
        create = self.create

        original = DEFAULT
        if _has_local_attr(target, name):
            try:
                original = target.__dict__[name]
            except AttributeError:
                # for instances of classes with slots, they have no __dict__
                original = getattr(target, name)
        elif not create and not hasattr(target, name):
            raise AttributeError("{0!s} does not have the attribute {1!r}".format(target, name))
        return original


    def __enter__(self):
        new, spec, = self.new, self.spec
        original = self.get_original()
        if new is DEFAULT:
            # XXXX what if original is DEFAULT - shouldn't use it as a spec
            inherit = False
            if spec == True:
                # set spec to the object we are replacing
                spec = original
                if isinstance(spec, (type, ClassType)):
                    inherit = True
            new = Mock(spec=spec)
            if inherit:
                new.return_value = Mock(spec=spec)
        self.temp_original = original
        setattr(self.target, self.attribute, new)
        return new


    def __exit__(self, *_):
        if self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
        del self.temp_original


def patch_object(target, attribute, new=DEFAULT, spec=None, create=False):
    return _patch(target, attribute, new, spec, create)


def patch(target, new=DEFAULT, spec=None, create=False):
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: {0!r}".format(target,))
    target = _importer(target)
    return _patch(target, attribute, new, spec, create)



def _has_local_attr(obj, name):
    try:
        return name in vars(obj)
    except TypeError:
        # objects without a __dict__
        return hasattr(obj, name)

########NEW FILE########
__FILENAME__ = helper
#!/usr/bin/env python
# -*- coding: utf-8 -*-

def cls_name(obj):
    return obj.__class__.__name__
########NEW FILE########
__FILENAME__ = koan
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import re

# Starting a classname or attribute with an underscore normally implies Private scope.
# However, we are making an exception for __ and ___.

__all__ = [ "__", "___", "____", "_____", "Koan" ]

__ = "-=> FILL ME IN! <=-"

class ___(Exception):
    pass

____ = "-=> TRUE OR FALSE? <=-"

_____ = 0


class Koan(unittest.TestCase):
    def assertNoRegexpMatches(self, text, expected_regex, msg=None):
        """
        Throw an exception if the regular expresson pattern is not matched
        """
        if isinstance(expected_regex, (str, bytes)):
            expected_regex = re.compile(expected_regex)
        if expected_regex.search(text):
            msg = msg or "Regexp matched"
            msg = '{0}: {1!r} found in {2!r}'.format(msg, expected_regex.pattern, text)
            raise self.failureException(msg)

########NEW FILE########
__FILENAME__ = mockable_test_result
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

# Needed to stop unittest.TestResult itself getting Mocked out of existence,
# which is a problem when testing the helper classes! (It confuses the runner)

class MockableTestResult(unittest.TestResult):
    pass
########NEW FILE########
__FILENAME__ = mountain
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys

from . import path_to_enlightenment
from .sensei import Sensei
from .writeln_decorator import WritelnDecorator

class Mountain:
    def __init__(self):
        self.stream = WritelnDecorator(sys.stdout)
        self.tests = path_to_enlightenment.koans()
        self.lesson = Sensei(self.stream)

    def walk_the_path(self, args=None):
        "Run the koans tests with a custom runner output."

        if args and len(args) >=2:
            self.tests = unittest.TestLoader().loadTestsFromName("koans." + args[1])

        self.tests(self.lesson)
        self.lesson.learn()
        return self.lesson

########NEW FILE########
__FILENAME__ = path_to_enlightenment
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The path to enlightenment starts with the following:

import unittest

from koans.about_asserts import AboutAsserts
from koans.about_strings import AboutStrings
from koans.about_none import AboutNone
from koans.about_lists import AboutLists
from koans.about_list_assignments import AboutListAssignments
from koans.about_dictionaries import AboutDictionaries
from koans.about_string_manipulation import AboutStringManipulation
from koans.about_tuples import AboutTuples
from koans.about_methods import AboutMethods
from koans.about_control_statements import AboutControlStatements
from koans.about_true_and_false import AboutTrueAndFalse
from koans.about_sets import AboutSets
from koans.about_triangle_project import AboutTriangleProject
from koans.about_exceptions import AboutExceptions
from koans.about_triangle_project2 import AboutTriangleProject2
from koans.about_iteration import AboutIteration
from koans.about_comprehension import AboutComprehension
from koans.about_generators import AboutGenerators
from koans.about_lambdas import AboutLambdas
from koans.about_scoring_project import AboutScoringProject
from koans.about_classes import AboutClasses
from koans.about_with_statements import AboutWithStatements
from koans.about_monkey_patching import AboutMonkeyPatching
from koans.about_dice_project import AboutDiceProject
from koans.about_method_bindings import AboutMethodBindings
from koans.about_decorating_with_functions import AboutDecoratingWithFunctions
from koans.about_decorating_with_classes import AboutDecoratingWithClasses
from koans.about_inheritance import AboutInheritance
from koans.about_multiple_inheritance import AboutMultipleInheritance
from koans.about_regex import AboutRegex
from koans.about_scope import AboutScope
from koans.about_modules import AboutModules
from koans.about_packages import AboutPackages
from koans.about_class_attributes import AboutClassAttributes
from koans.about_attribute_access import AboutAttributeAccess
from koans.about_deleting_objects import AboutDeletingObjects
from koans.about_proxy_object_project import *
from koans.about_extra_credit import AboutExtraCredit

def koans():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    loader.sortTestMethodsUsing = None
    suite.addTests(loader.loadTestsFromTestCase(AboutAsserts))
    suite.addTests(loader.loadTestsFromTestCase(AboutStrings))
    suite.addTests(loader.loadTestsFromTestCase(AboutNone))
    suite.addTests(loader.loadTestsFromTestCase(AboutLists))
    suite.addTests(loader.loadTestsFromTestCase(AboutListAssignments))
    suite.addTests(loader.loadTestsFromTestCase(AboutDictionaries))
    suite.addTests(loader.loadTestsFromTestCase(AboutStringManipulation))
    suite.addTests(loader.loadTestsFromTestCase(AboutTuples))
    suite.addTests(loader.loadTestsFromTestCase(AboutMethods))
    suite.addTests(loader.loadTestsFromTestCase(AboutControlStatements))
    suite.addTests(loader.loadTestsFromTestCase(AboutTrueAndFalse))
    suite.addTests(loader.loadTestsFromTestCase(AboutSets))
    suite.addTests(loader.loadTestsFromTestCase(AboutTriangleProject))
    suite.addTests(loader.loadTestsFromTestCase(AboutExceptions))
    suite.addTests(loader.loadTestsFromTestCase(AboutTriangleProject2))
    suite.addTests(loader.loadTestsFromTestCase(AboutIteration))
    suite.addTests(loader.loadTestsFromTestCase(AboutComprehension))
    suite.addTests(loader.loadTestsFromTestCase(AboutGenerators))
    suite.addTests(loader.loadTestsFromTestCase(AboutLambdas))
    suite.addTests(loader.loadTestsFromTestCase(AboutScoringProject))
    suite.addTests(loader.loadTestsFromTestCase(AboutClasses))
    suite.addTests(loader.loadTestsFromTestCase(AboutWithStatements))
    suite.addTests(loader.loadTestsFromTestCase(AboutMonkeyPatching))
    suite.addTests(loader.loadTestsFromTestCase(AboutDiceProject))
    suite.addTests(loader.loadTestsFromTestCase(AboutMethodBindings))
    suite.addTests(loader.loadTestsFromTestCase(AboutDecoratingWithFunctions))
    suite.addTests(loader.loadTestsFromTestCase(AboutDecoratingWithClasses))
    suite.addTests(loader.loadTestsFromTestCase(AboutInheritance))
    suite.addTests(loader.loadTestsFromTestCase(AboutMultipleInheritance))
    suite.addTests(loader.loadTestsFromTestCase(AboutScope))
    suite.addTests(loader.loadTestsFromTestCase(AboutModules))
    suite.addTests(loader.loadTestsFromTestCase(AboutPackages))
    suite.addTests(loader.loadTestsFromTestCase(AboutClassAttributes))
    suite.addTests(loader.loadTestsFromTestCase(AboutAttributeAccess))
    suite.addTests(loader.loadTestsFromTestCase(AboutDeletingObjects))
    suite.addTests(loader.loadTestsFromTestCase(AboutProxyObjectProject))
    suite.addTests(loader.loadTestsFromTestCase(TelevisionTest))
    suite.addTests(loader.loadTestsFromTestCase(AboutExtraCredit))
    suite.addTests(loader.loadTestsFromTestCase(AboutRegex))

    return suite

########NEW FILE########
__FILENAME__ = test_helper
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from runner import helper

class TestHelper(unittest.TestCase):

    def test_that_get_class_name_works_with_a_string_instance(self):
        self.assertEqual("str", helper.cls_name(str()))

    def test_that_get_class_name_works_with_a_4(self):
        self.assertEquals("int", helper.cls_name(4))

    def test_that_get_class_name_works_with_a_tuple(self):
        self.assertEquals("tuple", helper.cls_name((3,"pie", [])))

########NEW FILE########
__FILENAME__ = test_mountain
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from libs.mock import *

from runner.mountain import Mountain
from runner import path_to_enlightenment

class TestMountain(unittest.TestCase):

    def setUp(self):
        path_to_enlightenment.koans = Mock()
        self.mountain = Mountain()
        self.mountain.stream.writeln = Mock()

    def test_it_gets_test_results(self):
        self.mountain.lesson.learn = Mock()
        self.mountain.walk_the_path()
        self.assertTrue(self.mountain.lesson.learn.called)


########NEW FILE########
__FILENAME__ = test_sensei
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import re

from libs.mock import *

from runner.sensei import Sensei
from runner.writeln_decorator import WritelnDecorator
from runner.mockable_test_result import MockableTestResult
from runner import path_to_enlightenment

class AboutParrots:
    pass
class AboutLumberjacks:
    pass
class AboutTennis:
    pass
class AboutTheKnightsWhoSayNi:
    pass
class AboutMrGumby:
    pass
class AboutMessiahs:
    pass
class AboutGiantFeet:
    pass
class AboutTrebuchets:
    pass
class AboutFreemasons:
    pass

error_assertion_with_message = """Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_exploding_trousers.py ", line 43, in test_durability
    self.assertEqual("Steel","Lard", "Another fine mess you've got me into Stanley...")
AssertionError: Another fine mess you've got me into Stanley..."""

error_assertion_equals = """

Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_exploding_trousers.py", line 49, in test_math
    self.assertEqual(4,99)
AssertionError: 4 != 99
"""

error_assertion_true = """Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_armories.py", line 25, in test_weoponary
    self.assertTrue("Pen" > "Sword")
AssertionError

"""

error_mess = """
Traceback (most recent call last):
  File "contemplate_koans.py", line 5, in <module>
    from runner.mountain import Mountain
  File "/Users/Greg/hg/python_koans/runner/mountain.py", line 7, in <module>
    import path_to_enlightenment
  File "/Users/Greg/hg/python_koans/runner/path_to_enlightenment.py", line 8, in <module>
    from koans import *
  File "/Users/Greg/hg/python_koans/koans/about_asserts.py", line 20
    self.assertTrue(eoe"Pen" > "Sword", "nhnth")
                           ^
SyntaxError: invalid syntax"""

error_with_list = """Traceback (most recent call last):
  File "/Users/Greg/hg/python_koans/koans/about_armories.py", line 84, in test_weoponary
    self.assertEqual([1, 9], [1, 2])
AssertionError: Lists differ: [1, 9] != [1, 2]

First differing element 1:
9
2

- [1, 9]
?     ^

+ [1, 2]
?     ^

"""


class TestSensei(unittest.TestCase):

    def setUp(self):
        self.sensei = Sensei(WritelnDecorator(sys.stdout))
        self.sensei.stream.writeln = Mock()
        path_to_enlightenment.koans = Mock()
        self.tests = Mock()
        self.tests.countTestCases = Mock()

    def test_that_it_successes_only_count_if_passes_are_currently_allowed(self):
        self.sensei.passesCount = Mock()
        MockableTestResult.addSuccess = Mock()
        self.sensei.addSuccess(Mock())
        self.assertTrue(self.sensei.passesCount.called)

    def test_that_it_increases_the_passes_on_every_success(self):
        pass_count = self.sensei.pass_count
        MockableTestResult.addSuccess = Mock()
        self.sensei.addSuccess(Mock())
        self.assertEqual(pass_count + 1, self.sensei.pass_count)

    def test_that_nothing_is_returned_as_sorted_result_if_there_are_no_failures(self):
        self.sensei.failures = []
        self.assertEqual(None, self.sensei.sortFailures("AboutLife"))

    def test_that_nothing_is_returned_as_sorted_result_if_there_are_no_relevent_failures(self):
        self.sensei.failures = [
            (AboutTheKnightsWhoSayNi(),"File 'about_the_knights_whn_say_ni.py', line 24"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 43"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 844")
        ]
        self.assertEqual(None, self.sensei.sortFailures("AboutLife"))

    def test_that_nothing_is_returned_as_sorted_result_if_there_are_3_shuffled_results(self):
        self.sensei.failures = [
            (AboutTennis(),"File 'about_tennis.py', line 299"),
            (AboutTheKnightsWhoSayNi(),"File 'about_the_knights_whn_say_ni.py', line 24"),
            (AboutTennis(),"File 'about_tennis.py', line 30"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 43"),
            (AboutTennis(),"File 'about_tennis.py', line 2"),
            (AboutMrGumby(),"File 'about_mr_gumby.py', line odd"),
            (AboutMessiahs(),"File 'about_messiahs.py', line 844")
        ]

        expected = [
            (AboutTennis(),"File 'about_tennis.py', line 2"),
            (AboutTennis(),"File 'about_tennis.py', line 30"),
            (AboutTennis(),"File 'about_tennis.py', line 299")
        ]

        results = self.sensei.sortFailures("AboutTennis")
        self.assertEqual(3, len(results))
        self.assertEqual(2, results[0][0])
        self.assertEqual(30, results[1][0])
        self.assertEqual(299, results[2][0])

    def test_that_it_will_choose_not_find_anything_with_non_standard_error_trace_string(self):
        self.sensei.failures = [
            (AboutMrGumby(),"File 'about_mr_gumby.py', line MISSING"),
        ]
        self.assertEqual(None, self.sensei.sortFailures("AboutMrGumby"))


    def test_that_it_will_choose_correct_first_result_with_lines_9_and_27(self):
        self.sensei.failures = [
            (AboutTrebuchets(),"File 'about_trebuchets.py', line 27"),
            (AboutTrebuchets(),"File 'about_trebuchets.py', line 9"),
            (AboutTrebuchets(),"File 'about_trebuchets.py', line 73v")
        ]
        self.assertEqual("File 'about_trebuchets.py', line 9", self.sensei.firstFailure()[1])

    def test_that_it_will_choose_correct_first_result_with_multiline_test_classes(self):
        self.sensei.failures = [
            (AboutGiantFeet(),"File 'about_giant_feet.py', line 999"),
            (AboutGiantFeet(),"File 'about_giant_feet.py', line 44"),
            (AboutFreemasons(),"File 'about_freemasons.py', line 1"),
            (AboutFreemasons(),"File 'about_freemasons.py', line 11")
        ]
        self.assertEqual("File 'about_giant_feet.py', line 44", self.sensei.firstFailure()[1])

    def test_that_error_report_features_a_stack_dump(self):
        self.sensei.scrapeInterestingStackDump = Mock()
        self.sensei.firstFailure = Mock()
        self.sensei.firstFailure.return_value = (Mock(), "FAILED")
        self.sensei.errorReport()
        self.assertTrue(self.sensei.scrapeInterestingStackDump.called)

    def test_that_scraping_the_assertion_error_with_nothing_gives_you_a_blank_back(self):
        self.assertEqual("", self.sensei.scrapeAssertionError(None))

    def test_that_scraping_the_assertion_error_with_messaged_assert(self):
        self.assertEqual("  AssertionError: Another fine mess you've got me into Stanley...",
            self.sensei.scrapeAssertionError(error_assertion_with_message))

    def test_that_scraping_the_assertion_error_with_assert_equals(self):
        self.assertEqual("  AssertionError: 4 != 99",
            self.sensei.scrapeAssertionError(error_assertion_equals))

    def test_that_scraping_the_assertion_error_with_assert_true(self):
        self.assertEqual("  AssertionError",
            self.sensei.scrapeAssertionError(error_assertion_true))

    def test_that_scraping_the_assertion_error_with_syntax_error(self):
        self.assertEqual("  SyntaxError: invalid syntax",
            self.sensei.scrapeAssertionError(error_mess))

    def test_that_scraping_the_assertion_error_with_list_error(self):
        self.assertEqual("""  AssertionError: Lists differ: [1, 9] != [1, 2]

  First differing element 1:
  9
  2

  - [1, 9]
  ?     ^

  + [1, 2]
  ?     ^""",
            self.sensei.scrapeAssertionError(error_with_list))

    def test_that_scraping_a_non_existent_stack_dump_gives_you_nothing(self):
        self.assertEqual("", self.sensei.scrapeInterestingStackDump(None))

    def test_that_if_there_are_no_failures_say_the_final_zenlike_remark(self):
        self.sensei.failures = None
        words = self.sensei.say_something_zenlike()

        m = re.search("Spanish Inquisition", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_are_0_successes_it_will_say_the_first_zen_of_python_koans(self):
        self.sensei.pass_count = 0
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Beautiful is better than ugly", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_1_successes_it_will_say_the_second_zen_of_python_koans(self):
        self.sensei.pass_count = 1
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Explicit is better than implicit", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_10_successes_it_will_say_the_sixth_zen_of_python_koans(self):
        self.sensei.pass_count = 10
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Sparse is better than dense", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_36_successes_it_will_say_the_final_zen_of_python_koans(self):
        self.sensei.pass_count = 36
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Namespaces are one honking great idea", words)
        self.assertTrue(m and m.group(0))

    def test_that_if_there_is_37_successes_it_will_say_the_first_zen_of_python_koans_again(self):
        self.sensei.pass_count = 37
        self.sensei.failures = Mock()
        words = self.sensei.say_something_zenlike()

        m = re.search("Beautiful is better than ugly", words)
        self.assertTrue(m and m.group(0))

    def test_that_total_lessons_return_7_if_there_are_7_lessons(self):
        self.sensei.filter_all_lessons = Mock()
        self.sensei.filter_all_lessons.return_value = [1,2,3,4,5,6,7]

        self.assertEqual(7, self.sensei.total_lessons())

    def test_that_total_lessons_return_0_if_all_lessons_is_none(self):
        self.sensei.filter_all_lessons = Mock()
        self.sensei.filter_all_lessons.return_value = None

        self.assertEqual(0, self.sensei.total_lessons())

    def test_total_koans_return_43_if_there_are_43_test_cases(self):
        self.sensei.tests.countTestCases = Mock()
        self.sensei.tests.countTestCases.return_value = 43

        self.assertEqual(43, self.sensei.total_koans())

    def test_filter_all_lessons_will_discover_test_classes_if_none_have_been_discovered_yet(self):
        self.sensei.all_lessons = 0
        self.assertTrue(len(self.sensei.filter_all_lessons()) > 10)
        self.assertTrue(len(self.sensei.all_lessons) > 10)

########NEW FILE########
__FILENAME__ = sensei
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import re
import sys
import os
import glob

from . import helper
from .mockable_test_result import MockableTestResult
from runner import path_to_enlightenment

from libs.colorama import init, Fore, Style
init() # init colorama

class Sensei(MockableTestResult):
    def __init__(self, stream):
        unittest.TestResult.__init__(self)
        self.stream = stream
        self.prevTestClassName = None
        self.tests = path_to_enlightenment.koans()
        self.pass_count = 0
        self.lesson_pass_count  = 0
        self.all_lessons = None

    def startTest(self, test):
        MockableTestResult.startTest(self, test)

        if helper.cls_name(test) != self.prevTestClassName:
            self.prevTestClassName = helper.cls_name(test)
            if not self.failures:
                self.stream.writeln()
                self.stream.writeln("{0}{1}Thinking {2}".format(
                    Fore.RESET, Style.NORMAL, helper.cls_name(test)))
                if helper.cls_name(test) != 'AboutAsserts':
                    self.lesson_pass_count += 1

    def addSuccess(self, test):
        if self.passesCount():
            MockableTestResult.addSuccess(self, test)
            self.stream.writeln( \
                "  {0}{1}{2} has expanded your awareness.{3}{4}" \
                .format(Fore.GREEN, Style.BRIGHT, test._testMethodName, \
                Fore.RESET, Style.NORMAL))
            self.pass_count += 1

    def addError(self, test, err):
        # Having 1 list for errors and 1 list for failures would mess with
        # the error sequence
        self.addFailure(test, err)

    def passesCount(self):
        return not (self.failures and helper.cls_name(self.failures[0][0]) != self.prevTestClassName)

    def addFailure(self, test, err):
        MockableTestResult.addFailure(self, test, err)

    def sortFailures(self, testClassName):
        table = list()
        for test, err in self.failures:
            if helper.cls_name(test) ==  testClassName:
                m = re.search("(?<= line )\d+" ,err)
                if m:
                    tup = (int(m.group(0)), test, err)
                    table.append(tup)

        if table:
            return sorted(table)
        else:
            return None

    def firstFailure(self):
        if not self.failures: return None

        table = self.sortFailures(helper.cls_name(self.failures[0][0]))

        if table:
            return (table[0][1], table[0][2])
        else:
            return None

    def learn(self):
        self.errorReport()

        self.stream.writeln("")
        self.stream.writeln("")
        self.stream.writeln(self.report_progress())
        if self.failures:
          self.stream.writeln(self.report_remaining())
        self.stream.writeln("")
        self.stream.writeln(self.say_something_zenlike())

        if self.failures: sys.exit(-1)
        self.stream.writeln(
            "\n{0}**************************************************" \
            .format(Fore.RESET))
        self.stream.writeln("\n{0}That was the last one, well done!" \
            .format(Fore.MAGENTA))
        self.stream.writeln(
            "\nIf you want more, take a look at about_extra_credit_task.py{0}{1}" \
            .format(Fore.RESET, Style.NORMAL))

    def errorReport(self):
        problem = self.firstFailure()
        if not problem: return
        test, err = problem
        self.stream.writeln("  {0}{1}{2} has damaged your "
          "karma.".format(Fore.RED, Style.BRIGHT, test._testMethodName))

        self.stream.writeln("\n{0}{1}You have not yet reached enlightenment ..." \
            .format(Fore.RESET, Style.NORMAL))
        self.stream.writeln("{0}{1}{2}".format(Fore.RED, \
            Style.BRIGHT, self.scrapeAssertionError(err)))
        self.stream.writeln("")
        self.stream.writeln("{0}{1}Please meditate on the following code:" \
            .format(Fore.RESET, Style.NORMAL))
        self.stream.writeln("{0}{1}{2}{3}{4}".format(Fore.YELLOW, Style.BRIGHT, \
            self.scrapeInterestingStackDump(err), Fore.RESET, Style.NORMAL))

    def scrapeAssertionError(self, err):
        if not err: return ""

        error_text = ""
        count = 0
        for line in err.splitlines():
            m = re.search("^[^^ ].*$",line)
            if m and m.group(0):
                count+=1

            if count>1:
                error_text += ("  " + line.strip()).rstrip() + '\n'
        return error_text.strip('\n')

    def scrapeInterestingStackDump(self, err):
        if not err:
            return ""

        lines = err.splitlines()

        sep = '@@@@@SEP@@@@@'

        stack_text = ""
        for line in lines:
            m = re.search("^  File .*$",line)
            if m and m.group(0):
                stack_text += '\n' + line

            m = re.search("^    \w(\w)+.*$",line)
            if m and m.group(0):
                stack_text += sep + line

        lines = stack_text.splitlines()

        stack_text = ""
        for line in lines:
            m = re.search("^.*[/\\\\]koans[/\\\\].*$",line)
            if m and m.group(0):
                stack_text += line + '\n'


        stack_text = stack_text.replace(sep, '\n').strip('\n')
        stack_text = re.sub(r'(about_\w+.py)',
                r"{0}\1{1}".format(Fore.BLUE, Fore.YELLOW), stack_text)
        stack_text = re.sub(r'(line \d+)',
                r"{0}\1{1}".format(Fore.BLUE, Fore.YELLOW), stack_text)
        return stack_text

    def report_progress(self):
        return "You have completed {0} koans and " \
            "{1} lessons.".format(
                self.pass_count,
                self.lesson_pass_count)

    def report_remaining(self):
        koans_remaining = self.total_koans() - self.pass_count
        lessons_remaining = self.total_lessons() - self.lesson_pass_count

        return "You are now {0} koans and {1} lessons away from " \
            "reaching enlightenment.".format(
                koans_remaining,
                lessons_remaining)

    # Hat's tip to Tim Peters for the zen statements from The 'Zen
    # of Python' (http://www.python.org/dev/peps/pep-0020/)
    #
    # Also a hat's tip to Ara T. Howard for the zen statements from his
    # metakoans Ruby Quiz (http://rubyquiz.com/quiz67.html) and
    # Edgecase's later permutation in the Ruby Koans
    def say_something_zenlike(self):
        if self.failures:
            turn = self.pass_count % 37

            zenness = "";
            if turn == 0:
                zenness = "Beautiful is better than ugly."
            elif turn == 1 or turn == 2:
                zenness = "Explicit is better than implicit."
            elif turn == 3 or turn == 4:
                zenness = "Simple is better than complex."
            elif turn == 5 or turn == 6:
                zenness = "Complex is better than complicated."
            elif turn == 7 or turn == 8:
                zenness = "Flat is better than nested."
            elif turn == 9 or turn == 10:
                zenness = "Sparse is better than dense."
            elif turn == 11 or turn == 12:
                zenness = "Readability counts."
            elif turn == 13 or turn == 14:
                zenness = "Special cases aren't special enough to " \
                          "break the rules."
            elif turn == 15 or turn == 16:
                zenness = "Although practicality beats purity."
            elif turn == 17 or turn == 18:
                zenness = "Errors should never pass silently."
            elif turn == 19 or turn == 20:
                zenness = "Unless explicitly silenced."
            elif turn == 21 or turn == 22:
                zenness = "In the face of ambiguity, refuse the " \
                          "temptation to guess."
            elif turn == 23 or turn == 24:
                zenness = "There should be one-- and preferably only " \
                          "one --obvious way to do it."
            elif turn == 25 or turn == 26:
                zenness = "Although that way may not be obvious at " \
                          "first unless you're Dutch."
            elif turn == 27 or turn == 28:
                zenness = "Now is better than never."
            elif turn == 29 or turn == 30:
                zenness = "Although never is often better than right " \
                          "now."
            elif turn == 31 or turn == 32:
                zenness = "If the implementation is hard to explain, " \
                          "it's a bad idea."
            elif turn == 33 or turn == 34:
                zenness = "If the implementation is easy to explain, " \
                          "it may be a good idea."
            else:
                zenness = "Namespaces are one honking great idea -- " \
                          "let's do more of those!"
            return "{0}{1}{2}{3}".format(Fore.CYAN, zenness, Fore.RESET, Style.NORMAL);
        else:
            return "{0}Nobody ever expects the Spanish Inquisition." \
                .format(Fore.CYAN)

        # Hopefully this will never ever happen!
        return "The temple is collapsing! Run!!!"

    def total_lessons(self):
        all_lessons = self.filter_all_lessons()
        if all_lessons:
          return len(all_lessons)
        else:
          return 0

    def total_koans(self):
        return self.tests.countTestCases()

    def filter_all_lessons(self):
        cur_dir = os.path.split(os.path.realpath(__file__))[0]
        if not self.all_lessons:
            self.all_lessons = glob.glob('{0}/../koans/about*.py'.format(cur_dir))
            self.all_lessons = list(filter(lambda filename:
                                      "about_extra_credit" not in filename,
                                      self.all_lessons))

        return self.all_lessons

########NEW FILE########
__FILENAME__ = writeln_decorator
#!/usr/bin/env python
# encoding: utf-8

import sys
import os

# Taken from legacy python unittest
class WritelnDecorator:
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        return getattr(self.stream,attr)

    def writeln(self, arg=None):
        if arg: self.write(arg)
        self.write('\n') # text-mode streams translate to \r\n if needed


########NEW FILE########
__FILENAME__ = _runner_tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest

from runner.runner_tests.test_mountain import TestMountain
from runner.runner_tests.test_sensei import TestSensei
from runner.runner_tests.test_helper import TestHelper

def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMountain))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSensei))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHelper))
    return suite

if __name__ == '__main__':
    res = unittest.TextTestRunner(verbosity=2).run(suite())
    sys.exit(not res.wasSuccessful())

########NEW FILE########
