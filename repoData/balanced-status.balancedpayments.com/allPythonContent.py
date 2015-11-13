__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2


class MainHandler(webapp2.RequestHandler):

    def get(self):
        self.response.write('Hello world!')

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)

########NEW FILE########
__FILENAME__ = encoding
from __future__ import unicode_literals
import json
from datetime import datetime

from google.appengine.ext import db


SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list, datetime)
_ERROR_MSG = 'Object of type {0} with value of {1} is not JSON serializable'


class JSONSterlingSerializer(object):

    def __init__(self, explicit_none_check=False):
        self.serialization_chain = []
        self.explicit_none_check = explicit_none_check

    def add(self, callable_serializer):
        self.serialization_chain.append(callable_serializer)
        return self

    def __call__(self, serializable):
        for serializer in self.serialization_chain:
            result = serializer(serializable)
            if ((not self.explicit_none_check and result) or
                (self.explicit_none_check and result is not None)):
                return result

        error_msg = _ERROR_MSG.format(type(serializable), repr(serializable))
        raise TypeError(error_msg)


def handle_datetime(serializable):
    if hasattr(serializable, 'isoformat'):
        # Serialize DateTime objects to RFC3339 protocol.
        # http://www.ietf.org/rfc/rfc3339.txt
        return serializable.isoformat() + 'Z'


# should be a singleton
default_json_serializer = JSONSterlingSerializer()
default_json_serializer.add(handle_datetime)


def to_json(*args, **kwargs):

    is_xhr = kwargs.pop('is_xhr', None)
    indent = None if is_xhr else 2
    return json.dumps(dict(*args, **kwargs),
                      indent=indent,
                      default=default_json_serializer)


def to_dict(model):
    output = {}

    for key, prop in model.properties().iteritems():
        value = getattr(model, key)

        if value is None or isinstance(value, SIMPLE_TYPES):
            output[key] = value
        elif isinstance(value, db.Model):
            output[key] = to_dict(value)
        else:
            raise ValueError('cannot encode ' + repr(prop))


    return output

########NEW FILE########
__FILENAME__ = mailer
from google.appengine.api import mail
import settings
import base64
from urlparse import urlparse

class Mail(object):
    def __init__(self):
        self.sender = settings.EMAIL['sender']

    def send(self, email_address, subject, message, request_url=None):
        if not email_address or not subject or not message:
            return False

        if request_url:
            request_url = urlparse(request_url)

            # Add unsubscribe footer to e-emails
            message = message + "\n\n" + \
            "Click the following link below at any time to unsubscribe.\n" + \
            request_url.scheme + "://" + request_url.netloc + \
            "/subscriptions/email/" + base64.urlsafe_b64encode(email_address)

        return mail.send_mail(self.sender, email_address, subject, message)
########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import base64
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import os
import time

import webapp2
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.ext import db

from twilio.rest import TwilioException

import encoding
import json
import settings
import tweeter
import models
import mailer
import sms
import subscription
from uptime import graphite
from uptime import librato


LOGGER = logging.getLogger(__name__)


def cache(method, seconds=60 * 60 * 24):
    """ A basic caching wrapper that will generate a key based off of the URL
    of the request """
    #@functools.wraps
    def wrapped(handler, *a, **kw):
        key = (handler.request.path.replace('/', '') +
               handler.request.query_string)

        # This is absolutely required, to normalize memcached keys
        # from /twitter/post and /uptime/post
        if "post" in key:
            key = key.replace("post", '')

        data = memcache.get(key)
        if not data:
            LOGGER.info('CACHE miss')
            data = method(handler, *a, **kw)
            if not memcache.add(key=key, value=data, time=seconds):
                LOGGER.error('Failed to set cache ' + key)
        return data
    return wrapped


class TwitterBaseController(webapp2.RequestHandler):

    def __init__(self, *a, **kw):
        super(TwitterBaseController, self).__init__(*a, **kw)
        self.tweet_manager = tweeter.TwitterStatusProcessor(
            **settings.TWITTER['AUTH']
        )


class TwitterHandler(TwitterBaseController):

    def get(self, service=None, **_):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get(service))

    @cache
    def _get(self, service):
        tweets = []
        services = [service] if service else tweeter.SERVICES
        for service in services:
            tweets += self.tweet_manager.get(service)

        return encoding.to_json({
            'messages': [encoding.to_dict(m) for m in tweets]
        })

    def post(self):
        self.tweet_manager.run()

        keys = [
            'twitter',
            'twittermessages',
            'twittermessageslatest',
        ]

        for key in keys:
            memcache.delete(key)

        # Send notifications on tweet
        for service in tweeter.SERVICES:
            latest_tweet = self.tweet_manager.get_last_message(service)

            # Notified must be set, False, and created within the last 10
            # minutes
            if (latest_tweet and hasattr(latest_tweet, 'notified') and
               not latest_tweet.notified
               and latest_tweet.created_at > datetime.utcnow() - timedelta(minutes=10)):

                self.tweet_manager._set_notified(latest_tweet.tweet_id)

                subscription.send_emails(service=service,
                                         request_url=self.request.url,
                                         current_state=latest_tweet.status,
                                         twitter_tweet=latest_tweet.message)

                subscription.send_smses(service=service,
                                        current_state=latest_tweet.status,
                                        twitter_tweet=latest_tweet.message)

        self.get()


class TwitterPostHandler(webapp2.RequestHandler):

    def get(self):
        th = TwitterHandler(self.request, self.response)
        th.post()


class TwitterMessageHandler(TwitterBaseController):

    def get(self, *a, **kw):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())

    @cache
    def _get(self):
        offset = int(self.request.get('offset', 0))
        max_date = datetime.utcnow() - timedelta(days=offset)
        min_date = max_date - timedelta(days=30)
        messages = defaultdict(list)   # messages by service
        messages['min'] = time.mktime(min_date.timetuple())
        messages['max'] = time.mktime(max_date.timetuple())

        for service in tweeter.SERVICES:
            tweets = self.tweet_manager.get_by_dates(
                service,
                max_date=max_date,
                min_date=min_date,
            )
            tweets = [t for t in tweets]
            messages[service] = [encoding.to_dict(m)
                                 for m in reversed(tweets)]

        return encoding.to_json({
            'messages': messages,
        })


class TwitterLatestMessageHandler(TwitterBaseController):

    """
    Mounted at /twitter/messages/latest
    GET returns a dictionary of messages by service
    {
        'DASH': message1,
        'API': message1,
        'JS': message1,
    }
    """

    def get(self, *a, **kw):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())

    @cache
    def _get(self):
        messages = {}   # messages by date + service

        for service in tweeter.SERVICES:
            tweet = self.tweet_manager.get_last_message(service)
            if tweet:
                if tweet.created_at < datetime.utcnow() - timedelta(days=1):
                    tweet = None
            messages[service] = encoding.to_dict(
                tweet,
            ) if tweet else None

        return encoding.to_json({
            'messages': messages,
        })


class UptimeHandler(TwitterBaseController):

    """
    Mounted at /uptime
    GET returns a dictionary of uptime for the various services
    POST deletes cached results, the subsequent GET will re-populate the cache
    """

    def __init__(self, request, response):
        super(UptimeHandler, self).__init__(request, response)
        self.uptime_managers = [
            graphite.Calculator(**settings.UPTIME),
            librato.Calculator(**settings.LIBRATO_UPTIME)
        ]

    def get(self, *a, **kw):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())

    @cache
    def _get(self):
        uptimes = []
        for manager in self.uptime_managers:
            uptimes.extend(manager.refresh())
        raw = {
            'uptime': dict(uptimes)
        }

        for service in tweeter.SERVICES:
            # if a service is UP and a tweet says it's down, then the down
            # takes precedence
            _s = raw['uptime'][service]

            if _s['status'] == 'UP':
                tweet_state = self.tweet_manager.get_latest_state(
                    service
                )

                _s['status'] = tweet_state or _s['status']

            subscription.should_notify(service, _s['status'], self.request.url)

        return encoding.to_json(raw)

    def post(self):
        memcache.delete('uptime')
        self.get()


class UptimePostHandler(webapp2.RequestHandler):

    def get(self):
        uh = UptimeHandler(self.request, self.response)
        uh.post()


class MainHandler(webapp2.RequestHandler):

    """
    Serves the index.html, that's it.
    """

    def get(self, *a, **kw):
        path = os.path.join(
            os.path.dirname(__file__),
            'templates',
            'index.html')
        self.response.out.write(template.render(path, {}))


class SubscribeEmailHandler(webapp2.RequestHandler):

    def post(self):
        self.response.headers['Content-Type'] = 'application/json'

        email = self.request.get('email')
        services = self.request.get('services').rstrip(',')

        query = db.GqlQuery(
            "SELECT * FROM EmailSubscriber WHERE email = :1",
            email)

        number_rows = query.count()

        if number_rows > 0:
            self.response.status = 409
            self.response.out.write(json.dumps({
                "error": email + " is already subscribed."
            }))
            return

        mail = mailer.Mail()
        mail.send(email,
                  "Successfully subscribed to Balanced " +
                  services + " incidents",
                  "You successfully subscribed to Balanced " +
                  services + " incidents.",
                  self.request.url)

        s = models.EmailSubscriber(email=email,
                                   services=services.split(','))

        s.put()

        self.response.out.write(json.dumps({
            "subscribed": "email",
            "services": services.split(',')
        }))


class SubscribeSMSHandler(webapp2.RequestHandler):

    def post(self):
        self.response.headers['Content-Type'] = 'application/json'

        phone = self.request.get('phone')
        services = self.request.get('services').rstrip(',')

        query = db.GqlQuery(
            "SELECT * FROM SMSSubscriber WHERE phone = :1",
            phone)

        number_rows = query.count()

        if number_rows > 0:
            self.response.status = 409
            self.response.out.write(json.dumps({
                "error": phone + " is already subscribed."
            }))
            return

        txt = sms.SMS()
        try:
            txt.send(phone,
                     "Successfully subscribed to Balanced "
                     + services +
                     " incidents. Reply with STOP to unsubscribe.")

        except TwilioException, e:
            LOGGER.error("Failed to send SMS via Twilio - " + e.msg)
            self.response.status = 400
            self.response.out.write(json.dumps({
                "error": e.msg
            }))
            return

        s = models.SMSSubscriber(phone=phone,
                                 services=services.split(','))

        s.put()

        self.response.out.write(json.dumps({
            "subscribed": "sms",
            "services": services.split(',')
        }))


