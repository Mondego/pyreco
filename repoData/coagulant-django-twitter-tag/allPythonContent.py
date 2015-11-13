__FILENAME__ = test_functional
# coding: utf-8
# from __future__ import unicode_literals
# import os
# import mock
# from django.conf import settings
# from nose.plugins.attrib import attr
# from nose.tools import nottest
# from .utils import render_template
#
#
# @nottest
# @attr('functional')
# @mock.patch.multiple(settings, TWITTER_OAUTH_TOKEN=os.environ.get('OAUTH_TOKEN'),
#                                TWITTER_OAUTH_SECRET=os.environ.get('OAUTH_SECRET'),
#                                TWITTER_CONSUMER_KEY=os.environ.get('CONSUMER_KEY'),
#                                TWITTER_CONSUMER_SECRET=os.environ.get('CONSUMER_SECRET'), create=True)
# def test_func():
#     o, c = render_template("""{% search_tweets for "питон" as tweets %}""")
#     for t in c['tweets']:
#         assert 'питон' in t['html'].lower()
########NEW FILE########
__FILENAME__ = test_tag
# coding: utf-8
from __future__ import unicode_literals
import json
import unittest
import warnings
import datetime

from mock import patch
from nose.tools import nottest
from sure import expect
from django.conf import settings
from django.core.cache import cache
from django.template import Template, TemplateSyntaxError
from django.utils import timezone
from httpretty import httprettified, HTTPretty
from tests.utils import render_template, clear_query_dict, get_json

from twitter_tag.utils import get_user_cache_key


class TwitterTag(unittest.TestCase):
    api_url = None
    logger_name = 'twitter_tag.templatetags.twitter_tag'

    @httprettified
    def check_render(self, template, json_mock, expected_kwargs, length=None, asvar='tweets'):
        output, context = self.render(template, json_mock)

        expect(output).should.be.empty
        expect(clear_query_dict(HTTPretty.last_request.querystring)).should.equal(expected_kwargs)
        if length is None:
            length = len(json.loads(get_json(json_mock).decode('utf8')))
        expect(context[asvar]).should.have.length_of(length)
        return context

    def render(self, template, json_mocks):
        if type(json_mocks) is not list:
            json_mocks = [json_mocks]
        responses = [HTTPretty.Response(get_json(_)) for _ in json_mocks]

        HTTPretty.register_uri(HTTPretty.GET, self.api_url, responses=responses, content_type='application/json')
        return render_template(template=template)


@patch.multiple(settings, TWITTER_OAUTH_TOKEN='foo', TWITTER_OAUTH_SECRET='bar',
                TWITTER_CONSUMER_KEY='baz', TWITTER_CONSUMER_SECRET='Alice', create=True)
