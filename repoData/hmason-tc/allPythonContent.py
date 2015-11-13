__FILENAME__ = classify_tweets
from __future__ import division
import sys, os, random
import nltk, re
from nltk.tokenize import *
import pickle

active_classifiers = ['betaworks', 'narcissism', 'sports', 'checkin']

class tweetClassifier(object):
    def __init__(self):
        pass

    def load_data(self, categories):
        """
        load_data: load a document line by line
        """
        data = []
        for category in categories:
            f = open('classifiers/data/%s' % category, 'r')
            for line in f.readlines():
                data.append((line, category))
        return data # returns a list of tuples of the form (line of text, category)
        
    def document_features(self, document):
        """
        document_features: this breaks a text document into the comparison set of features
        """
        document_words = set(word_tokenize(document)) # break the text down into a set (for speed) of individual words
        features = {}
        for word in self.word_features:
            features['contains(%s)' % word] = (word in document_words) # feature format follows canonical example
        return features

    def print_classification(self, classifier, line):
        """
        print_classification: Given a trained classifer and a line of text, it prints the probability that the text falls into each category
        """
        print "Content: %s" % line
        line_prob = classifier.prob_classify(self.document_features(line)) # get the probability for each category
        for cat in line_prob.samples():
            print "prob. %s = %s" % (cat, line_prob.prob(cat))
        
        

class sports(tweetClassifier):
    SAMPLE_SIZE = 500
    CLASSIFIER_DUMP = 'classifiers/trained/sports'
    
    def __init__(self, debug=False):
        self.debug = debug
        
        try:
            (self.classifier, self.word_features) = pickle.load(open(self.CLASSIFIER_DUMP, 'r'))
        except IOError:
            data = self.load_data(['sports', 'new_york'])
            self.train_classifier(data)
            pickle.dump((self.classifier, self.word_features), open(self.CLASSIFIER_DUMP, 'w'))
                    
        
    def train_classifier(self, data):
        data = random.sample(data, self.SAMPLE_SIZE)

        all_words = [] # build a freq distribution of all words used in all documents in the dataset
        for line,cat in data:
            all_words.extend(word_tokenize(line))
        all_words = [word for word in all_words if len(word) > 2] # filter out very short words
        all_words_freq = nltk.FreqDist(w.lower() for w in all_words) # frequency distribution is a dist of the form word: count_of_how_often_word_appears
        self.word_features = all_words_freq.keys()[:1000] # use the 2k most freq words as our set of features

        featuresets = [(self.document_features(d), c) for (d,c) in data] # divide data into testing and training sets
        train_set, test_set = featuresets[200:], featuresets[:200]

        self.classifier = nltk.NaiveBayesClassifier.train(train_set) # invoke the naive bayesian classifier

        if self.debug:
            print "training new sports classifier"
            print "Accuracy of the classifier: %s" % nltk.classify.accuracy(self.classifier, test_set) # print the accuracy of the classifier

        # classifier.show_most_informative_features(100) # show the features that have high relevance
    
        
    def classify(self, tweet):
        line_prob = self.classifier.prob_classify(self.document_features(tweet)) # get the probability for each category
        return ('sports', line_prob.prob('sports'))

        
class narcissism(tweetClassifier):
    N_THRESHOLD = 5.0
    
    def __init__(self):
        self.keywords = ['my latest', 'out my', 'my new', 'i am', 'i hate', 'i love', 'i like', "i can't", 'new post', 'did i', 'i shall', 'i really', 'i wish', 'mine', "i'll", 'i do', "i don't", "i won't", "for my", "i did", "i have", "i had", 'fml']
        
    def classify(self, tweet):
        count = 0
        for word in self.keywords:
            if word in tweet.lower():
                count += 1
                
        score = min((float(count) / self.N_THRESHOLD), 1.0) # max score = 1.0
        return ('narcissism', score)
        
class betaworks(tweetClassifier):
    def __init__(self):
        self.keywords = ['tweetdeck', 'chartbeat', 'socialflow', '@bitly', 'venmo', 'tumblr', 'superfeedr', 'backupify', 'fluiddb', 'twitterfeed']
        
    def classify(self, tweet):
        score = 0.0
        for word in self.keywords:
            if word in tweet.lower():
                score = 1.0
                
        return ('betaworks', score)

