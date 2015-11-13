__FILENAME__ = cass
from datetime import datetime
from uuid import uuid1, UUID
import random

from cassandra.cluster import Cluster

cluster = Cluster(['127.0.0.1'])
session = cluster.connect('twissandra')

# Prepared statements, reuse as much as possible by binding new values
tweets_query = None
userline_query = None
timeline_query = None
friends_query = None
followers_query = None
remove_friends_query = None
remove_followers_query = None
add_user_query = None
get_tweets_query = None
get_usernames_query = None
get_followers_query = None
get_friends_query = None

# NOTE: Having a single userline key to store all of the public tweets is not
#       scalable.  This result in all public tweets being stored in a single
#       partition, which means they must all fit on a single node.
#
#       One fix for this is to partition the timeline by time, so we could use
#       a key like !PUBLIC!2010-04-01 to partition it per day.  We could drill
#       down even further into hourly keys, etc.  Since this is a demonstration
#       and that would add quite a bit of extra code, this excercise is left to
#       the reader.
PUBLIC_USERLINE_KEY = '!PUBLIC!'


class DatabaseError(Exception):
    """
    The base error that functions in this module will raise when things go
    wrong.
    """
    pass


class NotFound(DatabaseError):
    pass


class InvalidDictionary(DatabaseError):
    pass


def _get_line(table, username, start, limit):
    """
    Gets a timeline or a userline given a username, a start, and a limit.
    """
    global get_tweets_query
    if get_tweets_query is None:
        get_tweets_query = session.prepare("""
            SELECT * FROM tweets WHERE tweet_id=?
            """)

    # First we need to get the raw timeline (in the form of tweet ids)
    query = "SELECT time, tweet_id FROM {table} WHERE username=%s {time_clause} LIMIT %s"

    # See if we need to start our page at the beginning or further back
    if not start:
        time_clause = ''
        params = (username, limit)
    else:
        time_clause = 'AND time < %s'
        params = (username, UUID(start), limit)

    query = query.format(table=table, time_clause=time_clause)

    results = session.execute(query, params)
    if not results:
        return [], None

    # If we didn't get to the end, return a starting point for the next page
    if len(results) == limit:
        # Find the oldest ID
        oldest_timeuuid = min(row.time for row in results)

        # Present the string version of the oldest_timeuuid for the UI
        next_timeuuid = oldest_timeuuid.urn[len('urn:uuid:'):]
    else:
        next_timeuuid = None

    # Now we fetch the tweets themselves
    futures = []
    for row in results:
        futures.append(session.execute_async(
            get_tweets_query, (row.tweet_id,)))

    tweets = [f.result()[0] for f in futures]
    return (tweets, next_timeuuid)


# QUERYING APIs

def get_user_by_username(username):
    """
    Given a username, this gets the user record.
    """
    global get_usernames_query
    if get_usernames_query is None:
        get_usernames_query = session.prepare("""
            SELECT * FROM users WHERE username=?
            """)

    rows = session.execute(get_usernames_query, (username,))
    if not rows:
        raise NotFound('User %s not found' % (username,))
    else:
        return rows[0]


def get_friend_usernames(username, count=5000):
    """
    Given a username, gets the usernames of the people that the user is
    following.
    """
    global get_friends_query
    if get_friends_query is None:
        get_friends_query = session.prepare("""
            SELECT friend FROM friends WHERE username=? LIMIT ?
            """)

    rows = session.execute(get_friends_query, (username, count))
    return [row.friend for row in rows]


def get_follower_usernames(username, count=5000):
    """
    Given a username, gets the usernames of the people following that user.
    """
    global get_followers_query
    if get_followers_query is None:
        get_followers_query = session.prepare("""
            SELECT follower FROM followers WHERE username=? LIMIT ?
            """)

    rows = session.execute(get_followers_query, (username, count))
    return [row.follower for row in rows]


def get_users_for_usernames(usernames):
    """
    Given a list of usernames, this gets the associated user object for each
    one.
    """
    global get_usernames_query
    if get_usernames_query is None:
        get_usernames_query = session.prepare("""
            SELECT * FROM users WHERE username=?
            """)

    futures = []
    for user in usernames:
        future = session.execute_async(get_usernames_query, (user, ))
        futures.append(future)

    users = []
    for user, future in zip(usernames, futures):
        results = future.result()
        if not results:
            raise NotFound('User %s not found' % (user,))
        users.append(results[0])

    return users