class UsernameTag(TwitterTag):
    api_url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'

    def test_no_args(self):
        context = self.check_render(
            template="""{% get_tweets for "jresig" as tweets %}""",
            json_mock='jeresig.json',
            expected_kwargs={'screen_name': ['jresig']},
        )
        expect(context['tweets'][0]['text']).to.equal("This is not John Resig - you should be following @jeresig instead!!!")

    def test_limit(self):
        self.check_render(
            template="""{% get_tweets for "futurecolors" as tweets limit 2 %}""",
            json_mock='coagulant.json',
            expected_kwargs={'screen_name': ['futurecolors']},
            length=2
        )

    def test_exclude_replies(self):
        self.check_render(
            template="""{% get_tweets for "futurecolors" as tweets exclude 'replies' %}""",
            json_mock='coagulant.json',
            expected_kwargs={'screen_name': ['futurecolors'], 'exclude_replies': ['True']},
        )

    def test_exclude_retweets(self):
        self.check_render(
            template="""{% get_tweets for "coagulant" as tweets exclude 'retweets' %}""",
            json_mock='coagulant.json',
            expected_kwargs={'screen_name': ['coagulant'], 'include_rts': ['False']},
        )

    def test_exclude_all(self):
        self.check_render(
            template="""{% get_tweets for "coagulant" as tweets exclude 'replies,rts' %}""",
            json_mock='coagulant.json',
            expected_kwargs={'screen_name': ['coagulant'], 'exclude_replies': ['True'], 'include_rts': ['False']},
        )

    @httprettified
    def test_several_twitter_tags_on_page(self):
        output, context = self.render(
            template="""{% get_tweets for "jresig" as tweets %}{% get_tweets for "coagulant" as more_tweets %}""",
            json_mocks=['jeresig.json', 'coagulant.json'],
        )
        expect(output).should.be.empty
        expect(context['tweets']).should.have.length_of(1)
        expect(context['more_tweets']).should.have.length_of(3)

    def test_bad_syntax(self):
        Template.when.called_with("""{% get_tweets %}""").should.throw(TemplateSyntaxError)
        Template.when.called_with("""{% get_tweets as "tweets" %}""").should.throw(TemplateSyntaxError)

    @patch('logging.getLogger')
    @httprettified
    def test_exception_is_not_propagated_but_logged(self, logging_mock):
        exception_message = 'Capacity Error'
        HTTPretty.register_uri(HTTPretty.GET, self.api_url, body=exception_message, status=503, content_encoding='identity')
        output, context = render_template("""{% get_tweets for "twitter" as tweets %}""")
        expect(output).should.be.empty
        expect(context['tweets']).should.be.empty

        logging_mock.assert_called_with(self.logger_name)
        expect(logging_mock.return_value.error.call_args[0][0]).should.contain(exception_message)

    @patch('logging.getLogger')
    @httprettified
    def test_get_from_cache_when_twitter_api_fails(self, logging_mock):
        exception_message = 'Too many requests'
        HTTPretty.register_uri(HTTPretty.GET, self.api_url,
                               responses=[
                                   HTTPretty.Response(body=get_json('jeresig.json'), status=200, content_encoding='identity'),
                                   HTTPretty.Response(body=exception_message, status=429, content_encoding='identity'),
                               ])

        # it should be ok by now
        output, context = render_template("""{% get_tweets for "jresig" as tweets %}""")
        cache_key = get_user_cache_key(asvar='tweets', username='jresig')
        expect(cache.get(cache_key)).should.have.length_of(1)
        expect(context['tweets'][0]['text']).to.equal("This is not John Resig - you should be following @jeresig instead!!!")

        # when twitter api fails, should use cache
        output2, context2 = render_template("""{% get_tweets for "jresig" as tweets %}""")
        expect(cache.get(cache_key)).should.have.length_of(1)
        expect(context2['tweets'][0]['text']).to.equal("This is not John Resig - you should be following @jeresig instead!!!")
        logging_mock.assert_called_with(self.logger_name)
        expect(logging_mock.return_value.error.call_args[0][0]).should.contain(exception_message)

    @httprettified
    def test_cache_key_portable(self):
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            output, context = self.render(
                template="""{% get_tweets for "jresig" as tweets exclude 'replies, retweets' %}""",
                json_mocks=['jeresig.json'],
            )
            assert len(caught_warnings) == 0

    @httprettified
    def test_datetime(self):
        output, context = self.render(
            template="""{% get_tweets for "jresig" as tweets %}""",
            json_mocks='jeresig.json',
        )
        # Fri Mar 21 19:42:21 +0000 2008
        if settings.USE_TZ:
            # Get utc.
            (context['tweets'][0]['datetime']).should.be.equal(datetime.datetime(2008, 3, 21, 19, 42, 21).replace(tzinfo=timezone.utc))
        else:
            (context['tweets'][0]['datetime']).should.be.equal(datetime.datetime(2008, 3, 21, 19, 42, 21))


    @httprettified
    def test_html_mentions(self):
        output, context = self.render(
            template="""{% get_tweets for "jresig" as tweets %}""",
            json_mocks='jeresig.json',
        )
        (context['tweets'][0]['html']).should.be.equal("""This is not John Resig - you should be following <a href=\"https://twitter.com/jeresig\">@jeresig</a> instead!!!""")

    @httprettified
    def test_expand_urlize(self):
        output, context = self.render(
            template="""{% get_tweets for "futurecolors" as tweets %}""",
            json_mocks='futurecolors.json',
        )
        tweet = context['tweets'][0]

        expect(tweet['text'].endswith('...')).should.be.true  # original response is trimmed by api...
        expect(tweet['html'].endswith('...')).should.be.false  # but not ours html ;)
        expect(tweet['html'].startswith('RT <a href="https://twitter.com/travisci">@travisci</a>: ')).should.be.true


def test_settings():
    render_template.when.called_with('{% get_tweets for "futurecolors" as tweets %}').should.throw(AttributeError)


@patch.multiple(settings, TWITTER_OAUTH_TOKEN='foo', TWITTER_OAUTH_SECRET='bar',
                TWITTER_CONSUMER_KEY='baz', TWITTER_CONSUMER_SECRET='Alice', create=True)
