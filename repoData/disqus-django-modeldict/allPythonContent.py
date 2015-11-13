__FILENAME__ = base
import time

from django.core.cache import cache

NoValue = object()


class CachedDict(object):
    def __init__(self, cache=cache, timeout=30):
        cls_name = type(self).__name__

        self._local_cache = None
        self._local_last_updated = None

        self._last_checked_for_remote_changes = None
        self.timeout = timeout

        self.remote_cache = cache
        self.remote_cache_key = cls_name
        self.remote_cache_last_updated_key = '%s.last_updated' % (cls_name,)

    def __getitem__(self, key):
        self._populate()

        try:
            return self._local_cache[key]
        except KeyError:
            value = self.get_default(key)

            if value is NoValue:
                raise

            return value

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

    def __len__(self):
        if self._local_cache is None:
            self._populate()

        return len(self._local_cache)

    def __contains__(self, key):
        self._populate()
        return key in self._local_cache

    def __iter__(self):
        self._populate()
        return iter(self._local_cache)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.model.__name__)

    def iteritems(self):
        self._populate()
        return self._local_cache.iteritems()

    def itervalues(self):
        self._populate()
        return self._local_cache.itervalues()

    def iterkeys(self):
        self._populate()
        return self._local_cache.iterkeys()

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        self._populate()
        return self._local_cache.items()

    def get(self, key, default=None):
        self._populate()
        return self._local_cache.get(key, default)

    def pop(self, key, default=NoValue):
        value = self.get(key, default)

        try:
            del self[key]
        except KeyError:
            pass

        return value

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value

    def get_default(self, key):
        return NoValue

    def local_cache_has_expired(self):
        """
        Returns ``True`` if the in-memory cache has expired.
        """
        if not self._last_checked_for_remote_changes:
            return True  # Never checked before

        recheck_at = self._last_checked_for_remote_changes + self.timeout
        return time.time() > recheck_at

    def local_cache_is_invalid(self):
        """
        Returns ``True`` if the local cache is invalid and needs to be
        refreshed with data from the remote cache.

        A return value of ``None`` signifies that no data was available.
        """
        # If the local_cache is empty, avoid hitting memcache entirely
        if self._local_cache is None:
            return True

        remote_last_updated = self.remote_cache.get(
            self.remote_cache_last_updated_key
        )

        if not remote_last_updated:
            # TODO: I don't like how we're overloading the return value here for
            # this method.  It would be better to have a separate method or
            # @property that is the remote last_updated value.
            return None  # Never been updated

        return int(remote_last_updated) > self._local_last_updated

    def get_cache_data(self):
        """
        Pulls data from the cache backend.
        """
        return self._get_cache_data()

    def clear_cache(self):
        """
        Clears the in-process cache.
        """
        self._local_cache = None
        self._local_last_updated = None
        self._last_checked_for_remote_changes = None

    def _populate(self, reset=False):
        """
        Ensures the cache is populated and still valid.

        The cache is checked when:

        - The local timeout has been reached
        - The local cache is not set

        The cache is invalid when:

        - The global cache has expired (via remote_cache_last_updated_key)
        """
        now = int(time.time())

        # If asked to reset, then simply set local cache to None
        if reset:
            self._local_cache = None
        # Otherwise, if the local cache has expired, we need to go check with
        # our remote last_updated value to see if the dict values have changed.
        elif self.local_cache_has_expired():

            local_cache_is_invalid = self.local_cache_is_invalid()

            # If local_cache_is_invalid  is None, that means that there was no
            # data present, so we assume we need to add the key to cache.
            if local_cache_is_invalid is None:
                self.remote_cache.add(self.remote_cache_last_updated_key, now)

            # Now, if the remote has changed OR it was None in the first place,
            # pull in the values from the remote cache and set it to the
            # local_cache
            if local_cache_is_invalid or local_cache_is_invalid is None:
                self._local_cache = self.remote_cache.get(self.remote_cache_key)

            # No matter what, we've updated from remote, so mark ourselves as
            # such so that we won't expire until the next timeout
            self._local_last_updated = now

        # Update from cache if local_cache is still empty
        if self._local_cache is None:
            self._update_cache_data()

        # No matter what happened, we last checked for remote changes just now
        self._last_checked_for_remote_changes = now

        return self._local_cache

    def _update_cache_data(self):
        self._local_cache = self.get_cache_data()

        now = int(time.time())
        self._local_last_updated = now
        self._last_checked_for_remote_changes = now

        # We only set remote_cache_last_updated_key when we know the cache is
        # current because setting this will force all clients to invalidate
        # their cached data if it's newer
        self.remote_cache.set(self.remote_cache_key, self._local_cache)
        self.remote_cache.set(
            self.remote_cache_last_updated_key,
            self._last_checked_for_remote_changes
        )

    def _get_cache_data(self):
        raise NotImplementedError

    def _cleanup(self, *args, **kwargs):
        # We set _last_updated to a false value to ensure we hit the
        # last_updated cache on the next request
        self._last_checked_for_remote_changes = None

