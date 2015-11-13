__FILENAME__ = dingus
import sys
from functools import wraps

def DingusTestCase(object_under_test, exclude=None):
    if isinstance(exclude, basestring):
        raise ValueError("Strings not allowed for exclude. " +
                         "Use a list: exclude=['identifier']")
    exclude = [] if exclude is None else exclude

    def get_names_under_test():
        module = sys.modules[object_under_test.__module__]
        for name, value in module.__dict__.iteritems():
            if value is object_under_test or name in exclude:
                yield name

    class TestCase(object):
        def setup(self):
            module_name = object_under_test.__module__
            self._dingus_module = sys.modules[module_name]
            self._dingus_replace_module_globals(self._dingus_module)

        def teardown(self):
            self._dingus_restore_module(self._dingus_module)

        def _dingus_replace_module_globals(self, module):
            old_module_dict = module.__dict__.copy()
            module_keys = set(module.__dict__.iterkeys())

            dunders = set(k for k in module_keys
                           if k.startswith('__') and k.endswith('__'))
            replaced_keys = (module_keys - dunders - set(names_under_test))
            for key in replaced_keys:
                module.__dict__[key] = Dingus()
            module.__dict__['__dingused_dict__'] = old_module_dict

        def _dingus_restore_module(self, module):
            old_module_dict = module.__dict__['__dingused_dict__']
            module.__dict__.clear()
            module.__dict__.update(old_module_dict)

    names_under_test = list(get_names_under_test())
    TestCase.__name__ = '%s_DingusTestCase' % '_'.join(names_under_test)
    return TestCase


# These sentinels are used for argument defaults because the user might want
# to pass in None, which is different in some cases than passing nothing.
class NoReturnValue(object):
    pass
class NoArgument(object):
    pass


def patch(object_path, new_object=NoArgument):
    module_name, attribute_name = object_path.rsplit('.', 1)
    return _Patcher(module_name, attribute_name, new_object)


class _Patcher:
    def __init__(self, module_name, attribute_name, new_object):
        self.module_name = module_name
        self.attribute_name = attribute_name
        self.module = _importer(self.module_name)
        if new_object is NoArgument:
            full_name = '%s.%s' % (module_name, attribute_name)
            self.new_object = Dingus(full_name)
        else:
            self.new_object = new_object

    def __call__(self, fn):
        @wraps(fn)
        def new_fn(*args, **kwargs):
            self.patch_object()
            try:
                return fn(*args, **kwargs)
            finally:
                self.restore_object()
        new_fn.__wrapped__ = fn
        return new_fn

    def __enter__(self):
        self.patch_object()

    def __exit__(self, exc_type, exc_value, traceback):
        self.restore_object()

    def patch_object(self):
        self.original_object = getattr(self.module, self.attribute_name)
        setattr(self.module, self.attribute_name, self.new_object)

    def restore_object(self):
        setattr(self.module, self.attribute_name, self.original_object)


def isolate(object_path):
    def decorator(fn):
        module_name, object_name = object_path.rsplit('.', 1)
        module = sys.modules[module_name]
        neighbors = set(dir(module)) - set([object_name])
        for neighbor in neighbors:
            neighbor_path = '%s.%s' % (module_name, neighbor)
            fn = patch(neighbor_path)(fn)
        return fn
    return decorator


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


class DontCare(object):
    pass


class Call(tuple):
    def __new__(cls, name, args, kwargs, return_value):
        return tuple.__new__(cls, (name, args, kwargs, return_value))

    def __init__(self, *args):
        self.name = self[0]
        self.args = self[1]
        self.kwargs = self[2]
        self.return_value = self[3]
        
    def __getnewargs__(self):
        return (self.name, self.args, self.kwargs, self.return_value)


class CallList(list):
    @staticmethod
    def _match_args(call, args):
        if not args:
            return True
        elif len(args) != len(call.args):
            return False
        else:
            return all(args[i] in (DontCare, call.args[i])
                       for i in range(len(call.args)))

    @staticmethod
    def _match_kwargs(call, kwargs):
        if not kwargs:
            return True
        elif len(kwargs) != len(call.kwargs):
            return False
        else:
            return all(name in kwargs and kwargs[name] in (DontCare, val)
                       for name, val in call.kwargs.iteritems())

    def one(self):
        if len(self) == 1:
            return self[0]
        else:
            return None

    def once(self):
        return self.one()

    def __call__(self, __name=NoArgument, *args, **kwargs):
        return CallList([call for call in self
                         if (__name is NoArgument or __name == call.name)
                         and self._match_args(call, args)
                         and self._match_kwargs(call, kwargs)])


def returner(return_value):
    return Dingus(return_value=return_value)


