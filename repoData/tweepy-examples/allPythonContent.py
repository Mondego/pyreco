__FILENAME__ = app
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import sys
sys.path.insert(0, 'tweepy.zip')

import oauth_example.handlers

# Construct the WSGI application
application = webapp.WSGIApplication([

        # OAuth example
        (r'/oauth/', oauth_example.handlers.MainPage),
        (r'/oauth/callback', oauth_example.handlers.CallbackPage),
        (r'/.*$', oauth_example.handlers.MainPage),

], debug=True)

def main():
    run_wsgi_app(application)

# Run the WSGI application
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = handlers
import pickle
from google.appengine.ext.webapp import RequestHandler, template
from google.appengine.ext import db
import tweepy

from oauth_example.models import OAuthToken

CONSUMER_KEY = 'e9n31I0z64dagq3WbErGvA'
CONSUMER_SECRET = '9hwCupdAKV8EixeNdN3xrxL9RG3X3JTXI0Q520Oyolo'
CALLBACK = 'http://localhost:8080/oauth/callback'

# Main page handler  (/oauth/)
class MainPage(RequestHandler):

    def get(self):
        # Build a new oauth handler and display authorization url to user.
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK)
        try:
            print template.render('oauth_example/main.html', {
                    "authurl": auth.get_authorization_url(),
                    "request_token": auth.request_token
            })
        except tweepy.TweepError, e:
            # Failed to get a request token
            print template.render('error.html', {'message': e})
            return

        # We must store the request token for later use in the callback page.
        request_token = OAuthToken(
                token_key = auth.request_token.key,
                token_secret = auth.request_token.secret
        )
        request_token.put()

# Callback page (/oauth/callback)
class CallbackPage(RequestHandler):

    def get(self):
        oauth_token = self.request.get("oauth_token", None)
        oauth_verifier = self.request.get("oauth_verifier", None)
        if oauth_token is None:
            # Invalid request!
            print template.render('error.html', {
                    'message': 'Missing required parameters!'
            })
            return

        # Lookup the request token
        request_token = OAuthToken.gql("WHERE token_key=:key", key=oauth_token).get()
        if request_token is None:
            # We do not seem to have this request token, show an error.
            print template.render('error.html', {'message': 'Invalid token!'})
            return

        # Rebuild the auth handler
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_request_token(request_token.token_key, request_token.token_secret)

        # Fetch the access token
        try:
            auth.get_access_token(oauth_verifier)
        except tweepy.TweepError, e:
            # Failed to get access token
            print template.render('error.html', {'message': e})
            return

        # So now we could use this auth handler.
        # Here we will just display the access token key&secret
        print template.render('oauth_example/callback.html', {
            'access_token': auth.access_token
        })


########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db

class OAuthToken(db.Model):
    token_key = db.StringProperty(required=True)
    token_secret = db.StringProperty(required=True)


########NEW FILE########
__FILENAME__ = getaccesstoken
import webbrowser

import tweepy

"""
    Query the user for their consumer key/secret
    then attempt to fetch a valid access token.
"""

if __name__ == "__main__":

    consumer_key = raw_input('Consumer key: ').strip()
    consumer_secret = raw_input('Consumer secret: ').strip()
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)

    # Open authorization URL in browser
    webbrowser.open(auth.get_authorization_url())

    # Ask user for verifier pin
    pin = raw_input('Verification pin number from twitter.com: ').strip()

    # Get access token
    token = auth.get_access_token(verifier=pin)

    # Give user the access token
    print 'Access token:'
    print '  Key: %s' % token.key
    print '  Secret: %s' % token.secret


########NEW FILE########
__FILENAME__ = repeater
#!/usr/bin/env python

"""
twitter-repeater is a bot that automatically retweets any tweets in which its name
is "mentioned" in. In order for a tweet to be retweeted, the bot account must be
following the original user who tweeted it, that user must not be on the ignore
list, and the tweet must pass some basic quality tests.

The idea was originally inspired by the @SanMo bot and was created so I could use
something similar for New London, CT (@NLCT)

It runs well on Linux but it should run just as well on Mac OSX or Windows.

I use the following user Cron job to run the bot every 5 minutes:

*/5     *       *       *       *       $HOME/twitter-repeater/repeater.py
"""

# Project: twitter-repeater
# Author: Charles Hooper <chooper@plumata.com>
#
# Copyright (c) 2010, Charles Hooper
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice, this
# list of conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.
#
# * Neither the name of Plumata LLC nor the names of its contributors may be
# used to endorse or promote products derived from this software without specific prior
# written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT
# SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

# imports
from sys import exit
import tweepy
import settings

# import exceptions
from urllib2 import HTTPError

# globals - The following is populated later by load_lists
IGNORE_LIST = []
FILTER_WORDS = []

def debug_print(text):
    """Print text if debugging mode is on"""
    if settings.debug:
        print text


def save_id(statefile,id):
    """Save last status ID to a file"""
    last_id = get_last_id(statefile)

    if last_id < id:
        debug_print('Saving new ID %d to %s' % (id,statefile))
        f = open(statefile,'w')
        f.write(str(id)) # no trailing newline
        f.close()
    else:
        debug_print('Received smaller ID, not saving. Old: %d, New: %s' % (
            last_id, id))