########NEW FILE########
__FILENAME__ = models
from django.db.models.signals import post_save, post_delete
from django.core.signals import request_finished

from modeldict.base import CachedDict, NoValue


try:
    from celery.signals import task_postrun
except ImportError:  # celery must not be installed
    has_celery = False
else:
    has_celery = True


class ModelDict(CachedDict):
    """
    Dictionary-style access to a model. Populates a cache and a local in-memory
    store to avoid multiple hits to the database.

    Specifying ``instances=True`` will cause the cache to store instances rather
    than simple values.

    If ``auto_create=True`` accessing modeldict[key] when key does not exist will
    attempt to create it in the database.

    Functions in two different ways, depending on the constructor:

        # Given ``Model`` that has a column named ``foo`` where the value is "bar":

        mydict = ModelDict(Model, value='foo')
        mydict['test']
        >>> 'bar' #doctest: +SKIP

    If you want to use another key besides ``pk``, you may specify that in the
    constructor. However, this will be used as part of the cache key, so it's recommended
    to access it in the same way throughout your code.

        mydict = ModelDict(Model, key='foo', value='id')
        mydict['bar']
        >>> 'test' #doctest: +SKIP

    """
    def __init__(self, model, key='pk', value=None, instances=False, auto_create=False, *args, **kwargs):
        assert value is not None

        super(ModelDict, self).__init__(*args, **kwargs)

        cls_name = type(self).__name__
        model_name = model.__name__

        self.key = key
        self.value = value

        self.model = model
        self.instances = instances
        self.auto_create = auto_create

        self.remote_cache_key = '%s:%s:%s' % (cls_name, model_name, self.key)
        self.remote_cache_last_updated_key = '%s.last_updated:%s:%s' % (cls_name, model_name, self.key)

        request_finished.connect(self._cleanup)
        post_save.connect(self._post_save, sender=model)
        post_delete.connect(self._post_delete, sender=model)

        if has_celery:
            task_postrun.connect(self._cleanup)

    def __setitem__(self, key, value):
        if isinstance(value, self.model):
            value = getattr(value, self.value)

        manager = self.model._default_manager
        instance, created = manager.get_or_create(
            defaults={self.value: value},
            **{self.key: key}
        )

        # Ensure we're updating the value in the database if it changes
        if getattr(instance, self.value) != value:
            setattr(instance, self.value, value)
            manager.filter(**{self.key: key}).update(**{self.value: value})
            self._post_save(sender=self.model, instance=instance, created=False)

    def __delitem__(self, key):
        self.model._default_manager.filter(**{self.key: key}).delete()
        # self._populate(reset=True)

    def setdefault(self, key, value):
        if isinstance(value, self.model):
            value = getattr(value, self.value)

        instance, created = self.model._default_manager.get_or_create(
            defaults={self.value: value},
            **{self.key: key}
        )

    def get_default(self, key):
        if not self.auto_create:
            return NoValue
        result = self.model.objects.get_or_create(**{self.key: key})[0]
        if self.instances:
            return result
        return getattr(result, self.value)

    def _get_cache_data(self):
        qs = self.model._default_manager
        if self.instances:
            return dict((getattr(i, self.key), i) for i in qs.all())
        return dict(qs.values_list(self.key, self.value))

    # Signals

    def _post_save(self, sender, instance, created, **kwargs):
        self._populate(reset=True)

    def _post_delete(self, sender, instance, **kwargs):
        self._populate(reset=True)