class Dingus(object):
    @property
    def __enter__(self):
        return self._existing_or_new_child('__enter__')

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if exc_type and exc_type not in self.consumed_context_manager_exceptions:
            return False
        else:
            return True

    def __init__(self,
                 dingus_name=None,
                 full_name=None,
                 consumed_context_manager_exceptions=None,
                 **kwargs):
        self._parent = None
        self.reset()
        name = 'dingus_%i' % id(self) if dingus_name is None else dingus_name
        full_name = name if full_name is None else full_name
        self._short_name = name
        self._full_name = full_name
        self.__name__ = name
        self._full_name = full_name
        self.consumed_context_manager_exceptions = (
            consumed_context_manager_exceptions or [])

        for attr_name, attr_value in kwargs.iteritems():
            if attr_name.endswith('__returns'):
                attr_name = attr_name.replace('__returns', '')
                returner = self._create_child(attr_name)
                returner.return_value = attr_value
                setattr(self, attr_name, returner)
            else:
                setattr(self, attr_name, attr_value)

        self._replace_init_method()

    @classmethod
    def many(cls, count):
        return tuple(cls() for _ in range(count))

    def _fake_init(self, *args, **kwargs):
        return self.__getattr__('__init__')(*args, **kwargs)

    def _replace_init_method(self):
        self.__init__ = self._fake_init

    def _create_child(self, name):
        separator = ('' if (name.startswith('()') or name.startswith('['))
                     else '.')
        full_name = self._full_name + separator + name
        child = self.__class__(name, full_name)
        child._parent = self
        return child

    def reset(self):
        self._return_value = NoReturnValue
        self.calls = CallList()
        self._children = {}

    def assert_call(self, *args, **kwargs):
        expected_call = self.calls('()', *args, **kwargs)
        if expected_call:
            return
        recorded_calls = self.calls
        calls_description = "No calls recorded" if not recorded_calls \
                                                else "Recorded calls: %s" % recorded_calls
        message = "Expected a call to: '%s', " % self + \
                  "args: %s, kwargs: %s, " % (args, kwargs) + \
                  "\n" + calls_description

        raise AssertionError(message)

    def _get_return_value(self):
        if self._return_value is NoReturnValue:
            self._return_value = self._create_child('()')
        return self._return_value

    def _set_return_value(self, value):
        self._return_value = value

    return_value = property(_get_return_value, _set_return_value)

    def __call__(self, *args, **kwargs):
        self._log_call('()', args, kwargs, self.return_value)
        if self._parent:
            self._parent._log_call(self._short_name,
                                   args,
                                   kwargs,
                                   self.return_value)

        return self.return_value

    def _log_call(self, name, args, kwargs, return_value):
        self.calls.append(Call(name, args, kwargs, return_value))

    def _should_ignore_attribute(self, name):
        return name in ['__pyobjc_object__', '__getnewargs__']
    
    def __getstate__(self):
        # Python cannot pickle a instancemethod
        # http://bugs.python.org/issue558238
        return [ (attr, value) for attr, value in self.__dict__.items() if attr != "__init__"]
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._replace_init_method()

    def _existing_or_new_child(self, child_name, default_value=NoArgument):
        if child_name not in self._children:
            value = (self._create_child(child_name)
                     if default_value is NoArgument
                     else default_value)
            self._children[child_name] = value

        return self._children[child_name]

    def _remove_child_if_exists(self, child_name):
        if child_name in self._children:
            del self._children[child_name]

    def __getattr__(self, name):
        if self._should_ignore_attribute(name):
            raise AttributeError(name)
        return self._existing_or_new_child(name)

    def __delattr__(self, name):
        self._log_call('__delattr__', (name,), {}, None)

    def __getitem__(self, index):
        child_name = '[%s]' % (index,)
        return_value = self._existing_or_new_child(child_name)
        self._log_call('__getitem__', (index,), {}, return_value)
        return return_value

    def __setitem__(self, index, value):
        child_name = '[%s]' % (index,)
        self._log_call('__setitem__', (index, value), {}, None)
        self._remove_child_if_exists(child_name)
        self._existing_or_new_child(child_name, value)

    def _create_infix_operator(name):
        def operator_fn(self, other):
            return_value = self._existing_or_new_child(name)
            self._log_call(name, (other,), {}, return_value)
            return return_value
        operator_fn.__name__ = name
        return operator_fn

    _BASE_OPERATOR_NAMES = ['add', 'and', 'div', 'lshift', 'mod', 'mul', 'or',
                            'pow', 'rshift', 'sub', 'xor']

    def _infix_operator_names(base_operator_names):
        # This function has to have base_operator_names passed in because
        # Python's scoping rules prevent it from seeing the class-level
        # _BASE_OPERATOR_NAMES.

        reverse_operator_names = ['r%s' % name for name in base_operator_names]
        for operator_name in base_operator_names + reverse_operator_names:
            operator_fn_name = '__%s__' % operator_name
            yield operator_fn_name

    # Define each infix operator
    for operator_fn_name in _infix_operator_names(_BASE_OPERATOR_NAMES):
        exec('%s = _create_infix_operator("%s")' % (operator_fn_name,
                                              operator_fn_name))

    def _augmented_operator_names(base_operator_names):
        # Augmented operators are things like +=. They behavior differently
        # than normal infix operators because they return self instead of a
        # new object.

        return ['__i%s__' % operator_name
                for operator_name in base_operator_names]

    def _create_augmented_operator(name):
        def operator_fn(self, other):
            return_value = self
            self._log_call(name, (other,), {}, return_value)
            return return_value
        operator_fn.__name__ = name
        return operator_fn

    # Define each augmenting operator
    for operator_fn_name in _augmented_operator_names(_BASE_OPERATOR_NAMES):
        exec('%s = _create_augmented_operator("%s")' % (operator_fn_name,
                                                        operator_fn_name))

    def __str__(self):
        return '<Dingus %s>' % self._full_name
    __repr__ = __str__

    def __len__(self):
        return 1

    def __iter__(self):
        return iter([self._existing_or_new_child('__iter__')])

    # We don't want to define __deepcopy__ at all. If there isn't one, deepcopy
    # will clone the whole object, which is what we want.
    __deepcopy__ = None


def exception_raiser(exception):
    def raise_exception(*args, **kwargs):
        raise exception
    return raise_exception

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import sys

import nose


if __name__ == '__main__':
    nose_args = sys.argv + [r'-m',
                            r'((?:^|[b_.-])(:?[Tt]est|When|should))']
    nose.run(argv=nose_args)


########NEW FILE########
__FILENAME__ = test_urllib2
from dingus import DingusTestCase, DontCare
import urllib2
from urllib2 import urlopen


