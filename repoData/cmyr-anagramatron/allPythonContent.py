__FILENAME__ = anadaemon
# coding=utf-8

from __future__ import print_function
import time
import sys
import random
import hitmanager
import anagramfunctions
import constants
import requests




class Daemon(object):

    """
    A stand alone tool for automatic posting of approved anagrams
    """

    def __init__(self, post_interval=0, debug=False):
        super(Daemon, self).__init__()
        self.datasource = None
        self._debug = debug
        self.post_interval = post_interval

    def run(self):
        try:
            self._check_post_time()
            while True:
                self.entertain_the_huddled_masses()
                self.sleep(self.post_interval)

        except KeyboardInterrupt:
            print('exiting')
            sys.exit(0)

    def _check_post_time(self):
        print('checking last post time')
        last_post = hitmanager.last_post_time() or 0
        print('last post at %s' % str(last_post))
        temps_perdu = time.time() - last_post
        if last_post and temps_perdu < (self.post_interval or constants.ANAGRAM_POST_INTERVAL) / 2:
            print('skipping post. %d elapsed, post_interval %d' %
                  (temps_perdu, self.post_interval))

            self.sleep()

    def entertain_the_huddled_masses(self):

        # ah, experience, my old master
        try:
            requests.head('http://www.twitter.com')
        except Exception as err:
            print('server appears offline', err, sep='\n')
            return

        # get most recent hit:
        hit = hitmanager.next_approved_hit()
        if not hit:
            print('no postable hit found')
            return

        print(hit['tweet_one']['tweet_text'], hit['tweet_two']['tweet_text'])
        if not hitmanager.post_hit(hit['id']):
            print('failed to post hit')
            # on failed post attempt again
            self.entertain_the_huddled_masses()
        else:
            print('posted hit')

    def sleep(self, interval=0, debug=False):
        interval = int(interval)
        
        if not interval:
            reload(constants)
            interval = constants.ANAGRAM_POST_INTERVAL * 60

        print('base interval is %d' % (interval / 60))

        randfactor = random.randrange(0, interval)
        interval = interval * 0.5 + randfactor
        sleep_chunk = 10  # seconds

        print('sleeping for %d minutes' % (interval / 60))

        if not debug:
            while interval > 0:
                sleep_status = ' %s remaining \r' % (
                    anagramfunctions.format_seconds(interval))
                sys.stdout.write(sleep_status.rjust(35))
                sys.stdout.flush()
                time.sleep(sleep_chunk)
                interval -= sleep_chunk

            print('\n')

        else:
            return interval / 60


# some reference stuff if we want to make this an actual daemon:


# def existing_instance():

#     if os.access(DAEMON_LOCK, os.F_OK):
#         print('accessed lockfile')
# if the lockfile is already there then check the PID number
# in the lock file
#         pidfile = open(DAEMON_LOCK, "r")
#         pidfile.seek(0)
#         old_pd = pidfile.readline()
#         print('found pidfile %d' % int(old_pd))
# Now we check the PID from lock file matches to the current
# process PID
#         if os.path.exists("/proc/%s" % old_pd):
#             print("You already have an instance of the program running")
#             print("It is running as process %s," % old_pd)
#             return True
#         else:

#             os.remove(DAEMON_LOCK)
#             return False
#     else:
#         print('no lock file found')

# def set_lock():
#     print('setting lock file')
#     pidfile = open(DAEMON_LOCK, "w")
#     pidfile.write("%s" % os.getpid())
#     pidfile.close


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--post-interval', type=int,
                        help='interval (in minutes) between posts')
    parser.add_argument('-d', '--debug',
                        help='run with debug flag', action="store_true")
    args = parser.parse_args()

    kwargs = {}
    kwargs['debug'] = args.debug
    kwargs['post_interval'] = args.post_interval or 0

    print(kwargs)
    print(type(kwargs['post_interval']))

    daemon = Daemon(**kwargs)
    return daemon.run()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = anagramatron
from __future__ import print_function

import time
import logging
import cPickle as pickle

from twitterhandler import StreamHandler
from datahandler import (DataCoordinator, NeedsMaintenance)
import anagramstats as stats
import hit_server
import multiprocessing


LOG_FILE_NAME = 'data/anagramer.log'


def main():
    # set up logging:
    logging.basicConfig(
        filename=LOG_FILE_NAME,
        format='%(asctime)s - %(levelname)s:%(message)s',
        level=logging.DEBUG
    )

    hitserver = multiprocessing.Process(target=hit_server.start_hit_server)
    hitserver.daemon = True
    hitserver.start()

    data_coordinator = DataCoordinator()
    stats.clear_stats()

    while 1:
        print('top of run loop')
        logging.debug('top of run loop')
        try:
            print('starting stream handler')
            stream_handler = StreamHandler()
            stream_handler.start()
            for processed_tweet in stream_handler:
                data_coordinator.handle_input(processed_tweet)
                stats.update_console()

        except NeedsMaintenance:
            logging.debug('caught NeedsMaintenance exception')
            print('performing maintenance')
            stream_handler.close()
            data_coordinator.perform_maintenance()

        except KeyboardInterrupt:
            stream_handler.close()
            data_coordinator.close()
            break



if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = anagramfunctions
import re
import anagramstats as stats
import unicodedata

from constants import (ANAGRAM_LOW_CHAR_CUTOFF, ANAGRAM_LOW_UNIQUE_CHAR_CUTOFF,
    ANAGRAM_ALPHA_RATIO_CUTOFF, ENGLISH_LETTER_FREQUENCIES)

ENGLISH_LETTER_LIST = sorted(ENGLISH_LETTER_FREQUENCIES.keys(),
                             key=lambda t: ENGLISH_LETTER_FREQUENCIES[t])
# This contains the various functions for filtering tweets, comparing
# potential anagrams, as well as some shared helper utilities.


freqsort = ENGLISH_LETTER_FREQUENCIES
# just to keep line_lengths sane



def improved_hash(text, debug=False):
    """
    only very *minorly* improved. sorts based on letter frequencies.
    """
    CHR_COUNT_START = 64  # we convert to chars; char 65 is A
    t_text = stripped_string(text)
    t_hash = ''.join(sorted(t_text, key=lambda t: freqsort[t]))
    letset = set(t_hash)
    break_letter = t_hash[-1:]
    if break_letter not in ENGLISH_LETTER_LIST:
        break_letter = ENGLISH_LETTER_LIST[-1]
    compressed_hash = ''
    for letter in ENGLISH_LETTER_LIST:
        if letter in letset:
            count = len(re.findall(letter, t_hash))
            count = (count if count < 48 else 48)
            # this is a hacky way of sanity checking our values.
            # if this shows up as a match we'll ignore it
            compressed_hash += chr(count + CHR_COUNT_START)
        else:
            if freqsort[letter] > freqsort[break_letter]:
                if len(compressed_hash) % 2:
                    # an uneven number of bytes will cause unicode errors?
                    compressed_hash += chr(64)
                break
            compressed_hash += chr(64)

    if len(compressed_hash) == 0:
        print('hash length is zero?')
        return '@@'
    return compressed_hash
    # return t_hash

def length_from_hash(in_hash):
    """
    takes an improved hash and returns the number of characters
    in the original string.
    """
    length = 0
    chars = list(in_hash)
    for c in chars:
        length += ord(c) - 64
    return length


def correct_encodings(text):
    """
    twitter auto converts &, <, > to &amp; &lt; &gt;
    """
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return text


def _strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def _text_contains_tricky_chars(text):
    if re.search(ur'[\u0080-\u024F]', text):
        return True
    return False


def _text_decodes_to_ascii(text):
    try:
        text.decode('ascii')
    except UnicodeEncodeError:
        return False
    return True


def _basic_filters(tweet):
    if tweet.get('lang') != 'en':
        return False
    if len(tweet.get('entities').get('user_mentions')) is not 0:
        return False
    #check for retweets
    if tweet.get('retweeted_status'):
        return False
    # check for links:
    if len(tweet.get('entities').get('urls')) is not 0:
        return False
    if re.search(r'[0-9]', tweet['text']):
        return False
    t = stripped_string(tweet['text'])
    if len(t) <= ANAGRAM_LOW_CHAR_CUTOFF:
        return False
    # ignore tweets with few characters
    st = set(t)
    if len(st) <= ANAGRAM_LOW_UNIQUE_CHAR_CUTOFF:
        return False
    return True