def get_friends(username, count=5000):
    """
    Given a username, gets the people that the user is following.
    """
    friend_usernames = get_friend_usernames(username, count=count)
    return get_users_for_usernames(friend_usernames)


def get_followers(username, count=5000):
    """
    Given a username, gets the people following that user.
    """
    follower_usernames = get_follower_usernames(username, count=count)
    return get_users_for_usernames(follower_usernames)


def get_timeline(username, start=None, limit=40):
    """
    Given a username, get their tweet timeline (tweets from people they follow).
    """
    return _get_line("timeline", username, start, limit)


def get_userline(username, start=None, limit=40):
    """
    Given a username, get their userline (their tweets).
    """
    return _get_line("userline", username, start, limit)


def get_tweet(tweet_id):
    """
    Given a tweet id, this gets the entire tweet record.
    """
    global get_tweets_query
    if get_tweets_query is None:
        get_tweets_query = session.prepare("""
            SELECT * FROM tweets WHERE tweet_id=?
            """)

    results = session.execute(get_tweets_query, (tweet_id, ))
    if not results:
        raise NotFound('Tweet %s not found' % (tweet_id,))
    else:
        return results[0]


def get_tweets_for_tweet_ids(tweet_ids):
    """
    Given a list of tweet ids, this gets the associated tweet object for each
    one.
    """
    global get_tweets_query
    if get_tweets_query is None:
        get_tweets_query = session.prepare("""
            SELECT * FROM tweets WHERE tweet_id=?
            """)

    futures = []
    for tweet_id in tweet_ids:
        futures.append(session.execute_async(get_tweets_query, (tweet_id,)))

    tweets = []
    for tweet_id, future in zip(tweet_id, futures):
        result = future.result()
        if not result:
            raise NotFound('Tweet %s not found' % (tweet_id,))
        else:
            tweets.append(result[0])

    return tweets


# INSERTING APIs