# We want to unit test the urlopen function. It's very small (as you can see
# by looking at the source at ${PYTHON_INSTALL}/lib/python2.5/urllib2.py
#
# (This example assumes Python 2.5. Hopefully it also works for your version.)
#
# Dingus allows us to test urlopen without actually touching the network, or
# any other classes and functions at all. When we define the test class, we
# inherit from "DingusTestCase(urlopen)". DingusTestCase will define setup and
# teardown method that replace every object in urllib2 with a dingus
# (except urlopen, which is the "object under test". It does this by looking
# at the module that urlopen was defined in, making a backup copy of its
# contents, then replacing everything with a dingus. So, instead of making
# network connections as it usually would, urlopen will be making calls into
# the dinguses, which will record the calls so that we can make assertions
# about them later.
class WhenOpeningURLs(DingusTestCase(urlopen)):
    def setup(self):
        # We have to call DingusTestCase's setup method so that it can
        # modify the urllib2 module's contents.
        super(WhenOpeningURLs, self).setup()

        # We set up the object under test here by calling urlopen with a URL.
        self.url = 'http://www.example.com'
        self.opened_url = urlopen(self.url)

    # First, we expect urlopen to try to open the URL.
    def should_open_provided_url(self):
        # Normally urlopen would use a prexisting "opener" object that would
        # touch the network, disk, etc., but DingusTestCase has replaced it
        # with a dingus. We first grab that _opener object so we can make
        # assertions about it.
        opener = urllib2._opener

        # We want to assert that urlopen should call "open" on the opener,
        # passing the URL we gave it. "open" also takes another argument, but
        # we don't care about that for this test. We pass in DontCare for
        # things we don't care about, and the dingus will ignore that argument
        # for the purposes of this assertion.
        #     assert opener.calls('open', self.url, DontCare, DontCare).once()
        # However, since we want this test to work across all Python versions,
        # and the opener.open() call differs between them, we'll use a
        # slightly more complex method to only check the first argument of the
        # open() call.
        assert opener.calls('open').once().args[0] == self.url

        # Note that we never told the _opener dingus that it should have an
        # "open" method. A dingus has *all* methods - it will try to allow
        # anything to be done to it.

    def should_return_opened_url(self):
        # Now we want to assert that the opened object is returned to the
        # caller. The line of code from urllib2 that we're testing is:
        #     return _opener.open(url, data)
        # We need to make sure that urlopen returned the result of that. We do
        # that by accessing _opener.open.return_value. _opener.open is the
        # dingus that replaced the original _opener.open method. The
        # return_value is a special attribute of all dinguses that gets
        # returned when the dingus is called as a function.
        assert self.opened_url is urllib2._opener.open.return_value

    # We could also define a teardown method for this test class, but that's
    # rarely needed when writing fully isolated tests like this one.
    # DingusTestCase does define a teardown method, though - it reverses the
    # changes it made to the module under test, removing the dinguses and
    # restoring the module's original contents. This class inherited it, so we
    # don't have to call it manually.


########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import sys

import nose


if __name__ == '__main__':
    nose_args = sys.argv + [r'-m',
                            r'((?:^|[b_.-])(:?[Tt]est|When|should))']
    nose.run(argv=nose_args)


########NEW FILE########
__FILENAME__ = socket_reader
def read_socket(socket):
    data = socket.recv(1024)
    socket.close()
    return data


########NEW FILE########
__FILENAME__ = test_socket_reader
from dingus import Dingus

from socket_reader import read_socket


class TestSocketReader:
    def setup(self):
        self.socket = Dingus()
        self.data_that_was_read = read_socket(self.socket)

    def should_read_from_socket(self):
        assert self.socket.calls('recv', 1024).once()

    def should_return_what_is_read(self):
        assert self.data_that_was_read == self.socket.recv()

    def should_close_socket_after_reading(self):
        # Sequence tests like this often aren't needed, as your higher-level
        # system tests will catch such problems. But I include one here to
        # illustrate more complex use of the "calls" list.

        assert self.socket.calls('close')
        call_names = [call.name for call in self.socket.calls]
        assert call_names.index('close') > call_names.index('recv')


########NEW FILE########
__FILENAME__ = nosy
'''
Watch for changes in all .py files. If changes, run nosetests. 
'''

# By Gary Bernhardt, http://extracheese.org
# Based on original nosy.py by Jeff Winkler, http://jeffwinkler.net


import sys, glob, os, stat, time
from hashlib import md5
import subprocess
import re


FILE_REGEX = re.compile(r'(py|README)$')
STAT_INTERVAL = .25 # seconds
CRAWL_INTERVAL = 10 # seconds


class Crawler:
    def __init__(self):
        self.last_crawl = 0
        self.filenames = []

    def crawl(self):
        # Only crawl if enough time has passed since the last crawl
        if time.time() - self.last_crawl < CRAWL_INTERVAL:
            return self.filenames

        self.last_crawl = time.time()

        # Build a list of all directories that are children of this one
        paths = ['.']
        for dirpath, _, filenames in os.walk('.'):
            paths += [os.path.join(dirpath, filename)
                      for filename in filenames]

        # Return all files in one of those directories that match the regex
        filenames = set([path
                         for path in paths
                         if re.search(FILE_REGEX, path)])
        self.filenames = filenames
        return self.filenames

    def checksum(self):
        """
        Return a dictionary that represents the current state of this
        directory
        """
        def stat_string(path):
            stat = os.stat(path)
            return '%s,%s' % (str(stat.st_size), str(stat.st_mtime))

        return dict((path, stat_string(path))
                    for path in self.crawl()
                    if os.path.exists(path))


iterations = 0