def _low_letter_ratio(text, cutoff=0.8):
    t = re.sub(r'[^a-zA-Z .,!?"\']', '', text)
    if (float(len(t)) / len(text)) < cutoff:
        return True
    return False


def filter_tweet(tweet):
    """
    filters out anagram-inappropriate tweets.
    Returns the original tweet object and cleaned tweet text on success.
    """
    if not _basic_filters(tweet):
        return False

    tweet_text = correct_encodings(tweet.get('text'))
    if not _text_decodes_to_ascii(tweet_text):
        # check for latin chars:
        if _text_contains_tricky_chars(tweet_text):
            tweet_text = _strip_accents(tweet_text)

    if _low_letter_ratio(tweet_text, ANAGRAM_ALPHA_RATIO_CUTOFF):
        return False

    return {'tweet_hash': improved_hash(tweet_text),
            'tweet_id': long(tweet['id_str']),
            'tweet_text': tweet_text
            }



def test_anagram(string_one, string_two):
    """
    most basic test, finds if tweets are just identical
    """
    stats.possible_hit()
    if not _char_diff_test(string_one, string_two):
        return False
    if not _word_diff_test(string_one, string_two):
        return False
    if not _combined_words_test(string_one, string_two):
        return False
    if not one_test_to_rule_them(string_one, string_two):
        return False
    return True


def _char_diff_test(string_one, string_two, cutoff=0.3):
    """
    basic test, looks for similarity on a char by char basis
    """
    stripped_one = stripped_string(string_one)
    stripped_two = stripped_string(string_two)

    total_chars = len(stripped_two)
    same_chars = 0

    if len(stripped_one) != len(stripped_two):
        return False

    for i in range(total_chars):
        if stripped_one[i] == stripped_two[i]:
            same_chars += 1
    try:
        if (float(same_chars) / total_chars) < cutoff:
            return True
    except ZeroDivisionError:
        print(string_one, string_two)
    return False


def _word_diff_test(string_one, string_two, cutoff=0.3):
    """
    looks for tweets containing the same words in different orders
    """
    words_one = stripped_string(string_one, spaces=True).split()
    words_two = stripped_string(string_two, spaces=True).split()

    word_count = len(words_one)
    same_words = 0

    if len(words_two) < len(words_one):
            word_count = len(words_two)
        # compare words to each other:
    for word in words_one:
        if word in words_two:
            same_words += 1
        # if more then $CUTOFF words are the same, fail test
    if (float(same_words) / word_count) < cutoff:
        return True
    else:
        return False

def _combined_words_test(string_one, string_two, cutoff=0.5):
    """
    looks for tweets where the same words have been #CombinedWithoutSpaces

    """
    words_one = stripped_string(string_one, spaces=True).split()
    words_two = stripped_string(string_two, spaces=True).split()

    if len(words_one) == len(words_two):
        return True
    # print(words_one, words_two)
    more_words = words_one if len(words_one) > len(words_two) else words_two;
    fewer_words = words_one if words_two == more_words else words_two
    # rejoin fewer words into a string:
    fewer_words = ' '.join(fewer_words)

    for word in more_words:
        if re.search(word, fewer_words):
            fewer_words = re.sub(word, '', fewer_words, count=1)

    # this leaves us, hopefully, with a smoking hulk of non-string.
    more_string = ''.join(more_words)
    fewer_words = re.sub(' ', '', fewer_words)
    more_string = re.sub(' ', '', more_string)
    if (len(fewer_words)/float(len(more_string))) > cutoff:
        return True
    else:
        return False


def one_test_to_rule_them(string_one, string_two, cutoff=0.8, stop=False):
    """
    searches s2 for words from s1, removing them where found.
    repeats in the opposite order on pass.
    """
    s1 = sorted(stripped_string(string_one, spaces=True).split(),
        key=len,
        reverse=True)
    s2 = stripped_string(string_two, spaces=True)
    for word in s1:
        if len(word) > 2 and re.search(word, s2):
            s2 = re.sub(word, '', s2, count=1)
    s1 = ''.join(s1)
    s2 = stripped_string(s2, spaces=False)

    if float(len(s2))/len(s1) < cutoff:
        return False
    else:
        if stop:
            return True
        return one_test_to_rule_them(string_two, string_one, stop=True)


def grade_anagram(hit):
    """
    an attempt to come up with a numerical value that expresses an anagrams
    potential 'interestingness'.
    """
    t1 = hit['tweet_one']['tweet_text']
    t2 = hit['tweet_two']['tweet_text']

    letter_count = len(stripped_string(t1))
    unique_letters = len(set(stripped_string(t1)))

    return letter_count, unique_letters


def format_seconds(seconds):
    """
    convert a number of seconds into a custom string representation
    """
    d, seconds = divmod(seconds, (60*60*24))
    h, seconds = divmod(seconds, (60*60))
    m, seconds = divmod(seconds, 60)
    time_string = ("%im %0.2fs" % (m, seconds))
    if h or d:
        time_string = "%ih %s" % (h, time_string)
    if d:
        time_string = "%id %s" % (d, time_string)
    return time_string


def show_anagram(one, two):
    print one
    print two
    print stripped_string(one, spaces=True)
    print stripped_string(two, spaces=True)
    print stripped_string(one)
    print stripped_string(two)
    print ''.join(sorted(stripped_string(two), key=str.lower))


def stripped_string(text, spaces=False):
    """
    returns lower case string with all non alpha chars removed
    """
    if spaces:
        text = re.sub(r'[_-]', ' ', text)  # replace dashes and underbars
        return re.sub(r'[^a-zA-Z ]', '', text).lower()
    return re.sub(r'[^a-zA-Z]', '', text).lower()


if __name__ == "__main__":
    pass

########NEW FILE########
__FILENAME__ = anagramstats
from __future__ import print_function
import time
import sys

import anagramfunctions

_tweets_seen = 0
_passed_filter = 0
_possible_hits = 0
_hits = 0
_overflow = 0
_start_time = time.time()
_buffer = 0
_max_buffer = 0
_cache_hits = 0
_cache_size = 0
_fetch_pool_size = 0


def clear_stats():
    global _tweets_seen, _passed_filter, _possible_hits
    global _hits, _overflow, _start_time, _buffer, _max_buffer
    global _cache_size, _cache_hits, _fetch_pool_size

    _tweets_seen = 0
    _passed_filter = 0
    _possible_hits = 0
    _hits = 0
    _overflow = 0
    _start_time = time.time()
    _buffer = 0
    _max_buffer = 0
    _cache_hits = 0
    _cache_size = 0
    _fetch_pool_size = 0


def tweets_seen(seen=1):
    global _tweets_seen
    _tweets_seen += seen


def passed_filter(passed=1):
    global _passed_filter
    _passed_filter += passed


def possible_hit(possible=1):
    global _possible_hits
    _possible_hits += possible


def hit(hit=1):
    global _hits
    _hits += hit


def overflow(over=1):
    global _overflow
    _overflow += over


def set_buffer(buffer_size):
    global _buffer, _max_buffer
    _buffer = buffer_size
    if _buffer > _max_buffer:
        _max_buffer = _buffer


def set_fetch_pool_size(size):
    global _fetch_pool_size
    _fetch_pool_size = size


def set_cache_size(size):
    global _cache_size
    _cache_size = size


def cache_hit():
    global _cache_hits
    _cache_hits += 1


def stats_dict():
    return {
            'tweets_seen': _tweets_seen,
            'passed_filter': _passed_filter,
            'possible_hits': _possible_hits,
            'hits': _hits,
            'overflow': _overflow,
            'start_time': _start_time
            }

def buffer_size():
    return _buffer