########NEW FILE########
__FILENAME__ = redis
from django.core.signals import request_finished

from modeldict.base import CachedDict


class RedisDict(CachedDict):
    """
    Dictionary-style access to a redis hash table. Populates a cache and a local
    in-memory to avoid multiple hits to the database.

    Functions just like you'd expect it::

        mydict = RedisDict('my_redis_key', Redis())
        mydict['test']
        >>> 'bar' #doctest: +SKIP

    """
    def __init__(self, keyspace, connection, *args, **kwargs):
        super(CachedDict, self).__init__(*args, **kwargs)

        self.keyspace = keyspace
        self.conn = connection

        self.remote_cache_key = 'RedisDict:%s' % (keyspace,)
        self.remote_cache_last_updated_key = 'RedisDict.last_updated:%s' % (keyspace,)

        request_finished.connect(self._cleanup)

    def __setitem__(self, key, value):
        self.conn.hset(self.keyspace, key, value)
        if value != self._local_cache.get(key):
            self._local_cache[key] = value
        self._populate(reset=True)

    def __delitem__(self, key):
        self.conn.hdel(self.keyspace, key)
        self._local_cache.pop(key)
        self._populate(reset=True)

    def _get_cache_data(self):
        return self.conn.hgetall(self.keyspace)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
from __future__ import absolute_import

import sys
from os.path import dirname, abspath

sys.path.insert(0, dirname(abspath(__file__)))

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',

            'modeldict',
            'tests.modeldict',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
    )

from django_nose import NoseTestSuiteRunner


def runtests(*test_args, **kwargs):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['tests']

    kwargs.setdefault('interactive', False)

    test_runner = NoseTestSuiteRunner(**kwargs)

    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--verbosity', dest='verbosity', action='store', default=1, type=int)
    parser.add_options(NoseTestSuiteRunner.options)
    (options, args) = parser.parse_args()

    runtests(*args, **options.__dict__)

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import

from django.db import models


class ModelDictModel(models.Model):
    key = models.CharField(max_length=32, unique=True)
    value = models.CharField(max_length=32, default='')

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

import mock
import time

from django.core.cache import cache
from django.core.signals import request_finished
from django.test import TestCase, TransactionTestCase

from modeldict import ModelDict
from modeldict.base import CachedDict
from .models import ModelDictModel


