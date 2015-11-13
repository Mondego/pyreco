__FILENAME__ = client
import collections
from datetime import datetime, timedelta
import json
import logging
import numbers
import threading

from dateutil.tz import tzutc
import requests

from stats import Statistics
from errors import ApiError
from utils import guess_timezone, DatetimeSerializer

import options


logging_enabled = True
logger = logging.getLogger('analytics')


def log(level, *args, **kwargs):
    if logging_enabled:
        method = getattr(logger, level)
        method(*args, **kwargs)


def package_exception(client, data, e):
    log('warn', 'Segment.io request error', exc_info=True)
    client._on_failed_flush(data, e)


def package_response(client, data, response):
    # TODO: reduce the complexity (mccabe)
    if response.status_code == 200:
        client._on_successful_flush(data, response)
    elif response.status_code == 400:
        content = response.text
        try:
            body = json.loads(content)

            code = 'bad_request'
            message = 'Bad request'

            if 'error' in body:
                error = body.error

                if 'code' in error:
                    code = error['code']

                if 'message' in error:
                    message = error['message']

            client._on_failed_flush(data, ApiError(code, message))

        except Exception:
            client._on_failed_flush(data, ApiError('Bad Request', content))
    else:
        client._on_failed_flush(data,
                                ApiError(response.status_code, response.text))


def request(client, url, data):

    log('debug', 'Sending request to Segment.io ...')
    try:

        response = requests.post(url,
                                 data=json.dumps(data, cls=DatetimeSerializer),
                                 headers={'content-type': 'application/json'},
                                 timeout=client.timeout)

        log('debug', 'Finished Segment.io request.')

        package_response(client, data, response)

        return response.status_code == 200

    except requests.ConnectionError as e:
        package_exception(client, data, e)
    except requests.Timeout as e:
        package_exception(client, data, e)

    return False


class FlushThread(threading.Thread):

    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client

    def run(self):
        log('debug', 'Flushing thread running ...')

        self.client._sync_flush()

        log('debug', 'Flushing thread done.')


