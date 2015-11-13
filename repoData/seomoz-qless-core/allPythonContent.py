__FILENAME__ = qless
'''Some helper functions for running tests. This should not be confused with
the python qless bindings.'''

try:
    import simplejson as json
except ImportError:
    import json
    json.JSONDecodeError = ValueError


class QlessRecorder(object):
    '''A context-manager to capture anything that goes back and forth'''
    __name__ = 'QlessRecorder'

    def __init__(self, client):
        self._client = client
        self._pubsub = self._client.pubsub()
        with open('qless.lua') as fin:
            self._lua = self._client.register_script(fin.read())
        # Record any log messages that we've seen
        self.log = []

    def raw(self, *args, **kwargs):
        '''Submit raw data to the lua script, untransformed'''
        return self._lua(*args, **kwargs)

    def __call__(self, *args):
        '''Invoke the lua script with no keys, and some simple transforms'''
        transformed = []
        for arg in args:
            if isinstance(arg, dict) or isinstance(arg, list):
                transformed.append(json.dumps(arg))
            else:
                transformed.append(arg)
        result = self._lua([], transformed)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
        except TypeError:
            return result

    def flush(self):
        '''Flush the database'''
        self._client.flushdb()

    def __enter__(self):
        self.log = []
        self._pubsub.psubscribe('*')
        self._pubsub.listen().next()
        return self

    def __exit__(self, typ, val, traceback):
        # Send the kill signal to our pubsub listener
        self._pubsub.punsubscribe('*')
        for message in self._pubsub.listen():
            typ = message.pop('type')
            # Only get subscribe messages
            if typ == 'pmessage':
                # And pop the pattern attribute
                message.pop('pattern')
                self.log.append(message)
            elif typ == 'punsubscribe':
                break

########NEW FILE########
__FILENAME__ = common
'''Base class for all of our tests'''

import os
import re
import redis
import qless
import unittest


class TestQless(unittest.TestCase):
    '''Base class for all of our tests'''
    @classmethod
    def setUpClass(cls):
        url = os.environ.get('REDIS_URL', 'redis://localhost:6379/')
        cls.lua = qless.QlessRecorder(redis.Redis.from_url(url))

    def tearDown(self):
        self.lua.flush()

    def assertMalformed(self, function, examples):
        '''Ensure that all the example inputs to the function are malformed.'''
        for args in examples:
            try:
                # The reason that we're not using assertRaises is that the error
                # message that is produces is unnecessarily vague, and offers no
                # indication of what arguments actually failed to raise the
                # exception
                function(*args)
                self.assertTrue(False, 'Exception not raised for %s(%s)' % (
                    function.__name__, repr(args)))
            except redis.ResponseError:
                self.assertTrue(True)

    def assertRaisesRegexp(self, typ, regex, func, *args, **kwargs):
        '''Python 2.6 doesn't include this method'''
        try:
            func(*args, **kwargs)
            self.assertFalse(True, 'No exception raised')
        except typ as exc:
            self.assertTrue(re.search(regex, str(exc)),
                '%s does not match %s' % (str(exc), regex))
        except Exception as exc:
            self.assertFalse(True,
                '%s raised, expected %s' % (type(exc).__name__, typ.__name__))

########NEW FILE########
__FILENAME__ = test_asserts
'''Test our own built-in asserts'''

from common import TestQless


class TestAsserts(TestQless):
    '''Ensure our own assert methods raise the exceptions they're supposed to'''
    def test_assertRaisesRegexp(self):
        '''Make sure that our home-brew assertRaisesRegexp works'''
        def func():
            '''Raises wrong error'''
            self.assertRaisesRegexp(NotImplementedError, 'base 10', int, 'foo')
        self.assertRaises(AssertionError, func)

        def func():
            '''Doesn't match regex'''
            self.assertRaisesRegexp(ValueError, 'sklfjlskjflksjfs', int, 'foo')
        self.assertRaises(AssertionError, func)
        self.assertRaises(ValueError, int, 'foo')

        def func():
            '''Doesn't throw any error'''
            self.assertRaisesRegexp(ValueError, 'base 10', int, 5)
        self.assertRaises(AssertionError, func)

########NEW FILE########
__FILENAME__ = test_config
'''Tests for our configuration'''

from common import TestQless


class TestConfig(TestQless):
    '''Test our config scripts'''
    def test_all(self):
        '''Should be able to access all configurations'''
        self.assertEqual(self.lua('config.get', 0), {
            'application': 'qless',
            'grace-period': 10,
            'heartbeat': 60,
            'histogram-history': 7,
            'jobs-history': 604800,
            'jobs-history-count': 50000,
            'stats-history': 30})

    def test_get(self):
        '''Should be able to get each key individually'''
        for key, value in self.lua('config.get', 0).items():
            self.assertEqual(self.lua('config.get', 0, key), value)

    def test_set_get(self):
        '''If we update a configuration setting, we can get it back'''
        self.lua('config.set', 0, 'foo', 'bar')
        self.assertEqual(self.lua('config.get', 0, 'foo'), 'bar')

    def test_unset_default(self):
        '''If we override a default and then unset it, it should return'''
        default = self.lua('config.get', 0, 'heartbeat')
        self.lua('config.set', 0, 'heartbeat', 100)
        self.assertEqual(self.lua('config.get', 0, 'heartbeat'), 100)
        self.lua('config.unset', 0, 'heartbeat')
        self.assertEqual(self.lua('config.get', 0, 'heartbeat'), default)

    def test_unset(self):
        '''If we set and then unset a setting, it should return to None'''
        self.assertEqual(self.lua('config.get', 0, 'foo'), None)
        self.lua('config.set', 0, 'foo', 5)
        self.assertEqual(self.lua('config.get', 0, 'foo'), 5)
        self.lua('config.unset', 0, 'foo')
        self.assertEqual(self.lua('config.get', 0, 'foo'), None)

########NEW FILE########
__FILENAME__ = test_dependencies
'''Test out dependency-related code'''

import redis
from common import TestQless


class TestDependencies(TestQless):
    '''Dependency-related tests'''
    def test_unlock(self):
        '''Dependencies unlock their dependents upon completion'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        # Only 'a' should show up
        self.assertEqual(len(self.lua('pop', 1, 'queue', 'worker', 10)), 1)
        self.lua('complete', 2, 'a', 'worker', 'queue', {})
        # And now 'b' should be available
        self.assertEqual(
            self.lua('pop', 3, 'queue', 'worker', 10)[0]['jid'], 'b')

    def test_unlock_with_delay(self):
        '''Dependencies schedule their dependents upon completion'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 1000, 'depends', ['a'])
        # Only 'a' should show up
        self.assertEqual(len(self.lua('pop', 1, 'queue', 'worker', 10)), 1)
        self.lua('complete', 2, 'a', 'worker', 'queue', {})
        # And now 'b' should be scheduled
        self.assertEqual(self.lua('get', 3, 'b')['state'], 'scheduled')
        # After we wait for the delay, it should be available
        self.assertEqual(len(self.lua('peek', 1000, 'queue', 10)), 1)
        self.assertEqual(self.lua('get', 1001, 'b')['state'], 'waiting')

    def test_unlock_with_delay_satisfied(self):
        '''If deps are satisfied, should be scheduled'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 10, 'depends', ['b'])
        self.assertEqual(self.lua('get', 1, 'a')['state'], 'scheduled')

    def test_complete_depends_with_delay(self):
        '''We should be able to complete a job and specify delay and depends'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.assertEqual(len(self.lua('pop', 2, 'queue', 'worker', 1)), 1)
        self.lua('complete', 3, 'a', 'worker', 'queue', {}, 'next', 'foo',
            'depends', ['b'], 'delay', 10)
        # Now its state should be 'depends'
        self.assertEqual(self.lua('get', 4, 'a')['state'], 'depends')
        # Now pop and complete the job it depends on
        self.lua('pop', 5, 'queue', 'worker', 1)
        self.lua('complete', 6, 'b', 'worker', 'queue', {})
        # Now it should be scheduled
        self.assertEqual(self.lua('get', 7, 'a')['state'], 'scheduled')
        self.assertEqual(len(self.lua('peek', 13, 'foo', 10)), 1)
        self.assertEqual(self.lua('get', 14, 'a')['state'], 'waiting')

    def test_complete_depends(self):
        '''Can also add dependencies upon completion'''
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'a', 'klass', {}, 0)
        # Pop 'b', and then complete it it and make it depend on 'a'
        self.lua('pop', 2, 'queue', 'worker', 1)
        self.lua('complete', 3, 'b', 'worker', 'queue', {},
            'depends', ['a'], 'next', 'queue')
        # Ensure that it shows up everywhere it should
        self.assertEqual(self.lua('get', 4, 'b')['state'], 'depends')
        self.assertEqual(self.lua('get', 5, 'b')['dependencies'], ['a'])
        self.assertEqual(self.lua('get', 6, 'a')['dependents'], ['b'])
        # Only one job should be available
        self.assertEqual(len(self.lua('peek', 7, 'queue', 10)), 1)

    def test_satisfied_dependencies(self):
        '''If dependencies are already complete, it should be available'''
        # First, let's try with a job that has been explicitly completed
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 1)
        self.lua('complete', 2, 'a', 'worker', 'queue', {})
        self.assertEqual(self.lua('get', 3, 'a')['state'], 'complete')
        # Now this job should be readily available
        self.lua('put', 4, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertEqual(self.lua('get', 5, 'b')['state'], 'waiting')
        self.assertEqual(self.lua('peek', 6, 'queue', 10)[0]['jid'], 'b')

    def test_nonexistent_dependencies(self):
        '''If dependencies don't exist, they're assumed completed'''
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertEqual(self.lua('get', 1, 'b')['state'], 'waiting')
        self.assertEqual(self.lua('peek', 2, 'queue', 10)[0]['jid'], 'b')

    def test_cancel_dependency_chain(self):
        '''If an entire dependency chain is cancelled together, it's ok'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.lua('cancel', 2, 'a', 'b')
        self.assertEqual(self.lua('get', 3, 'a'), None)
        self.assertEqual(self.lua('get', 4, 'b'), None)

    def test_cancel_incomplete_chain(self):
        '''Cannot bulk cancel if there are additional dependencies'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.lua('put', 2, 'worker', 'queue', 'c', 'klass', {}, 0, 'depends', ['b'])
        # Now, we'll only cancel part of this chain and see that it fails
        self.assertRaisesRegexp(redis.ResponseError, r'is a dependency',
            self.lua, 'cancel', 3, 'a', 'b')

    def test_cancel_with_missing_jobs(self):
        '''If some jobs are already canceled, it's ok'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.lua('cancel', 2, 'a', 'b', 'c')
        self.assertEqual(self.lua('get', 3, 'a'), None)
        self.assertEqual(self.lua('get', 4, 'b'), None)

    def test_cancel_any_order(self):
        '''Can bulk cancel jobs independent of the order'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.lua('cancel', 2, 'b', 'a')
        self.assertEqual(self.lua('get', 3, 'a'), None)
        self.assertEqual(self.lua('get', 4, 'b'), None)

    def test_multiple_dependency(self):
        '''Unlock a job only after all dependencies have been met'''
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
        # This job depends on all of the above
        self.lua('put', 20, 'worker', 'queue', 'jid', 'klass', {}, 0, 'depends', jids)
        for jid in jids:
            self.assertEqual(self.lua('get', 30, 'jid')['state'], 'depends')
            self.lua('pop', 30, 'queue', 'worker', 1)
            self.lua('complete', 30, jid, 'worker', 'queue', {})

        # With all of these dependencies finally satisfied, it's available
        self.assertEqual(self.lua('get', 40, 'jid')['state'], 'waiting')

    def test_dependency_chain(self):
        '''Test out successive unlocking of a dependency chain'''
        jids = map(str, range(10))
        self.lua('put', 0, 'worker', 'queue', 0, 'klass', {}, 0)
        for jid, dep in zip(jids[1:], jids[:-1]):
            self.lua(
                'put', jid, 'worker', 'queue', jid, 'klass', {}, 0, 'depends', [dep])
        # Now, we should successively pop jobs and they as we complete them
        # we should get the next
        for jid in jids:
            popped = self.lua('pop', 100, 'queue', 'worker', 10)
            self.assertEqual(len(popped), 1)
            self.assertEqual(popped[0]['jid'], jid)
            self.lua('complete', 100, jid, 'worker', 'queue', {})

    def test_add_dependency(self):
        '''We can add dependencies if it's already in the 'depends' state'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.lua('put', 2, 'worker', 'queue', 'c', 'klass', {}, 0, 'depends', ['a'])
        self.lua('depends', 3, 'c', 'on', 'b')
        self.assertEqual(self.lua('get', 4, 'c')['dependencies'], ['a', 'b'])

    def test_remove_dependency(self):
        '''We can remove dependencies'''
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
        # This job depends on all of the above
        self.lua('put', 100, 'worker', 'queue', 'jid', 'klass', {}, 0, 'depends', jids)
        # Now, we'll remove dependences one at a time
        for jid in jids:
            self.assertEqual(self.lua('get', 100, 'jid')['state'], 'depends')
            self.lua('depends', 100, 'jid', 'off', jid)
        # With all of these dependencies cancelled, this job should be ready
        self.assertEqual(self.lua('get', 100, 'jid')['state'], 'waiting')

    def test_reput_dependency(self):
        '''When we put a job with new deps, new replaces old'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.lua('put', 2, 'worker', 'queue', 'c', 'klass', {}, 0, 'depends', ['a'])
        self.lua('put', 3, 'worker', 'queue', 'c', 'klass', {}, 0, 'depends', ['b'])
        self.assertEqual(self.lua('get', 4, 'c')['dependencies'], ['b'])
        self.assertEqual(self.lua('get', 5, 'a')['dependents'], {})
        self.assertEqual(self.lua('get', 6, 'b')['dependents'], ['c'])
        # Also, let's make sure that its effective dependencies are changed
        self.lua('pop', 7, 'queue', 'worker', 10)
        self.lua('complete', 8, 'a', 'worker', 'queue', {})
        # We should not see the job unlocked
        self.assertEqual(self.lua('pop', 9, 'queue', 'worker', 10), {})
        self.lua('complete', 10, 'b', 'worker', 'queue', {})
        self.assertEqual(
            self.lua('pop', 9, 'queue', 'worker', 10)[0]['jid'], 'c')

    def test_depends_waiting(self):
        '''Cannot add or remove dependencies if the job is waiting'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'on', 'a')
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'off', 'a')

    def test_depends_scheduled(self):
        '''Cannot add or remove dependencies if the job is scheduled'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 1)
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'on', 'a')
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'off', 'a')

    def test_depends_nonexistent(self):
        '''Cannot add or remove dependencies if the job doesn't exist'''
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'on', 'a')
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'off', 'a')

    def test_depends_failed(self):
        '''Cannot add or remove dependencies if the job is failed'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 1, 'jid', 'worker', 'group', 'message', {})
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'on', 'a')
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'off', 'a')

    def test_depends_running(self):
        '''Cannot add or remove dependencies if the job is running'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'on', 'a')
        self.assertRaisesRegexp(redis.ResponseError, r'in the depends state',
            self.lua, 'depends', 0, 'jid', 'off', 'a')