def print_changes(changed_paths):
    global iterations
    iterations += 1

    print
    print
    print
    print '----- Iteration', iterations, '(%s)' % time.ctime()

    if changed_paths:
        print '      Changes:', ', '.join(sorted(changed_paths))


def change_generator():
    yield []
    crawler = Crawler()
    old_checksum = crawler.checksum()

    while True:
        time.sleep(STAT_INTERVAL)
        new_checksum = crawler.checksum()

        if new_checksum != old_checksum:
            # Wait and recaculate the checksum, so if multiple files are being
            # written we get them all in one iteration
            time.sleep(0.2)
            new_checksum = crawler.checksum()

            old_keys = set(old_checksum.keys())
            new_keys = set(new_checksum.keys())
            common_keys = old_keys.intersection(new_keys)

            # Add any files that exist in only one checksum
            changes = old_keys.symmetric_difference(new_keys)
            # Add any files that exist in both but changed
            changes.update([key for key in common_keys
                            if new_checksum[key] != old_checksum[key]])

            old_checksum = new_checksum
            yield changes


def main():
    old_checksum = None

    for changed_paths in change_generator():
        print_changes(changed_paths)
        os.system(' '.join(sys.argv[1:]))

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import sys

import nose


if __name__ == '__main__':
    nose_args = sys.argv + [r'-m',
                            r'((?:^|[b_.-])(:?[Tt]est|When|should))',
                            r'--with-doctest',
                            r'--doctest-extension=']
    nose.run(argv=nose_args)


########NEW FILE########
__FILENAME__ = test_assert_call
from dingus import Dingus
from nose.tools import raises


class AssertCallTest(object):

    def setup(self):
        self.ding = Dingus('ding')

class WhenCallsExists(AssertCallTest):

    def should_not_raise_any_error_simple_call(self):
        self.ding.foo()

        self.ding.foo.assert_call()

    def should_not_raise_any_error_with_args(self):
        self.ding.foo('bar')

        self.ding.foo.assert_call()
        self.ding.foo.assert_call('bar')

    def should_not_raise_any_error_with_args_and_kwargs(self):
        self.ding.foo('bar', qux=1)

        self.ding.foo.assert_call()
        self.ding.foo.assert_call('bar')
        self.ding.foo.assert_call('bar', qux=1)

class WhenThereIsNoCallsForTheMatchedArgs(AssertCallTest):

    @raises(AssertionError)
    def should_raise_an_assertion_error(self):
        self.ding.foo.assert_call()

    @raises(AssertionError)
    def should_raise_an_assertion_error_other_method_call(self):
        self.ding.bar()

        self.ding.foo.assert_call()

    @raises(AssertionError)
    def should_raise_an_assertion_error_with_args(self):
        self.ding.foo()

        self.ding.foo.assert_call('bar')

    @raises(AssertionError)
    def should_raise_an_assertion_error_with_args_and_kargs(self):
        self.ding.foo('bar')

        self.ding.foo.assert_call('bar', qux=1)

    def should_show_a_friendly_error_message(self):
        self._test_expectation_message('foo')

    def should_show_a_friendly_error_message_with_args(self):
        self._test_expectation_message('foo', 'baz', 'qux')

    def should_show_a_friendly_error_message_with_args_and_kargs(self):
        self._test_expectation_message('foo', 'baz', 'qux', one=1, two=2)

    def _test_expectation_message(self, method, *args, **kwargs):
        try:
            dingus = getattr(self.ding, method)
            dingus.assert_call(*args, **kwargs)
        except AssertionError, e:
            self._assert_message(e.message, dingus, args, kwargs)
        else:
            assert False, 'should not be here'

    def _assert_message(self, message, dingus, args, kwargs):
            expected, recorded_calls = message.split('\n')

            assert "Expected a call to: '%s', args: %s, kwargs: %s, " % (dingus, args, kwargs)

            if not self.ding.calls:
                assert "No calls recorded" == recorded_calls
            else:
                assert ("Recorded calls: %s" % self.ding.calls) == recorded_calls

########NEW FILE########
__FILENAME__ = test_call
import pickle

from dingus import Call


class WhenInstantiated:
    def setup(self):
        self.call = Call('test name',
                         'test args',
                         'test kwargs',
                         'test return_value')

    def should_have_name(self):
        assert self.call.name == 'test name'

    def should_have_args(self):
        assert self.call.args == 'test args'

    def should_have_kwargs(self):
        assert self.call.kwargs == 'test kwargs'

    def should_have_return_value(self):
        assert self.call.return_value == 'test return_value'


class WhenPickled(WhenInstantiated):
    def setup(self):
        WhenInstantiated.setup(self)
        call_str = pickle.dumps(self.call, pickle.HIGHEST_PROTOCOL)
        self.call = pickle.loads(call_str)


########NEW FILE########
__FILENAME__ = test_call_list
from dingus import Call, CallList, DontCare


class WhenEmpty:
    def setup(self):
        self.calls = CallList()

    def should_be_false_in_boolean_context(self):
        assert not self.calls

    def should_not_have_one_element(self):
        assert not self.calls.one()


class WhenPopulatedWithACall:
    def setup(self):
        self.calls = CallList()
        self.calls.append(Call('test name',
                               'test args',
                               'test kwargs',
                               'test return_value'))

    def should_be_true_in_boolean_context(self):
        assert self.calls

    def should_have_exactly_one_call(self):
        assert self.calls.one()

    def should_not_return_call_when_querying_for_wrong_name(self):
        assert not self.calls('wrong name')

    def should_not_return_call_when_querying_for_wrong_args(self):
        assert not self.calls('test name', 'wrong args')

    def should_not_return_call_when_querying_for_wrong_kwargs(self):
        assert not self.calls('test name', wrong_key='wrong_value')