def update_console():
    global _tweets_seen, _passed_filter, _possible_hits, _hits, _overflow
    global _buffer, _start_time, _cache_hits, _cache_size

    seen_percent = 0
    if _tweets_seen > 0:
        seen_percent = int(100*(float(_passed_filter)/_tweets_seen))
    runtime = time.time()-_start_time

    status = (
        'tweets seen: ' + str(_tweets_seen) +
        " passed filter: " + str(_passed_filter) +
        " ({0}%)".format(seen_percent) +
        " hits " + str(_possible_hits + _fetch_pool_size) + '/' + str(_cache_hits) +
        " agrams: " + str(_hits) +
        " cachesize: " + str(_cache_size) +
        " buffer: " + str(_buffer) +
        " runtime: " + anagramfunctions.format_seconds(runtime)
    )
    sys.stdout.write(status + '\r')
    sys.stdout.flush()


########NEW FILE########
__FILENAME__ = anagramstream
from __future__ import print_function
import requests
import json
from requests_oauthlib import OAuth1
from twittercreds import (CONSUMER_KEY, CONSUMER_SECRET,
                          ACCESS_KEY, ACCESS_SECRET)


# disable logging from requests
import logging
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

class AnagramStream(object):
    """
    very basic single-purpose object for connecting to the streaming API
    in most use-cases python-twitter-tools or tweepy would be preferred
    BUT we need both gzip compression and the 'language' parameter
    """
    def __init__(self, access_key, access_secret, consumer_key, consumer_secret):
        self._access_key = access_key
        self._access_secret = access_secret
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret

    def stream_iter(self, endpoint='sample', languages='None', stall_warnings=True):
        auth = OAuth1(self._access_key, self._access_secret,
                      self._consumer_key, self._consumer_secret)

        url = 'https://stream.twitter.com/1.1/statuses/%s.json' % endpoint
        query_headers = {'Accept-Encoding': 'deflate, gzip',
                         'User-Agent': 'ANAGRAMATRON v0.5'}
        query_params = dict()
        lang_string = None
        if languages:
            if type(languages) is list:
                lang_string = ','.join(languages)
            elif isinstance(languages, basestring):
                lang_string = languages

        if lang_string:
            query_params['language'] = lang_string
        if stall_warnings:
            query_params['stall_warnings'] = True

        stream_connection = requests.get(url, auth=auth, stream=True,
                                         params=query_params, headers=query_headers)
        return stream_connection.iter_lines()

if __name__ == '__main__':
    anagram_stream = AnagramStream(CONSUMER_KEY, CONSUMER_SECRET,
                                   ACCESS_KEY, ACCESS_SECRET)

    stream_connection = anagram_stream.stream_iter(languages=['en'])
    for line in stream_connection:
        if line:
            try:
                tweet = json.loads(line)
                if tweet.get('text'):
                    print(tweet.get('text'))
            except ValueError:
                print(line)

########NEW FILE########
__FILENAME__ = constants
ANAGRAM_CACHE_SIZE = 200000
ANAGRAM_STREAM_BUFFER_SIZE = 30000

ANAGRAM_LOW_CHAR_CUTOFF = 16
ANAGRAM_LOW_UNIQUE_CHAR_CUTOFF = 11
ANAGRAM_ALPHA_RATIO_CUTOFF = 0.85

ANAGRAM_POST_INTERVAL = 150 #  minutes

STORAGE_DIRECTORY_PATH = 'data/'

ENGLISH_LETTER_FREQUENCIES = {
    'e': 1,
    't': 2,
    'a': 3,
    'o': 4,
    'i': 5,
    'n': 6,
    's': 7,
    'h': 8,
    'r': 9,
    'd': 10,
    'l': 11,
    'c': 12,
    'u': 13,
    'm': 14,
    'w': 15,
    'f': 16,
    'g': 17,
    'y': 18,
    'p': 19,
    'b': 20,
    'v': 21,
    'k': 22,
    'j': 23,
    'x': 24,
    'q': 25,
    'z': 26
}

########NEW FILE########
__FILENAME__ = datahandler
from __future__ import print_function
import anydbm
import multidbm
import os
import re
import sys
import logging
import time
import cPickle as pickle
import multiprocessing
from operator import itemgetter


import anagramfunctions
import hitmanager
import anagramstats as stats

from constants import (ANAGRAM_CACHE_SIZE, STORAGE_DIRECTORY_PATH,
 ANAGRAM_STREAM_BUFFER_SIZE)


DATA_PATH_COMPONENT = 'anagrammdbm'
CACHE_PATH_COMPONENT = 'cachedump'

from hitmanager import (HIT_STATUS_SEEN, HIT_STATUS_REVIEW, HIT_STATUS_POSTED,
        HIT_STATUS_REJECTED, HIT_STATUS_APPROVED, HIT_STATUS_MISC,
        HIT_STATUS_FAILED)



class NeedsMaintenance(Exception):
    """
    hacky exception raised when DataCoordinator is no longer able to keep up.
    use this to signal that we should shutdown and perform maintenance.
    """
    pass


class DataCoordinator(object):
    """
    DataCoordinator handles the storage, retrieval and comparisons
    of anagram candidates.
    It caches newly returned or requested candidates to memory,
    and maintains & manages a persistent database of older candidates.
    """
    def __init__(self, languages=['en'], noload=False):
        """
        language selection is not currently implemented
        """
        self.languages = languages
        self.cache = dict()
        self.datastore = None
        self._should_trim_cache = False
        self._write_process = None
        self._lock = multiprocessing.Lock()
        self._is_writing = multiprocessing.Event()
        self.dbpath = (STORAGE_DIRECTORY_PATH +
                       DATA_PATH_COMPONENT +
                       '_'.join(self.languages) + '.db')
        self.cachepath = (STORAGE_DIRECTORY_PATH +
                          CACHE_PATH_COMPONENT +
                          '_'.join(self.languages) + '.p')
        if not noload:
            self._setup()

    def _setup(self):
        """
        - unpickle previous session's cache
        - load / init database
        - extract hashes
        """
        self.cache = self._load_cache()
        self.datastore = multidbm.MultiDBM(self.dbpath)
        hitmanager._setup(self.languages)

    def handle_input(self, tweet):
        """
        recieves a filtered tweet.
        - checks if it exists in cache
        - checks if in database
        - if yes checks for hit
        """

        key = tweet['tweet_hash']
        if key in self.cache:
            stats.cache_hit()
            hit_tweet = self.cache[key]['tweet']
            if anagramfunctions.test_anagram(tweet['tweet_text'], hit_tweet['tweet_text']):
                del self.cache[key]
                hitmanager.new_hit(tweet, hit_tweet)
            else:
                self.cache[key]['tweet'] = tweet
                self.cache[key]['hit_count'] += 1
        else:
            # not in cache. in datastore?
            if key in self.datastore:
                self._process_hit(tweet)
            else:
                # not in datastore. add to cache
                self.cache[key] = {'tweet': tweet,
                                   'hit_count': 0}
                stats.set_cache_size(len(self.cache))

                if len(self.cache) > ANAGRAM_CACHE_SIZE:
                    self._trim_cache()


    def _process_hit(self, tweet):
        key = tweet['tweet_hash']
        try:
            hit_tweet = _tweet_from_dbm(self.datastore[key])
        except UnicodeDecodeError as err:
            print('error decoding hit for key %s' % key)
            self.cache[key] = {'tweet': tweet, 'hit_count': 1}
            return
        if anagramfunctions.test_anagram(tweet['tweet_text'],
            hit_tweet['tweet_text']):
            hitmanager.new_hit(hit_tweet, tweet)
        else:
            self.cache[key] = {'tweet': tweet, 'hit_count': 1}


    def _trim_cache(self, to_trim=None):
        """
        takes least frequently hit tweets from cache and writes to datastore
        """

        self._should_trim_cache = False
        # first just grab hashes with zero hits. If that's less then 1/2 total
        # do a more complex filter
            # find the oldest, least frequently hit items in cache:
        cache_list = self.cache.values()
        cache_list = [(x['tweet']['tweet_hash'],
                       x['tweet']['tweet_id'],
                       x['hit_count']) for x in cache_list]
        s = sorted(cache_list, key=itemgetter(1))
        cache_list = sorted(s, key=itemgetter(2))
        if not to_trim:
            to_trim = min(10000, (ANAGRAM_CACHE_SIZE/10))
        hashes_to_save = [x for (x, y, z) in cache_list[:to_trim]]

        # write those caches to disk, delete from cache, add to hashes
        for x in hashes_to_save:

            self.datastore[x] = _dbm_from_tweet(self.cache[x]['tweet'])
            del self.cache[x]

        buffer_size = stats.buffer_size()
        if buffer_size > ANAGRAM_STREAM_BUFFER_SIZE:
            # self.perform_maintenance()
            print('raised needs maintenance')
            raise NeedsMaintenance

    def _save_cache(self):
        """
        pickles the tweets currently in the cache.
        doesn't save hit_count. we don't want to keep briefly popular
        tweets in cache indefinitely
        """
        tweets_to_save = [self.cache[t]['tweet'] for t in self.cache]
        try:
            pickle.dump(tweets_to_save, open(self.cachepath, 'wb'))
            print('saved cache to disk with %i tweets' % len(tweets_to_save))
        except:
            logging.error('unable to save cache, writing')
            self._trim_cache(len(self.cache))

    def _load_cache(self):
        print('loading cache')
        cache = dict()
        try:
            loaded_tweets = pickle.load(open(self.cachepath, 'r'))
            # print(loaded_tweets)
            for t in loaded_tweets:
                cache[t['tweet_hash']] = {'tweet': t, 'hit_count': 0}
            print('loaded %i tweets to cache' % len(cache))
            return cache
        except IOError:
            logging.error('error loading cache :(')
            return cache
            # really not tons we can do ehre


    def perform_maintenance(self):
        """
        called when we're not keeping up with input.
        moves current database elsewhere and starts again with new db
        """
        print("perform maintenance called")
        # save our current cache to be restored after we run _setup (hacky)
        moveddb = self.datastore.archive()
        print('moved mdbm chunk: %s' % moveddb)
        print('mdbm contains %s chunks' % self.datastore.section_count())


    def close(self):
        if self._write_process and self._write_process.is_alive():
            print('write process active. waiting.')
            self._write_process.join()

        self._save_cache()
        self.datastore.close()