########NEW FILE########
__FILENAME__ = test_events
'''A large number of operations generate events. Let's test'''

from common import TestQless


class TestEvents(TestQless):
    '''Check for all the events we expect'''
    def test_track(self):
        '''We should hear chatter about tracking and untracking jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        with self.lua:
            self.lua('track', 0, 'track', 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:track',
            'data': 'jid'
        }])

        with self.lua:
            self.lua('track', 0, 'untrack', 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:untrack',
            'data': 'jid'
        }])

    def test_track_canceled(self):
        '''Canceling a tracked job should spawn some data'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        with self.lua:
            self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"jid","queue":"queue","event":"canceled","worker":""}'
        }, {
            'channel': 'ql:canceled',
            'data': 'jid'
        }])

    def test_track_completed(self):
        '''Tracked jobs get extra notifications when they complete'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        self.lua('pop', 0, 'queue', 'worker', 10)
        with self.lua:
            self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:completed',
            'data': 'jid'
        }, {
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"completed","queue":"queue"}'
        }])

    def test_track_fail(self):
        '''We should hear chatter when failing a job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        self.lua('pop', 0, 'queue', 'worker', 10)
        with self.lua:
            self.lua('fail', 0, 'jid', 'worker', 'grp', 'mess', {})
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"message":"mess","jid":"jid","group":"grp","event":"failed","worker":"worker"}'
        }, {
            'channel': 'ql:failed',
            'data': 'jid'
        }])

    def test_track_popped(self):
        '''We should hear chatter when popping a tracked job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        with self.lua:
            self.lua('pop', 0, 'queue', 'worker', 10)
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:popped',
            'data': 'jid'
        }])

    def test_track_put(self):
        '''We should hear chatter when putting a tracked job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        with self.lua:
            self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"put","queue":"queue"}'
        }, {
            'channel': 'ql:put',
            'data': 'jid'
        }])

    def test_track_stalled(self):
        '''We should hear chatter when a job stalls'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        print self.lua('config.get', 0, 'grace-period')
        with self.lua:
            self.lua('pop', job['expires'] + 10, 'queue', 'worker', 10)
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:stalled',
            'data': 'jid'
        }, {
            'channel': 'ql:w:worker',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }, {
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }])

    def test_failed_retries(self):
        '''We should hear chatter when a job fails from retries'''
        self.lua('config.set', 0, 'grace-period', 0)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        with self.lua:
            self.assertEqual(self.lua(
                'pop', job['expires'] + 10, 'queue', 'worker', 10), {})
        self.assertEqual(self.lua('get', 0, 'jid')['state'], 'failed')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:w:worker',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }, {
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }, {
            'channel': 'ql:log',
            'data': '{"message":"Job exhausted retries in queue \\"queue\\"","jid":"jid","group":"failed-retries-queue","event":"failed","worker":"worker"}'
        }])

    def test_advance(self):
        '''We should hear chatter when completing and advancing a job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        with self.lua:
            self.lua(
                'complete', 0, 'jid', 'worker', 'queue', {}, 'next', 'queue')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"jid","to":"queue","event":"advanced","queue":"queue"}'
        }])

    def test_timeout(self):
        '''We should hear chatter when a job times out'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        with self.lua:
            self.lua('timeout', 0, 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:w:worker',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }, {
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }])

    def test_put(self):
        '''We should hear chatter when a job is put into a queueu'''
        with self.lua:
            self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"put","queue":"queue"}'
        }])

    def test_reput(self):
        '''When we put a popped job into a queue, it informs the worker'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        with self.lua:
            self.lua('put', 0, 'another', 'another', 'jid', 'klass', {}, 10)
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"put","queue":"another"}'
        }, {
            'channel': 'ql:w:worker',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }, {
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"lock_lost","worker":"worker"}'
        }])

    def test_config_set(self):
        '''We should hear chatter about setting configurations'''
        with self.lua:
            self.lua('config.set', 0, 'foo', 'bar')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data': '{"option":"foo","event":"config_set","value":"bar"}'
        }])

    def test_config_unset(self):
        '''We should hear chatter about unsetting configurations'''
        self.lua('config.set', 0, 'foo', 'bar')
        with self.lua:
            self.lua('config.unset', 0, 'foo')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data': '{"event":"config_unset","option":"foo"}'
        }])

    def test_cancel_waiting(self):
        '''We should hear chatter about canceling waiting jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        with self.lua:
            self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"jid","queue":"queue","event":"canceled","worker":""}'
        }])

    def test_cancel_running(self):
        '''We should hear chatter about canceling running jobs'''
        self.lua('put', 0, 'worker', 'q', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'q', 'wrk', 10)
        with self.lua:
            self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"jid","queue":"q","event":"canceled","worker":"wrk"}'
        }, {
            'channel': 'ql:w:wrk',
            'data':
                '{"jid":"jid","queue":"q","event":"canceled","worker":"wrk"}'
        }])

    def test_cancel_depends(self):
        '''We should hear chatter about canceling dependent jobs'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        with self.lua:
            self.lua('cancel', 0, 'b')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"b","queue":"queue","event":"canceled","worker":""}'
        }])

    def test_cancel_scheduled(self):
        '''We should hear chatter about canceling scheduled jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 10)
        with self.lua:
            self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"jid","queue":"queue","event":"canceled","worker":""}'
        }])

    def test_cancel_failed(self):
        '''We should hear chatter about canceling failed jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 0, 'jid', 'worker', 'group', 'message', {})
        with self.lua:
            self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data':
                '{"jid":"jid","queue":"queue","event":"canceled","worker":""}'
        }])

    def test_move_lock(self):
        '''We should /not/ get lock lost events for moving a job we own'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        with self.lua:
            # Put the job under the same worker who owns it now
            self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua.log, [{
            'channel': 'ql:log',
            'data': '{"jid":"jid","event":"put","queue":"queue"}'
        }])

########NEW FILE########
__FILENAME__ = test_fail
'''Tests about failing jobs'''

import redis
from common import TestQless


class TestFail(TestQless):
    '''Test the behavior of failing jobs'''
    def test_malformed(self):
        '''Enumerate all the malformed cases'''
        self.assertMalformed(self.lua, [
            ('fail', 0),
            ('fail', 0, 'jid'),
            ('fail', 0, 'jid', 'worker'),
            ('fail', 0, 'jid', 'worker', 'group'),
            ('fail', 0, 'jid', 'worker', 'group', 'message'),
            ('fail', 0, 'jid', 'worker', 'group', 'message', '[}')
        ])

    def test_basic(self):
        '''Fail a job in a very basic way'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('fail', 2, 'jid', 'worker', 'group', 'message', {})
        self.assertEqual(self.lua('get', 3, 'jid'), {'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {'group': 'group',
                        'message': 'message',
                        'when': 2,
                        'worker': 'worker'},
            'history': [{'q': 'queue', 'what': 'put', 'when': 0},
                        {'what': 'popped', 'when': 1, 'worker': 'worker'},
                        {'group': 'group',
                         'what': 'failed',
                         'when': 2,
                         'worker': 'worker'}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'queue',
            'remaining': 5,
            'retries': 5,
            'state': 'failed',
            'tags': {},
            'tracked': False,
            'worker': u'',
            'spawned_from_jid': False})

    def test_put(self):
        '''Can put a job that has been failed'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('fail', 2, 'jid', 'worker', 'group', 'message', {})
        self.lua('put', 3, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(len(self.lua('peek', 4, 'queue', 10)), 1)

    def test_fail_waiting(self):
        '''Only popped jobs can be failed'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertRaisesRegexp(redis.ResponseError, r'waiting',
            self.lua, 'fail', 1, 'jid', 'worker', 'group', 'message', {})
        # Pop is and it should work
        self.lua('pop', 2, 'queue', 'worker', 10)
        self.lua('fail', 3, 'jid', 'worker', 'group', 'message', {})

    def test_fail_depends(self):
        '''Cannot fail a dependent job'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertRaisesRegexp(redis.ResponseError, r'depends',
            self.lua, 'fail', 1, 'b', 'worker', 'group', 'message', {})

    def test_fail_scheduled(self):
        '''Cannot fail a scheduled job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 1)
        self.assertRaisesRegexp(redis.ResponseError, r'scheduled',
            self.lua, 'fail', 1, 'jid', 'worker', 'group', 'message', {})

    def test_fail_nonexistent(self):
        '''Cannot fail a job that doesn't exist'''
        self.assertRaisesRegexp(redis.ResponseError, r'does not exist',
            self.lua, 'fail', 1, 'jid', 'worker', 'group', 'message', {})
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 1, 'jid', 'worker', 'group', 'message', {})

    def test_fail_completed(self):
        '''Cannot fail a job that has been completed'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        self.assertRaisesRegexp(redis.ResponseError, r'complete',
            self.lua, 'fail', 1, 'jid', 'worker', 'group', 'message', {})

    def test_fail_owner(self):
        '''Cannot fail a job that's running with another worker'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('put', 2, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 3, 'queue', 'another-worker', 10)
        self.assertRaisesRegexp(redis.ResponseError, r'another worker',
            self.lua, 'fail', 4, 'jid', 'worker', 'group', 'message', {})