class ModelDictTest(TransactionTestCase):
    # XXX: uses transaction test due to request_finished signal causing a rollback
    urls = 'tests.modeldict.urls'

    def setUp(self):
        cache.clear()

    def assertHasReceiver(self, signal, function):
        for ident, reciever in signal.receivers:
            if reciever() is function:
                return True
        return False

    def test_api(self):
        base_count = ModelDictModel.objects.count()

        mydict = ModelDict(ModelDictModel, key='key', value='value')
        mydict['foo'] = 'bar'
        self.assertEquals(mydict['foo'], 'bar')
        self.assertEquals(ModelDictModel.objects.values_list('value', flat=True).get(key='foo'), 'bar')
        self.assertEquals(ModelDictModel.objects.count(), base_count + 1)
        mydict['foo'] = 'bar2'
        self.assertEquals(mydict['foo'], 'bar2')
        self.assertEquals(ModelDictModel.objects.values_list('value', flat=True).get(key='foo'), 'bar2')
        self.assertEquals(ModelDictModel.objects.count(), base_count + 1)
        mydict['foo2'] = 'bar'
        self.assertEquals(mydict['foo2'], 'bar')
        self.assertEquals(ModelDictModel.objects.values_list('value', flat=True).get(key='foo2'), 'bar')
        self.assertEquals(ModelDictModel.objects.count(), base_count + 2)
        del mydict['foo2']
        self.assertRaises(KeyError, mydict.__getitem__, 'foo2')
        self.assertFalse(ModelDictModel.objects.filter(key='foo2').exists())
        self.assertEquals(ModelDictModel.objects.count(), base_count + 1)

        ModelDictModel.objects.create(key='foo3', value='hello')

        self.assertEquals(mydict['foo3'], 'hello')
        self.assertTrue(ModelDictModel.objects.filter(key='foo3').exists(), True)
        self.assertEquals(ModelDictModel.objects.count(), base_count + 2)

        request_finished.send(sender=self)

        self.assertEquals(mydict._last_checked_for_remote_changes, None)

        # These should still error because even though the cache repopulates (local cache)
        # the remote cache pool does not
        # self.assertRaises(KeyError, mydict.__getitem__, 'foo3')
        # self.assertTrue(ModelDictModel.objects.filter(key='foo3').exists())
        # self.assertEquals(ModelDictModel.objects.count(), base_count + 2)

        self.assertEquals(mydict['foo'], 'bar2')
        self.assertEquals(ModelDictModel.objects.values_list('value', flat=True).get(key='foo'), 'bar2')
        self.assertEquals(ModelDictModel.objects.count(), base_count + 2)

        self.assertEquals(mydict.pop('foo'), 'bar2')
        self.assertEquals(mydict.pop('foo', None), None)
        self.assertFalse(ModelDictModel.objects.filter(key='foo').exists())
        self.assertEquals(ModelDictModel.objects.count(), base_count + 1)

    def test_modeldict_instances(self):
        base_count = ModelDictModel.objects.count()

        mydict = ModelDict(ModelDictModel, key='key', value='value', instances=True)
        mydict['foo'] = ModelDictModel(key='foo', value='bar')
        self.assertTrue(isinstance(mydict['foo'], ModelDictModel))
        self.assertTrue(mydict['foo'].pk)
        self.assertEquals(mydict['foo'].value, 'bar')
        self.assertEquals(ModelDictModel.objects.values_list('value', flat=True).get(key='foo'), 'bar')
        self.assertEquals(ModelDictModel.objects.count(), base_count + 1)
        old_pk = mydict['foo'].pk
        mydict['foo'] = ModelDictModel(key='foo', value='bar2')
        self.assertTrue(isinstance(mydict['foo'], ModelDictModel))
        self.assertEquals(mydict['foo'].pk, old_pk)
        self.assertEquals(mydict['foo'].value, 'bar2')
        self.assertEquals(ModelDictModel.objects.values_list('value', flat=True).get(key='foo'), 'bar2')
        self.assertEquals(ModelDictModel.objects.count(), base_count + 1)

        # test deletion
        mydict['foo'].delete()
        self.assertTrue('foo' not in mydict)

    def test_modeldict_expirey(self):
        base_count = ModelDictModel.objects.count()

        mydict = ModelDict(ModelDictModel, key='key', value='value')

        self.assertEquals(mydict._local_cache, None)

        mydict['test_modeldict_expirey'] = 'hello'

        self.assertEquals(len(mydict._local_cache), base_count + 1)
        self.assertEquals(mydict['test_modeldict_expirey'], 'hello')

        self.client.get('/')

        self.assertEquals(mydict._last_checked_for_remote_changes, None)
        self.assertEquals(mydict['test_modeldict_expirey'], 'hello')
        self.assertEquals(len(mydict._local_cache), base_count + 1)

        request_finished.send(sender=self)

        self.assertEquals(mydict._last_checked_for_remote_changes, None)
        self.assertEquals(mydict['test_modeldict_expirey'], 'hello')
        self.assertEquals(len(mydict._local_cache), base_count + 1)

    def test_modeldict_no_auto_create(self):
        # without auto_create
        mydict = ModelDict(ModelDictModel, key='key', value='value')
        self.assertRaises(KeyError, lambda x: x['hello'], mydict)
        self.assertEquals(ModelDictModel.objects.count(), 0)

    def test_modeldict_auto_create_no_value(self):
        # with auto_create and no value
        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        repr(mydict['hello'])
        self.assertEquals(ModelDictModel.objects.count(), 1)
        self.assertEquals(ModelDictModel.objects.get(key='hello').value, '')

    def test_modeldict_auto_create(self):
        # with auto_create and value
        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        mydict['hello'] = 'foo'
        self.assertEquals(ModelDictModel.objects.count(), 1)
        self.assertEquals(ModelDictModel.objects.get(key='hello').value, 'foo')

    def test_save_behavior(self):
        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        mydict['hello'] = 'foo'
        for n in xrange(10):
            mydict[str(n)] = 'foo'
        self.assertEquals(len(mydict), 11)
        self.assertEquals(ModelDictModel.objects.count(), 11)

        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        m = ModelDictModel.objects.get(key='hello')
        m.value = 'bar'
        m.save()

        self.assertEquals(ModelDictModel.objects.count(), 11)
        self.assertEquals(len(mydict), 11)
        self.assertEquals(mydict['hello'], 'bar')

        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        m = ModelDictModel.objects.get(key='hello')
        m.value = 'bar2'
        m.save()

        self.assertEquals(ModelDictModel.objects.count(), 11)
        self.assertEquals(len(mydict), 11)
        self.assertEquals(mydict['hello'], 'bar2')

    def test_django_signals_are_connected(self):
        from django.db.models.signals import post_save, post_delete
        from django.core.signals import request_finished

        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        self.assertHasReceiver(post_save, mydict._post_save)
        self.assertHasReceiver(post_delete, mydict._post_delete)
        self.assertHasReceiver(request_finished, mydict._cleanup)

    def test_celery_signals_are_connected(self):
        from celery.signals import task_postrun

        mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True)
        self.assertHasReceiver(task_postrun, mydict._cleanup)