class WhenPopulatedWithACallWithKwargs:
    def setup(self):
        self.calls = CallList()
        self.calls.append(Call("name",
                               "args",
                               {'kwarg1' : "arg1", 'kwarg2' : "arg2"},
                               "return_value"))

    def should_return_call_when_querying_for_no_kwargs(self):
        assert self.calls('name').one()

    def should_return_call_when_dontcare(self):
        assert self.calls('name', kwarg1=DontCare, kwarg2='arg2')


class WhenPopulatedWithACallWithNoKwargs:
    def setup(self):
        self.calls = CallList()
        self.calls.append(Call("name", "args", {}, "return_value"))

    def should_not_return_call_when_given_kwarg_filters(self):
        assert not self.calls('name', kwarg1=0)


class WhenPopulatedWithTwoCalls:
    def setup(self):
        self.calls = CallList()
        for _ in range(2):
            self.calls.append(Call('name', (), {}, None))

    def should_not_have_one_element(self):
        assert not self.calls.one()


class WhenTwoCallsDifferByName:
    def setup(self):
        self.calls = CallList()
        self.calls.append(Call('name1', (), {}, None))
        self.calls.append(Call('name2', (), {}, None))

    def should_filter_on_name(self):
        assert self.calls('name1').one()


class WhenTwoCallsDifferByArgs:
    def setup(self):
        self.calls = CallList()
        self.calls.append(Call('name', ('arg1',), {}, None))
        self.calls.append(Call('name', ('arg2',), {}, None))

    def should_filter_on_args(self):
        assert self.calls('name', 'arg1').one()


class WhenCallsDifferInAllWays:
    def setup(self):
        self.calls = CallList()
        for name in ('name1', 'name2'):
            for args in (('arg1',), ('arg2',)):
                for kwargs in ({'kwarg1': 1}, {'kwarg2': 2}):
                    call = Call(name, args, kwargs, 'return value')
                    self.calls.append(call)
        self.call_count = len(self.calls)

    def should_filter_on_name(self):
        assert len(self.calls('name1')) == self.call_count / 2

    def should_filter_on_args(self):
        assert len(self.calls('name1', 'arg1')) == self.call_count / 4

    def should_filter_on_kwargs(self):
        assert len(self.calls('name1', kwarg1=1)) == self.call_count / 4


class WhenCallsHaveMultipleArguments:
    def setup(self):
        self.calls = CallList()
        for arg1 in (1, 2):
            for arg2 in (1, 2):
                self.calls.append(Call('name',
                                       (arg1, arg2),
                                       {},
                                       'return_value'))
        self.call_count = len(self.calls)

    def should_be_able_to_ignore_all_arguments(self):
        assert len(self.calls('name', DontCare, DontCare)) == self.call_count

    def should_be_able_to_ignore_first_argument(self):
        assert len(self.calls('name', 1, DontCare)) == self.call_count / 2

    def should_be_able_to_ignore_second_argument(self):
        assert len(self.calls('name', DontCare, 1)) == self.call_count / 2

    def should_be_able_to_specify_both_arguments(self):
        assert len(self.calls('name', 1, 1)) == self.call_count / 4


########NEW FILE########
__FILENAME__ = test_case_fixture
atomic_value = 'foo'

class ClassUnderTest:
    pass
class Collaborator:
    pass


########NEW FILE########
__FILENAME__ = test_dingus
import operator
import pickle
import copy

from nose.tools import assert_raises

from dingus import Dingus, patch


class WhenCreatingNewDingus:
    def setup(self):
        self.dingus = Dingus()

    def should_not_have_any_recorded_calls(self):
        assert not self.dingus.calls()

    def should_have_a_name(self):
        assert self.dingus.__name__ == 'dingus_%i' % id(self.dingus)


class WhenCreatingNewDingusWithAName:
    def setup(self):
        self.dingus = Dingus('something')

    def should_have_a_name(self):
        assert self.dingus.__name__ == 'something'

    def should_include_name_in_repr(self):
        assert repr(self.dingus) == '<Dingus something>'

    def should_include_attribute_name_in_childrens_repr(self):
        assert repr(self.dingus.child) == '<Dingus something.child>'

    def should_include_attribute_name_in_repr_of_children_from_calling(self):
        assert repr(self.dingus()) == '<Dingus something()>'

    def should_include_attribute_name_in_repr_of_children_from_indexing(self):
        assert repr(self.dingus()['5']) == '<Dingus something()[5]>'


class WhenCallingDingusAsFunction:
    def setup(self):
        self.dingus = Dingus()
        self.dingus('arg', kwarg=None)

    def should_record_call(self):
        assert self.dingus.calls()

    def should_have_exactly_one_call(self):
        assert self.dingus.calls().one()

    def should_have_once_method_as_alias_for_one_method(self):
        assert self.dingus.calls().once()

    def should_record_args(self):
        assert self.dingus.calls.one().args == ('arg',)

    def should_record_kwargs(self):
        assert self.dingus.calls.one().kwargs == {'kwarg': None}


class WhenCallingAttributeChild:
    def setup(self):
        self.parent = Dingus()
        self.child = self.parent.child
        self.child('arg', kwarg=None)

    def should_record_call_on_child(self):
        assert self.child.calls.one()

    def should_record_call_on_parent(self):
        assert self.parent.calls('child').one()

    def should_record_args(self):
        assert self.parent.calls('child').one().args == ('arg',)

    def should_record_kwargs(self):
        assert self.parent.calls('child').one().kwargs == {'kwarg': None}