def save_user(username, password):
    """
    Saves the user record.
    """
    global add_user_query
    if add_user_query is None:
        add_user_query = session.prepare("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
            """)

    session.execute(add_user_query, (username, password))


def _timestamp_to_uuid(time_arg):
    # TODO: once this is in the python Cassandra driver, use that
    microseconds = int(time_arg * 1e6)
    timestamp = int(microseconds * 10) + 0x01b21dd213814000L

    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL

    rand_bits = random.getrandbits(8 + 8 + 48)
    clock_seq_low = rand_bits & 0xffL
    clock_seq_hi_variant = 0b10000000 | (0b00111111 & ((rand_bits & 0xff00L) >> 8))
    node = (rand_bits & 0xffffffffffff0000L) >> 16
    return UUID(
        fields=(time_low, time_mid, time_hi_version, clock_seq_hi_variant, clock_seq_low, node),
        version=1)


def save_tweet(tweet_id, username, tweet, timestamp=None):
    """
    Saves the tweet record.
    """

    global tweets_query
    global userline_query
    global timeline_query

    # Prepare the statements required for adding the tweet into the various timelines
    # Initialise only once, and then re-use by binding new values
    if tweets_query is None:
        tweets_query = session.prepare("""
            INSERT INTO tweets (tweet_id, username, body)
            VALUES (?, ?, ?)
            """)

    if userline_query is None:
        userline_query = session.prepare("""
            INSERT INTO userline (username, time, tweet_id)
            VALUES (?, ?, ?)
            """)

    if timeline_query is None:
        timeline_query = session.prepare("""
            INSERT INTO timeline (username, time, tweet_id)
            VALUES (?, ?, ?)
            """)

    if timestamp is None:
        now = uuid1()
    else:
        now = _timestamp_to_uuid(timestamp)

    # Insert the tweet
    session.execute(tweets_query, (tweet_id, username, tweet,))
    # Insert tweet into the user's timeline
    session.execute(userline_query, (username, now, tweet_id,))
    # Insert tweet into the public timeline
    session.execute(userline_query, (PUBLIC_USERLINE_KEY, now, tweet_id,))

    # Get the user's followers, and insert the tweet into all of their streams
    futures = []
    follower_usernames = [username] + get_follower_usernames(username)
    for follower_username in follower_usernames:
        futures.append(session.execute_async(
            timeline_query, (follower_username, now, tweet_id,)))

    for future in futures:
        future.result()


def add_friends(from_username, to_usernames):
    """
    Adds a friendship relationship from one user to some others.
    """
    global friends_query
    global followers_query

    if friends_query is None:
        friends_query = session.prepare("""
            INSERT INTO friends (username, friend, since)
            VALUES (?, ?, ?)
            """)

    if followers_query is None:
        followers_query = session.prepare("""
            INSERT INTO followers (username, follower, since)
            VALUES (?, ?, ?)
            """)

    now = datetime.utcnow()
    futures = []
    for to_user in to_usernames:
        # Start following user
        futures.append(session.execute_async(
            friends_query, (from_username, to_user, now,)))
        # Add yourself as a follower of the user
        futures.append(session.execute_async(
            followers_query, (to_user, from_username, now,)))

    for future in futures:
        future.result()


def remove_friends(from_username, to_usernames):
    """
    Removes a friendship relationship from one user to some others.
    """
    global remove_friends_query
    global remove_followers_query

    if remove_friends_query is None:
        remove_friends_query = session.prepare("""
            DELETE FROM friends WHERE username=? AND friend=?
            """)
    if remove_followers_query is None:
        remove_followers_query = session.prepare("""
            DELETE FROM followers WHERE username=? AND follower=?
            """)

    futures = []
    for to_user in to_usernames:
        futures.append(session.execute_async(
            remove_friends_query, (from_username, to_user,)))
        futures.append(session.execute_async(
            remove_followers_query, (to_user, from_username,)))

    for future in futures:
        future.result()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    #('Your Name', 'you@gmail.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'dev.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'm9$s12%k&z)v@7)9-mr7d4jn^7cqyxlj6a27!$svzb(43d0#of'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'users.middleware.UserMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
CACHE_BACKEND = 'locmem:///'

INSTALLED_APPS = (
    'django.contrib.sessions',
    'tweets',
    'users',
)

########NEW FILE########
__FILENAME__ = forms
from django import forms

class TweetForm(forms.Form):
    body = forms.CharField(max_length=140)
########NEW FILE########
__FILENAME__ = fake_data
import datetime
import loremipsum
import random
import string
import time
import uuid

import cass

from django.core.management.base import BaseCommand

class Command(BaseCommand):

    def handle(self, *args, **options):
        # Oldest account is 10 years
        origin = int(
            time.time() +
            datetime.timedelta(days=365.25 * 10).total_seconds() * 1e6)
        now = int(time.time() * 1e6)

        num_users = int(args[0])
        max_tweets = int(args[1])

        # Generate number of tweets based on a Zipfian distribution
        sample = [random.paretovariate(15) - 1 for x in range(max_tweets)]
        normalizer = 1 / float(max(sample)) * max_tweets
        num_tweets = [int(x * normalizer) for x in sample]

        for i in range(num_users):
            username = self.get_random_string()
            cass.save_user(username, self.get_random_string())
            creation_date = random.randint(origin, now)

            for _ in range(num_tweets[i % max_tweets]):
                cass.save_tweet(uuid.uuid1(), username, self.get_tweet(), timestamp=random.randint(creation_date, now))

            print "created user"

    def get_tweet(self):
        return loremipsum.get_sentence()

    def get_random_string(self):
        return ''.join(random.sample(string.letters, 10))

########NEW FILE########
__FILENAME__ = sync_cassandra
from cassandra.cluster import Cluster
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        cluster = Cluster(['127.0.0.1'])
        session = cluster.connect()

        rows = session.execute(
            "SELECT * FROM system.schema_keyspaces WHERE keyspace_name='twissandra'")

        if rows:
            msg = ' It looks like you already have a twissandra keyspace.\nDo you '
            msg += 'want to delete it and recreate it? All current data will '
            msg += 'be deleted! (y/n): '
            resp = raw_input(msg)
            if not resp or resp[0] != 'y':
                print "Ok, then we're done here."
                return
            session.execute("DROP KEYSPACE twissandra")

        session.execute("""
            CREATE KEYSPACE twissandra
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
            """)

        # create tables
        session.set_keyspace("twissandra")

        session.execute("""
            CREATE TABLE users (
                username text PRIMARY KEY,
                password text
            )
            """)

        session.execute("""
            CREATE TABLE friends (
                username text,
                friend text,
                since timestamp,
                PRIMARY KEY (username, friend)
            )
            """)

        session.execute("""
            CREATE TABLE followers (
                username text,
                follower text,
                since timestamp,
                PRIMARY KEY (username, follower)
            )
            """)

        session.execute("""
            CREATE TABLE tweets (
                tweet_id uuid PRIMARY KEY,
                username text,
                body text
            )
            """)

        session.execute("""
            CREATE TABLE userline (
                username text,
                time timeuuid,
                tweet_id uuid,
                PRIMARY KEY (username, time)
            ) WITH CLUSTERING ORDER BY (time DESC)
            """)

        session.execute("""
            CREATE TABLE timeline (
                username text,
                time timeuuid,
                tweet_id uuid,
                PRIMARY KEY (username, time)
            ) WITH CLUSTERING ORDER BY (time DESC)
            """)

        print 'All done!'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('tweets.views',
    url(r'^/?$', 'timeline', name='timeline'),
    url(r'^public/$', 'publicline', name='publicline'),
    url(r'^(?P<username>\w+)/$', 'userline', name='userline'),
)
########NEW FILE########
__FILENAME__ = views
import uuid

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse

from tweets.forms import TweetForm

import cass

NUM_PER_PAGE = 40

def timeline(request):
    form = TweetForm(request.POST or None)
    if request.user['is_authenticated'] and form.is_valid():
        tweet_id = uuid.uuid4()
        cass.save_tweet(tweet_id, request.session['username'], form.cleaned_data['body'])
        return HttpResponseRedirect(reverse('timeline'))
    start = request.GET.get('start')
    if request.user['is_authenticated']:
        tweets, next_timeuuid = cass.get_timeline(
            request.session['username'], start=start, limit=NUM_PER_PAGE)
    else:
        tweets, next_timeuuid = cass.get_userline(
            cass.PUBLIC_USERLINE_KEY, start=start, limit=NUM_PER_PAGE)
    context = {
        'form': form,
        'tweets': tweets,
        'next': next_timeuuid,
    }
    return render_to_response(
        'tweets/timeline.html', context, context_instance=RequestContext(request))


def publicline(request):
    start = request.GET.get('start')
    tweets, next_timeuuid = cass.get_userline(
        cass.PUBLIC_USERLINE_KEY, start=start, limit=NUM_PER_PAGE)
    context = {
        'tweets': tweets,
        'next': next_timeuuid,
    }
    return render_to_response(
        'tweets/publicline.html', context, context_instance=RequestContext(request))


def userline(request, username=None):
    try:
        user = cass.get_user_by_username(username)
    except cass.DatabaseError:
        raise Http404

    # Query for the friend ids
    friend_usernames = []
    if request.user['is_authenticated']:
        friend_usernames = cass.get_friend_usernames(username) + [username]

    # Add a property on the user to indicate whether the currently logged-in
    # user is friends with the user
    is_friend = username in friend_usernames

    start = request.GET.get('start')
    tweets, next_timeuuid = cass.get_userline(username, start=start, limit=NUM_PER_PAGE)
    context = {
        'user': user,
        'username': username,
        'tweets': tweets,
        'next': next_timeuuid,
        'is_friend': is_friend,
        'friend_usernames': friend_usernames,
    }
    return render_to_response(
        'tweets/userline.html', context, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
    url('^auth/', include('users.urls')),
    url('', include('tweets.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        (r'^media/(?P<path>.*)$', 'serve',
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )

########NEW FILE########
__FILENAME__ = forms
from django import forms

import cass

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password = forms.CharField(widget=forms.PasswordInput(render_value=False))

    def clean(self):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        try:
            user = cass.get_user_by_username(username)
        except cass.DatabaseError:
            raise forms.ValidationError(u'Invalid username and/or password')
        if user.password != password:
            raise forms.ValidationError(u'Invalid username and/or password')
        return self.cleaned_data

    def get_username(self):
        return self.cleaned_data['username']


class RegistrationForm(forms.Form):
    username = forms.RegexField(regex=r'^\w+$', max_length=30)
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False))

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            cass.get_user_by_username(username)
            raise forms.ValidationError(u'Username is already taken')
        except cass.DatabaseError:
            pass
        return username

    def clean(self):
        if ('password1' in self.cleaned_data and 'password2' in self.cleaned_data):
            password1 = self.cleaned_data['password1']
            password2 = self.cleaned_data['password2']
            if password1 != password2:
                raise forms.ValidationError(
                    u'You must type the same password each time')
        return self.cleaned_data

    def save(self):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password1']
        cass.save_user(username, password)
        return username

########NEW FILE########
__FILENAME__ = middleware
import cass

def get_user(request):
    if 'username' in request.session:
        try:
            user = cass.get_user_by_username(request.session['username'])
            return {
                'username': user.username,
                'password': user.password,
                'is_authenticated': True
            }
        except cass.DatabaseError:
            pass
    return {
        'password': None,
        'is_authenticated': False,
    }

class LazyUser(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_user'):
            request._cached_user = get_user(request)
        return request._cached_user

class UserMiddleware(object):
    def process_request(self, request):
        request.__class__.user = LazyUser()

########NEW FILE########
__FILENAME__ = models
# Nope, we're using Cassandra :)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('users.views',
    url('^login/$', 'login', name='login'),
    url('^logout/$', 'logout', name='logout'),
    url(r'^find-friends/$', 'find_friends', name='find_friends'),
    url(r'^modify-friend/$', 'modify_friend', name='modify_friend'),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from users.forms import LoginForm, RegistrationForm

import cass

def login(request):
    login_form = LoginForm()
    register_form = RegistrationForm()
    next = request.REQUEST.get('next')
    if 'kind' in request.POST:
        if request.POST['kind'] == 'login':
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.get_username()
                request.session['username'] = username
                if next:
                    return HttpResponseRedirect(next)
                return HttpResponseRedirect('/')
        elif request.POST['kind'] == 'register':
            register_form = RegistrationForm(request.POST)
            if register_form.is_valid():
                username = register_form.save()
                request.session['username'] = username
                if next:
                    return HttpResponseRedirect(next)
                return HttpResponseRedirect('/')
    context = {
        'login_form': login_form,
        'register_form': register_form,
        'next': next,
    }
    return render_to_response(
        'users/login.html', context, context_instance=RequestContext(request))

def logout(request):
    request.session.pop('username', None)
    return render_to_response(
        'users/logout.html', {}, context_instance=RequestContext(request))

def find_friends(request):
    friend_usernames = []
    if request.user['is_authenticated']:
        friend_usernames = cass.get_friend_usernames(
            request.session['username']) + [request.session['username']]
    q = request.GET.get('q')
    result = None
    searched = False
    if q is not None:
        searched = True
        try:
            result = cass.get_user_by_username(q)
            result = {
                'username': result.username,
                'friend': q in friend_usernames
            }
        except cass.DatabaseError:
            pass
    context = {
        'q': q,
        'result': result,
        'searched': searched,
        'friend_usernames': friend_usernames,
    }
    return render_to_response(
        'users/add_friends.html', context, context_instance=RequestContext(request))

def modify_friend(request):
    next = request.REQUEST.get('next')
    added = False
    removed = False
    if request.user['is_authenticated']:
        if 'add-friend' in request.POST:
            cass.add_friends(
                request.session['username'],
                [request.POST['add-friend']]
            )
            added = True
        if 'remove-friend' in request.POST:
            cass.remove_friends(
                request.session['username'],
                [request.POST['remove-friend']]
            )
            removed = True
    if next:
        return HttpResponseRedirect(next)
    context = {
        'added': added,
        'removed': removed,
    }
    return render_to_response(
        'users/modify_friend.html', context, context_instance=RequestContext(request))

########NEW FILE########
