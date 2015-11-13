__FILENAME__ = http
"""
mock_django.http
~~~~~~~~~~~~~~~~

:copyright: (c) 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.utils.datastructures import MergeDict
from urllib import urlencode

__all__ = ('MockHttpRequest',)


class WsgiHttpRequest(HttpRequest):
    def __init__(self, *args, **kwargs):
        super(WsgiHttpRequest, self).__init__(*args, **kwargs)
        self.user = AnonymousUser()
        self.session = {}
        self.META = {}
        self.GET = {}
        self.POST = {}

    def _get_request(self):
        if not hasattr(self, '_request'):
            self._request = MergeDict(self.POST, self.GET)
        return self._request
    REQUEST = property(_get_request)

    def _get_raw_post_data(self):
        if not hasattr(self, '_raw_post_data'):
            self._raw_post_data = urlencode(self.POST)
        return self._raw_post_data

    def _set_raw_post_data(self, data):
        self._raw_post_data = data
        self.POST = {}
    raw_post_data = property(_get_raw_post_data, _set_raw_post_data)


def MockHttpRequest(path='/', method='GET', GET=None, POST=None, META=None, user=None):
    if GET is None:
        GET = {}
    if POST is None:
        POST = {}
    else:
        method = 'POST'
    if META is None:
        META = {
            'REMOTE_ADDR': '127.0.0.1',
            'SERVER_PORT': '8000',
            'HTTP_REFERER': '',
            'SERVER_NAME': 'testserver',
        }
    if user is not None:
        user = user

    request = WsgiHttpRequest()
    request.path = request.path_info = path
    request.method = method
    request.META = META
    request.GET = GET
    request.POST = POST
    request.user = user
    return request

########NEW FILE########
__FILENAME__ = managers
"""
mock_django.managers
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import mock
from .query import QuerySetMock
from .shared import SharedMock


__all__ = ('ManagerMock',)


def ManagerMock(manager, *return_value):
    """
    Set the results to two items:

    >>> objects = ManagerMock(Post.objects, 'queryset', 'result')
    >>> assert objects.filter() == objects.all()

    Force an exception:

    >>> objects = ManagerMock(Post.objects, Exception())

    See QuerySetMock for more about how this works.
    """

    def make_get_query_set(self, model):
        def _get(*a, **k):
            return QuerySetMock(model, *return_value)
        return _get

    actual_model = getattr(manager, 'model', None)
    if actual_model:
        model = mock.MagicMock(spec=actual_model())
    else:
        model = mock.MagicMock()

    m = SharedMock()
    m.model = model
    m.get_query_set = make_get_query_set(m, actual_model)
    m.get = m.get_query_set().get
    m.count = m.get_query_set().count
    m.exists = m.get_query_set().exists
    m.__iter__ = m.get_query_set().__iter__
    m.__getitem__ = m.get_query_set().__getitem__
    return m

########NEW FILE########
__FILENAME__ = models
"""
mock_django.models
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import mock

__all__ = ('ModelMock',)


# TODO: make foreignkey_id == foreignkey.id
class _ModelMock(mock.MagicMock):
    def _get_child_mock(self, **kwargs):
        name = kwargs.get('name', '')
        if name == 'pk':
            return self.id
        return super(_ModelMock, self)._get_child_mock(**kwargs)


def ModelMock(model):
    """
    >>> Post = ModelMock(Post)
    >>> assert post.pk == post.id
    """
    return _ModelMock(spec=model())

########NEW FILE########
__FILENAME__ = query
"""
mock_django.query
~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
import copy

import mock
from .shared import SharedMock

__all__ = ('QuerySetMock',)

QUERYSET_RETURNING_METHODS = ['filter', 'exclude', 'order_by', 'reverse',
                              'distinct', 'none', 'all', 'select_related',
                              'prefetch_related', 'defer', 'only', 'using',
                              'select_for_update']