def _tweet_from_dbm(dbm_tweet):
    tweet_values = re.split(unichr(0017), dbm_tweet.decode('utf-8'))
    t = dict()
    t['tweet_id'] = int(tweet_values[0])
    t['tweet_hash'] = tweet_values[1]
    t['tweet_text'] = tweet_values[2]
    return t


def _dbm_from_tweet(tweet):
    dbm_string = unichr(0017).join([unicode(i) for i in tweet.values()])
    return dbm_string.encode('utf-8')


def repair_database():
    db = DataCoordinator()
    db.datastore.perform_maintenance()


def delete_short_entries(srcdb, cutoff=20, start=0):
    try:
        import gdbm
    except ImportError:
        print('database manipulation requires gdbm')

    print('trimming %s, cutoff %i' %(srcdb, cutoff))
    start_time = time.time()
    db = gdbm.open(srcdb, 'wf')
    k = db.firstkey()
    seen = 0
    marked = 0
    prevk = k
    todel = set()
    try:
        while k is not None:
            seen += 1
            prevk = k
            nextk = db.nextkey(k)
            if anagramfunctions.length_from_hash(k) < cutoff:
                todel.add(k)
                marked += 1
            sys.stdout.write('seen/marked: %i/%i next: %s\t\t\t\t\r' % (seen, marked, nextk))
            sys.stdout.flush()
            k = nextk
    finally:
        deleted = 0
        print('\ndeleting %i entries' % marked)
        for i in todel:
            try:
                del db[i]
            except KeyError:
                print('key error for key %s' % i)
            deleted += 1
            sys.stdout.write('deleted %i/%i\r' % (deleted, marked))
            sys.stdout.flush()
        
        db.sync()
        db.close()
        duration = time.time() - start_time
        print('\ndeleted %i of %i in %s' %
            (deleted, seen, anagramfunctions.format_seconds(duration)))


def combine_databases(srcdb, destdb, cutoff=20, start=0):
    try:
        import gdbm
    except ImportError:
        print('combining databases requires the gdbm module. :(')
    print('adding tweets from %s to %s' % (srcdb, destdb))

    db1 = gdbm.open(destdb, 'wf')
    db2 = gdbm.open(srcdb, 'w')

    k = db2.firstkey()
    temp_k = None
    seen = 0
    # if not start:
    #     start = 10**10

    if start:
        seen = 0
        while seen < start:
            k = db2.nextkey(k)
            sys.stdout.write('skipping: %i/%i \r' % (seen, start))
            sys.stdout.flush()
            seen += 1
    
    try:
        while k is not None:
            stats.tweets_seen()
            if (anagramfunctions.length_from_hash(k) < cutoff):
                k = db2.nextkey(k)
                continue                
            stats.passed_filter()
            tweet = _tweet_from_dbm(db2[k])
            if k in db1:
                tweet2 = _tweet_from_dbm(db1[k])
                if anagramfunctions.test_anagram(
                    tweet['tweet_text'],
                    tweet2['tweet_text'] 
                    ):
                    temp_k = db2.nextkey(k)
                    del db2[k]
                    hitmanager.new_hit(tweet, tweet2)
                else:
                    pass
            else:
                db1[k] = _dbm_from_tweet(tweet)
            stats.update_console()
            k = db2.nextkey(k)
            if not k and temp_k:
                k = temp_k
                temp_k = None
    finally:
        db1.sync()
        db1.close()
        db2.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repair', help='repair target database', action="store_true")
    parser.add_argument('db', type=str, help="source database file")
    parser.add_argument('-t', '--trim', type=int, help="trim low length values")
    parser.add_argument('-d', '--destination', type=str, help="destination database file")
    parser.add_argument('-s', '--start', type=int, help='skip-to position')
    args = parser.parse_args()

    
    if args.repair:
        return repair_database()


    if not args.db:
        print('please specify a target database.')

    outargs = dict()
    outargs['srcdb'] = args.db

    if args.trim:
        print('trim requested %i' % args.trim)
        outargs['cutoff'] = args.trim

    if args.start:
        outargs['start'] = args.start

    if args.destination:
        print('destination: %s' %args.destination)
        outargs['destdb'] = args.destination
        combine_databases(**outargs)
    else:
        delete_short_entries(**outargs)


    

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = hitmanager
from __future__ import print_function

import sqlite3 as lite
import os
import time

# import anagramconfig
import anagramfunctions
import anagramstats as stats
import logging
import sys

from twitterhandler import TwitterHandler
from twitter.api import TwitterError
from constants import STORAGE_DIRECTORY_PATH
HIT_PATH_COMPONENT = 'hitdata2'

HIT_STATUS_REVIEW = 'review'
HIT_STATUS_SEEN = 'seen'
HIT_STATUS_REJECTED = 'rejected'
HIT_STATUS_POSTED = 'posted'
HIT_STATUS_APPROVED = 'approved'
HIT_STATUS_MISC = 'misc'
HIT_STATUS_FAILED = 'failed'

dbpath = None
hitsdb = None
twitter_handler = None
_new_hits_counter = 0


def _setup(languages=['en'], path=None):
    global dbpath, hitsdb
    dbpath = path
    if not dbpath:
        dbpath = (STORAGE_DIRECTORY_PATH +
                  HIT_PATH_COMPONENT +
                  '_'.join(languages) + '.db')

    if not os.path.exists(dbpath):
        hitsdb = lite.connect(dbpath)
        cursor = hitsdb.cursor()
        print('hits db not found, creating')
        cursor.execute("""CREATE TABLE hits
            (hit_id INTEGER, hit_status TEXT, hit_date INTEGER, hit_hash TEXT, hit_rating text, flags TEXT,
                tweet_one TEXT, tweet_two TEXT)""")
        cursor.execute("CREATE TABLE hitinfo (last_post REAL)")
        cursor.execute("CREATE TABLE post_queue (hit_id INTEGER)")
        hitsdb.commit()
    else:
        hitsdb = lite.connect(dbpath)
        cursor = hitsdb.cursor() 
        cursor.execute("CREATE TABLE IF NOT EXISTS post_queue (hit_id INTEGER)")

