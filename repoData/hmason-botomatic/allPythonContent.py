__FILENAME__ = botomatic
import sys
import os
import pickle
import tweepy #requires version 2.1+
import urllib
import urllib2
import json
import re

import settings

def bitlify(match):
    if settings.BITLY_LOGIN and settings.BITLY_APIKEY:
        response = urllib2.urlopen("http://api.bitly.com/v3/shorten?" + urllib.urlencode({'longUrl': match.group(0), 'apiKey': settings.BITLY_APIKEY, 'login': settings.BITLY_LOGIN}))
        data = response.read()
        try:
            url = json.loads(data)['data']['url']
        except ValueError:
            url = match.group(0)

        return url


class TBot(object):
    handle = None
    debug_mode = True
    bitlify_links = True
    settings = {}
    tweets = []
    follow_handles = []
    dms = []

    def __init__(self, handle):
        self.history_filename = handle + "_history.pickle"
        self.auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET, secret=True)
        try:
            self.settings = pickle.load(open(handle + "_settings.pickle",'r'))
        except IOError:
            self.authenticate()
            pickle.dump(self.settings, open(handle + "_settings.pickle",'w')) # right place to save settings?

        try:
            self.history = pickle.load(open(self.history_filename,'r'))
        except IOError:
            self.history = {}

        self.auth.set_access_token(self.settings['key'], self.settings['secret'])
        self.api = tweepy.API(self.auth)

        self.run()

    def handle_DMs(self, new_only=True):
        if new_only and self.history.get('last_dm_id', None):
            dms = self.api.direct_messages(since_id=self.history['last_dm_id'])
        else:
            dms = self.api.direct_messages()

        if dms:
            self.history['last_dm_id'] = dms[0].id

        return dms

    def handle_mentions(self, new_only=True):
        if new_only and self.history.get('last_mention_id', None):
            mentions = self.api.mentions_timeline(since_id=self.history['last_mention_id'])
        else:
            mentions = self.api.mentions_timeline()
        
        if mentions:
            self.history['last_mention_id'] = mentions[0].id

        return mentions

    def search(self, query, lang='en'):
        return self.api.search(q=query, lang=lang)

    def handle_stream(self):
        return self.api.home_timeline()

    def handle_followers(self): # TODO
        pass

    def process_tweets(self):
        http_re = re.compile(r'http://\S+')
        processed_tweets = []
        for tweet in self.tweets:
            if 'http://' in tweet:
                tweet = http_re.sub(bitlify, tweet)
            processed_tweets.append(tweet)
        self.tweets = processed_tweets
                

    def publish_tweets(self, limit=None):
        tweeted_count = 0

        if self.tweets:
            for twt in self.tweets:
                try:
                    (tweet, reply_id) = twt
                except ValueError:
                    tweet = twt
                    reply_id = None

                if self.debug_mode:
                    print "FAKETWEET: " + tweet[:140] # for debug mode
                else:
                    try:
                        if limit:
                            if tweeted_count >= limit:
                                continue
                        else:
                            status = self.api.update_status(tweet[:140], reply_id) # cap length at 140 chars
                            self.history['last_tweet_id'] = status.id
                            tweeted_count += 1
                    except tweepy.error.TweepError: # prob a duplicate
                        pass

    def publish_dms(self):
        if self.dms:
            for (handle, msg) in self.dms:
                user = self.api.get_user(screen_name=handle)
                self.api.send_direct_message(screen_name=handle, text=msg)

    def authenticate(self):
        print self.auth.get_authorization_url()
        verifier = raw_input('Verification code: ')
        try:
            self.auth.get_access_token(verifier)
        except tweepy.TweepError:
            print 'Error: failed to get access token.'

        self.settings['key'] = self.auth.access_token.key
        self.settings['secret'] = self.auth.access_token.secret

    def follow_users(self):
        for handle in self.follow_handles:
            try:
                user = self.api.get_user(screen_name=handle)
                user.follow()
            except tweepy.error.TweepError: # no such user?
                continue


    def run(self):
        pass

    def wrap_up(self, tweet_limit=None):
        self.process_tweets()
        self.follow_users()
        self.publish_tweets(tweet_limit)
        self.publish_dms()
        pickle.dump(self.history, open(self.history_filename, 'w'))


if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = bc_l
from botomatic import TBot
import subprocess

class bc_l(TBot):
    def __init__(self):
        handle = "bc_l"
        super(bc_l, self).__init__(handle)

    def bc_l(self, input_text):
        p = subprocess.Popen("bc -l", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            out, err = p.communicate(input_text + "\n")
        except UnicodeEncodeError:
            return ''

        return out


    def run(self):
        for dm in self.handle_DMs():
            out = self.bc_l(dm.text)
            if out.strip():
                reply = "@%s %s = %s" % (dm.sender_screen_name, dm.text, out.strip())
                self.tweets.append(reply)

        for msg in self.handle_mentions():
            expression = msg.text[5:] # assuming the @bc_l is a prefix
            out = self.bc_l(expression)
            if out.strip():
                reply = "@%s %s = %s" % (msg.user.screen_name, expression, out.strip())
                self.tweets.append(reply)


        self.wrap_up()

if __name__ == '__main__':
    b = bc_l()

########NEW FILE########
__FILENAME__ = bookbookgoose
import csv
import random
from botomatic import TBot

data_file = "kindle.csv"

class BookBookGooseBot(TBot):
    debug_mode = False

    def __init__(self):
        handle = "bookbookgoose"
        super(BookBookGooseBot, self).__init__(handle)

    def run(self):
        r = csv.reader(open(data_file))
        books = [row for row in r]
        random.shuffle(books)
        book = books.pop()

        book_text = book[1] + ', by ' + book[0]

        self.tweets.append(book_text[0:117] + ' ' + book[2])

        self.wrap_up()

if __name__ == '__main__':
    b = BookBookGooseBot()

########NEW FILE########
__FILENAME__ = magic8ball
import random

from botomatic import TBot

RESPONSES = ['It is certain', 'It is decidedly so', 'Without a doubt', 'Yes definitely', 'You may rely on it', 'As I see it yes',
             'Most likely', 'Outlook good', 'Yes', 'Signs point to yes', 'Reply hazy try again', 'Ask again later', 
             'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again', 'Don\'t count on it', 'My reply is no', 
             'My sources say no', 'Outlook not so good', 'Very doubtful']

class Magic8Ball(TBot):
    debug_mode = False

    def __init__(self):
        handle = "dodecaDecider"
        super(Magic8Ball, self).__init__(handle)

    def run(self):
        for msg in self.handle_mentions():
            reply = "@%s %s" % (msg.user.screen_name, random.choice(RESPONSES))
            self.tweets.append((reply, msg.id))

        self.wrap_up()

if __name__ == '__main__':
    m = Magic8Ball()


########NEW FILE########
__FILENAME__ = protip
import pickle
import tweepy
from botomatic import TBot

class Protip(TBot):
    debug_mode = True

    def __init__(self):
        handle = "protipbot"
        super(Protip, self).__init__(handle)

    def run(self):
        results = self.search('"pro-tip" protip')
        for result in results:
            try:
                result.retweet()
            except tweepy.error.TweepError: # private status update?
                continue


        self.wrap_up()

if __name__ == '__main__':
    p = Protip()

########NEW FILE########