class Client(object):
    """The Client class is a batching asynchronous python wrapper over the
    Segment.io API.

    """

    def __init__(self, secret=None, log_level=logging.INFO, log=True,
                 flush_at=20, flush_after=timedelta(0, 10),
                 async=True, max_queue_size=10000, stats=Statistics(),
                 timeout=10, send=True):
        """Create a new instance of a analytics-python Client

        :param str secret: The Segment.io API secret
        :param logging.LOG_LEVEL log_level: The logging log level for the
        client talks to. Use log_level=logging.DEBUG to troubleshoot
        : param bool log: False to turn off logging completely, True by default
        : param int flush_at: Specicies after how many messages the client will
        flush to the server. Use flush_at=1 to disable batching
        : param datetime.timedelta flush_after: Specifies after how much time
        of no flushing that the server will flush. Used in conjunction with
        the flush_at size policy
        : param bool async: True to have the client flush to the server on
        another thread, therefore not blocking code (this is the default).
        False to enable blocking and making the request on the calling thread.
        : param float timeout: Number of seconds before timing out request to
        Segment.io
        : param bool send: True to send requests, False to not send. False to
        turn analytics off (for testing).
        """

        self.secret = secret

        self.queue = collections.deque()
        self.last_flushed = None

        if not log:
            # TODO: logging_enabled is assigned, but not used
            logging_enabled = False
            # effectively disables the logger
            logger.setLevel(logging.CRITICAL)
        else:
            logger.setLevel(log_level)

        self.async = async

        self.max_queue_size = max_queue_size
        self.max_flush_size = 50

        self.flush_at = flush_at
        self.flush_after = flush_after

        self.timeout = timeout

        self.stats = stats

        self.flush_lock = threading.Lock()
        self.flushing_thread = None

        self.send = send

        self.success_callbacks = []
        self.failure_callbacks = []

    def set_log_level(self, level):
        """Sets the log level for analytics-python

        :param logging.LOG_LEVEL level: The level at which analytics-python log
        should talk at
        """
        logger.setLevel(level)

    def _check_for_secret(self):
        if not self.secret:
            raise Exception('Please set analytics.secret before calling ' +
                            'identify or track.')

    def _coerce_unicode(self, cmplx):
        return unicode(cmplx)

    def _clean_list(self, l):
        return [self._clean(item) for item in l]

    def _clean_dict(self, d):
        data = {}
        for k, v in d.iteritems():
            try:
                data[k] = self._clean(v)
            except TypeError:
                log('warn', 'Dictionary values must be serializeable to ' +
                            'JSON "%s" value %s of type %s is unsupported.'
                            % (k, v, type(v)))
        return data

    def _clean(self, item):
        if isinstance(item, (str, unicode, int, long, float, bool,
                             numbers.Number, datetime)):
            return item
        elif isinstance(item, (set, list, tuple)):
            return self._clean_list(item)
        elif isinstance(item, dict):
            return self._clean_dict(item)
        else:
            return self._coerce_unicode(item)

    def on_success(self, callback):
        """
        Assign a callback to fire after a successful flush

        :param func callback: A callback that will be fired on a flush success
        """
        self.success_callbacks.append(callback)

    def on_failure(self, callback):
        """
        Assign a callback to fire after a failed flush

        :param func callback: A callback that will be fired on a failed flush
        """
        self.failure_callbacks.append(callback)

    def identify(self, user_id=None, traits={}, context={}, timestamp=None):
        """Identifying a user ties all of their actions to an id, and
        associates user traits to that id.

        :param str user_id: the user's id after they are logged in. It's the
        same id as which you would recognize a signed-in user in your system.

        : param dict traits: a dictionary with keys like subscriptionPlan or
        age. You only need to record a trait once, no need to send it again.
        Accepted value types are string, boolean, ints,, longs, and
        datetime.datetime.

        : param dict context: An optional dictionary with additional
        information thats related to the visit. Examples are userAgent, and IP
        address of the visitor.

        : param datetime.datetime timestamp: If this event happened in the
        past, the timestamp  can be used to designate when the identification
        happened.  Careful with this one,  if it just happened, leave it None.
        If you do choose to provide a timestamp, make sure it has a timezone.
        """

        self._check_for_secret()

        if not user_id:
            raise Exception('Must supply a user_id.')

        if traits is not None and not isinstance(traits, dict):
            raise Exception('Traits must be a dictionary.')

        if context is not None and not isinstance(context, dict):
            raise Exception('Context must be a dictionary.')

        if timestamp is None:
            timestamp = datetime.utcnow().replace(tzinfo=tzutc())
        elif not isinstance(timestamp, datetime):
            raise Exception('Timestamp must be a datetime object.')
        else:
            timestamp = guess_timezone(timestamp)

        cleaned_traits = self._clean(traits)

        action = {'userId':      user_id,
                  'traits':      cleaned_traits,
                  'context':     context,
                  'timestamp':   timestamp.isoformat(),
                  'action':      'identify'}

        context['library'] = 'analytics-python'

        if self._enqueue(action):
            self.stats.identifies += 1

    def track(self, user_id=None, event=None, properties={}, context={},
              timestamp=None):
        """Whenever a user triggers an event, you'll want to track it.

        :param str user_id:  the user's id after they are logged in. It's the
        same id as which you would recognize a signed-in user in your system.

        :param str event: The event name you are tracking. It is recommended
        that it is in human readable form. For example, "Bought T-Shirt"
        or "Started an exercise"

        :param dict properties: A dictionary with items that describe the
        event in more detail. This argument is optional, but highly recommended
        - you'll find these properties extremely useful later. Accepted value
        types are string, boolean, ints, doubles, longs, and datetime.datetime.

        :param dict context: An optional dictionary with additional information
        thats related to the visit. Examples are userAgent, and IP address
        of the visitor.

        :param datetime.datetime timestamp: If this event happened in the past,
        the timestamp   can be used to designate when the identification
        happened.  Careful with this one,  if it just happened, leave it None.
        If you do choose to provide a timestamp, make sure it has a timezone.

        """

        self._check_for_secret()

        if not user_id:
            raise Exception('Must supply a user_id.')

        if not event:
            raise Exception('Event is a required argument as a non-empty ' +
                            'string.')

        if properties is not None and not isinstance(properties, dict):
            raise Exception('Context must be a dictionary.')

        if context is not None and not isinstance(context, dict):
            raise Exception('Context must be a dictionary.')

        if timestamp is None:
            timestamp = datetime.utcnow().replace(tzinfo=tzutc())
        elif not isinstance(timestamp, datetime):
            raise Exception('Timestamp must be a datetime.datetime object.')
        else:
            timestamp = guess_timezone(timestamp)

        cleaned_properties = self._clean(properties)

        action = {'userId':       user_id,
                  'event':        event,
                  'context':      context,
                  'properties':   cleaned_properties,
                  'timestamp':    timestamp.isoformat(),
                  'action':       'track'}

        context['library'] = 'analytics-python'

        if self._enqueue(action):
            self.stats.tracks += 1

    def alias(self, from_id, to_id, context={}, timestamp=None):
        """Aliases an anonymous user into an identified user

        :param str from_id: the anonymous user's id before they are logged in

        :param str to_id: the identified user's id after they're logged in

        :param dict context: An optional dictionary with additional information
        thats related to the visit. Examples are userAgent, and IP address
        of the visitor.

        :param datetime.datetime timestamp: If this event happened in the past,
        the timestamp   can be used to designate when the identification
        happened.  Careful with this one,  if it just happened, leave it None.
        If you do choose to provide a timestamp, make sure it has a timezone.
        """

        self._check_for_secret()

        if not from_id:
            raise Exception('Must supply a from_id.')

        if not to_id:
            raise Exception('Must supply a to_id.')

        if context is not None and not isinstance(context, dict):
            raise Exception('Context must be a dictionary.')

        if timestamp is None:
            timestamp = datetime.utcnow().replace(tzinfo=tzutc())
        elif not isinstance(timestamp, datetime):
            raise Exception('Timestamp must be a datetime.datetime object.')
        else:
            timestamp = guess_timezone(timestamp)

        action = {'from':         from_id,
                  'to':           to_id,
                  'context':      context,
                  'timestamp':    timestamp.isoformat(),
                  'action':       'alias'}

        context['library'] = 'analytics-python'

        if self._enqueue(action):
            self.stats.aliases += 1

    def _should_flush(self):
        """ Determine whether we should sync """

        full = len(self.queue) >= self.flush_at
        stale = self.last_flushed is None

        if not stale:
            stale = datetime.now() - self.last_flushed > self.flush_after

        return full or stale

    def _enqueue(self, action):

        # if we've disabled sending, just return False
        if not self.send:
            return False

        submitted = False

        if len(self.queue) < self.max_queue_size:
            self.queue.append(action)

            self.stats.submitted += 1

            submitted = True

            log('debug', 'Enqueued ' + action['action'] + '.')

        else:
            log('warn', 'analytics-python queue is full')

        if self._should_flush():
            self.flush()

        return submitted

    def _on_successful_flush(self, data, response):
        if 'batch' in data:
            for item in data['batch']:
                self.stats.successful += 1
                for callback in self.success_callbacks:
                    callback(data, response)

    def _on_failed_flush(self, data, error):
        if 'batch' in data:
            for item in data['batch']:
                self.stats.failed += 1
                for callback in self.failure_callbacks:
                    callback(data, error)

    def _flush_thread_is_free(self):
        return self.flushing_thread is None \
            or not self.flushing_thread.is_alive()

    def flush(self, async=None):
        """ Forces a flush from the internal queue to the server

        :param bool async: True to block until all messages have been flushed
        """

        flushing = False

        # if the async arg is provided, it overrides the client's settings
        if async is None:
            async = self.async

        if async:
            # We should asynchronously flush on another thread
            with self.flush_lock:

                if self._flush_thread_is_free():

                    log('debug', 'Initiating asynchronous flush ..')

                    self.flushing_thread = FlushThread(self)
                    self.flushing_thread.start()

                    flushing = True

                else:
                    log('debug', 'The flushing thread is still active.')
        else:

            # Flushes on this thread
            log('debug', 'Initiating synchronous flush ..')
            self._sync_flush()
            flushing = True

        if flushing:
            self.last_flushed = datetime.now()
            self.stats.flushes += 1

        return flushing

    def _sync_flush(self):

        log('debug', 'Starting flush ..')

        successful = 0
        failed = 0

        url = options.host + options.endpoints['batch']

        while len(self.queue) > 0:

            batch = []
            for i in range(self.max_flush_size):
                if len(self.queue) == 0:
                    break

                batch.append(self.queue.pop())

            payload = {'batch': batch, 'secret': self.secret}

            if request(self, url, payload):
                successful += len(batch)
            else:
                failed += len(batch)

        log('debug', 'Successfully flushed {0} items [{1} failed].'.
                     format(str(successful), str(failed)))