def QuerySetMock(model, *return_value):
    """
    Get a SharedMock that returns self for most attributes and a new copy of
    itself for any method that ordinarily generates QuerySets.

    Set the results to two items:

    >>> class Post(object): pass
    >>> objects = QuerySetMock(Post, 'return', 'values')
    >>> assert list(objects.filter()) == list(objects.all())

    Force an exception:

    >>> objects = QuerySetMock(Post, Exception())

    Chain calls:
    >>> objects.all().filter(filter_arg='dummy')
    """

    def make_get(self, model):
        def _get(*a, **k):
            results = list(self)
            if len(results) > 1:
                raise model.MultipleObjectsReturned
            try:
                return results[0]
            except IndexError:
                raise model.DoesNotExist
        return _get

    def make_qs_returning_method(self):
        def _qs_returning_method(*a, **k):
            return copy.deepcopy(self)
        return _qs_returning_method

    def make_getitem(self):
        def _getitem(k):
            if isinstance(k, slice):
                self.__start = k.start
                self.__stop = k.stop
            else:
                return list(self)[k]
            return self
        return _getitem

    def make_iterator(self):
        def _iterator(*a, **k):
            if len(return_value) == 1 and isinstance(return_value[0], Exception):
                raise return_value[0]

            start = getattr(self, '__start', None)
            stop = getattr(self, '__stop', None)
            for x in return_value[start:stop]:
                yield x
        return _iterator

    actual_model = model
    if actual_model:
        model = mock.MagicMock(spec=actual_model())
    else:
        model = mock.MagicMock()

    m = SharedMock(reserved=['count', 'exists'] + QUERYSET_RETURNING_METHODS)
    m.__start = None
    m.__stop = None
    m.__iter__.side_effect = lambda: iter(m.iterator())
    m.__getitem__.side_effect = make_getitem(m)
    m.__nonzero__.side_effect = lambda: bool(return_value)
    m.__len__.side_effect = lambda: len(return_value)
    m.exists.side_effect = m.__nonzero__
    m.count.side_effect = m.__len__

    m.model = model
    m.get = make_get(m, actual_model)

    for method_name in QUERYSET_RETURNING_METHODS:
        setattr(m, method_name, make_qs_returning_method(m))

    # Note since this is a SharedMock, *all* auto-generated child
    # attributes will have the same side_effect ... might not make
    # sense for some like count().
    m.iterator.side_effect = make_iterator(m)
    return m

########NEW FILE########
__FILENAME__ = shared
import mock


class SharedMock(mock.MagicMock):

    """
    A MagicMock whose children are all itself.

    >>> m = SharedMock()
    >>> m is m.foo is m.bar is m.foo.bar.baz.qux
    True
    >>> m.foo.side_effect = ['hello from foo']
    >>> m.bar()
    'hello from foo'

    'Magic' methods are not shared.
    >>> m.__getitem__ is m.__len__
    False

    Neither are attributes you assign.
    >>> m.explicitly_assigned_attribute = 1
    >>> m.explicitly_assigned_attribute is m.foo
    False

    """

    def __init__(self, *args, **kwargs):
        reserved = kwargs.pop('reserved', [])

        # XXX: we cannot bind to self until after the mock is initialized
        super(SharedMock, self).__init__(*args, **kwargs)

        parent = mock.MagicMock()
        parent.child = self
        self.__parent = parent
        self.__reserved = reserved

    def _get_child_mock(self, **kwargs):
        name = kwargs.get('name', '')
        if (name[:2] == name[-2:] == '__') or name in self.__reserved:
            return super(SharedMock, self)._get_child_mock(**kwargs)
        return self

    def __getattr__(self, name):
        result = super(SharedMock, self).__getattr__(name)
        if result is self:
            result._mock_name = result._mock_new_name = name
        return result

    def assert_chain_calls(self, *calls):
        """
        Asserts that a chained method was called (parents in the chain do not
        matter, nor are they tracked).  Use with `mock.call`.

        >>> obj.filter(foo='bar').select_related('baz')
        >>> obj.assert_chain_calls(mock.call.filter(foo='bar'))
        >>> obj.assert_chain_calls(mock.call.select_related('baz'))
        >>> obj.assert_chain_calls(mock.call.reverse())
        *** AssertionError: [call.reverse()] not all found in call list, ...

        """

        all_calls = self.__parent.mock_calls[:]

        not_found = []
        for kall in calls:
            try:
                all_calls.remove(kall)
            except ValueError:
                not_found.append(kall)
        if not_found:
            if self.__parent.mock_calls:
                message = '%r not all found in call list, %d other(s) were:\n%r' % (not_found, len(self.__parent.mock_calls), self.__parent.mock_calls)
            else:
                message = 'no calls were found'

            raise AssertionError(message)