class SearchTag(TwitterTag):
    api_url = 'https://api.twitter.com/1.1/search/tweets.json'

    def test_search(self):
        self.check_render(
            template="""{% search_tweets for "python 3" as tweets %}""",
            json_mock='python3.json',
            expected_kwargs={'q': ['python 3']},
            length=15
        )

    def test_custom_args(self):
        self.check_render(
            template="""{% search_tweets for "python 3" as tweets lang='eu' result_type='popular' %}""",
            json_mock='python3.json',
            expected_kwargs={'q': ['python 3'], 'lang': ['eu'], 'result_type': ['popular']},
            length=15
        )

    @httprettified
    def test_html_hashtags(self):
        output, context = self.render(
            template="""{% search_tweets for "python 3" as tweets %}""",
            json_mocks='python3.json',
        )
        tweet_html = context['tweets'][0]['html']
        expect(tweet_html).should.contain('<a href="https://twitter.com/search?q=%23python">#python')
        expect(tweet_html).should.contain('<a href="https://twitter.com/search?q=%23%D0%9A%D0%B0%D1%83%D1%87%D0%94%D0%91">#КаучДБ')

    @nottest  # https://github.com/gabrielfalcao/HTTPretty/issues/36')
    @httprettified
    def test_unicode_query(self):
        self.check_render(
            template=u"""{% search_tweets for "питон" as tweets %}""",
            json_mock='python3.json',
            expected_kwargs={'q': ['питон']},
            length=15
        )
########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
import io
import os
from django.template import Context, Template


def render_template(template):
    context = Context()
    template = Template('{% load twitter_tag %}'+template)
    output = template.render(context)
    return output, context


def clear_query_dict(query):
    oauth_keys = [
        'oauth_consumer_key',
        'oauth_nonce',
        'oauth_signature',
        'oauth_signature_method',
        'oauth_timestamp',
        'oauth_token',
        'oauth_version'
    ]
    return dict((k, v) for k, v in query.items() if k not in oauth_keys)


def get_json(somefile):
    with io.open(os.path.join('tests', 'json', somefile), mode='rb') as f:
        return f.read()
########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from appconf import AppConf


class TwitterConf(AppConf):
    class Meta:
        prefix = 'twitter'
        required = ['OAUTH_TOKEN', 'OAUTH_SECRET', 'CONSUMER_KEY', 'CONSUMER_SECRET']
########NEW FILE########
__FILENAME__ = twitter_tag
from __future__ import unicode_literals
from datetime import datetime
from six.moves import http_client
import logging

from django import template
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from twitter import Twitter, OAuth, TwitterError
from classytags.core import Tag, Options
from classytags.arguments import Argument, MultiKeywordArgument

from ..utils import *

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError

register = template.Library()


class BaseTwitterTag(Tag):
    """ Abstract twitter tag"""

    def get_cache_key(self, args_disct):
        raise NotImplementedError

    def get_json(self, twitter):
        raise NotImplementedError

    def get_api_call_params(self, **kwargs):
        raise NotImplementedError

    def enrich(self, tweet):
        """ Apply the local presentation logic to the fetched data."""
        tweet = urlize_tweet(expand_tweet_urls(tweet))
        # parses created_at "Wed Aug 27 13:08:45 +0000 2008"

        if settings.USE_TZ:
            tweet['datetime'] = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y').replace(tzinfo=timezone.utc)
        else:
            tweet['datetime'] = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')

        return tweet

    def render_tag(self, context, **kwargs):
        cache_key = self.get_cache_key(kwargs)

        try:
            twitter = Twitter(auth=OAuth(settings.TWITTER_OAUTH_TOKEN,
                                         settings.TWITTER_OAUTH_SECRET,
                                         settings.TWITTER_CONSUMER_KEY,
                                         settings.TWITTER_CONSUMER_SECRET))
            json = self.get_json(twitter, **self.get_api_call_params(**kwargs))
        except (TwitterError, URLError, ValueError, http_client.HTTPException) as e:
            logging.getLogger(__name__).error(str(e))
            context[kwargs['asvar']] = cache.get(cache_key, [])
            return ''

        json = [self.enrich(tweet) for tweet in json]

        if kwargs['limit']:
            json = json[:kwargs['limit']]
        context[kwargs['asvar']] = json
        cache.set(cache_key, json)

        return ''