class TestFailed(TestQless):
    '''Test access to our failed jobs'''
    def test_malformed(self):
        '''Enumerate all the malformed requests'''
        self.assertMalformed(self.lua, [
            ('failed', 0, 'foo', 'foo'),
            ('failed', 0, 'foo', 0, 'foo')
        ])

    def test_basic(self):
        '''We can keep track of failed jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 0, 'jid', 'worker', 'group', 'message')
        self.assertEqual(self.lua('failed', 0), {
            'group': 1
        })
        self.assertEqual(self.lua('failed', 0, 'group'), {
            'total': 1,
            'jobs': ['jid']
        })

    def test_retries(self):
        '''Jobs that fail because of retries should show up'''
        self.lua('config.set', 0, 'grace-period', 0)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        self.lua('pop', job['expires'] + 10, 'queue', 'worker', 10)
        self.assertEqual(self.lua('failed', 0), {
            'failed-retries-queue': 1
        })
        self.assertEqual(self.lua('failed', 0, 'failed-retries-queue'), {
            'total': 1,
            'jobs': ['jid']
        })

    def test_failed_pagination(self):
        '''Failed provides paginated access'''
        jids = map(str, range(100))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', jid, 'queue', 'worker', 10)
            self.lua('fail', jid, jid, 'worker', 'group', 'message')
        # Get two pages of 50 and make sure they're what we expect
        jids = list(reversed(jids))
        self.assertEqual(
            self.lua('failed', 0, 'group',  0, 50)['jobs'], jids[:50])
        self.assertEqual(
            self.lua('failed', 0, 'group', 50, 50)['jobs'], jids[50:])


class TestUnfailed(TestQless):
    '''Test access to unfailed'''
    def test_basic(self):
        '''We can unfail in a basic way'''
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', 0, 'queue', 'worker', 10)
            self.lua('fail', 0, jid, 'worker', 'group', 'message')
            self.assertEqual(self.lua('get', 0, jid)['state'], 'failed')
        self.lua('unfail', 0, 'queue', 'group', 100)
        for jid in jids:
            self.assertEqual(self.lua('get', 0, jid)['state'], 'waiting')

########NEW FILE########
__FILENAME__ = test_general
'''Check some general functionality surrounding the the API'''

import redis
from common import TestQless


class TestGeneral(TestQless):
    '''Some general tests'''
    def test_keys(self):
        '''No keys may be provided to the script'''
        self.assertRaises(redis.ResponseError, self.lua.raw, 'foo')

    def test_unknown_function(self):
        '''If the API function is unknown, it should throw an error'''
        self.assertRaises(redis.ResponseError, self.lua, 'foo')

    def test_no_time(self):
        '''If we neglect to provide a time, it should throw an error'''
        self.assertRaises(redis.ResponseError, self.lua, 'put')

    def test_malformed_time(self):
        '''If we provide a non-numeric time, it should throw an error'''
        self.assertRaises(redis.ResponseError, self.lua, 'put', 'foo')

########NEW FILE########
__FILENAME__ = test_job
'''Test job-centric operations'''

import redis
from common import TestQless


class TestJob(TestQless):
    '''Some general jobby things'''
    def test_malformed(self):
        '''Enumerate all malformed input to priority'''
        self.assertMalformed(self.lua, [
            ('priority', '0'),
            ('priority', '0', 'jid'),
            ('priority', '0', 'jid', 'foo')
        ])

    def test_log(self):
        '''Can add a log to a job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('log', 0, 'jid', 'foo', {'foo': 'bar'})
        self.assertEqual(self.lua('get', 0, 'jid')['history'], [
            {'q': 'queue', 'what': 'put', 'when': 0},
            {'foo': 'bar', 'what': 'foo', 'when': 0}
        ])

    def test_log_nonexistent(self):
        '''If a job doesn't exist, logging throws an error'''
        self.assertRaisesRegexp(redis.ResponseError, r'does not exist',
            self.lua, 'log', 0, 'jid', 'foo', {'foo': 'bar'})

    def test_history(self):
        '''We only keep the most recent max-job-history items in history'''
        self.lua('config.set', 0, 'max-job-history', 5)
        for index in range(100):
            self.lua('put', index, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('get', 0, 'jid')['history'], [
            {'q': 'queue', 'what': 'put', 'when': 0},
            {'q': 'queue', 'what': 'put', 'when': 96},
            {'q': 'queue', 'what': 'put', 'when': 97},
            {'q': 'queue', 'what': 'put', 'when': 98},
            {'q': 'queue', 'what': 'put', 'when': 99}])


class TestComplete(TestQless):
    '''Test how we complete jobs'''
    def test_malformed(self):
        '''Enumerate all the way they can be malformed'''
        self.assertMalformed(self.lua, [
            ('complete', 0, 'jid', 'worker', 'queue', {}, 'next'),
            ('complete', 0, 'jid', 'worker', 'queue', {}, 'delay'),
            ('complete', 0, 'jid', 'worker', 'queue', {}, 'delay', 'foo'),
            ('complete', 0, 'jid', 'worker', 'queue', {}, 'depends'),
            ('complete', 0, 'jid', 'worker', 'queue', {}, 'depends', '[}'),
            # Can't have 'depends' with a delay
            ('complete', 0, 'jid', 'worker', 'queue', {},
                'depends', ['foo'], 'delay', 5),
            # Can't have 'depends' without 'next'
            ('complete', 0, 'jid', 'worker', 'queue', {}, 'depends', ['foo'])
        ])

    def test_complete_waiting(self):
        '''Only popped jobs can be completed'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertRaisesRegexp(redis.ResponseError, r'waiting',
            self.lua, 'complete', 1, 'jid', 'worker', 'queue', {})
        # Pop it and it should work
        self.lua('pop', 2, 'queue', 'worker', 10)
        self.lua('complete', 1, 'jid', 'worker', 'queue', {})

    def test_complete_depends(self):
        '''Cannot complete a dependent job'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertRaisesRegexp(redis.ResponseError, r'depends',
            self.lua, 'complete', 1, 'b', 'worker', 'queue', {})

    def test_complete_scheduled(self):
        '''Cannot complete a scheduled job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 1)
        self.assertRaisesRegexp(redis.ResponseError, r'scheduled',
            self.lua, 'complete', 1, 'jid', 'worker', 'queue', {})

    def test_complete_nonexistent(self):
        '''Cannot complete a job that doesn't exist'''
        self.assertRaisesRegexp(redis.ResponseError, r'does not exist',
            self.lua, 'complete', 1, 'jid', 'worker', 'queue', {})
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 1, 'jid', 'worker', 'queue', {})

    def test_complete_failed(self):
        '''Cannot complete a failed job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 1, 'jid', 'worker', 'group', 'message', {})
        self.assertRaisesRegexp(redis.ResponseError, r'failed',
            self.lua, 'complete', 0, 'jid', 'worker', 'queue', {})

    def test_complete_previously_failed(self):
        '''Erases failure data after completing'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('fail', 2, 'jid', 'worker', 'group', 'message', {})
        self.lua('put', 3, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 4, 'queue', 'worker', 10)
        self.assertEqual(self.lua('get', 5, 'jid')['failure'], {
            'group': 'group',
            'message': 'message',
            'when': 2,
            'worker': 'worker'})
        self.lua('complete', 6, 'jid', 'worker', 'queue', {})
        self.assertEqual(self.lua('get', 7, 'jid')['failure'], {})

    def test_basic(self):
        '''Basic completion'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('complete', 2, 'jid', 'worker', 'queue', {})
        self.assertEqual(self.lua('get', 3, 'jid'), {
            'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {},
            'history': [{'q': 'queue', 'what': 'put', 'when': 0},
                        {'what': 'popped', 'when': 1, 'worker': 'worker'},
                        {'what': 'done', 'when': 2}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': u'',
            'remaining': 5,
            'retries': 5,
            'state': 'complete',
            'tags': {},
            'tracked': False,
            'worker': u'',
            'spawned_from_jid': False})

    def test_advance(self):
        '''Can complete and advance a job in one fell swooop'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('complete', 2, 'jid', 'worker', 'queue', {}, 'next', 'foo')
        self.assertEqual(
            self.lua('pop', 3, 'foo', 'worker', 10)[0]['jid'], 'jid')

    def test_wrong_worker(self):
        '''Only the right worker can complete it'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertRaisesRegexp(redis.ResponseError, r'another worker',
            self.lua, 'complete', 2, 'jid', 'another', 'queue', {})

    def test_wrong_queue(self):
        '''A job can only be completed in the queue it's in'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertRaisesRegexp(redis.ResponseError, r'another queue',
            self.lua, 'complete', 2, 'jid', 'worker', 'another-queue', {})

    def test_expire_complete_count(self):
        '''Jobs expire after a k complete jobs'''
        self.lua('config.set', 0, 'jobs-history-count', 5)
        jids = range(10)
        for jid in range(10):
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        for jid in jids:
            self.lua('complete', 2, jid, 'worker', 'queue', {})
        existing = [self.lua('get', 3, jid) for jid in range(10)]
        self.assertEqual(len([i for i in existing if i]), 5)

    def test_expire_complete_time(self):
        '''Jobs expire after a certain amount of time'''
        self.lua('config.set', 0, 'jobs-history', -1)
        jids = range(10)
        for jid in range(10):
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        for jid in jids:
            self.lua('complete', 2, jid, 'worker', 'queue', {})
        existing = [self.lua('get', 3, jid) for jid in range(10)]
        self.assertEqual([i for i in existing if i], [])


class TestCancel(TestQless):
    '''Canceling jobs'''
    def test_cancel_waiting(self):
        '''You can cancel waiting jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua('get', 0, 'jid'), None)

    def test_cancel_depends(self):
        '''You can cancel dependent job'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.lua('cancel', 0, 'b')
        self.assertEqual(self.lua('get', 0, 'b'), None)
        self.assertEqual(self.lua('get', 0, 'a')['dependencies'], {})

    def test_cancel_dependents(self):
        '''Cannot cancel jobs if they still have dependencies'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertRaisesRegexp(redis.ResponseError, r'dependency',
            self.lua, 'cancel', 0, 'a')

    def test_cancel_scheduled(self):
        '''You can cancel scheduled jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 1)
        self.lua('cancel', 0, 'jid')
        self.assertEqual(self.lua('get', 0, 'jid'), None)

    def test_cancel_nonexistent(self):
        '''Can cancel jobs that do not exist without failing'''
        self.lua('cancel', 0, 'jid')

    def test_cancel_failed(self):
        '''Can cancel failed jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 1, 'jid', 'worker', 'group', 'message', {})
        self.lua('cancel', 2, 'jid')
        self.assertEqual(self.lua('get', 3, 'jid'), None)

    def test_cancel_running(self):
        '''Can cancel running jobs, prevents heartbeats'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('heartbeat', 2, 'jid', 'worker', {})
        self.lua('cancel', 3, 'jid')
        self.assertRaisesRegexp(redis.ResponseError, r'Job does not exist',
            self.lua, 'heartbeat', 4, 'jid', 'worker', {})

    def test_cancel_retries(self):
        '''Can cancel job that has been failed from retries through retry'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('get', 2, 'jid')['state'], 'running')
        self.lua('retry', 3, 'jid', 'queue', 'worker')
        self.lua('cancel', 4, 'jid')
        self.assertEqual(self.lua('get', 5, 'jid'), None)

    def test_cancel_pop_retries(self):
        '''Can cancel job that has been failed from retries through pop'''
        self.lua('config.set', 0, 'heartbeat', -10)
        self.lua('config.set', 0, 'grace-period', 0)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('pop', 2, 'queue', 'worker', 10)
        self.lua('cancel', 3, 'jid')
        self.assertEqual(self.lua('get', 4, 'jid'), None)

########NEW FILE########
__FILENAME__ = test_locks
'''Tests about locks'''

import redis
from common import TestQless


class TestLocks(TestQless):
    '''Locks tests'''
    def test_malformed(self):
        '''Enumerate malformed inputs into heartbeat'''
        self.assertMalformed(self.lua, [
            ('heartbeat', 0),
            ('heartbeat', 0, 'jid'),
            ('heartbeat', 0, 'jid', 'worker', '[}')
        ])

    def setUp(self):
        TestQless.setUp(self)
        # No grace period for any of these tests
        self.lua('config.set', 0, 'grace-period', 0)

    def test_move(self):
        '''Moving ajob should expire any existing locks'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('heartbeat', 2, 'jid', 'worker', {})
        # Move the job after it's been popped
        self.lua('put', 3, 'worker', 'other', 'jid', 'klass', {}, 0)
        # Now this job cannot be heartbeated
        self.assertRaisesRegexp(redis.ResponseError, r'waiting',
            self.lua, 'heartbeat',  4, 'jid', 'worker', {})

    def test_lose_lock(self):
        '''When enough time passes, we lose our lock on a job'''
        # Put and pop a job
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 1, 'queue', 'worker', 10)[0]
        # No jobs should be available since the lock is still valid
        self.assertEqual(self.lua('pop', 2, 'queue', 'worker', 10), {})
        self.assertEqual(self.lua(
            'pop', job['expires'] + 10, 'queue', 'another', 10), [{
                'data': '{}',
                'dependencies': {},
                'dependents': {},
                'expires': 131,
                'failure': {},
                'history': [
                    {'q': 'queue', 'what': 'put', 'when': 0},
                    {'what': 'popped', 'when': 1, 'worker': 'worker'},
                    {'what': 'timed-out', 'when': 71},
                    {'what': 'popped', 'when': 71, 'worker': 'another'}],
                'jid': 'jid',
                'klass': 'klass',
                'priority': 0,
                'queue': 'queue',
                'remaining': 4,
                'retries': 5,
                'state': 'running',
                'tags': {},
                'tracked': False,
                'worker': 'another',
                'spawned_from_jid': False}])
        # When we try to heartbeat, it should raise an exception
        self.assertRaisesRegexp(redis.ResponseError, r'given out to another',
            self.lua, 'heartbeat', 1000, 'jid', 'worker', {})

    def test_heartbeat(self):
        '''Heartbeating extends the lock'''
        # Put and pop a job
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 1, 'queue', 'worker', 10)[0]
        # No jobs should be available since the lock is still valid
        self.assertEqual(self.lua('pop', 2, 'queue', 'worker', 10), {})
        # We should see our expiration update after a heartbeat
        self.assertTrue(
            self.lua('heartbeat', 3, 'jid', 'worker', {}) > job['expires'])

    def test_heartbeat_waiting(self):
        '''Only popped jobs can be heartbeated'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertRaisesRegexp(redis.ResponseError, r'waiting',
            self.lua, 'heartbeat',  1, 'jid', 'worker', {})
        # Pop is and it should work
        self.lua('pop', 2, 'queue', 'worker', 10)
        self.lua('heartbeat', 3, 'jid', 'worker', {})

    def test_heartbeat_failed(self):
        '''Cannot heartbeat a failed job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 0, 'jid', 'worker', 'foo', 'bar', {})
        self.assertRaisesRegexp(redis.ResponseError, r'failed',
            self.lua, 'heartbeat',  0, 'jid', 'worker', {})

    def test_heartbeat_depends(self):
        '''Cannot heartbeat a dependent job'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertRaisesRegexp(redis.ResponseError, r'depends',
            self.lua, 'heartbeat',  0, 'b', 'worker', {})

    def test_heartbeat_scheduled(self):
        '''Cannot heartbeat a scheduled job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 1)
        self.assertRaisesRegexp(redis.ResponseError, r'scheduled',
            self.lua, 'heartbeat',  0, 'jid', 'worker', {})

    def test_heartbeat_nonexistent(self):
        '''Cannot heartbeat a job that doesn't exist'''
        self.assertRaisesRegexp(redis.ResponseError, r'does not exist',
            self.lua, 'heartbeat',  0, 'jid', 'worker', {})
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('heartbeat', 0, 'jid', 'worker', {})

    def test_heartbeat_completed(self):
        '''Cannot heartbeat a job that has been completed'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        self.assertRaisesRegexp(redis.ResponseError, r'complete',
            self.lua, 'heartbeat',  0, 'jid', 'worker', {})

    def test_heartbeat_wrong_worker(self):
        '''Only the worker with a job's lock can heartbeat it'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        # Another worker can't heartbeat, but we can
        self.assertRaisesRegexp(redis.ResponseError, r'another worker',
            self.lua, 'heartbeat',  2, 'jid', 'another', {})
        self.lua('heartbeat', 2, 'jid', 'worker', {})