class CacheIntegrationTest(TestCase):
    def setUp(self):
        self.cache = mock.Mock()
        self.cache.get.return_value = {}
        self.mydict = ModelDict(ModelDictModel, key='key', value='value', auto_create=True, cache=self.cache)

    def test_switch_creation(self):
        self.mydict['hello'] = 'foo'
        self.assertEquals(self.cache.get.call_count, 0)
        self.assertEquals(self.cache.set.call_count, 2)
        self.cache.set.assert_any_call(self.mydict.remote_cache_key, {u'hello': u'foo'})
        self.cache.set.assert_any_call(self.mydict.remote_cache_last_updated_key, self.mydict._last_checked_for_remote_changes)

    def test_switch_change(self):
        self.mydict['hello'] = 'foo'
        self.cache.reset_mock()
        self.mydict['hello'] = 'bar'
        self.assertEquals(self.cache.get.call_count, 0)
        self.assertEquals(self.cache.set.call_count, 2)
        self.cache.set.assert_any_call(self.mydict.remote_cache_key, {u'hello': u'bar'})
        self.cache.set.assert_any_call(self.mydict.remote_cache_last_updated_key, self.mydict._last_checked_for_remote_changes)

    def test_switch_delete(self):
        self.mydict['hello'] = 'foo'
        self.cache.reset_mock()
        del self.mydict['hello']
        self.assertEquals(self.cache.get.call_count, 0)
        self.assertEquals(self.cache.set.call_count, 2)
        self.cache.set.assert_any_call(self.mydict.remote_cache_key, {})
        self.cache.set.assert_any_call(self.mydict.remote_cache_last_updated_key, self.mydict._last_checked_for_remote_changes)

    def test_switch_access(self):
        self.mydict['hello'] = 'foo'
        self.cache.reset_mock()
        foo = self.mydict['hello']
        foo = self.mydict['hello']
        foo = self.mydict['hello']
        foo = self.mydict['hello']
        self.assertEquals(foo, 'foo')
        self.assertEquals(self.cache.get.call_count, 0)
        self.assertEquals(self.cache.set.call_count, 0)

    def test_switch_access_without_local_cache(self):
        self.mydict['hello'] = 'foo'
        self.mydict._local_cache = None
        self.mydict._last_checked_for_remote_changes = None
        self.cache.reset_mock()
        foo = self.mydict['hello']
        self.assertEquals(foo, 'foo')
        # "1" here signifies that we didn't ask the remote cache for its last
        # updated value
        self.assertEquals(self.cache.get.call_count, 1)
        self.assertEquals(self.cache.set.call_count, 0)
        self.cache.get.assert_any_call(self.mydict.remote_cache_key)
        self.cache.reset_mock()
        foo = self.mydict['hello']
        foo = self.mydict['hello']
        foo = self.mydict['hello']
        self.assertEquals(self.cache.get.call_count, 0)
        self.assertEquals(self.cache.set.call_count, 0)

    def test_switch_access_with_expired_local_cache(self):
        self.mydict['hello'] = 'foo'
        self.mydict._last_checked_for_remote_changes = None
        self.cache.reset_mock()
        foo = self.mydict['hello']
        self.assertEquals(foo, 'foo')
        self.assertEquals(self.cache.get.call_count, 2)
        self.assertEquals(self.cache.set.call_count, 0)
        self.cache.get.assert_any_call(self.mydict.remote_cache_last_updated_key)
        self.cache.reset_mock()
        foo = self.mydict['hello']
        foo = self.mydict['hello']
        self.assertEquals(self.cache.get.call_count, 0)
        self.assertEquals(self.cache.set.call_count, 0)

    def test_does_not_pull_down_all_data(self):
        self.mydict['hello'] = 'foo'
        self.cache.get.return_value = self.mydict._local_last_updated - 100
        self.cache.reset_mock()

        self.mydict._cleanup()

        self.assertEquals(self.mydict['hello'], 'foo')
        self.cache.get.assert_called_once_with(
            self.mydict.remote_cache_last_updated_key
        )