########NEW FILE########
__FILENAME__ = errors


class ApiError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return repr(self.message)

########NEW FILE########
__FILENAME__ = options

host = 'https://api.segment.io'

endpoints = {
    'track': '/v1/track',
    'identify': '/v1/identify',
    'alias': '/v1/alias',
    'batch': '/v1/import'
}

########NEW FILE########
__FILENAME__ = stats


class Statistics(object):

    def __init__(self):
        # The number of submitted identifies/tracks
        self.submitted = 0

        # The number of identifies submitted
        self.identifies = 0
        # The number of tracks submitted
        self.tracks = 0
        # The number of aliases
        self.aliases = 0

        # The number of actions to be successful
        self.successful = 0
        # The number of actions to fail
        self.failed = 0

        # The number of flushes to happen
        self.flushes = 0

########NEW FILE########
__FILENAME__ = utils
import json
from datetime import datetime
from dateutil.tz import tzlocal, tzutc


def is_naive(dt):
    """ Determines if a given datetime.datetime is naive. """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None

def total_seconds(delta):
    """ Determines total seconds with python < 2.7 compat """
    # http://stackoverflow.com/questions/3694835/python-2-6-5-divide-timedelta-with-timedelta
    return (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 1e6) / 1e6

def guess_timezone(dt):
    """ Attempts to convert a naive datetime to an aware datetime """
    if is_naive(dt):
        # attempts to guess the datetime.datetime.now() local timezone
        # case, and then defaults to utc

        delta = datetime.now() - dt
        if total_seconds(delta) < 5:
            # this was created using datetime.datetime.now()
            # so we are in the local timezone
            return dt.replace(tzinfo=tzlocal())
        else:
            # at this point, the best we can do (I htink) is guess UTC
            return dt.replace(tzinfo=tzutc())

    return dt