class UnsubscribeEmailHandler(webapp2.RequestHandler):

    def get(self, base64email):
        if not base64email:
            self.redirect("/")

        email = base64.urlsafe_b64decode(base64email)

        if email:
            email_subscriber = models.EmailSubscriber.all()
            email_subscriber.filter('email =', email)

            for es in email_subscriber:
                es.delete()

        # ToDo: show a nice pretty notification that e-mail is subscribed
        self.redirect("/")


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/uptime', UptimeHandler),
    ('/uptime/post', UptimePostHandler),
    ('/twitter', TwitterHandler),
    ('/twitter/post', TwitterPostHandler),
    ('/twitter/messages', TwitterMessageHandler),
    ('/twitter/messages/latest', TwitterLatestMessageHandler),
    ('/twitter/(.*)', TwitterHandler),
    ('/subscriptions/email', SubscribeEmailHandler),
    ('/subscriptions/email/(.*)', UnsubscribeEmailHandler),
    ('/subscriptions/sms', SubscribeSMSHandler)
], debug=settings.DEBUG)

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from google.appengine.ext import db

class Tweet(db.Model):
    created_at = db.DateTimeProperty()
    message = db.StringProperty()
    status = db.StringProperty()
    service = db.StringProperty()
    tweet_id = db.StringProperty()
    notified = db.BooleanProperty()

    @db.ComputedProperty
    def created_date(self):
        return self.created_at.date().strftime('%Y-%m-%d')

    def set_notified(self):
        self.notified = True
        self.put()


class Uptime(db.Model):
    start = db.DateTimeProperty()
    end = db.DateTimeProperty()
    data = db.StringProperty(multiline=True)

    @classmethod
    def get_by_dates(cls, start, end):
        result = cls.all().filter(
            'start = ', start
        ).filter(
            'end = ', end
        ).fetch(1)
        if result:
            return result
        return None

    @classmethod
    def latest(cls):
        result = cls.all().order('-end').fetch(1)
        if result:
            return result[0].end
        return None

    @classmethod
    def latest(cls):
        result = cls.all().order('-end').fetch(1)
        if result:
            return result[0].end
        return None


def kv_key(key=None):
    return db.Key.from_path('KV', key)


class KV(db.Model):
    k = db.StringProperty()
    value = db.StringProperty()

    @classmethod
    def generate_key(cls, key):
        return kv_key(key)

    @classmethod
    def get(cls, key):
        return db.get(cls.generate_key(key))


class EmailSubscriber(db.Model):
    created_at = db.DateTimeProperty(auto_now_add=True)
    email = db.EmailProperty(required=True)
    services = db.StringListProperty(required=True)


class SMSSubscriber(db.Model):
    created_at = db.DateTimeProperty(auto_now_add=True)
    phone = db.StringProperty(required=True)
    services = db.StringListProperty(required=True)


class ServiceStatus(db.Model):
    service = db.StringProperty(required=True,
                                choices=('API', 'DASHBOARD', 'JS'))

    current = db.StringProperty(required=True,
                                choices=('UP', 'ISSUE', 'DOWN'))

    down_count = db.IntegerProperty(required=True,
                                    default=0)

    UP = "UP"
    DOWN = "DOWN"
    ISSUE = "ISSUE"
    NOTIFY_DOWN = "NOTIFY_DOWN"
    NOTIFY_UP = "NOTIFY_UP"

    def _on_down(self):
        self.down_count += 1
        self.put()
        if self.down_count == 1:
            return self.NOTIFY_DOWN

        return None

    def _on_up(self):
        if self.down_count > 0:
            self.down_count = 0
            self.put()
            return self.NOTIFY_UP

        return None

    _dfa = {
        UP: {
            ISSUE: None,
            DOWN: _on_down,
            UP: None
        },
        ISSUE: {
            UP: _on_up,
            DOWN: _on_down,
            ISSUE: None
        },
        DOWN: {
            UP: _on_up,
            ISSUE: None,
            DOWN: None,
        }
    }

    def change(self, new_state):
        action = self._dfa[self.current][new_state]

        self.current = new_state
        self.put()

        if action is not None:
            return action(self)

########NEW FILE########
__FILENAME__ = settings
# Notice:
# If you are running this in production environment, generate
# these for your app at https://dev.twitter.com/apps/new
TWITTER = {
    'AUTH': {
        'consumer_key': 'XXXX',
        'consumer_secret': 'XXXX',
        'token': 'XXXX',
        'token_secret': 'XXXX',
     }
}


# We're pulling data from graphite to calculate the uptime. Each service has a
# list of counters that it uses to help calculate the % of successful / failed
# requests.
UPTIME = {
    'root_uri': 'http://graphite.balancedpayments.com/render/?',
    'username': 'username',
    'password': 'password',
    'services': {
        'DASH': {
            'OK_TARGETS': [
                'stats_counts.status.dashboard.2xx',
                'stats_counts.status.dashboard.3xx',
                'stats_counts.status.dashboard.4xx',
                ],
            'ERROR_TARGETS': [
                'stats_counts.status.dashboard.5xx',
                'stats_counts.status.dashboard.timeout',
                ]
        },
        'JS': {
            'OK_TARGETS': [
                'stats_counts.status.balanced-js.2xx',
                'stats_counts.status.balanced-js.3xx',
                'stats_counts.status.balanced-js.4xx',
                ],
            'ERROR_TARGETS': [
                'stats_counts.status.balanced-js.5xx',
                'stats_counts.status.balanced-js.timeout',
                ]
        },
        'API': {
            'OK_TARGETS': [
                'stats_counts.status.balanced-api.2xx',
                'stats_counts.status.balanced-api.3xx',
                'stats_counts.status.balanced-api.4xx',
                ],
            'ERROR_TARGETS': [
                'stats_counts.status.balanced-api.5xx',
                'stats_counts.status.balanced-api.timeout',
                ]
        }
    }
}

# The e-mail address to send notifications from
EMAIL = {
    'sender': 'Balanced Status <noreply@balancedpayments.com>'
}

LIBRATO_UPTIME = {
    'root_uri': 'https://metrics-api.librato.com/v1/metrics/',
    'username': 'FIXME',
    'password': 'FIXME',
    'services': {
        'API': {
            'SOURCE': '*bapi-live*',
            'TOTAL_TARGETS': [
                'AWS.ELB.RequestCount',
            ],
            'ERROR_TARGETS': [
                'AWS.ELB.HTTPCode_Backend_5XX',
                'AWS.ELB.HTTPCode_ELB_5XX',
            ]
        },
    }
}

# TWILIO API credentials
TWILIO = {
    'account_sid': 'XXXX',
    'auth_token': 'XXXX',
    'from_number': 'XXXX'
}

DEBUG = True

# Currently DASHBOARD does not send out notifications
NOTIFY_SERVICES = ['API', 'JS']

########NEW FILE########
__FILENAME__ = six
../venv/lib/python2.7/site-packages/six.py
########NEW FILE########
__FILENAME__ = sms
from twilio.rest import TwilioRestClient
import settings


class SMS(object):
    def __init__(self):
        self.client = TwilioRestClient(
            settings.TWILIO['account_sid'],
            settings.TWILIO['auth_token'],
        )

    def send(self, phone_number, message):
        if not phone_number or not message:
            return False

        # Cleanup phone number, strip spaces, dashes, ( and )
        phone_number = phone_number.replace(' ', '').replace(
            '-', '').replace('(', '').replace(')', '')

        # Limit message to 160 characters, enforced by Twilio
        message = message[:160]

        return self.client.sms.messages.create(
            to=phone_number,
            from_=settings.TWILIO['from_number'],
            body=message,
        )

########NEW FILE########
__FILENAME__ = subscription
import models
import settings
import logging
import mailer
import sms
from twilio.rest import TwilioException

LOGGER = logging.getLogger(__name__)


def should_notify(service, current_state, request_url):
     # This is filthy. Don't judge me bro
    if service == "DASH":
        service = "DASHBOARD"

    svc_status = models.ServiceStatus.all()
    svc_status.filter('service =', service)

    # No status object stored. Create it, and return
    if svc_status.count() == 0:
        ss = models.ServiceStatus(service=service, current=current_state)
        ss.put()
        return

    # Will always just run just once
    for ss in svc_status:
        result = ss.change(current_state)

        if result == "NOTIFY_UP" or result == "NOTIFY_DOWN":
            if settings.DEBUG:
                LOGGER.info("SERVICE [" + service + "] IS " + current_state)

            send_emails(service, request_url, current_state)
            send_smses(service, current_state)
            return True

    return False


def send_emails(service, request_url, current_state=None, twitter_tweet=None):
    # This is filthy. Don't judge me bro
    if service == "DASH":
        service = "DASHBOARD"

    email_subscribers = models.EmailSubscriber.gql("WHERE services IN (:1)", service)

    if settings.DEBUG:
        LOGGER.info(
            "SENDING NOTIFICATION TO [" + str(email_subscribers.count()) + "] EMAIL SUBSCRIBERS"
        )

    if service in settings.NOTIFY_SERVICES:
        mail = mailer.Mail()
        for email_subscriber in email_subscribers:
            # Tweet
            if(twitter_tweet):
                twitter_tweet = twitter_tweet.strip()

                mail.send(
                    email_subscriber.email,
                    "Tweet from @balancedstatus",
                    "{}".format(twitter_tweet) +
                    "\n\nThis is an automated notification from https://status.balancedpayments.com",
                    request_url)
            # UP/DOWN
            else:
                mail.send(
                    email_subscriber.email,
                    "Balanced {} is {}".format(
                        service, current_state),
                    "Balanced {} is {}.".format(service, current_state) +
                    "\n\nThis is an automated notification from https://status.balancedpayments.com",
                    request_url)