class UserTag(BaseTwitterTag):
    """ A django template tag to display user's recent tweets.

        :type context: list
        :type username: string
        :type asvar: string
        :type exclude: string
        :type limit: string

        NB: count argument of twitter API is not useful, so we slice it ourselves
            "We include retweets in the count, even if include_rts is not supplied.
             It is recommended you always send include_rts=1 when using this API method."

        Examples:
        {% get_tweets for "futurecolors" as tweets exclude "replies" limit 10 %}
        {% get_tweets for "futurecolors" as tweets exclude "retweets" %}
        {% get_tweets for "futurecolors" as tweets exclude "retweets,replies" limit 1 %}
    """
    name = 'get_tweets'
    options = Options(
        'for', Argument('username'),
        'as', Argument('asvar', resolve=False),
        'exclude', Argument('exclude', required=False),
        'limit', Argument('limit', required=False),
    )

    def get_cache_key(self, kwargs_dict):
        return get_user_cache_key(**kwargs_dict)

    def get_api_call_params(self, **kwargs):
        params = {'screen_name': kwargs['username']}
        if kwargs['exclude']:
            if 'replies' in kwargs['exclude']:
                params['exclude_replies'] = True
            if 'retweets' in kwargs['exclude'] or 'rts' in kwargs['exclude']:
                params['include_rts'] = False
        return params

    def get_json(self, twitter, **kwargs):
        return twitter.statuses.user_timeline(**kwargs)


class SearchTag(BaseTwitterTag):
    name = 'search_tweets'
    options = Options(
        'for', Argument('q'),
        'as', Argument('asvar', resolve=False),
        MultiKeywordArgument('options', required=False),
        'limit', Argument('limit', required=False),
    )

    def get_cache_key(self, kwargs_dict):
        return get_search_cache_key(kwargs_dict)

    def get_api_call_params(self, **kwargs):
        params = {'q': kwargs['q'].encode('utf-8')}
        params.update(kwargs['options'])
        return params

    def get_json(self, twitter, **kwargs):
        return twitter.search.tweets(**kwargs)['statuses']


register.tag(UserTag)
register.tag(SearchTag)
########NEW FILE########
__FILENAME__ = test_settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

SECRET_KEY = '_'
INSTALLED_APPS = ('twitter_tag',)
########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
import re
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote


def get_user_cache_key(**kwargs):
    """ Generate suitable key to cache twitter tag context
    """
    key = 'get_tweets_%s' % ('_'.join([str(kwargs[key]) for key in sorted(kwargs) if kwargs[key]]))
    not_allowed = re.compile('[^%s]' % ''.join([chr(i) for i in range(33, 128)]))
    key = not_allowed.sub('', key)
    return key


def get_search_cache_key(prefix, *args):
    """ Generate suitable key to cache twitter tag context
    """
    key = '%s_%s' % (prefix, '_'.join([str(arg) for arg in args if arg]))
    not_allowed = re.compile('[^%s]' % ''.join([chr(i) for i in range(33, 128)]))
    key = not_allowed.sub('', key)
    return key


TWITTER_HASHTAG_URL = '<a href="https://twitter.com/search?q=%%23%s">#%s</a>'
TWITTER_USERNAME_URL = '<a href="https://twitter.com/%s">@%s</a>'


def urlize_tweet(tweet):
    """ Turn #hashtag and @username in a text to Twitter hyperlinks,
        similar to the ``urlize()`` function in Django.
    """
    text = tweet.get('html', tweet['text'])
    for hash in tweet['entities']['hashtags']:
        text = text.replace('#%s' % hash['text'], TWITTER_HASHTAG_URL % (quote(hash['text'].encode("utf-8")), hash['text']))
    for mention in tweet['entities']['user_mentions']:
        text = text.replace('@%s' % mention['screen_name'], TWITTER_USERNAME_URL % (quote(mention['screen_name']), mention['screen_name']))
    tweet['html'] = text
    return tweet


def expand_tweet_urls(tweet):
    """ Replace shortened URLs with long URLs in the twitter status, and add the "RT" flag.
        Should be used before urlize_tweet
    """
    if 'retweeted_status' in tweet:
        text = 'RT @{user}: {text}'.format(user=tweet['retweeted_status']['user']['screen_name'],
                                           text=tweet['retweeted_status']['text'])
        urls = tweet['retweeted_status']['entities']['urls']
    else:
        text = tweet['text']
        urls = tweet['entities']['urls']

    for url in urls:
        text = text.replace(url['url'], '<a href="%s">%s</a>' % (url['expanded_url'], url['display_url']))
    tweet['html'] = text
    return tweet
########NEW FILE########