def _checkit():
    if not dbpath or hitsdb:
        _setup()


def new_hit(first, second):
    _checkit()
    global _new_hits_counter
    
    hit = {
           "id": int(time.time()*1000),
           "status": HIT_STATUS_REVIEW,
           "hash": first['tweet_hash'],
           "tweet_one": first,
           "tweet_two": second
        }

    # if _hit_on_blacklist(hit):
    #     return
    if _hit_collides_with_previous_hit(hit):
        return

    stats.hit()
    try:
        hit = _fetch_hit_tweets(hit)
        _new_hits_counter += 1
        _add_hit(hit)
    except TwitterError as err:
        print('tweet missing, will pass')
        pass


def _fetch_hit_tweets(hit):
    """
    attempts to fetch tweets in hit.
    if successful builds up more detailed hit object.
    returns the input hit unchaged on failure
    """
    global twitter_handler
    if not twitter_handler:
        twitter_handler = TwitterHandler()

    t1 = twitter_handler.fetch_tweet(hit['tweet_one']['tweet_id'])
    t2 = twitter_handler.fetch_tweet(hit['tweet_two']['tweet_id'])
    if t1 and t2:
        hit['tweet_one']['fetched'] = _cleaned_tweet(t1)
        hit['tweet_two']['fetched'] = _cleaned_tweet(t2)

    return hit


def _cleaned_tweet(tweet):
    """
    returns a dict of desirable twitter info
    """
    twict = dict()
    twict['text'] = anagramfunctions.correct_encodings(tweet.get('text'))
    twict['user'] = {
        'name': tweet.get('user').get('name'),
        'screen_name': tweet.get('user').get('screen_name'), 
        'profile_image_url': tweet.get('user').get('profile_image_url')
        }
    twict['created_at'] = tweet.get('created_at')
    return twict


def hits_newer_than_hit(hit_id):
    
    cursor = hitsdb.cursor()
    cursor.execute("SELECT * FROM hits WHERE hit_id > (?)", (hit_id,))
    results = cursor.fetchall()
    return len(results)


def new_hits_count():
    _checkit()
    cursor = hitsdb.cursor()
    try:
        cursor.execute("SELECT * FROM hits WHERE hit_status = (?)",
            (HIT_STATUS_REVIEW,))
        results = cursor.fetchall()
        return len(results)
    except ValueError:
        return "420"


def last_post_time():
    # return the time of the last successful post
    _checkit()
    cursor = hitsdb.cursor()
    cursor.execute("SELECT * from hitinfo")
    results = cursor.fetchall()
    results = [float(x[0]) for x in results]
    if len(results):
        return max(results)


def _hit_collides_with_previous_hit(hit):
    
    cursor = hitsdb.cursor()
    cursor.execute("SELECT * FROM hits WHERE hit_hash=?", (hit['hash'], ))
    result = cursor.fetchone()
    if result:
        # do some comparisons
        result = hit_from_sql(result)
        r1 = result['tweet_one']['tweet_text']
        r2 = result['tweet_two']['tweet_text']
        t1 = hit['tweet_one']['tweet_text']
        t2 = hit['tweet_two']['tweet_text']
        if anagramfunctions.test_anagram(r1, t1):
            # print('hit collision:', hit, result)
            logging.debug('hit collision: %s %s' % (r1, t1))
            return True
        if anagramfunctions.test_anagram(r1, t2):
            # print('hit collision:', hit, result)
            logging.debug('hit collision: %s %s' % (r1, t2))
            return True
        if anagramfunctions.test_anagram(r2, t1):
            # print('hit collision:', hit, result)
            logging.debug('hit collision: %s %s' % (r2, t1))
            return True
        if anagramfunctions.test_anagram(r2, t2):
            # print('hit collision:', hit, result)
            logging.debug('hit collision: %s %s' % (r2, t2))
            return True

    return False


def _add_hit(hit):
    cursor = hitsdb.cursor()

    cursor.execute("INSERT INTO hits VALUES (?,?,?,?,?,?,?,?)",
                  (str(hit['id']),
                   hit['status'],
                   str(time.time()),
                   str(hit['hash']),
                   '0',
                   '0',
                   repr(hit['tweet_one']),
                   repr(hit['tweet_two'])
                   ))
    hitsdb.commit()


def get_hit(hit_id):
    
    cursor = hitsdb.cursor()
    cursor.execute("SELECT * FROM hits WHERE hit_id=:id",
                   {"id": str(hit_id)})
    result = cursor.fetchone()
    return hit_from_sql(result)


def remove_hit(hit_id):
    
    cursor = hitsdb.cursor()
    cursor.execute("DELETE FROM hits WHERE hit_id=:id",
                   {"id": str(hit_id)})
    hitsdb.commit()


def set_hit_status(hit_id, status):
    
    if status not in [HIT_STATUS_REVIEW, HIT_STATUS_MISC, HIT_STATUS_SEEN,
                      HIT_STATUS_APPROVED, HIT_STATUS_POSTED,
                      HIT_STATUS_REJECTED, HIT_STATUS_FAILED]:
        print('invalid status')
        return False
    # get the hit, delete the hit, add it again with new status.
    hit = get_hit(hit_id)
    hit['status'] = status
    remove_hit(hit_id)
    _add_hit(hit)
    # assert(get_hit(hit_id)['status'] == status)
    return True


def all_hits(with_status=None, cutoff_id=None):
    _checkit()
    cursor = hitsdb.cursor()
    if not with_status:
        cursor.execute("SELECT * FROM hits")
    else:
        cursor.execute("SELECT * FROM hits WHERE hit_status = (?)", (with_status,))
    results = cursor.fetchall()
    hits = []
    for item in results:
        hits.append(hit_from_sql(item))
    if cutoff_id:
        hits = [h for h in hits if h['id'] < cutoff_id]
    return hits


def next_approved_hit():
    """ no, this is not particuarly efficient """
    hits = all_hits(HIT_STATUS_APPROVED)
    hits = sorted(hits, key=lambda k: k['id'])
    if len(hits):
        return hits.pop()


def hit_from_sql(item):
    """
    convenience method for converting the result of an sql query
    into a python dictionary compatable with anagramer
    """
    return {'id': long(item[0]),
            'status': str(item[1]),
            'timestamp': item[2],
            'hash': str(item[3]),
            'rating': str(item[4]),
            'flags': str(item[5]),
            'tweet_one': eval(item[6]),
            'tweet_two': eval(item[7])
            }

def reject_hit(hit_id):
    set_hit_status(hit_id, HIT_STATUS_REJECTED)
    return True


def post_hit(hit_id):
    global twitter_handler
    if not twitter_handler:
        twitter_handler = TwitterHandler()
    if twitter_handler.post_hit(get_hit(hit_id)):
        set_hit_status(hit_id, HIT_STATUS_POSTED)
        # keep track of most recent post:
        cursor = hitsdb.cursor()
        cursor.execute("INSERT INTO hitinfo VALUES (?)", (str(time.time()),))
        hitsdb.commit()
        return True
    else:
        set_hit_status(hit_id, HIT_STATUS_FAILED)
        return False

def queue_hit(hit_id):
    cursor = hitsdb.cursor()
    cursor.execute("INSERT INTO post_queue VALUES (?)", (str(hit_id),))
    hitsdb.commit()

def get_queued_hits():
    cursor = hitsdb.cursor()
    cursor.execute("SELECT * FROM post_queue")
    hits = cursor.fetchall()
    return [h[0] for h in hits]

def post_queued_hit(hit_id):
    cursor = hitsdb.cursor()
    cursor.execute("DELETE FROM post_queue WHERE hit_id = (?)", (str(hit_id),))
    return post_hit(hit_id)


def approve_hit(hit_id):
    set_hit_status(hit_id, HIT_STATUS_APPROVED)
    return True