class TestRetries(TestQless):
    '''Test all the behavior surrounding retries'''
    def setUp(self):
        TestQless.setUp(self)
        # No grace periods for this
        self.lua('config.set', 0, 'grace-period', 0)
        self.lua('config.set', 0, 'heartbeat', -10)

    def test_basic(self):
        '''The retries and remaining counters are decremented appropriately'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 5)
        self.lua('pop', 0, 'queue', 'worker', 10)
        job = self.lua('pop', 0, 'queue', 'another', 10)[0]
        self.assertEqual(job['retries'], 5)
        self.assertEqual(job['remaining'], 4)

    def test_move_failed_retries(self):
        '''Can move a job even if it's failed retries'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.assertEqual(self.lua('pop', 0, 'queue', 'worker', 10), {})
        self.assertEqual(self.lua('get', 0, 'jid')['state'], 'failed')
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('get', 0, 'jid')['state'], 'waiting')

    def test_reset_complete(self):
        '''Completing a job resets its retries counter'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 5)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua(
            'complete', 0, 'jid', 'worker', 'queue', {}, 'next', 'queue')
        self.assertEqual(self.lua(
            'pop', 0, 'queue', 'worker', 10)[0]['remaining'], 5)

    def test_reset_move(self):
        '''Moving a job resets its retries counter'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 5)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('pop', 0, 'queue', 'worker', 10)
        # Re-put the job without specifying retries
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua(
            'pop', 0, 'queue', 'worker', 10)[0]['remaining'], 5)


class TestRetry(TestQless):
    '''Test all the behavior surrounding retry'''
    maxDiff = 100000
    def test_malformed(self):
        '''Enumerate all the malformed inputs'''
        self.assertMalformed(self.lua, [
            ('retry', 0),
            ('retry', 0, 'jid'),
            ('retry', 0, 'jid', 'queue'),
            ('retry', 0, 'jid', 'queue', 'worker'),
            ('retry', 0, 'jid', 'queue', 'worker', 'foo'),
        ])
        # function QlessJob:retry(now, queue, worker, delay, group, message)

    def test_retry_waiting(self):
        '''Cannot retry a job that's waiting'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'retry', 0, 'jid', 'queue', 'worker', 0)

    def test_retry_completed(self):
        '''Cannot retry a completed job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'retry', 0, 'jid', 'queue', 'worker', 0)

    def test_retry_failed(self):
        '''Cannot retry a failed job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('fail', 0, 'jid', 'worker', 'group', 'message', {})
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'retry', 0, 'jid', 'queue', 'worker', 0)

    def test_retry_otherowner(self):
        '''Cannot retry a job owned by another worker'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.assertRaisesRegexp(redis.ResponseError, r'another worker',
            self.lua, 'retry', 0, 'jid', 'queue', 'another', 0)

    def test_retry_complete(self):
        '''Cannot complete a job immediately after retry'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('retry', 0, 'jid', 'queue', 'worker', 0)
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'complete', 0, 'jid', 'worker', 'queue', {})

    def test_retry_fail(self):
        '''Cannot fail a job immediately after retry'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('retry', 0, 'jid', 'queue', 'worker', 0)
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'fail', 0, 'jid', 'worker', 'group', 'message', {})

    def test_retry_heartbeat(self):
        '''Cannot heartbeat a job immediately after retry'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('retry', 0, 'jid', 'queue', 'worker', 0)
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'heartbeat', 0, 'jid', 'worker', {})

    def test_retry_nonexistent(self):
        '''It's an error to retry a nonexistent job'''
        self.assertRaisesRegexp(redis.ResponseError, r'does not exist',
            self.lua, 'retry', 0, 'jid', 'queue', 'another', 0)

    def test_retry_group_message(self):
        '''Can provide a group/message to be used for retries'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua(
            'retry', 0, 'jid', 'queue', 'worker', 0, 'group', 'message')
        self.assertEqual(self.lua('get', 0, 'jid'), {'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {'group': 'group',
                        'message': 'message',
                        'when': 0,
                        'worker': 'worker'},
            'history': [{'q': 'queue', 'what': 'put', 'when': 0},
                        {'what': 'popped', 'when': 0, 'worker': 'worker'},
                        {'group': 'group', 'what': 'failed', 'when': 0}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'queue',
            'remaining': -1,
            'retries': 0,
            'state': 'failed',
            'tags': {},
            'tracked': False,
            'worker': u'',
            'spawned_from_jid': False})

    def test_retry_delay(self):
        '''Can retry a job with a delay and then it's considered scheduled'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua(
            'retry', 0, 'jid', 'queue', 'worker', 10)
        # Now it should be considered scheduled
        self.assertEqual(self.lua('pop', 0, 'queue', 'worker', 10), {})
        self.assertEqual(self.lua('get', 0, 'jid')['state'], 'scheduled')

    def test_retry_wrong_queue(self):
        '''Cannot retry a job in the wrong queue'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('retry', 0, 'jid', 'queue', 'worker', 0)
        self.assertRaisesRegexp(redis.ResponseError, r'not currently running',
            self.lua, 'heartbeat', 0, 'jid', 'worker', {})

    def test_retry_failed_retries(self):
        '''Retry can be invoked enough to cause it to fail retries'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua(
            'retry', 0, 'jid', 'queue', 'worker', 0)
        self.assertEqual(self.lua('get', 0, 'jid'), {
            'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {
                'group': 'failed-retries-queue',
                'message': 'Job exhausted retries in queue "queue"',
                'when': 0,
                'worker': u''},
            'history': [
                {'q': 'queue', 'what': 'put', 'when': 0},
                {'what': 'popped', 'when': 0, 'worker': 'worker'},
                {'group': 'failed-retries-queue', 'what': 'failed', 'when': 0}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'queue',
            'remaining': -1,
            'retries': 0,
            'state': 'failed',
            'tags': {},
            'tracked': False,
            'worker': u'',
            'spawned_from_jid': False
        })