def send_smses(service, current_state=None, twitter_tweet=None):
    # This is filthy. Don't judge me bro
    if service == "DASH":
        service = "DASHBOARD"

    sms_subscribers = models.SMSSubscriber.gql("WHERE services IN (:1)", service)

    if settings.DEBUG:
        LOGGER.info(
            "SENDING NOTIFICATION TO [" + str(sms_subscribers.count()) + "] SMS SUBSCRIBERS"
        )

    if service in settings.NOTIFY_SERVICES:
        txt = sms.SMS()
        for sms_subscriber in sms_subscribers:
            try:
                # Tweet
                if(twitter_tweet):
                    twitter_tweet = twitter_tweet.strip()

                    txt.send(
                        sms_subscriber.phone,
                        "@balancedstatus: {} - {}".format(
                            service, twitter_tweet))
                # UP/DOWN
                else:
                    txt.send(
                        sms_subscriber.phone,
                        "Balanced {} is {}. Reply with STOP to unsubscribe.".format(
                        service, current_state))
            except TwilioException, e:
                LOGGER.error("Failed to send SMS via Twilio - " + e.msg)
                pass

########NEW FILE########
__FILENAME__ = api
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import os
import mimetypes

from .binder import bind_api
from .error import TweepError
from .parsers import ModelParser
from .utils import list_to_csv