class checkin(tweetClassifier):
    def __init__(self):
        self.keywords = ['4sq.com']

    def classify(self, tweet):
        score = 0.0
        for word in self.keywords:
            if word in tweet.lower():
                score = 1.0

        return ('checkin', score)

        
if __name__ == '__main__':
    # n = narcissism()
    # print n.classify("I like marshamllowdkjfdk my mine my new i hate i am")
    s = sports(debug=True)
    print s.classify("#Dolphins WR Brandon Marshall says he plans to pursue NBA career if NFL teams lock out their players.")
    print s.classify("Open mapping potentials for humanitarian response by @rrbaker #isb2")
########NEW FILE########
__FILENAME__ = fetch_data
import sys, os
import tweepy
from optparse import OptionParser

sys.path.append('..')
import settings


if __name__ == '__main__':
    parser = OptionParser("usage: %prog [options]") # no args this time
    # parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False, help="set debug mode = True")
    parser.add_option("-q", "--query", dest="query", action="store", help="query")
    (options, args) = parser.parse_args()
    
    auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
    auth.set_access_token(settings.ACCESS_KEY, settings.ACCESS_SECRET)
    api = tweepy.API(auth)
    
    for t in api.search(options.query, lang='en', rpp=100):
        try:
            print "%s %s" % (t.from_user, t.text)
        except UnicodeEncodeError:
            pass
########NEW FILE########
__FILENAME__ = run_classification
import sys, os
import pymongo

sys.path.append('..')
from lib import mongodb
from classify_tweets import *

DB_NAME = 'tweets'

if __name__ == '__main__':
    classifiers = []
    for active_classifier in active_classifiers:
        c = globals()[active_classifier]()
        classifiers.append(c)


    db =  mongodb.connect(DB_NAME)
    for r in db[DB_NAME].find(spec={'topics': {'$exists': False } },fields={'text': True, 'user': True}): # for all unclassified tweets
        print r
        topics = {}
        for c in classifiers:
            (topic, score) = c.classify(r['text'])
            topics[topic] = score
        
        print topics
        db[DB_NAME].update({'_id': r['_id']}, {'$set': {'topics': topics }})
########NEW FILE########
__FILENAME__ = display
import sys, os

sys.path.append('..')
import settings

import htmlentitydefs
import re
import string