class TestGracePeriod(TestQless):
    '''Make sure the grace period is honored'''
    # Our grace period for the tests
    grace = 10

    def setUp(self):
        TestQless.setUp(self)
        # Ensure whe know what the grace period is
        self.lua('config.set', 0, 'grace-period', self.grace)

    def test_basic(self):
        '''The lock must expire, and then the grace period must pass'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 1, 'queue', 'worker', 10)[0]
        # Now, we'll lose the lock, but we should only get a warning, and not
        # actually have the job handed off to another yet
        expires = job['expires'] + 10
        self.assertEqual(self.lua('pop', expires, 'queue', 'another', 10), {})
        # However, once the grace period passes, we should be fine
        self.assertNotEqual(
            self.lua('pop', expires + self.grace, 'queue', 'another', 10), {})

    def test_repeated(self):
        '''Grace periods should be given for each lock lost, not just first'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 20)
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        for _ in xrange(10):
            # Now, we'll lose the lock, but we should only get a warning, and
            # not actually have the job handed off to another yet
            expires = job['expires'] + 10
            self.assertEqual(
                self.lua('pop', expires, 'queue', 'worker', 10), {})
            # However, once the grace period passes, we should be fine
            job = self.lua(
                'pop', expires + self.grace, 'queue', 'worker', 10)[0]

    def test_fail(self):
        '''Can still fail a job during the grace period'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        # Lose the lock and fail the job
        expires = job['expires'] + 10
        self.lua('pop', expires, 'queue', 'worker', 10)
        self.lua('fail', expires, 'jid', 'worker', 'foo', 'bar', {})
        # And make sure that no job is available after the grace period
        self.assertEqual(
            self.lua('pop', expires + self.grace, 'queue', 'worker', 10), {})

########NEW FILE########
__FILENAME__ = test_queue
'''Test the queue functionality'''

from common import TestQless


class TestJobs(TestQless):
    '''We should be able to list jobs in various states for a given queue'''
    def test_malformed(self):
        '''Enumerate all the ways that the input can be malformed'''
        self.assertMalformed(self.lua, [
            ('jobs', 0, 'complete', 'foo'),
            ('jobs', 0, 'complete', 0, 'foo'),
            ('jobs', 0, 'running'),
            ('jobs', 0, 'running', 'queue', 'foo'),
            ('jobs', 0, 'running', 'queue', 0, 'foo'),
            ('jobs', 0, 'stalled'),
            ('jobs', 0, 'stalled`', 'queue', 'foo'),
            ('jobs', 0, 'stalled', 'queue', 0, 'foo'),
            ('jobs', 0, 'scheduled'),
            ('jobs', 0, 'scheduled', 'queue', 'foo'),
            ('jobs', 0, 'scheduled', 'queue', 0, 'foo'),
            ('jobs', 0, 'depends'),
            ('jobs', 0, 'depends', 'queue', 'foo'),
            ('jobs', 0, 'depends', 'queue', 0, 'foo'),
            ('jobs', 0, 'recurring'),
            ('jobs', 0, 'recurring', 'queue', 'foo'),
            ('jobs', 0, 'recurring', 'queue', 0, 'foo'),
            ('jobs', 0, 'foo', 'queue', 0, 25)
        ])

    def test_complete(self):
        '''Verify we can list complete jobs'''
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', jid, 'queue', 'worker', 10)
            self.lua('complete', jid, jid, 'worker', 'queue', {})
            complete = self.lua('jobs', jid, 'complete')
            self.assertEqual(len(complete), int(jid) + 1)
            self.assertEqual(complete[0], jid)

    def test_running(self):
        '''Verify that we can get a list of running jobs in a queue'''
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', jid, 'queue', 'worker', 10)
            running = self.lua('jobs', jid, 'running', 'queue')
            self.assertEqual(len(running), int(jid) + 1)
            self.assertEqual(running[-1], jid)

    def test_stalled(self):
        '''Verify that we can get a list of stalled jobs in a queue'''
        self.lua('config.set', 0, 'heartbeat', 10)
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', jid, 'queue', 'worker', 10)
            stalled = self.lua('jobs', int(jid) + 20, 'stalled', 'queue')
            self.assertEqual(len(stalled), int(jid) + 1)
            self.assertEqual(stalled[-1], jid)

    def test_scheduled(self):
        '''Verify that we can get a list of scheduled jobs in a queue'''
        jids = map(str, range(1, 11))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, jid)
            scheduled = self.lua('jobs', 0, 'scheduled', 'queue')
            self.assertEqual(len(scheduled), int(jid))
            self.assertEqual(scheduled[-1], jid)

    def test_depends(self):
        '''Verify that we can get a list of dependent jobs in a queue'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        jids = map(str, range(0, 10))
        for jid in jids:
            self.lua(
                'put', jid, 'worker', 'queue', jid, 'klass', {}, 0, 'depends', ['a'])
            depends = self.lua('jobs', 0, 'depends', 'queue')
            self.assertEqual(len(depends), int(jid) + 1)
            self.assertEqual(depends[-1], jid)

    def test_recurring(self):
        '''Verify that we can get a list of recurring jobs in a queue'''
        jids = map(str, range(0, 10))
        for jid in jids:
            self.lua(
                'recur', jid, 'queue', jid, 'klass', {}, 'interval', 60, 0)
            recurring = self.lua('jobs', 0, 'recurring', 'queue')
            self.assertEqual(len(recurring), int(jid) + 1)
            self.assertEqual(recurring[-1], jid)

    def test_recurring_offset(self):
        '''Recurring jobs with a future offset should be included'''
        jids = map(str, range(0, 10))
        for jid in jids:
            self.lua(
                'recur', jid, 'queue', jid, 'klass', {}, 'interval', 60, 10)
            recurring = self.lua('jobs', 0, 'recurring', 'queue')
            self.assertEqual(len(recurring), int(jid) + 1)
            self.assertEqual(recurring[-1], jid)

    def test_scheduled_waiting(self):
        '''Jobs that were scheduled but are ready shouldn't be in scheduled'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 10)
        self.assertEqual(len(self.lua('jobs', 20, 'scheduled', 'queue')), 0)

    def test_pagination_complete(self):
        '''Jobs should be able to provide paginated results for complete'''
        jids = map(str, range(100))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', jid, 'queue', 'worker', 10)
            self.lua('complete', jid, jid, 'worker', 'queue', {})
        # Get two pages and ensure they're what we expect
        jids = list(reversed(jids))
        self.assertEqual(
            self.lua('jobs', 0, 'complete',  0, 50), jids[:50])
        self.assertEqual(
            self.lua('jobs', 0, 'complete', 50, 50), jids[50:])

    def test_pagination_running(self):
        '''Jobs should be able to provide paginated result for running'''
        jids = map(str, range(100))
        self.lua('config.set', 0, 'heartbeat', 1000)
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', jid, 'queue', 'worker', 10)
        # Get two pages and ensure they're what we expect
        self.assertEqual(
            self.lua('jobs', 100, 'running', 'queue',  0, 50), jids[:50])
        self.assertEqual(
            self.lua('jobs', 100, 'running', 'queue', 50, 50), jids[50:])


class TestQueue(TestQless):
    '''Test queue info tests'''
    expected = {
        'name': 'queue',
        'paused': False,
        'stalled': 0,
        'waiting': 0,
        'running': 0,
        'depends': 0,
        'scheduled': 0,
        'recurring': 0
    }

    def setUp(self):
        TestQless.setUp(self)
        # No grace period
        self.lua('config.set', 0, 'grace-period', 0)

    def test_stalled(self):
        '''Discern stalled job counts correctly'''
        expected = dict(self.expected)
        expected['stalled'] = 1
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 1, 'queue', 'worker', 10)[0]
        expires = job['expires'] + 10
        self.assertEqual(self.lua('queues', expires, 'queue'), expected)
        self.assertEqual(self.lua('queues', expires), [expected])

    def test_waiting(self):
        '''Discern waiting job counts correctly'''
        expected = dict(self.expected)
        expected['waiting'] = 1
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

    def test_running(self):
        '''Discern running job counts correctly'''
        expected = dict(self.expected)
        expected['running'] = 1
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

    def test_depends(self):
        '''Discern dependent job counts correctly'''
        expected = dict(self.expected)
        expected['depends'] = 1
        expected['waiting'] = 1
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

    def test_scheduled(self):
        '''Discern scheduled job counts correctly'''
        expected = dict(self.expected)
        expected['scheduled'] = 1
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 10)
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

    def test_recurring(self):
        '''Discern recurring job counts correctly'''
        expected = dict(self.expected)
        expected['recurring'] = 1
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

    def test_recurring_offset(self):
        '''Discern future recurring job counts correctly'''
        expected = dict(self.expected)
        expected['recurring'] = 1
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 10)
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

    def test_pause(self):
        '''Can pause and unpause a queue'''
        jids = map(str, range(10))
        for jid in jids:
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
        # After pausing, we can't get the jobs, and the state reflects it
        self.lua('pause', 0, 'queue')
        self.assertEqual(len(self.lua('pop', 0, 'queue', 'worker', 100)), 0)
        expected = dict(self.expected)
        expected['paused'] = True
        expected['waiting'] = 10
        self.assertEqual(self.lua('queues', 0, 'queue'), expected)
        self.assertEqual(self.lua('queues', 0), [expected])

        # Once unpaused, we should be able to pop jobs off
        self.lua('unpause', 0, 'queue')
        self.assertEqual(len(self.lua('pop', 0, 'queue', 'worker', 100)), 10)

    def test_advance(self):
        '''When advancing a job to a new queue, queues should know about it'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {}, 'next', 'another')
        expected = dict(self.expected)
        expected['name'] = 'another'
        expected['waiting'] = 1
        self.assertEqual(self.lua('queues', 0), [expected, self.expected])

    def test_recurring_move(self):
        '''When moving a recurring job, it should add the queue to queues'''
        expected = dict(self.expected)
        expected['name'] = 'another'
        expected['recurring'] = 1
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.lua('recur.update', 0, 'jid', 'queue', 'another')
        self.assertEqual(self.lua('queues', 0), [expected, self.expected])

    def test_scheduled_waiting(self):
        '''When checking counts, jobs that /were/ scheduled can be waiting'''
        expected = dict(self.expected)
        expected['waiting'] = 1
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 10)
        self.assertEqual(self.lua('queues', 20), [expected])
        self.assertEqual(self.lua('queues', 20, 'queue'), expected)