class API(object):
    """Twitter API"""

    def __init__(self, auth_handler=None,
            host='api.twitter.com', search_host='search.twitter.com',
             cache=None, secure=True, api_root='/1.1', search_root='',
            retry_count=0, retry_delay=0, retry_errors=None, timeout=60,
            parser=None, compression=False):
        self.auth = auth_handler
        self.host = host
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.compression = compression
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.timeout = timeout
        self.parser = parser or ModelParser()

    """ statuses/home_timeline """
    home_timeline = bind_api(
        path = '/statuses/home_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """ statuses/user_timeline """
    user_timeline = bind_api(
        path = '/statuses/user_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'since_id',
                          'max_id', 'count', 'include_rts']
    )

    """ statuses/mentions """
    mentions_timeline = bind_api(
        path = '/statuses/mentions_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """/related_results/show/:id.format"""
    related_results = bind_api(
        path = '/related_results/show/{id}.json',
        payload_type = 'relation', payload_list = True,
        allowed_param = ['id'],
        require_auth = False
    )

    """ statuses/retweets_of_me """
    retweets_of_me = bind_api(
        path = '/statuses/retweets_of_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """ statuses/show """
    get_status = bind_api(
        path = '/statuses/show.json',
        payload_type = 'status',
        allowed_param = ['id']
    )

    """ statuses/update """
    update_status = bind_api(
        path = '/statuses/update.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['status', 'in_reply_to_status_id', 'lat', 'long', 'source', 'place_id'],
        require_auth = True
    )

    """ statuses/destroy """
    destroy_status = bind_api(
        path = '/statuses/destroy/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweet """
    retweet = bind_api(
        path = '/statuses/retweet/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweets """
    retweets = bind_api(
        path = '/statuses/retweets/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count'],
        require_auth = True
    )

    retweeters = bind_api(
        path = '/statuses/retweeters/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'cursor', 'stringify_ids']
    )

    """ users/show """
    get_user = bind_api(
        path = '/users/show.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name']
    )

    ''' statuses/oembed '''
    get_oembed = bind_api(
        path = '/statuses/oembed.json',
        payload_type = 'json',
        allowed_param = ['id', 'url', 'maxwidth', 'hide_media', 'omit_script', 'align', 'related', 'lang']
    )

    """ Perform bulk look up of users from user ID or screenname """
    def lookup_users(self, user_ids=None, screen_names=None):
        return self._lookup_users(list_to_csv(user_ids), list_to_csv(screen_names))

    _lookup_users = bind_api(
        path = '/users/lookup.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['user_id', 'screen_name'],
    )

    """ Get the authenticated user """
    def me(self):
        return self.get_user(screen_name=self.auth.get_username())

    """ users/search """
    search_users = bind_api(
        path = '/users/search.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['q', 'per_page', 'page']
    )

    """ users/suggestions/:slug """
    suggested_users = bind_api(
        path = '/users/suggestions/{slug}.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['slug', 'lang']
    )

    """ users/suggestions """
    suggested_categories = bind_api(
        path = '/users/suggestions.json',
        payload_type = 'category', payload_list = True,
        allowed_param = ['lang'],
        require_auth = True
    )

    """ users/suggestions/:slug/members """
    suggested_users_tweets = bind_api(
        path = '/users/suggestions/{slug}/members.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['slug'],
        require_auth = True
    )

    """ direct_messages """
    direct_messages = bind_api(
        path = '/direct_messages.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count'],
        require_auth = True
    )

    """ direct_messages/show """
    get_direct_message = bind_api(
        path = '/direct_messages/show/{id}.json',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ direct_messages/sent """
    sent_direct_messages = bind_api(
        path = '/direct_messages/sent.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/new """
    send_direct_message = bind_api(
        path = '/direct_messages/new.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['user', 'screen_name', 'user_id', 'text'],
        require_auth = True
    )

    """ direct_messages/destroy """
    destroy_direct_message = bind_api(
        path = '/direct_messages/destroy.json',
        method = 'DELETE',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ friendships/create """
    create_friendship = bind_api(
        path = '/friendships/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'follow'],
        require_auth = True
    )

    """ friendships/destroy """
    destroy_friendship = bind_api(
        path = '/friendships/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ friendships/show """
    show_friendship = bind_api(
        path = '/friendships/show.json',
        payload_type = 'friendship',
        allowed_param = ['source_id', 'source_screen_name',
                          'target_id', 'target_screen_name']
    )

    """ Perform bulk look up of friendships from user ID or screenname """
    def lookup_friendships(self, user_ids=None, screen_names=None):
        return self._lookup_friendships(list_to_csv(user_ids), list_to_csv(screen_names))

    _lookup_friendships = bind_api(
        path = '/friendships/lookup.json',
        payload_type = 'relationship', payload_list = True,
        allowed_param = ['user_id', 'screen_name'],
        require_auth = True
    )


    """ friends/ids """
    friends_ids = bind_api(
        path = '/friends/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ friends/list """
    friends = bind_api(
        path = '/friends/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ friendships/incoming """
    friendships_incoming = bind_api(
        path = '/friendships/incoming.json',
        payload_type = 'ids',
        allowed_param = ['cursor']
    )

    """ friendships/outgoing"""
    friendships_outgoing = bind_api(
        path = '/friendships/outgoing.json',
        payload_type = 'ids',
        allowed_param = ['cursor']
    )

    """ followers/ids """
    followers_ids = bind_api(
        path = '/followers/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ followers/list """
    followers = bind_api(
        path = '/followers/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ account/verify_credentials """
    def verify_credentials(self, **kargs):
        try:
            return bind_api(
                path = '/account/verify_credentials.json',
                payload_type = 'user',
                require_auth = True,
                allowed_param = ['include_entities', 'skip_status'],
            )(self, **kargs)
        except TweepError, e:
            if e.response and e.response.status == 401:
                return False
            raise

    """ account/rate_limit_status """
    rate_limit_status = bind_api(
        path = '/application/rate_limit_status.json',
        payload_type = 'json',
        allowed_param = ['resources'],
        use_cache = False
    )

    """ account/update_delivery_device """
    set_delivery_device = bind_api(
        path = '/account/update_delivery_device.json',
        method = 'POST',
        allowed_param = ['device'],
        payload_type = 'user',
        require_auth = True
    )

    """ account/update_profile_colors """
    update_profile_colors = bind_api(
        path = '/account/update_profile_colors.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['profile_background_color', 'profile_text_color',
                          'profile_link_color', 'profile_sidebar_fill_color',
                          'profile_sidebar_border_color'],
        require_auth = True
    )

    """ account/update_profile_image """
    def update_profile_image(self, filename):
        headers, post_data = API._pack_image(filename, 700)
        return bind_api(
            path = '/account/update_profile_image.json',
            method = 'POST',
            payload_type = 'user',
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_background_image """
    def update_profile_background_image(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 800)
        bind_api(
            path = '/account/update_profile_background_image.json',
            method = 'POST',
            payload_type = 'user',
            allowed_param = ['tile'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_banner """
    def update_profile_banner(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 700, form_field="banner")
        bind_api(
            path = '/account/update_profile_banner.json',
            method = 'POST',
            allowed_param = ['width', 'height', 'offset_left', 'offset_right'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)


    """ account/update_profile """
    update_profile = bind_api(
        path = '/account/update_profile.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['name', 'url', 'location', 'description'],
        require_auth = True
    )

    """ favorites """
    favorites = bind_api(
        path = '/favorites/list.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['screen_name', 'user_id', 'max_id', 'count', 'since_id', 'max_id']
    )

    """ favorites/create """
    create_favorite = bind_api(
        path = '/favorites/create.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ favorites/destroy """
    destroy_favorite = bind_api(
        path = '/favorites/destroy.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ blocks/create """
    create_block = bind_api(
        path = '/blocks/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/destroy """
    destroy_block = bind_api(
        path = '/blocks/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/blocking """
    blocks = bind_api(
        path = '/blocks/list.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['cursor'],
        require_auth = True
    )

    """ blocks/blocking/ids """
    blocks_ids = bind_api(
        path = '/blocks/ids.json',
        payload_type = 'json',
        require_auth = True
    )

    """ report_spam """
    report_spam = bind_api(
        path = '/users/report_spam.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['user_id', 'screen_name'],
        require_auth = True
    )

    """ saved_searches """
    saved_searches = bind_api(
        path = '/saved_searches/list.json',
        payload_type = 'saved_search', payload_list = True,
        require_auth = True
    )

    """ saved_searches/show """
    get_saved_search = bind_api(
        path = '/saved_searches/show/{id}.json',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ saved_searches/create """
    create_saved_search = bind_api(
        path = '/saved_searches/create.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['query'],
        require_auth = True
    )

    """ saved_searches/destroy """
    destroy_saved_search = bind_api(
        path = '/saved_searches/destroy/{id}.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    create_list = bind_api(
        path = '/lists/create.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['name', 'mode', 'description'],
        require_auth = True
    )

    destroy_list = bind_api(
        path = '/lists/destroy.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'owner_id', 'list_id', 'slug'],
        require_auth = True
    )

    update_list = bind_api(
        path = '/lists/update.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['list_id', 'slug', 'name', 'mode', 'description', 'owner_screen_name', 'owner_id'],
        require_auth = True
    )

    lists_all = bind_api(
        path = '/lists/list.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['screen_name', 'user_id'],
        require_auth = True
    )

    lists_memberships = bind_api(
        path = '/lists/memberships.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['screen_name', 'user_id', 'filter_to_owned_lists', 'cursor'],
        require_auth = True
    )

    lists_subscriptions = bind_api(
        path = '/lists/subscriptions.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['screen_name', 'user_id', 'cursor'],
        require_auth = True
    )

    list_timeline = bind_api(
        path = '/lists/statuses.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id', 'since_id', 'max_id', 'count']
    )

    get_list = bind_api(
        path = '/lists/show.json',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'owner_id', 'slug', 'list_id']
    )

    add_list_member = bind_api(
        path = '/lists/members/create.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['screen_name', 'user_id', 'owner_screen_name', 'owner_id', 'slug', 'list_id'],
        require_auth = True
    )

    remove_list_member = bind_api(
        path = '/lists/members/destroy.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['screen_name', 'user_id', 'owner_screen_name', 'owner_id', 'slug', 'list_id'],
        require_auth = True
    )

    list_members = bind_api(
        path = '/lists/members.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner_screen_name', 'slug', 'list_id', 'owner_id', 'cursor']
    )

    show_list_member = bind_api(
        path = '/lists/members/show.json',
        payload_type = 'user',
        allowed_param = ['list_id', 'slug', 'user_id', 'screen_name', 'owner_screen_name', 'owner_id']
    )

    subscribe_list = bind_api(
        path = '/lists/subscribers/create.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id'],
        require_auth = True
    )

    unsubscribe_list = bind_api(
        path = '/lists/subscribers/destroy.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id'],
        require_auth = True
    )

    list_subscribers = bind_api(
        path = '/lists/subscribers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner_screen_name', 'slug', 'owner_id', 'list_id', 'cursor']
    )

    show_list_subscriber = bind_api(
        path = '/lists/subscribers/show.json',
        payload_type = 'user',
        allowed_param = ['owner_screen_name', 'slug', 'screen_name', 'owner_id', 'list_id', 'user_id']
    )

    """ trends/available """
    trends_available = bind_api(
        path = '/trends/available.json',
        payload_type = 'json'
    )

    trends_place = bind_api(
        path = '/trends/place.json',
        payload_type = 'json',
        allowed_param = ['id', 'exclude']
    )

    trends_closest = bind_api(
        path = '/trends/closest.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long']
    )

    """ search """
    search = bind_api(
        path = '/search/tweets.json',
        payload_type = 'search_results',
        allowed_param = ['q', 'lang', 'locale', 'since_id', 'geocode', 'show_user', 'max_id', 'since', 'until', 'result_type']
    )

    """ trends/daily """
    trends_daily = bind_api(
        path = '/trends/daily.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ trends/weekly """
    trends_weekly = bind_api(
        path = '/trends/weekly.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ geo/reverse_geocode """
    reverse_geocode = bind_api(
        path = '/geo/reverse_geocode.json',
        payload_type = 'place', payload_list = True,
        allowed_param = ['lat', 'long', 'accuracy', 'granularity', 'max_results']
    )

    """ geo/id """
    geo_id = bind_api(
        path = '/geo/id/{id}.json',
        payload_type = 'place',
        allowed_param = ['id']
    )

    """ geo/search """
    geo_search = bind_api(
        path = '/geo/search.json',
        payload_type = 'place', payload_list = True,
        allowed_param = ['lat', 'long', 'query', 'ip', 'granularity', 'accuracy', 'max_results', 'contained_within']
    )

    """ geo/similar_places """
    geo_similar_places = bind_api(
        path = '/geo/similar_places.json',
        payload_type = 'place', payload_list = True,
        allowed_param = ['lat', 'long', 'name', 'contained_within']
    )

    """ Internal use only """
    @staticmethod
    def _pack_image(filename, max_size, form_field="image"):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise TweepError('File is too big, must be less than 700kb.')
        except os.error:
            raise TweepError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise TweepError('Could not determine file type')
        file_type = file_type[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png']:
            raise TweepError('Invalid file type for image: %s' % file_type)

        # build the mulitpart-formdata body
        fp = open(filename, 'rb')
        BOUNDARY = 'Tw3ePy'
        body = []
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (form_field, filename))
        body.append('Content-Type: %s' % file_type)
        body.append('')
        body.append(fp.read())
        body.append('--' + BOUNDARY + '--')
        body.append('')
        fp.close()
        body = '\r\n'.join(body)

        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=Tw3ePy',
            'Content-Length': str(len(body))
        }

        return headers, body


########NEW FILE########
__FILENAME__ = auth
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from urllib2 import Request, urlopen
import base64

from . import oauth
from .error import TweepError
from .api import API


class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'api.twitter.com'
    OAUTH_ROOT = '/oauth/'

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint, secure=False):
        if self.secure or secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(url, headers=request.to_header()))
            return oauth.OAuthToken.from_string(resp.read())
        except Exception, e:
            raise TweepError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            if signin_with_twitter:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url
            )

            return request.to_url()
        except Exception, e:
            raise TweepError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')

            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request
            resp = urlopen(Request(url, headers=request.to_header()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            return self.access_token
        except Exception, e:
            raise TweepError(e)

    def get_xauth_access_token(self, username, password):
        """
        Get an access token from an username and password combination.
        In order to get this working you need to create an app at
        http://twitter.com/apps, after that send a mail to api@twitter.com
        and request activation of xAuth for it.
        """
        try:
            url = self._get_oauth_url('access_token', secure=True) # must use HTTPS
            request = oauth.OAuthRequest.from_consumer_and_token(
                oauth_consumer=self._consumer,
                http_method='POST', http_url=url,
                parameters = {
                    'x_auth_mode': 'client_auth',
                    'x_auth_username': username,
                    'x_auth_password': password
                }
            )
            request.sign_request(self._sigmethod, self._consumer, None)

            resp = urlopen(Request(url, data=request.to_postdata()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            return self.access_token
        except Exception, e:
            raise TweepError(e)

    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise TweepError("Unable to get username, invalid oauth token!")
        return self.username


########NEW FILE########
__FILENAME__ = binder
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
import urllib
import time
import re
from StringIO import StringIO
import gzip

from .error import TweepError
from .utils import convert_to_utf8_str
from .models import Model

re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):

        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)
        use_cache = config.get('use_cache', True)

        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise TweepError('Authentication required!')

            self.api = api
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)

            # Pick correct URL root to use
            if self.search_api:
                self.api_root = api.search_root
            else:
                self.api_root = api.api_root

            # Perform any path variable substitution
            self.build_path()

            if api.secure:
                self.scheme = 'https://'
            else:
                self.scheme = 'http://'

            if self.search_api:
                self.host = api.search_host
            else:
                self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue https://github.com/tweepy/tweepy/issues/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            self.parameters = {}
            for idx, arg in enumerate(args):
                if arg is None:
                    continue

                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise TweepError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if arg is None:
                    continue
                if k in self.parameters:
                    raise TweepError('Multiple values for parameter %s supplied!' % k)

                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and 'user' not in self.parameters and self.api.auth:
                    # No 'user' parameter provided, fetch it from Auth instead.
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = urllib.quote(self.parameters[name])
                    except KeyError:
                        raise TweepError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            if len(self.parameters):
                url = '%s?%s' % (url, urllib.urlencode(self.parameters))

            # Query the cache if one is available
            # and this request uses a GET method.
            if self.use_cache and self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            if isinstance(result, Model):
                                result._api = self.api
                    else:
                        if isinstance(cache_result, Model):
                            cache_result._api = self.api
                    return cache_result

            # Continue attempting request until successful
            # or maximum number of retries is reached.
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                if self.api.secure:
                    conn = httplib.HTTPSConnection(self.host, timeout=self.api.timeout)
                else:
                    conn = httplib.HTTPConnection(self.host, timeout=self.api.timeout)

                # Apply authentication
                if self.api.auth:
                    self.api.auth.apply_auth(
                            self.scheme + self.host + url,
                            self.method, self.headers, self.parameters
                    )

                # Request compression if configured
                if self.api.compression:
                    self.headers['Accept-encoding'] = 'gzip'

                # Execute request
                try:
                    conn.request(self.method, url, headers=self.headers, body=self.post_data)
                    resp = conn.getresponse()

                except Exception, e:
                    raise TweepError('Failed to send request: %s' % e)

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.status not in self.retry_errors: break
                else:
                    if resp.status == 200: break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            self.api.last_response = resp
            if resp.status and not 200 <= resp.status < 300:
                try:
                    error_msg = self.api.parser.parse_error(resp.read())
                except Exception:
                    error_msg = "Twitter error response: status code = %s" % resp.status
                raise TweepError(error_msg, resp)

            # Parse the response payload
            body = resp.read()
            if resp.getheader('Content-Encoding', '') == 'gzip':
                try:
                    zipper = gzip.GzipFile(fileobj=StringIO(body))
                    body = zipper.read()
                except Exception, e:
                    raise TweepError('Failed to decompress data: %s' % e)
            result = self.api.parser.parse(self, body)

            conn.close()

            # Store result into cache if one is available.
            if self.use_cache and self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)

            return result


    def _call(api, *args, **kargs):

        method = APIMethod(api, args, kargs)
        return method.execute()


    # Set pagination mode
    if 'cursor' in APIMethod.allowed_param:
        _call.pagination_mode = 'cursor'
    elif 'max_id' in APIMethod.allowed_param and \
         'since_id' in APIMethod.allowed_param:
        _call.pagination_mode = 'id'
    elif 'page' in APIMethod.allowed_param:
        _call.pagination_mode = 'page'

    return _call


########NEW FILE########
__FILENAME__ = cache
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import time
import datetime
import threading
import os

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import hashlib
except ImportError:
    # python 2.4
    import md5 as hashlib

try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print 'Warning! FileCache locking not supported on this system!'
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        md5.update(key)
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))

class MemCacheCache(Cache):
    """Cache interface"""

    def __init__(self, client, timeout=60):
        """Initialize the cache
            client: The memcache client
            timeout: number of seconds to keep a cached entry
        """
        self.client = client
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        self.client.set(key, value, time=self.timeout)

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]. DOES NOT WORK HERE
        """
        return self.client.get(key)

    def count(self):
        """Get count of entries currently stored in cache. RETURN 0"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache. NO-OP"""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries. NO-OP"""
        raise NotImplementedError

class RedisCache(Cache):
    '''Cache running in a redis server'''

    def __init__(self, client, timeout=60, keys_container = 'tweepy:keys', pre_identifier = 'tweepy:'):
        Cache.__init__(self, timeout)
        self.client = client
        self.keys_container = keys_container
        self.pre_identifier = pre_identifier

    def _is_expired(self, entry, timeout):
        # Returns true if the entry has expired
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        '''Store the key, value pair in our redis server'''
        # Prepend tweepy to our key, this makes it easier to identify tweepy keys in our redis server
        key = self.pre_identifier + key
        # Get a pipe (to execute several redis commands in one step)
        pipe = self.client.pipeline()
        # Set our values in a redis hash (similar to python dict)
        pipe.set(key, pickle.dumps((time.time(), value)))
        # Set the expiration
        pipe.expire(key, self.timeout)
        # Add the key to a set containing all the keys
        pipe.sadd(self.keys_container, key)
        # Execute the instructions in the redis server
        pipe.execute()

    def get(self, key, timeout=None):
        '''Given a key, returns an element from the redis table'''
        key = self.pre_identifier + key
        # Check to see if we have this key
        unpickled_entry = self.client.get(key)
        if not unpickled_entry:
            # No hit, return nothing
            return None

        entry = pickle.loads(unpickled_entry)
        # Use provided timeout in arguments if provided
        # otherwise use the one provided during init.
        if timeout is None:
            timeout = self.timeout

        # Make sure entry is not expired
        if self._is_expired(entry, timeout):
            # entry expired, delete and return nothing
            self.delete_entry(key)
            return None
        # entry found and not expired, return it
        return entry[1]

    def count(self):
        '''Note: This is not very efficient, since it retreives all the keys from the redis
        server to know how many keys we have'''
        return len(self.client.smembers(self.keys_container))

    def delete_entry(self, key):
        '''Delete an object from the redis table'''
        pipe = self.client.pipeline()
        pipe.srem(self.keys_container, key)
        pipe.delete(key)
        pipe.execute()

    def cleanup(self):
        '''Cleanup all the expired keys'''
        keys = self.client.smembers(self.keys_container)
        for key in keys:
            entry = self.client.get(key)
            if entry:
                entry = pickle.loads(entry)
                if self._is_expired(entry, self.timeout):
                    self.delete_entry(key)

    def flush(self):
        '''Delete all entries from the cache'''
        keys = self.client.smembers(self.keys_container)
        for key in keys:
            self.delete_entry(key)


class MongodbCache(Cache):
    """A simple pickle-based MongoDB cache sytem."""

    def __init__(self, db, timeout=3600, collection='tweepy_cache'):
        """Should receive a "database" cursor from pymongo."""
        Cache.__init__(self, timeout)
        self.timeout = timeout
        self.col = db[collection]
        self.col.create_index('created', expireAfterSeconds=timeout)

    def store(self, key, value):
        from bson.binary import Binary

        now = datetime.datetime.utcnow()
        blob = Binary(pickle.dumps(value))

        self.col.insert({'created': now, '_id': key, 'value': blob})

    def get(self, key, timeout=None):
        if timeout:
            raise NotImplementedError
        obj = self.col.find_one({'_id': key})
        if obj:
            return pickle.loads(obj['value'])

    def count(self):
        return self.col.find({}).count()

    def delete_entry(self, key):
        return self.col.remove({'_id': key})

    def cleanup(self):
        """MongoDB will automatically clear expired keys."""
        pass

    def flush(self):
        self.col.drop()
        self.col.create_index('created', expireAfterSeconds=self.timeout)

########NEW FILE########
__FILENAME__ = cursor
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from .error import TweepError


class Cursor(object):
    """Pagination helper class"""

    def __init__(self, method, *args, **kargs):
        if hasattr(method, 'pagination_mode'):
            if method.pagination_mode == 'cursor':
                self.iterator = CursorIterator(method, args, kargs)
            elif method.pagination_mode == 'id':
                self.iterator = IdIterator(method, args, kargs)
            elif method.pagination_mode == 'page':
                self.iterator = PageIterator(method, args, kargs)
            else:
                raise TweepError('Invalid pagination mode.')
        else:
            raise TweepError('This method does not perform pagination')

    def pages(self, limit=0):
        """Return iterator for pages"""
        if limit > 0:
            self.iterator.limit = limit
        return self.iterator

    def items(self, limit=0):
        """Return iterator for items in each page"""
        i = ItemIterator(self.iterator)
        i.limit = limit
        return i

class BaseIterator(object):

    def __init__(self, method, args, kargs):
        self.method = method
        self.args = args
        self.kargs = kargs
        self.limit = 0

    def next(self):
        raise NotImplementedError

    def prev(self):
        raise NotImplementedError

    def __iter__(self):
        return self

class CursorIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.next_cursor = -1
        self.prev_cursor = 0
        self.count = 0

    def next(self):
        if self.next_cursor == 0 or (self.limit and self.count == self.limit):
            raise StopIteration
        data, cursors = self.method(
                cursor=self.next_cursor, *self.args, **self.kargs
        )
        self.prev_cursor, self.next_cursor = cursors
        if len(data) == 0:
            raise StopIteration
        self.count += 1
        return data

    def prev(self):
        if self.prev_cursor == 0:
            raise TweepError('Can not page back more, at first page')
        data, self.next_cursor, self.prev_cursor = self.method(
                cursor=self.prev_cursor, *self.args, **self.kargs
        )
        self.count -= 1
        return data

class IdIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.max_id = kargs.get('max_id')
        self.since_id = kargs.get('since_id')
        self.count = 0

    def next(self):
        """Fetch a set of items with IDs less than current set."""
        if self.limit and self.limit == self.count:
            raise StopIteration

        # max_id is inclusive so decrement by one
        # to avoid requesting duplicate items.
        max_id = self.since_id - 1 if self.max_id else None
        data = self.method(max_id = max_id, *self.args, **self.kargs)
        if len(data) == 0:
            raise StopIteration
        self.max_id = data.max_id
        self.since_id = data.since_id
        self.count += 1
        return data

    def prev(self):
        """Fetch a set of items with IDs greater than current set."""
        if self.limit and self.limit == self.count:
            raise StopIteration

        since_id = self.max_id
        data = self.method(since_id = since_id, *self.args, **self.kargs)
        if len(data) == 0:
            raise StopIteration
        self.max_id = data.max_id
        self.since_id = data.since_id
        self.count += 1
        return data

class PageIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.current_page = 0

    def next(self):
        self.current_page += 1
        items = self.method(page=self.current_page, *self.args, **self.kargs)
        if len(items) == 0 or (self.limit > 0 and self.current_page > self.limit):
            raise StopIteration
        return items

    def prev(self):
        if (self.current_page == 1):
            raise TweepError('Can not page back more, at first page')
        self.current_page -= 1
        return self.method(page=self.current_page, *self.args, **self.kargs)

class ItemIterator(BaseIterator):

    def __init__(self, page_iterator):
        self.page_iterator = page_iterator
        self.limit = 0
        self.current_page = None
        self.page_index = -1
        self.count = 0

    def next(self):
        if self.limit > 0 and self.count == self.limit:
            raise StopIteration
        if self.current_page is None or self.page_index == len(self.current_page) - 1:
            # Reached end of current page, get the next page...
            self.current_page = self.page_iterator.next()
            self.page_index = -1
        self.page_index += 1
        self.count += 1
        return self.current_page[self.page_index]

    def prev(self):
        if self.current_page is None:
            raise TweepError('Can not go back more, at first page')
        if self.page_index == 0:
            # At the beginning of the current page, move to next...
            self.current_page = self.page_iterator.prev()
            self.page_index = len(self.current_page)
            if self.page_index == 0:
                raise TweepError('No more items')
        self.page_index -= 1
        self.count -= 1
        return self.current_page[self.page_index]


########NEW FILE########
__FILENAME__ = error
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

class TweepError(Exception):
    """Tweepy exception"""

    def __init__(self, reason, response=None):
        self.reason = unicode(reason)
        self.response = response
        Exception.__init__(self, reason)

    def __str__(self):
        return self.reason


########NEW FILE########
__FILENAME__ = models
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from .error import TweepError
from .utils import parse_datetime, parse_html_value, parse_a_href


class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""
    def __init__(self, max_id=None, since_id=None):
        super(ResultSet, self).__init__()
        self._max_id = max_id
        self._since_id = since_id

    @property
    def max_id(self):
        if self._max_id:
            return self._max_id
        ids = self.ids()
        return max(ids) if ids else None

    @property
    def since_id(self):
        if self._since_id:
            return self._since_id
        ids = self.ids()
        return min(ids) if ids else None

    def ids(self):
        return [item.id for item in self if hasattr(item, 'id')]

class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        try:
            del pickle['_api']  # do not pickle the API reference
        except KeyError:
            pass
        return pickle

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        results = ResultSet()
        for obj in json_list:
            if obj:
                results.append(cls.parse(api, obj))
        return results


class Status(Model):

    @classmethod
    def parse(cls, api, json):
        status = cls(api)
        for k, v in json.items():
            if k == 'user':
                user_model = getattr(api.parser.model_factory, 'user') if api else User
                user = user_model.parse(api, v)
                setattr(status, 'author', user)
                setattr(status, 'user', user)  # DEPRECIATED
            elif k == 'created_at':
                setattr(status, k, parse_datetime(v))
            elif k == 'source':
                if '<' in v:
                    setattr(status, k, parse_html_value(v))
                    setattr(status, 'source_url', parse_a_href(v))
                else:
                    setattr(status, k, v)
                    setattr(status, 'source_url', None)
            elif k == 'retweeted_status':
                setattr(status, k, Status.parse(api, v))
            elif k == 'place':
                if v is not None:
                    setattr(status, k, Place.parse(api, v))
                else:
                    setattr(status, k, None)
            else:
                setattr(status, k, v)
        return status

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)


class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(user, k, parse_datetime(v))
            elif k == 'status':
                setattr(user, k, Status.parse(api, v))
            elif k == 'following':
                # twitter sets this to null if it is false
                if v is True:
                    setattr(user, k, True)
                else:
                    setattr(user, k, False)
            else:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def timeline(self, **kargs):
        return self._api.user_timeline(user_id=self.id, **kargs)

    def friends(self, **kargs):
        return self._api.friends(user_id=self.id, **kargs)

    def followers(self, **kargs):
        return self._api.followers(user_id=self.id, **kargs)

    def follow(self):
        self._api.create_friendship(user_id=self.id)
        self.following = True

    def unfollow(self):
        self._api.destroy_friendship(user_id=self.id)
        self.following = False

    def lists_memberships(self, *args, **kargs):
        return self._api.lists_memberships(user=self.screen_name, *args, **kargs)

    def lists_subscriptions(self, *args, **kargs):
        return self._api.lists_subscriptions(user=self.screen_name, *args, **kargs)

    def lists(self, *args, **kargs):
        return self._api.lists(user=self.screen_name, *args, **kargs)

    def followers_ids(self, *args, **kargs):
        return self._api.followers_ids(user_id=self.id, *args, **kargs)


class DirectMessage(Model):

    @classmethod
    def parse(cls, api, json):
        dm = cls(api)
        for k, v in json.items():
            if k == 'sender' or k == 'recipient':
                setattr(dm, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(dm, k, parse_datetime(v))
            else:
                setattr(dm, k, v)
        return dm

    def destroy(self):
        return self._api.destroy_direct_message(self.id)


class Friendship(Model):

    @classmethod
    def parse(cls, api, json):
        relationship = json['relationship']

        # parse source
        source = cls(api)
        for k, v in relationship['source'].items():
            setattr(source, k, v)

        # parse target
        target = cls(api)
        for k, v in relationship['target'].items():
            setattr(target, k, v)

        return source, target


class Category(Model):

    @classmethod
    def parse(cls, api, json):
        category = cls(api)
        for k, v in json.items():
            setattr(category, k, v)
        return category


class SavedSearch(Model):

    @classmethod
    def parse(cls, api, json):
        ss = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(ss, k, parse_datetime(v))
            else:
                setattr(ss, k, v)
        return ss

    def destroy(self):
        return self._api.destroy_saved_search(self.id)


class SearchResults(ResultSet):

    @classmethod
    def parse(cls, api, json):
        metadata = json['search_metadata']
        results = SearchResults(metadata.get('max_id'), metadata.get('since_id'))
        results.refresh_url = metadata.get('refresh_url')
        results.completed_in = metadata.get('completed_in')
        results.query = metadata.get('query')

        for status in json['statuses']:
            results.append(Status.parse(api, status))
        return results


class List(Model):

    @classmethod
    def parse(cls, api, json):
        lst = List(api)
        for k,v in json.items():
            if k == 'user':
                setattr(lst, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(lst, k, parse_datetime(v))
            else:
                setattr(lst, k, v)
        return lst

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        if isinstance(json_list, dict):
            json_list = json_list['lists']
        for obj in json_list:
            results.append(cls.parse(api, obj))
        return results

    def update(self, **kargs):
        return self._api.update_list(self.slug, **kargs)

    def destroy(self):
        return self._api.destroy_list(self.slug)

    def timeline(self, **kargs):
        return self._api.list_timeline(self.user.screen_name, self.slug, **kargs)

    def add_member(self, id):
        return self._api.add_list_member(self.slug, id)

    def remove_member(self, id):
        return self._api.remove_list_member(self.slug, id)

    def members(self, **kargs):
        return self._api.list_members(self.user.screen_name, self.slug, **kargs)

    def is_member(self, id):
        return self._api.is_list_member(self.user.screen_name, self.slug, id)

    def subscribe(self):
        return self._api.subscribe_list(self.user.screen_name, self.slug)

    def unsubscribe(self):
        return self._api.unsubscribe_list(self.user.screen_name, self.slug)

    def subscribers(self, **kargs):
        return self._api.list_subscribers(self.user.screen_name, self.slug, **kargs)

    def is_subscribed(self, id):
        return self._api.is_subscribed_list(self.user.screen_name, self.slug, id)

class Relation(Model):
    @classmethod
    def parse(cls, api, json):
        result = cls(api)
        for k,v in json.items():
            if k == 'value' and json['kind'] in ['Tweet', 'LookedupStatus']:
                setattr(result, k, Status.parse(api, v))
            elif k == 'results':
                setattr(result, k, Relation.parse_list(api, v))
            else:
                setattr(result, k, v)
        return result

class Relationship(Model):
    @classmethod
    def parse(cls, api, json):
        result = cls(api)
        for k,v in json.items():
            if k == 'connections':
                setattr(result, 'is_following', 'following' in v)
                setattr(result, 'is_followed_by', 'followed_by' in v)
            else:
                setattr(result, k, v)
        return result

class JSONModel(Model):

    @classmethod
    def parse(cls, api, json):
        return json


class IDModel(Model):

    @classmethod
    def parse(cls, api, json):
        if isinstance(json, list):
            return json
        else:
            return json['ids']


class BoundingBox(Model):

    @classmethod
    def parse(cls, api, json):
        result = cls(api)
        if json is not None:
            for k, v in json.items():
                setattr(result, k, v)
        return result

    def origin(self):
        """
        Return longitude, latitude of southwest (bottom, left) corner of
        bounding box, as a tuple.

        This assumes that bounding box is always a rectangle, which
        appears to be the case at present.
        """
        return tuple(self.coordinates[0][0])

    def corner(self):
        """
        Return longitude, latitude of northeast (top, right) corner of
        bounding box, as a tuple.

        This assumes that bounding box is always a rectangle, which
        appears to be the case at present.
        """
        return tuple(self.coordinates[0][2])


class Place(Model):

    @classmethod
    def parse(cls, api, json):
        place = cls(api)
        for k, v in json.items():
            if k == 'bounding_box':
                # bounding_box value may be null (None.)
                # Example: "United States" (id=96683cc9126741d1)
                if v is not None:
                    t = BoundingBox.parse(api, v)
                else:
                    t = v
                setattr(place, k, t)
            elif k == 'contained_within':
                # contained_within is a list of Places.
                setattr(place, k, Place.parse_list(api, v))
            else:
                setattr(place, k, v)
        return place

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['result']['places']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    status = Status
    user = User
    direct_message = DirectMessage
    friendship = Friendship
    saved_search = SavedSearch
    search_results = SearchResults
    category = Category
    list = List
    relation = Relation
    relationship = Relationship

    json = JSONModel
    ids = IDModel
    place = Place
    bounding_box = BoundingBox


########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = parsers
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from .models import ModelFactory
from .utils import import_simplejson
from .error import TweepError


class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class RawParser(Parser):

    def __init__(self):
        pass

    def parse(self, method, payload):
        return payload

    def parse_error(self, payload):
        return payload


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = import_simplejson()

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload)
        except Exception, e:
            raise TweepError('Failed to parse JSON payload: %s' % e)

        needsCursors = method.parameters.has_key('cursor')
        if needsCursors and isinstance(json, dict) and 'previous_cursor' in json and 'next_cursor' in json:
            cursors = json['previous_cursor'], json['next_cursor']
            return json, cursors
        else:
            return json

    def parse_error(self, payload):
        error = self.json_lib.loads(payload)
        if error.has_key('error'):
            return error['error']
        else:
            return error['errors']


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None: return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise TweepError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        if isinstance(json, tuple):
            json, cursors = json
        else:
            cursors = None

        if method.payload_list:
            result = model.parse_list(method.api, json)
        else:
            result = model.parse(method.api, json)

        if cursors:
            return result, cursors
        else:
            return result


########NEW FILE########
__FILENAME__ = streaming
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import logging
import httplib
from socket import timeout
from threading import Thread
from time import sleep

from .models import Status
from .api import API
from .error import TweepError

from .utils import import_simplejson, urlencode_noplus
json = import_simplejson()

STREAM_VERSION = '1.1'


class StreamListener(object):

    def __init__(self, api=None):
        self.api = api or API()

    def on_connect(self):
        """Called once connected to streaming server.

        This will be invoked once a successful response
        is received from the server. Allows the listener
        to perform some work prior to entering the read loop.
        """
        pass

    def on_data(self, raw_data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """
        data = json.loads(raw_data)

        if 'in_reply_to_status_id' in data:
            status = Status.parse(self.api, data)
            if self.on_status(status) is False:
                return False
        elif 'delete' in data:
            delete = data['delete']['status']
            if self.on_delete(delete['id'], delete['user_id']) is False:
                return False
        elif 'limit' in data:
            if self.on_limit(data['limit']['track']) is False:
                return False
        elif 'disconnect' in data:
            if self.on_disconnect(data['disconnect']) is False:
                return False
        else:
            logging.error("Unknown message type: " + str(raw_data))

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return

    def on_disconnect(self, notice):
        """Called when twitter sends a disconnect notice

        Disconnect codes are listed here:
        https://dev.twitter.com/docs/streaming-apis/messages#Disconnect_messages_disconnect
        """
        return


class Stream(object):

    host = 'stream.twitter.com'

    def __init__(self, auth, listener, **options):
        self.auth = auth
        self.listener = listener
        self.running = False
        self.timeout = options.get("timeout", 300.0)
        self.retry_count = options.get("retry_count")
        self.retry_time = options.get("retry_time", 10.0)
        self.snooze_time = options.get("snooze_time",  5.0)
        self.buffer_size = options.get("buffer_size",  1500)
        if options.get("secure", True):
            self.scheme = "https"
        else:
            self.scheme = "http"

        self.api = API()
        self.headers = options.get("headers") or {}
        self.parameters = None
        self.body = None

    def _run(self):
        # Authenticate
        url = "%s://%s%s" % (self.scheme, self.host, self.url)

        # Connect and process the stream
        error_counter = 0
        conn = None
        exception = None
        while self.running:
            if self.retry_count is not None and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                if self.scheme == "http":
                    conn = httplib.HTTPConnection(self.host, timeout=self.timeout)
                else:
                    conn = httplib.HTTPSConnection(self.host, timeout=self.timeout)
                self.auth.apply_auth(url, 'POST', self.headers, self.parameters)
                conn.connect()
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    sleep(self.retry_time)
                else:
                    error_counter = 0
                    self.listener.on_connect()
                    self._read_loop(resp)
            except timeout:
                if self.listener.on_timeout() == False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
            except Exception, exception:
                # any other exception is fatal, so kill loop
                break

        # cleanup
        self.running = False
        if conn:
            conn.close()

        if exception:
            raise

    def _data(self, data):
        if self.listener.on_data(data) is False:
            self.running = False

    def _read_loop(self, resp):

        while self.running and not resp.isclosed():

            # Note: keep-alive newlines might be inserted before each length value.
            # read until we get a digit...
            c = '\n'
            while c == '\n' and self.running and not resp.isclosed():
                c = resp.read(1)
            delimited_string = c

            # read rest of delimiter length..
            d = ''
            while d != '\n' and self.running and not resp.isclosed():
                d = resp.read(1)
                delimited_string += d

            # read the next twitter status object
            if delimited_string.strip().isdigit():
                next_status_obj = resp.read( int(delimited_string) )
                self._data(next_status_obj)

        if resp.isclosed():
            self.on_closed(resp)

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def on_closed(self, resp):
        """ Called when the response has been closed by Twitter """
        pass

    def userstream(self, count=None, async=False, secure=True):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/2/user.json?delimited=length'
        self.host='userstream.twitter.com'
        self._start(async)

    def firehose(self, count=None, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/firehose.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def retweet(self, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/retweet.json?delimited=length' % STREAM_VERSION
        self._start(async)

    def sample(self, count=None, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/sample.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def filter(self, follow=None, track=None, async=False, locations=None, 
        count = None, stall_warnings=False, languages=None):
        self.parameters = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%s/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            self.parameters['follow'] = ','.join(map(str, follow))
        if track:
            self.parameters['track'] = ','.join(map(str, track))
        if locations and len(locations) > 0:
            assert len(locations) % 4 == 0
            self.parameters['locations'] = ','.join(['%.2f' % l for l in locations])
        if count:
            self.parameters['count'] = count
        if stall_warnings:
            self.parameters['stall_warnings'] = stall_warnings
        if languages:
            self.parameters['language'] = ','.join(map(str, languages))
        self.body = urlencode_noplus(self.parameters)
        self.parameters['delimited'] = 'length'
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.running = False


########NEW FILE########
__FILENAME__ = utils
# Tweepy
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re
import locale
from urllib import quote
from email.utils import parsedate


def parse_datetime(string):
    return datetime(*(parsedate(string)[:6]))


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json

def list_to_csv(item_list):
    if item_list:
        return ','.join([str(i) for i in item_list])

def urlencode_noplus(query):
    return '&'.join(['%s=%s' % (quote(str(k), ''), quote(str(v), '')) \
        for k, v in query.iteritems()])

########NEW FILE########
__FILENAME__ = tweeter
from __future__ import unicode_literals
import logging

import tweepy

import models


LOGGER = logging.getLogger(__name__)

SERVICES = [
    'API', 'JS', 'DASH'
]

STATUSES = [
    '', 'UP', 'DOWN', 'ISSUE'
]


class TwitterStatusProcessor(object):
    SEPARATOR = ':'

    def __init__(self, **auth):
        if auth:
            self.auth = tweepy.OAuthHandler(auth['consumer_key'],
                                            auth['consumer_secret'])
            self.auth.set_access_token(auth['token'], auth['token_secret'])

            self.twitter = tweepy.API(
                self.auth,
                api_root='/1.1',
            )

    def _parse_tweet(self, message, created_at, tweet_id, tweet_id_str):
        spec, _, message = message.partition(self.SEPARATOR)
        if not spec:
            return

        spec = spec.split('-')
        service = spec[0]
        if len(spec) > 1:
            state = spec[1]
        else:
            state = ''
        if service not in SERVICES or state not in STATUSES:
            return

        self._insert(service, created_at, message, state, tweet_id_str)

        self._set_last_updated(service, tweet_id)

    def _get_tw_key(self, service=None):
        if not service:
            service = '__general'
        return service + '-timestamp'

    def _set_last_updated(self, service=None, tweet_id=None):
        key = self._get_tw_key(service)
        kv = models.KV(k=key, value=str(tweet_id), key_name=key)
        kv.put()

    def _set_notified(self, tweet_id):
        results = models.Tweet.all()
        results.filter('tweet_id =', tweet_id)

        for tweet in results:
            if tweet:
                tweet.set_notified()

    def _get_last_updated(self, service=None):
        key = self._get_tw_key(service)
        return models.KV.get(key)

    def _insert(self, service, created_at, message, status, tweet_id):
        key = '{}-{}'.format(service, created_at)
        tw = models.Tweet.all().filter('key_name=', key).fetch(1)

        if not tw:
            tw = models.Tweet(
                service=service,
                created_at=created_at,
                message=message,
                status=status,
                key_name=key,
                tweet_id=tweet_id,
                notified=False
            )

            tw.put()

    def _get_tweets(self, min_date):
        filters = {}
        if min_date:
            filters['since_id'] = min_date.value

        return self.twitter.user_timeline(**filters)

    def run(self):
        last_check = self._get_last_updated()

        # get tweets where > last_updated
        tweets = self._get_tweets(last_check)

        for tweet in tweets:
            self._parse_tweet(tweet.text,
                              tweet.created_at,
                              tweet.id,
                              tweet.id_str)

        if tweets:
            max_id = max(tweet.id for tweet in tweets)
            self._set_last_updated(tweet_id=max_id)
            return max_id == last_check

        return False

    def get(self, service=None, count=10):
        tweets = models.Tweet.all().filter(
            'service = ', service
        ).order('-created_at').fetch(limit=count)
        return tweets

    def get_by_date(self, service, date):
        tweets = models.Tweet.all().filter(
            'service = ', service
        ).filter(
            'created_date =', date.strftime('%Y-%m-%d')
        ).order('-created_at')
        return tweets

    def get_by_dates(self, service, min_date, max_date):
        tweets = models.Tweet.all().filter(
            'service = ', service
        ).filter(
            'created_date <=', max_date.strftime('%Y-%m-%d')
        ).filter(
            'created_date >', min_date.strftime('%Y-%m-%d')
        )
        return tweets

    def get_last_message(self, service):
        tweets = models.Tweet.all().filter(
            'service = ', service
        ).order('-created_at').fetch(1)

        try:
            return tweets[0]
        except IndexError:
            return None

    def get_latest_state(self, service):
        tweets = models.Tweet.all().filter(
            'service = ', service
        ).order('-created_at')
        for tweet in tweets:
            if tweet.status:
                return tweet.status
        return None

########NEW FILE########
__FILENAME__ = graphite
from __future__ import unicode_literals
import logging
import urllib2
import json

from . import determine_status


LOGGER = logging.getLogger(__name__)


class Calculator(object):

    def __init__(self, root_uri, username, password, services):
        self.root_uri = root_uri
        self.services = services
        self.username = username
        self.password = password

        self._create_opener_for_uri(self.root_uri)

    def _create_opener_for_uri(self, uri):
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, uri, self.username, self.password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        self.opener = urllib2.build_opener(authhandler)

    def _construct_uri(self, targets, minutes_ago=5):
        return '&'.join([
            self.root_uri,
            'from=-{}minute'.format(minutes_ago),
            'until=now',
            'format=json',
        ] + [
            'target={}'.format(
                self._summarize(t, minutes_ago)) for t in targets
        ])

    def _summarize(self, target, minutes_ago):
        return 'summarize({},\'{}minute\')'.format(target, minutes_ago)

    def _calculate_data(self, stats):
        count = 0
        for item in stats:
            datapoints = item['datapoints']
            count += sum(
                count for count, _ in datapoints if count
            )
        return count

    def _for_service(self, targets, minutes_ago):
        ok_uri = self._construct_uri(targets['OK_TARGETS'], minutes_ago)
        error_uri = self._construct_uri(targets['ERROR_TARGETS'], minutes_ago)

        ok_stats = json.loads(self.opener.open(ok_uri).read())
        error_stats = json.loads(self.opener.open(error_uri).read())

        error_counts = self._calculate_data(error_stats)
        ok_counts = self._calculate_data(ok_stats)
        total_counts = ok_counts + error_counts

        if total_counts:
            percentage = (total_counts - float(error_counts)) / total_counts
        else:
            percentage = 1

        return percentage * 100

    def refresh(self):
        for service, targets in self.services.iteritems():
            # 5 minutes
            five_min_percentage = self._for_service(targets, 5)
            # 60 minutes (1 hour) * 24 (hours) * 30 (days)
            thirty_day_percentage = self._for_service(targets, 60 * 24 * 30)

            yield service, {
                'uptime': thirty_day_percentage,
                'status': determine_status(five_min_percentage)
            }

########NEW FILE########
__FILENAME__ = librato
from __future__ import unicode_literals
import logging
import urllib
import urllib2
import time
import json

from . import determine_status

logger = logging.getLogger(__name__)


class Calculator(object):

    def __init__(self, root_uri, username, password, services):
        self.root_uri = root_uri
        self.services = services
        self.username = username
        self.password = password

        self._create_opener_for_uri(self.root_uri)

    def _create_opener_for_uri(self, uri):
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, uri, self.username, self.password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        self.opener = urllib2.build_opener(authhandler)

    def _construct_url(
        self,
        metrics,
        source,
        start_time,
        end_time,
        resolution=60,
    ):
        return '{}{}?{}'.format(
            self.root_uri,
            metrics,
            urllib.urlencode(dict(
                source=source,
                start_time=int(start_time),
                end_time=int(end_time),
                resolution=resolution,
                summarize_time=1,
            ))
        )

    def _calculate_data(self, stats):
        count = 0
        for _, values in stats.iteritems():
            for item in values:
                count += item['count']
        return count

    def _get_targets_sum(self, key, targets, minutes_ago):
        """Get all count sum in given targets during minutes ago to now period
        and return

        """
        count = 0
        # we need the biggest window to move along time line for reducing
        # requests to a reasonable number. Oterwise, there is 43,200 minutes
        # in a month, if we are using 1 minutes resolution, librato's
        # request limitation is 100 data points per request, so we need
        # 43,200 / 100 which is 432 requests to get sum of all data points
        # in a month. With 3600 seconds (60 minutes or 1 hour) resolution,
        # we only need 43,200 / (60 * 100) = 7 requests. This still sucks,
        # but at least it is not a thousand requests. Oh, by the way, by
        # setting the resolution to an hour, it's not so accurate. Looks
        # like some data points are dropped
        resolution = 60
        if minutes_ago > 3600 / 60:
            resolution = 3600
        end_time = int(time.time())
        start_time = end_time - (minutes_ago * 60)
        for metrics in targets[key]:
            while True:
                url = self._construct_url(
                    metrics,
                    targets['SOURCE'],
                    start_time=start_time,
                    end_time=end_time,
                    resolution=resolution,
                )
                logger.debug('Fetching %s', url)
                response = json.loads(self.opener.open(url).read())
                count += self._calculate_data(response['measurements'])
                if response.get('query', {}).get('next_time'):
                    start_time = response['query']['next_time']
                else:
                    break
        return count

    def _for_service(self, targets, minutes_ago):
        total_count = self._get_targets_sum('TOTAL_TARGETS', targets, minutes_ago)
        error_count = self._get_targets_sum('ERROR_TARGETS', targets, minutes_ago)

        if total_count:
            percentage = (total_count - float(error_count)) / total_count
        else:
            percentage = 1

        logger.info(
            'TOTAL=%s, ERROR=%s, PERCENTAGE=%s',
            total_count, error_count, percentage * 100,
        )

        return percentage * 100

    def refresh(self):
        for service, targets in self.services.iteritems():
            # 5 minutes
            five_min_percentage = self._for_service(targets, 5)
            # 60 minutes (1 hour) * 24 (hours) * 30 (days)
            thirty_day_percentage = self._for_service(targets, 60 * 24 * 30)
            status = determine_status(five_min_percentage)

            logger.info(
                'Service %s, 30 days percentage: %s, status: %s',
                service, thirty_day_percentage, status,
            )
            yield service, {
                'uptime': thirty_day_percentage,
                'status': status,
            }

########NEW FILE########
__FILENAME__ = test_librato_uptime
import os
import sys
import unittest
import json

sys.path.insert(0, os.path.abspath('./situation'))
sys.path.insert(0, os.path.abspath('./'))

from situation.uptime.librato import Calculator
from google.appengine.ext import testbed
import mock


UPTIME_CFG = {
    'root_uri': 'https://metrics-api.librato.com/v1/metrics/',
    'username': 'MOCK_USERNAME',
    'password': 'MOCK_PWD',
    'services': {
        'API': {
            'SOURCE': '*bapi-live*',
            'TOTAL_TARGETS': [
                'MOCK_TOTAL_TARGET_A',
                'MOCK_TOTAL_TARGET_B',
            ],
            'ERROR_TARGETS': [
                'MOCK_ERROR_TARGET_A',
                'MOCK_ERROR_TARGET_B',
                'MOCK_ERROR_TARGET_C',
            ]
        },
    }
}


class TestLibratoUptime(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()

    def tearDown(self):
        self.testbed.deactivate()

    def test_service_uptime(self):
        index = [0]
        resps = [
            # TOTAL A
            dict(
                measurements=dict(
                    foobar=[dict(count=1), dict(count=7788), dict(count=123)],
                ),
                query=dict(next_time=999),
            ),
            dict(
                measurements=dict(
                    foobar=[dict(count=888)],
                ),
            ),
            # TOTAL B
            dict(
                measurements=dict(
                    foobar=[dict(count=3), dict(count=4)],
                )
            ),
            # ERROR A
            dict(
                measurements=dict(
                    foobar=[dict(count=5)],
                    barfoo=[dict(count=78)],
                )
            ),
            # ERROR B
            dict(
                measurements=dict(
                    foobar=[dict(count=6)],
                    barfoo=[dict(count=78)],
                )
            ),
            # ERROR C
            dict(
                measurements=dict(
                    foobar=[dict(count=0)],
                )
            ),
        ]

        def read():
            result = resps[index[0]]
            index[0] += 1
            return json.dumps(result)

        calculator = Calculator(**UPTIME_CFG)
        calculator.opener = mock.Mock()
        calculator.opener.open.return_value = mock.Mock()
        calculator.opener.open.return_value.read.side_effect = read

        result = calculator._for_service(calculator.services['API'], 5)
        total_number = (
            (1 + 7788 + 123) +
            (888) +
            (3 + 4)
        )
        error_number = (
            (5 + 78) +
            (6 + 78) +
            (0)
        )
        expected_result = ((total_number - float(error_number)) / total_number) * 100
        self.assertEqual(result, expected_result)

########NEW FILE########
__FILENAME__ = test_sms
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('./situation'))
sys.path.insert(0, os.path.abspath('./'))

from situation import sms
from twilio.rest import TwilioException
from google.appengine.ext import testbed
from . import skip_auth


class TestSMS(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_logservice_stub()

    def tearDown(self):
        self.testbed.deactivate()

    # Assert that trying to send a SMS over 160 characters gets truncated
    # before attempting to send with Twilio
    @skip_auth()
    def test_sms_max_length(self):
        response = None
        try:
            twilio = sms.SMS()
            response = twilio.send(
                '+15005550000',
                'This is a super duper long sms message that is over ' +
                'one hundred and sixty characters, but should be auto ' +
                'truncated by the SMS class before attempting to  ' +
                'send via Twilio.')
        except TwilioException:
            pass

        self.assertIsNotNone(response, 'Failed to send SMS message over 160 characters with Twilio')

########NEW FILE########
__FILENAME__ = test_subscription
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('./situation'))
sys.path.insert(0, os.path.abspath('./'))

from situation import main, subscription, models
from google.appengine.ext import testbed
import webapp2
import mock


class TestSubscription(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_logservice_stub()
        self.testbed.init_mail_stub()

        # Create default API ServiceStatus
        default_api = models.ServiceStatus(service='API', current='UP')
        default_api.put()

        # Create default DASHBOARD ServiceStatus
        default_dashboard = models.ServiceStatus(service='DASHBOARD',
                                                 current='UP')
        default_dashboard.put()

        # Create default JS ServiceStatus
        default_js = models.ServiceStatus(service='JS', current='UP')
        default_js.put()

    def tearDown(self):
        self.testbed.deactivate()

    def _assert_expectations(self, tests):
        for index, (service, status, expected) in enumerate(tests, start=1):
            result = subscription.should_notify(service, status, None)
            self.assertEqual(result, expected,
                             'Assertion failed for case# {}'.format(index))

    def test_should_notify_api(self):
        tests = [
            ('API', 'DOWN', True),
            ('API', 'ISSUE', False),
            ('API', 'DOWN', False),
            ('API', 'ISSUE', False),
            ('API', 'UP', True),
            ('API', 'DOWN', True),
            ('API', 'UP', True),
            ('API', 'ISSUE', False),
            ('API', 'UP', False),
            ('API', 'UP', False),
            ('API', 'DOWN', True),
            ('API', 'DOWN', False),
            ('API', 'UP', True),
            ('API', 'ISSUE', False),
            ('API', 'DOWN', True)
        ]

        self._assert_expectations(tests)

    def test_should_notify_dashboard(self):
        tests = [
            ('DASHBOARD', 'DOWN', True),
            ('DASHBOARD', 'ISSUE', False),
            ('DASHBOARD', 'DOWN', False),
            ('DASHBOARD', 'ISSUE', False),
            ('DASHBOARD', 'UP', True),
            ('DASHBOARD', 'DOWN', True),
            ('DASHBOARD', 'UP', True),
            ('DASHBOARD', 'ISSUE', False),
            ('DASHBOARD', 'UP', False),
            ('DASHBOARD', 'UP', False),
            ('DASHBOARD', 'DOWN', True),
            ('DASHBOARD', 'DOWN', False),
            ('DASHBOARD', 'UP', True),
            ('DASHBOARD', 'ISSUE', False),
            ('DASHBOARD', 'DOWN', True)
        ]

        self._assert_expectations(tests)

    def test_should_notify_js(self):
        tests = [
            ('JS', 'DOWN', True),
            ('JS', 'ISSUE', False),
            ('JS', 'DOWN', False),
            ('JS', 'ISSUE', False),
            ('JS', 'UP', True),
            ('JS', 'DOWN', True),
            ('JS', 'UP', True),
            ('JS', 'ISSUE', False),
            ('JS', 'UP', False),
            ('JS', 'UP', False),
            ('JS', 'DOWN', True),
            ('JS', 'DOWN', False),
            ('JS', 'UP', True),
            ('JS', 'ISSUE', False),
            ('JS', 'DOWN', True)
        ]

        self._assert_expectations(tests)

    def test_subscribe_email(self):
        request = webapp2.Request.blank(path='/subscriptions/email', POST={
            'email': 'foo@bar.com',
            'services': 'API,DASH,JS'
        })

        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200, 'Failed to get back a 200 status code from POST /subscriptions/email')
        self.assertEqual(response.body, '{"services": ["API", "DASH", "JS"], "subscribed": "email"}')

    @mock.patch('situation.sms.SMS.send')
    def test_subscribe_sms(self, send_method):
        # +15005550000 is a special testing Twilio number that passes their checks
        request = webapp2.Request.blank(path='/subscriptions/sms', POST={
            'phone': '+15005550000',
            'services': 'API,DASH,JS'
        })

        response = request.get_response(main.app)
        self.assertEqual(response.status_int, 200, 'Failed to get back a 200 status code from POST /subscriptions/sms')
        self.assertEqual(response.body, '{"services": ["API", "DASH", "JS"], "subscribed": "sms"}')
        send_method.assert_called_once_with(
            '+15005550000',
            'Successfully subscribed to Balanced API,DASH,JS incidents. Reply '
            'with STOP to unsubscribe.'
        )

########NEW FILE########
__FILENAME__ = test_twitter
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('./situation'))
sys.path.insert(0, os.path.abspath('./'))

from situation import settings, tweeter
from situation.tweepy import TweepError
from google.appengine.ext import testbed
from . import skip_auth


class TestTwitter(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_logservice_stub()

    def tearDown(self):
        self.testbed.deactivate()

    # Assert that fetching timeline tweets from twitter does not throw an exception
    @skip_auth()
    def test_get_tweets(self):
        t = tweeter.TwitterStatusProcessor(**settings.TWITTER['AUTH'])

        tweets = []
        try:
            tweets = t._get_tweets(None)
        except TweepError:
            pass

        self.assertGreater(len(tweets), 0, 'Failed to fetch timeline tweets from twitter')

########NEW FILE########