class Display(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    ITAL_ON = '\033[3m'
    ITAL_OFF = '\033[23m'
    BOLD_ON = '\033[1m'
    BOLD_OFF = '\033[22m'
    
    MAX_TWITTER_USERNAME_LENGTH = 15
    
    def html_decode(self, text):
	for entity, repl in htmlentitydefs.entitydefs.iteritems():
		if repl in string.printable:
			text = re.sub('&%s;' % entity, repl, text)
	return text

    def display_tweets(self, tweets):

        for t in tweets:
            if t['_display']:
		text = self.html_decode(t['text'])
                spacer = ' '.join(['' for i in range((self.MAX_TWITTER_USERNAME_LENGTH + 2) - len(t['user']))])
                if settings.TWITTER_USERNAME in text: # highlight replies   
                    text = self.BOLD_ON + text + self.BOLD_OFF
                tweet_text = self.OKGREEN + t['user'] + self.ENDC + spacer + text
                if t.get('_display_topics', None): # print with topics
                    print tweet_text + '  ' + self.OKBLUE + ' '.join(t['_display_topics']) + self.ENDC
                elif t.get('_datetime', None): # print with date/time
                    print tweet_text + '  ' + self.OKBLUE + t['_datetime'] + self.ENDC
                else: # print without topics
                    print tweet_text

    def display_users(self, users):

        for t in users:
            if t['_display']:
                spacer = ' '.join(['' for i in range((self.MAX_TWITTER_USERNAME_LENGTH + 2) - len(t['_id']))])
                tweet_text = self.OKGREEN + t['_id'] + self.ENDC + spacer + t['name'] + '  ' + t['location'] + '  ' + t['description']
                if t.get('url', None): # print with url
                    print tweet_text + '  ' + self.OKBLUE + t['url'] + self.ENDC
                else: # print without topics
                    print tweet_text
    

########NEW FILE########
__FILENAME__ = klout
# From: http://code.google.com/p/python-klout/

from datetime import date, timedelta

import time
import urllib
import urllib2

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except:
            raise 'Requires either Python 2.6 or above, simplejson or django.utils!'

RETRY_COUNT = 5
API_BASE_URL = 'http://api.klout.com/1/'

#
# NOTE: some verbs are disabled as they are still under development
# and currently don't work with the API
# 
VERB_PARAMS = {
    'klout': [
        'users'
    ],
    'soi.influenced_by': [
        'users'
    ],
    'soi.influencer_of': [
        'users'
    ],
    # 'topics.search': [
    #     'topic'
    # ],
    # 'topics.verify': [
    #     'topic'
    # ],
    # 'users.history': [
    #     'end_date',
    #     'start_date',
    #     'users'
    # ],
    'users.show': [
        'users'
    ],
    # 'users.stats': [
    #     'users'
    # ],
    'users.topics': [
        'users'
    ],
}


class KloutError( Exception ):
    """
    Base class for Klout API errors.
    """
    @property
    def message( self ):
        """
        Return the first argument passed to this class as the message.
        """
        return self.args[ 0 ]
    
    
class KloutAPI( object ):
    def __init__( self, api_key ):
        self.api_key = api_key
        self._urllib = urllib2
        
    def call( self, verb, **kwargs ):
        # build request
        request = self._buildRequest( verb, **kwargs )

        # fetch data
        result = self._fetchData( request )

        # return result
        return result
    
    def _buildRequest( self, verb, **kwargs ):
        # add API key to all requests
        params = [
            ( 'key', self.api_key ),
        ]

        # check params based on the given verb and build params
        for k, v in kwargs.iteritems():
            if k in VERB_PARAMS[ verb ]:
                params.append( ( k , v ) )
            else:
                raise KloutError(
                        "Invalid API parameter %s for verb %s" % ( k, verb ) )

        # encode params
        encoded_params = urllib.urlencode( params )
        
        # URL to API endpoint
        url = '%s/%s.json?%s' % ( API_BASE_URL, verb.replace( '.', '/' ), 
            encoded_params )
        
        # build request and return it
        request = urllib2.Request( url )
        return request
    
    def _fetchData( self, request ):
        counter = 0
        while True:
            try:
                if counter > 0:
                    time.sleep( counter * 0.5 )
                url_data = self._urllib.urlopen( request ).read()
                json_data = json.loads( url_data )
            except urllib2.HTTPError, e:
                if e.code == 400:
                    raise KloutError(
                        "Klout sent status %i:\ndetails: %s" % (
                            e.code, e.fp.read() ) )
                counter += 1
                if counter > RETRY_COUNT:
                    raise KloutError(
                        "Klout sent status %i:\ndetails: %s" % (
                            e.code, e.fp.read() ) )
            except ValueError:
                counter += 1
                if counter > RETRY_COUNT:
                    raise KloutError(
                        "Klout did not return valid JSON data" )
            else:
                return json_data


if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter( indent = 4 )
    
    verb_list = VERB_PARAMS.keys()
    verb_list.sort()

    users = 'biz,mashable'
    topic = 'iPhone'
    start_date = date.today() - timedelta( days = 6 )
    end_date = date.today()
    
    a = KloutAPI( api_key = 'v4rexwayms7kumxgqgh57nhx' )
    
    for verb in verb_list:
        print 'Testing verb: %s' % ( verb )
        if verb in [ 'topics.search', 'topics.verify' ]:
            kwargs = { 'topic': topic }
        else:
            kwargs = { 'users': users }
        x = a.call( verb, **kwargs )
        pp.pprint( x )
########NEW FILE########
__FILENAME__ = mongodb
import logging
from pymongo import *

def connect(dbname, port=27017):
    logging.debug("connecting to magicbus mongodb")
    conn = connection.Connection('localhost', port)
    db = database.Database(conn, dbname)
    return db
########NEW FILE########
__FILENAME__ = display_test
import lib.display

class TestDisplay:
	def setup(self):
		self.display = lib.display.Display()

	def test_display_decodes_gt_entity(self):
		assert self.display.html_decode("&gt;") == '>'

	def test_html_decode_doesnt_remove_single_ampersand(self):
		assert self.display.html_decode("&;") == '&;'

	def test_html_decode_doesnt_replace_unprintable_entites(self):
		unprintable_entity = "&Ouml;"
		assert self.display.html_decode(unprintable_entity) == unprintable_entity

########NEW FILE########
__FILENAME__ = load_tweets
#!/usr/bin/env python
# encoding: utf-8
"""
load_tweets.py

Created by Hilary Mason on 2010-04-25.
Copyright (c) 2010 Hilary Mason. All rights reserved.
"""

import sys, os
import datetime
import subprocess
import pickle
import pymongo
import tweepy # Twitter API class: http://github.com/joshthecoder/tweepy
from lib import mongodb
from lib import klout
from classifiers.classify_tweets import *
import settings # local app settings

class loadTweets(object):
    DB_NAME = 'tweets'
    USER_COLL_NAME = 'users'
    
    def __init__(self, debug=False):
        self.debug = debug
        self.db = mongodb.connect(self.DB_NAME)
        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_KEY, settings.ACCESS_SECRET)
        self.api = tweepy.API(auth)

        last_tweet_id = self.get_last_tweet_id()
        try:
            self.fetchTweets(last_tweet_id)
        except tweepy.error.TweepError: # authorization failure
            print "You need to authorize tc to connect to your twitter account. I'm going to open a browser. Once you authorize, I'll ask for your PIN."
            auth = self.setup_auth()
            self.api = tweepy.API(auth)
            self.fetchTweets(last_tweet_id)
        
        self.classify_tweets()


    def get_last_tweet_id(self):
        for r in self.db[self.DB_NAME].find(fields={'id': True}).sort('id',direction=pymongo.DESCENDING).limit(1):
            return r['id']

    def fetchTweets(self, since_id=None):
        if since_id:
            tweets = self.api.home_timeline(since_id, count=500)
        else:
            tweets = self.api.home_timeline(count=500)
        
        # parse each incoming tweet
        ts = []
        authors = []
        for tweet in tweets: 
            t = {
            'author': tweet.author.screen_name,
            'contributors': tweet.contributors,
            'coordinates': tweet.coordinates,
            'created_at': tweet.created_at,
            # 'destroy': tweet.destroy,
            # 'favorite': tweet.favorite,
            'favorited': tweet.favorited,
            'geo': tweet.geo,
            'id': tweet.id,
            'in_reply_to_screen_name': tweet.in_reply_to_screen_name,
            'in_reply_to_status_id': tweet.in_reply_to_status_id,
            'in_reply_to_user_id': tweet.in_reply_to_user_id,
            # 'parse': tweet.parse,
            # 'parse_list': tweet.parse_list,
            'place': tweet.place,
            # 'retweet': dir(tweet.retweet),
            # 'retweets': dir(tweet.retweets),
            'source': tweet.source,
            # 'source_url': tweet.source_url,
            'text': tweet.text,
            'truncated': tweet.truncated,
            'user': tweet.user.screen_name,
            }
            u = {
            '_id': tweet.author.screen_name, # use as mongo primary key
            'contributors_enabled': tweet.author.contributors_enabled, 
            'created_at': tweet.author.created_at, 
            'description': tweet.author.description, 
            'favourites_count': tweet.author.favourites_count, # beware the british
            'follow_request_sent': tweet.author.follow_request_sent, 
            'followers_count': tweet.author.followers_count, 
            'following': tweet.author.following, 
            'friends_count': tweet.author.friends_count, 
            'geo_enabled': tweet.author.geo_enabled, 
            'twitter_user_id': tweet.author.id, 
            'lang': tweet.author.lang, 
            'listed_count': tweet.author.listed_count, 
            'location': tweet.author.location, 
            'name': tweet.author.name, 
            'notifications': tweet.author.notifications, 
            'profile_image_url': tweet.author.profile_image_url, 
            'protected': tweet.author.protected, 
            'statuses_count': tweet.author.statuses_count, 
            'time_zone': tweet.author.time_zone, 
            'url': tweet.author.url, 
            'utc_offset': tweet.author.utc_offset, 
            'verified': tweet.author.verified,
            '_updated': datetime.datetime.now(),
            }
            authors.append(u)
            ts.append(t)

        self.update_authors(authors)
        
        # insert into db
        try:
            self.db[self.DB_NAME].insert(ts)
        except pymongo.errors.InvalidOperation: # no tweets?
            pass
        
        if self.debug:
            print "added %s tweets to the db" % (len(ts))

    def update_authors(self, authors):
        k = klout.KloutAPI(settings.KLOUT_API_KEY)
        update_count = 0
        
        for user in authors:
            records = [r for r in self.db[self.USER_COLL_NAME].find(spec={'_id': user['_id']})]
            if not records or abs(records[0]['_updated'] - datetime.datetime.now()) >= datetime.timedelta(1): # update once per day
                kwargs = { 'users': user['_id'] }
                try:
                    response = k.call('klout', **kwargs)
                    user['klout_score'] = response['users'][0]['kscore']
                except klout.KloutError: # probably a 404
                    pass
                self.db[self.USER_COLL_NAME].remove({'_id': user['_id']})
                self.db[self.USER_COLL_NAME].insert(user)
                update_count += 1

        if self.debug:
            print "updated %s users in the db" % (update_count)

            

    def classify_tweets(self):
        classifiers = []
        for active_classifier in active_classifiers:
            c = globals()[active_classifier]()
            classifiers.append(c)

        for r in self.db[self.DB_NAME].find(spec={'topics': {'$exists': False } },fields={'text': True, 'user': True}): # for all unclassified tweets
            topics = {}
            for c in classifiers:
                (topic, score) = c.classify(r['text'])
                topics[topic] = score

            self.db[self.DB_NAME].update({'_id': r['_id']}, {'$set': {'topics': topics }})

    
    # util classes    
    def setup_auth(self):
        """
        setup_auth: authorize tc with oath
        """
        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth_url = auth.get_authorization_url()
        p = subprocess.Popen("open %s" % auth_url, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        print "( if the browser fails to open, please go to: %s )" % auth_url
        verifier = raw_input("What's your PIN: ").strip()
        auth.get_access_token(verifier)
        pickle.dump((auth.access_token.key, auth.access_token.secret), open('settings_twitter_creds','w'))        
        return auth
    
    def init_twitter(self, username, password):
        auth = tweepy.BasicAuthHandler(username, password)
        api = tweepy.API(auth)
        return api


if __name__ == '__main__':
    l = loadTweets(debug=True)
########NEW FILE########
__FILENAME__ = s
#!/usr/bin/env python
# encoding: utf-8
"""
s.py

Created by Hilary Mason on 2010-08-15.
Copyright (c) 2010 Hilary Mason. All rights reserved.
"""


import sys, os
import re
import datetime
from optparse import OptionParser

import pymongo

import settings
from lib import mongodb
from lib import display


class Search(object):
    def __init__(self, options, args):
        self.debug = options.debug
        self.db = mongodb.connect('tweets')
        d = display.Display()        

        if options.user_search:
            twitterers = self.user_search(options.user_search, int(options.num))
            d.display_users(twitterers)
        else:
            tweets = self.tweet_search(args, int(options.num))
            d.display_tweets(tweets)
        
        
    def tweet_search(self, query_terms, num=10):
        r = re.compile(' '.join(query_terms), re.I)
        tweets = []
        for t in self.db['tweets'].find(spec={'text': r }).sort('created_at',direction=pymongo.DESCENDING):
            t['_display'] = True
            t['_datetime'] = datetime.datetime.strftime(t['created_at'], "%I:%M%p, %b %d, %Y %Z")
            tweets.append(t)
        
        if self.debug:
            print "%s total results" % (len(tweets))
            
        return tweets[:num]
        
    def user_search(self, user_terms, num=10):
        r = re.compile(user_terms, re.I)
        tweets = []
        
        # search username
        for t in self.db['users'].find(spec={'_id': r}).sort('_updated', direction=pymongo.DESCENDING):
            t['_display'] = True
            t['_datetime'] = datetime.datetime.strftime(t['_updated'], "%I:%M%p, %b %d, %Y %Z")
            tweets.append(t)

        usernames = [t['_id'] for t in tweets]

        # search name
        for t in self.db['users'].find(spec={'name': r}).sort('_updated', direction=pymongo.DESCENDING):
            if t['_id'] not in usernames:
                t['_display'] = True
                t['_datetime'] = datetime.datetime.strftime(t['_updated'], "%I:%M%p, %b %d, %Y %Z")
                tweets.append(t)
            
        



        if self.debug:
            print "%s total results" % (len(tweets))
            
        return tweets[:num]
    
    
if __name__ == "__main__":
    parser = OptionParser("usage: %prog [options] query terms")
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False, help="set debug mode = True")
    parser.add_option("-n", "--num", dest="num", action="store", default=10, help="number of tweets to retrieve")
    parser.add_option("-u", "--user", dest="user_search", action="store", default=None, help="search users")
    (options, args) = parser.parse_args()

    t = Search(options, args)