class TestPut(TestQless):
    '''Test putting jobs into a queue'''
    # For reference:
    #
    #   Put(now, jid, klass, data, delay,
    #       [priority, p],
    #       [tags, t],
    #       [retries, r],
    #       [depends, '[...]'])
    def put(self, *args):
        '''Alias for self.lua('put', ...)'''
        return self.lua('put', *args)

    def test_malformed(self):
        '''Enumerate all the ways in which the input can be messed up'''
        self.assertMalformed(self.put, [
            (12345,),                              # No queue provided
            (12345, 'foo'),                        # No jid provided
            (12345, 'foo', 'bar'),                 # No klass provided
            (12345, 'foo', 'bar', 'whiz'),         # No data provided
            (12345, 'foo', 'bar', 'whiz',
                '{}'),                               # No delay provided
            (12345, 'foo', 'bar', 'whiz',
                '{]'),                               # Malformed data provided
            (12345, 'foo', 'bar', 'whiz',
                '{}', 'number'),                     # Malformed delay provided
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'retries'),                          # Retries arg missing
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'retries', 'foo'),                   # Retries arg not a number
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'tags'),                             # Tags arg missing
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'tags', '{]'),                       # Tags arg malformed
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'priority'),                         # Priority arg missing
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'priority', 'foo'),                  # Priority arg malformed
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'depends'),                          # Depends arg missing
            (12345, 'foo', 'bar', 'whiz', '{}', 1,
                'depends', '{]')                     # Depends arg malformed
        ])

    def test_basic(self):
        '''We should be able to put and get jobs'''
        jid = self.lua('put', 12345, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(jid, 'jid')
        # Now we should be able to verify the data we get back
        self.assertEqual(self.lua('get', 12345, 'jid'), {
            'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {},
            'history': [{'q': 'queue', 'what': 'put', 'when': 12345}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'queue',
            'remaining': 5,
            'retries': 5,
            'state': 'waiting',
            'tags': {},
            'tracked': False,
            'worker': u'',
            'spawned_from_jid': False
        })

    def test_data_as_array(self):
        '''We should be able to provide an array as data'''
        # In particular, an empty array should be acceptable, and /not/
        # transformed into a dictionary when it returns
        self.lua('put', 12345, 'worker', 'queue', 'jid', 'klass', [], 0)
        self.assertEqual(self.lua('get', 12345, 'jid')['data'], '[]')

    def test_put_delay(self):
        '''When we put a job with a delay, it's reflected in its data'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 1)
        self.assertEqual(self.lua('get', 0, 'jid')['state'], 'scheduled')
        # After the delay, we should be able to pop
        self.assertEqual(self.lua('pop', 0, 'queue', 'worker', 10), {})
        self.assertEqual(len(self.lua('pop', 2, 'queue', 'worker', 10)), 1)

    def test_put_retries(self):
        '''Reflects changes to 'retries' '''
        self.lua('put', 12345, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 2)
        self.assertEqual(self.lua('get', 12345, 'jid')['retries'], 2)
        self.assertEqual(self.lua('get', 12345, 'jid')['remaining'], 2)

    def test_put_tags(self):
        '''When we put a job with tags, it's reflected in its data'''
        self.lua('put', 12345, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.assertEqual(self.lua('get', 12345, 'jid')['tags'], ['foo'])

    def test_put_priority(self):
        '''When we put a job with priority, it's reflected in its data'''
        self.lua('put', 12345, 'worker', 'queue', 'jid', 'klass', {}, 0, 'priority', 1)
        self.assertEqual(self.lua('get', 12345, 'jid')['priority'], 1)

    def test_put_depends(self):
        '''Dependencies are reflected in job data'''
        self.lua('put', 12345, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 12345, 'worker', 'queue', 'b', 'klass', {}, 0, 'depends', ['a'])
        self.assertEqual(self.lua('get', 12345, 'a')['dependents'], ['b'])
        self.assertEqual(self.lua('get', 12345, 'b')['dependencies'], ['a'])
        self.assertEqual(self.lua('get', 12345, 'b')['state'], 'depends')

    def test_put_depends_with_delay(self):
        '''When we put a job with a depends and a delay it is reflected in the job data'''
        self.lua('put', 12345, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 12345, 'worker', 'queue', 'b', 'klass', {}, 1, 'depends', ['a'])
        self.assertEqual(self.lua('get', 12345, 'a')['dependents'], ['b'])
        self.assertEqual(self.lua('get', 12345, 'b')['dependencies'], ['a'])
        self.assertEqual(self.lua('get', 12345, 'b')['state'], 'depends')

    def test_move(self):
        '''Move is described in terms of puts.'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {'foo': 'bar'}, 0)
        self.lua('put', 0, 'worker', 'other', 'jid', 'klass', {'foo': 'bar'}, 0)
        self.assertEqual(self.lua('get', 1, 'jid'), {
            'data': '{"foo": "bar"}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {},
            'history': [
                {'q': 'queue', 'what': 'put', 'when': 0},
                {'q': 'other', 'what': 'put', 'when': 0}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'other',
            'remaining': 5,
            'retries': 5,
            'state': 'waiting',
            'tags': {},
            'tracked': False,
            'worker': u'', 
            'spawned_from_jid': False})

    def test_move_update(self):
        '''When moving, ensure data's only changed when overridden'''
        for key, value, update in [
            ('priority', 1, 2),
            ('tags', ['foo'], ['bar']),
            ('retries', 2, 3)]:
            # First, when not overriding the value, it should stay the sam3
            # even after moving
            self.lua('put', 0, 'worker', 'queue', key, 'klass', {}, 0, key, value)
            self.lua('put', 0, 'worker', 'other', key, 'klass', {}, 0)
            self.assertEqual(self.lua('get', 0, key)[key], value)
            # But if we override it, it should be updated
            self.lua('put', 0, 'worker', 'queue', key, 'klass', {}, 0, key, update)
            self.assertEqual(self.lua('get', 0, key)[key], update)

        # Updating dependecies has to be special-cased a little bit. Without
        # overriding dependencies, they should be carried through the move
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'queue', 'c', 'klass', {}, 0, 'depends', ['a'])
        self.lua('put', 0, 'worker', 'other', 'c', 'klass', {}, 0)
        self.assertEqual(self.lua('get', 0, 'a')['dependents'], ['c'])
        self.assertEqual(self.lua('get', 0, 'b')['dependents'], {})
        self.assertEqual(self.lua('get', 0, 'c')['dependencies'], ['a'])
        # But if we move and update depends, then it should correctly reflect
        self.lua('put', 0, 'worker', 'queue', 'c', 'klass', {}, 0, 'depends', ['b'])
        self.assertEqual(self.lua('get', 0, 'a')['dependents'], {})
        self.assertEqual(self.lua('get', 0, 'b')['dependents'], ['c'])
        self.assertEqual(self.lua('get', 0, 'c')['dependencies'], ['b'])


class TestPeek(TestQless):
    '''Test peeking jobs'''
    # For reference:
    #
    #   QlessAPI.peek = function(now, queue, count)
    def test_malformed(self):
        '''Enumerate all the ways in which the input can be malformed'''
        self.assertMalformed(self.lua, [
            ('peek', 12345,),                         # No queue provided
            ('peek', 12345, 'foo'),                   # No count provided
            ('peek', 12345, 'foo', 'number'),         # Count arg malformed
        ])

    def test_basic(self):
        '''Can peek at a single waiting job'''
        # No jobs for an empty queue
        self.assertEqual(self.lua('peek', 0, 'foo', 10), {})
        self.lua('put', 0, 'worker', 'foo', 'jid', 'klass', {}, 0)
        # And now we should see a single job
        self.assertEqual(self.lua('peek', 1, 'foo', 10), [{
            'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 0,
            'failure': {},
            'history': [{'q': 'foo', 'what': 'put', 'when': 0}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'foo',
            'remaining': 5,
            'retries': 5,
            'state': 'waiting',
            'tags': {},
            'tracked': False,
            'worker': u'',
            'spawned_from_jid': False
        }])
        # With several jobs in the queue, we should be able to see more
        self.lua('put', 2, 'worker', 'foo', 'jid2', 'klass', {}, 0)
        self.assertEqual([o['jid'] for o in self.lua('peek', 3, 'foo', 10)], [
            'jid', 'jid2'])

    def test_priority(self):
        '''Peeking honors job priorities'''
        # We'll inserts some jobs with different priorities
        for jid in xrange(-10, 10):
            self.lua(
                'put', 0, 'worker', 'queue', jid, 'klass', {}, 0, 'priority', jid)

        # Peek at the jobs, and they should be in the right order
        jids = [job['jid'] for job in self.lua('peek', 1, 'queue', 100)]
        self.assertEqual(jids, map(str, range(9, -11, -1)))

    def test_time_order(self):
        '''Honor the time that jobs were put, priority constant'''
        # Put 100 jobs on with different times
        for time in xrange(100):
            self.lua('put', time, 'worker', 'queue', time, 'klass', {}, 0)
        jids = [job['jid'] for job in self.lua('peek', 200, 'queue', 100)]
        self.assertEqual(jids, map(str, range(100)))

    def test_move(self):
        '''When we move a job, it should be visible in the new, not old'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'other', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('peek', 1, 'queue', 10), {})
        self.assertEqual(self.lua('peek', 1, 'other', 10)[0]['jid'], 'jid')

    def test_recurring(self):
        '''We can peek at recurring jobs'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 10, 0)
        self.assertEqual(len(self.lua('peek', 99, 'queue', 100)), 10)

    def test_priority_update(self):
        '''We can change a job's priority'''
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0, 'priority', 0)
        self.lua('put', 0, 'worker', 'queue', 'b', 'klass', {}, 0, 'priority', 1)
        self.assertEqual(['b', 'a'],
            [j['jid'] for j in self.lua('peek', 0, 'queue', 100)])
        self.lua('priority', 0, 'a', 2)
        self.assertEqual(['a', 'b'],
            [j['jid'] for j in self.lua('peek', 0, 'queue', 100)])


class TestPop(TestQless):
    '''Test popping jobs'''
    # For reference:
    #
    #   QlessAPI.pop = function(now, queue, worker, count)
    def test_malformed(self):
        '''Enumerate all the ways this can be malformed'''
        self.assertMalformed(self.lua, [
            ('pop', 12345,),                              # No queue provided
            ('pop', 12345, 'queue'),                      # No worker provided
            ('pop', 12345, 'queue', 'worker'),            # No count provided
            ('pop', 12345, 'queue', 'worker', 'number'),  # Malformed count
        ])

    def test_basic(self):
        '''Pop some jobs in a simple way'''
        # If the queue is empty, you get no jobs
        self.assertEqual(self.lua('pop', 0, 'queue', 'worker', 10), {})
        # With job put, we can get one back
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('pop', 1, 'queue', 'worker', 1), [{
            'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 61,
            'failure': {},
            'history': [{'q': 'queue', 'what': 'put', 'when': 0},
                {'what': 'popped', 'when': 1, 'worker': 'worker'}],
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'queue',
            'remaining': 5,
            'retries': 5,
            'state': 'running',
            'tags': {},
            'tracked': False,
            'worker': 'worker',
            'spawned_from_jid': False}])

    def test_pop_many(self):
        '''We should be able to pop off many jobs'''
        for jid in range(10):
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
        # This should only pop the first 7
        self.assertEqual(
            [job['jid'] for job in self.lua('pop', 100, 'queue', 'worker', 7)],
            map(str, range(7)))
        # This should only leave 3 left
        self.assertEqual(
            [job['jid'] for job in self.lua('pop', 100, 'queue', 'worker', 10)],
            map(str, range(7, 10)))

    def test_priority(self):
        '''Popping should honor priority'''
        # We'll inserts some jobs with different priorities
        for jid in xrange(-10, 10):
            self.lua(
                'put', 0, 'worker', 'queue', jid, 'klass', {}, 0, 'priority', jid)

        # Peek at the jobs, and they should be in the right order
        jids = [job['jid'] for job in self.lua('pop', 1, 'queue', 'worker', 100)]
        self.assertEqual(jids, map(str, range(9, -11, -1)))

    def test_time_order(self):
        '''Honor the time jobs were inserted, priority held constant'''
        # Put 100 jobs on with different times
        for time in xrange(100):
            self.lua('put', time, 'worker', 'queue', time, 'klass', {}, 0)
        jids = [job['jid'] for job in self.lua('pop', 200, 'queue', 'worker', 100)]
        self.assertEqual(jids, map(str, range(100)))

    def test_move(self):
        '''When we move a job, it should be visible in the new, not old'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('put', 0, 'worker', 'other', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('pop', 1, 'queue', 'worker', 10), {})
        self.assertEqual(self.lua('pop', 1, 'other', 'worker', 10)[0]['jid'], 'jid')

    def test_max_concurrency(self):
        '''We can control the maxinum number of jobs available in a queue'''
        self.lua('config.set', 0, 'queue-max-concurrency', 5)
        for jid in xrange(10):
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
        self.assertEqual(len(self.lua('pop', 10, 'queue', 'worker', 10)), 5)
        # But as we complete the jobs, we can pop more
        for jid in xrange(5):
            self.lua('complete', 10, jid, 'worker', 'queue', {})
            self.assertEqual(
                len(self.lua('pop', 10, 'queue', 'worker', 10)), 1)

    def test_reduce_max_concurrency(self):
        '''We can reduce max_concurrency at any time'''
        # We'll put and pop a bunch of jobs, then restruct concurrency and
        # validate that jobs can't be popped until we dip below that level
        for jid in xrange(100):
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0)
        self.lua('pop', 100, 'queue', 'worker', 10)
        self.lua('config.set', 100, 'queue-max-concurrency', 5)
        for jid in xrange(6):
            self.assertEqual(
                len(self.lua('pop', 100, 'queue', 'worker', 10)), 0)
            self.lua('complete', 100, jid, 'worker', 'queue', {})
        # And now we should be able to start popping jobs
        self.assertEqual(
            len(self.lua('pop', 100, 'queue', 'worker', 10)), 1)

    def test_stalled_max_concurrency(self):
        '''Stalled jobs can still be popped with max concurrency'''
        self.lua('config.set', 0, 'queue-max-concurrency', 1)
        self.lua('config.set', 0, 'grace-period', 0)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 5)
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        job = self.lua('pop', job['expires'] + 10, 'queue', 'worker', 10)[0]
        self.assertEqual(job['jid'], 'jid')
        self.assertEqual(job['remaining'], 4)

    def test_fail_max_concurrency(self):
        '''Failing a job makes space for a job in a queue with concurrency'''
        self.lua('config.set', 0, 'queue-max-concurrency', 1)
        self.lua('put', 0, 'worker', 'queue', 'a', 'klass', {}, 0)
        self.lua('put', 1, 'worker', 'queue', 'b', 'klass', {}, 0)
        self.lua('pop', 2, 'queue', 'worker', 10)
        self.lua('fail', 3, 'a', 'worker', 'group', 'message', {})
        job = self.lua('pop', 4, 'queue', 'worker', 10)[0]
        self.assertEqual(job['jid'], 'b')

########NEW FILE########
__FILENAME__ = test_recurring
'''Tests for recurring jobs'''

from common import TestQless


class TestRecurring(TestQless):
    '''Tests for recurring jobs'''
    def test_malformed(self):
        '''Enumerate all the malformed possibilities'''
        self.assertMalformed(self.lua, [
            ('recur', 0),
            ('recur', 0, 'queue'),
            ('recur', 0, 'queue', 'jid'),
            ('recur', 0, 'queue', 'jid', 'klass'),
            ('recur', 0, 'queue', 'jid', 'klass', {}),
            ('recur', 0, 'queue', 'jid', 'klass', '[}'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'foo'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 'foo'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 'foo'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'tags'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'tags', '[}'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'priority'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'priority', 'foo'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'retries'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'retries', 'foo'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'backlog'),
            ('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
                'backlog', 'foo'),
        ])

        # In order for these tests to work, there must be a job
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertMalformed(self.lua, [
            ('recur.update', 0, 'jid', 'priority'),
            ('recur.update', 0, 'jid', 'priority', 'foo'),
            ('recur.update', 0, 'jid', 'interval'),
            ('recur.update', 0, 'jid', 'interval', 'foo'),
            ('recur.update', 0, 'jid', 'retries'),
            ('recur.update', 0, 'jid', 'retries', 'foo'),
            ('recur.update', 0, 'jid', 'data'),
            ('recur.update', 0, 'jid', 'data', '[}'),
            ('recur.update', 0, 'jid', 'klass'),
            ('recur.update', 0, 'jid', 'queue'),
            ('recur.update', 0, 'jid', 'backlog'),
            ('recur.update', 0, 'jid', 'backlog', 'foo')
        ])

    def test_basic(self):
        '''Simple recurring jobs'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        # Pop off the first recurring job
        popped = self.lua('pop', 0, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 1)
        self.assertEqual(popped[0]['jid'], 'jid-1')
        self.assertEqual(popped[0]['spawned_from_jid'], 'jid')

        # If we wait 59 seconds, there won't be a job, but at 60, yes
        popped = self.lua('pop', 59, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 0)
        popped = self.lua('pop', 61, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 1)
        self.assertEqual(popped[0]['jid'], 'jid-2')
        self.assertEqual(popped[0]['spawned_from_jid'], 'jid')

    def test_offset(self):
        '''We can set an offset from now for jobs to recur on'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 10)
        # There shouldn't be any jobs available just yet
        popped = self.lua('pop', 9, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 0)
        popped = self.lua('pop', 11, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 1)
        self.assertEqual(popped[0]['jid'], 'jid-1')

        # And now it recurs normally
        popped = self.lua('pop', 69, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 0)
        popped = self.lua('pop', 71, 'queue', 'worker', 10)
        self.assertEqual(len(popped), 1)
        self.assertEqual(popped[0]['jid'], 'jid-2')

    def test_tags(self):
        '''Recurring jobs can be given tags'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
            'tags', ['foo', 'bar'])
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        self.assertEqual(job['tags'], ['foo', 'bar'])

    def test_priority(self):
        '''Recurring jobs can be given priority'''
        # Put one job with low priority
        self.lua('put', 0, 'worker', 'queue', 'low', 'klass', {}, 0, 'priority', 0)
        self.lua('recur', 0, 'queue', 'high', 'klass', {},
            'interval', 60, 0, 'priority', 10)
        jobs = self.lua('pop', 0, 'queue', 'worker', 10)
        # We should see high-1 and then low
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]['jid'], 'high-1')
        self.assertEqual(jobs[0]['priority'], 10)
        self.assertEqual(jobs[1]['jid'], 'low')

    def test_retries(self):
        '''Recurring job retries are passed on to child jobs'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {},
            'interval', 60, 0, 'retries', 2)
        job = self.lua('pop', 0, 'queue', 'worker', 10)[0]
        self.assertEqual(job['retries'], 2)
        self.assertEqual(job['remaining'], 2)

    def test_backlog(self):
        '''Recurring jobs can limit the number of jobs they spawn'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {},
            'interval', 60, 0, 'backlog', 1)
        jobs = self.lua('pop', 600, 'queue', 'worker', 10)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]['jid'], 'jid-1')

    def test_get(self):
        '''We should be able to get recurring jobs'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(self.lua('recur.get', 0, 'jid'), {
            'backlog': 0,
            'count': 0,
            'data': '{}',
            'interval': 60,
            'jid': 'jid',
            'klass': 'klass',
            'priority': 0,
            'queue': 'queue',
            'retries': 0,
            'state': 'recur',
            'tags': {}
        })

    def test_update_priority(self):
        '''We need to be able to update recurring job attributes'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['priority'], 0)
        self.lua('recur.update', 0, 'jid', 'priority', 10)
        self.assertEqual(
            self.lua('pop', 60, 'queue', 'worker', 10)[0]['priority'], 10)

    def test_update_interval(self):
        '''We need to be able to update the interval'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(len(self.lua('pop', 0, 'queue', 'worker', 10)), 1)
        self.lua('recur.update', 0, 'jid', 'interval', 10)
        self.assertEqual(len(self.lua('pop', 60, 'queue', 'worker', 10)), 6)

    def test_update_retries(self):
        '''We need to be able to update the retries'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {},
            'interval', 60, 0, 'retries', 5)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['retries'], 5)
        self.lua('recur.update', 0, 'jid', 'retries', 2)
        self.assertEqual(
            self.lua('pop', 60, 'queue', 'worker', 10)[0]['retries'], 2)

    def test_update_data(self):
        '''We need to be able to update the data'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60,  0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['data'], '{}')
        self.lua('recur.update', 0, 'jid', 'data', {'foo': 'bar'})
        self.assertEqual(self.lua(
            'pop', 60, 'queue', 'worker', 10)[0]['data'], '{"foo": "bar"}')

    def test_update_klass(self):
        '''We need to be able to update klass'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['klass'], 'klass')
        self.lua('recur.update', 0, 'jid', 'klass', 'class')
        self.assertEqual(
            self.lua('pop', 60, 'queue', 'worker', 10)[0]['klass'], 'class')

    def test_update_queue(self):
        '''Need to be able to move the recurring job to another queue'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(len(self.lua('pop', 0, 'queue', 'worker', 10)), 1)
        self.lua('recur.update', 0, 'jid', 'queue', 'other')
        # No longer available in the old queue
        self.assertEqual(len(self.lua('pop', 60, 'queue', 'worker', 10)), 0)
        self.assertEqual(len(self.lua('pop', 60, 'other', 'worker', 10)), 1)

    def test_unrecur(self):
        '''Stop a recurring job'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(len(self.lua('pop', 0, 'queue', 'worker', 10)), 1)
        self.lua('unrecur', 0, 'jid')
        self.assertEqual(len(self.lua('pop', 60, 'queue', 'worker', 10)), 0)

    def test_empty_array_data(self):
        '''Empty array of data is preserved'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', [], 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['data'], '[]')

    def test_multiple(self):
        '''If multiple intervals have passed, then returns multiple jobs'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            len(self.lua('pop', 599, 'queue', 'worker', 10)), 10)

    def test_tag(self):
        '''We should be able to add tags to jobs'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['tags'], {})
        self.lua('recur.tag', 0, 'jid', 'foo')
        self.assertEqual(
            self.lua('pop', 60, 'queue', 'worker', 10)[0]['tags'], ['foo'])

    def test_untag(self):
        '''We should be able to remove tags from a job'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {},
            'interval', 60, 0, 'tags', ['foo'])
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['tags'], ['foo'])
        self.lua('recur.untag', 0, 'jid', 'foo')
        self.assertEqual(
            self.lua('pop', 60, 'queue', 'worker', 10)[0]['tags'], {})

    def test_rerecur(self):
        '''Don't reset the jid counter when re-recurring a job'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['jid'], 'jid-1')
        # Re-recur it
        self.lua('recur', 60, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 60, 'queue', 'worker', 10)[0]['jid'], 'jid-2')

    def test_rerecur_attributes(self):
        '''Re-recurring a job updates its attributes'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0,
            'priority', 10, 'tags', ['foo'], 'retries', 2)
        self.assertEqual(self.lua('pop', 0, 'queue', 'worker', 10)[0], {
            'data': '{}',
            'dependencies': {},
            'dependents': {},
            'expires': 60,
            'failure': {},
            'history': [{'q': 'queue', 'what': 'put', 'when': 0},
                        {'what': 'popped', 'when': 0, 'worker': 'worker'}],
            'jid': 'jid-1',
            'klass': 'klass',
            'priority': 10,
            'queue': 'queue',
            'remaining': 2,
            'retries': 2,
            'state': 'running',
            'tags': ['foo'],
            'tracked': False,
            'worker': 'worker',
            'spawned_from_jid': 'jid'})
        self.lua('recur', 60, 'queue', 'jid', 'class', {'foo': 'bar'},
            'interval', 10, 0, 'priority', 5, 'tags', ['bar'], 'retries', 5)
        self.assertEqual(self.lua('pop', 60, 'queue', 'worker', 10)[0], {
            'data': '{"foo": "bar"}',
            'dependencies': {},
            'dependents': {},
            'expires': 120,
            'failure': {},
            'history': [{'q': 'queue', 'what': 'put', 'when': 60},
                        {'what': 'popped', 'when': 60, 'worker': 'worker'}],
            'jid': 'jid-2',
            'klass': 'class',
            'priority': 5,
            'queue': 'queue',
            'remaining': 5,
            'retries': 5,
            'state': 'running',
            'tags': ['bar'],
            'tracked': False,
            'worker': 'worker',
            'spawned_from_jid': 'jid'})

    def test_rerecur_move(self):
        '''Re-recurring a job in a new queue works like a move'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 0, 'queue', 'worker', 10)[0]['jid'], 'jid-1')
        self.lua('recur', 60, 'other', 'jid', 'klass', {}, 'interval', 60, 0)
        self.assertEqual(
            self.lua('pop', 60, 'other', 'worker', 10)[0]['jid'], 'jid-2')

    def test_history(self):
        '''Spawned jobs are 'put' at the time they would have been scheduled'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {}, 'interval', 60, 0)
        jobs = self.lua('pop', 599, 'queue', 'worker', 100)
        times = [job['history'][0]['when'] for job in jobs]
        self.assertEqual(
            times, [0, 60, 120, 180, 240, 300, 360, 420, 480, 540])