class WhenCallingAttributeGrandchild:
    def setup(self):
        self.grandparent = Dingus()
        self.parent = self.grandparent.parent
        self.child = self.parent.child
        self.child('arg', kwarg=None)

    def should_not_record_call_on_grandparent(self):
        assert not self.grandparent.calls('parent.child')

    def should_record_call_on_parent(self):
        assert self.parent.calls('child').one()


class WhenCallingAttributesOfReturnedValues:
    def setup(self):
        self.grandparent = Dingus()
        self.parent = self.grandparent()
        self.child = self.parent.child
        self.child('arg', kwarg=None)

    def should_record_call_on_grandparent(self):
        assert self.grandparent.calls('()').one()

    def should_record_child_call_on_child(self):
        assert self.child.calls('()').one()

    def should_record_child_call_on_parent(self):
        assert self.parent.calls('child').one()

    def should_not_record_child_call_on_grandparent(self):
        assert not self.grandparent.calls('().child')


class WhenCallingItemChild:
    def should_record_call(self):
        parent = Dingus()
        parent['child']()
        assert parent.calls('[child]').one()


class WhenCallingListItemOfDingus:
    def setup(self):
        self.parent = Dingus()
        self.child = self.parent[0]
        self.child()

    def should_record_call_on_parent(self):
        assert self.parent.calls('[0]').one()

    def should_record_call_on_child(self):
        assert self.child.calls('()').one()


class WhenAccessingMagicAttributes:
    def should_raise_attribute_error_for_pyobjc_object(self):
        # PyObjC uses __pyobjc_object__ to get an ObjC object from a Python
        # object. Returning a Mock will cause a crash.
        assert_raises(AttributeError, lambda: Dingus().__pyobjc_object__)

    def should_raise_attribute_error_for_getnewargs(self):
        # Pickle uses __getnewargs__ to pickle a new-style object.
        assert_raises(AttributeError, lambda: Dingus().__getnewargs__)


INFIX_OPERATORS = ['add', 'and_', 'div', 'lshift', 'mod', 'mul', 'or_',
                   'pow', 'rshift', 'sub', 'xor']


class WhenApplyingInfixOperators:
    def __init__(self):
        self.operators = [getattr(operator, operator_name)
                          for operator_name in INFIX_OPERATORS]

    def assert_returns_new_dingus(self, op):
        left, right = Dingus.many(2)
        result = op(left, right)
        assert result is not left and result is not right

    def should_always_return_new_dingus(self):
        for operator in self.operators:
            yield self.assert_returns_new_dingus, operator

    def should_record_call(self):
        for operator in self.operators:
            left, right = Dingus.many(2)
            operator(left, right)
            operator_name_without_mangling = operator.__name__.replace('_', '')
            magic_method_name = '__%s__' % operator_name_without_mangling
            yield assert_call_was_logged, left, magic_method_name, right


class WhenApplyingAugmentedOperators:
    AUGMENTED_OPERATORS = ['i%s' % operator_name.replace('_', '')
                           for operator_name in INFIX_OPERATORS]

    def __init__(self):
        self.operators = [getattr(operator, operator_name)
                          for operator_name in self.AUGMENTED_OPERATORS]

    def assert_returns_same_dingus(self, op):
        left, right = Dingus.many(2)
        result = op(left, right)
        assert result is left

    def should_always_return_same_dingus(self):
        for operator in self.operators:
            yield self.assert_returns_same_dingus, operator

    def should_record_call(self):
        for operator in self.operators:
            left, right = Dingus.many(2)
            operator(left, right)
            magic_method_name = '__%s__' % operator.__name__
            yield assert_call_was_logged, left, magic_method_name, right


def assert_call_was_logged(dingus, method_name, *args):
    assert dingus.calls(method_name, *args).once()


class WhenComputingLength:
    def should_be_one(self):
        assert len(Dingus()) == 1


class WhenIterating:
    def should_return_one_dingus(self):
        assert len(list(Dingus())) == 1

    def should_return_dinguses(self):
        assert isinstance(list(Dingus())[0], Dingus)


class WhenAccessingReturnValueBeforeCalling:
    def setup(self):
        self.dingus = Dingus()

    def should_have_return_value_before_calling(self):
        assert self.dingus.return_value

    def should_return_same_return_value_that_existed_before_calling(self):
        original_return_value = self.dingus.return_value
        return_value = self.dingus()
        assert return_value is original_return_value

    def should_have_same_return_value_before_and_after_calling(self):
        original_return_value = self.dingus.return_value
        self.dingus()
        assert self.dingus.return_value is original_return_value


class WhenSettingReturnValue:
    def setup(self):
        self.dingus = Dingus()
        self.return_value = 5
        self.dingus.return_value = self.return_value

    def should_return_assigned_return_value(self):
        assert self.dingus() is self.return_value

    def should_have_same_return_value_after_calling(self):
        self.dingus()
        assert self.dingus.return_value is self.return_value


class WhenSettingAttributes:
    def setup(self):
        self.dingus = Dingus()
        self.attr = Dingus()
        self.dingus.attr = self.attr

    def should_remember_attr(self):
        assert self.dingus.attr is self.attr

    def should_not_return_attributes_as_items(self):
        assert self.dingus['attr'] is not self.attr

    def should_return_distinct_dinguses_for_different_attributes(self):
        assert self.dingus['attr'] is not self.dingus['attr2']


class WhenDeletingAttributes:
    def should_record_deletion(self):
        dingus = Dingus()
        del dingus.foo
        assert dingus.calls('__delattr__', 'foo').once()


class WhenAccessingItems:
    def should_log_access(self):
        dingus = Dingus()
        dingus['item']
        assert dingus.calls('__getitem__', 'item').one()

    def should_log_access_after_initial_item_read(self):
        dingus = Dingus()
        for _ in range(2):
            dingus['item']
        assert len(dingus.calls('__getitem__', 'item')) == 2

    def should_accept_tuples_as_item_name(self):
        dingus = Dingus()
        assert dingus[('x', 'y')]