########NEW FILE########
__FILENAME__ = settings

# configure me!
TWITTER_USERNAME = 'hmason'

# you shouldn't need to touch

import pickle

CONSUMER_KEY = 'KYQAsPtHu09IzYpoQesZvA'
CONSUMER_SECRET = '3afLbAvMNFhsNLK6OcqxBjKSjD3hGaPKgXgFV38Ug'

KLOUT_API_KEY = 'p4ccneaqr32tjyygjgg25cm2'

try:
    (ACCESS_KEY, ACCESS_SECRET) = pickle.load(open('settings_twitter_creds'))
except IOError:
    (ACCESS_KEY, ACCESS_SECRET) = ('', '')
########NEW FILE########
__FILENAME__ = t
#!/usr/bin/env python
# encoding: utf-8
"""
t.py

Created by Hilary Mason on 2010-04-25.
Copyright (c) 2010 Hilary Mason. All rights reserved.
"""

import sys, os
import re
from optparse import OptionParser

import pymongo
import tweepy

import settings
from lib import mongodb
from lib import display    

class Twitter(object):
    def __init__(self, options):
        self.settings = self.load_settings()
        self.db = mongodb.connect('tweets')
                
        tweets = self.load_tweets(int(options.num), sort=options.sort, mark_read=options.mark_read)
        d = display.Display()
        d.display_tweets(tweets)
        
        
    def load_tweets(self, num, sort='time',mark_read=True):
        tweets = []
        
        if sort == 'antitime': # sort by time, oldest first
            for t in self.db['tweets'].find(spec={'r': {'$exists': False } }).sort('created_at',direction=pymongo.ASCENDING).limit(num):
                t['_display'] = True # mark all for display, so optimistic
                tweets.append(t)
        elif sort == 'rel':
            for t in self.db['tweets'].find(spec={'r': {'$exists': False } }).sort('created_at',direction=pymongo.ASCENDING): # get all unread tweets
                t['_display'] = True
                tweets.append(t)
            tweets = self.sort_by_relevance(tweets, num=num)
        elif sort == 'inf':
            for t in self.db['tweets'].find(spec={'r': {'$exists': False } }).sort('created_at',direction=pymongo.ASCENDING): # get all unread tweets
                t['_display'] = True
                tweets.append(t)
            tweets = self.sort_by_influence(tweets, num=num)
        else: # sort by time, newest first
            for t in self.db['tweets'].find(spec={'r': {'$exists': False } }).sort('created_at',direction=pymongo.DESCENDING).limit(num):
                t['_display'] = True
                tweets.append(t)
    
        # mark these tweets as 'read' in the db
        if mark_read:
            for t in tweets:
                self.db['tweets'].update({'_id': t['_id']}, {'$set': {'r': 1 }})


        # black/white lists
        for t in tweets:
            if t['user'] in self.settings['blacklist_users']:
                t['_display'] = False
                
            for blackword in self.settings['blacklist']:
                if blackword.search(t['text'].lower()):
                    t['_display'] = False
            
            t['_display_topics'] = []
            try:
                for topic, score in t['topics'].items():
                    # print "topic: %s, score: %s" % (topic, score)
                    # print "threshold: %s" % self.settings['topic_thresholds'][topic]
                    if score >= self.settings['topic_thresholds'][topic]:
                        t['_display_topics'].append(topic) 
            except KeyError: # no topic analysis for this tweet
                pass
                    
            if t['user'] in self.settings['whitelist_users']:
                t['_display'] = True
                
        # cache any links in these tweets so I can get to them easily
        self.extract_links(tweets)
                    
        return tweets
    
    def sort_by_influence(self, tweets, num):
        """
        sort_by_influence: sort tweets by klout score
        """
        for t in tweets:
            for k in self.db['users'].find(spec={'_id':t['author']}, fields={'klout_score': True}):
                try:
                    t['influence'] = k['klout_score']
                except KeyError: # no klout score
                    t['influence'] = 0

        return sorted(tweets, key=lambda x:-x['influence'])[:num]
        
    def sort_by_relevance(self, tweets, num):
        """
        sort_by_relevance: sorts tweets by arbitrary relevance to me. Criteria:
        1) does it mention me?
        2) is it by someone on my whitelist?
        3) is it about a topic that I care about?
        4) sort remainder by 'interestingness'
        """
        mentions = []
        whitelist = []
        topical = []
        other = []
        
        for t in tweets:
            t['_display_topics'] = []
            try:
                for topic, score in t['topics'].items():
                    if score >= self.settings['topic_thresholds'][topic]:
                        t['_display_topics'].append(topic) 
            except KeyError:
                pass

            if settings.TWITTER_USERNAME in t['text']:
                mentions.append(t)
            elif t['user'] in self.settings['whitelist_users']:
                whitelist.append(t)
            elif t['_display_topics']:
                topical.append(t)
            else:
                other.append(t)

        tweets = mentions + whitelist + topical + other
        
        return tweets[:num]
        
        
    def extract_links(self, tweets):
        """
        extract_links: pull links out of tweets and cache in a text file
        """
        re_http = re.compile("(http|https):\/\/(([a-z0-9\-]+\.)*([a-z]{2,5}))\/[\w|\/]+")
        links = []
        for t in tweets:
            r = re_http.search(t['text'])
            if r:
                links.append(r.group(0))
        
        if links:
            f = open(self.settings['link_cache_filename'], 'w')
            for link in links:
                f.write('%s\n' % link)
            f.close()
        
        
    def load_settings(self):
        settings = {}
        
        settings['topic_thresholds'] = {'default': .6, 'betaworks': 1.0, 'narcissism': .25, 'sports': .9999 }
        settings['link_cache_filename'] = 'link_cache'
        
        try:
            f = open('whitelist_users', 'r')
            settings['whitelist_users'] = [user.strip() for user in f.readlines()]
            f.close()
        except IOError:
            settings['whitelist_users'] = []

        try:
            f = open('blacklist_users', 'r')
            settings['blacklist_users'] = [user.strip() for user in f.readlines()]
            f.close()
        except IOError:
            settings['blacklist_users'] = []
        
        try:
            f = open('blacklist', 'r')
            settings['blacklist'] = [re.compile(b.lower().strip()) for b in f.readlines()]
            f.close()
        except IOError:
            settings['blacklist'] = []
        
        return settings