########NEW FILE########
__FILENAME__ = test_stats
'''Test the stats we keep about queues'''

from common import TestQless


class TestStats(TestQless):
    '''Tests the stats we keep about queues'''
    def test_malformed(self):
        '''Enumerate all the ways to send malformed requests'''
        self.assertMalformed(self.lua, [
            ('stats', 0),
            ('stats', 0, 'queue'),
            ('stats', 0, 'queue', 'foo')
        ])

    def test_wait(self):
        '''It correctly tracks wait times'''
        stats = self.lua('stats', 0, 'queue', 0)
        self.assertEqual(stats['wait']['count'], 0)
        self.assertEqual(stats['run']['count'], 0)

        # Put in jobs all at the same time, and then pop them at different
        # times to ensure that we know stats about how long they've waited
        jids = map(str, range(20))
        for jid in jids:
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
        for jid in jids:
            self.lua('pop', jid, 'queue', 'worker', 1)

        stats = self.lua('stats', 0, 'queue', 0)
        self.assertEqual(stats['wait']['count'], 20)
        self.assertAlmostEqual(stats['wait']['mean'], 9.5)
        self.assertAlmostEqual(stats['wait']['std'], 5.916079783099)
        self.assertEqual(stats['wait']['histogram'][0:20], [1] * 20)
        self.assertEqual(sum(stats['wait']['histogram']), 20)

    def test_completion(self):
        '''It correctly tracks job run times'''
        # Put in a bunch of jobs and pop them all at the same time, and then
        # we'll complete them at different times and check the computed stats
        jids = map(str, range(20))
        for jid in jids:
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
            self.lua('pop', 0, 'queue', 'worker', 1)
        for jid in jids:
            self.lua('complete', jid, jid, 'worker', 'queue', {})

        stats = self.lua('stats', 0, 'queue', 0)
        self.assertEqual(stats['run']['count'], 20)
        self.assertAlmostEqual(stats['run']['mean'], 9.5)
        self.assertAlmostEqual(stats['run']['std'], 5.916079783099)
        self.assertEqual(stats['run']['histogram'][0:20], [1] * 20)
        self.assertEqual(sum(stats['run']['histogram']), 20)

    def test_failed(self):
        '''It correctly tracks failed jobs and failures'''
        # The distinction here between 'failed' and 'failure' is that 'failed'
        # is the number of jobs that are currently failed, as opposed to the
        # number of times a job has failed in that queue
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 1)
        self.lua('fail', 0, 'jid', 'worker', 'group', 'message', {})
        stats = self.lua('stats', 0, 'queue', 0)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['failures'], 1)

        # If we put the job back in a queue, we don't see any failed jobs,
        # but we still see a failure
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        stats = self.lua('stats', 0, 'queue', 0)
        self.assertEqual(stats['failed'], 0)
        self.assertEqual(stats['failures'], 1)

    def test_failed_cancel(self):
        '''If we fail a job, and then cancel it, stats reflects 0 failed job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 1)
        self.lua('fail', 0, 'jid', 'worker', 'group', 'message', {})
        self.lua('cancel', 0, 'jid')
        stats = self.lua('stats', 0, 'queue', 0)
        self.assertEqual(stats['failed'], 0)
        self.assertEqual(stats['failures'], 1)

    def test_retries(self):
        '''It correctly tracks retries in a queue'''
        self.lua('config.set', 0, 'heartbeat', '-10')
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 1)
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['retries'], 0)
        self.lua('pop', 0, 'queue', 'worker', 1)
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['retries'], 1)

    def test_original_day(self):
        '''It updates stats for the original day of stats'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 1)
        self.lua('fail', 0, 'jid', 'worker', 'group', 'message', {})
        # Put it somehwere 1.5 days later
        self.lua('put', 129600, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['failed'], 0)
        self.assertEqual(self.lua('stats', 0, 'queue', 129600)['failed'], 0)

    def test_failed_retries(self):
        '''It updates stats for jobs failed from retries'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('retry', 3, 'jid', 'queue', 'worker')
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['failed'], 1)
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['failures'], 1)

    def test_failed_pop_retries(self):
        '''Increment the count failed jobs when job fail from retries'''
        '''Can cancel job that has been failed from retries through pop'''
        self.lua('config.set', 0, 'heartbeat', -10)
        self.lua('config.set', 0, 'grace-period', 0)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'retries', 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('pop', 2, 'queue', 'worker', 10)
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['failed'], 1)
        self.assertEqual(self.lua('stats', 0, 'queue', 0)['failures'], 1)

########NEW FILE########
__FILENAME__ = test_tag
'''Test our tagging functionality'''

from common import TestQless


class TestTag(TestQless):
    '''Test our tagging functionality'''
    #
    # QlessAPI.tag = function(now, command, ...)
    #     return cjson.encode(Qless.tag(now, command, unpack(arg)))
    # end
    def test_malformed(self):
        '''Enumerate all the ways it could be malformed'''
        self.assertMalformed(self.lua, [
            ('tag', 0),
            ('tag', 0, 'add'),
            ('tag', 0, 'remove'),
            ('tag', 0, 'get'),
            ('tag', 0, 'get', 'foo', 'bar'),
            ('tag', 0, 'get', 'foo', 0, 'bar'),
            ('tag', 0, 'top', 'bar'),
            ('tag', 0, 'top', 0, 'bar'),
            ('tag', 0, 'foo')
        ])

    def test_add(self):
        '''Add a tag'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('tag', 0, 'add', 'jid', 'foo')
        self.assertEqual(self.lua('get', 0, 'jid')['tags'], ['foo'])

    def test_remove(self):
        '''Remove a tag'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.lua('tag', 0, 'remove', 'jid', 'foo')
        self.assertEqual(self.lua('get', 0, 'jid')['tags'], {})

    def test_add_existing(self):
        '''We shouldn't double-add tags that already exist for the job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.lua('tag', 0, 'add', 'jid', 'foo')
        self.assertEqual(self.lua('get', 0, 'jid')['tags'], ['foo'])

    def test_remove_nonexistent(self):
        '''Removing a nonexistent tag from a job is ok'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.lua('tag', 0, 'remove', 'jid', 'bar')
        self.assertEqual(self.lua('get', 0, 'jid')['tags'], ['foo'])

    def test_add_multiple(self):
        '''Adding the same tag twice at the same time yields no duplicates'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('tag', 0, 'add', 'jid', 'foo', 'foo', 'foo')
        self.assertEqual(self.lua('get', 0, 'jid')['tags'], ['foo'])

    def test_get(self):
        '''Should be able to get jobs taggs with a particular tag'''
        self.lua('put', 0, 'worker', 'queue', 'foo', 'klass', {}, 0,
            'tags', ['foo', 'both'])
        self.lua('put', 0, 'worker', 'queue', 'bar', 'klass', {}, 0,
            'tags', ['bar', 'both'])
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], ['foo'])
        self.assertEqual(
            self.lua('tag', 0, 'get', 'bar', 0, 10)['jobs'], ['bar'])
        self.assertEqual(
            self.lua('tag', 0, 'get', 'both', 0, 10)['jobs'], ['bar', 'foo'])

    def test_get_add(self):
        '''When adding a tag, it should be available for searching'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], {})
        self.lua('tag', 0, 'add', 'jid', 'foo')
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], ['jid'])

    def test_order(self):
        '''It should preserve the order of the tags'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        tags = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for tag in tags:
            self.lua('tag', 0, 'add', 'jid', tag)
            found = self.lua('get', 0, 'jid')['tags']
            self.assertEqual(found, sorted(found))
        # And now remove them one at a time
        import random
        for tag in random.sample(tags, len(tags)):
            self.lua('tag', 0, 'remove', 'jid', tag)
            found = self.lua('get', 0, 'jid')['tags']
            self.assertEqual(list(found), sorted(found))

    def test_cancel(self):
        '''When a job is canceled, it's not found in tags'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], ['jid'])
        self.lua('cancel', 0, 'jid')
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], {})

    def test_expired_jobs(self):
        '''When a job expires, it's removed from its tags'''
        self.lua('config.set', 0, 'jobs-history', 100)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        self.assertEqual(
            self.lua('tag', 99, 'get', 'foo', 0, 10)['jobs'], ['jid'])
        # We now need another job to complete to expire this job
        self.lua('put', 101, 'worker', 'queue', 'foo', 'klass', {}, 0)
        self.lua('pop', 101, 'queue', 'worker', 10)
        self.lua('complete', 101, 'foo', 'worker', 'queue', {})
        self.assertEqual(
            self.lua('tag', 101, 'get', 'foo', 0, 10)['jobs'], {})

    def test_expired_count_jobs(self):
        '''When a job expires from jobs-history-count, remove from its tags'''
        self.lua('config.set', 0, 'jobs-history-count', 1)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0, 'tags', ['foo'])
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], ['jid'])
        # We now need another job to complete to expire this job
        self.lua('put', 1, 'worker', 'queue', 'foo', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.lua('complete', 1, 'foo', 'worker', 'queue', {})
        self.assertEqual(
            self.lua('tag', 1, 'get', 'foo', 0, 10)['jobs'], {})

    def test_top(self):
        '''Ensure that we can find the most common tags'''
        for tag in range(10):
            self.lua('put', 0, 'worker', 'queue', tag, 'klass', {}, 0,
                'tags', range(tag, 10))
        self.assertEqual(self.lua('tag', 0, 'top', 0, 20),
            map(str, reversed(range(1, 10))))

    def test_recurring(self):
        '''Ensure that jobs spawned from recurring jobs are tagged'''
        self.lua('recur', 0, 'queue', 'jid', 'klass', {},
            'interval', 60, 0, 'tags', ['foo'])
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.assertEqual(
            self.lua('tag', 0, 'get', 'foo', 0, 10)['jobs'], ['jid-1'])

    def test_pagination_get(self):
        '''Pagination should work for tag.get'''
        jids = map(str, range(100))
        for jid in jids:
            self.lua('put', jid, 'worker', 'queue', jid, 'klass', {}, 0, 'tags', ['foo'])
        # Get two pages and ensure they're what we expect
        self.assertEqual(
            self.lua('tag', 100, 'get', 'foo',  0, 50)['jobs'], jids[:50])
        self.assertEqual(
            self.lua('tag', 100, 'get', 'foo', 50, 50)['jobs'], jids[50:])

    def test_pagination_top(self):
        '''Pagination should work for tag.top'''
        jids = map(str, range(10))
        for jid in jids:
            for suffix in map(str, range(int(jid) + 5)):
                self.lua('put', jid, 'worker', 'queue',
                    jid + '.' + suffix, 'klass', {}, 0, 'tags', [jid])
        # Get two pages and ensure they're what we expect
        jids = list(reversed(jids))
        self.assertEqual(
            self.lua('tag', 100, 'top', 0, 5), jids[:5])
        self.assertEqual(
            self.lua('tag', 100, 'top', 5, 5), jids[5:])

########NEW FILE########
__FILENAME__ = test_track
'''Test all the tracking'''

import redis
from common import TestQless


class TestTrack(TestQless):
    '''Test our tracking abilities'''
    def test_malfomed(self):
        '''Enumerate all the ways that it can be malformed'''
        self.assertMalformed(self.lua, [
            ('track', 0, 'track'),
            ('track', 0, 'untrack'),
            ('track', 0, 'foo')
        ])

    def test_track(self):
        '''Can track a job and it appears in "track"'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        self.assertEqual(self.lua('track', 0), {
            'jobs': [{
                'retries': 5,
                'jid': 'jid',
                'tracked': True,
                'tags': {},
                'worker': u'',
                'expires': 0,
                'priority': 0,
                'queue': 'queue',
                'failure': {},
                'state': 'waiting',
                'dependencies': {},
                'klass': 'klass',
                'dependents': {},
                'data': '{}',
                'remaining': 5,
                'spawned_from_jid': False,
                'history': [{
                    'q': 'queue', 'what': 'put', 'when': 0
                }]
            }], 'expired': {}})

    def test_untrack(self):
        '''We can stop tracking a job'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        self.lua('track', 0, 'untrack', 'jid')
        self.assertEqual(self.lua('track', 0), {'jobs': {}, 'expired': {}})

    def test_track_nonexistent(self):
        '''Tracking nonexistent jobs raises an error'''
        self.assertRaisesRegexp(redis.ResponseError, r'does not exist',
            self.lua, 'track', 0, 'track', 'jid')

    def test_jobs_tracked(self):
        '''Jobs know when they're tracked'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('track', 0, 'track', 'jid')
        self.assertEqual(self.lua('get', 0, 'jid')['tracked'], True)

    def test_jobs_untracked(self):
        '''Jobs know when they're not tracked'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('get', 0, 'jid')['tracked'], False)