class WhenSettingItems:
    def setup(self):
        self.dingus = Dingus()
        self.item = Dingus()
        self.dingus['item'] = self.item

    def should_remember_item(self):
        assert self.dingus['item'] is self.item

    def should_remember_item_even_if_its_value_is_None(self):
        self.dingus['item'] = None
        assert self.dingus['item'] is None

    def should_log_access(self):
        assert self.dingus.calls('__setitem__', 'item', self.item).one()

    def should_not_return_items_as_attributes(self):
        assert self.dingus.item is not self.item

    def should_return_distinct_dinguses_for_different_items(self):
        assert self.dingus['item'] is not self.dingus['item2']
    
    def should_accept_tuples_as_item_name(self):
        dingus = Dingus()
        dingus[('x', 'y')] = 'foo'
        assert dingus[('x', 'y')] == 'foo'


class WhenNothingIsSet:
    def setup(self):
        self.attribute_name = 'attr'
        self.dingus = Dingus()

    def should_be_able_to_access_attributes_that_dont_exist(self):
        assert isinstance(getattr(self.dingus, self.attribute_name), Dingus)

    def should_get_same_attribute_on_every_access(self):
        get_attr = lambda: getattr(self.dingus, self.attribute_name)
        assert get_attr() is get_attr()

    def should_be_able_to_acces_items_that_dont_exist(self):
        assert isinstance(self.dingus[self.attribute_name], Dingus)

    def should_get_same_item_on_every_access(self):
        get_item = lambda: self.dingus[self.attribute_name]
        assert get_item() is get_item()

    def should_have_attributes_that_have_not_been_set(self):
        assert hasattr(self.dingus, self.attribute_name)


class WhenSpecifyingAttributesViaKeywordArguments:
    def should_set_specified_attributes(self):
        attr = Dingus()
        object_with_attr = Dingus(attr=attr)
        assert object_with_attr.attr is attr


class WhenSpecifyingMethodReturnValuesViaKeywordArguments:
    def should_define_methods_returning_specified_values(self):
        result = Dingus()
        object_with_result = Dingus(method__returns=result)
        assert object_with_result.method() is result

    def should_record_calls_on_children(self):
        result = Dingus()
        object_with_result = Dingus(method__returns=result)
        object_with_result.method()
        assert object_with_result.calls('method')


class WhenCallingInitMethod:
    def should_record_call(self):
        dingus = Dingus()
        dingus.__init__()
        assert dingus.calls('__init__').one()


class WhenCreatingMultipleDinguses:
    def should_return_a_dingus_when_asked_for_one(self):
        assert len(Dingus.many(1)) == 1

    def should_return_two_dinguses_when_asked_for_two(self):
        assert len(Dingus.many(2)) == 2

    def should_return_dingus_instances_when_asked_for_multiple(self):
        assert all(isinstance(dingus, Dingus) for dingus in Dingus.many(2))

    def should_return_dinguses_in_tuple(self):
        assert isinstance(Dingus.many(2), tuple)

    def should_return_nothing_when_asked_for_zero_dinguses(self):
        assert not Dingus.many(0)

class WhenPicklingDingus:
    def setup(self):
        self.dingus = Dingus("something")

        # interact before pickling
        self.dingus('arg', kwarg=None)
        self.dingus.child.function_with_return_value.return_value = 'RETURN'
        self.dingus.child('arg', kwarg=None)
        
        self.dump_str = pickle.dumps(self.dingus, pickle.HIGHEST_PROTOCOL)
        del self.dingus        
        self.unpickled_dingus = pickle.loads(self.dump_str)

    def should_remember_name(self):
        assert self.unpickled_dingus.__name__ == 'something'
    
    def should_remember_called_functions(self):
        assert self.unpickled_dingus.calls('()').one().args == ('arg',) 

    def should_remember_child_calls(self):
        assert self.unpickled_dingus.calls("child").one().args == ('arg',)

    def should_remember_child_functions_return_value(self):
        assert self.unpickled_dingus.child.function_with_return_value() == 'RETURN'

    def should_have_replaced_init(self):
        assert self.unpickled_dingus.__init__ == self.unpickled_dingus._fake_init
        assert self.unpickled_dingus.child.__init__ == self.unpickled_dingus.child._fake_init


class WhenDingusIsSubclassed:
    def should_return_subclass_instances_instead_of_dinguses(self):
        class MyDingus(Dingus):
            pass

        dingus = MyDingus()
        assert isinstance(dingus.foo, MyDingus)


class WhenDingusIsDeepCopied:
    def should_retain_attributes(self):
        dingus = Dingus(foo=1)
        assert copy.deepcopy(dingus).foo == 1

    def should_be_independent_of_original_dingus(self):
        dingus = Dingus()
        copied_dingus = copy.deepcopy(dingus)
        copied_dingus.frob()
        assert copied_dingus.calls('frob').once()
        assert not dingus.calls('frob')