def review_hits(to_post=False):
    """
    manual tool for reviewing hits on the command line
    """
    
    status = HIT_STATUS_REVIEW if not to_post else HIT_STATUS_APPROVED
    hits = all_hits(status)
    hits = [(h, anagramfunctions.grade_anagram(h)) for h in hits]
    hits = sorted(hits, key= lambda k: k[1], reverse=True)
    hits = [h[0] for h in hits]

    print('found %i hits in need of review' % len(hits))
    while True:
        print(' anagram review (%i)'.center(80, '-') % len(hits))
        term_height = int(os.popen('stty size', 'r').read().split()[0])
        display_count = min(((term_height - 3) / 3), len(hits))
        display_hits = {k: hits[k] for k in range(display_count)}
        
        for h in display_hits:
            msg = "%s  %s" % (display_hits[h]['tweet_one']['tweet_id'], display_hits[h]['tweet_two']['tweet_id'])
            print(msg)
            print(str(h).ljust(9), display_hits[h]['tweet_one']['tweet_text'])
            print(' '*10, display_hits[h]['tweet_two']['tweet_text'])

        print('enter space seperated numbers of anagrams to approve. q to quit.')
        inp = raw_input(': ')
        if inp in [chr(27), 'x', 'q']:
            break

        approved = inp.split()
        print(approved)
        for h in display_hits:
            if str(h) in approved:
                if not to_post:
                    print('approved', h)
                    approve_hit(display_hits[h]['id'])
                else:
                    print('marked %i as posted' % h)
                    set_hit_status(display_hits[h]['id'], HIT_STATUS_POSTED)
            else:
                if not to_post:
                    set_hit_status(display_hits[h]['id'], HIT_STATUS_SEEN)
            hits.remove(display_hits[h])




if __name__ == "__main__":
    args = sys.argv[1:]
    if "-r" in args:
        review_hits(True)


    review_hits()


########NEW FILE########
__FILENAME__ = hit_server
from __future__ import print_function
from bottle import (Bottle, run, request, server_names,
                    ServerAdapter, abort)
import time
import hitmanager
import anagramstats as stats
import daemon
# import os
# import sys

from hitmanager import (HIT_STATUS_REVIEW, HIT_STATUS_SEEN, HIT_STATUS_MISC,
    HIT_STATUS_REJECTED, HIT_STATUS_POSTED, HIT_STATUS_APPROVED)
# SSL subclass of bottle cribbed from:
# http://dgtool.blogspot.com.au/2011/12/ssl-encryption-in-python-bottle.html

# Declaration of new class that inherits from ServerAdapter
# It's almost equal to the supported cherrypy class CherryPyServer

from serverauth import AUTH_TOKEN, TEST_PORT


class MySSLCherryPy(ServerAdapter):
    def run(self, handler):
        import cherrypy
        from cherrypy import wsgiserver
        server = cherrypy.wsgiserver.CherryPyWSGIServer(
                                                        (self.host, self.port),
                                                        handler,
                                                        numthreads=1,
                                                        max=1)
        # If cert variable is has a valid path, SSL will be used
        # You can set it to None to disable SSL
        cert = 'data/server.pem'  # certificate path
        server.ssl_certificate = cert
        server.ssl_private_key = cert
        try:
            server.start()
        finally:
            server.stop()

# Add our new MySSLCherryPy class to the supported servers
# under the key 'mysslcherrypy'

server_names['sslbottle'] = MySSLCherryPy
app = Bottle()

def authenticate(auth):
    return True
    if auth == AUTH_TOKEN:
        return True
    print('failed authentication')
    abort(401, '-_-')
# actual bottle stuff


@app.route('/hits')
def get_hits():
    print(request)
    count = 50
    auth = request.get_header('Authorization')
    if not authenticate(auth):
        return
    # update data
    try:
        status = str(request.query.status)
    except ValueError:
        status = HIT_STATUS_REVIEW
    try:
        cutoff = int(request.query.cutoff)
    except ValueError:
        cutoff = 0
    if (request.query.count):
        count = int(request.query.count)

    print('client requested %i hits with %s status, from %i' % 
        (count, status, cutoff))    
    hits = hitmanager.all_hits(status, cutoff)
    total_hits = len(hits)
    print('hitmanager returned %i hits' % total_hits)
    hits = sorted(hits, key=lambda k: k['id'], reverse=True)
    hits = hits[:count]
    print("returned %i hits" % len(hits))
    return {'hits': hits, 'total_count': total_hits}


@app.route('/mod')
def modify_hit():
    print(request)
    auth = request.get_header('Authorization')
    if not authenticate(auth):
        return
    hit_id = int(request.query.id)
    action = str(request.query.status)
    print(hit_id, action)
    if not hit_id or not action:
        abort(400, 'v0_0v')
        
    success_flag = hitmanager.set_hit_status(hit_id, action)
    success_string = 'succeeded' if success_flag else 'FAILED'
    print('modification of hit %i to status %s %s'
        % (hit_id, action, success_string))
    return {'action': action, 'hit': hit_id, 'success': success_flag}

@app.route('/seen')
def mark_seen():
    auth = request.get_header('Authorization')
    if not authenticate(auth):
        return
    hit_ids = request.query.hits
    hit_ids = hit_ids.split(',')
    print(hit_ids)
    if not len(hit_ids):
        print('no ids -_-')

    if len(hit_ids) == 1:
        itwerked = hitmanager.set_hit_status(hit_ids[0], HIT_STATUS_SEEN)
        print('status changed? %s' % str(itwerked))
    for i in hit_ids:
        hitmanager.set_hit_status(i, HIT_STATUS_SEEN)

    return {'action': HIT_STATUS_SEEN, 'count': len(hit_ids)}


@app.route('/approve')
def approve_hit():
    auth = request.get_header('Authorization')
    if not authenticate(auth):
        return
    print("/approve endpoint received request:", request.json, request.params)
    hit_id = int(request.query.id)
    post_now = int(request.query.post_now)
    print(hit_id, post_now)
    flag = None
    if (post_now):
        flag = hitmanager.post_hit(hit_id)
        if flag:
            print('posting hit: %i' % hit_id)
    else:
        flag = hitmanager.approve_hit(hit_id)
        if flag:
            print('approved hit: %i' % hit_id)

    action = HIT_STATUS_POSTED if post_now else HIT_STATUS_APPROVED
    return {
        'action': action,
        'hit': hit_id,
        'success': flag}


@app.route('/info')
def info():
    """
    returns some basic stats about what's happening on the server.
    """
    auth = request.get_header('Authorization')
    if not authenticate(auth):
        return
    stats_dict = stats.stats_dict()
    new_hits = hitmanager.new_hits_count()
    last_post = hitmanager.last_post_time()
    return {'stats': stats_dict, 'new_hits': new_hits, 'last_post': last_post}


def start_hit_server(debug=False):
    if debug:
        run(app, host='127.0.0.1', port=TEST_PORT, debug=True)
    else:
        run(app, host='0.0.0.0', port=TEST_PORT, debug=True, server='sslbottle')
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--daemonize',
                        help='run as daemon', action="store_true")
    parser.add_argument('--debug',
                        help='run locally', action="store_true")
    args = parser.parse_args()
    if args.daemonize:
        start_hit_daemon(args.debug)
    else:
        start_hit_server(args.debug)

########NEW FILE########
__FILENAME__ = multidbm
from __future__ import print_function
import anydbm
import cPickle as pickle
import os
import time
import re
import logging
from stat import S_ISREG, ST_CTIME, ST_MODE


_METADATA_FILE = 'meta.p'
_PATHKEY = 'X43q2smxlkFJ28h$@3xGN' # gurrenteed unlikely!!