########NEW FILE########
__FILENAME__ = test_worker
'''Tests about worker information'''

from common import TestQless


class TestWorker(TestQless):
    '''Test worker information API'''
    def setUp(self):
        TestQless.setUp(self)
        # No grace period
        self.lua('config.set', 0, 'grace-period', 0)

    def test_basic(self):
        '''Basic worker-level information'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('workers', 2, 'worker'), {
            'jobs': ['jid'],
            'stalled': {}
        })
        self.assertEqual(self.lua('workers', 2), [{
            'name': 'worker',
            'jobs': 1,
            'stalled': 0
        }])

    def test_stalled(self):
        '''We should be able to detect stalled jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 1, 'queue', 'worker', 10)[0]
        expires = job['expires'] + 10
        self.lua('peek', expires, 'queue', 10)
        self.assertEqual(self.lua('workers', expires, 'worker'), {
            'jobs': {},
            'stalled': ['jid']
        })
        self.assertEqual(self.lua('workers', expires), [{
            'name': 'worker',
            'jobs': 0,
            'stalled': 1
        }])

    def test_locks(self):
        '''When a lock is lost, removes the job from the worker's info'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        job = self.lua('pop', 1, 'queue', 'worker', 10)[0]
        self.assertEqual(self.lua('workers', 2, 'worker'), {
            'jobs': ['jid'],
            'stalled': {}
        })
        # Once it gets handed off to another worker, we shouldn't see any info
        # about that job from that worker
        expires = job['expires'] + 10
        self.lua('pop', expires, 'queue', 'another', 10)
        self.assertEqual(self.lua('workers', expires, 'worker'), {
            'jobs': {},
            'stalled': {}
        })

    def test_cancelled(self):
        '''Canceling a job removes it from the worker's stats'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('workers', 2, 'worker'), {
            'jobs': ['jid'],
            'stalled': {}
        })
        # And now, we'll cancel it, and it should disappear
        self.lua('cancel', 3, 'jid')
        self.assertEqual(self.lua('workers', 4, 'worker'), {
            'jobs': {},
            'stalled': {}
        })
        self.assertEqual(self.lua('workers', 4), [{
            'name': 'worker',
            'jobs': 0,
            'stalled': 0
        }])

    def test_failed(self):
        '''When a job fails, it should be removed from a worker's jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('workers', 2, 'worker'), {
            'jobs': ['jid'],
            'stalled': {}
        })
        self.lua('fail', 3, 'jid', 'worker', 'group', 'message', {})
        self.assertEqual(self.lua('workers', 4, 'worker'), {
            'jobs': {},
            'stalled': {}
        })
        self.assertEqual(self.lua('workers', 4), [{
            'name': 'worker',
            'jobs': 0,
            'stalled': 0
        }])

    def test_complete(self):
        '''When a job completes, it should be remove from the worker's jobs'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('workers', 2, 'worker'), {
            'jobs': ['jid'],
            'stalled': {}
        })
        self.lua('complete', 3, 'jid', 'worker', 'queue', {})
        self.assertEqual(self.lua('workers', 4, 'worker'), {
            'jobs': {},
            'stalled': {}
        })
        self.assertEqual(self.lua('workers', 4), [{
            'name': 'worker',
            'jobs': 0,
            'stalled': 0
        }])

    def test_put(self):
        '''When a job's put in another queue, remove it from the worker'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 1, 'queue', 'worker', 10)
        self.assertEqual(self.lua('workers', 2, 'worker'), {
            'jobs': ['jid'],
            'stalled': {}
        })
        self.lua('put', 3, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.assertEqual(self.lua('workers', 4, 'worker'), {
            'jobs': {},
            'stalled': {}
        })
        self.assertEqual(self.lua('workers', 4), [{
            'name': 'worker',
            'jobs': 0,
            'stalled': 0
        }])

    def test_reregister(self):
        '''We should be able to remove workers from the list of workers'''
        for jid in xrange(10):
            self.lua('put', 0, 'worker', 'queue', jid, 'klass', {}, 0)
        # And pop them from 10 different workers
        workers = map(str, range(10))
        for worker in workers:
            self.lua('pop', 1, 'queue', worker, 1)
        # And we'll deregister them each one at a time and ensure they are
        # indeed removed from our list
        for worker in workers:
            found = [w['name'] for w in self.lua('workers', 2)]
            self.assertTrue(worker in found)
            self.lua('worker.deregister', 2, worker)
            found = [w['name'] for w in self.lua('workers', 2)]
            self.assertFalse(worker in found)

    def test_expiration(self):
        '''After a certain amount of time, inactive workers expire'''
        # Set the maximum worker age
        self.lua('config.set', 0, 'max-worker-age', 3600)
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua('complete', 0, 'jid', 'worker', 'queue', {})
        # When we check on workers in a little while, it won't be listed
        self.assertEqual(self.lua('workers', 3600), {})

    def test_unregistered(self):
        '''If a worker is unknown, it should still be ok'''
        self.assertEqual(self.lua('workers', 3600, 'worker'), {
            'jobs': {},
            'stalled': {}
        })

    def test_retry_worker(self):
        '''When retried, it removes a job from the worker's data'''
        self.lua('put', 0, 'worker', 'queue', 'jid', 'klass', {}, 0)
        self.lua('pop', 0, 'queue', 'worker', 10)
        self.lua(
            'retry', 0, 'jid', 'queue', 'worker', 0)
        self.assertEqual(self.lua('workers', 3600, 'worker'), {
            'jobs': {},
            'stalled': {}
        })

########NEW FILE########