class CachedDictTest(TestCase):
    def setUp(self):
        self.cache = mock.Mock()
        self.mydict = CachedDict(timeout=100, cache=self.cache)

    @mock.patch('modeldict.base.CachedDict._update_cache_data')
    @mock.patch('modeldict.base.CachedDict.local_cache_has_expired', mock.Mock(return_value=True))
    @mock.patch('modeldict.base.CachedDict.local_cache_is_invalid', mock.Mock(return_value=False))
    def test_expired_does_update_data(self, _update_cache_data):
        self.mydict._local_cache = {}
        self.mydict._last_checked_for_remote_changes = time.time()
        self.mydict._populate()

        self.assertFalse(_update_cache_data.called)

    @mock.patch('modeldict.base.CachedDict._update_cache_data')
    @mock.patch('modeldict.base.CachedDict.local_cache_has_expired', mock.Mock(return_value=False))
    @mock.patch('modeldict.base.CachedDict.local_cache_is_invalid', mock.Mock(return_value=True))
    def test_reset_does_expire(self, _update_cache_data):
        self.mydict._local_cache = {}
        self.mydict._last_checked_for_remote_changes = time.time()
        self.mydict._populate(reset=True)

        _update_cache_data.assert_called_once_with()

    @mock.patch('modeldict.base.CachedDict._update_cache_data')
    @mock.patch('modeldict.base.CachedDict.local_cache_has_expired', mock.Mock(return_value=False))
    @mock.patch('modeldict.base.CachedDict.local_cache_is_invalid', mock.Mock(return_value=True))
    def test_does_not_expire_by_default(self, _update_cache_data):
        self.mydict._local_cache = {}
        self.mydict._last_checked_for_remote_changes = time.time()
        self.mydict._populate()

        self.assertFalse(_update_cache_data.called)

    def test_is_expired_missing_last_checked_for_remote_changes(self):
        self.mydict._last_checked_for_remote_changes = None
        self.assertTrue(self.mydict.local_cache_has_expired())
        self.assertFalse(self.cache.get.called)

    def test_is_expired_last_updated_beyond_timeout(self):
        self.mydict._local_last_updated = time.time() - 101
        self.assertTrue(self.mydict.local_cache_has_expired())

    def test_is_expired_within_bounds(self):
        self.mydict._last_checked_for_remote_changes = time.time()

    def test_is_not_expired_if_remote_cache_is_old(self):
        # set it to an expired time
        self.mydict._local_cache = dict(a=1)
        self.mydict._local_last_updated = time.time() - 101
        self.cache.get.return_value = self.mydict._local_last_updated

        result = self.mydict.local_cache_is_invalid()

        self.cache.get.assert_called_once_with(self.mydict.remote_cache_last_updated_key)
        self.assertFalse(result)

    def test_is_expired_if_remote_cache_is_new(self):
        # set it to an expired time, but with a local cache
        self.mydict._local_cache = dict(a=1)
        self.mydict._last_checked_for_remote_changes = time.time() - 101
        self.cache.get.return_value = time.time()

        result = self.mydict.local_cache_is_invalid()

        self.cache.get.assert_called_once_with(
            self.mydict.remote_cache_last_updated_key
        )
        self.assertEquals(result, True)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

def dummy_view(request):
    from django.http import HttpResponse
    return HttpResponse()

urlpatterns = patterns('',
    url(r'^$', dummy_view, name='modeldict-home'),
)
########NEW FILE########
