__FILENAME__ = nosecomplete
import os
import sys
import re
import ast

from optparse import OptionParser


class PythonTestFinder(object):
    def find_functions(self, ast_body, matcher):
        for obj in ast_body:
            if not matcher(obj):
                continue
            if isinstance(obj, ast.FunctionDef):
                yield obj.name
            if isinstance(obj, ast.ClassDef):
                for func in self.find_functions(obj.body, matcher):
                    yield '%s.%s' % (obj.name, func)

    def get_module_tests(self, module):
        with open(module) as f:
            data = f.read()
        result = ast.parse(data)

        def matcher(obj):
            if isinstance(obj, ast.FunctionDef):
                return re.search('test', obj.name, re.IGNORECASE)
            # Unlike nose, we're not able to determine whether this class
            # inherits from unittest.TestCase
            # So it may be the case that this class name lacks 'test'. As a
            # compromise, match all classes
            return isinstance(obj, ast.ClassDef)
        tests = list(
            self.find_functions(result.body, matcher)
        )
        return tests


class NoseTestFinder(object):
    def _generate_tests(self, suite):
        from nose.suite import ContextSuite
        from nose.case import Test
        for context in suite._tests:
            if isinstance(context, Test):
                yield context
                continue
            assert isinstance(context, ContextSuite)
            for test in self._generate_tests(context):
                yield test

    def _get_test_name(self, test_wrapper):
        from nose.case import FunctionTestCase
        test = test_wrapper.test
        if isinstance(test, FunctionTestCase):
            return test.test.__name__
        return test.__class__.__name__ + '.' + test._testMethodName

    def _generate_test_names(self, suite):
        return map(self._get_test_name, self._generate_tests(suite))

    def get_module_tests(self, module):
        import nose
        loader = nose.loader.defaultTestLoader()
        return self._generate_test_names(loader.loadTestsFromName(module))


def _get_prefixed(strings, prefix):
    for string in strings:
        if string.startswith(prefix):
            yield string.replace(prefix, '', 1)


def _get_py_or_dirs(directory, prefix):
    for entry in os.listdir(directory or '.'):
        path = os.path.join(directory, entry)
        if entry.startswith(prefix):
            leftover = entry.replace(prefix, '', 1)
            if os.path.isdir(path):
                yield leftover + '/'
            elif leftover.endswith('.py'):
                yield leftover + ':'


def _complete(test_finder, thing):
    if ':' in thing:
        # complete a test
        module, test_part = thing.split(':')
        tests = list(test_finder.get_module_tests(module))
        if '.' in test_part:
            # complete a method
            return _get_prefixed(strings=tests, prefix=test_part)
        funcs = [test for test in tests if test.count('.') == 0]
        classes = [test.split('.')[0] for test in tests if '.' in test]
        if test_part in classes:
            # indicate a method should be completed
            return ['.']
        return _get_prefixed(strings=funcs + classes, prefix=test_part)
    if os.path.isdir(thing):
        # complete directory contents
        if thing != '.' and not thing.endswith('/'):
            return ['/']
        return _get_py_or_dirs(thing, '')
    if os.path.exists(thing):
        # add a colon to indicate search for specific class/func
        return [':']
    # path not exists, complete a partial path
    directory, file_part = os.path.split(thing)
    return _get_py_or_dirs(directory, file_part)


def complete(test_finder, thing):
    for option in set(_complete(test_finder, thing)):
        sys.stdout.write(thing + option + ' ')  # avoid print for python 3


def main():
    methods = {
        'nose': NoseTestFinder,
        'python': PythonTestFinder,
    }
    parser = OptionParser(usage='usage: %prog [options] ')
    parser.add_option(
        "-s",
        "--search-method",
        help="Search method to use when locating tests",
        choices=list(methods.keys()),
        default='python',
    )
    (options, args) = parser.parse_args()
    finder_class = methods[options.search_method]
    finder_instance = finder_class()

    complete(finder_instance, './' if len(args) == 0 else args[0])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = basic
import unittest


def test_red():
    pass


class AwesomeTestCase(unittest.TestCase):
    def test_yellow(self):
        pass

    def test_green(self):
        pass


def test_blue():
    pass

########NEW FILE########
__FILENAME__ = tests
import unittest
import nosecomplete

FIXTURES = {
    'basic': 'tests/fixtures/basic.py',
}

class _BaseTestFinderTestCase(unittest.TestCase):

    def test_complete(self):
        # this prints to the screen.. just make sure the code's not broken
        nosecomplete.complete(self.finder, FIXTURES['basic'])
    
    def test_basic(self):
        actual = list(self.finder.get_module_tests(FIXTURES['basic']))
        expected = [
            'AwesomeTestCase.test_green',
            'AwesomeTestCase.test_yellow',
            'test_red',
            'test_blue',
        ]
        self.assertEqual(set(actual), set(expected))
        
    def _assert_complete(self, thing, options):
        self.assertEqual(set(nosecomplete._complete(self.finder, thing)),
                         set(options))

    def test_dir_prefix(self):
        self._assert_complete('tests/fixtures', ['/'])
        
    def test_dir(self):
        try:
            options = ['fixtures/', '__init__.py:', 'tests.py:']
            self._assert_complete('tests/', options)
        except AssertionError:
            options.append('__pycache__/') # py3 leaves these around
            self._assert_complete('tests/', options)
                
    def test_partial_filename(self):
        self._assert_complete('tests/fixtures/ba', ['sic.py:'])
        
    def test_filename(self):
        self._assert_complete('tests/fixtures/basic.py', [':'])

    def test_partial_case(self):
        self._assert_complete('tests/fixtures/basic.py:test', ['_red', '_blue'])

    def test_partial_class(self):
        self._assert_complete('tests/fixtures/basic.py:AwesomeTestCase', ['.'])

    def test_partial_method(self):
        self._assert_complete('tests/fixtures/basic.py:AwesomeTestCase.',
                              ['test_green',
                               'test_yellow'])
        
class NoseTestFinderTestCase(_BaseTestFinderTestCase):
    finder = nosecomplete.NoseTestFinder()
    
class PythonTestFinderTestCase(_BaseTestFinderTestCase):
    finder = nosecomplete.PythonTestFinder()


########NEW FILE########