class MultiDBM(object):
    """
    MultiDBM acts as a wrapper around multiple DBM files
    as data retrieval becomes too slow older files are archived.
    """

    def __init__(self, path, chunk_size=2000000):
        self._data = []
        self._metadata = dict()
        self._path = path
        self._section_size = chunk_size
        self._setup()

    def __contains__(self, item):
        for db in self._data:
            if item in db:
                return True
        return False

    def __getitem__(self, key):
        for db in self._data:
            if key in db:
                return db[key]
        raise KeyError

    def __setitem__(self, key, value):
        i = 0
        if self._metadata['cursize'] == self._section_size:
            self._add_db()
        last_db = len(self._data) - 1
        for db in self._data:
            if key in db or i == last_db:
                if i == last_db and key not in db:
                    self._metadata['totsize'] += 1
                    self._metadata['cursize'] += 1
                # logging.debug('adding key to file # %i' % i)
                db[key] = value
                return
            i += 1

    def __delitem__(self, key):
        for db in self._data:
            if key in db:
                del db[key]
                self._metadata['totsize'] -= 1
                return
        raise KeyError

    def __len__(self):
        """
        length calculations are estimates since we assume
        all non-current chunks are at capacity.
        In reality some keys will likely get deleted.
        """
        return (self._section_size * len(self._data-1)
            + self._metadata['cursize'])


    def _setup(self):
        if os.path.exists(self._path):
            self._metadata = pickle.load(open('%s/%s' % (self._path, _METADATA_FILE), 'r'))
            print('loaded metadata: %s' % repr(self._metadata))
            logging.debug('loaded metadata %s' % repr(self._metadata))
            
            # sort our dbm segments by creation date
            ls = (os.path.join(self._path, i) for i in os.listdir(self._path)
                if re.findall('mdbm', i))
            ls = ((os.stat(path), path) for path in ls)
            ls = ((stat[ST_CTIME], path) for stat, path in ls)
            dbses = [path for stat, path in sorted(ls)]
            for db in dbses:
                try:
                    self._data.append(anydbm.open(db, 'c'))
                except Exception as err:
                    print('error appending dbfile: %s' % db, err)

            print('loaded %i dbm files' % len(self._data))
        else:
            print('path not found, creating')
            os.makedirs(self._path)
            os.makedirs('%s/archive' % self._path)
            self._metadata['totsize'] = 0
            self._metadata['cursize'] = 0

        if not len(self._data):
            self._add_db()

    def _add_db(self):
        filename = 'mdbm%s.db' % time.strftime("%b%d%H%M")
        # filename = 'mdbm%s.db' % str(time.time())
        path = self._path + '/%s' % filename
        db = anydbm.open(path, 'c')
        db[_PATHKEY] = filename
        self._data.append(db)
        self._metadata['cursize'] = 0
        logging.debug('mdbm added new dbm file: %s' % filename)

    def _remove_old(self):
        db = self._data.pop(0)
        filename = db[_PATHKEY]
        db.close()
        target = '%s/%s' % (self._path, filename)
        destination = '%s/archive/%s' % (self._path, filename)
        os.rename(target, destination)
        logging.debug('mdbm moved old dbm file to %s' % destination)
        return destination

    def section_count(self):
        return len(self._data)

    def archive(self):
        return self._remove_old()

    def close(self):
        path = '%s/%s' % (self._path, _METADATA_FILE)
        print('dumping path:', path)
        pickle.dump(self._metadata, open(path, 'wb'))
        for db in self._data:
            db.close()


    def perform_maintenance(self):
        for db in self._data:
            db.reorganize()

if __name__ == '__main__':
    test()
########NEW FILE########
__FILENAME__ = tweetfetcher
import cPickle as pickle
import time
import sys
import twitterhandler
import anagramer

if __name__ == "__main__":
    stream = twitterhandler.StreamHandler(languages=['en'])
    stream.start()
    count = 0
    save_interval = 50000
    tlist = []

    try:
        for t in stream:
            t = anagramer.filter_tweet(t)
            if not t: 
                continue

            tlist.append(t)
            count += 1
            sys.stdout.write(str(count) + '\r')
            sys.stdout.flush()
            if count > save_interval:
                filename = "testdata/filt_%s.p" % time.strftime("%b%d%H%M")
                pickle.dump(tlist, open(filename, 'wb'))
                count = 0
                tlist = []
    finally:
        if count > 1000:
            filename = "testdata/filt_%s.p" % time.strftime("%b%d%H%M")
            pickle.dump(tlist, open(filename, 'wb'))

########NEW FILE########
__FILENAME__ = twitterhandler
from __future__ import print_function

import httplib
import logging
import Queue
import multiprocessing
import time

from collections import deque
from ssl import SSLError
from socket import error as SocketError
from urllib2 import HTTPError

from twitter.oauth import OAuth
from twitter.stream import TwitterStream
from twitter.api import Twitter, TwitterError, TwitterHTTPError
import tumblpy
import json

import anagramfunctions
import anagramstats as stats
from anagramstream import AnagramStream


# my twitter OAuth key:
from twittercreds import (CONSUMER_KEY, CONSUMER_SECRET,
                          ACCESS_KEY, ACCESS_SECRET)
# my tumblr OAuth key:
from tumblrcreds import (TUMBLR_KEY, TUMBLR_SECRET,
                         TOKEN_KEY, TOKEN_SECRET, TUMBLR_BLOG_URL)

from constants import (ANAGRAM_STREAM_BUFFER_SIZE)


class StreamHandler(object):
    """
    handles twitter stream connections. Buffers incoming tweets and
    acts as an iter.
    """
    def __init__(self,
                 buffersize=ANAGRAM_STREAM_BUFFER_SIZE,
                 timeout=90,
                 languages=['en']
                 ):
        self.buffersize = buffersize
        self.timeout = timeout
        self.languages = languages
        self.stream_process = None
        self.queue = multiprocessing.Queue()
        self._error_queue = multiprocessing.Queue()
        self._buffer = deque()
        self._should_return = False
        self._iter = self.__iter__()
        self._overflow = multiprocessing.Value('L', 0)
        self._tweets_seen = multiprocessing.Value('L', 0)
        self._passed_filter = multiprocessing.Value('L', 0)
        self._lock = multiprocessing.Lock()
        self._backoff_time = 0

    @property
    def overflow(self):
        return long(self._overflow.value)

    def update_stats(self):
        with self._lock:
            if self._overflow.value:
                stats.overflow(self._overflow.value)
                self._overflow.value = 0
            if self._tweets_seen.value:
                stats.tweets_seen(self._tweets_seen.value)
                self._tweets_seen.value = 0
            if self._passed_filter.value:
                stats.passed_filter(self._passed_filter.value)
                self._passed_filter.value = 0
        stats.set_buffer(self.bufferlength())

    def __iter__(self):
        """
        the connection to twitter is handled in another process
        new tweets are added to self.queue as they arrive.
        on each call to iter we move any tweets in the queue to a fifo buffer
        this makes keeping track of the buffer size a lot cleaner.
        """
        while 1:
            if self._should_return:
                print('breaking iteration')
                raise StopIteration
            while 1:
                # add all new items from the queue to the buffer
                try:
                    self._buffer.append(self.queue.get_nowait())
                except Queue.Empty:
                    break
            try:
                self.update_stats()
                if len(self._buffer):
                    # if there's a buffer element return it
                    yield self._buffer.popleft()
                else:
                    yield self.queue.get(True, self.timeout)
                    self._backoff_time = 0
                    continue
            except Queue.Empty:
                print('queue timeout, restarting thread')
                # means we've timed out, and should try to reconnect
                self._stream_did_timeout()
        print('exiting iter loop')

    def next(self):
        return self._iter.next()

    def start(self):
        """
        creates a new thread and starts a streaming connection.
        If a thread already exists, it is terminated.
        """
        self._should_return = False
        print('creating new server connection')
        logging.debug('creating new server connection')
        if self.stream_process is not None:
            print('terminating existing server connection')
            logging.debug('terminating existing server connection')
            self.stream_process.terminate()
            if self.stream_process.is_alive():
                pass
            else:
                print('thread terminated successfully')
                logging.debug('thread terminated successfully')

        self.stream_process = multiprocessing.Process(
                                target=self._run,
                                args=(self.queue,
                                      self._error_queue,
                                      self._backoff_time,
                                      self._overflow,
                                      self._tweets_seen,
                                      self._passed_filter,
                                      self._lock,
                                      self.languages))
        self.stream_process.daemon = True
        self.stream_process.start()

        print('created process %i' % self.stream_process.pid)

    def _stream_did_timeout(self):
        """
        check for errors and choose a reconnection strategy.
        see: (https://dev.twitter.com/docs/streaming-apis/connecting#Stalls)
        """
        err = None
        while 1:
            # we could possible have more then one error?
            try:
                err = self._error_queue.get_nowait()
                logging.error('received error from stream process', err)
                print(err, 'backoff time:', self._backoff_time)
            except Queue.Empty:
                break
        if err:
            print(err)
            error_code = err.get('code')

            if error_code == 420:
                if not self._backoff_time:
                    self._backoff_time = 60
                else:
                    self._backoff_time *= 2
            else:
                # a placeholder, for now
                # elif error_code in [400, 401, 403, 404, 405, 406, 407, 408, 410]:
                if not self._backoff_time:
                    self._backoff_time = 5
                else:
                    self._backoff_time *= 2
                if self._backoff_time > 320:
                    self._backoff_time = 320
            # if error_code == 'TCP/IP level network error':
            #     self._backoff_time += 0.25
            #     if self._backoff_time > 16.0:
            #         self._backoff_time = 16.0
        self.start()

    def close(self):
        """
        terminates existing connection and returns
        """
        self._should_return = True
        if self.stream_process:
            self.stream_process.terminate()
        print("\nstream handler closed with overflow %i from buffer size %i" %
              (self.overflow, self.buffersize))
        logging.debug("stream handler closed with overflow %i from buffer size %i" %
              (self.overflow, self.buffersize))

    def bufferlength(self):
        return len(self._buffer)

    def _run(self, queue, errors, backoff_time, overflow, seen, passed, lock, languages):
        """
        handle connection to streaming endpoint.
        adds incoming tweets to queue.
        runs in own process.
        errors is a queue we use to transmit exceptions to parent process.
        """
        # if we've been given a backoff time, sleep
        if backoff_time:
            time.sleep(backoff_time)
        stream = AnagramStream(
            CONSUMER_KEY,
            CONSUMER_SECRET,
            ACCESS_KEY,
            ACCESS_SECRET)

        try:
            stream_iter = stream.stream_iter(languages=languages)
            logging.debug('stream begun')
            for tweet in stream_iter:
                if tweet is not None:
                    try:
                        tweet = json.loads(tweet)
                    except ValueError:
                        continue
                    if not isinstance(tweet, dict):
                        continue
                    if tweet.get('warning'):
                        print('\n', tweet)
                        logging.warning(tweet)
                        errors.put(dict(tweet))
                        continue
                    if tweet.get('disconnect'):
                        logging.warning(tweet)
                        errors.put(dict(tweet))
                        continue
                    if tweet.get('text'):
                        with lock:
                            seen.value += 1
                        processed_tweet = anagramfunctions.filter_tweet(tweet)
                        if processed_tweet:
                            with lock:
                                passed.value += 1
                            try:
                                queue.put(processed_tweet, block=False)
                            except Queue.Full:
                                pass

        except (HTTPError, SSLError, TwitterHTTPError, SocketError) as err:
            print(type(err))
            print(err)
            error_dict = {'error': str(err), 'code': err.code}
            errors.put(error_dict)