def get_last_id(statefile):
    """Retrieve last status ID from a file"""

    debug_print('Getting last ID from %s' % (statefile,))
    try:
        f = open(statefile,'r')
        id = int(f.read())
        f.close()
    except IOError:
        debug_print('IOError raised, returning zero (0)')
        return 0
    debug_print('Got %d' % (id,))
    return id


def load_lists(force=False):
    """Load ignore and filtered word lists"""
    debug_print('Loading ignore list')
    if not IGNORE_LIST or force is True:
        global IGNORE_LIST
        IGNORE_LIST = [
            line.lower().strip() for line in open(settings.ignore_list) ]

    debug_print('Loading filtered word list')
    if not FILTER_WORDS or force is True:
        global FILTER_WORDS
        FILTER_WORDS = [
            line.lower().strip() for line in open(settings.filtered_word_list) ]


def careful_retweet(api,reply):
    """Perform retweets while avoiding loops and spam"""

    load_lists()

    debug_print('Preparing to retweet #%d' % (reply.id,))
    normalized_tweet = reply.text.lower().strip()

    # Don't try to retweet our own tweets
    if reply.user.screen_name.lower() == settings.username.lower():
        return

    # Don't retweet if the tweet is from an ignored user
    if reply.user.screen_name.lower() in IGNORE_LIST:
        return

    # Don't retweet if the tweet contains a filtered word
    for word in normalized_tweet.split():
        if word.lower().strip() in FILTER_WORDS:
            return

    # HACK: Don't retweet if tweet contains more usernames than words (roughly)
    username_count = normalized_tweet.count('@')
    if username_count >= len(normalized_tweet.split()) - username_count:
        return

    # Try to break retweet loops by counting the occurences tweeting user's name
    if normalized_tweet.split().count('@'+ reply.user.screen_name.lower()) > 0:
        return

    debug_print('Retweeting #%d' % (reply.id,))
    return api.retweet(id=reply.id)


def main():
    auth = tweepy.BasicAuthHandler(username=settings.username,
        password=settings.password)
    api = tweepy.API(auth_handler=auth, secure=True, retry_count=3)

    last_id = get_last_id(settings.lastid)

    debug_print('Loading friends list')
    friends = api.friends_ids()
    debug_print('Friend list loaded, size: %d' % len(friends))

    try:
        debug_print('Retrieving mentions')
        replies = api.mentions()
    except Exception, e:    # quit on error here
        print e
        exit(1)

    # want these in ascending order, api orders them descending
    replies.reverse()

    for reply in replies:
        # ignore tweet if it's id is lower than our last tweeted id
        if reply.id > last_id and reply.user.id in friends:
            try:
                careful_retweet(api,reply)
            except HTTPError, e:
                print e.code()
                print e.read()
            except Exception, e:
                print 'e: %s' % e
                print repr(e)
            else:
                save_id(settings.lastid,reply.id)

    debug_print('Exiting cleanly')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        quit()


########NEW FILE########
__FILENAME__ = streamwatcher
#!/usr/bin/env python

import time
from getpass import getpass
from textwrap import TextWrapper

import tweepy


class StreamWatcherListener(tweepy.StreamListener):

    status_wrapper = TextWrapper(width=60, initial_indent='    ', subsequent_indent='    ')

    def on_status(self, status):
        try:
            print self.status_wrapper.fill(status.text)
            print '\n %s  %s  via %s\n' % (status.author.screen_name, status.created_at, status.source)
        except:
            # Catch any unicode errors while printing to console
            # and just ignore them to avoid breaking application.
            pass

    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True  # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'


def main():
    # Prompt for login credentials and setup stream object
    consumer_key = raw_input('Consumer Key: ')
    consumer_secret = getpass('Consumer Secret: ')
    access_token = raw_input('Access Token: ')
    access_token_secret = getpass('Access Token Secret: ')

    auth = tweepy.auth.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    stream = tweepy.Stream(auth, StreamWatcherListener(), timeout=None)

    # Prompt for mode of streaming
    valid_modes = ['sample', 'filter']
    while True:
        mode = raw_input('Mode? [sample/filter] ')
        if mode in valid_modes:
            break
        print 'Invalid mode! Try again.'

    if mode == 'sample':
        stream.sample()

    elif mode == 'filter':
        follow_list = raw_input('Users to follow (comma separated): ').strip()
        track_list = raw_input('Keywords to track (comma seperated): ').strip()
        if follow_list:
            follow_list = [u for u in follow_list.split(',')]
            userid_list = []
            username_list = []
            
            for user in follow_list:
                if user.isdigit():
                    userid_list.append(user)
                else:
                    username_list.append(user)
            
            for username in username_list:
                user = tweepy.API().get_user(username)
                userid_list.append(user.id)
            
            follow_list = userid_list
        else:
            follow_list = None
        if track_list:
            track_list = [k for k in track_list.split(',')]
        else:
            track_list = None
        print follow_list
        stream.filter(follow_list, track_list)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\nGoodbye!'


########NEW FILE########