if __name__ == "__main__":
    parser = OptionParser("usage: %prog [options]") # no args this time
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False, help="set debug mode = True")
    parser.add_option("-m", "--mark_read", dest="mark_read", action="store_false", default=True, help="Don't mark displayed tweets as read")
    parser.add_option("-s", "--sort", dest="sort", action="store", default='time', help="Sort by time, antitime, rel")
    parser.add_option("-n", "--num", dest="num", action="store", default=10, help="number of tweets to retrieve")
    # parser.add_option("-t", "--topic", dest="topic", action="store", default=None, help="show one topic only")
    (options, args) = parser.parse_args()
    
    t = Twitter(options)
########NEW FILE########
__FILENAME__ = w
#!/usr/bin/env python
# encoding: utf-8
"""
w.py

Created by Hilary Mason on 2010-08-21.
"""

import sys, os
from optparse import OptionParser
import pickle

import tweepy

import settings
from lib import mongodb


class writeTweet(object):
    def __init__(self, options, args):
        if options.debug:
            print options
            print args
        
        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_KEY, settings.ACCESS_SECRET)
        self.api = tweepy.API(auth)
        tweet = args[0]
        self.post_tweet(tweet)
        
    def post_tweet(self, tweet):
        self.api.update_status(tweet)
    
    
    
if __name__ == '__main__':
    parser = OptionParser("usage: %prog [options] [tweet]") # no args this time
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False, help="set debug mode = True")
    (options, args) = parser.parse_args()

    l = writeTweet(options, args)
########NEW FILE########