class TwitterHandler(object):
    """
    The TwitterHandler object handles all of the interactions with twitter.
    This includes setting up streams and returning stream iterators, as well
    as handling normal twitter functions such as retrieving specific tweets,
    posting tweets, and sending messages as necessary.
    It also now includes a basic tumblr posting utility function.
    """

    def __init__(self):
        self.stream = TwitterStream(
            auth=OAuth(ACCESS_KEY,
                       ACCESS_SECRET,
                       CONSUMER_KEY,
                       CONSUMER_SECRET),
            api_version='1.1')
        self.twitter = Twitter(
            auth=OAuth(ACCESS_KEY,
                       ACCESS_SECRET,
                       CONSUMER_KEY,
                       CONSUMER_SECRET),
            api_version='1.1')
        self.tmblr = tumblpy.Tumblpy(app_key=TUMBLR_KEY,
                                     app_secret=TUMBLR_SECRET,
                                     oauth_token=TOKEN_KEY,
                                     oauth_token_secret=TOKEN_SECRET
                                     )

    def stream_iter(self):
        """returns a stream iterator."""
        # this is still here because it is ocassionally used for testing.
        # streaming is now handled by StreamHandler.
        return self.stream.statuses.sample(language='en', stall_warnings='true')

    def fetch_tweet(self, tweet_id):
        """
        attempts to retrieve the specified tweet. returns False on failure.
        """
        try:
            tweet = self.twitter.statuses.show(
                id=str(tweet_id),
                include_entities='false')
            return tweet
        except httplib.IncompleteRead as err:
            # print statements for debugging
            logging.debug(err)
            print(err)
            return False
        except TwitterError as err:
            logging.debug('error fetching tweet %i' % tweet_id)
            try:
                if err.e.code == 404:
                    # we reraise 404s, and return false on other exceptions.
                    # 404 means we should not use this resource any more.
                    raise
            except AttributeError:
                pass
            return False
        except Exception as err:
            print('unhandled exception suppressed in fetch_tweet', err)

    def retweet(self, tweet_id):
        try:
            success = self.twitter.statuses.retweet(id=tweet_id)
        except TwitterError as err:
            logging.debug(err)
            return False
        if success:
            return True
        else:
            return False

    def delete_last_tweet(self):
        try:
            tweet = self.twitter.statuses.user_timeline(count="1")[0]
        except TwitterError as err:
            logging.debug(err)
            return False
        try:
            success = self.twitter.statuses.destroy(id=tweet['id_str'])
        except TwitterError as err:
            print(err)
            return False

        if success:
            return True
        else:
            return False

    def url_for_tweet(self, tweet_id):
        tweet = self.fetch_tweet(tweet_id)
        if tweet:
            username = tweet.get('user').get('screen_name')
            return('https://www.twitter.com/%s/status/%s'
                   % (username, str(tweet_id)))
        return False

    def oembed_for_tweet(self, tweet_id):
        return (self.twitter.statuses.oembed(_id=tweet_id))

    def retweet_hit(self, hit):
        """
        handles retweeting a pair of tweets & various possible failures
        """
        if not self.retweet(hit['tweet_one']['tweet_id']):
            return False
        if not self.retweet(hit['tweet_two']['tweet_id']):
            self.delete_last_tweet()
            return False
        return True

    def tumbl_tweets(self, tweetone, tweettwo):
        """
        posts a pair of tweets to tumblr. for url needs real tweet from twitter
        """
        sn1 = tweetone.get('user').get('screen_name')
        sn2 = tweettwo.get('user').get('screen_name')
        oembed1 = self.oembed_for_tweet(tweetone.get('id_str'))
        oembed2 = self.oembed_for_tweet(tweettwo.get('id_str'))
        post_title = "@%s vs @%s" % (sn1, sn2)
        post_content = '<div class="tweet-pair">%s<br /><br />%s</div>' % (oembed1['html'], oembed2['html'])
        post = self.tmblr.post('post',
                               blog_url=TUMBLR_BLOG_URL,
                               params={'type': 'text',
                                       'title': post_title,
                                       'body': post_content
                                       })
        if not post:
            return False
        return True

    def post_hit(self, hit):
        try:
            t1 = self.fetch_tweet(hit['tweet_one']['tweet_id'])
            t2 = self.fetch_tweet(hit['tweet_two']['tweet_id'])
        except TwitterHTTPError as err:
            print('error posting tweet', err)
            return False
        if not t1 or not t2:
            print('failed to fetch tweets')
            # tweet doesn't exist or is unavailable
            # TODO: better error handling here
            return False
        # retewet hits
        if not self.retweet_hit(hit):
            print('failed to retweet hits')
            return False
        if not self.tumbl_tweets(t1, t2):
            # if a tumblr post fails in a forest and nobody etc
            logging.warning('tumblr failed with hit', hit)
        return True


if __name__ == "__main__":

    count = 0
    stream = StreamHandler()
    stream.start()

    for t in stream:
        count += 1
        # print(count)

        print(t['tweet_text'], 'buffer length: %i' % len(stream._buffer))
        # if count > 100:
        #     stream.close()

########NEW FILE########