class WhenUsedAsAContextManager:
    def should_not_raise_an_exception(self):
        with Dingus():
            pass

    def should_be_able_to_return_something(self):
        open = Dingus()
        open().__enter__().read.return_value = "some data"
        with open('foo') as h:
            data_that_was_read = h.read()

        assert data_that_was_read == "some data"

    def _raiser(self, exc, dingus):
        def callable():
            with dingus:
                raise exc
        return callable

    def should_not_consume_exceptions_from_context(self):
        dingus = Dingus()
        assert_raises(KeyError, self._raiser(KeyError, dingus))

    def should_be_able_to_consume_an_arbitrary_exception(self):
        dingus = Dingus(consumed_context_manager_exceptions=(EOFError,))
        self._raiser(EOFError, dingus)()
        assert_raises(KeyError, self._raiser(KeyError, dingus))

    def should_be_able_to_consume_multiple_exceptions(self):
        dingus = Dingus(consumed_context_manager_exceptions=(
            NameError, NotImplementedError))
        self._raiser(NameError, dingus)()
        self._raiser(NotImplementedError, dingus)()
        assert_raises(KeyError, self._raiser(KeyError, dingus))

    def should_be_able_to_manually_consume_exceptions(self):
        dingus = Dingus(consumed_context_manager_exceptions=(EOFError,))
        self._raiser(EOFError, dingus)()
        assert_raises(KeyError, self._raiser(KeyError, dingus))


########NEW FILE########
__FILENAME__ = test_dingus_test_case
from nose.tools import assert_raises

from tests import test_case_fixture as module
from tests.test_case_fixture import ClassUnderTest, Collaborator

from dingus import DingusTestCase, Dingus


class WhenObjectIsExcludedFromTest:
    def setup(self):
        class TestCase(DingusTestCase(module.ClassUnderTest,
                                      exclude=['Collaborator'])):
            pass
        self.test_case_instance = TestCase()
        self.test_case_instance.setup()

    def should_not_replace_it_with_dingus(self):
        assert module.Collaborator is Collaborator

    def should_not_allow_strings_used_to_exclude(self):
        assert_raises(ValueError,
                      DingusTestCase,
                      module.ClassUnderTest,
                      exclude='a_string')

    def teardown(self):
        self.test_case_instance.teardown()


class WhenCallingSetupFunction:
    def setup(self):
        class TestCase(DingusTestCase(module.ClassUnderTest)):
            pass
        self.test_case_instance = TestCase()
        self.test_case_instance.setup()

    def teardown(self):
        self.test_case_instance.teardown()

    def should_not_replace_module_dunder_attributes(self):
        assert isinstance(module.__name__, str)
        assert isinstance(module.__file__, str)

    def should_replace_module_non_dunder_attributes(self):
        assert isinstance(module.atomic_value, Dingus)

    def should_replace_collaborating_classes(self):
        assert isinstance(module.Collaborator, Dingus)

    def should_leave_class_under_test_intact(self):
        assert module.ClassUnderTest is ClassUnderTest


class WhenCallingTeardownFunction:
    def setup(self):
        self.original_module_dict = module.__dict__.copy()
        class TestCase(DingusTestCase(module.ClassUnderTest)):
            pass
        test_case_object = TestCase()
        test_case_object.setup()
        test_case_object.teardown()

    def should_restore_module_attributes(self):
        assert module.atomic_value is 'foo'

    def should_leave_globals_as_they_were_before_dingusing(self):
        assert module.__dict__ == self.original_module_dict


########NEW FILE########
__FILENAME__ = test_exception_raiser
from nose.tools import assert_raises

from dingus import exception_raiser


class WhenCalled:
    def setup(self):
        exception = ValueError()
        self.raise_exception = exception_raiser(exception)

    def should_raise_provided_exception(self):
        assert_raises(ValueError, self.raise_exception)

    def should_take_args(self):
        assert_raises(ValueError, self.raise_exception, 1)

    def should_take_kwargs(self):
        assert_raises(ValueError, self.raise_exception, kwarg=1)


########NEW FILE########
__FILENAME__ = test_isolation
from __future__ import with_statement
import urllib2
import os

from dingus import Dingus, patch, isolate


class WhenPatchingObjects:
    @patch('urllib2.urlopen')
    def should_replace_object_with_dingus(self):
        assert isinstance(urllib2.urlopen, Dingus)

    def should_restore_object_after_patched_function_exits(self):
        @patch('urllib2.urlopen')
        def patch_urllib2():
            pass
        patch_urllib2()
        assert not isinstance(urllib2.urlopen, Dingus)

    def should_be_usable_as_context_manager(self):
        with patch('urllib2.urlopen'):
            assert isinstance(urllib2.urlopen, Dingus)
        assert not isinstance(urllib2.urlopen, Dingus)

    def should_be_able_to_provide_explicit_dingus(self):
        my_dingus = Dingus()
        with patch('urllib2.urlopen', my_dingus):
            assert urllib2.urlopen is my_dingus

    def should_name_dingus_after_patched_object(self):
        with patch('urllib2.urlopen'):
            assert str(urllib2.urlopen) == '<Dingus urllib2.urlopen>'

    def should_set_wrapped_on_patched_function(self):
        def urllib2():
            pass
        patch_urllib2 = patch('urllib2.urlopen')(urllib2)
        assert patch_urllib2.__wrapped__ == urllib2


class WhenIsolating:
    def should_isolate(self):
        @isolate("os.popen")
        def ensure_isolation():
            assert not isinstance(os.popen, Dingus)
            assert isinstance(os.walk, Dingus)

        assert not isinstance(os.walk, Dingus)
        ensure_isolation()
        assert not isinstance(os.walk, Dingus)


class WhenIsolatingSubmoduleObjects:
    def should_isolate(self):
        @isolate("os.path.isdir")
        def ensure_isolation():
            assert not isinstance(os.path.isdir, Dingus)
            assert isinstance(os.path.isfile, Dingus)

        assert not isinstance(os.path.isfile, Dingus)
        ensure_isolation()
        assert not isinstance(os.path.isfile, Dingus)

########NEW FILE########
__FILENAME__ = test_returner
from dingus import Dingus, returner


class WhenCreatingReturner:
    def should_return_given_value(self):
        return_value = Dingus()
        r = returner(return_value)
        assert r() == return_value


########NEW FILE########