class DatetimeSerializer(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)

########NEW FILE########
__FILENAME__ = version
VERSION = '0.4.4'

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# encoding: utf-8

import unittest
import json

from datetime import datetime, timedelta

from random import randint
from time import sleep, time
from decimal import *

import logging
logging.basicConfig()

from dateutil.tz import tzutc

import analytics
import analytics.utils

secret = 'testsecret'


def on_success(data, response):
    print 'Success', response


def on_failure(data, error):
    print 'Failure', error


class AnalyticsBasicTests(unittest.TestCase):

    def setUp(self):
        analytics.init(secret, log_level=logging.DEBUG)

        analytics.on_success(on_success)
        analytics.on_failure(on_failure)

    def test_timezone_utils(self):

        now = datetime.now()
        utcnow = datetime.now(tz=tzutc())

        self.assertTrue(analytics.utils.is_naive(now))
        self.assertFalse(analytics.utils.is_naive(utcnow))

        fixed = analytics.utils.guess_timezone(now)

        self.assertFalse(analytics.utils.is_naive(fixed))

        shouldnt_be_edited = analytics.utils.guess_timezone(utcnow)

        self.assertEqual(utcnow, shouldnt_be_edited)

    def test_clean(self):

        simple = {
            'integer': 1,
            'float': 2.0,
            'long': 200000000,
            'bool': True,
            'str': 'woo',
            'unicode': u'woo',
            'decimal': Decimal('0.142857'),
            'date': datetime.now(),
        }

        complicated = {
            'exception': Exception('This should show up'),
            'timedelta': timedelta(microseconds=20),
            'list': [1, 2, 3]
        }

        combined = dict(simple.items() + complicated.items())

        pre_clean_keys = combined.keys()

        analytics.default_client._clean(combined)

        self.assertEqual(combined.keys(), pre_clean_keys)
        
    def test_datetime_serialization(self):
        
        data = {
            'created': datetime(2012, 3, 4, 5, 6, 7, 891011),
        }
        result = json.dumps(data, cls=analytics.utils.DatetimeSerializer)
        
        self.assertEqual(result, '{"created": "2012-03-04T05:06:07.891011"}')

    def test_async_basic_identify(self):
        # flush after every message
        analytics.default_client.flush_at = 1
        analytics.default_client.async = True

        last_identifies = analytics.stats.identifies
        last_successful = analytics.stats.successful
        last_flushes = analytics.stats.flushes

        analytics.identify('ilya@analytics.io', {
            "Subscription Plan": "Free",
            "Friends": 30
        })

        self.assertEqual(analytics.stats.identifies, last_identifies + 1)

        # this should flush because we set the flush_at to 1
        self.assertEqual(analytics.stats.flushes, last_flushes + 1)

        # this should do nothing, as the async thread is currently active
        analytics.flush()

        # we should see no more flushes here
        self.assertEqual(analytics.stats.flushes, last_flushes + 1)

        sleep(1)

        self.assertEqual(analytics.stats.successful, last_successful + 1)

    def test_async_basic_track(self):

        analytics.default_client.flush_at = 50
        analytics.default_client.async = True

        last_tracks = analytics.stats.tracks
        last_successful = analytics.stats.successful

        analytics.track('ilya@analytics.io', 'Played a Song', {
            "Artist": "The Beatles",
            "Song": "Eleanor Rigby"
        })

        self.assertEqual(analytics.stats.tracks, last_tracks + 1)

        analytics.flush()

        sleep(2)

        self.assertEqual(analytics.stats.successful, last_successful + 1)

    def test_async_full_identify(self):

        analytics.default_client.flush_at = 1
        analytics.default_client.async = True

        last_identifies = analytics.stats.identifies
        last_successful = analytics.stats.successful

        traits = {
            "Subscription Plan": "Free",
            "Friends": 30
        }

        context = {
            "ip": "12.31.42.111",
            "location": {
                "countryCode": "US",
                "region": "CA"
            },
            "userAgent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) " +
                "AppleWebKit/534.53.11 (KHTML, like Gecko) Version/5.1.3 " +
                "Safari/534.53.10"),
            "language": "en-us"
        }

        analytics.identify('ilya@analytics.io', traits,
            context=context, timestamp=datetime.now())

        self.assertEqual(analytics.stats.identifies, last_identifies + 1)

        sleep(2)

        self.assertEqual(analytics.stats.successful, last_successful + 1)

    def test_async_full_track(self):

        analytics.default_client.flush_at = 1
        analytics.default_client.async = True

        last_tracks = analytics.stats.tracks
        last_successful = analytics.stats.successful

        properties = {
            "Artist": "The Beatles",
            "Song": "Eleanor Rigby"
        }

        analytics.track('ilya@analytics.io', 'Played a Song',
            properties, timestamp=datetime.now())

        self.assertEqual(analytics.stats.tracks, last_tracks + 1)

        sleep(1)

        self.assertEqual(analytics.stats.successful, last_successful + 1)

    def test_alias(self):

        session_id = str(randint(1000000, 99999999))
        user_id = 'bob+'+session_id + '@gmail.com'

        analytics.default_client.flush_at = 1
        analytics.default_client.async = False

        last_aliases = analytics.stats.aliases
        last_successful = analytics.stats.successful

        analytics.identify(session_id, traits={'AnonymousTrait': 'Who am I?'})
        analytics.track(session_id, 'Anonymous Event')

        # alias the user
        analytics.alias(session_id, user_id)

        analytics.identify(user_id, traits={'IdentifiedTrait': 'A Hunk'})
        analytics.track(user_id, 'Identified Event')

        self.assertEqual(analytics.stats.aliases, last_aliases + 1)
        self.assertEqual(analytics.stats.successful, last_successful + 5)

    def test_blocking_flush(self):

        analytics.default_client.flush_at = 1
        analytics.default_client.async = False

        last_tracks = analytics.stats.tracks
        last_successful = analytics.stats.successful

        properties = {
            "Artist": "The Beatles",
            "Song": "Eleanor Rigby"
        }

        analytics.track('ilya@analytics.io', 'Played a Song',
            properties, timestamp=datetime.today())

        self.assertEqual(analytics.stats.tracks, last_tracks + 1)
        self.assertEqual(analytics.stats.successful, last_successful + 1)

    def test_time_policy(self):

        analytics.default_client.async = False
        analytics.default_client.flush_at = 1

        # add something so we have a reason to flush
        analytics.track('ilya@analytics.io', 'Played a Song', {
            "Artist": "The Beatles",
            "Song": "Eleanor Rigby"
        })

        # flush to reset flush count
        analytics.flush()

        last_flushes = analytics.stats.flushes

        # set the flush size trigger high
        analytics.default_client.flush_at = 50
        # set the time policy to 1 second from now
        analytics.default_client.flush_after = timedelta(seconds=1)

        analytics.track('ilya@analytics.io', 'Played a Song', {
            "Artist": "The Beatles",
            "Song": "Eleanor Rigby"
        })

        # that shouldn't of triggered a flush
        self.assertEqual(analytics.stats.flushes, last_flushes)

        # sleep past the time-flush policy
        sleep(1.2)

        # submit another track to trigger the policy
        analytics.track('ilya@analytics.io', 'Played a Song', {
            "Artist": "The Beatles",
            "Song": "Eleanor Rigby"
        })

        self.assertEqual(analytics.stats.flushes, last_flushes + 1)

    def test_performance(self):

        to_send = 100

        target = analytics.stats.successful + to_send

        analytics.default_client.async = True
        analytics.default_client.flush_at = 200
        analytics.default_client.max_flush_size = 50
        analytics.default_client.set_log_level(logging.DEBUG)

        for i in range(to_send):
            analytics.track('ilya@analytics.io', 'Played a Song', {
                "Artist": "The Beatles",
                "Song": "Eleanor Rigby"
            })

        print 'Finished submitting into the queue'

        start = time()
        while analytics.stats.successful < target:
            print ('Successful ', analytics.stats.successful, 'Left',
                (target - analytics.stats.successful),
                'Duration ', (time() - start))
            analytics.flush()
            sleep(1.0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