########NEW FILE########
__FILENAME__ = signals
"""
mock_django.signals
~~~~~~~~~~~~~~~~

:copyright: (c) 2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""
import contextlib
import mock


@contextlib.contextmanager
def mock_signal_receiver(signal, wraps=None, **kwargs):
    """
    Temporarily attaches a receiver to the provided ``signal`` within the scope
    of the context manager.

    The mocked receiver is returned as the ``as`` target of the ``with``
    statement.

    To have the mocked receiver wrap a callable, pass the callable as the
    ``wraps`` keyword argument. All other keyword arguments provided are passed
    through to the signal's ``connect`` method.

    >>> with mock_signal_receiver(post_save, sender=Model) as receiver:
    >>>     Model.objects.create()
    >>>     assert receiver.call_count = 1
    """
    if wraps is None:
        wraps = lambda *args, **kwargs: None

    receiver = mock.Mock(wraps=wraps)
    signal.connect(receiver, **kwargs)
    yield receiver
    signal.disconnect(receiver)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
from django.conf import settings
# collector import is required otherwise setuptools errors
from nose.core import run, collector


# Trick Django into thinking that we've configured a project, so importing
# anything that tries to access attributes of `django.conf.settings` will just
# return the default values, instead of crashing out.
if not settings.configured:
    settings.configure()


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = tests
from unittest2 import TestCase
from urllib import urlencode

from django.contrib.auth.models import AnonymousUser
from django.utils.datastructures import MergeDict

from mock import Mock

from mock_django.http import MockHttpRequest
from mock_django.http import WsgiHttpRequest


class WsgiHttpRequestTest(TestCase):
    def test_instance(self):
        wsgi_r = WsgiHttpRequest()

        self.assertTrue(isinstance(wsgi_r.user, AnonymousUser))
        self.assertEqual({}, wsgi_r.session)
        self.assertEqual({}, wsgi_r.META)
        self.assertEqual({}, wsgi_r.GET)
        self.assertEqual({}, wsgi_r.POST)

    def test__get_request(self):
        wsgi_r = WsgiHttpRequest()
        expected_items = MergeDict({}, {}).items()

        wsgi_r.GET = {}
        wsgi_r.POST = {}

        self.assertListEqual(sorted(expected_items),
                             sorted(wsgi_r._get_request().items()))

    def test_REQUEST_property(self):
        self.assertTrue(isinstance(WsgiHttpRequest.REQUEST, property))

    def test__get_raw_post_data(self):
        wsgi_r = WsgiHttpRequest()

        wsgi_r._get_raw_post_data()

        self.assertEqual(urlencode({}), wsgi_r._raw_post_data)

    def test__set_raw_post_data(self):
        wsgi_r = WsgiHttpRequest()

        wsgi_r._set_raw_post_data('')

        self.assertEqual({}, wsgi_r.POST)
        self.assertEqual(urlencode({}), wsgi_r._raw_post_data)

    def test_raw_post_data_property(self):
        self.assertTrue(isinstance(WsgiHttpRequest.raw_post_data, property))


class MockHttpRequestTest(TestCase):
    def test_call(self):
        result = MockHttpRequest()
        meta = {
            'REMOTE_ADDR': '127.0.0.1',
            'SERVER_PORT': '8000',
            'HTTP_REFERER': '',
            'SERVER_NAME': 'testserver',
        }

        self.assertTrue(isinstance(result, WsgiHttpRequest))
        self.assertEqual('/', result.path)
        self.assertEqual('GET', result.method)
        self.assertEqual(meta, result.META)
        self.assertEqual({}, result.GET)
        self.assertEqual({}, result.POST)
        self.assertTrue(isinstance(result.user, AnonymousUser))

    def test_call(self):
        class MockUser:
            pass

        result = MockHttpRequest(user=MockUser())

        self.assertTrue(isinstance(result.user, MockUser))

########NEW FILE########
__FILENAME__ = tests
import mock
from mock_django.managers import ManagerMock
from unittest2 import TestCase


class Model(object):
    class DoesNotExist(Exception):
        pass

    class MultipleObjectsReturned(Exception):
        pass


def make_manager():
    manager = mock.MagicMock(spec=(
        'all', 'filter', 'order_by',
    ))
    manager.model = Model
    return manager


class ManagerMockTestCase(TestCase):
    def test_iter(self):
        manager = make_manager()
        inst = ManagerMock(manager, 'foo')
        self.assertEquals(list(inst.all()), ['foo'])

    def test_iter_exception(self):
        manager = make_manager()
        inst = ManagerMock(manager, Exception())
        self.assertRaises(Exception, list, inst.all())

    def test_getitem(self):
        manager = make_manager()
        inst = ManagerMock(manager, 'foo')
        self.assertEquals(inst.all()[0], 'foo')

    def test_returns_self(self):
        manager = make_manager()
        inst = ManagerMock(manager, 'foo')
        self.assertEquals(inst.all(), inst)

    def test_get_on_singular_list(self):
        manager = make_manager()
        inst = ManagerMock(manager, 'foo')

        self.assertEquals(inst.get(), 'foo')

    def test_get_on_multiple_objects(self):
        manager = make_manager()
        inst = ManagerMock(manager, 'foo', 'bar')
        inst.model.MultipleObjectsReturned = Exception

        self.assertRaises(inst.model.MultipleObjectsReturned, inst.get)

    def test_get_raises_doesnotexist(self):
        manager = make_manager()
        inst = ManagerMock(manager)
        inst.model.DoesNotExist = Exception

        self.assertRaises(inst.model.DoesNotExist, inst.get)

    def test_call_tracking(self):
        # only works in >= mock 0.8
        manager = make_manager()
        inst = ManagerMock(manager, 'foo')

        inst.filter(foo='bar').select_related('baz')

        calls = inst.mock_calls

        self.assertGreater(len(calls), 1)
        inst.assert_chain_calls(mock.call.filter(foo='bar'))
        inst.assert_chain_calls(mock.call.select_related('baz'))

    def test_getitem_get(self):
        manager = make_manager()
        inst = ManagerMock(manager, 'foo')
        self.assertEquals(inst[0:1].get(), 'foo')

    def test_get_raises_doesnotexist_with_queryset(self):
        manager = make_manager()
        inst = ManagerMock(manager)
        queryset = inst.using('default.slave')[0:1]
        self.assertRaises(manager.model.DoesNotExist, queryset.get)

########NEW FILE########
__FILENAME__ = tests
from mock import MagicMock
from mock_django.models import ModelMock
from unittest2 import TestCase


class Model(object):
    id = '1'
    pk = '2'

    def foo(self):
        pass

    def bar(self):
        return 'bar'


class ModelMockTestCase(TestCase):
    def test_pk_alias(self):
        mock = ModelMock(Model)
        self.assertEquals(mock.id, mock.pk)

    def test_only_model_attrs_exist(self):
        """
        ModelMocks have only the members that the Model has.
        """
        mock = ModelMock(Model)
        self.assertRaises(AttributeError, lambda x: x.baz, mock)

    def test_model_attrs_are_mocks(self):
        """
        ModelMock members are Mocks, not the actual model members.
        """
        mock = ModelMock(Model)
        self.assertNotEquals(mock.bar(), 'bar')
        self.assertIsInstance(mock, MagicMock)

    def test_attrs_are_not_identical(self):
        """
        Each member of a ModelMock is unique.
        """
        mock = ModelMock(Model)
        self.assertIsNot(mock.foo, mock.bar)
        self.assertIsNot(mock.foo, mock.id)

########NEW FILE########
__FILENAME__ = tests
from mock_django.query import QuerySetMock
from unittest2 import TestCase


class TestException(Exception):
    pass


class TestModel(object):
    def foo(self):
        pass

    def bar(self):
        return 'bar'


class QuerySetTestCase(TestCase):
    def test_vals_returned(self):
        qs = QuerySetMock(None, 1, 2, 3)
        self.assertEquals(list(qs), [1, 2, 3])

    def test_qs_generator_inequality(self):
        """
        Each QuerySet-returning method's return value is unique.
        """
        qs = QuerySetMock(None, 1, 2, 3)
        self.assertNotEquals(qs.all(), qs.filter())
        self.assertNotEquals(qs.filter(), qs.order_by())

    def test_qs_yield_equality(self):
        """
        The generators may not be the same, but they do produce the same output.
        """
        qs = QuerySetMock(None, 1, 2, 3)
        self.assertEquals(list(qs.all()), list(qs.filter()))

    def test_qs_method_takes_arg(self):
        """
        QS-returning methods are impotent, but they do take args.
        """
        qs = QuerySetMock(None, 1, 2, 3)
        self.assertEquals(list(qs.order_by('something')), [1, 2, 3])

    def test_raises_exception_when_evaluated(self):
        """
        Exception raises when you actually use a QS-returning method.
        """
        qs = QuerySetMock(None, TestException())
        self.assertRaises(TestException, list, qs.all())

    def test_raises_exception_when_accessed(self):
        """
        Exceptions can raise on getitem, too.
        """
        qs = QuerySetMock(None, TestException())
        self.assertRaises(TestException, lambda x: x[0], qs)

    def test_chaining_calls_works(self):
        """
        Chained calls to QS-returning methods should return new QuerySetMocks.
        """
        qs = QuerySetMock(None, 1, 2, 3)
        qs.all().filter(filter_arg='dummy')
        qs.filter(filter_arg='dummy').order_by('-date')

    def test_chained_calls_return_new_querysetmocks(self):
        qs = QuerySetMock(None, 1, 2, 3)
        qs_all = qs.all()
        qs_filter = qs.filter()
        qs_all_filter = qs.filter().all()

        self.assertIsNot(qs_all, qs_filter)
        self.assertIsNot(qs_filter, qs_all_filter)

    # Test reserved methods
    def test_count_is_scalar(self):
        qs = QuerySetMock(None, 1, 2, 3)
        self.assertEquals(qs.count(), 3)

    def test_exists_is_boolean(self):
        qs = QuerySetMock(None)
        self.assertFalse(qs.exists())

        qs = QuerySetMock(None, 1, 2, 3)
        self.assertTrue(qs.exists())

    def test_objects_returned_do_not_change_type(self):
        """
        Not sure this is the behavior we want, but it's the behavior we have.
        """
        qs = QuerySetMock(TestModel, 1, 2, 3)
        self.assertNotIsInstance(qs[0], TestModel)

########NEW FILE########
__FILENAME__ = tests
from django.dispatch import Signal
from mock_django.signals import mock_signal_receiver
from unittest2 import TestCase


class MockSignalTestCase(TestCase):
    def test_mock_receiver(self):
        signal = Signal()
        with mock_signal_receiver(signal) as receiver:
            signal.send(sender=None)
            self.assertEqual(receiver.call_count, 1)

        sentinel = {}

        def side_effect(*args, **kwargs):
            return sentinel

        with mock_signal_receiver(signal, wraps=side_effect) as receiver:
            responses = signal.send(sender=None)
            self.assertEqual(receiver.call_count, 1)

            # Signals respond with a list of tuple pairs [(receiver, response), ...]
            self.assertIs(responses[0][1], sentinel)

########NEW FILE########
